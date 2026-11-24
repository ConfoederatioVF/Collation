"""Shared Lambert Azimuthal Equal-Area & vector cartography utilities for Project QUIPU.

Provides upright Equal-Area Lambert Azimuthal projections across Andean South America,
the Southern Cone, Galápagos, Juan Fernández and the South Atlantic archipelagos,
Natural Earth land/river pre-projection, curved graticules and clean vector
PatchCollection rendering strictly compliant with `viscount_plot_utils.py` and
`audit_figure_scripts.js`.
"""

import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
import shapely
from shapely.geometry import LineString, MultiPolygon, Polygon, box, shape
from shapely.ops import transform as shp_transform, unary_union

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
QUIPU_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "QUIPU")
GIS_CACHE = os.path.join(QUIPU_DIR, "_shared", "_gis_cache")
SHARED_UTILS = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared")
PARENT_GIS_CACHE = os.path.join(SHARED_UTILS, "_gis_cache")
if SHARED_UTILS not in sys.path:
  sys.path.insert(0, SHARED_UTILS)

from viscount_plot_utils import (
  apply_human_colorbar_ticks,
  apply_human_log_ticks,
  apply_viscount_style,
  euro_log_formatter,
  euro_tick_formatter,
  format_euro_number,
  format_mathtext_euro,
  format_semantic_population,
  mute_rgb_hex,
  pad_projected_bounds,
  place_inbounds_callouts,
  save_viscount_figure,
  verify_panel_bounds_and_overlaps,
)


class LambertAzimuthalEqualArea:
  """Spherical Lambert Azimuthal Equal-Area projection returning kilometres (upright north-up along central meridian)."""

  def __init__ (self, arg0_lon0=-68.0, arg1_lat0=-20.0):
    self.lon0_deg = float(arg0_lon0)
    self.lat0_deg = float(arg1_lat0)
    self.lon0 = math.radians(self.lon0_deg)
    self.lat0 = math.radians(self.lat0_deg)
    self.sin_lat0 = math.sin(self.lat0)
    self.cos_lat0 = math.cos(self.lat0)
    self.r_km = 6371.0088

  def fwd_pt (self, arg0_lon, arg1_lat):
    lon_r = math.radians(float(arg0_lon))
    lat_r = math.radians(max(-89.5, min(89.5, float(arg1_lat))))
    dlon = lon_r - self.lon0
    sin_lat = math.sin(lat_r)
    cos_lat = math.cos(lat_r)
    cos_dlon = math.cos(dlon)
    denom = 1.0 + self.sin_lat0 * sin_lat + self.cos_lat0 * cos_lat * cos_dlon
    kp = math.sqrt(2.0 / max(1e-12, denom))
    x = self.r_km * kp * cos_lat * math.sin(dlon)
    y = self.r_km * kp * (self.cos_lat0 * sin_lat - self.sin_lat0 * cos_lat * cos_dlon)
    return x, y

  def fwd_xy (self, arg0_lon, arg1_lat):
    lon_r = np.radians(np.asarray(arg0_lon, dtype=np.float64))
    lat_r = np.radians(np.clip(np.asarray(arg1_lat, dtype=np.float64), -89.5, 89.5))
    dlon = lon_r - self.lon0
    sin_lat = np.sin(lat_r)
    cos_lat = np.cos(lat_r)
    cos_dlon = np.cos(dlon)
    denom = 1.0 + self.sin_lat0 * sin_lat + self.cos_lat0 * cos_lat * cos_dlon
    kp = np.sqrt(2.0 / np.maximum(1e-12, denom))
    x = self.r_km * kp * cos_lat * np.sin(dlon)
    y = self.r_km * kp * (self.cos_lat0 * sin_lat - self.sin_lat0 * cos_lat * cos_dlon)
    return x, y

  def inv_xy (self, arg0_x, arg1_y):
    x = np.asarray(arg0_x, dtype=np.float64)
    y = np.asarray(arg1_y, dtype=np.float64)
    rho = np.hypot(x, y)
    safe_rho = np.where(rho > 1e-9, rho, 1.0)
    arg_asin = np.clip(rho / (2.0 * self.r_km), 0.0, 1.0)
    c = 2.0 * np.arcsin(arg_asin)
    sin_c = np.sin(c)
    cos_c = np.cos(c)
    sin_lat = np.where(
      rho > 1e-9,
      np.clip(cos_c * self.sin_lat0 + (y * sin_c * self.cos_lat0) / safe_rho, -1.0, 1.0),
      self.sin_lat0,
    )
    lat = np.degrees(np.arcsin(sin_lat))
    lon = np.where(
      rho > 1e-9,
      np.degrees(self.lon0 + np.arctan2(x * sin_c, safe_rho * self.cos_lat0 * cos_c - y * self.sin_lat0 * sin_c)),
      self.lon0_deg,
    )
    return lon, lat


