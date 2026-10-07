"""Smoke tests for Strategy Recommender integration primitives.

Run from the Pokemon Battle Compass project root:

    python strategy_recommender_smoke_test.py
"""

from engine.learnsets import supported_strategy_move_methods
from engine.strategy_capabilities import (
    recognize_team_capabilities,
    recommend_strategy_moves_for_added_pokemon,
)
from engine.strategy_definitions import (
    BATTLE_COMPASS_SELECTABLE_STRATEGY_IDS,
    RECOMMENDER_STRATEGY_IDS,
)
from ui.storage.journey_storage import VALID_TEAM_STRATEGIES


CANONICAL = {
    "strongest_matchup",
    "poison_offensive_pressure",
    "poison_attrition",
    "screen_control",
    "setup_offense",
    "status_control_punish",
    "weather_control",
    "defensive_attrition",
}

MOVES = [
    {"Move": "Reflect", "Category": "Status", "MechanicsTags": ["Screen"]},
    {"Move": "Light Screen", "Category": "Status", "MechanicsTags": ["Screen"]},
    {"Move": "Psychic", "Category": "Special", "Power": 90, "Type": "Psychic"},
    {"Move": "Close Combat", "Category": "Physical", "Power": 120, "Type": "Fighting"},
    {"Move": "Will-O-Wisp", "Category": "Status", "StatusEffect": "burn"},
    {
        "Move": "Hex",
        "Category": "Special",
        "Power": 65,
        "Type": "Ghost",
        "ActivationCondition": "TargetAnyStatus",
        "ActivationPowerMultiplier": 2,
    },
]

LEARNSETS = {
    "pokemon": {
        "orbeetle": {
            "moves": {
                "Reflect": [{"method": "tm", "item": "TM18", "supported_for_strategy": True}],
                "Light Screen": [{"method": "tm", "item": "TM17", "supported_for_strategy": True}],
                "Psychic": [{"method": "tr", "item": "TR11", "supported_for_strategy": True}],
            }
        },
        "chandelure": {
            "moves": {
                "Will-O-Wisp": [{"method": "tm", "item": "TM38", "supported_for_strategy": True}],
                "Hex": [{"method": "level", "level": 1, "supported_for_strategy": True}],
            }
        },
        "testmon": {
            "moves": {
                "Reflect": [
                    {"method": "egg"},
                    {"method": "tm", "item": "TM18"},
                ]
            }
        },
    }
}


def require(label: str, condition: bool, detail=None) -> None:
    if not condition:
        raise AssertionError(f"{label} FAILED\n{detail}")
    print(f"PASS  {label}")


def main() -> None:
    require(
        "All canonical strategies are valid saved Team Strategy values",
        VALID_TEAM_STRATEGIES == CANONICAL,
        VALID_TEAM_STRATEGIES,
    )
    require(
        "All canonical strategies are manually selectable in Battle Compass",
        set(BATTLE_COMPASS_SELECTABLE_STRATEGY_IDS) == CANONICAL,
        BATTLE_COMPASS_SELECTABLE_STRATEGY_IDS,
    )
    require(
        "All canonical strategies appear in Strategy Recommender",
        set(RECOMMENDER_STRATEGY_IDS) == CANONICAL,
        RECOMMENDER_STRATEGY_IDS,
    )

    team = [
        {"Pokemon": "Machamp", "Move1": "Close Combat"},
        {"Pokemon": "Alakazam", "Move1": "Psychic"},
    ]
    current = recognize_team_capabilities(team, MOVES)
    screen_moves = recommend_strategy_moves_for_added_pokemon(
        "screen_control",
        current,
        {"Pokemon": "Orbeetle"},
        MOVES,
        LEARNSETS,
    )
    require(
        "Guided Orbeetle plan includes both screens",
        set(screen_moves[:2]) == {"Reflect", "Light Screen"},
        screen_moves,
    )

    status_moves = recommend_strategy_moves_for_added_pokemon(
        "status_control_punish",
        [],
        {"Pokemon": "Chandelure"},
        MOVES,
        LEARNSETS,
    )
    require(
        "Guided Chandelure plan includes reliable status plus Hex",
        {"Will-O-Wisp", "Hex"}.issubset(status_moves),
        status_moves,
    )

    methods = supported_strategy_move_methods(
        {"Pokemon": "Testmon"},
        "Reflect",
        LEARNSETS,
    )
    require(
        "Move planning excludes Egg method while retaining supported TM method",
        len(methods) == 1 and methods[0].get("item") == "TM18",
        methods,
    )

    print("\nAll 6 Strategy Recommender integration smoke tests passed.")


if __name__ == "__main__":
    main()
