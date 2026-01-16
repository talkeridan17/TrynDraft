"""
SINGLE LLM Service for TrynDraft
Handles: Analysis, Fine-tuning prep, and HuggingFace integration
"""
import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import httpx

logger = logging.getLogger(__name__)

class LLMService:
    """
    Complete LLM service for TrynDraft.
    
    Features:
    1. Draft analysis (with Mistral 7B via HuggingFace)
    2. Data scraping for fine-tuning
    3. Fine-tuning preparation
    4. Fallback to rule-based analysis
    
    Why Mistral 7B via HuggingFace?
    - Free (no API costs)
    - Can be fine-tuned
    - Runs in Docker
    - Good enough for draft analysis
    """
    
    def __init__(self):
        # HuggingFace for Mistral 7B
        self.hf_token = os.getenv("HF_TOKEN")  # Get from huggingface.co
        self.hf_api = "https://api-inference.huggingface.co"
        self.model_name = "mistralai/Mistral-7B-Instruct-v0.2"
        
        # Fine-tuned model ID (set after fine-tuning)
        self.fine_tuned_model_id = os.getenv("FINE_TUNED_MODEL_ID")
        
        # Scraping headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Simple rule-based fallback
        self.rules = {
            "BAN": [
                "Ban meta champions: Kassadin, Akali, Yone",
                "Target counters to your composition",
                "Ban high win-rate champions"
            ],
            "PICK": [
                "Pick strong meta champions",
                "Choose champions that counter enemy picks",
                "Pick for team synergy"
            ]
        }
    
    # ===== PART 1: DRAFT ANALYSIS =====
    
    async def analyze_draft(self, draft_state: Dict, user_preferences: Optional[Dict] = None) -> Dict:
        """Generate analysis for current draft state with user preferences."""
        prompt = self._build_draft_prompt(draft_state, user_preferences)

        # Try HuggingFace API first
        if self.hf_token:
            try:
                analysis = await self._query_huggingface(prompt)
                if analysis and not analysis.startswith("Error"):
                    return {
                        "analysis": analysis,
                        "source": "huggingface",
                        "model": "Mistral-7B"
                    }
            except Exception as e:
                logger.error(f"HuggingFace error: {e}")

        # Fallback to rules
        return self._rule_based_analysis(draft_state, user_preferences)

    def _build_draft_prompt(self, draft_state: Dict, user_preferences: Optional[Dict] = None) -> str:
        """Build comprehensive prompt for continuous draft analysis with user context."""
        blue_bans = draft_state.get('bans', {}).get('blue', [])
        red_bans = draft_state.get('bans', {}).get('red', [])
        blue_picks = self._extract_champs(draft_state.get('picks', {}).get('blue', []))
        red_picks = self._extract_champs(draft_state.get('picks', {}).get('red', []))
        phase = draft_state.get('phase', 'BAN')
        turn = draft_state.get('turn', 0)

        # Build contextual prompt based on draft progress
        if turn < 10:
            stage = "Early Draft (Ban Phase)"
            focus = "Analyze ban priorities and denied strategies"
        elif turn < 16:
            stage = "Mid Draft (Core Picks)"
            focus = "Evaluate team compositions and win conditions"
        else:
            stage = "Late Draft (Final Picks)"
            focus = "Assess team strengths, weaknesses, and gameplan"

        # Build user context section
        user_context = ""
        if user_preferences:
            champion_pool = user_preferences.get("champion_pool", [])
            preferred_roles = user_preferences.get("preferred_roles", [])
            rank = user_preferences.get("rank", "PLATINUM")

            user_context = f"""
=== USER PROFILE ===
Rank: {rank}
Preferred Roles: {', '.join(preferred_roles) if preferred_roles else 'None set'}
Champion Pool: {len(champion_pool)} champions
"""
            if champion_pool:
                pool_list = []
                for champ in champion_pool[:10]:  # Show max 10
                    styles = ', '.join(champ.get('playstyles', [])) if champ.get('playstyles') else 'No styles'
                    pool_list.append(f"{champ['champion']} ({champ['role']}, {styles})")
                user_context += f"├─ Pool: {'; '.join(pool_list)}\n"

        return f"""You are a professional League of Legends draft analyst. Provide continuous commentary on this draft:

=== DRAFT STATE ===
Stage: {stage}
Phase: {phase} | Turn: {turn}/20

Blue Team:
├─ Bans: {', '.join(blue_bans) if blue_bans else 'None yet'}
└─ Picks: {', '.join(blue_picks) if blue_picks else 'None yet'}

Red Team:
├─ Bans: {', '.join(red_bans) if red_bans else 'None yet'}
└─ Picks: {', '.join(red_picks) if red_picks else 'None yet'}
{user_context}
=== ANALYSIS TASK ===
{focus}

Provide:
1. Which team has the advantage and why
2. Key strengths of each composition
3. Win conditions for both teams
4. Strategic recommendations for next picks{' (PRIORITIZE champions from user pool if suitable)' if user_preferences and user_preferences.get('champion_pool') else ''}

Keep response concise (3-4 sentences)."""
    
    async def _query_huggingface(self, prompt: str) -> str:
        """Query HuggingFace Inference API."""
        headers = {
            "Authorization": f"Bearer {self.hf_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 100,
                "temperature": 0.7
            }
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.hf_api}/models/{self.model_name}",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                return result[0]['generated_text']
        
        return ""
    
    def _rule_based_analysis(self, draft_state: Dict, user_preferences: Optional[Dict] = None) -> Dict:
        """Simple rule-based analysis with user context."""
        phase = draft_state.get('phase', 'BAN')
        rules = self.rules.get(phase, ["Analyzing draft..."])

        import random
        analysis = random.choice(rules)

        # Add user-specific suggestion if champion pool exists
        if user_preferences and user_preferences.get('champion_pool'):
            pool = user_preferences['champion_pool']
            if pool:
                champ = random.choice(pool)
                analysis += f" Consider picking {champ['champion']} from your pool for {champ['role']}."

        return {
            "analysis": analysis,
            "source": "rule-based",
            "model": "fallback"
        }
    
    # ===== PART 2: DATA SCRAPING FOR FINE-TUNING =====
    
    async def scrape_champion_data(self, champion: str) -> List[Dict]:
        """Scrape data for a single champion."""
        data = []
        
        # Scrape Mobafire
        mobafire_data = await self._scrape_mobafire(champion)
        data.extend(mobafire_data)
        
        # Scrape Lolalytics  
        lolalytics_data = await self._scrape_lolalytics(champion)
        data.extend(lolalytics_data)
        
        return data
    
    async def _scrape_mobafire(self, champion: str) -> List[Dict]:
        """Scrape Mobafire guide."""
        url = f"https://www.mobafire.com/league-of-legends/champion/{champion.lower().replace(' ', '-')}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=5) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Get guide text
                        guide_text = soup.get_text(separator=' ', strip=True)[:500]
                        
                        return [{
                            "source": "mobafire",
                            "champion": champion,
                            "content": guide_text,
                            "type": "guide"
                        }]
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Failed to scrape MOBAFire for {champion}: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error scraping MOBAFire for {champion}: {e}")

        return []
    
    async def _scrape_lolalytics(self, champion: str) -> List[Dict]:
        """Scrape Lolalytics stats."""
        url = f"https://lolalytics.com/lol/{champion.lower()}/"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=5) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Get page text
                        page_text = soup.get_text(separator=' ', strip=True)[:500]
                        
                        return [{
                            "source": "lolalytics",
                            "champion": champion,
                            "content": page_text,
                            "type": "stats"
                        }]
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Failed to scrape LoLalytics for {champion}: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error scraping LoLalytics for {champion}: {e}")

        return []
    
    # ===== PART 3: FINE-TUNING PREPARATION =====
    
    def prepare_training_data(self, scraped_data: List[Dict]) -> List[Dict]:
        """Prepare scraped data for fine-tuning."""
        training_data = []
        
        for item in scraped_data:
            prompt = f"Tell me about {item['champion']} in League of Legends"
            
            if item['type'] == 'guide':
                completion = f"{item['champion']} guide: {item['content'][:200]}"
            elif item['type'] == 'stats':
                completion = f"{item['champion']} statistics: {item['content'][:200]}"
            else:
                completion = f"Information about {item['champion']}: {item['content'][:200]}"
            
            training_data.append({
                "prompt": prompt,
                "completion": completion
            })
        
        return training_data
    
    # ===== HELPER METHODS =====
    
    def _extract_champs(self, picks) -> List[str]:
        """Extract champion names from picks array."""
        champs = []
        for pick in picks:
            if isinstance(pick, dict) and pick.get('champion'):
                champs.append(pick['champion'])
            elif isinstance(pick, str) and pick:
                champs.append(pick)
        return champs