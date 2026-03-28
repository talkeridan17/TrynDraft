#!/usr/bin/env python3
from dataclasses import dataclass
import os
import time
import csv
import requests
from collections import defaultdict
import threading
import logging
from collections import deque
import sys


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("apad.log"),
    ])
log = logging.getLogger(__name__)

API_KEY = os.getenv("RIOT_API_KEY")  # export RIOT_API_KEY=...
PLATFORM = "na1"      # e.g., na1, euw1, kr
ROUTING = "americas"  # americas, europe, asia, sea depending on PLATFORM
QUEUE_ID = 420        # Ranked Solo/Duo
SEASON = 16
MIN_GAME_DURATION_SECONDS = 15 * 60

# How many players per apex tier to sample
MAX_PLAYERS_PER_TIER = 800       # tune for rate limits

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

MATCH_IDS = set()

@dataclass
class ChampionDamageOutput:
    champion_id: int
    avg_attack_damage: float
    avg_ap_damage: float
    avg_true_damage: float
    num_games: int

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


PLATFORM_TO_REGION = {
    "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas",
    "euw1": "europe",  "eun1": "europe",  "tr1": "europe",   "ru":   "europe",
    "kr":   "asia",    "jp1":  "asia",
    "oc1":  "sea",     "ph2":  "sea",     "sg2": "sea",      "tw2":  "sea",     "vn2": "sea",
}


class RiotClient:

    def __init__(self, api_key: str, platform: str = "na1"):
        self.api_key = api_key
        self.platform = platform
        self.region = PLATFORM_TO_REGION.get(platform, "americas")
        self._platform_host = f"{platform}.api.riotgames.com"
        self._regional_host = REGIONAL_HOSTS.get(self.region, "americas.api.riotgames.com")
        self._limiter = TokenBucketLimiter()

    def _get(self, host: str, path: str, params: dict = None, retries: int = 3):
        for attempt in range(retries):
            self._limiter.wait()
            url = f"https://{host}{path}"
            try:
                resp = requests.get(
                    url,
                    headers={"X-Riot-Token": self.api_key},
                    params=params,
                    timeout=10
                )
            except requests.RequestException as e:
                log.warning(f"Request error (attempt {attempt+1}/{retries}): {e}")
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
                log.error("403 Forbidden — API key likely expired")
                raise SystemExit(1)
            else:
                log.error(f"HTTP {resp.status_code}: {resp.text[:200]}")
                return None

        log.error(f"All retries exhausted for {path}")
        return None

    def get_challenger_league(self, queue="RANKED_SOLO_5x5"):
        return self._get(self._platform_host, f"/lol/league/v4/challengerleagues/by-queue/{queue}")

    def get_grandmaster_league(self, queue="RANKED_SOLO_5x5"):
        return self._get(self._platform_host, f"/lol/league/v4/grandmasterleagues/by-queue/{queue}")

    def get_master_league(self, queue="RANKED_SOLO_5x5"):
        return self._get(self._platform_host, f"/lol/league/v4/masterleagues/by-queue/{queue}")

    def get_league_page(self, tier, division, queue="RANKED_SOLO_5x5", page=1):
        return self._get(self._platform_host, f"/lol/league/v4/entries/{queue}/{tier}/{division}", {"page": page})

    def get_match_ids_by_puuid(self, puuid, count=20, start=0):
        params = {"queue": QUEUE_ID, "type": "ranked", "count": count, "start": start}
        return self._get(self._regional_host, f"/lol/match/v5/matches/by-puuid/{puuid}/ids", params) or []

    def get_match(self, match_id):
        return self._get(self._regional_host, f"/lol/match/v5/matches/{match_id}")


