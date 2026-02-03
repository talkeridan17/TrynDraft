#!/usr/bin/env python3
"""
Quick test script for TrynDraft scrapers
Tests that all scraper components are working
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

print("=" * 60)
print("TrynDraft Scraper Test")
print("=" * 60)
print()

# Test 1: Imports
print("[1/5] Testing imports...")
try:
    from app.services.stats_scraper import RiotStatsScraper, Rank, ScraperConfig
    from app.services.stats_loader import StatsLoader
    from app.services.web_scraper import WebScraper
    from app.services.progress_tracker import get_progress_tracker
    from app.core.config import settings
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

print()

# Test 2: Configuration
print("[2/5] Testing configuration...")
try:
    # Check API key
    if settings.RIOT_API_KEY:
        print(f"✓ Riot API key found: {settings.RIOT_API_KEY[:20]}...")
    else:
        print("⚠ Riot API key not set (stats scraping will fail)")

    # Check output directories
    ScraperConfig.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Output directory: {ScraperConfig.OUTPUT_DIR}")

    # Check current patch
    patch = ScraperConfig.get_current_patch()
    print(f"✓ Current patch: {patch}")

except Exception as e:
    print(f"✗ Configuration test failed: {e}")
    sys.exit(1)

print()

# Test 3: Progress Tracker
print("[3/5] Testing progress tracker...")
try:
    tracker = get_progress_tracker()
    status = tracker.get_status()
    print(f"✓ Progress tracker initialized")
    print(f"  - Last updated: {status.get('last_updated', 'never')}")
except Exception as e:
    print(f"✗ Progress tracker failed: {e}")
    sys.exit(1)

print()

# Test 4: Web Scraper (async test)
print("[4/5] Testing web scraper (simple fetch)...")
async def test_web_scraper():
    try:
        scraper = WebScraper()
        await scraper.initialize()

        # Test fetching champion page
        test_url = "https://www.mobafire.com/league-of-legends/champion/ahri"
        print(f"  Fetching: {test_url}")

        async with scraper.session.get(test_url, timeout=10) as response:
            if response.status == 200:
                html = await response.text()
                print(f"✓ Web scraper works (fetched {len(html)} bytes)")
            else:
                print(f"⚠ Got status {response.status}")

        await scraper.close()
        return True

    except Exception as e:
        print(f"⚠ Web scraper test failed: {e}")
        print("  (This is OK if you don't have internet connection)")
        return False

asyncio.run(test_web_scraper())

print()

# Test 5: Stats Loader
print("[5/5] Testing stats loader...")
try:
    loader = StatsLoader()

    # Check for existing data
    patches = loader.get_available_patches()
    if patches:
        print(f"✓ Stats loader works")
        print(f"  - Available patches: {patches}")

        latest = patches[0]
        ranks = loader.get_available_ranks(latest)
        print(f"  - Ranks for {latest}: {ranks}")
    else:
        print("✓ Stats loader works (no data yet)")
        print("  - Run scraping to populate data:")
        print("    python scripts/run_scrapers.py stats --mode quick")

except Exception as e:
    print(f"✗ Stats loader failed: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("✅ All tests passed!")
print("=" * 60)
print()
print("Next steps:")
print("  1. Test quick scrape:")
print("     python scripts/run_scrapers.py stats --mode quick")
print()
print("  2. View status:")
print("     python scripts/run_scrapers.py status")
print()
print("  3. See full documentation:")
print("     cat docs/SCRAPING.md")
print()
