"""Strategic capability recognition and Poison tactical plan evaluation.

The reusable capability layer supports canonical strategy viability checks, while
the mature Poison tactical machinery below continues to evaluate live matchups.
Neither layer changes Move Score, Ratio, or Full Analysis calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from engine.calculations import (
    calculate_damage_range,
    calculate_incoming_multiplier,
    calculate_move_score,
    evaluate_team_matchups,
    get_moves,
    get_stat,
    get_move_type_multiplier,
)

from engine.mechanics import get_item_speed_multiplier
from engine.learnsets import supported_strategy_move_names, supported_strategy_move_methods
from engine.ability_registry import eligible_abilities, ability_eligibility
from engine.pokemon_identity import resolve_pokemon_id

CAPABILITY_LABELS: dict[str, str] = {
    # Existing keys stay in their original order for compatibility.
    "STATUS_POISON_RELIABLE": "Reliable Poison",
    "STATUS_POISON_TEAM_SETUP": "Team Poison Setup",
    "STATUS_POISON_CONTACT": "Conditional Poison",
    "POISON_EXPLOIT_DAMAGE": "Poison Exploitation",
    "POISON_EXPLOIT_CONTROL": "Poison Control",
    "RELIABLE_RECOVERY": "Reliable Recovery",
    "DAMAGE_RECOVERY": "Damage Recovery",
    "PROTECTION": "Protection",
    "SETUP_DENIAL": "Setup Denial",
    "SPECIAL_SETUP": "Special Setup",
    "SCREEN": "Screen Support",
    "DEFENSE_SETUP": "Defensive Setup",
    "MERCILESS": "Merciless",
    "REGENERATOR_SUSTAIN": "Regenerator Switching Sustain",
    "CORROSION": "Corrosion",

    # Screen Control beneficiaries / delivery.
    "DUAL_SCREEN": "Dual Screen Support",
    "PRIORITY_SCREEN": "Priority Screen Support",
    "FAST_SCREEN": "Fast Screen Support",
    "OFFENSIVE_PHYSICAL": "Physical Offense",
    "OFFENSIVE_SPECIAL": "Special Offense",
    "OFFENSIVE_MIXED": "Mixed Offense",

    # Setup Offense.
    "PHYSICAL_SETUP": "Physical Setup",
    "MIXED_SETUP": "Mixed Offensive Setup",
    "SPEED_SETUP": "Speed Setup",
    "SPEED_BOOST": "Speed Boost",
    "SETUP_FACILITATION": "Setup Facilitation",

    # Status Control & Punish.
    "STATUS_BURN_RELIABLE": "Reliable Burn",
    "STATUS_PARALYSIS_RELIABLE": "Reliable Paralysis",
    "STATUS_SLEEP_RELIABLE": "Reliable Sleep",
    "STATUS_YAWN": "Yawn Pressure",
    "STATUS_ANY_RELIABLE": "Reliable Status",
    "STATUS_EXPLOIT_DAMAGE": "Status Exploitation",
    "STATUS_EXPLOIT_ANY_DAMAGE": "Any-Status Exploitation",

    # Weather Control.
    "WEATHER_SET_RAIN": "Rain Setter",
    "WEATHER_SET_SUN": "Sun Setter",
    "WEATHER_SET_SAND": "Sand Setter",
    "WEATHER_SET_HAIL": "Hail Setter",
    "WEATHER_BENEFIT_RAIN": "Rain Beneficiary",
    "WEATHER_BENEFIT_SUN": "Sun Beneficiary",
    "WEATHER_BENEFIT_SAND": "Sand Beneficiary",
    "WEATHER_BENEFIT_HAIL": "Hail Beneficiary",

    # Defensive Attrition.
    "BODY_PRESS": "Defense-to-Damage",
    "CONTACT_PUNISHMENT": "Contact Punishment",
    "PASSIVE_CHIP": "Passive Chip",
}

_CAPABILITY_ORDER = tuple(CAPABILITY_LABELS)

_POISON_IMMUNE_ABILITIES = {"immunity", "comatose", "pastel veil"}

_FIT_RANK = {"Blocked": 0, "Risky": 1, "Viable": 2, "Strong": 3}
_VIABILITY_RANK = {"Incomplete": 0, "Viable": 1, "Strong": 2}


@dataclass(frozen=True)
class StrategicCapabilityResult:
    """Recognized strategic tools for one saved team member."""
    pokemon_name: str
    capability_keys: tuple[str, ...]
    capabilities: tuple[str, ...]


@dataclass(frozen=True)
class StrategyViabilityResult:
    """Team-level readiness for a canonical strategy.

    The evaluator is intentionally battle-agnostic. Pass equipped-move capability
    results when evaluating the current team's live readiness, or learnable-move
    capability results when evaluating recommendation-side potential.
    """
    strategy_key: str
    viability: str
    viability_rank: int
    summary: str
    required_roles: tuple[str, ...]
    satisfied_required_roles: tuple[str, ...]
    missing_required_roles: tuple[str, ...]
    supporting_roles: tuple[str, ...]
    contributing_pokemon: tuple[str, ...]
    one_change_away: bool


@dataclass(frozen=True)
class StrategyRecommendationCandidate:
    """One supported change evaluated against the current strategy package."""
    strategy_key: str
    recommendation_kind: str
    pokemon_name: str
    move_name: str | None
    replace_move_name: str | None
    score: float
    resulting_viability: str
    resulting_viability_rank: int
    roles_filled: tuple[str, ...]
    supporting_roles_added: tuple[str, ...]
    capability_keys_added: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class StrategyRecommendationResult:
    """Recommendation-side analysis for one canonical strategy."""
    strategy_key: str
    viability: StrategyViabilityResult
    pokemon_additions: tuple[StrategyRecommendationCandidate, ...]
    move_changes: tuple[StrategyRecommendationCandidate, ...]
    one_change_away: bool


@dataclass(frozen=True)
class PoisonAttritionPlanResult:
    """Poison / Attrition viability for one saved team member."""
    pokemon_name: str
    fit: str
    fit_rank: int
    summary: str
    reason: str
    action: str
    action_detail: str
    plan_kind: str
    can_override_direct: bool
    source_reliability: int
    strategic_depth: float
    safety_score: float
    team_setup_priority: int
    incoming_worst_score: float
    lead_pokemon_name: str
    lead_move: str
    opener_threat_move: str | None
    opener_threat_category: str | None
    opener_threat_type: str | None
    opener_threat_score: float
    opener_threat_multiplier: float
    strategy_branch: str = "poison_attrition"
    assumed_poisoned: bool = False
    state_assumption: str | None = None
    fallback_if_assumption_fails: str | None = None
    recommended_pokemon_name: str = ""
    conditional_move_name: str | None = None
    conditional_move_score: float | None = None


def _move_names(pokemon: dict) -> list[str]:
    names: list[str] = []
    for slot in range(1, 5):
        value = pokemon.get(f"Move{slot}")
        if isinstance(value, str) and value.strip():
            names.append(value.strip())
    return names


def _mechanics_tags(move: dict) -> set[str]:
    raw_tags = move.get("MechanicsTags", [])
    if not isinstance(raw_tags, list):
        return set()
    return {tag for tag in raw_tags if isinstance(tag, str) and tag}


def _negative_target_stage_control(move: dict) -> bool:
    if move.get("ActivationCondition") != "TargetPoisoned":
        return False
    stage_fields = (
        "AtkStageChange",
        "DefStageChange",
        "SpAStageChange",
        "SpDStageChange",
        "SpeStageChange",
    )
    return any(
        isinstance(move.get(field), (int, float)) and float(move.get(field, 0)) < 0
        for field in stage_fields
    )


def _poison_exploit_damage(move: dict) -> bool:
    if move.get("ActivationCondition") not in {"TargetPoisoned", "TargetAnyStatus"}:
        return False
    power = move.get("Power", 0)
    multiplier = move.get("ActivationPowerMultiplier", 1)
    return (
        isinstance(power, (int, float))
        and float(power) > 0
        and isinstance(multiplier, (int, float))
        and float(multiplier) > 1
    )


def _status_exploit_damage(move: dict) -> bool:
    """Return whether damage is explicitly amplified by target status."""
    if move.get("ActivationCondition") not in {"TargetPoisoned", "TargetAnyStatus"}:
        return False
    power = move.get("Power", 0)
    multiplier = move.get("ActivationPowerMultiplier", 1)
    return (
        isinstance(power, (int, float))
        and float(power) > 0
        and isinstance(multiplier, (int, float))
        and float(multiplier) > 1
    )


def _user_positive_stage_changes(move: dict) -> dict[str, float]:
    if str(move.get("StageChangeTarget") or "") != "User":
        return {}
    fields = {
        "atk": "AtkStageChange",
        "def": "DefStageChange",
        "spa": "SpAStageChange",
        "spd": "SpDStageChange",
        "spe": "SpeStageChange",
    }
    return {
        key: float(move.get(field) or 0.0)
        for key, field in fields.items()
        if isinstance(move.get(field), (int, float)) and float(move.get(field) or 0.0) > 0
    }


def _target_negative_stage_changes(move: dict) -> bool:
    target = str(move.get("StageChangeTarget") or "")
    if target not in {"Target", "Opponent"}:
        return False
    return any(
        isinstance(move.get(field), (int, float)) and float(move.get(field) or 0.0) < 0
        for field in (
            "AtkStageChange", "DefStageChange", "SpAStageChange",
            "SpDStageChange", "SpeStageChange",
        )
    )


def _base_speed_value(pokemon: dict) -> float | None:
    """Read base Speed only when a caller/data source exposes it explicitly."""
    for field in ("BaseSPE", "BaseSpe", "BaseSpeed", "Base Speed"):
        value = pokemon.get(field)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _weather_setter_from_move(move_name: str, move: dict) -> str | None:
    by_name = {
        "Rain Dance": "RAIN",
        "Sunny Day": "SUN",
        "Sandstorm": "SAND",
        "Hail": "HAIL",
    }
    if move_name in by_name:
        return by_name[move_name]
    weather = str(move.get("Weather") or move.get("WeatherEffect") or "").casefold()
    if "rain" in weather:
        return "RAIN"
    if "sun" in weather or "harsh sunlight" in weather:
        return "SUN"
    if "sand" in weather:
        return "SAND"
    if "hail" in weather or "snow" in weather:
        return "HAIL"
    return None


def _weather_setter_from_ability(ability: str) -> str | None:
    return {
        "drizzle": "RAIN",
        "drought": "SUN",
        "sand stream": "SAND",
        "snow warning": "HAIL",
    }.get(ability)


def _weather_benefits_from_ability(ability: str) -> set[str]:
    mapping = {
        "swift swim": {"RAIN"},
        "rain dish": {"RAIN"},
        "dry skin": {"RAIN"},
        "hydration": {"RAIN"},
        "chlorophyll": {"SUN"},
        "solar power": {"SUN"},
        "flower gift": {"SUN"},
        "sand rush": {"SAND"},
        "sand force": {"SAND"},
        "sand veil": {"SAND"},
        "slush rush": {"HAIL"},
        "ice body": {"HAIL"},
        "snow cloak": {"HAIL"},
    }
    return set(mapping.get(ability, set()))


def _weather_benefits_from_move(move_name: str, move: dict) -> set[str]:
    benefits: set[str] = set()
    category = str(move.get("Category") or "")
    move_type = str(move.get("Type") or "")
    if category in {"Physical", "Special"}:
        # Rain and sun directly boost their corresponding STAB/damaging types.
        if move_type == "Water":
            benefits.add("RAIN")
        if move_type == "Fire":
            benefits.add("SUN")
    if move_name in {"Thunder", "Hurricane"}:
        benefits.add("RAIN")
    if move_name in {"Solar Beam", "Solar Blade"}:
        benefits.add("SUN")
    if move_name == "Blizzard":
        benefits.add("HAIL")
    return benefits


def _recognize_capability_keys(
    pokemon: dict,
    move_names: list[str] | tuple[str, ...],
    move_lookup: dict[str, dict],
) -> set[str]:
    """Recognize strategy primitives from an arbitrary move-name collection."""
    capability_keys: set[str] = set()
    screen_names: set[str] = set()
    damaging_categories: set[str] = set()
    weather_benefits: set[str] = set()
    has_offensive_setup_physical = False
    has_offensive_setup_special = False

    ability = str(pokemon.get("Ability") or "").strip().casefold()
    weather_from_ability = _weather_setter_from_ability(ability)
    if weather_from_ability:
        capability_keys.add(f"WEATHER_SET_{weather_from_ability}")
    weather_benefits.update(_weather_benefits_from_ability(ability))

    for move_name in move_names:
        move = move_lookup.get(move_name, {})
        tags = _mechanics_tags(move)
        category = str(move.get("Category") or "")
        status_effect = str(move.get("StatusEffect") or "").casefold()

        # Existing Poison capability behavior.
        if move_name == "Toxic Spikes":
            capability_keys.add("STATUS_POISON_TEAM_SETUP")
        if move_name == "Baneful Bunker":
            capability_keys.add("STATUS_POISON_CONTACT")
        if status_effect == "poison" and category == "Status":
            capability_keys.add("STATUS_POISON_RELIABLE")
        if _poison_exploit_damage(move):
            capability_keys.add("POISON_EXPLOIT_DAMAGE")
        if _negative_target_stage_control(move):
            capability_keys.add("POISON_EXPLOIT_CONTROL")

        # Shared defensive/control capabilities.
        if "RecoveryMove" in tags:
            capability_keys.add("RELIABLE_RECOVERY")
        if "HPStealingMove" in tags:
            capability_keys.add("DAMAGE_RECOVERY")
        if "Protection" in tags:
            capability_keys.add("PROTECTION")
        if "StatReset" in tags:
            capability_keys.add("SETUP_DENIAL")
        if "Screen" in tags or move_name in {"Reflect", "Light Screen", "Aurora Veil"}:
            capability_keys.add("SCREEN")
            screen_names.add(move_name)
        if "DefenseSetup" in tags:
            capability_keys.add("DEFENSE_SETUP")

        # Offensive profile / setup primitives.
        if category in {"Physical", "Special"} and float(move.get("Power") or 0) > 0:
            damaging_categories.add(category)
        positive = _user_positive_stage_changes(move)
        if positive.get("atk", 0) > 0:
            capability_keys.add("PHYSICAL_SETUP")
            has_offensive_setup_physical = True
        if positive.get("spa", 0) > 0:
            capability_keys.add("SPECIAL_SETUP")
            has_offensive_setup_special = True
        # Preserve the legacy mechanics tag path even if the stage fields are absent.
        if "SpecialAttackSetup" in tags:
            capability_keys.add("SPECIAL_SETUP")
            has_offensive_setup_special = True
        if positive.get("spe", 0) > 0:
            capability_keys.add("SPEED_SETUP")
        if _target_negative_stage_changes(move):
            capability_keys.add("SETUP_FACILITATION")

        # Deliberate status moves count; incidental damaging-move proc chances do not.
        if category == "Status":
            if status_effect == "burn":
                capability_keys.add("STATUS_BURN_RELIABLE")
            elif status_effect in {"paralysis", "paralyze", "paralyzed"}:
                capability_keys.add("STATUS_PARALYSIS_RELIABLE")
            elif status_effect == "sleep":
                capability_keys.add("STATUS_SLEEP_RELIABLE")
            if move_name == "Yawn":
                capability_keys.add("STATUS_YAWN")
                capability_keys.add("STATUS_SLEEP_RELIABLE")
            if status_effect in {"burn", "paralysis", "paralyze", "paralyzed", "sleep", "poison"} or move_name == "Yawn":
                capability_keys.add("STATUS_ANY_RELIABLE")
        if _status_exploit_damage(move):
            capability_keys.add("STATUS_EXPLOIT_DAMAGE")
            if str(move.get("ActivationCondition") or "") == "TargetAnyStatus":
                capability_keys.add("STATUS_EXPLOIT_ANY_DAMAGE")

        # Weather setup and beneficiaries.
        weather = _weather_setter_from_move(move_name, move)
        if weather:
            capability_keys.add(f"WEATHER_SET_{weather}")
        weather_benefits.update(_weather_benefits_from_move(move_name, move))

        # Defensive attrition pressure.
        if move_name == "Body Press":
            capability_keys.add("BODY_PRESS")
        if move_name in {"Baneful Bunker", "Obstruct", "Spiky Shield", "King's Shield"}:
            capability_keys.add("CONTACT_PUNISHMENT")
        if move_name in {
            "Leech Seed", "Toxic", "Toxic Spikes", "Infestation", "Bind", "Wrap",
            "Fire Spin", "Whirlpool", "Sand Tomb", "Clamp",
        }:
            capability_keys.add("PASSIVE_CHIP")

    if {"Reflect", "Light Screen"}.issubset(screen_names) or "Aurora Veil" in screen_names:
        capability_keys.add("DUAL_SCREEN")
    if "SCREEN" in capability_keys:
        screen_moves = [move_lookup.get(name, {}) for name in screen_names]
        if ability == "prankster" or any(float(move.get("Priority") or 0) > 0 for move in screen_moves):
            capability_keys.add("PRIORITY_SCREEN")
        base_speed = _base_speed_value(pokemon)
        if base_speed is not None and base_speed >= 90:
            capability_keys.add("FAST_SCREEN")

    if "Physical" in damaging_categories:
        capability_keys.add("OFFENSIVE_PHYSICAL")
    if "Special" in damaging_categories:
        capability_keys.add("OFFENSIVE_SPECIAL")
    if {"Physical", "Special"}.issubset(damaging_categories):
        capability_keys.add("OFFENSIVE_MIXED")

    if has_offensive_setup_physical and has_offensive_setup_special:
        capability_keys.add("MIXED_SETUP")

    if ability == "speed boost":
        capability_keys.add("SPEED_BOOST")
        capability_keys.add("SPEED_SETUP")

    if ability in {"iron barbs", "rough skin"}:
        capability_keys.add("CONTACT_PUNISHMENT")
    if ability in {"liquid ooze", "aftermath"}:
        capability_keys.add("CONTACT_PUNISHMENT")

    for weather in weather_benefits:
        capability_keys.add(f"WEATHER_BENEFIT_{weather}")

    if ability == "corrosion":
        capability_keys.add("CORROSION")
    if ability == "regenerator":
        capability_keys.add("REGENERATOR_SUSTAIN")

    if ability == "merciless":
        capability_keys.add("MERCILESS")
        capability_keys.add("STATUS_EXPLOIT_DAMAGE")

    return capability_keys


def recognize_pokemon_capabilities(pokemon: dict, move_lookup: dict[str, dict]) -> StrategicCapabilityResult:
    """Recognize reusable strategy tools from this Pokémon's equipped moves."""
    capability_keys = _recognize_capability_keys(pokemon, _move_names(pokemon), move_lookup)
    ordered_keys = tuple(key for key in _CAPABILITY_ORDER if key in capability_keys)
    return StrategicCapabilityResult(
        pokemon_name=str(pokemon.get("Pokemon") or "Unknown Pokémon"),
        capability_keys=ordered_keys,
        capabilities=tuple(CAPABILITY_LABELS[key] for key in ordered_keys),
    )


