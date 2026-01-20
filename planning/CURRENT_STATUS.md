# TrynDraft - Current Development Status

**Last Updated:** 2026-01-16
**Version:** 0.5.0-alpha

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                            │
│  React 19 + TypeScript + Vite + TailwindCSS + Zustand      │
│  • Draft Interface    • Profile Page    • Champion Picker  │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                         BACKEND                             │
│              FastAPI + Python 3.12 + SQLAlchemy            │
├─────────────────────────────────────────────────────────────┤
│ SERVICES                                                    │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────────┐  │
│ │  NN Service   │ │  LLM Service  │ │  Stats Scraper   │  │
│ │  (PyTorch)    │ │  (Mistral 7B) │ │  (LoLalytics)    │  │
│ └───────────────┘ └───────────────┘ └───────────────────┘  │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────────┐  │
│ │  Text Scraper │ │  Scheduler    │ │  Draft Logic     │  │
│ │  (MOBAFire)   │ │  (APScheduler)│ │  (Validation)    │  │
│ └───────────────┘ └───────────────┘ └───────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│ STORAGE                                                     │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│ │ PostgreSQL  │ │    Redis    │ │  File Storage          ││
│ │ (Database)  │ │   (Cache)   │ │  (Models, Scraped Data)││
│ └─────────────┘ └─────────────┘ └─────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Completed Features

### Frontend (React 19 + TypeScript + TailwindCSS)

#### Draft Interface
- [x] Complete draft UI with Blue/Red team boards
- [x] Phase-based system (BAN/PICK/COMPLETE) with color coding
- [x] Manual draft cursor - click any slot to select it
- [x] Drag-and-drop champions between slots
- [x] Champion picker with search filtering
- [x] Role icons from Community Dragon API
- [x] Rank icons for ELO selection
- [x] Live champion splash art in pick slots
- [x] LLM Analysis box (expands when draft complete)
- [x] Reset button preserves user's role and rank settings
- [x] No duplicate picks - filtering works correctly
- [x] Draft phase auto-advancement with manual override
- [x] Text selection disabled to prevent accidental selection during drag

#### Authentication & User Management
- [x] Login/Register pages connected to backend
- [x] JWT token authentication with localStorage
- [x] Guest mode - full draft access without account
- [x] Header with auth status (profile picture, username, logout)
- [x] Profile page with full functionality

#### Profile/Settings Page
- [x] Profile picture selection (champion splash art)
- [x] Main role selection (single role)
- [x] Rank selection
- [x] Champion pool management (add/remove champions)
- [x] Proficiency ratings for champions
- [x] Save preferences with visual feedback
- [x] Preferences auto-load on draft page
- [x] Profile picture updates immediately in header

### Backend (FastAPI + PostgreSQL)

#### API Endpoints
- [x] User registration/login (`/api/v1/users/`)
- [x] User profile and preferences (`/api/v1/users/me`)
- [x] Champion pool management
- [x] Champion data (`/api/v1/champions/`)
- [x] Draft CRUD and actions (`/api/v1/drafts/`)
- [x] **NEW** Recommendations API (`/api/v1/recommendations/`)
- [x] **NEW** Admin API (`/api/v1/admin/`)

#### Services (NEW)
- [x] **Neural Network Service** - PyTorch-based recommendation model
  - 50-feature extraction (stats, matchups, synergies, composition)
  - Rule-based fallback when model not trained
  - Model persistence (save/load)
- [x] **LLM Prompts Service** - Stage-aware prompt generation
  - EARLY_BAN, FIRST_PICK, SECOND_BAN, FINAL_PICK, COMPLETE stages
  - Analysis, recommendation, gameplan prompts
  - User context integration
- [x] **Stats Scraper** - Champion statistics collection
  - Scrapes LoLalytics/U.GG for win rates, matchups, synergies
  - Async implementation with rate limiting
- [x] **Text Scraper** - LLM training data collection
  - MOBAFire guides, Reddit discussions, Fandom wiki
  - Quality scoring for training data
- [x] **Scheduler Service** - Automated task execution
  - Stats scraping (daily at 6 AM UTC)
  - Text scraping (weekly on Sundays)
  - Database cleanup (monthly)
- [x] **NN Trainer** - Neural network training pipeline
  - Generates training data from scraped stats
  - PyTorch model with configurable architecture
  - Validation and model saving

#### Database Models
- [x] User (auth, preferences, profile)
- [x] UserChampionPool (champion preferences with proficiency)
- [x] Champion (stats, matchups, synergies per patch)
- [x] Draft (state, picks, bans, analysis)
- [x] ScrapedContent (text data for LLM training)
- [x] LLMInteraction (analysis history)
- [x] DraftRecommendation (NN recommendations)

#### Authentication & Security
- [x] Password hashing (bcrypt)
- [x] JWT tokens with expiration
- [x] CORS configuration
- [x] Protected endpoints

### Infrastructure
- [x] Docker + Docker Compose (PostgreSQL, Redis, Backend, Frontend)
- [x] Alembic migrations
- [x] **NEW** deploy.sh with dev/prod modes
- [x] **NEW** Comprehensive requirements.txt
- [x] Environment-based configuration
- [x] .gitignore properly configured

