import json, urllib.request, urllib.parse, time

with open('tests/chunk025_input.json', encoding='utf-8') as f:
    inp = json.load(f)

results = {}
for idx, item in enumerate(inp):
    lat, lon = item['ll']
    # Use Wikidata around query within 8 km
    q = f'''SELECT ?item ?itemLabel ?itemDescription ?inception ?eswiki ?enwiki ?dist WHERE {{
  SERVICE wikibase:around {{
    ?item wdt:P625 ?location .
    bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral .
    bd:serviceParam wikibase:radius "8" .
    bd:serviceParam wikibase:distance ?dist .
  }}
  OPTIONAL {{ ?item wdt:P571 ?inception . }}
  OPTIONAL {{ ?eswiki schema:about ?item ; schema:isPartOf <https://es.wikipedia.org/> . }}
  OPTIONAL {{ ?enwiki schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en" . }}
}} ORDER BY ?dist LIMIT 8'''
    url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': q, 'format': 'json'})
    req = urllib.request.Request(url, headers={'User-Agent': 'SVEA-Project1509-Research/1.0 (https://confoederatio.org)'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode('utf-8'))
        bindings = data.get('results', {}).get('bindings', [])
        cleaned = []
        for b in bindings:
            cleaned.append({
                'label': b.get('itemLabel', {}).get('value'),
                'desc': b.get('itemDescription', {}).get('value'),
                'inception': b.get('inception', {}).get('value'),
                'eswiki': b.get('eswiki', {}).get('value'),
                'enwiki': b.get('enwiki', {}).get('value'),
                'dist': b.get('dist', {}).get('value'),
                'qid': b.get('item', {}).get('value', '').split('/')[-1]
            })
        results[item['key']] = cleaned
    except Exception as e:
        results[item['key']] = [{'error': str(e)}]
    time.sleep(0.15)

with open('tests/chunk025_wikidata.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Done, queried", len(results))
