# TrynDraft - Current Development Status

**Last Updated:** 2026-02-02
**Version:** 0.8.0-beta

---

## System Status

| Component | Status | Notes |
|-----------|--------|-------|
| **Frontend** | Ready | React 19 + TypeScript + Vite |
| **Backend** | Ready | FastAPI + SQLAlchemy |
| **Neural Network** | Trained | All 10 ranks + combined (11 models) |
| **Stats Scraper** | Complete | Patch 16.2, all ranks, 30K+ matches |
| **LLM Integration** | Placeholder | Disabled for beta (cost management) |

---

## Data Status

### Scraped Data (Patch 16.2)
| Rank | Matches | Champions | Status |
|------|---------|-----------|--------|
| IRON | 451 | 172 | Complete |
| BRONZE | 1,244 | 172 | Complete |
| SILVER | 2,984 | 172 | Complete |
| GOLD | 3,252 | 172 | Complete |
| PLATINUM | 3,820 | 172 | Complete |
| EMERALD | 3,868 | 172 | Complete |
| DIAMOND | 4,796 | 172 | Complete |
| MASTER | 5,196 | 172 | Complete |
| GRANDMASTER | 2,631 | 172 | Complete |
| CHALLENGER | 2,144 | 172 | Complete |
| **Total** | **30,386** | 172 | |

### Trained Models
All 11 models trained (2026-02-02):
- Per-rank: IRON through CHALLENGER (10 models)
- Combined: Fallback model for all ranks
- Validation loss: ~0.001 (excellent)

---

## Neural Network Architecture

```
Input (48 features)
    │
    ▼
┌─────────────────────────┐
│ Linear(48, 128) + ReLU  │
│ BatchNorm + Dropout(0.3)│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Linear(128, 64) + ReLU  │
│ BatchNorm + Dropout(0.3)│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Linear(64, 32) + ReLU   │
│ BatchNorm + Dropout(0.3)│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Linear(32, 1) + Sigmoid │
│ Output: Score (0-1)     │
└─────────────────────────┘

Key Features (48 total):
- Champion base stats (4)
- Meta stats: win rate, pick rate, ban rate (3)
- Role one-hot encoding (5)
- Role flexibility (1)
- User proficiency (1)
- Draft phase context (2)
- Matchup scores vs 5 enemies (5)
- Synergy scores with 4 allies (4)
- Team composition (6)
- Champion tags (8)
- Meta position (3)
- TARGET ROLE-SPECIFIC (6) - Critical for role recommendations
```

---

## Recent Changes (2026-02-02)

### Bug Fixes
- Fixed damage split calculation (was showing 50/50)
- Fixed matchup data lookup (role-nested structure)
- Fixed 0-games-in-role champions appearing in recommendations (95% penalty)
- Fixed NN matchup win rate lookup

### Improvements
- Trained all 11 NN models
- Simplified matchup dropdown UI
- Added matchupOverride to useEffect dependencies
- Consolidated documentation

### Infrastructure & Security
- Created GitHub Actions workflow for automated scraping & training
- Fixed backend Dockerfile (removed --reload, added workers)
- Fixed frontend Dockerfile (npm ci order for build)
- Created .env.example files for backend and frontend
- Verified security: SECRET_KEY from environment, no hardcoded secrets

### Documentation
- Created DEPLOYMENT_STRATEGY.md (deployment + NN update strategy)
- Created train_nn.py CLI script
- Updated CURRENT_STATUS.md

---

## Deployment Checklist

### Ready for Beta Launch
- [x] Core draft tool working
- [x] NN recommendations functional for all ranks
- [x] Role-aware recommendations
- [x] Matchup-aware recommendations
- [x] User champion pool integration
- [x] Profile/preferences saved
- [x] Damage split calculation
- [x] Stats bar at draft completion
- [x] Security: SECRET_KEY from environment variables
- [x] Docker configuration production-ready
- [x] GitHub Actions for automated scraping/training
- [x] .env.example files created

### Pending (Post-Beta)
- [ ] LLM integration (cost analysis needed)
- [ ] WebSocket for live drafts
- [ ] Pro play data integration
- [ ] Mobile responsive improvements

---

## Quick Start Commands

```bash
# Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev

# Train NN models
cd backend
python scripts/train_nn.py --all

# Scrape stats
cd backend
python scripts/run_scrapers.py all-ranks

# Check training status
python scripts/train_nn.py --status
```

---

## Project Structure

```
TrynDraft/
├── frontend/              # React 19 + Vite
├── backend/
│   ├── app/               # FastAPI application
│   │   ├── api/v1/        # REST endpoints
│   │   └── services/      # Business logic
│   ├── models/            # Trained NN models (11)
│   ├── scraped_data/      # Riot API data
│   └── scripts/           # CLI tools
├── docs/                  # Documentation
│   └── DEPLOYMENT_STRATEGY.md
├── planning/              # Planning docs
│   └── CURRENT_STATUS.md
└── logs/                  # Application logs
    ├── stats/
    ├── text/
    └── training/
```

---

**Project Status:** Beta Ready
**Next Milestone:** Production Deployment
