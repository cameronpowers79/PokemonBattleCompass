import streamlit as st

from engine.moves import apply_move_metadata
from ui.constants import TYPE_COLORS
from ui.rendering import (
    get_badge_img_html,
    get_sprite_img_html,
)

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

    def parse_stat_value(value):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0


    stat_values = {
        stat: parse_stat_value(pokemon.get(stat))
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
        f"{get_sprite_img_html(
            pokemon.get("Pokemon"),
            size=72,
            texture_size=144,
            gender=pokemon.get("Gender")
        )}"
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

def parse_optional_int(value):
    if value is None or value == "":
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None

def render_my_team_editor(team_data, moves_data):
    st.subheader("Manage My Team")

    st.caption(
    "Edit your current party. Click Save Team to apply changes "
    "to your current browser session."
)

    editable_columns = [
        "Pokemon",
        "Gender",
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
            "Level": st.column_config.NumberColumn(
                "Level",
                min_value=1,
                step=1,
                format="%d"
                ),
            "HP": st.column_config.NumberColumn(
                "HP",
                min_value=0,
                step=1,
                format="%d"
            ),
            "ATK": st.column_config.NumberColumn(
                "ATK",
                min_value=0,
                step=1,
                format="%d"
            ),
            "DEF": st.column_config.NumberColumn(
                "DEF",
                min_value=0,
                step=1,
                format="%d"
            ),
            "SPA": st.column_config.NumberColumn(
                "SPA",
                min_value=0,
                step=1,
                format="%d"
            ),
            "SPD": st.column_config.NumberColumn(
                "SPD",
                min_value=0,
                step=1,
                format="%d"
            ),
            "SPE": st.column_config.NumberColumn(
                "SPE",
                min_value=0,
                step=1,
                format="%d"
            ),
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
    "💾 Apply Team Changes",
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

            numeric_columns = {
                "Level",
                "HP",
                "ATK",
                "DEF",
                "SPA",
                "SPD",
                "SPE",
            }

            for column in editable_columns:
                value = edited_pokemon.get(column)

                if column in numeric_columns:
                    value = parse_optional_int(value)

                merged_pokemon[column] = value

            saved_team.append(
                apply_move_metadata(
                    merged_pokemon,
                    moves_data
                )
            )

        st.session_state["team_data"] = saved_team
        st.success("Team saved for this session!")

    st.caption(
        "Only modeled held items affect Move Scores. If a held item "
        "should improve a score but does not, verify the item name is "
        "spelled correctly. A blue ⊕ beside the Move Score indicates "
        "an active held item bonus. Tap it to see the bonus breakdown."
    )

    st.divider()

    st.subheader("Pokémon Details")

    valid_pokemon = [
        pokemon
        for pokemon in edited_team
        if (
            isinstance(pokemon.get("Pokemon"), str)
            and pokemon.get("Pokemon").strip()
        )
    ]

    if not valid_pokemon:
        st.info(
            "No Pokémon are currently loaded. Add your team above "
            "or restore a save file."
        )
        return

    pokemon_names = [
        pokemon["Pokemon"]
        for pokemon in valid_pokemon
    ]

    selected_pokemon_name = st.selectbox(
        "Select Pokémon",
        pokemon_names,
        key="team_detail_selector"
    )

    selected_pokemon = next(
        pokemon
        for pokemon in valid_pokemon
        if pokemon["Pokemon"] == selected_pokemon_name
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