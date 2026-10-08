"""Targeted scoring checks without importing unrelated battle-engine modules."""
import ast
from pathlib import Path
source = Path(__file__).parent / 'engine' / 'strategy_capabilities.py'
tree = ast.parse(source.read_text())
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_defensive_attrition_quality')
namespace = {}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
quality = namespace['_defensive_attrition_quality']

def score(name, ability, moves):
    return quality({'Pokemon': name, 'Ability': ability}, set(moves), set())

checks = {
    'Corviknight defense + Body Press': score('Corviknight', 'Pressure', ['Iron Defense', 'Body Press', 'Protect', 'Rest']),
    'Avalugg defense + Body Press + Recover': score('Avalugg', 'Own Tempo', ['Iron Defense','Body Press','Recover','Protect']),
    'Ferrothorn contact punishment + defense': score('Ferrothorn', 'Iron Barbs', ['Iron Defense','Body Press','Leech Seed','Protect']),
    'Toxapex Regenerator + Recover + poison': score('Toxapex', 'Regenerator', ['Recover','Toxic','Protect']),
    'Rest and Protect only': score('Example', 'Pressure', ['Rest', 'Protect']),
    'Recover and Protect only': score('Example', 'Pressure', ['Recover', 'Protect']),
    'Iron Defense only': score('Example', 'Pressure', ['Iron Defense']),
    'Iron Defense + Body Press': score('Example', 'Pressure', ['Iron Defense', 'Body Press']),
}
for name, value in checks.items():
    print(f'{name}: {value:.1f}')
assert checks['Iron Defense + Body Press'] > checks['Iron Defense only']
assert checks['Rest and Protect only'] < checks['Recover and Protect only']
assert checks['Corviknight defense + Body Press'] > checks['Rest and Protect only']
assert checks['Ferrothorn contact punishment + defense'] > checks['Iron Defense + Body Press']
assert checks['Toxapex Regenerator + Recover + poison'] > checks['Rest and Protect only']
print('PASS: 5 focused defensive scoring assertions')
