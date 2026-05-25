import json
import torch
import pickle
from pathlib import Path
import sys
from explainability import build_suggestion_contexts, contexts_to_json
from proficiency import build_proficiency_map
from inference import predict_named, DOMAIN_PRO, load_model
from train import build_damage_matrix, build_tag_matrix

sys.path.insert(0, str(Path(__file__).parent.parent))
from data.utility import load_champion_map, reverse_champion_map

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

damage_matrix_tensor = build_damage_matrix(damage_df)
tag_matrix, valid_tags = build_tag_matrix(tag_df, damage_df)

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

# Use your existing variables from inference testing
contexts = build_suggestion_contexts(
    result=result,
    events=partial_events,
    domain=DOMAIN_PRO,
    id_to_name=load_champion_map(),
    tag_matrix=tag_matrix,
    damage_matrix=damage_matrix_tensor,
    valid_tags=valid_tags,
    proficiency_map=prof_map,
)

serialized = contexts_to_json(contexts)
print(json.dumps(serialized[0], indent=2))