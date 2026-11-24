import json, glob, os, math

wiki_res = json.load(open('tests/chunk040_wiki_summary.json', encoding='utf-8'))
from query_chunk040 import INPUT

# Search all settlement_sources and chapter settlements json for matching keys or nearby coords
local_hits = {x['key']: [] for x in INPUT}

files = (
    glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/*.json') +
    glob.glob('histmap/1.data_raw/population_regional/QUIPU/*/*/*_settlements.json') +
    glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/*.json')
)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(a))

input_by_key = {x['key']: x for x in INPUT}

for fp in files:
    try:
        data = json.load(open(fp, encoding='utf-8'))
    except Exception:
        continue
    rows = []
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        if 'settlements' in data and isinstance(data['settlements'], list):
            rows = data['settlements']
        elif 'features' in data and isinstance(data['features'], list):
            rows = data['features']
        else:
            for v in data.values():
                if isinstance(v, list):
                    rows.extend(v)
    fn = os.path.basename(fp)
    for row in rows:
        if not isinstance(row, dict):
            continue
        rname = str(row.get('name') or row.get('n') or row.get('site_name') or row.get('properties', {}).get('name', '') or '')
        rkey = str(row.get('key') or '')
        rlat = row.get('lat') or (row.get('ll', [None, None])[0] if isinstance(row.get('ll'), list) else None)
        rlng = row.get('lng') or row.get('lon') or (row.get('ll', [None, None])[1] if isinstance(row.get('ll'), list) else None)
        if rlat is None and isinstance(row.get('geometry'), dict):
            coords = row['geometry'].get('coordinates', [])
            if len(coords) >= 2:
                rlng, rlat = coords[0], coords[1]
        for item in INPUT:
            hit = False
            if rkey and rkey == item['key']:
                hit = True
            elif rlat is not None and rlng is not None:
                try:
                    if haversine(item['ll'][0], item['ll'][1], float(rlat), float(rlng)) < 1.5:
                        if item['n'].lower()[:5] in rname.lower() or rname.lower()[:5] in item['n'].lower():
                            hit = True
                except Exception:
                    pass
            if hit:
                # keep compact info
                compact = {k: v for k, v in row.items() if k not in ('geometry', 'pop', 'population', 'years') and len(str(v)) < 400}
                local_hits[item['key']].append({'file': fn, 'data': compact})

with open('tests/chunk040_local_hits.json', 'w', encoding='utf-8') as f:
    json.dump(local_hits, f, ensure_ascii=False, indent=2)

print("Local hits count:", sum(1 for v in local_hits.values() if v))
