"""Shared Historical GIS, Topology Repair, OpenCV Rasterisation & Lambert Azimuthal
Equal-Area Cartography Utilities for Operation Viscount Project JAGUAR.

Scope: Mexico, Central America, the Caribbean Islands, and Bermuda.
"""

import csv
import io
import json
import math
import os
import re
import sqlite3
import sys
import unicodedata
import zipfile
from collections import defaultdict

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch, Polygon as MplPolygon
import numpy as np
import shapefile
import shapely
from scipy.ndimage import distance_transform_edt
from shapely import wkb
from shapely.geometry import (
  GeometryCollection,
  LineString,
  MultiPolygon,
  Polygon,
  box,
  shape,
)
from shapely.ops import transform as shp_transform, unary_union
from shapely.validation import make_valid

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
JAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JAGUAR")
JAG_SHARED = os.path.join(JAG_DIR, "_shared")
JAG_GIS = os.path.join(JAG_SHARED, "_gis_cache")
SUB_GJ_DIR = os.path.join(JAG_GIS, "chapter_subregions")
HGIS_ROOT = os.path.join(JAG_SHARED, "subadmin_hgis")
HGIS_RAW = os.path.join(HGIS_ROOT, "raw_sources")
HGIS_PARSED = os.path.join(HGIS_ROOT, "parsed")
HGIS_RASTERS = os.path.join(HGIS_ROOT, "rasters")
DOMAIN_MASK_PNG = os.path.join(JAG_SHARED, "sites_jaguar_mesoamerica", "config", "jaguar_domain_mask.png")
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
PARENT_GIS_CACHE = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared", "_gis_cache")
SHARED_UTILS = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared")
TESTS_MASK_CROPS = os.path.join(SVEA_ROOT, "tests", "mask_crops")
TESTS_SUBADMIN_CROPS = os.path.join(SVEA_ROOT, "tests", "subadmin_crops")

if SHARED_UTILS not in sys.path:
  sys.path.insert(0, SHARED_UTILS)

from viscount_plot_utils import apply_viscount_style, save_viscount_figure

GRID_W, GRID_H = 4320, 2160

ALL_HYDE_YEARS = [
  -10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000,
  0, 100, 200, 300, 400, 500, 600, 700, 800, 900,
  1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
  1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790,
  1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890,
  1900, 1910, 1920, 1930, 1940, 1950,
] + list(range(1951, 2026))

ALL_HYDE_AD_YEARS = (
  list(range(0, 1701, 100))
  + list(range(1710, 1951, 10))
  + list(range(1951, 2026))
)  # Exactly 118 overlapping AD HYDE years

PALETTE = [
  [184, 105, 81], [86, 134, 168], [118, 158, 98], [198, 152, 74],
  [146, 106, 162], [78, 156, 148], [204, 118, 132], [134, 146, 86],
  [172, 128, 104], [96, 118, 174], [164, 154, 88], [192, 102, 106],
  [88, 148, 118], [156, 116, 138], [122, 164, 184], [186, 142, 112],
]


def norm_str (arg0_text):
  """ASCII-folds and normalises a string for deterministic matching."""
  s = unicodedata.normalize("NFKD", str(arg0_text or "")).encode("ascii", "ignore").decode("ascii").lower()
  return re.sub(r"[^a-z0-9]+", " ", s).strip()


def interp_dict (arg0_series, arg1_year):
  """Log-linearly interpolates a year -> population dictionary cleanly."""
  if not arg0_series:
    return None
  pts = sorted((int(k), float(v)) for k, v in arg0_series.items() if v is not None and float(v) >= 0.0)
  if not pts:
    return None
  yr = float(arg1_year)
  if yr <= pts[0][0]:
    return float(pts[0][1])
  if yr >= pts[-1][0]:
    return float(pts[-1][1])
  for i in range(len(pts) - 1):
    y0, v0 = pts[i]
    y1, v1 = pts[i + 1]
    if y0 <= yr <= y1:
      t = (yr - y0) / max(1.0, float(y1 - y0))
      if v0 > 0.0 and v1 > 0.0:
        return math.exp((1.0 - t) * math.log(v0) + t * math.log(v1))
      return v0 * (1.0 - t) + v1 * t
  return float(pts[-1][1])


def safe_geom (arg0_geom):
  """Applies make_valid(), strips non-polygonal GeometryCollection members and heals seams."""
  if arg0_geom is None or arg0_geom.is_empty:
    return None
  g = arg0_geom
  try:
    if not g.is_valid:
      g = make_valid(g)
    if isinstance(g, GeometryCollection):
      polys = [p for p in g.geoms if isinstance(p, (Polygon, MultiPolygon)) and not p.is_empty]
      if not polys:
        return None
      g = unary_union(polys)
    if not isinstance(g, (Polygon, MultiPolygon)) or g.is_empty:
      return None
    if not g.is_valid:
      g = g.buffer(0)
    if isinstance(g, GeometryCollection):
      polys = [p for p in g.geoms if isinstance(p, (Polygon, MultiPolygon)) and not p.is_empty]
      if not polys:
        return None
      g = unary_union(polys)
    if not isinstance(g, (Polygon, MultiPolygon)) or g.is_empty:
      return None
    return g
  except Exception:
    try:
      g2 = arg0_geom.buffer(0)
      if isinstance(g2, (Polygon, MultiPolygon)) and not g2.is_empty:
        return g2
    except Exception:
      pass
    return None


