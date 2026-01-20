#!/usr/bin/env python3
"""
Comprehensive LLM Training Data Scraper for TrynDraft.

Scrapes real content from:
1. Reddit (r/summonerschool, r/leagueoflegends) - discussions, tips, champion advice
2. MOBAFire - guide content (what's available without JS rendering)

Output: JSONL files ready for fine-tuning
"""
import sys
import os
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Champion
from app.services.web_scraper import WebScraper
from app.services.progress_tracker import get_progress_tracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LLMTrainingDataScraper:
    """Scrape real content for LLM fine-tuning."""

    def __init__(self, output_dir: str = "training_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.scraper = WebScraper()

    async def scrape_reddit_champion_advice(self, champions: List[str], limit_per_champ: int = 5) -> List[Dict]:
        """Scrape Reddit posts about specific champions from r/summonerschool."""
        all_content = []

        await self.scraper.initialize()

        for champ in champions:
            logger.info(f"Scraping Reddit advice for {champ}...")
            try:
                posts = await self.scraper.scrape_champion_forum_posts(champ)
                # Filter to only substantial posts
                good_posts = [p for p in posts if len(p.get('content', '')) > 200][:limit_per_champ]
                all_content.extend(good_posts)
                logger.info(f"  Found {len(good_posts)} posts for {champ}")
                await asyncio.sleep(2)  # Rate limiting
            except Exception as e:
                logger.error(f"  Failed for {champ}: {e}")

        await self.scraper.close()
        return all_content

    async def scrape_reddit_general_advice(self) -> List[Dict]:
        """Scrape general League advice from r/summonerschool."""
        content = []

        await self.scraper.initialize()

        # Get posts from subreddit
        topics = [
            "how to improve",
            "climbing tips",
            "macro guide",
            "wave management",
            "jungle pathing",
            "trading stance",
            "team fighting",
            "draft strategy",
            "counter pick",
            "lane matchup"
        ]

        for topic in topics:
            logger.info(f"Scraping Reddit for: {topic}")
            try:
                search_url = f"https://www.reddit.com/r/summonerschool/search.json?q={topic.replace(' ', '+')}&restrict_sr=on&sort=top&t=year"

                async with self.scraper.session.get(search_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        posts = data.get('data', {}).get('children', [])

                        for post in posts[:5]:  # Top 5 per topic
                            post_data = post['data']
                            post_text = f"{post_data.get('title', '')}\n\n{post_data.get('selftext', '')}"

                            if len(post_text) > 300:  # Substantial content
                                content.append({
                                    'source': 'reddit_general',
                                    'topic': topic,
                                    'url': f"https://reddit.com{post_data.get('permalink', '')}",
                                    'content': post_text[:3000],  # Limit length
                                    'type': 'general_advice',
                                    'score': post_data.get('score', 0),
                                    'created_at': datetime.now().isoformat()
                                })

                        logger.info(f"  Found {len([c for c in content if c.get('topic') == topic])} posts")

                await asyncio.sleep(2)  # Rate limiting

            except Exception as e:
                logger.error(f"  Failed for topic '{topic}': {e}")

        await self.scraper.close()
        return content

    async def scrape_mobafire_guides(self, champions: List[str]) -> List[Dict]:
        """Scrape MOBAFire guide pages."""
        content = []

        await self.scraper.initialize()

        for champ in champions:
            logger.info(f"Scraping MOBAFire for {champ}...")
            try:
                guide_content = await self.scraper.scrape_mobafire_champion_guide(champ)
                # Only keep chunks with actual content
                useful = [c for c in guide_content if len(c.get('content', '')) > 100]
                content.extend(useful)
                logger.info(f"  Found {len(useful)} content chunks for {champ}")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"  Failed for {champ}: {e}")

        await self.scraper.close()
        return content

    def prepare_for_finetuning(self, scraped_data: List[Dict]) -> List[Dict]:
        """
        Convert scraped data to instruction-following format for fine-tuning.

        This creates realistic prompts and completions based on actual scraped content.
        """
        training_examples = []

        for item in scraped_data:
            source = item.get('source', '')
            content = item.get('content', '')
            champion = item.get('champion', '')
            topic = item.get('topic', '')

            if len(content) < 100:
                continue

            # Create instruction-following format
            if source == 'reddit_champion' and champion:
                # Champion-specific advice
                instruction = f"What are some tips for playing {champion} in League of Legends?"
                response = f"Here's advice for {champion}:\n\n{content}"

            elif source == 'reddit_general' and topic:
                # General gameplay advice
                instruction = f"Give me advice about {topic} in League of Legends."
                response = f"Here's what you should know about {topic}:\n\n{content}"

            elif source == 'mobafire' and champion:
                # Build/guide info
                instruction = f"Tell me about {champion}'s build and playstyle."
                response = f"{champion} guide info:\n\n{content}"

            else:
                continue

            # Create training example in chat format
            training_examples.append({
                "messages": [
                    {"role": "user", "content": instruction},
                    {"role": "assistant", "content": response[:2000]}  # Limit response length
                ]
            })

            # Also create the old format for compatibility
            training_examples.append({
                "prompt": instruction,
                "completion": response[:2000]
            })

        return training_examples

    def save_training_data(self, training_data: List[Dict], filename: str = "training_data.jsonl"):
        """Save training data in JSONL format."""
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            for item in training_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        logger.info(f"Saved {len(training_data)} training examples to {filepath}")
        return filepath

    def save_raw_data(self, data: List[Dict], filename: str = "raw_scraped.json"):
        """Save raw scraped data."""
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(data)} raw items to {filepath}")
        return filepath


