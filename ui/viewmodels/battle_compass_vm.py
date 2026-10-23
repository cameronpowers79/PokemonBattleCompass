"""Battle Compass view model.



Loads Battle Compass data, calls the existing battle engine, and converts



engine output into UI-friendly objects without depending on Streamlit.



"""
from __future__ import annotations
from dataclasses import dataclass, field, replace
from ui.pokemon_display import pokemon_display_name
from typing import TypedDict
from engine.calculations import (
    calculate_move_score, evaluate_team_matchups, find_best_team_member,
    get_moves, get_stat, get_deterministic_fixed_damage, resolve_move_for_matchup,
)
from engine.data_loader import load_json
from engine.strategy_capabilities import (
    describe_poison_attrition_fallback,
    evaluate_poison_attrition_plans,
    recognize_team_capabilities,
    select_poison_attrition_plan,
    project_poisoned_followup,
)
from ui.constants import NOTE_ICONS
from ui.viewmodels.recommendation_explanations import build_recommendation_why


class ReferenceData(TypedDict):
    """Bundled application reference datasets."""
    team_data: list[dict]
    opponents: list[dict]
    items: list[dict]
    item_validation: list[str]
    ability_rules: list[dict]
    abilities: list[str]
    ability_descriptions: list[dict]
    pokemon_validation: list[str]
    moves_data: list[dict]
    learnsets_swsh: dict
    type_chart: dict[str, dict[str, float]]
    evolutions: dict[str, dict]
@dataclass(frozen=True)


class BattleNoteViewModel:
    """Display-ready battle note."""
    icon: str
    text: str
    category: str
@dataclass(frozen=True)


class MatchupViewModel:
    """Display-ready matchup result for one team member."""
    pokemon: dict
    best_move: dict
    best_move_score: float
    best_move_type_multiplier: float
    best_move_multiplier: float
    base_move_score: float
    item_boosted: bool
    item_multiplier: float
    item_bonus_amount: float
    held_item: str | None
    worst_move: dict
    incoming_worst_score: float
    incoming_type_multiplier: float
    incoming_multiplier: float
    ratio: float
    is_immune: bool
    matchup_label: str
    matchup_level: int
    battle_notes: list[BattleNoteViewModel]
@dataclass(frozen=True)


class StrategyCapabilityViewModel:
    """Display-ready strategic capability summary for one team member."""
    pokemon_name: str
    capabilities: tuple[str, ...]
@dataclass(frozen=True)


class StrategyPlanViewModel:
    """Display-ready Poison / Attrition viability for one team member."""
    pokemon_name: str
    fit: str
    fit_rank: int
    summary: str
    reason: str
    action: str
    action_detail: str
    plan_kind: str
    can_override_direct: bool
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
    action_type: str = ""
    plan_role: str = ""
    fit_explanation: str = ""
    attack_move_score: float | None = None
    attack_score_conditional: bool = False
    sequence_heading: str = ""
    condition_detail: str = ""
    member_id: str | None = None
    setter_member_id: str | None = None
    payoff_member_id: str | None = None
    setup_followup_move: str | None = None
    setup_followup_type: str | None = None
    setup_followup_score: float | None = None
    setup_followup_base_score: float | None = None
    setup_followup_effectiveness: float | None = None
    setup_followup_likely_ohko: bool = False
    # Explanation evidence only; never changes strategy selection.
    continuation_same_direct: bool = False
    continuation_below_threshold: bool = False
    continuation_dig_shelter: bool = False
    weather_why_evidence: str = ""
@dataclass(frozen=True)


class BattleCompassViewModel:
    """Complete display model for one selected opponent."""
    opponent: dict
    recommendation: MatchupViewModel | None
    why_text: str
    other_options: list[MatchupViewModel]
    all_matchups: list[MatchupViewModel]
    empty_state_message: str | None = None
    team_strategy: str = "strongest_matchup"
    strategy_capabilities: list[StrategyCapabilityViewModel] = field(default_factory=list)
    strategy_plans: list[StrategyPlanViewModel] = field(default_factory=list)
    selected_strategy_plan: StrategyPlanViewModel | None = None
    strategy_fallback_reason: str | None = None
    direct_recommendation_name: str | None = None
    direct_fallback_move_name: str | None = None


def get_matchup_strength(ratio: float, is_immune: bool = False) -> tuple[str, int]:
    """Return the user-facing matchup label and active meter segment."""
    if is_immune:
        return "Immune", 4
    if ratio >= 3:
        return "Comfortable", 3
    if ratio >= 2:
        return "Favorable", 2
    if ratio >= 1:
        return "Competitive", 1
    return "Challenging", 0




def _force_strongest_matchup_for_known_doubles(opponent: dict) -> bool:
    """Return True for Hammerlocke Gym battles that are modeled as singles elsewhere."""
    trainer = str(opponent.get("Trainer") or "").strip()
    battle = str(opponent.get("Battle") or "").strip()
    if trainer in {"HT Sebastian", "HT Camilla", "HT Aria"} and battle == "Hammerlocke Gym":
        return True
    return trainer == "Raihan" and battle == "Gym 8"

def _opponent_is_dynamaxed(opponent: dict) -> bool:
    """Detect a modeled Dynamax/Gigantamax opponent from its Max Move set."""
    for slot in range(1, 5):
        move_name = opponent.get(f"Move{slot}")
        if not isinstance(move_name, str):
            continue
        if move_name.startswith("Max ") or move_name.startswith("G-Max "):
            return True
    return False


def _steel_direct_fallback_reason(
    opponent: dict,
    matchup_results: list[dict],
) -> str | None:
    """Explain why Steel matchups may favor direct offense over attrition."""
    opponent_types = {
        str(opponent.get("Type1") or ""),
        str(opponent.get("Type2") or ""),
    }
    if "Steel" not in opponent_types:
        return None
    candidates: list[dict] = []
    for result in matchup_results:
        if not isinstance(result, dict):
            continue
        multiplier = float(result.get("Best Move Type Multiplier") or 0.0)
        ratio = float(result.get("Ratio") or 0.0)
        notes = {
            note.get("text")
            for note in result.get("Battle Notes", [])
            if isinstance(note, dict)
        }
        if multiplier <= 1 or ratio < 1:
            continue
        if "Likely Incoming OHKO" in notes or "Possible Incoming OHKO" in notes:
            continue
        candidates.append(result)
    if not candidates:
        return None
    best = max(
        candidates,
        key=lambda result: (
            float(result.get("Ratio") or 0.0),
            float(result.get("Best MoveScore") or 0.0),
        ),
    )
    pokemon_name = str(best.get("Pokemon") or "A teammate")
    move_name = str(best.get("Best Move") or "a super-effective move")
    return (
        "Corrosion can establish poison against this Steel-type opponent, but Steel "
        "remains immune to Poison-type attacks. Because "
        f"{pokemon_name} has a safe super-effective direct option with {move_name}, "
        "Battle Compass is prioritizing direct offense for this matchup."
    )


def get_effectiveness_label(multiplier: float | None, *, mode: str) -> str:
    """Return the established player-facing effectiveness text."""
    if multiplier is None:
        return "Effectiveness unavailable"
    if mode == "offense":
        if multiplier == 0:
            return "🚫 No Effect (0×)"
        if multiplier < 1:
            return f"🟡 Not Very Effective ({multiplier:g}×)"
        if multiplier == 1:
            return "⚪ Neutral (1×)"
        if multiplier < 4:
            return f"🟢 Super Effective ({multiplier:g}×)"
        return "🔥 4× Effective"
    if multiplier == 0:
        return "🛡️ No Effect (0×)"
    if multiplier < 1:
        return f"🟢 Not Very Effective ({multiplier:g}×)"
    if multiplier == 1:
        return "⚪ Neutral (1×)"
    if multiplier < 4:
        return f"🔺 Super Effective ({multiplier:g}×)"
    return "🔥 4× Weakness"


def _build_move_lookup(moves_data: list[dict]) -> dict[str, dict]:
    return {move["Move"]: move for move in moves_data if move.get("Move")}


def _build_note_view_models(battle_notes: list[dict]) -> list[BattleNoteViewModel]:
    note_view_models: list[BattleNoteViewModel] = []
    for note in battle_notes:
        category_value = note.get("category")
        text_value = note.get("text")
        category = category_value if isinstance(category_value, str) else "info"
        text = text_value if isinstance(text_value, str) else ""
        note_view_models.append(
            BattleNoteViewModel(
                icon=NOTE_ICONS.get(category, "•"),
                text=text,
                category=category,
            )
        )
    return note_view_models


def _build_matchup_view_model(
    *,
    result: dict,
    pokemon: dict,
    move_lookup: dict[str, dict],
) -> MatchupViewModel:
    best_move_name = result["Best Move"]
    worst_move_name = result["Worst Incoming Move"]
    best_move = dict(move_lookup.get(best_move_name, {}))
    best_move["Move"] = best_move_name
    best_move["Type"] = result.get("Best Move Type")
    best_move["Category"] = result.get("Best Move Category")
    worst_move = dict(move_lookup.get(worst_move_name, {}))
    worst_move["Move"] = worst_move_name
    worst_move["Type"] = result.get("Worst Incoming Move Type")
    worst_move["Category"] = result.get("Worst Incoming Move Category")
    ratio = float(result["Ratio"])
    is_immune = bool(result.get("Is Immune", False))
    matchup_label, matchup_level = get_matchup_strength(ratio, is_immune)
    return MatchupViewModel(
        pokemon=pokemon,
        best_move=best_move,
        best_move_score=float(result["Best MoveScore"]),
        best_move_type_multiplier=float(
            result.get("Best Move Type Multiplier", result["Best Move Multiplier"])
        ),
        best_move_multiplier=float(result["Best Move Multiplier"]),
        base_move_score=float(result["Base MoveScore"]),
        item_boosted=bool(result["Item Boosted"]),
        item_multiplier=float(result["Item Multiplier"]),
        item_bonus_amount=float(result["Item Bonus Amount"]),
        held_item=result.get("Held Item"),
        worst_move=worst_move,
        incoming_worst_score=float(result["Incoming Worst Score"]),
        incoming_type_multiplier=float(
            result.get("Incoming Type Multiplier", result["Incoming Multiplier"])
        ),
        incoming_multiplier=float(result["Incoming Multiplier"]),
        ratio=ratio,
        is_immune=is_immune,
        matchup_label=matchup_label,
        matchup_level=matchup_level,
        battle_notes=_build_note_view_models(result.get("Battle Notes", [])),
    )


def _strategy_label(strategy: str) -> str:
    if strategy == "poison_offensive_pressure":
        return "Poison – Offensive Pressure"
    if strategy == "poison_attrition":
        return "Poison – Attrition"
    return "Strongest Matchup"


def _poison_safety_tradeoff_text(raw_plans: list, selected_plan) -> str | None:
    if selected_plan is None or selected_plan.strategy_branch != "poison_offensive_pressure" or selected_plan.conditional_move_score is None:
        return None
    candidates = [plan for plan in raw_plans if plan.can_override_direct and plan.conditional_move_score is not None]
    if not candidates:
        return None
    strongest = max(candidates, key=lambda plan: float(plan.conditional_move_score or 0.0))
    selected_score = float(selected_plan.conditional_move_score or 0.0)
    strongest_score = float(strongest.conditional_move_score or 0.0)
    if (strongest.member_id or strongest.pokemon_name) == (selected_plan.member_id or selected_plan.pokemon_name) or strongest_score <= selected_score:
        return None
    selected_iws = float(selected_plan.incoming_worst_score or 0.0)
    strongest_iws = float(strongest.incoming_worst_score or 0.0)
    if selected_iws >= strongest_iws:
        return None
    selected_move = selected_plan.conditional_move_name or selected_plan.lead_move or "its poison payoff"
    strongest_move = strongest.conditional_move_name or strongest.lead_move or "its poison payoff"
    return (
        f"{strongest.pokemon_name} has the higher conditional offensive ceiling with {strongest_move} ({strongest_score:.2f}), "
        f"but {selected_plan.pokemon_name} is the safer modeled follow-up: Incoming Worst Score {selected_iws:.2f} versus {strongest_iws:.2f}. "
        f"The Compass is accepting some offensive loss and recommends {selected_plan.pokemon_name} with {selected_move} to reduce incoming danger."
    )


def _screened_worst_incoming(opponent, defender, screen, moves_data, items, ability_rules):
    """Re-rank incoming Move Scores under one assumed active screen (singles).

    Direct Matchup continues to use the unscreened scores. Screen effects are
    conditional and do not apply to fixed damage, screen-breaking attacks,
    attacks from Infiltrator, or critical hits (which aren't simulated).
    """
    protected_category = {"Reflect": "Physical", "Light Screen": "Special"}.get(screen)
    if protected_category is None:
        return None

    infiltrator = str(opponent.get("Ability") or "").strip().casefold() == "infiltrator"
    screen_breakers = {"Brick Break", "Psychic Fangs"}
    scored = []
    for move in get_moves(opponent, moves_data):
        resolved = resolve_move_for_matchup(opponent, defender, move)
        score = calculate_move_score(opponent, defender, move, items, ability_rules)
        covered = (
            resolved.get("Category") == protected_category
            and get_deterministic_fixed_damage(opponent, resolved) is None
            and not infiltrator
            and str(resolved.get("Move") or "") not in screen_breakers
        )
        if covered:
            score *= 0.5
        scored.append((str(resolved.get("Move") or "Unknown move"), score))
    return max(scored, key=lambda item: item[1]) if scored else None


def _matchup_index(matchups: list[dict]) -> dict[str, dict]:
    indexed = {}
    for row in matchups:
        member_id = row.get("MemberID")
        if member_id:
            indexed[str(member_id)] = row
        indexed.setdefault(str(row.get("Pokemon") or ""), row)
    return indexed


def _offensive_payoff_key(member, opponent, move, items, ability_rules, *, incoming=None):
    """Shared OHKO-first ordering for conditional offensive plans.

    Use the same 110%-of-target-HP minimum-damage confidence and first-turn
    safety that drive Strongest Matchup's OHKO promotion. Move Score is only a
    secondary metric; it is not damage in HP.
    """
    from engine.calculations import calculate_damage_range, OHKO_RECOMMENDATION_CONFIDENCE
    if not move:
        return (0, 0.0, 0.0)
    low, _ = calculate_damage_range(member, opponent, move, items, ability_rules)
    target_hp = float(get_stat(opponent, "HP") or 0)
    speed = float(get_stat(member, "SPE"))
    from engine.mechanics import get_item_speed_multiplier
    speed *= get_item_speed_multiplier(member, items)
    opponent_speed = float(get_stat(opponent, "SPE")) * get_item_speed_multiplier(opponent, items)
    priority = float(move.get("Priority") or 0)
    can_strike_first = priority > 0 or (priority == 0 and speed >= opponent_speed)
    no_incoming = incoming is not None and incoming <= 0
    confidence = float(low or 0) / target_hp if target_hp else 0.0
    promoted = bool((can_strike_first or no_incoming) and
                    confidence >= OHKO_RECOMMENDATION_CONFIDENCE)
    return (int(promoted), confidence if promoted else 0.0,
            float(calculate_move_score(member, opponent, move, items, ability_rules)))


def _screen_damage_max(opponent, setter, move, active_screens, items, ability_rules):
    """Worst modeled HP damage after specified screens (not an IWS)."""
    from engine.calculations import calculate_damage_range
    resolved = resolve_move_for_matchup(opponent, setter, move)
    low, high = calculate_damage_range(opponent, setter, move, items, ability_rules)
    if high is None:
        return None
    breaker = str(resolved.get("Move") or "") in {"Brick Break", "Psychic Fangs"}
    infiltrator = str(opponent.get("Ability") or "").casefold() == "infiltrator"
    if not breaker and not infiltrator and get_deterministic_fixed_damage(opponent, resolved) is None:
        category = resolved.get("Category")
        if (category == "Physical" and "Reflect" in active_screens or
                category == "Special" and "Light Screen" in active_screens):
            high = float(high) / 2
    return float(high)


def _screen_two_turn_survival(setter, opponent, first_screen, moves_data, items, ability_rules):
    """A conservative two-turn HP budget: initial hit + screened hit.

    The screen can be cast before the first hit only if the user moves first;
    priority and the opponent's priority are considered. No assumed healing.
    """
    moves = [m for m in get_moves(opponent, moves_data)
             if m.get("Category") in {"Physical", "Special"}]
    if not moves:
        return False
    from engine.mechanics import get_item_speed_multiplier
    own_speed = float(get_stat(setter, "SPE")) * get_item_speed_multiplier(setter, items)
    enemy_speed = float(get_stat(opponent, "SPE")) * get_item_speed_multiplier(opponent, items)
    screen_priority = 1 if str(setter.get("Ability") or "").casefold() == "prankster" else 0
    first = []
    second = []
    for move in moves:
        enemy_priority = float(move.get("Priority") or 0)
        casts_first = screen_priority > enemy_priority or (screen_priority == enemy_priority and own_speed >= enemy_speed)
        first_hit = _screen_damage_max(opponent, setter, move,
                                        {first_screen} if casts_first else set(), items, ability_rules)
        second_hit = _screen_damage_max(opponent, setter, move, {first_screen}, items, ability_rules)
        if first_hit is None or second_hit is None:
            return False
        first.append(first_hit)
        second.append(second_hit)
    hp = float(get_stat(setter, "HP"))
    return bool(hp > 0 and max(first) + max(second) < hp * 0.90)


def _remaining_opponents(opponent, roster):
    """Only known later members of this battle, never subsequent encounters."""
    if not roster:
        return []
    try:
        current_slot = int(opponent.get("Slot") or 0)
    except (TypeError, ValueError):
        return []
    return [other for other in roster if other is not opponent
            and str(other.get("Trainer") or "") == str(opponent.get("Trainer") or "")
            and str(other.get("Battle") or "") == str(opponent.get("Battle") or "")
            and str(other.get("Slot") or "").isdigit()
            and int(other["Slot"]) > current_slot and not _opponent_is_dynamaxed(other)]


def _other_battle_opponents(opponent, roster):
    """Other modeled members of this battle, independent of switch order."""
    if not roster:
        return []
    current_slot = str(opponent.get("Slot") or "")
    return [other for other in roster
            if other is not opponent
            and str(other.get("Trainer") or "") == str(opponent.get("Trainer") or "")
            and str(other.get("Battle") or "") == str(opponent.get("Battle") or "")
            and str(other.get("Slot") or "") != current_slot
            and not _opponent_is_dynamaxed(other)]


def _screen_damaging_moves(opponent, moves_data):
    """Moves that can directly damage the defender; status doesn't dilute coverage."""
    return [move for move in get_moves(opponent, moves_data)
            if move.get("Category") in {"Physical", "Special"}
            and (float(move.get("Power") or 0) > 0 or move.get("DamageMethod") == "Fixed")]


def _screen_order(setter, opponent, available, moves_data, items, ability_rules):
    """Prefer coverage among damaging moves, then modeled mitigated threat.

    This is *coverage*, not a probability claim about AI decisions. Compare
    against the known move categories and retain worst-hit magnitude as tie-break.
    """
    damaging = _screen_damaging_moves(opponent, moves_data)
    from engine.mechanics import get_item_speed_multiplier
    our_speed = float(get_stat(setter, "SPE")) * get_item_speed_multiplier(setter, items)
    foe_speed = float(get_stat(opponent, "SPE")) * get_item_speed_multiplier(opponent, items)
    our_priority = 1 if str(setter.get("Ability") or "").casefold() == "prankster" else 0
    rankings = []
    for screen in available:
        category = "Special" if screen == "Light Screen" else "Physical"
        coverage = sum(move.get("Category") == category for move in damaging)
        actual_coverage = 0.0
        peak = 0.0
        for move in damaging:
            enemy_priority = float(move.get("Priority") or 0)
            acts_first = (our_priority > enemy_priority or
                          our_priority == enemy_priority and our_speed >= foe_speed)
            unshielded = _screen_damage_max(opponent, setter, move, set(), items, ability_rules)
            shielded = _screen_damage_max(opponent, setter, move, {screen} if acts_first else set(), items, ability_rules)
            if unshielded is None or shielded is None:
                continue
            actual_coverage += max(0.0, unshielded - shielded)
            peak = max(peak, unshielded)
        # Exposure to a category is dominant; actual prevention breaks ties.
        rankings.append((coverage, actual_coverage, peak, screen))
    return max(rankings)[3] if rankings else None


def _screen_coverage_names(opponent, battle_roster, screen, moves_data):
    """Name known current/future opponents whose damaging moves the screen covers."""
    category = "Special" if screen == "Light Screen" else "Physical"
    names = []
    for target in [opponent, *_remaining_opponents(opponent, battle_roster)]:
        if any(move.get("Category") == category
               for move in _screen_damaging_moves(target, moves_data)):
            name = str(target.get("Pokemon") or "").strip()
            if name and name not in names:
                names.append(name)
    return names


