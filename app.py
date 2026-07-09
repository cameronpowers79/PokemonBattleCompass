import streamlit as st
from engine.data_loader import load_json
from engine.calculations import find_best_team_member, evaluate_team_matchups

st.set_page_config(
    page_title="Pokémon Battle Compass Alpha",
    layout="wide"
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: "Aptos", "Segoe UI", sans-serif;
        }

        h1, h2, h3, h4,
        .stMarkdown h1,
        .stMarkdown h2,
        .stMarkdown h3,
        .stMarkdown h4 {
            font-family: "Exo 2", "Bahnschrift", "Aptos", sans-serif;
            font-weight: 700;
            letter-spacing: 0.01em;
        }

        [data-testid="stMetricValue"] {
            font-family: "Bahnschrift", "Aptos", "Segoe UI", sans-serif;
            font-weight: 500;
        }

        [data-testid="stMetricLabel"] {
            font-family: "Aptos", "Segoe UI", sans-serif;
        }

        section[data-testid="stSidebar"] {
            width: 260px !important;
        }

        section[data-testid="stSidebar"] > div {
            width: 260px !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] {
            width: 260px !important;
        }

        section[data-testid="stSidebar"] > div {
            width: 260px !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
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

def render_offensive_effectiveness(multiplier):
    if multiplier is None:
        st.caption("Effectiveness unavailable")
        return

    if multiplier == 0:
        st.error("🚫 No effect (0×)")
    elif multiplier < 1:
        st.warning(f"🟡 Not Very Effective ({multiplier:g}×)")
    elif multiplier == 1:
        st.info("⚪ Neutral (1×)")
    elif multiplier < 4:
        st.success(f"🟢 Super Effective ({multiplier:g}×)")
    else:
        st.success(f"🔥 4× Weakness ({multiplier:g}×)")


def render_defensive_effectiveness(multiplier):
    if multiplier is None:
        st.caption("Effectiveness unavailable")
        return

    if multiplier == 0:
        st.success("🛡️ No effect (0×)")
    elif multiplier < 1:
        st.success(f"🟢 Not Very Effective ({multiplier:g}×)")
    elif multiplier == 1:
        st.info("⚪ Neutral (1×)")
    elif multiplier < 4:
        st.warning(f"🔺 Super Effective ({multiplier:g}×)")
    else:
        st.error(f"🔥 4× Weakness ({multiplier:g}×)")


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

other_options = [
    row
    for row in matchup_results
    if row["Pokemon"] != recommended_pokemon["Pokemon"]
]

top_three = other_options[:2]
recommended_result = next(
    row
    for row in matchup_results
    if row["Pokemon"] == recommended_pokemon["Pokemon"]
)

top_notes = recommended_result.get("Battle Notes", [])

st.divider()

left, right = st.columns([1.2, 1])

with left:

    st.subheader("⭐ Recommended Pokémon")

    st.markdown(f"## {recommended_pokemon['Pokemon']}")

    type_line = " / ".join(
        t for t in [
            recommended_pokemon.get("Type1"),
            recommended_pokemon.get("Type2")
        ] if t
    )

    st.caption(type_line)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Best Move",
            best_move["Move"]
        )

    render_offensive_effectiveness(
        recommended_result.get("Best Move Multiplier")
)

    with col2:
        st.metric(
            "Matchup Ratio",
            round(ratio, 2)
        )

    st.markdown("### Why this Pokémon?")

    st.info(why)

    st.markdown("### Battle Notes")

    render_battle_notes(top_notes)

with right:
    st.subheader("Battle Snapshot")
    st.metric(
    "Matchup Ratio",
    round(ratio, 2)
)
    st.metric("Best MoveScore", round(best_score, 2))
    st.metric("Incoming Worst", round(worst_score, 2))
    st.write(
        f"**Worst incoming move:** {worst_move['Move']} "
        f"({worst_move.get('Category', 'Unknown')})"
    )
    
    render_defensive_effectiveness(
    recommended_result.get("Incoming Multiplier")
)

st.divider()

st.subheader("Other Strong Options")

for index, row in enumerate(top_three, start=1):
    with st.container(border=True):
        st.markdown(f"### {index}. {row['Pokemon']}")
        st.write(f"**Best move:** {row['Best Move']}")
        st.caption(f"Matchup Ratio: {row['Ratio']}")

        notes = row.get("Battle Notes", [])
        render_battle_notes(notes)

analysis_columns = [
    "Pokemon",
    "Best Move",
    "Best Move Multiplier",
    "Best MoveScore",
    "Worst Incoming Move",
    "Incoming Multiplier",
    "Incoming Worst Score",
    "Ratio",
    "Notes",
]

analysis_rows = [
    {
        column: row.get(column)
        for column in analysis_columns
    }
    for row in matchup_results
]

with st.expander("Full Analysis"):
    st.dataframe(
    analysis_rows,
    use_container_width=True,
    column_config={
        "Pokemon": st.column_config.TextColumn(
            width="small"
        ),

        "Best Move": st.column_config.TextColumn(
            width="small"
        ),

        "Best Move Multiplier": st.column_config.NumberColumn(
            "Effectiveness",
            format="%g×",
            width="small"
        ),

        "Best MoveScore": st.column_config.NumberColumn(
            "Move Score",
            format="%.2f",
            width="small"
        ),

        "Worst Incoming Move": st.column_config.TextColumn(
            width="medium"
        ),

        "Incoming Multiplier": st.column_config.NumberColumn(
            "Effectiveness",
            format="%g×",
            width="small"
        ),

        "Incoming Worst Score": st.column_config.NumberColumn(
            "IWS",
            format="%.2f",
            width="small"
        ),

        "Ratio": st.column_config.NumberColumn(
            format="%.2f",
            width="small"
        ),

        "Notes": st.column_config.TextColumn(
            width="large"
        ),
    },
)