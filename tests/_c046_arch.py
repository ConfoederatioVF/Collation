import json, os, glob, math, csv

with open(r"f:\Active Projects\Project 1509 - SVEA\tests\_c046_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

def dist_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(min(1.0, math.sqrt(a)))

raw_sites_dir = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\QUIPU\_shared\sites_quipu_andes_cone\0.raw_sites"
hits = {it["key"]: [] for it in items}

for path in sorted(glob.glob(os.path.join(raw_sites_dir, "*"))):
    fn = os.path.basename(path)
    if fn.startswith("summary_"):
        continue
    if fn.endswith(".json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except:
            continue
        rows = d if isinstance(d, list) else (d.get("features") or d.get("sites") or d.get("records") or [])
        if isinstance(d, dict) and not rows:
            for v in d.values():
                if isinstance(v, list):
                    rows = v
                    break
        for row in rows:
            if not isinstance(row, dict):
                continue
            props = row.get("properties", row)
            geom = row.get("geometry") or {}
            coords = geom.get("coordinates") if isinstance(geom, dict) else None
            rlat = props.get("lat") or props.get("latitude") or props.get("y") or (coords[1] if isinstance(coords, list) and len(coords)>=2 else None)
            rlon = props.get("lon") or props.get("lng") or props.get("longitude") or props.get("x") or (coords[0] if isinstance(coords, list) and len(coords)>=2 else None)
            if rlat is None or rlon is None:
                continue
            try:
                rlat, rlon = float(rlat), float(rlon)
            except:
                continue
            for it in items:
                d_km = dist_km(it["ll"][0], it["ll"][1], rlat, rlon)
                if d_km < 0.8:
                    c = {k: v for k, v in props.items() if v not in (None, "", [])}
                    c["_src"] = fn
                    c["_d"] = round(d_km, 3)
                    hits[it["key"]].append(c)
    elif fn.endswith(".csv"):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rlat = row.get("lat") or row.get("latitude") or row.get("Lat")
                    rlon = row.get("lon") or row.get("lng") or row.get("longitude") or row.get("Lon")
                    if not rlat or not rlon:
                        continue
                    try:
                        rlat, rlon = float(rlat), float(rlon)
                    except:
                        continue
                    for it in items:
                        d_km = dist_km(it["ll"][0], it["ll"][1], rlat, rlon)
                        if d_km < 0.8:
                            c = {k: v for k, v in row.items() if v not in (None, "", [])}
                            c["_src"] = fn
                            c["_d"] = round(d_km, 3)
                            hits[it["key"]].append(c)
        except:
            pass

out = []
for it in items:
    if hits[it["key"]]:
        out.append(f'=== {it["key"]} (ey={it["ey"]}, ly={it["ly"]}) ===')
        for h in hits[it["key"]][:5]:
            out.append("  " + json.dumps(h, ensure_ascii=False)[:450])
with open(r"f:\Active Projects\Project 1509 - SVEA\tests\_c046_arch.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Arch hits:", sum(1 for v in hits.values() if v))
