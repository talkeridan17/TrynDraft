"""
Scheduler Service for Automated Tasks
Handles periodic scraping of champion stats and text data.
Uses APScheduler for cross-platform scheduling.

Designed to run in background on deployment:
- Stats scraping runs daily using Riot API
- Text scraping runs weekly for LLM training data
- Database cleanup runs monthly
"""
import logging
import asyncio
import threading
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Champion, ScrapedContent
from .stats_scraper import RiotStatsScraper, Rank
from .stats_loader import StatsLoader
from .web_scraper import WebScraper
from ..core.config import settings

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Manages scheduled background tasks for TrynDraft.

    Scheduled jobs:
    1. Stats scraping via Riot API (daily, runs in background thread)
    2. Text content scraping (weekly)
    3. Stats loading to database (after each scrape)
    4. Database cleanup (monthly)
    """

    def __init__(self):
        # Use background scheduler for long-running sync tasks (Riot API scraper)
        self.bg_scheduler = BackgroundScheduler()
        # Use async scheduler for quick async tasks
        self.async_scheduler = AsyncIOScheduler()
        self.is_running = False
        self._scrape_thread: Optional[threading.Thread] = None
        self._executor = ThreadPoolExecutor(max_workers=2)

    def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        # Add background jobs (long-running, runs in separate thread)
        self._add_stats_scraping_job()

        # Add async jobs
        self._add_text_scraping_job()
        self._add_cleanup_job()
        self._add_stats_loading_job()

        self.bg_scheduler.start()
        self.async_scheduler.start()
        self.is_running = True
        logger.info("Scheduler started with jobs: riot_stats_scrape, text_scrape, stats_load, cleanup")

    def stop(self):
        """Stop the scheduler."""
        if self.is_running:
            self.bg_scheduler.shutdown(wait=False)
            self.async_scheduler.shutdown(wait=False)
            self._executor.shutdown(wait=False)
            self.is_running = False
            logger.info("Scheduler stopped")

    def _add_stats_scraping_job(self):
        """
        Add daily Riot API stats scraping job.
        Runs in background thread because it takes hours due to rate limits.
        """
        # Run at 6 AM UTC daily
        self.bg_scheduler.add_job(
            self._run_riot_stats_scrape,
            CronTrigger(hour=6, minute=0),
            id='riot_stats_scrape',
            name='Riot API Stats Scraping',
            replace_existing=True,
            max_instances=1,  # Only one scrape at a time
            misfire_grace_time=3600  # Allow 1 hour grace period
        )
        logger.info("Added Riot stats scraping job (daily at 6 AM UTC)")

    def _add_stats_loading_job(self):
        """Add job to load scraped stats into database."""
        # Run at 8 AM UTC (2 hours after scrape starts, should have some data)
        self.async_scheduler.add_job(
            self._load_stats_to_db,
            CronTrigger(hour=8, minute=0),
            id='stats_load',
            name='Load Stats to Database',
            replace_existing=True,
            max_instances=1
        )
        logger.info("Added stats loading job (daily at 8 AM UTC)")

    def _add_text_scraping_job(self):
        """Add weekly text content scraping job."""
        # Run every Sunday at 3 AM UTC
        self.async_scheduler.add_job(
            self._run_text_scrape,
            CronTrigger(day_of_week='sun', hour=3, minute=0),
            id='text_scrape',
            name='Text Content Scraping',
            replace_existing=True,
            max_instances=1
        )
        logger.info("Added text scraping job (weekly on Sunday at 3 AM UTC)")

    def _add_cleanup_job(self):
        """Add monthly database cleanup job."""
        # Run on the 1st of each month at 2 AM UTC
        self.async_scheduler.add_job(
            self._run_cleanup,
            CronTrigger(day=1, hour=2, minute=0),
            id='cleanup',
            name='Database Cleanup',
            replace_existing=True,
            max_instances=1
        )
        logger.info("Added cleanup job (monthly on 1st at 2 AM UTC)")

    def _run_riot_stats_scrape(self):
        """
        Execute Riot API stats scraping.
        This runs in a background thread because it can take hours.
        """
        logger.info("Starting scheduled Riot API stats scrape (background)")
        start_time = datetime.now(timezone.utc)

        try:
            # Run scraper synchronously (it handles its own rate limiting)
            scraper = RiotStatsScraper()

            # Default: scrape high elo for faster results
            # Full scrape of all ranks takes much longer
            result = scraper.run(
                ranks=[Rank.CHALLENGER, Rank.GRANDMASTER, Rank.MASTER, Rank.DIAMOND, Rank.EMERALD, Rank.PLATINUM],
                regions=["na1", "euw1", "kr"],
                save_interval=50
            )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds() / 60
            logger.info(f"Riot stats scrape completed in {duration:.1f} minutes")
            logger.info(f"Results: {result}")

        except Exception as e:
            logger.error(f"Riot stats scrape failed: {e}", exc_info=True)

    async def _load_stats_to_db(self):
        """Load scraped stats from files into database."""
        logger.info("Loading scraped stats into database")

        try:
            loader = StatsLoader()
            result = loader.load_all_ranks()
            logger.info(f"Stats loading complete: {result}")
        except Exception as e:
            logger.error(f"Stats loading failed: {e}")

    async def _run_text_scrape(self):
        """Execute text content scraping for LLM training."""
        logger.info("Starting scheduled text scrape")
        start_time = datetime.now(timezone.utc)

        try:
            scraper = WebScraper()
            await scraper.initialize()

            # Get champion list from database
            db = SessionLocal()
            try:
                champions = db.query(Champion.name).distinct().limit(50).all()
                champion_names = [c[0] for c in champions]
            finally:
                db.close()

            # Scrape text for champions
            all_content = []
            for champion in champion_names:
                try:
                    content = await scraper.scrape_mobafire_champion_guide(champion)
                    all_content.extend(content)

                    reddit_content = await scraper.scrape_champion_forum_posts(champion)
                    all_content.extend(reddit_content)

                    await asyncio.sleep(2)  # Rate limiting
                except Exception as e:
                    logger.warning(f"Failed to scrape text for {champion}: {e}")
                    continue

            await scraper.close()

            # Save to database
            await self._save_text_to_db(all_content)

            # Save to file backup
            scraper.save_scraped_data(all_content)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"Text scrape completed in {duration:.1f}s - {len(all_content)} items")

        except Exception as e:
            logger.error(f"Text scrape failed: {e}")

    async def _run_cleanup(self):
        """Clean up old data from database."""
        logger.info("Starting scheduled cleanup")

        try:
            db = SessionLocal()
            try:
                # Keep only last 3 patches worth of champion data
                patches = db.query(Champion.patch).distinct().order_by(Champion.patch.desc()).all()

                if len(patches) > 3:
                    old_patches = [p[0] for p in patches[3:]]
                    deleted = db.query(Champion).filter(
                        Champion.patch.in_(old_patches)
                    ).delete(synchronize_session=False)
                    db.commit()
                    logger.info(f"Cleaned up {deleted} old champion entries")

                # Keep only last 1000 scraped content items per source
                for source in ['mobafire', 'lolalytics', 'reddit']:
                    count = db.query(ScrapedContent).filter(
                        ScrapedContent.source == source
                    ).count()

                    if count > 1000:
                        old_ids = db.query(ScrapedContent.id).filter(
                            ScrapedContent.source == source
                        ).order_by(ScrapedContent.created_at.asc()).limit(count - 1000).all()

                        if old_ids:
                            db.query(ScrapedContent).filter(
                                ScrapedContent.id.in_([i[0] for i in old_ids])
                            ).delete(synchronize_session=False)
                            db.commit()
                            logger.info(f"Cleaned up {len(old_ids)} old {source} entries")

            finally:
                db.close()

            # Clean up old scraped data files
            scraped_dir = Path("scraped_data/riot_stats")
            if scraped_dir.exists():
                patch_dirs = sorted(scraped_dir.iterdir(), reverse=True)
                # Keep only last 3 patch directories
                for old_dir in patch_dirs[3:]:
                    if old_dir.is_dir():
                        import shutil
                        shutil.rmtree(old_dir)
                        logger.info(f"Removed old scrape directory: {old_dir}")

            logger.info("Cleanup completed")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    async def _save_text_to_db(self, content: List[dict]):
        """Save scraped text content to database."""
        db = SessionLocal()
        try:
            saved_count = 0
            for item in content:
                existing = db.query(ScrapedContent).filter(
                    ScrapedContent.url == item.get('url')
                ).first()

                if existing:
                    existing.content = item.get('content', '')
                    existing.created_at = datetime.now(timezone.utc)
                else:
                    scraped = ScrapedContent(
                        source=item.get('source', 'unknown'),
                        url=item.get('url', ''),
                        title=item.get('title', ''),
                        content=item.get('content', ''),
                        champion=item.get('champion'),
                        role=item.get('role'),
                        tags=item.get('tags', []),
                        patch_version=item.get('patch'),
                        quality_score=item.get('quality_score', 0)
                    )
                    db.add(scraped)

                saved_count += 1

            db.commit()
            logger.info(f"Saved {saved_count} text items to database")

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save text to database: {e}")
        finally:
            db.close()

    # Manual trigger methods for admin API
    def trigger_stats_scrape_async(self, ranks: List[str] = None, regions: List[str] = None) -> Dict[str, Any]:
        """
        Trigger stats scraping in background.
        Returns immediately, scraping continues in background thread.
        """
        if self._scrape_thread and self._scrape_thread.is_alive():
            return {"status": "error", "message": "Scrape already in progress"}

        def run_scrape():
            try:
                scraper = RiotStatsScraper()
                rank_enums = [Rank[r.upper()] for r in (ranks or ["CHALLENGER", "DIAMOND"])]
                result = scraper.run(
                    ranks=rank_enums,
                    regions=regions or ["na1"],
                    save_interval=20
                )
                logger.info(f"Manual scrape completed: {result}")
            except Exception as e:
                logger.error(f"Manual scrape failed: {e}")

        self._scrape_thread = threading.Thread(target=run_scrape, daemon=True)
        self._scrape_thread.start()

        return {
            "status": "started",
            "message": f"Stats scraping started in background for ranks: {ranks or ['CHALLENGER', 'DIAMOND']}"
        }

    def trigger_stats_load(self) -> Dict[str, Any]:
        """Trigger loading stats from files to database."""
        try:
            loader = StatsLoader()
            result = loader.load_all_ranks()
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def trigger_text_scrape(self):
        """Manually trigger text scraping."""
        logger.info("Manually triggering text scrape")
        await self._run_text_scrape()

    async def trigger_cleanup(self):
        """Manually trigger cleanup."""
        logger.info("Manually triggering cleanup")
        await self._run_cleanup()

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        status = {
            "is_running": self.is_running,
            "scrape_in_progress": self._scrape_thread is not None and self._scrape_thread.is_alive(),
            "jobs": []
        }

        if self.is_running:
            for job in self.bg_scheduler.get_jobs():
                status["jobs"].append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": str(job.next_run_time) if job.next_run_time else None
                })
            for job in self.async_scheduler.get_jobs():
                status["jobs"].append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": str(job.next_run_time) if job.next_run_time else None
                })

        return status


# Global scheduler instance
_scheduler: Optional[SchedulerService] = None


def get_scheduler() -> SchedulerService:
    """Get global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerService()
    return _scheduler


def start_scheduler():
    """Start the global scheduler."""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """Stop the global scheduler."""
    scheduler = get_scheduler()
    scheduler.stop()
