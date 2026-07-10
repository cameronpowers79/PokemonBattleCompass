import streamlit as st

from engine.data_loader import load_json, save_json
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
from ui.constants import TYPE_COLORS
from ui.rendering import (
    get_badge_img_html,
    get_sprite_img_html,
)
from ui.styles import apply_app_styles


st.set_page_config(
    page_title="Pokémon Battle Compass Alpha",
    layout="wide"
)

apply_app_styles()

def get_move_metadata(move_name):
    for move in moves_data:
        if move.get("Move") == move_name:
            return move

    return None


def apply_move_metadata(pokemon):
    for slot in range(1, 5):
        move_name = pokemon.get(f"Move{slot}")
        move = get_move_metadata(move_name)

        if not move:
            continue

        pokemon[f"Move{slot}Type"] = move.get("Type")
        pokemon[f"Move{slot}Power"] = move.get("Power")
        pokemon[f"Move{slot}Category"] = move.get("Category")
        pokemon[f"Move{slot}Accuracy"] = move.get("Accuracy")

    return pokemon

def render_my_team_editor(team_data):
    st.subheader("Manage My Team")

    st.caption(
        "Edit your current party. Changes are not saved until "
        "you click Save Team."
    )

    editable_columns = [
        "Pokemon",
        "Type1",
        "Type2",
        "Level",
        "HP",
        "ATK",
        "DEF",
        "SPA",
        "SPD",
        "SPE",
        "Move1",
        "Move2",
        "Move3",
        "Move4",
        "Ability",
        "Held Item",
    ]

    editable_team = [
        {
            column: pokemon.get(column)
            for column in editable_columns
        }
        for pokemon in team_data
    ]

    move_options = sorted({
        move.get("Move")
        for move in moves_data
        if move.get("Move")
    })

    edited_team = st.data_editor(
        editable_team,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="team_editor",
        column_config={
            "Move1": st.column_config.SelectboxColumn(
                "Move1",
                options=move_options
            ),
            "Move2": st.column_config.SelectboxColumn(
                "Move2",
                options=move_options
            ),
            "Move3": st.column_config.SelectboxColumn(
                "Move3",
                options=move_options
            ),
            "Move4": st.column_config.SelectboxColumn(
                "Move4",
                options=move_options
            ),
        }
    )

    save_clicked = st.button(
        "💾 Save Team",
        type="primary",
        key="save_team_button"
    )

    if save_clicked:
        saved_team = []

        for original_pokemon, edited_pokemon in zip(
            team_data,
            edited_team
        ):
            merged_pokemon = dict(original_pokemon)

            for column in editable_columns:
                merged_pokemon[column] = edited_pokemon.get(column)

            saved_team.append(
                apply_move_metadata(merged_pokemon)
            )

        save_json("team_data", saved_team)
        st.success("Team saved!")

    st.caption(
        "Only modeled held items affect scores. If an item "
        "should improve scores but does not, check the spelling."
    )

    st.divider()

    st.subheader("Pokémon Details")

    pokemon_names = [
        pokemon.get("Pokemon")
        for pokemon in edited_team
        if pokemon.get("Pokemon")
    ]

    selected_pokemon_name = st.selectbox(
        "Select Pokémon",
        pokemon_names,
        key="team_detail_selector"
    )

    selected_pokemon = next(
        (
            pokemon
            for pokemon in edited_team
            if pokemon.get("Pokemon") == selected_pokemon_name
        ),
        None
    )

    if selected_pokemon:
        render_selected_pokemon_details(selected_pokemon)


def render_selected_pokemon_details(pokemon):
    type_badges = "".join(
        get_badge_img_html(pokemon_type, height=22)
        for pokemon_type in [
            pokemon.get("Type1"),
            pokemon.get("Type2"),
        ]
        if pokemon_type
    )

    stat_names = ["HP", "ATK", "DEF", "SPA", "SPD", "SPE"]
    stat_scale_max = 300

    stat_values = {
        stat: pokemon.get(stat) or 0
        for stat in stat_names
    }

    stat_css_classes = {
        "HP": "hp",
        "ATK": "atk",
        "DEF": "def",
        "SPA": "spa",
        "SPD": "spd",
        "SPE": "spe",
    }

    stats_html = "".join(
        (
            "<div class='team-stat-row'>"
            f"<div class='team-stat-label'>{stat}</div>"
            "<div class='team-stat-track'>"
            f"<div class='team-stat-fill "
            f"team-stat-fill-{stat_css_classes[stat]}' "
            f"style='width:{min(100, max(1, stat_values[stat] / stat_scale_max * 100)):.1f}%;'>"
            "</div>"
            "</div>"
            f"<div class='team-stat-value'>{stat_values[stat]}</div>"
            "</div>"
        )
        for stat in stat_names
    )

    move_cards = []

    for slot in range(1, 5):
        move_name = pokemon.get(f"Move{slot}")

        if not move_name:
            move_cards.append(
                "<div class='team-move' "
                "style='background: rgba(255,255,255,0.055);'>"
                "<span class='team-move-name'>Empty move slot</span>"
                "</div>"
            )
            continue

        move = move_lookup.get(move_name)
        move_type = move.get("Type") if move else None
        background = TYPE_COLORS.get(move_type, "#666666")

        badge = (
            get_badge_img_html(move_type, height=18)
            if move_type
            else ""
        )

        move_cards.append(
            "<div class='team-move' "
            f"style='background: linear-gradient("
            f"180deg, {background} 0%, {background}DD 60%, {background}BB 100%);'>"
            f"<span class='team-move-name'>{move_name}</span>"
            f"<span class='team-move-badge'>{badge}</span>"
            "</div>"
        )

    moves_html = "".join(move_cards)

    html = (
        "<div class='team-detail-card'>"

        "<div class='team-detail-header'>"
        f"{get_sprite_img_html(pokemon.get('Pokemon'), size=72)}"
        f"<div class='team-detail-name'>{pokemon.get('Pokemon', 'Unknown')}</div>"
        f"<div class='type-badge-row'>{type_badges}</div>"
        f"<div class='team-detail-level'>Lv. {pokemon.get('Level', '—')}</div>"
        "</div>"

        "<div class='team-detail-section-title'>Stats</div>"
        f"<div class='team-stat-list'>{stats_html}</div>"

        "<div class='team-detail-section-title'>Moveset</div>"
        f"<div class='team-move-grid'>{moves_html}</div>"

        "<div class='team-detail-footer'>"
        "<div class='team-detail-field'>"
        "<div class='team-detail-field-label'>Ability</div>"
        f"<div>{pokemon.get('Ability') or '—'}</div>"
        "</div>"

        "<div class='team-detail-field'>"
        "<div class='team-detail-field-label'>Held Item</div>"
        f"<div>{pokemon.get('Held Item') or '—'}</div>"
        "</div>"
        "</div>"

        "</div>"
    )

    st.markdown(html, unsafe_allow_html=True)        

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

move_lookup = {
    move["Move"]: move
    for move in moves_data
    if move.get("Move")
}


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
    render_my_team_editor(team_data)