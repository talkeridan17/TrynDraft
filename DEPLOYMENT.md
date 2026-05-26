# TrynDraft - Production Deployment Guide

**Last Updated:** 2026-05-25

TrynDraft is now a **static frontend-only application**. There is no backend required for the core draft experience — the ONNX model, LLM, and Deeplol proficiency lookup all run client-side in the browser.

---

## Current Architecture (v0.7)

```
┌────────────────────────────────────────────────────┐
│             Browser (React + ONNX Runtime Web)     │
│                                                    │
│  ┌──────────────┐  ┌──────────────┐               │
│  │  ONNX Model  │  │  Qwen2.5 LLM │               │
│  │  (20MB, CDN) │  │  (HuggingFace│               │
│  └──────────────┘  └──────────────┘               │
│                                                    │
│  ┌──────────────┐  ┌──────────────┐               │
│  │  Data Dragon │  │  Deeplol CDN │               │
│  │  (champions) │  │  (SID stats) │               │
│  └──────────────┘  └──────────────┘               │
└────────────────────────────────────────────────────┘
        ↑ served as static files from any CDN
```

No database, no auth, no Redis, no backend process. Serves as a `dist/` folder from any static host.

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | React 19 + TypeScript + Vite | User interface |
| AI Inference | ONNX Runtime Web (CDN) | DraftTransformer in browser |
| LLM | HuggingFace Transformers.js v3 | Explainability (Qwen2.5) |
| Player Data | Deeplol.gg CDN API | Champion proficiency per Riot ID |
| Champion Data | Riot Data Dragon CDN | Champion names, images, patches |
| Deployment | Vercel / Netlify / GitHub Pages | Static site hosting |

---

## Deploying to Vercel (Recommended — 5 minutes)

This is the fastest path to a live URL.

### 1. Build locally to verify

```bash
cd frontend
npm install
npm run build       # produces frontend/dist/
```

### 2. Deploy via Vercel CLI

```bash
npm install -g vercel
cd frontend
vercel --prod
```

Or connect the GitHub repo to vercel.com → set **Root Directory** to `frontend` → auto-deploys on every push to `main`.

### 3. Set the one required env var

In Vercel project settings → Environment Variables:

```
VITE_API_URL=   (leave blank — frontend-only mode, no backend)
```

That's it. The ONNX model, LLM weights, and all data are fetched client-side at runtime.

---

## Deploying to Netlify

```bash
cd frontend
npm run build
npx netlify deploy --prod --dir=dist
```

Or drag `frontend/dist/` onto app.netlify.com.

Add a `frontend/public/_redirects` file to handle SPA routing:
```
/*    /index.html   200
```

---

## Custom Domain

Once you have a domain (e.g. tryndraft.com):

