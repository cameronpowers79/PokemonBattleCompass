"""Team coverage calculations for Sword/Shield planning UI and recommendations.

This module calculates *type matchups*, not damage or battle outcomes.
It has no UI, persistence, learnset, or strategy-ranking dependencies.

Inputs are the existing Battle Compass Type1/Type2, Ability, and Move1..4
team records. Callers can also supply separate planned-move choices.
A type's defensive multiplier is the arithmetic mean across team members.
An immunity star is separate: one immune member does not make the team immune.
Offensive coverage is the best single-type effectiveness from all selected
planned damaging moves, not the product or average of different attacks.

Do not treat these coverage values as a promise of a safe switch or a KO.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


# Battle Compass stores the attacking type -> defending type chart, with
# omitted entries implicitly equal to 1.0.
IMMUNITY_ABILITIES: dict[str, frozenset[str]] = {
    "Fire": frozenset({"flash fire"}),
    "Water": frozenset({"water absorb", "storm drain", "dry skin"}),
    "Electric": frozenset({"volt absorb", "motor drive", "lightning rod"}),
    "Grass": frozenset({"sap sipper"}),
    "Ground": frozenset({"levitate"}),
}
WEATHER_BALL_TYPES = {
    "sun": "Fire", "harsh sunlight": "Fire", "sunny": "Fire",
    "rain": "Water", "rainy": "Water", "heavy rain": "Water",
    "sandstorm": "Rock", "sand": "Rock",
    "hail": "Ice", "snow": "Ice",
}
# These moves do not express normal type-multiplier-based damage.
NON_STANDARD_DAMAGE = frozenset({"fixed", "ohko", "custom"})


def _first(record: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        value = record.get(name)
        if value is not None and value != "":
            return value
    return None


def _name(member: Mapping[str, Any], index: int) -> str:
    return str(_first(member, "Nickname", "nickname", "Pokemon", "pokemon", "name") or f"Member {index + 1}")


def _types(member: Mapping[str, Any], known_types: set[str]) -> tuple[str, ...]:
    raw = member.get("types")
    values = raw if isinstance(raw, (tuple, list)) else (
        _first(member, "Type1", "type1"), _first(member, "Type2", "type2")
    )
    result = []
    for value in values:
        if isinstance(value, str):
            resolved = next((name for name in known_types if name.casefold() == value.strip().casefold()), None)
            if resolved is not None and resolved not in result:
                result.append(resolved)
    return tuple(result)


def _selected_moves(member: Mapping[str, Any], index: int, planned_moves: Mapping[Any, Sequence[Any]] | None) -> list[str]:
    if planned_moves is not None:
        # Planner keys may be stable slots, IDs, or Pokémon names; a supplied
        # override takes precedence, including an intentionally empty list.
        keys = [index, str(index), member.get("id"), member.get("ID"),
                member.get("Pokemon"), member.get("pokemon"), member.get("Nickname")]
        for key in keys:
            if key is not None and key in planned_moves:
                values = planned_moves[key]
                return [str(v).strip() for v in values if isinstance(v, str) and v.strip()][:4]
    direct = member.get("planned_moves")
    if direct is None:
        direct = member.get("moves")
    if isinstance(direct, (list, tuple)):
        result = [str(v).strip() for v in direct if isinstance(v, str) and v.strip()]
    else:
        result = [str(member.get(f"Move{i}")).strip() for i in range(1, 5)
                  if member.get(f"Move{i}") and str(member.get(f"Move{i}")).strip().lower() not in {"none", "-"}]
    return result[:4]


def _lookup_moves(moves_data: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    if isinstance(moves_data, Mapping):
        return {str(key).casefold(): value for key, value in moves_data.items() if isinstance(value, Mapping)}
    return {str(record.get("Move", "")).casefold(): record for record in moves_data if isinstance(record, Mapping)}


def _move_type(move: Mapping[str, Any], weather: str | None) -> tuple[str | None, bool]:
    move_name = str(_first(move, "Move", "name") or "").casefold()
    move_type = _first(move, "Type", "type")
    if move_name == "weather ball":
        if weather is None:
            return None, True   # Conditional; do not assume an active weather.
        return WEATHER_BALL_TYPES.get(weather.strip().casefold(), "Normal"), False
    # Explicitly avoid claiming a fixed type for other context-sensitive moves.
    if move_name in {"terrain pulse", "hidden power", "judgment", "natural gift", "revelation dance", "multi-attack", "techno blast"}:
        return None, True
    return str(move_type) if move_type else None, False


def type_multiplier(attack_type: str, defender_types: Sequence[str],
                    type_chart: Mapping[str, Mapping[str, float]]) -> float:
    """Type chart multiplier for a single move against one Pokémon."""
    if attack_type not in type_chart:
        raise ValueError(f"Unknown attack type: {attack_type}")
    result = 1.0
    for defending_type in defender_types:
        if defending_type not in type_chart:
            raise ValueError(f"Unknown defender type: {defending_type}")
        result *= float(type_chart[attack_type].get(defending_type, 1))
    return result


def team_coverage(
    team: Sequence[Mapping[str, Any]],
    type_chart: Mapping[str, Mapping[str, float]],
    moves_data: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
    *,
    planned_moves: Mapping[Any, Sequence[str]] | None = None,
    weather: str | None = None,
) -> dict[str, Any]:
    """Return 18-type defensive and offensive coverage ready for UI consumption.

    Defensive: average attacking-type multiplier over valid team members.
      `immunity_members` always reports abilities/type immunities separately.
    Offensive: highest type effectiveness of any *planned* damaging move
      against a single defending type. `contributors` lists all moves with
      super-effective coverage (rather than just the strongest).

    Unknown team typing is *excluded* from defense and reported in `warnings`;
    unknown planned moves are skipped and reported (never given fictitious
    neutral or super-effective coverage). No implicit weather is assumed.
    """
    if not type_chart:
        raise ValueError("A nonempty type chart is required")
    type_names = list(type_chart)
    known_types = set(type_names)
    moves_by_name = _lookup_moves(moves_data)
    warnings: list[str] = []
    defenders: list[dict[str, Any]] = []
    attackers: list[dict[str, Any]] = []
    for index, member in enumerate(team[:6]):
        if not isinstance(member, Mapping):
            warnings.append(f"Team slot {index + 1}: invalid Pokémon record")
            continue
        name = _name(member, index)
        types = _types(member, known_types)
        ability = str(_first(member, "Ability", "ability") or "")
        if types:
            defenders.append({"name": name, "slot": index, "types": types, "ability": ability})
        else:
            warnings.append(f"{name}: missing or unrecognized defensive typing")
        for move_name in _selected_moves(member, index, planned_moves):
            move = moves_by_name.get(move_name.casefold())
            if move is None:
                warnings.append(f"{name}: unknown planned move '{move_name}'")
                continue
            category = str(_first(move, "Category", "category") or "").casefold()
            if category == "status":
                continue
            method = str(_first(move, "DamageMethod", "damage_method") or "").casefold()
            if method in NON_STANDARD_DAMAGE:
                warnings.append(f"{name}: '{move_name}' uses nonstandard damage and is not included in type coverage")
                continue
            move_type, conditional = _move_type(move, weather)
            if conditional:
                warnings.append(f"{name}: '{move_name}' has conditional typing; select a battle condition to assess it")
                continue
            if move_type not in known_types:
                warnings.append(f"{name}: unsupported type for '{move_name}'")
                continue
            attackers.append({"name": name, "slot": index, "move": move_name,
                              "move_type": move_type, "damage_method": method})

    result: dict[str, Any] = {"team_size": len(team[:6]),
                              "defensive_members": len(defenders),
                              "planned_attacks": len(attackers),
                              "weather": weather,
                              "defensive": {}, "offensive": {}, "warnings": warnings}
    for attack_type in type_names:
        breakdown = []
        for mon in defenders:
            base = type_multiplier(attack_type, mon["types"], type_chart)
            ability_name = mon["ability"].strip().casefold()
            # Wonder Guard blocks direct damaging moves unless they are
            # super-effective against the holder. Neutral and resisted hits
            # are therefore immune, as are types already blocked by typing.
            # This type-coverage model does not represent indirect damage,
            # ability-bypassing effects, or battle-specific exceptions.
            ability_immune = (
                ability_name in IMMUNITY_ABILITIES.get(attack_type, frozenset())
                or (ability_name == "wonder guard" and base <= 1.0)
            )
            effective = 0.0 if ability_immune else base
            immunity_source = (
                "typing" if base == 0 else "ability" if ability_immune else None
            )
            breakdown.append({"pokemon": mon["name"], "slot": mon["slot"],
                              "types": list(mon["types"]), "ability": mon["ability"],
                              "multiplier": effective,
                              "immune": effective == 0,
                              "immunity_source": immunity_source})
        avg = sum(x["multiplier"] for x in breakdown) / len(breakdown) if breakdown else None
        result["defensive"][attack_type] = {
            "average": avg,
            "immunity_members": [x for x in breakdown if x["immune"]],
            "has_immunity": any(x["immune"] for x in breakdown),
            "members": breakdown,
        }
        contributors = []
        best = None
        for move in attackers:
            effectiveness = type_multiplier(move["move_type"], [attack_type], type_chart)
            # Freeze-Dry is super effective against Water even though Ice
            # otherwise hits Water for 1/2 damage.
            if move["move"].casefold() == "freeze-dry" and attack_type == "Water":
                effectiveness = 2.0
            # Flying Press applies Fighting * Flying effectiveness.
            if move["move"].casefold() == "flying press":
                effectiveness *= type_multiplier("Flying", [attack_type], type_chart)
            best = effectiveness if best is None else max(best, effectiveness)
            if effectiveness > 1:
                contributors.append({"pokemon": move["name"], "slot": move["slot"],
                                     "move": move["move"], "move_type": move["move_type"],
                                     "multiplier": effectiveness})
        result["offensive"][attack_type] = {
            "best_multiplier": best,
            "covered": bool(contributors),
            "contributors": contributors,
        }
    return result
