"""Shared Team Strategy labels, colors, and explanatory text."""

from __future__ import annotations

from engine.strategy_definitions import (
    BATTLE_COMPASS_SELECTABLE_STRATEGY_IDS,
    STRATEGY_DEFINITIONS,
    get_strategy_definition,
)
from ui.theme import TEXT_PRIMARY


STRATEGY_PURPLE = STRATEGY_DEFINITIONS[
    "poison_offensive_pressure"
].color


# Only strategies whose live tactical behavior has been implemented
# appear in the Battle Compass selector.
TEAM_STRATEGY_LABELS = {
    key: STRATEGY_DEFINITIONS[key].label
    for key in BATTLE_COMPASS_SELECTABLE_STRATEGY_IDS
}

TEAM_STRATEGY_COLORS = {
    key: STRATEGY_DEFINITIONS[key].color
    for key in BATTLE_COMPASS_SELECTABLE_STRATEGY_IDS
}


def strategy_label(strategy: str) -> str:
    return get_strategy_definition(strategy).label


def strategy_color(strategy: str) -> str:
    definition = STRATEGY_DEFINITIONS.get(strategy)
    return (
        definition.color
        if definition is not None
        else TEXT_PRIMARY
    )


def strategy_compact_description(strategy: str) -> str:
    return get_strategy_definition(
        strategy
    ).compact_description


def strategy_full_description(strategy: str) -> str:
    return get_strategy_definition(
        strategy
    ).full_description


def strategy_tooltip(
    strategy: str,
    *,
    location: str,
) -> str:
    description = strategy_full_description(strategy)

    if location == "my_team":
        return (
            f"{description} Change Team Strategy from Battle Compass "
            "when you want to compare recommendation styles for the "
            "current battle."
        )

    return (
        f"{description} Changing this selection updates Battle Compass "
        "recommendations and saves the active strategy to your Journey."
    )