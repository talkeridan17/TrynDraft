#!/usr/bin/env python3
"""
TrynDraft Model Refresh Pipeline
=================================
Orchestrates the full data → train → export → deploy cycle.

Usage (full refresh):
    cd model-training
    python training/refresh.py --riot-key RGAPI-xxxx --platform na1

Usage (retrain only on existing data):
    python training/refresh.py --skip-scrape

Usage (export only, no retrain):
    python training/refresh.py --skip-scrape --skip-train

The script automatically copies the resulting ONNX model and metadata
to frontend/public/models/ so the browser can pick it up immediately.
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]           # repo root
LLM_DIR = ROOT / "model-training"
TRAINING_DIR = LLM_DIR / "training"
DATA_DIR = LLM_DIR / "data"
CHECKPOINTS_DIR = LLM_DIR / "checkpoints"
MODELS_DIR = LLM_DIR / "models"
FRONTEND_MODELS = ROOT / "frontend" / "public" / "models"

CHECKPOINT_PT = MODELS_DIR / "best.pt"
CHECKPOINT_PT_FALLBACK = MODELS_DIR / "base_prediction_model.pt"
ONNX_OUTPUT = MODELS_DIR / "model.onnx"

TAG_DF = DATA_DIR / "annotated_abilities_df.pkl"
DAMAGE_DF = DATA_DIR / "champion_damage_breakdown.pkl"
UNIFIED_DF = DATA_DIR / "cleaned_matches_df.pkl"

LOG_FILE = LLM_DIR / "refresh.log"


class _Tee:
    """Write to both stdout and the log file simultaneously."""
    def __init__(self, log_path: Path):
        self._log = open(log_path, "w", buffering=1)
        self._stdout = sys.__stdout__

    def write(self, data: str):
        self._stdout.write(data)
        self._log.write(data)

    def flush(self):
        self._stdout.flush()
        self._log.flush()

    def close(self):
        self._log.close()


def run(cmd: list[str], cwd: Path = LLM_DIR, env_extra: dict | None = None) -> int:
    import os
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    print(f"\n▶ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env)
    if result.returncode != 0:
        print(f"❌ Command failed with exit code {result.returncode}")
    return result.returncode


def step_scrape(args: argparse.Namespace) -> bool:
    """Pull fresh high-ELO SoloQ matches from Riot Match-v5 API."""
    print("\n" + "="*60)
    print("STEP 1: Scraping new SoloQ matches")
    print("="*60)

    if not args.riot_key:
        print("⚠  No --riot-key provided. Skipping scrape.")
        return True

    raw_output = DATA_DIR / "raw_soloq"
    raw_output.mkdir(parents=True, exist_ok=True)

    # Translate --max-games to scraper's --max-summoners / --matches-per-summoner.
    # Default: 50 summoners × 100 matches each = 5,000 games (after dedup, ~3–4K unique).
    matches_per = 100
    max_summoners = max(1, args.max_games // matches_per)

    rc = run(
        [
            sys.executable, "scraping/scraper.py",
            "--platform", args.platform,
            "--tier", args.tier,
            "--output", str(raw_output),
            "--max-summoners", str(max_summoners),
            "--matches-per-summoner", str(matches_per),
        ],
        env_extra={"RIOT_API_KEY": args.riot_key},
    )
    return rc == 0


def step_clean(args: argparse.Namespace) -> bool:
    """Clean raw JSON matches into a unified DataFrame."""
    print("\n" + "="*60)
    print("STEP 2: Cleaning and unifying match data")
    print("="*60)

    raw_soloq = DATA_DIR / "raw_soloq"
    proplay_pkl = DATA_DIR / "proplay_cleaned.pkl"

    if not raw_soloq.exists() and not proplay_pkl.exists():
        print("⚠  No raw data found. Skipping clean step.")
        return True

    rc = run(
        [sys.executable, "-c", f"""
import sys, os, pickle
sys.path.insert(0, "{DATA_DIR}")
from unify import clean_soloq_matches, unify

# Step 1: raw JSON directory → cleaned soloq pickle
raw_dir = "{raw_soloq}"
soloq_pkl = "{DATA_DIR / 'cleaned_soloq_matches_df.pkl'}"
if os.path.isdir(raw_dir) and any(f.endswith('.json') for f in os.listdir(raw_dir)):
    print(f"Cleaning {{len([f for f in os.listdir(raw_dir) if f.endswith('.json')])}} raw JSON files...")
    clean_soloq_matches(raw_dir)
elif not os.path.exists(soloq_pkl):
    print("⚠  No raw soloq data found, using proplay only")
    soloq_pkl = None

