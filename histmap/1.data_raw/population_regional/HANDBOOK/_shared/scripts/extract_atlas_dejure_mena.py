"""Extracts coastal-complete MENA polities from `saves/.cache/atlas_dejure/partition_*.ndjson`
(SVEA's coastal-complete re-encoding of Seshat Cliopatria) into
`HANDBOOK/_shared/_gis_cache/atlas_dejure_mena/dejure_<year>.geojson`.
"""

import glob
import json
import os

from shapely.geometry import box as sbox, mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CACHE_DIR = os.path.join(SVEA_ROOT, "saves", ".cache", "atlas_dejure")
OUT_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "HANDBOOK",
  "_shared", "_gis_cache", "atlas_dejure_mena"
)
os.makedirs(OUT_DIR, exist_ok=True)

MENA_BOX = sbox(-19.0, 11.0, 76.5, 45.0)
BC_LEAP = {-45, -42, -39, -36, -33, -30, -27, -24, -21, -18, -15, -12, -9}

TARGET_YEARS = sorted(set(
  [-3000, -2500, -2000, -1500, -1000, -600, -539, -500, -330, -200, 0]
  + list(range(100, 1700, 100))
  + [117, 200, 632, 750, 850, 1150, 1250, 1350, 1520]
  + list(range(1700, 1951, 10))
  + [1881, 1914, 1918, 1922, 1932, 1936, 1945, 1948, 1960, 1975, 1990, 2000, 2010]
))


def is_leap(yr):
  if yr in BC_LEAP:
    return True
  return (((yr % 4 == 0) and (yr % 100 != 0)) or (yr % 400 == 0)) and yr != 4


def year_to_ts(yr):
  mins = 0
  if yr > 0:
    for y in range(0, yr):
      mins += (366 if is_leap(y) else 365) * 1440
  elif yr < 0:
    for y in range(-1, yr - 1, -1):
      mins -= (366 if is_leap(y) else 365) * 1440
  return mins + 182 * 1440


YEAR_TS = {y: year_to_ts(y) for y in TARGET_YEARS}


def clean_mena_geom(raw_g):
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
    if maxx < -19.0 or minx > 76.5 or maxy < 11.0 or miny > 45.0:
      return None
    if not g.is_valid:
      g = make_valid(g)
      if g.geom_type == "GeometryCollection":
        polys = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon") and not p.is_empty]
        if not polys:
          return None
        g = unary_union(polys)
    gc = g.intersection(MENA_BOX)
    if gc.is_empty or gc.area < 0.005:
      return None
    return gc.simplify(0.01, preserve_topology=True)
  except Exception:
    return None


def main():
  by_year = {y: [] for y in TARGET_YEARS}
  parts = sorted(glob.glob(os.path.join(CACHE_DIR, "partition_*.ndjson")))
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
        for eid, ent in obj.items():
          if not isinstance(ent, dict) or ent.get("class_name") != "GeometryPolygon":
            continue
          n_ent += 1
          hist = ent.get("history") or {}
          h_items = []
          for tk, tv in hist.items():
            try:
              h_items.append((int(tk), tv))
            except Exception:
              pass
          if not h_items:
            continue
          h_items.sort(key=lambda x: x[0])
          idx = 0
          n = len(h_items)
          cur_g = None
          cur_nm = str((ent.get("metadata") or {}).get("name") or "")
          cur_hidden = False
          for y in TARGET_YEARS:
            ts = YEAR_TS[y]
            while idx < n and h_items[idx][0] <= ts:
              tv = h_items[idx][1]
              if isinstance(tv, list):
                if len(tv) > 0:
                  cur_g = None if (tv[0] is None or tv[0] == "null") else tv[0]
                if len(tv) > 2 and isinstance(tv[2], dict):
                  if tv[2].get("name"):
                    cur_nm = str(tv[2]["name"]).replace("\n", " ").strip()
                  cur_hidden = bool(tv[2].get("hidden", False))
              idx += 1
            if cur_g is not None and not cur_hidden:
              gc = clean_mena_geom(cur_g)
              if gc is not None and not gc.is_empty:
                by_year[y].append({
                  "type": "Feature",
                  "properties": {"id": str(eid), "name": cur_nm or f"DeJure_{eid}", "year": y},
                  "geometry": mapping(gc),
                })

  for y, feats in by_year.items():
    out_p = os.path.join(OUT_DIR, f"dejure_{y}.geojson")
    with open(out_p, "w", encoding="utf-8") as fh:
      json.dump({"type": "FeatureCollection", "features": feats}, fh)
  print(f"Extracted {len(by_year)} coastal-complete atlas_dejure MENA snapshots (scanned {n_ent} entities):",
        {y: len(by_year[y]) for y in (-1000, 200, 750, 1000, 1200, 1500, 1700, 1880, 1914, 1930)}, flush=True)


if __name__ == "__main__":
  main()
