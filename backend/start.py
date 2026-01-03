#!/usr/bin/env python3
"""Start the TrynDraft backend with database initialization."""

import os
import sys
import subprocess

def main():
    print("🚀 Starting TrynDraft Backend Setup")
    print("=" * 50)
    
    # Check if database exists
    db_file = "tryndraft.db"
    if not os.path.exists(db_file):
        print("Creating database tables...")
        try:
            # Add current directory to Python path
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            
            from app.database import engine, Base
            from app import models
            
            Base.metadata.create_all(bind=engine)
            print(f"✅ Created {db_file}")
        except Exception as e:
            print(f"❌ Error creating database: {e}")
            return
    
    # Check if requirements are installed
    print("Checking dependencies...")
    try:
        import fastapi
        import sqlalchemy
        import uvicorn
        print("✅ Dependencies are installed")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return
    
    # Start the server
    print("\nStarting FastAPI server...")
    print("Access the API at: http://localhost:8000")
    print("API Documentation at: http://localhost:8000/api/docs")
    print("\nPress Ctrl+C to stop the server\n")
    
    os.system("uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")

if __name__ == "__main__":
    main()