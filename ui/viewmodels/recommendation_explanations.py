"""Shared player-facing Why? wording for Battle Compass.

Strategy evaluators select Pokémon and provide battle evidence. This module
communicates their reasons; it does not select or score a Pokémon.
"""
from __future__ import annotations

import re
from typing import Any


def _field(plan: Any, name: str, default: Any = "") -> Any:
    return getattr(plan, name, default) if plan is not None else default


def _move_pair(plan: Any) -> tuple[str, str]:
    heading = str(_field(plan, "sequence_heading") or _field(plan, "summary"))
    parts = [part.strip() for part in heading.split("→")]
    return (parts[1] if len(parts) > 1 else str(_field(plan, "lead_move")),
            parts[-1] if len(parts) > 2 else str(_field(plan, "setup_followup_move")))


def _sweep_targets(detail: str) -> list[str]:
    """Use only the named projected OHKOs actually reported by Setup Offense."""
    match = re.search(r"Sweep potential:.*?projected OHKOs against (.*?)(?:\.|$)", detail)
    if not match:
        return []
    return [name.strip().removeprefix("and ").strip() for name in
            re.findall(r"([^,]+?) \([^)]+\)", match.group(1))]


def _threat_details(selected_matchup: Any) -> tuple[str, float]:
    move = _field(selected_matchup, "worst_move", {}) or {}
    name = str(move.get("Move") or "") if isinstance(move, dict) else ""
    multiplier = float(_field(selected_matchup, "incoming_type_multiplier", 1) or 1)
    return name, multiplier