def _screen_name_list(names):
    if len(names) <= 1:
        return names[0] if names else "the opposing lineup"
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def _screen_control_battle_plan(team_data, opponent, matchups, moves_data, items, ability_rules, battle_roster=None):
    """Conservative single-opponent screen sequence, using only equipped moves.

    Returns a selected tactical plan and its target recommendation, or a reason
    to keep Strongest Matchup. No persistent battle-state assumptions are stored.
    """
    lookup = _build_move_lookup(moves_data)
    by_name = _matchup_index(matchups)
    damaging = _screen_damaging_moves(opponent, moves_data)
    physical = any(m.get("Category") == "Physical" for m in damaging)
    special = any(m.get("Category") == "Special" for m in damaging)
    if not physical and not special:
        return None, None, "The opponent's damaging move category is not modeled; screen selection cannot be justified safely."

    candidates = []
    for mon in team_data:
        name = str(mon.get("Pokemon") or "")
        result = by_name.get(mon.get("MemberID")) or by_name.get(name)
        if not result:
            continue
        equipped = {str(mon.get(f"Move{i}") or "") for i in range(1, 5)}
        options = (["Reflect"] if physical and "Reflect" in equipped else []) + (["Light Screen"] if special and "Light Screen" in equipped else [])
        if not options and "Aurora Veil" in equipped:
            # Aurora Veil requires hail already active; weather is not modeled here.
            continue
        if not options:
            continue
        notes = {str(n.get("text") or "") for n in result.get("Battle Notes", []) if isinstance(n, dict)}
        if {"Likely Incoming OHKO", "Possible Incoming OHKO"} & notes:
            continue
        selected = _screen_order(mon, opponent, options, moves_data, items, ability_rules)
        if selected is None:
            continue
        ability = str(mon.get("Ability") or "").casefold()
        priority = ability == "prankster"
        speed = float(mon.get("SPE") or 0)
        safety = float(result.get("Ratio") or 0)
        candidates.append((int(priority), safety, speed, name, selected, result, options))

    if not candidates:
        return None, None, "No equipped screen setter has a supported safe opening against this opponent; use the strongest direct matchup."
    candidates.sort(key=lambda c: (c[0], c[1], c[2]), reverse=True)
    priority, safety, speed, setter, screen, result, options = candidates[0]
    setter_id = result.get("MemberID")
    setter_member = next((m for m in team_data if m.get("MemberID") == setter_id), None)
    if setter_member is not None:
        setter = pokemon_display_name(setter_member)
    # Both screens must be equipped. The current target dictates the first
    # screen; later known opponents can make the other screen worth the turn.
    second_screen = None
    if setter_member is not None and {"Reflect", "Light Screen"}.issubset(set(
            str(setter_member.get(f"Move{i}") or "") for i in range(1, 5))):
        other_screen = "Light Screen" if screen == "Reflect" else "Reflect"
        later = _remaining_opponents(opponent, battle_roster)
        other_category = "Special" if other_screen == "Light Screen" else "Physical"
        other_relevant = any(str(m.get("Category") or "") == other_category
                             for future in [opponent, *later]
                             for m in _screen_damaging_moves(future, moves_data))
        if other_relevant and _screen_two_turn_survival(
                setter_member, opponent, screen, moves_data, items, ability_rules):
            second_screen = other_screen
    threat = str(result.get("Worst Incoming Move") or "the opponent's strongest modeled move")
    threat_category = str(result.get("Worst Incoming Move Category") or "")
    delivered = "Prankster priority" if priority else "its modeled survivability"
    slot = opponent.get("Slot")
    is_lead = str(slot) in {"1", "1.0"}

    # Re-evaluate ONLY the follow-up options with delayed attacks removed. Future
    # Sight is useful strategically, but its delayed hit is not an immediate payoff.
    # Preserve the original matchup results for the UI and Strongest Matchup.
    delayed = {"Future Sight", "Doom Desire"}
    immediate_team = []
    for original in team_data:
        member = dict(original)
        for i in range(1, 5):
            if str(member.get(f"Move{i}") or "") in delayed:
                member[f"Move{i}"] = ""
        immediate_team.append(member)
    immediate_matchups = evaluate_team_matchups(
        immediate_team, opponent, items, ability_rules, moves_data
    )
    # Follow-up selection shares Strongest Matchup's OHKO promotion: select
    # from *other individuals* first, not by defensive Ratio alone.
    attackers = [r for r in immediate_matchups
                 if r.get("MemberID") != result.get("MemberID")
                 and str(r.get("Best Move") or "") not in delayed
                 and float(r.get("Best MoveScore") or 0) > 0]
    attacker_ids = {r.get("MemberID") for r in attackers}
    direct_pool = [m for m in immediate_team if m.get("MemberID") in attacker_ids]
    chosen, _, _ = find_best_team_member(direct_pool, opponent, items, ability_rules, moves_data)
    payoff = next((r for r in attackers if chosen is not None and
                   r.get("MemberID") == chosen.get("MemberID")), None)
    payoff_member = next((m for m in team_data if payoff is not None and
                          m.get("MemberID") == payoff.get("MemberID")), None)
    payoff_name = pokemon_display_name(payoff_member) if payoff_member else (str(payoff.get("Pokemon") or "") if payoff else "")
    payoff_move = str(payoff.get("Best Move") or "") if payoff else ""
    first_targets = _screen_coverage_names(opponent, battle_roster, screen, moves_data)
    second_targets = (_screen_coverage_names(opponent, battle_roster, second_screen, moves_data)
                      if second_screen else [])
    primary_purpose = (f"{screen} covers {_screen_name_list(first_targets)}'s "
                       f"{'special' if screen == 'Light Screen' else 'physical'} attacks.")
    second_purpose = (f" {second_screen} covers {_screen_name_list(second_targets)}'s "
                      f"{'special' if second_screen == 'Light Screen' else 'physical'} attacks."
                      if second_screen else "")
    if is_lead or not payoff:
        action_name = setter
        selected_move = screen
        plan_kind = "screen_setup"
        action = f"Establish {screen} with {setter}"
        assumed = False
        assumption = "Neither screen is assumed active at entry."
    else:
        action_name = payoff_name
        selected_move = payoff_move
        plan_kind = "screen_followup_assumed"
        action = f"Follow up with {payoff_name} using {payoff_move}"
        assumed = True
        assumption = (f"Conditional protection: {screen} may already be active; "
                      "the Compass cannot verify screen state. The attacking choice is evaluated without it.")
    if plan_kind == "screen_followup_assumed" and payoff:
        # Recompute the incoming threat for this *attacker*, not the setter.
        # This is an illustrative conditional defense calculation: we neither
        # infer an active screen nor alter the outgoing attack/Full Analysis.
        screened = (_screened_worst_incoming(
            opponent, payoff_member, screen, moves_data, items, ability_rules
        ) if payoff_member is not None else None)
        unscreened_score = float(payoff.get("Incoming Worst Score") or 0)
        unscreened_move = str(payoff.get("Worst Incoming Move") or "")
        if screened is not None:
            screened_move, screened_score = screened
            threat_change = (
                f"If {screen} remains active, projected Incoming Worst Score "
                f"for {payoff_name}: {unscreened_score:.2f} without it → "
                f"{screened_score:.2f} with it"
                + (f"; worst modeled move becomes {screened_move}"
                   if screened_move and screened_move != unscreened_move else "")
                + ". "
            )
        else:
            threat_change = ""
        # Later opponents are offensive follow-ups, not fresh screen-setting
        # opportunities. Screen state is unknown; never repeat setter steps.
        detail = (f"{payoff_name} is the preferred attacker against "
                  f"{opponent.get('Pokemon', 'this opponent')} with {payoff_move}. "
                  + threat_change
                  + (f"{screen} can reduce relevant "
                     f"{'physical' if screen == 'Reflect' else 'special'} attacks, "
                     "but the Compass cannot verify that it is active. "
                     "If it has expired, consider renewing it when safe."))
    elif second_screen:
        detail = (f"{primary_purpose}{second_purpose} "
                  f"{setter} is projected to survive both setup turns in that order, "
                  f"provided the first screen takes effect before the attacks it protects against. "
                  f"Then switch to {payoff_name} and use {payoff_move}." if payoff else
                  f"{primary_purpose}{second_purpose} {setter} is projected to survive both setup turns "
                  "in that order; choose an attacker afterward.")
        action += f" (then {second_screen} if safe)"
    else:
        detail = (f"{primary_purpose} {setter} has a supported safe opening against {threat}. "
                  + (f"Then switch to {payoff_name} and use {payoff_move}." if payoff
                     else "No reliable immediate attacking follow-up was identified."))
    # These are *tactical* grades, distinct from the direct-matchup meter.
    # A safe screen opener with priority and a useful follow-up earns Strong;
    # uncertain post-setup survival/exit earns Viable or Risky.
    setter_ratio = float(result.get("Ratio") or 0)
    incoming_notes = {str(n.get("text") or "") for n in result.get("Battle Notes", []) if isinstance(n, dict)}
    strong_payoff = bool(payoff and float(payoff.get("Ratio") or 0) >= 2)
    if plan_kind == "screen_followup_assumed" and payoff:
        attacker_ratio = float(payoff.get("Ratio") or 0)
        attacker_notes = {str(n.get("text") or "") for n in payoff.get("Battle Notes", []) if isinstance(n, dict)}
        threatened = bool({"Likely Incoming OHKO", "Possible Incoming OHKO"} & attacker_notes)
        # An attacker promoted for a guaranteed-range first-strike OHKO does
        # not need to tank the opponent's hypothetical retaliatory move.
        best_move = lookup.get(payoff_move)
        offensive_key = (_offensive_payoff_key(payoff_member, opponent, best_move,
                         items, ability_rules, incoming=float(payoff.get("Incoming Worst Score") or 0))
                         if payoff_member is not None else (0, 0, 0))
        if offensive_key[0]:
            fit, rank = "Strong", 3
        elif threatened:
            fit, rank = "Risky", 1
        elif attacker_ratio >= 3:
            fit, rank = "Strong", 3
        elif attacker_ratio >= 1.5:
            fit, rank = "Viable", 2
        else:
            fit, rank = "Risky", 1
    elif setter_ratio < 1 and not priority:
        fit, rank = "Risky", 1
    elif strong_payoff and (priority or setter_ratio >= 2):
        fit, rank = "Strong", 3
    else:
        fit, rank = "Viable", 2
    action_id = (setter_id if plan_kind == "screen_setup" else
                 payoff.get("MemberID") if payoff else None)
    chosen_member = next((m for m in team_data if m.get("MemberID") == action_id), {})
    chosen_moves = {str(chosen_member.get(f"Move{i}") or "") for i in range(1, 5)}
    pivot = next((m for m in ("U-turn", "Volt Switch", "Parting Shot", "Flip Turn", "Baton Pass") if m in chosen_moves), None)
    contingency = f"{pivot} offers a pivot option, subject to surviving until it acts." if pivot else "An ordinary switch to the protected attacker is the modeled exit."
    if plan_kind == "screen_followup_assumed" and payoff:
        # A screen cannot increase Power Gem or any other attack's damage.
        # Explain when it changes *survivability*, rather than implying that
        # the offensive choice requires the screen to be present.
        from engine.calculations import calculate_damage_range
        covered_category = "Physical" if screen == "Reflect" else "Special"
        enemy_moves = _screen_damaging_moves(opponent, moves_data)
        unscreened_max = []
        screened_max = []
        if payoff_member is not None:
            for enemy_move in enemy_moves:
                plain = _screen_damage_max(opponent, payoff_member, enemy_move,
                                           set(), items, ability_rules)
                screened_hit = _screen_damage_max(opponent, payoff_member, enemy_move,
                                                  {screen}, items, ability_rules)
                if plain is not None and screened_hit is not None:
                    unscreened_max.append(plain)
                    screened_max.append(screened_hit)
        hp = float(get_stat(payoff_member, "HP")) if payoff_member else 0.0
        screen_rescues = bool(unscreened_max and hp > 0 and
                              max(unscreened_max) >= hp and max(screened_max) < hp)
        # Keep Strategic Fit scannable. The full conditional discussion and
        # screen-specific threat details remain in Why this Pokémon.
        if screened is not None:
            _, screened_score = screened
            threat_brief = (f"{screen} (if active): Incoming Worst Score "
                            f"{unscreened_score:.2f} → {screened_score:.2f}.")
        else:
            threat_brief = f"{screen} offers conditional protection."
        if screen_rescues:
            explanation = f"Screen may prevent a modeled KO. {threat_brief}"
        else:
            explanation = f"Direct attacker. {threat_brief}"
    else:
        explanation = (f"{'Prankster priority' if priority else 'Modeled survival'} supports {screen}. "
                       + (f"{payoff_name} offers a favorable follow-up. " if strong_payoff else "Follow-up is less secure. ")
                       + (f"Exit: {pivot}." if pivot else "Exit: switch to the attacker."))
    return dict(
        member_id=action_id, setter_member_id=setter_id, payoff_member_id=payoff.get("MemberID") if payoff else None,
        action_type="Screen Setup" if plan_kind == "screen_setup" else "Screen Payoff",
        condition_detail=(f"{screen} provides conditional protection if still active; "
                          "the offensive recommendation itself does not assume a screen."
                          if assumed else ""),
        plan_role="Screen Setter" if plan_kind == "screen_setup" else "Protected Attacker",
        fit_explanation=explanation,
        attack_move_score=float(payoff.get("Best MoveScore") or 0) if plan_kind == "screen_followup_assumed" and payoff else None,
        sequence_heading=(f"{payoff_name} → {payoff_move}"
                          if plan_kind == "screen_followup_assumed" and payoff else
                          f"{setter} → {screen}" + (f" → {second_screen}" if second_screen else "")
                          + (f" → {payoff_name}" if payoff_name else "")),
        pokemon_name=action_name, recommended_pokemon_name=action_name,
        lead_pokemon_name=setter, lead_move=selected_move,
        fit=fit, fit_rank=rank, summary=action, reason=detail,
        action=action, action_detail=detail, plan_kind=plan_kind,
        can_override_direct=True,
        opener_threat_move=threat, opener_threat_category=threat_category or None,
        opener_threat_type=str(result.get("Worst Incoming Move Type") or "") or None,
        opener_threat_score=float(result.get("Incoming Worst Score") or 0),
        opener_threat_multiplier=float(result.get("Incoming Multiplier") or 1),
        strategy_branch="screen_control", assumed_poisoned=False,
        state_assumption=assumption, fallback_if_assumption_fails=(
            "If the screen has expired, reassess protection; the attacker is still selected on unscreened offense."
            if assumed else "If the setter is already damaged or unsafe, use Strongest Matchup instead."
        ),
    ), action_id or action_name, None


# Status Control & Punish: each opposing Pokémon starts without an assumed status.
# A later payoff is shown as a conditional *option*, not a status carried over
# from the preceding opposing Pokémon.
_STATUS_MOVES = {
    "Will-O-Wisp": "burn", "Thunder Wave": "paralysis",
    "Glare": "paralysis", "Stun Spore": "paralysis",
    "Toxic": "poison", "Poison Gas": "poison",
    "Hypnosis": "sleep", "Sleep Powder": "sleep", "Spore": "sleep",
    
}


def _status_applicable(opponent: dict, move_name: str, status: str) -> bool:
    """Conservative checks for known immunities; unknown interactions fall back."""
    types = {str(opponent.get("Type1") or ""), str(opponent.get("Type2") or "")}
    ability = str(opponent.get("Ability") or "").casefold().strip()
    if ability in {"magic bounce", "good as gold", "comatose", "purifying salt"}:
        return False
    if status == "burn" and ("Fire" in types or ability in {"water veil", "water bubble"}):
        return False
    if status == "paralysis" and ("Electric" in types or ability in {"limber"}):
        return False
    if move_name == "Thunder Wave" and "Ground" in types:
        return False
    if status == "poison" and ("Poison" in types or "Steel" in types or ability in {"immunity", "pastel veil"}):
        return False
    if status == "sleep" and ability in {"insomnia", "vital spirit", "sweet veil"}:
        return False
    if move_name in {"Sleep Powder", "Stun Spore", "Spore"} and (
        "Grass" in types or ability in {"overcoat", "sap sipper"}
    ):
        return False
    return True


def _status_payoff(team_data, opponent, moves_data, items, ability_rules, status=None):
    """Highest real Move Score payoff compatible with the *proposed* status.

    Hex works for any major status; Venoshock only when poisoned. The caller
    must never project a poison-only payoff from burn or paralysis.
    """
    options = []
    for member in team_data:
        for move in get_moves(member, moves_data):
            condition = str(move.get("ActivationCondition") or "")
            if condition != "TargetAnyStatus" and not (
                condition == "TargetPoisoned" and status in (None, "poison")
            ):
                continue
            if str(move.get("Category") or "") not in {"Special", "Physical"}:
                continue
            multiplier = float(move.get("ActivationPowerMultiplier") or 1)
            if multiplier <= 1:
                continue
            normal = float(calculate_move_score(member, opponent, move, items, ability_rules))
            boosted_move = dict(move, Power=float(move.get("Power") or 0) * multiplier)
            boosted = float(calculate_move_score(member, opponent, boosted_move, items, ability_rules))
            if boosted > 0:
                options.append((boosted, normal, member, str(move.get("Move") or "")))
    return max(options, key=lambda row: row[0]) if options else None


def _status_speed_analysis(setter, opponent, status, items):
    """Compare actual equipped Speed against modeled opposing Speed.

    Only deterministic entry weather is assumed; manually-set rain and
    weather changes during the fight remain unmodeled. Paralysis halves
    effective Speed in Gen VIII. Do not claim a flip if weather is uncertain.
    """
    from engine.mechanics import get_item_speed_multiplier, get_guaranteed_weather
    own = float(setter.get("SPE") or 0) * float(get_item_speed_multiplier(setter, items))
    enemy = float(get_stat(opponent, "SPE")) * float(get_item_speed_multiplier(opponent, items))
    weather = get_guaranteed_weather(setter, opponent)
    ability = str(opponent.get("Ability") or "").casefold()
    weather_speed_abilities = {
        "swift swim": "Rain", "chlorophyll": "Sun",
        "sand rush": "Sandstorm", "slush rush": "Hail",
    }
    required_weather = weather_speed_abilities.get(ability)
    if required_weather and weather == required_weather:
        enemy *= 2
    uncertain = bool(required_weather and weather is None)
    if own <= 0 or enemy <= 0 or status != "paralysis":
        return 0, ""
    after = enemy * 0.5
    flip = own <= enemy and own > after
    if uncertain:
        return 0, (f"Paralysis can reduce {opponent.get('Pokemon', 'the target')}'s Speed, but "
                   f"{opponent.get('Ability')} may alter turn order if its weather is active; "
                   "no guaranteed Speed flip is credited. ")
    if flip:
        return 1, (f"Paralysis flips turn order: {setter.get('Pokemon')} Speed {own:.0f} "
                   f"versus opponent {enemy:.0f} before, {after:.0f} afterward. ")
    return 0, (f"Paralysis lowers modeled opponent Speed {enemy:.0f} → {after:.0f}; "
               f"{setter.get('Pokemon')}'s Speed is {own:.0f}, so no turn-order flip is projected. ")


