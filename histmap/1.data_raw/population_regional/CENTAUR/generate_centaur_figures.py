# -*- coding: utf-8 -*-
"""Generate POLARIS-calibre Equal-Area vector maps, raster kriging mosaics and
zero-occlusion diagnostic figures for CENTAUR-II (5 root + 124 chapter PNGs).
"""

import json
import math
import pathlib
import re
import sys

import json5
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.colors import LogNorm
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch, Polygon as MplPolygon
from matplotlib.ticker import FuncFormatter
import numpy as np
from shapely.geometry import shape
from shapely.ops import unary_union

CENTAUR_DIR = pathlib.Path(__file__).resolve().parent
SHARED_DIR = CENTAUR_DIR.parent / "_shared"
GIS_DIR = CENTAUR_DIR / "_shared" / "_gis_cache"
SUBREG_DIR = GIS_DIR / "chapter_subregions"
ROOT_FIG_DIR = CENTAUR_DIR / "figures"

for p_str in (str(SHARED_DIR), str(GIS_DIR)):
  if p_str not in sys.path:
    sys.path.insert(0, p_str)

import centaur_map_helper as cmh
import viscount_plot_utils as vpu

PROJ_NC = cmh.AlbersEqualAreaConic(-146.0, 52.0, 68.0, 60.0, arg5_wrap_hi=135.0)
PROJ_US48 = cmh.AlbersEqualAreaConic(-95.0, 29.5, 45.5, 38.0)
CAN_WIDE_IDS = {
  "northern_canada", "prairies", "hudson_bay", "saint_lawrence", "maritimes",
  "colonial_canada_to_1763", "colonial_canada_to_1867", "canada_post_confederation"
}
PALETTE = [
  "#2b5c8f", "#c05246", "#3d8a5a", "#85529e", "#c9842c",
  "#4784b3", "#a43f37", "#2d9281", "#784c8f", "#b05a28",
  "#5294c4", "#cf5d4e", "#4da672", "#9b6ab5", "#c4a337"
]

MOD_META = {
  "northern_cascadia_and_alaska": ("Northern Cascadia and Alaska", 1500),
  "northern_canada": ("Northern Canada, Boreal Shield and Greenland", 1500),
  "prairies": ("Canadian Prairies", 1500),
  "hudson_bay": ("Hudson Bay and James Bay Lowlands", 1500),
  "saint_lawrence": ("Saint Lawrence River Basin", 1500),
  "maritimes": ("Atlantic Maritimes and Newfoundland", 1500),
  "upper_colorado": ("Upper Colorado Basin (HU 14)", 1100),
  "extreme_northern_plains": ("Extreme Northern Plains", 1100),
  "northern_plains": ("Northern Plains and Upper Missouri", 1100),
  "arizona": ("Arizona and Lower Colorado (HU 15)", 1100),
  "great_basin": ("Great Basin (HU 16)", 1500),
  "upper_mississippi": ("Upper Mississippi Basin (HU 07)", 1150),
  "rio_grande": ("Rio Grande Basin (HU 13)", 1400),
  "cumberland": ("Cumberland River Basin", 1200),
  "southeast": ("Southeast Atlantic and Gulf (HU 03 and 06)", 1250),
  "lower_mississippi": ("Lower Mississippi Valley (HU 08)", 1250),
  "southern_plains": ("Southern Plains and Texas Gulf (HU 11 and 12)", 1500),
  "ohio_river": ("Ohio River Basin (HU 05)", 1250),
  "new_england": ("New England (HU 01)", 1500),
  "central_plains": ("Central Plains (HU 10)", 1500),
  "mid_atlantic": ("Mid-Atlantic Chesapeake and Delaware (HU 02)", 1500),
  "great_lakes": ("Great Lakes Basin (HU 04)", 1500),
  "california": ("California (HU 18)", 1500),
  "northwest": ("Pacific Northwest Columbia Basin (HU 17)", 1500),
  "hawaii_and_american_polynesia": ("Hawai'i and American Polynesia", 1898),
  "colonial_america_to_1754": ("Colonial America to 1754AD", 1754),
  "colonial_america_to_1783": ("Colonial America to 1783AD", 1783),
  "colonial_canada_to_1763": ("Colonial Canada to 1763AD", 1763),
  "colonial_canada_to_1867": ("Colonial Canada to 1867AD", 1867),
  "canada_post_confederation": ("Canada Post-Confederation", 1890),
  "united_states_post_independence": ("United States Post-Independence", 1890)
}

KELLY_HUC_ORDER = [
  "upper_colorado", "extreme_northern_plains", "northern_plains", "arizona",
  "great_basin", "upper_mississippi", "rio_grande", "cumberland",
  "southeast", "lower_mississippi", "southern_plains", "ohio_river",
  "new_england", "central_plains", "mid_atlantic", "great_lakes",
  "california", "northwest"
]

US_DIVISIONS = [
  ("New England", "#7fa8c9", {"usa_connecticut", "usa_maine", "usa_massachusetts", "usa_new_hampshire", "usa_rhode_island", "usa_vermont"}),
  ("Mid-Atlantic", "#95b89a", {"usa_new_jersey", "usa_new_york", "usa_pennsylvania"}),
  ("East North Central", "#d4b483", {"usa_illinois", "usa_indiana", "usa_michigan", "usa_ohio", "usa_wisconsin"}),
  ("West North Central", "#c29bb8", {"usa_iowa", "usa_kansas", "usa_minnesota", "usa_missouri", "usa_nebraska", "usa_north_dakota", "usa_south_dakota"}),
  ("South Atlantic and DC", "#d6948a", {"usa_delaware", "usa_district_of_columbia", "usa_florida", "usa_georgia", "usa_maryland", "usa_north_carolina", "usa_south_carolina", "usa_virginia", "usa_west_virginia"}),
  ("East South Central", "#8ebfb5", {"usa_alabama", "usa_kentucky", "usa_mississippi", "usa_tennessee"}),
  ("West South Central", "#c9a87a", {"usa_arkansas", "usa_louisiana", "usa_oklahoma", "usa_texas"}),
  ("Mountain States", "#b3a4c7", {"usa_arizona", "usa_colorado", "usa_idaho", "usa_montana", "usa_nevada", "usa_new_mexico", "usa_utah", "usa_wyoming"}),
  ("Pacific Coast", "#85adc4", {"usa_california", "usa_oregon", "usa_washington"}),
  ("Alaska", "#9bbd8e", {"usa_alaska"}),
  ("Hawai'i, Am. Samoa and Bermuda", "#c98f88", {"usa_hawaii", "usa_american_samoa", "usa_bermuda"})
]


def _fmt_yr (arg0_yr):
  """Formats integer year concisely in British historical convention."""
  yi = int(arg0_yr)
  if yi < 0:
    return f"{abs(yi)}BC"
  return f"{yi}AD"


def _fmt_yr_ticks (arg0_ax, arg1_years):
  """Sets crisp non-overlapping BC/AD tick labels spaced by calendar year."""
  ys = sorted(set(int(y) for y in arg1_years))
  if not ys:
    return
  y_min, y_max = ys[0], ys[-1]
  span = max(1, y_max - y_min)
  if len(ys) <= 6 and all((b - a) >= 0.14 * span for a, b in zip(ys, ys[1:])):
    chosen = ys
  else:
    chosen = [y_min, y_max]
    for frac in (0.25, 0.50, 0.75):
      raw_t = y_min + frac * span
      step = 500 if span >= 3000 else (100 if span >= 600 else (50 if span >= 250 else 25))
      cand = int(round(raw_t / step) * step)
      if min(abs(cand - c) for c in chosen) >= 0.17 * span:
        chosen.append(cand)
    chosen = sorted(set(chosen))
  arg0_ax.set_xticks(chosen)
  arg0_ax.set_xticklabels([_fmt_yr(y) for y in chosen], fontsize=7.5)


def _clean_sub_label (arg0_name, arg1_max_len=34):
  """Formats sub-region or town names without harsh mid-word chopping."""
  txt = re.sub(r"^\d+\.\s*", "", str(arg0_name or "")).strip()
  txt = re.sub(r"\s*\([^)]*\)", "", txt).strip()
  txt = re.sub(r"\s+", " ", re.sub(r"\s*/\s*", " and ", txt)).strip()
  if len(txt) <= arg1_max_len:
    return txt
  words = txt.split()
  out, cur = [], 0
  for w in words:
    if cur + len(w) + (1 if out else 0) > arg1_max_len - 3:
      break
    out.append(w)
    cur += len(w) + (1 if out else 0)
  return " ".join(out) + "..." if out else txt[:arg1_max_len - 3] + "..."


