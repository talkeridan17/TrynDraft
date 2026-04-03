import pickle

def load_champion_map():
    with open("data/champion_map.pkl", "rb") as f:
        return pickle.load(f)

def reverse_champion_map():
    return {v: k for k, v in load_champion_map().items()}

def unify_champ_names(name):
    match name:
        case "AurelionSol":
            return "Aurelion Sol"
        case "Belveth":
            return "Bel'Veth"
        case "Chogath":
            return "Cho'Gath"
        case "DrMundo":
            return "Dr. Mundo"
        case "JarvanIV":
            return "Jarvan IV"
        case "KSante":
            return "K'Sante"
        case "Kaisa":
            return "Kai'Sa"
        case "Khazix":
            return "Kha'Zix"
        case "KogMaw":
            return "Kog'Maw"
        case "LeeSin":
            return "Lee Sin"
        case "Nunu":
            return "Nunu & Willump"
        case "MasterYi":
            return "Master Yi"
        case "MissFortune":
            return "Miss Fortune"
        case "Renata":
            return "Renata Glasc"
        case "RekSai":
            return "Rek'Sai"
        case "Shacoking":
            return "Shaco"
        case "TahmKench":
            return "Tahm Kench"
        case "TwistedFate":
            return "Twisted Fate"
        case "Velkoz":
            return "Vel'Koz"
        case "XinZhao":
            return "Xin Zhao"
        case _:
            return name

if __name__ == "__main__":
    # fix the champion map
    # champion_map = load_champion_map()
    # for key, value in champion_map.items():
    #     if value != unify_champ_names(value):
    #         print(f"{key}: {value} -> {unify_champ_names(value)}")
    #         champion_map[key] = unify_champ_names(value)
    
    # with open("data/champion_map.pkl", "wb") as f:
    #     pickle.dump(champion_map, f)
    print(list(load_champion_map().keys()))
    print(list(load_champion_map().values()))