# Step 2: unify proplay + soloq into training format
df = unify("{proplay_pkl}", soloq_pkl) if soloq_pkl else __import__('pandas').read_pickle("{proplay_pkl}")
with open("{UNIFIED_DF}", "wb") as f:
    pickle.dump(df, f)
print(f"Unified DataFrame saved: {{len(df)}} records")
"""],
    )
    return rc == 0


def step_train(args: argparse.Namespace) -> bool:
    """Train (or fine-tune) the DraftTransformer on all available data."""
    print("\n" + "="*60)
    print("STEP 3: Training DraftTransformer")
    print("="*60)

    if not UNIFIED_DF.exists():
        print(f"⚠  Unified DataFrame not found at {UNIFIED_DF}. Using existing checkpoint.")
        return CHECKPOINT_PT.exists()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, str(TRAINING_DIR / "train.py"),
        "--data", str(UNIFIED_DF),
        "--tags", str(TAG_DF),
        "--damage", str(DAMAGE_DF),
        "--output", str(MODELS_DIR),
        "--epochs", str(args.epochs),
    ]
    resume_ckpt = CHECKPOINT_PT if CHECKPOINT_PT.exists() else CHECKPOINT_PT_FALLBACK
    if args.fine_tune and resume_ckpt.exists():
        cmd += ["--resume", str(resume_ckpt)]

    rc = run(cmd)
    return rc == 0


def step_cleanup() -> None:
    """Remove intermediate training artifacts that aren't needed after export."""
    removed = []
    # Periodic epoch checkpoints
    for f in MODELS_DIR.glob("epoch_*.pt"):
        f.unlink()
        removed.append(f.name)
    # Tag index file written by train.py (baked into model.json already)
    tags_cache = MODELS_DIR / "valid_tags.json"
    if tags_cache.exists():
        tags_cache.unlink()
        removed.append(tags_cache.name)
    if removed:
        print(f"  Cleaned up: {', '.join(removed)}")


def step_role_affinity() -> bool:
    """Compute per-champion role affinity from pro-play data."""
    print("\n" + "="*60)
    print("STEP 3.5: Computing role affinity")
    print("="*60)

    rc = run([sys.executable, str(TRAINING_DIR / "compute_role_affinity.py")])
    return rc == 0


def step_matchup_winrates() -> bool:
    """Compute per-champion matchup win rates from scraped SoloQ data."""
    print("\n" + "="*60)
    print("STEP 3.6: Computing matchup win rates")
    print("="*60)

    raw_dir = DATA_DIR / "raw_soloq"
    if not raw_dir.exists() or not any(raw_dir.glob("*.json")):
        print("⚠  No raw SoloQ data found — skipping matchup computation")
        return True

    rc = run([sys.executable, str(TRAINING_DIR / "compute_matchup_winrates.py")])
    return rc == 0


def step_export() -> bool:
    """Export the trained .pt checkpoint to ONNX."""
    print("\n" + "="*60)
    print("STEP 4: Exporting to ONNX")
    print("="*60)

    ckpt = CHECKPOINT_PT if CHECKPOINT_PT.exists() else CHECKPOINT_PT_FALLBACK
    if not ckpt.exists():
        print(f"❌ No checkpoint found at {CHECKPOINT_PT} or {CHECKPOINT_PT_FALLBACK}")
        return False
    if ckpt == CHECKPOINT_PT_FALLBACK:
        print(f"⚠  best.pt not found, falling back to {CHECKPOINT_PT_FALLBACK.name}")

    rc = run(
        [
            sys.executable, str(TRAINING_DIR / "export_onnx.py"),
            "--checkpoint", str(ckpt),
            "--tags", str(TAG_DF),
            "--damage", str(DAMAGE_DF),
            "--output", str(ONNX_OUTPUT),
        ]
    )
    return rc == 0


