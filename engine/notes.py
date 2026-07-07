def build_notes(best_score, worst_score, ratio):
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