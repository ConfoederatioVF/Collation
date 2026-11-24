import json, urllib.request, urllib.parse, concurrent.futures, re

with open('tests/chunk041_input.json', encoding='utf-8') as f:
    items = json.load(f)

HEADERS = {'User-Agent': 'SVEA-Toponymy-Research/1.0 (contact: research@example.org)'}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode('utf-8'))

def clean_name(n):
    return re.sub(r'\s*\([^)]*\)', '', n).strip()

def query_wiki_for_item(it):
    lat, lon = it['ll']
    name = clean_name(it['n'])
    country = it['c']
    out = {'key': it['key'], 'es_geo': [], 'en_geo': [], 'es_search': [], 'extracts': {}}
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=10&format=json"
        out['es_geo'] = fetch_json(u).get('query', {}).get('geosearch', [])
    except Exception as e:
        out['es_geo_err'] = str(e)
    try:
        u = f"https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
        out['en_geo'] = fetch_json(u).get('query', {}).get('geosearch', [])
    except Exception as e:
        pass
    try:
        q = urllib.parse.quote(f"{name} {country}")
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=5&format=json"
        out['es_search'] = fetch_json(u).get('query', {}).get('search', [])
    except Exception as e:
        pass

    # Pick candidate titles to fetch extracts
    es_titles = []
    name_low = name.lower()
    for g in out['es_geo']:
        if g['dist'] < 4000 or name_low in g['title'].lower() or any(w in g['title'].lower() for w in name_low.split() if len(w) > 3):
            es_titles.append(g['title'])
    for s in out['es_search'][:2]:
        if s['title'] not in es_titles and (name_low in s['title'].lower() or s['title'].lower() in name_low):
            es_titles.append(s['title'])
    if not es_titles and out['es_geo']:
        es_titles.append(out['es_geo'][0]['title'])

    if es_titles:
        try:
            titles_param = urllib.parse.quote('|'.join(es_titles[:4]))
            u = f"https://es.wikipedia.org/w/api.php?action=query&titles={titles_param}&prop=extracts|coordinates&explaintext=1&exchars=3500&format=json"
            pages = fetch_json(u).get('query', {}).get('pages', {})
            for pid, p in pages.items():
                if int(pid) > 0:
                    out['extracts'][f"es:{p['title']}"] = {
                        'coords': p.get('coordinates'),
                        'extract': p.get('extract', '')[:3000]
                    }
        except Exception as e:
            pass

    en_titles = [g['title'] for g in out['en_geo'][:2]]
    if en_titles:
        try:
            titles_param = urllib.parse.quote('|'.join(en_titles))
            u = f"https://en.wikipedia.org/w/api.php?action=query&titles={titles_param}&prop=extracts|coordinates&explaintext=1&exchars=2500&format=json"
            pages = fetch_json(u).get('query', {}).get('pages', {})
            for pid, p in pages.items():
                if int(pid) > 0:
                    out['extracts'][f"en:{p['title']}"] = {
                        'coords': p.get('coordinates'),
                        'extract': p.get('extract', '')[:2000]
                    }
        except Exception:
            pass
    return out

results = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    for res in ex.map(query_wiki_for_item, items):
        results[res['key']] = res

with open('tests/chunk041_wiki.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Done wiki lookup for", len(results), "items")
