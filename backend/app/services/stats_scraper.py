"""
Champion Statistics Scraper - Riot API Based
Adapted from soloq_scraper.py for TrynDraft backend integration.

Scrapes real match data from Riot API to get:
- Win rates per champion per role PER RANK
- Matchup data (champion vs champion win rates)
- Synergy data (champion combo win rates)

Designed to run in background on deployment with rate limiting.
"""

import os
import time
import logging
import socket
import json
from datetime import datetime, timezone
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum

import requests

from .progress_tracker import get_progress_tracker

logger = logging.getLogger(__name__)


class Rank(Enum):
    """Ranked tiers for data collection."""
    IRON = "IRON"
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"
    EMERALD = "EMERALD"
    DIAMOND = "DIAMOND"
    MASTER = "MASTER"
    GRANDMASTER = "GRANDMASTER"
    CHALLENGER = "CHALLENGER"


class ScraperConfig:
    """Configuration for the Riot API scraper."""

    API_KEY = os.getenv("RIOT_API_KEY")
    BASE_URL = "https://{region}.api.riotgames.com/lol"
    DATA_DRAGON_URL = "https://ddragon.leagueoflegends.com/realms/{region}.json"

    # Regions to scrape (prioritized by player population)
    REGIONS = [
        "na1", "euw1", "kr",  # Major regions first
        "eun1", "br1", "tr1", "jp1",
        "la1", "la2", "oc1", "ph2", "sg2", "th2", "tw2", "vn2"
    ]

    MATCH_REGION_MAP = {
        region:
            "americas" if region in ["na1", "br1", "la1", "la2"] else
            "europe" if region in ["euw1", "eun1", "tr1"] else
            "asia" if region in ["kr", "jp1"] else
            "sea"
        for region in REGIONS
    }

    # Rate limits (conservative to avoid 429s)
    # Development API key: 20 requests per second, 100 per 2 minutes
    # Production API key: 500 per 10 seconds, 30000 per 10 minutes
    RATE_LIMITS = {
        "app": {"per_two_minutes": 95, "window_seconds": 120},
        "endpoints": {
            "league": {"per_two_minutes": 85, "window_seconds": 120},
            "match": {"per_two_minutes": 85, "window_seconds": 120},
            "summoner": {"per_two_minutes": 85, "window_seconds": 120}
        }
    }

    MAX_MATCHES_PER_PLAYER = 20  # Keep low for faster iteration
    REQUEST_TIMEOUT = 15
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 3]

    # Output directory structure:
    # scraped_data/
    #   riot_stats/
    #     patch_16.1/
    #       IRON/
    #         champion_stats.json
    #         synergies.json
    #       BRONZE/
    #         ...
    OUTPUT_DIR = Path("scraped_data/riot_stats")

    ROLE_MAP = {
        "TOP": "Top",
        "JUNGLE": "Jungle",
        "MIDDLE": "Mid",
        "BOTTOM": "ADC",
        "UTILITY": "Support"
    }

    # Number of players to sample per rank per region
    PLAYERS_PER_RANK = {
        Rank.CHALLENGER: 50,      # Small population
        Rank.GRANDMASTER: 50,     # Small population
        Rank.MASTER: 100,         # Medium population
        Rank.DIAMOND: 100,        # Medium population
        Rank.EMERALD: 100,        # Medium population
        Rank.PLATINUM: 100,       # Large population
        Rank.GOLD: 100,           # Largest population
        Rank.SILVER: 100,         # Large population
        Rank.BRONZE: 50,          # Medium population
        Rank.IRON: 30,            # Small population
    }

    @classmethod
    def get_role_name(cls, position: str) -> str:
        return cls.ROLE_MAP.get(position, position)

    @classmethod
    def get_current_patch(cls) -> str:
        try:
            response = requests.get(
                cls.DATA_DRAGON_URL.format(region="na"),
                timeout=5
            )
            response.raise_for_status()
            full_version = response.json()['v']
            year, patch_num = full_version.split('.')[:2]
            return f"{year}.{patch_num}"
        except Exception as e:
            logger.warning(f"Failed to get current patch: {e}")
            current_year = datetime.now().year % 100
            return f"{current_year}.1"

    @classmethod
    def get_output_dir(cls, patch: str, rank: Rank) -> Path:
        """Get output directory for a specific patch and rank."""
        return cls.OUTPUT_DIR / f"patch_{patch}" / rank.value

    @classmethod
    def validate(cls) -> bool:
        if not cls.API_KEY:
            raise ValueError("RIOT_API_KEY environment variable not set")
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return True


