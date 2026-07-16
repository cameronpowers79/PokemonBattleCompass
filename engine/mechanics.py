from engine.data_loader import load_json


ABILITY_BYPASS_NAMES = {
    "Mold Breaker",
    "Teravolt",
    "Turboblaze",
}

NON_IGNORABLE_DEFENSIVE_ABILITIES = {
    "Prism Armor",
    "Full Metal Body",
    "Shadow Shield",
}

SOUND_TAGS = {
    "sound",
    "soundbased",
    "soundmove",
}

BULLET_TAGS = {
    "bullet",
    "ballbomb",
    "ballorb",
    "bomb",
    "bulletproof",
}


def load_type_chart():
    return load_json("type_chart")


def get_type_multiplier(attack_type, defender_types):
    type_chart = load_type_chart()
    multiplier = 1

    for defender_type in defender_types:
        if defender_type:
            multiplier *= type_chart.get(
                attack_type,
                {},
            ).get(
                defender_type,
                1,
            )

    return multiplier


def normalize_mechanics_tag(value):
    if not isinstance(value, str):
        return ""

    return "".join(
        character
        for character in value.lower()
        if character.isalnum()
    )


def move_has_any_tag(move, accepted_tags):
    raw_tags = move.get("MechanicsTags")

    if not isinstance(raw_tags, list):
        return False

    normalized_tags = {
        normalize_mechanics_tag(tag)
        for tag in raw_tags
        if isinstance(tag, str)
    }

    return bool(
        normalized_tags.intersection(
            accepted_tags
        )
    )


def move_is_sound_based(move):
    return move_has_any_tag(
        move,
        SOUND_TAGS,
    )


def move_is_ball_or_bomb(move):
    return move_has_any_tag(
        move,
        BULLET_TAGS,
    )


def move_makes_contact(move):
    return move.get("MakesContact") in {
        True,
        "TRUE",
        "True",
        "Yes",
        "Y",
        1,
    }


def attacker_ignores_defender_ability(
    attacker,
    defender,
    ability_rules,
):
    if not attacker:
        return False

    attacker_ability = attacker.get("Ability")
    defender_ability = defender.get("Ability")

    if (
        not attacker_ability
        or defender_ability
        in NON_IGNORABLE_DEFENSIVE_ABILITIES
    ):
        return False

    if attacker_ability in ABILITY_BYPASS_NAMES:
        return True

    return any(
        rule.get("Ability") == attacker_ability
        and rule.get("Effect") == "AbilityBypass"
        for rule in ability_rules
    )


def get_stab_multiplier(
    move_type,
    attacker_types,
    attacker=None,
    ability_rules=None,
):
    if move_type not in attacker_types:
        return 1

    if attacker is None:
        return 1.5

    if ability_rules is None:
        ability_rules = []

    ability_name = attacker.get("Ability")

    for rule in ability_rules:
        if rule.get("Ability") != ability_name:
            continue

        if (
            rule.get("Effect") == "STABBoost"
            and rule.get("TargetType") == "STAB"
        ):
            return rule.get(
                "Modifier",
                1.5,
            )

    return 1.5


def get_item_multiplier(
    item_name,
    move,
    items,
):
    if not item_name:
        return 1

    for item in items:
        if item.get("Item") != item_name:
            continue

        if item.get("EffectType") != "DamageMultiplier":
            continue

        if item.get("AppliesTo") != "Offense":
            continue

        move_type_affected = item.get(
            "MoveTypeAffected"
        )
        move_category_affected = item.get(
            "MoveCategoryAffected"
        )

        type_matches = (
            move_type_affected
            in [
                None,
                "None",
                move.get("Type"),
            ]
        )

        category_matches = (
            move_category_affected
            in [
                None,
                "None",
                move.get("Category"),
            ]
        )

        if type_matches and category_matches:
            return item.get(
                "Multiplier",
                1,
            )

    return 1


def ability_rule_applies(
    rule,
    move,
    effectiveness,
):
    effect = rule.get("Effect")
    target_type = rule.get("TargetType")
    move_type = move.get("Type")
    move_category = move.get("Category")

    if effect == "Immunity":
        if target_type == move_type:
            return True

        if (
            target_type == "Sound"
            and move_is_sound_based(move)
        ):
            return True

        if (
            target_type == "Bullet"
            and move_is_ball_or_bomb(move)
        ):
            return True

        if (
            target_type == "NotSuperEffective"
            and effectiveness <= 1
        ):
            return True

        return False

    if effect == "Reduction":
        if target_type == move_type:
            return True

        if (
            target_type == "SuperEffective"
            and effectiveness > 1
        ):
            return True

        if target_type == move_category:
            return True

        if (
            target_type == "Contact"
            and move_makes_contact(move)
        ):
            return True

        return False

    if effect == "Vulnerability":
        if target_type == move_type:
            return True

        if target_type == move_category:
            return True

        if (
            target_type == "Contact"
            and move_makes_contact(move)
        ):
            return True

    return False


def get_ability_multiplier(
    defender,
    move,
    ability_rules,
    effectiveness=1,
    attacker=None,
):
    ability_name = defender.get("Ability")

    if not ability_name:
        return 1

    if attacker_ignores_defender_ability(
        attacker,
        defender,
        ability_rules,
    ):
        return 1

    multiplier = 1

    for rule in ability_rules:
        if rule.get("Ability") != ability_name:
            continue

        if not ability_rule_applies(
            rule,
            move,
            effectiveness,
        ):
            continue

        modifier = rule.get(
            "Modifier",
            1,
        )

        if rule.get("Effect") == "Immunity":
            return modifier

        multiplier *= modifier

    return multiplier


def get_attack_stat_multiplier(
    attacker,
    move,
    ability_rules,
):
    ability_name = attacker.get("Ability")

    if not ability_name:
        return 1

    for rule in ability_rules:
        if rule.get("Ability") != ability_name:
            continue

        if rule.get("Effect") != "AttackBoost":
            continue

        if rule.get("TargetType") == move.get("Category"):
            return rule.get(
                "Modifier",
                1,
            )

    return 1


def get_attack_reduction_multiplier(
    attacker,
    defender,
    move,
    ability_rules,
):
    defender_ability = defender.get("Ability")

    if not defender_ability:
        return 1

    for rule in ability_rules:
        if rule.get("Ability") != defender_ability:
            continue

        if rule.get("Effect") != "AttackReduction":
            continue

        if rule.get("TargetType") == move.get("Category"):
            return rule.get(
                "Modifier",
                1,
            )

    return 1


def get_move_power_multiplier(
    attacker,
    move,
    ability_rules,
):
    ability_name = attacker.get("Ability")

    if not ability_name:
        return 1

    for rule in ability_rules:
        if rule.get("Ability") != ability_name:
            continue

        if rule.get("Effect") != "PowerBoost":
            continue

        if (
            rule.get("TargetType") == "LowPower"
            and move.get("Power", 0) <= 60
        ):
            return rule.get(
                "Modifier",
                1,
            )

    return 1