def _matern32_gamma (arg0_u, arg1_c0, arg2_c1, arg3_c2, arg4_tau1, arg5_tau2):
  """Evaluates normalized two-component Matern 3/2 semivariogram."""
  r3 = math.sqrt(3.0)
  u = np.maximum(np.asarray(arg0_u, dtype=float), 0.0)
  a1 = r3 * u / max(float(arg4_tau1), 1e-6)
  a2 = r3 * u / max(float(arg5_tau2), 1e-6)
  corr = float(arg2_c1) * (1.0 + a1) * np.exp(-a1) + float(arg3_c2) * (1.0 + a2) * np.exp(-a2)
  return np.where(u <= 1e-12, 0.0, float(arg1_c0) + (1.0 - float(arg1_c0)) * np.maximum(0.0, 1.0 - corr))


def _load_modules ():
  """Loads all 31 CENTAUR module manifests, JSON5 series, gazetteers and vectors."""
  cfg = json5.loads((CENTAUR_DIR / "centaur_areal_masks.json5").read_text(encoding="utf-8"))
  mods = list(cfg.get("specialist_masks", [])) + list(cfg.get("national_epoch_masks", []))
  out = []
  for m in mods:
    mid = m["id"]
    j5_rel = pathlib.Path(m["json5_path"])
    j5_abs = CENTAUR_DIR.parents[3] / j5_rel if j5_rel.parts[0] == "histmap" else CENTAUR_DIR / j5_rel
    ch_dir = j5_abs.parent
    set_p = ch_dir / f"{mid}_settlements.json"
    gj_p = SUBREG_DIR / f"{mid}_subregions.geojson"
    title_s, border_yr = MOD_META.get(mid, (mid, 1500))
    out.append({
      "id": mid,
      "title": title_s,
      "border_year": border_yr,
      "dir": ch_dir,
      "fig_dir": ch_dir / "figures",
      "data": json5.loads(j5_abs.read_text(encoding="utf-8")),
      "settlements": json.loads(set_p.read_text(encoding="utf-8")) if set_p.exists() else [],
      "geojson": json.loads(gj_p.read_text(encoding="utf-8")) if gj_p.exists() else {"features": []}
    })
  return out


def _build_vector_patches (arg0_features, arg1_proj, arg2_seg=0.22, arg3_color_fn=None):
  """Projects pure vector GeoJSON polygons into muted POLARIS PatchCollections and union outline."""
  patches_list, cols_list, raw_geoms = [], [], []
  xs_all, ys_all = [], []
  for idx, feat in enumerate(arg0_features):
    geom = feat.get("geometry")
    if not geom:
      continue
    g_raw = shape(geom)
    raw_geoms.append(g_raw)
    pg = cmh.clip_and_project(g_raw, arg1_proj, arg2_seg)
    ps = cmh.geom_to_patches(pg)
    if not ps:
      continue
    if arg3_color_fn is not None:
      c_hex = arg3_color_fn(feat, idx)
    else:
      c_hex = cmh.mute_rgb_hex(feat.get("properties", {}).get("colour"), idx, arg2_blend=0.45)
    for p in ps:
      xy = p.get_xy()
      if len(xy) >= 3:
        xs_all.extend([float(xy[:, 0].min()), float(xy[:, 0].max())])
        ys_all.extend([float(xy[:, 1].min()), float(xy[:, 1].max())])
        patches_list.append(MplPolygon(xy, closed=True))
        cols_list.append(c_hex)
  if not patches_list:
    return None, None, None
  pc = PatchCollection(patches_list, facecolor=cols_list, edgecolor="#334155", linewidths=0.38, alpha=0.80, zorder=2.5)
  env_pc = None
  try:
    env_g = cmh.clip_and_project(unary_union([g.buffer(0) for g in raw_geoms]), arg1_proj, arg2_seg)
    eps = cmh.geom_to_patches(env_g)
    if eps:
      env_pc = PatchCollection(eps, facecolor="none", edgecolor="#111827", linewidths=0.85, zorder=3.8)
  except Exception:
    env_pc = None
  bounds = (min(xs_all), min(ys_all), max(xs_all), max(ys_all))
  return pc, env_pc, bounds


def _pad_aspect (arg0_bounds, arg1_aspect=1.48, arg2_min_span=320.0):
  """Symmetrically pads projected bounds to eliminate distortion or excessive ocean."""
  x0, y0, x1, y1 = arg0_bounds
  cx = 0.5 * (x0 + x1)
  cy = 0.5 * (y0 + y1)
  w = max((x1 - x0) * 1.16, arg2_min_span)
  h = max((y1 - y0) * 1.16, arg2_min_span / arg1_aspect)
  if w / h > arg1_aspect:
    h = w / arg1_aspect
  else:
    w = h * arg1_aspect
  return (cx - 0.5 * w, cx + 0.5 * w), (cy - 0.5 * h, cy + 0.5 * h)


def _rank_setts_in_bounds (arg0_setts, arg1_proj, arg2_xlim, arg3_ylim):
  """Extracts ranked settlements inside projected axis limits."""
  x0, x1 = arg2_xlim
  y0, y1 = arg3_ylim
  out = []
  items = arg0_setts.values() if isinstance(arg0_setts, dict) else arg0_setts
  for s in items:
    coords = s.get("coords")
    if not isinstance(coords, list) or len(coords) < 2:
      continue
    lat, lon = float(coords[0]), float(coords[1])
    px, py = arg1_proj.fwd_pt(lon, lat)
    if not (x0 <= px <= x1 and y0 <= py <= y1):
      continue
    pk = max((float(v) for v in (s.get("population") or {}).values()), default=0.0)
    ct_s = str(s.get("country", "")).strip()
    short = re.sub(r"-" + re.escape(ct_s) + r"$", "", str(s.get("name", ""))).strip() if ct_s else str(s.get("name", "")).strip()
    if len(short) > 20:
      short = short[:17] + "..."
    lbl = f"{short} ({vpu.format_semantic_population(pk)})"
    out.append((pk, lbl, lon, lat, px, py))
  out.sort(key=lambda t: (-t[0], t[1]))
  return out


def _draw_panel_map (arg0_fig, arg1_ax, arg2_proj, arg3_feats, arg4_border_yr, arg5_xlim, arg6_ylim, arg7_setts=None, arg8_max_lbl=6, arg9_color_fn=None, arg10_is_dense=False, arg11_grat_labels=True):
  """Renders vector basemap, polygons, .naissance borders, graticule and callouts."""
  cmh.draw_basemap(arg1_ax, arg2_proj)
  pc, env_pc, _ = _build_vector_patches(arg3_feats, arg2_proj, arg3_color_fn=arg9_color_fn)
  if pc is not None:
    arg1_ax.add_collection(pc)
  if env_pc is not None:
    arg1_ax.add_collection(env_pc)
  if arg4_border_yr >= 1000:
    cmh.draw_historical_borders(arg1_ax, arg2_proj, arg4_border_yr, arg4_color="#1f2937")
  arg1_ax.set_xlim(*arg5_xlim)
  arg1_ax.set_ylim(*arg6_ylim)
  arg1_ax.set_aspect("equal", adjustable="box")
  arg1_ax.set_xticks([])
  arg1_ax.set_yticks([])
  cmh.draw_inline_graticule(arg1_ax, arg2_proj, arg5_xlim, arg6_ylim, [20, 30, 40, 50, 60, 70], [-170, -155, -140, -120, -100, -80, -60, -40], arg6_show_labels=arg11_grat_labels)
  vpu.apply_viscount_style(arg1_ax)

  if arg7_setts:
    ranked = _rank_setts_in_bounds(arg7_setts, arg2_proj, arg5_xlim, arg6_ylim)
    if ranked:
      pt_sz = 0.7 if arg10_is_dense else 8.5
      pt_al = 0.14 if arg10_is_dense else 0.76
      arg1_ax.scatter(
        [r[4] for r in ranked], [r[5] for r in ranked],
        s=pt_sz, c="#1e293b", edgecolors="none" if arg10_is_dense else "white",
        linewidths=0.0 if arg10_is_dense else 0.35, alpha=pt_al, zorder=6.2
      )
      items = [(r[1], r[2], r[3]) for r in ranked[:40]]
      cmh.place_bbox_callouts(
        arg0_fig, arg1_ax, items, arg2_proj, arg5_xlim, arg6_ylim,
        arg6_max_labels=arg8_max_lbl, arg7_min_sep_px=42.0, arg8_fontsize=6.4
      )


