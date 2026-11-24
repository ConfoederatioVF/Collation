import json, os, math

with open("tests/chunk054_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

matches = {it["key"]: [] for it in items}

# 1. hgis_indias_colonial_raw.json
hgis_path = "histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/hgis_indias_colonial_raw.json"
with open(hgis_path, "r", encoding="utf-8") as f:
    hdata = json.load(f)["settlements"]
for k, rec in hdata.items():
    coords = rec.get("coords")
    if not coords or len(coords) != 2:
        continue
    rlat, rlng = float(coords[0]), float(coords[1])
    for it in items:
        d = haversine(it["ll"][0], it["ll"][1], rlat, rlng)
        if d < 5.0:
            matches[it["key"]].append(("hgis_indias", round(d, 2), {k2: rec.get(k2) for k2 in ("name", "modern_name", "variants", "colonial_province", "colonial_partido", "categoria", "start_year", "end_year", "observaciones") if rec.get(k2)}))

# 2. raw_setts_*.json
src_dir = "histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources"
for fn in os.listdir(src_dir):
    if fn.startswith("raw_setts_") and fn.endswith(".json"):
        with open(os.path.join(src_dir, fn), "r", encoding="utf-8") as f:
            d = json.load(f)
        recs = d.get("settlements", d)
        it_list = recs.values() if isinstance(recs, dict) else recs
        for rec in it_list:
            if not isinstance(rec, dict):
                continue
            coords = rec.get("coords") or rec.get("ll")
            if not coords or len(coords) != 2:
                continue
            rlat, rlng = float(coords[0]), float(coords[1])
            for it in items:
                d_km = haversine(it["ll"][0], it["ll"][1], rlat, rlng)
                if d_km < 1.0:
                    keep = {k2: rec.get(k2) for k2 in ("name", "other_names", "admin1", "admin2", "coord_source", "sources", "category", "notes") if rec.get(k2)}
                    matches[it["key"]].append((fn, round(d_km, 2), keep))

# 3. documented_arch_sites.json
arch_p = "histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/config/documented_arch_sites.json"
if os.path.exists(arch_p):
    with open(arch_p, "r", encoding="utf-8") as f:
        adata = json.load(f)
    recs = adata.get("sites", adata) if isinstance(adata, dict) else adata
    if isinstance(recs, dict):
        recs = recs.values()
    for rec in recs:
        if not isinstance(rec, dict):
            continue
        rlat = rec.get("lat") or (rec.get("coords")[0] if isinstance(rec.get("coords"), list) else None)
        rlng = rec.get("lng") or rec.get("lon") or (rec.get("coords")[1] if isinstance(rec.get("coords"), list) else None)
        if rlat is None or rlng is None:
            continue
        for it in items:
            d_km = haversine(it["ll"][0], it["ll"][1], float(rlat), float(rlng))
            if d_km < 1.0:
                matches[it["key"]].append(("documented_arch", round(d_km, 2), {k2: rec.get(k2) for k2 in rec if k2 not in ("geometry",)}))

with open("tests/chunk054_local.json", "w", encoding="utf-8") as f:
    json.dump(matches, f, ensure_ascii=False, indent=2)

print("Non-empty matches:", sum(1 for v in matches.values() if v), "/", len(items))
