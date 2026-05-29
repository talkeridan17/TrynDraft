# train.py

import pickle
import pandas as pd
import torch
import torch.nn as nn
import argparse
from torch.utils.data import Dataset, DataLoader, Sampler
from ast import literal_eval
from collections import defaultdict
from pathlib import Path

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

parser = argparse.ArgumentParser()

# ── Champion vocab ────────────────────────────────────────────────────────────
# Set high enough to cover all champion IDs including future releases.
# Index 0 is reserved as a padding sentinel — no champion has ID 0.
CHAMPION_VOCAB = 1000
NO_BAN_ID = CHAMPION_VOCAB - 1

# ── Event types ───────────────────────────────────────────────────────────────
EVENT_BAN  = 0
EVENT_PICK = 1

MIN_TAG_CHAMPIONS = 3   # tags appearing on fewer champions are filtered out

PRO_SEQUENCE = [
    (0, 1, EVENT_BAN),  (1, 1, EVENT_BAN),  (0, 1, EVENT_BAN),  (1, 1, EVENT_BAN),  (0, 1, EVENT_BAN),  (1, 1, EVENT_BAN),
    (0, 2, EVENT_PICK), (1, 2, EVENT_PICK), (0, 2, EVENT_PICK), (1, 2, EVENT_PICK), (0, 2, EVENT_PICK), (1, 2, EVENT_PICK),
    (0, 3, EVENT_BAN),  (1, 3, EVENT_BAN),  (0, 3, EVENT_BAN),  (1, 3, EVENT_BAN),
    (0, 4, EVENT_PICK), (1, 4, EVENT_PICK), (0, 4, EVENT_PICK), (1, 4, EVENT_PICK),
]

