# -*- coding: utf-8 -*-
"""Generate POLARIS-calibre Equal-Area vector maps, raster kriging mosaics and
zero-occlusion diagnostic figures for Project CASTLE (4 root + 52 chapter PNGs).
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
from matplotlib.patches import Patch, Polygon as MplPolygon
from matplotlib.ticker import FuncFormatter
import numpy as np
from shapely.geometry import box, shape
from shapely.ops import unary_union

CASTLE_DIR = pathlib.Path(__file__).resolve().parent
SHARED_DIR = CASTLE_DIR.parent / "_shared"
GIS_DIR = CASTLE_DIR / "_shared" / "_gis_cache"
SUBREG_DIR = GIS_DIR / "chapter_subregions"
ROOT_FIG_DIR = CASTLE_DIR / "figures"

for p_str in (str(SHARED_DIR), str(GIS_DIR)):
  if p_str not in sys.path:
    sys.path.insert(0, p_str)

import castle_map_helper as cmh
import viscount_plot_utils as vpu

JAPAN_IDS = {
  "yayoi_and_kofun_japan",
  "nara_heian_and_feudal_japan",
  "tokugawa_japan_ryukyu_and_ezo",
  "meiji_and_imperial_japan",
  "japan_after_1945"
}

KOREA_IDS = {
  "gojoseon_commanderies_and_three_kingdoms",
  "unified_silla_and_goryeo_korea",
  "joseon_korea",
  "korea_under_japanese_occupation",
  "korean_division_and_korean_war",
  "south_korea_after_1953",
  "north_korea_after_1953"
}

PALETTE = [
  "#2b5c8f", "#c05246", "#3d8a5a", "#85529e", "#c9842c",
  "#4784b3", "#a43f37", "#2d9281", "#784c8f", "#b05a28",
  "#5294c4", "#cf5d4e", "#4da672", "#9b6ab5", "#c4a337"
]

MOD_META = {
  "prehistoric_and_food_gathering_korea_and_japan": "Prehistoric Korea and Japan (Jomon, Chulmun and Ainu)",
  "yayoi_and_kofun_japan": "Yayoi and Kofun Japan",
  "gojoseon_commanderies_and_three_kingdoms": "Gojoseon, Commanderies and Three Kingdoms of Korea",
  "unified_silla_and_goryeo_korea": "Unified Silla and Goryeo Korea",
  "nara_heian_and_feudal_japan": "Nara, Heian and Feudal Japan",
  "joseon_korea": "Joseon Korea up to Japanese Annexation",
  "tokugawa_japan_ryukyu_and_ezo": "Tokugawa Japan, Ryukyu and Ezo",
  "meiji_and_imperial_japan": "Meiji Restoration and Imperial Japan",
  "korea_under_japanese_occupation": "Korea Under Japanese Occupation",
  "korean_division_and_korean_war": "Korean Division and the Korean War",
  "japan_after_1945": "Japan After 1945",
  "south_korea_after_1953": "South Korea After 1953",
  "north_korea_after_1953": "North Korea After 1953"
}

JP_MACRO_REGIONS = [
  ("Hokkaido", "#4784b3", {"jp_hokkaido"}),
  ("Tohoku", "#3d8a5a", {"jp_aomori", "jp_iwate", "jp_miyagi", "jp_akita", "jp_yamagata", "jp_fukushima"}),
  ("Kanto", "#c05246", {"jp_ibaraki", "jp_tochigi", "jp_gunma", "jp_saitama", "jp_chiba", "jp_tokyo", "jp_kanagawa"}),
  ("Chubu", "#c9842c", {"jp_niigata", "jp_toyama", "jp_ishikawa", "jp_fukui", "jp_yamanashi", "jp_nagano", "jp_gifu", "jp_shizuoka", "jp_aichi"}),
  ("Kansai", "#85529e", {"jp_mie", "jp_shiga", "jp_kyoto", "jp_osaka", "jp_hyogo", "jp_nara", "jp_wakayama"}),
  ("Chugoku", "#2d9281", {"jp_tottori", "jp_shimane", "jp_okayama", "jp_hiroshima", "jp_yamaguchi"}),
  ("Shikoku", "#b05a28", {"jp_tokushima", "jp_kagawa", "jp_ehime", "jp_kochi"}),
  ("Kyushu and Okinawa", "#2b5c8f", {"jp_fukuoka", "jp_saga", "jp_nagasaki", "jp_kumamoto", "jp_oita", "jp_miyazaki", "jp_kagoshima", "jp_okinawa"})
]

JP_PREF_TO_MACRO_COL = {}
for _mlbl, _mcol, _mkeys in JP_MACRO_REGIONS:
  for _mk in _mkeys:
    JP_PREF_TO_MACRO_COL[_mk] = _mcol

MAIN_JAPAN_CLIP = box(128.0, 29.8, 147.0, 46.2)
RYUKYU_CLIP = box(122.0, 23.5, 132.0, 30.2)


def _fmt_yr (arg0_yr):
  """Formats integer year cleanly in British historical convention."""
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
      step = 500 if span >= 3000 else (100 if span >= 600 else (50 if span >= 250 else (20 if span >= 80 else (10 if span >= 30 else 2))))
      cand = int(round(raw_t / step) * step)
      if min(abs(cand - c) for c in chosen) >= 0.16 * span:
        chosen.append(cand)
    chosen = sorted(set(chosen))
  arg0_ax.set_xticks(chosen)
  arg0_ax.set_xticklabels([_fmt_yr(y) for y in chosen], fontsize=7.5)


def _clean_sub_label (arg0_name, arg1_max_len=30):
  """Formats sub-region or settlement labels cleanly without harsh mid-word clipping."""
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
  """Evaluates normalised two-component Matern 3/2 semivariogram."""
  r3 = math.sqrt(3.0)
  u = np.maximum(np.asarray(arg0_u, dtype=float), 0.0)
  a1 = r3 * u / max(float(arg4_tau1), 1e-6)
  a2 = r3 * u / max(float(arg5_tau2), 1e-6)
  corr = float(arg2_c1) * (1.0 + a1) * np.exp(-a1) + float(arg3_c2) * (1.0 + a2) * np.exp(-a2)
  return np.where(u <= 1e-12, 0.0, float(arg1_c0) + (1.0 - float(arg1_c0)) * np.maximum(0.0, 1.0 - corr))


def _compute_headline_series (arg0_regions):
  """Aggregates benchmark totals across all sub-regions in a chapter."""
  all_yrs = sorted({int(k) for rv in arg0_regions.values() for k in (rv.get("population") or {}).keys()})
  out = {}
  for y in all_yrs:
    tot_y = 0.0
    for rv in arg0_regions.values():
      pm = rv.get("population") or {}
      ks = sorted(int(k) for k in pm.keys())
      if not ks:
        continue
      if str(y) in pm:
        tot_y += float(pm[str(y)])
      elif ks[0] <= y <= ks[-1]:
        tot_y += float(np.interp(y, ks, [float(pm[str(k)]) for k in ks]))
    out[y] = tot_y
  return out


def _load_modules ():
  """Loads all 13 CASTLE chapter manifests, JSON5 regional series, gazetteers and vectors."""
  cfg = json5.loads((CASTLE_DIR / "castle_areal_masks.json5").read_text(encoding="utf-8"))
  mods = list(cfg.get("specialist_masks", [])) + list(cfg.get("national_epoch_masks", []))
  out = []
  for m in mods:
    mid = m["id"]
    j5_rel = pathlib.Path(m["json5_path"])
    j5_abs = CASTLE_DIR.parents[3] / j5_rel if j5_rel.parts[0] == "histmap" else CASTLE_DIR / j5_rel
    ch_dir = j5_abs.parent
    set_p = ch_dir / f"{mid}_settlements.json"
    gj_p = SUBREG_DIR / f"{mid}_subregions.geojson"
    data = json5.loads(j5_abs.read_text(encoding="utf-8"))
    out.append({
      "id": mid,
      "title": MOD_META.get(mid, data.get("title", mid)),
      "dir": ch_dir,
      "fig_dir": ch_dir / "figures",
      "data": data,
      "headline": _compute_headline_series(data.get("regions", {})),
      "settlements": json.loads(set_p.read_text(encoding="utf-8")) if set_p.exists() else {},
      "geojson": json.loads(gj_p.read_text(encoding="utf-8")) if gj_p.exists() else {"features": []}
    })
  return out


def _build_vector_patches (arg0_features, arg1_proj, arg2_seg=0.14, arg3_color_fn=None, arg4_clip_box=None):
  """Projects pure vector GeoJSON polygons into muted POLARIS PatchCollections and union outline."""
  patches_list, cols_list, raw_geoms = [], [], []
  xs_all, ys_all = [], []
  for idx, feat in enumerate(arg0_features):
    geom = feat.get("geometry")
    if not geom:
      continue
    g_raw = shape(geom)
    pg = cmh.clip_and_project(g_raw, arg1_proj, arg2_seg, arg4_clip_box)
    ps = cmh.geom_to_patches(pg)
    if not ps:
      continue
    raw_geoms.append(g_raw)
    if arg3_color_fn is not None:
      c_hex = arg3_color_fn(feat, idx)
    else:
      props = feat.get("properties", {})
      c_hex = cmh.mute_rgb_hex(props.get("rgb") or props.get("colour"), idx, arg2_blend=0.44)
    for p in ps:
      xy = p.get_xy()
      if len(xy) >= 3:
        xs_all.extend([float(xy[:, 0].min()), float(xy[:, 0].max())])
        ys_all.extend([float(xy[:, 1].min()), float(xy[:, 1].max())])
        patches_list.append(MplPolygon(xy, closed=True))
        cols_list.append(c_hex)
  if not patches_list:
    return None, None, None
  pc = PatchCollection(patches_list, facecolor=cols_list, edgecolor="#334155", linewidths=0.38, alpha=0.82, zorder=2.5)
  env_pc = None
  try:
    env_g = cmh.clip_and_project(unary_union([g.buffer(0) for g in raw_geoms]), arg1_proj, arg2_seg, arg4_clip_box)
    eps = cmh.geom_to_patches(env_g)
    if eps:
      env_pc = PatchCollection(eps, facecolor="none", edgecolor="#111827", linewidths=0.80, zorder=3.8)
  except Exception:
    env_pc = None
  bounds = (min(xs_all), min(ys_all), max(xs_all), max(ys_all))
  return pc, env_pc, bounds


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
    short = str(s.get("name", "")).strip()
    if len(short) > 18:
      short = short[:15] + "..."
    lbl = f"{short} ({vpu.format_semantic_population(pk)})"
    out.append((pk, lbl, lon, lat, px, py))
  out.sort(key=lambda t: (-t[0], t[1]))
  return out


def _draw_panel_map (arg0_fig, arg1_ax, arg2_proj, arg3_feats, arg4_xlim, arg5_ylim, arg6_setts=None, arg7_max_lbl=8, arg8_color_fn=None, arg9_is_dense=False, arg10_scope="castle", arg11_clip_box=None):
  """Renders vector basemap, sub-region polygons, graticule and callouts."""
  cmh.draw_basemap(arg1_ax, arg2_proj)
  pc, env_pc, _ = _build_vector_patches(arg3_feats, arg2_proj, arg3_color_fn=arg8_color_fn, arg4_clip_box=arg11_clip_box)
  if pc is not None:
    arg1_ax.add_collection(pc)
  if env_pc is not None:
    arg1_ax.add_collection(env_pc)
  arg1_ax.set_xlim(*arg4_xlim)
  arg1_ax.set_ylim(*arg5_ylim)
  arg1_ax.set_aspect("equal", adjustable="box")
  arg1_ax.set_xticks([])
  arg1_ax.set_yticks([])
  if arg10_scope == "korea":
    lats_g, lons_g = [34, 36, 38, 40, 42], [125, 127, 129]
  elif arg10_scope == "japan":
    lats_g, lons_g = [32, 36, 40, 44], [130, 135, 140, 145]
  else:
    lats_g, lons_g = [26, 32, 38, 44], [125, 131, 137, 143]
  cmh.draw_inline_graticule(arg1_ax, arg2_proj, arg4_xlim, arg5_ylim, lats_g, lons_g)
  vpu.apply_viscount_style(arg1_ax)

  if arg6_setts:
    ranked = _rank_setts_in_bounds(arg6_setts, arg2_proj, arg4_xlim, arg5_ylim)
    if ranked:
      pt_sz = 2.0 if arg9_is_dense else 7.2
      pt_al = 0.28 if arg9_is_dense else 0.74
      arg1_ax.scatter(
        [r[4] for r in ranked], [r[5] for r in ranked],
        s=pt_sz, c="#1e293b", edgecolors="none" if arg9_is_dense else "white",
        linewidths=0.0 if arg9_is_dense else 0.35, alpha=pt_al, zorder=6.2
      )
      items = [(r[1], r[2], r[3]) for r in ranked[:48]]
      cmh.place_bbox_callouts(
        arg0_fig, arg1_ax, items, arg2_proj, arg4_xlim, arg5_ylim,
        arg6_max_labels=arg7_max_lbl, arg7_min_sep_px=42.0, arg8_fontsize=6.3
      )


def _draw_ryukyu_inset (arg0_ax, arg1_feats, arg2_color_fn=None):
  """Adds a clean framed Equal-Area inset for the Ryukyu Archipelago (Okinawa & Sakishima) in the Pacific corner."""
  iax = arg0_ax.inset_axes([0.72, 0.04, 0.25, 0.36])
  cmh.draw_basemap(iax, cmh.PROJ_RYUKYU, arg2_clip_box=RYUKYU_CLIP)
  pc_r, env_r, bnd_r = _build_vector_patches(arg1_feats, cmh.PROJ_RYUKYU, arg2_seg=0.10, arg3_color_fn=arg2_color_fn, arg4_clip_box=RYUKYU_CLIP)
  if pc_r is not None:
    iax.add_collection(pc_r)
  if env_r is not None:
    iax.add_collection(env_r)
  if bnd_r is not None:
    xl_r, yl_r = vpu.pad_projected_bounds(bnd_r, arg1_target_aspect=1.12, arg2_pad_factor=1.22, arg3_min_span_km=380.0)
  else:
    xl_r, yl_r = (-460.0, 460.0), (-380.0, 380.0)
  iax.set_xlim(*xl_r)
  iax.set_ylim(*yl_r)
  iax.set_aspect("equal", adjustable="box")
  iax.set_xticks([])
  iax.set_yticks([])
  for sp in iax.spines.values():
    sp.set_edgecolor("#334155")
    sp.set_linewidth(0.8)
  iax.set_title("Ryukyu / Okinawa Inset", fontsize=6.6, pad=2.5, backgroundcolor="white")
  return iax


def render_root_fig1 (arg0_mods):
  """Generates Root Figure 1: four-epoch Equal-Area CASTLE macro-regional coverage."""
  plt.rcdefaults()
  plt.style.use("default")
  by_id = {m["id"]: m for m in arg0_mods}
  fig, axes = plt.subplots(2, 2, figsize=(14.4, 10.6), dpi=300)
  plt.subplots_adjust(left=0.02, right=0.98, top=0.91, bottom=0.05, wspace=0.04, hspace=0.14)

  xlim_c = (-1250.0, 1280.0)
  ylim_c = (-1380.0, 1080.0)

  panels_cfg = [
    ("A. Prehistoric, Yayoi-Kofun and Three Kingdoms (10000BC-668AD)", [
      ("Yayoi and Kofun Japan (10 basins)", "#2b5c8f", "yayoi_and_kofun_japan"),
      ("Gojoseon and Three Kingdoms Korea (8 zones)", "#c05246", "gojoseon_commanderies_and_three_kingdoms")
    ]),
    ("B. Nara-Heian-Feudal Japan, Silla and Goryeo (650AD-1603AD)", [
      ("Nara, Heian and Feudal Circuits (10 zones)", "#3d8a5a", "nara_heian_and_feudal_japan"),
      ("Unified Silla and Goryeo Provinces (9 zones)", "#c9842c", "unified_silla_and_goryeo_korea")
    ]),
    ("C. Tokugawa Bakuhan, Joseon and Colonial Eras (1392AD-1945AD)", [
      ("Tokugawa Circuits, Ryukyu and Ezo (10 zones)", "#85529e", "tokugawa_japan_ryukyu_and_ezo"),
      ("Joseon Eight Provinces (8 zones)", "#2d9281", "joseon_korea")
    ]),
    ("D. Contemporary Japan, South Korea and North Korea (1945AD-2026AD)", [
      ("Japan Prefectures (47 units)", "#2b5c8f", "japan_after_1945"),
      ("South Korea Provinces and Metros (17 units)", "#3d8a5a", "south_korea_after_1953"),
      ("North Korea Provinces and Pyongyang (11 units)", "#c05246", "north_korea_after_1953")
    ])
  ]

  for idx, (ptitle, grp_list) in enumerate(panels_cfg):
    ax = axes[idx // 2, idx % 2]
    cmh.draw_basemap(ax, cmh.PROJ_CASTLE)
    leg_h = []
    for glbl, ghex, gid in grp_list:
      if gid in by_id:
        ps_g = []
        for f in by_id[gid]["geojson"].get("features", []):
          if f.get("geometry"):
            ps_g.extend(cmh.geom_to_patches(cmh.clip_and_project(shape(f["geometry"]), cmh.PROJ_CASTLE, 0.16)))
        if ps_g:
          ax.add_collection(
            PatchCollection(
              [MplPolygon(p.get_xy(), closed=True) for p in ps_g],
              facecolor=ghex, edgecolor="#1e293b", linewidths=0.28, alpha=0.72, zorder=2.5
            )
          )
      leg_h.append(Patch(facecolor=ghex, edgecolor="#1e293b", linewidth=0.45, label=glbl))
    ax.set_xlim(*xlim_c)
    ax.set_ylim(*ylim_c)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend(handles=leg_h, loc="lower right", fontsize=6.5, frameon=True, facecolor="white", edgecolor="#94a3b8", framealpha=0.95)
    cmh.draw_inline_graticule(ax, cmh.PROJ_CASTLE, xlim_c, ylim_c, [26, 32, 38, 44], [125, 131, 137, 143])
    vpu.apply_viscount_style(ax)
    ax.set_title(ptitle, fontsize=8.8, pad=5)

  fig.suptitle("Korea and Japan Spatial Regimes Across Four Historical Epochs (10000BC-2026AD)", fontsize=11.6, y=0.965)
  cmh.verify_zero_text_overlaps(fig, "root_fig1")
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig1_castle_macro_zones.png", 300)
  plt.close(fig)


def render_root_fig2 (arg0_mods):
  """Generates Root Figure 2: long-run demographic trajectories for Japan and Korea."""
  plt.rcdefaults()
  plt.style.use("default")
  by_id = {m["id"]: m for m in arg0_mods}
  fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.4, 5.6), dpi=300)
  plt.subplots_adjust(left=0.07, right=0.97, top=0.86, bottom=0.14, wspace=0.22)

  jp_seq = [
    ("yayoi_and_kofun_japan", "Yayoi and Kofun (250BC-650AD)", "#2b5c8f"),
    ("nara_heian_and_feudal_japan", "Nara, Heian and Feudal (650AD-1603AD)", "#3d8a5a"),
    ("tokugawa_japan_ryukyu_and_ezo", "Tokugawa, Ryukyu and Ezo (1603AD-1868AD)", "#85529e"),
    ("meiji_and_imperial_japan", "Meiji and Imperial Japan (1868AD-1945AD)", "#c05246"),
    ("japan_after_1945", "Modern Japan (1945AD-2026AD)", "#0f172a")
  ]
  for mid, lbl, col in jp_seq:
    if mid not in by_id:
      continue
    hl = by_id[mid]["headline"]
    ys = sorted(hl.keys())
    vs = [hl[y] for y in ys]
    if ys:
      axL.plot(ys, vs, color=col, linewidth=2.0, label=lbl)
  axL.set_yscale("log")
  vpu.apply_human_log_ticks(axL, "y", True)
  _fmt_yr_ticks(axL, [-250, 250, 750, 1250, 1750, 2026])
  axL.set_xlim(-300, 2050)
  axL.set_xlabel("Calendar Year", fontsize=8.5)
  axL.set_ylabel("Total Population (log scale)", fontsize=8.5)
  axL.set_title("A. Japanese Archipelago Trajectory (250BC-2026AD)", fontsize=9.2, pad=6)
  axL.legend(loc="lower right", fontsize=6.5, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axL)
  axL.grid(True, linestyle=":", alpha=0.45)

  kr_seq = [
    ("gojoseon_commanderies_and_three_kingdoms", "Gojoseon and Three Kingdoms (250BC-668AD)", "#2b5c8f"),
    ("unified_silla_and_goryeo_korea", "Unified Silla and Goryeo (668AD-1392AD)", "#3d8a5a"),
    ("joseon_korea", "Joseon Korea (1392AD-1910AD)", "#c9842c"),
    ("korea_under_japanese_occupation", "Colonial Korea (1905AD-1945AD)", "#85529e"),
    ("korean_division_and_korean_war", "Division and Korean War (1945AD-1953AD)", "#2d9281"),
    ("south_korea_after_1953", "South Korea (1953AD-2026AD)", "#0f172a"),
    ("north_korea_after_1953", "North Korea (1953AD-2026AD)", "#c05246")
  ]
  for mid, lbl, col in kr_seq:
    if mid not in by_id:
      continue
    hl = by_id[mid]["headline"]
    ys = sorted(hl.keys())
    vs = [hl[y] for y in ys]
    if ys:
      axR.plot(ys, vs, color=col, linewidth=2.0, label=lbl)
  axR.set_yscale("log")
  vpu.apply_human_log_ticks(axR, "y", True)
  _fmt_yr_ticks(axR, [-250, 250, 750, 1250, 1750, 2026])
  axR.set_xlim(-300, 2050)
  axR.set_xlabel("Calendar Year", fontsize=8.5)
  axR.set_ylabel("Total Population (log scale)", fontsize=8.5)
  axR.set_title("B. Korean Peninsula Trajectory (250BC-2026AD)", fontsize=9.2, pad=6)
  axR.legend(loc="lower right", fontsize=6.4, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axR)
  axR.grid(True, linestyle=":", alpha=0.45)

  fig.suptitle("Japan and Korea Long-Run Demographic Trajectories (250BC-2026AD)", fontsize=11.0, y=0.97)
  cmh.verify_zero_text_overlaps(fig, "root_fig2")
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig2_castle_long_run_trajectory.png", 300)
  plt.close(fig)


def render_root_fig3 ():
  """Generates Root Figure 3: 4-panel POLARIS-style kriging and semivariogram mosaic."""
  plt.rcdefaults()
  plt.style.use("default")
  fig, axes = plt.subplots(2, 2, figsize=(14.4, 10.6), dpi=300)
  plt.subplots_adjust(left=0.03, right=0.97, top=0.91, bottom=0.07, wspace=0.11, hspace=0.22)
  xlim_c = (-1250.0, 1280.0)
  ylim_c = (-1380.0, 1080.0)

  # Panel A: Observation catchments & cross-frontier conditioning belt
  axA = axes[0, 0]
  cmh.draw_basemap(axA, cmh.PROJ_CASTLE)
  gj_p = CASTLE_DIR / "_shared/sites_korea_japan/geojson/00_all_periods.geojson"
  gj = json.loads(gj_p.read_text(encoding="utf-8"))
  dom_x, dom_y, buf_x, buf_y = [], [], [], []
  for f in gj.get("features", []):
    g = f.get("geometry")
    if not g:
      continue
    rep = shape(g).representative_point()
    px, py = cmh.PROJ_CASTLE.fwd_pt(rep.x, rep.y)
    if xlim_c[0] <= px <= xlim_c[1] and ylim_c[0] <= py <= ylim_c[1]:
      if f.get("properties", {}).get("is_frontier_buffer"):
        buf_x.append(px)
        buf_y.append(py)
      else:
        dom_x.append(px)
        dom_y.append(py)
  if dom_x:
    axA.scatter(dom_x, dom_y, s=6.5, c="#2b5c8f", alpha=0.76, edgecolors="none", zorder=5.0, label=f"Domestic catchments (n={vpu.format_euro_number(len(dom_x), 0)})")
  if buf_x:
    axA.scatter(buf_x, buf_y, s=8.0, c="#c9842c", alpha=0.88, edgecolors="none", zorder=5.5, label=f"Cross-frontier buffers (n={vpu.format_euro_number(len(buf_x), 0)})")
  axA.set_xlim(*xlim_c)
  axA.set_ylim(*ylim_c)
  axA.set_aspect("equal", adjustable="box")
  axA.set_xticks([])
  axA.set_yticks([])
  axA.legend(loc="lower right", fontsize=6.6, frameon=True, facecolor="white", framealpha=0.96)
  cmh.draw_inline_graticule(axA, cmh.PROJ_CASTLE, xlim_c, ylim_c, [26, 32, 38, 44], [125, 131, 137, 143])
  vpu.apply_viscount_style(axA)
  axA.set_title("A. Archaeological Catchments and 300 km Frontier Belt", fontsize=9.0, pad=5)

  # Panel B: Kofun & Three Kingdoms Kriged Intensity Raster (Horizon 05)
  axB = axes[0, 1]
  cmh.draw_basemap(axB, cmh.PROJ_CASTLE, arg3_dark=True)
  krig_p = CASTLE_DIR / "_shared/sites_korea_japan/1.kriged_rasters/05_kofun_three_kingdoms_h5.png"
  if krig_p.exists():
    rk_f32 = cmh.load_f32_raster(krig_p)
    grid_k = cmh.reproject_f32_raster(rk_f32, cmh.PROJ_CASTLE, xlim_c, ylim_c, arg4_width_px=960, arg5_height_px=760)
    pos_k = grid_k[grid_k > 0.0]
    hi_k = max(0.5, float(np.percentile(pos_k, 99.6))) if pos_k.size > 0 else 10.0
    lo_k = max(0.05, hi_k * 5e-3)
    grid_k_m = np.ma.masked_where(grid_k <= 0.0, np.clip(grid_k, lo_k, hi_k))
    imB = axB.imshow(grid_k_m, extent=[xlim_c[0], xlim_c[1], ylim_c[0], ylim_c[1]], origin="upper", cmap="magma", norm=LogNorm(vmin=lo_k, vmax=hi_k), alpha=0.92, zorder=3.5)
    caxB = axB.inset_axes([0.56, 0.075, 0.38, 0.042])
    cbB = fig.colorbar(imB, cax=caxB, orientation="horizontal", format=vpu.euro_log_formatter(False))
    vpu.apply_human_colorbar_ticks(cbB, False)
    cbB.outline.set_edgecolor("#e2e8f0")
    cbB.ax.tick_params(labelsize=6.0, colors="white")
    caxB.set_title("Kriged Intensity (Horizon 5)", fontsize=6.4, pad=2, color="white")
  axB.set_xlim(*xlim_c)
  axB.set_ylim(*ylim_c)
  axB.set_aspect("equal", adjustable="box")
  axB.set_xticks([])
  axB.set_yticks([])
  cmh.draw_inline_graticule(axB, cmh.PROJ_CASTLE, xlim_c, ylim_c, [26, 32, 38, 44], [125, 131, 137, 143])
  cmh.place_bbox_callouts(
    fig, axB,
    [("Nara", 135.80, 34.68), ("Gyeongju", 129.22, 35.85), ("Pyongyang", 125.76, 39.03), ("Hanseong", 126.98, 37.56), ("Fukuoka", 130.40, 33.59)],
    cmh.PROJ_CASTLE, xlim_c, ylim_c, arg6_max_labels=5, arg7_min_sep_px=45.0, arg8_fontsize=6.0
  )
  vpu.apply_viscount_style(axB)
  axB.set_title("B. Kofun and Three Kingdoms Kriged Surface (450AD)", fontsize=9.0, pad=5)

  # Panel C: Reconstructed Benchmark Population Density (1850AD)
  axC = axes[1, 0]
  cmh.draw_basemap(axC, cmh.PROJ_CASTLE, arg3_dark=True)
  pop_p = CASTLE_DIR / "_shared/sites_korea_japan/2.population_rasters/popc_1850.png"
  if pop_p.exists():
    vp_f32 = cmh.load_f32_raster(pop_p)
    grid_v = cmh.reproject_f32_raster(vp_f32, cmh.PROJ_CASTLE, xlim_c, ylim_c, arg4_width_px=960, arg5_height_px=760)
    pos_v = grid_v[grid_v > 0.0]
    hi_v = max(100.0, float(np.percentile(pos_v, 99.5))) if pos_v.size > 0 else 8000.0
    lo_v = max(1.0, hi_v * 1e-3)
    grid_v_m = np.ma.masked_where(grid_v <= 0.0, np.clip(grid_v, lo_v, hi_v))
    imC = axC.imshow(grid_v_m, extent=[xlim_c[0], xlim_c[1], ylim_c[0], ylim_c[1]], origin="upper", cmap="viridis", norm=LogNorm(vmin=lo_v, vmax=hi_v), alpha=0.92, zorder=3.5)
    caxC = axC.inset_axes([0.56, 0.075, 0.38, 0.042])
    cbC = fig.colorbar(imC, cax=caxC, orientation="horizontal", format=vpu.euro_log_formatter(True))
    vpu.apply_human_colorbar_ticks(cbC, True)
    cbC.outline.set_edgecolor("#e2e8f0")
    cbC.ax.tick_params(labelsize=6.0, colors="white")
    caxC.set_title("Inhabitants per 5' Cell (1850AD)", fontsize=6.4, pad=2, color="white")
  axC.set_xlim(*xlim_c)
  axC.set_ylim(*ylim_c)
  axC.set_aspect("equal", adjustable="box")
  axC.set_xticks([])
  axC.set_yticks([])
  cmh.draw_inline_graticule(axC, cmh.PROJ_CASTLE, xlim_c, ylim_c, [26, 32, 38, 44], [125, 131, 137, 143])
  cmh.place_bbox_callouts(
    fig, axC,
    [("Edo", 139.69, 35.69), ("Kyoto", 135.77, 35.01), ("Hanseong", 126.98, 37.56), ("Pyongyang", 125.76, 39.03), ("Naha", 127.68, 26.21)],
    cmh.PROJ_CASTLE, xlim_c, ylim_c, arg6_max_labels=5, arg7_min_sep_px=45.0, arg8_fontsize=6.0
  )
  vpu.apply_viscount_style(axC)
  axC.set_title("C. Reconstructed Rural Population Surface (1850AD)", fontsize=9.0, pad=5)

  # Panel D: Multi-Horizon Empirical Semivariograms & Fitted Matern Models
  axD = axes[1, 1]
  u_grid = np.linspace(0.0, 14.0, 260)
  kd = json.loads((CASTLE_DIR / "_shared/sites_korea_japan/config/kriging_diagnostics.json").read_text(encoding="utf-8"))
  vms = kd.get("variogram_models", {})
  emps, u_ref = [], None
  t1s, t2s, nts_l, c1s, c2s, r2s = [], [], [], [], [], []
  for h_k, vm in vms.items():
    ue = np.asarray(vm.get("empirical_u_lags", []), dtype=float)
    ge = np.asarray(vm.get("empirical_gammas", []), dtype=float)
    if len(ue) > 0 and len(ge) == len(ue):
      sill_h = float(np.mean(ge[-min(2, len(ge)):]))
      ge_n = ge / max(sill_h, 1e-9)
      axD.plot(ue, ge_n, color="#2b5c8f", alpha=0.22, linewidth=0.9)
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
  axD.plot(u_grid, g_fit, color="#c05246", linewidth=2.2, label=f"Matérn ($\\nu = 3/2$, $\\tau_1 = {t1x}$, $R^2 = {r2x}$)")
  if emps and u_ref is not None:
    axD.scatter(u_ref, np.mean(np.vstack(emps), axis=0), s=28, color="#2b5c8f", edgecolors="white", linewidths=0.5, zorder=6, label=f"Mean empirical bins ($n = {len(vms)}$ horizons)")

  axD.set_xlabel("Dimensionless catchment geodesic lag $u_{ij}$", fontsize=8.4)
  axD.set_ylabel("Normalised semivariance $\\gamma(u)/\\sigma^2$", fontsize=8.4)
  axD.set_xlim(0.0, 14.0)
  axD.set_ylim(0.0, 1.18)
  axD.xaxis.set_major_formatter(vpu.euro_tick_formatter(0))
  axD.yaxis.set_major_formatter(vpu.euro_tick_formatter(1))
  axD.legend(loc="lower right", fontsize=6.8, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axD)
  axD.grid(True, linestyle=":", alpha=0.45)
  axD.set_title("D. Multi-Horizon Semivariograms and Matérn Fits", fontsize=9.0, pad=5)

  fig.suptitle("Korea and Japan Substrata Kriging, Rural Density Surface and Semivariogram Mosaic", fontsize=11.4, y=0.965)
  cmh.verify_zero_text_overlaps(fig, "root_fig3")
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig3_castle_kriging_diagnostics.png", 300)
  plt.close(fig)


def render_root_fig4 (arg0_mods):
  """Generates Root Figure 4: pan-CASTLE rank-size evolution and leading 15 modern urban centres."""
  plt.rcdefaults()
  plt.style.use("default")
  by_id = {m["id"]: m for m in arg0_mods}
  fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.4, 5.8), dpi=300, gridspec_kw={"width_ratios": [1.0, 1.25]})
  plt.subplots_adjust(left=0.07, right=0.97, top=0.85, bottom=0.14, wspace=0.42)

  epoch_curves = [
    ("nara_heian_and_feudal_japan", "Nara-Feudal Japan (650AD-1603AD)", "#3d8a5a"),
    ("tokugawa_japan_ryukyu_and_ezo", "Tokugawa Japan (1603AD-1868AD)", "#85529e"),
    ("joseon_korea", "Joseon Korea (1392AD-1910AD)", "#c9842c"),
    ("japan_after_1945", "Modern Japan (1945AD-2026AD)", "#2b5c8f"),
    ("south_korea_after_1953", "Modern South Korea (1953AD-2026AD)", "#c05246"),
    ("north_korea_after_1953", "Modern North Korea (1953AD-2026AD)", "#2d9281")
  ]
  for mid, lbl, col in epoch_curves:
    if mid not in by_id:
      continue
    s_vals = sorted(
      [max((float(v) for v in (s.get("population") or {}).values()), default=0.0) for s in by_id[mid]["settlements"].values()],
      reverse=True
    )
    s_vals = [v for v in s_vals if v > 0]
    if len(s_vals) >= 25:
      axL.loglog(np.arange(1, len(s_vals) + 1, dtype=float), s_vals, linewidth=1.8, color=col, label=f"{lbl} ($n={vpu.format_euro_number(len(s_vals), 0)}$)")
  vpu.apply_human_log_ticks(axL, "both", True)
  axL.set_ylim(300.0, 2.5e7)
  axL.set_xlabel("Settlement Rank (log)", fontsize=8.4)
  axL.set_ylabel("Peak Urban Population (log)", fontsize=8.4)
  axL.set_title("A. Rank-Size Evolution Across Six Regimes", fontsize=9.2, pad=5)
  axL.legend(loc="lower left", fontsize=6.1, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axL)
  axL.grid(True, linestyle=":", alpha=0.45)

  modern_peaks = {}
  for mid in ("japan_after_1945", "south_korea_after_1953", "north_korea_after_1953"):
    if mid not in by_id:
      continue
    for s in by_id[mid]["settlements"].values():
      nm = str(s.get("name", "")).strip()
      pk = max((float(v) for v in (s.get("population") or {}).values()), default=0.0)
      if pk > modern_peaks.get(nm, 0.0):
        modern_peaks[nm] = pk
  top15 = sorted(modern_peaks.items(), key=lambda kv: (-kv[1], kv[0]))[:15][::-1]
  if top15:
    y_pos = np.arange(len(top15))
    bar_v = [r[1] for r in top15]
    bar_l = [_clean_sub_label(r[0], 24) for r in top15]
    mx_v = max(bar_v)
    axR.barh(y_pos, bar_v, height=0.68, color="#2b5c8f", alpha=0.86, edgecolor="#1e3a5f", linewidth=0.4)
    for k_i, pv in enumerate(bar_v):
      axR.text(pv + mx_v * 0.02, y_pos[k_i], vpu.format_semantic_population(pv), va="center", ha="left", fontsize=6.6)
    axR.set_yticks(y_pos)
    axR.set_yticklabels(bar_l, fontsize=7.0)
    axR.set_xlim(0, mx_v * 1.26)
  axR.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  axR.set_xlabel("Peak Urban Population", fontsize=8.4)
  axR.set_title("B. Leading 15 Modern Municipalities", fontsize=9.2, pad=5)
  vpu.apply_viscount_style(axR)
  axR.grid(True, linestyle=":", alpha=0.45)

  fig.suptitle("Korea and Japan Urban Hierarchy Across Historical and Modern Regimes", fontsize=11.0, y=0.96)
  cmh.verify_zero_text_overlaps(fig, "root_fig4")
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig4_castle_urban_hierarchy.png", 300)
  plt.close(fig)


def render_chapter_fig1 (arg0_mod):
  """Generates Chapter Figure 1: Equal-Area pure-vector POLARIS map with callouts and Ryukyu inset."""
  plt.rcdefaults()
  plt.style.use("default")
  mid = arg0_mod["id"]
  is_jp = mid in JAPAN_IDS
  is_kr = mid in KOREA_IDS
  proj = cmh.PROJ_JAPAN if is_jp else (cmh.PROJ_KOREA if is_kr else cmh.PROJ_CASTLE)
  scope = "japan" if is_jp else ("korea" if is_kr else "castle")
  feats = arg0_mod["geojson"].get("features", [])
  setts = arg0_mod["settlements"]
  ys_dom = sorted(arg0_mod["headline"].keys())
  span_str = f"({_fmt_yr(ys_dom[0])} to {_fmt_yr(ys_dom[-1])})" if ys_dom else ""
  regs = arg0_mod["data"].get("regions", {})
  n_regs = len(regs)
  use_jp_macro_leg = is_jp and n_regs > 20

  def _jp_pref_col (arg0_feat, arg1_idx):
    rk_f = (arg0_feat.get("properties") or {}).get("region_key", "")
    base_hex = JP_PREF_TO_MACRO_COL.get(rk_f)
    if base_hex:
      return cmh.mute_rgb_hex(base_hex, arg1_idx, arg2_blend=0.32)
    pr = arg0_feat.get("properties", {})
    return cmh.mute_rgb_hex(pr.get("rgb") or pr.get("colour"), arg1_idx, arg2_blend=0.44)

  col_fn = _jp_pref_col if use_jp_macro_leg else None
  main_clip = MAIN_JAPAN_CLIP if is_jp else None

  _, _, bounds = _build_vector_patches(feats, proj, arg3_color_fn=col_fn, arg4_clip_box=main_clip)
  if bounds is None:
    bounds = (-900.0, -900.0, 900.0, 900.0)

  if use_jp_macro_leg:
    leg_h = [Patch(facecolor=cmh.mute_rgb_hex(mc, i, arg2_blend=0.32), edgecolor="#334155", linewidth=0.40, label=f"{ml} ({len(mk)} pref.)") for i, (ml, mc, mk) in enumerate(JP_MACRO_REGIONS)]
    ncols_l = 4
  else:
    col_map = {}
    for i, f in enumerate(feats):
      pr = f.get("properties", {})
      rk_f = pr.get("region_key") or pr.get("region_id") or ""
      if rk_f:
        col_map[rk_f] = cmh.mute_rgb_hex(pr.get("rgb") or pr.get("colour"), i, arg2_blend=0.44)
    ncols_l = 3 if n_regs <= 9 else (4 if n_regs <= 16 else 5)
    max_lbl_len = 24 if n_regs >= 15 else 30
    leg_h = [
      Patch(facecolor=col_map.get(rk, cmh.mute_rgb_hex(rv.get("colour"), i, arg2_blend=0.44)), edgecolor="#334155", linewidth=0.38, label=_clean_sub_label(rv.get("name", rk), max_lbl_len))
      for i, (rk, rv) in enumerate(regs.items())
    ]

  nrows_l = max(1, int(math.ceil(len(leg_h) / float(ncols_l))))
  bot_m = min(0.26, 0.065 + 0.032 * nrows_l)
  fig_h = 8.0 if n_regs >= 15 else 7.6
  fig, ax = plt.subplots(figsize=(12.4, fig_h), dpi=300)
  plt.subplots_adjust(left=0.025, right=0.975, top=0.90, bottom=bot_m)

  aspect_t = 1.38 if is_jp else (1.15 if is_kr else 1.42)
  xl, yl = vpu.pad_projected_bounds(bounds, arg1_target_aspect=aspect_t, arg2_pad_factor=1.15, arg3_min_span_km=320.0)
  if is_jp:
    _draw_ryukyu_inset(ax, feats, arg2_color_fn=col_fn)
  _draw_panel_map(
    fig, ax, proj, feats, xl, yl, setts,
    arg7_max_lbl=8, arg8_color_fn=col_fn, arg9_is_dense=(len(setts) > 750), arg10_scope=scope, arg11_clip_box=main_clip
  )

  leg_fs = 6.2 if len(leg_h) >= 14 else 6.8
  if leg_h:
    fig.legend(handles=leg_h, loc="lower center", bbox_to_anchor=(0.5, 0.014), ncol=ncols_l, fontsize=leg_fs, frameon=True, facecolor="white")

  fig.suptitle(f"{arg0_mod['title']}: Sub-Regions and Settlements {span_str}", fontsize=10.6, y=0.96)
  cmh.verify_zero_text_overlaps(fig, f"{mid}_fig1")
  vpu.save_viscount_figure(fig, arg0_mod["fig_dir"] / f"fig1_{mid}_spatial.png", 300)
  plt.close(fig)


def render_chapter_fig2 (arg0_mod):
  """Generates Chapter Figure 2: 2-panel trajectory (sub-regions + aggregate bounds)."""
  plt.rcdefaults()
  plt.style.use("default")
  mid = arg0_mod["id"]
  hl = arg0_mod["headline"]
  ys = sorted(hl.keys())
  tot = np.array([float(hl[y]) for y in ys], dtype=float)
  regs = arg0_mod["data"].get("regions", {})
  ranked = sorted(regs.items(), key=lambda kv: max((float(v) for v in kv[1].get("population", {}).values()), default=0.0), reverse=True)

  fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.0, 5.8), dpi=300)
  show_legs = ranked[:8]
  nrows_l = max(1, int(math.ceil(len(show_legs) / 3.0)))
  bot_m = min(0.28, 0.13 + 0.036 * nrows_l)
  plt.subplots_adjust(left=0.07, right=0.97, top=0.84, bottom=bot_m, wspace=0.20)

  handles_l = []
  for r_i, (rk, rv) in enumerate(show_legs):
    pm = rv.get("population", {})
    ry = sorted(int(k) for k in pm.keys())
    ln, = axL.plot(ry, [float(pm[str(y)]) for y in ry], linewidth=1.7, color=PALETTE[r_i % len(PALETTE)], label=_clean_sub_label(rv.get("name", rk), 30))
    handles_l.append(ln)
  axL.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  _fmt_yr_ticks(axL, ys)
  axL.set_xlim(ys[0], ys[-1])
  axL.set_xlabel("Calendar Year", fontsize=8.4)
  axL.set_ylabel("Sub-Regional Population", fontsize=8.4)
  axL.set_title("A. Leading Sub-Regional Trajectories", fontsize=9.2, pad=5)
  vpu.apply_viscount_style(axL)
  axL.grid(True, linestyle=":", alpha=0.45)

  axR.fill_between(ys, tot * 0.92, tot * 1.08, color="#2b5c8f", alpha=0.16, label="Uncertainty interval (+/- 8%)")
  axR.plot(ys, tot, color="#0f172a", linewidth=2.2, label="Regional total")
  axR.scatter([ys[0], ys[-1]], [tot[0], tot[-1]], s=24, color="#b91c1c", zorder=6)
  axR.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  _fmt_yr_ticks(axR, ys)
  axR.set_xlim(ys[0], ys[-1])
  axR.set_ylim(0, max(float(np.max(tot)) * 1.28, 10.0))
  axR.set_xlabel("Calendar Year", fontsize=8.4)
  axR.set_ylabel("Aggregate Population", fontsize=8.4)
  axR.set_title("B. Aggregate Trajectory and Bounds", fontsize=9.2, pad=5)
  axR.legend(loc="upper left", fontsize=7.0, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axR)
  axR.grid(True, linestyle=":", alpha=0.45)

  if handles_l:
    fig.legend(handles=handles_l, loc="lower center", bbox_to_anchor=(0.5, 0.015), ncol=min(3, len(handles_l)), fontsize=6.6, frameon=True, facecolor="white")
  fig.suptitle(f"{arg0_mod['title']}: Demographic Trajectory ({_fmt_yr(ys[0])} to {_fmt_yr(ys[-1])})", fontsize=10.6, y=0.95)
  cmh.verify_zero_text_overlaps(fig, f"{mid}_fig2")
  vpu.save_viscount_figure(fig, arg0_mod["fig_dir"] / f"fig2_{mid}_trajectory.png", 300)
  plt.close(fig)


def render_chapter_fig3 (arg0_mod):
  """Generates Chapter Figure 3: 2-panel composition shares and peak vs terminal bars."""
  plt.rcdefaults()
  plt.style.use("default")
  mid = arg0_mod["id"]
  hl = arg0_mod["headline"]
  ys = sorted(hl.keys())
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
    lbls.append(_clean_sub_label(rv.get("name", rk), 28))
    cols.append(PALETTE[r_i % len(PALETTE)])
  if len(ranked) > 8:
    rem = np.sum([_interp_series(rv.get("population", {}), ys) for _, rv in ranked[8:]], axis=0)
    mat.append(rem.tolist())
    lbls.append("Remaining Sub-Regions")
    cols.append("#94a3b8")

  arr = np.asarray(mat, dtype=float)
  pcts = arr / np.maximum(np.sum(arr, axis=0), 1.0) * 100.0
  nrows_l = max(1, int(math.ceil(len(lbls) / 3.0)))
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
    axR.barh(y_i + 0.17, pks, height=0.33, color="#2b5c8f", alpha=0.86, label="Epoch Peak")
    axR.barh(y_i - 0.17, terms, height=0.33, color="#3d8a5a", alpha=0.86, label=f"Terminal ({_fmt_yr(ys[-1])})")
    mx_b = max(max(pks), max(terms), 1.0)
    for k_i, pv in enumerate(pks):
      axR.text(pv + mx_b * 0.02, y_i[k_i] + 0.17, vpu.format_semantic_population(pv), va="center", ha="left", fontsize=6.6)
    axR.set_yticks(y_i)
    axR.set_yticklabels(ynms, fontsize=7.0)
    axR.set_xlim(0, mx_b * 1.26)
  axR.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  axR.set_xlabel("Population", fontsize=8.4)
  axR.set_title("B. Leading Sub-Regions: Peak vs Terminal", fontsize=9.2, pad=5)
  axR.legend(loc="lower right", fontsize=6.8, frameon=True, facecolor="white")
  vpu.apply_viscount_style(axR)
  axR.grid(True, linestyle=":", alpha=0.45)

  leg_handles = [Patch(facecolor=c, edgecolor="#334155", linewidth=0.35, label=l) for l, c in zip(lbls, cols)]
  fig.legend(handles=leg_handles, loc="lower center", bbox_to_anchor=(0.5, 0.015), ncol=min(3, len(lbls)), fontsize=6.6, frameon=True, facecolor="white")
  fig.suptitle(f"{arg0_mod['title']}: Sub-Regional Distribution ({_fmt_yr(ys[0])} to {_fmt_yr(ys[-1])})", fontsize=10.6, y=0.95)
  cmh.verify_zero_text_overlaps(fig, f"{mid}_fig3")
  vpu.save_viscount_figure(fig, arg0_mod["fig_dir"] / f"fig3_{mid}_shares.png", 300)
  plt.close(fig)


def render_chapter_fig4 (arg0_mod):
  """Generates Chapter Figure 4: rank-size curve (n >= 25) and top 15 settlements."""
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

  if len(ranked) >= 25:
    ranks = np.arange(1, len(ranked) + 1, dtype=float)
    vals = np.array([r[0] for r in ranked], dtype=float)
    axL.loglog(ranks, vals, "o", markersize=3.2, color="#2b5c8f", alpha=0.78)
    vpu.apply_human_log_ticks(axL, "both", True)
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
    axR.set_xlim(0, mx_v * 1.26)
  axR.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: vpu.format_semantic_population(x)))
  axR.set_xlabel("Peak Population", fontsize=8.4)
  axR.set_title("B. Leading 15 Catalogued Settlements", fontsize=9.2, pad=5)
  vpu.apply_viscount_style(axR)
  axR.grid(True, linestyle=":", alpha=0.45)

  n_disp = len(ranked)
  fig.suptitle(f"{arg0_mod['title']}: Settlement Hierarchy ($n={vpu.format_euro_number(n_disp, 0)}$)", fontsize=10.6, y=0.96)
  cmh.verify_zero_text_overlaps(fig, f"{mid}_fig4")
  vpu.save_viscount_figure(fig, arg0_mod["fig_dir"] / f"fig4_{mid}_settlements.png", 300)
  plt.close(fig)


def main ():
  """Renders all 4 CASTLE root figures and 52 chapter figures across 13 modules."""
  ROOT_FIG_DIR.mkdir(parents=True, exist_ok=True)
  mods = _load_modules()
  print(f"[generate_figures] Rendering 4 root + {len(mods) * 4} chapter figures for CASTLE...")
  render_root_fig1(mods)
  print("[root] Rendered fig1_castle_macro_zones.png")
  render_root_fig2(mods)
  print("[root] Rendered fig2_castle_long_run_trajectory.png")
  render_root_fig3()
  print("[root] Rendered fig3_castle_kriging_diagnostics.png")
  render_root_fig4(mods)
  print("[root] Rendered fig4_castle_urban_hierarchy.png")

  for idx, m in enumerate(mods, start=1):
    m["fig_dir"].mkdir(parents=True, exist_ok=True)
    render_chapter_fig1(m)
    render_chapter_fig2(m)
    render_chapter_fig3(m)
    render_chapter_fig4(m)
    print(f"[{idx:02d}/{len(mods)}] Rendered 4 figures for {m['id']}")


if __name__ == "__main__":
  main()
