"""Dependency-free structural regression tests; full Flet UAT is still required."""
from pathlib import Path
import ast
root=Path(__file__).resolve().parent
paths=[root/'ui/components/recommendation_card.py',root/'ui/views/battle_compass_view.py',root/'ui/viewmodels/battle_compass_vm.py']
for path in paths:
    compile(path.read_text(encoding='utf8'),str(path),'exec')
card,view,vm=(path.read_text(encoding='utf8') for path in paths)
assert 'def _build_strategy_fit_meter' in card
assert 'Direct Matchup' in card and 'Matchup Strength' in card
assert 'strategy_fit=tactical_fit' in view
assert 'selected_plan.attack_move_score' in view
assert 'selected_plan.attack_score_conditional' in view
assert 'Conditional Move Score (poison active)' in view
assert 'show_move_score=show_move_score' in view
assert 'sequence_heading=f"{screen} → {payoff_name}"' in vm
assert 'fit=fit, fit_rank=rank' in vm
assert 'if plan_kind == "screen_followup_assumed" and payoff' in vm
assert 'selected_strategy_plan.conditional_move_score' in vm
assert 'Direct fallback if the screen is absent' in vm
assert 'evaluate_poison_attrition_plans(' in vm
assert 'select_poison_attrition_plan(' in vm
print('PASS: 14 targeted structural checks and 3 compilation checks')
