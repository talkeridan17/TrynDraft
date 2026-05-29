# Development Setup

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | Any | `git --version` |

Python is only needed if you plan to retrain the model (see [model-training/PIPELINE.md](../../model-training/PIPELINE.md)).

## Frontend (the app)

```bash
git clone https://github.com/talkeridan17/TrynDraft.git
cd TrynDraft/frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # production build → frontend/dist/
npm run lint       # ESLint check
```

## Model retraining (optional)

See [model-training/PIPELINE.md](../../model-training/PIPELINE.md) for the full pipeline. Quick summary:

```bash
cd model-training
# requires Python 3.12+ and a Riot API key
pip install -r ../backend/requirements.txt  # shared deps
python training/refresh.py --riot-key $RIOT_API_KEY --platform na1
```

The refresh script scrapes data, retrains the model, exports ONNX, and copies the result to `frontend/public/models/` automatically.

## Deployment

See [DEPLOYMENT.md](../../DEPLOYMENT.md) for static site deployment (Vercel / Netlify).
