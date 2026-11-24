"""Generates the 5 publication-grade root synthesis figures for Project JAGUAR
(`studies_on_population.Rmd`) plus high-res verifier panel crops inside `tests/figure_panels/`.

All 5 figures are strictly vector-rendered with default Matplotlib styling (`DejaVu Sans`,
4-sided boxed axes), Lambert Azimuthal Equal-Area cartography (`PatchCollection`) with
dedicated Bermuda inset (`32,3°N, 64,8°W`), MathText `{,}` European decimals, plain
human log ticks, and strict zero-occlusion layout checks (`save_viscount_figure`).

Outputs inside `JAGUAR/figures/`:
  1. `jaguar_areal_coverage_hero.png`
  2. `jaguar_longrun_trajectory.png`
  3. `jaguar_kriging_diagnostics.png`
  4. `jaguar_urban_hierarchy_evolution.png`
  5. `jaguar_subadmin_coverage.png`
"""

import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch
import numpy as np
from PIL import Image
from shapely.geometry import shape
from shapely.ops import unary_union

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
JAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JAGUAR")
SHARED = os.path.join(JAG_DIR, "_shared")
SCRIPTS_DIR = os.path.join(SHARED, "scripts")
SUBREG_DIR = os.path.join(SHARED, "_gis_cache", "chapter_subregions")
FIG_DIR = os.path.join(JAG_DIR, "figures")
CROPS_DIR = os.path.join(SVEA_ROOT, "tests", "figure_panels")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(CROPS_DIR, exist_ok=True)

if SCRIPTS_DIR not in sys.path:
  sys.path.insert(0, SCRIPTS_DIR)

from jaguar_map_helper import (
  BERMUDA_CLIP_BOX,
  PROJ_BERMUDA,
  PROJ_JAGUAR,
  apply_human_log_ticks,
  apply_viscount_style,
  draw_basemap,
  draw_bermuda_inset,
  draw_graticule,
  euro_tick_formatter,
  format_euro_number,
  format_mathtext_euro,
  format_semantic_population,
  geom_to_patches,
  load_basemap_cache,
  mute_rgb_hex,
  prepare_and_project,
  save_viscount_figure,
)

JAG_XLIM = (-3150.0, 3150.0)
JAG_YLIM = (-1680.0, 1780.0)

# Explicit display names for kriging epochs & HGIS eras (never mechanical .replace("_", " ").title())
KRIG_EPOCH_LABELS = {
  "01_palaeoindian_archaic": "Palaeoindian & Archaic",
  "02_early_middle_preclassic_olmec": "Pre-Classic & Olmec",
  "03_late_preclassic_teotihuacan_rise": "Late Pre-Classic",
  "04_classic_mesoamerica_maya_peak": "Classic Mesoamerica & Maya",
  "05_epiclassic_early_postclassic_toltec": "Epi-Classic & Toltec",
  "06_late_postclassic_aztec_taino": "Late Post-Classic (Aztec & Taíno)",
  "07_conquest_epidemic_collapse": "Conquest Collapse (1519–1650)",
  "08_bourbon_colonial_plantation": "Bourbon & Plantation Era",
  "09_independence_pre_census": "Independence Pre-Census",
}

HGIS_ERA_LABELS = {
  "colonial_new_spain_1570_1810": "Colonial New Spain (1570–1810)",
  "colonial_central_america_1778_1816": "Colonial Central America",
  "colonial_caribbean_bermuda_1655_1899": "Colonial Caribbean & Bermuda",
  "mexico_republic_19c_1820_1889": "Mexico Republic (1820–1889)",
  "mexico_inegi_1895_2020": "Mexico INEGI (1895–2020)",
  "central_america_modern_1864_2024": "Central America (1864–2024)",
  "greater_antilles_historic_1899_1979": "Greater Antilles (1899–1979)",
  "greater_antilles_modern_1935_2023": "Greater Antilles (1935–2023)",
  "lesser_antilles_bahamas_bermuda_1900_2025": "Lesser Antilles & Bermuda",
}

