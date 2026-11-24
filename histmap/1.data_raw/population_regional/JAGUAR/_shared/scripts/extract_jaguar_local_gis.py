"""Local GIS, Domain Mask & Naissance Extraction for Operation Viscount Project JAGUAR.

Extracts:
  1. JAGUAR country & Admin-1 vector subsets from Natural Earth 10m cache (Mexico, Central America,
     Greater & Lesser Antilles, Bahamas, Trinidad & Tobago, and Bermuda).
  2. 4320x2160 RGBA `jaguar_domain_mask.png` preserving all habitable islands including Bermuda and
     Lesser Antilles micro-islands.
  3. Coastal-complete `atlas_dejure_jaguar_cache.json` from `saves/.cache/atlas_dejure/` and
     strictly z=1 fallback `atlas_defacto_jaguar_cache.json` from `saves/.cache/atlas_defacto/`.
"""

import glob
import json
import os

import cv2
import numpy as np
from PIL import Image
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
JAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JAGUAR")
JAG_GIS = os.path.join(JAG_DIR, "_shared", "_gis_cache")
PARSED_DIR = os.path.join(JAG_DIR, "_shared", "subadmin_hgis", "parsed")
DOMAIN_CFG_DIR = os.path.join(JAG_DIR, "_shared", "sites_jaguar_mesoamerica", "config")
NE_ADM0 = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared", "_gis_cache", "ne_10m_admin_0_countries.geojson")
NE_ADM1 = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CENTAUR", "_shared", "_gis_cache", "ne_10m_admin_1_states_provinces.geojson")
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")

