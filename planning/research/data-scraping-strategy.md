# Data Scraping Strategy for TrynDraft

## Overview
This document details the comprehensive data scraping strategy to collect champion statistics, matchup data, and draft compositions for training the neural network and providing real-time recommendations.

---

## 1. Data Sources

### Primary Sources

#### 1.1 U.GG (https://u.gg)
**What to Scrape:**
- Champion win rates, pick rates, ban rates (per role, per rank)
- Matchup win rates (champion vs champion)
- Item build win rates
- Rune/summoner spell statistics
- Patch-specific data

**Data Structure:**
```json
{
  "champion": "Ahri",
  "role": "MID",
  "patch": "16.1.1",
  "rank": "PLATINUM_PLUS",
  "stats": {
    "win_rate": 51.23,
    "pick_rate": 8.45,
    "ban_rate": 3.21,
    "games_played": 145230
  },
  "matchups": {
    "Yasuo": {"win_rate": 52.1, "games": 3245},
    "Zed": {"win_rate": 48.3, "games": 2981}
  }
}
```

**Scraping Method:**
```python
async def scrape_ugg_champion(champion: str, role: str):
    url = f"https://u.gg/lol/champions/{champion}/build?role={role}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=get_headers()) as response:
            html = await response.text()

    soup = BeautifulSoup(html, 'html.parser')

    # Find win rate element (inspect page to get selector)
    win_rate_elem = soup.select_one('.champion-stats .win-rate .value')
    win_rate = float(win_rate_elem.text.strip('%'))

    # Extract matchup data
    matchup_table = soup.select('.matchup-table tbody tr')
    matchups = {}
    for row in matchup_table:
        enemy = row.select_one('.champion-name').text
        wr = float(row.select_one('.win-rate').text.strip('%'))
        games = int(row.select_one('.games').text.replace(',', ''))
        matchups[enemy] = {'win_rate': wr, 'games': games}

    return {
        'champion': champion,
        'role': role,
        'win_rate': win_rate,
        'matchups': matchups
    }
```

**Rate Limiting:** 1 request per 2 seconds, max 100 champions × 5 roles = 500 requests (~17 minutes)

#### 1.2 LoLalytics (https://lolalytics.com)
**What to Scrape:**
- Champion statistics (similar to U.GG, for validation)
- Duo synergy data (which champions work well together)
- Meta tier lists

**Data Structure:**
```json
{
  "champion": "Thresh",
  "synergies": [
    {"champion": "Ezreal", "win_rate_boost": 3.2, "games": 8234},
    {"champion": "Lucian", "win_rate_boost": 2.8, "games": 7123}
  ]
}
```

**Scraping Method:**
```python
async def scrape_lolalytics_synergies(champion: str):
    url = f"https://lolalytics.com/lol/{champion}/synergy/"

    # Similar scraping logic
    synergies = parse_synergy_table(html)
    return synergies
```

#### 1.3 OP.GG (https://op.gg)
**What to Scrape:**
- Korean server meta (often ahead of other regions)
- High-elo player champion pools
- Trending picks

**Note:** OP.GG blocks scrapers more aggressively, use proxies

#### 1.4 Riot Data Dragon (Official API)
**What to Fetch:**
- Champion static data (name, ID, role tags)
- Current patch version
- Champion splash art URLs

**API Endpoints:**
```python
async def fetch_data_dragon():
    # Get latest version
    versions = await fetch_json('https://ddragon.leagueoflegends.com/api/versions.json')
    latest = versions[0]  # e.g., "16.1.1"

    # Get all champions
    url = f'https://ddragon.leagueoflegends.com/cdn/{latest}/data/en_US/champion.json'
    data = await fetch_json(url)

    champions = []
    for champ_id, champ_data in data['data'].items():
        champions.append({
            'id': champ_id,
            'name': champ_data['name'],
            'title': champ_data['title'],
            'tags': champ_data['tags'],  # ['Assassin', 'Mage']
            'image_url': f'https://ddragon.leagueoflegends.com/cdn/{latest}/img/champion/{champ_id}.png'
        })

    return champions
```

**Rate Limiting:** None (official API), but cache results (updates only on patch)

#### 1.5 LoL Esports API (Pro Games)
**What to Scrape:**
- Professional draft sequences (LCS, LEC, LCK, LPL)
- Pick/ban order with timestamps
- Game outcomes

