import json, glob, os, math, csv

with open('tests/tmp_chunk035_input.json', encoding='utf-8') as f:
    items = json.load(f)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(a))

raw_records = []

# 1. settlement_sources/*.json (dict of settlements with coords=[lat, lng])
for p in glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/*.json'):
    if 'wave1' in p: continue
    with open(p, encoding='utf-8') as f:
        data = json.load(f)
    setts = data.get('settlements') if isinstance(data, dict) else data
    if isinstance(setts, dict):
        for k, r in setts.items():
            if isinstance(r, dict):
                r['_key'] = k
                r['_src_file'] = os.path.basename(p)
                r['_coords_latlng'] = True
                raw_records.append(r)
    elif isinstance(setts, list):
        for r in setts:
            if isinstance(r, dict):
                r['_src_file'] = os.path.basename(p)
                r['_coords_latlng'] = True
                raw_records.append(r)

# 2. 0.raw_sites/*.json, *.geojson, *.csv
for p in glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/*'):
    bn = os.path.basename(p)
    if bn.startswith('summary_'): continue
    if p.endswith('.json') or p.endswith('.geojson'):
        try:
            with open(p, encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    if k == 'features' and isinstance(v, list):
                        for r in v:
                            if isinstance(r, dict) and r.get('geometry') and r['geometry'].get('coordinates'):
                                c = r['geometry']['coordinates']
                                props = dict(r.get('properties') or {})
                                props['_lat'] = c[1]; props['_lng'] = c[0]; props['_src_file'] = bn
                                raw_records.append(props)
                    elif isinstance(v, list):
                        for r in v:
                            if isinstance(r, dict):
                                r['_src_file'] = bn; raw_records.append(r)
                    elif isinstance(v, dict):
                        v['_key'] = k; v['_src_file'] = bn; raw_records.append(v)
            elif isinstance(data, list):
                for r in data:
                    if isinstance(r, dict):
                        r['_src_file'] = bn; raw_records.append(r)
        except Exception:
            pass
    elif p.endswith('.csv'):
        try:
            with open(p, encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for r in reader:
                    r['_src_file'] = bn
                    raw_records.append(r)
        except Exception:
            pass

def get_lat_lng(r):
    if '_lat' in r and '_lng' in r:
        try: return float(r['_lat']), float(r['_lng'])
        except: return None, None
    for lk, gk in [('lat', 'lng'), ('lat', 'lon'), ('latitude', 'longitude'), ('Lat', 'Lon'), ('LAT', 'LON'), ('y', 'x')]:
        if lk in r and gk in r and r[lk] not in (None, '') and r[gk] not in (None, ''):
            try: return float(r[lk]), float(r[gk])
            except: pass
    if 'll' in r and isinstance(r['ll'], list) and len(r['ll']) == 2:
        try: return float(r['ll'][0]), float(r['ll'][1])
        except: pass
    if 'coords' in r and isinstance(r['coords'], list) and len(r['coords']) == 2:
        try:
            if r.get('_coords_latlng'):
                return float(r['coords'][0]), float(r['coords'][1])
            return float(r['coords'][1]), float(r['coords'][0])
        except: pass
    return None, None

grid = {}
for r in raw_records:
    la, lo = get_lat_lng(r)
    if la is None or not (-90 <= la <= 90 and -180 <= lo <= 180): continue
    r['_la'] = la; r['_lo'] = lo
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
                if d <= 2.5:
                    rc = {k: v for k, v in r.items() if k not in ('_la', '_lo', '_coords_latlng', 'population', 'urban_population') and v not in (None, '', [])}
                    rc['_dist_km'] = round(d, 3)
                    matches.append(rc)
    matches.sort(key=lambda x: x['_dist_km'])
    out[it['key']] = matches[:5]

with open('tests/tmp_chunk035_local_matches.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

matched = sum(1 for v in out.values() if v)
print(f'Total records: {len(raw_records)}, Matched: {matched}/{len(items)}')
for it in items:
    if not out[it['key']]:
        print('UNMATCHED:', it['key'], it['c'], it['r'], it['ll'])