def _status_control_battle_plan(team_data, opponent, matchups, moves_data, items, ability_rules):
    """Plan setup against THIS target; never infer persistent status from its slot.

    The Compass has no battle-state feedback, so it cannot assert a target is
    already burned, poisoned, etc. Setup is the actionable first step; an
    amplified attack is a *projected* follow-up, possibly from another member.
    """
    lookup = _matchup_index(matchups)
    # Evaluate each setter’s own payoff, rather than giving the team’s globally
    # highest Hex user automatic priority as the setter.
    candidates = []
    opponent_moves = get_moves(opponent, moves_data)
    physical_threat = any(m.get("Category") == "Physical" and float(m.get("Power") or 0) > 0
                          for m in opponent_moves)
    for member in team_data:
        name = str(member.get("Pokemon") or "")
        result = lookup.get(member.get("MemberID")) or lookup.get(name)
        if result is None:
            continue
        notes = {str(n.get("text") or "") for n in result.get("Battle Notes", []) if isinstance(n, dict)}
        if {"Likely Incoming OHKO", "Possible Incoming OHKO"} & notes:
            continue
        for move in get_moves(member, moves_data):
            move_name = str(move.get("Move") or "")
            status = _STATUS_MOVES.get(move_name)
            if not status or not _status_applicable(opponent, move_name, status):
                continue
            accuracy = float(move.get("Accuracy") or 0)
            if accuracy <= 0:
                accuracy = 100 if move_name in {"Glare", "Spore"} else 0
            if accuracy < 70:
                continue
            priority = str(member.get("Ability") or "").casefold() == "prankster"
            if priority and "Dark" in {opponent.get("Type1"), opponent.get("Type2")}:
                continue
            ratio = float(result.get("Ratio") or 0)
            if ratio < 0.75 and not priority:
                continue
            # Status control retains value even when Hex cannot affect this target.
            # Burn is especially helpful versus physical threats, independently
            # of any projected status-amplified attack.
            speed_flip, speed_note = _status_speed_analysis(member, opponent, status, items)
            control_value = (3 if status == "burn" and physical_threat else
                             2 if status == "paralysis" else 1)
            pivot = any(member.get(f"Move{i}") in {"U-turn", "Volt Switch", "Parting Shot", "Flip Turn"}
                        for i in range(1, 5))
            own_payoff = _status_payoff([member], opponent, moves_data, items, ability_rules, status)
            team_payoff = _status_payoff(team_data, opponent, moves_data, items, ability_rules, status)
            # The original lexicographic tuple prioritized self-contained Hex
            # above *any* defensive or offensive advantage. That could select a
            # frail, poor-matchup setter over an excellent status setter with a
            # much safer alternate attack. The direct ratio is a useful safety
            # and contingency signal, but status control still adds value.
            # Cap extreme ratios so an immunity does not dominate indefinitely.
            own_boosted = float(own_payoff[0]) if own_payoff else 0.0
            direct_score = float(result.get("Best MoveScore") or 0)
            incoming = float(result.get("Incoming Worst Score") or 0)
            is_status_payoff = bool(own_payoff and own_boosted > 0)
            grade = (
                min(max(ratio, 0.0), 8.0) * 1.25
                + (0.85 if is_status_payoff else 0.0)
                + (0.65 if priority else 0.0)
                + control_value * 0.20
                + (1.75 if speed_flip else 0.0)
                + (0.35 if team_payoff and team_payoff[0] > 0 else 0.0)
                + (0.20 if pivot else 0.0)
                + min(max(accuracy - 70.0, 0.0), 30.0) / 100.0
                + min(direct_score / max(incoming, 1.0), 5.0) * 0.12
            )
            candidates.append((grade, member, move_name, status, result, accuracy, pivot, own_payoff, team_payoff, speed_note, speed_flip))
    if not candidates:
        return None, "No reliable, safely modeled status setter can affect this opponent; use Strongest Matchup."
    _, setter, move_name, status, result, accuracy, pivot, own_payoff, payoff, speed_note, speed_flip = max(candidates, key=lambda c: c[0])
    # Judge the entire follow-through, not just the largest conditional Hex.
    # A switch costs a turn and exposes the incoming Pokémon. The current
    # unconditioned matchup is our conservative safety baseline: never project
    # a switch into a recorded incoming OHKO or a clearly unfavorable matchup.
    # Status may mitigate some physical attacks, but that is not sufficient to
    # declare a previously unsafe switch safe without redoing the damage model.
    setter_direct_score = float(result.get("Best MoveScore") or 0.0)
    setter_direct_move = str(result.get("Best Move") or "")
    if own_payoff and (not payoff or own_payoff[0] >= 0.70 * payoff[0]):
        payoff = own_payoff
    if payoff is not None:
        projected_score, _, projected_member, _ = payoff
        projected_name = str(projected_member.get("Pokemon") or "")
        if projected_member.get("MemberID") != setter.get("MemberID"):
            projected_matchup = lookup.get(projected_member.get("MemberID")) or lookup.get(projected_name)
            projected_notes = {
                str(note.get("text") or "")
                for note in (projected_matchup or {}).get("Battle Notes", [])
                if isinstance(note, dict)
            }
            projected_ratio = float((projected_matchup or {}).get("Ratio") or 0.0)
            unsafe_switch = (
                projected_matchup is None
                or projected_ratio < 1.0
                or bool({"Likely Incoming OHKO", "Possible Incoming OHKO"} & projected_notes)
            )
            # A cross-team payoff also needs enough upside to justify giving
            # up a safe immediate attack from the Pokémon already on the field.
            inadequate_gain = setter_direct_score > 0 and projected_score < setter_direct_score * 1.25
            if unsafe_switch or inadequate_gain:
                payoff = own_payoff
        # Compare even a *self-contained* conditional payoff with the user's
        # actual immediate attack. For example, Runerigus's Body Press is much
        # better into Dark-type Scrafty than its resisted boosted Hex.
        if payoff is not None and payoff[2].get("MemberID") == setter.get("MemberID"):
            if setter_direct_score > 0 and float(payoff[0]) <= setter_direct_score:
                payoff = None
    name = pokemon_display_name(setter)
    ratio = float(result.get("Ratio") or 0)
    priority = str(setter.get("Ability") or "").casefold() == "prankster"
    if (ratio >= 1.5 and accuracy >= 85) or (priority and ratio >= 0.8 and accuracy >= 85):
        fit, rank = "Strong", 3
    elif ratio >= 0.9:
        fit, rank = "Viable", 2
    else:
        fit, rank = "Risky", 1

    projected = None
    payoff_member = None
    if payoff is not None:
        boosted, unboosted, payoff_member, payoff_move = payoff
        payoff_name = pokemon_display_name(payoff_member)
        same = setter.get("MemberID") == payoff_member.get("MemberID")
        followup = (f"stay in and use {payoff_move}" if same else
                    f"switch to {payoff_name} and use {payoff_move}")
        detail = (f"Step 1: {name} uses {move_name} to inflict {status} on this opponent. "
                  f"Step 2: if status lands, {followup}. "
                  "Reapply status separately against each new opponent.")
        heading = (f"{name} → {move_name} → {payoff_move}" if same else
                   f"{name} → {move_name} → {payoff_name} ({payoff_move})")
        projected = (payoff_name, payoff_move, boosted, unboosted, status)
        payoff_comment = ("The setter supplies its own payoff." if same else
                          f"{payoff_name} supplies the payoff after a switch.")
    else:
        detail = (f"Step 1: {name} uses {move_name} to inflict {status} on this opponent. "
                  "This provides status control even without a supported boosted attack. "
                  "Choose a safe ordinary attack or switch afterward; reassess status for each new opponent.")
        # No status-boosted move is usable, but the selected setter may still
        # have a solid direct attack. Put that contingency in the quick heading.
        direct_move = str(result.get("Best Move") or "").strip()
        direct_score = float(result.get("Best MoveScore") or 0)
        heading = (f"{name} → {move_name} → {direct_move}"
                   if direct_move and direct_score > 0 else f"{name} → {move_name}")
        if direct_move and direct_score > 0:
            detail = (f"Step 1: {name} uses {move_name} to inflict {status} on this opponent. "
                      f"Step 2: {direct_move} provides an immediate damaging alternative. "
                      "Reassess status separately against each new opponent.")
        payoff_comment = "The setter's direct attack is the safer or stronger follow-up here."
    return dict(
        member_id=setter.get("MemberID"), setter_member_id=setter.get("MemberID"),
        payoff_member_id=payoff_member.get("MemberID") if payoff_member else None,
        pokemon_name=name, recommended_pokemon_name=name, lead_pokemon_name=name,
        lead_move=move_name, fit=fit, fit_rank=rank,
        summary=f"Inflict {status} with {name}", reason=detail,
        action=f"Establish {status} with {name}", action_detail=detail,
        plan_kind="status_setup", can_override_direct=True,
        opener_threat_move=str(result.get("Worst Incoming Move") or "") or None,
        opener_threat_category=str(result.get("Worst Incoming Move Category") or "") or None,
        opener_threat_type=str(result.get("Worst Incoming Move Type") or "") or None,
        opener_threat_score=float(result.get("Incoming Worst Score") or 0),
        opener_threat_multiplier=float(result.get("Incoming Multiplier") or 1),
        strategy_branch="status_control_punish", action_type="Status Setup",
        plan_role="Status Setter",
        fit_explanation=(f"{move_name}: {accuracy:g}% accuracy. "
                         f"{'Prankster priority. ' if priority else ''}"
                         f"{'Speed advantage projected. ' if speed_flip else ''}{payoff_comment}"),
        sequence_heading=heading,
        state_assumption="No status is assumed on this opponent before setup. " + speed_note,
        fallback_if_assumption_fails="If status misses or cannot be established, use the named direct fallback.",
        condition_detail="",
    ), projected


def _enemy_setup_followup_is_lethal(opponent, member, planned_attack, our_setup,
                                    boosted_member, moves_data, items, ability_rules,
                                    own_speed, speed_after, enemy_speed,
                                    uncertain_weather):
    """Reject setups exposed to a credible enemy boost-then-lethal-hit branch.

    We do not charge a Speed-stage change as danger on its own. Only a damaging
    follow-up that can move before our attack can veto the setup.
    """
    from engine.calculations import calculate_damage_range
    enemy_moves = get_moves(opponent, moves_data)
    lookup = _build_move_lookup(moves_data)
    hp = float(get_stat(member, "HP") or 0)
    if hp <= 0:
        return True
    for move in enemy_moves:
        status = {**move, **lookup.get(str(move.get("Move") or ""), {})}
        if status.get("Category") != "Status" or status.get("StageChangeTarget") != "User":
            continue
        boosts = {stat: float(status.get(field) or 0) for stat, field in
                  (("ATK", "AtkStageChange"), ("SPA", "SpAStageChange"),
                   ("SPE", "SpeStageChange"))}
        if boosts["ATK"] <= 0 and boosts["SPA"] <= 0:
            continue
        boosted_foe = dict(opponent)
        for stat, stage in boosts.items():
            if stage > 0:
                boosted_foe[stat] = float(get_stat(opponent, stat)) * (2 + stage) / 2
        foe_after = enemy_speed * ((2 + boosts["SPE"]) / 2 if boosts["SPE"] > 0 else 1)
        priority = float(planned_attack.get("Priority") or 0)
        enemy_first = priority < 0 or (priority == 0 and
                       (uncertain_weather or foe_after >= speed_after))
        if not enemy_first:
            continue
        for attack in enemy_moves:
            if attack.get("Category") not in {"Physical", "Special"}:
                continue
            _, high = calculate_damage_range(boosted_foe, member, attack,
                                             items, ability_rules)
            if high is not None and float(high) >= hp:
                return True
    return False


def _setup_sweep_continuation(lead_plan, team_data, opponent, matchups,
                               moves_data, items, ability_rules, battle_roster=None):
    """Conditional, conservative continuation of the lead's single setup turn."""
    from engine.calculations import calculate_damage_range
    from engine.mechanics import get_type_multiplier, get_effective_pokemon_types
    member = next((m for m in team_data
                   if m.get("MemberID") == lead_plan.get("member_id")), None)
    if member is None:
        return None
    setup = _build_move_lookup(moves_data).get(lead_plan.get("lead_move"), {})
    projected = dict(member)
    for stat, field in (("ATK", "AtkStageChange"), ("SPA", "SpAStageChange"),
                        ("SPE", "SpeStageChange")):
        stage = float(setup.get(field) or 0)
        if stage > 0:
            projected[stat] = float(get_stat(member, stat)) * (2 + stage) / 2
    options = []
    for attack in get_moves(member, moves_data):
        if attack.get("Category") not in {"Physical", "Special"}:
            continue
        boosted_score = float(calculate_move_score(projected, opponent, attack,
                                                   items, ability_rules))
        if boosted_score <= 0:
            continue
        low, high = calculate_damage_range(projected, opponent, attack,
                                           items, ability_rules)
        options.append((boosted_score, float(low or 0), attack))
    if not options:
        return None
    boosted_score, min_damage, attack = max(options, key=lambda t: t[0])
    # No invented boost count; the one lead setup turn is the *only* assumption.
    # Use real HP damage for survivability and never claim an OHKO from MoveScore.
    hp = float(get_stat(member, "HP") or 0)
    worst = 0.0
    for move in get_moves(opponent, moves_data):
        if move.get("Category") not in {"Physical", "Special"}:
            continue
        _, maximum = calculate_damage_range(opponent, member, move, items, ability_rules)
        if maximum is not None:
            worst = max(worst, float(maximum))
    if hp <= 0 or worst >= hp:
        return None
    # Survival alone does not make a sweep worth preserving. Compare the
    # established attack's conditional offense and defense with the available
    # unboosted direct alternatives. Require a meaningful continuation, not a
    # merely nonlethal incoming hit.
    current_row = next((r for r in matchups if r.get("MemberID") == member.get("MemberID")), None)
    direct_ratio = float((current_row or {}).get("Ratio") or 0.0)
    incoming_score = float((current_row or {}).get("Incoming Worst Score") or 0.0)
    boosted_ratio = boosted_score / max(incoming_score, 1.0)
    best_direct_ratio = max((float(r.get("Ratio") or 0.0) for r in matchups), default=0.0)
    # If Strongest Matchup would choose the very same member, a low ratio is
    # not a reason to abandon an established boost: the fallback cannot offer
    # a better teammate, and switching tactics would not undo Swords Dance.
    direct_best, _, _ = find_best_team_member(
        team_data, opponent, items, ability_rules, moves_data
    )
    same_direct_member = bool(
        isinstance(direct_best, dict)
        and (direct_best.get("MemberID") == member.get("MemberID")
             if member.get("MemberID") else direct_best is member)
    )
    if not same_direct_member and (
        boosted_ratio < 1.25 or
        (direct_ratio < 1.0 and best_direct_ratio >= 1.5 and
         boosted_ratio < best_direct_ratio * 0.85)
    ):
        return None
    name = pokemon_display_name(member)
    move_name = str(attack.get("Move") or "")
    direct = float(calculate_move_score(member, opponent, attack, items, ability_rules))
    target_hp = float(get_stat(opponent, "HP") or 0)
    likely_ko = bool(target_hp > 0 and min_damage >= 1.10 * target_hp)
    # Retain the lead plan's named sweep projection on continuation cards.
    # Each other roster member is evaluated independently; no order or extra
    # setup turns are assumed. This is descriptive, not a ranking modifier.
    from engine.calculations import OHKO_RECOMMENDATION_CONFIDENCE
    sweep_targets = []
    for future in [opponent, *_other_battle_opponents(opponent, battle_roster)]:
        future_hp = float(get_stat(future, "HP") or 0)
        if future_hp <= 0:
            continue
        best = None
        for future_move in get_moves(member, moves_data):
            if future_move.get("Category") not in {"Physical", "Special"}:
                continue
            low, _ = calculate_damage_range(projected, future, future_move,
                                            items, ability_rules)
            if low is not None and float(low) >= OHKO_RECOMMENDATION_CONFIDENCE * future_hp:
                score = float(calculate_move_score(projected, future, future_move,
                                                   items, ability_rules))
                if best is None or score > best[0]:
                    best = (score, str(future_move.get("Move") or ""))
        if best:
            sweep_targets.append(f"{future.get('Pokemon', 'opponent')} ({best[1]})")
    sweep_note = (f" Sweep potential: With {lead_plan['lead_move']} active, {name} has projected "
                  f"OHKOs against {_screen_name_list(sweep_targets)}."
                  if sweep_targets else "")
    # Dig protects the user while underground from ordinary attacks, although
    # Earthquake/Magnitude and certain other effects can still reach it.
    # Describe that advantage only when the opponent's known move list does
    # not contain a relevant underground-hitting attack.
    dig_shelter = move_name == "Dig" and not any(
        str(m.get("Move") or "") in {"Earthquake", "Magnitude", "Fissure"}
        for m in get_moves(opponent, moves_data)
    )
    if dig_shelter:
        sweep_note += (" Dig's underground turn protects against this "
                       "opponent's listed attacks before the strike lands.")
    assumption = (f"Conditional continuation: if {name} established {lead_plan['lead_move']} "
                  "against the lead and has remained in battle, preserve the boost. "
                  "The Compass cannot verify current HP, stages, or who is active.")
    return dict(
        member_id=member.get("MemberID"), pokemon_name=name,
        recommended_pokemon_name=name, lead_pokemon_name=name,
        lead_move=move_name, fit="Strong" if likely_ko else "Viable",
        fit_rank=3 if likely_ko else 2,
        summary=f"Continue sweep with {move_name}",
        reason=f"Keep the lead's setup investment; use {move_name} without another setup turn.",
        action=f"Continue {name}'s sweep", action_detail=(
            f"Assuming {lead_plan['lead_move']} has been used and its boosts are still active, use {move_name}. "
            f"Projected boosted Move Score {boosted_score:.2f} (unboosted {direct:.2f}). "
            "Switching removes stat boosts." + sweep_note),
        plan_kind="offensive_setup_continuation", can_override_direct=True,
        continuation_same_direct=same_direct_member,
        continuation_below_threshold=boosted_ratio < 1.25,
        continuation_dig_shelter=dig_shelter,
        strategy_branch="setup_offense", action_type="Offensive Payoff",
        plan_role="Established Sweeper", sequence_heading=f"{name} → {move_name}",
        state_assumption=assumption, condition_detail=assumption,
        fallback_if_assumption_fails=("If this Pokémon did not establish the boost, "
                                     "was switched out, or is too damaged, use the direct fallback."),
        setup_followup_move=move_name,
        setup_followup_type=str(attack.get("Type") or ""),
        setup_followup_score=boosted_score,
        setup_followup_base_score=direct,
        setup_followup_effectiveness=float(get_type_multiplier(
            str(attack.get("Type") or ""), get_effective_pokemon_types(opponent))),
        setup_followup_likely_ohko=likely_ko,
        attack_move_score=boosted_score, attack_score_conditional=True,
        fit_explanation=(f"Established one-turn {lead_plan['lead_move']} boost; "
                         "continuation is conditional on actual battle state."),
        opener_threat_move=None, opener_threat_category=None,
        opener_threat_type=None, opener_threat_score=0.0,
        opener_threat_multiplier=1.0,
    )


def _setup_sweep_quality(entry, opponent, team_data, moves_data, items,
                         ability_rules, battle_roster):
    """Estimate the *cost* of a one-boost sweep against the known battle roster.

    Every opposing member is evaluated independently; this does not claim a
    future send-out order or that the player's boost has actually been used.
    Prefer a plan that can deliver useful KOs without exhausting its HP budget.
    """
    from math import ceil
    from engine.calculations import calculate_damage_range
    from engine.mechanics import get_item_speed_multiplier

    _, member, setup_name, _, _, _, _, _, _, _, _, opening_risk, _ = entry
    setup = _build_move_lookup(moves_data).get(setup_name, {})
    projected = dict(member)
    for stat, field in (("ATK", "AtkStageChange"), ("SPA", "SpAStageChange"),
                        ("SPE", "SpeStageChange"), ("DEF", "DefStageChange"),
                        ("SPD", "SpDStageChange")):
        stage = float(setup.get(field) or 0)
        if stage > 0:
            projected[stat] = float(get_stat(member, stat)) * (2 + stage) / 2
    own_hp = float(get_stat(member, "HP") or 0)
    if own_hp <= 0:
        return (0, 0, -float("inf"), 0.0)
    # The known lead must be handled; future members are alternatives, not a
    # guaranteed sequence. No hypothetical additional setup turn is credited.
    rivals = [opponent, *_other_battle_opponents(opponent, battle_roster)]
    attacks = [m for m in get_moves(member, moves_data)
               if m.get("Category") in {"Physical", "Special"}]
    successes = 0
    reliable_ohkos = 0
    exposure_sum = 0.0
    offensive_margin = 0.0
    for foe in rivals:
        target_hp = float(get_stat(foe, "HP") or 0)
        if target_hp <= 0:
            continue
        choices = []
        for attack in attacks:
            low, _ = calculate_damage_range(projected, foe, attack, items, ability_rules)
            if low is None or float(low) <= 0:
                continue
            choices.append((float(low), attack))
        if not choices:
            continue
        low, attack = max(choices, key=lambda choice: choice[0])
        # Two-turn attacks must not be counted as immediate sweep KOs. The
        # charge turn can consume another action (or enable counterplay), even
        # if the attacker is semi-invulnerable for part of it.
        delayed_attacks = {"Dig", "Fly", "Dive", "Bounce", "Phantom Force",
                           "Shadow Force", "Solar Beam", "Solar Blade",
                           "Sky Attack", "Skull Bash", "Razor Wind",
                           "Freeze Shock", "Ice Burn"}
        attack_delay = int(str(attack.get("Move") or "") in delayed_attacks)
        turns = ceil(target_hp / low) + attack_delay
        if turns > 2:
            continue
        our_speed = float(get_stat(projected, "SPE")) * get_item_speed_multiplier(projected, items)
        foe_speed = float(get_stat(foe, "SPE")) * get_item_speed_multiplier(foe, items)
        priority = float(attack.get("Priority") or 0)
        strikes_first = priority > 0 or (priority == 0 and our_speed > foe_speed)
        # Hits before this member finishes its target, including an attack
        # before a slower sweeper's first move. The lead's setup-turn hit is
        # included separately below, not silently ignored.
        hits = turns - (1 if strikes_first else 0)
        worst = 0.0
        for enemy_move in get_moves(foe, moves_data):
            if enemy_move.get("Category") not in {"Physical", "Special"}:
                continue
            _, high = calculate_damage_range(foe, projected, enemy_move,
                                             items, ability_rules)
            if high is not None:
                worst = max(worst, float(high))
        damage = worst * hits
        if damage >= own_hp:
            continue
        successes += 1
        reliable_ohkos += int(turns == 1 and low >= 1.10 * target_hp)
        exposure_sum += damage / own_hp
        offensive_margin += min(2.0, low / target_hp)

    # The lead setup turn may itself consume HP (even when the next attack
    # outspeeds), and must count in the total cost of establishing the boost.
    exposure_sum += float(opening_risk)
    # Use attacks won and HP cost as the primary battle-wide discriminator.
    # Strong attacks and conservative OHKOs resolve otherwise close plans.
    return (successes, reliable_ohkos,
            -exposure_sum, offensive_margin)


