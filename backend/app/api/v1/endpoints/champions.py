# app/api/v1/endpoints/champions.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
import asyncio

from app.services.data_dragon import DataDragonService
from app.database import get_db
from app import models

router = APIRouter()
data_dragon = DataDragonService()

@router.get("/")
async def get_champions():
    """Get all champions from Data Dragon."""
    try:
        champions = await data_dragon.get_champion_data()
        return list(champions.values())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch champions: {str(e)}")

@router.get("/{champion_name}/image")
async def get_champion_image(champion_name: str):
    """Get champion image URL."""
    try:
        url = await data_dragon.get_champion_image_url(champion_name)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/roles/{role}")
async def get_role_icon(role: str):
    """Get role icon."""
    try:
        role_icons = await data_dragon.get_role_icons()
        icon = role_icons.get(role.upper(), "❓")
        return {"icon": icon}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ranks/{rank}")
async def get_rank_icon(rank: str):
    """Get rank icon URL."""
    try:
        rank_icons = await data_dragon.get_rank_icons()
        icon_url = rank_icons.get(rank.upper())
        if not icon_url:
            raise HTTPException(status_code=404, detail="Rank not found")
        return {"url": icon_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/version/latest")
async def get_latest_version():
    """Get the latest game version."""
    try:
        version = await data_dragon.get_latest_version()
        return {"version": version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{champion_id}/details")
async def get_champion_details(champion_id: str):
    """Get detailed champion information."""
    try:
        details = await data_dragon.get_champion_details(champion_id)
        return details
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))