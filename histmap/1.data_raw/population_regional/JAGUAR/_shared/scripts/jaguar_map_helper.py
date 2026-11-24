"""Shared Lambert Azimuthal Equal-Area & vector cartography utilities for Project JAGUAR.

Provides upright Equal-Area projections for Mexico, Central America, the Caribbean
archipelago, and Bermuda insets, Natural Earth 10m physical landmass and river
pre-projection, curved graticules, and clean vector PatchCollection rendering
compliant with `viscount_plot_utils.py` and Gatekeeper D2 (`audit_figure_scripts.js`).
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
from shapely.geometry import LineString, Polygon, box, shape
from shapely.ops import transform as shp_transform, unary_union

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
JAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JAGUAR")
GIS_CACHE = os.path.join(JAG_DIR, "_shared", "_gis_cache")
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


class LambertAzimuthalEqualArea:
  """Spherical Lambert Azimuthal Equal-Area (LAEA) projection returning kilometres."""

  def __init__ (self, arg0_lon0=-88.0, arg1_lat0=19.5):
    self.lon0_deg = float(arg0_lon0)
    self.lat0_deg = float(arg1_lat0)
    self.lon0 = math.radians(self.lon0_deg)
    self.lat0 = math.radians(self.lat0_deg)
    self.sin_lat0 = math.sin(self.lat0)
    self.cos_lat0 = math.cos(self.lat0)
    self.r_km = 6371.0088

  def fwd_pt (self, arg0_lon, arg1_lat):
    lon_r = math.radians(float(arg0_lon))
    lat_r = math.radians(max(-85.0, min(85.0, float(arg1_lat))))
    dlon = lon_r - self.lon0
    sin_lat = math.sin(lat_r)
    cos_lat = math.cos(lat_r)
    cos_dlon = math.cos(dlon)
    denom = max(1e-12, 1.0 + self.sin_lat0 * sin_lat + self.cos_lat0 * cos_lat * cos_dlon)
    k = math.sqrt(2.0 / denom)
    x = self.r_km * k * cos_lat * math.sin(dlon)
    y = self.r_km * k * (self.cos_lat0 * sin_lat - self.sin_lat0 * cos_lat * cos_dlon)
    return x, y

  def fwd_xy (self, arg0_lon, arg1_lat):
    lon_r = np.radians(np.asarray(arg0_lon, dtype=np.float64))
    lat_r = np.radians(np.clip(np.asarray(arg1_lat, dtype=np.float64), -85.0, 85.0))
    dlon = lon_r - self.lon0
    sin_lat = np.sin(lat_r)
    cos_lat = np.cos(lat_r)
    cos_dlon = np.cos(dlon)
    denom = np.maximum(1e-12, 1.0 + self.sin_lat0 * sin_lat + self.cos_lat0 * cos_lat * cos_dlon)
    k = np.sqrt(2.0 / denom)
    x = self.r_km * k * cos_lat * np.sin(dlon)
    y = self.r_km * k * (self.cos_lat0 * sin_lat - self.sin_lat0 * cos_lat * cos_dlon)
    return x, y

  def inv_xy (self, arg0_x, arg1_y):
    x = np.asarray(arg0_x, dtype=np.float64)
    y = np.asarray(arg1_y, dtype=np.float64)
    rho = np.hypot(x, y)
    c = 2.0 * np.arcsin(np.clip(rho / (2.0 * self.r_km), -1.0, 1.0))
    sin_c = np.sin(c)
    cos_c = np.cos(c)
    safe_rho = np.where(rho > 1e-12, rho, 1.0)
    sin_lat = np.where(rho > 1e-12, cos_c * self.sin_lat0 + (y * sin_c * self.cos_lat0) / safe_rho, self.sin_lat0)
    lat = np.degrees(np.arcsin(np.clip(sin_lat, -1.0, 1.0)))
    lon = np.degrees(self.lon0 + np.arctan2(x * sin_c, safe_rho * self.cos_lat0 * cos_c - y * self.sin_lat0 * sin_c))
    return lon, lat


PROJ_JAGUAR = LambertAzimuthalEqualArea(-88.0, 19.5)
PROJ_BERMUDA = LambertAzimuthalEqualArea(-64.78, 32.31)
BERMUDA_CLIP_BOX = box(-65.8, 31.2, -63.8, 33.4)

# Cache raw Natural Earth GeoJSONs in memory across calls so 14 chapters render quickly
_NE_CACHE = {}


def _load_ne_geojson (arg0_kind):
  if arg0_kind in _NE_CACHE:
    return _NE_CACHE[arg0_kind]
  if arg0_kind == "countries_10m":
    cands = [
      os.path.join(PARENT_GIS_CACHE, "ne_10m_admin_0_countries.geojson"),
      os.path.join(PARENT_GIS_CACHE, "ne_50m_admin_0_countries.geojson"),
    ]
  elif arg0_kind == "countries_50m":
    cands = [
      os.path.join(PARENT_GIS_CACHE, "ne_50m_admin_0_countries.geojson"),
      os.path.join(PARENT_GIS_CACHE, "ne_10m_admin_0_countries.geojson"),
    ]
  else:
    cands = [
      os.path.join(PARENT_GIS_CACHE, "ne_10m_rivers_lake_centerlines.geojson"),
      os.path.join(PARENT_GIS_CACHE, "ne_50m_rivers_lake_centerlines.geojson"),
    ]
  for p in cands:
    if os.path.isfile(p):
      gj = json.load(open(p, encoding="utf-8"))
      # Pre-parse Shapely geometries clipped broadly to Americas/Atlantic once
      americas = box(-128.0, 0.0, -52.0, 42.0)
      geoms = []
      for feat in gj.get("features", []):
        gr = feat.get("geometry")
        if not gr:
          continue
        try:
          g = shape(gr)
          if g.intersects(americas):
            geoms.append(g)
        except Exception:
          continue
      _NE_CACHE[arg0_kind] = geoms
      return geoms
  _NE_CACHE[arg0_kind] = []
  return []


def prepare_and_project (arg0_geom, arg1_proj, arg2_seg_deg=0.25, arg3_clip_box=None):
  """Clips, segmentises, and projects a Shapely geometry cleanly into projected km."""
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


def load_basemap_cache (arg0_proj, arg1_clip_bbox=(-122.0, 4.0, -56.0, 36.0), arg2_show_modern_borders=False, arg3_high_res=True):
  """Loads and pre-projects Natural Earth land polygons and rivers.
  For all pre-modern/historical chapters (`arg2_show_modern_borders=False`), dissolves
  country polygons into pure physical landmasses so zero modern country borders appear
  underneath Pre-Columbian or Colonial territories."""
  cbox = box(*arg1_clip_bbox)
  ctry_geoms = _load_ne_geojson("countries_10m" if arg3_high_res else "countries_50m")
  riv_geoms_raw = _load_ne_geojson("rivers")

  land_patches = []
  raw_land = []
  seg_deg = 0.05 if (arg1_clip_bbox[2] - arg1_clip_bbox[0]) < 4.0 else 0.25
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

  river_geoms = []
  for g in riv_geoms_raw:
    if not g.intersects(cbox):
      continue
    pg = prepare_and_project(g, arg0_proj, 0.25, cbox)
    if not pg.is_empty:
      river_geoms.append(pg)

  return land_patches, river_geoms


def draw_basemap (arg0_ax, arg1_land_patches, arg2_river_geoms):
  """Draws ocean backdrop, warm parchment land polygons, and river network."""
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


def draw_graticule (arg0_ax, arg1_proj, arg2_xlim, arg3_ylim, arg4_lats, arg5_lons, arg6_lon_span=(-124.0, -54.0), arg7_lat_span=(3.0, 38.0)):
  """Draws curved Lambert Azimuthal Equal-Area graticule lines cleanly inside panel bounds."""
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


def draw_bermuda_inset (arg0_ax, arg1_bm_feats, arg2_rgb_map, arg3_name_map, arg4_bm_land, arg5_legend_handles, arg6_seen_leg, arg7_inset_rect=None, arg8_title_fs=6.8):
  """Draws a crisp dedicated Bermuda inset (`32,3°N, -64,8°W`) in Lambert Azimuthal Equal-Area."""
  from matplotlib.patches import Patch

  rect = arg7_inset_rect if arg7_inset_rect is not None else [0.74, 0.67, 0.24, 0.29]
  ax_bm = arg0_ax.inset_axes(rect)
  apply_viscount_style(ax_bm, {"grid": False})
  draw_basemap(ax_bm, arg4_bm_land, [])

  bm_pgs = []
  for idx_b, (rid, g) in enumerate(arg1_bm_feats):
    pg = prepare_and_project(g, PROJ_BERMUDA, 0.02)
    if pg.is_empty:
      continue
    bm_pgs.append(pg)
    hex_c = mute_rgb_hex(arg2_rgb_map.get(rid), idx_b + 3, 0.35)
    ps = geom_to_patches(pg)
    if ps:
      ax_bm.add_collection(PatchCollection(ps, facecolor=hex_c, edgecolor="#111827", linewidths=0.75, alpha=0.90, zorder=2.5))
    if rid not in arg6_seen_leg and arg5_legend_handles is not None:
      arg6_seen_leg.add(rid)
      lbl = str(arg3_name_map.get(rid, rid))
      if len(lbl) > 30:
        lbl = lbl[:29].rstrip(" ,;-") + "…"
      arg5_legend_handles.append(Patch(facecolor=hex_c, edgecolor="#334155", linewidth=0.55, label=lbl))

  # Frame Bermuda cleanly around island group (~32,3°N, -64,78°W)
  if bm_pgs:
    bx, by = pad_projected_bounds(unary_union(bm_pgs).bounds, arg1_target_aspect=1.22, arg2_pad_factor=1.65, arg3_min_span_km=36.0)
  else:
    bx, by = (-18.0, 18.0), (-15.0, 15.0)
  ax_bm.set_xlim(*bx)
  ax_bm.set_ylim(*by)
  ax_bm.set_aspect("equal", adjustable="box")
  ax_bm.set_xticks([])
  ax_bm.set_yticks([])
  ax_bm.set_title("Bermuda (32,3°N, 64,8°W)", fontsize=arg8_title_fs, pad=2)
  return ax_bm
