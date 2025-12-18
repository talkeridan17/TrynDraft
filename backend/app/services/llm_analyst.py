import os
from typing import List, Dict, Optional
from openai import OpenAI
import json

class LLMAnalystService:
    """Service to provide real-time draft analysis using LLM."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.model = "gpt-4-turbo-preview"  # or "gpt-3.5-turbo" for cheaper
        
        # Fallback templates if LLM is unavailable
        self.fallback_responses = {
            "BAN": {
                "early": "Consider banning meta champions that counter your planned composition.",
                "mid": "Target champions that synergize well with the enemy's current picks.",
                "late": "Ban comfort picks for the enemy team's likely roles."
            },
            "PICK": {
                "early": "Pick strong meta champions or secure your team's core composition.",
                "mid": "Look for champions that counter the enemy's picks or complete your team synergy.",
                "late": "Fill remaining roles with comfort picks that round out your team composition."
            }
        }
    
    def generate_analysis(self, draft_state: Dict, available_champions: List[str], 
                         top_recommendation: str) -> str:
        """Generate analysis for the current draft state."""
        
        if not self.client:
            return self._generate_fallback_analysis(draft_state)
        
        prompt = self._build_analysis_prompt(draft_state, available_champions, top_recommendation)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional League of Legends draft analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM API error: {e}")
            return self._generate_fallback_analysis(draft_state)
    
    def _build_analysis_prompt(self, draft_state: Dict, available_champions: List[str], 
                              top_recommendation: str) -> str:
        """Build the prompt for the LLM."""
        
        blue_picks = draft_state.get('picks', {}).get('BLUE', [])
        red_picks = draft_state.get('picks', {}).get('RED', [])
        blue_bans = draft_state.get('bans', {}).get('BLUE', [])
        red_bans = draft_state.get('bans', {}).get('RED', [])
        
        prompt = f"""
        Current Draft State:
        
        Blue Team:
        - Picks: {[p.get('champion', 'Empty') for p in blue_picks]}
        - Bans: {blue_bans}
        
        Red Team:
        - Picks: {[p.get('champion', 'Empty') for p in red_picks]}
        - Bans: {red_bans}
        
        Current Phase: {draft_state.get('phase', 'BAN')}
        Turn: {draft_state.get('turn', 0)}/20
        
        Available Champions: {available_champions[:10]}... (and {len(available_champions)-10} more)
        
        Top Recommended Pick: {top_recommendation}
        
        Please provide a concise analysis (3-4 sentences) about:
        1. The current draft state
        2. Why {top_recommendation} is a good pick/ban now
        3. Strategic considerations for the next move
        
        Focus on practical, actionable advice.
        """
        
        return prompt
    
    def _generate_fallback_analysis(self, draft_state: Dict) -> str:
        """Generate fallback analysis when LLM is unavailable."""
        phase = draft_state.get('phase', 'BAN')
        turn = draft_state.get('turn', 0)
        
        if phase == 'BAN':
            if turn < 3:
                stage = "early"
            elif turn < 7:
                stage = "mid"
            else:
                stage = "late"
        else:
            pick_turn = turn - 10
            if pick_turn < 3:
                stage = "early"
            elif pick_turn < 7:
                stage = "mid"
            else:
                stage = "late"
        
        return self.fallback_responses[phase][stage]