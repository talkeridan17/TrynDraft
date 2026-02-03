#!/usr/bin/env python3
"""
TrynDraft Unified Scraper Runner
================================
Orchestrates all scraping operations:
1. Riot API stats scraping (champion stats, matchups, synergies)
2. Web scraping for LLM training (MOBAFire, Reddit)
3. Loading scraped data into database

Usage:
    # Quick test (Challenger only, 1 region)
    python scripts/run_scrapers.py stats --mode quick

    # Scrape specific rank
    python scripts/run_scrapers.py stats --rank GOLD

    # Scrape multiple ranks
    python scripts/run_scrapers.py stats --rank GOLD PLATINUM DIAMOND

    # Full stats scrape (all ranks)
    python scripts/run_scrapers.py stats --mode full

    # LLM text scraping
    python scripts/run_scrapers.py text --test  # Test mode (5 champions)
    python scripts/run_scrapers.py text         # Full scrape

    # Run everything
    python scripts/run_scrapers.py all

    # Load scraped stats into database
    python scripts/run_scrapers.py load --patch 16.2 --rank GOLD
    python scripts/run_scrapers.py load --patch 16.2  # Load all ranks
"""

import sys
import os
import asyncio
import logging
import argparse
from pathlib import Path
from typing import List, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.stats_scraper import (
    RiotStatsScraper, Rank, run_quick_scrape, run_full_scrape,
    run_high_elo_scrape, run_single_rank_scrape
)
from app.services.stats_loader import StatsLoader, load_stats_to_database
from scripts.scrape_llm_training import main as scrape_llm_main
from app.services.progress_tracker import get_progress_tracker
from app.core.config import settings

# Setup logging - use project root logs/ directory with subdirectories
PROJECT_ROOT = Path(__file__).parent.parent.parent  # backend/scripts -> backend -> project root
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Create organized subdirectories
(LOGS_DIR / "text").mkdir(exist_ok=True)
(LOGS_DIR / "stats").mkdir(exist_ok=True)
(LOGS_DIR / "pro").mkdir(exist_ok=True)
(LOGS_DIR / "training").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / 'stats' / 'scraper_runner.log')
    ]
)
logger = logging.getLogger(__name__)


def check_api_key():
    """Check if Riot API key is set."""
    if not settings.RIOT_API_KEY:
        logger.error("❌ RIOT_API_KEY not set in environment!")
        logger.info("Get your API key from: https://developer.riotgames.com/")
        logger.info("Then add it to backend/.env file:")
        logger.info("  RIOT_API_KEY=your-key-here")
        return False
    return True


