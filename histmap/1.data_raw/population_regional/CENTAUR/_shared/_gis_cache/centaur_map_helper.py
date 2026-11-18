# -*- coding: utf-8 -*-
"""Shared equal-area cartographic projection, Natural Earth basemap, historical
border overlay (.naissance snapshots), GeoPNG reprojection and label utilities
for CENTAUR-II visual verification and monograph figures.
"""

import json
import math
import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import Polygon as MplPolygon
import shapely
from shapely.geometry import box, shape
from shapely.ops import transform as shp_transform, unary_union

GIS_DIR = pathlib.Path(__file__).resolve().parent
CENTAUR_DIR = GIS_DIR.parents[1]
GLOBAL_GIS_DIR = CENTAUR_DIR.parent / "_shared" / "_gis_cache"
POLARIS_GIS_DIR = CENTAUR_DIR.parent / "POLARIS" / "_shared" / "_gis_cache"
HIST_DIR = GIS_DIR / "historical_layers"
SUBREG_DIR = CENTAUR_DIR / "_shared" / "_gis_cache" / "chapter_subregions"

SHARED_DIR = CENTAUR_DIR.parent / "_shared"
if str(SHARED_DIR) not in sys.path:
  sys.path.insert(0, str(SHARED_DIR))
import viscount_plot_utils as vpu


class AlbersEqualAreaConic:
  """Snyder Equal-Area Conic projection (kilometres) for North America & Polynesia."""

  def __init__ (self, arg0_lon_0, arg1_lat_1, arg2_lat_2, arg3_lat_0, arg4_r_km=6371.0088, arg5_wrap_hi=165.0):
    self.lon_0 = math.radians(arg0_lon_0)
    self.lat_0 = math.radians(arg3_lat_0)
    p1 = math.radians(arg1_lat_1)
    p2 = math.radians(arg2_lat_2)
    self.n = 0.5 * (math.sin(p1) + math.sin(p2))
    if abs(self.n) < 1e-6:
      self.n = 1e-6
    self.C = (math.cos(p1) ** 2) + 2.0 * self.n * math.sin(p1)
    self.R = float(arg4_r_km)
    self.wrap_hi = float(arg5_wrap_hi)
    self.rho_0 = (self.R / self.n) * math.sqrt(max(0.0, self.C - 2.0 * self.n * math.sin(self.lat_0)))

  def fwd_pt (self, arg0_lon_deg, arg1_lat_deg):
    lon_u = arg0_lon_deg - 360.0 if arg0_lon_deg > self.wrap_hi else arg0_lon_deg
    lam = math.radians(lon_u)
    phi = math.radians(max(-89.5, min(89.5, arg1_lat_deg)))
    rho = (self.R / self.n) * math.sqrt(max(0.0, self.C - 2.0 * self.n * math.sin(phi)))
    theta = self.n * (lam - self.lon_0)
    return (rho * math.sin(theta), self.rho_0 - rho * math.cos(theta))

  def fwd_xy (self, arg0_xs, arg1_ys, arg2_zs=None):
    arr_x = np.asarray(arg0_xs, dtype=float)
    arr_y = np.asarray(arg1_ys, dtype=float)
    lon_u = np.where(arr_x > self.wrap_hi, arr_x - 360.0, arr_x)
    lam = np.radians(lon_u)
    phi = np.radians(np.clip(arr_y, -89.5, 89.5))
    rho = (self.R / self.n) * np.sqrt(np.maximum(0.0, self.C - 2.0 * self.n * np.sin(phi)))
    theta = self.n * (lam - self.lon_0)
    px = rho * np.sin(theta)
    py = self.rho_0 - rho * np.cos(theta)
    if np.ndim(arg0_xs) == 0:
      return float(px), float(py)
    return px, py

  def inv_xy (self, arg0_px, arg1_py):
    dx = np.asarray(arg0_px, dtype=float)
    dy = self.rho_0 - np.asarray(arg1_py, dtype=float)
    sign_n = 1.0 if self.n >= 0 else -1.0
    theta = np.arctan2(sign_n * dx, sign_n * dy)
    rho_signed = sign_n * np.hypot(dx, dy)
    lam = self.lon_0 + theta / self.n
    sin_phi = (self.C - (rho_signed * self.n / self.R) ** 2) / (2.0 * self.n)
    valid = (sin_phi >= -1.0) & (sin_phi <= 1.0)
    lat = np.degrees(np.arcsin(np.clip(sin_phi, -1.0, 1.0)))
    lon = np.degrees(lam)
    lon = ((lon + 180.0) % 360.0) - 180.0
    return lon, lat, valid


