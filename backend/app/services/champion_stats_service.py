"""
Champion Statistics Service
Integrates Riot API scraper with database to collect and store champion statistics
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models import Champion
from ..core.config import settings

logger = logging.getLogger(__name__)


class ChampionStatsService:
    """Service for managing champion statistics from Riot API."""

    def __init__(self, db: Session):
        self.db = db
        self.riot_api_key = settings.RIOT_API_KEY

    async def update_champion_stats(
        self,
        champion_name: str,
        patch: str,
        win_rate: Optional[float] = None,
        pick_rate: Optional[float] = None,
        ban_rate: Optional[float] = None,
        role_stats: Optional[Dict] = None,
        matchup_data: Optional[Dict] = None,
        synergy_data: Optional[Dict] = None
    ) -> Champion:
        """
        Update or create champion statistics in the database.

        Args:
            champion_name: Champion name
            patch: Game patch version (e.g., "14.5")
            win_rate: Overall win rate percentage
            pick_rate: Pick rate percentage
            ban_rate: Ban rate percentage
            role_stats: Statistics per role
            matchup_data: Matchup win rates vs other champions
            synergy_data: Synergy win rates with other champions
        """
        # Find champion by name (ignore patch to prevent duplicates)
        # We want ONE entry per champion, updated with latest stats
        champion = self.db.query(Champion).filter(
            Champion.name == champion_name
        ).first()

        if not champion:
            # Try by normalized key
            normalized_key = champion_name.lower().replace(" ", "").replace("'", "")
            champion = self.db.query(Champion).filter(
                Champion.key == normalized_key
            ).first()

        if not champion:
            # Create new champion entry (should rarely happen if seeded properly)
            logger.info(f"Creating new champion entry: {champion_name}")
            champion = Champion(
                id=champion_name.lower().replace(" ", "").replace("'", ""),
                name=champion_name,
                key=champion_name.lower().replace(" ", "").replace("'", ""),
                patch=patch
            )
            self.db.add(champion)
        else:
            # Update existing champion with new patch
            champion.patch = patch

        # Update statistics
        if win_rate is not None:
            champion.win_rate = int(win_rate * 100)  # Store as integer percentage
        if pick_rate is not None:
            champion.pick_rate = int(pick_rate * 100)
        if ban_rate is not None:
            champion.ban_rate = int(ban_rate * 100)

        # Update role-specific data
        if role_stats:
            # Store the most played role in the roles field
            most_played_roles = sorted(
                role_stats.items(),
                key=lambda x: x[1].get('games', 0),
                reverse=True
            )
            champion.roles = [role for role, _ in most_played_roles[:2]]

        # Update matchup data (counters)
        if matchup_data:
            champion.counters = matchup_data

        # Update synergy data
        if synergy_data:
            champion.synergies = synergy_data

        champion.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(champion)

        logger.info(f"Updated stats for {champion_name} on patch {patch}")
        return champion

    def get_champion_stats(
        self,
        champion_name: str,
        patch: Optional[str] = None
    ) -> Optional[Champion]:
        """Get champion statistics from database."""
        query = self.db.query(Champion).filter(Champion.name == champion_name)

        if patch:
            query = query.filter(Champion.patch == patch)
        else:
            # Get most recent patch
            query = query.order_by(Champion.updated_at.desc())

        return query.first()

    def get_top_champions_by_win_rate(
        self,
        role: Optional[str] = None,
        patch: Optional[str] = None,
        limit: int = 10
    ) -> List[Champion]:
        """Get top champions by win rate."""
        query = self.db.query(Champion).filter(Champion.win_rate.isnot(None))

        if patch:
            query = query.filter(Champion.patch == patch)

        if role:
            # Filter by role - champions that have this role in their roles list
            query = query.filter(Champion.roles.contains([role]))

        return query.order_by(Champion.win_rate.desc()).limit(limit).all()

    def get_matchup_win_rate(
        self,
        champion_name: str,
        opponent_name: str,
        patch: Optional[str] = None
    ) -> Optional[float]:
        """Get win rate for a specific matchup."""
        champion = self.get_champion_stats(champion_name, patch)

        if not champion or not champion.counters:
            return None

        # Look through counters data for this matchup
        for role, matchups in champion.counters.items():
            if opponent_name in matchups:
                matchup_data = matchups[opponent_name]
                games = matchup_data.get('games', 0)
                wins = matchup_data.get('wins', 0)
                if games > 0:
                    return (wins / games) * 100

        return None

    def get_synergy_win_rate(
        self,
        champion_name: str,
        ally_name: str,
        patch: Optional[str] = None
    ) -> Optional[float]:
        """Get win rate when playing with a specific ally."""
        champion = self.get_champion_stats(champion_name, patch)

        if not champion or not champion.synergies:
            return None

        # Look through synergy data
        if ally_name in champion.synergies:
            synergy_data = champion.synergies[ally_name]
            games = synergy_data.get('games', 0)
            wins = synergy_data.get('wins', 0)
            if games > 0:
                return (wins / games) * 100

        return None

    def get_all_champions_for_patch(self, patch: str) -> List[Champion]:
        """Get all champions with statistics for a specific patch."""
        return self.db.query(Champion).filter(Champion.patch == patch).all()

    def get_available_patches(self) -> List[str]:
        """Get list of patches with champion data."""
        patches = self.db.query(Champion.patch).distinct().all()
        return sorted([p[0] for p in patches if p[0]], reverse=True)
