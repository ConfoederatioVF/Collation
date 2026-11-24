import json, os, glob, math

items = json.load(open('tests/tmp_input_029.json', encoding='utf-8'))
root = 'histmap/1.data_raw/population_regional/QUIPU'

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))

sett_by_key = {}
sett_list = []
for p in glob.glob(os.path.join(root, '*', '*', '*_settlements.json')):
    fname = os.path.basename(p)
    try:
        data = json.load(open(p, encoding='utf-8'))
        if isinstance(data, dict):
            for k, r in data.items():
                if not isinstance(r, dict): continue
                c = r.get('coords')
                if isinstance(c, list) and len(c) >= 2:
                    rec = (fname, k, float(c[0]), float(c[1]), r)
                    sett_by_key.setdefault(k, []).append(rec)
                    sett_list.append(rec)
    except Exception as e:
        print('err', p, e)

# Also check hgis_indias_colonial_raw.json
hgis_path = os.path.join(root, '_shared/settlement_sources/hgis_indias_colonial_raw.json')
hgis = []
if os.path.exists(hgis_path):
    hd = json.load(open(hgis_path, encoding='utf-8'))
    if isinstance(hd, list): hgis = hd
    elif isinstance(hd, dict):
        for v in hd.values():
            if isinstance(v, list): hgis = v; break

# Check ICANH and SIGDA
icanh = []
icanh_path = os.path.join(root, '_shared/sites_quipu_andes_cone/0.raw_sites/raw_colombia_icanh_sitios.json')
if os.path.exists(icanh_path):
    d = json.load(open(icanh_path, encoding='utf-8'))
    icanh = d if isinstance(d, list) else d.get('features', d.get('data', []))

sigda = []
sigda_path = os.path.join(root, '_shared/sites_quipu_andes_cone/0.raw_sites/raw_peru_sigda.json')
if os.path.exists(sigda_path):
    d = json.load(open(sigda_path, encoding='utf-8'))
    sigda = d if isinstance(d, list) else d.get('features', d.get('data', []))

out = []
for it in items:
    lat, lng = it['ll']
    key = it['key']
    matches = []
    # Exact key or nearby coord
    seen_files = set()
    for fname, k, rlat, rlng, r in sett_by_key.get(key, []):
        seen_files.add((fname, k))
        matches.append({
            'file': fname,
            'key_match': True,
            'name': r.get('name'),
            'other_names': r.get('other_names'),
            'sources': r.get('sources'),
            'provenance_source': r.get('provenance_source'),
            'notes': r.get('notes'),
            'period': r.get('period'),
            'culture': r.get('culture'),
            'foundation_year': r.get('foundation_year'),
            'pop_years': sorted(list((r.get('population') or {}).keys()))
        })
    for fname, k, rlat, rlng, r in sett_list:
        if (fname, k) in seen_files: continue
        if abs(rlat - lat) < 0.03 and abs(rlng - lng) < 0.03:
            d = haversine(lat, lng, rlat, rlng)
            if d < 2.0:
                matches.append({
                    'file': fname,
                    'key_match': False,
                    'other_key': k,
                    'dist_km': round(d, 2),
                    'name': r.get('name'),
                    'other_names': r.get('other_names'),
                    'sources': r.get('sources'),
                    'provenance_source': r.get('provenance_source'),
                    'pop_years': sorted(list((r.get('population') or {}).keys()))
                })
    out.append({
        'key': key, 'n': it['n'], 'c': it['c'], 'r': it['r'], 'll': it['ll'],
        'ey': it['ey'], 'ly': it['ly'], 'al': it.get('al'), 'ex': it.get('ex'),
        'local_matches': matches
    })

json.dump(out, open('tests/tmp_local_context.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Matched settlements:', sum(1 for x in out if x['local_matches']), 'out of', len(out))
