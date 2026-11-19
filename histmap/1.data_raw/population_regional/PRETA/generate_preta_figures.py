"""Publication-grade Equal-Area Vector Cartography & Diagnostic Figure Generator for
Operation Viscount Project PRETA (13 constituent chapters + root synthesis).

Strictly complies with all 5 POLARIS Figure Laws & `audit_figure_scripts.py`:
  1. Vector GeoJSON `PatchCollection` polygons (`0` pixelated categorical mask `imshow`).
  2. Upright Lambert Azimuthal Equal-Area (`set_aspect("equal", adjustable="box")`).
  3. Renderer-bbox in-panel containment via `place_inbounds_callouts` & `verify_panel_bounds_and_overlaps`.
  4. Default Matplotlib theme (`plt.rcdefaults(); plt.style.use("default")`), `DejaVu Sans`,
     rendered `$...$` MathText with `{,}`, European comma ticks, plain human log numerals (`0,01..1k..1,5M`).
  5. Freshness synchronisation: run prior to RMarkdown PDF compilation.
"""

import json
import math
import os
import pathlib
import sys
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import shape
from shapely.ops import unary_union

sys.stdout.reconfigure(encoding="utf-8")

PRETA_DIR = pathlib.Path(__file__).resolve().parent
SVEA_ROOT = PRETA_DIR.parents[3]
SHARED_UTILS_DIR = SVEA_ROOT / "histmap/1.data_raw/population_regional/_shared"
sys.path.insert(0, str(SHARED_UTILS_DIR))

from viscount_plot_utils import (
  apply_human_colorbar_ticks,
  apply_human_log_ticks,
  apply_viscount_style,
  euro_log_formatter,
  euro_tick_formatter,
  format_euro_number,
  format_mathtext_euro,
  format_semantic_population,
  mute_rgb_hex,
  pad_projected_bounds,
  place_inbounds_callouts,
  save_viscount_figure,
)

GIS_SHARED = SVEA_ROOT / "histmap/1.data_raw/population_regional/_shared/_gis_cache"
SUBREG_DIR = PRETA_DIR / "_shared/_gis_cache/chapter_subregions"
DOMAIN_DIR = PRETA_DIR / "_shared/sites_preta_amazon_brazil"

NE_LAND_GJ = GIS_SHARED / "ne_10m_admin_0_countries.geojson"
NE_RIVERS_GJ = GIS_SHARED / "ne_10m_rivers_lake_centerlines.geojson"

CHAPTER_META = [
  ("1.pre_columbian/1.eastern_amazon_basin", "eastern_amazon_basin", "Pre-Columbian Eastern Amazon Basin"),
  ("1.pre_columbian/2.western_amazon_basin", "western_amazon_basin", "Pre-Columbian Western Amazon Basin"),
  ("1.pre_columbian/3.northeastern_brazil", "northeastern_brazil", "Pre-Columbian North-Eastern Brazil"),
  ("1.pre_columbian/4.southern_brazil", "southern_brazil", "Pre-Columbian Southern Brazil"),
  ("1.pre_columbian/5.guyana", "guyana", "Pre-Columbian Guianas"),
  ("2.colonial/1.colonial_brazil", "colonial_brazil", "Colonial Brazil"),
  ("2.colonial/2.colonial_guyana", "colonial_guyana", "Colonial Guianas"),
  ("2.colonial/3.colonial_paraguay", "colonial_paraguay", "Colonial Paraguay"),
  ("2.colonial/4.colonial_spanish_amazon", "colonial_spanish_amazon", "Colonial Spanish Amazon"),
  ("3.post_independence/1.brazil_after_independence", "brazil_after_independence", "Brazil after Independence"),
  ("3.post_independence/2.bolivia_after_independence", "bolivia_after_independence", "Bolivia after Independence"),
  ("3.post_independence/3.paraguay_after_independence", "paraguay_after_independence", "Paraguay after Independence"),
  ("3.post_independence/4.guianas_post_1815", "guianas_post_1815", "Guianas post-1815"),
]

HORIZON_DISPLAY_NAMES = {
  "01_palaeoindian_early_holocene": "Palaeoindian (8000BC)",
  "02_middle_holocene_archaic_sambaqui": "Middle Holocene (4500BC)",
  "03_late_archaic_early_formative": "Late Archaic (2000BC)",
  "04_formative_early_ade": "Early Formative (500BC)",
  "05_classic_amazonian_ade_expansion": "Classic ADE (250AD)",
  "06_polychrome_mound_chiefdoms": "Polychrome Mounds (750AD)",
  "07_late_precolumbian_chiefdoms": "Late Pre-Columbian (1200AD)",
  "08_contact_horizon": "Contact Horizon (1500AD)",
  "09_terra_preta_ade_anthrosol": "Terra Preta Anthrosol",
}


