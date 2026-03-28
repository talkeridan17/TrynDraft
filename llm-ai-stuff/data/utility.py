import pickle

def load_champion_map():
    with open("data/champion_map.pkl", "rb") as f:
        return pickle.load(f)

def reverse_champion_map():
    return {v: k for k, v in load_champion_map().items()}