def render_root_fig1 (arg0_mods):
  """Generates Root Figure 1: four-epoch Equal-Area CENTAUR-II coverage."""
  plt.rcdefaults()
  plt.style.use("default")
  by_id = {m["id"]: m for m in arg0_mods}
  fig, axes = plt.subplots(2, 2, figsize=(15.4, 10.8), dpi=300)
  plt.subplots_adjust(left=0.02, right=0.98, top=0.91, bottom=0.10, wspace=0.04, hspace=0.14)

  xlim_na = (-4550.0, 3250.0)
  ylim_na = (-2100.0, 3950.0)
  groups_cfg = [
    ("A. Pre-Columbian Ecological Zones and US Watersheds (10000BC-1600AD)", 1500, [
      ("Canada, Alaska and Greenland (6 modules)", "#7097ba", ["northern_cascadia_and_alaska", "northern_canada", "prairies", "hudson_bay", "saint_lawrence", "maritimes"]),
      ("Western and Plains US HUs (7 units)", "#d4a86e", ["upper_colorado", "extreme_northern_plains", "northern_plains", "arizona", "great_basin", "central_plains", "southern_plains"]),
      ("Eastern Woodlands and Mississippi HUs (9 units)", "#7db38f", ["upper_mississippi", "rio_grande", "cumberland", "southeast", "lower_mississippi", "ohio_river", "new_england", "mid_atlantic", "great_lakes"]),
      ("Pacific Coast and Polynesia (3 modules)", "#c97e79", ["california", "northwest", "hawaii_and_american_polynesia"])
    ], True),
    ("B. Early Colonial Contact and Indigenous Continuity (1500AD-1763AD)", 1754, [
      ("Colonial America to 1754AD", "#7aa2c4", ["colonial_america_to_1754"]),
      ("Colonial Canada to 1763AD", "#cf887e", ["colonial_canada_to_1763"])
    ], False),
    ("C. Late Colonial and Confederation Transitions (1754AD-1867AD)", 1815, [
      ("Colonial America to 1783AD", "#668db3", ["colonial_america_to_1783"]),
      ("Colonial Canada to 1867AD", "#c7966f", ["colonial_canada_to_1867"])
    ], False),
    ("D. Post-Independence States and Territories (1783AD-2026AD)", 1890, [
      ("United States Post-1783AD", "#7aa2c4", ["united_states_post_independence"]),
      ("Canada, Greenland and St-Pierre Post-1867AD", "#cf887e", ["canada_post_confederation"])
    ], True)
  ]

  hi_feats = by_id["hawaii_and_american_polynesia"]["geojson"].get("features", []) if "hawaii_and_american_polynesia" in by_id else []
  for idx, (ptitle, byear, grp_list, has_insets) in enumerate(groups_cfg):
    ax = axes[idx // 2, idx % 2]
    cmh.draw_basemap(ax, cmh.PROJ_NA)
    leg_h = []
    for glbl, ghex, gids in grp_list:
      ps_g = []
      for gid in gids:
        if gid in by_id:
          for f in by_id[gid]["geojson"].get("features", []):
            if f.get("geometry"):
              ps_g.extend(cmh.geom_to_patches(cmh.clip_and_project(shape(f["geometry"]), cmh.PROJ_NA, 0.35)))
      if ps_g:
        ax.add_collection(PatchCollection([MplPolygon(p.get_xy(), closed=True) for p in ps_g], facecolor=ghex, edgecolor="#334155", linewidths=0.25, alpha=0.80, zorder=2.5))
      leg_h.append(Patch(facecolor=ghex, edgecolor="#334155", linewidth=0.45, label=glbl))
    cmh.draw_historical_borders(ax, cmh.PROJ_NA, byear, arg4_color="#111827")
    ax.set_xlim(*xlim_na)
    ax.set_ylim(*ylim_na)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    if has_insets and hi_feats:
      ax_hi = ax.inset_axes([0.02, 0.03, 0.21, 0.20])
      _draw_panel_map(fig, ax_hi, cmh.PROJ_HI, hi_feats, byear, (-365.0, 320.0), (-215.0, 260.0), arg11_grat_labels=False)
      ax_hi.text(0.05, 0.90, "Hawai'i", transform=ax_hi.transAxes, fontsize=6.0, va="top", ha="left", zorder=11, bbox=dict(boxstyle="round,pad=0.14", facecolor="white", edgecolor="#94a3b8", linewidth=0.45, alpha=0.92))
      ax_as = ax.inset_axes([0.245, 0.03, 0.16, 0.20])
      _draw_panel_map(fig, ax_as, cmh.PROJ_AS, hi_feats, byear, (-125.0, 175.0), (-80.0, 125.0), arg11_grat_labels=False)
      ax_as.text(0.05, 0.90, "Am. Samoa", transform=ax_as.transAxes, fontsize=6.0, va="top", ha="left", zorder=11, bbox=dict(boxstyle="round,pad=0.14", facecolor="white", edgecolor="#94a3b8", linewidth=0.45, alpha=0.92))

    ax.legend(handles=leg_h, loc="lower right", fontsize=6.2, frameon=True, facecolor="white", edgecolor="#94a3b8", framealpha=0.94)
    cmh.draw_inline_graticule(ax, cmh.PROJ_NA, xlim_na, ylim_na, [25, 45, 65], [-160, -120, -80, -40])
    vpu.apply_viscount_style(ax)
    ax.set_title(ptitle, fontsize=9.0, pad=5)

  fig.suptitle("CENTAUR-II Spatial Domains and Historical Boundaries (10000BC-2026AD)", fontsize=12.0, y=0.965)
  cmh.verify_zero_text_overlaps(fig, "root_fig1")
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig1_centaur_macro_zones.png", 300)
  plt.close(fig)


def render_root_fig2 (arg0_mods):
  """Generates Root Figure 2: Holocene relative intensity across 18 US HUs."""
  plt.rcdefaults()
  plt.style.use("default")
  by_id = {m["id"]: m for m in arg0_mods}
  hucs = [mid for mid in KELLY_HUC_ORDER if mid in by_id]
  bench_yrs = [-10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000, 0, 400, 800, 1000, 1100, 1200, 1300, 1400, 1500, 1600]
  mat = np.zeros((len(hucs), len(bench_yrs)), dtype=float)
  y_lbls = []
  for r_i, mid in enumerate(hucs):
    hl = by_id[mid]["data"]["summary"]["headline_population_by_benchmark"]
    ser = np.array([float(hl.get(str(y), 0.0)) for y in bench_yrs], dtype=float)
    mat[r_i, :] = ser / max(float(np.max(ser)), 1.0)
    y_lbls.append(MOD_META[mid][0])

  fig, ax = plt.subplots(figsize=(12.2, 6.8), dpi=300)
  plt.subplots_adjust(left=0.27, right=0.90, top=0.90, bottom=0.14)
  im = ax.imshow(mat, aspect="auto", cmap="YlOrRd", vmin=0.0, vmax=1.0, interpolation="nearest")
  ax.set_yticks(np.arange(len(y_lbls)))
  ax.set_yticklabels(y_lbls, fontsize=7.6)
  ax.set_xticks(np.arange(len(bench_yrs)))
  ax.set_xticklabels([_fmt_yr(y) for y in bench_yrs], fontsize=7.4, rotation=32, ha="right")
  ax.set_xlabel("Calendar Year", fontsize=8.8)
  ax.set_title("Pre-Columbian United States: Relative Demographic Intensity Across 18 Hydrological Units", fontsize=10.5, pad=8)
  cbar = fig.colorbar(im, ax=ax, fraction=0.032, pad=0.025)
  cbar.set_ticks([0.0, 0.25, 0.5, 0.75, 1.0])
  cbar.set_ticklabels(["0", "0,25", "0,50", "0,75", "1,00"])
  cbar.set_label("Share of Unit Pre-Contact Peak", fontsize=8.5)
  vpu.apply_viscount_style(ax)
  cmh.verify_zero_text_overlaps(fig, "root_fig2")
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig2_precolumbian_kelly_hucs.png", 300)
  plt.close(fig)


def render_root_fig3 (arg0_mods):
  """Generates Root Figure 3: two-panel colonial demographic transition."""
  plt.rcdefaults()
  plt.style.use("default")
  by_id = {m["id"]: m for m in arg0_mods}
  fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.2, 5.6), dpi=300)
  plt.subplots_adjust(left=0.07, right=0.97, top=0.86, bottom=0.14, wspace=0.22)

  specs = [
    ("colonial_america_to_1754", "Colonial America to 1754AD", "#2b5c8f"),
    ("colonial_america_to_1783", "Colonial America to 1783AD", "#c9842c"),
    ("colonial_canada_to_1763", "Colonial Canada to 1763AD", "#3d8a5a"),
    ("colonial_canada_to_1867", "Colonial Canada to 1867AD", "#c05246")
  ]
  for mid, lbl, col in specs:
    hl = by_id[mid]["data"]["summary"]["headline_population_by_benchmark"]
    ys = sorted(int(k) for k in hl.keys())
    vs = [float(hl[str(y)]) for y in ys]
    axL.plot(ys, vs, color=col, linewidth=2.1, label=f"{lbl} ({vpu.format_semantic_population(vs[-1])})")
  axL.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  _fmt_yr_ticks(axL, [1500, 1590, 1680, 1775, 1867])
  axL.set_xlim(1495, 1872)
  axL.set_xlabel("Calendar Year", fontsize=8.5)
  axL.set_ylabel("Total Population", fontsize=8.5)
  axL.set_title("A. Aggregate Continental Trajectories (1500AD-1867AD)", fontsize=9.4, pad=6)
  axL.legend(loc="upper left", fontsize=7.0, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axL)
  axL.grid(True, linestyle=":", alpha=0.45)

  def _sum_dom (arg0_regs, arg1_yr):
    tot_d = 0.0
    for rv in arg0_regs.values():
      pm = rv.get("population", {})
      ks = sorted(int(k) for k in pm.keys())
      if ks and ks[0] <= arg1_yr <= ks[-1]:
        tot_d += float(np.interp(arg1_yr, ks, [float(pm[str(k)]) for k in ks]))
    return tot_d

  ca1 = by_id["colonial_america_to_1754"]["data"]["regions"]
  ca2 = by_id["colonial_america_to_1783"]["data"]["regions"]
  cc1 = by_id["colonial_canada_to_1763"]["data"]["regions"]
  cc2 = by_id["colonial_canada_to_1867"]["data"]["regions"]
  b_yrs = [1500, 1680, 1754, 1783, 1867]
  us_vals = [_sum_dom(ca1, 1500), _sum_dom(ca1, 1680), _sum_dom(ca1, 1754), _sum_dom(ca2, 1783), 0.0]
  can_vals = [_sum_dom(cc1, 1500), _sum_dom(cc1, 1680), _sum_dom(cc1, 1754), _sum_dom(cc2, 1783), _sum_dom(cc2, 1867)]
  x_i = np.arange(len(b_yrs))
  bw = 0.36
  axR.bar(x_i - 0.5 * bw, us_vals, width=bw, color="#2b5c8f", alpha=0.86, label="Colonial America Domain")
  axR.bar(x_i + 0.5 * bw, can_vals, width=bw, color="#c05246", alpha=0.86, label="Colonial Canada Domain")
  for i_k in range(len(b_yrs)):
    if us_vals[i_k] > 0:
      axR.text(x_i[i_k] - 0.5 * bw, us_vals[i_k] * 1.03, vpu.format_semantic_population(us_vals[i_k]), ha="center", va="bottom", fontsize=6.8)
    if can_vals[i_k] > 0:
      axR.text(x_i[i_k] + 0.5 * bw, can_vals[i_k] * 1.03, vpu.format_semantic_population(can_vals[i_k]), ha="center", va="bottom", fontsize=6.8)
  axR.set_xticks(x_i)
  axR.set_xticklabels([_fmt_yr(y) for y in b_yrs], fontsize=7.6)
  axR.set_ylim(0, max(max(us_vals), max(can_vals)) * 1.18)
  axR.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  axR.set_xlabel("Historical Benchmark", fontsize=8.5)
  axR.set_ylabel("Domain Population", fontsize=8.5)
  axR.set_title("B. Benchmark Domain Totals at Boundary Transfers", fontsize=9.4, pad=6)
  axR.legend(loc="upper left", fontsize=7.0, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axR)
  axR.grid(True, linestyle=":", alpha=0.45)

  fig.suptitle("Colonial America and Canada: Indigenous Continuity and Settler Growth (1500AD-1867AD)", fontsize=11.0, y=0.97)
  cmh.verify_zero_text_overlaps(fig, "root_fig3")
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig3_colonial_transition_trajectories.png", 300)
  plt.close(fig)