class LambertAzimuthalEqualArea:
  """Spherical Lambert Azimuthal Equal-Area projection in kilometres (`set_aspect('equal')`)."""

  def __init__(self, arg0_lon0_deg, arg1_lat0_deg):
    self.lon0 = math.radians(float(arg0_lon0_deg))
    self.lat0 = math.radians(float(arg1_lat0_deg))
    self.sin_lat0 = math.sin(self.lat0)
    self.cos_lat0 = math.cos(self.lat0)
    self.r_km = 6371.0

  def fwd_pt(self, arg0_lon_deg, arg1_lat_deg):
    lon = math.radians(float(arg0_lon_deg))
    lat = math.radians(float(arg1_lat_deg))
    dlon = lon - self.lon0
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    denom = 1.0 + self.sin_lat0 * sin_lat + self.cos_lat0 * cos_lat * math.cos(dlon)
    k = math.sqrt(2.0 / max(1e-9, denom))
    x = self.r_km * k * cos_lat * math.sin(dlon)
    y = self.r_km * k * (self.cos_lat0 * sin_lat - self.sin_lat0 * cos_lat * math.cos(dlon))
    return x, y

  def fwd_arrays(self, arg0_lon_deg, arg1_lat_deg):
    lon = np.radians(arg0_lon_deg)
    lat = np.radians(arg1_lat_deg)
    dlon = lon - self.lon0
    sin_lat = np.sin(lat)
    cos_lat = np.cos(lat)
    denom = 1.0 + self.sin_lat0 * sin_lat + self.cos_lat0 * cos_lat * np.cos(dlon)
    k = np.sqrt(2.0 / np.maximum(1e-9, denom))
    x = self.r_km * k * cos_lat * np.sin(dlon)
    y = self.r_km * k * (self.cos_lat0 * sin_lat - self.sin_lat0 * cos_lat * np.cos(dlon))
    return x, y

  def inv_arrays(self, arg0_x_km, arg1_y_km):
    x = arg0_x_km / self.r_km
    y = arg1_y_km / self.r_km
    rho = np.hypot(x, y)
    c = 2.0 * np.arcsin(np.clip(0.5 * rho, -1.0, 1.0))
    sin_c = np.sin(c)
    cos_c = np.cos(c)
    safe_rho = np.where(rho > 1e-12, rho, 1.0)
    lat = np.where(
      rho > 1e-12,
      np.arcsin(np.clip(cos_c * self.sin_lat0 + (y * sin_c * self.cos_lat0) / safe_rho, -1.0, 1.0)),
      self.lat0,
    )
    lon = self.lon0 + np.arctan2(
      x * sin_c,
      safe_rho * self.cos_lat0 * cos_c - y * self.sin_lat0 * sin_c,
    )
    return np.degrees(lon), np.degrees(lat)


def geom_to_mpl_patches(arg0_geom, arg1_proj):
  """Projects a Shapely Polygon/MultiPolygon into Matplotlib Polygon patches."""
  patches = []
  if arg0_geom is None or arg0_geom.is_empty:
    return patches
  polys = [arg0_geom] if arg0_geom.geom_type == "Polygon" else (
    list(arg0_geom.geoms) if arg0_geom.geom_type in ("MultiPolygon", "GeometryCollection") else []
  )
  for poly in polys:
    if poly.geom_type != "Polygon" or poly.is_empty:
      continue
    coords = np.asarray(poly.exterior.coords, dtype=float)
    if len(coords) < 3:
      continue
    xs, ys = arg1_proj.fwd_arrays(coords[:, 0], coords[:, 1])
    patches.append(MplPolygon(np.column_stack([xs, ys]), closed=True))
  return patches


