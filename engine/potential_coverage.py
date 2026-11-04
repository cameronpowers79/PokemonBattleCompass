"""Estimate realistic offensive *potential* for a prospective team member.

Step 3 of Team Coverage: no UI, persistence, or recommendation-ranking changes.
The candidate has only four move slots. Locked/strategy-essential moves take
precedence; remaining slots are assigned from supported Sword/Shield learnsets
by marginal improvement over the *already planned* team's type coverage.

These are type-matchup opportunities, NOT projected damage/KO estimates.
Moves whose acquisition is legal but not verified for the user's current point
in the story are marked as timing-unverified (never promised available now).
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from engine.base_stats_registry import role_base_stats
from engine.coverage_planning import catalog_team_member
from engine.learnsets import supported_strategy_move_methods, supported_strategy_move_names
from engine.team_coverage import _lookup_moves, _move_type, team_coverage, type_multiplier


# Reusing Step 1's move semantics avoids crediting nonstandard fixed damage or
# conditional type without a selected battle condition.
_NONSTANDARD = frozenset({"fixed", "ohko", "custom"})


def _name_of(pokemon: Mapping[str, Any]) -> str:
    return str(pokemon.get("Pokemon") or pokemon.get("pokemon") or pokemon.get("name") or "").strip()


def _move_effectiveness(move: Mapping[str, Any], defending_type: str,
                        chart: Mapping[str, Mapping[str, float]], weather: str | None) -> float | None:
    category = str(move.get("Category") or move.get("category") or "").casefold()
    if category not in {"physical", "special"}:
        return None
    method = str(move.get("DamageMethod") or "").casefold()
    if method in _NONSTANDARD:
        return None
    name = str(move.get("Move") or "").casefold()
    attack_type, conditional = _move_type(move, weather)
    if conditional or attack_type not in chart:
        return None
    effect = type_multiplier(attack_type, [defending_type], chart)
    if name == "freeze-dry" and defending_type == "Water":
        return 2.0
    if name == "flying press":
        effect *= type_multiplier("Flying", [defending_type], chart)
    return effect


def _move_quality(move: Mapping[str, Any], pokemon: dict[str, Any]) -> float:
    """Conservative tie-break ONLY, never a damage or OHKO prediction."""
    category = str(move.get("Category") or "").casefold()
    method = str(move.get("DamageMethod") or "").casefold()
    stats = role_base_stats(pokemon, "special" if category == "special" else "physical")
    attack_stat = (stats or {}).get("SPA" if category == "special" else "ATK", 80)
    if method == "usedef":
        attack_stat = (stats or {}).get("DEF", attack_stat)
    if method == "targetatk":
        attack_stat = 80  # user's Attack is not the damage source
    power = move.get("Power")
    # Dynamic-power moves are viable, but their actual power is not assumed.
    power_proxy = float(power) if isinstance(power, (float, int)) and power > 0 else 60.0
    accuracy = move.get("Accuracy")
    accuracy_proxy = max(0.25, min(1.0, float(accuracy) / 100)) if isinstance(accuracy, (int, float)) and accuracy > 0 else 1.0
    move_type = str(move.get("Type") or "")
    own_types = (str(pokemon.get("Type1") or ""), str(pokemon.get("Type2") or ""))
    stab_bonus = 1.15 if move_type in own_types else 1.0
    return attack_stat * min(power_proxy, 150) * accuracy_proxy * stab_bonus


def _timing(methods: Sequence[Mapping[str, Any]], *, level: int | None,
            obtainable_items: set[str] | None) -> str:
    """Current access is confirmed only when enough explicit context exists."""
    if level is not None and any(
        str(m.get("method", "")).casefold() == "level"
        and isinstance(m.get("level"), int) and m["level"] <= level
        for m in methods
    ):
        return "available_now"
    if obtainable_items is not None and any(
        str(m.get("method", "")).casefold() in {"tm", "tr"}
        and str(m.get("item") or "").casefold() in obtainable_items
        for m in methods
    ):
        return "available_now"
    # We cannot infer location unlocks, inventory, or tutor availability from
    # an item code alone; don't claim a move is already obtainable.
    return "timing_unverified"


def evaluate_candidate_coverage(
    current_team: Sequence[Mapping[str, Any]],
    candidate: Mapping[str, Any],
    type_chart: Mapping[str, Mapping[str, float]],
    moves_data: Sequence[Mapping[str, Any]],
    learnsets_data: dict[str, Any],
    *,
    protected_moves: Sequence[str] = (),
    level: int | None = None,
    obtainable_items: set[str] | None = None,
    weather: str | None = None,
) -> dict[str, Any]:
    """Evaluate a *single* candidate, without changing ranking or saved moves.

    `current_team` carries the player's actual *planned* moves in Move1..Move4
    or `planned_moves`. `protected_moves` are user-locked or essential strategy
    moves the optimizer must keep, in their supplied order. Callers should pass
    only moves truly essential to that specific candidate/strategy—not every
    possible status or setup move. Four total slots are enforced.

    The search is bounded: choose the candidate move with the greatest marginal
    increase in single-type offensive coverage at each available slot; use
    conservative move quality only to break equal-coverage ties. All moves
    must have supported learnset methods. Unknown legality is not credited.
    """
    if len(current_team) >= 6:
        raise ValueError("The team already has six Pokémon; remove a member before evaluating an addition")
    if not isinstance(candidate, Mapping) or not _name_of(candidate):
        raise ValueError("Candidate Pokémon identity is required")
    if len(protected_moves) > 4:
        raise ValueError("A Pokémon cannot have more than four protected moves")

    mon = dict(candidate)
    mon["Pokemon"] = _name_of(candidate)
    # Journey targets store evolution-form typing in `types` rather than
    # Type1/Type2. Resolve it for STAB tie-breaks without mutating the record.
    if isinstance(mon.get("types"), Mapping) and not mon.get("Type1"):
        resolved = catalog_team_member(mon, form=str(mon.get("Form") or ""),
                                       gender=str(mon.get("Gender") or ""))
        mon["Type1"], mon["Type2"] = resolved["Type1"], resolved["Type2"]
    move_lookup = _lookup_moves(moves_data)
    legal = set(supported_strategy_move_names(mon, learnsets_data, list(moves_data)))
    warnings: list[str] = []

    fixed: list[str] = []
    for raw in protected_moves:
        name = str(raw).strip()
        if not name or name in fixed:
            continue
        if name not in legal:
            raise ValueError(f"{mon['Pokemon']}: protected move '{name}' is not a confirmed supported base-game move")
        fixed.append(name)
    if len(fixed) > 4:
        raise ValueError("More than four unique protected moves")

    before = team_coverage(current_team, type_chart, moves_data, weather=weather)
    initial = {t: float(info["best_multiplier"] or 0.0) for t, info in before["offensive"].items()}
    best_by_type = dict(initial)
    chosen = list(fixed)
    move_evidence: dict[str, dict[str, Any]] = {}

    def analyze(name: str) -> dict[str, Any] | None:
        move = move_lookup.get(name.casefold())
        if move is None:
            return None
        values = {t: _move_effectiveness(move, t, type_chart, weather) for t in type_chart}
        if not any(v is not None and v > 1 for v in values.values()):
            return None
        methods = supported_strategy_move_methods(mon, name, learnsets_data)
        return {
            "name": name,
            "type": str(move.get("Type") or ""),
            "category": str(move.get("Category") or ""),
            "targets": {t: v for t, v in values.items() if v is not None and v > 1},
            "values": values,
            "quality_tiebreak": _move_quality(move, mon),
            "availability": _timing(methods, level=level,
                                    obtainable_items={x.casefold() for x in obtainable_items} if obtainable_items is not None else None),
            "methods": [dict(m) for m in methods],
        }

    legal_attacks = {n: info for n in sorted(legal) if (info := analyze(n)) is not None}
    for name in fixed:
        info = legal_attacks.get(name)
        if info:
            move_evidence[name] = info
            for t, value in info["values"].items():
                if value is not None:
                    best_by_type[t] = max(best_by_type[t], value)

    def gain(info: dict[str, Any]) -> float:
        return sum(max(0.0, value - best_by_type[t]) for t, value in info["values"].items()
                   if value is not None and value > 1)

    # Rank independently useful alternative moves against the *original*
    # team's gaps (not a fictitious unlimited-moveset combination).
    coverage_options = []
    for info in legal_attacks.values():
        newly = [t for t, v in info["values"].items() if v is not None and v > 1
                 and not before["offensive"][t]["covered"]]
        if newly:
            coverage_options.append({"move": info["name"], "type": info["type"],
                                     "new_types": newly,
                                     "availability": info["availability"],
                                     "selected": info["name"] in chosen,
                                     "_quality": info["quality_tiebreak"]})
    coverage_options.sort(key=lambda info: (-len(info["new_types"]), -info["_quality"], info["move"]))

    remaining = [info for n, info in legal_attacks.items() if n not in chosen]
    while len(chosen) < 4 and remaining:
        picked = max(remaining, key=lambda info: (round(gain(info), 8), info["quality_tiebreak"], info["name"]))
        if gain(picked) <= 0:
            break
        chosen.append(picked["name"])
        move_evidence[picked["name"]] = picked
        for t, value in picked["values"].items():
            if value is not None:
                best_by_type[t] = max(best_by_type[t], value)
        remaining.remove(picked)

    mon["planned_moves"] = chosen
    after = team_coverage([*current_team, mon], type_chart, moves_data, weather=weather)
    gained = [t for t in type_chart if (after["offensive"][t]["best_multiplier"] or 0) >
              max(1.0, initial[t]) and after["offensive"][t]["covered"]]
    # Expose only new coverage opportunities, not all existing team coverages.
    newly_covered = [t for t in type_chart if not before["offensive"][t]["covered"]
                     and after["offensive"][t]["covered"]]
    if not legal:
        warnings.append("Candidate learnset has no confirmed supported modeled moves")
    if any(info["availability"] == "timing_unverified" for info in move_evidence.values()):
        warnings.append("Some proposed moves are legal but their current acquisition timing is unverified")

    # Selection happens after options were computed; flag the final picks.
    for option in coverage_options:
        option["selected"] = option["move"] in chosen
        option.pop("_quality")

    moves_public = [
        {k: v for k, v in move_evidence[name].items() if k not in {"values", "quality_tiebreak"}}
        for name in chosen if name in move_evidence
    ]
    return {
        "pokemon": mon["Pokemon"],
        "protected_moves": list(fixed),
        "proposed_moves": chosen,
        "open_slots": 4 - len(chosen),
        "newly_covered_types": newly_covered,
        "improved_types": gained,
        "coverage_gain_count": len(newly_covered),
        "before": {t: before["offensive"][t]["best_multiplier"] for t in type_chart},
        "after": {t: after["offensive"][t]["best_multiplier"] for t in type_chart},
        "moves": moves_public,
        "coverage_move_options": coverage_options[:20],
        "warnings": warnings,
    }