def iter_polys (arg0_geom):
  """Yields every non-empty Polygon member of a Polygon/MultiPolygon/GeometryCollection."""
  if arg0_geom is None or arg0_geom.is_empty:
    return
  if isinstance(arg0_geom, Polygon):
    yield arg0_geom
  elif isinstance(arg0_geom, MultiPolygon):
    for p in arg0_geom.geoms:
      if not p.is_empty:
        yield p
  elif isinstance(arg0_geom, GeometryCollection):
    for p in arg0_geom.geoms:
      yield from iter_polys(p)


def u_geoms (arg0_list):
  """Safely computes the unary union of a list of geometries."""
  valid = []
  for g in arg0_list:
    sg = safe_geom(g)
    if sg is not None:
      valid.append(sg)
  if not valid:
    return None
  try:
    return safe_geom(unary_union(valid))
  except Exception:
    return safe_geom(unary_union([v.buffer(0) for v in valid]))


def clip_geom (arg0_geom, arg1_clip):
  """Safely clips a geometry to a reference mask geometry."""
  g = safe_geom(arg0_geom)
  c = safe_geom(arg1_clip)
  if g is None or c is None:
    return None
  try:
    return safe_geom(g.intersection(c))
  except Exception:
    try:
      return safe_geom(g.buffer(0).intersection(c.buffer(0)))
    except Exception:
      return None


def diff_geom (arg0_a, arg1_b):
  """Safely subtracts geometry B from geometry A."""
  a = safe_geom(arg0_a)
  if a is None:
    return None
  b = safe_geom(arg1_b)
  if b is None:
    return a
  try:
    return safe_geom(a.difference(b))
  except Exception:
    try:
      return safe_geom(a.buffer(0).difference(b.buffer(0)))
    except Exception:
      return a


def absorb_micro_slivers (arg0_zones, arg1_min_area_deg2=0.0022):
  """Absorbs small interior overlay slivers (< ~25 km^2) into their longest-shared-edge neighbour.
  Standalone micro-islands (zero shared boundary with other zones) are ALWAYS preserved untouched."""
  zones = [dict(z) for z in arg0_zones]
  min_a = float(arg1_min_area_deg2)

  for _ in range(2):
    reassignments = defaultdict(list)
    new_parts = defaultdict(list)
    changed = False
    z_bounds = [(z["geom"].bounds if z.get("geom") is not None else None) for z in zones]

    for i, z in enumerate(zones):
      g = safe_geom(z.get("geom"))
      if g is None:
        continue
      parts = list(iter_polys(g))
      if len(parts) == 1:
        new_parts[i].append(parts[0])
        continue
      for p in parts:
        if p.area >= min_a:
          new_parts[i].append(p)
          continue
        if p.area < 1e-6:
          continue
        pb = p.bounds
        p_buf = p.buffer(0.002)
        best_j = -1
        best_len = 0.0
        for j, oz in enumerate(zones):
          if j == i:
            continue
          ob = z_bounds[j]
          if ob is None or pb[2] + 0.01 < ob[0] or pb[0] - 0.01 > ob[2] or pb[3] + 0.01 < ob[1] or pb[1] - 0.01 > ob[3]:
            continue
          og = oz.get("geom")
          if og is None or not p_buf.intersects(og):
            continue
          try:
            shared = p_buf.intersection(og.boundary).length
          except Exception:
            shared = 0.0
          if shared > best_len:
            best_len = shared
            best_j = j
        if best_j >= 0 and best_len > 0.002:
          reassignments[best_j].append(p)
          changed = True
        else:
          new_parts[i].append(p)

    if not changed:
      break
    for i in range(len(zones)):
      merged = new_parts[i] + reassignments[i]
      zones[i]["geom"] = u_geoms(merged) if merged else zones[i].get("geom")

  return zones


def parse_gpkg_wkb (arg0_blob):
  """Parses a GeoPackage StandardGeoPackageBinary geometry blob into a Shapely geometry."""
  if not arg0_blob or len(arg0_blob) < 10 or arg0_blob[0:2] != b"GP":
    return None
  flags = arg0_blob[3]
  env_ind = (flags >> 1) & 0x07
  env_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
  offset = 8 + env_sizes.get(env_ind, 0)
  if offset >= len(arg0_blob):
    return None
  try:
    return safe_geom(wkb.loads(arg0_blob[offset:]))
  except Exception:
    return None