def recognize_learnable_pokemon_capabilities(
    pokemon: dict,
    moves_data: list[dict],
    learnsets_data: dict,
) -> StrategicCapabilityResult:
    """Recognize strategy tools this exact Pokémon can learn through supported methods.

    This is recommendation-side potential, not the Pokémon's current moveset.
    Egg Moves and DLC-only acquisition methods are excluded by the learnset gate.
    Existing battle plans continue to use the player's saved equipped moves.
    """
    move_lookup = {
        move["Move"]: move
        for move in moves_data
        if isinstance(move, dict)
        and isinstance(move.get("Move"), str)
        and move.get("Move")
    }
    candidate_names = supported_strategy_move_names(
        pokemon,
        learnsets_data,
        moves_data,
    )
    capability_keys = _recognize_capability_keys(pokemon, candidate_names, move_lookup)
    ordered_keys = tuple(key for key in _CAPABILITY_ORDER if key in capability_keys)
    return StrategicCapabilityResult(
        pokemon_name=str(pokemon.get("Pokemon") or "Unknown Pokémon"),
        capability_keys=ordered_keys,
        capabilities=tuple(CAPABILITY_LABELS[key] for key in ordered_keys),
    )


def recognize_team_learnable_capabilities(
    team_data: list[dict],
    moves_data: list[dict],
    learnsets_data: dict,
) -> list[StrategicCapabilityResult]:
    """Return recommendation-side strategy potential for each saved team member."""
    return [
        recognize_learnable_pokemon_capabilities(
            pokemon, moves_data, learnsets_data
        )
        for pokemon in team_data
        if isinstance(pokemon, dict) and pokemon.get("Pokemon")
    ]


def recognize_team_capabilities(
    team_data: list[dict],
    moves_data: list[dict],
) -> list[StrategicCapabilityResult]:
    """Recognize equipped-move strategic tools across the saved party."""
    move_lookup = {
        move["Move"]: move
        for move in moves_data
        if isinstance(move, dict)
        and isinstance(move.get("Move"), str)
        and move.get("Move")
    }
    return [
        recognize_pokemon_capabilities(pokemon, move_lookup)
        for pokemon in team_data
        if isinstance(pokemon, dict) and pokemon.get("Pokemon")
    ]


_STRATEGY_ALIASES = {
    "strongest matchup": "strongest_matchup",
    "strongest_matchup": "strongest_matchup",
    "poison - offensive pressure": "poison_offensive_pressure",
    "poison – offensive pressure": "poison_offensive_pressure",
    "poison_offensive_pressure": "poison_offensive_pressure",
    "poison - attrition": "poison_attrition",
    "poison – attrition": "poison_attrition",
    "poison_attrition": "poison_attrition",
    "screen control": "screen_control",
    "screen_control": "screen_control",
    "setup offense": "setup_offense",
    "setup_offense": "setup_offense",
    "status control & punish": "status_control_punish",
    "status_control_punish": "status_control_punish",
    "weather control": "weather_control",
    "weather_control": "weather_control",
    "defensive attrition": "defensive_attrition",
    "defensive_attrition": "defensive_attrition",
}

_STRATEGY_LABELS = {
    "strongest_matchup": "Strongest Matchup",
    "poison_offensive_pressure": "Poison – Offensive Pressure",
    "poison_attrition": "Poison – Attrition",
    "screen_control": "Screen Control",
    "setup_offense": "Setup Offense",
    "status_control_punish": "Status Control & Punish",
    "weather_control": "Weather Control",
    "defensive_attrition": "Defensive Attrition",
}


def _canonical_strategy_key(strategy_key: str) -> str:
    raw = str(strategy_key or "").strip()
    return _STRATEGY_ALIASES.get(raw.casefold(), raw.casefold().replace(" ", "_"))


def _capability_provider_names(
    capability_results: list[StrategicCapabilityResult],
    accepted_keys: set[str],
) -> tuple[str, ...]:
    return tuple(
        result.pokemon_name
        for result in capability_results
        if accepted_keys.intersection(result.capability_keys)
    )


def _role_satisfied(
    capability_results: list[StrategicCapabilityResult],
    accepted_keys: set[str],
) -> bool:
    return bool(_capability_provider_names(capability_results, accepted_keys))


def _matched_weather_roles(
    capability_results: list[StrategicCapabilityResult],
) -> tuple[bool, tuple[str, ...], tuple[str, ...]]:
    """Return whether distinct teammates provide matched weather setup and payoff."""
    matched: list[str] = []
    contributing: list[str] = []
    for weather in ("RAIN", "SUN", "SAND", "HAIL"):
        setter = f"WEATHER_SET_{weather}"
        beneficiary = f"WEATHER_BENEFIT_{weather}"
        setters = [result for result in capability_results if setter in result.capability_keys]
        beneficiaries = [result for result in capability_results if beneficiary in result.capability_keys]
        if not any(a.pokemon_name != b.pokemon_name for a in setters for b in beneficiaries):
            continue
        matched.append(weather.title())
        for result in (*setters, *beneficiaries):
            if result.pokemon_name not in contributing:
                contributing.append(result.pokemon_name)
    return bool(matched), tuple(matched), tuple(contributing)


def _screen_offensive_beneficiaries(team_data: list[dict] | None, screeners: set[str]) -> tuple[str, ...]:
    """Identify offense-leaning saved teammates from their own comparable stats.

    Avoid inventing base stats or using move presence as a proxy for offensive fit.
    Compare stats within a Pokémon so mixed team levels do not bias the assessment.
    """
    def stat(mon: dict, *keys: str) -> float | None:
        for key in keys:
            value = mon.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
                return float(value)
        return None

    beneficiaries: list[str] = []
    for mon in team_data or []:
        if not isinstance(mon, dict):
            continue
        name = str(mon.get("Pokemon") or "").strip()
        if not name or name in screeners:
            continue
        attack = stat(mon, "ATK", "Atk", "Attack")
        spa = stat(mon, "SPA", "SpA", "SpecialAttack", "Special Attack")
        defense = stat(mon, "DEF", "Def", "Defense")
        spd = stat(mon, "SPD", "SpD", "SpecialDefense", "Special Defense")
        speed = stat(mon, "SPE", "Spe", "Speed")
        if (attack is None and spa is None) or defense is None or spd is None:
            continue
        offense = max(x for x in (attack, spa) if x is not None)
        bulk = (defense + spd) / 2
        # Emphasize hard hitters whose offenses materially exceed their defenses;
        # Speed modestly strengthens the profile but cannot qualify a weak attacker.
        if offense >= bulk * 1.20 and (speed is None or speed >= bulk * 0.75):
            beneficiaries.append(name)
    return tuple(beneficiaries)


def evaluate_strategy_viability(
    strategy_key: str,
    capability_results: list[StrategicCapabilityResult],
    *,
    team_data: list[dict] | None = None,
) -> StrategyViabilityResult:
    """Evaluate generic team readiness as Incomplete, Viable, or Strong.

    This function does not inspect a live opponent and never invents unequipped
    tactical actions. Its meaning depends on the supplied capability results:
    equipped results measure the current team; learnable results measure supported
    recommendation-side potential.
    """
    key = _canonical_strategy_key(strategy_key)
    label = _STRATEGY_LABELS.get(key, strategy_key)

    if key == "strongest_matchup":
        viability = "Strong"
        return StrategyViabilityResult(
            strategy_key=key,
            viability=viability,
            viability_rank=_VIABILITY_RANK[viability],
            summary="Strongest Matchup is always available because it does not require a strategy package.",
            required_roles=(),
            satisfied_required_roles=(),
            missing_required_roles=(),
            supporting_roles=(),
            contributing_pokemon=(),
            one_change_away=False,
        )

    required: list[tuple[str, set[str]]] = []
    supports: list[tuple[str, set[str]]] = []
    strong_bonus = False
    strong_support_threshold = 2
    special_contributors: tuple[str, ...] = ()

    if key == "poison_offensive_pressure":
        required = [
            ("reliable poison", {"STATUS_POISON_RELIABLE", "STATUS_POISON_TEAM_SETUP", "STATUS_POISON_CONTACT"}),
            ("poison payoff", {"POISON_EXPLOIT_DAMAGE", "MERCILESS"}),
        ]
        supports = [
            ("Corrosion access", {"CORROSION"}),
            ("setup or sustain", {"SPECIAL_SETUP", "PHYSICAL_SETUP", "RELIABLE_RECOVERY", "DAMAGE_RECOVERY", "REGENERATOR_SUSTAIN"}),
        ]
    elif key == "poison_attrition":
        required = [
            ("reliable poison", {"STATUS_POISON_RELIABLE", "STATUS_POISON_TEAM_SETUP", "STATUS_POISON_CONTACT"}),
            ("attrition anchor", {"RELIABLE_RECOVERY", "DAMAGE_RECOVERY", "REGENERATOR_SUSTAIN", "PROTECTION", "DEFENSE_SETUP", "SCREEN"}),
        ]
        supports = [
            ("poison control/payoff", {"POISON_EXPLOIT_CONTROL", "POISON_EXPLOIT_DAMAGE", "MERCILESS"}),
            ("setup denial", {"SETUP_DENIAL"}),
        ]
    elif key == "screen_control":
        # The setter is the lynchpin. Attack moves on that setter (or any other
        # teammate) do not, by themselves, make this a Strong screen team.
        screeners = [r for r in capability_results if "DUAL_SCREEN" in r.capability_keys]
        screen_names = {r.pokemon_name for r in screeners}
        beneficiaries = _screen_offensive_beneficiaries(team_data, screen_names)
        required = [("reliable screen setter", {"DUAL_SCREEN"})]
        supports = [
            ("priority screen delivery", {"PRIORITY_SCREEN"}),
            ("fast screen delivery", {"FAST_SCREEN"}),
        ]
        if not screeners:
            status = "Incomplete"
            detail = "no reliable dual-screen setter yet; seek Reflect + Light Screen."
        elif beneficiaries:
            status = "Strong"
            detail = ("reliable screen setup supports offense-oriented teammates: "
                      + ", ".join(beneficiaries) + ".")
        else:
            status = "Viable"
            detail = ("the setter can establish screens. For greater payoff, favor "
                      "fast, hard-hitting teammates with comparatively low bulk "
                      "(for example Salazzle or Gengar); individual stat evidence "
                      "is needed before rating this team Strong.")
        return StrategyViabilityResult(
            strategy_key=key,
            viability=status,
            viability_rank=_VIABILITY_RANK[status],
            summary=f"Screen Control is {status.lower()}: {detail}",
            required_roles=("reliable screen setter",),
            satisfied_required_roles=("reliable screen setter",) if screeners else (),
            missing_required_roles=() if screeners else ("reliable screen setter",),
            supporting_roles=tuple(name for name, keys in supports
                                   if _role_satisfied(capability_results, keys)),
            contributing_pokemon=tuple(dict.fromkeys([*screen_names, *beneficiaries])),
            one_change_away=False,
        )
    elif key == "setup_offense":
        required = [
            ("offensive setup", {"PHYSICAL_SETUP", "SPECIAL_SETUP", "MIXED_SETUP"}),
            ("setup access", {"SPEED_SETUP", "SPEED_BOOST", "SETUP_FACILITATION", "SCREEN", "RELIABLE_RECOVERY", "PROTECTION"}),
        ]
        supports = [
            ("Speed control", {"SPEED_SETUP", "SPEED_BOOST"}),
            ("facilitation", {"SETUP_FACILITATION", "SCREEN"}),
            ("sustain", {"RELIABLE_RECOVERY", "DAMAGE_RECOVERY", "REGENERATOR_SUSTAIN", "PROTECTION"}),
        ]
        strong_bonus = _role_satisfied(capability_results, {"SPEED_BOOST", "SPEED_SETUP"})
    elif key == "status_control_punish":
        required = [
            ("reliable status", {"STATUS_ANY_RELIABLE", "STATUS_BURN_RELIABLE", "STATUS_PARALYSIS_RELIABLE", "STATUS_SLEEP_RELIABLE", "STATUS_YAWN", "STATUS_POISON_RELIABLE"}),
            ("status payoff", {"STATUS_EXPLOIT_DAMAGE", "STATUS_EXPLOIT_ANY_DAMAGE", "MERCILESS"}),
        ]
        supports = [
            ("any-status damage payoff", {"STATUS_EXPLOIT_ANY_DAMAGE"}),
            ("setup denial", {"SETUP_DENIAL"}),
            ("sustain/protection", {"RELIABLE_RECOVERY", "DAMAGE_RECOVERY", "REGENERATOR_SUSTAIN", "PROTECTION"}),
        ]
        strong_bonus = _role_satisfied(capability_results, {"STATUS_EXPLOIT_ANY_DAMAGE"})
    elif key == "weather_control":
        matched, weather_names, special_contributors = _matched_weather_roles(capability_results)
        required = [
            ("weather setter", {"WEATHER_SET_RAIN", "WEATHER_SET_SUN", "WEATHER_SET_SAND", "WEATHER_SET_HAIL"}),
            ("matched weather beneficiary", set()),
        ]
        supports = [
            ("multiple weather benefits", {"WEATHER_BENEFIT_RAIN", "WEATHER_BENEFIT_SUN", "WEATHER_BENEFIT_SAND", "WEATHER_BENEFIT_HAIL"}),
        ]
        # The second required role is intentionally handled as a matched pair rather
        # than allowing (for example) Drizzle + Chlorophyll to count as coherent.
        required_satisfied = {
            "weather setter": _role_satisfied(capability_results, required[0][1]),
            "matched weather beneficiary": matched,
        }
        satisfied = tuple(name for name, ok in required_satisfied.items() if ok)
        missing = tuple(name for name, ok in required_satisfied.items() if not ok)
        support_satisfied = tuple(
            name for name, keys in supports if _role_satisfied(capability_results, keys)
        )
        contributors = special_contributors or tuple(
            result.pokemon_name
            for result in capability_results
            if any(k.startswith("WEATHER_") for k in result.capability_keys)
        )
        if missing:
            viability = "Incomplete"
        else:
            weather_benefit_count = sum(
                1
                for result in capability_results
                if any(k.startswith("WEATHER_BENEFIT_") for k in result.capability_keys)
            )
            viability = "Strong" if weather_benefit_count >= 2 or len(weather_names) > 1 else "Viable"
        return StrategyViabilityResult(
            strategy_key=key,
            viability=viability,
            viability_rank=_VIABILITY_RANK[viability],
            summary=(
                f"{label} is {viability.lower()}: "
                + (f"matched weather package: {', '.join(weather_names)}." if weather_names else "a setter and beneficiary are not yet matched to the same weather.")
            ),
            required_roles=tuple(name for name, _ in required),
            satisfied_required_roles=satisfied,
            missing_required_roles=missing,
            supporting_roles=support_satisfied,
            contributing_pokemon=contributors,
            one_change_away=False,
        )
    elif key == "defensive_attrition":
        required = [
            ("survival loop", {"RELIABLE_RECOVERY", "DAMAGE_RECOVERY", "REGENERATOR_SUSTAIN", "PROTECTION", "DEFENSE_SETUP"}),
            ("attrition pressure", {"BODY_PRESS", "CONTACT_PUNISHMENT", "PASSIVE_CHIP"}),
        ]
        supports = [
            ("Defense-to-damage", {"BODY_PRESS"}),
            ("contact punishment", {"CONTACT_PUNISHMENT"}),
            ("passive chip", {"PASSIVE_CHIP"}),
            ("setup denial", {"SETUP_DENIAL"}),
        ]
        strong_bonus = (
            _role_satisfied(capability_results, {"DEFENSE_SETUP"})
            and _role_satisfied(capability_results, {"BODY_PRESS"})
        )
    else:
        raise ValueError(f"Unsupported strategy for viability evaluation: {strategy_key}")

    role_status = [
        (role_name, _role_satisfied(capability_results, accepted_keys))
        for role_name, accepted_keys in required
    ]
    satisfied = tuple(role_name for role_name, ok in role_status if ok)
    missing = tuple(role_name for role_name, ok in role_status if not ok)
    support_satisfied = tuple(
        role_name
        for role_name, accepted_keys in supports
        if _role_satisfied(capability_results, accepted_keys)
    )

    contributor_keys = set().union(*(keys for _, keys in required), *(keys for _, keys in supports))
    contributors = tuple(
        result.pokemon_name
        for result in capability_results
        if contributor_keys.intersection(result.capability_keys)
    )

    if missing:
        viability = "Incomplete"
    elif strong_bonus or len(support_satisfied) >= strong_support_threshold:
        viability = "Strong"
    else:
        viability = "Viable"

    if viability == "Incomplete":
        detail = "missing " + ", ".join(missing) + "."
    elif viability == "Strong":
        detail = "all required roles are covered with meaningful supporting depth."
    else:
        detail = "all required roles are covered, but the package has limited supporting depth."

    return StrategyViabilityResult(
        strategy_key=key,
        viability=viability,
        viability_rank=_VIABILITY_RANK[viability],
        summary=f"{label} is {viability.lower()}: {detail}",
        required_roles=tuple(role_name for role_name, _ in required),
        satisfied_required_roles=satisfied,
        missing_required_roles=missing,
        supporting_roles=support_satisfied,
        contributing_pokemon=contributors,
        one_change_away=False,
    )



