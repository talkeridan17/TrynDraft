"""
Recommendations API for TrynDraft Frontend
Provides endpoints for champion sorting and LLM analysis box
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import logging

from app.database import get_db
from app import models
from app.auth import get_current_user_optional
from app.services.draft_nn_service import get_nn_service
from app.services.champion_stats_service import ChampionStatsService
from app.services.llm_service import LLMService
from app.services.llm_prompts import get_prompts_service, DraftContext
from app.services.data_dragon import DataDragonService

logger = logging.getLogger(__name__)

router = APIRouter()
data_dragon = DataDragonService()
llm_service = LLMService()

# Standard draft order: position -> role
POSITION_TO_ROLE = {0: 'Top', 1: 'Jungle', 2: 'Mid', 3: 'ADC', 4: 'Support'}


def get_current_slot_role(turn: int, user_side: str) -> tuple[str, int]:
    """
    Determine the role being picked based on turn number.

    Draft turn order (standard):
    - Turns 0-9: Ban phase (doesn't apply)
    - Turn 10: Blue 1st pick (position 0 = TOP)
    - Turn 11: Red 1st pick (position 0 = TOP)
    - Turn 12: Red 2nd pick (position 1 = JUNGLE)
    - Turn 13: Blue 2nd pick (position 1 = JUNGLE)
    - Turn 14: Blue 3rd pick (position 2 = MID)
    - Turn 15: Red 3rd pick (position 2 = MID)
    - Turn 16: Red 4th pick (position 3 = ADC)
    - Turn 17: Blue 4th pick (position 3 = ADC)
    - Turn 18: Blue 5th pick (position 4 = SUPPORT)
    - Turn 19: Red 5th pick (position 4 = SUPPORT)

    Returns:
        (role, position) tuple
    """
    if turn < 10:
        # Ban phase - return None for role
        return None, -1

    # Pick order mapping: turn -> (side, position)
    pick_order = {
        10: ('BLUE', 0),  # Blue 1st
        11: ('RED', 0),   # Red 1st
        12: ('RED', 1),   # Red 2nd
        13: ('BLUE', 1),  # Blue 2nd
        14: ('BLUE', 2),  # Blue 3rd
        15: ('RED', 2),   # Red 3rd
        16: ('RED', 3),   # Red 4th
        17: ('BLUE', 3),  # Blue 4th
        18: ('BLUE', 4),  # Blue 5th
        19: ('RED', 4),   # Red 5th
    }

    side, position = pick_order.get(turn, ('BLUE', 0))
    role = POSITION_TO_ROLE.get(position, 'Mid')

    return role, position


def load_scraped_role_stats(elo: str, patch: str) -> Dict[str, Dict]:
    """
    Load role-specific stats from scraped data files.
    Returns dict mapping champion name -> role_stats
    """
    # Try to find scraped data
    base_path = Path("scraped_data/riot_stats")

    # Try exact patch, then major.minor
    patch_variants = [patch]
    if '.' in patch:
        patch_variants.append('.'.join(patch.split('.')[:2]))

    for p in patch_variants:
        data_path = base_path / f"patch_{p}" / elo.upper() / "champion_stats.json"
        if data_path.exists():
            try:
                with open(data_path) as f:
                    data = json.load(f)
                    champions = data.get("champions", {})

                    # Extract role_stats for each champion
                    role_stats_map = {}
                    for champ_name, champ_data in champions.items():
                        roles = champ_data.get("roles", {})
                        total_games = sum(r.get("games", 0) for r in roles.values())
                        role_stats_map[champ_name] = {
                            "role_stats": roles,
                            "total_games": total_games,
                            "matchups": champ_data.get("matchups", {})
                        }

                    logger.info(f"Loaded role stats for {len(role_stats_map)} champions from {data_path}")
                    return role_stats_map
            except Exception as e:
                logger.warning(f"Failed to load scraped data from {data_path}: {e}")

    return {}


def predict_enemy_role(champion_name: str, role_stats: Dict) -> tuple[str, float]:
    """
    Predict what role an enemy champion is playing based on their most common role.
    Returns (predicted_role, confidence) where confidence is based on game distribution.
    """
    if not role_stats:
        return "Mid", 0.0

    stats = role_stats.get(champion_name, {}).get("role_stats", {})
    if not stats:
        return "Mid", 0.0

    # Find role with most games
    total_games = sum(r.get("games", 0) for r in stats.values())
    if total_games == 0:
        return "Mid", 0.0

    best_role = max(stats.keys(), key=lambda r: stats[r].get("games", 0), default="Mid")
    best_role_games = stats.get(best_role, {}).get("games", 0)
    confidence = best_role_games / total_games if total_games > 0 else 0.0

    return best_role, confidence


def detect_matchup_for_role(
    target_role: str,
    enemy_picks: List[Any],
    scraped_role_stats: Dict[str, Dict],
    user_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    Detect if there's a likely matchup for the target role.

    Args:
        target_role: The role we're picking for (e.g., "Jungle")
        enemy_picks: List of enemy picks (can be dicts or strings)
        scraped_role_stats: Role stats for champions
        user_override: User-specified matchup champion (overrides prediction)

    Returns:
        {
            "matchup_champion": str or None,
            "matchup_type": "counter" | "blind" | "unknown",
            "confidence": float (0-1),
            "reasoning": str,
            "all_enemy_roles": Dict[str, str]  # champion -> predicted role
        }
    """
    # Extract enemy champion names
    enemy_champs = []
    for pick in enemy_picks:
        if isinstance(pick, dict) and pick.get('champion'):
            enemy_champs.append(pick['champion'])
        elif isinstance(pick, str) and pick:
            enemy_champs.append(pick)

    if not enemy_champs:
        return {
            "matchup_champion": None,
            "matchup_type": "blind",
            "confidence": 1.0,
            "reasoning": "No enemy picks yet - blind pick situation",
            "all_enemy_roles": {}
        }

    # Predict roles for all enemy champions
    enemy_role_predictions = {}
    for champ in enemy_champs:
        role, conf = predict_enemy_role(champ, scraped_role_stats)
        enemy_role_predictions[champ] = {"role": role, "confidence": conf}

    # User override takes priority
    if user_override:
        # Special case: user explicitly wants blind pick mode
        if user_override == "__blind__":
            return {
                "matchup_champion": None,
                "matchup_type": "blind",
                "confidence": 1.0,
                "reasoning": f"User selected blind pick mode for {target_role}",
                "all_enemy_roles": {c: p["role"] for c, p in enemy_role_predictions.items()}
            }
        # User specified an enemy champion as their matchup
        elif user_override in enemy_champs:
            return {
                "matchup_champion": user_override,
                "matchup_type": "counter",
                "confidence": 1.0,
                "reasoning": f"User specified {user_override} as {target_role} opponent",
                "all_enemy_roles": {c: p["role"] for c, p in enemy_role_predictions.items()}
            }

    # Find enemy champion most likely playing target role
    target_role_normalized = target_role.capitalize()
    best_matchup = None
    best_confidence = 0.0

    for champ, prediction in enemy_role_predictions.items():
        if prediction["role"].capitalize() == target_role_normalized:
            if prediction["confidence"] > best_confidence:
                best_matchup = champ
                best_confidence = prediction["confidence"]

    if best_matchup and best_confidence >= 0.3:  # At least 30% of games in that role
        return {
            "matchup_champion": best_matchup,
            "matchup_type": "counter",
            "confidence": best_confidence,
            "reasoning": f"Assuming {best_matchup} is {target_role} ({best_confidence*100:.0f}% of games)",
            "all_enemy_roles": {c: p["role"] for c, p in enemy_role_predictions.items()}
        }
    else:
        return {
            "matchup_champion": None,
            "matchup_type": "blind",
            "confidence": 1.0,
            "reasoning": f"No clear {target_role} opponent detected - suggesting strong blind picks",
            "all_enemy_roles": {c: p["role"] for c, p in enemy_role_predictions.items()}
        }


@router.get("/models")
async def get_available_models() -> Dict[str, Any]:
    """
    Get information about available trained models.

    Returns which rank-specific models are available for recommendations.
    """
    nn_service = get_nn_service()
    available = nn_service.get_available_models()

    return {
        "models": available,
        "has_any_model": any(available.values()),
        "recommendation_mode": "neural_network" if any(available.values()) else "rule_based"
    }


@router.post("/sorted-champions")
async def get_sorted_champions(
    data: Dict[str, Any],
    current_user: Optional[models.User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all champions sorted by recommendation score for the champion picker.

    This endpoint is called by the frontend to sort champions in the picker
    based on neural network recommendations.

    Request body:
    {
        "phase": "BAN" | "PICK",
        "turn": 0-19,
        "side": "BLUE" | "RED",
        "role": "TOP" | "JUNGLE" | "MID" | "ADC" | "SUPPORT",
        "elo": "IRON" - "CHALLENGER",
        "patch": "14.24",
        "bans_blue": ["ChampName", ...],
        "bans_red": ["ChampName", ...],
        "picks_blue": [{"champion": "Name", "role": "ROLE"}, ...],
        "picks_red": [{"champion": "Name", "role": "ROLE"}, ...]
    }

    Returns:
    {
        "champions": [
            {
                "id": "aatrox",
                "name": "Aatrox",
                "score": 85.5,
                "available": true,
                "in_user_pool": true,
                "win_rate": 51.2,
                "roles": ["TOP"]
            },
            ...
        ],
        "model_type": "neural_network" | "rule_based"
    }
    """
    # Extract draft state from request
    phase = data.get('phase', 'BAN')
    turn = data.get('turn', 0)
    side = data.get('side', 'BLUE')
    role = data.get('role', 'MID')
    elo = data.get('elo', 'PLATINUM')
    patch = data.get('patch', '14.24')
    bans_blue = data.get('bans_blue', [])
    bans_red = data.get('bans_red', [])
    picks_blue = data.get('picks_blue', [])
    picks_red = data.get('picks_red', [])

    # Get current slot info from frontend (it knows the actual role assignments)
    current_slot_role = data.get('current_slot_role')
    current_slot_side = data.get('current_slot_side')
    current_slot_position = data.get('current_slot_position', -1)

    # Determine the TARGET ROLE for recommendations
    # - Ban phase: Use user's role (to ban counters to their lane)
    # - Pick phase: Use the current SLOT's role from frontend (user can change role order)
    if phase == 'BAN':
        target_role = role  # User's selected role for banning counters
    else:
        # Use frontend-provided slot role (respects user's custom role assignments)
        target_role = current_slot_role if current_slot_role else role

    logger.info(f"Phase={phase}, Turn={turn}, User role={role}, Slot role={current_slot_role}, Target role={target_role}")

    # Build draft state with correct target role
    draft_state = {
        'phase': phase,
        'current_turn': turn,
        'side': side,
        'role': target_role,  # Use TARGET role, not user role
        'user_role': role,    # Keep user's actual role for reference
        'bans_blue': bans_blue,
        'bans_red': bans_red,
        'picks_blue': picks_blue,
        'picks_red': picks_red
    }

    # Load role-specific stats from scraped data
    scraped_role_stats = load_scraped_role_stats(elo, patch)

    # Get user's champion pool if authenticated
    user_champion_pool = {}
    if current_user:
        user_pool = db.query(models.UserChampionPool).filter(
            models.UserChampionPool.user_id == current_user.id
        ).all()
        user_champion_pool = {
            pool.champion_name: pool.proficiency
            for pool in user_pool
        }

    # Get all champions with stats from database
    # First try exact patch match, then try major.minor, then get any champions
    stats_service = ChampionStatsService(db)
    all_champions_data = stats_service.get_all_champions_for_patch(patch)

    # If no exact match, try major.minor (e.g., "16.1" from "16.1.1")
    if not all_champions_data and '.' in patch:
        major_minor = '.'.join(patch.split('.')[:2])
        all_champions_data = stats_service.get_all_champions_for_patch(major_minor)

    # If still no data, get all champions from database (any patch)
    if not all_champions_data:
        all_champions_data = db.query(models.Champion).filter(
            models.Champion.name.isnot(None)
        ).all()

    # If still no champions in DB, raise error
    if not all_champions_data:
        logger.error("No champion data found in database")
        raise HTTPException(status_code=500, detail="No champion data in database. Run champion sync first.")

    # De-duplicate champions by normalized name (handle case/whitespace differences)
    # This prevents "Dr. Mundo" and "DrMundo" from appearing as separate entries
    seen_names = set()
    unique_champions = []
    for champ in all_champions_data:
        if champ.name:
            # Normalize name for comparison (lowercase, strip whitespace)
            normalized_name = champ.name.strip().lower()
            if normalized_name not in seen_names:
                seen_names.add(normalized_name)
                unique_champions.append(champ)
    all_champions_data = unique_champions

    logger.debug(f"De-duplicated to {len(all_champions_data)} unique champions")

    # Determine unavailable champions (banned + picked)
    unavailable = set(bans_blue + bans_red)
    for pick in picks_blue + picks_red:
        if isinstance(pick, dict) and pick.get('champion'):
            unavailable.add(pick['champion'])
        elif isinstance(pick, str):
            unavailable.add(pick)

    # Convert to dict format for NN service, enriching with scraped role stats
    champions_for_nn = []
    for champ in all_champions_data:
        # Get scraped role stats for this champion
        scraped_data = scraped_role_stats.get(champ.name, {})
        role_stats = scraped_data.get("role_stats", {})
        total_games = scraped_data.get("total_games", 0)
        matchups = scraped_data.get("matchups", {})

        champions_for_nn.append({
            'id': champ.id,
            'name': champ.name,
            'key': getattr(champ, 'key', champ.name.lower()),
            'title': getattr(champ, 'title', ''),
            'roles': champ.roles or [],
            'tags': champ.roles or [],
            'attack': champ.attack or 5,
            'defense': champ.defense or 5,
            'magic': champ.magic or 5,
            'difficulty': champ.difficulty or 5,
            'win_rate': champ.win_rate or 50,
            'pick_rate': champ.pick_rate or 5,
            'ban_rate': champ.ban_rate or 5,
            'counters': getattr(champ, 'counters', {}) or {},
            'synergies': getattr(champ, 'synergies', {}) or {},
            # CRITICAL: Include role-specific stats from scraped data
            'role_stats': role_stats,
            'total_games': total_games,
            'matchups': matchups
        })

    # Get NN service for scoring
    nn_service = get_nn_service()

    # Determine if we're picking for the USER's role or someone else's
    is_picking_for_user_role = (target_role.upper() == role.upper())

    # Get matchup override from frontend (user can specify which enemy is their opponent)
    matchup_override = data.get('matchup_override')

    # Detect matchup for the current target role
    enemy_picks = picks_red if side == 'BLUE' else picks_blue
    matchup_info = detect_matchup_for_role(
        target_role,
        enemy_picks,
        scraped_role_stats,
        user_override=matchup_override
    )

    logger.info(f"Matchup detection: {matchup_info['matchup_type']} - {matchup_info['reasoning']}")

    # Score all champions using rank-specific model
    scored_champions = []
    for champion in champions_for_nn:
        is_available = champion['name'] not in unavailable
        is_in_user_pool = champion['name'] in user_champion_pool

        # CRITICAL: Only consider user proficiency when picking for USER's role
        # When picking for someone else (e.g., Top when user is Jungle), don't boost
        # user's pool champions - they're irrelevant for that role
        if is_picking_for_user_role:
            user_prof = user_champion_pool.get(champion['name'])
        else:
            user_prof = None  # Don't pass proficiency for non-user roles

        # Get recommendation score (pass elo for rank-specific model)
        if is_available:
            score = nn_service.predict_recommendation_score(
                champion, draft_state, user_prof, rank=elo
            )

            # BAN PHASE ADJUSTMENTS
            if phase == 'BAN':
                # Don't suggest banning user's own champions!
                if is_in_user_pool:
                    score *= 0.1  # Heavy penalty - user doesn't want to ban their own champs

                # Boost champions that are strong in user's lane (counters to user)
                # These are the ones user should consider banning
                role_stats = champion.get('role_stats', {})
                user_role_stats = role_stats.get(role, role_stats.get(role.capitalize(), {}))
                if user_role_stats.get('games', 0) > 50:
                    # Champion is played in user's role with decent sample size
                    user_role_wr = user_role_stats.get('win_rate', 50)
                    if user_role_wr > 52:  # Above average WR in user's lane = threat
                        score *= 1.2  # Boost as a ban target

            # PICK PHASE - Matchup-aware scoring
            elif phase == 'PICK' and matchup_info['matchup_champion']:
                # We have a detected matchup - boost counters
                matchup_champ = matchup_info['matchup_champion']
                champ_matchups = champion.get('matchups', {})

                # Matchups are nested by role: {role: {opponent: {games, wins}}}
                # Try target role first, then capitalize variant
                role_matchups = champ_matchups.get(target_role, {})
                if not role_matchups:
                    role_matchups = champ_matchups.get(target_role.capitalize(), {})

                # Check if this champion has good stats vs the matchup
                if matchup_champ in role_matchups:
                    matchup_data = role_matchups[matchup_champ]
                    games = matchup_data.get('games', 0)
                    wins = matchup_data.get('wins', 0)
                    if games >= 10:  # Lower threshold since matchup data can be sparse
                        matchup_wr = (wins / games) * 100
                        if matchup_wr > 52:
                            # Good counter - boost significantly
                            boost = 1 + (matchup_wr - 50) / 50  # e.g., 60% WR = 1.2x boost
                            score *= min(1.5, boost)  # Cap at 1.5x
                        elif matchup_wr < 48:
                            # Bad matchup - penalize
                            penalty = 1 - (50 - matchup_wr) / 50  # e.g., 40% WR = 0.8x
                            score *= max(0.5, penalty)  # Floor at 0.5x
        else:
            score = 0  # Unavailable champions get 0 score

        # Get role-specific stats for the target role
        role_stats = champion.get('role_stats', {})
        target_role_stats = role_stats.get(target_role, role_stats.get(target_role.capitalize(), {}))

        role_wr = target_role_stats.get('win_rate', champion['win_rate'])
        role_games = target_role_stats.get('games', 0)
        role_kda = target_role_stats.get('kda', 0)

        # CRITICAL: Heavily penalize champions with no games in target role
        # This prevents Vi being recommended for ADC when she has 0 ADC games
        if role_games == 0 and phase == 'PICK':
            score *= 0.05  # 95% penalty - almost never recommend
        elif role_games < 10 and phase == 'PICK':
            score *= 0.3   # 70% penalty for very low sample size

        scored_champions.append({
            'id': champion['id'],
            'name': champion['name'],
            'key': champion['key'],
            'score': round(score * 100, 2),
            'available': is_available,
            'in_user_pool': is_in_user_pool,
            'user_proficiency': user_champion_pool.get(champion['name']) if is_in_user_pool else None,
            'win_rate': (champion['win_rate'] / 100) if champion['win_rate'] > 1 else champion['win_rate'],
            'pick_rate': (champion['pick_rate'] / 100) if champion['pick_rate'] > 1 else champion['pick_rate'],
            'roles': champion['roles'],
            # Role-specific stats for transparency
            'role_win_rate': role_wr / 100 if role_wr > 1 else role_wr,
            'role_games': role_games,
            'role_kda': round(role_kda, 2) if role_kda else None,
            'target_role': target_role
        })

    # Sort by score (highest first), with available champions prioritized
    scored_champions.sort(key=lambda x: (x['available'], x['score']), reverse=True)

    return {
        'champions': scored_champions,
        'total': len(scored_champions),
        'available_count': sum(1 for c in scored_champions if c['available']),
        'model_type': 'neural_network' if nn_service.is_trained else 'rule_based',
        # Include context for UI transparency
        'phase': phase,
        'target_role': target_role,
        'user_role': role,
        'turn': turn,
        'is_user_role': is_picking_for_user_role,
        # Matchup info for transparency window
        'matchup': matchup_info
    }


@router.post("/analysis")
async def get_draft_analysis(
    data: Dict[str, Any],
    current_user: Optional[models.User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get LLM analysis for the current draft state.

    This endpoint powers the LLM analysis box in the frontend.
    Returns stage-appropriate analysis based on draft progress.

    Request body: Same as /sorted-champions

    Returns:
    {
        "analysis": "Strategic analysis text...",
        "stage": "EARLY_BAN" | "FIRST_PICK" | etc,
        "advantage": "Blue team ahead" | "Red team ahead" | "Even",
        "blue_power": 52.3,
        "red_power": 48.7,
        "recommendations": ["Recommendation 1", "Recommendation 2"],
        "source": "huggingface" | "rule-based"
    }
    """
    # Extract draft state
    phase = data.get('phase', 'BAN')
    turn = data.get('turn', 0)
    side = data.get('side', 'BLUE')
    role = data.get('role', 'MID')  # User's selected role
    elo = data.get('elo', 'PLATINUM')
    patch = data.get('patch', '14.24')
    bans_blue = data.get('bans_blue', [])
    bans_red = data.get('bans_red', [])
    picks_blue = data.get('picks_blue', [])
    picks_red = data.get('picks_red', [])

    # Get current slot info from frontend (it knows the actual role assignments)
    current_slot_role = data.get('current_slot_role')

    # Determine the TARGET ROLE for recommendations (same logic as sorted-champions)
    if phase == 'BAN':
        target_role = role  # User's selected role for banning counters
    else:
        target_role = current_slot_role if current_slot_role else role

    # Load role-specific stats from scraped data
    scraped_role_stats = load_scraped_role_stats(elo, patch)

    # Determine if we're picking for user's role
    is_picking_for_user_role = (target_role.upper() == role.upper())

    # Get user preferences if authenticated
    user_preferences = None
    user_pool_names = []
    if current_user:
        user_pool = db.query(models.UserChampionPool).filter(
            models.UserChampionPool.user_id == current_user.id
        ).all()
        user_pool_names = [p.champion_name for p in user_pool]

        user_prefs = current_user.preferences or {}

        user_preferences = {
            'champion_pool': [
                {
                    'champion': pool.champion_name,
                    'role': role,  # User's actual role
                    'playstyles': pool.playstyles or [],
                    'proficiency': pool.proficiency
                }
                for pool in user_pool
            ],
            'preferred_roles': user_prefs.get('roles', []),
            'rank': elo
        }

    # Get top NN recommendations for context
    nn_service = get_nn_service()

    # Get champions from DB for NN scoring
    stats_service = ChampionStatsService(db)
    all_champions_data = stats_service.get_all_champions_for_patch(patch)
    if not all_champions_data:
        major_minor = '.'.join(patch.split('.')[:2]) if '.' in patch else patch
        all_champions_data = stats_service.get_all_champions_for_patch(major_minor)
    if not all_champions_data:
        all_champions_data = db.query(models.Champion).filter(models.Champion.name.isnot(None)).all()

    # Get unavailable champions
    unavailable = set(bans_blue + bans_red)
    for pick in picks_blue + picks_red:
        if isinstance(pick, dict) and pick.get('champion'):
            unavailable.add(pick['champion'])
        elif isinstance(pick, str):
            unavailable.add(pick)

    # Get matchup detection for the target role
    enemy_picks = picks_red if side == 'BLUE' else picks_blue
    matchup_info = detect_matchup_for_role(
        target_role,
        enemy_picks,
        scraped_role_stats,
        user_override=data.get('matchup_override')
    )

    # Build champions list WITH role_stats from scraped data (critical for role-aware scoring)
    champions_for_nn = []
    for champ in all_champions_data:
        if champ.name in unavailable:
            continue

        # Get scraped role stats for this champion
        scraped_data = scraped_role_stats.get(champ.name, {})
        role_stats = scraped_data.get("role_stats", {})
        total_games = scraped_data.get("total_games", 0)
        matchups = scraped_data.get("matchups", {})

        champions_for_nn.append({
            'id': champ.id, 'name': champ.name, 'roles': champ.roles or [],
            'tags': champ.roles or [], 'win_rate': champ.win_rate or 50,
            'attack': champ.attack or 5, 'defense': champ.defense or 5,
            'magic': champ.magic or 5, 'difficulty': champ.difficulty or 5,
            'pick_rate': champ.pick_rate or 5, 'ban_rate': champ.ban_rate or 5,
            'counters': getattr(champ, 'counters', {}) or {},
            'synergies': getattr(champ, 'synergies', {}) or {},
            # CRITICAL: Include role-specific stats
            'role_stats': role_stats,
            'total_games': total_games,
            'matchups': matchups
        })

    # Sort by role-specific win rate for target role, then general win rate
    def get_role_priority(c):
        rs = c.get('role_stats', {})
        role_data = rs.get(target_role.capitalize(), rs.get(target_role, {}))
        role_wr = role_data.get('win_rate', 0)
        role_games = role_data.get('games', 0)
        # Prioritize champions with games in the target role
        if role_games > 50:
            return (1, role_wr, c.get('win_rate', 50))
        return (0, c.get('win_rate', 50), 0)

    champions_for_nn.sort(key=get_role_priority, reverse=True)

    # Build draft state with target role
    draft_state_for_nn = {
        'phase': phase, 'current_turn': turn, 'side': side,
        'role': target_role,  # Use TARGET role, not user role
        'user_role': role,
        'bans_blue': bans_blue, 'bans_red': bans_red,
        'picks_blue': picks_blue, 'picks_red': picks_red
    }

    # Score top 80 meta picks through NN for performance
    # Only pass user proficiency when picking for user's role
    top_nn_picks = []
    for champ in champions_for_nn[:80]:
        user_prof = None
        if is_picking_for_user_role and champ['name'] in user_pool_names:
            # Find proficiency
            for pool_item in (user_preferences or {}).get('champion_pool', []):
                if pool_item['champion'] == champ['name']:
                    user_prof = pool_item['proficiency']
                    break

        score = nn_service.predict_recommendation_score(champ, draft_state_for_nn, user_prof, elo)
        top_nn_picks.append((champ['name'], score))

    top_nn_picks.sort(key=lambda x: x[1], reverse=True)
    top_5_nn = [name for name, _ in top_nn_picks[:5]]

    # Build draft state for LLM with NN context
    draft_state = {
        'phase': phase,
        'turn': turn,
        'side': side,
        'role': target_role,  # Use target role for context
        'user_role': role,
        'bans': {
            'blue': bans_blue,
            'red': bans_red
        },
        'picks': {
            'blue': picks_blue,
            'red': picks_red
        },
        'nn_recommendations': top_5_nn,
        'user_pool': user_pool_names if is_picking_for_user_role else [],  # Only include when relevant
        'is_user_turn': data.get('is_user_turn', False),
        'matchup_info': matchup_info  # Include matchup context
    }

    # Get analysis from LLM service
    analysis_result = await llm_service.analyze_draft(draft_state, user_preferences)

    # Determine stage
    prompts_service = get_prompts_service()
    stage = prompts_service.get_stage(turn)

    # Calculate team power
    blue_power = _calculate_team_power(picks_blue, stats_service, patch)
    red_power = _calculate_team_power(picks_red, stats_service, patch)

    # Determine advantage
    diff = blue_power - red_power
    if abs(diff) < 2:
        advantage = "Even draft"
    elif diff > 0:
        advantage = f"Blue team ahead (+{diff:.1f}%)"
    else:
        advantage = f"Red team ahead (+{abs(diff):.1f}%)"

    # Build recommendations list - ONLY add user pool when picking for user's role
    recommendations = []
    if is_picking_for_user_role and user_pool_names:
        # First add 1-2 from user's pool if picking for their role
        pool_picks = [c for c in user_pool_names if c not in unavailable][:2]
        recommendations.extend(pool_picks)

    # Then add NN picks that aren't already in recommendations
    for nn_pick in top_5_nn:
        if nn_pick not in recommendations and nn_pick not in unavailable:
            recommendations.append(nn_pick)
        if len(recommendations) >= 5:
            break

    return {
        'analysis': analysis_result.get('analysis', 'Analyzing draft...'),
        'stage': stage,
        'turn': turn,
        'phase': phase,
        'advantage': advantage,
        'blue_power': round(blue_power, 1),
        'red_power': round(red_power, 1),
        'source': analysis_result.get('source', 'unknown'),
        'model': analysis_result.get('model', 'unknown'),
        'recommendations': recommendations,  # Role-aware champion suggestions
        # Include role and matchup context for frontend
        'target_role': target_role,
        'user_role': role,
        'is_user_role': is_picking_for_user_role,
        'matchup': matchup_info
    }


@router.post("/gameplan")
async def get_gameplan(
    data: Dict[str, Any],
    current_user: Optional[models.User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive gameplan when draft is complete.

    Called when draft phase is COMPLETE.
    Returns detailed strategic analysis for both teams.
    """
    picks_blue = data.get('picks_blue', [])
    picks_red = data.get('picks_red', [])
    side = data.get('side', 'BLUE')
    role = data.get('role', 'MID')
    elo = data.get('elo', 'PLATINUM')

    # Extract champion names
    blue_champs = [p.get('champion') if isinstance(p, dict) else p for p in picks_blue if p]
    red_champs = [p.get('champion') if isinstance(p, dict) else p for p in picks_red if p]

    # Build draft context
    context = DraftContext(
        phase='COMPLETE',
        turn=20,
        side=side,
        role=role,
        elo=elo,
        bans_blue=data.get('bans_blue', []),
        bans_red=data.get('bans_red', []),
        picks_blue=picks_blue,
        picks_red=picks_red
    )

    # Get prompts service
    prompts_service = get_prompts_service()
    gameplan_prompt = prompts_service.get_gameplan_prompt(context)

    # Get LLM analysis
    draft_state = {
        'phase': 'COMPLETE',
        'turn': 20,
        'bans': {'blue': data.get('bans_blue', []), 'red': data.get('bans_red', [])},
        'picks': {'blue': picks_blue, 'red': picks_red}
    }

    analysis_result = await llm_service.analyze_draft(draft_state)

    # Generate gameplans for both teams
    your_team = blue_champs if side == 'BLUE' else red_champs
    enemy_team = red_champs if side == 'BLUE' else blue_champs

    return {
        'your_team': {
            'champions': your_team,
            'gameplan': _generate_detailed_gameplan(your_team, 'your_team')
        },
        'enemy_team': {
            'champions': enemy_team,
            'gameplan': _generate_detailed_gameplan(enemy_team, 'enemy_team')
        },
        'analysis': analysis_result.get('analysis', ''),
        'win_conditions': _generate_win_conditions(your_team, enemy_team),
        'source': analysis_result.get('source', 'unknown')
    }


@router.post("/draft-stats")
async def get_draft_stats(
    data: Dict[str, Any],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive draft statistics when draft is complete.

    Returns lane matchup win rates, synergy scores, damage split, and team power.
    """
    picks_blue = data.get('picks_blue', [])
    picks_red = data.get('picks_red', [])
    side = data.get('side', 'BLUE')
    role = data.get('role', 'MID')
    elo = data.get('elo', 'PLATINUM')
    patch = data.get('patch', '14.24')

    # Load scraped data for calculations
    scraped_stats = load_scraped_role_stats(elo, patch)

    # Get stats service
    stats_service = ChampionStatsService(db)

    # Extract champion names and roles
    your_picks = picks_blue if side == 'BLUE' else picks_red
    enemy_picks = picks_red if side == 'BLUE' else picks_blue

    your_champs = []
    enemy_champs = []
    your_role_champ = None
    enemy_role_champ = None

    for pick in your_picks:
        if isinstance(pick, dict):
            champ = pick.get('champion')
            champ_role = pick.get('role', '')
            if champ:
                your_champs.append(champ)
                if champ_role.upper() == role.upper():
                    your_role_champ = champ
        elif pick:
            your_champs.append(pick)

    for pick in enemy_picks:
        if isinstance(pick, dict):
            champ = pick.get('champion')
            champ_role = pick.get('role', '')
            if champ:
                enemy_champs.append(champ)
                # Predict enemy role if not specified
                if not enemy_role_champ:
                    pred_role, conf = predict_enemy_role(champ, scraped_stats)
                    if pred_role.upper() == role.upper() and conf > 0.3:
                        enemy_role_champ = champ
        elif pick:
            enemy_champs.append(pick)
            pred_role, conf = predict_enemy_role(pick, scraped_stats)
            if pred_role.upper() == role.upper() and conf > 0.3:
                enemy_role_champ = pick

    # Calculate stats
    your_power = _calculate_team_power(your_picks, stats_service, patch)
    enemy_power = _calculate_team_power(enemy_picks, stats_service, patch)

    your_damage = _calculate_damage_split(your_picks, stats_service, patch)
    enemy_damage = _calculate_damage_split(enemy_picks, stats_service, patch)

    lane_matchup = _calculate_lane_matchup(
        your_role_champ, enemy_role_champ, role, scraped_stats
    )

    your_synergy = _calculate_synergy_score(your_picks, scraped_stats)
    enemy_synergy = _calculate_synergy_score(enemy_picks, scraped_stats)

    # Calculate overall composition advantage
    # Based on: team power (50%), synergy (30%), damage balance (20%)
    def calc_comp_score(power, synergy, damage):
        balance_penalty = abs(damage['ad'] - 50) / 100  # Penalty for imbalanced comps
        return (power * 0.5) + (synergy['score'] * 5 * 0.3) + ((1 - balance_penalty) * 50 * 0.2)

    your_comp_score = calc_comp_score(your_power, your_synergy, your_damage)
    enemy_comp_score = calc_comp_score(enemy_power, enemy_synergy, enemy_damage)

    # Normalize to percentages
    total = your_comp_score + enemy_comp_score
    your_win_pct = (your_comp_score / total * 100) if total > 0 else 50
    enemy_win_pct = (enemy_comp_score / total * 100) if total > 0 else 50

    return {
        "lane_matchup": {
            "your_champion": your_role_champ,
            "enemy_champion": enemy_role_champ,
            "win_rate": lane_matchup["win_rate"],
            "games": lane_matchup["games"],
            "confidence": lane_matchup["confidence"]
        },
        "comp_win": {
            "your_team": round(your_win_pct, 1),
            "enemy_team": round(enemy_win_pct, 1)
        },
        "synergy": {
            "your_team": your_synergy,
            "enemy_team": enemy_synergy
        },
        "damage_split": {
            "your_team": your_damage,
            "enemy_team": enemy_damage
        },
        "team_power": {
            "your_team": round(your_power, 1),
            "enemy_team": round(enemy_power, 1)
        }
    }


def _calculate_team_power(picks: List, stats_service: ChampionStatsService, patch: str) -> float:
    """Calculate team power from champion win rates."""
    if not picks:
        return 50.0

    total_power = 0
    count = 0

    for pick in picks:
        champ_name = pick.get('champion') if isinstance(pick, dict) else pick
        if champ_name:
            stats = stats_service.get_champion_stats(champ_name, patch)
            if stats and stats.win_rate:
                # win_rate stored as int (e.g., 5150 for 51.50%)
                wr = stats.win_rate / 100 if stats.win_rate > 100 else stats.win_rate
                total_power += wr
            else:
                total_power += 50
            count += 1

    return total_power / count if count > 0 else 50.0


def _calculate_damage_split(picks: List, stats_service: ChampionStatsService, patch: str) -> Dict[str, float]:
    """
    Calculate AP/AD damage split based on champion class/tags.

    Uses champion tags from Data Dragon to infer damage type:
    - Marksman, Fighter: Primarily AD
    - Mage: Primarily AP
    - Assassin: Mixed (some AD like Zed, some AP like Fizz)
    - Tank, Support: Lower damage weight

    Falls back to attack/magic ratios from Data Dragon if tags unavailable.
    """
    if not picks:
        return {"ad": 50.0, "ap": 50.0}

    # Known AP assassins/fighters (from game knowledge - these deal magic damage)
    AP_CHAMPIONS = {
        'Akali', 'Diana', 'Ekko', 'Evelynn', 'Fizz', 'Kassadin', 'Katarina',
        'Leblanc', 'Elise', 'Nidalee', 'Shaco', 'Teemo', 'Kennen', 'Rumble',
        'Mordekaiser', 'Singed', 'Vladimir', 'Sylas', 'Gwen', 'Kayle', 'Aurora',
        # Mages that might have Fighter/Assassin tags
        'Gragas', 'Galio', 'Cho\'Gath', 'Amumu', 'Zac', 'Maokai'
    }

    # Known hybrid champions (deal significant amounts of both)
    HYBRID_CHAMPIONS = {
        'Corki', 'Kai\'Sa', 'Kog\'Maw', 'Varus', 'Ezreal', 'Jax', 'Warwick',
        'Volibear', 'Dr. Mundo', 'Shyvana', 'Udyr', 'Skarner'
    }

    total_ad = 0.0
    total_ap = 0.0

    for pick in picks:
        champ_name = pick.get('champion') if isinstance(pick, dict) else pick
        if not champ_name:
            continue

        stats = stats_service.get_champion_stats(champ_name, patch)

        # Determine damage type based on champion
        if champ_name in AP_CHAMPIONS:
            # Known AP champion
            total_ad += 1
            total_ap += 9
        elif champ_name in HYBRID_CHAMPIONS:
            # Hybrid - splits damage
            total_ad += 5
            total_ap += 5
        elif stats:
            # Use tags/roles to infer damage type
            tags = stats.roles or []
            tags_upper = [t.upper() for t in tags] if tags else []

            # Check for Mage tag - primarily AP
            if 'MAGE' in tags_upper:
                total_ad += 2
                total_ap += 8
            # Marksman - primarily AD
            elif 'MARKSMAN' in tags_upper:
                total_ad += 9
                total_ap += 1
            # Fighter - usually AD
            elif 'FIGHTER' in tags_upper:
                total_ad += 7
                total_ap += 3
            # Assassin - check attack/magic ratio
            elif 'ASSASSIN' in tags_upper:
                attack = stats.attack or 5
                magic = stats.magic or 5
                if magic > attack:
                    total_ad += 2
                    total_ap += 8
                else:
                    total_ad += 8
                    total_ap += 2
            # Tank - lower damage, usually physical
            elif 'TANK' in tags_upper:
                total_ad += 4
                total_ap += 2
            # Support - often AP utility
            elif 'SUPPORT' in tags_upper:
                attack = stats.attack or 5
                magic = stats.magic or 5
                total_ad += min(attack, 3)
                total_ap += min(magic, 3)
            else:
                # Fallback: use attack/magic ratio from Data Dragon
                attack = stats.attack or 5
                magic = stats.magic or 5
                total_ad += attack
                total_ap += magic
        else:
            # No stats available - assume balanced
            total_ad += 5
            total_ap += 5

    total = total_ad + total_ap
    if total == 0:
        return {"ad": 50.0, "ap": 50.0}

    return {
        "ad": round((total_ad / total) * 100, 1),
        "ap": round((total_ap / total) * 100, 1)
    }


def _calculate_lane_matchup(
    your_champ: str,
    enemy_champ: str,
    role: str,
    scraped_stats: Dict[str, Dict]
) -> Dict[str, Any]:
    """Calculate lane matchup win rate from scraped data."""
    if not your_champ or not enemy_champ:
        return {"win_rate": 50.0, "games": 0, "confidence": "low"}

    your_data = scraped_stats.get(your_champ, {})
    matchups = your_data.get("matchups", {})

    # Look for matchup data
    matchup_data = matchups.get(enemy_champ, {})
    games = matchup_data.get("games", 0)
    wins = matchup_data.get("wins", 0)

    if games > 0:
        wr = (wins / games) * 100
        confidence = "high" if games >= 100 else "medium" if games >= 30 else "low"
        return {"win_rate": round(wr, 1), "games": games, "confidence": confidence}

    return {"win_rate": 50.0, "games": 0, "confidence": "low"}


def _calculate_synergy_score(picks: List, scraped_stats: Dict[str, Dict]) -> Dict[str, Any]:
    """Calculate team synergy score based on champion pairings."""
    if len(picks) < 2:
        return {"score": 5.0, "max_score": 10, "details": []}

    total_synergy = 0
    pairs_count = 0
    details = []

    champions = []
    for pick in picks:
        champ_name = pick.get('champion') if isinstance(pick, dict) else pick
        if champ_name:
            champions.append(champ_name)

    # Calculate pairwise synergies
    for i, champ1 in enumerate(champions):
        for j, champ2 in enumerate(champions):
            if i >= j:
                continue

            champ1_data = scraped_stats.get(champ1, {})
            synergies = champ1_data.get("synergies", {})
            synergy_data = synergies.get(champ2, {})

            games = synergy_data.get("games", 0)
            wins = synergy_data.get("wins", 0)

            if games >= 10:
                wr = (wins / games) * 100
                # Convert win rate to synergy score (0-10)
                # 50% = 5, 55% = 7.5, 45% = 2.5
                synergy_score = 5 + ((wr - 50) / 10)
                synergy_score = max(0, min(10, synergy_score))
                total_synergy += synergy_score
                pairs_count += 1
                if wr > 52 or wr < 48:
                    details.append({
                        "pair": f"{champ1} + {champ2}",
                        "win_rate": round(wr, 1),
                        "games": games,
                        "synergy": "good" if wr > 52 else "poor"
                    })
            else:
                # No data - assume neutral
                total_synergy += 5
                pairs_count += 1

    avg_synergy = total_synergy / pairs_count if pairs_count > 0 else 5.0

    return {
        "score": round(avg_synergy, 1),
        "max_score": 10,
        "details": details[:3]  # Top 3 notable synergies
    }


def _generate_detailed_gameplan(champions: List[str], team_type: str) -> Dict[str, str]:
    """Generate detailed gameplan sections."""
    if not champions:
        return {
            'early_game': 'Complete your draft to get gameplan.',
            'mid_game': '',
            'late_game': '',
            'win_condition': ''
        }

    # These are template gameplans - would be enhanced with actual champion data
    champ_str = ', '.join(champions)

    return {
        'early_game': f"Focus on lane stability and jungle tracking. {champ_str} composition should look for early advantages.",
        'mid_game': f"Group for objectives and look for picks. Your composition excels at teamfighting around dragon/baron.",
        'late_game': f"Scale into teamfights. With {len(champions)} champions, focus on playing around your primary carry.",
        'win_condition': f"Win teamfights and control objectives. Don't let the game go too long if you have early-game champions."
    }


def _generate_win_conditions(your_team: List[str], enemy_team: List[str]) -> List[str]:
    """Generate win conditions based on team compositions."""
    conditions = []

    if your_team:
        conditions.append(f"Your team ({', '.join(your_team[:3])}) should focus on teamfighting")
        conditions.append("Control vision around major objectives")
        conditions.append("Look for flanks and engages in the mid-game")

    if enemy_team:
        conditions.append(f"Watch out for enemy ({', '.join(enemy_team[:3])}) power spikes")

    if not conditions:
        conditions.append("Complete your draft to see win conditions")

    return conditions