1. In Vercel/Netlify: Add custom domain → point DNS to their nameservers
2. TLS is automatic (Let's Encrypt)
3. Update `CORS_ORIGINS` if you later add a backend

**Estimated time from domain purchase to live site: 1–2 hours** (DNS propagation is the bottleneck).

---

## CI/CD (GitHub Actions)

The existing `.github/workflows/ci.yml` already:
- Type-checks and lints the frontend on every push to `dev` or `main`
- Builds the frontend and verifies it compiles

To add auto-deploy on merge to `main`, uncomment the Vercel step in `ci.yml` and add `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` to GitHub Secrets.

---

## Model Updates

When the DraftTransformer is retrained (new patch data), update the browser model:

```bash
cd llm-ai-stuff
python training/refresh.py --skip-scrape --epochs 50 --fine-tune
# This copies updated ONNX files to frontend/public/models/ automatically
```

Then commit + push → CI builds → Vercel deploys → users get the new model on next page load.

---

## Legacy: Docker / Backend Setup

The backend (`backend/`) still exists and can be used for saved drafts or additional analytics in the future. The Docker Compose setup from earlier versions still works. See git history for the full backend deployment guide. For the current release, it is not needed.

---

## Deployment Timeline

| Date | Milestone |
|---|---|
| 2026-04-18 | DraftTransformer model complete (Rohan) |
| 2026-05-25 | Merge frontend-AI branch, remove auth, SID lookup integrated |
| **Target: 2026-06-01** | **Domain live, first public users** |
| Target: 2026-06-15 | Model retrain on Season 2026 patch data |
| Target: 2026-07 | Clash mode end-to-end tested, team sharing feature |

---

## Legacy Docker Setup (pre-v0.7)

> The following is kept for reference. Not needed for the current static deployment.

### Quick Start with Docker

```bash
git clone https://github.com/yourusername/TrynDraft.git
cd TrynDraft

# Copy environment template
cp .env.example .env
```

### Environment Variables

```bash
# Security (REQUIRED)
SECRET_KEY=<generate: openssl rand -hex 32>
POSTGRES_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>

# Database
POSTGRES_USER=postgres
DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/tryndraft

# API Keys (for full functionality)
HF_TOKEN=<huggingface-api-token>
RIOT_API_KEY=<riot-games-api-key>

# Production Settings
DEBUG=False
CORS_ORIGINS=https://yourdomain.com
```

### 3. Deploy

```bash
# Start all services
./deploy.sh prod

# Or manually:
docker compose up -d --build
```

### 4. Initialize Data

```bash
# Seed champion data from Riot's Data Dragon
docker compose exec backend python scripts/seed_champions.py

# Trigger initial stats scraping
./deploy.sh scrape

# Train neural network (after scraping completes)
./deploy.sh train
```

---

## Services

### Backend API (Port 8000)

| Endpoint | Description |
|----------|-------------|
| `/health` | Health check |
| `/docs` | Swagger API documentation |
| `/api/v1/users/*` | Authentication & profiles |
| `/api/v1/champions/*` | Champion data |
| `/api/v1/drafts/*` | Draft management |
| `/api/v1/recommendations/*` | AI recommendations |
| `/api/v1/admin/*` | Admin operations |

### Scheduled Tasks

The backend scheduler runs automatically in production (`DEBUG=False`):

| Task | Schedule | Description |
|------|----------|-------------|
| Stats Scraping | Daily 6 AM UTC | Scrape LoLalytics/U.GG for champion stats |
| Text Scraping | Weekly Sunday 3 AM | Scrape MOBAFire/Reddit for LLM training |
| DB Cleanup | Monthly 1st 2 AM | Remove old data, optimize storage |

### Manual Task Triggers

```bash
# Trigger stats scraping
curl -X POST http://localhost:8000/api/v1/admin/scrape/stats

# Trigger text scraping
curl -X POST http://localhost:8000/api/v1/admin/scrape/text

# Check system status
curl http://localhost:8000/api/v1/admin/status
```

---

## Cloud Deployment

### Railway / Render / Fly.io

1. Connect your GitHub repository
2. Set environment variables in dashboard
3. Deploy with PostgreSQL add-on
4. Configure custom domain

### AWS / GCP / Azure

1. Use provided `docker-compose.yml` with managed PostgreSQL
2. Set up load balancer for frontend/backend
3. Configure auto-scaling as needed
4. Use managed Redis (ElastiCache, MemoryStore, etc.)

---

## Environment Variables Reference

### Required

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key (32+ hex chars) |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `DATABASE_URL` | Full PostgreSQL connection string |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `False` | Enable debug mode (dev only) |
| `HF_TOKEN` | - | HuggingFace API token for LLM |
| `RIOT_API_KEY` | - | Riot Games API key |
| `REDIS_PASSWORD` | - | Redis authentication |
| `CORS_ORIGINS` | `localhost` | Allowed frontend origins |

---

## Data Pipeline

### Initial Setup

1. **Seed Champions**: `python scripts/seed_champions.py`
   - Fetches all champions from Data Dragon
   - Populates database with base champion data

2. **Scrape Stats**: `POST /api/v1/admin/scrape/stats`
   - Scrapes win rates, pick rates, matchups from LoLalytics
   - Stores in Champion model

3. **Scrape Text**: `POST /api/v1/admin/scrape/text`
   - Scrapes guides from MOBAFire
   - Scrapes discussions from Reddit
   - Stores in ScrapedContent model

4. **Train Neural Network**: `python -c "from app.services.nn_trainer import train_model; train_model()"`
   - Uses scraped champion stats
   - Generates recommendation model
   - Saves to `models/` directory

### Ongoing Updates

- Stats scraping runs daily at 6 AM UTC
- Text scraping runs weekly on Sundays
- Neural network retraining: manual (after major patches)

---

## Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# System status
curl http://localhost:8000/api/v1/admin/status
```

### Logs

```bash
# All services
./deploy.sh logs

# Specific service
./deploy.sh logs backend
./deploy.sh logs frontend
./deploy.sh logs postgres
```

### Database

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d tryndraft

# Backup database
docker compose exec postgres pg_dump -U postgres tryndraft > backup.sql
```

---

## Troubleshooting

### Backend won't start
- Check `DATABASE_URL` is correct
- Verify PostgreSQL is running: `docker compose ps postgres`
- Check logs: `./deploy.sh logs backend`

### Scraping fails
- Verify internet connectivity from container
- Check rate limiting (wait 1-2 hours between full scrapes)
- External sites may block: try different User-Agent

### Neural network errors
- Ensure scraped data exists in database
- Check PyTorch is installed: `pip list | grep torch`
- Verify sufficient memory (2GB+ recommended)

### LLM analysis unavailable
- Check `HF_TOKEN` is set and valid
- HuggingFace may be rate-limiting: wait and retry
- Fallback to rule-based analysis if HF unavailable

---

## Security Checklist

- [ ] Strong passwords for PostgreSQL and Redis
- [ ] SECRET_KEY is unique and random (32+ chars)
- [ ] DEBUG=False in production
- [ ] CORS_ORIGINS limited to your domain
- [ ] SSL/TLS enabled (use reverse proxy)
- [ ] Regular database backups
- [ ] API rate limiting configured
- [ ] No secrets in git repository

---

## Commands Reference

```bash
./deploy.sh dev      # Start development mode
./deploy.sh prod     # Start production mode
./deploy.sh stop     # Stop all services
./deploy.sh logs     # View logs
./deploy.sh status   # Show service status
./deploy.sh scrape   # Trigger stats scraping
./deploy.sh train    # Train neural network
```
