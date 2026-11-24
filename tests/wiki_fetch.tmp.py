import json, time, urllib.request, urllib.parse, sys

HEADERS = {'User-Agent': 'SVEA-Historical-Research/1.0 (https://confoederatio.org; research@confoederatio.org)'}

def api(lang, params):
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))

def wd_search(q):
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
        'action': 'wbsearchentities', 'search': q, 'language': 'es', 'format': 'json', 'limit': 3
    })
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8')).get('search', [])

def get_info(key, name, country, lat, lng):
    out = {'key': key, 'geo': [], 'search': []}
    try:
        g = api('es', {'action': 'query', 'list': 'geosearch', 'gscoord': f"{lat}|{lng}", 'gsradius': 10000, 'gslimit': 5, 'format': 'json'})
        titles = [x['title'] for x in g.get('query', {}).get('geosearch', [])]
        if titles:
            ext = api('es', {'action': 'query', 'prop': 'extracts', 'exintro': 1, 'explaintext': 1, 'titles': '|'.join(titles[:3]), 'format': 'json'})
            for p in ext.get('query', {}).get('pages', {}).values():
                if 'extract' in p:
                    out['geo'].append({'title': p['title'], 'extract': p['extract'][:600]})
        s = api('es', {'action': 'query', 'list': 'search', 'srsearch': f'"{name}" {country}', 'srlimit': 3, 'format': 'json'})
        st = [x['title'] for x in s.get('query', {}).get('search', [])]
        if st:
            ext = api('es', {'action': 'query', 'prop': 'extracts', 'exintro': 1, 'explaintext': 1, 'titles': '|'.join(st[:2]), 'format': 'json'})
            for p in ext.get('query', {}).get('pages', {}).values():
                if 'extract' in p and p['title'] not in titles:
                    out['search'].append({'title': p['title'], 'extract': p['extract'][:600]})
    except Exception as e:
        out['error'] = str(e)
    return out

items = json.loads(sys.argv[1])
start = int(sys.argv[2])
end = int(sys.argv[3])
for it in items[start:end]:
    res = get_info(it['key'], it['n'], it['c'], it['ll'][0], it['ll'][1])
    print("===", res['key'], "===")
    for g in res['geo']:
        print("  [GEO]", g['title'], "||", g['extract'].replace('\n', ' '))
    for s in res['search']:
        print("  [SRC]", s['title'], "||", s['extract'].replace('\n', ' '))
    if 'error' in res:
        print("  [ERR]", res['error'])
    time.sleep(0.12)
