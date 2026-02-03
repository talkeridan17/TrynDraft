# TrynDraft Deployment & Continuous Improvement Strategy

## Overview

This document outlines the strategy for deploying TrynDraft to production, maintaining continuous data updates, and improving the neural network models over time.

---

## 1. Deployment Architecture

### Recommended Hosting Stack

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Vercel/Netlify)               │
│                     React + Vite Static Build               │
│                     URL: tryndraft.com                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND (Railway/Render/Fly.io)         │
│                     FastAPI + PostgreSQL                    │
│                     URL: api.tryndraft.com                  │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   PostgreSQL     │ │   Redis Cache    │ │   S3/R2 Storage  │
│   (Supabase/     │ │   (Upstash)      │ │   (Scraped Data) │
│    Railway)      │ │                  │ │                  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

### Service Recommendations

| Component | Free Tier Option | Paid Recommendation |
|-----------|------------------|---------------------|
| Frontend | Vercel (free) | Vercel Pro |
| Backend | Railway ($5/mo credit) | Railway/Fly.io |
| Database | Supabase (free tier) | Railway PostgreSQL |
| Redis | Upstash (free tier) | Upstash Pro |
| Scraper Jobs | GitHub Actions (free) | Railway Cron / Render Cron |
| File Storage | Cloudflare R2 (free tier) | R2 or S3 |

---

## 2. Git Workflow for Continuous Development

```
main (production)
  │
  └── dev (staging/testing)
        │
        ├── feature/matchup-ui
        ├── feature/llm-integration
        └── fix/damage-split
```

### Workflow

1. **Development**: Work on `dev` branch or feature branches
2. **Testing**: Merge features to `dev`, test on staging environment
3. **Release**: When stable, merge `dev` → `main`
4. **Auto-Deploy**: CI/CD triggers deployment on `main` push

### CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./frontend

  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Railway
        uses: bervProject/railway-deploy@main
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
```

---

## 3. Automated Scraping Strategy

### Scraping Schedule

| Scraper | Frequency | Trigger | Purpose |
|---------|-----------|---------|---------|
| SoloQ Stats | Every 6 hours | Cron | Fresh matchup/win rate data |
| Patch Detection | Every 2 hours | Cron | Detect new patches |
| Full Rank Scrape | On new patch | Event | Complete re-scrape all ranks |
| High Elo Priority | Every 4 hours | Cron | Master+ data (most valuable) |

### GitHub Actions Cron for Scraping

```yaml
# .github/workflows/scrape.yml
name: Automated Scraping

on:
  schedule:
    # Run every 6 hours
    - cron: '0 */6 * * *'
  workflow_dispatch: # Manual trigger

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      - name: Run scraper
        env:
          RIOT_API_KEY: ${{ secrets.RIOT_API_KEY }}
        run: |
          cd backend
          python scripts/run_scrapers.py high-elo --ranks MASTER GRANDMASTER CHALLENGER

      - name: Upload scraped data
        # Upload to S3/R2 or commit to repo
        run: |
          # Option 1: Commit to repo (simple)
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add backend/scraped_data/
          git commit -m "chore: update scraped data $(date +%Y-%m-%d)" || true
          git push
```

### Alternative: Railway Cron Service

Create a separate Railway service for scraping:

```dockerfile
# Dockerfile.scraper
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["python", "scripts/run_scrapers.py", "high-elo"]
```

Configure Railway cron: `0 */6 * * *`

---

## 4. Neural Network Update Strategy

### Key Principles

1. **Patch-Aware Training**: Each patch gets its own training data
2. **Recency Weighting**: Recent data weighted higher than old data
3. **No Data Leakage**: Each match counted once, train/val split by time
4. **Incremental Learning**: Update existing models, don't retrain from scratch

### Data Flow for NN Training

```
New Patch Detected
       │
       ▼
┌─────────────────────┐
│ Scrape Initial Data │  (First 24-48 hours of patch)
│ ~500 matches/rank   │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ Retrain NN Models   │  (Fine-tune on new patch data)
│ With Transfer       │
│ Learning            │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ Continuous Updates  │  (Every 6 hours)
│ Incremental Train   │
└─────────────────────┘
```

### Avoiding Data Leakage

```python
# In nn_trainer.py - ensure unique matches

class NNTrainer:
    def __init__(self):
        self.seen_match_ids = set()  # Track processed matches

    def load_training_data(self, patch: str, rank: str):
        data_path = f"scraped_data/riot_stats/patch_{patch}/{rank}/champion_stats.json"
        with open(data_path) as f:
            data = json.load(f)

        # Each match has unique ID from Riot API
        # The scraper already handles deduplication via match_id
        # But we add a safety check here
        unique_samples = []
        for sample in data.get('training_samples', []):
            match_id = sample.get('match_id')
            if match_id and match_id not in self.seen_match_ids:
                self.seen_match_ids.add(match_id)
                unique_samples.append(sample)

        return unique_samples

    def split_by_time(self, samples: List[Dict]) -> Tuple[List, List]:
        """Split train/val by time, not random, to prevent leakage."""
        # Sort by match timestamp
        sorted_samples = sorted(samples, key=lambda x: x.get('timestamp', 0))

        # Use last 20% as validation (most recent matches)
        split_idx = int(len(sorted_samples) * 0.8)
        train = sorted_samples[:split_idx]
        val = sorted_samples[split_idx:]

        return train, val
```

### Recency Weighting

```python
def calculate_sample_weight(match_timestamp: int, current_time: int) -> float:
    """Weight recent matches higher than old ones."""
    age_hours = (current_time - match_timestamp) / 3600

    # Exponential decay: recent = 1.0, week old = 0.5, month old = 0.1
    decay_rate = 0.01  # Adjust based on patch cycle
    weight = math.exp(-decay_rate * age_hours)

    return max(0.1, weight)  # Floor at 0.1, don't completely ignore old data
