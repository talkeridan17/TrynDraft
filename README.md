# TrynDraft

> AI-powered League of Legends draft assistant — runs entirely in your browser, no account or server required.

<p align="center">
  <img src="frontend/public/logo.svg" alt="TrynDraft Logo" width="80" height="80" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Live-brightgreen" alt="Status"/>
  <img src="https://img.shields.io/badge/React-19-blue" alt="React"/>
  <img src="https://img.shields.io/badge/TypeScript-5.6-blue" alt="TypeScript"/>
  <img src="https://img.shields.io/badge/ONNX-Runtime_Web-orange" alt="ONNX"/>
  <img src="https://img.shields.io/badge/Version-0.7.0--beta-lightgrey" alt="Version"/>
</p>

---

## What is TrynDraft?

TrynDraft is a **fully client-side** League of Legends draft assistant. Open the page, enter your Riot ID (`Name#TAG`), and get AI-powered pick and ban suggestions — no login, no server, no backend.

- **DraftTransformer** — 5M-parameter Transformer trained on ~160K pro + high-ELO matches, runs in-browser via ONNX Runtime Web
- **LLM Explainability** — Qwen2.5 (0.5B / 1.5B) quantized models explain top picks in natural language via Transformers.js
- **Deeplol Proficiency** — Your Riot ID is used to fetch your champion stats from Deeplol and bias recommendations toward your best picks
- **Champion Data** — Always up-to-date via Riot's Data Dragon CDN; no static bundle needed

---

## Quick Start

```bash
git clone https://github.com/talkeridan17/TrynDraft.git
cd TrynDraft/frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). That's it.

To build for production:

```bash
npm run build   # outputs to frontend/dist/
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for deploying to Vercel or Netlify (5 minutes, free tier).

---

## Project Map

This is your navigation hub. Every major aspect of the project is listed below with a link to the relevant file or folder.

### Frontend — [frontend/](frontend/)

The entire app lives here. React 19 + TypeScript + Vite + Tailwind.

| What | Where |
|------|-------|
| App entry & routes | [frontend/src/App.tsx](frontend/src/App.tsx) |
| Draft page (main UI) | [frontend/src/pages/DraftPage.tsx](frontend/src/pages/DraftPage.tsx) |
| Settings page | [frontend/src/pages/SettingsPage.tsx](frontend/src/pages/SettingsPage.tsx) |
| Layout + Nav | [frontend/src/components/layout/](frontend/src/components/layout/) |
| Draft components | [frontend/src/components/drafting/](frontend/src/components/drafting/) |
| AI inference (ONNX + LLM + Deeplol) | [frontend/src/utils/frontendAi.ts](frontend/src/utils/frontendAi.ts) |
| Service layer (API wrapper) | [frontend/src/utils/api.ts](frontend/src/utils/api.ts) |
| Draft state (Zustand) | [frontend/src/store/useDraftStore.ts](frontend/src/store/useDraftStore.ts) |
| ONNX model + metadata | [frontend/public/models/](frontend/public/models/) |

**Key flows:**
- User enters `Name#TAG` on Draft page → `fetchAndStoreDeeplolByRiotIds()` stores proficiency in `localStorage`
- On any draft pick → `runFrontendRanking()` loads ONNX model, scores all champions, adjusts by proficiency
- "Explain" button → `runFrontendExplainability()` runs Qwen2.5 in-browser

### AI Model — [model-training/](model-training/)

Everything needed to understand, retrain, and re-export the DraftTransformer.

| What | Where |
|------|-------|
| Full architecture & pipeline docs | [model-training/PIPELINE.md](model-training/PIPELINE.md) |
| ONNX model + base PyTorch model | [model-training/models/](model-training/models/) |
| Training script | [model-training/training/train.py](model-training/training/train.py) |
| ONNX export script | [model-training/training/export_onnx.py](model-training/training/export_onnx.py) |
| Full refresh pipeline (scrape → train → export → deploy) | [model-training/training/refresh.py](model-training/training/refresh.py) |
| Proficiency computation | [model-training/training/proficiency.py](model-training/training/proficiency.py) |
| Scraping (pro-play + SoloQ) | [model-training/scraping/](model-training/scraping/) |
| Training data (pickles, CSVs) | [model-training/data/](model-training/data/) |
| Champion/tag lookup tables | [model-training/checkpoints/](model-training/checkpoints/) |

**To retrain the model** (requires Riot API key):

```bash
cd model-training
python training/refresh.py --riot-key $RIOT_API_KEY --platform na1
```

See [model-training/PIPELINE.md](model-training/PIPELINE.md) for full instructions.

### Deployment — [DEPLOYMENT.md](DEPLOYMENT.md)

Static site deployment. No backend needed. Read this when you're ready to go live.

### Backend — [backend/](backend/)

The FastAPI backend from the original architecture. **Currently dormant** — the app runs fully client-side and does not need this. It is kept for potential future use (saved drafts, team history). Do not deploy it or run CI against it.

### Docs & Planning

| What | Where |
|------|-------|
| Contributing guidelines | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security policy | [SECURITY.md](SECURITY.md) |
| Code of conduct | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |
| Wiki (setup, branching, FAQ) | [docs/wiki/](docs/wiki/) |
| Historical planning | [planning/](planning/) |

---

## CI/CD

CI runs on every push to `main` and `dev`: lints and builds the frontend. See [.github/workflows/ci.yml](.github/workflows/ci.yml).

Auto-deploy to Vercel on merge to `main` can be enabled — see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Roadmap

| Status | Item |
|--------|------|
| ✅ Done | DraftTransformer ONNX, full client-side inference |
| ✅ Done | Deeplol Riot ID proficiency, cached in localStorage |
| ✅ Done | SoloQ + Clash draft sequences |
| ✅ Done | LLM explainability (Qwen2.5 in-browser, Web Worker) |
| ✅ Done | Role affinity system (data-driven, auto-refreshes) |
| ✅ Done | SoloQ / Clash mode toggle on draft page |
| ✅ Done | Clash: per-slot IGN lookup for all 10 players |
| ✅ Done | op.gg build link (updates live on hover) |
| ✅ Done | Live at [tryndraft.vercel.app](https://tryndraft.vercel.app) |
| ✅ Done | Automated weekly model refresh on patch drop |
| 🔄 Now | Production Riot API key (application submitted) |
| 🟡 Next | Large-scale fresh SoloQ data collection + retrain (no pro data) |
| 🟠 Soon | Custom domain (tryndraft.com) |
| 🟠 Soon | LLM explainability improvements (currently deprioritised) |

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, TypeScript 5.6, Vite, TailwindCSS, Zustand |
| AI (in-browser) | ONNX Runtime Web, Transformers.js v3 (Qwen2.5) |
| Data sources | Riot Data Dragon CDN, Deeplol CDN (`b2c-api-cdn.deeplol.gg`) |
| Model training | Python 3.12, PyTorch, ONNX export |
| CI | GitHub Actions (lint + build) |
| Hosting | Vercel / Netlify (static) |

---

## Acknowledgments

- **Rohan Cherukuri** — DraftTransformer model, frontend AI integration, Deeplol proficiency system
- **Riot Games** — Riot API, Data Dragon
- **HuggingFace** — Transformers.js, model hosting
- **Deeplol.gg** — Player stats CDN

**Built by [Idan Talker](https://github.com/talkeridan17) & [Rohan Cherukuri](https://github.com/greenden007)**

---

*TrynDraft is not endorsed by Riot Games and does not reflect the views or opinions of Riot Games, Inc. League of Legends and Riot Games are trademarks of Riot Games, Inc.*
