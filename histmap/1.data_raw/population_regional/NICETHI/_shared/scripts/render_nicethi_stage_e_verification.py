# -*- coding: utf-8 -*-
"""Render Stage E Velkscala optical verification figure (06_velkscala_nicethi_verification.png)
for Operation Viscount Project NICETHI (Sub-Saharan Africa, Madagascar & African Ocean Islands).

Uses Lambert Azimuthal Equal-Area projection centred on Sub-Saharan Africa (20.0, -4.0),
proper IEEE-754 big-endian float32 RGBA decoding (4-byte non-zero check, zero alpha-byte holes),
Natural Earth 10m vector coastlines/borders/rivers, human European log colorbar ticks,
and zero overlapping text.
"""

import json
import math
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.colors import LogNorm
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
from PIL import Image
from shapely.geometry import shape

SVEA_ROOT = pathlib.Path(__file__).resolve().parents[6]
NICETHI_DIR = SVEA_ROOT / "histmap/1.data_raw/population_regional/NICETHI"
SHARED_DIR = SVEA_ROOT / "histmap/1.data_raw/population_regional/_shared"
GIS_SHARED = SHARED_DIR / "_gis_cache"
VELK_DIR = SVEA_ROOT / "histmap/2.data_cleaning/population_Velkscala/population_rasters"
OUT_PNG = NICETHI_DIR / "_shared/sites_nicethi_africa/diagnostics_visual/06_velkscala_nicethi_verification.png"

if str(SHARED_DIR) not in sys.path:
  sys.path.insert(0, str(SHARED_DIR))

import viscount_plot_utils as vpu


class LambertAzimuthalEqualArea:
  """Spherical Lambert Azimuthal Equal-Area projection in kilometres."""

  def __init__ (self, arg0_lon0_deg, arg1_lat0_deg):
    self.lon0 = math.radians(float(arg0_lon0_deg))
    self.lat0 = math.radians(float(arg1_lat0_deg))
    self.sin_lat0 = math.sin(self.lat0)
    self.cos_lat0 = math.cos(self.lat0)
    self.r_km = 6371.0

  def fwd_arrays (self, arg0_lon_deg, arg1_lat_deg):
    lon = np.radians(arg0_lon_deg)
    lat = np.radians(arg1_lat_deg)
    dlon = lon - self.lon0
    sin_lat = np.sin(lat)
    cos_lat = np.cos(lat)
    denom = 1.0 + self.sin_lat0 * sin_lat + self.cos_lat0 * cos_lat * np.cos(dlon)
    k = np.sqrt(2.0 / np.maximum(1e-9, denom))
    x = self.r_km * k * cos_lat * np.sin(dlon)
    y = self.r_km * k * (self.cos_lat0 * sin_lat - self.sin_lat0 * cos_lat * np.cos(dlon))
    return x, y

  def inv_arrays (self, arg0_x_km, arg1_y_km):
    x = arg0_x_km / self.r_km
    y = arg1_y_km / self.r_km
    rho = np.hypot(x, y)
    c = 2.0 * np.arcsin(np.clip(0.5 * rho, 0.0, 1.0))
    sin_c = np.sin(c)
    cos_c = np.cos(c)
    safe_rho = np.where(rho > 1e-12, rho, 1.0)
    sin_lat = np.where(rho > 1e-12, cos_c * self.sin_lat0 + (y * sin_c * self.cos_lat0) / safe_rho, self.sin_lat0)
    lat = np.arcsin(np.clip(sin_lat, -1.0, 1.0))
    dlon = np.arctan2(x * sin_c, safe_rho * self.cos_lat0 * cos_c - y * self.sin_lat0 * sin_c)
    lon = self.lon0 + np.where(rho > 1e-12, dlon, 0.0)
    lon_deg = (np.degrees(lon) + 180.0) % 360.0 - 180.0
    lat_deg = np.degrees(lat)
    return lon_deg, lat_deg