def load_south_america_context():
  """Loads Natural Earth South American land polygons and major river centerlines once."""
  land_gj = json.loads(NE_LAND_GJ.read_text(encoding="utf-8"))
  sa_geoms = []
  for ft in land_gj["features"]:
    g = shape(ft["geometry"])
    bb = g.bounds
    if bb[2] >= -84.0 and bb[0] <= -32.0 and bb[3] >= -56.0 and bb[1] <= 14.0:
      sa_geoms.append(g)

  riv_gj = json.loads(NE_RIVERS_GJ.read_text(encoding="utf-8"))
  riv_lines = []
  for ft in riv_gj["features"]:
    p = ft.get("properties") or {}
    sr = int(p.get("scalerank") or 9)
    if sr > 6:
      continue
    g = shape(ft["geometry"])
    bb = g.bounds
    if bb[2] >= -82.0 and bb[0] <= -33.0 and bb[3] >= -38.0 and bb[1] <= 12.0:
      lines = [g] if g.geom_type == "LineString" else (list(g.geoms) if g.geom_type == "MultiLineString" else [])
      for ln in lines:
        coords = np.asarray(ln.coords, dtype=float)
        if len(coords) >= 2:
          riv_lines.append((sr, coords))
  return sa_geoms, riv_lines


def fmt_year_label(arg0_yr):
  """Formats integer year consistently ('10000BC', '1500AD')."""
  y = int(round(arg0_yr))
  return f"{abs(y)}BC" if y < 0 else f"{y}AD"


