"""
Leaguepedia Pro Draft Scraper
==============================
Scrapes standard-draft pro games (2020-2024) from Leaguepedia's Cargo API,
excluding fearless tournaments (LDL 2022+, LPL Summer 2024+).

Setup:
    1. Create a bot password at https://lol.fandom.com/wiki/Special:BotPasswords
       (grant Basic rights only)
    2. Copy .env.example to .env and fill in your credentials

Commands:
    python leaguepedia.py scrape  --output data/pro/raw
    python leaguepedia.py resolve --input data/pro/raw
                                  --ddragon data/ddragon
                                  --output data/pro/processed
"""

import argparse
import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

API_URL         = "https://lol.fandom.com/api.php"
MAX_RETRIES     = 10
BACKOFF_BASE    = 2.0   # seconds, doubles each retry
BACKOFF_CAP     = 60.0  # max sleep per retry
REQUEST_GAP     = 1.0   # min seconds between requests when logged in

# (tournament substring, exclude from this date onward)
FEARLESS_RULES = [
    ("LDL", "2022-01-01"),
    ("LPL", "2024-06-01"),
]

# Blue=0, Red=1 | (side, phase)
PICK_ORDER = [
    (0, 1), (1, 1), (1, 1), (0, 1), (0, 1), (1, 1),
    (1, 2), (0, 2), (0, 2), (1, 2),
]

BAN_ORDER = [
    (0, 1), (0, 1), (1, 1), (1, 1), (0, 1), (1, 1),
    (0, 2), (1, 2), (0, 2), (1, 2),
]

ROLE_MAP = {
    "Top":     "TOP",
    "Jungle":  "JUNGLE",
    "Mid":     "MIDDLE",
    "Bot":     "BOTTOM",
    "Support": "UTILITY",
}

YEAR_WEIGHTS = {2020: 0.52, 2021: 0.61, 2022: 0.72, 2023: 0.85, 2024: 1.00}

# Known display name mismatches between Leaguepedia and Data Dragon
CHAMPION_QUIRKS = {
    "Nunu & Willump": "Nunu",
    "Renata Glasc":   "Renata",
    "Wukong":         "MonkeyKing",
    "Dr. Mundo":      "DrMundo",
    "Cho'Gath":       "Chogath",
    "Kai'Sa":         "Kaisa",
    "Kha'Zix":        "Khazix",
    "LeBlanc":        "Leblanc",
    "Vel'Koz":        "Velkoz",
    "Kog'Maw":        "KogMaw",
    "Rek'Sai":        "RekSai",
    "Bel'Veth":       "Belveth",
}


# ── Data class ─────────────────────────────────────────────────────────────────

@dataclass
class DraftRecord:
    match_id:        str
    tournament:      str
    patch:           str
    date:            str
    year:            int
    blue_team:       str
    red_team:        str
    blue_win:        bool
    game_length_s:   int
    recency_weight:  float
    bans:            list   # [{champion_name, champion_id, side, phase, pick_turn}]
    picks:           list   # [{champion_name, champion_id, side, phase, pick_turn, lane}]


# ── API client ─────────────────────────────────────────────────────────────────

