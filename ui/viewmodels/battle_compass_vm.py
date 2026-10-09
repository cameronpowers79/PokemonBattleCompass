"""Battle Compass view model.



Loads Battle Compass data, calls the existing battle engine, and converts



engine output into UI-friendly objects without depending on Streamlit.



"""
from __future__ import annotations
from dataclasses import dataclass, field, replace
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
    if strongest.pokemon_name == selected_plan.pokemon_name or strongest_score <= selected_score:
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


def _strategy_why_text(plan: StrategyPlanViewModel, opponent: dict, poisoned_followup: tuple[str, str | None, float | None] | None = None, safety_tradeoff: str | None = None) -> str:
    opponent_name = str(opponent.get("Pokemon") or "this opponent")
    branch_label = _strategy_label(plan.strategy_branch)
    paragraphs: list[str] = []

    primary_bits: list[str] = []
    if plan.state_assumption:
        primary_bits.append(plan.state_assumption)
    lead_plan_kinds = {"lead_toxic_then_spikes", "lead_team_setup"}
    if plan.plan_kind == "followup_assumed_poison":
        primary_bits.append(f"Under {branch_label}, {opponent_name} is being evaluated as a poisoned follow-up.")
    elif plan.plan_kind in lead_plan_kinds and plan.lead_pokemon_name:
        primary_bits.append(f"{plan.lead_pokemon_name} is the recommended lead for {branch_label}.")
    elif plan.lead_pokemon_name:
        primary_bits.append(f"{plan.lead_pokemon_name} is the recommendation for this matchup under {branch_label}.")
    if plan.action_detail:
        primary_bits.append(plan.action_detail)
    if primary_bits:
        paragraphs.append(" ".join(primary_bits))

    if opponent.get("Slot") != 1 and not plan.assumed_poisoned and poisoned_followup is not None:
        alt_name, alt_move, alt_score = poisoned_followup
        displayed_name = plan.recommended_pokemon_name or plan.lead_pokemon_name or plan.pokemon_name
        shown_name = f"**{alt_name}**" if alt_name and alt_name != displayed_name else alt_name
        if alt_name:
            if alt_move:
                alt_text = f"If poison is already active from an earlier setup opportunity: {shown_name} → {alt_move}."
            else:
                alt_text = f"If poison is already active from an earlier setup opportunity: {shown_name} is the best modeled follow-up."
            if alt_score is not None:
                alt_text += f" Conditional Move Score: {alt_score:.2f}."
            paragraphs.append(alt_text)

    rationale_bits: list[str] = []
    if plan.reason:
        rationale_bits.append(plan.reason)
    if plan.conditional_move_name and plan.conditional_move_score is not None:
        rationale_bits.append(f"With poison active, {plan.conditional_move_name}'s conditional Move Score is {plan.conditional_move_score:.2f}.")
    if rationale_bits:
        paragraphs.append(" ".join(rationale_bits))
    if safety_tradeoff:
        paragraphs.append(safety_tradeoff)

    footer_bits: list[str] = []
    if plan.fallback_if_assumption_fails:
        footer_bits.append(plan.fallback_if_assumption_fails)
    if plan.assumed_poisoned:
        footer_bits.append("Full Analysis shows strategy-neutral direct options if the assumed poison state is no longer valid.")
    elif plan.state_assumption:
        footer_bits.append("Full Analysis shows strategy-neutral direct options while the Compass re-evaluates from the modeled post-lead state.")
    else:
        footer_bits.append("Full Analysis remains strategy-neutral for direct comparison.")
    paragraphs.append(" ".join(footer_bits))
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


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


