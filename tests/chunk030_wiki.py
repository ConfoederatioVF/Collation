import json, urllib.request, urllib.parse, time

from chunk030_local import INPUT

HEADERS = {"User-Agent": "ViscountHistoricalToponymy/1.0 (research)"}

def api_get(lang, params):
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

out = {}
for idx, item in enumerate(INPUT):
    key = item["key"]
    n = item["n"]
    lat, lon = item["ll"]
    c = item["c"]
    rec = {"geo_es": [], "title_es": None, "search_es": [], "geo_en": [], "title_en": None}
    try:
        # 1. Geosearch es
        g = api_get("es", {
            "action": "query", "list": "geosearch",
            "gscoord": f"{lat}|{lon}", "gsradius": 10000, "gslimit": 5, "format": "json"
        })
        rec["geo_es"] = g.get("query", {}).get("geosearch", [])
        # 2. Search by name + country
        q = f"{n} {c}"
        s = api_get("es", {
            "action": "query", "list": "search", "srsearch": q, "srlimit": 3, "format": "json"
        })
        rec["search_es"] = [{"title": x["title"], "snippet": x["snippet"]} for x in s.get("query", {}).get("search", [])]
        # Pick best candidate titles to fetch extracts
        cand_titles = []
        for gitem in rec["geo_es"][:2]:
            cand_titles.append(gitem["title"])
        for sitem in rec["search_es"][:2]:
            if sitem["title"] not in cand_titles:
                cand_titles.append(sitem["title"])
        if cand_titles:
            ex = api_get("es", {
                "action": "query", "titles": "|".join(cand_titles[:4]),
                "prop": "extracts", "exintro": 0, "exchars": 2500, "explaintext": 1, "redirects": 1, "format": "json"
            })
            rec["extracts_es"] = [
                {"title": p.get("title"), "extract": p.get("extract", "")}
                for p in ex.get("query", {}).get("pages", {}).values() if "missing" not in p
            ]
    except Exception as e:
        rec["err_es"] = str(e)
    out[key] = rec
    if (idx + 1) % 15 == 0:
        print(f"Processed {idx+1}/{len(INPUT)}")
    time.sleep(0.08)

with open("tests/chunk030_wiki.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("Saved tests/chunk030_wiki.json")
