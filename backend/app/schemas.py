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

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    summoner_name: Optional[str] = None
    region: Optional[str] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    id: str
    is_active: bool
    is_premium: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Champion pool schemas
class UserChampionPoolBase(BaseModel):
    champion_name: str
    role: Optional[str] = None
    proficiency: Optional[int] = 1
    is_favorite: Optional[bool] = False
    games_played: Optional[int] = 0
    win_rate: Optional[int] = None

class UserChampionPoolCreate(UserChampionPoolBase):
    pass

class UserChampionPoolResponse(UserChampionPoolBase):
    id: str
    user_id: str
    created_at: datetime
    
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

# Draft schemas - FIXED to match your frontend store
class DraftBase(BaseModel):
    game_mode: str = "DRAFT"
    side: str = "BLUE"
    role: str = "TOP"
    elo: str = "PLATINUM"
    region: str = "NA"
    patch: str = "14.4.1"
    phase: str = "BAN"
    current_turn: int = 0
    
    # Draft state
    bans_blue: List[str] = []
    bans_red: List[str] = []
    picks_blue: List[Dict[str, Any]] = []
    picks_red: List[Dict[str, Any]] = []

class DraftCreate(DraftBase):
    pass

class DraftUpdate(BaseModel):
    phase: Optional[str] = None
    current_turn: Optional[int] = None
    bans_blue: Optional[List[str]] = None
    bans_red: Optional[List[str]] = None
    picks_blue: Optional[List[Dict[str, Any]]] = None
    picks_red: Optional[List[Dict[str, Any]]] = None

class DraftResponse(DraftBase):
    id: str
    user_id: str
    analysis: Optional[str] = None
    win_prediction: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# LLM schemas
class LLMAnalysisRequest(BaseModel):
    draft_state: Dict[str, Any]
    available_champions: List[str]
    top_recommendation: str

class LLMAnalysisResponse(BaseModel):
    analysis: str
    top_recommendation: str
    available_count: int

# Recommendation schemas
class Recommendation(BaseModel):
    champion: str
    reason: str
    score: int
    recommendation_type: str