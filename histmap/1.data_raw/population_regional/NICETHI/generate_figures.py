"""Generates the 4 publication-grade root synthesis figures for Project NICETHI (`studies_on_population.Rmd`).

Produces inside `NICETHI/figures/`:
  1. `fig_01_nicethi_overview_map.png` — Pan-NICETHI Lambert Azimuthal Equal-Area vector
     overview of Sub-Saharan Africa study basins & major urban corridors + dedicated insets
     for Cabo Verde, São Tomé & Príncipe and Mascarenes / Seychelles.
  2. `fig_02_nicethi_kriged_substrata.png` — 4-panel reprojected continuous kriged /
     disaggregated population density benchmarks (1000BC, 1000AD, 1500AD, 1900AD) with
     human European log colorbar.
  3. `fig_03_nicethi_macro_trajectories.png` — 2-panel secular Sub-Saharan Africa & WIO
     population trajectories combining Manning (2014), Frankema & Jerven (2014) and
     macro-regional sub-administrative series (10000BC–2025).
  4. `fig_04_nicethi_urban_hierarchy.png` — 2-panel Pan-NICETHI Zipf rank-size evolution
     across five epochs (1000, 1500, 1850, 1950, 2020) and primate metropolis growth.
"""

import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch
import numpy as np
from PIL import Image
from shapely.geometry import box, shape
from shapely.ops import unary_union

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
NIC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "NICETHI")
SHARED = os.path.join(NIC_DIR, "_shared")
SCRIPTS_DIR = os.path.join(SHARED, "scripts")
SUBREG_DIR = os.path.join(SHARED, "_gis_cache", "chapter_subregions")
POP_DIR = os.path.join(SHARED, "sites_nicethi_africa", "2.population_rasters")
CACHE_PATH = os.path.join(SHARED, "nicethi_figure_cache.json")
FIG_DIR = os.path.join(NIC_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

if SCRIPTS_DIR not in sys.path:
  sys.path.insert(0, SCRIPTS_DIR)

from nicethi_map_helper import (
  BasemapSource10m,
  PROJ_AFRICA,
  PROJ_CABO_VERDE,
  PROJ_GULF_GUINEA,
  PROJ_WIO,
  apply_human_colorbar_ticks,
  apply_human_log_ticks,
  apply_viscount_style,
  draw_basemap,
  draw_graticule,
  euro_log_formatter,
  format_mathtext_euro,
  format_semantic_population,
  geom_to_patches,
  mute_rgb_hex,
  pad_projected_bounds,
  place_inbounds_callouts,
  prepare_and_project,
  save_viscount_figure,
)

GRID_W, GRID_H = 4320, 2160
AF_XLIM = (-4250.0, 4350.0)
AF_YLIM = (-3850.0, 3850.0)

MACRO_BASIN_MAP = {
  "senegal_gambia_atlantic": "West Africa & Sahel",
  "upper_middle_niger": "West Africa & Sahel",
  "upper_guinea_forest": "West Africa & Sahel",
  "lower_niger_benue_volta": "West Africa & Sahel",
  "chad_mega_basin": "West Africa & Sahel",
  "nile_nubia_sudd": "Horn of Africa & Sudan",
  "ethiopian_highlands_horn": "Horn of Africa & Sudan",
  "somali_arid_horn": "Horn of Africa & Sudan",
  "congo_ubangi_basin": "Central Africa & Angola",
  "lower_guinea_ogowe_cuanza": "Central Africa & Angola",
  "east_african_great_lakes": "East Africa & Great Lakes",
  "swahili_rufiji_coast": "East Africa & Great Lakes",
  "zambezi_okavango_limpopo": "Southern Africa",
  "kalahari_namib_arid": "Southern Africa",
  "orange_cape_drakensberg": "Southern Africa",
  "madagascar_wio_atlantic_isl": "African Ocean Islands",
}

MACRO_COLORS = {
  "West Africa & Sahel": (91, 143, 185),
  "Horn of Africa & Sudan": (212, 134, 92),
  "Central Africa & Angola": (118, 174, 122),
  "East Africa & Great Lakes": (176, 132, 188),
  "Southern Africa": (206, 118, 114),
  "African Ocean Islands": (98, 176, 172),
}


def decode_velk_density_grid (arg0_png_path):
  """Decodes a 4320x2160 big-endian float32 RGBA population raster into inhabitants per cell."""
  arr = np.ascontiguousarray(Image.open(arg0_png_path).convert("RGBA"), dtype=np.uint8)
  vals = arr.view(">f4").reshape(arr.shape[:2])
  return np.where(np.isfinite(vals) & (vals > 0.0) & (vals < 1e8), vals, 0.0).astype(np.float32)


def sample_raster_to_laea (arg0_vals, arg1_proj, arg2_xlim, arg3_ylim, arg4_nx=480, arg5_ny=460):
  """Reprojects equirectangular population grid onto Lambert Azimuthal Equal-Area canvas."""
  xs = np.linspace(arg2_xlim[0], arg2_xlim[1], arg4_nx)
  ys = np.linspace(arg3_ylim[0], arg3_ylim[1], arg5_ny)
  xx, yy = np.meshgrid(xs, ys)
  lons, lats = arg1_proj.inv_xy(xx, yy)
  cols = np.clip(np.floor((lons + 180.0) * GRID_W / 360.0).astype(np.int32), 0, GRID_W - 1)
  rows = np.clip(np.floor((90.0 - lats) * GRID_H / 180.0).astype(np.int32), 0, GRID_H - 1)
  sampled = arg0_vals[rows, cols]
  return np.where(sampled > 0.5, sampled, np.nan)


def render_fig1_overview_map (arg0_cache, arg1_bm_src):
  """Figure 1: Pan-NICETHI Lambert Azimuthal Equal-Area vector overview & urban corridors."""
  vp = os.path.join(SUBREG_DIR, "prehistoric_ssa_subregions.geojson")
  gj = json.load(open(vp, encoding="utf-8"))

  box_main = box(-18.5, -36.0, 53.0, 28.5)
  box_cv = box(-26.2, 14.2, -22.0, 17.8)
  box_wio = box(54.0, -22.5, 65.0, -3.5)

  land_af, riv_af = arg1_bm_src.load_for_extent(PROJ_AFRICA, (-22.0, -38.0, 58.0, 32.0), arg2_show_modern_borders=False, arg3_simplify_deg=0.025)

  apply_viscount_style()
  fig, ax = plt.subplots(figsize=(10.2, 7.6), dpi=300)
  apply_viscount_style(ax, {"grid": False})
  draw_basemap(ax, land_af, riv_af)

  macro_seen = {}
  cv_geoms = []
  wio_geoms = []
  all_main_pgs = []

  for idx_f, feat in enumerate(gj.get("features", [])):
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    g = shape(geom_raw).buffer(0)
    if g.is_empty:
      continue
    rid = str(feat.get("properties", {}).get("id") or "")
    mname = MACRO_BASIN_MAP.get(rid, "West Africa & Sahel")
    base_rgb = MACRO_COLORS[mname]
    fc = mute_rgb_hex(base_rgb, idx_f, 0.34 if idx_f % 2 == 0 else 0.44)
    macro_seen[mname] = mute_rgb_hex(base_rgb, 0, 0.36)

    gm = g.intersection(box_main)
    if not gm.is_empty and gm.area > 1e-4:
      pg = prepare_and_project(gm, PROJ_AFRICA, 0.30)
      if not pg.is_empty:
        all_main_pgs.append(pg)
        ps = geom_to_patches(pg)
        if ps:
          ax.add_collection(PatchCollection(ps, facecolor=fc, edgecolor="#334155", linewidths=0.48, alpha=0.88, zorder=2.5))

    gc = g.intersection(box_cv)
    if not gc.is_empty and gc.area > 1e-5:
      cv_geoms.append((gc, mute_rgb_hex(MACRO_COLORS["African Ocean Islands"], 0, 0.34)))
    gw = g.intersection(box_wio)
    if not gw.is_empty and gw.area > 1e-5:
      wio_geoms.append((gw, mute_rgb_hex(MACRO_COLORS["African Ocean Islands"], 0, 0.34)))

  if all_main_pgs:
    outer_pg = unary_union([pg.buffer(0) for pg in all_main_pgs])
    outer_ps = geom_to_patches(outer_pg)
    if outer_ps:
      ax.add_collection(PatchCollection(outer_ps, facecolor="none", edgecolor="#111827", linewidths=1.05, zorder=3.8))

  ax.set_xlim(*AF_XLIM)
  ax.set_ylim(*AF_YLIM)
  ax.set_aspect("equal", adjustable="box")
  ax.set_xticks([])
  ax.set_yticks([])
  draw_graticule(ax, PROJ_AFRICA, AF_XLIM, AF_YLIM, [-30, -20, -10, 0, 10, 20], [-10, 0, 10, 20, 30, 40, 50])

  # Plot major Pan-NICETHI cities sized by peak population
  top_c = arg0_cache["pan_top_cities"]
  max_pk = max((float(c["peak_pop"]) for c in top_c), default=1.0)
  xs_p, ys_p, sz_p = [], [], []
  for c in top_c:
    px, py = PROJ_AFRICA.fwd_pt(c["lon"], c["lat"])
    if AF_XLIM[0] <= px <= AF_XLIM[1] and AF_YLIM[0] <= py <= AF_YLIM[1]:
      xs_p.append(px)
      ys_p.append(py)
      sz_p.append(16.0 + 70.0 * math.sqrt(float(c["peak_pop"]) / max(1.0, max_pk)))
  if xs_p:
    ax.scatter(xs_p, ys_p, s=sz_p, c="#b91c1c", alpha=0.72, edgecolors="white", linewidths=0.55, zorder=5.2)

  # Inset 1 (bottom-left): Cabo Verde Archipelago
  ax_cv = ax.inset_axes([0.02, 0.04, 0.21, 0.20])
  apply_viscount_style(ax_cv, {"grid": False})
  cv_l, cv_r = arg1_bm_src.load_for_extent(PROJ_CABO_VERDE, (-26.2, 14.2, -22.0, 17.8), arg2_show_modern_borders=False)
  draw_basemap(ax_cv, cv_l, cv_r)
  cv_pgs = []
  for g, fc in cv_geoms:
    pg = prepare_and_project(g, PROJ_CABO_VERDE, 0.12)
    if not pg.is_empty:
      cv_pgs.append(pg)
      ps = geom_to_patches(pg)
      if ps:
        ax_cv.add_collection(PatchCollection(ps, facecolor=fc, edgecolor="#111827", linewidths=0.55, alpha=0.90, zorder=2.6))
  if cv_pgs:
    cx, cy = pad_projected_bounds(unary_union(cv_pgs).bounds, 1.35, 1.30, 340.0)
    ax_cv.set_xlim(*cx)
    ax_cv.set_ylim(*cy)
  ax_cv.set_aspect("equal", adjustable="box")
  ax_cv.set_xticks([])
  ax_cv.set_yticks([])
  ax_cv.set_title("Cabo Verde", fontsize=6.8, pad=2)

  # Inset 2 (top-right, over Arabian Sea): Mascarenes Archipelago
  ax_wio = ax.inset_axes([0.75, 0.78, 0.23, 0.19])
  apply_viscount_style(ax_wio, {"grid": False})
  w_l, w_r = arg1_bm_src.load_for_extent(PROJ_WIO, (54.5, -22.2, 64.2, -19.0), arg2_show_modern_borders=False)
  draw_basemap(ax_wio, w_l, w_r)
  box_masc = box(54.5, -22.2, 64.2, -19.0)
  w_pgs = []
  for g, fc in wio_geoms:
    gm_w = g.intersection(box_masc)
    if gm_w.is_empty:
      continue
    pg = prepare_and_project(gm_w, PROJ_WIO, 0.08)
    if not pg.is_empty:
      w_pgs.append(pg)
      ps = geom_to_patches(pg)
      if ps:
        ax_wio.add_collection(PatchCollection(ps, facecolor=fc, edgecolor="#111827", linewidths=0.55, alpha=0.90, zorder=2.6))
  if w_pgs:
    wx, wy = pad_projected_bounds(unary_union(w_pgs).bounds, 1.45, 1.25, 420.0)
    ax_wio.set_xlim(*wx)
    ax_wio.set_ylim(*wy)
  ax_wio.set_aspect("equal", adjustable="box")
  ax_wio.set_xticks([])
  ax_wio.set_yticks([])
  ax_wio.set_title("Mascarenes", fontsize=6.8, pad=2)

  ax.set_title("Sub-Saharan Africa and Western Indian Ocean Study Regions", fontsize=10.8, pad=8)

  leg_order = [
    "West Africa & Sahel",
    "Horn of Africa & Sudan",
    "Central Africa & Angola",
    "East Africa & Great Lakes",
    "Southern Africa",
    "African Ocean Islands",
  ]
  handles = [Patch(facecolor=macro_seen[m], edgecolor="#334155", linewidth=0.55, label=m) for m in leg_order if m in macro_seen]
  fig.subplots_adjust(left=0.03, right=0.97, top=0.93, bottom=0.13)
  fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=7.6, frameon=True, facecolor="white", edgecolor="#cbd5e1", bbox_to_anchor=(0.5, 0.015))

  # Select spatially distributed iconic cities for clean callouts
  featured = [
    {"label": "Lagos", "lon": 3.39, "lat": 6.45},
    {"label": "Kinshasa", "lon": 15.31, "lat": -4.32},
    {"label": "Johannesburg", "lon": 28.04, "lat": -26.20},
    {"label": "Nairobi", "lon": 36.82, "lat": -1.29},
    {"label": "Khartoum", "lon": 32.56, "lat": 15.50},
    {"label": "Addis Ababa", "lon": 38.74, "lat": 9.03},
    {"label": "Dakar", "lon": -17.44, "lat": 14.69},
    {"label": "Luanda", "lon": 13.23, "lat": -8.84},
    {"label": "Cape Town", "lon": 18.42, "lat": -33.92},
    {"label": "Dar es Salaam", "lon": 39.28, "lat": -6.80},
    {"label": "Antananarivo", "lon": 47.52, "lat": -18.91},
    {"label": "Timbuktu", "lon": -3.01, "lat": 16.77},
    {"label": "Kano", "lon": 8.52, "lat": 12.00},
    {"label": "Abidjan", "lon": -4.01, "lat": 5.36},
  ]
  place_inbounds_callouts(
    fig, ax, featured, PROJ_AFRICA, AF_XLIM, AF_YLIM,
    {"max_labels": 11, "min_sep_px": 56.0, "fontsize": 6.7, "margin_px": 10.0, "dot_color": "#b91c1c"},
  )
  save_viscount_figure(fig, os.path.join(FIG_DIR, "fig_01_nicethi_overview_map.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_fig2_kriged_substrata (arg0_bm_src):
  """Figure 2: 4-panel reprojected continuous kriged/disaggregated density surfaces (1000BC-1900AD)."""
  epochs = [
    ("A. 1000BC (Early Iron Age & Kushite Nile)", "popc_-1000.png"),
    ("B. 1000AD (Sahelian, Aksumite & Swahili Cores)", "popc_1000.png"),
    ("C. 1500AD (Pre-Atlantic Demographic Peak)", "popc_1500.png"),
    ("D. 1900AD (Late Colonial Sub-Admin Baseline)", "popc_1900.png"),
  ]
  land_af, riv_af = arg0_bm_src.load_for_extent(PROJ_AFRICA, (-22.0, -38.0, 58.0, 32.0), arg2_show_modern_borders=False, arg3_simplify_deg=0.03)

  norm = mcolors.LogNorm(vmin=1.0, vmax=20000.0)
  cmap = plt.get_cmap("magma").copy()
  cmap.set_bad(alpha=0.0)

  apply_viscount_style()
  fig, axes = plt.subplots(2, 2, figsize=(11.6, 9.8), dpi=300)
  im_ref = None
  for ax, (etitle, fn) in zip(axes.flat, epochs):
    apply_viscount_style(ax, {"grid": False})
    draw_basemap(ax, land_af, riv_af)
    rp = os.path.join(POP_DIR, fn)
    if os.path.isfile(rp):
      grid = decode_velk_density_grid(rp)
      reproj = sample_raster_to_laea(grid, PROJ_AFRICA, AF_XLIM, AF_YLIM, 460, 440)
      im_ref = ax.imshow(
        reproj,
        origin="lower",
        extent=[AF_XLIM[0], AF_XLIM[1], AF_YLIM[0], AF_YLIM[1]],
        cmap=cmap,
        norm=norm,
        interpolation="nearest",
        aspect="equal",
        zorder=3.0,
      )
    ax.set_xlim(*AF_XLIM)
    ax.set_ylim(*AF_YLIM)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    draw_graticule(ax, PROJ_AFRICA, AF_XLIM, AF_YLIM, [-30, -15, 0, 15], [-10, 10, 30, 50])
    ax.set_title(etitle, fontsize=9.4, pad=5)

  fig.subplots_adjust(left=0.03, right=0.88, top=0.94, bottom=0.04, wspace=0.07, hspace=0.12)
  if im_ref is not None:
    cax = fig.add_axes([0.905, 0.16, 0.022, 0.68])
    cbar = fig.colorbar(im_ref, cax=cax, format=euro_log_formatter(True))
    apply_human_colorbar_ticks(cbar, arg1_semantic=True)
    cbar.ax.set_title("Inhab. /\n5' cell", fontsize=8.2, pad=8)

  save_viscount_figure(fig, os.path.join(FIG_DIR, "fig_02_nicethi_kriged_substrata.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_fig3_macro_trajectories (arg0_cache):
  """Figure 3: Three-panel secular Sub-Saharan Africa & WIO regional trajectories & historiographic benchmarks."""
  ms = arg0_cache["macro_series"]
  yrs = ms["years"]
  tot = ms["total"]
  urb = arg0_cache["pan_urban_secular"]

  # Published Sub-Saharan African historical benchmarks (Manning 2014; Frankema & Jerven 2014)
  manning_yrs = [1650, 1700, 1750, 1800, 1850, 1900, 1950]
  manning_pop = [7.4e7, 7.9e7, 8.2e7, 8.4e7, 8.8e7, 1.04e8, 1.76e8]
  fj_yrs = [1850, 1900, 1920, 1940, 1950, 1960]
  fj_pop = [8.5e7, 1.05e8, 1.18e8, 1.54e8, 1.80e8, 2.26e8]

  apply_viscount_style()
  fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14.0, 4.5), dpi=300, gridspec_kw={"wspace": 0.30})
  for ax in (ax1, ax2, ax3):
    apply_viscount_style(ax, {"grid": True})

  # Panel A: Long-run Holocene trajectory (-10000 to 2025) on semi-log axis
  ax1.semilogy(yrs, tot, "-", linewidth=2.0, color="#1d4ed8", label="NICETHI domain total")
  ax1.semilogy([p["year"] for p in urb], [p["urban_pop"] for p in urb], "--o", linewidth=1.4, markersize=3.0, color="#b91c1c", label="Attested urban total")
  ax1.set_xlim(-10400, 2350)
  ax1.set_ylim(4e4, max(tot) * 3.2)
  ax1.xaxis.set_major_locator(mticker.MaxNLocator(nbins=4, integer=True))
  ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: f"{int(abs(x))}BC" if x < 0 else f"{int(x)}"))
  apply_human_log_ticks(ax1, "y", arg2_semantic=True)
  ax1.set_xlabel("Calendar year")
  ax1.set_ylabel("Population (inhabitants, log)")
  ax1.set_title("A. Holocene Trajectory (10000BC–2025)", fontsize=9.2, pad=6)
  ax1.legend(loc="upper left", fontsize=7.0, frameon=True, facecolor="white", framealpha=0.92)

  # Panel B: Historiographic Comparison (1600-1965)
  hist_pts = [(y, v) for y, v in zip(yrs, tot) if 1600 <= y <= 1965]
  ax2.plot([p[0] for p in hist_pts], [p[1] for p in hist_pts], "-o", linewidth=2.0, markersize=3.4, color="#1d4ed8", label="NICETHI total")
  ax2.plot(manning_yrs, manning_pop, "--^", linewidth=1.4, markersize=5.0, color="#0f766e", label="Manning (2014)")
  ax2.plot(fj_yrs, fj_pop, ":s", linewidth=1.4, markersize=4.4, color="#d97706", label="Frankema & Jerven (2014)")
  ax2.set_xlim(1590, 1972)
  ax2.set_ylim(0.0, 2.75e8)
  ax2.xaxis.set_major_locator(mticker.MaxNLocator(nbins=5, integer=True))
  ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  ax2.set_xlabel("Calendar year")
  ax2.set_ylabel("Population (inhabitants)")
  ax2.set_title("B. Historiographic Benchmarks (1600–1965)", fontsize=9.2, pad=6)
  ax2.legend(loc="upper left", fontsize=7.0, frameon=True, facecolor="white", framealpha=0.92)

  # Panel C: 6 Macro-Regional Trajectories (1500-2025)
  mod_idx = [i for i, y in enumerate(yrs) if y >= 1500]
  mod_yrs = [yrs[i] for i in mod_idx]
  reg_styles = [
    ("West Africa & Sahel", "#1d4ed8", "-"),
    ("Horn of Africa & Sudan", "#d97706", "-"),
    ("East Africa & Great Lakes", "#7c3aed", "-"),
    ("Central Africa & Angola", "#059669", "--"),
    ("Southern Africa", "#dc2626", "--"),
    ("African Ocean Islands", "#0891b2", ":"),
  ]
  max_r = 1.0
  for rname, col, ls in reg_styles:
    rvals = [ms["regions"][rname][i] for i in mod_idx]
    max_r = max(max_r, max(rvals))
    ax3.plot(mod_yrs, rvals, linestyle=ls, linewidth=1.8, color=col, label=rname)

  ax3.set_xlim(1485, 2035)
  ax3.set_ylim(0.0, max_r * 1.24)
  ax3.xaxis.set_major_locator(mticker.MaxNLocator(nbins=5, integer=True))
  ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  ax3.set_xlabel("Calendar year")
  ax3.set_ylabel("Population (inhabitants)")
  ax3.set_title("C. Macro-Regional Growth (1500–2025)", fontsize=9.2, pad=6)
  ax3.legend(loc="upper left", fontsize=6.7, frameon=True, facecolor="white", framealpha=0.92)

  fig.subplots_adjust(left=0.06, right=0.985, top=0.88, bottom=0.14, wspace=0.30)
  save_viscount_figure(fig, os.path.join(FIG_DIR, "fig_03_nicethi_macro_trajectories.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_fig4_urban_hierarchy (arg0_cache):
  """Figure 4: Pan-NICETHI Zipf rank-size evolution (1000-2020) and primate metropolis growth."""
  zipf_ep = arg0_cache["pan_zipf_epochs"]
  primates = arg0_cache["primate_cities"]

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.8), dpi=300, gridspec_kw={"wspace": 0.28})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: 5-epoch rank-size curves
  ep_styles = [
    ("1000", "1000AD", "#0891b2"),
    ("1500", "1500AD", "#059669"),
    ("1850", "1850", "#d97706"),
    ("1950", "1950", "#7c3aed"),
    ("2020", "2020", "#dc2626"),
  ]
  max_n = 25
  max_p = 1e4
  for yk, ylbl, col in ep_styles:
    ep = zipf_ep.get(yk)
    if not ep or len(ep["pops"]) < 25:
      continue
    pops = np.asarray(ep["pops"], dtype=np.float64)
    ranks = np.arange(1, len(pops) + 1, dtype=np.float64)
    n_fit = min(max(25, len(pops) // 2), 200)
    slope, _ = np.polyfit(np.log10(ranks[:n_fit]), np.log10(pops[:n_fit]), 1)
    q_val = -slope
    ax1.loglog(ranks, pops, "-", linewidth=1.7, color=col, alpha=0.88, label=rf"{ylbl} ($q = {format_mathtext_euro(q_val, 2)}$)")
    max_n = max(max_n, len(pops))
    max_p = max(max_p, float(pops.max()))

  ax1.set_xlim(0.75, max_n * 1.5)
  ax1.set_ylim(400.0, max_p * 2.8)
  apply_human_log_ticks(ax1, "both", arg2_semantic=True)
  ax1.set_xlabel("Urban rank")
  ax1.set_ylabel("Settlement population (inhabitants)")
  ax1.set_title("A. Rank-Size Evolution Across Five Epochs", fontsize=9.6, pad=6)
  ax1.legend(loc="lower left", fontsize=7.3, frameon=True, facecolor="white", framealpha=0.92)

  # Panel B: Primate city trajectories (1800-2025), decadal envelope to suppress municipal/metro boundary jumps
  city_cols = ["#1d4ed8", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2", "#be185d", "#475569"]
  max_cp = 1e5
  for idx_c, c in enumerate(primates):
    pts = c["series"]
    if not pts:
      continue
    # Aggregate into clean decadal upper-envelope bins (1800..2020 + 2025) and filter spurious single-year drops
    bins = {}
    for yr_p, val_p in pts:
      bk = 2025 if yr_p >= 2023 else int(round(yr_p / 10.0) * 10)
      if val_p > bins.get(bk, 0.0):
        bins[bk] = val_p
    raw_sorted = sorted(bins.items())
    # Remove single-bin city-proper dip artefacts (> 45% sudden drop followed by immediate rebound)
    cleaned = []
    for k_i, (bk, bv) in enumerate(raw_sorted):
      if 0 < k_i < len(raw_sorted) - 1:
        prev_v = raw_sorted[k_i - 1][1]
        next_v = raw_sorted[k_i + 1][1]
        if bv < 0.55 * min(prev_v, next_v):
          continue
        if bv > 2.4 * max(prev_v, next_v) and bk < 1900:
          continue
      cleaned.append((bk, bv))
    xs = [p[0] for p in cleaned]
    ys = [p[1] for p in cleaned]
    if not ys:
      continue
    max_cp = max(max_cp, max(ys))
    ax2.semilogy(xs, ys, "-o", linewidth=1.6, markersize=3.0, color=city_cols[idx_c % len(city_cols)], label=c["name"])

  ax2.set_xlim(1795, 2032)
  ax2.set_ylim(1.5e3, max_cp * 3.0)
  ax2.xaxis.set_major_locator(mticker.MaxNLocator(nbins=5, integer=True))
  apply_human_log_ticks(ax2, "y", arg2_semantic=True)
  ax2.set_xlabel("Calendar year")
  ax2.set_ylabel("Metropolitan population (log scale)")
  ax2.set_title("B. Leading African Metropolises (1800–2025)", fontsize=9.6, pad=6)
  ax2.legend(loc="upper left", ncol=2, fontsize=6.8, frameon=True, facecolor="white", framealpha=0.92)

  fig.subplots_adjust(left=0.075, right=0.975, top=0.88, bottom=0.14, wspace=0.28)
  save_viscount_figure(fig, os.path.join(FIG_DIR, "fig_04_nicethi_urban_hierarchy.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def main ():
  cache = json.load(open(CACHE_PATH, encoding="utf-8"))
  print("[1] Loading Natural Earth 10m coastlines & rivers once into memory...", flush=True)
  bm_src = BasemapSource10m()

  print("[2] Rendering Fig 1: fig_01_nicethi_overview_map.png ...", flush=True)
  render_fig1_overview_map(cache, bm_src)

  print("[3] Rendering Fig 2: fig_02_nicethi_kriged_substrata.png ...", flush=True)
  render_fig2_kriged_substrata(bm_src)

  print("[4] Rendering Fig 3: fig_03_nicethi_macro_trajectories.png ...", flush=True)
  render_fig3_macro_trajectories(cache)

  print("[5] Rendering Fig 4: fig_04_nicethi_urban_hierarchy.png ...", flush=True)
  render_fig4_urban_hierarchy(cache)

  print("[DONE] Generated all 4 root NICETHI figures cleanly.", flush=True)


if __name__ == "__main__":
  main()