def render_chapter_figures(arg0_rel_dir, arg1_stem, arg2_title, arg3_sa_geoms, arg4_riv_lines):
  """Renders Fig 1 (Equal-Area Vector Spatial Map) and Fig 2 (Demographic Trajectory & Urban Hierarchy) for one chapter."""
  ch_dir = PRETA_DIR / arg0_rel_dir
  fig_dir = ch_dir / "figures"
  fig_dir.mkdir(parents=True, exist_ok=True)

  mod_data = json.loads((ch_dir / f"{arg1_stem}.json5").read_text(encoding="utf-8"))
  sett_data = json.loads((ch_dir / f"{arg1_stem}_settlements.json").read_text(encoding="utf-8"))
  subreg_gj = json.loads((SUBREG_DIR / f"{arg1_stem}_subregions.geojson").read_text(encoding="utf-8"))

  # Compute chapter centroid for Lambert Azimuthal Equal-Area
  reg_geoms = []
  for ft in subreg_gj["features"]:
    g = shape(ft["geometry"])
    if not g.is_empty:
      reg_geoms.append((ft["properties"], g))
  union_g = unary_union([g for _, g in reg_geoms])
  cent = union_g.centroid
  proj = LambertAzimuthalEqualArea(cent.x, cent.y)

  # ---------------- FIGURE 1: EQUAL-AREA VECTOR SPATIAL MAP ----------------
  apply_viscount_style()
  fig, ax = plt.subplots(figsize=(9.2, 6.2), dpi=300)
  apply_viscount_style(ax, {"grid": True})
  ax.set_facecolor("#e8f1f8")

  # Background South American land
  bg_patches = []
  for sg in arg3_sa_geoms:
    bg_patches.extend(geom_to_mpl_patches(sg, proj))
  if bg_patches:
    ax.add_collection(PatchCollection(bg_patches, facecolor="#f4f1ea", edgecolor="#94a3b8", linewidths=0.45, zorder=1))

  # Chapter sub-region vector polygons blended smoothly via mute_rgb_hex
  all_xs, all_ys = [], []
  legend_handles = []
  for idx, (props, g) in enumerate(reg_geoms):
    hex_col = mute_rgb_hex(props.get("colour"), idx, arg2_blend=0.42)
    ps = geom_to_mpl_patches(g, proj)
    for p in ps:
      xy = p.get_xy()
      all_xs.extend(xy[:, 0])
      all_ys.extend(xy[:, 1])
    if ps:
      ax.add_collection(PatchCollection(ps, facecolor=hex_col, edgecolor="#334155", linewidths=0.55, zorder=2))
    if len(reg_geoms) <= 10:
      lbl = str(props.get("name") or props.get("region_id"))
      if len(lbl) > 36:
        lbl = lbl[:33] + "..."
      legend_handles.append(mpatches.Patch(facecolor=hex_col, edgecolor="#334155", linewidth=0.55, label=lbl))

  # Bold dissolved outer perimeter outline
  outer_ps = geom_to_mpl_patches(union_g, proj)
  if outer_ps:
    ax.add_collection(PatchCollection(outer_ps, facecolor="none", edgecolor="#111827", linewidths=1.15, zorder=3))

  # Rivers clipped to padded projected bounds
  xlim, ylim = pad_projected_bounds([min(all_xs), min(all_ys), max(all_xs), max(all_ys)], arg1_target_aspect=1.42, arg2_pad_factor=1.16)
  riv_segs = []
  for sr, coords in arg4_riv_lines:
    rx, ry = proj.fwd_arrays(coords[:, 0], coords[:, 1])
    if rx.max() >= xlim[0] and rx.min() <= xlim[1] and ry.max() >= ylim[0] and ry.min() <= ylim[1]:
      riv_segs.append(np.column_stack([rx, ry]))
  if riv_segs:
    ax.add_collection(LineCollection(riv_segs, colors="#2b6cb0", linewidths=0.65, alpha=0.62, zorder=4))

  # Plot catalogued settlements
  sett_list = list(sett_data.values())
  s_lons = np.array([s["coords"][1] for s in sett_list], dtype=float)
  s_lats = np.array([s["coords"][0] for s in sett_list], dtype=float)
  s_peaks = np.array([max(s["population"].values()) if s.get("population") else 10 for s in sett_list], dtype=float)
  sx, sy = proj.fwd_arrays(s_lons, s_lats)
  sz = np.clip(4.0 + 3.2 * np.log10(np.maximum(10.0, s_peaks)), 5.0, 28.0)
  ax.scatter(sx, sy, s=sz, c="#1e293b", alpha=0.58, edgecolors="white", linewidths=0.25, zorder=5)

  ax.set_xlim(xlim)
  ax.set_ylim(ylim)
  ax.set_aspect("equal", adjustable="box")
  ax.set_xlabel("Lambert Azimuthal Equal-Area Easting (km)")
  ax.set_ylabel("Lambert Azimuthal Equal-Area Northing (km)")
  ax.xaxis.set_major_formatter(euro_tick_formatter(0))
  ax.yaxis.set_major_formatter(euro_tick_formatter(0))

  dom = mod_data["domain"]
  n_s_fmt = format_euro_number(len(sett_list), 0)
  area_fmt = format_semantic_population(mod_data["total_area_km2"]).replace("k", "k km²").replace("M", "M km²")
  if "km²" not in area_fmt:
    area_fmt += " km²"
  ax.set_title(f"{arg2_title} ({fmt_year_label(dom[0])} to {fmt_year_label(dom[1])}; n={n_s_fmt}, {area_fmt})", fontsize=10.5)

  # Place top 7 non-overlapping settlement callouts inside panel bounds
  top_order = np.argsort(-s_peaks)
  callout_items = []
  seen_lbl = set()
  for idx in top_order[:40]:
    s = sett_list[int(idx)]
    nm = s["name"]
    if len(nm) > 26:
      nm = nm.split("(")[0].strip()[:26]
    if nm.lower() in seen_lbl:
      continue
    seen_lbl.add(nm.lower())
    callout_items.append((nm, s["coords"][1], s["coords"][0]))
    if len(callout_items) >= 18:
      break
  place_inbounds_callouts(fig, ax, callout_items, arg3_proj=proj, arg4_xlim=xlim, arg5_ylim=ylim, arg6_options={"max_labels": 7, "min_sep_px": 46.0, "fontsize": 6.5})

  if legend_handles:
    ncol = 2 if len(legend_handles) <= 4 else 3
    n_rows = int(math.ceil(len(legend_handles) / float(ncol)))
    fig.legend(handles=legend_handles, loc="lower center", ncol=ncol, fontsize=6.4, frameon=True, bbox_to_anchor=(0.5, 0.015), columnspacing=0.9, handlelength=1.2)
    fig.subplots_adjust(bottom=0.11 + 0.038 * n_rows, top=0.92, left=0.11, right=0.97)
  else:
    fig.tight_layout()

  fig1_path = fig_dir / f"fig1_{arg1_stem}_spatial.png"
  save_viscount_figure(fig, fig1_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})

  # ---------------- FIGURE 2: DEMOGRAPHIC TRAJECTORY & TOP SETTLEMENTS ----------------
  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.6), dpi=300)
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Total population trajectory + empirical uncertainty band
  hl = mod_data["summary"]["headline_population_by_benchmark"]
  yrs = sorted(int(y) for y in hl.keys())
  tots = np.array([float(hl[str(y)]) for y in yrs], dtype=float)
  lo_tot = np.zeros_like(tots)
  hi_tot = np.zeros_like(tots)
  for rinfo in mod_data["regions"].values():
    bnds = rinfo.get("population_bounds") or {}
    r_yrs = sorted(int(k) for k in rinfo["population"].keys())
    r_lo = [float(bnds[str(k)][0]) if str(k) in bnds and len(bnds[str(k)]) >= 2 else float(rinfo["population"][str(k)]) * 0.9 for k in r_yrs]
    r_hi = [float(bnds[str(k)][1]) if str(k) in bnds and len(bnds[str(k)]) >= 2 else float(rinfo["population"][str(k)]) * 1.1 for k in r_yrs]
    lo_tot += np.interp(yrs, r_yrs, r_lo)
    hi_tot += np.interp(yrs, r_yrs, r_hi)

  ax1.fill_between(yrs, lo_tot, hi_tot, color="#93c5fd", alpha=0.38, label="Uncertainty interval")
  ax1.plot(yrs, tots, color="#1d4ed8", linewidth=2.0, marker="o", markersize=3.2, label="Regional total")
  ax1.set_ylim(0, float(np.max(hi_tot)) * 1.22)
  ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: format_semantic_population(x)))
  ax1.xaxis.set_major_locator(mticker.MaxNLocator(nbins=5, integer=True))
  ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: fmt_year_label(x)))
  ax1.set_title("A. Regional Population Trajectory", fontsize=9.8)
  ax1.set_xlabel("Calendar year")
  ax1.set_ylabel("Inhabitants")
  ax1.legend(loc="upper left", fontsize=7.5, frameon=True)

  # Panel B: Top 10 deduplicated settlements horizontal bar chart with 1.26x headroom
  sorted_setts = sorted(sett_list, key=lambda s: max(s["population"].values()), reverse=True)
  top10 = []
  seen_bar_names = set()
  for s in sorted_setts:
    raw_nm = s["name"].strip()
    base_nm = raw_nm.split("(")[0].strip() if len(raw_nm) > 24 else raw_nm
    if len(base_nm) > 26:
      base_nm = base_nm[:25].rstrip() + "."
    k_nm = base_nm.lower()
    if k_nm in seen_bar_names:
      continue
    seen_bar_names.add(k_nm)
    top10.append((base_nm, float(max(s["population"].values()))))
    if len(top10) >= 10:
      break
  top10 = list(reversed(top10))
  bar_lbls = [it[0] for it in top10]
  bar_vals = [it[1] for it in top10]
  y_pos = np.arange(len(top10))
  ax2.barh(y_pos, bar_vals, color="#0f766e", edgecolor="#134e4a", linewidth=0.5, height=0.68)
  ax2.set_yticks(y_pos)
  ax2.set_yticklabels(bar_lbls, fontsize=7.6)
  xmax_b = max(bar_vals) * 1.26
  ax2.set_xlim(0, xmax_b)
  ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: format_semantic_population(x)))
  for yi, v in enumerate(bar_vals):
    ax2.text(v + xmax_b * 0.015, yi, format_semantic_population(v), va="center", ha="left", fontsize=7.2, color="#0f172a")
  ax2.set_title(f"B. Leading Catalogued Settlements (n={n_s_fmt})", fontsize=9.8)
  ax2.set_xlabel("Peak settlement population")

  fig.subplots_adjust(wspace=0.48, left=0.08, right=0.97, top=0.89, bottom=0.14)
  fig2_path = fig_dir / f"fig2_{arg1_stem}_trajectory.png"
  save_viscount_figure(fig, fig2_path, arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})
  print(f"  [FIGS OK] {arg1_stem}")


