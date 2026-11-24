import json
import math
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

with open("tests/chunk046_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

# 1. Check local QUIPU files
local_hits = {it["key"]: [] for it in items}
src_dir = "histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources"
for fn in os.listdir(src_dir):
    if not fn.endswith(".json"):
        continue
    path = os.path.join(src_dir, fn)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        continue
    rows = data if isinstance(data, list) else data.get("settlements", data.get("data", []))
    if not isinstance(rows, list):
        continue
    for r in rows:
        if not isinstance(r, dict):
            continue
        rlat = r.get("lat") or (r.get("ll")[0] if isinstance(r.get("ll"), list) and len(r.get("ll")) == 2 else None)
        rlng = r.get("lng") or r.get("lon") or (r.get("ll")[1] if isinstance(r.get("ll"), list) and len(r.get("ll")) == 2 else None)
        rname = str(r.get("name") or r.get("n") or "").strip().lower()
        if rlat is None or rlng is None:
            continue
        try:
            rlat, rlng = float(rlat), float(rlng)
        except Exception:
            continue
        for it in items:
            d = haversine(it["ll"][0], it["ll"][1], rlat, rlng)
            if d <= 3.0 or (d <= 15.0 and it["n"].lower() in rname):
                rec = {k: v for k, v in r.items() if k in ("name", "n", "country", "c", "admin1", "admin2", "source", "sources", "year", "foundation_year", "earliest_year", "historical_names", "other_names", "notes", "pop", "p", "type")}
                rec["_file"] = fn
                rec["_dist_km"] = round(d, 2)
                local_hits[it["key"]].append(rec)

# Also check sites_quipu_andes_cone/0.raw_sites
arch_dir = "histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites"
if os.path.exists(arch_dir):
    for fn in os.listdir(arch_dir):
        if not fn.endswith(".json") and not fn.endswith(".geojson"):
            continue
        path = os.path.join(arch_dir, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        rows = data.get("features", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        for r in rows:
            if isinstance(r, dict) and "properties" in r and "geometry" in r:
                props = r["properties"] or {}
                coords = (r["geometry"] or {}).get("coordinates") or []
                if len(coords) >= 2:
                    rlng, rlat = coords[0], coords[1]
                else:
                    continue
            elif isinstance(r, dict):
                props = r
                rlat = r.get("lat")
                rlng = r.get("lng") or r.get("lon")
            else:
                continue
            if rlat is None or rlng is None:
                continue
            try:
                rlat, rlng = float(rlat), float(rlng)
            except Exception:
                continue
            for it in items:
                d = haversine(it["ll"][0], it["ll"][1], rlat, rlng)
                if d <= 2.0:
                    rec = {k: v for k, v in props.items() if k in ("name", "site_name", "culture", "period", "earliest_year", "latest_year", "c14_date", "source", "department", "province", "municipality", "notes")}
                    rec["_file"] = fn
                    rec["_dist_km"] = round(d, 2)
                    local_hits[it["key"]].append(rec)

with open("tests/chunk046_local.json", "w", encoding="utf-8") as f:
    json.dump(local_hits, f, ensure_ascii=False, indent=2)

# 2. Query es.wikipedia.org and en.wikipedia.org
def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "AntigravityToponymyBot/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def research_wiki(it):
    lat, lng = it["ll"]
    name = it["n"]
    country = it["c"]
    out = {"key": it["key"], "n": name, "c": country, "r": it["r"], "ll": it["ll"], "ey": it["ey"], "ly": it["ly"], "es_geo": [], "en_geo": [], "es_search": [], "en_search": []}
    for lang, key_geo, key_sr in [("es", "es_geo", "es_search"), ("en", "en_geo", "en_search")]:
        try:
            u = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
            res = fetch_json(u)
            out[key_geo] = res.get("query", {}).get("geosearch", [])
        except Exception as e:
            out[key_geo] = [{"error": str(e)}]
        if name and name != "None":
            q = urllib.parse.quote(f'"{name}" {country}')
            try:
                u = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
                res = fetch_json(u)
                out[key_sr] = [{"title": x["title"], "snippet": x["snippet"]} for x in res.get("query", {}).get("search", [])]
            except Exception as e:
                out[key_sr] = [{"error": str(e)}]
    # Fetch extracts for top geo hit (within 5km) and top search hit if exact-ish
    titles_es = []
    for g in out["es_geo"]:
        if isinstance(g, dict) and "title" in g and g.get("dist", 99999) < 8000:
            titles_es.append(g["title"])
    for s in out["es_search"][:2]:
        if isinstance(s, dict) and "title" in s and s["title"] not in titles_es:
            titles_es.append(s["title"])
    if titles_es:
        try:
            tparam = urllib.parse.quote("|".join(titles_es[:4]))
            u = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&exintro=false&explaintext=true&exchars=3000&titles={tparam}&format=json"
            res = fetch_json(u)
            out["es_pages"] = list(res.get("query", {}).get("pages", {}).values())
        except Exception as e:
            out["es_pages_err"] = str(e)
    return out

wiki_results = {}
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = {ex.submit(research_wiki, it): it["key"] for it in items}
    for fut in as_completed(futs):
        r = fut.result()
        wiki_results[r["key"]] = r

with open("tests/chunk046_wiki.json", "w", encoding="utf-8") as f:
    json.dump(wiki_results, f, ensure_ascii=False, indent=2)

print("Done. Local hits non-empty:", sum(1 for v in local_hits.values() if v), "/ 90")
print("Wiki results:", len(wiki_results))