def render_root_fig4 (arg0_mods):
  """Generates Root Figure 4: modern US and Canada growth trajectories."""
  plt.rcdefaults()
  plt.style.use("default")
  by_id = {m["id"]: m for m in arg0_mods}
  fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.0, 5.4), dpi=300)
  plt.subplots_adjust(left=0.07, right=0.97, top=0.86, bottom=0.14, wspace=0.22)

  us_hl = by_id["united_states_post_independence"]["data"]["summary"]["headline_population_by_benchmark"]
  ca_hl = by_id["canada_post_confederation"]["data"]["summary"]["headline_population_by_benchmark"]
  us_y = sorted(int(k) for k in us_hl.keys())
  ca_y = sorted(int(k) for k in ca_hl.keys())
  us_v = [float(us_hl[str(y)]) for y in us_y]
  ca_v = [float(ca_hl[str(y)]) for y in ca_y]

  axL.plot(us_y, us_v, color="#2b5c8f", linewidth=2.2, label=f"United States ({vpu.format_semantic_population(us_v[0])} to {vpu.format_semantic_population(us_v[-1])})")
  axL.plot(ca_y, ca_v, color="#c05246", linewidth=2.0, label=f"Canada and Greenland ({vpu.format_semantic_population(ca_v[0])} to {vpu.format_semantic_population(ca_v[-1])})")
  axL.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  _fmt_yr_ticks(axL, [1783, 1844, 1905, 1966, 2026])
  axL.set_xlabel("Calendar Year", fontsize=8.5)
  axL.set_ylabel("Total Population", fontsize=8.5)
  axL.set_title("A. United States and Canada Totals (Linear Scale)", fontsize=9.4, pad=6)
  axL.legend(loc="upper left", fontsize=7.0, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axL)
  axL.grid(True, linestyle=":", alpha=0.45)

  ca_regs = by_id["canada_post_confederation"]["data"]["regions"]
  top_ca = sorted(ca_regs.items(), key=lambda kv: max((float(v) for v in kv[1]["population"].values()), default=0.0), reverse=True)[:6]
  for r_i, (rk, rv) in enumerate(top_ca):
    pmap = rv["population"]
    ry = sorted(int(k) for k in pmap.keys())
    axR.plot(ry, [float(pmap[str(y)]) for y in ry], linewidth=1.7, color=PALETTE[r_i % len(PALETTE)], label=_clean_sub_label(rv["name"], 26))
  axR.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  _fmt_yr_ticks(axR, [1867, 1907, 1947, 1987, 2026])
  axR.set_xlabel("Calendar Year", fontsize=8.5)
  axR.set_ylabel("Provincial Population", fontsize=8.5)
  axR.set_title("B. Leading Canadian Provinces After Confederation", fontsize=9.4, pad=6)
  axR.legend(loc="upper left", fontsize=6.9, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axR)
  axR.grid(True, linestyle=":", alpha=0.45)

  fig.suptitle("Modern United States, Canada and Greenland Growth (1783AD-2026AD)", fontsize=11.0, y=0.97)
  cmh.verify_zero_text_overlaps(fig, "root_fig4")
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig4_modern_us_canada_growth.png", 300)
  plt.close(fig)


