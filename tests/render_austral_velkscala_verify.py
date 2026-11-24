# -*- coding: utf-8 -*-
"""Refresh 06_velkscala_austral_verification.png from newly rebuilt Stage E Velkscala rasters & 13_austral shards."""

import glob
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np
from PIL import Image

SVEA_ROOT = pathlib.Path(r"f:\Active Projects\Project 1509 - SVEA")
AUSTRAL_DIR = SVEA_ROOT / "histmap/1.data_raw/population_regional/AUSTRAL"
VELK_POP_DIR = SVEA_ROOT / "histmap/2.data_cleaning/population_Velkscala/population_rasters"
VELK_RUR_DIR = SVEA_ROOT / "histmap/2.data_cleaning/population_Velkscala/population_rural_rasters"
STAD_URB_DIR = SVEA_ROOT / "histmap/2.data_cleaning/population_Stadester/stadester_urban_rasters"
SHARDS_DIR = SVEA_ROOT / "histmap/3.data_transform/population_Stadester.transform/stadester"
OUT_PATH = AUSTRAL_DIR / "_shared/sites_austral_oceania/diagnostics_visual/06_velkscala_austral_verification.png"


def load_f32_png (arg0_path):
  img = Image.open(arg0_path).convert("RGBA")
  arr = np.array(img, dtype=np.uint8)
  f32 = np.ascontiguousarray(arr).view(np.dtype(">f4")).reshape(arr.shape[0], arr.shape[1])
  f32 = np.where(np.isfinite(f32) & (f32 > 0.0) & (f32 < 1e9), f32, 0.0)
  return f32


def pacific_crop (arg0_f32):
  # 4320x2160 equirectangular: lon in [-180, 180], lat in [90, -90]
  # Crop Pacific-centred 108E..255E (108E..105W), lat 22N..50S
  # cols: 108E -> (108+180)*12 = 3456..4320, plus 0..(255-180)*12 = 0..900
  r0 = int((90 - 22) * 12)   # 816
  r1 = int((90 + 50) * 12)   # 1680
  c_west = int((108 + 180) * 12)  # 3456
  c_east = int((255 - 180) * 12)  # 900
  left = arg0_f32[r0:r1, c_west:4320]
  right = arg0_f32[r0:r1, 0:c_east]
  return np.concatenate([left, right], axis=1)


def load_austral_cities ():
  cities = {}
  for sp in sorted(glob.glob(str(SHARDS_DIR / "13_austral*.json"))):
    cities.update(json.load(open(sp, encoding="utf-8")))
  return cities


def get_active_for_year (arg0_cities, arg1_yr):
  yr_s = str(arg1_yr)
  pts = []
  for k, c in arg0_cities.items():
    co = c.get("coords")
    pop = c.get("population") or {}
    if not co or len(co) < 2 or yr_s not in pop:
      continue
    val = float(pop[yr_s] or 0)
    if val <= 0:
      continue
    lat, lon = float(co[0]), float(co[1])
    lon360 = lon if lon >= 0 else lon + 360.0
    if 108.0 <= lon360 <= 255.0 and -50.0 <= lat <= 22.0:
      pts.append((val, str(c.get("name") or k), lon360, lat))
  pts.sort(key=lambda t: (-t[0], t[1]))
  return pts


def fmt_pop (arg0_v):
  if arg0_v >= 1_000_000:
    return f"{arg0_v/1_000_000:.2f}M".replace(".", ",")
  if arg0_v >= 1_000:
    return f"{arg0_v/1_000:.1f}k".replace(".", ",")
  return str(int(round(arg0_v)))


