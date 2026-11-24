"""Generates the 4 publication-grade root synthesis figures for Project QUIPU (`studies_on_population.Rmd`).

Produces inside `QUIPU/figures/`:
  1. `quipu_areal_coverage_hero.png` — 6-panel upright Lambert Azimuthal Equal-Area historical coverage
     across Andean South America, the Southern Cone and South Atlantic Islands (10000BC-2025).
  2. `quipu_holocene_trajectory.png` — Two-panel Holocene Andean & Southern Cone demographic trajectory
     (semi-log 10000BC-2025 + linear 1500-2025 showing Conquest collapse and republican expansion).
  3. `quipu_kriging_diagnostics.png` — 4-panel Stage C Matérn residual kriging & dasymetric diagnostics
     (empirical vs fitted semivariograms, archaeological site coverage by jurisdiction, and reprojected
     1500AD & 1900AD continuous population density surfaces with plain European log colorbars).
  4. `quipu_hgis_regimes.png` — 4-panel LAEA vector density choropleths across the 4 historical HGIS
     boundary regimes (1500AD, 1780, 1900, 2020).
"""

import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
import numpy as np
from PIL import Image
from shapely.geometry import box, shape
from shapely.ops import unary_union

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
QUIPU_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "QUIPU")
SHARED = os.path.join(QUIPU_DIR, "_shared")
SCRIPTS_DIR = os.path.join(SHARED, "scripts")
SUBREG_DIR = os.path.join(SHARED, "_gis_cache", "chapter_subregions")
SITES_CFG = os.path.join(SHARED, "sites_quipu_andes_cone", "config")
POP_DIR = os.path.join(SHARED, "sites_quipu_andes_cone", "2.population_rasters")
FIG_DIR = os.path.join(QUIPU_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

if SCRIPTS_DIR not in sys.path:
  sys.path.insert(0, SCRIPTS_DIR)

from quipu_map_helper import (
  PROJ_FALKLANDS,
  PROJ_QUIPU,
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
  pad_projected_bounds,
  prepare_and_project,
  save_viscount_figure,
)

GRID_W, GRID_H = 4320, 2160
QUIPU_XLIM = (-2550.0, 2450.0)
QUIPU_YLIM = (-4050.0, 4050.0)

PERIOD_DISPLAY_LABELS = {
  "01_palaeoindian_early_holocene": "Palaeoindian (10000–6000BC)",
  "04_early_horizon_formative": "Early Horizon (1000BC–1AD)",
  "07_late_intermediate_chiefdoms": "Late Intermediate (1000–1438AD)",
  "08_late_horizon_tawantinsuyu": "Tawantinsuyu (1438–1532AD)",
}

JURISDICTION_DISPLAY_LABELS = {
  "colombia_venezuela_ecuador": "Northern Andes\n(COL, VEN, ECU)",
  "peru": "Central Andes\n(Peru & Titicaca)",
  "southern_cone": "Southern Cone\n(CHL, ARG, URY)",
}


def decode_velk_density_grid (arg0_png_path):
  """Decodes a 4320x2160 big-endian float32 RGBA Viscount population raster into inhabitants per cell."""
  arr = np.ascontiguousarray(Image.open(arg0_png_path).convert("RGBA"), dtype=np.uint8)
  vals = arr.view(">f4").reshape(arr.shape[:2])
  return np.where(np.isfinite(vals) & (vals > 0.0) & (vals < 1e8), vals, 0.0).astype(np.float32)


def sample_raster_to_laea (arg0_vals, arg1_proj, arg2_xlim, arg3_ylim, arg4_nx=420, arg5_ny=640):
  """Reprojects equirectangular population grid onto Lambert Azimuthal Equal-Area canvas via inverse coordinates."""
  xs = np.linspace(arg2_xlim[0], arg2_xlim[1], arg4_nx)
  ys = np.linspace(arg3_ylim[0], arg3_ylim[1], arg5_ny)
  xx, yy = np.meshgrid(xs, ys)
  lons, lats = arg1_proj.inv_xy(xx, yy)
  cols = np.clip(np.floor((lons + 180.0) * GRID_W / 360.0).astype(np.int32), 0, GRID_W - 1)
  rows = np.clip(np.floor((90.0 - lats) * GRID_H / 180.0).astype(np.int32), 0, GRID_H - 1)
  sampled = arg0_vals[rows, cols]
  return np.where(sampled > 0.5, sampled, np.nan)


def extract_mainland_sa_geom (arg0_geom):
  """Clips away distant Pacific islands west of -82.5E (Galápagos) while retaining continental South America & Falklands."""
  if arg0_geom is None or arg0_geom.is_empty:
    return arg0_geom
  cbox = box(-82.5, -56.5, -52.0, 14.0)
  try:
    return arg0_geom.intersection(cbox)
  except Exception:
    return arg0_geom.buffer(0).intersection(cbox)


def render_fig1_hero_coverage (arg0_land_hist, arg1_riv_hist, arg2_land_mod, arg3_riv_mod, arg4_land_flk, arg5_riv_flk):
  """Figure 1: 6-panel historical coverage & regional partitions across QUIPU (10000BC-2025)."""
  panels = [
    ("A. 10000BC–1500AD: Pre-Columbian Regions", ["pre_columbian_northern_andes", "pre_columbian_central_andes", "pre_columbian_southern_cone"], False),
    ("B. 1438–1532: Inca Empire (Tawantinsuyu)", ["inca_empire_tawantinsuyu"], False),
    ("C. 1525–1650: Conquest & Collapse", ["spanish_conquest_andes_collapse"], False),
    ("D. 1536–1830: Viceroyalties & Captaincies", ["viceroyalty_new_granada", "viceroyalty_peru_upper_peru", "chile_rio_plata_banda_oriental"], False),
    ("E. 1819–2025: Independent Andean Republics", ["colombia_after_independence", "venezuela_after_independence", "ecuador_after_independence", "peru_after_independence", "andean_bolivia_independence"], True),
    ("F. 1810–2025: Southern Cone & South Atlantic", ["chile_after_independence", "argentina_after_independence", "uruguay_after_independence"], True),
  ]
  macro_palette = [
    "#6ca6c1", "#7fb685", "#e09f5a", "#b288c0", "#d67d79", "#6db7b0",
    "#c9b46e", "#8da0cb", "#e5a3b3", "#a3c478", "#d4956a", "#7d9fc2",
  ]

  apply_viscount_style()
  fig, axes = plt.subplots(2, 3, figsize=(11.4, 10.6), dpi=300)
  for idx_p, (ax, (ptitle, stems, show_mod)) in enumerate(zip(axes.flat, panels)):
    apply_viscount_style(ax, {"grid": False})
    if show_mod:
      draw_basemap(ax, arg2_land_mod, arg3_riv_mod)
    else:
      draw_basemap(ax, arg0_land_hist, arg1_riv_hist)

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
        g = extract_mainland_sa_geom(shape(geom_raw).buffer(0))
        if g.is_empty:
          continue
        pg = prepare_and_project(g, PROJ_QUIPU, 0.40, None, 2.5e-4, 0.015)
        ps = geom_to_patches(pg)
        if ps:
          fc = macro_palette[col_i % len(macro_palette)]
          ax.add_collection(PatchCollection(ps, facecolor=fc, edgecolor="#334155", linewidths=0.32, alpha=0.84, zorder=2.5))
          col_i += 1

    ax.set_xlim(*QUIPU_XLIM)
    ax.set_ylim(*QUIPU_YLIM)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    draw_graticule(ax, PROJ_QUIPU, QUIPU_XLIM, QUIPU_YLIM, [-50, -40, -30, -20, -10, 0, 10], [-80, -70, -60, -50])
    ax.set_title(ptitle, fontsize=8.6, pad=5)

    # Dedicated Falkland Islands inset on Panel F to display South Atlantic scope
    if idx_p == 5:
      ax_flk = ax.inset_axes([0.56, 0.025, 0.41, 0.21])
      apply_viscount_style(ax_flk, {"grid": False})
      draw_basemap(ax_flk, arg4_land_flk, arg5_riv_flk)
      vp_flk = os.path.join(SUBREG_DIR, "falklands_south_atlantic_subregions.geojson")
      if os.path.isfile(vp_flk):
        gj_flk = json.load(open(vp_flk, encoding="utf-8"))
        flk_pgs = []
        for fi, feat in enumerate(gj_flk.get("features", [])):
          rid = str(feat.get("properties", {}).get("id") or "")
          if not rid.startswith("flk_"):
            continue
          g = shape(feat["geometry"]).buffer(0)
          pg = prepare_and_project(g, PROJ_FALKLANDS, 0.08, None, 1e-5, 0.0)
          if not pg.is_empty:
            flk_pgs.append(pg)
            ps = geom_to_patches(pg)
            if ps:
              ax_flk.add_collection(PatchCollection(ps, facecolor=macro_palette[(fi + 2) % len(macro_palette)], edgecolor="#1e293b", linewidths=0.45, alpha=0.88, zorder=2.5))
        if flk_pgs:
          fx, fy = pad_projected_bounds(unary_union(flk_pgs).bounds, 1.50, 1.38, 220.0)
          ax_flk.set_xlim(*fx)
          ax_flk.set_ylim(*fy)
      ax_flk.set_aspect("equal", adjustable="box")
      ax_flk.set_xticks([])
      ax_flk.set_yticks([])
      ax_flk.text(
        0.50, 0.90, "Falkland Islands", transform=ax_flk.transAxes,
        ha="center", va="top", fontsize=6.1, color="#0f172a", zorder=8.0,
        bbox=dict(boxstyle="round,pad=0.14", facecolor="white", edgecolor="#94a3b8", alpha=0.92, linewidth=0.45),
      )

  fig.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.02, wspace=0.06, hspace=0.11)
  save_viscount_figure(fig, os.path.join(FIG_DIR, "quipu_areal_coverage_hero.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_fig2_holocene_trajectory (arg0_root_summary):
  """Figure 2: Two-panel Holocene Andean & Southern Cone demographic trajectory (10000BC-2025)."""
  rs = arg0_root_summary["macro_raster_series"]
  pts = sorted((int(k), float(v)) for k, v in rs.items() if float(v) > 0)
  yrs_all = [p[0] for p in pts]
  vals_all = [p[1] for p in pts]

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.5), dpi=300, gridspec_kw={"wspace": 0.28})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Long-run Holocene trajectory (-10000 to 2025) on semi-log population axis
  ax1.semilogy(yrs_all, vals_all, "-o", linewidth=1.8, markersize=3.2, color="#1d4ed8", label="QUIPU domain total")
  ax1.set_xlim(-10500, 2250)
  ax1.set_ylim(max(1e4, min(vals_all) * 0.55), max(vals_all) * 2.4)
  ax1.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, integer=True))
  ax1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: f"{int(abs(x))}BC" if x < 0 else f"{int(x)}"))
  apply_human_log_ticks(ax1, "y", arg2_semantic=True)
  ax1.set_xlabel("Calendar year")
  ax1.set_ylabel("Population (inhabitants, log scale)")
  ax1.set_title("A. Holocene Demographic Trajectory (10000BC–2025)", fontsize=9.8, pad=6)
  ax1.legend(loc="lower right", fontsize=7.6, frameon=True, facecolor="white")

  # Panel B: Conquest collapse to contemporary growth (1500–2025) on linear axis
  mod_pts = [(y, v) for y, v in pts if y >= 1500]
  ax2.plot([p[0] for p in mod_pts], [p[1] for p in mod_pts], "-s", linewidth=2.0, markersize=4.0, color="#b91c1c", label="Andes & Southern Cone")
  ax2.set_xlim(1485, 2035)
  ax2.set_ylim(0.0, max(p[1] for p in mod_pts) * 1.18)
  ax2.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, integer=True))
  ax2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  ax2.set_xlabel("Calendar year")
  ax2.set_ylabel("Population (inhabitants)")
  ax2.set_title("B. Conquest Collapse to Contemporary Growth (1500–2025)", fontsize=9.8, pad=6)
  ax2.legend(loc="upper left", fontsize=7.6, frameon=True, facecolor="white")

  fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.14, wspace=0.28)
  save_viscount_figure(fig, os.path.join(FIG_DIR, "quipu_holocene_trajectory.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def _matern15_corr (arg0_u, arg1_tau):
  """Matérn nu = 3/2 correlation function k(u) = (1 + sqrt(3)*u/tau) * exp(-sqrt(3)*u/tau)."""
  z = math.sqrt(3.0) * np.asarray(arg0_u, dtype=np.float64) / max(1e-6, float(arg1_tau))
  return (1.0 + z) * np.exp(-z)


def render_fig3_kriging_diagnostics (arg0_land_hist, arg1_riv_hist, arg2_land_mod, arg3_riv_mod):
  """Figure 3: 4-panel Stage C Matérn residual kriging & continuous population surfaces."""
  kd = json.load(open(os.path.join(SITES_CFG, "kriging_diagnostics.json"), encoding="utf-8"))
  vmodels = kd["variogram_models"]
  jcov = kd["jurisdiction_arch_coverage"]

  apply_viscount_style()
  fig = plt.figure(figsize=(11.8, 10.0), dpi=300)
  gs = fig.add_gridspec(2, 2, height_ratios=[0.85, 1.35], width_ratios=[1.0, 1.0], left=0.08, right=0.88, top=0.94, bottom=0.05, wspace=0.26, hspace=0.24)
  ax1 = fig.add_subplot(gs[0, 0])
  ax2 = fig.add_subplot(gs[0, 1])
  ax3 = fig.add_subplot(gs[1, 0])
  ax4 = fig.add_subplot(gs[1, 1])

  # Panel A: Normalised empirical vs fitted nested Matérn semivariogram across 4 key archaeological horizons
  apply_viscount_style(ax1, {"grid": True})
  sel_keys = [
    ("01_palaeoindian_early_holocene", "#2563eb", "o"),
    ("04_early_horizon_formative", "#16a34a", "s"),
    ("07_late_intermediate_chiefdoms", "#d97706", "^"),
    ("08_late_horizon_tawantinsuyu", "#b91c1c", "D"),
  ]
  u_dense = np.linspace(0.0, 7.2, 200)
  for pkey, col, mk in sel_keys:
    vm = vmodels[pkey]
    u_emp = np.asarray(vm["empirical_u_lags"], dtype=np.float64)
    g_emp = np.asarray(vm["empirical_gammas"], dtype=np.float64)
    plat_mask = (u_emp >= 2.60) & (u_emp <= 7.00)
    sill = max(1e-9, float(np.mean(g_emp[plat_mask])) if np.any(plat_mask) else float(g_emp[-1]))
    fit_mask = u_emp <= 7.2
    g_norm = g_emp[fit_mask] / sill
    lbl_base = PERIOD_DISPLAY_LABELS[pkey]
    r2_str = format_mathtext_euro(vm["residual_r2"], 3)
    ax1.plot(u_emp[fit_mask], g_norm, mk, markersize=4.2, color=col, alpha=0.88, label=rf"{lbl_base} ($R^2 = {r2_str}$)")
    if pkey == "08_late_horizon_tawantinsuyu":
      c0_r = float(vm["nugget_to_sill_ratio"])
      c1_w = float(vm["c1_weight"])
      c2_w = float(vm["c2_weight"])
      t1 = float(vm["tau1_dimensionless"])
      t2 = float(vm["tau2_dimensionless"])
      g_fit = c0_r + (1.0 - c0_r) * (1.0 - (c1_w * _matern15_corr(u_dense, t1) + c2_w * _matern15_corr(u_dense, t2)))
      t1_s = format_mathtext_euro(t1, 2)
      t2_s = format_mathtext_euro(t2, 2)
      ax1.plot(u_dense, g_fit, "-", linewidth=1.7, color="#111827", label=rf"Nested Matérn ($\tau_1 = {t1_s}$, $\tau_2 = {t2_s}$)")

  ax1.set_xlim(0.0, 7.3)
  ax1.set_ylim(0.0, 1.32)
  ax1.xaxis.set_major_formatter(euro_tick_formatter(0))
  ax1.yaxis.set_major_formatter(euro_tick_formatter(1))
  ax1.set_xlabel("Dimensionless catchment lag")
  ax1.set_ylabel("Normalised semivariance")
  ax1.set_title("A. Pre-Columbian Residual Variograms", fontsize=9.5, pad=6)
  ax1.legend(loc="lower right", fontsize=6.5, frameon=True, facecolor="white", framealpha=0.92)

  # Panel B: Archaeological site provenance breakdown by jurisdiction (zero crowd-sourced sites)
  apply_viscount_style(ax2, {"grid": True})
  j_order = ["southern_cone", "peru", "colombia_venezuela_ecuador"]
  y_pos = np.arange(len(j_order))
  nat_vals = np.array([jcov[k]["national_register_sites"] for k in j_order], dtype=np.float64)
  mon_vals = np.array([jcov[k]["regional_monograph_sites"] for k in j_order], dtype=np.float64)
  c14_vals = np.array([jcov[k]["radiocarbon_db_sites"] for k in j_order], dtype=np.float64)
  tot_vals = nat_vals + mon_vals + c14_vals

  ax2.barh(y_pos, nat_vals, color="#2b6cb0", edgecolor="#1e293b", linewidth=0.5, label="National heritage registers")
  ax2.barh(y_pos, mon_vals, left=nat_vals, color="#d97706", edgecolor="#1e293b", linewidth=0.5, label="Academic monographs")
  ax2.barh(y_pos, c14_vals, left=nat_vals + mon_vals, color="#2a9d8f", edgecolor="#1e293b", linewidth=0.5, label="Radiocarbon databases")
  ax2.set_yticks(y_pos)
  ax2.set_yticklabels([JURISDICTION_DISPLAY_LABELS[k] for k in j_order], fontsize=7.6)
  max_tot = float(tot_vals.max())
  ax2.set_xlim(0.0, max_tot * 1.28)
  ax2.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5))
  ax2.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  for yp, tv in zip(y_pos, tot_vals):
    ax2.text(tv + max_tot * 0.02, yp, format_semantic_population(tv), va="center", ha="left", fontsize=7.4, color="#0f172a")
  ax2.set_xlabel("Archaeological sites (total 101,9k; 0% crowd)")
  ax2.set_title("B. Archaeological Site Coverage by Jurisdiction", fontsize=9.5, pad=6)
  ax2.legend(loc="lower right", fontsize=6.9, frameon=True, facecolor="white", framealpha=0.92)

  # Panels C & D: Reprojected Stage C continuous population density surfaces (`popc_1500.png` & `popc_1900.png`)
  norm = mcolors.LogNorm(vmin=1.0, vmax=10000.0)
  cmap = plt.get_cmap("magma").copy()
  cmap.set_bad(alpha=0.0)
  map_specs = [
    (ax3, "C. 1500AD Reconstructed Population Surface", "popc_1500.png", arg0_land_hist, arg1_riv_hist),
    (ax4, "D. 1900AD Sub-Admin Dasymetric Surface", "popc_1900.png", arg2_land_mod, arg3_riv_mod),
  ]
  im_ref = None
  for axm, mtitle, fn, l_p, r_g in map_specs:
    apply_viscount_style(axm, {"grid": False})
    draw_basemap(axm, l_p, r_g)
    rp = os.path.join(POP_DIR, fn)
    if os.path.isfile(rp):
      grid = decode_velk_density_grid(rp)
      reproj = sample_raster_to_laea(grid, PROJ_QUIPU, QUIPU_XLIM, QUIPU_YLIM, 380, 600)
      im_ref = axm.imshow(
        reproj,
        origin="lower",
        extent=[QUIPU_XLIM[0], QUIPU_XLIM[1], QUIPU_YLIM[0], QUIPU_YLIM[1]],
        cmap=cmap,
        norm=norm,
        interpolation="nearest",
        aspect="equal",
        zorder=3.0,
      )
    axm.set_xlim(*QUIPU_XLIM)
    axm.set_ylim(*QUIPU_YLIM)
    axm.set_aspect("equal", adjustable="box")
    axm.set_xticks([])
    axm.set_yticks([])
    draw_graticule(axm, PROJ_QUIPU, QUIPU_XLIM, QUIPU_YLIM, [-50, -40, -30, -20, -10, 0, 10], [-80, -70, -60, -50])
    axm.set_title(mtitle, fontsize=9.3, pad=5)

  if im_ref is not None:
    cax = fig.add_axes([0.905, 0.08, 0.022, 0.42])
    cbar = fig.colorbar(im_ref, cax=cax, format=euro_log_formatter(True))
    apply_human_colorbar_ticks(cbar, arg1_semantic=True)
    cbar.ax.set_title("Inhab. /\n5' cell", fontsize=8.0, pad=7)

  save_viscount_figure(fig, os.path.join(FIG_DIR, "quipu_kriging_diagnostics.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_fig4_hgis_regimes (arg0_land_hist, arg1_riv_hist, arg2_land_mod, arg3_riv_mod):
  """Figure 4: 4-panel LAEA vector density choropleths across QUIPU's 4 historical HGIS boundary regimes."""
  specs = [
    (
      "A. 1500AD (Pre-Columbian & Tawantinsuyu)",
      [("pre_columbian_northern_andes", 1500), ("inca_empire_tawantinsuyu", 1500), ("pre_columbian_southern_cone", 1500)],
      False,
    ),
    (
      "B. 1780 (Bourbon Viceroyalties & HGIS Indias)",
      [("viceroyalty_new_granada", 1780), ("viceroyalty_peru_upper_peru", 1780), ("chile_rio_plata_banda_oriental", 1780)],
      False,
    ),
    (
      "C. 1900 (Republican Provincial Censuses)",
      [
        ("colombia_after_independence", 1900), ("venezuela_after_independence", 1900), ("ecuador_after_independence", 1900),
        ("peru_after_independence", 1900), ("andean_bolivia_independence", 1900), ("chile_after_independence", 1900),
        ("argentina_after_independence", 1900), ("uruguay_after_independence", 1900),
      ],
      True,
    ),
    (
      "D. 2020 (Contemporary National Censuses)",
      [
        ("colombia_after_independence", 2020), ("venezuela_after_independence", 2020), ("ecuador_after_independence", 2020),
        ("peru_after_independence", 2020), ("andean_bolivia_independence", 2020), ("chile_after_independence", 2020),
        ("argentina_after_independence", 2020), ("uruguay_after_independence", 2020),
      ],
      True,
    ),
  ]

  vmin, vmax = 0.1, 300.0
  norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)
  cmap = plt.get_cmap("YlOrRd")

  # Index chapter summary paths once
  summary_paths = {}
  for rdir, _, fns in os.walk(QUIPU_DIR):
    for fn in fns:
      if fn.endswith("_summary.json"):
        summary_paths[fn[:-13]] = os.path.join(rdir, fn)

  apply_viscount_style()
  fig, axes = plt.subplots(2, 2, figsize=(10.2, 11.0), dpi=300)
  for ax, (ptitle, ch_specs, show_mod) in zip(axes.flat, specs):
    apply_viscount_style(ax, {"grid": False})
    if show_mod:
      draw_basemap(ax, arg2_land_mod, arg3_riv_mod)
    else:
      draw_basemap(ax, arg0_land_hist, arg1_riv_hist)

    for stem, target_yr in ch_specs:
      vp = os.path.join(SUBREG_DIR, f"{stem}_subregions.geojson")
      sum_p = summary_paths.get(stem)
      if not os.path.isfile(vp) or not sum_p:
        continue
      s_obj = json.load(open(sum_p, encoding="utf-8"))
      dens_by_id = {}
      for sr in s_obj["subregions"]:
        pdict = sr["population"]
        if not pdict:
          continue
        best_y = min(pdict.keys(), key=lambda yk: abs(int(yk) - target_yr))
        dens_by_id[sr["id"]] = max(vmin, min(vmax, float(pdict[best_y]) / max(1.0, float(sr["area_km2"]))))

      gj = json.load(open(vp, encoding="utf-8"))
      for feat in gj.get("features", []):
        geom_raw = feat.get("geometry")
        if not geom_raw:
          continue
        g = extract_mainland_sa_geom(shape(geom_raw).buffer(0))
        if g.is_empty:
          continue
        rid = str(feat.get("properties", {}).get("id") or "")
        dval = dens_by_id.get(rid, vmin)
        pg = prepare_and_project(g, PROJ_QUIPU, 0.40, None, 2.5e-4, 0.015)
        ps = geom_to_patches(pg)
        if ps:
          ax.add_collection(PatchCollection(ps, facecolor=cmap(norm(dval)), edgecolor="#334155", linewidths=0.35, alpha=0.90, zorder=2.5))

    ax.set_xlim(*QUIPU_XLIM)
    ax.set_ylim(*QUIPU_YLIM)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    draw_graticule(ax, PROJ_QUIPU, QUIPU_XLIM, QUIPU_YLIM, [-50, -40, -30, -20, -10, 0, 10], [-80, -70, -60, -50])
    ax.set_title(ptitle, fontsize=9.4, pad=5)

  fig.subplots_adjust(left=0.03, right=0.87, top=0.95, bottom=0.03, wspace=0.07, hspace=0.10)
  sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
  sm.set_array([])
  cax = fig.add_axes([0.895, 0.16, 0.024, 0.68])
  cbar = fig.colorbar(sm, cax=cax, format=euro_log_formatter(False, 1))
  apply_human_colorbar_ticks(cbar, arg1_semantic=False, arg2_digits=1)
  cbar.ax.set_title("Inhab. /\nkm²", fontsize=8.4, pad=8)

  save_viscount_figure(fig, os.path.join(FIG_DIR, "quipu_hgis_regimes.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def main ():
  root_summary = json.load(open(os.path.join(SHARED, "quipu_root_summary.json"), encoding="utf-8"))
  print("[1] Pre-projecting South America & Falklands Natural Earth basemaps...", flush=True)
  land_hist, riv_hist = load_basemap_cache(PROJ_QUIPU, (-90.0, -60.0, -30.0, 16.0), arg2_show_modern_borders=False)
  land_mod, riv_mod = load_basemap_cache(PROJ_QUIPU, (-90.0, -60.0, -30.0, 16.0), arg2_show_modern_borders=True)
  land_flk, riv_flk = load_basemap_cache(PROJ_FALKLANDS, (-62.5, -53.2, -56.5, -50.5), arg2_show_modern_borders=True, arg3_high_res=True)

  print("[2] Rendering Fig 1: quipu_areal_coverage_hero.png ...", flush=True)
  render_fig1_hero_coverage(land_hist, riv_hist, land_mod, riv_mod, land_flk, riv_flk)

  print("[3] Rendering Fig 2: quipu_holocene_trajectory.png ...", flush=True)
  render_fig2_holocene_trajectory(root_summary)

  print("[4] Rendering Fig 3: quipu_kriging_diagnostics.png ...", flush=True)
  render_fig3_kriging_diagnostics(land_hist, riv_hist, land_mod, riv_mod)

  print("[5] Rendering Fig 4: quipu_hgis_regimes.png ...", flush=True)
  render_fig4_hgis_regimes(land_hist, riv_hist, land_mod, riv_mod)
  print("[DONE] Generated all 4 root QUIPU figures cleanly.", flush=True)


if __name__ == "__main__":
  main()
