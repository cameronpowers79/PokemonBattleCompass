from engine.mechanics import get_ability_multiplier, get_type_multiplier


# ---------- General helpers ----------

def move_makes_contact(move):
    return move.get("MakesContact") in [True, "TRUE", "True", "Yes", "Y", 1]


def move_has_priority(move):
    return move.get("Priority") is not None and move.get("Priority") > 0


def pokemon_knows_move(pokemon, move_name):
    return move_name in [
        pokemon.get("Move1"),
        pokemon.get("Move2"),
        pokemon.get("Move3"),
        pokemon.get("Move4"),
    ]


def unique_text_list(values):
    cleaned = []

    for value in values:
        if value and value not in cleaned:
            cleaned.append(value)

    if len(cleaned) == 0:
        return ""

    if len(cleaned) == 1:
        return cleaned[0]

    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"

    return f"{', '.join(cleaned[:-1])} and {cleaned[-1]}"


# ---------- Tactical ability notes ----------

def build_tactical_note(rule, best_move, best_score, move_name):
    target_type = rule.get("TargetType")
    ability = rule.get("Ability")

    if target_type == "OHKO":
        if best_score >= 260:
            return "Sturdy may prevent OHKO"

    if target_type == "Contact":
        if move_makes_contact(best_move):
            return f"{move_name} will trigger {ability}"

    return None


def get_tactical_ability_notes(attacker, defender, best_move, best_score, ability_rules):
    notes = []

    defender_ability = defender.get("Ability")
    move_name = best_move.get("Move", "This move")

    if not defender_ability:
        return notes

    for rule in ability_rules:
        if rule.get("Ability") != defender_ability:
            continue

        if rule.get("Effect") != "Tactical":
            continue

        note = build_tactical_note(
            rule,
            best_move,
            best_score,
            move_name
        )

        if note:
            notes.append(note)

    return notes


# ---------- Move mechanics notes ----------

def get_priority_notes(best_move, worst_move, opponent):
    notes = []

    opponent_name = opponent.get("Pokemon", "The opponent")
    opponent_move_name = worst_move.get("Move", "its move")
    best_move_name = best_move.get("Move", "Your move")

    player_has_priority = move_has_priority(best_move)
    opponent_has_priority = move_has_priority(worst_move)

    if player_has_priority and opponent_has_priority:
        notes.append("Both sides have priority")
    elif player_has_priority:
        notes.append(f"{best_move_name} has priority")
    elif opponent_has_priority:
        if worst_move.get("Power", 0) >= 70:
            notes.append(f"{opponent_name}'s {opponent_move_name} is powerful and has priority")
        else:
            notes.append(f"{opponent_name}'s {opponent_move_name} has priority")

    return notes


def get_activation_condition_notes(attacker, defender, best_move, opponent_moves):
    notes = []

    opponent_name = defender.get("Pokemon", "The opponent")
    best_move_name = best_move.get("Move", "This move")
    best_move_category = best_move.get("Category")
    best_move_power = best_move.get("Power", 0)

    for opponent_move in opponent_moves:
        move_name = opponent_move.get("Move")
        condition = opponent_move.get("ActivationCondition")

        if not move_name or not condition:
            continue

        if condition == "RequiresTargetContactMove" and move_makes_contact(best_move):
            notes.append(f"{best_move_name} may trigger {opponent_name}'s {move_name}")

        if condition == "RequiresTargetPhysicalMove" and best_move_category == "Physical":
            notes.append(f"Physical attacks may trigger {opponent_name}'s {move_name}")

        if condition == "RequiresTargetSpecialMove" and best_move_category == "Special":
            notes.append(f"Special attacks may trigger {opponent_name}'s {move_name}")

        if condition == "RequiresTargetDamagingMove" and best_move_power and best_move_power > 0:
            notes.append(f"{opponent_name}'s {move_name} can punish damaging attacks")

        if (
            condition == "RequiresFirstTurn"
            and opponent_move.get("Power", 0) >= 70
            and move_has_priority(opponent_move)
        ):
            notes.append(f"{opponent_name}'s {move_name} is powerful and has priority")

    return notes