def main ():
  cities = load_austral_cities()
  panels = [
    (VELK_POP_DIR / "population_1000.png", 1000, "1000 AD — Velkscala Total + Settlements", "inferno", True),
    (VELK_POP_DIR / "population_1800.png", 1800, "1800 AD — Velkscala Total + Settlements", "inferno", True),
    (VELK_POP_DIR / "population_1900.png", 1900, "1900 AD — Velkscala Total + Settlements", "inferno", True),
    (VELK_POP_DIR / "population_2000.png", 2000, "2000 AD — Velkscala Total + Settlements", "inferno", True),
    (VELK_RUR_DIR / "population_rural_2000.png", 2000, "2000 AD — Velkscala Rural (Zero Swiss-Cheese Check)", "viridis", False),
    (STAD_URB_DIR / "stadester_urban_2000.png", 2000, "2000 AD — Velkscala Urban + Micro-Island Floor", "inferno", True),
  ]

  fig, axes = plt.subplots(2, 3, figsize=(18, 10.5), dpi=200, facecolor="#0b1220")
  plt.subplots_adjust(left=0.03, right=0.98, top=0.90, bottom=0.11, wspace=0.08, hspace=0.18)
  last_im = None

  for idx, (rpath, yr, title, cmap_nm, show_pts) in enumerate(panels):
    ax = axes[idx // 3, idx % 3]
    ax.set_facecolor("#0f172a")
    f32 = load_f32_png(rpath)
    crop = pacific_crop(f32)
    s_tot = float(crop.sum())
    act_px = int((crop > 0).sum())
    pts = get_active_for_year(cities, yr)

    masked = np.ma.masked_where(crop <= 0.01, np.clip(crop, 0.01, 20000.0))
    im = ax.imshow(
      masked, extent=[108.0, 255.0, -50.0, 22.0],
      origin="upper", cmap=cmap_nm, norm=LogNorm(vmin=0.01, vmax=15000.0), alpha=0.95, zorder=2
    )
    if cmap_nm == "inferno":
      last_im = im

    ax.axvline(180.0, color="#475569", lw=0.7, ls="--", zorder=3)
    if show_pts and pts:
      xs = [p[2] for p in pts]
      ys = [p[3] for p in pts]
      ax.scatter(xs, ys, s=3.2, c="#38bdf8", alpha=0.55, edgecolors="none", zorder=4)
      # Label top 6 well-separated settlements
      placed = []
      for val, nm, lx, ly in pts[:80]:
        if "(Metro)" in nm:
          continue
        if any(abs(lx - px) < 16.0 and abs(ly - py) < 7.5 for px, py in placed):
          continue
        placed.append((lx, ly))
        ax.annotate(
          f"{nm} ({fmt_pop(val)})",
          xy=(lx, ly), xytext=(lx + 2.5, ly + 2.0),
          fontsize=6.5, color="#f8fafc", fontweight="bold",
          bbox=dict(boxstyle="round,pad=0.2", fc="#0f172a", ec="#38bdf8", alpha=0.82, lw=0.6),
          arrowprops=dict(arrowstyle="-", color="#38bdf8", lw=0.5),
          zorder=5
        )
        if len(placed) >= 6:
          break

    ax.set_xlim(108.0, 255.0)
    ax.set_ylim(-50.0, 22.0)
    ax.set_xticks([120, 150, 180, 210, 240])
    ax.set_xticklabels(["120°E", "150°E", "180°", "150°W", "120°W"], fontsize=7, color="#94a3b8")
    ax.set_yticks([-40, -20, 0, 20])
    ax.set_yticklabels(["40°S", "20°S", "0°", "20°N"], fontsize=7, color="#94a3b8")
    for sp in ax.spines.values():
      sp.set_color("#334155")
    ax.set_title(f"{title}\n(sum={fmt_pop(s_tot)}, active_px={act_px:,}, n_setts={len(pts):,})", fontsize=8.8, color="#f1f5f9", pad=5)

  if last_im is not None:
    cax = fig.add_axes([0.28, 0.045, 0.44, 0.02])
    cb = fig.colorbar(last_im, cax=cax, orientation="horizontal")
    cb.ax.tick_params(labelsize=7.5, colors="#cbd5e1")
    cb.set_label("Population per 5-arcminute pixel (log scale, Pacific-centred 108°E–105°W)", fontsize=8.5, color="#e2e8f0")

  fig.suptitle("Project AUSTRAL (Oceania) — Reconciled Stage E Velkscala Total, Rural & Urban Surface Verification (1000–2000 AD)", fontsize=12.5, color="#f8fafc", fontweight="bold", y=0.96)
  fig.savefig(OUT_PATH, dpi=200, facecolor=fig.get_facecolor())
  plt.close(fig)
  print("Saved refreshed Velkscala verification figure:", OUT_PATH)


if __name__ == "__main__":
  main()
