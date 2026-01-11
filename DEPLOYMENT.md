# TrynDraft - Production Deployment Guide

This guide covers deploying TrynDraft to production using Docker, cloud platforms, and best practices.

---

## 📋 Pre-Deployment Checklist

### 1. Environment Variables
- [ ] Generate strong `SECRET_KEY` with `openssl rand -hex 32`
- [ ] Set `DEBUG=False` in production
- [ ] Configure PostgreSQL connection string
- [ ] Set secure `POSTGRES_PASSWORD`
- [ ] Add production domain to `CORS_ORIGINS`
- [ ] Obtain Riot API Key (Production tier recommended)
- [ ] Get HuggingFace API Token for LLM
- [ ] Configure Redis password

### 2. Security
- [ ] All `.env` files excluded from git
- [ ] Database backups configured
- [ ] SSL/TLS certificates ready
- [ ] Firewall rules configured
- [ ] Rate limiting enabled

### 3. Data Collection
- [ ] Run `make seed` to populate champion data
- [ ] Run `make scrape-stats` for Riot API statistics
- [ ] Verify database migrations completed

---

## 🐳 Docker Deployment (Recommended)

### Step 1: Build and Deploy

\`\`\`bash
# Build and start all services
docker-compose up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f
\`\`\`

### Step 2: Initialize Database

\`\`\`bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Seed champion data
docker-compose exec backend python scripts/seed_champions.py
\`\`\`

### Step 3: Verify Deployment

- Frontend: `http://localhost`
- Backend API: `http://localhost/api/docs`
- Health Check: `http://localhost/api/health`

---

See README.md for detailed deployment instructions, cloud platform guides, and troubleshooting.
