"""Shared Albers Equal-Area Conic & vector cartography utilities for Project MAGNETIC.

Provides European Equal-Area projections (continental Europe, Greenland inset and
Macaronesia inset), Natural Earth land/river pre-projection, curved graticules
and clean vector PatchCollection rendering strictly compliant with `viscount_plot_utils.py`
and `audit_figure_scripts.py`.
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
from shapely.ops import transform as shp_transform

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC")
GIS_CACHE = os.path.join(MAG_DIR, "_shared", "_gis_cache")
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
)


class AlbersEqualAreaConic:
  """Spherical Albers Equal-Area Conic projection returning kilometres."""

  def __init__ (self, arg0_lon0=11.0, arg1_lat1=43.0, arg2_lat2=62.0, arg3_lat0=52.0):
    self.lon0 = math.radians(float(arg0_lon0))
    self.lat1 = math.radians(float(arg1_lat1))
    self.lat2 = math.radians(float(arg2_lat2))
    self.lat0 = math.radians(float(arg3_lat0))
    self.r_km = 6371.0088
    self.n = 0.5 * (math.sin(self.lat1) + math.sin(self.lat2))
    self.c = (math.cos(self.lat1) ** 2) + 2.0 * self.n * math.sin(self.lat1)
    self.rho0 = (self.r_km / self.n) * math.sqrt(max(1e-12, self.c - 2.0 * self.n * math.sin(self.lat0)))

  def fwd_pt (self, arg0_lon, arg1_lat):
    lon_r = math.radians(float(arg0_lon))
    lat_r = math.radians(max(-85.0, min(85.0, float(arg1_lat))))
    theta = self.n * (lon_r - self.lon0)
    rho = (self.r_km / self.n) * math.sqrt(max(1e-12, self.c - 2.0 * self.n * math.sin(lat_r)))
    return rho * math.sin(theta), self.rho0 - rho * math.cos(theta)

  def fwd_xy (self, arg0_lon, arg1_lat):
    lon_r = np.radians(np.asarray(arg0_lon, dtype=np.float64))
    lat_r = np.radians(np.clip(np.asarray(arg1_lat, dtype=np.float64), -85.0, 85.0))
    theta = self.n * (lon_r - self.lon0)
    rho = (self.r_km / self.n) * np.sqrt(np.maximum(1e-12, self.c - 2.0 * self.n * np.sin(lat_r)))
    return rho * np.sin(theta), self.rho0 - rho * np.cos(theta)

  def inv_xy (self, arg0_x, arg1_y):
    x = np.asarray(arg0_x, dtype=np.float64)
    y = np.asarray(arg1_y, dtype=np.float64)
    dy = self.rho0 - y
    rho = np.hypot(x, dy)
    theta = np.arctan2(x, dy)
    sin_lat = np.clip((self.c - ((rho * self.n / self.r_km) ** 2)) / (2.0 * self.n), -1.0, 1.0)
    lat = np.degrees(np.arcsin(sin_lat))
    lon = np.degrees(self.lon0 + theta / self.n)
    return lon, lat


PROJ_EUROPE = AlbersEqualAreaConic(11.0, 43.0, 62.0, 52.0)
PROJ_GREENLAND = AlbersEqualAreaConic(-42.0, 62.0, 78.0, 71.0)
PROJ_MACARONESIA = AlbersEqualAreaConic(-20.0, 29.0, 38.0, 33.5)


def prepare_and_project (arg0_geom, arg1_proj, arg2_seg_deg=0.35, arg3_clip_box=None):
  """Clips, segmentises and projects a Shapely geometry cleanly into projected km."""
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


def load_basemap_cache (arg0_proj, arg1_clip_bbox=(-30.0, 26.0, 48.0, 82.0), arg2_show_modern_borders=False):
  """Loads and pre-projects Natural Earth 50m land polygons and major rivers.
  For ALL historical/pre-1945 chapters (`arg2_show_modern_borders=False`), dissolves
  `ne_50m_admin_0_countries.geojson` into pure continental landmasses so ZERO modern
  2025 country borders appear underneath prehistoric, classical, mediaeval, early modern
  or imperial/interwar historical borders!"""
  cbox = box(*arg1_clip_bbox)
  ctry_p = os.path.join(PARENT_GIS_CACHE, "ne_50m_admin_0_countries.geojson")
  if not os.path.isfile(ctry_p):
    ctry_p = os.path.join(GIS_CACHE, "ne_50m_admin_0_countries.geojson")
  riv_p = os.path.join(PARENT_GIS_CACHE, "ne_50m_rivers_lake_centerlines.geojson")
  if not os.path.isfile(riv_p):
    riv_p = os.path.join(GIS_CACHE, "ne_50m_rivers_lake_centerlines.geojson")
  ctry_gj = json.load(open(ctry_p, encoding="utf-8"))
  riv_gj = json.load(open(riv_p, encoding="utf-8"))

  land_patches = []
  raw_land = []
  for feat in ctry_gj.get("features", []):
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    g = shape(geom_raw)
    if not g.intersects(cbox):
      continue
    if arg2_show_modern_borders:
      pg = prepare_and_project(g, arg0_proj, 0.35, cbox)
      land_patches.extend(geom_to_patches(pg))
    else:
      try:
        gc = g.buffer(0).intersection(cbox)
        if not gc.is_empty:
          raw_land.append(gc)
      except Exception:
        pass

  if not arg2_show_modern_borders and raw_land:
    from shapely.ops import unary_union
    dissolved = unary_union(raw_land).buffer(0)
    pg = prepare_and_project(dissolved, arg0_proj, 0.35, None)
    land_patches.extend(geom_to_patches(pg))

  river_geoms = []
  for feat in riv_gj.get("features", []):
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    g = shape(geom_raw)
    if not g.intersects(cbox):
      continue
    pg = prepare_and_project(g, arg0_proj, 0.30, cbox)
    if not pg.is_empty:
      river_geoms.append(pg)

  return land_patches, river_geoms


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


def draw_graticule (arg0_ax, arg1_proj, arg2_xlim, arg3_ylim, arg4_lats, arg5_lons, arg6_lon_span=(-32.0, 44.0), arg7_lat_span=(26.0, 82.0)):
  """Draws subtle curved Albers graticule lines inside panel bounds without clutter."""
  lon_grid = np.linspace(arg6_lon_span[0], arg6_lon_span[1], 180)
  lat_grid = np.linspace(arg7_lat_span[0], arg7_lat_span[1], 160)
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
