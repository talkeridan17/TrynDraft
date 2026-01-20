"""
Admin Endpoints for TrynDraft
Provides endpoints for manual scraping triggers and system status.
Designed for production with background task management.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session
from ....database import get_db
from ....models import Champion, ScrapedContent
from ....services.scheduler import get_scheduler
from ....services.stats_scraper import Rank
from ....services.stats_loader import StatsLoader
from ....services.web_scraper import WebScraper
from ....services.nn_trainer import NNTrainer, train_model, train_all_ranks, get_available_models
from ....services.progress_tracker import get_progress_tracker

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def get_system_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get comprehensive system status.

    Returns scheduler state, database stats, and scraping status.
    """
    scheduler = get_scheduler()

    # Count database records
    champion_count = db.query(Champion).count()
    scraped_content_count = db.query(ScrapedContent).count()

    # Get latest patch with data
    latest_champion = db.query(Champion).order_by(Champion.updated_at.desc()).first()
    latest_patch = latest_champion.patch if latest_champion else None
    latest_update = latest_champion.updated_at.isoformat() if latest_champion else None

    # Get scraper sources
    scraper_sources = db.query(ScrapedContent.source).distinct().all()
    sources = [s[0] for s in scraper_sources]

    # Get scheduler status
    scheduler_status = scheduler.get_status()

    # Get available scraped data
    loader = StatsLoader(db)
    available_patches = loader.get_available_patches()
    available_ranks = {}
    for patch in available_patches[:3]:  # Only show recent patches
        available_ranks[patch] = loader.get_available_ranks(patch)

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scheduler": scheduler_status,
        "database": {
            "champions": champion_count,
            "scraped_content": scraped_content_count,
            "sources": sources,
            "latest_patch": latest_patch,
            "latest_update": latest_update
        },
        "scraped_data": {
            "available_patches": available_patches,
            "ranks_per_patch": available_ranks
        }
    }


@router.post("/scrape/stats")
async def trigger_stats_scrape(
    ranks: Optional[List[str]] = Query(default=None, description="Ranks to scrape (e.g., CHALLENGER, DIAMOND)"),
    regions: Optional[List[str]] = Query(default=None, description="Regions to scrape (e.g., na1, euw1, kr)")
) -> Dict[str, Any]:
    """
    Trigger Riot API stats scraping in background.

    This starts a background scrape that collects champion statistics
    from the Riot API. Due to rate limits, this can take hours to complete.

    Args:
        ranks: List of ranks to scrape (default: CHALLENGER, DIAMOND)
        regions: List of regions to scrape (default: na1)

    The scrape runs in a background thread and saves data to:
    scraped_data/riot_stats/patch_X.X/{RANK}/champion_stats.json
    """
    scheduler = get_scheduler()

    result = scheduler.trigger_stats_scrape_async(
        ranks=ranks,
        regions=regions
    )

    return result


@router.post("/scrape/load")
async def load_scraped_stats(
    patch: Optional[str] = None,
    rank: Optional[str] = None
) -> Dict[str, Any]:
    """
    Load scraped stats from files into database.

    Call this after stats scraping completes to update the database
    with the scraped champion statistics.

    Args:
        patch: Specific patch to load (default: latest)
        rank: Specific rank to load (default: all available)
    """
    scheduler = get_scheduler()

    if rank:
        loader = StatsLoader()
        patches = loader.get_available_patches()
        if not patches:
            raise HTTPException(status_code=404, detail="No scraped data available")
        result = loader.update_database_from_rank(patch or patches[0], rank.upper())
        return {"status": "success", "result": result}
    else:
        result = scheduler.trigger_stats_load()
        return result


@router.post("/scrape/text")
async def trigger_text_scrape(
    background_tasks: BackgroundTasks,
    champion: str = None
) -> Dict[str, str]:
    """
    Trigger text content scraping for LLM training.

    Args:
        champion: Optional specific champion to scrape (if None, scrapes top champions)
    """
    if champion:
        background_tasks.add_task(_scrape_single_champion_text, champion)
        return {
            "status": "started",
            "message": f"Scraping text content for {champion} in background"
        }
    else:
        scheduler = get_scheduler()
        background_tasks.add_task(scheduler.trigger_text_scrape)
        return {
            "status": "started",
            "message": "Scraping text content in background"
        }


