import streamlit as st

from engine.data_loader import save_json
from ui.constants import TYPE_COLORS
from ui.rendering import (
    get_badge_img_html,
    get_sprite_img_html,
)


def get_move_metadata(move_name, moves_data):
    for move in moves_data:
        if move.get("Move") == move_name:
            return move

    return None


def apply_move_metadata(pokemon, moves_data):
    for slot in range(1, 5):
        move_name = pokemon.get(f"Move{slot}")
        move = get_move_metadata(move_name, moves_data)

        if not move:
            continue

        pokemon[f"Move{slot}Type"] = move.get("Type")
        pokemon[f"Move{slot}Power"] = move.get("Power")
        pokemon[f"Move{slot}Category"] = move.get("Category")
        pokemon[f"Move{slot}Accuracy"] = move.get("Accuracy")

    return pokemon


def render_selected_pokemon_details(pokemon, move_lookup):
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
            f"style='width:"
            f"{min(100, max(1, stat_values[stat] / stat_scale_max * 100)):.1f}%;'>"
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
            f"180deg, {background} 0%, "
            f"{background}DD 60%, "
            f"{background}BB 100%);'>"
            f"<span class='team-move-name'>{move_name}</span>"
            f"<span class='team-move-badge'>{badge}</span>"
            "</div>"
        )

    moves_html = "".join(move_cards)

    html = (
        "<div class='team-detail-card'>"

        "<div class='team-detail-header'>"
        f"{get_sprite_img_html(pokemon.get('Pokemon'), size=72)}"
        f"<div class='team-detail-name'>"
        f"{pokemon.get('Pokemon', 'Unknown')}"
        "</div>"
        f"<div class='type-badge-row'>{type_badges}</div>"
        f"<div class='team-detail-level'>"
        f"Lv. {pokemon.get('Level', '—')}"
        "</div>"
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


def render_my_team_editor(team_data, moves_data):
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

    move_lookup = {
        move["Move"]: move
        for move in moves_data
        if move.get("Move")
    }

    move_options = sorted(move_lookup)

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
                apply_move_metadata(
                    merged_pokemon,
                    moves_data
                )
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
        render_selected_pokemon_details(
            selected_pokemon,
            move_lookup
        )