def _setup_offense_battle_plan(team_data, opponent, matchups, moves_data, items, ability_rules, battle_roster=None, *, _lead_only=False):
    """Model an equipped self-boost followed by that same Pokémon's attack.

    Project one setup turn only. No boosts are transferred to teammates or
    inferred from earlier opponents. Full Analysis remains unboosted.
    """
    from engine.mechanics import get_item_speed_multiplier, get_guaranteed_weather
    # Later opponents are primarily a continuation decision, NOT an invitation
    # to spend another turn setting up with a different Pokémon. Reconstruct the
    # lead plan from the static roster, with an explicit conditional assumption:
    # the player followed the plan and the original sweeper retains its boost.
    if not _lead_only and str(opponent.get("Slot") or "") not in {"1", "1.0"}:
        lead = next((foe for foe in (battle_roster or [])
                     if str(foe.get("Trainer") or "") == str(opponent.get("Trainer") or "")
                     and str(foe.get("Battle") or "") == str(opponent.get("Battle") or "")
                     and str(foe.get("Slot") or "") in {"1", "1.0"}), None)
        if lead is not None:
            lead_matchups = evaluate_team_matchups(team_data, lead, items, ability_rules, moves_data)
            lead_plan = _setup_offense_battle_plan(
                team_data, lead, lead_matchups, moves_data, items, ability_rules,
                battle_roster=battle_roster, _lead_only=True)
            if isinstance(lead_plan, dict):
                continuing = _setup_sweep_continuation(
                    lead_plan, team_data, opponent, matchups, moves_data, items,
                    ability_rules, battle_roster=battle_roster)
                if continuing is not None:
                    return continuing
                # A genuine inability to continue is an explicit break of the
                # sweep, not another arbitrary fresh setup recommendation.
                return ("The planned lead sweeper cannot safely or effectively continue "
                        "against this opponent. Its earlier boost may need to be abandoned; "
                        "use Strongest Matchup and reassess the field.")
            # A lead that required direct fallback never established a modeled
            # setup plan. Do not fabricate one on subsequent roster members.
            return ("No safe Setup Offense opener was established for this battle's "
                    "lead. Use Strongest Matchup rather than assuming a fresh "
                    "setup on this later opponent.")
    by_name = _matchup_index(matchups)
    opponent_speed = float(get_stat(opponent, "SPE")) * float(get_item_speed_multiplier(opponent, items))
    weather = get_guaranteed_weather({}, opponent)
    weather_ability = {"swift swim": "Rain", "chlorophyll": "Sun",
                       "sand rush": "Sandstorm", "slush rush": "Hail"}
    required = weather_ability.get(str(opponent.get("Ability") or "").casefold())
    if required and weather == required:
        opponent_speed *= 2
    uncertain_weather = bool(required and weather is None)
    candidates = []
    setup_lookup = _build_move_lookup(moves_data)
    for member in team_data:
        name = str(member.get("Pokemon") or "")
        row = by_name.get(member.get("MemberID")) or by_name.get(name)
        if row is None:
            continue
        notes = {str(n.get("text") or "") for n in row.get("Battle Notes", []) if isinstance(n, dict)}
        if {"Likely Incoming OHKO", "Possible Incoming OHKO"} & notes:
            continue
        incoming = float(row.get("Incoming Worst Score") or 0)
        hp = float(get_stat(member, "HP"))
        # Move Score is not HP damage: use the actual damage-range model for
        # the incoming threat instead of treating IWS as a damage estimate.
        from engine.calculations import calculate_damage_range
        worst_name = str(row.get("Worst Incoming Move") or "")
        incoming_move = next((m for m in get_moves(opponent, moves_data)
                              if m.get("Move") == worst_name), None)
        if incoming_move is None:
            continue
        _, worst_max = calculate_damage_range(opponent, member, incoming_move, items, ability_rules)
        # When every known incoming damaging attack is ineffective, the matchup
        # engine correctly reports IWS=0. Its worst-move fallback may be a
        # status move (e.g. Duosion's Light Screen); Status has no HP damage
        # range, but that is a *safe* setup opening, not an unknown threat.
        # Preserve conservative rejection of unknown damage for nonimmune rows.
        if worst_max is None and incoming <= 0:
            worst_max = 0.0
        if worst_max is None or float(worst_max) >= hp:
            continue
        own_speed = float(get_stat(member, "SPE")) * float(get_item_speed_multiplier(member, items))
        own_weather_ability = weather_ability.get(str(member.get("Ability") or "").casefold())
        entry_weather = get_guaranteed_weather(member, opponent)
        if own_weather_ability and entry_weather == own_weather_ability:
            own_speed *= 2
        for equipped_setup in get_moves(member, moves_data):
            setup = {**equipped_setup, **setup_lookup.get(str(equipped_setup.get("Move") or ""), {})}
            if setup.get("Category") != "Status" or setup.get("StageChangeTarget") != "User":
                continue
            fields = (("ATK", "AtkStageChange"), ("SPA", "SpAStageChange"),
                      ("SPE", "SpeStageChange"))
            boosts = {stat: float(setup.get(field) or 0) for stat, field in fields}
            if not any(value > 0 for value in boosts.values()):
                continue
            if any(value < 0 for value in boosts.values()):
                continue
            if str(setup.get("Move") or "") in {"Belly Drum", "Shell Smash"}:
                # HP payment and defensive drops require additional survival modeling.
                continue
            speed_after = own_speed * ((2 + boosts["SPE"]) / 2 if boosts["SPE"] else 1)
            speed_flip = bool(not uncertain_weather and own_speed <= opponent_speed < speed_after)
            boosted_member = dict(member)
            for stat in ("ATK", "SPA", "SPE"):
                stage = boosts[stat]
                if stage:
                    # Speed-dependent attacks (particularly Electro Ball) must
                    # receive the same boosted Speed as turn-order analysis.
                    boosted_member[stat] = float(get_stat(member, stat)) * (2 + stage) / 2
            attacks = []
            for attack in get_moves(member, moves_data):
                if attack.get("Category") not in {"Physical", "Special"}:
                    continue
                base = float(calculate_move_score(member, opponent, attack, items, ability_rules))
                projected = float(calculate_move_score(boosted_member, opponent, attack, items, ability_rules))
                if projected > 0:
                    attacks.append((projected, base, attack))
            if not attacks:
                continue
            boosted_score, base_score, attack = max(attacks, key=lambda item: item[0])
            direct_score = float(row.get("Best MoveScore") or 0)
            damage_gain = boosted_score / max(direct_score, 1)
            if damage_gain < 1.15 and not speed_flip:
                continue
            setup_name = str(setup.get("Move") or "")
            priority = int(float(setup.get("Priority") or 0))
            if str(member.get("Ability") or "").casefold() == "prankster":
                priority += 1
            acts_first = priority > 0 or (priority == 0 and own_speed >= opponent_speed and not uncertain_weather)
            risk_ratio = float(worst_max) / hp
            # Unsafe two-turn setup is not justified by a hypothetical payoff.
            if risk_ratio > 0.70 and not acts_first:
                continue
            if risk_ratio > 0.85:
                continue
            # Preserve setup eligibility but rank the *resulting attack*, not
            # the relative multiplier. A safe direct OHKO merits a promotion;
            # OHKO promotion is evaluated after the projected boost as well.
            direct_move_name = str(row.get("Best Move") or "")
            direct_move = setup_lookup.get(direct_move_name)
            direct_ko = _offensive_payoff_key(member, opponent, direct_move,
                                               items, ability_rules, incoming=incoming)
            boosted_ko = _offensive_payoff_key(boosted_member, opponent, attack,
                                                items, ability_rules, incoming=incoming)
            sweep_ohkos = 0
            sweep_coverage = 0
            for future in _other_battle_opponents(opponent, battle_roster):
                moves_future = [m for m in get_moves(member, moves_data)
                                if m.get("Category") in {"Physical", "Special"}]
                if not moves_future:
                    continue
                future_keys = [_offensive_payoff_key(boosted_member, future, m,
                               items, ability_rules) for m in moves_future]
                best_future = max(future_keys)
                # Sweep continuation is not required to outspeed: a slower
                # boosted attacker may survive and KO. Use actual damage and
                # the supported conservative 110% threshold.
                future_hp = float(get_stat(future, "HP") or 0)
                if future_hp > 0:
                    for future_move in moves_future:
                        low, _ = calculate_damage_range(boosted_member, future,
                                                        future_move, items, ability_rules)
                        if low is not None and float(low) >= 1.10 * future_hp:
                            sweep_ohkos += 1
                            break
                sweep_coverage += best_future[2] > 0
            # Survival is a prerequisite, not merely a late tie-break.
            # If the foe strikes before our boosted follow-up, we must weather
            # two hits (the setup turn and the turn we attempt to attack),
            # unless a priority attack can preempt it.
            attack_priority = float(attack.get("Priority") or 0)
            attack_first = (attack_priority > 0 or
                            (attack_priority == 0 and speed_after >= opponent_speed
                             and not uncertain_weather))
            # A speed tie is uncertain, so do not promise an uncontested attack.
            if attack_priority < 0:
                attack_first = False
            opening_exposure = 0.0 if acts_first else 1.0
            # Even when setup occurs first, an opponent typically responds
            # after the boost; allow for one hit during the setup turn.
            first_hit = float(worst_max)
            if attack_first:
                total_exposure = first_hit
            else:
                total_exposure = first_hit * 2
            # Risk model deliberately does not assume healing, screens, or
            # opponent move choice. Don't advertise unsafe setup sequences.
            if total_exposure >= hp:
                continue
            # Enemy status setup can create an enhanced second-turn attack.
            # Evaluate the setup-then-attack branch separately; never combine
            # two mutually exclusive attacks on turn one. Speed itself is not
            # penalized: it matters only if the boosted attack can land first.
            if _enemy_setup_followup_is_lethal(
                opponent, member, attack, setup, boosted_member, moves_data,
                items, ability_rules, own_speed, speed_after, opponent_speed,
                uncertain_weather):
                continue
            setup_safety = max(0.0, 1.0 - total_exposure / hp)
            # Safety is the entry requirement; the ranking next compares
            # current-opponent offense, then the surviving HP margin. Sweep
            # potential belongs at the end as a tie-break, never ahead of
            # a better setup opportunity against the current opponent.
            score = (setup_safety, boosted_ko[0], direct_ko[0],
                     boosted_score, float(row.get("Ratio") or 0),
                     sweep_ohkos, sweep_coverage)
            candidates.append((score, member, setup_name, attack, row, boosted_score,
                               base_score, speed_flip, own_speed, opponent_speed,
                               speed_after, risk_ratio, uncertain_weather))
    if not candidates:
        return "No safe, worthwhile one-turn offensive setup was modeled. Use the strongest direct matchup."
    # Complete-sequence survival was a hard prerequisite above. Do not
    # exclude a candidate just because its safe setup costs slightly more HP
    # than a different safe opening. Compare the utility of *one* established
    # boost across the known opposing roster; the player can still abandon the
    # sweep when a later matchup no longer supports it.
    def plan_key(entry):
        cover, kos, negative_hp_cost, margin = _setup_sweep_quality(
            entry, opponent, team_data, moves_data, items,
            ability_rules, battle_roster)
        score, _, _, _, row, boosted, *_ = entry
        # Covering the roster is the objective. For similarly productive
        # plans, conserve HP, then favor the stronger immediate matchup.
        return (cover, negative_hp_cost, kos,
                float(row.get("Ratio") or 0.0), boosted, margin)

    (score, member, setup_name, attack, row, boosted_score, base_score,
     flip, own_speed, enemy_speed, speed_after, damage_risk, unknown_weather) = max(
         candidates, key=plan_key)
    name = pokemon_display_name(member)
    move_name = str(attack.get("Move") or "")
    # Explain a meaningful safety-led decision when boosted offense is close.
    # This is not a claim about which move the AI will select.
    safety_comparison = ""
    alternatives = [entry for entry in candidates if entry[1].get("MemberID") != member.get("MemberID")]
    if alternatives:
        closest = min(alternatives, key=lambda e: abs(float(e[5]) - float(boosted_score)))
        alternate_boosted = float(closest[5])
        if (max(alternate_boosted, boosted_score) > 0 and
                abs(alternate_boosted - boosted_score) / max(alternate_boosted, boosted_score) < 0.05):
            alternative_name = pokemon_display_name(closest[1])
            alternate_risk = float(closest[11])
            if damage_risk + 0.05 < alternate_risk:
                safety_comparison = (f" {name} and {alternative_name} have comparable boosted offense; "
                                     f"{name} is favored for a safer projected setup opportunity.")
    # Describe named sweep targets, not an assumed opponent order or a count.
    # Use the same conservative OHKO confidence as offensive promotion; a
    # second opponent can be fought at any point after the lead.
    from engine.calculations import calculate_damage_range, OHKO_RECOMMENDATION_CONFIDENCE
    from engine.mechanics import get_type_multiplier, get_effective_pokemon_types
    sweep_targets = []
    boosted_member = dict(member)
    setup_meta = setup_lookup.get(setup_name, {})
    boosts = {"ATK": float(setup_meta.get("AtkStageChange") or 0),
              "SPA": float(setup_meta.get("SpAStageChange") or 0),
              "SPE": float(setup_meta.get("SpeStageChange") or 0)}
    for stat, stages in boosts.items():
        if stages > 0:
            boosted_member[stat] = float(get_stat(member, stat)) * (2 + stages) / 2
    for future in _other_battle_opponents(opponent, battle_roster):
        hp_future = float(get_stat(future, "HP") or 0)
        if hp_future <= 0:
            continue
        best = None
        for future_move in get_moves(member, moves_data):
            if future_move.get("Category") not in {"Physical", "Special"}:
                continue
            low, _ = calculate_damage_range(boosted_member, future, future_move, items, ability_rules)
            if low is not None and float(low) >= OHKO_RECOMMENDATION_CONFIDENCE * hp_future:
                power = float(calculate_move_score(boosted_member, future, future_move, items, ability_rules))
                if best is None or power > best[0]:
                    best = (power, str(future_move.get("Move") or ""))
        if best:
            sweep_targets.append(f"{future.get('Pokemon', 'opponent')} ({best[1]})")
    sweep_note = (f" Sweep potential: With {setup_name} active, {name} has projected "
                  f"OHKOs against {_screen_name_list(sweep_targets)}."
                  if sweep_targets else "")
    strong = damage_risk <= 0.4 and (boosted_score >= base_score * 1.5 or flip)
    fit, rank = ("Strong", 3) if strong else ("Viable", 2)
    speed_text = (f" Setup changes turn order: Speed {own_speed:.0f} → {speed_after:.0f} "
                  f"versus {enemy_speed:.0f}." if flip else "")
    assumption = (f"Assumes {name} successfully used {setup_name} and kept its stat boosts. "
                  "Switching removes these boosts. The Compass cannot verify live battle state.")
    detail = (f"Step 1: {name} uses {setup_name} if at sufficient HP to survive setup. "
              f"Step 2: stay in and use {move_name}. Projected Move Score {boosted_score:.2f} "
              f"versus {base_score:.2f} before setup.{speed_text} "
              "Boosts are not carried over after switching or to another teammate." + sweep_note + safety_comparison)
    return dict(
        member_id=member.get("MemberID"),
        setup_followup_move=move_name,
        setup_followup_type=str(attack.get("Type") or ""),
        setup_followup_score=boosted_score,
        setup_followup_base_score=base_score,
        setup_followup_effectiveness=float(get_type_multiplier(str(attack.get("Type") or ""), get_effective_pokemon_types(opponent))),
        setup_followup_likely_ohko=bool(boosted_ko[0]),
        pokemon_name=name, recommended_pokemon_name=name, lead_pokemon_name=name,
        lead_move=setup_name, fit=fit, fit_rank=rank,
        summary=f"{setup_name} → {move_name}", reason=detail,
        action=f"Set up with {name}", action_detail=detail,
        plan_kind="offensive_setup", can_override_direct=True,
        opener_threat_move=str(row.get("Worst Incoming Move") or "") or None,
        opener_threat_category=str(row.get("Worst Incoming Move Category") or "") or None,
        opener_threat_type=str(row.get("Worst Incoming Move Type") or "") or None,
        opener_threat_score=float(row.get("Incoming Worst Score") or 0),
        opener_threat_multiplier=float(row.get("Incoming Multiplier") or 1),
        strategy_branch="setup_offense", action_type="Offensive Setup", plan_role="Setup Sweeper",
        fit_explanation=(f"{setup_name} enables {move_name} ({base_score:.2f} → {boosted_score:.2f}). "
                         + ("Speed advantage gained. " if flip else "")
                         + "Check HP before boosting." + safety_comparison),
        sequence_heading=f"{name} → {setup_name} → {move_name}",
        state_assumption="No stat boosts are assumed active at entry.",
        fallback_if_assumption_fails="If setup is unsafe or interrupted, use the named direct fallback.",
        condition_detail=assumption,
    )



def _contact_punishment_plan(team_data, opponent, matchups, moves_data, items, ability_rules):
    """Consider high-confidence contact-punishing protection (single battle).

    Opponent move choice and prior Protect uses are unknown. A contact-heavy
    attacking moveset is evidence of value, not a guarantee that contact occurs.
    """
    from engine.calculations import calculate_damage_range

    lookup = _build_move_lookup(moves_data)
    by_name = _matchup_index(matchups)
    incoming = [m for m in get_moves(opponent, moves_data)
                if m.get("Category") in {"Physical", "Special"}]
    if not incoming:
        return None
    contact = [m for m in incoming if m.get("MakesContact") is True]
    if not contact:
        return None
    contact_share = len(contact) / len(incoming)
    # Mixed noncontact moves make the expected punishment too speculative to
    # override an otherwise sound Iron Defense line.
    if contact_share < 1.0:
        return None
    target_types = {str(opponent.get("Type1") or ""), str(opponent.get("Type2") or "")}
    target_ability = str(opponent.get("Ability") or "").casefold()
    candidates = []
    for member in team_data:
        name = str(member.get("Pokemon") or "")
        row = by_name.get(member.get("MemberID")) or by_name.get(name)
        if not row:
            continue
        notes = {str(n.get("text") or "") for n in row.get("Battle Notes", []) if isinstance(n, dict)}
        if notes & {"Likely Incoming OHKO", "Possible Incoming OHKO"}:
            continue
        hp = float(get_stat(member, "HP") or 0)
        if hp <= 0:
            continue
        worst = []
        for move in incoming:
            _, upper = calculate_damage_range(opponent, member, move, items, ability_rules)
            if upper is None:
                break
            worst.append(float(upper))
        if len(worst) != len(incoming) or max(worst) >= hp:
            continue
        risk = max(worst) / hp
        equipped = {str(member.get(f"Move{i}") or "") for i in range(1, 5)}
        display_name = pokemon_display_name(member)
        for guard in ("Baneful Bunker", "Obstruct"):
            if guard not in equipped:
                continue
            if guard == "Baneful Bunker":
                # Unlike direct Toxic, Baneful Bunker's contact poisoning is not
                # modeled as Corrosion bypassing type immunity.
                if (target_types & {"Poison", "Steel"}
                    or target_ability in {"immunity", "pastel veil", "comatose", "purifying salt"}):
                    continue
                payoff = None
                venoshock = lookup.get("Venoshock") if "Venoshock" in equipped else None
                if venoshock:
                    normal = float(calculate_move_score(member, opponent, venoshock, items, ability_rules))
                    boosted = dict(venoshock, Power=float(venoshock.get("Power") or 0) * 2)
                    projected = float(calculate_move_score(member, opponent, boosted, items, ability_rules))
                    if projected > 0:
                        payoff = ("Venoshock", normal, projected)
                follow = payoff[0] if payoff else str(row.get("Best Move") or "")
                if not follow:
                    continue
                detail = (f"Step 1: {display_name} uses Baneful Bunker to block an attack. "
                          "If the opponent chooses a contact move, it becomes poisoned. "
                          + (f"Step 2: use Venoshock (projected conditional Move Score "
                             f"{payoff[2]:.2f} versus {payoff[1]:.2f} unpoisoned). " if payoff else
                             f"Step 2: use {follow} or continue attrition. ")
                          + "Contact and successful poison are not guaranteed; repeated protection can fail.")
                role = "Poison Setter" if payoff else "Attrition Anchor"
                action = "Poison Setup" if payoff else "Attrition"
                note = (f"Contact-only damaging moves favor Baneful Bunker. "
                        + ("Venoshock rewards a successful poison." if payoff else "The move denies damage while applying poison."))
                quality = 3 if payoff else 2
            else:
                # Obstruct is a Defense drop on the *opponent*, not a boost to
                # the user's Defense. Project damage by changing the defender.
                # Opponent records use base stats and a modeled IV. Convert
                # the defender to explicit effective stats before projecting a
                # stage drop; otherwise get_stat() would ignore the override.
                dropped = dict(opponent)
                for stat in ("HP", "ATK", "DEF", "SPA", "SPD", "SPE"):
                    dropped[stat] = float(get_stat(opponent, stat))
                dropped.pop("Trainer", None)
                dropped.pop("Battle", None)
                dropped["DEF"] *= 0.5
                attacks = []
                for move in get_moves(member, moves_data):
                    if move.get("Category") not in {"Physical", "Special"}:
                        continue
                    if move.get("Category") != "Physical" and move.get("Move") != "Body Press":
                        continue
                    normal = float(calculate_move_score(member, opponent, move, items, ability_rules))
                    projected = float(calculate_move_score(member, dropped, move, items, ability_rules))
                    if projected > 0:
                        attacks.append((projected, normal, str(move.get("Move") or "")))
                if not attacks:
                    continue
                projected, normal, follow = max(attacks)
                detail = (f"Step 1: {display_name} uses Obstruct to block an attack. "
                          "If the opponent chooses a contact move, its Defense falls two stages. "
                          f"Step 2: use {follow} (projected Move Score {projected:.2f} "
                          f"versus {normal:.2f} without the Defense drop). "
                          "Contact is not guaranteed; repeated protection can fail.")
                role, action = "Attrition Anchor", "Attrition"
                note = "Contact-only damaging moves make Obstruct's Defense reduction a credible payoff."
                quality = 2 if projected >= normal * 1.4 else 1
            fit = "Strong" if quality >= 2 and risk < 0.5 else "Viable"
            # Give contact punishment a role, but preserve much stronger
            # Iron Defense/Body Press plans via a later comparison.
            score = 2.2 + quality * 0.45 + min(float(row.get("Ratio") or 0), 4) * 0.2 - risk
            candidates.append((score, dict(
                member_id=member.get("MemberID"),
                pokemon_name=display_name, recommended_pokemon_name=display_name, lead_pokemon_name=display_name,
                lead_move=guard, fit=fit, fit_rank=3 if fit == "Strong" else 2,
                summary=f"{guard} → {follow}", reason=detail,
                action=f"Punish contact with {display_name}", action_detail=detail,
                plan_kind="contact_punishment", can_override_direct=True,
                opener_threat_move=str(row.get("Worst Incoming Move") or "") or None,
                opener_threat_category=str(row.get("Worst Incoming Move Category") or "") or None,
                opener_threat_type=str(row.get("Worst Incoming Move Type") or "") or None,
                opener_threat_score=float(row.get("Incoming Worst Score") or 0),
                opener_threat_multiplier=float(row.get("Incoming Multiplier") or 1),
                strategy_branch="defensive_attrition", action_type=action, plan_role=role,
                fit_explanation=note,
                sequence_heading=f"{display_name} → {guard} → {follow}",
                state_assumption="No contact or status is assumed active at entry.",
                fallback_if_assumption_fails="If the opponent uses a noncontact or status move, reassess and use the direct fallback.",
                condition_detail=(f"Assumes {guard} succeeds and the opponent chooses a contact attack. "
                                  "This is a conditional tactical projection, not a confirmed battle state."),
            )))
    return max(candidates, key=lambda x: x[0]) if candidates else None


