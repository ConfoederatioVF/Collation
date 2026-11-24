import json, urllib.request, urllib.parse, concurrent.futures, math

with open('tests/tmp_chunk035_input.json', encoding='utf-8') as f:
    items = json.load(f)

HEADERS = {'User-Agent': 'HistoricalToponymyResearch/1.0 (academic)'}

def api_get(lang, params):
    qs = urllib.parse.urlencode(params)
    url = f'https://{lang}.wikipedia.org/w/api.php?{qs}'
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode('utf-8'))

def lookup_item(it):
    key = it['key']
    la, lo = it['ll']
    name = it['n']
    res = {'key': key, 'n': name, 'c': it['c'], 'r': it['r'], 'll': it['ll'], 'ey': it['ey'], 'ly': it['ly'], 'al': it.get('al', [])}
    
    # 1. es.wikipedia geosearch
    try:
        gs = api_get('es', {
            'action': 'query', 'list': 'geosearch',
            'gscoord': f'{la}|{lo}', 'gsradius': 10000, 'gslimit': 8, 'format': 'json'
        })
        res['es_geo'] = [{'title': g['title'], 'dist': g['dist'], 'pageid': g['pageid']} for g in gs.get('query', {}).get('geosearch', [])]
    except Exception as e:
        res['es_geo_err'] = str(e)

    # 2. es.wikipedia title search (name + country)
    try:
        sr = api_get('es', {
            'action': 'query', 'list': 'search',
            'srsearch': f'"{name}" {it["c"]}', 'srlimit': 5, 'format': 'json'
        })
        res['es_search'] = [{'title': s['title'], 'pageid': s['pageid'], 'snippet': s.get('snippet', '')} for s in sr.get('query', {}).get('search', [])]
    except Exception as e:
        res['es_search_err'] = str(e)

    # 3. en.wikipedia geosearch if es_geo empty or for arch sites
    if not res.get('es_geo'):
        try:
            gs = api_get('en', {
                'action': 'query', 'list': 'geosearch',
                'gscoord': f'{la}|{lo}', 'gsradius': 10000, 'gslimit': 5, 'format': 'json'
            })
            res['en_geo'] = [{'title': g['title'], 'dist': g['dist'], 'pageid': g['pageid']} for g in gs.get('query', {}).get('geosearch', [])]
        except Exception as e:
            pass

    return res

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    for r in ex.map(lookup_item, items):
        results.append(r)

with open('tests/tmp_chunk035_wiki_hits.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

geo_hits = sum(1 for r in results if r.get('es_geo') or r.get('en_geo'))
sr_hits = sum(1 for r in results if r.get('es_search'))
print(f'Geo hits: {geo_hits}/90, Search hits: {sr_hits}/90')
