# backend/app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timedelta
from typing import List

from app.database import get_db
from app import models, schemas
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter()

@router.post("/register", response_model=schemas.UserResponse)
async def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user exists
    db_user = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.username == user.username)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email or username already registered")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        summoner_name=user.summoner_name,
        region=user.region,
        preferences={
            "favorite_champions": [],
            "preferred_roles": ["FILL"],
            "notifications": True
        }
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login user and return access token."""
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}

@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    """Get current user information."""
    return current_user

@router.put("/me", response_model=schemas.UserResponse)
async def update_current_user(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user information."""
    # Check if email is being changed and if it's already taken
    if user_update.email and user_update.email != current_user.email:
        existing_user = db.query(models.User).filter(models.User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if summoner_name is being changed
    if user_update.summoner_name:
        existing_user = db.query(models.User).filter(
            models.User.summoner_name == user_update.summoner_name,
            models.User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Summoner name already taken")
    
    # Update fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "password":
            value = get_password_hash(value)
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/me/champion-pool", response_model=List[schemas.UserChampionPoolResponse])
async def get_user_champion_pool(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's champion pool."""
    champion_pool = db.query(models.UserChampionPool).filter(
        models.UserChampionPool.user_id == current_user.id
    ).all()
    return champion_pool

@router.post("/me/champion-pool", response_model=schemas.UserChampionPoolResponse)
async def add_to_champion_pool(
    champion_data: schemas.UserChampionPoolCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add champion to user's pool."""
    # Check if champion already in pool (unique constraint per user)
    existing = db.query(models.UserChampionPool).filter(
        models.UserChampionPool.user_id == current_user.id,
        models.UserChampionPool.champion_name == champion_data.champion_name
    ).first()

    if existing:
        # Update playstyles for existing entry
        existing.playstyles = champion_data.playstyles
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new entry
        db_champion = models.UserChampionPool(
            user_id=current_user.id,
            champion_name=champion_data.champion_name,
            playstyles=champion_data.playstyles or []
        )
        db.add(db_champion)
        db.commit()
        db.refresh(db_champion)
        return db_champion

@router.put("/me/champion-pool/{champion_id}", response_model=schemas.UserChampionPoolResponse)
async def update_champion_pool_entry(
    champion_id: str,
    update_data: schemas.UserChampionPoolUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update playstyles and proficiency for a champion in user's pool."""
    champion = db.query(models.UserChampionPool).filter(
        models.UserChampionPool.id == champion_id,
        models.UserChampionPool.user_id == current_user.id
    ).first()

    if not champion:
        raise HTTPException(status_code=404, detail="Champion not found in pool")

    if update_data.playstyles is not None:
        champion.playstyles = update_data.playstyles

    if update_data.proficiency is not None:
        # Validate proficiency is between 0-5
        if 0 <= update_data.proficiency <= 5:
            champion.proficiency = update_data.proficiency
        else:
            raise HTTPException(status_code=400, detail="Proficiency must be between 0 and 5")

    db.commit()
    db.refresh(champion)
    return champion

@router.delete("/me/champion-pool/{champion_id}")
async def remove_from_champion_pool(
    champion_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove champion from user's pool by ID."""
    champion = db.query(models.UserChampionPool).filter(
        models.UserChampionPool.id == champion_id,
        models.UserChampionPool.user_id == current_user.id
    ).first()

    if not champion:
        raise HTTPException(status_code=404, detail="Champion not found in pool")

    db.delete(champion)
    db.commit()
    return {"message": "Champion removed from pool"}

@router.get("/me/drafts", response_model=List[schemas.DraftResponse])
async def get_user_drafts(
    skip: int = 0,
    limit: int = 20,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's drafts."""
    drafts = db.query(models.Draft).filter(
        models.Draft.user_id == current_user.id
    ).order_by(models.Draft.created_at.desc()).offset(skip).limit(limit).all()
    return drafts

@router.put("/me/preferences")
async def update_preferences(
    preferences: schemas.UserPreferencesUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences (preferred roles, rank, and profile picture)."""
    current_prefs = current_user.preferences or {}

    # Update only provided fields
    if preferences.preferred_roles is not None:
        current_prefs["preferred_roles"] = preferences.preferred_roles
    if preferences.rank is not None:
        current_prefs["rank"] = preferences.rank
    if preferences.profile_picture is not None:
        current_prefs["profile_picture"] = preferences.profile_picture

    current_user.preferences = current_prefs
    # CRITICAL: Flag the JSON column as modified so SQLAlchemy detects the change
    flag_modified(current_user, "preferences")
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return {"message": "Preferences updated", "preferences": current_user.preferences}

@router.get("/me/preferences")
async def get_preferences(
    current_user: models.User = Depends(get_current_user)
):
    """Get user preferences."""
    return current_user.preferences or {}