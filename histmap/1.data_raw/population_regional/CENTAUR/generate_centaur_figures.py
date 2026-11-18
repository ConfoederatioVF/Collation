# -*- coding: utf-8 -*-
"""Generate equal-area spatial maps with .naissance historical borders and
publication diagnostic figures for CENTAUR-II (5 root + 124 chapter PNGs).
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

PROJ_NC = cmh.AlbersEqualAreaConic(-145.0, 52.0, 68.0, 60.0)
NORTHERN_CAN_IDS = {
  "northern_canada", "prairies", "hudson_bay", "saint_lawrence", "maritimes",
  "colonial_canada_to_1763", "colonial_canada_to_1867", "canada_post_confederation"
}
PALETTE = [
  "#1b4f72", "#b03a2e", "#1e8449", "#7d3c98", "#b9770e",
  "#2874a6", "#922b21", "#148f77", "#6c3483", "#a04000",
  "#2e86c1", "#cb4335", "#239b56", "#884ea0", "#d4ac0d"
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
  "canada_post_confederation": ("Canada Post-Confederation (1867AD to 2026AD)", 1890),
  "united_states_post_independence": ("United States Post-Independence (1783AD to 2026AD)", 1890)
}

KELLY_HUC_ORDER = [
  "upper_colorado", "extreme_northern_plains", "northern_plains", "arizona",
  "great_basin", "upper_mississippi", "rio_grande", "cumberland",
  "southeast", "lower_mississippi", "southern_plains", "ohio_river",
  "new_england", "central_plains", "mid_atlantic", "great_lakes",
  "california", "northwest"
]


def _fmt_yr (arg0_yr):
  """Formats integer year concisely in British historical convention."""
  yi = int(arg0_yr)
  if yi < 0:
    return f"{abs(yi)}BC"
  return f"{yi}AD"


def _fmt_yr_ticks (arg0_ax, arg1_years):
  """Sets readable formatted historical year ticks on horizontal axis."""
  ys = sorted(set(int(y) for y in arg1_years))
  if not ys:
    return
  if len(ys) <= 7:
    chosen = ys
  else:
    idx = np.linspace(0, len(ys) - 1, 6).round().astype(int)
    chosen = sorted(set(ys[i] for i in idx))
  arg0_ax.set_xticks(chosen)
  arg0_ax.set_xticklabels([_fmt_yr(y) for y in chosen], fontsize=7.5)


def _clean_sub_label (arg0_name, arg1_max_len=32):
  """Formats sub-region label cleanly without awkward mid-word slicing."""
  txt = re.sub(r"^\d+\.\s*", "", str(arg0_name or "")).strip()
  txt = re.sub(r"\s*\([^)]*\)", "", txt).strip()
  txt = txt.replace("/", " and ")
  if len(txt) <= arg1_max_len:
    return txt
  words = txt.split()
  out = []
  cur = 0
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
  k1 = (1.0 + a1) * np.exp(-a1)
  k2 = (1.0 + a2) * np.exp(-a2)
  corr = float(arg2_c1) * k1 + float(arg3_c2) * k2
  return np.where(u <= 1e-12, 0.0, float(arg1_c0) + np.maximum(0.0, 1.0 - float(arg1_c0) - corr))


def _load_modules ():
  """Loads all 31 ordered module specs plus parsed JSON5 and settlement lists."""
  cfg_path = CENTAUR_DIR / "centaur_areal_masks.json5"
  cfg = json5.loads(cfg_path.read_text(encoding="utf-8"))
  mods = list(cfg.get("specialist_masks", [])) + list(cfg.get("national_epoch_masks", []))
  out = []
  for m in mods:
    mid = m["id"]
    j5_rel = pathlib.Path(m["json5_path"])
    j5_abs = CENTAUR_DIR.parents[2] / j5_rel if j5_rel.parts[0] == "histmap" else CENTAUR_DIR / j5_rel
    ch_dir = j5_abs.parent
    set_path = ch_dir / f"{mid}_settlements.json"
    gj_path = SUBREG_DIR / f"{mid}_subregions.geojson"
    data = json5.loads(j5_abs.read_text(encoding="utf-8"))
    setts = json.loads(set_path.read_text(encoding="utf-8")) if set_path.exists() else []
    gj = json.loads(gj_path.read_text(encoding="utf-8")) if gj_path.exists() else {"features": []}
    title_str, border_yr = MOD_META.get(mid, (mid, 1500))
    out.append({
      "id": mid,
      "title": title_str,
      "border_year": border_yr,
      "dir": ch_dir,
      "fig_dir": ch_dir / "figures",
      "data": data,
      "settlements": setts,
      "geojson": gj
    })
  return out


def _rgba_to_hex (arg0_col, arg1_idx):
  """Converts GeoJSON RGB list to Matplotlib hex colour with fallback."""
  if isinstance(arg0_col, (list, tuple)) and len(arg0_col) >= 3:
    r, g, b = [max(0, min(255, int(c))) for c in arg0_col[:3]]
    return f"#{r:02x}{g:02x}{b:02x}"
  return PALETTE[arg1_idx % len(PALETTE)]


def _proj_patch_collection (arg0_features, arg1_proj, arg2_seg=0.25, arg3_alpha=0.76, arg4_lw=0.35):
  """Builds PatchCollection and projected bounding box from GeoJSON features."""
  patches_list = []
  cols_list = []
  xs_all, ys_all = [], []
  for i, feat in enumerate(arg0_features):
    geom = feat.get("geometry")
    if not geom:
      continue
    pg = cmh.clip_and_project(shape(geom), arg1_proj, arg2_seg)
    ps = cmh.geom_to_patches(pg)
    if not ps:
      continue
    c_hex = _rgba_to_hex(feat.get("properties", {}).get("colour"), i)
    for p in ps:
      xy = p.get_xy()
      if len(xy) >= 3:
        xs_all.extend([float(xy[:, 0].min()), float(xy[:, 0].max())])
        ys_all.extend([float(xy[:, 1].min()), float(xy[:, 1].max())])
        patches_list.append(MplPolygon(xy, closed=True))
        cols_list.append(c_hex)
  if not patches_list:
    return None, None
  pc = PatchCollection(patches_list, facecolor=cols_list, edgecolor="#1e293b", linewidths=arg4_lw, alpha=arg3_alpha, zorder=2.5)
  bounds = (min(xs_all), min(ys_all), max(xs_all), max(ys_all))
  return pc, bounds


def _place_clean_callouts (arg0_ax, arg1_setts, arg2_proj, arg3_xlim, arg4_ylim, arg5_max_labels=6, arg6_min_sep_km=45.0):
  """Places top settlement callout boxes using greedy overlap rejection."""
  x0_lim, x1_lim = float(arg3_xlim[0]), float(arg3_xlim[1])
  y0_lim, y1_lim = float(arg4_ylim[0]), float(arg4_ylim[1])
  dx_span = max(x1_lim - x0_lim, 1.0)
  dy_span = max(y1_lim - y0_lim, 1.0)

  ranked = []
  for s in arg1_setts:
    coords = s.get("coords")
    if not isinstance(coords, list) or len(coords) < 2:
      continue
    lat, lon = float(coords[0]), float(coords[1])
    px, py = arg2_proj.fwd_pt(lon, lat)
    if not (x0_lim <= px <= x1_lim and y0_lim <= py <= y1_lim):
      continue
    pops = s.get("population") or {}
    pk = max((float(v) for v in pops.values()), default=0.0)
    ranked.append((pk, str(s.get("name", "")), px, py))
  ranked.sort(key=lambda t: (-t[0], t[1]))

  if ranked:
    arg0_ax.scatter(
      [r[2] for r in ranked], [r[3] for r in ranked],
      s=11, c="#0f172a", edgecolors="white", linewidths=0.4, alpha=0.82, zorder=6.2
    )

  cand_offsets = [
    (0.09, 0.07), (-0.09, 0.07), (0.09, -0.07), (-0.09, -0.07),
    (0.0, 0.11), (0.0, -0.11), (0.14, 0.0), (-0.14, 0.0),
    (0.14, 0.12), (-0.14, 0.12), (0.14, -0.12), (-0.14, -0.12)
  ]
  placed_boxes = []
  chosen_pts = []
  labels_placed = 0

  for pk, raw_name, px, py in ranked:
    if labels_placed >= arg5_max_labels:
      break
    too_close = any(math.hypot(px - cx, py - cy) < arg6_min_sep_km for cx, cy in chosen_pts)
    if too_close:
      continue
    short_nm = re.sub(r"-[A-Za-z .]+$", "", raw_name) if "-" in raw_name and pk > 0 else raw_name
    if len(short_nm) > 22:
      short_nm = short_nm[:19] + "..."
    label_txt = f"{short_nm} ({vpu.format_semantic_population(pk)})"
    bw = min(0.28, 0.0085 * len(label_txt) + 0.045)
    bh = 0.056

    best_pos = None
    for ox, oy in cand_offsets:
      fx = (px - x0_lim) / dx_span + ox
      fy = (py - y0_lim) / dy_span + oy
      fx = max(0.03 + 0.5 * bw, min(0.97 - 0.5 * bw, fx))
      fy = max(0.04 + 0.5 * bh, min(0.96 - 0.5 * bh, fy))
      box_cur = (fx - 0.5 * bw, fy - 0.5 * bh, fx + 0.5 * bw, fy + 0.5 * bh)
      collides = False
      for b0 in placed_boxes:
        if not (box_cur[2] < b0[0] or box_cur[0] > b0[2] or box_cur[3] < b0[1] or box_cur[1] > b0[3]):
          collides = True
          break
      if not collides:
        best_pos = (x0_lim + fx * dx_span, y0_lim + fy * dy_span, box_cur)
        break

    if best_pos is None:
      continue

    tx, ty, b_fin = best_pos
    placed_boxes.append(b_fin)
    chosen_pts.append((px, py))
    labels_placed += 1
    arg0_ax.plot([px, tx], [py, ty], color="#1e293b", linewidth=0.6, zorder=7.0)
    arg0_ax.scatter([px], [py], s=26, c="#b91c1c", edgecolors="white", linewidths=0.65, zorder=8.0)
    arg0_ax.text(
      tx, ty, label_txt, fontsize=6.4, color="#0f172a", ha="center", va="center", zorder=10.0,
      bbox=dict(boxstyle="round,pad=0.16", facecolor="white", edgecolor="#475569", alpha=0.95, linewidth=0.5)
    )


def _pad_bounds_for_aspect (arg0_bounds, arg1_aspect=1.55, arg2_min_span=420.0):
  """Expands projected bounding box symmetrically to fit target axes aspect."""
  x0, y0, x1, y1 = arg0_bounds
  cx = 0.5 * (x0 + x1)
  cy = 0.5 * (y0 + y1)
  w = max((x1 - x0) * 1.24, arg2_min_span)
  h = max((y1 - y0) * 1.24, arg2_min_span / arg1_aspect)
  if w / h > arg1_aspect:
    h = w / arg1_aspect
  else:
    w = h * arg1_aspect
  return (cx - 0.5 * w, cx + 0.5 * w), (cy - 0.5 * h, cy + 0.5 * h)


def _draw_styled_map_axis (arg0_ax, arg1_proj, arg2_feats, arg3_border_yr, arg4_xlim, arg5_ylim, arg6_grats=True):
  """Draws equal-area basemap, subregions, .naissance borders and graticules."""
  cmh.draw_basemap(arg0_ax, arg1_proj)
  pc, _ = _proj_patch_collection(arg2_feats, arg1_proj)
  if pc is not None:
    arg0_ax.add_collection(pc)
  if arg3_border_yr >= 1000:
    cmh.draw_historical_borders(arg0_ax, arg1_proj, arg3_border_yr, arg4_color="#1f2937")
  if arg6_grats:
    cmh.draw_graticule(arg0_ax, arg1_proj, arg4_xlim, arg5_ylim, [20, 35, 50, 65], [-160, -140, -120, -100, -80, -60, -40])
  arg0_ax.set_xlim(*arg4_xlim)
  arg0_ax.set_ylim(*arg5_ylim)
  arg0_ax.set_aspect("equal", adjustable="box")
  arg0_ax.set_xticks([])
  arg0_ax.set_yticks([])
  vpu.apply_viscount_style(arg0_ax, grid=False)


def render_root_fig1 (arg0_mods):
  """Generates Figure 1: four-epoch Equal-Area CENTAUR macro-regional coverage."""
  plt.rcdefaults()
  plt.style.use("default")
  by_id = {m["id"]: m for m in arg0_mods}
  fig, axes = plt.subplots(2, 2, figsize=(15.0, 10.6), dpi=300)
  plt.subplots_adjust(left=0.025, right=0.975, top=0.91, bottom=0.075, wspace=0.05, hspace=0.14)

  xlim_na = (-4850.0, 3450.0)
  ylim_na = (-2250.0, 4100.0)
  panel_specs = [
    ("A. Pre-Columbian Zones and Watersheds (10000BC-1600AD)", 1500, [
      ("Canada, Alaska and Greenland (6 modules)", "#1b4f72", [
        "northern_cascadia_and_alaska", "northern_canada", "prairies", "hudson_bay", "saint_lawrence", "maritimes"
      ]),
      ("Western and Plains US HUs (7 units)", "#b9770e", [
        "upper_colorado", "extreme_northern_plains", "northern_plains", "arizona", "great_basin", "central_plains", "southern_plains"
      ]),
      ("Eastern Woodlands and Mississippi HUs (9 units)", "#1e8449", [
        "upper_mississippi", "rio_grande", "cumberland", "southeast", "lower_mississippi", "ohio_river", "new_england", "mid_atlantic", "great_lakes"
      ]),
      ("Pacific Coast and Polynesia (3 modules)", "#922b21", [
        "california", "northwest", "hawaii_and_american_polynesia"
      ])
    ], True),
    ("B. Early Colonial Contact and Indigenous Continuity (1500AD-1763AD)", 1754, [
      ("Colonial America to 1754AD", "#2874a6", ["colonial_america_to_1754"]),
      ("Colonial Canada to 1763AD", "#b03a2e", ["colonial_canada_to_1763"])
    ], False),
    ("C. Late Colonial and Confederation Period (1754AD-1867AD)", 1815, [
      ("Colonial America to 1783AD", "#1b4f72", ["colonial_america_to_1783"]),
      ("Colonial Canada to 1867AD", "#a04000", ["colonial_canada_to_1867"])
    ], False),
    ("D. Post-Independence States and Territories (1783AD-2026AD)", 1890, [
      ("United States Post-1783AD", "#2874a6", ["united_states_post_independence"]),
      ("Canada, Greenland and St-Pierre Post-1867AD", "#b03a2e", ["canada_post_confederation"])
    ], True)
  ]

  for idx, (ptitle, byear, groups, show_insets) in enumerate(panel_specs):
    ax = axes[idx // 2, idx % 2]
    cmh.draw_basemap(ax, cmh.PROJ_NA)
    leg_handles = []
    for glabel, ghex, gids in groups:
      g_patches = []
      for gid in gids:
        if gid not in by_id:
          continue
        for feat in by_id[gid]["geojson"].get("features", []):
          geom = feat.get("geometry")
          if geom:
            pg = cmh.clip_and_project(shape(geom), cmh.PROJ_NA, 0.35)
            g_patches.extend(cmh.geom_to_patches(pg))
      if g_patches:
        ax.add_collection(PatchCollection(
          [MplPolygon(p.get_xy(), closed=True) for p in g_patches],
          facecolor=ghex, edgecolor="#1e293b", linewidths=0.22, alpha=0.72, zorder=2.5
        ))
      leg_handles.append(Patch(facecolor=ghex, edgecolor="#1e293b", linewidth=0.5, label=glabel))
    cmh.draw_historical_borders(ax, cmh.PROJ_NA, byear, arg4_color="#111827")
    cmh.draw_graticule(ax, cmh.PROJ_NA, xlim_na, ylim_na, [25, 45, 65], [-160, -120, -80, -40])
    ax.set_xlim(*xlim_na)
    ax.set_ylim(*ylim_na)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    vpu.apply_viscount_style(ax, grid=False)
    ax.set_title(ptitle, fontsize=9.2, pad=5)
    ax.legend(handles=leg_handles, loc="lower right", fontsize=6.4, frameon=True, facecolor="white", edgecolor="#94a3b8", framealpha=0.92)

    if show_insets and "hawaii_and_american_polynesia" in by_id:
      hi_feats = by_id["hawaii_and_american_polynesia"]["geojson"].get("features", [])
      ax_hi = ax.inset_axes([0.02, 0.03, 0.22, 0.19])
      _draw_styled_map_axis(ax_hi, cmh.PROJ_HI, hi_feats, byear, (-390, 320), (-240, 260), arg6_grats=False)
      ax_hi.set_title("Hawai'i", fontsize=6.0, pad=2)
      ax_as = ax.inset_axes([0.25, 0.03, 0.15, 0.19])
      _draw_styled_map_axis(ax_as, cmh.PROJ_AS, hi_feats, byear, (-120, 170), (-70, 70), arg6_grats=False)
      ax_as.set_title("Am. Samoa", fontsize=6.0, pad=2)

  fig.suptitle("CENTAUR-II Spatial Domains and Historical Boundaries (10000BC-2026AD)", fontsize=12.0, y=0.965)
  out_p = ROOT_FIG_DIR / "fig1_centaur_macro_zones.png"
  vpu.save_viscount_figure(fig, out_p, dpi=300)
  plt.close(fig)


def render_root_fig2 (arg0_mods):
  """Generates Figure 2: Holocene relative intensity across 18 US HUs."""
  plt.rcdefaults()
  plt.style.use("default")
  by_id = {m["id"]: m for m in arg0_mods}
  hucs = [mid for mid in KELLY_HUC_ORDER if mid in by_id]
  bench_yrs = [-10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000, 0, 400, 800, 1000, 1100, 1200, 1300, 1400, 1500, 1600]
  mat = np.zeros((len(hucs), len(bench_yrs)), dtype=float)
  y_labels = []

  for r_i, mid in enumerate(hucs):
    hl = by_id[mid]["data"]["summary"]["headline_population_by_benchmark"]
    series = np.array([float(hl.get(str(y), 0.0)) for y in bench_yrs], dtype=float)
    mx = float(np.max(series)) if len(series) else 1.0
    mat[r_i, :] = series / max(mx, 1.0)
    y_labels.append(MOD_META[mid][0])

  fig, ax = plt.subplots(figsize=(12.2, 6.8), dpi=300)
  im = ax.imshow(mat, aspect="auto", cmap="YlOrRd", vmin=0.0, vmax=1.0, interpolation="nearest")
  ax.set_yticks(np.arange(len(y_labels)))
  ax.set_yticklabels(y_labels, fontsize=7.6)
  ax.set_xticks(np.arange(len(bench_yrs)))
  ax.set_xticklabels([_fmt_yr(y) for y in bench_yrs], fontsize=7.4, rotation=32, ha="right")
  ax.set_xlabel("Calendar Year", fontsize=8.8)
  ax.set_title("Pre-Columbian United States: Relative Demographic Intensity Across 18 Hydrological Units", fontsize=10.5, pad=8)

  cbar = fig.colorbar(im, ax=ax, fraction=0.032, pad=0.025)
  cbar.set_ticks([0.0, 0.25, 0.5, 0.75, 1.0])
  cbar.set_ticklabels(["$0$", "$0{,}25$", "$0{,}50$", "$0{,}75$", "$1{,}00$"])
  cbar.set_label("Share of Unit Pre-Contact Peak", fontsize=8.5)
  vpu.apply_viscount_style(ax, grid=False)
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig2_precolumbian_kelly_hucs.png", dpi=300)
  plt.close(fig)


def render_root_fig3 (arg0_mods):
  """Generates Figure 3: Colonial continental demographic trajectories."""
  plt.rcdefaults()
  plt.style.use("default")
  by_id = {m["id"]: m for m in arg0_mods}
  specs = [
    ("colonial_america_to_1754", "Colonial America to 1754AD", "#1b4f72"),
    ("colonial_america_to_1783", "Colonial America to 1783AD", "#b9770e"),
    ("colonial_canada_to_1763", "Colonial Canada to 1763AD", "#1e8449"),
    ("colonial_canada_to_1867", "Colonial Canada to 1867AD", "#b03a2e")
  ]
  fig, ax = plt.subplots(figsize=(11.4, 5.8), dpi=300)
  all_yrs = []
  for mid, lbl, col in specs:
    hl = by_id[mid]["data"]["summary"]["headline_population_by_benchmark"]
    ys = sorted(int(k) for k in hl.keys())
    vs = [float(hl[str(y)]) for y in ys]
    all_yrs.extend(ys)
    ax.plot(ys, vs, color=col, linewidth=2.2, label=f"{lbl} (end {vpu.format_semantic_population(vs[-1])})")

  ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  _fmt_yr_ticks(ax, [1500, 1550, 1600, 1650, 1700, 1754, 1783, 1825, 1867])
  ax.set_xlim(1495, 1872)
  ax.set_xlabel("Calendar Year", fontsize=8.8)
  ax.set_ylabel("Total Population", fontsize=8.8)
  ax.set_title("Colonial America and Canada: Indigenous Continuity and Frontier Growth (1500AD-1867AD)", fontsize=10.4, pad=8)
  ax.legend(loc="upper left", fontsize=7.6, frameon=True, facecolor="white", edgecolor="#94a3b8")
  vpu.apply_viscount_style(ax, grid=True)
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig3_colonial_transition_trajectories.png", dpi=300)
  plt.close(fig)


def render_root_fig4 (arg0_mods):
  """Generates Figure 4: Modern United States and Canada dual-scale trajectories."""
  plt.rcdefaults()
  plt.style.use("default")
  by_id = {m["id"]: m for m in arg0_mods}
  fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.6, 5.4), dpi=300)
  plt.subplots_adjust(wspace=0.22)

  us_hl = by_id["united_states_post_independence"]["data"]["summary"]["headline_population_by_benchmark"]
  ca_hl = by_id["canada_post_confederation"]["data"]["summary"]["headline_population_by_benchmark"]
  us_y = sorted(int(k) for k in us_hl.keys())
  ca_y = sorted(int(k) for k in ca_hl.keys())
  us_v = [float(us_hl[str(y)]) for y in us_y]
  ca_v = [float(ca_hl[str(y)]) for y in ca_y]

  axL.plot(us_y, us_v, color="#1b4f72", linewidth=2.2, label=f"United States ({vpu.format_semantic_population(us_v[0])} to {vpu.format_semantic_population(us_v[-1])})")
  axL.plot(ca_y, ca_v, color="#b03a2e", linewidth=2.0, label=f"Canada and Greenland ({vpu.format_semantic_population(ca_v[0])} to {vpu.format_semantic_population(ca_v[-1])})")
  axL.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  _fmt_yr_ticks(axL, [1783, 1850, 1900, 1950, 2000, 2026])
  axL.set_xlabel("Calendar Year", fontsize=8.5)
  axL.set_ylabel("Total Population", fontsize=8.5)
  axL.set_title("A. Aggregate Trajectories (Linear Scale)", fontsize=9.4, pad=6)
  axL.legend(loc="upper left", fontsize=7.0, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axL, grid=True)

  axR.plot(ca_y, ca_v, color="#b03a2e", linewidth=2.2, label="Canada, Greenland and St-Pierre Total")
  axR.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  _fmt_yr_ticks(axR, [1867, 1901, 1931, 1961, 1991, 2026])
  axR.set_xlabel("Calendar Year", fontsize=8.5)
  axR.set_ylabel("Canadian Total Population", fontsize=8.5)
  axR.set_title("B. Post-Confederation Canada Expansion (1867AD-2026AD)", fontsize=9.4, pad=6)
  axR.legend(loc="upper left", fontsize=7.2, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axR, grid=True)

  fig.suptitle("Modern United States, Canada and Greenland Growth (1783AD-2026AD)", fontsize=11.0, y=0.98)
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig4_modern_us_canada_growth.png", dpi=300)
  plt.close(fig)


def render_root_fig5 ():
  """Generates Figure 5: Empirical vs fitted Matern semivariograms across domains."""
  plt.rcdefaults()
  plt.style.use("default")
  fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.6, 5.2), dpi=300)
  plt.subplots_adjust(wspace=0.18)

  dom_specs = [
    (axL, "North America", CENTAUR_DIR / "_shared/sites_northern_america/config/kriging_diagnostics.json", "#1b4f72"),
    (axR, "Hawai'i and Polynesia", CENTAUR_DIR / "_shared/sites_hawaii_polynesia/config/kriging_diagnostics.json", "#b03a2e")
  ]
  u_grid = np.linspace(0.0, 3.5, 160)

  for ax, title_lbl, diag_p, col_hex in dom_specs:
    kd = json.loads(diag_p.read_text(encoding="utf-8"))
    vms = kd.get("variogram_models", {})
    all_gammas = []
    u_ref = None
    tau1_list, tau2_list, r2_list, c0_list, c1_list, c2_list = [], [], [], [], [], []
    raw_c0_list, raw_tau1_list = [], []

    for h_i, (hk, vm) in enumerate(vms.items()):
      u_emp = np.asarray(vm.get("empirical_u_lags", []), dtype=float)
      g_emp = np.asarray(vm.get("empirical_gammas", []), dtype=float)
      if len(u_emp) > 0 and len(g_emp) == len(u_emp):
        lbl_h = "Horizon empirical bins" if h_i == 0 else None
        ax.plot(u_emp, g_emp, color=col_hex, alpha=0.22, linewidth=0.9, label=lbl_h)
        if u_ref is None:
          u_ref = u_emp
        if len(g_emp) == len(u_ref):
          all_gammas.append(g_emp)
      tau1_list.append(float(vm["tau1_dimensionless"]))
      tau2_list.append(float(vm["tau2_dimensionless"]))
      raw_tau1_list.append(float(vm.get("raw_tau1_dimensionless", vm["tau1_dimensionless"])))
      r2_list.append(float(vm["residual_r2"]))
      c0_list.append(float(vm["c0_nugget"]))
      raw_c0_list.append(float(vm.get("raw_nugget_to_sill_ratio", 0.0)))
      c1_list.append(float(vm["c1_weight"]))
      c2_list.append(float(vm["c2_weight"]))

    t1 = float(np.mean(tau1_list))
    t2 = float(np.mean(tau2_list))
    rt1 = float(np.mean(raw_tau1_list))
    c0 = float(np.mean(c0_list))
    rc0 = float(np.mean(raw_c0_list))
    c1 = float(np.mean(c1_list))
    c2 = float(np.mean(c2_list))
    r2_m = float(np.mean(r2_list))

    g_reg = _matern32_gamma(u_grid, c0, c1, c2, t1, t2)
    scale_raw = (1.0 - rc0) / max(c1 + c2, 1e-6)
    g_raw = _matern32_gamma(u_grid, rc0, c1 * scale_raw, c2 * scale_raw, rt1, t2)

    t1_tex = vpu.format_mathtext_euro(t1, 2)
    rc0_tex = vpu.format_mathtext_euro(rc0, 2)
    r2_tex = vpu.format_mathtext_euro(r2_m, 3)
    ax.plot(u_grid, g_reg, color=col_hex, linewidth=2.2, label=f"Regularised Matérn ($\\tau_1 = {t1_tex}$)")
    ax.plot(u_grid, g_raw, color="#334155", linestyle="--", linewidth=1.4, label=f"Raw catchment fit ($c_0/\\sigma^2 = {rc0_tex}$)")
    if all_gammas and u_ref is not None:
      mean_emp = np.mean(np.vstack(all_gammas), axis=0)
      ax.scatter(u_ref, mean_emp, s=26, color=col_hex, edgecolors="white", linewidths=0.6, zorder=6, label=f"Mean empirical bins ($n = {len(vms)}$)")

    ax.set_title(f"{title_lbl} ($\\nu = 3/2$, $\\tau_1 = {t1_tex}$, $R^2 = {r2_tex}$)", fontsize=9.4, pad=6)
    ax.set_xlabel("Dimensionless Voronoi geodesic lag $u_{ij}$", fontsize=8.4)
    ax.set_ylabel("Normalised semivariance $\\gamma(u)/\\sigma^2$", fontsize=8.4)
    ax.set_xlim(0.0, 3.5)
    ax.set_ylim(0.0, 1.05)
    ax.yaxis.set_major_formatter(vpu.euro_tick_formatter(1))
    ax.xaxis.set_major_formatter(vpu.euro_tick_formatter(1))
    ax.legend(loc="lower right", fontsize=6.9, frameon=True, facecolor="white")
    vpu.apply_viscount_style(ax, grid=True)

  fig.suptitle("Substrata Multi-Horizon Semivariogram Calibration Across North America and Polynesia", fontsize=11.0, y=0.98)
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig5_kriging_validation.png", dpi=300)
  plt.close(fig)


def render_chapter_fig1 (arg0_mod):
  """Generates Figure 1: projected Equal-Area chapter spatial map with .naissance borders."""
  plt.rcdefaults()
  plt.style.use("default")
  mid = arg0_mod["id"]
  feats = arg0_mod["geojson"].get("features", [])
  setts = arg0_mod["settlements"]
  byr = arg0_mod["border_year"]
  ys_dom = [int(k) for k in arg0_mod["data"]["summary"]["headline_population_by_benchmark"].keys()]
  span_str = f"({_fmt_yr(min(ys_dom))} to {_fmt_yr(max(ys_dom))})"

  if mid == "hawaii_and_american_polynesia":
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.2, 5.4), dpi=300, gridspec_kw={"width_ratios": [1.55, 1.0]})
    plt.subplots_adjust(left=0.02, right=0.98, top=0.86, bottom=0.14, wspace=0.08)
    _draw_styled_map_axis(axL, cmh.PROJ_HI, feats, byr, (-390.0, 320.0), (-240.0, 260.0))
    _place_clean_callouts(axL, setts, cmh.PROJ_HI, (-390.0, 320.0), (-240.0, 260.0), arg5_max_labels=6, arg6_min_sep_km=40.0)
    axL.set_title("A. Hawaiian Archipelago (Albers Equal-Area)", fontsize=9.0, pad=5)

    _draw_styled_map_axis(axR, cmh.PROJ_AS, feats, byr, (-125.0, 175.0), (-85.0, 95.0))
    _place_clean_callouts(axR, setts, cmh.PROJ_AS, (-125.0, 175.0), (-85.0, 95.0), arg5_max_labels=4, arg6_min_sep_km=12.0)
    axR.set_title("B. American Samoa: Tutuila and Manu'a Islands", fontsize=9.0, pad=5)
  else:
    proj = PROJ_NC if mid == "northern_cascadia_and_alaska" else (cmh.PROJ_CAN if mid in NORTHERN_CAN_IDS else cmh.PROJ_NA)
    fig, ax = plt.subplots(figsize=(12.2, 6.8), dpi=300)
    plt.subplots_adjust(left=0.025, right=0.77, top=0.90, bottom=0.05)

    use_feats = feats
    if mid == "united_states_post_independence":
      main_feats = [f for f in feats if not any(t in str(f.get("properties", {}).get("region_id", "")).lower() for t in ("hawaii", "samoa", "alaska"))]
      if main_feats:
        use_feats = main_feats
    pc, bounds = _proj_patch_collection(use_feats, proj, arg2_seg=0.22)
    if bounds is None:
      bounds = (-2500.0, -1600.0, 2500.0, 1600.0)
    xlim, ylim = _pad_bounds_for_aspect(bounds, arg1_aspect=1.55)
    _draw_styled_map_axis(ax, proj, use_feats, byr, xlim, ylim)
    _place_clean_callouts(ax, setts, proj, xlim, ylim, arg5_max_labels=6, arg6_min_sep_km=max(35.0, (xlim[1] - xlim[0]) * 0.08))

    if mid == "united_states_post_independence":
      ak_feats = [f for f in feats if "alaska" in str(f.get("properties", {}).get("region_id", "")).lower()]
      hi_feats = [f for f in feats if any(t in str(f.get("properties", {}).get("region_id", "")).lower() for t in ("hawaii", "samoa"))]
      if ak_feats:
        ax_ak = ax.inset_axes([0.015, 0.03, 0.24, 0.26])
        _draw_styled_map_axis(ax_ak, PROJ_NC, ak_feats, byr, (-2050, 1300), (-950, 1250), arg6_grats=False)
        ax_ak.set_title("Alaska", fontsize=6.4, pad=2)
      if hi_feats:
        ax_hi = ax.inset_axes([0.27, 0.03, 0.16, 0.22])
        _draw_styled_map_axis(ax_hi, cmh.PROJ_HI, hi_feats, byr, (-390, 320), (-240, 260), arg6_grats=False)
        ax_hi.set_title("Hawai'i", fontsize=6.4, pad=2)
        ax_as = ax.inset_axes([0.445, 0.03, 0.12, 0.22])
        _draw_styled_map_axis(ax_as, cmh.PROJ_AS, hi_feats, byr, (-120, 170), (-70, 70), arg6_grats=False)
        ax_as.set_title("Am. Samoa", fontsize=6.4, pad=2)

    regs = arg0_mod["data"].get("regions", {})
    col_map = {}
    for f in feats:
      pr = f.get("properties", {})
      col_map[pr.get("region_id", "")] = _rgba_to_hex(pr.get("colour"), len(col_map))
    leg_h = []
    for rk_i, (rk, rv) in enumerate(regs.items()):
      if rk_i >= 18:
        break
      leg_h.append(Patch(facecolor=col_map.get(rk, PALETTE[rk_i % len(PALETTE)]), edgecolor="#1e293b", linewidth=0.4, label=_clean_sub_label(rv.get("name", rk), 30)))
    if leg_h:
      ax.legend(handles=leg_h, loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=6.6, frameon=True, facecolor="white", title="Sub-Regions", title_fontsize=7.4)

  fig.suptitle(f"{arg0_mod['title']}: Sub-Regions and Settlements {span_str}", fontsize=11.0, y=0.96)
  vpu.save_viscount_figure(fig, arg0_mod["fig_dir"] / f"fig1_{mid}_spatial.png", dpi=300)
  plt.close(fig)


def render_chapter_fig2 (arg0_mod):
  """Generates Figure 2: total trajectory with +/- 8% interval and sub-regional curves."""
  plt.rcdefaults()
  plt.style.use("default")
  mid = arg0_mod["id"]
  hl = arg0_mod["data"]["summary"]["headline_population_by_benchmark"]
  ys = sorted(int(k) for k in hl.keys())
  tot = np.array([float(hl[str(y)]) for y in ys], dtype=float)
  ys_span = f"({_fmt_yr(ys[0])} to {_fmt_yr(ys[-1])})"

  fig, ax = plt.subplots(figsize=(11.4, 5.6), dpi=300)
  plt.subplots_adjust(left=0.08, right=0.73, top=0.90, bottom=0.12)
  ax.fill_between(ys, tot * 0.92, tot * 1.08, color="#3b82f6", alpha=0.16, label="Uncertainty envelope (+/- 8%)")
  ax.plot(ys, tot, color="#0f172a", linewidth=2.3, label="Regional total")

  regs = arg0_mod["data"].get("regions", {})
  ranked_regs = sorted(regs.items(), key=lambda kv: max((float(v) for v in kv[1].get("population", {}).values()), default=0.0), reverse=True)
  for r_i, (rk, rv) in enumerate(ranked_regs[:8]):
    pmap = rv.get("population", {})
    ry = sorted(int(k) for k in pmap.keys())
    rv_vals = [float(pmap[str(y)]) for y in ry]
    ax.plot(ry, rv_vals, linestyle="--", linewidth=1.35, color=PALETTE[r_i % len(PALETTE)], label=_clean_sub_label(rv.get("name", rk), 28))

  ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  _fmt_yr_ticks(ax, ys)
  ax.set_xlim(ys[0], ys[-1])
  ax.set_xlabel("Calendar Year", fontsize=8.6)
  ax.set_ylabel("Population", fontsize=8.6)
  ax.set_title(f"{arg0_mod['title']}: Demographic Trajectory {ys_span}", fontsize=10.2, pad=7)
  ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=7.0, frameon=True, facecolor="white")
  vpu.apply_viscount_style(ax, grid=True)
  vpu.save_viscount_figure(fig, arg0_mod["fig_dir"] / f"fig2_{mid}_trajectory.png", dpi=300)
  plt.close(fig)


def render_chapter_fig3 (arg0_mod):
  """Generates Figure 3: 100% stacked sub-regional population shares."""
  plt.rcdefaults()
  plt.style.use("default")
  mid = arg0_mod["id"]
  hl = arg0_mod["data"]["summary"]["headline_population_by_benchmark"]
  ys = sorted(int(k) for k in hl.keys())
  regs = arg0_mod["data"].get("regions", {})
  ranked_regs = sorted(regs.items(), key=lambda kv: max((float(v) for v in kv[1].get("population", {}).values()), default=0.0), reverse=True)

  top_k = ranked_regs[:8]
  series_mat = []
  lbls = []
  cols = []
  for r_i, (rk, rv) in enumerate(top_k):
    pmap = rv.get("population", {})
    series_mat.append([float(pmap.get(str(y), 0.0)) for y in ys])
    lbls.append(_clean_sub_label(rv.get("name", rk), 28))
    cols.append(PALETTE[r_i % len(PALETTE)])
  if len(ranked_regs) > 8:
    rem = np.zeros(len(ys), dtype=float)
    for _, rv in ranked_regs[8:]:
      pmap = rv.get("population", {})
      rem += np.array([float(pmap.get(str(y), 0.0)) for y in ys], dtype=float)
    series_mat.append(rem.tolist())
    lbls.append("Remaining Sub-Regions")
    cols.append("#94a3b8")

  arr = np.asarray(series_mat, dtype=float)
  col_sums = np.maximum(np.sum(arr, axis=0), 1.0)
  pcts = arr / col_sums * 100.0

  fig, ax = plt.subplots(figsize=(11.4, 5.2), dpi=300)
  plt.subplots_adjust(left=0.07, right=0.73, top=0.89, bottom=0.13)
  ax.stackplot(ys, pcts, labels=lbls, colors=cols, alpha=0.86)
  _fmt_yr_ticks(ax, ys)
  ax.set_xlim(ys[0], ys[-1])
  ax.set_ylim(0, 100)
  ax.yaxis.set_major_formatter(vpu.euro_tick_formatter(0))
  ax.set_xlabel("Calendar Year", fontsize=8.6)
  ax.set_ylabel("Share of Regional Total (%)", fontsize=8.6)
  ax.set_title(f"{arg0_mod['title']}: Sub-Regional Population Composition (%)", fontsize=10.2, pad=7)
  ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=7.0, frameon=True, facecolor="white")
  vpu.apply_viscount_style(ax, grid=True)
  vpu.save_viscount_figure(fig, arg0_mod["fig_dir"] / f"fig3_{mid}_shares.png", dpi=300)
  plt.close(fig)


def render_chapter_fig4 (arg0_mod):
  """Generates Figure 4: settlement rank-size distribution and top 12 horizontal bars."""
  plt.rcdefaults()
  plt.style.use("default")
  mid = arg0_mod["id"]
  setts = arg0_mod["settlements"]
  ranked = []
  for s in setts:
    pops = s.get("population") or {}
    pk = max((float(v) for v in pops.values()), default=0.0)
    if pk > 0:
      ranked.append((pk, str(s.get("name", ""))))
  ranked.sort(key=lambda t: (-t[0], t[1]))

  fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.8, 5.4), dpi=300, gridspec_kw={"width_ratios": [1.0, 1.25]})
  plt.subplots_adjust(left=0.07, right=0.97, top=0.86, bottom=0.13, wspace=0.42)

  if ranked:
    ranks = np.arange(1, len(ranked) + 1, dtype=float)
    vals = np.array([r[0] for r in ranked], dtype=float)
    axL.loglog(ranks, vals, "o", markersize=3.8, color="#1b4f72", alpha=0.8)
  axL.set_xlabel("Settlement Rank (log)", fontsize=8.4)
  axL.set_ylabel("Peak Population (log)", fontsize=8.4)
  axL.set_title("A. Rank-Size Distribution", fontsize=9.2, pad=6)
  vpu.apply_viscount_style(axL, grid=True)

  top12 = ranked[:12][::-1]
  if top12:
    y_pos = np.arange(len(top12))
    bar_v = [r[0] for r in top12]
    bar_l = [_clean_sub_label(r[1], 24) for r in top12]
    axR.barh(y_pos, bar_v, height=0.68, color="#239b56", alpha=0.85, edgecolor="#145a32", linewidth=0.4)
    axR.set_yticks(y_pos)
    axR.set_yticklabels(bar_l, fontsize=7.2)
  axR.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  axR.set_xlabel("Peak Population", fontsize=8.4)
  axR.set_title("B. Leading 12 Catalogued Settlements", fontsize=9.2, pad=6)
  vpu.apply_viscount_style(axR, grid=True)

  fig.suptitle(f"{arg0_mod['title']}: Settlement Hierarchy (n={vpu.format_euro_number(len(setts), 0)})", fontsize=10.8, y=0.96)
  vpu.save_viscount_figure(fig, arg0_mod["fig_dir"] / f"fig4_{mid}_settlements.png", dpi=300)
  plt.close(fig)


def main ():
  """Renders all 5 CENTAUR root figures and 124 chapter figures across 31 modules."""
  ROOT_FIG_DIR.mkdir(parents=True, exist_ok=True)
  mods = _load_modules()
  print(f"[generate_centaur_figures] Rendering root figures for {len(mods)} CENTAUR modules...")
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
