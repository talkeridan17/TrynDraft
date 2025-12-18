# app/services/draft_service.py
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

class DraftService:
    """Service to manage draft state and logic."""
    
    # Standard draft order (Blue = B, Red = R)
    # 10 bans: B1, R1, B2, R2, B3, R3, B4, R4, B5, R5
    # 10 picks: B1, R1, R2, B2, B3, R3, R4, B4, B5, R5
    
    BAN_ORDER = [
        ("BLUE", 0), ("RED", 0), ("BLUE", 1), ("RED", 1), ("BLUE", 2),
        ("RED", 2), ("BLUE", 3), ("RED", 3), ("BLUE", 4), ("RED", 4)
    ]
    
    PICK_ORDER = [
        ("BLUE", 0), ("RED", 0), ("RED", 1), ("BLUE", 1), ("BLUE", 2),
        ("RED", 2), ("RED", 3), ("BLUE", 3), ("BLUE", 4), ("RED", 4)
    ]
    
    def __init__(self):
        self.drafts = {}
    
    def create_draft(self, user_id: str, settings: Dict) -> str:
        """Create a new draft."""
        draft_id = f"draft_{user_id}_{int(datetime.now().timestamp())}"
        
        self.drafts[draft_id] = {
            'id': draft_id,
            'user_id': user_id,
            'settings': settings,
            'state': {
                'phase': 'BAN',  # BAN or PICK
                'turn': 0,  # 0-19 (0-9 bans, 10-19 picks)
                'bans': {'BLUE': [], 'RED': []},
                'picks': {
                    'BLUE': [None, None, None, None, None],
                    'RED': [None, None, None, None, None]
                },
                'roles': {
                    'BLUE': ['FILL', 'FILL', 'FILL', 'FILL', 'FILL'],
                    'RED': ['FILL', 'FILL', 'FILL', 'FILL', 'FILL']
                }
            },
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        return draft_id
    
    def get_current_picker(self, draft_id: str) -> Optional[Tuple[str, int, bool]]:
        """Get the current picker information (side, position, is_ban)."""
        if draft_id not in self.drafts:
            return None
        
        draft = self.drafts[draft_id]
        turn = draft['state']['turn']
        
        if turn < 10:  # Ban phase
            side, position = self.BAN_ORDER[turn]
            return (side, position, True)
        else:  # Pick phase
            side, position = self.PICK_ORDER[turn - 10]
            return (side, position, False)
    
    def make_pick(self, draft_id: str, champion: str, role: Optional[str] = None) -> bool:
        """Make a pick or ban in the draft."""
        if draft_id not in self.drafts:
            return False
        
        draft = self.drafts[draft_id]
        picker_info = self.get_current_picker(draft_id)
        
        if not picker_info:
            return False
        
        side, position, is_ban = picker_info
        
        if is_ban:
            # Add ban
            if champion in draft['state']['bans']['BLUE'] or champion in draft['state']['bans']['RED']:
                return False  # Already banned
            
            draft['state']['bans'][side].append(champion)
        else:
            # Add pick
            # Check if champion is already picked or banned
            all_bans = draft['state']['bans']['BLUE'] + draft['state']['bans']['RED']
            all_picks = [
                p for p in draft['state']['picks']['BLUE'] + draft['state']['picks']['RED']
                if p is not None
            ]
            
            if champion in all_bans or champion in all_picks:
                return False  # Already banned or picked
            
            draft['state']['picks'][side][position] = champion
            if role:
                draft['state']['roles'][side][position] = role
        
        # Move to next turn
        draft['state']['turn'] += 1
        
        # Check if phase should change
        if draft['state']['turn'] == 10 and draft['state']['phase'] == 'BAN':
            draft['state']['phase'] = 'PICK'
        
        draft['updated_at'] = datetime.now().isoformat()
        return True
    
    def remove_pick(self, draft_id: str, side: str, position: int) -> bool:
        """Remove a pick from the draft."""
        if draft_id not in self.drafts:
            return False
        
        draft = self.drafts[draft_id]
        
        # Can only remove picks, not bans
        if draft['state']['picks'][side][position] is None:
            return False
        
        draft['state']['picks'][side][position] = None
        draft['state']['roles'][side][position] = 'FILL'
        draft['updated_at'] = datetime.now().isoformat()
        return True
    
    def remove_ban(self, draft_id: str, side: str, champion: str) -> bool:
        """Remove a ban from the draft."""
        if draft_id not in self.drafts:
            return False
        
        draft = self.drafts[draft_id]
        
        if champion not in draft['state']['bans'][side]:
            return False
        
        draft['state']['bans'][side].remove(champion)
        draft['updated_at'] = datetime.now().isoformat()
        return True
    
    def move_pick(self, draft_id: str, side: str, from_idx: int, to_idx: int) -> bool:
        """Move a pick to a different position."""
        if draft_id not in self.drafts:
            return False
        
        draft = self.drafts[draft_id]
        
        if draft['state']['picks'][side][from_idx] is None:
            return False
        
        # Swap positions
        temp_champ = draft['state']['picks'][side][from_idx]
        temp_role = draft['state']['roles'][side][from_idx]
        
        draft['state']['picks'][side][from_idx] = draft['state']['picks'][side][to_idx]
        draft['state']['roles'][side][from_idx] = draft['state']['roles'][side][to_idx]
        
        draft['state']['picks'][side][to_idx] = temp_champ
        draft['state']['roles'][side][to_idx] = temp_role
        
        draft['updated_at'] = datetime.now().isoformat()
        return True
    
    def set_picker(self, draft_id: str, turn: int) -> bool:
        """Manually set the current picker position."""
        if draft_id not in self.drafts:
            return False
        
        if turn < 0 or turn > 19:
            return False
        
        draft = self.drafts[draft_id]
        draft['state']['turn'] = turn
        
        # Update phase if needed
        if turn >= 10 and draft['state']['phase'] == 'BAN':
            draft['state']['phase'] = 'PICK'
        elif turn < 10 and draft['state']['phase'] == 'PICK':
            draft['state']['phase'] = 'BAN'
        
        draft['updated_at'] = datetime.now().isoformat()
        return True
    
    def get_available_champions(self, draft_id: str) -> List[str]:
        """Get list of champions that can still be picked."""
        if draft_id not in self.drafts:
            return []
        
        draft = self.drafts[draft_id]
        
        # Get all champions from Data Dragon
        # This would be async in practice
        all_champions = []  # Would be fetched from service
        
        # Get banned and picked champions
        banned = draft['state']['bans']['BLUE'] + draft['state']['bans']['RED']
        picked = [
            p for p in draft['state']['picks']['BLUE'] + draft['state']['picks']['RED']
            if p is not None
        ]
        
        taken = set(banned + picked)
        
        # Filter out taken champions
        available = [c for c in all_champions if c not in taken]
        return available
    
    def get_draft_summary(self, draft_id: str) -> Dict:
        """Get a summary of the draft state."""
        if draft_id not in self.drafts:
            return {}
        
        draft = self.drafts[draft_id]
        picker_info = self.get_current_picker(draft_id)
        
        summary = {
            'id': draft_id,
            'phase': draft['state']['phase'],
            'turn': draft['state']['turn'],
            'current_picker': picker_info,
            'bans': draft['state']['bans'],
            'picks': draft['state']['picks'],
            'roles': draft['state']['roles'],
            'progress': {
                'bans_completed': draft['state']['turn'] if draft['state']['phase'] == 'BAN' else 10,
                'total_bans': 10,
                'picks_completed': max(0, draft['state']['turn'] - 10) if draft['state']['phase'] == 'PICK' else 0,
                'total_picks': 10
            }
        }
        
        return summary