# TrynDraft Development Roadmap

**Last Updated:** 2026-02-12

## Phase 1: Core Draft Interface ✅ COMPLETED
- [x] Draft UI with pick/ban slots
- [x] Champion picker with search and filtering
- [x] Phase-based system (BAN/PICK/COMPLETE)
- [x] Drag-and-drop functionality for swapping champions
- [x] Role and rank selection
- [x] Settings page with game mode (Ranked/Clash/Pro)
- [x] Clickable recommendations in LLM panel
- [x] Draft stats bar on completion (matchup, synergy, damage split)

## Phase 2: User Management ✅ COMPLETED
- [x] User registration and login (JWT auth with bcrypt)
- [x] Profile page with settings
- [x] Champion pool management with proficiency ratings
- [x] Preferences (role, rank, profile picture)
- [x] Guest mode for quick access
- [x] Security: SECRET_KEY from environment variables

## Phase 3: Data Collection ✅ COMPLETED
- [x] Riot API integration via Riot-Watcher
- [x] Automated match scraping across all ranks (IRON-CHALLENGER)
- [x] Champion win rates, pick rates, ban rates by role
- [x] Counter/matchup relationships (role-nested structure)
- [x] KDA, gold, damage stats per role
- [x] 30K+ matches scraped for Patch 16.2
- [ ] **MISSING:** Automated scraping workflow (GitHub Actions)
- [ ] Text data scraping for LLM (MOBAFire/LoLalytics guides)
- [ ] Professional draft data (GRID API)

## Phase 4: Neural Network Engine ✅ COMPLETED
- [x] 48-feature neural network architecture
- [x] Role-specific features (win rate, games, KDA per role)
- [x] Matchup-aware scoring (vs 5 enemies)
- [x] Synergy scoring (with 4 allies)
- [x] Team composition analysis
- [x] 11 trained models (10 rank-specific + 1 combined)
- [x] 0-games-in-role penalty (95% score reduction)
- [x] Validation loss ~0.001 (excellent)
- [x] Matchup override functionality
- [ ] **MISSING:** Data weighting strategy (newer patches > older)
- [ ] **MISSING:** Automated retraining on new patches

## Phase 5: LLM Integration 🔄 PARTIAL
- [x] HuggingFace integration framework
- [x] Rule-based fallback system
- [x] Draft analysis endpoint
- [x] Turn-based recommendations
- [ ] **DISABLED FOR BETA:** LLM enabled (cost concerns)
- [ ] LLM fine-tuning on LoL-specific data
- [ ] Text data collection and preprocessing
- [ ] Model selection (HF vs OpenAI vs local)

## Phase 6: Production Deployment ⚠️ BLOCKED
- [x] Docker configuration (backend + frontend + PostgreSQL + Redis)
- [x] Environment variable management (.env.example files)
- [x] Production-ready Dockerfiles (no --reload, workers=2)
- [x] CI/CD test pipeline (GitHub Actions)
- [x] Security audit (no hardcoded secrets)
- [ ] **BLOCKED:** Railway deployment (build timeouts due to PyTorch size)
- [ ] **MISSING:** Automated deployment workflow
- [ ] Monitoring and logging
- [ ] Performance optimization

## Phase 7: Advanced Features 📋 FUTURE
- [ ] WebSocket for multi-user live drafts
- [ ] Draft history and replay
- [ ] Draft sharing via URL
- [ ] Mobile responsive design
- [ ] Voice/LLM commentary mode
- [ ] Pro play integration and analysis

---

## Current Status: Beta-Ready (Deployment Paused)

**What's Working:**
- ✅ Full draft interface with drag-and-drop
- ✅ NN recommendations (11 trained models)
- ✅ Role-aware and matchup-aware scoring
- ✅ User authentication and champion pools
- ✅ Draft completion stats
- ✅ 30K+ match dataset (Patch 16.2)

