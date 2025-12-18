# app/services/llm_service.py
import os
import json
from typing import Dict, List, Optional
import httpx
from datetime import datetime

class LLMService:
    """Service to generate gameplans using LLM."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = os.getenv("LLM_API_URL", "https://api.openai.com/v1")
        self.model = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
        
        # Gameplan templates
        self.templates = {
            "EARLY_GAME": [
                "Focus on farming and avoiding early trades",
                "Look for level 2 advantage",
                "Coordinate with jungle for early gank",
                "Control vision around river",
                "Track enemy summoner spells"
            ],
            "MID_GAME": [
                "Rotate for objective control",
                "Look for picks when enemies are out of position",
                "Set up vision for Baron/Dragon",
                "Split push when appropriate",
                "Group for teamfights around key objectives"
            ],
            "LATE_GAME": [
                "Stay grouped and avoid getting caught",
                "Focus on protecting carries",
                "Control vision in enemy jungle",
                "Look for Elder/Baron opportunities",
                "End game with coordinated pushes"
            ]
        }
    
    async def generate_gameplan(self, draft_state: Dict) -> Dict:
        """Generate a gameplan based on draft composition."""
        
        blue_picks = draft_state.get('picks', {}).get('BLUE', [])
        red_picks = draft_state.get('picks', {}).get('RED', [])
        
        # Analyze team compositions
        blue_comp = self._analyze_composition(blue_picks)
        red_comp = self._analyze_composition(red_picks)
        
        # Generate win conditions
        win_conditions = self._generate_win_conditions(blue_comp, red_comp)
        
        # Generate key objectives
        key_objectives = self._generate_key_objectives(blue_comp)
        
        # Generate teamfight strategy
        teamfight_strategy = self._generate_teamfight_strategy(blue_comp)
        
        # Generate draft grade
        draft_grade = self._calculate_draft_grade(blue_comp, red_comp)
        
        gameplan = {
            "summary": self._generate_summary(blue_comp, red_comp),
            "win_conditions": win_conditions,
            "key_objectives": key_objectives,
            "teamfight_strategy": teamfight_strategy,
            "lane_assignments": self._generate_lane_assignments(blue_picks),
            "draft_grade": draft_grade,
            "strengths": blue_comp.get('strengths', []),
            "weaknesses": blue_comp.get('weaknesses', []),
            "generated_at": datetime.now().isoformat()
        }
        
        return gameplan
    
    def _analyze_composition(self, picks: List[Optional[str]]) -> Dict:
        """Analyze team composition."""
        if not picks or all(p is None for p in picks):
            return {"type": "UNKNOWN", "strengths": [], "weaknesses": []}
        
        # This would use actual champion data
        # For now, return basic analysis
        return {
            "type": "BALANCED",
            "strengths": ["Good teamfight", "Scaling potential"],
            "weaknesses": ["Weak early game", "Vulnerable to split push"]
        }
    
    def _generate_win_conditions(self, blue_comp: Dict, red_comp: Dict) -> List[str]:
        """Generate win conditions for blue team."""
        conditions = [
            "Reach late game where our scaling champions come online",
            "Win teamfights with proper engagement and peel",
            "Secure key objectives (Baron, Elder Dragon)",
            "Protect carries in fights",
            "Control vision to set up picks"
        ]
        
        return conditions[:3]  # Return top 3
    
    def _generate_key_objectives(self, composition: Dict) -> List[str]:
        """Generate key objectives based on composition."""
        objectives = [
            "First Dragon: Look for early dragon control",
            "Herald: Use for early tower pressure",
            "Vision: Control river and enemy jungle",
            "Towers: Focus on outer towers first"
        ]
        return objectives
    
    def _generate_teamfight_strategy(self, composition: Dict) -> str:
        """Generate teamfight strategy."""
        return """Frontline engages while backline deals damage. Focus on protecting carries and using crowd control effectively. Disengage if fight turns unfavorable."""
    
    def _generate_lane_assignments(self, picks: List[Optional[str]]) -> List[str]:
        """Generate lane assignments."""
        if len(picks) < 5:
            return ["Assign champions to positions as they are picked"]
        
        roles = ["Top", "Jungle", "Mid", "ADC", "Support"]
        assignments = []
        
        for i, (pick, role) in enumerate(zip(picks, roles)):
            if pick:
                assignments.append(f"{role}: {pick}")
            else:
                assignments.append(f"{role}: Empty slot")
        
        return assignments
    
    def _calculate_draft_grade(self, blue_comp: Dict, red_comp: Dict) -> Dict:
        """Calculate draft grade."""
        # Simple grading for now
        grade = "B"
        score = 75
        
        strengths = len(blue_comp.get('strengths', []))
        weaknesses = len(blue_comp.get('weaknesses', []))
        
        if strengths >= 3 and weaknesses <= 1:
            grade = "A"
            score = 90
        elif strengths <= 1 and weaknesses >= 3:
            grade = "C"
            score = 60
        
        return {"grade": grade, "score": score, "comment": "Solid draft with good teamfight potential"}
    
    def _generate_summary(self, blue_comp: Dict, red_comp: Dict) -> str:
        """Generate draft summary."""
        return "Blue team has a balanced composition with good scaling into late game. Focus on teamfighting and objective control."
    
    async def generate_with_llm(self, prompt: str) -> str:
        """Generate text using actual LLM API."""
        if not self.api_key:
            return "LLM service not configured. Please set API key."
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 500
                }
                
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content']
                else:
                    return f"LLM API error: {response.status_code}"
                    
        except Exception as e:
            return f"LLM service error: {str(e)}"