#!/usr/bin/env python3
"""
Scrape training data from MOBAFire and LoLalytics for LLM fine-tuning.

This script collects textual data about champion strategies, builds, matchups,
and gameplay tips to prepare training data for fine-tuning an LLM (like Llama).

Usage:
    python scripts/scrape_training_data.py

Output:
    - training_data/scraped_data.json: Raw scraped content
    - training_data/prepared_data.jsonl: Formatted for fine-tuning
"""
import sys
import os
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.services.llm_service import LLMService
from app.models import Champion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def scrape_all_champions(limit: int = None) -> List[Dict]:
    """
    Scrape data for all champions from MOBAFire and LoLalytics.

    Args:
        limit: Optional limit on number of champions to scrape (for testing)

    Returns:
        List of scraped data dictionaries
    """
    db = SessionLocal()
    llm_service = LLMService()
    all_data = []

    try:
        # Get all champions from database
        champions = db.query(Champion).all()

        if limit:
            champions = champions[:limit]

        logger.info(f"Starting scraping for {len(champions)} champions...")

        for i, champion in enumerate(champions, 1):
            logger.info(f"[{i}/{len(champions)}] Scraping {champion.name}...")

            try:
                # Scrape data for this champion
                champ_data = await llm_service.scrape_champion_data(champion.name)

                if champ_data:
                    all_data.extend(champ_data)
                    logger.info(f"  ✓ Scraped {len(champ_data)} entries for {champion.name}")
                else:
                    logger.warning(f"  ✗ No data found for {champion.name}")

                # Rate limiting - be respectful to servers
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"  ✗ Error scraping {champion.name}: {e}")
                continue

        logger.info(f"\n✅ Scraping complete! Collected {len(all_data)} total entries")
        return all_data

    finally:
        db.close()


def save_scraped_data(data: List[Dict], output_dir: str = "training_data"):
    """Save scraped data to JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "scraped_data.json")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"💾 Saved scraped data to {output_path}")
    logger.info(f"   Total entries: {len(data)}")
    logger.info(f"   File size: {os.path.getsize(output_path) / 1024:.1f} KB")


def prepare_training_data(scraped_data: List[Dict], output_dir: str = "training_data"):
    """
    Prepare scraped data for LLM fine-tuning.

    Converts raw scraped data into prompt-completion pairs suitable for
    fine-tuning models like Llama, GPT, or Mistral.
    """
    llm_service = LLMService()
    training_data = llm_service.prepare_training_data(scraped_data)

    # Save in JSONL format (one JSON object per line) for fine-tuning
    output_path = os.path.join(output_dir, "prepared_data.jsonl")

    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in training_data:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    logger.info(f"📝 Prepared training data saved to {output_path}")
    logger.info(f"   Training examples: {len(training_data)}")
    logger.info(f"   Ready for fine-tuning!")


async def main():
    """Main execution flow."""
    print("=" * 60)
    print("TrynDraft LLM Training Data Scraper")
    print("=" * 60)
    print()

    # Check if we should run in test mode
    import sys
    test_mode = '--test' in sys.argv
    limit = 5 if test_mode else None

    if test_mode:
        logger.info("🧪 Running in TEST MODE - scraping only 5 champions")
    else:
        logger.info("🚀 Running in FULL MODE - scraping all champions")

    print()

    # Step 1: Scrape data
    logger.info("Step 1: Scraping champion data from MOBAFire and LoLalytics...")
    scraped_data = await scrape_all_champions(limit=limit)

    if not scraped_data:
        logger.error("❌ No data scraped. Check your internet connection and try again.")
        return

    print()

    # Step 2: Save raw data
    logger.info("Step 2: Saving raw scraped data...")
    save_scraped_data(scraped_data)

    print()

    # Step 3: Prepare training data
    logger.info("Step 3: Preparing data for fine-tuning...")
    prepare_training_data(scraped_data)

    print()
    print("=" * 60)
    print("✅ SUCCESS!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Review training_data/prepared_data.jsonl")
    print("  2. Upload to HuggingFace or your fine-tuning platform")
    print("  3. Fine-tune Llama or Mistral model on this data")
    print("  4. Update FINE_TUNED_MODEL_ID in your .env file")
    print()
    print("Fine-tuning resources:")
    print("  - HuggingFace: https://huggingface.co/docs/transformers/training")
    print("  - Llama fine-tuning: https://github.com/facebookresearch/llama-recipes")
    print()


if __name__ == "__main__":
    asyncio.run(main())
