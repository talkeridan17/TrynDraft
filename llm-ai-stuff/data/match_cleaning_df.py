import pickle
import pandas as pd

with open("data/matches_df.pkl", "rb") as f:
    df = pickle.load(f)

def clean_data(df):
    # Create champion ID to name mapping (common LoL champions)
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
    
    # Create new dataframe for cleaned data
    cleaned_df = pd.DataFrame()
    
    # Copy basic match info
    cleaned_df['match_id'] = df['match_id']
    cleaned_df['patch'] = df['patch']
    cleaned_df['platform'] = df['platform']
    cleaned_df['queue_id'] = df['queue_id']
    cleaned_df['game_duration'] = df['game_duration']
    cleaned_df['blue_win'] = df['blue_win']
    
    # Process bans and translate champion IDs to names
    def process_champion_list(champion_list):
        champion_names = []
        for champ in champion_list:
            champ_id = champ.get('champion_id')
            champ_name = champion_map.get(champ_id, f"Unknown_{champ_id}")
            if champ_name.startswith("Unknown_"):
                print(f"Unknown champion ID: {champ_id}")
            champion_names.append(champ_name)
        return champion_names
    
    # Add champion names for bans and picks
    cleaned_df['blue_bans'] = df['bans'].apply(lambda x: process_champion_list([b for b in x if b['side'] == 0]))
    cleaned_df['red_bans'] = df['bans'].apply(lambda x: process_champion_list([b for b in x if b['side'] == 1]))
    cleaned_df['blue_picks'] = df['picks'].apply(lambda x: process_champion_list([p for p in x if p['side'] == 0]))
    cleaned_df['red_picks'] = df['picks'].apply(lambda x: process_champion_list([p for p in x if p['side'] == 1]))
    
    # Add draft order information
    def get_draft_order(picks):
        draft_order = []
        for pick in sorted(picks, key=lambda x: (x['phase'], x['pick_turn'])):
            champ_id = pick.get('champion_id')
            champ_name = champion_map.get(champ_id, f"Unknown_{champ_id}")
            side = "Blue" if pick['side'] == 0 else "Red"
            draft_order.append(f"{side}_{champ_name}")
        return draft_order
    
    cleaned_df['draft_order'] = df['picks'].apply(get_draft_order)
    
    # Save cleaned dataframe as pickle
    with open("data/cleaned_matches_df.pkl", "wb") as f:
        pickle.dump(cleaned_df, f)
    
    print(f"Cleaned data saved. Shape: {cleaned_df.shape}")
    return cleaned_df

if __name__ == "__main__":
    cleaned = clean_data(df)
    print(cleaned.head())

