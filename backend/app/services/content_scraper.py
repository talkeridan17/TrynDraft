import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class ContentScraper:
    """Scrape content from League of Legends websites for LLM training."""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def scrape_mobafire_guide(self, champion: str) -> List[Dict]:
        """Scrape Mobafire guides for a specific champion."""
        content = []
        url = f"https://www.mobafire.com/league-of-legends/champion/{champion.lower()}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Find guide sections
                        guide_sections = soup.find_all('div', class_=re.compile(r'guide-section|build-container'))
                        
                        for section in guide_sections:
                            text = section.get_text(separator='\n', strip=True)
                            if len(text) > 100:
                                content.append({
                                    'source': 'mobafire',
                                    'url': url,
                                    'title': f"{champion} Guide",
                                    'content': text[:2000],  # Limit length
                                    'champion': champion,
                                    'tags': ['guide', 'build'],
                                    'patch_version': '14.4'  # Would need to parse
                                })
        except Exception as e:
            logger.error(f"Error scraping Mobafire for {champion}: {e}")
        
        return content
    
    async def scrape_lolalytics(self, champion: str) -> List[Dict]:
        """Scrape Lolalytics data for a champion."""
        content = []
        url = f"https://lolalytics.com/lol/{champion.lower()}/build/"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Look for statistical data
                        stats_sections = soup.find_all('div', class_=re.compile(r'stats-panel|tier-data'))
                        
                        for section in stats_sections:
                            text = section.get_text(separator='\n', strip=True)
                            if 'win rate' in text.lower() or 'pick rate' in text.lower():
                                content.append({
                                    'source': 'lolalytics',
                                    'url': url,
                                    'title': f"{champion} Stats",
                                    'content': text[:1500],
                                    'champion': champion,
                                    'tags': ['statistics', 'meta'],
                                    'patch_version': '14.4'
                                })
        except Exception as e:
            logger.error(f"Error scraping Lolalytics for {champion}: {e}")
        
        return content
    
    async def scrape_for_champion(self, champion: str) -> List[Dict]:
        """Scrape all sources for a specific champion."""
        tasks = [
            self.scrape_mobafire_guide(champion),
            self.scrape_lolalytics(champion)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_content = []
        
        for result in results:
            if isinstance(result, list):
                all_content.extend(result)
        
        return all_content