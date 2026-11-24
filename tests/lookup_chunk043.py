import json
import urllib.request
import urllib.parse
import concurrent.futures

HEADERS = {"User-Agent": "OperationViscountResearch/1.0 (contact: research@example.org)"}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode("utf-8"))

def lookup_item(item):
    lat, lng = item["ll"]
    name = item["n"]
    country = item["c"]
    out = {"key": item["key"], "n": name, "c": country, "r": item["r"], "ey": item["ey"]}
    # 1. ES Wikipedia geosearch
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
        d = fetch_json(u)
        gs = d.get("query", {}).get("geosearch", [])
        out["es_geo"] = [(g["title"], round(g["dist"])) for g in gs]
    except Exception as e:
        out["es_geo_err"] = str(e)
    # 2. ES Wikipedia title search
    try:
        q = urllib.parse.quote(f"{name} {country}")
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        d = fetch_json(u)
        sr = d.get("query", {}).get("search", [])
        out["es_search"] = [s["title"] for s in sr]
    except Exception as e:
        out["es_search_err"] = str(e)
    return out

with open("tests/chunk043_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    for res in ex.map(lookup_item, items):
        results.append(res)

with open("tests/chunk043_wiki_geo.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Done:", len(results))