def get_move_mechanics_notes(attacker, defender, best_move, worst_move, opponent_moves):
    notes = []

    notes.extend(
        get_priority_notes(
            best_move,
            worst_move,
            defender
        )
    )

    notes.extend(
        get_activation_condition_notes(
            attacker,
            defender,
            best_move,
            opponent_moves
        )
    )

    return unique_text_list(notes).split("; ") if False else list(dict.fromkeys(notes))


# ---------- Incoming move helpers ----------

def get_move_type_list(pokemon):
    move_types = []

    for slot in range(1, 5):
        move_name = pokemon.get(f"Move{slot}")
        move_type = pokemon.get(f"Move{slot}Type")

        if move_name and move_type:
            move_types.append({
                "Move": move_name,
                "Type": move_type,
                "Power": pokemon.get(f"Move{slot}Power"),
                "Category": pokemon.get(f"Move{slot}Category"),
            })

    return move_types


def get_immune_and_resisted_types(pokemon, opponent, ability_rules):
    pokemon_types = [pokemon.get("Type1"), pokemon.get("Type2")]

    immune_types = []
    resisted_types = []

    for move in get_move_type_list(opponent):
        move_type = move["Type"]

        type_multiplier = get_type_multiplier(move_type, pokemon_types)
        ability_multiplier = get_ability_multiplier(
            pokemon,
            move,
            ability_rules,
            type_multiplier
        )

        final_multiplier = type_multiplier * ability_multiplier

        if final_multiplier == 0:
            immune_types.append(move_type)
        elif 0 < final_multiplier < 1:
            resisted_types.append(move_type)

    return unique_text_list(immune_types), unique_text_list(resisted_types)


def has_ability_immunity(pokemon, opponent, ability_rules):
    pokemon_types = [pokemon.get("Type1"), pokemon.get("Type2")]

    for move in get_move_type_list(opponent):
        type_multiplier = get_type_multiplier(move["Type"], pokemon_types)
        ability_multiplier = get_ability_multiplier(
            pokemon,
            move,
            ability_rules,
            type_multiplier
        )

        if ability_multiplier == 0:
            return True

    return False


def has_type_immunity(pokemon, opponent):
    pokemon_types = [pokemon.get("Type1"), pokemon.get("Type2")]

    for move in get_move_type_list(opponent):
        if get_type_multiplier(move["Type"], pokemon_types) == 0:
            return True

    return False


# ---------- Opportunity notes ----------

def get_status_boosted_move_notes(attacker, team_status_effects):
    notes = []

    if pokemon_knows_move(attacker, "Hex"):
        if any(status in team_status_effects for status in ["Burn", "Paralysis", "Poison", "Sleep", "Freeze"]):
            notes.append("Status-boosted Hex possible")

    if pokemon_knows_move(attacker, "Venoshock"):
        if "Poison" in team_status_effects:
            notes.append("Poison-boosted Venoshock possible")

    return notes


# ---------- Notes ----------

def build_notes(
    attacker,
    defender,
    best_move,
    best_score,
    worst_move,
    worst_score,
    ratio,
    ability_rules=None,
    boosted_body_press_score=None,
    team_status_effects=None,
    opponent_moves=None
):
    if ability_rules is None:
        ability_rules = []

    if team_status_effects is None:
        team_status_effects = set()

    if opponent_moves is None:
        opponent_moves = []

    notes = []

    if worst_score == 0:
        notes.append("Immune to opponent's attacks")

    if best_score >= 260:
        notes.append("Likely OHKO")
    elif best_score >= 220:
        notes.append("Possible OHKO")

    if (
        boosted_body_press_score
        and best_move.get("Move") != "Body Press"
        and boosted_body_press_score > best_score
    ):
        notes.append("One Iron Defense makes Body Press the strongest move")

    notes.extend(
        get_status_boosted_move_notes(
            attacker,
            team_status_effects
        )
    )

    notes.extend(
        get_tactical_ability_notes(
            attacker,
            defender,
            best_move,
            best_score,
            ability_rules
        )
    )

    notes.extend(
        get_move_mechanics_notes(
            attacker,
            defender,
            best_move,
            worst_move,
            opponent_moves
        )
    )

    if worst_score >= 260:
        notes.append("Likely Incoming OHKO")
    elif worst_score >= 220:
        notes.append("Possible Incoming OHKO")

    return "; ".join(list(dict.fromkeys(notes)))


