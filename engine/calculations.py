'''calculations.py'''

from engine.mechanics import (
    get_stab_multiplier,
    get_type_multiplier,
    get_item_multiplier,
    get_item_damage_multiplier,
    get_item_attack_stat_multiplier,
    get_item_defense_stat_multiplier,
    get_item_speed_multiplier,
    get_item_immunity_multiplier,
    get_ability_multiplier,
    get_applicable_ability_rules,
    get_attack_stat_multiplier,
    get_attack_reduction_multiplier,
    get_move_power_multiplier,
)
from engine.notes import build_notes, build_battle_notes, build_why_explanation


def is_opponent_record(pokemon):
    return pokemon.get("Trainer") is not None and pokemon.get("Battle") is not None


CONSERVATIVE_OPPONENT_IV = 31
AVERAGE_OPPONENT_IV = 16


def approximate_stat(base_stat, level, iv=CONSERVATIVE_OPPONENT_IV):
    return ((2 * base_stat + iv) * level / 100) + 5


def approximate_hp(base_hp, level, iv=CONSERVATIVE_OPPONENT_IV):
    return ((2 * base_hp + iv) * level / 100) + level + 10


def get_stat(pokemon, stat_name, opponent_iv_override=None):
    if is_opponent_record(pokemon):
        iv = (
            CONSERVATIVE_OPPONENT_IV
            if opponent_iv_override is None
            else opponent_iv_override
        )

        if stat_name == "HP":
            return approximate_hp(
                pokemon[stat_name],
                pokemon["Level"],
                iv,
            )

        return approximate_stat(
            pokemon[stat_name],
            pokemon["Level"],
            iv,
        )

    value = pokemon.get(stat_name, 1)

    if stat_name in {"HP", "ATK", "DEF", "SPA", "SPD", "SPE"}:
        return max(float(value or 0), 1.0)

    return value


def get_relevant_attack_stat(
    attacker,
    move,
    opponent_iv_override=None,
    target=None,
    target_opponent_iv_override=None,
):
    damage_method = move.get("DamageMethod")

    if damage_method == "UseDEF":
        return get_stat(attacker, "DEF", opponent_iv_override)

    if damage_method == "TargetATK" and target is not None:
        return get_stat(
            target,
            "ATK",
            target_opponent_iv_override,
        )

    if move.get("Category") == "Physical":
        return get_stat(attacker, "ATK", opponent_iv_override)

    if move.get("Category") == "Special":
        return get_stat(attacker, "SPA", opponent_iv_override)

    return 0


def get_relevant_defense_stat(defender, move, opponent_iv_override=None):
    damage_method = move.get("DamageMethod")

    if damage_method == "TargetDEFasSPD":
        return get_stat(defender, "DEF", opponent_iv_override)

    if move.get("Category") == "Physical":
        return get_stat(defender, "DEF", opponent_iv_override)

    if move.get("Category") == "Special":
        return get_stat(defender, "SPD", opponent_iv_override)

    return 1


def get_effective_move_power(
    attacker,
    defender,
    move,
    items=None,
    attacker_opponent_iv_override=None,
    defender_opponent_iv_override=None,
):
    """Return the modeled base power for the current matchup.

    Most moves use the stored Power value directly. Damage methods that can
    be derived from information the Compass already has may calculate their
    power here without requiring additional battle-state input.
    """
    if items is None:
        items = []

    damage_method = move.get("DamageMethod")

    if damage_method == "SpeedRatioInverse":
        user_speed = (
            get_stat(
                attacker,
                "SPE",
                attacker_opponent_iv_override,
            )
            * get_item_speed_multiplier(attacker, items)
        )
        target_speed = (
            get_stat(
                defender,
                "SPE",
                defender_opponent_iv_override,
            )
            * get_item_speed_multiplier(defender, items)
        )

        # Generation VI onward sets Gyro Ball to 1 BP if the user's
        # effective Speed rounds down to 0. get_stat() normally keeps
        # modeled Speed positive, but retain the guard for completeness.
        if user_speed <= 0:
            return 1

        return min(
            150,
            max(
                1,
                int(25 * target_speed / user_speed) + 1,
            ),
        )

    try:
        return float(move.get("Power") or 0)
    except (TypeError, ValueError):
        return 0