PROJ_QUIPU = LambertAzimuthalEqualArea(-69.0, -22.0)
PROJ_GALAPAGOS = LambertAzimuthalEqualArea(-90.6, -0.3)
PROJ_JUAN_FERNANDEZ = LambertAzimuthalEqualArea(-79.8, -33.65)
PROJ_FALKLANDS = LambertAzimuthalEqualArea(-59.5, -51.8)
PROJ_SOUTH_GEORGIA = LambertAzimuthalEqualArea(-36.9, -54.4)
PROJ_SOUTH_SANDWICH = LambertAzimuthalEqualArea(-26.8, -57.9)

_NE_CACHE = {}


def _load_ne_geojson (arg0_filename):
  if arg0_filename in _NE_CACHE:
    return _NE_CACHE[arg0_filename]
  p = os.path.join(PARENT_GIS_CACHE, arg0_filename)
  if not os.path.isfile(p):
    p = os.path.join(GIS_CACHE, arg0_filename)
  gj = json.load(open(p, encoding="utf-8"))
  geoms = []
  for feat in gj.get("features", []):
    geom_raw = feat.get("geometry")
    if geom_raw:
      try:
        g = shape(geom_raw)
        if not g.is_empty:
          geoms.append(g)
      except Exception:
        continue
  _NE_CACHE[arg0_filename] = geoms
  return geoms


def filter_tiny_slivers (arg0_geom, arg1_min_area_deg2=1.5e-4, arg2_simplify_deg=0.0):
  """Drops microscopic fjord slivers while preserving island archipelagos when threshold is small."""
  if arg0_geom is None or arg0_geom.is_empty:
    return Polygon()
  gt = arg0_geom.geom_type
  if gt == "Polygon":
    g = arg0_geom.simplify(arg2_simplify_deg, preserve_topology=True) if arg2_simplify_deg > 0 else arg0_geom
    return g
  if gt in ("MultiPolygon", "GeometryCollection"):
    kept = []
    for sub in arg0_geom.geoms:
      if sub.geom_type == "Polygon" and not sub.is_empty and sub.area >= arg1_min_area_deg2:
        kept.append(sub.simplify(arg2_simplify_deg, preserve_topology=True) if arg2_simplify_deg > 0 else sub)
    if not kept:
      polys = [sub for sub in arg0_geom.geoms if sub.geom_type == "Polygon" and not sub.is_empty]
      if polys:
        kept = [max(polys, key=lambda p: p.area)]
    if not kept:
      return Polygon()
    return kept[0] if len(kept) == 1 else MultiPolygon(kept)
  return arg0_geom


def prepare_and_project (arg0_geom, arg1_proj, arg2_seg_deg=0.35, arg3_clip_box=None, arg4_min_area_deg2=0.0, arg5_simplify_deg=0.0):
  """Clips, optionally filters slivers, segmentises and projects a Shapely geometry cleanly into projected km."""
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
  if arg4_min_area_deg2 > 0.0 or arg5_simplify_deg > 0.0:
    g = filter_tiny_slivers(g, arg4_min_area_deg2, arg5_simplify_deg)
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