def load_hgis_indias_lcg (arg0_jaguar_union):
  """Loads HGIS de las Indias LCG geometries (`the_geom.gpkg`) and temporal lookup (`Niveles.tab`)."""
  gpkg_p = os.path.join(HGIS_RAW, "hgis_indias", "the_geom.gpkg")
  con = sqlite3.connect(gpkg_p)
  lcg_geoms = {}
  jag_bbox = box(-120.0, 6.0, -58.0, 34.0)
  for row in con.execute('SELECT ILCG_ID, Region, Province_1, geom FROM "LCG"'):
    pid = str(row[0] or "").strip()
    reg = str(row[1] or "").strip()
    if not pid:
      continue
    g = parse_gpkg_wkb(row[3])
    if g is None or not g.intersects(jag_bbox):
      continue
    gc = clip_geom(g, arg0_jaguar_union)
    if gc is not None and gc.area > 1e-6:
      gc_s = safe_geom(gc.simplify(0.002, preserve_topology=True)) or gc
      lcg_geoms[pid] = {"geom": gc_s, "region": reg, "province": str(row[2] or "").strip()}
  con.close()

  niveles_rows = []
  niv_p = os.path.join(HGIS_RAW, "hgis_indias", "Niveles.tab")
  with open(niv_p, encoding="utf-8-sig", errors="replace") as fh:
    for r in csv.DictReader(fh):
      pid = (r.get("Polygon_ID") or "").strip()
      if pid not in lcg_geoms:
        continue
      try:
        s = int(r.get("START") or 0)
        e = int(r.get("END") or 0)
      except Exception:
        continue
      niveles_rows.append({
        "pid": pid,
        "start": s,
        "end": e,
        "nivel": (r.get("Nivel") or "").strip(),
        "entidad": (r.get("Entidad_ID") or "").strip(),
        "nombre": (r.get("Nombre") or "").strip(),
        "tipo": (r.get("Tipo") or "").strip(),
      })

  return lcg_geoms, niveles_rows


def dissolve_hgis_indias_by_year (arg0_lcg, arg1_niveles, arg2_year, arg3_nivel="Provincia"):
  """Dissolves HGIS de las Indias LCG polygons into named entities for a specific year & level."""
  yr = int(arg2_year)
  buckets = defaultdict(list)
  meta = {}
  for r in arg1_niveles:
    if r["nivel"] == arg3_nivel and r["start"] <= yr <= r["end"]:
      eid = r["entidad"]
      buckets[eid].append(arg0_lcg[r["pid"]]["geom"])
      if eid not in meta:
        meta[eid] = {"nombre": r["nombre"], "tipo": r["tipo"]}
  out = {}
  for eid, glist in buckets.items():
    ug = u_geoms(glist)
    if ug is not None:
      out[eid] = {"geom": ug, "nombre": meta[eid]["nombre"], "tipo": meta[eid]["tipo"]}
  return out


def load_hydrobasins_jaguar (arg0_jaguar_union):
  """Loads Pfafstetter Level 6 HydroBASINS (NA + SA) strictly clipped to JAGUAR land union."""
  basins = []
  jag_bbox = (-119.5, 6.0, -58.0, 34.0)
  for zn in ("hybas_na_lev06_v1c.zip", "hybas_sa_lev06_v1c.zip"):
    zp = os.path.join(JAG_GIS, zn)
    with zipfile.ZipFile(zp) as zf:
      sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
      sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
      for sr in sf.iterShapeRecords():
        bb = sr.shape.bbox
        if bb[2] < jag_bbox[0] or bb[0] > jag_bbox[2] or bb[3] < jag_bbox[1] or bb[1] > jag_bbox[3]:
          continue
        g = clip_geom(shape(sr.shape.__geo_interface__), arg0_jaguar_union)
        if g is None or g.area < 0.0004:
          continue
        rp = g.representative_point()
        basins.append({
          "g": g,
          "lat": float(rp.y),
          "lon": float(rp.x),
          "pfaf": str(sr.record["PFAF_ID"]),
          "main_bas": int(sr.record["MAIN_BAS"]),
          "hybas_id": int(sr.record["HYBAS_ID"]),
        })
  return basins


def group_basins (arg0_basins, arg1_classifier, arg2_clip_geom=None):
  """Groups natural HydroBASINS L6 watersheds organically without synthetic straight-line cuts."""
  buckets = defaultdict(list)
  for b in arg0_basins:
    g = b["g"]
    if arg2_clip_geom is not None:
      g = clip_geom(g, arg2_clip_geom)
      if g is None or g.area < 0.0008:
        continue
      rp = g.representative_point()
      lat, lon = float(rp.y), float(rp.x)
    else:
      lat, lon = b["lat"], b["lon"]
    zid = arg1_classifier(lat, lon, b["pfaf"], b["main_bas"])
    if zid:
      buckets[zid].append(g)
  return {k: u_geoms(gs) for k, gs in buckets.items()}


