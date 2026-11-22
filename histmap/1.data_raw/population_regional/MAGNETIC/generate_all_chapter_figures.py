"""Generates POLARIS-grade vector cartography and demographic diagnostic figures for all 21 Project MAGNETIC chapters.

Produces three publication figures per chapter inside `<chapter_dir>/figures/`:
  1. `<stem>_regional_map.png` — Equal-Area Albers vector PatchCollection sub-regions, Natural Earth
     basemap & rivers, curved graticule, dedicated Greenland/Macaronesia inset when in domain,
     in-bounds top-settlement callouts and bottom region legend.
  2. `<stem>_population_trajectory.png` — Two-panel sub-regional population trajectory & end-epoch
     population density (inhabitants / km²) bar chart with European decimals.
  3. `<stem>_urban_hierarchy.png` — Two-panel top named settlements horizontal bar chart & empirical
     log-log rank-size distribution (for n >= 25 settlements) formatted with human European log ticks.
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
from matplotlib.patches import Patch, Polygon as MplPolygon
import numpy as np
from shapely.geometry import box, shape
from shapely.ops import unary_union

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC")
SHARED = os.path.join(MAG_DIR, "_shared")
SCRIPTS_DIR = os.path.join(SHARED, "scripts")
SUBREG_DIR = os.path.join(SHARED, "_gis_cache", "chapter_subregions")
ITIN_PATH = os.path.join(MAG_DIR, "magnetic_itinerary.json5")

if SCRIPTS_DIR not in sys.path:
  sys.path.insert(0, SCRIPTS_DIR)

from magnetic_map_helper import (
  AlbersEqualAreaConic,
  PROJ_EUROPE,
  PROJ_GREENLAND,
  PROJ_MACARONESIA,
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


def render_regional_map (arg0_ch, arg1_summary, arg2_basemaps):
  key = arg0_ch["key"]
  ch_dir = os.path.join(MAG_DIR, arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", f"{key}_regional_map.png")
  vec_path = os.path.join(SUBREG_DIR, f"{key}_subregions.geojson")
  gj = json.load(open(vec_path, encoding="utf-8"))

  rgb_map = {r["id"]: r["rgb"] for r in arg1_summary["subregions"]}
  name_map = {r["id"]: r["name"] for r in arg1_summary["subregions"]}

  # Partition polygons into European mainland/North Atlantic vs distant Greenland / Macaronesia insets
  main_feats = []
  gl_feats = []
  mac_feats = []
  box_gl = unary_union([box(-76.0, 58.0, -26.0, 84.5), box(-26.0, 68.0, -10.5, 84.5)])
  box_mac = box(-34.0, 26.5, -12.0, 41.0)
  for feat in gj.get("features", []):
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    g = shape(geom_raw).buffer(0)
    if g.is_empty:
      continue
    rid = str(feat.get("properties", {}).get("id") or "")
    g_gl = g.intersection(box_gl)
    if not g_gl.is_empty and g_gl.area > 1e-4:
      gl_feats.append((rid, g_gl))
    g_mac = g.intersection(box_mac)
    if not g_mac.is_empty and g_mac.area > 1e-4:
      mac_feats.append((rid, g_mac))
    g_rem = g.difference(box_gl).difference(box_mac)
    if not g_rem.is_empty and g_rem.area > 1e-4:
      main_feats.append((rid, g_rem))

  if not main_feats:
    main_feats = gl_feats + mac_feats
    gl_feats, mac_feats = [], []

  # Fit chapter-specific Albers projection centred on mainland extent
  union_main = unary_union([g for _, g in main_feats])
  minx, miny, maxx, maxy = union_main.bounds
  lon0 = max(-15.0, min(26.0, 0.5 * (minx + maxx)))
  lat_span = max(3.0, maxy - miny)
  lat1 = max(34.0, miny + 0.25 * lat_span)
  lat2 = min(72.0, maxy - 0.25 * lat_span)
  lat0 = 0.5 * (lat1 + lat2)
  proj_main = AlbersEqualAreaConic(lon0, lat1, lat2, lat0)

  # Pre-project basemap for this chapter's extent (NEVER draw modern 2025 country borders on pre-1945 historical chapters!)
  clip_bb = (max(-32.0, minx - 8.0), max(30.0, miny - 5.0), min(45.0, maxx + 8.0), min(82.0, maxy + 5.0))
  is_modern_ch = (int(arg0_ch.get("index", 1)) >= 19)
  land_p, riv_g = load_basemap_cache(proj_main, clip_bb, arg2_show_modern_borders=is_modern_ch)

  apply_viscount_style()
  fig, ax = plt.subplots(figsize=(9.6, 6.2), dpi=300)
  apply_viscount_style(ax, {"grid": False})
  draw_basemap(ax, land_p, riv_g)

  # Project and plot sub-region vector polygons
  proj_all_main = []
  legend_handles = []
  seen_leg = set()
  for idx_f, (rid, g) in enumerate(main_feats):
    pg = prepare_and_project(g, proj_main, 0.25)
    if pg.is_empty:
      continue
    proj_all_main.append(pg)
    patches = geom_to_patches(pg)
    hex_c = mute_rgb_hex(rgb_map.get(rid), idx_f, 0.38)
    if patches:
      ax.add_collection(PatchCollection(patches, facecolor=hex_c, edgecolor="#334155", linewidths=0.55, alpha=0.88, zorder=2.5))
    if rid not in seen_leg:
      seen_leg.add(rid)
      legend_handles.append(Patch(facecolor=hex_c, edgecolor="#334155", linewidth=0.55, label=truncate_label(name_map.get(rid, rid), 30)))

  # Bold dissolved outer perimeter
  if proj_all_main:
    outer_pg = unary_union([pg.buffer(0) for pg in proj_all_main])
    outer_patches = geom_to_patches(outer_pg)
    if outer_patches:
      ax.add_collection(PatchCollection(outer_patches, facecolor="none", edgecolor="#111827", linewidths=1.15, zorder=3.6))
    xlim, ylim = pad_projected_bounds(outer_pg.bounds, arg1_target_aspect=1.54, arg2_pad_factor=1.18, arg3_min_span_km=360.0)
  else:
    xlim, ylim = (-1200.0, 1200.0), (-800.0, 800.0)

  ax.set_xlim(*xlim)
  ax.set_ylim(*ylim)
  ax.set_aspect("equal", adjustable="box")
  ax.set_xticks([])
  ax.set_yticks([])

  glats = [v for v in (35, 40, 45, 50, 55, 60, 65, 70) if miny - 2 <= v <= maxy + 2]
  glons = [v for v in (-20, -10, 0, 10, 20, 30) if minx - 4 <= v <= maxx + 4]
  draw_graticule(ax, proj_main, xlim, ylim, glats, glons, (clip_bb[0], clip_bb[2]), (clip_bb[1], clip_bb[3]))

  # Add distant Greenland inset if present in this chapter
  if gl_feats:
    ax_gl = ax.inset_axes([0.02, 0.57, 0.25, 0.40])
    apply_viscount_style(ax_gl, {"grid": False})
    draw_basemap(ax_gl, arg2_basemaps["gl_land"], arg2_basemaps["gl_riv"])
    gl_pgs = []
    for idx_g, (rid, g) in enumerate(gl_feats):
      pg = prepare_and_project(g, PROJ_GREENLAND, 0.35)
      if pg.is_empty:
        continue
      gl_pgs.append(pg)
      hex_c = mute_rgb_hex(rgb_map.get(rid), idx_g + 5, 0.38)
      ps = geom_to_patches(pg)
      if ps:
        ax_gl.add_collection(PatchCollection(ps, facecolor=hex_c, edgecolor="#111827", linewidths=0.7, alpha=0.88, zorder=2.5))
      if rid not in seen_leg:
        seen_leg.add(rid)
        legend_handles.append(Patch(facecolor=hex_c, edgecolor="#334155", linewidth=0.55, label=truncate_label(name_map.get(rid, rid), 30)))
    if gl_pgs:
      gx, gy = pad_projected_bounds(unary_union(gl_pgs).bounds, arg1_target_aspect=0.78, arg2_pad_factor=1.18, arg3_min_span_km=600.0)
      ax_gl.set_xlim(*gx)
      ax_gl.set_ylim(*gy)
    ax_gl.set_aspect("equal", adjustable="box")
    ax_gl.set_xticks([])
    ax_gl.set_yticks([])
    ax_gl.set_title("Greenland", fontsize=7.0, pad=2)

  # Add distant Macaronesia inset if present in this chapter
  if mac_feats:
    mac_box = [0.02, 0.04, 0.24, 0.30] if gl_feats else [0.02, 0.62, 0.24, 0.30]
    ax_mc = ax.inset_axes(mac_box)
    apply_viscount_style(ax_mc, {"grid": False})
    draw_basemap(ax_mc, arg2_basemaps["mac_land"], arg2_basemaps["mac_riv"])
    mc_pgs = []
    for idx_m, (rid, g) in enumerate(mac_feats):
      pg = prepare_and_project(g, PROJ_MACARONESIA, 0.20)
      if pg.is_empty:
        continue
      mc_pgs.append(pg)
      hex_c = mute_rgb_hex(rgb_map.get(rid), idx_m + 7, 0.38)
      ps = geom_to_patches(pg)
      if ps:
        ax_mc.add_collection(PatchCollection(ps, facecolor=hex_c, edgecolor="#111827", linewidths=0.7, alpha=0.88, zorder=2.5))
      if rid not in seen_leg:
        seen_leg.add(rid)
        legend_handles.append(Patch(facecolor=hex_c, edgecolor="#334155", linewidth=0.55, label=truncate_label(name_map.get(rid, rid), 30)))
    if mc_pgs:
      mx, my = pad_projected_bounds(unary_union(mc_pgs).bounds, arg1_target_aspect=1.35, arg2_pad_factor=1.28, arg3_min_span_km=350.0)
      ax_mc.set_xlim(*mx)
      ax_mc.set_ylim(*my)
    ax_mc.set_aspect("equal", adjustable="box")
    ax_mc.set_xticks([])
    ax_mc.set_yticks([])
    ax_mc.set_title("Macaronesia", fontsize=7.0, pad=2)

  # Plot settlement cloud + top 8 in-bounds callouts
  sett_path = os.path.join(ch_dir, f"{key}_settlements.json")
  setts = json.load(open(sett_path, encoding="utf-8"))
  xs_s, ys_s = [], []
  for s in setts.values():
    lat, lon = float(s["coords"][0]), float(s["coords"][1])
    px, py = proj_main.fwd_pt(lon, lat)
    if xlim[0] <= px <= xlim[1] and ylim[0] <= py <= ylim[1]:
      xs_s.append(px)
      ys_s.append(py)
  if xs_s:
    ax.scatter(xs_s, ys_s, s=4.5, c="#1e293b", alpha=0.35, linewidths=0.0, zorder=4.8)

  top_items = [
    {"label": truncate_label(s["name"], 18), "lon": s["lon"], "lat": s["lat"]}
    for s in arg1_summary["top_settlements"][:14]
  ]
  d0, d1 = arg0_ch["domain"]
  title_str = f"{arg0_ch['itinerary_title']} ({format_year_label(d0)}–{format_year_label(d1)})"
  ax.set_title(title_str, fontsize=10.5, pad=8)

  n_leg = len(legend_handles)
  ncol = 3 if n_leg >= 4 else max(1, n_leg)
  nrows = math.ceil(n_leg / max(1, ncol))
  bot_margin = min(0.32, 0.08 + 0.048 * nrows)
  fig.subplots_adjust(left=0.03, right=0.97, top=0.92, bottom=bot_margin)

  if legend_handles:
    fig.legend(
      handles=legend_handles,
      loc="lower center",
      ncol=ncol,
      fontsize=7.2,
      frameon=True,
      facecolor="white",
      edgecolor="#cbd5e1",
      bbox_to_anchor=(0.5, 0.015),
    )

  place_inbounds_callouts(
    fig, ax, top_items, proj_main, xlim, ylim,
    {"max_labels": 7, "min_sep_px": 54.0, "fontsize": 6.6, "margin_px": 10.0, "dot_color": "#b91c1c"},
  )
  save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_trajectory_figure (arg0_ch, arg1_summary):
  key = arg0_ch["key"]
  ch_dir = os.path.join(MAG_DIR, arg0_ch["folder"])
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
  ax1.set_ylim(0.0, max_v * 1.24)
  ax1.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, integer=True))
  ax1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: f"{int(abs(x))}BC" if x < 0 else f"{int(x)}"))
  ax1.tick_params(axis="x", labelsize=8.0)
  ax1.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  ax1.set_xlabel("Calendar year")
  ax1.set_ylabel("Population (inhabitants)")
  ax1.set_title("A. Demographic Trajectory by Sub-Region", fontsize=9.8, pad=6)
  ax1.legend(loc="upper left", fontsize=7.0, frameon=True, facecolor="white", framealpha=0.92)

  # Panel B: End-epoch population density (inhabitants / km²) by sub-region
  dens_items = []
  for sr in subregs:
    p_end = sr["population"].get(last_yr, 0)
    a_km2 = max(1.0, float(sr["area_km2"]))
    dens_items.append((truncate_label(sr["name"], 24), p_end / a_km2, mute_rgb_hex(sr["rgb"], 0, 0.25)))
  dens_items.sort(key=lambda x: x[1])
  show_d = dens_items[-10:]
  y_pos = np.arange(len(show_d))
  vals_d = [x[1] for x in show_d]
  ax2.barh(y_pos, vals_d, color=[x[2] for x in show_d], edgecolor="#334155", linewidth=0.55)
  ax2.set_yticks(y_pos)
  ax2.set_yticklabels([x[0] for x in show_d], fontsize=7.6)
  max_d = max(vals_d) if vals_d else 1.0
  ax2.set_xlim(0.0, max_d * 1.28)
  ax2.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5))
  ax2.xaxis.set_major_formatter(euro_tick_formatter(1 if max_d < 20 else 0))
  for yp, vd in zip(y_pos, vals_d):
    lbl_d = format_euro_number(vd, 2 if vd < 5 else (1 if vd < 50 else 0))
    ax2.text(vd + max_d * 0.025, yp, lbl_d, va="center", ha="left", fontsize=7.2, color="#1e293b")
  ax2.set_xlabel("Density (inhabitants / km²)")
  ax2.set_title(f"B. Sub-Regional Density in {format_year_label(yrs[-1])}", fontsize=9.8, pad=6)

  fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.14, wspace=0.46)
  save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_urban_hierarchy_figure (arg0_ch, arg1_summary):
  key = arg0_ch["key"]
  ch_dir = os.path.join(MAG_DIR, arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", f"{key}_urban_hierarchy.png")
  sett_path = os.path.join(ch_dir, f"{key}_settlements.json")
  setts = json.load(open(sett_path, encoding="utf-8"))

  peaks = []
  for s in setts.values():
    pdict = s.get("population") or {}
    if pdict:
      pk = max(int(v) for v in pdict.values() if int(v) > 0)
      peaks.append((s["name"], s.get("country", ""), pk))
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

  # Panel B: Rank-size distribution (strictly for n >= 25 settlements!)
  n_all = len(peaks)
  if n_all >= 25:
    ranks = np.arange(1, n_all + 1, dtype=np.float64)
    pops = np.array([x[2] for x in peaks], dtype=np.float64)
    ax2.loglog(ranks, pops, "o", markersize=2.8, alpha=0.55, color="#2563eb", label=f"Observed (n={n_all:,})".replace(",", "."))
    # Fit OLS slope on top 50% or min(150, n) settlements to avoid rural truncation tail
    n_fit = min(max(25, n_all // 2), 180)
    lx = np.log10(ranks[:n_fit])
    ly = np.log10(pops[:n_fit])
    slope, intercept = np.polyfit(lx, ly, 1)
    y_hat = slope * lx + intercept
    ss_res = float(np.sum((ly - y_hat) ** 2))
    ss_tot = float(np.sum((ly - np.mean(ly)) ** 2))
    r2 = max(0.0, 1.0 - ss_res / max(1e-12, ss_tot))
    ax2.loglog(ranks[:n_fit], 10.0 ** y_hat, "-", linewidth=1.6, color="#dc2626", label=rf"Power fit ($\alpha = {format_mathtext_euro(-slope, 2)}$, $R^2 = {format_mathtext_euro(r2, 2)}$)")
    ax2.set_xlim(0.8, n_all * 1.4)
    ax2.set_ylim(max(20.0, float(pops.min()) * 0.65), float(pops.max()) * 2.2)
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
  print("[1] Pre-projecting Greenland & Macaronesia inset basemaps...", flush=True)
  gl_land, gl_riv = load_basemap_cache(PROJ_GREENLAND, (-76.0, 58.0, -8.0, 84.0), arg2_show_modern_borders=False)
  mac_land, mac_riv = load_basemap_cache(PROJ_MACARONESIA, (-33.0, 26.5, -12.0, 41.0), arg2_show_modern_borders=False)
  basemaps = {"gl_land": gl_land, "gl_riv": gl_riv, "mac_land": mac_land, "mac_riv": mac_riv}

  print(f"[2] Rendering 3 POLARIS-grade figures across all {len(itin['chapters'])} MAGNETIC chapters...", flush=True)
  for ch in itin["chapters"]:
    key = ch["key"]
    ch_dir = os.path.join(MAG_DIR, ch["folder"])
    summary = json.load(open(os.path.join(ch_dir, f"{key}_summary.json"), encoding="utf-8"))
    render_regional_map(ch, summary, basemaps)
    render_trajectory_figure(ch, summary)
    render_urban_hierarchy_figure(ch, summary)
    print(f"  [CH {ch['index']:02d}] {key}: 3 figures verified & saved", flush=True)
  print("[DONE] Generated 63 chapter figures cleanly.", flush=True)


if __name__ == "__main__":
  main()