def _defensive_attrition_battle_plan(team_data, opponent, matchups, moves_data, items, ability_rules):
    """Select a cautious defensive setup and project its immediate payoff.

    Scores and damage forecasts are conditional; no live boosts or HP are assumed.
    Iron Defense contributes +2 Defense stages, capped at +6 after three uses.
    """
    from engine.calculations import calculate_damage_range

    by_name = _matchup_index(matchups)
    move_lookup = _build_move_lookup(moves_data)
    candidates = []
    for member in team_data:
        name = str(member.get("Pokemon") or "")
        row = by_name.get(member.get("MemberID")) or by_name.get(name)
        if row is None:
            continue
        notes = {str(note.get("text") or "") for note in row.get("Battle Notes", []) if isinstance(note, dict)}
        if {"Likely Incoming OHKO", "Possible Incoming OHKO"} & notes:
            continue
        hp = float(get_stat(member, "HP"))
        incoming_moves = [move for move in get_moves(opponent, moves_data) if move.get("Category") in {"Physical", "Special"}]
        if not incoming_moves:
            continue
        incoming_ranges = [(move, calculate_damage_range(opponent, member, move, items, ability_rules)) for move in incoming_moves]
        if any(upper is None for _, (_, upper) in incoming_ranges):
            continue
        worst_max = max(float(upper) for _, (_, upper) in incoming_ranges if upper is not None)
        if worst_max >= hp or worst_max / max(hp, 1) > 0.75:
            continue
        equipped = {str(member.get(f"Move{i}") or "") for i in range(1, 5)}
        original_def = float(get_stat(member, "DEF"))
        body_press = move_lookup.get("Body Press") if "Body Press" in equipped else None
        base_bp = float(calculate_move_score(member, opponent, body_press, items, ability_rules)) if body_press else 0
        direct_score = float(row.get("Best MoveScore") or 0)
        direct_move = str(row.get("Best Move") or "")
        # Never spend a free turn boosting if the team's direct line already has
        # a modeled immediate OHKO from this Pokémon.
        if {"Likely OHKO", "Likely Survival OHKO"} & notes:
            continue
        for setup_name, defense_stages in (("Iron Defense", 2), ("Amnesia", 0), ("Cosmic Power", 1), ("Stockpile", 1)):
            if setup_name not in equipped:
                continue
            # Favor Iron Defense when it mitigates actual physical pressure or
            # produces a worthwhile Body Press damage payoff.
            new_member = dict(member)
            if defense_stages:
                new_member["DEF"] = original_def * (2 + defense_stages) / 2
            post_scores = [(str(move.get("Move") or ""), float(calculate_move_score(opponent, new_member, move, items, ability_rules))) for move in incoming_moves]
            post_worst_move, post_iws = max(post_scores, key=lambda entry: entry[1])
            original_worst = float(row.get("Incoming Worst Score") or 0)
            mitigation = max(0, original_worst - post_iws)
            if setup_name == "Amnesia":
                # Calculate the SpD gain, not just Defense.
                new_member["SPD"] = float(get_stat(member, "SPD")) * 2
                post_scores = [(str(move.get("Move") or ""), float(calculate_move_score(opponent, new_member, move, items, ability_rules))) for move in incoming_moves]
                post_worst_move, post_iws = max(post_scores, key=lambda entry: entry[1])
                mitigation = max(0, original_worst - post_iws)
            if setup_name in {"Cosmic Power", "Stockpile"}:
                new_member["SPD"] = float(get_stat(member, "SPD")) * 1.5
                post_scores = [(str(move.get("Move") or ""), float(calculate_move_score(opponent, new_member, move, items, ability_rules))) for move in incoming_moves]
                post_worst_move, post_iws = max(post_scores, key=lambda entry: entry[1])
                mitigation = max(0, original_worst - post_iws)
            boosted_bp = float(calculate_move_score(new_member, opponent, body_press, items, ability_rules)) if body_press else 0
            bp_gain = max(0, boosted_bp - base_bp)
            if mitigation < original_worst * 0.08 and bp_gain < max(20, base_bp * 0.35):
                continue
            attack_name = "Body Press" if boosted_bp > direct_score * 1.1 else direct_move
            attack_score = boosted_bp if attack_name == "Body Press" else direct_score
            # A useful setup needs to compensate for a lost turn and yield either
            # stronger offense or genuine mitigation of the opponent's attacks.
            score = (mitigation / max(original_worst, 1) * 3
                     + max(0, attack_score - direct_score) / max(direct_score, 1) * 1.3
                     + min(float(row.get("Ratio") or 0), 4) * 0.30
                     - worst_max / hp)
            candidates.append((score, member, row, setup_name, attack_name, attack_score, post_worst_move, post_iws, worst_max / hp, body_press, original_def))
    if not candidates:
        return "No sufficiently safe, valuable defensive setup was modeled; use Strongest Matchup."
    _, member, row, setup_name, attack_name, attack_score, post_move, post_iws, risk, body_press, original_def = max(candidates, key=lambda entry: entry[0])
    name = pokemon_display_name(member)
    detailed = ""
    if setup_name == "Iron Defense" and body_press is not None:
        base = float(calculate_move_score(member, opponent, body_press, items, ability_rules))
        milestones = []
        first_ko = None
        target_hp = float(get_stat(opponent, "HP"))
        for uses in (1, 2, 3):
            boosted = dict(member)
            # +2/+4/+6 stages = 2x/3x/4x Defense respectively.
            boosted["DEF"] = original_def * (1 + uses)
            value = float(calculate_move_score(boosted, opponent, body_press, items, ability_rules))
            minimum, maximum = calculate_damage_range(boosted, opponent, body_press, items, ability_rules)
            ko = bool(minimum is not None and target_hp > 0 and float(minimum) >= target_hp)
            if ko and first_ko is None:
                first_ko = uses
            milestones.append(f"{uses}: {value:.2f}" + (" (Likely OHKO)" if ko else ""))
        detailed = (f"Body Press Move Scores after Iron Defense(s) (unboosted {base:.2f}): "
                    + "; ".join(milestones) + ". ")
        if first_ko is not None:
            detailed += f"The first projected Likely OHKO occurs after {first_ko} Iron Defense(s); additional boosts may be unnecessary. "
        else:
            detailed += "No guaranteed-range OHKO is projected within three Iron Defenses. "
        detailed += "Likely OHKO assumes Body Press can hit and the opponent does not interrupt setup; the damage range uses its modeled HP. "
    fit = "Strong" if risk < 0.40 and (attack_score >= float(row.get("Best MoveScore") or 0) * 1.5 or post_iws < float(row.get("Incoming Worst Score") or 0) * 0.7) else "Viable"
    return dict(
        member_id=member.get("MemberID"),
        pokemon_name=name, recommended_pokemon_name=name, lead_pokemon_name=name,
        lead_move=setup_name, fit=fit, fit_rank=3 if fit == "Strong" else 2,
        summary=f"{setup_name} → {attack_name}",
        reason=f"{name} sets up {setup_name} before attacking with {attack_name}.",
        action=f"Set up defenses with {name}",
        action_detail=(f"Step 1: {name} uses {setup_name} when sufficiently healthy. "
                       f"Step 2: use {attack_name}. With one setup, the modeled Incoming Worst Move "
                       f"is {post_move} (IWS {post_iws:.2f}). " + detailed
                       + "Boosts are lost when switching."),
        plan_kind="defensive_setup", can_override_direct=True,
        opener_threat_move=str(row.get("Worst Incoming Move") or "") or None,
        opener_threat_category=str(row.get("Worst Incoming Move Category") or "") or None,
        opener_threat_type=str(row.get("Worst Incoming Move Type") or "") or None,
        opener_threat_score=float(row.get("Incoming Worst Score") or 0),
        opener_threat_multiplier=float(row.get("Incoming Multiplier") or 1),
        strategy_branch="defensive_attrition", action_type="Defensive Setup",
        plan_role="Defensive Anchor" if attack_name != "Body Press" else "Attrition Attacker",
        fit_explanation=f"{setup_name} reduces modeled incoming pressure; {attack_name} provides the follow-up. Check HP before boosting.",
        sequence_heading=f"{name} → {setup_name} → {attack_name}",
        state_assumption="No defensive boosts are assumed active at entry.",
        fallback_if_assumption_fails="If setup is unsafe or interrupted, use the named direct fallback.",
        condition_detail=f"Assumes {setup_name} succeeded and {name} remains on the field.",
    )

def _anti_setup_interception(team_data, opponent, matchups, moves_data, items, ability_rules):
    """Find a credible immediate KO before a dangerous opposing offensive boost.

    Only the opponent's EQUIPPED setup moves count. This does not treat a high
    Move Score as HP damage: a modeled minimum damage range must meet target HP.
    Setup is not automatically overridden against non-threatening defensive boosts.
    """
    from engine.calculations import calculate_damage_range

    move_lookup = _build_move_lookup(moves_data)
    threats = []
    for move in get_moves(opponent, moves_data):
        record = {**move, **move_lookup.get(str(move.get("Move") or ""), {})}
        if record.get("Category") != "Status" or record.get("StageChangeTarget") != "User":
            continue
        attack_boost = max(float(record.get("AtkStageChange") or 0),
                           float(record.get("SpAStageChange") or 0))
        speed_boost = float(record.get("SpeStageChange") or 0)
        if attack_boost >= 2 or (attack_boost >= 1 and speed_boost >= 1):
            threats.append(str(record.get("Move") or ""))
    if not threats:
        return None
    # A survival effect can make a nominal OHKO fail; don't promise interception.
    if str(opponent.get("Ability") or "").casefold() in {"sturdy", "disguise"}:
        return None
    if str(opponent.get("Held Item") or "").casefold() == "focus sash":
        return None
    hp = float(get_stat(opponent, "HP") or 0)
    if hp <= 0:
        return None
    by_name = _matchup_index(matchups)
    candidates = []
    for member in team_data:
        name = str(member.get("Pokemon") or "")
        row = by_name.get(member.get("MemberID")) or by_name.get(name)
        if row is None:
            continue
        notes = {str(n.get("text") or "") for n in row.get("Battle Notes", []) if isinstance(n, dict)}
        if notes & {"Likely Incoming OHKO", "Possible Incoming OHKO"}:
            continue
        for move in get_moves(member, moves_data):
            if move.get("Category") not in {"Physical", "Special"}:
                continue
            try:
                minimum, maximum = calculate_damage_range(member, opponent, move, items, ability_rules)
            except (ValueError, TypeError, ZeroDivisionError):
                continue
            if minimum is None or float(minimum) < hp:
                continue
            accuracy = float(move.get("Accuracy") or 100)
            if accuracy < 80:
                continue
            move_name = str(move.get("Move") or "")
            score = float(calculate_move_score(member, opponent, move, items, ability_rules))
            # Every candidate already has a conservative on-hit OHKO and >=80%
            # accuracy. Prefer survival/matchup safety before hit chance: a
            # 95%-accurate KO from a vulnerable attacker must not outrank an
            # 85%-accurate KO from a teammate that safely walls the opponent.
            # Accuracy and offensive score break ties between similarly safe picks.
            candidates.append((float(row.get("Ratio") or 0), accuracy, score, member.get("MemberID"), move_name))
    if not candidates:
        return None
    ratio, accuracy, score, member_id, attack = max(candidates)
    return member_id, attack, threats[0], accuracy



# Weather Control uses the same four weather families as guided onboarding.
_WEATHER_MOVES = {"Rain Dance": "Rain", "Sunny Day": "Sun", "Sandstorm": "Sandstorm", "Hail": "Hail"}
_WEATHER_ABILITIES = {"Drizzle": "Rain", "Drought": "Sun", "Sand Stream": "Sandstorm", "Snow Warning": "Hail"}
_WEATHER_SPEED_ABILITIES = {"Swift Swim": "Rain", "Chlorophyll": "Sun", "Sand Rush": "Sandstorm", "Slush Rush": "Hail"}
_WEATHER_EXTENSION_ITEMS = {"Rain": "Damp Rock", "Sun": "Heat Rock", "Sandstorm": "Smooth Rock", "Hail": "Icy Rock"}



def _unmodeled_weather_notes(member: dict, weather: str | None) -> list[BattleNoteViewModel]:
    """Informational Gen VIII singles notes; no speculative HP or hit-rate modeling.

    These effects are NOT applied to Move Score, incoming damage, or OHKO odds.
    Weather is the projected condition *after* the recommended member enters.
    """
    if weather not in {"Rain", "Sun", "Sandstorm", "Hail"}:
        return []
    ability = str(member.get("Ability") or "").strip()
    name = pokemon_display_name(member)
    types = {str(member.get(key) or "").title() for key in ("Type1", "Type2")}
    notes: list[BattleNoteViewModel] = []

    def add(category: str, message: str) -> None:
        notes.append(BattleNoteViewModel(
            icon=NOTE_ICONS.get(category, "•"), category=category, text=message))

    if weather == "Sandstorm":
        exempt = bool(types & {"Rock", "Ground", "Steel"}) or ability in {
            "Overcoat", "Magic Guard", "Sand Rush", "Sand Force", "Sand Veil"
        }
        if not exempt:
            add("caution", f"Sandstorm chip: {name} loses 1/16 maximum HP at the end of each turn while Sandstorm is active (not included in matchup calculations).")
        if ability == "Sand Veil":
            add("info", f"Sand Veil: Sandstorm reduces the accuracy of moves targeting {name} to 80% of normal; this evasion benefit is not modeled.")
    elif weather == "Hail":
        exempt = "Ice" in types or ability in {
            "Overcoat", "Magic Guard", "Snow Cloak", "Ice Body", "Slush Rush"
        }
        if not exempt:
            add("caution", f"Hail chip: {name} loses 1/16 maximum HP at the end of each turn while Hail is active (not included in matchup calculations).")
        if ability == "Snow Cloak":
            add("info", f"Snow Cloak: Hail reduces the accuracy of moves targeting {name} to 80% of normal; this evasion benefit is not modeled.")
        if ability == "Ice Body":
            add("info", f"Ice Body: Hail restores 1/16 of {name}'s maximum HP at the end of each turn; recovery is not modeled.")
    elif weather == "Rain":
        if ability == "Rain Dish":
            add("info", f"Rain Dish: Rain restores 1/16 of {name}'s maximum HP at the end of each turn; recovery is not modeled.")
        elif ability == "Dry Skin":
            add("info", f"Dry Skin: Rain restores 1/8 of {name}'s maximum HP at the end of each turn; recovery is not modeled.")
        elif ability == "Hydration":
            add("info", f"Hydration: Rain cures {name}'s major status conditions at the end of each turn; status recovery is not modeled.")
    elif weather == "Sun":
        if ability == "Dry Skin":
            add("caution", f"Dry Skin: Harsh sunlight damages {name} for 1/8 maximum HP at the end of each turn; residual damage is not modeled.")
        elif ability == "Solar Power":
            add("caution", f"Solar Power: Harsh sunlight costs {name} 1/8 maximum HP at the end of each turn; residual damage is not modeled.")
        elif ability == "Leaf Guard":
            add("info", f"Leaf Guard: Harsh sunlight prevents major status conditions on {name}; status protection is not modeled.")
        elif ability == "Flower Gift":
            add("info", f"Flower Gift: Harsh sunlight boosts {name}'s Attack and Special Defense; its conditional stat effects are not fully modeled.")
    return notes


def _weather_for_recommended_member(member: dict, plan: StrategyPlanViewModel | None,
                                    reported_weather: str | None) -> str | None:
    """Use planned weather, not just dropdown; entry Abilities override it."""
    entry = _WEATHER_ABILITIES.get(str(member.get("Ability") or ""))
    if entry:
        return entry
    if plan is not None and plan.strategy_branch == "weather_control":
        # The plan is the authoritative projection when its setter differs
        # from the beneficiary or the dropdown is unspecified.
        for candidate in ("Sandstorm", "Hail", "Rain", "Sun"):
            if candidate in str(plan.action or "") or candidate in str(plan.sequence_heading or ""):
                return candidate
    return reported_weather if reported_weather in _WEATHER_EXTENSION_ITEMS else None


def _weather_entry_order(ours, opponent, items):
    """Compare simultaneous entry-weather Abilities; slower activates last.

    This is a conditional projection, not evidence both Pokemon entered at once.
    Unknown Speed or tied Speed leaves the outcome unresolved.
    """
    from engine.mechanics import get_item_speed_multiplier
    own_weather = _WEATHER_ABILITIES.get(str(ours.get("Ability") or ""))
    foe_weather = _WEATHER_ABILITIES.get(str(opponent.get("Ability") or ""))
    if not own_weather or not foe_weather or own_weather == foe_weather:
        return None
    try:
        own_speed = float(get_stat(ours, "SPE")) * float(get_item_speed_multiplier(ours, items))
        foe_speed = float(get_stat(opponent, "SPE")) * float(get_item_speed_multiplier(opponent, items))
    except (ValueError, TypeError, KeyError):
        return None
    if own_speed <= 0 or foe_speed <= 0 or abs(own_speed - foe_speed) < 0.001:
        return None
    return (own_weather if own_speed < foe_speed else foe_weather, own_speed, foe_speed)


def _weather_battle_advice(team_data, opponent, items, battle_roster=None, moves_data=None):
    """Short, opponent-specific advisory; never infer currently active weather."""
    ours = [(p, _WEATHER_ABILITIES.get(str(p.get("Ability") or ""))) for p in team_data]
    ours = [(p, w) for p, w in ours if w]
    foe_weather = _WEATHER_ABILITIES.get(str(opponent.get("Ability") or ""))
    opponent_name = str(opponent.get("Pokemon") or "the opponent")
    if not ours:
        return "No automatic weather setter is on your team; manual setup takes a turn."
    if foe_weather:
        results = []
        for setter, weather in ours:
            if weather == foe_weather:
                continue
            name = pokemon_display_name(setter)
            order = _weather_entry_order(setter, opponent, items)
            if order is None:
                results.append(f"{name} ({weather}) versus {opponent_name} ({foe_weather}): entry order is uncertain")
            else:
                winner, a, b = order
                results.append(f"{name} ({weather}, Speed {a:.0f}) versus {opponent_name} ({foe_weather}, Speed {b:.0f}): {winner} activates last on simultaneous entry")
        if not results:
            return f"Both sides can establish {foe_weather}. Check which weather is currently active."
        # Distinct named comparisons; no repeated 'if both' with an unclear antecedent.
        return "Weather order: " + "; ".join(results) + ". A later switch-in can replace it."
    names = ", ".join(f"{pokemon_display_name(p)} ({w})" for p, w in ours)
    return f"Automatic setters available: {names}. Switching one in replaces existing ordinary weather; check remaining turns."