def cv2_rasterise_zones (arg0_domain_mask, arg1_zones_spec, arg2_land_area=None, arg3_full_domain=False, arg4_snap_coastal_px=2):
  """Scanline-free OpenCV `cv2.fillPoly(..., shift=4)` rasteriser with local hole subtraction
  and micro-island pixel preservation."""
  id_grid = np.zeros((GRID_H, GRID_W), dtype=np.int32)
  scale_x = GRID_W / 360.0
  scale_y = GRID_H / 180.0
  sm = 16.0  # shift=4 -> 1/16th pixel sub-pixel precision

  for z_idx, z in enumerate(arg1_zones_spec, start=1):
    g = safe_geom(z.get("geom"))
    if g is None:
      continue
    for poly in iter_polys(g):
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

      # Guarantee micro-islands (Bermuda, Saba, St Barts, Anguilla, Montserrat, etc.) never drop to 0 px!
      if poly.area < 0.03:
        rp = poly.representative_point()
        col = min(GRID_W - 1, max(0, int((rp.x + 180.0) * scale_x)))
        row = min(GRID_H - 1, max(0, int((90.0 - rp.y) * scale_y)))
        if arg0_domain_mask[row, col] and id_grid[row, col] == 0:
          id_grid[row, col] = z_idx
        else:
          # Search immediate 3x3 neighbourhood in domain_mask
          r_lo, r_hi = max(0, row - 1), min(GRID_H, row + 2)
          c_lo, c_hi = max(0, col - 1), min(GRID_W, col + 2)
          dm_sub = arg0_domain_mask[r_lo:r_hi, c_lo:c_hi] & (id_grid[r_lo:r_hi, c_lo:c_hi] == 0)
          if dm_sub.any():
            ys, xs = np.where(dm_sub)
            id_grid[r_lo + ys[0], c_lo + xs[0]] = z_idx

  # Clip strictly to JAGUAR domain mask
  id_grid[~arg0_domain_mask] = 0

  # Fill coastal vector/raster alignment slivers cleanly without bridging oceans
  missing = arg0_domain_mask & (id_grid == 0)
  if missing.any() and (id_grid > 0).any():
    if arg3_full_domain:
      _, idx = distance_transform_edt(id_grid == 0, return_indices=True)
      id_grid[missing] = id_grid[idx[0][missing], idx[1][missing]]
    elif arg4_snap_coastal_px > 0:
      dist, idx = distance_transform_edt(id_grid == 0, return_indices=True)
      fill_m = missing & (dist <= float(arg4_snap_coastal_px))
      if fill_m.any():
        id_grid[fill_m] = id_grid[idx[0][fill_m], idx[1][fill_m]]

  # Belt-and-suspenders scanline hole guard
  mid = id_grid[1:-1, :]
  above = id_grid[:-2, :]
  below = id_grid[2:, :]
  scanline_holes = (mid == 0) & arg0_domain_mask[1:-1, :] & (above > 0) & (above == below)
  if scanline_holes.any():
    id_grid[1:-1, :][scanline_holes] = above[scanline_holes]

  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  px_counts = {}
  area_km2 = {}
  for z_idx, z in enumerate(arg1_zones_spec, start=1):
    m = (id_grid == z_idx)
    cnt = int(m.sum())
    px_counts[z["id"]] = cnt
    if arg2_land_area is not None:
      area_km2[z["id"]] = round(float(arg2_land_area[m].sum()), 1)
    else:
      area_km2[z["id"]] = round(float(cnt) * 76.0, 1)
    if cnt > 0:
      rgb = z["rgb"]
      rgba[m, 0] = rgb[0]
      rgba[m, 1] = rgb[1]
      rgba[m, 2] = rgb[2]
      rgba[m, 3] = 255

  return rgba, id_grid, px_counts, area_km2


def fill_small_holes (arg0_geom, arg1_max_hole_area=0.35):
  """Fills small interior holes (< `arg1_max_hole_area` deg^2) inside polygons so tiny
  unassigned colonial cabeceras/lakebed holes do not let lower z-index fallback layers poke through."""
  g = safe_geom(arg0_geom)
  if g is None:
    return None
  max_a = float(arg1_max_hole_area)
  cleaned = []
  for p in iter_polys(g):
    kept_holes = [ring for ring in p.interiors if Polygon(ring).area >= max_a]
    cleaned.append(Polygon(p.exterior, kept_holes))
  return u_geoms(cleaned)


def build_organic_mosquitia_geom (arg0_basins, arg1_f90, arg2_hn_ni_union):
  """Builds an organic Taguzgalpa-Tologalpa-Mosquitia polygon from HGIS de las Indias
  (`FRGUCYTA` + `FRGUNITO`) and HydroBASINS L6 Mosquitia watersheds (Rio Sico-Tinto,
  Rio Patuca, Rio Coco/Wawa, Rio Grande/Escondido), with ZERO straight-line meridian cuts."""
  mosq_hybas = {7060053850, 7060054070, 7060054310}
  parts = [b["g"] for b in arg0_basins if b.get("hybas_id") in mosq_hybas]
  for k in ("FRGUCYTA", "FRGUNITO"):
    if k in arg1_f90 and arg1_f90[k].get("geom") is not None:
      parts.append(arg1_f90[k]["geom"])
  raw = u_geoms(parts)
  if raw is None:
    return None
  clipped = clip_geom(raw, arg2_hn_ni_union)
  if clipped is None:
    return None
  # Keep only main contiguous Mosquitia landmass + immediate coastal cays (>= 0.01 deg^2)
  kept = [p for p in iter_polys(clipped) if p.area >= 0.01 or p.representative_point().x > -84.0]
  return u_geoms(kept) if kept else clipped


