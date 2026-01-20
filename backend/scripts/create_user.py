#!/usr/bin/env python3
"""Script to create the initial user in the database."""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import User
from app.auth import get_password_hash


def create_user(username: str, password: str, email: str = None):
    """Create a user in the database."""
    db = SessionLocal()

    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"User '{username}' already exists in database.")
            return False

        # Hash the password
        hashed_password = get_password_hash(password)

        # Create user
        new_user = User(
            username=username,
            email=email or f"{username}@example.com",
            hashed_password=hashed_password,
            is_active=True
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        print(f"✅ Successfully created user '{username}' (ID: {new_user.id})")
        return True

    except Exception as e:
        print(f"❌ Error creating user: {e}")
        db.rollback()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    import os
    import argparse

    parser = argparse.ArgumentParser(description="Create a user in the database")
    parser.add_argument("--username", "-u", help="Username", default=os.environ.get("CREATE_USER_USERNAME"))
    parser.add_argument("--password", "-p", help="Password", default=os.environ.get("CREATE_USER_PASSWORD"))
    parser.add_argument("--email", "-e", help="Email (optional)")

    args = parser.parse_args()

    if not args.username or not args.password:
        print("Usage: python create_user.py -u USERNAME -p PASSWORD [-e EMAIL]")
        print("Or set CREATE_USER_USERNAME and CREATE_USER_PASSWORD environment variables")
        sys.exit(1)

    print(f"Creating user '{args.username}'...")
    success = create_user(args.username, args.password, args.email)
    sys.exit(0 if success else 1)
