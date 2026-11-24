import json
import math
import time
import urllib.parse
import urllib.request

with open("tests/lookup_chunk040.py", "r", encoding="utf-8") as f:
    src = f.read()
ns = {}
exec(src.split("def api_get")[0], ns)
SETTLEMENTS = ns["SETTLEMENTS"]

def sparql_around(lat, lng, radius_km=12):
    query = f"""
    SELECT ?place ?placeLabel ?placeDescription ?inception ?dist ?sitelink WHERE {{
      SERVICE wikibase:around {{
        ?place wdt:P625 ?location .
        bd:serviceParam wikibase:center "Point({lng} {lat})"^^geo:wktLiteral .
        bd:serviceParam wikibase:radius "{radius_km}" .
        bd:serviceParam wikibase:distance ?dist .
      }}
      OPTIONAL {{ ?place wdt:P571 ?inception . }}
      OPTIONAL {{
        ?sitelink schema:about ?place ;
                  schema:isPartOf <https://es.wikipedia.org/> .
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en" . }}
    }}
    ORDER BY ?dist
    LIMIT 12
    """
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={
        "User-Agent": "SVEA-Toponymy/1.0 (https://confoederatio.org)",
        "Accept": "application/sparql-results+json"
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8"))
    out = []
    for b in data.get("results", {}).get("bindings", []):
        out.append({
            "qid": b["place"]["value"].split("/")[-1],
            "label": b.get("placeLabel", {}).get("value"),
            "desc": b.get("placeDescription", {}).get("value"),
            "inception": b.get("inception", {}).get("value"),
            "dist": b.get("dist", {}).get("value"),
            "eswiki": b.get("sitelink", {}).get("value")
        })
    return out

results = {}
for idx, s in enumerate(SETTLEMENTS):
    lat, lng = s["ll"]
    try:
        hits = sparql_around(lat, lng, 12)
        results[s["key"]] = hits
    except Exception as e:
        results[s["key"]] = [{"error": str(e)}]
    if idx % 10 == 0:
        print(f"{idx}/{len(SETTLEMENTS)}", flush=True)
    time.sleep(0.25)

with open("tests/chunk040_wikidata.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("Done Wikidata:", len(results))
