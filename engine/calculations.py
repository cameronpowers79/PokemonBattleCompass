def is_opponent_record(pokemon):
    return pokemon.get("Trainer") is not None and pokemon.get("Battle") is not None


def approximate_stat(base_stat, level):
    return ((2 * base_stat + 31) * level / 100) + 5


def get_stat(pokemon, stat_name):
    if is_opponent_record(pokemon):
        return approximate_stat(
            pokemon[stat_name],
            pokemon["Level"]
        )

    return pokemon[stat_name]

from engine.mechanics import get_stab_multiplier, get_type_multiplier


def get_relevant_attack_stat(attacker, move_category):
    if move_category == "Physical":
        return get_stat(attacker, "ATK")

    if move_category == "Special":
        return get_stat(attacker, "SPA")

    return 0


def get_relevant_defense_stat(defender, move_category):
    if move_category == "Physical":
        return get_stat(defender, "DEF")

    if move_category == "Special":
        return get_stat(defender, "SPD")


def calculate_move_score(attacker, defender, move):
    if move["Category"] == "Status" or not move["Power"]:
        return 0

    attacker_types = [
        attacker.get("Type1"),
        attacker.get("Type2")
    ]

    defender_types = [
        defender.get("Type1"),
        defender.get("Type2")
    ]

    effectiveness = get_type_multiplier(move["Type"], defender_types)
    stab = get_stab_multiplier(move["Type"], attacker_types)

    attack_stat = get_relevant_attack_stat(attacker, move["Category"])
    defense_stat = get_relevant_defense_stat(defender, move["Category"])

    return move["Power"] * effectiveness * stab * attack_stat / defense_stat