import json
import torch
import torch.nn as nn
from pathlib import Path
import pickle
import pandas
import sys

from train import (
    DraftTransformer,
    CHAMPION_VOCAB,
    NO_BAN_ID,
    DOMAIN_PRO,
    DOMAIN_SOLOQ,
    EVENT_BAN,
    EVENT_PICK,
    LANE_MAP,
    build_damage_matrix,
    build_tag_matrix,
)

sys.path.insert(0, str(Path(__file__).parent.parent))
from data.utility import load_champion_map, reverse_champion_map
from proficiency import build_proficiency_map, get_champion_proficiency

saved_map = load_champion_map()
reverse_map = reverse_champion_map()

def id_to_champion(id: int):
    return saved_map[id]


def load_model(checkpoint_dir: str, tag_df, damage_df, device: torch.device):
    ckpt_dir = Path(checkpoint_dir)
    ckpt = torch.load(ckpt_dir / "base_prediction_model.pt", map_location=device)

    args = ckpt["args"]
    num_tags = ckpt["num_tags"]
    
    model = DraftTransformer(
        num_tags=num_tags,
        d_model=args.get("d_model", 256),
        num_layers=args.get("n_layers", 4),
    ).to(device)

    
    damage_matrix = build_damage_matrix(damage_df)
    tag_matrix, valid_tags = build_tag_matrix(tag_df, damage_df)
    model.register_static_features(tag_matrix.to(device), damage_matrix.to(device))

    model.load_state_dict(ckpt["model"])
    model.eval()
    print(f"Loaded checkpoint from epoch {ckpt['epoch']} "
          f"(val_loss={ckpt['val_loss']:.4f}, "
          f"val_acc={ckpt['val_pick_acc']:.3f})")
    return model

PRO_SEQUENCE = [
    # Phase 1 bans: B B R R B R
    (0, 1, EVENT_BAN),  (0, 1, EVENT_BAN),  (1, 1, EVENT_BAN),
    (1, 1, EVENT_BAN),  (0, 1, EVENT_BAN),  (1, 1, EVENT_BAN),
    # Phase 1 picks: Blue1, Red2, Blue2, Red1
    (0, 1, EVENT_PICK), (1, 1, EVENT_PICK), (1, 1, EVENT_PICK),
    (0, 1, EVENT_PICK), (0, 1, EVENT_PICK), (1, 1, EVENT_PICK),
    # Phase 2 bans: B R B R
    (0, 2, EVENT_BAN),  (1, 2, EVENT_BAN),  (0, 2, EVENT_BAN),  (1, 2, EVENT_BAN),
    # Phase 2 picks: Red1, Blue2, Red1
    (1, 2, EVENT_PICK), (0, 2, EVENT_PICK), (0, 2, EVENT_PICK), (1, 2, EVENT_PICK),
]

SOLOQ_SEQUENCE = [
    # Bans first (10), then picks (10)
    (0, 1, EVENT_BAN),  (0, 1, EVENT_BAN),  (1, 1, EVENT_BAN),
    (1, 1, EVENT_BAN),  (0, 1, EVENT_BAN),  (1, 1, EVENT_BAN),
    (0, 2, EVENT_BAN),  (1, 2, EVENT_BAN),  (0, 2, EVENT_BAN),  (1, 2, EVENT_BAN),
    (0, 1, EVENT_PICK), (1, 1, EVENT_PICK), (1, 1, EVENT_PICK),
    (0, 1, EVENT_PICK), (0, 1, EVENT_PICK), (1, 1, EVENT_PICK),
    (1, 2, EVENT_PICK), (0, 2, EVENT_PICK), (0, 2, EVENT_PICK), (1, 2, EVENT_PICK),
]

