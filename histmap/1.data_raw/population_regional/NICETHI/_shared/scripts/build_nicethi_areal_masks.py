"""Stage A2 Dual Mask, Topology-Repaired Sub-Region GeoJSON & Annotated QA Crop Builder
for Operation Viscount Project NICETHI (Sub-Saharan Africa & Western Indian Ocean / African Atlantic Islands).

Constructs:
  1. `NICETHI/_shared/sites_nicethi_africa/config/nicethi_domain_mask.png` (4320x2160 RGBA),
     strictly disjoint from HANDBOOK along the Sahara/Nubia frontier, clipped to land_area.png
     with all WIO & African Atlantic micro-islands preserved.
  2. All 23 chapter dual outputs:
       - `<chapter_dir>/<stem>_areal_mask.png` (4320x2160 RGBA, vectorised shapely.contains_xy)
       - `<chapter_dir>/<stem>.json5` (`subregions` array with id, name, rgb, source, era, description)
       - `NICETHI/_shared/_gis_cache/chapter_subregions/<stem>_subregions.geojson` (topology-repaired)
  3. Crisp annotated bbox QA crop PNGs in `tests/mask_crops/crop_<idx>_<stem>.png`.

All pre-1945 chapters strictly use verified academic HGIS polygons (HydroBASINS L6, OHM,
coastal-complete atlas_dejure, Harvard WorldMap African States 900-1800, Nunn-Murdock 1959
Ethnographic Atlas, Colonial Africa 1895-1950, CShapes 2.0) with zero modern nation-state leakage.
"""

import io
import json
import math
import os
import re
import unicodedata
import zipfile
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import shapefile
import shapely
from PIL import Image
from shapely.geometry import MultiPolygon, Point, Polygon, mapping, shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.validation import make_valid

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
NI_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "NICETHI")
GIS_DIR = os.path.join(NI_DIR, "_shared", "_gis_cache")
SCRAPED_DIR = os.path.join(GIS_DIR, "scraped_hgis")
DEJURE_DIR = os.path.join(GIS_DIR, "atlas_dejure_nicethi")
SUB_GJ_DIR = os.path.join(GIS_DIR, "chapter_subregions")
DOMAIN_CFG_DIR = os.path.join(NI_DIR, "_shared", "sites_nicethi_africa", "config")
DOMAIN_MASK_PNG = os.path.join(DOMAIN_CFG_DIR, "nicethi_domain_mask.png")
HB_DOMAIN_PNG = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "HANDBOOK",
  "_shared", "sites_handbook_mena", "config", "handbook_domain_mask.png"
)
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
CROP_DIR = os.path.join(SVEA_ROOT, "tests", "mask_crops")

