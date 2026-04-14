from dataclasses import dataclass
import math
import pathlib
# insert path to data/utiltiy.py
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "data"))
from utility import load_champion_map, unify_champ_names

MIN_GAMES = 3

VALID_ROLES = ["top", "jungle", "middle", "bot", "supporter"]

id_to_name = load_champion_map()

@dataclass
class PlayerProficiency:
    champion_id: int
    champion_name: str
    role: str
    games: int
    win_rate: float
    ai_score: float
    proficiency: float

def _compute_proficiency(games: int, win_rate: float, ai_score: float) -> float:
    games_score = min(math.log1p(games) / math.log1p(50), 1.0)
    wr_score = max(0.0, min((win_rate - 35.0) / 30.0, 1.0))
    ai_score_norm = max(0.0, min(ai_score / 100.0, 1.0))
    
    return round(
        0.50 * ai_score_norm +
        0.30 * wr_score +
        0.20 * games_score,
        4
    )

def build_proficiency_map(
    deeplol_data: dict[str, list[dict]],
    min_games: int = MIN_GAMES
) -> dict[str, list[PlayerProficiency]]:
    result = {}
    
    for role, entries in deeplol_data.items():
        role_norm = role.lower()
        if role_norm not in VALID_ROLES:
            continue
        
        for entry in entries:
            cid = entry.get("champion_id")
            games = entry.get("games")
            win_rate = entry.get("win_rate")
            ai_score = entry.get("ai_score")
            
            if cid is None or games < min_games:
                continue

            prof = PlayerProficiency(
                champion_id=cid,
                champion_name=unify_champ_names(id_to_name.get(cid, "Unknown")),
                role=role_norm,
                games=games,
                win_rate=win_rate,
                ai_score=ai_score,
                proficiency=_compute_proficiency(games, win_rate, ai_score)
            )

            result.setdefault(cid, []).append(prof)
        
    for cid in result:
        result[cid].sort(key=lambda x: x.proficiency, reverse=True)
    
    return result

def get_champion_proficiency(proficiency_map: dict[str, list[PlayerProficiency]], champion_id: int, role: str = None) -> PlayerProficiency:
    entries = proficiency_map.get(champion_id)
    if entries is None:
        return None
    if role is None:
        return entries[0]
    
    role_norm = role.lower()
    for entry in entries:
        if entry.role == role_norm:
            return entry
    return None

def annotate_suggestions(suggestions, proficiency_map: dict[str, list[PlayerProficiency]]):
    for s in suggestions:
        cid = s.get("champion_id")
        role = s.get("role")
        s["proficiency"] = get_champion_proficiency(proficiency_map, cid, role)
    return suggestions
