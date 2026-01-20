"""
LLM Prompts Service for TrynDraft
Contains all prompts for different draft stages and analysis types
"""
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class DraftContext:
    """Context for generating prompts."""
    phase: str  # 'BAN' or 'PICK'
    turn: int  # 0-19
    side: str  # 'BLUE' or 'RED'
    role: str  # 'TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'
    elo: str  # 'IRON' to 'CHALLENGER'
    bans_blue: List[str]
    bans_red: List[str]
    picks_blue: List[Dict]  # [{champion, role}, ...]
    picks_red: List[Dict]
    user_champion_pool: Optional[List[Dict]] = None  # [{champion, role, proficiency}, ...]
    user_preferred_roles: Optional[List[str]] = None


class LLMPromptsService:
    """
    Generates context-aware prompts for LLM analysis.

    Prompts are designed for:
    1. Draft stage awareness (early ban, mid pick, final picks)
    2. User context (champion pool, role preference)
    3. Specific analysis types (recommendations, analysis, gameplan)
    """

    # Draft stage definitions
    STAGES = {
        'EARLY_BAN': (0, 5),      # Turns 0-5: First ban phase
        'FIRST_PICK': (6, 9),     # Turns 6-9: First pick phase
        'SECOND_BAN': (10, 13),   # Turns 10-13: Second ban phase
        'FINAL_PICK': (14, 19),   # Turns 14-19: Final pick phase
        'COMPLETE': (20, 20)      # Turn 20: Draft complete
    }

    def get_stage(self, turn: int) -> str:
        """Determine draft stage from turn number."""
        for stage, (start, end) in self.STAGES.items():
            if start <= turn <= end:
                return stage
        return 'COMPLETE'

    def get_analysis_prompt(self, context: DraftContext) -> str:
        """
        Generate analysis prompt based on current draft state.

        Returns a prompt that asks the LLM to analyze the draft and provide
        strategic insight appropriate to the current stage.
        """
        stage = self.get_stage(context.turn)

        # Build the base state description
        state_desc = self._build_state_description(context)

        # Build user context if available
        user_context = self._build_user_context(context)

        # Get stage-specific analysis focus
        analysis_focus = self._get_analysis_focus(stage, context)

        prompt = f"""You are an expert League of Legends draft analyst. Analyze the following draft state and provide strategic insight.

{state_desc}

{user_context}

{analysis_focus}

Provide your analysis in 3-4 concise sentences. Focus on:
1. Current state assessment (who has the advantage)
2. Key strategic implications
3. What to watch for in upcoming picks/bans

Keep your response focused and actionable."""

        return prompt

    def get_recommendation_prompt(self, context: DraftContext, num_recommendations: int = 5) -> str:
        """
        Generate prompt for champion recommendations.

        Asks the LLM to recommend champions to pick or ban based on the current state.
        """
        stage = self.get_stage(context.turn)
        is_ban_phase = 'BAN' in stage

        state_desc = self._build_state_description(context)
        user_context = self._build_user_context(context)

        action = "ban" if is_ban_phase else "pick"
        role_context = f" for the {context.role} role" if not is_ban_phase else ""

        pool_instruction = ""
        if context.user_champion_pool and not is_ban_phase:
            pool_instruction = "\n\nIMPORTANT: Prioritize champions from the user's champion pool when making recommendations."

        prompt = f"""You are an expert League of Legends draft coach. Based on the current draft state, recommend the best champions to {action}{role_context}.

{state_desc}

{user_context}
{pool_instruction}

Provide exactly {num_recommendations} {action} recommendations in this format:
1. [Champion Name] - [Brief reason]
2. [Champion Name] - [Brief reason]
...

Consider:
- Current meta strength
- Team composition needs
- Counter-pick potential
- User's champion pool (if picking)

Be specific and strategic."""

        return prompt

    def get_gameplan_prompt(self, context: DraftContext) -> str:
        """
        Generate prompt for complete draft gameplan.

        Used when draft is complete to generate comprehensive analysis and gameplan.
        """
        state_desc = self._build_state_description(context)

        prompt = f"""You are an expert League of Legends analyst. The draft is complete. Provide a comprehensive gameplan for the {context.side} team.

{state_desc}

Provide analysis covering:

## Team Composition Analysis
- Strengths of {context.side} team
- Weaknesses and vulnerabilities
- Win conditions

## Laning Phase
- Expected lane matchups and outcomes
- Jungle pathing considerations
- Early game priorities

## Mid-Game Strategy
- Power spikes to play around
- Objective priorities
- Teamfight vs splitpush orientation

## Late Game
- Scaling outlook
- How to close out the game

Keep each section to 2-3 sentences. Be specific to these champions."""

        return prompt

    def get_matchup_analysis_prompt(
        self,
        champion: str,
        opponent: str,
        role: str
    ) -> str:
        """Generate prompt for specific matchup analysis."""
        prompt = f"""You are an expert League of Legends analyst. Provide a concise matchup analysis.

Matchup: {champion} vs {opponent} in {role} lane

Cover:
1. Who wins at different stages (early/mid/late)
2. Key abilities and interactions to watch
3. How to play the matchup (aggressive/passive/reactive)
4. Items or runes that affect the matchup

Keep response to 4-5 sentences. Be specific and practical."""

        return prompt

    def get_counter_pick_prompt(
        self,
        enemy_champion: str,
        role: str,
        available_champions: List[str] = None
    ) -> str:
        """Generate prompt for counter-pick suggestions."""
        available_context = ""
        if available_champions:
            available_context = f"\n\nAvailable champions: {', '.join(available_champions[:20])}"

        prompt = f"""You are an expert League of Legends draft coach. The enemy has picked {enemy_champion} for {role}.

Suggest the best counter-picks, explaining why each is effective.{available_context}

Format:
1. [Champion] - [Why they counter {enemy_champion}]
2. [Champion] - [Why they counter {enemy_champion}]
3. [Champion] - [Why they counter {enemy_champion}]

Consider: lane matchup, teamfight impact, and scaling."""

        return prompt

    def get_synergy_analysis_prompt(
        self,
        champions: List[str]
    ) -> str:
        """Generate prompt for team synergy analysis."""
        prompt = f"""You are an expert League of Legends analyst. Analyze the synergy of this team composition:

Team: {', '.join(champions)}

Cover:
1. Key synergies between champions
2. Wombo combo potential
3. Teamfight coordination
4. Weaknesses in the composition
5. Suggested playstyle

Keep response focused and actionable (5-6 sentences)."""

        return prompt

    def get_draft_start_prompt(self, context: DraftContext) -> str:
        """Generate prompt for draft start (initial overview)."""
        prompt = f"""You are an expert League of Legends draft analyst helping with a {context.elo} ranked draft.

The user is playing {context.side} side as {context.role}.

Provide a brief overview (2-3 sentences) covering:
1. General draft strategy for {context.side} side
2. Key priorities for {context.role} in this meta
3. What to consider during the ban phase

Be concise and practical."""

        return prompt

    # Helper methods

    def _build_state_description(self, context: DraftContext) -> str:
        """Build draft state description."""
        blue_picks = self._format_picks(context.picks_blue)
        red_picks = self._format_picks(context.picks_red)

        stage = self.get_stage(context.turn)

        return f"""=== DRAFT STATE ===
Stage: {stage} (Turn {context.turn}/20)
Phase: {context.phase}
User: {context.side} side, playing {context.role}
Rank: {context.elo}

Blue Team:
├─ Bans: {', '.join(context.bans_blue) if context.bans_blue else 'None'}
└─ Picks: {blue_picks if blue_picks else 'None'}

Red Team:
├─ Bans: {', '.join(context.bans_red) if context.bans_red else 'None'}
└─ Picks: {red_picks if red_picks else 'None'}"""

    def _build_user_context(self, context: DraftContext) -> str:
        """Build user context section."""
        if not context.user_champion_pool and not context.user_preferred_roles:
            return ""

        sections = ["=== USER PROFILE ==="]

        if context.user_preferred_roles:
            sections.append(f"Preferred Roles: {', '.join(context.user_preferred_roles)}")

        if context.user_champion_pool:
            pool_str = []
            for champ in context.user_champion_pool[:10]:  # Limit to 10
                name = champ.get('champion', champ.get('champion_name', ''))
                prof = champ.get('proficiency', 0)
                stars = '★' * prof + '☆' * (5 - prof)
                pool_str.append(f"{name} ({stars})")

            sections.append(f"Champion Pool: {', '.join(pool_str)}")

        return '\n'.join(sections)

    def _format_picks(self, picks: List[Dict]) -> str:
        """Format picks list for display."""
        if not picks:
            return ""

        formatted = []
        for pick in picks:
            if isinstance(pick, dict):
                champ = pick.get('champion', '')
                role = pick.get('role', '')
                if champ:
                    formatted.append(f"{champ} ({role})" if role else champ)
            elif isinstance(pick, str) and pick:
                formatted.append(pick)

        return ', '.join(formatted)

    def _get_analysis_focus(self, stage: str, context: DraftContext) -> str:
        """Get stage-specific analysis focus."""
        focuses = {
            'EARLY_BAN': f"""=== ANALYSIS FOCUS: Early Ban Phase ===
Focus on:
- Which champions should be banned to deny enemy strategies
- What bans protect the {context.role} lane
- Meta-relevant bans for {context.elo} rank""",

            'FIRST_PICK': f"""=== ANALYSIS FOCUS: First Pick Phase ===
Focus on:
- Flex picks that can go multiple roles
- Strong blind picks for {context.role}
- Setting up team composition direction""",

            'SECOND_BAN': f"""=== ANALYSIS FOCUS: Second Ban Phase ===
Focus on:
- Targeted bans against enemy composition
- Protecting remaining picks
- Denying counters to your team""",

            'FINAL_PICK': f"""=== ANALYSIS FOCUS: Final Picks ===
Focus on:
- Counter-picking opportunities
- Completing team composition
- Role-specific matchup considerations""",

            'COMPLETE': f"""=== ANALYSIS FOCUS: Draft Complete ===
Focus on:
- Overall composition comparison
- Win conditions for each team
- Game plan recommendations"""
        }

        return focuses.get(stage, focuses['COMPLETE'])


# Singleton instance
_prompts_service: Optional[LLMPromptsService] = None


def get_prompts_service() -> LLMPromptsService:
    """Get singleton instance of LLMPromptsService."""
    global _prompts_service
    if _prompts_service is None:
        _prompts_service = LLMPromptsService()
    return _prompts_service
