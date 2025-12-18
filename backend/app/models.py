from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    summoner_name = Column(String)
    region = Column(String, default="NA")
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    preferences = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    drafts = relationship("Draft", back_populates="user")
    champion_pool = relationship("UserChampionPool", back_populates="user")

class Draft(Base):
    __tablename__ = "drafts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    game_mode = Column(String, default="DRAFT")
    side = Column(String, default="BLUE")
    role = Column(String, default="TOP")
    elo = Column(String, default="PLATINUM")
    region = Column(String, default="NA")
    patch = Column(String, default="14.1")
    
    # Draft state
    phase = Column(String, default="BAN")  # BAN or PICK
    current_turn = Column(Integer, default=1)
    bans_blue = Column(JSON, default=[])
    bans_red = Column(JSON, default=[])
    picks_blue = Column(JSON, default=[])
    picks_red = Column(JSON, default=[])
    
    # Analysis
    analysis = Column(Text)
    win_prediction = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="drafts")

class UserChampionPool(Base):
    __tablename__ = "user_champion_pool"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    champion_name = Column(String, nullable=False)
    role = Column(String)
    proficiency = Column(Integer, default=1)  # 1-5 scale
    is_favorite = Column(Boolean, default=False)
    games_played = Column(Integer, default=0)
    win_rate = Column(Integer)  # Percentage
    
    user = relationship("User", back_populates="champion_pool")

class Champion(Base):
    __tablename__ = "champions"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    key = Column(String, nullable=False)
    title = Column(String)
    roles = Column(JSON, default=[])
    
    # Stats
    attack = Column(Integer)
    defense = Column(Integer)
    magic = Column(Integer)
    difficulty = Column(Integer)
    
    # Patch specific data
    patch = Column(String)
    win_rate = Column(Integer)
    pick_rate = Column(Integer)
    ban_rate = Column(Integer)
    
    # Synergy and counter data
    synergies = Column(JSON, default={})
    counters = Column(JSON, default={})
    
    updated_at = Column(DateTime, default=datetime.utcnow)

class DraftRecommendation(Base):
    __tablename__ = "draft_recommendations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    draft_id = Column(String, ForeignKey("drafts.id"))
    champion_name = Column(String, nullable=False)
    role = Column(String)
    reason = Column(Text)
    score = Column(Integer)
    recommendation_type = Column(String)  # PICK, BAN, COUNTER, SYNERGY
    
    created_at = Column(DateTime, default=datetime.utcnow)

class ScrapedContent(Base):
    __tablename__ = "scraped_content"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    source = Column(String, nullable=False)  # 'mobafire', 'lolalytics', 'reddit'
    url = Column(String)
    title = Column(String)
    content = Column(Text, nullable=False)
    champion = Column(String)  # Which champion this is about
    role = Column(String)      # TOP, JUNGLE, etc.
    tags = Column(JSON, default=[])  # ['guide', 'matchup', 'build']
    patch_version = Column(String)
    quality_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # For full-text search
    __table_args__ = (Index('ix_scraped_content_search', 'content', postgresql_using='gin'),)

class LLMInteraction(Base):
    __tablename__ = "llm_interactions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    draft_id = Column(String, ForeignKey("drafts.id"))
    turn_number = Column(Integer)
    phase = Column(String)  # 'BAN' or 'PICK'
    champion_in_question = Column(String)
    prompt = Column(Text)
    response = Column(Text)
    model_used = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    draft = relationship("Draft", back_populates="llm_interactions")