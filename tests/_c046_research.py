import json, os, glob, math, urllib.request, urllib.parse, concurrent.futures

with open(r"f:\Active Projects\Project 1509 - SVEA\tests\_c046_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

# 1. Check local settlement sources
base = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\QUIPU\_shared\settlement_sources"
local_hits = {it["key"]: [] for it in items}

def dist_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(min(1.0, math.sqrt(a)))

for path in glob.glob(os.path.join(base, "*.json")):
    fn = os.path.basename(path)
    if fn == "wave1_harvest_summary.json":
        continue
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        continue
    rows = data if isinstance(data, list) else (data.get("settlements") or data.get("features") or list(data.values()))
    if isinstance(data, dict) and all(isinstance(v, dict) for v in data.values()):
        rows = list(data.values())
    for row in rows:
        if not isinstance(row, dict):
            continue
        rlat = row.get("lat") or row.get("latitude") or (row.get("ll")[0] if isinstance(row.get("ll"), list) and len(row.get("ll"))>=2 else None)
        rlon = row.get("lng") or row.get("lon") or row.get("longitude") or (row.get("ll")[1] if isinstance(row.get("ll"), list) and len(row.get("ll"))>=2 else None)
        if rlat is None or rlon is None:
            continue
        try:
            rlat, rlon = float(rlat), float(rlon)
        except:
            continue
        for it in items:
            d = dist_km(it["ll"][0], it["ll"][1], rlat, rlon)
            if d < 5.0:
                rname = str(row.get("name") or row.get("nombre") or row.get("n") or row.get("toponimo") or "")
                if d < 0.5 or it["n"].lower()[:4] in rname.lower():
                    compact = {k: v for k, v in row.items() if k not in ("pop", "populations", "series") and v not in (None, "", [])}
                    compact["_src"] = fn
                    compact["_d_km"] = round(d, 3)
                    local_hits[it["key"]].append(compact)

# 2. Query Wikipedia (es + en) geosearch + title search
UA = {"User-Agent": "ViscountToponymyResearch/1.0 (https://confoederatio.org)"}

def fetch_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))

def wiki_lookup(it):
    lat, lon = it["ll"]
    res = {"key": it["key"], "n": it["n"], "c": it["c"], "ll": it["ll"], "ey": it["ey"], "ly": it["ly"], "al": it.get("al", []), "ex": it.get("ex", [])}
    geo_hits = {}
    for lang in ("es", "en"):
        try:
            u = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
            d = fetch_json(u)
            geo_hits[lang] = d.get("query", {}).get("geosearch", [])
        except Exception as e:
            geo_hits[lang] = []
    # Also search by name if needed
    titles_to_fetch = {"es": [], "en": []}
    for lang in ("es", "en"):
        for g in geo_hits[lang]:
            titles_to_fetch[lang].append(g["title"])
        # Also search exact name + country/region
        try:
            q = urllib.parse.quote(f'{it["n"]} {it["c"]}')
            u = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
            d = fetch_json(u)
            for s in d.get("query", {}).get("search", []):
                if s["title"] not in titles_to_fetch[lang]:
                    titles_to_fetch[lang].append(s["title"])
        except Exception:
            pass
    extracts = {}
    for lang in ("es", "en"):
        ts = titles_to_fetch[lang][:4]
        if not ts:
            continue
        try:
            tp = urllib.parse.quote("|".join(ts))
            u = f"https://{lang}.wikipedia.org/w/api.php?action=query&titles={tp}&prop=extracts|coordinates&exintro=0&explaintext=1&exchars=4000&format=json"
            d = fetch_json(u)
            pages = d.get("query", {}).get("pages", {})
            extracts[lang] = []
            for pid, p in pages.items():
                if int(pid) > 0:
                    extracts[lang].append({
                        "title": p.get("title"),
                        "coords": p.get("coordinates"),
                        "extract": p.get("extract", "")[:2500]
                    })
        except Exception:
            pass
    res["geo"] = geo_hits
    res["wiki"] = extracts
    res["local"] = local_hits[it["key"]][:5]
    return res

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    for r in ex.map(wiki_lookup, items):
        results.append(r)

with open(r"f:\Active Projects\Project 1509 - SVEA\tests\_c046_research.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Done:", len(results))
