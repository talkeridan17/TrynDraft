from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.api.v1.endpoints import champions  # Add this import

app = FastAPI(
    title=settings.APP_NAME,
    description="League of Legends Drafting Assistant API",
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(
    champions.router,
    prefix=settings.API_V1_PREFIX,
    tags=["champions"]
)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}...")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info(f"Shutting down {settings.APP_NAME}...")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs" if settings.DEBUG else None,
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}