def render_root_fig5 ():
  """Generates Root Figure 5: 4-panel POLARIS-style kriging mosaic and empirical variograms."""
  plt.rcdefaults()
  plt.style.use("default")
  fig, axes = plt.subplots(2, 2, figsize=(15.2, 10.6), dpi=300)
  plt.subplots_adjust(left=0.03, right=0.97, top=0.91, bottom=0.07, wspace=0.11, hspace=0.22)
  xlim_na = (-4450.0, 3250.0)
  ylim_na = (-2050.0, 3900.0)

  # Panel A: Voronoi catchments & frontier buffers
  axA = axes[0, 0]
  cmh.draw_basemap(axA, cmh.PROJ_NA)
  gj_p = CENTAUR_DIR / "_shared/sites_northern_america/geojson/00_all_periods.geojson"
  gj = json.loads(gj_p.read_text(encoding="utf-8"))
  dom_x, dom_y, buf_x, buf_y = [], [], [], []
  for f in gj.get("features", []):
    g = f.get("geometry")
    if not g:
      continue
    rep = shape(g).representative_point()
    px, py = cmh.PROJ_NA.fwd_pt(rep.x, rep.y)
    if xlim_na[0] <= px <= xlim_na[1] and ylim_na[0] <= py <= ylim_na[1]:
      if f.get("properties", {}).get("is_frontier_buffer"):
        buf_x.append(px)
        buf_y.append(py)
      else:
        dom_x.append(px)
        dom_y.append(py)
  if dom_x:
    axA.scatter(dom_x, dom_y, s=2.2, c="#2b5c8f", alpha=0.65, edgecolors="none", zorder=5.0, label=f"Domestic catchments (n={vpu.format_euro_number(len(dom_x), 0)})")
  if buf_x:
    axA.scatter(buf_x, buf_y, s=4.8, c="#c9842c", alpha=0.85, edgecolors="none", zorder=5.5, label=f"Cross-frontier buffers (n={vpu.format_euro_number(len(buf_x), 0)})")
  cmh.draw_historical_borders(axA, cmh.PROJ_NA, 1500, arg4_color="#334155")
  axA.set_xlim(*xlim_na)
  axA.set_ylim(*ylim_na)
  axA.set_aspect("equal", adjustable="box")
  axA.set_xticks([])
  axA.set_yticks([])
  axA.legend(loc="lower left", fontsize=6.6, frameon=True, facecolor="white", framealpha=0.97)
  cmh.draw_inline_graticule(axA, cmh.PROJ_NA, xlim_na, ylim_na, [25, 45, 65], [-160, -120, -40])
  vpu.apply_viscount_style(axA)
  axA.set_title("A. Multi-Registry Voronoi Catchments and Frontier Conditioning Belt", fontsize=9.0, pad=5)

  # Panel B: Pre-Columbian Kriged Intensity Raster (1200AD, Horizon 08)
  axB = axes[0, 1]
  cmh.draw_basemap(axB, cmh.PROJ_NA, arg3_dark=True)
  krig_p = CENTAUR_DIR / "_shared/sites_northern_america/1.kriged_rasters/08_middle_mississippian_pueblo_iii_h8.png"
  if krig_p.exists():
    rk_f32 = cmh.load_f32_raster(krig_p)
    grid_k = cmh.reproject_f32_raster(rk_f32, cmh.PROJ_NA, xlim_na, ylim_na, arg4_width_px=960, arg5_height_px=760)
    pos_k = grid_k[grid_k > 0.0]
    hi_k = max(0.5, float(np.percentile(pos_k, 99.6))) if pos_k.size > 0 else 12.0
    lo_k = max(1e-4, hi_k * 5e-4)
    grid_k_m = np.ma.masked_where(grid_k <= 0.0, np.clip(grid_k, lo_k, hi_k))
    imB = axB.imshow(grid_k_m, extent=[xlim_na[0], xlim_na[1], ylim_na[0], ylim_na[1]], origin="upper", cmap="magma", norm=LogNorm(vmin=lo_k, vmax=hi_k), alpha=0.92, zorder=3.5)
    caxB = axB.inset_axes([0.04, 0.075, 0.36, 0.042])
    cbB = fig.colorbar(imB, cax=caxB, orientation="horizontal", format=vpu.euro_log_formatter(False))
    vpu.apply_human_colorbar_ticks(cbB, False)
    cbB.outline.set_edgecolor("#e2e8f0")
    cbB.ax.tick_params(labelsize=6.0, colors="white")
    caxB.set_title("Kriged Intensity (1200AD)", fontsize=6.4, pad=2, color="white")
  cmh.draw_historical_borders(axB, cmh.PROJ_NA, 1250, arg4_color="#94a3b8")
  axB.set_xlim(*xlim_na)
  axB.set_ylim(*ylim_na)
  axB.set_aspect("equal", adjustable="box")
  axB.set_xticks([])
  axB.set_yticks([])
  cmh.draw_inline_graticule(axB, cmh.PROJ_NA, xlim_na, ylim_na, [25, 45, 65], [-160, -120, -80, -40])
  cmh.place_bbox_callouts(
    fig, axB,
    [("Cahokia", -90.06, 38.66), ("Moundville", -87.63, 33.00), ("Chaco Canyon", -107.96, 36.06), ("Salish Sea", -123.1, 49.2), ("San Francisco Bay", -122.3, 37.8)],
    cmh.PROJ_NA, xlim_na, ylim_na, arg6_max_labels=5, arg7_min_sep_px=45.0, arg8_fontsize=6.0
  )
  vpu.apply_viscount_style(axB)
  axB.set_title("B. Middle Mississippian and Pueblo III Kriged Substrata (1200AD)", fontsize=9.0, pad=5)

  # Panel C: Velkscala Disaggregated Population Density (1500AD)
  axC = axes[1, 0]
  cmh.draw_basemap(axC, cmh.PROJ_NA, arg3_dark=True)
  velk_p = CENTAUR_DIR.parents[3] / "histmap/2.data_cleaning/population_Velkscala/population_rasters/population_1500.png"
  if velk_p.exists():
    vp_f32 = cmh.load_f32_raster(velk_p)
    grid_v = cmh.reproject_f32_raster(vp_f32, cmh.PROJ_NA, xlim_na, ylim_na, arg4_width_px=960, arg5_height_px=760)
    pos_v = grid_v[grid_v > 0.0]
    hi_v = max(10.0, float(np.percentile(pos_v, 99.6))) if pos_v.size > 0 else 300.0
    lo_v = max(0.05, hi_v * 5e-4)
    grid_v_m = np.ma.masked_where(grid_v <= 0.0, np.clip(grid_v, lo_v, hi_v))
    imC = axC.imshow(grid_v_m, extent=[xlim_na[0], xlim_na[1], ylim_na[0], ylim_na[1]], origin="upper", cmap="viridis", norm=LogNorm(vmin=lo_v, vmax=hi_v), alpha=0.92, zorder=3.5)
    caxC = axC.inset_axes([0.04, 0.075, 0.36, 0.042])
    cbC = fig.colorbar(imC, cax=caxC, orientation="horizontal", format=vpu.euro_log_formatter(True))
    vpu.apply_human_colorbar_ticks(cbC, True)
    cbC.outline.set_edgecolor("#e2e8f0")
    cbC.ax.tick_params(labelsize=6.0, colors="white")
    caxC.set_title("Inhabitants per 5' Cell (1500AD)", fontsize=6.4, pad=2, color="white")
  cmh.draw_historical_borders(axC, cmh.PROJ_NA, 1500, arg4_color="#e2e8f0")
  axC.set_xlim(*xlim_na)
  axC.set_ylim(*ylim_na)
  axC.set_aspect("equal", adjustable="box")
  axC.set_xticks([])
  axC.set_yticks([])
  cmh.draw_inline_graticule(axC, cmh.PROJ_NA, xlim_na, ylim_na, [25, 45, 65], [-160, -120, -80, -40])
  cmh.place_bbox_callouts(
    fig, axC,
    [("Moundville", -87.63, 33.00), ("Taos Pueblo", -105.55, 36.44), ("Stadacona", -71.21, 46.81), ("Marpole", -123.14, 49.20), ("Central Valley", -121.5, 38.5)],
    cmh.PROJ_NA, xlim_na, ylim_na, arg6_max_labels=5, arg7_min_sep_px=45.0, arg8_fontsize=6.0
  )
  vpu.apply_viscount_style(axC)
  axC.set_title("C. Disaggregated Population Density Surface (1500AD)", fontsize=9.0, pad=5)

  # Panel D: Actual Multi-Horizon Empirical Semivariograms & Fitted Matern Models
  axD = axes[1, 1]
  u_grid = np.linspace(0.0, 14.0, 260)
  for dom_lbl, diag_rel, col_h, ls_h in [
    ("North America", "_shared/sites_northern_america/config/kriging_diagnostics.json", "#2b5c8f", "-"),
    ("Hawai'i and Polynesia", "_shared/sites_hawaii_polynesia/config/kriging_diagnostics.json", "#c05246", "--")
  ]:
    kd = json.loads((CENTAUR_DIR / diag_rel).read_text(encoding="utf-8"))
    vms = kd.get("variogram_models", {})
    emps, u_ref = [], None
    t1s, t2s, nts_l, c1s, c2s, r2s = [], [], [], [], [], []
    for h_k, vm in vms.items():
      ue = np.asarray(vm.get("empirical_u_lags", []), dtype=float)
      ge = np.asarray(vm.get("empirical_gammas", []), dtype=float)
      if len(ue) > 0 and len(ge) == len(ue):
        pl_m = (ue >= 2.4) & (ue <= 8.0)
        sill_h = float(np.mean(ge[pl_m])) if np.any(pl_m) else float(np.mean(ge[-min(3, len(ge)):]))
        ge_n = ge / max(sill_h, 1e-9)
        axD.plot(ue, ge_n, color=col_h, alpha=0.18, linewidth=0.8)
        if u_ref is None:
          u_ref = ue
        if len(ge_n) == len(u_ref):
          emps.append(ge_n)
      t1s.append(float(vm["tau1_dimensionless"]))
      t2s.append(float(vm["tau2_dimensionless"]))
      nts_l.append(float(vm.get("nugget_to_sill_ratio", 0.04)))
      c1s.append(float(vm["c1_weight"]))
      c2s.append(float(vm["c2_weight"]))
      r2s.append(float(vm["residual_r2"]))
    t1m = float(np.mean(t1s))
    r2m = float(np.mean(r2s))
    g_fit = _matern32_gamma(u_grid, float(np.mean(nts_l)), float(np.mean(c1s)), float(np.mean(c2s)), t1m, float(np.mean(t2s)))
    t1x = vpu.format_mathtext_euro(t1m, 2)
    r2x = vpu.format_mathtext_euro(r2m, 3)
    axD.plot(u_grid, g_fit, color=col_h, linestyle=ls_h, linewidth=2.1, label=f"{dom_lbl} Matérn ($\\tau_1={t1x}$, $R^2={r2x}$)")
    if emps and u_ref is not None:
      axD.scatter(u_ref, np.mean(np.vstack(emps), axis=0), s=24, color=col_h, edgecolors="white", linewidths=0.5, zorder=6, label=f"{dom_lbl} mean empirical bins ($n={len(vms)}$)")

  axD.set_xlabel("Dimensionless Voronoi geodesic lag $u_{ij}$", fontsize=8.4)
  axD.set_ylabel("Normalised semivariance $\\gamma(u)/\\sigma^2$", fontsize=8.4)
  axD.set_xlim(0.0, 14.0)
  axD.set_ylim(0.0, 1.24)
  axD.xaxis.set_major_formatter(vpu.euro_tick_formatter(0))
  axD.yaxis.set_major_formatter(vpu.euro_tick_formatter(1))
  axD.legend(loc="lower right", fontsize=6.6, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axD)
  axD.grid(True, linestyle=":", alpha=0.45)
  axD.set_title("D. Multi-Horizon Empirical Semivariograms and Matérn Fits", fontsize=9.0, pad=5)

  fig.suptitle("North America and Polynesia Substrata Kriging, Disaggregated Density and Semivariogram Mosaic", fontsize=11.4, y=0.965)
  cmh.verify_zero_text_overlaps(fig, "root_fig5")
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig5_kriging_validation.png", 300)
  plt.close(fig)


