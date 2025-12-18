# backend/app/services/web_scraper.py
import asyncio
import aiohttp
import json
import re
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin, urlparse
import time

logger = logging.getLogger(__name__)

class WebScraper:
    """Scrape League of Legends content for LLM training."""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Sources to scrape
        self.sources = {
            'mobafire': {
                'base_url': 'https://www.mobafire.com',
                'paths': [
                    '/league-of-legends/build',
                    '/league-of-legends/guide',
                    '/league-of-legends/champion'
                ]
            },
            'lolalytics': {
                'base_url': 'https://lolalytics.com',
                'paths': ['/lol']
            },
            'opgg': {
                'base_url': 'https://www.op.gg',
                'paths': ['/champions']
            },
            'reddit': {
                'base_url': 'https://www.reddit.com',
                'paths': ['/r/summonerschool', '/r/leagueoflegends']
            }
        }
    
    async def initialize(self):
        """Initialize the HTTP session."""
        self.session = aiohttp.ClientSession(headers=self.headers)
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
    
    async def scrape_source(self, source_name: str) -> List[Dict]:
        """Scrape a specific source."""
        if source_name not in self.sources:
            logger.error(f"Unknown source: {source_name}")
            return []
        
        source_config = self.sources[source_name]
        all_content = []
        
        for path in source_config['paths']:
            url = urljoin(source_config['base_url'], path)
            logger.info(f"Scraping {url}")
            
            try:
                if source_name == 'mobafire':
                    content = await self.scrape_mobafire(url)
                elif source_name == 'lolalytics':
                    content = await self.scrape_lolalytics(url)
                elif source_name == 'opgg':
                    content = await self.scrape_opgg(url)
                elif source_name == 'reddit':
                    content = await self.scrape_reddit(url)
                else:
                    content = await self.scrape_generic(url)
                
                all_content.extend(content)
                await asyncio.sleep(2)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")
                continue
        
        return all_content
    
    async def scrape_mobafire(self, url: str) -> List[Dict]:
        """Scrape Mobafire guides and builds."""
        content = []
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find guide links
                guide_links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '/league-of-legends/guide/' in href or '/league-of-legends/build/' in href:
                        full_url = urljoin('https://www.mobafire.com', href)
                        guide_links.append(full_url)
                
                # Scrape each guide
                for guide_url in guide_links[:10]:  # Limit to 10 guides per path
                    try:
                        guide_content = await self.scrape_mobafire_guide(guide_url)
                        if guide_content:
                            content.append({
                                'source': 'mobafire',
                                'url': guide_url,
                                'content': guide_content,
                                'champion': self.extract_champion_from_url(guide_url),
                                'role': self.extract_role_from_content(guide_content),
                                'tags': ['guide', 'build', 'strategy'],
                                'created_at': datetime.now().isoformat()
                            })
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"Error scraping guide {guide_url}: {str(e)}")
                        continue
                
        except Exception as e:
            logger.error(f"Error scraping Mobafire: {str(e)}")
        
        return content
    
    async def scrape_mobafire_guide(self, url: str) -> Optional[str]:
        """Scrape individual Mobafire guide content."""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract guide content
                content_divs = soup.find_all('div', class_=re.compile(r'guide-content|build-section'))
                content_parts = []
                
                for div in content_divs:
                    # Remove script and style tags
                    for script in div.find_all(['script', 'style']):
                        script.decompose()
                    
                    text = div.get_text(strip=True, separator='\n')
                    if text and len(text) > 100:  # Only include substantial content
                        content_parts.append(text)
                
                return '\n\n'.join(content_parts)
                
        except Exception as e:
            logger.error(f"Error scraping guide {url}: {str(e)}")
            return None
    
    async def scrape_lolalytics(self, url: str) -> List[Dict]:
        """Scrape Lolalytics data."""
        content = []
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract champion data
                champion_sections = soup.find_all('div', class_=re.compile(r'champion|tier-list'))
                
                for section in champion_sections:
                    text = section.get_text(strip=True, separator='\n')
                    if text and len(text) > 50:
                        content.append({
                            'source': 'lolalytics',
                            'url': url,
                            'content': text,
                            'tags': ['stats', 'meta', 'tier_list'],
                            'created_at': datetime.now().isoformat()
                        })
                
        except Exception as e:
            logger.error(f"Error scraping Lolalytics: {str(e)}")
        
        return content
    
    async def scrape_reddit(self, url: str) -> List[Dict]:
        """Scrape Reddit posts and comments."""
        content = []
        
        try:
            # Use Reddit's JSON API
            json_url = url.rstrip('/') + '.json'
            async with self.session.get(json_url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                # Extract posts and comments
                if isinstance(data, list) and len(data) > 0:
                    posts = data[0]['data']['children']
                    
                    for post in posts[:20]:  # Limit to 20 posts
                        post_data = post['data']
                        
                        # Get post content
                        post_content = f"Title: {post_data.get('title', '')}\n\n"
                        post_content += f"Text: {post_data.get('selftext', '')}"
                        
                        if post_content.strip():
                            content.append({
                                'source': 'reddit',
                                'url': f"https://reddit.com{post_data.get('permalink', '')}",
                                'content': post_content,
                                'tags': ['discussion', 'community', 'advice'],
                                'created_at': datetime.fromtimestamp(post_data.get('created_utc', 0)).isoformat()
                            })
                        
                        # Get comments if available
                        if 'replies' in post_data and post_data['replies']:
                            comments = self.extract_comments(post_data['replies'])
                            for comment in comments[:10]:  # Limit to 10 comments per post
                                content.append({
                                    'source': 'reddit',
                                    'url': f"https://reddit.com{post_data.get('permalink', '')}",
                                    'content': f"Comment: {comment}",
                                    'tags': ['discussion', 'comment', 'advice'],
                                    'created_at': datetime.now().isoformat()
                                })
                
        except Exception as e:
            logger.error(f"Error scraping Reddit: {str(e)}")
        
        return content
    
    def extract_comments(self, replies: Dict) -> List[str]:
        """Extract comments from Reddit replies."""
        comments = []
        
        if isinstance(replies, dict) and 'data' in replies:
            for child in replies['data'].get('children', []):
                if child['kind'] == 't1':  # Comment
                    comment_data = child['data']
                    if comment_data.get('body'):
                        comments.append(comment_data['body'])
                        
                        # Recursively extract replies
                        if 'replies' in comment_data and comment_data['replies']:
                            comments.extend(self.extract_comments(comment_data['replies']))
        
        return comments
    
    async def scrape_opgg(self, url: str) -> List[Dict]:
        """Scrape OP.GG data."""
        content = []
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract champion statistics
                stats_tables = soup.find_all('table', class_=re.compile(r'champion|stat'))
                
                for table in stats_tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 3:
                            champion = cells[0].get_text(strip=True)
                            win_rate = cells[1].get_text(strip=True)
                            pick_rate = cells[2].get_text(strip=True)
                            
                            if champion and win_rate and pick_rate:
                                content.append({
                                    'source': 'opgg',
                                    'url': url,
                                    'content': f"{champion}: Win Rate: {win_rate}, Pick Rate: {pick_rate}",
                                    'champion': champion,
                                    'tags': ['stats', 'meta'],
                                    'created_at': datetime.now().isoformat()
                                })
                
        except Exception as e:
            logger.error(f"Error scraping OP.GG: {str(e)}")
        
        return content
    
    async def scrape_generic(self, url: str) -> List[Dict]:
        """Generic web scraping for fallback."""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract main content
                text = soup.get_text(strip=True, separator='\n')
                
                if text and len(text) > 500:
                    return [{
                        'source': 'generic',
                        'url': url,
                        'content': text[:5000],  # Limit content length
                        'tags': ['general'],
                        'created_at': datetime.now().isoformat()
                    }]
        
        except Exception as e:
            logger.error(f"Error scraping generic URL {url}: {str(e)}")
        
        return []
    
    def extract_champion_from_url(self, url: str) -> Optional[str]:
        """Extract champion name from URL."""
        # Common patterns for champion names in URLs
        patterns = [
            r'/([a-z-]+)-guide-',
            r'/([a-z-]+)-build-',
            r'/champion/([a-z-]+)',
            r'/([a-z-]+)/'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url.lower())
            if match:
                champion = match.group(1).replace('-', ' ').title()
                return champion
        
        return None
    
    def extract_role_from_content(self, content: str) -> Optional[str]:
        """Extract role from content text."""
        roles = ['top', 'jungle', 'mid', 'adc', 'support']
        content_lower = content.lower()
        
        for role in roles:
            if role in content_lower:
                return role.upper()
        
        return None
    
    async def run_scraping_job(self, sources: List[str] = None) -> List[Dict]:
        """Run scraping for specified sources."""
        if sources is None:
            sources = list(self.sources.keys())
        
        await self.initialize()
        
        all_content = []
        for source in sources:
            logger.info(f"Starting scraping for {source}")
            try:
                content = await self.scrape_source(source)
                all_content.extend(content)
                logger.info(f"Scraped {len(content)} items from {source}")
            except Exception as e:
                logger.error(f"Failed to scrape {source}: {str(e)}")
        
        await self.close()
        return all_content