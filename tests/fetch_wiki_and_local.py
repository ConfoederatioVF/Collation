import json, time, urllib.request, urllib.parse, glob, os

HEADERS = {'User-Agent': 'OperationViscountResearch/1.0 (contact: research@example.org)'}
def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))

items = json.load(open('tests/chunk043_input.json', encoding='utf-8'))
prev = {x['key']: x for x in json.load(open('tests/chunk043_wiki_geo.json', encoding='utf-8'))}

# 1. Finish Wikipedia geosearch + search sequentially
out = []
for i, it in enumerate(items):
    k = it['key']
    p = prev.get(k, {})
    if 'es_geo' in p and 'es_search' in p:
        out.append(p)
        continue
    lat, lng = it['ll']
    rec = {'key': k, 'n': it['n'], 'c': it['c'], 'r': it['r'], 'ey': it['ey']}
    try:
        u = f'https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json'
        d = fetch_json(u)
        rec['es_geo'] = [(g['title'], round(g['dist'])) for g in d.get('query',{}).get('geosearch',[])]
    except Exception as e:
        rec['es_geo_err'] = str(e)
    time.sleep(0.25)
    try:
        q = urllib.parse.quote(f"{it['n']} {it['c']}")
        u = f'https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json'
        d = fetch_json(u)
        rec['es_search'] = [s['title'] for s in d.get('query',{}).get('search',[])]
    except Exception as e:
        rec['es_search_err'] = str(e)
    time.sleep(0.25)
    out.append(rec)

json.dump(out, open('tests/chunk043_wiki_geo.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
errs = sum(1 for x in out if 'es_geo_err' in x or 'es_search_err' in x)
print('Wiki done, errs:', errs)

# 2. Match HGIS Indias by coords
hgis = json.load(open('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/hgis_indias_colonial_raw.json', encoding='utf-8'))
hrows = hgis['settlements']
hgis_hits = {}
for it in items:
    lat, lng = it['ll']
    for gid, r in hrows.items():
        c = r.get('coords')
        if not c or len(c)<2: continue
        if abs(c[0]-lat)<0.03 and abs(c[1]-lng)<0.03:
            hgis_hits.setdefault(it['key'], []).append({
                'name': r.get('name'), 'modern_name': r.get('modern_name'),
                'variants': r.get('variants'), 'provincia': r.get('colonial_province'),
                'partido': r.get('colonial_partido'), 'categoria': r.get('categoria'),
                'start_year': r.get('start_year'), 'obs_years': sorted({o.get('year') for o in r.get('observations',[]) if o.get('year')}),
                'sources': r.get('sources')[:2] if r.get('sources') else []
            })
json.dump(hgis_hits, open('tests/chunk043_hgis.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('HGIS hits:', len(hgis_hits))
