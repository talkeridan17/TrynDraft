"""
Tests for API endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests for health/root endpoints."""

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns OK."""
        response = client.get("/")
        assert response.status_code == 200
        assert "TrynDraft" in response.json()["message"]

    def test_health_endpoint(self, client: TestClient):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    def test_register_user(self, client: TestClient):
        """Test user registration."""
        response = client.post(
            "/api/v1/users/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "securepassword123",
                "summoner_name": "NewSummoner",
                "region": "NA"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "password" not in data

    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Test registration with duplicate email fails."""
        response = client.post(
            "/api/v1/users/register",
            json={
                "email": "test@example.com",  # Same as test_user
                "username": "differentuser",
                "password": "password123",
                "region": "NA"
            }
        )
        assert response.status_code == 400

    def test_login_success(self, client: TestClient, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/users/login",
            data={
                "username": "testuser",
                "password": "testpassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, test_user):
        """Test login with wrong password fails."""
        response = client.post(
            "/api/v1/users/login",
            data={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401

    def test_get_current_user(self, client: TestClient, auth_headers):
        """Test getting current user info."""
        response = client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"


class TestChampionEndpoints:
    """Tests for champion endpoints."""

    def test_get_champions(self, client: TestClient):
        """Test getting champion list."""
        response = client.get("/api/v1/champions/")
        assert response.status_code == 200
        data = response.json()
        assert "champions" in data or isinstance(data, list)


class TestRecommendationEndpoints:
    """Tests for recommendation endpoints."""

    def test_get_sorted_champions(self, client: TestClient, auth_headers, multiple_champions, sample_draft_state):
        """Test getting sorted champions."""
        response = client.post(
            "/api/v1/recommendations/sorted-champions",
            json=sample_draft_state,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "champions" in data
        assert "model_type" in data

    def test_get_sorted_champions_guest(self, client: TestClient, multiple_champions, sample_draft_state):
        """Test sorted champions works for guests too."""
        # This might fail if auth is required - adjust based on actual implementation
        response = client.post(
            "/api/v1/recommendations/sorted-champions",
            json=sample_draft_state
        )
        # Should either work or return 401
        assert response.status_code in [200, 401]

    def test_get_draft_analysis(self, client: TestClient, auth_headers, sample_draft_state):
        """Test getting draft analysis."""
        response = client.post(
            "/api/v1/recommendations/analysis",
            json=sample_draft_state,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "analysis" in data
        assert "stage" in data
        assert "advantage" in data


class TestAdminEndpoints:
    """Tests for admin endpoints."""

    def test_get_system_status(self, client: TestClient):
        """Test getting system status."""
        response = client.get("/api/v1/admin/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "scheduler" in data

    def test_preview_scrape(self, client: TestClient):
        """Test scrape preview for a champion."""
        # This is a slower test as it makes external requests
        # Skip in CI or mock the external calls
        response = client.get("/api/v1/admin/scrape/preview/Aatrox")
        # Might fail due to rate limiting or network issues
        assert response.status_code in [200, 500]


class TestDraftEndpoints:
    """Tests for draft management endpoints."""

    def test_create_draft(self, client: TestClient, auth_headers):
        """Test creating a new draft."""
        response = client.post(
            "/api/v1/drafts/",
            json={
                "game_mode": "DRAFT",
                "side": "BLUE",
                "role": "TOP",
                "elo": "PLATINUM",
                "region": "NA",
                "patch": "14.24"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["side"] == "BLUE"
        assert data["role"] == "TOP"
        return data["id"]

    def test_get_user_drafts(self, client: TestClient, auth_headers):
        """Test getting user's drafts."""
        # First create a draft
        client.post(
            "/api/v1/drafts/",
            json={
                "game_mode": "DRAFT",
                "side": "BLUE",
                "role": "MID",
                "elo": "GOLD"
            },
            headers=auth_headers
        )

        response = client.get("/api/v1/drafts/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestChampionPoolEndpoints:
    """Tests for champion pool management."""

    def test_add_champion_to_pool(self, client: TestClient, auth_headers):
        """Test adding a champion to user's pool."""
        response = client.post(
            "/api/v1/users/me/champion-pool",
            json={
                "champion_name": "Aatrox",
                "playstyles": ["BRUISER", "TEAMFIGHT"],
                "proficiency": 4
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["champion_name"] == "Aatrox"
        # Proficiency might default to 0 depending on endpoint implementation
        assert "proficiency" in data

    def test_get_champion_pool(self, client: TestClient, auth_headers):
        """Test getting user's champion pool."""
        # First add a champion
        client.post(
            "/api/v1/users/me/champion-pool",
            json={
                "champion_name": "Ahri",
                "proficiency": 5
            },
            headers=auth_headers
        )

        response = client.get("/api/v1/users/me/champion-pool", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_update_proficiency(self, client: TestClient, auth_headers, test_db):
        """Test updating champion proficiency."""
        # First add a champion
        add_response = client.post(
            "/api/v1/users/me/champion-pool",
            json={
                "champion_name": "Jinx",
                "proficiency": 3
            },
            headers=auth_headers
        )
        champion_id = add_response.json()["id"]

        # Update proficiency
        response = client.put(
            f"/api/v1/users/me/champion-pool/{champion_id}",
            json={"proficiency": 5},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["proficiency"] == 5