@router.post("/cleanup")
async def trigger_cleanup(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Manually trigger database cleanup."""
    scheduler = get_scheduler()
    background_tasks.add_task(scheduler.trigger_cleanup)
    return {
        "status": "started",
        "message": "Database cleanup started in background"
    }


@router.get("/scraped-data/patches")
async def get_available_patches() -> Dict[str, Any]:
    """Get list of available scraped data patches."""
    loader = StatsLoader()
    patches = loader.get_available_patches()

    result = {}
    for patch in patches:
        ranks = loader.get_available_ranks(patch)
        result[patch] = {
            "ranks": ranks,
            "rank_count": len(ranks)
        }

    return {
        "patches": patches,
        "details": result
    }


@router.get("/scraped-data/{patch}/{rank}")
async def get_scraped_rank_stats(
    patch: str,
    rank: str,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Get scraped stats for a specific patch and rank.

    This reads directly from the scraped JSON files.
    """
    loader = StatsLoader()
    stats = loader.load_rank_stats(patch, rank.upper())

    if not stats:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for patch {patch}, rank {rank}"
        )

    # Get top champions by games played
    champions = stats.get("champions", {})
    top_champions = sorted(
        champions.items(),
        key=lambda x: sum(r.get("games", 0) for r in x[1].get("roles", {}).values()),
        reverse=True
    )[:limit]

    return {
        "patch": patch,
        "rank": rank,
        "total_matches": stats.get("total_matches", 0),
        "total_champions": len(champions),
        "scraped_at": stats.get("scraped_at"),
        "top_champions": [
            {
                "name": name,
                "roles": data.get("roles", {}),
                "matchups_count": sum(len(m) for m in data.get("matchups", {}).values())
            }
            for name, data in top_champions
        ]
    }


@router.get("/champions/stats")
async def get_champion_stats_summary(
    db: Session = Depends(get_db),
    patch: str = None,
    limit: int = 20
) -> Dict[str, Any]:
    """Get summary of champion stats from database."""
    query = db.query(Champion)

    if patch:
        query = query.filter(Champion.patch == patch)

    champions = query.order_by(Champion.win_rate.desc()).limit(limit).all()

    return {
        "count": len(champions),
        "patch": patch,
        "champions": [
            {
                "name": c.name,
                "win_rate": c.win_rate / 100 if c.win_rate else None,
                "pick_rate": c.pick_rate / 100 if c.pick_rate else None,
                "ban_rate": c.ban_rate / 100 if c.ban_rate else None,
                "roles": c.roles,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None
            }
            for c in champions
        ]
    }


