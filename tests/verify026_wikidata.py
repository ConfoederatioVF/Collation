import json, urllib.request, urllib.parse, time, re

with open("tests/chunk026_research.json", encoding="utf-8") as f:
    research = json.load(f)

UA = {"User-Agent": "OperationViscountToponymy/1.0 (https://confoederatio.org; mailto:research@confoederatio.org)"}

def api_get(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if "429" in str(e):
                time.sleep(2.0 * (attempt + 1))
            else:
                return {"_err": str(e)}
    return {"_err": "429_exhausted"}

# Step 1: check which items need Wikipedia geo/search (items 39..90 or items with missing extracts)
# Also query Wikidata SPARQL by coordinates (within 5km) in batches of 30!
wd_results = {}
for batch_start in range(0, len(research), 30):
    batch = research[batch_start:batch_start+30]
    values = " ".join(f'("{d["key"]}" "Point({d["ll"][1]} {d["ll"][0]})"^^geo:wktLiteral)' for d in batch)
    sparql = f"""
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX bd: <http://www.bigdata.com/rdf#>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <http://schema.org/>
SELECT ?key ?place ?placeLabel ?inception ?eswiki ?enwiki WHERE {{
  VALUES (?key ?loc) {{ {values} }}
  SERVICE wikibase:around {{
    ?place wdt:P625 ?coord .
    bd:serviceParam wikibase:center ?loc .
    bd:serviceParam wikibase:radius "3.0" .
  }}
  OPTIONAL {{ ?place wdt:P571 ?inception . }}
  OPTIONAL {{ ?eswiki schema:about ?place ; schema:isPartOf <https://es.wikipedia.org/> . }}
  OPTIONAL {{ ?enwiki schema:about ?place ; schema:isPartOf <https://en.wikipedia.org/> . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en" . }}
}}
"""
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": sparql, "format": "json"})
    res = api_get(url)
    for b in res.get("results", {}).get("bindings", []):
        k = b["key"]["value"]
        wd_results.setdefault(k, []).append({
            "label": b.get("placeLabel", {}).get("value", ""),
            "inception": b.get("inception", {}).get("value", ""),
            "eswiki": b.get("eswiki", {}).get("value", ""),
            "enwiki": b.get("enwiki", {}).get("value", ""),
        })
    time.sleep(0.5)

with open("tests/verify026_wikidata.json", "w", encoding="utf-8") as f:
    json.dump(wd_results, f, ensure_ascii=False, indent=2)
print("Wikidata keys matched:", len(wd_results))
