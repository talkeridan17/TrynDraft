"""
League of Legends Draft Data Scraper
Pulls high-ELO ranked solo/duo games from Riot Match-v5 API.

Features:
  - Token bucket rate limiter (respects Riot's 20/s + 100/2min limits)
  - Reads X-App-Rate-Limit-Count response headers to self-correct
  - Pauses automatically on network loss or low battery
  - Resumes cleanly from checkpoint after interruption
  - Safe to run unattended (e.g. on a cloud VM)

Usage:
    export RIOT_API_KEY=RGAPI-xxxx
    pip install requests psutil
    python scraper.py --platform na1 --tier EMERALD --output data/raw

Note on dev keys: Dev keys expire every 24 hours. If you plan to run this
unattended for days, get a Personal API key from the Riot Developer Portal
(register a product — it's free for personal use and doesn't expire daily).
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
import threading
from pathlib import Path
from collections import deque
from dataclasses import dataclass, asdict
from typing import Optional

import requests

# psutil is optional — used for battery detection
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("[warn] psutil not installed. Battery detection disabled. Run: pip install psutil")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scraper.log"),
    ]
)
log = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────────────

QUEUE_RANKED_SOLO = 420
MIN_GAME_DURATION_SECONDS = 15 * 60

# Dev key limits per Riot docs: 20/second, 100/2 minutes
APP_RATE_LIMITS = [
    {"requests": 20,  "window_seconds": 1},
    {"requests": 100, "window_seconds": 120},
]

REGIONAL_HOSTS = {
    "americas": "americas.api.riotgames.com",
    "europe":   "europe.api.riotgames.com",
    "asia":     "asia.api.riotgames.com",
    "sea":      "sea.api.riotgames.com",
}

PLATFORM_TO_REGION = {
    "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas",
    "euw1": "europe",  "eun1": "europe",  "tr1": "europe",   "ru":   "europe",
    "kr":   "asia",    "jp1":  "asia",
    "oc1":  "sea",     "ph2":  "sea",     "sg2": "sea",      "tw2":  "sea",     "vn2": "sea",
}

TIER_DIVISIONS = {
    "EMERALD":     ["I", "II", "III", "IV"],
    "DIAMOND":     ["I", "II", "III", "IV"],
    "MASTER":      ["I"],
    "GRANDMASTER": ["I"],
    "CHALLENGER":  ["I"],
}

PICK_ORDER = [
    (0, 1), (1, 1), (1, 1), (0, 1), (0, 1), (1, 1),  # Phase 1
    (1, 2), (0, 2), (0, 2), (1, 2),                    # Phase 2
]

BAN_ORDER = [
    (0, 1), (0, 1), (1, 1), (1, 1), (0, 1), (1, 1),   # Phase 1: B B R R B R
    (0, 2), (1, 2), (0, 2), (1, 2),                    # Phase 2: B R B R
]

LOW_BATTERY_THRESHOLD = 20   # percent
PAUSE_POLL_INTERVAL   = 30   # seconds between checks while paused


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class BanEvent:
    champion_id: int
    side: int
    phase: int
    pick_turn: int

@dataclass
class PickEvent:
    champion_id: int
    side: int
    phase: int
    pick_turn: int
    lane: str

@dataclass
class DraftRecord:
    match_id: str
    patch: str
    platform: str
    queue_id: int
    game_duration: int
    blue_win: bool
    bans: list
    picks: list
    blue_puuids: list
    red_puuids: list


# ── Token bucket rate limiter ─────────────────────────────────────────────────

class TokenBucketLimiter:
    """
    Implements Riot's dual rate limits (20/s and 100/2min) using sliding
    window tracking. Also reads response headers to self-correct if we
    drift out of sync (e.g. after the scraper resumes from a pause).

    Thread-safe.
    """

    def __init__(self, limits=None):
        self._limits = limits or APP_RATE_LIMITS
        self._buckets = [deque() for _ in self._limits]
        self._lock = threading.Lock()

    def wait(self):
        """Block until it is safe to make the next request."""
        with self._lock:
            now = time.monotonic()
            for i, limit in enumerate(self._limits):
                window  = limit["window_seconds"]
                max_req = limit["requests"]
                bucket  = self._buckets[i]

                # Drop timestamps older than this window
                while bucket and now - bucket[0] > window:
                    bucket.popleft()

                if len(bucket) >= max_req:
                    sleep_until = bucket[0] + window + 0.05
                    wait_time = sleep_until - now
                    if wait_time > 0:
                        log.debug(f"Rate bucket {i}: sleeping {wait_time:.2f}s")
                        time.sleep(wait_time)
                        now = time.monotonic()
                        while bucket and now - bucket[0] > window:
                            bucket.popleft()

            now = time.monotonic()
            for bucket in self._buckets:
                bucket.append(now)

    def adjust_from_headers(self, headers: dict):
        """
        Parse X-App-Rate-Limit-Count and back off if we're near the ceiling.
        Header format: "5:1,40:120" = 5 used in 1s window, 40 used in 120s window.
        """
        count_header = headers.get("X-App-Rate-Limit-Count", "")
        limit_header = headers.get("X-App-Rate-Limit", "")
        if not count_header or not limit_header:
            return
        try:
            counts = {int(w): int(c) for c, w in (p.split(":") for p in count_header.split(","))}
            limits = {int(w): int(m) for m, w in (p.split(":") for p in limit_header.split(","))}
            for window, used in counts.items():
                max_allowed = limits.get(window, 0)
                if max_allowed and used >= max_allowed * 0.90:
                    sleep_time = window * (1 - used / max_allowed) + 0.5
                    log.warning(f"Near rate limit ({used}/{max_allowed} in {window}s). Sleeping {sleep_time:.1f}s")
                    time.sleep(sleep_time)
        except (ValueError, AttributeError):
            pass


# ── Connectivity & battery checks ─────────────────────────────────────────────

def has_network(timeout: int = 5) -> bool:
    try:
        requests.head("https://americas.api.riotgames.com", timeout=timeout)
        return True
    except requests.RequestException:
        return False


def get_battery_status() -> tuple:
    """Returns (percent_or_None, is_plugged_in)."""
    if not HAS_PSUTIL:
        return None, True
    battery = psutil.sensors_battery()
    if battery is None:
        return None, True  # Desktop with no battery
    return battery.percent, battery.power_plugged


def wait_for_safe_conditions(require_plugged_in: bool = False):
    """
    Block until network is up and battery conditions are satisfied.
    Polls every PAUSE_POLL_INTERVAL seconds and logs why it's waiting.
    """
    while True:
        network_ok  = has_network()
        batt_pct, is_plugged = get_battery_status()

        battery_ok = True
        if batt_pct is not None:
            if require_plugged_in and not is_plugged:
                battery_ok = False
                log.warning(f"Paused: not plugged in ({batt_pct:.0f}%). Waiting...")
            elif batt_pct < LOW_BATTERY_THRESHOLD and not is_plugged:
                battery_ok = False
                log.warning(f"Paused: battery low ({batt_pct:.0f}%). Plug in to resume.")

        if not network_ok:
            log.warning("Paused: no network connection. Waiting...")

        if network_ok and battery_ok:
            return

        time.sleep(PAUSE_POLL_INTERVAL)


# ── API client ────────────────────────────────────────────────────────────────

class RiotClient:

    def __init__(self, api_key: str, platform: str = "na1", require_plugged_in: bool = False):
        self.api_key          = api_key
        self.platform         = platform
        self.region           = PLATFORM_TO_REGION[platform]
        self._platform_host   = f"{platform}.api.riotgames.com"
        self._regional_host   = REGIONAL_HOSTS[self.region]
        self._limiter         = TokenBucketLimiter()
        self._require_plugged = require_plugged_in

    def _get(self, host: str, path: str, params: dict = None, retries: int = 3):
        for attempt in range(retries):
            wait_for_safe_conditions(require_plugged_in=self._require_plugged)
            self._limiter.wait()

            url = f"https://{host}{path}"
            try:
                resp = requests.get(url, headers={"X-Riot-Token": self.api_key},
                                    params=params, timeout=10)
            except requests.ConnectionError:
                log.warning("Connection dropped mid-request. Will retry after connectivity check.")
                time.sleep(PAUSE_POLL_INTERVAL)
                continue
            except requests.Timeout:
                log.warning(f"Timeout (attempt {attempt+1}/{retries})")
                time.sleep(5)
                continue

            self._limiter.adjust_from_headers(dict(resp.headers))

            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 10))
                log.warning(f"429 from Riot. Sleeping {retry_after}s")
                time.sleep(retry_after)
            elif resp.status_code == 404:
                return None
            elif resp.status_code in (500, 502, 503, 504):
                wait = 2 ** attempt * 5
                log.warning(f"HTTP {resp.status_code} — retrying in {wait}s")
                time.sleep(wait)
            elif resp.status_code == 403:
                log.error("403 Forbidden — API key likely expired (dev keys expire every 24h). "
                          "Regenerate at https://developer.riotgames.com")
                raise SystemExit(1)
            else:
                log.error(f"HTTP {resp.status_code}: {resp.text[:200]}")
                return None

        log.error(f"All retries exhausted for {path}")
        return None

    def get_league_page(self, tier, division, queue="RANKED_SOLO_5x5", page=1):
        return self._get(self._platform_host, f"/lol/league/v4/entries/{queue}/{tier}/{division}", {"page": page})

    def get_challenger_league(self, queue="RANKED_SOLO_5x5"):
        return self._get(self._platform_host, f"/lol/league/v4/challengerleagues/by-queue/{queue}")

    def get_grandmaster_league(self, queue="RANKED_SOLO_5x5"):
        return self._get(self._platform_host, f"/lol/league/v4/grandmasterleagues/by-queue/{queue}")

    def get_master_league(self, queue="RANKED_SOLO_5x5"):
        return self._get(self._platform_host, f"/lol/league/v4/masterleagues/by-queue/{queue}")

    def get_summoner_by_id(self, summoner_id):
        return self._get(self._platform_host, f"/lol/summoner/v4/summoners/{summoner_id}")

    def get_match_ids_by_puuid(self, puuid, count=20, start=0):
        params = {"queue": QUEUE_RANKED_SOLO, "type": "ranked", "count": count, "start": start}
        return self._get(self._regional_host, f"/lol/match/v5/matches/by-puuid/{puuid}/ids", params) or []

    def get_match(self, match_id):
        return self._get(self._regional_host, f"/lol/match/v5/matches/{match_id}")


# ── Draft extraction ──────────────────────────────────────────────────────────

def extract_patch(game_version: str) -> str:
    parts = game_version.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else game_version


def extract_draft(match: dict) -> Optional[DraftRecord]:
    info = match.get("info", {})
    if info.get("queueId") != QUEUE_RANKED_SOLO: return None
    if info.get("gameDuration", 0) < MIN_GAME_DURATION_SECONDS: return None
    if info.get("gameEndedInEarlySurrender", False): return None

    participants = info.get("participants", [])
    if len(participants) != 10: return None

    teams    = {t["teamId"]: t for t in info.get("teams", [])}
    blue_win = teams.get(100, {}).get("win", False)
    blue     = sorted([p for p in participants if p["teamId"] == 100], key=lambda p: p["participantId"])
    red      = sorted([p for p in participants if p["teamId"] == 200], key=lambda p: p["participantId"])
    if len(blue) != 5 or len(red) != 5: return None

    # Bans
    blue_bans = sorted(teams.get(100, {}).get("bans", []), key=lambda b: b.get("pickTurn", 0))
    red_bans  = sorted(teams.get(200, {}).get("bans", []), key=lambda b: b.get("pickTurn", 0))
    bb, rb    = iter(blue_bans), iter(red_bans)
    bans = []
    for side, phase in BAN_ORDER:
        try:
            raw = next(bb) if side == 0 else next(rb)
            bans.append(asdict(BanEvent(raw.get("championId", -1), side, phase, raw.get("pickTurn", len(bans)))))
        except StopIteration:
            return None

    # Picks
    bi, ri = iter(blue), iter(red)
    picks = []
    for idx, (side, phase) in enumerate(PICK_ORDER):
        try:
            p = next(bi) if side == 0 else next(ri)
            picks.append(asdict(PickEvent(p["championId"], side, phase, idx, p.get("teamPosition", "UNKNOWN"))))
        except StopIteration:
            return None

    meta = match.get("metadata", {})
    return DraftRecord(
        match_id=meta.get("matchId", ""),
        patch=extract_patch(info.get("gameVersion", "")),
        platform=info.get("platformId", "").lower(),
        queue_id=info.get("queueId", 0),
        game_duration=info.get("gameDuration", 0),
        blue_win=blue_win,
        bans=bans, picks=picks,
        blue_puuids=[p["puuid"] for p in blue],
        red_puuids=[p["puuid"] for p in red],
    )


# ── Checkpointing ─────────────────────────────────────────────────────────────

def load_seen(path: Path) -> set:
    if path.exists():
        seen = set(path.read_text().splitlines())
        log.info(f"Resuming — {len(seen)} matches already processed")
        return seen
    return set()

def save_seen(path: Path, seen: set):
    path.write_text("\n".join(seen))


# ── Graceful shutdown ─────────────────────────────────────────────────────────

_shutdown = threading.Event()
def _handle_signal(sig, frame):
    log.info("Shutdown signal received — will stop after current request.")
    _shutdown.set()
signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ── Main scrape loop ──────────────────────────────────────────────────────────

def collect_puuids(client: RiotClient, tier: str, max_summoners: int) -> set:
    puuids = set()

    if tier in ("MASTER", "GRANDMASTER", "CHALLENGER"):
        log.info(f"Fetching {tier} league")
        if tier == "CHALLENGER":
            league_data = client.get_challenger_league()
        elif tier == "GRANDMASTER":
            league_data = client.get_grandmaster_league()
        else:
            league_data = client.get_master_league()

        if league_data:
            entries = league_data.get("entries", [])
            log.info(f"Found {len(entries)} players in {tier}")
            for entry in entries:
                # puuid is returned directly on the entry — no second API call needed
                puuid = entry.get("puuid")
                if puuid:
                    puuids.add(puuid)
                if len(puuids) >= max_summoners:
                    break
    else:
        for division in TIER_DIVISIONS.get(tier, ["I"]):
            page = 1
            while len(puuids) < max_summoners:
                log.info(f"Fetching {tier} {division} page {page} ({len(puuids)} puuids so far)")
                entries = client.get_league_page(tier, division, page=page)
                if not entries:
                    log.info(f"No entries for {tier} {division} page {page}, moving on")
                    break

                found_on_page = 0
                for entry in entries:
                    puuid = entry.get("puuid")
                    if puuid:
                        puuids.add(puuid)
                        found_on_page += 1
                    if len(puuids) >= max_summoners:
                        break

                log.info(f"Page {page}: {found_on_page} puuids found, {len(entries)} entries total")

                # If the page returned fewer entries than a full page, we've exhausted this division
                if len(entries) < 205:
                    break
                page += 1

    log.info(f"Collected {len(puuids)} PUUIDs for {tier}")
    return puuids


def scrape(api_key, platform, tier, output_dir,
           max_summoners=200, matches_per_summoner=20, require_plugged_in=False):

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    seen_path = out / "seen_matches.txt"
    seen = load_seen(seen_path)

    client = RiotClient(api_key, platform, require_plugged_in)
    log.info(f"Starting scrape: {tier} on {platform}")

    puuids = collect_puuids(client, tier, max_summoners)
    records_written = 0

    for i, puuid in enumerate(puuids):
        if _shutdown.is_set(): break
        log.info(f"Summoner {i+1}/{len(puuids)}")

        for match_id in client.get_match_ids_by_puuid(puuid, count=matches_per_summoner):
            if _shutdown.is_set(): break
            if match_id in seen: continue

            raw = client.get_match(match_id)
            seen.add(match_id)

            if raw:
                record = extract_draft(raw)
                if record:
                    (out / f"{match_id}.json").write_text(json.dumps(asdict(record)))
                    records_written += 1

            if records_written % 100 == 0 and records_written > 0:
                log.info(f"Progress: {records_written} records")
                save_seen(seen_path, seen)

    save_seen(seen_path, seen)
    log.info(f"Done. {records_written} records in {output_dir}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform",   default="na1", choices=list(PLATFORM_TO_REGION.keys()))
    parser.add_argument("--tier",       default="EMERALD", choices=list(TIER_DIVISIONS.keys()))
    parser.add_argument("--output",     default="data/raw")
    parser.add_argument("--max-summoners",         type=int, default=200)
    parser.add_argument("--matches-per-summoner",  type=int, default=20)
    parser.add_argument("--require-plugged-in",    action="store_true",
                        help="Pause whenever the laptop is unplugged, not just on low battery")
    args = parser.parse_args()

    api_key = os.environ.get("RIOT_API_KEY")
    if not api_key:
        raise ValueError("Set the RIOT_API_KEY environment variable")

    scrape(
        api_key=api_key,
        platform=args.platform,
        tier=args.tier,
        output_dir=args.output,
        max_summoners=args.max_summoners,
        matches_per_summoner=args.matches_per_summoner,
        require_plugged_in=args.require_plugged_in,
    )