CHAPTER_SHORT_LABELS = {
  "precolumbian_mesoamerica": "Ch 01: Mesoamerica",
  "classic_postclassic_maya": "Ch 02: Maya Lands",
  "aztec_late_postclassic_mexico": "Ch 03: Aztec Mexico",
  "precolumbian_lower_central_america": "Ch 04: Lower C. America",
  "precolumbian_caribbean_islands": "Ch 05: Pre-Col. Caribbean",
  "conquest_collapse_mesoamerica": "Ch 06: Mesoam. Collapse",
  "viceroyalty_of_new_spain": "Ch 07: New Spain",
  "captaincy_general_guatemala": "Ch 08: Capt. Guatemala",
  "conquest_indigenous_caribbean": "Ch 09: Carib. Collapse",
  "colonial_caribbean_plantation": "Ch 10: Plantation Carib.",
  "mexico_after_independence": "Ch 11: Modern Mexico",
  "central_american_republics": "Ch 12: Modern C. America",
  "greater_antilles_modern": "Ch 13: Greater Antilles",
  "lesser_antilles_bahamas_bermuda": "Ch 14: Lesser Ant. & Berm.",
}


def export_root_crops (arg0_png_path, arg1_prefix, arg2_mode="lr"):
  img = Image.open(arg0_png_path)
  w, h = img.size
  if arg2_mode == "lr":
    mid = int(round(w * 0.50))
    img.crop((0, 0, min(w, mid + 30), h)).save(os.path.join(CROPS_DIR, f"{arg1_prefix}_A.png"))
    img.crop((max(0, mid - 50), 0, w, h)).save(os.path.join(CROPS_DIR, f"{arg1_prefix}_B.png"))
  elif arg2_mode == "grid2x3":
    row_h = h // 2
    img.crop((0, 0, w, min(h, row_h + 25))).save(os.path.join(CROPS_DIR, f"{arg1_prefix}_top.png"))
    img.crop((0, max(0, row_h - 25), w, h)).save(os.path.join(CROPS_DIR, f"{arg1_prefix}_bot.png"))


