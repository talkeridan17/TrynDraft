# app/api/v1/endpoints/drafts.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.draft_service import DraftService

router = APIRouter()
draft_service = DraftService()

@router.post("/", response_model=schemas.DraftResponse)
async def create_draft(
    draft_data: schemas.DraftCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new draft."""
    db_draft = models.Draft(
        user_id=current_user.id,
        **draft_data.dict()
    )
    db.add(db_draft)
    db.commit()
    db.refresh(db_draft)
    return db_draft

@router.get("/{draft_id}", response_model=schemas.DraftResponse)
async def get_draft(
    draft_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a draft by ID."""
    draft = db.query(models.Draft).filter(
        models.Draft.id == draft_id,
        models.Draft.user_id == current_user.id
    ).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    return draft

@router.put("/{draft_id}", response_model=schemas.DraftResponse)
async def update_draft(
    draft_id: str,
    draft_data: schemas.DraftCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a draft."""
    draft = db.query(models.Draft).filter(
        models.Draft.id == draft_id,
        models.Draft.user_id == current_user.id
    ).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    for key, value in draft_data.dict().items():
        setattr(draft, key, value)
    
    db.commit()
    db.refresh(draft)
    return draft

@router.delete("/{draft_id}")
async def delete_draft(
    draft_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a draft."""
    draft = db.query(models.Draft).filter(
        models.Draft.id == draft_id,
        models.Draft.user_id == current_user.id
    ).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    db.delete(draft)
    db.commit()
    
    return {"message": "Draft deleted"}

@router.get("/", response_model=List[schemas.DraftResponse])
async def get_user_drafts(
    skip: int = 0,
    limit: int = 20,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all drafts for current user."""
    drafts = db.query(models.Draft).filter(
        models.Draft.user_id == current_user.id
    ).order_by(models.Draft.created_at.desc()).offset(skip).limit(limit).all()
    
    return drafts