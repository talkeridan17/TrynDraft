#!/bin/bash

# TrynDraft Production Deployment Script
# Usage: ./deploy.sh [dev|prod|stop|logs|status]

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! docker info > /dev/null 2>&1; then
        log_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available."
        exit 1
    fi

    log_success "Prerequisites satisfied"
}

# Load environment
load_env() {
    if [ -f .env ]; then
        log_info "Loading environment from .env"
        set -a
        source .env
        set +a
    else
        log_error ".env file not found. Copy .env.example to .env and configure it."
        exit 1
    fi

    # Validate required variables
    if [ -z "$SECRET_KEY" ]; then
        log_error "SECRET_KEY is not set in .env"
        exit 1
    fi

    if [ -z "$POSTGRES_PASSWORD" ]; then
        log_error "POSTGRES_PASSWORD is not set in .env"
        exit 1
    fi

    log_success "Environment loaded"
}

# Start development mode
start_dev() {
    log_info "Starting TrynDraft in DEVELOPMENT mode..."

    export DEBUG=True
    docker compose up -d --build

    wait_for_services
    show_status
}

# Start production mode
start_prod() {
    log_info "Starting TrynDraft in PRODUCTION mode..."

    export DEBUG=False
    docker compose up -d --build

    # Run migrations
    log_info "Running database migrations..."
    docker compose run --rm migrations

    wait_for_services
    show_status
}

# Stop all services
stop_services() {
    log_info "Stopping all TrynDraft services..."
    docker compose down
    log_success "All services stopped"
}

# Wait for services to be healthy
wait_for_services() {
    log_info "Waiting for services to be ready..."

    # Wait for PostgreSQL
    echo -n "  PostgreSQL: "
    for i in {1..30}; do
        if docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-postgres}" > /dev/null 2>&1; then
            echo -e "${GREEN}ready${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done

    # Wait for backend
    echo -n "  Backend API: "
    for i in {1..60}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}ready${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done

    # Wait for frontend
    echo -n "  Frontend: "
    for i in {1..30}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            echo -e "${GREEN}ready${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done

    echo ""
}

# Show service status
show_status() {
    log_info "Service Status:"
    docker compose ps

    echo ""
    log_success "TrynDraft is running!"
    echo ""
    echo "🌐 Frontend:    http://localhost:3000"
    echo "🔧 Backend API: http://localhost:8000"
    echo "📚 API Docs:    http://localhost:8000/docs"
    echo "🗄️  PostgreSQL: localhost:5432"
    echo ""
    echo "Commands:"
    echo "  ./deploy.sh logs    - View logs"
    echo "  ./deploy.sh stop    - Stop all services"
    echo "  ./deploy.sh status  - Show service status"
    echo ""
}

# Show logs
show_logs() {
    docker compose logs -f "$@"
}

# Trigger data scraping
trigger_scrape() {
    log_info "Triggering champion stats scraping..."
    curl -X POST http://localhost:8000/api/v1/admin/scrape/stats
    echo ""
    log_info "Scraping started in background. Check logs for progress."
}

# Train neural network
train_nn() {
    log_info "Training neural network model..."
    docker compose exec backend python -c "
from app.services.nn_trainer import train_model
result = train_model(epochs=100)
print(f'Training complete: {result}')
"
}

# Main script
main() {
    case "${1:-}" in
        dev)
            check_prerequisites
            load_env
            start_dev
            ;;
        prod)
            check_prerequisites
            load_env
            start_prod
            ;;
        stop)
            stop_services
            ;;
        logs)
            shift
            show_logs "$@"
            ;;
        status)
            show_status
            ;;
        scrape)
            trigger_scrape
            ;;
        train)
            train_nn
            ;;
        *)
            echo "TrynDraft Deployment Script"
            echo ""
            echo "Usage: ./deploy.sh [command]"
            echo ""
            echo "Commands:"
            echo "  dev      Start in development mode (hot reload enabled)"
            echo "  prod     Start in production mode"
            echo "  stop     Stop all services"
            echo "  logs     View service logs (use: logs backend, logs frontend, etc.)"
            echo "  status   Show service status"
            echo "  scrape   Trigger champion data scraping"
            echo "  train    Train neural network model"
            echo ""
            ;;
    esac
}

main "$@"
