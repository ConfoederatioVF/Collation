import json
import time
import urllib.error
import urllib.parse
import urllib.request

HEADERS = {'User-Agent': 'OperationViscountResearch/1.0 (mailto:research@example.org)'}

def api_get(lang, params):
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"Failed after retries: {url}")

with open("tests/q019_wiki_index.json", "r", encoding="utf-8") as f:
    items = json.load(f)

updated = 0
for item in items:
    lat, lng = item["ll"]
    name = item["n"]
    country = item["c"]
    if "es_geo_err" in item or "es_geo" not in item:
        item.pop("es_geo_err", None)
        time.sleep(0.15)
        geo = api_get("es", {
            "action": "query", "list": "geosearch",
            "gscoord": f"{lat}|{lng}", "gsradius": 10000, "gslimit": 5, "format": "json"
        })
        item["es_geo"] = [{"title": g["title"], "dist": g["dist"]} for g in geo.get("query", {}).get("geosearch", [])]
        updated += 1
    if "es_search_err" in item or "es_search" not in item:
        item.pop("es_search_err", None)
        time.sleep(0.15)
        sr = api_get("es", {
            "action": "query", "list": "search",
            "srsearch": f"{name} {country}", "srlimit": 4, "format": "json"
        })
        item["es_search"] = [s["title"] for s in sr.get("query", {}).get("search", [])]
        updated += 1
    if "en_geo_err" in item or "en_geo" not in item:
        item.pop("en_geo_err", None)
        time.sleep(0.15)
        en_geo = api_get("en", {
            "action": "query", "list": "geosearch",
            "gscoord": f"{lat}|{lng}", "gsradius": 10000, "gslimit": 3, "format": "json"
        })
        item["en_geo"] = [{"title": g["title"], "dist": g["dist"]} for g in en_geo.get("query", {}).get("geosearch", [])]
        updated += 1

with open("tests/q019_wiki_index.json", "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"Updated {updated} fields across {len(items)} items.")

# Collect candidate es titles and en titles to fetch extracts
es_titles = []
en_titles = []
seen_es = set()
seen_en = set()

for item in items:
    # Take close geo matches (< 5000m) and any search title that shares a word with n or al
    words = [w.lower() for w in item["n"].replace("(", " ").replace(")", " ").split() if len(w) > 3]
    for al in item.get("al", []):
        words.extend([w.lower() for w in al.split() if len(w) > 3])
    for g in item.get("es_geo", []):
        t = g["title"]
        if g["dist"] < 4000 or any(w in t.lower() for w in words):
            if t not in seen_es:
                seen_es.add(t)
                es_titles.append(t)
    for t in item.get("es_search", []):
        if any(w in t.lower() for w in words):
            if t not in seen_es:
                seen_es.add(t)
                es_titles.append(t)
    for g in item.get("en_geo", []):
        t = g["title"]
        if g["dist"] < 3500 or any(w in t.lower() for w in words):
            if t not in seen_en:
                seen_en.add(t)
                en_titles.append(t)

def fetch_extracts(lang, titles):
    out = {}
    for i in range(0, len(titles), 20):
        batch = titles[i:i+20]
        time.sleep(0.2)
        res = api_get(lang, {
            "action": "query",
            "prop": "extracts|revisions",
            "exintro": False,
            "explaintext": True,
            "exchars": 3500,
            "rvprop": "content",
            "rvslots": "main",
            "titles": "|".join(batch),
            "redirects": 1,
            "format": "json"
        })
        pages = res.get("query", {}).get("pages", {})
        for pid, p in pages.items():
            if int(pid) < 0:
                continue
            title = p.get("title", "")
            extract = p.get("extract", "")
            rev_text = ""
            revs = p.get("revisions", [])
            if revs:
                rev_text = revs[0].get("slots", {}).get("main", {}).get("*", "")[:2500]
            out[title] = {"extract": extract, "infobox_head": rev_text}
    return out

es_pages = fetch_extracts("es", es_titles)
en_pages = fetch_extracts("en", en_titles)

with open("tests/q019_wiki_pages.json", "w", encoding="utf-8") as f:
    json.dump({"es": es_pages, "en": en_pages}, f, ensure_ascii=False, indent=2)

print(f"Fetched {len(es_pages)} es pages and {len(en_pages)} en pages.")
