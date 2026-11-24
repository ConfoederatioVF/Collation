import json, math, os, glob, urllib.request, urllib.parse, time, concurrent.futures

HEADERS = {'User-Agent': 'ViscountToponymyResearch/1.0 (https://confoederatio.org)'}
INPUT_PATH = 'tests/_chunk032_input.json'
HGIS_PATH = 'histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/hgis_indias_colonial_raw.json'
RAW_SETTS_DIR = 'histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources'
SITES_DIR = 'histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites'

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(min(1.0, math.sqrt(a)))

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))

def load_local():
    hgis = json.load(open(HGIS_PATH, encoding='utf-8'))['settlements']
    hgis_list = list(hgis.values()) if isinstance(hgis, dict) else hgis
    raw_setts = {}
    for p in glob.glob(os.path.join(RAW_SETTS_DIR, 'raw_setts_*.json')):
        d = json.load(open(p, encoding='utf-8'))['settlements']
        if isinstance(d, dict):
            raw_setts.update(d)
    # Index arch sites lightly by lat/lon
    arch_sites = []
    for p in glob.glob(os.path.join(SITES_DIR, '*.json')):
        if os.path.basename(p).startswith('summary_'):
            continue
        try:
            d = json.load(open(p, encoding='utf-8'))
            items = d if isinstance(d, list) else d.get('sites', d.get('features', d.get('records', [])))
            if isinstance(d, dict) and not items:
                items = [v for v in d.values() if isinstance(v, dict)]
            src_name = os.path.basename(p)
            for it in items:
                if not isinstance(it, dict):
                    continue
                lat = it.get('lat') or it.get('latitude') or (it.get('coords', [None, None])[0] if isinstance(it.get('coords'), list) else None)
                lon = it.get('lon') or it.get('lng') or it.get('longitude') or (it.get('coords', [None, None])[1] if isinstance(it.get('coords'), list) else None)
                if lat is None or lon is None:
                    geom = it.get('geometry') or {}
                    coords = geom.get('coordinates')
                    if isinstance(coords, list) and len(coords) >= 2 and isinstance(coords[0], (int, float)):
                        lon, lat = coords[0], coords[1]
                    props = it.get('properties') or {}
                    if props:
                        it = {**props, '_lat': lat, '_lon': lon}
                if lat is not None and lon is not None:
                    try:
                        arch_sites.append((float(lat), float(lon), src_name, it))
                    except Exception:
                        pass
        except Exception:
            pass
    return hgis_list, raw_setts, arch_sites

