import json
import time
import urllib.parse
import urllib.request

with open("tests/chunk015_wiki.json", encoding="utf-8") as f:
  data = json.load(f)

items = list(data.items())
results = {}
for i in range(0, len(items), 10):
  batch = items[i : i + 10]
  subq = []
  for k, v in batch:
    lat, lon = v["ll"]
    k_esc = k.replace('"', '\\"')
    subq.append(
      f"""{{
      BIND("{k_esc}" AS ?key)
      SERVICE wikibase:around {{
        ?item wdt:P625 ?loc .
        bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral .
        bd:serviceParam wikibase:radius "8" .
      }}
    }}"""
    )
  sparql = (
    """SELECT DISTINCT ?key ?item ?itemLabel ?itemDesc ?inception ?adminLabel ?eswiki ?enwiki WHERE {
    """
    + " UNION ".join(subq)
    + """
    OPTIONAL { ?item wdt:P571 ?inception . }
    OPTIONAL { ?item wdt:P131 ?admin . }
    OPTIONAL { ?eswiki schema:about ?item ; schema:isPartOf <https://es.wikipedia.org/> . }
    OPTIONAL { ?enwiki schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }
    SERVICE wikibase:label { bd:serviceParam wikibase:language "es,en". ?item rdfs:label ?itemLabel ; schema:description ?itemDesc . ?admin rdfs:label ?adminLabel . }
  }"""
  )
  url = "https://query.wikidata.org/sparql"
  req = urllib.request.Request(
    url,
    data=urllib.parse.urlencode({"query": sparql, "format": "json"}).encode(),
    headers={
      "User-Agent": "OperationViscount/1.0",
      "Accept": "application/sparql-results+json",
    },
  )
  try:
    with urllib.request.urlopen(req, timeout=45) as r:
      res = json.loads(r.read().decode())
      for b in res["results"]["bindings"]:
        k = b["key"]["value"]
        results.setdefault(k, []).append(
          {kk: vv["value"] for kk, vv in b.items() if kk != "key"}
        )
    print(f"Batch {i//10+1}: ok, total keys={len(results)}", flush=True)
  except Exception as e:
    print(f"Batch {i//10+1} ERR:", e, flush=True)
  time.sleep(1.0)

with open("tests/chunk015_wd_sparql.json", "w", encoding="utf-8") as f:
  json.dump(results, f, ensure_ascii=False, indent=2)
print("Saved tests/chunk015_wd_sparql.json")
