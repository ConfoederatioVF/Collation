"""Operation Viscount Project AUSTRAL — Pass-2 Domain Mask, 16-Chapter Areal Masks,
Smooth Vector Sub-Region GeoJSONs, and Optical QA Crop Builder.

Builds:
  1. `AUSTRAL/_shared/sites_austral_oceania/config/austral_domain_mask.png` (4320x2160 RGB PNG)
     covering ALL AUSTRAL lands with pixel-for-pixel subtraction of MANDALA and CENTAUR
     (asserted 0 overlap pixels) and explicit micro-island centroid stamping.
  2. ALL 16 chapter areal masks (`*_areal_mask.png`), sibling `<stem>.json5` configs,
     and smooth vector `_shared/_gis_cache/chapter_subregions/<stem>_subregions.geojson`
     using:
       - Ch 01, 02, 05 (Regime I Precolonial): 100% organic HydroBASINS AU L6 watersheds
         (ZERO modern straight-line state/colonial borders!).
       - Ch 03, 04 (Regime I Precolonial Melanesia/Micronesia/Polynesia): Archipelago &
         cultural-ecological zones (strictly excluding Hawai'i & American Samoa).
       - Ch 06-11 (Regime II Colonial): Period-authentic OHM + Esri + dissolved NZ Provinces +
         tri-colonial New Guinea + Pacific colonial jurisdictions.
       - Ch 12-16 (Regime III Modern, `is_admin1: true`): Official Admin-1 boundaries across
         Australia, New Zealand, PNG (22), Indonesian Papua (6), Melanesia, Micronesia, Polynesia.
  3. `AUSTRAL/austral_areal_masks.json5` manifest.
  4. Regional optical QA crop PNGs for ALL 16 chapters in `tests/mask_crops/mask_ch<01..16>_<stem>.png`
     with continuous antimeridian wrapping (0..360 deg) for trans-180 Pacific chapters and ZERO
     modern borders on pre-1945 crops.
"""

import io
import json
import math
import os
import shutil
import sys
import zipfile
from collections import defaultdict

import cv2
import json5
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch, Polygon as MplPolygon
import numpy as np
import shapefile
from PIL import Image
from scipy.ndimage import distance_transform_edt
from shapely import set_precision
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box, mapping, shape
from shapely.ops import transform as shp_transform, unary_union
from shapely.validation import make_valid

GRID_W, GRID_H = 4320, 2160

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
AUSTRAL_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL")
SHARED_DIR = os.path.join(AUSTRAL_DIR, "_shared")
GIS_CACHE = os.path.join(SHARED_DIR, "_gis_cache")
SUB_GJ_DIR = os.path.join(GIS_CACHE, "chapter_subregions")
HGIS_RAW = os.path.join(SHARED_DIR, "subadmin_hgis", "raw_sources")
SITES_CFG_DIR = os.path.join(SHARED_DIR, "sites_austral_oceania", "config")
DOMAIN_MASK_PNG = os.path.join(SITES_CFG_DIR, "austral_domain_mask.png")

MANDALA_MASK_PNG = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MANDALA",
  "_shared", "sites_mandala_southeast_asia", "config", "mandala_domain_mask.png"
)
CENTAUR_MASK_PNG = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CENTAUR",
  "_shared", "sites_hawaii_polynesia", "config", "centaur_hp_domain_mask.png"
)
HYBAS_L6_ZIP = os.path.join(GIS_CACHE, "hybas_au_lev06_v1c.zip")
NE_ADMIN0_GJ = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared", "_gis_cache",
  "ne_10m_admin_0_countries.geojson"
)
TESTS_CROP_DIR = os.path.join(SVEA_ROOT, "tests", "mask_crops")

SHARED_UTILS = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared")
if SHARED_UTILS not in sys.path:
  sys.path.insert(0, SHARED_UTILS)
from viscount_plot_utils import apply_viscount_style, save_viscount_figure

os.makedirs(SUB_GJ_DIR, exist_ok=True)
os.makedirs(SITES_CFG_DIR, exist_ok=True)
os.makedirs(TESTS_CROP_DIR, exist_ok=True)

ALL_HYDE_YEARS = [
  -10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000,
  0, 100, 200, 300, 400, 500, 600, 700, 800, 900,
  1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
  1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790,
  1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890,
  1900, 1910, 1920, 1930, 1940, 1950,
] + list(range(1951, 2026))

# 48 perceptually distinct muted-cartographic RGB colours (zero duplicates even for 36-zone Ch 15!)
PALETTE = [
  [184, 105, 81],  [86, 134, 168],  [118, 158, 98],  [198, 152, 74],
  [146, 106, 162], [78, 156, 148],  [204, 118, 132], [134, 146, 86],
  [172, 128, 104], [96, 118, 174],  [164, 154, 88],  [192, 102, 106],
  [88, 148, 118],  [156, 116, 138], [122, 164, 184], [186, 142, 112],
  [108, 138, 94],  [168, 96, 124],  [142, 126, 166], [92, 158, 168],
  [210, 138, 92],  [74, 118, 142],  [152, 174, 108], [182, 122, 154],
  [116, 142, 162], [194, 168, 96],  [136, 98, 118],  [98, 168, 134],
  [176, 112, 96],  [124, 112, 176], [162, 142, 76],  [84, 142, 158],
  [202, 126, 114], [112, 154, 122], [158, 104, 144], [146, 162, 124],
  [188, 134, 84],  [94, 128, 154],  [174, 158, 118], [132, 118, 146],
  [104, 162, 156], [196, 112, 122], [128, 148, 98],  [166, 122, 118],
  [82, 132, 126],  [178, 148, 134], [118, 126, 164], [154, 138, 92],
]


def extract_polygonal(g):
  """Strictly extracts valid Polygon / MultiPolygon components from any Shapely geometry."""
  if g is None or g.is_empty:
    return None
  if isinstance(g, Polygon):
    return g if g.area > 0 else None
  if isinstance(g, MultiPolygon):
    ps = [p for p in g.geoms if not p.is_empty and p.area > 0]
    if not ps:
      return None
    return ps[0] if len(ps) == 1 else MultiPolygon(ps)
  if isinstance(g, GeometryCollection):
    ps = []
    for sub in g.geoms:
      ex = extract_polygonal(sub)
      if isinstance(ex, Polygon):
        ps.append(ex)
      elif isinstance(ex, MultiPolygon):
        ps.extend(ex.geoms)
    if not ps:
      return None
    return ps[0] if len(ps) == 1 else MultiPolygon(ps)
  return None


def safe_geom(g, snap_tol=0):
  """Full degenerate-topology repair: make_valid -> polygonal extract -> buffer(0) -> optional snap."""
  if g is None or g.is_empty:
    return None
  try:
    if not g.is_valid:
      g = make_valid(g)
    g = extract_polygonal(g)
    if g is None or g.is_empty:
      return None
    g = g.buffer(0)
    g = extract_polygonal(g)
    if g is None or g.is_empty:
      return None
    if snap_tol and snap_tol > 0:
      g2 = extract_polygonal(make_valid(set_precision(g, snap_tol)))
      if g2 is not None and not g2.is_empty:
        g = g2
    return g
  except Exception:
    try:
      g = extract_polygonal(make_valid(g).buffer(0))
      return g
    except Exception:
      return None


def u_geoms(glist, snap_tol=0):
  valid = [safe_geom(g, snap_tol=snap_tol) for g in glist if g is not None]
  valid = [g for g in valid if g is not None and not g.is_empty]
  if not valid:
    return None
  try:
    return safe_geom(unary_union(valid), snap_tol=snap_tol)
  except Exception:
    acc = valid[0]
    for g in valid[1:]:
      try:
        acc = safe_geom(acc.union(g), snap_tol=snap_tol)
      except Exception:
        pass
    return acc


def weld_union(glist, tol=0.006):
  """Dissolves adjacent sub-units into a single seamless polygon with ZERO internal hairline cracks."""
  valid = [safe_geom(g) for g in glist if g is not None]
  valid = [g for g in valid if g is not None and not g.is_empty]
  if not valid:
    return None
  if len(valid) == 1:
    return valid[0]
  try:
    expanded = [g.buffer(tol, join_style=2) for g in valid]
    merged = unary_union(expanded)
    shrunk = safe_geom(merged.buffer(-tol, join_style=2))
    return shrunk if shrunk is not None else u_geoms(valid)
  except Exception:
    return u_geoms(valid)


def clip_geom(a, b, snap_tol=0):
  a = safe_geom(a, snap_tol=snap_tol)
  b = safe_geom(b, snap_tol=snap_tol)
  if a is None or b is None:
    return None
  try:
    return safe_geom(a.intersection(b), snap_tol=snap_tol)
  except Exception:
    try:
      return safe_geom(a.buffer(0).intersection(b.buffer(0)), snap_tol=snap_tol)
    except Exception:
      return None


def diff_geom(a, b, snap_tol=0):
  a = safe_geom(a, snap_tol=snap_tol)
  if a is None:
    return None
  b = safe_geom(b, snap_tol=snap_tol)
  if b is None:
    return a
  try:
    return safe_geom(a.difference(b), snap_tol=snap_tol)
  except Exception:
    try:
      return safe_geom(a.buffer(0).difference(b.buffer(0)), snap_tol=snap_tol)
    except Exception:
      return a


def filter_polygons_by_bbox(g, predicate):
  """Keeps only Polygon parts whose representative point satisfies predicate(lat, lon, poly)."""
  g = safe_geom(g)
  if g is None:
    return None
  polys = [g] if isinstance(g, Polygon) else list(g.geoms)
  kept = []
  for p in polys:
    if p.is_empty or p.area <= 0:
      continue
    rp = p.representative_point()
    if predicate(float(rp.y), float(rp.x), p):
      kept.append(p)
  return u_geoms(kept) if kept else None


def drop_continental_slivers(g, min_area_deg2=0.0022):
  """Drops tiny border residual fragments (< ~25 km^2) on continental regions while always
  retaining at least the largest polygon if all components are small."""
  g = safe_geom(g)
  if g is None:
    return None
  polys = [g] if isinstance(g, Polygon) else list(g.geoms)
  big = [p for p in polys if p.area >= min_area_deg2]
  if big:
    return u_geoms(big)
  return max(polys, key=lambda p: p.area) if polys else None


def iter_safe_raster_polys(g):
  """Yields polygons safe for -180..+180 equirectangular rasterisation without antimeridian streaks."""
  g = safe_geom(g, snap_tol=0)
  if g is None:
    return
  polys = [g] if isinstance(g, Polygon) else list(g.geoms)
  for p in polys:
    if p.is_empty or p.area <= 0:
      continue
    minx, miny, maxx, maxy = p.bounds
    if (maxx - minx) > 180.0:
      # Split antimeridian-crossing polygon by shifting to 0..360 then clipping east/west halves
      p360 = shp_transform(lambda x, y, z=None: ((x + 360.0) if x < 0 else x, y), p)
      p360 = safe_geom(p360, snap_tol=0)
      if p360 is None:
        continue
      east = clip_geom(p360, box(0.0, -90.0, 180.0, 90.0), snap_tol=0)
      west = clip_geom(p360, box(180.0, -90.0, 360.0, 90.0), snap_tol=0)
      if east is not None:
        for ep in ([east] if isinstance(east, Polygon) else list(east.geoms)):
          yield ep
      if west is not None:
        west180 = shp_transform(lambda x, y, z=None: (x - 360.0, y), west)
        west180 = safe_geom(west180, snap_tol=0)
        if west180 is not None:
          for wp in ([west180] if isinstance(west180, Polygon) else list(west180.geoms)):
            yield wp
    else:
      yield p


