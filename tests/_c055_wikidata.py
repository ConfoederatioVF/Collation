import json, time, urllib.request, urllib.parse

with open("tests/_c055_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

HEADERS = {"User-Agent": "SVEA-Viscount-Chunk055/1.0 (https://confoederatio.org; research@confoederatio.org)"}

def fetch_json(url, data=None, retries=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 504):
                wait = 2.0 * (2 ** attempt)
                time.sleep(wait)
                continue
            return {"_err": f"HTTP {e.code}"}
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.5)
                continue
            return {"_err": str(e)}
    return {"_err": "max_retries"}

# Step 1: Query Wikidata SPARQL in chunks of 15 points using wikibase:around (radius 8 km)
wd_hits = {}
for start in range(0, len(items), 15):
    batch = items[start:start+15]
    values_rows = []
    for idx, it in enumerate(batch):
        lat, lng = it["ll"]
        values_rows.append(f'("{it["key"]}" "Point({lng} {lat})"^^geo:wktLiteral)')
    sparql = f"""
SELECT ?k ?place ?placeLabel ?placeDescription ?inception ?dissolved ?eswiki ?enwiki ?dist WHERE {{
  VALUES (?k ?loc) {{ {' '.join(values_rows)} }}
  SERVICE wikibase:around {{
    ?place wdt:P625 ?coord .
    bd:serviceParam wikibase:center ?loc .
    bd:serviceParam wikibase:radius "8" .
    bd:serviceParam wikibase:distance ?dist .
  }}
  OPTIONAL {{ ?place wdt:P571 ?inception . }}
  OPTIONAL {{ ?place wdt:P576 ?dissolved . }}
  OPTIONAL {{ ?eswiki schema:about ?place ; schema:isPartOf <https://es.wikipedia.org/> . }}
  OPTIONAL {{ ?enwiki schema:about ?place ; schema:isPartOf <https://en.wikipedia.org/> . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en" . }}
}}
ORDER BY ?k ?dist
"""
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(sparql)
    res = fetch_json(url)
    for b in res.get("results", {}).get("bindings", []):
        k = b["k"]["value"]
        wd_hits.setdefault(k, []).append({
            "qid": b["place"]["value"].split("/")[-1],
            "label": b.get("placeLabel", {}).get("value"),
            "desc": b.get("placeDescription", {}).get("value"),
            "inception": b.get("inception", {}).get("value"),
            "dissolved": b.get("dissolved", {}).get("value"),
            "eswiki": b.get("eswiki", {}).get("value"),
            "enwiki": b.get("enwiki", {}).get("value"),
            "dist": b.get("dist", {}).get("value"),
        })
    time.sleep(0.8)

with open("tests/_c055_wikidata.json", "w", encoding="utf-8") as f:
    json.dump(wd_hits, f, ensure_ascii=False, indent=2)
print("Wikidata keys with hits:", len(wd_hits))
