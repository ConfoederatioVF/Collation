import json, time, urllib.request, urllib.parse

with open("tests/chunk034_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

HEADERS = {"User-Agent": "SVEA-Toponymy/1.0 (https://confoederatio.org; research@confoederatio.org)"}

def fetch_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if "429" in str(e):
                time.sleep(2 * (i + 1))
            else:
                time.sleep(0.5)
    return {}

# 1. Batch geosearch sequentially with polite delay (only 90 calls -> ~20s)
geo_results = {}
all_titles = set()
for idx, item in enumerate(items):
    lat, lon = item["ll"]
    url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
    d = fetch_json(url)
    gs = d.get("query", {}).get("geosearch", [])
    if not gs:
        # fallback: try search by name + country
        q = urllib.parse.quote(f"{item['n']} {item['c']}")
        u2 = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        d2 = fetch_json(u2)
        sr = [{"title": x["title"]} for x in d2.get("query", {}).get("search", [])]
        geo_results[item["key"]] = {"geo": [], "sr": sr}
        for s in sr[:2]:
            all_titles.add(s["title"])
    else:
        geo_results[item["key"]] = {"geo": gs, "sr": []}
        for g in gs[:2]:
            all_titles.add(g["title"])
    time.sleep(0.18)

# Also add direct title candidates for items that might have an article under exact name
for item in items:
    all_titles.add(item["n"])

titles_list = sorted(all_titles)
extracts = {}
for i in range(0, len(titles_list), 20):
    batch = urllib.parse.quote("|".join(titles_list[i:i+20]))
    url = f"https://es.wikipedia.org/w/api.php?action=query&titles={batch}&prop=extracts|pageprops&exintro=1&explaintext=1&redirects=1&format=json"
    d = fetch_json(url)
    q = d.get("query", {})
    redirects = {r["from"]: r["to"] for r in q.get("redirects", [])}
    pages_by_title = {}
    for pid, p in q.get("pages", {}).items():
        if "title" in p and "missing" not in p:
            pages_by_title[p["title"]] = {
                "extract": (p.get("extract") or "")[:1200],
                "wikibase": p.get("pageprops", {}).get("wikibase_item")
            }
    for t in titles_list[i:i+20]:
        target = redirects.get(t, t)
        if target in pages_by_title:
            extracts[t] = {"resolved": target, **pages_by_title[target]}
    time.sleep(0.25)

# Fetch Wikidata P571 (inception) and P1448 (official name)
qids = sorted({v["wikibase"] for v in extracts.values() if v.get("wikibase")})
wd = {}
for i in range(0, len(qids), 50):
    batch = "|".join(qids[i:i+50])
    url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={batch}&props=claims&format=json"
    d = fetch_json(url)
    for qid, ent in d.get("entities", {}).items():
        claims = ent.get("claims", {})
        p571 = [c["mainsnak"]["datavalue"]["value"]["time"] for c in claims.get("P571", []) if "datavalue" in c.get("mainsnak", {}) and isinstance(c["mainsnak"]["datavalue"]["value"], dict) and "time" in c["mainsnak"]["datavalue"]["value"]]
        p1448 = [c["mainsnak"]["datavalue"]["value"]["text"] for c in claims.get("P1448", []) if "datavalue" in c.get("mainsnak", {}) and isinstance(c["mainsnak"]["datavalue"]["value"], dict) and "text" in c["mainsnak"]["datavalue"]["value"]]
        wd[qid] = {"p571": p571, "p1448": p1448}
    time.sleep(0.25)

out = []
for idx, item in enumerate(items):
    gr = geo_results[item["key"]]
    cand_titles = [g["title"] for g in gr["geo"][:2]] + [s["title"] for s in gr["sr"][:2]] + [item["n"]]
    seen = set()
    cands = []
    for t in cand_titles:
        if t not in seen and t in extracts:
            seen.add(t)
            ex = extracts[t]
            w = wd.get(ex.get("wikibase"), {})
            cands.append({"title": t, "resolved": ex["resolved"], "qid": ex.get("wikibase"), "p571": w.get("p571", []), "p1448": w.get("p1448", []), "extract": ex["extract"]})
    out.append({"idx": idx, "key": item["key"], "n": item["n"], "c": item["c"], "r": item["r"], "ll": item["ll"], "ey": item["ey"], "ly": item["ly"], "geo": [(g["title"], round(g["dist"])) for g in gr["geo"][:3]], "cands": cands})

open("tests/chunk034_resolved_wiki.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2))
print("Saved", len(out), "items; with cands:", sum(1 for x in out if x["cands"]))
