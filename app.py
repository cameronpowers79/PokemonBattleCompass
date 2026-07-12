import streamlit as st

from ui.rendering import (
    get_sprite_img_html,
    image_to_base64,
)
from engine.data_loader import load_json
from engine.calculations import (
    find_best_team_member,
    evaluate_team_matchups,
)
from ui.cards import (
    get_matchup_strength,
    render_battle_notes,
    render_battle_snapshot,
    render_opponent_card,
    render_recommendation_card,
)
from ui.styles import apply_app_styles
from ui.team import render_my_team_editor

st.set_page_config(
    page_title="Pokémon Battle Compass Alpha",
    page_icon="assets/raw/BattleCompassLogo.png",
    layout="wide",
)

apply_app_styles()        

logo_encoded = image_to_base64(
    "assets/raw/BattleCompassLogo.png"
)

wordmark_encoded = image_to_base64(
    "assets/raw/WordMarkLogoBlock.png"
)

st.markdown(
    (
        "<div class='app-branding'>"
        f"<img src='data:image/png;base64,{logo_encoded}' "
        "class='brand-logo' alt='Battle Compass logo'>"
        f"<img src='data:image/png;base64,{wordmark_encoded}' "
        "class='brand-wordmark' alt='Pokémon Battle Compass'>"
        "<div class='app-tagline'>"
        "Navigate every matchup with confidence."
        "</div>"
        "</div>"
    ),
    unsafe_allow_html=True,
)

team_data = load_json("team_data")
opponents = load_json("opponents")
items = load_json("items")
ability_rules = load_json("ability_rules")
moves_data = load_json("moves")

def opponent_row_matches_starter(row, selected_starter):
    player_starter = row.get("PlayerStarter")

    return (
        not player_starter
        or player_starter == selected_starter
    )

def render_selectbox_label(label_text):
    st.markdown(
        f"<div class='battle-setting-label'>{label_text}</div>",
        unsafe_allow_html=True,
    )

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

# Preserve Battle Compass selections while its widgets are not rendered.
for state_key in [
    "player_starter",
    "selected_trainer",
    "selected_battle",
    "selected_opponent",
]:
    if state_key in st.session_state:
        st.session_state[state_key] = st.session_state[state_key]

st.divider()


# ---------------------------------------------------------
# Battle Compass
# ---------------------------------------------------------

if active_view == "Battle Compass":

    st.subheader("Battle Settings")

    starter_filtered_opponents = []

    starter_col, trainer_col, battle_col = st.columns(3)

    with starter_col:
        render_selectbox_label("Your Starter")

        selected_starter = st.selectbox(
            "Choose Your Starter",
            options=["Grookey", "Scorbunny", "Sobble"],
            index=1,
            key="player_starter",
            label_visibility="collapsed",
        )

    starter_filtered_opponents = [
        row
        for row in opponents
        if opponent_row_matches_starter(
            row,
            selected_starter
        )
    ]

    trainer_names = sorted({
        row["Trainer"]
        for row in starter_filtered_opponents
        if row.get("Trainer")
    })

    with trainer_col:
        render_selectbox_label("Trainer")

        selected_trainer = st.selectbox(
            "Trainer",
            trainer_names,
            key="selected_trainer",
            label_visibility="collapsed",
        )

    trainer_rows = [
        row
        for row in starter_filtered_opponents
        if row.get("Trainer") == selected_trainer
    ]

    battle_order_lookup = {}

    for row in trainer_rows:
        battle_name = row.get("Battle")

        if not battle_name:
            continue

        battle_order = row.get("BattleOrder", 9999)

        if battle_name not in battle_order_lookup:
            battle_order_lookup[battle_name] = battle_order
        else:
            battle_order_lookup[battle_name] = min(
                battle_order_lookup[battle_name],
                battle_order
            )

    battles = sorted(
        battle_order_lookup,
        key=lambda battle_name: (
            battle_order_lookup[battle_name],
            battle_name
        )
    )

    with battle_col:
        render_selectbox_label("Battle")

        selected_battle = st.selectbox(
            "Battle",
            battles,
            key="selected_battle",
            label_visibility="collapsed",
        )

    battle_opponents = sorted(
        [
            row
            for row in starter_filtered_opponents
            if (
                row.get("Trainer") == selected_trainer
                and row.get("Battle") == selected_battle
            )
        ],
        key=lambda row: row.get("Slot", 9999)
    )

    opponent_names = [
        row["Pokemon"]
        for row in battle_opponents
        if row.get("Pokemon")
    ]

    render_selectbox_label("Opponent Pokémon")

    selected_opponent_name = st.selectbox(
        "Opponent Pokémon",
        opponent_names,
        key="selected_opponent",
        label_visibility="collapsed",
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
            is_immune = row.get("Is Immune", False)

            strength_label, _, strength_class = get_matchup_strength(
                row["Ratio"],
                is_immune
            )

            option_sprite_html = get_sprite_img_html(
                row["Pokemon"],
                size=40,
                gender=row.get("Gender"),
                use_texture=False,
            )

            st.markdown(
                (
                    "<div class='other-option-heading'>"
                    f"<span class='other-option-rank'>{index}.</span>"
                    f"{option_sprite_html}"
                    f"<span class='other-option-name'>{row['Pokemon']}</span>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
            st.write(f"**Best move:** {row['Best Move']}")

            ratio_html = (
                ""
                if is_immune
                else (
                    f"<span class='other-option-ratio'>"
                    f"Matchup Ratio: {row['Ratio']}"
                    "</span>"
                )
            )

            st.markdown(
                (
                    "<div class='other-option-matchup-line'>"
                    f"<span class='other-option-strength "
                    f"matchup-label-{strength_class}'>"
                    f"{strength_label}"
                    "</span>"
                    f"{ratio_html}"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

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