#!/usr/bin/env bash
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting TrynDraft dev server..."
echo "Open http://localhost:5173 in your browser."
echo "Press Ctrl+C to stop."

cd "$REPO_ROOT/frontend"
npm run dev