**API Endpoint:**
```python
async def fetch_pro_drafts(league: str = 'LCS'):
    # LoL Esports API (unofficial but accessible)
    url = f'https://esports-api.lolesports.com/persisted/gw/getLive?hl=en-US'

    data = await fetch_json(url)

    for game in data['games']:
        draft = {
            'tournament': game['league'],
            'blue_team': game['blue']['team_name'],
            'red_team': game['red']['team_name'],
            'blue_picks': [p['champion'] for p in game['blue']['picks']],
            'blue_bans': [b['champion'] for b in game['blue']['bans']],
            'red_picks': [p['champion'] for p in game['red']['picks']],
            'red_bans': [b['champion'] for b in game['red']['bans']],
            'winner': game['winner'],
            'game_duration': game['duration']
        }
        yield draft
```

#### 1.6 Riot Official Match API (for training data)
**Requires:** Riot API Key (free, 20 requests/second)

**What to Fetch:**
- Individual ranked game data (Diamond+ for quality)
- Draft order, champion selections
- Game outcome, duration, KDA

**API Usage:**
```python
import aiohttp

RIOT_API_KEY = os.getenv('RIOT_API_KEY')

async def fetch_ranked_matches(region: str, tier: str, count: int):
    """
    Fetch match IDs for a specific tier
    """
    base_url = f'https://{region}.api.riotgames.com'

    # Step 1: Get summoner IDs for tier
    summoners = await fetch_summoners_by_tier(region, tier)

    # Step 2: Get match IDs for each summoner
    match_ids = []
    for summoner in summoners[:count]:
        matches = await fetch_summoner_matches(summoner['puuid'])
        match_ids.extend(matches)

    # Step 3: Fetch match details
    drafts = []
    for match_id in match_ids[:count]:
        match_data = await fetch_match_details(match_id)
        draft = extract_draft_from_match(match_data)
        drafts.append(draft)

    return drafts

async def fetch_match_details(match_id: str):
    url = f'https://americas.api.riotgames.com/lol/match/v5/matches/{match_id}'
    headers = {'X-Riot-Token': RIOT_API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            return await response.json()
```

**Rate Limit:** 20 requests/second, 100 requests/2 minutes

---

## 2. Scraping Architecture

### Option 1: Centralized Scraper (Simple)
```
┌─────────────────────────────────────┐
│     Scheduler (APScheduler)         │
│  - Daily at 3 AM: Scrape U.GG      │
│  - Weekly: Scrape LoLalytics        │
│  - Hourly: Check for new patch     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     Scraper Service (FastAPI)       │
│  - Scrape functions                 │
│  - Rate limiting                    │
│  - Error handling                   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│        PostgreSQL Database          │
│  - champion_stats table             │
│  - matchup_data table               │
│  - draft_compositions table         │
└─────────────────────────────────────┘
```

**Implementation:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=3)  # 3 AM daily
async def daily_champion_stats_scrape():
    logger.info("Starting daily champion stats scrape")

    for champion in ALL_CHAMPIONS:
        for role in ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT']:
            try:
                data = await scrape_ugg_champion(champion, role)
                await save_to_database(data)
                await asyncio.sleep(2)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed to scrape {champion} {role}: {e}")

    logger.info("Daily scrape completed")
```

### Option 2: Distributed Scraper (Scalable)
```
┌─────────────────────┐
│  Celery Beat        │ ──┐
│  (Scheduler)        │   │
└─────────────────────┘   │
                          │ Enqueue tasks
                          ▼
┌──────────────────────────────────┐
│     Redis Task Queue             │
└───────────┬──────────────────────┘
            │
            ├─────────────┬─────────────┬─────────────┐
            ▼             ▼             ▼             ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Celery       │  │ Celery       │  │ Celery       │
│ Worker 1     │  │ Worker 2     │  │ Worker 3     │
│ (U.GG)       │  │ (LoLalytics) │  │ (Riot API)   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┴─────────────────┘
                         │
                         ▼
           ┌──────────────────────────┐
           │   PostgreSQL Database    │
           └──────────────────────────┘
```

**Celery Task Example:**
```python
from celery import Celery

celery_app = Celery('scraper', broker='redis://localhost:6379/0')

@celery_app.task
def scrape_champion_stats(champion: str, role: str):
    """
    Distributed scraping task
    Can run on multiple workers in parallel
    """
    data = scrape_ugg_champion(champion, role)
    save_to_database(data)
    return f"Scraped {champion} {role}"