def wiki_lookup(item):
    n = item['n']
    c = item['c']
    lat, lon = item['ll']
    res = {'es_geo': [], 'es_search': [], 'en_geo': [], 'en_search': [], 'wd_geo': []}
    # ES Wiki geo
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=8&format=json"
        data = fetch_json(u)
        res['es_geo'] = data.get('query', {}).get('geosearch', [])
    except Exception as e:
        res['es_geo_err'] = str(e)
    # ES Wiki search
    try:
        q = urllib.parse.quote(f'"{n}" {c}')
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=5&format=json"
        data = fetch_json(u)
        res['es_search'] = [{'title': x['title'], 'snippet': x['snippet']} for x in data.get('query', {}).get('search', [])]
    except Exception as e:
        res['es_search_err'] = str(e)
    # EN Wiki geo
    try:
        u = f"https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
        data = fetch_json(u)
        res['en_geo'] = data.get('query', {}).get('geosearch', [])
    except Exception:
        pass
    # EN Wiki search
    try:
        q = urllib.parse.quote(f'"{n}" {c}')
        u = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=4&format=json"
        data = fetch_json(u)
        res['en_search'] = [{'title': x['title'], 'snippet': x['snippet']} for x in data.get('query', {}).get('search', [])]
    except Exception:
        pass
    # Fetch top ES page extracts (closest geo match if < 6km or matching name, plus top search result)
    titles_to_fetch = []
    for g in res['es_geo'][:3]:
        if g.get('dist', 99999) < 6000 or n.lower() in g['title'].lower():
            titles_to_fetch.append(g['title'])
    for s in res['es_search'][:2]:
        if s['title'] not in titles_to_fetch:
            titles_to_fetch.append(s['title'])
    if titles_to_fetch:
        try:
            ts = urllib.parse.quote('|'.join(titles_to_fetch[:4]))
            u = f"https://es.wikipedia.org/w/api.php?action=query&titles={ts}&prop=extracts&explaintext=1&exchars=3500&format=json"
            data = fetch_json(u)
            pages = data.get('query', {}).get('pages', {})
            res['es_extracts'] = {p.get('title'): p.get('extract', '') for p in pages.values() if 'missing' not in p}
        except Exception:
            pass
    # Fetch top EN page extract if ES had nothing useful
    en_titles = []
    for g in res['en_geo'][:2]:
        if g.get('dist', 99999) < 6000 or n.lower() in g['title'].lower():
            en_titles.append(g['title'])
    for s in res['en_search'][:2]:
        if s['title'] not in en_titles:
            en_titles.append(s['title'])
    if en_titles:
        try:
            ts = urllib.parse.quote('|'.join(en_titles[:3]))
            u = f"https://en.wikipedia.org/w/api.php?action=query&titles={ts}&prop=extracts&explaintext=1&exchars=2500&format=json"
            data = fetch_json(u)
            pages = data.get('query', {}).get('pages', {})
            res['en_extracts'] = {p.get('title'): p.get('extract', '') for p in pages.values() if 'missing' not in p}
        except Exception:
            pass
    return res

def main():
    items = json.load(open(INPUT_PATH, encoding='utf-8'))
    hgis_list, raw_setts, arch_sites = load_local()
    print(f"Loaded {len(items)} items, {len(hgis_list)} HGIS, {len(raw_setts)} raw_setts, {len(arch_sites)} arch_sites")

    # Local matching
    local_hits = {}
    for it in items:
        key = it['key']
        lat, lon = it['ll']
        hits = {'raw_sett': None, 'hgis': [], 'arch': []}
        if key in raw_setts:
            rs = dict(raw_setts[key])
            rs.pop('population', None)
            rs.pop('urban_population', None)
            hits['raw_sett'] = rs
        for h in hgis_list:
            hc = h.get('coords')
            if hc and len(hc) == 2:
                d = haversine(lat, lon, hc[0], hc[1])
                if d <= 15.0 or (h.get('name','').lower() == it['n'].lower() and d <= 50.0):
                    hits['hgis'].append((round(d, 2), h))
        hits['hgis'].sort(key=lambda x: x[0])
        hits['hgis'] = hits['hgis'][:5]
        for alat, alon, src, aobj in arch_sites:
            d = haversine(lat, lon, alat, alon)
            if d <= 2.5:
                slim = {k: v for k, v in aobj.items() if k in ('name', 'sitio', 'site_name', 'nombre', 'cultura', 'culture', 'period', 'periodo', 'epoca', 'cronologia', 'description', 'descripcion', 'tipo', 'type', 'c14_ages', 'age_bp', 'cal_bp', 'earliest_year', 'latest_year', 'alt_names', 'denominacion')}
                hits['arch'].append((round(d, 3), src, slim if slim else str(aobj)[:200]))
        hits['arch'].sort(key=lambda x: x[0])
        hits['arch'] = hits['arch'][:6]
        local_hits[key] = hits

    wiki_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(wiki_lookup, it): it['key'] for it in items}
        for f in concurrent.futures.as_completed(futs):
            k = futs[f]
            wiki_results[k] = f.result()

    out = {'local': local_hits, 'wiki': wiki_results}
    with open('tests/_chunk032_research.json', 'w', encoding='utf-8') as fp:
        json.dump(out, fp, ensure_ascii=False, indent=2)
    print("Saved tests/_chunk032_research.json")

if __name__ == '__main__':
    main()
