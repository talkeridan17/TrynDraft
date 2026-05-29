# TrynDraft AI Pipeline

This document describes every component in the `model-training/` folder and how to use it end-to-end — from raw match data all the way to the ONNX model running live in the browser.

---

## Directory Structure

```
model-training/
├── checkpoints/           # Exported JSON artifacts (champ_to_id, tags, valid_tags)
├── data/                  # All data artifacts and processing scripts
│   ├── annotated_abilities_df.pkl  # Champion ability → tag annotations
│   ├── champion_damage_breakdown.pkl / .csv  # AD/AP/True damage % per champ
│   ├── champion_map.pkl   # champion_id → champion_name lookup
│   ├── champion_tags.csv  # Per-champion tag list (for RAG explainability)
│   ├── cleaned_matches_df.pkl      # Unified training DataFrame
│   ├── proplay_cleaned.pkl         # Processed pro-play matches
│   ├── match_cleaning.py   # Cleans raw Riot JSON → structured DataFrame
│   ├── unify.py            # Merges pro-play + soloq DataFrames
│   └── utility.py          # Champion name normalization, map loaders
├── models/                # Saved model artifacts
│   ├── base_prediction_model.pt    # PyTorch checkpoint
│   ├── model.onnx                  # ONNX export (deployed to browser)
│   ├── model.onnx.data             # External weights (large tensors)
│   ├── model.json                  # Model metadata (tags, vocab, arch)
│   └── README.md                   # Model card
├── scraping/              # Riot API data collection
│   ├── scraper.py         # High-ELO SoloQ match scraper (rate-limited)
│   └── leaguepedia.py     # Pro-play match scraper (Leaguepedia API)
└── training/              # Model training and export
    ├── train.py            # DraftTransformer definition + training loop
    ├── export_onnx.py      # Export .pt checkpoint → ONNX
    ├── inference.py        # Python inference wrapper
    ├── proficiency.py      # Deeplol champion proficiency scoring
    ├── refresh.py              # ⭐ Full pipeline orchestration script
    ├── compute_role_affinity.py # Computes per-champion role frequencies → role_affinity.json
    └── inference.py            # Python inference wrapper (dev use)
```

---

## Architecture: DraftTransformer

The model is a **Transformer Encoder** that takes a 20-step draft sequence (10 bans + 10 picks) and predicts the optimal next pick/ban.

| Component | Value |
|---|---|
| Architecture | Transformer Encoder |
| Embedding dim (`d_model`) | 256 |
| Attention heads | 8 |
| Encoder layers | 4 |
| FFN dim | 1024 |
| Champion vocab | 1000 |
| Ability tags | 134 binary features |
| Damage features | 3 (AD%, AP%, True%) |
| Parameters | ~5M |
| ONNX size | ~20 MB |

### Input Sequence (20 events)

Each event in the 20-step sequence encodes:

| Feature | Description | Range |
|---|---|---|
| `champion_ids` | Champion ID (0 = padding/empty) | 0–999 |
| `sides` | Team (0=Blue, 1=Red) | 0–1 |
| `phases` | Draft phase | 1–3 |
| `lanes` | Role (TOP/JGL/MID/BOT/SUP/UNK) | 0–5 |
| `event_types` | Ban (0) or Pick (1) | 0–1 |
| `domain` | Match type (Pro=0, SoloQ=1) | 0–1 |

### Outputs

| Output | Description | Shape |
|---|---|---|
| `pick_ban_logits` | Raw logit per champion | `[batch, 1000]` |
| `win_probability_logit` | Blue-side win probability logit | `[batch]` |

### Role Affinity + Proficiency Adjustment (Frontend)

After softmax over `pick_ban_logits`, two post-processing steps are applied:

**1. Role affinity multiplier** (data-driven, never hardcoded):
```
role_mult = role_affinity[champion][target_role]  # 0.0–1.0
adjusted_prob = softmax_prob * role_mult
```
`role_affinity.json` stores per-champion role frequencies computed from pro-play picks. A champion with 0% affinity for the requested role gets a score of 0.

**2. Player proficiency boost** (if Riot ID loaded):
```
final_score = adjusted_prob + (proficiency * 0.1)
```
`proficiency` is computed from the player's Deeplol.gg data:
```
proficiency = 0.50 * ai_score_norm + 0.30 * wr_score + 0.20 * games_score
```

Both steps run entirely in the browser with no backend required.

---

## Training Data

| Dataset | Source | Matches | Period |
|---|---|---|---|
| Pro matches | Leaguepedia (LCK/LPL/LEC/LCS/etc.) | ~60,000 | 2020–2024 |
| SoloQ matches | Riot Match-v5 API (Emerald+) | ~100,000 | 2026 |

Pro matches use the standard pro draft sequence (6+4 bans, 6+4 picks). SoloQ uses the standard ranked sequence (10 bans, then picks B-R-R-B-B-R, R-B-B-R).