def _replace_team_capability(
    capability_results: list[StrategicCapabilityResult],
    team_index: int,
    replacement: StrategicCapabilityResult,
) -> list[StrategicCapabilityResult]:
    """Return a copy with one exact party slot's capability result replaced."""
    updated = list(capability_results)
    if 0 <= team_index < len(updated):
        updated[team_index] = replacement
    else:
        updated.append(replacement)
    return updated


def _recommendation_improvement(
    before: StrategyViabilityResult,
    after: StrategyViabilityResult,
) -> tuple[int, int, int]:
    """Return viability gain, required-role gain, and supporting-role gain."""
    viability_gain = after.viability_rank - before.viability_rank
    required_gain = len(before.missing_required_roles) - len(after.missing_required_roles)
    support_gain = len(set(after.supporting_roles) - set(before.supporting_roles))
    return viability_gain, required_gain, support_gain


def _recommendation_score(
    before: StrategyViabilityResult,
    after: StrategyViabilityResult,
    capability_keys_added: set[str],
) -> float:
    """Score one simulated change, heavily prioritizing actual viability improvement."""
    viability_gain, required_gain, support_gain = _recommendation_improvement(before, after)
    crosses_viable = before.viability == "Incomplete" and after.viability_rank >= _VIABILITY_RANK["Viable"]
    return (
        (1000.0 if crosses_viable else 0.0)
        + max(viability_gain, 0) * 200.0
        + max(required_gain, 0) * 50.0
        + max(support_gain, 0) * 10.0
        + min(len(capability_keys_added), 20) * 0.25
    )


def _recommendation_candidate(
    *,
    strategy_key: str,
    recommendation_kind: str,
    pokemon_name: str,
    move_name: str | None,
    replace_move_name: str | None,
    before: StrategyViabilityResult,
    after: StrategyViabilityResult,
    capability_keys_added: set[str],
) -> StrategyRecommendationCandidate | None:
    """Build a candidate only when the simulated change measurably helps."""
    viability_gain, required_gain, support_gain = _recommendation_improvement(before, after)
    if viability_gain <= 0 and required_gain <= 0 and support_gain <= 0:
        return None

    roles_filled = tuple(
        role for role in before.missing_required_roles
        if role in after.satisfied_required_roles
    )
    support_added = tuple(
        role for role in after.supporting_roles
        if role not in before.supporting_roles
    )
    ordered_added = tuple(
        key for key in _CAPABILITY_ORDER
        if key in capability_keys_added
    )
    score = _recommendation_score(before, after, capability_keys_added)

    if recommendation_kind == "pokemon":
        action = f"Add {pokemon_name}"
    elif replace_move_name:
        action = f"Teach {pokemon_name} {move_name} over {replace_move_name}"
    else:
        action = f"Teach {pokemon_name} {move_name}"

    gains: list[str] = []
    if roles_filled:
        if recommendation_kind == "pokemon":
            gains.append("team gains " + ", ".join(roles_filled))
        else:
            gains.append("team gains " + ", ".join(roles_filled))
    if support_added:
        gains.append("adds " + ", ".join(support_added))
    gain_text = "; ".join(gains) if gains else "improves the strategy package"
    summary = f"{action}: {gain_text}; resulting readiness is {after.viability}."

    return StrategyRecommendationCandidate(
        strategy_key=_canonical_strategy_key(strategy_key),
        recommendation_kind=recommendation_kind,
        pokemon_name=pokemon_name,
        move_name=move_name,
        replace_move_name=replace_move_name,
        score=score,
        resulting_viability=after.viability,
        resulting_viability_rank=after.viability_rank,
        roles_filled=roles_filled,
        supporting_roles_added=support_added,
        capability_keys_added=ordered_added,
        summary=summary,
    )


def _potential_ability_options(pokemon: dict) -> tuple[tuple[str, str | None], ...]:
    """Enumerate actual individual Ability builds; unresolved species are conservative."""
    pokemon_id = resolve_pokemon_id(
        pokemon.get("Pokemon"), gender=pokemon.get("Gender"),
        nature=pokemon.get("Nature"), form=pokemon.get("Form"),
    )
    if not pokemon_id:
        return ((str(pokemon.get("Ability") or ""), None),)
    try:
        names = eligible_abilities(pokemon_id)
    except (OSError, ValueError, KeyError):
        names = ()
    if not names:
        return ((str(pokemon.get("Ability") or ""), None),)
    return tuple((name, ability_eligibility(pokemon_id, name)) for name in names)


def _ability_strategy_bonus(strategy_key: str, ability: str, capabilities: set[str]) -> float:
    """Reward abilities only if they assist a strategy-specific role."""
    key = _canonical_strategy_key(strategy_key)
    a = ability.casefold()
    bonus = {
        "poison_offensive_pressure": {"merciless": 55, "corrosion": 45},
        "poison_attrition": {"regenerator": 65, "corrosion": 30, "merciless": 15},
        "screen_control": {"prankster": 15},
        "setup_offense": {"speed boost": 55, "simple": 40, "contrary": 25, "moxie": 25},
        "status_control_punish": {"prankster": 25, "merciless": 20},
        "weather_control": {"drizzle": 65, "drought": 65, "sand stream": 65,
                            "snow warning": 65, "swift swim": 30, "chlorophyll": 30,
                            "sand rush": 30, "slush rush": 30, "solar power": 25},
        "defensive_attrition": {"regenerator": 60, "iron barbs": 50,
                                "rough skin": 50, "stamina": 35, "magic guard": 25,
                                "fur coat": 35, "fluffy": 30},
    }.get(key, {})
    value = float(bonus.get(a, 0))
    if a == "prankster" and not ({"SCREEN", "STATUS_ANY_RELIABLE", "STATUS_POISON_RELIABLE",
                                 "SETUP_FACILITATION"} & capabilities or
                                any(c.startswith("WEATHER_SET_") for c in capabilities)):
        return 0.0
    if a in {"swift swim", "chlorophyll", "sand rush", "slush rush", "solar power"} and not any(c.startswith("WEATHER_BENEFIT_") for c in capabilities):
        return 0.0
    return value


_NATURAL_SCREEN_METHODS = {"level", "evolution", "relearner", "reminder"}


def _screen_acquisition_tier(pokemon: dict, learnsets_data: dict) -> tuple[int, bool]:
    """Screen performance first: Prankster dual screens beat natural-only access."""
    natural = 0
    supported = 0
    for name in ("Reflect", "Light Screen"):
        methods = supported_strategy_move_methods(pokemon, name, learnsets_data)
        if methods:
            supported += 1
            if any(str(m.get("method") or "").casefold() in _NATURAL_SCREEN_METHODS for m in methods):
                natural += 1
    prankster = str(pokemon.get("Ability") or "").casefold() == "prankster"
    if supported == 2 and prankster:
        return (8 if natural == 2 else 7), prankster
    if supported == 2:
        return (6 if natural == 2 else 5 if natural == 1 else 4), prankster
    if supported == 1:
        return (3 if prankster else 2 if natural else 1), prankster
    return 0, prankster


def _prankster_status_bonus(strategy_key: str, pokemon: dict, learnsets_data: dict, moves_data: list[dict]) -> float:
    """Small delivery bonus only for a relevant learnable status move."""
    if str(pokemon.get("Ability") or "").casefold() != "prankster":
        return 0.0
    key = _canonical_strategy_key(strategy_key)
    categories = {
        "screen_control": {"Reflect", "Light Screen"},
        "weather_control": {"Rain Dance", "Sunny Day", "Sandstorm", "Hail"},
        "poison_offensive_pressure": {"Toxic", "Poison Gas"},
        "poison_attrition": {"Toxic", "Poison Gas"},
    }
    names = set(supported_strategy_move_names(pokemon, learnsets_data, moves_data))
    if key in categories:
        relevant = names & categories[key]
    elif key == "status_control_punish":
        lookup = {m.get("Move"): m for m in moves_data if isinstance(m, dict)}
        relevant = {name for name in names if name in lookup and
                    str(lookup[name].get("Category") or "") == "Status" and
                    (str(lookup[name].get("StatusEffect") or "").casefold() in
                     {"burn", "paralysis", "paralyze", "sleep", "poison"} or name == "Yawn")}
    elif key in {"setup_offense", "defensive_attrition"}:
        lookup = {m.get("Move"): m for m in moves_data if isinstance(m, dict)}
        relevant = {name for name in names if name in lookup and
                    str(lookup[name].get("Category") or "") == "Status" and
                    (name in {"Reflect", "Light Screen", "Taunt", "Thunder Wave", "Will-O-Wisp", "Toxic"} or
                     _target_negative_stage_changes(lookup[name]))}
    else:
        relevant = set()
    return 15.0 if relevant else 0.0


def _recommendation_sort_key(candidate: StrategyRecommendationCandidate) -> tuple:
    # Python's sort is stable, so exact ties preserve caller/data order instead of
    # introducing an arbitrary alphabetical preference.
    return (
        candidate.resulting_viability_rank,
        candidate.score,
        len(candidate.roles_filled),
        len(candidate.supporting_roles_added),
    )




# Recommendation-side capability scoring. No move-combination search.
def _weighted_role_quality(strategy_key: str, pokemon: dict, names: set[str], caps: set[str], learnsets_data: dict) -> float:
    key = _canonical_strategy_key(strategy_key)
    ability = str(pokemon.get("Ability") or "").casefold()
    has = names.__contains__
    if key == "screen_control":
        tier, _ = _screen_acquisition_tier(pokemon, learnsets_data)
        # Delivery tier is a real priority, not a tiny bonus after viability.
        return tier * 130 + (110 if {"Reflect", "Light Screen"} <= names else 0)
    if key == "poison_attrition":
        poison = 100 if (names & {"Toxic", "Toxic Spikes", "Poison Gas", "Baneful Bunker"}) else 0
        sustain = 115 if has("Recover") else (55 if has("Rest") else 0)
        defense = 90 if has("Baneful Bunker") else (35 if names & {"Protect", "Spiky Shield", "Obstruct"} else 0)
        return poison + sustain + defense + (95 if ability == "regenerator" else 0) + (30 if has("Toxic Spikes") else 0)
    if key == "poison_offensive_pressure":
        return (115 if names & {"Toxic", "Toxic Spikes", "Poison Gas"} else 0) + (125 if names & {"Venoshock", "Hex"} else 0) + (80 if ability == "merciless" else 0) + (65 if ability == "corrosion" else 0)
    if key == "status_control_punish":
        return (100 if "STATUS_ANY_RELIABLE" in caps else 0) + (125 if names & {"Hex", "Venoshock"} else 0) + (65 if ability == "prankster" and "STATUS_ANY_RELIABLE" in caps else 0)
    if key == "weather_control":
        automatic = {"drizzle", "drought", "sand stream", "snow warning"}
        return (200 if ability in automatic else 0) + (90 if any(c.startswith("WEATHER_SET_") for c in caps) else 0) + (80 if any(c.startswith("WEATHER_BENEFIT_") for c in caps) else 0)
    if key == "setup_offense":
        return (125 if caps & {"PHYSICAL_SETUP", "SPECIAL_SETUP"} else 0) + (80 if caps & {"SPEED_SETUP", "SPEED_BOOST"} else 0) + (65 if caps & {"SETUP_FACILITATION", "SCREEN"} else 0)
    if key == "defensive_attrition":
        return (110 if names & {"Recover", "Roost", "Slack Off", "Shore Up", "Strength Sap"} else 0) + (110 if {"Iron Defense", "Body Press"} <= names else 0) + (85 if caps & {"CONTACT_PUNISHMENT", "PASSIVE_CHIP"} else 0) + (85 if ability == "regenerator" else 0)
    return 0.0