def _screen_control_battle_plan(team_data, opponent, matchups, moves_data, items, ability_rules):
    """Conservative single-opponent screen sequence, using only equipped moves.

    Returns a selected tactical plan and its target recommendation, or a reason
    to keep Strongest Matchup. No persistent battle-state assumptions are stored.
    """
    lookup = _build_move_lookup(moves_data)
    by_name = {str(row.get("Pokemon") or ""): row for row in matchups}
    opponents = [str(opponent.get(f"Move{i}") or "") for i in range(1, 5)]
    damaging = [lookup.get(name, {}) for name in opponents]
    physical = any(m.get("Category") == "Physical" and float(m.get("Power") or 0) > 0 for m in damaging)
    special = any(m.get("Category") == "Special" and float(m.get("Power") or 0) > 0 for m in damaging)
    if not physical and not special:
        return None, None, "The opponent's damaging move category is not modeled; screen selection cannot be justified safely."

    candidates = []
    for mon in team_data:
        name = str(mon.get("Pokemon") or "")
        result = by_name.get(name)
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
        worst_move = lookup.get(str(result.get("Worst Incoming Move") or ""), {})
        worst_category = worst_move.get("Category") or result.get("Worst Incoming Move Category")
        preferred = "Reflect" if worst_category == "Physical" else "Light Screen" if worst_category == "Special" else ""
        selected = preferred if preferred in options else options[0]
        ability = str(mon.get("Ability") or "").casefold()
        priority = ability == "prankster"
        speed = float(mon.get("SPE") or 0)
        safety = float(result.get("Ratio") or 0)
        candidates.append((int(priority), safety, speed, name, selected, result, options))

    if not candidates:
        return None, None, "No equipped screen setter has a supported safe opening against this opponent; use the strongest direct matchup."
    candidates.sort(reverse=True)
    priority, safety, speed, setter, screen, result, options = candidates[0]
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
    attackers = [r for r in immediate_matchups
                 if r.get("Pokemon") != setter
                 and str(r.get("Best Move") or "") not in delayed
                 and float(r.get("Best MoveScore") or 0) > 0]
    attackers.sort(key=lambda r: (float(r.get("Ratio") or 0),
                                  float(r.get("Best MoveScore") or 0)), reverse=True)
    payoff = attackers[0] if attackers else None
    payoff_name = str(payoff.get("Pokemon") or "") if payoff else ""
    payoff_move = str(payoff.get("Best Move") or "") if payoff else ""
    if is_lead or not payoff:
        action_name = setter
        selected_move = screen
        plan_kind = "screen_setup"
        action = f"Establish {screen} with {setter}"
        detail = (f"Step 1: {setter} establishes {screen} to reduce incoming "
                  f"{'physical' if screen == 'Reflect' else 'special'} damage. "
                  f"The setter has {delivered} against {threat}. "
                  + (f"Step 2: switch to {payoff_name} and attack with {payoff_move} behind the screen. " if payoff else "No safe immediate follow-up is modeled."))
        assumed = False
        assumption = "Screens have not yet been assumed active for the lead." if is_lead else "Screen setup is still needed; no protected attacker could be established."
    else:
        action_name = payoff_name
        selected_move = payoff_move
        plan_kind = "screen_followup_assumed"
        action = f"Follow up with {payoff_name} using {payoff_move}"
        detail = (f"Step 1: {setter} establishes {screen}. "
                  f"Step 2: {payoff_name} uses {payoff_move} behind that screen. "
                  "The attacking move is modeled as immediate damage; delayed-hit moves are excluded. "
                  "The Compass cannot verify whether the screen is still active.")
        assumed = True
        assumption = f"Conditional: assumes {screen} was established on an earlier turn and remains active."
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
        if threatened:
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
    chosen_member = next((m for m in team_data if str(m.get("Pokemon") or "") == action_name), {})
    chosen_moves = {str(chosen_member.get(f"Move{i}") or "") for i in range(1, 5)}
    pivot = next((m for m in ("U-turn", "Volt Switch", "Parting Shot", "Flip Turn", "Baton Pass") if m in chosen_moves), None)
    contingency = f"{pivot} offers a pivot option, subject to surviving until it acts." if pivot else "An ordinary switch to the protected attacker is the modeled exit."
    if plan_kind == "screen_followup_assumed" and payoff:
        explanation = (f"{payoff_move} has a favorable direct matchup (Ratio "
                       f"{float(payoff.get('Ratio') or 0):.2f}). "
                       f"{screen} adds protection; fall back if it expires.")
    else:
        explanation = (f"{'Prankster priority' if priority else 'Modeled survival'} supports {screen}. "
                       + (f"{payoff_name} offers a favorable follow-up. " if strong_payoff else "Follow-up is less secure. ")
                       + (f"Exit: {pivot}." if pivot else "Exit: switch to the attacker."))
    return dict(
        action_type="Screen Setup" if plan_kind == "screen_setup" else "Screen Payoff",
        condition_detail=(f"Assumes {screen} was established earlier and is still active. "
                          "If it has expired or was removed, use the named direct fallback."
                          if assumed else ""),
        plan_role="Screen Setter" if plan_kind == "screen_setup" else "Protected Attacker",
        fit_explanation=explanation,
        attack_move_score=float(payoff.get("Best MoveScore") or 0) if plan_kind == "screen_followup_assumed" and payoff else None,
        sequence_heading=f"{screen} → {payoff_name}" if payoff_name else f"{setter} → {screen}",
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
            "If the screen is absent or expired, establish it safely first or use Strongest Matchup."
            if assumed else "If the setter is already damaged or unsafe, use Strongest Matchup instead."
        ),
    ), action_name, None


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
    lookup = {str(r.get("Pokemon")): r for r in matchups}
    # Evaluate each setter’s own payoff, rather than giving the team’s globally
    # highest Hex user automatic priority as the setter.
    candidates = []
    opponent_moves = get_moves(opponent, moves_data)
    physical_threat = any(m.get("Category") == "Physical" and float(m.get("Power") or 0) > 0
                          for m in opponent_moves)
    for member in team_data:
        name = str(member.get("Pokemon") or "")
        result = lookup.get(name)
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
        if projected_name != str(setter.get("Pokemon") or ""):
            projected_matchup = lookup.get(projected_name)
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
        if payoff is not None and str(payoff[2].get("Pokemon") or "") == str(setter.get("Pokemon") or ""):
            if setter_direct_score > 0 and float(payoff[0]) <= setter_direct_score:
                payoff = None
    name = str(setter.get("Pokemon") or "")
    ratio = float(result.get("Ratio") or 0)
    priority = str(setter.get("Ability") or "").casefold() == "prankster"
    if (ratio >= 1.5 and accuracy >= 85) or (priority and ratio >= 0.8 and accuracy >= 85):
        fit, rank = "Strong", 3
    elif ratio >= 0.9:
        fit, rank = "Viable", 2
    else:
        fit, rank = "Risky", 1

    projected = None
    if payoff is not None:
        boosted, unboosted, payoff_member, payoff_move = payoff
        payoff_name = str(payoff_member.get("Pokemon") or "")
        same = name == payoff_name
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