def clean_raster_confetti (arg0_id_grid, arg1_domain_mask, arg2_min_comp_px=10):
  """Absorbs small interior speckle/sliver connected components (< `arg2_min_comp_px`) into
  their longest-shared-edge neighbouring painted unit. Standalone ocean micro-islands (zero
  adjacent differing painted pixels) are ALWAYS preserved untouched."""
  min_px = int(arg2_min_comp_px)
  if min_px <= 1:
    return arg0_id_grid
  grid = arg0_id_grid.copy()
  kernel = np.ones((3, 3), dtype=np.uint8)
  # Restrict scan strictly to active JAGUAR bounding box for speed (< 80 ms per regime)
  ys_all, xs_all = np.where(arg1_domain_mask)
  if len(ys_all) == 0:
    return grid
  r0 = max(0, int(ys_all.min()) - 1)
  r1 = min(grid.shape[0], int(ys_all.max()) + 2)
  c0 = max(0, int(xs_all.min()) - 1)
  c1 = min(grid.shape[1], int(xs_all.max()) + 2)
  sub = grid[r0:r1, c0:c1]

  for _ in range(2):
    changed = False
    uniq_ids = np.unique(sub)
    for uid in uniq_ids:
      if uid <= 0:
        continue
      bin_m = (sub == uid).astype(np.uint8)
      n_lab, labels, stats, _ = cv2.connectedComponentsWithStats(bin_m, connectivity=8)
      for lab in range(1, n_lab):
        area = int(stats[lab, cv2.CC_STAT_AREA])
        if area >= min_px:
          continue
        lx = int(stats[lab, cv2.CC_STAT_LEFT])
        ly = int(stats[lab, cv2.CC_STAT_TOP])
        lw = int(stats[lab, cv2.CC_STAT_WIDTH])
        lh = int(stats[lab, cv2.CC_STAT_HEIGHT])
        y_a = max(0, ly - 1)
        y_b = min(sub.shape[0], ly + lh + 1)
        x_a = max(0, lx - 1)
        x_b = min(sub.shape[1], lx + lw + 1)
        patch_lab = (labels[y_a:y_b, x_a:x_b] == lab).astype(np.uint8)
        dil = cv2.dilate(patch_lab, kernel, iterations=1)
        ring = (dil > 0) & (patch_lab == 0)
        nbrs = sub[y_a:y_b, x_a:x_b][ring]
        nbrs = nbrs[(nbrs > 0) & (nbrs != uid)]
        if len(nbrs) == 0:
          # Genuine standalone ocean micro-island (e.g. Bermuda, Saba, St Barts) — NEVER erase!
          continue
        vals, cnts = np.unique(nbrs, return_counts=True)
        best_nbr = int(vals[int(np.argmax(cnts))])
        sub[y_a:y_b, x_a:x_b][patch_lab > 0] = best_nbr
        changed = True
    if not changed:
      break
  grid[r0:r1, c0:c1] = sub
  return grid


def cv2_rasterise_subadmin_units (arg0_units, arg1_domain_mask, arg2_land_area, arg3_snap_coastal_px=3, arg4_clean_confetti_px=0):
  """Zero-scanline, hole-aware OpenCV subadmin rasteriser with strict z-index ordering."""
  id_grid = np.zeros((GRID_H, GRID_W), dtype=np.int32)
  scale_x = GRID_W / 360.0
  scale_y = GRID_H / 180.0
  sm = 16.0

  # Strict z-index: priority ASC (z=1 defacto fallback first -> z=4 academic HGIS on top!), area DESC
  ordered = sorted(arg0_units, key=lambda u: (float(u.get("priority", 1.0)), -float(u["geom"].area)))

  for u in ordered:
    uid = int(u["id"])
    for poly in iter_polys(u["geom"]):
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
      sub[lm > 0] = uid

      # Preserve micro-islands (e.g. Bermuda, Saba, St Barts, Anguilla, Montserrat)
      if poly.area < 0.03:
        rp = poly.representative_point()
        col = min(GRID_W - 1, max(0, int((rp.x + 180.0) * scale_x)))
        row = min(GRID_H - 1, max(0, int((90.0 - rp.y) * scale_y)))
        if arg1_domain_mask[row, col]:
          id_grid[row, col] = uid

  max_id = max((int(u["id"]) for u in arg0_units), default=0)
  full_area = np.bincount(id_grid.ravel(), weights=arg2_land_area.ravel().astype(np.float64), minlength=max_id + 1)

  id_grid[~arg1_domain_mask] = 0

  if arg3_snap_coastal_px > 0:
    missing = arg1_domain_mask & (id_grid == 0)
    if missing.any() and (id_grid > 0).any():
      dist, idx = distance_transform_edt(id_grid == 0, return_indices=True)
      fill_m = missing & (dist <= float(arg3_snap_coastal_px))
      if fill_m.any():
        id_grid[fill_m] = id_grid[idx[0][fill_m], idx[1][fill_m]]

  mid = id_grid[1:-1, :]
  above = id_grid[:-2, :]
  below = id_grid[2:, :]
  scanline_holes = (mid == 0) & arg1_domain_mask[1:-1, :] & (above > 0) & (above == below)
  if scanline_holes.any():
    id_grid[1:-1, :][scanline_holes] = above[scanline_holes]

  if arg4_clean_confetti_px and int(arg4_clean_confetti_px) > 1:
    id_grid = clean_raster_confetti(id_grid, arg1_domain_mask, int(arg4_clean_confetti_px))

  flat_ids = id_grid[arg1_domain_mask]
  flat_la = arg2_land_area[arg1_domain_mask].astype(np.float64)
  px_cnt = np.bincount(flat_ids, minlength=max_id + 1)
  area_sum = np.bincount(flat_ids, weights=flat_la, minlength=max_id + 1)

  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  pos = id_grid > 0
  rgba[pos, 0] = ((id_grid[pos] >> 8) & 0xFF).astype(np.uint8)
  rgba[pos, 1] = (id_grid[pos] & 0xFF).astype(np.uint8)
  rgba[pos, 3] = 255
  return rgba, id_grid, px_cnt, area_sum, full_area


