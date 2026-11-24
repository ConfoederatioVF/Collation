import json, os, math

with open("tests/chunk054_input.json", encoding="utf-8") as f:
    inp = json.load(f)
with open("tests/chunk054_local.json", encoding="utf-8") as f:
    loc = json.load(f)
with open("tests/chunk054_wiki.json", encoding="utf-8") as f:
    wiki = {x["key"]: x for x in json.load(f)}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# Also scan raw_sites for exact coordinate matches (< 0.5 km) on items with no local match or arch items
arch_dir = "histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites"
arch_hits = {it["key"]: [] for it in inp}
for fn in os.listdir(arch_dir):
    if not fn.endswith(".json"):
        continue
    p = os.path.join(arch_dir, fn)
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        continue
    recs = data if isinstance(data, list) else data.get("features", data.get("sites", data.get("records", [])))
    if isinstance(data, dict) and not recs:
        recs = list(data.values())
    for rec in recs:
        if not isinstance(rec, dict):
            continue
        props = rec.get("properties", rec)
        geom = rec.get("geometry") or {}
        coords = geom.get("coordinates") if isinstance(geom, dict) else None
        rlat = props.get("lat") or props.get("latitude") or (coords[1] if isinstance(coords, list) and len(coords)>=2 else None)
        rlng = props.get("lng") or props.get("lon") or props.get("longitude") or (coords[0] if isinstance(coords, list) and len(coords)>=2 else None)
        if rlat is None or rlng is None:
            continue
        try:
            rlat, rlng = float(rlat), float(rlng)
        except Exception:
            continue
        for it in inp:
            d = haversine(it["ll"][0], it["ll"][1], rlat, rlng)
            if d < 0.35:
                arch_hits[it["key"]].append((fn, round(d, 2), {k: v for k, v in props.items() if k in ("name", "nombre", "sitio", "site_name", "period", "periodo", "cultura", "culture", "departamento", "provincia", "distrito", "municipio", "region", "fecha", "date", "c14", "bp", "start_year", "end_year") and v is not None}))

lines = []
for idx, it in enumerate(inp, 1):
    k = it["key"]
    lines.append(f'=== [{idx}] {k} | n={it["n"]} | c={it["c"]} | r={it["r"]} | ll={it["ll"]} | ey={it["ey"]} | ly={it["ly"]} | al={it.get("al")} | ex={it.get("ex")} ===')
    for m in loc.get(k, []):
        lines.append("  LOC: " + json.dumps(m, ensure_ascii=False))
    for a in arch_hits.get(k, []):
        lines.append("  ARCH: " + json.dumps(a, ensure_ascii=False))
    w = wiki.get(k, {})
    lines.append("  W_GEO: " + str(w.get("es_geo")) + " | W_SRCH: " + str(w.get("es_search")))
    for t, ex in w.get("extracts", {}).items():
        lines.append(f"  W_EX[{t}]: " + ex.replace("\n", " ")[:600])

with open("tests/chunk054_summary.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Summary lines:", len(lines))
