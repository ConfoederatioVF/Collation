import json, urllib.request, urllib.parse

with open('tests/lookup_chunk37.py', encoding='utf-8') as f:
    src = f.read()
ns = {}
exec(src.split('def wiki_lookup')[0], ns)
inp = ns['INPUT']

vals = []
for x in inp:
    lat, lon = x['ll']
    k = x['key'].replace('"', '')
    vals.append(f'("{k}" "Point({lon} {lat})"^^geo:wktLiteral)')

all_rows = {}
for idx in range(0, len(vals), 30):
    chunk = vals[idx:idx+30]
    q = f'''
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX schema: <http://schema.org/>
SELECT ?key ?place ?placeLabel ?placeDescription ?inception ?eswiki WHERE {{
  VALUES (?key ?loc) {{ {' '.join(chunk)} }}
  SERVICE wikibase:around {{
    ?place wdt:P625 ?coords .
    bd:serviceParam wikibase:center ?loc .
    bd:serviceParam wikibase:radius "8" .
  }}
  OPTIONAL {{ ?place wdt:P571 ?inception . }}
  OPTIONAL {{ ?eswiki schema:about ?place ; schema:isPartOf <https://es.wikipedia.org/> . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en". }}
}}
'''
    data = urllib.parse.urlencode({'query': q, 'format': 'json'}).encode()
    req = urllib.request.Request('https://query.wikidata.org/sparql', data=data, headers={'User-Agent': 'ViscountResearch/1.0 (https://confoederatio.org)', 'Accept': 'application/sparql-results+json'})
    res = json.loads(urllib.request.urlopen(req, timeout=45).read())
    for b in res['results']['bindings']:
        k = b['key']['value']
        all_rows.setdefault(k, []).append({
            'place': b['place']['value'].split('/')[-1],
            'label': b.get('placeLabel', {}).get('value'),
            'desc': b.get('placeDescription', {}).get('value'),
            'inception': b.get('inception', {}).get('value'),
            'eswiki': b.get('eswiki', {}).get('value')
        })
    print(f'Chunk {idx}: ok')

with open('tests/wd_results37.json', 'w', encoding='utf-8') as f:
    json.dump(all_rows, f, ensure_ascii=False, indent=2)
print('Keys found in WD:', len(all_rows))