def recommend_strategy_pokemon_additions(
    strategy_key: str,
    current_capability_results: list[StrategicCapabilityResult],
    candidate_pokemon_data: list[dict],
    moves_data: list[dict],
    learnsets_data: dict,
    *,
    limit: int | None = 5,
) -> list[StrategyRecommendationCandidate]:
    """Rank final-form potential directly, without inventing a full moveset."""
    before = evaluate_strategy_viability(strategy_key, current_capability_results)
    if before.viability == "Strong":
        return []
    lookup = {m["Move"]: m for m in moves_data if isinstance(m, dict) and isinstance(m.get("Move"), str)}
    out = []
    for pokemon in candidate_pokemon_data:
        if not isinstance(pokemon, dict) or not pokemon.get("Pokemon"):
            continue
        names = set(supported_strategy_move_names(pokemon, learnsets_data, moves_data))
        best = None
        for ability, eligibility in _potential_ability_options(pokemon):
            build = dict(pokemon, Ability=ability)
            caps = _recognize_capability_keys(build, tuple(names), lookup)
            display_name = str(build["Pokemon"])
            if build.get("_strategy_gender_variant") and build.get("Gender") in {"Male", "Female"}:
                display_name = f'{display_name} ({build["Gender"]})'
            result = StrategicCapabilityResult(display_name, tuple(k for k in _CAPABILITY_ORDER if k in caps), tuple(CAPABILITY_LABELS[k] for k in _CAPABILITY_ORDER if k in caps))
            after = evaluate_strategy_viability(strategy_key, [*current_capability_results, result])
            rec = _recommendation_candidate(strategy_key=strategy_key, recommendation_kind="pokemon", pokemon_name=result.pokemon_name, move_name=None, replace_move_name=None, before=before, after=after, capability_keys_added=caps)
            if rec is None:
                continue
            quality = _weighted_role_quality(strategy_key, build, names, caps, learnsets_data)
            # Strategic role fit dominates viability/support flag counts.
            score = quality + max(0, len(before.missing_required_roles) - len(after.missing_required_roles)) * 20 + max(0, after.viability_rank - before.viability_rank) * 15
            score += (0 if _canonical_strategy_key(strategy_key) == "screen_control" else _ability_strategy_bonus(strategy_key, ability, caps) * 0.35)
            if _canonical_strategy_key(strategy_key) != "screen_control":
                score += _prankster_status_bonus(strategy_key, build, learnsets_data, moves_data)
            if pokemon.get("_available_now") is True:
                score += 0.5
            label = (f" Recommended Ability: {ability}" + (" (Hidden Ability; acquisition must be verified)" if eligibility == "hidden" else " (normal Ability)" if eligibility == "normal" else " (saved Ability)") + ".") if ability else ""
            rec = replace(rec, score=score, summary=rec.summary + label)
            if best is None or rec.score > best.score:
                best = rec
        if best:
            try:
                badge = int(pokemon.get("required_badge"))
            except (TypeError, ValueError):
                badge = None
            availability = ("Available at your current badge count." if pokemon.get("_available_now") is True else f"Available after {badge} badge(s); you can plan it now." if badge is not None else "Availability depends on Journey progression.")
            out.append(replace(best, summary=best.summary + " " + availability))
    out.sort(key=lambda c: c.score, reverse=True)
    return out if limit is None else out[:max(0, limit)]


_STRATEGY_MOVE_PURPOSES = {
    "screen_control": (("Reflect", "Core — protects the team from physical attacks"), ("Light Screen", "Core — protects the team from special attacks")),
    "poison_attrition": (("Toxic Spikes", "Core option — poisons incoming grounded opponents"), ("Toxic", "Core option — poisons the current target"), ("Baneful Bunker", "Support — protects while punishing contact"), ("Recover", "Support — sustains the attrition loop")),
    "poison_offensive_pressure": (("Toxic Spikes", "Core option — poisons switch-ins"), ("Toxic", "Core option — poisons the current opponent"), ("Venoshock", "Payoff — doubles power against poisoned targets"), ("Hex", "Payoff — doubles power against statused targets")),
    "status_control_punish": (("Will-O-Wisp", "Core option — reliable burn setup"), ("Thunder Wave", "Core option — reliable paralysis"), ("Yawn", "Core option — forces sleep or a switch"), ("Hex", "Payoff — doubles power against statused targets")),
    "setup_offense": (("Swords Dance", "Core option — raises physical Attack"), ("Nasty Plot", "Core option — raises Special Attack"), ("Calm Mind", "Core option — boosts special offense and defense"), ("Agility", "Support — increases Speed")),
    "weather_control": (("Rain Dance", "Core option — sets rain"), ("Sunny Day", "Core option — sets sun"), ("Sandstorm", "Core option — sets sand"), ("Hail", "Core option — sets hail")),
    "defensive_attrition": (("Iron Defense", "Support — increases Defense"), ("Body Press", "Payoff — converts Defense into damage"), ("Leech Seed", "Support — persistent chip and healing"), ("Recover", "Support — restores HP"), ("Protect", "Support — buys a safe turn")),
}


def strategy_move_guidance(strategy_key: str, pokemon: dict, moves_data: list[dict], learnsets_data: dict, *, limit: int = 4) -> tuple[tuple[str, str, str], ...]:
    """Offer only role-relevant moves, with purpose and supported acquisition."""
    if limit <= 0:
        return ()
    names = set(supported_strategy_move_names(pokemon, learnsets_data, moves_data))
    key = _canonical_strategy_key(strategy_key)
    output = []
    for name, purpose in _STRATEGY_MOVE_PURPOSES.get(key, ()):
        if name not in names:
            continue
        methods = supported_strategy_move_methods(pokemon, name, learnsets_data)
        labels = []
        for method in methods:
            how = str(method.get("method") or "").casefold()
            item = method.get("item")
            label = str(item) if item else "Move Reminder" if how in {"relearner", "reminder", "evolution"} else f"Level {method.get('level')}" if how == "level" and method.get("level") is not None else how.title()
            if label not in labels:
                labels.append(label)
        output.append((name, purpose, " / ".join(labels) or "Supported method"))
        if len(output) >= min(limit, 4):
            break
    # Dual-screen setters only need two moves; never pad with unrelated attacks.
    return tuple(output)


def recommend_strategy_moves_for_added_pokemon(
    strategy_key: str,
    current_capability_results: list[StrategicCapabilityResult],
    pokemon: dict,
    moves_data: list[dict],
    learnsets_data: dict,
    *,
    limit: int = 4,
) -> tuple[str, ...]:
    """Compatibility helper for planning: moves with explicit strategic purposes only."""
    del current_capability_results
    return tuple(name for name, _, _ in strategy_move_guidance(strategy_key, pokemon, moves_data, learnsets_data, limit=limit))


def _move_change_slots(pokemon: dict) -> list[int]:
    """Return legal single-change destinations, preferring an empty slot when present."""
    empty = [
        slot for slot in range(1, 5)
        if not isinstance(pokemon.get(f"Move{slot}"), str) or not str(pokemon.get(f"Move{slot}") or "").strip()
    ]
    return empty[:1] if empty else [1, 2, 3, 4]


def recommend_strategy_move_changes(
    strategy_key: str,
    team_data: list[dict],
    moves_data: list[dict],
    learnsets_data: dict,
    *,
    limit: int | None = 10,
) -> list[StrategyRecommendationCandidate]:
    """Rank legal one-move changes by their simulated strategy improvement.

    Each recommendation is a true one-change simulation. If a Pokémon already has
    four moves, every replacement slot is tested independently so the evaluator can
    reject a change that gains one role by destroying another.
    """
    move_lookup = {
        move["Move"]: move
        for move in moves_data
        if isinstance(move, dict) and isinstance(move.get("Move"), str) and move.get("Move")
    }
    current_results = recognize_team_capabilities(team_data, moves_data)
    before = evaluate_strategy_viability(strategy_key, current_results)
    if before.viability == "Strong":
        return []

    candidates: list[StrategyRecommendationCandidate] = []
    seen: set[tuple[str, str, str | None, str]] = set()

    valid_team = [
        pokemon for pokemon in team_data
        if isinstance(pokemon, dict) and pokemon.get("Pokemon")
    ]
    for team_index, pokemon in enumerate(valid_team):
        pokemon_name = str(pokemon.get("Pokemon"))
        current_moves = set(_move_names(pokemon))
        current_result = recognize_pokemon_capabilities(pokemon, move_lookup)
        learnable_names = supported_strategy_move_names(pokemon, learnsets_data, moves_data)

        for move_name in learnable_names:
            if move_name in current_moves or move_name not in move_lookup:
                continue
            for slot in _move_change_slots(pokemon):
                hypothetical = dict(pokemon)
                old_move = hypothetical.get(f"Move{slot}")
                replace_move_name = str(old_move).strip() if isinstance(old_move, str) and old_move.strip() else None
                hypothetical[f"Move{slot}"] = move_name
                new_result = recognize_pokemon_capabilities(hypothetical, move_lookup)
                after_results = _replace_team_capability(current_results, team_index, new_result)
                after = evaluate_strategy_viability(strategy_key, after_results)
                capability_keys_added = set(new_result.capability_keys) - set(current_result.capability_keys)
                recommendation = _recommendation_candidate(
                    strategy_key=strategy_key,
                    recommendation_kind="move",
                    pokemon_name=pokemon_name,
                    move_name=move_name,
                    replace_move_name=replace_move_name,
                    before=before,
                    after=after,
                    capability_keys_added=capability_keys_added,
                )
                if recommendation is None:
                    continue
                dedupe = (
                    recommendation.pokemon_name,
                    recommendation.move_name or "",
                    recommendation.replace_move_name,
                    recommendation.resulting_viability,
                )
                if dedupe in seen:
                    continue
                seen.add(dedupe)
                candidates.append(recommendation)

    candidates.sort(key=_recommendation_sort_key, reverse=True)
    return candidates if limit is None else candidates[:max(limit, 0)]



def evaluate_strategy_recommendations(
    strategy_key: str,
    team_data: list[dict],
    candidate_pokemon_data: list[dict],
    moves_data: list[dict],
    learnsets_data: dict,
    *,
    pokemon_limit: int | None = 5,
    move_limit: int | None = 10,
) -> StrategyRecommendationResult:
    """Evaluate readiness and rank supported one-change paths toward viability.

    `one_change_away` is True only when the current equipped team is Incomplete and
    at least one *single* supported Pokémon addition or *single* supported move change
    reaches Viable or Strong. This is the gate intended for future near-readiness UI.
    """
    current_results = recognize_team_capabilities(team_data, moves_data)
    current = evaluate_strategy_viability(strategy_key, current_results, team_data=team_data)

    team_size = sum(
        1 for pokemon in team_data
        if isinstance(pokemon, dict) and pokemon.get("Pokemon")
    )
    pokemon_additions = recommend_strategy_pokemon_additions(
        strategy_key,
        current_results,
        candidate_pokemon_data if team_size < 6 else [],
        moves_data,
        learnsets_data,
        limit=None,
    )
    move_changes = recommend_strategy_move_changes(
        strategy_key,
        team_data,
        moves_data,
        learnsets_data,
        limit=None,
    )

    reaches_viable = any(
        candidate.resulting_viability_rank >= _VIABILITY_RANK["Viable"]
        for candidate in (*pokemon_additions, *move_changes)
    )
    one_change_away = current.viability == "Incomplete" and reaches_viable
    viability = replace(current, one_change_away=one_change_away)

    if pokemon_limit is not None:
        pokemon_additions = pokemon_additions[:max(pokemon_limit, 0)]
    if move_limit is not None:
        move_changes = move_changes[:max(move_limit, 0)]

    return StrategyRecommendationResult(
        strategy_key=_canonical_strategy_key(strategy_key),
        viability=viability,
        pokemon_additions=tuple(pokemon_additions),
        move_changes=tuple(move_changes),
        one_change_away=one_change_away,
    )

def _opponent_has_contact_move(opponent: dict, move_lookup: dict[str, dict]) -> bool:
    for slot in range(1, 5):
        move_name = opponent.get(f"Move{slot}")
        if not isinstance(move_name, str) or not move_name:
            continue
        if bool(move_lookup.get(move_name, {}).get("MakesContact")):
            return True
    return False


def _opponent_has_hazard_removal(opponent: dict, move_lookup: dict[str, dict]) -> bool:
    for move_name in _move_names(opponent):
        if "HazardRemoval" in _mechanics_tags(move_lookup.get(move_name, {})):
            return True
    return False


def _note_texts(matchup_result: dict) -> set[str]:
    texts: set[str] = set()
    for note in matchup_result.get("Battle Notes", []):
        if isinstance(note, dict) and isinstance(note.get("text"), str):
            texts.add(note["text"])
    return texts


def _pokemon_types(pokemon: dict) -> set[str]:
    return {
        value
        for value in (str(pokemon.get("Type1") or ""), str(pokemon.get("Type2") or ""))
        if value
    }


def _is_grounded(pokemon: dict) -> bool:
    if "Flying" in _pokemon_types(pokemon):
        return False
    if str(pokemon.get("Ability") or "").strip().casefold() == "levitate":
        return False
    if str(pokemon.get("Held Item") or "").strip().casefold() == "air balloon":
        return False
    return True


def _poison_block_reason(opponent: dict, has_corrosion: bool) -> str | None:
    ability = str(opponent.get("Ability") or "").strip().casefold()
    if ability in _POISON_IMMUNE_ABILITIES:
        return f"{opponent.get('Ability')} prevents poison."
    if _pokemon_types(opponent).intersection({"Poison", "Steel"}) and not has_corrosion:
        return "The target's typing blocks poison from this Pokémon."
    return None


def _toxic_spikes_can_poison(opponent: dict) -> bool:
    if not _is_grounded(opponent):
        return False
    if _pokemon_types(opponent).intersection({"Poison", "Steel"}):
        return False
    ability = str(opponent.get("Ability") or "").strip().casefold()
    return ability not in _POISON_IMMUNE_ABILITIES


def _toxic_spikes_clears(opponent: dict) -> bool:
    return _is_grounded(opponent) and "Poison" in _pokemon_types(opponent)


def _strategic_depth(keys: set[str], strategy_branch: str = "poison_attrition") -> float:
    if strategy_branch == "poison_offensive_pressure":
        weights = {
            "POISON_EXPLOIT_DAMAGE": 4.0, "MERCILESS": 3.5, "SPECIAL_SETUP": 1.5,
            "DAMAGE_RECOVERY": 1.0, "RELIABLE_RECOVERY": 0.75, "SETUP_DENIAL": 0.75,
            "PROTECTION": 0.5, "POISON_EXPLOIT_CONTROL": 0.5,
        }
    else:
        weights = {
            "RELIABLE_RECOVERY": 4.0, "DAMAGE_RECOVERY": 3.0, "PROTECTION": 3.0,
            "SCREEN": 2.5, "DEFENSE_SETUP": 2.5, "POISON_EXPLOIT_CONTROL": 2.0,
            "SETUP_DENIAL": 1.5, "MERCILESS": 0.75, "POISON_EXPLOIT_DAMAGE": 0.5,
        }
    return sum(weights.get(key, 0.0) for key in keys)


def _effective_strategy_keys(keys: set[str], opponent: dict) -> set[str]:
    """Remove strategy tools that the current opponent's typing makes unusable."""
    effective_keys = set(keys)
    if "Steel" in _pokemon_types(opponent):
        effective_keys.discard("POISON_EXPLOIT_DAMAGE")
    return effective_keys


