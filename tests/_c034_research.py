import json, os, urllib.request, urllib.parse, concurrent.futures

INPUT_PATH = "tests/_c034_input.json"
OUT_PATH = "tests/_c034_research.json"

with open(INPUT_PATH, "r", encoding="utf-8") as f:
    items = json.load(f)

# Load local raw_setts and hgis_indias
base_dir = "histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources"
local_by_country = {}
for fname in os.listdir(base_dir):
    if fname.startswith("raw_setts_") and fname.endswith(".json"):
        with open(os.path.join(base_dir, fname), "r", encoding="utf-8") as f:
            data = json.load(f)
        rows = []
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list):
                    rows.extend([x for x in v if isinstance(x, dict)])
                elif isinstance(v, dict):
                    rows.append(v)
        elif isinstance(data, list):
            rows = [x for x in data if isinstance(x, dict)]
        local_by_country[fname] = rows

with open(os.path.join(base_dir, "hgis_indias_colonial_raw.json"), "r", encoding="utf-8") as f:
    hgis_raw = json.load(f)
hgis_rows = []
if isinstance(hgis_raw, dict):
    for k, v in hgis_raw.items():
        if isinstance(v, list):
            hgis_rows.extend([x for x in v if isinstance(x, dict)])
        elif isinstance(v, dict):
            hgis_rows.append(v)
elif isinstance(hgis_raw, list):
    hgis_rows = [x for x in hgis_raw if isinstance(x, dict)]

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SVEA-Toponymy-Research/1.0"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))

def wiki_lookup(item):
    lat, lng = item["ll"]
    name = item["n"]
    country = item["c"]
    res = {"key": item["key"], "es_geo": [], "es_search": [], "en_geo": [], "es_extracts": {}, "en_extracts": {}}
    # Geosearch es.wikipedia within 10km
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
        res["es_geo"] = fetch_json(u).get("query", {}).get("geosearch", [])
    except Exception as e:
        res["es_geo_err"] = str(e)
    # Search es.wikipedia by name + country
    try:
        q = urllib.parse.quote(f"{name} {country}")
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        res["es_search"] = [x["title"] for x in fetch_json(u).get("query", {}).get("search", [])]
    except Exception as e:
        res["es_search_err"] = str(e)
    # Collect titles to fetch full extract (first 3000 chars)
    titles = []
    for g in res["es_geo"][:2]:
        if g["title"] not in titles:
            titles.append(g["title"])
    for t in res["es_search"][:2]:
        if t not in titles:
            titles.append(t)
    if titles:
        try:
            t_param = urllib.parse.quote("|".join(titles))
            u = f"https://es.wikipedia.org/w/api.php?action=query&titles={t_param}&prop=extracts|coordinates&explaintext=1&exchars=4000&format=json"
            pages = fetch_json(u).get("query", {}).get("pages", {})
            for p in pages.values():
                if "title" in p and "extract" in p:
                    res["es_extracts"][p["title"]] = {
                        "extract": p["extract"][:3500],
                        "coords": p.get("coordinates", [])
                    }
        except Exception as e:
            res["es_ext_err"] = str(e)
    # Also check en.wikipedia geosearch if es gave nothing
    if not res["es_extracts"]:
        try:
            u = f"https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=3&format=json"
            res["en_geo"] = fetch_json(u).get("query", {}).get("geosearch", [])
            en_titles = [g["title"] for g in res["en_geo"][:2]]
            if en_titles:
                t_param = urllib.parse.quote("|".join(en_titles))
                u2 = f"https://en.wikipedia.org/w/api.php?action=query&titles={t_param}&prop=extracts|coordinates&explaintext=1&exchars=3000&format=json"
                pages = fetch_json(u2).get("query", {}).get("pages", {})
                for p in pages.values():
                    if "title" in p and "extract" in p:
                        res["en_extracts"][p["title"]] = p["extract"][:2500]
        except Exception as e:
            res["en_err"] = str(e)
    # Check local gazetteer near coords
    local_hits = []
    for fname, rows in local_by_country.items():
        for r in rows:
            rlat = r.get("lat") or (r.get("ll")[0] if isinstance(r.get("ll"), list) else None)
            rlng = r.get("lng") or r.get("lon") or (r.get("ll")[1] if isinstance(r.get("ll"), list) else None)
            if rlat is not None and rlng is not None:
                if abs(float(rlat) - lat) < 0.03 and abs(float(rlng) - lng) < 0.03:
                    local_hits.append({k: v for k, v in r.items() if k in ("name", "n", "key", "source", "type", "admin1", "admin2", "dept", "province", "municipality", "notes", "ey", "ly", "p", "pop", "year", "founded")})
    for r in hgis_rows:
        rlat = r.get("lat") or (r.get("ll")[0] if isinstance(r.get("ll"), list) else None)
        rlng = r.get("lng") or r.get("lon") or (r.get("ll")[1] if isinstance(r.get("ll"), list) else None)
        if rlat is not None and rlng is not None:
            if abs(float(rlat) - lat) < 0.05 and abs(float(rlng) - lng) < 0.05:
                local_hits.append({"hgis": True, **{k: v for k, v in r.items() if k in ("name", "nombre", "categoria", "partido", "provincia", "obispado", "audiencia", "year", "lat", "lng")}})
    res["local_hits"] = local_hits[:6]
    return res

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    for r in ex.map(wiki_lookup, items):
        results.append(r)

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=1)

# Also write 3 readable summary files
for p_idx in range(3):
    chunk = results[p_idx*30:(p_idx+1)*30]
    lines = []
    for idx, r in enumerate(chunk, start=p_idx*30):
        it = items[idx]
        lines.append(f"=== [{idx}] {it['key']} | n={it['n']} | c={it['c']} | r={it['r']} | ll={it['ll']} | ey={it['ey']} ly={it['ly']} p={it['p']} ===")
        if "ex" in it:
            lines.append(f"  ex: {it['ex']}")
        if "al" in it:
            lines.append(f"  al: {it['al']}")
        if r.get("local_hits"):
            lines.append(f"  LOCAL: {json.dumps(r['local_hits'], ensure_ascii=False)}")
        if r.get("es_geo"):
            lines.append(f"  ES_GEO: {[(g.get('title'), g.get('dist')) for g in r['es_geo']]}")
        if r.get("es_search"):
            lines.append(f"  ES_SEARCH: {r['es_search']}")
        for title, info in r.get("es_extracts", {}).items():
            txt = info["extract"].replace("\n", " ")[:1800]
            lines.append(f"  [ES: {title} | coords={info.get('coords')}]: {txt}")
        for title, txt in r.get("en_extracts", {}).items():
            txt2 = txt.replace("\n", " ")[:1500]
            lines.append(f"  [EN: {title}]: {txt2}")
        lines.append("")
    with open(f"tests/_c034_part{p_idx+1}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

print("Done:", len(results))
