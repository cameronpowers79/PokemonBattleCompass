import ast
from pathlib import Path
src=Path('/mnt/data/battle_compass_vm.py').read_text()
mod=ast.parse(src)
functions=[n for n in mod.body if isinstance(n,ast.FunctionDef) and n.name in {'_status_applicable','_status_payoff','_status_control_battle_plan'}]
assigns=[n for n in mod.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_STATUS_MOVES' for t in n.targets)]
ns={}
ns['get_moves']=lambda p, moves_data: [dict(next((r for r in moves_data if r['Move']==p.get(f'Move{i}')),{})) for i in range(1,5) if p.get(f'Move{i}')]
ns['calculate_move_score']=lambda atk,defn,m,items,ability: float(m.get('Power') or 0) * (2 if m.get('Type')=='Ghost' else 1)
exec(compile(ast.Module(body=assigns+functions,type_ignores=[]),'<test>','exec'),ns)
team=[{'Pokemon':'Chandelure','Ability':'Flash Fire','Move1':'Will-O-Wisp','Move2':'Hex'},{'Pokemon':'Froslass','Move1':'Thunder Wave','Move2':'Hex'}]
moves=[{'Move':'Will-O-Wisp','Category':'Status','Accuracy':85},{'Move':'Thunder Wave','Category':'Status','Accuracy':90},{'Move':'Hex','Category':'Special','Power':65,'Type':'Ghost','ActivationCondition':'TargetAnyStatus','ActivationPowerMultiplier':2}]
opp={'Pokemon':'Dubwool','Type1':'Normal','Slot':1}
# Ghost is immune in actual battle; the scoring stub doesn't model that; tested branches only.
match=[{'Pokemon':'Chandelure','Ratio':2,'Worst Incoming Move':'Body Slam','Incoming Worst Score':40,'Battle Notes':[]},{'Pokemon':'Froslass','Ratio':1.5,'Worst Incoming Move':'Body Slam','Incoming Worst Score':60,'Battle Notes':[]}]
plan,payoff=ns['_status_control_battle_plan'](team,opp,match,moves,[],[])
assert plan['action_type']=='Status Setup',plan
assert payoff[2]==260 and payoff[3]==130,payoff
opp['Slot']=2
plan,payoff=ns['_status_control_battle_plan'](team,opp,match,moves,[],[])
assert plan['action_type']=='Status Payoff',plan
assert 'THIS opposing' in plan['condition_detail']
assert plan['attack_move_score']==260
assert ns['_status_applicable']({'Type1':'Ground','Type2':''},'Thunder Wave','paralysis') is False
assert ns['_status_applicable']({'Type1':'Fire','Type2':''},'Will-O-Wisp','burn') is False
assert ns['_status_applicable']({'Type1':'Dark','Ability':''},'Will-O-Wisp','burn') is True
print('6 tactical smoke assertions passed')