```

### Patch Transition Strategy

```python
def handle_new_patch(old_patch: str, new_patch: str, rank: str):
    """Strategy for transitioning models to a new patch."""

    # 1. Start with transfer learning from previous patch model
    old_model = load_model(f"models/{rank}/draft_recommendation.pth")

    # 2. Scrape initial data for new patch (at least 500 matches)
    scrape_new_patch(new_patch, rank, min_matches=500)

    # 3. Fine-tune on new patch data with lower learning rate
    new_model = fine_tune(
        old_model,
        new_patch_data,
        learning_rate=0.0001,  # 10x lower than initial training
        epochs=10
    )

    # 4. Validate: new model should outperform old on new patch data
    old_accuracy = evaluate(old_model, new_patch_data)
    new_accuracy = evaluate(new_model, new_patch_data)

    if new_accuracy > old_accuracy:
        save_model(new_model, f"models/{rank}/draft_recommendation.pth")
        log(f"Updated model for {rank}: {old_accuracy:.2f}% -> {new_accuracy:.2f}%")
    else:
        log(f"Warning: New model underperforms, keeping old model")
```

---

## 5. Environment Configuration

### Production Environment Variables

```bash
# Backend (.env.production)
SECRET_KEY=<generate with: openssl rand -hex 32>
DATABASE_URL=postgresql://user:pass@host:5432/tryndraft
REDIS_URL=redis://default:pass@host:6379
RIOT_API_KEY=<production API key>
CORS_ORIGINS=["https://tryndraft.com"]
DEBUG=false

# For LLM (when ready)
HF_TOKEN=<huggingface token>
OPENAI_API_KEY=<optional>
```

### Frontend Environment

```bash
# Frontend (.env.production)
VITE_API_URL=https://api.tryndraft.com
VITE_APP_ENV=production
```

---

## 6. Monitoring & Alerts

### Key Metrics to Track

1. **API Health**: Response times, error rates
2. **Scraper Status**: Last run time, matches scraped, failures
3. **NN Performance**: Recommendation accuracy, user feedback
4. **Data Freshness**: Age of newest match data per rank

### Simple Monitoring Setup

```python
# In progress_tracker.py - add health check endpoint

@router.get("/health")
async def health_check():
    progress = get_progress_tracker()

    # Check data freshness
    last_scrape = max(
        datetime.fromisoformat(tier['last_run'])
        for tier in progress.stats_scraping.values()
        if tier.get('last_run')
    )
    hours_since_update = (datetime.now(timezone.utc) - last_scrape).total_seconds() / 3600

    return {
        "status": "healthy" if hours_since_update < 12 else "stale",
        "last_data_update": last_scrape.isoformat(),
        "hours_since_update": round(hours_since_update, 1),
        "scrape_status": {
            rank: tier['status']
            for rank, tier in progress.stats_scraping.items()
        }
    }
```

---

## 7. Launch Checklist

### Before Launch

- [ ] Remove all hardcoded secrets
- [ ] Set up production environment variables
- [ ] Configure CORS for production domain
- [ ] Set up SSL/HTTPS
- [ ] Create production database (PostgreSQL)
- [ ] Run database migrations
- [ ] Seed champion data from Data Dragon
- [ ] Upload scraped stats data
- [ ] Deploy NN models
- [ ] Test all API endpoints
- [ ] Test frontend on production build

### Post-Launch

- [ ] Set up automated scraping cron jobs
- [ ] Configure monitoring/alerts
- [ ] Set up error tracking (Sentry)
- [ ] Monitor API usage and costs
- [ ] Gather user feedback
- [ ] Plan LLM integration (Phase 2)

---

## 8. Cost Estimates

### Minimal Beta Launch (Free/Cheap)

| Service | Cost | Notes |
|---------|------|-------|
| Vercel (Frontend) | $0 | Free tier |
| Railway (Backend) | $5/mo | Hobby plan |
| Supabase (DB) | $0 | Free tier (500MB) |
| Upstash (Redis) | $0 | Free tier |
| GitHub Actions | $0 | Free for public repos |
| **Total** | **~$5/mo** | |

### Production Scale

| Service | Cost | Notes |
|---------|------|-------|
| Vercel Pro | $20/mo | Better performance |
| Railway | $20/mo | More resources |
| PostgreSQL | $15/mo | Dedicated instance |
| Redis | $10/mo | More memory |
| S3/R2 Storage | $5/mo | Scraped data |
| **Total** | **~$70/mo** | |

---

## 9. Future Phases

### Phase 1: Beta Launch (Current)
- Core draft tool working
- NN recommendations functional
- LLM box shows loading/placeholder
- Manual data refresh

### Phase 2: LLM Integration
- Evaluate LLM API costs (OpenAI vs local)
- Fine-tune small model for draft analysis
- Implement streaming responses

### Phase 3: User Features
- User accounts with saved preferences
- Draft history and analytics
- Custom champion pools per role

### Phase 4: Pro Play Integration
- Scrape pro match data
- "Pro Picks" mode
- Meta analysis by region

---

## Quick Commands Reference

```bash
# Local development
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
cd frontend && npm run dev

# Run scrapers manually
cd backend && python scripts/run_scrapers.py high-elo

# Train NN models
cd backend && python scripts/train_nn.py --rank PLATINUM

# Build frontend for production
cd frontend && npm run build

# Check scraping progress
cat logs/progress.json | jq '.stats_scraping'
```