def render_chapter_fig1 (arg0_mod):
  """Generates Chapter Figure 1: Equal-Area pure-vector POLARIS map with .naissance borders."""
  plt.rcdefaults()
  plt.style.use("default")
  mid = arg0_mod["id"]
  feats = arg0_mod["geojson"].get("features", [])
  setts = arg0_mod["settlements"]
  byr = arg0_mod["border_year"]
  ys_dom = [int(k) for k in arg0_mod["data"]["summary"]["headline_population_by_benchmark"].keys()]
  span_str = f"({_fmt_yr(min(ys_dom))} to {_fmt_yr(max(ys_dom))})"
  regs = arg0_mod["data"].get("regions", {})

  if mid == "united_states_post_independence":
    div_lookup = {}
    for d_name, d_col, d_ids in US_DIVISIONS:
      for rid in d_ids:
        div_lookup[rid] = d_col
    color_fn = lambda feat, idx: div_lookup.get(feat.get("properties", {}).get("region_id", ""), cmh.mute_rgb_hex(feat.get("properties", {}).get("colour"), idx))

    fig = plt.figure(figsize=(14.4, 8.6), dpi=300)
    gs = GridSpec(3, 2, figure=fig, width_ratios=[2.45, 1.0], left=0.025, right=0.98, top=0.89, bottom=0.14, wspace=0.08, hspace=0.22)
    axA = fig.add_subplot(gs[:, 0])
    axB = fig.add_subplot(gs[0, 1])
    axC = fig.add_subplot(gs[1, 1])
    axD = fig.add_subplot(gs[2, 1])

    f_l48 = [f for f in feats if not any(t in str(f.get("properties", {}).get("region_id", "")) for t in ("alaska", "hawaii", "samoa"))]
    f_ak = [f for f in feats if "alaska" in str(f.get("properties", {}).get("region_id", ""))]
    f_hi = [f for f in feats if "hawaii" in str(f.get("properties", {}).get("region_id", ""))]
    f_as = [f for f in feats if "samoa" in str(f.get("properties", {}).get("region_id", ""))]

    _, _, b_l48 = _build_vector_patches(f_l48, PROJ_US48, arg3_color_fn=color_fn)
    xl_a, yl_a = _pad_aspect(b_l48 if b_l48 else (-2400, -1400, 2600, 1600), arg1_aspect=1.45)
    _draw_panel_map(fig, axA, PROJ_US48, f_l48, byr, xl_a, yl_a, setts, arg8_max_lbl=8, arg9_color_fn=color_fn, arg10_is_dense=True)
    axA.set_title("A. Contiguous 48 States, DC and Bermuda", fontsize=9.0, pad=4)

    _, _, b_ak = _build_vector_patches(f_ak, PROJ_NC, arg3_color_fn=color_fn)
    xl_b, yl_b = _pad_aspect(b_ak if b_ak else (-2000, -900, 1300, 1200), arg1_aspect=1.45)
    _draw_panel_map(fig, axB, PROJ_NC, f_ak, byr, xl_b, yl_b, setts, arg8_max_lbl=3, arg9_color_fn=color_fn, arg10_is_dense=True)
    axB.set_title("B. Alaska", fontsize=8.4, pad=3)

    _draw_panel_map(fig, axC, cmh.PROJ_HI, f_hi, byr, (-355.0, 320.0), (-215.0, 225.0), setts, arg8_max_lbl=3, arg9_color_fn=color_fn)
    axC.set_title("C. Hawai'i", fontsize=8.4, pad=3)

    _draw_panel_map(fig, axD, cmh.PROJ_AS, f_as, byr, (-125.0, 175.0), (-85.0, 95.0), setts, arg8_max_lbl=2, arg9_color_fn=color_fn)
    axD.set_title("D. American Samoa", fontsize=8.4, pad=3)

    leg_h = [Patch(facecolor=dc, edgecolor="#334155", linewidth=0.45, label=dn) for dn, dc, _ in US_DIVISIONS]
    fig.legend(handles=leg_h, loc="lower center", bbox_to_anchor=(0.5, 0.015), ncol=4, fontsize=6.8, frameon=True, facecolor="white", title="Jurisdictional Groupings (50 States, DC, Bermuda and Am. Samoa)", title_fontsize=7.2)

  elif mid == "hawaii_and_american_polynesia":
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.6, 5.8), dpi=300, gridspec_kw={"width_ratios": [1.55, 1.0]})
    plt.subplots_adjust(left=0.025, right=0.975, top=0.86, bottom=0.18, wspace=0.08)
    _draw_panel_map(fig, axL, cmh.PROJ_HI, feats, byr, (-355.0, 320.0), (-215.0, 225.0), setts, arg8_max_lbl=6)
    axL.set_title("A. Hawaiian Archipelago (Albers Equal-Area)", fontsize=9.0, pad=5)
    _draw_panel_map(fig, axR, cmh.PROJ_AS, feats, byr, (-125.0, 175.0), (-85.0, 95.0), setts, arg8_max_lbl=4)
    axR.set_title("B. American Samoa: Tutuila and Manu'a Islands", fontsize=9.0, pad=5)
    leg_h = [Patch(facecolor=cmh.mute_rgb_hex(f.get("properties", {}).get("colour"), i), edgecolor="#334155", linewidth=0.45, label=_clean_sub_label(f.get("properties", {}).get("name", ""), 28)) for i, f in enumerate(feats)]
    if leg_h:
      fig.legend(handles=leg_h, loc="lower center", bbox_to_anchor=(0.5, 0.02), ncol=3, fontsize=7.0, frameon=True, facecolor="white")

  elif mid in ("colonial_america_to_1754", "colonial_america_to_1783"):
    f_main = [f for f in feats if "alaska" not in str(f.get("properties", {}).get("region_id", ""))]
    f_ak = [f for f in feats if "alaska" in str(f.get("properties", {}).get("region_id", ""))]
    ncols_l = 5
    nrows_l = max(1, math.ceil(len(regs) / ncols_l))
    bot_m = min(0.32, 0.07 + 0.036 * nrows_l)
    fig = plt.figure(figsize=(14.2, 8.2), dpi=300)
    gs = GridSpec(1, 2, figure=fig, width_ratios=[2.35, 1.0], left=0.025, right=0.98, top=0.88, bottom=bot_m, wspace=0.07)
    axA = fig.add_subplot(gs[0, 0])
    axB = fig.add_subplot(gs[0, 1])

    _, _, b_m = _build_vector_patches(f_main, PROJ_US48)
    xl_m, yl_m = _pad_aspect(b_m if b_m else (-2400, -1400, 2600, 1600), arg1_aspect=1.42)
    _draw_panel_map(fig, axA, PROJ_US48, f_main, byr, xl_m, yl_m, setts, arg8_max_lbl=7)
    axA.set_title("A. Atlantic Colonies, Indigenous Confederacies and Borderlands", fontsize=9.0, pad=4)

    _, _, b_ak = _build_vector_patches(f_ak, PROJ_NC)
    xl_b, yl_b = _pad_aspect(b_ak if b_ak else (-2000, -900, 1300, 1200), arg1_aspect=0.95)
    _draw_panel_map(fig, axB, PROJ_NC, f_ak, byr, xl_b, yl_b, setts, arg8_max_lbl=4)
    axB.set_title("B. Alaska Maritime Contact Zone", fontsize=9.0, pad=4)

    col_map = {f.get("properties", {}).get("region_id", ""): cmh.mute_rgb_hex(f.get("properties", {}).get("colour"), i) for i, f in enumerate(feats)}
    leg_h = [Patch(facecolor=col_map.get(rk, PALETTE[i % len(PALETTE)]), edgecolor="#334155", linewidth=0.4, label=_clean_sub_label(rv.get("name", rk), 25)) for i, (rk, rv) in enumerate(regs.items())]
    if leg_h:
      fig.legend(handles=leg_h, loc="lower center", bbox_to_anchor=(0.5, 0.015), ncol=ncols_l, fontsize=5.8, frameon=True, facecolor="white")

  else:
    proj = PROJ_NC if mid == "northern_cascadia_and_alaska" else (cmh.PROJ_CAN if mid in CAN_WIDE_IDS else cmh.choose_local_albers(feats))
    _, _, bounds = _build_vector_patches(feats, proj)
    if bounds is None:
      bounds = (-1200.0, -800.0, 1200.0, 800.0)
    ncols_l = min(4, max(2, len(regs)))
    nrows_l = max(1, math.ceil(len(regs) / ncols_l))
    bot_m = min(0.28, 0.06 + 0.042 * nrows_l)
    fig, ax = plt.subplots(figsize=(12.4, 7.6), dpi=300)
    plt.subplots_adjust(left=0.025, right=0.975, top=0.89, bottom=bot_m)
    xl, yl = _pad_aspect(bounds, arg1_aspect=1.65)
    _draw_panel_map(fig, ax, proj, feats, byr, xl, yl, setts, arg8_max_lbl=7, arg10_is_dense=(len(setts) > 1200))

    col_map = {f.get("properties", {}).get("region_id", ""): cmh.mute_rgb_hex(f.get("properties", {}).get("colour"), i) for i, f in enumerate(feats)}
    leg_h = [Patch(facecolor=col_map.get(rk, PALETTE[i % len(PALETTE)]), edgecolor="#334155", linewidth=0.4, label=_clean_sub_label(rv.get("name", rk), 32)) for i, (rk, rv) in enumerate(regs.items())]
    if leg_h:
      fig.legend(handles=leg_h, loc="lower center", bbox_to_anchor=(0.5, 0.018), ncol=ncols_l, fontsize=6.4, frameon=True, facecolor="white")

  fig.suptitle(f"{arg0_mod['title']}: Sub-Regions and Settlements {span_str}", fontsize=11.0, y=0.96)
  cmh.verify_zero_text_overlaps(fig, f"{mid}_fig1")
  vpu.save_viscount_figure(fig, arg0_mod["fig_dir"] / f"fig1_{mid}_spatial.png", 300)
  plt.close(fig)


