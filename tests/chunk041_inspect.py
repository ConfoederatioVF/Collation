import json, glob, math, os

with open('tests/chunk041_input.json', encoding='utf-8') as f:
    items = json.load(f)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(min(1.0, a)))

hgis_obj = json.load(open('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/hgis_indias_colonial_raw.json', encoding='utf-8'))['settlements']
hgis_raw = list(hgis_obj.values()) if isinstance(hgis_obj, dict) else hgis_obj

raw_setts = []
for p in glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/raw_setts_*.json'):
    data = json.load(open(p, encoding='utf-8'))
    arr = list(data.values()) if isinstance(data, dict) and 'settlements' not in data and 'features' not in data else (
        data.get('settlements', data.get('features', [])) if isinstance(data, dict) else data
    )
    if isinstance(arr, dict):
        arr = list(arr.values())
    for x in arr:
        if isinstance(x, dict):
            raw_setts.append((os.path.basename(p), x))

arch_files = glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/**/*', recursive=True)
arch_sites = []
for p in arch_files:
    if p.endswith('.json') or p.endswith('.geojson'):
        try:
            d = json.load(open(p, encoding='utf-8'))
            if isinstance(d, dict) and 'features' in d:
                for feat in d['features']:
                    geom = feat.get('geometry') or {}
                    coords = geom.get('coordinates')
                    if coords and len(coords) >= 2:
                        arch_sites.append((os.path.basename(p), float(coords[1]), float(coords[0]), feat.get('properties', {})))
            elif isinstance(d, list):
                for row in d:
                    if not isinstance(row, dict): continue
                    lat = row.get('lat') or row.get('latitude')
                    lon = row.get('lon') or row.get('lng') or row.get('longitude')
                    if lat is not None and lon is not None:
                        arch_sites.append((os.path.basename(p), float(lat), float(lon), row))
        except Exception:
            pass

print(f"Loaded hgis={len(hgis_raw)}, raw_setts={len(raw_setts)}, arch_sites={len(arch_sites)}")

results = {}
for it in items:
    lat, lon = it['ll']
    k = it['key']
    res = {'hgis': [], 'raw': [], 'arch': []}
    for h in hgis_raw:
        if not isinstance(h, dict): continue
        hlat = h.get('lat') or (h.get('ll')[0] if isinstance(h.get('ll'), list) else None)
        hlon = h.get('lng') or h.get('lon') or (h.get('ll')[1] if isinstance(h.get('ll'), list) else None)
        if hlat is not None and hlon is not None:
            d = haversine(lat, lon, float(hlat), float(hlon))
            if d <= 5.0:
                res['hgis'].append((round(d, 2), h))
    for fn, r in raw_setts:
        rlat = r.get('lat') or (r.get('ll')[0] if isinstance(r.get('ll'), list) else None)
        rlon = r.get('lng') or r.get('lon') or (r.get('ll')[1] if isinstance(r.get('ll'), list) else None)
        if rlat is not None and rlon is not None:
            d = haversine(lat, lon, float(rlat), float(rlon))
            if d <= 2.0:
                res['raw'].append((round(d, 2), fn, r))
    for fn, alat, alon, props in arch_sites:
        d = haversine(lat, lon, alat, alon)
        if d <= 2.0:
            res['arch'].append((round(d, 2), fn, props))
    results[k] = res

with open('tests/chunk041_local_matches.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

matched_hgis = sum(1 for v in results.values() if v['hgis'])
matched_raw = sum(1 for v in results.values() if v['raw'])
matched_arch = sum(1 for v in results.values() if v['arch'])
print(f"Matches: hgis={matched_hgis}, raw={matched_raw}, arch={matched_arch}")
