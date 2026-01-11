# TrynDraft Production Deployment Strategy

## Overview
This document outlines the production deployment strategy for TrynDraft, including data scraping, database management, infrastructure requirements, and maintenance procedures.

---

## 1. Infrastructure & Hosting

### Recommended Stack
**Option A: AWS (Recommended for Scale)**
- **Frontend**: AWS S3 + CloudFront (static hosting)
- **Backend**: AWS ECS (Fargate) or EC2 instances
- **Database**: AWS RDS (PostgreSQL)
- **Cache**: AWS ElastiCache (Redis)
- **Storage**: S3 for scraped data, training datasets
- **Job Scheduler**: AWS EventBridge + Lambda (for scraping tasks)

**Option B: Railway/Render (Easier Start)**
- **Frontend**: Vercel or Netlify
- **Backend**: Railway or Render
- **Database**: Railway PostgreSQL or Render PostgreSQL
- **Cache**: Railway Redis or Render Redis
- **Scraping**: Railway Cron Jobs or GitHub Actions

**Estimated Monthly Costs**:
- **Hobby/Start**: $15-30/month (Render/Railway free tier + small DB)
- **Production**: $100-200/month (AWS t3.medium EC2, RDS db.t3.micro, S3)
- **Scale**: $500+/month (Multi-region, larger instances, CDN)

---

## 2. Data Scraping Strategy

### What Needs to be Scraped
1. **Champion Statistics** (daily)
   - Win rates, pick rates, ban rates per patch per rank
   - Sources: U.GG, LoLalytics, OP.GG

2. **Champion Matchup Data** (weekly)
   - Counter matchups, synergies
   - Lane win rates vs specific champions

3. **Draft Composition Data** (weekly)
   - Team comp win rates
   - Meta compositions by patch and rank

4. **Professional Drafts** (after each pro game)
   - LCS, LEC, LCK, LPL draft sequences
   - Pick/ban patterns from tournaments

### Scraping Architecture

#### Option 1: Scheduled Jobs (Production-Ready)
```python
# Use APScheduler for in-process scheduling
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Daily scrape at 3 AM UTC
@scheduler.scheduled_job('cron', hour=3)
async def daily_champion_stats():
    await scrape_champion_stats()
    await update_database()

# Weekly scrape on Sunday
@scheduler.scheduled_job('cron', day_of_week='sun', hour=2)
async def weekly_matchup_data():
    await scrape_matchups()
```

#### Option 2: Separate Scraper Service (Scalable)
- Run scrapers as separate Docker containers
- Use Redis queues for task distribution
- Celery workers for distributed scraping
- MongoDB for raw scraped HTML (before processing)

```bash
# docker-compose.yml
services:
  backend:
    # Main API server

  scraper-worker:
    # Celery worker for scraping tasks
    command: celery -A app.scraping.celery worker

  scraper-scheduler:
    # Celery beat for scheduling
    command: celery -A app.scraping.celery beat

  redis:
    # Task queue

  mongodb:
    # Raw scraping cache
```

#### Option 3: Serverless Scraping (AWS Lambda)
- Lambda functions triggered by EventBridge cron
- Store results in S3
- Process and load into RDS via Lambda or Step Functions
- Cost-effective for infrequent scraping

### Scraping Best Practices
1. **Rate Limiting**: Max 1 request per 2 seconds per domain
2. **User Agents**: Rotate user agents, use realistic browser signatures
3. **Proxies**: Use residential proxy service (BrightData, SmartProxy) if blocked
4. **Error Handling**: Retry with exponential backoff (3 retries max)
5. **Data Validation**: Schema validation before database insert
6. **Caching**: Store raw HTML for 7 days (reprocess if needed)
7. **Legal Compliance**: Respect robots.txt, Terms of Service

### Scraper Monitoring
- Log all scraping runs (success/failure, duration, records)
- Alert on consecutive failures (Slack/Discord webhook)
- Track data freshness (alert if no new data in 48 hours)

---

## 3. Database Management

### Schema Design

