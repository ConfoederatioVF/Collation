"""Extracts & caches time-sliced South American (QUIPU) historical polygons from SVEA `.naissance`
archives and CShapes 2.0 for Operation Viscount Project QUIPU (`_shared/subadmin_hgis/parsed/`).

Z-INDEX CONTRACT (STRICT):
  - `atlas_defacto_quipu_cache.json` (from `saves/.cache/atlas_defacto/partition_*.ndjson`)
    is STRICTLY a lowest z-index (z = 1) fallback ONLY.
  - `atlas_dejure_quipu_cache.json` (from `saves/.cache/atlas_dejure/partition_*.ndjson`
    or `saves/atlas_dejure.naissance`) provides coastal-complete de jure polities.
  - `cshapes_quipu_cache.json` (from `saves/CShapes-2.0.geojson`) provides academic 1886-2019
    national borders across South America.
"""

import glob
import json
import os
from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
PARSED_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "QUIPU",
  "_shared", "subadmin_hgis", "parsed"
)
os.makedirs(PARSED_DIR, exist_ok=True)

TARGET_YEARS = [
  -1000, -500, 0, 200, 500, 800, 1000, 1200, 1400, 1450, 1500, 1525, 1532,
  1550, 1600, 1650, 1700, 1750, 1776, 1780, 1800, 1810, 1820, 1825, 1830,
  1850, 1875, 1883, 1890, 1900, 1910, 1920, 1930, 1940, 1950, 1970, 1990, 2010
]

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


def clean_sa_geom(raw_g):
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
    # QUIPU + South Atlantic bbox: lon [-95, -24], lat [-60, 15]
    if maxx < -95.0 or minx > -24.0 or maxy < -60.0 or miny > 15.0:
      return None
    if not g.is_valid:
      g = make_valid(g)
      if g.geom_type == "GeometryCollection":
        polys = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon") and not p.is_empty]
        if not polys:
          return None
        g = unary_union(polys)
    if g.is_empty or g.area < 0.0005:
      return None
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
          meta = tv[2]
          if "name" in meta and meta["name"]:
            cur_nm = str(meta["name"])
          if "hidden" in meta:
            cur_hidden = bool(meta["hidden"])
      idx += 1
    if cur_g and not cur_hidden:
      g = clean_sa_geom(cur_g)
      if g is not None:
        out[str(y)] = {
          "id": str(eid),
          "name": cur_nm or str(ent.get("name") or eid),
          "geometry": mapping(g),
        }
  return out


def extract_cache_dir(cache_subdir, out_name):
  cdir = os.path.join(SVEA_ROOT, "saves", ".cache", cache_subdir)
  ndjsons = sorted(glob.glob(os.path.join(cdir, "partition_*.ndjson")))
  by_year = {str(y): [] for y in TARGET_YEARS}
  if not ndjsons:
    print(f"[WARN] No partition_*.ndjson in {cdir}")
    return
  total_ent = 0
  sa_hits = 0
  for fp in ndjsons:
    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
      for line in f:
        s = line.strip().rstrip(",")
        if not s or not s.startswith('"'):
          continue
        try:
          obj = json.loads("{" + s + "}")
        except Exception:
          continue
        for eid, ent in obj.items():
          if not isinstance(ent, dict) or ent.get("class_name") != "GeometryPolygon":
            continue
          total_ent += 1
          res = eval_entity_at_years(eid, ent, TARGET_YEARS)
          if res:
            sa_hits += 1
            for yk, item in res.items():
              by_year[yk].append(item)
  out_path = os.path.join(PARSED_DIR, out_name)
  with open(out_path, "w", encoding="utf-8") as f:
    json.dump(by_year, f)
  counts = {y: len(v) for y, v in by_year.items() if len(v) > 0}
  print(f"[OK] {out_name}: scanned {total_ent} entities, {sa_hits} SA hits, populated years={len(counts)}")
  for k in ["1450", "1500", "1600", "1700", "1780", "1820", "1850", "1900", "1950"]:
    if k in counts:
      nms = [x["name"] for x in by_year[k][:6]]
      print(f"   {k}: {counts[k]} polygons ({', '.join(nms)})")


def extract_cshapes_sa():
  cs_path = os.path.join(SVEA_ROOT, "saves", "CShapes-2.0.geojson")
  if not os.path.exists(cs_path):
    print("[WARN] CShapes-2.0.geojson not found")
    return
  with open(cs_path, "r", encoding="utf-8") as f:
    gj = json.load(f)
  sa_names = {
    "Colombia", "Venezuela", "Ecuador", "Peru", "Bolivia", "Chile",
    "Argentina", "Uruguay", "Paraguay", "Brazil", "Panama", "Guyana", "Suriname"
  }
  feats = []
  for ft in gj.get("features", []):
    props = ft.get("properties") or {}
    cname = str(props.get("cntry_name") or "")
    if cname in sa_names:
      feats.append(ft)
  out_path = os.path.join(PARSED_DIR, "cshapes_quipu_cache.json")
  with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f)
  print(f"[OK] cshapes_quipu_cache.json: {len(feats)} South American CShapes 2.0 features extracted.")


if __name__ == "__main__":
  extract_cache_dir("atlas_dejure", "atlas_dejure_quipu_cache.json")
  extract_cache_dir("atlas_defacto", "atlas_defacto_quipu_cache.json")
  extract_cshapes_sa()
