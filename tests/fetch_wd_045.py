import json
import urllib.parse
import urllib.request
import time

with open(r'f:\Active Projects\Project 1509 - SVEA\tests\settlements_045.json', encoding='utf-8') as f:
    SETTLEMENTS = json.load(f)

HEADERS = {'User-Agent': 'OperationViscountBot/1.0 (https://confoederatio.org; mailto:research@confoederatio.org)'}

def sparql_query(q):
    url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': q, 'format': 'json'})
    req = urllib.request.Request(url, headers={**HEADERS, 'Accept': 'application/sparql-results+json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))

# Query Wikidata around coordinates for settlements (batch of 30 at a time)
all_wd = {}
for i in range(0, len(SETTLEMENTS), 15):
    batch = SETTLEMENTS[i:i+15]
    values = " ".join([f'("{s["key"].replace(chr(34), "")}" "Point({s["ll"][1]} {s["ll"][0]})"^^geo:wktLiteral)' for s in batch])
    q = f"""
    SELECT ?key ?place ?placeLabel ?placeDescription ?inception ?dissolved ?articleEs ?articleEn WHERE {{
      VALUES (?key ?center) {{ {values} }}
      SERVICE wikibase:around {{
        ?place wdt:P625 ?location .
        bd:serviceParam wikibase:center ?center .
        bd:serviceParam wikibase:radius "8" .
      }}
      OPTIONAL {{ ?place wdt:P571 ?inception . }}
      OPTIONAL {{ ?place wdt:P576 ?dissolved . }}
      OPTIONAL {{ ?articleEs schema:about ?place ; schema:isPartOf <https://es.wikipedia.org/> . }}
      OPTIONAL {{ ?articleEn schema:about ?place ; schema:isPartOf <https://en.wikipedia.org/> . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en" . }}
    }}
    """
    try:
        res = sparql_query(q)
        for row in res['results']['bindings']:
            k = row['key']['value']
            all_wd.setdefault(k, []).append({
                'label': row.get('placeLabel', {}).get('value'),
                'desc': row.get('placeDescription', {}).get('value'),
                'inception': row.get('inception', {}).get('value'),
                'es': row.get('articleEs', {}).get('value'),
                'en': row.get('articleEn', {}).get('value'),
            })
        print(f"Batch {i} ok, got {len(res['results']['bindings'])} rows", flush=True)
    except Exception as e:
        print(f"Batch {i} err: {e}", flush=True)
    time.sleep(1.5)

with open(r'f:\Active Projects\Project 1509 - SVEA\tests\chunk045_wd.json', 'w', encoding='utf-8') as f:
    json.dump(all_wd, f, ensure_ascii=False, indent=2)
print("Done WD")
