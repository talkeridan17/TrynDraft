from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.draft_logic import DraftLogic
from app.services.data_dragon import DataDragonService
from app.services.draft_nn_service import get_nn_service
from app.services.champion_stats_service import ChampionStatsService
from app.services.llm_service import LLMService

router = APIRouter()
data_dragon = DataDragonService()
llm_service = LLMService()

@router.post("/", response_model=schemas.DraftResponse)
async def create_draft(
    draft_data: schemas.DraftCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new draft."""
    # Validate draft state
    draft_dict = draft_data.dict()
    draft_dict = DraftLogic.validate_draft_state(draft_dict)
    
    db_draft = models.Draft(
        user_id=current_user.id,
        **draft_dict
    )
    db.add(db_draft)
    db.commit()
    db.refresh(db_draft)
    return db_draft

@router.get("/{draft_id}", response_model=schemas.DraftResponse)
async def get_draft(
    draft_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a draft by ID."""
    draft = db.query(models.Draft).filter(
        models.Draft.id == draft_id,
        models.Draft.user_id == current_user.id
    ).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    return draft

@router.put("/{draft_id}", response_model=schemas.DraftResponse)
async def update_draft(
    draft_id: str,
    draft_data: schemas.DraftUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a draft."""
    draft = db.query(models.Draft).filter(
        models.Draft.id == draft_id,
        models.Draft.user_id == current_user.id
    ).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    # Get current draft state
    draft_dict = {
        'bans_blue': draft.bans_blue or [],
        'bans_red': draft.bans_red or [],
        'picks_blue': draft.picks_blue or [],
        'picks_red': draft.picks_red or [],
        'phase': draft.phase,
        'current_turn': draft.current_turn
    }
    
    # Update with new data
    update_data = draft_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(draft, key, value)
    
    # Validate the updated state
    draft_dict = DraftLogic.validate_draft_state({
        'bans_blue': draft.bans_blue or [],
        'bans_red': draft.bans_red or [],
        'picks_blue': draft.picks_blue or [],
        'picks_red': draft.picks_red or [],
    })
    
    draft.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(draft)
    return draft

@router.post("/{draft_id}/ban")
async def add_ban(
    draft_id: str,
    data: Dict[str, Any] = Body(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a ban to draft."""
    draft = db.query(models.Draft).filter(
        models.Draft.id == draft_id,
        models.Draft.user_id == current_user.id
    ).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    champion = data.get('champion')
    side = data.get('side', 'BLUE')
    
    if not champion:
        raise HTTPException(status_code=400, detail="Champion required")
    
    try:
        # Create draft state dict
        draft_state = {
            'bans_blue': draft.bans_blue or [],
            'bans_red': draft.bans_red or [],
            'picks_blue': draft.picks_blue or [],
            'picks_red': draft.picks_red or [],
            'phase': draft.phase,
            'current_turn': draft.current_turn
        }
        
        # Add ban
        draft_state = DraftLogic.add_ban(champion, side, draft_state)
        
        # Update draft
        draft.bans_blue = draft_state['bans_blue']
        draft.bans_red = draft_state['bans_red']
        draft.phase = draft_state.get('phase', draft.phase)
        draft.current_turn = draft_state.get('current_turn', draft.current_turn)
        draft.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(draft)
        
        return {"message": f"Banned {champion} for {side} team", "draft": draft}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{draft_id}/pick")
async def add_pick(
    draft_id: str,
    data: Dict[str, Any] = Body(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a pick to draft."""
    draft = db.query(models.Draft).filter(
        models.Draft.id == draft_id,
        models.Draft.user_id == current_user.id
    ).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    champion = data.get('champion')
    role = data.get('role', 'FILL')
    side = data.get('side', 'BLUE')
    
    if not champion:
        raise HTTPException(status_code=400, detail="Champion required")
    
    try:
        # Create draft state dict
        draft_state = {
            'bans_blue': draft.bans_blue or [],
            'bans_red': draft.bans_red or [],
            'picks_blue': draft.picks_blue or [],
            'picks_red': draft.picks_red or [],
            'phase': draft.phase,
            'current_turn': draft.current_turn
        }
        
        # Add pick
        draft_state = DraftLogic.add_pick(champion, role, side, draft_state)
        
        # Update draft
        draft.picks_blue = draft_state['picks_blue']
        draft.picks_red = draft_state['picks_red']
        draft.phase = draft_state.get('phase', draft.phase)
        draft.current_turn = draft_state.get('current_turn', draft.current_turn)
        draft.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(draft)
        
        return {"message": f"Picked {champion} for {side} team", "draft": draft}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{draft_id}/available-champions")
async def get_available_champions(
    draft_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get available champions for a draft."""
    draft = db.query(models.Draft).filter(
        models.Draft.id == draft_id,
        models.Draft.user_id == current_user.id
    ).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    # Get all champions from Data Dragon
    try:
        champion_data = await data_dragon.get_champion_data(draft.patch or "14.5.1")
        all_champions = [champ['name'] for champ in champion_data.values()]
    except:
        # Fallback to static list
        all_champions = [
            "Aatrox", "Ahri", "Akali", "Alistar", "Amumu", "Anivia", "Annie", "Aphelios",
            "Ashe", "Aurelion Sol", "Azir", "Bard", "Blitzcrank", "Brand", "Braum",
            "Caitlyn", "Camille", "Cassiopeia", "Cho'Gath", "Corki", "Darius", "Diana",
            "Draven", "Dr. Mundo", "Ekko", "Elise", "Evelynn", "Ezreal", "Fiddlesticks",
            "Fiora", "Fizz", "Galio", "Gangplank", "Garen", "Gnar", "Gragas", "Graves",
            "Hecarim", "Heimerdinger", "Illaoi", "Irelia", "Ivern", "Janna", "Jarvan IV",
            "Jax", "Jayce", "Jhin", "Jinx", "Kai'Sa", "Kalista", "Karma", "Karthus",
            "Kassadin", "Katarina", "Kayle", "Kayn", "Kennen", "Kha'Zix", "Kindred",
            "Kled", "Kog'Maw", "LeBlanc", "Lee Sin", "Leona", "Lillia", "Lissandra",
            "Lucian", "Lulu", "Lux", "Malphite", "Malzahar", "Maokai", "Master Yi",
            "Miss Fortune", "Mordekaiser", "Morgana", "Nami", "Nasus", "Nautilus",
            "Neeko", "Nidalee", "Nocturne", "Nunu & Willump", "Olaf", "Orianna",
            "Ornn", "Pantheon", "Poppy", "Pyke", "Qiyana", "Quinn", "Rakan", "Rammus",
            "Rek'Sai", "Rell", "Renekton", "Rengar", "Riven", "Rumble", "Ryze",
            "Samira", "Sejuani", "Senna", "Seraphine", "Sett", "Shaco", "Shen",
            "Shyvana", "Singed", "Sion", "Sivir", "Skarner", "Sona", "Soraka",
            "Swain", "Sylas", "Syndra", "Tahm Kench", "Taliyah", "Talon", "Taric",
            "Teemo", "Thresh", "Tristana", "Trundle", "Tryndamere", "Twisted Fate",
            "Twitch", "Udyr", "Urgot", "Varus", "Vayne", "Veigar", "Vel'Koz",
            "Vex", "Vi", "Viego", "Viktor", "Vladimir", "Volibear", "Warwick",
            "Wukong", "Xayah", "Xerath", "Xin Zhao", "Yasuo", "Yone", "Yorick",
            "Yuumi", "Zac", "Zed", "Zeri", "Ziggs", "Zilean", "Zoe", "Zyra"
        ]
    
    # Get available champions
    draft_state = {
        'bans_blue': draft.bans_blue or [],
        'bans_red': draft.bans_red or [],
        'picks_blue': draft.picks_blue or [],
        'picks_red': draft.picks_red or [],
    }
    
    available = DraftLogic.get_available_champions(all_champions, draft_state)
    
    return {
        "available_champions": available,
        "total_champions": len(all_champions),
        "taken_champions": len(all_champions) - len(available)
    }

@router.delete("/{draft_id}")
async def delete_draft(
    draft_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a draft."""
    draft = db.query(models.Draft).filter(
        models.Draft.id == draft_id,
        models.Draft.user_id == current_user.id
    ).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    db.delete(draft)
    db.commit()
    
    return {"message": "Draft deleted"}

@router.get("/", response_model=List[schemas.DraftResponse])
async def get_user_drafts(
    skip: int = 0,
    limit: int = 20,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all drafts for current user."""
    drafts = db.query(models.Draft).filter(
        models.Draft.user_id == current_user.id
    ).order_by(models.Draft.created_at.desc()).offset(skip).limit(limit).all()

    return drafts


@router.post("/{draft_id}/recommendations")
async def get_champion_recommendations(
    draft_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered champion recommendations for current draft state.

    Uses neural network (if available) or rule-based system to recommend
    champions based on:
    - Banned champions (filtered out)
    - User champion pool and proficiency
    - Champion statistics (win rates, matchups, synergies)
    - Current draft state and team composition
    """
    # Get draft
    draft = db.query(models.Draft).filter(
        models.Draft.id == draft_id,
        models.Draft.user_id == current_user.id
    ).first()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Get user's champion pool
    user_pool = db.query(models.UserChampionPool).filter(
        models.UserChampionPool.user_id == current_user.id
    ).all()

    user_champion_pool = {
        pool.champion_name: pool.proficiency
        for pool in user_pool
    }

    # Get available champions (not banned/picked)
    draft_state = {
        'bans_blue': draft.bans_blue or [],
        'bans_red': draft.bans_red or [],
        'picks_blue': draft.picks_blue or [],
        'picks_red': draft.picks_red or [],
        'phase': draft.phase,
        'current_turn': draft.current_turn,
        'role': draft.role,
        'side': draft.side
    }

    # Get champion statistics from database
    stats_service = ChampionStatsService(db)
    patch = draft.patch or "14.5"
    all_champions_data = stats_service.get_all_champions_for_patch(patch)

    # Filter out banned/picked champions
    banned_names = set(draft.bans_blue or []) | set(draft.bans_red or [])
    picked_names = {
        pick.get('champion') for pick in (draft.picks_blue or [])
    } | {
        pick.get('champion') for pick in (draft.picks_red or [])
    }
    unavailable = banned_names | picked_names

    available_champions = [
        {
            'id': champ.id,
            'name': champ.name,
            'key': champ.key,
            'title': champ.title,
            'roles': champ.roles or [],
            'tags': champ.roles or [],  # Use roles as tags for now
            'attack': champ.attack or 5,
            'defense': champ.defense or 5,
            'magic': champ.magic or 5,
            'difficulty': champ.difficulty or 5,
            'win_rate': champ.win_rate or 50,
            'pick_rate': champ.pick_rate or 10,
            'ban_rate': champ.ban_rate or 5,
            'counters': champ.counters or {},
            'synergies': champ.synergies or {}
        }
        for champ in all_champions_data
        if champ.name not in unavailable
    ]

    if not available_champions:
        raise HTTPException(
            status_code=400,
            detail="No available champions for recommendation"
        )

    # Get neural network recommendations
    nn_service = get_nn_service()
    recommendations = nn_service.get_top_recommendations(
        available_champions=available_champions,
        draft_state=draft_state,
        user_champion_pool=user_champion_pool,
        top_k=10
    )

    # Format response
    result = []
    for champion, score in recommendations:
        user_prof = user_champion_pool.get(champion['name'])

        result.append({
            'champion': champion['name'],
            'champion_id': champion['id'],
            'score': round(score * 100, 2),  # Convert to percentage
            'reason': _generate_recommendation_reason(
                champion, draft_state, score, user_prof
            ),
            'win_rate': champion['win_rate'],
            'user_proficiency': user_prof,
            'roles': champion['roles']
        })

    return {
        'draft_id': draft_id,
        'recommendations': result,
        'model_type': 'neural_network' if nn_service.is_trained else 'rule_based'
    }


def _generate_recommendation_reason(
    champion: Dict,
    draft_state: Dict,
    score: float,
    user_proficiency: Optional[int]
) -> str:
    """Generate human-readable reason for recommendation."""
    reasons = []

    # User proficiency
    if user_proficiency and user_proficiency >= 4:
        reasons.append(f"You're proficient with {champion['name']}")

    # Win rate
    win_rate = champion.get('win_rate', 50)
    if win_rate >= 52:
        reasons.append(f"High win rate ({win_rate}%)")

    # Role fit
    target_role = draft_state.get('role', 'MID')
    if target_role in champion.get('roles', []):
        reasons.append(f"Strong {target_role} pick")

    # Meta strength
    if score >= 0.8:
        reasons.append("Excellent meta pick")
    elif score >= 0.6:
        reasons.append("Strong situational pick")

    if not reasons:
        reasons.append("Solid champion choice")

    return " • ".join(reasons)


@router.post("/{draft_id}/analyze")
async def get_continuous_draft_analysis(
    draft_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get continuous LLM-powered draft analysis and commentary.

    Provides real-time analysis throughout the entire draft, including:
    - Current draft state assessment
    - Which team is ahead and why
    - Strengths and weaknesses of each composition
    - Gameplan suggestions for both teams
    - Next pick recommendations with strategic reasoning

    This endpoint is called continuously throughout the draft, not just on user's turn.
    """
    # Get draft
    draft = db.query(models.Draft).filter(
        models.Draft.id == draft_id,
        models.Draft.user_id == current_user.id
    ).first()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Build comprehensive draft state
    draft_state = {
        'phase': draft.phase or 'BAN',
        'turn': draft.current_turn or 0,
        'side': draft.side or 'BLUE',
        'role': draft.role or 'MID',
        'bans': {
            'blue': draft.bans_blue or [],
            'red': draft.bans_red or []
        },
        'picks': {
            'blue': draft.picks_blue or [],
            'red': draft.picks_red or []
        }
    }

    # Get LLM analysis
    analysis_result = await llm_service.analyze_draft(draft_state)

    # Get champion statistics for deeper analysis
    stats_service = ChampionStatsService(db)
    patch = draft.patch or "14.5"

    # Calculate team power levels
    blue_power, red_power = _calculate_team_power(
        draft_state['picks']['blue'],
        draft_state['picks']['red'],
        stats_service,
        patch
    )

    # Determine who's ahead
    power_diff = blue_power - red_power
    if abs(power_diff) < 5:
        advantage = "Even draft - both teams have similar strength"
    elif power_diff > 0:
        advantage = f"Blue team is ahead (+{power_diff:.1f}% power advantage)"
    else:
        advantage = f"Red team is ahead (+{abs(power_diff):.1f}% power advantage)"

    # Generate gameplan based on compositions
    blue_gameplan = _generate_gameplan(draft_state['picks']['blue'], stats_service, patch)
    red_gameplan = _generate_gameplan(draft_state['picks']['red'], stats_service, patch)

    # Store analysis in database for history
    llm_interaction = models.LLMInteraction(
        draft_id=draft_id,
        turn=draft_state['turn'],
        prompt=f"Draft analysis at turn {draft_state['turn']}",
        response=analysis_result.get('analysis', ''),
        model_name=analysis_result.get('model', 'Mistral-7B'),
        tokens_used=0  # TODO: Track tokens if using paid API
    )
    db.add(llm_interaction)
    db.commit()

    return {
        'draft_id': draft_id,
        'turn': draft_state['turn'],
        'phase': draft_state['phase'],
        'analysis': analysis_result.get('analysis', ''),
        'advantage': advantage,
        'blue_power': round(blue_power, 1),
        'red_power': round(red_power, 1),
        'blue_gameplan': blue_gameplan,
        'red_gameplan': red_gameplan,
        'model_used': analysis_result.get('model', 'unknown'),
        'source': analysis_result.get('source', 'unknown')
    }


def _calculate_team_power(
    blue_picks: List[Dict],
    red_picks: List[Dict],
    stats_service: ChampionStatsService,
    patch: str
) -> tuple:
    """Calculate team power levels based on champion stats."""
    def calculate_power(picks):
        if not picks:
            return 50.0

        total_power = 0
        count = 0

        for pick in picks:
            champ_name = pick.get('champion') if isinstance(pick, dict) else pick
            if champ_name:
                champ_stats = stats_service.get_champion_stats(champ_name, patch)
                if champ_stats and champ_stats.win_rate:
                    total_power += champ_stats.win_rate
                    count += 1
                else:
                    total_power += 50  # Average win rate
                    count += 1

        return total_power / count if count > 0 else 50.0

    blue_power = calculate_power(blue_picks)
    red_power = calculate_power(red_picks)

    return blue_power, red_power


def _generate_gameplan(
    picks: List[Dict],
    stats_service: ChampionStatsService,
    patch: str
) -> str:
    """Generate gameplan based on team composition."""
    if not picks or len(picks) == 0:
        return "No picks yet - focus on strong meta champions in your role"

    # Extract champion names
    champions = []
    for pick in picks:
        if isinstance(pick, dict):
            champ_name = pick.get('champion')
            if champ_name:
                champions.append(champ_name)
        elif isinstance(pick, str) and pick:
            champions.append(pick)

    if not champions:
        return "Build a balanced team composition"

    # Simple gameplan logic based on champion characteristics
    # TODO: Enhance with actual champion data analysis
    gameplans = []

    if len(champions) < 3:
        gameplans.append(f"Early draft: {', '.join(champions)} picked")
        gameplans.append("Complete your composition with balanced picks")
    else:
        gameplans.append(f"Composition: {', '.join(champions)}")
        gameplans.append("Focus on team coordination and objective control")
        gameplans.append("Identify win conditions and play towards them")

    return " • ".join(gameplans)


@router.get("/{draft_id}/statistics")
async def get_draft_statistics(
    draft_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistical analysis of the current draft state.

    Returns comprehensive team composition metrics calculated from scraped data:

    WIN PROBABILITY:
    - Based on historical matchup data between team compositions
    - Synergy scores from champion pairings (scraped from high-elo games)
    - Individual champion win rates at specified elo

    COMPOSITION SCORE:
    - Overall team balance (tank/damage/support distribution)
    - Role coverage and flexibility
    - Teamfight vs split-push potential

    DAMAGE TYPE ANALYSIS:
    - AD/AP/True damage split
    - Helps identify if enemy can itemize against (full AD = armor stacking)
    - Mixed damage = harder to counter-build

    TEAM FIGHT POWER:
    - AoE damage capability
    - CC chain potential
    - Engage/disengage tools
    - Peel for carries

    POWER SPIKE TIMING:
    - Early game (levels 1-6, first items)
    - Mid game (levels 11-13, 2-3 items)
    - Late game (levels 16-18, full build)
    - Based on champion scaling curves from scraped match data

    ADDITIONAL METRICS (to be added):
    - Objective control (dragon/baron potential)
    - Wave clear score
    - Poke vs all-in composition
    - Mobility/kiting potential

    TODO: Currently returns placeholder calculations. Will integrate with:
    - ChampionStatsService for scraped win rates and matchup data
    - Synergy matrix from high-elo game analysis
    - Power spike curves from item/level breakpoints
    """
    # Get draft
    draft = db.query(models.Draft).filter(
        models.Draft.id == draft_id,
        models.Draft.user_id == current_user.id
    ).first()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Extract picks for both teams
    blue_picks = [p['champion'] for p in (draft.picks_blue or []) if p.get('champion')]
    red_picks = [p['champion'] for p in (draft.picks_red or []) if p.get('champion')]

    # Calculate basic statistics
    def analyze_team(picks: List[str]) -> Dict[str, Any]:
        """Analyze a team composition."""
        if not picks:
            return {
                'damage_split': {'ap': 0, 'ad': 0, 'mixed': 0},
                'cc_score': 0,
                'mobility_score': 0,
                'tankiness_score': 0,
                'early_game_power': 0,
                'late_game_power': 0
            }

        # Simple heuristic analysis (can be enhanced with actual champion data)
        # These are placeholder calculations
        total_champions = len(picks)

        return {
            'damage_split': {
                'ap': round(40 + (hash(','.join(picks)) % 20), 1),
                'ad': round(40 + (hash(','.join(reversed(picks))) % 20), 1),
                'mixed': round(20, 1)
            },
            'cc_score': round(min(100, total_champions * 15 + (hash('cc' + ''.join(picks)) % 25)), 1),
            'mobility_score': round(min(100, total_champions * 12 + (hash('mob' + ''.join(picks)) % 30)), 1),
            'tankiness_score': round(min(100, total_champions * 14 + (hash('tank' + ''.join(picks)) % 28)), 1),
            'early_game_power': round(min(100, 50 + (hash('early' + ''.join(picks)) % 50)), 1),
            'late_game_power': round(min(100, 50 + (hash('late' + ''.join(picks)) % 50)), 1)
        }

    blue_stats = analyze_team(blue_picks)
    red_stats = analyze_team(red_picks)

    # Calculate win probability (simple heuristic)
    if not blue_picks or not red_picks:
        win_probability = 50.0
    else:
        # Average all scores to estimate relative strength
        blue_score = sum([
            blue_stats['cc_score'],
            blue_stats['mobility_score'],
            blue_stats['tankiness_score'],
            (blue_stats['early_game_power'] + blue_stats['late_game_power']) / 2
        ]) / 4

        red_score = sum([
            red_stats['cc_score'],
            red_stats['mobility_score'],
            red_stats['tankiness_score'],
            (red_stats['early_game_power'] + red_stats['late_game_power']) / 2
        ]) / 4

        total = blue_score + red_score
        win_probability = round((blue_score / total * 100) if total > 0 else 50.0, 1)

    return {
        'blue_team': {
            'champions': blue_picks,
            'stats': blue_stats
        },
        'red_team': {
            'champions': red_picks,
            'stats': red_stats
        },
        'win_probability': {
            'blue': win_probability,
            'red': round(100 - win_probability, 1)
        },
        'draft_phase': draft.phase or 'BAN',
        'current_turn': draft.current_turn or 0
    }