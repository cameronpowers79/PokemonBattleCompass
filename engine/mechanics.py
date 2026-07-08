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


def get_stab_multiplier(move_type, attacker_types, attacker=None, ability_rules=None):
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

        if rule.get("Effect") == "STABBoost" and rule.get("TargetType") == "STAB":
            return rule.get("Modifier", 1.5)

    return 1.5

def get_item_multiplier(item_name, move, items):
    if not item_name:
        return 1

    for item in items:
        if item.get("Item") != item_name:
            continue

        if item.get("EffectType") != "DamageMultiplier":
            continue

        if item.get("AppliesTo") != "Offense":
            continue

        move_type_affected = item.get("MoveTypeAffected")
        move_category_affected = item.get("MoveCategoryAffected")

        type_matches = (
            move_type_affected in [None, "None", move.get("Type")]
        )

        category_matches = (
            move_category_affected in [None, "None", move.get("Category")]
        )

        if type_matches and category_matches:
            return item.get("Multiplier", 1)

    return 1

def get_ability_multiplier(defender, move, ability_rules, effectiveness=1):
    ability_name = defender.get("Ability")

    if not ability_name:
        return 1

    for rule in ability_rules:
        if rule.get("Ability") != ability_name:
            continue

        effect = rule.get("Effect")
        target_type = rule.get("TargetType")
        modifier = rule.get("Modifier", 1)

        if effect == "Immunity" and target_type == move.get("Type"):
            return modifier

        if effect == "Reduction":
            if target_type == move.get("Type"):
                return modifier

            if target_type == "SuperEffective" and effectiveness > 1:
                return modifier

    return 1

def get_attack_stat_multiplier(attacker, move, ability_rules):
    ability_name = attacker.get("Ability")

    if not ability_name:
        return 1

    for rule in ability_rules:
        if rule.get("Ability") != ability_name:
            continue

        if rule.get("Effect") != "AttackBoost":
            continue

        if rule.get("TargetType") == move.get("Category"):
            return rule.get("Modifier", 1)

    return 1

def get_attack_reduction_multiplier(attacker, defender, move, ability_rules):
    defender_ability = defender.get("Ability")

    if not defender_ability:
        return 1

    for rule in ability_rules:
        if rule.get("Ability") != defender_ability:
            continue

        if rule.get("Effect") != "AttackReduction":
            continue

        if rule.get("TargetType") == move.get("Category"):
            return rule.get("Modifier", 1)

    return 1

def get_move_power_multiplier(attacker, move, ability_rules):
    ability_name = attacker.get("Ability")

    if not ability_name:
        return 1

    for rule in ability_rules:
        if rule.get("Ability") != ability_name:
            continue

        if rule.get("Effect") != "PowerBoost":
            continue

        if rule.get("TargetType") == "LowPower" and move.get("Power", 0) <= 60:
            return rule.get("Modifier", 1)

    return 1