from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import uvicorn

from .database import get_db, engine, Base
from . import models, schemas
from .auth import get_password_hash, verify_password, create_access_token, get_current_user
from .api.v1.endpoints import champions, drafts, llm, metadata, users

# Create tables
Base.metadata.create_all(bind=engine)

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
app.include_router(drafts.router, prefix="/api/v1/drafts", tags=["drafts"])
app.include_router(llm.router, prefix="/api/v1/llm", tags=["llm"])
app.include_router(metadata.router, prefix="/api/v1/metadata", tags=["metadata"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

# Root endpoints
@app.get("/")
async def root():
    return {"message": "TrynDraft API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)