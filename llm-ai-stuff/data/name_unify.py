import pandas as pd
import pickle
import os
from utility import load_champion_map, reverse_champion_map

# Define the 3 data input files
data_inputs = [
    "data/annotated_abilities_df.pkl",
    "data/champion_damage_breakdown.pkl",
    "data/unified_data.pkl"
]

def create_name_unifier():
    """
    Create a mapping from variant champion names to canonical names.
    Based on analysis of missing champions in the data files.
    """
    champion_map = load_champion_map()
    canonical_names = set(champion_map.values())
    
    # Mapping from variant names to canonical names
    name_mappings = {
        # Case variations
        "Leblanc": "LeBlanc",
        "LeeSin": "LeeSin",  # Already correct
        "MasterYi": "MasterYi",  # Already correct
        "MissFortune": "MissFortune",  # Already correct
        "Khazix": "Khazix",  # Already correct
        "KogMaw": "KogMaw",  # Already correct
        "TwistedFate": "TwistedFate",  # Already correct
        "JarvanIV": "JarvanIV",  # Already correct
        "XinZhao": "XinZhao",  # Already correct
        "TahmKench": "TahmKench",  # Already correct
        "Velkoz": "Velkoz",  # Already correct
        "DrMundo": "DrMundo",  # Already correct
        "Chogath": "Chogath",  # Already correct
        "Kaisa": "Kaisa",  # Already correct
        "Renata": "Renata",  # Already correct
        "KSante": "KSante",  # Already correct
        "Belveth": "Belveth",  # Already correct
        "AurelionSol": "AurelionSol",  # Already correct
        
        # Common API/data variations
        "MonkeyKing": "Wukong",
        "Nunu": "Nunu",  # May need to map to "NunuWillump" in some cases
        "RekSai": "RekSai",  # Already correct, but sometimes "Rek'Sai"
        
        # Space variations (API often returns names with spaces)
        "Aurelion Sol": "AurelionSol",
        "Bel'Veth": "Belveth",
        "Cho'Gath": "Chogath",
        "Dr. Mundo": "DrMundo",
        "Jarvan IV": "JarvanIV",
        "Kai'Sa": "Kaisa",
        "Kha'Zix": "Khazix",
        "Kog'Maw": "KogMaw",
        "K'Sante": "KSante",
        "LeBlanc": "LeBlanc",
        "Lee Sin": "LeeSin",
        "Master Yi": "MasterYi",
        "Miss Fortune": "MissFortune",
        "Nunu & Willump": "Nunu",
        "Rek'Sai": "RekSai",
        "Renata Glasc": "Renata",
        "Tahm Kench": "TahmKench",
        "Twisted Fate": "TwistedFate",
        "Vel'Koz": "Velkoz",
        "Xin Zhao": "XinZhao",
        "Wukong": "Wukong",  # Ensure this maps to itself
    }
    
    # Also create lowercase mappings for case-insensitive matching
    lowercase_map = {k.lower(): v for k, v in name_mappings.items()}
    
    return name_mappings, lowercase_map, canonical_names

def unify_name(name, name_mappings, lowercase_map, canonical_names):
    """Unify a single champion name to its canonical form."""
    if not isinstance(name, str):
        return name
    
    # If already canonical, return as-is
    if name in canonical_names:
        return name
    
    # Try direct mapping
    if name in name_mappings:
        return name_mappings[name]
    
    # Try lowercase mapping
    lower_name = name.lower()
    if lower_name in lowercase_map:
        return lowercase_map[lower_name]
    
    # Return original if no mapping found (will need manual review)
    return name

