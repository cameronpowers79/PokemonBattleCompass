import json
from pathlib import Path


def load_type_chart():
    data_path = Path("data/type_chart.json")

    with open(data_path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_type_multiplier(attack_type, defender_types):
    type_chart = load_type_chart()
    multiplier = 1

    for defender_type in defender_types:
        if defender_type:
            multiplier *= type_chart.get(attack_type, {}).get(defender_type, 1)

    return multiplier