def render_chapter_fig2 (arg0_mod):
  """Generates Chapter Figure 2: POLARIS 2-panel trajectory (sub-regions + aggregate bounds)."""
  plt.rcdefaults()
  plt.style.use("default")
  mid = arg0_mod["id"]
  hl = arg0_mod["data"]["summary"]["headline_population_by_benchmark"]
  ys = sorted(int(k) for k in hl.keys())
  tot = np.array([float(hl[str(y)]) for y in ys], dtype=float)
  regs = arg0_mod["data"].get("regions", {})
  ranked = sorted(regs.items(), key=lambda kv: max((float(v) for v in kv[1].get("population", {}).values()), default=0.0), reverse=True)

  fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.0, 5.8), dpi=300)
  show_legs = ranked[:8]
  nrows_l = max(1, math.ceil(len(show_legs) / 3))
  bot_m = min(0.28, 0.13 + 0.036 * nrows_l)
  plt.subplots_adjust(left=0.07, right=0.97, top=0.84, bottom=bot_m, wspace=0.20)

  handles_l = []
  for r_i, (rk, rv) in enumerate(show_legs):
    pm = rv.get("population", {})
    ry = sorted(int(k) for k in pm.keys())
    ln, = axL.plot(ry, [float(pm[str(y)]) for y in ry], linewidth=1.7, color=PALETTE[r_i % len(PALETTE)], label=_clean_sub_label(rv.get("name", rk), 32))
    handles_l.append(ln)
  axL.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  _fmt_yr_ticks(axL, ys)
  axL.set_xlim(ys[0], ys[-1])
  axL.set_xlabel("Calendar Year", fontsize=8.4)
  axL.set_ylabel("Sub-Regional Population", fontsize=8.4)
  axL.set_title("A. Leading Sub-Regional Trajectories", fontsize=9.2, pad=5)
  vpu.apply_viscount_style(axL)
  axL.grid(True, linestyle=":", alpha=0.45)

  axR.fill_between(ys, tot * 0.92, tot * 1.08, color="#2b5c8f", alpha=0.16, label="Uncertainty envelope (+/- 8%)")
  axR.plot(ys, tot, color="#0f172a", linewidth=2.2, label="Regional total")
  axR.scatter([ys[0], ys[-1]], [tot[0], tot[-1]], s=24, color="#b91c1c", zorder=6)
  axR.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  _fmt_yr_ticks(axR, ys)
  axR.set_xlim(ys[0], ys[-1])
  axR.set_ylim(0, max(float(np.max(tot)) * 1.18, 10.0))
  axR.set_xlabel("Calendar Year", fontsize=8.4)
  axR.set_ylabel("Aggregate Population", fontsize=8.4)
  axR.set_title("B. Aggregate Trajectory and Bounds", fontsize=9.2, pad=5)
  axR.legend(loc="upper left", fontsize=7.0, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axR)
  axR.grid(True, linestyle=":", alpha=0.45)

  if handles_l:
    fig.legend(handles=handles_l, loc="lower center", bbox_to_anchor=(0.5, 0.015), ncol=min(3, len(handles_l)), fontsize=6.6, frameon=True, facecolor="white")
  fig.suptitle(f"{arg0_mod['title']}: Demographic Trajectory ({_fmt_yr(ys[0])} to {_fmt_yr(ys[-1])})", fontsize=10.8, y=0.95)
  cmh.verify_zero_text_overlaps(fig, f"{mid}_fig2")
  vpu.save_viscount_figure(fig, arg0_mod["fig_dir"] / f"fig2_{mid}_trajectory.png", 300)
  plt.close(fig)


