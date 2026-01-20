"""
Pytest configuration and fixtures for TrynDraft backend tests.
"""
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
from app.main import app
from app.models import Base, User, Champion, Draft
from app.auth import get_password_hash

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///./test_tryndraft.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create a fresh database for each test."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_db: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword123"),
        summoner_name="TestSummoner",
        region="NA"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_champion(test_db: Session) -> Champion:
    """Create a test champion."""
    champion = Champion(
        id="aatrox",
        name="Aatrox",
        key="aatrox",
        title="The Darkin Blade",
        roles=["TOP", "MID"],
        attack=8,
        defense=5,
        magic=3,
        difficulty=4,
        patch="14.24",
        win_rate=5100,  # 51.00%
        pick_rate=800,   # 8.00%
        ban_rate=500,    # 5.00%
        counters={
            "TOP": {
                "Fiora": {"wins": 45, "games": 100},
                "Irelia": {"wins": 52, "games": 100}
            }
        },
        synergies={
            "LeeSin": {"wins": 54, "games": 100},
            "Thresh": {"wins": 56, "games": 100}
        }
    )
    test_db.add(champion)
    test_db.commit()
    test_db.refresh(champion)
    return champion


@pytest.fixture
def auth_headers(client: TestClient, test_user: User) -> dict:
    """Get authentication headers for a test user."""
    response = client.post(
        "/api/v1/users/login",
        data={
            "username": "testuser",
            "password": "testpassword123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_draft_state() -> dict:
    """Sample draft state for testing."""
    return {
        "phase": "PICK",
        "turn": 10,
        "side": "BLUE",
        "role": "TOP",
        "elo": "PLATINUM",
        "patch": "14.24",
        "bans_blue": ["Yasuo", "Yone", "Zed"],
        "bans_red": ["Akali", "Katarina", "LeBlanc"],
        "picks_blue": [
            {"champion": "Jinx", "role": "ADC"},
            {"champion": "Thresh", "role": "SUPPORT"}
        ],
        "picks_red": [
            {"champion": "Kaisa", "role": "ADC"},
            {"champion": "Nautilus", "role": "SUPPORT"}
        ]
    }


@pytest.fixture
def multiple_champions(test_db: Session) -> list:
    """Create multiple test champions."""
    champions_data = [
        ("ahri", "Ahri", ["MID"], 5200, 1000, 300),
        ("jinx", "Jinx", ["ADC"], 5100, 900, 200),
        ("thresh", "Thresh", ["SUPPORT"], 4900, 1200, 400),
        ("lee-sin", "Lee Sin", ["JUNGLE"], 4800, 1500, 600),
        ("garen", "Garen", ["TOP"], 5300, 500, 100),
    ]

    champions = []
    for champ_id, name, roles, win_rate, pick_rate, ban_rate in champions_data:
        champion = Champion(
            id=champ_id,
            name=name,
            key=champ_id.replace("-", ""),
            roles=roles,
            patch="14.24",
            win_rate=win_rate,
            pick_rate=pick_rate,
            ban_rate=ban_rate,
            attack=5,
            defense=5,
            magic=5,
            difficulty=5
        )
        test_db.add(champion)
        champions.append(champion)

    test_db.commit()
    return champions
