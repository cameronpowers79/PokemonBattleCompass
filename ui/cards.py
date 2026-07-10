import streamlit as st

from ui.constants import NOTE_ICONS
from ui.rendering import (
    get_badge_img_html,
    get_sprite_img_html,
    opponent_uses_gmax,
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


def get_matchup_strength(ratio, is_immune=False):
    """
    Classify a matchup into a player-facing strength category.

    Immunity is supplied explicitly by the engine and is not inferred
    from the numeric matchup ratio.
    """
    if is_immune:
        return "Immune", 4, "immune"

    if ratio >= 3:
        return "Comfortable", 3, "comfortable"

    if ratio >= 2:
        return "Favorable", 2, "favorable"

    if ratio >= 1:
        return "Competitive", 1, "competitive"

    return "Challenging", 0, "challenging"


def get_matchup_strength_html(ratio, is_immune=False):
    label, active_index, css_class = get_matchup_strength(
        ratio,
        is_immune
    )

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

    ratio_html = (
        ""
        if is_immune
        else f"<div class='matchup-ratio-detail'>Ratio {ratio:.2f}</div>"
    )

    return (
        "<div class='matchup-strength'>"
        "<div class='matchup-strength-title'>Matchup Strength</div>"
        f"<div class='matchup-meter'>{segments_html}</div>"
        f"<div class='matchup-strength-label matchup-label-{css_class}'>"
        f"{label}"
        "</div>"
        f"{ratio_html}"
        "</div>"
    )


def render_recommendation_card(
    recommended_pokemon,
    best_move,
    ratio,
    why,
    recommended_result
):
    type_badges = "".join(
        get_badge_img_html(pokemon_type)
        for pokemon_type in [
            recommended_pokemon.get("Type1"),
            recommended_pokemon.get("Type2"),
        ]
        if pokemon_type
    )

    offensive_multiplier = recommended_result.get("Best Move Multiplier")
    effectiveness_text = get_effectiveness_text(
        offensive_multiplier,
        "offense"
    )
    effectiveness_class = get_effectiveness_class(
        offensive_multiplier,
        "offense"
    )

    notes_html = ""

    for battle_note in recommended_result.get("Battle Notes", []):
        category = battle_note.get("category", "info")
        text = battle_note.get("text", "")
        icon = NOTE_ICONS.get(category, "•")

        notes_html += (
            f"<div class='battle-note note-{category}'>"
            f"<span class='note-icon'>{icon}</span>"
            f"<span>{text}</span>"
            "</div>"
        )

    if not notes_html:
        notes_html = (
            "<div class='battle-note note-info'>"
            "No special notes."
            "</div>"
        )

    matchup_strength_html = get_matchup_strength_html(
        ratio,
        recommended_result.get("Is Immune", False)
    )

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


def render_opponent_card(opponent):
    type_badges = "".join(
        get_badge_img_html(pokemon_type, height=20)
        for pokemon_type in [
            opponent.get("Type1"),
            opponent.get("Type2"),
        ]
        if pokemon_type
    )

    sprite_html = get_sprite_img_html(
        opponent["Pokemon"],
        size=70,
        use_gmax=opponent_uses_gmax(opponent)
    )

    st.markdown(
        (
            "<div class='side-card'>"
            "<div class='side-card-title'>Opponent</div>"
            "<div class='pokemon-header-row'>"
            f"{sprite_html}"
            "<div class='pokemon-text-block'>"
            f"<div class='opponent-name'>{opponent['Pokemon']}</div>"
            f"<div class='type-badge-row'>{type_badges}</div>"
            f"<div class='opponent-level'>"
            f"Lv. {opponent.get('Level', '—')}"
            "</div>"
            "</div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_battle_snapshot(
    best_score,
    worst_score,
    worst_move,
    recommended_result
):
    incoming_multiplier = recommended_result.get("Incoming Multiplier")

    effectiveness_text = get_effectiveness_text(
        incoming_multiplier,
        "defense"
    )
    effectiveness_class = get_effectiveness_class(
        incoming_multiplier,
        "defense"
    )

    st.markdown(
        (
            "<div class='side-card'>"
            "<div class='side-card-title'>Battle Snapshot</div>"
            "<div class='snapshot-grid'>"
            "<div>"
            "<div class='label'>Move Score</div>"
            f"<div class='snapshot-value'>{best_score:.2f}</div>"
            "</div>"
            "<div>"
            "<div class='label'>Incoming Worst</div>"
            f"<div class='snapshot-value'>{worst_score:.2f}</div>"
            "</div>"
            "</div>"
            "<div class='snapshot-move-label'>"
            "Worst incoming move"
            "</div>"
            "<div class='snapshot-move-line'>"
            "<span class='snapshot-move'>"
            f"{worst_move['Move']} "
            f"({worst_move.get('Category', 'Unknown')})"
            "</span>"
            f"{get_badge_img_html(worst_move.get('Type'), height=18)}"
            "</div>"
            f"<div class='effectiveness-pill "
            f"effectiveness-{effectiveness_class}'>"
            f"{effectiveness_text}"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_battle_notes(notes):
    if not notes:
        st.caption("No special notes.")
        return

    for battle_note in notes:
        icon = NOTE_ICONS.get(
            battle_note.get("category"),
            "•"
        )

        st.write(
            f"{icon} {battle_note.get('text')}"
        )


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