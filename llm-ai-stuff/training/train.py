# train.py

import pickle
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, Sampler
from ast import literal_eval
from collections import defaultdict

# ── Domain flags (must match your unified dataframe) ──────────────────────────
DOMAIN_PRO   = 0
DOMAIN_SOLOQ = 1

# ── Lane encoding ─────────────────────────────────────────────────────────────
LANE_MAP = {
    "TOP":     0,
    "JUNGLE":  1,
    "MIDDLE":  2,
    "BOTTOM":  3,
    "UTILITY": 4,
    "UNKNOWN": 5,
}

# ── Champion vocab ────────────────────────────────────────────────────────────
# Set high enough to cover all champion IDs including future releases.
# Index 0 is reserved as a padding sentinel — no champion has ID 0.
CHAMPION_VOCAB = 1000

# ── Event types ───────────────────────────────────────────────────────────────
EVENT_BAN  = 0
EVENT_PICK = 1

MIN_TAG_CHAMPIONS = 3   # tags appearing on fewer champions are filtered out


def build_damage_matrix(damage_df: pd.DataFrame) -> torch.Tensor:
    """
    Builds a [CHAMPION_VOCAB, 3] float tensor from your damage stats pickle.
    Each row is [ad_pct, ap_pct, true_pct] normalized to sum to 1.0.

    Indexed by champion_id so the model can look up any champion instantly.
    Champions missing from the dataframe get [0.5, 0.5, 0.0] as a fallback
    (treated as mixed AD/AP with no true damage).
    """
    # Fallback for unknown champions
    matrix = torch.zeros(CHAMPION_VOCAB, 3)
    matrix[:, 0] = 0.5   # ad_pct
    matrix[:, 1] = 0.5   # ap_pct

    for _, row in damage_df.iterrows():
        cid = int(row["champion_id"])
        if cid >= CHAMPION_VOCAB:
            continue
        matrix[cid, 0] = float(row["ad_pct"])   / 100.0
        matrix[cid, 1] = float(row["ap_pct"])   / 100.0
        matrix[cid, 2] = float(row["true_pct"]) / 100.0

    return matrix   # [CHAMPION_VOCAB, 3]


def build_tag_matrix(tag_df: pd.DataFrame, damage_df: pd.DataFrame) -> tuple[torch.Tensor, list]:
    """
    Builds a binary multi-hot tag matrix of shape [CHAMPION_VOCAB, num_tags].

    We need damage_df here only to resolve champion_name → champion_id,
    since the tag dataframe has names but not IDs.

    Returns:
        matrix:     FloatTensor [CHAMPION_VOCAB, num_tags]
        valid_tags: list of tag strings in column order (for reference)
    """
    # Build name → id lookup from damage dataframe
    name_to_id = {
        str(row["champion_name"]): int(row["champion_id"])
        for _, row in damage_df.iterrows()
    }

    # Parse tag lists (stored as strings in CSV)
    tag_df = tag_df.copy()
    tag_df["tags"] = tag_df["tags"].apply(
        lambda x: literal_eval(x) if isinstance(x, str) else
                  (x if isinstance(x, list) else [])
    )

    # Aggregate all tags per champion across all abilities
    champ_tags = defaultdict(set)
    for _, row in tag_df.iterrows():
        champ = row["champion"]
        for tag in row["tags"]:
            champ_tags[champ].add(tag)

    # Count how many champions have each tag, filter rare ones
    tag_counts = defaultdict(int)
    for tags in champ_tags.values():
        for tag in tags:
            tag_counts[tag] += 1

    valid_tags = sorted(t for t, c in tag_counts.items() if c >= MIN_TAG_CHAMPIONS)
    tag_to_idx = {t: i for i, t in enumerate(valid_tags)}
    print(f"Tags after filtering: {len(valid_tags)} (from {len(tag_counts)} total)")

    # Build binary matrix
    matrix = torch.zeros(CHAMPION_VOCAB, len(valid_tags))
    unresolved = []

    for champ_name, tags in champ_tags.items():
        cid = name_to_id.get(champ_name)
        if cid is None:
            unresolved.append(champ_name)
            continue
        if cid >= CHAMPION_VOCAB:
            continue
        for tag in tags:
            idx = tag_to_idx.get(tag)
            if idx is not None:
                matrix[cid, idx] = 1.0

    if unresolved:
        print(f"Warning: {len(unresolved)} champions unresolved in tag matrix: {unresolved}")

    return matrix, valid_tags   # [CHAMPION_VOCAB, num_tags], list[str]

def _make_event(champion_id: int, side: int, phase: int,
                lane: int, event_type: int) -> dict:
    return {
        "champion_id": min(int(champion_id), CHAMPION_VOCAB - 1),
        "side":        int(side),
        "phase":       int(phase),
        "lane":        int(lane),
        "event_type":  int(event_type),
    }

