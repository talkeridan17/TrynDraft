# TrynDraft — Deployment Guide

**Last Updated:** 2026-05-29

TrynDraft is a **static frontend-only application**. There is no backend — the ONNX model, LLM, and Deeplol proficiency lookup all run client-side in the browser.

---

## Architecture

```
┌────────────────────────────────────────────────────┐
│             Browser (React + ONNX Runtime Web)     │
│                                                    │
│  ┌──────────────┐  ┌──────────────┐               │
│  │  ONNX Model  │  │  Qwen2.5 LLM │               │
│  │  (~20MB)     │  │  (HuggingFace│               │
│  └──────────────┘  └──────────────┘               │
│                                                    │
│  ┌──────────────┐  ┌──────────────┐               │
│  │  Data Dragon │  │  Deeplol CDN │               │
│  │  (champions) │  │  (player stats)│              │
│  └──────────────┘  └──────────────┘               │
└────────────────────────────────────────────────────┘
        ↑ served as static files from Vercel
```

No database, no auth, no server process.

---

## Live Deployment (Vercel)

The app is live at **https://tryndraft.vercel.app**

Auto-deploys on every push to `main` via Vercel's native GitHub integration.

### Re-deploying from scratch

1. Go to [vercel.com](https://vercel.com) → New Project → import `talkeridan17/TrynDraft`
2. Set **Root Directory** to `frontend`
3. Framework auto-detected as Vite
4. Click Deploy

No environment variables required for the frontend.

---

## Local Development

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

Build for production:
```bash
npm run build   # outputs to frontend/dist/
```

---

## Custom Domain

To add `tryndraft.com` (or any domain):

1. Buy the domain (Namecheap, Google Domains, etc.)
2. In Vercel: Project Settings → Domains → Add domain
3. Copy the DNS records Vercel provides
4. Paste into your domain registrar's DNS settings
5. Live within 10–30 minutes (DNS propagation)

TLS is automatic via Let's Encrypt.

---

## CI/CD (GitHub Actions)

`.github/workflows/ci.yml` runs on every push to `dev` or `main`:
- Lint (`npm run lint`)
- Build (`npm run build`)

Vercel handles deployment automatically via GitHub integration — the CI action deploy step is kept as a placeholder for future use.

`.github/workflows/model-refresh.yml` runs every Wednesday:
- Detects new LoL patch via Data Dragon
- Scrapes fresh high-ELO games
- Opens a PR to `dev` with new data for local retraining

---

## Model Updates

When the DraftTransformer is retrained:

```bash
cd model-training
source .venv/bin/activate
python training/refresh.py --fine-tune --epochs 30
# Automatically copies updated ONNX + role_affinity.json to frontend/public/models/
```

Commit `frontend/public/models/` → push to `dev` → merge to `main` → Vercel deploys → users get the new model on next page load.

See [model-training/PIPELINE.md](model-training/PIPELINE.md) for full training docs.

---

## Deployment Timeline

| Date | Milestone |
|---|---|
| 2026-04-18 | DraftTransformer model complete |
| 2026-05-25 | Fully client-side, auth removed, Deeplol integrated |
| 2026-05-29 | Live at tryndraft.vercel.app, Riot production key applied |
| Pending | Production Riot API key approved |
| Pending | Large-scale SoloQ retrain, custom domain |