def _safe_super_effective_direct_option(matchup_results: list[dict]) -> dict | None:
    """Return the strongest safe super-effective direct option, if one exists."""
    candidates: list[dict] = []
    for result in matchup_results:
        if not isinstance(result, dict):
            continue
        multiplier = float(result.get("Best Move Type Multiplier") or 0.0)
        ratio = float(result.get("Ratio") or 0.0)
        notes = _note_texts(result)
        if multiplier <= 1:
            continue
        if ratio < 1:
            continue
        if "Likely Incoming OHKO" in notes or "Possible Incoming OHKO" in notes:
            continue
        candidates.append(result)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda result: (
            float(result.get("Ratio") or 0.0),
            float(result.get("Best MoveScore") or 0.0),
        ),
    )


def _can_damage_steel_target(matchup: dict) -> bool:
    """Return whether this Pokémon has a modeled non-Poison damaging option."""
    best_move = str(matchup.get("Best Move") or "")
    best_move_type = str(matchup.get("Best Move Type") or "")
    best_score = float(matchup.get("Best MoveScore") or 0.0)
    return bool(best_move and best_score > 0 and best_move_type != "Poison")


def _safety_score(matchup: dict, keys: set[str]) -> float:
    multiplier = float(matchup.get("Incoming Type Multiplier") or 0.0)
    incoming_score = float(matchup.get("Incoming Worst Score") or 0.0)
    if incoming_score == 0:
        score = 5.0
    elif multiplier == 0:
        score = 4.0
    elif multiplier <= 0.5:
        score = 3.0
    elif multiplier <= 1:
        score = 1.0
    elif multiplier <= 2:
        score = -1.0
    else:
        score = -3.0
    if keys.intersection({"RELIABLE_RECOVERY", "DAMAGE_RECOVERY"}):
        score += 2.0
    if "PROTECTION" in keys:
        score += 1.0
    if "POISON_EXPLOIT_CONTROL" in keys:
        score += 0.75
    if "SETUP_DENIAL" in keys:
        score += 0.5
    return score


def _opener_allows_response(opener_move: dict, response_move: dict) -> bool:
    """Return whether an opponent move can activate against the recommended opener."""
    condition = str(response_move.get("ActivationCondition") or "Always")
    opener_category = str(opener_move.get("Category") or "")
    opener_power = float(opener_move.get("Power") or 0)
    opener_is_damaging = opener_category in {"Physical", "Special"} and opener_power > 0
    if condition == "RequiresTargetDamagingMove":
        return opener_is_damaging
    if condition == "RequiresTargetPhysicalMove":
        return opener_category == "Physical"
    if condition == "RequiresTargetSpecialMove":
        return opener_category == "Special"
    if condition == "RequiresTargetContactMove":
        return bool(opener_move.get("MakesContact"))
    # Conditions such as first-turn requirements are battle-state dependent,
    # so keep them available rather than pretending they cannot occur.
    return True


def _safety_from_values(incoming_score: float, incoming_multiplier: float, keys: set[str]) -> float:
    if incoming_score == 0:
        score = 5.0
    elif incoming_multiplier == 0:
        score = 4.0
    elif incoming_multiplier <= 0.5:
        score = 3.0
    elif incoming_multiplier <= 1:
        score = 1.0
    elif incoming_multiplier <= 2:
        score = -1.0
    else:
        score = -3.0
    if keys.intersection({"RELIABLE_RECOVERY", "DAMAGE_RECOVERY"}):
        score += 2.0
    if "PROTECTION" in keys:
        score += 1.0
    if "POISON_EXPLOIT_CONTROL" in keys:
        score += 0.75
    if "SETUP_DENIAL" in keys:
        score += 0.5
    return score


def _opener_safety_profile(
    pokemon: dict,
    opponent: dict,
    opener_move_name: str,
    move_lookup: dict[str, dict],
    moves_data: list[dict],
    items: list[dict],
    ability_rules: list[dict],
    keys: set[str],
) -> tuple[float, set[str], float, dict | None, float]:
    """Evaluate incoming danger against the specific recommended opening action."""
    opener_move = move_lookup.get(opener_move_name, {})
    if not opener_move:
        matchup_notes: set[str] = set()
        return 0.0, matchup_notes, 0.0, None, 0.0
    legal_responses = [
        move
        for move in get_moves(opponent, moves_data)
        if _opener_allows_response(opener_move, move)
    ]
    worst_move: dict | None = None
    worst_score = 0.0
    for move in legal_responses:
        score = float(
            calculate_move_score(
                opponent,
                pokemon,
                move,
                items,
                ability_rules,
            )
            or 0.0
        )
        if score > worst_score:
            worst_score = score
            worst_move = move
    if worst_move is None:
        return _safety_from_values(0.0, 0.0, keys), set(), 0.0, None, 0.0
    incoming_multiplier = float(
        calculate_incoming_multiplier(
            opponent,
            pokemon,
            worst_move,
            items,
            ability_rules,
        )
        or 0.0
    )
    notes: set[str] = set()
    minimum_damage, maximum_damage = calculate_damage_range(
        opponent,
        pokemon,
        worst_move,
        items,
        ability_rules,
    )
    hp = float(pokemon.get("HP") or 0)
    if hp > 0 and minimum_damage is not None and maximum_damage is not None:
        if minimum_damage >= hp:
            notes.add("Likely Incoming OHKO")
        elif maximum_damage >= hp:
            notes.add("Possible Incoming OHKO")
    safety = _safety_from_values(worst_score, incoming_multiplier, keys)
    return safety, notes, worst_score, worst_move, incoming_multiplier


def _corrosion_only_callout(
    provider_name: str,
    opponent: dict,
    pokemon_lookup: dict[str, dict],
    raw_sources: list[tuple[str, int, str]],
) -> str | None:
    """Explain when Corrosion is the only route to poisoning the current target."""
    provider = pokemon_lookup.get(provider_name, {})
    if str(provider.get("Ability") or "").strip().casefold() != "corrosion":
        return None
    if len(raw_sources) != 1 or raw_sources[0][0] != provider_name:
        return None
    blocked_types = [
        type_name
        for type_name in ("Poison", "Steel")
        if type_name in _pokemon_types(opponent)
    ]
    if not blocked_types:
        return None
    target_name = str(opponent.get("Pokemon") or "this opponent")
    type_text = "/".join(blocked_types)
    return (
        f"{provider_name} is the only Pokémon on this team that can establish poison "
        f"against {target_name}; Corrosion bypasses its {type_text} typing."
    )


def _is_confirmed_battle_lead(opponent: dict) -> bool:
    """Return True only when opponent data identifies the confirmed lead slot."""
    return opponent.get("Slot") == 1


def _remaining_roster_for_lead(
    battle_roster: list[dict] | None,
    opponent: dict,
) -> list[dict]:
    """Return the rest of the trainer roster when the selected opponent is the lead.
    Only the lead order is treated as authoritative. Later slot order may vary with
    battle state, so Toxic Spikes planning considers the remaining roster as a set
    rather than assuming the listed sequence will be followed.
    """
    if not battle_roster or not _is_confirmed_battle_lead(opponent):
        return []
    current_name = str(opponent.get("Pokemon") or "")
    return [
        row
        for row in battle_roster
        if isinstance(row, dict)
        and row is not opponent
        and str(row.get("Pokemon") or "") != current_name
    ]


def _toxic_spikes_profile(
    opponent: dict,
    battle_roster: list[dict] | None,
    move_lookup: dict[str, dict],
) -> tuple[bool, int, tuple[str, ...], tuple[str, ...]]:
    """Return lead setup viability and roster-wide Toxic Spikes context.
    The opponent database's lead is trusted, but later ordering is not. Therefore
    grounded Poison types and hazard removal are reported as risks without assuming
    exactly when they will appear.
    """
    current_supported = _toxic_spikes_can_poison(opponent)
    targets: list[str] = []
    risks: list[str] = []
    for row in _remaining_roster_for_lead(battle_roster, opponent):
        name = str(row.get("Pokemon") or "an opposing Pokémon")
        if _toxic_spikes_clears(row):
            risks.append(f"{name} is a grounded Poison type that can clear Toxic Spikes on entry.")
            continue
        if _opponent_has_hazard_removal(row, move_lookup):
            risks.append(f"{name} has modeled hazard removal.")
        if _toxic_spikes_can_poison(row):
            targets.append(name)
    return current_supported, len(targets), tuple(targets), tuple(risks)


def _direct_poison_sources(team_data: list[dict], opponent: dict, move_lookup: dict[str, dict]) -> list[tuple[str, int, str]]:
    """Return valid current-target poison sources as (name, reliability, method)."""
    contact_available = _opponent_has_contact_move(opponent, move_lookup)
    sources: list[tuple[str, int, str]] = []
    for pokemon in team_data:
        capability = recognize_pokemon_capabilities(pokemon, move_lookup)
        keys = set(capability.capability_keys)
        if _poison_block_reason(opponent, "CORROSION" in keys):
            continue
        direct_moves: list[tuple[int, str]] = []
        for move_name in _move_names(pokemon):
            move = move_lookup.get(move_name, {})
            if str(move.get("StatusEffect") or "").casefold() == "poison" and str(move.get("Category") or "") == "Status":
                reliability = 3 if move_name == "Toxic" else 2
                direct_moves.append((reliability, move_name))
        if "STATUS_POISON_CONTACT" in keys and contact_available:
            direct_moves.append((1, "Baneful Bunker"))
        if direct_moves:
            reliability, method = max(direct_moves, key=lambda row: row[0])
            if "CORROSION" in keys and _pokemon_types(opponent).intersection({"Poison", "Steel"}):
                reliability += 2
            sources.append((capability.pokemon_name, reliability, method))
    return sources


def _fit_from_support(
    *,
    source_available: bool,
    source_reliability: int,
    keys: set[str],
    safety: float,
    notes: set[str],
) -> str:
    if "Likely Incoming OHKO" in notes:
        return "Blocked"
    if "Possible Incoming OHKO" in notes:
        return "Risky"
    if not source_available:
        return "Blocked"
    has_sustain = bool(keys.intersection({"RELIABLE_RECOVERY", "DAMAGE_RECOVERY"}))
    has_exploit = "POISON_EXPLOIT_DAMAGE" in keys
    has_control = "POISON_EXPLOIT_CONTROL" in keys
    has_protection = "PROTECTION" in keys
    has_denial = "SETUP_DENIAL" in keys
    support_count = sum((has_sustain, has_exploit, has_control, has_protection, has_denial))
    if safety >= 3 and (support_count >= 2 or (has_sustain and source_reliability >= 1)):
        return "Strong"
    if safety >= 0 and (support_count >= 1 or source_reliability >= 2):
        return "Viable"
    return "Risky"


def _moves_before(
    pokemon: dict,
    opponent: dict,
    items: list[dict],
) -> bool:
    """Return whether the saved team member is modeled to move first."""
    pokemon_speed = get_stat(pokemon, "SPE") * get_item_speed_multiplier(pokemon, items)
    opponent_speed = get_stat(opponent, "SPE") * get_item_speed_multiplier(opponent, items)
    return pokemon_speed > opponent_speed


def _can_open_toxic_then_spikes(
    pokemon: dict,
    opponent: dict,
    move_lookup: dict[str, dict],
    moves_data: list[dict],
    items: list[dict],
    ability_rules: list[dict],
    keys: set[str],
) -> bool:
    """Return whether Toxic can safely secure a turn-two Toxic Spikes setup."""
    if "STATUS_POISON_RELIABLE" not in keys or "STATUS_POISON_TEAM_SETUP" not in keys:
        return False
    if _poison_block_reason(opponent, "CORROSION" in keys) is not None:
        return False
    if not _moves_before(pokemon, opponent, items):
        return False
    safety, notes, _, _, _ = _opener_safety_profile(
        pokemon,
        opponent,
        "Toxic",
        move_lookup,
        moves_data,
        items,
        ability_rules,
        keys,
    )
    return (
        safety >= 0
        and "Likely Incoming OHKO" not in notes
        and "Possible Incoming OHKO" not in notes
    )


def _confirmed_lead(battle_roster: list[dict] | None) -> dict | None:
    if not battle_roster:
        return None
    return next((row for row in battle_roster if isinstance(row, dict) and row.get("Slot") == 1), None)


def _safe_setup_source(pokemon: dict, opponent: dict, move_name: str, move_lookup: dict[str, dict], moves_data: list[dict], items: list[dict], ability_rules: list[dict]) -> tuple[bool, float, float, dict | None, float]:
    keys = set(recognize_pokemon_capabilities(pokemon, move_lookup).capability_keys)
    safety, notes, incoming_score, threat_move, threat_multiplier = _opener_safety_profile(
        pokemon, opponent, move_name, move_lookup, moves_data, items, ability_rules, keys
    )
    safe = safety >= 0 and "Likely Incoming OHKO" not in notes and "Possible Incoming OHKO" not in notes
    return safe, safety, incoming_score, threat_move, threat_multiplier


def _selected_confirmed_lead_plan(team_data: list[dict], battle_roster: list[dict] | None, moves_data: list[dict], items: list[dict], ability_rules: list[dict], strategy_branch: str) -> tuple[dict | None, PoisonAttritionPlanResult | None]:
    lead = _confirmed_lead(battle_roster)
    if lead is None:
        return None, None
    lead_matchups = evaluate_team_matchups(team_data, lead, items, ability_rules, moves_data)
    lead_plans = evaluate_poison_attrition_plans(team_data, lead, moves_data, lead_matchups, battle_roster, items, ability_rules, strategy_branch)
    return lead, select_poison_attrition_plan(lead_plans, lead_matchups)


def _persistent_setup_from_lead_plan(lead_plan: PoisonAttritionPlanResult | None, lead: dict | None, battle_roster: list[dict] | None, move_lookup: dict[str, dict]) -> tuple[str, str, tuple[str, ...]] | None:
    if lead_plan is None or lead is None or lead_plan.plan_kind not in {"lead_team_setup", "lead_toxic_then_spikes"}:
        return None
    _, _, _, risks = _toxic_spikes_profile(lead, battle_roster, move_lookup)
    return lead_plan.lead_pokemon_name, "Toxic Spikes", risks


def _lead_plan_replan_context(lead: dict | None, lead_plan: PoisonAttritionPlanResult | None) -> str | None:
    if lead is None:
        return None
    lead_name = str(lead.get("Pokemon") or "the confirmed lead")
    if lead_plan is None:
        return f"No persistent Poison setup is assumed from the confirmed lead {lead_name}. This matchup is being re-evaluated under the selected Poison strategy."
    if lead_plan.plan_kind in {"lead_team_setup", "lead_toxic_then_spikes"}:
        return None
    if lead_plan.plan_kind == "setup_threat_direct_override":
        return f"Against the confirmed lead {lead_name}, the Compass recommended {lead_plan.lead_pokemon_name} use {lead_plan.lead_move} immediately because the normal Poison setup created a dangerous tactical exchange. Toxic Spikes are therefore not assumed active. This matchup is being re-evaluated from that post-lead state."
    if lead_plan.plan_kind in {"low_value_direct_override", "low_value_attrition_override"}:
        return f"Against the confirmed lead {lead_name}, the Compass recommended {lead_plan.lead_pokemon_name} use {lead_plan.lead_move} instead of spending a turn on Poison setup because the setup was not worth its cost. Toxic Spikes are therefore not assumed active. This matchup is being re-evaluated from that post-lead state."
    if lead_plan.plan_kind.startswith("direct_poison_then_"):
        return f"Against the confirmed lead {lead_name}, the recommended plan established poison only on that target rather than persistent Toxic Spikes. That status does not carry to the next Pokémon, so this matchup is being re-evaluated unpoisoned."
    return f"The confirmed-lead recommendation against {lead_name} did not establish persistent Toxic Spikes. This matchup is being re-evaluated under the selected Poison strategy."