def build_draft_tensor(
    events: list[dict],
    domain: int,
    target_slot: int,
    device: torch.device
) -> tuple[dict, torch.Tensor, int]:
    sequence = PRO_SEQUENCE if domain == DOMAIN_PRO else SOLOQ_SEQUENCE
    
    if target_slot is None:
        target_slot = len(events)
    if target_slot > 19:
        raise ValueError(f"target_slot {target_slot} is out of range (0-19)")
    if target_slot < len(events):
        raise ValueError(
            f"target_slot {target_slot} is before the last known event "
            f"(have {len(events)} events). Cannot predict a slot already filled."
        )
    
    champion_ids = []
    sides        = []
    phases       = []
    lanes        = []
    event_types  = []
    is_pick      = []

    for slot_idx, (side, phase, event_type) in enumerate(sequence):
        if slot_idx < len(events):
            # Known event — use provided data
            ev    = events[slot_idx]
            cid   = int(ev["champion_id"])
            # Handle no-ban sentinel
            if cid == -1:
                cid = NO_BAN_ID
            cid   = min(cid, CHAMPION_VOCAB - 1)
            lane  = LANE_MAP.get(ev.get("lane", "UNKNOWN"), 5)
        else:
            # Unknown slot — padding
            cid   = 0
            lane  = 5   # UNKNOWN

        champion_ids.append(cid)
        sides.append(side)
        phases.append(phase)
        lanes.append(lane)
        event_types.append(event_type)
        is_pick.append(event_type == EVENT_PICK)
    
    mask = torch.tensor(
        [i >= target_slot for i in range(20)],
        dtype=torch.bool,
        device=device,
    ).unsqueeze(0)   # [1, 20]

    batch = {
        "champion_ids":   torch.tensor([champion_ids], dtype=torch.long,  device=device),
        "sides":          torch.tensor([sides],        dtype=torch.long,  device=device),
        "phases":         torch.tensor([phases],       dtype=torch.long,  device=device),
        "lanes":          torch.tensor([lanes],        dtype=torch.long,  device=device),
        "event_types":    torch.tensor([event_types],  dtype=torch.long,  device=device),
        "is_pick":        torch.tensor([is_pick],      dtype=torch.bool,  device=device),
        "domain":         torch.tensor([domain],       dtype=torch.long,  device=device),
        # These aren't used during inference but kept for API consistency
        "blue_win":       torch.tensor([0.0],          dtype=torch.float, device=device),
        "recency_weight": torch.tensor([1.0],          dtype=torch.float, device=device),
        "win_confidence": torch.tensor([1.0],          dtype=torch.float, device=device),
    }

    return batch, mask, target_slot

def predict(
    model:          DraftTransformer,
    events:         list[dict],
    domain:         int,
    picked_ids:     list[int],
    banned_ids:     list[int],
    target_slot:    int | None = None,
    top_k:          int = 3,
    device:         torch.device = torch.device("cpu"),
) -> dict:
    """
    Given a partial draft state, returns top-k champion suggestions
    and the blue side win probability.

    Args:
        model:       loaded DraftTransformer in eval mode
        events:      list of filled draft events in sequence order.
                     Each dict: {champion_id: int, lane: str}
        domain:      DOMAIN_PRO or DOMAIN_SOLOQ
        picked_ids:  champion IDs already picked by either team.
                     These are masked out of suggestions.
        banned_ids:  champion IDs already banned.
                     These are masked out of suggestions.
        target_slot: slot to predict (0-19). None = next unfilled slot.
        top_k:       number of suggestions to return (default 3)
        device:      torch device

    Returns:
        dict with keys:
            suggestions:  list of {champion_id, probability} dicts, length top_k
            win_prob:     float, blue side win probability (0.0 - 1.0)
            target_slot:  int, the slot that was predicted
            is_pick:      bool, whether the predicted slot is a pick or ban
    """
    model.eval()
    with torch.no_grad():
        # Build input tensors
        batch, mask, resolved_slot = build_draft_tensor(
            events=events,
            domain=domain,
            target_slot=target_slot,
            device=device,
        )

        # Forward pass
        logits, win_logit = model(batch, target_mask=mask)
        # logits:    [1, CHAMPION_VOCAB]
        # win_logit: [1]

        # ── Availability mask ──────────────────────────────────────────────
        # Mask out unavailable champions BEFORE softmax so they get
        # exactly zero probability rather than a small residual.
        # Determine which to mask based on whether we're predicting a ban
        sequence    = PRO_SEQUENCE if domain == DOMAIN_PRO else SOLOQ_SEQUENCE
        slot_is_ban = sequence[resolved_slot][2] == EVENT_BAN

        unavailable = set(banned_ids)
        if not slot_is_ban:
            # For picks: also mask out already-picked champions
            unavailable.update(picked_ids)

        # Always mask padding and no-ban sentinel
        unavailable.add(0)
        unavailable.add(NO_BAN_ID)

        avail_mask = torch.zeros(CHAMPION_VOCAB, dtype=torch.bool, device=device)
        for cid in unavailable:
            if 0 <= cid < CHAMPION_VOCAB:
                avail_mask[cid] = True

        # Apply mask — set unavailable logits to -inf
        logits[0][avail_mask] = float("-inf")

        # ── Top-k suggestions ──────────────────────────────────────────────
        probs      = logits[0].softmax(dim=-1)
        top_probs, top_ids = probs.topk(top_k)

        suggestions = [
            {
                "champion_id": top_ids[i].item(),
                "probability": round(top_probs[i].item(), 4),
            }
            for i in range(top_k)
        ]

        # ── Win probability ────────────────────────────────────────────────
        win_prob = torch.sigmoid(win_logit[0]).item()

        return {
            "suggestions":   suggestions,
            "win_prob":      round(win_prob, 4),
            "target_slot":   resolved_slot,
            "is_pick":       not slot_is_ban,
        }