async def main():
    """Main scraping flow."""
    print("=" * 60)
    print("TrynDraft LLM Training Data Scraper")
    print("=" * 60)
    print()

    # Parse args
    test_mode = '--test' in sys.argv
    skip_reddit = '--skip-reddit' in sys.argv

    # Initialize progress tracker
    tracker = get_progress_tracker()

    # Get champions from database
    db = SessionLocal()
    all_champions = [c.name for c in db.query(Champion).all()]
    db.close()

    # In test mode, only use 5 champions
    if test_mode:
        champions = all_champions[:5]
        logger.info(f"TEST MODE: Using {len(champions)} champions")
    else:
        champions = all_champions[:50]  # Limit to 50 for reasonable scraping time
        logger.info(f"Scraping data for {len(champions)} champions")

    # Start tracking
    tracker.start_text_scrape(total_champions=len(champions))

    scraper = LLMTrainingDataScraper()
    all_data = []

    try:
        reddit_posts = 0
        mobafire_guides = 0
        champions_scraped = 0

        # 1. Scrape Reddit general advice
        if not skip_reddit:
            logger.info("\n=== Scraping Reddit General Advice ===")
            general_advice = await scraper.scrape_reddit_general_advice()
            all_data.extend(general_advice)
            reddit_posts += len(general_advice)
            logger.info(f"Collected {len(general_advice)} general advice posts")
            tracker.update_text_scrape(reddit_posts=reddit_posts)

            # 2. Scrape Reddit champion-specific advice
            logger.info("\n=== Scraping Reddit Champion Advice ===")
            champ_advice = await scraper.scrape_reddit_champion_advice(champions, limit_per_champ=3)
            all_data.extend(champ_advice)
            reddit_posts += len(champ_advice)
            champions_scraped = len(set(p.get('champion') for p in champ_advice if p.get('champion')))
            logger.info(f"Collected {len(champ_advice)} champion-specific posts")
            tracker.update_text_scrape(reddit_posts=reddit_posts, champions_scraped=champions_scraped)

        # 3. Scrape MOBAFire guides
        logger.info("\n=== Scraping MOBAFire Guides ===")
        mobafire_data = await scraper.scrape_mobafire_guides(champions[:20] if not test_mode else champions)
        all_data.extend(mobafire_data)
        mobafire_guides = len(mobafire_data)
        champions_scraped = len(set(p.get('champion') for p in all_data if p.get('champion')))
        logger.info(f"Collected {len(mobafire_data)} MOBAFire chunks")
        tracker.update_text_scrape(mobafire_guides=mobafire_guides, champions_scraped=champions_scraped)

        if not all_data:
            logger.error("No data collected! Check network connection.")
            tracker.update_text_scrape(error="No data collected")
            return

        # Save raw data
        logger.info("\n=== Saving Raw Data ===")
        scraper.save_raw_data(all_data)

        # Prepare and save training data
        logger.info("\n=== Preparing Training Data ===")
        training_data = scraper.prepare_for_finetuning(all_data)
        scraper.save_training_data(training_data)

        # Update tracker with completion
        tracker.complete_text_scrape(training_examples=len(training_data))

        print()
        print("=" * 60)
        print("SCRAPING COMPLETE")
        print("=" * 60)
        print(f"Total raw items: {len(all_data)}")
        print(f"Training examples: {len(training_data)}")
        print(f"Output directory: {scraper.output_dir}")
        print()
        print("Next steps:")
        print("1. Review training_data/training_data.jsonl")
        print("2. Upload to HuggingFace for fine-tuning")
        print("3. Or use local fine-tuning with unsloth/llama.cpp")
        print()

    except Exception as e:
        logger.error(f"Text scraping failed: {e}")
        tracker.update_text_scrape(error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