def calculate_move_score(
    attacker,
    defender,
    move,
    items=None,
    ability_rules=None,
):
    if move["Category"] == "Status":
        return 0

    if items is None:
        items = []

    effective_power = get_effective_move_power(
        attacker,
        defender,
        move,
        items,
    )

    if effective_power <= 0:
        return 0

    if ability_rules is None:
        ability_rules = []

    attacker_types = [
        attacker.get("Type1"),
        attacker.get("Type2"),
    ]
    defender_types = [
        defender.get("Type1"),
        defender.get("Type2"),
    ]

    effectiveness = get_type_multiplier(
        move["Type"],
        defender_types,
    )
    ability_multiplier = get_ability_multiplier(
        defender,
        move,
        ability_rules,
        effectiveness,
        attacker,
    )
    effectiveness *= ability_multiplier

    stab = get_stab_multiplier(
        move["Type"],
        attacker_types,
        attacker,
        ability_rules,
    )

    item_multiplier = get_item_multiplier(
        attacker.get("Held Item"),
        move,
        items,
    )
    power_multiplier = get_move_power_multiplier(
        attacker,
        move,
        ability_rules,
    )

    attack_stat = get_relevant_attack_stat(
        attacker,
        move,
        target=defender,
    )
    attack_stat *= get_attack_stat_multiplier(
        attacker,
        move,
        ability_rules,
    )

    # Foul Play-style moves use the target's Attack stat. Defender-side
    # AttackReduction rules such as Intimidate represent lowering the user's
    # own Attack, so they do not reduce a TargetATK calculation.
    if move.get("DamageMethod") != "TargetATK":
        attack_stat *= get_attack_reduction_multiplier(
            attacker,
            defender,
            move,
            ability_rules,
        )

    defense_stat = get_relevant_defense_stat(
        defender,
        move,
    )

    hits = move.get("Hits", 1)

    try:
        hits = float(hits)
    except (TypeError, ValueError):
        hits = 1

    if hits <= 0:
        hits = 1

    return (
        effective_power
        * hits
        * power_multiplier
        * effectiveness
        * stab
        * item_multiplier
        * attack_stat
        / defense_stat
    )