class ChampionStats:
    """Tracks stats for a single champion."""

    def __init__(self):
        self.roles = defaultdict(lambda: {
            "games": 0, "wins": 0, "kills": 0, "deaths": 0, "assists": 0
        })
        self.matchups = defaultdict(lambda: defaultdict(lambda: {
            "games": 0, "wins": 0
        }))

    def add_game(self, win: bool, kills: int, deaths: int, assists: int,
                 role: str, opponent: Optional[str] = None):
        role_stats = self.roles[role]
        role_stats["games"] += 1
        role_stats["wins"] += int(win)
        role_stats["kills"] += kills
        role_stats["deaths"] += deaths
        role_stats["assists"] += assists

        if opponent:
            matchup = self.matchups[role][opponent]
            matchup["games"] += 1
            matchup["wins"] += int(win)

    def to_dict(self) -> Dict:
        """Convert to serializable dict."""
        result = {"roles": {}, "matchups": {}}

        for role, data in self.roles.items():
            if data["games"] > 0:
                games = data["games"]
                result["roles"][role] = {
                    "games": games,
                    "wins": data["wins"],
                    "win_rate": round((data["wins"] / games) * 100, 2),
                    "avg_kills": round(data["kills"] / games, 2),
                    "avg_deaths": round(data["deaths"] / games, 2),
                    "avg_assists": round(data["assists"] / games, 2),
                    "kda": round((data["kills"] + data["assists"]) / max(1, data["deaths"]), 2)
                }

        for role, matchups in self.matchups.items():
            result["matchups"][role] = {}
            for opponent, data in matchups.items():
                if data["games"] >= 3:  # Minimum games threshold
                    result["matchups"][role][opponent] = {
                        "games": data["games"],
                        "wins": data["wins"],
                        "win_rate": round((data["wins"] / data["games"]) * 100, 2)
                    }

        return result


class SynergyStats:
    """Tracks synergy stats between champions."""

    def __init__(self):
        self.games = 0
        self.wins = 0

    def add_game(self, win: bool):
        self.games += 1
        self.wins += int(win)


class RateLimiter:
    """Precision rate limiter for Riot API."""

    def __init__(self):
        self.request_times = {
            "app": deque(maxlen=ScraperConfig.RATE_LIMITS["app"]["per_two_minutes"]),
            "league": deque(maxlen=ScraperConfig.RATE_LIMITS["endpoints"]["league"]["per_two_minutes"]),
            "match": deque(maxlen=ScraperConfig.RATE_LIMITS["endpoints"]["match"]["per_two_minutes"]),
            "summoner": deque(maxlen=ScraperConfig.RATE_LIMITS["endpoints"]["summoner"]["per_two_minutes"])
        }
        self.total_requests = 0

    def wait(self, endpoint_type: str) -> None:
        now = time.time()
        self.total_requests += 1
        delays = []

        for limit_type in ["app", endpoint_type]:
            queue = self.request_times[limit_type]
            if limit_type == "app":
                max_requests = ScraperConfig.RATE_LIMITS["app"]["per_two_minutes"]
                window = ScraperConfig.RATE_LIMITS["app"]["window_seconds"]
            else:
                max_requests = ScraperConfig.RATE_LIMITS["endpoints"][endpoint_type]["per_two_minutes"]
                window = ScraperConfig.RATE_LIMITS["endpoints"][endpoint_type]["window_seconds"]

            if len(queue) >= max_requests:
                elapsed = now - queue[0]
                if elapsed < window:
                    delays.append((queue[0] + window) - now)

        if delays:
            wait_time = max(delays)
            logger.debug(f"Rate limiting: waiting {wait_time:.1f}s")
            time.sleep(wait_time)

        current_time = time.time()
        self.request_times["app"].append(current_time)
        self.request_times[endpoint_type].append(current_time)


