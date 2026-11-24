import json
import time
import urllib.parse
import urllib.request

with open('tests/c053_input.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

HEADERS = {'User-Agent': 'SVEA-Viscount-Toponymy/1.0 (historical-gazetteer-research)'}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))

def wiki_geosearch(lang, lat, lon, radius=10000):
    params = urllib.parse.urlencode({
        'action': 'query',
        'list': 'geosearch',
        'gscoord': f'{lat}|{lon}',
        'gsradius': str(radius),
        'gslimit': '5',
        'format': 'json'
    })
    url = f'https://{lang}.wikipedia.org/w/api.php?{params}'
    try:
        data = fetch_json(url)
        return data.get('query', {}).get('geosearch', [])
    except Exception:
        return []

def wiki_search(lang, q):
    params = urllib.parse.urlencode({
        'action': 'query',
        'list': 'search',
        'srsearch': q,
        'srlimit': '5',
        'format': 'json'
    })
    url = f'https://{lang}.wikipedia.org/w/api.php?{params}'
    try:
        data = fetch_json(url)
        return [x['title'] for x in data.get('query', {}).get('search', [])]
    except Exception:
        return []

def wiki_extracts(lang, titles):
    if not titles:
        return {}
    out = {}
    for i in range(0, len(titles), 20):
        batch = titles[i:i+20]
        params = urllib.parse.urlencode({
            'action': 'query',
            'prop': 'extracts|coordinates|pageprops',
            'exintro': '0',
            'explaintext': '1',
            'exchars': '3500',
            'titles': '|'.join(batch),
            'redirects': '1',
            'format': 'json'
        })
        url = f'https://{lang}.wikipedia.org/w/api.php?{params}'
        try:
            data = fetch_json(url)
            pages = data.get('query', {}).get('pages', {})
            for pid, p in pages.items():
                if 'title' in p and 'extract' in p:
                    out[p['title']] = {
                        'extract': p['extract'][:3000],
                        'coords': p.get('coordinates'),
                        'wikibase': p.get('pageprops', {}).get('wikibase_item')
                    }
        except Exception as e:
            print('extract err:', e)
        time.sleep(0.2)
    return out

results = {}
es_titles_needed = set()
en_titles_needed = set()

for idx, it in enumerate(items):
    k = it['key']
    lat, lon = it['ll']
    geo_es = wiki_geosearch('es', lat, lon, 10000)
    geo_en = wiki_geosearch('en', lat, lon, 10000)
    q = f"{it['n']} {it['c']}"
    sr_es = wiki_search('es', q)
    sr_en = wiki_search('en', q)
    results[k] = {
        'geo_es': geo_es,
        'geo_en': geo_en,
        'sr_es': sr_es[:3],
        'sr_en': sr_en[:3],
    }
    for g in geo_es[:2]:
        es_titles_needed.add(g['title'])
    for t in sr_es[:2]:
        es_titles_needed.add(t)
    for g in geo_en[:2]:
        en_titles_needed.add(g['title'])
    for t in sr_en[:2]:
        en_titles_needed.add(t)
    if (idx + 1) % 15 == 0:
        print(f"Searched {idx+1}/{len(items)}")
    time.sleep(0.05)

es_extracts = wiki_extracts('es', list(es_titles_needed))
en_extracts = wiki_extracts('en', list(en_titles_needed))

out = {
    'items': results,
    'es_extracts': es_extracts,
    'en_extracts': en_extracts
}
with open('tests/c053_wiki_results.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"Done. ES extracts: {len(es_extracts)}, EN extracts: {len(en_extracts)}")
