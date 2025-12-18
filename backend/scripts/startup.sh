#!/bin/bash
# scripts/startup.sh

echo "Starting TrynDraft Backend..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your configuration and restart."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Seed database if needed
if [ "$SEED_DATABASE" = "true" ]; then
    echo "Seeding database..."
    python scripts/seed_database.py
fi

# Run initial scraping if needed
if [ "$INITIAL_SCRAPE" = "true" ]; then
    echo "Running initial data scrape..."
    python scripts/initial_scrape.py
fi

# Start the server
echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload