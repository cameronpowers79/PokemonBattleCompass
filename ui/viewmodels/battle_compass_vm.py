"""
Battle Compass view model.

Loads Battle Compass data, calls the existing battle engine, and converts
engine output into UI-friendly objects without depending on Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.calculations import (
    evaluate_team_matchups,
    find_best_team_member,
)
from engine.data_loader import load_json
from ui.constants import NOTE_ICONS


@dataclass(frozen=True)
class BattleNoteViewModel:
    """Display-ready battle note."""

    icon: str
    text: str
    category: str


@dataclass(frozen=True)
class MatchupViewModel:
    """Display-ready matchup result for one team member."""

    pokemon: dict
    best_move: dict
    best_move_score: float
    best_move_multiplier: float
    base_move_score: float
    item_boosted: bool
    item_multiplier: float
    item_bonus_amount: float
    held_item: str | None
    worst_move: dict
    incoming_worst_score: float
    incoming_multiplier: float
    ratio: float
    is_immune: bool
    matchup_label: str
    matchup_level: int
    battle_notes: list[BattleNoteViewModel]


@dataclass(frozen=True)
class BattleCompassViewModel:
    """Complete display model for one selected opponent."""

    opponent: dict
    recommendation: MatchupViewModel
    why_text: str
    other_options: list[MatchupViewModel]
    all_matchups: list[MatchupViewModel]


def get_matchup_strength(
    ratio: float,
    is_immune: bool = False,
) -> tuple[str, int]:
    """Return the user-facing matchup label and active meter segment."""

    if is_immune:
        return "Immune", 4

    if ratio >= 3:
        return "Comfortable", 3

    if ratio >= 2:
        return "Favorable", 2

    if ratio >= 1:
        return "Competitive", 1

    return "Challenging", 0


def get_effectiveness_label(
    multiplier: float | None,
    *,
    mode: str,
) -> str:
    """Return the established player-facing effectiveness text."""

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


def _build_move_lookup(
    moves_data: list[dict],
) -> dict[str, dict]:
    return {
        move["Move"]: move
        for move in moves_data
        if move.get("Move")
    }


def _build_note_view_models(
    battle_notes: list[dict],
) -> list[BattleNoteViewModel]:
    note_view_models: list[BattleNoteViewModel] = []

    for note in battle_notes:
        category_value = note.get("category")
        text_value = note.get("text")

        category = (
            category_value
            if isinstance(category_value, str)
            else "info"
        )

        text = (
            text_value
            if isinstance(text_value, str)
            else ""
        )

        note_view_models.append(
            BattleNoteViewModel(
                icon=NOTE_ICONS.get(
                    category,
                    "•",
                ),
                text=text,
                category=category,
            )
        )

    return note_view_models


def _build_matchup_view_model(
    *,
    result: dict,
    pokemon: dict,
    move_lookup: dict[str, dict],
) -> MatchupViewModel:
    best_move_name = result["Best Move"]
    worst_move_name = result["Worst Incoming Move"]

    best_move = dict(
        move_lookup.get(
            best_move_name,
            {},
        )
    )

    best_move.setdefault(
        "Move",
        best_move_name,
    )
    best_move.setdefault(
        "Type",
        result.get("Best Move Type"),
    )
    best_move.setdefault(
        "Category",
        result.get("Best Move Category"),
    )

    worst_move = dict(
        move_lookup.get(
            worst_move_name,
            {},
        )
    )

    worst_move.setdefault(
        "Move",
        worst_move_name,
    )
    worst_move.setdefault(
        "Type",
        result.get("Worst Incoming Move Type"),
    )
    worst_move.setdefault(
        "Category",
        result.get("Worst Incoming Move Category"),
    )

    ratio = float(result["Ratio"])
    is_immune = bool(result.get("Is Immune", False))

    matchup_label, matchup_level = get_matchup_strength(
        ratio,
        is_immune,
    )

    return MatchupViewModel(
        pokemon=pokemon,
        best_move=best_move,
        best_move_score=float(result["Best MoveScore"]),
        best_move_multiplier=float(
            result["Best Move Multiplier"]
        ),
        base_move_score=float(result["Base MoveScore"]),
        item_boosted=bool(result["Item Boosted"]),
        item_multiplier=float(result["Item Multiplier"]),
        item_bonus_amount=float(result["Item Bonus Amount"]),
        held_item=result.get("Held Item"),
        worst_move=worst_move,
        incoming_worst_score=float(
            result["Incoming Worst Score"]
        ),
        incoming_multiplier=float(
            result["Incoming Multiplier"]
        ),
        ratio=ratio,
        is_immune=is_immune,
        matchup_label=matchup_label,
        matchup_level=matchup_level,
        battle_notes=_build_note_view_models(
            result.get("Battle Notes", [])
        ),
    )


def build_battle_compass_view_model(
    *,
    team_data: list[dict],
    opponent: dict,
    items: list[dict],
    ability_rules: list[dict],
    moves_data: list[dict],
) -> BattleCompassViewModel:
    """
    Run the existing battle engine and return display-ready results for
    the selected opponent.
    """

    recommended_pokemon, _, why_text = find_best_team_member(
        team_data,
        opponent,
        items,
        ability_rules,
        moves_data,
    )

    if recommended_pokemon is None:
        raise RuntimeError(
            "No team members currently have a damaging move."
        )

    matchup_results = evaluate_team_matchups(
        team_data,
        opponent,
        items,
        ability_rules,
        moves_data,
    )

    move_lookup = _build_move_lookup(moves_data)

    pokemon_lookup = {
        pokemon["Pokemon"]: pokemon
        for pokemon in team_data
        if pokemon.get("Pokemon")
    }

    all_matchups = [
        _build_matchup_view_model(
            result=result,
            pokemon=pokemon_lookup[result["Pokemon"]],
            move_lookup=move_lookup,
        )
        for result in matchup_results
    ]

    recommendation = next(
        matchup
        for matchup in all_matchups
        if (
            matchup.pokemon["Pokemon"]
            == recommended_pokemon["Pokemon"]
        )
    )

    other_options = [
        matchup
        for matchup in all_matchups
        if matchup is not recommendation
    ]

    return BattleCompassViewModel(
        opponent=opponent,
        recommendation=recommendation,
        why_text=why_text,
        other_options=other_options[:2],
        all_matchups=all_matchups,
    )


def load_reference_data() -> dict[str, list]:
    """Load the bundled reference and default team data."""

    return {
        "team_data": load_json("team_data"),
        "opponents": load_json("opponents"),
        "items": load_json("items"),
        "ability_rules": load_json("ability_rules"),
        "abilities": load_json("abilities_swsh"),
        "moves_data": load_json("moves"),
    }