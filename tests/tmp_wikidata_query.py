import json, urllib.request, urllib.parse, time

items = json.load(open('tests/tmp_043_matches.json', encoding='utf-8'))
res = {}
for i, it in enumerate(items):
    lat, lng = it['ll']
    q = f'''SELECT ?place ?placeLabel ?placeDescription ?inception ?adminLabel ?eswiki ?enwiki WHERE {{
  SERVICE wikibase:around {{
    ?place wdt:P625 ?loc .
    bd:serviceParam wikibase:center "Point({lng} {lat})"^^geo:wktLiteral .
    bd:serviceParam wikibase:radius "3.5" .
  }}
  OPTIONAL {{ ?place wdt:P571 ?inception . }}
  OPTIONAL {{ ?place wdt:P131 ?admin . }}
  OPTIONAL {{ ?eswiki schema:about ?place ; schema:isPartOf <https://es.wikipedia.org/> . }}
  OPTIONAL {{ ?enwiki schema:about ?place ; schema:isPartOf <https://en.wikipedia.org/> . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en" . }}
}} LIMIT 8'''
    url = 'https://query.wikidata.org/sparql?format=json&query=' + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={'User-Agent': 'SVEA-ToponymyResearch/1.0'})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode('utf-8'))
        rows = []
        for b in data['results']['bindings']:
            rows.append({k: v['value'] for k, v in b.items()})
        res[it['key']] = rows
    except Exception as e:
        res[it['key']] = [{'error': str(e)}]
    time.sleep(0.15)
open('tests/tmp_043_wikidata.json', 'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=2))
print('Done Wikidata:', len(res))
