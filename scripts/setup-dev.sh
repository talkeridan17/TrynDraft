#!/bin/bash
#
# TrynDraft Development Setup Script
# ----------------------------------
# One-command setup for new contributors
#
# Usage: ./scripts/setup-dev.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_step() {
    echo -e "\n${BLUE}==>${NC} ${GREEN}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

print_error() {
    echo -e "${RED}Error:${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Header
echo ""
echo "=================================================="
echo "   TrynDraft Development Environment Setup"
echo "=================================================="
echo ""

# Check prerequisites
print_step "Checking prerequisites..."

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_success "Python 3 found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.12+"
    exit 1
fi

# Check Node.js
if command_exists node; then
    NODE_VERSION=$(node --version)
    print_success "Node.js found: $NODE_VERSION"
else
    print_error "Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Check npm
if command_exists npm; then
    NPM_VERSION=$(npm --version)
    print_success "npm found: $NPM_VERSION"
else
    print_error "npm not found. Please install npm"
    exit 1
fi

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo "Project root: $PROJECT_ROOT"

# ========================================
# Backend Setup
# ========================================
print_step "Setting up backend..."

cd "$PROJECT_ROOT/backend"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    print_step "Creating Python virtual environment..."
    python3 -m venv .venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment exists"
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
print_step "Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
print_success "Python dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_step "Creating backend .env file..."
    cat > .env << 'EOF'
# Database
DATABASE_URL=sqlite:///./tryndraft.db

# Security - Generate a new key: openssl rand -hex 32
SECRET_KEY=dev-secret-key-change-in-production

# LLM Configuration (disabled by default to prevent charges)
USE_HUGGINGFACE_API=false
HF_TOKEN=

# Riot API (optional, for scraping)
RIOT_API_KEY=

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
EOF
    print_success "Backend .env created"
    print_warning "Edit backend/.env to add your API keys"
else
    print_success "Backend .env exists"
fi

# Initialize database
print_step "Initializing database..."
python3 -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)" 2>/dev/null
print_success "Database initialized"

# Seed champion data
print_step "Seeding champion data from Data Dragon..."
python3 scripts/seed_champions.py 2>/dev/null || {
    print_warning "Seed script had issues, but continuing..."
}
print_success "Champion data seeded"

# Deactivate virtual environment
deactivate

# ========================================
# Frontend Setup
# ========================================
print_step "Setting up frontend..."

cd "$PROJECT_ROOT/frontend"

# Install dependencies
print_step "Installing npm dependencies..."
npm install --silent
print_success "npm dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_step "Creating frontend .env file..."
    cat > .env << 'EOF'
VITE_API_URL=http://localhost:8000
EOF
    print_success "Frontend .env created"
else
    print_success "Frontend .env exists"
fi

# ========================================
# Final Summary
# ========================================
cd "$PROJECT_ROOT"

echo ""
echo "=================================================="
echo "   Setup Complete!"
echo "=================================================="
echo ""
echo "To start development:"
echo ""
echo "  ${GREEN}1. Start backend:${NC}"
echo "     cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo ""
echo "  ${GREEN}2. Start frontend (new terminal):${NC}"
echo "     cd frontend && npm run dev"
echo ""
echo "  ${GREEN}Or use the convenience script:${NC}"
echo "     ./scripts/start-dev.sh"
echo ""
echo "URLs:"
echo "  - Frontend: http://localhost:5173"
echo "  - Backend:  http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "Next steps:"
echo "  - Edit backend/.env to add your HF_TOKEN and RIOT_API_KEY"
echo "  - Read CONTRIBUTING.md for coding guidelines"
echo "  - Check docs/wiki/ for documentation"
echo ""