class DraftDataset(Dataset):

    def __init__(self, df: pd.DataFrame):
        self.records = []
        skipped = 0

        for _, row in df.iterrows():
            record = self._parse_row(row)
            if record is not None:
                self.records.append(record)
            else:
                skipped += 1

        pro_n   = sum(1 for r in self.records if r["domain"] == DOMAIN_PRO)
        soloq_n = len(self.records) - pro_n
        print(f"Loaded {len(self.records)} records ({pro_n} pro, {soloq_n} soloq) | {skipped} skipped")

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        return self.records[idx]
    
    def _parse_row(self, row) -> dict | None:
        try:
            picks = row["picks"]
            bans  = row["bans"]

            sorted_picks = sorted(picks, key=lambda p: p["pick_turn"])
            sorted_bans  = sorted(bans,  key=lambda b: b["pick_turn"])


            if not isinstance(picks, list) or not isinstance(bans, list):
                return None
            if len(picks) != 10 or len(bans) != 10:
                return None
            if any(p.get("champion_id") is None for p in picks):
                return None
            if any(b.get("champion_id") is None for b in bans):
                return None

            domain         = int(row["domain"])
            blue_win       = float(row["blue_win"])
            recency_weight = float(row["recency_weight"])
            game_length_s  = int(row["game_length_s"])

            if domain == DOMAIN_PRO:
                p1_bans  = [b for b in sorted_bans  if b["phase"] == 1]
                p2_bans  = [b for b in sorted_bans  if b["phase"] == 2]
                p1_picks = [p for p in sorted_picks if p["phase"] == 1]
                p2_picks = [p for p in sorted_picks if p["phase"] == 2]

                if len(p1_bans) != 6 or len(p2_bans) != 4:
                    return None
                if len(p1_picks) != 6 or len(p2_picks) != 4:
                    return None

                events = (
                    [_make_event(b["champion_id"], b["side"], b["phase"], 5, EVENT_BAN)
                    for b in p1_bans]  +
                    [_make_event(p["champion_id"], p["side"], p["phase"],
                                LANE_MAP.get(p.get("lane", "UNKNOWN"), 5), EVENT_PICK)
                    for p in p1_picks] +
                    [_make_event(b["champion_id"], b["side"], b["phase"], 5, EVENT_BAN)
                    for b in p2_bans]  +
                    [_make_event(p["champion_id"], p["side"], p["phase"],
                                LANE_MAP.get(p.get("lane", "UNKNOWN"), 5), EVENT_PICK)
                    for p in p2_picks]
                )
            else:
                events = (
                    [_make_event(b["champion_id"], b["side"], b["phase"], 5, EVENT_BAN)
                    for b in sorted_bans]  +
                    [_make_event(p["champion_id"], p["side"], p["phase"],
                                LANE_MAP.get(p.get("lane", "UNKNOWN"), 5), EVENT_PICK)
                    for p in sorted_picks]
                )

            if len(events) != 20:
                return None

            # Win confidence — longer games are more draft-determined
            # A 15 min game is often decided by one early fight, not the draft.
            # A 40+ min game is much more likely to reflect draft quality.
            win_confidence = min(game_length_s / (40 * 60), 1.0)

            return {
                "champion_ids":   torch.tensor([e["champion_id"] for e in events], dtype=torch.long),
                "sides":          torch.tensor([e["side"]        for e in events], dtype=torch.long),
                "phases":         torch.tensor([e["phase"]       for e in events], dtype=torch.long),
                "lanes":          torch.tensor([e["lane"]        for e in events], dtype=torch.long),
                "event_types":    torch.tensor([e["event_type"]  for e in events], dtype=torch.long),
                "is_pick":        torch.tensor([e["event_type"] == EVENT_PICK for e in events], dtype=torch.bool),
                "blue_win":       torch.tensor(blue_win,       dtype=torch.float),
                "domain":         torch.tensor(domain,         dtype=torch.long),
                "recency_weight": torch.tensor(recency_weight, dtype=torch.float),
                "win_confidence": torch.tensor(win_confidence, dtype=torch.float),
            }

        except (KeyError, TypeError, ValueError):
            return None

class StratifiedSampler():
    pass

with open("data/unified_data.pkl", "rb") as f:
    df = pickle.load(f)

dataset = DraftDataset(df)
print(len(dataset))

# Check domain split
pro_n   = sum(1 for i in range(len(dataset)) if dataset[i]["domain"] == DOMAIN_PRO)
soloq_n = len(dataset) - pro_n
print(f"Pro: {pro_n} | Soloq: {soloq_n}")