class LeaguepediaClient:
    """
    Authenticated MediaWiki Cargo client.
    Login persists via a requests.Session cookie — all requests
    after login automatically carry the auth token.
    """

    def __init__(self):
        self._session  = requests.Session()
        self._session.headers.update({"Accept-Encoding": "gzip"})
        self._last_req = 0.0

    # ── Auth ───────────────────────────────────────────────────────────────────

    def login(self, username: str, password: str):
        """
        Two-step MediaWiki bot login.
        Step 1: fetch a login token.
        Step 2: POST credentials + token.
        Uses action=login which is correct for bot passwords from Special:BotPasswords.
        """
        log.info(f"Logging in as '{username}'...")

        # Step 1 — get login token
        r = self._session.get(
            API_URL,
            params={"action": "query", "meta": "tokens", "type": "login", "format": "json"},
            timeout=15,
        )
        r.raise_for_status()
        token = r.json()["query"]["tokens"]["logintoken"]

        # Step 2 — post credentials
        r = self._session.post(
            API_URL,
            data={"action": "login", "lgname": username, "lgpassword": password,
                  "lgtoken": token, "format": "json"},
            timeout=15,
        )
        r.raise_for_status()
        result = r.json().get("login", {})

        if result.get("result") != "Success":
            raise RuntimeError(
                f"Login failed: {result.get('reason', result)}\n"
                "Username must be 'YourName@botname' (from Special:BotPasswords)."
            )

        log.info("Login successful.")
        self._log_rights()

    def _log_rights(self):
        r = self._session.get(
            API_URL,
            params={"action": "query", "meta": "userinfo",
                    "uiprop": "rights", "format": "json"},
            timeout=15,
        )
        info   = r.json().get("query", {}).get("userinfo", {})
        rights = info.get("rights", [])
        name   = info.get("name", "unknown")
        relevant = [r for r in rights if "rate" in r or "bot" in r]
        log.info(f"Logged in as: {name} | Relevant rights: {relevant}")
        if "noratelimit" not in rights:
            log.warning(
                "No 'noratelimit' right — you have elevated but not unlimited rate limits. "
                "Request bot flag from Leaguepedia admins for large scrapes."
            )

    # ── Requests ───────────────────────────────────────────────────────────────

    def _get(self, params: dict) -> dict:
        """Single GET with exponential backoff retry."""
        for attempt in range(MAX_RETRIES):
            # Enforce minimum gap between requests
            gap = REQUEST_GAP - (time.monotonic() - self._last_req)
            if gap > 0:
                time.sleep(gap)
            self._last_req = time.monotonic()

            try:
                r = self._session.get(API_URL, params=params, timeout=20)
            except requests.ConnectionError as e:
                wait = min(BACKOFF_BASE ** attempt, BACKOFF_CAP)
                log.warning(f"Connection error (attempt {attempt+1}): {e}. Retrying in {wait:.0f}s")
                time.sleep(wait)
                continue
            except requests.Timeout:
                wait = min(BACKOFF_BASE ** attempt, BACKOFF_CAP)
                log.warning(f"Timeout (attempt {attempt+1}). Retrying in {wait:.0f}s")
                time.sleep(wait)
                continue

            if r.status_code == 200:
                data = r.json()
                # MediaWiki returns rate limit errors as 200 with an error key
                if "error" in data:
                    code = data["error"].get("code", "")
                    if code == "ratelimited":
                        wait = min(BACKOFF_BASE ** attempt, BACKOFF_CAP)
                        log.warning(f"Rate limited (attempt {attempt+1}). Sleeping {wait:.0f}s")
                        time.sleep(wait)
                        continue
                    raise RuntimeError(f"API error: {data['error']}")
                return data

            elif r.status_code == 429:
                wait = float(r.headers.get("Retry-After", min(BACKOFF_BASE ** attempt, BACKOFF_CAP)))
                log.warning(f"HTTP 429 (attempt {attempt+1}). Sleeping {wait:.0f}s")
                time.sleep(wait)

            elif r.status_code in (500, 502, 503, 504):
                wait = min(BACKOFF_BASE ** attempt, BACKOFF_CAP)
                log.warning(f"HTTP {r.status_code} (attempt {attempt+1}). Retrying in {wait:.0f}s")
                time.sleep(wait)

            else:
                r.raise_for_status()

        raise RuntimeError(f"Exhausted {MAX_RETRIES} retries")

    # ── Cargo ──────────────────────────────────────────────────────────────────

    def cargo(self, params: dict, page_size: int = 500) -> list:
        """Paginate through all results for a Cargo query."""
        results, offset = [], 0
        while True:
            data = self._get({"action": "cargoquery", "format": "json",
                              "limit": page_size, "offset": offset, **params})
            page = [row["title"] for row in data.get("cargoquery", [])]
            results.extend(page)
            log.info(f"  {len(results)} rows fetched...")
            if len(page) < page_size:
                break
            offset += page_size
        return results


# ── Scraper ────────────────────────────────────────────────────────────────────