def _weather_control_battle_plan(team_data, opponent, matchups, moves_data, items, ability_rules, battle_roster=None, *, assumed_weather=None):
    """Rank actionable weather setter -> beneficiary sequences, not isolated moves.

    Weather is only assumed after the indicated setup/entry. The Compass does
    not know whether manual weather is still active later in the battle.
    """
    from engine.mechanics import get_guaranteed_weather, get_item_speed_multiplier
    from engine.calculations import calculate_damage_range

    by_name = _matchup_index(matchups)
    weather_options = []
    for setter in team_data:
        name = str(setter.get('Pokemon') or '')
        result = by_name.get(setter.get("MemberID")) or by_name.get(name)
        if not result:
            continue
        known = _WEATHER_ABILITIES.get(str(setter.get('Ability') or ''))
        options: list[tuple[str, str | None]] = [(known, None)] if known else []
        for move in get_moves(setter, moves_data):
            move_name = str(move.get('Move') or '')
            if move_name in _WEATHER_MOVES:
                options.append((_WEATHER_MOVES[move_name], move_name))
        for weather, setup_move in options:
            if not weather or (assumed_weather is not None and weather != assumed_weather):
                continue
            opponent_weather = _WEATHER_ABILITIES.get(str(opponent.get('Ability') or ''))
            if assumed_weather is None and opponent_weather and opponent_weather != weather and setup_move is None:
                # Only plan a simultaneous-entry payoff when the *desired*
                # weather activates last. Otherwise leave the counterplay to
                # the advisory instead of crediting weather that may not persist.
                order = _weather_entry_order(setter, opponent, items)
                if order is None or order[0] != weather:
                    continue
            notes = {str(n.get('text') or '') for n in result.get('Battle Notes', []) if isinstance(n, dict)}
            if assumed_weather is None and {'Likely Incoming OHKO', 'Possible Incoming OHKO'} & notes:
                continue
            if setup_move and assumed_weather is None:
                # A weather move consumes a vulnerable turn. Test modeled damage,
                # not IWS (which is not an HP estimate).
                threat = str(result.get('Worst Incoming Move') or '')
                incoming = next((m for m in get_moves(opponent, moves_data) if m.get('Move') == threat), None)
                if incoming is None:
                    continue
                _, max_damage = calculate_damage_range(opponent, setter, incoming, items, ability_rules)
                if max_damage is None or max_damage >= float(get_stat(setter, 'HP')) * 0.8:
                    continue
            weather_options.append((setter, result, weather, setup_move))

    if assumed_weather is not None:
        # Every member is eligible under the battlefield's reported weather.
        # An automatic setter changes that weather on entry; evaluate the
        # setter under its *resulting* weather rather than excluding it.
        weather_options = []
        for member in team_data:
            row = by_name.get(member.get('MemberID')) or by_name.get(str(member.get('Pokemon') or ''))
            if row is not None:
                effective_weather = _WEATHER_ABILITIES.get(str(member.get('Ability') or '')) or assumed_weather
                weather_options.append((member, row, effective_weather, None))
    if not weather_options:
        return 'No safe, supported weather setter can establish a useful weather condition here.' 

    # Compare any proposed two-step sequence with the team's strongest direct
    # score; a spectacular percentage gain from a weak base is not enough.
    best_direct_score = max((float(row.get("Best MoveScore") or 0.0)
                             for row in matchups if isinstance(row, dict)), default=0.0)
    best_direct_ratio = max((float(row.get("Ratio") or 0.0)
                             for row in matchups if isinstance(row, dict)), default=0.0)
    # Weather belongs to the battlefield, not to one attacker. Count the
    # opponent's known damaging moves across the battle when possible. This
    # explicitly distinguishes rain versus a Fire team from rain versus a
    # Water team. Missing roster moves never count as evidence.
    enemy_team = [row for row in (battle_roster or []) if isinstance(row, dict)] or [opponent]
    elemental_counts = {'Fire': 0, 'Water': 0}
    for enemy in enemy_team:
        for enemy_move in get_moves(enemy, moves_data):
            if enemy_move.get('Category') in {'Physical', 'Special'}:
                move_type = str(enemy_move.get('Type') or '')
                if move_type in elemental_counts:
                    elemental_counts[move_type] += 1
    # Let a diverse attack list count, without allowing repetitive attacks
    # from a large roster to swamp the direct battle evidence.
    fire_pressure = min(elemental_counts['Fire'], 5)
    water_pressure = min(elemental_counts['Water'], 5)
    candidates = []
    # The weather planner chooses viable field/setup possibilities. The shared
    # recommendation engine, not a separate Weather OHKO heuristic, chooses the
    # best eligible attacker once the resulting weather is assumed active.
    # Cache per-weather results to avoid repeating the expensive candidate scan.
    shared_weather_selection = {}
    for setter, setter_row, weather, setup_move in weather_options:
        setter_name = str(setter.get('Pokemon') or '')
        duration = 8 if str(setter.get('Held Item') or '') == _WEATHER_EXTENSION_ITEMS[weather] else 5
        # Ability-triggered weather is established on entry; manual weather costs
        # a turn. A change of Pokémon consumes a further weather turn.
        entry = setup_move is None
        for beneficiary in team_data:
            bname = str(beneficiary.get('Pokemon') or '')
            b_row = by_name.get(beneficiary.get("MemberID")) or by_name.get(bname)
            if b_row is None:
                continue
            # Switching in a different auto-weather setter immediately erases
            # the proposed weather. Never credit a cross-weather payoff.
            beneficiary_entry_weather = _WEATHER_ABILITIES.get(str(beneficiary.get('Ability') or ''))
            if assumed_weather is not None and beneficiary.get('MemberID') != setter.get('MemberID'):
                # This candidate is evaluated under its own entry weather.
                continue
            if assumed_weather is None and beneficiary.get("MemberID") != setter.get("MemberID") and beneficiary_entry_weather and beneficiary_entry_weather != weather:
                continue
            bnotes = {str(n.get('text') or '') for n in b_row.get('Battle Notes', []) if isinstance(n, dict)}
            if assumed_weather is None and {'Likely Incoming OHKO', 'Possible Incoming OHKO'} & bnotes:
                continue
            if assumed_weather is None and beneficiary.get("MemberID") != setter.get("MemberID") and float(b_row.get('Ratio') or 0) < 0.8:
                continue
            baseline_weather = get_guaranteed_weather(beneficiary, opponent)
            best_attack = None
            for attack in get_moves(beneficiary, moves_data):
                if str(attack.get('Category') or '') not in {'Physical', 'Special'}:
                    continue
                # Score through the shared damage model with explicit projected
                # weather, retaining the member's actual Ability and held item.
                normal = float(calculate_move_score(beneficiary, opponent, attack, items, ability_rules, weather_override=""))
                projected = float(calculate_move_score(beneficiary, opponent, attack, items, ability_rules, weather_override=weather))
                if projected <= 0:
                    continue
                candidate = (projected, normal, attack)
                if best_attack is None or candidate[0] > best_attack[0]:
                    best_attack = candidate
            if not best_attack:
                continue
            projected, normal, attack = best_attack
            bmove = str(attack.get('Move') or '')
            accurate_weather_move = (weather == 'Rain' and bmove in {'Thunder', 'Hurricane'}) or (weather == 'Hail' and bmove == 'Blizzard')
            instant_solar_move = weather == 'Sun' and bmove in {'Solar Beam', 'Solar Blade'}
            bability = str(beneficiary.get('Ability') or '')
            # The shared calculate_move_score() already applies Sand Force.
            # Applying it again here inflated conditional scores by another
            # 30%, changing weather-plan ranking and explanations.
            # Preserve the pre-existing Solar Power projection separately:
            # it is not yet implemented by the shared damage calculator.
            if weather == 'Sun' and bability == 'Solar Power' and attack.get('Category') == 'Special':
                projected *= 1.5
            speed_ability = _WEATHER_SPEED_ABILITIES.get(str(beneficiary.get('Ability') or ''))
            before_speed = float(get_stat(beneficiary, 'SPE')) * float(get_item_speed_multiplier(beneficiary, items))
            after_speed = before_speed * (2 if speed_ability == weather else 1)
            opponent_speed = float(get_stat(opponent, 'SPE')) * float(get_item_speed_multiplier(opponent, items))
            enemy_weather = _WEATHER_SPEED_ABILITIES.get(str(opponent.get('Ability') or ''))
            if enemy_weather == weather:
                opponent_speed *= 2
            flip = bool(before_speed <= opponent_speed < after_speed)
            # A nominal STAB attack alone isn't enough: weather must deliver a
            # real payoff in damage, Speed, or sand-based defense.
            sand_wall = weather == 'Sandstorm' and 'Rock' in {beneficiary.get('Type1'), beneficiary.get('Type2')}
            benefit = max(projected - normal, 0.0) / max(normal, 1.0)
            # An automatic setter can still be the best immediate attacker even
            # when weather improves accuracy or team utility rather than raw
            # damage. Do not exclude a strong direct matchup just because its
            # chosen attack has no weather damage multiplier.
            direct_weather_lead = (
                entry and beneficiary.get("MemberID") == setter.get("MemberID")
                and projected >= best_direct_score * 0.95
                and float(b_row.get("Ratio") or 0) >= best_direct_ratio * 0.95
            )
            if (benefit < 0.12 and not flip and not sand_wall
                    and not accurate_weather_move and not instant_solar_move
                    and not direct_weather_lead
                    and assumed_weather is None
                    and not ((weather == 'Rain' and fire_pressure >= 2 and fire_pressure > water_pressure)
                             or (weather == 'Sun' and water_pressure >= 2 and water_pressure > fire_pressure))):
                continue
            if assumed_weather is None and beneficiary.get("MemberID") != setter.get("MemberID") and duration - 1 <= 1:
                continue
            # Score the actual opponent's moves under the proposed weather.
            # Rock typing only grants sandstorm defense versus SPECIAL attacks;
            # a physical Water move remains dangerous even in sandstorm.
            opposing_attacks = [m for m in get_moves(opponent, moves_data)
                                if m.get('Category') in {'Physical', 'Special'}]
            projected_incoming = [(m, float(calculate_move_score(
                opponent, beneficiary, m, items, ability_rules, weather_override=weather)))
                                  for m in opposing_attacks]
            worst_weather_move, weather_iws = max(projected_incoming, key=lambda x: x[1],
                                                   default=(None, 0.0))
            baseline_incoming = [(m, float(calculate_move_score(
                opponent, beneficiary, m, items, ability_rules, weather_override='')))
                for m in opposing_attacks]
            worst_baseline_move, baseline_iws = max(
                baseline_incoming, key=lambda x: x[1], default=(None, 0.0))
            # An accuracy-only Rain plan is not an advantage when it mainly
            # strengthens the opposing Water attacks. Compare the opposing
            # damage in rain with neutral conditions before accepting it.
            # Genuine offensive weather boosts can still qualify below.
            if (weather == 'Rain' and accurate_weather_move
                    and projected <= normal * 1.001
                    and any(str(m.get('Type') or '') == 'Water' for m in opposing_attacks)
                    and weather_iws > baseline_iws * 1.05):
                continue
            # A switch must be evaluated under the proposed weather, not only
            # the strategy-neutral matchup (which can include Drizzle/Drought).
            if assumed_weather is None and beneficiary.get("MemberID") != setter.get("MemberID") and weather_iws > 0 and projected / weather_iws < 0.85:
                continue
            max_incoming_hp_damage = 0.0
            for incoming_move in opposing_attacks:
                _, high = calculate_damage_range(opponent, beneficiary, incoming_move,
                                                 items, ability_rules, weather_override=weather)
                if high is not None:
                    max_incoming_hp_damage = max(max_incoming_hp_damage, float(high))
            beneficiary_hp = float(get_stat(beneficiary, 'HP') or 1)
            # The same survival gate applies whether weather must be set or is
            # already reported active. A favorable damage boost cannot make a
            # candidate with a lethal modeled incoming hit a safe weather plan.
            # Keep this eligibility check consistent across both paths; the
            # shared OHKO/ratio selector then ranks the surviving candidates.
            if max_incoming_hp_damage >= beneficiary_hp:
                continue
            # Spending a turn to establish weather and another to switch must
            # produce a real gain over the direct recommendation. Weather
            # utility alone is not an excuse for a weak or exposed attacker.
            switching = beneficiary.get("MemberID") != setter.get("MemberID")
            attack_gain = projected / max(best_direct_score, 1.0)
            weather_ratio_now = projected / max(weather_iws, 1.0)
            # An established-weather attack must earn its extra switch turn.
            # A near-equal attack can still qualify when the weather counters
            # the *opposing team's* dominant damaging type.
            counter_weather = ((weather == 'Rain' and fire_pressure >= 2 and fire_pressure > water_pressure)
                               or (weather == 'Sun' and water_pressure >= 2 and water_pressure > fire_pressure))
            if assumed_weather is None and switching and attack_gain < (0.88 if counter_weather else 1.06):
                continue
            # Compare *every* proposed weather attack with the team's strongest
            # direct offensive AND overall matchup options. Defensive weather
            # alone must not justify a much weaker attack when another member
            # has a stronger, safer offensive solution (e.g. Ice versus Goodra).
            # Keep some tolerance for useful weather accuracy/Speed benefits.
            if (assumed_weather is None and not switching and attack_gain < 0.95
                    and weather_ratio_now < best_direct_ratio * 0.95
                    and not counter_weather):
                continue
            # Weather Ball in hail/sandstorm must not get a free pass when its
            # user takes residual damage. Reward the actual projected payoff.
            incoming_reduction = ((baseline_iws - weather_iws) / max(baseline_iws, 1.0))
            # Raw offensive score and conditional safety matter together.
            # Avoid granting a generic Rock-in-sand reward: the actual incoming
            # damage calculations already incorporate its special-defense boost.
            weather_ratio = projected / max(weather_iws, 1.0)
            offensive_gain = max(projected - normal, 0.0) / max(normal, 1.0)
            # Select among all eligible weather plans by their *actual*
            # offensive payoff and matchup quality relative to the alternatives,
            # not by a capped raw Ratio or defensive improvement alone. This
            # keeps a Rock-in-sand defensive boost from hiding a much better
            # Ice attack against a Dragon opponent.
            relative_offense = projected / max(best_direct_score, 1.0)
            relative_matchup = weather_ratio / max(best_direct_ratio, 0.01)
            # Strong opposing weather pressure is a battle-wide benefit or
            # liability. Rain counters Fire-heavy teams but is a liability
            # against Water-heavy teams, including when the user's own Water
            # attacks are boosted. Likewise, sun suppresses opposing Water.
            weather_field_value = 0.0
            if weather == 'Rain':
                weather_field_value = 1.35 * fire_pressure - 1.65 * water_pressure
            elif weather == 'Sun':
                weather_field_value = 1.35 * water_pressure - 1.65 * fire_pressure
            # Preserve the selection's actual offensive payoff and the
            # attacker's survival in weather; do not let a weather-only bonus
            # rescue a plan that cannot survive its first attack.
            score = (min(relative_offense, 2.5) * 4.0
                     + min(relative_matchup, 2.5) * 3.5
                     + min(offensive_gain, 2.5) * 0.6
                     + max(min(incoming_reduction, 1.0), -1.0) * 1.3
                     + weather_field_value
                     + (0.9 if flip else 0.0)
                     + (0.5 if accurate_weather_move else 0.0)
                     + (0.35 if instant_solar_move else 0.0)
                     + (0.18 if entry else -0.12)
                     - (0.85 if switching and assumed_weather is None else 0))
            candidates.append((score, setter, setup_move, beneficiary, attack, weather,
                               projected, normal, before_speed, after_speed, opponent_speed,
                               flip, duration, sand_wall, baseline_weather,
                               accurate_weather_move, instant_solar_move,
                               weather_iws, baseline_iws, max_incoming_hp_damage,
                               weather_field_value))

    if not candidates:
        return 'No useful, safe weather beneficiary or projected weather payoff is modeled; use the direct matchup.'

    # Compare COMPLETE actions. A setter attacking immediately and a setter
    # handing off to a beneficiary do not consume the same number of turns.
    # Reuse the canonical conditional OHKO note builder (not Move Score alone)
    # when deciding whether a handoff has earned its exposure.
    ohko_order = {"Likely Survival OHKO": 4, "Likely OHKO": 3,
                  "Possible Survival OHKO": 2, "Possible OHKO": 1}
    ohko_cache = {}

    def conditional_ohko(candidate):
        member, move, condition = candidate[3], candidate[4], candidate[5]
        cache_key = (member.get("MemberID") or id(member),
                     str(move.get("Move") or ""), condition)
        if cache_key not in ohko_cache:
            found = _weather_conditional_ohko_notes(
                member, opponent, move, condition, items, ability_rules, moves_data)
            labels = [getattr(note, "text", "") for note in found]
            ohko_cache[cache_key] = max((ohko_order.get(t, 0) for t in labels), default=0)
        return ohko_cache[cache_key]

    # When weather must be established, evaluate handoffs against the
    # setter's actual attack under that SAME resulting weather. An additional
    # exposed switch cannot be justified by a modest score/ratio advantage
    # if the setter already has an equal-or-better knockout opportunity.
    setup_self = {}
    for candidate in candidates:
        if candidate[1].get("MemberID") == candidate[3].get("MemberID"):
            key = (candidate[1].get("MemberID") or id(candidate[1]),
                   candidate[2], candidate[5])
            prior = setup_self.get(key)
            if prior is None or candidate[0] > prior[0]:
                setup_self[key] = candidate
    if assumed_weather is None:
        retained = []
        for candidate in candidates:
            setter, beneficiary = candidate[1], candidate[3]
            if setter.get("MemberID") == beneficiary.get("MemberID"):
                retained.append(candidate)
                continue
            key = (setter.get("MemberID") or id(setter), candidate[2], candidate[5])
            stays = setup_self.get(key)
            if stays is None:
                retained.append(candidate)
                continue
            stays_tier = conditional_ohko(stays)
            switch_tier = conditional_ohko(candidate)
            # A better KO classification or a materially safer matchup can
            # justify the turn; a small offensive improvement alone cannot.
            stays_ratio = stays[6] / max(stays[17], 1.0)
            switch_ratio = candidate[6] / max(candidate[17], 1.0)
            clearly_better = (switch_tier > stays_tier or
                              (stays_tier == 0 and switch_ratio >= stays_ratio * 1.5
                               and candidate[19] < stays[19] * 0.75))
            if clearly_better:
                retained.append(candidate)
        candidates = retained

    # For each attainable setup, rank the surviving candidate beneficiaries
    # through the *same* OHKO-promotion / ratio chooser used by Strongest
    # Matchup. Only its optional weather context differs. The ordinary/raw
    # matchup rows above and the Opponent Card are intentionally untouched.
    setup_groups = {}
    for candidate in candidates:
        _, setter, setup_move, beneficiary, attack, weather, *_ = candidate
        group_key = (setter.get('MemberID') or id(setter), setup_move, weather)
        setup_groups.setdefault(group_key, []).append(candidate)
    shared_ranked_plans = []
    if assumed_weather is not None:
        # One comparison across the WHOLE team, using the same OHKO/ratio
        # promotion as Strongest Matchup. Weather may differ per candidate
        # because Snow Warning, Drizzle, etc. trigger on switch-in.
        pool = []
        per_member_weather = {}
        seen = set()
        for candidate in candidates:
            member = candidate[3]
            mid = member.get('MemberID')
            if mid in seen:
                continue
            seen.add(mid)
            pool.append(member)
            per_member_weather[mid] = candidate[5]
        best_member, shared_matchup, _ = find_best_team_member(
            pool, opponent, items, ability_rules, moves_data,
            weather_by_member=per_member_weather,
        )
        if best_member is not None:
            # In the selected weather, do not let a Ratio-only selection
            # displace a stronger conditional OHKO classification. This is
            # the same conditional evidence displayed in Battle Notes.
            highest_tier = max((conditional_ohko(c) for c in candidates), default=0)
            if highest_tier >= 2:
                finalists = [c for c in candidates if conditional_ohko(c) == highest_tier]
                best_conditional = max(finalists, key=lambda c: c[6] / max(c[17], 1.0))
                best_member = best_conditional[3]
            chosen_id = best_member.get('MemberID')
            eligible = [candidate for candidate in candidates
                        if candidate[3].get('MemberID') == chosen_id]
            if eligible:
                shared_ranked_plans.append(max(eligible, key=lambda row: row[0]))
    else:
        for group_key, group in setup_groups.items():
            weather = group[0][5]
            attacker_pool = []
            seen = set()
            for candidate in group:
                attacker = candidate[3]
                key = attacker.get('MemberID') or id(attacker)
                if key not in seen:
                    seen.add(key)
                    attacker_pool.append(attacker)
            best_member, shared_matchup, _ = find_best_team_member(
                attacker_pool, opponent, items, ability_rules, moves_data,
                weather_override=weather,
            )
            if best_member is None:
                continue
            # Preserve the shared selector's result unless a complete
            # one-Pokémon plan has a superior conditional knockout tier.
            highest_tier = max((conditional_ohko(c) for c in group), default=0)
            if highest_tier >= 2:
                finalists = [c for c in group if conditional_ohko(c) == highest_tier]
                best_member = max(finalists, key=lambda c: c[6] / max(c[17], 1.0))[3]
            selected_id = best_member.get('MemberID') or id(best_member)
            eligible = [candidate for candidate in group
                        if (candidate[3].get('MemberID') or id(candidate[3])) == selected_id]
            if eligible:
                shared_ranked_plans.append(max(eligible, key=lambda row: row[0]))
    if not shared_ranked_plans:
        return 'No supported weather-adjusted attacker survived the setup checks; use the direct matchup.'
    # Cross-weather plan selection must respect the SAME knockout/survival
    # priorities already used within each individual weather proposal.
    # Otherwise a field-utility bonus can override a clearly safer OHKO plan
    # (e.g. Torkoal/Sun over Gigalith/Sandstorm against Pelipper).
    if assumed_weather is None:
        best_ohko_tier = max(conditional_ohko(row) for row in shared_ranked_plans)
        if best_ohko_tier >= 2:
            shared_ranked_plans = [row for row in shared_ranked_plans
                                   if conditional_ohko(row) == best_ohko_tier]
    (score, setter, setup_move, beneficiary, attack, weather, projected, normal,
     before_speed, after_speed, enemy_speed, flip, duration, sand_wall, baseline_weather,
     accurate_weather_move, instant_solar_move, weather_iws, baseline_iws,
     maximum_incoming_damage, field_value) = max(shared_ranked_plans, key=lambda row: row[0])
    setter_species = str(setter.get('Pokemon') or '')
    attacker_species = str(beneficiary.get('Pokemon') or '')
    setter_name = pokemon_display_name(setter)
    attacker_name = pokemon_display_name(beneficiary)
    attack_name = str(attack.get('Move') or '')
    is_switch = setter.get("MemberID") != beneficiary.get("MemberID")
    # Subsequent roster slots are conditional follow-ups, not new openers.
    # We cannot observe live weather: if the original weather has expired,
    # been overridden, or the beneficiary is unavailable, recalculate.
    step = setup_move or f'{setter_name} enters ({setter.get("Ability")})'
    if assumed_weather is not None:
        # A later-roster recommendation describes the attack to make NOW,
        # not the opening setup sequence that created the assumed weather.
        heading = (f'{attacker_name} → {weather} on entry → {attack_name}'
                   if weather != assumed_weather else
                   f'{weather} assumed active → {attacker_name} ({attack_name})')
        lead_move = attack_name
        opening_name = attacker_name
    else:
        heading = f'{setter_name} → {setup_move or weather} → ' + (f'{attacker_name} ({attack_name})' if is_switch else attack_name)
    # When entry weather is automatic, recommending an already-active setter's
    # damaging action as weather setup would falsely spend a move. Use the real
    # attacking move whenever the setter also supplies the payoff.
    # An automatic entry Ability isn't a move. For a cross-team payoff the
    # setter has no commanded action; only self-beneficiaries display an attack.
    if assumed_weather is None:
        lead_move = setup_move or (attack_name if not is_switch else '')
        opening_name = setter_name
    b_row = by_name.get(beneficiary.get("MemberID")) or by_name[attacker_species]
    ratio = float(b_row.get('Ratio') or 0)
    weather_ratio = projected / max(weather_iws, 1.0)
    weather_improvement = baseline_iws > 0 and weather_iws <= baseline_iws * 0.8
    if weather_ratio < 1.0 or maximum_incoming_damage > get_stat(beneficiary, 'HP') * 0.75:
        fit, rank = 'Risky', 1
    elif weather_ratio >= 2.0 and (flip or projected >= normal * 1.25 or weather_improvement):
        fit, rank = 'Strong', 3
    else:
        fit, rank = 'Viable', 2
    speed_note = (f' {attacker_name} Speed {before_speed:.0f} → {after_speed:.0f} versus target {enemy_speed:.0f}; turn order flips.' if flip else '')
    sand_note = (' Sandstorm raises Rock-type Special Defense against special attacks.' if sand_wall else '')
    if abs(projected - normal) < 0.01:
        if accurate_weather_move:
            attack_note = f' {weather} leaves {attack_name} damage unchanged but makes it bypass normal accuracy checks.'
        elif instant_solar_move:
            attack_note = f' {weather} removes {attack_name}’s charging turn without increasing its damage.'
        elif sand_wall:
            attack_note = f' {weather} leaves {attack_name} damage unchanged but boosts Rock-type Special Defense.'
        else:
            attack_note = f' {weather} does not increase {attack_name} damage; its benefit is defensive or positional.'
    else:
        attack_note = ''
    weather_safety_note = (f' Incoming Worst Score against {attacker_name} without weather: '
                           f'{baseline_iws:.2f} versus {weather_iws:.2f} with {weather}. '
                           f'Modeled maximum incoming hit: {maximum_incoming_damage:.0f} '
                           f'of {get_stat(beneficiary, "HP"):.0f} HP.')
    line = ((f'{attacker_name} establishes {weather} on entry, replacing the reported {assumed_weather}; '
              f'use {attack_name} under {weather}. ')
            if assumed_weather is not None and weather != assumed_weather else
            f'{weather} is assumed active for this matchup; use {attack_name} with {attacker_name}. '
            if assumed_weather is not None else
            (f'Step 1: {step}. ' if setup_move else f'Step 1: {setter_name} establishes {weather} on entry via {setter.get("Ability")}. '))
    other_weather = _WEATHER_ABILITIES.get(str(opponent.get('Ability') or ''))
    if setup_move and other_weather and other_weather != weather:
        line += f'{setup_move} replaces the opposing {other_weather} weather. '
    if assumed_weather is None:
        if is_switch:
            line += f'Step 2: switch to {attacker_name}; then use {attack_name} while {weather} remains active. '
        else:
            line += f'Step 2: use {attack_name} while {weather} remains active. '
    accuracy_note = '' if accurate_weather_move and abs(projected - normal) < 0.01 else (' Weather makes this move bypass normal accuracy checks.' if accurate_weather_move else '')
    charge_note = (' Sun removes this move’s charging turn.' if instant_solar_move else '')
    # Show the responsible incoming move on both sides of the projection.
    # The largest post-weather threat may be a different move from the raw one.
    opponent_attacks = [m for m in get_moves(opponent, moves_data)
                        if m.get('Category') in {'Physical', 'Special'}]
    incoming_before = [(str(m.get('Move') or ''), float(calculate_move_score(
        opponent, beneficiary, m, items, ability_rules, weather_override='')))
        for m in opponent_attacks]
    incoming_after = [(str(m.get('Move') or ''), float(calculate_move_score(
        opponent, beneficiary, m, items, ability_rules, weather_override=weather)))
        for m in opponent_attacks]
    raw_worst = max(incoming_before, key=lambda row: row[1], default=None)
    adjusted_worst = max(incoming_after, key=lambda row: row[1], default=None)
    # Compare the worst threat in each state, rather than implying that
    # rain/sun changed the damage of a move that is unaffected by weather.
    # Scores and the responsible moves come from the same per-move results.
    if raw_worst and adjusted_worst:
        if raw_worst[0] != adjusted_worst[0]:
            threat_explanation = (
                f' Worst Incoming Move: {raw_worst[0]} ({raw_worst[1]:.2f})'
                f' → {adjusted_worst[0]} ({adjusted_worst[1]:.2f}) under {weather}.')
        else:
            threat_explanation = (
                f' Incoming Worst Score: {raw_worst[1]:.2f}'
                f' → {adjusted_worst[1]:.2f} '
                f'({adjusted_worst[0]}, under {weather}).')
    else:
        threat_explanation = ''
    line += (f'Projected {attack_name} Move Score: {normal:.2f} → {projected:.2f} in {weather}.'
             f'{attack_note}{speed_note}{sand_note}'
             f'{threat_explanation} '
             f'Maximum modeled hit {maximum_incoming_damage:.0f}/{get_stat(beneficiary, "HP"):.0f} HP.'
             f'{accuracy_note}{charge_note} '
             f'Weather lasts up to {duration} turns; switching uses one turn.')
    condition = (f'Assumes {weather} is active and not overridden; Battle Compass cannot verify remaining turns. '
                 'If the weather changes or expires, use the direct matchup or re-establish weather.')
    # The fit meter gets a short role/viability explanation. Matchup-specific
    # evidence is passed separately to the shared Why? builder.
    fit_summary = (
        f'{weather} beneficiary; projected matchup is {fit.lower()}.'
        if assumed_weather is not None else
        f'{weather} setter; projected follow-up is {fit.lower()}.'
    )
    rationales = []
    from engine.mechanics import get_type_multiplier, get_effective_pokemon_types
    effective_attack_type = str(attack.get('Type') or '')
    if attack_name == 'Weather Ball':
        effective_attack_type = {'Rain': 'Water', 'Sun': 'Fire',
                                 'Hail': 'Ice', 'Sandstorm': 'Rock'}.get(weather, effective_attack_type)
    attack_effectiveness = get_type_multiplier(effective_attack_type, get_effective_pokemon_types(opponent))
    # Explain the winning tradeoff, not merely that the attack is available.
    chosen_tier = conditional_ohko(max(shared_ranked_plans, key=lambda row: row[0]))
    tier_names = {4: 'Likely Survival OHKO', 3: 'Likely OHKO',
                  2: 'Possible Survival OHKO', 1: 'Possible OHKO'}
    if is_switch:
        rationales.append(f'{setter_name} establishes {weather}, then a switch to {attacker_name} costs an exposed turn.')
    elif assumed_weather is not None and weather != assumed_weather:
        rationales.append(f'{attacker_name} replaces {assumed_weather} with {weather} on entry and attacks immediately.')
    elif assumed_weather is not None:
        rationales.append(f'With {weather} already active, {attacker_name} can attack immediately; no extra weather setup is needed.')
    else:
        rationales.append(f'{setter_name} establishes {weather} on entry and attacks immediately without a handoff.')
    if chosen_tier:
        rationales.append(f'{attack_name} has a {tier_names[chosen_tier]} projection.')
    # Compare the closest viable alternative under the same resulting weather.
    # This gives Why? a decisive reason without guessing which member is active.
    alternatives = [c for c in candidates
                    if c[3].get('MemberID') != beneficiary.get('MemberID')
                    and c[5] == weather]
    if alternatives:
        runner = max(alternatives, key=lambda c: (conditional_ohko(c), c[6] / max(c[17], 1.0)))
        other = pokemon_display_name(runner[3])
        other_tier = conditional_ohko(runner)
        if chosen_tier > other_tier:
            rationales.append(f'{other} has a weaker projected knockout opportunity ({tier_names.get(other_tier, "no modeled OHKO")}).')
        elif not is_switch and runner[1].get('MemberID') != runner[3].get('MemberID'):
            rationales.append(f'{other} requires an additional exposed switch turn without a stronger projected OHKO.')
        else:
            chosen_ratio = projected / max(weather_iws, 1.0)
            other_ratio = runner[6] / max(runner[17], 1.0)
            if chosen_ratio >= other_ratio:
                rationales.append(f'{attacker_name} has the better weather-adjusted attack-to-threat ratio than {other} ({chosen_ratio:.2f} versus {other_ratio:.2f}).')
    if attack_effectiveness > 1:
        rationales.append(f'{attack_name} is super effective against {str(opponent.get("Pokemon") or "the opponent")}.')
    if field_value >= 1.0 and weather == 'Rain':
        rationales.append('Rain weakens the opposing team’s Fire attacks and strengthens Water attacks.')
    elif field_value >= 1.0 and weather == 'Sun':
        rationales.append('Sun weakens the opposing team’s Water attacks and strengthens Fire attacks.')
    if projected > normal * 1.05:
        rationales.append(f'{weather} improves the projected score of {attack_name}.')
    elif accurate_weather_move:
        rationales.append(f'{weather} makes {attack_name} bypass its normal accuracy checks.')
    elif sand_wall and weather_iws < baseline_iws * 0.95:
        rationales.append(f'Sandstorm reduces incoming special-attack pressure on {attacker_name}.')
    return dict(
        member_id=(beneficiary.get("MemberID") if assumed_weather is not None else setter.get("MemberID")),
        setter_member_id=setter.get("MemberID"), payoff_member_id=beneficiary.get("MemberID"),
        pokemon_name=opening_name, recommended_pokemon_name=opening_name,
        lead_pokemon_name=(attacker_name if assumed_weather is not None else setter_name),
        lead_move=lead_move, fit=fit, fit_rank=rank, summary=heading, reason=line,
        action=(f'Continue under {weather} with {attacker_name}' if assumed_weather is not None else f'Establish {weather} with {setter_name}'), action_detail=line,
        plan_kind=('weather_followup' if assumed_weather is not None else
                   'weather_setup' if setup_move or is_switch else 'weather_entry_payoff'),
        can_override_direct=True,
        opener_threat_move=str((by_name.get(setter.get("MemberID")) or by_name[setter_species]).get('Worst Incoming Move') or '') or None,
        opener_threat_category=str((by_name.get(setter.get("MemberID")) or by_name[setter_species]).get('Worst Incoming Move Category') or '') or None,
        opener_threat_type=str((by_name.get(setter.get("MemberID")) or by_name[setter_species]).get('Worst Incoming Move Type') or '') or None,
        opener_threat_score=float((by_name.get(setter.get("MemberID")) or by_name[setter_species]).get('Incoming Worst Score') or 0),
        opener_threat_multiplier=float((by_name.get(setter.get("MemberID")) or by_name[setter_species]).get('Incoming Multiplier') or 1),
        strategy_branch='weather_control', action_type=('Weather Payoff' if assumed_weather is not None else
            'Weather Setup' if setup_move else 'Weather Payoff' if not is_switch else 'Automatic Weather'),
        plan_role=('Weather Beneficiary' if assumed_weather is not None else
                   'Weather Setter' if setup_move or is_switch else 'Weather Beneficiary'),
        fit_explanation=fit_summary,
        weather_why_evidence=' '.join(rationales),
        attack_move_score=(projected if lead_move == attack_name else None),
        attack_score_conditional=(lead_move == attack_name),
        sequence_heading=heading, state_assumption=('Assumes the lead weather remains active; verify the field.'
            if assumed_weather is not None else 'No manual weather is assumed active before setup.'),
        fallback_if_assumption_fails='If weather setup is unsafe or weather expires, use the direct fallback.',
        condition_detail=condition if assumed_weather is not None or (not setup_move and not is_switch) else '',
    )


