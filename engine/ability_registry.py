"""Sword/Shield species/form Ability eligibility (recommendation-side only).

Load data/abilities_registry_swsh.json; never use eligibility to overwrite a saved
Pokemon's actual Ability in Battle Compass live tactical calculations.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=4)
def load_ability_registry(path: str | Path | None = None) -> dict:
    registry_path = Path(path) if path is not None else Path(__file__).resolve().parent.parent / 'data' / 'abilities_registry_swsh.json'
    with registry_path.open(encoding='utf-8') as source:
        return json.load(source)['pokemon']


def eligible_abilities(pokemon_id: str, registry: dict | None = None) -> tuple[str, ...]:
    """Return available normal + Hidden Ability names for an exact canonical ID.

    The caller should pass an ID from pokemon_identity.resolve_pokemon_id,
    not a display name. Unknown IDs return no eligibility, not a guessed form.
    """
    entries = load_ability_registry() if registry is None else registry
    entry = entries.get(str(pokemon_id or '').casefold())
    if not isinstance(entry, dict):
        return ()
    return tuple(dict.fromkeys([*(entry.get('normal') or []), *([entry['hidden']] if entry.get('hidden') else [])]))


def ability_eligibility(pokemon_id: str, ability: str, registry: dict | None = None) -> str | None:
    """Return 'normal', 'hidden', or None for a species/form and Ability."""
    entries = load_ability_registry() if registry is None else registry
    entry = entries.get(str(pokemon_id or '').casefold())
    if not isinstance(entry, dict):
        return None
    desired = str(ability or '').casefold()
    if any(str(a).casefold() == desired for a in entry.get('normal', [])):
        return 'normal'
    if str(entry.get('hidden') or '').casefold() == desired and desired:
        return 'hidden'
    return None
