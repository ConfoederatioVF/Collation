"""Renders 06_velkscala_mandala_verification.png (300 DPI 4-panel cartographic audit of population_Velkscala
rasters across MANDALA: -2000BC, 1000AD, 1600AD, 1950AD) for Gatekeeper E2 visual inspection."""

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.collections import LineCollection
import numpy as np
from PIL import Image

SVEA = r"f:\Active Projects\Project 1509 - SVEA"
MANDALA = os.path.join(SVEA, "histmap", "1.data_raw", "population_regional", "MANDALA")
SITES_DIR = os.path.join(MANDALA, "_shared", "sites_mandala_southeast_asia")
VELK_DIR = os.path.join(SVEA, "histmap", "2.data_cleaning", "population_Velkscala", "population_rasters")
MASK_PNG = os.path.join(SITES_DIR, "config", "mandala_domain_mask.png")
OUT_PNG = os.path.join(SITES_DIR, "diagnostics_visual", "06_velkscala_mandala_verification.png")
GIS_DIR = os.path.join(SVEA, "histmap", "1.data_raw", "population_regional", "_shared", "_gis_cache")


def decode_f32(p):
  raw = np.asarray(Image.open(p).convert("RGBA"), dtype=np.uint8)
  nz = (raw[:, :, 0] > 0) | (raw[:, :, 1] > 0) | (raw[:, :, 2] > 0) | (raw[:, :, 3] > 0)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
  valid = nz & np.isfinite(f32) & (f32 > 0.0)
  return np.where(valid, f32, 0.0)


def fmt_pop(v, pos=None):
  if not np.isfinite(v) or v <= 0:
    return ""
  if v >= 1e6:
    return f"{v/1e6:.1f}".rstrip("0").rstrip(".").replace(".", ",") + "M"
  if v >= 1e3:
    return f"{v/1e3:.1f}".rstrip("0").rstrip(".").replace(".", ",") + "k"
  return f"{v:.1f}".rstrip("0").rstrip(".").replace(".", ",")


def load_lines(p, lon_b, lat_b):
  if not os.path.isfile(p):
    return []
  gj = json.load(open(p, encoding="utf-8"))
  segs = []
  def acc(c):
    pts = [(float(x[0]), float(x[1])) for x in c if len(x) >= 2]
    if len(pts) < 2:
      return
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    if max(xs) < lon_b[0] or min(xs) > lon_b[1] or max(ys) < lat_b[0] or min(ys) > lat_b[1]:
      return
    segs.append(pts)
  for f in gj.get("features", []):
    g = f.get("geometry") or {}
    t, c = g.get("type"), g.get("coordinates") or []
    if t == "LineString":
      acc(c)
    elif t == "MultiLineString":
      for l in c:
        acc(l)
  return segs


def main():
  dm = np.asarray(Image.open(MASK_PNG).convert("RGBA"), dtype=np.uint8)
  mask = (dm[:, :, 3] > 0) & (dm[:, :, :3].sum(axis=2) > 0)
  rs, cs = np.where(mask)
  r0, r1 = max(0, int(rs.min()) - 6), min(2160, int(rs.max()) + 7)
  c0, c1 = max(0, int(cs.min()) - 6), min(4320, int(cs.max()) + 7)
  lon_min = -180.0 + c0 * 360.0 / 4320.0
  lon_max = -180.0 + c1 * 360.0 / 4320.0
  lat_max = 90.0 - r0 * 180.0 / 2160.0
  lat_min = 90.0 - r1 * 180.0 / 2160.0
  extent = [lon_min, lon_max, lat_min, lat_max]
  geo_aspect = 1.0 / max(0.25, float(np.cos(np.radians(0.5 * (lat_min + lat_max)))))

  coast = load_lines(os.path.join(GIS_DIR, "ne_50m_coastline.geojson"), (lon_min, lon_max), (lat_min, lat_max))
  rivers = load_lines(os.path.join(GIS_DIR, "ne_50m_rivers_lake_centerlines.geojson"), (lon_min, lon_max), (lat_min, lat_max))

  plt.rcdefaults()
  plt.style.use("default")
  fig, axes = plt.subplots(2, 2, figsize=(14, 9), dpi=300)
  years = [(-2000, "(A) Velkscala 2000BC (Neolithic-Bronze)"), (1000, "(B) Velkscala 1000AD (Angkor-Pagan-Kediri)"), (1600, "(C) Velkscala 1600AD (Age of Commerce)"), (1950, "(D) Velkscala 1950AD (Post-War Census Era)")]
  log_fmt = mticker.FuncFormatter(fmt_pop)

  for ax, (yr, title) in zip(axes.flat, years):
    p = os.path.join(VELK_DIR, f"population_{yr}.png")
    arr = decode_f32(p)
    sub = np.where(mask[r0:r1, c0:c1] & (arr[r0:r1, c0:c1] > 0), arr[r0:r1, c0:c1], np.nan)
    fin = sub[np.isfinite(sub)]
    tot = float(np.nansum(sub))
    vmin = max(0.05, float(np.nanpercentile(fin, 2))) if fin.size else 0.1
    vmax = max(vmin * 10.0, float(np.nanpercentile(fin, 99.5))) if fin.size else 1000.0
    im = ax.imshow(sub, origin="upper", extent=extent, cmap="magma", norm=mcolors.LogNorm(vmin=vmin, vmax=vmax))
    if coast:
      ax.add_collection(LineCollection(coast, colors="#333333", linewidths=0.45, alpha=0.7))
    if rivers:
      ax.add_collection(LineCollection(rivers, colors="#2b6cb0", linewidths=0.35, alpha=0.5))
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect(geo_aspect)
    ax.grid(True, alpha=0.25, linewidth=0.4)
    cb = fig.colorbar(im, ax=ax, fraction=0.036, pad=0.02, format=log_fmt, label="Inhabitants / 5' Cell")
    decades = [10.0 ** e for e in range(-1, 8) if vmin * 0.9 <= (10.0 ** e) <= vmax * 1.1]
    if len(decades) >= 2:
      cb.set_ticks(decades)
    cb.ax.yaxis.set_major_formatter(log_fmt)
    cb.ax.yaxis.set_minor_formatter(mticker.NullFormatter())
    ax.set_title(f"{title} | Sum={fmt_pop(tot)}")

  fig.suptitle("MANDALA (South-East Asia Excl. West New Guinea): Velkscala End-to-End Reconciliation Verification", fontsize=12, fontweight="bold")
  fig.tight_layout(rect=[0, 0, 1, 0.96])
  os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
  fig.savefig(OUT_PNG, dpi=300)
  plt.close(fig)
  print("Saved:", OUT_PNG)


if __name__ == "__main__":
  main()
