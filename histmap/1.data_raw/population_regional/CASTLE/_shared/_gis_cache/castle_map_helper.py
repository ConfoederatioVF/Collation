# -*- coding: utf-8 -*-
"""Shared Equal-Area cartographic projection, Natural Earth basemap,
float32 GeoPNG reprojection and zero-overlap callout utilities for CASTLE
(Korea and Japan) monograph and chapter figures.
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
from matplotlib.transforms import Bbox
from PIL import Image
import shapely
from shapely.geometry import box, shape
from shapely.ops import transform as shp_transform

GIS_DIR = pathlib.Path(__file__).resolve().parent
CASTLE_DIR = GIS_DIR.parents[1]
GLOBAL_GIS_DIR = CASTLE_DIR.parent / "_shared" / "_gis_cache"
POLARIS_GIS_DIR = CASTLE_DIR.parent / "POLARIS" / "_shared" / "_gis_cache"
SUBREG_DIR = GIS_DIR / "chapter_subregions"

SHARED_DIR = CASTLE_DIR.parent / "_shared"
if str(SHARED_DIR) not in sys.path:
  sys.path.insert(0, str(SHARED_DIR))
import viscount_plot_utils as vpu


class AlbersEqualAreaConic:
  """Snyder Equal-Area Conic projection (kilometres) for Korea and Japan."""

  def __init__ (self, arg0_lon_0, arg1_lat_1, arg2_lat_2, arg3_lat_0, arg4_r_km=6371.0088):
    self.lon_0 = math.radians(arg0_lon_0)
    self.lat_0 = math.radians(arg3_lat_0)
    p1 = math.radians(arg1_lat_1)
    p2 = math.radians(arg2_lat_2)
    self.n = 0.5 * (math.sin(p1) + math.sin(p2))
    if abs(self.n) < 1e-6:
      self.n = 1e-6
    self.C = (math.cos(p1) ** 2) + 2.0 * self.n * math.sin(p1)
    self.R = float(arg4_r_km)
    self.rho_0 = (self.R / self.n) * math.sqrt(max(0.0, self.C - 2.0 * self.n * math.sin(self.lat_0)))

  def fwd_pt (self, arg0_lon_deg, arg1_lat_deg):
    lam = math.radians(float(arg0_lon_deg))
    phi = math.radians(max(-89.5, min(89.5, float(arg1_lat_deg))))
    rho = (self.R / self.n) * math.sqrt(max(0.0, self.C - 2.0 * self.n * math.sin(phi)))
    theta = self.n * (lam - self.lon_0)
    return (rho * math.sin(theta), self.rho_0 - rho * math.cos(theta))

  def fwd_xy (self, arg0_xs, arg1_ys, arg2_zs=None):
    arr_x = np.asarray(arg0_xs, dtype=float)
    arr_y = np.asarray(arg1_ys, dtype=float)
    lam = np.radians(arr_x)
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


PROJ_CASTLE = AlbersEqualAreaConic(134.5, 30.0, 42.5, 36.5)
PROJ_JAPAN = AlbersEqualAreaConic(137.5, 31.5, 43.0, 37.0)
PROJ_KOREA = AlbersEqualAreaConic(127.5, 35.0, 41.0, 38.0)
PROJ_RYUKYU = AlbersEqualAreaConic(127.0, 24.5, 28.5, 26.5)
CASTLE_CLIP = box(118.0, 21.0, 152.0, 50.0)


def clip_and_project (arg0_geom, arg1_proj, arg2_seg_deg=0.18, arg3_clip_box=None):
  if arg0_geom is None or arg0_geom.is_empty:
    return shapely.geometry.Polygon()
  clip_b = arg3_clip_box if arg3_clip_box is not None else CASTLE_CLIP
  minx, miny, maxx, maxy = arg0_geom.bounds
  cb = clip_b.bounds
  if maxx < cb[0] or minx > cb[2] or maxy < cb[1] or miny > cb[3]:
    return shapely.geometry.Polygon()
  gm = arg0_geom.intersection(clip_b)
  if gm.is_empty:
    return shapely.geometry.Polygon()
  if arg2_seg_deg and arg2_seg_deg > 0:
    gm = shapely.segmentize(gm, max_segment_length=arg2_seg_deg)
  return shp_transform(arg1_proj.fwd_xy, gm)


def geom_to_patches (arg0_proj_geom):
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
  for folder in (GIS_DIR, POLARIS_GIS_DIR, GLOBAL_GIS_DIR):
    p = folder / arg0_name
    if p.exists():
      return p
  return None


_BASEMAP_CACHE = {}


def load_basemap (arg0_proj, arg1_clip_box=None, arg2_seg_deg=0.22):
  key = (id(arg0_proj), str(arg1_clip_box.bounds if arg1_clip_box else "default"))
  if key in _BASEMAP_CACHE:
    return _BASEMAP_CACHE[key]
  land_p = _resolve_ne_file("ne_10m_admin_0_countries.geojson") or _resolve_ne_file("ne_50m_admin_0_countries.geojson")
  lakes_p = _resolve_ne_file("ne_10m_lakes.geojson") or _resolve_ne_file("ne_50m_lakes.geojson")
  rivers_p = _resolve_ne_file("ne_10m_rivers_lake_centerlines.geojson") or _resolve_ne_file("ne_50m_rivers_lake_centerlines.geojson")
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
        pg = clip_and_project(shape(f["geometry"]), arg0_proj, 0.18, arg1_clip_box)
        lake_patches.extend(geom_to_patches(pg))
  if rivers_p:
    gj = json.loads(rivers_p.read_text(encoding="utf-8"))
    for f in gj.get("features", []):
      if f.get("geometry"):
        pg = clip_and_project(shape(f["geometry"]), arg0_proj, 0.18, arg1_clip_box)
        if not pg.is_empty:
          river_geoms.append(pg)
  _BASEMAP_CACHE[key] = (land_patches, lake_patches, river_geoms)
  return _BASEMAP_CACHE[key]


def draw_basemap (arg0_ax, arg1_proj, arg2_clip_box=None, arg3_dark=False):
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
      PatchCollection([MplPolygon(p.get_xy(), closed=True) for p in land_p], facecolor=land_fc, edgecolor=land_ec, linewidths=0.35, zorder=1.0)
    )
  for rg in river_g:
    draw_proj_lines(arg0_ax, rg, color=riv_col, linewidth=0.38, alpha=0.52, zorder=4.0)
  if lake_p:
    arg0_ax.add_collection(
      PatchCollection([MplPolygon(p.get_xy(), closed=True) for p in lake_p], facecolor=lake_fc, edgecolor=riv_col, linewidths=0.28, zorder=4.1)
    )


def load_f32_raster (arg0_path):
  arr = np.asarray(Image.open(arg0_path).convert("RGBA"), dtype=np.uint8)
  f32 = np.frombuffer(arr.tobytes(), dtype=">f4").reshape(arr.shape[0], arr.shape[1]).copy()
  return np.where(np.isfinite(f32) & (f32 >= 0.0) & (f32 < 1e12), f32, 0.0)


def reproject_f32_raster (arg0_raster, arg1_proj, arg2_xlim, arg3_ylim, arg4_width_px=1000, arg5_height_px=760):
  xs_1d = np.linspace(arg2_xlim[0], arg2_xlim[1], int(arg4_width_px))
  ys_1d = np.linspace(arg3_ylim[1], arg3_ylim[0], int(arg5_height_px))
  xg, yg = np.meshgrid(xs_1d, ys_1d)
  lon_g, lat_g, valid_g = arg1_proj.inv_xy(xg, yg)
  col_idx = np.clip(((lon_g + 180.0) * 12.0).astype(int), 0, 4319)
  row_idx = np.clip(((90.0 - lat_g) * 12.0).astype(int), 0, 2159)
  return np.where(valid_g, arg0_raster[row_idx, col_idx], 0.0)


def mute_rgb_hex (arg0_col, arg1_idx=0, arg2_blend=0.44):
  return vpu.mute_rgb_hex(arg0_col, arg1_idx, arg2_blend)


def draw_inline_graticule (arg0_ax, arg1_proj, arg2_xlim, arg3_ylim, arg4_lats, arg5_lons, arg6_show_labels=True):
  x0, x1 = float(arg2_xlim[0]), float(arg2_xlim[1])
  y0, y1 = float(arg3_ylim[0]), float(arg3_ylim[1])
  span_x = max(1e-6, x1 - x0)
  span_y = max(1e-6, y1 - y0)
  lon_seq = np.linspace(118.0, 152.0, 220)
  lat_seq = np.linspace(21.0, 50.0, 180)
  label_xs = x0 + 0.022 * span_x
  label_ys = y0 + 0.020 * span_y
  avoid_bbs = []
  rend = None
  if arg6_show_labels and arg0_ax.figure is not None:
    arg0_ax.figure.canvas.draw()
    rend = arg0_ax.figure.canvas.get_renderer()
    dp_s = max(1.0, float(arg0_ax.figure.dpi) / 100.0)
    for ch_ax in arg0_ax.child_axes:
      cbb = ch_ax.get_window_extent(rend)
      avoid_bbs.append(Bbox.from_extents(cbb.x0 - 16.0 * dp_s, cbb.y0 - 24.0 * dp_s, cbb.x1 + 16.0 * dp_s, cbb.y1 + 18.0 * dp_s))
    leg = arg0_ax.get_legend()
    if leg is not None and leg.get_visible():
      lbb = leg.get_window_extent(rend)
      avoid_bbs.append(Bbox.from_extents(lbb.x0 - 10.0 * dp_s, lbb.y0 - 10.0 * dp_s, lbb.x1 + 10.0 * dp_s, lbb.y1 + 10.0 * dp_s))
  placed_lat_ys, placed_lat_bbs = [], []
  for lat_v in arg4_lats:
    px, py = arg1_proj.fwd_xy(lon_seq, np.full_like(lon_seq, float(lat_v)))
    arg0_ax.plot(px, py, linestyle=":", linewidth=0.38, color="#64748b", alpha=0.44, zorder=4.2)
    if not arg6_show_labels or rend is None:
      continue
    inside = np.where((px >= x0) & (px <= x1) & (py >= y0 + 0.10 * span_y) & (py <= y1 - 0.08 * span_y))[0]
    if len(inside) == 0:
      continue
    idx_k = inside[int(np.argmin(np.abs(px[inside] - label_xs)))]
    if abs(float(px[idx_k]) - label_xs) > 0.055 * span_x:
      continue
    disp_pt = arg0_ax.transData.transform((label_xs, float(py[idx_k])))
    if any(abs(disp_pt[1] - py_p) < 26.0 for py_p in placed_lat_ys):
      continue
    t_obj = arg0_ax.text(label_xs, float(py[idx_k]), f"{abs(int(lat_v))}°N", fontsize=5.8, color="#475569", alpha=0.75, va="bottom", ha="left", zorder=4.6)
    arg0_ax.figure.canvas.draw()
    t_bb = t_obj.get_window_extent(rend).expanded(1.06, 1.14)
    if any(t_bb.overlaps(ab) for ab in avoid_bbs) or any(t_bb.overlaps(pb) for pb in placed_lat_bbs):
      t_obj.remove()
    else:
      placed_lat_ys.append(float(disp_pt[1]))
      placed_lat_bbs.append(t_bb)
  placed_lon_xs, placed_lon_bbs = [], []
  for lon_v in arg5_lons:
    px, py = arg1_proj.fwd_xy(np.full_like(lat_seq, float(lon_v)), lat_seq)
    arg0_ax.plot(px, py, linestyle=":", linewidth=0.38, color="#64748b", alpha=0.44, zorder=4.2)
    if not arg6_show_labels or rend is None:
      continue
    inside = np.where((py >= y0) & (py <= y1) & (px >= x0 + 0.10 * span_x) & (px <= x1 - 0.08 * span_x))[0]
    if len(inside) == 0:
      continue
    idx_k = inside[int(np.argmin(np.abs(py[inside] - label_ys)))]
    if abs(float(py[idx_k]) - label_ys) > 0.055 * span_y:
      continue
    disp_pt = arg0_ax.transData.transform((float(px[idx_k]), label_ys))
    if any(abs(disp_pt[0] - px_p) < 48.0 for px_p in placed_lon_xs):
      continue
    t_obj = arg0_ax.text(float(px[idx_k]), label_ys, f"{abs(int(round(lon_v)))}°E", fontsize=5.8, color="#475569", alpha=0.75, va="bottom", ha="center", zorder=4.6)
    arg0_ax.figure.canvas.draw()
    t_bb = t_obj.get_window_extent(rend).expanded(1.06, 1.14)
    if any(t_bb.overlaps(ab) for ab in avoid_bbs) or any(t_bb.overlaps(lb) for lb in placed_lon_bbs) or any(t_bb.overlaps(pb) for pb in placed_lat_bbs):
      t_obj.remove()
    else:
      placed_lon_xs.append(float(disp_pt[0]))
      placed_lon_bbs.append(t_bb)


def place_bbox_callouts (arg0_fig, arg1_ax, arg2_items, arg3_proj, arg4_xlim, arg5_ylim, arg6_max_labels=6, arg7_min_sep_px=38.0, arg8_fontsize=6.4):
  x0_lim, x1_lim = float(arg4_xlim[0]), float(arg4_xlim[1])
  y0_lim, y1_lim = float(arg5_ylim[0]), float(arg5_ylim[1])
  in_pts = []
  for it in arg2_items:
    lbl, lon, lat = it[0], float(it[1]), float(it[2])
    px, py = arg3_proj.fwd_pt(lon, lat)
    if x0_lim <= px <= x1_lim and y0_lim <= py <= y1_lim:
      in_pts.append((lbl, px, py))
  if not in_pts:
    return []
  arg0_fig.canvas.draw()
  rend = arg0_fig.canvas.get_renderer()
  ax_bb = arg1_ax.get_window_extent(rend)
  safe_bb = Bbox.from_extents(ax_bb.x0 + 6.0, ax_bb.y0 + 6.0, ax_bb.x1 - 6.0, ax_bb.y1 - 6.0)
  occupied = []
  for child_ax in arg1_ax.child_axes:
    if child_ax.get_visible():
      occupied.append(child_ax.get_window_extent(rend).expanded(1.04, 1.08))
  leg = arg1_ax.get_legend()
  if leg is not None and leg.get_visible():
    occupied.append(leg.get_window_extent(rend).expanded(1.04, 1.06))
  for t_ex in arg1_ax.texts:
    if t_ex.get_visible() and t_ex.get_text().strip():
      occupied.append(t_ex.get_window_extent(rend).expanded(1.05, 1.12))
  dp_s = max(1.0, float(arg0_fig.dpi) / 100.0)
  min_sep_d = max(float(arg7_min_sep_px), 18.0 * dp_s)
  disp_pts, placed_anchors = [], []
  for lbl, px, py in in_pts:
    dx_p, dy_p = arg1_ax.transData.transform((px, py))
    if any(math.hypot(dx_p - axp, dy_p - ayp) < min_sep_d for axp, ayp in placed_anchors):
      continue
    placed_anchors.append((dx_p, dy_p))
    disp_pts.append((lbl, px, py, dx_p, dy_p))
    occupied.append(Bbox.from_bounds(dx_p - 3.0 * dp_s, dy_p - 3.0 * dp_s, 6.0 * dp_s, 6.0 * dp_s))
    if len(disp_pts) >= arg6_max_labels:
      break
  offsets_px = []
  for rad in (28.0, 50.0, 76.0, 106.0, 136.0):
    for ang_deg in (90, 118, 62, 145, 35, 0, 180, 330, 210, 295, 245):
      ar = math.radians(ang_deg)
      offsets_px.append((rad * 1.12 * math.cos(ar), rad * 0.90 * math.sin(ar)))
  placed = []
  inv_trans = arg1_ax.transData.inverted()
  for lbl, px, py, dx_p, dy_p in disp_pts:
    t_obj = arg1_ax.text(
      px, py, lbl, fontsize=arg8_fontsize, color="#0f172a", ha="center", va="center", zorder=10.5,
      bbox=dict(boxstyle="round,pad=0.16", facecolor="white", edgecolor="#475569", alpha=0.95, linewidth=0.5)
    )
    chosen_bb, chosen_xy = None, None
    for ox, oy in offsets_px:
      tx_d, ty_d = dx_p + ox, dy_p + oy
      tx_w, ty_w = inv_trans.transform((tx_d, ty_d))
      t_obj.set_position((tx_w, ty_w))
      arg0_fig.canvas.draw()
      bb_cur = t_obj.get_window_extent(rend).expanded(1.06, 1.16)
      if not (bb_cur.x0 >= safe_bb.x0 and bb_cur.x1 <= safe_bb.x1 and bb_cur.y0 >= safe_bb.y0 and bb_cur.y1 <= safe_bb.y1):
        continue
      if any(bb_cur.overlaps(o_bb) for o_bb in occupied):
        continue
      chosen_bb = bb_cur
      chosen_xy = (tx_w, ty_w)
      break
    if chosen_xy is None:
      t_obj.remove()
      continue
    arg1_ax.plot([px, chosen_xy[0]], [py, chosen_xy[1]], color="#1e293b", linewidth=0.58, zorder=7.5)
    arg1_ax.scatter([px], [py], s=22.0, c="#b91c1c", edgecolors="white", linewidths=0.65, zorder=8.8)
    occupied.append(chosen_bb)
    placed.append(t_obj)
  return placed


def verify_zero_text_overlaps (arg0_fig, arg1_label=""):
  """Checks renderer bounding boxes via viscount_plot_utils and prints any layout warnings."""
  res = vpu.verify_panel_bounds_and_overlaps(arg0_fig, arg1_label, {"strict": False})
  for issue in res.get("panel_bleeds", []) + res.get("canvas_bleeds", []) + res.get("overlaps", []):
    print(f"[LAYOUT WARN] {issue}")
  return res