def load_float32_png (arg0_path):
  """Decodes a 4-channel big-endian IEEE-754 float32 RGBA PNG safely (zero alpha-byte holes)."""
  im = Image.open(arg0_path).convert("RGBA")
  raw = np.asarray(im, dtype=np.uint8)
  nonzero = np.any(raw != 0, axis=2)
  vals = np.frombuffer(np.ascontiguousarray(raw).tobytes(), dtype=">f4").reshape(raw.shape[0], raw.shape[1])
  out = np.where(nonzero & np.isfinite(vals) & (vals > 0.0), vals, 0.0).astype(np.float32)
  return out


def reproject_f32_raster (arg0_f32, arg1_proj, arg2_xlim, arg3_ylim, arg4_w=820, arg5_h=820):
  """Reprojects a global 4320x2160 equirectangular float32 grid onto LAEA via nearest lookup."""
  h_src, w_src = arg0_f32.shape
  xs = np.linspace(arg2_xlim[0], arg2_xlim[1], arg4_w)
  ys = np.linspace(arg3_ylim[1], arg3_ylim[0], arg5_h)
  gx, gy = np.meshgrid(xs, ys)
  lon, lat = arg1_proj.inv_arrays(gx, gy)
  px = np.clip(np.floor((lon + 180.0) * (w_src / 360.0)).astype(np.int32), 0, w_src - 1)
  py = np.clip(np.floor((90.0 - lat) * (h_src / 180.0)).astype(np.int32), 0, h_src - 1)
  return arg0_f32[py, px]


def load_africa_vectors (arg0_proj):
  """Loads projected Natural Earth 10m land polygons, borders, and rivers for Africa & WIO."""
  land_polys = []
  border_segs = []
  river_segs = []

  countries_p = GIS_SHARED / "ne_10m_admin_0_countries.geojson"
  if countries_p.exists():
    gj = json.loads(countries_p.read_text(encoding="utf-8"))
    for feat in gj.get("features", []):
      geom = shape(feat["geometry"])
      minx, miny, maxx, maxy = geom.bounds
      if maxx < -30.0 or minx > 75.0 or maxy < -42.0 or miny > 38.0:
        continue
      geoms = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
      for poly in geoms:
        coords = np.asarray(poly.exterior.coords, dtype=np.float64)
        if len(coords) < 4:
          continue
        px, py = arg0_proj.fwd_arrays(coords[:, 0], coords[:, 1])
        pts = np.column_stack([px, py])
        land_polys.append(MplPolygon(pts, closed=True))
        border_segs.append(pts)

  rivers_p = GIS_SHARED / "ne_10m_rivers_lake_centerlines.geojson"
  if rivers_p.exists():
    gj = json.loads(rivers_p.read_text(encoding="utf-8"))
    for feat in gj.get("features", []):
      geom = shape(feat["geometry"])
      minx, miny, maxx, maxy = geom.bounds
      if maxx < -22.0 or minx > 62.0 or maxy < -38.0 or miny > 34.0:
        continue
      lines = [geom] if geom.geom_type == "LineString" else list(geom.geoms)
      for ln in lines:
        coords = np.asarray(ln.coords, dtype=np.float64)
        if len(coords) < 2:
          continue
        px, py = arg0_proj.fwd_arrays(coords[:, 0], coords[:, 1])
        river_segs.append(np.column_stack([px, py]))

  return land_polys, border_segs, river_segs


def draw_graticule (arg0_ax, arg1_proj):
  """Draws subtle projected latitude/longitude graticule lines."""
  lats = [-30, -15, 0, 15, 30]
  lons = [-20, 0, 20, 40, 60]
  segs = []
  for lat_v in lats:
    lo = np.linspace(-28.0, 66.0, 140)
    la = np.full_like(lo, float(lat_v))
    px, py = arg1_proj.fwd_arrays(lo, la)
    segs.append(np.column_stack([px, py]))
  for lon_v in lons:
    la = np.linspace(-40.0, 34.0, 140)
    lo = np.full_like(la, float(lon_v))
    px, py = arg1_proj.fwd_arrays(lo, la)
    segs.append(np.column_stack([px, py]))
  lc = LineCollection(segs, colors="#64748b", linewidths=0.35, linestyles=":", alpha=0.45, zorder=2.2)
  arg0_ax.add_collection(lc)


