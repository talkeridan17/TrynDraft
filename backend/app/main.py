# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import uvicorn
from typing import List

from .database import get_db, engine
from . import models, schemas
from .auth import get_password_hash, verify_password, create_access_token, get_current_user
from .api.v1.endpoints import champions

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="TrynDraft API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(champions.router, prefix="/api/v1/champions", tags=["champions"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Health check
@app.get("/")
async def root():
    return {"message": "TrynDraft API is running"}

# Auth endpoints
@app.post("/auth/register", response_model=schemas.UserResponse)
async def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
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
        region=user.region
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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
    return {"access_token": access_token, "token_type": "bearer"}

# User endpoints
@app.get("/auth/me", response_model=schemas.UserResponse)
async def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    return current_user

# Draft endpoints (simplified for now)
@app.post("/api/v1/drafts")
async def create_draft(
    draft: schemas.DraftCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_draft = models.Draft(
        user_id=current_user.id,
        game_mode=draft.game_mode,
        side=draft.side,
        role=draft.role,
        elo=draft.elo,
        region=draft.region,
        patch=draft.patch,
        phase=draft.phase,
        current_turn=draft.current_turn,
        bans_blue=draft.bans_blue,
        bans_red=draft.bans_red,
        picks_blue=draft.picks_blue,
        picks_red=draft.picks_red
    )
    db.add(db_draft)
    db.commit()
    db.refresh(db_draft)
    return db_draft

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)