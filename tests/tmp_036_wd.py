import json
import urllib.request
import urllib.parse
import time

data = json.load(open("tests/tmp_036_data.json", encoding="utf-8"))
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
    body = urllib.parse.urlencode({"query": query, "format": "json"}).encode("utf-8")
    req = urllib.request.Request(
        "https://query.wikidata.org/sparql",
        data=body,
        headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

all_wd = {}
for i in range(0, len(data), 15):
    batch = data[i:i+15]
    try:
        res = sparql_batch(batch)
        for b in res["results"]["bindings"]:
            k = b["key"]["value"]
            all_wd.setdefault(k, []).append({
                "qid": b["place"]["value"].split("/")[-1],
                "label": b.get("placeLabel", {}).get("value"),
                "desc": b.get("placeDesc", {}).get("value"),
                "dist": round(float(b["dist"]["value"]), 2),
                "inception": b.get("inception", {}).get("value"),
                "esTitle": b.get("esTitle", {}).get("value"),
                "enTitle": b.get("enTitle", {}).get("value"),
            })
    except Exception as e:
        print(f"Batch {i//15 + 1}: err {e}")
    time.sleep(0.5)

for k, rows in all_wd.items():
    seen = {}
    for r in rows:
        q = r["qid"]
        if q not in seen:
            seen[q] = r
    all_wd[k] = sorted(seen.values(), key=lambda x: x["dist"])[:5]

with open("tests/tmp_036_wd.json", "w", encoding="utf-8") as f:
    json.dump(all_wd, f, ensure_ascii=False, indent=2)
print("Wikidata matched:", len(all_wd))