# ---------- Recommendation text ----------

def get_second_largest(values):
    sorted_values = sorted(values, reverse=True)

    if len(sorted_values) < 2:
        return sorted_values[0] if sorted_values else 1

    return sorted_values[1]


def get_second_smallest(values):
    sorted_values = sorted(values)

    if len(sorted_values) < 2:
        return sorted_values[0] if sorted_values else 1

    return sorted_values[1]


def get_why_code(selected_result, all_results, opponent, ability_rules):
    best_scores = [result["best_score"] for result in all_results]
    worst_scores = [result["worst_score"] for result in all_results]

    selected_best_score = selected_result["best_score"]
    selected_worst_score = selected_result["worst_score"]
    selected_ratio = selected_result["ratio"]
    selected_pokemon = selected_result["pokemon"]

    second_best_score = get_second_largest(best_scores)
    second_lowest_worst_score = get_second_smallest(worst_scores)

    off_adv_ratio = selected_best_score / second_best_score if second_best_score else selected_best_score
    def_adv_ratio = second_lowest_worst_score / selected_worst_score if selected_worst_score else 999

    overwhelming_results = [
        result
        for result in all_results
        if result["best_score"] > 300 and result["ratio"] > 10
    ]

    has_overwhelming_offense = (
        selected_best_score > 300
        and selected_ratio > 10
    )

    any_overwhelming = len(overwhelming_results) > 0

    best_overwhelming_ratio = max(
        [result["ratio"] for result in overwhelming_results],
        default=None
    )

    ability_immunity = has_ability_immunity(
        selected_pokemon,
        opponent,
        ability_rules
    )

    type_immunity = has_type_immunity(
        selected_pokemon,
        opponent
    )

    if (
        any_overwhelming
        and selected_ratio == best_overwhelming_ratio
        and has_overwhelming_offense
    ):
        return 0

    if ability_immunity:
        return 1

    if type_immunity and selected_worst_score == min(worst_scores):
        return 2

    if off_adv_ratio > 1.3 and def_adv_ratio > 1.3:
        return 3

    if off_adv_ratio >= def_adv_ratio * 0.9 and off_adv_ratio > 1.2:
        return 4

    if def_adv_ratio > off_adv_ratio * 1.1 and def_adv_ratio > 1.2:
        return 5

    if selected_ratio >= 0.8:
        return 6

    return 7


def build_durability_reason(pokemon, opponent, ability_rules):
    immune_types, resisted_types = get_immune_and_resisted_types(
        pokemon,
        opponent,
        ability_rules
    )

    pokemon_name = pokemon.get("Pokemon", "This Pokémon")

    if immune_types and resisted_types:
        return (
            f"{pokemon_name} is immune to {immune_types} attacks "
            f"and resists {resisted_types} attacks"
        )

    if immune_types:
        return f"{pokemon_name} is immune to {immune_types} attacks"

    if resisted_types:
        return f"{pokemon_name} resists {resisted_types} attacks"

    return f"{pokemon_name} has the best durability against this opponent"


def build_why_explanation(all_results, selected_result, opponent, ability_rules=None):
    if ability_rules is None:
        ability_rules = []

    if len(all_results) == 1:
        return "Only Pokemon available"

    selected_pokemon = selected_result["pokemon"]
    worst_score = selected_result["worst_score"]

    if worst_score == 0:
        return build_durability_reason(
            selected_pokemon,
            opponent,
            ability_rules
        )

    why_code = get_why_code(
        selected_result,
        all_results,
        opponent,
        ability_rules
    )

    if why_code == 0:
        return "Overwhelming offensive advantage"

    if why_code == 1:
        return build_durability_reason(
            selected_pokemon,
            opponent,
            ability_rules
        )

    if why_code == 2:
        return build_durability_reason(
            selected_pokemon,
            opponent,
            ability_rules
        )

    if why_code == 3:
        return "Best overall matchup"

    if why_code == 4:
        return "Strongest attack against this opponent"

    if why_code == 5:
        return build_durability_reason(
            selected_pokemon,
            opponent,
            ability_rules
        )

    if why_code == 6:
        return "Best balance of damage and durability"

    return "Highest overall matchup rating"