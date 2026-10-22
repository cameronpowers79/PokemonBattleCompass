"""Potential strategic fit and concrete supporting evidence for planning candidates.

Separate from ranked team recommendations: candidate ranking remains unchanged.
"""
from __future__ import annotations
from dataclasses import dataclass
from engine.strategy_capabilities import (
    _potential_ability_options, _recognize_capability_keys, _weighted_role_quality,
    _role_stat_bonus, _canonical_strategy_key, _planning_types,
    _weather_intent_fit, _screen_offense_fit, _WEATHER_MOVE, _WEATHER_BENEFIT_ABILITIES,
)
from engine.learnsets import supported_strategy_move_names

@dataclass(frozen=True)
class StrategyFit:
    fraction: float
    label: str
    evidence: str
    ability: str

# Fixed strategy-relative quality reference points, not per-page min/max.
# Calibrated to the existing scoring categories, and kept independent of
# readiness/rank bonuses. Thus a poor candidate stays poor even alone.
_REFERENCES = {
    "poison_attrition": 390.0, "poison_offensive_pressure": 400.0,
    "screen_control": 680.0, "setup_offense": 330.0,
    "status_control_punish": 340.0, "weather_control": 400.0,
    "defensive_attrition": 325.0,
}
_EXAMPLES = {
    "Recover": "Recover restores HP", "Roost": "Roost restores HP", "Rest": "Rest restores HP but induces sleep",
    "Baneful Bunker": "Baneful Bunker protects and poisons contact attackers",
    "Spiky Shield": "Spiky Shield protects and damages contact attackers",
    "Obstruct": "Obstruct protects and lowers contact attackers' Defense",
    "King's Shield": "King's Shield protects and lowers contact attackers' Attack",
    "Iron Defense": "Iron Defense raises Defense", "Body Press": "Body Press uses Defense to deal damage",
    "Toxic": "Toxic applies worsening poison", "Toxic Spikes": "Toxic Spikes poisons eligible switch-ins",
    "Venoshock": "Venoshock increases its power against poisoned targets",
    "Hex": "Hex increases its power against statused targets",
    "Will-O-Wisp": "Will-O-Wisp burns targets and weakens their physical attacks",
    "Reflect": "Reflect reduces physical damage", "Light Screen": "Light Screen reduces special damage",
    "Calm Mind": "Calm Mind raises Special Attack and Special Defense",
    "Swords Dance": "Swords Dance sharply raises Attack",
    "Nasty Plot": "Nasty Plot sharply raises Special Attack",
    "Leech Seed": "Leech Seed drains HP each turn",
    "Sand Tomb": "Sand Tomb traps and deals residual damage",
    "Infestation": "Infestation traps and deals residual damage",
    "Rain Dance": "Rain Dance establishes rain", "Sunny Day": "Sunny Day establishes sun",
    "Sandstorm": "Sandstorm establishes sandstorm", "Hail": "Hail establishes hail",
    "Protect": "Protect blocks an attack", "Detect": "Detect blocks an attack",
}
_ABILITY = {
    "regenerator": "Regenerator restores HP upon switching out",
    "iron barbs": "Iron Barbs damages contact attackers", "rough skin": "Rough Skin damages contact attackers",
    "stamina": "Stamina raises Defense when hit", "levitate": "Levitate grants Ground immunity",
    "prankster": "Prankster gives status moves priority",
    "corrosion": "Corrosion permits poisoning Steel- and Poison-type targets",
    "merciless": "Merciless guarantees critical hits against poisoned targets",
    "drizzle": "Drizzle summons rain", "drought": "Drought summons sun",
    "sand stream": "Sand Stream summons sandstorm", "snow warning": "Snow Warning summons hail",
    "swift swim": "Swift Swim doubles Speed in rain", "chlorophyll": "Chlorophyll doubles Speed in sun",
    "sand rush": "Sand Rush doubles Speed in sandstorm", "slush rush": "Slush Rush doubles Speed in hail",
}
_PRIORITY = {
    "poison_attrition": ("Toxic", "Toxic Spikes", "Recover", "Baneful Bunker", "Protect", "Rest", "Leech Seed"),
    "poison_offensive_pressure": ("Toxic", "Toxic Spikes", "Poison Gas", "Venoshock", "Hex"),
    "screen_control": ("Reflect", "Light Screen"),
    "setup_offense": ("Swords Dance", "Nasty Plot", "Calm Mind", "Dragon Dance", "Agility"),
    "status_control_punish": ("Will-O-Wisp", "Thunder Wave", "Toxic", "Hypnosis", "Hex", "Venoshock"),
    "weather_control": ("Rain Dance", "Sunny Day", "Sandstorm", "Hail", "Thunder", "Hurricane", "Blizzard"),
    "defensive_attrition": ("Recover", "Baneful Bunker", "Obstruct", "Spiky Shield", "Iron Defense", "Body Press", "Leech Seed", "Toxic Spikes", "Sand Tomb", "Protect", "Rest"),
}
_RELEVANT_ABILITIES = {
    "poison_attrition": {"regenerator", "corrosion"},
    "poison_offensive_pressure": {"corrosion", "merciless"},
    "screen_control": {"prankster"},
    "setup_offense": {"speed boost", "moxie"},
    "status_control_punish": {"prankster"},
    "weather_control": {"drizzle", "drought", "sand stream", "snow warning", "swift swim", "chlorophyll", "sand rush", "slush rush"},
    "defensive_attrition": {"regenerator", "iron barbs", "rough skin", "stamina", "levitate"},
}

