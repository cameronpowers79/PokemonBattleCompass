import base64
from io import BytesIO

import streamlit as st
from PIL import Image

from engine.data_loader import load_json, save_json
from engine.calculations import (
    find_best_team_member,
    evaluate_team_matchups,
)
from ui.constants import (
    NOTE_ICONS,
    SPRITE_DIR,
    TYPE_BADGE_DIR,
    TYPE_COLORS,
)
from ui.styles import apply_app_styles


st.set_page_config(
    page_title="Pokémon Battle Compass Alpha",
    layout="wide"
)

apply_app_styles()



st.markdown(
    """
    
    """,
    unsafe_allow_html=True,
)


def image_to_base64(path, crop_transparency=False, output_size=None):
    if not crop_transparency and output_size is None:
        with open(path, "rb") as file:
            return base64.b64encode(file.read()).decode("utf-8")

    image = Image.open(path).convert("RGBA")

    if crop_transparency:
        alpha = image.getchannel("A")
        bbox = alpha.getbbox()

        if bbox:
            image = image.crop(bbox)

    if output_size:
        image.thumbnail((output_size, output_size), Image.Resampling.NEAREST)

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def get_badge_img_html(pokemon_type, height=22):
    badge = TYPE_BADGE_DIR / f"{pokemon_type}.png"

    if not badge.exists():
        return f"<span>{pokemon_type}</span>"

    encoded = image_to_base64(badge)

    return (
        f"<img "
        f"src='data:image/png;base64,{encoded}' "
        f"alt='{pokemon_type}' "
        f"class='type-badge' "
        f"style='height:{height}px;width:auto;' "
        f"/>"
    )

def get_effectiveness_text(multiplier, mode):
    if multiplier is None:
        return "Effectiveness unavailable"

    if mode == "offense":
        if multiplier == 0:
            return "🚫 No Effect (0×)"
        if multiplier < 1:
            return f"🟡 Not Very Effective ({multiplier:g}×)"
        if multiplier == 1:
            return "⚪ Neutral (1×)"
        if multiplier < 4:
            return f"🟢 Super Effective ({multiplier:g}×)"
        return f"🔥 4× Weakness ({multiplier:g}×)"

    if multiplier == 0:
        return "🛡️ No Effect (0×)"
    if multiplier < 1:
        return f"🟢 Not Very Effective ({multiplier:g}×)"
    if multiplier == 1:
        return "⚪ Neutral (1×)"
    if multiplier < 4:
        return f"🔺 Super Effective ({multiplier:g}×)"
    return f"🔥 4× Weakness ({multiplier:g}×)"


def get_effectiveness_class(multiplier, mode):
    if multiplier is None:
        return "neutral"

    if mode == "offense":
        if multiplier == 0:
            return "bad"
        if multiplier < 1:
            return "caution"
        if multiplier == 1:
            return "neutral"
        return "good"

    if multiplier == 0:
        return "good"
    if multiplier < 1:
        return "good"
    if multiplier == 1:
        return "neutral"
    if multiplier < 4:
        return "caution"
    return "bad"

def get_matchup_strength(ratio):
    """
    Classify a matchup ratio into a player-facing strength category.

    Returns:
        label: Display label
        index: Segment position from 0 to 4
        css_class: Styling class for the active category
    """
    if ratio >= 99:
        return "Immune", 4, "immune"

    if ratio >= 3:
        return "Comfortable", 3, "comfortable"

    if ratio >= 2:
        return "Favorable", 2, "favorable"

    if ratio >= 1:
        return "Competitive", 1, "competitive"

    return "Challenging", 0, "challenging"

