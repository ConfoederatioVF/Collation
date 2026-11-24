import concurrent.futures
import glob
import json
import math
import os
import re
import urllib.parse
import urllib.request

with open("tests/chunk055_input.json", encoding="utf-8") as f:
    ITEMS = json.load(f)

HEADERS = {"User-Agent": "ViscountToponymyResearch/1.0 (https://confoederatio.org)"}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

def search_local():
    local_hits = {x["key"]: [] for x in ITEMS}
    files = (
        glob.glob("histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/*.json")
        + glob.glob("histmap/1.data_raw/population_regional/QUIPU/*/*/*_settlements.json")
        + glob.glob("histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/*.json")
        + glob.glob("histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/*/*.json")
    )
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        rows = []
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            for k in ("settlements", "features", "sites", "records", "data"):
                if k in data and isinstance(data[k], list):
                    rows = data[k]
                    break
            if not rows:
                for v in data.values():
                    if isinstance(v, list):
                        rows.extend(v)
        fn = os.path.basename(fp)
        for row in rows:
            if not isinstance(row, dict):
                continue
            rkey = str(row.get("key") or "")
            rlat = row.get("lat")
            rlng = row.get("lng") or row.get("lon")
            if rlat is None and isinstance(row.get("ll"), list) and len(row["ll"]) >= 2:
                rlat, rlng = row["ll"][0], row["ll"][1]
            if rlat is None and isinstance(row.get("geometry"), dict):
                coords = row["geometry"].get("coordinates", [])
                if len(coords) >= 2:
                    rlng, rlat = coords[0], coords[1]
            for item in ITEMS:
                hit = False
                if rkey and rkey == item["key"]:
                    hit = True
                elif rlat is not None and rlng is not None:
                    try:
                        d = haversine(item["ll"][0], item["ll"][1], float(rlat), float(rlng))
                        if d < 1.2:
                            hit = True
                    except Exception:
                        pass
                if hit:
                    compact = {
                        k: v
                        for k, v in row.items()
                        if k not in ("geometry", "pop", "population", "years") and len(str(v)) < 600
                    }
                    local_hits[item["key"]].append({"file": fn, "data": compact})
    with open("tests/chunk055_local.json", "w", encoding="utf-8") as f:
        json.dump(local_hits, f, ensure_ascii=False, indent=2)
    print("Local hits:", sum(1 for v in local_hits.values() if v), "/", len(ITEMS))

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode("utf-8"))

def clean_name(n):
    return re.sub(r"\s*\([^)]*\)", "", n).strip()

def query_wiki(it):
    lat, lon = it["ll"]
    name = clean_name(it["n"])
    country = it["c"]
    out = {"key": it["key"], "es_geo": [], "en_geo": [], "es_search": [], "extracts": {}}
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=8&format=json"
        out["es_geo"] = fetch_json(u).get("query", {}).get("geosearch", [])
    except Exception as e:
        out["es_geo_err"] = str(e)
    try:
        u = f"https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
        out["en_geo"] = fetch_json(u).get("query", {}).get("geosearch", [])
    except Exception:
        pass
    try:
        q = urllib.parse.quote(f'"{name}" {country}')
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=5&format=json"
        out["es_search"] = fetch_json(u).get("query", {}).get("search", [])
    except Exception:
        pass

    es_titles = []
    name_low = name.lower()
    words = [w for w in re.split(r"\W+", name_low) if len(w) > 3]
    for g in out["es_geo"]:
        tl = g["title"].lower()
        if g["dist"] < 3000 or name_low in tl or any(w in tl for w in words):
            if g["title"] not in es_titles:
                es_titles.append(g["title"])
    for s in out["es_search"][:3]:
        tl = s["title"].lower()
        if s["title"] not in es_titles and (name_low in tl or any(w in tl for w in words)):
            es_titles.append(s["title"])
    if not es_titles and out["es_geo"]:
        es_titles.append(out["es_geo"][0]["title"])

    if es_titles:
        try:
            titles_param = urllib.parse.quote("|".join(es_titles[:4]))
            u = f"https://es.wikipedia.org/w/api.php?action=query&titles={titles_param}&prop=extracts|coordinates&explaintext=1&exchars=4500&format=json"
            pages = fetch_json(u).get("query", {}).get("pages", {})
            for pid, p in pages.items():
                if int(pid) > 0:
                    out["extracts"][f"es:{p['title']}"] = {
                        "coords": p.get("coordinates"),
                        "extract": p.get("extract", "")[:4000],
                    }
        except Exception:
            pass

    en_titles = [g["title"] for g in out["en_geo"][:2] if g["dist"] < 4000 or any(w in g["title"].lower() for w in words)]
    if en_titles:
        try:
            titles_param = urllib.parse.quote("|".join(en_titles))
            u = f"https://en.wikipedia.org/w/api.php?action=query&titles={titles_param}&prop=extracts|coordinates&explaintext=1&exchars=3000&format=json"
            pages = fetch_json(u).get("query", {}).get("pages", {})
            for pid, p in pages.items():
                if int(pid) > 0:
                    out["extracts"][f"en:{p['title']}"] = {
                        "coords": p.get("coordinates"),
                        "extract": p.get("extract", "")[:2500],
                    }
        except Exception:
            pass
    return out

search_local()
wiki_res = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    for res in ex.map(query_wiki, ITEMS):
        wiki_res[res["key"]] = res

with open("tests/chunk055_wiki.json", "w", encoding="utf-8") as f:
    json.dump(wiki_res, f, ensure_ascii=False, indent=2)
print("Wiki lookup done:", len(wiki_res))