def unify_annotated_abilities():
    """Unify champion names in annotated_abilities_df.pkl"""
    print("Processing annotated_abilities_df.pkl...")
    
    with open("data/annotated_abilities_df.pkl", "rb") as f:
        df = pickle.load(f)
    
    name_mappings, lowercase_map, canonical_names = create_name_unifier()
    
    # Store original unique champions for comparison
    original_champions = set(df["champion"].unique())
    
    # Apply unification
    df["champion"] = df["champion"].apply(
        lambda x: unify_name(x, name_mappings, lowercase_map, canonical_names)
    )
    
    # Check for any remaining unmapped names
    new_champions = set(df["champion"].unique())
    unmapped = original_champions - new_champions
    if unmapped:
        print(f"  Warning: Unmapped champions found: {unmapped}")
    
    # Check for names not in canonical list
    non_canonical = new_champions - canonical_names
    if non_canonical:
        print(f"  Warning: Non-canonical champions after unification: {non_canonical}")
    
    # Save back
    with open("data/annotated_abilities_df.pkl", "wb") as f:
        pickle.dump(df, f)
    
    print(f"  Updated {len(df)} rows")
    print(f"  Unified {len(original_champions)} unique champions to {len(new_champions)} canonical names")

def unify_champion_damage_breakdown():
    """Unify champion names in champion_damage_breakdown.pkl"""
    print("Processing champion_damage_breakdown.pkl...")
    
    with open("data/champion_damage_breakdown.pkl", "rb") as f:
        df = pickle.load(f)
    
    name_mappings, lowercase_map, canonical_names = create_name_unifier()
    
    # Store original unique champions for comparison
    original_champions = set(df["champion_name"].unique())
    
    # Apply unification
    df["champion_name"] = df["champion_name"].apply(
        lambda x: unify_name(x, name_mappings, lowercase_map, canonical_names)
    )
    
    # Check for any remaining unmapped names
    new_champions = set(df["champion_name"].unique())
    unmapped = original_champions - new_champions
    if unmapped:
        print(f"  Warning: Unmapped champions found: {unmapped}")
    
    # Check for names not in canonical list
    non_canonical = new_champions - canonical_names
    if non_canonical:
        print(f"  Warning: Non-canonical champions after unification: {non_canonical}")
    
    # Save back
    with open("data/champion_damage_breakdown.pkl", "wb") as f:
        pickle.dump(df, f)
    
    print(f"  Updated {len(df)} rows")
    print(f"  Unified {len(original_champions)} unique champions to {len(new_champions)} canonical names")

def unify_unified_data():
    """Unify champion names in unified_data.pkl (picks and bans)"""
    print("Processing unified_data.pkl...")
    
    with open("data/unified_data.pkl", "rb") as f:
        df = pickle.load(f)
    
    name_mappings, lowercase_map, canonical_names = create_name_unifier()
    
    # Track original champion names found
    original_champions = set()
    
    # Update picks
    for idx, row in df.iterrows():
        for pick in row["picks"]:
            if "champion_name" in pick:
                original_champions.add(pick["champion_name"])
                pick["champion_name"] = unify_name(
                    pick["champion_name"], name_mappings, lowercase_map, canonical_names
                )
        for ban in row["bans"]:
            if "champion_name" in ban:
                original_champions.add(ban["champion_name"])
                ban["champion_name"] = unify_name(
                    ban["champion_name"], name_mappings, lowercase_map, canonical_names
                )
    
    # Check for non-canonical names after unification
    new_champions = set()
    for idx, row in df.iterrows():
        for pick in row["picks"]:
            if "champion_name" in pick:
                new_champions.add(pick["champion_name"])
        for ban in row["bans"]:
            if "champion_name" in ban:
                new_champions.add(ban["champion_name"])
    
    non_canonical = new_champions - canonical_names
    if non_canonical:
        print(f"  Warning: Non-canonical champions after unification: {non_canonical}")
    
    # Save back
    with open("data/unified_data.pkl", "wb") as f:
        pickle.dump(df, f)
    
    print(f"  Updated {len(df)} matches")
    print(f"  Unified {len(original_champions)} unique champion references to {len(new_champions)} canonical names")

if __name__ == "__main__":
    print("=" * 60)
    print("Champion Name Unification Script")
    print("=" * 60)
    
    unify_annotated_abilities()
    unify_champion_damage_breakdown()
    unify_unified_data()
    
    print("=" * 60)
    print("Unification complete!")
    print("=" * 60)
