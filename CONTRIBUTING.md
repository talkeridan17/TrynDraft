# Contributing to TrynDraft

Thank you for your interest in contributing! This document explains how to get started.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the dev environment: `cd frontend && npm install && npm run dev`
4. Create a branch for your work from `dev`

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production — auto-deploys to Vercel |
| `dev` | Development — all PRs target here |

Create branches from `dev`:

| Pattern | Purpose | Example |
|---------|---------|---------|
| `feat/*` | New features | `feat/champion-filter` |
| `bug/*` | Bug fixes | `bug/cursor-fix` |
| `task/*` | Refactors, docs | `task/update-readme` |

**Workflow:** branch from `dev` → PR to `dev` → periodically merge `dev` to `main`

## Commit Messages

Use conventional commits:
```
feat: add champion search filter
fix: resolve cursor position bug
docs: update pipeline documentation
refactor: simplify draft state management
chore: update dependencies
```

## Pull Requests

1. Target `dev` (not `main`)
2. Describe what changed and why
3. Ensure CI passes (lint + build)
4. No `console.log` or debug statements
5. No hardcoded secrets or credentials

## Code Standards

### TypeScript (Frontend)
- Use TypeScript strict mode — avoid `any`
- Functional components with hooks
- Define interfaces for props and state

### Python (Model Training)
- Follow PEP 8
- Use type hints for function signatures
- Run from the `model-training/` directory with the `.venv` active

## Project Structure

### Frontend (`frontend/src/`)
- `pages/` — page-level components (DraftPage, SettingsPage)
- `components/` — reusable UI components
- `utils/frontendAi.ts` — ONNX inference + LLM + Deeplol
- `utils/api.ts` — service layer
- `store/useDraftStore.ts` — Zustand draft state

### Model Training (`model-training/`)
- `training/refresh.py` — full pipeline (scrape → train → export → deploy)
- `training/train.py` — DraftTransformer definition + training loop
- `training/export_onnx.py` — PyTorch → ONNX export
- `scraping/scraper.py` — Riot API data collection
- `data/unify.py` — merge pro-play + SoloQ DataFrames

### Adding a New Page
1. Create component in `frontend/src/pages/`
2. Add route in `frontend/src/App.tsx`

### Adding a New Component
1. Create in `frontend/src/components/common/` (shared) or `drafting/` (draft-specific)

## Running Linters

```bash
cd frontend
npm run lint
npm run build   # catches TypeScript errors
```

## Questions?

Open an issue or start a discussion on GitHub.

## License

By contributing, you agree your contributions will be licensed under the MIT License.
