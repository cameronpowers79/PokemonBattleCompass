import base64
from pathlib import Path
from textwrap import dedent
import streamlit as st
from io import BytesIO
from PIL import Image

from engine.data_loader import load_json, save_json
from engine.calculations import find_best_team_member, evaluate_team_matchups


st.set_page_config(
    page_title="Pokémon Battle Compass Alpha",
    layout="wide"
)

TYPE_BADGE_DIR = Path("assets/type_badges")

NOTE_ICONS = {
    "info": "ℹ️",
    "opportunity": "💡",
    "caution": "⚠️",
    "warning": "🚨",
}

TYPE_COLORS = {
    "Normal": "#A8A77A",
    "Fire": "#EE8130",
    "Water": "#6390F0",
    "Electric": "#F7D02C",
    "Grass": "#7AC74C",
    "Ice": "#96D9D6",
    "Fighting": "#C22E28",
    "Poison": "#A33EA1",
    "Ground": "#E2BF65",
    "Flying": "#A98FF3",
    "Psychic": "#F95587",
    "Bug": "#A6B91A",
    "Rock": "#B6A136",
    "Ghost": "#735797",
    "Dragon": "#6F35FC",
    "Dark": "#705746",
    "Steel": "#B7B7CE",
    "Fairy": "#D685AD",
}

SPRITE_DIR = Path("assets/raw/pokesprite/pokemon-gen8/regular")