# Schedule tasks
for champion in ALL_CHAMPIONS:
    for role in ROLES:
        scrape_champion_stats.delay(champion, role)
```

---

## 3. Anti-Scraping Countermeasures

### Challenge 1: IP Bans
**Solution:** Rotating Proxies
```python
from itertools import cycle

PROXY_LIST = [
    'http://proxy1.com:8080',
    'http://proxy2.com:8080',
    'http://proxy3.com:8080',
]

proxy_pool = cycle(PROXY_LIST)

async def fetch_with_proxy(url: str):
    proxy = next(proxy_pool)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, proxy=proxy) as response:
            return await response.text()
```

**Recommended Services:**
- BrightData (https://brightdata.com): $500/month, residential IPs
- SmartProxy: $75/month, 5GB
- ProxyMesh: $10/month, limited

### Challenge 2: Captchas
**Solution:** Headless Browser (Selenium/Playwright)
```python
from playwright.async_api import async_playwright

async def scrape_with_browser(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Set realistic user agent
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        await page.goto(url)
        await page.wait_for_selector('.champion-stats')  # Wait for content

        html = await page.content()
        await browser.close()

        return html
```

### Challenge 3: Rate Limiting
**Solution:** Exponential Backoff
```python
async def fetch_with_retry(url: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await fetch(url)
        except aiohttp.ClientError as e:
            if attempt == max_retries - 1:
                raise

            # Exponential backoff: 2^attempt seconds
            wait_time = 2 ** attempt
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
            await asyncio.sleep(wait_time)
```

### Challenge 4: Dynamic Content (JavaScript-rendered)
**Solution:** Use Selenium or API endpoints directly
```python
# Many sites have hidden API endpoints
# Example: U.GG has internal API

async def scrape_ugg_via_api(champion: str):
    # Discovered by inspecting network tab in browser
    api_url = f'https://stats2.u.gg/lol/1.5/champion_stats/{champion}/1.5.json'

    data = await fetch_json(api_url)
    return data  # Already in JSON format!
```

---

## 4. Data Storage Schema

### Table: champion_stats
```sql
CREATE TABLE champion_stats (
    id SERIAL PRIMARY KEY,
    champion_name VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL,
    patch VARCHAR(20) NOT NULL,
    rank VARCHAR(20) NOT NULL,
    win_rate DECIMAL(5, 2),
    pick_rate DECIMAL(5, 2),
    ban_rate DECIMAL(5, 2),
    games_played INTEGER,
    source VARCHAR(50),  -- 'UGG', 'LOLALYTICS'
    scraped_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(champion_name, role, patch, rank, source)
);

CREATE INDEX idx_champion_patch ON champion_stats(champion_name, patch);
```

### Table: matchup_data
```sql
CREATE TABLE matchup_data (
    id SERIAL PRIMARY KEY,
    champion VARCHAR(50) NOT NULL,
    enemy_champion VARCHAR(50) NOT NULL,
    role VARCHAR(20),
    patch VARCHAR(20),
    win_rate DECIMAL(5, 2),
    games_played INTEGER,
    scraped_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(champion, enemy_champion, role, patch)
);
```

### Table: draft_compositions
```sql
CREATE TABLE draft_compositions (
    id SERIAL PRIMARY KEY,
    patch VARCHAR(20),
    rank VARCHAR(20),
    blue_picks JSONB,  -- ["Aatrox", "Lee Sin", "Ahri", "Jinx", "Thresh"]
    red_picks JSONB,
    blue_bans JSONB,
    red_bans JSONB,
    winner VARCHAR(10),  -- 'BLUE' or 'RED'
    game_duration INTEGER,  -- seconds
    source VARCHAR(50),  -- 'RIOT_API', 'PRO_LCS', 'SCRAPER'
    game_id VARCHAR(100) UNIQUE,  -- Riot match ID
    scraped_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_draft_patch ON draft_compositions(patch);
CREATE INDEX idx_draft_source ON draft_compositions(source);
```

---

## 5. Scraping Schedule

| Task | Frequency | Duration | Data Volume |
|------|-----------|----------|-------------|
| Riot Data Dragon (champions) | On patch release | 5 min | ~5 MB |
| U.GG champion stats | Daily at 3 AM | ~30 min | 170 champions × 5 roles |
| LoLalytics synergies | Weekly (Sunday) | ~1 hour | 170 × 170 pairs |
| Pro match drafts | After each game | ~5 min/game | 20-30 games/day |
| Riot API ranked games | Continuous | Depends on quota | 1000 games/hour |

---

## 6. Error Handling & Monitoring

### Error Types & Responses

```python
class ScraperError(Exception):
    pass

class RateLimitError(ScraperError):
    """Hit rate limit, need to back off"""
    pass

class ParseError(ScraperError):
    """HTML structure changed, scraper needs update"""
    pass

class NetworkError(ScraperError):
    """Connection failed, retry"""
    pass

async def scrape_with_monitoring(url: str):
    try:
        data = await scrape(url)
        metrics.increment('scraper.success')
        return data

    except RateLimitError:
        metrics.increment('scraper.rate_limited')
        logger.warning(f"Rate limited on {url}")
        await asyncio.sleep(60)  # Wait 1 minute
        raise

    except ParseError as e:
        metrics.increment('scraper.parse_error')
        logger.error(f"Parse error on {url}: {e}")
        await send_alert("Scraper needs update", url)
        raise

    except NetworkError:
        metrics.increment('scraper.network_error')
        logger.error(f"Network error on {url}")
        raise
```

### Monitoring Dashboard

**Metrics to Track:**
- Scrape success rate (target: >95%)
- Average scrape duration
- Data freshness (time since last successful scrape)
- Error breakdown (rate limit, parse, network)

**Alerting:**
```python
async def check_data_freshness():
    """Alert if data is stale"""
    latest = await db.query(
        "SELECT MAX(scraped_at) FROM champion_stats"
    ).scalar()

    if datetime.now() - latest > timedelta(hours=48):
        await send_slack_alert(
            "⚠️ Champion stats data is stale!",
            f"Last update: {latest}"
        )
```

---

## 7. Legal & Ethical Considerations

### Terms of Service
- **U.GG, LoLalytics:** No explicit ToS against scraping, but be respectful (rate limit)
- **Riot API:** Official API, follow rate limits strictly
- **OP.GG:** More restrictive, use cautiously

### Best Practices
1. **Respect robots.txt** (check before scraping)
2. **Rate limit aggressively** (1-2 req/sec per domain)
3. **Identify yourself** (use descriptive User-Agent)
4. **Don't resell data** (use only for TrynDraft)
5. **Cache aggressively** (reduce load on source servers)

### Example User-Agent
```python
headers = {
    'User-Agent': 'TrynDraft/1.0 (https://tryndraft.com; scraper@tryndraft.com)'
}
```

---

## 8. Implementation Checklist

### Phase 1: Setup (Week 1)
- [ ] Set up scraping infrastructure (Docker, Celery)
- [ ] Implement U.GG scraper for champion stats
- [ ] Implement Data Dragon fetcher
- [ ] Set up PostgreSQL tables
- [ ] Test scrapers locally

### Phase 2: Scale (Week 2)
- [ ] Implement LoLalytics scraper for synergies
- [ ] Implement Riot API scraper for ranked games
- [ ] Add proxy rotation
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Deploy scrapers to production

### Phase 3: Pro Data (Week 3)
- [ ] Implement LoL Esports API scraper
- [ ] Parse pro match data
- [ ] Store in draft_compositions table
- [ ] Validate data quality

### Phase 4: Automation (Week 4)
- [ ] Schedule daily/weekly scraping jobs
- [ ] Set up alerting (Slack/Discord)
- [ ] Implement auto-retry on failures
- [ ] Test full pipeline end-to-end

---

## 9. Data Quality Validation

```python
async def validate_scraped_data(data: dict):
    """Ensure scraped data is valid before saving"""

    # Check required fields
    required = ['champion', 'role', 'patch', 'win_rate']
    for field in required:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # Validate ranges
    if not (0 <= data['win_rate'] <= 100):
        raise ValueError(f"Invalid win rate: {data['win_rate']}")

    if not (0 <= data['pick_rate'] <= 100):
        raise ValueError(f"Invalid pick rate: {data['pick_rate']}")

    # Check champion exists
    if data['champion'] not in VALID_CHAMPIONS:
        raise ValueError(f"Invalid champion: {data['champion']}")

    return True
```

---

**Last Updated:** 2026-01-11
**Status:** Planning Phase
**Next Step:** Implement U.GG scraper prototype
