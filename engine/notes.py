from engine.mechanics import get_ability_multiplier, get_type_multiplier

NOTE_INFO = "info"
NOTE_OPPORTUNITY = "opportunity"
NOTE_CAUTION = "caution"
NOTE_WARNING = "warning"

# ---------- General helpers ----------

def note(category, text):
    return {
        "category": category,
        "text": text
    }


def note_text(notes):
    return "; ".join(item["text"] for item in dedupe_notes(notes))


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


def dedupe_notes(notes):
    seen = set()
    cleaned = []

    for item in notes:
        text = item.get("text")

        if not text or text in seen:
            continue

        seen.add(text)
        cleaned.append(item)

    return cleaned


# ---------- Tactical ability notes ----------

def build_tactical_note(rule, best_move, move_name, has_ohko_note):
    target_type = rule.get("TargetType")
    ability = rule.get("Ability")

    if target_type == "OHKO" and has_ohko_note:
        return note(NOTE_WARNING, "Sturdy may prevent OHKO")

    if target_type == "Contact" and move_makes_contact(best_move):
        return note(NOTE_CAUTION, f"{move_name} will trigger {ability}")

    if target_type == "Faint" and has_ohko_note:
        return note(NOTE_CAUTION, f"{ability} may trigger if the target faints")

    return None


def get_tactical_ability_notes(defender, best_move, ability_rules, has_ohko_note):
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

        built_note = build_tactical_note(
            rule,
            best_move,
            move_name,
            has_ohko_note
        )

        if built_note:
            notes.append(built_note)

    return notes


# ---------- Tactical item notes ----------

def pokemon_has_status_move(pokemon):
    return any(
        pokemon.get(f"Move{slot}Category") == "Status"
        for slot in range(1, 5)
    )


def get_tactical_item_notes(
    attacker,
    defender,
    best_move,
    worst_move,
    has_ohko_note,
):
    notes = []

    attacker_item = attacker.get("Held Item")
    defender_item = defender.get("Held Item")
    best_move_name = best_move.get(
        "Move",
        "This move",
    )

    if attacker_item == "Life Orb":
        notes.append(
            note(
                NOTE_CAUTION,
                "Life Orb recoil follows successful damaging attacks",
            )
        )

    if attacker_item in {
        "Choice Band",
        "Choice Specs",
        "Choice Scarf",
    }:
        notes.append(
            note(
                NOTE_INFO,
                f"{attacker_item} locks the user into its first selected move",
            )
        )

    if (
        attacker_item == "Assault Vest"
        and pokemon_has_status_move(attacker)
    ):
        notes.append(
            note(
                NOTE_WARNING,
                "Assault Vest prevents the use of status moves",
            )
        )

    if (
        defender_item == "Rocky Helmet"
        and move_makes_contact(best_move)
    ):
        notes.append(
            note(
                NOTE_CAUTION,
                f"{best_move_name} will trigger Rocky Helmet",
            )
        )

    if (
        defender_item == "Focus Sash"
        and has_ohko_note
    ):
        notes.append(
            note(
                NOTE_WARNING,
                "Focus Sash may prevent an OHKO at full HP",
            )
        )

    if (
        attacker_item == "Focus Sash"
        and worst_move
    ):
        notes.append(
            note(
                NOTE_INFO,
                "Focus Sash may preserve 1 HP from a lethal hit at full HP",
            )
        )

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
        notes.append(note(NOTE_INFO, "Both sides have priority"))
    elif player_has_priority:
        notes.append(note(NOTE_INFO, f"{best_move_name} has priority"))
    elif opponent_has_priority:
        if worst_move.get("Power", 0) >= 70:
            notes.append(note(NOTE_WARNING, f"{opponent_name}'s {opponent_move_name} is powerful and has priority"))
        else:
            notes.append(note(NOTE_CAUTION, f"{opponent_name}'s {opponent_move_name} has priority"))

    return notes


