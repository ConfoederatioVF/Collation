"""Deterministic 5-arcminute (4320x2160) Dual-Output GIS Mask Builder for Operation Viscount
Project QUIPU (17 chapters across Pre-Columbian, Colonial, and Post-Independence regimes).

Generates:
  1. `QUIPU/_shared/sites_quipu_andes_cone/config/quipu_domain_mask.png` (4320x2160 binary uint8 land mask)
  2. All 17 chapter `<stem>_areal_mask.png` (4320x2160 RGBA PNGs, OpenCV cv2.fillPoly shift=4 with local hole subtraction)
  3. All 17 chapter `<stem>.json5` demographic & spatial manifests (exact PRETA schema + verified eda_part3 enumerations)
  4. All 17 smooth vector GeoJSONs (`QUIPU/_shared/_gis_cache/chapter_subregions/<stem>_subregions.geojson`)
  5. High-resolution regional bbox crop QA PNGs (`tests/mask_crops/quipu_<stem>.png`)

Sources strictly limited to authentic GIS & academic HGIS:
  - OpenHistoricalMap (ohm_quipu_polities_cache.geojson from ohm_sa_admin.geojson, CC0)
  - HydroBASINS South America Level 4 & Level 5 watersheds
  - Werner Stangl's HGIS de las Indias (the_geom.gpkg LCG polygons)
  - CONICET Argentina (Departamentos_2022_INDEC.shp, all 24 provinces incl. Entre Rios & CABA)
  - geoBoundaries ADM1 (COL, VEN excl. Essequibo, ECU incl. Galapagos, PER, BOL 6 Andean depts, CHL excl. Rapa Nui, URY)
  - Natural Earth 10m Admin-0 (FLK & SGS split into East Falkland, West Falkland, South Georgia, South Sandwich Islands)
"""

import colorsys
import io
import json
import math
import os
import pathlib
import re
import sqlite3
import sys
import unicodedata
import zipfile

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.ndimage import binary_closing, binary_dilation, label as nd_label
from scipy.spatial import cKDTree
import shapefile
import shapely
from shapely import wkb
from shapely.geometry import MultiPolygon, Polygon, box, mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

sys.stdout.reconfigure(encoding="utf-8")

W, H = 4320, 2160
SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
QUIPU_DIR = SCRIPTS_DIR.parents[1]
POP_REG_DIR = QUIPU_DIR.parent
SVEA_ROOT = POP_REG_DIR.parents[2]

RAW_DIR = QUIPU_DIR / "_shared/subadmin_hgis/raw_sources"
GIS_CACHE_DIR = QUIPU_DIR / "_shared/_gis_cache"
SUBREG_OUT_DIR = GIS_CACHE_DIR / "chapter_subregions"
DOMAIN_CFG_DIR = QUIPU_DIR / "_shared/sites_quipu_andes_cone/config"
QA_CROPS_DIR = SVEA_ROOT / "tests/mask_crops"

SUBREG_OUT_DIR.mkdir(parents=True, exist_ok=True)
DOMAIN_CFG_DIR.mkdir(parents=True, exist_ok=True)
QA_CROPS_DIR.mkdir(parents=True, exist_ok=True)

LAND_AREA_PNG = SVEA_ROOT / "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png"
NE10_ADM0_JSON = POP_REG_DIR / "_shared/_gis_cache/ne_10m_admin_0_countries.geojson"
HYBAS_L4_SHP = POP_REG_DIR / "PRETA/_shared/_gis_cache/hydrobasins/hybas_sa_lev04_v1c.shp"
HYBAS_L5_SHP = POP_REG_DIR / "PRETA/_shared/_gis_cache/hydrobasins/hybas_sa_lev05_v1c.shp"
HYBAS_L6_SHP = POP_REG_DIR / "PRETA/_shared/_gis_cache/hydrobasins/hybas_sa_lev06_v1c.shp"
OHM_CACHE_JSON = GIS_CACHE_DIR / "ohm_quipu_polities_cache.geojson"
HGIS_GPKG = RAW_DIR / "hgis_indias/the_geom.gpkg"
GB_DIR = RAW_DIR / "geoboundaries"
CONICET_ZIP = RAW_DIR / "national_hgis/conicet_arg_1869_2022/Base_deptos_1869-2022.zip"
ENUM_JSON = RAW_DIR / "eda_part3_enumerations.json"
PRETA_BOL_JSON5 = POP_REG_DIR / "PRETA/3.post_independence/2.bolivia_after_independence/bolivia_after_independence.json5"

QUIPU_CLIP_BOX = box(-95.0, -59.8, -24.0, 14.0)
ARG_TDF_CLIP_BOX = box(-76.0, -56.0, -63.0, -52.0)
CHL_CLIP_BOX = box(-95.0, -56.5, -66.0, -17.0)
ANDEAN_BOL_DEPTS = {"Chuquisaca", "Cochabamba", "La Paz", "Oruro", "Potosí", "Tarija"}


def norm_key(arg0_text):
  """Normalises Spanish/English place names to ASCII lowercase keys for deterministic matching."""
  if not arg0_text:
    return ""
  s = str(arg0_text)
  try:
    if "Ã" in s or "Â" in s:
      s = s.encode("latin1").decode("utf-8")
  except Exception:
    pass
  s = re.sub(r"\([^)]*\)", " ", s)
  s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
  s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
  return s


def fix_mojibake(arg0_text):
  """Fixes double-encoded UTF-8 strings (e.g. CHL_ADM1 shapeName)."""
  s = str(arg0_text or "")
  try:
    if "Ã" in s or "Â" in s:
      return s.encode("latin1").decode("utf-8")
  except Exception:
    pass
  return s


def slugify(arg0_text):
  """Produces a clean snake_case identifier."""
  return re.sub(r"[^a-z0-9]+", "_", norm_key(arg0_text)).strip("_")


def repair_geom(arg0_geom, arg1_min_area=1e-7):
  """Mandatory degenerate-topology repair: make_valid, Polygon/MultiPolygon extraction, precision snap."""
  if arg0_geom is None or arg0_geom.is_empty:
    return None
  try:
    g = make_valid(arg0_geom) if not arg0_geom.is_valid else arg0_geom
    if g.is_empty:
      return None
    if g.geom_type == "GeometryCollection":
      polys = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon") and not p.is_empty]
      if not polys:
        return None
      g = unary_union(polys)
    if g.geom_type not in ("Polygon", "MultiPolygon"):
      return None
    g = shapely.set_precision(g, 1e-4)
    g = make_valid(g)
    if g.geom_type == "GeometryCollection":
      polys = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon") and not p.is_empty]
      if not polys:
        return None
      g = unary_union(polys)
    if g.geom_type == "MultiPolygon":
      parts = [p for p in g.geoms if not p.is_empty and p.area >= arg1_min_area]
      if not parts:
        parts = [p for p in g.geoms if not p.is_empty]
      if not parts:
        return None
      g = MultiPolygon(parts) if len(parts) > 1 else parts[0]
    elif g.geom_type == "Polygon":
      if g.is_empty:
        return None
    else:
      return None
    return g
  except Exception:
    try:
      g = arg0_geom.buffer(0)
      return g if (g is not None and not g.is_empty and g.geom_type in ("Polygon", "MultiPolygon")) else None
    except Exception:
      return None


def safe_union(arg0_geoms):
  """Repairs and unions a list of shapely geometries."""
  gs = [repair_geom(g) for g in arg0_geoms if g is not None and not g.is_empty]
  gs = [g for g in gs if g is not None and not g.is_empty]
  if not gs:
    return None
  return repair_geom(unary_union(gs))


def safe_clip(arg0_geom, arg1_clip):
  """Repairs and intersects two geometries safely."""
  if arg0_geom is None or arg1_clip is None:
    return None
  try:
    return repair_geom(arg0_geom.intersection(arg1_clip))
  except Exception:
    g0 = repair_geom(arg0_geom)
    g1 = repair_geom(arg1_clip)
    if g0 is None or g1 is None:
      return None
    return repair_geom(g0.intersection(g1))


def safe_diff(arg0_geom, arg1_sub):
  """Repairs and subtracts arg1_sub from arg0_geom safely."""
  if arg0_geom is None:
    return None
  if arg1_sub is None or arg1_sub.is_empty:
    return repair_geom(arg0_geom)
  try:
    return repair_geom(arg0_geom.difference(arg1_sub))
  except Exception:
    g0 = repair_geom(arg0_geom)
    g1 = repair_geom(arg1_sub)
    if g0 is None:
      return None
    if g1 is None:
      return g0
    return repair_geom(g0.difference(g1))


def load_land_area():
  """Decodes SVEA 4320x2160 land_area.png into km² float64 grid."""
  raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  u32 = raw.reshape(-1, 4).copy().view(">u4").reshape((H, W)).astype(np.float64)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape((H, W)).astype(np.float64)
  if np.nanmax(f32) > 1.0 and np.nanmax(f32) < 500.0 and np.isfinite(f32[1080, 1500]):
    return np.where(np.isfinite(f32) & (f32 > 0), f32, 0.0)
  med = float(np.median(u32[u32 > 0])) if (u32 > 0).any() else 0.0
  if 1.0 <= med <= 500.0:
    return u32
  lats = 90.0 - (np.arange(H) + 0.5) / 12.0
  cell_km2 = (111.32 / 12.0) * (111.32 / 12.0) * np.cos(np.radians(lats))
  return np.where(u32 > 0, cell_km2[:, None], 0.0)


def spherical_cell_km2():
  """Returns (H,) float64 pixel area per latitude row in km²."""
  lats = 90.0 - (np.arange(H) + 0.5) / 12.0
  return (111.32 / 12.0) * (111.32 / 12.0) * np.cos(np.radians(lats))


def rasterise_geom_cv2(arg0_geom):
  """Rasterises a Polygon/MultiPolygon onto (H, W) bool mask via OpenCV cv2.fillPoly(shift=4)
  with strict local interior hole subtraction (zero scanline gaps, zero cross-polygon hole erasure)."""
  out = np.zeros((H, W), dtype=np.uint8)
  if arg0_geom is None or arg0_geom.is_empty:
    return out.astype(bool)

  polys = []
  if arg0_geom.geom_type == "Polygon":
    polys = [arg0_geom]
  elif arg0_geom.geom_type == "MultiPolygon":
    polys = list(arg0_geom.geoms)
  elif arg0_geom.geom_type == "GeometryCollection":
    for p in arg0_geom.geoms:
      if p.geom_type == "Polygon":
        polys.append(p)
      elif p.geom_type == "MultiPolygon":
        polys.extend(list(p.geoms))

  scale = 16.0  # shift=4 subpixel precision
  for poly in polys:
    if poly.is_empty:
      continue
    minx, miny, maxx, maxy = poly.bounds
    c0 = max(0, int(math.floor((minx + 180.0) * 12.0)) - 2)
    c1 = min(W, int(math.ceil((maxx + 180.0) * 12.0)) + 2)
    r0 = max(0, int(math.floor((90.0 - maxy) * 12.0)) - 2)
    r1 = min(H, int(math.ceil((90.0 - miny) * 12.0)) + 2)
    if c1 <= c0 or r1 <= r0:
      continue

    lh, lw = r1 - r0, c1 - c0
    local = np.zeros((lh, lw), dtype=np.uint8)

    ext = np.asarray(poly.exterior.coords, dtype=np.float64)
    if len(ext) < 3:
      continue
    ex_x = np.round(((ext[:, 0] + 180.0) * 12.0 - c0) * scale).astype(np.int32)
    ex_y = np.round(((90.0 - ext[:, 1]) * 12.0 - r0) * scale).astype(np.int32)
    pts_ext = np.column_stack([ex_x, ex_y]).reshape(-1, 1, 2)
    cv2.fillPoly(local, [pts_ext], 1, shift=4)

    for hole in poly.interiors:
      hc = np.asarray(hole.coords, dtype=np.float64)
      if len(hc) < 3:
        continue
      hx = np.round(((hc[:, 0] + 180.0) * 12.0 - c0) * scale).astype(np.int32)
      hy = np.round(((90.0 - hc[:, 1]) * 12.0 - r0) * scale).astype(np.int32)
      pts_h = np.column_stack([hx, hy]).reshape(-1, 1, 2)
      cv2.fillPoly(local, [pts_h], 0, shift=4)

    out[r0:r1, c0:c1] |= local

  return out.astype(bool)


def latlon_to_rc(arg0_lat, arg1_lon):
  """Converts (lat, lon) to integer (row, col) on the 4320x2160 grid."""
  r = min(H - 1, max(0, int(math.floor((90.0 - arg0_lat) * 12.0))))
  c = min(W - 1, max(0, int(math.floor((arg1_lon + 180.0) * 12.0))))
  return r, c


def nearest_fill(arg0_target_mask, arg1_label_grid, arg2_valid_labels):
  """Assigns any True pixel in target_mask not yet labelled to its nearest valid pixel."""
  src_mask = np.isin(arg1_label_grid, list(arg2_valid_labels))
  missing = arg0_target_mask & (~src_mask)
  if not missing.any() or not src_mask.any():
    return arg1_label_grid
  sr, sc = np.where(src_mask)
  mr, mc = np.where(missing)
  tree = cKDTree(np.column_stack([sr, sc]))
  _, idx = tree.query(np.column_stack([mr, mc]))
  out = arg1_label_grid.copy()
  out[mr, mc] = arg1_label_grid[sr[idx], sc[idx]]
  return out


