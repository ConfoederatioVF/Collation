import json
import math
import os
import time
import urllib.parse
import urllib.request

with open("tests/chunk046_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

# 1. Deep local lookup by coordinates (<= 5 km) and exact key across QUIPU
local_deep = {it["key"]: [] for it in items}

# Search hgis_indias_colonial_raw.json by coordinate <= 10 km
hgis_path = "histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/hgis_indias_colonial_raw.json"
if os.path.exists(hgis_path):
    with open(hgis_path, "r", encoding="utf-8") as f:
        hgis = json.load(f)
    if isinstance(hgis, dict):
        for gid, rec in hgis.items():
            if not isinstance(rec, dict):
                continue
            coords = rec.get("coords")
            if isinstance(coords, list) and len(coords) == 2:
                try:
                    lat, lng = float(coords[0]), float(coords[1])
                except Exception:
                    continue
                for it in items:
                    d = haversine(it["ll"][0], it["ll"][1], lat, lng)
                    if d <= 5.0:
                        local_deep[it["key"]].append({
                            "_src": "hgis_indias_colonial_raw",
                            "_dist_km": round(d, 2),
                            "gz_id": gid,
                            "name": rec.get("name"),
                            "modern_name": rec.get("modern_name"),
                            "variants": rec.get("variants"),
                            "province": rec.get("colonial_province"),
                            "partido": rec.get("colonial_partido"),
                            "categoria": rec.get("categoria"),
                            "observations": rec.get("observations", [])[:3],
                            "sources": rec.get("sources", [])[:2],
                        })

# Search raw_setts_*.json by key or <= 3 km
src_dir = "histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources"
for fn in os.listdir(src_dir):
    if not fn.startswith("raw_setts_") or not fn.endswith(".json"):
        continue
    with open(os.path.join(src_dir, fn), "r", encoding="utf-8") as f:
        data = json.load(f)
    # raw_setts_* may be dict of key -> rec, or have "settlements" dict
    sdict = data.get("settlements", data) if isinstance(data, dict) else {}
    if isinstance(sdict, dict):
        for k, rec in sdict.items():
            if not isinstance(rec, dict):
                continue
            for it in items:
                if k == it["key"] or (rec.get("coords") and isinstance(rec["coords"], list) and len(rec["coords"]) == 2 and haversine(it["ll"][0], it["ll"][1], float(rec["coords"][0]), float(rec["coords"][1])) <= 2.0):
                    local_deep[it["key"]].append({
                        "_src": fn,
                        "key": k,
                        "name": rec.get("name"),
                        "other_names": rec.get("other_names"),
                        "admin1": rec.get("admin1"),
                        "admin2": rec.get("admin2"),
                        "foundation_year": rec.get("foundation_year"),
                        "earliest_year": rec.get("earliest_year"),
                        "sources": rec.get("sources"),
                    })

# Search 0.raw_sites and 1.pre_columbian / 2.colonial / 3.post_independence gazetteers
for root, dirs, files in os.walk("histmap/1.data_raw/population_regional/QUIPU"):
    for fn in files:
        if not (fn.endswith("_settlements.json") or fn.endswith("_gazetteer.json") or fn.endswith("_sites.json")):
            continue
        p = os.path.join(root, fn)
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        slist = data.get("settlements", data) if isinstance(data, dict) else data
        if isinstance(slist, dict):
            for k, rec in slist.items():
                if not isinstance(rec, dict):
                    continue
                for it in items:
                    if k == it["key"]:
                        local_deep[it["key"]].append({"_src": fn, "rec": {kk: vv for kk, vv in rec.items() if kk != "population"}})

with open("tests/chunk046_local_deep.json", "w", encoding="utf-8") as f:
    json.dump(local_deep, f, ensure_ascii=False, indent=2)

# 2. Throttled Wikipedia lookup
UA = "SVEA-Viscount-Toponymy/1.0 (research-gazetteer; python-urllib)"

def fetch_json(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=12) as resp:
                time.sleep(0.18)
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2.5 * (attempt + 1))
                continue
            return {"_err": str(e)}
        except Exception as e:
            return {"_err": str(e)}
    return {"_err": "429 after retries"}

wiki_deep = {}
for idx, it in enumerate(items):
    k = it["key"]
    lat, lng = it["ll"]
    name = it["n"]
    country = it["c"]
    rec = {"key": k, "es_geo": [], "es_search": [], "en_geo": [], "pages": []}

    # ES geosearch
    res = fetch_json(f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json")
    rec["es_geo"] = res.get("query", {}).get("geosearch", []) if isinstance(res, dict) else []

    # ES text search (for non-generic names)
    if name and name != "None":
        q = urllib.parse.quote(f'"{name}" {country}')
        res2 = fetch_json(f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json")
        rec["es_search"] = [{"title": x["title"], "snippet": x["snippet"]} for x in res2.get("query", {}).get("search", [])] if isinstance(res2, dict) else []

    # Pick titles to fetch extracts
    titles = []
    for g in rec["es_geo"]:
        if isinstance(g, dict) and g.get("dist", 99999) <= 6000 and g["title"] not in titles:
            titles.append(g["title"])
    for s in rec["es_search"][:2]:
        if isinstance(s, dict) and s["title"] not in titles:
            # avoid obvious off-topic like biography if name is person's name unless no geo hit
            titles.append(s["title"])

    if titles:
        tparam = urllib.parse.quote("|".join(titles[:3]))
        res3 = fetch_json(f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&explaintext=true&exchars=3500&titles={tparam}&format=json")
        for pg in (res3.get("query", {}).get("pages", {}) or {}).values():
            rec["pages"].append({
                "lang": "es",
                "title": pg.get("title"),
                "coordinates": pg.get("coordinates"),
                "extract": pg.get("extract", "")[:2500]
            })
    else:
        # Try EN geosearch if ES returned nothing
        res_en = fetch_json(f"https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=3&format=json")
        rec["en_geo"] = res_en.get("query", {}).get("geosearch", []) if isinstance(res_en, dict) else []
        en_titles = [g["title"] for g in rec["en_geo"] if isinstance(g, dict) and g.get("dist", 99999) <= 6000]
        if en_titles:
            tparam = urllib.parse.quote("|".join(en_titles[:2]))
            res4 = fetch_json(f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&explaintext=true&exchars=2500&titles={tparam}&format=json")
            for pg in (res4.get("query", {}).get("pages", {}) or {}).values():
                rec["pages"].append({
                    "lang": "en",
                    "title": pg.get("title"),
                    "coordinates": pg.get("coordinates"),
                    "extract": pg.get("extract", "")[:2000]
                })

    wiki_deep[k] = rec
    if (idx + 1) % 15 == 0:
        print(f"Processed {idx+1}/90", flush=True)

with open("tests/chunk046_wiki_deep.json", "w", encoding="utf-8") as f:
    json.dump(wiki_deep, f, ensure_ascii=False, indent=2)

print("Completed deep research.")
