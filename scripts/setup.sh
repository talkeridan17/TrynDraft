#!/usr/bin/env bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Installing frontend dependencies..."
cd "$REPO_ROOT/frontend"
npm install

echo "Done. Run ./scripts/start.sh to launch the app."
