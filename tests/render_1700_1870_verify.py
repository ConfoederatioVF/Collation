# -*- coding: utf-8 -*-
"""Temporary QA renderer for CENTAUR-II 1700-1790 & 1790-1870 county census + bleeding frontier surfaces."""

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np
from PIL import Image

SVEA_ROOT = pathlib.Path(__file__).resolve().parents[1]
CENTAUR_DIR = SVEA_ROOT / "histmap/1.data_raw/population_regional/CENTAUR"
SHARED_DIR = CENTAUR_DIR.parent / "_shared"
GIS_DIR = CENTAUR_DIR / "_shared/_gis_cache"
VELK_DIR = SVEA_ROOT / "histmap/2.data_cleaning/population_Velkscala/population_rasters"
HYDE_DIR = SVEA_ROOT / "histmap/2.data_cleaning/landuse_HYDE/rasters"

for p_s in (str(SHARED_DIR), str(GIS_DIR)):
  if p_s not in sys.path:
    sys.path.insert(0, p_s)

import centaur_map_helper as cmh
import viscount_plot_utils as vpu


def load_land_area():
  p = SVEA_ROOT / "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png"
  arr = np.asarray(Image.open(p).convert("RGBA"), dtype=np.uint8)
  raw = np.ascontiguousarray(arr).view(">f4")[..., 0]
  return np.where(np.isfinite(raw) & (raw > 0), raw, np.nan)


def lonlat_slice(f32_grid, lon_w, lon_e, lat_s, lat_n):
  c0 = max(0, int(round((lon_w + 180.0) * 12.0)))
  c1 = min(4320, int(round((lon_e + 180.0) * 12.0)))
  r0 = max(0, int(round((90.0 - lat_n) * 12.0)))
  r1 = min(2160, int(round((90.0 - lat_s) * 12.0)))
  return f32_grid[r0:r1, c0:c1], [lon_w, lon_e, lat_s, lat_n]


def print_diagnostics(area_grid):
  c0, c1 = int((-95 + 180) * 12), int((-65 + 180) * 12)
  r0, r1 = int((90 - 50) * 12), int((90 - 25) * 12)
  print("=== Sharpness & Frontier Diagnostics (Velkscala vs raw HYDE) ===")
  for yr in [1600, 1700, 1720, 1750, 1770, 1790, 1800, 1820, 1850, 1860, 1870, 1880, 1890, 1900]:
    vp = VELK_DIR / f"population_{yr}.png"
    hp = HYDE_DIR / f"popc_{yr}AD.png"
    if not vp.exists():
      continue
    v_arr = cmh.load_f32_raster(vp)[r0:r1, c0:c1] / np.maximum(1.0, area_grid[r0:r1, c0:c1])
    h_arr = cmh.load_f32_raster(hp)[r0:r1, c0:c1] / np.maximum(1.0, area_grid[r0:r1, c0:c1]) if hp.exists() else None

    def grad_norm(g):
      m = g > 0.05
      if m.sum() < 50:
        return 0.0
      lg = np.log10(np.maximum(1e-4, g))
      dx = np.abs(lg[:, 1:] - lg[:, :-1])[m[:, 1:] & m[:, :-1]]
      dy = np.abs(lg[1:, :] - lg[:-1, :])[m[1:, :] & m[:-1, :]]
      return float(0.5 * (dx.mean() + dy.mean()))

    vg = grad_norm(v_arr)
    hg = grad_norm(h_arr) if h_arr is not None else 0.0
    print(f"  yr={yr:4d} | Velk_grad={vg:.3f} | HYDE_grad={hg:.3f} | ratio={(vg / hg if hg > 0 else 0):.2f}x")


