import json, glob, os, csv

with open("tests/chunk31_input.json", "r", encoding="utf-8") as f:
  b31 = json.load(f)

target_keys = {x["key"]: x for x in b31}
matches = {k: [] for k in target_keys}

# 1. Search chapter settlement files (dict keyed by settlement key)
for p in glob.glob("histmap/1.data_raw/population_regional/QUIPU/*/*/*_settlements.json"):
  with open(p, "r", encoding="utf-8") as f:
    data = json.load(f)
  items = data.items() if isinstance(data, dict) else enumerate(data)
  for k, r in items:
    if not isinstance(r, dict):
      continue
    rk = r.get("key") or (k if isinstance(k, str) else None)
    coords = r.get("coords") or r.get("ll") or []
    lat = r.get("lat")
    lng = r.get("lng")
    if lat is None and isinstance(coords, list) and len(coords) >= 2:
      # Check if [lat, lng] or [lng, lat]
      lat, lng = coords[0], coords[1]
    for tk, tv in target_keys.items():
      hit = (rk == tk) or (rk == tk.split("_")[0] and tv["n"] in str(r.get("name", "")))
      if not hit and lat is not None and lng is not None:
        try:
          f1, f2 = float(lat), float(lng)
          if (abs(f1 - tv["ll"][0]) < 0.01 and abs(f2 - tv["ll"][1]) < 0.01) or (abs(f2 - tv["ll"][0]) < 0.01 and abs(f1 - tv["ll"][1]) < 0.01):
            hit = True
        except Exception:
          pass
      if hit:
        matches[tk].append({
          "chapter_file": os.path.basename(p),
          "key": rk,
          "data": {kk: r[kk] for kk in r if kk != "population"}
        })

# 2. Search settlement_sources & raw_sites JSONs (including nested dicts/lists)
extra_json = glob.glob("histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/*.json") + \
             glob.glob("histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/raw/*.json") + \
             glob.glob("histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/*.json")
for p in extra_json:
  try:
    with open(p, "r", encoding="utf-8") as f:
      data = json.load(f)
  except Exception:
    continue
  rows = data if isinstance(data, list) else (data.get("features") or data.get("sites") or data.get("settlements") or data.get("records") or data.get("data") or list(data.values()))
  if isinstance(rows, dict):
    rows = list(rows.values())
  for r in rows:
    if not isinstance(r, dict):
      continue
    props = r.get("properties", r)
    geom = r.get("geometry", {})
    lat = props.get("lat") or props.get("latitude") or props.get("y")
    lng = props.get("lng") or props.get("lon") or props.get("longitude") or props.get("x")
    if lat is None and isinstance(geom.get("coordinates"), list) and len(geom["coordinates"]) >= 2:
      lng, lat = geom["coordinates"][0], geom["coordinates"][1]
    if lat is None and isinstance(props.get("coords"), list) and len(props["coords"]) >= 2:
      lat, lng = props["coords"][0], props["coords"][1]
    if lat is None or lng is None:
      continue
    try:
      flat, flng = float(lat), float(lng)
    except Exception:
      continue
    for tk, tv in target_keys.items():
      if (abs(flat - tv["ll"][0]) < 0.005 and abs(flng - tv["ll"][1]) < 0.005) or (abs(flng - tv["ll"][0]) < 0.005 and abs(flat - tv["ll"][1]) < 0.005):
        matches[tk].append({
          "raw_file": os.path.basename(p),
          "props": {kk: props[kk] for kk in props if kk not in ("geometry", "polygon", "rings") and props[kk] not in (None, "", [])}
        })

with open("tests/chunk31_chapter_matches.json", "w", encoding="utf-8") as f:
  json.dump(matches, f, ensure_ascii=False, indent=2)

found = sum(1 for v in matches.values() if v)
print(f"Found matches for {found}/{len(target_keys)} keys")
missing = [k for k, v in matches.items() if not v]
print("Missing:", missing)
