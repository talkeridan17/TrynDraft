from fastapi import APIRouter, HTTPException
from typing import List, Dict
import httpx
import asyncio

router = APIRouter()

# Cache champion data to avoid repeated API calls
_champion_cache = None
_last_fetch_time = 0
CACHE_DURATION = 3600  # 1 hour

async def fetch_all_champions() -> List[Dict]:
    """Fetch all champions from Data Dragon API."""
    global _champion_cache, _last_fetch_time
    
    import time
    current_time = time.time()
    
    # Return cached data if still valid
    if _champion_cache and (current_time - _last_fetch_time) < CACHE_DURATION:
        return _champion_cache
    
    try:
        # Get latest version first
        async with httpx.AsyncClient() as client:
            # Get latest version
            versions_resp = await client.get("https://ddragon.leagueoflegends.com/api/versions.json")
            versions = versions_resp.json()
            latest_version = versions[0]
            
            # Get champion data
            champions_resp = await client.get(
                f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion.json"
            )
            champions_data = champions_resp.json()
            
            # Process champion data
            champions = []
            for champ_id, champ_data in champions_data['data'].items():
                champion = {
                    'id': champ_id,
                    'key': champ_data['key'],
                    'name': champ_data['name'],
                    'title': champ_data['title'],
                    'blurb': champ_data.get('blurb', ''),
                    'tags': champ_data.get('tags', []),
                    'partype': champ_data.get('partype', ''),
                    'image': champ_data.get('image', {}),
                    'stats': champ_data.get('stats', {}),
                    'version': latest_version
                }
                champions.append(champion)
            
            # Update cache
            _champion_cache = champions
            _last_fetch_time = current_time
            
            return champions
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch champions: {str(e)}")

@router.get("/")
async def get_champions():
    """Get all champions from Data Dragon."""
    try:
        champions = await fetch_all_champions()
        return champions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch champions: {str(e)}")

@router.get("/{champion_name}/image")
async def get_champion_image(champion_name: str):
    """Get champion image URL."""
    try:
        # First, get the champion to find its image name
        champions = await fetch_all_champions()
        champion = next((c for c in champions if c['name'].lower() == champion_name.lower()), None)
        
        if not champion:
            raise HTTPException(status_code=404, detail=f"Champion {champion_name} not found")
        
        # Get latest version
        async with httpx.AsyncClient() as client:
            versions_resp = await client.get("https://ddragon.leagueoflegends.com/api/versions.json")
            versions = versions_resp.json()
            latest_version = versions[0]
        
        # Clean champion ID for URL
        clean_id = champion['id'].replace("'", "").replace(" ", "").replace(".", "")
        image_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/img/champion/{clean_id}.png"
        
        return {"url": image_url}
        
    except Exception as e:
        # Fallback to generic URL
        clean_name = champion_name.replace("'", "").replace(" ", "").replace(".", "")
        fallback_url = f"https://ddragon.leagueoflegends.com/cdn/14.5.1/img/champion/{clean_name}.png"
        return {"url": fallback_url}

@router.get("/roles/{role}")
async def get_role_icon(role: str):
    """Get role icon URL."""
    # Proper role icons from League CDN
    role_icons = {
        'TOP': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-top.png',
        'JUNGLE': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-jungle.png',
        'MID': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-middle.png',
        'ADC': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-bottom.png',
        'SUPPORT': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-utility.png',
        'FILL': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-fill.png'
    }
    
    icon_url = role_icons.get(role.upper())
    if not icon_url:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return {"url": icon_url}

@router.get("/ranks/{rank}")
async def get_rank_icon(rank: str):
    """Get rank icon URL."""
    rank_icons = {
        'IRON': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/iron.png',
        'BRONZE': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/bronze.png',
        'SILVER': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/silver.png',
        'GOLD': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/gold.png',
        'PLATINUM': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/platinum.png',
        'EMERALD': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/emerald.png',
        'DIAMOND': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/diamond.png',
        'MASTER': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/master.png',
        'GRANDMASTER': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/grandmaster.png',
        'CHALLENGER': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/challenger.png'
    }
    
    icon_url = rank_icons.get(rank.upper())
    if not icon_url:
        raise HTTPException(status_code=404, detail="Rank not found")
    
    return {"url": icon_url}

@router.get("/version/latest")
async def get_latest_version():
    """Get the latest game version."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://ddragon.leagueoflegends.com/api/versions.json")
            versions = response.json()
            latest_version = versions[0]
            return {"version": latest_version}
    except Exception as e:
        # Fallback to known version
        return {"version": "14.5.1"}