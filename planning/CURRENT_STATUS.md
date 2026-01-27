# TrynDraft - Current Development Status

**Last Updated:** 2026-01-26
**Version:** 0.5.0-alpha

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                            │
│  React 19 + TypeScript + Vite + TailwindCSS + Zustand      │
│  • Draft Interface    • Profile Page    • Settings Page    │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                         BACKEND                             │
│              FastAPI + Python 3.12 + SQLAlchemy            │
├─────────────────────────────────────────────────────────────┤
│ SERVICES                                                    │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────────┐  │
│ │  NN Service   │ │  LLM Service  │ │  Stats Scraper   │  │
│ │  (PyTorch)    │ │ (Qwen2.5-72B) │ │  (LoLalytics)    │  │
│ └───────────────┘ └───────────────┘ └───────────────────┘  │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────────┐  │
│ │  Text Scraper │ │  Prompts Svc  │ │  Draft Logic     │  │
│ │  (MOBAFire)   │ │ (Stage-aware) │ │  (Validation)    │  │
│ └───────────────┘ └───────────────┘ └───────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│ STORAGE                                                     │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│ │ SQLite/PG   │ │    Redis    │ │  File Storage          ││
│ │ (Database)  │ │   (Cache)   │ │  (Models, Logs)        ││
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
- [x] Drag-and-drop champions between slots (with swap support)
- [x] Champion picker with search filtering
- [x] **NEW** Clickable champion recommendations in LLM panel
- [x] Role icons from Community Dragon API
- [x] Rank icons for ELO selection
- [x] Live champion splash art in pick slots
- [x] LLM Analysis box (expands when draft complete)
- [x] Reset button preserves user's role and rank settings
- [x] No duplicate picks - filtering works correctly
- [x] Draft phase auto-advancement with manual override
- [x] AbortController for cancelling stale LLM requests

#### Authentication & User Management
- [x] Login/Register pages connected to backend
- [x] JWT token authentication with localStorage
- [x] Guest mode - full draft access without account
- [x] Header with auth status (profile picture, username, logout)
- [x] Profile page with full functionality

#### Settings Page (NEW)
- [x] Game mode selection (Ranked/Clash/Pro)
- [x] Separate from Profile page
- [x] Accessible to all users (logged in or guest)

#### Profile Page
- [x] Profile picture selection (champion splash art)
- [x] Main role selection (single role)
- [x] Rank selection
- [x] Champion pool management (add/remove champions)
- [x] Proficiency ratings (1-5 stars) for champions
- [x] Save preferences with visual feedback
- [x] Preferences auto-load on draft page

### Backend (FastAPI + Python 3.12)

#### API Endpoints
- [x] User registration/login (`/api/v1/users/`)
- [x] User profile and preferences (`/api/v1/users/me`)
- [x] Champion pool management
- [x] Champion data (`/api/v1/champions/`)
- [x] Draft CRUD and actions (`/api/v1/drafts/`)
- [x] Recommendations API (`/api/v1/recommendations/`)
- [x] Admin API (`/api/v1/admin/`)

#### Services
- [x] **Neural Network Service** - 50-feature PyTorch model
- [x] **LLM Service** - HuggingFace Qwen2.5-72B integration
- [x] **LLM Prompts Service** - Stage-aware prompt generation
- [x] **Rule-based Fallback** - Free dev mode (USE_HUGGINGFACE_API=false)
- [x] **Stats Scraper** - Champion statistics collection
- [x] **Text Scraper** - MOBAFire/LoLalytics guide scraping
- [x] **Progress Tracker** - Unified logging for scrapers

#### Database Models
- [x] User (auth, preferences, profile)
- [x] UserChampionPool (champion preferences with proficiency)
- [x] Champion (stats, matchups, synergies per patch)
- [x] Draft (state, picks, bans, analysis)
- [x] ScrapedContent (text data for LLM training)
- [x] LLMInteraction (analysis history)

