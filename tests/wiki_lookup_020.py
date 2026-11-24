import json
import urllib.request
import urllib.parse
import re
import time

with open("tests/lookup_chunk_020.py", "r", encoding="utf-8") as f:
    src = f.read()
# Extract INPUT
m = re.search(r"INPUT = (\[.*?\])\n\n# 1\.", src, re.S)
INPUT = json.loads(m.group(1))

HEADERS = {"User-Agent": "SVEA-Toponymy/1.0 (academic research)"}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))

def wiki_lookup(item):
    lat, lng = item["ll"]
    name = item["n"]
    country = item["c"]
    res = {"key": item["key"], "n": name, "c": country, "r": item["r"], "ey": item["ey"]}
    
    # 1. Geosearch on es.wikipedia
    try:
        geo_url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
        g = fetch_json(geo_url).get("query", {}).get("geosearch", [])
        res["geo_es"] = [x["title"] for x in g]
    except Exception as e:
        res["geo_es_err"] = str(e)

    # 2. Text search on es.wikipedia
    clean_n = re.sub(r"\(.*?\)", "", name).strip()
    q = urllib.parse.quote(f"{clean_n} {country}")
    try:
        sr_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        s = fetch_json(sr_url).get("query", {}).get("search", [])
        res["search_es"] = [x["title"] for x in s]
    except Exception as e:
        res["search_es_err"] = str(e)

    # Pick best title to fetch extract
    candidates = []
    for t in res.get("geo_es", []) + res.get("search_es", []):
        if t not in candidates:
            candidates.append(t)
    # Prioritize title matching clean_n
    best = None
    cn_low = clean_n.lower()
    for t in candidates:
        if cn_low in t.lower() or any(w in t.lower() for w in cn_low.split() if len(w) > 3):
            best = t
            break
    if not best and candidates:
        best = candidates[0]

    if best:
        try:
            ex_url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&exchars=1800&titles={urllib.parse.quote(best)}&format=json"
            pages = fetch_json(ex_url).get("query", {}).get("pages", {})
            for pid, pdata in pages.items():
                res["best_title"] = pdata.get("title")
                res["extract"] = pdata.get("extract", "")[:1600]
        except Exception as e:
            res["extract_err"] = str(e)
    return res

out = []
for idx, item in enumerate(INPUT):
    out.append(wiki_lookup(item))
    if idx % 10 == 9:
        time.sleep(0.3)

with open("tests/wiki_020.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("Done wiki_020.json, count:", len(out))
