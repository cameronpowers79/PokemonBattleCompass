from engine.mechanics import (
    get_stab_multiplier,
    get_type_multiplier,
    get_item_multiplier,
    get_ability_multiplier,
    get_attack_stat_multiplier,
    get_attack_reduction_multiplier,
    get_move_power_multiplier,
)
from engine.notes import build_notes, build_battle_notes, build_why_explanation


def is_opponent_record(pokemon):
    return pokemon.get("Trainer") is not None and pokemon.get("Battle") is not None


def approximate_stat(base_stat, level):
    return ((2 * base_stat + 31) * level / 100) + 5


def approximate_hp(base_hp, level):
    return ((2 * base_hp + 31) * level / 100) + level + 10


def get_stat(pokemon, stat_name):
    if is_opponent_record(pokemon):
        if stat_name == "HP":
            return approximate_hp(
                pokemon[stat_name],
                pokemon["Level"]
            )

        return approximate_stat(
            pokemon[stat_name],
            pokemon["Level"]
        )

    return pokemon[stat_name]


def get_relevant_attack_stat(attacker, move):
    damage_method = move.get("DamageMethod")

    if damage_method == "UseDEF":
        return get_stat(attacker, "DEF")

    if move.get("Category") == "Physical":
        return get_stat(attacker, "ATK")

    if move.get("Category") == "Special":
        return get_stat(attacker, "SPA")

    return 0


def get_relevant_defense_stat(defender, move):
    damage_method = move.get("DamageMethod")

    if damage_method == "TargetDEFasSPD":
        return get_stat(defender, "DEF")

    if move.get("Category") == "Physical":
        return get_stat(defender, "DEF")

    if move.get("Category") == "Special":
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
    ability_multiplier = get_ability_multiplier(
        defender,
        move,
        ability_rules,
        effectiveness
    )
    effectiveness *= ability_multiplier

    stab = get_stab_multiplier(
        move["Type"],
        attacker_types,
        attacker,
        ability_rules
    )

    item_multiplier = get_item_multiplier(attacker.get("Held Item"), move, items)
    power_multiplier = get_move_power_multiplier(attacker, move, ability_rules)

    attack_stat = get_relevant_attack_stat(attacker, move)
    attack_stat *= get_attack_stat_multiplier(attacker, move, ability_rules)
    attack_stat *= get_attack_reduction_multiplier(
        attacker,
        defender,
        move,
        ability_rules
    )

    defense_stat = get_relevant_defense_stat(defender, move)

    return (
        move["Power"]
        * power_multiplier
        * effectiveness
        * stab
        * item_multiplier
        * attack_stat
        / defense_stat
    )


def get_moves(pokemon, moves_data=None):
    moves = []

    if moves_data is None:
        moves_data = []

    move_lookup = {
        move.get("Move"): move
        for move in moves_data
        if move.get("Move")
    }

    for slot in range(1, 5):
        move_name = pokemon.get(f"Move{slot}")

        if not move_name:
            continue

        move_info = move_lookup.get(move_name, {})

        moves.append({
            "Move": move_name,

            # Trust the battle/team sheet for scoring fields.
            "Type": pokemon.get(f"Move{slot}Type"),
            "Power": pokemon.get(f"Move{slot}Power"),
            "Category": pokemon.get(f"Move{slot}Category"),
            "Accuracy": pokemon.get(f"Move{slot}Accuracy"),

            # Use moves.json for mechanics metadata.
            "Hits": move_info.get("Hits", 1),
            "MakesContact": move_info.get("MakesContact"),
            "Priority": move_info.get("Priority"),
            "DamageMethod": move_info.get("DamageMethod"),
            "MechanicsNotes": move_info.get("MechanicsNotes"),
            "ActivationCondition": move_info.get("ActivationCondition"),
            "StatusEffect": move_info.get("StatusEffect"),
            "ActivationPowerMultiplier": move_info.get("ActivationPowerMultiplier", 1),
        })

    return moves