---

## LLM Integration Details

### Current State
- **Model**: Qwen2.5-72B via HuggingFace Inference API
- **Status**: Disabled by default (USE_HUGGINGFACE_API=false)
- **Fallback**: Rule-based analysis with role-specific advice

### Prompt Types
1. **Analysis Prompt** - Comp needs + strategic analysis + recommendations
2. **Gameplan Prompt** - 4-section detailed strategy (COMPLETE phase)
3. **Draft Start Prompt** - Meta overview and ban targets
4. **Matchup Prompt** - 1v1 lane analysis
5. **Counter-pick Prompt** - Counter suggestions
6. **Synergy Prompt** - Team composition analysis

### Token Limits
- Regular analysis: 500 tokens
- Complete gameplan: 1500 tokens

---

## Neural Network Architecture

```
Input (50 features)
    │
    ▼
┌─────────────────────┐
│ Linear(50, 128)     │
│ BatchNorm + ReLU    │
│ Dropout(0.3)        │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Linear(128, 64)     │
│ BatchNorm + ReLU    │
│ Dropout(0.2)        │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Linear(64, 32)      │
│ ReLU                │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Linear(32, 1)       │
│ Sigmoid → Score     │
└─────────────────────┘

Features:
- Base stats (attack, defense, magic, difficulty)
- Meta stats (win rate, pick rate, ban rate)
- User proficiency (1-5)
- Matchup scores vs enemy picks
- Synergy scores with ally picks
- Role compatibility
- Team composition balance
```

---

## Data Pipeline

```
1. SEED CHAMPIONS
   └─> python scripts/seed_champions.py
   └─> Data Dragon → Champion table

2. SCRAPE STATS (Manual)
   └─> POST /api/v1/admin/scrape/stats
   └─> LoLalytics/U.GG → Champion stats JSON

3. TRAIN NEURAL NETWORK
   └─> POST /api/v1/admin/train
   └─> Stats → models/draft_recommendation.pth

4. SCRAPE TEXT (For LLM fine-tuning)
   └─> POST /api/v1/admin/scrape/text
   └─> MOBAFire → ScrapedContent table

5. FINE-TUNE LLM (Planned)
   └─> ScrapedContent → Fine-tuned model
```

---

## Recent Changes

### 2026-01-26
- Added clickable champion recommendations in LLM panel
- Added AbortController for LLM request cancellation
- Disabled HuggingFace API by default (USE_HUGGINGFACE_API=false)
- Improved rule-based analysis with role-specific advice
- Updated all documentation (README, SECURITY, CONTRIBUTING)
- Cleaned up empty directories in planning folder
- Increased LLM token limits (500 regular, 1500 gameplan)

### 2026-01-25
- Added Settings page with game mode selection
- Fixed champion swapping in draft slots
- Fixed LLM response text size and structure
- Added champion de-duplication in database
- Created root-level logs folder for scrapers

### 2026-01-17
- Per-rank neural network models
- Riot API integration for stats
- Background thread execution for scraping

---

## Environment Configuration

```bash
# Backend .env
DATABASE_URL=sqlite:///./tryndraft.db
SECRET_KEY=your-secret-key
RIOT_API_KEY=your-riot-key           # Optional
HF_TOKEN=your-huggingface-token      # Optional
USE_HUGGINGFACE_API=false            # Set true for production

# Frontend .env
VITE_API_URL=http://localhost:8000
```

---

## Remaining Work

### Immediate (Phase 3 Completion)
- [ ] Complete data scraping pipeline
- [ ] Train NN with real champion stats
- [ ] Fine-tune LLM on LoL content (post-scraping)
- [ ] Integrate matchup data into recommendations

### Future
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Production deployment (AWS/Railway)
- [ ] Draft history and sharing
- [ ] Multi-user live drafts (WebSocket)
- [ ] Mobile responsive design

---

**Project Status:** Active Development
**License:** MIT
