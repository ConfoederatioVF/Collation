"""Generates the 5 publication-grade root synthesis figures for Project MAGNETIC (`studies_on_population.Rmd`).

All figures use default Matplotlib styling (DejaVu Sans, 4-sided boxed axes), Albers Equal-Area
vector cartography (`PatchCollection`), reprojected Stage C continuous density rasters with plain
European log colorbars and strict zero-occlusion layout verification (`save_viscount_figure`).
"""

import json
import math
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch, Polygon as MplPolygon
import numpy as np
from PIL import Image
from shapely.geometry import shape
from shapely.ops import unary_union

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC")
SHARED = os.path.join(MAG_DIR, "_shared")
SCRIPTS_DIR = os.path.join(SHARED, "scripts")
SUBREG_DIR = os.path.join(SHARED, "_gis_cache", "chapter_subregions")
POP_DIR = os.path.join(SHARED, "sites_magnetic_europe", "2.population_rasters")
FIG_DIR = os.path.join(MAG_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

if SCRIPTS_DIR not in sys.path:
  sys.path.insert(0, SCRIPTS_DIR)

from magnetic_map_helper import (
  PROJ_EUROPE,
  PROJ_GREENLAND,
  apply_human_colorbar_ticks,
  apply_human_log_ticks,
  apply_viscount_style,
  draw_basemap,
  draw_graticule,
  euro_log_formatter,
  euro_tick_formatter,
  format_euro_number,
  format_mathtext_euro,
  format_semantic_population,
  geom_to_patches,
  load_basemap_cache,
  mute_rgb_hex,
  pad_projected_bounds,
  place_inbounds_callouts,
  prepare_and_project,
  save_viscount_figure,
)

GRID_W, GRID_H = 4320, 2160
EU_XLIM = (-1820.0, 1780.0)
EU_YLIM = (-1880.0, 2120.0)


def decode_velk_density_grid (arg0_png_path):
  """Decodes a 4320x2160 big-endian float32 RGBA Viscount population raster into inhabitants per cell."""
  arr = np.ascontiguousarray(Image.open(arg0_png_path).convert("RGBA"), dtype=np.uint8)
  vals = arr.view(">f4").reshape(arr.shape[:2])
  return np.where(np.isfinite(vals) & (vals > 0.0) & (vals < 1e8), vals, 0.0).astype(np.float32)


def sample_raster_to_albers (arg0_vals, arg1_proj, arg2_xlim, arg3_ylim, arg4_nx=480, arg5_ny=520):
  """Reprojects equirectangular population grid onto Albers Equal-Area canvas via inverse coordinates."""
  xs = np.linspace(arg2_xlim[0], arg2_xlim[1], arg4_nx)
  ys = np.linspace(arg3_ylim[0], arg3_ylim[1], arg5_ny)
  xx, yy = np.meshgrid(xs, ys)
  lons, lats = arg1_proj.inv_xy(xx, yy)
  cols = np.clip(np.floor((lons + 180.0) * GRID_W / 360.0).astype(np.int32), 0, GRID_W - 1)
  rows = np.clip(np.floor((90.0 - lats) * GRID_H / 180.0).astype(np.int32), 0, GRID_H - 1)
  sampled = arg0_vals[rows, cols]
  # Mask zero/ocean pixels as NaN so basemap shows cleanly underneath
  return np.where(sampled > 0.5, sampled, np.nan)


def render_fig1_hero_coverage (arg0_land_eu, arg1_riv_eu, arg2_land_gl, arg3_riv_gl):
  """Figure 1: 6-panel historical coverage & regional partitions across Europe (10000BC-2025)."""
  panels = [
    ("A. 10000–1000BC: Prehistoric & Bronze Age", "neolithic_and_bronze_age_europe"),
    ("B. 1000BC–400AD: Classical & Roman Europe", "iron_age_and_roman_europe"),
    ("C. 800–1347AD: Mediaeval Christendom & Iberia", "mediaeval_western_and_central_europe"),
    ("D. 1347–1500AD: Black Death & Late Mediaeval", "black_death_and_late_mediaeval_crisis"),
    ("E. 1500–1914: Early Modern & Industrial HGIS", "industrialisation_western_and_northern_europe"),
    ("F. 1945–2025: Contemporary European Censuses", "western_and_northern_europe_after_1945"),
  ]
  # Supplement multi-chapter pan-European snapshots for panels C, E and F
  extra_layers = {
    "mediaeval_western_and_central_europe": ["mediaeval_iberia", "mediaeval_scandinavia_and_north_atlantic", "mediaeval_east_central_baltic_balkans"],
    "iron_age_and_roman_europe": ["classical_greece_and_aegean", "free_germany_scandinavia_baltic_slavic"],
    "industrialisation_western_and_northern_europe": ["early_modern_nineteenth_century_southern_east_central_europe"],
    "western_and_northern_europe_after_1945": ["southern_europe_and_islands_after_1945", "east_central_balkans_baltic_after_1945"],
  }
  macro_palette = {
    0: "#6ca6c1", 1: "#7fb685", 2: "#e09f5a", 3: "#b288c0", 4: "#d67d79", 5: "#6db7b0",
    6: "#c9b46e", 7: "#8da0cb", 8: "#e5a3b3", 9: "#a3c478", 10: "#d4956a", 11: "#7d9fc2",
  }

  apply_viscount_style()
  fig, axes = plt.subplots(2, 3, figsize=(13.2, 8.2), dpi=300)
  for idx_p, (ax, (ptitle, primary_stem)) in enumerate(zip(axes.flat, panels)):
    apply_viscount_style(ax, {"grid": False})
    draw_basemap(ax, arg0_land_eu, arg1_riv_eu)
    stems = [primary_stem] + extra_layers.get(primary_stem, [])
    col_i = 0
    for st in stems:
      vp = os.path.join(SUBREG_DIR, f"{st}_subregions.geojson")
      if not os.path.isfile(vp):
        continue
      gj = json.load(open(vp, encoding="utf-8"))
      for feat in gj.get("features", []):
        geom_raw = feat.get("geometry")
        if not geom_raw:
          continue
        g = shape(geom_raw).buffer(0)
        if g.is_empty or g.centroid.x < -25.0:
          continue
        pg = prepare_and_project(g, PROJ_EUROPE, 0.35)
        ps = geom_to_patches(pg)
        if ps:
          fc = macro_palette[col_i % len(macro_palette)]
          ax.add_collection(PatchCollection(ps, facecolor=fc, edgecolor="#334155", linewidths=0.38, alpha=0.82, zorder=2.5))
          col_i += 1
    ax.set_xlim(*EU_XLIM)
    ax.set_ylim(*EU_YLIM)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    draw_graticule(ax, PROJ_EUROPE, EU_XLIM, EU_YLIM, [40, 50, 60, 70], [-10, 0, 10, 20, 30])
    ax.set_title(ptitle, fontsize=8.8, pad=5)

    # Greenland inset on Panel F to show full North Atlantic territorial scope
    if idx_p == 5:
      ax_gl = ax.inset_axes([0.02, 0.62, 0.28, 0.35])
      apply_viscount_style(ax_gl, {"grid": False})
      draw_basemap(ax_gl, arg2_land_gl, arg3_riv_gl)
      vp_gl = os.path.join(SUBREG_DIR, "southern_europe_and_islands_after_1945_subregions.geojson")
      if os.path.isfile(vp_gl):
        gj_gl = json.load(open(vp_gl, encoding="utf-8"))
        for feat in gj_gl.get("features", []):
          g = shape(feat["geometry"]).buffer(0)
          if g.centroid.x < -25.0 and g.centroid.y > 55.0:
            pg = prepare_and_project(g, PROJ_GREENLAND, 0.40)
            ps = geom_to_patches(pg)
            if ps:
              ax_gl.add_collection(PatchCollection(ps, facecolor="#7d9fc2", edgecolor="#1e293b", linewidths=0.5, alpha=0.85, zorder=2.5))
              gx, gy = pad_projected_bounds(pg.bounds, 0.80, 1.18, 600.0)
              ax_gl.set_xlim(*gx)
              ax_gl.set_ylim(*gy)
      ax_gl.set_aspect("equal", adjustable="box")
      ax_gl.set_xticks([])
      ax_gl.set_yticks([])
      ax_gl.set_title("Greenland", fontsize=6.4, pad=1.5)

  fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.03, wspace=0.06, hspace=0.14)
  save_viscount_figure(fig, os.path.join(FIG_DIR, "magnetic_areal_coverage_hero.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_fig2_holocene_trajectories (arg0_root_summary):
  """Figure 2: Two-panel Holocene European demographic trajectory (10000BC-2025)."""
  rs = arg0_root_summary["macro_raster_series"]
  pts = sorted((int(k), float(v)) for k, v in rs.items() if float(v) > 0)
  yrs_all = [p[0] for p in pts]
  vals_all = [p[1] for p in pts]

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.5), dpi=300, gridspec_kw={"wspace": 0.28})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Long-run Holocene trajectory (-10000 to 2025) on semi-log population axis
  ax1.semilogy(yrs_all, vals_all, "-o", linewidth=1.8, markersize=3.2, color="#1d4ed8", label="MAGNETIC domain total")
  ax1.set_xlim(-10500, 2200)
  ax1.set_ylim(4e4, max(vals_all) * 2.2)
  ax1.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, integer=True))
  ax1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: f"{int(abs(x))}BC" if x < 0 else f"{int(x)}"))
  apply_human_log_ticks(ax1, "y", arg2_semantic=True)
  ax1.set_xlabel("Calendar year")
  ax1.set_ylabel("Population (inhabitants, log scale)")
  ax1.set_title("A. Holocene Demographic Trajectory (10000BC–2025)", fontsize=9.8, pad=6)
  ax1.legend(loc="lower right", fontsize=7.6, frameon=True, facecolor="white")

  # Panel B: Modern & Early Modern trajectory (1500–2025) on linear axis showing Black Death recovery, Industrialisation, Wars
  mod_pts = [(y, v) for y, v in pts if y >= 1500]
  ax2.plot([p[0] for p in mod_pts], [p[1] for p in mod_pts], "-s", linewidth=2.0, markersize=4.0, color="#b91c1c", label="Total MAGNETIC Europe")
  ax2.set_xlim(1480, 2035)
  ax2.set_ylim(0.0, max(p[1] for p in mod_pts) * 1.18)
  ax2.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, integer=True))
  ax2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  ax2.set_xlabel("Calendar year")
  ax2.set_ylabel("Population (inhabitants)")
  ax2.set_title("B. Early Modern to Contemporary Growth (1500–2025)", fontsize=9.8, pad=6)
  ax2.legend(loc="upper left", fontsize=7.6, frameon=True, facecolor="white")

  fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.14, wspace=0.28)
  save_viscount_figure(fig, os.path.join(FIG_DIR, "magnetic_holocene_trajectories.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_fig3_kriging_mosaic (arg0_land_eu, arg1_riv_eu):
  """Figure 3: 4-panel reprojected Stage C Matérn kriging & mass-conserving dasymetric surfaces."""
  epochs = [
    ("A. 1000BC (Bronze–Iron Age Kriging)", "popc_-1000.png"),
    ("B. 1AD (Roman Imperial Peak)", "popc_0.png"),
    ("C. 1500AD (Renaissance & HRE Circles)", "popc_1500.png"),
    ("D. 1880AD (Industrial Sub-Admin HGIS)", "popc_1880.png"),
  ]
  norm = mcolors.LogNorm(vmin=1.0, vmax=20000.0)
  cmap = plt.get_cmap("magma").copy()
  cmap.set_bad(alpha=0.0)

  apply_viscount_style()
  fig, axes = plt.subplots(2, 2, figsize=(11.6, 9.2), dpi=300)
  im_ref = None
  for ax, (etitle, fn) in zip(axes.flat, epochs):
    apply_viscount_style(ax, {"grid": False})
    draw_basemap(ax, arg0_land_eu, arg1_riv_eu)
    rp = os.path.join(POP_DIR, fn)
    if not os.path.isfile(rp):
      rp = os.path.join(POP_DIR, fn.replace("AD.png", ".png"))
    if os.path.isfile(rp):
      grid = decode_velk_density_grid(rp)
      reproj = sample_raster_to_albers(grid, PROJ_EUROPE, EU_XLIM, EU_YLIM, 460, 500)
      im_ref = ax.imshow(
        reproj,
        origin="lower",
        extent=[EU_XLIM[0], EU_XLIM[1], EU_YLIM[0], EU_YLIM[1]],
        cmap=cmap,
        norm=norm,
        interpolation="nearest",
        aspect="equal",
        zorder=3.0,
      )
    ax.set_xlim(*EU_XLIM)
    ax.set_ylim(*EU_YLIM)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    draw_graticule(ax, PROJ_EUROPE, EU_XLIM, EU_YLIM, [40, 50, 60, 70], [-10, 0, 10, 20, 30])
    ax.set_title(etitle, fontsize=9.6, pad=5)

  fig.subplots_adjust(left=0.03, right=0.88, top=0.94, bottom=0.04, wspace=0.07, hspace=0.12)
  if im_ref is not None:
    cax = fig.add_axes([0.905, 0.16, 0.022, 0.68])
    cbar = fig.colorbar(im_ref, cax=cax, format=euro_log_formatter(True))
    apply_human_colorbar_ticks(cbar, arg1_semantic=True)
    cbar.ax.set_title("Inhab. /\n5' cell", fontsize=8.2, pad=8)

  save_viscount_figure(fig, os.path.join(FIG_DIR, "magnetic_kriging_mosaic.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_choropleth_4panel (arg0_out_name, arg1_specs, arg2_land_eu, arg3_riv_eu, arg4_vmin, arg5_vmax):
  """Renders a 4-panel Albers vector sub-regional density choropleth (`inhabitants / km²`)."""
  norm = mcolors.LogNorm(vmin=arg4_vmin, vmax=arg5_vmax)
  cmap = plt.get_cmap("YlOrRd")

  apply_viscount_style()
  fig, axes = plt.subplots(2, 2, figsize=(11.6, 9.2), dpi=300)
  for ax, (ptitle, chapter_specs) in zip(axes.flat, arg1_specs):
    apply_viscount_style(ax, {"grid": False})
    draw_basemap(ax, arg2_land_eu, arg3_riv_eu)
    for stem, target_yr in chapter_specs:
      # Locate chapter summary & vector polygons
      vp = os.path.join(SUBREG_DIR, f"{stem}_subregions.geojson")
      if not os.path.isfile(vp):
        continue
      # Find summary JSON
      sum_p = None
      for rdir, _, fns in os.walk(MAG_DIR):
        if f"{stem}_summary.json" in fns:
          sum_p = os.path.join(rdir, f"{stem}_summary.json")
          break
      if not sum_p:
        continue
      s_obj = json.load(open(sum_p, encoding="utf-8"))
      dens_by_id = {}
      for sr in s_obj["subregions"]:
        pdict = sr["population"]
        if not pdict:
          continue
        best_y = min(pdict.keys(), key=lambda yk: abs(int(yk) - target_yr))
        dens_by_id[sr["id"]] = max(arg4_vmin, float(pdict[best_y]) / max(1.0, float(sr["area_km2"])))
      gj = json.load(open(vp, encoding="utf-8"))
      for feat in gj.get("features", []):
        geom_raw = feat.get("geometry")
        if not geom_raw:
          continue
        g = shape(geom_raw).buffer(0)
        if g.is_empty or g.centroid.x < -25.0:
          continue
        rid = str(feat.get("properties", {}).get("id") or "")
        dval = dens_by_id.get(rid, arg4_vmin)
        pg = prepare_and_project(g, PROJ_EUROPE, 0.35)
        ps = geom_to_patches(pg)
        if ps:
          ax.add_collection(PatchCollection(ps, facecolor=cmap(norm(dval)), edgecolor="#334155", linewidths=0.40, alpha=0.90, zorder=2.5))
    ax.set_xlim(*EU_XLIM)
    ax.set_ylim(*EU_YLIM)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    draw_graticule(ax, PROJ_EUROPE, EU_XLIM, EU_YLIM, [40, 50, 60, 70], [-10, 0, 10, 20, 30])
    ax.set_title(ptitle, fontsize=9.6, pad=5)

  fig.subplots_adjust(left=0.03, right=0.88, top=0.94, bottom=0.04, wspace=0.07, hspace=0.12)
  sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
  sm.set_array([])
  cax = fig.add_axes([0.905, 0.16, 0.022, 0.68])
  cbar = fig.colorbar(sm, cax=cax, format=euro_log_formatter(False, 1))
  apply_human_colorbar_ticks(cbar, arg1_semantic=False, arg2_digits=1)
  cbar.ax.set_title("Inhab. /\nkm²", fontsize=8.4, pad=8)

  save_viscount_figure(fig, os.path.join(FIG_DIR, arg0_out_name), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def main ():
  root_summary = json.load(open(os.path.join(SHARED, "magnetic_root_summary.json"), encoding="utf-8"))
  print("[1] Pre-projecting European & Greenland Natural Earth basemaps...", flush=True)
  land_eu, riv_eu = load_basemap_cache(PROJ_EUROPE, (-30.0, 28.0, 48.0, 82.0))
  land_gl, riv_gl = load_basemap_cache(PROJ_GREENLAND, (-76.0, 58.0, -8.0, 84.0))

  print("[2] Rendering Fig 1: magnetic_areal_coverage_hero.png ...", flush=True)
  render_fig1_hero_coverage(land_eu, riv_eu, land_gl, riv_gl)

  print("[3] Rendering Fig 2: magnetic_holocene_trajectories.png ...", flush=True)
  render_fig2_holocene_trajectories(root_summary)

  print("[4] Rendering Fig 3: magnetic_kriging_mosaic.png ...", flush=True)
  render_fig3_kriging_mosaic(land_eu, riv_eu)

  print("[5] Rendering Fig 4: magnetic_premodern_choropleths.png ...", flush=True)
  premod_specs = [
    ("A. 3000BC (Neolithic Expansion)", [("neolithic_and_bronze_age_europe", -3000)]),
    ("B. 1AD (Roman & Free Germanic Worlds)", [("iron_age_and_roman_europe", 1), ("free_germany_scandinavia_baltic_slavic", 1)]),
    ("C. 1000AD (High Mediaeval Core & Periphery)", [("mediaeval_western_and_central_europe", 1000), ("mediaeval_iberia", 1000), ("mediaeval_scandinavia_and_north_atlantic", 1000), ("mediaeval_east_central_baltic_balkans", 1000)]),
    ("D. 1400AD (Post-Plague Late Mediaeval Trough)", [("black_death_and_late_mediaeval_crisis", 1400)]),
  ]
  render_choropleth_4panel("magnetic_premodern_choropleths.png", premod_specs, land_eu, riv_eu, 0.2, 60.0)

  print("[6] Rendering Fig 5: magnetic_modern_choropleths.png ...", flush=True)
  mod_specs = [
    ("A. 1700 (Early Modern Regional States)", [("early_modern_western_and_northern_europe", 1700), ("early_modern_central_europe", 1700), ("early_modern_southern_europe_and_atlantic_islands", 1700), ("ottoman_balkans_and_southeastern_europe", 1700)]),
    ("B. 1880 (Industrial & Imperial Censuses)", [("industrialisation_western_and_northern_europe", 1880), ("early_modern_nineteenth_century_southern_east_central_europe", 1880)]),
    ("C. 1930 (Inter-War Sovereign States)", [("world_wars_and_interwar_europe", 1930)]),
    ("D. 2020 (Contemporary European Censuses)", [("western_and_northern_europe_after_1945", 2020), ("southern_europe_and_islands_after_1945", 2020), ("east_central_balkans_baltic_after_1945", 2020)]),
  ]
  render_choropleth_4panel("magnetic_modern_choropleths.png", mod_specs, land_eu, riv_eu, 1.0, 500.0)
  print("[DONE] Generated all 5 root MAGNETIC figures cleanly.", flush=True)


if __name__ == "__main__":
  main()