def calculate_damage_range(
    attacker,
    defender,
    move,
    items=None,
    ability_rules=None,
    attacker_opponent_iv_override=None,
    defender_opponent_iv_override=None,
):
    """Estimate minimum and maximum damage using the in-game formula shape.

    The estimate uses the same modeled stats and multipliers as Move Score,
    then applies the Gen VIII random damage range. It intentionally assumes
    the defender's currently modeled, unboosted defensive stat.
    """

    if move["Category"] == "Status":
        return None, None

    if items is None:
        items = []

    effective_power = get_effective_move_power(
        attacker,
        defender,
        move,
        items,
        attacker_opponent_iv_override,
        defender_opponent_iv_override,
    )

    if effective_power <= 0:
        return None, None

    if ability_rules is None:
        ability_rules = []

    attacker_types = [
        attacker.get("Type1"),
        attacker.get("Type2"),
    ]
    defender_types = [
        defender.get("Type1"),
        defender.get("Type2"),
    ]

    effectiveness = get_type_multiplier(
        move["Type"],
        defender_types,
    )
    effectiveness *= get_ability_multiplier(
        defender,
        move,
        ability_rules,
        effectiveness,
        attacker,
    )

    if effectiveness == 0:
        return 0, 0

    stab = get_stab_multiplier(
        move["Type"],
        attacker_types,
        attacker,
        ability_rules,
    )
    item_multiplier = get_item_multiplier(
        attacker.get("Held Item"),
        move,
        items,
    )
    power_multiplier = get_move_power_multiplier(
        attacker,
        move,
        ability_rules,
    )

    attack_stat = get_relevant_attack_stat(
        attacker,
        move,
        attacker_opponent_iv_override,
        target=defender,
        target_opponent_iv_override=defender_opponent_iv_override,
    )
    attack_stat *= get_attack_stat_multiplier(
        attacker,
        move,
        ability_rules,
    )

    if move.get("DamageMethod") != "TargetATK":
        attack_stat *= get_attack_reduction_multiplier(
            attacker,
            defender,
            move,
            ability_rules,
        )

    defense_stat = max(
        get_relevant_defense_stat(
            defender,
            move,
            defender_opponent_iv_override,
        ),
        1,
    )
    level = max(int(attacker.get("Level") or 1), 1)

    effective_power = max(
        effective_power * power_multiplier,
        1,
    )

    # Pokémon's damage formula floors repeatedly. Keeping those floors is
    # especially important at low levels, where one point is a large swing.
    level_factor = (2 * level) // 5 + 2
    scaled_damage = int(
        level_factor
        * effective_power
        * attack_stat
        / defense_stat
    )
    base_damage = scaled_damage // 50 + 2

    fixed_modifier = (
        effectiveness
        * stab
        * item_multiplier
    )

    hits = move.get("Hits", 1)

    try:
        hits = float(hits)
    except (TypeError, ValueError):
        hits = 1.0

    if hits <= 0:
        hits = 1.0

    minimum_per_hit = max(
        int(base_damage * fixed_modifier * 0.85),
        1,
    )
    maximum_per_hit = max(
        int(base_damage * fixed_modifier),
        1,
    )

    return (
        minimum_per_hit * hits,
        maximum_per_hit * hits,
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
            "MechanicsTags": move_info.get("MechanicsTags", []),
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


def get_best_move(
    attacker,
    defender,
    items,
    ability_rules=None,
    moves_data=None,
):
    best_move = None
    best_score = 0

    for move in get_moves(
        attacker,
        moves_data,
    ):
        score = calculate_move_score(
            attacker,
            defender,
            move,
            items,
            ability_rules,
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


def calculate_matchup_ratio(
    attacker,
    defender,
    items,
    ability_rules=None,
    moves_data=None,
):
    best_move, best_score = get_best_move(
        attacker,
        defender,
        items,
        ability_rules,
        moves_data,
    )

    # An empty or status-only moveset has no offensive matchup
    # to evaluate. Return immediately before calculating incoming
    # damage against potentially incomplete stats.
    if best_move is None:
        return None, 0, None, 0, 0

    worst_move, worst_score = get_worst_incoming_move(
        defender,
        attacker,
        items,
        ability_rules,
        moves_data,
    )

    if worst_score == 0:
        return (
            best_move,
            best_score,
            worst_move,
            worst_score,
            99,
        )

    ratio = best_score / worst_score

    return (
        best_move,
        best_score,
        worst_move,
        worst_score,
        ratio,
    )



def build_no_recommendation_reason(
    team,
    opponent,
    ability_rules=None,
    moves_data=None,
):
    """Explain when the opponent's Ability blocks every damaging option."""

    if ability_rules is None:
        ability_rules = []

    opponent_name = str(
        opponent.get("Pokemon")
        or "The opponent"
    )
    opponent_types = [
        opponent.get("Type1"),
        opponent.get("Type2"),
    ]
    blocked_options = []

    for pokemon in team:
        pokemon_name = str(
            pokemon.get("Pokemon")
            or "A team member"
        )

        for move in get_moves(
            pokemon,
            moves_data,
        ):
            if (
                move.get("Category") == "Status"
                or not move.get("Power")
            ):
                continue

            type_multiplier = get_type_multiplier(
                move.get("Type"),
                opponent_types,
            )

            immunity_rule = next(
                (
                    rule
                    for rule in get_applicable_ability_rules(
                        opponent,
                        move,
                        ability_rules,
                        type_multiplier,
                        pokemon,
                    )
                    if rule.get("Effect") == "Immunity"
                ),
                None,
            )

            if immunity_rule is None:
                continue

            blocked_options.append(
                (
                    str(
                        immunity_rule.get("Ability")
                        or opponent.get("Ability")
                        or "Ability"
                    ),
                    pokemon_name,
                    str(
                        move.get("Move")
                        or "damaging move"
                    ),
                )
            )

    unique_options = []

    for option in blocked_options:
        if option not in unique_options:
            unique_options.append(option)

    if not unique_options:
        return ""

    blocked_descriptions = [
        f"{team_member_name}'s {move_name}"
        for _, team_member_name, move_name
        in unique_options
    ]

    if len(blocked_descriptions) == 1:
        blocked_moves_text = blocked_descriptions[0]
    elif len(blocked_descriptions) == 2:
        blocked_moves_text = (
            f"{blocked_descriptions[0]} and "
            f"{blocked_descriptions[1]}"
        )
    else:
        blocked_moves_text = (
            f"{', '.join(blocked_descriptions[:-1])}, "
            f"and {blocked_descriptions[-1]}"
        )

    ability_names = []

    for ability_name, _, _ in unique_options:
        if ability_name not in ability_names:
            ability_names.append(ability_name)

    if len(ability_names) == 1:
        blocker_text = (
            f"{opponent_name}'s {ability_names[0]}"
        )
    else:
        blocker_text = (
            f"{opponent_name}'s "
            f"{' and '.join(ability_names)}"
        )

    return (
        "No usable damaging move is available: "
        f"{blocker_text} blocks {blocked_moves_text}."
    )



def find_best_team_member(
    team,
    opponent,
    items,
    ability_rules=None,
    moves_data=None,
):
    all_results = []

    for pokemon in team:
        (
            best_move,
            best_score,
            worst_move,
            worst_score,
            ratio,
        ) = calculate_matchup_ratio(
            pokemon,
            opponent,
            items,
            ability_rules,
            moves_data,
        )

        if best_move is None:
            continue

        all_results.append(
            {
                "pokemon": pokemon,
                "best_move": best_move,
                "best_score": best_score,
                "worst_move": worst_move,
                "worst_score": worst_score,
                "ratio": ratio,
            }
        )

    if not all_results:
        return (
            None,
            None,
            build_no_recommendation_reason(
                team,
                opponent,
                ability_rules,
                moves_data,
            ),
        )

    selected_result = max(
        all_results,
        key=lambda result: result["ratio"],
    )

    why = build_why_explanation(
        all_results,
        selected_result,
        opponent,
        ability_rules,
        opponent_moves=get_moves(
            opponent,
            moves_data,
        ),
    )

    best_result = (
        selected_result["best_move"],
        selected_result["best_score"],
        selected_result["worst_move"],
        selected_result["worst_score"],
        selected_result["ratio"],
    )

    return (
        selected_result["pokemon"],
        best_result,
        why,
    )

def calculate_offensive_multiplier(
    attacker,
    defender,
    move,
    items=None,
    ability_rules=None,
):
    if items is None:
        items = []

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
        type_multiplier,
        attacker,
    )

    item_multiplier = get_item_immunity_multiplier(
        defender,
        move,
        items,
    )

    return (
        type_multiplier
        * ability_multiplier
        * item_multiplier
    )

def calculate_incoming_multiplier(
    opponent,
    defender,
    move,
    items=None,
    ability_rules=None,
):
    if items is None:
        items = []

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
        type_multiplier,
        opponent,
    )

    item_multiplier = get_item_immunity_multiplier(
        defender,
        move,
        items,
    )

    return (
        type_multiplier
        * ability_multiplier
        * item_multiplier
    )

