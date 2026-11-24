import json, glob, math, os

with open('tests/chunk025_input.json', encoding='utf-8') as f:
    inp = json.load(f)

def dist_km(ll1, ll2):
    lat1, lon1 = ll1
    lat2, lon2 = ll2
    return math.hypot((lat1 - lat2) * 111.0, (lon1 - lon2) * 111.0 * math.cos(math.radians((lat1 + lat2) / 2)))

with open('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/hgis_indias_colonial_raw.json', encoding='utf-8') as f:
    hgis = json.load(f)['settlements']

hgis_list = list(hgis.values()) if isinstance(hgis, dict) else hgis

raw_setts = []
for fn in glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/raw_setts_*.json'):
    with open(fn, encoding='utf-8') as f:
        d = json.load(f)
    s = d.get('settlements', {})
    if isinstance(s, dict):
        for k, v in s.items():
            v['_file'] = os.path.basename(fn)
            v['_key'] = k
            raw_setts.append(v)
    elif isinstance(s, list):
        for v in s:
            v['_file'] = os.path.basename(fn)
            raw_setts.append(v)

print(f"Loaded {len(hgis_list)} HGIS, {len(raw_setts)} raw_setts")
if hgis_list:
    print("HGIS sample:", json.dumps(hgis_list[0], ensure_ascii=False)[:300])
if raw_setts:
    print("raw_setts sample:", json.dumps(raw_setts[0], ensure_ascii=False)[:300])

# Match each input settlement
for item in inp:
    ll = item['ll']
    n = item['n'].lower()
    # Find closest HGIS within 15 km
    h_matches = []
    for h in hgis_list:
        h_ll = h.get('coords') or h.get('ll') or [h.get('lat'), h.get('lon') or h.get('lng')]
        if h_ll and h_ll[0] is not None and h_ll[1] is not None:
            dk = dist_km(ll, h_ll)
            if dk < 15.0:
                h_matches.append((dk, h))
    h_matches.sort(key=lambda x: x[0])

    r_matches = []
    for r in raw_setts:
        r_ll = r.get('coords') or r.get('ll') or [r.get('lat'), r.get('lon') or r.get('lng')]
        if r_ll and r_ll[0] is not None and r_ll[1] is not None:
            dk = dist_km(ll, r_ll)
            if dk < 5.0:
                r_matches.append((dk, r))
    r_matches.sort(key=lambda x: x[0])

    print(f"\n=== {item['key']} | n={item['n']} | c={item['c']} | r={item['r']} | ll={ll} | ey={item['ey']} | ly={item['ly']} | al={item.get('al')} | ex={item.get('ex')} ===")
    for dk, h in h_matches[:3]:
        print(f"  HGIS ({dk:.2f}km): {json.dumps(h, ensure_ascii=False)[:350]}")
    for dk, r in r_matches[:3]:
        rc = {k: v for k, v in r.items() if k != 'population'}
        print(f"  RAW ({dk:.2f}km): {json.dumps(rc, ensure_ascii=False)[:350]}")