def get_matchup_strength_html(ratio):
    label, active_index, css_class = get_matchup_strength(ratio)

    segment_classes = [
        "challenging",
        "competitive",
        "favorable",
        "comfortable",
        "immune",
    ]

    segments_html = "".join(
        (
            f"<div class='matchup-segment matchup-{segment_class} "
            f"{'matchup-segment-active' if index == active_index else ''}'>"
            f"{'<div class=\"matchup-pointer\"></div>' if index == active_index else ''}"
            "</div>"
        )
        for index, segment_class in enumerate(segment_classes)
    )

    return (
        "<div class='matchup-strength'>"
        "<div class='matchup-strength-title'>Matchup Strength</div>"
        f"<div class='matchup-meter'>{segments_html}</div>"
        f"<div class='matchup-strength-label matchup-label-{css_class}'>"
        f"{label}"
        "</div>"
        f"<div class='matchup-ratio-detail'>Ratio {ratio:.2f}</div>"
        "</div>"
    )


def render_recommendation_card(recommended_pokemon, best_move, ratio, why, recommended_result):
    type_badges = "".join(
        get_badge_img_html(pokemon_type)
        for pokemon_type in [
            recommended_pokemon.get("Type1"),
            recommended_pokemon.get("Type2"),
        ]
        if pokemon_type
    )

    offensive_multiplier = recommended_result.get("Best Move Multiplier")
    effectiveness_text = get_effectiveness_text(offensive_multiplier, "offense")
    effectiveness_class = get_effectiveness_class(offensive_multiplier, "offense")

    notes_html = ""

    for battle_note in recommended_result.get("Battle Notes", []):
        category = battle_note.get("category", "info")
        text = battle_note.get("text", "")
        icon = NOTE_ICONS.get(category, "•")

        notes_html += (
            f"<div class='battle-note note-{category}'>"
            f"<span class='note-icon'>{icon}</span>"
            f"<span>{text}</span>"
            f"</div>"
        )

    if not notes_html:
        notes_html = "<div class='battle-note note-info'>No special notes.</div>"

    matchup_strength_html = get_matchup_strength_html(ratio)

    html = (
        "<div class='recommendation-card'>"
        "<div class='card-kicker'>⭐ Recommended Pokémon</div>"
        "<div class='pokemon-header-row'>"
        f"{get_sprite_img_html(recommended_pokemon['Pokemon'], size=72)}"
        "<div class='pokemon-text-block'>"
        f"<div class='pokemon-name'>{recommended_pokemon['Pokemon']}</div>"
        f"<div class='type-badge-row'>{type_badges}</div>"
        "</div>"
        "</div>"
        "<div class='card-divider'></div>"
        "<div class='move-row'>"

        "<div class='best-move-column'>"
        "<div class='label'>Best Move</div>"
        "<div class='move-name-line'>"
        f"<span class='move-name'>{best_move['Move']}</span>"
        f"{get_badge_img_html(best_move.get('Type'), height=20)}"
        "</div>"
        f"<div class='effectiveness-pill "
        f"effectiveness-{effectiveness_class} "
        f"best-move-effectiveness'>"
        f"{effectiveness_text}"
        "</div>"
        "</div>"

        f"<div>{matchup_strength_html}</div>"

        "</div>"
        "<div class='section-title'>Why this Pokémon?</div>"
        f"<div class='why-box'>{why}</div>"
        "<div class='section-title'>Battle Notes</div>"
        f"<div class='notes-list'>{notes_html}</div>"
        "</div>"
    )

    st.markdown(html, unsafe_allow_html=True)

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

def get_move_type(move_name):
    if not move_name:
        return None

    move = move_lookup.get(move_name)
    if move:
        return move.get("Type")

    return None