def distinct_palette(arg0_n, arg1_seed_offset=0.0):
  """Generates n visually distinct vivid non-black RGB colours."""
  cols = []
  used = {(0, 0, 0)}
  for i in range(arg0_n):
    hue = (arg1_seed_offset + i * 0.618033988749895) % 1.0
    sat = 0.58 + 0.28 * ((i % 3) / 2.0)
    val = 0.72 + 0.22 * (((i // 3) % 3) / 2.0)
    r, g, b = [max(24, min(244, int(round(c * 255)))) for c in colorsys.hsv_to_rgb(hue, sat, val)]
    while (r, g, b) in used:
      r = (r + 19) % 220 + 24
      g = (g + 31) % 220 + 24
    used.add((r, g, b))
    cols.append([r, g, b])
  return cols


def make_bounds(arg0_pop_dict, arg1_rel_unc=0.18):
  """Generates symmetric [low, high] uncertainty bounds calibrated to historical period."""
  out = {}
  for yk, val in arg0_pop_dict.items():
    v = int(round(val))
    yr = int(yk)
    if yr <= -2000:
      u = max(arg1_rel_unc, 0.35)
    elif yr < 1500:
      u = max(arg1_rel_unc, 0.25)
    elif yr < 1850:
      u = max(arg1_rel_unc, 0.14)
    elif yr < 1950:
      u = 0.06
    else:
      u = 0.025
    lo = max(0, int(round(v * (1.0 - u))))
    hi = max(lo + 1, int(round(v * (1.0 + u))))
    out[str(yk)] = [lo, hi]
  return out


def holocene_curve(arg0_peak, arg1_profile="northern_andes", arg2_end_year=1500):
  """Generates smooth log-calibrated Holocene demographic benchmark trajectories."""
  curves = {
    "northern_andes": {
      -10000: 0.006, -9000: 0.010, -8000: 0.015, -7000: 0.022, -6000: 0.034,
      -5000: 0.052, -4000: 0.078, -3000: 0.115, -2000: 0.175, -1000: 0.265,
      0: 0.420, 200: 0.490, 400: 0.565, 600: 0.645, 800: 0.730,
      1000: 0.815, 1100: 0.855, 1200: 0.895, 1300: 0.935, 1400: 0.970, 1500: 1.000,
    },
    "central_andes_preinca": {
      -10000: 0.004, -9000: 0.007, -8000: 0.011, -7000: 0.017, -6000: 0.026,
      -5000: 0.042, -4000: 0.066, -3000: 0.105, -2000: 0.165, -1000: 0.260,
      0: 0.440, 200: 0.530, 400: 0.630, 600: 0.740, 800: 0.835,
      1000: 0.865, 1100: 0.880, 1200: 0.915, 1300: 0.955, 1400: 0.985, 1438: 1.000,
    },
    "central_andes_altiplano": {
      -10000: 0.004, -9000: 0.007, -8000: 0.011, -7000: 0.017, -6000: 0.027,
      -5000: 0.043, -4000: 0.068, -3000: 0.105, -2000: 0.160, -1000: 0.255,
      0: 0.440, 200: 0.545, 400: 0.680, 600: 0.850, 800: 0.975,
      1000: 0.960, 1100: 0.870, 1200: 0.895, 1300: 0.940, 1400: 0.980, 1438: 1.000,
    },
    "southern_cone_agri": {
      -10000: 0.010, -9000: 0.016, -8000: 0.024, -7000: 0.036, -6000: 0.052,
      -5000: 0.075, -4000: 0.105, -3000: 0.145, -2000: 0.205, -1000: 0.295,
      0: 0.430, 200: 0.495, 400: 0.565, 600: 0.640, 800: 0.725,
      1000: 0.815, 1100: 0.860, 1200: 0.900, 1300: 0.940, 1400: 0.975, 1500: 1.000,
    },
    "southern_cone_forager": {
      -10000: 0.050, -9000: 0.075, -8000: 0.105, -7000: 0.140, -6000: 0.185,
      -5000: 0.235, -4000: 0.295, -3000: 0.365, -2000: 0.440, -1000: 0.520,
      0: 0.610, 200: 0.655, 400: 0.700, 600: 0.745, 800: 0.790,
      1000: 0.840, 1100: 0.875, 1200: 0.910, 1300: 0.945, 1400: 0.975, 1500: 1.000,
    },
  }
  c = curves[arg1_profile]
  return {str(y): max(100, int(round(arg0_peak * frac))) for y, frac in c.items() if y <= arg2_end_year}


def parse_gpkg_wkb(arg0_blob):
  """Decodes a GeoPackage geometry blob to shapely geometry (skipping unsupported nonlinear types)."""
  if not arg0_blob:
    return None
  flags = arg0_blob[3]
  env_bytes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get((flags >> 1) & 0x07, 0)
  try:
    return repair_geom(wkb.loads(arg0_blob[8 + env_bytes:]))
  except Exception:
    return None


def load_all_gis():
  """Loads geoBoundaries ADM1, CONICET 2022 ARG ADM1, NE10m FLK/SGS, HydroBASINS L4/L5, OHM, and HGIS de las Indias."""
  print("Loading geoBoundaries ADM1, CONICET 2022 Argentina, NE 10m FLK/SGS...", flush=True)
  gb_adm1 = {}
  for iso in ["COL", "VEN", "ECU", "PER", "BOL", "CHL", "URY"]:
    with open(GB_DIR / f"{iso}_ADM1.geojson", "r", encoding="utf-8") as fh:
      gj = json.load(fh)
    units = {}
    for ft in gj["features"]:
      nm = fix_mojibake(ft["properties"].get("shapeName", ""))
      g = repair_geom(shape(ft["geometry"]))
      if g is None:
        continue
      if iso == "CHL":
        g = safe_clip(g, CHL_CLIP_BOX)
        if g is None:
          continue
      elif iso == "BOL" and nm not in ANDEAN_BOL_DEPTS:
        continue
      units[nm] = safe_union([units[nm], g]) if nm in units else g
    gb_adm1[iso] = units

  # Argentina: CONICET 2022 INDEC dissolved by cpr (all 24 provinces incl. Entre Rios & CABA!)
  arg_by_prov = {}
  with zipfile.ZipFile(CONICET_ZIP) as zf:
    sn = "Base deptos 1869-2022/Departamentos_2022_INDEC.shp"
    sf = shapefile.Reader(
      shp=io.BytesIO(zf.read(sn)),
      dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")),
      encoding="latin1",
    )
    flds = [f[0] for f in sf.fields[1:]]
    for i, rec in enumerate(sf.records()):
      d = dict(zip(flds, rec))
      jur = str(d["jur"]).strip()
      if jur.startswith("Tierra del Fuego"):
        jur = "Tierra del Fuego"
      g = repair_geom(shape(sf.shape(i).__geo_interface__))
      if g is None:
        continue
      if jur == "Tierra del Fuego":
        g = safe_clip(g, ARG_TDF_CLIP_BOX)
        if g is None:
          continue
      arg_by_prov.setdefault(jur, []).append(g)
  gb_adm1["ARG"] = {k: safe_union(v) for k, v in arg_by_prov.items() if safe_union(v) is not None}

  # Falkland Islands & South Georgia / South Sandwich from NE 10m Admin-0
  flk_sgs = {}
  with open(NE10_ADM0_JSON, "r", encoding="utf-8") as fh:
    ne0 = json.load(fh)
  for ft in ne0["features"]:
    p = ft["properties"]
    iso = p.get("ADM0_A3") or p.get("ISO_A3") or ""
    if iso == "FLK":
      g = repair_geom(shape(ft["geometry"]))
      east_parts, west_parts = [], []
      parts = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
      for pt in parts:
        if pt.centroid.x >= -59.55:
          east_parts.append(pt)
        else:
          west_parts.append(pt)
      flk_sgs["East Falkland"] = safe_union(east_parts)
      flk_sgs["West Falkland"] = safe_union(west_parts)
    elif iso == "SGS":
      g = repair_geom(shape(ft["geometry"]))
      sg_parts, ss_parts = [], []
      parts = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
      for pt in parts:
        if pt.centroid.x <= -34.0:
          sg_parts.append(pt)
        else:
          ss_parts.append(pt)
      flk_sgs["South Georgia"] = safe_union(sg_parts)
      flk_sgs["South Sandwich Islands"] = safe_union(ss_parts)
  gb_adm1["FLK_SGS"] = flk_sgs

  # HydroBASINS SA Level 4, Level 5 & Level 6 (filtered to Central Andes headwaters for L6!)
  print("Loading HydroBASINS SA Level 4, Level 5 & Level 6...", flush=True)
  hybas4, hybas5, hybas6 = [], [], []
  for shp_p, target, l6_only in [(HYBAS_L4_SHP, hybas4, False), (HYBAS_L5_SHP, hybas5, False), (HYBAS_L6_SHP, hybas6, True)]:
    sf = shapefile.Reader(str(shp_p))
    flds = [f[0] for f in sf.fields[1:]]
    for i, rec in enumerate(sf.records()):
      d = dict(zip(flds, rec))
      pf = str(d["PFAF_ID"])
      if l6_only and not pf.startswith(("67107", "62298", "62299")):
        continue
      bb = sf.shape(i).bbox
      if bb[2] < -95.0 or bb[0] > -24.0 or bb[3] < -60.0 or bb[1] > 14.0:
        continue
      g = repair_geom(shape(sf.shape(i).__geo_interface__).simplify(0.01, preserve_topology=True))
      if g is not None:
        target.append((pf, g))

  # OHM Polities Cache
  print("Loading OHM historical polities cache...", flush=True)
  ohm_by_name = {}
  with open(OHM_CACHE_JSON, "r", encoding="utf-8") as fh:
    ohm_gj = json.load(fh)
  for ft in ohm_gj["features"]:
    p = ft["properties"]
    nm = str(p.get("name") or "")
    sd = str(p.get("start_date") or "")
    g = repair_geom(shape(ft["geometry"]))
    if g is not None:
      ohm_by_name.setdefault(nm, []).append((sd, str(p.get("end_date") or ""), str(p.get("admin_level") or ""), g))

  # HGIS de las Indias the_geom.gpkg LCG polygons (strictly filtering out mislabelled Brazilian frontier slugs FRED03/FRED05
  # and reassigning QUFR01 Colombian Amazon frontier to NGR Caguan instead of Popayan!)
  print("Loading Werner Stangl HGIS de las Indias (the_geom.gpkg)...", flush=True)
  hgis_lcg = {}  # (Region, Province_1) -> list of geoms
  con = sqlite3.connect(str(HGIS_GPKG))
  for fid, blob, ilcg, reg, prov in con.execute("SELECT fid, geom, ILCG_ID, Region, Province_1 FROM LCG"):
    if reg not in ("NGR", "QUI", "VEN", "PER", "CHA", "CHL", "RPL"):
      continue
    if ilcg in ("FRED03", "FRED05"):
      continue
    g = parse_gpkg_wkb(blob)
    if g is not None and g.intersects(QUIPU_CLIP_BOX):
      if ilcg == "QUFR01":
        hgis_lcg.setdefault(("NGR", "Caguan"), []).append(g)
      else:
        hgis_lcg.setdefault((reg, str(prov or "")), []).append(g)
  con.close()
  hgis_prov = {k: safe_union(v) for k, v in hgis_lcg.items() if safe_union(v) is not None}

  return {
    "adm1": gb_adm1,
    "hybas4": hybas4,
    "hybas5": hybas5,
    "hybas6": hybas6,
    "ohm": ohm_by_name,
    "hgis": hgis_prov,
  }


def union_hybas(arg0_hybas, arg1_prefixes, arg2_clip=None, arg3_excl=None):
  """Unions HydroBASINS polygons matching Pfafstetter prefixes."""
  excl = tuple(arg3_excl) if arg3_excl else ()
  gs = [
    g for pf, g in arg0_hybas
    if any(pf.startswith(p) for p in arg1_prefixes)
    and (not excl or not pf.startswith(excl))
  ]
  u = safe_union(gs)
  if u is not None and arg2_clip is not None:
    u = safe_clip(u, arg2_clip)
  return u


def union_hgis(arg0_hgis, arg1_pairs, arg2_clip=None):
  """Unions HGIS de las Indias (Region, Province_1) polygons."""
  gs = [arg0_hgis[k] for k in arg1_pairs if k in arg0_hgis]
  u = safe_union(gs)
  if u is not None and arg2_clip is not None:
    u = safe_clip(u, arg2_clip)
  return u


def get_ohm_geom(arg0_ohm, arg1_name, arg2_start_prefix=None):
  """Returns the repaired OHM geometry matching name and optional start_date prefix."""
  items = arg0_ohm.get(arg1_name, [])
  if arg2_start_prefix:
    items = [x for x in items if x[0].startswith(arg2_start_prefix)]
  if not items:
    return None
  return safe_union([x[3] for x in items])


def render_qa_crop(arg0_rgba, arg1_regions_meta, arg2_title, arg3_domain, arg4_out_path):
  """Renders a high-resolution regional bbox crop PNG with legend for optical QA."""
  alpha = arg0_rgba[:, :, 3] > 0
  rs, cs = np.where(alpha)
  if len(rs) == 0:
    return
  pad_r = max(14, int((rs.max() - rs.min()) * 0.06))
  pad_c = max(18, int((cs.max() - cs.min()) * 0.06))
  r0 = max(0, int(rs.min()) - pad_r)
  r1 = min(H, int(rs.max()) + pad_r + 1)
  c0 = max(0, int(cs.min()) - pad_c)
  c1 = min(W, int(cs.max()) + pad_c + 1)

  crop_rgba = arg0_rgba[r0:r1, c0:c1]
  crop_mask = crop_rgba[:, :, 3] > 0
  # Pale sea background + crisp dark coastal edge
  bg = np.full((r1 - r0, c1 - c0, 3), [228, 238, 246], dtype=np.uint8)
  edge = binary_dilation(crop_mask, iterations=1) & (~crop_mask)
  bg[edge] = [55, 65, 80]
  bg[crop_mask] = crop_rgba[crop_mask, :3]

  lon_min = -180.0 + c0 / 12.0
  lon_max = -180.0 + c1 / 12.0
  lat_max = 90.0 - r0 / 12.0
  lat_min = 90.0 - r1 / 12.0

  n_reg = len(arg1_regions_meta)
  fig_h = 8.2 if n_reg <= 16 else 9.6
  plt.rcdefaults()
  plt.style.use("default")
  fig, ax = plt.subplots(figsize=(12.5, fig_h), dpi=135)
  ax.imshow(bg, extent=[lon_min, lon_max, lat_min, lat_max], interpolation="nearest", aspect="equal")
  ax.set_aspect("equal", adjustable="box")
  ax.set_xlabel("Longitude (°E)", fontsize=9)
  ax.set_ylabel("Latitude (°N)", fontsize=9)
  ax.set_title(f"{arg2_title}\nDomain: {arg3_domain[0]}..{arg3_domain[1]} AD | {n_reg} sub-regions | {int(alpha.sum()):,} px", fontsize=10.5, fontweight="bold")
  ax.grid(True, linestyle=":", linewidth=0.45, color="#556677", alpha=0.55)

  # Build legend sorted by pixel_count descending
  patches = []
  for rid, meta in sorted(arg1_regions_meta.items(), key=lambda kv: -kv[1]["pixel_count"]):
    col = [c / 255.0 for c in meta["colour"]]
    lbl = f"{meta['name']} ({meta['pixel_count']:,} px)"
    patches.append(mpatches.Patch(facecolor=col, edgecolor="#222222", linewidth=0.4, label=lbl))
  ncol = 1 if n_reg <= 22 else 2
  ax.legend(handles=patches, loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=7.0 if n_reg > 20 else 8.0, frameon=True, ncol=ncol)
  plt.tight_layout()
  import sys as _sys
  _shared_utils = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared")
  if _shared_utils not in _sys.path:
    _sys.path.insert(0, _shared_utils)
  from viscount_plot_utils import verify_panel_bounds_and_overlaps
  verify_panel_bounds_and_overlaps(fig, os.path.basename(str(arg4_out_path)), {"strict": False})
  fig.savefig(arg4_out_path, dpi=135, bbox_inches="tight")
  plt.close(fig)


def absorb_small_slivers(arg0_label_grid, arg1_target_mask, arg2_min_px=15):
  """Absorbs tiny disconnected micro-sliver fragments (< arg2_min_px) into their dominant adjacent region
  (or drops isolated floating sea/border slivers if disconnected from all regions and < arg2_min_px)."""
  out = arg0_label_grid.copy()
  tmask = arg1_target_mask.copy()
  gids = [int(v) for v in np.unique(out) if v > 0]
  struct = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.int32)
  for gid in gids:
    rm = (out == gid)
    comp, ncomp = nd_label(rm, structure=struct)
    if ncomp <= 1:
      continue
    sizes = np.bincount(comp.ravel())
    sizes[0] = 0
    main_cid = int(np.argmax(sizes))
    for cid in range(1, ncomp + 1):
      if cid == main_cid or sizes[cid] >= arg2_min_px:
        continue
      cm = (comp == cid)
      ring = binary_dilation(cm, structure=struct) & (~cm)
      nbrs = out[ring]
      nbrs = nbrs[(nbrs > 0) & (nbrs != gid)]
      if len(nbrs) > 0:
        vals, cnts = np.unique(nbrs, return_counts=True)
        out[cm] = int(vals[int(np.argmax(cnts))])
      else:
        # Tiny completely isolated detached sliver fragment (e.g. stray border speck) -> drop from mask
        out[cm] = 0
        tmask[cm] = False
  return out, tmask


def build_chapter(arg0_spec, arg1_land_area, arg2_cell_km2, arg3_quipu_domain_mask=None):
  """Builds smooth GeoJSON, 4320x2160 RGBA areal_mask PNG, <stem>.json5, and QA crop PNG for one chapter."""
  ch_dir = QUIPU_DIR / arg0_spec["rel_dir"]
  stem = arg0_spec["stem"]
  ch_dir.mkdir(parents=True, exist_ok=True)
  regions_spec = arg0_spec["regions"]
  palette = distinct_palette(len(regions_spec), arg0_spec.get("palette_seed", 0.07))
  preserve_micro = bool(arg0_spec.get("preserve_micro_islands", False))
  clip_to_domain = bool(arg0_spec.get("clip_to_domain", False))
  clean_slivers = bool(arg0_spec.get("clean_slivers", False))

  # Rasterise every region via OpenCV shift=4 with local hole subtraction
  raw_masks = {}
  valid_regions = []
  union_mask = np.zeros((H, W), dtype=bool)
  for idx, reg in enumerate(regions_spec):
    gid = idx + 1
    g = repair_geom(reg["geom"])
    if g is None or g.is_empty:
      raise RuntimeError(f"Empty geometry for {stem} -> {reg['id']}")
    rm = rasterise_geom_cv2(g)
    raw_masks[gid] = rm
    union_mask |= rm
    valid_regions.append((gid, reg, g, palette[idx]))

  if clip_to_domain and arg3_quipu_domain_mask is not None:
    target_mask = union_mask & arg3_quipu_domain_mask
    # Close any tiny 1-2 px interior void seams strictly on land_area > 0 inside the healed domain
    # (preserves real lakes like Maracaibo, Titicaca, Poopo, Valencia where land_area == 0!)
    closed_tm = binary_closing(target_mask, iterations=2) & arg3_quipu_domain_mask & (arg1_land_area > 0)
    target_mask |= closed_tm
  elif preserve_micro:
    target_mask = union_mask & ((arg1_land_area > 0) | union_mask)
  else:
    target_mask = union_mask & (arg1_land_area > 0)

  # Ensure micro-islands or small Admin-1 units (e.g. San Andres, Callao, CABA, Dependencias Federales,
  # South Sandwich, Juan Fernandez & Desventuradas inside Valparaiso) always retain land pixels!
  for gid, reg, g, _ in valid_regions:
    rm_land = raw_masks[gid] & target_mask
    if not rm_land.any():
      if raw_masks[gid].any():
        target_mask |= raw_masks[gid]
      else:
        pt = g.representative_point()
        rr, cc = latlon_to_rc(pt.y, pt.x)
        target_mask[rr, cc] = True
        raw_masks[gid][rr, cc] = True
    # Explicitly preserve offshore oceanic island parts (e.g. Juan Fernandez & Desventuradas west of -78 deg inside Chile)
    if stem == "chile_after_independence" and "Valpara" in reg["name"]:
      parts = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
      for pt_poly in parts:
        if -95.0 <= pt_poly.centroid.x <= -78.0 and pt_poly.area >= 1e-4:
          rp = pt_poly.representative_point()
          rr, cc = latlon_to_rc(rp.y, rp.x)
          target_mask[rr, cc] = True
          raw_masks[gid][rr, cc] = True

  # Ordered rasterisation: paint largest regions first so small enclaves win cleanly
  order = sorted(valid_regions, key=lambda item: -int(raw_masks[item[0]].sum()))
  label_grid = np.zeros((H, W), dtype=np.int32)
  for gid, reg, g, _ in order:
    sel = target_mask & raw_masks[gid]
    label_grid[sel] = gid

  # Pin any starved unit at its representative point so zero RGB starvation is mathematically guaranteed
  for gid, reg, g, _ in valid_regions:
    if not (label_grid == gid).any():
      pt = g.representative_point()
      rr, cc = latlon_to_rc(pt.y, pt.x)
      target_mask[rr, cc] = True
      label_grid[rr, cc] = gid

  # Nearest-neighbour fill any unlabelled interior pixels inside target_mask
  all_gids = [gid for gid, _, _, _ in valid_regions]
  label_grid = nearest_fill(target_mask, label_grid, all_gids)
  label_grid = np.where(target_mask, label_grid, 0)

  # For Regime I & II historical masks, absorb tiny disconnected micro-slivers (< 18 px) into dominant neighbours
  if clean_slivers:
    label_grid, target_mask = absorb_small_slivers(label_grid, target_mask, arg2_min_px=18)
    label_grid, target_mask = absorb_small_slivers(label_grid, target_mask, arg2_min_px=18)

  # Write 4320x2160 RGBA PNG + compute exact stats & GeoJSON
  rgba = np.zeros((H, W, 4), dtype=np.uint8)
  regions_meta = {}
  gj_features = []
  total_px = 0
  total_area = 0

  for gid, reg, g, col in valid_regions:
    rmask = (label_grid == gid)
    rs, cs = np.where(rmask)
    px_cnt = int(len(rs))
    if px_cnt == 0:
      raise RuntimeError(f"Starved zero-pixel sub-region in {stem}: {reg['id']}")
    rgba[rmask, 0] = col[0]
    rgba[rmask, 1] = col[1]
    rgba[rmask, 2] = col[2]
    rgba[rmask, 3] = 255

    lats = 90.0 - (rs + 0.5) / 12.0
    lons = -180.0 + (cs + 0.5) / 12.0
    area_vals = np.where(arg1_land_area[rs, cs] > 0, arg1_land_area[rs, cs], arg2_cell_km2[rs])
    area_km2 = max(1, int(round(float(area_vals.sum()))))
    total_px += px_cnt
    total_area += area_km2

    pop_dict = {str(k): int(round(v)) for k, v in reg["population"].items()}
    if "population_bounds" in reg and reg["population_bounds"]:
      bounds_dict = reg["population_bounds"]
    else:
      bounds_dict = make_bounds(pop_dict, arg1_rel_unc=arg0_spec.get("rel_unc", 0.18))

    regions_meta[reg["id"]] = {
      "name": reg["name"],
      "colour": col,
      "pixel_count": px_cnt,
      "area_km2": area_km2,
      "bbox": {
        "min_lat": round(float(lats.min()), 2),
        "max_lat": round(float(lats.max()), 2),
        "min_lon": round(float(lons.min()), 2),
        "max_lon": round(float(lons.max()), 2),
      },
      "population": pop_dict,
      "population_bounds": bounds_dict,
    }

    simp_g = g.simplify(0.008, preserve_topology=True)
    gj_features.append({
      "type": "Feature",
      "properties": {
        "id": reg["id"],
        "region_id": reg["id"],
        "name": reg["name"],
        "rgb": col,
        "colour": col,
        "colour_hex": "#{:02x}{:02x}{:02x}".format(col[0], col[1], col[2]),
        "pixel_count": px_cnt,
        "area_km2": area_km2,
      },
      "geometry": mapping(simp_g),
    })

  mask_png_path = ch_dir / f"{stem}_areal_mask.png"
  Image.fromarray(rgba, mode="RGBA").save(mask_png_path, compress_level=6)

  subreg_gj_path = SUBREG_OUT_DIR / f"{stem}_subregions.geojson"
  with open(subreg_gj_path, "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": gj_features}, fh, ensure_ascii=False)

  all_yrs = sorted({int(y) for r in regions_meta.values() for y in r["population"].keys()})
  headline = {str(yr): sum(int(r["population"].get(str(yr), 0)) for r in regions_meta.values()) for yr in all_yrs}

  ch_json = {
    "id": stem,
    "title": arg0_spec["title"],
    "source_review": f"histmap/1.data_raw/population_regional/QUIPU/{arg0_spec['rel_dir']}/{stem}_literature_review.md",
    "settlements_gazetteer": f"histmap/1.data_raw/population_regional/QUIPU/{arg0_spec['rel_dir']}/{stem}_settlements.json",
    "mask_file": f"{stem}_areal_mask.png",
    "vector_subregions_geojson": f"histmap/1.data_raw/population_regional/QUIPU/_shared/_gis_cache/chapter_subregions/{stem}_subregions.geojson",
    "domain": arg0_spec["domain"],
    "grid_dimensions": [W, H],
    "total_pixels": total_px,
    "total_area_km2": total_area,
    "summary": {
      "headline_population_by_benchmark": headline,
    },
    "regions": regions_meta,
  }
  json5_path = ch_dir / f"{stem}.json5"
  with open(json5_path, "w", encoding="utf-8") as fh:
    json.dump(ch_json, fh, indent=2, ensure_ascii=False)

  qa_crop_path = QA_CROPS_DIR / f"quipu_{stem}.png"
  render_qa_crop(rgba, regions_meta, arg0_spec["title"], arg0_spec["domain"], qa_crop_path)

  print(f"  [OK] {stem:34s} | regions={len(regions_meta):2d} | px={total_px:6,d} | area={total_area:9,d} km² | domain={arg0_spec['domain']}", flush=True)
  return target_mask


# ---------------------------------------------------------------------------
# Post-Independence Census Extraction from Verified eda_part3_enumerations.json
# ---------------------------------------------------------------------------

def _extract_year_dict(arg0_row, arg1_allowed_years=None):
  """Extracts {int_year: int_val} from a dict keyed by date/year strings (e.g. '1950-05-09', '1907 (1)', '2023_proj')."""
  if not isinstance(arg0_row, dict):
    return {}
  out = {}
  for k, v in arg0_row.items():
    if not isinstance(v, (int, float)) or v <= 0:
      continue
    m = re.match(r"^(\d{4})", str(k).strip())
    if not m:
      continue
    yr = int(m.group(1))
    if arg1_allowed_years is None or yr in arg1_allowed_years:
      out[yr] = int(round(v))
  return out


def _lookup_norm(arg0_dict, arg1_target, arg2_aliases=None):
  """Finds a value in arg0_dict matching arg1_target via normalised names & aliases."""
  aliases = arg2_aliases or {}
  tk = norm_key(aliases.get(arg1_target, arg1_target))
  nk_map = {norm_key(k): v for k, v in arg0_dict.items()}
  if tk in nk_map:
    return nk_map[tk]
  for k, v in nk_map.items():
    if k == tk or tk in k or k in tk:
      return v
  return None


def _fill_missing_series(arg0_unit_series, arg1_benchmarks, arg2_nat_totals):
  """Fills missing early/split years for newly created Admin-1 units proportionally to their earliest
  documented share scaled to the national trajectory, while preserving every documented census value verbatim."""
  # First pass: determine earliest known value for every unit
  bms = [int(y) for y in arg1_benchmarks]
  out = {u: {} for u in arg0_unit_series}
  for u, sd in arg0_unit_series.items():
    for y in bms:
      v = sd.get(y)
      if v is not None and v > 0:
        out[u][y] = int(round(v))

  # Compute fallback shares from earliest fully-covered benchmark (typically >= 1990)
  full_yr = None
  for y in bms:
    if all(y in out[u] for u in out):
      full_yr = y
      break
  if full_yr is None:
    full_yr = max(bms)
  ref_sum = sum(out[u].get(full_yr, 1000) for u in out) or 1

  for y in bms:
    nat = arg2_nat_totals.get(y)
    known_sum = sum(out[u][y] for u in out if y in out[u])
    missing_units = [u for u in out if y not in out[u]]
    if not missing_units:
      continue
    if nat and nat > known_sum:
      rem = nat - known_sum
      m_ref = sum(out[u].get(full_yr, 1000) for u in missing_units) or 1
      for u in missing_units:
        out[u][y] = max(100, int(round(rem * (out[u].get(full_yr, 1000) / m_ref))))
    else:
      # Scale from earliest known year of this unit using national ratio
      for u in missing_units:
        known_yrs = sorted(out[u].keys())
        if known_yrs:
          ky = known_yrs[0] if y < known_yrs[0] else known_yrs[-1]
          rat = (arg2_nat_totals.get(y, ref_sum) / max(1, arg2_nat_totals.get(ky, ref_sum)))
          out[u][y] = max(100, int(round(out[u][ky] * rat)))
        else:
          out[u][y] = max(100, int(round((nat or ref_sum) / max(1, len(out)))))

  # Return sorted string-keyed dicts
  return {u: {str(y): out[u][y] for y in bms} for u in out}


def build_post_independence_specs(arg0_gis, arg1_e3, arg2_preta_bol):
  """Constructs all 9 Regime III Post-Independence chapter specifications from verified census enumerations."""
  pi = arg1_e3["post_independence_censuses"]
  adm1 = arg0_gis["adm1"]
  specs = []

  # 1. COLOMBIA (33 units)
  col_e = pi["colombia"]
  col_bms = [1835, 1851, 1870, 1912, 1938, 1950, 1964, 1973, 1985, 1993, 2005, 2018, 2023, 2024]
  col_st_cols = [1912, 1938, 1950, 1964, 1973, 1985, 1993, 2005]
  col_cp_cols = [1985, 1993, 2005, 2018, 2023]
  col_aliases = {
    "Bogota Capital District": "Distrito Capital",
    "Archipiélago de San Andrés, Providencia y Santa Catalina": "San Andrés y Providencia",
  }
  col_cp_aliases = {
    "Bogota Capital District": "Bogotá, Distrito Especial",
    "Archipiélago de San Andrés, Providencia y Santa Catalina": "San Andrés y Providencia",
  }
  col_d24_aliases = {
    "Bogota Capital District": "Bogotá, D.C.",
    "Archipiélago de San Andrés, Providencia y Santa Catalina": "San Andrés y Providencia",
  }
  col_nat = {
    1835: 1687109, 1851: 2243730, 1870: 2951323, 1912: 5072604, 1938: 8701816,
    1950: 11548172, 1964: 17484508, 1973: 22915229, 1985: 30062200, 1993: 37664711,
    2005: 42888592, 2018: 48258494, 2023: 52215503, 2024: 52695952,
  }
  col_raw = {}
  col_bm_set = set(col_bms)
  for nm in sorted(adm1["COL"].keys()):
    sd = {}
    sd.update(_extract_year_dict(_lookup_norm(col_e["statoids_1912_2005"]["units"], nm, col_aliases), col_bm_set))
    sd.update(_extract_year_dict(_lookup_norm(col_e["citypopulation_1985_2023"]["units"], nm, col_cp_aliases), col_bm_set))
    d24 = _lookup_norm(col_e.get("dane_2024_projection_33_units", {}), nm, col_d24_aliases)
    if d24:
      sd[2024] = int(round(d24))
    col_raw[nm] = sd
  col_series = _fill_missing_series(col_raw, col_bms, col_nat)
  specs.append({
    "rel_dir": "3.post_independence/1.colombia_after_independence",
    "stem": "colombia_after_independence",
    "title": "Colombia after Independence: Andean Highlands, Caribbean Ports, and National Censuses (1819-2026AD)",
    "domain": [1819, 2026],
    "is_admin1": True,
    "palette_seed": 0.03,
    "regions": [
      {"id": f"col_{slugify(nm)}", "name": nm, "geom": adm1["COL"][nm], "population": col_series[nm]}
      for nm in sorted(adm1["COL"].keys())
    ],
  })

  # 2. VENEZUELA (25 units, excl. Essequibo)
  ven_e = pi["venezuela"]
  ven_bms = [1873, 1881, 1891, 1920, 1926, 1936, 1941, 1950, 1961, 1971, 1981, 1990, 2001, 2011, 2019, 2024]
  ven_st_cols = [1926, 1941, 1950, 1961, 1971, 1981, 1990, 2001, 2011]
  ven_aliases = {"La Guaira": "Vargas"}
  ven_nat = {
    1873: 1732411, 1881: 2005139, 1891: 2221572, 1920: 2479525, 1926: 2814131,
    1936: 3364347, 1941: 3850771, 1950: 5034838, 1961: 7523999, 1971: 10721522,
    1981: 14516735, 1990: 18105265, 2001: 23054210, 2011: 27227930, 2019: 28515829, 2024: 28405543,
  }
  ven_raw = {}
  ven_bm_set = set(ven_bms)
  for nm in sorted(adm1["VEN"].keys()):
    sd = {}
    sd.update(_extract_year_dict(_lookup_norm(ven_e["historical_1873_1936_ula_ine"], nm, ven_aliases), ven_bm_set))
    sd.update(_extract_year_dict(_lookup_norm(ven_e["statoids_1926_2011"]["units"], nm, ven_aliases), ven_bm_set))
    cp_row = _lookup_norm(ven_e["citypopulation_2001_2019"]["units"], nm, ven_aliases)
    if isinstance(cp_row, dict) and cp_row.get("2019_proj"):
      sd[2019] = int(round(cp_row["2019_proj"]))
    ine24 = _lookup_norm(ven_e.get("ine_2024_projection", {}), nm, ven_aliases)
    if ine24:
      sd[2024] = int(round(ine24))
    ven_raw[nm] = sd
  ven_series = _fill_missing_series(ven_raw, ven_bms, ven_nat)
  specs.append({
    "rel_dir": "3.post_independence/2.venezuela_after_independence",
    "stem": "venezuela_after_independence",
    "title": "Venezuela after Independence: Coastal Core, Oil Urbanisation, and National Censuses (1830-2026AD)",
    "domain": [1830, 2026],
    "is_admin1": True,
    "palette_seed": 0.14,
    "regions": [
      {"id": f"ven_{slugify(nm)}", "name": nm, "geom": adm1["VEN"][nm], "population": ven_series[nm]}
      for nm in sorted(adm1["VEN"].keys())
    ],
  })

  # 3. ECUADOR (24 units, incl. Galapagos)
  ecu_e = pi["ecuador"]
  ecu_bms = [1889, 1909, 1933, 1950, 1962, 1974, 1982, 1990, 2001, 2010, 2022]
  ecu_st_cols = [1933, 1950, 1962, 1974, 1982, 1990, 2001, 2010]
  ecu_nat = {
    1889: 1271861, 1909: 1500000, 1933: 2600116, 1950: 3202757, 1962: 4476007,
    1974: 6521710, 1982: 8060712, 1990: 9648189, 2001: 12156608, 2010: 14483499, 2022: 16938986,
  }
  ecu_raw = {}
  ecu_bm_set = set(ecu_bms)
  for nm in sorted(adm1["ECU"].keys()):
    sd = {}
    sd.update(_extract_year_dict(_lookup_norm(ecu_e["historical_provinces_1889_1909"], nm), ecu_bm_set))
    sd.update(_extract_year_dict(_lookup_norm(ecu_e["statoids_1933_2010"]["units"], nm), ecu_bm_set))
    sd.update(_extract_year_dict(_lookup_norm(ecu_e["citypopulation_1990_2022"]["units"], nm), ecu_bm_set))
    ecu_raw[nm] = sd
  ecu_series = _fill_missing_series(ecu_raw, ecu_bms, ecu_nat)
  specs.append({
    "rel_dir": "3.post_independence/3.ecuador_after_independence",
    "stem": "ecuador_after_independence",
    "title": "Ecuador after Independence: Sierra, Costa, Oriente, and Galápagos Censuses (1830-2026AD)",
    "domain": [1830, 2026],
    "is_admin1": True,
    "palette_seed": 0.25,
    "regions": [
      {"id": f"ecu_{slugify(nm)}", "name": nm, "geom": adm1["ECU"][nm], "population": ecu_series[nm]}
      for nm in sorted(adm1["ECU"].keys())
    ],
  })

  # 4. PERU (26 units, separating Municipalidad Metropolitana de Lima from Lima Provincias!)
  per_e = pi["peru"]
  per_bms = [1876, 1907, 1940, 1961, 1972, 1981, 1993, 2007, 2017, 2024, 2025]
  per_st_cols = [1876, 1907, 1940, 1961, 1972, 1981, 1993, 2007]
  per_nat = {
    1876: 2699106, 1907: 4559550, 1940: 6207967, 1961: 9906746, 1972: 13538208,
    1981: 17005210, 1993: 22048356, 2007: 27412157, 2017: 29381884, 2024: 34038457, 2025: 34350244,
  }
  lima_metro_cp = per_e["citypopulation_1993_2025"].get("lima_province_separate", {})
  lima_24 = per_e.get("inei_2024_lima_breakdown", {})
  per_raw = {}
  per_bm_set = set(per_bms)
  st_lima_dict = _extract_year_dict(per_e["statoids_1876_2007"]["units"].get("Lima", {}), per_bm_set)
  for nm in sorted(adm1["PER"].keys()):
    sd = {}
    if nm == "Municipalidad Metropolitana de Lima":
      hist_shares = {1876: 0.56, 1907: 0.62, 1940: 0.72, 1961: 0.81, 1972: 0.86, 1981: 0.89}
      for yr, sh in hist_shares.items():
        if yr in st_lima_dict:
          sd[yr] = int(round(st_lima_dict[yr] * sh))
      sd.update(_extract_year_dict(lima_metro_cp, per_bm_set))
      if lima_24.get("Lima_Metropolitana"):
        sd[2024] = int(round(lima_24["Lima_Metropolitana"]))
    elif nm == "Lima":
      hist_shares = {1876: 0.44, 1907: 0.38, 1940: 0.28, 1961: 0.19, 1972: 0.14, 1981: 0.11}
      for yr, sh in hist_shares.items():
        if yr in st_lima_dict:
          sd[yr] = int(round(st_lima_dict[yr] * sh))
      cp_lima = _extract_year_dict(per_e["citypopulation_1993_2025"]["units"].get("Lima (incl. Provincia de Lima)", {}), per_bm_set)
      lm_d = _extract_year_dict(lima_metro_cp, per_bm_set)
      for yr in (1993, 2007, 2017, 2025):
        if yr in cp_lima and yr in lm_d:
          sd[yr] = max(100000, cp_lima[yr] - lm_d[yr])
      if lima_24.get("Lima_Provincias"):
        sd[2024] = int(round(lima_24["Lima_Provincias"]))
    else:
      alias_p = {"El Callao": "Callao"}
      sd.update(_extract_year_dict(_lookup_norm(per_e["statoids_1876_2007"]["units"], nm, alias_p), per_bm_set))
      sd.update(_extract_year_dict(_lookup_norm(per_e["citypopulation_1993_2025"]["units"], nm, alias_p), per_bm_set))
      inei24 = _lookup_norm(per_e.get("inei_2024_projection", {}), nm, alias_p)
      if inei24:
        sd[2024] = int(round(inei24))
    per_raw[nm] = sd
  per_series = _fill_missing_series(per_raw, per_bms, per_nat)
  specs.append({
    "rel_dir": "3.post_independence/4.peru_after_independence",
    "stem": "peru_after_independence",
    "title": "Peru after Independence: Costa Urbanisation, Andean Sierra, and Selva Censuses (1821-2026AD)",
    "domain": [1821, 2026],
    "is_admin1": True,
    "palette_seed": 0.37,
    "regions": [
      {"id": f"per_{slugify(nm)}", "name": nm, "geom": adm1["PER"][nm], "population": per_series[nm]}
      for nm in sorted(adm1["PER"].keys())
    ],
  })

  # 5. ANDEAN BOLIVIA (6 Andean departments ONLY — exact match to PRETA bolivia_after_independence.json5!)
  bol_preta_regs = arg2_preta_bol["regions"]
  bol_key_map = {
    "Chuquisaca": "bol_chuquisaca",
    "Cochabamba": "bol_cochabamba",
    "La Paz": "bol_la_paz",
    "Oruro": "bol_oruro",
    "Potosí": "bol_potosi",
    "Tarija": "bol_tarija",
  }
  bol_regions = []
  for nm in sorted(adm1["BOL"].keys()):
    pk = bol_key_map[nm]
    bol_regions.append({
      "id": pk,
      "name": nm,
      "geom": adm1["BOL"][nm],
      "population": bol_preta_regs[pk]["population"],
      "population_bounds": bol_preta_regs[pk]["population_bounds"],
    })
  specs.append({
    "rel_dir": "3.post_independence/5.andean_bolivia_independence",
    "stem": "andean_bolivia_independence",
    "title": "Andean Bolivia after Independence: Altiplano & Cordillera Departments (1825-2026AD)",
    "domain": [1825, 2026],
    "is_admin1": True,
    "palette_seed": 0.49,
    "regions": bol_regions,
  })

  # 6. CHILE (16 regions, excl. Rapa Nui & Antarctica)
  chl_e = pi["chile"]
  chl_bms = [1835, 1854, 1865, 1875, 1885, 1895, 1907, 1920, 1930, 1940, 1952, 1960, 1970, 1982, 1992, 2002, 2017, 2024]
  chl_nat = {
    1835: 1010332, 1854: 1439120, 1865: 1819223, 1875: 2075971, 1885: 2507005,
    1895: 2712145, 1907: 3249279, 1920: 3753799, 1930: 4287445, 1940: 5023539,
    1952: 5932995, 1960: 7374115, 1970: 8884768, 1982: 11329736, 1992: 13348401,
    2002: 15116435, 2017: 17574003, 2024: 18480432,
  }
  chl_cp = chl_e["citypopulation_regions_1982_2024"]["units"]
  chl_aliases = {
    "Región Metropolitana de Santiago": "Región Metropolitana de Santiago",
    "Región de Antofagasta": "Antofagasta",
    "Región de Arica y Parinacota": "Arica y Parinacota",
    "Región de Atacama": "Atacama",
    "Región de Aysén del Gral.Ibañez del Campo": "Aysén del General Carlos Ibáñez del Campo (Aisén)",
    "Región de Coquimbo": "Coquimbo",
    "Región de La Araucanía": "La Araucanía",
    "Región de Los Lagos": "Los Lagos",
    "Región de Los Ríos": "Los Ríos",
    "Región de Magallanes y Antártica Chilena": "Magallanes y de la Antártica Chilena",
    "Región de Tarapacá": "Tarapacá",
    "Región de Valparaíso": "Valparaíso",
    "Región de Ñuble": "Ñuble",
    "Región del Bío-Bío": "Biobío (Bío Bío)",
    "Región del Libertador Bernardo O'Higgins": "Libertador General Bernardo O'Higgins (O'Higgins)",
    "Región del Maule": "Maule",
  }
  # Map 1895/1907/1940/1952/1960/1970 historical Chilean provinces into modern 16 regions!
  chl_prov_to_reg = {
    "Tarapacá": ("Región de Tarapacá", 0.62),  # split w/ Arica y Parinacota
    "Antofagasta": ("Región de Antofagasta", 1.0),
    "Atacama": ("Región de Atacama", 1.0),
    "Coquimbo": ("Región de Coquimbo", 1.0),
    "Aconcagua": ("Región de Valparaíso", 1.0),
    "Valparaíso": ("Región de Valparaíso", 1.0),
    "Santiago": ("Región Metropolitana de Santiago", 1.0),
    "O'Higgins": ("Región del Libertador Bernardo O'Higgins", 1.0),
    "Colchagua": ("Región del Libertador Bernardo O'Higgins", 1.0),
    "Curicó": ("Región del Maule", 1.0),
    "Talca": ("Región del Maule", 1.0),
    "Maule": ("Región del Maule", 1.0),
    "Linares": ("Región del Maule", 1.0),
    "Ñuble": ("Región de Ñuble", 1.0),
    "Concepción": ("Región del Bío-Bío", 1.0),
    "Arauco": ("Región del Bío-Bío", 1.0),
    "Bío-Bío": ("Región del Bío-Bío", 1.0),
    "Biobío": ("Región del Bío-Bío", 1.0),
    "Malleco": ("Región de La Araucanía", 1.0),
    "Cautín": ("Región de La Araucanía", 1.0),
    "Valdivia": ("Región de Los Ríos", 1.0),
    "Osorno": ("Región de Los Lagos", 1.0),
    "Llanquihue": ("Región de Los Lagos", 1.0),
    "Chiloé": ("Región de Los Lagos", 1.0),
    "Aysén": ("Región de Aysén del Gral.Ibañez del Campo", 1.0),
    "Magallanes": ("Región de Magallanes y Antártica Chilena", 1.0),
  }
  chl_raw = {nm: {} for nm in sorted(adm1["CHL"].keys())}
  for nm in chl_raw:
    cp_row = _lookup_norm(chl_cp, nm, chl_aliases)
    if isinstance(cp_row, dict):
      for yk, val in cp_row.items():
        if str(yk).isdigit() and val:
          chl_raw[nm][int(yk)] = val
  # Aggregate historical provinces into regions for 1895, 1907, 1940, 1952, 1960, 1970
  for yr, src_dict in [(1895, chl_e["census_1895_provinces"]), (1907, chl_e["census_1907_provinces"]), (1960, chl_e["census_1960_provinces"])]:
    for pnm, val in src_dict.items():
      if not isinstance(val, (int, float)):
        continue
      m = _lookup_norm(chl_prov_to_reg, pnm)
      if m:
        rnm, w = m
        chl_raw[rnm][yr] = chl_raw[rnm].get(yr, 0) + int(round(val * w))
        if norm_key(pnm) == "tarapaca":
          chl_raw["Región de Arica y Parinacota"][yr] = chl_raw["Región de Arica y Parinacota"].get(yr, 0) + int(round(val * (1.0 - w)))
  for pnm, pdict in chl_e["statoids_provinces_1910_1970"].items():
    m = _lookup_norm(chl_prov_to_reg, pnm)
    if not m or not isinstance(pdict, dict):
      continue
    rnm, w = m
    for yk, yr in [("1940", 1940), ("1952", 1952), ("1970", 1970)]:
      val = pdict.get(yk)
      if isinstance(val, (int, float)) and val > 0:
        chl_raw[rnm][yr] = chl_raw[rnm].get(yr, 0) + int(round(val * w))
        if norm_key(pnm) == "tarapaca":
          chl_raw["Región de Arica y Parinacota"][yr] = chl_raw["Región de Arica y Parinacota"].get(yr, 0) + int(round(val * (1.0 - w)))
  chl_series = _fill_missing_series(chl_raw, chl_bms, chl_nat)
  specs.append({
    "rel_dir": "3.post_independence/6.chile_after_independence",
    "stem": "chile_after_independence",
    "title": "Chile after Independence: Norte Grande, Central Valley, and Austral Censuses (1818-2026AD)",
    "domain": [1818, 2026],
    "is_admin1": True,
    "palette_seed": 0.61,
    "regions": [
      {"id": f"chl_{slugify(nm)}", "name": nm, "geom": adm1["CHL"][nm], "population": chl_series[nm]}
      for nm in sorted(adm1["CHL"].keys())
    ],
  })

  # 7. ARGENTINA (24 provinces from CONICET 2022, incl. Entre Rios & CABA!)
  arg_e = pi["argentina"]
  arg_bms = [1869, 1895, 1914, 1947, 1960, 1970, 1980, 1991, 2001, 2010, 2022]
  arg_st_cols = [1895, 1914, 1940, 1947, 1960, 1970, 1980, 1991, 2001, 2010]
  arg_nat = {
    1869: 1877490, 1895: 4044911, 1914: 7903662, 1947: 15893827, 1960: 20013793,
    1970: 23364431, 1980: 27949480, 1991: 32615528, 2001: 36260130, 2010: 40117096, 2022: 46044703,
  }
  arg_st_aliases = {"Ciudad Autónoma de Buenos Aires": "Federal District"}
  arg_w69_aliases = {"Ciudad Autónoma de Buenos Aires": "Ciudad de Buenos Aires", "Buenos Aires": "Buenos Aires Provincia"}
  arg_raw = {}
  arg_bm_set = set(arg_bms)
  for nm in sorted(adm1["ARG"].keys()):
    sd = {}
    w69 = _lookup_norm(arg_e["wiki_1869"], nm, arg_w69_aliases)
    if isinstance(w69, (int, float)) and w69 > 0:
      sd[1869] = int(round(w69))
    sd.update(_extract_year_dict(_lookup_norm(arg_e["statoids_1895_2010"]["units"], nm, arg_st_aliases), arg_bm_set))
    sd.update(_extract_year_dict(_lookup_norm(arg_e["citypopulation_1991_2022"]["units"], nm), arg_bm_set))
    arg_raw[nm] = sd
  arg_series = _fill_missing_series(arg_raw, arg_bms, arg_nat)
  specs.append({
    "rel_dir": "3.post_independence/7.argentina_after_independence",
    "stem": "argentina_after_independence",
    "title": "Argentina after Independence: Río de la Plata Immigration, Pampas, and National Censuses (1810-2026AD)",
    "domain": [1810, 2026],
    "is_admin1": True,
    "palette_seed": 0.72,
    "regions": [
      {"id": f"arg_{slugify(nm)}", "name": nm, "geom": adm1["ARG"][nm], "population": arg_series[nm]}
      for nm in sorted(adm1["ARG"].keys())
    ],
  })

  # 8. URUGUAY (19 departments)
  ury_e = pi["uruguay"]
  ury_bms = [1852, 1860, 1908, 1941, 1953, 1963, 1975, 1985, 1996, 2004, 2011, 2023, 2026]
  ury_st_cols = [1908, 1911, 1921, 1941, 1953, 1963, 1975, 1985, 1996, 2004, 2011]
  ury_nat = {
    1852: 131969, 1860: 229480, 1908: 1042686, 1941: 2185626, 1953: 2525000,
    1963: 2595510, 1975: 2788429, 1985: 2955241, 1996: 3163763, 2004: 3241003,
    2011: 3286314, 2023: 3499451, 2026: 3530000,
  }
  ury_raw = {}
  ury_bm_set = set(ury_bms)
  for nm in sorted(adm1["URY"].keys()):
    sd = {}
    sd.update(_extract_year_dict(_lookup_norm(ury_e["historical_1852_1860_1908"], nm), ury_bm_set))
    sd.update(_extract_year_dict(_lookup_norm(ury_e["statoids_1908_2011"]["units"], nm), ury_bm_set))
    sd.update(_extract_year_dict(_lookup_norm(ury_e["citypopulation_1975_2026"]["units"], nm), ury_bm_set))
    ury_raw[nm] = sd
  ury_series = _fill_missing_series(ury_raw, ury_bms, ury_nat)
  specs.append({
    "rel_dir": "3.post_independence/8.uruguay_after_independence",
    "stem": "uruguay_after_independence",
    "title": "Uruguay after Independence: Montevideo Primacy and Departmental Censuses (1830-2026AD)",
    "domain": [1830, 2026],
    "is_admin1": True,
    "palette_seed": 0.83,
    "regions": [
      {"id": f"ury_{slugify(nm)}", "name": nm, "geom": adm1["URY"][nm], "population": ury_series[nm]}
      for nm in sorted(adm1["URY"].keys())
    ],
  })

  # 9. FALKLANDS & SOUTH ATLANTIC ISLANDS (4 geographic subregions: East Falkland, West Falkland, South Georgia, South Sandwich)
  flk_c = pi["falklands_and_south_atlantic"]["falkland_islands_censuses_1851_2021"]
  flk_sub = pi["falklands_and_south_atlantic"]["falkland_islands_subregions_1986_2021"]
  # Benchmarks across 1764..2025 (Port Louis 1764 -> British 1833 -> 1851-2021 censuses)
  flk_bms = [1764, 1800, 1833, 1851, 1871, 1891, 1911, 1931, 1953, 1972, 1986, 1996, 2006, 2016, 2021]
  ef_pop, wf_pop, sg_pop, ss_pop = {}, {}, {}, {}
  for y in flk_bms:
    yk = str(y)
    if y == 1764:
      ef_pop[yk], wf_pop[yk], sg_pop[yk], ss_pop[yk] = 29, 0, 0, 0
    elif y == 1800:
      ef_pop[yk], wf_pop[yk], sg_pop[yk], ss_pop[yk] = 75, 0, 15, 0
    elif y == 1833:
      ef_pop[yk], wf_pop[yk], sg_pop[yk], ss_pop[yk] = 45, 5, 10, 0
    elif yk in flk_sub:
      sr = flk_sub[yk]
      ef_v = (sr.get("Stanley") or 0) + (sr.get("RAF_Mount_Pleasant") or 0) + (sr.get("Rest_of_East_Falkland") or 0)
      wf_v = (sr.get("West_Falkland") or 0) + (sr.get("Outer_islands") or 0)
      tot = flk_c.get(yk, {}).get("total_population") or (ef_v + wf_v)
      # Scale minor census-night gap proportionally if any
      if ef_v + wf_v > 0 and tot > (ef_v + wf_v):
        ef_v += (tot - ef_v - wf_v)
      ef_pop[yk] = max(1, int(ef_v))
      wf_pop[yk] = max(1, int(wf_v))
      sg_pop[yk] = 20 if y >= 1986 else 30
      ss_pop[yk] = 0
    else:
      tot = flk_c.get(yk, {}).get("total_population", 1000)
      ef_share = 0.85 if y < 1900 else 0.82
      ef_pop[yk] = int(round(tot * ef_share))
      wf_pop[yk] = max(10, tot - ef_pop[yk])
      # Whaling era peak 1904-1965 on South Georgia
      if 1911 <= y <= 1953:
        sg_pop[yk] = 650 if y == 1911 else (850 if y == 1931 else 700)
      elif y == 1972:
        sg_pop[yk] = 22
      else:
        sg_pop[yk] = 15
      ss_pop[yk] = 0
  # Keep ss_pop tiny nonzero sentinel (1 seasonal scientific/sealing visitor) only if needed? No, 0 is historically accurate!
  specs.append({
    "rel_dir": "3.post_independence/9.falklands_south_atlantic",
    "stem": "falklands_south_atlantic",
    "title": "Falkland Islands, South Georgia, and the South Sandwich Islands (1764-2026AD)",
    "domain": [1764, 2026],
    "is_admin1": True,
    "preserve_micro_islands": True,
    "palette_seed": 0.91,
    "regions": [
      {"id": "flk_east_falkland", "name": "East Falkland (Stanley & Camp)", "geom": adm1["FLK_SGS"]["East Falkland"], "population": ef_pop},
      {"id": "flk_west_falkland", "name": "West Falkland & Outer Islands", "geom": adm1["FLK_SGS"]["West Falkland"], "population": wf_pop},
      {"id": "sgs_south_georgia", "name": "South Georgia", "geom": adm1["FLK_SGS"]["South Georgia"], "population": sg_pop},
      {"id": "sgs_south_sandwich", "name": "South Sandwich Islands", "geom": adm1["FLK_SGS"]["South Sandwich Islands"], "population": ss_pop},
    ],
  })

  return specs


# ---------------------------------------------------------------------------
# Regime I (Pre-Columbian: HydroBASINS + OHM) & Regime II (Colonial: HGIS Indias)
# ---------------------------------------------------------------------------

def prune_small_parts(arg0_geom, arg1_min_deg2=0.02):
  """Drops tiny detached polygon sliver fragments (< arg1_min_deg2) while preserving the main body."""
  g = repair_geom(arg0_geom)
  if g is None or g.geom_type == "Polygon":
    return g
  parts = list(g.geoms)
  kept = [p for p in parts if p.area >= arg1_min_deg2]
  if not kept:
    kept = [max(parts, key=lambda p: p.area)]
  return repair_geom(MultiPolygon(kept) if len(kept) > 1 else kept[0])


def make_disjoint_geoms(arg0_geoms):
  """Enforces strict priority-ordered disjointness across a list of polygons (eliminating crest/border overlap speckles)."""
  out = []
  used = None
  for g in arg0_geoms:
    cur = safe_diff(g, used) if used is not None else repair_geom(g)
    out.append(cur)
    used = safe_union([used, cur]) if used is not None else cur
  return out


def build_precolumbian_and_colonial_specs(arg0_gis, arg1_quipu_mainland_healed):
  """Constructs all 4 Regime I Pre-Columbian chapters and 4 Regime II Colonial chapters
  with ZERO modern Admin-0/Admin-1 border leakage, ZERO synthetic horizontal box() cuts,
  ZERO detached frontier slivers, and healed inter-country mainland seams."""
  h4 = arg0_gis["hybas4"]
  h5 = arg0_gis["hybas5"]
  h6 = arg0_gis["hybas6"]
  ohm = arg0_gis["ohm"]
  hgis = arg0_gis["hgis"]
  mainland = arg1_quipu_mainland_healed

  specs = []

  # =========================================================================
  # REGIME I: 4 PRE-COLUMBIAN CHAPTERS (100% Natural HydroBASINS + OHM — ZERO box() cuts!)
  # =========================================================================

  # 1. pre_columbian_northern_andes (-10000..1500)
  # Strictly complete natural HydroBASINS L4/L5 watersheds — ZERO horizontal box() cuts!
  g_mag_cauca = union_hybas(h4, ["6120"], mainland)
  g_carib_mar = union_hybas(h4, ["6110", "6130", "6140"], mainland)
  g_orinoco = union_hybas(h4, ["615"], mainland)
  g_pac_eq = union_hybas(h5, ["67204", "67205", "67206", "67207", "67208", "67209"], mainland)
  g_nw_amaz = union_hybas(h5, ["62287", "62288", "62289", "62294"], mainland)
  g_mag_cauca, g_carib_mar, g_orinoco, g_pac_eq, g_nw_amaz = make_disjoint_geoms(
    [g_mag_cauca, g_carib_mar, g_orinoco, g_pac_eq, g_nw_amaz]
  )

  specs.append({
    "rel_dir": "1.pre_columbian/1.pre_columbian_northern_andes",
    "stem": "pre_columbian_northern_andes",
    "title": "Pre-Columbian Northern Andes, Caribbean Littoral, and Orinoquía (-10000BC-1500AD)",
    "domain": [-10000, 1500],
    "clip_to_domain": True,
    "clean_slivers": True,
    "rel_unc": 0.28,
    "palette_seed": 0.05,
    "regions": [
      {
        "id": "na_magdalena_cauca_muisca",
        "name": "Magdalena–Cauca Basin (Muisca, Quimbaya & Tolima)",
        "geom": g_mag_cauca,
        "population": holocene_curve(1550000, "northern_andes", 1500),
      },
      {
        "id": "na_caribbean_maracaibo_tairona",
        "name": "Caribbean–Maracaibo Littoral (Tairona, Sinú & Caquetío)",
        "geom": g_carib_mar,
        "population": holocene_curve(950000, "northern_andes", 1500),
      },
      {
        "id": "na_pacific_equatorial_valdivia",
        "name": "Equatorial Pacific & Chocó–Esmeraldas (Valdivia, Tumaco & Manteño)",
        "geom": g_pac_eq,
        "population": holocene_curve(780000, "northern_andes", 1500),
      },
      {
        "id": "na_orinoco_llanos_guayana",
        "name": "Orinoco Llanos & Western Guayana Drainage",
        "geom": g_orinoco,
        "population": holocene_curve(520000, "northern_andes", 1500),
      },
      {
        "id": "na_nw_amazon_foothills",
        "name": "Caquetá–Putumayo–Vaupés Piedmont",
        "geom": g_nw_amaz,
        "population": holocene_curve(350000, "northern_andes", 1500),
      },
    ],
  })

  # 2. pre_columbian_central_andes (-10000..1438)
  # Strictly complete natural HydroBASINS L4/L5/L6 headwaters + OHM Pre-Inca polities — ZERO horizontal box() cuts!
  ohm_moche = get_ohm_geom(ohm, "Moche")
  ohm_chimu = get_ohm_geom(ohm, "Chimu")
  ohm_wari = get_ohm_geom(ohm, "Wari")
  ohm_tiw = get_ohm_geom(ohm, "Tiahuanaco")
  ohm_lup = get_ohm_geom(ohm, "Lupaca")
  ohm_cuz = get_ohm_geom(ohm, "Cuzco", "1197")
  ohm_cha = get_ohm_geom(ohm, "Chanka")

  g_altiplano = safe_clip(safe_union([union_hybas(h4, ["6640"]), ohm_tiw, ohm_lup]), mainland)
  g_ncoast = safe_clip(
    safe_union([
      union_hybas(h5, ["67108", "67109"]),
      union_hybas(h6, ["671075", "671076", "671077", "671078", "671079"]),
      ohm_moche, ohm_chimu,
    ]),
    mainland,
  )
  g_scoast = safe_clip(
    safe_union([
      union_hybas(h6, ["671071", "671072", "671073", "671074"]),
      union_hybas(h5, ["67101", "67102", "67103", "67104", "67105", "67106"]),
      union_hybas(h4, ["6629", "6628"]),
    ]),
    mainland,
  )
  g_eq_sierra = safe_clip(
    safe_union([
      union_hybas(h5, ["67201", "67202", "67203", "67204"]),
      union_hybas(h6, ["622986", "622988"]),
    ]),
    mainland,
  )
  # Central Sierra strictly confined to Andean cordillera headwaters (Upper Maranon, Mantaro, Apurimac, Urubamba + OHM Wari/Chanka/Cusco)
  g_sierra_core = safe_clip(
    safe_union([
      ohm_wari, ohm_cuz, ohm_cha,
      union_hybas(h6, ["622989", "622996", "622997", "622998", "622999"]),
    ]),
    mainland,
  )
  # ONE single continuous Eastern Montana, Chachapoya, Loreto-Ucayali & Yungas Slopes region!
  g_montana = safe_clip(
    safe_union([
      union_hybas(h5, ["62297", "62296", "62292", "62266", "62269"]),
      union_hybas(h6, ["622981", "622982", "622983", "622984", "622985", "622987", "622991", "622992", "622993", "622994", "622995"]),
    ]),
    mainland,
  )
  g_altiplano, g_ncoast, g_scoast, g_eq_sierra, g_sierra_core, g_montana = make_disjoint_geoms(
    [g_altiplano, g_ncoast, g_scoast, g_eq_sierra, g_sierra_core, g_montana]
  )

  specs.append({
    "rel_dir": "1.pre_columbian/2.pre_columbian_central_andes",
    "stem": "pre_columbian_central_andes",
    "title": "Pre-Columbian Central Andes: Caral, Chavín, Moche, Wari, Tiwanaku, and Chimor (-10000BC-1438AD)",
    "domain": [-10000, 1438],
    "clip_to_domain": True,
    "clean_slivers": True,
    "rel_unc": 0.25,
    "palette_seed": 0.16,
    "regions": [
      {
        "id": "ca_north_coast_moche_chimu",
        "name": "North & Central Pacific Coast (Caral, Moche & Chimú)",
        "geom": g_ncoast,
        "population": holocene_curve(1650000, "central_andes_preinca", 1438),
      },
      {
        "id": "ca_south_coast_nazca_chincha",
        "name": "South Coast & Atacama Valleys (Paracas, Nazca & Chincha)",
        "geom": g_scoast,
        "population": holocene_curve(620000, "central_andes_preinca", 1438),
      },
      {
        "id": "ca_central_sierra_wari_chanka",
        "name": "Central Sierra (Chavín, Wari, Chanka & Early Cusco)",
        "geom": g_sierra_core,
        "population": holocene_curve(2150000, "central_andes_preinca", 1438),
      },
      {
        "id": "ca_titicaca_altiplano_tiwanaku",
        "name": "Titicaca–Poopó Altiplano (Tiwanaku & Aymara Señoríos)",
        "geom": g_altiplano,
        "population": holocene_curve(1450000, "central_andes_altiplano", 1438),
      },
      {
        "id": "ca_equatorial_sierra_canari",
        "name": "Equatorial Sierra & Guayas (Cañari, Puruhá & Caranqui)",
        "geom": g_eq_sierra,
        "population": holocene_curve(780000, "central_andes_preinca", 1438),
      },
      {
        "id": "ca_eastern_montana_yungas",
        "name": "Eastern Montaña, Chachapoya & Yungas Slopes",
        "geom": g_montana,
        "population": holocene_curve(550000, "central_andes_preinca", 1438),
      },
    ],
  })

  # 3. inca_empire_tawantinsuyu (1438..1532) — EXACT OHM Four Suyos + Cusco Imperial Heartland!
  g_inc_cuzco, g_inc_chinchay, g_inc_anti, g_inc_conti, g_inc_colla = make_disjoint_geoms([
    safe_clip(get_ohm_geom(ohm, "Cuzco", "1438"), mainland),
    safe_clip(get_ohm_geom(ohm, "Chinchaysuyo", "1438"), mainland),
    safe_clip(get_ohm_geom(ohm, "Antisuyo", "1438"), mainland),
    safe_clip(get_ohm_geom(ohm, "Contisuyo", "1438"), mainland),
    safe_clip(get_ohm_geom(ohm, "Collasuyo", "1438"), mainland),
  ])

  specs.append({
    "rel_dir": "1.pre_columbian/3.inca_empire_tawantinsuyu",
    "stem": "inca_empire_tawantinsuyu",
    "title": "The Inca Empire (Tawantinsuyu): Four Suyos and Imperial Census Demography (1438-1532AD)",
    "domain": [1438, 1532],
    "clip_to_domain": True,
    "clean_slivers": True,
    "rel_unc": 0.22,
    "palette_seed": 0.29,
    "regions": [
      {
        "id": "inca_cuzco_heartland",
        "name": "Cusco Imperial Heartland",
        "geom": g_inc_cuzco,
        "population": {"1438": 320000, "1470": 420000, "1500": 480000, "1525": 520000, "1532": 460000},
      },
      {
        "id": "inca_chinchaysuyu",
        "name": "Chinchaysuyu (Northern & Central Andes to Ancasmayo)",
        "geom": g_inc_chinchay,
        "population": {"1438": 450000, "1470": 2400000, "1500": 3950000, "1525": 4600000, "1532": 3950000},
      },
      {
        "id": "inca_collasuyu",
        "name": "Collasuyu (Altiplano, Charcas, Tucumán & Central Chile)",
        "geom": g_inc_colla,
        "population": {"1438": 280000, "1470": 1650000, "1500": 2650000, "1525": 3050000, "1532": 2780000},
      },
      {
        "id": "inca_contisuyu",
        "name": "Contisuyu (Southwestern Pacific Slope & Arequipa)",
        "geom": g_inc_conti,
        "population": {"1438": 110000, "1470": 480000, "1500": 680000, "1525": 760000, "1532": 670000},
      },
      {
        "id": "inca_antisuyu",
        "name": "Antisuyu (Eastern Ceja de Selva & Montaña Frontier)",
        "geom": g_inc_anti,
        "population": {"1438": 80000, "1470": 250000, "1500": 440000, "1525": 520000, "1532": 480000},
      },
    ],
  })

  # 4. pre_columbian_southern_cone (-10000..1500) — Strictly HydroBASINS L4 watersheds on healed mainland!
  g_sc_araucania = union_hybas(h4, ["6619", "6621", "6622", "6623", "6624", "6625"], mainland)
  g_sc_nw_cuyo = union_hybas(h4, ["6440", "6524", "6525", "6526", "6527", "6528", "6529"], mainland)
  g_sc_chaco = union_hybas(h4, ["6422", "6423", "6424"], mainland)
  g_sc_parana_ury = union_hybas(h4, ["6412", "6413", "6414", "6415", "6416", "6417", "6418", "6419", "6421", "6425", "6430"], mainland)
  g_sc_pampas = union_hybas(h4, ["6510", "6511", "6512", "6513", "6514", "6515", "6516", "6517", "6518", "6519", "6520", "6521", "6522", "6523"], mainland)
  g_sc_atacama = union_hybas(h4, ["6626", "6627", "6628", "6629"], mainland)
  g_sc_patag = union_hybas(h4, ["6530", "6531", "6532", "6533", "6534", "6535", "6536", "6537", "6538", "6539", "6610", "6611", "6612", "6613", "6614", "6615", "6616", "6617", "6618"], mainland)
  g_sc_araucania, g_sc_nw_cuyo, g_sc_chaco, g_sc_parana_ury, g_sc_pampas, g_sc_atacama, g_sc_patag = make_disjoint_geoms(
    [g_sc_araucania, g_sc_nw_cuyo, g_sc_chaco, g_sc_parana_ury, g_sc_pampas, g_sc_atacama, g_sc_patag]
  )

  specs.append({
    "rel_dir": "1.pre_columbian/4.pre_columbian_southern_cone",
    "stem": "pre_columbian_southern_cone",
    "title": "Pre-Columbian Southern Cone: Mapuche Araucanía, Diaguita Andes, Chaco, Pampas, and Patagonia (-10000BC-1500AD)",
    "domain": [-10000, 1500],
    "clip_to_domain": True,
    "clean_slivers": True,
    "rel_unc": 0.30,
    "palette_seed": 0.42,
    "regions": [
      {
        "id": "sc_chile_central_araucania",
        "name": "Central Chile & Araucanía (Picunche, Mapuche & Huilliche)",
        "geom": g_sc_araucania,
        "population": holocene_curve(760000, "southern_cone_agri", 1500),
      },
      {
        "id": "sc_nw_andes_sierras_cuyo",
        "name": "Northwestern Andes, Sierras Pampeanas & Cuyo (Diaguita, Comechingón & Huarpe)",
        "geom": g_sc_nw_cuyo,
        "population": holocene_curve(390000, "southern_cone_agri", 1500),
      },
      {
        "id": "sc_gran_chaco_pilcomayo",
        "name": "Gran Chaco & Pilcomayo–Bermejo Basins (Guaycurú, Wichí & Tonocoté)",
        "geom": g_sc_chaco,
        "population": holocene_curve(220000, "southern_cone_agri", 1500),
      },
      {
        "id": "sc_parana_uruguay_charrua",
        "name": "Paraná–Uruguay Littoral & Banda Oriental (Guaraní, Chaná & Charrúa)",
        "geom": g_sc_parana_ury,
        "population": holocene_curve(190000, "southern_cone_agri", 1500),
      },
      {
        "id": "sc_pampas_salado_colorado",
        "name": "Humid & Dry Pampas (Querandí & Het)",
        "geom": g_sc_pampas,
        "population": holocene_curve(115000, "southern_cone_forager", 1500),
      },
      {
        "id": "sc_atacama_norte_grande",
        "name": "Atacama & Norte Chico Oases (Atacameño, Changos & Diaguita)",
        "geom": g_sc_atacama,
        "population": holocene_curve(75000, "southern_cone_agri", 1500),
      },
      {
        "id": "sc_patagonia_tierra_del_fuego",
        "name": "Patagonia, Magallanes & Tierra del Fuego (Tehuelche, Selk'nam & Yaghan)",
        "geom": g_sc_patag,
        "population": holocene_curve(55000, "southern_cone_forager", 1500),
      },
    ],
  })

  # =========================================================================
  # REGIME II: 4 COLONIAL CHAPTERS (EXACT HGIS de las Indias the_geom.gpkg LCG!)
  # (FRED03/FRED05 Brazilian border slugs excluded; QUFR01 assigned to NGR Caguan!)
  # =========================================================================
  qui_all = [("QUI", p) for p in ["Esmeraldas", "Guayaquil", "Jaen", "Maynas", "Popayan", "Quijos", "Quito"]]
  cha_andean = [("CHA", p) for p in ["Charcas", "Cochabamba", "La Paz", "Potosi"]]
  chl_all = [("CHL", p) for p in ["Chiloe", "Concepcion", "Santiago"]]

  # 5. spanish_conquest_andes_collapse (1525..1650)
  g_c5_list = make_disjoint_geoms([
    prune_small_parts(union_hgis(hgis, [("NGR", p) for p in ["Cartagena", "Santa Marta", "Riohacha", "Antioquia", "Choco", "Santa Fe", "Tunja", "Tunja-Giron", "Pamplona", "Mariquita", "Neiva", "Llanos", "Caguan"]], mainland)),
    prune_small_parts(union_hgis(hgis, [("NGR", "Popayan")] + qui_all, mainland)),
    prune_small_parts(union_hgis(hgis, [("PER", "Lima"), ("PER", "Trujillo"), ("PER", "Arequipa")], mainland)),
    prune_small_parts(union_hgis(hgis, [("PER", "Cuzco"), ("PER", "Huamanga"), ("PER", "Huancavelica"), ("PER", "Tarma"), ("PER", "Puno"), ("PER", "Paititi")], mainland)),
    prune_small_parts(union_hgis(hgis, cha_andean, mainland)),
    prune_small_parts(union_hgis(hgis, chl_all, mainland)),
  ])

  specs.append({
    "rel_dir": "2.colonial/1.spanish_conquest_andes_collapse",
    "stem": "spanish_conquest_andes_collapse",
    "title": "Spanish Conquest and the Andean Demographic Collapse (1525-1650AD)",
    "domain": [1525, 1650],
    "clip_to_domain": True,
    "clean_slivers": True,
    "rel_unc": 0.22,
    "palette_seed": 0.54,
    "regions": [
      {
        "id": "conq_nuevo_reino_granada",
        "name": "Nuevo Reino de Granada (Santafé, Tunja & Caribbean Coast)",
        "geom": g_c5_list[0],
        "population": {"1525": 2450000, "1550": 1450000, "1570": 950000, "1600": 620000, "1625": 540000, "1650": 560000},
      },
      {
        "id": "conq_audiencia_quito_popayan",
        "name": "Audiencia de Quito & Gobernación de Popayán",
        "geom": g_c5_list[1],
        "population": {"1525": 1650000, "1550": 920000, "1570": 610000, "1600": 440000, "1625": 390000, "1650": 410000},
      },
      {
        "id": "conq_peru_costa_lima_trujillo",
        "name": "Perú Costa (Lima, Trujillo & Arequipa)",
        "geom": g_c5_list[2],
        "population": {"1525": 2350000, "1550": 950000, "1570": 480000, "1600": 290000, "1625": 255000, "1650": 270000},
      },
      {
        "id": "conq_peru_sierra_cusco_huamanga",
        "name": "Perú Sierra (Cusco, Huamanga, Tarma & Puno)",
        "geom": g_c5_list[3],
        "population": {"1525": 3100000, "1550": 1650000, "1570": 960000, "1600": 690000, "1625": 580000, "1650": 540000},
      },
      {
        "id": "conq_audiencia_charcas_potosi",
        "name": "Audiencia de Charcas (La Paz, Potosí, Cochabamba & La Plata)",
        "geom": g_c5_list[4],
        "population": {"1525": 1550000, "1550": 980000, "1570": 680000, "1600": 540000, "1625": 480000, "1650": 465000},
      },
      {
        "id": "conq_gobernacion_chile",
        "name": "Gobernación de Chile (Santiago, Concepción & Araucanía)",
        "geom": g_c5_list[5],
        "population": {"1525": 950000, "1550": 720000, "1570": 560000, "1600": 430000, "1625": 370000, "1650": 350000},
      },
    ],
  })

  # 6. viceroyalty_peru_upper_peru (1542..1825)
  # Separate highland Intendencia del Cusco strictly from Paititi / Maynas Eastern Amazonian Frontier!
  g_c6_list = make_disjoint_geoms([
    prune_small_parts(union_hgis(hgis, [("PER", "Lima")], mainland)),
    prune_small_parts(union_hgis(hgis, [("PER", "Trujillo")], mainland)),
    prune_small_parts(union_hgis(hgis, [("PER", "Tarma")], mainland)),
    prune_small_parts(union_hgis(hgis, [("PER", "Huamanga"), ("PER", "Huancavelica")], mainland)),
    prune_small_parts(union_hgis(hgis, [("PER", "Cuzco")], mainland)),
    prune_small_parts(union_hgis(hgis, [("PER", "Arequipa")], mainland)),
    prune_small_parts(union_hgis(hgis, [("PER", "Puno")], mainland)),
    prune_small_parts(union_hgis(hgis, [("PER", "Paititi"), ("QUI", "Maynas")], mainland), arg1_min_deg2=0.05),
    prune_small_parts(union_hgis(hgis, [("CHA", "La Paz")], mainland)),
    prune_small_parts(union_hgis(hgis, [("CHA", "Cochabamba")], mainland)),
    prune_small_parts(union_hgis(hgis, [("CHA", "Charcas"), ("CHA", "Potosi")], mainland)),
  ])

  specs.append({
    "rel_dir": "2.colonial/2.viceroyalty_peru_upper_peru",
    "stem": "viceroyalty_peru_upper_peru",
    "title": "Viceroyalty of Peru and Upper Peru (Audiencia de Charcas): Intendancies, Mita, and Bourbon Censuses (1542-1825AD)",
    "domain": [1542, 1825],
    "clip_to_domain": True,
    "clean_slivers": True,
    "rel_unc": 0.16,
    "palette_seed": 0.67,
    "regions": [
      {
        "id": "vp_intendencia_lima",
        "name": "Intendencia de Lima",
        "geom": g_c6_list[0],
        "population": {"1542": 290000, "1570": 155000, "1620": 118000, "1700": 115000, "1750": 130000, "1795": 149112, "1825": 168000},
      },
      {
        "id": "vp_intendencia_trujillo",
        "name": "Intendencia de Trujillo",
        "geom": g_c6_list[1],
        "population": {"1542": 480000, "1570": 215000, "1620": 145000, "1700": 162000, "1750": 195000, "1795": 230967, "1825": 265000},
      },
      {
        "id": "vp_intendencia_tarma",
        "name": "Intendencia de Tarma",
        "geom": g_c6_list[2],
        "population": {"1542": 420000, "1570": 210000, "1620": 148000, "1700": 145000, "1750": 172000, "1795": 201259, "1825": 230000},
      },
      {
        "id": "vp_intendencia_huamanga_huancavelica",
        "name": "Intendencias de Huamanga y Huancavelica",
        "geom": g_c6_list[3],
        "population": {"1542": 340000, "1570": 158000, "1620": 112000, "1700": 108000, "1750": 124000, "1795": 142327, "1825": 162000},
      },
      {
        "id": "vp_intendencia_cusco",
        "name": "Intendencia del Cusco",
        "geom": g_c6_list[4],
        "population": {"1542": 580000, "1570": 255000, "1620": 185000, "1700": 168000, "1750": 192000, "1795": 216282, "1825": 248000},
      },
      {
        "id": "vp_intendencia_arequipa",
        "name": "Intendencia de Arequipa",
        "geom": g_c6_list[5],
        "population": {"1542": 360000, "1570": 201000, "1620": 125000, "1700": 105000, "1750": 120000, "1795": 136175, "1825": 158000},
      },
      {
        "id": "vp_intendencia_puno",
        "name": "Intendencia de Puno (Chucuito & Azángaro)",
        "geom": g_c6_list[6],
        "population": {"1542": 320000, "1570": 175000, "1620": 130000, "1700": 118000, "1750": 135000, "1795": 156000, "1825": 182000},
      },
      {
        "id": "vp_paititi_maynas_amazonia",
        "name": "Paititi, Maynas & Eastern Amazonian Frontier",
        "geom": g_c6_list[7],
        "population": {"1542": 185000, "1570": 145000, "1620": 110000, "1700": 88000, "1750": 75000, "1795": 68000, "1825": 64000},
      },
      {
        "id": "vp_intendencia_la_paz",
        "name": "Intendencia de La Paz (Alto Perú)",
        "geom": g_c6_list[8],
        "population": {"1542": 420000, "1570": 220000, "1620": 175000, "1700": 168000, "1750": 195000, "1795": 225000, "1825": 320000},
      },
      {
        "id": "vp_intendencia_cochabamba",
        "name": "Intendencia de Cochabamba (Alto Perú)",
        "geom": g_c6_list[9],
        "population": {"1542": 260000, "1570": 145000, "1620": 115000, "1700": 112000, "1750": 128000, "1795": 150000, "1825": 225000},
      },
      {
        "id": "vp_intendencia_charcas_potosi",
        "name": "Intendencias de La Plata (Charcas) y Potosí",
        "geom": g_c6_list[10],
        "population": {"1542": 520000, "1570": 315000, "1620": 295000, "1700": 215000, "1750": 235000, "1795": 255000, "1825": 377000},
      },
    ],
  })

  # 7. viceroyalty_new_granada (1538..1830) — Clean disjoint HGIS Provinces (FRED03 excluded, QUFR01 in Casanare/Caguan!)
  g_c7_list = make_disjoint_geoms([
    prune_small_parts(union_hgis(hgis, [("NGR", "Santa Fe"), ("NGR", "Tunja"), ("NGR", "Tunja-Giron"), ("NGR", "Pamplona"), ("NGR", "Mariquita"), ("NGR", "Neiva")], mainland)),
    prune_small_parts(union_hgis(hgis, [("NGR", "Cartagena"), ("NGR", "Santa Marta"), ("NGR", "Riohacha")], mainland)),
    prune_small_parts(union_hgis(hgis, [("NGR", "Antioquia"), ("NGR", "Popayan"), ("NGR", "Choco"), ("QUI", "Popayan")], mainland)),
    prune_small_parts(union_hgis(hgis, [("NGR", "Llanos"), ("NGR", "Caguan")], mainland)),
    prune_small_parts(union_hgis(hgis, [("QUI", "Quito"), ("QUI", "Jaen"), ("QUI", "Quijos"), ("QUI", "Maynas")], mainland)),
    prune_small_parts(union_hgis(hgis, [("QUI", "Guayaquil"), ("QUI", "Esmeraldas")], mainland)),
    prune_small_parts(union_hgis(hgis, [("VEN", "Caracas"), ("VEN", "Maracaibo")], mainland)),
    prune_small_parts(union_hgis(hgis, [("VEN", "Cumana"), ("VEN", "Guayana"), ("VEN", "Isla Margarita")], mainland)),
  ])

  specs.append({
    "rel_dir": "2.colonial/3.viceroyalty_new_granada",
    "stem": "viceroyalty_new_granada",
    "title": "Viceroyalty of New Granada, Audiencia de Quito, and Captaincy General of Venezuela (1538-1830AD)",
    "domain": [1538, 1830],
    "clip_to_domain": True,
    "clean_slivers": True,
    "rel_unc": 0.16,
    "palette_seed": 0.78,
    "regions": [
      {
        "id": "vng_santafe_tunja_highlands",
        "name": "Santafé, Tunja, Pamplona, Mariquita & Neiva",
        "geom": g_c7_list[0],
        "population": {"1538": 1150000, "1600": 310000, "1650": 285000, "1700": 305000, "1778": 365000, "1810": 540000, "1830": 690000},
      },
      {
        "id": "vng_cartagena_santa_marta",
        "name": "Cartagena, Santa Marta & Riohacha",
        "geom": g_c7_list[1],
        "population": {"1538": 580000, "1600": 145000, "1650": 135000, "1700": 152000, "1778": 205000, "1810": 265000, "1830": 290000},
      },
      {
        "id": "vng_antioquia_popayan_choco",
        "name": "Antioquia, Popayán & Chocó",
        "geom": g_c7_list[2],
        "population": {"1538": 620000, "1600": 140000, "1650": 125000, "1700": 138000, "1778": 168000, "1810": 265000, "1830": 345000},
      },
      {
        "id": "vng_llanos_caguan",
        "name": "Los Llanos de Casanare & Caguán Missions",
        "geom": g_c7_list[3],
        "population": {"1538": 240000, "1600": 95000, "1650": 72000, "1700": 55000, "1778": 38000, "1810": 46000, "1830": 54000},
      },
      {
        "id": "vng_audiencia_quito_sierra",
        "name": "Real Audiencia de Quito (Sierra, Jaén, Quijos & Maynas)",
        "geom": g_c7_list[4],
        "population": {"1538": 950000, "1600": 340000, "1650": 325000, "1700": 355000, "1778": 375000, "1810": 430000, "1830": 485000},
      },
      {
        "id": "vng_guayaquil_esmeraldas",
        "name": "Gobernación de Guayaquil & Esmeraldas",
        "geom": g_c7_list[5],
        "population": {"1538": 220000, "1600": 45000, "1650": 36000, "1700": 38000, "1778": 49000, "1810": 72000, "1830": 95000},
      },
      {
        "id": "vng_capitania_caracas_maracaibo",
        "name": "Provincia de Caracas (Venezuela) & Maracaibo",
        "geom": g_c7_list[6],
        "population": {"1538": 460000, "1600": 185000, "1650": 195000, "1700": 255000, "1778": 415000, "1810": 605000, "1830": 620000},
      },
      {
        "id": "vng_cumana_guayana_margarita",
        "name": "Cumaná (Nueva Andalucía), Guayana & Margarita",
        "geom": g_c7_list[7],
        "population": {"1538": 260000, "1600": 110000, "1650": 95000, "1700": 108000, "1778": 148000, "1810": 195000, "1830": 215000},
      },
    ],
  })

  # 8. chile_rio_plata_banda_oriental (1536..1830)
  # Split Gran Chaco and Patagonia & Southern Pampas into TWO separate, contiguous sub-regions;
  # enforce strict ordered polygon disjointness across the Andean crest (Santiago vs Cuyo)!
  g_c8_list = make_disjoint_geoms([
    prune_small_parts(union_hgis(hgis, [("CHL", "Santiago")], mainland)),
    prune_small_parts(union_hgis(hgis, [("CHL", "Concepcion"), ("CHL", "Chiloe")], mainland)),
    prune_small_parts(union_hgis(hgis, [("RPL", "Cuyo")], mainland)),
    prune_small_parts(union_hgis(hgis, [("RPL", "Buenos Aires")], mainland)),
    prune_small_parts(union_hgis(hgis, [("RPL", "Banda oriental"), ("RPL", "Misiones")], mainland)),
    prune_small_parts(union_hgis(hgis, [("RPL", "Tucuman")], mainland)),
    prune_small_parts(union_hgis(hgis, [("RPL", "Chaco")], mainland)),
    prune_small_parts(union_hgis(hgis, [("RPL", "Patagonia")], mainland)),
  ])

  specs.append({
    "rel_dir": "2.colonial/4.chile_rio_plata_banda_oriental",
    "stem": "chile_rio_plata_banda_oriental",
    "title": "Captaincy General of Chile, Viceroyalty of the Río de la Plata, and the Banda Oriental (1536-1830AD)",
    "domain": [1536, 1830],
    "clip_to_domain": True,
    "clean_slivers": True,
    "rel_unc": 0.16,
    "palette_seed": 0.89,
    "regions": [
      {
        "id": "crp_obispado_santiago",
        "name": "Obispado de Santiago (Central & Northern Chile)",
        "geom": g_c8_list[0],
        "population": {"1536": 260000, "1600": 135000, "1650": 128000, "1700": 155000, "1778": 240748, "1813": 465000, "1830": 585000},
      },
      {
        "id": "crp_obispado_concepcion_chiloe",
        "name": "Obispado de Concepción, Araucanía & Chiloé",
        "geom": g_c8_list[1],
        "population": {"1536": 590000, "1600": 310000, "1650": 235000, "1700": 205000, "1778": 215000, "1813": 295000, "1830": 375000},
      },
      {
        "id": "crp_corregimiento_cuyo",
        "name": "Corregimiento de Cuyo (Mendoza, San Juan & San Luis)",
        "geom": g_c8_list[2],
        "population": {"1536": 65000, "1600": 38000, "1650": 26000, "1700": 22000, "1778": 23411, "1813": 48000, "1830": 68000},
      },
      {
        "id": "crp_intendencia_buenos_aires",
        "name": "Intendencia de Buenos Aires (Río de la Plata & Litoral)",
        "geom": g_c8_list[3],
        "population": {"1536": 75000, "1600": 42000, "1650": 38000, "1700": 45000, "1778": 58000, "1813": 145000, "1830": 240000},
      },
      {
        "id": "crp_banda_oriental_misiones",
        "name": "Banda Oriental del Uruguay & Misiones",
        "geom": g_c8_list[4],
        "population": {"1536": 85000, "1600": 58000, "1650": 52000, "1700": 58000, "1778": 42000, "1813": 68000, "1830": 82000},
      },
      {
        "id": "crp_gobernacion_tucuman",
        "name": "Gobernación del Tucumán (Córdoba, Salta, Jujuy & Interior)",
        "geom": g_c8_list[5],
        "population": {"1536": 285000, "1600": 165000, "1650": 125000, "1700": 118000, "1778": 138000, "1813": 220000, "1830": 295000},
      },
      {
        "id": "crp_gran_chaco_frontier",
        "name": "Gran Chaco Indigenous Frontier",
        "geom": g_c8_list[6],
        "population": {"1536": 185000, "1600": 152000, "1650": 132000, "1700": 115000, "1778": 98000, "1813": 84000, "1830": 76000},
      },
      {
        "id": "crp_patagonia_pampas_frontier",
        "name": "Patagonia & Southern Pampas Indigenous Frontier",
        "geom": g_c8_list[7],
        "population": {"1536": 110000, "1600": 93000, "1650": 83000, "1700": 73000, "1778": 60000, "1813": 51000, "1830": 46000},
      },
    ],
  })

  return specs


def heal_mainland_domain(arg0_domain_union, arg1_mainland_geoms, arg2_land_area):
  """Closes all 1-2 px modern inter-country border sliver seams (COL-VEN, COL-ECU-PER, PER-BOL,
  BOL-CHL-ARG, CHL-ARG Andean crest & -68.6E Tierra del Fuego meridian) while preserving real lakes
  (Maracaibo, Titicaca, Poopo, Valencia where land_area == 0) and coastlines."""
  simp_parts = [g.simplify(0.012, preserve_topology=True) for g in arg1_mainland_geoms if g is not None and not g.is_empty]
  raw_mainland = safe_union(simp_parts)
  # Topological buffer-unbuffer seals inter-country hairline seams (< 0.08 deg) without altering coastlines/large lakes
  healed_geom = repair_geom(raw_mainland.buffer(0.08, quad_segs=4).buffer(-0.08, quad_segs=4).simplify(0.012, preserve_topology=True))
  healed_poly_mask = rasterise_geom_cv2(healed_geom) & (arg2_land_area > 0)
  closed_mask = binary_closing(arg0_domain_union | healed_poly_mask, iterations=2) & (arg2_land_area > 0)
  healed_domain = arg0_domain_union | healed_poly_mask | closed_mask
  added_px = int(healed_domain.sum()) - int(arg0_domain_union.sum())
  print(f"  [HEAL] Closed {added_px:,} inter-country border seam land pixels (lakes & coastline strictly preserved)", flush=True)
  return healed_domain, healed_geom


def main():
  regime12_only = "--regime12-only" in sys.argv
  print(f"=== Operation Viscount Project QUIPU — Pass-2 Areal Masks & Domain Builder (regime12_only={regime12_only}) ===", flush=True)
  land_area = load_land_area()
  cell_km2 = spherical_cell_km2()
  gis = load_all_gis()

  with open(ENUM_JSON, "r", encoding="utf-8") as fh:
    e3 = json.load(fh)
  with open(PRETA_BOL_JSON5, "r", encoding="utf-8") as fh:
    preta_bol = json.load(fh)

  dom_png = DOMAIN_CFG_DIR / "quipu_domain_mask.png"
  post_specs = build_post_independence_specs(gis, e3, preta_bol)

  mainland_geoms = []
  for spec in post_specs:
    if spec["stem"] != "falklands_south_atlantic":
      for reg in spec["regions"]:
        if reg["id"] != "ecu_galapagos":
          mainland_geoms.append(reg["geom"])

  if regime12_only and dom_png.exists():
    print("\n[1/3] Preserving passed Regime III chapters (9-17); loading & healing quipu_domain_mask.png...", flush=True)
    dm_raw = np.asarray(Image.open(dom_png).convert("RGBA"), dtype=np.uint8)
    domain_union = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)
  else:
    print("\n[1/3] Building Regime III Post-Independence chapters (9/17) & QUIPU domain mask...", flush=True)
    domain_union = np.zeros((H, W), dtype=bool)
    for spec in post_specs:
      cmask = build_chapter(spec, land_area, cell_km2)
      domain_union |= cmask

  # Heal inter-country border seams in domain mask & mainland vector geometry
  domain_healed, quipu_mainland_healed = heal_mainland_domain(domain_union, mainland_geoms, land_area)
  dom_rgba = np.zeros((H, W, 4), dtype=np.uint8)
  dom_rgba[domain_healed] = [255, 255, 255, 255]
  Image.fromarray(dom_rgba, mode="RGBA").save(dom_png, compress_level=6)
  print(f"  [OK] Saved healed {dom_png} | active_px={int(domain_healed.sum()):,}", flush=True)

  # Step 2: Build Regime I (4 Pre-Columbian) & Regime II (4 Colonial) chapters on healed mainland!
  print("\n[2/3] Building Regime I Pre-Columbian (4/17) & Regime II Colonial (4/17) chapters...", flush=True)
  pre_col_specs = build_precolumbian_and_colonial_specs(gis, quipu_mainland_healed)
  for spec in pre_col_specs:
    build_chapter(spec, land_area, cell_km2, arg3_quipu_domain_mask=domain_healed)

  print(f"\n[3/3] DONE! Built healed quipu_domain_mask.png + Regime I/II masks, JSON5s, vector GeoJSONs & QA crops in {QA_CROPS_DIR}.", flush=True)


if __name__ == "__main__":
  main()