class LambertAzimuthalEqualArea:
  """Spherical Lambert Azimuthal Equal-Area projection returning kilometres."""

  def __init__ (self, arg0_lon0=-88.0, arg1_lat0=19.5):
    self.lon0 = math.radians(float(arg0_lon0))
    self.lat0 = math.radians(float(arg1_lat0))
    self.r_km = 6371.0088
    self.sin_lat0 = math.sin(self.lat0)
    self.cos_lat0 = math.cos(self.lat0)

  def fwd_xy (self, arg0_lon, arg1_lat):
    lon_r = np.radians(np.asarray(arg0_lon, dtype=np.float64))
    lat_r = np.radians(np.clip(np.asarray(arg1_lat, dtype=np.float64), -89.0, 89.0))
    dlon = lon_r - self.lon0
    sin_lat = np.sin(lat_r)
    cos_lat = np.cos(lat_r)
    denom = np.maximum(1e-9, 1.0 + self.sin_lat0 * sin_lat + self.cos_lat0 * cos_lat * np.cos(dlon))
    k = np.sqrt(2.0 / denom)
    x = self.r_km * k * cos_lat * np.sin(dlon)
    y = self.r_km * k * (self.cos_lat0 * sin_lat - self.sin_lat0 * cos_lat * np.cos(dlon))
    return x, y


PROJ_JAGUAR = LambertAzimuthalEqualArea(-88.0, 19.5)
PROJ_BERMUDA = LambertAzimuthalEqualArea(-64.77, 32.32)


def prepare_and_project (arg0_geom, arg1_proj, arg2_seg_deg=0.30, arg3_clip_box=None):
  """Clips, segmentises and projects a Shapely geometry cleanly into LAEA kilometres."""
  if arg0_geom is None or arg0_geom.is_empty:
    return Polygon()
  g = arg0_geom
  if arg3_clip_box is not None:
    try:
      g = g.intersection(arg3_clip_box)
    except Exception:
      g = g.buffer(0).intersection(arg3_clip_box)
  if g.is_empty:
    return Polygon()
  try:
    g = shapely.segmentize(g, float(arg2_seg_deg))
  except Exception:
    pass
  try:
    return shp_transform(lambda x, y, z=None: arg1_proj.fwd_xy(x, y), g)
  except Exception:
    return Polygon()


def geom_to_patches (arg0_proj_geom):
  """Extracts Matplotlib Polygon patches from a projected Shapely geometry."""
  patches = []
  if arg0_proj_geom is None or arg0_proj_geom.is_empty:
    return patches
  gt = arg0_proj_geom.geom_type
  if gt == "Polygon":
    coords = np.asarray(arg0_proj_geom.exterior.coords)
    if len(coords) >= 3:
      patches.append(MplPolygon(coords[:, :2], closed=True))
  elif gt in ("MultiPolygon", "GeometryCollection"):
    for sub in arg0_proj_geom.geoms:
      patches.extend(geom_to_patches(sub))
  return patches


def draw_proj_lines (arg0_ax, arg1_proj_geom, **kwargs):
  """Plots projected LineString or MultiLineString features."""
  if arg1_proj_geom is None or arg1_proj_geom.is_empty:
    return
  gt = arg1_proj_geom.geom_type
  if gt == "LineString":
    xs, ys = arg1_proj_geom.xy
    arg0_ax.plot(xs, ys, **kwargs)
  elif gt in ("MultiLineString", "GeometryCollection"):
    for sub in arg1_proj_geom.geoms:
      draw_proj_lines(arg0_ax, sub, **kwargs)


def load_jaguar_basemap_cache (arg0_proj, arg1_clip_bbox=(-122.0, 4.0, -56.0, 36.0), arg2_show_modern_borders=False):
  """Loads Natural Earth 50m land polygons & rivers for JAGUAR.
  When `arg2_show_modern_borders=False` (Ch 1-10), dissolves countries into pure landmasses
  so ZERO modern 2025 country borders appear beneath pre-Columbian or colonial masks."""
  cbox = box(*arg1_clip_bbox)
  ctry_p = os.path.join(PARENT_GIS_CACHE, "ne_50m_admin_0_countries.geojson")
  riv_p = os.path.join(PARENT_GIS_CACHE, "ne_50m_rivers_lake_centerlines.geojson")
  ctry_gj = json.load(open(ctry_p, encoding="utf-8"))
  riv_gj = json.load(open(riv_p, encoding="utf-8"))

  land_patches = []
  raw_land = []
  for feat in ctry_gj.get("features", []):
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    g = safe_geom(shape(geom_raw))
    if g is None or not g.intersects(cbox):
      continue
    if arg2_show_modern_borders:
      pg = prepare_and_project(g, arg0_proj, 0.30, cbox)
      land_patches.extend(geom_to_patches(pg))
    else:
      gc = clip_geom(g, cbox)
      if gc is not None:
        raw_land.append(gc)

  if not arg2_show_modern_borders and raw_land:
    dissolved = u_geoms(raw_land)
    pg = prepare_and_project(dissolved, arg0_proj, 0.30, None)
    land_patches.extend(geom_to_patches(pg))

  river_geoms = []
  for feat in riv_gj.get("features", []):
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    g = shape(geom_raw)
    if not g.intersects(cbox):
      continue
    pg = prepare_and_project(g, arg0_proj, 0.25, cbox)
    if not pg.is_empty:
      river_geoms.append(pg)

  return land_patches, river_geoms