def render_opponent_card(opponent):
    type_badges = "".join(
        get_badge_img_html(pokemon_type, height=20)
        for pokemon_type in [
            opponent.get("Type1"),
            opponent.get("Type2"),
        ]
        if pokemon_type
    )

    st.markdown(
        (
            "<div class='side-card'>"
            "<div class='side-card-title'>Opponent</div>"
            "<div class='pokemon-header-row'>"
            f"{get_sprite_img_html(opponent['Pokemon'], size=70, use_gmax=opponent_uses_gmax(opponent))}"
            "<div class='pokemon-text-block'>"
            f"<div class='opponent-name'>{opponent['Pokemon']}</div>"
            f"<div class='type-badge-row'>{type_badges}</div>"
            f"<div class='opponent-level'>Lv. {opponent.get('Level', '—')}</div>"
            "</div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_battle_snapshot(best_score, worst_score, worst_move, recommended_result):
    incoming_multiplier = recommended_result.get("Incoming Multiplier")

    effectiveness_text = get_effectiveness_text(incoming_multiplier, "defense")
    effectiveness_class = get_effectiveness_class(incoming_multiplier, "defense")

    st.markdown(
        (
            "<div class='side-card'>"
            "<div class='side-card-title'>Battle Snapshot</div>"
            "<div class='snapshot-grid'>"
            "<div><div class='label'>Move Score</div>"
            f"<div class='snapshot-value'>{best_score:.2f}</div></div>"
            "<div><div class='label'>Incoming Worst</div>"
            f"<div class='snapshot-value'>{worst_score:.2f}</div></div>"
            "</div>"
            "<div class='snapshot-move-label'>Worst incoming move</div>"
            f"<div class='snapshot-move-line'>"
            f"<span class='snapshot-move'>{worst_move['Move']} ({worst_move.get('Category', 'Unknown')})</span>"
            f"{get_badge_img_html(worst_move.get('Type'), height=18)}"
            f"</div>"
            f"<div class='effectiveness-pill effectiveness-{effectiveness_class}'>{effectiveness_text}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

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

def render_battle_notes(notes):
    if not notes:
        st.caption("No special notes.")
        return

    for note in notes:
        icon = NOTE_ICONS.get(note.get("category"), "•")
        st.write(f"{icon} {note.get('text')}")


def render_defensive_effectiveness(multiplier):
    if multiplier is None:
        st.caption("Effectiveness unavailable")
        return

    if multiplier == 0:
        st.success("🛡️ No Effect (0×)")
    elif multiplier < 1:
        st.success(f"🟢 Not Very Effective ({multiplier:g}×)")
    elif multiplier == 1:
        st.info("⚪ Neutral (1×)")
    elif multiplier < 4:
        st.warning(f"🔺 Super Effective ({multiplier:g}×)")
    else:
        st.error(f"🔥 4× Weakness ({multiplier:g}×)")

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

def slugify_pokemon_name(pokemon_name):
    return (
        pokemon_name
        .lower()
        .replace("♀", "-f")
        .replace("♂", "-m")
        .replace(".", "")
        .replace("'", "")
        .replace(" ", "-")
    )


def get_sprite_path(pokemon_name, use_gmax=False):
    sprite_name = slugify_pokemon_name(pokemon_name)

    if use_gmax:
        gmax_path = SPRITE_DIR / f"{sprite_name}-gmax.png"
        if gmax_path.exists():
            return gmax_path

    galar_path = SPRITE_DIR / f"{sprite_name}-galar.png"
    if galar_path.exists():
        return galar_path

    sprite_path = SPRITE_DIR / f"{sprite_name}.png"
    if sprite_path.exists():
        return sprite_path

    return None


def get_sprite_img_html(pokemon_name, size=64, use_gmax=False):
    sprite_path = get_sprite_path(pokemon_name, use_gmax)

    if sprite_path is None:
        return (
            f"<div class='sprite-placeholder' "
            f"style='width:{size}px;height:{size}px;'>?</div>"
        )

    encoded = image_to_base64(sprite_path)

    return (
        f"<img "
        f"src='data:image/png;base64,{encoded}' "
        f"alt='{pokemon_name}' "
        f"class='pokemon-sprite' "
        f"style='max-width:{size}px;max-height:{size}px;' "
        f"/>"
    )

def opponent_uses_gmax(opponent):
    return any(
        str(opponent.get(f"Move{slot}", "")).startswith("G-Max")
        for slot in range(1, 5)
    )

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