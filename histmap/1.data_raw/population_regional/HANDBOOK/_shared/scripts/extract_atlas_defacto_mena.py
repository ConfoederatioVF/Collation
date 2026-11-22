"""Extracts period-authentic MENA sovereign polity snapshots from `saves/.cache/atlas_defacto/partition_*.ndjson`
into `HANDBOOK/_shared/_gis_cache/atlas_defacto_mena/defacto_<year>.geojson`.

Used strictly as the LOWEST z-index sovereign fallback (z = 1) beneath higher-resolution historical
subadministrative divisions (AWMC Roman provinces, Al-Thurayya Islamic aqalim, Ottoman vilayets,
1897 Russian guberniyas, Egyptian mudiriyas, Mandate districts, and geoBoundaries ADM2/ADM1).
"""

import glob
import json
import os
import sys
import time

from shapely.geometry import box as sbox, mapping, shape

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CACHE_DIR = os.path.join(SVEA_ROOT, "saves", ".cache", "atlas_defacto")
OUT_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "HANDBOOK",
  "_shared", "_gis_cache", "atlas_defacto_mena"
)
os.makedirs(OUT_DIR, exist_ok=True)

MENA_BBOX = sbox(-19.0, 11.0, 76.5, 45.0)

# All HYDE overlapping years from -3000 to 1950 + decennial modern + key chapter anchor years
TARGET_YEARS = sorted(set(
  [-3000, -2500, -2000, -1800, -1300, -1000, -600, -539, -500, -330, -200, 0]
  + list(range(100, 1700, 100))
  + [117, 200, 632, 750, 850, 1150, 1250, 1350, 1520]
  + list(range(1700, 1951, 10))
  + [1881, 1914, 1918, 1922, 1932, 1936, 1945, 1948, 1956, 1960, 1962, 1970, 1975, 1980, 1990, 2000, 2010, 2020]
))


def is_leap(y):
  if -45 <= y <= 45:
    return (y % 4 == 0)
  return (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))


def year_to_ts(target_yr):
  """Exact Naissance timestamp (minutes from year 0 Jan 1) matching UF/js/date/date_conversion.js, evaluated at July 1."""
  mins = 0
  if target_yr >= 0:
    for y in range(0, target_yr):
      mins += (366 if is_leap(y) else 365) * 1440
  else:
    for y in range(-1, target_yr - 1, -1):
      mins -= (366 if is_leap(y) else 365) * 1440
  return mins + 182 * 1440


