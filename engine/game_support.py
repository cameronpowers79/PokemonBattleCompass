"""Game identity and mechanics-family registry. Gen IX deliberately not enabled yet."""
from __future__ import annotations

GAMES = ("Sword", "Shield", "Scarlet", "Violet")
SUPPORTED_GAMES = ("Sword", "Shield")
GAME_MECHANICS = {"Sword": "swsh", "Shield": "swsh", "Scarlet": "sv", "Violet": "sv"}
SHARED_GAME = "Sword and Shield"


def matches_game(record: dict, game: str) -> bool:
    """Filter an encounter/catalog entry by its supported game(s).

    Untagged legacy rows belong to the original Sword and Shield catalog.
    Future Gen IX catalogs must use explicit Game metadata.
    """
    available = record.get("Game", SHARED_GAME)
    if isinstance(available, list):
        return game in available
    if isinstance(available, str):
        return available == game or (available == SHARED_GAME and game in ("Sword", "Shield"))
    return False


def mechanics_for(game: str) -> str:
    if game not in GAME_MECHANICS:
        raise ValueError(f"Unknown game: {game}")
    return GAME_MECHANICS[game]


def resolve_game_record(record: dict, game: str) -> dict:
    """Return a game's acquisition/item-source presentation without mutating catalog data.

    Caller should first apply matches_game(). Species IDs, evolution and
    strategy metadata stay shared; only version-specific source fields vary.
    """
    from copy import deepcopy

    resolved = deepcopy(record)
    acquisition_options = resolved.pop("acquisition_by_game", None)
    if isinstance(acquisition_options, dict):
        acquisition = acquisition_options.get(game)
        if isinstance(acquisition, dict):
            resolved["primary_acquisition"] = deepcopy(acquisition)
    source_options = resolved.pop("sources_by_game", None)
    if isinstance(source_options, dict):
        sources = source_options.get(game)
        if isinstance(sources, list):
            resolved["sources"] = deepcopy(sources)
    return resolved