#### Core Tables
```sql
-- Champion master data (static, updates with new champions)
CREATE TABLE champions (
    id SERIAL PRIMARY KEY,
    riot_id VARCHAR(50) UNIQUE NOT NULL,  -- "Aatrox", "Kaisa"
    name VARCHAR(100) NOT NULL,
    roles VARCHAR[] NOT NULL,  -- ["TOP", "MID"]
    created_at TIMESTAMP DEFAULT NOW()
);

-- Champion statistics (time-series data)
CREATE TABLE champion_stats (
    id SERIAL PRIMARY KEY,
    champion_id INTEGER REFERENCES champions(id),
    patch VARCHAR(20) NOT NULL,  -- "14.5"
    rank VARCHAR(20) NOT NULL,   -- "PLATINUM+"
    role VARCHAR(20) NOT NULL,
    win_rate DECIMAL(5,2),
    pick_rate DECIMAL(5,2),
    ban_rate DECIMAL(5,2),
    games_played INTEGER,
    scraped_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(champion_id, patch, rank, role)
);

-- Draft compositions (LLM training data)
CREATE TABLE draft_compositions (
    id SERIAL PRIMARY KEY,
    patch VARCHAR(20),
    rank VARCHAR(20),
    blue_picks JSONB,  -- ["Aatrox", "Lee Sin", ...]
    red_picks JSONB,
    blue_bans JSONB,
    red_bans JSONB,
    blue_win BOOLEAN,
    game_duration INTEGER,
    source VARCHAR(50),  -- "SOLOQ", "PRO_LCS"
    created_at TIMESTAMP DEFAULT NOW()
);

-- User drafts (user generated data)
CREATE TABLE drafts (
    -- Existing schema from models.py
);
```

### Data Retention Policy
- **Champion Stats**: Keep last 6 patches (6 months)
- **Draft Compositions**: Keep last 3 patches for training data
- **User Drafts**: Keep indefinitely (user data)
- **Scraped HTML Cache**: 7 days
- **Old Logs**: 30 days

### Backup Strategy
- **Daily automated backups** (AWS RDS automated backups or pg_dump)
- **Weekly full backups** to S3 (encrypted)
- **Point-in-time recovery** enabled (last 7 days)
- **Test restore monthly** to ensure backups work

---

## 4. Data Pipeline Architecture

```
┌─────────────────┐
│  Riot API       │
│  Data Dragon    │◄────── Daily fetch (champions, items, patches)
└────────┬────────┘
         │
         ▼
┌─────────────────┐       ┌──────────────────┐
│  Web Scrapers   │       │  Pro Match API   │
│  (U.GG, etc.)   │       │  (LoLEsports)    │
└────────┬────────┘       └────────┬─────────┘
         │                         │
         ▼                         ▼
┌────────────────────────────────────────┐
│         Redis Task Queue               │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│     Celery Workers (Scrapers)          │
│  - Fetch HTML                          │
│  - Parse with BeautifulSoup            │
│  - Validate data                       │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│    PostgreSQL Database                 │
│  - Champion stats                      │
│  - Draft compositions                  │
│  - User data                           │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│    Backend API (FastAPI)               │
│  - Serve stats to frontend             │
│  - LLM inference                       │
│  - User management                     │
└────────────────────────────────────────┘
```

---

## 5. Neural Network Training Pipeline

### Training Data Sources
1. **Historical Drafts**: Scraped SoloQ and Pro drafts (100k+ games)
2. **User-Generated Drafts**: User draft tool usage data
3. **Augmented Data**: Synthetic drafts from Monte Carlo simulations

### Training Schedule
- **Initial Training**: One-time on historical data (1M+ drafts)
- **Incremental Training**: Weekly with new patch data
- **Full Retraining**: Monthly with accumulated data

### Model Storage
- **S3 Bucket**: Store model checkpoints (.pt files)
- **Versioning**: Semantic versioning (v1.2.3)
- **Deployment**: Blue-green deployment (test new model before switching)

```python
# Model serving in production
class DraftRecommendationService:
    def __init__(self):
        self.model = self.load_latest_model()

    def load_latest_model(self):
        # Load from S3 or local cache
        model_path = get_model_from_s3("draft-models/latest.pt")
        return torch.load(model_path)

    async def get_recommendations(self, draft_state):
        # Run inference
        return self.model.predict(draft_state)
```

---

## 6. LLM Integration for Analysis

### Current Setup
- **Model**: Mistral-7B via HuggingFace Inference
- **Token Limit**: 8192 tokens per request
- **Cost**: Free tier (rate limited) or $0.001 per 1k tokens

### Production Considerations
1. **Caching**: Cache LLM responses for identical draft states (30 min TTL)
2. **Rate Limiting**: Max 10 requests/minute per user
3. **Fallback**: If LLM unavailable, return rule-based analysis
4. **Prompt Optimization**: Minimize token usage (compress context)

### Alternative LLM Options
- **GPT-4 Turbo**: More expensive but better quality ($0.01/1k tokens)
- **Claude 3 Haiku**: Fast and cheap ($0.00025/1k tokens)
- **Self-Hosted**: Llama 3 8B on GPU instance (fixed cost)

---

## 7. Monitoring & Maintenance

### Application Monitoring
- **Uptime**: UptimeRobot or Pingdom (free tier)
- **APM**: New Relic, Datadog, or Sentry
- **Logs**: CloudWatch (AWS) or Logtail
- **Metrics**: Prometheus + Grafana

