import json
import urllib.request
import urllib.parse
import time
import re

UA = {"User-Agent": "ViscountToponymyBot/1.0 (https://confoederatio.org; research@confoederatio.org)"}

def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            raise

def clean_html(s):
    return re.sub(r"<[^>]+>", "", s)

with open("tests/chunk054_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

results = []
for idx, item in enumerate(items):
    key = item["key"]
    n = item["n"]
    c = item["c"]
    lat, lng = item["ll"]
    r = item["r"]
    out = [f"=== [{idx+1}/90] {key} | n={n} | c={c} | r={r} | ll={lat},{lng} | ey={item['ey']} | ly={item['ly']} | al={item.get('al', [])} | ex={item.get('ex', [])}"]

    geo = []
    try:
        geo_url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
        geo = fetch_json(geo_url).get("query", {}).get("geosearch", [])
        if geo:
            out.append("  GEO_ES: " + "; ".join(f"{g['title']} ({int(g['dist'])}m)" for g in geo))
    except Exception as e:
        out.append(f"  GEO_ES_ERR: {e}")
    time.sleep(0.25)

    titles_to_fetch = []
    try:
        q = urllib.parse.quote(f"{n} {c}")
        s_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        sr = fetch_json(s_url).get("query", {}).get("search", [])
        if sr:
            out.append("  SEARCH_ES: " + "; ".join(f"{x['title']}: {clean_html(x['snippet'])[:140]}" for x in sr))
            titles_to_fetch.append(sr[0]["title"])
    except Exception as e:
        out.append(f"  SEARCH_ES_ERR: {e}")
    time.sleep(0.25)

    if geo and geo[0]["title"] not in titles_to_fetch and geo[0]["dist"] < 5000:
        titles_to_fetch.append(geo[0]["title"])

    if titles_to_fetch:
        try:
            qt = urllib.parse.quote("|".join(titles_to_fetch[:2]))
            ext_url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&explaintext=1&exintro=0&exchars=2400&titles={qt}&format=json"
            pages = fetch_json(ext_url).get("query", {}).get("pages", {})
            for pid, p in pages.items():
                if pid == "-1":
                    continue
                coords = p.get("coordinates", [])
                cstr = f" ({coords[0]['lat']},{coords[0]['lon']})" if coords else ""
                txt = (p.get("extract") or "").replace("\n", " ")[:1800]
                out.append(f"  PAGE_ES[{p.get('title','')}{cstr}]: {txt}")
        except Exception as e:
            out.append(f"  PAGE_ES_ERR: {e}")
        time.sleep(0.25)

    results.append("\n".join(out))
    if (idx + 1) % 15 == 0:
        print(f"Progress: {idx+1}/90", flush=True)

with open("tests/chunk054_wiki_report.txt", "w", encoding="utf-8") as f:
    f.write("\n\n".join(results))

print(f"Done: {len(results)} items")