os.makedirs(JAG_GIS, exist_ok=True)
os.makedirs(PARSED_DIR, exist_ok=True)
os.makedirs(DOMAIN_CFG_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160

JAGUAR_ADMIN_NAMES = {
  "Anguilla", "Antigua and Barbuda", "Aruba", "Barbados", "Belize", "Bermuda",
  "British Virgin Islands", "Cayman Islands", "Costa Rica", "Cuba", "Curaçao",
  "Curacao", "Dominica", "Dominican Republic", "El Salvador", "Grenada",
  "Guatemala", "Haiti", "Honduras", "Jamaica", "Mexico", "Montserrat",
  "Nicaragua", "Panama", "Puerto Rico", "Saint Barthelemy", "Saint Barthélemy",
  "Saint Kitts and Nevis", "Saint Lucia", "Saint Martin", "Saint-Martin",
  "Saint Vincent and the Grenadines", "Sint Maarten", "The Bahamas",
  "Trinidad and Tobago", "Turks and Caicos Islands",
  "United States Virgin Islands", "US Virgin Islands",
  "Bajo Nuevo Bank (Petrel Is.)", "Clipperton Island", "Navassa Island",
  "Serranilla Bank", "US Naval Base Guantanamo Bay",
}

# French & Dutch Caribbean overseas territories stored inside France / Netherlands in NE 10m ADM0
CARIBBEAN_OVERSEAS_SOVS = {"France", "Netherlands"}
CARIBBEAN_BBOX = (-86.0, 10.0, -58.0, 22.0)

TARGET_YEARS = [
  -1000, -500, 0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000,
  1100, 1200, 1300, 1400, 1492, 1500, 1519, 1550, 1600, 1650, 1700,
  1750, 1790, 1800, 1810, 1821, 1830, 1840, 1850, 1860, 1880, 1900,
  1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020
]

BC_LEAP = {-45, -42, -39, -36, -33, -30, -27, -24, -21, -18, -15, -12, -9}


def is_leap_year (arg0_yr):
  if arg0_yr in BC_LEAP:
    return True
  return (((arg0_yr % 4 == 0) and (arg0_yr % 100 != 0)) or (arg0_yr % 400 == 0)) and arg0_yr != 4


def year_to_ts (arg0_yr, arg1_month=6, arg2_day=15):
  mins = 0
  if arg0_yr > 0:
    for y in range(0, arg0_yr):
      mins += (366 if is_leap_year(y) else 365) * 1440
  elif arg0_yr < 0:
    for y in range(-1, arg0_yr - 1, -1):
      mins -= (366 if is_leap_year(y) else 365) * 1440
  mdays = [31, 29 if is_leap_year(arg0_yr) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  for m in range(1, arg1_month):
    mins += mdays[m - 1] * 1440
  mins += (arg2_day - 1) * 1440
  return mins


YEAR_TS = {y: year_to_ts(y, 6, 15) for y in TARGET_YEARS}


def safe_poly (arg0_geom):
  if arg0_geom is None or arg0_geom.is_empty:
    return None
  g = arg0_geom
  if not g.is_valid:
    g = make_valid(g)
  if g.geom_type == "GeometryCollection":
    polys = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon") and not p.is_empty]
    if not polys:
      return None
    g = unary_union(polys)
  if g.geom_type not in ("Polygon", "MultiPolygon") or g.is_empty:
    return None
  return g


def extract_ne_subsets ():
  print("[1] Extracting JAGUAR countries & ADM1 subsets from Natural Earth 10m...", flush=True)
  adm0 = json.load(open(NE_ADM0, encoding="utf-8"))
  adm1 = json.load(open(NE_ADM1, encoding="utf-8"))

  country_feats = []
  adm1_feats = []
  seen_adm0 = set()

  for feat in adm0["features"]:
    props = feat.get("properties") or {}
    nm = props.get("ADMIN") or props.get("NAME") or ""
    g = safe_poly(shape(feat["geometry"]))
    if g is None:
      continue
    if nm in JAGUAR_ADMIN_NAMES:
      country_feats.append({"type": "Feature", "properties": {"ADMIN": nm, "ISO_A3": props.get("ISO_A3", ""), "SOVEREIGNT": props.get("SOVEREIGNT", nm)}, "geometry": mapping(g)})
      seen_adm0.add(nm)
    elif nm in CARIBBEAN_OVERSEAS_SOVS:
      # Extract Caribbean overseas islands (Guadeloupe, Martinique, Bonaire, Saba, Sint Eustatius)
      polys = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
      carib_polys = []
      for p in polys:
        cx, cy = p.centroid.x, p.centroid.y
        if CARIBBEAN_BBOX[0] <= cx <= CARIBBEAN_BBOX[2] and CARIBBEAN_BBOX[1] <= cy <= CARIBBEAN_BBOX[3]:
          # Exclude French Guiana (lat < 10)
          carib_polys.append(p)
      if carib_polys:
        u = safe_poly(unary_union(carib_polys))
        if u is not None:
          label = "French Antilles" if nm == "France" else "Caribbean Netherlands"
          country_feats.append({"type": "Feature", "properties": {"ADMIN": label, "ISO_A3": "GLP_MTQ" if nm == "France" else "BES", "SOVEREIGNT": nm}, "geometry": mapping(u)})
          seen_adm0.add(label)

  for feat in adm1["features"]:
    props = feat.get("properties") or {}
    adm_nm = props.get("admin") or props.get("ADMIN") or ""
    unit_nm = props.get("name") or props.get("NAME") or ""
    g = safe_poly(shape(feat["geometry"]))
    if g is None:
      continue
    cx, cy = g.centroid.x, g.centroid.y
    include = False
    eff_adm = adm_nm
    if adm_nm in JAGUAR_ADMIN_NAMES:
      include = True
    elif adm_nm in CARIBBEAN_OVERSEAS_SOVS and CARIBBEAN_BBOX[0] <= cx <= CARIBBEAN_BBOX[2] and CARIBBEAN_BBOX[1] <= cy <= CARIBBEAN_BBOX[3]:
      include = True
      eff_adm = "French Antilles" if adm_nm == "France" else "Caribbean Netherlands"
    if include:
      adm1_feats.append({
        "type": "Feature",
        "properties": {
          "admin": eff_adm,
          "name": unit_nm,
          "iso_3166_2": props.get("iso_3166_2", ""),
          "type_en": props.get("type_en", ""),
        },
        "geometry": mapping(g)
      })

  c_out = os.path.join(JAG_GIS, "jaguar_countries.geojson")
  a1_out = os.path.join(JAG_GIS, "jaguar_admin1.geojson")
  json.dump({"type": "FeatureCollection", "features": country_feats}, open(c_out, "w", encoding="utf-8"))
  json.dump({"type": "FeatureCollection", "features": adm1_feats}, open(a1_out, "w", encoding="utf-8"))
  print(f"  Saved {len(country_feats)} countries/territories -> {c_out}", flush=True)
  print(f"  Saved {len(adm1_feats)} ADM1 units -> {a1_out}", flush=True)
  print(f"  Territories: {sorted(seen_adm0)}", flush=True)
  return country_feats


def build_domain_mask (arg0_country_feats):
  print("[2] Rasterising 4320x2160 jaguar_domain_mask.png (with micro-island guarantee)...", flush=True)
  mask = np.zeros((GRID_H, GRID_W), dtype=np.uint8)
  shift = 4
  scale = 1 << shift

  def ring_to_pts (arg0_ring):
    coords = np.asarray(arg0_ring.coords, dtype=np.float64)
    xs = np.round((coords[:, 0] + 180.0) * (GRID_W / 360.0) * scale).astype(np.int32)
    ys = np.round((90.0 - coords[:, 1]) * (GRID_H / 180.0) * scale).astype(np.int32)
    return np.stack([xs, ys], axis=1).reshape(-1, 1, 2)

  for feat in arg0_country_feats:
    g = safe_poly(shape(feat["geometry"]))
    if g is None:
      continue
    polys = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    local_mask = np.zeros((GRID_H, GRID_W), dtype=np.uint8)
    for p in polys:
      cv2.fillPoly(local_mask, [ring_to_pts(p.exterior)], 1, shift=shift)
      for hole in p.interiors:
        cv2.fillPoly(local_mask, [ring_to_pts(hole)], 0, shift=shift)
      # Guarantee micro-islands (Bermuda, Saba, St Barts, Anguilla, Caymans, etc.) retain at least their centroid pixel
      if local_mask.sum() == 0 or p.area < 0.02:
        cx, cy = p.centroid.x, p.centroid.y
        col = min(GRID_W - 1, max(0, int((cx + 180.0) * GRID_W / 360.0)))
        row = min(GRID_H - 1, max(0, int((90.0 - cy) * GRID_H / 180.0)))
        local_mask[row, col] = 1
    mask |= local_mask

  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  rgba[mask > 0] = [68, 132, 92, 255]
  out_png = os.path.join(DOMAIN_CFG_DIR, "jaguar_domain_mask.png")
  Image.fromarray(rgba, mode="RGBA").save(out_png)
  ys, xs = np.where(mask > 0)
  print(f"  Saved {out_png}: active_px={int(mask.sum())}, row=[{int(ys.min())}..{int(ys.max())}], col=[{int(xs.min())}..{int(xs.max())}]", flush=True)


def clean_jaguar_geom (arg0_raw_g):
  if not isinstance(arg0_raw_g, dict):
    return None
  raw_g = arg0_raw_g
  if "feature" in raw_g:
    raw_g = (raw_g.get("feature") or {}).get("geometry")
  if not isinstance(raw_g, dict) or raw_g.get("type") not in ("Polygon", "MultiPolygon"):
    return None
  try:
    g = safe_poly(shape(raw_g))
    if g is None:
      return None
    minx, miny, maxx, maxy = g.bounds
    if maxx < -120.0 or minx > -58.0 or maxy < 6.0 or miny > 35.0:
      return None
    if g.area < 0.001:
      return None
    g = g.simplify(0.01, preserve_topology=True)
    if g.is_empty:
      return None
    return g
  except Exception:
    return None


def eval_entity_at_years (arg0_eid, arg1_ent, arg2_years):
  hist = arg1_ent.get("history") or {}
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
  for y in sorted(arg2_years):
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
      g = clean_jaguar_geom(cur_g)
      if g is not None:
        out[y] = {"id": str(arg0_eid), "name": cur_nm or f"Entity_{arg0_eid}", "geometry": mapping(g)}
  return out


def extract_naissance_cache (arg0_cache_name, arg1_out_name):
  print(f"[3] Extracting {arg0_cache_name} -> {arg1_out_name}...", flush=True)
  by_year = {str(y): [] for y in TARGET_YEARS}
  parts = sorted(glob.glob(os.path.join(SVEA_ROOT, "saves", ".cache", arg0_cache_name, "partition_*.ndjson")))
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
  out_p = os.path.join(PARSED_DIR, arg1_out_name)
  json.dump(by_year, open(out_p, "w", encoding="utf-8"))
  sample = {y: len(by_year[str(y)]) for y in (0, 600, 1200, 1492, 1519, 1600, 1700, 1790, 1821, 1850, 1900, 1950, 2000)}
  print(f"  Saved {out_p} ({n_ent} scanned): {sample}", flush=True)


if __name__ == "__main__":
  feats = extract_ne_subsets()
  build_domain_mask(feats)
  extract_naissance_cache("atlas_dejure", "atlas_dejure_jaguar_cache.json")
  extract_naissance_cache("atlas_defacto", "atlas_defacto_jaguar_cache.json")

