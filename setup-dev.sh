#!/bin/bash

# TrynDraft Development Setup Script
echo "🔧 Setting up TrynDraft for development..."

# Backend setup
echo "📦 Setting up backend..."
cd backend

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Set up database
echo "🗄️  Setting up database..."
if command -v createdb &> /dev/null; then
    createdb tryndraft_dev 2>/dev/null || true
fi

# Run migrations
echo "🔄 Running database migrations..."
alembic upgrade head

# Seed data
echo "🌱 Seeding initial data..."
python -c "
from app.database import engine
from app.models import Base
Base.metadata.create_all(bind=engine)
print('✅ Database created')
"

cd ..

# Frontend setup
echo "📦 Setting up frontend..."
cd frontend

# Install dependencies
echo "📦 Installing Node.js dependencies..."
npm install

cd ..

echo "✅ Development setup complete!"
echo ""
echo "To start development servers:"
echo ""
echo "Backend:"
echo "  cd backend"
echo "  source .venv/bin/activate"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Frontend:"
echo "  cd frontend"
echo "  npm run dev"
echo ""
echo "Or use Docker:"
echo "  docker-compose up"