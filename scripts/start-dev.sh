#!/bin/bash
#
# TrynDraft Development Server Starter
# ------------------------------------
# Starts both backend and frontend servers
#
# Usage: ./scripts/start-dev.sh
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo -e "${BLUE}Starting TrynDraft Development Servers...${NC}"
echo ""

# Kill any existing servers
echo "Stopping any existing servers..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 1

# Start backend
echo -e "${GREEN}Starting backend server...${NC}"
cd "$PROJECT_ROOT/backend"
source .venv/bin/activate
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/tryndraft-backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Start frontend
echo -e "${GREEN}Starting frontend server...${NC}"
cd "$PROJECT_ROOT/frontend"
nohup npm run dev > /tmp/tryndraft-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

# Wait for servers to start
echo ""
echo "Waiting for servers to start..."
sleep 3

# Check if servers are running
if curl -s http://localhost:8000/api/v1/champions/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend is running at http://localhost:8000"
else
    echo "⚠ Backend may still be starting... check /tmp/tryndraft-backend.log"
fi

if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend is running at http://localhost:5173"
else
    echo "⚠ Frontend may still be starting... check /tmp/tryndraft-frontend.log"
fi

echo ""
echo "=================================================="
echo "  TrynDraft Development Servers Started"
echo "=================================================="
echo ""
echo "URLs:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Logs:"
echo "  Backend:  tail -f /tmp/tryndraft-backend.log"
echo "  Frontend: tail -f /tmp/tryndraft-frontend.log"
echo ""
echo "To stop: ./scripts/stop-dev.sh or pkill -f 'uvicorn|vite'"
echo ""
