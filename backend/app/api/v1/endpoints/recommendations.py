"""
Recommendations API for TrynDraft Frontend
Provides endpoints for champion sorting and LLM analysis box
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
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

    # Build draft state
    draft_state = {
        'phase': phase,
        'current_turn': turn,
        'side': side,
        'role': role,
        'bans_blue': bans_blue,
        'bans_red': bans_red,
        'picks_blue': picks_blue,
        'picks_red': picks_red
    }

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

    # De-duplicate champions by name (keep most recent/best data)
    seen_names = set()
    unique_champions = []
    for champ in all_champions_data:
        if champ.name and champ.name not in seen_names:
            seen_names.add(champ.name)
            unique_champions.append(champ)
    all_champions_data = unique_champions

    # Determine unavailable champions (banned + picked)
    unavailable = set(bans_blue + bans_red)
    for pick in picks_blue + picks_red:
        if isinstance(pick, dict) and pick.get('champion'):
            unavailable.add(pick['champion'])
        elif isinstance(pick, str):
            unavailable.add(pick)

    # Convert to dict format for NN service
    champions_for_nn = []
    for champ in all_champions_data:
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
            'synergies': getattr(champ, 'synergies', {}) or {}
        })

    # Get NN service for scoring
    nn_service = get_nn_service()

    # Score all champions using rank-specific model
    scored_champions = []
    for champion in champions_for_nn:
        is_available = champion['name'] not in unavailable
        user_prof = user_champion_pool.get(champion['name'])

        # Get recommendation score (pass elo for rank-specific model)
        if is_available:
            score = nn_service.predict_recommendation_score(
                champion, draft_state, user_prof, rank=elo
            )
        else:
            score = 0  # Unavailable champions get 0 score

        scored_champions.append({
            'id': champion['id'],
            'name': champion['name'],
            'key': champion['key'],
            'score': round(score * 100, 2),
            'available': is_available,
            'in_user_pool': champion['name'] in user_champion_pool,
            'user_proficiency': user_prof,
            'win_rate': (champion['win_rate'] / 100) if champion['win_rate'] > 1 else champion['win_rate'],
            'pick_rate': (champion['pick_rate'] / 100) if champion['pick_rate'] > 1 else champion['pick_rate'],
            'roles': champion['roles']
        })

    # Sort by score (highest first), with available champions prioritized
    scored_champions.sort(key=lambda x: (x['available'], x['score']), reverse=True)

    return {
        'champions': scored_champions,
        'total': len(scored_champions),
        'available_count': sum(1 for c in scored_champions if c['available']),
        'model_type': 'neural_network' if nn_service.is_trained else 'rule_based'
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
    role = data.get('role', 'MID')
    elo = data.get('elo', 'PLATINUM')
    bans_blue = data.get('bans_blue', [])
    bans_red = data.get('bans_red', [])
    picks_blue = data.get('picks_blue', [])
    picks_red = data.get('picks_red', [])

    # Get user preferences if authenticated
    user_preferences = None
    if current_user:
        user_pool = db.query(models.UserChampionPool).filter(
            models.UserChampionPool.user_id == current_user.id
        ).all()

        user_prefs = current_user.preferences or {}

        user_preferences = {
            'champion_pool': [
                {
                    'champion': pool.champion_name,
                    'role': role,  # Use current role
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
    patch = data.get('patch', '14.24')

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

    # Get user's champion pool if authenticated
    user_pool_names = []
    if current_user:
        user_pool = db.query(models.UserChampionPool).filter(
            models.UserChampionPool.user_id == current_user.id
        ).all()
        user_pool_names = [p.champion_name for p in user_pool]

    # Get top NN recommendations
    top_nn_picks = []
    champions_for_nn = [
        {
            'id': champ.id, 'name': champ.name, 'roles': champ.roles or [],
            'tags': champ.roles or [], 'win_rate': champ.win_rate or 50,
            'attack': champ.attack or 5, 'defense': champ.defense or 5,
            'magic': champ.magic or 5, 'difficulty': champ.difficulty or 5,
            'pick_rate': champ.pick_rate or 5, 'ban_rate': champ.ban_rate or 5,
            'counters': getattr(champ, 'counters', {}) or {},
            'synergies': getattr(champ, 'synergies', {}) or {}
        }
        for champ in all_champions_data if champ.name not in unavailable
    ]

    # Sort by win_rate and pick_rate to prioritize strong meta picks
    champions_for_nn.sort(key=lambda x: (x['win_rate'] or 50) + (x['pick_rate'] or 5) * 0.3, reverse=True)

    draft_state_for_nn = {
        'phase': phase, 'current_turn': turn, 'side': side, 'role': role,
        'bans_blue': bans_blue, 'bans_red': bans_red,
        'picks_blue': picks_blue, 'picks_red': picks_red
    }

    # Score top 80 meta picks through NN for performance
    for champ in champions_for_nn[:80]:
        score = nn_service.predict_recommendation_score(champ, draft_state_for_nn, None, elo)
        top_nn_picks.append((champ['name'], score))
    top_nn_picks.sort(key=lambda x: x[1], reverse=True)
    top_5_nn = [name for name, _ in top_nn_picks[:5]]

    # Build draft state for LLM with NN context
    draft_state = {
        'phase': phase,
        'turn': turn,
        'side': side,
        'role': role,
        'bans': {
            'blue': bans_blue,
            'red': bans_red
        },
        'picks': {
            'blue': picks_blue,
            'red': picks_red
        },
        'nn_recommendations': top_5_nn,
        'user_pool': user_pool_names,
        'is_user_turn': data.get('is_user_turn', False)  # For detailed vs brief response
    }

    # Get analysis from LLM service
    analysis_result = await llm_service.analyze_draft(draft_state, user_preferences)

    # Determine stage
    prompts_service = get_prompts_service()
    stage = prompts_service.get_stage(turn)

    # Calculate team power
    stats_service = ChampionStatsService(db)
    patch = data.get('patch', '14.24')

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

    # Build recommendations list - mix user pool and NN picks
    recommendations = []
    # First add 1-2 from user's pool if available and not banned/picked
    if user_pool_names:
        pool_picks = [c for c in user_pool_names if c not in unavailable][:2]
        recommendations.extend(pool_picks)
    # Then add NN picks that aren't already in recommendations
    for nn_pick in top_5_nn:
        if nn_pick not in recommendations and nn_pick not in unavailable:
            recommendations.append(nn_pick)
        if len(recommendations) >= 4:
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
        'recommendations': recommendations  # Champion suggestions
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