def _weather_conditional_ohko_notes(member, opponent, move, weather, items, ability_rules, moves_data):
    """Use the canonical OHKO note builder with the projected move and weather.

    Does not change the neutral Full Analysis or recommendation thresholds.
    """
    from engine.calculations import (calculate_damage_range, calculate_move_score,
                                     AVERAGE_OPPONENT_IV, get_weather_speed_multiplier)
    from engine.mechanics import get_item_speed_multiplier
    from engine.notes import build_offensive_ohko_note, build_incoming_ohko_note

    low, high = calculate_damage_range(member, opponent, move, items, ability_rules,
                                       weather_override=weather)
    possible_low, possible_high = calculate_damage_range(
        member, opponent, move, items, ability_rules,
        defender_opponent_iv_override=AVERAGE_OPPONENT_IV,
        weather_override=weather)
    attacks = [m for m in get_moves(opponent, moves_data)
               if m.get('Category') in {'Physical', 'Special'}]
    scored = [(float(calculate_move_score(opponent, member, m, items, ability_rules,
                                          weather_override=weather)), m) for m in attacks]
    worst_score, worst_move = max(scored, key=lambda pair: pair[0], default=(0.0, None))
    incoming_low = incoming_high = None
    if worst_move is not None:
        incoming_low, incoming_high = calculate_damage_range(
            opponent, member, worst_move, items, ability_rules, weather_override=weather)
    our_speed = float(get_stat(member, 'SPE')) * get_item_speed_multiplier(member, items) * get_weather_speed_multiplier(member, weather)
    their_speed = float(get_stat(opponent, 'SPE')) * get_item_speed_multiplier(opponent, items) * get_weather_speed_multiplier(opponent, weather)
    # Use the same Speed tie handling as the existing shared OHKO evaluator.
    moves_second = our_speed < their_speed
    hp = float(get_stat(member, 'HP') or 0)
    target_hp = float(get_stat(opponent, 'HP') or 0)
    from engine.calculations import get_opponent_dmax_note
    if get_opponent_dmax_note(opponent):
        target_hp *= 2
    possible_hp = float(get_stat(opponent, 'HP', AVERAGE_OPPONENT_IV) or 0)
    if get_opponent_dmax_note(opponent):
        possible_hp *= 2
    off = build_offensive_ohko_note(
        low, high, target_hp, possible_low, possible_high, possible_hp,
        moves_second, incoming_low is None or incoming_low < hp, worst_score > 0)
    inc = build_incoming_ohko_note(worst_score == 0, incoming_low, incoming_high, hp)
    return [BattleNoteViewModel(icon=NOTE_ICONS.get(n.get('category', 'info'), '•'),
                                category=n.get('category', 'info'), text=n.get('text', ''))
            for n in (off, inc) if n is not None]



