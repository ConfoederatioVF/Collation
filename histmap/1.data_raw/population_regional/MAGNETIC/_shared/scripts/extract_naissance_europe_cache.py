"""Extracts & caches time-sliced European historical polygons from SVEA `.naissance` archives
for Operation Viscount Project MAGNETIC (`_shared/subadmin_hgis/parsed/`).

Z-INDEX CONTRACT (STRICT):
  - `atlas_defacto_europe_cache.json` (from `saves/.cache/atlas_defacto/partition_*.ndjson`)
    is STRICTLY a lowest z-index (Priority 0) fallback ONLY, because it represents de facto
    dynastic holdings without feudatories.
  - `detailed_borders_europe_cache.json` (from `saves/archives/detailed_borders/*.naissance`
    and `saves/atlas_dejure.naissance`) provides higher-resolution feudatories & de jure states
    at middle z-index, still strictly below primary archival sub-administrative GIS layers.
"""

import glob
import json
import os

from shapely.geometry import mapping, shape
from shapely.validation import make_valid

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
PARSED_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC", "_shared", "subadmin_hgis", "parsed"
)
os.makedirs(PARSED_DIR, exist_ok=True)

TARGET_YEARS = [
  -500, -350, -200, 0, 100, 200, 300, 400,
  500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1347, 1400, 1492,
  1500, 1600, 1700, 1750, 1790, 1800, 1815, 1850, 1880, 1914, 1920, 1930, 1938
]

# Exact UF Date.isLeapYear / Date.getTimestamp implementation (minutes since 1 Jan 0000 00:00)
BC_LEAP = {-45, -42, -39, -36, -33, -30, -27, -24, -21, -18, -15, -12, -9}


def is_leap_year(yr):
  if yr in BC_LEAP:
    return True
  return (((yr % 4 == 0) and (yr % 100 != 0)) or (yr % 400 == 0)) and yr != 4