PROJ_NA = AlbersEqualAreaConic(-96.0, 29.5, 62.5, 45.0)
PROJ_CAN = AlbersEqualAreaConic(-84.0, 49.0, 76.0, 62.0)
PROJ_HI = AlbersEqualAreaConic(-157.5, 19.0, 22.0, 20.5, arg5_wrap_hi=180.0)
PROJ_AS = AlbersEqualAreaConic(-170.3, -14.5, -14.0, -14.25, arg5_wrap_hi=180.0)


def _shift_neg_360 (arg0_xs, arg1_ys, arg2_zs=None):
  ax = np.asarray(arg0_xs, dtype=float) - 360.0
  ay = np.asarray(arg1_ys, dtype=float)
  if np.ndim(arg0_xs) == 0:
    return float(ax), float(ay)
  return ax, ay


def clip_and_project (arg0_geom, arg1_proj, arg2_seg_deg=0.35, arg3_clip_box=None):
  """Clips geometry across antimeridian split for Alaska Aleutians and projects cleanly."""
  if arg0_geom is None or arg0_geom.is_empty:
    return shapely.geometry.Polygon()
  g = arg0_geom
  clip_b = arg3_clip_box if arg3_clip_box is not None else box(-180.0, -30.0, -8.0, 86.0)
  minx, miny, maxx, maxy = g.bounds
  parts = []
  if maxx > clip_b.bounds[0] and minx < clip_b.bounds[2] and maxy > clip_b.bounds[1] and miny < clip_b.bounds[3]:
    gm = g.intersection(clip_b)
    if not gm.is_empty:
      parts.append(gm)
  if arg1_proj.wrap_hi < 179.0 and maxx > arg1_proj.wrap_hi and maxy > 48.0:
    gw = g.intersection(box(arg1_proj.wrap_hi, 48.0, 180.0, 86.0))
    if not gw.is_empty:
      parts.append(shp_transform(_shift_neg_360, gw))
  if not parts:
    return shapely.geometry.Polygon()
  g_u = unary_union(parts) if len(parts) > 1 else parts[0]
  if g_u.is_empty:
    return shapely.geometry.Polygon()
  if arg2_seg_deg and arg2_seg_deg > 0:
    g_u = shapely.segmentize(g_u, max_segment_length=arg2_seg_deg)
  return shp_transform(arg1_proj.fwd_xy, g_u)


def geom_to_patches (arg0_proj_geom):
  """Converts a projected Shapely geometry into Matplotlib Polygon objects."""
  patches = []
  g = arg0_proj_geom
  if g is None or g.is_empty:
    return patches
  gtype = g.geom_type
  if gtype == "Polygon":
    if len(g.exterior.coords) >= 3:
      patches.append(MplPolygon(np.asarray(g.exterior.coords), closed=True))
  elif gtype in ("MultiPolygon", "GeometryCollection"):
    for part in g.geoms:
      patches.extend(geom_to_patches(part))
  return patches


def draw_proj_lines (arg0_ax, arg1_proj_geom, **kwargs):
  """Draws projected LineString / MultiLineString geometries."""
  if arg1_proj_geom is None or arg1_proj_geom.is_empty:
    return
  segs = []

  def collect_ln (arg0_g):
    if arg0_g.is_empty:
      return
    if arg0_g.geom_type == "LineString":
      pts = np.asarray(arg0_g.coords)
      if len(pts) >= 2:
        segs.append(pts)
    elif arg0_g.geom_type in ("MultiLineString", "GeometryCollection"):
      for part in arg0_g.geoms:
        collect_ln(part)

  collect_ln(arg1_proj_geom)
  if segs:
    arg0_ax.add_collection(LineCollection(segs, **kwargs))


def _resolve_ne_file (arg0_name):
  for folder in (GLOBAL_GIS_DIR, POLARIS_GIS_DIR, GIS_DIR):
    p = folder / arg0_name
    if p.exists():
      return p
  return None


