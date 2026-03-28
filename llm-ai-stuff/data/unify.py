import pandas as pd
import pickle
import json
import os

champion_map = {
        1: "Annie", 2: "Olaf", 3: "Galio", 4: "TwistedFate", 5: "XinZhao",
        6: "Urgot", 7: "LeBlanc", 8: "Vladimir", 9: "Fiddlesticks", 10: "Kayle",
        11: "MasterYi", 12: "Alistar", 13: "Ryze", 14: "Sion", 15: "Sivir",
        16: "Soraka", 17: "Teemo", 18: "Tristana", 19: "Warwick", 20: "Nunu",
        21: "MissFortune", 22: "Ashe", 23: "Tryndamere", 24: "Jax", 25: "Morgana",
        26: "Zilean", 27: "Singed", 28: "Evelynn", 29: "Twitch", 30: "Karthus",
        31: "Chogath", 32: "Amumu", 33: "Rammus", 34: "Anivia", 35: "Shacoking",
        36: "DrMundo", 37: "Sona", 38: "Kassadin", 39: "Irelia", 40: "Janna",
        41: "Gangplank", 42: "Corki", 43: "Karma", 44: "Taric", 45: "Veigar",
        48: "Trundle", 50: "Swain", 51: "Caitlyn", 53: "Blitzcrank", 54: "Malphite",
        55: "Katarina", 56: "Nocturne", 57: "Maokai", 58: "Renekton", 59: "JarvanIV",
        60: "Elise", 61: "Orianna", 62: "Wukong", 63: "Brand", 64: "LeeSin",
        67: "Vayne", 68: "Rumble", 69: "Cassiopeia", 72: "Skarner", 74: "Mordekaiser",
        75: "Nasus", 76: "Nidalee", 77: "Udyr", 78: "Poppy", 79: "Gragas",
        80: "Pantheon", 81: "Ezreal", 82: "Mordekaiser", 83: "Yorick", 84: "Akali",
        85: "Kennen", 86: "Garen", 89: "Leona", 90: "Malzahar", 91: "Talon",
        92: "Riven", 96: "KogMaw", 98: "Shen", 99: "Lux", 101: "Xerath",
        102: "Shyvana", 103: "Ahri", 104: "Graves", 105: "Fizz", 106: "Volibear",
        107: "Rengar", 110: "Zed", 111: "Varus", 112: "Nautilus", 113: "Sejuani",
        114: "Fiora", 115: "Ziggs", 117: "Lulu", 119: "Draven", 120: "Hecarim",
        121: "Khazix", 122: "Darius", 123: "Jayce", 126: "Kled", 127: "Lissandra",
        131: "Diana", 133: "Quinn", 134: "Syndra", 136: "AurelionSol", 141: "Kayn",
        142: "Zoe", 143: "Zyra", 145: "Varus", 147: "Seraphine", 150: "Gnar",
        154: "Zac", 157: "Yasuo", 161: "Velkoz", 163: "Taliyah", 164: "Camille",
        166: "Akshan", 200: "Belveth", 201: "Braum", 202: "Jhin", 203: "Kindred",
        221: "Zeri", 222: "Jinx", 223: "TahmKench", 234: "Viego", 235: "Senna",
        236: "Lucian", 238: "Zoe", 240: "Kaisa", 245: "Ekko", 246: "Qiyana",
        254: "Vi", 266: "Varus", 267: "Nami", 268: "Rell", 350: "Yuumi",
        360: "Samira", 412: "Thresh", 420: "Illaoi", 427: "Aphelios", 429: "Kalista",
        497: "Rakan", 498: "Xayah", 516: "Ornn", 517: "Sylas", 518: "Neeko",
        523: "Aphelios", 526: "Rell", 555: "Pyke", 711: "Vex", 777: "Sett",
        887: "Gwen", 900: "Renata", 902: "Nilah",
        # Additional champions based on unknown IDs found
        233: "Vex", 421: "Milio", 432: "Belveth", 799: "KSante", 800: "Smolder",
        804: "Naafiri", 875: "Hwei", 876: "Ambessa", 888: "Aatrox", 893: "Rell",
        895: "Aurora", 897: "Braum", 901: "Akshan", 904: "Vex", 910: "Renata",
        950: "Nilah", -1: "None"
}

