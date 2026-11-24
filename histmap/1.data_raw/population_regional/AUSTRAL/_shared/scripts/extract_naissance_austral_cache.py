"""Extracts & caches time-sliced Oceania (Project AUSTRAL) historical polygons from local SVEA
`.naissance` caches and `CShapes-2.0.geojson` into `_shared/subadmin_hgis/parsed/`.

Z-INDEX CONTRACT (STRICT):
  - `atlas_defacto_austral_cache.json` (from `saves/.cache/atlas_defacto/partition_*.ndjson`)
    is STRICTLY tagged `z_priority: 1` (lowest fallback ONLY), because it represents de facto
    dynastic/imperial holdings without sub-administrative feudatories.
  - `atlas_dejure_austral_cache.json` (from `saves/.cache/atlas_dejure/partition_*.ndjson`)
    provides coastal-complete de jure historical polities at middle z-index (`z_priority: 2`),
    still strictly below primary archival/OHM sub-administrative HGIS layers.
  - `cshapes_austral_cache.json` (from `saves/CShapes-2.0.geojson`) provides colonial and
    post-colonial polities across 1886-2019 (plus 2020 sampled from 2019 end-state) at
    `z_priority: 3` (still below primary census/OHM sub-administrative boundaries).

ZERO BANNED SOURCES:
  - Strictly excludes banned videogame maps and non-sanctioned basemap archives.

SPATIAL EXCLUSION CONTRACT (ZERO OVERLAP WITH MANDALA, CENTAUR, CASTLE, JADE, JAGUAR):
  - Includes Oceania (`lon >= 110.0` OR `lon <= -105.0`, `lat in [-56.0, 25.0]`).
  - Strictly excludes:
    * CENTAUR Hawai'i (`lat 18..25, lon -162..-154` + NW Hawaiian Islands `lat 22..25, lon -179..-162`)
    * CENTAUR American Samoa (`lat -15..-11, lon -171.25..-168.0`, preserving Independent Samoa Upolu <= -171.438W)
    * MANDALA & East Asia west of 129.5E north of -11.0S (Timor/Roti/Savu reach -10.96S; NW Australia west of 129.5E is <= -12.2S)
    * MANDALA Maluku islands east of 129.5E derived directly from `mandala_domain_mask.png`
      (East Seram, Gorom/Watubela, Babar/Tanimbar, Kai, Aru, Gebe up to 134.875E)
    * CASTLE Bonin/Volcano/Minamitorishima islands (`lat 21..25, lon 129.5..160.0`; Northern Marianas end at 20.56N)
    * JAGUAR Baja California / Revillagigedo / Mexico (`lat 15..25, lon -116..-105`)
"""

import glob
import json
import os
import sys

import numpy as np
from PIL import Image
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
PARSED_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "_shared", "subadmin_hgis", "parsed"
)
MANDALA_MASK_PNG = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MANDALA", "_shared",
  "sites_mandala_southeast_asia", "config", "mandala_domain_mask.png"
)
os.makedirs(PARSED_DIR, exist_ok=True)

# Canonical HYDE overlapping windows (-10000 to 1950)
HYDE_YEARS = (
  list(range(-10000, 0, 1000))
  + list(range(0, 1701, 100))
  + list(range(1710, 1951, 10))
)

