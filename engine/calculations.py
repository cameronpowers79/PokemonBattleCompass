from engine.mechanics import (
    get_stab_multiplier,
    get_type_multiplier,
    get_item_multiplier,
    get_ability_multiplier,
)
from engine.notes import build_notes

def is_opponent_record(pokemon):
    return pokemon.get("Trainer") is not None and pokemon.get("Battle") is not None


def approximate_stat(base_stat, level):
    return ((2 * base_stat + 31) * level / 100) + 5


def get_stat(pokemon, stat_name):
    if is_opponent_record(pokemon):
        return approximate_stat(pokemon[stat_name], pokemon["Level"])

    return pokemon[stat_name]


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

    return 1


def calculate_move_score(attacker, defender, move, items=None, ability_rules=None):
    if move["Category"] == "Status" or not move["Power"]:
        return 0

    if items is None:
        items = []

    if ability_rules is None:
        ability_rules = []

    attacker_types = [attacker.get("Type1"), attacker.get("Type2")]
    defender_types = [defender.get("Type1"), defender.get("Type2")]

    effectiveness = get_type_multiplier(move["Type"], defender_types)
    ability_multiplier = get_ability_multiplier(defender, move, ability_rules)
    effectiveness *= ability_multiplier

    stab = get_stab_multiplier(move["Type"], attacker_types)
    item_multiplier = get_item_multiplier(attacker.get("Held Item"), move, items)

    attack_stat = get_relevant_attack_stat(attacker, move["Category"])
    defense_stat = get_relevant_defense_stat(defender, move["Category"])

    return move["Power"] * effectiveness * stab * item_multiplier * attack_stat / defense_stat


def get_moves(pokemon):
    moves = []

    for slot in range(1, 5):
        move_name = pokemon.get(f"Move{slot}")

        if not move_name:
            continue

        moves.append({
            "Move": move_name,
            "Type": pokemon.get(f"Move{slot}Type"),
            "Power": pokemon.get(f"Move{slot}Power"),
            "Category": pokemon.get(f"Move{slot}Category"),
            "Accuracy": pokemon.get(f"Move{slot}Accuracy"),
        })

    return moves


def get_best_move(attacker, defender, items, ability_rules=None):
    best_move = None
    best_score = -1

    for move in get_moves(attacker):
        score = calculate_move_score(
            attacker,
            defender,
            move,
            items,
            ability_rules
        )

        if score > best_score:
            best_score = score
            best_move = move

    return best_move, best_score


def get_worst_incoming_move(opponent, defender, items, ability_rules=None):
    worst_move = None
    worst_score = -1

    for move in get_moves(opponent):
        score = calculate_move_score(
            opponent,
            defender,
            move,
            items,
            ability_rules
        )

        if score > worst_score:
            worst_score = score
            worst_move = move

    return worst_move, worst_score


def calculate_matchup_ratio(attacker, defender, items, ability_rules=None):
    best_move, best_score = get_best_move(
        attacker,
        defender,
        items,
        ability_rules
    )

    worst_move, worst_score = get_worst_incoming_move(
        defender,
        attacker,
        items,
        ability_rules
    )

    if worst_score == 0:
        return best_move, best_score, worst_move, worst_score, 99

    ratio = best_score / worst_score

    return best_move, best_score, worst_move, worst_score, ratio


def find_best_team_member(team, opponent, items, ability_rules=None):
    best_pokemon = None
    best_ratio = -1
    best_result = None

    for pokemon in team:
        result = calculate_matchup_ratio(
            pokemon,
            opponent,
            items,
            ability_rules
        )

        ratio = result[4]

        if ratio > best_ratio:
            best_ratio = ratio
            best_pokemon = pokemon
            best_result = result

    return best_pokemon, best_result


def evaluate_team_matchups(team, opponent, items, ability_rules=None):
    results = []

    for pokemon in team:
        best_move, best_score, worst_move, worst_score, ratio = calculate_matchup_ratio(
            pokemon,
            opponent,
            items,
            ability_rules
        )

        results.append({
    "Pokemon": pokemon["Pokemon"],
    "Best Move": best_move["Move"],
    "Best MoveScore": round(best_score, 2),
    "Worst Incoming Move": worst_move["Move"],
    "Incoming Worst Score": round(worst_score, 2),
    "Ratio": round(ratio, 2),
    "Notes": build_notes(best_score, worst_score, ratio)
})

    return sorted(
        results,
        key=lambda row: row["Ratio"],
        reverse=True
    )