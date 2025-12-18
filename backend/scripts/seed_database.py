# scripts/seed_database.py
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app import models
from app.auth import get_password_hash
from datetime import datetime

def seed_database():
    """Seed the database with initial data."""
    db = SessionLocal()
    
    try:
        print("Seeding database...")
        
        # Create admin user
        admin_user = db.query(models.User).filter(
            models.User.email == "admin@tryndraft.com"
        ).first()
        
        if not admin_user:
            admin_user = models.User(
                email="admin@tryndraft.com",
                username="admin",
                hashed_password=get_password_hash("admin123"),
                summoner_name="TrynDraftAdmin",
                region="NA",
                is_active=True,
                is_premium=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print("Created admin user")
        
        # Add some test champions to admin's pool
        test_champions = ["Ahri", "Yasuo", "Jinx", "Thresh", "Lee Sin"]
        
        for champ_name in test_champions:
            existing = db.query(models.UserChampionPool).filter(
                models.UserChampionPool.user_id == admin_user.id,
                models.UserChampionPool.champion_name == champ_name
            ).first()
            
            if not existing:
                pool_item = models.UserChampionPool(
                    user_id=admin_user.id,
                    champion_name=champ_name,
                    role="MID" if champ_name == "Ahri" else "TOP",
                    proficiency=4,
                    is_favorite=True,
                    games_played=100,
                    win_rate=55
                )
                db.add(pool_item)
        
        db.commit()
        print("Database seeded successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()