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
from dotenv import load_dotenv

# Ensure .env is loaded before reading environment variables
load_dotenv()

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
        # HuggingFace - using OpenAI-compatible router endpoint
        self.hf_token = os.getenv("HF_TOKEN")  # Get from huggingface.co
        self.hf_api = "https://router.huggingface.co/v1"  # New HF router (OpenAI-compatible)
        self.model_name = "Qwen/Qwen2.5-72B-Instruct"  # High-quality model

        # DEVELOPMENT MODE: Set to False to avoid HuggingFace API charges
        # Set USE_HUGGINGFACE_API=true in .env when ready for production
        self.use_hf_api = os.getenv("USE_HUGGINGFACE_API", "false").lower() == "true"

        if not self.use_hf_api:
            logger.info("HuggingFace API disabled (USE_HUGGINGFACE_API=false). Using rule-based analysis.")

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
        phase = draft_state.get('phase', 'BAN')
        is_complete = phase == 'COMPLETE'

        prompt = self._build_draft_prompt(draft_state, user_preferences)

        # Try HuggingFace API first (only if enabled to avoid charges during dev)
        if self.use_hf_api and self.hf_token:
            try:
                analysis = await self._query_huggingface(prompt, is_complete=is_complete)
                if analysis and not analysis.startswith("Error"):
                    return {
                        "analysis": analysis,
                        "source": "huggingface",
                        "model": "Qwen2.5-72B"
                    }
            except Exception as e:
                logger.error(f"HuggingFace error: {e}")

        # Fallback to rules
        return self._rule_based_analysis(draft_state, user_preferences)

    def _build_draft_prompt(self, draft_state: Dict, user_preferences: Optional[Dict] = None) -> str:
        """Build user-centric prompt focusing on lane matchups and champion pool."""
        blue_bans = draft_state.get('bans', {}).get('blue', [])
        red_bans = draft_state.get('bans', {}).get('red', [])
        blue_picks = self._extract_picks_with_roles(draft_state.get('picks', {}).get('blue', []))
        red_picks = self._extract_picks_with_roles(draft_state.get('picks', {}).get('red', []))
        phase = draft_state.get('phase', 'BAN')
        side = draft_state.get('side', 'BLUE')
        role = draft_state.get('role', 'MID')
        is_user_turn = draft_state.get('is_user_turn', False)

        # NN recommendations and user pool from analysis endpoint
        nn_recommendations = draft_state.get('nn_recommendations', [])
        user_pool = draft_state.get('user_pool', [])

        # Determine user's team and enemy
        user_team_picks = blue_picks if side == 'BLUE' else red_picks
        enemy_team_picks = red_picks if side == 'BLUE' else blue_picks
        all_bans = [b for b in (blue_bans + red_bans) if b]

        # Find enemy laner for this role
        enemy_laner = None
        for pick in enemy_team_picks:
            if pick.get('role', '').upper() == role.upper():
                enemy_laner = pick.get('champion')
                break

        # Build user-centric prompt
        if phase == 'BAN':
            # Ban phase - only shown for user's specific ban turn
            pool_text = ""
            if user_pool:
                pool_text = f"Your {role} champion pool: {', '.join(user_pool[:4])}"

            lane_threats = nn_recommendations[:5] if nn_recommendations else []

            return f"""You're advising a {role} player on what to BAN.

{pool_text}
Already banned: {', '.join(all_bans) if all_bans else 'None'}
Top {role} lane threats: {', '.join(lane_threats[:3]) if lane_threats else 'Check meta'}

IMPORTANT: Only suggest {role} lane champions to ban. Banning an assassin when you play jungle is pointless.

Give ONE ban suggestion in 1-2 sentences.
Focus on: What {role} champion would counter your pool or dominate lane?

Format: "Ban [champion] - [reason focused on {role} lane]" """

        else:
            # Pick phase
            team_champs = [p['champion'] for p in user_team_picks if p.get('champion')]
            enemy_champs = [p['champion'] for p in enemy_team_picks if p.get('champion')]

            if is_user_turn:
                # USER'S PICK - Detailed suggestion
                pool_in_nn = [c for c in user_pool if c in nn_recommendations] if user_pool else []

                matchup_text = ""
                if enemy_laner:
                    matchup_text = f"Enemy {role}: {enemy_laner} - you need a counter or safe pick"
                elif enemy_champs:
                    matchup_text = f"Enemy team so far: {', '.join(enemy_champs)}"
                else:
                    matchup_text = "Enemy hasn't picked yet - consider blind-pick strength"

                recommendation_text = ""
                if pool_in_nn:
                    recommendation_text = f"Best from your pool: {', '.join(pool_in_nn[:3])}"
                elif user_pool:
                    recommendation_text = f"Your pool: {', '.join(user_pool[:3])}"
                if nn_recommendations:
                    recommendation_text += f"\nMeta picks for {role}: {', '.join(nn_recommendations[:3])}"

                team_text = f"Your team: {', '.join(team_champs)}" if team_champs else "First pick"

                return f"""You're advising a {role} player on what to PICK.

{team_text}
{matchup_text}
{recommendation_text}

Give ONE pick suggestion in 1-2 sentences.
Prioritize: 1) Counter enemy {role} if known, 2) Champion from their pool, 3) Team synergy

Format: "Pick [champion] - [reason focused on matchup/synergy]" """

            else:
                # TEAMMATE'S PICK - Brief assessment of what they should consider
                last_pick = team_champs[-1] if team_champs else None

                return f"""A teammate just picked or is picking. Give a BRIEF (1 sentence) assessment.

Your team so far: {', '.join(team_champs) if team_champs else 'None yet'}
Enemy team: {', '.join(enemy_champs) if enemy_champs else 'None yet'}

Just note what the team still needs (tank? AP? engage?) or synergy potential. Be very brief."""

    def _extract_picks_with_roles(self, picks) -> List[Dict]:
        """Extract champion picks with their roles."""
        result = []
        for pick in picks:
            if isinstance(pick, dict) and pick.get('champion'):
                result.append({'champion': pick['champion'], 'role': pick.get('role', '')})
            elif isinstance(pick, str) and pick:
                result.append({'champion': pick, 'role': ''})
        return result
    
    async def _query_huggingface(self, prompt: str, is_complete: bool = False) -> str:
        """Query HuggingFace via OpenAI-compatible router endpoint."""
        headers = {
            "Authorization": f"Bearer {self.hf_token}",
            "Content-Type": "application/json"
        }

        # Adjust system message and max_tokens based on context
        if is_complete:
            system_content = "You are an expert League of Legends analyst and coach. Provide detailed, comprehensive analysis with specific strategies. Write thorough responses covering all requested sections."
            max_tokens = 1500  # Much longer for gameplan
        else:
            system_content = "You are a League of Legends draft analyst. Provide helpful analysis in 4-6 sentences. Be specific with champion recommendations."
            max_tokens = 500  # Reasonable for mid-draft analysis

        # Use OpenAI-compatible chat completions format
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.hf_api}/chat/completions",
                headers=headers,
                json=data
            )

            logger.info(f"HuggingFace response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                # OpenAI format: choices[0].message.content
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                return str(result)
            else:
                logger.warning(f"HuggingFace error: {response.status_code} - {response.text[:200]}")

        return ""
    
    def _rule_based_analysis(self, draft_state: Dict, user_preferences: Optional[Dict] = None) -> Dict:
        """Enhanced rule-based analysis for development mode."""
        phase = draft_state.get('phase', 'BAN')
        role = draft_state.get('role', 'MID')
        side = draft_state.get('side', 'BLUE')
        turn = draft_state.get('turn', 0)

        # Get NN recommendations passed from analysis endpoint
        nn_recs = draft_state.get('nn_recommendations', [])
        user_pool = draft_state.get('user_pool', [])

        # Role-specific meta advice (placeholder until real data)
        role_advice = {
            'TOP': "Strong top laners right now include tanks with good teamfight presence and split-push duelists. Consider champions with CC for engage or sustain for lane dominance.",
            'JUNGLE': "Jungle meta favors early-game gankers and objective control. Look for champions with strong level 3 power spikes and dragon/baron secure.",
            'MID': "Mid lane rewards roaming assassins and control mages. Wave clear and map pressure are key - pick based on your team's win condition.",
            'ADC': "ADC picks should consider team composition peel and engage. Scaling hypercarries work with protect comps, while early-game ADCs pair with aggressive supports.",
            'SUPPORT': "Support picks should complement your ADC and provide what the team needs - engage, peel, or sustain. Vision control champions are always valuable."
        }

        if phase == 'BAN':
            # Ban phase analysis
            analysis = f"[DEV MODE] {role_advice.get(role, 'Analyzing...')}\n\n"
            analysis += f"As {role} on {side} side, focus your bans on champions that counter your role or are strong in the current meta. "
            if nn_recs:
                analysis += f"Top meta picks to consider banning: {', '.join(nn_recs[:3])}."
            if user_pool:
                analysis += f" Protect your pool ({', '.join(user_pool[:2])}) by banning their counters."

        elif phase == 'PICK':
            # Pick phase analysis
            analysis = f"[DEV MODE] {role_advice.get(role, 'Analyzing...')}\n\n"
            if nn_recs:
                analysis += f"Strong picks for {role}: {', '.join(nn_recs[:4])}. "
            if user_pool:
                pool_in_meta = [c for c in user_pool if c in nn_recs] if nn_recs else user_pool[:2]
                if pool_in_meta:
                    analysis += f"From your pool, {', '.join(pool_in_meta[:2])} are good choices."
                else:
                    analysis += f"Your pool ({', '.join(user_pool[:2])}) - pick what you're comfortable with."

        elif phase == 'COMPLETE':
            # Draft complete - detailed gameplan
            analysis = f"[DEV MODE - Full LLM analysis disabled to save costs]\n\n"
            analysis += f"=== DRAFT COMPLETE ===\n"
            analysis += f"Playing {role} on {side} side.\n\n"
            analysis += f"GENERAL STRATEGY:\n"
            analysis += f"• Early game: Focus on lane fundamentals and track the enemy jungler\n"
            analysis += f"• Mid game: Group for objectives when your team has priority\n"
            analysis += f"• Late game: Play around your win condition and don't get caught\n\n"
            analysis += f"Enable USE_HUGGINGFACE_API=true in .env for detailed AI analysis."

        else:
            analysis = "[DEV MODE] Analyzing draft state..."

        return {
            "analysis": analysis,
            "source": "rule-based",
            "model": "development-fallback"
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