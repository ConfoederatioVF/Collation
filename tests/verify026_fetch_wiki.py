import json, urllib.request, urllib.parse, time, math

with open("tests/chunk026_research.json", encoding="utf-8") as f:
    research = json.load(f)
with open("tests/verify026_wikidata.json", encoding="utf-8") as f:
    wd = json.load(f)

UA = {"User-Agent": "OperationViscountToponymy/1.0 (https://confoederatio.org; mailto:research@confoederatio.org)"}

def api_get(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            time.sleep(1.5 * (attempt + 1))
    return {}

# Collect eswiki and enwiki titles from Wikidata results
es_titles = []
en_titles = []
key_to_titles = {}
for item in research:
    k = item["key"]
    hits = wd.get(k, [])
    kt = []
    seen = set()
    for h in hits:
        es = h.get("eswiki", "")
        en = h.get("enwiki", "")
        if es and "/wiki/" in es:
            t = urllib.parse.unquote(es.split("/wiki/")[-1]).replace("_", " ")
            if t not in seen:
                seen.add(t)
                es_titles.append(t)
                kt.append(("es", t, h.get("inception", ""), h.get("label", "")))
        elif en and "/wiki/" in en:
            t = urllib.parse.unquote(en.split("/wiki/")[-1]).replace("_", " ")
            if t not in seen:
                seen.add(t)
                en_titles.append(t)
                kt.append(("en", t, h.get("inception", ""), h.get("label", "")))
    key_to_titles[k] = kt

# Deduplicate titles preserving order
es_unique = list(dict.fromkeys(es_titles))
en_unique = list(dict.fromkeys(en_titles))
print(f"Fetching {len(es_unique)} eswiki and {len(en_unique)} enwiki pages in batches of 20...")

es_extracts = {}
for i in range(0, len(es_unique), 20):
    batch = es_unique[i:i+20]
    url = "https://es.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "titles": "|".join(batch), "prop": "extracts",
        "explaintext": 1, "exintro": 0, "exchars": 3000, "redirects": 1, "format": "json"
    })
    d = api_get(url)
    for pid, pinfo in d.get("query", {}).get("pages", {}).items():
        if "extract" in pinfo:
            es_extracts[pinfo["title"]] = pinfo["extract"]
    time.sleep(0.3)

en_extracts = {}
for i in range(0, len(en_unique), 20):
    batch = en_unique[i:i+20]
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "titles": "|".join(batch), "prop": "extracts",
        "explaintext": 1, "exintro": 0, "exchars": 3000, "redirects": 1, "format": "json"
    })
    d = api_get(url)
    for pid, pinfo in d.get("query", {}).get("pages", {}).items():
        if "extract" in pinfo:
            en_extracts[pinfo["title"]] = pinfo["extract"]
    time.sleep(0.3)

# Also check hgis_indias_colonial_raw.json for any coordinate matches within 15 km
hgis_matches = {}
try:
    hgis = json.load(open("histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/hgis_indias_colonial_raw.json", encoding="utf-8"))
    # handle list or dict or geojson
    feats = hgis.get("features", hgis) if isinstance(hgis, dict) else hgis
    pts = []
    for f in feats:
        if isinstance(f, dict):
            if "geometry" in f and f["geometry"]:
                coords = f["geometry"].get("coordinates")
                if coords and len(coords) >= 2 and isinstance(coords[0], (int, float)):
                    pts.append((coords[1], coords[0], f.get("properties", {})))
            elif "lat" in f and "lon" in f:
                pts.append((f["lat"], f["lon"], f))
    for item in research:
        lat, lng = item["ll"]
        m = []
        for plat, plng, props in pts:
            if abs(plat - lat) < 0.15 and abs(plng - lng) < 0.15:
                dist = math.hypot((plat - lat)*111.0, (plng - lng)*111.0*math.cos(math.radians(lat)))
                if dist <= 15.0:
                    m.append((round(dist, 2), props))
        m.sort(key=lambda x: x[0])
        if m:
            hgis_matches[item["key"]] = m[:5]
    print("HGIS matches:", len(hgis_matches))
except Exception as e:
    print("HGIS error:", e)

out = []
for item in research:
    k = item["key"]
    kt = key_to_titles.get(k, [])
    ex_list = []
    for lang, t, inc, lbl in kt:
        txt = es_extracts.get(t, "") if lang == "es" else en_extracts.get(t, "")
        ex_list.append({"lang": lang, "title": t, "inception": inc, "label": lbl, "extract": txt[:2500]})
    out.append({
        "key": k, "n": item["n"], "c": item["c"], "r": item["r"],
        "ll": item["ll"], "ey": item["ey"], "ly": item["ly"],
        "al": item.get("al", []), "ex": item.get("ex", []),
        "wd_wiki": ex_list,
        "hgis": hgis_matches.get(k, [])
    })

with open("tests/verify026_full.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("Wrote tests/verify026_full.json")