def patch_recency_weight(patch: str, half_life_patches: float = 12.0) -> float:
    """
    Exponential decay by patch distance from the most recent patch.
    Half-life of 12 patches ≈ 6 months (2 patches/month).
    """
    try:
        major, minor = map(int, patch.split(".")[:2])
        patch_idx   = major * 24 + minor
        LATEST_IDX  = 14 * 24 + 24   # patch 14.24 = end of 2024 season
        distance    = max(0, LATEST_IDX - patch_idx)
        return 0.5 ** (distance / half_life_patches)
    except (ValueError, AttributeError):
        return 0.5

class PDUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "pandas.core.arrays.string_arrow" and name == "StringDtype":
            from pandas import StringDtype
            return StringDtype
        if module == "pandas.core.dtypes.dtypes" and name == "StringDtype":
            from pandas import StringDtype
            return StringDtype
        return super().find_class(module, name)

def load_pickle_compat(fp):
    try:
        return pd.read_pickle(fp)
    except Exception:
        with open(fp, "rb") as f:
            return pickle.load(f)

def clean_soloq_matches(match_dir):
    soloq_df = pd.DataFrame()
    for file in os.listdir(match_dir):
        if not file.endswith(".json"):
            continue
        with open(os.path.join(match_dir, file), "r") as f:
            match = json.load(f)
            soloq_df = pd.concat([soloq_df, pd.DataFrame([match])], ignore_index=True)

    with open("data/cleaned_soloq_matches_df.pkl", "wb") as f:
        pickle.dump(soloq_df, f)
    
    return soloq_df

def unify(proplay_fp, soloq_fp):
    try:
        proplay_data = load_pickle_compat(proplay_fp)
        soloq_data = load_pickle_compat(soloq_fp)
    except Exception as e:
        raise ValueError(f"Failed to load pickle files: {e}")
    
    # TODO: This function should return a new dataframe that modifies the soloq_data to match the proplay_data structure
    # For example, adding a 'platform' column to soloq_data

    soloq_data.drop(columns=['queue_id', 'blue_puuids', 'red_puuids'], inplace=True)

    new_df = proplay_data.copy()

    for _, match in soloq_data.iterrows():
        new_df_row = {}
        new_df_row['match_id'] = match['match_id']
        new_df_row['patch'] = match['patch']
        new_df_row['domain'] = 'soloq'
        new_df_row['recency_weight'] = patch_recency_weight(match['patch'])
        new_df_row['game_length_s'] = match['game_duration']
        new_df_row['blue_win'] = match['blue_win']
        new_df_row['bans'] = match['bans']
        new_df_row['picks'] = match['picks'] # Assume pick and bans are in order in array
        for ban in new_df_row['bans']:
            ban['side'] = 0 if ban['side'] == 'blue' else 1
            ban['champion_name'] = champion_map[ban['champion_id']]
        for pick in new_df_row['picks']:
            pick['side'] = 0 if pick['side'] == 'blue' else 1
            pick['champion_name'] = champion_map[pick['champion_id']]
        
        new_df = pd.concat([new_df, pd.DataFrame([new_df_row])], ignore_index=True)
    
    with open("data/unified_data.pkl", "wb") as f:
        pickle.dump(new_df, f)
    
    return new_df

if __name__ == "__main__":
    proplay_fp = "data/proplay_cleaned.pkl"
    soloq_fp = "data/cleaned_soloq_matches_df.pkl"
    
    proplay_data = load_pickle_compat(proplay_fp)
    soloq_data = load_pickle_compat(soloq_fp)

    # unified = unify(proplay_fp, soloq_fp)
    
    unified = None
    with open("data/unified_data.pkl", "rb") as f:
        unified = pickle.load(f)
    
    
    # For every pro play match, (domain=0), update every pick and ban dictionary to include phase and pick_turn
    for _, match in unified[unified['domain'] == 0].iterrows():
        i = 0
        for ban in match['bans']:
            ban['phase'] = 2 if i > 5 else 1
            ban['pick_turn'] = i
            i += 1
        i = 0
        for pick in match['picks']:
            pick['phase'] = 2 if i > 5 else 1
            pick['pick_turn'] = i
            i += 1
    
    with open("data/unified_data.pkl", "wb") as f:
        pickle.dump(unified, f)
    
    print(unified[unified['domain'] == 0]['picks'].iloc[0])