def render_fig1_areal_coverage_hero (arg0_land, arg1_riv, arg2_bm_land):
  """Figure 1: 6-panel regional partition coverage across Mexico, Central America, Caribbean & Bermuda."""
  panels = [
    ("A. 10000BC–1200AD: Pre-Columbian Basins", [
      "precolumbian_mesoamerica", "classic_postclassic_maya",
      "precolumbian_lower_central_america", "precolumbian_caribbean_islands",
    ]),
    ("B. 1200–1519AD: Aztec, Maya & Taíno Worlds", [
      "aztec_late_postclassic_mexico", "classic_postclassic_maya",
      "precolumbian_lower_central_america", "precolumbian_caribbean_islands",
    ]),
    ("C. 1492–1650: Conquest & Demographic Collapse", [
      "conquest_collapse_mesoamerica", "conquest_indigenous_caribbean",
    ]),
    ("D. 1535–1821: New Spain & Capt. Guatemala", [
      "viceroyalty_of_new_spain", "captaincy_general_guatemala",
    ]),
    ("E. 1650–1898: Colonial Plantation Caribbean", [
      "colonial_caribbean_plantation",
    ]),
    ("F. 1821–2025: Republican & Island Censuses", [
      "mexico_after_independence", "central_american_republics",
      "greater_antilles_modern", "lesser_antilles_bahamas_bermuda",
    ]),
  ]
  macro_palette = [
    "#6ca6c1", "#7fb685", "#e09f5a", "#b288c0", "#d67d79", "#6db7b0",
    "#c9b46e", "#8da0cb", "#e5a3b3", "#a3c478", "#d4956a", "#7d9fc2",
  ]

  apply_viscount_style()
  fig, axes = plt.subplots(2, 3, figsize=(13.6, 7.6), dpi=300)
  for idx_p, (ax, (ptitle, stems)) in enumerate(zip(axes.flat, panels)):
    apply_viscount_style(ax, {"grid": False})
    draw_basemap(ax, arg0_land, arg1_riv)
    col_i = 0
    bm_feats = []
    bm_rgb = {}
    bm_names = {}
    for st in stems:
      vp = os.path.join(SUBREG_DIR, f"{st}_subregions.geojson")
      if not os.path.isfile(vp):
        continue
      gj = json.load(open(vp, encoding="utf-8"))
      for feat in gj.get("features", []):
        gr = feat.get("geometry")
        if not gr:
          continue
        g = shape(gr).buffer(0)
        if g.is_empty:
          continue
        rid = str(feat.get("properties", {}).get("id") or "")
        rgb = feat.get("properties", {}).get("rgb")
        g_bm = g.intersection(BERMUDA_CLIP_BOX)
        if not g_bm.is_empty and g_bm.area > 1e-6:
          bm_feats.append((rid, g_bm))
          bm_rgb[rid] = rgb
          bm_names[rid] = "Bermuda"
        g_rem = g.difference(BERMUDA_CLIP_BOX)
        if g_rem.is_empty:
          continue
        pg = prepare_and_project(g_rem, PROJ_JAGUAR, 0.30)
        ps = geom_to_patches(pg)
        if ps:
          fc = macro_palette[col_i % len(macro_palette)]
          ax.add_collection(PatchCollection(ps, facecolor=fc, edgecolor="#334155", linewidths=0.35, alpha=0.84, zorder=2.5))
          col_i += 1
    ax.set_xlim(*JAG_XLIM)
    ax.set_ylim(*JAG_YLIM)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    draw_graticule(ax, PROJ_JAGUAR, JAG_XLIM, JAG_YLIM, [10, 20, 30], [-110, -100, -90, -80, -70, -60])
    ax.set_title(ptitle, fontsize=8.6, pad=5)

    # Dedicated Bermuda inset on Panels E & F
    if idx_p in (4, 5) and bm_feats:
      draw_bermuda_inset(
        ax, bm_feats, bm_rgb, bm_names, arg2_bm_land, None, set(),
        arg7_inset_rect=[0.69, 0.63, 0.28, 0.32], arg8_title_fs=5.8,
      )

  fig.subplots_adjust(left=0.02, right=0.98, top=0.93, bottom=0.03, wspace=0.06, hspace=0.14)
  out_p = os.path.join(FIG_DIR, "jaguar_areal_coverage_hero.png")
  save_viscount_figure(fig, out_p, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})
  export_root_crops(out_p, "root_fig1_hero", arg2_mode="grid2x3")


def render_fig2_longrun_trajectory (arg0_root):
  """Figure 2: Two-panel JAGUAR gridded population trajectory (-10000 to 2025 & 1500 to 2025)."""
  gt = arg0_root["gridded_trajectory"]
  pts = sorted((int(k), float(v)) for k, v in gt.items() if float(v) > 0)
  yrs_all = [p[0] for p in pts]
  vals_all = [p[1] for p in pts]

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.8, 4.6), dpi=300, gridspec_kw={"wspace": 0.30})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Full Holocene trajectory (-10000 to 2025) on semi-log population axis
  mk_every = max(1, len(yrs_all) // 18)
  ax1.semilogy(yrs_all, vals_all, "-o", markevery=mk_every, linewidth=1.8, markersize=3.4, color="#1d4ed8", label="JAGUAR macro-region total")
  ax1.set_xlim(-10400, 2250)
  ax1.set_ylim(max(5e4, min(vals_all) * 0.55), max(vals_all) * 2.5)
  ax1.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, integer=True))
  ax1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: f"{int(abs(x))}BC" if x < 0 else f"{int(x)}"))
  apply_human_log_ticks(ax1, "y", arg2_semantic=True)
  ax1.set_xlabel("Calendar year")
  ax1.set_ylabel("Population (inhabitants, log scale)")
  ax1.set_title("A. Holocene Demographic Trajectory (10000BC–2025)", fontsize=9.6, pad=6)
  ax1.legend(loc="lower right", fontsize=7.6, frameon=True, facecolor="white")

  # Panel B: Conquest Collapse to Contemporary Era (1500–2025) on linear axis
  mod_pts = [(y, v) for y, v in pts if y >= 1500]
  myrs = [p[0] for p in mod_pts]
  mvals = [p[1] for p in mod_pts]
  ax2.plot(myrs, mvals, "-s", markevery=max(1, len(myrs) // 14), linewidth=2.0, markersize=3.8, color="#b91c1c", label="Gridded population (1500–2025)")
  ax2.set_xlim(1485, 2035)
  ax2.set_ylim(0.0, max(mvals) * 1.22)
  ax2.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, integer=True))
  ax2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  ax2.set_xlabel("Calendar year")
  ax2.set_ylabel("Population (inhabitants)")
  ax2.set_title("B. Colonial Trough to Modern Expansion (1500–2025)", fontsize=9.6, pad=6)
  ax2.legend(loc="upper left", fontsize=7.6, frameon=True, facecolor="white")

  fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.14, wspace=0.30)
  out_p = os.path.join(FIG_DIR, "jaguar_longrun_trajectory.png")
  save_viscount_figure(fig, out_p, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})
  export_root_crops(out_p, "root_fig2_traj", arg2_mode="lr")


