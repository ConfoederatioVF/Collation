import json
import os

data = json.load(open('tests/chunk038_local_matches.json', encoding='utf-8'))

for i, d in enumerate(data, 1):
    print(f"=== {i:2d}. {d['key']} (n={d['n']}, c={d['c']}, r={d['r']}, ey={d['ey']}, ly={d['ly']}, ll={d['ll']}) ===")
    for m in d['matches']:
        print(f"   FILE: {m['file']} | SK: {m['sk']} | name: {m['name']} | subr: {m['subregion']}")
        if m.get('other_names'):
            print(f"   other_names: {m['other_names']}")
        if m.get('culture') or m.get('period') or m.get('site_type'):
            print(f"   culture={m.get('culture')} period={m.get('period')} site_type={m.get('site_type')}")
        print(f"   years={m.get('years')} | src={m.get('source') or m.get('sources')}")
