"""Strategic capability and Poison / Attrition plan recognition.

The strategy layer identifies reusable team tools and evaluates whether they
form a credible Poison / Attrition plan for the selected matchup. It does not
change Move Score, Ratio, or Full Analysis calculations.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.calculations import (
    calculate_damage_range,
    calculate_incoming_multiplier,
    calculate_move_score,
    get_moves,
    get_stat,
)
from engine.mechanics import get_item_speed_multiplier


CAPABILITY_LABELS: dict[str, str] = {
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
    "CORROSION": "Corrosion",
}

_CAPABILITY_ORDER = tuple(CAPABILITY_LABELS)
_POISON_IMMUNE_ABILITIES = {"immunity", "comatose", "pastel veil"}
_FIT_RANK = {"Blocked": 0, "Risky": 1, "Viable": 2, "Strong": 3}


@dataclass(frozen=True)
class StrategicCapabilityResult:
    """Recognized strategic tools for one saved team member."""

    pokemon_name: str
    capability_keys: tuple[str, ...]
    capabilities: tuple[str, ...]


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
    if move.get("ActivationCondition") != "TargetPoisoned":
        return False

    power = move.get("Power", 0)
    multiplier = move.get("ActivationPowerMultiplier", 1)
    return (
        isinstance(power, (int, float))
        and float(power) > 0
        and isinstance(multiplier, (int, float))
        and float(multiplier) > 1
    )


def recognize_pokemon_capabilities(
    pokemon: dict,
    move_lookup: dict[str, dict],
) -> StrategicCapabilityResult:
    """Recognize Poison / Attrition-relevant tools for one Pokémon."""

    capability_keys: set[str] = set()

    for move_name in _move_names(pokemon):
        move = move_lookup.get(move_name, {})
        tags = _mechanics_tags(move)

        if move_name == "Toxic":
            capability_keys.add("STATUS_POISON_RELIABLE")
        elif move_name == "Toxic Spikes":
            capability_keys.add("STATUS_POISON_TEAM_SETUP")
        elif move_name == "Baneful Bunker":
            capability_keys.add("STATUS_POISON_CONTACT")

        if _poison_exploit_damage(move):
            capability_keys.add("POISON_EXPLOIT_DAMAGE")
        if _negative_target_stage_control(move):
            capability_keys.add("POISON_EXPLOIT_CONTROL")
        if "RecoveryMove" in tags:
            capability_keys.add("RELIABLE_RECOVERY")
        if "HPStealingMove" in tags:
            capability_keys.add("DAMAGE_RECOVERY")
        if "Protection" in tags:
            capability_keys.add("PROTECTION")
        if "StatReset" in tags:
            capability_keys.add("SETUP_DENIAL")
        if "SpecialAttackSetup" in tags:
            capability_keys.add("SPECIAL_SETUP")

    ability = pokemon.get("Ability")
    if isinstance(ability, str) and ability.strip().casefold() == "corrosion":
        capability_keys.add("CORROSION")

    ordered_keys = tuple(key for key in _CAPABILITY_ORDER if key in capability_keys)
    return StrategicCapabilityResult(
        pokemon_name=str(pokemon.get("Pokemon") or "Unknown Pokémon"),
        capability_keys=ordered_keys,
        capabilities=tuple(CAPABILITY_LABELS[key] for key in ordered_keys),
    )


def recognize_team_capabilities(
    team_data: list[dict],
    moves_data: list[dict],
) -> list[StrategicCapabilityResult]:
    """Recognize strategic tools across the saved party in party order."""

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


def _strategic_depth(keys: set[str]) -> float:
    weights = {
        "RELIABLE_RECOVERY": 3.0,
        "DAMAGE_RECOVERY": 2.5,
        "PROTECTION": 2.0,
        "POISON_EXPLOIT_DAMAGE": 2.0,
        "POISON_EXPLOIT_CONTROL": 2.0,
        "SETUP_DENIAL": 1.5,
        "SPECIAL_SETUP": 0.5,
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


def _direct_poison_sources(
    team_data: list[dict],
    opponent: dict,
    move_lookup: dict[str, dict],
) -> list[tuple[str, int, str]]:
    """Return valid current-target poison sources as (name, reliability, method)."""

    contact_available = _opponent_has_contact_move(opponent, move_lookup)
    sources: list[tuple[str, int, str]] = []

    for pokemon in team_data:
        capability = recognize_pokemon_capabilities(pokemon, move_lookup)
        keys = set(capability.capability_keys)
        blocked = _poison_block_reason(opponent, "CORROSION" in keys)
        if blocked:
            continue

        if "STATUS_POISON_RELIABLE" in keys:
            sources.append((capability.pokemon_name, 2, "Toxic"))
        elif "STATUS_POISON_CONTACT" in keys and contact_available:
            sources.append((capability.pokemon_name, 1, "Baneful Bunker"))

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


def describe_poison_attrition_fallback(
    team_data: list[dict],
    opponent: dict,
    moves_data: list[dict],
    matchup_results: list[dict],
    items: list[dict] | None = None,
    ability_rules: list[dict] | None = None,
) -> str:
    """Explain why Poison / Attrition did not produce a safe recommendation."""

    if items is None:
        items = []
    if ability_rules is None:
        ability_rules = []

    move_lookup = {
        move["Move"]: move
        for move in moves_data
        if isinstance(move, dict)
        and isinstance(move.get("Move"), str)
        and move.get("Move")
    }
    pokemon_lookup = {
        str(pokemon.get("Pokemon") or ""): pokemon
        for pokemon in team_data
        if isinstance(pokemon, dict) and pokemon.get("Pokemon")
    }

    raw_sources = _direct_poison_sources(team_data, opponent, move_lookup)
    if raw_sources:
        safe_sources: list[str] = []
        unsafe_sources: list[tuple[str, str | None]] = []

        for source_name, _, source_method in raw_sources:
            pokemon = pokemon_lookup.get(source_name, {})
            keys = set(
                recognize_pokemon_capabilities(
                    pokemon,
                    move_lookup,
                ).capability_keys
            )
            safety, notes, _, threat_move, _ = _opener_safety_profile(
                pokemon,
                opponent,
                source_method,
                move_lookup,
                moves_data,
                items,
                ability_rules,
                keys,
            )

            if (
                safety >= 0
                and "Likely Incoming OHKO" not in notes
                and "Possible Incoming OHKO" not in notes
            ):
                safe_sources.append(source_name)
            else:
                threat_name = (
                    str(threat_move.get("Move"))
                    if threat_move is not None
                    else None
                )
                unsafe_sources.append((source_name, threat_name))

        if not safe_sources and unsafe_sources:
            source_names = ", ".join(name for name, _ in unsafe_sources)
            threat_names = {
                threat
                for _, threat in unsafe_sources
                if threat
            }
            target_name = str(opponent.get("Pokemon") or "this opponent")

            if len(threat_names) == 1:
                threat_name = next(iter(threat_names))
                return (
                    f"Poison can be established against {target_name}, but none of the "
                    f"available setters ({source_names}) can do so safely. {threat_name} "
                    "is the modeled response creating the setup disadvantage, so Battle "
                    "Compass is falling back to the strongest direct matchup."
                )

            return (
                f"Poison can be established against {target_name}, but none of the "
                f"available setters ({source_names}) meet the setup-safety threshold. "
                "Battle Compass is falling back to the strongest direct matchup."
            )

        if safe_sources:
            return (
                "Poison can be established safely, but no available follow-up produces "
                "a Strong or Viable attrition plan in this matchup, so Battle Compass "
                "is falling back to the strongest direct matchup."
            )

    return (
        "No Strong or Viable Poison / Attrition plan is available in this matchup, "
        "so Battle Compass is falling back to the strongest direct matchup."
    )


def evaluate_poison_attrition_plans(
    team_data: list[dict],
    opponent: dict,
    moves_data: list[dict],
    matchup_results: list[dict],
    battle_roster: list[dict] | None = None,
    items: list[dict] | None = None,
    ability_rules: list[dict] | None = None,
) -> list[PoisonAttritionPlanResult]:
    """Evaluate Poison / Attrition plans using team synergy and matchup safety."""

    move_lookup = {
        move["Move"]: move
        for move in moves_data
        if isinstance(move, dict)
        and isinstance(move.get("Move"), str)
        and move.get("Move")
    }
    matchup_lookup = {
        result.get("Pokemon"): result
        for result in matchup_results
        if isinstance(result, dict) and result.get("Pokemon")
    }
    if items is None:
        items = []
    if ability_rules is None:
        ability_rules = []

    raw_direct_sources = _direct_poison_sources(team_data, opponent, move_lookup)
    direct_sources = list(raw_direct_sources)

    pokemon_lookup = {
        str(pokemon.get("Pokemon") or ""): pokemon
        for pokemon in team_data
        if isinstance(pokemon, dict) and pokemon.get("Pokemon")
    }
    safe_direct_sources: list[tuple[str, int, str]] = []

    for source in direct_sources:
        source_name, _, source_method = source
        source_pokemon = pokemon_lookup.get(source_name, {})
        source_keys = set(
            recognize_pokemon_capabilities(source_pokemon, move_lookup).capability_keys
        )
        source_safety, source_notes, _, _, _ = _opener_safety_profile(
            source_pokemon,
            opponent,
            source_method,
            move_lookup,
            moves_data,
            items,
            ability_rules,
            source_keys,
        )

        if "Likely Incoming OHKO" in source_notes:
            continue
        if "Possible Incoming OHKO" in source_notes:
            continue
        if source_safety < 0:
            continue

        safe_direct_sources.append(source)

    direct_sources = safe_direct_sources
    team_source = max(direct_sources, key=lambda source: source[1], default=None)
    spikes_current_supported, spikes_targets, spikes_names, spikes_risks = _toxic_spikes_profile(
        opponent,
        battle_roster,
        move_lookup,
    )
    confirmed_lead = _is_confirmed_battle_lead(opponent)

    results: list[PoisonAttritionPlanResult] = []

    for pokemon in team_data:
        name = str(pokemon.get("Pokemon") or "Unknown Pokémon")
        matchup = matchup_lookup.get(name, {})
        capability = recognize_pokemon_capabilities(pokemon, move_lookup)
        keys = set(capability.capability_keys)
        effective_keys = _effective_strategy_keys(keys, opponent)
        notes = _note_texts(matchup)
        incoming_score = float(matchup.get("Incoming Worst Score") or 0.0)
        safety = _safety_score(matchup, effective_keys)
        depth = _strategic_depth(effective_keys)

        own_source = next((source for source in direct_sources if source[0] == name), None)
        source = own_source or team_source
        source_available = source is not None
        source_reliability = source[1] if source else 0
        team_setup_priority = 0
        plan_kind = "current_target"

        spikes_safety = safety
        spikes_notes = notes
        spikes_incoming_score = incoming_score
        if "STATUS_POISON_TEAM_SETUP" in keys:
            spikes_safety, spikes_notes, spikes_incoming_score, _, _ = _opener_safety_profile(
                pokemon,
                opponent,
                "Toxic Spikes",
                move_lookup,
                moves_data,
                items,
                ability_rules,
                effective_keys,
            )

        use_toxic_then_spikes = (
            confirmed_lead
            and spikes_targets > 0
            and _can_open_toxic_then_spikes(
                pokemon,
                opponent,
                move_lookup,
                moves_data,
                items,
                ability_rules,
                effective_keys,
            )
        )
        use_team_setup = (
            confirmed_lead
            and "STATUS_POISON_TEAM_SETUP" in keys
            and spikes_targets > 0
            and "Likely Incoming OHKO" not in spikes_notes
            and "Possible Incoming OHKO" not in spikes_notes
            and spikes_safety >= 0
        )

        if use_toxic_then_spikes:
            plan_kind = "lead_toxic_then_spikes"
            team_setup_priority = 4
            source_reliability = 3
            toxic_safety, toxic_notes, toxic_incoming_score, _, _ = (
                _opener_safety_profile(
                    pokemon,
                    opponent,
                    "Toxic",
                    move_lookup,
                    moves_data,
                    items,
                    ability_rules,
                    effective_keys,
                )
            )
            safety = toxic_safety
            notes = toxic_notes
            incoming_score = toxic_incoming_score
            fit = "Strong"

            target_text = ", ".join(spikes_names[:3])
            if spikes_targets > 3:
                target_text += f", and {spikes_targets - 3} more"

            summary = (
                "This lead can poison the active opponent first, then establish "
                "persistent Toxic Spikes pressure."
            )
            reason = (
                f"{name} is modeled to move first and survive the response to Toxic, "
                "so it can poison the current lead before using Toxic Spikes for the "
                f"{spikes_targets} modeled later target(s)."
            )
            if target_text:
                reason += f" Later poisonable targets include {target_text}."
            if spikes_risks:
                reason += " Risks: " + " ".join(spikes_risks)

            action = "Toxic → Toxic Spikes"
            action_detail = (
                f"Lead with {name} and use Toxic on the active opponent. If the first "
                "turn goes as modeled, use Toxic Spikes next to seed persistent poison "
                "pressure for later grounded opponents."
            )
            lead_pokemon_name = name
            lead_move = "Toxic"
        elif use_team_setup:
            plan_kind = "lead_team_setup"
            team_setup_priority = 3
            source_reliability = 3
            safety = spikes_safety
            notes = spikes_notes
            incoming_score = spikes_incoming_score
            fit = "Strong" if safety >= 0 else "Viable"

            target_text = ", ".join(spikes_names[:3])
            if spikes_targets > 3:
                target_text += f", and {spikes_targets - 3} more"

            summary = (
                "The confirmed battle lead creates a setup window for persistent "
                "Toxic Spikes pressure."
            )
            reason = (
                f"Toxic Spikes will not poison the Pokémon already on the field, but "
                f"this opening can seed poison pressure for {spikes_targets} modeled "
                "later target(s) without assuming their exact order."
            )
            if spikes_current_supported:
                reason += (
                    " The active opponent is also a valid Toxic Spikes target if it "
                    "returns later after switching out."
                )
            if target_text:
                reason += f" Later poisonable targets include {target_text}."
            if spikes_risks:
                reason += " Risks: " + " ".join(spikes_risks)

            action = "Toxic Spikes"
            action_detail = (
                "Set Toxic Spikes to prepare later switch-ins. The active opponent is "
                "not poisoned by placing the hazard, so handle the current matchup "
                "directly until a future opponent enters."
            )
            lead_pokemon_name = name
            lead_move = "Toxic Spikes"
        else:
            if own_source is not None:
                own_method = own_source[2]
                safety, notes, incoming_score, _, _ = _opener_safety_profile(
                    pokemon,
                    opponent,
                    own_method,
                    move_lookup,
                    moves_data,
                    items,
                    ability_rules,
                    effective_keys,
                )

            candidate_participates = own_source is not None or depth > 0
            fit = _fit_from_support(
                source_available=source_available and candidate_participates,
                source_reliability=source_reliability,
                keys=effective_keys,
                safety=safety,
                notes=notes,
            )

            if not candidate_participates:
                summary = "No meaningful Poison / Attrition role is available for this Pokémon."
                reason = "A teammate can establish poison, but this Pokémon has no modeled sustain, protection, poison exploitation, control, or denial tools to extend that plan."
                action = "Direct fallback"
                action_detail = "Treat this Pokémon as direct-damage coverage rather than part of the Poison / Attrition engine."
                lead_pokemon_name = name
                lead_move = ""
            elif not source_available:
                summary = "No current-target poison engine is available for this Pokémon."
                if "STATUS_POISON_TEAM_SETUP" in keys and not confirmed_lead:
                    reason = "Toxic Spikes are treated as a battle-opening plan because only the trainer's lead order is confirmed."
                elif "STATUS_POISON_TEAM_SETUP" in keys and not spikes_current_supported:
                    reason = "Toxic Spikes do not affect the selected lead because it is not a valid grounded Toxic Spikes target."
                elif "STATUS_POISON_TEAM_SETUP" in keys and spikes_targets == 0:
                    reason = "The confirmed lead offers no modeled remaining targets that make Toxic Spikes useful."
                elif keys.intersection({"POISON_EXPLOIT_DAMAGE", "POISON_EXPLOIT_CONTROL"}):
                    reason = "This Pokémon can exploit poison, but no teammate can reliably establish it against the selected opponent."
                else:
                    reason = "No meaningful Poison / Attrition route is available in this matchup."
                action = "Direct fallback"
                action_detail = "Use the normal matchup recommendation because the selected strategy cannot be established safely."
                lead_pokemon_name = name
                lead_move = ""
            else:
                assert source is not None
                provider_name, _, provider_method = source
                corrosion_callout = _corrosion_only_callout(
                    provider_name,
                    opponent,
                    pokemon_lookup,
                    raw_direct_sources,
                )
                has_sustain = bool(
                    effective_keys.intersection({"RELIABLE_RECOVERY", "DAMAGE_RECOVERY"})
                )
                has_exploit = "POISON_EXPLOIT_DAMAGE" in effective_keys
                has_control = "POISON_EXPLOIT_CONTROL" in effective_keys
                has_protection = "PROTECTION" in effective_keys

                if own_source:
                    summary = "This Pokémon can establish poison and support the selected strategy itself."
                    action = provider_method
                    action_detail = f"Use {provider_method} to establish poison."
                    lead_pokemon_name = name
                    lead_move = provider_method
                else:
                    summary = (
    f"{provider_name} can establish poison with {provider_method}, then "
    f"{name} can take over as the safer attrition anchor."
)
                    action = f"{provider_name}: {provider_method} → {name}"
                    action_detail = f"Have {provider_name} establish poison with {provider_method}, then pivot to {name} for the sustained matchup."
                    lead_pokemon_name = provider_name
                    lead_move = provider_method

                pieces: list[str] = []
                if has_sustain:
                    pieces.append("recovery")
                if has_exploit:
                    pieces.append("poison-boosted damage")
                if has_control:
                    pieces.append("poison-enabled control")
                if has_protection:
                    pieces.append("protected turns")
                if "SETUP_DENIAL" in effective_keys:
                    pieces.append("setup denial")

                if pieces:
                    reason = f"{name}'s matchup combines favorable strategic safety with " + ", ".join(pieces) + "."
                    action_detail += f" Then let {name} lean on " + ", ".join(pieces) + " while poison progresses."
                else:
                    reason = "Poison is available, but this Pokémon has limited tools for extending the attrition plan."

                if corrosion_callout:
                    reason = f"{corrosion_callout} {reason}"

                steel_direct_option = (
                    _safe_super_effective_direct_option(matchup_results)
                    if "Steel" in _pokemon_types(opponent)
                    else None
                )
                if "Steel" in _pokemon_types(opponent):
                    if not _can_damage_steel_target(matchup):
                        fit = "Risky"
                        reason = (
                            f"{name} cannot meaningfully damage this Steel target with its "
                            "modeled best attack, so it is not a suitable attrition anchor."
                        )
                    elif steel_direct_option is not None:
                        fit = "Risky"
                        direct_name = str(steel_direct_option.get("Pokemon") or "A teammate")
                        direct_move = str(
                            steel_direct_option.get("Best Move") or "a super-effective move"
                        )
                        reason = (
                            f"Corrosion can establish poison, but Steel remains immune to "
                            f"Poison-type attacks. {direct_name} has a safe super-effective "
                            f"direct option with {direct_move}, so the attrition route stays "
                            "secondary in this matchup."
                        )

                if fit == "Blocked":
                    if "Likely Incoming OHKO" in notes:
                        reason = "A modeled likely incoming OHKO makes the sustained plan unsafe."
                    else:
                        reason = "The selected strategy cannot be established in this matchup."
                elif fit == "Risky" and "Possible Incoming OHKO" in notes:
                    reason = "A modeled possible incoming OHKO makes the strategy a genuine safety gamble."

        lead_pokemon = pokemon_lookup.get(lead_pokemon_name, {})
        _, _, opener_threat_score, opener_threat_move, opener_threat_multiplier = (
            _opener_safety_profile(
                lead_pokemon,
                opponent,
                lead_move,
                move_lookup,
                moves_data,
                items,
                ability_rules,
                set(
                    recognize_pokemon_capabilities(
                        lead_pokemon,
                        move_lookup,
                    ).capability_keys
                ),
            )
        )

        results.append(
            PoisonAttritionPlanResult(
                pokemon_name=name,
                fit=fit,
                fit_rank=_FIT_RANK[fit],
                summary=summary,
                reason=reason,
                action=action,
                action_detail=action_detail,
                plan_kind=plan_kind,
                can_override_direct=fit in {"Strong", "Viable"},
                source_reliability=source_reliability,
                strategic_depth=depth,
                safety_score=safety,
                team_setup_priority=team_setup_priority,
                incoming_worst_score=incoming_score,
                lead_pokemon_name=lead_pokemon_name,
                lead_move=lead_move,
                opener_threat_move=(
                    str(opener_threat_move.get("Move"))
                    if opener_threat_move is not None
                    else None
                ),
                opener_threat_category=(
                    str(opener_threat_move.get("Category"))
                    if opener_threat_move is not None
                    else None
                ),
                opener_threat_type=(
                    str(opener_threat_move.get("Type"))
                    if opener_threat_move is not None
                    else None
                ),
                opener_threat_score=opener_threat_score,
                opener_threat_multiplier=opener_threat_multiplier,
            )
        )

    return results


def select_poison_attrition_plan(
    plans: list[PoisonAttritionPlanResult],
    matchup_results: list[dict],
) -> PoisonAttritionPlanResult | None:
    """Choose the best safe strategic plan before considering direct offense."""

    candidates = [plan for plan in plans if plan.can_override_direct]
    if not candidates:
        return None

    ratio_lookup = {
        str(result.get("Pokemon")): float(result.get("Ratio") or 0.0)
        for result in matchup_results
        if isinstance(result, dict) and result.get("Pokemon")
    }

    return max(
        candidates,
        key=lambda plan: (
            plan.team_setup_priority,
            plan.fit_rank,
            plan.safety_score,
            plan.strategic_depth,
            -plan.incoming_worst_score,
            plan.source_reliability,
            ratio_lookup.get(plan.pokemon_name, 0.0),
        ),
    )
