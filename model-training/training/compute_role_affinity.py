#!/usr/bin/env python3
"""
Compute per-champion role affinity from pro-play training data.

Outputs checkpoints/role_affinity.json:
  { "champion_id": { "MID": 0.996, "SUPPORT": 0.002, ... }, ... }

Role names use frontend canonical form: TOP, JUNGLE, MID, BOT, SUPPORT.
Data comes from proplay_cleaned.pkl (63K+ games with explicit lane per pick).
"""

import json
import pickle
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "model-training" / "data"
CHECKPOINTS_DIR = ROOT / "model-training" / "checkpoints"

# Map training lane strings → frontend canonical role names
LANE_TO_ROLE: dict[str, str] = {
    "TOP":     "TOP",
    "JUNGLE":  "JUNGLE",
    "MIDDLE":  "MID",
    "BOTTOM":  "BOT",
    "UTILITY": "SUPPORT",
}


def compute_role_affinity(proplay_pkl: Path) -> dict[str, dict[str, float]]:
    counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    with open(proplay_pkl, "rb") as f:
        pro_df = pickle.load(f)

    for _, row in pro_df.iterrows():
        for pick in row.get("picks", []):
            cid = pick.get("champion_id")
            role = LANE_TO_ROLE.get(pick.get("lane", ""), None)
            if cid is not None and role is not None:
                counts[cid][role] += 1

    affinity: dict[str, dict[str, float]] = {}
    for cid, role_counts in counts.items():
        total = sum(role_counts.values())
        if total < 5:
            continue
        affinity[str(cid)] = {
            role: round(count / total, 4)
            for role, count in sorted(role_counts.items(), key=lambda x: -x[1])
        }

    return affinity


def main() -> None:
    proplay = DATA_DIR / "proplay_cleaned.pkl"
    output = CHECKPOINTS_DIR / "role_affinity.json"

    if not proplay.exists():
        print(f"⚠  {proplay} not found — skipping role affinity")
        return

    print(f"Computing role affinity from {proplay.name} ...")
    affinity = compute_role_affinity(proplay)
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(output, "w") as f:
        json.dump(affinity, f, separators=(",", ":"))

    print(f"✅ Wrote role_affinity.json — {len(affinity)} champions")

    for cid_str, label in [("103", "Ahri"), ("157", "Yasuo"), ("235", "Senna")]:
        if cid_str in affinity:
            print(f"  {label} ({cid_str}): {affinity[cid_str]}")


if __name__ == "__main__":
    main()