def predict_named(
    model: DraftTransformer,
    events: list[dict],
    domain: int,
    picked_ids: list[int],
    banned_ids: list[int],
    proficiency_map: dict,
    target_slot: int,
    top_k: int = 3,
    device: torch.device = torch.device("cpu"),
):
    result = predict(
        model,
        events,
        domain,
        picked_ids,
        banned_ids,
        target_slot,
        top_k,
        device,
    )
    
    for s in result["suggestions"]:
        s["champion_name"] = saved_map[s["champion_id"]]
        if proficiency_map is not None:
            s["proficiency"] = get_champion_proficiency(proficiency_map, s["champion_id"])
        else:
            s["proficiency"] = None
    return result


if __name__ == "__main__":
    with open("data/annotated_abilities_df.pkl", "rb") as f:
        tag_df = pickle.load(f)
    with open("data/champion_damage_breakdown.pkl", "rb") as f:
        damage_df = pickle.load(f)

    device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    model  = load_model("models", tag_df, damage_df, device)

    partial_events = [
        {"champion_id": 235, "lane": "UNKNOWN"},  # ban 1 — blue
        {"champion_id": 114, "lane": "UNKNOWN"},  # ban 2 — blue
        {"champion_id": 238, "lane": "UNKNOWN"},  # ban 3 — red
    ]

    deeplol_data = {
        "mid": [
            {"champion_id": 103, "games": 3,  "win_rate": 33.33, "ai_score": 51.12},
            {"champion_id": 147, "games": 25, "win_rate": 60.0,  "ai_score": 72.50},
            {"champion_id": 876, "games": 18, "win_rate": 55.0,  "ai_score": 68.30},
        ],
        "support": [
            {"champion_id": 147, "games": 10, "win_rate": 70.0,  "ai_score": 75.00},
        ]
    }

    prof_map = build_proficiency_map(deeplol_data, min_games=3)

    result = predict_named(
        model=model,
        events=partial_events,
        domain=DOMAIN_PRO,
        picked_ids=[],
        banned_ids=[235, 114, 238],
        proficiency_map=prof_map,
        device=device,
        target_slot=4
    )

    print(f"Slot {result['target_slot']} | Win prob: {result['win_prob']:.1%}")
    for s in result["suggestions"]:
        prof = s["proficiency"]
        prof_str = (
            f"games={prof.games} wr={prof.win_rate:.1f}% "
            f"ai={prof.ai_score:.1f} prof={prof.proficiency:.4f}"
            if prof else "no data"
        )
        print(f"  {s['champion_name']:<20} {s['probability']:.1%}  |  {prof_str}")


        