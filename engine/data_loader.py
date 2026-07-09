import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def load_json(file_name):
    """
    Load a JSON file from the data folder.

    Example:
        load_json("type_chart.json")
        load_json("type_chart")
    """
    if not file_name.endswith(".json"):
        file_name = f"{file_name}.json"

    file_path = DATA_DIR / file_name

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)
    
def save_json(file_name, data):
    """
    Save data to a JSON file in the data folder.

    Example:
        save_json("team_data", team)
        save_json("team_data.json", team)
    """
    if not file_name.endswith(".json"):
        file_name = f"{file_name}.json"

    file_path = DATA_DIR / file_name

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)