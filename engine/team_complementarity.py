"""Team-specific coverage recommendation priority (Step 4).

Only activates after the team's selected strategy is Strong.  Never changes
individual Strategy Fit or uses hypothetical moves as confirmed coverage.
Coverage-only candidates must be genuinely bulky to join an established
Defensive Attrition team; ordinary candidate selection is unchanged otherwise.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any
import re

from engine.base_stats_registry import role_base_stats
from engine.coverage_planning import catalog_team_member
from engine.potential_coverage import evaluate_candidate_coverage
from engine.strategy_capabilities import StrategyRecommendationCandidate, strategy_move_guidance
from engine.team_coverage import team_coverage

_COVERAGE_STRATEGIES = {"defensive_attrition", "status_control_punish", "setup_offense"}

@dataclass(frozen=True)
class ComplementarySuggestion:
    recommendation: StrategyRecommendationCandidate
    proposed_moves: tuple[str, ...]
    coverage_moves: tuple[tuple[str, tuple[str, ...], str], ...]
    gained_types: tuple[str, ...]
    defensive_improvements: tuple[str, ...]
    new_immunities: tuple[str, ...]
    projected_score: float
    coverage_only: bool
    recommendation_reason: str = "Core Strategy"
    coverage_focus: str = ""
    priority_weaknesses: tuple[str, ...] = ()


def _key(name: str) -> str:
    return re.sub(r'\s+\((Male|Female)\)$', '', name, flags=re.I).casefold().strip()


def _candidate_name(candidate: Mapping[str, Any]) -> str:
    return str(candidate.get('Pokemon') or candidate.get('pokemon') or '').strip()


def _candidate_for_display(candidate: Mapping[str, Any]) -> str:
    name = _candidate_name(candidate)
    if candidate.get('_strategy_gender_variant') and candidate.get('Gender'):
        name += f" ({candidate['Gender']})"
    return name


def _ability_from_summary(summary: str) -> str:
    match = re.search(r'Recommended Ability:\s*(.*?)\s*\(', summary)
    return match.group(1).strip() if match else ''


def _bulk(candidate: dict[str, Any]) -> float:
    stats = role_base_stats(candidate, 'defense') or {}
    return float(stats.get('HP') or 0) * (float(stats.get('DEF') or 0) + float(stats.get('SPD') or 0)) / 200


def rank_with_team_coverage(
    strategy_key: str,
    readiness: str,
    team: Sequence[Mapping[str, Any]],
    recommendations: Sequence[StrategyRecommendationCandidate],
    candidates: Sequence[Mapping[str, Any]],
    type_chart: Mapping[str, Mapping[str, float]],
    moves_data: Sequence[Mapping[str, Any]],
    learnsets_data: dict[str, Any],
    *,
    include_coverage_only: bool = True,
) -> list[ComplementarySuggestion]:
    """Evaluate realistic marginal team value, preserving strategy fundamentals.

    Recommendation scores and Strategy Fit remain untouched; ranking is based on
    a separate context-specific score. Coverage-only additions require a strong
    existing plan, legitimate legal moves, material defensive/offensive benefit,
    and substantial defensive bulk (Defensive Attrition only).
    """
    original = list(recommendations)
    if readiness != 'Strong' or strategy_key not in _COVERAGE_STRATEGIES or not team or len(team) >= 6:
        return [ComplementarySuggestion(rec, (), (), (), (), (), rec.score, False) for rec in original]

    before = team_coverage(team, type_chart, moves_data)
    # The two most exposed types should drive complementary defensive selection,
    # not vanish into a sum of minor resistance improvements across 18 types.
    vulnerabilities = sorted(
        ((t, row['average']) for t, row in before['defensive'].items()
         if row['average'] is not None and row['average'] > 1.001),
        key=lambda x: x[1], reverse=True,
    )
    worst = vulnerabilities[0][1] if vulnerabilities else 1.0
    urgent = {t for t, value in vulnerabilities if value >= worst - 0.05}
    active = { _key(str(x.get('Pokemon') or x.get('pokemon') or '')) for x in team }
    indexed = {_candidate_for_display(c).casefold():dict(c) for c in candidates if _candidate_name(c)}
    known = {rec.pokemon_name.casefold():rec for rec in original}
    source = dict(indexed)
    if not include_coverage_only:
        source = {k:v for k,v in source.items() if k in known}
    ranked: list[ComplementarySuggestion] = []
    for label, entry in source.items():
        if _key(_candidate_name(entry)) in active:
            continue
        original_rec = known.get(label)
        # No unsaved/unspecified ability is assumed. A recommended ability is
        # possible, not current; display and calculation both identify it.
        ability = _ability_from_summary(original_rec.summary) if original_rec else ''
        if not ability:
            ability = str(entry.get('Ability') or '')
        if not ability:
            abilities = entry.get('abilities')
            if isinstance(abilities, list) and len(abilities) == 1:
                ability = str(abilities[0])
        candidate = dict(entry, Ability=ability)
        # Prevent the absence of strategy eligibility from turning weak glass
        # cannons into defensive recommendations.
        if original_rec is None:
            if strategy_key == 'defensive_attrition':
                if _bulk(candidate) < 85:
                    continue
            else:
                stats = role_base_stats(candidate, 'offense') or {}
                if max(float(stats.get('ATK') or 0), float(stats.get('SPA') or 0)) < 100 \
                        and _bulk(candidate) < 85:
                    continue
        # Strategy moves are protected during hypothetical move selection;
        # they are defaults for *this scenario*, never forced on the player.
        guidance = strategy_move_guidance(strategy_key, candidate, list(moves_data), learnsets_data, limit=2)
        protected = tuple(dict.fromkeys(row[0] for row in guidance))[:2]
        try:
            potential = evaluate_candidate_coverage(
                team, candidate, type_chart, moves_data, learnsets_data,
                protected_moves=protected,
            )
        except (ValueError, KeyError, TypeError):
            # Unsupported/missing learnset isn't evidence of usable coverage.
            continue
        member = catalog_team_member(candidate, ability=ability)
        after = team_coverage([*team, member], type_chart, moves_data)
        improved = []
        new_immune = []
        benefit = 0.0
        urgent_gain = 0.0
        urgent_fixed = []
        for t in type_chart:
            old = before['defensive'][t]
            new = after['defensive'][t]
            old_average, new_average = old['average'], new['average']
            if old_average is None or new_average is None:
                continue
            reduction = old_average - new_average
            # Prioritize fixing weaknesses over adding yet another resistance.
            if reduction > 0.05:
                improved.append(t)
            # Averaging in another neutral team member also lowers an average
            # above 1x, but that is *dilution*, not a genuine defensive answer.
            # Reserve the urgent-weakness bonus for actual resistances/immunities.
            new_member = next((m for m in new['members']
                               if m['slot'] == len(team)), None)
            new_multiplier = new_member['multiplier'] if new_member else None
            if (t in urgent and reduction > 0 and new_multiplier is not None
                    and new_multiplier < 0.999):
                urgent_gain += reduction * (12.0 + 6.0 * (old_average - 1.0))
                if reduction >= 0.05:
                    urgent_fixed.append(t)
            if new['has_immunity'] and not old['has_immunity']:
                new_immune.append(t)
            if reduction > 0:
                benefit += reduction * (2.0 if old_average > 1.001 else 0.65)
            else:
                benefit += reduction * (1.25 if old_average >= 1.0 else 0.85)
        # A serious weakness matters more than several insignificant gains.
        # Still charge for any new above-neutral exposures via `benefit`.
        def_score = max(-5.0, min(10.0, benefit + urgent_gain)) + 1.1 * len(new_immune)
        new_types = tuple(potential['newly_covered_types'])
        off_score = min(8.0, len(new_types))
        if strategy_key == 'defensive_attrition':
            context = 0.7 * def_score + 0.3 * off_score
        elif strategy_key == 'status_control_punish':
            context = (0.65 * def_score + 0.35 * off_score) if urgent else (0.45 * def_score + 0.55 * off_score)
        else:
            context = 0.25 * def_score + 0.75 * off_score
        # The candidate may be new to our list; only add if it offers a real,
        # measurable contribution and the strategy is already complete.
        if original_rec is None and context < (1.2 if strategy_key == 'defensive_attrition' else 1.6):
            continue
        rec = original_rec or StrategyRecommendationCandidate(
            strategy_key, 'pokemon', _candidate_for_display(entry), None, None,
            0.0, 'Strong', 2, (), (), (),
            f"Add {_candidate_for_display(entry)} for complementary coverage. Projected strategy readiness remains Strong.",
        )
        # The on-card reason uses the *same* marginal contributions as ranking.
        # A strategy specialist may still be selected for coverage once the core
        # requirements are established. Before Strong, the UI says Core Strategy.
        if strategy_key == 'defensive_attrition':
            defensive_weight, offensive_weight = 0.7, 0.3
        elif strategy_key == 'status_control_punish':
            defensive_weight, offensive_weight = ((0.65, 0.35) if urgent else (0.45, 0.55))
        else:
            defensive_weight, offensive_weight = 0.25, 0.75
        defense_contribution = max(0.0, defensive_weight * def_score)
        offense_contribution = max(0.0, offensive_weight * off_score)
        complementary = (original_rec is None or
                         (context >= 1.4 and
                          (defense_contribution >= 1.0 or offense_contribution >= 1.0)))
        focus = ''
        if complementary:
            has_defense = defense_contribution >= 0.75
            has_offense = offense_contribution >= 0.75
            if has_defense and has_offense and min(defense_contribution, offense_contribution) >= 0.42 * max(defense_contribution, offense_contribution):
                focus = 'Both'
            elif has_defense and (defense_contribution >= offense_contribution or not has_offense):
                focus = 'Defense'
            elif has_offense:
                focus = 'Offense'
            elif defense_contribution >= offense_contribution:
                focus = 'Defense'
            else:
                focus = 'Offense'
        explanatory = []
        if urgent_fixed:
            explanatory.append('addresses team weakness to ' + ', '.join(urgent_fixed[:2]) + ' attacks')
        if improved:
            explanatory.append('lowers average defensive exposure to ' + ', '.join(improved[:4]) + ' attacks')
        if new_immune:
            explanatory.append('offers a possible immunity to ' + ', '.join(new_immune[:3]))
        if new_types:
            explanatory.append('can add super-effective moves against ' + ', '.join(new_types[:5]))
        notes = tuple((move['name'], tuple(move['targets']), move['availability'])
                      for move in potential['moves'] if move['name'] not in protected and move.get('targets'))
        if notes:
            named = ', '.join(f"{name} ({', '.join(types[:3])})" for name, types, _ in notes[:2])
            explanatory.append('coverage move options: ' + named)
        if explanatory:
            rec = replace(rec, summary=rec.summary + ' Team coverage: ' + '; '.join(explanatory) + '.')
        ranked.append(ComplementarySuggestion(rec, tuple(potential['proposed_moves']), notes,
            new_types, tuple(improved), tuple(new_immune), context, original_rec is None,
            'Complementary Coverage' if complementary else 'Core Strategy', focus,
            tuple(urgent_fixed)))
    # Compare existing strategy scores on a relative scale; preserve that
    # signal, but place majority weight on team-specific complementarity.
    normal = [c.recommendation.score for c in ranked if not c.coverage_only]
    lo, hi = (min(normal), max(normal)) if normal else (0.0, 1.0)
    def ordering(row: ComplementarySuggestion):
        base = (row.recommendation.score - lo) / (hi - lo) if hi > lo and not row.coverage_only else 0.0
        return (0.35 * base + 0.65 * max(0.0, min(1.0, row.projected_score / 5.0)),
                row.projected_score, row.recommendation.score)
    ranked.sort(key=ordering, reverse=True)
    return ranked
