from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.draft_logic import DraftLogic
from app.services.data_dragon import DataDragonService

router = APIRouter()
data_dragon = DataDragonService()

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