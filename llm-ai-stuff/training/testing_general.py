import pickle
import pandas as pd
from proficiency import fetch_proficiency

with open("data/champion_damage_breakdown.pkl", "rb") as f:
    damage_df = pickle.load(f)

id_to_name = {
    int(row["champion_id"]): str(row["champion_name"])
    for _, row in damage_df.iterrows()
}

# profs = fetch_proficiency(
#     game_name="巧みな",
#     tag="4444",
#     region="na",
#     id_to_name=id_to_name,
#     min_games=5,
# )

profs = fetch_proficiency(
    game_name="IdanTheTalker",
    tag="itt",
    region="na",
    id_to_name=id_to_name,
    min_games=5,
)

# Sort by proficiency score descending
top10 = sorted(profs.values(), key=lambda x: x.proficiency, reverse=True)

print(f"Total champions with ≥5 games: {len(profs)}\n")
print(f"{'Champion':<20} {'Games':>6} {'WR':>6} {'KDA':>6} {'OP':>6} {'Prof':>6}")
print("-" * 55)
for p in top10:
    print(
        f"{p.champion_name:<20} {p.games:>6} "
        f"{p.winrate*100:>5.1f}% {p.kda:>6.2f} "
        f"{p.avg_op_score:>6.1f} {p.proficiency:>6.4f}"
    )