"""Antimeridian-safe Equal-Area vector cartography utilities for Project AUSTRAL.

Provides upright Lambert Azimuthal Equal-Area (`LAEA`) and Southern-Hemisphere Albers
Equal-Area Conic (`AEAC`) projections with continuous Pacific longitude shifting
(`lon_shifted = lon + 360 if lon < 0 else lon` when `lon0` lies in `100..260°E`),
ensuring Fiji, Tonga, Samoa, Kiribati, French Polynesia, Cook Islands, Chatham Islands,
Pitcairn and Rapa Nui render seamlessly across `180°` without antimeridian spikes.

Wraps `viscount_plot_utils.py` (`apply_viscount_style`, `euro_tick_formatter`,
`apply_human_log_ticks`, `euro_log_formatter`, `mute_rgb_hex`, `place_inbounds_callouts`,
`save_viscount_figure`) and Natural Earth 10m physical coastlines & rivers.
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
from shapely.ops import unary_union

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
AUS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL")
GIS_CACHE = os.path.join(AUS_DIR, "_shared", "_gis_cache")
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

R_EARTH_KM = 6371.0088

# Module-level cache of Pacific-shifted Natural Earth 10m geometries (loaded once per process)
_NE_CACHE = {}


def shift_lon_scalar (arg0_lon, arg1_pacific_shift=True):
  """Shifts a scalar longitude into continuous Pacific `[0, 360]` degrees when enabled."""
  val = float(arg0_lon)
  if arg1_pacific_shift and val < 0.0:
    return val + 360.0
  return val


def shift_lon_array (arg0_lon, arg1_pacific_shift=True):
  """Shifts a NumPy array of longitudes into continuous Pacific `[0, 360]` degrees when enabled."""
  arr = np.asarray(arg0_lon, dtype=np.float64)
  if arg1_pacific_shift:
    return np.where(arr < 0.0, arr + 360.0, arr)
  return arr


def shift_geom_pacific (arg0_geom, arg1_east_min=95.0, arg2_west_max=-95.0, arg3_lat_min=-60.0, arg4_lat_max=35.0):
  """Clips a WGS84 Shapely geometry to the Pacific hemisphere (`[95, 180]` and `[-180, -95]`)
  and shifts western-hemisphere coordinates by `+360°`, eliminating all `±180°` wrapping spikes."""
  if arg0_geom is None or arg0_geom.is_empty:
    return Polygon()
  g = arg0_geom
  box_e = box(float(arg1_east_min), float(arg3_lat_min), 180.0, float(arg4_lat_max))
  box_w = box(-180.0, float(arg3_lat_min), float(arg2_west_max), float(arg4_lat_max))
  parts = []
  for b_cur, do_shift in ((box_e, False), (box_w, True)):
    if not g.intersects(b_cur):
      continue
    try:
      sub = g.intersection(b_cur)
    except Exception:
      try:
        sub = g.buffer(0).intersection(b_cur)
      except Exception:
        continue
    if sub.is_empty:
      continue
    if do_shift:
      sub = shp_transform(lambda x, y, z=None: (x + 360.0, y), sub)
    parts.append(sub)
  if not parts:
    return Polygon()
  if len(parts) == 1:
    return parts[0]
  try:
    return unary_union(parts)
  except Exception:
    return parts[0]


class LambertAzimuthalEqualArea:
  """Upright spherical Lambert Azimuthal Equal-Area (`LAEA`) projection returning kilometres,
  with automatic continuous Pacific longitude shifting across the `180°` antimeridian."""

  def __init__ (self, arg0_lon0=165.0, arg1_lat0=-18.0):
    self.lon0_deg = float(arg0_lon0)
    if self.lon0_deg < 0.0:
      self.lon0_deg += 360.0
    self.pacific_shift = (100.0 <= self.lon0_deg <= 265.0)
    self.lon0 = math.radians(self.lon0_deg)
    self.lat0 = math.radians(float(arg1_lat0))
    self.sin_lat0 = math.sin(self.lat0)
    self.cos_lat0 = math.cos(self.lat0)
    self.r_km = R_EARTH_KM

  def fwd_pt (self, arg0_lon, arg1_lat):
    lon_s = shift_lon_scalar(arg0_lon, self.pacific_shift)
    dlon = math.radians(lon_s - self.lon0_deg)
    lat_r = math.radians(max(-85.0, min(85.0, float(arg1_lat))))
    sin_lat = math.sin(lat_r)
    cos_lat = math.cos(lat_r)
    denom = 1.0 + self.sin_lat0 * sin_lat + self.cos_lat0 * cos_lat * math.cos(dlon)
    k = math.sqrt(2.0 / max(1e-9, denom))
    x = self.r_km * k * cos_lat * math.sin(dlon)
    y = self.r_km * k * (self.cos_lat0 * sin_lat - self.sin_lat0 * cos_lat * math.cos(dlon))
    return x, y

  def fwd_xy (self, arg0_lon, arg1_lat):
    lon_s = shift_lon_array(arg0_lon, self.pacific_shift)
    dlon = np.radians(lon_s - self.lon0_deg)
    lat_r = np.radians(np.clip(np.asarray(arg1_lat, dtype=np.float64), -85.0, 85.0))
    sin_lat = np.sin(lat_r)
    cos_lat = np.cos(lat_r)
    denom = 1.0 + self.sin_lat0 * sin_lat + self.cos_lat0 * cos_lat * np.cos(dlon)
    k = np.sqrt(2.0 / np.maximum(1e-9, denom))
    x = self.r_km * k * cos_lat * np.sin(dlon)
    y = self.r_km * k * (self.cos_lat0 * sin_lat - self.sin_lat0 * cos_lat * np.cos(dlon))
    return x, y

  def inv_xy (self, arg0_x, arg1_y):
    x = np.asarray(arg0_x, dtype=np.float64)
    y = np.asarray(arg1_y, dtype=np.float64)
    rho = np.hypot(x, y)
    c = 2.0 * np.arcsin(np.clip(rho / (2.0 * self.r_km), -1.0, 1.0))
    sin_c = np.sin(c)
    cos_c = np.cos(c)
    safe_rho = np.where(rho > 1e-9, rho, 1.0)
    sin_lat = np.where(
      rho > 1e-9,
      cos_c * self.sin_lat0 + (y * sin_c * self.cos_lat0) / safe_rho,
      self.sin_lat0,
    )
    lat = np.degrees(np.arcsin(np.clip(sin_lat, -1.0, 1.0)))
    lon_sh = self.lon0_deg + np.degrees(
      np.arctan2(
        x * sin_c,
        safe_rho * self.cos_lat0 * cos_c - y * self.sin_lat0 * sin_c,
      )
    )
    lon_raw = ((lon_sh + 180.0) % 360.0) - 180.0
    return lon_raw, lat


class AlbersEqualAreaConic:
  """Upright spherical Albers Equal-Area Conic (`AEAC`) projection returning kilometres,
  valid in both hemispheres with continuous Pacific longitude shifting."""

  def __init__ (self, arg0_lon0=134.0, arg1_lat1=-18.0, arg2_lat2=-36.0, arg3_lat0=-27.0):
    self.lon0_deg = float(arg0_lon0)
    if self.lon0_deg < 0.0:
      self.lon0_deg += 360.0
    self.pacific_shift = (100.0 <= self.lon0_deg <= 265.0)
    self.lon0 = math.radians(self.lon0_deg)
    self.lat1 = math.radians(float(arg1_lat1))
    self.lat2 = math.radians(float(arg2_lat2))
    self.lat0 = math.radians(float(arg3_lat0))
    self.r_km = R_EARTH_KM
    self.n = 0.5 * (math.sin(self.lat1) + math.sin(self.lat2))
    if abs(self.n) < 1e-4:
      self.n = -1e-4 if self.lat0 < 0.0 else 1e-4
    self.c = (math.cos(self.lat1) ** 2) + 2.0 * self.n * math.sin(self.lat1)
    self.rho0 = (self.r_km / self.n) * math.sqrt(max(1e-12, self.c - 2.0 * self.n * math.sin(self.lat0)))

  def fwd_pt (self, arg0_lon, arg1_lat):
    lon_s = shift_lon_scalar(arg0_lon, self.pacific_shift)
    lat_r = math.radians(max(-85.0, min(85.0, float(arg1_lat))))
    theta = self.n * math.radians(lon_s - self.lon0_deg)
    rho = (self.r_km / self.n) * math.sqrt(max(1e-12, self.c - 2.0 * self.n * math.sin(lat_r)))
    return rho * math.sin(theta), self.rho0 - rho * math.cos(theta)

  def fwd_xy (self, arg0_lon, arg1_lat):
    lon_s = shift_lon_array(arg0_lon, self.pacific_shift)
    lat_r = np.radians(np.clip(np.asarray(arg1_lat, dtype=np.float64), -85.0, 85.0))
    theta = self.n * np.radians(lon_s - self.lon0_deg)
    rho = (self.r_km / self.n) * np.sqrt(np.maximum(1e-12, self.c - 2.0 * self.n * np.sin(lat_r)))
    return rho * np.sin(theta), self.rho0 - rho * np.cos(theta)

  def inv_xy (self, arg0_x, arg1_y):
    x = np.asarray(arg0_x, dtype=np.float64)
    y = np.asarray(arg1_y, dtype=np.float64)
    dy = self.rho0 - y
    if self.n < 0.0:
      rho = -np.hypot(x, dy)
      theta = np.arctan2(-x, -dy)
    else:
      rho = np.hypot(x, dy)
      theta = np.arctan2(x, dy)
    sin_lat = np.clip((self.c - ((rho * self.n / self.r_km) ** 2)) / (2.0 * self.n), -1.0, 1.0)
    lat = np.degrees(np.arcsin(sin_lat))
    lon_sh = self.lon0_deg + np.degrees(theta / self.n)
    lon_raw = ((lon_sh + 180.0) % 360.0) - 180.0
    return lon_raw, lat


# Canonical AUSTRAL regional equal-area projections
PROJ_AUSTRALIA = AlbersEqualAreaConic(133.5, -18.0, -36.0, -27.0)
PROJ_NEW_ZEALAND = AlbersEqualAreaConic(173.0, -37.0, -45.5, -41.2)
PROJ_CHATHAMS = LambertAzimuthalEqualArea(183.45, -44.0)
PROJ_NORFOLK_LORD_HOWE = LambertAzimuthalEqualArea(163.5, -30.3)
PROJ_NEW_GUINEA = LambertAzimuthalEqualArea(143.0, -5.5)
PROJ_MELANESIA = LambertAzimuthalEqualArea(168.5, -14.5)
PROJ_MICRONESIA = LambertAzimuthalEqualArea(155.0, 8.5)
PROJ_LINE_PHOENIX = LambertAzimuthalEqualArea(196.0, 1.0)
PROJ_WEST_POLYNESIA = LambertAzimuthalEqualArea(189.0, -14.5)
PROJ_EAST_POLYNESIA = LambertAzimuthalEqualArea(215.0, -17.5)
PROJ_RAPA_NUI_PITCAIRN = LambertAzimuthalEqualArea(241.0, -25.8)
PROJ_PAN_OCEANIA_WEST = LambertAzimuthalEqualArea(147.0, -24.0)
PROJ_PAN_OCEANIA_EAST = LambertAzimuthalEqualArea(192.0, -10.0)


def prepare_and_project (arg0_geom, arg1_proj, arg2_seg_deg=0.35, arg3_clip_box_shifted=None):
  """Clips (in shifted Pacific degrees), segmentises and projects a Pacific-shifted Shapely geometry cleanly."""
  if arg0_geom is None or arg0_geom.is_empty:
    return Polygon()
  g = arg0_geom
  if arg3_clip_box_shifted is not None:
    try:
      g = g.intersection(arg3_clip_box_shifted)
    except Exception:
      try:
        g = g.buffer(0).intersection(arg3_clip_box_shifted)
      except Exception:
        return Polygon()
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


def _load_pacific_natural_earth ():
  """Loads and caches Pacific-shifted Natural Earth 10m countries (split & dissolved) and 10m rivers."""
  if "loaded" in _NE_CACHE:
    return _NE_CACHE

  ctry_p = os.path.join(PARENT_GIS_CACHE, "ne_10m_admin_0_countries.geojson")
  if not os.path.isfile(ctry_p):
    ctry_p = os.path.join(PARENT_GIS_CACHE, "ne_50m_admin_0_countries.geojson")
  riv_p = os.path.join(PARENT_GIS_CACHE, "ne_10m_rivers_lake_centerlines.geojson")
  if not os.path.isfile(riv_p):
    riv_p = os.path.join(PARENT_GIS_CACHE, "ne_50m_rivers_lake_centerlines.geojson")

  ctry_gj = json.load(open(ctry_p, encoding="utf-8"))
  riv_gj = json.load(open(riv_p, encoding="utf-8"))

  pac_countries = []
  for feat in ctry_gj.get("features", []):
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    g = shape(geom_raw)
    sg = shift_geom_pacific(g, 95.0, -95.0, -56.0, 32.0)
    if not sg.is_empty:
      pac_countries.append(sg)

  pac_rivers = []
  for feat in riv_gj.get("features", []):
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    g = shape(geom_raw)
    sg = shift_geom_pacific(g, 95.0, -95.0, -56.0, 32.0)
    if not sg.is_empty:
      pac_rivers.append(sg)

  _NE_CACHE["countries"] = pac_countries
  _NE_CACHE["rivers"] = pac_rivers
  _NE_CACHE["loaded"] = True
  return _NE_CACHE


def load_basemap_cache (arg0_proj, arg1_clip_bbox_shifted=(105.0, -52.0, 260.0, 28.0), arg2_show_modern_borders=False):
  """Projects Natural Earth 10m Pacific coastlines and rivers into `arg0_proj`.

  For ALL pre-1945/historical chapters (`arg2_show_modern_borders=False`), dissolves
  Natural Earth country geometries into pure physical landmasses so ZERO modern 2025
  state borders appear beneath pre-colonial or colonial boundaries.
  """
  ne = _load_pacific_natural_earth()
  cbox = box(*arg1_clip_bbox_shifted)

  land_patches = []
  raw_land = []
  for g in ne["countries"]:
    if not g.intersects(cbox):
      continue
    if arg2_show_modern_borders:
      pg = prepare_and_project(g, arg0_proj, 0.30, cbox)
      land_patches.extend(geom_to_patches(pg))
    else:
      try:
        gc = g.intersection(cbox)
      except Exception:
        try:
          gc = g.buffer(0).intersection(cbox)
        except Exception:
          continue
      if not gc.is_empty:
        raw_land.append(gc)

  if not arg2_show_modern_borders and raw_land:
    try:
      dissolved = unary_union(raw_land).buffer(0)
    except Exception:
      dissolved = unary_union([r.buffer(0) for r in raw_land])
    pg = prepare_and_project(dissolved, arg0_proj, 0.30, None)
    land_patches.extend(geom_to_patches(pg))

  river_geoms = []
  for rg in ne["rivers"]:
    if not rg.intersects(cbox):
      continue
    pg = prepare_and_project(rg, arg0_proj, 0.25, cbox)
    if not pg.is_empty:
      river_geoms.append(pg)

  return land_patches, river_geoms


def draw_basemap (arg0_ax, arg1_land_patches, arg2_river_geoms):
  """Draws clean ocean backdrop, parchment physical land polygons and subtle blue rivers."""
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
    draw_proj_lines(arg0_ax, rg, color="#2b6cb0", linewidth=0.40, alpha=0.50, zorder=4.0)


def draw_graticule (arg0_ax, arg1_proj, arg2_xlim, arg3_ylim, arg4_lats, arg5_lons_shifted, arg6_lon_span_shifted=(105.0, 260.0), arg7_lat_span=(-52.0, 28.0)):
  """Draws subtle curved equal-area graticule lines seamlessly across `180°` without clutter."""
  lon_grid = np.linspace(arg6_lon_span_shifted[0], arg6_lon_span_shifted[1], 180)
  lat_grid = np.linspace(arg7_lat_span[0], arg7_lat_span[1], 160)
  x0, x1 = arg2_xlim
  y0, y1 = arg3_ylim
  bview = box(x0, y0, x1, y1)

  for lat_v in arg4_lats:
    px, py = arg1_proj.fwd_xy(lon_grid, np.full_like(lon_grid, float(lat_v)))
    ls = LineString(np.column_stack([px, py])).intersection(bview)
    if not ls.is_empty:
      draw_proj_lines(arg0_ax, ls, linestyle="--", linewidth=0.32, color="#64748b", alpha=0.34, zorder=4.2)

  for lon_v in arg5_lons_shifted:
    px, py = arg1_proj.fwd_xy(np.full_like(lat_grid, float(lon_v)), lat_grid)
    ls = LineString(np.column_stack([px, py])).intersection(bview)
    if not ls.is_empty:
      is_antimeridian = abs(float(lon_v) - 180.0) < 1e-6
      ls_style = "-." if is_antimeridian else "--"
      ls_alpha = 0.48 if is_antimeridian else 0.34
      draw_proj_lines(arg0_ax, ls, linestyle=ls_style, linewidth=0.38 if is_antimeridian else 0.32, color="#475569" if is_antimeridian else "#64748b", alpha=ls_alpha, zorder=4.2)