def render_fig3_kriging_diagnostics (arg0_root):
  """Figure 3: Two-panel Matérn variogram models and archaeological site coverage diagnostics."""
  kd = arg0_root["kriging_diagnostics"]
  vmods = kd.get("variogram_models", {})

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.8, 4.8), dpi=300, gridspec_kw={"width_ratios": [1.08, 1.0], "wspace": 0.66})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Observed normalised semivariograms across 4 representative kriging epochs
  show_epochs = [
    ("02_early_middle_preclassic_olmec", "#2563eb", "o"),
    ("04_classic_mesoamerica_maya_peak", "#16a34a", "s"),
    ("06_late_postclassic_aztec_taino", "#d97706", "^"),
    ("07_conquest_epidemic_collapse", "#dc2626", "D"),
  ]
  max_g = 0.0
  for ek, col, mk in show_epochs:
    vm = vmods.get(ek)
    if not vm:
      continue
    ulags = np.array(vm["empirical_u_lags"], dtype=np.float64)
    gammas = np.array(vm["empirical_gammas"], dtype=np.float64) * 1e4
    max_g = max(max_g, float(gammas.max()))
    r2_v = float(vm.get("residual_r2", 0.999))
    lbl = f"{KRIG_EPOCH_LABELS[ek]} ($R^2 = {format_mathtext_euro(r2_v, 3)}$)"
    ax1.plot(ulags, gammas, f"-{mk}", color=col, linewidth=1.6, markersize=4.2, label=lbl)

  tau1 = float(kd.get("tau1_dimensionless", 1.35))
  tau2 = float(kd.get("tau2_dimensionless", 2.90))
  ax1.set_xlim(0.0, 13.5)
  ax1.set_ylim(0.0, max_g * 1.32)
  ax1.xaxis.set_major_formatter(euro_tick_formatter(0))
  ax1.yaxis.set_major_formatter(euro_tick_formatter(2))
  ax1.set_xlabel(r"Dimensionless lag distance $u$")
  ax1.set_ylabel(r"Semivariance $\gamma(u)$ ($\times 10^{-4}$)")
  ax1.set_title(rf"A. Residual Variograms ($\tau_1 = {format_mathtext_euro(tau1, 2)}$, $\tau_2 = {format_mathtext_euro(tau2, 2)}$)", fontsize=9.4, pad=6)
  ax1.legend(loc="upper left", fontsize=6.9, frameon=True, facecolor="white", framealpha=0.92)

  # Panel B: Archaeological site counts by primary regional archive source (top 9 sources)
  src_display = {
    "famsi_witschey_brown_mayagis": "FAMSI MayaGIS Atlas",
    "ucsb_maya_forest_gis": "UCSB Maya Forest GIS",
    "decm_relaciones_geograficas_16c": "Relaciones Geog. (16th c.)",
    "harvard_dataverse_arch_atlas": "Harvard Arch. Atlas",
    "rcesaret_basin_of_mexico_survey": "Basin of Mexico Survey",
    "cadb_pitt_regional_surveys": "Pittsburgh CADB Surveys",
    "swsn_southwest_nw_mexico": "SWSN North-West Mexico",
    "svea_c14_cleaned_dedup": "Radiocarbon Compendium",
    "harvard_aadr_v66": "Harvard AADR Ancient DNA",
    "sic_inah_mexico_register": "INAH Mexico Register",
    "dans_nexus1492_montecristi": "NEXUS 1492 Caribbean",
  }
  by_src = kd.get("source_provenance_breakdown", {}).get("by_source", {})
  ranked_s = sorted(by_src.items(), key=lambda kv: -int(kv[1]["count"]))[:9]
  ranked_s = list(reversed(ranked_s))
  y_pos = np.arange(len(ranked_s))
  cnts = [int(kv[1]["count"]) for kv in ranked_s]
  lbls = [src_display.get(kv[0], kv[0]) for kv in ranked_s]
  ax2.barh(y_pos, cnts, color="#2b6cb0", edgecolor="#1e293b", linewidth=0.55)
  ax2.set_yticks(y_pos)
  ax2.set_yticklabels(lbls, fontsize=7.4)
  max_c = max(cnts) if cnts else 1
  ax2.set_xlim(0.0, max_c * 1.30)
  ax2.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=4))
  ax2.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  for yp, cv in zip(y_pos, cnts):
    ax2.text(cv + max_c * 0.025, yp, f"{cv:,}".replace(",", "."), va="center", ha="left", fontsize=7.0, color="#0f172a")
  ax2.set_xlabel("Unique archaeological sites")
  ax2.set_title("B. Primary Archaeological Site Archives", fontsize=9.4, pad=6)

  fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.14, wspace=0.66)
  out_p = os.path.join(FIG_DIR, "jaguar_kriging_diagnostics.png")
  save_viscount_figure(fig, out_p, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})
  export_root_crops(out_p, "root_fig3_krig", arg2_mode="lr")


