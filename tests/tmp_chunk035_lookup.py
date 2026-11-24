import json, glob, os, math

with open('tests/tmp_chunk035_input.json', encoding='utf-8') as f:
    items = json.load(f)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(a))

# Load all raw sources
raw_records = []
for p in glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/*.json'):
    if 'wave1' in p: continue
    with open(p, encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list):
                for r in v:
                    r['_src_file'] = os.path.basename(p)
                    raw_records.append(r)
            elif isinstance(v, dict):
                v['_src_file'] = os.path.basename(p)
                raw_records.append(v)
    elif isinstance(data, list):
        for r in data:
            if isinstance(r, dict):
                r['_src_file'] = os.path.basename(p)
                raw_records.append(r)

# Also check 0.raw_sites
for p in glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/*'):
    if p.endswith('.json') or p.endswith('.geojson'):
        try:
            with open(p, encoding='utf-8') as f:
                data = json.load(f)
            feats = data.get('features', data) if isinstance(data, dict) else data
            if isinstance(feats, list):
                for r in feats:
                    if isinstance(r, dict):
                        if 'geometry' in r and r['geometry'] and 'coordinates' in r['geometry']:
                            c = r['geometry']['coordinates']
                            props = dict(r.get('properties') or {})
                            props['_lat'] = c[1]
                            props['_lng'] = c[0]
                            props['_src_file'] = os.path.basename(p)
                            raw_records.append(props)
                        else:
                            r['_src_file'] = os.path.basename(p)
                            raw_records.append(r)
        except Exception as e:
            pass

print('Total raw records loaded:', len(raw_records))

def get_lat_lng(r):
    if '_lat' in r and '_lng' in r:
        return float(r['_lat']), float(r['_lng'])
    for lk, gk in [('lat', 'lng'), ('lat', 'lon'), ('latitude', 'longitude'), ('y', 'x')]:
        if lk in r and gk in r and r[lk] is not None and r[gk] is not None:
            try:
                return float(r[lk]), float(r[gk])
            except:
                pass
    if 'll' in r and isinstance(r['ll'], list) and len(r['ll']) == 2:
        return float(r['ll'][0]), float(r['ll'][1])
    if 'coords' in r and isinstance(r['coords'], list) and len(r['coords']) == 2:
        return float(r['coords'][1]), float(r['coords'][0])
    return None, None

# Index raw records by rounded grid
grid = {}
for r in raw_records:
    la, lo = get_lat_lng(r)
    if la is None: continue
    r['_la'] = la
    r['_lo'] = lo
    gk = (round(la * 10), round(lo * 10))
    grid.setdefault(gk, []).append(r)

out = {}
for it in items:
    la, lo = it['ll']
    gx, gy = round(la * 10), round(lo * 10)
    matches = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for r in grid.get((gx+dx, gy+dy), []):
                d = haversine(la, lo, r['_la'], r['_lo'])
                if d <= 2.0:
                    rc = {k: v for k, v in r.items() if k not in ('_la', '_lo') and v not in (None, '', [])}
                    rc['_dist_km'] = round(d, 3)
                    matches.append(rc)
    matches.sort(key=lambda x: x['_dist_km'])
    out[it['key']] = matches[:5]

with open('tests/tmp_chunk035_local_matches.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

matched = sum(1 for v in out.values() if v)
print(f'Matched {matched}/{len(items)} items locally')
