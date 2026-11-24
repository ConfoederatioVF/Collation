"""Generates POLARIS-grade vector cartography and demographic diagnostic figures for all 16 Project AUSTRAL chapters.

Produces three publication figures per chapter inside `<chapter_dir>/figures/` (48 PNGs total):
  1. `<stem>_regional_map.png` — Equal-Area vector PatchCollection sub-regions (`LAEA` / `AEAC`)
     with antimeridian-safe Pacific longitude shifting, Natural Earth 10m physical coastlines &
     rivers (zero modern 2025 borders on pre-1945 chapters Ch 01–11), dedicated insets/dual panels
     for distant exclaves & archipelagos, in-bounds settlement callouts and clean bottom legend.
  2. `<stem>_population_trajectory.png` — Two-panel sub-regional population trajectory & end-epoch
     population density (`inhabitants / km²`) horizontal bar chart with European decimals.
  3. `<stem>_urban_hierarchy.png` — Two-panel top named settlements horizontal bar chart & empirical
     log-log rank-size distribution (`n >= 25`) formatted with plain European semantic log ticks.
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
AUS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL")
SHARED = os.path.join(AUS_DIR, "_shared")
SCRIPTS_DIR = os.path.join(SHARED, "scripts")
SUBREG_DIR = os.path.join(SHARED, "_gis_cache", "chapter_subregions")
ITIN_PATH = os.path.join(AUS_DIR, "austral_itinerary.json5")

if SCRIPTS_DIR not in sys.path:
  sys.path.insert(0, SCRIPTS_DIR)

from austral_map_helper import (
  AlbersEqualAreaConic,
  LambertAzimuthalEqualArea,
  PROJ_AUSTRALIA,
  PROJ_CHATHAMS,
  PROJ_EAST_POLYNESIA,
  PROJ_LINE_PHOENIX,
  PROJ_MELANESIA,
  PROJ_MICRONESIA,
  PROJ_NEW_GUINEA,
  PROJ_NEW_ZEALAND,
  PROJ_NORFOLK_LORD_HOWE,
  PROJ_RAPA_NUI_PITCAIRN,
  PROJ_WEST_POLYNESIA,
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
  shift_geom_pacific,
  shift_lon_scalar,
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
  if y == 0:
    return "1AD"
  return f"{y}AD" if y <= 1500 else str(y)


def truncate_label (arg0_text, arg1_max=26):
  s = str(arg0_text or "").strip()
  if len(s) <= arg1_max:
    return s
  return s[: arg1_max - 1].rstrip(" ,;-") + "…"


def load_shifted_subregions (arg0_key):
  """Loads `<stem>_subregions.geojson` and shifts all polygons cleanly into continuous Pacific `[95..265]`."""
  vec_path = os.path.join(SUBREG_DIR, f"{arg0_key}_subregions.geojson")
  gj = json.load(open(vec_path, encoding="utf-8"))
  feats = []
  for feat in gj.get("features", []):
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    g = shift_geom_pacific(shape(geom_raw), 95.0, -95.0, -56.0, 32.0)
    if g.is_empty:
      continue
    props = feat.get("properties") or {}
    rid = str(props.get("id") or "")
    feats.append((rid, g))
  return feats


def draw_subregion_collection (arg0_ax, arg1_feats, arg2_proj, arg3_rgb_map, arg4_name_map, arg5_legend_map, arg6_options=None):
  """Projects and renders sub-region polygons onto an axes, adding crisp archipelago halos for tiny islands."""
  opts = arg6_options if isinstance(arg6_options, dict) else {}
  halo_thresh_km2 = float(opts.get("halo_thresh_km2", 0.0))
  halo_size = float(opts.get("halo_size", 46.0))
  seg_deg = float(opts.get("seg_deg", 0.25))
  edge_lw = float(opts.get("edge_lw", 0.55))
  draw_outer = bool(opts.get("draw_outer", True))

  proj_geoms = []
  for idx_f, (rid, g) in enumerate(arg1_feats):
    pg = prepare_and_project(g, arg2_proj, seg_deg)
    if pg.is_empty:
      continue
    proj_geoms.append(pg)
    patches = geom_to_patches(pg)
    hex_c = mute_rgb_hex(arg3_rgb_map.get(rid), idx_f, 0.36)
    if patches:
      arg0_ax.add_collection(
        PatchCollection(patches, facecolor=hex_c, edgecolor="#334155", linewidths=edge_lw, alpha=0.88, zorder=2.5)
      )
    if halo_thresh_km2 > 0.0 and pg.area < halo_thresh_km2:
      rp = pg.representative_point()
      arg0_ax.scatter(
        [rp.x], [rp.y],
        s=halo_size, facecolor=hex_c, edgecolor="#1e293b", linewidths=0.75, alpha=0.82, zorder=2.8
      )
    if rid not in arg5_legend_map:
      arg5_legend_map[rid] = Patch(
        facecolor=hex_c, edgecolor="#334155", linewidth=0.55,
        label=truncate_label(arg4_name_map.get(rid, rid), 28)
      )

  if draw_outer and proj_geoms:
    try:
      outer_pg = unary_union([pg.buffer(0) for pg in proj_geoms])
      outer_patches = geom_to_patches(outer_pg)
      if outer_patches:
        arg0_ax.add_collection(
          PatchCollection(outer_patches, facecolor="none", edgecolor="#111827", linewidths=0.95, zorder=3.6)
        )
    except Exception:
      pass

  return proj_geoms


def plot_settlement_cloud (arg0_ax, arg1_setts, arg2_proj, arg3_xlim, arg4_ylim):
  """Plots background settlement cloud inside projected panel bounds."""
  xs_s, ys_s = [], []
  for s in arg1_setts.values():
    lat, lon = float(s["coords"][0]), float(s["coords"][1])
    px, py = arg2_proj.fwd_pt(lon, lat)
    if arg3_xlim[0] <= px <= arg3_xlim[1] and arg4_ylim[0] <= py <= arg4_ylim[1]:
      xs_s.append(px)
      ys_s.append(py)
  if xs_s:
    n_pts = len(xs_s)
    pt_s = 1.6 if n_pts > 800 else (3.5 if n_pts > 200 else 6.0)
    pt_a = 0.28 if n_pts > 800 else (0.38 if n_pts > 200 else 0.48)
    arg0_ax.scatter(xs_s, ys_s, s=pt_s, c="#1e293b", alpha=pt_a, linewidths=0.0, zorder=4.8)


def build_compact_legend_handles (arg0_legend_map, arg1_summary, arg2_max_items=15):
  """Returns ordered legend handles, collapsing overflow beyond `arg2_max_items` cleanly to prevent overlap."""
  subregs = arg1_summary.get("subregions", [])
  ranked = sorted(subregs, key=lambda r: -int(r.get("end_epoch_population", 0)))
  handles = []
  shown = 0
  for sr in ranked:
    rid = sr["id"]
    if rid in arg0_legend_map:
      if shown < arg2_max_items:
        handles.append(arg0_legend_map[rid])
        shown += 1
  overflow = len(arg0_legend_map) - shown
  if overflow > 0:
    handles.append(Patch(facecolor="#cbd5e1", edgecolor="#334155", linewidth=0.55, label=f"Other sub-regions ({overflow})"))
  return handles


def attach_bottom_legend (arg0_fig, arg1_handles, arg2_top=0.92, arg3_left=0.03, arg4_right=0.97, arg5_wspace=0.08):
  """Places a clean bottom legend with dynamic bottom margin so it never touches subplot spines."""
  n_leg = len(arg1_handles)
  ncol = 4 if n_leg >= 10 else (3 if n_leg >= 4 else max(1, n_leg))
  nrows = math.ceil(n_leg / max(1, ncol))
  bot_margin = min(0.32, 0.065 + 0.046 * nrows)
  arg0_fig.subplots_adjust(left=arg3_left, right=arg4_right, top=arg2_top, bottom=bot_margin, wspace=arg5_wspace)
  if arg1_handles:
    arg0_fig.legend(
      handles=arg1_handles,
      loc="lower center",
      ncol=ncol,
      fontsize=6.8 if ncol >= 4 else 7.1,
      frameon=True,
      facecolor="white",
      edgecolor="#cbd5e1",
      bbox_to_anchor=(0.5, 0.012),
    )


def clean_callout_name (arg0_text):
  """Returns a crisp, concise settlement name for map callouts without redundant `(Metro)` suffixes."""
  s = str(arg0_text or "").replace(" (Metro)", "").strip()
  if " - " in s and len(s) > 16:
    s = s.split(" - ")[0].strip()
  return truncate_label(s, 18)


def render_regional_map (arg0_ch, arg1_summary):
  """Renders the chapter's equal-area antimeridian-safe vector cartography figure."""
  key = arg0_ch["key"]
  ch_idx = int(arg0_ch["index"])
  ch_dir = os.path.join(AUS_DIR, arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", f"{key}_regional_map.png")
  feats = load_shifted_subregions(key)
  setts = json.load(open(os.path.join(ch_dir, f"{key}_settlements.json"), encoding="utf-8"))

  # NEVER draw modern 2025 country borders on pre-1945 historical chapters (Ch 01-11)!
  is_modern_ch = (ch_idx >= 12)

  rgb_map = {r["id"]: r["rgb"] for r in arg1_summary["subregions"]}
  name_map = {r["id"]: r["name"] for r in arg1_summary["subregions"]}
  legend_map = {}

  d0, d1 = arg0_ch["domain"]
  title_str = f"{arg0_ch['title']} ({format_year_label(d0)}–{format_year_label(d1)})"

  seen_call = set()
  top_items = []
  for s in arg1_summary["top_settlements"]:
    cn = clean_callout_name(s["name"])
    if cn.lower() in seen_call:
      continue
    seen_call.add(cn.lower())
    top_items.append({"label": cn, "lon": s["lon"], "lat": s["lat"]})
    if len(top_items) >= 20:
      break

  apply_viscount_style()

  # --- CASE 1: Australia chapters (Ch 01, 06, 12) -> Mainland + Norfolk/Lord Howe inset ---
  if key in ("pre_1788_australia", "colonial_australia", "modern_australia"):
    box_nlh = box(157.5, -33.0, 170.0, -27.5)
    main_f, nlh_f = [], []
    for rid, g in feats:
      g_in = g.intersection(box_nlh)
      if not g_in.is_empty and g_in.area > 1e-6:
        nlh_f.append((rid, g_in))
      g_out = g.difference(box_nlh)
      if not g_out.is_empty and g_out.area > 1e-6:
        main_f.append((rid, g_out))

    fig, ax = plt.subplots(figsize=(9.8, 6.4), dpi=300)
    apply_viscount_style(ax, {"grid": False})
    land_p, riv_g = load_basemap_cache(PROJ_AUSTRALIA, (100.0, -48.0, 160.0, -5.0), arg2_show_modern_borders=is_modern_ch)
    draw_basemap(ax, land_p, riv_g)
    pgs = draw_subregion_collection(ax, main_f, PROJ_AUSTRALIA, rgb_map, name_map, legend_map, {"seg_deg": 0.25})
    xlim, ylim = pad_projected_bounds(unary_union(pgs).bounds, arg1_target_aspect=1.45, arg2_pad_factor=1.14, arg3_min_span_km=600.0)
    # Add extra western ocean padding so the lower-left Lord Howe & Norfolk inset clears SW Western Australia cleanly
    w_span = xlim[1] - xlim[0]
    xlim = (xlim[0] - 0.11 * w_span, xlim[1] + 0.01 * w_span)
    h_span = (xlim[1] - xlim[0]) / 1.45
    yc = 0.5 * (ylim[0] + ylim[1])
    ylim = (yc - 0.5 * h_span, yc + 0.5 * h_span)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    draw_graticule(ax, PROJ_AUSTRALIA, xlim, ylim, [-40, -30, -20, -10], [115, 125, 135, 145, 155], (102.0, 160.0), (-48.0, -5.0))
    plot_settlement_cloud(ax, setts, PROJ_AUSTRALIA, xlim, ylim)

    if nlh_f:
      ax_in = ax.inset_axes([0.015, 0.025, 0.175, 0.175])
      apply_viscount_style(ax_in, {"grid": False})
      l_in, r_in = load_basemap_cache(PROJ_NORFOLK_LORD_HOWE, (156.5, -34.0, 171.0, -26.5), arg2_show_modern_borders=is_modern_ch)
      draw_basemap(ax_in, l_in, r_in)
      in_pgs = draw_subregion_collection(
        ax_in, nlh_f, PROJ_NORFOLK_LORD_HOWE, rgb_map, name_map, legend_map,
        {"halo_thresh_km2": 5000.0, "halo_size": 44.0, "seg_deg": 0.15, "draw_outer": False}
      )
      if in_pgs:
        ix, iy = pad_projected_bounds(unary_union(in_pgs).bounds, arg1_target_aspect=1.35, arg2_pad_factor=1.50, arg3_min_span_km=320.0)
        ax_in.set_xlim(*ix)
        ax_in.set_ylim(*iy)
      ax_in.set_aspect("equal", adjustable="box")
      ax_in.set_xticks([])
      ax_in.set_yticks([])
      ax_in.set_title("Lord Howe & Norfolk", fontsize=6.0, pad=1.8)

    ax.set_title(title_str, fontsize=10.2, pad=8)
    attach_bottom_legend(fig, build_compact_legend_handles(legend_map, arg1_summary, 12))
    place_inbounds_callouts(
      fig, ax, top_items, PROJ_AUSTRALIA, xlim, ylim,
      {"max_labels": 7, "min_sep_px": 54.0, "fontsize": 6.6, "margin_px": 10.0, "dot_color": "#b91c1c"}
    )
    save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})
    return

  # --- CASE 2: New Zealand chapters (Ch 05, 07, 13) -> Mainland + Chatham Islands inset ---
  if key in ("pre_european_new_zealand", "colonial_new_zealand", "modern_new_zealand"):
    box_ch = box(181.5, -45.5, 186.0, -42.5)
    main_f, ch_f = [], []
    for rid, g in feats:
      g_in = g.intersection(box_ch)
      if not g_in.is_empty and g_in.area > 1e-6:
        ch_f.append((rid, g_in))
      g_out = g.difference(box_ch)
      if not g_out.is_empty and g_out.area > 1e-6:
        main_f.append((rid, g_out))

    fig, ax = plt.subplots(figsize=(9.4, 6.8), dpi=300)
    apply_viscount_style(ax, {"grid": False})
    land_p, riv_g = load_basemap_cache(PROJ_NEW_ZEALAND, (163.0, -49.0, 181.0, -32.0), arg2_show_modern_borders=is_modern_ch)
    draw_basemap(ax, land_p, riv_g)
    pgs = draw_subregion_collection(ax, main_f, PROJ_NEW_ZEALAND, rgb_map, name_map, legend_map, {"seg_deg": 0.15})
    xlim, ylim = pad_projected_bounds(unary_union(pgs).bounds, arg1_target_aspect=1.32, arg2_pad_factor=1.15, arg3_min_span_km=500.0)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    draw_graticule(ax, PROJ_NEW_ZEALAND, xlim, ylim, [-46, -44, -42, -40, -38, -36], [166, 170, 174, 178], (163.0, 181.0), (-49.0, -32.0))
    plot_settlement_cloud(ax, setts, PROJ_NEW_ZEALAND, xlim, ylim)

    if ch_f:
      ax_in = ax.inset_axes([0.69, 0.04, 0.28, 0.27])
      apply_viscount_style(ax_in, {"grid": False})
      l_in, r_in = load_basemap_cache(PROJ_CHATHAMS, (181.5, -45.2, 185.5, -42.8), arg2_show_modern_borders=is_modern_ch)
      draw_basemap(ax_in, l_in, r_in)
      in_pgs = draw_subregion_collection(
        ax_in, ch_f, PROJ_CHATHAMS, rgb_map, name_map, legend_map,
        {"halo_thresh_km2": 1200.0, "halo_size": 40.0, "seg_deg": 0.08}
      )
      if in_pgs:
        ix, iy = pad_projected_bounds(unary_union(in_pgs).bounds, arg1_target_aspect=1.25, arg2_pad_factor=1.55, arg3_min_span_km=120.0)
        ax_in.set_xlim(*ix)
        ax_in.set_ylim(*iy)
      ax_in.set_aspect("equal", adjustable="box")
      ax_in.set_xticks([])
      ax_in.set_yticks([])
      ax_in.set_title("Chatham Is. (176°W)", fontsize=6.6, pad=2)

    ax.set_title(title_str, fontsize=10.2, pad=8)
    attach_bottom_legend(fig, build_compact_legend_handles(legend_map, arg1_summary, 18))
    place_inbounds_callouts(
      fig, ax, top_items, PROJ_NEW_ZEALAND, xlim, ylim,
      {"max_labels": 7, "min_sep_px": 50.0, "fontsize": 6.6, "margin_px": 10.0, "dot_color": "#b91c1c"}
    )
    save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})
    return

  # --- CASE 3: Dual Island Melanesia + Micronesia chapters (Ch 03, 15) ---
  if key in ("precolonial_melanesia_micro", "modern_melanesia_micro"):
    box_mel = box(152.5, -24.5, 184.0, -2.5)
    box_lp = box(185.0, -5.0, 206.0, 7.0)
    mel_f, mic_f, lp_f = [], [], []
    for rid, g in feats:
      c_lat = g.representative_point().y
      c_lon = g.representative_point().x
      if c_lat < -3.0 and 152.5 <= c_lon <= 184.0:
        mel_f.append((rid, g))
      else:
        g_lp = g.intersection(box_lp)
        if not g_lp.is_empty and g_lp.area > 1e-6:
          lp_f.append((rid, g_lp))
        g_mc = g.difference(box_lp)
        if not g_mc.is_empty and g_mc.area > 1e-6:
          mic_f.append((rid, g_mc))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 6.2), dpi=300)
    # Panel A: Island Melanesia
    apply_viscount_style(ax1, {"grid": False})
    l1, r1 = load_basemap_cache(PROJ_MELANESIA, (150.0, -26.0, 186.0, -1.0), arg2_show_modern_borders=is_modern_ch)
    draw_basemap(ax1, l1, r1)
    pg1 = draw_subregion_collection(
      ax1, mel_f, PROJ_MELANESIA, rgb_map, name_map, legend_map,
      {"halo_thresh_km2": 8000.0, "halo_size": 36.0, "seg_deg": 0.20, "draw_outer": False}
    )
    x1, y1 = pad_projected_bounds(unary_union(pg1).bounds, arg1_target_aspect=1.18, arg2_pad_factor=1.16, arg3_min_span_km=600.0)
    ax1.set_xlim(*x1)
    ax1.set_ylim(*y1)
    ax1.set_aspect("equal", adjustable="box")
    ax1.set_xticks([])
    ax1.set_yticks([])
    draw_graticule(ax1, PROJ_MELANESIA, x1, y1, [-20, -15, -10, -5], [155, 160, 165, 170, 175, 180], (150.0, 186.0), (-26.0, -1.0))
    plot_settlement_cloud(ax1, setts, PROJ_MELANESIA, x1, y1)
    ax1.set_title("A. Island Melanesia & Fiji", fontsize=9.4, pad=6)

    # Panel B: Micronesia + Phoenix/Line inset
    apply_viscount_style(ax2, {"grid": False})
    l2, r2 = load_basemap_cache(PROJ_MICRONESIA, (128.0, -6.0, 182.0, 23.0), arg2_show_modern_borders=is_modern_ch)
    draw_basemap(ax2, l2, r2)
    pg2 = draw_subregion_collection(
      ax2, mic_f, PROJ_MICRONESIA, rgb_map, name_map, legend_map,
      {"halo_thresh_km2": 18000.0, "halo_size": 52.0, "seg_deg": 0.25, "draw_outer": False}
    )
    x2, y2 = pad_projected_bounds(unary_union(pg2).bounds, arg1_target_aspect=1.18, arg2_pad_factor=1.16, arg3_min_span_km=800.0)
    ax2.set_xlim(*x2)
    ax2.set_ylim(*y2)
    ax2.set_aspect("equal", adjustable="box")
    ax2.set_xticks([])
    ax2.set_yticks([])
    draw_graticule(ax2, PROJ_MICRONESIA, x2, y2, [0, 5, 10, 15, 20], [135, 145, 155, 165, 175], (128.0, 182.0), (-6.0, 23.0))
    plot_settlement_cloud(ax2, setts, PROJ_MICRONESIA, x2, y2)
    ax2.set_title("B. Micronesia & Kiribati", fontsize=9.4, pad=6)

    if lp_f:
      ax_lp = ax2.inset_axes([0.66, 0.65, 0.32, 0.31])
      apply_viscount_style(ax_lp, {"grid": False})
      llp, rlp = load_basemap_cache(PROJ_LINE_PHOENIX, (184.0, -6.0, 206.0, 7.5), arg2_show_modern_borders=is_modern_ch)
      draw_basemap(ax_lp, llp, rlp)
      lp_pgs = draw_subregion_collection(
        ax_lp, lp_f, PROJ_LINE_PHOENIX, rgb_map, name_map, legend_map,
        {"halo_thresh_km2": 25000.0, "halo_size": 46.0, "seg_deg": 0.20, "draw_outer": False}
      )
      if lp_pgs:
        ix, iy = pad_projected_bounds(unary_union(lp_pgs).bounds, arg1_target_aspect=1.35, arg2_pad_factor=1.35, arg3_min_span_km=400.0)
        ax_lp.set_xlim(*ix)
        ax_lp.set_ylim(*iy)
      ax_lp.set_aspect("equal", adjustable="box")
      ax_lp.set_xticks([])
      ax_lp.set_yticks([])
      ax_lp.set_title("Phoenix & Line Is.", fontsize=6.4, pad=2)

    attach_bottom_legend(fig, build_compact_legend_handles(legend_map, arg1_summary, 15), arg2_top=0.90, arg5_wspace=0.06)
    mel_callouts = [it for it in top_items if it["lat"] < -3.0]
    mic_callouts = [it for it in top_items if it["lat"] >= -3.5]
    place_inbounds_callouts(
      fig, ax1, mel_callouts, PROJ_MELANESIA, x1, y1,
      {"max_labels": 5, "min_sep_px": 50.0, "fontsize": 6.4, "margin_px": 9.0, "dot_color": "#b91c1c"}
    )
    place_inbounds_callouts(
      fig, ax2, mic_callouts, PROJ_MICRONESIA, x2, y2,
      {"max_labels": 5, "min_sep_px": 50.0, "fontsize": 6.4, "margin_px": 9.0, "dot_color": "#b91c1c"}
    )
    save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})
    return

  # --- CASE 4: Polynesia chapters (Ch 04, 11, 16) -> Western/Central + Eastern + Rapa Nui/Pitcairn inset ---
  if key in ("precolonial_polynesia", "colonial_polynesia", "modern_polynesia"):
    west_f, east_f, rp_f = [], [], []
    box_rp = box(229.0, -30.0, 253.0, -22.0)
    for rid, g in feats:
      g_rp = g.intersection(box_rp)
      if not g_rp.is_empty and g_rp.area > 1e-6:
        rp_f.append((rid, g_rp))
      g_rem = g.difference(box_rp)
      if g_rem.is_empty or g_rem.area <= 1e-6:
        continue
      c_lon = g_rem.representative_point().x
      if c_lon < 204.5:
        west_f.append((rid, g_rem))
      else:
        east_f.append((rid, g_rem))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 6.2), dpi=300)
    # Panel A: Western & Central Polynesia
    apply_viscount_style(ax1, {"grid": False})
    l1, r1 = load_basemap_cache(PROJ_WEST_POLYNESIA, (173.0, -26.0, 206.0, -3.0), arg2_show_modern_borders=is_modern_ch)
    draw_basemap(ax1, l1, r1)
    pg1 = draw_subregion_collection(
      ax1, west_f, PROJ_WEST_POLYNESIA, rgb_map, name_map, legend_map,
      {"halo_thresh_km2": 12000.0, "halo_size": 48.0, "seg_deg": 0.20, "draw_outer": False}
    )
    x1, y1 = pad_projected_bounds(unary_union(pg1).bounds, arg1_target_aspect=1.18, arg2_pad_factor=1.18, arg3_min_span_km=600.0)
    ax1.set_xlim(*x1)
    ax1.set_ylim(*y1)
    ax1.set_aspect("equal", adjustable="box")
    ax1.set_xticks([])
    ax1.set_yticks([])
    draw_graticule(ax1, PROJ_WEST_POLYNESIA, x1, y1, [-20, -15, -10, -5], [175, 180, 185, 190, 195, 200], (173.0, 206.0), (-26.0, -3.0))
    plot_settlement_cloud(ax1, setts, PROJ_WEST_POLYNESIA, x1, y1)
    ax1.set_title("A. Western & Central Polynesia", fontsize=9.4, pad=6)

    # Panel B: Eastern Polynesia + Rapa Nui/Pitcairn inset
    apply_viscount_style(ax2, {"grid": False})
    l2, r2 = load_basemap_cache(PROJ_EAST_POLYNESIA, (202.0, -30.5, 229.0, -5.0), arg2_show_modern_borders=is_modern_ch)
    draw_basemap(ax2, l2, r2)
    pg2 = draw_subregion_collection(
      ax2, east_f, PROJ_EAST_POLYNESIA, rgb_map, name_map, legend_map,
      {"halo_thresh_km2": 12000.0, "halo_size": 48.0, "seg_deg": 0.20, "draw_outer": False}
    )
    x2, y2 = pad_projected_bounds(unary_union(pg2).bounds, arg1_target_aspect=1.18, arg2_pad_factor=1.18, arg3_min_span_km=600.0)
    ax2.set_xlim(*x2)
    ax2.set_ylim(*y2)
    ax2.set_aspect("equal", adjustable="box")
    ax2.set_xticks([])
    ax2.set_yticks([])
    draw_graticule(ax2, PROJ_EAST_POLYNESIA, x2, y2, [-25, -20, -15, -10], [205, 210, 215, 220, 225], (202.0, 229.0), (-30.5, -5.0))
    plot_settlement_cloud(ax2, setts, PROJ_EAST_POLYNESIA, x2, y2)
    ax2.set_title("B. Eastern Polynesia", fontsize=9.4, pad=6)

    if rp_f:
      ax_rp = ax2.inset_axes([0.55, 0.04, 0.43, 0.27])
      apply_viscount_style(ax_rp, {"grid": False})
      lrp, rrp = load_basemap_cache(PROJ_RAPA_NUI_PITCAIRN, (228.0, -30.0, 254.0, -21.5), arg2_show_modern_borders=is_modern_ch)
      draw_basemap(ax_rp, lrp, rrp)
      rp_pgs = draw_subregion_collection(
        ax_rp, rp_f, PROJ_RAPA_NUI_PITCAIRN, rgb_map, name_map, legend_map,
        {"halo_thresh_km2": 25000.0, "halo_size": 52.0, "seg_deg": 0.15, "draw_outer": False}
      )
      if rp_pgs:
        ix, iy = pad_projected_bounds(unary_union(rp_pgs).bounds, arg1_target_aspect=1.85, arg2_pad_factor=1.30, arg3_min_span_km=400.0)
        ax_rp.set_xlim(*ix)
        ax_rp.set_ylim(*iy)
      ax_rp.set_aspect("equal", adjustable="box")
      ax_rp.set_xticks([])
      ax_rp.set_yticks([])
      ax_rp.set_title("Pitcairn & Rapa Nui (109°W)", fontsize=6.4, pad=2)

    attach_bottom_legend(fig, build_compact_legend_handles(legend_map, arg1_summary, 16), arg2_top=0.90, arg5_wspace=0.06)
    place_inbounds_callouts(
      fig, ax1, top_items, PROJ_WEST_POLYNESIA, x1, y1,
      {"max_labels": 5, "min_sep_px": 48.0, "fontsize": 6.4, "margin_px": 9.0, "dot_color": "#b91c1c"}
    )
    place_inbounds_callouts(
      fig, ax2, top_items, PROJ_EAST_POLYNESIA, x2, y2,
      {"max_labels": 5, "min_sep_px": 48.0, "fontsize": 6.4, "margin_px": 9.0, "dot_color": "#b91c1c"}
    )
    save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})
    return

  # --- CASE 5: Colonial Micronesia (Ch 10) -> Main Micronesia + Phoenix/Line inset ---
  if key == "colonial_micronesia":
    box_lp = box(185.0, -5.0, 206.0, 7.0)
    main_f, lp_f = [], []
    for rid, g in feats:
      g_in = g.intersection(box_lp)
      if not g_in.is_empty and g_in.area > 1e-6:
        lp_f.append((rid, g_in))
      g_out = g.difference(box_lp)
      if not g_out.is_empty and g_out.area > 1e-6:
        main_f.append((rid, g_out))

    fig, ax = plt.subplots(figsize=(10.2, 6.0), dpi=300)
    apply_viscount_style(ax, {"grid": False})
    land_p, riv_g = load_basemap_cache(PROJ_MICRONESIA, (128.0, -6.0, 182.0, 23.0), arg2_show_modern_borders=is_modern_ch)
    draw_basemap(ax, land_p, riv_g)
    pgs = draw_subregion_collection(
      ax, main_f, PROJ_MICRONESIA, rgb_map, name_map, legend_map,
      {"halo_thresh_km2": 18000.0, "halo_size": 56.0, "seg_deg": 0.20, "draw_outer": False}
    )
    xlim, ylim = pad_projected_bounds(unary_union(pgs).bounds, arg1_target_aspect=1.65, arg2_pad_factor=1.18, arg3_min_span_km=800.0)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    draw_graticule(ax, PROJ_MICRONESIA, xlim, ylim, [0, 5, 10, 15, 20], [135, 145, 155, 165, 175], (128.0, 182.0), (-6.0, 23.0))
    plot_settlement_cloud(ax, setts, PROJ_MICRONESIA, xlim, ylim)

    if lp_f:
      ax_lp = ax.inset_axes([0.69, 0.65, 0.29, 0.31])
      apply_viscount_style(ax_lp, {"grid": False})
      llp, rlp = load_basemap_cache(PROJ_LINE_PHOENIX, (184.0, -6.0, 206.0, 7.5), arg2_show_modern_borders=is_modern_ch)
      draw_basemap(ax_lp, llp, rlp)
      lp_pgs = draw_subregion_collection(
        ax_lp, lp_f, PROJ_LINE_PHOENIX, rgb_map, name_map, legend_map,
        {"halo_thresh_km2": 25000.0, "halo_size": 48.0, "seg_deg": 0.20, "draw_outer": False}
      )
      if lp_pgs:
        ix, iy = pad_projected_bounds(unary_union(lp_pgs).bounds, arg1_target_aspect=1.35, arg2_pad_factor=1.35, arg3_min_span_km=400.0)
        ax_lp.set_xlim(*ix)
        ax_lp.set_ylim(*iy)
      ax_lp.set_aspect("equal", adjustable="box")
      ax_lp.set_xticks([])
      ax_lp.set_yticks([])
      ax_lp.set_title("Phoenix & Line Is.", fontsize=6.6, pad=2)

    ax.set_title(title_str, fontsize=10.2, pad=8)
    attach_bottom_legend(fig, build_compact_legend_handles(legend_map, arg1_summary, 12))
    place_inbounds_callouts(
      fig, ax, top_items, PROJ_MICRONESIA, xlim, ylim,
      {"max_labels": 7, "min_sep_px": 52.0, "fontsize": 6.6, "margin_px": 10.0, "dot_color": "#b91c1c"}
    )
    save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})
    return

  # --- CASE 6: New Guinea (Ch 02, 08, 14) & Colonial Island Melanesia (Ch 09) ---
  is_mel = (key == "colonial_island_melanesia")
  proj_cur = PROJ_MELANESIA if is_mel else PROJ_NEW_GUINEA
  clip_bb = (152.0, -25.0, 185.0, -4.0) if is_mel else (127.0, -13.5, 162.0, 2.0)
  glats = [-20, -15, -10] if is_mel else [-10, -5, 0]
  glons = [155, 160, 165, 170, 175, 180] if is_mel else [130, 135, 140, 145, 150, 155]
  halo_km2 = 8000.0 if is_mel else 0.0

  fig, ax = plt.subplots(figsize=(10.2, 6.0), dpi=300)
  apply_viscount_style(ax, {"grid": False})
  land_p, riv_g = load_basemap_cache(proj_cur, clip_bb, arg2_show_modern_borders=is_modern_ch)
  draw_basemap(ax, land_p, riv_g)
  pgs = draw_subregion_collection(
    ax, feats, proj_cur, rgb_map, name_map, legend_map,
    {"halo_thresh_km2": halo_km2, "halo_size": 40.0, "seg_deg": 0.20, "draw_outer": (not is_mel)}
  )
  xlim, ylim = pad_projected_bounds(unary_union(pgs).bounds, arg1_target_aspect=1.65, arg2_pad_factor=1.16, arg3_min_span_km=500.0)
  ax.set_xlim(*xlim)
  ax.set_ylim(*ylim)
  ax.set_aspect("equal", adjustable="box")
  ax.set_xticks([])
  ax.set_yticks([])
  draw_graticule(ax, proj_cur, xlim, ylim, glats, glons, (clip_bb[0], clip_bb[2]), (clip_bb[1], clip_bb[3]))
  plot_settlement_cloud(ax, setts, proj_cur, xlim, ylim)
  ax.set_title(title_str, fontsize=10.2, pad=8)
  attach_bottom_legend(fig, build_compact_legend_handles(legend_map, arg1_summary, 15))
  place_inbounds_callouts(
    fig, ax, top_items, proj_cur, xlim, ylim,
    {"max_labels": 7, "min_sep_px": 50.0, "fontsize": 6.6, "margin_px": 10.0, "dot_color": "#b91c1c"}
  )
  save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_trajectory_figure (arg0_ch, arg1_summary):
  """Renders two-panel sub-regional population trajectory & end-epoch population density bar chart."""
  key = arg0_ch["key"]
  ch_dir = os.path.join(AUS_DIR, arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", f"{key}_population_trajectory.png")

  yrs = arg1_summary["benchmark_years"]
  tot_vals = [arg1_summary["domain_totals"].get(str(y), 0) for y in yrs]
  subregs = arg1_summary["subregions"]
  last_yr = str(yrs[-1])

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 4.5), dpi=300, gridspec_kw={"width_ratios": [1.16, 1.0], "wspace": 0.46})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Domain total + top 4 sub-regions
  ax1.plot(yrs, tot_vals, marker="o", linewidth=2.0, markersize=4.4, color="#1f77b4", label="Chapter total")
  ranked_sr = sorted(subregs, key=lambda r: -r["population"].get(last_yr, 0))
  line_cols = ["#d97706", "#2a9d8f", "#9333ea", "#dc2626"]
  for idx_r, sr in enumerate(ranked_sr[:4]):
    sv = [sr["population"].get(str(y), 0) for y in yrs]
    ax1.plot(yrs, sv, marker="s", linewidth=1.2, markersize=3.0, linestyle="--", color=line_cols[idx_r], label=truncate_label(sr["name"], 24))

  max_v = max(tot_vals) if tot_vals else 1.0
  ax1.set_ylim(0.0, max_v * 1.25)
  ax1.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, integer=True))
  ax1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: f"{int(abs(x))}BC" if x < 0 else ("1AD" if int(x) == 0 else f"{int(x)}")))
  ax1.tick_params(axis="x", labelsize=8.0)
  ax1.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  ax1.set_xlabel("Calendar year")
  ax1.set_ylabel("Population (inhabitants)")
  ax1.set_title("A. Demographic Trajectory by Sub-Region", fontsize=9.8, pad=6)
  ax1.legend(loc="upper left", fontsize=6.9, frameon=True, facecolor="white", framealpha=0.92)

  # Panel B: End-epoch population density (inhabitants / km²) by sub-region
  dens_items = []
  for sr in subregs:
    p_end = sr["population"].get(last_yr, 0)
    a_km2 = float(sr["area_km2"])
    if a_km2 <= 0.5:
      continue
    dens_items.append((truncate_label(sr["name"], 24), p_end / a_km2, mute_rgb_hex(sr["rgb"], 0, 0.25)))
  dens_items.sort(key=lambda x: x[1])
  show_d = dens_items[-10:]
  y_pos = np.arange(len(show_d))
  vals_d = [x[1] for x in show_d]
  ax2.barh(y_pos, vals_d, color=[x[2] for x in show_d], edgecolor="#334155", linewidth=0.55)
  ax2.set_yticks(y_pos)
  ax2.set_yticklabels([x[0] for x in show_d], fontsize=7.5)
  max_d = max(vals_d) if vals_d else 1.0
  ax2.set_xlim(0.0, max_d * 1.30)
  ax2.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=4))
  if max_d >= 1000.0:
    ax2.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  else:
    ax2.xaxis.set_major_formatter(euro_tick_formatter(2 if max_d < 2 else (1 if max_d < 20 else 0)))
  for yp, vd in zip(y_pos, vals_d):
    lbl_d = format_semantic_population(vd) if vd >= 1000.0 else format_euro_number(vd, 2 if vd < 5 else (1 if vd < 50 else 0))
    ax2.text(vd + max_d * 0.025, yp, lbl_d, va="center", ha="left", fontsize=7.1, color="#1e293b")
  ax2.set_xlabel("Density (inhabitants / km²)")
  ax2.set_title(f"B. Sub-Regional Density in {format_year_label(yrs[-1])}", fontsize=9.8, pad=6)

  fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.14, wspace=0.48)
  save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def render_urban_hierarchy_figure (arg0_ch, arg1_summary):
  """Renders two-panel top named settlements bar chart & log-log rank-size Zipf distribution."""
  key = arg0_ch["key"]
  ch_dir = os.path.join(AUS_DIR, arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", f"{key}_urban_hierarchy.png")

  top_setts = arg1_summary["top_settlements"]
  rs_info = arg1_summary["rank_size"]
  pairs = rs_info["rank_pop_pairs"]
  zipf_fit = rs_info["all_settlements"]

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 4.6), dpi=300, gridspec_kw={"width_ratios": [1.14, 1.0], "wspace": 0.42})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Top 12 distinct named settlements (deduplicating metro vs city_proper pairs)
  seen_base = set()
  dedup_top = []
  for x in top_setts:
    if x.get("population_scope") == "suburb":
      continue
    bn = str(x["name"]).replace(" (Metro)", "").split(" - ")[0].strip().lower()
    if bn in seen_base:
      continue
    seen_base.add(bn)
    dedup_top.append(x)
    if len(dedup_top) >= 12:
      break
  if len(dedup_top) < min(12, len(top_setts)):
    dedup_top = top_setts[:12]
  top12 = list(reversed(dedup_top))
  y_pos = np.arange(len(top12))
  vals_p = [int(x["peak_pop"]) for x in top12]
  ax1.barh(y_pos, vals_p, color="#3b7ea1", edgecolor="#1e293b", linewidth=0.5)
  ax1.set_yticks(y_pos)
  ax1.set_yticklabels([truncate_label(x["name"], 22) for x in top12], fontsize=7.5)
  max_p = max(vals_p) if vals_p else 1.0
  ax1.set_xlim(0.0, max_p * 1.30)
  ax1.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=4))
  ax1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  for yp, vp in zip(y_pos, vals_p):
    ax1.text(vp + max_p * 0.022, yp, format_semantic_population(vp), va="center", ha="left", fontsize=7.0, color="#0f172a")
  ax1.set_xlabel("Peak settlement population")
  ax1.set_title("A. Largest Recorded Settlements", fontsize=9.8, pad=6)

  # Panel B: Empirical rank-size distribution (strictly for n >= 25 settlements!)
  n_all = len(pairs)
  if n_all >= 25 and zipf_fit.get("fit_valid"):
    ranks = np.array([p[0] for p in pairs], dtype=np.float64)
    pops = np.array([p[1] for p in pairs], dtype=np.float64)
    n_fmt = f"{n_all:,}".replace(",", ".")
    ax2.loglog(ranks, pops, "o", markersize=2.8, alpha=0.58, color="#2563eb", label=f"Observed (n={n_fmt})")

    n_fit = int(zipf_fit["n_fit"])
    slope = float(zipf_fit["slope"])
    intercept = float(zipf_fit["intercept"])
    alpha_val = float(zipf_fit["zipf_alpha"])
    r2_val = float(zipf_fit["r2"])
    y_hat = 10.0 ** (slope * np.log10(ranks[:n_fit]) + intercept)
    ax2.loglog(
      ranks[:n_fit], y_hat, "-", linewidth=1.6, color="#dc2626",
      label=rf"Power fit ($\alpha = {format_mathtext_euro(alpha_val, 2)}$, $R^2 = {format_mathtext_euro(r2_val, 2)}$)"
    )
    ax2.set_xlim(0.8, n_all * 1.45)
    y_top = max(float(np.max(pops)), float(np.max(y_hat))) * 1.85
    ax2.set_ylim(max(10.0, float(pops.min()) * 0.65), y_top)
    apply_human_log_ticks(ax2, "both", arg2_semantic=True)
    ax2.set_xlabel("Settlement rank")
    ax2.set_ylabel("Peak population (inhabitants)")
    ax2.set_title("B. Settlement Rank-Size Distribution", fontsize=9.8, pad=6)
    ax2.legend(loc="lower left", fontsize=7.2, frameon=True, facecolor="white", framealpha=0.92)
  else:
    ax2.text(0.5, 0.5, "Insufficient sample for rank-size regression", ha="center", va="center", transform=ax2.transAxes)
    ax2.set_title("B. Settlement Rank-Size Distribution", fontsize=9.8, pad=6)

  fig.subplots_adjust(left=0.19, right=0.97, top=0.88, bottom=0.14, wspace=0.40)
  save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})


def main ():
  itin = load_json5_simple(ITIN_PATH)
  print(f"[1] Rendering 3 POLARIS-grade figures across all {len(itin['chapters'])} AUSTRAL chapters...", flush=True)
  for ch in itin["chapters"]:
    key = ch["key"]
    ch_dir = os.path.join(AUS_DIR, ch["folder"])
    summary_p = os.path.join(ch_dir, f"{key}_summary_cache.json")
    summary = json.load(open(summary_p, encoding="utf-8"))
    render_regional_map(ch, summary)
    render_trajectory_figure(ch, summary)
    render_urban_hierarchy_figure(ch, summary)
    print(f"  [CH {ch['index']:02d}] {key:28s}: 3 figures verified & saved", flush=True)
  print("[DONE] Generated all 48 AUSTRAL chapter figures cleanly.", flush=True)


if __name__ == "__main__":
  main()