def run_stats_scraping(args):
    """Run Riot API stats scraping."""
    logger.info("="*60)
    logger.info("Starting Riot API Stats Scraping")
    logger.info("="*60)

    if not check_api_key():
        return 1

    try:
        # Determine scraping mode
        if args.mode == "quick":
            logger.info("Mode: Quick test (Challenger only, NA)")
            result = run_quick_scrape()

        elif args.mode == "high_elo":
            logger.info("Mode: High elo (Challenger, GM, Master, Diamond)")
            result = run_high_elo_scrape()

        elif args.mode == "full":
            logger.info("Mode: Full scrape (all ranks)")
            result = run_full_scrape()

        elif args.rank:
            # Scrape specific ranks
            regions = args.regions or ["na1", "euw1", "kr"]

            for rank_str in args.rank:
                logger.info(f"Scraping {rank_str} from regions: {regions}")
                result = run_single_rank_scrape(rank_str, regions)
                logger.info(f"Completed {rank_str}: {result}")
        else:
            logger.error("Must specify --mode or --rank")
            return 1

        logger.info("\n" + "="*60)
        logger.info("✅ Stats scraping completed successfully!")
        logger.info("="*60)
        logger.info(f"Results: {result}")

        # Show next steps
        logger.info("\nNext steps:")
        logger.info("  1. Load data into database:")
        logger.info(f"     python scripts/run_scrapers.py load --patch {result['patch']}")
        logger.info("  2. Check scraped data:")
        logger.info("     ls -la scraped_data/riot_stats/")

        return 0

    except KeyboardInterrupt:
        logger.info("\n⚠️  Scraping interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"❌ Error during scraping: {e}", exc_info=True)
        return 1


async def run_text_scraping(args):
    """Run web scraping for LLM training data."""
    logger.info("="*60)
    logger.info("Starting Web Scraping for LLM Training")
    logger.info("="*60)

    try:
        # Modify sys.argv for the scrape_llm_training script
        original_argv = sys.argv.copy()
        sys.argv = ['scrape_llm_training.py']
        if args.test:
            sys.argv.append('--test')
        if args.skip_reddit:
            sys.argv.append('--skip-reddit')

        await scrape_llm_main()

        # Restore sys.argv
        sys.argv = original_argv

        logger.info("\n" + "="*60)
        logger.info("✅ Text scraping completed!")
        logger.info("="*60)
        logger.info("Check output at: training_data/")

        return 0

    except KeyboardInterrupt:
        logger.info("\n⚠️  Scraping interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"❌ Error during text scraping: {e}", exc_info=True)
        return 1


def run_data_loading(args):
    """Load scraped stats into database."""
    logger.info("="*60)
    logger.info("Loading Scraped Stats into Database")
    logger.info("="*60)

    try:
        loader = StatsLoader()

        # Show available data
        patches = loader.get_available_patches()
        if not patches:
            logger.error("❌ No scraped data found!")
            logger.info("Run scraping first:")
            logger.info("  python scripts/run_scrapers.py stats --mode quick")
            return 1

        logger.info(f"Available patches: {patches}")

        # Determine patch to load
        patch = args.patch or patches[0]  # Latest by default
        logger.info(f"Loading patch: {patch}")

        ranks = loader.get_available_ranks(patch)
        logger.info(f"Available ranks: {ranks}")

        if not ranks:
            logger.error(f"❌ No data found for patch {patch}")
            return 1

        # Load specific rank or all ranks
        if args.rank:
            # Load each specified rank
            for rank in args.rank:
                if rank not in ranks:
                    logger.warning(f"Rank {rank} not found in scraped data")
                    continue

                logger.info(f"Loading {rank} data...")
                result = loader.update_database_from_rank(patch, rank)
                logger.info(f"  Updated {result['champions_updated']} champions")
                if result['errors']:
                    logger.warning(f"  Errors: {result['errors']}")
        else:
            # Load all ranks
            logger.info("Loading all ranks...")
            result = loader.load_all_ranks(patch)
            logger.info(f"  Total champions updated: {result['total_champions_updated']}")
            for rank, rank_result in result['ranks'].items():
                logger.info(f"  {rank}: {rank_result['champions_updated']} champions")

        logger.info("\n" + "="*60)
        logger.info("✅ Database loading completed!")
        logger.info("="*60)

        return 0

    except Exception as e:
        logger.error(f"❌ Error loading data: {e}", exc_info=True)
        return 1


async def run_all_scrapers(args):
    """Run all scraping operations in sequence."""
    logger.info("="*60)
    logger.info("Running ALL Scrapers")
    logger.info("="*60)

    # 1. Stats scraping (quick mode by default for "all")
    logger.info("\n[1/3] Running stats scraping...")
    args.mode = "quick" if not args.full else "full"
    if run_stats_scraping(args) != 0:
        logger.error("Stats scraping failed")
        return 1

    # 2. Text scraping
    logger.info("\n[2/3] Running text scraping...")
    args.test = not args.full  # Test mode unless full requested
    if await run_text_scraping(args) != 0:
        logger.error("Text scraping failed")
        return 1

    # 3. Load stats into database
    logger.info("\n[3/3] Loading stats into database...")
    args.patch = None  # Use latest
    args.rank = None  # Load all ranks
    if run_data_loading(args) != 0:
        logger.error("Data loading failed")
        return 1

    logger.info("\n" + "="*60)
    logger.info("✅ ALL SCRAPING OPERATIONS COMPLETED!")
    logger.info("="*60)

    # Show progress summary
    tracker = get_progress_tracker()
    print("\n" + tracker.get_summary())

    return 0


def show_status():
    """Show current scraping status."""
    tracker = get_progress_tracker()
    print(tracker.get_summary())


def main():
    parser = argparse.ArgumentParser(
        description="TrynDraft Scraper Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Stats scraping
    stats_parser = subparsers.add_parser('stats', help='Scrape Riot API stats')
    stats_parser.add_argument(
        '--mode',
        choices=['quick', 'high_elo', 'full'],
        help='Scraping mode'
    )
    stats_parser.add_argument(
        '--rank',
        nargs='+',
        choices=['IRON', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM',
                 'EMERALD', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER'],
        help='Specific ranks to scrape'
    )
    stats_parser.add_argument(
        '--regions',
        nargs='+',
        help='Regions to scrape (default: na1 euw1 kr)'
    )

    # Text scraping
    text_parser = subparsers.add_parser('text', help='Scrape web content for LLM training')
    text_parser.add_argument('--test', action='store_true', help='Test mode (5 champions)')
    text_parser.add_argument('--skip-reddit', action='store_true', help='Skip Reddit scraping')

    # Data loading
    load_parser = subparsers.add_parser('load', help='Load scraped data into database')
    load_parser.add_argument('--patch', help='Patch version to load (default: latest)')
    load_parser.add_argument(
        '--rank',
        nargs='+',
        help='Specific ranks to load (default: all)'
    )

    # Run all
    all_parser = subparsers.add_parser('all', help='Run all scraping operations')
    all_parser.add_argument('--full', action='store_true', help='Full scrape (all ranks, all champions)')

    # Status
    subparsers.add_parser('status', help='Show scraping progress status')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Create logs directory
    Path('logs').mkdir(exist_ok=True)

    # Run command
    if args.command == 'stats':
        return run_stats_scraping(args)
    elif args.command == 'text':
        return asyncio.run(run_text_scraping(args))
    elif args.command == 'load':
        return run_data_loading(args)
    elif args.command == 'all':
        return asyncio.run(run_all_scrapers(args))
    elif args.command == 'status':
        show_status()
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