# 10 bans in no order followed by picks in order B, R, R, B, B, R, R, B, B, R
SOLOQ_SEQUENCE = [
    # Phase 1 bans: B, B, R, R, B, R
    (0, 1, EVENT_BAN), (0, 1, EVENT_BAN), (1, 1, EVENT_BAN), (1, 1, EVENT_BAN), (0, 1, EVENT_BAN), (1, 1, EVENT_BAN),
    # Phase 2 bans: B, R, B, R
    (0, 2, EVENT_BAN), (1, 2, EVENT_BAN), (0, 2, EVENT_BAN), (1, 2, EVENT_BAN),
    # Phase 2 picks: B, R, R, B, B, R
    (0, 2, EVENT_PICK), (1, 2, EVENT_PICK), (1, 2, EVENT_PICK), (0, 2, EVENT_PICK), (0, 2, EVENT_PICK), (1, 2, EVENT_PICK),
    # Phase 3 picks: R, B, B, R
    (1, 3, EVENT_PICK), (0, 3, EVENT_PICK), (0, 3, EVENT_PICK), (1, 3, EVENT_PICK),
]

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
        if isinstance(idx, list):
            return [self.records[i] for i in idx]
        return self.records[idx]
    
    def domain_indices(self) -> tuple[list, list]:
        pro   = [i for i, r in enumerate(self.records) if r["domain"] == DOMAIN_PRO]
        soloq = [i for i, r in enumerate(self.records) if r["domain"] == DOMAIN_SOLOQ]
        return pro, soloq
    
    @staticmethod
    def _normalize_domain(raw) -> int:
        """Accept both integer and string domain labels from different data vintages."""
        if isinstance(raw, str):
            return DOMAIN_PRO if raw.lower() in ("pro", "proplay", "0") else DOMAIN_SOLOQ
        return int(raw)

    @staticmethod
    def _add_missing_fields(bans: list, picks: list) -> tuple[list, list]:
        """
        Older scraped data lacks pick_turn and phase. Reconstruct from position:
        - pick_turn = index in the list
        - phase: first 6 items → phase 1, last 4 → phase 2 (standard pro/soloq split)
        """
        need_pick_turn = bans and "pick_turn" not in bans[0]
        need_phase     = bans and "phase"     not in bans[0]
        if need_pick_turn or need_phase:
            bans = [
                dict(b,
                     pick_turn=(b.get("pick_turn", i)),
                     phase=(b.get("phase", 1 if i < 6 else 2)))
                for i, b in enumerate(bans)
            ]
        need_pick_turn = picks and "pick_turn" not in picks[0]
        need_phase     = picks and "phase"     not in picks[0]
        if need_pick_turn or need_phase:
            picks = [
                dict(p,
                     pick_turn=(p.get("pick_turn", i)),
                     phase=(p.get("phase", 1 if i < 6 else 2)))
                for i, p in enumerate(picks)
            ]
        return bans, picks

    def _parse_row(self, row) -> dict | None:
        try:
            picks = list(row["picks"])
            bans  = list(row["bans"])

            if not isinstance(picks, list) or not isinstance(bans, list):
                return None
            if len(picks) != 10 or len(bans) != 10:
                return None
            if any(p.get("champion_id") is None for p in picks):
                return None
            if any(b.get("champion_id") is None for b in bans):
                return None

            domain         = self._normalize_domain(row["domain"])
            blue_win       = float(row["blue_win"])
            recency_weight = float(row["recency_weight"])
            game_length_s  = int(row["game_length_s"])

            bans, picks = self._add_missing_fields(bans, picks)

            sorted_picks = sorted(picks, key=lambda p: p["pick_turn"])
            sorted_bans  = sorted(bans,  key=lambda b: b["pick_turn"])

            if domain == DOMAIN_PRO:
                p1_bans  = [b for b in sorted_bans  if b["phase"] == 1]
                p2_bans  = [b for b in sorted_bans  if b["phase"] == 2]
                p1_picks = [p for p in sorted_picks if p["phase"] == 1]
                p2_picks = [p for p in sorted_picks if p["phase"] == 2]

                for ban in p1_bans + p2_bans:
                    if ban["champion_id"] == -1:
                        ban["champion_id"] = NO_BAN_ID

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
                for ban in sorted_bans:
                    if ban["champion_id"] == -1:
                        ban["champion_id"] = NO_BAN_ID

                events = (
                    [_make_event(b["champion_id"], b["side"], b["phase"], 5, EVENT_BAN)
                    for b in sorted_bans]  +
                    [_make_event(p["champion_id"], p["side"], p["phase"],
                                LANE_MAP.get(p.get("lane", "UNKNOWN"), 5), EVENT_PICK)
                    for p in sorted_picks]
                )

            if len(events) != 20:
                return None

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

def _shuffled(lst: list) -> list:
    return [lst[i] for i in torch.randperm(len(lst)).tolist()]

