import json
import urllib.request
import urllib.parse
import time
import re

with open("tests/query_chunk026.py", encoding="utf-8") as f:
    src = f.read()

# Extract INPUT from existing script or define helper
from query_chunk026 import INPUT

UA = {"User-Agent": "SVEA-Toponymy-Research/1.0 (https://confoederatio.org; mailto:research@confoederatio.org)"}

def api_get(lang, params):
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if "429" in str(e) or "503" in str(e):
                time.sleep(1.5 * (attempt + 1))
            else:
                time.sleep(0.5)
    return {}

results = []
for idx, item in enumerate(INPUT):
    key = item["key"]
    n = item["n"]
    c = item["c"]
    lat, lng = item["ll"]
    res = {
        "key": key, "n": n, "c": c, "r": item["r"], "ll": item["ll"],
        "ey": item["ey"], "ly": item["ly"], "al": item.get("al", []), "ex": item.get("ex", []),
        "geo_es": [], "search_es": [], "geo_en": [], "extracts": {}
    }
    g = api_get("es", {"action": "query", "list": "geosearch", "gscoord": f"{lat}|{lng}", "gsradius": 10000, "gslimit": 5, "format": "json"})
    res["geo_es"] = g.get("query", {}).get("geosearch", [])

    # Search with name + country or region hint
    s = api_get("es", {"action": "query", "list": "search", "srsearch": f'"{n}" {c}', "srlimit": 4, "format": "json"})
    res["search_es"] = [{"title": x["title"], "snippet": re.sub("<[^>]+>", "", x["snippet"])} for x in s.get("query", {}).get("search", [])]

    # Also search by aliases if no good match
    if not res["geo_es"] and not res["search_es"] and item.get("al"):
        s2 = api_get("es", {"action": "query", "list": "search", "srsearch": f'"{item["al"][0]}" {c}', "srlimit": 2, "format": "json"})
        res["search_es"].extend([{"title": x["title"], "snippet": re.sub("<[^>]+>", "", x["snippet"])} for x in s2.get("query", {}).get("search", [])])

    # Pick titles carefully
    titles = []
    n_low = n.lower()
    first_tok = n_low.split()[0]
    for g_item in res["geo_es"]:
        t_low = g_item["title"].lower()
        if n_low in t_low or first_tok in t_low or g_item["dist"] < 2000:
            titles.append(g_item["title"])
    for s_item in res["search_es"]:
        t_low = s_item["title"].lower()
        if (n_low in t_low or first_tok in t_low or any(a.lower() in t_low for a in item.get("al", []))) and s_item["title"] not in titles:
            titles.append(s_item["title"])
    if not titles and res["geo_es"]:
        titles.append(res["geo_es"][0]["title"])

    if titles:
        ex = api_get("es", {"action": "query", "titles": "|".join(titles[:3]), "prop": "extracts", "explaintext": 1, "exchars": 5000, "format": "json"})
        for pid, pinfo in ex.get("query", {}).get("pages", {}).items():
            if "extract" in pinfo:
                res["extracts"][pinfo["title"]] = pinfo["extract"]

    # EN fallback if still thin
    if not res["extracts"]:
        ge = api_get("en", {"action": "query", "list": "geosearch", "gscoord": f"{lat}|{lng}", "gsradius": 10000, "gslimit": 3, "format": "json"})
        res["geo_en"] = ge.get("query", {}).get("geosearch", [])
        if res["geo_en"]:
            ex_en = api_get("en", {"action": "query", "titles": "|".join(x["title"] for x in res["geo_en"][:2]), "prop": "extracts", "explaintext": 1, "exchars": 3000, "format": "json"})
            for pid, pinfo in ex_en.get("query", {}).get("pages", {}).items():
                if "extract" in pinfo:
                    res["extracts"]["EN:" + pinfo["title"]] = pinfo["extract"]

    results.append(res)
    time.sleep(0.05)

with open("tests/chunk026_research_full.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Done:", len(results))
