"""Renders 06_velkscala_castle_verification.png comparing CASTLE reconciled Velkscala
total and rural population rasters across four canonical epochs (2000 BCE - 2025 CE).
"""

import json
import os
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.ticker as mticker
from matplotlib.collections import LineCollection


SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
DOMAIN_DIR = os.path.join(
  SVEA_ROOT,
  "histmap", "1.data_raw", "population_regional", "CASTLE", "_shared", "sites_korea_japan"
)
VELK_DIR = os.path.join(SVEA_ROOT, "histmap", "2.data_cleaning", "population_Velkscala")
SHARED_GIS_CACHE = os.path.join(
  SVEA_ROOT,
  "histmap", "1.data_raw", "population_regional", "_shared", "_gis_cache"
)
INDUS_GIS_CACHE = os.path.join(
  SVEA_ROOT,
  "histmap", "1.data_raw", "population_regional", "INDUS", "_shared", "_gis_cache"
)
OUT_PNG = os.path.join(DOMAIN_DIR, "diagnostics_visual", "06_velkscala_castle_verification.png")

LON_MIN, LON_MAX = 123.5, 147.5
LAT_MIN, LAT_MAX = 23.5, 46.0


def format_plain_log_tick(arg0_val, arg1_pos=None):
  val = float(arg0_val)
  if not np.isfinite(val) or val <= 0.0:
    return ""
  if val >= 1e6:
    return f"{val/1e6:.1f}".rstrip("0").rstrip(".").replace(".", ",") + "M"
  if val >= 1e3:
    return f"{val/1e3:.1f}".rstrip("0").rstrip(".").replace(".", ",") + "k"
  if val >= 1.0:
    if abs(val - round(val)) < 1e-6:
      return str(int(round(val)))
    return f"{val:.1f}".rstrip("0").rstrip(".").replace(".", ",")
  return f"{val:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def decode_float32_png(arg0_path):
  raw = np.asarray(Image.open(arg0_path).convert("RGBA"), dtype=np.uint8)
  nonzero = (raw[:, :, 0] > 0) | (raw[:, :, 1] > 0) | (raw[:, :, 2] > 0) | (raw[:, :, 3] > 0)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
  valid = nonzero & np.isfinite(f32) & (f32 > 0.0)
  return np.where(valid, f32, 0.0)


def resolve_ne_geojson(arg0_filename):
  for base in (SHARED_GIS_CACHE, INDUS_GIS_CACHE):
    cand = os.path.join(base, arg0_filename)
    if os.path.isfile(cand):
      return cand
  return ""


def extract_lines(arg0_path):
  if not arg0_path or not os.path.isfile(arg0_path):
    return []
  gj = json.load(open(arg0_path, "r", encoding="utf-8"))
  segs = []

  def accept(coords):
    pts = [(float(p[0]), float(p[1])) for p in coords if len(p) >= 2]
    if len(pts) < 2:
      return
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    if max(xs) < LON_MIN or min(xs) > LON_MAX or max(ys) < LAT_MIN or min(ys) > LAT_MAX:
      return
    segs.append(pts)

  for feat in gj.get("features", []):
    geom = feat.get("geometry") or {}
    gt = geom.get("type")
    cc = geom.get("coordinates") or []
    if gt == "LineString":
      accept(cc)
    elif gt == "MultiLineString":
      for line in cc:
        accept(line)
    elif gt == "Polygon":
      for ring in cc:
        accept(ring)
    elif gt == "MultiPolygon":
      for poly in cc:
        for ring in poly:
          accept(ring)
  return segs