def get_activation_condition_notes(defender, best_move, opponent_moves):
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
            notes.append(note(NOTE_WARNING, f"{best_move_name} may trigger {opponent_name}'s {move_name}"))

        if condition == "RequiresTargetPhysicalMove" and best_move_category == "Physical":
            notes.append(note(NOTE_WARNING, f"Physical attacks may trigger {opponent_name}'s {move_name}"))

        if condition == "RequiresTargetSpecialMove" and best_move_category == "Special":
            notes.append(note(NOTE_WARNING, f"Special attacks may trigger {opponent_name}'s {move_name}"))

        if condition == "RequiresTargetDamagingMove" and best_move_power and best_move_power > 0:
            notes.append(note(NOTE_WARNING, f"{opponent_name}'s {move_name} can punish damaging attacks"))

        if (
            condition == "RequiresFirstTurn"
            and opponent_move.get("Power", 0) >= 70
            and move_has_priority(opponent_move)
        ):
            notes.append(note(NOTE_WARNING, f"{opponent_name}'s {move_name} is powerful and has priority"))

    return notes


def get_move_mechanics_notes(defender, best_move, worst_move, opponent_moves):
    notes = []

    notes.extend(get_priority_notes(best_move, worst_move, defender))
    notes.extend(get_activation_condition_notes(defender, best_move, opponent_moves))

    return dedupe_notes(notes)


# ---------- Incoming move helpers ----------

def get_move_type_list(pokemon):
    moves = []

    for slot in range(1, 5):
        move_name = pokemon.get(f"Move{slot}")
        move_type = pokemon.get(f"Move{slot}Type")
        move_power = pokemon.get(f"Move{slot}Power")
        move_category = pokemon.get(f"Move{slot}Category")

        if not move_name or not move_type:
            continue

        # Defensive resistance/immunity language should only consider
        # moves that can actually deal damage.
        if move_category not in {"Physical", "Special"}:
            continue

        moves.append({
            "Move": move_name,
            "Type": move_type,
            "Power": move_power,
            "Category": move_category,
            "MakesContact": pokemon.get(
                f"Move{slot}MakesContact"
            ),
            "MechanicsTags": pokemon.get(
                f"Move{slot}MechanicsTags",
                [],
            ),
        })

    return moves


def get_immune_and_resisted_types(
    pokemon,
    opponent,
    ability_rules,
    opponent_moves=None,
):
    pokemon_types = [
        pokemon.get("Type1"),
        pokemon.get("Type2"),
    ]

    immune_types = []
    resisted_types = []

    moves = (
        opponent_moves
        if opponent_moves is not None
        else get_move_type_list(opponent)
    )

    for move in moves:
        move_type = move.get("Type")

        if not move_type:
            continue

        type_multiplier = get_type_multiplier(
            move_type,
            pokemon_types,
        )

        ability_multiplier = get_ability_multiplier(
            pokemon,
            move,
            ability_rules,
            type_multiplier,
            opponent,
        )

        final_multiplier = (
            type_multiplier
            * ability_multiplier
        )

        if final_multiplier == 0:
            immune_types.append(move_type)
        elif 0 < final_multiplier < 1:
            resisted_types.append(move_type)

    return (
        unique_text_list(immune_types),
        unique_text_list(resisted_types),
    )


