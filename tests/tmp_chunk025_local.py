import json, math, os, glob

with open("tests/tmp_chunk025_wiki.py", "r", encoding="utf-8") as f:
  pass

# Read INPUT from tmp_chunk025_wiki.py
import sys
sys.path.insert(0, "tests")
from tmp_chunk025_wiki import INPUT, haversine

def extract_coords(obj):
  if isinstance(obj, dict):
    lat = obj.get("lat") or obj.get("latitude") or obj.get("y")
    lng = obj.get("lng") or obj.get("lon") or obj.get("longitude") or obj.get("x")
    if lat is not None and lng is not None:
      try:
        return float(lat), float(lng)
      except:
        pass
    ll = obj.get("ll") or obj.get("coords")
    if isinstance(ll, list) and len(ll) >= 2:
      try:
        a, b = float(ll[0]), float(ll[1])
        # check if [lat, lng] or [lng, lat]
        if -60 <= a <= 20 and -90 <= b <= -30:
          return a, b
        if -60 <= b <= 20 and -90 <= a <= -30:
          return b, a
      except:
        pass
  return None

matches = {it["key"]: [] for it in INPUT}

files = glob.glob("histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/*.json")
files += glob.glob("histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/*.json")

for fp in files:
  fn = os.path.basename(fp)
  try:
    with open(fp, "r", encoding="utf-8") as f:
      data = json.load(f)
  except Exception as e:
    continue
  rows = []
  if isinstance(data, list):
    rows = data
  elif isinstance(data, dict):
    for k in ["features", "sites", "records", "settlements", "data", "rows"]:
      if isinstance(data.get(k), list):
        rows = data[k]
        break
    if not rows:
      # maybe dict of dicts
      vals = list(data.values())
      if vals and isinstance(vals[0], dict):
        rows = vals
  for row in rows:
    if not isinstance(row, dict):
      continue
    props = row.get("properties", row)
    if row.get("geometry") and isinstance(row["geometry"], dict) and row["geometry"].get("type") == "Point":
      coords = row["geometry"].get("coordinates", [])
      if len(coords) >= 2:
        try:
          rlat, rlng = float(coords[1]), float(coords[0])
        except:
          rlat, rlng = None, None
      else:
        rlat, rlng = None, None
    else:
      c = extract_coords(props) or extract_coords(row)
      rlat, rlng = c if c else (None, None)
    if rlat is None:
      continue
    for it in INPUT:
      ilat, ilng = it["ll"]
      if abs(ilat - rlat) < 0.05 and abs(ilng - rlng) < 0.05:
        d = haversine(ilat, ilng, rlat, rlng)
        if d < 3.0:
          # compact summary
          slim = {k: v for k, v in props.items() if k not in ("geometry", "polygon", "points") and len(str(v)) < 300}
          matches[it["key"]].append({"file": fn, "dist_km": round(d, 3), "data": slim})

with open("tests/tmp_chunk025_local.json", "w", encoding="utf-8") as f:
  json.dump(matches, f, ensure_ascii=False, indent=2)

found = sum(1 for v in matches.values() if v)
print(f"Matched {found}/{len(INPUT)} items in local raw sources.")
