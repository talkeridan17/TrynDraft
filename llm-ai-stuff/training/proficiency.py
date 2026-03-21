# proficiency.py

from dataclasses import dataclass
from opgg.opgg import OPGG
from opgg.params import Region


REGION_MAP = {
    "na":   Region.NA,
    "euw":  Region.EUW,
    "kr":   Region.KR,
    "eune": Region.EUNE,
    "jp":   Region.JP,
    "br":   Region.BR,
    "oce":  Region.OCE,
    "las":  Region.LAS,
    "lan":  Region.LAN,
    "ru":   Region.RU,
    "tr":   Region.TR,
}


@dataclass
class ChampionProficiency:
    champion_id:   int
    champion_name: str
    games:         int
    wins:          int
    losses:        int
    winrate:       float   # 0.0 - 1.0
    kda:           float
    avg_op_score:  float
    proficiency:   float   # composite score 0.0 - 1.0


def _compute_kda(kills: int, deaths: int, assists: int, games: int) -> float:
    """Average KDA across all games on this champion."""
    if games == 0:
        return 0.0
    avg_k = kills   / games
    avg_d = deaths  / games
    avg_a = assists / games
    return round((avg_k + avg_a) / max(avg_d, 1.0), 2)


def _compute_proficiency(games: int, winrate: float, avg_op_score: float) -> float:
    """
    Composite proficiency score in [0, 1].

    Three signals combined:
      - games played:   log-scaled so 100 games ≈ 0.5, 500 games ≈ 0.85
      - winrate:        normalized from [0.4, 0.65] typical range to [0, 1]
      - avg op_score:   OP.GG scores typically range 40-80, normalize to [0, 1]

    Weighted sum: games 40%, winrate 35%, op_score 25%.
    Games is weighted highest because consistency matters more than a few
    high-winrate games on a champion the player rarely plays.
    """
    import math

    games_score    = min(math.log1p(games) / math.log1p(500), 1.0)
    winrate_score  = max(0.0, min((winrate - 0.40) / 0.25, 1.0))
    op_score_norm  = max(0.0, min((avg_op_score - 40.0) / 40.0, 1.0))

    return round(
        0.35 * games_score +
        0.30 * winrate_score +
        0.35 * op_score_norm,
        4,
    )


def fetch_proficiency(
    game_name:  str,
    tag:        str,
    region:     str = "na",
    id_to_name: dict = None,
    min_games:  int = 5,
) -> dict[int, ChampionProficiency]:
    """
    Fetches per-champion proficiency for a player from OP.GG.

    Args:
        game_name:  Riot ID game name  e.g. "Faker"
        tag:        Riot ID tag        e.g. "KR1"
        region:     region string      e.g. "kr", "na", "euw"
        id_to_name: {champion_id: champion_name} lookup — from your damage_df
        min_games:  minimum games played to include a champion

    Returns:
        dict mapping champion_id → ChampionProficiency
        Only includes champions with at least min_games played.
    """
    opgg_region = REGION_MAP.get(region.lower())
    if opgg_region is None:
        raise ValueError(f"Unknown region '{region}'. Valid: {list(REGION_MAP.keys())}")

    opgg    = OPGG()
    results = opgg.search(f"{game_name}#{tag}", opgg_region)

    if not results:
        raise ValueError(f"No summoner found for {game_name}#{tag} in {region}")

    summoner   = results[0].summoner
    champ_stats = summoner.most_champions.champion_stats

    proficiencies = {}

    for cs in champ_stats:
        if cs.id is None or cs.play is None:
            continue
        if cs.play < min_games:
            continue

        games    = cs.play
        wins     = cs.win   or 0
        losses   = cs.lose  or 0
        winrate  = wins / games if games > 0 else 0.0

        kda      = _compute_kda(
            cs.kill   or 0,
            cs.death  or 0,
            cs.assist or 0,
            games,
        )

        avg_op   = (cs.op_score / games) if cs.op_score else 0.0
        prof     = _compute_proficiency(games, winrate, avg_op)

        name     = (id_to_name or {}).get(cs.id, f"Champion({cs.id})")

        proficiencies[cs.id] = ChampionProficiency(
            champion_id=cs.id,
            champion_name=name,
            games=games,
            wins=wins,
            losses=losses,
            winrate=round(winrate, 4),
            kda=kda,
            avg_op_score=round(avg_op, 2),
            proficiency=prof,
        )

    return proficiencies