def _conditional_poison_move_score(pokemon: dict, opponent: dict, move: dict, items: list[dict], ability_rules: list[dict]) -> float:
    modeled_move = dict(move)
    condition = str(modeled_move.get("ActivationCondition") or "Always")
    multiplier = float(modeled_move.get("ActivationPowerMultiplier") or 1.0)
    if condition in {"TargetPoisoned", "TargetAnyStatus"} and multiplier > 1:
        modeled_move["Power"] = float(modeled_move.get("Power") or 0) * multiplier
        modeled_move["ActivationCondition"] = "Always"
        modeled_move["ActivationPowerMultiplier"] = 1
    score = float(calculate_move_score(pokemon, opponent, modeled_move, items, ability_rules) or 0.0)
    if str(pokemon.get("Ability") or "").strip().casefold() == "merciless" and score > 0:
        score *= 1.5
    return score


def _best_offensive_payoff(pokemon: dict, opponent: dict, move_lookup: dict[str, dict], items: list[dict], ability_rules: list[dict]) -> tuple[str | None, float, bool]:
    best_name: str | None = None
    best_score = 0.0
    best_uses_poison = False
    merciless = str(pokemon.get("Ability") or "").strip().casefold() == "merciless"
    for move_name in _move_names(pokemon):
        move = move_lookup.get(move_name, {})
        if str(move.get("Category") or "") not in {"Physical", "Special"}:
            continue
        score = _conditional_poison_move_score(pokemon, opponent, move, items, ability_rules)
        condition = str(move.get("ActivationCondition") or "Always")
        uses_poison = condition in {"TargetPoisoned", "TargetAnyStatus"} or merciless
        rank = (1 if uses_poison else 0, score)
        current_rank = (1 if best_uses_poison else 0, best_score)
        if rank > current_rank:
            best_name, best_score, best_uses_poison = move_name, score, uses_poison
    return best_name, best_score, best_uses_poison



def _likely_direct_ohko(matchup: dict) -> bool:
    notes = _note_texts(matchup)
    return bool({"Likely OHKO", "Likely Survival OHKO"}.intersection(notes))


def _conditional_payoff_context(move_name: str | None, opponent: dict, move_lookup: dict[str, dict]) -> str | None:
    if not move_name:
        return None
    move = move_lookup.get(move_name, {})
    if not move:
        return None
    defender_types = list(_pokemon_types(opponent))
    multiplier = get_move_type_multiplier(move, defender_types)
    poison_multiplier = get_move_type_multiplier({"Type": "Poison"}, defender_types)
    target_name = str(opponent.get("Pokemon") or "The target")
    if str(move.get("Type") or "") != "Poison" and poison_multiplier < 1:
        return f"{target_name} resists Poison-type damage at {poison_multiplier:g}×, so even boosted Venoshock alternatives are reduced by typing while {move_name} avoids that penalty."
    if multiplier == 0:
        return f"{move_name} has no effect because of the target's typing."
    if multiplier < 1:
        return f"{move_name} is still resisted at {multiplier:g}× even after its poison-based power boost."
    if multiplier > 1:
        return f"{move_name} also benefits from {multiplier:g}× type effectiveness here."
    return None


def _dangerous_setup_move(opponent: dict, move_lookup: dict[str, dict]) -> tuple[dict | None, float]:
    """Return the opponent's most consequential modeled setup move and severity."""
    best_move: dict | None = None
    best_severity = 0.0
    opponent_move_names = set(_move_names(opponent))
    has_body_press = "Body Press" in opponent_move_names
    for move_name in opponent_move_names:
        move = move_lookup.get(move_name, {})
        if str(move.get("StageChangeTarget") or "") != "User":
            continue
        atk = max(float(move.get("AtkStageChange") or 0), 0.0)
        spa = max(float(move.get("SpAStageChange") or 0), 0.0)
        spe = max(float(move.get("SpeStageChange") or 0), 0.0)
        defense = max(float(move.get("DefStageChange") or 0), 0.0)
        spd = max(float(move.get("SpDStageChange") or 0), 0.0)
        severity = atk + spa + spe + 0.35 * (defense + spd)
        if has_body_press and defense > 0:
            severity += defense
        if severity > best_severity:
            best_move = move
            best_severity = severity
    return best_move, best_severity


def _setup_threat_description(move: dict | None) -> str | None:
    if not move:
        return None
    boosts: list[str] = []
    labels = (("AtkStageChange", "Attack"), ("SpAStageChange", "Special Attack"), ("SpeStageChange", "Speed"), ("DefStageChange", "Defense"), ("SpDStageChange", "Special Defense"))
    for field, label in labels:
        value = float(move.get(field) or 0)
        if value > 0:
            boosts.append(f"{label} +{int(value)}")
    if not boosts:
        return None
    return f"{move.get('Move')} can raise " + ", ".join(boosts) + "."


def _best_setup_denial(team_data: list[dict], opponent: dict, move_lookup: dict[str, dict], matchup_lookup: dict[str, dict]) -> tuple[str, str] | None:
    candidates: list[tuple[tuple[float, ...], str, str]] = []
    defender_types = list(_pokemon_types(opponent))
    for pokemon in team_data:
        name = str(pokemon.get("Pokemon") or "Unknown Pokémon")
        matchup = matchup_lookup.get(name, {})
        notes = _note_texts(matchup)
        if "Likely Incoming OHKO" in notes:
            continue
        keys = set(recognize_pokemon_capabilities(pokemon, move_lookup).capability_keys)
        if "SETUP_DENIAL" not in keys:
            continue
        safety = _safety_score(matchup, keys)
        ratio = float(matchup.get("Ratio") or 0.0)
        for move_name in _move_names(pokemon):
            move = move_lookup.get(move_name, {})
            if "StatReset" not in _mechanics_tags(move):
                continue
            if str(move.get("Category") or "") in {"Physical", "Special"} and get_move_type_multiplier(move, defender_types) == 0:
                continue
            candidates.append(((safety, ratio), name, move_name))
    if not candidates:
        return None
    _, name, move_name = max(candidates, key=lambda row: row[0])
    return name, move_name


def _best_likely_ohko(matchup_results: list[dict]) -> dict | None:
    candidates = [result for result in matchup_results if isinstance(result, dict) and _likely_direct_ohko(result) and "Likely Incoming OHKO" not in _note_texts(result)]
    if not candidates:
        return None
    return max(candidates, key=lambda result: (float(result.get("Best MoveScore") or 0.0), float(result.get("Ratio") or 0.0)))


def _team_has_likely_ohko(team_data: list[dict], opponent: dict, move_lookup: dict[str, dict], items: list[dict], ability_rules: list[dict]) -> bool:
    target_hp = get_stat(opponent, "HP")
    if any(str(opponent.get(f"Move{slot}") or "").startswith(("Max ", "G-Max ")) for slot in range(1, 5)):
        target_hp *= 2
    for pokemon in team_data:
        for move_name in _move_names(pokemon):
            move = move_lookup.get(move_name, {})
            if str(move.get("Category") or "") not in {"Physical", "Special"}:
                continue
            minimum_damage, _ = calculate_damage_range(pokemon, opponent, move, items, ability_rules)
            if minimum_damage is not None and minimum_damage >= target_hp:
                return True
    return False


def _opponent_burn_move(opponent: dict, move_lookup: dict[str, dict]) -> str | None:
    for move_name in _move_names(opponent):
        move = move_lookup.get(move_name, {})
        if str(move.get("StatusEffect") or "").casefold() == "burn":
            return move_name
    return None


def _physical_burn_risk(pokemon: dict, move_name: str | None, move_lookup: dict[str, dict]) -> bool:
    if not move_name:
        return False
    move = move_lookup.get(move_name, {})
    if str(move.get("Category") or "") != "Physical":
        return False
    if "Fire" in _pokemon_types(pokemon):
        return False
    ability = str(pokemon.get("Ability") or "").strip().casefold()
    return ability not in {"guts", "water veil", "water bubble", "comatose"}


def _offensive_pressure_comparison_text(team_data: list[dict], opponent: dict, move_lookup: dict[str, dict], matchup_lookup: dict[str, dict], items: list[dict], ability_rules: list[dict]) -> str | None:
    conditional: list[tuple[float, str, str]] = []
    for pokemon in team_data:
        name = str(pokemon.get("Pokemon") or "Unknown Pokémon")
        move_name, score, uses_poison = _best_offensive_payoff(pokemon, opponent, move_lookup, items, ability_rules)
        if move_name and uses_poison and score > 0:
            conditional.append((score, name, move_name))
    conditional.sort(reverse=True)
    parts: list[str] = []
    if conditional:
        top = conditional[:2]
        parts.append("Conditional poison payoff: " + "; ".join(f"{name} {move} {score:.2f}" for score, name, move in top) + ".")
    direct_candidates = [m for m in matchup_lookup.values() if isinstance(m, dict) and m.get("Best Move")]
    if direct_candidates:
        direct = max(direct_candidates, key=lambda result: float(result.get("Best MoveScore") or 0.0))
        direct_note = " Likely OHKO." if _likely_direct_ohko(direct) else "."
        parts.append(f"Best immediate non-conditional option: {direct.get('Pokemon')} {direct.get('Best Move')} {float(direct.get('Best MoveScore') or 0.0):.2f}.{direct_note}".replace("..", "."))
    return " ".join(parts) or None


def _magic_guard_attrition_note(opponent: dict) -> str | None:
    if str(opponent.get("Ability") or "").strip().casefold() != "magic guard":
        return None
    return "Magic Guard allows poison status but prevents poison's residual damage, so a pure attrition line has little value against this target."


def _opponent_recovery_moves(opponent: dict, move_lookup: dict[str, dict]) -> list[str]:
    return [name for name in _move_names(opponent) if "RecoveryMove" in _mechanics_tags(move_lookup.get(name, {}))]


def _opponent_status_block_move(opponent: dict) -> str | None:
    return next((name for name in _move_names(opponent) if name == "Safeguard"), None)


def _screen_matches_threat(move_name: str, matchup: dict) -> bool:
    category = str(matchup.get("Worst Incoming Move Category") or "")
    return (move_name == "Reflect" and category == "Physical") or (move_name == "Light Screen" and category == "Special")


def _defense_setup_matches_threat(move: dict, matchup: dict) -> bool:
    category = str(matchup.get("Worst Incoming Move Category") or "")
    if category == "Physical":
        return float(move.get("DefStageChange") or 0) > 0
    if category == "Special":
        return float(move.get("SpDStageChange") or 0) > 0
    return False


def _attrition_profile(pokemon: dict, opponent: dict, matchup: dict, move_lookup: dict[str, dict], setup_threat: bool = False) -> tuple[str | None, float, str]:
    """Return the best immediate attrition action plus a branch-specific value explanation."""
    contact_available = _opponent_has_contact_move(opponent, move_lookup)
    recovery_moves: list[str] = []
    protection_moves: list[str] = []
    screen_moves: list[str] = []
    defense_moves: list[str] = []
    denial_moves: list[str] = []
    draining_moves: list[str] = []
    control_moves: list[str] = []
    scored: list[tuple[float, str]] = []
    for move_name in _move_names(pokemon):
        move = move_lookup.get(move_name, {})
        tags = _mechanics_tags(move)
        score = 0.0
        if "StatReset" in tags:
            denial_moves.append(move_name)
            score = 9.0 if setup_threat else 2.0
        if "RecoveryMove" in tags:
            recovery_moves.append(move_name)
            score = max(score, 6.0 if move_name == "Rest" else 8.0)
        if "Protection" in tags:
            protection_moves.append(move_name)
            contact_bonus = 1.0 if contact_available and move_name in {"Baneful Bunker", "Obstruct"} else 0.0
            score = max(score, 6.5 + contact_bonus)
        if "Screen" in tags:
            screen_moves.append(move_name)
            score = max(score, 6.0 if _screen_matches_threat(move_name, matchup) else 3.0)
        if "DefenseSetup" in tags:
            defense_moves.append(move_name)
            score = max(score, 6.0 if _defense_setup_matches_threat(move, matchup) else 3.0)
        if "HPStealingMove" in tags:
            draining_moves.append(move_name)
            score = max(score, 5.5)
        if _negative_target_stage_control(move):
            control_moves.append(move_name)
            score = max(score, 5.0)
        if score > 0:
            scored.append((score, move_name))
    if not scored:
        return None, 0.0, "This Pokémon lacks a modeled recovery, protection, defensive setup, screen, draining, or setup-denial action for an attrition loop."
    synergy = 0.0
    features: list[str] = []
    if recovery_moves and protection_moves:
        synergy += 3.0
        features.append("recovery plus protected turns")
    if recovery_moves and defense_moves:
        synergy += 2.5
        features.append("recovery plus defensive setup")
    if recovery_moves and screen_moves:
        synergy += 2.0
        features.append("recovery plus screen support")
    if draining_moves:
        synergy += 1.5
        features.append("damaging recovery")
    if setup_threat and denial_moves:
        synergy += 3.0
        features.append("setup denial")
    best_score, best_move = max(scored, key=lambda row: row[0])
    value = best_score + synergy
    description = f"{pokemon.get('Pokemon') or 'This Pokémon'} can anchor attrition with {best_move}"
    if features:
        description += ", backed by " + ", ".join(features)
    if best_move in {"Baneful Bunker", "Obstruct"} and contact_available:
        description += "; the opponent has at least one contact move, so the move's contact punishment is live"
    description += "."
    return best_move, value, description


def _preferred_attrition_move(pokemon: dict, opponent: dict, matchup: dict, move_lookup: dict[str, dict], setup_threat: bool = False) -> str | None:
    return _attrition_profile(pokemon, opponent, matchup, move_lookup, setup_threat)[0]


def _best_followup(team_data: list[dict], opponent: dict, move_lookup: dict[str, dict], matchup_lookup: dict[str, dict], items: list[dict], ability_rules: list[dict], strategy_branch: str, poisoned: bool, current_pokemon_name: str | None = None) -> tuple[str, str | None, float | None]:
    candidates: list[tuple[tuple[float, ...], str, str | None, float | None]] = []
    setup_move, setup_severity = _dangerous_setup_move(opponent, move_lookup)
    burn_move = _opponent_burn_move(opponent, move_lookup)
    setup_threat = setup_move is not None and setup_severity >= 2.0
    for pokemon in team_data:
        name = str(pokemon.get("Pokemon") or "Unknown Pokémon")
        matchup = matchup_lookup.get(name, {})
        keys = set(recognize_pokemon_capabilities(pokemon, move_lookup).capability_keys)
        safety = _safety_score(matchup, keys)
        notes = _note_texts(matchup)
        if "Likely Incoming OHKO" in notes:
            continue
        ratio = float(matchup.get("Ratio") or 0.0)
        stay_bonus = 1.0 if current_pokemon_name and name == current_pokemon_name else 0.0
        if strategy_branch == "poison_offensive_pressure":
            move_name, conditional_score, uses_poison = _best_offensive_payoff(pokemon, opponent, move_lookup, items, ability_rules)
            if not poisoned:
                uses_poison = False
                conditional_score = float(matchup.get("Best MoveScore") or 0.0)
                move_name = str(matchup.get("Best Move") or "") or move_name
            burn_penalty = 0.72 if burn_move and _physical_burn_risk(pokemon, move_name, move_lookup) and not _likely_direct_ohko(matchup) else 1.0
            switch_factor = 1.0 if not current_pokemon_name or name == current_pokemon_name else 0.80
            adjusted_score = conditional_score * burn_penalty * switch_factor
            depth = _strategic_depth(keys, strategy_branch)
            rank = (1.0 if poisoned and uses_poison else 0.0, adjusted_score, safety, depth, stay_bonus, ratio)
            candidates.append((rank, name, move_name, conditional_score if poisoned and uses_poison else None))
        else:
            attrition_move, attrition_value, _ = _attrition_profile(pokemon, opponent, matchup, move_lookup, setup_threat=setup_threat)
            depth = _strategic_depth(keys, strategy_branch)
            has_attrition_tools = attrition_move is not None
            denial_bonus = 2.0 if setup_threat and "SETUP_DENIAL" in keys else 0.0
            rank = (1.0 if has_attrition_tools else 0.0, denial_bonus, safety, attrition_value, depth, stay_bonus, ratio)
            candidates.append((rank, name, attrition_move, None))
    if not candidates:
        first = str(team_data[0].get("Pokemon") or "Unknown Pokémon") if team_data else "Unknown Pokémon"
        return first, None, None
    _, name, move_name, conditional_score = max(candidates, key=lambda row: row[0])
    return name, move_name, conditional_score


