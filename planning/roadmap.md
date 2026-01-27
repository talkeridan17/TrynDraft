# TrynDraft Development Roadmap

**Last Updated:** 2026-01-26

## Phase 1: Core Draft Interface ✅ COMPLETED
- [x] Draft UI with pick/ban slots
- [x] Champion picker with search and filtering
- [x] Phase-based system (BAN/PICK/COMPLETE)
- [x] Drag-and-drop functionality for swapping champions
- [x] Role and rank selection
- [x] Settings page with game mode (Ranked/Clash/Pro)
- [x] Clickable recommendations in LLM panel

## Phase 2: User Management ✅ COMPLETED
- [x] User registration and login (JWT auth)
- [x] Profile page with settings
- [x] Champion pool management with proficiency ratings
- [x] Preferences (role, rank, profile picture)
- [x] Guest mode for quick access

## Phase 3: AI Integration 🔄 IN PROGRESS
- [x] Neural network recommendation engine (50-feature model)
- [x] LLM analysis integration (HuggingFace Qwen2.5-72B)
- [x] Rule-based fallback for development
- [x] Role-specific recommendations
- [ ] **NEXT:** Data scraping for training
- [ ] LLM fine-tuning with LoL-specific data
- [ ] Matchup data integration

## Phase 4: Data Collection 📋 PLANNED
- [ ] MOBAFire guide scraping
- [ ] LoLalytics statistics scraping
- [ ] Riot API integration for match data
- [ ] Champion win rates, pick rates, ban rates
- [ ] Counter/synergy relationships
- [ ] Professional draft data (via GRID API)

## Phase 5: ML Enhancement 📋 PLANNED
- [ ] Train NN on scraped data
- [ ] Fine-tune LLM on LoL content
- [ ] A/B test model performance
- [ ] Implement feedback loop for continuous improvement

## Phase 6: Production Deployment 📋 PLANNED
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Cloud deployment (AWS/Railway)
- [ ] Monitoring and logging (Sentry)
- [ ] Performance optimization
- [ ] Beta testing with real users

## Phase 7: Advanced Features 📋 FUTURE
- [ ] Draft history and replay
- [ ] Draft sharing via URL
- [ ] Multi-user live drafts (WebSocket)
- [ ] Mobile responsive design
- [ ] Voice/LLM commentary mode

---

## Current Focus

**Phase 3 - AI Integration**
- Setting up data scrapers for MOBAFire and LoLalytics
- Building training dataset for LLM fine-tuning
- Improving NN model with real statistics

## Key Milestones

| Milestone | Target | Status |
|-----------|--------|--------|
| MVP Draft Interface | Q4 2025 | ✅ Done |
| User Auth System | Q4 2025 | ✅ Done |
| NN Recommendations | Q1 2026 | ✅ Done |
| LLM Integration | Q1 2026 | ✅ Done |
| Data Scraping | Q1 2026 | 🔄 In Progress |
| LLM Fine-tuning | Q1 2026 | 📋 Planned |
| Beta Launch | Q2 2026 | 📋 Planned |

---

**Contributors:** Idan Talker
