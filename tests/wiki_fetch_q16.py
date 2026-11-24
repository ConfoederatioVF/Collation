import json, time, urllib.request, urllib.parse

HEADERS = {'User-Agent': 'SVEA-Toponymy-Research/1.0 (https://confoederatio.org; mailto:research@confoederatio.org)'}

def api_get(url):
    time.sleep(0.35)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))

with open('tests/q16_wiki.json', encoding='utf-8') as f:
    results = json.load(f)

for i, res in enumerate(results):
    needs_geo = 'geo_err' in res
    needs_sr = 'sr_err' in res
    needs_ext = 'ext_err' in res or (not res.get('extracts') and (res.get('geo_es') or res.get('sr_es')))
    if not (needs_geo or needs_sr or needs_ext):
        continue
    lat, lon = res['ll']
    name = res['n']
    country = res['c']
    if needs_geo:
        res.pop('geo_err', None)
        try:
            u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
            d = api_get(u)
            res['geo_es'] = [x['title'] for x in d.get('query', {}).get('geosearch', [])]
        except Exception as e:
            res['geo_err'] = str(e)
    if needs_sr:
        res.pop('sr_err', None)
        try:
            q = urllib.parse.quote(f"{name} {country}")
            u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
            d = api_get(u)
            res['sr_es'] = [x['title'] for x in d.get('query', {}).get('search', [])]
        except Exception as e:
            res['sr_err'] = str(e)
    cand = []
    for t in res.get('geo_es', []) + res.get('sr_es', []):
        if t not in cand:
            cand.append(t)
    cand = cand[:3]
    if cand and (needs_ext or not res.get('extracts')):
        res.pop('ext_err', None)
        try:
            t_param = urllib.parse.quote('|'.join(cand))
            u = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={t_param}&format=json"
            d = api_get(u)
            for pid, p in d.get('query', {}).get('pages', {}).items():
                if 'extract' in p:
                    res['extracts'][p['title']] = p['extract'][:1200]
        except Exception as e:
            res['ext_err'] = str(e)
    if (i + 1) % 10 == 0:
        with open('tests/q16_wiki.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

with open('tests/q16_wiki.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("Done retry, errors left:", sum(1 for r in results if 'geo_err' in r or 'sr_err' in r or 'ext_err' in r))
