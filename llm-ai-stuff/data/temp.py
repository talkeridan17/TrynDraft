import pickle
import pandas as pd
from ast import literal_eval
from utility import reverse_champion_map, load_champion_map, unify_champ_names

inv_map = reverse_champion_map()

def fix_tags():
    with open("data/annotated_abilities_df.pkl", "rb") as f:
        df = pickle.load(f)


    # Check that all champion names are in the inv_map
    missing = []
    for _, row in df.iterrows():
        if row["champion"] not in inv_map:
            missing.append(row["champion"])

    # For each champion, rename them using the inv_map
    for champion in missing:
        # Rename the champion using unify_champ_names
        unified = unify_champ_names(champion)
        if unified in inv_map:
            print(f"Champion {champion} unified to {unified}")
            df.loc[df["champion"] == champion, "champion"] = unified
        else:
            print(f"Champion {champion} could not be unified")

    # Check that all champion ids are correct and match up with the champion names
    incorrect_or_na_ids = []
    for _, row in df.iterrows():
        if pd.isna(row["champion_id"]):
            print(f"Champion {row['champion']} has no id")
            incorrect_or_na_ids.append(row["champion"])
            continue
        if row["champion_id"] != inv_map[row["champion"]]:
            print(f"Champion {row['champion']} has id {row['champion_id']} but should have {inv_map[row['champion']]}")
            incorrect_or_na_ids.append(row["champion"])

    # Fix champion id for each champion in incorrect_or_na_ids
    for champion in incorrect_or_na_ids:
        df.loc[df["champion"] == champion, "champion_id"] = inv_map[champion]

    # Save df to pickle
    with open("data/annotated_abilities_df.pkl", "wb") as f:
        pickle.dump(df, f)

def fix_dmg():
    with open("data/champion_damage_breakdown.pkl", "rb") as f:
        df = pickle.load(f)
    # Fix champion names to match the inv_map
    incorrect_names = []
    for _, row in df.iterrows():
        if row["champion_name"] not in inv_map:
            incorrect_names.append(row["champion_name"])

    for name in incorrect_names:
        # Rename the champion using unify_champ_names
        unified = unify_champ_names(name)
        if unified in inv_map:
            print(f"Champion {name} unified to {unified}")
            df.loc[df["champion_name"] == name, "champion_name"] = unified
        else:
            print(f"Champion {name} could not be unified")
    
    ids_to_fix = []
    for _, row in df.iterrows():
        if row["champion_id"] != inv_map[row["champion_name"]]:
            ids_to_fix.append(row["champion_name"])
    
    print(f"Found {len(ids_to_fix)} champions with incorrect ids")
    for champion in ids_to_fix:
        df.loc[df["champion_name"] == champion, "champion_id"] = inv_map[champion]

    # Save df to pickle
    with open("data/champion_damage_breakdown.pkl", "wb") as f:
        pickle.dump(df, f)

if __name__ == "__main__":
    with open("data/champion_damage_breakdown.pkl", "rb") as f:
        df = pickle.load(f)
    
    # Add columns for ad_pct, ap_pct, true_pct
    df["ad_pct"] = df["avg_attack_damage"] / (df["avg_attack_damage"] + df["avg_ap_damage"] + df["avg_true_damage"])
    df["ap_pct"] = df["avg_ap_damage"] / (df["avg_attack_damage"] + df["avg_ap_damage"] + df["avg_true_damage"])
    df["true_pct"] = df["avg_true_damage"] / (df["avg_attack_damage"] + df["avg_ap_damage"] + df["avg_true_damage"])
    
    # Save df to pickle
    with open("data/champion_damage_breakdown.pkl", "wb") as f:
        pickle.dump(df, f)
