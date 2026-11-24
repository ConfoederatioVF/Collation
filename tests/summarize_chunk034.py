import json, urllib.request

data = json.load(open("tests/chunk034_wiki.json", encoding="utf-8"))
qids = set()
for item in data:
    for lang in ["es", "en"]:
        for t, ex in item.get(lang, {}).get("extracts", {}).items():
            if ex.get("wikibase"):
                qids.add(ex["wikibase"])

qlist = sorted(qids)
wd = {}
HEADERS = {"User-Agent": "SVEA-Toponymy-Research/1.0"}
for i in range(0, len(qlist), 50):
    batch = "|".join(qlist[i:i+50])
    url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={batch}&props=claims|labels&languages=es|en&format=json"
    req = urllib.request.Request(url, headers=HEADERS)
    res = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
    for q, ent in res.get("entities", {}).items():
        claims = ent.get("claims", {})
        p571 = []
        for c in claims.get("P571", []):
            v = c.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            if isinstance(v, dict) and "time" in v:
                p571.append(v["time"])
        p1448 = []
        for c in claims.get("P1448", []):
            v = c.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            if isinstance(v, dict) and "text" in v:
                p1448.append((v.get("language"), v["text"]))
        wd[q] = {"p571": p571, "p1448": p1448}

open("tests/chunk034_wikidata.json", "w", encoding="utf-8").write(json.dumps(wd, ensure_ascii=False, indent=2))

lines = []
for idx, item in enumerate(data):
    es_geo = [(g["title"], round(g["dist"])) for g in item["es"].get("geosearch", [])[:3]]
    es_srch = [s["title"] for s in item["es"].get("search", [])[:2]]
    exts = []
    for lang in ["es", "en"]:
        for t, ex in item.get(lang, {}).get("extracts", {}).items():
            q = ex.get("wikibase")
            w = wd.get(q, {})
            txt = ex["extract"].replace("\n", " ")[:300]
            exts.append(f"[{lang}:{t} {q} P571={w.get('p571')}] {txt}")
    lines.append(f"{idx:02d}. {item['key']} | n={item['n']} | ey={item['ey']} ly={item['ly']} | geo={es_geo} | srch={es_srch}")
    for e in exts:
        lines.append("    " + e)

open("tests/chunk034_summary.txt", "w", encoding="utf-8").write("\n".join(lines))
print("Wrote summary lines:", len(lines))
