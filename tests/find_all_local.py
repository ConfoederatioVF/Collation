import json, glob, math, os
from query_chunk040 import INPUT

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(a))

def extract_rows(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ('settlements', 'records', 'places', 'features', 'data', 'rows'):
            if k in obj and isinstance(obj[k], list):
                return obj[k]
        out = []
        for k, v in obj.items():
            if isinstance(v, list):
                out.extend(v)
        return out
    return []

files = (
    glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/*.json') +
    glob.glob('histmap/1.data_raw/population_regional/QUIPU/*/*/*_settlements.json')
)

hits = {x['key']: [] for x in INPUT}
for fp in files:
    try:
        data = json.load(open(fp, encoding='utf-8'))
    except Exception:
        continue
    rows = extract_rows(data)
    fn = os.path.basename(fp)
    for row in rows:
        if not isinstance(row, dict):
            continue
        props = row.get('properties', row)
        rname = str(props.get('name') or props.get('n') or props.get('nombre') or props.get('label') or props.get('place') or '')
        rlat = props.get('lat') or props.get('latitude') or props.get('y')
        rlng = props.get('lng') or props.get('lon') or props.get('longitude') or props.get('x')
        if rlat is None and isinstance(row.get('ll'), list):
            rlat, rlng = row['ll'][0], row['ll'][1]
        if rlat is None and isinstance(row.get('geometry'), dict):
            c = row['geometry'].get('coordinates', [])
            if len(c) >= 2:
                rlng, rlat = c[0], c[1]
        if rlat is None or rlng is None:
            continue
        try:
            rlat, rlng = float(rlat), float(rlng)
        except Exception:
            continue
        for item in INPUT:
            d = haversine(item['ll'][0], item['ll'][1], rlat, rlng)
            if d < 2.0:
                if item['n'].lower()[:4] in rname.lower() or rname.lower()[:4] in item['n'].lower() or d < 0.2:
                    compact = {k: v for k, v in props.items() if k not in ('pop', 'population', 'years', 'timeline') and len(str(v)) < 500}
                    hits[item['key']].append({'file': fn, 'dist_km': round(d, 3), 'data': compact})

with open('tests/chunk040_all_local.json', 'w', encoding='utf-8') as f:
    json.dump(hits, f, ensure_ascii=False, indent=2)
print("Matched items:", sum(1 for v in hits.values() if v))
