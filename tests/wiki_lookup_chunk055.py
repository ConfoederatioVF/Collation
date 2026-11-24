import json
import math
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {"User-Agent": "SVEA-Historical-Toponymy-Resolver/1.0 (https://confoederatio.org)"}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

def query_item(item):
    key = item["key"]
    name = item["n"]
    country = item["c"]
    lat, lon = item["ll"]
    res = {"key": key, "n": name, "c": country, "ll": [lat, lon], "geosearch": [], "search": []}
    # 1. es.wikipedia geosearch around ll (10km)
    try:
        geo_url = (
            f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch"
            f"&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
        )
        gdata = fetch_json(geo_url)
        for g in gdata.get("query", {}).get("geosearch", []):
            res["geosearch"].append({
                "title": g["title"],
                "dist_m": g["dist"],
                "pageid": g["pageid"]
            })
    except Exception as e:
        res["geo_err"] = str(e)

    # 2. es.wikipedia text search
    try:
        q = urllib.parse.quote(f"{name} {country}")
        s_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        sdata = fetch_json(s_url)
        for s in sdata.get("query", {}).get("search", []):
            res["search"].append({"title": s["title"], "pageid": s["pageid"]})
    except Exception as e:
        res["search_err"] = str(e)

    # Fetch intro + history extracts for top geosearch or exact match
    titles_to_fetch = []
    for g in res["geosearch"][:2]:
        if g["title"] not in titles_to_fetch:
            titles_to_fetch.append(g["title"])
    for s in res["search"][:2]:
        if s["title"] not in titles_to_fetch:
            titles_to_fetch.append(s["title"])

    res["extracts"] = {}
    if titles_to_fetch:
        try:
            t_param = urllib.parse.quote("|".join(titles_to_fetch))
            ex_url = (
                f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates"
                f"&explaintext=1&exchars=2500&titles={t_param}&format=json"
            )
            edata = fetch_json(ex_url)
            for pid, pinfo in edata.get("query", {}).get("pages", {}).items():
                title = pinfo.get("title")
                coords = pinfo.get("coordinates", [])
                dist = None
                if coords:
                    dist = round(haversine_km(lat, lon, coords[0]["lat"], coords[0]["lon"]), 2)
                res["extracts"][title] = {
                    "dist_km": dist,
                    "extract": (pinfo.get("extract") or "")[:2000]
                }
        except Exception as e:
            res["ex_err"] = str(e)
    return res

def main():
    import lookup_chunk055
    items = lookup_chunk055.INPUT_DATA
    results = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(query_item, it): it["key"] for it in items}
        for fut in as_completed(futs):
            k = futs[fut]
            try:
                results[k] = fut.result()
            except Exception as e:
                results[k] = {"error": str(e)}
    with open("tests/chunk055_wiki.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Fetched wiki for:", len(results))

if __name__ == "__main__":
    main()
