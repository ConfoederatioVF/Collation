import json, time, urllib.parse, urllib.request
from c039_research import INPUT

HEADERS = {"User-Agent": "SVEA-Toponymy-Research/1.0 (https://confoederatio.org)"}

def get_json(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2.5 * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt == 2: raise
            time.sleep(1.5)
    return {}

wiki = {}
for idx, x in enumerate(INPUT):
    lat, lon = x["ll"]
    rec = {"n": x["n"], "c": x["c"], "r": x["r"], "ll": x["ll"], "ey": x["ey"], "ly": x["ly"]}
    # Geosearch es.wikipedia
    try:
        d = get_json(f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json")
        rec["geo_es"] = [{"t": g["title"], "d": round(g["dist"])} for g in d.get("query", {}).get("geosearch", [])]
    except Exception as e:
        rec["geo_err"] = str(e)
    time.sleep(0.2)
    # Search by name + country
    try:
        q = urllib.parse.quote(f"{x['n']} {x['c']}")
        d = get_json(f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json")
        rec["sr_es"] = [s["title"] for s in d.get("query", {}).get("search", [])]
    except Exception as e:
        rec["sr_err"] = str(e)
    time.sleep(0.2)
    cands = []
    for g in rec.get("geo_es", []):
        if g["t"] not in cands: cands.append(g["t"])
    for s in rec.get("sr_es", []):
        if s not in cands: cands.append(s)
    cands = cands[:3]
    rec["extracts"] = {}
    if cands:
        try:
            tp = urllib.parse.quote("|".join(cands))
            d = get_json(f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=0&explaintext=1&exchars=2200&titles={tp}&format=json")
            for pid, p in d.get("query", {}).get("pages", {}).items():
                if "extract" in p:
                    rec["extracts"][p["title"]] = p["extract"]
        except Exception as e:
            rec["ext_err"] = str(e)
        time.sleep(0.2)
    wiki[x["key"]] = rec
    if (idx + 1) % 15 == 0:
        print(f"Wiki {idx+1}/90")
        with open("tests/c039_wiki.json", "w", encoding="utf-8") as f:
            json.dump(wiki, f, ensure_ascii=False, indent=2)

with open("tests/c039_wiki.json", "w", encoding="utf-8") as f:
    json.dump(wiki, f, ensure_ascii=False, indent=2)
print("Wiki done!")
