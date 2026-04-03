import json
import torch
import torch.nn as nn
from pathlib import Path
import pickle
import pandas

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
    build_tag_matrix
)

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

device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.mps.is_available() else "cpu")

with open("data/annotated_abilities_df.pkl", "rb") as f:
    annotated_abilities_df = pickle.load(f)

with open("data/champion_damage_breakdown.pkl", "rb") as f:
    champion_damage_breakdown = pickle.load(f)

model = load_model("models", annotated_abilities_df, champion_damage_breakdown, device)
print(model)

