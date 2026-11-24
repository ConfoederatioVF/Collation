import json, time, urllib.request, urllib.parse

with open("tests/lookup_wiki.py", "r", encoding="utf-8") as f:
    src = f.read()

# Extract SETTLEMENTS
ns = {}
exec(src.split("def fetch")[0], ns)
SETTLEMENTS = ns["SETTLEMENTS"]

UA = "ViscountToponymyResearch/1.0 (https://confoederatio.org; research@confoederatio.org)"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

# Only query settlements that aren't purely obvious pre-colonial sites OR query all sequentially with 0.25s delay
# Actually 90 * 0.25s = ~22s for geosearch! Let's do geosearch for all 90 sequentially, and fetch full extracts for hits.
results = []
for idx, s in enumerate(SETTLEMENTS):
    lat, lon = s["ll"]
    out = {"key": s["key"], "n": s["n"], "c": s["c"], "r": s["r"], "ey": s["ey"], "ly": s["ly"]}
    try:
        gs_url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
        gs = fetch(gs_url).get("query", {}).get("geosearch", [])
        out["es_geo"] = [{"title": g["title"], "dist": g["dist"]} for g in gs]
    except Exception as e:
        out["es_geo_err"] = str(e)
    time.sleep(0.25)

    # Pick title from geo if close or matching, else search
    title = None
    for g in out.get("es_geo", []):
        if g["dist"] < 4000 or s["n"].lower().split()[0] in g["title"].lower():
            title = g["title"]
            break
    if not title and s["ly"] > 1532:
        try:
            q = urllib.parse.quote(f"{s['n']} {s['c']}")
            sr_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
            sr = fetch(sr_url).get("query", {}).get("search", [])
            out["es_sr"] = [x["title"] for x in sr]
            if sr:
                title = sr[0]["title"]
        except Exception as e:
            out["es_sr_err"] = str(e)
        time.sleep(0.25)

    if title:
        try:
            t_param = urllib.parse.quote(title)
            ex_url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&exchars=2500&titles={t_param}&format=json"
            pages = fetch(ex_url).get("query", {}).get("pages", {})
            for p in pages.values():
                if "extract" in p:
                    out["title"] = p.get("title")
                    out["extract"] = p.get("extract", "")
        except Exception as e:
            out["ex_err"] = str(e)
        time.sleep(0.25)
    results.append(out)

with open("tests/wiki_lookup_053.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("Done:", len(results))