def build_recommendation_why(
    *, strategy: str, plan: Any, selected_name: str,
    direct_name: str, direct_move: str, direct_why: str,
    fallback_reason: str | None, previous_why: str,
    opponent_name: str = "this opponent", selected_matchup: Any = None,
) -> str:
    """Explain the deciding tactical advantages without repeating the plan.

    Every outcome claimed here is conditioned on evidence passed from existing
    strategy plans and matchup data; no new tactical ranking is performed.
    """
    if strategy == "strongest_matchup":
        return direct_why
    if fallback_reason or plan is None:
        reason = (fallback_reason or "").split(" Weather outlook:", 1)[0].strip()
        if strategy == "weather_control" and reason:
            if "doubles and Dynamax" in reason:
                return (f"{selected_name or direct_name} is recommended against {opponent_name} "
                        "using Strongest Matchup. Double Battles and Dynamax opponents "
                        "are not supported by Weather Control's tactical sequence.")
            return (f"{selected_name or direct_name} is the strongest supported direct choice "
                    f"against {opponent_name}; the proposed weather sequence does not "
                    "offer a sufficiently safe or effective advantage.")
        return reason or direct_why or previous_why

    name = selected_name or str(_field(plan, "recommended_pokemon_name") or _field(plan, "pokemon_name"))
    lead = str(_field(plan, "lead_move"))
    kind = str(_field(plan, "plan_kind"))
    detail = str(_field(plan, "action_detail"))
    setup, attack = _move_pair(plan)
    alternate = bool(direct_name and direct_name != name)

    if strategy in {"poison_offensive_pressure", "poison_attrition"}:
        if _field(plan, "assumed_poisoned"):
            payoff = str(_field(plan, "conditional_move_name") or lead)
            intro = f"If the earlier poison setup is still active, {name} can exploit it with {payoff}."
        elif "Toxic Spikes" in detail and "Toxic" in detail:
            intro = f"{name} can poison {opponent_name} and prepare Toxic Spikes for later opponents."
        elif lead:
            intro = f"{name} can use {lead} to establish or exploit poison against {opponent_name}."
        else:
            intro = f"{name} offers a poison-based approach against {opponent_name}."
        rationale = str(_field(plan, "reason")).strip()
        if rationale and rationale != detail and len(rationale) <= 150 and not any(
            marker in rationale for marker in ("Step 1", "Full Analysis", "Move Score", "Direct fallback")
        ):
            return intro + " " + rationale
        if strategy == "poison_attrition":
            return intro + " Its defensive tools favor sustained poison pressure over immediate damage."
        return intro

    if strategy == "screen_control":
        if kind == "screen_followup_assumed":
            # A screen lowers incoming damage; it does NOT affect the choice of
            # strongest direct attacker. Name the actual threat when available.
            attack_name = str(_field(plan, "sequence_heading")).split("→")[-1].strip()
            first = (f"{name} is the preferred attacker against {opponent_name}"
                     + (f" with {attack_name}" if attack_name else "") + ".")
            threat, multiplier = _threat_details(selected_matchup)
            if multiplier > 1 and threat:
                first += f" {threat} is super effective against {name},"
            else:
                first += ""
            screen = "Reflect" if "Reflect" in detail else "Light Screen" if "Light Screen" in detail else ""
            scores = re.search(r"Incoming Worst Score.*?:\s*([\d.]+) without it\s*→\s*([\d.]+) with it", detail)
            if screen and scores:
                prefix = " but " if multiplier > 1 and threat else " If "
                if prefix == " If ":
                    first += f" If {screen} is still active, projected incoming damage falls from {scores.group(1)} to {scores.group(2)}."
                else:
                    first += f" but {screen}, if still active, reduces the projected Incoming Worst Score from {scores.group(1)} to {scores.group(2)}."
            elif screen:
                first += f" {screen}, if still active, helps protect {name} against incoming attacks."
            return first
        screen = lead if lead in {"Reflect", "Light Screen"} else setup
        if screen not in {"Reflect", "Light Screen"}:
            screen = "a screen"
        return f"{name} can safely establish {screen}, giving the team better protection against {opponent_name}."

    if strategy == "setup_offense":
        if kind == "offensive_setup_continuation":
            assumed = str(_field(plan, "state_assumption"))
            match = re.search(r"established ([\w -]+?) against", assumed)
            setup_name = match.group(1) if match else "its earlier boost"
            move = lead or str(_field(plan, "setup_followup_move"))
            ohko = bool(_field(plan, "setup_followup_likely_ohko", False))
            text = (f"If {setup_name} is still active, {name}'s {move} is projected to OHKO {opponent_name}."
                    if ohko else f"If {setup_name} is still active, {name} can continue its sweep with {move}.")
            # When the direct fallback chooses the same Pokémon, explain why
            # continuing with its established boost is preferable to a circular
            # "abandon the strategy" instruction. The evaluator supplied this
            # evidence; the wording layer does not recalculate the matchup.
            if (_field(plan, "continuation_same_direct", False)
                    and _field(plan, "continuation_below_threshold", False)):
                threat, multiplier = _threat_details(selected_matchup)
                if threat and multiplier > 1:
                    text += f" {opponent_name}'s super-effective {threat} makes this a risky matchup."
                else:
                    text += " The boosted matchup is still challenging."
                text += f" {name} is also the best direct matchup, so preserving the existing boost is preferable to abandoning it."
                if _field(plan, "continuation_dig_shelter", False):
                    text += f" {move} protects {name} from the opponent's listed attacks while underground."
            elif alternate:
                text += f" {direct_name} has the stronger unboosted matchup if the boost is gone."
            return text
        setup_move = setup or lead
        attack_move = attack or str(_field(plan, "setup_followup_move"))
        targets = _sweep_targets(detail)
        safety = "safe" if str(_field(plan, "fit")) == "Strong" else "supported"
        # Battle-wide sweep evidence is the key distinction when the immediate
        # direct matchup points to a different Pokémon.
        if targets:
            if alternate:
                text = (f"{direct_name}'s {direct_move or 'attack'} is the stronger immediate option, "
                        f"but {name} has a {safety} opening for {setup_move} and projected OHKOs "
                        f"against {', '.join(targets)} after boosting.")
            else:
                text = (f"{name} has a {safety} opening to use {setup_move}, setting up "
                        f"projected OHKOs against {', '.join(targets)}.")
            return text
        text = (f"{name} has a {safety} opening to use {setup_move}"
                + (f" and strengthen {attack_move}." if attack_move and attack_move != setup_move else "."))
        if alternate:
            text += (f" {direct_name} has the stronger direct matchup, but {name} offers "
                     "a longer-term offensive advantage after setup.")
        return text

    if strategy == "status_control_punish":
        status = re.search(r"inflict (burn|poison|paralysis|sleep)", detail, re.I)
        status_name = status.group(1).lower() if status else "status"
        payoff = re.search(r"Step 2: if status lands, (.*?)(?:\.|$)", detail)
        opening = f"{name} can inflict {status_name} on {opponent_name} with {lead}, creating an opening for status punishment."
        if payoff:
            action = payoff.group(1).strip()
            if action.startswith("stay in and use "):
                move = action.removeprefix("stay in and use ")
                opening += f" {move} becomes a stronger follow-up while the status holds."
            elif action.startswith("switch to "):
                opening += f" After the status lands, {action} for the payoff."
        return opening

    if strategy == "defensive_attrition":
        if kind == "contact_punishment":
            if lead == "Obstruct":
                return f"{name} can use Obstruct to punish contact by lowering {opponent_name}'s Defense, strengthening subsequent physical attacks."
            if lead == "Baneful Bunker":
                return f"{name} can block a contact attack with Baneful Bunker and poison {opponent_name}, creating steady attrition pressure."
            return f"{name} can use {lead} to punish {opponent_name}'s contact attacks and gain an attrition advantage."
        if setup == "Iron Defense" and attack == "Body Press":
            return f"{name} can use Iron Defense to improve both its durability and Body Press damage against {opponent_name}."
        return f"{name} can use {lead} defensively while increasing pressure on {opponent_name}."

    if strategy == "weather_control":
        # Use the plan's actual evidence, not its Strategic Fit caption.
        evidence = str(_field(plan, "weather_why_evidence") or "").strip()
        weather_match = re.search(r"(?:^|→\s*)(Sun|Rain|Hail|Sandstorm)(?: assumed active|\s*→)",
                                  str(_field(plan, "sequence_heading")), re.I)
        weather = weather_match.group(1) if weather_match else "weather"
        is_followup = kind == "weather_followup"
        attack_name = (str(_field(plan, "lead_move")) if is_followup
                       else str(_field(plan, "sequence_heading")).split("→")[-1].strip())
        if attack_name.startswith("(") and attack_name.endswith(")"):
            attack_name = attack_name[1:-1]

        # The benefit is tied to the chosen plan. Don't state that all weather
        # boosts damage, or incorrectly attribute a beneficiary's attack to a setter.
        if evidence:
            text = evidence
        elif is_followup:
            text = (f"If {weather} remains active, {name} can attack "
                    f"{opponent_name} with {attack_name or lead}.")
        else:
            text = (f"{name} establishes {weather} as the selected weather plan "
                    f"against {opponent_name}.")
        # When the strategy selects a different Pokémon than the direct
        # baseline, acknowledge the comparison without asserting an unmodeled
        # numerical advantage or immunity.
        if alternate and not is_followup:
            text += (f" {direct_name} is the strongest unboosted direct option; "
                     f"this plan instead establishes {weather} for its conditional payoff.")
        return text

    return direct_why or previous_why
