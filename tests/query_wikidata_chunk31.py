import json, urllib.request, urllib.parse, time

with open("tests/chunk31_input.json", "r", encoding="utf-8") as f:
  items = json.load(f)

# Query Wikidata by coordinate proximity for all 90 items in batches of 15
results = {}
batch_size = 15
for i in range(0, len(items), batch_size):
  batch = items[i:i+batch_size]
  values_rows = []
  for idx, it in enumerate(batch):
    lat, lng = it["ll"]
    # Wikidata Point(lng lat)
    values_rows.append(f'("{it["key"]}" "Point({lng} {lat})"^^geo:wktLiteral)')
  values_str = "\n    ".join(values_rows)
  q = f"""
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX bd: <http://www.bigdata.com/rdf#>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX schema: <http://schema.org/>
SELECT ?key ?place ?placeLabel ?dist ?inception ?eswiki ?enwiki WHERE {{
  VALUES (?key ?pt) {{
    {values_str}
  }}
  SERVICE wikibase:around {{
    ?place wdt:P625 ?location .
    bd:serviceParam wikibase:center ?pt .
    bd:serviceParam wikibase:radius "5" .
    bd:serviceParam wikibase:distance ?dist .
  }}
  OPTIONAL {{ ?place wdt:P571 ?inception . }}
  OPTIONAL {{ ?eswiki schema:about ?place ; schema:isPartOf <https://es.wikipedia.org/> . }}
  OPTIONAL {{ ?enwiki schema:about ?place ; schema:isPartOf <https://en.wikipedia.org/> . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en". }}
}}
ORDER BY ?key ?dist
"""
  url = "https://query.wikidata.org/sparql"
  data = urllib.parse.urlencode({"format": "json", "query": q}).encode("utf-8")
  req = urllib.request.Request(url, data=data, headers={"User-Agent": "ProjectSVEA/1.0 (https://confoederatio.org)"})
  try:
    with urllib.request.urlopen(req, timeout=30) as r:
      res = json.loads(r.read().decode("utf-8"))
    for b in res["results"]["bindings"]:
      k = b["key"]["value"]
      results.setdefault(k, []).append({
        "place": b["place"]["value"].split("/")[-1],
        "label": b.get("placeLabel", {}).get("value"),
        "dist_km": b.get("dist", {}).get("value"),
        "inception": b.get("inception", {}).get("value"),
        "eswiki": b.get("eswiki", {}).get("value"),
        "enwiki": b.get("enwiki", {}).get("value"),
      })
    print(f"Batch {i//batch_size + 1} OK, keys matched so far: {len(results)}")
  except Exception as e:
    print(f"Batch {i//batch_size + 1} error: {e}")
  time.sleep(1)

with open("tests/chunk31_wikidata.json", "w", encoding="utf-8") as f:
  json.dump(results, f, ensure_ascii=False, indent=2)
print("Done! Total keys with Wikidata hits:", len(results))
