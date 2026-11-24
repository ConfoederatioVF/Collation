import json
import urllib.request
import urllib.parse
import urllib.error
import time

with open("tests/chunk017_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

HEADERS = {"User-Agent": "ProjectSVEA-ToponymyResearch/1.0 (contact: local-research-script)"}

def fetch_json(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                wait = 2 * (attempt + 1)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"Failed after retries: {url}")

results = []
for idx, item in enumerate(items):
    key = item["key"]
    name = item["n"]
    country = item["c"]
    lat, lng = item["ll"]
    res = {"key": key, "n": name, "c": country, "r": item["r"], "ll": item["ll"], "ey": item["ey"], "ly": item["ly"], "al": item.get("al", []), "ex": item.get("ex", [])}
    
    try:
        geo_url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}%7C{lng}&gsradius=10000&gslimit=5&format=json"
        geo = fetch_json(geo_url)
        res["es_geo"] = geo.get("query", {}).get("geosearch", [])
    except Exception as e:
        res["es_geo_err"] = str(e)

    try:
        q = urllib.parse.quote(f"{name} {country}")
        sr_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        sr = fetch_json(sr_url)
        res["es_sr"] = [x["title"] for x in sr.get("query", {}).get("search", [])]
    except Exception as e:
        res["es_sr_err"] = str(e)

    titles = []
    for g in res.get("es_geo", [])[:2]:
        if g["title"] not in titles:
            titles.append(g["title"])
    for t in res.get("es_sr", [])[:2]:
        if t not in titles:
            titles.append(t)

    res["es_pages"] = {}
    if titles:
        try:
            t_param = urllib.parse.quote("|".join(titles[:3]))
            ext_url = f"https://es.wikipedia.org/w/api.php?action=query&titles={t_param}&prop=extracts|revisions&rvprop=content&rvslots=main&explaintext=1&exchars=2200&format=json"
            ext = fetch_json(ext_url)
            for pid, pdata in ext.get("query", {}).get("pages", {}).items():
                title = pdata.get("title", "")
                extract = pdata.get("extract", "")
                wikitext = ""
                revs = pdata.get("revisions", [])
                if revs:
                    wikitext = revs[0].get("slots", {}).get("main", {}).get("*", "")[:3000]
                res["es_pages"][title] = {"extract": extract, "infobox": wikitext}
        except Exception as e:
            res["es_ext_err"] = str(e)

    results.append(res)
    if (idx + 1) % 15 == 0:
        print(f"Processed {idx + 1}/90 (last={key}, geo={len(res.get('es_geo', []))}, sr={len(res.get('es_sr', []))})", flush=True)
    time.sleep(0.25)

with open("tests/chunk017_wiki.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Fetched {len(results)} items")