def render_root_figures(arg0_sa_geoms, arg1_riv_lines):
  """Renders the 3 root comparative synthesis figures for studies_on_population.Rmd."""
  fig_dir = PRETA_DIR / "figures"
  fig_dir.mkdir(parents=True, exist_ok=True)
  proj = LambertAzimuthalEqualArea(-57.0, -12.0)

  # ---------------- ROOT FIG 1: TWO-PANEL MACRO ZONES (PRE-COLUMBIAN vs MODERN) ----------------
  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 6.0), dpi=300)
  precol_stems = [
    ("eastern_amazon_basin", "#15803d", "Eastern Amazon Basin"),
    ("western_amazon_basin", "#0d9488", "Western Amazon Basin"),
    ("northeastern_brazil", "#d97706", "North-Eastern Brazil"),
    ("southern_brazil", "#2563eb", "Southern Brazil"),
    ("guyana", "#9333ea", "Guianas"),
  ]
  mod_stems = [
    ("brazil_after_independence", "#16a34a", "Brazil (27 UFs)"),
    ("bolivia_after_independence", "#ea580c", "Bolivia (9 Depts)"),
    ("paraguay_after_independence", "#2563eb", "Paraguay (18 Admin-1)"),
    ("guianas_post_1815", "#7c3aed", "Guianas (21 Admin-1)"),
  ]

  for ax, group_specs, panel_title in [
    (ax1, precol_stems, "A. Pre-Columbian Hydrological Basins (10000BC to 1595AD)"),
    (ax2, mod_stems, "B. Post-Independence National Domains (1811 to 2026AD)"),
  ]:
    apply_viscount_style(ax, {"grid": True})
    ax.set_facecolor("#e8f1f8")
    bg_ps = []
    for sg in arg0_sa_geoms:
      bg_ps.extend(geom_to_mpl_patches(sg, proj))
    if bg_ps:
      ax.add_collection(PatchCollection(bg_ps, facecolor="#f4f1ea", edgecolor="#94a3b8", linewidths=0.45, zorder=1))

    handles = []
    all_x, all_y = [], []
    for stem, col_hex, label in group_specs:
      gj = json.loads((SUBREG_DIR / f"{stem}_subregions.geojson").read_text(encoding="utf-8"))
      ps = []
      for ft in gj["features"]:
        g = shape(ft["geometry"])
        for p in geom_to_mpl_patches(g, proj):
          xy = p.get_xy()
          all_x.extend(xy[:, 0])
          all_y.extend(xy[:, 1])
          ps.append(p)
      if ps:
        ax.add_collection(PatchCollection(ps, facecolor=col_hex, alpha=0.58, edgecolor="#1e293b", linewidths=0.35, zorder=2))
      handles.append(mpatches.Patch(facecolor=col_hex, alpha=0.65, edgecolor="#1e293b", label=label))

    xlim, ylim = pad_projected_bounds([min(all_x), min(all_y), max(all_x), max(all_y)], arg1_target_aspect=1.0, arg2_pad_factor=1.10)
    r_segs = []
    for sr, coords in arg1_riv_lines:
      if sr > 4:
        continue
      rx, ry = proj.fwd_arrays(coords[:, 0], coords[:, 1])
      if rx.max() >= xlim[0] and rx.min() <= xlim[1] and ry.max() >= ylim[0] and ry.min() <= ylim[1]:
        r_segs.append(np.column_stack([rx, ry]))
    if r_segs:
      ax.add_collection(LineCollection(r_segs, colors="#1d4ed8", linewidths=0.6, alpha=0.55, zorder=3))

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_aspect("equal", adjustable="box")
    ax.xaxis.set_major_formatter(euro_tick_formatter(0))
    ax.yaxis.set_major_formatter(euro_tick_formatter(0))
    ax.set_title(panel_title, fontsize=9.6)
    ax.set_xlabel("Easting (km)")
    ax.set_ylabel("Northing (km)")
    ax.legend(handles=handles, loc="lower left", fontsize=7.4, frameon=True)

  fig.subplots_adjust(wspace=0.22, left=0.07, right=0.98, top=0.91, bottom=0.11)
  save_viscount_figure(fig, fig_dir / "fig1_preta_macro_zones.png", arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})

  # ---------------- ROOT FIG 2: TERRA PRETA KRIGED SURFACE + MATERN VARIOGRAM ----------------
  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 5.2), dpi=300)
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Reprojected 09_terra_preta_ade_anthrosol.png continuous float32 surface
  tp_png = DOMAIN_DIR / "1.kriged_terra_preta/09_terra_preta_ade_anthrosol.png"
  raw = np.asarray(Image.open(tp_png).convert("RGBA"), dtype=np.uint8)
  f32_tp = raw.reshape(-1, 4).copy().view(">f4").reshape((2160, 4320))
  valid_tp = np.isfinite(f32_tp) & (f32_tp > 1e-4)

  ax1.set_facecolor("#e8f1f8")
  bg_ps = []
  for sg in arg0_sa_geoms:
    bg_ps.extend(geom_to_mpl_patches(sg, proj))
  if bg_ps:
    ax1.add_collection(PatchCollection(bg_ps, facecolor="#f4f1ea", edgecolor="#94a3b8", linewidths=0.45, zorder=1))

  # Sample continuous float32 Terra Preta surface onto an upright Equal-Area grid
  x_min, x_max, y_min, y_max = -2600.0, 2500.0, -2450.0, 2350.0
  gx = np.linspace(x_min, x_max, 520)
  gy = np.linspace(y_min, y_max, 490)
  gxx, gyy = np.meshgrid(gx, gy)
  glon, glat = proj.inv_arrays(gxx, gyy)
  rows_i = np.clip(((90.0 - glat) * 12.0).astype(int), 0, 2159)
  cols_i = np.clip(((glon + 180.0) * 12.0).astype(int), 0, 4319)
  krig_tp_grid = np.where(valid_tp[rows_i, cols_i], f32_tp[rows_i, cols_i], np.nan)

  vmax_tp = float(np.nanpercentile(krig_tp_grid, 99.5)) if np.isfinite(krig_tp_grid).any() else 1.0
  vmin_tp = max(0.005, vmax_tp / 200.0)
  im = ax1.imshow(
    krig_tp_grid, extent=[x_min, x_max, y_min, y_max], origin="lower",
    cmap="magma_r", norm=mcolors.LogNorm(vmin=vmin_tp, vmax=max(vmax_tp, vmin_tp * 10.0)),
    interpolation="bilinear", alpha=0.88, zorder=2
  )
  r_segs = []
  for sr, coords in arg1_riv_lines:
    if sr > 4:
      continue
    rx, ry = proj.fwd_arrays(coords[:, 0], coords[:, 1])
    if rx.max() >= x_min and rx.min() <= x_max and ry.max() >= y_min and ry.min() <= y_max:
      r_segs.append(np.column_stack([rx, ry]))
  if r_segs:
    ax1.add_collection(LineCollection(r_segs, colors="#0ea5e9", linewidths=0.55, alpha=0.58, zorder=3))
  ax1.set_xlim(x_min, x_max)
  ax1.set_ylim(y_min, y_max)
  ax1.set_aspect("equal", adjustable="box")
  ax1.xaxis.set_major_formatter(euro_tick_formatter(0))
  ax1.yaxis.set_major_formatter(euro_tick_formatter(0))
  ax1.set_title("A. Kriged Terra Preta Anthropogenic Soil Intensity", fontsize=9.6)
  ax1.set_xlabel("Easting (km)")
  ax1.set_ylabel("Northing (km)")
  cb = fig.colorbar(im, ax=ax1, fraction=0.044, pad=0.03, format=euro_log_formatter(False, 2))
  apply_human_colorbar_ticks(cb, arg1_semantic=False, arg2_digits=2)
  cb.ax.set_title("ADE index", fontsize=8.0, pad=6)

  # Panel B: Matérn nu = 3/2 Empirical Semivariogram
  diag = json.loads((DOMAIN_DIR / "config/kriging_diagnostics.json").read_text(encoding="utf-8"))
  tau1 = float(diag.get("raw_tau1_dimensionless") or diag.get("tau1_dimensionless") or 1.42)
  tau2 = float(diag.get("tau2_dimensionless") or 2.84)
  nug = float(diag.get("nugget_to_sill_ratio") or 0.04)
  u_grid = np.linspace(0.05, 12.0, 240)
  matern_corr = (1.0 + math.sqrt(3.0) * u_grid / tau1) * np.exp(-math.sqrt(3.0) * u_grid / tau1)
  gamma_model = nug + (1.0 - nug) * (1.0 - matern_corr)

  emp_bins = diag.get("empirical_semivariogram_bins") or []
  if emp_bins:
    bu = [float(b.get("mean_u") or b.get("lag") or 0) for b in emp_bins if b.get("mean_u") or b.get("lag")]
    bg = [float(b.get("gamma") or b.get("semivariance") or 0) for b in emp_bins if b.get("mean_u") or b.get("lag")]
    if bu and bg:
      ax2.scatter(bu, bg, s=34, c="#b91c1c", zorder=4, label="Empirical Matheron bins")
  ax2.plot(
    u_grid, gamma_model, color="#1d4ed8", linewidth=2.0, zorder=3,
    label=rf"Matérn $\nu = 3/2$ ($\tau_1 = {format_mathtext_euro(tau1)}$, $\tau_2 = {format_mathtext_euro(tau2)}$)"
  )
  ax2.set_xlim(0, 12.0)
  ax2.set_ylim(0, 1.25)
  ax2.xaxis.set_major_formatter(euro_tick_formatter(1))
  ax2.yaxis.set_major_formatter(euro_tick_formatter(2))
  ax2.set_title(r"B. Semivariogram Calibration ($\nu = 3/2$)", fontsize=9.6)
  ax2.set_xlabel(r"Dimensionless Voronoi geodesic lag $u_{ij}$")
  ax2.set_ylabel(r"Normalised semivariance $\gamma(u) / \sigma^2$")
  ax2.legend(loc="lower right", fontsize=8.0, frameon=True)

  fig.subplots_adjust(wspace=0.28, left=0.07, right=0.97, top=0.90, bottom=0.13)
  save_viscount_figure(fig, fig_dir / "fig2_preta_terra_preta_kriging.png", arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})

  # ---------------- ROOT FIG 3: LONG-RUN MACRO TRAJECTORIES ----------------
  apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.8, 4.7), dpi=300)
  apply_viscount_style(ax1, {"grid": True})
  apply_viscount_style(ax2, {"grid": True})

  # Panel A: Pre-Columbian Holocene expansion (-10000 to 1500)
  pre_cols = [
    ("1.pre_columbian/2.western_amazon_basin", "western_amazon_basin", "Western Amazon", "#0d9488"),
    ("1.pre_columbian/1.eastern_amazon_basin", "eastern_amazon_basin", "Eastern Amazon", "#15803d"),
    ("1.pre_columbian/4.southern_brazil", "southern_brazil", "Southern Brazil", "#2563eb"),
    ("1.pre_columbian/3.northeastern_brazil", "northeastern_brazil", "North-Eastern Brazil", "#d97706"),
    ("1.pre_columbian/5.guyana", "guyana", "Guianas", "#9333ea"),
  ]
  ymax1 = 0.0
  for rdir, stem, lbl, col in pre_cols:
    md = json.loads((PRETA_DIR / rdir / f"{stem}.json5").read_text(encoding="utf-8"))
    hl = md["summary"]["headline_population_by_benchmark"]
    ys = sorted(int(y) for y in hl.keys() if int(y) <= 1500)
    vs = [float(hl[str(y)]) for y in ys]
    ymax1 = max(ymax1, max(vs))
    ax1.plot(ys, vs, linewidth=1.8, color=col, label=lbl)
  ax1.set_ylim(0, ymax1 * 1.24)
  ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: format_semantic_population(x)))
  ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: fmt_year_label(x)))
  ax1.set_title("A. Pre-Columbian Holocene Expansion (10000BC to 1500AD)", fontsize=9.5)
  ax1.set_xlabel("Calendar year")
  ax1.set_ylabel("Inhabitants")
  ax1.legend(loc="upper left", fontsize=7.6, frameon=True)

  # Panel B: Post-1815 National Expansion (Log scale with plain human numerals!)
  mod_cols = [
    ("3.post_independence/1.brazil_after_independence", "brazil_after_independence", "Brazil", "#16a34a"),
    ("3.post_independence/2.bolivia_after_independence", "bolivia_after_independence", "Bolivia", "#ea580c"),
    ("3.post_independence/3.paraguay_after_independence", "paraguay_after_independence", "Paraguay", "#2563eb"),
    ("3.post_independence/4.guianas_post_1815", "guianas_post_1815", "Three Guianas", "#7c3aed"),
  ]
  for rdir, stem, lbl, col in mod_cols:
    md = json.loads((PRETA_DIR / rdir / f"{stem}.json5").read_text(encoding="utf-8"))
    hl = md["summary"]["headline_population_by_benchmark"]
    ys = sorted(int(y) for y in hl.keys())
    vs = [float(hl[str(y)]) for y in ys]
    ax2.semilogy(ys, vs, linewidth=1.9, marker="o", markersize=2.6, color=col, label=lbl)
  ax2.set_ylim(1e5, 4e8)
  apply_human_log_ticks(ax2, arg1_axes="y", arg2_semantic=True)
  ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: fmt_year_label(x)))
  ax2.set_title("B. Post-Independence National Trajectories (1811 to 2026AD)", fontsize=9.5)
  ax2.set_xlabel("Calendar year")
  ax2.set_ylabel("Inhabitants (logarithmic scale)")
  ax2.legend(loc="lower right", fontsize=7.8, frameon=True)

  fig.subplots_adjust(wspace=0.26, left=0.08, right=0.97, top=0.89, bottom=0.14)
  save_viscount_figure(fig, fig_dir / "fig3_preta_long_run_trajectories.png", arg2_dpi=300, arg3_options={"verify_layout": True, "strict_layout": True})
  print("  [ROOT FIGS OK] fig1..fig3 saved.")


def main():
  print("Loading Natural Earth South America vector base layers...")
  sa_geoms, riv_lines = load_south_america_context()
  for rel_dir, stem, title in CHAPTER_META:
    render_chapter_figures(rel_dir, stem, title, sa_geoms, riv_lines)
  render_root_figures(sa_geoms, riv_lines)
  print("ALL PRETA CHAPTER AND ROOT FIGURES GENERATED SUCCESSFULLY.")


if __name__ == "__main__":
  main()