def scrape(output_dir: str):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    username = os.getenv("LEAGUEPEDIA_USERNAME")
    password = os.getenv("LEAGUEPEDIA_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            "LEAGUEPEDIA_USERNAME and LEAGUEPEDIA_PASSWORD must be set in your .env file."
        )

    client = LeaguepediaClient()
    client.login(username, password)

    # ── Fetch game metadata ────────────────────────────────────────────────────
    log.info("Fetching ScoreboardGames...")
    games = client.cargo({
        "tables":  "ScoreboardGames=SG, Tournaments=T",
        "join_on": "SG.OverviewPage=T.OverviewPage",
        "fields":  ("SG.GameId, T.StandardName=Tournament, T.Region, "
                    "SG.DateTime_UTC=DateTime_UTC, SG.Patch, "
                    "SG.Team1, SG.Team2, SG.WinTeam, "
                    "SG.Gamelength_Number, SG.Team1Kills, SG.Team2Kills"),
        "where":   ("SG.DateTime_UTC >= '2020-01-01 00:00:00' "
                    "AND SG.DateTime_UTC < '2025-01-01 00:00:00' "
                    "AND SG.Patch IS NOT NULL "
                    "AND SG.WinTeam IS NOT NULL AND SG.WinTeam != ''"),
        "order_by": "SG.DateTime_UTC ASC",
    })
    log.info(f"ScoreboardGames: {len(games)} rows")

    # ── Fetch picks and bans ───────────────────────────────────────────────────
    log.info("Fetching PicksAndBansS7...")
    pb_rows = client.cargo({
        "tables": "PicksAndBansS7",
        "fields": ("GameId, "
                   "Team1Ban1, Team1Ban2, Team1Ban3, Team1Ban4, Team1Ban5, "
                   "Team2Ban1, Team2Ban2, Team2Ban3, Team2Ban4, Team2Ban5, "
                   "Team1Pick1, Team1Pick2, Team1Pick3, Team1Pick4, Team1Pick5, "
                   "Team2Pick1, Team2Pick2, Team2Pick3, Team2Pick4, Team2Pick5, "
                   "Team1Role1, Team1Role2, Team1Role3, Team1Role4, Team1Role5, "
                   "Team2Role1, Team2Role2, Team2Role3, Team2Role4, Team2Role5"),
        "where":   "GameId IS NOT NULL",
        "order_by": "GameId ASC",
    })
    pb = {row["GameId"]: row for row in pb_rows if row.get("GameId")}
    log.info(f"PicksAndBansS7: {len(pb)} rows")

    # ── Parse and write ────────────────────────────────────────────────────────
    written = skipped_fearless = skipped_incomplete = 0

    for g in games:
        game_id    = g.get("GameId", "")
        tournament = g.get("Tournament", "")
        date       = (g.get("DateTime UTC") or "")[:10]
        year       = int(date[:4]) if len(date) >= 4 else 0

        if _is_fearless(tournament, date):
            skipped_fearless += 1
            continue

        if game_id not in pb:
            skipped_incomplete += 1
            continue

        record = _parse(g, pb[game_id], game_id, tournament, date, year)
        if record is None:
            skipped_incomplete += 1
            continue

        file_path = out / f"{game_id}.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(asdict(record), indent=2))
        written += 1

    log.info(f"Done — written: {written} | fearless: {skipped_fearless} | incomplete: {skipped_incomplete}")


def _is_fearless(tournament: str, date: str) -> bool:
    for substring, cutoff in FEARLESS_RULES:
        if substring.lower() in tournament.lower() and date >= cutoff:
            return True
    return False


