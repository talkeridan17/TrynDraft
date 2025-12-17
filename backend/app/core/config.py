from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "TrynDraft"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Database
    DATABASE_URL: str = "postgresql://tryndraft:password@localhost:5432/tryndraft"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Riot API
    RIOT_API_KEY: str = ""
    RIOT_API_REGION: str = "na1"
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 120  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()