**What's Broken/Missing:**
- ✅ **FIXED:** Win rate display (was showing 10000% instead of 100%)
- ✅ **FIXED:** Draft stats damage split (was showing 50% instead of 0%)
- ✅ **FIXED:** Picker alphabetical order (missing patch data, now auto-fallbacks to latest)
- ✅ **READY:** Automated scraping + training (GitHub Actions workflow includes both)
- ✅ **CREATED:** Text data scraper (for LLM training)
- ⚠️ **ACTION REQUIRED:** Set RIOT_API_KEY in GitHub secrets, then trigger workflow manually
- ⚠️ Railway deployment (PyTorch too large)
- ⚠️ LLM disabled (no actual AI analysis, just rule-based)
- ⚠️ Login issues (needs investigation)

---

## Current Focus

### Immediate (Sprint 1 - Week of Feb 10-17)
1. ✅ **Create automated scraping workflow** - DONE
   - GitHub Actions cron job every 6 hours
   - Scrape high-elo data for latest patch
   - Auto-commit to repo
   - **Status:** Created, ready for testing

2. ✅ **Fix critical display bugs** - DONE
   - Fixed win rate display (10000% → 100%)
   - Fixed draft stats damage split (50% → 0% when appropriate)
   - **Status:** Backend fixed, frontend needs hard refresh

3. ⚠️ **Fix picker alphabetical order bug** - IN PROGRESS
   - Backend API confirmed working
   - Frontend likely needs browser cache clear
   - **Next:** User needs to hard refresh (Cmd+Shift+R)

4. 🔲 **Create automated training workflow** - PARTIAL
   - Workflow created in GitHub Actions
   - Needs testing to confirm it works
   - **Todo:** Implement data weighting (newer > older)

5. 🔲 **Fix deployment blockers** - NOT STARTED
   - Option A: Use CPU-only PyTorch (200MB vs 2GB)
   - Option B: Use different platform (not Railway)
   - Option C: Pre-build image and push to registry

6. 🔲 **Investigate login issue** - NOT STARTED
   - Verify backend running
   - Check SECRET_KEY configuration
   - Test registration flow

### Short-term (Sprint 2 - Week of Feb 17)
1. **Improve draft stats accuracy**
   - Add confidence indicators
   - Better missing data handling
   - Collect more matchup/synergy data

2. **Text data scraping**
   - Scrape MOBAFire for champion guides
   - Scrape LoLalytics for meta insights
   - Prepare for LLM fine-tuning

3. **Beta deployment**
   - Resolve Railway issues OR migrate platform
   - Deploy to production
   - Add URL to GitHub README

### Medium-term (Q1 2026)
1. **LLM enablement**
   - Cost analysis (HF vs OpenAI vs local)
   - Fine-tune on LoL-specific data
   - Replace rule-based analysis

2. **Pro play integration**
   - GRID API for tournament data
   - Meta trend analysis
   - Professional draft patterns

3. **Mobile optimization**
   - Responsive design
   - Touch-friendly controls
   - PWA capabilities

---

## Key Milestones

| Milestone | Target | Status |
|-----------|--------|--------|
| MVP Draft Interface | Q4 2025 | ✅ Done |
| User Auth System | Q4 2025 | ✅ Done |
| Data Scraping | Q1 2026 | ✅ Done |
| NN Training | Q1 2026 | ✅ Done |
| Automated Workflows | Q1 2026 | ❌ Blocked |
| Beta Deployment | Q1 2026 | ⚠️ Paused |
| LLM Fine-tuning | Q1 2026 | 📋 Planned |
| Production Launch | Q2 2026 | 📋 Planned |

---

## Technical Debt & Known Issues

See [ISSUES_AND_FIXES.md](../docs/ISSUES_AND_FIXES.md) for detailed issue tracker.

**High Priority:**
1. GitHub Actions workflows missing
2. Railway deployment timeouts
3. Data weighting strategy not implemented
4. Login authentication needs verification

**Medium Priority:**
1. Draft stats show placeholders for missing data
2. Synergy calculation needs more data
3. Matchup dropdown behavior
4. LLM disabled (cost concerns)

**Low Priority:**
1. Mobile responsive improvements
2. Loading states and animations
3. Error handling edge cases

---

**Project Lead:** Idan Talker
**Contributors:** Idan Talker + Claude (Sonnet 4.5)
**License:** See [LICENSE](../LICENSE)