def rasterise_geom_bool(g, min_stamp_px=0):
  """Rasterises a Shapely geometry onto a 4320x2160 boolean grid using OpenCV sub-pixel fillPoly.
  If `min_stamp_px > 0` and the filled pixel count is smaller, stamps a compact micro-island
  footprint around its representative point(s) so inhabited atolls never vanish."""
  mask = np.zeros((GRID_H, GRID_W), dtype=bool)
  if g is None or g.is_empty:
    return mask
  scale_x, scale_y, sm = GRID_W / 360.0, GRID_H / 180.0, 16.0
  polys = list(iter_safe_raster_polys(g))
  for poly in polys:
    minx, miny, maxx, maxy = poly.bounds
    c0 = max(0, int(math.floor((minx + 180.0) * scale_x)) - 2)
    c1 = min(GRID_W, int(math.ceil((maxx + 180.0) * scale_x)) + 2)
    r0 = max(0, int(math.floor((90.0 - maxy) * scale_y)) - 2)
    r1 = min(GRID_H, int(math.ceil((90.0 - miny) * scale_y)) + 2)
    if c1 <= c0 or r1 <= r0:
      continue
    lm = np.zeros((r1 - r0, c1 - c0), dtype=np.uint8)
    ec = np.asarray(poly.exterior.coords, dtype=np.float64)
    if len(ec) < 3:
      continue
    px = np.round(((ec[:, 0] + 180.0) * scale_x - 0.5 - c0) * sm).astype(np.int32)
    py = np.round(((90.0 - ec[:, 1]) * scale_y - 0.5 - r0) * sm).astype(np.int32)
    cv2.fillPoly(lm, [np.column_stack([px, py])], 1, lineType=cv2.LINE_8, shift=4)
    for interior in poly.interiors:
      ic = np.asarray(interior.coords, dtype=np.float64)
      if len(ic) < 3:
        continue
      hx = np.round(((ic[:, 0] + 180.0) * scale_x - 0.5 - c0) * sm).astype(np.int32)
      hy = np.round(((90.0 - ic[:, 1]) * scale_y - 0.5 - r0) * sm).astype(np.int32)
      cv2.fillPoly(lm, [np.column_stack([hx, hy])], 0, lineType=cv2.LINE_8, shift=4)
    mask[r0:r1, c0:c1] |= (lm > 0)

  if min_stamp_px > 0 and int(mask.sum()) < min_stamp_px and polys:
    # Stamp representative points of largest polygons until at least min_stamp_px pixels exist
    polys_sorted = sorted(polys, key=lambda p: -p.area)
    for p in polys_sorted[:max(1, min_stamp_px)]:
      rp = p.representative_point()
      cc = min(GRID_W - 1, max(0, int(math.floor((rp.x + 180.0) * scale_x))))
      rr = min(GRID_H - 1, max(0, int(math.floor((90.0 - rp.y) * scale_y))))
      mask[rr, cc] = True
    # If single tiny atoll still < min_stamp_px, expand to compact 2x2 (4 px) footprint
    if int(mask.sum()) < min_stamp_px:
      rp = polys_sorted[0].representative_point()
      cc = min(GRID_W - 2, max(0, int(math.floor((rp.x + 180.0) * scale_x))))
      rr = min(GRID_H - 2, max(0, int(math.floor((90.0 - rp.y) * scale_y))))
      mask[rr:rr + 2, cc:cc + 2] = True
  return mask


def load_geojson_features(fn):
  fp = os.path.join(HGIS_RAW, fn)
  gj = json.load(open(fp, encoding="utf-8"))
  return gj.get("features", [])


def load_geojson_by_prop(fn, prop_key, filter_fn=None):
  out = {}
  for f in load_geojson_features(fn):
    nm = str(f["properties"].get(prop_key) or "").strip()
    if not nm:
      continue
    g = safe_geom(shape(f["geometry"]))
    if g is None:
      continue
    if filter_fn is not None:
      g = filter_polygons_by_bbox(g, filter_fn)
      if g is None:
        continue
    if g.area > 0.05:
      g = safe_geom(g.simplify(0.002, preserve_topology=True)) or g
    out[nm] = u_geoms([out[nm], g]) if nm in out else g
  return out


def load_geojson_union(fn, filter_fn=None):
  gs = []
  for f in load_geojson_features(fn):
    g = safe_geom(shape(f["geometry"]))
    if g is None:
      continue
    if filter_fn is not None:
      g = filter_polygons_by_bbox(g, filter_fn)
    if g is not None:
      if g.area > 0.05:
        g = safe_geom(g.simplify(0.002, preserve_topology=True)) or g
      gs.append(g)
  return u_geoms(gs)


def load_kiribati_adm1_clean():
  """Re-partitions geoboundaries_kir_adm1 polygons strictly by true geographic longitude so
  Banaba (169.53E) and Tarawa (173.0E) are in Gilbert Islands (168E..180E), Phoenix Islands
  strictly in -175.5..-169.0W, and Line Islands strictly in -163.0..-149.0W."""
  kir_all = load_geojson_union("geoboundaries_kir_adm1.geojson")
  return {
    "Gilbert Islands": filter_polygons_by_bbox(kir_all, lambda lat, lon, p: 168.0 <= lon <= 180.0),
    "Phoenix Islands": filter_polygons_by_bbox(kir_all, lambda lat, lon, p: -175.5 <= lon <= -169.0),
    "Line Islands": filter_polygons_by_bbox(kir_all, lambda lat, lon, p: -163.0 <= lon <= -149.0),
  }


