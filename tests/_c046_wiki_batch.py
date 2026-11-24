import json, time, urllib.request, urllib.parse

with open(r"f:\Active Projects\Project 1509 - SVEA\tests\_c046_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

UA = {"User-Agent": "ViscountToponymyResearch/1.0 (https://confoederatio.org; mailto:research@confoederatio.org)"}

def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if "429" in str(e):
                time.sleep(2.0 * (attempt + 1))
            else:
                time.sleep(0.5)
    return {}

# Step 1: geosearch on es.wikipedia for all 90 items (gentle sequential, 0.1s delay)
geo_map = {}
for i, it in enumerate(items):
    lat, lon = it["ll"]
    u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
    d = fetch_json(u)
    hits = d.get("query", {}).get("geosearch", [])
    geo_map[it["key"]] = hits
    time.sleep(0.08)

print("Geosearch done:", sum(1 for v in geo_map.values() if v), "/ 90")

# Step 2: collect candidate titles per item (from geosearch + exact name + name with country/province hints)
titles_needed = set()
item_candidates = {}
for it in items:
    cands = []
    for g in geo_map[it["key"]][:3]:
        cands.append(g["title"])
    n = it["n"]
    if n and n != "None":
        cands.append(n)
        cands.append(f"{n} ({it['c']})")
    item_candidates[it["key"]] = list(dict.fromkeys(cands))
    for t in item_candidates[it["key"]]:
        titles_needed.add(t)

# Also do title search on es.wikipedia for items with 0 geosearch hits and non-archaeo modern/colonial names
for it in items:
    if not geo_map[it["key"]] and it["n"] not in ("None", "Arq", "Mal ubicado"):
        q = urllib.parse.quote(f'{it["n"]} {it["c"]}')
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        d = fetch_json(u)
        for s in d.get("query", {}).get("search", [])[:2]:
            if s["title"] not in item_candidates[it["key"]]:
                item_candidates[it["key"]].append(s["title"])
            titles_needed.add(s["title"])
        time.sleep(0.08)

# Step 3: batch fetch full extracts (up to 10 titles per call, redirects=1)
all_titles = sorted(titles_needed)
page_data = {}
for idx in range(0, len(all_titles), 10):
    batch = all_titles[idx:idx+10]
    tp = urllib.parse.quote("|".join(batch))
    u = f"https://es.wikipedia.org/w/api.php?action=query&titles={tp}&redirects=1&prop=extracts|coordinates&explaintext=1&exchars=6000&format=json"
    d = fetch_json(u)
    q = d.get("query", {})
    redirs = {r["from"]: r["to"] for r in q.get("redirects", [])}
    norm = {n["from"]: n["to"] for n in q.get("normalized", [])}
    pages = {}
    for pid, p in q.get("pages", {}).items():
        if int(pid) > 0:
            pages[p["title"]] = {
                "title": p["title"],
                "coords": p.get("coordinates"),
                "extract": p.get("extract", "")
            }
    for t in batch:
        t2 = norm.get(t, t)
        t3 = redirs.get(t2, t2)
        if t3 in pages:
            page_data[t] = pages[t3]
    time.sleep(0.15)

out = []
for it in items:
    pages = []
    seen = set()
    for t in item_candidates[it["key"]]:
        p = page_data.get(t)
        if p and p["title"] not in seen:
            seen.add(p["title"])
            pages.append(p)
    out.append({
        "key": it["key"],
        "n": it["n"],
        "c": it["c"],
        "r": it["r"],
        "ll": it["ll"],
        "ey": it["ey"],
        "ly": it["ly"],
        "al": it.get("al", []),
        "ex": it.get("ex", []),
        "geo": geo_map[it["key"]],
        "pages": pages
    })

with open(r"f:\Active Projects\Project 1509 - SVEA\tests\_c046_wiki_full.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("Wiki full saved! Items with pages:", sum(1 for x in out if x["pages"]))
