import pandas as pd
import numpy as np
import pickle
import os

with open(os.path.join(os.path.dirname(__file__), "../data/annotated_abilities_df.pkl"), "rb") as f:
    champions = pickle.load(f)

print(champions.head())

