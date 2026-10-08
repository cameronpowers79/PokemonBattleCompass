"""Offline Sword/Shield species/form base-stat profiles for strategic planning.

Stats are *base* stats, never the player's actual battle stats. Dynamic
forms are returned as separate profiles, never blended or combined.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

from engine.pokemon_identity import resolve_pokemon_id

_PATH = Path(__file__).resolve().parents[1] / 'data' / 'pokemon_base_stats_swsh.json'
_KEYS = ('HP', 'ATK', 'DEF', 'SPA', 'SPD', 'SPE')


@lru_cache(maxsize=1)
def _rows() -> dict[str, dict[str, int]]:
    try:
        data = json.loads(_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    result = {}
    for row in data if isinstance(data, list) else []:
        if not isinstance(row, dict) or not isinstance(row.get('pokemon_id'), str):
            continue
        if all(type(row.get(k)) is int and 1 <= row[k] <= 255 for k in _KEYS):
            result[row['pokemon_id']] = {k: row[k] for k in _KEYS}
    return result


def base_stat_profiles(pokemon: dict) -> tuple[tuple[str, dict[str, int]], ...]:
    """Return named, legitimate stat states conditional on form mechanics.

    Aegislash changes stance in battle, Wishiwashi schools only above 25% HP
    at level >=20, and Galarian Darmanitan's Zen Mode requires its HA and
    at most half HP. Do not use multiple states as simultaneous stats.
    """
    pid = resolve_pokemon_id(pokemon.get('Pokemon'), gender=pokemon.get('Gender'),
                             nature=pokemon.get('Nature'), form=pokemon.get('Form'))
    if not pid:
        return ()
    names = [pid]
    ability = str(pokemon.get('Ability') or '').casefold()
    if pid in {'aegislash-shield', 'aegislash-blade', 'aegislash'}:
        names = ['aegislash-shield', 'aegislash-blade']
    elif pid in {'wishiwashi-solo', 'wishiwashi-school', 'wishiwashi'}:
        names = ['wishiwashi-solo', 'wishiwashi-school']
    elif pid.startswith('darmanitan-galar') and ability == 'zen mode':
        names = ['darmanitan-galar-standard', 'darmanitan-galar-zen']
    return tuple((name, _rows()[name]) for name in names if name in _rows())


def role_base_stats(pokemon: dict, role: str) -> dict[str, int] | None:
    """Select a valid state for ONE role; never synthesize best-of-six stats."""
    profiles = base_stat_profiles(pokemon)
    if not profiles:
        return None
    if role in {'physical', 'special', 'offense'}:
        stat = {'physical':'ATK', 'special':'SPA', 'offense':'ATK'}[role]
        if role == 'offense':
            return dict(max(profiles, key=lambda p: max(p[1]['ATK'], p[1]['SPA']))[1])
        return dict(max(profiles, key=lambda p: p[1][stat])[1])
    if role == 'defense':
        return dict(max(profiles, key=lambda p: p[1]['HP'] * (p[1]['DEF'] + p[1]['SPD']))[1])
    return dict(profiles[0][1])