def draw_jaguar_basemap (arg0_ax, arg1_land_patches, arg2_river_geoms):
  """Draws ocean backdrop, parchment land polygons and subtle blue rivers."""
  arg0_ax.set_facecolor("#d9ebf7")
  if arg1_land_patches:
    arg0_ax.add_collection(
      PatchCollection(
        [MplPolygon(p.get_xy(), closed=True) for p in arg1_land_patches],
        facecolor="#f2efe9",
        edgecolor="#b8b2a6",
        linewidths=0.35,
        zorder=1.0,
      )
    )
  for rg in arg2_river_geoms:
    draw_proj_lines(arg0_ax, rg, color="#2b6cb0", linewidth=0.38, alpha=0.45, zorder=4.0)


def draw_jaguar_graticule (arg0_ax, arg1_proj, arg2_xlim, arg3_ylim):
  """Draws subtle LAEA graticule lines inside panel bounds."""
  lon_grid = np.linspace(-122.0, -56.0, 180)
  lat_grid = np.linspace(4.0, 36.0, 140)
  bview = box(arg2_xlim[0], arg3_ylim[0], arg2_xlim[1], arg3_ylim[1])
  for lat_v in (10, 15, 20, 25, 30):
    px, py = arg1_proj.fwd_xy(lon_grid, np.full_like(lon_grid, float(lat_v)))
    ls = LineString(np.column_stack([px, py])).intersection(bview)
    if not ls.is_empty:
      draw_proj_lines(arg0_ax, ls, linestyle="--", linewidth=0.32, color="#64748b", alpha=0.34, zorder=4.2)
  for lon_v in (-115, -105, -95, -85, -75, -65):
    px, py = arg1_proj.fwd_xy(np.full_like(lat_grid, float(lon_v)), lat_grid)
    ls = LineString(np.column_stack([px, py])).intersection(bview)
    if not ls.is_empty:
      draw_proj_lines(arg0_ax, ls, linestyle="--", linewidth=0.32, color="#64748b", alpha=0.34, zorder=4.2)


def render_jaguar_mask_qa_png (arg0_ch_meta, arg1_zones_spec, arg2_basemap_hist, arg3_basemap_mod, arg4_bermuda_geom=None):
  """Renders a crisp Lambert Azimuthal Equal-Area optical QA crop PNG into `tests/mask_crops/`.
  Adds a magnified Bermuda inset box whenever Bermuda falls in the chapter (Ch 10, Ch 14)."""
  os.makedirs(TESTS_MASK_CROPS, exist_ok=True)
  is_modern = (int(arg0_ch_meta["index"]) >= 11)
  land_p, riv_g = arg3_basemap_mod if is_modern else arg2_basemap_hist

  plt.rcdefaults()
  apply_viscount_style()
  fig, ax = plt.subplots(figsize=(10.5, 7.4), dpi=135)
  draw_jaguar_basemap(ax, land_p, riv_g)

  # Exclude distant Bermuda from main auto-zoom bbox so Caribbean/Mainland fills frame cleanly
  main_clip = box(-120.0, 6.0, -58.0, 33.5)
  carib_no_bmu = box(-120.0, 6.0, -58.0, 28.5)
  has_bermuda = False
  bermuda_rgb = None
  bermuda_zone_geom = None
  all_xs, all_ys = [], []
  handles = []

  for z in arg1_zones_spec:
    g = safe_geom(z.get("geom"))
    if g is None:
      continue
    rgb_f = [c / 255.0 for c in z["rgb"]]
    handles.append(Patch(facecolor=rgb_f, edgecolor="#222228", label=z["name"]))

    # Check if this zone includes Bermuda (~32.3N, -64.8W)
    bmu_box = box(-65.2, 31.9, -64.3, 32.7)
    if g.intersects(bmu_box):
      has_bermuda = True
      bermuda_rgb = rgb_f
      bermuda_zone_geom = clip_geom(g, bmu_box)

    g_plot = clip_geom(g, carib_no_bmu if (arg0_ch_meta["index"] in (10, 14) and g.intersects(bmu_box)) else main_clip)
    if g_plot is None or g_plot.is_empty:
      continue
    pg = prepare_and_project(g_plot, PROJ_JAGUAR, 0.22, None)
    ps = geom_to_patches(pg)
    if not ps:
      continue
    ax.add_collection(PatchCollection(ps, facecolor=rgb_f, edgecolor="#222228", linewidths=0.72, alpha=0.86, zorder=2.5))
    b = pg.bounds
    all_xs.extend([b[0], b[2]])
    all_ys.extend([b[1], b[3]])

  if all_xs and all_ys:
    span_x = max(250.0, max(all_xs) - min(all_xs))
    span_y = max(250.0, max(all_ys) - min(all_ys))
    pad_x = max(110.0, span_x * 0.08)
    pad_y = max(110.0, span_y * 0.08)
    xlim = (min(all_xs) - pad_x, max(all_xs) + pad_x)
    ylim = (min(all_ys) - pad_y, max(all_ys) + pad_y)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    draw_jaguar_graticule(ax, PROJ_JAGUAR, xlim, ylim)

  ax.set_aspect("equal", adjustable="box")
  ax.set_xticks([])
  ax.set_yticks([])

  # Render magnified Bermuda inset when Bermuda is included in this chapter!
  if has_bermuda and bermuda_zone_geom is not None:
    ins = ax.inset_axes([0.78, 0.72, 0.20, 0.24])
    ins.set_facecolor("#d9ebf7")
    pg_bmu = prepare_and_project(bermuda_zone_geom, PROJ_BERMUDA, 0.02, None)
    ps_bmu = geom_to_patches(pg_bmu)
    if ps_bmu:
      ins.add_collection(PatchCollection(ps_bmu, facecolor=bermuda_rgb, edgecolor="#222228", linewidths=0.85, alpha=0.92, zorder=3.0))
      bx0, by0, bx1, by1 = pg_bmu.bounds
      bp = max(6.0, max(bx1 - bx0, by1 - by0) * 0.35)
      ins.set_xlim(bx0 - bp, bx1 + bp)
      ins.set_ylim(by0 - bp, by1 + bp)
    ins.set_aspect("equal", adjustable="box")
    ins.set_xticks([])
    ins.set_yticks([])
    ins.set_title("Bermuda (32,3°N, 64,8°W)", fontsize=6.6, fontweight="bold", pad=2)
    for sp in ins.spines.values():
      sp.set_edgecolor("#1e293b")
      sp.set_linewidth(0.85)

  d0, d1 = arg0_ch_meta["domain"]
  mode_lbl = "Regime III Modern" if is_modern else "Pure Land Basemap (Zero Modern Borders)"
  ax.set_title(
    f"CH {arg0_ch_meta['index']:02d}: {arg0_ch_meta['title']} ({d0}..{d1}) — {mode_lbl}",
    fontsize=8.8, fontweight="bold", pad=6,
  )
  nrows_q = max(1, (len(handles) + 1) // 2)
  fig.subplots_adjust(left=0.03, right=0.97, top=0.92, bottom=min(0.34, 0.07 + 0.038 * nrows_q))
  fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.012), ncol=2, fontsize=6.8, frameon=True)
  out_p = os.path.join(TESTS_MASK_CROPS, f"mask_ch{arg0_ch_meta['index']:02d}_{arg0_ch_meta['stem']}.png")
  save_viscount_figure(fig, out_p, arg2_dpi=135, arg3_options={"verify_layout": True, "strict_layout": True})
  return out_p