def get_team_status_effects(team, moves_data=None):
    if moves_data is None:
        moves_data = []

    move_lookup = {
        move.get("Move"): move
        for move in moves_data
        if move.get("Move")
    }

    status_effects = set()

    for pokemon in team:
        for slot in range(1, 5):
            move_name = pokemon.get(f"Move{slot}")

            if not move_name:
                continue

            move_info = move_lookup.get(move_name, {})
            status_effect = move_info.get("StatusEffect")

            if status_effect:
                status_effects.add(status_effect)

    return status_effects


def calculate_boosted_body_press_score(attacker, defender, items, ability_rules=None, moves_data=None):
    move_names = [
        attacker.get("Move1"),
        attacker.get("Move2"),
        attacker.get("Move3"),
        attacker.get("Move4"),
    ]

    if "Iron Defense" not in move_names or "Body Press" not in move_names:
        return None

    body_press = None

    for move in get_moves(attacker, moves_data):
        if move.get("Move") == "Body Press":
            body_press = move
            break

    if body_press is None:
        return None

    boosted_attacker = dict(attacker)
    boosted_attacker["DEF"] = attacker["DEF"] * 2

    return calculate_move_score(
        boosted_attacker,
        defender,
        body_press,
        items,
        ability_rules
    )


def get_opponent_dmax_note(opponent):
    move_names = [
        opponent.get("Move1"),
        opponent.get("Move2"),
        opponent.get("Move3"),
        opponent.get("Move4"),
    ]

    if any(move and str(move).startswith("G-Max") for move in move_names):
        return "G-Max"

    if any(move and str(move).startswith("Max ") for move in move_names):
        return "Dmax"

    return ""


def get_best_move(attacker, defender, items, ability_rules=None, moves_data=None):
    best_move = None
    best_score = -1

    for move in get_moves(attacker, moves_data):
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


def get_worst_incoming_move(opponent, defender, items, ability_rules=None, moves_data=None):
    worst_move = None
    worst_score = -1

    for move in get_moves(opponent, moves_data):
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


def calculate_matchup_ratio(attacker, defender, items, ability_rules=None, moves_data=None):
    best_move, best_score = get_best_move(
        attacker,
        defender,
        items,
        ability_rules,
        moves_data
    )

    worst_move, worst_score = get_worst_incoming_move(
        defender,
        attacker,
        items,
        ability_rules,
        moves_data
    )

    if worst_score == 0:
        return best_move, best_score, worst_move, worst_score, 99

    ratio = best_score / worst_score

    return best_move, best_score, worst_move, worst_score, ratio


def find_best_team_member(team, opponent, items, ability_rules=None, moves_data=None):
    all_results = []

    for pokemon in team:
        best_move, best_score, worst_move, worst_score, ratio = calculate_matchup_ratio(
            pokemon,
            opponent,
            items,
            ability_rules,
            moves_data
        )

        all_results.append({
            "pokemon": pokemon,
            "best_move": best_move,
            "best_score": best_score,
            "worst_move": worst_move,
            "worst_score": worst_score,
            "ratio": ratio
        })

    selected_result = max(
        all_results,
        key=lambda result: result["ratio"]
    )

    why = build_why_explanation(
        all_results,
        selected_result,
        opponent,
        ability_rules
    )

    best_result = (
        selected_result["best_move"],
        selected_result["best_score"],
        selected_result["worst_move"],
        selected_result["worst_score"],
        selected_result["ratio"]
    )

    return selected_result["pokemon"], best_result, why

def calculate_offensive_multiplier(attacker, defender, move, ability_rules=None):
    if ability_rules is None:
        ability_rules = []

    defender_types = [
        defender.get("Type1"),
        defender.get("Type2")
    ]

    type_multiplier = get_type_multiplier(move["Type"], defender_types)

    ability_multiplier = get_ability_multiplier(
        defender,
        move,
        ability_rules,
        type_multiplier
    )

    return type_multiplier * ability_multiplier

def calculate_incoming_multiplier(opponent, defender, move, ability_rules=None):
    if ability_rules is None:
        ability_rules = []

    defender_types = [
        defender.get("Type1"),
        defender.get("Type2")
    ]

    type_multiplier = get_type_multiplier(move["Type"], defender_types)

    ability_multiplier = get_ability_multiplier(
        defender,
        move,
        ability_rules,
        type_multiplier
    )

    return type_multiplier * ability_multiplier

