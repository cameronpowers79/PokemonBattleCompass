import ast, json
from pathlib import Path
src=Path('/mnt/data/battle_compass_vm.py').read_text()
mod=ast.parse(src)
fnames={'_status_applicable','_status_payoff','_status_speed_analysis','_status_control_battle_plan'}
body=[node for node in mod.body if isinstance(node,ast.FunctionDef) and node.name in fnames]
body += [node for node in mod.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_STATUS_MOVES' for t in node.targets)]
moves={r['Move']:r for r in json.load(open('/mnt/data/moves(7).json'))}
def get_moves(mon,unused):return [moves[mon[f'Move{i}']] for i in range(1,5) if mon.get(f'Move{i}') in moves]
def calc(a,d,m,items,ability):
    if m.get('Category')=='Status':return 0
    if m.get('Type')=='Ghost' and d.get('Type1')=='Normal':return 0
    return float(m.get('Power') or 0)*(2 if m.get('Type')=='Fire' and d.get('Type2')=='Steel' else 1)
class Mechanics:
    @staticmethod
    def get_item_speed_multiplier(mon,items):return 1
    @staticmethod
    def get_guaranteed_weather(a,d):return 'Rain' if d.get('Weather')=='Rain' else None
import sys,types
m=types.ModuleType('engine'); m.__path__=[]; mm=types.ModuleType('engine.mechanics')
mm.get_item_speed_multiplier=Mechanics.get_item_speed_multiplier
mm.get_guaranteed_weather=Mechanics.get_guaranteed_weather
sys.modules.setdefault('engine',m);sys.modules['engine.mechanics']=mm
ns={'get_moves':get_moves,'calculate_move_score':calc,'get_stat':lambda p,k:float(p.get(k) or 1)}
exec(compile(ast.Module(body=body,type_ignores=[]),'<sut>','exec'),ns)
def match(n,ratio,score=200):return {'Pokemon':n,'Ratio':ratio,'Best Move':'Heat Wave','Best MoveScore':score,'Incoming Worst Score':100,'Battle Notes':[]}
poison=[{'Pokemon':'Roserade','SPE':104,'Move1':'Toxic','Move2':'Stun Spore','Move3':'Venoshock','Move4':'Giga Drain'}]
opp={'Pokemon':'Barraskewda','SPE':160,'Type1':'Water'}
assert ns['_status_payoff'](poison,opp,moves,[],[],'poison')[3]=='Venoshock'
assert ns['_status_payoff'](poison,opp,moves,[],[],'paralysis') is None
flip,msg=ns['_status_speed_analysis'](poison[0],opp,'paralysis',[])
assert flip==1 and 'flips' in msg,msg
plan,payoff=ns['_status_control_battle_plan'](poison,opp,[match('Roserade',2)],list(moves.values()),[],[])
assert plan['lead_move']=='Stun Spore',plan
assert 'Speed' in plan['state_assumption']
opp['SPE']=80
plan,_=ns['_status_control_battle_plan'](poison,opp,[match('Roserade',2)],list(moves.values()),[],[])
assert plan['lead_move']=='Toxic',plan
assert 'Venoshock' in plan['sequence_heading'],plan
opp['SPE']=160;opp['Ability']='Swift Swim';opp['Weather']='Rain'
flip,msg=ns['_status_speed_analysis'](poison[0],opp,'paralysis',[])
assert flip==0 and 'no turn-order flip' in msg,msg
print('PASS: status compatible Venoshock, paralysis speed flip, Toxic wins without flip, Swift Swim rain')
