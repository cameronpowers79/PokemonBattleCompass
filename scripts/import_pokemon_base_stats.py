"""Build data/pokemon_base_stats_swsh.json from PokéAPI's source CSV tables.

Run from the Pokémon Battle Compass project root:
    python scripts/import_pokemon_base_stats.py

Uses the existing Journey catalog and canonical identity resolver, never a
hand-curated species list. Download happens only when running this importer;
the generated JSON is fully offline thereafter.
"""
from __future__ import annotations

import csv
import io
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = 'https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/'
STATS = ('HP', 'ATK', 'DEF', 'SPA', 'SPD', 'SPE')
STAT_IDS = {str(i): key for i, key in enumerate(STATS, 1)}


def fetch_csv(name: str) -> list[dict[str, str]]:
    url = BASE_URL + name
    request = urllib.request.Request(url, headers={'User-Agent': 'PokemonBattleCompass-BaseStats-Importer/1.0'})
    with urllib.request.urlopen(request, timeout=45) as response:
        content = response.read().decode('utf-8-sig')
    return list(csv.DictReader(io.StringIO(content)))


def build(catalog: list[dict], pokemon_rows: list[dict], stat_rows: list[dict], resolver):
    by_name = {p['identifier']: p['id'] for p in pokemon_rows}
    by_id = {}
    for r in stat_rows:
        stat_name = STAT_IDS.get(r['stat_id'])
        if stat_name:
            by_id.setdefault(r['pokemon_id'], {})[stat_name] = int(r['base_stat'])

    candidates = []
    for row in catalog:
        name = row.get('pokemon') or row.get('Pokemon')
        if not name:
            continue
        low = str(name).casefold()
        variants = ({'Gender': 'Male'}, {'Gender': 'Female'}) if low == 'meowstic' or low == 'indeedee' else ({},)
        if low == 'toxtricity':
            variants = ({'Form': 'Amped'}, {'Form': 'Low Key'})
        if low == 'urshifu':
            variants = ({'Form': 'Single Strike'}, {'Form': 'Rapid Strike'})
        for variant in variants:
            pid = resolver(name, gender=variant.get('Gender'), form=variant.get('Form'))
            candidates.append((name, pid, variant))

    results = {}
    missing = []
    for label, key, detail in candidates:
        if not key or key not in by_name:
            missing.append({'pokemon': label, 'pokemon_id': key, **detail, 'reason': 'PokéAPI identity unavailable'})
            continue
        values = by_id.get(by_name[key], {})
        if set(values) != set(STATS):
            missing.append({'pokemon': label, 'pokemon_id': key, **detail, 'reason': 'incomplete base stats'})
            continue
        results[key] = {'pokemon_id': key, **{stat: values[stat] for stat in STATS}}

    return [results[k] for k in sorted(results)], missing


def main():
    import sys
    sys.path.insert(0, str(ROOT))
    from engine.pokemon_identity import resolve_pokemon_id

    catalog_path = ROOT / 'data' / 'journey_pokemon.json'
    target = ROOT / 'data' / 'pokemon_base_stats_swsh.json'
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    records, missing = build(catalog, fetch_csv('pokemon.csv'), fetch_csv('pokemon_stats.csv'), resolve_pokemon_id)
    if not records:
        raise RuntimeError('No stats were matched. Check data sources before writing output.')
    target.write_text(json.dumps(records, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Saved {len(records)} form-specific base-stat records to {target}')
    if missing:
        report = ROOT / 'data' / 'pokemon_base_stats_import_unmatched.json'
        report.write_text(json.dumps(missing, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f'WARNING: {len(missing)} unmatched forms. Review {report} before treating coverage as complete.')
    else:
        print('Validated: all Journey final-form candidates resolved, six stats each.')


if __name__ == '__main__':
    main()