def render_sheet_lonlat(panels, out_path, title, bbox_default, vmax_dens=120.0, area_grid=None):
  fig, axes = plt.subplots(2, 3, figsize=(15.5, 9.6), dpi=220)
  plt.subplots_adjust(left=0.03, right=0.98, top=0.90, bottom=0.10, wspace=0.08, hspace=0.14)
  last_im = None
  for idx, item in enumerate(panels):
    yr, plbl = item[0], item[1]
    bbox = item[2] if len(item) > 2 else bbox_default
    lon_w, lon_e, lat_s, lat_n = bbox
    ax = axes[idx // 3, idx % 3]
    ax.set_facecolor("#0f172a")
    rp = VELK_DIR / f"population_{yr}.png"
    if rp.exists():
      f32 = cmh.load_f32_raster(rp)
      sub_p, ext = lonlat_slice(f32, lon_w, lon_e, lat_s, lat_n)
      sub_a, _ = lonlat_slice(area_grid, lon_w, lon_e, lat_s, lat_n)
      dens = np.where(np.isfinite(sub_a) & (sub_p > 0), sub_p / np.maximum(1.0, sub_a), np.nan)
      last_im = ax.imshow(
        np.ma.masked_invalid(np.clip(dens, 1e-3, vmax_dens)),
        extent=ext, origin="upper", cmap="magma",
        norm=LogNorm(vmin=0.005, vmax=vmax_dens), aspect="auto", interpolation="nearest"
      )
      ocean = np.where(~np.isfinite(sub_a), 1.0, np.nan)
      ax.imshow(ocean, extent=ext, origin="upper", cmap="Blues_r", vmin=0, vmax=3, aspect="auto", alpha=0.35)
    ax.set_title(plbl, fontsize=10.0, pad=5, fontweight="bold")
    ax.set_xlabel("Longitude", fontsize=7.5)
    ax.set_ylabel("Latitude", fontsize=7.5)
    ax.tick_params(labelsize=7.0)
  if last_im is not None:
    cax = fig.add_axes([0.28, 0.035, 0.44, 0.022])
    cb = fig.colorbar(last_im, cax=cax, orientation="horizontal")
    cb.ax.tick_params(labelsize=8.0)
    cb.set_label("Population density (inhabitants / km2, log10 scale)", fontsize=9.0)
  fig.suptitle(title, fontsize=12.5, fontweight="bold", y=0.96)
  fig.savefig(out_path, dpi=220)
  plt.close(fig)
  print("Saved:", out_path)


def main():
  area_grid = load_land_area()
  print_diagnostics(area_grid)

  out1 = SVEA_ROOT / "tests/verify_1700_1790_colonial_expansion.png"
  render_sheet_lonlat(
    [(1700, "1700AD: Early Tidewater & St. Lawrence"),
     (1720, "1720AD: Chesapeake & New England Consolidation"),
     (1740, "1740AD: Valley & Piedmont Push"),
     (1750, "1750AD: Pre-Seven Years' War Frontier"),
     (1770, "1770AD: Trans-Appalachian & Maritimes"),
     (1790, "1790AD: First US Census & Loyalist Canada")],
    out1,
    "CENTAUR-II Colonial America & Canada Areal County Census + Frontier (1700-1790AD)",
    (-92.0, -56.0, 26.0, 51.0),
    vmax_dens=80.0, area_grid=area_grid
  )

  out2 = SVEA_ROOT / "tests/verify_1790_1870_westward_settlement.png"
  render_sheet_lonlat(
    [(1790, "1790AD: Eastern Seaboard & Early Republic"),
     (1800, "1800AD: Northwest Territory & Indigenous Heartland"),
     (1820, "1820AD: Ohio-Mississippi Wave & Missouri"),
     (1840, "1840AD: Great Lakes, Cotton Belt & Plains"),
     (1850, "1850AD: California Gold Rush, Texas & Upper Canada"),
     (1870, "1870AD: Post-Civil War US & Confederation Canada")],
    out2,
    "CENTAUR-II United States & Canada County Census + Bleeding Frontier (1790-1870AD)",
    (-126.0, -60.0, 24.0, 53.0),
    vmax_dens=120.0, area_grid=area_grid
  )

  out3 = SVEA_ROOT / "tests/verify_1700_1870_closeups.png"
  render_sheet_lonlat(
    [(1750, "1750AD Close-up: Mid-Atlantic & New England", (-82.0, -69.5, 36.5, 44.5)),
     (1750, "1750AD Close-up: St. Lawrence & Acadia", (-76.5, -60.0, 43.0, 50.0)),
     (1800, "1800AD Close-up: Ohio-Michigan-Illinois Frontier", (-91.5, -77.5, 34.5, 46.5)),
     (1850, "1850AD Close-up: NE Seaboard, Ohio Valley & ON/QC", (-88.0, -69.0, 37.5, 47.5)),
     (1850, "1850AD Close-up: California & Oregon Frontier", (-125.0, -112.0, 32.0, 46.5)),
     (1880, "1880AD Continuity Check: East-Central & Canada", (-92.0, -68.0, 35.0, 48.0))],
    out3,
    "CENTAUR-II High-Resolution 5-Arcminute County Sharpness & Frontier Continuity Close-ups",
    (-92.0, -68.0, 35.0, 48.0),
    vmax_dens=160.0, area_grid=area_grid
  )


if __name__ == "__main__":
  main()