def main ():
  proj = LambertAzimuthalEqualArea(20.0, -3.5)
  xlim_af = (-4450.0, 4450.0)
  ylim_af = (-3850.0, 3850.0)

  panels = [
    (-2000, "2000BC: Kerma, Sahel & Pre-Bantu"),
    (0, "0AD: Meroe, Aksum & Iron Age Bantu"),
    (900, "900AD: Ghana, Kanem, Swahili & Great Lakes"),
    (1400, "1400AD: Mali, Ethiopia, Great Zimbabwe"),
    (1900, "1900AD: Colonial-Era Benchmarks"),
    (2020, "2020AD: Contemporary DEGURBA Surface"),
  ]

  land_polys, border_segs, river_segs = load_africa_vectors(proj)

  plt.rcdefaults()
  plt.style.use("default")
  fig, axes = plt.subplots(2, 3, figsize=(15.4, 11.4), dpi=280)
  plt.subplots_adjust(left=0.02, right=0.98, top=0.90, bottom=0.10, wspace=0.05, hspace=0.12)
  last_im = None

  for idx, (yr, plbl) in enumerate(panels):
    ax = axes[idx // 3, idx % 3]
    ax.set_facecolor("#0f172a")
    if land_polys:
      pc = PatchCollection(land_polys, facecolor="#1e293b", edgecolor="none", zorder=1.0)
      ax.add_collection(pc)

    r_p = VELK_DIR / f"population_{yr}.png"
    if r_p.exists():
      f32 = load_float32_png(r_p)
      grd = reproject_f32_raster(f32, proj, xlim_af, ylim_af, arg4_w=820, arg5_h=720)
      grd_m = np.ma.masked_where(grd <= 0.005, np.clip(grd, 0.005, 5000.0))
      last_im = ax.imshow(
        grd_m,
        extent=[xlim_af[0], xlim_af[1], ylim_af[0], ylim_af[1]],
        origin="upper",
        cmap="viridis",
        norm=LogNorm(vmin=0.01, vmax=2000.0),
        alpha=0.92,
        zorder=3.0,
      )

    if river_segs:
      ax.add_collection(LineCollection(river_segs, colors="#38bdf8", linewidths=0.32, alpha=0.40, zorder=3.6))
    if border_segs:
      ax.add_collection(LineCollection(border_segs, colors="#cbd5e1", linewidths=0.42, alpha=0.62, zorder=4.0))
    draw_graticule(ax, proj)

    ax.set_xlim(*xlim_af)
    ax.set_ylim(*ylim_af)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    vpu.apply_viscount_style(ax, {"grid": False})
    ax.set_title(plbl, fontsize=9.2, pad=5)

  if last_im is not None:
    cax = fig.add_axes([0.28, 0.042, 0.44, 0.020])
    cb = fig.colorbar(last_im, cax=cax, orientation="horizontal", format=vpu.euro_log_formatter(True))
    vpu.apply_human_colorbar_ticks(cb, True)
    cb.ax.tick_params(labelsize=8.0)
    cb.set_label("Population per 5-arcminute pixel (log scale)", fontsize=8.8)

  fig.suptitle(
    "Project NICETHI Reconciled Velkscala Population Surface & HANDBOOK Frontier Seam (2000BC-2020AD)",
    fontsize=11.8,
    y=0.96,
  )
  OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
  vpu.save_viscount_figure(fig, OUT_PNG, 280)
  plt.close(fig)
  print(f"[render_nicethi_stage_e_verification] Saved {OUT_PNG}")


if __name__ == "__main__":
  main()