def quick_bbox_overlap(geom_dict):
  """Fast coarse bbox test against MENA (-19..76.5, 11..45) without constructing Shapely objects."""
  if not isinstance(geom_dict, dict):
    return False
  coords = geom_dict.get("coordinates")
  if not coords:
    return False
  gtype = geom_dict.get("type", "")
  # Sample vertices across rings
  rings = []
  if gtype == "Polygon":
    rings = [coords[0]] if coords else []
  elif gtype == "MultiPolygon":
    rings = [p[0] for p in coords if p]
  else:
    return False
  minx, miny, maxx, maxy = 999.0, 999.0, -999.0, -999.0
  for ring in rings:
    step = max(1, len(ring) // 24)
    for pt in ring[::step]:
      if isinstance(pt, (list, tuple)) and len(pt) >= 2:
        x, y = float(pt[0]), float(pt[1])
        if x < minx: minx = x
        if x > maxx: maxx = x
        if y < miny: miny = y
        if y > maxy: maxy = y
  return not (maxx < -19.0 or minx > 76.5 or maxy < 11.0 or miny > 45.0)


def extract_geom_dict(kf0):
  if not isinstance(kf0, dict):
    return None
  if "feature" in kf0 and isinstance(kf0["feature"], dict):
    return kf0["feature"].get("geometry")
  if "geometry" in kf0 and isinstance(kf0["geometry"], dict):
    return kf0["geometry"]
  if "type" in kf0 and "coordinates" in kf0:
    return kf0
  return None


def main():
  t0 = time.time()
  target_ts = {y: year_to_ts(y) for y in TARGET_YEARS}
  by_year = {y: [] for y in TARGET_YEARS}
  parts = sorted(glob.glob(os.path.join(CACHE_DIR, "partition_*.ndjson")))
  print(f"Scanning {len(parts)} atlas_defacto NDJSON partitions across {len(TARGET_YEARS)} target years...", flush=True)

  total_ents = 0
  mena_ents = 0
  for pi, ppath in enumerate(parts, 1):
    with open(ppath, "r", encoding="utf-8", errors="replace") as fh:
      for line in fh:
        s = line.strip()
        if not s:
          continue
        if s.endswith(","):
          s = s[:-1]
        if not s.startswith("{"):
          s = "{" + s + "}"
        try:
          obj = json.loads(s)
        except Exception:
          continue
        total_ents += 1
        val = next(iter(obj.values())) if len(obj) == 1 and isinstance(next(iter(obj.values())), dict) else obj
        if val.get("class_name") not in ("GeometryPolygon", "Polity", None):
          continue
        hist = val.get("history")
        if not isinstance(hist, dict) or not hist:
          continue

        # Parse timeline keyframes in chronological order
        ts_sorted = []
        for k_s in hist.keys():
          try:
            ts_sorted.append((int(float(k_s)), k_s))
          except Exception:
            continue
        if not ts_sorted:
          continue
        ts_sorted.sort()

        # Quick MENA filter across keyframes
        any_mena = False
        base_name = str(val.get("name") or "")
        for _, ks in ts_sorted:
          kf = hist[ks]
          if isinstance(kf, list) and kf:
            if len(kf) >= 3 and isinstance(kf[2], dict) and kf[2].get("name") and not base_name:
              base_name = str(kf[2]["name"])
            gd = extract_geom_dict(kf[0])
            if gd and quick_bbox_overlap(gd):
              any_mena = True
              break
        if not any_mena:
          continue
        mena_ents += 1

        # Walk keyframes once across all sorted target years (O(K + Y) sweep!)
        k_idx = 0
        n_k = len(ts_sorted)
        cur_gd = None
        cur_nm = base_name
        cur_props = {}
        hidden = False
        last_ts_val = ts_sorted[-1][0]
        last_kf = hist[ts_sorted[-1][1]]
        last_yr_approx = int(round(last_ts_val / 525949.2))
        last_ended = isinstance(last_kf, list) and len(last_kf) >= 1 and (
          last_kf[0] is None or (len(last_kf) >= 3 and isinstance(last_kf[2], dict) and last_kf[2].get("hidden") is True)
        )

        # Cache clipped shapely geometry per keyframe so unchanged polygons across decades aren't re-clipped!
        cached_geom_id = None
        cached_clipped = None

        for y in TARGET_YEARS:
          ty = target_ts[y]
          if ty < ts_sorted[0][0]:
            continue
          while k_idx < n_k and ts_sorted[k_idx][0] <= ty:
            kf = hist[ts_sorted[k_idx][1]]
            if isinstance(kf, list) and kf:
              if kf[0] is None:
                cur_gd = None
                cached_geom_id = None
                cached_clipped = None
              elif isinstance(kf[0], dict):
                gd_new = extract_geom_dict(kf[0])
                if gd_new is not None:
                  cur_gd = gd_new
                  hidden = False
                  cached_geom_id = None
                  cached_clipped = None
              if len(kf) >= 3 and isinstance(kf[2], dict):
                cur_props.update(kf[2])
                if kf[2].get("name"):
                  cur_nm = str(kf[2]["name"])
                if kf[2].get("hidden") is True:
                  hidden = True
                  cur_gd = None
            k_idx += 1

          if hidden or cur_gd is None:
            continue
          # Mirror PolitiesAtlasJoin ancient lifespan cutoff: unclosed pre-1750 entities stop +50y after last keyframe
          if ty > last_ts_val and not last_ended and last_yr_approx < 1750 and y > last_yr_approx + 50:
            continue
          if not quick_bbox_overlap(cur_gd):
            continue

          if cached_geom_id != id(cur_gd):
            cached_geom_id = id(cur_gd)
            try:
              g = shape(cur_gd).buffer(0)
              if not g.is_empty and g.intersects(MENA_BBOX):
                gc = g.intersection(MENA_BBOX).buffer(0)
                cached_clipped = gc if (not gc.is_empty and gc.area > 0.002) else None
              else:
                cached_clipped = None
            except Exception:
              cached_clipped = None

          if cached_clipped is not None:
            nm_out = cur_nm or cur_props.get("name") or f"Polity_{val.get('id', '')}"
            by_year[y].append({
              "type": "Feature",
              "properties": {
                "atlas_id": str(val.get("id", "")),
                "name": str(nm_out),
                "label": str(cur_props.get("label") or ""),
                "area_deg2": round(float(cached_clipped.area), 5),
              },
              "geometry": mapping(cached_clipped.simplify(0.015, preserve_topology=True)),
            })
    print(f"  [{pi}/{len(parts)}] scanned {os.path.basename(ppath)} ({time.time() - t0:.1f}s, {mena_ents:,} MENA entities)", flush=True)

  for y in TARGET_YEARS:
    feats = by_year[y]
    out_p = os.path.join(OUT_DIR, f"defacto_{y}.geojson")
    with open(out_p, "w", encoding="utf-8") as fh:
      json.dump({"type": "FeatureCollection", "year": y, "features": feats}, fh, ensure_ascii=False)
  print(f"DONE in {time.time() - t0:.1f}s! Wrote {len(TARGET_YEARS)} atlas_defacto MENA GeoJSONs to {OUT_DIR}", flush=True)
  for y in [-2000, -1000, -500, 100, 500, 750, 1000, 1200, 1500, 1600, 1700, 1800, 1850, 1900, 1920, 1940, 1950]:
    print(f"  defacto_{y:5d}.geojson: {len(by_year[y]):3d} polygons", flush=True)


if __name__ == "__main__":
  main()
