import json, time, urllib.request, urllib.parse
from query_chunk040 import INPUT

def wiki_get(lang, params):
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': 'SVEA-Toponymy-Verifier/1.0 (https://confoederatio.org; research@confoederatio.org)'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))

results = {}
titles_to_fetch = set()

for idx, item in enumerate(INPUT):
    key = item['key']
    lat, lng = item['ll']
    name = item['n']
    entry = {'key': key, 'n': name, 'c': item['c'], 'r': item['r'], 'll': item['ll'], 'ey': item['ey'], 'ly': item['ly'], 'geo': [], 'search': []}
    try:
        g = wiki_get('es', {'action': 'query', 'list': 'geosearch', 'gscoord': f'{lat}|{lng}', 'gsradius': 10000, 'gslimit': 5, 'format': 'json'})
        entry['geo'] = [x['title'] for x in g.get('query', {}).get('geosearch', [])]
        for t in entry['geo']:
            titles_to_fetch.add(t)
    except Exception as e:
        entry['geo_err'] = str(e)
    time.sleep(0.12)
    try:
        q = f'"{name}" {item["c"]}'
        s = wiki_get('es', {'action': 'query', 'list': 'search', 'srsearch': q, 'srlimit': 2, 'format': 'json'})
        entry['search'] = [x['title'] for x in s.get('query', {}).get('search', [])]
        if not entry['search']:
            s2 = wiki_get('es', {'action': 'query', 'list': 'search', 'srsearch': f'{name} {item["c"]}', 'srlimit': 2, 'format': 'json'})
            entry['search'] = [x['title'] for x in s2.get('query', {}).get('search', [])]
        for t in entry['search']:
            titles_to_fetch.add(t)
    except Exception as e:
        entry['search_err'] = str(e)
    time.sleep(0.12)
    results[key] = entry

# Fetch extracts in batches of 20
title_list = sorted(titles_to_fetch)
extracts = {}
for i in range(0, len(title_list), 20):
    batch = title_list[i:i+20]
    try:
        ex = wiki_get('es', {'action': 'query', 'prop': 'extracts', 'exintro': 1, 'explaintext': 1, 'titles': '|'.join(batch), 'format': 'json'})
        for p in ex.get('query', {}).get('pages', {}).values():
            if 'title' in p and 'extract' in p:
                extracts[p['title']] = p['extract'][:1200]
    except Exception as e:
        print("Extract batch err:", e)
    time.sleep(0.2)

with open('tests/chunk040_wiki_polite.json', 'w', encoding='utf-8') as f:
    json.dump({'items': results, 'extracts': extracts}, f, ensure_ascii=False, indent=2)
print("Done! Fetched", len(extracts), "extracts for", len(results), "items")
