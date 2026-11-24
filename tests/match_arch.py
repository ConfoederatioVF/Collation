import json, glob, math, os

with open('tests/chunk025_input.json', encoding='utf-8') as f:
    inp = json.load(f)

arch = [x for x in inp if not x['r'].startswith(('arg_','bol_','chl_','col_','ecu_','per_','ven_','ury_','vp_','vng_','crp_'))]

def dist_km(ll1, ll2):
    return math.hypot((ll1[0]-ll2[0])*111.0, (ll1[1]-ll2[1])*111.0*math.cos(math.radians((ll1[0]+ll2[0])/2)))

sites = []
for fn in glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/*.json'):
    with open(fn, encoding='utf-8') as f:
        d = json.load(f)
    rows = d if isinstance(d, list) else d.get('sites', d.get('features', d.get('data', [])))
    if isinstance(d, dict) and not rows:
        for v in d.values():
            if isinstance(v, list):
                rows = v
                break
    for r in rows:
        if isinstance(r, dict):
            r['_src'] = os.path.basename(fn)
            sites.append(r)

for a in arch:
    matches = []
    for s in sites:
        lat = s.get('lat') or s.get('latitude') or (s.get('coords')[0] if isinstance(s.get('coords'), list) else None)
        lon = s.get('lon') or s.get('lng') or s.get('longitude') or (s.get('coords')[1] if isinstance(s.get('coords'), list) else None)
        if lat is None or lon is None:
            geom = s.get('geometry', {})
            if isinstance(geom, dict) and geom.get('type') == 'Point':
                lon, lat = geom['coordinates'][:2]
            elif isinstance(s.get('properties'), dict):
                p = s['properties']
                lat = p.get('lat') or p.get('latitude')
                lon = p.get('lon') or p.get('lng')
        if lat is not None and lon is not None:
            try:
                dk = dist_km(a['ll'], [float(lat), float(lon)])
                if dk < 3.0:
                    matches.append((dk, s))
            except Exception:
                pass
    matches.sort(key=lambda x: x[0])
    print(f"\nARCH: {a['key']} | n={a['n']} | c={a['c']} | r={a['r']} | ll={a['ll']} | ey={a['ey']} | ly={a['ly']} | al={a.get('al')}")
    for dk, s in matches[:5]:
        print(f"  {dk:.2f}km [{s['_src']}]: {json.dumps(s, ensure_ascii=False)[:400]}")