def evaluate_team_matchups(team, opponent, items, ability_rules=None, moves_data=None):
    results = []
    team_status_effects = get_team_status_effects(team, moves_data)
    opponent_moves = get_moves(opponent, moves_data)
    dmax_note = get_opponent_dmax_note(opponent)

    opponent_hp = get_stat(opponent, "HP")
    opponent_spe = get_stat(opponent, "SPE")
    opponent_is_dmax = dmax_note != ""
    offensive_target_hp = (
        opponent_hp * 2
        if opponent_is_dmax
        else opponent_hp
    )

    for pokemon in team:
        best_move, best_score, worst_move, worst_score, ratio = calculate_matchup_ratio(
            pokemon,
            opponent,
            items,
            ability_rules,
            moves_data
        )

        if best_move is None:
            continue
            

        if worst_move is None:
            raise RuntimeError(
                f"No valid incoming move found for "
                f"{opponent.get('Pokemon', 'Unknown opponent')}."
            )

        type_effectiveness = get_type_multiplier(
            best_move["Type"],
            [
                opponent.get("Type1"),
                opponent.get("Type2"),
            ],
        )

        item_damage_multiplier = (
            get_item_damage_multiplier(
                pokemon,
                opponent,
                best_move,
                items,
                type_effectiveness,
            )
        )

        item_attack_multiplier = (
            get_item_attack_stat_multiplier(
                pokemon,
                best_move,
                items,
            )
        )

        item_multiplier = (
            item_damage_multiplier
            * item_attack_multiplier
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

        (
            offensive_min_damage,
            offensive_max_damage,
        ) = calculate_damage_range(
            pokemon,
            opponent,
            best_move,
            items,
            ability_rules,
        )

        offensive_possible_target_hp = get_stat(
            opponent,
            "HP",
            AVERAGE_OPPONENT_IV,
        )
        (
            offensive_possible_min_damage,
            offensive_possible_max_damage,
        ) = calculate_damage_range(
            pokemon,
            opponent,
            best_move,
            items,
            ability_rules,
            defender_opponent_iv_override=AVERAGE_OPPONENT_IV,
        )

        (
            incoming_min_damage,
            incoming_max_damage,
        ) = calculate_damage_range(
            opponent,
            pokemon,
            worst_move,
            items,
            ability_rules,
        )

        team_member_hp = get_stat(pokemon, "HP")
        incoming_hp_ratio = (
            (
                incoming_min_damage + incoming_max_damage
            )
            / 2
            / team_member_hp
            if (
                incoming_min_damage is not None
                and incoming_max_damage is not None
                and team_member_hp > 0
            )
            else None
        )

        effective_team_speed = (
            pokemon.get("SPE", 0)
            * get_item_speed_multiplier(
                pokemon,
                items,
            )
        )

        team_moves_second = (
            effective_team_speed
            < opponent_spe
        )

        # Survival OHKO only appears when the team member moves second
        # and the opponent's minimum modeled roll does not KO first.
        likely_survives_first_hit = (
            incoming_min_damage is None
            or incoming_min_damage < team_member_hp
        )

        attacker_moves = get_moves(
            pokemon,
            moves_data,
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
            dmax_note,
            items,
            attacker_moves,
            offensive_min_damage,
            offensive_max_damage,
            offensive_target_hp,
            offensive_possible_min_damage,
            offensive_possible_max_damage,
            offensive_possible_target_hp,
            incoming_min_damage,
            incoming_max_damage,
            team_member_hp,
        )

        incoming_type_multiplier = get_type_multiplier(
            worst_move["Type"],
            [
                pokemon.get("Type1"),
                pokemon.get("Type2"),
            ],
        )

        incoming_multiplier = calculate_incoming_multiplier(
            opponent,
            pokemon,
            worst_move,
            items,
            ability_rules,
        )

        offensive_type_multiplier = get_type_multiplier(
            best_move["Type"],
            [
                opponent.get("Type1"),
                opponent.get("Type2"),
            ],
        )

        offensive_multiplier = calculate_offensive_multiplier(
            pokemon,
            opponent,
            best_move,
            items,
            ability_rules,
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
            "Best Move Type Multiplier": round(
                offensive_type_multiplier,
                2,
            ),
            "Best Move Multiplier": round(offensive_multiplier, 2),
            "Worst Incoming Move": worst_move["Move"],
            "Worst Incoming Move Type": worst_move.get("Type"),
            "Worst Incoming Move Category": worst_move.get("Category"),
            "Incoming Type Multiplier": round(
                incoming_type_multiplier,
                2,
            ),
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
                dmax_note,
                items,
                attacker_moves,
                offensive_min_damage,
                offensive_max_damage,
                offensive_target_hp,
                offensive_possible_min_damage,
                offensive_possible_max_damage,
                offensive_possible_target_hp,
                incoming_min_damage,
                incoming_max_damage,
                team_member_hp,
            )
        })

    if not results:
        return []

    return sorted(
        results,
        key=lambda row: row["Ratio"],
        reverse=True
    )