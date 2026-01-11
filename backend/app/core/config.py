from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "TrynDraft"
    VERSION: str = "0.1.0"
    DEBUG: bool = False  # Default to False for production safety

    # Security - REQUIRED from environment
    SECRET_KEY: str  # No default - must be provided

    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database - REQUIRED from environment
    DATABASE_URL: str  # No default - must be provided

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # External API Keys
    RIOT_API_KEY: str = ""
    RIOT_API_REGION: str = "na1"
    HF_TOKEN: str = ""  # HuggingFace token for LLM

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 120  # seconds

    # Data caching
    CACHE_DURATION_HOURS: int = 6

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


# Instantiate settings and validate required fields
try:
    settings = Settings()
except Exception as e:
    raise RuntimeError(
        f"Failed to load settings. Ensure required environment variables are set: {e}\n"
        "Copy .env.example to .env and fill in the required values."
    )