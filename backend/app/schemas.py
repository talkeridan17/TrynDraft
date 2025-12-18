from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    summoner_name: Optional[str] = None
    region: Optional[str] = "NA"

class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

class UserResponse(UserBase):
    id: str
    is_active: bool
    is_premium: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None

# Champion schemas
class ChampionBase(BaseModel):
    name: str
    key: str
    title: Optional[str] = None
    roles: List[str] = []

class ChampionResponse(ChampionBase):
    id: str
    attack: Optional[int] = None
    defense: Optional[int] = None
    magic: Optional[int] = None
    difficulty: Optional[int] = None
    win_rate: Optional[int] = None
    pick_rate: Optional[int] = None
    ban_rate: Optional[int] = None
    
    class Config:
        from_attributes = True

# Draft schemas
class DraftBase(BaseModel):
    game_mode: str = "DRAFT"
    side: str = "BLUE"
    role: str = "TOP"
    elo: str = "PLATINUM"
    region: str = "NA"
    patch: str = "14.1"
    phase: str = "BAN"
    current_turn: int = 1
    bans_blue: List[str] = []
    bans_red: List[str] = []
    picks_blue: List[Dict[str, Any]] = []
    picks_red: List[Dict[str, Any]] = []

class DraftCreate(DraftBase):
    pass

class DraftResponse(DraftBase):
    id: str
    user_id: str
    analysis: Optional[str] = None
    win_prediction: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Recommendation schemas
class Recommendation(BaseModel):
    champion: str
    reason: str
    score: int
    recommendation_type: str