def render_jaguar_subadmin_crop_png (arg0_id_grid, arg1_domain_mask, arg2_out_png, arg3_title=""):
  """Renders a high-contrast JAGUAR subadmin optical QA PNG (with Bermuda inset box) into `tests/subadmin_crops/`."""
  os.makedirs(os.path.dirname(arg2_out_png), exist_ok=True)
  # JAGUAR bbox: lon [-119.0, -58.5], lat [6.8, 33.2]
  c0 = int((-119.0 + 180.0) * GRID_W / 360.0)
  c1 = int((-58.5 + 180.0) * GRID_W / 360.0)
  r0 = int((90.0 - 33.2) * GRID_H / 180.0)
  r1 = int((90.0 - 6.8) * GRID_H / 180.0)

  sub_id = arg0_id_grid[r0:r1, c0:c1]
  sub_dom = arg1_domain_mask[r0:r1, c0:c1]
  h, w = sub_id.shape

  img = np.full((h, w, 3), [215, 232, 245], dtype=np.uint8)
  uncov = sub_dom & (sub_id == 0)
  img[uncov] = [255, 40, 40]  # Bright red highlights ANY missing coverage pixel

  pos = sub_id > 0
  if pos.any():
    u = sub_id[pos].astype(np.uint32)
    r = ((u * 2654435761) >> 16) % 190 + 50
    g = ((u * 2246822519) >> 16) % 190 + 50
    b = ((u * 3266489917) >> 16) % 190 + 50
    img[pos, 0] = r.astype(np.uint8)
    img[pos, 1] = g.astype(np.uint8)
    img[pos, 2] = b.astype(np.uint8)

  border = np.zeros((h, w), dtype=bool)
  border[:, 1:] |= (sub_id[:, 1:] != sub_id[:, :-1]) & ((sub_id[:, 1:] > 0) | (sub_id[:, :-1] > 0))
  border[1:, :] |= (sub_id[1:, :] != sub_id[:-1, :]) & ((sub_id[1:, :] > 0) | (sub_id[:-1, :] > 0))
  img[border] = [30, 30, 38]

  img_up = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_NEAREST)

  # Draw magnified Bermuda inset box in top-right corner
  rb = int((90.0 - 32.32) * GRID_H / 180.0) - r0
  cb = int((-64.77 + 180.0) * GRID_W / 360.0) - c0
  if 8 <= rb < h - 8 and 8 <= cb < w - 8:
    bmu_patch = img[rb - 6:rb + 7, cb - 6:cb + 7]
    bmu_big = cv2.resize(bmu_patch, (130, 130), interpolation=cv2.INTER_NEAREST)
    ih, iw = img_up.shape[:2]
    y_ins, x_ins = 52, iw - 146
    img_up[y_ins:y_ins + 130, x_ins:x_ins + 130] = bmu_big
    cv2.rectangle(img_up, (x_ins - 1, y_ins - 1), (x_ins + 130, y_ins + 130), (20, 20, 30), 2)
    cv2.putText(img_up, "Bermuda 10x", (x_ins + 4, y_ins + 146), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (20, 20, 30), 1, cv2.LINE_AA)

  if arg3_title:
    cv2.rectangle(img_up, (8, 8), (min(img_up.shape[1] - 8, 20 + len(arg3_title) * 11), 42), (255, 255, 255), -1)
    cv2.putText(img_up, arg3_title, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (15, 15, 20), 2, cv2.LINE_AA)
  cv2.imwrite(arg2_out_png, img_up[:, :, ::-1])
