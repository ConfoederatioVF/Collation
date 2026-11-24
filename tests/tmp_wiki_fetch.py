import json, urllib.request, urllib.parse, concurrent.futures, time

items = json.load(open('tests/tmp_input_029.json', encoding='utf-8'))

def wiki_geosearch_and_search(it):
    lat, lng = it['ll']
    name = it['n']
    country = it['c']
    res = {'key': it['key'], 'n': name, 'c': country, 'll': [lat, lng]}
    headers = {'User-Agent': 'SVEA-Toponymy/1.0 (historical research)'}
    
    # 1. Spanish Wikipedia geosearch within 10km
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
        data = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=headers), timeout=12).read().decode())
        geo = data.get('query', {}).get('geosearch', [])
        res['es_geo'] = [{'title': g['title'], 'dist_m': g['dist']} for g in geo]
    except Exception as e:
        res['es_geo_err'] = str(e)

    # 2. Spanish Wikipedia text search (name + country)
    try:
        q = f"{name} {country}"
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&srlimit=3&format=json"
        data = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=headers), timeout=12).read().decode())
        res['es_search'] = [s['title'] for s in data.get('query', {}).get('search', [])]
    except Exception as e:
        res['es_search_err'] = str(e)

    # 3. Fetch intro extract of top geo or search hit if relevant
    titles = []
    if res.get('es_geo'):
        titles.append(res['es_geo'][0]['title'])
    if res.get('es_search') and res['es_search'][0] not in titles:
        titles.append(res['es_search'][0])
    
    res['extracts'] = {}
    for t in titles[:2]:
        try:
            u = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={urllib.parse.quote(t)}&format=json"
            data = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=headers), timeout=12).read().decode())
            pages = data.get('query', {}).get('pages', {})
            for p in pages.values():
                res['extracts'][t] = (p.get('extract') or '')[:800]
        except:
            pass
    return res

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    results = list(ex.map(wiki_geosearch_and_search, items))

json.dump(results, open('tests/tmp_wiki_029.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Fetched Wikipedia info for', len(results), 'settlements')
