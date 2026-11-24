import ast, csv, glob, json, os
with open("tests/c039_research.py", encoding="utf-8") as f:
    src = f.read()
INPUT = json.loads(src.split("INPUT = ")[1].split("\n\nBASE =")[0])

KEYS = {x["key"] for x in INPUT}
BY_KEY = {x["key"]: x for x in INPUT}

# 1. Check QUIPU chapter settlement JSONs for exact key matches
chap_hits = {}
for p in glob.glob("histmap/1.data_raw/population_regional/QUIPU/**/*.json", recursive=True):
    if "_shared" in p or "cache" in p.lower():
        continue
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    items = (d.get("settlements") if isinstance(d, dict) else (d if isinstance(d, list) else [])) or []
    if isinstance(items, dict):
        items = list(items.items())
    for it in items:
        if isinstance(it, tuple):
            k, v = it
            if k in KEYS and isinstance(v, dict):
                chap_hits[k] = {fk: fv for fk, fv in v.items() if fk != "population"}
                chap_hits[k]["_file"] = os.path.basename(p)
        elif isinstance(it, dict):
            k = it.get("key")
            if k in KEYS:
                chap_hits[k] = {fk: fv for fk, fv in it.items() if fk != "population"}
                chap_hits[k]["_file"] = os.path.basename(p)

# 2. Also scan CSV radiocarbon / site files in _shared/settlement_sources
csv_hits = {x["key"]: [] for x in INPUT}
BASE = "histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources"
for p in glob.glob(os.path.join(BASE, "*.csv")):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                lat = row.get("lat") or row.get("latitude") or row.get("Lat")
                lon = row.get("lon") or row.get("lng") or row.get("longitude") or row.get("Lon")
                if not lat or not lon: continue
                try:
                    flat, flon = float(lat), float(lon)
                except: continue
                for x in INPUT:
                    if abs(flat - x["ll"][0]) < 0.03 and abs(flon - x["ll"][1]) < 0.03:
                        r2 = {k: v for k, v in row.items() if v}
                        r2["_file"] = os.path.basename(p)
                        csv_hits[x["key"]].append(r2)
    except Exception as e:
        print("csv err", p, e)

# 3. Scan raw/nso_* JSONs for matches (Ecuador, Venezuela, Colombia, Bolivia, Argentina, Peru)
nso_hits = {x["key"]: [] for x in INPUT}
for p in glob.glob(os.path.join(BASE, "raw", "**", "*.json"), recursive=True):
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    items = d if isinstance(d, list) else (d.get("features") or d.get("settlements") or d.get("records") or [])
    if not isinstance(items, list): continue
    for s in items:
        if not isinstance(s, dict): continue
        props = s.get("properties", s)
        c = s.get("coords") or s.get("ll")
        if not c and "geometry" in s and s["geometry"]:
            gc = s["geometry"].get("coordinates")
            if gc and isinstance(gc, list) and len(gc) >= 2 and isinstance(gc[0], (int, float)):
                c = [gc[1], gc[0]]
        if not c:
            lat = props.get("lat") or props.get("latitude") or props.get("Y") or props.get("y")
            lon = props.get("lon") or props.get("lng") or props.get("longitude") or props.get("X") or props.get("x")
            if lat is not None and lon is not None: c = [lat, lon]
        if not c: continue
        try:
            flat, flon = float(c[0]), float(c[1])
        except: continue
        for x in INPUT:
            if abs(flat - x["ll"][0]) < 0.015 and abs(flon - x["ll"][1]) < 0.015:
                r2 = {k: v for k, v in props.items() if not isinstance(v, (dict, list)) and v is not None}
                r2["_file"] = os.path.basename(p)
                nso_hits[x["key"]].append(r2)

with open("tests/c039_deep.json", "w", encoding="utf-8") as f:
    json.dump({"chap_hits": chap_hits, "csv_hits": {k:v for k,v in csv_hits.items() if v}, "nso_hits": {k:v for k,v in nso_hits.items() if v}}, f, ensure_ascii=False, indent=2)

print("chap_hits:", len(chap_hits), "csv_hits:", sum(1 for v in csv_hits.values() if v), "nso_hits:", sum(1 for v in nso_hits.values() if v))