def render_chapter_fig3 (arg0_mod):
  """Generates Chapter Figure 3: POLARIS 2-panel composition shares and regional bars."""
  plt.rcdefaults()
  plt.style.use("default")
  mid = arg0_mod["id"]
  hl = arg0_mod["data"]["summary"]["headline_population_by_benchmark"]
  ys = sorted(int(k) for k in hl.keys())
  regs = arg0_mod["data"].get("regions", {})
  ranked = sorted(regs.items(), key=lambda kv: max((float(v) for v in kv[1].get("population", {}).values()), default=0.0), reverse=True)

  top_k = ranked[:8]
  mat, lbls, cols = [], [], []
  def _interp_series (arg0_pop_map, arg1_ys):
    ks = sorted(int(k) for k in arg0_pop_map.keys())
    if not ks:
      return [0.0] * len(arg1_ys)
    vals = [float(arg0_pop_map[str(k)]) for k in ks]
    return np.interp(arg1_ys, ks, vals, left=0.0, right=vals[-1]).tolist()
  for r_i, (rk, rv) in enumerate(top_k):
    mat.append(_interp_series(rv.get("population", {}), ys))
    lbls.append(_clean_sub_label(rv.get("name", rk), 30))
    cols.append(PALETTE[r_i % len(PALETTE)])
  if len(ranked) > 8:
    rem = np.sum([_interp_series(rv.get("population", {}), ys) for _, rv in ranked[8:]], axis=0)
    mat.append(rem.tolist())
    lbls.append("Remaining Sub-Regions")
    cols.append("#94a3b8")

  arr = np.asarray(mat, dtype=float)
  pcts = arr / np.maximum(np.sum(arr, axis=0), 1.0) * 100.0
  nrows_l = max(1, math.ceil(len(lbls) / 3))
  bot_m = min(0.28, 0.13 + 0.036 * nrows_l)

  fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.2, 5.8), dpi=300, gridspec_kw={"width_ratios": [1.05, 1.15]})
  plt.subplots_adjust(left=0.06, right=0.97, top=0.84, bottom=bot_m, wspace=0.42)

  axL.stackplot(ys, pcts, labels=lbls, colors=cols, alpha=0.84)
  _fmt_yr_ticks(axL, ys)
  axL.set_xlim(ys[0], ys[-1])
  axL.set_ylim(0, 100)
  axL.yaxis.set_major_formatter(vpu.euro_tick_formatter(0))
  axL.set_xlabel("Calendar Year", fontsize=8.4)
  axL.set_ylabel("Share (%)", fontsize=8.4)
  axL.set_title("A. Sub-Regional Share Evolution (%)", fontsize=9.2, pad=5)
  vpu.apply_viscount_style(axL)
  axL.grid(True, linestyle=":", alpha=0.45)

  top_bars = ranked[:10][::-1]
  if top_bars:
    y_i = np.arange(len(top_bars))
    pks = [max((float(v) for v in kv[1].get("population", {}).values()), default=0.0) for kv in top_bars]
    terms = [float(kv[1].get("population", {}).get(str(ys[-1]), 0.0)) for kv in top_bars]
    ynms = [_clean_sub_label(kv[1].get("name", kv[0]), 24) for kv in top_bars]
    axR.barh(y_i + 0.17, pks, height=0.33, color="#2b5c8f", alpha=0.86, label="Holocene/Epoch Peak")
    axR.barh(y_i - 0.17, terms, height=0.33, color="#3d8a5a", alpha=0.86, label=f"Terminal ({_fmt_yr(ys[-1])})")
    mx_b = max(max(pks), max(terms), 1.0)
    for k_i, pv in enumerate(pks):
      axR.text(pv + mx_b * 0.02, y_i[k_i] + 0.17, vpu.format_semantic_population(pv), va="center", ha="left", fontsize=6.6)
    axR.set_yticks(y_i)
    axR.set_yticklabels(ynms, fontsize=7.0)
    axR.set_xlim(0, mx_b * 1.25)
  axR.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  axR.set_xlabel("Population", fontsize=8.4)
  axR.set_title("B. Leading Sub-Regions: Peak vs Terminal", fontsize=9.2, pad=5)
  axR.legend(loc="lower right", fontsize=6.8, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axR)
  axR.grid(True, linestyle=":", alpha=0.45)

  leg_handles = [Patch(facecolor=c, edgecolor="#334155", linewidth=0.35, label=l) for l, c in zip(lbls, cols)]
  fig.legend(handles=leg_handles, loc="lower center", bbox_to_anchor=(0.5, 0.015), ncol=min(3, len(lbls)), fontsize=6.6, frameon=True, facecolor="white")
  fig.suptitle(f"{arg0_mod['title']}: Sub-Regional Distribution ({_fmt_yr(ys[0])} to {_fmt_yr(ys[-1])})", fontsize=10.8, y=0.95)
  cmh.verify_zero_text_overlaps(fig, f"{mid}_fig3")
  vpu.save_viscount_figure(fig, arg0_mod["fig_dir"] / f"fig3_{mid}_shares.png", 300)
  plt.close(fig)


def render_chapter_fig4 (arg0_mod):
  """Generates Chapter Figure 4: rank-size curve and top 15 settlements without label clipping."""
  plt.rcdefaults()
  plt.style.use("default")
  mid = arg0_mod["id"]
  setts = arg0_mod["settlements"]
  items = setts.values() if isinstance(setts, dict) else setts
  ranked = []
  for s in items:
    pk = max((float(v) for v in (s.get("population") or {}).values()), default=0.0)
    if pk > 0:
      ranked.append((pk, str(s.get("name", ""))))
  ranked.sort(key=lambda t: (-t[0], t[1]))

  fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.2, 5.8), dpi=300, gridspec_kw={"width_ratios": [1.0, 1.25]})
  plt.subplots_adjust(left=0.07, right=0.97, top=0.85, bottom=0.13, wspace=0.44)

  if ranked:
    ranks = np.arange(1, len(ranked) + 1, dtype=float)
    vals = np.array([r[0] for r in ranked], dtype=float)
    axL.loglog(ranks, vals, "o", markersize=3.5, color="#2b5c8f", alpha=0.80)
    vpu.apply_human_log_ticks(axL, "both")
  axL.set_xlabel("Settlement Rank (log)", fontsize=8.4)
  axL.set_ylabel("Peak Population (log)", fontsize=8.4)
  axL.set_title("A. Rank-Size Distribution", fontsize=9.2, pad=5)
  vpu.apply_viscount_style(axL)
  axL.grid(True, linestyle=":", alpha=0.45)

  top15 = ranked[:15][::-1]
  if top15:
    y_pos = np.arange(len(top15))
    bar_v = [r[0] for r in top15]
    bar_l = [_clean_sub_label(r[1], 24) for r in top15]
    mx_v = max(bar_v) if bar_v else 1.0
    axR.barh(y_pos, bar_v, height=0.68, color="#3d8a5a", alpha=0.85, edgecolor="#145a32", linewidth=0.4)
    for k_i, pv in enumerate(bar_v):
      axR.text(pv + mx_v * 0.02, y_pos[k_i], vpu.format_semantic_population(pv), va="center", ha="left", fontsize=6.6)
    axR.set_yticks(y_pos)
    axR.set_yticklabels(bar_l, fontsize=7.0)
    axR.set_xlim(0, mx_v * 1.24)
  axR.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  axR.set_xlabel("Peak Population", fontsize=8.4)
  axR.set_title("B. Leading 15 Catalogued Settlements", fontsize=9.2, pad=5)
  vpu.apply_viscount_style(axR)
  axR.grid(True, linestyle=":", alpha=0.45)

  n_disp = len(items) if isinstance(setts, dict) else len(setts)
  fig.suptitle(f"{arg0_mod['title']}: Settlement Hierarchy (n={vpu.format_euro_number(n_disp, 0)})", fontsize=10.8, y=0.96)
  cmh.verify_zero_text_overlaps(fig, f"{mid}_fig4")
  vpu.save_viscount_figure(fig, arg0_mod["fig_dir"] / f"fig4_{mid}_settlements.png", 300)
  plt.close(fig)


def main ():
  """Renders all 5 CENTAUR root figures and 124 chapter figures across 31 modules."""
  ROOT_FIG_DIR.mkdir(parents=True, exist_ok=True)
  mods = _load_modules()
  print(f"[generate_centaur_figures] Rendering root POLARIS-grade figures for {len(mods)} CENTAUR modules...")
  render_root_fig1(mods)
  render_root_fig2(mods)
  render_root_fig3(mods)
  render_root_fig4(mods)
  render_root_fig5()

  for idx, m in enumerate(mods, start=1):
    m["fig_dir"].mkdir(parents=True, exist_ok=True)
    render_chapter_fig1(m)
    render_chapter_fig2(m)
    render_chapter_fig3(m)
    render_chapter_fig4(m)
    print(f"[{idx:02d}/31] Rendered 4 figures for {m['id']}")


if __name__ == "__main__":
  main()