@router.get("/scraped-content")
async def get_scraped_content_summary(
    db: Session = Depends(get_db),
    source: str = None,
    champion: str = None,
    limit: int = 50
) -> Dict[str, Any]:
    """Get summary of scraped text content."""
    query = db.query(ScrapedContent)

    if source:
        query = query.filter(ScrapedContent.source == source)
    if champion:
        query = query.filter(ScrapedContent.champion == champion)

    content = query.order_by(ScrapedContent.created_at.desc()).limit(limit).all()

    return {
        "count": len(content),
        "filters": {"source": source, "champion": champion},
        "content": [
            {
                "id": c.id,
                "source": c.source,
                "champion": c.champion,
                "title": c.title,
                "content_preview": c.content[:200] + "..." if c.content and len(c.content) > 200 else c.content,
                "tags": c.tags,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in content
        ]
    }


@router.get("/ranks")
async def get_available_ranks() -> Dict[str, Any]:
    """Get list of available rank tiers for scraping."""
    return {
        "ranks": [r.value for r in Rank],
        "description": {
            "CHALLENGER": "Top ~300 players per region",
            "GRANDMASTER": "Top ~700 players per region",
            "MASTER": "Top tier below GM",
            "DIAMOND": "High elo",
            "EMERALD": "Upper mid elo",
            "PLATINUM": "Mid elo",
            "GOLD": "Average elo (most players)",
            "SILVER": "Below average",
            "BRONZE": "Low elo",
            "IRON": "Lowest tier"
        }
    }


# ========== Progress Tracking ==========

@router.get("/progress")
async def get_progress() -> Dict[str, Any]:
    """
    Get comprehensive progress status for all scrapers and models.

    Returns status for:
    - Stats scraping per rank
    - Text scraping for LLM fine-tuning
    - Model training status per rank

    Also available as plain text at /admin/progress/summary
    """
    tracker = get_progress_tracker()
    return tracker.get_status()


@router.get("/progress/summary")
async def get_progress_summary() -> str:
    """Get human-readable progress summary."""
    tracker = get_progress_tracker()
    return tracker.get_summary()


@router.get("/progress/stats/{rank}")
async def get_stats_progress(rank: str) -> Dict[str, Any]:
    """Get stats scraping progress for a specific rank."""
    tracker = get_progress_tracker()
    return tracker.get_stats_status(rank)


@router.get("/progress/models")
async def get_models_progress() -> Dict[str, Any]:
    """Get model training progress for all ranks."""
    tracker = get_progress_tracker()
    return tracker.get_model_status()


# ========== Neural Network Training Endpoints ==========

@router.get("/models")
async def get_nn_models() -> Dict[str, Any]:
    """Get list of available trained neural network models."""
    return get_available_models()


@router.post("/train")
async def trigger_training(
    background_tasks: BackgroundTasks,
    rank: Optional[str] = Query(default=None, description="Specific rank to train (e.g., DIAMOND)"),
    epochs: int = Query(default=50, description="Number of training epochs")
) -> Dict[str, Any]:
    """
    Trigger neural network training in background.

    Args:
        rank: Specific rank to train for (if None, trains combined model)
        epochs: Number of training epochs (default: 50)

    The trained model will be saved to:
    - models/{RANK}/draft_recommendation.pth for rank-specific
    - models/combined/draft_recommendation.pth for combined model
    """
    if rank:
        rank = rank.upper()
        if rank not in [r.value for r in Rank]:
            raise HTTPException(status_code=400, detail=f"Invalid rank: {rank}")

    background_tasks.add_task(_train_model_background, rank, epochs)

    return {
        "status": "started",
        "message": f"Training {'rank ' + rank if rank else 'combined'} model with {epochs} epochs",
        "rank": rank,
        "epochs": epochs
    }


@router.post("/train/all")
async def trigger_training_all_ranks(
    background_tasks: BackgroundTasks,
    epochs: int = Query(default=50, description="Number of training epochs per model")
) -> Dict[str, Any]:
    """
    Train models for all available ranks in background.

    This will train a separate model for each rank that has scraped data,
    plus a combined model using all data.
    """
    background_tasks.add_task(_train_all_models_background, epochs)

    loader = StatsLoader()
    patches = loader.get_available_patches()
    ranks = loader.get_available_ranks(patches[0]) if patches else []

    return {
        "status": "started",
        "message": f"Training models for {len(ranks)} ranks + combined",
        "ranks": ranks,
        "epochs": epochs
    }


# Background task functions
def _train_model_background(rank: str, epochs: int):
    """Background task to train a single model."""
    try:
        logger.info(f"Starting background training for {'rank ' + rank if rank else 'combined'}")
        result = train_model(epochs=epochs, rank=rank)
        logger.info(f"Training complete: {result}")
    except Exception as e:
        logger.error(f"Background training failed: {e}")


def _train_all_models_background(epochs: int):
    """Background task to train all rank models."""
    try:
        logger.info(f"Starting background training for all ranks")
        result = train_all_ranks(epochs=epochs)
        logger.info(f"Training all ranks complete: {result}")
    except Exception as e:
        logger.error(f"Background training all failed: {e}")


async def _scrape_single_champion_text(champion: str):
    """Background task to scrape single champion text content."""
    try:
        scraper = WebScraper()
        await scraper.initialize()

        content = []

        # Scrape MOBAFire
        mobafire_content = await scraper.scrape_mobafire_champion_guide(champion)
        content.extend(mobafire_content)

        # Scrape Reddit
        reddit_content = await scraper.scrape_champion_forum_posts(champion)
        content.extend(reddit_content)

        await scraper.close()

        # Save to database
        from ....database import SessionLocal
        db = SessionLocal()
        try:
            for item in content:
                scraped = ScrapedContent(
                    source=item.get('source', 'unknown'),
                    url=item.get('url', ''),
                    title=item.get('title', ''),
                    content=item.get('content', ''),
                    champion=item.get('champion'),
                    role=item.get('role'),
                    tags=item.get('tags', []),
                    quality_score=item.get('quality_score', 0)
                )
                db.add(scraped)

            db.commit()
            logger.info(f"Saved {len(content)} text items for {champion}")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Background text scrape failed for {champion}: {e}")
