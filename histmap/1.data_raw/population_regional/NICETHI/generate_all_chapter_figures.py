"""Generates POLARIS-grade vector cartography and demographic figures for all 23 Project NICETHI chapters.

Produces three publication figures per chapter inside `<chapter_dir>/figures/`:
  1. `fig_01_map.png` — Lambert Azimuthal Equal-Area vector PatchCollection sub-regions,
     Natural Earth 10m coastlines & rivers, curved graticule, dedicated multi-panel/inset
     layouts for archipelago chapters (Ch. 10, Ch. 17) and distant ocean islands (Ch. 01),
     proportional settlement markers, in-bounds callouts and clean bottom legend.
  2. `fig_02_trends.png` — Three-panel demographic trends: total regional & attested urban
     population trajectories, recorded settlement count growth, and leading urban centre curves.
  3. `fig_03_rank_size.png` — Two-panel Zipf rank-size distribution (strictly n >= 25) on
     plain human European log-log axes with OLS Pareto slope q & R^2, plus sub-regional
     end-epoch population density (inhabitants / km²) bar chart.
"""

import json
import math
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch
import numpy as np
from shapely.geometry import box, shape
from shapely.ops import unary_union

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
NIC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "NICETHI")
SHARED = os.path.join(NIC_DIR, "_shared")
SCRIPTS_DIR = os.path.join(SHARED, "scripts")
SUBREG_DIR = os.path.join(SHARED, "_gis_cache", "chapter_subregions")
CACHE_PATH = os.path.join(SHARED, "nicethi_figure_cache.json")

if SCRIPTS_DIR not in sys.path:
  sys.path.insert(0, SCRIPTS_DIR)

from nicethi_map_helper import (
  BasemapSource10m,
  COUNTRY_PALETTE,
  ISO3_DISPLAY,
  LambertAzimuthalEqualArea,
  PROJ_AFRICA,
  PROJ_CABO_VERDE,
  PROJ_GULF_GUINEA,
  PROJ_ST_HELENA,
  PROJ_WIO,
  apply_human_log_ticks,
  apply_viscount_style,
  draw_basemap,
  draw_graticule,
  euro_tick_formatter,
  format_euro_number,
  format_mathtext_euro,
  format_semantic_population,
  geom_to_patches,
  mute_rgb_hex,
  pad_projected_bounds,
  place_inbounds_callouts,
  prepare_and_project,
  save_viscount_figure,
  tint_country_shade,
)


def format_year_label (arg0_yr):
  y = int(arg0_yr)
  if y < 0:
    return f"{abs(y)}BC"
  return f"{y}AD" if y <= 1500 else str(y)


def clean_subregion_label (arg0_name, arg1_max=28):
  s = str(arg0_name or "").strip()
  s = re.sub(r"\s*\[[^\]]*\]\s*", "", s).strip()
  s = s.replace("Nothern Cape", "Northern Cape")
  s = s.replace("La Reunion (France — DOM 974)", "La Réunion")
  s = s.replace("Mayotte (France — DOM 976)", "Mayotte")
  if len(s) <= arg1_max:
    return s
  return s[: arg1_max - 1].rstrip(" ,;-(") + "…"


def plot_proportional_settlements (arg0_ax, arg1_cities, arg2_proj, arg3_xlim, arg4_ylim, arg5_all_pts=None):
  """Plots optional settlement cloud + proportional circles sized by peak population."""
  if arg5_all_pts:
    xs_c, ys_c = [], []
    for lon, lat in arg5_all_pts:
      px, py = arg2_proj.fwd_pt(lon, lat)
      if arg3_xlim[0] <= px <= arg3_xlim[1] and arg4_ylim[0] <= py <= arg4_ylim[1]:
        xs_c.append(px)
        ys_c.append(py)
    if xs_c:
      n_c = len(xs_c)
      pt_s = 1.1 if n_c > 1200 else (2.4 if n_c > 350 else 5.0)
      pt_a = 0.24 if n_c > 1200 else 0.34
      arg0_ax.scatter(xs_c, ys_c, s=pt_s, c="#334155", alpha=pt_a, linewidths=0.0, zorder=4.6)

  xs_p, ys_p, sz_p = [], [], []
  max_pk = max((float(c["peak_pop"]) for c in arg1_cities), default=1.0)
  for c in arg1_cities:
    px, py = arg2_proj.fwd_pt(c["lon"], c["lat"])
    if arg3_xlim[0] <= px <= arg3_xlim[1] and arg4_ylim[0] <= py <= arg4_ylim[1]:
      xs_p.append(px)
      ys_p.append(py)
      sz_p.append(12.0 + 62.0 * math.sqrt(max(0.0, float(c["peak_pop"])) / max(1.0, max_pk)))
  if xs_p:
    arg0_ax.scatter(xs_p, ys_p, s=sz_p, c="#dc2626", alpha=0.72, edgecolors="white", linewidths=0.55, zorder=5.4)


