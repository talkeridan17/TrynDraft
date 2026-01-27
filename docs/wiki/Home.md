# TrynDraft Wiki

Welcome to the TrynDraft wiki - your comprehensive guide to the AI-powered League of Legends drafting assistant.

## What is TrynDraft?

TrynDraft is an intelligent drafting tool that helps League of Legends players make better pick and ban decisions. It combines:

- **Neural Network Recommendations**: A 50-feature PyTorch model that scores champions based on draft state, matchups, synergies, and user preferences
- **LLM Analysis**: Strategic analysis powered by Qwen2.5-72B (or rule-based fallback) that explains why picks are good and provides gameplan advice
- **User Preferences**: Personalized recommendations based on your champion pool, role, and proficiency ratings

## Quick Links

| Page | Description |
|------|-------------|
| [Development Setup](Development-Setup) | How to set up the development environment |
| [User Guide](User-Guide) | How to use TrynDraft effectively |
| [Contributing](Contributing) | Guidelines for contributing to the project |
| [Branching Standards](Branching-Standards) | Git workflow and branch naming conventions |
| [FAQ](FAQ) | Frequently asked questions |

## Current Version

**Version:** 0.5.0-alpha
**Status:** Active Development (Phase 3 - AI Integration)

### What's Working
- Complete draft interface with pick/ban phases
- Manual cursor control (click any slot to select)
- Drag-and-drop champion swapping
- Champion search and filtering
- Clickable recommendations in LLM panel
- User authentication and profiles
- Champion pool management with proficiency ratings
- Neural network recommendations
- LLM/rule-based analysis

### In Progress
- Data scraping pipeline (MOBAFire, LoLalytics)
- LLM fine-tuning with LoL-specific content
- Real matchup data integration

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 19, TypeScript, Vite, TailwindCSS, Zustand |
| **Backend** | FastAPI, Python 3.12, SQLAlchemy, PyTorch |
| **AI/ML** | PyTorch NN (50 features), HuggingFace Qwen2.5-72B |
| **Database** | SQLite (dev), PostgreSQL (prod) |
| **Assets** | Riot Data Dragon, Community Dragon |

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/your-repo/TrynDraft/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/TrynDraft/discussions)
- **Documentation**: This wiki + [README.md](https://github.com/your-repo/TrynDraft/blob/main/README.md)

---

**Last Updated:** 2026-01-26
