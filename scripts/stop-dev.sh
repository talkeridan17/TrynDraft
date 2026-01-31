#!/bin/bash
#
# TrynDraft Development Server Stopper
# ------------------------------------
# Stops both backend and frontend servers
#
# Usage: ./scripts/stop-dev.sh
#

echo "Stopping TrynDraft development servers..."

pkill -f "uvicorn app.main:app" 2>/dev/null && echo "✓ Backend stopped" || echo "Backend was not running"
pkill -f "vite" 2>/dev/null && echo "✓ Frontend stopped" || echo "Frontend was not running"

echo "Done."
