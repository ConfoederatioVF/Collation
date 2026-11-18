# -*- coding: utf-8 -*-
"""Render Stage E Velkscala verification sheet (06) and multi-epoch Dataview verification raster."""

import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

SVEA_ROOT = pathlib.Path(__file__).resolve().parents[1]
CENTAUR_DIR = SVEA_ROOT / "histmap/1.data_raw/population_regional/CENTAUR"
SHARED_DIR = CENTAUR_DIR.parent / "_shared"
GIS_DIR = CENTAUR_DIR / "_shared/_gis_cache"
VELK_DIR = SVEA_ROOT / "histmap/2.data_cleaning/population_Velkscala/population_rasters"

for p_s in (str(SHARED_DIR), str(GIS_DIR)):
  if p_s not in sys.path:
    sys.path.insert(0, p_s)

import centaur_map_helper as cmh
import viscount_plot_utils as vpu


def _load_active_setts_for_year (arg0_yr):
  """Collects active CENTAUR settlements at arg0_yr sorted by population descending."""
  yr_i = int(arg0_yr)
  out = []
  for p in sorted(CENTAUR_DIR.rglob("*_settlements.json")):
    if yr_i <= 1600 and "4.colonial_america" in str(p):
      continue
    if yr_i < 1783 and "5.modern_canada" in str(p):
      continue
    data = json.loads(p.read_text(encoding="utf-8"))
    items = data.values() if isinstance(data, dict) else data
    for s in items:
      coords = s.get("coords")
      if not isinstance(coords, list) or len(coords) < 2:
        continue
      fy = s.get("foundation_year") or s.get("found.yr")
      if fy is not None and yr_i < int(fy):
        continue
      pops = s.get("population") or {}
      if str(yr_i) in pops:
        val = float(pops[str(yr_i)])
      else:
        ys = sorted(int(k) for k in pops.keys())
        if not ys or yr_i < ys[0] or yr_i > ys[-1]:
          continue
        near_y = min(ys, key=lambda y: abs(y - yr_i))
        if abs(near_y - yr_i) > 150:
          continue
        val = float(pops[str(near_y)])
      if val > 0:
        nm = str(s.get("name", "")).strip()
        out.append((val, nm, float(coords[1]), float(coords[0])))
  out.sort(key=lambda t: (-t[0], t[1]))
  seen = set()
  uniq = []
  for val, nm, lon, lat in out:
    if nm in seen:
      continue
    seen.add(nm)
    uniq.append((val, f"{nm} ({vpu.format_semantic_population(val)})", lon, lat))
  return uniq


def render_grid (arg0_panels, arg1_out_path, arg2_title, arg3_overlay_setts=False):
  """Renders a 2x3 Equal-Area Velkscala verification figure."""
  plt.rcdefaults()
  plt.style.use("default")
  fig, axes = plt.subplots(2, 3, figsize=(15.6, 10.0), dpi=280)
  plt.subplots_adjust(left=0.02, right=0.98, top=0.90, bottom=0.11, wspace=0.04, hspace=0.12)
  xlim_na = (-4450.0, 3250.0)
  ylim_na = (-2050.0, 3900.0)
  last_im = None

  for idx, (yr, plbl) in enumerate(arg0_panels):
    ax = axes[idx // 3, idx % 3]
    cmh.draw_basemap(ax, cmh.PROJ_NA, arg3_dark=True)
    r_p = VELK_DIR / f"population_{yr}.png"
    if r_p.exists():
      f32 = cmh.load_f32_raster(r_p)
      grd = cmh.reproject_f32_raster(f32, cmh.PROJ_NA, xlim_na, ylim_na, arg4_width_px=960, arg5_height_px=740)
      grd_m = np.ma.masked_where(grd <= 0.005, np.clip(grd, 0.005, 5000.0))
      last_im = ax.imshow(
        grd_m, extent=[xlim_na[0], xlim_na[1], ylim_na[0], ylim_na[1]],
        origin="upper", cmap="viridis", norm=LogNorm(vmin=0.01, vmax=2000.0), alpha=0.90, zorder=3.5
      )
    byr = max(1000, min(1890, yr)) if yr >= 1000 else 1000
    cmh.draw_historical_borders(ax, cmh.PROJ_NA, byr, arg4_color="#94a3b8")
    ax.set_xlim(*xlim_na)
    ax.set_ylim(*ylim_na)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    cmh.draw_inline_graticule(ax, cmh.PROJ_NA, xlim_na, ylim_na, [25, 45, 65], [-160, -120, -80, -40])
    vpu.apply_viscount_style(ax)
    ax.set_title(plbl, fontsize=9.0, pad=4)

    if arg3_overlay_setts:
      cands = _load_active_setts_for_year(yr)
      items = [(lbl, lon, lat) for _, lbl, lon, lat in cands[:36]]
      cmh.place_bbox_callouts(fig, ax, items, cmh.PROJ_NA, xlim_na, ylim_na, arg6_max_labels=6, arg7_min_sep_px=45.0, arg8_fontsize=5.8)

  if last_im is not None:
    cax = fig.add_axes([0.30, 0.045, 0.40, 0.022])
    cb = fig.colorbar(last_im, cax=cax, orientation="horizontal")
    vpu.apply_human_colorbar_ticks(cb, True)
    cb.ax.tick_params(labelsize=7.5)
    cb.set_label("Population per 5-arcminute pixel (log scale)", fontsize=8.4)

  fig.suptitle(arg2_title, fontsize=11.4, y=0.96)
  cmh.verify_zero_text_overlaps(fig, arg1_out_path.name)
  vpu.save_viscount_figure(fig, arg1_out_path, 280)
  plt.close(fig)


def main ():
  out06 = CENTAUR_DIR / "_shared/sites_northern_america/diagnostics_visual/06_velkscala_centaur_verification.png"
  render_grid(
    [(-4000, "4000BC: Middle Archaic"), (0, "0AD: Woodland and Puebloan"), (1200, "1200AD: Mississippian Peak"),
     (1750, "1750AD: Colonial Frontier"), (1920, "1920AD: Industrial Urbanisation"), (2020, "2020AD: Contemporary Distribution")],
    out06,
    "CENTAUR-II Reconciled Velkscala Population Surface Across Six Epochs (4000BC-2020AD)",
    arg3_overlay_setts=False
  )
  out_dv = SVEA_ROOT / "tests/verify_centaur_dataview_epochs.png"
  render_grid(
    [(-400, "400BC: Early Woodland"), (100, "100AD: Hopewell Horizon"), (1200, "1200AD: Cahokia and Chaco"),
     (1500, "1500AD: Late Pre-Contact"), (1750, "1750AD: Pre-1754 Colonial"), (1800, "1800AD: Early Republican")],
    out_dv,
    "CENTAUR-II Epoch Continuity and Active Settlement Alignment (-400BC to 1800AD)",
    arg3_overlay_setts=True
  )


if __name__ == "__main__":
  main()
