#!/usr/bin/env python3
"""
Simple text data scraper for LLM training.
Scrapes champion guides and meta insights from public sources.

Logs to: logs/text/scrape_TIMESTAMP.log
Output: training_data/text_data.jsonl
"""
import sys
import os
import json
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging to logs/text directory
log_dir = Path("logs/text")
log_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"scrape_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_champion_list() -> List[str]:
    """Get list of all champions from Data Dragon."""
    try:
        # Get latest version
        version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
        versions = requests.get(version_url, timeout=10).json()
        latest = versions[0]

        # Get champion list
        champ_url = f"https://ddragon.leagueoflegends.com/cdn/{latest}/data/en_US/champion.json"
        data = requests.get(champ_url, timeout=10).json()
        champions = list(data['data'].keys())

        logger.info(f"Found {len(champions)} champions from Data Dragon")
        return champions
    except Exception as e:
        logger.error(f"Failed to get champion list: {e}")
        return []

def scrape_champion_text_data(champion: str) -> Dict:
    """
    Scrape text data for a champion.
    Currently a placeholder that generates sample data.
    TODO: Implement actual scraping from MOBAFire/LoLalytics
    """
    # For now, generate placeholder data
    # Real implementation would scrape from:
    # - MOBAFire: https://www.mobafire.com/league-of-legends/{champion}-guide
    # - LoLalytics: https://lolalytics.com/lol/{champion}/build/

    return {
        "champion": champion,
        "timestamp": datetime.now().isoformat(),
        "guide_tips": [
            f"{champion} excels in team fights with proper positioning",
            f"Build core items first, then adapt to enemy team composition",
            f"Master {champion}'s key abilities for maximum impact"
        ],
        "matchup_notes": {
            "strengths": [f"{champion} is strong against immobile champions"],
            "weaknesses": [f"{champion} struggles against high burst damage"]
        },
        "meta_info": {
            "patch": "16.2",
            "tier": "A",
            "notes": "Solid pick in current meta"
        }
    }

def main():
    logger.info("=== Starting LLM Text Data Scraper ===")
    logger.info(f"Log file: {log_file}")

    # Get champion list
    champions = get_champion_list()
    if not champions:
        logger.error("No champions found, exiting")
        return

    # Create output directory
    output_dir = Path("training_data")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "text_data.jsonl"

    # Scrape data for each champion
    scraped_count = 0
    failed_count = 0

    with open(output_file, 'w') as f:
        for champion in champions[:10]:  # Limit to 10 for now
            try:
                logger.info(f"Scraping {champion}...")
                data = scrape_champion_text_data(champion)
                f.write(json.dumps(data) + '\n')
                scraped_count += 1

            except Exception as e:
                logger.error(f"Failed to scrape {champion}: {e}")
                failed_count += 1

    logger.info(f"=== Scraping Complete ===")
    logger.info(f"Scraped: {scraped_count} champions")
    logger.info(f"Failed: {failed_count} champions")
    logger.info(f"Output: {output_file}")
    logger.info(f"Log: {log_file}")

if __name__ == "__main__":
    main()