class StratifiedSampler(Sampler):
    def __init__(self, pro_idx: list, soloq_idx: list, batch_size: int=64, pro_fraction: float=0.4):
        self.pro_idx = pro_idx
        self.soloq_idx = soloq_idx
        self.pro_per_batch = max(1, int(batch_size * pro_fraction))
        self.soloq_per_batch = batch_size - self.pro_per_batch
        self.batch_size = batch_size
        self.num_batches = min(len(self.pro_idx) // self.pro_per_batch, len(self.soloq_idx) // self.soloq_per_batch)
        print(f"StratifiedSampler: {self.num_batches} batches / epoch | Pro: {self.pro_per_batch} | Soloq: {self.soloq_per_batch}")
    
    def __iter__(self):
        pro_pool = _shuffled(self.pro_idx)
        soloq_pool = _shuffled(self.soloq_idx)
        
        for b in range(self.num_batches):
            pro_batch   = pro_pool  [b * self.pro_per_batch   : (b+1) * self.pro_per_batch]
            soloq_batch = soloq_pool[b * self.soloq_per_batch : (b+1) * self.soloq_per_batch]

            # Combine and shuffle within the batch so domain isn't
            # positionally correlated (all pro first, then soloq)
            batch = pro_batch + soloq_batch
            yield [batch[i] for i in _shuffled(list(range(len(batch))))]
    
    def __len__(self):
        return self.num_batches * self.batch_size

def collate_fn(batch: list):
    return {k: torch.stack([record[k] for record in batch]) for k in batch[0].keys()}

def make_dataloaders(
    df: pd.DataFrame,
    val_split: float = 0.05,
    batch_size: int = 64,
    pro_fraction: float = 0.40,
    num_workers: int = 2
):
    dataset = DraftDataset(df)
    pro_idx, soloq_idx = dataset.domain_indices()
    n_val_pro   = max(1, int(len(pro_idx)   * val_split))
    n_val_soloq = max(1, int(len(soloq_idx) * val_split))

    val_pro_idx   = pro_idx[:n_val_pro]
    val_soloq_idx = soloq_idx[:n_val_soloq]
    val_idx       = set(val_pro_idx + val_soloq_idx)

    train_idx = [i for i in range(len(dataset)) if i not in val_idx]

    global_to_local = {g: l for l, g in enumerate(train_idx)}

    train_pro   = [global_to_local[i] for i in train_idx
                   if dataset[i]["domain"] == DOMAIN_PRO]
    train_soloq = [global_to_local[i] for i in train_idx
                   if dataset[i]["domain"] == DOMAIN_SOLOQ]

    train_set = torch.utils.data.Subset(dataset, train_idx)
    val_set   = torch.utils.data.Subset(dataset, list(val_idx))

    # Fall back to simple random batching when only one domain is present
    if train_pro and train_soloq:
        sampler = StratifiedSampler(
            train_pro, train_soloq,
            batch_size=batch_size,
            pro_fraction=pro_fraction,
        )
        batch_sampler_arg = {"batch_sampler": sampler}
    else:
        print("⚠  Single-domain data — using standard random sampler (no stratification)")
        batch_sampler_arg = {"batch_size": batch_size, "shuffle": True}

    train_loader = DataLoader(
        train_set,
        collate_fn=collate_fn,
        num_workers=num_workers,
        pin_memory=True,
        **batch_sampler_arg,
    )

    val_loader = DataLoader(
        val_set,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=num_workers,
        pin_memory=True,
    )


    return train_loader, val_loader

class DraftTransformer(nn.Module):
    def __init__(
        self,
        num_tags: int,
        d_model: int = 256,
        n_heads: int = 8,
        num_layers: int = 4,
        ffn_dim: int = 1024,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.champion_embed = nn.Embedding(CHAMPION_VOCAB, d_model, padding_idx=0)
        self.side_embed = nn.Embedding(2, d_model // 4)
        self.phase_embed = nn.Embedding(3, d_model // 4)
        self.lane_embed = nn.Embedding(6, d_model // 4)
        self.event_embed = nn.Embedding(2, d_model // 4)
        self.domain_embed = nn.Embedding(2, d_model // 4)

        self.aux_proj = nn.Linear(5 * (d_model // 4), d_model)

        self.tag_proj = nn.Sequential(nn.Linear(num_tags, 64), nn.GELU())
        self.damage_proj = nn.Linear(3, d_model)
        self.feature_proj = nn.Linear(d_model + 64, d_model)

        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))
        nn.init.trunc_normal_(self.cls_token, std=0.02)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=ffn_dim,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.pick_ban_head = nn.Sequential(
            nn.Linear(d_model, ffn_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(ffn_dim, CHAMPION_VOCAB),
        )

        self.win_head = nn.Linear(d_model, 1)
        self._init_weights()
    
    def _init_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.trunc_normal_(module.weight, std=0.02)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.trunc_normal_(module.weight, std=0.02)
    
    def forward(self, batch: dict, target_mask: torch.Tensor | None = None):
        B = batch["champion_ids"].size(0)
        tokens = self._embed_tokens(batch)
        cls = self.cls_token.expand(B, -1, -1)
        seq = torch.cat([cls, tokens], dim=1)

        src_key_padding_mask = None
        if target_mask is not None:
            cls_mask = torch.zeros(B, 1, dtype=torch.bool, device=target_mask.device)
            src_key_padding_mask = torch.cat([cls_mask, target_mask], dim=1)
        
        encoded = self.transformer(seq, src_key_padding_mask=src_key_padding_mask)
        cls_out = encoded[:, 0, :]  # CLS token
        logits = self.pick_ban_head(cls_out)
        win_logit = self.win_head(cls_out).squeeze(-1)
        
        return logits, win_logit

    def register_static_features(self, tag_matrix: torch.Tensor, damage_matrix: torch.Tensor):
        self.register_buffer("tag_matrix", tag_matrix)
        self.register_buffer("damage_matrix", damage_matrix)
    
    def _embed_tokens(self, batch: dict):
        ids = batch["champion_ids"].clamp(0, CHAMPION_VOCAB - 1)
        B, S = ids.shape
        domain = batch["domain"]
        # Handle both [B] and [B, S] domain shapes
        if domain.dim() == 1:
            domain = domain.unsqueeze(1).expand(B, S)

        champ_emb = self.champion_embed(ids)
        aux_emb = self.aux_proj(torch.cat([
            self.side_embed(batch["sides"]),
            self.phase_embed(batch["phases"]),
            self.lane_embed(batch["lanes"]),
            self.event_embed(batch["event_types"]),
            self.domain_embed(domain),
        ], dim=-1))

        tag_feats = self.tag_proj(self.tag_matrix[ids].float())
        damage_feats = self.damage_proj(self.damage_matrix[ids])

        token = champ_emb + aux_emb + damage_feats
        token = self.feature_proj(torch.cat([token, tag_feats], dim=-1))
        
        return token

def build_champion_weights(df: pd.DataFrame) -> torch.Tensor:
    counts = torch.zeros(CHAMPION_VOCAB)
    for picks in df["picks"]:
        for p in picks:
            cid = p.get("champion_id")
            if cid and 0 < cid < CHAMPION_VOCAB:
                counts[cid] += 1
    for bans in df["bans"]:
        for b in bans:
            cid = b.get("champion_id")
            if cid and 0 < cid < CHAMPION_VOCAB:
                counts[cid] += 1
    
    weights = 1.0 / (counts + 1).sqrt()
    weights[0] = 0.0  # Padding
    weights[NO_BAN_ID] = 0.0  # No ban num
    weights = weights / weights.sum() * CHAMPION_VOCAB
    return weights

class DraftLoss(nn.Module):
    WIN_WEIGHT = 0.3

    def __init__(self, champion_weights: torch.Tensor):
        super().__init__()
        self.ce = nn.CrossEntropyLoss(reduction='none', label_smoothing=0.1)
        self.bce = nn.BCEWithLogitsLoss(reduction='none')
        self.register_buffer("champion_weights", champion_weights)
    
    def forward(self, logits, win_logit, targets):
        pick_loss = self.ce(logits, targets["target_id"])
        
        sample_weights = self.champion_weights[targets["target_id"]]
        pick_loss = pick_loss * sample_weights

        pick_loss = (pick_loss * targets["recency_weight"]).mean()

        win_loss = self.bce(win_logit, targets["blue_win"])
        win_loss = (win_loss * targets["recency_weight"] * targets["win_confidence"]).mean()

        total = pick_loss + self.WIN_WEIGHT * win_loss

        return total, pick_loss.detach(), win_loss.detach()

def sample_target_and_mask(batch):
    B = batch["champion_ids"].size(0)

    valid_mask = (batch["champion_ids"] != 0) & \
                 (batch["champion_ids"] != NO_BAN_ID)

    target_slots = torch.zeros(B, dtype=torch.long)
    for i in range(B):
        valid_positions = valid_mask[i].nonzero().squeeze(1)
        sampled         = valid_positions[torch.randint(len(valid_positions), (1,))]
        target_slots[i] = sampled

    target_ids = batch["champion_ids"][torch.arange(B), target_slots]
    is_pick    = batch["is_pick"][torch.arange(B), target_slots]

    positions = torch.arange(20).unsqueeze(0).expand(B, -1)
    mask      = positions >= target_slots.unsqueeze(1)
    targets = {
        "target_id": target_ids,
        "is_pick": is_pick,
        "blue_win": batch["blue_win"],
        "win_confidence": batch["win_confidence"],
        "recency_weight": batch["recency_weight"],
    }
    
    return targets, mask

def train_epoch(model, loader, optimizer, loss_fn, device, scaler=None):
    model.train()
    total_loss = pick_loss_sum = win_loss_sum = correct = total = 0

    for batch in loader:
        batch = {k: v.to(device) for k, v in batch.items()}
        targets, mask = sample_target_and_mask(batch)
        targets = {k: v.to(device) for k, v in targets.items()}
        mask = mask.to(device)


        optimizer.zero_grad()
        if scaler is not None:
            with torch.autocast(device_type="cuda"):
                logits, win_logit = model(batch, target_mask=mask)
                loss, pick_l, win_l = loss_fn(logits, win_logit, targets)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            logits, win_logit = model(batch, target_mask=mask)
            loss, pick_l, win_l = loss_fn(logits, win_logit, targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
        
        preds = logits.argmax(dim=-1)
        correct += (preds == targets["target_id"]).sum().item()
        total += batch["champion_ids"].size(0)

        total_loss += loss.item()
        pick_loss_sum += pick_l.item()
        win_loss_sum += win_l.item()
    
    n = max(len(loader), 1)
    return {
        "loss": total_loss / n,
        "pick_loss": pick_loss_sum / n,
        "win_loss": win_loss_sum / n,
        "pick_acc": correct / max(total, 1)
    }

@torch.no_grad()
def val_epoch(model, loader, loss_fn, device):
    model.eval()
    total_loss = 0.0
    pick_loss_sum = 0.0
    win_loss_sum = 0.0
    correct = 0
    total = 0
    
    for batch in loader:
        batch = {k: v.to(device) for k, v in batch.items()}
        targets, mask = sample_target_and_mask(batch)
        targets = {k: v.to(device) for k, v in targets.items()}
        mask = mask.to(device)
        
        logits, win_logit = model(batch, target_mask=mask)
        loss, pick_l, win_l = loss_fn(logits, win_logit, targets)


        preds = logits.argmax(dim=-1)
        correct += (preds == targets["target_id"]).sum().item()
        total += batch["champion_ids"].size(0)
        
        total_loss += loss.item()
        pick_loss_sum += pick_l.item()
        win_loss_sum += win_l.item()
    
    n = max(len(loader), 1)
    return {
        "loss": total_loss / n,
        "pick_loss": pick_loss_sum / n,
        "win_loss": win_loss_sum / n,
        "pick_acc": correct / max(total, 1)
    }

def main(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.mps.is_available() else "cpu")
    print(f"Using device: {device}")
    print(f"Loading {args.data}")
    with open(args.data, "rb") as f:
        df = pickle.load(f)
    print(f"Loaded {len(df)} records")
    print(f"Loading tag matrix from {args.tags}")
    with open(args.tags, "rb") as f:
        tag_df = pickle.load(f)

    print(f"Loading damage matrix from {args.damage}")
    with open(args.damage, "rb") as f:
        damage_matrix = pickle.load(f)
    
    print(f"Loaded tag matrix")
    print(f"Loaded damage matrix")

    damage_matrix_tensor = build_damage_matrix(damage_matrix)
    tag_matrix, valid_tags = build_tag_matrix(tag_df, damage_matrix)
    print(f"Tags: {tag_matrix.size(1)} | Damage matrix: {damage_matrix_tensor.shape}")

    champion_weights = build_champion_weights(df).to(device)
    print(f"Champion weights built, shape: {champion_weights.shape}")

    train_loader, val_loader = make_dataloaders(
        df,
        val_split=args.val_split,
        batch_size=args.batch_size,
        pro_fraction=args.pro_fraction,
        num_workers=args.num_workers
    )

    model = DraftTransformer(
        num_tags=tag_matrix.size(1),
        d_model=args.d_model,
        num_layers=args.n_layers,    
    ).to(device)
    model.register_static_features(tag_matrix.to(device), damage_matrix_tensor.to(device))
    print(f"Parameters: {sum(p.numel() for p in model.parameters()):,}")

    if args.resume:
        ckpt = torch.load(args.resume, map_location=device, weights_only=True)
        model.load_state_dict(ckpt["model"])
        print(f"Resumed from {args.resume} (epoch {ckpt.get('epoch', '?')}, val_acc={ckpt.get('val_pick_acc', '?'):.4f})")

    loss_fn   = DraftLoss(champion_weights)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.lr, weight_decay=0.05
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs, eta_min=1e-5
    )
    scaler = torch.amp.GradScaler("cuda") if device.type == "cuda" else None
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    import json
    (out / "valid_tags.json").write_text(json.dumps(valid_tags))
    print(f"Checkpoints will be saved to: {out}")

    best_val_loss = float("inf")

    for epoch in range(1, args.epochs + 1):
        train_m = train_epoch(model, train_loader, optimizer, loss_fn, device, scaler)
        val_m   = val_epoch(model, val_loader, loss_fn, device)
        scheduler.step()

        print(
            f"Epoch {epoch:03d} | "
            f"train loss {train_m['loss']:.4f}  acc {train_m['pick_acc']:.3f} | "
            f"val loss {val_m['loss']:.4f}  acc {val_m['pick_acc']:.3f} | "
            f"lr {scheduler.get_last_lr()[0]:.2e}"
        )

        # Save checkpoint on every improvement
        if val_m["loss"] < best_val_loss:
            best_val_loss = val_m["loss"]
            torch.save({
                "epoch":        epoch,
                "model":        model.state_dict(),
                "optimizer":    optimizer.state_dict(),
                "val_loss":     val_m["loss"],
                "val_pick_acc": val_m["pick_acc"],
                "args":         vars(args),
                "num_tags":     tag_matrix.size(1),
            }, out / "best.pt")
            print(f"  Saved best checkpoint (val_loss={best_val_loss:.4f})")

        # Save periodic checkpoint every 5 epochs for resuming
        if epoch % 5 == 0:
            torch.save({
                "epoch": epoch,
                "model": model.state_dict(),
            }, out / f"epoch_{epoch:03d}.pt")



if __name__ == "__main__":
    parser.add_argument("--data",         required=True,          help="Path to unified pickle")
    parser.add_argument("--tags",         required=True,          help="Path to champion tags CSV")
    parser.add_argument("--damage",       required=True,          help="Path to damage stats pickle")
    parser.add_argument("--output",       default="checkpoints")
    parser.add_argument("--epochs",       type=int,   default=30)
    parser.add_argument("--batch-size",   type=int,   default=64)
    parser.add_argument("--lr",           type=float, default=1e-4)
    parser.add_argument("--d-model",      type=int,   default=256)
    parser.add_argument("--n-layers",     type=int,   default=4)
    parser.add_argument("--pro-fraction", type=float, default=0.40)
    parser.add_argument("--val-split",    type=float, default=0.05)
    parser.add_argument("--num-workers",  type=int,   default=2)
    parser.add_argument("--resume",       default=None, help="Path to .pt checkpoint to fine-tune from")
    args = parser.parse_args()
    main(args)


