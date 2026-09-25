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


def _strategy_why_text(plan: StrategyPlanViewModel, opponent: dict) -> str:
    opponent_name = str(opponent.get("Pokemon") or "this opponent")

    if plan.lead_pokemon_name != plan.pokemon_name:
        opening = (
            f"{plan.lead_pokemon_name} is the recommended lead for the selected "
            f"Poison / Attrition strategy. Start with {plan.lead_move} to establish "
            f"poison, then pivot to {plan.pokemon_name} as the safer attrition anchor."
        )
        explanation = plan.reason
    else:
        opening = (
            f"{plan.lead_pokemon_name} is the recommended lead for the selected "
            f"Poison / Attrition strategy. Start with {plan.lead_move}."
        )
        explanation = f"{plan.summary} {plan.reason}"

    return (
        f"{opening} {explanation} Against {opponent_name}, this is the stronger "
        "strategic route. Direct Move Score and Ratio remain available as secondary "
        "guidance and stay unchanged in Full Analysis."
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
    if team_strategy == "poison_attrition":
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

    if team_strategy == "poison_attrition":
        if _opponent_is_dynamaxed(opponent):
            fallback_reason = (
                "The selected opponent is Dynamaxed or Gigantamaxed. At this point, "
                "Battle Compass prioritizes the strongest direct matchup rather than "
                "trying to start a new Poison / Attrition engine."
            )
            why_text = f"{fallback_reason} {direct_why_text}".strip()
        else:
            raw_plans = evaluate_poison_attrition_plans(
                team_data,
                opponent,
                moves_data,
                matchup_results,
                battle_roster=battle_roster,
                items=items,
                ability_rules=ability_rules,
            )
            strategy_plans = [
                StrategyPlanViewModel(
                    pokemon_name=plan.pokemon_name,
                    fit=plan.fit,
                    fit_rank=plan.fit_rank,
                    summary=plan.summary,
                    reason=plan.reason,
                    action=plan.action,
                    action_detail=plan.action_detail,
                    plan_kind=plan.plan_kind,
                    can_override_direct=plan.can_override_direct,
                    lead_pokemon_name=plan.lead_pokemon_name,
                    lead_move=plan.lead_move,
                    opener_threat_move=plan.opener_threat_move,
                    opener_threat_category=plan.opener_threat_category,
                    opener_threat_type=plan.opener_threat_type,
                    opener_threat_score=plan.opener_threat_score,
                    opener_threat_multiplier=plan.opener_threat_multiplier,
                )
                for plan in raw_plans
            ]
            selected_raw_plan = select_poison_attrition_plan(raw_plans, matchup_results)

            if selected_raw_plan is not None:
                selected_strategy_plan = next(
                    plan
                    for plan in strategy_plans
                    if plan.pokemon_name == selected_raw_plan.pokemon_name
                )
                lead_matchup = matchup_lookup.get(selected_raw_plan.lead_pokemon_name)
                if lead_matchup is not None:
                    recommendation = lead_matchup
                    why_text = _strategy_why_text(selected_strategy_plan, opponent)
            else:
                fallback_reason = _steel_direct_fallback_reason(
                    opponent,
                    matchup_results,
                )
                if fallback_reason is None:
                    fallback_reason = describe_poison_attrition_fallback(
                        team_data,
                        opponent,
                        moves_data,
                        matchup_results,
                        items=items,
                        ability_rules=ability_rules,
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
        "evolutions": load_json("evolutions"),
    }
