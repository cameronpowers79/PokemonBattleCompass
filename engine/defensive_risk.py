"""Gen VIII defensive setup risk estimates (not general battle damage overrides).

Accuracy and critical-hit estimates support the Defensive Attrition tactical
planner only. They do not modify the base Move Score or OHKO classifications.
"""
from __future__ import annotations

# Known Sword/Shield move effects not yet structured in moves.json.
_EVASION_BOOSTS = {"Minimize": 2, "Double Team": 1}
_ACCURACY_DROPS = {"Sand Attack": 1, "Smokescreen": 1, "Kinesis": 1,
                   "Flash": 1, "Mud Bomb": 0}  # damaging effects are excluded below
_MINIMIZE_COUNTERS = {
    "Body Slam", "Dragon Rush", "Flying Press", "Heat Crash",
    "Heavy Slam", "Steamroller", "Stomp", "Phantom Force", "Shadow Force",
}


def avoidance_setup(move: dict) -> tuple[str, int] | None:
    """Return (kind, stages) for deterministic, equipped, status setup.

    Move descriptions are used because the current move catalog doesn't
    expose Evasion/Accuracy stage-change fields. Do not infer secondary effects.
    """
    if not isinstance(move, dict) or move.get("Category") != "Status":
        return None
    name = str(move.get("Move") or "")
    if name in _EVASION_BOOSTS:
        return "evasion", _EVASION_BOOSTS[name]
    if name in _ACCURACY_DROPS and _ACCURACY_DROPS[name] > 0:
        return "accuracy", _ACCURACY_DROPS[name]
    return None


def accuracy_after_setup(move: dict, stages: int, *, minimize: bool = False,
                         opponent: dict | None = None) -> float:
    """Gen VIII hit probability after +evasion or -opponent accuracy.

    Ignores untracked live accuracy modifiers; counter moves bypass Minimize.
    """
    name = str(move.get("Move") or "")
    description = str(move.get("EffectDescription") or "").lower()
    if str((opponent or {}).get("Ability") or "") == "No Guard":
        return 1.0
    if "never misses" in description or "bypass" in description and "accuracy" in description:
        return 1.0
    if minimize and name in _MINIMIZE_COUNTERS:
        return 1.0
    value = move.get("Accuracy")
    try:
        base = float(value) / 100.0 if value not in (None, "") else 1.0
    except (ValueError, TypeError):
        base = 1.0
    # Negative net accuracy stages: multiplier 3/(3 + abs(stage)).
    return max(0.0, min(1.0, base * 3.0 / (3.0 + min(6, max(0, stages)))))


def critical_hit_probability(move: dict, opponent: dict | None = None) -> float:
    """Conservative critical-hit risk from catalog text and known abilities.

    Merciless requires target poison state, which Battle Compass doesn't track;
    it is represented as a conditional threat separately.
    """
    description = str(move.get("EffectDescription") or "").lower()
    if "always scores a critical hit" in description or "always lands a critical hit" in description:
        return 1.0
    if "increased chance for a critical hit" in description or "high critical-hit ratio" in description:
        return 0.125
    # Super Luck raises critical stage on attacking moves.
    if str((opponent or {}).get("Ability") or "") == "Super Luck":
        return 0.125
    return 1.0 / 24.0


def has_critical_threat(move: dict, opponent: dict | None = None) -> bool:
    return critical_hit_probability(move, opponent) >= 0.125 or str((opponent or {}).get("Ability") or "") == "Merciless"


def minimize_damage_multiplier(move: dict, *, minimize: bool) -> float:
    return 2.0 if minimize and str(move.get("Move") or "") in _MINIMIZE_COUNTERS else 1.0
