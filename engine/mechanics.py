from engine.data_loader import load_json


def load_type_chart():
    return load_json("type_chart")


def get_type_multiplier(attack_type, defender_types):
    type_chart = load_type_chart()
    multiplier = 1

    for defender_type in defender_types:
        if defender_type:
            multiplier *= type_chart.get(attack_type, {}).get(defender_type, 1)

    return multiplier