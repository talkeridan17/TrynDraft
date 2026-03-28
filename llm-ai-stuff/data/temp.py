import pickle
import pandas as pd
from ast import literal_eval
from utility import reverse_champion_map

inv_map = reverse_champion_map()

with open("data/annotated_abilities_df.pkl", "rb") as f:
    df = pickle.load(f)

# Add champion ids as integer column
df["champion_id"] = df["champion"].map(inv_map).astype('Int64')

# Look for any NaN values in champion_id, print the list of champions that are missing
print("Champions missing from champion map:", df[df["champion_id"].isna()]["champion"].unique())