def _setup_offense_battle_plan(team_data, opponent, matchups, moves_data, items, ability_rules):
    """Model an equipped self-boost followed by that same Pokémon's attack.

    Project one setup turn only. No boosts are transferred to teammates or
    inferred from earlier opponents. Full Analysis remains unboosted.
    """
    from engine.mechanics import get_item_speed_multiplier, get_guaranteed_weather
    by_name = {str(row.get("Pokemon") or ""): row for row in matchups}
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
        row = by_name.get(name)
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
            score = (min(damage_gain, 4) * 2.0 + (1.3 if speed_flip else 0)
                     + min(float(row.get("Ratio") or 0), 5) * 0.35
                     - risk_ratio * 1.4 + (0.25 if acts_first else 0))
            candidates.append((score, member, setup_name, attack, row, boosted_score,
                               base_score, speed_flip, own_speed, opponent_speed,
                               speed_after, risk_ratio, uncertain_weather))
    if not candidates:
        return "No safe, worthwhile one-turn offensive setup was modeled. Use the strongest direct matchup."
    (score, member, setup_name, attack, row, boosted_score, base_score,
     flip, own_speed, enemy_speed, speed_after, damage_risk, unknown_weather) = max(candidates, key=lambda x:x[0])
    name = str(member.get("Pokemon") or "")
    move_name = str(attack.get("Move") or "")
    strong = damage_risk <= 0.4 and (boosted_score >= base_score * 1.5 or flip)
    fit, rank = ("Strong", 3) if strong else ("Viable", 2)
    speed_text = (f" Setup changes turn order: Speed {own_speed:.0f} → {speed_after:.0f} "
                  f"versus {enemy_speed:.0f}." if flip else "")
    assumption = (f"Assumes {name} successfully used {setup_name} and kept its stat boosts. "
                  "Switching removes these boosts. The Compass cannot verify live battle state.")
    detail = (f"Step 1: {name} uses {setup_name} if at sufficient HP to survive setup. "
              f"Step 2: stay in and use {move_name}. Projected Move Score {boosted_score:.2f} "
              f"versus {base_score:.2f} before setup.{speed_text} "
              "Boosts are not carried over after switching or to another teammate.")
    return dict(
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
                         + "Check HP before boosting."),
        sequence_heading=f"{name} → {setup_name} → {move_name}",
        state_assumption="No stat boosts are assumed active at entry.",
        fallback_if_assumption_fails="If setup is unsafe or interrupted, use the named direct fallback.",
        condition_detail=assumption,
    )


