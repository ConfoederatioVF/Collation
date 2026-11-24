"""Generates POLARIS-grade vector cartography and demographic diagnostic figures for all 17 Project QUIPU chapters.

Produces three publication figures per chapter inside `<chapter_dir>/figures/`:
  1. `<stem>_regional_map.png` — Upright Lambert Azimuthal Equal-Area vector PatchCollection sub-regions,
     Natural Earth basemap & rivers, curved graticule, dedicated Galápagos (Ecuador) and Juan Fernández (Chile)
     insets, split 3-panel layout for Falklands & South Atlantic Islands, in-bounds top-settlement callouts
     and compact bottom region legend. Modern national borders are suppressed on Chapters 1-8 (Pre-Columbian &
     Colonial) and drawn only on Post-Independence Chapters 9-17.
  2. `<stem>_population_trajectory.png` — Two-panel sub-regional population trajectory & end-epoch population
     density (inhabitants / km²) bar chart with European decimals.
  3. `<stem>_urban_hierarchy.png` — Two-panel top named settlements horizontal bar chart & empirical log-log
     rank-size distribution formatted with human European log ticks.
"""

import json
import math
import os
import re
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
QUIPU_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "QUIPU")
SHARED = os.path.join(QUIPU_DIR, "_shared")
SCRIPTS_DIR = os.path.join(SHARED, "scripts")
SUBREG_DIR = os.path.join(SHARED, "_gis_cache", "chapter_subregions")
ITIN_PATH = os.path.join(QUIPU_DIR, "quipu_itinerary.json5")

if SCRIPTS_DIR not in sys.path:
  sys.path.insert(0, SCRIPTS_DIR)

from quipu_map_helper import (
  LambertAzimuthalEqualArea,
  PROJ_FALKLANDS,
  PROJ_GALAPAGOS,
  PROJ_JUAN_FERNANDEZ,
  PROJ_SOUTH_GEORGIA,
  PROJ_SOUTH_SANDWICH,
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
  mute_rgb_hex,
  pad_projected_bounds,
  place_inbounds_callouts,
  prepare_and_project,
  save_viscount_figure,
)


