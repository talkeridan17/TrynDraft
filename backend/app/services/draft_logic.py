from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)

class DraftLogic:
    """Core draft logic to prevent duplicate picks and validate actions."""
    
    @staticmethod
    def validate_draft_state(draft_state: Dict) -> Dict:
        """Validate draft state and return cleaned version."""
        # Ensure all required fields exist
        required = ['bans_blue', 'bans_red', 'picks_blue', 'picks_red']
        for field in required:
            if field not in draft_state:
                draft_state[field] = []
        
        # Clean picks to ensure proper structure
        for side in ['picks_blue', 'picks_red']:
            picks = draft_state.get(side, [])
            if not isinstance(picks, list):
                draft_state[side] = []
            elif len(picks) < 5:
                # Pad with empty slots
                draft_state[side] = picks + [{'champion': '', 'role': 'FILL'}] * (5 - len(picks))
        
        return draft_state
    
    @staticmethod
    def get_all_taken_champions(draft_state: Dict) -> Set[str]:
        """Get all champions that are banned or picked."""
        taken = set()
        
        # Add bans
        for side in ['bans_blue', 'bans_red']:
            bans = draft_state.get(side, [])
            for ban in bans:
                if ban and isinstance(ban, str):
                    taken.add(ban)
        
        # Add picks
        for side in ['picks_blue', 'picks_red']:
            picks = draft_state.get(side, [])
            for pick in picks:
                if isinstance(pick, dict) and pick.get('champion'):
                    taken.add(pick['champion'])
        
        return taken
    
    @staticmethod
    def is_champion_available(champion: str, draft_state: Dict) -> bool:
        """Check if a champion can be picked/banned."""
        if not champion:
            return False
        
        taken = DraftLogic.get_all_taken_champions(draft_state)
        return champion not in taken
    
    @staticmethod
    def get_available_champions(all_champions: List[str], draft_state: Dict) -> List[str]:
        """Get list of champions that can still be picked."""
        taken = DraftLogic.get_all_taken_champions(draft_state)
        return [champ for champ in all_champions if champ not in taken]
    
    @staticmethod
    def get_current_picker_info(turn: int) -> Dict:
        """Get information about current picker."""
        if turn < 10:  # Ban phase
            side = "BLUE" if turn % 2 == 0 else "RED"
            position = turn // 2
            is_ban = True
        else:  # Pick phase
            pick_turn = turn - 10
            pick_order = [
                {"side": "BLUE", "position": 0},
                {"side": "RED", "position": 0},
                {"side": "RED", "position": 1},
                {"side": "BLUE", "position": 1},
                {"side": "BLUE", "position": 2},
                {"side": "RED", "position": 2},
                {"side": "RED", "position": 3},
                {"side": "BLUE", "position": 3},
                {"side": "BLUE", "position": 4},
                {"side": "RED", "position": 4},
            ]
            picker = pick_order[pick_turn]
            side = picker["side"]
            position = picker["position"]
            is_ban = False
        
        return {
            "side": side,
            "position": position,
            "is_ban": is_ban,
            "turn": turn
        }
    
    @staticmethod
    def add_ban(champion: str, side: str, draft_state: Dict) -> Dict:
        """Add a ban to draft state with validation."""
        if not DraftLogic.is_champion_available(champion, draft_state):
            raise ValueError(f"Champion {champion} is already taken")
        
        ban_key = f"bans_{side.lower()}"
        bans = draft_state.get(ban_key, [])
        
        if len(bans) >= 5:
            raise ValueError(f"{side} team already has 5 bans")
        
        bans.append(champion)
        draft_state[ban_key] = bans
        
        # Move to next turn if it's the current picker's action
        current_info = DraftLogic.get_current_picker_info(draft_state.get('current_turn', 0))
        if current_info['is_ban'] and current_info['side'] == side:
            draft_state['current_turn'] += 1
            if draft_state['current_turn'] == 10:
                draft_state['phase'] = 'PICK'
        
        return draft_state
    
    @staticmethod
    def add_pick(champion: str, role: str, side: str, draft_state: Dict) -> Dict:
        """Add a pick to draft state with validation."""
        if not DraftLogic.is_champion_available(champion, draft_state):
            raise ValueError(f"Champion {champion} is already taken")
        
        pick_key = f"picks_{side.lower()}"
        picks = draft_state.get(pick_key, [])
        
        # Find empty slot
        slot_index = None
        for i, pick in enumerate(picks):
            if isinstance(pick, dict) and not pick.get('champion'):
                slot_index = i
                break
        
        if slot_index is None:
            # Find first empty slot (padded with empty picks)
            for i in range(len(picks), 5):
                picks.append({'champion': '', 'role': 'FILL'})
            slot_index = len(picks) - 1
        
        picks[slot_index] = {'champion': champion, 'role': role}
        draft_state[pick_key] = picks
        
        # Move to next turn if it's the current picker's action
        current_info = DraftLogic.get_current_picker_info(draft_state.get('current_turn', 0))
        if not current_info['is_ban'] and current_info['side'] == side:
            draft_state['current_turn'] += 1
        
        return draft_state