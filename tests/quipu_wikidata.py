import json
import urllib.request
import urllib.parse
import time

with open("tests/quipu_lookup.py", "r", encoding="utf-8") as f:
    src = f.read()

# Extract INPUT from quipu_lookup.py
ns = {}
exec(src.split("HEADERS =")[0], ns)
INPUT = ns["INPUT"]

UA = "ViscountHistoricalResearch/1.0 (mailto:research@confoederatio.org)"

def sparql_batch(items):
    values = "\n".join(
        f'("{i["key"]}" "Point({i["ll"][1]} {i["ll"][0]})"^^geo:wktLiteral)'
        for i in items
    )
    query = f"""
SELECT ?key ?place ?placeLabel ?placeDesc ?dist ?inception ?esTitle ?enTitle WHERE {{
  VALUES (?key ?center) {{
    {values}
  }}
  SERVICE wikibase:around {{
    ?place wdt:P625 ?loc .
    bd:serviceParam wikibase:center ?center .
    bd:serviceParam wikibase:radius "8" .
    bd:serviceParam wikibase:distance ?dist .
  }}
  OPTIONAL {{ ?place wdt:P571 ?inception . }}
  OPTIONAL {{
    ?esArticle schema:about ?place ;
               schema:isPartOf <https://es.wikipedia.org/> ;
               schema:name ?esTitle .
  }}
  OPTIONAL {{
    ?enArticle schema:about ?place ;
               schema:isPartOf <https://en.wikipedia.org/> ;
               schema:name ?enTitle .
  }}
  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "es,en" .
    ?place rdfs:label ?placeLabel .
    ?place schema:description ?placeDesc .
  }}
}}
"""
    data = urllib.parse.urlencode({"query": query, "format": "json"}).encode("utf-8")
    req = urllib.request.Request(
        "https://query.wikidata.org/sparql",
        data=data,
        headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

all_wd = {}
for i in range(0, len(INPUT), 15):
    batch = INPUT[i:i+15]
    try:
        res = sparql_batch(batch)
        for b in res["results"]["bindings"]:
            k = b["key"]["value"]
            all_wd.setdefault(k, []).append({
                "qid": b["place"]["value"].split("/")[-1],
                "label": b.get("placeLabel", {}).get("value"),
                "desc": b.get("placeDesc", {}).get("value"),
                "dist": float(b["dist"]["value"]),
                "inception": b.get("inception", {}).get("value"),
                "esTitle": b.get("esTitle", {}).get("value"),
                "enTitle": b.get("enTitle", {}).get("value"),
            })
        print(f"Batch {i//15 + 1}: ok ({len(res['results']['bindings'])} rows)")
    except Exception as e:
        print(f"Batch {i//15 + 1}: err {e}")
    time.sleep(1.0)

# Sort matches per key by name similarity then distance
for k, rows in all_wd.items():
    # deduplicate by qid
    seen = {}
    for r in rows:
        q = r["qid"]
        if q not in seen:
            seen[q] = r
    all_wd[k] = sorted(seen.values(), key=lambda x: x["dist"])[:8]

with open("tests/quipu_wikidata.json", "w", encoding="utf-8") as f:
    json.dump(all_wd, f, ensure_ascii=False, indent=2)

print("Keys matched:", len(all_wd))