def _parse(g: dict, pb: dict, game_id: str, tournament: str,
           date: str, year: int) -> Optional[DraftRecord]:

    blue_team = g.get("Team1", "")
    red_team  = g.get("Team2", "")
    blue_win  = g.get("WinTeam", "") == blue_team

    try:
        game_length_s = int(float(g.get("Gamelength Number") or 0) * 60)
    except (ValueError, TypeError):
        return None

    if game_length_s < 15 * 60:
        return None

    blue_roles = [ROLE_MAP.get(pb.get(f"Team1Role{i}", ""), "UNKNOWN") for i in range(1, 6)]
    red_roles  = [ROLE_MAP.get(pb.get(f"Team2Role{i}", ""), "UNKNOWN") for i in range(1, 6)]

    # Bans
    bans = []
    blue_ban_iter = iter(pb.get(f"Team1Ban{i}", "") for i in range(1, 6))
    red_ban_iter  = iter(pb.get(f"Team2Ban{i}", "") for i in range(1, 6))
    for turn, (side, phase) in enumerate(BAN_ORDER):
        name = next(blue_ban_iter) if side == 0 else next(red_ban_iter)
        bans.append({"champion_name": name or "None", "champion_id": None,
                     "side": side, "phase": phase, "pick_turn": turn})

    # Picks
    picks = []
    blue_pick_iter = iter(zip((pb.get(f"Team1Pick{i}", "") for i in range(1, 6)), blue_roles))
    red_pick_iter  = iter(zip((pb.get(f"Team2Pick{i}", "") for i in range(1, 6)), red_roles))
    for turn, (side, phase) in enumerate(PICK_ORDER):
        name, lane = next(blue_pick_iter) if side == 0 else next(red_pick_iter)
        if not name:
            return None
        picks.append({"champion_name": name, "champion_id": None,
                      "side": side, "phase": phase, "pick_turn": turn, "lane": lane})

    return DraftRecord(
        match_id=game_id,
        tournament=tournament,
        patch=(g.get("Patch") or "").strip(),
        date=date,
        year=year,
        blue_team=blue_team,
        red_team=red_team,
        blue_win=blue_win,
        game_length_s=game_length_s,
        recency_weight=YEAR_WEIGHTS.get(year, 0.5),
        bans=bans,
        picks=picks,
    )


# ── Champion name resolver ─────────────────────────────────────────────────────

def resolve(input_dir: str, ddragon_dir: str, output_dir: str):
    """Resolve champion_name strings → integer champion_id using Data Dragon."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    name_to_id = _build_name_map(ddragon_dir)
    unknown    = set()
    resolved   = 0

    for path in sorted(Path(input_dir).rglob("*.json")):
        record = json.loads(path.read_text())
        ok     = True

        for entry in record["bans"]:
            name = entry["champion_name"]
            if name in ("None", "", "No Ban"):
                entry["champion_id"] = -1
            else:
                cid = name_to_id.get(name)
                if cid is None:
                    unknown.add(name)
                    ok = False
                    break
                entry["champion_id"] = cid

        if not ok:
            continue

        for entry in record["picks"]:
            name = entry["champion_name"]
            cid  = name_to_id.get(name)
            if cid is None:
                unknown.add(name)
                ok = False
                break
            entry["champion_id"] = cid

        if ok:
            (out / path.name).write_text(json.dumps(record, indent=2))
            resolved += 1

    if unknown:
        log.warning(f"Unresolved names — add to CHAMPION_QUIRKS: {sorted(unknown)}")
    log.info(f"Resolved {resolved} records → {output_dir}")


def _build_name_map(ddragon_dir: str) -> dict:
    name_to_id = {}
    for path in sorted(Path(ddragon_dir).glob("*.json")):
        for key, champ in json.loads(path.read_text()).get("data", {}).items():
            iid = int(champ["key"])
            name_to_id[champ["name"]] = iid  # display name  e.g. "Cho'Gath"
            name_to_id[key]           = iid  # internal key  e.g. "Chogath"
    for lp_name, dd_key in CHAMPION_QUIRKS.items():
        if dd_key in name_to_id:
            name_to_id[lp_name] = name_to_id[dd_key]
    return name_to_id


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub    = parser.add_subparsers(dest="cmd")

    p_scrape = sub.add_parser("scrape", help="Pull raw pro drafts from Leaguepedia")
    p_scrape.add_argument("--output", default="data/pro/raw")

    p_resolve = sub.add_parser("resolve", help="Resolve champion names to IDs via Data Dragon")
    p_resolve.add_argument("--input",   default="data/pro/raw")
    p_resolve.add_argument("--ddragon", default="data/ddragon")
    p_resolve.add_argument("--output",  default="data/pro/processed")

    args = parser.parse_args()

    if args.cmd == "scrape":
        scrape(args.output)
    elif args.cmd == "resolve":
        resolve(args.input, args.ddragon, args.output)
    else:
        parser.print_help()