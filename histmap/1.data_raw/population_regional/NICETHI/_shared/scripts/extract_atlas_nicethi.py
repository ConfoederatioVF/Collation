"""Extracts coastal-complete Sub-Saharan Africa & Western Indian Ocean polities from
`saves/.cache/atlas_dejure/partition_*.ndjson` (SVEA's coastal-complete re-encoding of Cliopatria)
and lowest-fallback (`z = 1`) polygons from `saves/.cache/atlas_defacto/partition_*.ndjson`
into `NICETHI/_shared/_gis_cache/atlas_dejure_nicethi/` and `atlas_defacto_nicethi/`.
"""

import glob
import json
import os
import sys

from shapely.geometry import box as sbox, mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
NICETHI_GIS = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "NICETHI",
  "_shared", "_gis_cache"
)
AFRICA_BOX = sbox(-27.0, -41.0, 64.0, 28.0)
BC_LEAP = {-45, -42, -39, -36, -33, -30, -27, -24, -21, -18, -15, -12, -9}

TARGET_YEARS = sorted(set(
  [-2500, -2000, -1500, -1000, -500, 0]
  + list(range(100, 1700, 100))
  + [350, 550, 750, 1050, 1250, 1325, 1450, 1500, 1550, 1650]
  + list(range(1700, 1951, 10))
  + [1821, 1885, 1898, 1902, 1914, 1920, 1938, 1945, 1956, 1960, 1963, 1975, 1980, 1990, 1993, 2000, 2011, 2020]
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


def clean_africa_geom(raw_g):
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
    if maxx < -27.0 or minx > 64.0 or maxy < -41.0 or miny > 28.0:
      return None
    if not g.is_valid:
      g = make_valid(g)
      if g.geom_type == "GeometryCollection":
        polys = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon") and not p.is_empty]
        if not polys:
          return None
        g = unary_union(polys)
    gc = g.intersection(AFRICA_BOX)
    if gc.is_empty or gc.area < 0.002:
      return None
    return gc.simplify(0.01, preserve_topology=True)
  except Exception:
    return None


def extract_layer(cache_name, out_subdir, prefix):
  cache_dir = os.path.join(SVEA_ROOT, "saves", ".cache", cache_name)
  out_dir = os.path.join(NICETHI_GIS, out_subdir)
  os.makedirs(out_dir, exist_ok=True)
  by_year = {y: [] for y in TARGET_YEARS}
  parts = sorted(glob.glob(os.path.join(cache_dir, "partition_*.ndjson")))
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
              cg = clean_africa_geom(cur_g)
              if cg is not None:
                by_year[y].append({
                  "type": "Feature",
                  "properties": {"id": eid, "name": cur_nm or eid, "year": y, "layer": cache_name},
                  "geometry": mapping(cg)
                })
  total_written = 0
  for y, feats in by_year.items():
    out_p = os.path.join(out_dir, f"{prefix}_{y}.geojson")
    with open(out_p, "w", encoding="utf-8") as fh:
      json.dump({"type": "FeatureCollection", "features": feats}, fh)
    total_written += len(feats)
  print(f"[{cache_name}] entities_scanned={n_ent}, snapshots={len(by_year)}, total_features={total_written}")


def main():
  extract_layer("atlas_dejure", "atlas_dejure_nicethi", "dejure")
  extract_layer("atlas_defacto", "atlas_defacto_nicethi", "defacto")


if __name__ == "__main__":
  main()
