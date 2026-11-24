import json
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

with open(r"f:\Active Projects\Project 1509 - SVEA\tests\chunk016_local_matches.json", encoding="utf-8") as f:
    data = json.load(f)

HEADERS = {"User-Agent": "ViscountToponymyResearch/1.0 (https://confoederatio.org; research@confoederatio.org)"}

def wiki_search_and_extract(lang, query):
    url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&srlimit=3&format=json"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as r:
        res = json.loads(r.read().decode("utf-8"))
    hits = res.get("query", {}).get("search", [])
    if not hits:
        return []
    titles = "|".join(h["title"] for h in hits[:2])
    url2 = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&explaintext=1&exchars=3500&titles={urllib.parse.quote(titles)}&format=json"
    req2 = urllib.request.Request(url2, headers=HEADERS)
    with urllib.request.urlopen(req2, timeout=12) as r2:
        res2 = json.loads(r2.read().decode("utf-8"))
    pages = res2.get("query", {}).get("pages", {})
    out = []
    for pid, p in pages.items():
        if int(pid) > 0:
            out.append({
                "title": p.get("title"),
                "coords": p.get("coordinates"),
                "extract": p.get("extract", "")[:1500]
            })
    return out

def process_item(item):
    n = item["n"]
    c = item["c"]
    # Build context term
    ctx = c
    if item["raw"]:
        r0 = item["raw"][0]
        ctx = f"{r0.get('admin2') or ''} {r0.get('admin1') or ''} {c}".strip()
    elif item["hgis"]:
        # pick closest hgis
        lat, lng = item["ll"]
        best = min(item["hgis"], key=lambda h: abs(h["coords"][0]-lat)+abs(h["coords"][1]-lng))
        ctx = f"{best.get('partido') or ''} {best.get('prov') or ''} {c}".strip()
    
    # Specific queries
    res_es = []
    try:
        res_es = wiki_search_and_extract("es", f"{n} {ctx}")
        if not res_es:
            res_es = wiki_search_and_extract("es", f"{n} {c}")
        if not res_es:
            res_es = wiki_search_and_extract("en", f"{n} {c}")
    except Exception as e:
        res_es = [{"error": str(e)}]
    return item["input_key"], res_es

results = {}
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = [ex.submit(process_item, item) for item in data]
    for fut in as_completed(futs):
        k, r = fut.result()
        results[k] = r

ordered = [{"key": item["input_key"], "n": item["n"], "ll": item["ll"], "wiki_es": results[item["input_key"]]} for item in data]
with open(r"f:\Active Projects\Project 1509 - SVEA\tests\chunk016_wiki.json", "w", encoding="utf-8") as f:
    json.dump(ordered, f, ensure_ascii=False, indent=2)

print("Done:", len(ordered))
