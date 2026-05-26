import pandas as pd
import pickle
import json
import os
from utility import unify_champ_names, load_champion_map

champion_map = load_champion_map()


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
    # proplay_fp = "data/proplay_cleaned.pkl"
    # soloq_fp = "data/cleaned_soloq_matches_df.pkl"
    
    # proplay_data = load_pickle_compat(proplay_fp)
    # soloq_data = load_pickle_compat(soloq_fp)

    # unified = unify(proplay_fp, soloq_fp)
    
    unified = None
    with open("data/unified_data.pkl", "rb") as f:
        unified = pickle.load(f)

    # Rename soloq domain to 1
    
    
    # For every pro play match, (domain=0), update every pick and ban dictionary to include phase and pick_turn
    # for _, match in unified[unified['domain'] == 0].iterrows():
    #     i = 0
    #     for ban in match['bans']:
    #         ban['phase'] = 2 if i > 5 else 1
    #         ban['pick_turn'] = i
    #         i += 1
    #     i = 0
    #     for pick in match['picks']:
    #         pick['phase'] = 2 if i > 5 else 1
    #         pick['pick_turn'] = i
    #         i += 1
    
    # with open("data/unified_data.pkl", "wb") as f:
    #     pickle.dump(unified, f)
    
    # Count unique champions
    champions = set()
    for _, match in unified.iterrows():
        for pick in match['picks']:
            champions.add(pick['champion_name'])
    
    print(len(champions))

    