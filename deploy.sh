#!/bin/bash

# TrynDraft Deployment Script
set -e  # Exit on error

echo "🚀 Starting TrynDraft deployment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    echo "📄 Loading environment variables from .env file"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠️  No .env file found. Using default values."
fi

# Check for required environment variables
if [ -z "$SECRET_KEY" ]; then
    echo "❌ SECRET_KEY is not set. Please set it in .env file"
    exit 1
fi

echo "🔨 Building Docker images..."
docker-compose build

echo "📦 Pulling latest images..."
docker-compose pull

echo "🔄 Stopping existing containers..."
docker-compose down

echo "🚀 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be healthy..."
sleep 10

echo "📊 Checking service status..."
docker-compose ps

echo "✅ Deployment complete!"
echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "📝 Logs: docker-compose logs -f"
echo "🛑 Stop: docker-compose down"
echo ""