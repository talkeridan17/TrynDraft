#!/usr/bin/env bash
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG=/tmp/tryndraft-dev.log

# Kill anything holding port 5173 or 5174
for PORT in 5173 5174; do
  PID=$(lsof -ti:$PORT 2>/dev/null)
  [ -n "$PID" ] && kill -9 $PID 2>/dev/null && echo "Killed stale process on :$PORT"
done
pkill -f "vite" 2>/dev/null || true
sleep 0.8

cd "$REPO_ROOT/frontend"

# Run Vite in background so Ctrl+C in this terminal can't kill it
nohup npm run dev > "$LOG" 2>&1 &
VITE_PID=$!

echo "Server starting (PID $VITE_PID)..."

# Wait up to 10 seconds for Vite to be ready
for i in $(seq 1 33); do
  if grep -q "Local:" "$LOG" 2>/dev/null; then
    echo "✓ Dev server ready → http://localhost:5173"
    echo "  Logs: tail -f $LOG"
    echo "  Stop: ./scripts/stop.sh"
    exit 0
  fi
  sleep 0.3
done

echo "Server may still be starting. Check: tail -f $LOG"
echo "Stop: ./scripts/stop.sh"