_BASEMAP_CACHE = {}


def load_basemap (arg0_proj, arg1_clip_box=None, arg2_seg_deg=0.45):
  """Loads and pre-projects Natural Earth land, lake and river vector layers."""
  key = (id(arg0_proj), str(arg1_clip_box.bounds if arg1_clip_box else "default"))
  if key in _BASEMAP_CACHE:
    return _BASEMAP_CACHE[key]

  land_p = _resolve_ne_file("ne_50m_land.geojson") or _resolve_ne_file("ne_50m_admin_0_countries.geojson")
  lakes_p = _resolve_ne_file("ne_50m_lakes.geojson")
  rivers_p = _resolve_ne_file("ne_50m_rivers_lake_centerlines.geojson")

  land_patches, lake_patches, river_geoms = [], [], []
  if land_p:
    gj = json.loads(land_p.read_text(encoding="utf-8"))
    for f in gj.get("features", []):
      if f.get("geometry"):
        pg = clip_and_project(shape(f["geometry"]), arg0_proj, arg2_seg_deg, arg1_clip_box)
        land_patches.extend(geom_to_patches(pg))
  if lakes_p:
    gj = json.loads(lakes_p.read_text(encoding="utf-8"))
    for f in gj.get("features", []):
      if f.get("geometry"):
        pg = clip_and_project(shape(f["geometry"]), arg0_proj, 0.25, arg1_clip_box)
        lake_patches.extend(geom_to_patches(pg))
  if rivers_p:
    gj = json.loads(rivers_p.read_text(encoding="utf-8"))
    for f in gj.get("features", []):
      if f.get("geometry"):
        pg = clip_and_project(shape(f["geometry"]), arg0_proj, 0.25, arg1_clip_box)
        if not pg.is_empty:
          river_geoms.append(pg)

  _BASEMAP_CACHE[key] = (land_patches, lake_patches, river_geoms)
  return _BASEMAP_CACHE[key]


def draw_basemap (arg0_ax, arg1_proj, arg2_clip_box=None, arg3_dark=False):
  """Renders vector land/ocean/rivers/lakes basemap cleanly inside projected axes."""
  land_p, lake_p, river_g = load_basemap(arg1_proj, arg2_clip_box)
  if arg3_dark:
    arg0_ax.set_facecolor("#142230")
    land_fc, land_ec = "#1e293b", "#475569"
    lake_fc, riv_col = "#162d42", "#38bdf8"
  else:
    arg0_ax.set_facecolor("#d9ebf7")
    land_fc, land_ec = "#f2efe9", "#b8b2a6"
    lake_fc, riv_col = "#b3d9ff", "#2b6cb0"

  if land_p:
    arg0_ax.add_collection(
      PatchCollection([MplPolygon(p.get_xy(), closed=True) for p in land_p],
                      facecolor=land_fc, edgecolor=land_ec, linewidths=0.35, zorder=1.0)
    )
  for rg in river_g:
    draw_proj_lines(arg0_ax, rg, color=riv_col, linewidth=0.38, alpha=0.52, zorder=4.0)
  if lake_p:
    arg0_ax.add_collection(
      PatchCollection([MplPolygon(p.get_xy(), closed=True) for p in lake_p],
                      facecolor=lake_fc, edgecolor=riv_col, linewidths=0.28, zorder=4.1)
    )


def draw_historical_borders (arg0_ax, arg1_proj, arg2_year, arg3_clip_box=None, arg4_color="#334155"):
  """Overlays closest available .naissance historical polity boundaries onto axes."""
  snap_years = [1000, 1250, 1500, 1650, 1707, 1750, 1754, 1763, 1775, 1782, 1784, 1815, 1821, 1850, 1867, 1890]
  nearest_y = min(snap_years, key=lambda y: abs(y - int(arg2_year)))
  cand_names = [f"atlas_na_{nearest_y}.geojson", f"atlas_na_{nearest_y}_mid.geojson"]
  gj_p = next((HIST_DIR / cn for cn in cand_names if (HIST_DIR / cn).exists()), None)
  if gj_p is None:
    return
  gj = json.loads(gj_p.read_text(encoding="utf-8"))
  patches = []
  for f in gj.get("features", []):
    if f.get("geometry"):
      pg = clip_and_project(shape(f["geometry"]), arg1_proj, 0.35, arg3_clip_box)
      patches.extend(geom_to_patches(pg))
  if patches:
    arg0_ax.add_collection(
      PatchCollection([MplPolygon(p.get_xy(), closed=True) for p in patches],
                      facecolor="none", edgecolor=arg4_color, linewidths=0.55, linestyle="--", alpha=0.72, zorder=4.4)
    )