def step_deploy_frontend() -> bool:
    """Copy ONNX model and metadata to frontend/public/models/."""
    print("\n" + "="*60)
    print("STEP 5: Deploying to frontend/public/models/")
    print("="*60)

    FRONTEND_MODELS.mkdir(parents=True, exist_ok=True)

    files_to_copy = [
        (ONNX_OUTPUT, FRONTEND_MODELS / "model.onnx"),
        (ONNX_OUTPUT.with_suffix(".json"), FRONTEND_MODELS / "model.json"),
    ]

    # Also copy the external data file if it exists (large models split weights)
    external_data = ONNX_OUTPUT.with_suffix(".onnx.data")
    if not external_data.exists():
        external_data = ONNX_OUTPUT.parent / "model.onnx.data"
    if external_data.exists():
        files_to_copy.append((external_data, FRONTEND_MODELS / "model.onnx.data"))

    # Copy checkpoint JSON artifacts
    for src_name, dst_name in [
        ("champ_to_id.json", "champ_to_id.json"),
        ("tags.json", "tags.json"),
    ]:
        src = CHECKPOINTS_DIR / src_name
        if src.exists():
            files_to_copy.append((src, FRONTEND_MODELS / dst_name))

    # champion_tags.csv lives in data/
    tags_csv = DATA_DIR / "champion_tags.csv"
    if tags_csv.exists():
        files_to_copy.append((tags_csv, FRONTEND_MODELS / "champion_tags.csv"))

    # role_affinity.json and matchup_winrates.json live in checkpoints/
    for ckpt_file in ["role_affinity.json", "matchup_winrates.json"]:
        src = CHECKPOINTS_DIR / ckpt_file
        if src.exists():
            files_to_copy.append((src, FRONTEND_MODELS / ckpt_file))

    success = True
    for src, dst in files_to_copy:
        if src.exists():
            shutil.copy2(src, dst)
            size_mb = src.stat().st_size / 1_000_000
            print(f"  ✅ {src.name} → {dst} ({size_mb:.1f} MB)")
        else:
            print(f"  ⚠  {src} not found, skipping")
            success = False

    return success


def main():
    parser = argparse.ArgumentParser(description="TrynDraft model refresh pipeline")

    parser.add_argument("--riot-key", default=None,
                        help="Riot API key (RGAPI-xxxx). Can also set RIOT_API_KEY env var.")
    parser.add_argument("--platform", default="na1",
                        help="Riot platform (na1, euw1, kr, etc.)")
    parser.add_argument("--tier", default="EMERALD",
                        choices=["CHALLENGER", "GRANDMASTER", "MASTER", "DIAMOND", "EMERALD", "PLATINUM"],
                        help="Minimum rank tier to scrape")
    parser.add_argument("--max-games", type=int, default=10_000,
                        help="Max new games to scrape per run (default 10,000)")
    parser.add_argument("--epochs", type=int, default=50,
                        help="Training epochs (default 50; use 100 for full retrain)")
    parser.add_argument("--fine-tune", action="store_true",
                        help="Fine-tune from existing checkpoint instead of training from scratch")
    parser.add_argument("--skip-scrape", action="store_true",
                        help="Skip scraping step (use existing raw data)")
    parser.add_argument("--skip-clean", action="store_true",
                        help="Skip cleaning step (use existing unified DataFrame)")
    parser.add_argument("--skip-train", action="store_true",
                        help="Skip training (export only)")
    parser.add_argument("--skip-export", action="store_true",
                        help="Skip ONNX export")
    parser.add_argument("--skip-deploy", action="store_true",
                        help="Skip copying to frontend/public/models/")

    args = parser.parse_args()

    # Allow RIOT_API_KEY env var as fallback
    if not args.riot_key:
        import os
        args.riot_key = os.environ.get("RIOT_API_KEY")

    # Mirror all output to refresh.log (overwritten each run)
    tee = _Tee(LOG_FILE)
    sys.stdout = tee  # type: ignore[assignment]

    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("TrynDraft Model Refresh Pipeline")
    print(f"  Platform : {args.platform}")
    print(f"  Tier     : {args.tier}")
    print(f"  Epochs   : {args.epochs}")
    print(f"  Fine-tune: {args.fine_tune}")

    ok = True

    if not args.skip_scrape:
        ok = step_scrape(args)
        if not ok:
            print("⚠  Scrape step had errors — continuing with existing data")

    if not args.skip_clean:
        ok = step_clean(args)
        if not ok:
            print("⚠  Clean step had errors — continuing with existing data")

    if not args.skip_train:
        ok = step_train(args)
        if not ok:
            print("❌ Training failed. Aborting.")
            sys.exit(1)

    step_role_affinity()
    step_matchup_winrates()

    if not args.skip_export:
        ok = step_export()
        if not ok:
            print("❌ ONNX export failed. Aborting.")
            sys.exit(1)

    if not args.skip_deploy:
        ok = step_deploy_frontend()
        if not ok:
            print("⚠  Some files missing from deploy step")

    step_cleanup()

    print("\n" + "="*60)
    print("✅ Refresh pipeline complete!")
    print(f"   Model: {ONNX_OUTPUT}")
    print(f"   Frontend: {FRONTEND_MODELS}/model.onnx")
    print(f"   Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Log: {LOG_FILE}")
    print("="*60)


if __name__ == "__main__":
    main()