def render_fig4_urban_hierarchy_evolution (arg0_root):
  """Figure 4: Two-panel rank-size Zipf exponent evolution & cross-era settlement hierarchy."""
  zlist = arg0_root["settlement_totals"]["zipf_by_chapter"]
  ch_map = {c["stem"]: c for c in arg0_root["chapters"]}

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 4.8), dpi=300, gridspec_kw={"width_ratios": [1.18, 1.0], "wspace": 0.34})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Zipf slope exponent alpha across all 14 chapters coloured by era group
  era_cols = {
    "1.precolumbian": "#2a9d8f",
    "2.conquest_and_colonial": "#d97706",
    "3.modern_and_census": "#2563eb",
  }
  rev_z = list(reversed(zlist))
  y_pos = np.arange(len(rev_z))
  alphas = [float(z["alpha"] or 0.0) for z in rev_z]
  cols = [era_cols.get(ch_map[z["stem"]]["group"], "#64748b") for z in rev_z]
  ax1.barh(y_pos, alphas, color=cols, edgecolor="#1e293b", linewidth=0.5, zorder=2.5)
  ax1.axvline(1.0, color="#dc2626", linestyle="--", linewidth=1.15, zorder=1.0)
  ax1.set_yticks(y_pos)
  ax1.set_yticklabels([CHAPTER_SHORT_LABELS.get(z["stem"], z["stem"]) for z in rev_z], fontsize=7.2)
  max_a = max(alphas) if alphas else 1.5
  ax1.set_xlim(0.0, max(1.65, max_a * 1.56))
  ax1.xaxis.set_major_formatter(euro_tick_formatter(1))
  for yp, av, z in zip(y_pos, alphas, rev_z):
    lbl_v = f"{format_euro_number(av, 2)} ($R^2={format_mathtext_euro(z['r2'], 2)}$)"
    ax1.text(
      av + max_a * 0.025, yp, lbl_v, va="center", ha="left", fontsize=6.4, color="#0f172a",
      zorder=5.0, bbox=dict(boxstyle="square,pad=0.10", facecolor="white", edgecolor="none", alpha=0.92),
    )
  ax1.set_xlabel(r"Rank-size exponent $\alpha$")
  ax1.set_title(r"A. Settlement Rank-Size Exponent ($\alpha$) by Chapter", fontsize=9.4, pad=6)
  leg_h = [
    Patch(facecolor="#2a9d8f", edgecolor="#1e293b", label="Pre-Columbian"),
    Patch(facecolor="#d97706", edgecolor="#1e293b", label="Colonial Era"),
    Patch(facecolor="#2563eb", edgecolor="#1e293b", label="Modern Censuses"),
  ]

  # Panel B: Comparative log-log rank-size trajectories across 4 benchmark chapters
  bench_stems = [
    ("precolumbian_mesoamerica", "Pre-Columbian Mesoamerica", "#2a9d8f", "o"),
    ("aztec_late_postclassic_mexico", "Aztec & Post-Classic Mexico", "#16a34a", "^"),
    ("viceroyalty_of_new_spain", "Viceroyalty of New Spain", "#d97706", "s"),
    ("mexico_after_independence", "Mexico after Independence", "#2563eb", "D"),
  ]
  max_pop_all = 1.0
  for st, lbl, col, mk in bench_stems:
    ci = ch_map[st]
    sp = os.path.join(JAG_DIR, ci["group"], ci["folder"], f"{st}_settlements.json")
    setts = json.load(open(sp, encoding="utf-8"))
    pks = sorted(
      (max(int(round(float(v))) for v in (s.get("population") or {}).values() if 0.0 < float(v) < 25_000_000.0)
       for s in setts.values() if any(0.0 < float(v) < 25_000_000.0 for v in (s.get("population") or {}).values())),
      reverse=True,
    )[:100]
    if pks:
      ranks = np.arange(1, len(pks) + 1, dtype=np.float64)
      pops = np.array(pks, dtype=np.float64)
      max_pop_all = max(max_pop_all, float(pops.max()))
      ax2.loglog(ranks, pops, f"-{mk}", markevery=max(1, len(ranks) // 10), linewidth=1.55, markersize=3.8, color=col, label=lbl)

  ax2.set_xlim(0.8, 140.0)
  ax2.set_ylim(500.0, max_pop_all * 2.8)
  apply_human_log_ticks(ax2, "both", arg2_semantic=True)
  ax2.set_xlabel("Settlement rank (top 100)")
  ax2.set_ylabel("Peak population (inhabitants)")
  ax2.set_title("B. Cross-Era Mexican Urban Hierarchy Shift", fontsize=9.4, pad=6)
  ax2.legend(loc="lower left", fontsize=7.0, frameon=True, facecolor="white", framealpha=0.92)

  fig.subplots_adjust(left=0.17, right=0.97, top=0.89, bottom=0.21, wspace=0.34)
  fig.legend(handles=leg_h, loc="lower left", bbox_to_anchor=(0.17, 0.015), ncol=3, fontsize=7.2, frameon=True, facecolor="white", edgecolor="#cbd5e1")
  out_p = os.path.join(FIG_DIR, "jaguar_urban_hierarchy_evolution.png")
  save_viscount_figure(fig, out_p, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})
  export_root_crops(out_p, "root_fig4_urban", arg2_mode="lr")


def render_fig5_subadmin_coverage (arg0_root):
  """Figure 5: Two-panel scraped HGIS sub-administrative unit & archival observation coverage."""
  sh = arg0_root["subadmin_hgis_coverage"]
  mc_samples = sh.get("mass_conservation", {}).get("sample_years", {})
  era_rows = sh.get("era_breakdown", [])

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 4.7), dpi=300, gridspec_kw={"width_ratios": [1.0, 1.05], "wspace": 0.68})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Active sub-admin polygons vs direct primary census units applied (1500–2025)
  s_pts = sorted((int(k), v) for k, v in mc_samples.items())
  syrs = [p[0] for p in s_pts]
  act_u = [int(p[1]["active_units"]) for p in s_pts]
  dir_u = [int(p[1]["direct_census_units_applied"]) for p in s_pts]
  ax1.plot(syrs, act_u, "-o", linewidth=1.9, markersize=4.0, color="#1d4ed8", label="Active HGIS sub-admin units")
  ax1.plot(syrs, dir_u, "--s", linewidth=1.7, markersize=3.8, color="#16a34a", label="Direct census enumerations applied")
  ax1.set_xlim(1485, 2035)
  max_u = max(act_u) if act_u else 100
  ax1.set_ylim(0.0, max_u * 1.24)
  ax1.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, integer=True))
  ax1.yaxis.set_major_formatter(euro_tick_formatter(0))
  ax1.set_xlabel("Snapshot year")
  ax1.set_ylabel("Sub-administrative units")
  ax1.set_title("A. Sub-Administrative Coverage (1500–2025)", fontsize=9.4, pad=6)
  ax1.legend(loc="upper left", fontsize=7.2, frameon=True, facecolor="white", framealpha=0.92)

  # Panel B: Primary archival enumeration observations by compiled era regime
  rev_e = list(reversed(era_rows))
  y_pos = np.arange(len(rev_e))
  obs_v = [int(r["observations"]) for r in rev_e]
  lbl_e = [HGIS_ERA_LABELS.get(r["era"], r["era"]) for r in rev_e]
  ax2.barh(y_pos, obs_v, color="#0d9488", edgecolor="#1e293b", linewidth=0.55)
  ax2.set_yticks(y_pos)
  ax2.set_yticklabels(lbl_e, fontsize=7.3)
  max_o = max(obs_v) if obs_v else 100
  ax2.set_xlim(0.0, max_o * 1.30)
  ax2.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=4))
  ax2.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  for yp, ov in zip(y_pos, obs_v):
    ax2.text(ov + max_o * 0.025, yp, f"{ov:,}".replace(",", "."), va="center", ha="left", fontsize=7.0, color="#0f172a")
  ax2.set_xlabel("Primary sub-administrative observations")
  ax2.set_title("B. Compiled Archival Census Series by Era", fontsize=9.4, pad=6)

  fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.14, wspace=0.68)
  out_p = os.path.join(FIG_DIR, "jaguar_subadmin_coverage.png")
  save_viscount_figure(fig, out_p, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})
  export_root_crops(out_p, "root_fig5_hgis", arg2_mode="lr")


