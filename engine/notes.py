# ---------- Tactical helpers ----------

def get_tactical_ability_notes(attacker, defender, best_move, best_score, ability_rules):
    notes = []
    defender_ability = defender.get("Ability")

    if not defender_ability:
        return notes

    for rule in ability_rules:
        if rule.get("Ability") != defender_ability:
            continue

        if rule.get("Effect") != "Tactical":
            continue

        target_type = rule.get("TargetType")

        if target_type == "OHKO" and best_score >= 260:
            notes.append("Sturdy may prevent OHKO")

        if target_type == "Contact" and best_move.get("MakesContact"):
            notes.append(rule.get("Notes"))

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
    ability_rules=None
):
    if ability_rules is None:
        ability_rules = []

    notes = []

    if worst_score == 0:
        notes.append("Immune to opponent's attacks")

    if best_score >= 260:
        notes.append("Likely OHKO")
    elif best_score >= 220:
        notes.append("Possible OHKO")

    notes.extend(
        get_tactical_ability_notes(
            attacker,
            defender,
            best_move,
            best_score,
            ability_rules
        )
    )

    if worst_score >= 260:
        notes.append("Likely Incoming OHKO")
    elif worst_score >= 220:
        notes.append("Possible Incoming OHKO")

    return "; ".join(notes)


# ---------- Recommendation text ----------

def build_why_explanation(team_size, recommended_pokemon, best_score, worst_score, ratio):
    if team_size == 1:
        return "Only Pokemon available"

    if worst_score == 0:
        ability = recommended_pokemon.get("Ability")

        if ability:
            return f"{ability} grants full immunity"

        return "Immune to all opponent's attacks"

    if ratio >= 5:
        return "Overwhelming offensive advantage"

    if best_score >= 260 and ratio >= 2:
        return "Strongest attack against this opponent"

    if worst_score <= 100 and ratio >= 1:
        return "Best durability against this opponent"

    if ratio >= 1:
        return "Best balance of damage and durability"

    return "Highest overall matchup rating"