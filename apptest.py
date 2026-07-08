import streamlit as st
from engine.data_loader import load_json
from engine.calculations import find_best_team_member, evaluate_team_matchups

st.set_page_config(
    page_title="Pokémon Battle Compass Alpha",
    layout="wide"
)

NOTE_ICONS = {
    "info": "ℹ️",
    "opportunity": "💡",
    "caution": "⚠️",
    "warning": "🚨",
}


def render_battle_notes(notes):
    if not notes:
        st.caption("No special notes.")
        return

    for note in notes:
        icon = NOTE_ICONS.get(note.get("category"), "•")
        st.write(f"{icon} {note.get('text')}")


st.title("Pokémon Battle Compass")
st.caption("Alpha UI preview — advice first, spreadsheet goblins later.")

team_data = load_json("team_data")
opponents = load_json("opponents")
items = load_json("items")
ability_rules = load_json("ability_rules")
moves_data = load_json("moves")

with st.sidebar:
    st.header("Battle Setup")

    trainer_names = sorted({
        row["Trainer"]
        for row in opponents
        if row.get("Trainer")
    })

    selected_trainer = st.selectbox("Trainer", trainer_names)

    battles = sorted({
        row["Battle"]
        for row in opponents
        if row.get("Trainer") == selected_trainer and row.get("Battle")
    })

    selected_battle = st.selectbox("Battle", battles)

battle_opponents = [
    row
    for row in opponents
    if row.get("Trainer") == selected_trainer
    and row.get("Battle") == selected_battle
]

opponent_names = [
    row["Pokemon"]
    for row in battle_opponents
    if row.get("Pokemon")
]

selected_opponent_name = st.selectbox(
    "Opponent Pokémon",
    opponent_names
)

selected_opponent = next(
    row
    for row in battle_opponents
    if row["Pokemon"] == selected_opponent_name
)

recommended_pokemon, recommendation_result, why = find_best_team_member(
    team_data,
    selected_opponent,
    items,
    ability_rules,
    moves_data
)

best_move, best_score, worst_move, worst_score, ratio = recommendation_result

matchup_results = evaluate_team_matchups(
    team_data,
    selected_opponent,
    items,
    ability_rules,
    moves_data
)

top_three = matchup_results[:3]
top_notes = top_three[0].get("Battle Notes", [])

st.divider()

left, right = st.columns([1.2, 1])

with left:
    st.subheader("⭐ Recommendation")
    st.markdown(f"## {recommended_pokemon['Pokemon']}")
    st.write(f"**Best move:** {best_move['Move']}")
    st.write(f"**Why:** {why}")

    st.markdown("### Battle Notes")
    render_battle_notes(top_notes)

with right:
    st.subheader("Battle Snapshot")
    st.metric("Ratio", round(ratio, 2))
    st.metric("Best MoveScore", round(best_score, 2))
    st.metric("Incoming Worst", round(worst_score, 2))
    st.write(
        f"**Worst incoming move:** {worst_move['Move']} "
        f"({worst_move.get('Category', 'Unknown')})"
    )

st.divider()

st.subheader("Top Options")

for index, row in enumerate(top_three, start=1):
    with st.container(border=True):
        st.markdown(f"### {index}. {row['Pokemon']}")
        st.write(f"**Best move:** {row['Best Move']}")
        st.write(f"**Ratio:** {row['Ratio']}")

        notes = row.get("Battle Notes", [])
        render_battle_notes(notes)

analysis_rows = [
    {
        key: value
        for key, value in row.items()
        if key != "Battle Notes"
    }
    for row in matchup_results
]

with st.expander("Full Analysis"):
    st.dataframe(analysis_rows)