def build_battle_compass_view_model(
    *,
    team_data: list[dict],
    opponent: dict,
    items: list[dict],
    ability_rules: list[dict],
    moves_data: list[dict],
    team_strategy: str = "strongest_matchup",
    battle_roster: list[dict] | None = None,
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
    pokemon_lookup = {
        pokemon["Pokemon"]: pokemon for pokemon in team_data if pokemon.get("Pokemon")
    }
    all_matchups = [
        _build_matchup_view_model(
            result=result,
            pokemon=pokemon_lookup[result["Pokemon"]],
            move_lookup=move_lookup,
        )
        for result in matchup_results
        if result.get("Pokemon") in pokemon_lookup
    ]
    matchup_lookup = {
        matchup.pokemon["Pokemon"]: matchup for matchup in all_matchups
    }
    direct_name = str(recommended_pokemon.get("Pokemon") or "")
    recommendation = matchup_lookup.get(direct_name)
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
    why_text = direct_why_text
    strategy_plans: list[StrategyPlanViewModel] = []
    selected_strategy_plan: StrategyPlanViewModel | None = None
    fallback_reason: str | None = None
    if team_strategy in {"poison_attrition", "poison_offensive_pressure"}:
        if _force_strongest_matchup_for_known_doubles(opponent):
            fallback_reason = (
                "This is a Double Battle. Battle Compass currently models single-opponent tactical states, so strategy-specific recommendations are disabled here and Strongest Matchup is being used instead."
            )
            why_text = f"{fallback_reason} {direct_why_text}".strip()
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
                )
                for plan in raw_plans
            ]
            selected_raw_plan = select_poison_attrition_plan(raw_plans, matchup_results)
            is_dynamaxed = _opponent_is_dynamaxed(opponent)
            allow_dmax_poison_plan = False
            if is_dynamaxed and selected_raw_plan is not None and team_strategy == "poison_offensive_pressure":
                direct_result = next((row for row in matchup_results if str(row.get("Pokemon") or "") == direct_name), None)
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
                why_text = f"{fallback_reason} {direct_why_text}".strip()
            elif selected_raw_plan is not None:
                selected_strategy_plan = next(
                    plan for plan in strategy_plans
                    if plan.pokemon_name == selected_raw_plan.pokemon_name
                    and plan.plan_kind == selected_raw_plan.plan_kind
                )
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
                strategy_matchup = matchup_lookup.get(recommended_name)
                if strategy_matchup is not None:
                    recommendation = strategy_matchup
                poisoned_followup = None
                if opponent.get("Slot") != 1 and not selected_strategy_plan.assumed_poisoned:
                    poisoned_followup = project_poisoned_followup(
                        team_data, opponent, moves_data, matchup_results, items=items, ability_rules=ability_rules,
                        strategy_branch=team_strategy, current_pokemon_name=recommended_name,
                    )
                safety_tradeoff = _poison_safety_tradeoff_text(raw_plans, selected_raw_plan)
                why_text = _strategy_why_text(selected_strategy_plan, opponent, poisoned_followup, safety_tradeoff)
            else:
                fallback_reason = describe_poison_attrition_fallback(
                    team_data, opponent, moves_data, matchup_results, items=items, ability_rules=ability_rules,
                    strategy_branch=team_strategy,
                )
                why_text = f"{fallback_reason} {direct_why_text}".strip()
    elif team_strategy == "status_control_punish":
        if _force_strongest_matchup_for_known_doubles(opponent) or _opponent_is_dynamaxed(opponent):
            fallback_reason = "Status Control & Punish falls back to direct offense for modeled doubles and Dynamax encounters."
            why_text = f"{fallback_reason} {direct_why_text}".strip()
        else:
            status_result, payoff = _status_control_battle_plan(
                team_data, opponent, matchup_results, moves_data, items, ability_rules
            )
            if status_result is None:
                fallback_reason = payoff
                why_text = f"{fallback_reason} {direct_why_text}".strip()
            else:
                selected_strategy_plan = StrategyPlanViewModel(**status_result)
                strategy_plans = [selected_strategy_plan]
                recommendation = matchup_lookup.get(selected_strategy_plan.pokemon_name, recommendation)
                payoff_detail = ""
                if payoff is not None:
                    payoff_name, payoff_move, boosted, unboosted, status = payoff
                    payoff_detail = (
                        f"With {status} active on THIS opponent, {payoff_name}'s {payoff_move} "
                        f"has a projected conditional Move Score of {boosted:.2f} "
                        f"versus {unboosted:.2f} without status. "
                    )
                why_text = (
                    f"{selected_strategy_plan.state_assumption} "
                    f"{selected_strategy_plan.action_detail} "
                    f"{payoff_detail}"
                    f"Direct fallback: {direct_name} → "
                    f"{next((str(r.get('Best Move') or '') for r in matchup_results if r.get('Pokemon') == direct_name), 'best attack')}. "
                    "Full Analysis retains unconditioned scores."
                )
    elif team_strategy == "setup_offense":
        if _force_strongest_matchup_for_known_doubles(opponent) or _opponent_is_dynamaxed(opponent):
            fallback_reason = "Setup Offense uses Strongest Matchup for modeled doubles and Dynamax opponents."
            why_text = f"{fallback_reason} {direct_why_text}".strip()
        else:
            setup_result = _setup_offense_battle_plan(team_data, opponent, matchup_results, moves_data, items, ability_rules)
            if isinstance(setup_result, str):
                fallback_reason = setup_result
                why_text = f"{fallback_reason} {direct_why_text}".strip()
            elif setup_result is None:
                fallback_reason = "No supported offensive setup found; use Strongest Matchup."
                why_text = f"{fallback_reason} {direct_why_text}".strip()
            else:
                selected_strategy_plan = StrategyPlanViewModel(**setup_result)
                strategy_plans = [selected_strategy_plan]
                recommendation = matchup_lookup.get(selected_strategy_plan.pokemon_name, recommendation)
                why_text = (f"{selected_strategy_plan.state_assumption} "
                            f"{selected_strategy_plan.action_detail} "
                            f"Direct fallback: {direct_name} → "
                            f"{next((str(r.get('Best Move') or '') for r in matchup_results if r.get('Pokemon') == direct_name), 'best attack')}. "
                            "Full Analysis retains unboosted scores.")
    elif team_strategy == "screen_control":
        if _force_strongest_matchup_for_known_doubles(opponent) or _opponent_is_dynamaxed(opponent):
            fallback_reason = (
                "Screen Control's single-opponent sequence is not modeled safely for "
                "this Double Battle or Dynamax opponent; Strongest Matchup is used."
            )
            why_text = f"{fallback_reason} {direct_why_text}".strip()
        else:
            screen_plan, screen_name, screen_fallback = _screen_control_battle_plan(
                team_data, opponent, matchup_results, moves_data, items, ability_rules
            )
            if screen_plan is None:
                fallback_reason = screen_fallback
                why_text = f"{fallback_reason} {direct_why_text}".strip()
            else:
                selected_strategy_plan = StrategyPlanViewModel(**screen_plan)
                strategy_plans = [selected_strategy_plan]
                recommendation = matchup_lookup.get(screen_name, recommendation)
                screen_move = (selected_strategy_plan.lead_move
                               if selected_strategy_plan.plan_kind == "screen_setup"
                               else "")
                # Follow-up plans store the attack in lead_move. Recover the
                # assumed screen from the explicit battle-state assumption.
                if not screen_move:
                    assumption = selected_strategy_plan.state_assumption or ""
                    screen_move = ("Light Screen" if "Light Screen" in assumption
                                   else "Reflect" if "Reflect" in assumption else "")
                chosen_defender = next(
                    (member for member in team_data if member.get("Pokemon") == screen_name),
                    None,
                )
                screened = (
                    _screened_worst_incoming(
                        opponent, chosen_defender, screen_move,
                        moves_data, items, ability_rules,
                    )
                    if chosen_defender is not None else None
                )
                mitigation_text = (
                    f"With {screen_move} active, the Incoming Worst Move against "
                    f"{screen_name} is {screened[0]}, with an Incoming Worst "
                    f"Score of {screened[1]:.2f}. "
                    "This assumes a single battle without a critical hit; "
                    "Full Analysis retains the unscreened score."
                    if screened is not None else ""
                )
                why_text = " ".join(filter(None, (
                    selected_strategy_plan.state_assumption,
                    mitigation_text,
                    selected_strategy_plan.action_detail,
                    selected_strategy_plan.fallback_if_assumption_fails,
                    f"Direct fallback if the screen is absent: {direct_name} → {recommendation.best_move.get('Move') if recommendation and recommendation.pokemon.get('Pokemon') == direct_name else next((r.get('Best Move') for r in matchup_results if r.get('Pokemon') == direct_name), 'best attack')}.",
                    "Full Analysis remains strategy-neutral for direct comparisons."
                )))
    elif team_strategy != "strongest_matchup":
        fallback_reason = (
            "This strategy is selected for team-building analysis, but its live "
            "opponent-aware tactical branch is not implemented yet. Battle Compass "
            "is using the strongest direct matchup for this battle while keeping "
            "the selected strategy active for readiness and recommendation guidance."
        )
        why_text = f"{fallback_reason} {direct_why_text}".strip()
    other_options = [matchup for matchup in all_matchups if matchup is not recommendation]
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
        direct_fallback_move_name=next((str(r.get("Best Move") or "") for r in matchup_results if r.get("Pokemon") == direct_name), None),
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