def build_battle_compass_view_model(
    *,
    team_data: list[dict],
    opponent: dict,
    items: list[dict],
    ability_rules: list[dict],
    moves_data: list[dict],
    team_strategy: str = "strongest_matchup",
    battle_roster: list[dict] | None = None,
    current_weather: str | None = None,
) -> BattleCompassViewModel:
    """Run the battle engine and return display-ready matchup results."""
    strategy_capabilities: list[StrategyCapabilityViewModel] = []
    if team_strategy != "strongest_matchup":
        strategy_capabilities = [
            StrategyCapabilityViewModel(
                pokemon_name=result.pokemon_name,
                capabilities=result.capabilities,
            )
            for result in recognize_team_capabilities(team_data, moves_data)
        ]
    recommended_pokemon, _, direct_why_text = find_best_team_member(
        team_data,
        opponent,
        items,
        ability_rules,
        moves_data,
    )
    if recommended_pokemon is None:
        return BattleCompassViewModel(
            opponent=opponent,
            recommendation=None,
            why_text="",
            other_options=[],
            all_matchups=[],
            team_strategy=team_strategy,
            strategy_capabilities=strategy_capabilities,
            empty_state_message=(
                direct_why_text
                or "No battle recommendation is available yet. Add at least one usable "
                "damaging move to your team, save the team, and return to the Battle "
                "Compass. An opponent's type, Ability, or held item may completely block "
                "a move."
            ),
        )
    matchup_results = evaluate_team_matchups(
        team_data,
        opponent,
        items,
        ability_rules,
        moves_data,
    )
    move_lookup = _build_move_lookup(moves_data)
    # Matchup results belong to individual party members, not species names.
    # The calculation engine preserves team order, including duplicate species.
    members_by_id = {p.get("MemberID"): p for p in team_data
                     if isinstance(p, dict) and p.get("MemberID")}
    usable_members = [p for p in team_data if isinstance(p, dict)
                      and p.get("Pokemon") and any(str(p.get(f"Move{i}") or "")
                      for i in range(1, 5))]
    all_matchups = []
    for result in matchup_results:
        original = members_by_id.get(result.get("MemberID"))
        if original is None:
            original = next((p for p in usable_members if p.get("Pokemon") == result.get("Pokemon")
                             and p not in [m.pokemon for m in all_matchups]), None)
        if original is not None:
            all_matchups.append(_build_matchup_view_model(
                result=result, pokemon=original, move_lookup=move_lookup))
    matchup_lookup = {m.pokemon.get("MemberID"): m for m in all_matchups
                      if m.pokemon.get("MemberID")}
    direct_name = pokemon_display_name(recommended_pokemon)
    recommendation = matchup_lookup.get(recommended_pokemon.get("MemberID"))
    if recommendation is None:
        recommendation = next((m for m in all_matchups if m.pokemon is recommended_pokemon
                               or m.pokemon == recommended_pokemon), None)
    direct_move_name = recommendation.best_move.get("Move") if recommendation else None
    if recommendation is None:
        return BattleCompassViewModel(
            opponent=opponent,
            recommendation=None,
            why_text="",
            other_options=[],
            all_matchups=all_matchups,
            team_strategy=team_strategy,
            strategy_capabilities=strategy_capabilities,
            direct_recommendation_name=direct_name or None,
            empty_state_message=(
                "The team could not produce a usable recommendation for this opponent. "
                "Check that at least one saved team member has a valid damaging move."
            ),
        )
    def select_strategy_member(name: str, action: str = "") -> MatchupViewModel | None:
        choices = [m for m in all_matchups if m.pokemon.get("Pokemon") == name]
        if action:
            equipped = [m for m in choices if action in {
                str(m.pokemon.get(f"Move{i}") or "") for i in range(1, 5)}]
            if equipped:
                choices = equipped
        if len(choices) == 1:
            return choices[0]
        # Never credit one same-species teammate with another's tactical plan.
        # Leave the direct recommendation intact if the strategy is ambiguous.
        return None

    why_text = direct_why_text
    strategy_plans: list[StrategyPlanViewModel] = []
    selected_strategy_plan: StrategyPlanViewModel | None = None
    fallback_reason: str | None = None
    anti_setup = (
        _anti_setup_interception(team_data, opponent, matchup_results, moves_data, items, ability_rules)
        # Setup Offense must evaluate its complete, survival-gated lead plan
        # before a generic immediate-KO interception can override it. The
        # setup evaluator itself models lethal opponent boost follow-ups.
        # Keep the existing interception behavior for other strategies.
        if team_strategy not in {"strongest_matchup", "setup_offense"}
        # Screen Control's later opponents are *attacker follow-ups*, not
        # opportunities to start a fresh screen-setting sequence. An enemy
        # setup move alone must not discard a planned protected attacker.
        # Lead interception remains available before screens are established.
        and (team_strategy != "screen_control"
             or str(opponent.get("Slot") or "") in {"1", "1.0"})
        and not _force_strongest_matchup_for_known_doubles(opponent)
        and not _opponent_is_dynamaxed(opponent)
        else None
    )
    if anti_setup is not None:
        intercept_id, intercept_move, enemy_setup, accuracy = anti_setup
        intercept_matchup = matchup_lookup.get(intercept_id)
        if intercept_matchup is not None:
            recommendation = intercept_matchup
            intercept_name = pokemon_display_name(intercept_matchup.pokemon)
            fallback_reason = (
                f"Anti-setup interception: {opponent.get('Pokemon', 'the opponent')} knows {enemy_setup}, "
                f"which could sharply increase its offensive threat. "
                f"{intercept_name} can knock it out immediately with {intercept_move} "
                f"(modeled minimum damage reaches its HP; move accuracy {accuracy:g}%). "
                "Attack now rather than spend a turn setting up. The selected strategy remains active."
            )
            # Why? is composed once by the shared explanation builder.
    elif team_strategy in {"poison_attrition", "poison_offensive_pressure"}:
        if _force_strongest_matchup_for_known_doubles(opponent):
            fallback_reason = (
                "This is a Double Battle. Battle Compass currently models single-opponent tactical states, so strategy-specific recommendations are disabled here and Strongest Matchup is being used instead."
            )
            # Why? is composed once by the shared explanation builder.
        else:
            raw_plans = evaluate_poison_attrition_plans(
                team_data, opponent, moves_data, matchup_results, battle_roster=battle_roster,
                items=items, ability_rules=ability_rules, strategy_branch=team_strategy,
            )
            strategy_plans = [
                StrategyPlanViewModel(
                    pokemon_name=plan.pokemon_name, fit=plan.fit, fit_rank=plan.fit_rank, summary=plan.summary,
                    reason=plan.reason, action=plan.action, action_detail=plan.action_detail, plan_kind=plan.plan_kind,
                    can_override_direct=plan.can_override_direct, lead_pokemon_name=plan.lead_pokemon_name,
                    lead_move=plan.lead_move, opener_threat_move=plan.opener_threat_move,
                    opener_threat_category=plan.opener_threat_category, opener_threat_type=plan.opener_threat_type,
                    opener_threat_score=plan.opener_threat_score, opener_threat_multiplier=plan.opener_threat_multiplier,
                    strategy_branch=plan.strategy_branch, assumed_poisoned=plan.assumed_poisoned,
                    state_assumption=plan.state_assumption, fallback_if_assumption_fails=plan.fallback_if_assumption_fails,
                    recommended_pokemon_name=plan.recommended_pokemon_name, conditional_move_name=plan.conditional_move_name,
                    conditional_move_score=plan.conditional_move_score,
                    member_id=plan.recommended_member_id or plan.member_id,
                    setter_member_id=plan.lead_member_id,
                    payoff_member_id=plan.followup_member_id,
                )
                for plan in raw_plans
            ]
            selected_raw_plan = select_poison_attrition_plan(raw_plans, matchup_results)
            is_dynamaxed = _opponent_is_dynamaxed(opponent)
            allow_dmax_poison_plan = False
            if is_dynamaxed and selected_raw_plan is not None and team_strategy == "poison_offensive_pressure":
                direct_result = next((row for row in matchup_results if row.get("MemberID") == recommended_pokemon.get("MemberID")), None)
                direct_score = float(direct_result.get("Best MoveScore") or 0.0) if direct_result else 0.0
                conditional_score = float(selected_raw_plan.conditional_move_score or 0.0)
                allow_dmax_poison_plan = (
                    selected_raw_plan.plan_kind == "followup_assumed_poison"
                    and selected_raw_plan.assumed_poisoned
                    and conditional_score > 0
                    and conditional_score >= direct_score * 1.25
                )
            if is_dynamaxed and not allow_dmax_poison_plan:
                fallback_reason = (
                    "This opponent is Dynamaxed or Gigantamaxed. Because Max moves add secondary effects and other battle-state variables, Battle Compass is conservatively falling back to Strongest Matchup unless an already-active Poison line is materially stronger."
                )
                # Why? is composed once by the shared explanation builder.
            elif selected_raw_plan is not None:
                # Select the exact engine plan object, never a same-named species.
                selected_index = next(i for i, raw in enumerate(raw_plans)
                                      if raw is selected_raw_plan)
                selected_strategy_plan = strategy_plans[selected_index]
                poison_kind = selected_strategy_plan.plan_kind
                move_name = str(selected_strategy_plan.lead_move or "")
                move_lookup = _build_move_lookup(moves_data)
                move_record = move_lookup.get(move_name, {})
                attack = (str(move_record.get("Category") or "") in {"Physical", "Special"}
                          and float(move_record.get("Power") or 0) > 0)
                recovery = move_name in {"Recover", "Roost", "Slack Off", "Soft-Boiled", "Rest", "Synthesis", "Moonlight", "Morning Sun", "Shore Up", "Milk Drink"}
                defensive = move_name in {"Baneful Bunker", "Obstruct", "Protect", "Detect", "King's Shield", "Spiky Shield", "Iron Defense", "Amnesia", "Cosmic Power", "Stockpile", "Calm Mind"}
                poison_setup_move = move_name in {"Toxic", "Toxic Spikes", "Poison Gas"}
                assumed_poison = bool(selected_strategy_plan.assumed_poisoned)
                payoff = (attack and assumed_poison
                          and selected_strategy_plan.conditional_move_score is not None)
                if recovery or defensive:
                    action_type, plan_role = "Attrition", "Attrition Anchor"
                elif poison_setup_move:
                    action_type, plan_role = "Poison Setup", "Poison Setter"
                elif payoff:
                    action_type, plan_role = "Poison Payoff", "Poison Punisher"
                elif attack:
                    action_type, plan_role = "Direct Attack", "Direct Attacker"
                elif "setup" in poison_kind or "toxic" in poison_kind:
                    action_type, plan_role = "Poison Setup", "Poison Setter"
                else:
                    action_type, plan_role = "Attrition", "Attrition Anchor"
                raw_fit = selected_strategy_plan.fit
                fit = "Unsafe" if raw_fit == "Blocked" else raw_fit
                if recovery or defensive:
                    fit_reason = (f"{move_name} sustains the defensive plan. "
                                  "Use it when healing or protection is needed; reassess incoming threats.")
                elif payoff:
                    fit_reason = (f"{move_name} exploits the assumed poison state. "
                                  "Use the direct fallback if poison is absent.")
                elif poison_setup_move:
                    fit_reason = (f"{move_name} establishes poison pressure. "
                                  "Use the direct fallback if setup is unsafe.")
                else:
                    fit_reason = ("The tactical plan balances matchup safety with poison pressure. "
                                  "Use the direct fallback if conditions change.")
                condition_detail = (
                    "Assumes the opponent was poisoned on an earlier turn and is still poisoned. "
                    "Battle Compass cannot verify live status; if poison is absent, use the named direct fallback."
                    if payoff else ""
                )
                selected_strategy_plan = replace(
                    selected_strategy_plan, fit=fit,
                    action_type=action_type, plan_role=plan_role,
                    fit_explanation=fit_reason,
                    condition_detail=condition_detail,
                    attack_move_score=selected_strategy_plan.conditional_move_score if payoff else None,
                    attack_score_conditional=payoff,
                )
                recommended_name = selected_raw_plan.recommended_pokemon_name or selected_raw_plan.lead_pokemon_name or selected_raw_plan.pokemon_name
                strategy_matchup = (
                    matchup_lookup.get(selected_raw_plan.recommended_member_id)
                    if selected_raw_plan.recommended_member_id else
                    select_strategy_member(recommended_name, selected_strategy_plan.lead_move)
                )
                if strategy_matchup is not None:
                    recommendation = strategy_matchup
                poisoned_followup = None
                if opponent.get("Slot") != 1 and not selected_strategy_plan.assumed_poisoned:
                    poisoned_followup = project_poisoned_followup(
                        team_data, opponent, moves_data, matchup_results, items=items, ability_rules=ability_rules,
                        strategy_branch=team_strategy,
                        current_pokemon_name=(selected_raw_plan.recommended_member_id or recommended_name),
                    )
                # Why? is composed once by the shared explanation builder.
            else:
                fallback_reason = describe_poison_attrition_fallback(
                    team_data, opponent, moves_data, matchup_results, items=items, ability_rules=ability_rules,
                    strategy_branch=team_strategy,
                )
                # Why? is composed once by the shared explanation builder.
    elif team_strategy == "status_control_punish":
        if _force_strongest_matchup_for_known_doubles(opponent) or _opponent_is_dynamaxed(opponent):
            fallback_reason = "Status Control & Punish falls back to direct offense for modeled doubles and Dynamax encounters."
            # Why? is composed once by the shared explanation builder.
        else:
            status_result, payoff = _status_control_battle_plan(
                team_data, opponent, matchup_results, moves_data, items, ability_rules
            )
            if status_result is None:
                fallback_reason = payoff
                # Why? is composed once by the shared explanation builder.
            else:
                selected_strategy_plan = StrategyPlanViewModel(**status_result)
                strategy_plans = [selected_strategy_plan]
                recommendation = (matchup_lookup.get(selected_strategy_plan.member_id)
                                  or select_strategy_member(selected_strategy_plan.pokemon_name,
                                                            selected_strategy_plan.lead_move)
                                  or recommendation)
                # Why? is composed once by the shared explanation builder.
    elif team_strategy == "defensive_attrition":
        if _force_strongest_matchup_for_known_doubles(opponent) or _opponent_is_dynamaxed(opponent):
            fallback_reason = "Defensive Attrition uses Strongest Matchup for modeled doubles and Dynamax opponents."
            # Why? is composed once by the shared explanation builder.
        else:
            contact_candidate = _contact_punishment_plan(team_data, opponent, matchup_results, moves_data, items, ability_rules)
            defensive_result = _defensive_attrition_battle_plan(team_data, opponent, matchup_results, moves_data, items, ability_rules)
            # Prefer contact punishment when the opposing damaging moveset is
            # entirely contact-based; neither plan assumes a live battle state.
            if contact_candidate is not None and (isinstance(defensive_result, str) or
                    contact_candidate[0] >= 3.0):
                defensive_result = contact_candidate[1]
            if isinstance(defensive_result, str):
                fallback_reason = defensive_result
                # Why? is composed once by the shared explanation builder.
            else:
                selected_strategy_plan = StrategyPlanViewModel(**defensive_result)
                strategy_plans = [selected_strategy_plan]
                recommendation = (matchup_lookup.get(selected_strategy_plan.member_id)
                                  or select_strategy_member(selected_strategy_plan.pokemon_name,
                                                            selected_strategy_plan.lead_move)
                                  or recommendation)
                # Why? is composed once by the shared explanation builder.
    elif team_strategy == "weather_control":
        weather_advice = _weather_battle_advice(team_data, opponent, items, battle_roster, moves_data)
        if _force_strongest_matchup_for_known_doubles(opponent) or _opponent_is_dynamaxed(opponent):
            fallback_reason = "Weather Control uses Strongest Matchup for modeled doubles and Dynamax opponents."
            fallback_reason += " Weather outlook: " + weather_advice
            # Why? is composed once by the shared explanation builder.
        else:
            # Never infer weather from a hypothetical prior opponent order.
            # Current Weather is explicit battle state supplied by the view.
            # The known lead is the strategic opening anchor. Its setter and
            # attacker must be selected from the same opening conditions even
            # after the player reports the weather created by that recommendation.
            # Current Weather informs later opponents, not a retroactive rewrite
            # of the lead plan. The selected setter's own weather is still
            # evaluated by _weather_control_battle_plan below.
            is_known_lead = str(opponent.get("Slot") or "") in {"1", "1.0"}
            assumed_weather = (
                None if is_known_lead else
                current_weather if current_weather in _WEATHER_EXTENSION_ITEMS else None
            )
            # Unspecified weather may conditionally inherit only the KNOWN
            # lead's recommendation, never hypothetical intermediate opponents.
            # This is computed afresh from the same inputs on every navigation;
            # selecting "No weather" explicitly disables the assumption.
            if current_weather is None and str(opponent.get("Slot") or "") not in {"1", "1.0"}:
                leader = next((row for row in (battle_roster or [])
                               if isinstance(row, dict)
                               and str(row.get("Slot") or "") in {"1", "1.0"}), None)
                if leader is not None:
                    lead_model = build_battle_compass_view_model(
                        team_data=team_data, opponent=leader, items=items,
                        ability_rules=ability_rules, moves_data=moves_data,
                        team_strategy="weather_control", battle_roster=battle_roster,
                        current_weather="None",
                    )
                    picked = lead_model.recommendation.pokemon if lead_model.recommendation else {}
                    assumed_weather = _WEATHER_ABILITIES.get(str(picked.get("Ability") or ""))
                    if assumed_weather is None and lead_model.selected_strategy_plan:
                        lead_move = str(lead_model.selected_strategy_plan.lead_move or "")
                        assumed_weather = _WEATHER_MOVES.get(lead_move)
            result = _weather_control_battle_plan(
                team_data, opponent, matchup_results, moves_data, items, ability_rules,
                battle_roster=battle_roster, assumed_weather=assumed_weather)
            if isinstance(result, str):
                fallback_reason = result + " Weather outlook: " + weather_advice
                # Why? is composed once by the shared explanation builder.
            else:
                # The player-selected weather is the calculation context, not a
                # command to stop giving weather advice. Compare independent
                # alternative plans using this same planner and shared matchup
                # selector; don't alter the reported battlefield condition.
                if assumed_weather is not None:
                    # Compare the SAME attacker's SAME move in both weather
                    # states. Comparing two independent plans' top scores can
                    # falsely credit weather with differences caused by a
                    # different candidate, attack, or setup choice.
                    actor_id = result.get("payoff_member_id")
                    attack_name = str(result.get("lead_move") or "")
                    actor = next((member for member in team_data
                                  if member.get("MemberID") == actor_id), None)
                    attack = next((move for move in get_moves(actor, moves_data)
                                   if str(move.get("Move") or "") == attack_name), None) if actor else None
                    if actor is not None and attack is not None:
                        current_score = float(calculate_move_score(
                            actor, opponent, attack, items, ability_rules,
                            weather_override=assumed_weather))
                        options = []
                        for alternative in ("Rain", "Sun", "Hail", "Sandstorm"):
                            if alternative == assumed_weather:
                                continue
                            if not any(
                                _WEATHER_ABILITIES.get(str(member.get("Ability") or "")) == alternative
                                or any(_WEATHER_MOVES.get(str(move.get("Move") or "")) == alternative
                                       for move in get_moves(member, moves_data))
                                for member in team_data
                            ):
                                continue
                            new_score = float(calculate_move_score(
                                actor, opponent, attack, items, ability_rules,
                                weather_override=alternative))
                            # The calculator's Move Score is a damage-based
                            # projection; guaranteed-hit benefits are evaluated
                            # separately, rather than inventing a damage boost.
                            accuracy_gain = (
                                (alternative == "Rain" and attack_name in {"Thunder", "Hurricane"})
                                or (alternative == "Hail" and attack_name == "Blizzard")
                            ) and not (
                                (assumed_weather == "Rain" and attack_name in {"Thunder", "Hurricane"})
                                or (assumed_weather == "Hail" and attack_name == "Blizzard")
                            )
                            damage_gain = (current_score > 0 and new_score > current_score * 1.20)
                            # Only advertise a Speed Ability when its weather
                            # changes which Pokémon actually attacks first.
                            # Reuse the same weather Speed multipliers as the
                            # shared OHKO/turn-order calculator.
                            from engine.calculations import get_weather_speed_multiplier
                            from engine.mechanics import get_item_speed_multiplier
                            actor_speed = float(get_stat(actor, "SPE")) * float(get_item_speed_multiplier(actor, items))
                            foe_speed = float(get_stat(opponent, "SPE")) * float(get_item_speed_multiplier(opponent, items))
                            current_ours = actor_speed * get_weather_speed_multiplier(actor, assumed_weather)
                            current_foe = foe_speed * get_weather_speed_multiplier(opponent, assumed_weather)
                            projected_ours = actor_speed * get_weather_speed_multiplier(actor, alternative)
                            projected_foe = foe_speed * get_weather_speed_multiplier(opponent, alternative)
                            speed_gain = bool(
                                _WEATHER_SPEED_ABILITIES.get(str(actor.get("Ability") or "")) == alternative
                                and current_ours <= current_foe
                                and projected_ours > projected_foe
                            )
                            if damage_gain or accuracy_gain or speed_gain:
                                # Preserve existing damage/accuracy priority;
                                # speed-only advisories fill the previous gap.
                                options.append((int(accuracy_gain), int(damage_gain),
                                                new_score / max(current_score, 1.0),
                                                alternative, damage_gain, accuracy_gain,
                                                speed_gain, current_ours, current_foe,
                                                projected_ours, projected_foe))
                        if options:
                            (_, _, _, alt_weather, damage_gain, accuracy_gain,
                             speed_gain, speed_before, foe_before,
                             speed_after, foe_after) = max(options)
                            if accuracy_gain:
                                benefit = f"makes {attack_name} bypass its normal accuracy check"
                            elif damage_gain:
                                benefit = (
                                    f"raises {attack_name}'s projected Move Score from "
                                    f"{current_score:.2f} to "
                                    f"{float(calculate_move_score(actor, opponent, attack, items, ability_rules, weather_override=alt_weather)):.2f}"
                                )
                            else:
                                benefit = (
                                    f"activates {actor.get('Ability')}, increasing "
                                    f"{actor.get('Pokemon') or actor.get('Species') or 'the attacker'}'s effective Speed "
                                    f"from {speed_before:g} to {speed_after:g} "
                                    f"and allowing it to outspeed {opponent.get('Pokemon', 'the opponent')} "
                                    f"(effective Speed {foe_after:g})"
                                )
                            result["action_detail"] = (
                                f"**Weather opportunity: {alt_weather} may help {attack_name}.** "
                                f"For the same attacker, {alt_weather} {benefit}. "
                                f"Changing weather requires a setup move or switch-in; "
                                f"the plan below still uses your selected {assumed_weather}. "
                                + result["action_detail"]
                            )
                result["action_detail"] += " Weather outlook: " + weather_advice
                selected_strategy_plan = StrategyPlanViewModel(**result)
                strategy_plans = [selected_strategy_plan]
                recommendation = (matchup_lookup.get(selected_strategy_plan.member_id)
                                  or select_strategy_member(selected_strategy_plan.pokemon_name,
                                                            selected_strategy_plan.lead_move)
                                  or recommendation)
                # Why? is composed once by the shared explanation builder.
    elif team_strategy == "setup_offense":
        if _force_strongest_matchup_for_known_doubles(opponent) or _opponent_is_dynamaxed(opponent):
            fallback_reason = "Setup Offense uses Strongest Matchup for modeled doubles and Dynamax opponents."
            # Why? is composed once by the shared explanation builder.
        else:
            setup_result = _setup_offense_battle_plan(team_data, opponent, matchup_results, moves_data, items, ability_rules, battle_roster=battle_roster)
            if isinstance(setup_result, str):
                fallback_reason = setup_result
                # Report a known immediate interception only when the plan
                # failed safety/utility. Never let it preempt a safe plan.
                if str(opponent.get("Slot") or "") in {"1", "1.0"}:
                    intercept = _anti_setup_interception(
                        team_data, opponent, matchup_results, moves_data,
                        items, ability_rules,
                    )
                    if intercept is not None:
                        intercept_id, intercept_move, enemy_setup, accuracy = intercept
                        intercept_matchup = matchup_lookup.get(intercept_id)
                        if intercept_matchup is not None:
                            recommendation = intercept_matchup
                            intercept_name = pokemon_display_name(intercept_matchup.pokemon)
                            fallback_reason = (
                                f"{setup_result} Anti-setup option: "
                                f"{opponent.get('Pokemon', 'the opponent')} knows {enemy_setup}; "
                                f"{intercept_name} has a modeled immediate KO with "
                                f"{intercept_move} ({accuracy:g}% accuracy)."
                            )
                # Why? is composed once by the shared explanation builder.
            elif setup_result is None:
                fallback_reason = "No supported offensive setup found; use Strongest Matchup."
                # Why? is composed once by the shared explanation builder.
            else:
                selected_strategy_plan = StrategyPlanViewModel(**setup_result)
                strategy_plans = [selected_strategy_plan]
                recommendation = (matchup_lookup.get(selected_strategy_plan.member_id)
                                  or select_strategy_member(selected_strategy_plan.pokemon_name,
                                                            selected_strategy_plan.lead_move)
                                  or recommendation)
                # Why? is composed once by the shared explanation builder.
    elif team_strategy == "screen_control":
        if _force_strongest_matchup_for_known_doubles(opponent) or _opponent_is_dynamaxed(opponent):
            fallback_reason = (
                "Screen Control's single-opponent sequence is not modeled safely for "
                "this Double Battle or Dynamax opponent; Strongest Matchup is used."
            )
            # Why? is composed once by the shared explanation builder.
        else:
            screen_plan, screen_name, screen_fallback = _screen_control_battle_plan(
                team_data, opponent, matchup_results, moves_data, items, ability_rules,
                battle_roster=battle_roster,
            )
            if screen_plan is None:
                fallback_reason = screen_fallback
                # Why? is composed once by the shared explanation builder.
            else:
                selected_strategy_plan = StrategyPlanViewModel(**screen_plan)
                strategy_plans = [selected_strategy_plan]
                recommendation = (matchup_lookup.get(screen_name)
                                  or select_strategy_member(selected_strategy_plan.pokemon_name,
                                                            selected_strategy_plan.lead_move)
                                  or recommendation)
    elif team_strategy != "strongest_matchup":
        fallback_reason = (
            "This strategy is selected for team-building analysis, but its live "
            "opponent-aware tactical branch is not implemented yet. Battle Compass "
            "is using the strongest direct matchup for this battle while keeping "
            "the selected strategy active for readiness and recommendation guidance."
        )
        # Why? is composed once by the shared explanation builder.
    if team_strategy == "weather_control" and recommendation is not None and selected_strategy_plan is not None:
        # The visible conditional attack and the OHKO notes MUST share the same
        # effective weather. Preserve all non-OHKO tactical notes (including
        # weather disruption and residual notes) and the raw Full Analysis.
        attack_name = (selected_strategy_plan.conditional_move_name
                       or selected_strategy_plan.lead_move)
        weather = _weather_for_recommended_member(
            recommendation.pokemon, selected_strategy_plan, current_weather)
        attack = next((m for m in get_moves(recommendation.pokemon, moves_data)
                       if str(m.get('Move') or '') == str(attack_name or '')), None)
        if attack is not None and weather is not None and attack.get('Category') in {'Physical', 'Special'}:
            computed = _weather_conditional_ohko_notes(
                recommendation.pokemon, opponent, attack, weather,
                items, ability_rules, moves_data)
            ohko_texts = {'Likely OHKO', 'Possible OHKO', 'Likely Survival OHKO',
                          'Possible Survival OHKO', 'Likely Incoming OHKO',
                          'Possible Incoming OHKO'}
            retained = [n for n in recommendation.battle_notes if n.text not in ohko_texts]
            recommendation = replace(recommendation, battle_notes=[*computed, *retained])
    if team_strategy == "weather_control" and recommendation is not None:
        # Opposing weather moves can invalidate current projections. Use the
        # shared Battle Notes presentation, rather than a special callout UI.
        opponent_weather_moves = [str(m.get('Move') or '')
                                  for m in get_moves(opponent, moves_data)
                                  if str(m.get('Move') or '') in _WEATHER_MOVES]
        if opponent_weather_moves:
            label = ', '.join(dict.fromkeys(opponent_weather_moves))
            note = BattleNoteViewModel(
                icon=NOTE_ICONS.get('warning', '⚠'), category='warning',
                text=f"Weather disruption: {opponent.get('Pokemon', 'The opponent')} knows {label} and can replace the current weather. Reassess the plan if it does.",
            )
            if not any('Weather disruption:' in n.text for n in recommendation.battle_notes):
                recommendation = replace(recommendation, battle_notes=[*recommendation.battle_notes, note])
    if team_strategy == "weather_control" and recommendation is not None:
        weather_after_entry = _weather_for_recommended_member(
            recommendation.pokemon, selected_strategy_plan, current_weather)
        extra_notes = _unmodeled_weather_notes(recommendation.pokemon, weather_after_entry)
        if extra_notes:
            existing_text = {n.text for n in recommendation.battle_notes}
            recommendation = replace(
                recommendation, battle_notes=[*recommendation.battle_notes,
                                              *(n for n in extra_notes if n.text not in existing_text)])
    # One shared, presentation-only explanation path for every strategy.
    # Selection, Move Scores, tactical sequencing and fallbacks above remain
    # unchanged. Strongest Matchup retains its already-polished engine prose.
    why_text = build_recommendation_why(
        strategy=team_strategy, plan=selected_strategy_plan,
        selected_name=(pokemon_display_name(recommendation.pokemon)
                       if recommendation is not None else ""),
        direct_name=direct_name, direct_move=direct_move_name or "",
        direct_why=direct_why_text, fallback_reason=fallback_reason,
        previous_why=why_text,
        opponent_name=str(opponent.get("Pokemon") or "this opponent"),
        selected_matchup=recommendation,
    )
    # Identified strategy roles are named at their source using their original
    # MemberID-bearing records. Do not globally substitute species in prose.
    # Strategy recommendations are sometimes dataclass copies of their direct
    # matchups (conditional move, notes, item/Ability scoring). Exclude the same
    # party member, not merely the same Python object or species name.
    selected_id = recommendation.pokemon.get("MemberID") if recommendation else None
    other_options = [
        matchup for matchup in all_matchups
        if not (
            (selected_id is not None and matchup.pokemon.get("MemberID") == selected_id)
            or (
                selected_id is None
                and recommendation is not None
                and matchup.pokemon is recommendation.pokemon
            )
        )
    ]
    return BattleCompassViewModel(
        opponent=opponent,
        recommendation=recommendation,
        why_text=why_text,
        other_options=other_options[:2],
        all_matchups=all_matchups,
        empty_state_message=None,
        team_strategy=team_strategy,
        strategy_capabilities=strategy_capabilities,
        strategy_plans=strategy_plans,
        selected_strategy_plan=selected_strategy_plan,
        strategy_fallback_reason=fallback_reason,
        direct_recommendation_name=direct_name or None,
        direct_fallback_move_name=next((str(r.get("Best Move") or "") for r in matchup_results
                                        if r.get("MemberID") == recommended_pokemon.get("MemberID")), None),
    )


def load_reference_data() -> ReferenceData:
    """Load the bundled reference and default team data."""
    return {
        "team_data": load_json("team_data"),
        "opponents": load_json("opponents"),
        "items": load_json("items"),
        "item_validation": load_json("item_validation_swsh"),
        "ability_rules": load_json("ability_rules"),
        "abilities": load_json("abilities_swsh"),
        "ability_descriptions": load_json("ability_descriptions_swsh"),
        "type_chart": load_json("type_chart"),
        "pokemon_validation": load_json("pokemon_validation_swsh"),
        "moves_data": load_json("moves"),
        "learnsets_swsh": load_json("learnsets_swsh"),
        "evolutions": load_json("evolutions"),
    }
