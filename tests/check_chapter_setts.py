import json, glob, os

with open('tests/chunk025_input.json', encoding='utf-8') as f:
    inp = json.load(f)

keys = {x['key']: x for x in inp}

# Search all *_settlements.json in QUIPU
found = {k: [] for k in keys}
for fn in glob.glob('histmap/1.data_raw/population_regional/QUIPU/*/*/*_settlements.json'):
    with open(fn, encoding='utf-8') as f:
        d = json.load(f)
    # structure could be dict of settlements or list
    items = []
    if isinstance(d, dict):
        if 'settlements' in d:
            s = d['settlements']
            items = list(s.values()) if isinstance(s, dict) else s
        else:
            for k2, v2 in d.items():
                if isinstance(v2, dict):
                    v2.setdefault('key', k2)
                    items.append(v2)
    elif isinstance(d, list):
        items = d
    for it in items:
        if not isinstance(it, dict): continue
        k = it.get('key')
        if k in found:
            copy = {kk: vv for kk, vv in it.items() if kk != 'population'}
            copy['_file'] = os.path.basename(fn)
            found[k].append(copy)

for k, x in keys.items():
    if found[k]:
        print(f"=== {k} ===")
        for rec in found[k]:
            print(" ", json.dumps(rec, ensure_ascii=False)[:400])
    else:
        print(f"=== {k} === [NOT IN CHAPTER SETTLEMENTS]")
