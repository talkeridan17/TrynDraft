# TrynDraft Wiki

Welcome to the TrynDraft wiki — your guide to the AI-powered League of Legends draft assistant.

## What is TrynDraft?

TrynDraft is a fully client-side League of Legends draft tool. Open the page, enter your Riot ID, and get AI-powered pick and ban suggestions — no login, no server, no backend.

- **DraftTransformer** — 5M-parameter Transformer trained on ~63K pro matches, runs in-browser via ONNX Runtime Web
- **Role Affinity** — data-driven per-champion role frequencies ensure recommendations stay on-role
- **Deeplol Proficiency** — enter your Riot ID to bias recommendations toward your champion pool
- **LLM Explainability** — Qwen2.5 (0.5B/1.5B) explains top picks in natural language, runs in a Web Worker

**Live at:** https://tryndraft.vercel.app

## Quick Links

| Page | Description |
|------|-------------|
| [Development Setup](Development-Setup) | Set up the local dev environment |
| [User Guide](User-Guide) | How to use TrynDraft |
| [Contributing](Contributing) | Guidelines for contributors |
| [Branching Standards](Branching-Standards) | Git workflow and branch naming |
| [FAQ](FAQ) | Frequently asked questions |

## Current Version

**Version:** 0.7.0-beta  
**Status:** Live

### What's Working
- Full SoloQ + Clash draft interface (bans + picks)
- DraftTransformer ONNX running in-browser
- Role-aware recommendations (data-driven affinity)
- Deeplol Riot ID proficiency integration
- LLM explainability (Qwen2.5, runs in Web Worker)
- Automated weekly model refresh on patch drop

### Coming Soon
- Settings page (SoloQ/Clash team proficiency)
- Custom domain (tryndraft.com)
- Larger-scale model retrain with production API key

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 19, TypeScript, Vite, TailwindCSS, Zustand |
| **AI (in-browser)** | ONNX Runtime Web, Transformers.js v3 (Qwen2.5) |
| **Data sources** | Riot Data Dragon CDN, Deeplol CDN |
| **Model training** | Python 3.12, PyTorch, ONNX export |
| **Hosting** | Vercel (static) |

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/talkeridan17/TrynDraft/issues)

---

**Last Updated:** 2026-05-29
