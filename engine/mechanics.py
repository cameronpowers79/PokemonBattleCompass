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


def get_stab_multiplier(move_type, attacker_types):
    if move_type in attacker_types:
        return 1.5

    return 1

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

def get_ability_multiplier(defender, move, ability_rules):
    ability_name = defender.get("Ability")

    if not ability_name:
        return 1

    for rule in ability_rules:
        if rule.get("Ability") != ability_name:
            continue

        if rule.get("Effect") != "Immunity":
            continue

        if rule.get("TargetType") == move.get("Type"):
            return rule.get("Modifier", 0)

    return 1