class RiotAPIClient:
    """Client for Riot API with rate limiting and retry logic."""

    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.session = requests.Session()
        self.session.headers.update({
            "X-Riot-Token": ScraperConfig.API_KEY,
            "Accept": "application/json",
            "User-Agent": "TrynDraft/1.0"
        })
        self.total_requests = 0
        self.failed_requests = 0
        self.last_connection_state = True

    def check_connectivity(self) -> None:
        """Check internet connection."""
        while True:
            try:
                socket.create_connection(("1.1.1.1", 53), timeout=5)
                if not self.last_connection_state:
                    logger.info("Internet connection restored")
                    self.last_connection_state = True
                return
            except OSError:
                if self.last_connection_state:
                    logger.warning("Internet connection lost, waiting...")
                    self.last_connection_state = False
                time.sleep(10)

    def get_json(self, url: str, endpoint_type: str) -> Optional[Dict]:
        """Make API request with retry logic."""
        for attempt in range(ScraperConfig.MAX_RETRIES):
            self.rate_limiter.wait(endpoint_type)

            try:
                response = self.session.get(url, timeout=ScraperConfig.REQUEST_TIMEOUT)
                self.total_requests += 1

                if response.status_code == 404:
                    return None
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 10))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    time.sleep(retry_after)
                    continue
                elif response.status_code == 403:
                    logger.error("API key invalid or expired")
                    return None

                response.raise_for_status()
                return response.json()

            except requests.exceptions.ConnectionError:
                self.failed_requests += 1
                self.check_connectivity()
                continue
            except requests.exceptions.RequestException as e:
                self.failed_requests += 1
                logger.debug(f"Request failed (attempt {attempt+1}): {e}")
                time.sleep(ScraperConfig.RETRY_DELAYS[attempt])

        return None

    # League endpoints for different ranks
    def get_challenger_league(self, region: str) -> Optional[Dict]:
        url = f"{ScraperConfig.BASE_URL.format(region=region)}/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5"
        return self.get_json(url, "league")

    def get_grandmaster_league(self, region: str) -> Optional[Dict]:
        url = f"{ScraperConfig.BASE_URL.format(region=region)}/league/v4/grandmasterleagues/by-queue/RANKED_SOLO_5x5"
        return self.get_json(url, "league")

    def get_master_league(self, region: str) -> Optional[Dict]:
        url = f"{ScraperConfig.BASE_URL.format(region=region)}/league/v4/masterleagues/by-queue/RANKED_SOLO_5x5"
        return self.get_json(url, "league")

    def get_league_entries(self, region: str, tier: str, division: str, page: int = 1) -> Optional[List[Dict]]:
        """Get league entries for a specific tier and division (IRON-DIAMOND)."""
        url = f"{ScraperConfig.BASE_URL.format(region=region)}/league/v4/entries/RANKED_SOLO_5x5/{tier}/{division}?page={page}"
        return self.get_json(url, "league")

    def get_summoner_by_id(self, region: str, summoner_id: str) -> Optional[Dict]:
        """Get summoner info including PUUID."""
        url = f"{ScraperConfig.BASE_URL.format(region=region)}/summoner/v4/summoners/{summoner_id}"
        return self.get_json(url, "summoner")

    def get_match_history(self, puuid: str, region: str, count: int = 20) -> Optional[List[str]]:
        match_region = ScraperConfig.MATCH_REGION_MAP[region]
        url = f"https://{match_region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&count={count}"
        return self.get_json(url, "match")

    def get_match_details(self, match_id: str, region: str) -> Optional[Dict]:
        match_region = ScraperConfig.MATCH_REGION_MAP[region]
        url = f"https://{match_region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return self.get_json(url, "match")