def render_archipelago_map (arg0_ch, arg1_gj, arg2_bm_src, arg3_out_path):
  """Dedicated 4-panel GridSpec equal-area map for Ch. 10 & Ch. 17 spanning >90° of longitude."""
  is_adm1 = bool(arg0_ch["is_admin1"])
  rgb_map = {r["id"]: r["rgb"] for r in arg0_ch["subregions"]}
  name_map = {r["id"]: r["name"] for r in arg0_ch["subregions"]}
  iso_map = {r["id"]: r["iso3"] for r in arg0_ch["subregions"]}

  # Assign palette per country if admin1
  uniq_isos = sorted(set(v for v in iso_map.values() if v))
  iso_color = {iso: COUNTRY_PALETTE[i % len(COUNTRY_PALETTE)] for i, iso in enumerate(uniq_isos)}
  iso_counter = {iso: 0 for iso in uniq_isos}

  # Spatial clip boxes for the 4 equal-area panels
  box_wio = box(39.0, -27.5, 65.5, -2.5)
  box_cv = box(-26.2, 14.3, -22.2, 17.6)
  box_stp = box(5.8, -0.5, 8.2, 2.2)
  box_shn = box(-6.15, -16.25, -5.30, -15.65)

  wio_feats, cv_feats, stp_feats, shn_feats = [], [], [], []
  feat_colors = {}
  for idx_f, feat in enumerate(arg1_gj.get("features", [])):
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    g = shape(geom_raw).buffer(0)
    if g.is_empty:
      continue
    rid = str(feat.get("properties", {}).get("id") or "")
    if is_adm1:
      iso = iso_map.get(rid, rid.split("_")[0].upper())
      fc = tint_country_shade(iso_color.get(iso, (120, 150, 180)), iso_counter.get(iso, 0))
      iso_counter[iso] = iso_counter.get(iso, 0) + 1
    else:
      fc = mute_rgb_hex(rgb_map.get(rid), idx_f, 0.34)
    feat_colors[rid] = fc

    for target_list, cbox in (
      (wio_feats, box_wio),
      (cv_feats, box_cv),
      (stp_feats, box_stp),
      (shn_feats, box_shn),
    ):
      gi = g.intersection(cbox)
      if not gi.is_empty and gi.area > 1e-6:
        target_list.append((rid, gi, fc))

  apply_viscount_style()
  fig = plt.figure(figsize=(11.8, 7.6), dpi=300)
  gs = fig.add_gridspec(3, 2, width_ratios=[1.75, 1.0], wspace=0.08, hspace=0.22)
  ax_wio = fig.add_subplot(gs[:, 0])
  ax_cv = fig.add_subplot(gs[0, 1])
  ax_stp = fig.add_subplot(gs[1, 1])
  ax_shn = fig.add_subplot(gs[2, 1])

  panel_defs = [
    (ax_wio, PROJ_WIO, wio_feats, (38.0, -28.0, 66.0, -2.0), "A. Madagascar & Western Indian Ocean", 0.92, 1.18, 900.0, (-25, -20, -15, -10, -5), (40, 45, 50, 55, 60)),
    (ax_cv, PROJ_CABO_VERDE, cv_feats, (-26.2, 14.2, -22.0, 17.8), "B. Cabo Verde Archipelago", 1.38, 1.25, 360.0, (15, 16, 17), (-25, -24, -23)),
    (ax_stp, PROJ_GULF_GUINEA, stp_feats, (5.5, -0.6, 8.4, 2.3), "C. São Tomé and Príncipe", 1.38, 1.35, 260.0, (0, 1, 2), (6, 7, 8)),
    (ax_shn, PROJ_ST_HELENA, shn_feats, (-6.25, -16.30, -5.20, -15.60), "D. Saint Helena Island", 1.38, 1.55, 42.0, (-16,), (-6,)),
  ]

  top_cities = arg0_ch["top_cities"]
  all_city_pts = [(c["lon"], c["lat"]) for c in top_cities]
  panel_bounds = {}

  for ax, proj, flist, cbb, ptitle, asp, padf, min_km, glats, glons in panel_defs:
    apply_viscount_style(ax, {"grid": False})
    land_p, riv_g = arg2_bm_src.load_for_extent(proj, cbb, arg2_show_modern_borders=is_adm1)
    draw_basemap(ax, land_p, riv_g)

    pgs = []
    for rid, g, fc in flist:
      pg = prepare_and_project(g, proj, 0.15)
      if pg.is_empty:
        continue
      pgs.append(pg)
      ps = geom_to_patches(pg)
      if ps:
        ax.add_collection(PatchCollection(ps, facecolor=fc, edgecolor="#1e293b", linewidths=0.55, alpha=0.90, zorder=2.6))

    if pgs:
      u_pg = unary_union([p.buffer(0) for p in pgs])
      xl, yl = pad_projected_bounds(u_pg.bounds, arg1_target_aspect=asp, arg2_pad_factor=padf, arg3_min_span_km=min_km)
    else:
      x0, y0 = proj.fwd_pt(cbb[0], cbb[1])
      x1, y1 = proj.fwd_pt(cbb[2], cbb[3])
      xl, yl = (min(x0, x1), max(x0, x1)), (min(y0, y1), max(y0, y1))

    ax.set_xlim(*xl)
    ax.set_ylim(*yl)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    draw_graticule(ax, proj, xl, yl, glats, glons, (cbb[0] - 2, cbb[2] + 2), (cbb[1] - 2, cbb[3] + 2))
    plot_proportional_settlements(ax, top_cities, proj, xl, yl)
    ax.set_title(ptitle, fontsize=8.8, pad=4)
    panel_bounds[ax] = (proj, xl, yl)

  # Build clean bottom legend
  legend_handles = []
  if is_adm1:
    for iso in uniq_isos:
      fc = mute_rgb_hex(iso_color[iso], 0, 0.36)
      legend_handles.append(Patch(facecolor=fc, edgecolor="#1e293b", linewidth=0.55, label=ISO3_DISPLAY.get(iso, iso)))
  else:
    for sr in arg0_ch["subregions"]:
      rid = sr["id"]
      fc = feat_colors.get(rid, mute_rgb_hex(sr["rgb"], 0, 0.34))
      legend_handles.append(Patch(facecolor=fc, edgecolor="#1e293b", linewidth=0.55, label=clean_subregion_label(name_map.get(rid, rid), 28)))

  n_leg = len(legend_handles)
  ncol = 4 if n_leg >= 9 else 3
  nrows = math.ceil(n_leg / max(1, ncol))
  bot_margin = min(0.24, 0.055 + 0.036 * nrows)
  d0, d1 = arg0_ch["domain"]
  fig.suptitle(f"{arg0_ch['title']} ({format_year_label(d0)}–{format_year_label(d1)})", fontsize=10.8, y=0.975)
  fig.subplots_adjust(left=0.03, right=0.97, top=0.91, bottom=bot_margin, wspace=0.08, hspace=0.22)

  if legend_handles:
    fig.legend(
      handles=legend_handles,
      loc="lower center",
      ncol=ncol,
      fontsize=7.0,
      frameon=True,
      facecolor="white",
      edgecolor="#cbd5e1",
      bbox_to_anchor=(0.5, 0.012),
    )

  # Place in-bounds callouts on each panel
  callout_items = [{"label": clean_subregion_label(c["name"], 16), "lon": c["lon"], "lat": c["lat"]} for c in top_cities[:22]]
  for ax, max_l, min_s in ((ax_wio, 6, 48.0), (ax_cv, 2, 34.0), (ax_stp, 1, 30.0), (ax_shn, 1, 30.0)):
    proj, xl, yl = panel_bounds[ax]
    place_inbounds_callouts(
      fig, ax, callout_items, proj, xl, yl,
      {"max_labels": max_l, "min_sep_px": min_s, "fontsize": 6.4, "margin_px": 8.0, "dot_color": "#b91c1c"},
    )

  save_viscount_figure(fig, arg3_out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_chapter_map (arg0_ch, arg1_bm_src):
  key = arg0_ch["key"]
  ch_dir = os.path.join(NIC_DIR, arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", "fig_01_map.png")
  vec_path = os.path.join(SUBREG_DIR, f"{key}_subregions.geojson")
  gj = json.load(open(vec_path, encoding="utf-8"))

  if key in ("early_african_islands", "modern_african_islands"):
    render_archipelago_map(arg0_ch, gj, arg1_bm_src, out_path)
    return

  is_adm1 = bool(arg0_ch["is_admin1"])
  rgb_map = {r["id"]: r["rgb"] for r in arg0_ch["subregions"]}
  name_map = {r["id"]: r["name"] for r in arg0_ch["subregions"]}
  iso_map = {r["id"]: r["iso3"] for r in arg0_ch["subregions"]}

  # Clip prehistoric_ssa distant Atlantic/Chagos micro-islands into dedicated inset so mainland stays large
  box_main_af = box(-18.5, -36.0, 53.0, 28.5)
  box_cv_in = box(-26.2, 14.2, -22.0, 17.8)
  is_pan = (key == "prehistoric_ssa")

  main_feats = []
  cv_inset_feats = []
  for feat in gj.get("features", []):
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    g = shape(geom_raw).buffer(0)
    if g.is_empty:
      continue
    rid = str(feat.get("properties", {}).get("id") or "")
    if is_pan:
      g_m = g.intersection(box_main_af)
      if not g_m.is_empty and g_m.area > 1e-4:
        main_feats.append((rid, g_m))
      g_c = g.intersection(box_cv_in)
      if not g_c.is_empty and g_c.area > 1e-5:
        cv_inset_feats.append((rid, g_c))
    else:
      main_feats.append((rid, g))

  union_main = unary_union([g for _, g in main_feats])
  minx, miny, maxx, maxy = union_main.bounds
  lon0 = 0.5 * (minx + maxx)
  lat0 = 0.5 * (miny + maxy)
  proj_main = LambertAzimuthalEqualArea(lon0, lat0)

  clip_bb = (max(-30.0, minx - 14.0), max(-42.0, miny - 14.0), min(64.0, maxx + 14.0), min(38.0, maxy + 14.0))
  simp_deg = 0.025 if (maxx - minx) > 35.0 else 0.0
  land_p, riv_g = arg1_bm_src.load_for_extent(proj_main, clip_bb, arg2_show_modern_borders=is_adm1, arg3_simplify_deg=simp_deg)

  apply_viscount_style()
  fig, ax = plt.subplots(figsize=(9.8, 6.4), dpi=300)
  apply_viscount_style(ax, {"grid": False})
  draw_basemap(ax, land_p, riv_g)

  # Group colours by country for Admin-1 chapters; direct muted RGB for historical chapters
  uniq_isos = sorted(set(v for v in iso_map.values() if v))
  iso_color = {iso: COUNTRY_PALETTE[i % len(COUNTRY_PALETTE)] for i, iso in enumerate(uniq_isos)}
  iso_counter = {iso: 0 for iso in uniq_isos}
  iso_geoms = {iso: [] for iso in uniq_isos}

  proj_all_main = []
  legend_handles = []
  seen_leg = set()

  for idx_f, (rid, g) in enumerate(main_feats):
    pg = prepare_and_project(g, proj_main, 0.25)
    if pg.is_empty:
      continue
    proj_all_main.append(pg)
    ps = geom_to_patches(pg)
    if is_adm1:
      iso = iso_map.get(rid, rid.split("_")[0].upper())
      fc = tint_country_shade(iso_color.get(iso, (120, 150, 180)), iso_counter.get(iso, 0))
      iso_counter[iso] = iso_counter.get(iso, 0) + 1
      iso_geoms.setdefault(iso, []).append(pg.buffer(0))
      if ps:
        ax.add_collection(PatchCollection(ps, facecolor=fc, edgecolor="#475569", linewidths=0.32, alpha=0.88, zorder=2.5))
      if iso not in seen_leg:
        seen_leg.add(iso)
        leg_fc = mute_rgb_hex(iso_color.get(iso, (120, 150, 180)), 0, 0.36)
        legend_handles.append(Patch(facecolor=leg_fc, edgecolor="#1e293b", linewidth=0.65, label=ISO3_DISPLAY.get(iso, iso)))
    else:
      fc = mute_rgb_hex(rgb_map.get(rid), idx_f, 0.36)
      if ps:
        ax.add_collection(PatchCollection(ps, facecolor=fc, edgecolor="#334155", linewidths=0.55, alpha=0.88, zorder=2.5))
      if rid not in seen_leg:
        seen_leg.add(rid)
        legend_handles.append(Patch(facecolor=fc, edgecolor="#334155", linewidth=0.55, label=clean_subregion_label(name_map.get(rid, rid), 28)))

  # Bold country perimeters for Admin-1 chapters, or bold dissolved outer perimeter for historical chapters
  if is_adm1:
    for iso, glist in iso_geoms.items():
      if glist:
        c_u = unary_union(glist)
        c_ps = geom_to_patches(c_u)
        if c_ps:
          ax.add_collection(PatchCollection(c_ps, facecolor="none", edgecolor="#111827", linewidths=0.95, zorder=3.6))
  if proj_all_main:
    outer_pg = unary_union([pg.buffer(0) for pg in proj_all_main])
    outer_ps = geom_to_patches(outer_pg)
    if outer_ps:
      ax.add_collection(PatchCollection(outer_ps, facecolor="none", edgecolor="#111827", linewidths=1.15, zorder=3.8))
    xlim, ylim = pad_projected_bounds(outer_pg.bounds, arg1_target_aspect=1.50, arg2_pad_factor=1.18, arg3_min_span_km=420.0)
  else:
    xlim, ylim = (-1500.0, 1500.0), (-1000.0, 1000.0)

  ax.set_xlim(*xlim)
  ax.set_ylim(*ylim)
  ax.set_aspect("equal", adjustable="box")
  ax.set_xticks([])
  ax.set_yticks([])

  glats = [v for v in range(-35, 31, 5) if miny - 3 <= v <= maxy + 3]
  glons = [v for v in range(-20, 56, 5) if minx - 3 <= v <= maxx + 3]
  if len(glats) > 7:
    glats = glats[::2]
  if len(glons) > 8:
    glons = glons[::2]
  draw_graticule(ax, proj_main, xlim, ylim, glats, glons, (clip_bb[0], clip_bb[2]), (clip_bb[1], clip_bb[3]))

  # Cabo Verde inset on prehistoric_ssa so Atlantic islands are shown cleanly without shrinking mainland
  if is_pan and cv_inset_feats:
    ax_cv = ax.inset_axes([0.02, 0.04, 0.21, 0.24])
    apply_viscount_style(ax_cv, {"grid": False})
    cv_l, cv_r = arg1_bm_src.load_for_extent(PROJ_CABO_VERDE, (-26.2, 14.2, -22.0, 17.8), arg2_show_modern_borders=False)
    draw_basemap(ax_cv, cv_l, cv_r)
    cv_pgs = []
    for rid, g in cv_inset_feats:
      pg = prepare_and_project(g, PROJ_CABO_VERDE, 0.15)
      if not pg.is_empty:
        cv_pgs.append(pg)
        ps = geom_to_patches(pg)
        if ps:
          ax_cv.add_collection(PatchCollection(ps, facecolor=mute_rgb_hex(rgb_map.get(rid), 15, 0.36), edgecolor="#111827", linewidths=0.6, alpha=0.90, zorder=2.5))
    if cv_pgs:
      cx, cy = pad_projected_bounds(unary_union(cv_pgs).bounds, 1.30, 1.28, 350.0)
      ax_cv.set_xlim(*cx)
      ax_cv.set_ylim(*cy)
    ax_cv.set_aspect("equal", adjustable="box")
    ax_cv.set_xticks([])
    ax_cv.set_yticks([])
    ax_cv.set_title("Cabo Verde", fontsize=6.8, pad=2)

  # Settlement cloud (from raw gazetteer) + top-city proportional markers & callouts
  sett_path = os.path.join(ch_dir, f"{key}_settlements.json")
  raw_setts = json.load(open(sett_path, encoding="utf-8"))
  all_pts = [(float(s["coords"][1]), float(s["coords"][0])) for s in raw_setts.values() if s.get("coords") and len(s["coords"]) >= 2]
  plot_proportional_settlements(ax, arg0_ch["top_cities"][:18], proj_main, xlim, ylim, arg5_all_pts=all_pts)

  d0, d1 = arg0_ch["domain"]
  ax.set_title(f"{arg0_ch['title']} ({format_year_label(d0)}–{format_year_label(d1)})", fontsize=10.4, pad=7)

  n_leg = len(legend_handles)
  ncol = 4 if n_leg >= 11 else (3 if n_leg >= 4 else max(1, n_leg))
  nrows = math.ceil(n_leg / max(1, ncol))
  bot_margin = min(0.32, 0.065 + 0.044 * nrows)
  fig.subplots_adjust(left=0.03, right=0.97, top=0.92, bottom=bot_margin)

  if legend_handles:
    fig.legend(
      handles=legend_handles,
      loc="lower center",
      ncol=ncol,
      fontsize=6.8 if n_leg > 10 else 7.2,
      frameon=True,
      facecolor="white",
      edgecolor="#cbd5e1",
      bbox_to_anchor=(0.5, 0.012),
    )

  top_items = [{"label": clean_subregion_label(c["name"], 17), "lon": c["lon"], "lat": c["lat"]} for c in arg0_ch["top_cities"][:16]]
  place_inbounds_callouts(
    fig, ax, top_items, proj_main, xlim, ylim,
    {"max_labels": 7, "min_sep_px": 54.0, "fontsize": 6.6, "margin_px": 10.0, "dot_color": "#b91c1c"},
  )
  save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_trends_figure (arg0_ch):
  ch_dir = os.path.join(NIC_DIR, arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", "fig_02_trends.png")

  bench_yrs = arg0_ch["benchmark_years"]
  tot_vals = [float(arg0_ch["total_pop_by_year"].get(str(y), 0.0)) for y in bench_yrs]
  urb_ser = arg0_ch["urban_series"]
  urb_yrs = [int(p["year"]) for p in urb_ser]
  urb_pops = [float(p["urban_pop"]) for p in urb_ser]
  urb_cnts = [int(p["settlement_count"]) for p in urb_ser]

  apply_viscount_style()
  fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(13.6, 4.4), dpi=300, gridspec_kw={"wspace": 0.34})
  for ax in (ax1, ax2, ax3):
    apply_viscount_style(ax, {"grid": True})

  yr_fmt = mticker.FuncFormatter(lambda x, pos: f"{int(abs(x))}BC" if x < 0 else f"{int(x)}")

  # Panel A: Regional total vs attested urban population
  pos_vals = [v for v in tot_vals + urb_pops if v > 0.0]
  use_log_a = (len(pos_vals) >= 2 and (max(pos_vals) / max(1.0, min(pos_vals)) > 15.0))
  if use_log_a:
    tot_xy = [(y, v) for y, v in zip(bench_yrs, tot_vals) if v > 0.0]
    urb_xy = [(y, v) for y, v in zip(urb_yrs, urb_pops) if v > 0.0]
    if tot_xy:
      ax1.semilogy([p[0] for p in tot_xy], [p[1] for p in tot_xy], "-o", lw=1.9, ms=4.0, color="#1d4ed8", label="Regional total")
    if urb_xy:
      ax1.semilogy([p[0] for p in urb_xy], [p[1] for p in urb_xy], "--s", lw=1.6, ms=3.5, color="#b91c1c", label="Attested urban")
    lo_a = max(100.0, min(pos_vals) * 0.45)
    hi_a = max(pos_vals) * 3.8
    ax1.set_ylim(lo_a, hi_a)
    apply_human_log_ticks(ax1, "y", arg2_semantic=True)
    ax1.set_ylabel("Population (inhabitants, log)")
  else:
    ax1.plot(bench_yrs, tot_vals, "-o", lw=1.9, ms=4.0, color="#1d4ed8", label="Regional total")
    ax1.plot(urb_yrs, urb_pops, "--s", lw=1.6, ms=3.5, color="#b91c1c", label="Attested urban")
    hi_a = max(pos_vals) if pos_vals else 1.0
    ax1.set_ylim(0.0, hi_a * 1.25)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
    ax1.set_ylabel("Population (inhabitants)")

  ax1.xaxis.set_major_locator(mticker.MaxNLocator(nbins=4, integer=True))
  ax1.xaxis.set_major_formatter(yr_fmt)
  ax1.tick_params(axis="x", labelsize=7.8)
  ax1.set_xlabel("Calendar year")
  ax1.set_title("A. Regional & Urban Population", fontsize=9.4, pad=6)
  ax1.legend(loc="upper left", fontsize=7.0, frameon=True, facecolor="white", framealpha=0.92)

  # Panel B: Recorded settlement count over time
  ax2.fill_between(urb_yrs, 0, urb_cnts, color="#0f766e", alpha=0.18)
  ax2.plot(urb_yrs, urb_cnts, "-o", lw=1.9, ms=3.8, color="#0f766e", label="Active settlements")
  max_c = max(urb_cnts) if urb_cnts else 1
  ax2.set_ylim(0.0, max_c * 1.24)
  ax2.xaxis.set_major_locator(mticker.MaxNLocator(nbins=4, integer=True))
  ax2.xaxis.set_major_formatter(yr_fmt)
  ax2.yaxis.set_major_locator(mticker.MaxNLocator(nbins=5, integer=True))
  ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x >= 1000 else f"{int(round(x))}"))
  ax2.tick_params(axis="x", labelsize=7.8)
  ax2.set_xlabel("Calendar year")
  ax2.set_ylabel("Recorded settlements")
  ax2.set_title("B. Attested Settlement Count", fontsize=9.4, pad=6)
  ax2.legend(loc="upper left", fontsize=7.0, frameon=True, facecolor="white", framealpha=0.92)

  # Panel C: Top 5 named city trajectories
  palette_c = ["#1d4ed8", "#d97706", "#059669", "#7c3aed", "#dc2626"]
  multi_cities = [c for c in arg0_ch["top_cities"] if len(c["series"]) >= 2][:5]
  if len(multi_cities) < 3:
    multi_cities = arg0_ch["top_cities"][:5]

  all_cy = []
  for idx_c, c in enumerate(multi_cities):
    pts = c["series"]
    xs_c = [p[0] for p in pts]
    ys_c = [p[1] for p in pts]
    all_cy.extend(ys_c)
    lbl = clean_subregion_label(c["name"], 18)
    if len(xs_c) >= 2:
      ax3.plot(xs_c, ys_c, "-o", lw=1.55, ms=3.2, color=palette_c[idx_c % len(palette_c)], label=lbl)
    else:
      ax3.plot(xs_c, ys_c, "o", ms=5.2, color=palette_c[idx_c % len(palette_c)], label=lbl)

  max_cy = max(all_cy) if all_cy else 1.0
  ax3.set_ylim(0.0, max_cy * 1.32)
  ax3.xaxis.set_major_locator(mticker.MaxNLocator(nbins=4, integer=True))
  ax3.xaxis.set_major_formatter(yr_fmt)
  ax3.yaxis.set_major_locator(mticker.MaxNLocator(nbins=5))
  ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  ax3.tick_params(axis="x", labelsize=7.8)
  ax3.set_xlabel("Calendar year")
  ax3.set_ylabel("City population")
  ax3.set_title("C. Leading Urban Centres", fontsize=9.4, pad=6)
  ax3.legend(loc="upper left", fontsize=6.6, frameon=True, facecolor="white", framealpha=0.92)

  fig.subplots_adjust(left=0.065, right=0.985, top=0.88, bottom=0.14, wspace=0.34)
  save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_rank_size_figure (arg0_ch):
  ch_dir = os.path.join(NIC_DIR, arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", "fig_03_rank_size.png")
  peaks = [float(v) for v in arg0_ch["zipf_peaks"] if float(v) > 0.0]
  subregs = arg0_ch["subregions"]
  last_yr = arg0_ch["benchmark_years"][-1]

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.8, 4.7), dpi=300, gridspec_kw={"width_ratios": [1.05, 1.12], "wspace": 0.46})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Empirical Zipf rank-size distribution (n >= 25 strictly enforced)
  n_all = len(peaks)
  if n_all >= 25:
    ranks = np.arange(1, n_all + 1, dtype=np.float64)
    pops = np.asarray(peaks, dtype=np.float64)
    ax1.loglog(ranks, pops, "o", markersize=2.8, alpha=0.55, color="#2563eb", label=f"Observed ($n = {n_all:,}$)".replace(",", "."))

    n_fit = min(max(25, n_all // 2), 180)
    lx = np.log10(ranks[:n_fit])
    ly = np.log10(pops[:n_fit])
    slope, intercept = np.polyfit(lx, ly, 1)
    y_hat = slope * lx + intercept
    ss_res = float(np.sum((ly - y_hat) ** 2))
    ss_tot = float(np.sum((ly - np.mean(ly)) ** 2))
    r2 = max(0.0, 1.0 - ss_res / max(1e-12, ss_tot))
    q_val = -slope

    ax1.loglog(
      ranks[:n_fit],
      10.0 ** y_hat,
      "-",
      linewidth=1.7,
      color="#dc2626",
      label=rf"OLS fit ($q = {format_mathtext_euro(q_val, 2)}$, $R^2 = {format_mathtext_euro(r2, 2)}$)",
    )
    # Zipf q = 1 reference anchored at fitted rank-1 intercept
    zipf_ref = (10.0 ** intercept) / ranks[:n_fit]
    ax1.loglog(ranks[:n_fit], zipf_ref, ":", linewidth=1.2, color="#475569", label=r"Zipf reference ($q = 1$)")

    ax1.set_xlim(0.75, n_all * 1.45)
    ax1.set_ylim(max(20.0, float(pops.min()) * 0.55), float(pops.max()) * 2.4)
    apply_human_log_ticks(ax1, "both", arg2_semantic=True)
    ax1.set_xlabel("Settlement rank")
    ax1.set_ylabel("Peak population (inhabitants)")
    ax1.set_title("A. Settlement Rank-Size Distribution", fontsize=9.6, pad=6)
    ax1.legend(loc="lower left", fontsize=7.2, frameon=True, facecolor="white", framealpha=0.92)
  else:
    ax1.text(0.5, 0.5, "Insufficient sample for rank-size regression", ha="center", va="center", transform=ax1.transAxes)

  # Panel B: Top 10 sub-regions (or sovereign countries if Admin-1 has >16 units) by end-epoch density
  dens_items = []
  if arg0_ch["is_admin1"] and len(subregs) > 16:
    # Show top 10 highest-density Admin-1 units with clean names
    for idx_s, sr in enumerate(subregs):
      dval = float(sr.get("end_density", 0.0))
      iso = sr.get("iso3", "")
      nm_clean = clean_subregion_label(sr["name"], 24)
      dens_items.append((nm_clean, dval, mute_rgb_hex(sr["rgb"], idx_s, 0.25)))
  else:
    for idx_s, sr in enumerate(subregs):
      dval = float(sr.get("end_density", 0.0))
      nm_clean = clean_subregion_label(sr["name"], 24)
      dens_items.append((nm_clean, dval, mute_rgb_hex(sr["rgb"], idx_s, 0.25)))

  dens_items.sort(key=lambda x: x[1])
  show_d = dens_items[-10:]
  y_pos = np.arange(len(show_d))
  vals_d = [x[1] for x in show_d]
  ax2.barh(y_pos, vals_d, color=[x[2] for x in show_d], edgecolor="#334155", linewidth=0.55)
  ax2.set_yticks(y_pos)
  ax2.set_yticklabels([x[0] for x in show_d], fontsize=7.4)
  max_d = max(vals_d) if vals_d else 1.0
  ax2.set_xlim(0.0, max_d * 1.28)
  ax2.xaxis.set_major_locator(mticker.MaxNLocator(nbins=5))
  ax2.xaxis.set_major_formatter(euro_tick_formatter(1 if max_d < 20 else 0))
  for yp, vd in zip(y_pos, vals_d):
    lbl_d = format_euro_number(vd, 2 if vd < 5 else (1 if vd < 50 else 0))
    ax2.text(vd + max_d * 0.025, yp, lbl_d, va="center", ha="left", fontsize=7.1, color="#0f172a")
  ax2.set_xlabel("Density (inhabitants / km²)")
  ax2.set_title(f"B. Sub-Regional Density in {format_year_label(last_yr)}", fontsize=9.6, pad=6)

  fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.14, wspace=0.48)
  save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def main ():
  cache = json.load(open(CACHE_PATH, encoding="utf-8"))
  print("[1] Loading Natural Earth 10m coastlines & rivers once into memory...", flush=True)
  bm_src = BasemapSource10m()

  chapters = cache["chapters"]
  print(f"[2] Rendering 3 POLARIS-grade figures across all {len(chapters)} NICETHI chapters...", flush=True)
  for ch in chapters:
    render_chapter_map(ch, bm_src)
    render_trends_figure(ch)
    render_rank_size_figure(ch)
    print(f"  [CH {ch['index']:02d}] {ch['key']}: 3 figures verified & saved", flush=True)

  print(f"[DONE] Generated {len(chapters) * 3} NICETHI chapter figures cleanly.", flush=True)


if __name__ == "__main__":
  main()
