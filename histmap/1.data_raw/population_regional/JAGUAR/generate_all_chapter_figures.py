"""Generates POLARIS-grade vector cartography and demographic diagnostic figures
for all 14 Project JAGUAR chapters (`42` PNGs total) plus crisp panel crops for
independent visual QA inside `tests/figure_panels/`.

Produces three publication figures per chapter inside `<chapter_dir>/figures/`:
  1. `<stem>_regional_map.png` — Lambert Azimuthal Equal-Area vector PatchCollection
     sub-regions, Natural Earth 10m physical coastlines & rivers, curved graticule,
     dedicated Bermuda inset (`32,3°N, 64,8°W`) on Ch 10 and Ch 14, in-bounds
     top-settlement callouts, and bottom region legend.
  2. `<stem>_population_trajectory.png` — Two-panel sub-regional population trajectory
     and end-epoch population density (inhabitants / km²) bar chart with European decimals.
  3. `<stem>_urban_hierarchy.png` — Two-panel largest recorded settlements bar chart
     and log-log rank-size distribution (`n >= 25`) with plain human European log ticks.
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
from PIL import Image
from shapely.geometry import shape
from shapely.ops import unary_union

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
JAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JAGUAR")
SHARED = os.path.join(JAG_DIR, "_shared")
SCRIPTS_DIR = os.path.join(SHARED, "scripts")
SUBREG_DIR = os.path.join(SHARED, "_gis_cache", "chapter_subregions")
ITIN_PATH = os.path.join(JAG_DIR, "jaguar_itinerary.json5")
CROPS_DIR = os.path.join(SVEA_ROOT, "tests", "figure_panels")
os.makedirs(CROPS_DIR, exist_ok=True)

if SCRIPTS_DIR not in sys.path:
  sys.path.insert(0, SCRIPTS_DIR)

from jaguar_map_helper import (
  BERMUDA_CLIP_BOX,
  LambertAzimuthalEqualArea,
  PROJ_BERMUDA,
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


def export_panel_crops (arg0_png_path, arg1_prefix, arg2_split_lr=False):
  """Exports full-res or left/right panel crops into `tests/figure_panels/` for verifier QA."""
  img = Image.open(arg0_png_path)
  w, h = img.size
  if not arg2_split_lr:
    img.save(os.path.join(CROPS_DIR, f"{arg1_prefix}.png"))
    return
  mid = int(round(w * 0.51))
  img.crop((0, 0, min(w, mid + 30), h)).save(os.path.join(CROPS_DIR, f"{arg1_prefix}_A.png"))
  img.crop((max(0, mid - 60), 0, w, h)).save(os.path.join(CROPS_DIR, f"{arg1_prefix}_B.png"))


def render_regional_map (arg0_ch, arg1_cache, arg2_bm_land):
  stem = arg0_ch["stem"]
  idx = int(arg0_ch["index"])
  ch_dir = os.path.join(JAG_DIR, arg0_ch["group"], arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", f"{stem}_regional_map.png")
  vec_path = os.path.join(SUBREG_DIR, f"{stem}_subregions.geojson")
  gj = json.load(open(vec_path, encoding="utf-8"))

  rgb_map = {r["id"]: r["rgb"] for r in arg1_cache["subregions"]}
  name_map = {r["id"]: r["name"] for r in arg1_cache["subregions"]}

  # Partition Bermuda (`32,3°N, -64,8°W`) cleanly into dedicated inset on Ch 10 & Ch 14
  main_feats = []
  bm_feats = []
  for feat in gj.get("features", []):
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    g = shape(geom_raw).buffer(0)
    if g.is_empty:
      continue
    rid = str(feat.get("properties", {}).get("id") or "")
    g_bm = g.intersection(BERMUDA_CLIP_BOX)
    if not g_bm.is_empty and g_bm.area > 1e-6:
      bm_feats.append((rid, g_bm))
    g_rem = g.difference(BERMUDA_CLIP_BOX)
    if not g_rem.is_empty and g_rem.area > 1e-5:
      main_feats.append((rid, g_rem))

  if not main_feats:
    main_feats = bm_feats
    bm_feats = []

  union_main = unary_union([g for _, g in main_feats])
  minx, miny, maxx, maxy = union_main.bounds
  lon0 = 0.5 * (minx + maxx)
  lat0 = 0.5 * (miny + maxy)
  proj_main = LambertAzimuthalEqualArea(lon0, lat0)

  clip_bb = (max(-124.0, minx - 6.0), max(2.0, miny - 4.0), min(-54.0, maxx + 6.0), min(38.0, maxy + 4.0))
  is_modern_ch = (idx >= 11)
  land_p, riv_g = load_basemap_cache(proj_main, clip_bb, arg2_show_modern_borders=is_modern_ch, arg3_high_res=True)

  apply_viscount_style()
  fig, ax = plt.subplots(figsize=(9.8, 6.2), dpi=300)
  apply_viscount_style(ax, {"grid": False})
  draw_basemap(ax, land_p, riv_g)

  proj_all_main = []
  legend_handles = []
  seen_leg = set()
  for idx_f, (rid, g) in enumerate(main_feats):
    pg = prepare_and_project(g, proj_main, 0.18)
    if pg.is_empty:
      continue
    proj_all_main.append(pg)
    patches = geom_to_patches(pg)
    hex_c = mute_rgb_hex(rgb_map.get(rid), idx_f, 0.36)
    if patches:
      ax.add_collection(PatchCollection(patches, facecolor=hex_c, edgecolor="#334155", linewidths=0.55, alpha=0.88, zorder=2.5))
    if rid not in seen_leg:
      seen_leg.add(rid)
      legend_handles.append(Patch(facecolor=hex_c, edgecolor="#334155", linewidth=0.55, label=truncate_label(name_map.get(rid, rid), 30)))

  if proj_all_main:
    outer_pg = unary_union([pg.buffer(0) for pg in proj_all_main])
    outer_patches = geom_to_patches(outer_pg)
    if outer_patches:
      ax.add_collection(PatchCollection(outer_patches, facecolor="none", edgecolor="#111827", linewidths=1.10, zorder=3.6))
    xlim, ylim = pad_projected_bounds(outer_pg.bounds, arg1_target_aspect=1.58, arg2_pad_factor=1.18, arg3_min_span_km=360.0)
  else:
    xlim, ylim = (-1200.0, 1200.0), (-800.0, 800.0)

  ax.set_xlim(*xlim)
  ax.set_ylim(*ylim)
  ax.set_aspect("equal", adjustable="box")
  ax.set_xticks([])
  ax.set_yticks([])

  glats = [v for v in (5, 10, 15, 20, 25, 30, 35) if miny - 2 <= v <= maxy + 2]
  glons = [v for v in (-115, -110, -105, -100, -95, -90, -85, -80, -75, -70, -65, -60) if minx - 3 <= v <= maxx + 3]
  # Thin graticule on wide Mexico-to-Panama maps so grid stays clean
  if len(glons) > 7:
    glons = glons[::2]
  draw_graticule(ax, proj_main, xlim, ylim, glats, glons, (clip_bb[0], clip_bb[2]), (clip_bb[1], clip_bb[3]))

  # Dedicated Bermuda inset on Ch 10 & Ch 14 (placed over open Atlantic upper-right quadrant)
  if bm_feats:
    draw_bermuda_inset(
      ax, bm_feats, rgb_map, name_map, arg2_bm_land, legend_handles, seen_leg,
      arg7_inset_rect=[0.72, 0.65, 0.25, 0.30], arg8_title_fs=6.8,
    )

  # Settlement cloud + top 7 in-bounds callouts
  sett_path = os.path.join(ch_dir, f"{stem}_settlements.json")
  setts = json.load(open(sett_path, encoding="utf-8"))
  xs_s, ys_s = [], []
  for s in setts.values():
    lat, lon = float(s["coords"][0]), float(s["coords"][1])
    if bm_feats and lat > 30.0 and lon > -67.0:
      continue
    px, py = proj_main.fwd_pt(lon, lat)
    if xlim[0] <= px <= xlim[1] and ylim[0] <= py <= ylim[1]:
      xs_s.append(px)
      ys_s.append(py)
  if xs_s:
    n_pts = len(xs_s)
    pt_s = 0.70 if n_pts > 8000 else (1.8 if n_pts > 600 else 5.0)
    pt_a = 0.22 if n_pts > 8000 else (0.30 if n_pts > 600 else 0.42)
    ax.scatter(xs_s, ys_s, s=pt_s, c="#1e293b", alpha=pt_a, linewidths=0.0, zorder=4.8)

  top_items = [
    {"label": truncate_label(s["name"], 18), "lon": s["lon"], "lat": s["lat"]}
    for s in arg1_cache["settlement_stats"]["top_settlements"][:14]
    if not (bm_feats and s["lat"] > 30.0 and s["lon"] > -67.0)
  ]
  d0, d1 = arg0_ch["domain"]
  ax.set_title(f"{arg0_ch['title']} ({format_year_label(d0)}–{format_year_label(d1)})", fontsize=10.2, pad=8)

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
      fontsize=7.0,
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
  export_panel_crops(out_path, f"ch{idx:02d}_map", arg2_split_lr=False)


def render_trajectory_figure (arg0_ch, arg1_cache):
  stem = arg0_ch["stem"]
  idx = int(arg0_ch["index"])
  ch_dir = os.path.join(JAG_DIR, arg0_ch["group"], arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", f"{stem}_population_trajectory.png")

  dom_traj = arg1_cache["domain_trajectory"]
  yrs = sorted(int(k) for k in dom_traj.keys())
  tot_vals = [float(dom_traj[str(y)]) for y in yrs]
  subregs = arg1_cache["subregions"]
  last_yr = str(yrs[-1])

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.5), dpi=300, gridspec_kw={"width_ratios": [1.15, 1.0], "wspace": 0.46})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Thin markers when annual modern series has > 30 points
  mk_every = max(1, len(yrs) // 12)
  ax1.plot(yrs, tot_vals, marker="o", markevery=mk_every, linewidth=2.0, markersize=4.2, color="#1f77b4", label="Chapter total")
  ranked_sr = sorted(subregs, key=lambda r: -float(r["peak_pop"]))
  line_cols = ["#d97706", "#2a9d8f", "#9333ea", "#dc2626"]
  for idx_r, sr in enumerate(ranked_sr[:4]):
    sv = [float(sr["trajectory"].get(str(y), 0.0)) for y in yrs]
    ax1.plot(yrs, sv, marker="s", markevery=mk_every, linewidth=1.25, markersize=3.0, linestyle="--", color=line_cols[idx_r], label=truncate_label(sr["name"], 24))

  max_v = max(tot_vals) if tot_vals else 1.0
  ax1.set_ylim(0.0, max_v * 1.34)
  ax1.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, integer=True))
  ax1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: f"{int(abs(x))}BC" if x < 0 else f"{int(x)}"))
  ax1.tick_params(axis="x", labelsize=8.0)
  ax1.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  ax1.set_xlabel("Calendar year")
  ax1.set_ylabel("Population (inhabitants)")
  ax1.set_title("A. Population Trajectory by Sub-Region", fontsize=9.6, pad=6)
  # Compare left vs right half by geometric calendar-year midpoint so BC/AD sampling skew never misplaces legend
  x_mid = 0.5 * (yrs[0] + yrs[-1]) if len(yrs) >= 2 else 0.0
  left_vals = [v for y, v in zip(yrs, tot_vals) if y <= x_mid] or [tot_vals[0]]
  right_vals = [v for y, v in zip(yrs, tot_vals) if y > x_mid] or [tot_vals[-1]]
  leg_loc = "upper left" if max(left_vals) <= max(right_vals) else "upper right"
  ax1.legend(loc=leg_loc, fontsize=6.8, frameon=True, facecolor="white", framealpha=0.94)

  # Panel B: End-epoch population density (inhabitants / km²)
  dens_items = []
  for sr in subregs:
    dens_items.append((truncate_label(sr["name"], 24), float(sr["end_density_km2"]), mute_rgb_hex(sr["rgb"], 0, 0.25)))
  dens_items.sort(key=lambda x: x[1])
  show_d = dens_items[-10:]
  y_pos = np.arange(len(show_d))
  vals_d = [x[1] for x in show_d]
  ax2.barh(y_pos, vals_d, color=[x[2] for x in show_d], edgecolor="#334155", linewidth=0.55)
  ax2.set_yticks(y_pos)
  ax2.set_yticklabels([x[0] for x in show_d], fontsize=7.4)
  max_d = max(vals_d) if vals_d else 1.0
  ax2.set_xlim(0.0, max_d * 1.32)
  ax2.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5))
  ax2.xaxis.set_major_formatter(euro_tick_formatter(1 if max_d < 20 else 0))
  for yp, vd in zip(y_pos, vals_d):
    lbl_d = format_euro_number(vd, 2 if vd < 5 else (1 if vd < 50 else 0))
    ax2.text(vd + max_d * 0.025, yp, lbl_d, va="center", ha="left", fontsize=7.0, color="#1e293b")
  ax2.set_xlabel("Density (inhabitants / km²)")
  ax2.set_title(f"B. Sub-Regional Density in {format_year_label(yrs[-1])}", fontsize=9.6, pad=6)

  fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.14, wspace=0.50)
  save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})
  export_panel_crops(out_path, f"ch{idx:02d}_traj", arg2_split_lr=True)


def render_urban_hierarchy_figure (arg0_ch, arg1_cache):
  stem = arg0_ch["stem"]
  idx = int(arg0_ch["index"])
  ch_dir = os.path.join(JAG_DIR, arg0_ch["group"], arg0_ch["folder"])
  out_path = os.path.join(ch_dir, "figures", f"{stem}_urban_hierarchy.png")
  sett_path = os.path.join(ch_dir, f"{stem}_settlements.json")
  setts = json.load(open(sett_path, encoding="utf-8"))

  peaks = []
  for s in setts.values():
    pdict = s.get("population") or {}
    pos = [int(round(float(v))) for v in pdict.values() if 0.0 < float(v) < 25_000_000.0]
    if pos:
      peaks.append((s["name"], s.get("country", ""), max(pos)))
  peaks.sort(key=lambda x: -x[2])

  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.6), dpi=300, gridspec_kw={"width_ratios": [1.14, 1.0], "wspace": 0.42})
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Largest 12 recorded settlements
  top12 = list(reversed(peaks[:12]))
  y_pos = np.arange(len(top12))
  vals_p = [x[2] for x in top12]
  ax1.barh(y_pos, vals_p, color="#3b7ea1", edgecolor="#1e293b", linewidth=0.5)
  ax1.set_yticks(y_pos)
  ax1.set_yticklabels([truncate_label(x[0], 22) for x in top12], fontsize=7.5)
  max_p = max(vals_p) if vals_p else 1.0
  ax1.set_xlim(0.0, max_p * 1.30)
  ax1.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=4))
  ax1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: format_semantic_population(x) if x > 0 else "0"))
  for yp, vp in zip(y_pos, vals_p):
    ax1.text(vp + max_p * 0.022, yp, format_semantic_population(vp), va="center", ha="left", fontsize=7.0, color="#0f172a")
  ax1.set_xlabel("Peak settlement population")
  ax1.set_title("A. Largest Recorded Settlements", fontsize=9.6, pad=6)

  # Panel B: Rank-size distribution (strictly n >= 25)
  n_all = len(peaks)
  if n_all >= 25:
    ranks = np.arange(1, n_all + 1, dtype=np.float64)
    pops = np.array([x[2] for x in peaks], dtype=np.float64)
    n_fmt = f"{n_all:,}".replace(",", ".")
    ax2.loglog(ranks, pops, "o", markersize=2.8, alpha=0.55, color="#2563eb", label=f"Observed ({n_fmt} settlements)")
    n_fit = min(max(25, n_all // 2), 180)
    lx = np.log10(ranks[:n_fit])
    ly = np.log10(pops[:n_fit])
    slope, intercept = np.polyfit(lx, ly, 1)
    y_hat = slope * lx + intercept
    ss_res = float(np.sum((ly - y_hat) ** 2))
    ss_tot = float(np.sum((ly - np.mean(ly)) ** 2))
    r2 = max(0.0, 1.0 - ss_res / max(1e-12, ss_tot))
    ax2.loglog(
      ranks[:n_fit], 10.0 ** y_hat, "-", linewidth=1.65, color="#dc2626",
      label=rf"Power fit ($\alpha = {format_mathtext_euro(-slope, 2)}$, $R^2 = {format_mathtext_euro(r2, 2)}$)",
    )
    ax2.set_xlim(0.75, n_all * 1.6)
    ax2.set_ylim(max(20.0, float(pops.min()) * 0.55), float(pops.max()) * 2.5)
    apply_human_log_ticks(ax2, "both", arg2_semantic=True)
    ax2.set_xlabel("Settlement rank")
    ax2.set_ylabel("Peak population (inhabitants)")
    ax2.set_title("B. Settlement Rank-Size Distribution", fontsize=9.6, pad=6)
    ax2.legend(loc="lower left", fontsize=7.2, frameon=True, facecolor="white", framealpha=0.92)
  else:
    ax2.text(0.5, 0.5, "Insufficient sample for rank-size regression", ha="center", va="center", transform=ax2.transAxes)

  fig.subplots_adjust(left=0.19, right=0.97, top=0.88, bottom=0.14, wspace=0.40)
  save_viscount_figure(fig, out_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})
  export_panel_crops(out_path, f"ch{idx:02d}_urban", arg2_split_lr=True)


def main ():
  itin = load_json5_simple(ITIN_PATH)
  print("[1] Pre-projecting Bermuda inset basemap (Natural Earth 10m)...", flush=True)
  bm_land, _ = load_basemap_cache(PROJ_BERMUDA, (-65.8, 31.2, -63.8, 33.4), arg2_show_modern_borders=False, arg3_high_res=True)

  print(f"[2] Rendering 3 POLARIS-grade figures across all {len(itin['chapters'])} JAGUAR chapters...", flush=True)
  for ch in itin["chapters"]:
    stem = ch["stem"]
    ch_dir = os.path.join(JAG_DIR, ch["group"], ch["folder"])
    cache_path = os.path.join(ch_dir, f"{stem}_summary_cache.json")
    cache = json.load(open(cache_path, encoding="utf-8"))
    render_regional_map(ch, cache, bm_land)
    render_trajectory_figure(ch, cache)
    render_urban_hierarchy_figure(ch, cache)
    print(f"  [CH {ch['index']:02d}] {stem:35s}: 3 figures + crops saved", flush=True)

  print("[DONE] Generated all 42 JAGUAR chapter figures cleanly.", flush=True)


if __name__ == "__main__":
  main()