def has_ability_immunity(
    pokemon,
    opponent,
    ability_rules,
    opponent_moves=None,
):
    pokemon_types = [
        pokemon.get("Type1"),
        pokemon.get("Type2"),
    ]

    moves = (
        opponent_moves
        if opponent_moves is not None
        else get_move_type_list(opponent)
    )

    for move in moves:
        move_type = move.get("Type")

        if not move_type:
            continue

        type_multiplier = get_type_multiplier(
            move_type,
            pokemon_types,
        )

        ability_multiplier = get_ability_multiplier(
            pokemon,
            move,
            ability_rules,
            type_multiplier,
            opponent,
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
            notes.append(note(NOTE_OPPORTUNITY, "Status-boosted Hex possible"))

    if pokemon_knows_move(attacker, "Venoshock"):
        if "Poison" in team_status_effects:
            notes.append(note(NOTE_OPPORTUNITY, "Poison-boosted Venoshock possible"))

    return notes


# ---------- OHKO notes ----------

def build_offensive_ohko_note(
    best_hp_ratio,
    team_moves_second,
    likely_survives_first_hit,
    has_incoming_damage,
    is_dmax
):
    if best_hp_ratio is None:
        return None

    likely_threshold = 6.5 if is_dmax else 3
    possible_threshold = 4.5 if is_dmax else 2

    meets_likely_ohko = best_hp_ratio >= likely_threshold
    meets_possible_ohko = best_hp_ratio >= possible_threshold

    if (
        team_moves_second
        and has_incoming_damage
        and likely_survives_first_hit
        and meets_likely_ohko
    ):
        return note(NOTE_INFO, "Likely Survival OHKO")

    if (
        team_moves_second
        and has_incoming_damage
        and likely_survives_first_hit
        and meets_possible_ohko
    ):
        return note(NOTE_INFO, "Possible Survival OHKO")

    if (not team_moves_second) or (not has_incoming_damage):
        if meets_likely_ohko:
            return note(NOTE_INFO, "Likely OHKO")

        if meets_possible_ohko:
            return note(NOTE_INFO, "Possible OHKO")

    return None


def build_incoming_ohko_note(is_immune, incoming_hp_ratio):
    if is_immune or incoming_hp_ratio is None:
        return None

    if incoming_hp_ratio >= 3:
        return note(NOTE_WARNING, "Likely Incoming OHKO")

    if incoming_hp_ratio >= 2:
        return note(NOTE_CAUTION, "Possible Incoming OHKO")

    return None


# ---------- Battle Notes ----------

def build_battle_notes(
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
    opponent_moves=None,
    best_hp_ratio=None,
    incoming_hp_ratio=None,
    team_moves_second=False,
    likely_survives_first_hit=False,
    dmax_note="",
    items=None,
):
    if ability_rules is None:
        ability_rules = []

    if team_status_effects is None:
        team_status_effects = set()

    if opponent_moves is None:
        opponent_moves = []

    if items is None:
        items = []

    notes = []

    is_immune = worst_score == 0
    has_incoming_damage = worst_score > 0
    is_dmax = dmax_note != ""

    offensive_ohko_note = build_offensive_ohko_note(
        best_hp_ratio,
        team_moves_second,
        likely_survives_first_hit,
        has_incoming_damage,
        is_dmax
    )

    incoming_ohko_note = build_incoming_ohko_note(
        is_immune,
        incoming_hp_ratio
    )

    has_ohko_note = offensive_ohko_note is not None

    if dmax_note:
        notes.append(note(NOTE_INFO, dmax_note))

    if is_immune:
        notes.append(note(NOTE_INFO, "Immune to opponent's attacks"))

    if offensive_ohko_note:
        notes.append(offensive_ohko_note)

    if incoming_ohko_note:
        notes.append(incoming_ohko_note)

    if (
        not (incoming_ohko_note and incoming_ohko_note["text"].startswith("Likely"))
        and boosted_body_press_score
        and best_move.get("Move") != "Body Press"
        and boosted_body_press_score > best_score
    ):
        notes.append(note(NOTE_OPPORTUNITY, "One Iron Defense makes Body Press the strongest move"))

    if not (incoming_ohko_note and incoming_ohko_note["text"].startswith("Likely")):
        notes.extend(get_status_boosted_move_notes(attacker, team_status_effects))

    notes.extend(
        get_tactical_ability_notes(
            defender,
            best_move,
            ability_rules,
            has_ohko_note
        )
    )

    notes.extend(
        get_tactical_item_notes(
            attacker,
            defender,
            best_move,
            worst_move,
            has_ohko_note,
        )
    )

    notes.extend(
        get_move_mechanics_notes(
            defender,
            best_move,
            worst_move,
            opponent_moves
        )
    )

    return dedupe_notes(notes)


def build_notes(*args, **kwargs):
    return note_text(build_battle_notes(*args, **kwargs))


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


def get_why_code(
    selected_result,
    all_results,
    opponent,
    ability_rules,
    opponent_moves=None,
):
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
        ability_rules,
        opponent_moves,
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


def build_durability_reason(
    pokemon,
    opponent,
    ability_rules,
    opponent_moves=None,
):
    immune_types, resisted_types = get_immune_and_resisted_types(
        pokemon,
        opponent,
        ability_rules,
        opponent_moves,
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


def build_why_explanation(
    all_results,
    selected_result,
    opponent,
    ability_rules=None,
    opponent_moves=None,
):
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
            ability_rules,
            opponent_moves,
        )

    why_code = get_why_code(
        selected_result,
        all_results,
        opponent,
        ability_rules,
        opponent_moves,
    )

    if why_code == 0:
        return "Overwhelming offensive advantage"

    if why_code == 1:
        return build_durability_reason(
            selected_pokemon,
            opponent,
            ability_rules,
            opponent_moves,
        )

    if why_code == 2:
        return build_durability_reason(
            selected_pokemon,
            opponent,
            ability_rules,
            opponent_moves,
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
