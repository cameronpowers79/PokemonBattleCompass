"""Sword/Shield learnset queries used by validation and strategy features.

The finalized learnset dataset classifies acquisition methods individually.
Strategy queries intentionally include only methods marked
``supported_for_strategy``. Egg Moves, DLC-only methods, and unknown methods
therefore stay out of generated recommendations without affecting moves the
player has already entered and confirmed on a Pokémon.
"""

from __future__ import annotations

from engine.pokemon_identity import resolve_pokemon_id


def resolve_learnset_key(pokemon: dict) -> str | None:
    """Resolve a saved/planned Pokémon to the exact Sword/Shield learnset key."""
    return resolve_pokemon_id(
        pokemon.get("Pokemon") or pokemon.get("pokemon") or pokemon.get("name"),
        gender=pokemon.get("Gender") or pokemon.get("gender"),
        nature=pokemon.get("Nature") or pokemon.get("nature"),
        form=pokemon.get("Form") or pokemon.get("form"),
    )


def _learnset_record(pokemon: dict, learnsets_data: dict) -> tuple[str | None, dict | None]:
    key = resolve_learnset_key(pokemon)
    if key is None or not isinstance(learnsets_data, dict):
        return key, None
    records = learnsets_data.get("pokemon")
    if not isinstance(records, dict):
        return key, None
    record = records.get(key)
    return key, record if isinstance(record, dict) else None


def strategy_move_is_supported(
    pokemon: dict,
    move_name: str,
    learnsets_data: dict,
) -> bool | None:
    """Return whether a move may be generated as a strategy recommendation.

    ``None`` means the exact Pokémon/form or its learnset could not be resolved;
    callers should treat that as unknown rather than as proof of illegality.
    ``False`` includes Egg-only and DLC-only methods because those method records
    are deliberately excluded from automated strategy recommendations.
    """
    _, record = _learnset_record(pokemon, learnsets_data)
    if record is None:
        return None
    moves = record.get("moves")
    if not isinstance(moves, dict):
        return None
    methods = moves.get(move_name)
    if methods is None:
        return False
    if not isinstance(methods, list):
        return None
    return any(
        isinstance(method, dict)
        and method.get("supported_for_strategy") is True
        for method in methods
    )



def supported_strategy_move_methods(
    pokemon: dict,
    move_name: str,
    learnsets_data: dict,
) -> tuple[dict, ...]:
    """Return supported base-Sword acquisition methods for one strategy move.

    The returned method dictionaries are copies so UI/planning callers can inspect
    TM/TR item codes or level-up methods without mutating the learnset dataset.
    Older finalized datasets that predate the explicit ``supported_for_strategy``
    flag are handled conservatively: Egg and DLC-only methods remain excluded.
    """
    _, record = _learnset_record(pokemon, learnsets_data)
    if record is None:
        return ()
    moves = record.get("moves")
    if not isinstance(moves, dict):
        return ()
    methods = moves.get(move_name)
    if not isinstance(methods, list):
        return ()

    supported: list[dict] = []
    for method in methods:
        if not isinstance(method, dict):
            continue
        if method.get("supported_for_strategy") is True:
            supported.append(dict(method))
            continue
        if "supported_for_strategy" in method:
            continue
        method_name = str(method.get("method") or "").strip().casefold()
        if method_name == "egg":
            continue
        if method.get("dlc_only") is True:
            continue
        supported.append(dict(method))
    return tuple(supported)

def supported_strategy_move_names(
    pokemon: dict,
    learnsets_data: dict,
    moves_data: list[dict] | None = None,
) -> tuple[str, ...]:
    """Return base-Sword moves safe for automated strategy recommendations.

    When ``moves_data`` is supplied, candidates are additionally restricted to
    moves with Battle Compass mechanics definitions. This prevents a strategy
    feature from recommending a legal move that the engine cannot model.
    """
    _, record = _learnset_record(pokemon, learnsets_data)
    if record is None:
        return ()
    raw_moves = record.get("moves")
    if not isinstance(raw_moves, dict):
        return ()

    modeled_moves: set[str] | None = None
    if moves_data is not None:
        modeled_moves = {
            str(move.get("Move"))
            for move in moves_data
            if isinstance(move, dict)
            and isinstance(move.get("Move"), str)
            and move.get("Move")
        }

    candidates: list[str] = []
    for move_name, methods in raw_moves.items():
        if not isinstance(move_name, str) or not isinstance(methods, list):
            continue
        if modeled_moves is not None and move_name not in modeled_moves:
            continue
        if any(
            isinstance(method, dict)
            and method.get("supported_for_strategy") is True
            for method in methods
        ):
            candidates.append(move_name)
    return tuple(sorted(candidates))