def year_to_ts(yr, month=6, day=15):
  mins = 0
  if yr > 0:
    for y in range(0, yr):
      mins += (366 if is_leap_year(y) else 365) * 1440
  elif yr < 0:
    for y in range(-1, yr - 1, -1):
      mins -= (366 if is_leap_year(y) else 365) * 1440
  mdays = [31, 29 if is_leap_year(yr) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  for m in range(1, month):
    mins += mdays[m - 1] * 1440
  mins += (day - 1) * 1440
  return mins


YEAR_TS = {y: year_to_ts(y, 6, 15) for y in TARGET_YEARS}


def clean_eu_geom(raw_g):
  if not isinstance(raw_g, dict):
    return None
  if "feature" in raw_g:
    raw_g = (raw_g.get("feature") or {}).get("geometry")
  if not isinstance(raw_g, dict) or raw_g.get("type") not in ("Polygon", "MultiPolygon"):
    return None
  try:
    g = shape(raw_g)
    if g.is_empty:
      return None
    minx, miny, maxx, maxy = g.bounds
    if maxx < -75.0 or minx > 46.0 or maxy < 26.0 or miny > 83.0:
      return None
    if not g.is_valid:
      g = make_valid(g)
      if g.geom_type == "GeometryCollection":
        polys = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon") and not p.is_empty]
        if not polys:
          return None
        from shapely.ops import unary_union
        g = unary_union(polys)
    if g.is_empty or g.area < 0.002:
      return None
    # Light simplify (0.01 deg ~ 1 km, far finer than 5' = 0.0833 deg) for fast JSON loading
    g = g.simplify(0.01, preserve_topology=True)
    if g.is_empty:
      return None
    return g
  except Exception:
    return None


def eval_entity_at_years(eid, ent, years):
  hist = ent.get("history") or {}
  if not hist:
    return {}
  h_items = []
  for tk, tv in hist.items():
    try:
      h_items.append((int(tk), tv))
    except Exception:
      pass
  if not h_items:
    return {}
  h_items.sort(key=lambda x: x[0])

  out = {}
  idx = 0
  n = len(h_items)
  cur_g = None
  cur_nm = ""
  cur_hidden = False
  for y in sorted(years):
    ts = YEAR_TS[y]
    while idx < n and h_items[idx][0] <= ts:
      tv = h_items[idx][1]
      if isinstance(tv, list):
        if len(tv) > 0:
          cur_g = tv[0]
          if cur_g is None or cur_g == "null":
            cur_g = None
        if len(tv) > 2 and isinstance(tv[2], dict):
          if tv[2].get("name"):
            cur_nm = str(tv[2]["name"]).replace("\n", " ").strip()
          cur_hidden = bool(tv[2].get("hidden", False))
      idx += 1
    if cur_g is not None and not cur_hidden:
      g = clean_eu_geom(cur_g)
      if g is not None:
        out[y] = {"id": str(eid), "name": cur_nm or f"Entity_{eid}", "geometry": mapping(g)}
  return out


def extract_atlas_defacto():
  print("[1] Extracting atlas_defacto Europe fallback cache (Priority 0 ONLY)...", flush=True)
  by_year = {str(y): [] for y in TARGET_YEARS}
  parts = sorted(glob.glob(os.path.join(SVEA_ROOT, "saves", ".cache", "atlas_defacto", "partition_*.ndjson")))
  n_ent = 0
  for p in parts:
    with open(p, "r", encoding="utf-8") as fh:
      for line in fh:
        s = line.strip().rstrip(",")
        if not s or not s.startswith('"'):
          continue
        try:
          obj = json.loads("{" + s + "}")
        except Exception:
          continue
        for k, v in obj.items():
          if not isinstance(v, dict) or v.get("class_name") != "GeometryPolygon":
            continue
          n_ent += 1
          res = eval_entity_at_years(k, v, TARGET_YEARS)
          for y, rec in res.items():
            by_year[str(y)].append(rec)
  out_p = os.path.join(PARSED_DIR, "atlas_defacto_europe_cache.json")
  with open(out_p, "w", encoding="utf-8") as fh:
    json.dump(by_year, fh)
  print(f"  Saved {out_p} ({n_ent} scanned):", {y: len(by_year[str(y)]) for y in (0, 200, 400, 600, 800, 1000, 1200, 1347, 1500, 1700, 1800, 1914, 1938)}, flush=True)


def extract_detailed_borders():
  print("[2] Extracting detailed_borders/*.naissance Europe feudatories & states...", flush=True)
  file_year_map = [
    ("0.476.1.1.naissance", [-500, -350, -200, 0, 100, 200, 300, 400]),
    ("1.1356.1.1.naissance", [500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1347]),
    ("2.1707.1.1.naissance", [1400, 1492, 1500, 1600, 1700]),
    ("3.1815.1.1.naissance", [1750, 1790, 1800]),
    ("4.1914.1.1.naissance", [1815, 1850, 1880]),
    ("5.1936.1.1.naissance", [1914, 1920, 1930]),
    ("6.1946.1.1.naissance", [1938]),
  ]
  by_year = {str(y): [] for y in TARGET_YEARS}
  db_dir = os.path.join(SVEA_ROOT, "saves", "archives", "detailed_borders")
  for fn, yrs in file_year_map:
    fp = os.path.join(db_dir, fn)
    if not os.path.isfile(fp):
      continue
    d = json.load(open(fp, "r", encoding="utf-8"))
    for k, v in d.items():
      if not isinstance(v, dict) or v.get("class_name") != "GeometryPolygon":
        continue
      res = eval_entity_at_years(k, v, yrs)
      for y, rec in res.items():
        by_year[str(y)].append(rec)
    print(f"  Parsed {fn}:", {y: len(by_year[str(y)]) for y in yrs}, flush=True)

  out_p = os.path.join(PARSED_DIR, "detailed_borders_europe_cache.json")
  with open(out_p, "w", encoding="utf-8") as fh:
    json.dump(by_year, fh)
  print(f"  Saved {out_p}", flush=True)


if __name__ == "__main__":
  extract_atlas_defacto()
  extract_detailed_borders()