def build_austral_sources_and_domain_mask():
  print("[1] Loading AUSTRAL official Admin-1/Admin-2, OHM, Esri, HydroBASINS L6, and seam masks...", flush=True)

  # Load neighbour exclusion seam masks (MANDALA & CENTAUR)
  mandala_rgba = np.asarray(Image.open(MANDALA_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  mandala_mask = (mandala_rgba[:, :, 3] > 0) & (mandala_rgba[:, :, :3].sum(axis=2) > 0)
  centaur_rgba = np.asarray(Image.open(CENTAUR_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  centaur_mask = (centaur_rgba[:, :, 3] > 0) & (centaur_rgba[:, :, :3].sum(axis=2) > 0)
  forbidden_mask = mandala_mask | centaur_mask

  # Build pixel-coordinate exclusion mask for non-AUSTRAL outlier boxes
  lon_1d = (np.arange(GRID_W) + 0.5) * 360.0 / GRID_W - 180.0
  lat_1d = 90.0 - (np.arange(GRID_H) + 0.5) * 180.0 / GRID_H
  LON, LAT = np.meshgrid(lon_1d, lat_1d)
  excl_geo = (
    ((LON < 129.5) & (LON >= 0.0) & (LAT > -11.3))            # Maluku, Aru, Timor, Sumatra, Java
    | ((LON < 110.0) & (LON >= 0.0))                          # Indian Ocean (Christmas, Cocos)
    | ((LON > -171.25) & (LON < -168.0) & (LAT > -15.5) & (LAT < -13.0))  # American Samoa
    | ((LON > -179.0) & (LON < -154.0) & (LAT > 18.0) & (LAT < 29.0))     # Hawai'i
    | ((LON > -163.5) & (LON < -160.0) & (LAT > 5.0) & (LAT < 7.0))       # Palmyra
    | ((LON >= 129.5) & (LON <= 160.0) & (LAT > 21.0))                    # Bonin / Volcano Islands
    | ((LON >= -116.0) & (LON <= -105.0) & (LAT > 9.5))                   # Clipperton
  )
  forbidden_mask |= excl_geo

  # 1. Australia ADM1 (exclude Christmas/Cocos west of 110E & Macquarie/Heard south of -46S)
  aus_raw = load_geojson_by_prop(
    "geoboundaries_aus_adm1.geojson", "shapeName",
    filter_fn=lambda lat, lon, p: lon >= 110.0 and lat >= -46.0
  )
  other_terr = aus_raw.get("Other Territories")
  norfolk_g = filter_polygons_by_bbox(other_terr, lambda lat, lon, p: lon > 165.0) if other_terr else None
  jervis_g = filter_polygons_by_bbox(other_terr, lambda lat, lon, p: 149.5 < lon < 152.0) if other_terr else None
  aus_adm1 = {
    "New South Wales": u_geoms([aus_raw.get("New South Wales"), jervis_g]),
    "Victoria": aus_raw.get("Victoria"),
    "Queensland": aus_raw.get("Queensland"),
    "South Australia": aus_raw.get("South Australia"),
    "Western Australia": aus_raw.get("Western Australia"),
    "Tasmania": aus_raw.get("Tasmania"),
    "Northern Territory": aus_raw.get("Northern Territory"),
    "Australian Capital Territory": aus_raw.get("Australian Capital Territory"),
    "Norfolk Island": norfolk_g,
  }
  aus_mainland_tas = u_geoms([v for k, v in aus_adm1.items() if k != "Norfolk Island"])
  aus_full = u_geoms(list(aus_adm1.values()))

  # 2. New Zealand ADM1 (16 Regional Councils + Chatham Islands) & ADM2 (for 1853-76 Provinces)
  nzl_adm1 = load_geojson_by_prop("geoboundaries_nzl_adm1.geojson", "shapeName")
  nzl_adm2 = load_geojson_by_prop("geoboundaries_nzl_adm2.geojson", "shapeName")
  nzl_full = u_geoms(list(nzl_adm1.values()))

  # 3. PNG 22 Provinces & Indonesian Papua 6 Provinces (post-2022)
  png_adm1 = load_geojson_by_prop("hdx_codab_png_adm1.geojson", "adm1_name")
  idn_papua_adm1 = load_geojson_by_prop(
    "bps_idn_papua_6provinces_2022_adm1.geojson", "PROVINSI",
    filter_fn=lambda lat, lon, p: lon >= 129.35 and lat >= -9.5 and lat <= 1.0
  )
  # Ensure Raja Ampat / West Papua stays strictly outside Maluku (< 129.5E north of -11.3S)
  # Wait: Raja Ampat westernmost islet (Kofiau/Gag/Waigeo) is ~129.8E..131.3E; clip west of 129.5E!
  for k in list(idn_papua_adm1.keys()):
    idn_papua_adm1[k] = clip_geom(idn_papua_adm1[k], box(129.5, -11.3, 141.1, 1.5))

  png_full = u_geoms(list(png_adm1.values()))
  idn_papua_full = u_geoms(list(idn_papua_adm1.values()))
  bougainville_g = png_adm1.get("Autonomous Region of Bougainville")
  bismarck_provs = ["East New Britain Province", "West New Britain Province", "New Ireland Province", "Manus Province"]
  bismarck_g = u_geoms([png_adm1.get(k) for k in bismarck_provs])
  ng_mainland_bismarck = u_geoms([idn_papua_full] + [v for k, v in png_adm1.items() if k != "Autonomous Region of Bougainville"])
  ng_all_with_boug = u_geoms([idn_papua_full, png_full])

  # 4. Island Melanesia: Fiji (4 divisions + Rotuma from adm2 so Lau/Kadavu/Rotuma are intact!), Solomons, Vanuatu, New Caledonia
  fji_adm2 = load_geojson_by_prop("geoboundaries_fji_adm2.geojson", "shapeName")
  fji_div_map = {
    "Central Division": ["Naitasiri", "Namosi", "Rewa", "Serua", "Tailevu"],
    "Western Division": ["Ba", "Nadroga-Navosa", "Ra"],
    "Northern Division": ["Bua", "Cakaudrove", "Macuata"],
    "Eastern Division": ["Kadavu", "Lau", "Lomaiviti"],
    "Rotuma": ["Rotuma"],
  }
  fji_adm1 = {div: u_geoms([fji_adm2.get(p) for p in ps]) for div, ps in fji_div_map.items()}
  fji_full = u_geoms(list(fji_adm1.values()))

  slb_adm1 = load_geojson_by_prop("geoboundaries_slb_adm1.geojson", "shapeName")
  slb_full = u_geoms(list(slb_adm1.values()))
  vut_adm1 = load_geojson_by_prop("hdx_codab_vut_adm1.geojson", "adm1_name")
  vut_full = u_geoms(list(vut_adm1.values()))
  ncl_adm1 = load_geojson_by_prop("gadm41_ncl_adm1.geojson", "NAME_1")
  ncl_full = u_geoms(list(ncl_adm1.values()))

  # 5. Micronesia: FSM (4 states), Marshalls, Palau, Guam, CNMI, Kiribati (3 groups), Nauru
  fsm_adm1 = load_geojson_by_prop("geoboundaries_fsm_adm1.geojson", "shapeName")
  fsm_full = u_geoms(list(fsm_adm1.values()))
  mhl_full = load_geojson_union("geoboundaries_mhl_adm1.geojson")
  plw_full = load_geojson_union("geoboundaries_plw_adm1.geojson")
  gum_full = load_geojson_union("gadm41_gum_adm1.geojson")
  mnp_full = load_geojson_union("uscensus_mnp_adm1_municipalities.geojson", filter_fn=lambda lat, lon, p: lat <= 21.0)
  kir_adm1 = load_kiribati_adm1_clean()
  kir_full = u_geoms(list(kir_adm1.values()))
  nru_full = load_geojson_union("geoboundaries_nru_adm1.geojson")

  # 6. Polynesia (strictly EXCLUDING Hawai'i & American Samoa!)
  wsm_full = load_geojson_union("geoboundaries_wsm_adm1.geojson", filter_fn=lambda lat, lon, p: lon <= -171.25)
  ton_adm1 = load_geojson_by_prop("geoboundaries_ton_adm1.geojson", "shapeName")
  ton_full = u_geoms(list(ton_adm1.values()))
  pyf_adm1 = load_geojson_by_prop("gadm41_pyf_adm1.geojson", "NAME_1")
  pyf_full = u_geoms(list(pyf_adm1.values()))
  cok_full = load_geojson_union("gadm41_cok_adm1.geojson")
  tuv_full = load_geojson_union("geoboundaries_tuv_adm1.geojson")
  niu_full = load_geojson_union("geoboundaries_niu_adm1.geojson")
  tkl_full = load_geojson_union("gadm41_tkl_adm1.geojson")
  wlf_full = load_geojson_union("gadm41_wlf_adm1.geojson")
  pcn_full = load_geojson_union("geoboundaries_pcn_adm0.geojson")
  rapanui_full = load_geojson_union("geoboundaries_chl_rapanui_adm2.geojson")

  # Collect ALL atomic units that must be visible in austral_domain_mask.png (with micro-island stamping!)
  atomic_units = []
  for k, g in aus_adm1.items():
    atomic_units.append((f"AUS_{k}", g, 4))
  for k, g in nzl_adm1.items():
    atomic_units.append((f"NZL_{k}", g, 4))
  for k, g in png_adm1.items():
    atomic_units.append((f"PNG_{k}", g, 4))
  for k, g in idn_papua_adm1.items():
    atomic_units.append((f"IDN_{k}", g, 4))
  for k, g in fji_adm1.items():
    atomic_units.append((f"FJI_{k}", g, 4))
  for k, g in slb_adm1.items():
    atomic_units.append((f"SLB_{k}", g, 4))
  for k, g in vut_adm1.items():
    atomic_units.append((f"VUT_{k}", g, 4))
  for k, g in ncl_adm1.items():
    atomic_units.append((f"NCL_{k}", g, 4))
  for k, g in fsm_adm1.items():
    atomic_units.append((f"FSM_{k}", g, 4))
  for k, g in kir_adm1.items():
    atomic_units.append((f"KIR_{k}", g, 4))
  for k, g in ton_adm1.items():
    atomic_units.append((f"TON_{k}", g, 4))
  for k, g in pyf_adm1.items():
    atomic_units.append((f"PYF_{k}", g, 4))
  for nm, g in [
    ("MHL", mhl_full), ("PLW", plw_full), ("GUM", gum_full), ("MNP", mnp_full),
    ("NRU", nru_full), ("WSM", wsm_full), ("COK", cok_full), ("TUV", tuv_full),
    ("NIU", niu_full), ("TKL", tkl_full), ("WLF", wlf_full), ("PCN", pcn_full), ("RAPANUI", rapanui_full),
  ]:
    atomic_units.append((nm, g, 4))

  domain_mask = np.zeros((GRID_H, GRID_W), dtype=bool)
  for nm, g, min_px in atomic_units:
    if g is None:
      print(f"  [WARN] Missing atomic unit geometry: {nm}")
      continue
    um = rasterise_geom_bool(g, min_stamp_px=min_px)
    domain_mask |= um

  # MANDATORY SEAM SUBTRACTION: subtract MANDALA and CENTAUR pixel-for-pixel + geo exclusions
  before_px = int(domain_mask.sum())
  domain_mask &= ~forbidden_mask
  after_px = int(domain_mask.sum())

  # STRICT ZERO-OVERLAP ASSERTION!
  ov_mandala = int((domain_mask & mandala_mask).sum())
  ov_centaur = int((domain_mask & centaur_mask).sum())
  assert ov_mandala == 0, f"SEAM FAIL: {ov_mandala} overlap pixels with MANDALA!"
  assert ov_centaur == 0, f"SEAM FAIL: {ov_centaur} overlap pixels with CENTAUR!"

  # Save 4320x2160 RGB PNG for austral_domain_mask.png
  dm_rgb = np.zeros((GRID_H, GRID_W, 3), dtype=np.uint8)
  dm_rgb[domain_mask] = [255, 255, 255]
  Image.fromarray(dm_rgb, mode="RGB").save(DOMAIN_MASK_PNG, compress_level=6)
  print(f"  Saved austral_domain_mask.png: {after_px:,d} active px (subtracted {before_px - after_px:,d} seam/excl px | MANDALA ov={ov_mandala}, CENTAUR ov={ov_centaur})", flush=True)

  # 7. Load HydroBASINS AU L6 for organic Regime I precolonial watersheds (Australia, New Guinea, NZ)
  hybas_au, hybas_ng, hybas_nz = [], [], []
  with zipfile.ZipFile(HYBAS_L6_ZIP) as zf:
    sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
    for sr in sf.iterShapeRecords():
      pfaf = str(sr.record["PFAF_ID"])
      p3 = pfaf[:3]
      if p3 not in ("561", "562", "563", "564", "565", "566", "567", "568", "569",
                    "531", "534", "535", "536", "538", "571", "572", "573"):
        continue
      g = safe_geom(shape(sr.shape.__geo_interface__))
      if g is None:
        continue
      rp = g.representative_point()
      rec = {"g": g, "lat": float(rp.y), "lon": float(rp.x), "pfaf": pfaf, "p3": p3, "main_bas": int(sr.record["MAIN_BAS"])}
      if p3.startswith("56"):
        hybas_au.append(rec)
      elif p3.startswith("53"):
        # Clip Raja Ampat / West NG strictly >= 129.5E so ZERO Maluku bleed
        g_cl = clip_geom(g, box(129.5, -11.3, 156.0, 1.0))
        if g_cl is not None:
          rp2 = g_cl.representative_point()
          rec["g"] = g_cl
          rec["lat"] = float(rp2.y)
          rec["lon"] = float(rp2.x)
          hybas_ng.append(rec)
      elif p3.startswith("57"):
        hybas_nz.append(rec)
  print(f"  HydroBASINS AU L6 loaded: AU={len(hybas_au)} | NG={len(hybas_ng)} | NZ={len(hybas_nz)}", flush=True)

  # 8. Load OHM historical boundaries for colonial verification/geometries
  ohm_pac = load_geojson_features("ohm_pacific_melanesia.geojson")
  ohm_papua = u_geoms([shape(f["geometry"]) for f in ohm_pac if (f["properties"].get("name") or "") == "Territory of Papua"])
  ohm_tng = u_geoms([shape(f["geometry"]) for f in ohm_pac if (f["properties"].get("name") or "") == "Territory of New Guinea"])

  # 9. Load NE 10m coastlines for optical QA crop basemaps (land polygons only; NO modern borders on pre-1945 crops!)
  ne_gj = json.load(open(NE_ADMIN0_GJ, encoding="utf-8"))
  ne_oceania_polys = []
  for f in ne_gj["features"]:
    g = safe_geom(shape(f["geometry"]), snap_tol=0)
    if g is None:
      continue
    b = g.bounds
    # Keep land relevant to Indo-Pacific / Australasia / East Pacific context
    if b[2] >= 100.0 or b[0] <= -95.0:
      if b[1] <= 30.0 and b[3] >= -56.0:
        ne_oceania_polys.append(g)

  return {
    "domain_mask": domain_mask,
    "forbidden_mask": forbidden_mask,
    "aus_adm1": aus_adm1, "aus_mainland_tas": aus_mainland_tas, "aus_full": aus_full, "norfolk_g": norfolk_g,
    "nzl_adm1": nzl_adm1, "nzl_adm2": nzl_adm2, "nzl_full": nzl_full,
    "png_adm1": png_adm1, "png_full": png_full, "bougainville_g": bougainville_g, "bismarck_g": bismarck_g,
    "idn_papua_adm1": idn_papua_adm1, "idn_papua_full": idn_papua_full,
    "ng_mainland_bismarck": ng_mainland_bismarck, "ng_all_with_boug": ng_all_with_boug,
    "fji_adm1": fji_adm1, "fji_full": fji_full,
    "slb_adm1": slb_adm1, "slb_full": slb_full,
    "vut_adm1": vut_adm1, "vut_full": vut_full,
    "ncl_adm1": ncl_adm1, "ncl_full": ncl_full,
    "fsm_adm1": fsm_adm1, "fsm_full": fsm_full,
    "mhl_full": mhl_full, "plw_full": plw_full, "gum_full": gum_full, "mnp_full": mnp_full,
    "kir_adm1": kir_adm1, "kir_full": kir_full, "nru_full": nru_full,
    "wsm_full": wsm_full, "ton_adm1": ton_adm1, "ton_full": ton_full,
    "pyf_adm1": pyf_adm1, "pyf_full": pyf_full, "cok_full": cok_full,
    "tuv_full": tuv_full, "niu_full": niu_full, "tkl_full": tkl_full,
    "wlf_full": wlf_full, "pcn_full": pcn_full, "rapanui_full": rapanui_full,
    "hybas_au": hybas_au, "hybas_ng": hybas_ng, "hybas_nz": hybas_nz,
    "ohm_papua": ohm_papua, "ohm_tng": ohm_tng,
    "ne_oceania_polys": ne_oceania_polys,
  }


def group_basins(basins, classifier):
  buckets = defaultdict(list)
  for b in basins:
    zid = classifier(b["lat"], b["lon"], b["pfaf"], b["p3"])
    if zid:
      buckets[zid].append(b["g"])
  return {k: u_geoms(gs) for k, gs in buckets.items()}


def rasterise_chapter_zones(domain_mask, zones_spec, chapter_clip_geom=None, snap_px=2):
  """Zero-scanline OpenCV sub-pixel rasteriser with guaranteed micro-island survival (>= 4 px)
  strictly inside `domain_mask`."""
  id_grid = np.zeros((GRID_H, GRID_W), dtype=np.int32)
  scale_x, scale_y, sm = GRID_W / 360.0, GRID_H / 180.0, 16.0

  # Pass 1: polygon fillPoly in order
  for z_idx, z in enumerate(zones_spec, start=1):
    g = z.get("geom")
    if g is None or g.is_empty:
      continue
    for poly in iter_safe_raster_polys(g):
      minx, miny, maxx, maxy = poly.bounds
      c0 = max(0, int(math.floor((minx + 180.0) * scale_x)) - 2)
      c1 = min(GRID_W, int(math.ceil((maxx + 180.0) * scale_x)) + 2)
      r0 = max(0, int(math.floor((90.0 - maxy) * scale_y)) - 2)
      r1 = min(GRID_H, int(math.ceil((90.0 - miny) * scale_y)) + 2)
      if c1 <= c0 or r1 <= r0:
        continue
      lm = np.zeros((r1 - r0, c1 - c0), dtype=np.uint8)
      ec = np.asarray(poly.exterior.coords, dtype=np.float64)
      if len(ec) < 3:
        continue
      px = np.round(((ec[:, 0] + 180.0) * scale_x - 0.5 - c0) * sm).astype(np.int32)
      py = np.round(((90.0 - ec[:, 1]) * scale_y - 0.5 - r0) * sm).astype(np.int32)
      cv2.fillPoly(lm, [np.column_stack([px, py])], 1, lineType=cv2.LINE_8, shift=4)
      for interior in poly.interiors:
        ic = np.asarray(interior.coords, dtype=np.float64)
        if len(ic) < 3:
          continue
        hx = np.round(((ic[:, 0] + 180.0) * scale_x - 0.5 - c0) * sm).astype(np.int32)
        hy = np.round(((90.0 - ic[:, 1]) * scale_y - 0.5 - r0) * sm).astype(np.int32)
        cv2.fillPoly(lm, [np.column_stack([hx, hy])], 0, lineType=cv2.LINE_8, shift=4)
      sub = id_grid[r0:r1, c0:c1]
      sub[(lm > 0) & (sub == 0)] = z_idx

  id_grid[~domain_mask] = 0

  # Pass 2: Micro-island survival stamp — guarantee EVERY zone has >= 4 pixels inside domain_mask!
  for z_idx, z in enumerate(zones_spec, start=1):
    cnt = int((id_grid == z_idx).sum())
    if cnt >= 4:
      continue
    g = z.get("geom")
    if g is None or g.is_empty:
      continue
    polys = sorted(list(iter_safe_raster_polys(g)), key=lambda p: -p.area)
    if not polys:
      continue
    for p in polys[:6]:
      rp = p.representative_point()
      cc = min(GRID_W - 1, max(0, int(math.floor((rp.x + 180.0) * scale_x))))
      rr = min(GRID_H - 1, max(0, int(math.floor((90.0 - rp.y) * scale_y))))
      if domain_mask[rr, cc] and id_grid[rr, cc] == 0:
        id_grid[rr, cc] = z_idx
    if int((id_grid == z_idx).sum()) < 4:
      rp = polys[0].representative_point()
      cc = min(GRID_W - 2, max(0, int(math.floor((rp.x + 180.0) * scale_x))))
      rr = min(GRID_H - 2, max(0, int(math.floor((90.0 - rp.y) * scale_y))))
      for dr in range(0, 2):
        for dc in range(0, 2):
          if domain_mask[rr + dr, cc + dc] and (id_grid[rr + dr, cc + dc] == 0 or id_grid[rr + dr, cc + dc] == z_idx):
            id_grid[rr + dr, cc + dc] = z_idx
      # If still < 4 (e.g. near seam or single isolated domain px), search small 3x3 domain window
      if int((id_grid == z_idx).sum()) < 4:
        for dr in range(-2, 3):
          for dc in range(-2, 3):
            r2, c2 = rr + dr, cc + dc
            if 0 <= r2 < GRID_H and 0 <= c2 < GRID_W and domain_mask[r2, c2] and id_grid[r2, c2] == 0:
              id_grid[r2, c2] = z_idx
              if int((id_grid == z_idx).sum()) >= 4:
                break
          if int((id_grid == z_idx).sum()) >= 4:
            break

  # Pass 3: Snap 1-2 px coastal mismatch slivers inside the chapter's land footprint cleanly
  if snap_px > 0 and chapter_clip_geom is not None:
    chap_dom = rasterise_geom_bool(chapter_clip_geom, min_stamp_px=0) & domain_mask
    missing = chap_dom & (id_grid == 0)
    if missing.any() and (id_grid > 0).any():
      dist, idx = distance_transform_edt(id_grid == 0, return_indices=True)
      fill_m = missing & (dist <= float(snap_px))
      if fill_m.any():
        id_grid[fill_m] = id_grid[idx[0][fill_m], idx[1][fill_m]]

  # Belt-and-suspenders scanline hole guard
  mid = id_grid[1:-1, :]
  above = id_grid[:-2, :]
  below = id_grid[2:, :]
  scanline_holes = (mid == 0) & domain_mask[1:-1, :] & (above > 0) & (above == below)
  if scanline_holes.any():
    id_grid[1:-1, :][scanline_holes] = above[scanline_holes]

  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  px_counts = {}
  for z_idx, z in enumerate(zones_spec, start=1):
    m = (id_grid == z_idx)
    cnt = int(m.sum())
    px_counts[z["id"]] = cnt
    if cnt > 0:
      rgb = z["rgb"]
      rgba[m, 0] = rgb[0]
      rgba[m, 1] = rgb[1]
      rgba[m, 2] = rgb[2]
      rgba[m, 3] = 255
  return rgba, px_counts


def shift_geom_360(g):
  """Shifts negative longitudes to [180, 360] for continuous trans-antimeridian Pacific rendering."""
  polys_out = []
  for p in iter_safe_raster_polys(g):
    p360 = shp_transform(lambda x, y, z=None: (x + 360.0 if x < 0 else x, y), p)
    p360 = safe_geom(p360, snap_tol=0)
    if p360 is not None:
      polys_out.append(p360)
  return u_geoms(polys_out, snap_tol=0) if polys_out else None


def geom_to_mpl_patches(g):
  patches = []
  if g is None or g.is_empty:
    return patches
  polys = [g] if isinstance(g, Polygon) else (list(g.geoms) if isinstance(g, MultiPolygon) else [])
  for p in polys:
    if p.is_empty:
      continue
    coords = np.asarray(p.exterior.coords, dtype=np.float64)
    if len(coords) >= 3:
      patches.append(MplPolygon(coords[:, :2], closed=True))
  return patches


def render_chapter_crop_png(ch_meta, zones_spec, ne_polys, wrap_pacific=False, bbox_override=None):
  """Renders a high-clarity regional optical QA crop PNG into `tests/mask_crops/`.
  Uses pure land coastlines (NO modern national borders on pre-1945 chapters!) and continuous
  0..360 longitude wrapping for antimeridian-crossing Pacific chapters."""
  apply_viscount_style()
  fig, ax = plt.subplots(figsize=(11.2, 7.6), dpi=135)
  apply_viscount_style(ax, {"grid": True})
  fig.patch.set_facecolor("#F6F5F0")
  ax.set_facecolor("#DDEBF4")

  all_xs, all_ys = [], []
  handles = []
  zone_draw = []
  for z in zones_spec:
    g = z.get("geom")
    if g is None or g.is_empty:
      continue
    g_use = shift_geom_360(g) if wrap_pacific else g
    if g_use is None or g_use.is_empty:
      continue
    b = g_use.bounds
    all_xs.extend([b[0], b[2]])
    all_ys.extend([b[1], b[3]])
    zone_draw.append((z, g_use))

  if bbox_override is not None:
    x0, x1, y0, y1 = bbox_override
  elif all_xs and all_ys:
    span_x = max(2.0, max(all_xs) - min(all_xs))
    span_y = max(2.0, max(all_ys) - min(all_ys))
    x0, x1 = min(all_xs) - span_x * 0.07, max(all_xs) + span_x * 0.07
    y0, y1 = min(all_ys) - span_y * 0.08, max(all_ys) + span_y * 0.08
  else:
    x0, x1, y0, y1 = 110, 180, -48, 10

  # Draw pure land basemap (uniform warm-grey land with coastal outline ONLY; ZERO modern borders on pre-1945!)
  is_modern = bool(ch_meta.get("is_admin1"))
  clip_b = box(x0 - 5, y0 - 5, x1 + 5, y1 + 5)
  land_geoms = []
  for ng in ne_polys:
    g_n = shift_geom_360(ng) if wrap_pacific else ng
    if g_n is None:
      continue
    if g_n.bounds[2] < x0 - 5 or g_n.bounds[0] > x1 + 5 or g_n.bounds[3] < y0 - 5 or g_n.bounds[1] > y1 + 5:
      continue
    cl = clip_geom(g_n, clip_b, snap_tol=0)
    if cl is not None:
      land_geoms.append(cl)
  if land_geoms:
    if is_modern:
      base_ps = []
      for lg in land_geoms:
        base_ps.extend(geom_to_mpl_patches(lg))
      if base_ps:
        ax.add_collection(PatchCollection(base_ps, facecolor="#E8E4DA", edgecolor="#A8A49A", linewidths=0.45, zorder=1.0))
    else:
      # Dissolve into pure physical coastline union so ZERO modern state borders exist on pre-1945 crops!
      land_u = u_geoms(land_geoms, snap_tol=0)
      base_ps = geom_to_mpl_patches(land_u)
      if base_ps:
        ax.add_collection(PatchCollection(base_ps, facecolor="#E8E4DA", edgecolor="#9C988E", linewidths=0.5, zorder=1.0))

  # Draw chapter mask sub-regions (+ subtle visibility ring for tiny Pacific micro-atolls)
  span_diag = math.hypot(x1 - x0, y1 - y0)
  for z, g_use in zone_draw:
    rgb_f = [c / 255.0 for c in z["rgb"]]
    ps = geom_to_mpl_patches(g_use)
    if ps:
      ax.add_collection(PatchCollection(ps, facecolor=rgb_f, edgecolor="#1F1F24", linewidths=0.65, alpha=0.88, zorder=2.5))
    # If very tiny archipelago/island relative to map span, add crisp centroid locator halo so auditor sees every island!
    if g_use.area < (span_diag * 0.012) ** 2:
      rp = g_use.representative_point()
      ax.scatter([rp.x], [rp.y], s=48, facecolor=rgb_f, edgecolor="#111116", linewidths=0.9, zorder=3.5)
    handles.append(Patch(facecolor=rgb_f, edgecolor="#1F1F24", label=z["name"][:30]))

  ax.set_xlim(x0, x1)
  ax.set_ylim(y0, y1)
  # Format longitude ticks neatly (converting >180 back to deg W!)
  xticks = ax.get_xticks()
  ax.set_xticks([t for t in xticks if x0 <= t <= x1])
  ax.set_xticklabels([f"{(360 - t):.0f}°W" if t > 180.0 else (f"{t:.0f}°E" if t >= 0 else f"{-t:.0f}°W") for t in ax.get_xticks()], fontsize=7.5)
  yticks = ax.get_yticks()
  ax.set_yticks([t for t in yticks if y0 <= t <= y1])
  ax.set_yticklabels([f"{t:.0f}°N" if t >= 0 else f"{-t:.0f}°S" for t in ax.get_yticks()], fontsize=7.5)
  ax.grid(True, linestyle=":", linewidth=0.45, color="#8FA6B5", alpha=0.65, zorder=0.5)
  if wrap_pacific and x0 < 180.0 < x1:
    ax.axvline(180.0, color="#6B7E8C", linestyle="--", linewidth=0.7, alpha=0.65, zorder=1.2)

  # Aspect adjusted by cos(mid_lat) so equirectangular Pacific/Australia/NZ looks undistorted
  mid_lat = 0.5 * (y0 + y1)
  ax.set_aspect(1.0 / max(0.35, math.cos(math.radians(mid_lat))), adjustable="box")

  d0, d1 = ch_meta["domain"]
  regime_tag = "Regime III Admin-1" if is_modern else ("Regime I Organic/Precolonial" if ch_meta["index"] <= 5 else "Regime II Colonial HGIS")
  ax.set_title(f"CH {ch_meta['index']:02d}: {ch_meta['title']} ({d0}..{d1}) | {regime_tag}", fontsize=9.5, fontweight="bold", pad=8)

  ncol = 4 if len(handles) > 15 else (3 if len(handles) > 8 else 2)
  nrows_q = max(1, (len(handles) + ncol - 1) // ncol)
  fsize = 6.2 if len(handles) > 20 else 7.1
  bot_margin = min(0.38, 0.09 + 0.032 * nrows_q)
  fig.subplots_adjust(left=0.06, right=0.98, top=0.92, bottom=bot_margin)
  fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.012), ncol=ncol, fontsize=fsize, frameon=True, framealpha=0.92)

  out_p = os.path.join(TESTS_CROP_DIR, f"mask_ch{ch_meta['index']:02d}_{ch_meta['key']}.png")
  save_viscount_figure(fig, out_p, arg2_dpi=135, arg3_options={"verify_layout": True, "strict_layout": False, "bbox_inches": None})
  return out_p


def write_chapter_assets(ch_meta, zones_spec, D, chapter_clip_geom, wrap_pacific=False, bbox_override=None, drop_slivers=False, clip_vectors=True):
  ch_dir = os.path.join(AUSTRAL_DIR, ch_meta["folder"])
  os.makedirs(os.path.join(ch_dir, "figures"), exist_ok=True)
  os.makedirs(os.path.join(ch_dir, "papers"), exist_ok=True)
  for fn in ("crd-mla-numeric.csl", "crd_logo.png", "intellte.cls"):
    src_f = os.path.join(AUSTRAL_DIR, fn)
    dst_f = os.path.join(ch_dir, fn)
    if os.path.exists(src_f) and not os.path.exists(dst_f):
      shutil.copy2(src_f, dst_f)

  assert len(zones_spec) <= len(PALETTE), f"Need more palette colours for {ch_meta['key']} ({len(zones_spec)})"

  claimed_vec = None
  clean_zones = []
  for idx, z in enumerate(zones_spec):
    g = safe_geom(z.get("geom"))
    if g is not None and clip_vectors and chapter_clip_geom is not None:
      g = clip_geom(g, chapter_clip_geom)
    if g is not None and claimed_vec is not None:
      g = diff_geom(g, claimed_vec)
    if g is not None and drop_slivers:
      g = drop_continental_slivers(g)
    if g is not None:
      claimed_vec = u_geoms([claimed_vec, g])
    z2 = dict(z)
    z2["geom"] = g
    z2["rgb"] = PALETTE[idx]
    clean_zones.append(z2)

  rgba, px_counts = rasterise_chapter_zones(D["domain_mask"], clean_zones, chapter_clip_geom=chapter_clip_geom, snap_px=2)

  stem = ch_meta["key"]
  mask_out = os.path.join(ch_dir, f"{stem}_areal_mask.png")
  Image.fromarray(rgba, mode="RGBA").save(mask_out, compress_level=6)

  gj_feats = []
  regions_cfg = []
  zero_ids = []
  for z in clean_zones:
    cnt = px_counts.get(z["id"], 0)
    if cnt == 0 or z["geom"] is None:
      zero_ids.append(z["id"])
      continue
    g_simp = safe_geom(z["geom"].simplify(0.01, preserve_topology=True), snap_tol=1e-4) or z["geom"]
    gj_feats.append({
      "type": "Feature",
      "properties": {"id": z["id"], "name": z["name"], "rgb": z["rgb"], "pixel_count": cnt},
      "geometry": mapping(g_simp),
    })
    regions_cfg.append({
      "id": z["id"], "name": z["name"], "rgb": z["rgb"],
      "domain": ch_meta["domain"], "population": z["population"],
    })
  assert not zero_ids, f"STARVATION FAIL in {stem}: 0-pixel zones {zero_ids}"

  gj_out = os.path.join(SUB_GJ_DIR, f"{stem}_subregions.geojson")
  with open(gj_out, "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": gj_feats}, fh)

  cfg_obj = {
    "id": stem,
    "title": ch_meta["title"],
    "domain": ch_meta["domain"],
    "is_admin1": bool(ch_meta.get("is_admin1")),
    "mask_path": f"histmap/1.data_raw/population_regional/AUSTRAL/{ch_meta['folder']}/{stem}_areal_mask.png",
    "subregions_geojson": f"histmap/1.data_raw/population_regional/AUSTRAL/_shared/_gis_cache/chapter_subregions/{stem}_subregions.geojson",
    "regions": regions_cfg,
  }
  with open(os.path.join(ch_dir, f"{stem}.json5"), "w", encoding="utf-8") as fh:
    json.dump(cfg_obj, fh, indent=2, ensure_ascii=False)

  crop_p = render_chapter_crop_png(ch_meta, clean_zones, D["ne_oceania_polys"], wrap_pacific=wrap_pacific, bbox_override=bbox_override)
  min_px = min(px_counts.values()) if px_counts else 0
  print(f"  [CH {ch_meta['index']:02d}] {stem:32s}: {len(regions_cfg):2d} zones | {sum(px_counts.values()):6,d} px (min={min_px:3d}) | crop={os.path.basename(crop_p)}", flush=True)


def build_nz_colonial_provinces(nzl_adm2):
  """Deterministically dissolves 1853-1876 New Zealand Provinces from official NZ ADM2 districts."""
  # Exact assignment of all 88 geoboundaries_nzl_adm2 districts into the 10 historic provinces + Chathams
  prov_buckets = defaultdict(list)
  for nm, g in nzl_adm2.items():
    low = nm.lower()
    rp = g.representative_point()
    lat, lon = float(rp.y), float(rp.x)

    if "chatham" in low:
      p = "chatham_islands"
    elif "area outside" in low:
      p = "auckland_province"
    elif any(k in low for k in ("far north", "whangarei", "kaipara", "thames", "hauraki", "waikato",
                                "matamata", "hamilton", "waipa", "torohanga", "waitomo", "taupo",
                                "bay of plenty", "tauranga", "rotorua", "whakatane", "kawerau",
                                "tiki", "gisborne", "local board")):
      p = "auckland_province"
    elif any(k in low for k in ("new plymouth", "stratford", "south taranaki")):
      p = "taranaki_province"
    elif any(k in low for k in ("wairoa", "hastings", "napier", "hawke")):
      p = "hawkes_bay_province"
    elif any(k in low for k in ("ruapehu", "whanganui", "rangitikei", "manawatu", "palmerston",
                                "tararua", "horowhenua", "kapiti", "porirua", "hutt", "wellington",
                                "masterton", "carterton", "wairarapa")):
      p = "wellington_province"
    elif any(k in low for k in ("tasman", "nelson", "buller")):
      p = "nelson_province"
    elif any(k in low for k in ("marlborough", "kaikoura")):
      p = "marlborough_province"
    elif any(k in low for k in ("grey", "westland")):
      p = "westland_province"
    elif any(k in low for k in ("hurunui", "waimakariri", "christchurch", "selwyn", "ashburton",
                                "timaru", "mackenzie", "waimate")):
      p = "canterbury_province"
    elif any(k in low for k in ("waitaki", "central otago", "queenstown", "dunedin", "clutha")):
      p = "otago_province"
    elif any(k in low for k in ("southland", "gore", "invercargill")):
      p = "southland_province"
    else:
      # Fallback by latitude/island
      if lat > -38.8:
        p = "auckland_province"
      elif lat > -41.6:
        p = "wellington_province"
      elif lat > -44.6:
        p = "canterbury_province"
      else:
        p = "otago_province"
    prov_buckets[p].append(g)
  return {k: weld_union(gs, tol=0.005) for k, gs in prov_buckets.items()}


def main():
  D = build_austral_sources_and_domain_mask()
  itinerary = json5.load(open(os.path.join(AUSTRAL_DIR, "austral_itinerary.json5"), encoding="utf-8"))
  ch_by_idx = {c["index"]: c for c in itinerary["chapters"]}

  # Load enumerations for authentic modern/colonial anchor values
  aus_nz_enum = json.load(open(os.path.join(HGIS_RAW, "aus_nz_subadmin_enumerations.json"), encoding="utf-8"))
  pac_enum = json.load(open(os.path.join(HGIS_RAW, "pacific_ng_subadmin_enumerations.json"), encoding="utf-8"))

  print("\n[2] Building ALL 16 Chapter Areal Masks, Sibling JSON5s, Vector GeoJSONs & Optical QA Crops...", flush=True)

  # =========================================================================
  # CH 01: Pre-1788 Aboriginal Australia & Tasmania (-10000..1788) — Pure HydroBASINS AU L6!
  # =========================================================================
  def clf_aus_pre1788(lat, lon, pfaf, p3):
    if p3 == "569":
      return "tasmania"
    if p3 == "564":
      return "murray_darling"
    if p3 == "568":
      return "lake_eyre_basin"
    if p3 in ("566", "567"):
      return "central_arid_plateau"
    if p3 == "565":
      return "nullarbor_southern_gulfs"
    if p3 == "563":
      return "north_east_coast_cape_york" if lat > -28.0 else "south_east_coast_alps"
    if p3 == "562":
      if lon < 128.8:
        return "kimberley"
      if lon >= 141.6 and lat > -16.5:
        return "north_east_coast_cape_york"
      return "gulf_carpentaria_top_end"
    if p3 == "561":
      return "south_west_australia" if lat < -28.2 else "pilbara_western_coast"
    return "central_arid_plateau"

  b_aus = group_basins(D["hybas_au"], clf_aus_pre1788)
  # Attach Lord Howe & Norfolk islands to SE coast naturally
  lord_howe_g = filter_polygons_by_bbox(D["aus_adm1"]["New South Wales"], lambda lat, lon, p: lon > 158.0)
  b_aus["south_east_coast_alps"] = u_geoms([b_aus.get("south_east_coast_alps"), lord_howe_g, D["norfolk_g"]])
  ch1_zones = [
    {"id": "murray_darling", "name": "Murray-Darling Basin", "geom": b_aus["murray_darling"],
     "population": {"-10000": 48000, "-5000": 82000, "0": 135000, "1788": 185000}},
    {"id": "south_east_coast_alps", "name": "South-East Coast & Australian Alps", "geom": b_aus["south_east_coast_alps"],
     "population": {"-10000": 32000, "-5000": 54000, "0": 88000, "1788": 115000}},
    {"id": "tasmania", "name": "Tasmania & Bass Strait", "geom": b_aus["tasmania"],
     "population": {"-10000": 3200, "-5000": 4200, "0": 5200, "1788": 6000}},
    {"id": "north_east_coast_cape_york", "name": "North-East Coast & Cape York", "geom": b_aus["north_east_coast_cape_york"],
     "population": {"-10000": 42000, "-5000": 78000, "0": 122000, "1788": 165000}},
    {"id": "gulf_carpentaria_top_end", "name": "Gulf of Carpentaria & Top End", "geom": b_aus["gulf_carpentaria_top_end"],
     "population": {"-10000": 34000, "-5000": 58000, "0": 86000, "1788": 108000}},
    {"id": "kimberley", "name": "Kimberley & Fitzroy Basin", "geom": b_aus["kimberley"],
     "population": {"-10000": 16000, "-5000": 26000, "0": 38000, "1788": 46000}},
    {"id": "pilbara_western_coast", "name": "Pilbara & Western Coast", "geom": b_aus["pilbara_western_coast"],
     "population": {"-10000": 12000, "-5000": 20000, "0": 28000, "1788": 34000}},
    {"id": "south_west_australia", "name": "South-West Australia (Noongar)", "geom": b_aus["south_west_australia"],
     "population": {"-10000": 15000, "-5000": 26000, "0": 42000, "1788": 54000}},
    {"id": "lake_eyre_basin", "name": "Lake Eyre Endorheic Basin", "geom": b_aus["lake_eyre_basin"],
     "population": {"-10000": 8000, "-5000": 14000, "0": 21000, "1788": 26000}},
    {"id": "central_arid_plateau", "name": "Central Arid Western Plateau", "geom": b_aus["central_arid_plateau"],
     "population": {"-10000": 6000, "-5000": 10500, "0": 16000, "1788": 21000}},
    {"id": "nullarbor_southern_gulfs", "name": "Nullarbor & Southern Gulfs", "geom": b_aus["nullarbor_southern_gulfs"],
     "population": {"-10000": 7000, "-5000": 12000, "0": 19000, "1788": 25000}},
  ]
  write_chapter_assets(ch_by_idx[1], ch1_zones, D, chapter_clip_geom=D["aus_full"], wrap_pacific=False, bbox_override=(111, 160, -45, -9), drop_slivers=True, clip_vectors=False)

  # =========================================================================
  # CH 02: Pre-Colonial New Guinea & Bismarck Archipelago (-10000..1884) — Pure HydroBASINS L6!
  # =========================================================================
  def clf_ng_precol(lat, lon, pfaf, p3):
    if p3 == "536":
      return "bismarck_archipelago"
    if p3 == "538":
      return "papuan_peninsula_milne_bay"
    if p3 == "534" or (p3 == "531" and lon < 134.8):
      return "birds_head_raja_ampat"
    if p3 == "535":
      return "cenderawasih_mamberamo"
    # Main New Guinea island (531): group whole HydroBASINS L6 watersheds organically across 141E!
    if lon < 141.6:
      if lat >= -3.55:
        return "cenderawasih_mamberamo"
      if lat >= -4.95:
        return "western_highlands_baliem"
      return "southern_papuan_lowlands"
    if lon < 145.6:
      if lat >= -5.15:
        return "sepik_ramu"
      if lat >= -6.95:
        return "central_png_highlands"
      return "southern_papuan_lowlands"
    if lon < 147.9 and lat >= -7.75:
      return "huon_northern_coast"
    return "papuan_peninsula_milne_bay"

  b_ng = group_basins(D["hybas_ng"], clf_ng_precol)
  # Ensure Bismarck Archipelago includes all Bismarck islands cleanly
  b_ng["bismarck_archipelago"] = u_geoms([b_ng.get("bismarck_archipelago"), D["bismarck_g"]])
  ch2_zones = [
    {"id": "birds_head_raja_ampat", "name": "Bird's Head & Raja Ampat", "geom": b_ng["birds_head_raja_ampat"],
     "population": {"-10000": 18000, "-3000": 42000, "0": 75000, "1884": 135000}},
    {"id": "cenderawasih_mamberamo", "name": "Cenderawasih Bay & Mamberamo", "geom": b_ng["cenderawasih_mamberamo"],
     "population": {"-10000": 16000, "-3000": 38000, "0": 68000, "1884": 125000}},
    {"id": "western_highlands_baliem", "name": "Western Highlands & Baliem Valley", "geom": b_ng["western_highlands_baliem"],
     "population": {"-10000": 22000, "-3000": 85000, "0": 185000, "1884": 365000}},
    {"id": "southern_papuan_lowlands", "name": "Southern Papuan Lowlands (Digul-Fly)", "geom": b_ng["southern_papuan_lowlands"],
     "population": {"-10000": 18000, "-3000": 48000, "0": 95000, "1884": 175000}},
    {"id": "sepik_ramu", "name": "Sepik-Ramu Basin", "geom": b_ng["sepik_ramu"],
     "population": {"-10000": 24000, "-3000": 75000, "0": 145000, "1884": 265000}},
    {"id": "central_png_highlands", "name": "Central Highlands (Wahgi-Purari)", "geom": b_ng["central_png_highlands"],
     "population": {"-10000": 32000, "-3000": 145000, "0": 310000, "1884": 620000}},
    {"id": "huon_northern_coast", "name": "Huon Peninsula & Northern Coast", "geom": b_ng["huon_northern_coast"],
     "population": {"-10000": 16000, "-3000": 52000, "0": 98000, "1884": 180000}},
    {"id": "papuan_peninsula_milne_bay", "name": "Papuan Peninsula & Milne Bay", "geom": b_ng["papuan_peninsula_milne_bay"],
     "population": {"-10000": 20000, "-3000": 65000, "0": 125000, "1884": 220000}},
    {"id": "bismarck_archipelago", "name": "Bismarck Archipelago", "geom": b_ng["bismarck_archipelago"],
     "population": {"-10000": 14000, "-3000": 48000, "0": 88000, "1884": 155000}},
  ]
  write_chapter_assets(ch_by_idx[2], ch2_zones, D, chapter_clip_geom=D["ng_mainland_bismarck"], wrap_pacific=False, bbox_override=(129, 156, -12, 1), drop_slivers=True, clip_vectors=False)

  # =========================================================================
  # CH 03: Pre-Colonial Island Melanesia & Micronesia (-10000..1850)
  # =========================================================================
  slb_no_temotu = u_geoms([v for k, v in D["slb_adm1"].items() if k != "Temotu"] + [D["bougainville_g"]])
  ch3_zones = [
    {"id": "main_solomons", "name": "Main Solomon Islands (incl. Bougainville)", "geom": slb_no_temotu,
     "population": {"-10000": 8000, "-1500": 42000, "0": 78000, "1850": 135000}},
    {"id": "temotu_santa_cruz", "name": "Temotu / Santa Cruz Islands", "geom": D["slb_adm1"].get("Temotu"),
     "population": {"-10000": 0, "-1000": 4500, "0": 7500, "1850": 11000}},
    {"id": "vanuatu", "name": "Vanuatu Archipelago", "geom": D["vut_full"],
     "population": {"-10000": 0, "-1000": 18000, "0": 58000, "1850": 115000}},
    {"id": "new_caledonia_loyalty", "name": "New Caledonia & Loyalty Islands", "geom": D["ncl_full"],
     "population": {"-10000": 0, "-1000": 14000, "0": 42000, "1850": 65000}},
    {"id": "fiji_rotuma", "name": "Fiji & Rotuma", "geom": D["fji_full"],
     "population": {"-10000": 0, "-1000": 16000, "0": 68000, "1850": 145000}},
    {"id": "mariana_islands", "name": "Mariana Islands (Guam & CNMI)", "geom": u_geoms([D["gum_full"], D["mnp_full"]]),
     "population": {"-10000": 0, "-1500": 6000, "0": 24000, "1650": 42000, "1850": 9500}},
    {"id": "western_carolines_palau_yap", "name": "Western Carolines (Palau & Yap)", "geom": u_geoms([D["plw_full"], D["fsm_adm1"].get("Yap")]),
     "population": {"-10000": 0, "-1000": 8000, "0": 26000, "1850": 38000}},
    {"id": "central_eastern_carolines", "name": "Central-Eastern Carolines (Chuuk-Pohnpei-Kosrae)", "geom": u_geoms([D["fsm_adm1"].get(k) for k in ("Chuuk", "Pohnpei", "Kosrae")]),
     "population": {"-10000": 0, "0": 16000, "1000": 32000, "1850": 42000}},
    {"id": "marshall_islands", "name": "Marshall Islands", "geom": D["mhl_full"],
     "population": {"-10000": 0, "0": 6500, "1000": 12000, "1850": 15000}},
    {"id": "gilbert_islands_nauru", "name": "Gilbert Islands & Nauru", "geom": u_geoms([D["kir_full"], D["nru_full"]]),
     "population": {"-10000": 0, "0": 12000, "1000": 24000, "1850": 31000}},
  ]
  ch3_clip = u_geoms([z["geom"] for z in ch3_zones])
  write_chapter_assets(ch_by_idx[3], ch3_zones, D, chapter_clip_geom=ch3_clip, wrap_pacific=True, bbox_override=(129, 210, -25, 22))

  # =========================================================================
  # CH 04: Pre-Colonial Polynesia (-1000..1800) — NO Hawai'i, NO American Samoa!
  # =========================================================================
  pyf = D["pyf_adm1"]
  ch4_zones = [
    {"id": "tonga", "name": "Tonga Archipelago", "geom": D["ton_full"],
     "population": {"-1000": 2500, "0": 16000, "1000": 28000, "1800": 36000}},
    {"id": "samoa_wallis_futuna", "name": "Independent Samoa & Wallis-Futuna", "geom": u_geoms([D["wsm_full"], D["wlf_full"]]),
     "population": {"-1000": 2000, "0": 18000, "1000": 34000, "1800": 46000}},
    {"id": "society_islands", "name": "Society Islands (Windward & Leeward)", "geom": u_geoms([pyf.get("ÎlesduVent"), pyf.get("ÎlesSous-le-Vent")]),
     "population": {"-1000": 0, "500": 8000, "1200": 38000, "1770": 68000, "1800": 42000}},
    {"id": "marquesas_islands", "name": "Marquesas Islands", "geom": pyf.get("ÎlesMarquises"),
     "population": {"-1000": 0, "500": 6000, "1200": 28000, "1790": 45000, "1800": 38000}},
    {"id": "tuamotu_gambier", "name": "Tuamotu & Gambier Islands", "geom": pyf.get("ÎlesTuamotu-Gambier"),
     "population": {"-1000": 0, "800": 3500, "1400": 8500, "1800": 11000}},
    {"id": "austral_islands", "name": "Austral Islands", "geom": pyf.get("ÎlesAustrales"),
     "population": {"-1000": 0, "1000": 4000, "1500": 9500, "1800": 11000}},
    {"id": "cook_islands_niue", "name": "Cook Islands & Niue", "geom": u_geoms([D["cok_full"], D["niu_full"]]),
     "population": {"-1000": 0, "800": 6500, "1400": 16000, "1800": 21000}},
    {"id": "tuvalu_tokelau", "name": "Tuvalu & Tokelau", "geom": u_geoms([D["tuv_full"], D["tkl_full"]]),
     "population": {"-1000": 0, "500": 2000, "1200": 4200, "1800": 5200}},
    {"id": "rapa_nui_pitcairn", "name": "Rapa Nui & Pitcairn", "geom": u_geoms([D["rapanui_full"], D["pcn_full"]]),
     "population": {"-1000": 0, "1000": 1200, "1550": 9500, "1800": 3200}},
  ]
  ch4_clip = u_geoms([z["geom"] for z in ch4_zones])
  write_chapter_assets(ch_by_idx[4], ch4_zones, D, chapter_clip_geom=ch4_clip, wrap_pacific=True, bbox_override=(172, 255, -30, -3))

  # =========================================================================
  # CH 05: Pre-European New Zealand (700..1840) — Pure HydroBASINS AU L6!
  # =========================================================================
  def clf_nz_precol(lat, lon, pfaf, p3):
    if p3 == "573":
      return "murihiku_southland_chathams"
    if p3 == "571":
      if lat >= -37.25:
        return "te_tai_tokerau_auckland"
      if lat >= -38.85 and lon < 176.65:
        return "waikato_bay_of_plenty"
      if lon >= 176.35 and lat >= -40.55:
        return "east_coast_hawkes_bay"
      return "taranaki_cook_strait"
    if p3 == "572":
      if lat >= -42.35 or (lon < 170.85 and lat >= -44.65):
        return "northern_south_island_west_coast"
      if lat >= -45.95 and lon >= 168.85:
        return "canterbury_otago"
      return "murihiku_southland_chathams"
    return "murihiku_southland_chathams"

  b_nz = group_basins(D["hybas_nz"], clf_nz_precol)
  b_nz["murihiku_southland_chathams"] = u_geoms([b_nz.get("murihiku_southland_chathams"), D["nzl_adm1"].get("Chatham Islands Territory")])
  ch5_zones = [
    {"id": "te_tai_tokerau_auckland", "name": "Te Tai Tokerau (Northland & Tāmaki)", "geom": b_nz["te_tai_tokerau_auckland"],
     "population": {"700": 0, "1300": 1800, "1500": 12000, "1769": 28000, "1840": 22500}},
    {"id": "waikato_bay_of_plenty", "name": "Waikato, Hauraki & Bay of Plenty", "geom": b_nz["waikato_bay_of_plenty"],
     "population": {"700": 0, "1300": 1500, "1500": 11000, "1769": 26000, "1840": 21000}},
    {"id": "east_coast_hawkes_bay", "name": "Tairāwhiti (East Coast) & Hawke's Bay", "geom": b_nz["east_coast_hawkes_bay"],
     "population": {"700": 0, "1300": 900, "1500": 6800, "1769": 17500, "1840": 14000}},
    {"id": "taranaki_cook_strait", "name": "Taranaki, Whanganui & Cook Strait", "geom": b_nz["taranaki_cook_strait"],
     "population": {"700": 0, "1300": 1000, "1500": 6500, "1769": 17000, "1840": 13500}},
    {"id": "northern_south_island_west_coast", "name": "Te Tauihu & Te Tai Poutini (West Coast)", "geom": b_nz["northern_south_island_west_coast"],
     "population": {"700": 0, "1300": 800, "1500": 2200, "1769": 4200, "1840": 3200}},
    {"id": "canterbury_otago", "name": "Waitaha (Canterbury) & Ōtākou (Otago)", "geom": b_nz["canterbury_otago"],
     "population": {"700": 0, "1300": 1200, "1500": 2800, "1769": 4800, "1840": 3800}},
    {"id": "murihiku_southland_chathams", "name": "Murihiku (Southland), Rakiura & Chathams", "geom": b_nz["murihiku_southland_chathams"],
     "population": {"700": 0, "1300": 700, "1500": 1800, "1769": 2500, "1840": 2000}},
  ]
  write_chapter_assets(ch_by_idx[5], ch5_zones, D, chapter_clip_geom=D["nzl_full"], wrap_pacific=True, bbox_override=(165, 185, -48, -33.5), drop_slivers=True, clip_vectors=False)

  # =========================================================================
  # CH 06: Colonial Australia (1788..1901) — 6 Colonies (SA UNITED with NT; NSW incl. pre-1911 ACT!)
  # =========================================================================
  A = D["aus_adm1"]
  aus_s = aus_nz_enum["australia"]["colonial_and_state_annual_31dec_1788_2025"]["series_by_year"]
  def aus_val(yr_s, st):
    return int(aus_s.get(str(yr_s), {}).get(st, 0) or 0)

  ch6_zones = [
    {"id": "colony_nsw", "name": "Colony of New South Wales (incl. ACT)", "geom": u_geoms([weld_union([A["New South Wales"], A["Australian Capital Territory"]], tol=0.008), A["Norfolk Island"]]),
     "population": {"1788": 49000, "1820": 72000, "1851": 215000, "1881": 788000, "1901": aus_val(1901, "New South Wales") + 7434}},
    {"id": "colony_victoria", "name": "Colony of Victoria", "geom": A["Victoria"],
     "population": {"1788": 15000, "1836": 12000, "1851": 97489, "1881": 874000, "1901": aus_val(1901, "Victoria") + 850}},
    {"id": "colony_queensland", "name": "Colony of Queensland", "geom": A["Queensland"],
     "population": {"1788": 120000, "1824": 98000, "1860": 88055, "1881": 262000, "1901": aus_val(1901, "Queensland") + 27500}},
    {"id": "colony_south_australia_nt", "name": "Colony of South Australia (incl. NT)", "geom": weld_union([A["South Australia"], A["Northern Territory"]], tol=0.008),
     "population": {"1788": 65000, "1836": 64000, "1861": 188000, "1881": 332000, "1901": aus_val(1901, "South Australia") + aus_val(1901, "Northern Territory") + 32123}},
    {"id": "colony_western_australia", "name": "Colony of Western Australia", "geom": A["Western Australia"],
     "population": {"1788": 62000, "1829": 58000, "1861": 60200, "1881": 65600, "1901": aus_val(1901, "Western Australia") + 26500}},
    {"id": "colony_tasmania", "name": "Colony of Tasmania (Van Diemen's Land)", "geom": A["Tasmania"],
     "population": {"1788": 4500, "1825": 16200, "1851": 70130, "1881": 118900, "1901": aus_val(1901, "Tasmania") + 157}},
  ]
  write_chapter_assets(ch_by_idx[6], ch6_zones, D, chapter_clip_geom=D["aus_full"], wrap_pacific=False, bbox_override=(111, 160, -45, -9), drop_slivers=True, clip_vectors=False)

  # =========================================================================
  # CH 07: Colonial New Zealand (1840..1907) — Authentic 1853-1876 10 Provinces + Chathams!
  # =========================================================================
  nzp = build_nz_colonial_provinces(D["nzl_adm2"])
  nz_p_s = aus_nz_enum["new_zealand"]["provincial_non_maori_censuses_1851_1921"]["series_by_year"]
  def nz_p(yr_s, key):
    d = nz_p_s.get(str(yr_s), {})
    if key in d and d[key] is not None:
      return int(d[key])
    if key == "Otago":
      return int(d.get("Otago (Otago portion)", 0) or 0)
    if key == "Southland":
      return int(d.get("Otago (Southland portion)", 0) or 0)
    return 0

  ch7_zones = [
    {"id": "auckland_province", "name": "Auckland Province", "geom": nzp["auckland_province"],
     "population": {"1840": 48000, "1861": nz_p(1861, "Auckland") + 35000, "1881": nz_p(1881, "Auckland") + 28000, "1901": nz_p(1901, "Auckland") + 28000}},
    {"id": "taranaki_province", "name": "Taranaki Province", "geom": nzp["taranaki_province"],
     "population": {"1840": 5000, "1861": nz_p(1861, "Taranaki") + 2800, "1881": nz_p(1881, "Taranaki") + 3200, "1901": nz_p(1901, "Taranaki") + 3200}},
    {"id": "hawkes_bay_province", "name": "Hawke's Bay Province", "geom": nzp["hawkes_bay_province"],
     "population": {"1840": 7500, "1861": nz_p(1861, "Hawke's Bay") + 4200, "1881": nz_p(1881, "Hawke's Bay") + 3800, "1901": nz_p(1901, "Hawke's Bay") + 4200}},
    {"id": "wellington_province", "name": "Wellington Province", "geom": nzp["wellington_province"],
     "population": {"1840": 11500, "1861": nz_p(1861, "Wellington") + 7500, "1881": nz_p(1881, "Wellington") + 6200, "1901": nz_p(1901, "Wellington") + 6800}},
    {"id": "nelson_province", "name": "Nelson Province", "geom": nzp["nelson_province"],
     "population": {"1840": 2200, "1861": nz_p(1861, "Nelson") + 900, "1881": nz_p(1881, "Nelson") + 600, "1901": nz_p(1901, "Nelson") + 500}},
    {"id": "marlborough_province", "name": "Marlborough Province", "geom": nzp["marlborough_province"],
     "population": {"1840": 1000, "1861": nz_p(1861, "Marlborough") + 350, "1881": nz_p(1881, "Marlborough") + 350, "1901": nz_p(1901, "Marlborough") + 400}},
    {"id": "westland_province", "name": "Westland Province", "geom": nzp["westland_province"],
     "population": {"1840": 600, "1861": 800, "1881": nz_p(1881, "Westland") + 200, "1901": nz_p(1901, "Westland") + 150}},
    {"id": "canterbury_province", "name": "Canterbury Province", "geom": nzp["canterbury_province"],
     "population": {"1840": 2200, "1861": nz_p(1861, "Canterbury") + 600, "1881": nz_p(1881, "Canterbury") + 650, "1901": nz_p(1901, "Canterbury") + 950}},
    {"id": "otago_province", "name": "Otago Province", "geom": nzp["otago_province"],
     "population": {"1840": 1800, "1861": nz_p(1861, "Otago") + 500, "1881": nz_p(1881, "Otago") + 550, "1901": nz_p(1901, "Otago") + 650}},
    {"id": "southland_province", "name": "Southland Province", "geom": nzp["southland_province"],
     "population": {"1840": 900, "1861": nz_p(1861, "Southland") + 300, "1881": max(24000, nz_p(1881, "Southland")) + 300, "1901": max(46000, nz_p(1901, "Southland")) + 300}},
    {"id": "chatham_islands", "name": "Chatham Islands", "geom": nzp["chatham_islands"],
     "population": {"1840": 650, "1861": 560, "1881": 450, "1901": 420}},
  ]
  write_chapter_assets(ch_by_idx[7], ch7_zones, D, chapter_clip_geom=D["nzl_full"], wrap_pacific=True, bbox_override=(165, 185, -48, -33.5), drop_slivers=True)

  # =========================================================================
  # CH 08: Colonial New Guinea (1884..1975) — Authentic Tri-Colonial Partition!
  # =========================================================================
  papua_provs = [
    "Western Province", "Gulf Province", "Central Province", "National Capital District",
    "Milne Bay Province", "Northern (Oro) Province", "Southern Highlands Province", "Hela Province"
  ]
  papua_g = weld_union([D["png_adm1"].get(k) for k in papua_provs], tol=0.008)
  tng_g = weld_union([v for k, v in D["png_adm1"].items() if k not in papua_provs], tol=0.008)
  dutch_ng_g = weld_union(list(D["idn_papua_adm1"].values()), tol=0.008)
  ch8_zones = [
    {"id": "dutch_west_new_guinea", "name": "Dutch West New Guinea (Nederlands Nieuw-Guinea)", "geom": dutch_ng_g,
     "population": {"1884": 680000, "1930": 710000, "1955": 730000, "1971": 923440}},
    {"id": "german_territory_new_guinea", "name": "German New Guinea / Territory of New Guinea", "geom": tng_g,
     "population": {"1884": 1150000, "1921": 1050000, "1954": 1290000, "1971": 1795000}},
    {"id": "british_australian_papua", "name": "British / Australian Territory of Papua", "geom": papua_g,
     "population": {"1884": 420000, "1921": 380000, "1954": 440000, "1971": 695000}},
  ]
  write_chapter_assets(ch_by_idx[8], ch8_zones, D, chapter_clip_geom=D["ng_all_with_boug"], wrap_pacific=False, bbox_override=(129, 160, -12, 1), drop_slivers=True, clip_vectors=False)

  # =========================================================================
  # CH 09: Colonial Island Melanesia (1850..1970)
  # =========================================================================
  ch9_zones = [
    {"id": "british_solomon_islands", "name": "British Solomon Islands Protectorate", "geom": D["slb_full"],
     "population": {"1850": 110000, "1900": 95000, "1931": 94066, "1959": 124076, "1970": 160998}},
    {"id": "anglo_french_new_hebrides", "name": "Anglo-French New Hebrides", "geom": D["vut_full"],
     "population": {"1850": 115000, "1900": 62000, "1935": 45000, "1967": 77988}},
    {"id": "french_new_caledonia", "name": "French New Caledonia & Dependencies", "geom": D["ncl_full"],
     "population": {"1850": 65000, "1887": 62752, "1921": 47505, "1956": 68480, "1969": 100579}},
    {"id": "colony_of_fiji_rotuma", "name": "Colony of Fiji & Rotuma", "geom": D["fji_full"],
     "population": {"1850": 145000, "1881": 127486, "1921": 157266, "1946": 259638, "1966": 476727}},
  ]
  ch9_clip = u_geoms([z["geom"] for z in ch9_zones])
  write_chapter_assets(ch_by_idx[9], ch9_zones, D, chapter_clip_geom=ch9_clip, wrap_pacific=True, bbox_override=(153, 186, -24, -5))

  # =========================================================================
  # CH 10: Colonial Micronesia (1668..1979)
  # =========================================================================
  ch10_zones = [
    {"id": "guam", "name": "Guam", "geom": D["gum_full"],
     "population": {"1668": 25000, "1783": 3231, "1901": 9676, "1940": 22290, "1970": 84996}},
    {"id": "northern_mariana_islands", "name": "Northern Mariana Islands", "geom": D["mnp_full"],
     "population": {"1668": 15000, "1850": 950, "1935": 44025, "1958": 8290, "1973": 14333}},
    {"id": "palau", "name": "Palau (Belau)", "geom": D["plw_full"],
     "population": {"1668": 24000, "1900": 4200, "1935": 12798, "1958": 8884, "1973": 12673}},
    {"id": "yap", "name": "Yap District", "geom": D["fsm_adm1"].get("Yap"),
     "population": {"1668": 14000, "1900": 7500, "1935": 6006, "1958": 5540, "1973": 7870}},
    {"id": "chuuk", "name": "Chuuk (Truk) District", "geom": D["fsm_adm1"].get("Chuuk"),
     "population": {"1668": 16000, "1900": 13000, "1935": 17133, "1958": 20124, "1973": 31609}},
    {"id": "pohnpei_kosrae", "name": "Pohnpei & Kosrae Districts", "geom": u_geoms([D["fsm_adm1"].get("Pohnpei"), D["fsm_adm1"].get("Kosrae")]),
     "population": {"1668": 14000, "1900": 6200, "1935": 11467, "1958": 14335, "1973": 23252}},
    {"id": "marshall_islands", "name": "Marshall Islands", "geom": D["mhl_full"],
     "population": {"1668": 15000, "1900": 11000, "1935": 10446, "1958": 13928, "1973": 25045}},
    {"id": "gilbert_islands", "name": "Gilbert Islands (GEIC / Kiribati)", "geom": D["kir_full"],
     "population": {"1668": 28000, "1900": 26500, "1931": 29751, "1963": 43336, "1978": 56213}},
    {"id": "nauru", "name": "Nauru", "geom": D["nru_full"],
     "population": {"1668": 1400, "1900": 1500, "1933": 2641, "1961": 4613, "1977": 7254}},
  ]
  ch10_clip = u_geoms([z["geom"] for z in ch10_zones])
  write_chapter_assets(ch_by_idx[10], ch10_zones, D, chapter_clip_geom=ch10_clip, wrap_pacific=True, bbox_override=(129, 210, -5, 22))

  # =========================================================================
  # CH 11: Colonial Polynesia (1800..1962)
  # =========================================================================
  ch11_zones = [
    {"id": "kingdom_of_tonga", "name": "Kingdom of Tonga", "geom": D["ton_full"],
     "population": {"1800": 36000, "1891": 19196, "1921": 24937, "1956": 56838}},
    {"id": "western_samoa", "name": "Western Samoa (German / NZ Mandate)", "geom": D["wsm_full"],
     "population": {"1800": 42000, "1900": 32815, "1921": 36422, "1961": 114427}},
    {"id": "french_establishments_oceania", "name": "French Establishments in Oceania", "geom": D["pyf_full"],
     "population": {"1800": 102000, "1881": 25247, "1926": 35862, "1962": 84551}},
    {"id": "cook_islands_niue", "name": "Cook Islands & Niue", "geom": u_geoms([D["cok_full"], D["niu_full"]]),
     "population": {"1800": 21000, "1902": 12292, "1936": 16350, "1961": 23242}},
    {"id": "ellice_islands_tokelau", "name": "Ellice Islands (Tuvalu) & Tokelau", "geom": u_geoms([D["tuv_full"], D["tkl_full"]]),
     "population": {"1800": 5200, "1900": 4400, "1931": 5140, "1963": 7315}},
    {"id": "wallis_futuna", "name": "Wallis & Futuna", "geom": D["wlf_full"],
     "population": {"1800": 4500, "1900": 5400, "1936": 6019, "1969": 8546}},
    {"id": "pitcairn_rapa_nui", "name": "Pitcairn & Rapa Nui (Easter Island)", "geom": u_geoms([D["pcn_full"], D["rapanui_full"]]),
     "population": {"1800": 3200, "1877": 200, "1934": 656, "1960": 1260}},
  ]
  ch11_clip = u_geoms([z["geom"] for z in ch11_zones])
  write_chapter_assets(ch_by_idx[11], ch11_zones, D, chapter_clip_geom=ch11_clip, wrap_pacific=True, bbox_override=(172, 255, -30, -3))

  # =========================================================================
  # CH 12: Modern Australia (1901..2026, is_admin1: true) — Official 8 States/Territories + Norfolk
  # =========================================================================
  ch12_zones = []
  for st_nm, slug in [
    ("New South Wales", "new_south_wales"),
    ("Victoria", "victoria"),
    ("Queensland", "queensland"),
    ("South Australia", "south_australia"),
    ("Western Australia", "western_australia"),
    ("Tasmania", "tasmania"),
    ("Northern Territory", "northern_territory"),
    ("Australian Capital Territory", "australian_capital_territory"),
    ("Norfolk Island", "norfolk_island"),
  ]:
    if st_nm == "Norfolk Island":
      pop_d = {"1901": 827, "1961": 844, "2001": 2601, "2021": 2188, "2025": 2220}
    else:
      pop_d = {str(y): max(1000, aus_val(y, st_nm)) for y in (1901, 1921, 1947, 1971, 1991, 2011, 2025)}
      if st_nm == "Australian Capital Territory":
        pop_d["1901"] = 1500
    ch12_zones.append({"id": slug, "name": st_nm, "geom": A[st_nm], "population": pop_d})
  write_chapter_assets(ch_by_idx[12], ch12_zones, D, chapter_clip_geom=D["aus_full"], wrap_pacific=False, bbox_override=(111, 169, -45, -9))

  # =========================================================================
  # CH 13: Modern New Zealand (1907..2026, is_admin1: true) — Official 16 Regional Councils + Chathams
  # =========================================================================
  nz_reg_s = aus_nz_enum["new_zealand"]["regional_councils_1991_2023"]["series_by_year"]
  nz_name_map = {
    "Northland Region": "Northland", "Auckland Region": "Auckland", "Waikato Region": "Waikato",
    "Bay of Plenty Region": "Bay of Plenty", "Gisborne Region": "Gisborne", "Hawke's Bay Region": "Hawke's Bay",
    "Taranaki Region": "Taranaki", "Manawatu-Wanganui Region": "Manawatū-Whanganui", "Wellington Region": "Wellington",
    "West Coast Region": "West Coast", "Canterbury Region": "Canterbury", "Otago Region": "Otago",
    "Southland Region": "Southland", "Tasman Region": "Tasman", "Nelson Region": "Nelson",
    "Marlborough Region": "Marlborough", "Chatham Islands Territory": "Area Outside",
  }
  ch13_zones = []
  for rname, g in D["nzl_adm1"].items():
    ek = nz_name_map.get(rname, rname.replace(" Region", ""))
    p91 = int(nz_reg_s["1991"].get(ek, 5000))
    p06 = int(nz_reg_s["2006"].get(ek, p91))
    p23 = int(nz_reg_s["2023"].get(ek, p06))
    slug = rname.lower().replace("'", "").replace(" ", "_").replace("-", "_")
    ch13_zones.append({
      "id": slug, "name": rname, "geom": g,
      "population": {"1911": max(400, int(round(p91 * 0.31))), "1951": max(450, int(round(p91 * 0.57))), "1991": p91, "2006": p06, "2023": p23},
    })
  write_chapter_assets(ch_by_idx[13], ch13_zones, D, chapter_clip_geom=D["nzl_full"], wrap_pacific=True, bbox_override=(165, 185, -48, -33.5))

  # =========================================================================
  # CH 14: Modern New Guinea (1962..2026, is_admin1: true) — PNG 22 Provinces + IDN Papua 6 Provinces
  # =========================================================================
  png_enum_adm1 = pac_enum["new_guinea"]["papua_new_guinea"]["adm1_provinces"]
  idn_enum_adm1 = pac_enum["new_guinea"]["indonesian_west_new_guinea"]["adm1_provinces_post2022"]

  def match_png_pop(pnm):
    low = pnm.lower()
    for k, v in png_enum_adm1.items():
      kl = k.lower()
      if kl.split("(")[0].strip() in low or low.replace(" province", "") in kl:
        return {str(yk): int(yv) for yk, yv in v.items() if str(yk).isdigit()}
    return {"1980": 120000, "2000": 210000, "2011": 290000, "2024": 400000}

  ch14_zones = []
  for pnm, g in sorted(D["png_adm1"].items()):
    slug = "png_" + pnm.lower().replace("(", "").replace(")", "").replace(" ", "_").replace("-", "_")
    ch14_zones.append({"id": slug, "name": pnm.replace(" Province", ""), "geom": g, "population": match_png_pop(pnm)})
  for pnm, g in sorted(D["idn_papua_adm1"].items()):
    slug = "idn_" + pnm.lower().replace(" ", "_")
    ed = idn_enum_adm1.get(pnm, {})
    pop_d = {"1971": int(round(ed.get("2010", 500000) * 0.25)), "2010": int(ed.get("2010", 500000)),
             "2020": int(ed.get("2020", 700000)), "2023": int(ed.get("2023_bps_est", 750000))}
    ch14_zones.append({"id": slug, "name": pnm, "geom": g, "population": pop_d})
  write_chapter_assets(ch_by_idx[14], ch14_zones, D, chapter_clip_geom=D["ng_all_with_boug"], wrap_pacific=False, bbox_override=(129, 160, -12, 1))

  # =========================================================================
  # CH 15: Modern Island Melanesia & Micronesia (1960..2026, is_admin1: true) — 36 Official Admin-1!
  # =========================================================================
  mel_e = pac_enum["island_melanesia"]
  mic_e = pac_enum["micronesia"]
  ch15_zones = []

  # Fiji 4 divisions + Rotuma
  for dnm, g in D["fji_adm1"].items():
    if dnm == "Rotuma":
      pop_d = {"1966": 3365, "1986": 2688, "2007": 2002, "2017": 1594}
    else:
      key = dnm.replace(" Division", "")
      ed = mel_e["fiji"]["adm1_divisions"].get(key, {})
      pop_d = {str(y): int(v) for y, v in ed.items()} or {"1986": 100000, "2017": 150000}
    ch15_zones.append({"id": "fji_" + dnm.lower().replace(" ", "_"), "name": f"Fiji: {dnm}", "geom": g, "population": pop_d})

  # Solomons 10 provinces
  slb_e = mel_e["solomon_islands"]["adm1_provinces_and_honiara"]
  for pnm, g in sorted(D["slb_adm1"].items()):
    matched = None
    for k, v in slb_e.items():
      if pnm.lower()[:5] in k.lower() or ("honiara" in pnm.lower() and "honiara" in k.lower()):
        matched = {str(y): int(val) for y, val in v.items() if str(y).isdigit()}
        break
    ch15_zones.append({"id": "slb_" + pnm.lower().replace("(", "").replace(")", "").replace(" ", "_"), "name": f"SLB: {pnm}", "geom": g,
                       "population": matched or {"1976": 18000, "1999": 35000, "2019": 62000}})

  # Vanuatu 6 provinces
  vut_e = mel_e["vanuatu"]["adm1_provinces"]
  for pnm, g in sorted(D["vut_adm1"].items()):
    ed = vut_e.get(pnm, {})
    pop_d = {str(y): int(v) for y, v in ed.items() if str(y).isdigit()} or {"1989": 22000, "2020": 48000}
    ch15_zones.append({"id": "vut_" + pnm.lower(), "name": f"VUT: {pnm}", "geom": g, "population": pop_d})

  # New Caledonia 3 provinces
  ncl_e = mel_e["new_caledonia"]["adm1_provinces"]
  ncl_map = {"Sud": "Province Sud", "Nord": "Province Nord", "ÎlesLoyauté": "Province des Îles Loyauté"}
  for pnm, g in sorted(D["ncl_adm1"].items()):
    ek = ncl_map.get(pnm, pnm)
    ed = ncl_e.get(ek, {})
    pop_d = {str(y): int(v) for y, v in ed.items() if str(y).isdigit()} or {"1989": 35000, "2019": 60000}
    ch15_zones.append({"id": "ncl_" + pnm.lower().replace("î", "i").replace("é", "e"), "name": f"NCL: {ek}", "geom": g, "population": pop_d})

  # FSM 4 states
  fsm_e = mic_e["federated_states_of_micronesia"]["adm1_states"]
  for snm, g in sorted(D["fsm_adm1"].items()):
    ed = fsm_e.get(snm, {})
    pop_d = {str(y): int(v) for y, v in ed.items() if str(y).isdigit()} or {"1973": 15000, "2010": 25000}
    ch15_zones.append({"id": "fsm_" + snm.lower(), "name": f"FSM: {snm}", "geom": g, "population": pop_d})

  # Kiribati 3 groups
  kir_e = mic_e["kiribati"]["adm1_island_groups"]
  for gnm, g in sorted(D["kir_adm1"].items()):
    matched = None
    for k, v in kir_e.items():
      if gnm.split()[0].lower() in k.lower():
        matched = {str(y): int(val) for y, val in v.items() if str(y).isdigit()}
        break
    ch15_zones.append({"id": "kir_" + gnm.lower().replace(" ", "_"), "name": f"KIR: {gnm}", "geom": g,
                       "population": matched or {"1978": 2000, "2020": 5000}})

  # Marshalls, Palau, Guam, CNMI, Nauru
  for slug, lbl, g, ekey in [
    ("marshall_islands", "Marshall Islands", D["mhl_full"], "marshall_islands"),
    ("palau", "Palau", D["plw_full"], "palau"),
    ("guam", "Guam", D["gum_full"], "guam"),
    ("cnmi", "Northern Mariana Islands", D["mnp_full"], "northern_mariana_islands"),
    ("nauru", "Nauru", D["nru_full"], "nauru"),
  ]:
    ht = mic_e[ekey]["historical_national_totals"]
    pop_d = {str(y): int(v) for y, v in ht.items() if str(y).isdigit() and int(y) >= 1958}
    ch15_zones.append({"id": slug, "name": lbl, "geom": g, "population": pop_d})

  ch15_clip = u_geoms([z["geom"] for z in ch15_zones])
  write_chapter_assets(ch_by_idx[15], ch15_zones, D, chapter_clip_geom=ch15_clip, wrap_pacific=True, bbox_override=(129, 210, -25, 22))

  # =========================================================================
  # CH 16: Modern Polynesia (1960..2026, is_admin1: true) — 18 Official Admin-1/Polities!
  # =========================================================================
  pol_e = pac_enum["polynesia_excl_hawaii_american_samoa"]
  ch16_zones = []
  # Samoa
  wsm_ht = {str(y): int(v) for y, v in pol_e["samoa"]["historical_national_totals"].items() if str(y).isdigit() and int(y) >= 1960}
  ch16_zones.append({"id": "samoa", "name": "Samoa", "geom": D["wsm_full"], "population": wsm_ht})
  # Tonga 5 divisions
  ton_e = pol_e["tonga"]["adm1_divisions"]
  for dnm, g in sorted(D["ton_adm1"].items()):
    matched = None
    for k, v in ton_e.items():
      if dnm.lower().replace("'", "") in k.lower().replace("'", "").replace("ʻ", ""):
        matched = {str(y): int(val) for y, val in v.items() if str(y).isdigit()}
        break
    ch16_zones.append({"id": "ton_" + dnm.lower().replace("'", ""), "name": f"Tonga: {dnm}", "geom": g,
                       "population": matched or {"1976": 5000, "2021": 8000}})
  # French Polynesia 5 subdivisions
  pyf_e = pol_e["french_polynesia"]["adm1_subdivisions"]
  pyf_lbl_map = {
    "ÎlesduVent": ("Windward Islands", "Îles du Vent"),
    "ÎlesSous-le-Vent": ("Leeward Islands", "Îles Sous-le-Vent"),
    "ÎlesMarquises": ("Marquesas Islands", "Îles Marquises"),
    "ÎlesAustrales": ("Austral Islands", "Îles Australes"),
    "ÎlesTuamotu-Gambier": ("Tuamotu-Gambier", "Îles Tuamotu-Gambier"),
  }
  for snm, g in sorted(D["pyf_adm1"].items()):
    en_lbl, match_tok = pyf_lbl_map.get(snm, (snm, snm))
    matched = None
    for k, v in pyf_e.items():
      if en_lbl.split()[0].lower() in k.lower() or match_tok.split()[-1].lower() in k.lower():
        matched = {str(y): int(val) for y, val in v.items() if str(y).isdigit()}
        break
    ch16_zones.append({"id": "pyf_" + en_lbl.lower().replace(" ", "_").replace("-", "_"), "name": f"PYF: {en_lbl}", "geom": g,
                       "population": matched or {"1977": 8000, "2022": 12000}})
  # Cook Islands, Tuvalu, Niue, Tokelau, Wallis & Futuna, Pitcairn, Rapa Nui
  for slug, lbl, g, ekey in [
    ("cook_islands", "Cook Islands", D["cok_full"], "cook_islands"),
    ("tuvalu", "Tuvalu", D["tuv_full"], "tuvalu"),
    ("niue", "Niue", D["niu_full"], "niue"),
    ("tokelau", "Tokelau", D["tkl_full"], "tokelau"),
    ("wallis_futuna", "Wallis & Futuna", D["wlf_full"], "wallis_and_futuna"),
    ("pitcairn", "Pitcairn Islands", D["pcn_full"], "pitcairn_islands"),
    ("rapa_nui", "Rapa Nui (Easter Island)", D["rapanui_full"], "rapa_nui_easter_island"),
  ]:
    ht = pol_e[ekey].get("historical_national_totals") or pol_e[ekey].get("historical_totals") or {}
    pop_d = {str(y): int(v) for y, v in ht.items() if str(y).isdigit() and int(y) >= 1955}
    if not pop_d:
      pop_d = {"1960": 1000, "2020": 1500}
    ch16_zones.append({"id": slug, "name": lbl, "geom": g, "population": pop_d})

  ch16_clip = u_geoms([z["geom"] for z in ch16_zones])
  write_chapter_assets(ch_by_idx[16], ch16_zones, D, chapter_clip_geom=ch16_clip, wrap_pacific=True, bbox_override=(172, 255, -30, -3))

  # =========================================================================
  # [3] Write master manifest `AUSTRAL/austral_areal_masks.json5`
  # =========================================================================
  specialist_masks = []
  national_epoch_masks = []
  chapter_masks = []
  for ch in itinerary["chapters"]:
    stem = ch["key"]
    entry = {
      "id": stem,
      "domain": ch["domain"],
      "domain_group": "sites_austral_oceania",
      "json5_path": f"histmap/1.data_raw/population_regional/AUSTRAL/{ch['folder']}/{stem}.json5",
      "mask_path": f"histmap/1.data_raw/population_regional/AUSTRAL/{ch['folder']}/{stem}_areal_mask.png",
      "priority": ch["priority"],
    }
    if ch.get("is_admin1"):
      entry["is_admin1"] = True
    chapter_masks.append(entry)
    if ch["region_group"] == "1.precolonial":
      specialist_masks.append(entry)
    else:
      national_epoch_masks.append(entry)

  manifest = {
    "grid_dimensions": [GRID_W, GRID_H],
    "regime_transitions": {
      "australia": {"pre_admin_end": 1788, "colonial_start": 1788, "contemporary_start": 1901},
      "new_zealand": {"pre_admin_end": 1840, "colonial_start": 1840, "contemporary_start": 1907},
      "new_guinea": {"pre_admin_end": 1884, "colonial_start": 1884, "contemporary_start": 1962},
      "island_melanesia": {"pre_admin_end": 1850, "colonial_start": 1850, "contemporary_start": 1960},
      "micronesia": {"pre_admin_end": 1668, "colonial_start": 1668, "contemporary_start": 1960},
      "polynesia": {"pre_admin_end": 1800, "colonial_start": 1800, "contemporary_start": 1960},
    },
    "geography_profile": {
      "projection_class": "equirectangular_pacific_wrapped",
      "has_micro_islands": True,
      "max_adm2_area_km2": 50000,
      "note": "Australia, Tasmania, Norfolk/Lord Howe, New Zealand incl. Chathams, whole New Guinea incl. West Papua & Raja Ampat, Bismarcks, Solomons, Vanuatu, New Caledonia, Fiji, Micronesia, and Polynesia excl. Hawai'i and American Samoa.",
    },
    "script_profile": {
      "target_scripts": ["Latn"],
      "allow_native_toponyms": True,
    },
    "hyde_years": ALL_HYDE_YEARS,
    "substrata_sources": {
      "sites_austral_oceania": {
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/AUSTRAL/_shared/sites_austral_oceania/config/documented_site_pixels.json",
        "domain": [-10000, 2025],
        "domain_code": 1,
        "domain_mask_png": "histmap/1.data_raw/population_regional/AUSTRAL/_shared/sites_austral_oceania/config/austral_domain_mask.png",
        "rasters_folder": "histmap/1.data_raw/population_regional/AUSTRAL/_shared/sites_austral_oceania/2.population_rasters",
        "sample_year": 1800,
      }
    },
    "smoothing": {
      "border_feather_radius_px": 6,
      "interior_multiplier_blur_passes": 4,
      "interior_multiplier_blur_radius_px": 8,
      "temporal_log_Laplacian_weight": 0.15,
    },
    "specialist_masks": specialist_masks,
    "national_epoch_masks": national_epoch_masks,
    "chapter_masks": chapter_masks,
  }
  manifest_path = os.path.join(AUSTRAL_DIR, "austral_areal_masks.json5")
  with open(manifest_path, "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2, ensure_ascii=False)
  print(f"\n[DONE] Wrote {manifest_path} with {len(chapter_masks)} chapter masks ({len(specialist_masks)} precolonial + {len(national_epoch_masks)} colonial/modern).", flush=True)


if __name__ == "__main__":
  main()
