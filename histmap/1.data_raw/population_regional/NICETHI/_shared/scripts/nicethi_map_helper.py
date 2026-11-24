"""Shared Lambert Azimuthal Equal-Area & vector cartography utilities for Project NICETHI.

Provides upright Lambert Azimuthal Equal-Area projections for continental Sub-Saharan Africa,
Western Indian Ocean islands, Cabo Verde, Gulf of Guinea and South Atlantic exclaves, cached
Natural Earth 10m coastlines and rivers, curved graticules and POLARIS-compliant vector
PatchCollection rendering built on `viscount_plot_utils.py`.
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
NIC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "NICETHI")
GIS_CACHE = os.path.join(NIC_DIR, "_shared", "_gis_cache")
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

ISO3_DISPLAY = {
  "AGO": "Angola",
  "ATF": "Îles Éparses",
  "BDI": "Burundi",
  "BEN": "Benin",
  "BFA": "Burkina Faso",
  "BWA": "Botswana",
  "CAF": "Central African Rep.",
  "CIV": "Côte d'Ivoire",
  "CMR": "Cameroon",
  "COD": "DR Congo",
  "COG": "Rep. of the Congo",
  "COM": "Comoros",
  "CPV": "Cabo Verde",
  "DJI": "Djibouti",
  "ERI": "Eritrea",
  "ETH": "Ethiopia",
  "GAB": "Gabon",
  "GHA": "Ghana",
  "GIN": "Guinea",
  "GMB": "The Gambia",
  "GNB": "Guinea-Bissau",
  "GNQ": "Equatorial Guinea",
  "IOT": "Chagos Archipelago",
  "KEN": "Kenya",
  "LBR": "Liberia",
  "LSO": "Lesotho",
  "MDG": "Madagascar",
  "MLI": "Mali",
  "MOZ": "Mozambique",
  "MRT": "Mauritania",
  "MUS": "Mauritius",
  "MWI": "Malawi",
  "MYT": "Mayotte",
  "NAM": "Namibia",
  "NER": "Niger",
  "NGA": "Nigeria",
  "REU": "Réunion",
  "RWA": "Rwanda",
  "SDN": "Sudan",
  "SEN": "Senegal",
  "SHN": "Saint Helena",
  "SLE": "Sierra Leone",
  "SOL": "Somaliland",
  "SOM": "Somalia",
  "SSD": "South Sudan",
  "STP": "São Tomé & Príncipe",
  "SWZ": "Eswatini",
  "SYC": "Seychelles",
  "TCD": "Chad",
  "TGO": "Togo",
  "TZA": "Tanzania",
  "UGA": "Uganda",
  "ZAF": "South Africa",
  "ZMB": "Zambia",
  "ZWE": "Zimbabwe",
}

COUNTRY_PALETTE = [
  (91, 143, 185),
  (129, 178, 126),
  (221, 154, 102),
  (168, 134, 186),
  (204, 118, 114),
  (108, 174, 168),
  (195, 174, 105),
  (138, 152, 194),
  (212, 132, 160),
  (145, 182, 106),
  (186, 140, 112),
  (112, 162, 188),
  (178, 156, 196),
  (158, 178, 146),
  (216, 168, 124),
  (132, 166, 178),
]


class LambertAzimuthalEqualArea:
  """Spherical Lambert Azimuthal Equal-Area projection returning kilometres."""

  def __init__ (self, arg0_lon0=20.0, arg1_lat0=-4.0):
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
    denom = 1.0 + self.sin_lat0 * sin_lat + self.cos_lat0 * cos_lat * math.cos(dlon)
    k = math.sqrt(2.0 / max(1e-9, denom))
    x = self.r_km * k * cos_lat * math.sin(dlon)
    y = self.r_km * k * (self.cos_lat0 * sin_lat - self.sin_lat0 * cos_lat * math.cos(dlon))
    return x, y

  def fwd_xy (self, arg0_lon, arg1_lat):
    lon_r = np.radians(np.asarray(arg0_lon, dtype=np.float64))
    lat_r = np.radians(np.clip(np.asarray(arg1_lat, dtype=np.float64), -89.5, 89.5))
    dlon = lon_r - self.lon0
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
    arg = np.clip(rho / (2.0 * self.r_km), 0.0, 1.0)
    c = 2.0 * np.arcsin(arg)
    sin_c = np.sin(c)
    cos_c = np.cos(c)
    safe_rho = np.where(rho > 1e-9, rho, 1.0)
    sin_lat = np.where(
      rho > 1e-9,
      np.clip(cos_c * self.sin_lat0 + (y * sin_c * self.cos_lat0) / safe_rho, -1.0, 1.0),
      self.sin_lat0,
    )
    lat = np.degrees(np.arcsin(sin_lat))
    lon = np.degrees(
      self.lon0 + np.arctan2(
        x * sin_c,
        safe_rho * self.cos_lat0 * cos_c - y * self.sin_lat0 * sin_c,
      )
    )
    lon = np.where(rho > 1e-9, lon, self.lon0_deg)
    return lon, lat


PROJ_AFRICA = LambertAzimuthalEqualArea(20.0, -4.0)
PROJ_WIO = LambertAzimuthalEqualArea(49.5, -16.5)
PROJ_CABO_VERDE = LambertAzimuthalEqualArea(-24.0, 16.0)
PROJ_GULF_GUINEA = LambertAzimuthalEqualArea(7.0, 0.8)
PROJ_ST_HELENA = LambertAzimuthalEqualArea(-5.7, -15.95)
PROJ_CHAGOS = LambertAzimuthalEqualArea(71.9, -6.3)


class BasemapSource10m:
  """Loads Natural Earth 10m countries & rivers once and clips/projects rapidly on demand."""

  def __init__ (self):
    ctry_p = os.path.join(PARENT_GIS_CACHE, "ne_10m_admin_0_countries.geojson")
    if not os.path.isfile(ctry_p):
      ctry_p = os.path.join(PARENT_GIS_CACHE, "ne_50m_admin_0_countries.geojson")
    riv_p = os.path.join(PARENT_GIS_CACHE, "ne_10m_rivers_lake_centerlines.geojson")
    if not os.path.isfile(riv_p):
      riv_p = os.path.join(PARENT_GIS_CACHE, "ne_50m_rivers_lake_centerlines.geojson")

    # Pre-filter to Africa + Atlantic/Indian Ocean islands bounding box to stay lean
    af_box = box(-32.0, -44.0, 78.0, 38.0)
    ctry_gj = json.load(open(ctry_p, encoding="utf-8"))
    self.countries = []
    for feat in ctry_gj.get("features", []):
      geom_raw = feat.get("geometry")
      if not geom_raw:
        continue
      g = shape(geom_raw)
      if not g.intersects(af_box):
        continue
      try:
        gc = g.buffer(0).intersection(af_box)
        if not gc.is_empty:
          self.countries.append(gc)
      except Exception:
        pass

    riv_gj = json.load(open(riv_p, encoding="utf-8"))
    self.rivers = []
    for feat in riv_gj.get("features", []):
      geom_raw = feat.get("geometry")
      if not geom_raw:
        continue
      g = shape(geom_raw)
      if not g.intersects(af_box):
        continue
      try:
        gc = g.intersection(af_box)
        if not gc.is_empty:
          self.rivers.append(gc)
      except Exception:
        pass

  def load_for_extent (self, arg0_proj, arg1_clip_bbox, arg2_show_modern_borders=False, arg3_simplify_deg=0.0):
    cbox = box(*arg1_clip_bbox)
    land_patches = []
    raw_land = []
    for g in self.countries:
      if not g.intersects(cbox):
        continue
      try:
        gc = g.intersection(cbox)
        if gc.is_empty:
          continue
        if arg3_simplify_deg > 0.0:
          gc = gc.simplify(arg3_simplify_deg, preserve_topology=True)
        if arg2_show_modern_borders:
          pg = prepare_and_project(gc, arg0_proj, 0.35, None)
          land_patches.extend(geom_to_patches(pg))
        else:
          raw_land.append(gc)
      except Exception:
        pass

    if not arg2_show_modern_borders and raw_land:
      dissolved = unary_union(raw_land).buffer(0)
      pg = prepare_and_project(dissolved, arg0_proj, 0.35, None)
      land_patches.extend(geom_to_patches(pg))

    river_geoms = []
    for g in self.rivers:
      if not g.intersects(cbox):
        continue
      try:
        gc = g.intersection(cbox)
        if gc.is_empty:
          continue
        pg = prepare_and_project(gc, arg0_proj, 0.35, None)
        if not pg.is_empty:
          river_geoms.append(pg)
      except Exception:
        pass

    return land_patches, river_geoms


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


def draw_graticule (arg0_ax, arg1_proj, arg2_xlim, arg3_ylim, arg4_lats, arg5_lons, arg6_lon_span=(-30.0, 75.0), arg7_lat_span=(-42.0, 35.0)):
  """Draws subtle curved LAEA graticule lines inside panel bounds without clutter."""
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


def tint_country_shade (arg0_rgb, arg1_variant=0):
  """Subtly modulates a country's muted base RGB across Admin-1 units for crisp internal differentiation."""
  r0, g0, b0 = int(arg0_rgb[0]), int(arg0_rgb[1]), int(arg0_rgb[2])
  shifts = (0.30, 0.42, 0.52, 0.24, 0.47, 0.36)
  blend = shifts[int(arg1_variant) % len(shifts)]
  return mute_rgb_hex((r0, g0, b0), arg1_variant, blend)
