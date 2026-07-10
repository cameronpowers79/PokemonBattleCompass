import streamlit as st

from engine.data_loader import load_json
from engine.calculations import (
    find_best_team_member,
    evaluate_team_matchups,
)
from ui.cards import (
    render_battle_notes,
    render_battle_snapshot,
    render_opponent_card,
    render_recommendation_card,
)
from ui.styles import apply_app_styles
from ui.team import render_my_team_editor

st.set_page_config(
    page_title="Pokémon Battle Compass Alpha",
    layout="wide"
)

apply_app_styles()        

st.title("Pokémon Battle Compass")

st.markdown(
    (
        "<div class='app-tagline'>"
        "Navigate every matchup with confidence."
        "</div>"
    ),
    unsafe_allow_html=True,
)

team_data = load_json("team_data")
opponents = load_json("opponents")
items = load_json("items")
ability_rules = load_json("ability_rules")
moves_data = load_json("moves")


# ---------------------------------------------------------
# Sidebar: battle selection
# ---------------------------------------------------------

with st.sidebar:
    st.header("Battle Setup")

    trainer_names = sorted({
        row["Trainer"]
        for row in opponents
        if row.get("Trainer")
    })

    selected_trainer = st.selectbox(
        "Trainer",
        trainer_names
    )

    battles = sorted({
        row["Battle"]
        for row in opponents
        if (
            row.get("Trainer") == selected_trainer
            and row.get("Battle")
        )
    })

    selected_battle = st.selectbox(
        "Battle",
        battles
    )


# ---------------------------------------------------------
# Available opponents for selected battle
# ---------------------------------------------------------

battle_opponents = [
    row
    for row in opponents
    if (
        row.get("Trainer") == selected_trainer
        and row.get("Battle") == selected_battle
    )
]

opponent_names = [
    row["Pokemon"]
    for row in battle_opponents
    if row.get("Pokemon")
]


# ---------------------------------------------------------
# Main navigation
# ---------------------------------------------------------

active_view = st.segmented_control(
    "Main navigation",
    options=["Battle Compass", "My Team"],
    default="Battle Compass",
    key="main_view",
    label_visibility="collapsed",
    width="stretch",
    required=True,
)

st.divider()


# ---------------------------------------------------------
# Battle Compass
# ---------------------------------------------------------

if active_view == "Battle Compass":

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

    recommended_result = next(
        row
        for row in matchup_results
        if row["Pokemon"] == recommended_pokemon["Pokemon"]
    )

    other_options = [
        row
        for row in matchup_results
        if row["Pokemon"] != recommended_pokemon["Pokemon"]
    ]

    top_three = other_options[:2]

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

    left, right = st.columns([1.2, 1])

    with left:
        render_recommendation_card(
            recommended_pokemon,
            best_move,
            ratio,
            why,
            recommended_result
        )

    with right:
        render_opponent_card(selected_opponent)

        render_battle_snapshot(
            best_score,
            worst_score,
            worst_move,
            recommended_result
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
                    "Incoming Effectiveness",
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


# ---------------------------------------------------------
# My Team
# ---------------------------------------------------------

elif active_view == "My Team":
    render_my_team_editor(
        team_data,
        moves_data
    )