# CShapes 2.0 (1886-2019) decennial + key AUSTRAL constitutional splice years + 2020 (from 2019 end-state)
CSHAPES_YEARS = [
  1886, 1890, 1900, 1901, 1907, 1910, 1920, 1930, 1940,
  1949, 1950, 1960, 1962, 1970, 1975, 1980, 1990, 2000, 2010, 2019, 2020
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


YEAR_TS = {y: year_to_ts(y, 6, 15) for y in HYDE_YEARS}


def build_austral_keep_region():
  """Builds exact Shapely AUSTRAL inclusion geometry subtracting MANDALA, CENTAUR, CASTLE, JAGUAR."""
  base = unary_union([
    box(110.0, -56.0, 180.0, 25.0),
    box(-180.0, -56.0, -105.0, 25.0),
  ])

  exclusions = [
    # CENTAUR Hawai'i (main islands + NW Hawaiian Islands + Palmyra Atoll)
    box(-162.0, 18.0, -154.0, 25.0),
    box(-179.0, 22.0, -162.0, 25.0),
    box(-162.25, 5.7, -161.9, 6.05),
    # CENTAUR American Samoa (Tutuila/Manu'a/Swains >= -171.087W; Independent Samoa Upolu <= -171.438W)
    box(-171.25, -15.0, -168.0, -11.0),
    # MANDALA / JADE / CASTLE west of 129.5E north of -11.3S (covers Timor/Roti down to -11.08S; Ashmore is -12.2S)
    box(110.0, -11.3, 129.5, 25.0),
    # MANDALA Maluku islands east of 129.5E (exact archipelago boxes matching mandala_domain_mask.png,
    # keeping Raja Ampat / Misool / Bird's Head / Onin / Bomberai West Papua cleanly inside AUSTRAL)
    box(129.4, -0.35, 129.75, 0.25),   # Gebe (North Maluku)
    box(129.4, -4.8, 131.7, -2.65),    # East Seram, Gorom, Watubela
    box(129.4, -8.8, 132.25, -6.5),    # Babar, Leti, Sermata, Tanimbar
    box(132.1, -6.3, 133.45, -5.05),   # Kai Islands
    box(133.8, -7.25, 135.2, -5.15),   # Aru Islands
    # CASTLE Japan Bonin / Volcano / Minamitorishima north of Northern Marianas (20.56N)
    box(129.5, 21.0, 160.0, 25.0),
    # JAGUAR Mexico / Baja California / Revillagigedo + uninhabited Clipperton Atoll
    box(-116.0, 15.0, -105.0, 25.0),
    box(-110.0, 9.5, -108.5, 11.0),
  ]

  # Also union exact MANDALA eastern Maluku pixels (>= 129.45E) from mandala_domain_mask.png
  if os.path.isfile(MANDALA_MASK_PNG):
    arr = np.array(Image.open(MANDALA_MASK_PNG))
    mask = (arr[:, :, 3] > 0) & ((arr[:, :, 0] > 0) | (arr[:, :, 1] > 0) | (arr[:, :, 2] > 0))
    h, w = mask.shape
    ys, xs = np.where(mask)
    lons = -180.0 + (xs + 0.5) * (360.0 / w)
    lats = 90.0 - (ys + 0.5) * (180.0 / h)
    east = lons >= 129.45
    dx = 0.5 * (360.0 / w) + 0.08
    dy = 0.5 * (180.0 / h) + 0.08
    px_boxes = [box(lo - dx, la - dy, lo + dx, la + dy) for lo, la in zip(lons[east], lats[east])]
    if px_boxes:
      exclusions.append(unary_union(px_boxes))

  return base.difference(unary_union(exclusions))


AUSTRAL_KEEP_REGION = build_austral_keep_region()


def fast_coords_touch_austral(coords):
  """Fast recursive pre-filter on raw GeoJSON coordinate arrays before Shapely construction."""
  if not coords:
    return False
  first = coords[0]
  if isinstance(first, (int, float)):
    lon = float(coords[0])
    lat = float(coords[1])
    if lat < -56.0 or lat > 25.0:
      return False
    if -105.0 < lon < 110.0:
      return False
    # Fast reject inside MANDALA/East Asia main box
    if 110.0 <= lon <= 129.5 and lat >= -11.0:
      return False
    # Fast reject inside Mexico/Baja box
    if -116.0 <= lon <= -105.0 and lat >= 15.0:
      return False
    # Fast reject inside Hawai'i box
    if -162.0 <= lon <= -154.0 and lat >= 18.0:
      return False
    return True
  for item in coords:
    if fast_coords_touch_austral(item):
      return True
  return False


def unwrap_raw_geom(raw_g):
  if not isinstance(raw_g, dict):
    return None
  if "feature" in raw_g:
    raw_g = (raw_g.get("feature") or {}).get("geometry")
  if not isinstance(raw_g, dict) or raw_g.get("type") not in ("Polygon", "MultiPolygon"):
    return None
  return raw_g


def extract_polygonal(geom):
  if geom is None or geom.is_empty:
    return None
  if geom.geom_type in ("Polygon", "MultiPolygon"):
    return geom
  if geom.geom_type == "GeometryCollection":
    polys = [p for p in geom.geoms if p.geom_type in ("Polygon", "MultiPolygon") and not p.is_empty]
    if not polys:
      return None
    return unary_union(polys)
  return None


def clean_austral_geom(raw_g):
  raw_g = unwrap_raw_geom(raw_g)
  if raw_g is None:
    return None
  coords = raw_g.get("coordinates")
  if not coords or not fast_coords_touch_austral(coords):
    return None
  try:
    g = shape(raw_g)
    if g.is_empty:
      return None
    if not g.is_valid:
      g = make_valid(g)
      g = extract_polygonal(g)
      if g is None or g.is_empty:
        return None
    clipped = g.intersection(AUSTRAL_KEEP_REGION)
    clipped = extract_polygonal(clipped)
    if clipped is None or clipped.is_empty:
      return None
    # Keep small Pacific islands down to ~6 km2 (0.0005 deg2)
    if clipped.area < 0.0005:
      return None
    clipped = clipped.simplify(0.005, preserve_topology=True)
    clipped = extract_polygonal(clipped)
    if clipped is None or clipped.is_empty or clipped.area < 0.0005:
      return None
    return clipped
  except Exception:
    return None


def entity_can_touch_austral(ent):
  hist = ent.get("history") or {}
  for tv in hist.values():
    if isinstance(tv, list) and len(tv) > 0:
      raw_g = unwrap_raw_geom(tv[0])
      if raw_g is not None and fast_coords_touch_austral(raw_g.get("coordinates")):
        return True
  return False


def eval_entity_at_years(eid, ent, years, z_priority, source_tag, role_tag):
  hist = ent.get("history") or {}
  if not hist or not entity_can_touch_austral(ent):
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
  geom_cache = {}
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
      g_id = id(cur_g)
      if g_id not in geom_cache:
        g_clean = clean_austral_geom(cur_g)
        geom_cache[g_id] = (mapping(g_clean), [round(v, 4) for v in g_clean.bounds]) if g_clean is not None else None
      cached = geom_cache[g_id]
      if cached is not None:
        g_map, g_bbox = cached
        out[y] = {
          "id": str(eid),
          "name": cur_nm or f"Entity_{eid}",
          "source": source_tag,
          "z_priority": z_priority,
          "role": role_tag,
          "bbox": g_bbox,
          "geometry": g_map,
        }
  return out


def extract_naissance_cache(cache_subdir, out_filename, z_priority, source_tag, role_tag):
  print(f"[{source_tag}] Extracting from saves/.cache/{cache_subdir} (z_priority={z_priority}, role={role_tag})...", flush=True)
  by_year = {str(y): [] for y in HYDE_YEARS}
  parts = sorted(glob.glob(os.path.join(SVEA_ROOT, "saves", ".cache", cache_subdir, "partition_*.ndjson")))
  n_ent = 0
  n_hit_ent = 0
  unique_names = set()
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
          res = eval_entity_at_years(k, v, HYDE_YEARS, z_priority, source_tag, role_tag)
          if res:
            n_hit_ent += 1
            for y, rec in res.items():
              by_year[str(y)].append(rec)
              unique_names.add(rec["name"])

  payload = {
    "_metadata": {
      "project": "AUSTRAL",
      "source": source_tag,
      "source_dir": f"saves/.cache/{cache_subdir}",
      "z_priority": z_priority,
      "role": role_tag,
      "entities_scanned": n_ent,
      "entities_extracted": n_hit_ent,
      "unique_polity_names": sorted(unique_names),
      "target_years": HYDE_YEARS,
      "spatial_contract": {
        "include": "lon >= 110.0 OR lon <= -105.0, lat in [-56.0, 25.0]",
        "exclude_hawaii": "lat 18..25, lon -162..-154 (+ NW Hawaiian Is. lat 22..25, lon -179..-162 + Palmyra Atoll)",
        "exclude_american_samoa": "lat -15..-11, lon -171.25..-168.0 (preserves Upolu <= -171.438W)",
        "exclude_mandala_west": "lon 110.0..129.5, lat -11.3..25.0 (covers Roti/Timor down to -11.08S)",
        "exclude_mandala_east_maluku": "exact archipelago boxes + buffered pixels >= 129.45E from mandala_domain_mask.png (Gebe/East Seram/Babar/Tanimbar/Kai/Aru up to 135.2E)",
        "exclude_castle_bonin": "lon 129.5..160.0, lat 21.0..25.0",
        "exclude_jaguar_baja_clipperton": "lon -116.0..-105.0, lat 15.0..25.0 + Clipperton Atoll",
      },
    }
  }
  payload.update(by_year)
  out_p = os.path.join(PARSED_DIR, out_filename)
  with open(out_p, "w", encoding="utf-8") as fh:
    json.dump(payload, fh)
  counts = {y: len(by_year[str(y)]) for y in HYDE_YEARS if len(by_year[str(y)]) > 0}
  print(f"  Saved {out_p} | scanned={n_ent}, matched_entities={n_hit_ent}, non_empty_years={len(counts)}", flush=True)
  print(f"  Counts per non-empty year: {counts}", flush=True)
  return {
    "file": out_p,
    "size_bytes": os.path.getsize(out_p),
    "entities_scanned": n_ent,
    "entities_extracted": n_hit_ent,
    "unique_names_count": len(unique_names),
    "counts_by_year": {str(y): len(by_year[str(y)]) for y in HYDE_YEARS},
  }


def cshapes_date_tuple(props, prefix):
  y = int(props.get(f"{prefix}year") or 0)
  m = int(props.get(f"{prefix}month") or 1)
  d = int(props.get(f"{prefix}day") or 1)
  return (y, m, d)


def extract_cshapes():
  print("[cshapes_2_0] Extracting from saves/CShapes-2.0.geojson (1886-2019 + 2020 from 2019 end-state)...", flush=True)
  fp = os.path.join(SVEA_ROOT, "saves", "CShapes-2.0.geojson")
  with open(fp, "r", encoding="utf-8") as fh:
    data = json.load(fh)

  by_year = {str(y): [] for y in CSHAPES_YEARS}
  unique_names = set()
  matched_features = 0

  for idx, feat in enumerate(data.get("features") or []):
    props = feat.get("properties") or {}
    g_clean = clean_austral_geom(feat.get("geometry"))
    if g_clean is None:
      continue
    matched_features += 1
    s_dt = cshapes_date_tuple(props, "gws")
    e_dt = cshapes_date_tuple(props, "gwe")
    g_map = mapping(g_clean)
    g_bbox = [round(v, 4) for v in g_clean.bounds]
    cname = str(props.get("cntry_name") or f"CShapes_{idx}").strip()
    gwcode = props.get("gwcode")
    unique_names.add(cname)

    for y in CSHAPES_YEARS:
      sample_y = 2019 if y == 2020 else y
      target_dt = (sample_y, 6, 15)
      if s_dt <= target_dt <= e_dt:
        rec = {
          "id": f"gw_{gwcode}_{idx}",
          "gwcode": gwcode,
          "name": cname,
          "start_year": s_dt[0],
          "end_year": e_dt[0],
          "source": "cshapes_2_0",
          "z_priority": 3,
          "role": "colonial_postcolonial_polities_below_primary_subadmin",
          "bbox": g_bbox,
          "geometry": g_map,
        }
        if y == 2020:
          rec["cshapes_sampled_year"] = 2019
        by_year[str(y)].append(rec)

  payload = {
    "_metadata": {
      "project": "AUSTRAL",
      "source": "cshapes_2_0",
      "source_file": "saves/CShapes-2.0.geojson",
      "z_priority": 3,
      "role": "colonial_postcolonial_polities_below_primary_subadmin",
      "features_scanned": len(data.get("features") or []),
      "features_extracted": matched_features,
      "unique_polity_names": sorted(unique_names),
      "target_years": CSHAPES_YEARS,
      "note_2020": "CShapes-2.0 ends 2019-12-31; year 2020 slice is sampled from 2019-06-15.",
    }
  }
  payload.update(by_year)
  out_p = os.path.join(PARSED_DIR, "cshapes_austral_cache.json")
  with open(out_p, "w", encoding="utf-8") as fh:
    json.dump(payload, fh)
  counts = {y: len(by_year[str(y)]) for y in CSHAPES_YEARS}
  print(f"  Saved {out_p} | scanned={len(data.get('features') or [])}, matched={matched_features}", flush=True)
  print(f"  Counts per year: {counts}", flush=True)
  return {
    "file": out_p,
    "size_bytes": os.path.getsize(out_p),
    "features_scanned": len(data.get("features") or []),
    "features_extracted": matched_features,
    "unique_names": sorted(unique_names),
    "counts_by_year": {str(y): len(by_year[str(y)]) for y in CSHAPES_YEARS},
  }


def main():
  summary = {
    "atlas_dejure": extract_naissance_cache(
      "atlas_dejure",
      "atlas_dejure_austral_cache.json",
      z_priority=2,
      source_tag="atlas_dejure",
      role_tag="middle_z_dejure_polities_below_primary_hgis",
    ),
    "cshapes": extract_cshapes(),
    "atlas_defacto": extract_naissance_cache(
      "atlas_defacto",
      "atlas_defacto_austral_cache.json",
      z_priority=1,
      source_tag="atlas_defacto",
      role_tag="z1_fallback_only",
    ),
  }
  print("\n=== EXTRACTION COMPLETE ===", flush=True)
  for k, v in summary.items():
    print(f"  {k}: {os.path.basename(v['file'])} ({v['size_bytes']:,} bytes)", flush=True)


if __name__ == "__main__":
  main()