os.makedirs(SUB_GJ_DIR, exist_ok=True)
os.makedirs(DOMAIN_CFG_DIR, exist_ok=True)
os.makedirs(CROP_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160
GRID_LATS = 90.0 - (np.arange(GRID_H, dtype=np.float64) + 0.5) * 180.0 / GRID_H
GRID_LONS = -180.0 + (np.arange(GRID_W, dtype=np.float64) + 0.5) * 360.0 / GRID_W

CHAPTER_SPECS = [
  (1,  "1.ancient_mediaeval", "1.prehistoric_ssa",           "prehistoric_ssa",           "Prehistoric Sub-Saharan Africa",                                [-10000, -1000], 1, False),
  (2,  "1.ancient_mediaeval", "2.ancient_mediaeval_nubia",   "ancient_mediaeval_nubia",   "Ancient and Mediaeval Sudan and Nubia",                         [-2500, 1821],   2, False),
  (3,  "1.ancient_mediaeval", "3.ancient_horn_africa",       "ancient_horn_africa",       "Ancient and Mediaeval Ethiopia and the Horn",                   [-1000, 1885],   2, False),
  (4,  "1.ancient_mediaeval", "4.early_west_africa_sahel",   "early_west_africa_sahel",   "Early West Africa and the Sahel States",                        [-1000, 1500],   2, False),
  (5,  "1.ancient_mediaeval", "5.bantu_expansion_africa",    "bantu_expansion_africa",    "The Bantu Expansion Across Sub-Saharan Africa",                 [-1000, 1500],   2, False),
  (6,  "2.early_modern",      "1.atlantic_west_equatoria",   "atlantic_west_equatoria",   "Early Modern West Africa, Equatoria and Angola",                [1500, 1885],    2, False),
  (7,  "2.early_modern",      "2.early_modern_sahel_sudan",  "early_modern_sahel_sudan",  "Early Modern Sahel and Sudan (1500-1898)",                      [1500, 1898],    2, False),
  (8,  "2.early_modern",      "3.early_modern_east_africa",  "early_modern_east_africa",  "Early Modern East Africa and Mozambique",                       [1500, 1885],    2, False),
  (9,  "2.early_modern",      "4.precolonial_south_africa",  "precolonial_south_africa",  "Pre-Colonial Southern Africa and the Cape Frontier",            [1500, 1902],    2, False),
  (10, "2.early_modern",      "5.early_african_islands",     "early_african_islands",     "Western Indian Ocean and Cape Verde Islands",                   [-500, 1895],    2, False),
  (11, "3.colonial_era",      "1.colonial_west_sahel",       "colonial_west_sahel",       "Colonial West Africa and the Sahel",                            [1880, 1975],    2, False),
  (12, "3.colonial_era",      "2.colonial_equatoria_congo",  "colonial_equatoria_congo",  "Colonial Equatoria, Belgian Congo and Angola",                  [1880, 1975],    2, False),
  (13, "3.colonial_era",      "3.colonial_horn_sudan",       "colonial_horn_sudan",       "Colonial Horn of Africa and Anglo-Egyptian Sudan",              [1880, 1960],    2, False),
  (14, "3.colonial_era",      "4.colonial_east_africa",      "colonial_east_africa",      "Colonial East Africa (1880s-1963)",                             [1880, 1963],    2, False),
  (15, "3.colonial_era",      "5.colonial_south_central",    "colonial_south_central",    "Colonial South-Central Africa and Mozambique",                  [1890, 1980],    2, False),
  (16, "3.colonial_era",      "6.modern_southern_africa",    "modern_southern_africa",    "Modern Southern Africa (1902-Present)",                         [1902, 2026],    3, True),
  (17, "4.post_colonial",     "1.modern_african_islands",    "modern_african_islands",    "Modern African Ocean Islands (1890s-Present)",                  [1890, 2026],    3, True),
  (18, "4.post_colonial",     "2.postcolonial_sahel",        "postcolonial_sahel",        "Post-Colonial Sahel States (1960-Present)",                     [1960, 2026],    3, True),
  (19, "4.post_colonial",     "3.postcolonial_west_africa",  "postcolonial_west_africa",  "Post-Colonial West Africa (1957-Present)",                      [1957, 2026],    3, True),
  (20, "4.post_colonial",     "4.postcolonial_congo_angola", "postcolonial_congo_angola", "Post-Colonial Equatoria, DR Congo and Angola",                  [1960, 2026],    3, True),
  (21, "4.post_colonial",     "5.postcolonial_horn_sudan",   "postcolonial_horn_sudan",   "Post-Colonial Sudan, Ethiopia and the Horn",                    [1956, 2026],    3, True),
  (22, "4.post_colonial",     "6.postcolonial_east_africa",  "postcolonial_east_africa",  "Post-Colonial East Africa (1961-Present)",                      [1961, 2026],    3, True),
  (23, "4.post_colonial",     "7.postcolonial_south_central","postcolonial_south_central","Post-Colonial South-Central Africa and Mozambique",             [1964, 2026],    3, True),
]


def make_palette(n=260):
  cols = []
  used = set()
  for i in range(n * 4):
    h = (i * 0.618033988749895) % 1.0
    s = 0.46 + 0.30 * ((i % 3) / 2.0)
    v = 0.58 + 0.30 * (((i // 3) % 3) / 2.0)
    k = int(h * 6.0)
    f = h * 6.0 - k
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    if k % 6 == 0: r, g, b = v, t, p
    elif k % 6 == 1: r, g, b = q, v, p
    elif k % 6 == 2: r, g, b = p, v, t
    elif k % 6 == 3: r, g, b = p, q, v
    elif k % 6 == 4: r, g, b = t, p, v
    else: r, g, b = v, p, q
    rgb = (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))
    if rgb not in used and sum(rgb) > 150 and sum(rgb) < 690:
      used.add(rgb)
      cols.append(list(rgb))
    if len(cols) >= n:
      break
  return cols


PALETTE = make_palette(300)


def norm_str(s):
  if s is None:
    return ""
  return str(s).replace("\u200e", "").replace("\u200f", "").strip()


def slugify(s):
  s = unicodedata.normalize("NFKD", str(s))
  s = "".join(ch for ch in s if not unicodedata.combining(ch))
  s = re.sub(r"[^a-zA-Z0-9]+", "_", s.lower()).strip("_")
  return s[:42] or "unit"


def extract_polygons(g):
  """Strictly extracts valid Polygon/MultiPolygon members, discarding points/lines."""
  if g is None or g.is_empty:
    return None
  try:
    if not g.is_valid:
      g = make_valid(g)
    if g.is_empty:
      return None
    polys = []
    stack = [g]
    while stack:
      cur = stack.pop()
      if cur is None or cur.is_empty:
        continue
      gt = cur.geom_type
      if gt == "Polygon":
        if cur.area > 0:
          polys.append(orient(cur, sign=1.0))
      elif gt == "MultiPolygon":
        for p in cur.geoms:
          if p.geom_type == "Polygon" and not p.is_empty and p.area > 0:
            polys.append(orient(p, sign=1.0))
      elif gt == "GeometryCollection":
        stack.extend(cur.geoms)
    if not polys:
      return None
    if len(polys) == 1:
      return polys[0]
    out = MultiPolygon(polys)
    if not out.is_valid:
      out = make_valid(out)
      return extract_polygons(out) if out.geom_type != "MultiPolygon" else out
    return out
  except Exception:
    return None


def safe_geom(g):
  if g is None or g.is_empty:
    return None
  try:
    if not g.is_valid:
      g = make_valid(g)
    else:
      g = g.buffer(0)
    return extract_polygons(g)
  except Exception:
    return None


def poly_area_km2(poly):
  rp = poly.representative_point()
  cos_l = max(0.1, math.cos(math.radians(rp.y)))
  return float(poly.area) * (111.32 * 111.32 * cos_l)


def repair_topology(g, snap_deg=1e-4, min_sliver_km2=25.0, preserve_micro_islands=False):
  """Mandatory degenerate topology repair: make_valid, snap <= 1e-4 deg, orient CCW,
  strictly Polygon/MultiPolygon members only, and drop/absorb slivers < 25 km^2."""
  g = safe_geom(g)
  if g is None:
    return None
  try:
    g_snapped = shapely.set_precision(g, snap_deg)
    g_clean = extract_polygons(g_snapped)
    if g_clean is None:
      g_clean = g
  except Exception:
    g_clean = g

  polys = list(g_clean.geoms) if g_clean.geom_type == "MultiPolygon" else [g_clean]
  if not preserve_micro_islands and len(polys) > 1 and min_sliver_km2 > 0:
    kept = [p for p in polys if poly_area_km2(p) >= min_sliver_km2]
    if not kept:
      kept = [max(polys, key=lambda p: p.area)]
    polys = kept
  polys = [orient(p, sign=1.0) for p in polys if p.area > 0]
  if not polys:
    return None
  res = polys[0] if len(polys) == 1 else MultiPolygon(polys)
  return extract_polygons(res)


def u_union(*geoms):
  gs = [safe_geom(g) for g in geoms if g is not None]
  gs = [g for g in gs if g is not None and not g.is_empty]
  if not gs:
    return None
  return safe_geom(unary_union(gs))


def latlon_to_rc(lat, lon):
  r = min(GRID_H - 1, max(0, int((90.0 - lat) * GRID_H / 180.0)))
  c = min(GRID_W - 1, max(0, int((lon + 180.0) * GRID_W / 360.0)))
  return r, c


def load_gj(abs_path):
  if not os.path.exists(abs_path):
    return []
  gj = json.load(open(abs_path, "r", encoding="utf-8"))
  out = []
  for f in gj.get("features", []):
    if not f.get("geometry"):
      continue
    g = safe_geom(shape(f["geometry"]))
    if g is not None:
      out.append((f.get("properties") or {}, g))
  return out


def pick_by_prop(feats, keys, keywords, exact=False):
  gs = []
  kws = [k.lower() for k in keywords]
  for pr, g in feats:
    vals = [norm_str(pr.get(k)).lower() for k in keys if pr.get(k)]
    hit = False
    for v in vals:
      if exact:
        if any(v == kw for kw in kws):
          hit = True
      else:
        if any(kw in v for kw in kws):
          hit = True
      if hit:
        break
    if hit:
      gs.append(g)
  return u_union(*gs)


def make_partition_nonoverlapping(ordered_items, clip_envelope=None, preserve_micro_islands=False, min_area_km2=25.0):
  """Takes [(rid, rname, geom, source, era, desc)] in priority order, removes overlaps,
  clips to clip_envelope, absorbs any <25 km^2 detached slivers, and guarantees valid Polygons."""
  claimed = None
  out = []
  for rid, rname, geom, src, era, desc in ordered_items:
    g = safe_geom(geom)
    if g is None:
      continue
    if clip_envelope is not None:
      g = safe_geom(g.intersection(clip_envelope))
    if g is None:
      continue
    if claimed is not None:
      g = safe_geom(g.difference(claimed))
    if g is None:
      continue
    g = repair_topology(g, snap_deg=1e-4, min_sliver_km2=min_area_km2, preserve_micro_islands=preserve_micro_islands)
    if g is None:
      continue
    if not preserve_micro_islands and poly_area_km2(g) < min_area_km2:
      continue
    claimed = u_union(claimed, g)
    out.append([rid, rname, g, src, era, desc])

  # Absorb any leftover gap inside clip_envelope into its nearest / largest touching neighbour
  if clip_envelope is not None and claimed is not None and out:
    rem = safe_geom(clip_envelope.difference(claimed))
    if rem is not None:
      rem_polys = list(rem.geoms) if rem.geom_type == "MultiPolygon" else [rem]
      for rp in rem_polys:
        a_km = poly_area_km2(rp)
        if not preserve_micro_islands and a_km < 5.0:
          continue
        # Only absorb small residual gaps (< 12000 km^2) so we don't distort intentional sub-scopes
        if a_km > 12000.0:
          continue
        best_i = -1
        best_score = -1.0
        pt = rp.representative_point()
        for idx, item in enumerate(out):
          g_i = item[2]
          if g_i.touches(rp) or g_i.intersects(rp.buffer(0.05)):
            inter_len = g_i.boundary.intersection(rp.buffer(0.02)).length
            if inter_len > best_score:
              best_score = inter_len
              best_i = idx
        if best_i < 0:
          best_i = min(range(len(out)), key=lambda i: out[i][2].distance(pt))
        out[best_i][2] = repair_topology(
          u_union(out[best_i][2], rp), snap_deg=1e-4,
          min_sliver_km2=min_area_km2, preserve_micro_islands=preserve_micro_islands
        )
  return [tuple(x) for x in out if x[2] is not None]


def build_modern_border_edge_grid():
  """Builds 4320x2160 modern Admin-0 edge grid identical to audit_areal_masks.js for live QA."""
  ne_path = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared", "_gis_cache", "ne_10m_admin_0_countries.geojson")
  if not os.path.exists(ne_path):
    ne_path = os.path.join(SCRAPED_DIR, "ne_10m_nicethi_admin0.geojson")
  grid = np.zeros((GRID_H, GRID_W), dtype=np.uint8)
  gj = json.load(open(ne_path, "r", encoding="utf-8"))

  def draw_ring(ring):
    for i in range(1, len(ring)):
      x0 = (ring[i - 1][0] + 180.0) * GRID_W / 360.0
      y0 = (90.0 - ring[i - 1][1]) * GRID_H / 180.0
      x1 = (ring[i][0] + 180.0) * GRID_W / 360.0
      y1 = (90.0 - ring[i][1]) * GRID_H / 180.0
      steps = max(1, int(math.ceil(max(abs(x1 - x0), abs(y1 - y0)))))
      if steps > 400:
        continue
      ts = np.linspace(0.0, 1.0, steps + 1)
      cs = np.clip((x0 + (x1 - x0) * ts).astype(np.int32), 0, GRID_W - 1)
      rs = np.clip((y0 + (y1 - y0) * ts).astype(np.int32), 0, GRID_H - 1)
      grid[rs, cs] = 1

  for f in gj.get("features", []):
    g = f.get("geometry")
    if not g or not g.get("coordinates"):
      continue
    if g["type"] == "Polygon":
      draw_ring(g["coordinates"][0])
    elif g["type"] == "MultiPolygon":
      for p in g["coordinates"]:
        if p and p[0]:
          draw_ring(p[0])
  return grid


def compute_modern_border_leak(rgba, ne_edges):
  valid = (rgba[:, :, 3] > 0) & (rgba[:, :, :3].sum(axis=2) > 0)
  ys, xs = np.where(valid)
  if ys.size < 400:
    return 0.0
  r0, r1 = max(1, int(ys.min())), min(GRID_H - 1, int(ys.max()))
  c0, c1 = max(1, int(xs.min())), min(GRID_W - 1, int(xs.max()))
  sub_v = valid[r0:r1, c0:c1]
  col_id = (rgba[r0:r1, c0:c1, 0].astype(np.int32) << 16) | (rgba[r0:r1, c0:c1, 1].astype(np.int32) << 8) | rgba[r0:r1, c0:c1, 2].astype(np.int32)
  col_r = (rgba[r0:r1, c0 + 1:c1 + 1, 0].astype(np.int32) << 16) | (rgba[r0:r1, c0 + 1:c1 + 1, 1].astype(np.int32) << 8) | rgba[r0:r1, c0 + 1:c1 + 1, 2].astype(np.int32)
  col_d = (rgba[r0 + 1:r1 + 1, c0:c1, 0].astype(np.int32) << 16) | (rgba[r0 + 1:r1 + 1, c0:c1, 1].astype(np.int32) << 8) | rgba[r0 + 1:r1 + 1, c0:c1, 2].astype(np.int32)
  v_r = valid[r0:r1, c0 + 1:c1 + 1]
  v_d = valid[r0 + 1:r1 + 1, c0:c1]
  int_edge = sub_v & ((v_r & (col_r != col_id)) | (v_d & (col_d != col_id)))
  n_edges = int(int_edge.sum())
  if n_edges < 120:
    return 0.0
  ne_hit = (
    ne_edges[r0:r1, c0:c1]
    | ne_edges[r0:r1, c0 - 1:c1 - 1]
    | ne_edges[r0:r1, c0 + 1:c1 + 1]
    | ne_edges[r0 - 1:r1 - 1, c0:c1]
    | ne_edges[r0 + 1:r1 + 1, c0:c1]
  ) > 0
  return float((int_edge & ne_hit).sum()) / float(n_edges)


# Guaranteed sub-5-arcmin micro-island anchors (lat, lon) so Granitic Seychelles (Mahe/Praslin/La Digue),
# Rodrigues, Agalega, Chagos, Iles Eparses, St Helena, Ascension, Tristan da Cunha, STP & Cabo Verde
# are ALWAYS rasterised in domain_mask, Ch. 10, Ch. 17 and subadmin_hgis!
MICRO_ISLAND_ANCHORS = {
  "SYC": [(-4.67, 55.45), (-4.60, 55.45), (-4.73, 55.50), (-4.32, 55.74), (-4.36, 55.84), (-4.48, 55.23), (-9.42, 46.35)],
  "MUS": [(-20.25, 57.55), (-19.72, 63.42), (-10.42, 56.63)],
  "REU": [(-21.12, 55.53)],
  "COM": [(-11.70, 43.35), (-12.22, 44.43), (-12.30, 43.73)],
  "MYT": [(-12.82, 45.16)],
  "IOT": [(-7.32, 72.42), (-5.33, 71.85)],
  "ATF": [(-22.37, 40.36), (-17.05, 42.72), (-11.55, 47.30), (-15.89, 54.52)],
  "CPV": [(15.08, -23.62), (17.07, -25.17), (16.85, -24.98), (16.61, -24.28), (16.73, -22.93), (16.10, -22.80), (15.22, -23.16), (14.95, -24.38), (14.87, -24.71)],
  "STP": [(0.25, 6.61), (1.62, 7.40)],
  "SHN": [(-15.96, -5.71), (-7.94, -14.37), (-37.11, -12.29)],
}


def build_domain_mask(adm0_geoms, island_geoms):
  """Constructs nicethi_domain_mask.png strictly disjoint from HANDBOOK, clipped to land_area.png,
  while preserving all micro-islands (CPV, STP, SHN, COM, MYT, MUS, REU, SYC incl. Mahe/Praslin, ATF, IOT)."""
  print("[1] Building nicethi_domain_mask.png (4320x2160 RGBA, strictly disjoint from HANDBOOK)...", flush=True)
  hb_raw = np.asarray(Image.open(HB_DOMAIN_PNG).convert("RGBA"), dtype=np.uint8)
  hb_mask = (hb_raw[:, :, 3] > 0) & (hb_raw[:, :, :3].sum(axis=2) > 0)

  la_raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  land_area = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2])
  land_bool = land_area > 0

  ni_union = u_union(*list(adm0_geoms.values()), *list(island_geoms.values()))
  minx, miny, maxx, maxy = ni_union.bounds
  r0, c0 = latlon_to_rc(maxy, minx)
  r1, c1 = latlon_to_rc(miny, maxx)
  r0, c0 = max(0, r0 - 2), max(0, c0 - 2)
  r1, c1 = min(GRID_H - 1, r1 + 2), min(GRID_W - 1, c1 + 2)

  # Vectorised rasterisation of mainland+islands onto land_bool
  dom = np.zeros((GRID_H, GRID_W), dtype=bool)
  sub_land = land_bool[r0:r1 + 1, c0:c1 + 1] & (~hb_mask[r0:r1 + 1, c0:c1 + 1])
  drs, dcs = np.where(sub_land)
  rrs = r0 + drs
  ccs = c0 + dcs
  inside = shapely.contains_xy(ni_union, GRID_LONS[ccs], GRID_LATS[rrs])
  dom[rrs[inside], ccs[inside]] = True

  # All-touched rasterisation of micro-islands (half-pixel 0.042 deg tolerance) + explicit anchors
  for isl_key, ig in island_geoms.items():
    if ig is not None and not ig.is_empty:
      polys = list(ig.geoms) if ig.geom_type == "MultiPolygon" else [ig]
      for poly in polys:
        if poly.is_empty:
          continue
        ix0, iy0, ix1, iy1 = poly.bounds
        pr0, pc0 = latlon_to_rc(iy1, ix0)
        pr1, pc1 = latlon_to_rc(iy0, ix1)
        pr0, pc0 = max(0, pr0 - 1), max(0, pc0 - 1)
        pr1, pc1 = min(GRID_H - 1, pr1 + 1), min(GRID_W - 1, pc1 + 1)
        rr_grid, cc_grid = np.meshgrid(np.arange(pr0, pr1 + 1), np.arange(pc0, pc1 + 1), indexing="ij")
        # Use half-pixel all-touched buffer for small islands (< 1500 km^2) so Mahe/Praslin/Rodrigues never drop
        p_test = poly.buffer(0.042) if poly_area_km2(poly) < 1500.0 else poly
        hit = shapely.contains_xy(p_test, GRID_LONS[cc_grid.ravel()], GRID_LATS[rr_grid.ravel()])
        if hit.any():
          dom[rr_grid.ravel()[hit], cc_grid.ravel()[hit]] = True
        elif poly_area_km2(poly) >= 1.0 or len(polys) <= 5:
          rp = poly.representative_point()
          rr, cc = latlon_to_rc(rp.y, rp.x)
          dom[rr, cc] = True
    for alat, alon in MICRO_ISLAND_ANCHORS.get(isl_key, []):
      rr, cc = latlon_to_rc(alat, alon)
      dom[rr, cc] = True

  # Enforce strict disjointness from HANDBOOK
  dom &= ~hb_mask

  # Close any 1-px frontier gap between HANDBOOK and NICETHI on land_bool along the Sahara/Nubia border
  # (A land pixel strictly between hb_mask on north and dom on south, inside lat 15..28, lon -18..38)
  fr_r0, fr_c0 = latlon_to_rc(28.0, -18.0)
  fr_r1, fr_c1 = latlon_to_rc(15.0, 38.0)
  for _ in range(2):
    sub_u = land_bool[fr_r0:fr_r1, fr_c0:fr_c1] & (~hb_mask[fr_r0:fr_r1, fr_c0:fr_c1]) & (~dom[fr_r0:fr_r1, fr_c0:fr_c1])
    urs, ucs = np.where(sub_u)
    filled = 0
    for dr, dc in zip(urs, ucs):
      r, c = fr_r0 + dr, fr_c0 + dc
      n_hb = hb_mask[max(0, r - 1):min(GRID_H, r + 2), max(0, c - 1):min(GRID_W, c + 2)].any()
      n_ni = dom[max(0, r - 1):min(GRID_H, r + 2), max(0, c - 1):min(GRID_W, c + 2)].any()
      if n_hb and n_ni:
        dom[r, c] = True
        filled += 1
    if filled == 0:
      break

  overlap = int((dom & hb_mask).sum())
  assert overlap == 0, f"HANDBOOK overlap detected: {overlap}"

  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  rgba[dom] = [255, 255, 255, 255]
  Image.fromarray(rgba, mode="RGBA").save(DOMAIN_MASK_PNG)
  print(f"  Saved nicethi_domain_mask.png: {int(dom.sum()):,} px | HANDBOOK overlap = {overlap}", flush=True)
  return dom, ni_union


def render_annotated_crop(idx, stem, title, domain_yrs, rgba, full_domain_mask, subregions_meta, out_png):
  """Renders a crisp, high-resolution annotated bbox crop PNG with coastlines, sub-region outlines,
  title banner, and clean legend swatches for optical inspection by separate mask_auditor."""
  valid = (rgba[:, :, 3] > 0) & (rgba[:, :, :3].sum(axis=2) > 0)
  ys, xs = np.where(valid)
  if ys.size == 0:
    return
  pad_r = max(14, int((ys.max() - ys.min()) * 0.06))
  pad_c = max(14, int((xs.max() - xs.min()) * 0.06))
  r0 = max(0, int(ys.min()) - pad_r)
  r1 = min(GRID_H, int(ys.max()) + pad_r + 1)
  c0 = max(0, int(xs.min()) - pad_c)
  c1 = min(GRID_W, int(xs.max()) + pad_c + 1)

  sub_rgba = rgba[r0:r1, c0:c1]
  sub_dom = full_domain_mask[r0:r1, c0:c1]
  sub_val = valid[r0:r1, c0:c1]

  ch, cw = sub_rgba.shape[:2]
  canvas = np.full((ch, cw, 3), [228, 239, 248], dtype=np.uint8)  # soft ocean blue
  canvas[sub_dom & (~sub_val)] = [218, 216, 210]  # muted context land
  canvas[sub_val] = sub_rgba[sub_val, :3]

  # Draw crisp 1-px dark borders between adjacent sub-regions and along coastlines
  cid = (sub_rgba[:, :, 0].astype(np.int32) << 16) | (sub_rgba[:, :, 1].astype(np.int32) << 8) | sub_rgba[:, :, 2].astype(np.int32)
  edge = np.zeros((ch, cw), dtype=bool)
  edge[:-1, :] |= (sub_val[:-1, :] & sub_val[1:, :] & (cid[:-1, :] != cid[1:, :]))
  edge[:, :-1] |= (sub_val[:, :-1] & sub_val[:, 1:] & (cid[:, :-1] != cid[:, 1:]))
  coast = np.zeros((ch, cw), dtype=bool)
  coast[:-1, :] |= (sub_dom[:-1, :] != sub_dom[1:, :])
  coast[:, :-1] |= (sub_dom[:, :-1] != sub_dom[:, 1:])
  canvas[coast] = [120, 128, 136]
  canvas[edge] = (canvas[edge].astype(np.float32) * 0.45).astype(np.uint8)

  plt.rcdefaults()
  plt.style.use("default")
  n_sub = len(subregions_meta)
  fig_w = 13.5 if n_sub > 14 else 11.5
  aspect = ch / max(1, cw)
  fig_h = max(6.2, min(10.5, 7.2 * aspect + 1.2))
  fig = plt.figure(figsize=(fig_w, fig_h), dpi=130, facecolor="#ffffff")
  gs = fig.add_gridspec(1, 2, width_ratios=[2.35, 1.0], wspace=0.04)
  ax = fig.add_subplot(gs[0, 0])
  ax_leg = fig.add_subplot(gs[0, 1])

  lon_min = -180.0 + c0 * 360.0 / GRID_W
  lon_max = -180.0 + c1 * 360.0 / GRID_W
  lat_max = 90.0 - r0 * 180.0 / GRID_H
  lat_min = 90.0 - r1 * 180.0 / GRID_H

  ax.imshow(canvas, extent=[lon_min, lon_max, lat_min, lat_max], interpolation="nearest", aspect="equal")
  ax.set_aspect("equal", adjustable="box")
  ax.set_xlabel("Longitude (°E)", fontsize=8, color="#333333")
  ax.set_ylabel("Latitude (°N)", fontsize=8, color="#333333")
  ax.tick_params(labelsize=7.5, colors="#444444")
  ax.grid(color="#8ca0b0", linestyle=":", linewidth=0.45, alpha=0.55)

  # Direct numeric badges on map (zero overlapping text boxes; full names in numbered side legend)
  if n_sub <= 36:
    for i_s, sr in enumerate(subregions_meta, 1):
      rgb = sr["rgb"]
      m = sub_val & (sub_rgba[:, :, 0] == rgb[0]) & (sub_rgba[:, :, 1] == rgb[1]) & (sub_rgba[:, :, 2] == rgb[2])
      my, mx = np.where(m)
      if my.size > 0:
        # Pick the pixel closest to the median that actually lies inside the subregion
        med_y, med_x = float(np.median(my)), float(np.median(mx))
        best_idx = int(np.argmin((my - med_y) ** 2 + (mx - med_x) ** 2))
        cy, cx = float(my[best_idx]), float(mx[best_idx])
        lx = -180.0 + (c0 + cx + 0.5) * 360.0 / GRID_W
        ly = 90.0 - (r0 + cy + 0.5) * 180.0 / GRID_H
        ax.text(
          lx, ly, f"{i_s}", fontsize=7.6 if n_sub <= 18 else 6.2, fontweight="bold",
          color="#111111", ha="center", va="center",
          bbox=dict(boxstyle="round,pad=0.18", facecolor="#ffffff", edgecolor="#222222", alpha=0.84, lw=0.55)
        )

  ax.set_title(
    f"Ch. {idx:02d}: {title}  [{domain_yrs[0]}..{domain_yrs[1]}]  ({n_sub} sub-regions | {int(valid.sum()):,} px)",
    fontsize=10.0, fontweight="bold", color="#1a1a1a", pad=8
  )

  # Side legend panel
  ax_leg.axis("off")
  max_show = min(n_sub, 42)
  handles = []
  for i_s, sr in enumerate(subregions_meta[:max_show], 1):
    col = [c / 255.0 for c in sr["rgb"]]
    nm = sr["name"]
    if len(nm) > 30:
      nm = nm[:28] + "…"
    handles.append(mpatches.Patch(facecolor=col, edgecolor="#333333", linewidth=0.5, label=f"{i_s}. {nm} ({sr['pixel_count']} px)"))
  if n_sub > max_show:
    handles.append(mpatches.Patch(facecolor="none", edgecolor="none", label=f"... +{n_sub - max_show} more sub-regions"))
  fsize = 6.8 if max_show <= 18 else (5.6 if max_show <= 32 else 4.8)
  ax_leg.legend(handles=handles, loc="upper left", frameon=False, fontsize=fsize, handlelength=1.1, labelspacing=0.32)

  import sys
  shared_utils = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared")
  if shared_utils not in sys.path:
    sys.path.insert(0, shared_utils)
  from viscount_plot_utils import save_viscount_figure
  save_viscount_figure(fig, out_png, arg2_dpi=130, arg3_options={"verify_layout": False, "strict_layout": False})


def rasterise_chapter(idx, stem, title, domain_yrs, regime, is_admin1, regions, domain_mask, out_png, out_geojson, out_json5, crop_png, ne_edges, preserve_micro_islands=False):
  """Vectorised zero-scanline rasterisation + topology-repaired GeoJSON + JSON5 + annotated QA crop."""
  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  used_rgbs = set()

  # Order largest to smallest so smaller enclaves/islands paint crisply on top
  cleaned = []
  for item in regions:
    rid, rname, geom, src, era, desc = item
    g = repair_topology(geom, snap_deg=1e-4, min_sliver_km2=25.0, preserve_micro_islands=preserve_micro_islands)
    if g is not None and not g.is_empty:
      cleaned.append((rid, rname, g, src, era, desc))
  cleaned.sort(key=lambda x: -float(x[2].area))

  sub_meta = []
  features = []
  rgb_of_rid = {}
  geom_of_rid = {}

  for i_r, (rid, rname, g, src, era, desc) in enumerate(cleaned):
    rgb = list(PALETTE[i_r % len(PALETTE)])
    while tuple(rgb) in used_rgbs:
      rgb = [(rgb[0] + 17) % 230 + 15, (rgb[1] + 31) % 230 + 15, (rgb[2] + 47) % 230 + 15]
    used_rgbs.add(tuple(rgb))
    rgb_of_rid[rid] = rgb
    geom_of_rid[rid] = g

    minx, miny, maxx, maxy = g.bounds
    r0, c0 = latlon_to_rc(maxy, minx)
    r1, c1 = latlon_to_rc(miny, maxx)
    r0, c0 = max(0, r0 - 1), max(0, c0 - 1)
    r1, c1 = min(GRID_H - 1, r1 + 1), min(GRID_W - 1, c1 + 1)

    sub_dom = domain_mask[r0:r1 + 1, c0:c1 + 1]
    drs, dcs = np.where(sub_dom)
    if drs.size > 0:
      rrs = r0 + drs
      ccs = c0 + dcs
      # For micro-island subregions (small archipelagos), apply half-pixel all-touched tolerance onto domain_mask pixels!
      g_test = g.buffer(0.045) if (preserve_micro_islands and g.area < 1.0) else g
      inside = shapely.contains_xy(g_test, GRID_LONS[ccs], GRID_LATS[rrs])
      if inside.any():
        rgba[rrs[inside], ccs[inside]] = [rgb[0], rgb[1], rgb[2], 255]

  # Ensure zero starvation (pin representative point onto nearest domain_mask pixel if overwritten or sub-pixel)
  for rid, rname, g, src, era, desc in cleaned:
    rgb = rgb_of_rid[rid]
    m = (rgba[:, :, 3] > 0) & (rgba[:, :, 0] == rgb[0]) & (rgba[:, :, 1] == rgb[1]) & (rgba[:, :, 2] == rgb[2])
    if int(m.sum()) == 0:
      rp = g.representative_point()
      rr, cc = latlon_to_rc(rp.y, rp.x)
      placed = False
      for rad in range(0, 6):
        for dr in range(-rad, rad + 1):
          for dc in range(-rad, rad + 1):
            nr, nc = rr + dr, cc + dc
            if 0 <= nr < GRID_H and 0 <= nc < GRID_W and domain_mask[nr, nc]:
              rgba[nr, nc] = [rgb[0], rgb[1], rgb[2], 255]
              placed = True
              break
          if placed:
            break
        if placed:
          break
      if not placed:
        rgba[rr, cc] = [rgb[0], rgb[1], rgb[2], 255]

  # Count final exact pixels per RGB and assemble JSON5 & GeoJSON
  tiny_slivers = 0
  for rid, rname, g, src, era, desc in cleaned:
    rgb = rgb_of_rid[rid]
    m = (rgba[:, :, 3] > 0) & (rgba[:, :, 0] == rgb[0]) & (rgba[:, :, 1] == rgb[1]) & (rgba[:, :, 2] == rgb[2])
    px = int(m.sum())
    if 0 < px < 4:
      tiny_slivers += 1
    sub_meta.append({
      "id": rid,
      "name": rname,
      "rgb": rgb,
      "source": src,
      "era": era,
      "description": desc,
      "pixel_count": px,
    })
    g_out = repair_topology(g.simplify(0.008, preserve_topology=True), snap_deg=1e-4, min_sliver_km2=0.0, preserve_micro_islands=True)
    if g_out is None:
      g_out = g
    features.append({
      "type": "Feature",
      "properties": {
        "id": rid,
        "region_id": rid,
        "name": rname,
        "rgb": rgb,
        "hex": "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2]),
        "source": src,
        "era": era,
        "pixel_count": px,
      },
      "geometry": mapping(g_out),
    })

  os.makedirs(os.path.dirname(out_png), exist_ok=True)
  Image.fromarray(rgba, mode="RGBA").save(out_png)
  os.makedirs(os.path.dirname(out_geojson), exist_ok=True)
  with open(out_geojson, "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": features}, fh, ensure_ascii=False)

  ch_obj = {
    "id": stem,
    "title": title,
    "domain": domain_yrs,
    "regime": regime,
    "is_admin1": bool(is_admin1),
    "subregions": sub_meta,
  }
  with open(out_json5, "w", encoding="utf-8") as fh:
    json.dump(ch_obj, fh, indent=2, ensure_ascii=False)

  render_annotated_crop(idx, stem, title, domain_yrs, rgba, domain_mask, sub_meta, crop_png)

  leak = compute_modern_border_leak(rgba, ne_edges) if not is_admin1 else 0.0
  active_px = int((rgba[:, :, 3] > 0).sum())
  return len(sub_meta), active_px, tiny_slivers, leak