def evaluate_team_matchups(team, opponent, items, ability_rules=None, moves_data=None):
    results = []
    team_status_effects = get_team_status_effects(team, moves_data)
    opponent_moves = get_moves(opponent, moves_data)
    dmax_note = get_opponent_dmax_note(opponent)

    opponent_hp = get_stat(opponent, "HP")
    opponent_spe = get_stat(opponent, "SPE")

    for pokemon in team:
        best_move, best_score, worst_move, worst_score, ratio = calculate_matchup_ratio(
            pokemon,
            opponent,
            items,
            ability_rules,
            moves_data
        )

        if best_move is None:
            raise RuntimeError(
                f"No valid offensive move found for "
                f"{pokemon.get('Pokemon', 'Unknown Pokémon')}."
            )

        if worst_move is None:
            raise RuntimeError(
                f"No valid incoming move found for "
                f"{opponent.get('Pokemon', 'Unknown opponent')}."
            )

        item_multiplier = get_item_multiplier(
            pokemon.get("Held Item"),
            best_move,
            items
        )

        item_boosted = item_multiplier > 1

        base_move_score = (
            best_score / item_multiplier
            if item_boosted
            else best_score
        )

        item_bonus_amount = best_score - base_move_score

        boosted_body_press_score = calculate_boosted_body_press_score(
            pokemon,
            opponent,
            items,
            ability_rules,
            moves_data
        )

        best_hp_ratio = best_score / opponent_hp if opponent_hp else None
        incoming_hp_ratio = worst_score / pokemon["HP"] if pokemon.get("HP") else None

        team_moves_second = pokemon.get("SPE", 0) < opponent_spe

        # Workbook intent: Survival OHKO only appears when the team member moves second
        # and is not itself likely to be KO'd first.
        likely_survives_first_hit = (
            incoming_hp_ratio is None
            or incoming_hp_ratio < 2
        )

        battle_notes = build_battle_notes(
            pokemon,
            opponent,
            best_move,
            best_score,
            worst_move,
            worst_score,
            ratio,
            ability_rules,
            boosted_body_press_score,
            team_status_effects,
            opponent_moves,
            best_hp_ratio,
            incoming_hp_ratio,
            team_moves_second,
            likely_survives_first_hit,
            dmax_note
        )

        incoming_multiplier = calculate_incoming_multiplier(
            opponent,
            pokemon,
            worst_move,
            ability_rules
        )

        offensive_multiplier = calculate_offensive_multiplier(
            pokemon,
            opponent,
            best_move,
            ability_rules
        )

        results.append({
            "Pokemon": pokemon["Pokemon"],
            "Gender": pokemon.get("Gender"),
            "Best Move": best_move["Move"],
            "Best MoveScore": round(best_score, 2),
            "Base MoveScore": round(base_move_score, 2),
            "Best Move Type": best_move.get("Type"),
            "Best Move Category": best_move.get("Category"),
            "Item Boosted": item_boosted,
            "Item Multiplier": round(item_multiplier, 4),
            "Item Bonus Amount": round(item_bonus_amount, 2),
            "Held Item": pokemon.get("Held Item"),
            "Best Move Multiplier": round(offensive_multiplier, 2),
            "Worst Incoming Move": worst_move["Move"],
            "Worst Incoming Move Type": worst_move.get("Type"),
            "Worst Incoming Move Category": worst_move.get("Category"),
            "Incoming Multiplier": round(incoming_multiplier, 2),
            "Incoming Worst Score": round(worst_score, 2),
            "Is Immune": worst_score == 0,
            "Ratio": round(ratio, 2),
            "Battle Notes": battle_notes,
            "Notes": build_notes(
                pokemon,
                opponent,
                best_move,
                best_score,
                worst_move,
                worst_score,
                ratio,
                ability_rules,
                boosted_body_press_score,
                team_status_effects,
                opponent_moves,
                best_hp_ratio,
                incoming_hp_ratio,
                team_moves_second,
                likely_survives_first_hit,
                dmax_note
            )
        })

    return sorted(
        results,
        key=lambda row: row["Ratio"],
        reverse=True
    )