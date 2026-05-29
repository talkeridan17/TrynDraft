# TrynDraft: League of Legends Draft Prediction Model

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Model Size](https://img.shields.io/badge/Size-20MB-green.svg)]()
[![ONNX](https://img.shields.io/badge/Format-ONNX-blue.svg)]()

A lightweight transformer-based model for predicting optimal champion picks and bans in League of Legends draft phase, with win probability estimation.

## Model Description

**TrynDraft** is a neural network trained on professional and high-level solo queue matches to predict:
- **Next pick/ban** suggestions (champion selection)
- **Blue side win probability** given the current draft state

### Architecture

| Component            | Specification                  |
| -------------------- | ------------------------------ |
| **Architecture**     | Transformer Encoder            |
| **Embedding Dim**    | 256 (`d_model`)                |
| **Attention Heads**  | 8                              |
| **Layers**           | 4                              |
| **FFN Dim**          | 1024                           |
| **Champion Vocab**   | 1000                           |
| **Tag Features**     | 134 binary tags                |
| **Damage Features**  | 3 dimensions (AD%, AP%, True%) |
| **Total Parameters** | ~5M                            |
| **Model Size**       | ~20 MB (ONNX)                  |

### Input Features

The model ingests a **20-step draft sequence** (10 bans + 10 picks):

| Feature        | Description                                                   | Range               |
| -------------- | ------------------------------------------------------------- | ------------------- |
| `champion_ids` | Champion ID for each event                                    | 0-999 (0 = padding) |
| `sides`        | Team side (0=Blue, 1=Red)                                     | 0-1                 |
| `phases`       | Draft phase (1, 2, or 3)                                      | 0-2                 |
| `lanes`        | Assigned lane (TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY, UNKNOWN) | 0-5                 |
| `event_types`  | Ban (0) or Pick (1)                                           | 0-1                 |
| `domain`       | Match type (Pro=0, SoloQ=1)                                   | 0-1                 |

### Outputs

| Output                  | Description                        | Shape           |
| ----------------------- | ---------------------------------- | --------------- |
| `pick_ban_logits`       | Logits for next champion selection | `[batch, 1000]` |
| `win_probability_logit` | Blue side win probability logit    | `[batch]`       |

## How to Use

### With ONNX Runtime Web (Browser)

```javascript
import * as ort from 'onnxruntime-web';

// Load model
const session = await ort.InferenceSession.create(
  'https://huggingface.co/yourname/tryndraft/resolve/main/model.onnx'
);

// Prepare input (example: empty draft)
const batchSize = 1;
const seqLen = 20;

const feeds = {
  champion_ids: new ort.Tensor('int64', new BigInt64Array([...]), [batchSize, seqLen]),
  sides: new ort.Tensor('int64', new BigInt64Array([...]), [batchSize, seqLen]),
  phases: new ort.Tensor('int64', new BigInt64Array([...]), [batchSize, seqLen]),
  lanes: new ort.Tensor('int64', new BigInt64Array([...]), [batchSize, seqLen]),
  event_types: new ort.Tensor('int64', new BigInt64Array([...]), [batchSize, seqLen]),
  domain: new ort.Tensor('int64', new BigInt64Array([0n]), [batchSize]),
};

// Run inference
const results = await session.run(feeds);
const logits = results.pick_ban_logits.data;
const winProb = 1 / (1 + Math.exp(-results.win_probability_logit.data[0]));
```

### With ONNX Runtime (Python)

```python
import onnxruntime as ort
import numpy as np

session = ort.InferenceSession("model.onnx")

inputs = {
    "champion_ids": np.zeros((1, 20), dtype=np.int64),
    "sides": np.zeros((1, 20), dtype=np.int64),
    "phases": np.zeros((1, 20), dtype=np.int64),
    "lanes": np.zeros((1, 20), dtype=np.int64),
    "event_types": np.zeros((1, 20), dtype=np.int64),
    "domain": np.array([0], dtype=np.int64),
}

logits, win_logit = session.run(None, inputs)
win_prob = 1 / (1 + np.exp(-win_logit))
```

### With PyTorch (Original Implementation)

```python
from train import DraftTransformer, build_damage_matrix, build_tag_matrix

model = DraftTransformer(num_tags=134, d_model=256, num_layers=4)
model.load_state_dict(torch.load("base_prediction_model.pt")["model"])
model.eval()
```

## Training Data

| Dataset           | Source                                          | Matches  | Time Period |
| ----------------- | ----------------------------------------------- | -------- | ----------- |
| **Pro Matches**   | Professional leagues (LCK, LPL, LEC, LCS, etc.) | ~60,000  | 2020-2024   |
| **SoloQ Matches** | High ELO ranked games (Emerald+)                | Pending production key | 2026 |

### Data Features

- **Champion tags**: 134 ability/gameplay tags extracted from ability descriptions
- **Damage profile**: Physical/Magic/True damage percentages per champion
- **Recency weighting**: Recent patches weighted more heavily
- **Game length**: Used as confidence weight (longer games → more draft-determined)

## Training Procedure

### Hyperparameters

| Parameter     | Value            |
| ------------- | ---------------- |
| Optimizer     | AdamW            |
| Learning Rate | 1e-4             |
| Weight Decay  | 0.05             |
| Batch Size    | 64               |
| Epochs        | 100              |
| Dropout       | 0.1              |
| LR Schedule   | Cosine Annealing |

### Loss Function

```
Loss = PickBanLoss(logits, target) + 0.1 × BCEWithLogitsLoss(win_pred, actual_win)
```

The pick/ban loss uses **inverse frequency weighting** to balance rare vs. popular champions.

## Limitations & Biases

1. **Meta-dependent**: Model performance degrades significantly 2-3 patches after training data ends
2. **No player skill consideration**: Predictions are draft-only, not accounting for individual player proficiency (use RAG/deeplol.gg for that)
3. **Pro vs SoloQ gap**: Model trained primarily on coordinated pro drafts; solo queue predictions are less reliable
4. **Regional bias**: Training data skewed toward major regions (KR, CN, EU, NA)
5. **Champion updates**: Reworked champions may have outdated tag/damage features until re-extracted

## Ethical Considerations

- This tool is intended for **educational purposes** and **casual assistance**
- Using automated draft assistance in ranked games may violate Riot Games' Terms of Service
- Model predictions should not replace game knowledge or personal judgment

## Full Pipeline

This model is designed to work as part of the TrynDraft system:

```
┌─────────────────────────────────────────────────────────────┐
│  TrynDraft Pipeline                                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Deeplol.gg │───▶│  Proficiency │───▶│   This Model │  │
│  │   API       │    │    Lookup     │    │ (ONNX)       │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                   │         │
│  ┌────────────────────────────────────────────────┘         │
│  ▼                                                          │
│  ┌──────────────┐    ┌──────────────┐                      │
│  │  Prediction  │───▶│    Qwen      │                      │
│  │  Results     │    │  Explanation │                      │
│  └──────────────┘    └──────────────┘                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

- **This model**: Core pick/ban + win probability (this repo)
- **Proficiency**: Player champion skill lookup (separate RAG component)
- **Qwen 0.5B**: Natural language explanation generation ([separate loading](explainability.js))

## Citation

```bibtex
@misc{tryndraft2024,
  title = {TrynDraft: Transformer-based League of Legends Draft Prediction},
  author = {Rohan Cherukuri},
  year = {2026},
  howpublished = {\url{https://huggingface.co/yourname/tryndraft-model}},
  note = {ONNX model for draft phase prediction}
}
```

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Acknowledgments

- Training data sourced from [Riot Games API](https://developer.riotgames.com/)
- Champion ability data from [CommunityDragon](https://github.com/CommunityDragon/CDTB)
- Transformers.js for browser-based LLM inference