### Testing
- [x] Test fixtures (conftest.py)
- [x] Service tests (test_services.py)
- [x] API endpoint tests (test_api.py)

---

## Data Pipeline (Ready for Production)

```
1. SEED CHAMPIONS
   └─> python scripts/seed_champions.py
   └─> Fetches from Data Dragon → Champion table

2. SCRAPE STATS (Automated daily or manual) - Riot API
   └─> POST /api/v1/admin/scrape/stats?ranks=DIAMOND&regions=na1,euw1,kr
   └─> Riot API → scraped_data/riot_stats/patch_X.X/{RANK}/champion_stats.json
   └─> Runs in background thread due to rate limits (can take hours)
   └─> Supports ALL ranks: IRON through CHALLENGER

3. LOAD STATS TO DATABASE
   └─> POST /api/v1/admin/scrape/load?rank=DIAMOND
   └─> JSON files → Champion table (win_rate, matchups, synergies)

4. TRAIN NEURAL NETWORK (Per-rank or combined)
   └─> POST /api/v1/admin/train?rank=DIAMOND&epochs=50  (single rank)
   └─> POST /api/v1/admin/train/all?epochs=50           (all ranks)
   └─> Scraped data → models/{RANK}/draft_recommendation.pth
   └─> Combined model → models/combined/draft_recommendation.pth

5. SCRAPE TEXT (Automated weekly or manual)
   └─> POST /api/v1/admin/scrape/text
   └─> MOBAFire/Reddit → ScrapedContent table

6. PRODUCTION USAGE
   └─> /api/v1/recommendations/sorted-champions
   └─> Returns champions sorted by rank-specific NN score
   └─> Falls back to combined model if rank-specific not available
   └─> Falls back to rule-based scoring if no models trained
```

### Per-Rank Model Architecture

```
models/
├── IRON/
│   ├── draft_recommendation.pth
│   ├── feature_scaler.pkl
│   └── model_metadata.json
├── BRONZE/
├── SILVER/
├── GOLD/
├── PLATINUM/
├── EMERALD/
├── DIAMOND/
├── MASTER/
├── GRANDMASTER/
├── CHALLENGER/
└── combined/
    ├── draft_recommendation.pth
    ├── feature_scaler.pkl
    └── model_metadata.json

scraped_data/
└── riot_stats/
    └── patch_16.1/
        ├── IRON/
        │   ├── champion_stats.json
        │   ├── synergies.json
        │   └── scrape_tracker.json
        ├── BRONZE/
        ├── ...
        └── CHALLENGER/
```

---

## Remaining Work

### Immediate (Before Production)
- [ ] Test backend services with real data
- [ ] Verify scraping works in production environment
- [ ] Train initial neural network model
- [ ] Test LLM integration with HuggingFace

### Future Enhancements
- [ ] Settings page separate from Profile
- [ ] Game mode selection (Ranked, ARAM, etc.)
- [ ] Draft history (save and review past drafts)
- [ ] Draft sharing (share draft URL)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Rate limiting middleware

---

## Technology Summary

| Layer | Technology |
|-------|------------|
| Frontend | React 19, TypeScript, Vite, TailwindCSS, Zustand |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.0, Pydantic 2 |
| AI/ML | PyTorch, HuggingFace (Mistral 7B), scikit-learn |
| Database | PostgreSQL 15, Redis 7 |
| Scraping | aiohttp, BeautifulSoup4, APScheduler |
| Deployment | Docker, Docker Compose |
| Testing | pytest, pytest-asyncio |

---

## Recent Changes

### 2026-01-17 (Per-Rank Data Pipeline)
- Rewrote stats_scraper.py to use official Riot API instead of third-party scrapers
- Added support for ALL ranks (IRON through CHALLENGER)
- Data stored per-rank: scraped_data/riot_stats/patch_X.X/{RANK}/
- Updated nn_trainer.py to train per-rank models
- Updated draft_nn_service.py to load rank-specific models dynamically
- Updated recommendations endpoint to use rank-specific models
- Added training endpoints to admin API: POST /train, POST /train/all
- Added GET /models endpoint to check available trained models
- Background thread execution for long-running scrapes (rate limiting)
- Falls back to combined model → rule-based scoring gracefully

### 2026-01-16 (Backend Overhaul)
- Created comprehensive stats_scraper.py for LoLalytics/U.GG
- Created scheduler.py for automated scraping tasks
- Created nn_trainer.py for neural network training pipeline
- Created llm_prompts.py with stage-aware prompts
- Created recommendations.py API endpoint
- Created admin.py for manual task triggers
- Updated requirements.txt with all dependencies
- Updated deploy.sh with dev/prod modes
- Removed hardcoded credentials from scripts
- Deleted duplicate scrape_text_data.py
- Created comprehensive test suite

### 2026-01-16 (Frontend)
- Created custom TrynDraft logo
- Fixed guest login redirect
- Fixed reset button behavior
- Single role selection on profile
- Immediate profile picture updates
- Disabled text selection on draft page

---

**Project Status:** Ready for Production Testing
**License:** MIT