class RankDataStore:
    """Stores scraped data for a specific rank."""

    SYNERGY_COMBOS = ["jungle_mid", "jungle_adc", "support_adc", "top_jungle", "support_jungle"]

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.global_stats: Dict[str, ChampionStats] = defaultdict(ChampionStats)
        self.synergies = {combo: defaultdict(SynergyStats) for combo in self.SYNERGY_COMBOS}
        self.processed_matches: set = set()
        self.load_existing_data()

    def load_existing_data(self):
        """Load previously scraped data if exists."""
        tracker_file = self.output_dir / "scrape_tracker.json"
        if tracker_file.exists():
            try:
                with open(tracker_file) as f:
                    data = json.load(f)
                    self.processed_matches = set(data.get("processed_matches", []))
                logger.info(f"Loaded {len(self.processed_matches)} previously processed matches")
            except Exception as e:
                logger.warning(f"Could not load existing tracker: {e}")

    def save(self, patch: str):
        """Save all data to files."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Save champion stats
        champion_data = {}
        for champ_name, stats in self.global_stats.items():
            champion_data[champ_name] = stats.to_dict()

        stats_file = self.output_dir / "champion_stats.json"
        with open(stats_file, 'w') as f:
            json.dump({
                "patch": patch,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "total_champions": len(champion_data),
                "total_matches": len(self.processed_matches),
                "champions": champion_data
            }, f, indent=2)

        # Save synergies
        synergy_data = {}
        for combo, combos in self.synergies.items():
            synergy_data[combo] = []
            for champs, stats in combos.items():
                if stats.games >= 5:
                    synergy_data[combo].append({
                        "champions": list(champs),
                        "games": stats.games,
                        "wins": stats.wins,
                        "win_rate": round((stats.wins / stats.games) * 100, 2)
                    })

        synergy_file = self.output_dir / "synergies.json"
        with open(synergy_file, 'w') as f:
            json.dump({
                "patch": patch,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "synergies": synergy_data
            }, f, indent=2)

        # Save tracker
        tracker_file = self.output_dir / "scrape_tracker.json"
        # Keep only last 10k match IDs to prevent file from growing too large
        matches_to_save = list(self.processed_matches)
        if len(matches_to_save) > 10000:
            matches_to_save = matches_to_save[-10000:]

        with open(tracker_file, 'w') as f:
            json.dump({
                "processed_matches": matches_to_save,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "total_matches_processed": len(self.processed_matches)
            }, f)

        logger.info(f"Saved data to {self.output_dir}")


class RiotStatsScraper:
    """
    Main scraper class for collecting stats from Riot API.

    Collects data per rank so we can train rank-specific neural networks.
    Designed to run in background on deployment.
    """

    def __init__(self):
        """Initialize the scraper."""
        ScraperConfig.validate()

        self.rate_limiter = RateLimiter()
        self.api = RiotAPIClient(self.rate_limiter)
        self.current_patch = ScraperConfig.get_current_patch()

        # Data stores per rank
        self.data_stores: Dict[Rank, RankDataStore] = {}

        self.start_time = time.time()
        self.stats = {
            "players_processed": 0,
            "matches_processed": 0,
            "api_requests": 0,
            "failed_requests": 0
        }

        logger.info(f"Initialized scraper for patch {self.current_patch}")

    def _get_data_store(self, rank: Rank) -> RankDataStore:
        """Get or create data store for a rank."""
        if rank not in self.data_stores:
            output_dir = ScraperConfig.get_output_dir(self.current_patch, rank)
            self.data_stores[rank] = RankDataStore(output_dir)
        return self.data_stores[rank]

    def run(self,
            ranks: List[Rank] = None,
            regions: List[str] = None,
            save_interval: int = 50) -> Dict[str, Any]:
        """
        Run the scraper.

        Args:
            ranks: List of ranks to scrape (None = all ranks)
            regions: List of regions to scrape (None = major regions)
            save_interval: Save data after this many matches

        Returns:
            Dict with scraping results
        """
        if ranks is None:
            ranks = list(Rank)
        if regions is None:
            regions = ["na1", "euw1", "kr"]  # Major regions by default

        logger.info(f"Starting scrape for ranks: {[r.value for r in ranks]}")
        logger.info(f"Regions: {regions}")

        tracker = get_progress_tracker()

        try:
            for rank in ranks:
                logger.info(f"=== Scraping {rank.value} ===")
                tracker.start_stats_scrape(rank.value, patch=self.current_patch)

                for region in regions:
                    self._scrape_rank_region(rank, region, save_interval, tracker)

                # Save after each rank
                data_store = self._get_data_store(rank)
                data_store.save(self.current_patch)

                # Update tracker with completion
                tracker.complete_stats_scrape(
                    rank.value,
                    champions_with_data=len(data_store.global_stats)
                )

            self._log_final_stats()
            return self._get_results()

        except KeyboardInterrupt:
            logger.info("Scrape interrupted by user, saving progress...")
            for data_store in self.data_stores.values():
                data_store.save(self.current_patch)
            raise
        except Exception as e:
            logger.error(f"Scrape failed: {e}")
            for rank in ranks:
                tracker.update_stats_scrape(rank.value, error=str(e))
            for data_store in self.data_stores.values():
                data_store.save(self.current_patch)
            raise

    def _scrape_rank_region(self, rank: Rank, region: str, save_interval: int, tracker=None):
        """Scrape a specific rank in a specific region."""
        players = self._get_players_for_rank(rank, region)

        if not players:
            logger.warning(f"No players found for {rank.value} in {region}")
            return

        max_players = ScraperConfig.PLAYERS_PER_RANK.get(rank, 50)
        players = players[:max_players]

        logger.info(f"Processing {len(players)} {rank.value} players from {region}")

        data_store = self._get_data_store(rank)
        matches_since_save = 0

        for i, player in enumerate(players):
            puuid = player.get("puuid")

            # For lower ranks, we need to look up PUUID from summoner ID
            if not puuid and "summonerId" in player:
                summoner = self.api.get_summoner_by_id(region, player["summonerId"])
                if summoner:
                    puuid = summoner.get("puuid")

            if not puuid:
                continue

            new_matches = self._process_player(puuid, region, data_store)
            matches_since_save += new_matches
            self.stats["players_processed"] += 1

            if new_matches > 0:
                logger.debug(f"Player {i+1}/{len(players)}: {new_matches} matches")

            # Update progress tracker periodically
            if tracker and (i + 1) % 10 == 0:
                tracker.update_stats_scrape(
                    rank.value,
                    matches_processed=len(data_store.processed_matches),
                    champions_with_data=len(data_store.global_stats)
                )

            # Periodic save
            if matches_since_save >= save_interval:
                data_store.save(self.current_patch)
                matches_since_save = 0

    def _get_players_for_rank(self, rank: Rank, region: str) -> List[Dict]:
        """Get player entries for a specific rank."""
        if rank == Rank.CHALLENGER:
            league = self.api.get_challenger_league(region)
            return league.get("entries", []) if league else []

        elif rank == Rank.GRANDMASTER:
            league = self.api.get_grandmaster_league(region)
            return league.get("entries", []) if league else []

        elif rank == Rank.MASTER:
            league = self.api.get_master_league(region)
            return league.get("entries", []) if league else []

        else:
            # For IRON through DIAMOND, use league entries endpoint
            # Get from division I (top of the tier)
            entries = self.api.get_league_entries(region, rank.value, "I")
            return entries if entries else []

    def _process_player(self, puuid: str, region: str, data_store: RankDataStore) -> int:
        """Process a player's match history. Returns number of new matches."""
        match_ids = self.api.get_match_history(puuid, region, ScraperConfig.MAX_MATCHES_PER_PLAYER)
        if not match_ids:
            return 0

        new_matches = 0
        for match_id in match_ids:
            if match_id in data_store.processed_matches:
                continue

            match = self.api.get_match_details(match_id, region)
            if not match or "info" not in match:
                continue

            # Check patch
            game_version = match["info"].get("gameVersion", "")
            parts = game_version.split('.')
            if len(parts) >= 2:
                match_patch = f"{parts[0]}.{parts[1]}"
                if match_patch != self.current_patch:
                    continue

            self._process_match(match, data_store)
            data_store.processed_matches.add(match_id)
            self.stats["matches_processed"] += 1
            new_matches += 1

        return new_matches

    def _process_match(self, match: Dict, data_store: RankDataStore):
        """Extract stats from a single match."""
        try:
            participants = match["info"]["participants"]
            teams = defaultdict(list)

            for p in participants:
                team_id = p["teamId"]
                role = ScraperConfig.get_role_name(p.get("teamPosition", ""))
                champ = p.get("championName", "Unknown")

                if not role or role == "":
                    continue

                teams[team_id].append((role, champ, p))

                # Add base game stats
                stats = data_store.global_stats[champ]
                stats.add_game(
                    win=p["win"],
                    kills=p["kills"],
                    deaths=p["deaths"],
                    assists=p["assists"],
                    role=role
                )

            # Process matchups (lane opponents)
            for p in participants:
                role = ScraperConfig.get_role_name(p.get("teamPosition", ""))
                if role not in ("Top", "Mid", "ADC", "Support"):
                    continue

                champ = p.get("championName", "Unknown")
                opponent = self._get_lane_opponent(p, participants)

                if opponent:
                    opp_champ = opponent.get("championName", "Unknown")
                    data_store.global_stats[champ].add_game(
                        win=p["win"],
                        kills=p["kills"],
                        deaths=p["deaths"],
                        assists=p["assists"],
                        role=role,
                        opponent=opp_champ
                    )

            # Process synergies
            for team_id, team_players in teams.items():
                role_champs = {role: champ for role, champ, _ in team_players}
                team_win = any(p["win"] for _, _, p in team_players)

                if "Jungle" in role_champs and "Mid" in role_champs:
                    key = (role_champs["Jungle"], role_champs["Mid"])
                    data_store.synergies["jungle_mid"][key].add_game(team_win)

                if "Jungle" in role_champs and "ADC" in role_champs:
                    key = (role_champs["Jungle"], role_champs["ADC"])
                    data_store.synergies["jungle_adc"][key].add_game(team_win)

                if "Support" in role_champs and "ADC" in role_champs:
                    key = (role_champs["Support"], role_champs["ADC"])
                    data_store.synergies["support_adc"][key].add_game(team_win)

                if "Top" in role_champs and "Jungle" in role_champs:
                    key = (role_champs["Top"], role_champs["Jungle"])
                    data_store.synergies["top_jungle"][key].add_game(team_win)

                if "Support" in role_champs and "Jungle" in role_champs:
                    key = (role_champs["Support"], role_champs["Jungle"])
                    data_store.synergies["support_jungle"][key].add_game(team_win)

        except Exception as e:
            logger.warning(f"Error processing match: {e}")

    def _get_lane_opponent(self, player: Dict, participants: List[Dict]) -> Optional[Dict]:
        """Find the lane opponent for a player."""
        try:
            position = player.get("teamPosition")
            team_id = player["teamId"]
            return next(
                (p for p in participants
                 if p["teamId"] != team_id and p.get("teamPosition") == position),
                None
            )
        except Exception:
            return None

    def _log_final_stats(self):
        """Log final scraping statistics."""
        total_time = (time.time() - self.start_time) / 60
        logger.info("=" * 50)
        logger.info("Scrape Complete!")
        logger.info(f"Runtime: {total_time:.1f} minutes")
        logger.info(f"Players processed: {self.stats['players_processed']}")
        logger.info(f"Matches processed: {self.stats['matches_processed']}")
        logger.info(f"API requests: {self.api.total_requests}")
        logger.info(f"Failed requests: {self.api.failed_requests}")

        for rank, store in self.data_stores.items():
            logger.info(f"  {rank.value}: {len(store.global_stats)} champions, {len(store.processed_matches)} matches")

        logger.info("=" * 50)

    def _get_results(self) -> Dict[str, Any]:
        """Get scraping results summary."""
        results = {
            "patch": self.current_patch,
            "runtime_minutes": round((time.time() - self.start_time) / 60, 2),
            "stats": self.stats,
            "ranks_scraped": {}
        }

        for rank, store in self.data_stores.items():
            results["ranks_scraped"][rank.value] = {
                "champions": len(store.global_stats),
                "matches": len(store.processed_matches),
                "output_dir": str(store.output_dir)
            }

        return results