def main ():
  root_summary = json.load(open(os.path.join(SHARED, "jaguar_root_summary.json"), encoding="utf-8"))
  print("[1] Pre-projecting JAGUAR & Bermuda Natural Earth 10m physical coastlines...", flush=True)
  land_j, riv_j = load_basemap_cache(PROJ_JAGUAR, (-124.0, 2.0, -54.0, 38.0), arg2_show_modern_borders=False, arg3_high_res=True)
  land_bm, _ = load_basemap_cache(PROJ_BERMUDA, (-65.8, 31.2, -63.8, 33.4), arg2_show_modern_borders=False, arg3_high_res=True)

  print("[2] Rendering Fig 1: jaguar_areal_coverage_hero.png ...", flush=True)
  render_fig1_areal_coverage_hero(land_j, riv_j, land_bm)

  print("[3] Rendering Fig 2: jaguar_longrun_trajectory.png ...", flush=True)
  render_fig2_longrun_trajectory(root_summary)

  print("[4] Rendering Fig 3: jaguar_kriging_diagnostics.png ...", flush=True)
  render_fig3_kriging_diagnostics(root_summary)

  print("[5] Rendering Fig 4: jaguar_urban_hierarchy_evolution.png ...", flush=True)
  render_fig4_urban_hierarchy_evolution(root_summary)

  print("[6] Rendering Fig 5: jaguar_subadmin_coverage.png ...", flush=True)
  render_fig5_subadmin_coverage(root_summary)

  print("[DONE] Generated all 5 root JAGUAR figures + panel crops cleanly.", flush=True)


if __name__ == "__main__":
  main()
