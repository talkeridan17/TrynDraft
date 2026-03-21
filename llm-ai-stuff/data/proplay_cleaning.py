import json
import os
import logging
import argparse
import pandas as pd
import pickle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

def export_file_data(fp: str):
    with open(fp, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data is None:
        print(f"File {fp}: Failed to load JSON")
        return None
    
    # Create a new row as a dictionary
    new_row = {
        "match_id": data["match_id"],
        "patch": data["patch"],
        "domain": "proplay",
        "blue_win": data["blue_win"],
        "game_length_s": data["game_length_s"],
        "recency_weight": data["recency_weight"],
        "tournament": data["tournament"],
        "bans": [{"champion_id": ban["champion_id"], "champion_name": ban["champion_name"], "side": ban["side"]} for ban in data["bans"]],
        "picks": [{"champion_id": pick["champion_id"], "champion_name": pick["champion_name"], "side": pick["side"], "lane": pick["lane"]} for pick in data["picks"]]
    }
    
    # Return the new row
    return new_row

def clean(input_path: str, output_path: str):
    file_ct = 0
    dir_ct = 0
    for file in os.listdir(input_path):
        if os.path.isfile(os.path.join(input_path, file)):
            file_ct += 1
        elif os.path.isdir(os.path.join(input_path, file)):
            dir_ct += 1
    
    log.info(f"Found {file_ct} files and {dir_ct} directories in {input_path}")
    files_parsed = 0
    log.info(f"Starting cleaning process... Progress: {files_parsed}/{file_ct} ")
    
    # Collect all rows
    all_rows = []
    
    for root, dirs, files in os.walk(input_path):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                files_parsed += 1
                log.info(f"Processing {file_path}... Progress: {files_parsed}/{file_ct}")
                
                # Process the file and get the row
                row = export_file_data(file_path)
                if row is not None:
                    all_rows.append(row)
    
    # Create DataFrame from all collected rows
    df = pd.DataFrame(all_rows)
    
    # Create output directory if it doesn't exist, create parent directories if needed
    if not os.path.exists(output_path):
        os.makedirs(output_path, exist_ok=True)
    
    with open(os.path.join(output_path, "proplay_cleaned.pkl"), "wb") as f:
        pickle.dump(df, f)
    
    log.info(f"Saved cleaned data to {os.path.join(output_path, 'proplay_cleaned.pkl')}")
    log.info(f"Total files processed: {files_parsed}")
    log.info(f"Total rows in dataframe: {len(df)}")
    log.info(f"Sample head: \n{df.head()}")

test_mode = False
if __name__ == "__main__":
    if test_mode:
        clean("proplay_json_ex", "proplay_json_out")
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument("--input", default="data/pro/processed")
        parser.add_argument("--output", default="./")
        args = parser.parse_args()
        clean(args.input, args.output)