### Key Metrics to Track
- **API Response Time**: p50, p95, p99 latency
- **Error Rate**: 5xx errors per hour
- **Database Connections**: Pool usage
- **Scraping Success Rate**: % of successful scrapes
- **LLM Request Latency**: Time to generate analysis

### Alerts
- **Critical**: API down, database unreachable
- **Warning**: High error rate (>5%), scraper failing
- **Info**: New patch detected, model updated

---

## 8. Deployment Steps (AWS Example)

### Initial Setup
```bash
# 1. Create RDS PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier tryndraft-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username admin

# 2. Create ElastiCache Redis
aws elasticache create-cache-cluster \
  --cache-cluster-id tryndraft-redis \
  --cache-node-type cache.t3.micro \
  --engine redis

# 3. Build and push Docker image
docker build -t tryndraft-backend .
docker tag tryndraft-backend:latest YOUR_ECR_REPO:latest
docker push YOUR_ECR_REPO:latest

# 4. Deploy to ECS
aws ecs create-service \
  --cluster tryndraft \
  --service-name backend \
  --task-definition tryndraft-backend \
  --desired-count 1
```

### Environment Variables (Production)
```bash
DATABASE_URL=postgresql://admin:PASSWORD@RDS_ENDPOINT:5432/tryndraft
REDIS_URL=redis://ELASTICACHE_ENDPOINT:6379
SECRET_KEY=$(openssl rand -hex 32)
HF_TOKEN=your_huggingface_token
CORS_ORIGINS=["https://tryndraft.com"]
DEBUG=False
LOG_LEVEL=INFO
```

### CI/CD Pipeline (GitHub Actions)
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run tests
        run: |
          cd backend && pytest
          cd ../frontend && npm test

      - name: Build Docker image
        run: docker build -t tryndraft-backend .

      - name: Push to ECR
        run: |
          # Push to AWS ECR

      - name: Deploy to ECS
        run: |
          # Update ECS service
```

---

## 9. Cost Breakdown (AWS)

| Service | Instance Type | Monthly Cost |
|---------|--------------|--------------|
| EC2 (Backend) | t3.medium | $30 |
| RDS (PostgreSQL) | db.t3.micro | $15 |
| ElastiCache (Redis) | cache.t3.micro | $12 |
| S3 (Storage) | 100 GB | $3 |
| CloudFront (CDN) | 1 TB transfer | $85 |
| Lambda (Scrapers) | 1M requests | $0.20 |
| **Total** | | **~$145/month** |

---

## 10. Scaling Considerations

### When to Scale
- **Users**: >1000 concurrent users
- **Requests**: >100 req/sec
- **Database**: >1000 connections
- **Scraping**: >100k games/day

### Horizontal Scaling
- **Backend**: Add more ECS tasks (load balanced)
- **Database**: Read replicas for analytics queries
- **Redis**: Redis Cluster for distributed cache
- **Scrapers**: More Celery workers

### Caching Strategy
```python
# Cache frequently accessed data
@cache.memoize(timeout=3600)  # 1 hour
async def get_champion_stats(patch: str, rank: str):
    return await db.query(ChampionStats).filter(...)

# Cache LLM responses
@cache.memoize(timeout=1800)  # 30 min
async def get_draft_analysis(draft_hash: str):
    return await llm_service.analyze(draft_state)
```

---

## 11. Security Checklist

- [x] .env files not committed (.gitignore configured)
- [x] Secrets in environment variables only
- [x] Database credentials rotated regularly
- [x] HTTPS enabled (SSL certificates via Let's Encrypt)
- [x] CORS properly configured
- [x] SQL injection prevented (use parameterized queries)
- [x] Rate limiting enabled (10 req/sec per IP)
- [x] Input validation on all endpoints
- [x] JWT tokens with short expiration (1 hour)
- [x] Password hashing with bcrypt

---

## 12. Next Steps (Priority Order)

1. **Fix Backend** ✅ (NumPy compatibility fixed)
2. **Test Backend Locally**: Ensure all endpoints work
3. **Set Up Database**: Run migrations, seed champions
4. **Test Scrapers**: Verify U.GG, LoLalytics scrapers work
5. **Deploy to Staging**: Railway or Render free tier
6. **Load Test**: Simulate 100 concurrent users
7. **Deploy to Production**: AWS or preferred platform
8. **Set Up Monitoring**: Sentry + Uptime monitoring
9. **Schedule Scraping**: Daily stats, weekly matchups
10. **Train Initial Model**: Use historical draft data

---

## Contact & Support

For questions or issues, refer to the main README.md or open a GitHub issue.

**Last Updated**: 2026-01-09
**Version**: 1.0
