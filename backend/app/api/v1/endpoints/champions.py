# app/api/v1/endpoints/champions.py
from fastapi import APIRouter, HTTPException
from typing import List
import requests

router = APIRouter()

# Cache champion data
CHAMPION_CACHE = None

@router.get("/")
async def get_champions():
    """Get all champions from Data Dragon."""
    global CHAMPION_CACHE
    
    if CHAMPION_CACHE is not None:
        return CHAMPION_CACHE
    
    try:
        version = "14.4.1"  # Updated to current patch
        url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        champions = []
        
        for key, champ_data in data["data"].items():
            champions.append({
                "id": champ_data["id"],
                "key": champ_data["key"],
                "name": champ_data["name"],
                "title": champ_data["title"],
                "roles": champ_data["tags"],
                "image": {
                    "full": champ_data["image"]["full"],
                    "sprite": champ_data["image"]["sprite"],
                    "group": champ_data["image"]["group"]
                }
            })
        
        CHAMPION_CACHE = champions
        return champions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch champions: {str(e)}")

@router.get("/{champion_name}/image")
async def get_champion_image(champion_name: str):
    """Get champion image URL."""
    try:
        version = "14.4.1"
        # Clean up the champion name for URL
        cleaned_name = champion_name.replace("'", "").replace(" ", "").replace(".", "")
        return {
            "url": f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{cleaned_name}.png"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recommendations")
async def get_recommendations(data: dict):
    """Get champion recommendations based on draft state."""
    # TODO: Implement recommendation logic
    return [
        {"id": "Darius", "name": "Darius", "key": "Darius", "winRate": 54.2},
        {"id": "Garen", "name": "Garen", "key": "Garen", "winRate": 52.8},
        {"id": "Sett", "name": "Sett", "key": "Sett", "winRate": 51.5},
        {"id": "Mordekaiser", "name": "Mordekaiser", "key": "Mordekaiser", "winRate": 53.1},
        {"id": "Maokai", "name": "Maokai", "key": "Maokai", "winRate": 52.3},
    ]

@router.get("/ranks/{rank}")
async def get_rank_icon(rank: str):
    """Get rank icon URL."""
    rank_map = {
        "iron": "https://static.developer.riotgames.com/img/ranked-emblems/iron.png",
        "bronze": "https://static.developer.riotgames.com/img/ranked-emblems/bronze.png",
        "silver": "https://static.developer.riotgames.com/img/ranked-emblems/silver.png",
        "gold": "https://static.developer.riotgames.com/img/ranked-emblems/gold.png",
        "platinum": "https://static.developer.riotgames.com/img/ranked-emblems/platinum.png",
        "emerald": "https://static.developer.riotgames.com/img/ranked-emblems/emerald.png",
        "diamond": "https://static.developer.riotgames.com/img/ranked-emblems/diamond.png",
        "master": "https://static.developer.riotgames.com/img/ranked-emblems/master.png",
        "grandmaster": "https://static.developer.riotgames.com/img/ranked-emblems/grandmaster.png",
        "challenger": "https://static.developer.riotgames.com/img/ranked-emblems/challenger.png",
    }
    
    if rank.lower() in rank_map:
        return {"url": rank_map[rank.lower()]}
    
    raise HTTPException(status_code=404, detail="Rank not found")

@router.get("/roles/{role}")
async def get_role_icon(role: str):
    """Get role icon URL."""
    # Simple emoji fallback for now
    emoji_map = {
        "top": "🏹",
        "jungle": "🌿",
        "mid": "⚔️",
        "adc": "🎯",
        "support": "🛡️",
        "fill": "🔄",
    }
    
    return {"emoji": emoji_map.get(role.lower(), "❓")}