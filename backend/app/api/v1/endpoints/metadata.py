from fastapi import APIRouter, HTTPException
from app.services.data_dragon import DataDragonService

router = APIRouter()
data_dragon = DataDragonService()

@router.get("/patches")
async def get_patches():
    """Get available game patches."""
    try:
        patches = await data_dragon.get_live_patches()
        return {"patches": patches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/regions")
async def get_regions():
    """Get available regions."""
    try:
        regions = await data_dragon.get_live_regions()
        return {"regions": regions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))