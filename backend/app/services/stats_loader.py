"""
Stats Loader Service
Loads scraped champion statistics from JSON files into the database.
Supports per-rank data for rank-specific neural networks.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import Champion
from ..database import SessionLocal
from .stats_scraper import Rank, ScraperConfig

logger = logging.getLogger(__name__)


class StatsLoader:
    """
    Loads scraped stats from JSON files into the database.
    Supports loading from per-rank directories for rank-specific recommendations.
    """

    def __init__(self, db: Session = None):
        """
        Initialize the stats loader.

        Args:
            db: Database session (creates one if not provided)
        """
        self.db = db
        self._owns_session = False
        if self.db is None:
            self.db = SessionLocal()
            self._owns_session = True

    def __del__(self):
        if self._owns_session and self.db:
            self.db.close()

    def get_available_patches(self) -> List[str]:
        """Get list of available patch directories."""
        if not ScraperConfig.OUTPUT_DIR.exists():
            return []

        patches = []
        for path in ScraperConfig.OUTPUT_DIR.iterdir():
            if path.is_dir() and path.name.startswith("patch_"):
                patches.append(path.name.replace("patch_", ""))

        return sorted(patches, reverse=True)  # Newest first

    def get_available_ranks(self, patch: str) -> List[str]:
        """Get list of available ranks for a patch."""
        patch_dir = ScraperConfig.OUTPUT_DIR / f"patch_{patch}"
        if not patch_dir.exists():
            return []

        ranks = []
        for path in patch_dir.iterdir():
            if path.is_dir() and path.name in [r.value for r in Rank]:
                ranks.append(path.name)

        return ranks

    def load_rank_stats(self, patch: str, rank: str) -> Optional[Dict[str, Any]]:
        """
        Load champion stats for a specific patch and rank.

        Args:
            patch: Patch version (e.g., "16.1")
            rank: Rank tier (e.g., "GOLD", "DIAMOND")

        Returns:
            Dict with champion stats data or None if not found
        """
        stats_file = ScraperConfig.OUTPUT_DIR / f"patch_{patch}" / rank / "champion_stats.json"

        if not stats_file.exists():
            logger.warning(f"Stats file not found: {stats_file}")
            return None

        with open(stats_file, 'r') as f:
            return json.load(f)

    def load_rank_synergies(self, patch: str, rank: str) -> Optional[Dict[str, Any]]:
        """
        Load synergy data for a specific patch and rank.

        Args:
            patch: Patch version
            rank: Rank tier

        Returns:
            Dict with synergy data or None if not found
        """
        synergy_file = ScraperConfig.OUTPUT_DIR / f"patch_{patch}" / rank / "synergies.json"

        if not synergy_file.exists():
            logger.warning(f"Synergy file not found: {synergy_file}")
            return None

        with open(synergy_file, 'r') as f:
            return json.load(f)

    def update_database_from_rank(self, patch: str, rank: str) -> Dict[str, Any]:
        """
        Update database champions with stats from a specific rank.

        This updates the Champion model with win rates, matchups, and synergies
        from the scraped data for the specified rank.

        Args:
            patch: Patch version
            rank: Rank tier to load

        Returns:
            Dict with update results
        """
        results = {
            "patch": patch,
            "rank": rank,
            "champions_updated": 0,
            "errors": []
        }

        # Load stats
        stats_data = self.load_rank_stats(patch, rank)
        if not stats_data:
            results["errors"].append(f"No stats found for {rank} patch {patch}")
            return results

        champions_data = stats_data.get("champions", {})

        for champ_name, champ_stats in champions_data.items():
            champion = self._find_champion(champ_name)
            if not champion:
                continue

            try:
                # Update win rate from primary role
                roles_data = champ_stats.get("roles", {})
                if roles_data:
                    primary_role = max(roles_data.keys(), key=lambda r: roles_data[r].get("games", 0))
                    primary_stats = roles_data[primary_role]

                    # win_rate stored as integer (5123 = 51.23%)
                    win_rate = primary_stats.get("win_rate", 50.0)
                    champion.win_rate = int(win_rate * 100)

                    # Calculate pick rate from games
                    games = primary_stats.get("games", 0)
                    # Normalize: 100 games = ~5% pick rate
                    pick_rate = min(2000, int((games / 20) * 100))
                    champion.pick_rate = pick_rate

                # Update matchups (counters)
                matchups_data = champ_stats.get("matchups", {})
                if matchups_data:
                    counters = {}
                    for role, role_matchups in matchups_data.items():
                        role_key = self._normalize_role(role)
                        counters[role_key] = {}
                        for opponent, matchup_stats in role_matchups.items():
                            counters[role_key][opponent] = {
                                "wins": matchup_stats.get("wins", 0),
                                "games": matchup_stats.get("games", 0),
                                "win_rate": matchup_stats.get("win_rate", 50.0)
                            }
                    champion.counters = counters

                champion.patch = patch
                results["champions_updated"] += 1

            except Exception as e:
                results["errors"].append(f"Error updating {champ_name}: {str(e)}")

        # Load and update synergies
        synergy_data = self.load_rank_synergies(patch, rank)
        if synergy_data:
            self._update_synergies(synergy_data)

        # Commit changes
        try:
            self.db.commit()
            logger.info(f"Updated {results['champions_updated']} champions from {rank} patch {patch}")
        except Exception as e:
            self.db.rollback()
            results["errors"].append(f"Database commit failed: {str(e)}")

        return results

    def _update_synergies(self, synergy_data: Dict[str, Any]):
        """Update champion synergy data from scraped synergies."""
        synergies = synergy_data.get("synergies", {})

        # Build synergy lookup per champion
        champion_synergies: Dict[str, Dict[str, Any]] = {}

        for combo_type, combos in synergies.items():
            for combo in combos:
                champions = combo.get("champions", [])
                win_rate = combo.get("win_rate", 50.0)
                games = combo.get("games", 0)

                if len(champions) < 2:
                    continue

                for i, champ in enumerate(champions):
                    if champ not in champion_synergies:
                        champion_synergies[champ] = {}

                    for j, partner in enumerate(champions):
                        if i != j:
                            if partner not in champion_synergies[champ]:
                                champion_synergies[champ][partner] = {"wins": 0, "games": 0}
                            champion_synergies[champ][partner]["games"] += games
                            champion_synergies[champ][partner]["wins"] += int(games * win_rate / 100)

        # Update champions in database
        for champ_name, synergies in champion_synergies.items():
            champion = self._find_champion(champ_name)
            if champion:
                final_synergies = {}
                for partner, data in synergies.items():
                    if data["games"] >= 5:
                        final_synergies[partner] = {
                            "wins": data["wins"],
                            "games": data["games"],
                            "win_rate": round((data["wins"] / data["games"]) * 100, 2)
                        }
                champion.synergies = final_synergies

    def load_all_ranks(self, patch: str = None) -> Dict[str, Any]:
        """
        Load stats from all available ranks for a patch.

        This is useful for creating a combined dataset or for
        updating the database with the most comprehensive data.

        Args:
            patch: Patch version (uses latest if not specified)

        Returns:
            Dict with loading results per rank
        """
        if patch is None:
            patches = self.get_available_patches()
            if not patches:
                return {"error": "No patches available"}
            patch = patches[0]  # Latest patch

        results = {
            "patch": patch,
            "ranks": {},
            "total_champions_updated": 0
        }

        ranks = self.get_available_ranks(patch)
        for rank in ranks:
            rank_result = self.update_database_from_rank(patch, rank)
            results["ranks"][rank] = rank_result
            results["total_champions_updated"] += rank_result.get("champions_updated", 0)

        return results

    def get_stats_for_nn_training(self, patch: str, rank: str) -> Optional[Dict[str, Any]]:
        """
        Get stats in a format ready for neural network training.

        Returns champion stats organized for feature extraction:
        - Per champion: roles, win rates, matchups, synergies
        - Formatted for the NN trainer to consume directly

        Args:
            patch: Patch version
            rank: Rank tier

        Returns:
            Dict with training-ready data
        """
        stats = self.load_rank_stats(patch, rank)
        synergies = self.load_rank_synergies(patch, rank)

        if not stats:
            return None

        training_data = {
            "patch": patch,
            "rank": rank,
            "champions": {},
            "synergy_pairs": []
        }

        champions_data = stats.get("champions", {})

        for champ_name, champ_stats in champions_data.items():
            roles = champ_stats.get("roles", {})
            matchups = champ_stats.get("matchups", {})

            # Aggregate stats across roles
            total_games = sum(r.get("games", 0) for r in roles.values())
            total_wins = sum(r.get("wins", 0) for r in roles.values())

            if total_games == 0:
                continue

            training_data["champions"][champ_name] = {
                "total_games": total_games,
                "win_rate": round((total_wins / total_games) * 100, 2),
                "roles": {
                    role: {
                        "games": data.get("games", 0),
                        "win_rate": data.get("win_rate", 50.0),
                        "kda": data.get("kda", 2.0)
                    }
                    for role, data in roles.items()
                },
                "matchups": matchups
            }

        # Process synergies into pairs
        if synergies:
            for combo_type, combos in synergies.get("synergies", {}).items():
                for combo in combos:
                    if combo.get("games", 0) >= 10:  # Minimum threshold
                        training_data["synergy_pairs"].append({
                            "type": combo_type,
                            "champions": combo.get("champions", []),
                            "games": combo.get("games", 0),
                            "win_rate": combo.get("win_rate", 50.0)
                        })

        return training_data

    def _find_champion(self, name: str) -> Optional[Champion]:
        """Find a champion in the database by name."""
        # Try exact match
        champion = self.db.query(Champion).filter(Champion.name == name).first()
        if champion:
            return champion

        # Try key match (lowercase, no spaces)
        key = name.lower().replace(" ", "").replace("'", "").replace(".", "")
        champion = self.db.query(Champion).filter(Champion.key == key).first()
        if champion:
            return champion

        # Try ID match
        champion = self.db.query(Champion).filter(Champion.id == key).first()
        return champion

    def _normalize_role(self, role: str) -> str:
        """Normalize role name."""
        role_map = {
            "top": "TOP", "jungle": "JUNGLE", "mid": "MID",
            "middle": "MID", "adc": "ADC", "bottom": "ADC",
            "support": "SUPPORT", "utility": "SUPPORT"
        }
        return role_map.get(role.lower(), role.upper())


def load_stats_to_database(patch: str = None, rank: str = None) -> Dict[str, Any]:
    """
    Convenience function to load stats into database.

    Args:
        patch: Patch version (latest if None)
        rank: Specific rank (all ranks if None)

    Returns:
        Dict with loading results
    """
    loader = StatsLoader()

    if rank:
        if patch is None:
            patches = loader.get_available_patches()
            patch = patches[0] if patches else None
        if patch:
            return loader.update_database_from_rank(patch, rank)
        return {"error": "No patch data available"}

    return loader.load_all_ranks(patch)


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    loader = StatsLoader()

    # Show available data
    patches = loader.get_available_patches()
    print(f"Available patches: {patches}")

    if patches:
        latest = patches[0]
        ranks = loader.get_available_ranks(latest)
        print(f"Ranks for patch {latest}: {ranks}")

        if len(sys.argv) > 1:
            rank = sys.argv[1].upper()
            if rank in ranks:
                results = loader.update_database_from_rank(latest, rank)
                print(f"Results: {json.dumps(results, indent=2)}")
            else:
                print(f"Rank {rank} not available. Available: {ranks}")
        else:
            results = loader.load_all_ranks(latest)
            print(f"Results: {json.dumps(results, indent=2)}")
