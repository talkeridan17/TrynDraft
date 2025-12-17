from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

router = APIRouter()

# Mock data for now - we'll replace with real data later
MOCK_CHAMPIONS = [
    {"id": 1, "name": "Aatrox", "role": "Top", "difficulty": "Medium"},
    {"id": 2, "name": "Ahri", "role": "Mid", "difficulty": "Medium"},
    {"id": 3, "name": "Akali", "role": "Mid", "difficulty": "High"},
    {"id": 4, "name": "Alistar", "role": "Support", "difficulty": "Low"},
    {"id": 5, "name": "Amumu", "role": "Jungle", "difficulty": "Low"},
]

@router.get("/champions", response_model=List[Dict[str, Any]])
async def get_champions():
    """Get list of all champions."""
    return MOCK_CHAMPIONS

@router.get("/champions/{champion_name}")
async def get_champion(champion_name: str):
    """Get specific champion by name."""
    champion = next(
        (c for c in MOCK_CHAMPIONS if c["name"].lower() == champion_name.lower()),
        None
    )
    if not champion:
        raise HTTPException(status_code=404, detail="Champion not found")
    return champion

@router.get("/recommend/{enemy_champion}")
async def recommend_counter(enemy_champion: str):
    """Get champion recommendations against an enemy champion."""
    # Mock logic - we'll implement real logic later
    recommendations = [
        {"champion": "Darius", "reason": "Strong lane bully", "win_rate": "54.2%"},
        {"champion": "Garen", "reason": "Easy to play, durable", "win_rate": "52.8%"},
        {"champion": "Sett", "reason": "Good trades, strong all-in", "win_rate": "51.5%"},
    ]
    return {
        "enemy": enemy_champion,
        "recommendations": recommendations,
        "note": "Mock data - real recommendations coming soon!"
    }