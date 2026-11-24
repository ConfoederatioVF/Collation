import json, glob, os, math

with open("tests/research_c042.py", "r", encoding="utf-8") as f:
    src = f.read()
# Extract INPUT list safely
ns = {}
exec(src.split("print(f\"Total items")[0], ns)
INPUT = ns["INPUT"]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(min(1.0, a)))

# Index INPUT by rounded coords and name
by_name = {}
for item in INPUT:
    by_name.setdefault(item["n"].lower(), []).append(item)

local_hits = {item["key"]: [] for item in INPUT}

# 1. Scan *_settlements.json in QUIPU chapters
chap_files = glob.glob("histmap/1.data_raw/population_regional/QUIPU/*/*/*_settlements.json")
print(f"Scanning {len(chap_files)} chapter settlement files...")
for cf in chap_files:
    try:
        with open(cf, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        continue
    rows = data if isinstance(data, list) else data.get("settlements", data.get("rows", []))
    if isinstance(rows, dict):
        rows = list(rows.values())
    for row in rows:
        if not isinstance(row, dict):
            continue
        r_lat = row.get("lat") or (row.get("coords")[0] if isinstance(row.get("coords"), list) and len(row.get("coords")) == 2 else None)
        r_lng = row.get("lng") or row.get("lon") or (row.get("coords")[1] if isinstance(row.get("coords"), list) and len(row.get("coords")) == 2 else None)
        if r_lat is None or r_lng is None:
            continue
        r_lat, r_lng = float(r_lat), float(r_lng)
        for item in INPUT:
            ilat, ilng = item["ll"]
            if abs(r_lat - ilat) < 0.03 and abs(r_lng - ilng) < 0.03:
                d = haversine(ilat, ilng, r_lat, r_lng)
                if d < 2.0:
                    # Trim huge fields
                    summary = {k: v for k, v in row.items() if k in ("name", "canonical_name", "key", "lat", "lng", "lon", "source", "sources", "source_url", "foundation_year", "earliest_year", "latest_year", "period", "culture", "era", "notes", "admin1", "admin2", "departamento", "provincia", "municipio", "distrito", "other_names", "aliases", "description", "site_type", "year", "c14_bp", "cal_bc_ad")}
                    summary["_file"] = os.path.basename(cf)
                    summary["_dist_km"] = round(d, 3)
                    local_hits[item["key"]].append(summary)

# 2. Scan 0.raw_sites/*.json and documented_arch_sites.json
raw_files = glob.glob("histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/*.json")
raw_files.append("histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/config/documented_arch_sites.json")
print(f"Scanning {len(raw_files)} raw site files...")
for rf in raw_files:
    if not os.path.exists(rf): continue
    try:
        with open(rf, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        continue
    rows = data if isinstance(data, list) else data.get("sites", data.get("features", data.get("data", [])))
    if isinstance(rows, dict):
        rows = list(rows.values())
    for row in rows:
        if not isinstance(row, dict): continue
        props = row.get("properties", row)
        geom = row.get("geometry", {})
        r_lat = props.get("lat") or props.get("latitude") or props.get("y")
        r_lng = props.get("lng") or props.get("lon") or props.get("longitude") or props.get("x")
        if (r_lat is None or r_lng is None) and isinstance(geom, dict) and geom.get("type") == "Point":
            coords = geom.get("coordinates", [])
            if len(coords) >= 2:
                r_lng, r_lat = coords[0], coords[1]
        if r_lat is None or r_lng is None: continue
        try:
            r_lat, r_lng = float(r_lat), float(r_lng)
        except Exception:
            continue
        for item in INPUT:
            ilat, ilng = item["ll"]
            if abs(r_lat - ilat) < 0.02 and abs(r_lng - ilng) < 0.02:
                d = haversine(ilat, ilng, r_lat, r_lng)
                if d < 1.5:
                    summary = {k: v for k, v in props.items() if v is not None and str(v) != "" and len(str(v)) < 250}
                    summary["_file"] = os.path.basename(rf)
                    summary["_dist_km"] = round(d, 3)
                    local_hits[item["key"]].append(summary)

with open("tests/tmp_c042_local.json", "w", encoding="utf-8") as f:
    json.dump(local_hits, f, ensure_ascii=False, indent=2)

matched = sum(1 for v in local_hits.values() if v)
print(f"Matched {matched}/90 settlements in local QUIPU files.")
