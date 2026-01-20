#!/usr/bin/env python3
"""
Quick CLI utility to check scraping and training progress.
Usage: python scripts/check_progress.py
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.progress_tracker import get_progress_tracker


def main():
    tracker = get_progress_tracker()
    print(tracker.get_summary())


if __name__ == "__main__":
    main()
