"""
Battle Compass ViewModel smoke test.

Loads bundled data, evaluates the first available opponent, and prints
the resulting recommendation without launching either frontend.
"""

from ui.viewmodels.battle_compass_vm import (
    build_battle_compass_view_model,
    load_reference_data,
)


def main() -> None:
    data = load_reference_data()

    team_data = data["team_data"]
    opponents = data["opponents"]
    items = data["items"]
    ability_rules = data["ability_rules"]
    moves_data = data["moves_data"]

    if not team_data:
        raise RuntimeError("No team data is available.")

    if not opponents:
        raise RuntimeError("No opponent data is available.")

    opponent = opponents[0]

    view_model = build_battle_compass_view_model(
        team_data=team_data,
        opponent=opponent,
        items=items,
        ability_rules=ability_rules,
        moves_data=moves_data,
    )

    recommendation = view_model.recommendation

    print(f"Opponent: {opponent.get('Pokemon', 'Unknown')}")
    print(
        "Recommended Pokémon: "
        f"{recommendation.pokemon.get('Pokemon', 'Unknown')}"
    )
    print(
        "Best Move: "
        f"{recommendation.best_move.get('Move', 'Unknown')}"
    )
    print(f"Move Score: {recommendation.best_move_score:.2f}")
    print(f"Matchup Ratio: {recommendation.ratio:.2f}")
    print(f"Matchup Strength: {recommendation.matchup_label}")
    print(f"Other Strong Options: {len(view_model.other_options)}")


if __name__ == "__main__":
    main()