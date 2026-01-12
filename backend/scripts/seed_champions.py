#!/usr/bin/env python3
"""
Seed the database with champion data from Riot Games Data Dragon API.
This script fetches all champions and their information from the official API
and populates the champions table.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import asyncio
import httpx
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.models import Champion, Base
from datetime import datetime, timezone

# Data Dragon API endpoints
VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
CHAMPION_DATA_URL = "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"


async def get_latest_version() -> str:
    """Get the latest League of Legends version from Data Dragon."""
    async with httpx.AsyncClient() as client:
        response = await client.get(VERSIONS_URL)
        response.raise_for_status()
        versions = response.json()
        return versions[0]  # First item is the latest version


async def fetch_champion_data(version: str) -> dict:
    """Fetch all champion data from Data Dragon."""
    url = CHAMPION_DATA_URL.format(version=version)
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        return data["data"]


def seed_champions(db: Session, champions_data: dict, version: str):
    """Seed the champions table with data from Data Dragon."""

    print(f"\nSeeding {len(champions_data)} champions...")

    added = 0
    updated = 0

    for champion_id, champion_info in champions_data.items():
        # Check if champion already exists
        existing = db.query(Champion).filter(Champion.id == champion_id).first()

        # Parse tags (roles)
        tags = champion_info.get("tags", [])
        primary_role = tags[0] if tags else "Fighter"

        # Map Riot roles to our roles (convert to list)
        role_mapping = {
            "Assassin": ["MID"],
            "Fighter": ["TOP"],
            "Mage": ["MID"],
            "Marksman": ["ADC"],
            "Support": ["SUPPORT"],
            "Tank": ["TOP"]
        }

        roles = role_mapping.get(primary_role, ["FILL"])

        if existing:
            # Update existing champion
            existing.name = champion_info["name"]
            existing.key = champion_info["key"]
            existing.title = champion_info["title"]
            existing.roles = roles
            existing.difficulty = int(champion_info["info"]["difficulty"])
            existing.attack = int(champion_info["info"]["attack"])
            existing.defense = int(champion_info["info"]["defense"])
            existing.magic = int(champion_info["info"]["magic"])
            existing.updated_at = datetime.now(timezone.utc)
            updated += 1
        else:
            # Create new champion
            new_champion = Champion(
                id=champion_id,
                name=champion_info["name"],
                key=champion_info["key"],
                title=champion_info["title"],
                roles=roles,
                difficulty=int(champion_info["info"]["difficulty"]),
                attack=int(champion_info["info"]["attack"]),
                defense=int(champion_info["info"]["defense"]),
                magic=int(champion_info["info"]["magic"]),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(new_champion)
            added += 1

    db.commit()

    print(f"✅ Seeding complete!")
    print(f"   - Added: {added} champions")
    print(f"   - Updated: {updated} champions")
    print(f"   - Total: {added + updated} champions")


async def main():
    """Main function to seed the database."""
    print("=" * 60)
    print("TrynDraft - Champion Data Seeder")
    print("=" * 60)

    try:
        # Get latest version
        print("\n📥 Fetching latest version from Data Dragon...")
        version = await get_latest_version()
        print(f"   Latest version: {version}")

        # Fetch champion data
        print("\n📥 Fetching champion data...")
        champions_data = await fetch_champion_data(version)
        print(f"   Found {len(champions_data)} champions")

        # Seed database
        db = SessionLocal()
        try:
            seed_champions(db, champions_data, version)
        finally:
            db.close()

        print("\n" + "=" * 60)
        print("✨ Database seeded successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
