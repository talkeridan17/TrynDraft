#!/usr/bin/env bash
echo "Stopping TrynDraft dev server..."
pkill -f "vite" 2>/dev/null && echo "Stopped." || echo "No running dev server found."
