"""Smoke tests for engine.strategy_capabilities.

Run from the Pokémon Battle Compass project root:

    python strategy_capabilities_smoke_test.py

These tests use small synthetic move records so they isolate capability recognition
and generic strategy viability from battle calculations and external data files.
"""

import engine.strategy_capabilities as strategy_capabilities
from engine.strategy_capabilities import (
    evaluate_strategy_recommendations,
    evaluate_strategy_viability,
    recognize_team_capabilities,
)

MOVES = [
    {"Move": "Reflect", "Category": "Status", "MechanicsTags": ["Screen"]},
    {"Move": "Light Screen", "Category": "Status", "MechanicsTags": ["Screen"]},
    {"Move": "Psychic", "Category": "Special", "Power": 90, "Type": "Psychic"},
    {"Move": "Close Combat", "Category": "Physical", "Power": 120, "Type": "Fighting"},
    {
        "Move": "Swords Dance",
        "Category": "Status",
        "StageChangeTarget": "User",
        "AtkStageChange": 2,
    },
    {
        "Move": "Agility",
        "Category": "Status",
        "StageChangeTarget": "User",
        "SpeStageChange": 2,
    },
    {"Move": "Protect", "Category": "Status", "MechanicsTags": ["Protection"]},
    {"Move": "Will-O-Wisp", "Category": "Status", "StatusEffect": "burn"},
    {
        "Move": "Hex",
        "Category": "Special",
        "Power": 65,
        "Type": "Ghost",
        "ActivationCondition": "TargetAnyStatus",
        "ActivationPowerMultiplier": 2,
    },
    {
        "Move": "Flamethrower",
        "Category": "Special",
        "Power": 90,
        "Type": "Fire",
        "StatusEffect": "burn",
    },
    {"Move": "Rain Dance", "Category": "Status"},
    {"Move": "Sunny Day", "Category": "Status"},
    {"Move": "Surf", "Category": "Special", "Power": 90, "Type": "Water"},
    {"Move": "Solar Beam", "Category": "Special", "Power": 120, "Type": "Grass"},
    {
        "Move": "Iron Defense",
        "Category": "Status",
        "StageChangeTarget": "User",
        "DefStageChange": 2,
        "MechanicsTags": ["DefenseSetup"],
    },
    {"Move": "Body Press", "Category": "Physical", "Power": 80, "Type": "Fighting"},
]


def mon(
    name: str,
    ability: str = "",
    *moves: str,
    supported_moves: tuple[str, ...] | None = None,
) -> dict:
    pokemon = {"Pokemon": name, "Ability": ability}
    for slot, move_name in enumerate(moves[:4], start=1):
        pokemon[f"Move{slot}"] = move_name
    if supported_moves is not None:
        pokemon["_SupportedMoves"] = list(supported_moves)
    return pokemon


def capabilities(team: list[dict]):
    return recognize_team_capabilities(team, MOVES)


def require(name: str, condition: bool, detail: object = None) -> None:
    if not condition:
        raise AssertionError(f"{name} FAILED\n{detail}")
    print(f"PASS  {name}")


