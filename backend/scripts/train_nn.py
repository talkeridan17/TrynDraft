#!/usr/bin/env python3
"""
Neural Network Training CLI for TrynDraft

Usage:
    python train_nn.py                    # Train combined model
    python train_nn.py --rank DIAMOND     # Train single rank model
    python train_nn.py --all              # Train all available ranks
    python train_nn.py --status           # Check training status
    python train_nn.py --retrain-on-patch # Retrain when new patch detected

Examples:
    python train_nn.py --rank PLATINUM --epochs 100
    python train_nn.py --all --epochs 50
    python train_nn.py --retrain-on-patch
"""
import sys
import os
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.nn_trainer import (
    NNTrainer, train_model, train_all_ranks, get_available_models
)
from app.services.stats_loader import StatsLoader
from app.services.progress_tracker import get_progress_tracker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent.parent.parent / 'logs' / 'training' / 'nn_training.log')
    ]
)
logger = logging.getLogger(__name__)


def print_status():
    """Print current training and data status."""
    print("\n" + "=" * 60)
    print("TrynDraft NN Training Status")
    print("=" * 60)

    # Check scraped data
    loader = StatsLoader()
    patches = loader.get_available_patches()

    if patches:
        print(f"\n📊 Available Scraped Data:")
        for patch in patches[:3]:  # Show last 3 patches
            ranks = loader.get_available_ranks(patch)
            print(f"   Patch {patch}: {len(ranks)} ranks ({', '.join(ranks[:5])}{'...' if len(ranks) > 5 else ''})")
    else:
        print("\n⚠️  No scraped data found. Run scrapers first:")
        print("   python scripts/run_scrapers.py all-ranks")

    # Check trained models
    models_info = get_available_models()
    models = models_info.get('models', [])

    if models:
        print(f"\n🤖 Trained Models:")
        for model in models:
            rank = model.get('rank', 'unknown')
            trained_at = model.get('trained_at', 'unknown')[:10] if model.get('trained_at') else 'unknown'
            patch = model.get('patch', 'unknown')
            val_loss = model.get('best_val_loss', 0)
            print(f"   {rank:12} | Patch: {patch:6} | Loss: {val_loss:.4f} | Trained: {trained_at}")
    else:
        print("\n⚠️  No trained models found. Run training:")
        print("   python scripts/train_nn.py --all")

    # Check progress tracker
    tracker = get_progress_tracker()
    print(f"\n📈 Last Updated: {tracker.progress.get('last_updated', 'Never')}")

    print("\n" + "=" * 60)


def check_for_new_patch() -> tuple[bool, str, str]:
    """
    Check if there's a new patch that doesn't have trained models.

    Returns:
        (needs_retrain, latest_patch, model_patch)
    """
    loader = StatsLoader()
    patches = loader.get_available_patches()

    if not patches:
        return False, None, None

    latest_patch = patches[0]

    # Check existing models
    models_info = get_available_models()
    models = models_info.get('models', [])

    if not models:
        return True, latest_patch, None

    # Get the patch from the most recent model
    model_patches = [m.get('patch') for m in models if m.get('patch')]
    if not model_patches:
        return True, latest_patch, None

    most_recent_model_patch = model_patches[0]

    # Compare patches
    if latest_patch != most_recent_model_patch:
        logger.info(f"New patch detected: {latest_patch} (models trained on {most_recent_model_patch})")
        return True, latest_patch, most_recent_model_patch

    return False, latest_patch, most_recent_model_patch


def retrain_on_new_patch(epochs: int = 50, priority_ranks: list = None):
    """
    Retrain models if a new patch is detected.

    Uses transfer learning from existing models when available.
    """
    needs_retrain, latest_patch, model_patch = check_for_new_patch()

    if not needs_retrain:
        logger.info(f"Models are up to date for patch {latest_patch}")
        return {"status": "up_to_date", "patch": latest_patch}

    logger.info(f"Retraining models for new patch {latest_patch}")

    # Priority ranks to train first (high elo = most valuable)
    if priority_ranks is None:
        priority_ranks = ['MASTER', 'GRANDMASTER', 'CHALLENGER', 'DIAMOND', 'PLATINUM']

    loader = StatsLoader()
    available_ranks = loader.get_available_ranks(latest_patch)

    # Filter to available ranks
    ranks_to_train = [r for r in priority_ranks if r in available_ranks]
    ranks_to_train.extend([r for r in available_ranks if r not in ranks_to_train])

    results = {"patch": latest_patch, "previous_patch": model_patch, "ranks": {}}

    for rank in ranks_to_train:
        logger.info(f"Training {rank} model for patch {latest_patch}...")
        try:
            trainer = NNTrainer(rank=rank)

            # Lower learning rate for transfer learning if model exists
            lr = 0.0005 if trainer.model_path.exists() else 0.001

            result = trainer.train(
                epochs=epochs,
                learning_rate=lr,
                patch=latest_patch
            )
            results["ranks"][rank] = {
                "status": "success",
                "val_loss": result.get("best_val_loss")
            }
        except Exception as e:
            results["ranks"][rank] = {"status": "error", "error": str(e)}
            logger.error(f"Failed to train {rank}: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Train TrynDraft neural network models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--rank', '-r',
        type=str,
        help='Train model for specific rank (e.g., DIAMOND, PLATINUM)'
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Train models for all available ranks'
    )
    parser.add_argument(
        '--epochs', '-e',
        type=int,
        default=50,
        help='Number of training epochs (default: 50)'
    )
    parser.add_argument(
        '--status', '-s',
        action='store_true',
        help='Show training status and exit'
    )
    parser.add_argument(
        '--retrain-on-patch',
        action='store_true',
        help='Check for new patch and retrain if needed'
    )
    parser.add_argument(
        '--patch', '-p',
        type=str,
        help='Specific patch to train on (default: latest)'
    )

    args = parser.parse_args()

    if args.status:
        print_status()
        return 0

    if args.retrain_on_patch:
        result = retrain_on_new_patch(epochs=args.epochs)
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get('status') != 'error' else 1

    if args.all:
        logger.info("Training models for all available ranks...")
        result = train_all_ranks(epochs=args.epochs)
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.rank:
        logger.info(f"Training model for {args.rank.upper()}...")
        result = train_model(epochs=args.epochs, rank=args.rank.upper())
        print(json.dumps(result, indent=2, default=str))
        return 0

    # Default: train combined model
    logger.info("Training combined model...")
    result = train_model(epochs=args.epochs)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
