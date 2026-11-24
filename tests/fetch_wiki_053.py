import json, urllib.request, urllib.parse, time, concurrent.futures

from inspect_quipu_chunk053 import INPUT

UA = "SVEA-Toponymy/1.0 (contact@example.org)"

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))

def query_settlement(item):
    key = item["key"]
    name = item["n"]
    lat, lon = item["ll"]
    country = item["c"]
    out = {"key": key, "n": name, "c": country, "r": item["r"], "ey": item["ey"], "ly": item["ly"], "al": item.get("al", [])}
    
    # 1. ES Wikipedia geosearch within 10km
    try:
        geo_url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
        g = fetch_json(geo_url)
        geo_hits = g.get("query", {}).get("geosearch", [])
        out["es_geo"] = [{"title": x["title"], "dist": x["dist"]} for x in geo_hits]
    except Exception as e:
        out["es_geo_err"] = str(e)

    # 2. ES Wikipedia text search
    try:
        q = urllib.parse.quote(f"{name} {country}")
        s_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        s = fetch_json(s_url)
        out["es_search"] = [x["title"] for x in s.get("query", {}).get("search", [])]
    except Exception as e:
        out["es_search_err"] = str(e)

    # 3. Pick best title to get extract (prefer geo hit if name matches or close, else first search hit)
    titles_to_fetch = []
    for gh in out.get("es_geo", []):
        if name.lower().split()[0] in gh["title"].lower() or gh["dist"] < 2500:
            titles_to_fetch.append(gh["title"])
    for st in out.get("es_search", [])[:2]:
        if st not in titles_to_fetch:
            titles_to_fetch.append(st)
    titles_to_fetch = titles_to_fetch[:3]

    extracts = {}
    if titles_to_fetch:
        try:
            t_param = urllib.parse.quote("|".join(titles_to_fetch))
            ex_url = f"https://es.wikipedia.org/w/api.php?action=query&titles={t_param}&prop=extracts|coordinates&explaintext=1&exchars=1800&format=json"
            ex = fetch_json(ex_url)
            for pid, pdata in ex.get("query", {}).get("pages", {}).items():
                if "missing" not in pdata:
                    extracts[pdata["title"]] = {
                        "coords": pdata.get("coordinates"),
                        "extract": pdata.get("extract", "")[:1500]
                    }
        except Exception as e:
            out["ex_err"] = str(e)
    out["es_extracts"] = extracts
    return out

results = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    futs = {ex.submit(query_settlement, item): item["key"] for item in INPUT}
    for fut in concurrent.futures.as_completed(futs):
        r = fut.result()
        results[r["key"]] = r

with open("tests/wiki_hits_053.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Done fetching", len(results))
