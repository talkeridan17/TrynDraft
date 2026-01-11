# app/services/data_dragon.py
import httpx
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os

class DataDragonService:
    """Service to fetch and cache Data Dragon data."""
    
    def __init__(self):
        self.base_url = "https://ddragon.leagueoflegends.com"
        self.cache_dir = "data_cache"
        self.cache_duration = timedelta(hours=6)
        self._champion_data = None
        self._version = None
        self._champion_images = {}
        
        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)
    
    async def get_latest_version(self) -> str:
        """Get the latest game version from Data Dragon."""
        cache_file = os.path.join(self.cache_dir, "version.json")
        
        # Check cache
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                cached_time = datetime.fromisoformat(cache_data['cached_at'])
                if datetime.now() - cached_time < self.cache_duration:
                    return cache_data['version']
        
        # Fetch fresh data
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/versions.json")
            response.raise_for_status()
            versions = response.json()
            latest_version = versions[0]
            
            # Cache it
            cache_data = {
                'version': latest_version,
                'cached_at': datetime.now().isoformat()
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            
            return latest_version
    
    async def get_champion_data(self, version: Optional[str] = None) -> Dict:
        """Get champion data from Data Dragon."""
        if not version:
            version = await self.get_latest_version()
        
        cache_file = os.path.join(self.cache_dir, f"champions_{version}.json")
        
        # Check cache
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                cached_time = datetime.fromisoformat(cache_data['cached_at'])
                if datetime.now() - cached_time < self.cache_duration:
                    return cache_data['data']
        
        # Fetch fresh data
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/cdn/{version}/data/en_US/champion.json"
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Process champion data
            champions = {}
            for champ_id, champ_data in data['data'].items():
                champions[champ_id] = {
                    'id': champ_id,
                    'key': champ_data['key'],
                    'name': champ_data['name'],
                    'title': champ_data['title'],
                    'lore': champ_data.get('blurb', ''),
                    'tags': champ_data['tags'],
                    'stats': champ_data.get('stats', {}),
                    'image': {
                        'full': champ_data['image']['full'],
                        'sprite': champ_data['image']['sprite'],
                        'group': champ_data['image']['group']
                    }
                }
            
            # Cache it
            cache_data = {
                'data': champions,
                'cached_at': datetime.now().isoformat()
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            
            return champions
    
    async def get_champion_details(self, champion_id: str, version: Optional[str] = None) -> Dict:
        """Get detailed champion information."""
        if not version:
            version = await self.get_latest_version()
        
        cache_file = os.path.join(self.cache_dir, f"champion_{champion_id}_{version}.json")
        
        # Check cache
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                cached_time = datetime.fromisoformat(cache_data['cached_at'])
                if datetime.now() - cached_time < self.cache_duration:
                    return cache_data['data']
        
        # Fetch fresh data
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/cdn/{version}/data/en_US/champion/{champion_id}.json"
            response = await client.get(url)
            if response.status_code == 404:
                raise ValueError(f"Champion {champion_id} not found")
            response.raise_for_status()
            data = response.json()
            
            # Cache it
            cache_data = {
                'data': data['data'][champion_id],
                'cached_at': datetime.now().isoformat()
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            
            return data['data'][champion_id]
    
    async def get_champion_image_url(self, champion_id: str, version: Optional[str] = None) -> str:
        """Get champion image URL."""
        if not version:
            version = await self.get_latest_version()
        
        # Clean champion ID for URL
        clean_id = champion_id.replace("'", "").replace(" ", "").replace(".", "")
        return f"{self.base_url}/cdn/{version}/img/champion/{clean_id}.png"
    
    async def get_role_icons(self) -> Dict[str, str]:
        """Get role icon URLs from Community Dragon CDN."""
        # Community Dragon provides League client assets including role icons
        base_url = "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-champ-select/global/default"

        return {
            'TOP': f"{base_url}/position-top.png",
            'JUNGLE': f"{base_url}/position-jungle.png",
            'MID': f"{base_url}/position-middle.png",
            'MIDDLE': f"{base_url}/position-middle.png",
            'ADC': f"{base_url}/position-bottom.png",
            'BOTTOM': f"{base_url}/position-bottom.png",
            'SUPPORT': f"{base_url}/position-utility.png",
            'UTILITY': f"{base_url}/position-utility.png",
            'FILL': f"{base_url}/position-fill.png"
        }
    
    async def get_rank_icons(self) -> Dict[str, str]:
        """Get rank icon URLs."""
        return {
            'IRON': 'https://static.wikia.nocookie.net/leagueoflegends/images/e/e7/Season_2022_-_Iron.png',
            'BRONZE': 'https://static.wikia.nocookie.net/leagueoflegends/images/3/3c/Season_2022_-_Bronze.png',
            'SILVER': 'https://static.wikia.nocookie.net/leagueoflegends/images/8/8d/Season_2022_-_Silver.png',
            'GOLD': 'https://static.wikia.nocookie.net/leagueoflegends/images/6/6d/Season_2022_-_Gold.png',
            'PLATINUM': 'https://static.wikia.nocookie.net/leagueoflegends/images/5/5a/Season_2022_-_Platinum.png',
            'EMERALD': 'https://static.wikia.nocookie.net/leagueoflegends/images/0/06/Season_2024_-_Emerald.png',
            'DIAMOND': 'https://static.wikia.nocookie.net/leagueoflegends/images/4/44/Season_2022_-_Diamond.png',
            'MASTER': 'https://static.wikia.nocookie.net/leagueoflegends/images/c/cf/Season_2022_-_Master.png',
            'GRANDMASTER': 'https://static.wikia.nocookie.net/leagueoflegends/images/4/41/Season_2022_-_Grandmaster.png',
            'CHALLENGER': 'https://static.wikia.nocookie.net/leagueoflegends/images/0/04/Season_2022_-_Challenger.png'
        }
    
    async def get_live_patches(self) -> List[str]:
        """Fetch the latest 5 patches from Data Dragon."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://ddragon.leagueoflegends.com/api/versions.json")
                response.raise_for_status()
                all_versions = response.json()
                # Filter to major.minor versions and get latest 5
                patches = []
                for version in all_versions:
                    if version.count('.') >= 1:
                        major_minor = '.'.join(version.split('.')[:2])
                        if major_minor not in patches:
                            patches.append(major_minor)
                    if len(patches) >= 5:
                        break
                return patches
        except Exception as e:
            print(f"Error fetching patches: {e}")
            # Fallback to recent patches
            return ["14.5", "14.4", "14.3", "14.2", "14.1"]

    async def get_live_regions(self) -> List[Dict[str, str]]:
        """Fetch available regions from Riot API."""
        # Riot's platform regions
        regions = [
            {"id": "NA", "name": "North America"},
            {"id": "EUW", "name": "Europe West"},
            {"id": "EUNE", "name": "Europe Nordic & East"},
            {"id": "KR", "name": "Korea"},
            {"id": "BR", "name": "Brazil"},
            {"id": "LAN", "name": "Latin America North"},
            {"id": "LAS", "name": "Latin America South"},
            {"id": "OCE", "name": "Oceania"},
            {"id": "RU", "name": "Russia"},
            {"id": "TR", "name": "Turkey"},
            {"id": "JP", "name": "Japan"},
            {"id": "SG", "name": "Singapore"},
            {"id": "PH", "name": "Philippines"},
            {"id": "TW", "name": "Taiwan"},
            {"id": "VN", "name": "Vietnam"}
        ]
        return regions