from dataclasses import dataclass, asdict
from proficiency import PlayerProficiency


# Top N tags to surface per champion — keep it short for the LLM prompt
MAX_TAGS = 3

TAG_DISPLAY = {
    "ally_heal":          "ally healing",
    "aoe":                "area of effect damage",
    "burst_tool":         "burst damage",
    "cc_hard":            "hard crowd control",
    "cc_soft":            "soft crowd control",
    "engage":             "engage",
    "peel":               "peel for carries",
    "waveclear":          "wave clear",
    "mobility":           "mobility",
    "shield":             "shielding",
    "sustain":            "sustain",
    "tank":               "tankiness",
    "true_damage":        "true damage",
    "physical_damage":    "physical damage",
    "magic_damage":       "magic damage",
    "execute":            "execute damage",
    "stealth":            "stealth",
    "global":             "global presence",
    "split_push":         "split push threat",
    "teamfight":          "teamfight presence",
}

def _prettify_tags(tags: list[str]) -> list[str]:
    return [TAG_DISPLAY.get(tag, tag.replace("_", " ")) for tag in tags]

@dataclass
class SuggestionContext:
    """
    Structured context for one suggestion, ready to serialize to JSON
    and pass to the browser explainability LLM.
    """
    champion_id:        int
    champion_name:      str
    rank:               int       # 1, 2, or 3
    probability:        float
    damage_profile:     str       # e.g. "primarily magic (94%)"
    top_tags:           list[str]
    proficiency:        dict | None   # serialized ChampionProficiency or None
    draft_position:     str       # e.g. "Blue side ban 4, phase 1"
    allied_picks:       list[str]
    enemy_picks:        list[str]
    bans:               list[str]
    is_pick:            bool


def _damage_profile_str(damage_matrix_row: list[float]) -> str:
    """
    Convert [ad_pct, ap_pct, true_pct] into a readable string.
    damage_matrix_row values are in [0, 1].
    """
    ad, ap, tr = damage_matrix_row
    parts = []
    if ap  > 0.5:  parts.append(f"primarily magic ({ap*100:.0f}%)")
    elif ad > 0.5: parts.append(f"primarily physical ({ad*100:.0f}%)")
    else:          parts.append("mixed damage")
    if tr  > 0.15: parts.append(f"true damage ({tr*100:.0f}%)")
    return ", ".join(parts) if parts else "mixed damage"


def _proficiency_str(prof: PlayerProficiency | None) -> str:
    """Human-readable proficiency summary for the LLM prompt."""
    if prof is None:
        return "no data available"
    games_str = f"{prof.games} game{'s' if prof.games != 1 else ''}"
    return (
        f"{games_str} played, {prof.win_rate:.1f}% winrate, "
        f"AI score {prof.ai_score:.1f}/100 "
        f"(proficiency {prof.proficiency:.2f}/1.0)"
    )


def _draft_position_str(slot: int, is_pick: bool, domain: int) -> str:
    """
    Convert a slot index into a readable draft position description.
    Pro sequence: 6 bans, 6 picks, 4 bans, 4 picks
    Soloq sequence: 10 bans, 10 picks
    """
    from train import DOMAIN_PRO, PRO_SEQUENCE, SOLOQ_SEQUENCE

    sequence = PRO_SEQUENCE if domain == DOMAIN_PRO else SOLOQ_SEQUENCE
    side, phase, event_type = sequence[slot]
    side_str  = "Blue" if side == 0 else "Red"
    event_str = "pick" if is_pick else "ban"
    return f"{side_str} side {event_str} {slot + 1}, phase {phase}"


def build_suggestion_contexts(
    result:          dict,
    events:          list[dict],
    domain:          int,
    id_to_name:      dict[int, str],
    tag_matrix:      "torch.Tensor",
    damage_matrix:   "torch.Tensor",
    valid_tags:      list[str],
    proficiency_map: dict | None = None,
) -> list[SuggestionContext]:
    """
    Builds one SuggestionContext per suggestion in result["suggestions"].

    Args:
        result:          output from predict_named()
        events:          the partial draft events passed to predict()
        domain:          DOMAIN_PRO or DOMAIN_SOLOQ
        id_to_name:      {champion_id: name}
        tag_matrix:      [CHAMPION_VOCAB, num_tags] FloatTensor
        damage_matrix:   [CHAMPION_VOCAB, 3] FloatTensor
        valid_tags:      list of tag strings in column order
        proficiency_map: output of build_proficiency_map(), or None
    """
    from proficiency import get_champion_proficiency
    from train import DOMAIN_PRO, PRO_SEQUENCE, SOLOQ_SEQUENCE

    sequence = PRO_SEQUENCE if domain == DOMAIN_PRO else SOLOQ_SEQUENCE
    target_slot = result["target_slot"]
    is_pick     = result["is_pick"]

    # Build readable pick/ban lists from known events
    allied_picks = []
    enemy_picks  = []
    bans         = []

    for i, ev in enumerate(events):
        cid  = ev.get("champion_id", 0)
        name = id_to_name.get(cid, f"Champion({cid})")
        _, _, event_type = sequence[i]
        side = sequence[i][0]

        if event_type == 0:   # ban
            bans.append(name)
        else:                  # pick
            if side == 0:
                allied_picks.append(name)
            else:
                enemy_picks.append(name)

    contexts = []
    for rank, s in enumerate(result["suggestions"], start=1):
        cid  = s["champion_id"]
        name = s["champion_name"]

        # Damage profile
        dmg_row = damage_matrix[cid].tolist()
        dmg_str = _damage_profile_str(dmg_row)

        # Top tags — pick the N most distinctive ones for this champion
        tag_row  = tag_matrix[cid]
        top_idxs = tag_row.nonzero(as_tuple=True)[0].tolist()[:MAX_TAGS]
        top_tags = _prettify_tags([valid_tags[i] for i in top_idxs])

        # Proficiency
        prof = get_champion_proficiency(proficiency_map, cid) \
               if proficiency_map else None
        prof_dict = asdict(prof) if prof else None

        contexts.append(SuggestionContext(
            champion_id=cid,
            champion_name=name,
            rank=rank,
            probability=s["probability"],
            damage_profile=dmg_str,
            top_tags=top_tags,
            proficiency=prof_dict,
            draft_position=_draft_position_str(target_slot, is_pick, domain),
            allied_picks=allied_picks,
            enemy_picks=enemy_picks,
            bans=bans,
            is_pick=is_pick,
        ))

    return contexts


def contexts_to_json(contexts: list[SuggestionContext]) -> list[dict]:
    """Serialize contexts to plain dicts for JSON transport to the browser."""
    return [asdict(c) for c in contexts]

