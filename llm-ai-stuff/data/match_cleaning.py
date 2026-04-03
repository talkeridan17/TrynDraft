import json
import os
import pandas as pd
import pickle

df = pd.DataFrame()

for file in os.listdir("raw/matches/data/raw_soloq"):
    if not file.endswith(".json"):
        continue
    with open(os.path.join("raw/matches/data/raw_soloq", file), "r") as f:
        data = json.load(f)
        df = pd.concat([df, pd.DataFrame([data])])

with open("data/matches_df.pkl", "wb") as f:
    pickle.dump(df, f)

