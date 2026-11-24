import json
import urllib.request
import urllib.parse
import concurrent.futures

with open("tests/chunk054_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

HEADERS = {"User-Agent": "SVEA-Toponymy-Research/1.0"}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))

def query_wiki(item):
    lat, lng = item["ll"]
    name = item["n"]
    country = item["c"]
    out = {"key": item["key"], "n": name, "c": country, "r": item["r"], "ll": item["ll"], "ey": item["ey"], "ly": item["ly"]}
    
    # 1. es.wikipedia geosearch
    try:
        geo_url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gsradius=10000&gscoord={lat}|{lng}&gslimit=5&format=json"
        geo = fetch_json(geo_url)
        out["es_geo"] = [(g["title"], round(g["dist"])) for g in geo.get("query", {}).get("geosearch", [])]
    except Exception as e:
        out["es_geo_err"] = str(e)

    # 2. es.wikipedia search by name + country
    try:
        q = urllib.parse.quote(f'"{name}" {country}')
        s_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        sr = fetch_json(s_url)
        out["es_search"] = [s["title"] for s in sr.get("query", {}).get("search", [])]
    except Exception as e:
        out["es_search_err"] = str(e)

    # Pick candidate page titles to fetch extract
    titles = []
    for t, d in out.get("es_geo", []):
        if t.lower() in name.lower() or name.lower() in t.lower() or d < 3000:
            if t not in titles:
                titles.append(t)
    for t in out.get("es_search", []):
        if t not in titles and (name.lower() in t.lower() or country.lower() in t.lower()):
            titles.append(t)
    titles = titles[:3]

    out["extracts"] = {}
    if titles:
        try:
            t_param = urllib.parse.quote("|".join(titles))
            ex_url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=false&exchars=1800&explaintext=true&titles={t_param}&format=json"
            ex = fetch_json(ex_url)
            for pid, pdata in ex.get("query", {}).get("pages", {}).items():
                if "extract" in pdata:
                    out["extracts"][pdata["title"]] = pdata["extract"][:1500]
        except Exception as e:
            out["extract_err"] = str(e)
    return out

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    for res in pool.map(query_wiki, items):
        results.append(res)

with open("tests/chunk054_wiki.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Done:", len(results))