# Convenience functions for different scrape modes
def run_quick_scrape() -> Dict[str, Any]:
    """Quick scrape for testing (Challenger only, 1 region)."""
    scraper = RiotStatsScraper()
    return scraper.run(
        ranks=[Rank.CHALLENGER],
        regions=["na1"],
        save_interval=20
    )


def run_high_elo_scrape() -> Dict[str, Any]:
    """Scrape high elo (Challenger, GM, Master, Diamond)."""
    scraper = RiotStatsScraper()
    return scraper.run(
        ranks=[Rank.CHALLENGER, Rank.GRANDMASTER, Rank.MASTER, Rank.DIAMOND],
        regions=["na1", "euw1", "kr"],
        save_interval=50
    )


def run_full_scrape() -> Dict[str, Any]:
    """Full scrape of all ranks."""
    scraper = RiotStatsScraper()
    return scraper.run(
        ranks=list(Rank),
        regions=["na1", "euw1", "kr"],
        save_interval=100
    )


def run_single_rank_scrape(rank: str, regions: List[str] = None) -> Dict[str, Any]:
    """Scrape a single rank."""
    rank_enum = Rank[rank.upper()]
    scraper = RiotStatsScraper()
    return scraper.run(
        ranks=[rank_enum],
        regions=regions or ["na1", "euw1", "kr"],
        save_interval=50
    )


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    mode = sys.argv[1] if len(sys.argv) > 1 else "quick"

    if mode == "quick":
        result = run_quick_scrape()
    elif mode == "high_elo":
        result = run_high_elo_scrape()
    elif mode == "full":
        result = run_full_scrape()
    elif mode.upper() in [r.value for r in Rank]:
        result = run_single_rank_scrape(mode)
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python stats_scraper.py [quick|high_elo|full|RANK_NAME]")
        sys.exit(1)

    print(f"\nResults: {json.dumps(result, indent=2)}")
