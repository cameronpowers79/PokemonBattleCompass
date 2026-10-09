import ast
from pathlib import Path
from dataclasses import dataclass
source=Path(__file__).parent/'engine/strategy_capabilities.py'
tree=ast.parse(source.read_text())
wanted={'_canonical_strategy_key','_capability_provider_names','_role_satisfied','_matched_weather_roles','_screen_offensive_beneficiaries','evaluate_strategy_viability'}
nodes=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in wanted]
ns={'_STRATEGY_ALIASES':{'poison_attrition':'poison_attrition','poison_offensive_pressure':'poison_offensive_pressure','defensive_attrition':'defensive_attrition'},'_STRATEGY_LABELS':{'poison_attrition':'Poison – Attrition','poison_offensive_pressure':'Poison – Offensive Pressure','defensive_attrition':'Defensive Attrition'},'_VIABILITY_RANK':{'Incomplete':0,'Viable':1,'Strong':2},'__name__':'test'}
@dataclass
class StrategicCapabilityResult:
    pokemon_name:str
    capability_keys:tuple
ns['StrategicCapabilityResult']=StrategicCapabilityResult
@dataclass
class StrategyViabilityResult:
    strategy_key:str
    viability:str
    viability_rank:int
    summary:str
    required_roles:tuple
    satisfied_required_roles:tuple
    missing_required_roles:tuple
    supporting_roles:tuple
    contributing_pokemon:tuple
    one_change_away:bool
ns['StrategyViabilityResult']=StrategyViabilityResult
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)
check=ns['evaluate_strategy_viability']
def member(name,*keys):return StrategicCapabilityResult(name,tuple(keys))
poison='STATUS_POISON_RELIABLE'; anchor='RELIABLE_RECOVERY'; payoff='POISON_EXPLOIT_DAMAGE'; denial='SETUP_DENIAL'
cases=[
('attr single hybrid','poison_attrition',[member('Toxapex',poison,anchor)],'Viable'),
('attr distinct no redundancy','poison_attrition',[member('Roserade',poison),member('Toxapex',anchor)],'Viable'),
('attr redundant sources','poison_attrition',[member('Roserade',poison),member('Pyukumuku',poison,anchor)],'Strong'),
('attr redundant anchors','poison_attrition',[member('Roserade',poison),member('Pyukumuku',anchor),member('Toxapex',anchor)],'Strong'),
('off single hybrid','poison_offensive_pressure',[member('Salazzle',poison,payoff)],'Viable'),
('off separate roles','poison_offensive_pressure',[member('Roserade',poison),member('Chandelure',payoff)],'Viable'),
('off redundant poison','poison_offensive_pressure',[member('Roserade',poison),member('Toxapex',poison,payoff)],'Strong'),
('off redundant payoff','poison_offensive_pressure',[member('Roserade',poison),member('Chandelure',payoff),member('Salazzle',payoff)],'Strong'),
('attr missing pressure','poison_attrition',[member('Toxapex',anchor)],'Incomplete'),
('nonpoison unchanged','defensive_attrition',[member('Corviknight','DEFENSE_SETUP','BODY_PRESS')],'Viable'),
]
for label,strategy,members,expected in cases:
    actual=check(strategy,members).viability
    assert actual==expected,(label,actual,expected)
    print(f'PASS {label}: {actual}')
print(f'{len(cases)} focused viability checks passed')
