from typing import Dict, List, Optional, Tuple

class DraftRulesService:
    """
    Service to enforce draft rules, manage turn order, and validate picks/bans.
    """

    # Standard Ranked/Draft pick-ban order
    STANDARD_BAN_ORDER = [
        ("BLUE", 0), ("BLUE", 1), ("BLUE", 2), ("BLUE", 3), ("BLUE", 4),  # Blue bans 1-5
        ("RED", 0), ("RED", 1), ("RED", 2), ("RED", 3), ("RED", 4)       # Red bans 1-5
    ]
    
    STANDARD_PICK_ORDER = [
        ("BLUE", 0), ("RED", 0), ("RED", 1), ("BLUE", 1), ("BLUE", 2),  # B1, R1, R2, B2, B3
        ("RED", 2), ("BLUE", 3), ("BLUE", 4), ("RED", 3), ("RED", 4)    # R3, B4, B5, R4, R5
    ]
    
    # Pro/Clash pick-ban order (current alternating)
    PRO_BAN_ORDER = [
        ("BLUE", 0), ("RED", 0), ("BLUE", 1), ("RED", 1), ("BLUE", 2),
        ("RED", 2), ("BLUE", 3), ("RED", 3), ("BLUE", 4), ("RED", 4)
    ]
    
    PRO_PICK_ORDER = [
        ("BLUE", 0), ("RED", 0), ("RED", 1), ("BLUE", 1), ("BLUE", 2),
        ("RED", 2), ("RED", 3), ("BLUE", 3), ("BLUE", 4), ("RED", 4)
    ]

    def __init__(self, game_mode: str = "DRAFT"):
        self.game_mode = game_mode
        self.banned_champions: List[str] = []
        self.picked_champions: List[str] = []

    def get_current_action(self, turn: int) -> Tuple[str, int, bool, int]:
        """Returns (side, position, is_ban, action_number) for the current turn."""
        total_actions = 20  # 10 bans + 10 picks
        
        if turn < 10:  # Ban phase
            if self.game_mode in ["DRAFT", "RANKED", "FLEX"]:
                side, position = self.STANDARD_BAN_ORDER[turn]
            else:  # PRO, CLASH, etc.
                side, position = self.PRO_BAN_ORDER[turn]
            is_ban = True
            action_num = turn + 1  # Ban 1-10
        else:  # Pick phase
            pick_turn = turn - 10
            if self.game_mode in ["DRAFT", "RANKED", "FLEX"]:
                side, position = self.STANDARD_PICK_ORDER[pick_turn]
            else:
                side, position = self.PRO_PICK_ORDER[pick_turn]
            is_ban = False
            action_num = pick_turn + 1  # Pick 1-10
        
        return side, position, is_ban, action_num

    def add_ban(self, champion: str) -> bool:
        """Add a champion to the banned list."""
        if champion not in self.banned_champions and champion not in self.picked_champions:
            self.banned_champions.append(champion)
            return True
        return False

    def add_pick(self, champion: str) -> bool:
        """Add a champion to the picked list if not banned."""
        if champion not in self.banned_champions and champion not in self.picked_champions:
            self.picked_champions.append(champion)
            return True
        return False

    def get_available_champions(self, all_champions: List[str]) -> List[str]:
        """Filter out banned and picked champions from the full list."""
        return [champ for champ in all_champions 
                if champ not in self.banned_champions 
                and champ not in self.picked_champions]

    def is_action_valid(self, champion: str, is_ban: bool) -> bool:
        """Validate if an action (pick/ban) is allowed."""
        if is_ban:
            return champion not in self.banned_champions and champion not in self.picked_champions
        else:
            return (champion not in self.banned_champions 
                    and champion not in self.picked_champions)