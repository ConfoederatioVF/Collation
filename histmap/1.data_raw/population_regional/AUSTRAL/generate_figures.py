"""Generates the 4 POLARIS-grade root synthesis figures for Project AUSTRAL (`AUSTRAL/figures/`).

Outputs:
  1. `01_austral_overview_map.png` — Pan-Oceanic equal-area vector map (Sahul/NZ/Melanesia +
     Remote Oceania across the `180°` antimeridian, excluding Hawai'i & American Samoa).
  2. `02_austral_kriging_diagnostics.png` — Non-stationary Matérn variogram curves & 4-jurisdiction
     archaeological site provenance (`69.018` primary sites, `0,0%` crowd share).
  3. `03_austral_secular_trajectory.png` — Secular population trajectory across Australia,
     New Zealand, New Guinea, Island Melanesia, Micronesia and Polynesia (`10000BC–2025`).
  4. `04_austral_urban_hierarchy.png` — Pan-Oceanic urban hierarchy & rank-size Zipf distribution.
"""

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch
import numpy as np
from shapely.geometry import box, shape
from shapely.ops import unary_union

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
AUS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL")
SHARED = os.path.join(AUS_DIR, "_shared")
SCRIPTS_DIR = os.path.join(SHARED, "scripts")
SUBREG_DIR = os.path.join(SHARED, "_gis_cache", "chapter_subregions")
FIG_DIR = os.path.join(AUS_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

if SCRIPTS_DIR not in sys.path:
  sys.path.insert(0, SCRIPTS_DIR)

from austral_map_helper import (
  PROJ_PAN_OCEANIA_EAST,
  PROJ_PAN_OCEANIA_WEST,
  apply_human_log_ticks,
  apply_viscount_style,
  draw_basemap,
  draw_graticule,
  euro_tick_formatter,
  format_euro_number,
  format_mathtext_euro,
  format_semantic_population,
  geom_to_patches,
  load_basemap_cache,
  pad_projected_bounds,
  place_inbounds_callouts,
  prepare_and_project,
  save_viscount_figure,
  shift_geom_pacific,
)

MACRO_DISPLAY = {
  "australia": ("Australia & Tasmania", "#c47d5a"),
  "new_guinea": ("New Guinea & Bismarcks", "#5f9e75"),
  "new_zealand": ("New Zealand & Chathams", "#4d86b0"),
  "island_melanesia": ("Island Melanesia & Fiji", "#9b6fb0"),
  "micronesia": ("Micronesia & Kiribati", "#d4a448"),
  "polynesia": ("Polynesia (excl. Hawai'i & Am. Samoa)", "#c95f66"),
}

PERIOD_DISPLAY = {
  "01_pleistocene_early_holocene_sahul": ("10000–4000BC (Sahul)", "#1d4ed8"),
  "03_lapita_austronesian_dispersal": ("1500–500BC (Lapita)", "#0f766e"),
  "06_aotearoa_settlement_classic_chiefdoms": ("1000–1500AD (Aotearoa)", "#d97706"),
  "08_contact_and_early_colonial_transition": ("1750–1850 (Contact)", "#b91c1c"),
}

JURISDICTION_DISPLAY = {
  "australia": "Australia",
  "new_zealand": "New Zealand",
  "polynesia_micronesia": "Polynesia & Micronesia",
  "new_guinea_melanesia": "New Guinea & Melanesia",
}

COUNTRY_TO_MACRO = {
  "Australia": "australia",
  "Norfolk Island": "australia",
  "New Zealand": "new_zealand",
  "Papua New Guinea": "new_guinea",
  "Indonesia": "new_guinea",
  "Fiji": "island_melanesia",
  "Solomon Islands": "island_melanesia",
  "Vanuatu": "island_melanesia",
  "New Caledonia": "island_melanesia",
  "Guam": "micronesia",
  "Northern Mariana Islands": "micronesia",
  "Palau": "micronesia",
  "Federated States of Micronesia": "micronesia",
  "Marshall Islands": "micronesia",
  "Kiribati": "micronesia",
  "Nauru": "micronesia",
  "Samoa": "polynesia",
  "Tonga": "polynesia",
  "French Polynesia": "polynesia",
  "Cook Islands": "polynesia",
  "Tuvalu": "polynesia",
  "Niue": "polynesia",
  "Tokelau": "polynesia",
  "Wallis and Futuna": "polynesia",
  "Pitcairn Islands": "polynesia",
  "Chile": "polynesia",
}


def load_macro_geoms ():
  """Loads Pacific-shifted vector polygons grouped into the 6 canonical AUSTRAL macro-regions."""
  sources = {
    "australia": "colonial_australia_subregions.geojson",
    "new_guinea": "precolonial_new_guinea_subregions.geojson",
    "new_zealand": "pre_european_new_zealand_subregions.geojson",
    "island_melanesia": "colonial_island_melanesia_subregions.geojson",
    "micronesia": "colonial_micronesia_subregions.geojson",
    "polynesia": "precolonial_polynesia_subregions.geojson",
  }
  out = {}
  for m_key, fn in sources.items():
    gj = json.load(open(os.path.join(SUBREG_DIR, fn), encoding="utf-8"))
    geoms = []
    for feat in gj.get("features", []):
      raw = feat.get("geometry")
      if not raw:
        continue
      sg = shift_geom_pacific(shape(raw), 95.0, -95.0, -56.0, 32.0)
      if not sg.is_empty:
        geoms.append(sg)
    if m_key in ("australia", "new_guinea", "new_zealand") and geoms:
      try:
        out[m_key] = [unary_union([g.buffer(0) for g in geoms])]
      except Exception:
        out[m_key] = geoms
    else:
      out[m_key] = geoms
  return out


def render_fig1_overview_map ():
  """Figure 1: Pan-Oceanic equal-area vector map (Sahul/NZ + Remote Oceania across `180°`)."""
  macro_geoms = load_macro_geoms()

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 6.2), dpi=300, gridspec_kw={"width_ratios": [1.0, 1.15]})

  # Panel A: Near Oceania, Australia & New Zealand
  apply_viscount_style(ax1, {"grid": False})
  land_w, riv_w = load_basemap_cache(PROJ_PAN_OCEANIA_WEST, (106.0, -52.0, 190.0, 6.0), arg2_show_modern_borders=False)
  draw_basemap(ax1, land_w, riv_w)
  west_keys = ["australia", "new_guinea", "new_zealand", "island_melanesia"]
  for mk in west_keys:
    fc = MACRO_DISPLAY[mk][1]
    for g in macro_geoms[mk]:
      pg = prepare_and_project(g, PROJ_PAN_OCEANIA_WEST, 0.35)
      ps = geom_to_patches(pg)
      if ps:
        ax1.add_collection(PatchCollection(ps, facecolor=fc, edgecolor="#334155", linewidths=0.35, alpha=0.86, zorder=2.5))
      if mk == "island_melanesia" and not pg.is_empty and pg.area < 15000.0:
        rp = pg.representative_point()
        ax1.scatter([rp.x], [rp.y], s=26.0, facecolor=fc, edgecolor="#1e293b", linewidths=0.5, alpha=0.80, zorder=2.7)

  w_xlim = (-3700.0, 3950.0)
  w_ylim = (-2950.0, 3150.0)
  ax1.set_xlim(*w_xlim)
  ax1.set_ylim(*w_ylim)
  ax1.set_aspect("equal", adjustable="box")
  ax1.set_xticks([])
  ax1.set_yticks([])
  draw_graticule(ax1, PROJ_PAN_OCEANIA_WEST, w_xlim, w_ylim, [-45, -30, -15, 0], [120, 135, 150, 165, 180], (106.0, 190.0), (-52.0, 6.0))
  ax1.set_title("A. Australia, New Guinea, New Zealand & Melanesia", fontsize=9.4, pad=6)

  # Panel B: Remote Oceania (Micronesia, Melanesia & Polynesia across 180°)
  apply_viscount_style(ax2, {"grid": False})
  land_e, riv_e = load_basemap_cache(PROJ_PAN_OCEANIA_EAST, (126.0, -34.0, 256.0, 26.0), arg2_show_modern_borders=False)
  draw_basemap(ax2, land_e, riv_e)
  east_keys = ["island_melanesia", "micronesia", "polynesia"]
  for mk in east_keys:
    fc = MACRO_DISPLAY[mk][1]
    for g in macro_geoms[mk]:
      pg = prepare_and_project(g, PROJ_PAN_OCEANIA_EAST, 0.35)
      ps = geom_to_patches(pg)
      if ps:
        ax2.add_collection(PatchCollection(ps, facecolor=fc, edgecolor="#334155", linewidths=0.35, alpha=0.86, zorder=2.5))
      if not pg.is_empty and pg.area < 40000.0:
        rp = pg.representative_point()
        ax2.scatter([rp.x], [rp.y], s=36.0, facecolor=fc, edgecolor="#1e293b", linewidths=0.60, alpha=0.85, zorder=2.8)

  e_xlim = (-6550.0, 6250.0)
  e_ylim = (-3000.0, 4150.0)
  ax2.set_xlim(*e_xlim)
  ax2.set_ylim(*e_ylim)
  ax2.set_aspect("equal", adjustable="box")
  ax2.set_xticks([])
  ax2.set_yticks([])
  draw_graticule(ax2, PROJ_PAN_OCEANIA_EAST, e_xlim, e_ylim, [-30, -15, 0, 15], [140, 160, 180, 200, 220, 240], (126.0, 256.0), (-34.0, 26.0))
  ax2.set_title("B. Remote Oceania Across the Antimeridian (180°)", fontsize=9.4, pad=6)

  # Bottom 6-macro-region legend
  handles = [
    Patch(facecolor=fc, edgecolor="#334155", linewidth=0.55, label=lbl)
    for lbl, fc in MACRO_DISPLAY.values()
  ]
  fig.subplots_adjust(left=0.02, right=0.98, top=0.91, bottom=0.14, wspace=0.05)
  fig.legend(
    handles=handles, loc="lower center", ncol=3, fontsize=7.6,
    frameon=True, facecolor="white", edgecolor="#cbd5e1", bbox_to_anchor=(0.5, 0.018)
  )

  # Clean in-bounds geographic callouts
  west_callouts = [
    {"label": "Sydney", "lon": 151.21, "lat": -33.87},
    {"label": "Perth", "lon": 115.86, "lat": -31.95},
    {"label": "Port Moresby", "lon": 147.18, "lat": -9.44},
    {"label": "Auckland", "lon": 174.76, "lat": -36.85},
    {"label": "Suva", "lon": 178.44, "lat": -18.14},
    {"label": "Nouméa", "lon": 166.46, "lat": -22.27},
  ]
  east_callouts = [
    {"label": "Guam", "lon": 144.79, "lat": 13.44},
    {"label": "Suva", "lon": 178.44, "lat": -18.14},
    {"label": "Apia", "lon": -171.76, "lat": -13.83},
    {"label": "Nuku'alofa", "lon": -175.20, "lat": -21.14},
    {"label": "Pape'ete", "lon": -149.57, "lat": -17.54},
    {"label": "Rapa Nui", "lon": -109.35, "lat": -27.11},
  ]
  place_inbounds_callouts(
    fig, ax1, west_callouts, PROJ_PAN_OCEANIA_WEST, w_xlim, w_ylim,
    {"max_labels": 6, "min_sep_px": 48.0, "fontsize": 6.6, "margin_px": 10.0, "dot_color": "#b91c1c"}
  )
  place_inbounds_callouts(
    fig, ax2, east_callouts, PROJ_PAN_OCEANIA_EAST, e_xlim, e_ylim,
    {"max_labels": 6, "min_sep_px": 48.0, "fontsize": 6.6, "margin_px": 10.0, "dot_color": "#b91c1c"}
  )
  save_viscount_figure(fig, os.path.join(FIG_DIR, "01_austral_overview_map.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_fig2_kriging_diagnostics (arg0_root):
  """Figure 2: Non-stationary Matérn variogram curves & 4-jurisdiction archaeological site provenance."""
  kd = arg0_root["kriging_diagnostics"]
  arch = arg0_root["archaeological_provenance"]
  vmods = kd.get("variogram_models", {})

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.8, 4.7), dpi=300, gridspec_kw={"width_ratios": [1.05, 1.0], "wspace": 0.38})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Normalized Matérn (nu = 3/2) empirical semivariance curves across 4 key horizons
  max_g = 0.0
  for pkey, (plbl, pcol) in PERIOD_DISPLAY.items():
    vm = vmods.get(pkey)
    if not vm:
      continue
    lags = np.asarray(vm.get("empirical_u_lags", []), dtype=np.float64)
    gammas = np.asarray(vm.get("empirical_gammas", []), dtype=np.float64)
    if len(lags) == 0:
      continue
    # Express in 10^-3 units (milli-semivariance) for clean plain European tick labels
    g_milli = gammas * 1000.0
    max_g = max(max_g, float(g_milli.max()))
    r2_v = float(vm.get("residual_r2", 0.999))
    ax1.plot(
      lags, g_milli, "-o", linewidth=1.6, markersize=3.8, color=pcol,
      label=rf"{plbl} ($R^2 = {format_mathtext_euro(r2_v, 3)}$)"
    )

  tau1 = float(kd.get("tau1_dimensionless", 1.35))
  tau2 = float(kd.get("tau2_dimensionless", 2.90))
  ax1.axvline(tau1, linestyle="--", linewidth=1.0, color="#475569", alpha=0.75)
  ax1.axvline(tau2, linestyle=":", linewidth=1.0, color="#64748b", alpha=0.75)
  ax1.set_xlim(0.0, 13.8)
  ax1.set_ylim(0.0, max(0.25, max_g * 1.24))
  ax1.xaxis.set_major_formatter(euro_tick_formatter(1))
  ax1.yaxis.set_major_formatter(euro_tick_formatter(2))
  ax1.set_xlabel(r"Dimensionless Voronoi lag $u$")
  ax1.set_ylabel(r"Empirical semivariance ($\times 10^{-3}$)")
  ax1.set_title(r"A. Non-Stationary Matérn ($\nu = 3/2$) Variograms", fontsize=9.8, pad=6)
  ax1.legend(loc="upper left", fontsize=7.0, frameon=True, facecolor="white", framealpha=0.94)

  # Panel B: 4-jurisdiction archaeological site provenance (69.018 primary sites, 0,0% crowd share)
  cov = arch.get("jurisdiction_arch_coverage", {})
  j_order = ["new_guinea_melanesia", "polynesia_micronesia", "new_zealand", "australia"]
  y_pos = np.arange(len(j_order))
  reg_vals = []
  mono_vals = []
  c14_vals = []
  tot_vals = []
  for jk in j_order:
    blk = cov.get(jk, {})
    reg_v = int(blk.get("regional_register_sites", 0))
    mono_v = int(blk.get("monograph_sites", 0))
    c14_v = int(blk.get("c14_primary_sites", 0))
    tot_v = int(blk.get("total_sites", reg_v + mono_v + c14_v))
    reg_vals.append(reg_v)
    mono_vals.append(mono_v)
    c14_vals.append(c14_v)
    tot_vals.append(tot_v)

  reg_arr = np.array(reg_vals, dtype=np.float64)
  mono_arr = np.array(mono_vals, dtype=np.float64)
  c14_arr = np.array(c14_vals, dtype=np.float64)

  ax2.barh(y_pos, reg_arr, color="#2b6cb0", edgecolor="#1e293b", linewidth=0.5, label="Regional / national registers")
  ax2.barh(y_pos, mono_arr, left=reg_arr, color="#d97706", edgecolor="#1e293b", linewidth=0.5, label="Academic monographs")
  ax2.barh(y_pos, c14_arr, left=reg_arr + mono_arr, color="#2a9d8f", edgecolor="#1e293b", linewidth=0.5, label="Primary radiocarbon")

  max_t = max(tot_vals) if tot_vals else 1.0
  ax2.set_yticks(y_pos)
  ax2.set_yticklabels([JURISDICTION_DISPLAY[jk] for jk in j_order], fontsize=8.0)
  ax2.set_xlim(0.0, max_t * 1.28)
  ax2.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5))
  ax2.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  for yp, tv in zip(y_pos, tot_vals):
    lbl_t = f"{tv:,}".replace(",", ".")
    ax2.text(tv + max_t * 0.022, yp, lbl_t, va="center", ha="left", fontsize=7.5, color="#0f172a")
  ax2.set_xlabel("Unique primary archaeological sites (0,0% crowdsourced)")
  ax2.set_title("B. Archaeological Provenance by Jurisdiction", fontsize=9.8, pad=6)
  ax2.legend(loc="lower right", fontsize=7.0, frameon=True, facecolor="white", framealpha=0.94)

  fig.subplots_adjust(left=0.09, right=0.97, top=0.88, bottom=0.14, wspace=0.42)
  save_viscount_figure(fig, os.path.join(FIG_DIR, "02_austral_kriging_diagnostics.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_fig3_secular_trajectory (arg0_root):
  """Figure 3: Secular population trajectory across all 6 AUSTRAL macro-regions (10000BC–2025)."""
  series = arg0_root.get("macro_reconciled_series") or arg0_root["macro_raster_series"]
  yrs_all = sorted(int(k) for k in series["total_austral"].keys())
  tot_all = [max(1.0, float(series["total_austral"][str(y)])) for y in yrs_all]

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 4.7), dpi=300, gridspec_kw={"wspace": 0.28})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Long-run semi-log Holocene trajectory (-10000 to 2025)
  ax1.semilogy(yrs_all, tot_all, "-o", linewidth=2.1, markersize=3.0, color="#111827", label="Total AUSTRAL")
  for mk, (mlbl, mcol) in MACRO_DISPLAY.items():
    vals = [float(series[mk].get(str(y), 0)) for y in yrs_all]
    pts = [(y, v) for y, v in zip(yrs_all, vals) if v >= 500.0]
    if pts:
      short_lbl = mlbl.split(" (")[0].replace(" & Tasmania", "").replace(" & Bismarcks", "").replace(" & Chathams", "").replace(" & Fiji", "").replace(" & Kiribati", "")
      ax1.semilogy([p[0] for p in pts], [p[1] for p in pts], "-", linewidth=1.35, color=mcol, label=short_lbl)

  ax1.set_xlim(-10400, 2250)
  ax1.set_ylim(5e3, max(tot_all) * 2.5)
  ax1.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, integer=True))
  ax1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: f"{int(abs(x))}BC" if x < 0 else ("1AD" if int(x) == 0 else f"{int(x)}")))
  apply_human_log_ticks(ax1, "y", arg2_semantic=True)
  ax1.set_xlabel("Calendar year")
  ax1.set_ylabel("Population (inhabitants, log scale)")
  ax1.set_title("A. Long-Run Trajectory (10000BC–2025)", fontsize=9.8, pad=6)
  ax1.legend(loc="upper left", fontsize=6.6, ncol=2, frameon=True, facecolor="white", framealpha=0.92)

  # Panel B: Modern expansion (1780–2025) on linear scale
  mod_yrs = [y for y in yrs_all if y >= 1780]
  tot_mod = [float(series["total_austral"][str(y)]) for y in mod_yrs]
  ax2.plot(mod_yrs, tot_mod, "-o", linewidth=2.1, markersize=3.4, color="#111827", label="Total AUSTRAL")
  for mk, (mlbl, mcol) in MACRO_DISPLAY.items():
    vals = [float(series[mk].get(str(y), 0)) for y in mod_yrs]
    short_lbl = mlbl.split(" (")[0].replace(" & Tasmania", "").replace(" & Bismarcks", "").replace(" & Chathams", "").replace(" & Fiji", "").replace(" & Kiribati", "")
    ax2.plot(mod_yrs, vals, "-", linewidth=1.45, color=mcol, label=short_lbl)

  ax2.set_xlim(1775, 2032)
  ax2.set_ylim(0.0, max(tot_mod) * 1.22)
  ax2.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, integer=True))
  ax2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  ax2.set_xlabel("Calendar year")
  ax2.set_ylabel("Population (inhabitants)")
  ax2.set_title("B. Colonial to Contemporary Expansion (1780–2025)", fontsize=9.8, pad=6)
  ax2.legend(loc="upper left", fontsize=6.7, frameon=True, facecolor="white", framealpha=0.92)

  fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.14, wspace=0.28)
  save_viscount_figure(fig, os.path.join(FIG_DIR, "03_austral_secular_trajectory.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_fig4_urban_hierarchy (arg0_root):
  """Figure 4: Pan-Oceanic urban hierarchy & rank-size Zipf distribution across AUSTRAL."""
  uh = arg0_root["pan_oceanic_urban_hierarchy"]
  top_list = uh["top_settlements"]
  pairs = uh["rank_pop_pairs_non_suburb"]
  zipf_fit = uh["zipf_non_suburb_unique"]

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 4.9), dpi=300, gridspec_kw={"width_ratios": [1.14, 1.0], "wspace": 0.42})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Top 14 distinct Oceanian urban centres (deduplicating metro vs city_proper pairs)
  seen_base = set()
  non_sub_top = []
  for s in top_list:
    if s.get("population_scope") == "suburb":
      continue
    base_nm = str(s["name"]).replace(" (Metro)", "").split(" - ")[0].strip().lower()
    if base_nm in seen_base:
      continue
    seen_base.add(base_nm)
    non_sub_top.append(s)
    if len(non_sub_top) >= 14:
      break
  show14 = list(reversed(non_sub_top))
  y_pos = np.arange(len(show14))
  vals_p = [int(x["peak_pop"]) for x in show14]
  cols_p = [MACRO_DISPLAY[COUNTRY_TO_MACRO.get(x["country"], "australia")][1] for x in show14]

  ax1.barh(y_pos, vals_p, color=cols_p, edgecolor="#1e293b", linewidth=0.5)
  ax1.set_yticks(y_pos)
  ax1.set_yticklabels([x["name"] for x in show14], fontsize=7.5)
  max_p = max(vals_p) if vals_p else 1.0
  ax1.set_xlim(0.0, max_p * 1.28)
  ax1.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=4))
  ax1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  for yp, vp in zip(y_pos, vals_p):
    ax1.text(vp + max_p * 0.022, yp, format_semantic_population(vp), va="center", ha="left", fontsize=7.0, color="#0f172a")
  ax1.set_xlabel("Peak settlement population")
  ax1.set_title("A. Largest Oceanian Urban Centres", fontsize=9.8, pad=6)

  # Panel B: Pan-Oceanic log-log rank-size distribution
  ranks = np.array([p[0] for p in pairs], dtype=np.float64)
  pops = np.array([p[1] for p in pairs], dtype=np.float64)
  n_all = len(pairs)
  n_fmt = f"{n_all:,}".replace(",", ".")
  ax2.loglog(ranks, pops, "o", markersize=2.2, alpha=0.45, color="#2563eb", label=f"Observed (n={n_fmt})")

  n_fit = int(zipf_fit["n_fit"])
  slope = float(zipf_fit["slope"])
  intercept = float(zipf_fit["intercept"])
  alpha_val = float(zipf_fit["zipf_alpha"])
  r2_val = float(zipf_fit["r2"])
  y_hat = 10.0 ** (slope * np.log10(ranks[:n_fit]) + intercept)
  ax2.loglog(
    ranks[:n_fit], y_hat, "-", linewidth=1.7, color="#dc2626",
    label=rf"Core Zipf fit ($\alpha = {format_mathtext_euro(alpha_val, 2)}$, $R^2 = {format_mathtext_euro(r2_val, 3)}$)"
  )
  ax2.set_xlim(0.8, n_all * 1.6)
  y_top = max(float(np.max(pops)), float(np.max(y_hat))) * 1.85
  ax2.set_ylim(max(10.0, float(pops.min()) * 0.65), y_top)
  apply_human_log_ticks(ax2, "both", arg2_semantic=True)
  ax2.set_xlabel("Settlement rank")
  ax2.set_ylabel("Peak population (inhabitants)")
  ax2.set_title("B. Pan-Oceanic Rank-Size Distribution", fontsize=9.8, pad=6)
  ax2.legend(loc="lower left", fontsize=7.2, frameon=True, facecolor="white", framealpha=0.92)

  fig.subplots_adjust(left=0.20, right=0.97, top=0.88, bottom=0.13, wspace=0.40)
  save_viscount_figure(fig, os.path.join(FIG_DIR, "04_austral_urban_hierarchy.png"), arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def main ():
  root_summary = json.load(open(os.path.join(SHARED, "austral_root_summary.json"), encoding="utf-8"))
  print("[1] Rendering Fig 1: 01_austral_overview_map.png ...", flush=True)
  render_fig1_overview_map()
  print("[2] Rendering Fig 2: 02_austral_kriging_diagnostics.png ...", flush=True)
  render_fig2_kriging_diagnostics(root_summary)
  print("[3] Rendering Fig 3: 03_austral_secular_trajectory.png ...", flush=True)
  render_fig3_secular_trajectory(root_summary)
  print("[4] Rendering Fig 4: 04_austral_urban_hierarchy.png ...", flush=True)
  render_fig4_urban_hierarchy(root_summary)
  print("[DONE] Generated all 4 root AUSTRAL synthesis figures cleanly.", flush=True)


if __name__ == "__main__":
  main()
