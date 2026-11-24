import json, glob, urllib.request, urllib.parse, time

INPUT = json.load(open("tests/tmp_chunk054_input.json", encoding="utf-8"))
UA = "ViscountHistoricalResearch/1.0 (mailto:research@confoederatio.org)"

# 1. Local QUIPU records lookup
files = sorted(glob.glob("histmap/1.data_raw/population_regional/QUIPU/**/*_settlements.json", recursive=True))
all_recs = []
for fn in files:
    d = json.load(open(fn, encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("settlements", d.get("cities", []))
    if isinstance(d, dict) and not items:
        items = list(d.values())
    for it in items:
        if isinstance(it, dict):
            all_recs.append((fn.replace("\\", "/").split("/")[-1], it))

local_meta = {}
for item in INPUT:
    lat, lng = item["ll"]
    matches = []
    for fn, it in all_recs:
        c = it.get("coords") or it.get("ll")
        if not c or len(c) < 2:
            continue
        if abs(c[0] - lat) < 0.005 and abs(c[1] - lng) < 0.005:
            rec_copy = {k: v for k, v in it.items() if k != "population"}
            rec_copy["_file"] = fn
            matches.append(rec_copy)
    local_meta[item["key"]] = matches

with open("tests/tmp_chunk054_local.json", "w", encoding="utf-8") as f:
    json.dump(local_meta, f, ensure_ascii=False, indent=2)
print("Local matched keys:", sum(1 for v in local_meta.values() if v), "/", len(INPUT))

# 2. Wikidata SPARQL lookup
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
        print(f"WD Batch {i//15 + 1}: ok ({len(res['results']['bindings'])} rows)")
    except Exception as e:
        print(f"WD Batch {i//15 + 1}: err {e}")
    time.sleep(1.0)

for k, rows in all_wd.items():
    seen = {}
    for r in rows:
        q = r["qid"]
        if q not in seen:
            seen[q] = r
    all_wd[k] = sorted(seen.values(), key=lambda x: x["dist"])[:8]

with open("tests/tmp_chunk054_wd.json", "w", encoding="utf-8") as f:
    json.dump(all_wd, f, ensure_ascii=False, indent=2)
print("WD matched keys:", len(all_wd))
