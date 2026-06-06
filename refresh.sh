#!/usr/bin/env bash
# TrynDraft Model Refresh
# Run from the repo root (or anywhere — the script finds its own location).
#
# Full retrain (requires RIOT_API_KEY in .env or as env var):
#   ./refresh.sh
#
# Retrain on existing data (no API key needed):
#   ./refresh.sh --skip-scrape
#
# Fine-tune from current checkpoint (faster):
#   ./refresh.sh --skip-scrape --fine-tune --epochs 30
#
# After it finishes, commit frontend/public/models/ and push to dev:
#   git add frontend/public/models/
#   git commit -m "model: retrain $(date +%Y-%m-%d)"
#   git push origin dev

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env if present
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

cd model-training
python training/refresh.py "$@"