def project_poisoned_followup(team_data: list[dict], opponent: dict, moves_data: list[dict], matchup_results: list[dict], items: list[dict] | None = None, ability_rules: list[dict] | None = None, strategy_branch: str = "poison_attrition", current_pokemon_name: str | None = None) -> tuple[str, str | None, float | None]:
    """Return the best modeled follow-up if the selected non-lead is already poisoned."""
    items = items or []
    ability_rules = ability_rules or []
    move_lookup = {move["Move"]: move for move in moves_data if isinstance(move, dict) and isinstance(move.get("Move"), str) and move.get("Move")}
    matchup_lookup: dict[str, dict] = {str(result["Pokemon"]): result for result in matchup_results if isinstance(result, dict) and isinstance(result.get("Pokemon"), str) and result.get("Pokemon")}
    return _best_followup(team_data, opponent, move_lookup, matchup_lookup, items, ability_rules, strategy_branch, True, current_pokemon_name=current_pokemon_name)


def _switch_cost_context(current_name: str, follow_name: str, strategy_branch: str) -> str | None:
    if not current_name or current_name == follow_name:
        return "Staying in avoids spending an additional turn on a switch." if current_name else None
    if strategy_branch == "poison_offensive_pressure":
        return f"The follow-up comparison includes a switch-turn penalty; {follow_name}'s offensive payoff remains strong enough to justify leaving {current_name}."
    return f"The follow-up comparison favors {follow_name}'s safer or deeper attrition profile strongly enough to justify the switch from {current_name}."


def _attrition_context(pokemon: dict, opponent: dict, matchup: dict, move_lookup: dict[str, dict], setup_threat: bool = False) -> str:
    _, _, description = _attrition_profile(pokemon, opponent, matchup, move_lookup, setup_threat)
    opponent_recovery = _opponent_recovery_moves(opponent, move_lookup)
    if opponent_recovery:
        description += f" The opponent knows {', '.join(opponent_recovery)}, so the wall/stall loop must remain stable long enough to overcome its recovery."
    safeguard = _opponent_status_block_move(opponent)
    if safeguard:
        description += f" The opponent also knows {safeguard}; if it is already active, poison establishment must be re-evaluated."
    return description


def _attrition_action_detail(move_name: str | None, move_lookup: dict[str, dict]) -> str:
    if not move_name:
        return "use the defensive matchup to let poison progress"
    tags = _mechanics_tags(move_lookup.get(move_name, {}))
    if "StatReset" in tags:
        return f"keep {move_name} ready to erase boosts if the opponent sets up"
    if "RecoveryMove" in tags:
        return f"use {move_name} as needed to maintain the wall while poison progresses"
    if "Protection" in tags:
        return f"use {move_name} on appropriate turns to buy additional poison damage"
    if "Screen" in tags:
        return f"use {move_name} to reduce incoming pressure while poison progresses"
    if "DefenseSetup" in tags:
        return f"use {move_name} to reinforce the relevant defense while poison progresses"
    if "HPStealingMove" in tags:
        return f"use {move_name} to deal damage while recovering HP"
    return f"use {move_name} as the preferred attrition tool"


def _direct_fallback_text(matchup_results: list[dict]) -> str:
    if not matchup_results:
        return "Use Full Analysis or Strongest Matchup for a direct alternative."
    best = max(matchup_results, key=lambda result: (float(result.get("Ratio") or 0.0), float(result.get("Best MoveScore") or 0.0)))
    name = str(best.get("Pokemon") or "the strongest direct matchup")
    move = str(best.get("Best Move") or "its best move")
    return f"If the strategy state is no longer valid, the current strongest direct fallback is {name} with {move}."


def describe_poison_attrition_fallback(team_data: list[dict], opponent: dict, moves_data: list[dict], matchup_results: list[dict], items: list[dict] | None = None, ability_rules: list[dict] | None = None, strategy_branch: str = "poison_attrition") -> str:
    """Explain why the selected Poison branch did not produce a safe recommendation."""
    items = items or []
    ability_rules = ability_rules or []
    move_lookup = {move["Move"]: move for move in moves_data if isinstance(move, dict) and isinstance(move.get("Move"), str) and move.get("Move")}
    raw_sources = _direct_poison_sources(team_data, opponent, move_lookup)
    target_name = str(opponent.get("Pokemon") or "this opponent")
    global_block = _poison_block_reason(opponent, has_corrosion=any(str(p.get("Ability") or "").strip().casefold() == "corrosion" for p in team_data))
    if global_block:
        return f"Poison is blocked against {target_name}: {global_block} Battle Compass is deviating to the strongest direct matchup."
    if raw_sources:
        unsafe: list[str] = []
        safe: list[str] = []
        for source_name, _, source_method in raw_sources:
            pokemon = next((p for p in team_data if str(p.get("Pokemon") or "") == source_name), {})
            is_safe, _, _, threat_move, _ = _safe_setup_source(pokemon, opponent, source_method, move_lookup, moves_data, items, ability_rules)
            if is_safe:
                safe.append(source_name)
            else:
                threat = str(threat_move.get("Move")) if threat_move else "the modeled incoming response"
                unsafe.append(f"{source_name} ({threat})")
        if not safe and unsafe:
            return f"Poison is available against {target_name}, but establishing it is unsafe with the available setters: {', '.join(unsafe)}. Battle Compass is deviating to the strongest direct matchup."
        if safe:
            branch_label = "Offensive Pressure" if strategy_branch == "poison_offensive_pressure" else "Attrition"
            return f"Poison can be established safely, but it does not create a sufficiently valuable {branch_label} follow-up in this matchup. Battle Compass is deviating to the strongest direct matchup."
    return f"Poison cannot be established reliably against {target_name} with the current team, so Battle Compass is deviating to the strongest direct matchup."


def _best_direct_attack_profile(pokemon: dict, opponent: dict, move_lookup: dict[str, dict], items: list[dict], ability_rules: list[dict]) -> tuple[str | None, float, bool]:
    target_hp = get_stat(opponent, "HP")
    if any(str(opponent.get(f"Move{slot}") or "").startswith(("Max ", "G-Max ")) for slot in range(1, 5)):
        target_hp *= 2
    best_name: str | None = None
    best_score = 0.0
    best_likely_ohko = False
    for move_name in _move_names(pokemon):
        move = move_lookup.get(move_name, {})
        if str(move.get("Category") or "") not in {"Physical", "Special"}:
            continue
        score = float(calculate_move_score(pokemon, opponent, move, items, ability_rules) or 0.0)
        if score <= best_score:
            continue
        minimum_damage, _ = calculate_damage_range(pokemon, opponent, move, items, ability_rules)
        best_name = move_name
        best_score = score
        best_likely_ohko = minimum_damage is not None and minimum_damage >= target_hp
    return best_name, best_score, best_likely_ohko


def _nonlead_toxic_spikes_profile(opponent: dict, battle_roster: list[dict] | None, move_lookup: dict[str, dict]) -> tuple[int, tuple[str, ...], tuple[str, ...]]:
    if not battle_roster or _is_confirmed_battle_lead(opponent):
        return 0, (), ()
    current_name = str(opponent.get("Pokemon") or "")
    targets: list[str] = []
    risks: list[str] = []
    for row in battle_roster:
        if not isinstance(row, dict) or row.get("Slot") == 1 or str(row.get("Pokemon") or "") == current_name:
            continue
        name = str(row.get("Pokemon") or "an opposing Pokémon")
        if _toxic_spikes_clears(row):
            risks.append(f"{name} is a grounded Poison type that can clear Toxic Spikes on entry.")
            continue
        if _opponent_has_hazard_removal(row, move_lookup):
            risks.append(f"{name} has modeled hazard removal.")
        if _toxic_spikes_can_poison(row):
            targets.append(name)
    return len(targets), tuple(targets), tuple(risks)


