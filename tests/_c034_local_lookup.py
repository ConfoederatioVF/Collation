import json, os, glob

with open("tests/_c034_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)

base_dir = "histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources"
raw_dicts = {}
for fname in os.listdir(base_dir):
    if fname.startswith("raw_setts_") and fname.endswith(".json"):
        with open(os.path.join(base_dir, fname), "r", encoding="utf-8") as f:
            d = json.load(f)
        raw_dicts[fname] = d.get("settlements", {})

with open(os.path.join(base_dir, "hgis_indias_colonial_raw.json"), "r", encoding="utf-8") as f:
    hgis_setts = json.load(f).get("settlements", {})

# Also check chapter gazetteer json5/json files if any exist
chapter_gaz_files = glob.glob("histmap/1.data_raw/population_regional/QUIPU/*/*/*gazetteer*.json*")

# Index raw_dicts by key and list for coord search
all_raw_by_key = {}
all_raw_list = []
for fname, sdict in raw_dicts.items():
    if isinstance(sdict, dict):
        for k, v in sdict.items():
            if isinstance(v, dict):
                v["_file"] = fname
                v["_key"] = k
                all_raw_by_key[k] = v
                all_raw_list.append(v)

hgis_list = [v for v in hgis_setts.values() if isinstance(v, dict)]

# Index arch sites by coord
arch_files = glob.glob("histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/*.json")
arch_hits_map = {it["key"]: [] for it in items}
target_coords = [(it["key"], it["ll"][0], it["ll"][1]) for it in items]

for af in arch_files:
    bname = os.path.basename(af)
    if bname.startswith("summary_"):
        continue
    try:
        with open(af, "r", encoding="utf-8") as f:
            ad = json.load(f)
    except Exception:
        continue
    rows = []
    if isinstance(ad, list):
        rows = ad
    elif isinstance(ad, dict):
        for v in ad.values():
            if isinstance(v, list):
                rows.extend(v)
            elif isinstance(v, dict) and ("lat" in v or "coords" in v or "ll" in v):
                rows.append(v)
    for r in rows:
        if not isinstance(r, dict):
            continue
        rlat = r.get("lat") or r.get("latitude") or (r["coords"][0] if isinstance(r.get("coords"), list) and len(r["coords"])>=2 else None) or (r["ll"][0] if isinstance(r.get("ll"), list) and len(r["ll"])>=2 else None)
        rlng = r.get("lng") or r.get("lon") or r.get("longitude") or (r["coords"][1] if isinstance(r.get("coords"), list) and len(r["coords"])>=2 else None) or (r["ll"][1] if isinstance(r.get("ll"), list) and len(r["ll"])>=2 else None)
        if rlat is None or rlng is None:
            continue
        try:
            rlat, rlng = float(rlat), float(rlng)
        except Exception:
            continue
        for key, tlat, tlng in target_coords:
            if abs(rlat - tlat) < 0.015 and abs(rlng - tlng) < 0.015:
                slim = {k: v for k, v in r.items() if k in ("name", "site_name", "nombre", "sitio", "culture", "cultura", "period", "periodo", "department", "departamento", "province", "provincia", "municipality", "municipio", "distrito", "date_bp", "cal_bc_ad", "ey", "ly", "type", "categoria", "notes", "source", "description")}
                slim["_src"] = bname
                arch_hits_map[key].append(slim)

out = []
for it in items:
    key = it["key"]
    lat, lng = it["ll"]
    rec = {"key": key, "n": it["n"], "c": it["c"], "r": it["r"], "ll": it["ll"], "ey": it["ey"], "ly": it["ly"]}
    if key in all_raw_by_key:
        r = all_raw_by_key[key]
        rec["raw_exact"] = {k: v for k, v in r.items() if k != "population"}
    # Also coord hits in raw
    coord_raw = []
    for r in all_raw_list:
        c = r.get("coords")
        if isinstance(c, list) and len(c) >= 2:
            if abs(float(c[0]) - lat) < 0.02 and abs(float(c[1]) - lng) < 0.02 and r.get("_key") != key:
                coord_raw.append({k: v for k, v in r.items() if k in ("_key", "name", "other_names", "admin1", "admin2", "gl_category", "sources", "coords")})
    if coord_raw:
        rec["raw_near"] = coord_raw[:4]
    # HGIS coord hits
    hgis_near = []
    for r in hgis_list:
        c = r.get("coords")
        if isinstance(c, list) and len(c) >= 2:
            if abs(float(c[0]) - lat) < 0.04 and abs(float(c[1]) - lng) < 0.04:
                hgis_near.append({k: v for k, v in r.items() if k in ("gz_id", "name", "modern_name", "variants", "colonial_audiencia", "colonial_province", "colonial_partido", "categoria", "start_year", "coords")})
    if hgis_near:
        rec["hgis_near"] = hgis_near[:4]
    if arch_hits_map[key]:
        rec["arch_hits"] = arch_hits_map[key][:5]
    out.append(rec)

with open("tests/_c034_local.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print("Local hits:", sum(1 for x in out if "raw_exact" in x or "raw_near" in x or "hgis_near" in x or "arch_hits" in x), "/ 90")
print("Chapter gaz files:", chapter_gaz_files)
