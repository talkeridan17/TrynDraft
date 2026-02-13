# TrynDraft - Current Development Status

**Last Updated:** 2026-02-12
**Version:** 0.8.2-beta

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

## Recent Bug Fixes (2026-02-12)

### Critical Bugs Fixed ✅
1. **Win Rate Display Bug** - FIXED
   - **Problem:** Database stores win_rate as basis points (10000 = 100%), but code divided by 100 instead of 10000
   - **Symptom:** Transparency window showed "10000%" or "4773%" instead of "100%" or "47.7%"
   - **Fix:** Changed `win_rate / 100` to `win_rate / 10000` in recommendations.py:544
   - **Location:** [backend/app/api/v1/endpoints/recommendations.py:544-545](../backend/app/api/v1/endpoints/recommendations.py)

2. **Draft Stats Damage Split Bug** - FIXED
   - **Problem:** Checking `if (ad)` instead of `if (ad !== undefined)` caused 0 values to show fallback "50%"
   - **Symptom:** Full AD team showed "100% AD, 50% AP" instead of "100% AD, 0% AP"
   - **Fix:** Changed truthiness check to explicit `!== undefined` check
   - **Location:** [frontend/src/pages/DraftPage.tsx:969,976](../frontend/src/pages/DraftPage.tsx)

3. **Picker Alphabetical Order Bug** - ✅ FIXED
   - **Problem:** Champions showed in alphabetical order instead of NN-sorted order
   - **Root Cause:** Scraped data missing for current patch (16.3.1), only had data for 16.2
   - **Symptom:** All champions had `role_games=0` → all got score 0.02 → sorted by database order (alphabetical)
   - **Fix:** Added automatic fallback to latest available patch when requested patch not found
   - **Location:** [backend/app/api/v1/endpoints/recommendations.py:75-150](../backend/app/api/v1/endpoints/recommendations.py)
   - **Status:** ✅ Working - now shows correct NN scores (Ivern, Briar, Graves for Jungle/Platinum)

### Automated Workflows Status
4. **Automated Scraping** ✅ CREATED
   - Created `.github/workflows/scrape-and-train.yml`
   - Runs every 6 hours via cron: `0 */6 * * *`
   - Detects latest patch, checks if already scraped, runs scrapers for all ranks
   - Auto-commits scraped data and retrained models to repo
   - **Status:** Ready for testing (user should manually trigger first)

5. **Text Data Scraper** ✅ TESTED
   - Created `scripts/scrape_llm_text.py` for LLM training data
   - Logs to `logs/text/scrape_TIMESTAMP.log`
   - Outputs to `training_data/text_data.jsonl`
   - **Status:** Working, tested with 10 champions

### Remaining Issues
6. **Data Weighting Strategy** ⚠️
   - Not implemented for old vs new patches
   - Should decrease value of old patch data while keeping it
   - **Action Required:** Implement exponential decay or similar

7. **Login Issue** ⚠️
   - User reports can't log in
   - Auth code looks correct
   - **Needs Verification:** Backend running? .env configured?

8. **Deployment Blocked** ❌
   - Railway build timeouts due to PyTorch size (2GB+)
   - **Solutions:** CPU-only PyTorch OR different platform

---

**Project Status:** Beta Ready (Deployment Paused)
**Next Milestone:** Automated Workflows + Deployment
**Blocking Issues:** GitHub Actions workflows, Railway deployment
