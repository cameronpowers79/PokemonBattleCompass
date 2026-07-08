def build_notes(attacker, defender, best_move, best_score, worst_move, worst_score, ratio):
    notes = []

    if worst_score == 0:
        notes.append("Immune to opponent's attacks")

    if best_score >= 260:
        notes.append("Likely OHKO")
    elif best_score >= 220:
        notes.append("Possible OHKO")

    if worst_score >= 260:
        notes.append("Likely Incoming OHKO")
    elif worst_score >= 220:
        notes.append("Possible Incoming OHKO")

    return "; ".join(notes)


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