def evaluate_pokemon_fit(strategy: str, pokemon: dict, moves_data: list[dict], learnsets: dict, *, ability: str = "", role: str = "", weather_focus: str = "") -> StrategyFit:
    key = _canonical_strategy_key(strategy)
    if key == "strongest_matchup":
        return StrategyFit(0.5, "Flexible", "Strongest Matchup has no required team-building roles; choose this Pokémon for its battle coverage and personal preference.", ability)
    names = set(supported_strategy_move_names(pokemon, learnsets, moves_data))
    lookup = {m["Move"]: m for m in moves_data if isinstance(m, dict) and isinstance(m.get("Move"), str)}
    options = [(ability, "selected")] if ability else list(_potential_ability_options(pokemon))
    if not options: options = [("", "unspecified")]
    best = None
    focus = weather_focus.upper()
    assigned_role = role.lower()
    for option, _ in options:
        build = dict(pokemon, Ability=option)
        caps = _recognize_capability_keys(build, tuple(names), lookup)
        specific = None
        if key == "screen_control" and assigned_role == "beneficiary":
            specific = _screen_offense_fit(build)
        elif key == "weather_control" and focus in _WEATHER_MOVE and assigned_role in {"setter", "beneficiary"}:
            specific = _weather_intent_fit(build, names, focus, assigned_role, lookup)
        if (key == "screen_control" and assigned_role == "beneficiary") or (key == "weather_control" and focus in _WEATHER_MOVE and assigned_role in {"setter", "beneficiary"}):
            if specific is None:
                raw = 0.0
            else:
                raw = specific[0]
        else:
            raw = _weighted_role_quality(key, build, names, caps, learnsets) + _role_stat_bonus(key, build, names, caps)
        if best is None or raw > best[0]: best = (raw, option, caps, specific)
    raw, selected_ability, caps, specific = best
    reference = _REFERENCES.get(key, 400.0)
    if key == "screen_control" and assigned_role == "beneficiary":
        reference = 520.0
    elif key == "weather_control" and focus in _WEATHER_MOVE:
        reference = 1000.0 if assigned_role == "setter" else 620.0 if assigned_role == "beneficiary" else reference
    fraction = max(0.0, min(1.0, raw / reference))
    label = ("Excellent" if fraction >= .82 else "Good" if fraction >= .62 else
             "Moderate" if fraction >= .42 else "Limited" if fraction >= .22 else "Poor")
    if specific is not None:
        # The same role-specific evidence that ranked the candidate must explain the meter.
        picked = [specific[1]]
    elif assigned_role in {"setter", "beneficiary"} and key in {"screen_control", "weather_control"}:
        picked = []
    elif key == "weather_control" and focus in _WEATHER_MOVE:
        weather_move = _WEATHER_MOVE[focus]
        picked = [_EXAMPLES[weather_move]] if weather_move in names else []
    else:
        picked = [_EXAMPLES[n] for n in _PRIORITY.get(key, ()) if n in names and n in _EXAMPLES][:3]
    if key == "defensive_attrition" and "Iron Defense" in names and "Body Press" in names:
        picked = ["Iron Defense strengthens Body Press's Defense-based damage"] + [p for p in picked if not p.startswith(('Iron Defense ', 'Body Press '))]
    a = selected_ability.casefold()
    if specific is None and a in _RELEVANT_ABILITIES.get(key, set()) and a in _ABILITY:
        picked.insert(0, _ABILITY[a])
    if not picked and raw > 0 and key == "setup_offense":
        if "PHYSICAL_SETUP" in caps or "SPECIAL_SETUP" in caps:
            moves = [n for n in ("Dragon Dance", "Agility", "Swords Dance", "Nasty Plot", "Calm Mind", "Bulk Up", "Coil") if n in names]
            picked = [(f"{', '.join(moves[:2])} provides offensive setup" if moves else "This Pokémon has recognized offensive setup tools")]
        elif "SPEED_SETUP" in caps or "SPEED_BOOST" in caps:
            picked = ["Speed-boosting tools support an offensive setup role"]
        elif "SETUP_FACILITATION" in caps:
            picked = ["Its supporting moves help teammates establish boosts"]
    if not picked:
        picked = ["No strong role-specific combination was identified" if raw == 0 else "This candidate offers a supporting contribution to the selected strategy"]
    else:
        picked = picked[:3]
    # Recommender summaries can be sentence fragments ("can establish Hail").
    # The fit section stands alone, so supply a subject instead of displaying
    # that fragment as a lowercase sentence. Preserve the full tactic detail.
    if picked and picked[0] and picked[0][0].islower():
        name = str(pokemon.get("Pokemon") or "This Pokémon").strip()
        if picked[0].startswith("its "):
            picked[0] = f"{name}'s {picked[0][4:]}"
        else:
            picked[0] = f"{name} {picked[0]}"
    evidence = "; ".join(picked) + "."
    if selected_ability and not ability and a in _RELEVANT_ABILITIES.get(key, set()):
        evidence += f" This fit assumes {selected_ability} is obtainable; check Ability availability."
    return StrategyFit(fraction, label, evidence, selected_ability)
