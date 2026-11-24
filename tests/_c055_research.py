import json
import urllib.request
import urllib.parse
import concurrent.futures
import time

with open("tests/_c055_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

HEADERS = {"User-Agent": "SVEA-Toponymy-Research/1.0 (contact: research@example.org)"}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def query_wiki(lang, item):
    lat, lng = item["ll"]
    name = item["n"]
    country = item["c"]
    res = {"geosearch": [], "search": []}
    try:
        gs_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
        gs_data = fetch_json(gs_url)
        titles = [g["title"] for g in gs_data.get("query", {}).get("geosearch", [])]
        if titles:
            ex_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote('|'.join(titles))}&prop=extracts|coordinates&exintro=1&explaintext=1&exchars=900&format=json"
            ex_data = fetch_json(ex_url)
            for pid, p in ex_data.get("query", {}).get("pages", {}).items():
                res["geosearch"].append({
                    "title": p.get("title"),
                    "coords": p.get("coordinates"),
                    "extract": p.get("extract", "")
                })
    except Exception as e:
        res["geo_err"] = str(e)
    try:
        q = urllib.parse.quote(f"{name} {country}")
        sr_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        sr_data = fetch_json(sr_url)
        titles = [s["title"] for s in sr_data.get("query", {}).get("search", [])]
        if titles:
            ex_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote('|'.join(titles))}&prop=extracts|coordinates&exintro=1&explaintext=1&exchars=900&format=json"
            ex_data = fetch_json(ex_url)
            for pid, p in ex_data.get("query", {}).get("pages", {}).items():
                res["search"].append({
                    "title": p.get("title"),
                    "coords": p.get("coordinates"),
                    "extract": p.get("extract", "")
                })
    except Exception as e:
        res["sr_err"] = str(e)
    return res

def process_item(item):
    es = query_wiki("es", item)
    en = query_wiki("en", item)
    return {
        "key": item["key"],
        "n": item["n"],
        "c": item["c"],
        "r": item["r"],
        "ll": item["ll"],
        "ey": item["ey"],
        "ly": item["ly"],
        "al": item.get("al", []),
        "es": es,
        "en": en
    }

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    for r in ex.map(process_item, items):
        results.append(r)

with open("tests/_c055_research.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Done: {len(results)} items")
