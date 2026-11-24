import json
import math
import glob
import os

with open('tests/c053_input.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

def haversine_km(ll1, ll2):
    R = 6371.0
    lat1, lon1 = math.radians(ll1[0]), math.radians(ll1[1])
    lat2, lon2 = math.radians(ll2[0]), math.radians(ll2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))

# Scan all JSON files in settlement_sources and sites_quipu_andes_cone/0.raw_sites
dirs = [
    'histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/*.json',
    'histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/*.json',
]
files = []
for d in dirs:
    files.extend(glob.glob(d))

hits = {it['key']: [] for it in items}

def extract_coords_and_name(rec):
    if not isinstance(rec, dict):
        return None, None
    lat = rec.get('lat') or rec.get('latitude') or rec.get('y')
    lon = rec.get('lon') or rec.get('lng') or rec.get('longitude') or rec.get('x')
    if lat is None and 'll' in rec and isinstance(rec['ll'], list) and len(rec['ll']) == 2:
        lat, lon = rec['ll']
    if lat is None and 'coords' in rec and isinstance(rec['coords'], list) and len(rec['coords']) == 2:
        lat, lon = rec['coords']
    if lat is None and 'geometry' in rec and isinstance(rec['geometry'], dict):
        c = rec['geometry'].get('coordinates')
        if isinstance(c, list) and len(c) >= 2 and isinstance(c[0], (int, float)):
            lon, lat = c[0], c[1]
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return None, None
    return (lat, lon), rec

for fp in files:
    bn = os.path.basename(fp)
    if bn == 'wave1_harvest_summary.json' or bn.startswith('summary_'):
        continue
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        continue
    records = []
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        if 'features' in data and isinstance(data['features'], list):
            for feat in data['features']:
                props = feat.get('properties', {}) if isinstance(feat, dict) else {}
                props = dict(props)
                props['geometry'] = feat.get('geometry')
                records.append(props)
        elif 'settlements' in data and isinstance(data['settlements'], list):
            records = data['settlements']
        elif 'records' in data and isinstance(data['records'], list):
            records = data['records']
        elif 'sites' in data and isinstance(data['sites'], list):
            records = data['sites']
        else:
            for k, v in data.items():
                if isinstance(v, dict):
                    v2 = dict(v)
                    v2['_dict_key'] = k
                    records.append(v2)
                elif isinstance(v, list):
                    for sub in v:
                        if isinstance(sub, dict):
                            records.append(sub)
    for rec in records:
        ll, r = extract_coords_and_name(rec)
        if ll is None:
            continue
        for it in items:
            d = haversine_km(it['ll'], ll)
            if d <= 2.5:
                # compact summary
                compact = {k: v for k, v in r.items() if k not in ('geometry', 'pop', 'population', 'years', 'timeline') and v not in (None, '', [], {})}
                hits[it['key']].append({'file': bn, 'dist_km': round(d, 3), 'rec': compact})

with open('tests/c053_local_hits.json', 'w', encoding='utf-8') as f:
    json.dump(hits, f, ensure_ascii=False, indent=2)

found = sum(1 for v in hits.values() if v)
print(f"Matched {found}/{len(items)} items in local JSONs.")
