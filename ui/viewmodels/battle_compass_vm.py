"""Battle Compass view model.



Loads Battle Compass data, calls the existing battle engine, and converts



engine output into UI-friendly objects without depending on Streamlit.



"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TypedDict
from engine.calculations import evaluate_team_matchups, find_best_team_member
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
    return dict(
        pokemon_name=action_name, recommended_pokemon_name=action_name,
        lead_pokemon_name=setter, lead_move=selected_move,
        fit="Viable", fit_rank=2, summary=action, reason=detail,
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
                why_text = " ".join(filter(None, (
                    selected_strategy_plan.state_assumption,
                    selected_strategy_plan.action_detail,
                    selected_strategy_plan.fallback_if_assumption_fails,
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
