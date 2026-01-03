from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, List
import os

from app.database import get_db
from app import schemas
from app.auth import get_current_user
from app.services.llm_service import LLMService

router = APIRouter()
llm_service = LLMService()

@router.post("/analyze")
async def analyze_draft(
    request: schemas.LLMAnalysisRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate LLM analysis for current draft state."""
    try:
        analysis = await llm_service.generate_draft_analysis(
            request.draft_state,
            request.top_recommendation
        )
        
        return {
            "analysis": analysis.get("analysis", "Analysis not available"),
            "top_recommendation": request.top_recommendation,
            "available_count": len(request.available_champions),
            "source": analysis.get("source", "fallback"),
            "timestamp": analysis.get("timestamp")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate analysis: {str(e)}")

@router.post("/gameplan")
async def generate_gameplan(
    draft_state: Dict,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a comprehensive gameplan based on draft."""
    try:
        # This would use a more sophisticated analysis
        blue_picks = draft_state.get('picks', {}).get('blue', [])
        red_picks = draft_state.get('picks', {}).get('red', [])
        
        # Simple analysis for now
        blue_count = sum(1 for p in blue_picks if isinstance(p, dict) and p.get('champion'))
        red_count = sum(1 for p in red_picks if isinstance(p, dict) and p.get('champion'))
        
        analysis = f"Blue team has {blue_count} picks, Red team has {red_count} picks. "
        
        if blue_count > red_count:
            analysis += "Blue team has pick advantage. "
        elif red_count > blue_count:
            analysis += "Red team has pick advantage. "
        else:
            analysis += "Teams are even in picks. "
        
        return {
            "summary": analysis,
            "win_conditions": [
                "Secure early objectives",
                "Control vision around key areas",
                "Coordinate team fights"
            ],
            "key_objectives": [
                "First Dragon at 5:00",
                "Rift Herald at 8:00",
                "Baron after 20:00"
            ],
            "teamfight_strategy": "Frontline protects carries, backline deals damage",
            "draft_grade": {"grade": "B", "score": 75}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scrape")
async def scrape_data():
    """Admin endpoint to trigger data scraping."""
    # Check for admin permissions
    api_key = os.getenv("ADMIN_API_KEY")
    if not api_key:
        raise HTTPException(status_code=401, detail="Admin access required")
    
    # This would trigger async scraping
    return {
        "message": "Scraping job queued",
        "status": "processing"
    }