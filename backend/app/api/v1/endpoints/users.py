# backend/app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
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

@router.get("/me/champion-pool", response_model=List[schemas.UserChampionPool])
async def get_user_champion_pool(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's champion pool."""
    champion_pool = db.query(models.UserChampionPool).filter(
        models.UserChampionPool.user_id == current_user.id
    ).all()
    return champion_pool

@router.post("/me/champion-pool")
async def add_to_champion_pool(
    champion_data: schemas.UserChampionPoolCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add champion to user's pool."""
    # Check if champion already in pool
    existing = db.query(models.UserChampionPool).filter(
        models.UserChampionPool.user_id == current_user.id,
        models.UserChampionPool.champion_name == champion_data.champion_name
    ).first()
    
    if existing:
        # Update existing entry
        for field, value in champion_data.dict(exclude_unset=True).items():
            setattr(existing, field, value)
        existing.updated_at = datetime.utcnow()
    else:
        # Create new entry
        db_champion = models.UserChampionPool(
            user_id=current_user.id,
            **champion_data.dict()
        )
        db.add(db_champion)
    
    db.commit()
    return {"message": "Champion pool updated"}

@router.delete("/me/champion-pool/{champion_name}")
async def remove_from_champion_pool(
    champion_name: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove champion from user's pool."""
    champion = db.query(models.UserChampionPool).filter(
        models.UserChampionPool.user_id == current_user.id,
        models.UserChampionPool.champion_name == champion_name
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

@router.post("/me/preferences")
async def update_preferences(
    preferences: dict,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences."""
    current_user.preferences = {**current_user.preferences, **preferences}
    current_user.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Preferences updated"}