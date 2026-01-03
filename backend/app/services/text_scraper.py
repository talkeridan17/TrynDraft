"""
Text Data Scraper for LLM Fine-tuning
Focuses on scraping textual content from guides, discussions, and tutorials
"""

import asyncio
import aiohttp
import json
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import os

logger = logging.getLogger(__name__)

class TextScraper:
    """Scrape textual content for LLM fine-tuning from various sources."""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        self.sources = {
            'mobafire_guides': {
                'base_url': 'https://www.mobafire.com',
                'paths': ['/league-of-legends/guides']
            },
            'reddit_summonschool': {
                'base_url': 'https://www.reddit.com',
                'paths': ['/r/summonerschool', '/r/leagueoflegends']
            },
            'leagueoflegends_fandom': {
                'base_url': 'https://leagueoflegends.fandom.com',
                'paths': ['/wiki/Category:Champion_guides']
            }
        }
    
    async def initialize(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
    
    async def scrape_champion_text_data(self, champion_name: str) -> List[Dict]:
        """
        Scrape textual data for a specific champion.
        Returns: List of text chunks with metadata for training.
        """
        await self.initialize()
        
        all_text_chunks = []
        
        try:
            # 1. Mobafire Guides
            mobafire_data = await self._scrape_mobafire_guides(champion_name)
            all_text_chunks.extend(mobafire_data)
            
            # 2. Reddit Discussions
            reddit_data = await self._scrape_reddit_discussions(champion_name)
            all_text_chunks.extend(reddit_data)
            
            # 3. Fandom Wiki
            fandom_data = await self._scrape_fandom_guides(champion_name)
            all_text_chunks.extend(fandom_data)
            
        except Exception as e:
            logger.error(f"Error scraping {champion_name}: {e}")
        finally:
            await self.close()
        
        return all_text_chunks
    
    async def _scrape_mobafire_guides(self, champion_name: str) -> List[Dict]:
        """Scrape Mobafire champion guides."""
        url_safe_name = champion_name.lower().replace("'", "").replace(" ", "-").replace(".", "")
        url = f"https://www.mobafire.com/league-of-legends/champion/{url_safe_name}"
        
        text_chunks = []
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract guide content sections
                guide_sections = soup.find_all(['div', 'section'], class_=re.compile(r'guide|build|content|strategy'))
                
                for section in guide_sections:
                    # Clean the text
                    text = section.get_text(strip=True, separator='\n')
                    
                    # Remove excessive whitespace
                    text = re.sub(r'\n{3,}', '\n\n', text)
                    
                    # Only include substantial content
                    if len(text) > 200:
                        # Split into manageable chunks (500-1000 characters)
                        chunks = self._split_text_into_chunks(text, 800)
                        
                        for i, chunk in enumerate(chunks):
                            text_chunks.append({
                                'source': 'mobafire_guide',
                                'champion': champion_name,
                                'content': chunk,
                                'chunk_index': i,
                                'total_chunks': len(chunks),
                                'type': 'guide_content',
                                'scraped_at': datetime.now().isoformat()
                            })
                
                logger.info(f"Scraped {len(text_chunks)} text chunks from Mobafire for {champion_name}")
                
        except Exception as e:
            logger.error(f"Error scraping Mobafire for {champion_name}: {e}")
        
        return text_chunks
    
    async def _scrape_reddit_discussions(self, champion_name: str) -> List[Dict]:
        """Scrape Reddit discussions about a champion."""
        # Use Reddit search API
        search_url = f"https://www.reddit.com/r/summonerschool/search.json?q={champion_name}&restrict_sr=on&sort=relevance&t=year"
        
        text_chunks = []
        
        try:
            async with self.session.get(search_url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                if 'data' not in data or 'children' not in data['data']:
                    return []
                
                posts = data['data']['children']
                
                for post in posts[:10]:  # Limit to 10 most relevant posts
                    post_data = post['data']
                    
                    # Combine title and text
                    post_text = f"Title: {post_data.get('title', '')}\n\n"
                    post_text += f"Content: {post_data.get('selftext', '')}"
                    
                    # Clean the text
                    post_text = re.sub(r'\[.*?\]\(.*?\)', '', post_text)  # Remove markdown links
                    post_text = re.sub(r'\n{3,}', '\n\n', post_text)
                    
                    if len(post_text) > 300:
                        chunks = self._split_text_into_chunks(post_text, 600)
                        
                        for i, chunk in enumerate(chunks):
                            text_chunks.append({
                                'source': 'reddit_discussion',
                                'champion': champion_name,
                                'content': chunk,
                                'chunk_index': i,
                                'total_chunks': len(chunks),
                                'type': 'community_discussion',
                                'url': f"https://reddit.com{post_data.get('permalink', '')}",
                                'scraped_at': datetime.now().isoformat()
                            })
                
                logger.info(f"Scraped {len(text_chunks)} text chunks from Reddit for {champion_name}")
                
        except Exception as e:
            logger.error(f"Error scraping Reddit for {champion_name}: {e}")
        
        return text_chunks
    
    async def _scrape_fandom_guides(self, champion_name: str) -> List[Dict]:
        """Scrape League of Legends Fandom wiki guides."""
        url_safe_name = champion_name.replace(" ", "_")
        url = f"https://leagueoflegends.fandom.com/wiki/{url_safe_name}/Guide"
        
        text_chunks = []
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find main content
                    content_div = soup.find('div', {'id': 'mw-content-text'})
                    
                    if content_div:
                        # Get all text paragraphs
                        paragraphs = content_div.find_all('p')
                        
                        for para in paragraphs:
                            text = para.get_text(strip=True, separator=' ')
                            if len(text) > 100:
                                chunks = self._split_text_into_chunks(text, 500)
                                
                                for i, chunk in enumerate(chunks):
                                    text_chunks.append({
                                        'source': 'fandom_wiki',
                                        'champion': champion_name,
                                        'content': chunk,
                                        'chunk_index': i,
                                        'total_chunks': len(chunks),
                                        'type': 'wiki_guide',
                                        'scraped_at': datetime.now().isoformat()
                                    })
                    
                    logger.info(f"Scraped {len(text_chunks)} text chunks from Fandom for {champion_name}")
                    
        except Exception as e:
            logger.warning(f"Could not scrape Fandom for {champion_name}: {e}")
            # Not all champions have guide pages, so this is expected
        
        return text_chunks
    
    def _split_text_into_chunks(self, text: str, chunk_size: int = 500) -> List[str]:
        """Split text into chunks for training data."""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            if len(chunk) > 100:  # Only include substantial chunks
                chunks.append(chunk)
        
        return chunks
    
    def save_text_data(self, data: List[Dict], filename: str = None):
        """Save scraped text data to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"llm_training_data_{timestamp}.json"
        
        # Create directory if it doesn't exist
        os.makedirs("scraped_text_data", exist_ok=True)
        filepath = os.path.join("scraped_text_data", filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(data)} text chunks to {filepath}")
        return filepath
    
    async def scrape_all_champions_text(self, champion_names: List[str], limit: int = 20):
        """Scrape text data for multiple champions."""
        logger.info(f"Starting text data scraping for {len(champion_names)} champions")
        
        all_text_data = []
        
        for champion in champion_names[:limit]:  # Limit to avoid rate limiting
            logger.info(f"Scraping text data for {champion}...")
            
            try:
                champion_data = await self.scrape_champion_text_data(champion)
                all_text_data.extend(champion_data)
                
                logger.info(f"  → Found {len(champion_data)} text chunks")
                
                # Rate limiting - be nice to servers
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to scrape {champion}: {e}")
                continue
        
        # Save all collected data
        if all_text_data:
            self.save_text_data(all_text_data)
            logger.info(f"✅ Total scraped: {len(all_text_data)} text chunks")
        
        return all_text_data


# Utility function for easy usage
async def scrape_champions_for_llm(champions: List[str] = None):
    """
    Main function to scrape champion text data for LLM training.
    
    Args:
        champions: List of champion names to scrape. If None, uses popular champions.
    """
    if champions is None:
        # Default to popular champions for initial scraping
        champions = [
            "Aatrox", "Ahri", "Akali", "Alistar", "Amumu",
            "Annie", "Ashe", "Caitlyn", "Darius", "Ezreal",
            "Garen", "Jinx", "Lee Sin", "Lux", "Master Yi",
            "Miss Fortune", "Morgana", "Teemo", "Yasuo", "Zed"
        ]
    
    scraper = TextScraper()
    await scraper.initialize()
    
    try:
        data = await scraper.scrape_all_champions_text(champions, limit=20)
        return data
    finally:
        await scraper.close()