def main() -> None:
    total = 0

    # Screen Control: the setter alone establishes viability. Strong requires
    # saved stat evidence for a separate offense-leaning teammate.
    screen_team = [
        mon("Orbeetle", "", "Reflect", "Light Screen"),
        mon("Salazzle", "", "Psychic"),
    ]
    screen_team[1].update({"SPA": 170, "DEF": 80, "SPD": 75, "SPE": 155})
    result = evaluate_strategy_viability(
        "screen_control", capabilities(screen_team), team_data=screen_team,
    )
    require("Screen Control: dual screens + offense-leaning teammate => Strong",
            result.viability == "Strong", result)
    total += 1

    result = evaluate_strategy_viability(
        "screen_control",
        capabilities([mon("Orbeetle", "", "Reflect", "Light Screen")]),
    )
    require("Screen Control: dual-screen setter alone => Viable",
            result.viability == "Viable" and not result.missing_required_roles, result)
    total += 1

    result = evaluate_strategy_viability(
        "screen_control",
        capabilities([mon("Orbeetle", "", "Reflect", "Psychic")]),
    )
    require("Screen Control: only one screen => Incomplete",
            result.viability == "Incomplete"
            and "reliable screen setter" in result.missing_required_roles,
            result)
    total += 1

    # Setup Offense
    result = evaluate_strategy_viability(
        "setup_offense",
        capabilities([
            mon("Scizor", "", "Swords Dance", "Protect", "Close Combat"),
        ]),
    )
    require("Setup Offense: offensive setup + protected setup access => Viable",
            result.viability == "Viable", result)
    total += 1

    result = evaluate_strategy_viability(
        "setup_offense",
        capabilities([
            mon("Ninjask", "Speed Boost", "Swords Dance", "Close Combat"),
        ]),
    )
    require("Setup Offense: Speed Boost + offensive setup => Strong",
            result.viability == "Strong", result)
    total += 1

    result = evaluate_strategy_viability(
        "setup_offense",
        capabilities([
            mon("Scizor", "", "Swords Dance", "Close Combat"),
        ]),
    )
    require("Setup Offense: setup move without modeled setup access => Incomplete",
            result.viability == "Incomplete"
            and "setup access" in result.missing_required_roles,
            result)
    total += 1

    # Status Control & Punish
    result = evaluate_strategy_viability(
        "status_control_punish",
        capabilities([
            mon("Chandelure", "", "Will-O-Wisp", "Hex"),
        ]),
    )
    require("Status Control & Punish: Will-O-Wisp + Hex => Strong",
            result.viability == "Strong", result)
    total += 1

    result = evaluate_strategy_viability(
        "status_control_punish",
        capabilities([
            mon("Chandelure", "", "Flamethrower", "Hex"),
        ]),
    )
    require("Status Control & Punish: incidental damaging-move status is not a reliable setter",
            result.viability == "Incomplete"
            and "reliable status" in result.missing_required_roles,
            result)
    total += 1

    # Weather Control
    result = evaluate_strategy_viability(
        "weather_control",
        capabilities([
            mon("Pelipper", "", "Rain Dance"),
            mon("Barraskewda", "Swift Swim", "Surf"),
        ]),
    )
    require("Weather Control: matched Rain setter + distinct beneficiary => Viable",
            result.viability == "Viable", result)
    total += 1

    result = evaluate_strategy_viability(
        "weather_control",
        capabilities([
            mon("Pelipper", "", "Rain Dance"),
            mon("Venusaur", "Chlorophyll", "Solar Beam"),
        ]),
    )
    require("Weather Control: Rain setter + Sun beneficiary mismatch => Incomplete",
            result.viability == "Incomplete"
            and "matched weather beneficiary" in result.missing_required_roles,
            result)
    total += 1

    result = evaluate_strategy_viability(
        "weather_control",
        capabilities([
            mon("Pelipper", "", "Rain Dance"),
            mon("Barraskewda", "Swift Swim", "Surf"),
            mon("Kingdra", "Swift Swim", "Surf"),
        ]),
    )
    require("Weather Control: matched Rain package with multiple beneficiaries => Strong",
            result.viability == "Strong", result)
    total += 1

    result = evaluate_strategy_viability(
        "weather_control",
        capabilities([
            mon("Ludicolo", "Swift Swim", "Rain Dance", "Surf"),
        ]),
    )
    require("Weather Control: one Pokémon cannot be both the whole setter/beneficiary package",
            result.viability == "Incomplete", result)
    total += 1

    # Defensive Attrition
    result = evaluate_strategy_viability(
        "defensive_attrition",
        capabilities([
            mon("Corviknight", "", "Iron Defense", "Body Press"),
        ]),
    )
    require("Defensive Attrition: Iron Defense + Body Press => Strong",
            result.viability == "Strong", result)
    total += 1

    result = evaluate_strategy_viability(
        "defensive_attrition",
        capabilities([
            mon("Ferrothorn", "Iron Barbs", "Protect"),
        ]),
    )
    require("Defensive Attrition: protection + contact punishment => Viable",
            result.viability == "Viable", result)
    total += 1

    result = evaluate_strategy_viability(
        "defensive_attrition",
        capabilities([
            mon("Ferrothorn", "Iron Barbs", "Close Combat"),
        ]),
    )
    require("Defensive Attrition: punishment without a survival loop => Incomplete",
            result.viability == "Incomplete"
            and "survival loop" in result.missing_required_roles,
            result)
    total += 1

    # Generic evaluator guardrails.
    result = evaluate_strategy_viability("Strongest Matchup", [])
    require("Strongest Matchup is always Strong",
            result.viability == "Strong", result)
    total += 1

    for strategy in (
        "screen_control",
        "setup_offense",
        "status_control_punish",
        "weather_control",
        "defensive_attrition",
    ):
        result = evaluate_strategy_viability(strategy, [])
        require(f"{strategy}: plain viability evaluation does not guess one-change readiness",
                result.one_change_away is False, result)
        total += 1

    # Recommendation-side scoring. Patch only the learnset gate so these tests stay
    # synthetic and do not depend on the project's large learnsets JSON. The real
    # application continues to use engine.learnsets.supported_strategy_move_names().
    original_supported_moves = strategy_capabilities.supported_strategy_move_names
    strategy_capabilities.supported_strategy_move_names = (
        lambda pokemon, learnsets_data, moves_data: pokemon.get("_SupportedMoves", [])
    )
    try:
        result = evaluate_strategy_recommendations(
            "status_control_punish",
            [mon(
                "Chandelure", "", "Hex",
                supported_moves=("Hex", "Will-O-Wisp"),
            )],
            [],
            MOVES,
            {},
        )
        require(
            "Recommendation: one supported move makes Chandelure Status Control & Punish ready",
            result.viability.viability == "Incomplete"
            and result.one_change_away
            and result.viability.one_change_away
            and any(
                candidate.move_name == "Will-O-Wisp"
                and candidate.resulting_viability == "Strong"
                for candidate in result.move_changes
            ),
            result,
        )
        total += 1

        result = evaluate_strategy_recommendations(
            "screen_control",
            [mon(
                "Machamp", "", "Close Combat",
                supported_moves=("Close Combat",),
            )],
            [mon(
                "Orbeetle", "",
                supported_moves=("Reflect", "Light Screen", "Psychic"),
            )],
            MOVES,
            {},
        )
        require(
            "Recommendation: adding supported dual-screen Orbeetle completes Screen Control",
            result.one_change_away
            and any(
                candidate.pokemon_name == "Orbeetle"
                and candidate.resulting_viability in {"Viable", "Strong"}
                for candidate in result.pokemon_additions
            ),
            result,
        )
        total += 1

        result = evaluate_strategy_recommendations(
            "weather_control",
            [mon(
                "Venusaur", "Chlorophyll", "Solar Beam",
                supported_moves=("Solar Beam",),
            )],
            [mon(
                "Pelipper", "",
                supported_moves=("Rain Dance",),
            )],
            MOVES,
            {},
        )
        require(
            "Recommendation: mismatched Rain setter does not create a one-change Sun package",
            not result.one_change_away,
            result,
        )
        total += 1

        full_team = [
            mon(
                f"Party{i}", "", "Psychic",
                supported_moves=("Psychic",),
            )
            for i in range(6)
        ]
        result = evaluate_strategy_recommendations(
            "screen_control",
            full_team,
            [mon(
                "Orbeetle", "",
                supported_moves=("Reflect", "Light Screen"),
            )],
            MOVES,
            {},
        )
        require(
            "Recommendation: a full six-Pokémon team is not offered a seventh addition",
            not result.pokemon_additions,
            result,
        )
        total += 1

        result = evaluate_strategy_recommendations(
            "status_control_punish",
            [mon(
                "Chandelure", "", "Hex", "Psychic", "Close Combat", "Surf",
                supported_moves=("Hex", "Will-O-Wisp", "Psychic", "Close Combat", "Surf"),
            )],
            [],
            MOVES,
            {},
        )
        require(
            "Recommendation: replacement simulation preserves Hex when adding Will-O-Wisp",
            any(
                candidate.move_name == "Will-O-Wisp"
                and candidate.replace_move_name != "Hex"
                and candidate.resulting_viability == "Strong"
                for candidate in result.move_changes
            )
            and not any(
                candidate.move_name == "Will-O-Wisp"
                and candidate.replace_move_name == "Hex"
                and candidate.resulting_viability_rank >= 1
                for candidate in result.move_changes
            ),
            result,
        )
        total += 1

        result = evaluate_strategy_recommendations(
            "defensive_attrition",
            [mon(
                "Corviknight", "", "Iron Defense",
                supported_moves=("Iron Defense", "Body Press"),
            )],
            [],
            MOVES,
            {},
        )
        require(
            "Recommendation: Body Press is recognized as the single missing Defensive Attrition move",
            result.one_change_away
            and any(
                candidate.move_name == "Body Press"
                and candidate.resulting_viability == "Strong"
                for candidate in result.move_changes
            ),
            result,
        )
        total += 1
    finally:
        strategy_capabilities.supported_strategy_move_names = original_supported_moves

    print(f"\nAll {total} strategy capability/viability/recommendation smoke tests passed.")


if __name__ == "__main__":
    main()