def collect_puuids(client: RiotClient, max_players: int) -> set:
    """Collect PUUIDs from Challenger, Grandmaster, and Master leagues."""
    puuids = set()

    for league_fn in [client.get_challenger_league, client.get_grandmaster_league, client.get_master_league]:
        if len(puuids) >= max_players:
            break
        data = league_fn()
        if data:
            for entry in data.get("entries", []):
                puuid = entry.get("puuid")
                if puuid:
                    puuids.add(puuid)
                if len(puuids) >= max_players:
                    break

    log.info(f"Collected {len(puuids)} PUUIDs")
    return puuids


def extract_damage_data(match: dict) -> list:
    """Extract damage breakdown for each participant in a match."""
    info = match.get("info", {})

    if info.get("queueId") != QUEUE_ID:
        return []
    if info.get("gameDuration", 0) < MIN_GAME_DURATION_SECONDS:
        return []
    if info.get("gameEndedInEarlySurrender", False):
        return []

    participants = info.get("participants", [])
    if len(participants) != 10:
        return []

    damage_data = []
    for p in participants:
        champion_id = p.get("championId")
        phys = p.get("physicalDamageDealtToChampions", 0)
        magic = p.get("magicDamageDealtToChampions", 0)
        true = p.get("trueDamageDealtToChampions", 0)

        if champion_id and (phys > 0 or magic > 0 or true > 0):
            damage_data.append({
                "champion_id": champion_id,
                "physical": phys,
                "magic": magic,
                "true": true
            })

    return damage_data


def aggregate_damage(damage_records: list) -> dict:
    """Aggregate damage data by champion."""
    champ_data = defaultdict(lambda: {"physical": [], "magic": [], "true": []})

    for record in damage_records:
        cid = record["champion_id"]
        champ_data[cid]["physical"].append(record["physical"])
        champ_data[cid]["magic"].append(record["magic"])
        champ_data[cid]["true"].append(record["true"])

    results = {}
    for cid, dmg in champ_data.items():
        n = len(dmg["physical"])
        if n > 0:
            results[cid] = ChampionDamageOutput(
                champion_id=cid,
                avg_attack_damage=sum(dmg["physical"]) / n,
                avg_ap_damage=sum(dmg["magic"]) / n,
                avg_true_damage=sum(dmg["true"]) / n,
                num_games=n
            )

    return results


def export_to_csv(champ_damage: dict, filepath: str):
    """Export champion damage data to CSV."""
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["champion_id", "avg_attack_damage", "avg_ap_damage", "avg_true_damage", "num_games"])
        for cid in sorted(champ_damage.keys()):
            cdo = champ_damage[cid]
            writer.writerow([
                cdo.champion_id,
                f"{cdo.avg_attack_damage:.2f}",
                f"{cdo.avg_ap_damage:.2f}",
                f"{cdo.avg_true_damage:.2f}",
                cdo.num_games
            ])
    log.info(f"Exported {len(champ_damage)} champions to {filepath}")


def main():
    if not API_KEY:
        log.error("Set RIOT_API_KEY environment variable")
        raise SystemExit(1)

    client = RiotClient(API_KEY, PLATFORM)

    puuids = collect_puuids(client, MAX_PLAYERS_PER_TIER)

    all_damage_records = []
    seen_matches = MATCH_IDS.copy()

    for i, puuid in enumerate(puuids):
        log.info(f"Processing summoner {i+1}/{len(puuids)}")
        match_ids = client.get_match_ids_by_puuid(puuid, count=20)

        for match_id in match_ids:
            if match_id in seen_matches:
                continue
            seen_matches.add(match_id)

            match_data = client.get_match(match_id)
            if match_data:
                dmg_data = extract_damage_data(match_data)
                all_damage_records.extend(dmg_data)

            if len(all_damage_records) % 100 == 0:
                log.info(f"Collected {len(all_damage_records)} damage records so far")

    log.info(f"Total damage records collected: {len(all_damage_records)}")

    champ_damage = aggregate_damage(all_damage_records)
    export_to_csv(champ_damage, "champion_damage_breakdown.csv")
    log.info("Done!")


if __name__ == "__main__":
    main()
