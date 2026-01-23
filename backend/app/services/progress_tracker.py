"""
Unified Progress Tracker for TrynDraft
Tracks progress of:
- Stats scraping (per rank)
- Text scraping for LLM fine-tuning
- Model training status (per rank)
- Last update times

Logs are stored in: backend/logs/progress.json
"""
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from threading import Lock

logger = logging.getLogger(__name__)

# Valid ranks
RANKS = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM",
         "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]


class ProgressTracker:
    """
    Singleton tracker for all background jobs.

    Usage:
        tracker = get_progress_tracker()
        tracker.update_stats_scrape("DIAMOND", matches_processed=50, total_matches=100)
        tracker.update_model_training("DIAMOND", status="completed", val_loss=0.005)

        status = tracker.get_status()
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Use root-level logs directory (not backend/logs)
        # This makes logs easily accessible from project root
        backend_dir = Path(__file__).parent.parent.parent  # backend/app/services -> backend
        project_root = backend_dir.parent  # backend -> project root
        self.logs_dir = project_root / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        self.progress_file = self.logs_dir / "progress.json"
        self.log_file = self.logs_dir / "scraper.log"
        self.stats_log_file = self.logs_dir / "stats_scraper.log"
        self.text_log_file = self.logs_dir / "text_scraper.log"

        # Configure file loggers
        self._setup_file_logger()

        # Load existing progress or create new
        self.progress = self._load_progress()
        self._initialized = True

    def _setup_file_logger(self):
        """Set up file logging for scrapers with separate log files."""
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # General scraper log
        general_handler = logging.FileHandler(self.log_file)
        general_handler.setLevel(logging.INFO)
        general_handler.setFormatter(formatter)

        # Stats scraper log
        stats_handler = logging.FileHandler(self.stats_log_file)
        stats_handler.setLevel(logging.INFO)
        stats_handler.setFormatter(formatter)

        # Text scraper log
        text_handler = logging.FileHandler(self.text_log_file)
        text_handler.setLevel(logging.INFO)
        text_handler.setFormatter(formatter)

        # Add handlers to appropriate loggers
        scraper_logger = logging.getLogger('app.services')
        scraper_logger.addHandler(general_handler)

        stats_logger = logging.getLogger('app.services.stats_scraper')
        stats_logger.addHandler(stats_handler)

        text_logger = logging.getLogger('app.services.text_scraper')
        text_logger.addHandler(text_handler)

    def _load_progress(self) -> Dict:
        """Load progress from file or return default structure."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load progress file: {e}")

        # Default structure
        return {
            "stats_scraping": {rank: self._default_scrape_status() for rank in RANKS},
            "text_scraping": self._default_text_scrape_status(),
            "model_training": {rank: self._default_model_status() for rank in RANKS},
            "combined_model": self._default_model_status(),
            "last_updated": datetime.now().isoformat()
        }

    def _default_scrape_status(self) -> Dict:
        return {
            "status": "not_started",  # not_started, running, completed, error
            "matches_processed": 0,
            "total_matches": 0,
            "champions_with_data": 0,
            "last_run": None,
            "last_error": None,
            "patch": None
        }

    def _default_text_scrape_status(self) -> Dict:
        return {
            "status": "not_started",
            "champions_scraped": 0,
            "total_champions": 0,
            "reddit_posts": 0,
            "mobafire_guides": 0,
            "training_examples": 0,
            "last_run": None,
            "last_error": None
        }

    def _default_model_status(self) -> Dict:
        return {
            "status": "not_trained",  # not_trained, training, completed, error
            "trained_at": None,
            "epochs": 0,
            "val_loss": None,
            "input_size": None,
            "patch": None,
            "model_path": None
        }

    def _save_progress(self):
        """Save progress to file."""
        self.progress["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(self.progress, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")

    # ========== Stats Scraping ==========

    def update_stats_scrape(
        self,
        rank: str,
        status: str = None,
        matches_processed: int = None,
        total_matches: int = None,
        champions_with_data: int = None,
        patch: str = None,
        error: str = None
    ):
        """Update stats scraping progress for a rank."""
        rank = rank.upper()
        if rank not in RANKS:
            logger.warning(f"Unknown rank: {rank}")
            return

        scrape = self.progress["stats_scraping"][rank]

        if status:
            scrape["status"] = status
        if matches_processed is not None:
            scrape["matches_processed"] = matches_processed
        if total_matches is not None:
            scrape["total_matches"] = total_matches
        if champions_with_data is not None:
            scrape["champions_with_data"] = champions_with_data
        if patch:
            scrape["patch"] = patch
        if error:
            scrape["last_error"] = error
            scrape["status"] = "error"

        if status in ["running", "completed"]:
            scrape["last_run"] = datetime.now().isoformat()

        self._save_progress()

        # Log to file
        logger.info(f"Stats scrape [{rank}]: {status or scrape['status']} - "
                   f"{scrape['matches_processed']}/{scrape['total_matches']} matches")

    def start_stats_scrape(self, rank: str, total_matches: int = 0, patch: str = None):
        """Mark stats scraping as started for a rank."""
        self.update_stats_scrape(rank, status="running", matches_processed=0,
                                 total_matches=total_matches, patch=patch)

    def complete_stats_scrape(self, rank: str, champions_with_data: int = 0):
        """Mark stats scraping as completed for a rank."""
        self.update_stats_scrape(rank, status="completed",
                                 champions_with_data=champions_with_data)

    # ========== Text Scraping ==========

    def update_text_scrape(
        self,
        status: str = None,
        champions_scraped: int = None,
        total_champions: int = None,
        reddit_posts: int = None,
        mobafire_guides: int = None,
        training_examples: int = None,
        error: str = None
    ):
        """Update text scraping progress."""
        scrape = self.progress["text_scraping"]

        if status:
            scrape["status"] = status
        if champions_scraped is not None:
            scrape["champions_scraped"] = champions_scraped
        if total_champions is not None:
            scrape["total_champions"] = total_champions
        if reddit_posts is not None:
            scrape["reddit_posts"] = reddit_posts
        if mobafire_guides is not None:
            scrape["mobafire_guides"] = mobafire_guides
        if training_examples is not None:
            scrape["training_examples"] = training_examples
        if error:
            scrape["last_error"] = error
            scrape["status"] = "error"

        if status in ["running", "completed"]:
            scrape["last_run"] = datetime.now().isoformat()

        self._save_progress()

        logger.info(f"Text scrape: {status or scrape['status']} - "
                   f"{scrape['champions_scraped']}/{scrape['total_champions']} champions, "
                   f"{scrape['training_examples']} training examples")

    def start_text_scrape(self, total_champions: int):
        """Mark text scraping as started."""
        self.update_text_scrape(status="running", champions_scraped=0,
                               total_champions=total_champions)

    def complete_text_scrape(self, training_examples: int):
        """Mark text scraping as completed."""
        self.update_text_scrape(status="completed", training_examples=training_examples)

    # ========== Model Training ==========

    def update_model_training(
        self,
        rank: str = None,  # None for combined model
        status: str = None,
        epochs: int = None,
        val_loss: float = None,
        input_size: int = None,
        patch: str = None,
        model_path: str = None,
        error: str = None
    ):
        """Update model training status."""
        if rank:
            rank = rank.upper()
            if rank not in RANKS:
                logger.warning(f"Unknown rank: {rank}")
                return
            model = self.progress["model_training"][rank]
        else:
            model = self.progress["combined_model"]

        if status:
            model["status"] = status
        if epochs is not None:
            model["epochs"] = epochs
        if val_loss is not None:
            model["val_loss"] = val_loss
        if input_size is not None:
            model["input_size"] = input_size
        if patch:
            model["patch"] = patch
        if model_path:
            model["model_path"] = model_path
        if error:
            model["last_error"] = error
            model["status"] = "error"

        if status == "completed":
            model["trained_at"] = datetime.now().isoformat()

        self._save_progress()

        rank_str = rank or "combined"
        logger.info(f"Model [{rank_str}]: {status or model['status']} - "
                   f"epochs={model['epochs']}, val_loss={model['val_loss']}")

    def start_training(self, rank: str = None, epochs: int = 0):
        """Mark model training as started."""
        self.update_model_training(rank, status="training", epochs=epochs)

    def complete_training(self, rank: str = None, val_loss: float = None, model_path: str = None):
        """Mark model training as completed."""
        self.update_model_training(rank, status="completed", val_loss=val_loss,
                                  model_path=model_path)

    # ========== Status Queries ==========

    def get_status(self) -> Dict:
        """Get full progress status."""
        # Reload from file to get latest
        self.progress = self._load_progress()
        return self.progress

    def get_stats_status(self, rank: str = None) -> Dict:
        """Get stats scraping status for a rank or all ranks."""
        if rank:
            rank = rank.upper()
            return self.progress["stats_scraping"].get(rank, {})
        return self.progress["stats_scraping"]

    def get_text_status(self) -> Dict:
        """Get text scraping status."""
        return self.progress["text_scraping"]

    def get_model_status(self, rank: str = None) -> Dict:
        """Get model training status."""
        if rank:
            rank = rank.upper()
            return self.progress["model_training"].get(rank, {})
        return {
            "per_rank": self.progress["model_training"],
            "combined": self.progress["combined_model"]
        }

    def get_summary(self) -> str:
        """Get human-readable summary."""
        lines = ["=== TrynDraft Progress Summary ===", ""]

        # Stats scraping
        lines.append("📊 Stats Scraping:")
        for rank in RANKS:
            s = self.progress["stats_scraping"][rank]
            status_emoji = {"running": "🔄", "completed": "✅", "error": "❌"}.get(s["status"], "⏸️")
            if s["status"] != "not_started":
                lines.append(f"  {status_emoji} {rank}: {s['matches_processed']}/{s['total_matches']} matches "
                           f"({s['champions_with_data']} champs) - {s['last_run'] or 'never'}")

        # Text scraping
        lines.append("")
        lines.append("📝 Text Scraping (LLM):")
        t = self.progress["text_scraping"]
        status_emoji = {"running": "🔄", "completed": "✅", "error": "❌"}.get(t["status"], "⏸️")
        lines.append(f"  {status_emoji} {t['champions_scraped']}/{t['total_champions']} champions, "
                    f"{t['training_examples']} examples - {t['last_run'] or 'never'}")

        # Models
        lines.append("")
        lines.append("🧠 Trained Models:")
        for rank in RANKS:
            m = self.progress["model_training"][rank]
            if m["status"] != "not_trained":
                status_emoji = {"training": "🔄", "completed": "✅", "error": "❌"}.get(m["status"], "⏸️")
                val_loss_str = f"{m['val_loss']:.4f}" if m['val_loss'] else 'N/A'
                lines.append(f"  {status_emoji} {rank}: val_loss={val_loss_str} "
                           f"- {m['trained_at'] or 'never'}")

        m = self.progress["combined_model"]
        if m["status"] != "not_trained":
            status_emoji = {"training": "🔄", "completed": "✅", "error": "❌"}.get(m["status"], "⏸️")
            val_loss_str = f"{m['val_loss']:.4f}" if m['val_loss'] else 'N/A'
            lines.append(f"  {status_emoji} COMBINED: val_loss={val_loss_str} "
                       f"- {m['trained_at'] or 'never'}")

        lines.append("")
        lines.append(f"Last updated: {self.progress['last_updated']}")

        return "\n".join(lines)


# Singleton accessor
_tracker_instance = None

def get_progress_tracker() -> ProgressTracker:
    """Get the singleton progress tracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ProgressTracker()
    return _tracker_instance