st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@500;600;700;800&display=swap');

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

        .recommendation-card {
            background: linear-gradient(180deg, #151923 0%, #10141c 100%);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 18px;
            padding: 28px 32px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.25);
        }

        .card-kicker {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1.75rem;
            font-weight: 700;
            margin-bottom: 24px;
        }

        .pokemon-name {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 2.9rem;
            font-weight: 800;
            line-height: 1;
            margin-bottom: 12px;
        }

        .type-badge-row {
            display: flex;
            gap: 8px;
            align-items: center;
            justify-content: center;
            margin-bottom: 24px;
        }

        .type-badge {
            height: 24px;
            width: auto;
        }

        .card-divider {
            height: 1px;
            background: rgba(255,255,255,0.16);
            margin: 20px 0 24px 0;
        }

        .move-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 32px;
            margin-bottom: 18px;
        }

        .label {
            color: rgba(255,255,255,0.72);
            font-size: 0.92rem;
            margin-bottom: 6px;
        }

        .move-name,
        .ratio-value {
            font-family: "Bahnschrift", "Aptos", sans-serif;
            font-size: 2.35rem;
            line-height: 1.1;
            font-weight: 500;
        }

        .matchup-strength {
            min-width: 230px;
        }

        .matchup-strength-title {
            color: rgba(255,255,255,0.72);
            font-size: 0.92rem;
            margin-bottom: 12px;
        }

        .matchup-meter {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 4px;
            position: relative;
            margin-bottom: 16px;
        }

        .matchup-segment {
            position: relative;
            height: 14px;
            opacity: 0.38;
            border: 1px solid rgba(255,255,255,0.12);
        }

        .matchup-segment:first-child {
            border-radius: 999px 4px 4px 999px;
        }

        .matchup-segment:last-child {
            border-radius: 4px 999px 999px 4px;
        }

        .matchup-challenging {
            background: linear-gradient(180deg, #ef4444, #b91c1c);
        }

        .matchup-competitive {
            background: linear-gradient(180deg, #fb923c, #ea580c);
        }

        .matchup-favorable {
            background: linear-gradient(180deg, #d9f044, #a3c922);
        }

        .matchup-comfortable {
            background: linear-gradient(180deg, #4ade80, #16a34a);
        }

        .matchup-immune {
            background: linear-gradient(180deg, #60a5fa, #2563eb);
        }

        .matchup-segment-active {
            opacity: 1;
            box-shadow:
                0 0 0 1px rgba(255,255,255,0.20),
                0 0 10px rgba(255,255,255,0.12);
        }

        .matchup-pointer {
            position: absolute;
            left: 50%;
            bottom: -10px;
            transform: translateX(-50%);
            width: 0;
            height: 0;
            border-left: 7px solid transparent;
            border-right: 7px solid transparent;
            border-bottom: 9px solid rgba(255,255,255,0.92);
        }

        .matchup-strength-label {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1.25rem;
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 3px;
        }

        .matchup-label-challenging {
            color: #f87171;
        }

        .matchup-label-competitive {
            color: #fb923c;
        }

        .matchup-label-favorable {
            color: #d9f044;
        }

        .matchup-label-comfortable {
            color: #4ade80;
        }

        .matchup-label-immune {
            color: #60a5fa;
        }

        .matchup-ratio-detail {
            color: rgba(255,255,255,0.50);
            font-family: "Bahnschrift", "Aptos", sans-serif;
            font-size: 0.82rem;
        }

        .effectiveness-pill {
            border-radius: 12px;
            padding: 14px 18px;
            font-size: 1rem;
            font-weight: 600;
            margin: 8px 0 28px 0;
        }

        .effectiveness-good {
            background: rgba(34, 197, 94, 0.20);
            color: #4ade80;
        }

        .effectiveness-neutral {
            background: rgba(59, 130, 246, 0.18);
            color: #93c5fd;
        }

        .effectiveness-caution {
            background: rgba(245, 158, 11, 0.18);
            color: #fbbf24;
        }

        .effectiveness-bad {
            background: rgba(239, 68, 68, 0.18);
            color: #f87171;
        }

        .section-title {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1.35rem;
            font-weight: 700;
            margin-top: 20px;
            margin-bottom: 10px;
        }

        .why-box {
            background: rgba(59, 130, 246, 0.14);
            border: 1px solid rgba(59, 130, 246, 0.24);
            border-radius: 12px;
            padding: 14px 16px;
            color: #dbeafe;
            margin-bottom: 22px;
        }

        .notes-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .battle-note {
            border-radius: 10px;
            padding: 10px 12px;
            display: flex;
            gap: 10px;
            align-items: flex-start;
            font-size: 0.98rem;
        }

        .note-info {
            background: rgba(59, 130, 246, 0.12);
            color: #bfdbfe;
        }

        .note-opportunity {
            background: rgba(34, 197, 94, 0.12);
            color: #bbf7d0;
        }

        .note-caution {
            background: rgba(245, 158, 11, 0.14);
            color: #fde68a;
        }

        .note-warning {
            background: rgba(239, 68, 68, 0.15);
            color: #fecaca;
        }

        .note-icon {
            min-width: 22px;
        }

        .side-card {
            background: linear-gradient(180deg, #151923 0%, #10141c 100%);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 18px;
            padding: 24px 28px;
            margin-bottom: 20px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.20);
        }

        .side-card-title {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1.35rem;
            font-weight: 700;
            margin-bottom: 16px;
        }

        .opponent-name {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1;
            margin-bottom: 10px;
        }   

        .opponent-level {
            color: rgba(255,255,255,0.72);
            font-size: 1rem;
            margin-top: 8px;
        }

        .snapshot-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 22px;
            margin-bottom: 20px;
        }

        .snapshot-value {
            font-family: "Bahnschrift", "Aptos", sans-serif;
            font-size: 2rem;
            font-weight: 600;
        }

        .snapshot-move-label {
            color: rgba(255,255,255,0.72);
            font-size: 0.9rem;
            margin-bottom: 4px;
        }

        .snapshot-move {
            display: inline-block;
            transform: translateY(1px);
        }

        .move-name-line,
        .snapshot-move-line {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        .snapshot-move-line {
            margin-bottom: 12px;
        }

        .pokemon-header-row {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
            text-align: center;
        }

       .pokemon-text-block {
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .sprite-placeholder {
            border: 1px dashed rgba(255,255,255,0.25);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: rgba(255,255,255,0.45);
            font-size: 2rem;
            font-weight: 700;
            flex-shrink: 0;
        }

        .sprite-frame {
            width: 88px;
            height: 88px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: visible;
            flex-shrink: 0;
        }

        .pokemon-sprite {
            image-rendering: pixelated;
            image-rendering: crisp-edges;
            transform: scale(1.35);
            transform-origin: center center;
            display: block;
        }

        @media (max-width: 1350px) {
            div[data-testid="stHorizontalBlock"] {
                flex-direction: column;
            }

            div[data-testid="stHorizontalBlock"] > div {
                width: 100% !important;
            }
        }

        /* My Team detail panel */

        .team-detail-card {
            background: linear-gradient(180deg, #151923 0%, #10141c 100%);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 18px;
            padding: 24px 28px;
            margin-top: 22px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.20);
        }

        .team-detail-header {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            margin-bottom: 10px;
        }

        .team-detail-name {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1;
            margin: 10px 0 8px 0;
        }

        .team-detail-level {
            color: rgba(255,255,255,0.70);
            font-size: 1.25rem;
            margin-top: 4px;
        }

        .team-detail-section-title {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .team-stat-list {
            display: flex;
            flex-direction: column;
            gap: 9px;
            margin-bottom: 24px;
        }

        .team-stat-row {
            display: grid;
            grid-template-columns: 44px minmax(120px, 1fr) 48px;
            align-items: center;
            gap: 10px;
        }

        .team-stat-label {
            color: rgba(255,255,255,0.72);
            font-family: "Bahnschrift", "Aptos", sans-serif;
            font-size: 0.95rem;
            font-weight: 600;
        }

        .team-stat-track {
            height: 16px;
            background: rgba(255,255,255,0.09);
            border-radius: 999px;
            overflow: hidden;
        }

        .team-stat-fill {
            height: 100%;
            min-width: 3px;
            border-radius: 999px;
        }

        .team-stat-fill-hp {
            background: linear-gradient(
                90deg,
                rgba(34, 197, 94, 0.70),
                rgba(74, 222, 128, 0.98)
            );
        }

        .team-stat-fill-atk {
            background: linear-gradient(
                90deg,
                rgba(220, 38, 38, 0.72),
                rgba(248, 113, 113, 0.98)
            );
        }

        .team-stat-fill-def {
            background: linear-gradient(
                90deg,
                rgba(217, 119, 6, 0.72),
                rgba(251, 191, 36, 0.98)
            );
        }

        .team-stat-fill-spa {
            background: linear-gradient(
                90deg,
                rgba(37, 99, 235, 0.72),
                rgba(96, 165, 250, 0.98)
            );
        }

        .team-stat-fill-spd {
            background: linear-gradient(
                90deg,
                rgba(124, 58, 237, 0.72),
                rgba(167, 139, 250, 0.98)
            );
        }

        .team-stat-fill-spe {
            background: linear-gradient(
                90deg,
                rgba(219, 39, 119, 0.72),
                rgba(244, 114, 182, 0.98)
            );
        }

        .team-stat-value {
            font-family: "Bahnschrift", "Aptos", sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            text-align: right;
       }   

        .team-move-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(150px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
        }

        .team-move {

            display:flex;

            justify-content:space-between;

            align-items:center;

            gap:10px;

            color:white;

            border-radius:12px;

            padding:10px 14px;

            font-weight:700;

            border:1px solid rgba(255,255,255,.18);

            box-shadow:
                inset 0 1px rgba(255,255,255,.18),
                0 2px 6px rgba(0,0,0,.18);

            text-shadow:0 1px 2px rgba(0,0,0,.35);
        }

        .team-move-name{
            overflow:hidden;
            text-overflow:ellipsis;
            white-space:nowrap;
        }

        .team-move-badge{

            display:flex;

            align-items:center;

            flex-shrink:0;
        }

        .team-detail-footer {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }

        .team-detail-field {
            background: rgba(255,255,255,0.04);
            border-radius: 10px;
            padding: 10px 12px;
        }

        .team-detail-field-label {
            color: rgba(255,255,255,0.62);
            font-size: 0.78rem;
            margin-bottom: 3px;
        }

        @media (max-width: 900px) {

            .team-move-grid,
            .team-detail-footer {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 700px) {

            .move-row {
                display: grid;
                grid-template-columns: 1fr;
                gap: 18px;
            }

            .matchup-strength {
                width: 100%;
                min-width: 0;
            }

            .matchup-meter {
                width: 100%;
            }
}

</style>
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
        "<div>"
        "<div class='label'>Best Move</div>"
        f"<div class='move-name-line'>"
        f"<span class='move-name'>{best_move['Move']}</span>"
        f"{get_badge_img_html(best_move.get('Type'), height=20)}"
        f"</div>"
        "</div>"
        f"<div>{matchup_strength_html}</div>"
        "</div>"
        f"<div class='effectiveness-pill effectiveness-{effectiveness_class}'>{effectiveness_text}</div>"
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
    st.subheader("My Team")

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

    pokemon_names = [
        pokemon.get("Pokemon")
        for pokemon in editable_team
        if pokemon.get("Pokemon")
    ]

    selected_pokemon_name = st.selectbox(
        "View Pokémon Details",
        pokemon_names,
        key="team_detail_selector"
    )

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

    st.caption(
        "Edit your current party. Changes are not saved until you click Save Team."
    )

    st.caption(
        "Only modeled held items affect scores. If an item should improve "
        "scores but does not, check the spelling."
    )

    if st.button("💾 Save Team", type="primary"):
        saved_team = []

        for original_pokemon, edited_pokemon in zip(team_data, edited_team):
            merged_pokemon = dict(original_pokemon)

            for column in editable_columns:
                merged_pokemon[column] = edited_pokemon.get(column)

            saved_team.append(
                apply_move_metadata(merged_pokemon)
            )

        save_json("team_data", saved_team)
        st.success("Team saved!")

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
st.caption("Alpha UI preview — advice first, spreadsheet goblins later.")

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

active_view = st.segmented_control(
    "Main navigation",
    options=["Battle Compass", "My Team"],
    default="Battle Compass",
    key="main_view",
    label_visibility="collapsed",
    width="stretch",
)

if active_view == "Battle Compass":
    st.divider()

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

elif active_view == "My Team":
    render_my_team_editor(team_data)