def main():
  h, w = 2160, 4320
  r0 = max(0, int((90.0 - LAT_MAX) * h / 180.0))
  r1 = min(h, int((90.0 - LAT_MIN) * h / 180.0))
  c0 = max(0, int((LON_MIN + 180.0) * w / 360.0))
  c1 = min(w, int((LON_MAX + 180.0) * w / 360.0))
  extent = [
    -180.0 + c0 * 360.0 / w,
    -180.0 + c1 * 360.0 / w,
    90.0 - r1 * 180.0 / h,
    90.0 - r0 * 180.0 / h,
  ]
  mid_lat = 0.5 * (LAT_MIN + LAT_MAX)
  aspect = 1.0 / max(0.25, float(np.cos(np.radians(mid_lat))))

  coast = extract_lines(resolve_ne_geojson("ne_50m_coastline.geojson"))
  rivers = extract_lines(resolve_ne_geojson("ne_50m_rivers_lake_centerlines.geojson"))
  borders = extract_lines(resolve_ne_geojson("ne_50m_admin_0_boundary_lines_land.geojson"))

  panels = [
    ("A. Velkscala Total Population — 2000 BCE (Middle Jomon & Chulmun)", os.path.join(VELK_DIR, "population_rasters", "population_-2000.png"), 0.5, 2500.0),
    ("B. Velkscala Total Population — 1600 CE (Edo & Joseon Transition)", os.path.join(VELK_DIR, "population_rasters", "population_1600.png"), 5.0, 50000.0),
    ("C. Velkscala Rural Population — 1900 CE (Meiji & Late Joseon)", os.path.join(VELK_DIR, "population_rural_rasters", "population_rural_1900.png"), 5.0, 80000.0),
    ("D. Velkscala Total Population — 2025 CE (Modern Urban–Rural Synthesis)", os.path.join(VELK_DIR, "population_rasters", "population_2025.png"), 10.0, 500000.0),
  ]

  plt.rcdefaults()
  fig, axes = plt.subplots(2, 2, figsize=(15, 11.5), dpi=300)
  log_fmt = mticker.FuncFormatter(format_plain_log_tick)
  cmap = plt.get_cmap("magma").copy()
  cmap.set_bad("#0d1520")

  for ax, (title, fp, vmin, vmax) in zip(axes.flat, panels):
    arr = decode_float32_png(fp)[r0:r1, c0:c1]
    masked = np.where(arr > 0.0, arr, np.nan)
    im = ax.imshow(
      masked,
      extent=extent,
      origin="upper",
      cmap=cmap,
      norm=mcolors.LogNorm(vmin=vmin, vmax=vmax),
      interpolation="nearest",
    )
    if rivers:
      ax.add_collection(LineCollection(rivers, colors="#4ecdc4", linewidths=0.35, alpha=0.45))
    if coast:
      ax.add_collection(LineCollection(coast, colors="#d6e4f0", linewidths=0.45, alpha=0.75))
    if borders:
      ax.add_collection(LineCollection(borders, colors="#f7fff7", linewidths=0.35, linestyles="--", alpha=0.40))
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_aspect(aspect)
    ax.set_facecolor("#0d1520")
    ax.set_title(title, fontsize=10.5, fontweight="bold", pad=6)
    ax.set_xlabel("Longitude (°E)", fontsize=8.5)
    ax.set_ylabel("Latitude (°N)", fontsize=8.5)
    ax.tick_params(labelsize=8)
    cb = fig.colorbar(im, ax=ax, fraction=0.042, pad=0.025)
    cb.ax.yaxis.set_major_formatter(log_fmt)
    cb.ax.tick_params(labelsize=7.5)
    cb.set_label("Persons / 5-arcmin cell", fontsize=8)

  fig.suptitle(
    "Project CASTLE — Reconciled Velkscala Total & Rural Surfaces Verification (2000 BCE – 2025 CE)",
    fontsize=13,
    fontweight="bold",
    y=0.985,
  )
  fig.subplots_adjust(left=0.055, right=0.955, top=0.935, bottom=0.055, wspace=0.22, hspace=0.22)
  os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
  fig.savefig(OUT_PNG, dpi=300)
  plt.close(fig)
  print(f"Saved {OUT_PNG} ({os.path.getsize(OUT_PNG)} bytes)")


if __name__ == "__main__":
  main()