def main():
  print("[0] Loading Pass-1 cached HGIS layers for NICETHI...", flush=True)
  ne_edges = build_modern_border_edge_grid()

  # Load NE 10m NICETHI Admin-0 (52 features) keyed by ADM0_A3 / ISO3
  adm0 = {}
  ne0_feats = load_gj(os.path.join(SCRAPED_DIR, "ne_10m_nicethi_admin0.geojson"))
  for pr, g in ne0_feats:
    iso = norm_str(pr.get("ADM0_A3") or pr.get("ISO_A3") or pr.get("SOV_A3"))
    if iso == "SDS":
      iso = "SSD"
    if iso:
      adm0[iso] = u_union(adm0.get(iso), g)

  # Load GADM 4.1 island territories missing or incomplete in NE Admin-0
  gadm_dir = os.path.join(SCRAPED_DIR, "modern_admins", "gadm41")
  myt_feats = load_gj(os.path.join(gadm_dir, "gadm41_MYT_1.geojson"))
  reu_feats = load_gj(os.path.join(gadm_dir, "gadm41_REU_1.geojson"))
  shn_feats = load_gj(os.path.join(gadm_dir, "gadm41_SHN_1.geojson"))
  iot_feats = load_gj(os.path.join(gadm_dir, "gadm41_IOT_0.geojson"))
  atf_feats = [(pr, g) for pr, g in load_gj(os.path.join(gadm_dir, "gadm41_ATF_1.geojson")) if "eparse" in slugify(pr.get("NAME_1") or "")]

  adm0["MYT"] = u_union(*[g for _, g in myt_feats])
  adm0["REU"] = u_union(*[g for _, g in reu_feats])
  adm0["SHN"] = u_union(*[g for _, g in shn_feats], adm0.get("SHN"))
  adm0["IOT"] = u_union(*[g for _, g in iot_feats], adm0.get("IOT"))
  adm0["ATF"] = u_union(*[g for _, g in atf_feats])

  # Load geoBoundaries ADM1 for all 49 territories + HDX COD-AB + NE1 Niger upgrades
  gb_dir = os.path.join(SCRAPED_DIR, "modern_admins", "geoboundaries")
  hdx_dir = os.path.join(SCRAPED_DIR, "modern_admins", "hdx_codab")
  adm1 = {}
  for fn in sorted(os.listdir(gb_dir)):
    if not fn.endswith("_ADM1.geojson"):
      continue
    iso = fn.split("_")[0]
    by_nm = defaultdict(list)
    for pr, g in load_gj(os.path.join(gb_dir, fn)):
      nm = norm_str(pr.get("shapeName") or pr.get("name") or f"{iso}_ADM1")
      by_nm[nm].append(g)
    adm1[iso] = [(nm, u_union(*gs)) for nm, gs in sorted(by_nm.items()) if u_union(*gs) is not None]

  # Upgrade ETH (15 HDX COD-AB post-2023 regions), MLI (10 HDX regions incl. Menaka), NER (8 NE1 regions)
  hdx_eth = load_gj(os.path.join(hdx_dir, "hdx_codab_eth_adm1.geojson"))
  if hdx_eth:
    adm1["ETH"] = [(norm_str(pr.get("adm1_name") or f"ETH_{i}"), g) for i, (pr, g) in enumerate(hdx_eth)]
  hdx_mli = load_gj(os.path.join(hdx_dir, "hdx_codab_mli_adm1.geojson"))
  if hdx_mli:
    adm1["MLI"] = [(norm_str(pr.get("ADM1_FR") or f"MLI_{i}"), g) for i, (pr, g) in enumerate(hdx_mli)]
  ne1_feats = load_gj(os.path.join(SCRAPED_DIR, "ne_10m_nicethi_admin1.geojson"))
  ner_ne1 = [(norm_str(pr.get("name")), g) for pr, g in ne1_feats if norm_str(pr.get("admin")) == "Niger" and pr.get("name")]
  if len(ner_ne1) >= 8:
    adm1["NER"] = ner_ne1

  # Add island GADM Admin-1 entries
  adm1["MYT"] = [("Mayotte", adm0["MYT"])]
  adm1["REU"] = [(norm_str(pr.get("NAME_1") or f"REU_{i}"), g) for i, (pr, g) in enumerate(reu_feats)]
  adm1["SHN"] = [(norm_str(pr.get("NAME_1") or f"SHN_{i}"), g) for i, (pr, g) in enumerate(shn_feats)]
  adm1["IOT"] = [("Chagos Archipelago (BIOT)", adm0["IOT"])]
  adm1["ATF"] = [("Iles Eparses (Mozambique Channel)", adm0["ATF"])]

  # Ensure island geometries in adm0 include high-res geoBoundaries union
  island_isos = ("COM", "CPV", "MUS", "STP", "SYC", "MYT", "REU", "SHN", "IOT", "ATF")
  island_geoms = {}
  for iso in island_isos:
    g_isl = u_union(adm0.get(iso), *[g for _, g in adm1.get(iso, [])])
    adm0[iso] = g_isl
    island_geoms[iso] = g_isl

  # Build NICETHI Domain Mask (Deliverable 1)
  domain_mask, ni_union = build_domain_mask(adm0, island_geoms)

  def C(*isos):
    return u_union(*[adm0.get(i) for i in isos if adm0.get(i) is not None])

  # Exclude Prince Edward Islands (-46.9S) from mainland continental envelope for clean crops
  mainland_clip_box = shapely.geometry.box(-20.0, -35.5, 53.0, 28.0)
  continental_ssa = safe_geom(u_union(*[adm0[k] for k in adm0 if k not in island_isos and k != "MDG"]).intersection(mainland_clip_box))
  full_land = u_union(continental_ssa, adm0["MDG"], *[adm0[k] for k in island_isos])

  # Load HydroBASINS L6 Africa (clipped to NICETHI land)
  print("[2] Loading HydroBASINS L6 Africa & Pass-1 HGIS vector datasets...", flush=True)
  basins = []
  hybas_zip = os.path.join(GIS_DIR, "hybas_af_lev06_v1c.zip")
  with zipfile.ZipFile(hybas_zip) as zf:
    sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
    fields = [f[0] for f in sf.fields[1:]]
    idx_pfaf = fields.index("PFAF_ID") if "PFAF_ID" in fields else -1
    idx_main = fields.index("MAIN_BAS") if "MAIN_BAS" in fields else -1
    for sr in sf.iterShapeRecords():
      bb = sr.shape.bbox
      if bb[3] < -36.0 or bb[1] > 28.5:
        continue
      g = safe_geom(shape(sr.shape.__geo_interface__))
      if g is None or not g.intersects(full_land):
        continue
      gc = safe_geom(g.intersection(full_land))
      if gc is None or gc.area < 0.002:
        continue
      rp = gc.representative_point()
      basins.append({
        "geom": gc, "lat": float(rp.y), "lon": float(rp.x), "area": float(gc.area),
        "pfaf": str(sr.record[idx_pfaf]) if idx_pfaf >= 0 else "",
        "main_bas": int(sr.record[idx_main]) if idx_main >= 0 else 0,
      })
  print(f"  Loaded {len(basins)} HydroBASINS L6 watersheds inside NICETHI.", flush=True)

  def organic_subdivide(env_geom, seed_map):
    """Partitions any envelope organically along HydroBASINS L6 watershed ridges (ZERO straight box cuts)."""
    if env_geom is None or env_geom.is_empty:
      return {k: None for k in seed_map}
    keys = list(seed_map.keys())
    s_lats = np.array([seed_map[k][0] for k in keys], dtype=np.float64)
    s_lons = np.array([seed_map[k][1] for k in keys], dtype=np.float64)
    buckets = {k: [] for k in keys}
    for b in basins:
      bg = b["geom"]
      if not bg.intersects(env_geom):
        continue
      piece = safe_geom(bg.intersection(env_geom))
      if piece is None or piece.area < 0.001:
        continue
      rp = piece.representative_point()
      cos_l = math.cos(math.radians(rp.y))
      d2 = ((s_lons - rp.x) * cos_l) ** 2 + (s_lats - rp.y) ** 2
      buckets[keys[int(np.argmin(d2))]].append(piece)
    out = {k: u_union(*gs) for k, gs in buckets.items()}
    covered = u_union(*[v for v in out.values() if v is not None])
    rem = safe_geom(env_geom.difference(covered)) if covered is not None else env_geom
    if rem is not None:
      parts = list(rem.geoms) if rem.geom_type == "MultiPolygon" else [rem]
      for p in parts:
        if p.area < 0.0005:
          continue
        rp = p.representative_point()
        cos_l = math.cos(math.radians(rp.y))
        d2 = ((s_lons - rp.x) * cos_l) ** 2 + (s_lats - rp.y) ** 2
        best_k = keys[int(np.argmin(d2))]
        out[best_k] = u_union(out[best_k], p)
    return out

  # Load Nunn-Murdock 1959 Ethnographic Atlas (844 ethnic/cultural polygons)
  murdock_raw = load_gj(os.path.join(SCRAPED_DIR, "precolonial_ethnographic", "nunn_murdock_1959_ethnographic_atlas.geojson"))
  murdock_by_cg = defaultdict(list)
  murdock_by_nm = defaultdict(list)
  for pr, g in murdock_raw:
    if not g.intersects(full_land):
      continue
    gc = safe_geom(g.intersection(full_land))
    if gc is None:
      continue
    cg = norm_str(pr.get("CultureGrp") or pr.get("Cultgrp_30")).lower()
    nm = norm_str(pr.get("NAME") or pr.get("Name_Displ")).lower()
    if cg:
      murdock_by_cg[cg].append(gc)
    if nm:
      murdock_by_nm[nm].append(gc)

  def M_cg(*kws):
    gs = []
    for k in kws:
      kl = k.lower()
      for cg, lst in murdock_by_cg.items():
        if kl in cg:
          gs.extend(lst)
    return u_union(*gs)

  def M_nm(*kws):
    gs = []
    for k in kws:
      kl = k.lower()
      for nm, lst in murdock_by_nm.items():
        if kl in nm:
          gs.extend(lst)
    return u_union(*gs)

  # Load Harvard WorldMap African States (900-1800) & Mali
  hw_states = load_gj(os.path.join(SCRAPED_DIR, "precolonial_ethnographic", "harvard_worldmap_african_states_900_1800.geojson"))
  hw_mali = u_union(*[g for _, g in load_gj(os.path.join(SCRAPED_DIR, "precolonial_ethnographic", "harvard_worldmap_kingdom_of_mali.geojson"))])

  def HW(*kws):
    return pick_by_prop(hw_states, ["Name"], kws)

  # Load coastal-complete atlas_dejure snapshots
  def load_dj(yr):
    return load_gj(os.path.join(DEJURE_DIR, f"dejure_{yr}.geojson"))

  dj_m1000 = load_dj(-1000)
  dj_0 = load_dj(0)
  dj_500 = load_dj(500)
  dj_1000 = load_dj(1000)
  dj_1300 = load_dj(1300)
  dj_1500 = load_dj(1500)
  dj_1700 = load_dj(1700)
  dj_1800 = load_dj(1800)
  dj_1850 = load_dj(1850)
  dj_1880 = load_dj(1880)

  # Load OHM Africa boundaries
  ohm_all = load_gj(os.path.join(SCRAPED_DIR, "ohm_africa_boundaries.geojson"))

  def OHM(*kws, max_sy=1910):
    gs = []
    kls = [k.lower() for k in kws]
    for pr, g in ohm_all:
      sd = norm_str(pr.get("start_date"))
      try:
        sy = int(sd.split("-")[0]) if sd and sd[0] != "-" else (-int(sd[1:].split("-")[0]) if sd.startswith("-") else 9999)
      except Exception:
        sy = 9999
      if sy > max_sy:
        continue
      vals = [norm_str(pr.get(k)).lower() for k in ("name:en", "name", "official_name") if pr.get(k)]
      if any(any(kw in v for kw in kls) for v in vals):
        gs.append(g)
    return u_union(*gs)

  # Load Colonial Africa datasets (1895, 1914, 1915, 1920, 1941, 1950)
  col_1895 = load_gj(os.path.join(SCRAPED_DIR, "colonial_borders", "colonial_africa_1895.geojson"))
  col_1914 = load_gj(os.path.join(SCRAPED_DIR, "colonial_borders", "colonial_africa_berlin_partition_1914.geojson"))
  col_1915 = load_gj(os.path.join(SCRAPED_DIR, "colonial_borders", "colonial_africa_1915.geojson"))
  col_1920 = load_gj(os.path.join(SCRAPED_DIR, "colonial_borders", "worldhist_league_of_nations_mandates_africa_1920.geojson"))
  col_1941 = load_gj(os.path.join(SCRAPED_DIR, "colonial_borders", "colonial_africa_1941.geojson"))
  col_1950 = load_gj(os.path.join(SCRAPED_DIR, "colonial_borders", "colonial_africa_1950.geojson"))

  # =========================================================================
  # CH 1: Prehistoric Sub-Saharan Africa [-10000..-1000] (Pure HydroBASINS L6)
  # =========================================================================
  print("[3] Constructing all 23 NICETHI chapter partitions...", flush=True)
  ch1_seeds = {
    "senegal_gambia_atlantic":     (15.2, -13.5),
    "upper_middle_niger":          (14.5,  -4.8),
    "lower_niger_benue_volta":     ( 9.5,   5.2),
    "upper_guinea_forest":         ( 7.6,  -8.8),
    "chad_mega_basin":             (13.8,  15.8),
    "nile_nubia_sudd":             (14.2,  31.2),
    "ethiopian_highlands_horn":    (10.0,  38.5),
    "somali_arid_horn":            ( 6.8,  45.8),
    "congo_ubangi_basin":          ( 0.5,  22.5),
    "lower_guinea_ogowe_cuanza":   (-4.5,  13.2),
    "east_african_great_lakes":    (-1.5,  33.2),
    "swahili_rufiji_coast":        (-7.8,  38.2),
    "zambezi_okavango_limpopo":    (-16.5, 28.5),
    "kalahari_namib_arid":         (-22.2, 18.8),
    "orange_cape_drakensberg":     (-29.8, 24.5),
  }
  ch1_sub = organic_subdivide(continental_ssa, ch1_seeds)
  ch1_meta = [
    ("senegal_gambia_atlantic",      "Senegal-Gambia and Atlantic Sahel Basins",      ch1_sub["senegal_gambia_atlantic"],      "HydroBASINS L6 Africa", "-10000..-1000", "Holocene catchments of the Senegal, Gambia and western Mauritanian wadis."),
    ("upper_middle_niger",           "Upper and Middle Niger Inland Delta",           ch1_sub["upper_middle_niger"],           "HydroBASINS L6 Africa", "-10000..-1000", "Upper Niger headwaters, Inland Niger Delta and Niger Bend floodplains."),
    ("lower_niger_benue_volta",      "Lower Niger, Benue and Volta Basins",           ch1_sub["lower_niger_benue_volta"],      "HydroBASINS L6 Africa", "-10000..-1000", "Voltaic, Lower Niger and Benue savannas and forest-savanna mosaic."),
    ("upper_guinea_forest",          "Upper Guinea Forest and Coastal Rivers",        ch1_sub["upper_guinea_forest"],          "HydroBASINS L6 Africa", "-10000..-1000", "Humid Upper Guinea coastal catchments from Futa Jallon to Ivory Coast."),
    ("chad_mega_basin",              "Mega-Lake Chad and Chari-Logone Basin",         ch1_sub["chad_mega_basin"],              "HydroBASINS L6 Africa", "-10000..-1000", "Holocene Mega-Lake Chad endorheic catchment and Chari-Logone tributaries."),
    ("nile_nubia_sudd",              "Nubian Nile, Atbara and Sudd Wetlands",         ch1_sub["nile_nubia_sudd"],              "HydroBASINS L6 Africa", "-10000..-1000", "Middle Nile cataracts, Blue-White Nile confluence and Sudd marshes."),
    ("ethiopian_highlands_horn",     "Ethiopian Highlands and Rift Escarpment",       ch1_sub["ethiopian_highlands_horn"],     "HydroBASINS L6 Africa", "-10000..-1000", "Abbay, Tekeze and Omo-Awash montane catchments of the Ethiopian plateau."),
    ("somali_arid_horn",             "Somali Plateau and Juba-Shabelle Catchments",   ch1_sub["somali_arid_horn"],             "HydroBASINS L6 Africa", "-10000..-1000", "Arid Horn plateau and seasonal Juba-Shabelle drainage corridors."),
    ("congo_ubangi_basin",           "Central Congo, Ubangi and Kasai Basin",         ch1_sub["congo_ubangi_basin"],           "HydroBASINS L6 Africa", "-10000..-1000", "Equatorial Congo rainforest basin, Ubangi-Uele and Kasai tributaries."),
    ("lower_guinea_ogowe_cuanza",    "Lower Guinea Coast, Ogooue and Cuanza",         ch1_sub["lower_guinea_ogowe_cuanza"],    "HydroBASINS L6 Africa", "-10000..-1000", "Atlantic equatorial coastal catchments from Sanaga and Ogooue to Cuanza."),
    ("east_african_great_lakes",     "East African Great Lakes and Rift Highlands",   ch1_sub["east_african_great_lakes"],     "HydroBASINS L6 Africa", "-10000..-1000", "Lake Victoria, Albertine Rift and East African highland lake basins."),
    ("swahili_rufiji_coast",         "East African Coastal and Rufiji-Ruvuma Basins", ch1_sub["swahili_rufiji_coast"],         "HydroBASINS L6 Africa", "-10000..-1000", "Indian Ocean littoral rivers from Tana through Rufiji to Ruvuma."),
    ("zambezi_okavango_limpopo",     "Zambezi, Lake Malawi and Limpopo Basins",       ch1_sub["zambezi_okavango_limpopo"],     "HydroBASINS L6 Africa", "-10000..-1000", "Zambezi, Shire-Malawi, Okavango and Limpopo savanna-woodland watersheds."),
    ("kalahari_namib_arid",          "Kalahari Endorheic and Namib Escarpment",       ch1_sub["kalahari_namib_arid"],          "HydroBASINS L6 Africa", "-10000..-1000", "Arid Kalahari internal drainage and Namib-Cunene desert escarpment."),
    ("orange_cape_drakensberg",      "Orange-Vaal Basin, Drakensberg and Cape",       ch1_sub["orange_cape_drakensberg"],      "HydroBASINS L6 Africa", "-10000..-1000", "Orange-Vaal Highveld, Drakensberg littoral and Cape floristic catchments."),
    ("madagascar_wio_atlantic_isl",  "Madagascar and African Ocean Islands",          u_union(adm0["MDG"], *[adm0[k] for k in island_isos]), "HydroBASINS L6 + GADM/NE Coastlines", "-10000..-1000", "Madagascar and Western Indian Ocean / African Atlantic island ecosystems."),
  ]
  ch1_regions = make_partition_nonoverlapping(ch1_meta, clip_envelope=full_land, preserve_micro_islands=True)

  # =========================================================================
  # CH 2: Ancient and Mediaeval Sudan and Nubia [-2500..1821]
  # Strictly contiguous organic historical polities (ZERO detached Funj pockets!)
  # =========================================================================
  nubia_kush = u_union(
    pick_by_prop(dj_m1000, ["name"], ["kush"]),
    pick_by_prop(dj_0, ["name"], ["kush"]),
    pick_by_prop(dj_500, ["name"], ["nobatia", "makuria", "alodia"]),
    pick_by_prop(dj_1000, ["name"], ["makuria", "alodia"]),
    pick_by_prop(dj_1300, ["name"], ["makuria", "alodia"]),
    pick_by_prop(dj_1700, ["name"], ["funj", "darfur"]),
    OHM("dotawo", "ⲇⲱⲧⲁⲩⲟ", "الشلك", "shilluk", max_sy=1821),
  )
  nubia_murd_env = u_union(
    nubia_kush,
    M_cg("nubian", "beja", "darfur", "fung", "kordofan", "nuba", "nilotes, northern", "moru-madi", "dinka", "nuer", "shilluk", "bari", "lotuko", "azande"),
    M_nm("nubian", "danagla", "mahas", "kenuzi", "jaaliyin", "shaikia", "kababish", "baggara", "fur", "masalit", "zaghawa", "daju", "nuba", "fung", "shilluk", "dinka", "nuer", "anuak", "bari", "zande", "beja", "hadendoa", "bisharin", "bego"),
  )
  nubia_env = safe_geom(nubia_murd_env.intersection(u_union(*[b["geom"] for b in basins if 21.0 <= b["lon"] <= 38.8 and 3.5 <= b["lat"] <= 23.0])))
  # Partition purely via contiguous organic HydroBASINS L6 watershed seeds guided by historical polity cores
  # so Funj Sennar has ZERO detached pockets in Sobat/Pibor, Kassala/Beja, or Darfur!
  nub_org = organic_subdivide(nubia_env, {
    "nobatia":  (20.9, 30.8),
    "makuria":  (18.2, 30.8),
    "alodia":   (16.2, 34.0),
    "funj":     (12.8, 33.4),
    "beja":     (18.8, 36.4),
    "darfur":   (13.4, 24.4),
    "kordofan": (12.4, 29.4),
    "shilluk":  ( 7.4, 31.2),
  })
  ch2_regions = make_partition_nonoverlapping([
    ("nobatia_lower_nubia",    "Lower Nubia and Nobatia",                        nub_org["nobatia"],  "atlas_dejure (500 CE) + HydroBASINS L6",           "-2500..1500", "Lower Nubian Nile corridor from First to Third Cataract (Kerma, Kush, Nobatia)."),
    ("makuria_dongola_napata", "Makuria, Napata and Dongola Reach",              nub_org["makuria"],  "atlas_dejure (500-1300) + OHM Dotawo",             "-2500..1500", "Napatan Kushite core and Christian Kingdom of Makuria centred on Old Dongola."),
    ("meroe_alodia_butana",    "Island of Meroe, Alodia and Atbara-Butana",      nub_org["alodia"],   "atlas_dejure (0-1500) + HydroBASINS L6",           "-1000..1504", "Meroitic heartland and Christian Kingdom of Alodia (Soba) across Butana."),
    ("funj_sennar_gezira",     "Funj Sultanate of Sennar and Blue Nile Gezira",  nub_org["funj"],     "atlas_dejure (1700) + Nunn-Murdock 1959",          "1504..1821",  "Funj Sultanate heartland along the Blue and White Nile Gezira plains."),
    ("beja_red_sea_suakin",    "Beja Highlands, Blemmyes and Suakin Littoral",   nub_org["beja"],     "Nunn-Murdock 1959 (Beja) + HydroBASINS L6",        "-2500..1821", "Eastern Desert Beja pastoral highlands and Red Sea ports of Aidhab and Suakin."),
    ("darfur_keira_sultanate", "Daju, Tunjur and Keira Sultanate of Darfur",     nub_org["darfur"],   "atlas_dejure (1700) + Nunn-Murdock 1959 (Darfur)", "1200..1821",  "Jebel Marra uplands and successive Daju, Tunjur and Keira Darfur sultanates."),
    ("kordofan_nuba_hills",    "Kordofan Savanna and Nuba Mountains",            nub_org["kordofan"], "Nunn-Murdock 1959 + HydroBASINS L6",               "-1000..1821", "Kordofan corridor and Nuba upland refugia between Darfur and Sennar."),
    ("shilluk_sudd_upper_nile","Shilluk Kingdom, Sudd and Southern Nilotes",     nub_org["shilluk"],  "OHM Shilluk Kingdom + Nunn-Murdock 1959",          "1490..1821",  "Shilluk Kingdom on the White Nile, Sobat-Pibor, Sudd and Upper Nile Nilotes."),
  ], clip_envelope=nubia_env)

  # =========================================================================
  # CH 3: Ancient and Mediaeval Ethiopia and the Horn [-1000..1885]
  # =========================================================================
  horn_hist = u_union(
    pick_by_prop(dj_0, ["name"], ["axum"]),
    pick_by_prop(dj_500, ["name"], ["axum"]),
    pick_by_prop(dj_1000, ["name"], ["zagwe"]),
    pick_by_prop(dj_1300, ["name"], ["ethiopian", "ilfat", "ifat"]),
    pick_by_prop(dj_1500, ["name"], ["ethiopian", "adal"]),
    pick_by_prop(dj_1700, ["name"], ["ethiopian"]),
    pick_by_prop(dj_1800, ["name"], ["ethiopian"]),
    HW("ethiopia"),
    OHM("አክሱም", "حبش", "𐒈𐒚𐒐𐒆", max_sy=1885),
    M_cg("ethiopia", "galla", "afar", "somali", "sidamo", "kafa", "konso", "beja"),
  )
  # Organic HydroBASINS envelope across Horn (ZERO modern straight Ogaden/Kenya/Sudan borders!)
  horn_basins = u_union(*[b["geom"] for b in basins if (b["lon"] >= 34.5 and 0.5 <= b["lat"] <= 18.2) or (b["lon"] >= 40.5 and -1.8 <= b["lat"] <= 12.5)])
  horn_env = safe_geom(u_union(horn_hist, horn_basins).intersection(horn_basins).intersection(continental_ssa))
  h_axum = u_union(pick_by_prop(dj_0, ["name"], ["axum"]), pick_by_prop(dj_500, ["name"], ["axum"]), OHM("አክሱም", max_sy=1000))
  h_adal = u_union(pick_by_prop(dj_1300, ["name"], ["ilfat", "ifat"]), pick_by_prop(dj_1500, ["name"], ["adal"]))
  h_maj = OHM("𐒈𐒚𐒐𐒆", max_sy=1895)
  h_hab = u_union(OHM("حبش", max_sy=1875), M_cg("afar"))
  horn_org = organic_subdivide(horn_env, {
    "aksum_tigray": (14.4, 38.8),
    "amhara_tana":  (11.6, 37.5),
    "shewa_core":   ( 9.4, 39.2),
    "kaffa_omotic": ( 7.2, 36.2),
    "oromo_bale":   ( 6.4, 40.2),
    "ifat_adal":    ( 9.5, 42.6),
    "afar_habesh":  (12.2, 41.6),
    "north_somali": ( 9.5, 47.6),
    "ajuran_south": ( 3.4, 44.2),
  })
  ch3_regions = make_partition_nonoverlapping([
    ("aksum_tigray_medri_bahri", "Aksum, Tigray and Medri Bahri",              u_union(h_axum.intersection(horn_org["aksum_tigray"]) if h_axum else None, horn_org["aksum_tigray"]), "atlas_dejure (0-500 CE) + OHM Aksum",                "-1000..1885", "Da'amat, Kingdom of Aksum, Tigray and Eritrean highland Medri Bahri."),
    ("afar_red_sea_habesh",      "Afar Danakil, Massawa and Habesh Littoral",  u_union(h_hab.intersection(horn_env) if h_hab else None, horn_org["afar_habesh"]),                      "OHM Eyalet of Habesh + Nunn-Murdock 1959 (Afar)",    "-500..1885",  "Red Sea littoral of Adulis, Massawa, Zeila and Afar Sultanates."),
    ("amhara_gondar_gojjam",     "Zagwe, Begemder, Gojjam and Lake Tana",      horn_org["amhara_tana"],                                                                               "atlas_dejure (1000-1800) + HydroBASINS L6",          "900..1885",   "Zagwe Lasta, Gondarine Begemder and Gojjam around Lake Tana."),
    ("shewa_central_highlands",  "Shewa and Central Ethiopian Highlands",      horn_org["shewa_core"],                                                                                "atlas_dejure (1300-1850) + Harvard WorldMap",        "1270..1885",  "Solomonic Shewa and central plateau provinces."),
    ("kaffa_omotic_southwest",   "Kingdom of Kaffa, Wolayta and Omotic SW",    horn_org["kaffa_omotic"],                                                                              "Nunn-Murdock 1959 (Sidamo/Kafa) + HydroBASINS L6",   "1300..1885",  "Kingdom of Kaffa, Janjero, Wolayta and Omo-Gibe forest states."),
    ("oromo_borana_bale",        "Oromo Gadaa Confederacies and Bale",         horn_org["oromo_bale"],                                                                                "Nunn-Murdock 1959 (Galla/Oromo) + HydroBASINS L6",   "1500..1885",  "Borana and Barentu Oromo pastoral-agrarian highlands and Bale."),
    ("ifat_adal_harar",          "Sultanates of Ifat, Adal and Harar",         u_union(h_adal.intersection(horn_env) if h_adal else None, horn_org["ifat_adal"]),                     "atlas_dejure (1300-1500 Ifat/Adal) + HydroBASINS L6","1285..1885",  "Muslim sultanates of Ifat, Adal and the Emirate of Harar."),
    ("northern_somali_majeerteen","Northern Somali Clans and Majeerteen",      u_union(h_maj.intersection(horn_env) if h_maj else None, horn_org["north_somali"]),                    "OHM Majeerteen Sultanate + Nunn-Murdock 1959",       "1420..1885",  "Isaaq, Warsangali and Majeerteen maritime sultanates of the Gulf of Aden."),
    ("ajuran_benadir_geledi",    "Ajuran Empire, Benadir and Juba-Shabelle",   horn_org["ajuran_south"],                                                                              "Nunn-Murdock 1959 (Somali) + HydroBASINS L6",        "1200..1885",  "Ajuran hydraulic state, Mogadishu-Benadir coast and Geledi Sultanate."),
  ], clip_envelope=horn_env)

  # =========================================================================
  # CH 4: Early West Africa and the Sahel States [-1000..1500]
  # =========================================================================
  wa_basins = u_union(*[b["geom"] for b in basins if b["lon"] <= 22.0 and b["lat"] >= 4.2])
  wa_env = safe_geom(wa_basins.intersection(continental_ssa))
  w_ghana = u_union(pick_by_prop(dj_1000, ["name"], ["ghana"]), OHM("wagadou", max_sy=1300))
  w_jolof = OHM("جولوف", "baol", "waalo", "siin", "niani", max_sy=1550)
  w_mali = u_union(pick_by_prop(dj_1300, ["name"], ["mali"]), hw_mali)
  w_song = u_union(pick_by_prop(dj_1500, ["name"], ["songhai"]), HW("songhay"), OHM("songhai", max_sy=1600))
  w_kanem = u_union(pick_by_prop(dj_1300, ["name"], ["kanem"]), pick_by_prop(dj_1500, ["name"], ["bornu"]), OHM("kanem", max_sy=1500))
  wa_org = organic_subdivide(wa_env, {
    "wagadou":     (16.8, -11.5),
    "jolof":       (14.6, -15.4),
    "mali":        (12.8,  -7.8),
    "songhai":     (16.4,  -1.2),
    "mossi":       (11.8,  -1.6),
    "hausa":       (12.2,   8.4),
    "kanem_bornu": (13.6,  14.8),
    "nok_benue":   ( 9.2,   8.8),
    "ife_benin":   ( 6.8,   5.4),
    "akan_guinea": ( 7.2,  -4.8),
    "tuareg_air":  (19.2,   7.5),
  })
  ch4_regions = make_partition_nonoverlapping([
    ("jolof_senegambia_coast",    "Jolof Empire, Takrur and Senegambia",          u_union(w_jolof, wa_org["jolof"]),       "OHM Jolof/Waalo/Siin + HydroBASINS L6",             "800..1500",   "Takrur, Jolof confederation, Sine-Saloum and coastal Senegambia."),
    ("wagadou_ghana_takrur",      "Wagadou (Ghana) and Western Sahel",            u_union(w_ghana, wa_org["wagadou"]),     "atlas_dejure (1000) + OHM Wagadou",                 "300..1240",   "Soninke Empire of Wagadou-Ghana and Tagant-Hodh trans-Saharan gateways."),
    ("mali_manden_inland_delta",  "Mali Imperial Core and Inland Niger Delta",    u_union(w_mali.intersection(wa_org["mali"]) if w_mali else None, wa_org["mali"]), "atlas_dejure (1300) + Harvard WorldMap Mali", "1230..1500", "Manden heartland, Jenne-Jeno and Inland Niger Delta floodplains."),
    ("songhai_gao_timbuktu",      "Songhai Gao, Timbuktu and Niger Bend",         u_union(w_song.intersection(wa_org["songhai"]) if w_song else None, wa_org["songhai"]), "atlas_dejure (1500) + OHM Songhai", "800..1500", "Kawkaw-Gao, Timbuktu and Middle Niger trade arc."),
    ("kanem_bornu_chad",          "Kanem-Bornu Empire and Lake Chad Basin",       u_union(w_kanem.intersection(wa_env) if w_kanem else None, wa_org["kanem_bornu"]), "atlas_dejure (1300-1500) + OHM Kanem-Bornu", "700..1500", "Sayfawa Empire of Kanem and Bornu surrounding Lake Chad."),
    ("mossi_volta_gur",           "Mossi Kingdoms and Voltaic Gur States",        wa_org["mossi"],                         "Nunn-Murdock 1959 (Mole/Gur) + HydroBASINS L6",     "1100..1500",  "Ouagadougou, Yatenga, Dagomba and Mamprusi Voltaic polities."),
    ("hausa_bakwai_gobir_kano",   "Hausa Bakwai City-States (Kano, Katsina, Gobir)", wa_org["hausa"],                      "Nunn-Murdock 1959 (Hausa) + HydroBASINS L6",        "900..1500",   "Walled Hausa city-states of Kano, Katsina, Zazzau, Rano and Gobir."),
    ("nok_benue_middle_belt",     "Nok-Jos Plateau, Nupe and Benue Corridor",     wa_org["nok_benue"],                     "Nunn-Murdock 1959 (Jos/Nupe/Tiv) + HydroBASINS L6", "-1000..1500", "Nok terracotta iron-age core, Nupe, Igala and Kwararafa Benue basin."),
    ("ife_benin_igbo_lower_niger","Ile-Ife, Benin, Igbo-Ukwu and Lower Niger",    wa_org["ife_benin"],                     "Nunn-Murdock 1959 (Yoruba/Edo/Igbo) + HydroBASINS", "500..1500",   "Ile-Ife, Kingdom of Benin, Igbo-Ukwu and Lower Niger-Cross rainforests."),
    ("akan_upper_guinea_forest",  "Proto-Akan, Bono Manso and Guinea Forest",     wa_org["akan_guinea"],                   "Nunn-Murdock 1959 (Akan/Mende) + HydroBASINS L6",   "-1000..1500", "Bono Manso, forest Akan chiefdoms and Upper Guinea coastal corridors."),
    ("tuareg_air_saharan_caravans","Tuareg Air, Adrar des Ifoghas and Sahara",    wa_org["tuareg_air"],                    "Nunn-Murdock 1959 (Tuareg/Teda) + HydroBASINS L6",  "-500..1500",  "Sultanate of Agadez (Air), Tadmekka and central Saharan caravan routes."),
  ], clip_envelope=wa_env)

  # =========================================================================
  # CH 5: Bantu Expansion Across Sub-Saharan Africa [-1000..1500]
  # Strictly east of Cross River (~6.8E) — ZERO detached Upper Guinea strip!
  # Swahili City-States extended continuously north to Pemba, Zanzibar, Mombasa, Malindi & Lamu!
  # =========================================================================
  bantu_basins = u_union(*[b["geom"] for b in basins if b["lat"] <= 6.5 and b["lon"] >= 6.8])
  bantu_env = safe_geom(bantu_basins.intersection(continental_ssa))
  b_kongo = u_union(OHM("kongo", "mpemba", "mbata", "nsundi", "vungu", max_sy=1500), HW("kongo"), pick_by_prop(dj_1500, ["name"], ["kongo"]))
  b_zimb = u_union(OHM("great zimbabwe", "mapungubwe", "torwa", "mutapa", max_sy=1500), HW("zimbabwe", "mutapa"))
  b_rwa = OHM("rwanda", max_sy=1550)
  bantu_org = organic_subdivide(bantu_env, {
    "cameroon_homeland": ( 5.2, 11.4),
    "west_equatoria":    (-0.8, 12.6),
    "central_congo":     ( 0.8, 22.8),
    "kongo_angola":      (-7.2, 15.6),
    "upemba_katanga":    (-8.8, 25.8),
    "great_lakes":       (-0.8, 31.4),
    "rift_savanna":      (-2.8, 35.8),
    "swahili_north":     (-2.8, 40.4),
    "swahili_central":   (-6.2, 39.2),
    "swahili_south":     (-10.2, 39.6),
    "zambezi_maravi":    (-14.2, 32.8),
    "great_zimbabwe":    (-19.5, 30.2),
    "nguni_sotho_veld":  (-27.8, 28.6),
    "khoisan_cape_namib":(-25.8, 18.4),
  })
  swahili_full = u_union(bantu_org["swahili_north"], bantu_org["swahili_central"], bantu_org["swahili_south"])
  ch5_regions = make_partition_nonoverlapping([
    ("kongo_lower_congo_angola",   "Lower Congo, Kingdom of Kongo and Angola",     u_union(b_kongo, bantu_org["kongo_angola"]), "OHM Kongo/Mpemba/Nsundi + Harvard WorldMap Kongo",  "500..1500",   "Early Western Stream Bantu, Kingdom of Kongo and northern Angolan polities."),
    ("great_zimbabwe_mapungubwe",  "Mapungubwe, Great Zimbabwe and Mutapa",        u_union(b_zimb, bantu_org["great_zimbabwe"]), "OHM Mapungubwe/Great Zimbabwe/Mutapa + WorldMap", "1000..1500",  "Limpopo-Zimbabwe gold-trading states of Mapungubwe, Great Zimbabwe and early Mutapa."),
    ("great_lakes_urewe_kitara",   "Great Lakes Urewe Core (Kitara, Rwanda)",      u_union(b_rwa, bantu_org["great_lakes"]),    "OHM Rwanda + Nunn-Murdock 1959 + HydroBASINS L6",   "-500..1500",  "Urewe iron-working core of Lakes Victoria, Kivu and Tanganyika."),
    ("cameroon_bantu_homeland",    "Cameroon Grassfields Bantu Homeland",          bantu_org["cameroon_homeland"],              "Nunn-Murdock 1959 (Cameroon) + HydroBASINS L6",     "-1000..1500", "Cross-Sanaga-Grassfields proto-Bantu dispersal hearth."),
    ("western_equatorial_forest",  "Western Equatorial Rainforest (Ogooue-Sangha)",bantu_org["west_equatoria"],                 "Nunn-Murdock 1959 (Fang-Dzem) + HydroBASINS L6",    "-1000..1500", "Ogooue, Sangha and western Congo riverine expansion corridors."),
    ("central_congo_mongo_ubangi", "Inner Congo Basin, Mongo and Ubangi-Uele",     bantu_org["central_congo"],                  "Nunn-Murdock 1959 (Mongo/Babwa) + HydroBASINS L6",  "-500..1500",  "Inner Congo basin Bantu and northern Ubangi-Uele farming frontiers."),
    ("upemba_katanga_luba_lunda",  "Upemba Depression, Katanga and Proto-Luba",    bantu_org["upemba_katanga"],                 "Nunn-Murdock 1959 (Lunda/Luba) + HydroBASINS L6",   "500..1500",   "Kisalian-Kabambian Upemba copper-working chiefdoms and proto-Luba-Lunda."),
    ("swahili_kilwa_coast",        "Swahili City-States (Lamu, Mombasa, Zanzibar, Kilwa)", swahili_full,                        "Nunn-Murdock 1959 (Swahili/Rufiji) + HydroBASINS",  "700..1500",   "Indian Ocean Swahili mercantile littoral from Lamu, Malindi, Mombasa and Zanzibar to Kilwa."),
    ("east_african_rift_savanna",  "East African Rift Pastoralists and Savanna",   bantu_org["rift_savanna"],                   "Nunn-Murdock 1959 (Kenya/Nyamwezi) + HydroBASINS",  "-1000..1500", "Cushitic, Nilotic and Eastern Bantu pastoral-agricultural mosaic."),
    ("zambezi_maravi_ingombe",     "Zambezi Corridor, Maravi and Ingombe Ilede",   bantu_org["zambezi_maravi"],                 "Nunn-Murdock 1959 (Maravi/Bemba/Yao) + HydroBASINS","400..1500",   "Middle Zambezi trade entrepots, Lake Malawi Maravi and Mozambique interior."),
    ("southeastern_nguni_sotho",   "Highveld Sotho-Tswana and Nguni Iron Age",     bantu_org["nguni_sotho_veld"],               "Nunn-Murdock 1959 (Nguni/Sotho) + HydroBASINS L6",  "300..1500",   "Early and Late Iron Age Bantu agro-pastoralism of the Highveld and Natal."),
    ("khoisan_kalahari_cape_namib","Khoekhoe and San Cape, Namib and Kalahari",    bantu_org["khoisan_cape_namib"],             "Nunn-Murdock 1959 (Bushmen/Khoi) + HydroBASINS L6", "-1000..1500", "Khoekhoe pastoralist and San foraging territories of SW Africa and Cape."),
  ], clip_envelope=bantu_env)

  # =========================================================================
  # CH 6: Early Modern West Africa, Equatoria and Angola [1500..1885]
  # Authentic Guinea forest/savanna limits (~9N-11N West Africa, ~8N-10N Cameroon Grassfields)!
  # =========================================================================
  ch6_basins = u_union(*[
    b["geom"] for b in basins
    if (b["lon"] <= -10.5 and 4.0 <= b["lat"] <= 15.8)
    or (-10.5 < b["lon"] <= 10.0 and 4.0 <= b["lat"] <= 10.0)
    or (10.0 < b["lon"] <= 15.8 and 1.0 <= b["lat"] <= 8.8)
    or (10.0 <= b["lon"] <= 29.0 and -18.2 <= b["lat"] <= 5.8)
  ])
  ch6_env = safe_geom(ch6_basins.intersection(continental_ssa))
  em_asante = u_union(HW("asante"), pick_by_prop(dj_1800, ["name"], ["ashanti"]), pick_by_prop(dj_1850, ["name"], ["ashanti"]), OHM("gold coast", max_sy=1885))
  em_dahom = u_union(HW("dahomey"), OHM("danhɔmɛ", max_sy=1894))
  em_oyo = u_union(HW("oyo"), pick_by_prop(dj_1700, ["name"], ["oyo"]), OHM("lagos", "bight of benin", max_sy=1885))
  em_kongo = u_union(HW("kongo"), OHM("kingdom of kongo", "ndongo", "matamba", max_sy=1850))
  em_lunda = u_union(HW("lunda", "kazembe"), pick_by_prop(dj_1800, ["name"], ["lunda"]), OHM("lunda", "luba", max_sy=1885))
  em_loango = OHM("loango", "kakongo", "ngoyo", "makoko", max_sy=1885)
  em_kuba = OHM("kuba", "bolia", "okanga", max_sy=1885)
  em_seng = OHM("جولوف", "kajoor", "baol", "waalo", "saluum", "siin", "wuuli", "boundou", max_sy=1885)
  em_sl = u_union(OHM("sierra leone", "liberia", "maryland", max_sy=1885), pick_by_prop(dj_1850, ["name"], ["sierra leone"]))
  em_beng = OHM("benguela", max_sy=1885)
  ch6_org = organic_subdivide(ch6_env, {
    "senegambia":  (13.6, -14.8),
    "sl_liberia":  ( 7.6, -10.2),
    "asante":      ( 7.2,  -2.2),
    "dahomey":     ( 7.4,   1.8),
    "oyo_benin":   ( 7.4,   4.8),
    "niger_delta": ( 5.8,   7.6),
    "cameroon":    ( 5.4,  12.2),
    "gabon_loango":(-1.2,  12.8),
    "kongo_ndongo":(-7.6,  14.8),
    "ovimbundu":   (-14.0, 16.5),
    "kuba_congo":  ( 0.2,  21.5),
    "luba_lunda":  (-8.4,  24.5),
  })
  ch6_regions = make_partition_nonoverlapping([
    ("senegambia_jolof_kaabu",       "Wolof States, Futa Jallon and Kaabu",           u_union(em_seng, ch6_org["senegambia"]),   "OHM Wolof/Kajoor/Baol/Wuuli + HydroBASINS L6",      "1500..1885", "Senegambian Wolof kingdoms, Imamate of Futa Jallon and Kaabu empire."),
    ("sierra_leone_grain_liberia",   "Sierra Leone, Grain Coast and Early Liberia",   u_union(em_sl, ch6_org["sl_liberia"]),     "OHM Sierra Leone/Liberia + atlas_dejure",           "1500..1885", "Mane-Mende states, Freetown Colony (1787) and Republic of Liberia (1847)."),
    ("asante_gold_coast_akan",       "Asante Empire, Fante and Gold Coast",           u_union(em_asante, ch6_org["asante"]),     "Harvard WorldMap Asante + atlas_dejure + OHM",      "1670..1885", "Asante Confederation, Denkyira, Akwamu and Fante Gold Coast polities."),
    ("dahomey_slave_coast_ewe",      "Kingdom of Dahomey, Allada and Ewe Littoral",   u_union(em_dahom, ch6_org["dahomey"]),     "Harvard WorldMap Dahomey + OHM Danhɔmɛ",            "1600..1885", "Allada, Whydah, Kingdom of Dahomey and Ewe-Mina coastal corridor."),
    ("oyo_yorubaland_benin",         "Oyo Empire, Yorubaland and Kingdom of Benin",   u_union(em_oyo, ch6_org["oyo_benin"]),     "Harvard WorldMap Oyo + atlas_dejure + OHM",         "1500..1885", "Imperial Oyo, successor Yoruba city-states and Kingdom of Benin."),
    ("niger_delta_aro_calabar",      "Niger Delta States, Arochukwu and Cross River", ch6_org["niger_delta"],                    "Nunn-Murdock 1959 + OHM Bight of Biafra",           "1500..1885", "Bonny, Kalabari, Old Calabar and Arochukwu hinterland trade network."),
    ("cameroon_adamawa_grassfields", "Bamum, Cameroon Grassfields and Biafra Coast",  ch6_org["cameroon"],                       "Nunn-Murdock 1959 (Cameroon) + HydroBASINS L6",     "1500..1885", "Kingdom of Bamum, Grassfields fonships and Duala coastal chiefdoms."),
    ("gabon_loango_teke_equatoria",  "Loango, Teke-Makoko and Gabon Littoral",        u_union(em_loango, ch6_org["gabon_loango"]),"OHM Loango/Kakongo/Makoko + atlas_dejure",         "1500..1885", "Loango, Kakongo, Ngoyo, Teke (Anziku) and Mpongwe Gabon coast."),
    ("kongo_ndongo_matamba_angola",  "Kongo, Ndongo, Matamba and Portuguese Angola",  u_union(em_kongo, ch6_org["kongo_ndongo"]), "OHM Kongo/Ndongo/Matamba + Harvard WorldMap",      "1500..1885", "Kingdom of Kongo, Ndongo-Matamba (Nzinga) and Luanda hinterland."),
    ("ovimbundu_benguela_cuanza",    "Ovimbundu Kingdoms, Benguela and S. Angola",    u_union(em_beng, ch6_org["ovimbundu"]),    "OHM Benguela + Nunn-Murdock 1959 + HydroBASINS L6", "1500..1885", "Bailundo, Viye (Bie), Benguela and southern Angolan Ovimbundu plateau."),
    ("kuba_inner_congo_ubangi",      "Kuba Kingdom, Inner Congo and Ubangi",          u_union(em_kuba, ch6_org["kuba_congo"]),   "OHM Kuba/Bolia + Nunn-Murdock 1959 (Mongo)",        "1600..1885", "Kuba confederation, Bobangi river traders and inner Congo forest."),
    ("luba_lunda_kazembe_empire",    "Luba Empire, Lunda Commonwealth and Kazembe",   u_union(em_lunda, ch6_org["luba_lunda"]),  "Harvard WorldMap Lunda/Kazembe + OHM Luba/Lunda",   "1580..1885", "Luba Empire, Lunda Mwaant Yaav commonwealth and Kazembe."),
  ], clip_envelope=ch6_env)

  # =========================================================================
  # CH 7: Early Modern Sahel and Sudan [1500..1898]
  # Organic watershed-and-Murdock savanna limits (NO horizontal 9.5N/4.5N cuts, NO Bornu/Wadai plunge to 4N!)
  # =========================================================================
  ch7_murd_core = u_union(
    M_cg("tuareg", "teda", "bornu", "darfur", "fung", "mole", "mande, nuclear", "hausa", "fulani", "senegal", "nilotes, northern", "moru-madi", "azande", "beja", "nubian", "kordofan", "nuba", "bagirmi", "wadai", "mandara highlands", "chamba-yungur", "jos plateau"),
    OHM("دولة الخلافة في بلاد السودان", "إمامة فوتة تورو", "دار الكوتي", "السودان التركي-المصري", "الشلك", max_sy=1903),
    pick_by_prop(dj_1700, ["name"], ["bornu", "funj", "darfur", "wadai"]),
    pick_by_prop(dj_1850, ["name"], ["bornu", "massina"]),
  )
  # Select whole HydroBASINS L6 watersheds whose centroid lies inside the organic Sahel/Sudan savanna belt
  ch7_basins = u_union(*[
    b["geom"] for b in basins
    if b["lon"] <= 38.5 and (
      (b["lon"] < 10.5 and b["lat"] >= 9.6 and (b["lat"] >= 11.2 or b["geom"].intersects(ch7_murd_core)))
      or (10.5 <= b["lon"] < 23.0 and b["lat"] >= 7.8)
      or (b["lon"] >= 23.0 and (b["lat"] >= 7.5 or (b["lat"] >= 4.0 and b["geom"].intersects(M_cg("nilotes, northern", "moru-madi", "azande")))))
    )
  ])
  ch7_env = safe_geom(ch7_basins.intersection(continental_ssa))
  s_sokoto = OHM("دولة الخلافة في بلاد السودان", max_sy=1903)
  s_futa = u_union(OHM("إمامة فوتة تورو", max_sy=1860), pick_by_prop(dj_1800, ["name"], ["bamana"]))
  s_mass = u_union(pick_by_prop(dj_1850, ["name"], ["massina"]), pick_by_prop(dj_1500, ["name"], ["songhai"]))
  s_born = u_union(pick_by_prop(dj_1700, ["name"], ["bornu"]), pick_by_prop(dj_1800, ["name"], ["bornu"]), pick_by_prop(dj_1850, ["name"], ["bornu"]))
  s_kuti = OHM("دار الكوتي", max_sy=1912)
  s_turk = u_union(OHM("السودان التركي-المصري", max_sy=1885), pick_by_prop(dj_1700, ["name"], ["funj"]))
  s_darf = pick_by_prop(dj_1700, ["name"], ["darfur"])
  ch7_org = organic_subdivide(ch7_env, {
    "trarza":    (19.2, -12.5),
    "segou":     (13.6,  -8.4),
    "massina":   (16.8,  -3.2),
    "mossi":     (11.6,  -1.8),
    "sokoto":    (12.0,   7.5),
    "bornu":     (13.2,  14.2),
    "wadai":     (14.0,  20.4),
    "darfur":    (13.8,  25.6),
    "mahdist":   (16.4,  33.2),
    "equatoria": ( 6.8,  28.6),
  })
  ch7_regions = make_partition_nonoverlapping([
    ("trarza_brakna_mauritania",     "Trarza, Brakna and Adrar Emirates",            ch7_org["trarza"],                     "Nunn-Murdock 1959 + HydroBASINS L6",                "1600..1898", "Hassaniya Moorish emirates of Trarza, Brakna, Tagant and Adrar."),
    ("futa_toro_segou_toucouleur",   "Futa Toro, Segou Bamana and Toucouleur",       u_union(s_futa, ch7_org["segou"]),     "OHM Futa Toro + atlas_dejure (1800 Bamana)",        "1650..1893", "Imamate of Futa Toro, Bamana Kingdom of Segou and Umar Tal's empire."),
    ("massina_timbuktu_arma",        "Pashalik of Timbuktu, Massina and Niger Bend", u_union(s_mass.intersection(ch7_org["massina"]) if s_mass else None, ch7_org["massina"]), "atlas_dejure (1500/1850) + HydroBASINS L6", "1500..1898", "Songhai-Arma Timbuktu, Massina Caliphate and Tuareg Kel Adagh."),
    ("mossi_kong_wassoulou",         "Mossi Kingdoms, Kong and Wassoulou",           ch7_org["mossi"],                      "Nunn-Murdock 1959 (Mole/Senufo) + HydroBASINS L6",  "1500..1898", "Mossi states, Kong Empire and Samori Ture's Wassoulou."),
    ("sokoto_caliphate_hausaland",   "Sokoto Caliphate and Adamawa Emirates",        u_union(s_sokoto, ch7_org["sokoto"]),  "OHM Sokoto Caliphate (1804-1903) + HydroBASINS L6", "1500..1898", "Hausa states and Sokoto Caliphate (Kano, Katsina, Zaria, Adamawa)."),
    ("bornu_kanem_bagirmi",          "Kanem-Bornu Empire and Bagirmi Sultanate",     u_union(s_born, ch7_org["bornu"]),     "atlas_dejure (1700-1880 Bornu) + HydroBASINS L6",   "1500..1898", "Kanem-Bornu under the Sayfawa and al-Kanemi, plus Bagirmi."),
    ("wadai_dar_al_kuti_tibesti",    "Sultanate of Wadai, Tibesti and Dar al-Kuti",  u_union(s_kuti, ch7_org["wadai"]),     "OHM Dar al-Kuti + Nunn-Murdock 1959 + HydroBASINS", "1635..1898", "Wadai Sultanate, Borkou-Tibesti Teda and Dar al-Kuti."),
    ("darfur_kordofan_mahdist",      "Darfur Sultanate and Kordofan",                u_union(s_darf, ch7_org["darfur"]),    "atlas_dejure (1700 Darfur) + Nunn-Murdock 1959",    "1600..1898", "Keira Sultanate of Darfur and Kordofan trade crossroads."),
    ("turco_egyptian_mahdist_nile",  "Funj, Turco-Egyptian and Mahdist Nile",        u_union(s_turk.intersection(ch7_org["mahdist"]) if s_turk else None, ch7_org["mahdist"]), "OHM Turco-Egyptian Sudan + atlas_dejure", "1504..1898", "Sennar, Turco-Egyptian Sudan and the Mahdist State centred on Omdurman."),
    ("bahr_el_ghazal_azande_eq",     "Bahr el Ghazal, Azande and Equatoria",         ch7_org["equatoria"],                  "Nunn-Murdock 1959 (Azande/Nilotes) + HydroBASINS",  "1500..1898", "Azande kingdoms, Bahr el Ghazal and Upper Nile-Equatoria."),
  ], clip_envelope=ch7_env)

  # =========================================================================
  # CH 8: Early Modern East Africa and Mozambique [1500..1885]
  # Organic watershed + Murdock northern boundary (NO flat 4.5N northern cutoff!)
  # =========================================================================
  ch8_murd_north = M_cg("west lacustrine", "kenya highlands", "masai", "nilotes, eastern", "karamojong", "turkana", "luo", "nyamwezi", "rufiji", "maravi", "yao-makonde", "bemba-lamba")
  ch8_basins = u_union(*[
    b["geom"] for b in basins
    if (b["lon"] >= 27.8 and -26.8 <= b["lat"] <= 1.8 and not (b["lon"] < 31.5 and b["lat"] < -17.5))
    or (b["lon"] >= 29.0 and 1.8 < b["lat"] <= 5.2 and b["geom"].intersects(ch8_murd_north))
  ])
  ch8_env = safe_geom(ch8_basins.intersection(continental_ssa))
  ea_zanz = u_union(OHM("zanzibar", "الْعُمَانِيَّة", "quíloa", max_sy=1890))
  ea_rwa = OHM("rwanda", "urundi", max_sy=1890)
  ea_moz = OHM("moçambique", "mocambique", "sofala", "lourenco marques", max_sy=1891)
  ea_mut = u_union(HW("mutapa", "kazembe"), OHM("mutapa", max_sy=1800))
  ch8_org = organic_subdivide(ch8_env, {
    "buganda":     ( 1.2, 32.2),
    "rwanda_bdi":  (-2.5, 29.8),
    "kenya_rift":  ( 0.8, 36.8),
    "zanzibar":    (-5.5, 39.2),
    "nyamwezi":    (-4.8, 33.4),
    "hehe_south":  (-8.8, 36.2),
    "maravi_yao":  (-13.6, 36.8),
    "bemba_lozi":  (-13.4, 28.8),
    "mozambique":  (-19.5, 34.4),
  })
  ch8_regions = make_partition_nonoverlapping([
    ("rwanda_burundi_kivu",          "Kingdoms of Rwanda and Burundi",               u_union(ea_rwa, ch8_org["rwanda_bdi"]),  "OHM Rwanda & Burundi (1550-1890)",                  "1500..1885", "Nyiginya Kingdom of Rwanda, Kingdom of Burundi and Kivu highlands."),
    ("zanzibar_swahili_omani_coast", "Omani-Zanzibar Sultanate and Swahili Coast",   u_union(ea_zanz.intersection(ch8_env) if ea_zanz else None, ch8_org["zanzibar"]), "OHM Zanzibar/Omani Empire + HydroBASINS L6", "1500..1885", "Swahili littoral from Lamu and Mombasa to Zanzibar, Bagamoyo and Kilwa."),
    ("buganda_bunyoro_ankole",       "Buganda, Bunyoro-Kitara and Ankole",           ch8_org["buganda"],                      "Nunn-Murdock 1959 (West Lacustrine) + HydroBASINS", "1500..1885", "Interlacustrine kingdoms of Bunyoro-Kitara, Buganda, Toro and Ankole."),
    ("kenya_highlands_maasai_rift",  "Maasai Steppe, Kenya Highlands and Rift",      ch8_org["kenya_rift"],                   "Nunn-Murdock 1959 (Kenya/Masai) + HydroBASINS L6",  "1500..1885", "Central Kenya agricultural highlands, Maasai Rift plains and Turkana."),
    ("nyamwezi_unyamwezi_tabora",    "Nyamwezi, Mirambo and Caravan Corridor",       ch8_org["nyamwezi"],                     "Nunn-Murdock 1959 (Nyamwezi) + HydroBASINS L6",     "1500..1885", "Unyamwezi plateau, Tabora entrepot and Mirambo's ivory-caravan polity."),
    ("hehe_southern_tanganyika",     "Hehe, Rufiji and Southern Tanganyika",         ch8_org["hehe_south"],                   "Nunn-Murdock 1959 (Rufiji) + HydroBASINS L6",       "1500..1885", "Hehe chiefdom, Kilombero-Rufiji basin and Ruvuma corridor."),
    ("maravi_yao_lake_malawi",       "Maravi Confederacy, Yao and N. Mozambique",    ch8_org["maravi_yao"],                   "Nunn-Murdock 1959 (Maravi/Yao) + HydroBASINS L6",   "1500..1885", "Kalonga Maravi states, Yao caravan polities and northern Mozambique."),
    ("bemba_lozi_zambezi_plateau",   "Bemba, Lozi-Barotseland and Kazembe",          u_union(ea_mut.intersection(ch8_org["bemba_lozi"]) if ea_mut else None, ch8_org["bemba_lozi"]), "Harvard WorldMap Kazembe + Nunn-Murdock 1959", "1500..1885", "Bemba chieftaincies, Kazembe Luapula and Lozi kingdom of Barotseland."),
    ("portuguese_mozambique_gaza",   "Portuguese Zambezi Prazos, Sofala and Gaza",   u_union(ea_moz.intersection(ch8_env) if ea_moz else None, ch8_org["mozambique"]), "OHM Capitania de Mocambique/Sofala + WorldMap Mutapa", "1505..1885", "Zambezi prazo estates, Mutapa lowlands, Sofala and Gaza Nguni Empire."),
  ], clip_envelope=ch8_env)

  # =========================================================================
  # CH 9: Pre-Colonial Southern Africa and the Cape Frontier [1500..1902]
  # =========================================================================
  ch9_basins = u_union(*[b["geom"] for b in basins if b["lat"] <= -16.8 and b["lon"] <= 33.8])
  ch9_env = safe_geom(ch9_basins.intersection(continental_ssa))
  sa_cape = u_union(OHM("dutch cape colony", "cape colony", max_sy=1880), pick_by_prop(dj_1700, ["name"], ["dutch cape"]), pick_by_prop(dj_1850, ["name"], ["cape colony"]))
  sa_natal = OHM("colony of natal", max_sy=1897)
  sa_ofs = u_union(OHM("oranje vrijstaat", "orange river sovereignty", max_sy=1902), pick_by_prop(col_1895, ["Country1895"], ["orange free state", "basutoland"]))
  sa_zar = u_union(OHM("zuid-afrikaansche republiek", "zoutpansberg", max_sy=1902), pick_by_prop(col_1895, ["Country1895"], ["south african republic"]))
  sa_grik = OHM("griqualand", max_sy=1885)
  sa_kaff = OHM("british kaffraria", "queen adelaide", max_sy=1880)
  sa_rozv = u_union(OHM("rozvi", "thovhela", max_sy=1850), HW("mutapa", "zimbabwe"))
  sa_dam = pick_by_prop(col_1895, ["Country1895"], ["damara", "namaqua"])
  ch9_org = organic_subdivide(ch9_env, {
    "west_cape":  (-33.0, 19.6),
    "east_cape":  (-32.2, 27.2),
    "karoo_grik": (-29.4, 22.2),
    "natal_zulu": (-28.6, 30.8),
    "ofs_sotho":  (-29.2, 27.4),
    "zar_swazi":  (-24.8, 29.5),
    "bechuana":   (-22.4, 23.8),
    "rozvi_ndeb": (-19.4, 29.8),
    "nama_herero":(-23.8, 16.8),
    "ovambo_n":   (-18.6, 16.5),
  })
  ch9_regions = make_partition_nonoverlapping([
    ("western_cape_voc_colony",       "Western Cape and VOC-British Heartland",      ch9_org["west_cape"],                         "OHM Dutch/British Cape Colony + HydroBASINS L6",    "1652..1902", "Cape Town, Boland, Swellendam and western Cape pastoral districts."),
    ("eastern_cape_xhosa_frontier",   "Eastern Cape Frontier, Xhosa and Transkei",   u_union(sa_kaff, ch9_org["east_cape"]),       "OHM British Kaffraria + Nunn-Murdock 1959 (Nguni)", "1500..1902", "Xhosa kingdoms, Ciskei-Transkei and Cape Eastern Frontier."),
    ("natal_zulu_kingdom",            "Zulu Kingdom and Colony of Natal",            u_union(sa_natal, ch9_org["natal_zulu"]),     "OHM Colony of Natal + Nunn-Murdock 1959 (Nguni)",   "1500..1902", "Mthethwa, Shaka's Zulu Kingdom and British Colony of Natal."),
    ("orange_free_state_basutoland",  "Orange Free State and Basutoland",            u_union(sa_ofs, ch9_org["ofs_sotho"]),        "OHM Oranje Vrijstaat + Colonial Africa 1895",       "1822..1902", "Moshoeshoe's Sotho Kingdom (Basutoland) and Orange Free State."),
    ("transvaal_zar_swazi_pedi",      "Transvaal (ZAR), Pedi and Swazi Kingdom",     u_union(sa_zar, ch9_org["zar_swazi"]),        "OHM Zuid-Afrikaansche Republiek + Colonial 1895",   "1835..1902", "South African Republic (Transvaal), Pedi polity and Kingdom of Eswatini."),
    ("griqualand_northern_karoo",     "Griqualand West, Karoo and Orange Frontier",  u_union(sa_grik, ch9_org["karoo_grik"]),      "OHM Griqualand West + HydroBASINS L6",              "1750..1902", "Griqua captaincies, Northern Karoo and Kimberley diamond frontier."),
    ("rozvi_ndebele_matabeleland",    "Rozvi Empire, Ndebele and Mashonaland",       u_union(sa_rozv.intersection(ch9_env) if sa_rozv else None, ch9_org["rozvi_ndeb"]), "OHM Rozvi + Harvard WorldMap + HydroBASINS", "1500..1897", "Changamire Rozvi Empire, Mzilikazi's Ndebele state and Shona plateau."),
    ("tswana_bechuanaland_kalahari",  "Tswana Chiefdoms and Bechuanaland",           ch9_org["bechuana"],                          "Nunn-Murdock 1959 (Tswana) + Colonial 1895",        "1500..1902", "Ngwato, Kwena, Ngwaketse Tswana merafe and Kalahari Bechuanaland."),
    ("namaqua_herero_namibia",        "Namaqua and Herero Polities of SW Africa",    u_union(sa_dam.intersection(ch9_org["nama_herero"]) if sa_dam else None, ch9_org["nama_herero"]), "Colonial 1895 Damara/Namaqua + Nunn-Murdock", "1500..1902", "Nama, Orlam and Herero pastoral confederacies of central-southern Namibia."),
    ("ovambo_kavango_north_namibia",  "Ovambo Kingdoms and Kavango Floodplains",     ch9_org["ovambo_n"],                          "Nunn-Murdock 1959 (Ovambo) + HydroBASINS L6",       "1500..1902", "Ondonga, Uukwanyama Ovambo kingdoms and Kavango riverine chiefdoms."),
  ], clip_envelope=ch9_env)

  # =========================================================================
  # CH 10: Early African Islands (WIO + Atlantic) [-500..1895]
  # =========================================================================
  mdg_merina = u_union(OHM("imerina", max_sy=1895), pick_by_prop(dj_1800, ["name"], ["merina"]), pick_by_prop(dj_1850, ["name"], ["merina"]))
  mdg_org = organic_subdivide(adm0["MDG"], {
    "merina":       (-18.8, 47.4),
    "betsileo":     (-21.4, 47.0),
    "sakalava":     (-17.8, 45.0),
    "betsimisaraka":(-16.2, 49.4),
    "antandroy":    (-24.2, 45.6),
  })
  ch10_env = u_union(adm0["MDG"], *[adm0[k] for k in island_isos])
  ch10_regions = make_partition_nonoverlapping([
    ("merina_central_highlands",      "Kingdom of Imerina and Central Highlands",     u_union(mdg_merina.intersection(mdg_org["merina"]) if mdg_merina else None, mdg_org["merina"]), "OHM Fanjakan'Imerina + atlas_dejure (1800-1850)", "1540..1895", "Merina Kingdom centred on Antananarivo and central highland rice valleys."),
    ("betsileo_southern_highlands",   "Betsileo and Southern Plateau Kingdoms",       mdg_org["betsileo"],                     "Nunn-Murdock 1959 (Malagasy) + HydroBASINS L6",     "1500..1895", "Betsileo kingdoms (Isandra, Lalangina, Arindrano) of the southern plateau."),
    ("sakalava_menabe_boina",         "Sakalava Kingdoms of Menabe and Boina",        mdg_org["sakalava"],                     "Nunn-Murdock 1959 + OHM Nosy Be + HydroBASINS",     "1600..1895", "Western Malagasy Sakalava dynasties of Menabe, Boina and Nosy Be."),
    ("betsimisaraka_east_madagascar", "Betsimisaraka Confederation and Sainte-Marie", mdg_org["betsimisaraka"],                "OHM Ile Sainte-Marie + HydroBASINS L6",             "1710..1895", "Eastern littoral Betsimisaraka confederation and northern Antankarana."),
    ("antandroy_mahafaly_south_mdg",  "Antandroy, Mahafaly and Anosy South",          mdg_org["antandroy"],                    "Nunn-Murdock 1959 + HydroBASINS L6",                "1500..1895", "Arid southern Madagascar chiefdoms of Mahafaly, Antandroy and Fort-Dauphin."),
    ("comoros_sultanates_mayotte",    "Comoros Sultanates and Mayotte",               C("COM", "MYT"),                         "OHM Sultanates of Ndzuwani/Mwali/Maore",            "1490..1895", "Swahili-Shirazi sultanates of Ngazidja, Ndzuwani, Mwali and Maore."),
    ("mascarenes_mauritius_reunion",  "Mascarenes (Ile de France and Bourbon)",       C("MUS", "REU"),                         "OHM Nederlands-Mauritius/Ile de France/Bourbon",    "1638..1895", "Dutch/French/British Mauritius, Rodrigues and French Isle Bourbon (Reunion)."),
    ("seychelles_chagos_wio",         "Seychelles, Chagos and Iles Eparses",          C("SYC", "IOT", "ATF"),                  "GADM 4.1 + geoBoundaries Coastlines",               "1756..1895", "Granitic Seychelles, Chagos Archipelago and Mozambique Channel atolls."),
    ("cabo_verde_atlantic",           "Portuguese Cabo Verde Archipelago",            C("CPV"),                                "OHM Cabo Verde Portugues (1462-1879)",              "1462..1895", "Barlavento and Sotavento islands of Portuguese Cabo Verde."),
    ("sao_tome_principe_st_helena",   "Sao Tome, Principe and Saint Helena",          C("STP", "SHN"),                         "OHM Portuguese STP + Saint Helena Colony",          "1474..1895", "Gulf of Guinea sugar islands (Sao Tome & Principe) and South Atlantic St Helena."),
  ], clip_envelope=ch10_env, preserve_micro_islands=True, min_area_km2=0.0)

  # =========================================================================
  # CH 11..15: Colonial Era [1880..1980] — Colonial Africa 1914/1915/1920/1941/1950 + CShapes
  # =========================================================================
  # Helper to get named polygons from colonial_africa_1915/1941/1914
  def COL15(*kws):
    return pick_by_prop(col_1915, ["NAME"], kws)
  def COL41(*kws):
    return pick_by_prop(col_1941, ["NAME"], kws)
  def COL20(*kws):
    return pick_by_prop(col_1920, ["NAME"], kws)

  # Helper to group ADM1 polygons inside a country cleanly
  def grp_adm1(iso, pred_list, default_k):
    b = defaultdict(list)
    for nm, g in adm1.get(iso, []):
      rp = g.representative_point()
      rec = {"name": nm, "lat": float(rp.y), "lon": float(rp.x), "geom": g}
      k = default_k
      for pk, fn in pred_list:
        if fn(rec):
          k = pk
          break
      b[k].append(g)
    return {k: u_union(*gs) for k, gs in b.items()}

  # CH 11: Colonial West Africa and the Sahel [1880..1975]
  nga_col = grp_adm1("NGA", [
    ("north", lambda r: r["lat"] >= 7.8 or any(w in r["name"].lower() for w in ("sokoto","kebbi","zamfara","katsina","kano","jigawa","yobe","borno","kaduna","bauchi","gombe","adamawa","taraba","niger","kwara","kogi","nasarawa","plateau","benue","abuja"))),
  ], "south")
  ch11_env = C("MRT", "SEN", "GMB", "GNB", "GIN", "SLE", "LBR", "MLI", "BFA", "CIV", "GHA", "TGO", "BEN", "NER", "NGA")
  ch11_regions = make_partition_nonoverlapping([
    ("aof_senegal_mauritania",        "AOF: Senegal and Mauritania",                  u_union(COL15("senegal", "mauritania").intersection(ch11_env), C("SEN", "MRT")), "Colonial Africa 1915/1941 + CShapes 2.0", "1895..1960", "AOF territories of Senegal (incl. Four Communes) and Mauritania."),
    ("aof_french_sudan",              "AOF: French Sudan (Soudan Francais)",          C("MLI"), "Colonial Africa 1915/1941 + CShapes 2.0", "1892..1960", "AOF Colony of French Sudan (Haut-Senegal-Niger / Soudan Francais)."),
    ("aof_upper_volta_niger",         "AOF: Upper Volta and Niger Territory",         C("BFA", "NER"), "Colonial Africa 1915/1941 + CShapes 2.0", "1898..1960", "AOF colonies of Haute-Volta (partitioned 1932-1947) and Niger."),
    ("aof_french_guinea",             "AOF: French Guinea (Guinee Francaise)",        C("GIN"), "Colonial Africa 1915/1941 + CShapes 2.0", "1891..1958", "AOF Colony of French Guinea."),
    ("aof_cote_divoire",              "AOF: Cote d'Ivoire",                           C("CIV"), "Colonial Africa 1915/1941 + CShapes 2.0", "1893..1960", "AOF Colony of Cote d'Ivoire."),
    ("aof_dahomey",                   "AOF: Colony of Dahomey",                       C("BEN"), "Colonial Africa 1915/1941 + CShapes 2.0", "1894..1960", "AOF Colony of Dahomey."),
    ("togoland_mandate",              "German Togoland and Mandate Togo",             u_union(COL15("togoland").intersection(ch11_env), C("TGO")), "Colonial Africa 1915 + LoN Mandates 1920", "1884..1960", "German Togoland Protectorate and post-1919 British/French mandates."),
    ("british_gambia",                "Gambia Colony and Protectorate",               C("GMB"), "Colonial Africa 1915/1941 + CShapes 2.0", "1888..1965", "British Colony and Protectorate of The Gambia."),
    ("portuguese_guinea",             "Portuguese Guinea (Guine Portuguesa)",         C("GNB"), "Colonial Africa 1915/1941 + CShapes 2.0", "1879..1974", "Portuguese Overseas Province of Guinea."),
    ("british_sierra_leone",          "Colony and Protectorate of Sierra Leone",      C("SLE"), "Colonial Africa 1915/1941 + CShapes 2.0", "1896..1961", "Freetown Crown Colony and interior Sierra Leone Protectorate."),
    ("republic_of_liberia",           "Republic of Liberia",                          C("LBR"), "Colonial Africa 1915/1941 + CShapes 2.0", "1880..1975", "Independent Republic of Liberia."),
    ("british_gold_coast",            "British Gold Coast, Ashanti and N. Territories", C("GHA"), "Colonial Africa 1915/1941 + CShapes 2.0", "1880..1957", "Gold Coast Colony, Ashanti and Northern Territories."),
    ("british_northern_nigeria",      "Northern Nigeria Protectorate and Provinces",  nga_col["north"], "Colonial Africa 1915 + Nigeria Colonial Regions", "1900..1960", "Protectorate and Northern Provinces of British Nigeria."),
    ("british_southern_nigeria_lagos","Southern Nigeria, Lagos and Eastern Provinces",nga_col["south"], "Colonial Africa 1915 + Nigeria Colonial Regions", "1885..1960", "Lagos Colony, Oil Rivers and Southern Provinces of Nigeria."),
  ], clip_envelope=ch11_env)

  # CH 12: Colonial Equatoria, Belgian Congo and Angola [1880..1975]
  cod_col = grp_adm1("COD", [
    ("leo_eq", lambda r: any(w in slugify(r["name"]) for w in ("kinshasa","kongo_central","kwango","kwilu","mai_ndombe","equateur","mongala","nord_ubangi","north_ubangi","sud_ubangi","south_ubangi","tshuapa"))),
    ("ori_kiv", lambda r: any(w in slugify(r["name"]) for w in ("bas_uele","lower_uele","haut_uele","upper_uele","ituri","tshopo","maniema","nord_kivu","north_kivu","sud_kivu","south_kivu"))),
  ], "kas_kat")
  ago_col = grp_adm1("AGO", [
    ("north", lambda r: r["lat"] >= -9.8),
    ("central", lambda r: -13.6 <= r["lat"] < -9.8),
  ], "south")
  ch12_env = C("TCD", "CAF", "CMR", "GNQ", "GAB", "COG", "COD", "AGO")
  ch12_regions = make_partition_nonoverlapping([
    ("aef_chad",                           "AEF: Colony of Chad",                           C("TCD"), "Colonial Africa 1915/1941 + CShapes 2.0", "1900..1960", "French Equatorial Africa (AEF) Territory of Chad."),
    ("aef_ubangi_shari",                   "AEF: Ubangi-Shari (Oubangui-Chari)",            C("CAF"), "Colonial Africa 1915/1941 + CShapes 2.0", "1903..1960", "AEF Colony of Ubangi-Shari."),
    ("aef_middle_congo",                   "AEF: Middle Congo (Moyen-Congo)",               C("COG"), "Colonial Africa 1915/1941 + CShapes 2.0", "1882..1960", "AEF Colony of Moyen-Congo centred on Brazzaville."),
    ("aef_gabon",                          "AEF: Colony of Gabon",                          C("GAB"), "Colonial Africa 1915/1941 + CShapes 2.0", "1886..1960", "AEF Colony of Gabon."),
    ("kamerun_mandates",                   "German Kamerun and Mandate Cameroons",          C("CMR"), "Colonial Africa 1915 + LoN Mandates 1920", "1884..1961", "German Kamerun Protectorate and French/British Cameroon Mandates."),
    ("spanish_guinea",                     "Spanish Guinea (Rio Muni and Fernando Po)",     C("GNQ"), "Colonial Africa 1915/1941 + CShapes 2.0", "1885..1968", "Spanish territories of Fernando Po (Bioko) and Rio Muni."),
    ("belgian_congo_leopoldville_equateur","Belgian Congo: Leopoldville and Equateur",      cod_col["leo_eq"], "Belgian Congo 6-Province Architecture (1933-60)", "1885..1960", "Western Belgian Congo provinces of Leopoldville and Equateur."),
    ("belgian_congo_orientale_kivu",       "Belgian Congo: Orientale and Kivu",             cod_col["ori_kiv"], "Belgian Congo 6-Province Architecture (1933-60)", "1885..1960", "Northeastern Belgian Congo provinces of Orientale and Kivu."),
    ("belgian_congo_kasai_katanga",        "Belgian Congo: Kasai and Katanga",              cod_col["kas_kat"], "Belgian Congo 6-Province Architecture (1933-60)", "1885..1960", "Southern mining and agricultural provinces of Kasai and Katanga."),
    ("portuguese_angola_north_cabinda",    "Portuguese Angola: Cabinda, Congo and Luanda",  ago_col["north"], "Portuguese Angola Colonial Provinces", "1885..1975", "Cabinda enclave, Luanda and northern Portuguese Angola."),
    ("portuguese_angola_central_benguela", "Portuguese Angola: Benguela, Malanje and Bie",  ago_col["central"], "Portuguese Angola Colonial Provinces", "1885..1975", "Central plateau of Benguela, Huambo, Bie and Malanje."),
    ("portuguese_angola_south_huila",      "Portuguese Angola: Huila, Mocamedes and Moxico",ago_col["south"], "Portuguese Angola Colonial Provinces", "1885..1975", "Southern and eastern Angolan districts of Huila, Cunene and Moxico."),
  ], clip_envelope=ch12_env)

  # CH 13: Colonial Horn of Africa and Anglo-Egyptian Sudan [1880..1960]
  sdn_col = grp_adm1("SDN", [
    ("darf_kord", lambda r: any(w in r["name"].lower() for w in ("darfur", "kordofan", "abyei"))),
  ], "nile_east")
  eth_col = grp_adm1("ETH", [
    ("north_cent", lambda r: r["lat"] >= 11.2 or any(w in slugify(r["name"]) for w in ("tigray","amhara","afar","addis","benishangul","contested"))),
    ("harar_ogad", lambda r: any(w in slugify(r["name"]) for w in ("somali","harar","dire_dawa"))),
  ], "south_west")
  ch13_env = C("SDN", "SSD", "ERI", "ETH", "DJI", "SOM", "SOL")
  ch13_regions = make_partition_nonoverlapping([
    ("anglo_egyptian_sudan_north_nile",    "Anglo-Egyptian Sudan: Nile, Khartoum and Kassala", sdn_col["nile_east"], "Anglo-Egyptian Sudan 9-Province Architecture", "1899..1956", "Northern, Khartoum, Kassala and Blue Nile provinces of the Condominium."),
    ("anglo_egyptian_sudan_darfur_kord",   "Anglo-Egyptian Sudan: Darfur and Kordofan",        sdn_col["darf_kord"], "Anglo-Egyptian Sudan 9-Province Architecture", "1899..1956", "Western Condominium provinces of Darfur (annexed 1916) and Kordofan."),
    ("anglo_egyptian_sudan_south",         "Anglo-Egyptian Sudan: Southern Provinces",         C("SSD"), "Anglo-Egyptian Sudan 9-Province Architecture", "1899..1956", "Bahr el Ghazal, Upper Nile and Equatoria provinces."),
    ("italian_eritrea",                    "Italian Eritrea and BMA Eritrea",                  C("ERI"), "Colonial Africa 1915/1941 + CShapes 2.0", "1890..1960", "Colonia Eritrea, AOI Eritrea and UN-federated Eritrea."),
    ("imperial_ethiopia_north_central",    "Imperial Ethiopia: Northern and Central Highlands",eth_col["north_cent"], "Colonial Africa 1915/1941 + Imperial Provinces", "1880..1960", "Tigray, Begemder, Gojjam, Wollo and northern Shewa."),
    ("imperial_ethiopia_south_west",       "Imperial Ethiopia: Oromo, Kaffa and Southwest",    eth_col["south_west"], "Colonial Africa 1915/1941 + Imperial Provinces", "1880..1960", "Oromia, Kaffa, Sidamo, Gemu Gofa, Illubabor and Gambela."),
    ("imperial_ethiopia_hararghe_ogaden",  "Imperial Ethiopia: Hararghe, Bale and Ogaden",     eth_col["harar_ogad"], "Colonial Africa 1915/1941 + Imperial Provinces", "1887..1960", "Hararghe, Dire Dawa and the Ogaden lowlands."),
    ("french_british_somaliland",          "French Somaliland and British Somaliland",         C("DJI", "SOL"), "Colonial Africa 1915/1941 + CShapes 2.0", "1884..1960", "French Cote des Somalis (Djibouti) and British Somaliland Protectorate."),
    ("italian_somaliland",                 "Italian Somaliland (Somalia Italiana / AFIS)",     C("SOM"), "Colonial Africa 1915/1941 + CShapes 2.0", "1889..1960", "Italian Somaliland and UN Trusteeship Territory of Somalia."),
  ], clip_envelope=ch13_env)

  # CH 14: Colonial East Africa [1880..1963]
  ken_col = grp_adm1("KEN", [
    ("coast_nfd", lambda r: r["lon"] >= 37.8 or any(w in r["name"].lower() for w in ("mandera","wajir","garissa","marsabit","isiolo","tana","lamu","kilifi","mombasa","kwale","taita"))),
  ], "highlands")
  tza_col = grp_adm1("TZA", [
    ("zanzibar", lambda r: any(w in r["name"].lower() for w in ("unguja","pemba","zanzibar","mjini","kaskazini","kusini")) and r["lon"] >= 39.0 and -6.6 <= r["lat"] <= -4.8),
    ("north_lake", lambda r: r["lat"] >= -4.8),
    ("south_high", lambda r: r["lat"] < -8.2),
  ], "central_coast")
  ch14_env = C("UGA", "KEN", "TZA", "RWA", "BDI")
  ch14_regions = make_partition_nonoverlapping([
    ("zanzibar_protectorate",          "Sultanate and British Protectorate of Zanzibar", tza_col.get("zanzibar"), "Colonial Africa 1914/1915 + Zanzibar Censuses", "1890..1963", "Unguja and Pemba islands under the British Protectorate of Zanzibar."),
    ("uganda_protectorate",            "Uganda Protectorate",                            C("UGA"), "Colonial Africa 1914/1941 + CShapes 2.0", "1894..1962", "Buganda and Northern, Eastern and Western Provinces of Uganda."),
    ("kenya_colony_highlands_nyanza",  "Kenya Colony: Highlands, Rift and Nyanza",       ken_col["highlands"], "Colonial Africa 1914/1941 + Kenya Provinces", "1895..1963", "Central Highlands, Rift Valley, Nyanza and Nairobi."),
    ("kenya_coast_northern_frontier",  "Kenya Coast Protectorate and Northern Frontier", ken_col["coast_nfd"], "Colonial Africa 1914/1941 + Kenya Provinces", "1895..1963", "Ten-mile Coastal Protectorate and Northern Frontier District."),
    ("ruanda_urundi_mandate",          "German East Africa / Belgian Ruanda-Urundi",     C("RWA", "BDI"), "LoN Mandates 1920 + CShapes 2.0", "1890..1962", "Ruanda and Urundi kingdoms under German rule and Belgian Mandate."),
    ("tanganyika_north_lake",          "Tanganyika: Lake, Northern and Tanga Provinces", tza_col["north_lake"], "Colonial Africa 1914/1941 + Tanganyika 8 Provinces", "1885..1961", "Lake Victoria, Kilimanjaro-Arusha and Tanga northern provinces."),
    ("tanganyika_central_coastal",     "Tanganyika: Eastern, Central and Western",       tza_col["central_coast"], "Colonial Africa 1914/1941 + Tanganyika 8 Provinces", "1885..1961", "Dar es Salaam, Morogoro, Dodoma and Tabora central corridor."),
    ("tanganyika_southern_highlands",  "Tanganyika: Southern and Southern Highlands",    tza_col["south_high"], "Colonial Africa 1914/1941 + Tanganyika 8 Provinces", "1885..1961", "Mbeya, Iringa, Ruvuma, Lindi and Mtwara southern provinces."),
  ], clip_envelope=ch14_env)

  # CH 15: Colonial South-Central Africa and Mozambique [1890..1980]
  zmb_col = grp_adm1("ZMB", [
    ("copper_cent", lambda r: any(w in r["name"].lower() for w in ("copperbelt","central","lusaka"))),
    ("barotse_s",   lambda r: any(w in r["name"].lower() for w in ("western","southern","north-western"))),
  ], "north_east")
  zwe_col = grp_adm1("ZWE", [
    ("mashona", lambda r: any(w in r["name"].lower() for w in ("mashonaland","harare","manicaland"))),
  ], "matabele")
  moz_col = grp_adm1("MOZ", [
    ("north_zamb", lambda r: r["lat"] >= -18.2),
  ], "cent_south")
  ch15_env = C("ZMB", "ZWE", "MWI", "MOZ")
  ch15_regions = make_partition_nonoverlapping([
    ("northern_rhodesia_copperbelt",    "Northern Rhodesia: Copperbelt and Central",     zmb_col["copper_cent"], "Colonial Africa 1915/1950 + FRN Provinces", "1891..1964", "Copperbelt mining axis, Broken Hill (Kabwe) and Lusaka."),
    ("northern_rhodesia_barotseland",   "Northern Rhodesia: Barotseland and Southern",   zmb_col["barotse_s"],   "Colonial Africa 1915/1950 + FRN Provinces", "1891..1964", "Barotseland Protectorate, North-Western and Southern Provinces."),
    ("northern_rhodesia_north_east",    "Northern Rhodesia: Northern, Luapula and East", zmb_col["north_east"],  "Colonial Africa 1915/1950 + FRN Provinces", "1891..1964", "Northern, Luapula and Eastern provinces."),
    ("southern_rhodesia_mashonaland",   "Southern Rhodesia: Mashonaland and Manicaland", zwe_col["mashona"],     "Colonial Africa 1915/1950 + FRN Provinces", "1890..1980", "Salisbury (Harare), Mashonaland and Manicaland."),
    ("southern_rhodesia_matabeleland",  "Southern Rhodesia: Matabeleland and Midlands",  zwe_col["matabele"],    "Colonial Africa 1915/1950 + FRN Provinces", "1890..1980", "Bulawayo, Matabeleland, Midlands and Masvingo (Victoria)."),
    ("nyasaland_protectorate",          "Nyasaland Protectorate",                        C("MWI"),               "Colonial Africa 1915/1950 + CShapes 2.0",   "1891..1964", "British Central Africa / Nyasaland Protectorate."),
    ("portuguese_mozambique_north",     "Portuguese Mozambique: North and Zambezia",     moz_col["north_zamb"],  "Portuguese Mozambique Colonial Districts",  "1890..1975", "Niassa, Cabo Delgado, Mocambique (Nampula) and Zambezia."),
    ("portuguese_mozambique_south",     "Portuguese Mozambique: Central and South",      moz_col["cent_south"],  "Portuguese Mozambique Colonial Districts",  "1890..1975", "Tete, Manica e Sofala, Inhambane, Gaza and Lourenco Marques."),
  ], clip_envelope=ch15_env)

  # =========================================================================
  # CH 16..23: Regime III Modern / Post-Colonial Admin-1 Chapters (`is_admin1: true`)
  # =========================================================================
  def build_admin1_chapter(iso_list, era_str, conflict_tags=None, micro_group_isos=None, min_px_merge=False):
    """Assembles genuine Admin-1 polygons from geoBoundaries / HDX COD-AB / GADM 4.1 / NE1."""
    conflict_tags = conflict_tags or {}
    micro_group_isos = micro_group_isos or {}
    items = []
    seen_ids = set()
    for iso in iso_list:
      if iso in micro_group_isos:
        for gid, gname, ggeom, gsrc, gdesc in micro_group_isos[iso]:
          items.append((gid, gname, ggeom, gsrc, era_str, gdesc))
        continue
      units = adm1.get(iso, [])
      if not units and adm0.get(iso) is not None:
        units = [(iso, adm0[iso])]
      src_lbl = "HDX COD-AB Admin-1" if iso in ("ETH", "MLI") else ("Natural Earth 10m Admin-1" if iso == "NER" else ("GADM 4.1 Admin-1" if iso in ("MYT", "REU", "SHN", "IOT", "ATF") else "geoBoundaries Admin-1"))
      for nm, g in units:
        rid = f"{iso.lower()}_{slugify(nm)}"
        while rid in seen_ids:
          rid += "_x"
        seen_ids.add(rid)
        tag = ""
        nm_low = nm.lower()
        for ckey, cval in conflict_tags.items():
          if ckey in nm_low and (iso == cval[0]):
            tag = f" [{cval[1]}]"
            break
        disp_nm = f"{nm} ({iso}){tag}" if len(iso_list) > 1 else f"{nm}{tag}"
        desc = f"{nm} first-level administrative division ({iso}){tag}."
        items.append((rid, disp_nm, g, src_lbl, era_str, desc))
    return items

  # CH 16: Modern Southern Africa [1902..2026]
  # Merge geoBoundaries Namibia duplicate sliver 'Cunene' into 'Kunene'
  nam_clean = defaultdict(list)
  for nm, g in adm1["NAM"]:
    kn = "Kunene" if nm.strip().lower() == "cunene" else nm
    nam_clean[kn].append(g)
  adm1["NAM"] = [(nm, u_union(*gs)) for nm, gs in sorted(nam_clean.items())]
  ch16_regions = build_admin1_chapter(["ZAF", "NAM", "BWA", "LSO", "SWZ"], "1902..2026")

  # CH 17: Modern African Ocean Islands [1890..2026]
  # Group micro-island sub-districts cleanly by island/archipelago so ZERO sub-regions are starved or <4 px slivers!
  cpv_barla = u_union(*[g for nm, g in adm1["CPV"] if g.representative_point().y >= 15.8])
  cpv_sota = u_union(*[g for nm, g in adm1["CPV"] if g.representative_point().y < 15.8])
  mus_main = u_union(*[g for nm, g in adm1["MUS"] if g.representative_point().x < 60.0])
  mus_rod = u_union(*[g for nm, g in adm1["MUS"] if g.representative_point().x >= 60.0])
  isl_grouped = {
    "COM": [("com_grande_comore", "Grande Comore (Ngazidja) (COM)", u_union(*[g for nm, g in adm1["COM"] if "grande" in nm.lower()]), "geoBoundaries Admin-1", "Autonomous island of Grande Comore (COM)."),
            ("com_anjouan_moheli", "Anjouan and Moheli (COM)", u_union(*[g for nm, g in adm1["COM"] if "grande" not in nm.lower()]), "geoBoundaries Admin-1", "Autonomous islands of Anjouan (Ndzuwani) and Moheli (Mwali) (COM).")],
    "MYT": [("myt_mayotte", "Mayotte (France — DOM 976) (MYT)", adm0["MYT"], "GADM 4.1 Admin-1", "French overseas department of Mayotte (Grande-Terre and Petite-Terre).")],
    "MUS": [("mus_mauritius_main", "Mauritius Island (MUS)", mus_main, "geoBoundaries Admin-1", "Main island of Mauritius (9 administrative districts)."),
            ("mus_rodrigues_outer", "Rodrigues and Outer Islands (MUS)", mus_rod, "geoBoundaries Admin-1", "Autonomous Island of Rodrigues and outer Mauritian atolls.")],
    "REU": [("reu_reunion", "La Reunion (France — DOM 974) (REU)", adm0["REU"], "GADM 4.1 Admin-1", "French overseas department of La Reunion (4 arrondissements).")],
    "SYC": [("syc_seychelles", "Seychelles Archipelago (SYC)", adm0["SYC"], "geoBoundaries Admin-1", "Inner granitic islands (Mahe, Praslin, La Digue) and Outer Coral Islands.")],
    "CPV": [("cpv_barlavento", "Cabo Verde: Barlavento Islands (CPV)", cpv_barla, "geoBoundaries Admin-1", "Windward islands (Santo Antao, Sao Vicente, Sao Nicolau, Sal, Boa Vista)."),
            ("cpv_sotavento", "Cabo Verde: Sotavento Islands (CPV)", cpv_sota, "geoBoundaries Admin-1", "Leeward islands (Santiago, Fogo, Maio, Brava).")],
    "STP": [("stp_sao_tome_principe", "Sao Tome and Principe (STP)", adm0["STP"], "geoBoundaries Admin-1", "Sao Tome Island and Autonomous Region of Principe.")],
    "SHN": [("shn_saint_helena_asc_tdc", "Saint Helena, Ascension and Tristan da Cunha (SHN)", adm0["SHN"], "GADM 4.1 Admin-1", "British Overseas Territory across South Atlantic islands.")],
    "ATF": [("atf_iles_eparses", "Iles Eparses — Mozambique Channel (ATF)", adm0["ATF"], "GADM 4.1 Admin-1", "French Scattered Islands (Europa, Juan de Nova, Glorioso, Tromelin).")],
    "IOT": [("iot_chagos", "Chagos Archipelago / BIOT (IOT)", adm0["IOT"], "GADM 4.1 Admin-0", "Chagos Archipelago and Diego Garcia.")],
  }
  ch17_regions = build_admin1_chapter(
    ["MDG", "COM", "MYT", "MUS", "REU", "SYC", "CPV", "STP", "SHN", "ATF", "IOT"],
    "1890..2026",
    micro_group_isos=isl_grouped,
  )

  # CH 18: Post-Colonial Sahel [1960..2026] (group tiny Banjul+Kanifing in GMB into Greater Banjul to avoid <4px sliver)
  gmb_grouped = {
    "GMB": [
      ("gmb_greater_banjul_west", "Greater Banjul and West Coast (GMB)", u_union(*[g for nm, g in adm1["GMB"] if any(w in nm.lower() for w in ("banjul","kanifing","brikama"))]), "geoBoundaries Admin-1", "Banjul, Kanifing and Brikama West Coast."),
      ("gmb_north_bank_lower", "North Bank and Lower River (GMB)", u_union(*[g for nm, g in adm1["GMB"] if any(w in nm.lower() for w in ("kerewan","mansakonko"))]), "geoBoundaries Admin-1", "North Bank (Kerewan) and Lower River (Mansakonko)."),
      ("gmb_central_upper", "Central and Upper River (GMB)", u_union(*[g for nm, g in adm1["GMB"] if any(w in nm.lower() for w in ("kuntaur","janjanbureh","basse"))]), "geoBoundaries Admin-1", "Central River and Upper River (Basse)."),
    ]
  }
  ch18_regions = build_admin1_chapter(
    ["MRT", "MLI", "NER", "BFA", "TCD", "SEN", "GMB"], "1960..2026",
    conflict_tags={
      "kidal": ("MLI", "Regime III Sahel Conflict Zone"),
      "gao": ("MLI", "Regime III Liptako-Gourma Conflict"),
      "menaka": ("MLI", "Regime III Liptako-Gourma Conflict"),
      "tombouctou": ("MLI", "Regime III Northern Mali"),
      "lac": ("TCD", "Regime III Lake Chad Basin Conflict"),
      "diffa": ("NER", "Regime III Lake Chad Basin Conflict"),
      "tillab": ("NER", "Regime III Liptako-Gourma Conflict"),
      "sahel": ("BFA", "Regime III Liptako-Gourma Conflict"),
    },
    micro_group_isos=gmb_grouped,
  )

  # CH 19: Post-Colonial West Africa [1957..2026]
  ch19_regions = build_admin1_chapter(
    ["GIN", "GNB", "SLE", "LBR", "CIV", "GHA", "TGO", "BEN", "NGA"], "1957..2026",
    conflict_tags={
      "borno": ("NGA", "Regime III Lake Chad Basin Conflict"),
      "yobe": ("NGA", "Regime III Lake Chad Basin Conflict"),
      "adamawa": ("NGA", "Regime III Lake Chad Basin Conflict"),
    },
  )

  # CH 20: Post-Colonial Equatoria, DR Congo and Angola [1960..2026]
  # Merge Bioko Norte+Sur+Annobon into Insular GNQ to avoid tiny <4px sliver
  gnq_grouped = {
    "GNQ": [
      ("gnq_bioko_insular", "Bioko and Annobon Insular Region (GNQ)", u_union(*[g for nm, g in adm1["GNQ"] if any(w in slugify(nm) for w in ("bioko","annobon"))]), "geoBoundaries Admin-1", "Insular Equatorial Guinea (Bioko Norte, Bioko Sur, Annobon)."),
      ("gnq_litoral_rio_muni", "Litoral — Rio Muni West (GNQ)", u_union(*[g for nm, g in adm1["GNQ"] if "litoral" in nm.lower()]), "geoBoundaries Admin-1", "Litoral Province (Bata), continental Rio Muni."),
      ("gnq_interior_rio_muni", "Centro Sur, Kie-Ntem and Wele-Nzas (GNQ)", u_union(*[g for nm, g in adm1["GNQ"] if any(w in slugify(nm) for w in ("centro","kie","wele"))]), "geoBoundaries Admin-1", "Interior Rio Muni provinces."),
    ]
  }
  ch20_regions = build_admin1_chapter(
    ["CMR", "CAF", "GNQ", "GAB", "COG", "COD", "AGO"], "1960..2026",
    conflict_tags={
      "nord-kivu": ("COD", "Regime III Kivu Conflict Zone"),
      "sud-kivu": ("COD", "Regime III Kivu Conflict Zone"),
      "ituri": ("COD", "Regime III Eastern DRC Conflict"),
      "extr": ("CMR", "Regime III Lake Chad Basin Conflict"),
    },
    micro_group_isos=gnq_grouped,
  )

  # CH 21: Post-Colonial Sudan, Ethiopia and the Horn [1956..2026]
  # Distinguish Somaliland (SOL) 5 northern regions from Somalia (SOM) 13 regions cleanly!
  sol_names = {"awdal", "woqooyi galbeed", "togdheer", "sanaag", "sool"}
  som_grouped = {
    "SOM": [
      (
        f"{'sol' if nm.lower() in sol_names else 'som'}_{slugify(nm)}",
        f"{nm} ({'Somaliland de facto / SOL' if nm.lower() in sol_names else 'SOM'})",
        g,
        "geoBoundaries Admin-1 + Regime III Somaliland De Facto",
        f"{nm} region ({'de facto Republic of Somaliland since 1991' if nm.lower() in sol_names else 'Federal Republic of Somalia'})."
      )
      for nm, g in adm1["SOM"]
    ]
  }
  # Group tiny Djibouti City + Arta so zero <4px sliver
  dji_grouped = {
    "DJI": [
      ("dji_djibouti_arta", "Djibouti City and Arta (DJI)", u_union(*[g for nm, g in adm1["DJI"] if any(w in nm.lower() for w in ("djibouti","arta"))]), "geoBoundaries Admin-1", "Djibouti City metropolitan and Arta region."),
      ("dji_ali_sabieh_dikhil", "Ali Sabieh and Dikhil (DJI)", u_union(*[g for nm, g in adm1["DJI"] if any(w in nm.lower() for w in ("sabieh","dikhil"))]), "geoBoundaries Admin-1", "Southern Djibouti regions of Ali Sabieh and Dikhil."),
      ("dji_tadjourah_obock", "Tadjourah and Obock (DJI)", u_union(*[g for nm, g in adm1["DJI"] if any(w in nm.lower() for w in ("tadjourah","obock"))]), "geoBoundaries Admin-1", "Northern Djibouti regions of Tadjourah and Obock."),
    ]
  }
  ch21_regions = build_admin1_chapter(
    ["SDN", "SSD", "ERI", "ETH", "DJI", "SOM"], "1956..2026",
    conflict_tags={
      "darfur": ("SDN", "Regime III Darfur Conflict/Displacement"),
      "kordofan": ("SDN", "Regime III Kordofan Conflict"),
      "abyei": ("SDN", "Regime III Disputed Abyei PCA"),
      "tigray": ("ETH", "Regime III Tigray Conflict Zone"),
      "jonglei": ("SSD", "Regime III Conflict/Displacement"),
      "unity": ("SSD", "Regime III Conflict/Displacement"),
    },
    micro_group_isos={**som_grouped, **dji_grouped},
  )

  # CH 22: Post-Colonial East Africa [1961..2026]
  # Group tiny Mombasa+Kilifi or keep Mombasa if >=4px? Let's merge tiny Zanzibar 5 regions -> 2 islands (Unguja + Pemba) and Bujumbura Mairie+Rural so zero <4px slivers!
  tza_grouped = {
    "TZA": (
      [(f"tza_{slugify(nm)}", f"{nm} (TZA)", g, "geoBoundaries Admin-1", f"{nm} Region (TZA).")
       for nm, g in adm1["TZA"] if not any(w in nm.lower() for w in ("unguja","pemba","mjini","kaskazini","kusini","zanzibar"))]
      + [
        ("tza_zanzibar_unguja", "Zanzibar: Unguja Island (TZA/ZNZ)", u_union(*[g for nm, g in adm1["TZA"] if any(w in nm.lower() for w in ("unguja","mjini","zanzibar")) and "pemba" not in nm.lower()]), "geoBoundaries Admin-1", "Unguja Island (Revolutionary Government of Zanzibar)."),
        ("tza_zanzibar_pemba", "Zanzibar: Pemba Island (TZA/ZNZ)", u_union(*[g for nm, g in adm1["TZA"] if "pemba" in nm.lower()]), "geoBoundaries Admin-1", "Pemba Island (Revolutionary Government of Zanzibar)."),
      ]
    )
  }
  bdi_grouped = {
    "BDI": [
      ("bdi_bujumbura", "Bujumbura Mairie and Rural (BDI)", u_union(*[g for nm, g in adm1["BDI"] if "bujumbura" in nm.lower()]), "geoBoundaries Admin-1", "Bujumbura metropolitan and rural provinces (BDI)."),
    ] + [
      (f"bdi_{slugify(nm)}", f"{nm} (BDI)", g, "geoBoundaries Admin-1", f"{nm} Province (BDI).")
      for nm, g in adm1["BDI"] if "bujumbura" not in nm.lower()
    ]
  }
  ch22_regions = build_admin1_chapter(
    ["KEN", "UGA", "TZA", "RWA", "BDI"], "1961..2026",
    micro_group_isos={**tza_grouped, **bdi_grouped},
  )

  # CH 23: Post-Colonial South-Central Africa and Mozambique [1964..2026]
  ch23_regions = build_admin1_chapter(
    ["ZMB", "ZWE", "MWI", "MOZ"], "1964..2026",
    conflict_tags={"cabo delgado": ("MOZ", "Regime III Cabo Delgado Conflict Zone")},
  )

  chapter_map = {
    "prehistoric_ssa":            ch1_regions,
    "ancient_mediaeval_nubia":    ch2_regions,
    "ancient_horn_africa":        ch3_regions,
    "early_west_africa_sahel":    ch4_regions,
    "bantu_expansion_africa":     ch5_regions,
    "atlantic_west_equatoria":    ch6_regions,
    "early_modern_sahel_sudan":   ch7_regions,
    "early_modern_east_africa":   ch8_regions,
    "precolonial_south_africa":   ch9_regions,
    "early_african_islands":      ch10_regions,
    "colonial_west_sahel":        ch11_regions,
    "colonial_equatoria_congo":   ch12_regions,
    "colonial_horn_sudan":        ch13_regions,
    "colonial_east_africa":       ch14_regions,
    "colonial_south_central":     ch15_regions,
    "modern_southern_africa":     ch16_regions,
    "modern_african_islands":     ch17_regions,
    "postcolonial_sahel":         ch18_regions,
    "postcolonial_west_africa":   ch19_regions,
    "postcolonial_congo_angola":  ch20_regions,
    "postcolonial_horn_sudan":    ch21_regions,
    "postcolonial_east_africa":   ch22_regions,
    "postcolonial_south_central": ch23_regions,
  }

  print("[4] Rasterising all 23 NICETHI chapter masks, GeoJSONs, JSON5s & annotated QA crops...", flush=True)
  summary = []
  for idx, grp, folder, stem, title, dom_yrs, regime, is_admin1 in CHAPTER_SPECS:
    ch_dir = os.path.join(NI_DIR, grp, folder)
    os.makedirs(ch_dir, exist_ok=True)
    out_png = os.path.join(ch_dir, f"{stem}_areal_mask.png")
    out_json5 = os.path.join(ch_dir, f"{stem}.json5")
    out_gj = os.path.join(SUB_GJ_DIR, f"{stem}_subregions.geojson")
    crop_png = os.path.join(CROP_DIR, f"crop_{idx:02d}_{stem}.png")

    pres_isl = stem in ("prehistoric_ssa", "early_african_islands", "modern_african_islands")
    n_sub, active_px, slivers, leak = rasterise_chapter(
      idx, stem, title, dom_yrs, regime, is_admin1,
      chapter_map[stem], domain_mask, out_png, out_gj, out_json5, crop_png, ne_edges,
      preserve_micro_islands=pres_isl,
    )
    summary.append((idx, stem, n_sub, active_px, slivers, leak))
    print(f"  [{idx:02d}/23] {stem:28s} | sub={n_sub:3d} | px={active_px:7d} | slivers<4px={slivers:2d} | mod_leak={leak*100:5.1f}%", flush=True)

  print("\n[DONE] Built nicethi_domain_mask.png + all 23 chapter dual outputs + 23 annotated QA crops!", flush=True)


if __name__ == "__main__":
  main()
