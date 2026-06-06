#!/usr/bin/env python3
"""
Compute per-champion 1v1 matchup win rates from scraped SoloQ raw JSON.

Outputs checkpoints/matchup_winrates.json:
  { "champion_id": { "ROLE": { "enemy_champion_id": win_rate }, ... }, ... }

Role keys match role_affinity.json convention: TOP, JUNGLE, MID, BOT, SUPPORT.
Only matchups with >= MIN_GAMES appearances are included (default 15).
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "model-training" / "data"
CHECKPOINTS_DIR = ROOT / "model-training" / "checkpoints"

MIN_GAMES = 15

# Riot API teamPosition → frontend canonical role (matches role_affinity.json)
LANE_NORM: dict[str, str] = {
    "TOP":     "TOP",
    "JUNGLE":  "JUNGLE",
    "MID":     "MID",
    "MIDDLE":  "MID",
    "BOTTOM":  "BOT",
    "BOT":     "BOT",
    "UTILITY": "SUPPORT",
    "SUPPORT": "SUPPORT",
}


def compute_matchup_winrates(raw_dir: Path, min_games: int = MIN_GAMES) -> dict:
    # [champ_id_str][role][enemy_id_str] = [wins, total]
    counts: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0])))

    files = list(raw_dir.glob("*.json"))
    if not files:
        print(f"⚠  No JSON files found in {raw_dir}")
        return {}

    print(f"Processing {len(files):,} match files...")
    for i, fpath in enumerate(files):
        if i % 5000 == 0 and i > 0:
            print(f"  {i:,}/{len(files):,}")
        try:
            record = json.loads(fpath.read_text())
        except Exception:
            continue

        blue_win: bool = record.get("blue_win", False)
        picks: list = record.get("picks", [])

        blue_by_lane: dict[str, int] = {}
        red_by_lane: dict[str, int] = {}
        for pick in picks:
            raw_lane = pick.get("lane", "")
            role = LANE_NORM.get(raw_lane.upper(), None)
            if not role:
                continue
            cid = pick.get("champion_id", 0)
            if not isinstance(cid, int) or cid <= 0:
                continue
            side = pick.get("side", -1)
            if side == 0:
                blue_by_lane[role] = cid
            elif side == 1:
                red_by_lane[role] = cid

        for role in set(blue_by_lane) & set(red_by_lane):
            b, r = blue_by_lane[role], red_by_lane[role]
            b_str, r_str = str(b), str(r)

            counts[b_str][role][r_str][1] += 1
            if blue_win:
                counts[b_str][role][r_str][0] += 1

            counts[r_str][role][b_str][1] += 1
            if not blue_win:
                counts[r_str][role][b_str][0] += 1

    out: dict[str, dict[str, dict[str, float]]] = {}
    total_pairs = 0
    for cid_str, roles in counts.items():
        role_data: dict[str, dict[str, float]] = {}
        for role, enemies in roles.items():
            enemy_data: dict[str, float] = {}
            for enemy_str, (wins, games) in enemies.items():
                if games >= min_games:
                    enemy_data[enemy_str] = round(wins / games, 4)
            if enemy_data:
                role_data[role] = enemy_data
                total_pairs += len(enemy_data)
        if role_data:
            out[cid_str] = role_data

    print(f"✅ {len(out):,} champions, {total_pairs:,} matchup pairs (min {min_games} games)")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute champion matchup win rates from raw SoloQ data")
    parser.add_argument("--raw-dir", type=Path, default=DATA_DIR / "raw_soloq",
                        help="Directory of scraped match JSON files")
    parser.add_argument("--output", type=Path, default=CHECKPOINTS_DIR / "matchup_winrates.json",
                        help="Output JSON path")
    parser.add_argument("--min-games", type=int, default=MIN_GAMES,
                        help="Minimum games required to include a matchup (default 15)")
    args = parser.parse_args()

    if not args.raw_dir.exists():
        print(f"⚠  {args.raw_dir} not found — no SoloQ data to compute matchups from")
        return

    data = compute_matchup_winrates(args.raw_dir, args.min_games)
    if not data:
        print("No matchup data produced — skipping write")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