def load_json5_simple (arg0_path):
  raw = open(arg0_path, encoding="utf-8").read()
  raw = re.sub(r"//.*", "", raw)
  raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
  raw = re.sub(r",(\s*[}\]])", r"\1", raw)
  raw = re.sub(r"(\{|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
  return json.loads(raw)


def format_year_label (arg0_yr):
  y = int(arg0_yr)
  if y < 0:
    return f"{abs(y)}BC"
  return f"{y}AD" if y <= 1500 else str(y)


def truncate_label (arg0_text, arg1_max=28):
  s = str(arg0_text or "").strip()
  if len(s) <= arg1_max:
    return s
  return s[: arg1_max - 1].rstrip(" ,;-") + "…"


def render_falklands_split_map (arg0_ch, arg1_summary, arg2_basemaps):
  """Renders the 3-panel split equal-area map for Falkland Islands, South Georgia & South Sandwich Islands."""
  key = arg0_ch["key"]
  ch_dir = os.path.join(QUIPU_DIR, arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", f"{key}_regional_map.png")
  vec_path = os.path.join(SUBREG_DIR, f"{key}_subregions.geojson")
  gj = json.load(open(vec_path, encoding="utf-8"))

  rgb_map = {r["id"]: r["rgb"] for r in arg1_summary["subregions"]}
  name_map = {r["id"]: r["name"] for r in arg1_summary["subregions"]}

  feats_by_id = {}
  for feat in gj.get("features", []):
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    g = shape(geom_raw).buffer(0)
    if g.is_empty:
      continue
    rid = str(feat.get("properties", {}).get("id") or "")
    feats_by_id[rid] = g

  sett_path = os.path.join(ch_dir, f"{key}_settlements.json")
  setts = json.load(open(sett_path, encoding="utf-8"))
  sett_vals = list(setts.values()) if isinstance(setts, dict) else list(setts)

  panel_specs = [
    (
      "A. Falkland Islands",
      ["flk_east_falkland", "flk_west_falkland"],
      PROJ_FALKLANDS,
      arg2_basemaps["flk_land"],
      arg2_basemaps["flk_riv"],
      [-52.0, -51.5],
      [-61.0, -60.0, -59.0, -58.0],
      (-62.5, -56.5),
      (-53.2, -50.5),
      180.0,
      5,
    ),
    (
      "B. South Georgia",
      ["sgs_south_georgia"],
      PROJ_SOUTH_GEORGIA,
      arg2_basemaps["sg_land"],
      arg2_basemaps["sg_riv"],
      [-54.5, -54.0],
      [-38.0, -37.0, -36.0],
      (-39.5, -34.5),
      (-55.6, -53.2),
      150.0,
      4,
    ),
    (
      "C. South Sandwich Islands",
      ["sgs_south_sandwich"],
      PROJ_SOUTH_SANDWICH,
      arg2_basemaps["ss_land"],
      arg2_basemaps["ss_riv"],
      [-59.0, -58.0, -57.0, -56.0],
      [-28.0, -27.0, -26.0],
      (-29.5, -24.5),
      (-60.5, -55.5),
      260.0,
      3,
    ),
  ]

  apply_viscount_style()
  fig, axes = plt.subplots(1, 3, figsize=(12.0, 5.2), dpi=300)
  legend_handles = []
  seen_leg = set()
  callout_jobs = []

  for idx_p, (ax, spec) in enumerate(zip(axes, panel_specs)):
    ptitle, rids, proj, land_p, riv_g, glats, glons, lon_sp, lat_sp, min_km, max_lbl = spec
    apply_viscount_style(ax, {"grid": False})
    draw_basemap(ax, land_p, riv_g)

    proj_all = []
    for idx_r, rid in enumerate(rids):
      g = feats_by_id.get(rid)
      if g is None or g.is_empty:
        continue
      pg = prepare_and_project(g, proj, 0.05, None, 1e-6, 0.0)
      if pg.is_empty:
        continue
      proj_all.append(pg)
      hex_c = mute_rgb_hex(rgb_map.get(rid), idx_p * 2 + idx_r, 0.34)
      ps = geom_to_patches(pg)
      if ps:
        ax.add_collection(PatchCollection(ps, facecolor=hex_c, edgecolor="#1e293b", linewidths=0.75, alpha=0.88, zorder=2.5))
      if rid not in seen_leg:
        seen_leg.add(rid)
        legend_handles.append(Patch(facecolor=hex_c, edgecolor="#334155", linewidth=0.55, label=truncate_label(name_map.get(rid, rid), 28)))

    if proj_all:
      outer_pg = unary_union([pg.buffer(0) for pg in proj_all])
      xlim, ylim = pad_projected_bounds(outer_pg.bounds, arg1_target_aspect=0.92, arg2_pad_factor=1.32, arg3_min_span_km=min_km)
    else:
      xlim, ylim = (-150.0, 150.0), (-150.0, 150.0)

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    draw_graticule(ax, proj, xlim, ylim, glats, glons, lon_sp, lat_sp)
    ax.set_title(ptitle, fontsize=9.2, pad=5)

    xs_s, ys_s = [], []
    for s in sett_vals:
      lat, lon = float(s["coords"][0]), float(s["coords"][1])
      if lon_sp[0] <= lon <= lon_sp[1] and lat_sp[0] <= lat <= lat_sp[1]:
        px, py = proj.fwd_pt(lon, lat)
        if xlim[0] <= px <= xlim[1] and ylim[0] <= py <= ylim[1]:
          xs_s.append(px)
          ys_s.append(py)
    if xs_s:
      ax.scatter(xs_s, ys_s, s=12.0, c="#1e293b", alpha=0.55, linewidths=0.0, zorder=4.8)

    top_items = [
      {"label": truncate_label(s["name"], 18), "lon": s["lon"], "lat": s["lat"]}
      for s in arg1_summary["top_settlements"]
      if lon_sp[0] <= s["lon"] <= lon_sp[1] and lat_sp[0] <= s["lat"] <= lat_sp[1]
    ]
    callout_jobs.append((ax, top_items, proj, xlim, ylim, max_lbl))

  fig.subplots_adjust(left=0.02, right=0.98, top=0.90, bottom=0.14, wspace=0.07)
  if legend_handles:
    fig.legend(
      handles=legend_handles,
      loc="lower center",
      ncol=4,
      fontsize=7.4,
      frameon=True,
      facecolor="white",
      edgecolor="#cbd5e1",
      bbox_to_anchor=(0.5, 0.02),
    )

  for ax, top_items, proj, xlim, ylim, max_lbl in callout_jobs:
    if top_items:
      place_inbounds_callouts(
        fig, ax, top_items, proj, xlim, ylim,
        {"max_labels": max_lbl, "min_sep_px": 44.0, "fontsize": 6.4, "margin_px": 8.0, "dot_color": "#b91c1c"},
      )

  save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_regional_map (arg0_ch, arg1_summary, arg2_basemaps):
  key = arg0_ch["key"]
  if key == "falklands_south_atlantic":
    render_falklands_split_map(arg0_ch, arg1_summary, arg2_basemaps)
    return

  ch_dir = os.path.join(QUIPU_DIR, arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", f"{key}_regional_map.png")
  vec_path = os.path.join(SUBREG_DIR, f"{key}_subregions.geojson")
  gj = json.load(open(vec_path, encoding="utf-8"))

  rgb_map = {r["id"]: r["rgb"] for r in arg1_summary["subregions"]}
  name_map = {r["id"]: r["name"] for r in arg1_summary["subregions"]}
  last_yr = str(arg1_summary["benchmark_years"][-1]) if arg1_summary["benchmark_years"] else ""
  pop_end_map = {r["id"]: r["population"].get(last_yr, 0) for r in arg1_summary["subregions"]}

  # Partition distant oceanic archipelagos into dedicated insets (Galápagos for Ecuador; Juan Fernández for Chile)
  main_feats = []
  gal_feats = []
  jf_feats = []
  box_gal = box(-93.0, -2.5, -88.0, 2.5)
  box_jf = box(-81.5, -34.5, -77.5, -25.5)

  for feat in gj.get("features", []):
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    g = shape(geom_raw).buffer(0)
    if g.is_empty:
      continue
    rid = str(feat.get("properties", {}).get("id") or "")
    if key == "ecuador_after_independence":
      g_gal = g.intersection(box_gal)
      if not g_gal.is_empty and g_gal.area > 1e-5:
        gal_feats.append((rid, g_gal))
      g_rem = g.difference(box_gal)
      if not g_rem.is_empty and g_rem.area > 1e-4:
        main_feats.append((rid, g_rem))
    elif key == "chile_after_independence":
      g_jf = g.intersection(box_jf)
      if not g_jf.is_empty and g_jf.area > 1e-5:
        jf_feats.append((rid, g_jf))
      g_rem = g.difference(box_jf)
      if not g_rem.is_empty and g_rem.area > 1e-4:
        main_feats.append((rid, g_rem))
    else:
      main_feats.append((rid, g))

  if not main_feats:
    main_feats = gal_feats + jf_feats
    gal_feats, jf_feats = [], []

  # Fit chapter-specific upright Lambert Azimuthal Equal-Area projection centred on mainland extent
  union_main = unary_union([g for _, g in main_feats])
  minx, miny, maxx, maxy = union_main.bounds
  lon0 = 0.5 * (minx + maxx)
  lat0 = 0.5 * (miny + maxy)
  proj_main = LambertAzimuthalEqualArea(lon0, lat0)

  # Estimate mainland projected aspect to frame tall Andean corridors generously
  raw_proj_bounds = prepare_and_project(box(minx, miny, maxx, maxy), proj_main, 0.5).bounds
  proj_w = max(100.0, raw_proj_bounds[2] - raw_proj_bounds[0])
  proj_h = max(100.0, raw_proj_bounds[3] - raw_proj_bounds[1])
  is_tall = (proj_w / proj_h) < 0.72

  # Pre-project basemap: ZERO modern borders on Chapters 1-8 (Pre-Columbian & Colonial); modern borders ONLY on Chapters 9-17
  pad_lon = max(20.0, 0.85 * (maxx - minx))
  pad_lat = max(10.0, 0.45 * (maxy - miny))
  clip_bb = (
    max(-95.0, minx - pad_lon),
    max(-60.0, miny - pad_lat),
    min(-28.0, maxx + pad_lon),
    min(16.0, maxy + pad_lat),
  )
  is_modern_ch = (int(arg0_ch.get("index", 1)) >= 9)
  land_p, riv_g = load_basemap_cache(proj_main, clip_bb, arg2_show_modern_borders=is_modern_ch)

  apply_viscount_style()
  fig_size = (8.8, 7.2) if is_tall else (9.6, 6.2)
  target_aspect = 1.15 if is_tall else 1.52
  fig, ax = plt.subplots(figsize=fig_size, dpi=300)
  apply_viscount_style(ax, {"grid": False})
  draw_basemap(ax, land_p, riv_g)

  # Project and plot sub-region vector polygons (simplify dense Chilean fjord micro-slivers cleanly)
  is_fjord_ch = key in ("chile_after_independence", "chile_rio_plata_banda_oriental", "pre_columbian_southern_cone", "spanish_conquest_andes_collapse")
  min_area_filt = 2.5e-3 if is_fjord_ch else 2.0e-5
  simp_deg = 0.015 if is_fjord_ch else 0.003
  edge_lw = 0.35 if is_fjord_ch else 0.52
  outer_lw = 0.80 if is_fjord_ch else 1.10
  proj_all_main = []
  color_by_rid = {}
  for idx_f, (rid, g) in enumerate(main_feats):
    pg = prepare_and_project(g, proj_main, 0.25, None, min_area_filt, simp_deg)
    if pg.is_empty:
      continue
    proj_all_main.append(pg)
    patches = geom_to_patches(pg)
    hex_c = mute_rgb_hex(rgb_map.get(rid), idx_f, 0.38)
    color_by_rid[rid] = hex_c
    if patches:
      ax.add_collection(PatchCollection(patches, facecolor=hex_c, edgecolor="#334155", linewidths=edge_lw, alpha=0.88, zorder=2.5))

  if proj_all_main:
    outer_pg = unary_union([pg.buffer(0) for pg in proj_all_main])
    outer_patches = geom_to_patches(outer_pg)
    if outer_patches:
      ax.add_collection(PatchCollection(outer_patches, facecolor="none", edgecolor="#111827", linewidths=outer_lw, zorder=3.6))
    xlim, ylim = pad_projected_bounds(outer_pg.bounds, arg1_target_aspect=target_aspect, arg2_pad_factor=1.18, arg3_min_span_km=340.0)
  else:
    xlim, ylim = (-1200.0, 1200.0), (-1200.0, 1200.0)

  ax.set_xlim(*xlim)
  ax.set_ylim(*ylim)
  ax.set_aspect("equal", adjustable="box")
  ax.set_xticks([])
  ax.set_yticks([])

  lat_step = 5 if (maxy - miny) < 18 else 10
  lon_step = 5 if (maxx - minx) < 18 else 10
  glats = list(range(-60, 20, lat_step))
  glons = list(range(-90, -30, lon_step))
  glats = [v for v in glats if miny - pad_lat <= v <= maxy + pad_lat]
  glons = [v for v in glons if minx - pad_lon <= v <= maxx + pad_lon]
  draw_graticule(ax, proj_main, xlim, ylim, glats, glons, (clip_bb[0], clip_bb[2]), (clip_bb[1], clip_bb[3]))

  # Dedicated Galápagos Islands inset for Ecuador
  if gal_feats:
    ax_gal = ax.inset_axes([0.02, 0.56, 0.27, 0.38])
    apply_viscount_style(ax_gal, {"grid": False})
    draw_basemap(ax_gal, arg2_basemaps["gal_land"], arg2_basemaps["gal_riv"])
    gal_pgs = []
    for idx_g, (rid, g) in enumerate(gal_feats):
      pg = prepare_and_project(g, PROJ_GALAPAGOS, 0.05, None, 1e-6, 0.0)
      if pg.is_empty:
        continue
      gal_pgs.append(pg)
      hex_c = mute_rgb_hex(rgb_map.get(rid), idx_g + 5, 0.36)
      color_by_rid[rid] = hex_c
      ps = geom_to_patches(pg)
      if ps:
        ax_gal.add_collection(PatchCollection(ps, facecolor=hex_c, edgecolor="#111827", linewidths=0.65, alpha=0.88, zorder=2.5))
    if gal_pgs:
      gx, gy = pad_projected_bounds(unary_union(gal_pgs).bounds, arg1_target_aspect=1.05, arg2_pad_factor=1.22, arg3_min_span_km=260.0)
      ax_gal.set_xlim(*gx)
      ax_gal.set_ylim(*gy)
    ax_gal.set_aspect("equal", adjustable="box")
    ax_gal.set_xticks([])
    ax_gal.set_yticks([])
    ax_gal.set_title("Galápagos Islands", fontsize=7.0, pad=2)

  # Dedicated Juan Fernández inset for Chile (Robinsón Crusoe & Alejandro Selkirk at 33,6°S)
  if jf_feats:
    ax_jf = ax.inset_axes([0.03, 0.44, 0.27, 0.26])
    apply_viscount_style(ax_jf, {"grid": False})
    draw_basemap(ax_jf, arg2_basemaps["jf_land"], arg2_basemaps["jf_riv"])
    jf_box_33 = box(-81.2, -34.2, -78.4, -33.2)
    jf_pgs = []
    for idx_j, (rid, g) in enumerate(jf_feats):
      g_sub = g.intersection(jf_box_33)
      if g_sub.is_empty:
        continue
      pg = prepare_and_project(g_sub, PROJ_JUAN_FERNANDEZ, 0.03, None, 1e-6, 0.0)
      if pg.is_empty:
        continue
      jf_pgs.append(pg)
      hex_c = color_by_rid.get(rid, mute_rgb_hex(rgb_map.get(rid), idx_j + 3, 0.36))
      ps = geom_to_patches(pg)
      if ps:
        ax_jf.add_collection(PatchCollection(ps, facecolor=hex_c, edgecolor="#111827", linewidths=0.70, alpha=0.90, zorder=2.5))
    if jf_pgs:
      jx, jy = pad_projected_bounds(unary_union(jf_pgs).bounds, arg1_target_aspect=1.45, arg2_pad_factor=1.45, arg3_min_span_km=210.0)
      ax_jf.set_xlim(*jx)
      ax_jf.set_ylim(*jy)
    ax_jf.set_aspect("equal", adjustable="box")
    ax_jf.set_xticks([])
    ax_jf.set_yticks([])
    ax_jf.set_title("Juan Fernández", fontsize=7.0, pad=2)

  # Plot settlement cloud + top 7 in-bounds callouts
  sett_path = os.path.join(ch_dir, f"{key}_settlements.json")
  setts = json.load(open(sett_path, encoding="utf-8"))
  sett_vals = list(setts.values()) if isinstance(setts, dict) else list(setts)
  xs_s, ys_s = [], []
  for s in sett_vals:
    lat, lon = float(s["coords"][0]), float(s["coords"][1])
    if key == "ecuador_after_independence" and lon < -85.0:
      continue
    if key == "chile_after_independence" and lon < -77.5:
      continue
    px, py = proj_main.fwd_pt(lon, lat)
    if xlim[0] <= px <= xlim[1] and ylim[0] <= py <= ylim[1]:
      xs_s.append(px)
      ys_s.append(py)
  if xs_s:
    n_pts = len(xs_s)
    pt_s = 1.4 if n_pts > 1500 else (2.4 if n_pts > 400 else 5.0)
    pt_a = 0.28 if n_pts > 1500 else (0.34 if n_pts > 400 else 0.42)
    ax.scatter(xs_s, ys_s, s=pt_s, c="#1e293b", alpha=pt_a, linewidths=0.0, zorder=4.8)

  top_items = [
    {"label": truncate_label(s["name"], 18), "lon": s["lon"], "lat": s["lat"]}
    for s in arg1_summary["top_settlements"][:18]
    if not (key == "ecuador_after_independence" and s["lon"] < -85.0)
    and not (key == "chile_after_independence" and s["lon"] < -77.5)
  ]

  d0, d1 = arg0_ch["domain"]
  title_str = f"{arg0_ch['itinerary_title']} ({format_year_label(d0)}–{format_year_label(d1)})"
  ax.set_title(title_str, fontsize=10.4, pad=8)

  # Build compact legend: all subregions when <= 12, or top 11 by population + summary entry when > 12
  all_rids = [r["id"] for r in arg1_summary["subregions"] if r["id"] in color_by_rid]
  legend_handles = []
  if len(all_rids) <= 12:
    for rid in all_rids:
      legend_handles.append(Patch(facecolor=color_by_rid[rid], edgecolor="#334155", linewidth=0.55, label=truncate_label(name_map.get(rid, rid), 28)))
  else:
    ranked_rids = sorted(all_rids, key=lambda r: -pop_end_map.get(r, 0))
    for rid in ranked_rids[:11]:
      legend_handles.append(Patch(facecolor=color_by_rid[rid], edgecolor="#334155", linewidth=0.55, label=truncate_label(name_map.get(rid, rid), 26)))
    n_rem = len(ranked_rids) - 11
    legend_handles.append(Patch(facecolor="#cbd5e1", edgecolor="#334155", linewidth=0.55, label=f"Other {n_rem} units"))

  n_leg = len(legend_handles)
  ncol = 3 if n_leg >= 4 else max(1, n_leg)
  nrows = math.ceil(n_leg / max(1, ncol))
  bot_margin = min(0.28, 0.075 + 0.044 * nrows)
  fig.subplots_adjust(left=0.03, right=0.97, top=0.92, bottom=bot_margin)

  if legend_handles:
    fig.legend(
      handles=legend_handles,
      loc="lower center",
      ncol=ncol,
      fontsize=7.0,
      frameon=True,
      facecolor="white",
      edgecolor="#cbd5e1",
      bbox_to_anchor=(0.5, 0.015),
    )

  place_inbounds_callouts(
    fig, ax, top_items, proj_main, xlim, ylim,
    {"max_labels": 7, "min_sep_px": 50.0, "fontsize": 6.6, "margin_px": 10.0, "dot_color": "#b91c1c"},
  )
  save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_trajectory_figure (arg0_ch, arg1_summary):
  key = arg0_ch["key"]
  ch_dir = os.path.join(QUIPU_DIR, arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", f"{key}_population_trajectory.png")

  yrs = arg1_summary["benchmark_years"]
  tot_vals = [arg1_summary["domain_totals"].get(str(y), 0) for y in yrs]
  subregs = arg1_summary["subregions"]
  last_yr = str(yrs[-1])

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.4), dpi=300, gridspec_kw={"width_ratios": [1.18, 1.0], "wspace": 0.44})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Domain total + top 4 sub-region trajectories
  ax1.plot(yrs, tot_vals, marker="o", linewidth=2.0, markersize=4.5, color="#1f77b4", label="Chapter total")
  ranked_sr = sorted(subregs, key=lambda r: -r["population"].get(last_yr, 0))
  line_cols = ["#d97706", "#2a9d8f", "#9333ea", "#dc2626"]
  for idx_r, sr in enumerate(ranked_sr[:4]):
    sv = [sr["population"].get(str(y), 0) for y in yrs]
    ax1.plot(yrs, sv, marker="s", linewidth=1.2, markersize=3.0, linestyle="--", color=line_cols[idx_r], label=truncate_label(sr["name"], 24))

  max_v = max(tot_vals) if tot_vals else 1.0
  is_u_shaped = (
    len(tot_vals) >= 3
    and tot_vals[0] >= 0.70 * max_v
    and tot_vals[-1] >= 0.70 * max_v
    and min(tot_vals[1:-1]) <= 0.70 * max_v
  )
  ax1.set_ylim(0.0, max_v * (1.32 if is_u_shaped else 1.24))
  ax1.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, integer=True))
  ax1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: f"{int(abs(x))}BC" if x < 0 else f"{int(x)}"))
  ax1.tick_params(axis="x", labelsize=8.0)
  ax1.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  ax1.set_xlabel("Calendar year")
  ax1.set_ylabel("Population (inhabitants)")
  ax1.set_title("A. Demographic Trajectory by Sub-Region", fontsize=9.8, pad=6)
  if is_u_shaped:
    leg_loc = "upper center"
  elif tot_vals and tot_vals[0] > tot_vals[-1] * 1.15:
    leg_loc = "upper right"
  else:
    leg_loc = "upper left"
  ax1.legend(loc=leg_loc, fontsize=7.0, frameon=True, facecolor="white", framealpha=0.92)

  # Panel B: End-epoch population density (inhabitants / km²) by sub-region
  dens_items = []
  for idx_s, sr in enumerate(subregs):
    p_end = sr["population"].get(last_yr, 0)
    a_km2 = max(1.0, float(sr["area_km2"]))
    dens_items.append((truncate_label(sr["name"], 24), p_end / a_km2, mute_rgb_hex(sr["rgb"], idx_s, 0.25)))
  dens_items.sort(key=lambda x: x[1])
  show_d = dens_items[-10:]
  y_pos = np.arange(len(show_d))
  vals_d = [x[1] for x in show_d]
  ax2.barh(y_pos, vals_d, color=[x[2] for x in show_d], edgecolor="#334155", linewidth=0.55)
  ax2.set_yticks(y_pos)
  ax2.set_yticklabels([x[0] for x in show_d], fontsize=7.6)
  max_d = max(vals_d) if vals_d else 1.0
  ax2.set_xlim(0.0, max_d * 1.30)
  ax2.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5))
  tick_dig = 2 if max_d < 2.0 else (1 if max_d < 20.0 else 0)
  ax2.xaxis.set_major_formatter(euro_tick_formatter(tick_dig))
  for yp, vd in zip(y_pos, vals_d):
    lbl_d = format_euro_number(vd, 2 if vd < 5.0 else (1 if vd < 50.0 else 0))
    ax2.text(vd + max_d * 0.025, yp, lbl_d, va="center", ha="left", fontsize=7.2, color="#1e293b")
  ax2.set_xlabel("Density (inhabitants / km²)")
  ax2.set_title(f"B. Sub-Regional Density in {format_year_label(yrs[-1])}", fontsize=9.8, pad=6)

  fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.14, wspace=0.48)
  save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_urban_hierarchy_figure (arg0_ch, arg1_summary):
  key = arg0_ch["key"]
  ch_dir = os.path.join(QUIPU_DIR, arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", f"{key}_urban_hierarchy.png")
  sett_path = os.path.join(ch_dir, f"{key}_settlements.json")
  setts = json.load(open(sett_path, encoding="utf-8"))
  sett_vals = list(setts.values()) if isinstance(setts, dict) else list(setts)

  peaks = []
  for s in sett_vals:
    pdict = s.get("population") or {}
    pos_vals = [int(round(float(v))) for v in pdict.values() if float(v) > 0]
    if pos_vals:
      peaks.append((s["name"], s.get("country", ""), max(pos_vals)))
  peaks.sort(key=lambda x: -x[2])

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.6), dpi=300, gridspec_kw={"width_ratios": [1.15, 1.0], "wspace": 0.42})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Top 12 settlements bar chart
  top12 = list(reversed(peaks[:12]))
  y_pos = np.arange(len(top12))
  vals_p = [x[2] for x in top12]
  ax1.barh(y_pos, vals_p, color="#3b7ea1", edgecolor="#1e293b", linewidth=0.5)
  ax1.set_yticks(y_pos)
  ax1.set_yticklabels([truncate_label(x[0], 22) for x in top12], fontsize=7.6)
  max_p = max(vals_p) if vals_p else 1.0
  ax1.set_xlim(0.0, max_p * 1.28)
  ax1.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=4))
  ax1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  for yp, vp in zip(y_pos, vals_p):
    ax1.text(vp + max_p * 0.02, yp, format_semantic_population(vp), va="center", ha="left", fontsize=7.0, color="#0f172a")
  ax1.set_xlabel("Peak settlement population")
  ax1.set_title("A. Largest Recorded Settlements", fontsize=9.8, pad=6)

  # Panel B: Rank-size distribution (strictly for n >= 25 settlements)
  n_all = len(peaks)
  if n_all >= 25:
    ranks = np.arange(1, n_all + 1, dtype=np.float64)
    pops = np.array([x[2] for x in peaks], dtype=np.float64)
    ax2.loglog(ranks, pops, "o", markersize=2.8, alpha=0.55, color="#2563eb", label=f"Observed (n={n_all:,})".replace(",", "."))
    n_fit = min(max(25, n_all // 2), 180)
    lx = np.log10(ranks[:n_fit])
    ly = np.log10(pops[:n_fit])
    slope, intercept = np.polyfit(lx, ly, 1)
    y_hat = slope * lx + intercept
    ss_res = float(np.sum((ly - y_hat) ** 2))
    ss_tot = float(np.sum((ly - np.mean(ly)) ** 2))
    r2 = max(0.0, 1.0 - ss_res / max(1e-12, ss_tot))
    ax2.loglog(ranks[:n_fit], 10.0 ** y_hat, "-", linewidth=1.6, color="#dc2626", label=rf"Power fit ($\alpha = {format_mathtext_euro(-slope, 2)}$, $R^2 = {format_mathtext_euro(r2, 2)}$)")
    ax2.set_xlim(0.8, n_all * 1.45)
    ax2.set_ylim(max(1.0, float(pops.min()) * 0.60), float(pops.max()) * 2.4)
    apply_human_log_ticks(ax2, "both", arg2_semantic=True)
    ax2.set_xlabel("Settlement rank")
    ax2.set_ylabel("Peak population (inhabitants)")
    ax2.set_title("B. Settlement Rank-Size Distribution", fontsize=9.8, pad=6)
    ax2.legend(loc="lower left", fontsize=7.3, frameon=True, facecolor="white", framealpha=0.92)
  else:
    ax2.text(0.5, 0.5, "Insufficient sample for rank-size regression", ha="center", va="center", transform=ax2.transAxes)

  fig.subplots_adjust(left=0.18, right=0.97, top=0.88, bottom=0.14, wspace=0.38)
  save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def main ():
  itin = load_json5_simple(ITIN_PATH)
  print("[1] Pre-projecting high-resolution island inset & South Atlantic basemaps...", flush=True)
  gal_land, gal_riv = load_basemap_cache(PROJ_GALAPAGOS, (-93.0, -2.5, -88.0, 2.5), arg2_show_modern_borders=True, arg3_high_res=True)
  jf_land, jf_riv = load_basemap_cache(PROJ_JUAN_FERNANDEZ, (-81.5, -34.4, -78.2, -33.1), arg2_show_modern_borders=True, arg3_high_res=True)
  flk_land, flk_riv = load_basemap_cache(PROJ_FALKLANDS, (-62.5, -53.2, -56.5, -50.5), arg2_show_modern_borders=True, arg3_high_res=True)
  sg_land, sg_riv = load_basemap_cache(PROJ_SOUTH_GEORGIA, (-39.5, -55.6, -34.5, -53.2), arg2_show_modern_borders=True, arg3_high_res=True)
  ss_land, ss_riv = load_basemap_cache(PROJ_SOUTH_SANDWICH, (-29.5, -60.5, -24.5, -55.5), arg2_show_modern_borders=True, arg3_high_res=True)
  basemaps = {
    "gal_land": gal_land, "gal_riv": gal_riv,
    "jf_land": jf_land, "jf_riv": jf_riv,
    "flk_land": flk_land, "flk_riv": flk_riv,
    "sg_land": sg_land, "sg_riv": sg_riv,
    "ss_land": ss_land, "ss_riv": ss_riv,
  }

  print(f"[2] Rendering 3 POLARIS-grade figures across all {len(itin['chapters'])} QUIPU chapters...", flush=True)
  for ch in itin["chapters"]:
    key = ch["key"]
    ch_dir = os.path.join(QUIPU_DIR, ch["folder"])
    summary = json.load(open(os.path.join(ch_dir, f"{key}_summary.json"), encoding="utf-8"))
    render_regional_map(ch, summary, basemaps)
    render_trajectory_figure(ch, summary)
    render_urban_hierarchy_figure(ch, summary)
    print(f"  [CH {ch['index']:02d}] {key}: 3 figures verified & saved", flush=True)
  print("[DONE] Generated 51 chapter figures cleanly.", flush=True)


if __name__ == "__main__":
  main()