def draw_graticule (arg0_ax, arg1_proj, arg2_xlim, arg3_ylim, arg4_lats, arg5_lons, arg6_lat_span=(-20.0, 84.0), arg7_lon_span=(-178.0, -10.0)):
  """Draws subtle projected dashed graticules inside the target viewport."""
  lon_grid = np.linspace(arg7_lon_span[0], arg7_lon_span[1], 220)
  lat_grid = np.linspace(arg6_lat_span[0], arg6_lat_span[1], 180)
  for lat_v in arg4_lats:
    px, py = arg1_proj.fwd_xy(lon_grid, np.full_like(lon_grid, float(lat_v)))
    arg0_ax.plot(px, py, linestyle=":", linewidth=0.36, color="#64748b", alpha=0.42, zorder=4.2)
  for lon_v in arg5_lons:
    px, py = arg1_proj.fwd_xy(np.full_like(lat_grid, float(lon_v)), lat_grid)
    arg0_ax.plot(px, py, linestyle=":", linewidth=0.36, color="#64748b", alpha=0.42, zorder=4.2)


def reproject_f32_raster (arg0_raster, arg1_proj, arg2_xlim, arg3_ylim, arg4_width_px=1200, arg5_height_px=760):
  """Resamples a 4320x2160 float32 GeoPNG onto a uniform projected equal-area canvas."""
  xs_1d = np.linspace(arg2_xlim[0], arg2_xlim[1], int(arg4_width_px))
  ys_1d = np.linspace(arg3_ylim[1], arg3_ylim[0], int(arg5_height_px))
  xg, yg = np.meshgrid(xs_1d, ys_1d)
  lon_g, lat_g, valid_g = arg1_proj.inv_xy(xg, yg)
  col_idx = np.clip(((lon_g + 180.0) * 12.0).astype(int), 0, 4319)
  row_idx = np.clip(((90.0 - lat_g) * 12.0).astype(int), 0, 2159)
  out = np.where(valid_g, arg0_raster[row_idx, col_idx], 0.0)
  return out


def place_callout (arg0_ax, arg1_label, arg2_lon, arg3_lat, arg4_dx_frac, arg5_dy_frac, arg6_proj, arg7_xlim, arg8_ylim, **kwargs):
  """Places an in-bounds callout annotation with leader line on projected coordinates."""
  x0, y0 = arg6_proj.fwd_pt(arg2_lon, arg3_lat)
  if not (arg7_xlim[0] <= x0 <= arg7_xlim[1] and arg8_ylim[0] <= y0 <= arg8_ylim[1]):
    return
  span_x = arg7_xlim[1] - arg7_xlim[0]
  span_y = arg8_ylim[1] - arg8_ylim[0]
  pad_x = span_x * 0.095
  pad_y = span_y * 0.055
  tx = max(arg7_xlim[0] + pad_x, min(arg7_xlim[1] - pad_x, x0 + arg4_dx_frac * span_x))
  ty = max(arg8_ylim[0] + pad_y, min(arg8_ylim[1] - pad_y, y0 + arg5_dy_frac * span_y))
  fs = float(kwargs.get("fontsize", 6.2))
  dot_col = kwargs.get("dot_col", "#dc2626")
  dot_sz = float(kwargs.get("dot_sz", 16.0))
  arg0_ax.plot([x0, tx], [y0, ty], color="#1f2937", linewidth=0.55, zorder=6.0)
  arg0_ax.scatter([x0], [y0], s=dot_sz, c=dot_col, edgecolors="white", linewidths=0.55, zorder=7.0)
  arg0_ax.text(
    tx, ty, arg1_label,
    fontsize=fs, color="#111827", ha="center", va="center", zorder=10.0,
    bbox=dict(boxstyle="round,pad=0.14", facecolor="white", edgecolor="#6b7280", alpha=0.94, linewidth=0.45)
  )