def load_basemap_cache (arg0_proj, arg1_clip_bbox=(-96.0, -61.0, -24.0, 16.0), arg2_show_modern_borders=False, arg3_high_res=False):
  """Loads and pre-projects Natural Earth land polygons and major rivers.
  For ALL Pre-Columbian and Colonial chapters (`arg2_show_modern_borders=False`), dissolves
  `ne_50m_admin_0_countries.geojson` into pure continental landmasses so ZERO modern 2025
  national borders appear underneath historical maps!"""
  cbox = box(*arg1_clip_bbox)
  ctry_fn = "ne_10m_admin_0_countries.geojson" if arg3_high_res else "ne_50m_admin_0_countries.geojson"
  riv_fn = "ne_50m_rivers_lake_centerlines.geojson"
  ctry_geoms = _load_ne_geojson(ctry_fn)
  riv_geoms = [] if arg3_high_res else _load_ne_geojson(riv_fn)

  seg_deg = 0.12 if arg3_high_res else 0.35
  land_patches = []
  raw_land = []
  for g in ctry_geoms:
    if not g.intersects(cbox):
      continue
    if arg2_show_modern_borders:
      pg = prepare_and_project(g, arg0_proj, seg_deg, cbox)
      land_patches.extend(geom_to_patches(pg))
    else:
      try:
        gc = g.buffer(0).intersection(cbox)
        if not gc.is_empty:
          raw_land.append(gc)
      except Exception:
        pass

  if not arg2_show_modern_borders and raw_land:
    dissolved = unary_union(raw_land).buffer(0)
    pg = prepare_and_project(dissolved, arg0_proj, seg_deg, None)
    land_patches.extend(geom_to_patches(pg))

  river_proj = []
  for g in riv_geoms:
    if not g.intersects(cbox):
      continue
    pg = prepare_and_project(g, arg0_proj, 0.30, cbox)
    if not pg.is_empty:
      river_proj.append(pg)

  return land_patches, river_proj


def draw_basemap (arg0_ax, arg1_land_patches, arg2_river_geoms):
  """Draws clean ocean backdrop, parchment land polygons and subtle blue river network."""
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
    draw_proj_lines(arg0_ax, rg, color="#2b6cb0", linewidth=0.38, alpha=0.48, zorder=4.0)


def draw_graticule (arg0_ax, arg1_proj, arg2_xlim, arg3_ylim, arg4_lats, arg5_lons, arg6_lon_span=(-96.0, -24.0), arg7_lat_span=(-61.0, 16.0)):
  """Draws subtle curved Lambert Azimuthal graticule lines inside panel bounds without clutter."""
  lon_grid = np.linspace(arg6_lon_span[0], arg6_lon_span[1], 180)
  lat_grid = np.linspace(arg7_lat_span[0], arg7_lat_span[1], 180)
  x0, x1 = arg2_xlim
  y0, y1 = arg3_ylim
  bview = box(x0, y0, x1, y1)

  for lat_v in arg4_lats:
    px, py = arg1_proj.fwd_xy(lon_grid, np.full_like(lon_grid, float(lat_v)))
    ls = LineString(np.column_stack([px, py])).intersection(bview)
    if not ls.is_empty:
      draw_proj_lines(arg0_ax, ls, linestyle="--", linewidth=0.32, color="#64748b", alpha=0.34, zorder=4.2)

  for lon_v in arg5_lons:
    px, py = arg1_proj.fwd_xy(np.full_like(lat_grid, float(lon_v)), lat_grid)
    ls = LineString(np.column_stack([px, py])).intersection(bview)
    if not ls.is_empty:
      draw_proj_lines(arg0_ax, ls, linestyle="--", linewidth=0.32, color="#64748b", alpha=0.34, zorder=4.2)