def evaluate_poison_attrition_plans(team_data: list[dict], opponent: dict, moves_data: list[dict], matchup_results: list[dict], battle_roster: list[dict] | None = None, items: list[dict] | None = None, ability_rules: list[dict] | None = None, strategy_branch: str = "poison_attrition") -> list[PoisonAttritionPlanResult]:
    """Evaluate Poison plans for Offensive Pressure or Attrition with battle continuity."""
    items = items or []
    ability_rules = ability_rules or []
    move_lookup = {move["Move"]: move for move in moves_data if isinstance(move, dict) and isinstance(move.get("Move"), str) and move.get("Move")}
    matchup_lookup: dict[str, dict] = {str(result["Pokemon"]): result for result in matchup_results if isinstance(result, dict) and isinstance(result.get("Pokemon"), str) and result.get("Pokemon")}
    pokemon_lookup = {str(pokemon.get("Pokemon") or ""): pokemon for pokemon in team_data if isinstance(pokemon, dict) and pokemon.get("Pokemon")}
    confirmed_lead = _is_confirmed_battle_lead(opponent)
    lead_record: dict | None = None
    lead_plan: PoisonAttritionPlanResult | None = None
    if not confirmed_lead:
        lead_record, lead_plan = _selected_confirmed_lead_plan(team_data, battle_roster, moves_data, items, ability_rules, strategy_branch)
    expected_setup = _persistent_setup_from_lead_plan(lead_plan, lead_record, battle_roster, move_lookup)
    assumed_poisoned = expected_setup is not None and _toxic_spikes_can_poison(opponent)
    if not confirmed_lead and expected_setup is not None and not assumed_poisoned:
        setter_name, setter_move, _ = expected_setup
        replan_context = f"Assuming the confirmed-lead recommendation was followed, {setter_name} established {setter_move}. {opponent.get('Pokemon') or 'This opponent'} is not affected by Toxic Spikes, so this matchup is being re-evaluated directly while the hazard remains relevant only to eligible switch-ins."
    else:
        replan_context = _lead_plan_replan_context(lead_record, lead_plan) if not confirmed_lead and expected_setup is None else None
    raw_direct_sources = _direct_poison_sources(team_data, opponent, move_lookup)
    safe_direct_sources: list[tuple[str, int, str]] = []
    for source_name, reliability, source_method in raw_direct_sources:
        source_pokemon = pokemon_lookup.get(source_name, {})
        safe, _, _, _, _ = _safe_setup_source(source_pokemon, opponent, source_method, move_lookup, moves_data, items, ability_rules)
        if safe:
            safe_direct_sources.append((source_name, reliability, source_method))
    team_source = max(safe_direct_sources, key=lambda source: source[1], default=None)
    spikes_current_supported, spikes_targets, spikes_names, spikes_risks = _toxic_spikes_profile(opponent, battle_roster, move_lookup)
    replan_spikes_targets, replan_spikes_names, replan_spikes_risks = _nonlead_toxic_spikes_profile(opponent, battle_roster, move_lookup)
    setup_threat_move, setup_threat_severity = _dangerous_setup_move(opponent, move_lookup)
    setup_denial = _best_setup_denial(team_data, opponent, move_lookup, matchup_lookup) if setup_threat_move else None
    likely_ohko_direct = _best_likely_ohko(matchup_results) if setup_threat_move and setup_threat_severity >= 2.0 else None
    setup_threat_text = _setup_threat_description(setup_threat_move)
    burn_move = _opponent_burn_move(opponent, move_lookup)
    results: list[PoisonAttritionPlanResult] = []
    if not confirmed_lead and assumed_poisoned and expected_setup is not None:
        setter_name, setter_move, setup_risks = expected_setup
        if strategy_branch == "poison_attrition" and _magic_guard_attrition_note(opponent):
            return [PoisonAttritionPlanResult(
                pokemon_name=str(result.get("Pokemon") or "Unknown Pokémon"), fit="Blocked", fit_rank=_FIT_RANK["Blocked"],
                summary="Poison can be present, but residual-damage attrition is neutralized.",
                reason=_magic_guard_attrition_note(opponent) or "Attrition value is blocked.", action="Direct fallback",
                action_detail="Use Full Analysis or Strongest Matchup for a direct alternative.", plan_kind="low_value_attrition_override",
                can_override_direct=False, source_reliability=3, strategic_depth=0.0, safety_score=0.0, team_setup_priority=0,
                incoming_worst_score=float(result.get("Incoming Worst Score") or 0.0), lead_pokemon_name=str(result.get("Pokemon") or "Unknown Pokémon"),
                lead_move=str(result.get("Best Move") or ""), opener_threat_move=None, opener_threat_category=None, opener_threat_type=None,
                opener_threat_score=0.0, opener_threat_multiplier=0.0, strategy_branch=strategy_branch, assumed_poisoned=True,
                state_assumption=f"Assuming the recommendation against the confirmed lead was followed, {setter_name} established {setter_move}; {opponent.get('Pokemon') or 'this opponent'} therefore enters poisoned.",
                fallback_if_assumption_fails=_direct_fallback_text(matchup_results), recommended_pokemon_name=str(result.get("Pokemon") or "Unknown Pokémon"),
                conditional_move_name=None, conditional_move_score=None,
            ) for result in matchup_results if isinstance(result, dict)]
        assumption = f"Assuming the recommendation against the confirmed lead was followed, {setter_name} established {setter_move}; {opponent.get('Pokemon') or 'this opponent'} therefore enters poisoned."
        if setup_risks:
            assumption += " This remains conditional because " + " ".join(setup_risks)
        fallback = _direct_fallback_text(matchup_results)
        for pokemon in team_data:
            name = str(pokemon.get("Pokemon") or "Unknown Pokémon")
            matchup = matchup_lookup.get(name, {})
            keys = set(recognize_pokemon_capabilities(pokemon, move_lookup).capability_keys)
            safety = _safety_score(matchup, keys)
            notes = _note_texts(matchup)
            selected_move: str | None = None
            if strategy_branch == "poison_offensive_pressure":
                move_name, conditional_score, uses_poison = _best_offensive_payoff(pokemon, opponent, move_lookup, items, ability_rules)
                participates = uses_poison and move_name is not None
                summary = "This Pokémon can convert the established poison into immediate offensive pressure." if participates else "This Pokémon does not add a modeled poison-enabled offensive payoff."
                reason = f"{move_name} benefits from the assumed poison state." if participates else "Another teammate offers a stronger poison-enabled offensive continuation."
                if participates:
                    comparison = _offensive_pressure_comparison_text(team_data, opponent, move_lookup, matchup_lookup, items, ability_rules)
                    if comparison:
                        reason += f" {comparison}"
                    if burn_move and _physical_burn_risk(pokemon, move_name, move_lookup):
                        reason += f" {opponent.get('Pokemon') or 'The opponent'} knows {burn_move}, so this physical continuation carries burn risk and is devalued relative to comparable special offense."
                payoff_context = _conditional_payoff_context(move_name, opponent, move_lookup) if participates else None
                if payoff_context:
                    reason += f" {payoff_context}"
                action = f"{name}: {move_name}" if move_name else "Direct fallback"
                action_detail = f"Treat the target as poisoned and use {move_name}." if move_name else "Use Full Analysis for a direct alternative."
                depth = _strategic_depth(keys, strategy_branch) + (4.0 if participates else 0.0)
                fit = "Strong" if participates and safety >= 0 else "Viable" if participates else "Blocked"
                conditional_name = move_name if participates else None
                conditional_value = conditional_score if participates else None
                selected_move = move_name
            else:
                attrition_move = _preferred_attrition_move(pokemon, opponent, matchup, move_lookup, setup_threat=setup_threat_move is not None and setup_threat_severity >= 2.0)
                depth = _strategic_depth(keys, strategy_branch)
                participates = attrition_move is not None or depth >= 2.0
                summary = "This Pokémon can take over as the attrition anchor while poison ticks." if participates else "This Pokémon lacks a strong modeled stall or wall role."
                reason = _attrition_context(pokemon, opponent, matchup, move_lookup, setup_threat=setup_threat_move is not None and setup_threat_severity >= 2.0) if participates else "Another teammate offers a better defensive continuation."
                if participates and setup_threat_text:
                    reason += f" Setup warning: {setup_threat_text}"
                    if setup_denial:
                        reason += f" {setup_denial[0]} can use {setup_denial[1]} to reset those boosts."
                action = f"{name}: {attrition_move or 'hold the line'}"
                action_detail = _attrition_action_detail(attrition_move, move_lookup).capitalize() + "."
                fit = "Strong" if participates and safety >= 1 else "Viable" if participates and safety >= 0 else "Risky" if participates else "Blocked"
                conditional_name = None
                conditional_value = None
                selected_move = attrition_move
            results.append(PoisonAttritionPlanResult(
                pokemon_name=name, fit=fit, fit_rank=_FIT_RANK[fit], summary=summary, reason=reason, action=action, action_detail=action_detail,
                plan_kind="followup_assumed_poison", can_override_direct=fit in {"Strong", "Viable"}, source_reliability=3,
                strategic_depth=depth, safety_score=safety, team_setup_priority=5, incoming_worst_score=float(matchup.get("Incoming Worst Score") or 0.0),
                lead_pokemon_name=name, lead_move=selected_move or "", opener_threat_move=None, opener_threat_category=None,
                opener_threat_type=None, opener_threat_score=0.0, opener_threat_multiplier=0.0, strategy_branch=strategy_branch,
                assumed_poisoned=True, state_assumption=assumption, fallback_if_assumption_fails=fallback, recommended_pokemon_name=name,
                conditional_move_name=conditional_name, conditional_move_score=conditional_value,
            ))
        return results
    for pokemon in team_data:
        name = str(pokemon.get("Pokemon") or "Unknown Pokémon")
        matchup = matchup_lookup.get(name, {})
        keys = set(recognize_pokemon_capabilities(pokemon, move_lookup).capability_keys)
        effective_keys = _effective_strategy_keys(keys, opponent)
        safety = _safety_score(matchup, effective_keys)
        notes = _note_texts(matchup)
        incoming_score = float(matchup.get("Incoming Worst Score") or 0.0)
        depth = _strategic_depth(effective_keys, strategy_branch)
        own_source = next((source for source in safe_direct_sources if source[0] == name), None)
        source = own_source or team_source
        fit = "Blocked"
        summary = "No meaningful Poison strategy role is available for this Pokémon."
        reason = "The selected branch cannot be established or exploited safely in this matchup."
        action = "Direct fallback"
        action_detail = "Use Full Analysis or Strongest Matchup for a direct alternative."
        plan_kind = "current_target"
        setup_priority = 0
        source_reliability = source[1] if source else 0
        lead_name = name
        lead_move = ""
        recommended_name = name
        conditional_name = None
        conditional_score = None
        state_assumption = replan_context
        fallback = None
        if confirmed_lead and setup_threat_move is not None and setup_threat_severity >= 2.0 and likely_ohko_direct is not None and str(likely_ohko_direct.get("Pokemon") or "") == name:
            direct_move = str(likely_ohko_direct.get("Best Move") or "")
            plan_kind = "setup_threat_direct_override"
            setup_priority = 8
            fit = "Strong"
            lead_name = name
            lead_move = direct_move
            recommended_name = name
            action = f"{name}: {direct_move}"
            action_detail = f"Use {direct_move} immediately instead of giving {opponent.get('Pokemon') or 'the opponent'} a free setup turn."
            summary = f"The selected Poison strategy is tactically overridden because {opponent.get('Pokemon') or 'the opponent'} has dangerous setup and {name} can likely remove it now."
            reason = f"{setup_threat_text or 'The opponent has a dangerous setup move.'} A Poison setup turn would let it boost before the plan is established."
            if setup_denial:
                reason += f" {setup_denial[0]} can reset boosts with {setup_denial[1]}, but that creates a more dangerous exchange than immediate removal."
            reason += f" {direct_move} is modeled as a Likely OHKO, so the Compass is deviating for tactical safety rather than abandoning the Poison strategy generally."
            conditional_name = None
            conditional_score = None
            threat_move = None
            threat_multiplier = 0.0
            incoming_score = float(matchup.get("Incoming Worst Score") or 0.0)
        else:
            use_toxic_then_spikes = confirmed_lead and spikes_targets > 0 and _can_open_toxic_then_spikes(pokemon, opponent, move_lookup, moves_data, items, ability_rules, effective_keys)
            safe_spikes, spikes_safety, spikes_incoming, spikes_threat, spikes_multiplier = _safe_setup_source(pokemon, opponent, "Toxic Spikes", move_lookup, moves_data, items, ability_rules) if "STATUS_POISON_TEAM_SETUP" in keys else (False, safety, incoming_score, None, 0.0)
            team_setup_targets = spikes_targets if confirmed_lead else replan_spikes_targets
            team_setup_names = spikes_names if confirmed_lead else replan_spikes_names
            team_setup_risks = spikes_risks if confirmed_lead else replan_spikes_risks
            use_team_setup = "STATUS_POISON_TEAM_SETUP" in keys and team_setup_targets > 0 and safe_spikes and (confirmed_lead or expected_setup is None)
            if use_toxic_then_spikes or use_team_setup:
                poisoned_current = use_toxic_then_spikes
                follow_name, follow_move, follow_score = _best_followup(team_data, opponent, move_lookup, matchup_lookup, items, ability_rules, strategy_branch, poisoned_current, current_pokemon_name=name)
                setup_sequence = "Toxic → Toxic Spikes" if use_toxic_then_spikes else "Toxic Spikes"
                plan_kind = "lead_toxic_then_spikes" if use_toxic_then_spikes else "lead_team_setup"
                setup_priority = 4 if use_toxic_then_spikes else 3
                fit = "Strong"
                lead_name = name
                lead_move = "Toxic" if use_toxic_then_spikes else "Toxic Spikes"
                recommended_name = name
                target_text = ", ".join(team_setup_names[:3])
                summary = f"{name} can establish the battle's poison engine, then hand off to {follow_name}." if follow_name != name else f"{name} can establish the poison engine and remain in afterward."
                if confirmed_lead:
                    reason = f"The confirmed lead gives {name} a safe setup window. Toxic Spikes can pressure {team_setup_targets} modeled later target(s) without assuming their exact order."
                else:
                    plan_kind = "followup_replan_team_setup"
                    reason = f"Because the confirmed-lead plan did not leave persistent Toxic Spikes active for this matchup, the Compass is re-evaluating setup here. Toxic Spikes can still pressure {team_setup_targets} other modeled non-lead target(s); their exact later order is not assumed."
                if target_text:
                    reason += f" Other poisonable targets include {target_text}."
                if team_setup_risks:
                    reason += " Risks: " + " ".join(team_setup_risks)
                if setup_threat_text:
                    reason += f" Setup warning: {setup_threat_text}"
                    if setup_denial:
                        reason += f" {setup_denial[0]} can use {setup_denial[1]} to reset those boosts if needed."
                if follow_name == name:
                    action = f"{setup_sequence} → stay with {name}"
                    action_detail = f"Use {setup_sequence}. After setup, keep {name} in because it remains the preferred immediate follow-up"
                else:
                    action = f"{setup_sequence} → {follow_name}"
                    action_detail = f"Use {setup_sequence}, then switch to {follow_name} for the immediate matchup"
                if follow_move:
                    if strategy_branch == "poison_attrition":
                        action_detail += f"; {_attrition_action_detail(follow_move, move_lookup)}."
                    else:
                        action_detail += f" and use {follow_move} as the preferred next action."
                else:
                    action_detail += "."
                switch_context = _switch_cost_context(name, follow_name, strategy_branch)
                if switch_context:
                    reason += f" {switch_context}"
                if strategy_branch == "poison_attrition":
                    follow_pokemon = pokemon_lookup.get(follow_name, {})
                    follow_matchup = matchup_lookup.get(follow_name, {})
                    reason += f" {_attrition_context(follow_pokemon, opponent, follow_matchup, move_lookup, setup_threat=setup_threat_move is not None and setup_threat_severity >= 2.0)}"
                source_reliability = 3
                safety = spikes_safety
                incoming_score = spikes_incoming
                conditional_name = follow_move if poisoned_current and strategy_branch == "poison_offensive_pressure" else None
                conditional_score = follow_score if poisoned_current and strategy_branch == "poison_offensive_pressure" else None
                threat_move = spikes_threat
                threat_multiplier = spikes_multiplier
            elif source is not None:
                provider_name, source_reliability, provider_method = source
                provider_matchup = matchup_lookup.get(provider_name, {})
                provider_best_move = str(provider_matchup.get("Best Move") or "")
                if provider_best_move and _likely_direct_ohko(provider_matchup):
                    plan_kind = "low_value_direct_override"
                    setup_priority = 6
                    fit = "Strong"
                    lead_name = provider_name
                    lead_move = provider_best_move
                    recommended_name = provider_name
                    action = f"{provider_name}: {provider_best_move}"
                    action_detail = f"Use {provider_best_move} instead of spending a turn on {provider_method}."
                    summary = f"Poison is available, but {provider_name} can likely remove the target immediately."
                    reason = f"{provider_method} can establish poison, but {provider_best_move} is already modeled as a Likely OHKO. Spending a setup turn would add unnecessary exposure before an opponent that can likely be removed now, so the Compass is deviating from the selected Poison plan on value rather than availability."
                    corrosion_callout = _corrosion_only_callout(provider_name, opponent, pokemon_lookup, raw_direct_sources)
                    if corrosion_callout:
                        reason = f"{corrosion_callout} {reason}"
                    conditional_name = None
                    conditional_score = None
                    threat_move = None
                    threat_multiplier = 0.0
                else:
                    poisoned_after_setup = True
                    follow_name, follow_move, follow_score = _best_followup(team_data, opponent, move_lookup, matchup_lookup, items, ability_rules, strategy_branch, poisoned_after_setup, current_pokemon_name=provider_name)
                    plan_kind = "direct_poison_then_pressure" if strategy_branch == "poison_offensive_pressure" else "direct_poison_then_attrition"
                    setup_priority = 2
                    fit = "Strong" if safety >= 0 else "Viable"
                    lead_name = provider_name
                    lead_move = provider_method
                    recommended_name = provider_name
                    summary = f"{provider_name} can establish poison, then {follow_name} can execute the selected branch."
                    if provider_name == follow_name:
                        action = f"{provider_name}: {provider_method} → stay in"
                        action_detail = f"Use {provider_method} to establish poison, then keep {provider_name} in"
                    else:
                        action = f"{provider_name}: {provider_method} → {follow_name}"
                        action_detail = f"Use {provider_method} to establish poison, then pivot to {follow_name}"
                    if follow_move:
                        if strategy_branch == "poison_attrition":
                            action_detail += f"; {_attrition_action_detail(follow_move, move_lookup)}."
                        else:
                            action_detail += f" and use {follow_move} as the preferred continuation."
                    else:
                        action_detail += "."
                    reason = "Poison can be established safely and the follow-up directly serves Offensive Pressure." if strategy_branch == "poison_offensive_pressure" else "Poison can be established safely and the follow-up provides the strongest modeled wall/stall continuation."
                    switch_context = _switch_cost_context(provider_name, follow_name, strategy_branch)
                    if switch_context:
                        reason += f" {switch_context}"
                    if strategy_branch == "poison_attrition":
                        follow_pokemon = pokemon_lookup.get(follow_name, {})
                        follow_matchup = matchup_lookup.get(follow_name, {})
                        reason += f" {_attrition_context(follow_pokemon, opponent, follow_matchup, move_lookup, setup_threat=setup_threat_move is not None and setup_threat_severity >= 2.0)}"
                    if strategy_branch == "poison_offensive_pressure":
                        payoff_context = _conditional_payoff_context(follow_move, opponent, move_lookup)
                        if payoff_context:
                            reason += f" {payoff_context}"
                        comparison = _offensive_pressure_comparison_text(team_data, opponent, move_lookup, matchup_lookup, items, ability_rules)
                        if comparison:
                            reason += f" {comparison}"
                        follow_pokemon = pokemon_lookup.get(follow_name, {})
                        if burn_move and _physical_burn_risk(follow_pokemon, follow_move, move_lookup):
                            reason += f" {opponent.get('Pokemon') or 'The opponent'} knows {burn_move}; a physical continuation can be weakened by burn, so comparable special pressure is preferred when available."
                    corrosion_callout = _corrosion_only_callout(provider_name, opponent, pokemon_lookup, raw_direct_sources)
                    if corrosion_callout:
                        reason = f"{corrosion_callout} {reason}"
                    conditional_name = follow_move if strategy_branch == "poison_offensive_pressure" else None
                    conditional_score = follow_score if strategy_branch == "poison_offensive_pressure" else None
                    depth += 3.0
                    threat_move = None
                    threat_multiplier = 0.0
            else:
                threat_move = None
                threat_multiplier = 0.0
                if not confirmed_lead and expected_setup is not None and not _toxic_spikes_can_poison(opponent):
                    reason = "The Lead strategy may have established Toxic Spikes, but this opponent is not affected by them. A direct poison route is required for this target."
                elif _poison_block_reason(opponent, has_corrosion="CORROSION" in effective_keys):
                    reason = _poison_block_reason(opponent, has_corrosion="CORROSION" in effective_keys) or reason
        threat_name = str(threat_move.get("Move")) if threat_move else None
        threat_category = str(threat_move.get("Category")) if threat_move else None
        threat_type = str(threat_move.get("Type")) if threat_move else None
        results.append(PoisonAttritionPlanResult(
            pokemon_name=name, fit=fit, fit_rank=_FIT_RANK[fit], summary=summary, reason=reason, action=action, action_detail=action_detail,
            plan_kind=plan_kind, can_override_direct=fit in {"Strong", "Viable"}, source_reliability=source_reliability,
            strategic_depth=depth, safety_score=safety, team_setup_priority=setup_priority, incoming_worst_score=incoming_score,
            lead_pokemon_name=lead_name, lead_move=lead_move, opener_threat_move=threat_name, opener_threat_category=threat_category,
            opener_threat_type=threat_type, opener_threat_score=incoming_score if threat_name else 0.0, opener_threat_multiplier=threat_multiplier,
            strategy_branch=strategy_branch, assumed_poisoned=False, state_assumption=state_assumption,
            fallback_if_assumption_fails=fallback, recommended_pokemon_name=recommended_name,
            conditional_move_name=conditional_name, conditional_move_score=conditional_score,
        ))
    return results


def select_poison_attrition_plan(plans: list[PoisonAttritionPlanResult], matchup_results: list[dict]) -> PoisonAttritionPlanResult | None:
    """Choose the best safe strategic plan before considering direct offense."""
    candidates = [plan for plan in plans if plan.can_override_direct]
    if not candidates:
        return None
    ratio_lookup = {str(result.get("Pokemon")): float(result.get("Ratio") or 0.0) for result in matchup_results if isinstance(result, dict) and result.get("Pokemon")}
    return max(candidates, key=lambda plan: (
        plan.team_setup_priority, plan.fit_rank, plan.strategic_depth, plan.safety_score,
        -plan.incoming_worst_score, plan.source_reliability, ratio_lookup.get(plan.pokemon_name, 0.0),
    ))
