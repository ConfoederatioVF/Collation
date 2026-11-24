import glob, json, math, os, re, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

with open("tests/quipu_023_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Loaded {len(items)} items")

# 1. Search QUIPU gazetteers & data files for matching records
quipu_dir = "histmap/1.data_raw/population_regional/QUIPU"
matches = {}
target_names = {it["n"].lower(): it for it in items}
target_keys = {it["key"]: it for it in items}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

# Scan json / json5 / csv in QUIPU chapters (skip subadmin_hgis raw_sources)
for root, dirs, files in os.walk(quipu_dir):
    if "_gis_cache" in root or "subadmin_hgis" in root or "figures" in root:
        continue
    for fn in files:
        if not fn.endswith((".json", ".json5", ".csv")):
            continue
        fp = os.path.join(root, fn)
        try:
            txt = open(fp, "r", encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for it in items:
            n = it["n"]
            # quick substring check
            if n in txt:
                # extract matching lines/snippets
                for line in txt.splitlines():
                    if n in line:
                        matches.setdefault(it["key"], []).append((os.path.relpath(fp, quipu_dir), line.strip()[:300]))
                        if len(matches[it["key"]]) >= 8:
                            break

with open("tests/quipu_023_local_matches.json", "w", encoding="utf-8") as f:
    json.dump(matches, f, ensure_ascii=False, indent=2)
print(f"Local matches found for {len(matches)} keys")

# 2. Query es.wikipedia.org and en.wikipedia.org geosearch + search
HEADERS = {"User-Agent": "SVEA-Toponymy/1.0 (historical-gazetteer-research)"}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def lookup_item(it):
    lat, lng = it["ll"]
    name = it["n"]
    country = it["c"]
    out = {"key": it["key"], "n": name, "c": country, "r": it["r"], "ll": it["ll"], "ey": it["ey"], "ly": it["ly"], "al": it.get("al", [])}
    
    # Geosearch on es.wikipedia
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
        gs = fetch_json(u).get("query", {}).get("geosearch", [])
        out["es_geo"] = [{"title": g["title"], "dist": round(g["dist"]), "pageid": g["pageid"]} for g in gs]
    except Exception as e:
        out["es_geo_err"] = str(e)

    # Title search on es.wikipedia
    try:
        q = urllib.parse.quote(f"{name} {country}")
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        sr = fetch_json(u).get("query", {}).get("search", [])
        out["es_search"] = [{"title": s["title"], "pageid": s["pageid"], "snippet": re.sub(r'<[^>]+>', '', s.get("snippet",""))} for s in sr]
    except Exception as e:
        out["es_search_err"] = str(e)

    # Fetch summary/extract of top geo match or title match
    cand_titles = []
    for g in out.get("es_geo", [])[:2]:
        cand_titles.append(g["title"])
    for s in out.get("es_search", [])[:2]:
        if s["title"] not in cand_titles:
            cand_titles.append(s["title"])
    
    extracts = {}
    if cand_titles:
        try:
            titles_p = urllib.parse.quote("|".join(cand_titles[:3]))
            u = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&exintro=1&explaintext=1&titles={titles_p}&format=json"
            pages = fetch_json(u).get("query", {}).get("pages", {})
            for pid, p in pages.items():
                if int(pid) > 0:
                    extracts[p.get("title")] = {
                        "extract": p.get("extract", "")[:1500],
                        "coords": p.get("coordinates", [])
                    }
        except Exception as e:
            out["extract_err"] = str(e)
    out["es_extracts"] = extracts
    return out

results = []
with ThreadPoolExecutor(max_workers=8) as ex:
    for res in ex.map(lookup_item, items):
        results.append(res)

with open("tests/quipu_023_wiki.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"Fetched wiki info for {len(results)} items")
