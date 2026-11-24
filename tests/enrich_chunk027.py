import json
import urllib.request
import urllib.parse
import time

with open("tests/query_chunk027.py", "r", encoding="utf-8") as f:
    src = f.read()
ns = {}
exec(src.split("def api_get")[0], ns)
SETTLEMENTS = ns["SETTLEMENTS"]

with open("tests/chunk027_wikidata.json", "r", encoding="utf-8") as f:
    wd = json.load(f)

UA = "SVEA-Viscount-Research/1.0 (mailto:admin@confoederatio.org)"

# 1. Reverse geocode with Photon (fast, OSM-based)
rev = {}
for i, s in enumerate(SETTLEMENTS):
    lat, lng = s["ll"]
    url = f"https://photon.komoot.io/reverse?lat={lat}&lon={lng}&lang=en"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        feats = data.get("features", [])
        if feats:
            props = feats[0].get("properties", {})
            rev[s["key"]] = {k: props.get(k) for k in ["name", "city", "town", "village", "county", "state", "country", "district", "locality"] if props.get(k)}
        else:
            rev[s["key"]] = {}
    except Exception as e:
        rev[s["key"]] = {"err": str(e)}
    time.sleep(0.1)

with open("tests/chunk027_photon.json", "w", encoding="utf-8") as f:
    json.dump(rev, f, ensure_ascii=False, indent=2)
print("Photon reverse geocode done:", len(rev))

# 2. Query Wikidata by name for settlements whose 8km wikibase:around didn't give an obvious eswiki/enwiki article
missing_titles = []
for s in SETTLEMENTS:
    k = s["key"]
    hits = wd.get(k, [])
    has_wiki = any(h.get("es") or h.get("en") for h in hits if h.get("dist", 99) < 3.0)
    if not has_wiki:
        missing_titles.append(s)

print("Need name-based Wikidata lookup for:", len(missing_titles))

COUNTRY_QID = {
    "Colombia": "wd:Q739",
    "Ecuador": "wd:Q736",
    "Peru": "wd:Q419",
    "Argentina": "wd:Q414",
    "Bolivia": "wd:Q750",
    "Chile": "wd:Q298",
    "Venezuela": "wd:Q717",
}

def sparql_query(q):
    url = "https://query.wikidata.org/sparql"
    data = urllib.parse.urlencode({"query": q, "format": "json"}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))

name_hits = {}
for idx in range(0, len(missing_titles), 10):
    batch = missing_titles[idx:idx+10]
    rows = []
    for s in batch:
        k = s["key"].replace('"', '\\"')
        n = s["n"].replace('"', '\\"')
        cq = COUNTRY_QID[s["c"]]
        rows.append(f'("{k}" "{n}"@es {cq})')
        # Also try Distrito de X for Peru, or Municipio de X
        if s["c"] == "Peru":
            rows.append(f'("{k}" "Distrito de {n}"@es {cq})')
        elif s["c"] == "Bolivia":
            rows.append(f'("{k}" "Municipio de {n}"@es {cq})')
        elif s["c"] == "Ecuador":
            rows.append(f'("{k}" "Parroquia {n}"@es {cq})')
    vals = "\n    ".join(rows)
    q = f"""
SELECT ?key ?item ?esTitle ?enTitle ?inception ?coord WHERE {{
  VALUES (?key ?lbl ?country) {{
    {vals}
  }}
  ?item rdfs:label ?lbl ;
        wdt:P17 ?country .
  OPTIONAL {{ ?item wdt:P571 ?inception . }}
  OPTIONAL {{ ?item wdt:P625 ?coord . }}
  OPTIONAL {{
    ?esArticle schema:about ?item ;
               schema:isPartOf <https://es.wikipedia.org/> ;
               schema:name ?esTitle .
  }}
  OPTIONAL {{
    ?enArticle schema:about ?item ;
               schema:isPartOf <https://en.wikipedia.org/> ;
               schema:name ?enTitle .
  }}
}}
"""
    try:
        res = sparql_query(q)
        for b in res["results"]["bindings"]:
            k = b["key"]["value"]
            name_hits.setdefault(k, []).append({
                "qid": b["item"]["value"].split("/")[-1],
                "es": b.get("esTitle", {}).get("value", ""),
                "en": b.get("enTitle", {}).get("value", ""),
                "inception": b.get("inception", {}).get("value", ""),
                "coord": b.get("coord", {}).get("value", "")
            })
        print(f"Name batch {idx} ok", flush=True)
    except Exception as e:
        print(f"Name batch {idx} err: {e}", flush=True)
    time.sleep(1.5)

with open("tests/chunk027_wikidata_names.json", "w", encoding="utf-8") as f:
    json.dump(name_hits, f, ensure_ascii=False, indent=2)
print("Done name hits:", len(name_hits))
