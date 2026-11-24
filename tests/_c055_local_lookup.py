import json, glob

with open("tests/_c055_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

files = glob.glob("histmap/1.data_raw/population_regional/QUIPU/*/*/*_settlements.json")
hits = {}
for fn in files:
    data = json.load(open(fn, "r", encoding="utf-8"))
    if not isinstance(data, dict):
        continue
    # Index by key and also by approx coords
    for item in items:
        k = item["key"]
        if k in data:
            row = {kk: vv for kk, vv in data[k].items() if kk not in ("population", "pop", "population_history")}
            hits.setdefault(k, []).append({"file": fn.split("\\")[-1], "match": "key", "row": row})
        else:
            ilat, ilng = item["ll"]
            for dk, dv in data.items():
                if not isinstance(dv, dict):
                    continue
                coords = dv.get("coords") or dv.get("ll")
                lat = coords[0] if isinstance(coords, list) and len(coords) >= 2 else dv.get("lat")
                lng = coords[1] if isinstance(coords, list) and len(coords) >= 2 else dv.get("lng", dv.get("lon"))
                if lat is not None and lng is not None:
                    if abs(float(lat) - ilat) < 0.002 and abs(float(lng) - ilng) < 0.002:
                        row = {kk: vv for kk, vv in dv.items() if kk not in ("population", "pop", "population_history")}
                        hits.setdefault(k, []).append({"file": fn.split("\\")[-1], "match": f"coord:{dk}", "row": row})

with open("tests/_c055_local_hits.json", "w", encoding="utf-8") as f:
    json.dump(hits, f, ensure_ascii=False, indent=2)
print(f"Matched {len(hits)}/{len(items)} items locally")
