# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.7.x   | :white_check_mark: |
| < 0.7   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by opening a private security advisory on GitHub.

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours.

---

## Architecture & Security Model

TrynDraft is a **fully client-side application**. There is no backend server, no database, no user accounts, and no authentication. All AI inference runs in the browser via ONNX Runtime Web and Transformers.js.

This means:
- No user credentials are stored anywhere
- No personal data is sent to TrynDraft's servers
- No server-side attack surface exists

---

## Data Handling

### What runs in the browser
- DraftTransformer ONNX model (~20MB, loaded once and cached)
- Qwen2.5 LLM via Transformers.js (optional, loaded on demand)
- Champion data from Riot's Data Dragon CDN (public)
- Deeplol proficiency stats fetched client-side (public CDN)

### What is stored locally
- Deeplol champion proficiency data (`localStorage`)
- Draft settings and preferences (`localStorage`)
- Nothing is ever sent to TrynDraft's infrastructure

### Third-party data sources
- **Riot Data Dragon CDN** — public champion data, no key required
- **Deeplol CDN** (`b2c-api-cdn.deeplol.gg`) — public player stats by Riot ID

---

## Model Training Pipeline Security

The `model-training/` directory contains a Python pipeline for refreshing the AI model. This is a developer-only tool, not part of the deployed app.

### Secrets used in training pipeline only
- `RIOT_API_KEY` — stored in `model-training/.env` (gitignored) and GitHub Actions Secrets
- Never committed to version control
- Never exposed to end users

### Gitignore
```
model-training/.env
model-training/.venv/
model-training/models/*.pt
model-training/data/*.pkl
```

---

## Dependencies

Key client-side dependencies and their security properties:

- **React 19** — XSS-safe by default via JSX escaping
- **ONNX Runtime Web** — sandboxed WASM execution
- **Transformers.js** — runs entirely in browser, no external inference calls

Run `npm outdated` in `frontend/` regularly to check for updates.

---

## Contact

For security concerns, open a private security advisory on GitHub.

**Last Updated:** 2026-05-29