Both domains are trained jointly. The model learns a `domain` embedding so it can distinguish pro vs. soloq draft patterns.

### Recency Weighting

Games from older patches are downweighted with exponential decay (half-life = 12 patches, ≈ 6 months):

```python
weight = 0.5 ** (patch_distance / 12.0)
```

### Feature Extraction

Two static feature matrices are baked into the model at export time:

1. **Tag matrix** `[1000, 134]` — binary flags for champion ability tags (crowd control, dive, poke, etc.). Extracted from champion ability descriptions via keyword annotation. Used for RAG-style explainability.
2. **Damage matrix** `[1000, 3]` — (AD%, AP%, True%) per champion from game data. Helps the model reason about team damage composition.

---

## How to Refresh Data and Retrain

### Prerequisites

```bash
cd model-training
python -m venv .venv && source .venv/bin/activate
pip install torch onnx onnxruntime onnxscript pandas numpy tqdm scipy requests python-dotenv psutil
```

Set your Riot API key and key type in `model-training/.env`:
```
RIOT_API_KEY=RGAPI-your-key-here
RIOT_KEY_TYPE=personal   # or "production" for higher rate limits
```

### Full Pipeline (scrape + train + export + deploy)

```bash
python training/refresh.py \
  --platform na1 \
  --tier EMERALD \
  --max-games 5000 \
  --fine-tune \
  --epochs 30
```

This will:
1. Scrape up to 5,000 fresh Emerald+ SoloQ games from `na1`
2. Clean and unify with existing pro-play data
3. Fine-tune the DraftTransformer for 30 epochs from `models/best.pt`
4. Recompute role affinity frequencies → `checkpoints/role_affinity.json`
5. Export to ONNX
6. Copy `model.onnx`, `model.onnx.data`, `model.json`, `role_affinity.json`, `champ_to_id.json`, `tags.json`, `champion_tags.csv` → `frontend/public/models/`
7. Clean up intermediate epoch checkpoints automatically

After this completes, the updated model is immediately active next time you run or build the frontend.

### Retrain on Existing Data (no new scraping)

```bash
python training/refresh.py --skip-scrape --epochs 100
```

### Export Only (no retrain)

```bash
python training/refresh.py --skip-scrape --skip-train
```

### Manual Steps

If you prefer to run steps individually:

```bash
# 1. Scrape new games
python scraping/scraper.py --platform na1 --tier EMERALD --output data/raw_soloq

# 2. Clean + unify
python data/unify.py

# 3. Train
python training/train.py \
  --data data/cleaned_matches_df.pkl \
  --tags data/annotated_abilities_df.pkl \
  --damage data/champion_damage_breakdown.pkl \
  --output models/ \
  --epochs 100

# 4. Export to ONNX
python training/export_onnx.py \
  --checkpoint models/base_prediction_model.pt \
  --output models/model.onnx

# 5. Deploy to frontend
cp models/model.onnx models/model.onnx.data models/model.json ../frontend/public/models/
cp checkpoints/champ_to_id.json checkpoints/tags.json ../frontend/public/models/
cp data/champion_tags.csv ../frontend/public/models/
```

---

## Recommended Refresh Schedule

| Trigger | Action |
|---|---|
| New patch (every ~2 weeks) | `refresh.py --skip-scrape --epochs 30 --fine-tune` |
| Every month | `refresh.py --max-games 20000 --epochs 50 --fine-tune` |
| Major meta shift / large rework | `refresh.py --max-games 50000 --epochs 100` (full retrain) |
| New champion release | Re-extract tags → `refresh.py --skip-scrape --epochs 50` |

---

## Browser Inference (frontendAi.ts)

The frontend loads the ONNX model using `onnxruntime-web` (loaded via CDN) and runs inference entirely client-side — no backend required.

Key files:
- `frontend/src/utils/frontendAi.ts` — ONNX inference + LLM explainability
- `frontend/public/models/model.onnx` — transformer weights
- `frontend/public/models/model.onnx.data` — external weights
- `frontend/public/models/tags.json` — valid tag list for explainability
- `frontend/public/models/champ_to_id.json` — name→id mapping
- `frontend/public/models/champion_tags.csv` — per-champion tag lookup

LLM explainability uses a small quantized Qwen2.5 model (0.5B or 1.5B, user-selectable) loaded from HuggingFace via `@huggingface/transformers` v3. The LLM takes the top-5 ONNX picks + their ability tags and generates a 1-sentence explanation for each.

---

## Player Proficiency (Deeplol.gg)

Players enter their `Name#TAG` Riot ID on the Draft page. The browser calls the Deeplol CDN API directly (no backend needed) to fetch champion stats, then caches them in `localStorage`.

The proficiency score for each champion biases the ONNX softmax score upward by up to +0.1 (10%), giving the player's proven champions a slight edge without overriding the model's draft logic.

Proficiency data is scoped per session and never sent to any server.
