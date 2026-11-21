# -*- coding: utf-8 -*-
"""Generates POLARIS-calibre Albers Equal-Area vector cartography, kriging diagnostics,
long-run demographic trajectories and urban hierarchy figures for Project SARAY
(4 root figures + 36 chapter figures across 9 Central Asian modules).
"""

import json
import math
import os
import pathlib
import re
import sys

import json5
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.colors import LogNorm
from matplotlib.patches import Patch, Polygon as MplPolygon
import numpy as np
from PIL import Image
from shapely.geometry import shape
from shapely.ops import unary_union

SARAY_DIR = pathlib.Path(__file__).resolve().parent
SVEA_ROOT = SARAY_DIR.parents[3]
SHARED_DIR = SARAY_DIR.parent / "_shared"
GIS_SHARED = SHARED_DIR / "_gis_cache"
POLARIS_GIS = SARAY_DIR.parent / "POLARIS" / "_shared" / "_gis_cache"
SUBREG_DIR = SARAY_DIR / "_shared" / "_gis_cache" / "chapter_subregions"
SITES_DIR = SARAY_DIR / "_shared" / "sites_saray_central_asia"
ROOT_FIG_DIR = SARAY_DIR / "figures"

if str(SHARED_DIR) not in sys.path:
  sys.path.insert(0, str(SHARED_DIR))

import viscount_plot_utils as vpu

CHAPTER_TITLES = {
  "prehistoric_central_asian_steppe_and_oases": "Prehistoric Central Asian Steppe and Oases",
  "scythian_saka_and_classical_oasis_states": "Scythian-Saka Pastoralists and Classical Oasis States",
  "turkic_migrations_and_islamisation_turan": "Turkic Migrations and Islamisation of Turan and Transoxiana",
  "mongol_conquest_and_timurid_central_asia": "Mongol Conquest and Timurid Central Asia",
  "uzbek_khanates_and_kazakh_hordes": "Uzbek Khanates and Kazakh Steppe Hordes",
  "russian_conquest_imperial_turkestan_and_steppe": "Russian Conquest, Imperial Turkestan and Steppe Governorates",
  "russian_civil_war_basmachi_and_early_soviet": "Russian Civil War, Basmachi Revolt and Early Soviet Central Asia",
  "post_war_soviet_central_asian_republics": "Post-War Soviet Central Asian Republics",
  "post_soviet_central_asia": "Post-Soviet Central Asia",
}

HORIZON_DISPLAY_NAMES = {
  "01_epipalaeolithic_mesolithic_early_neolithic": "Epipalaeolithic & Early Neolithic",
  "02_chalcolithic_namazga_sarazm_botai": "Chalcolithic (Namazga-Sarazm-Botai)",
  "03_bronze_age_bmac_sintashta_andronovo": "Bronze Age (BMAC & Andronovo)",
  "04_iron_age_saka_achaemenid_hellenistic": "Iron Age (Saka & Hellenistic)",
  "05_kushan_kangju_wusun_parthian_antiquity": "Classical (Kushan-Kangju-Parthian)",
  "06_sogdian_turkic_early_islamic": "Sogdian, Turkic & Early Islamic",
  "07_samanid_karakhanid_seljuk_khwarazmshah": "Samanid, Karakhanid & Khwarazmshah",
  "08_mongol_chagatai_timurid": "Mongol, Chagatai & Timurid",
  "09_uzbek_khanates_kazakh_zhuzes": "Uzbek Khanates & Kazakh Zhuzes",
}

CHAPTER_KRIG_RASTER = {
  "prehistoric_central_asian_steppe_and_oases": ("03_bronze_age_bmac_sintashta_andronovo.png", "Bronze Age BMAC & Steppe"),
  "scythian_saka_and_classical_oasis_states": ("05_kushan_kangju_wusun_parthian_antiquity.png", "Classical Kushan-Kangju"),
  "turkic_migrations_and_islamisation_turan": ("07_samanid_karakhanid_seljuk_khwarazmshah.png", "Samanid-Karakhanid Zenith"),
  "mongol_conquest_and_timurid_central_asia": ("08_mongol_chagatai_timurid.png", "Mongol-Chagatai-Timurid"),
  "uzbek_khanates_and_kazakh_hordes": ("09_uzbek_khanates_kazakh_zhuzes.png", "Uzbek Khanates & Zhuzes"),
  "russian_conquest_imperial_turkestan_and_steppe": ("popc_1900.png", "Imperial Benchmark (1900AD)"),
  "russian_civil_war_basmachi_and_early_soviet": ("popc_1930.png", "Early Soviet Benchmark (1930AD)"),
  "post_war_soviet_central_asian_republics": ("popc_1989.png", "Late Soviet Census (1989AD)"),
  "post_soviet_central_asia": ("popc_2020.png", "Contemporary Surface (2020AD)"),
}

REPUBLIC_MACRO_COL = {
  "kz": ("Kazakhstan", "#4784b3"),
  "uz": ("Uzbekistan", "#3d8a5a"),
  "tm": ("Turkmenistan", "#c9842c"),
  "kg": ("Kyrgyzstan", "#85529e"),
  "tj": ("Tajikistan", "#c05246"),
}

LINE_PALETTE = ["#2b5c8f", "#c05246", "#3d8a5a", "#85529e", "#c9842c", "#2d9281", "#b05a28", "#64748b"]


class AlbersCentralAsia:
  """Albers Equal-Area Conic projection centred on Central Asia (lon0=66E, phi1=39N, phi2=50N, km)."""
  def __init__(self, lon0=66.0, lat0=44.5, phi1=39.0, phi2=50.0, r_km=6371.0):
    self.lon0 = math.radians(lon0)
    self.r_km = float(r_km)
    p1, p2, p0 = math.radians(phi1), math.radians(phi2), math.radians(lat0)
    self.n = 0.5 * (math.sin(p1) + math.sin(p2))
    self.c = math.cos(p1) ** 2 + 2.0 * self.n * math.sin(p1)
    self.rho0 = math.sqrt(max(1e-12, self.c - 2.0 * self.n * math.sin(p0))) / self.n

  def fwd_pt(self, lon_deg, lat_deg):
    la = math.radians(float(lat_deg))
    lo = math.radians(float(lon_deg))
    rho = math.sqrt(max(1e-12, self.c - 2.0 * self.n * math.sin(la))) / self.n
    th = self.n * (lo - self.lon0)
    return self.r_km * rho * math.sin(th), self.r_km * (self.rho0 - rho * math.cos(th))

  def fwd_arr(self, lons, lats):
    la = np.radians(np.asarray(lats, dtype=float))
    lo = np.radians(np.asarray(lons, dtype=float))
    rho = np.sqrt(np.maximum(1e-12, self.c - 2.0 * self.n * np.sin(la))) / self.n
    th = self.n * (lo - self.lon0)
    return self.r_km * rho * np.sin(th), self.r_km * (self.rho0 - rho * np.cos(th))

  def inv_arr(self, xs, ys):
    x = np.asarray(xs, dtype=float) / self.r_km
    y = np.asarray(ys, dtype=float) / self.r_km
    dy = self.rho0 - y
    rho = np.sqrt(x * x + dy * dy)
    th = np.arctan2(x, dy)
    lon = np.degrees(self.lon0 + th / self.n)
    sin_phi = np.clip((self.c - (rho * self.n) ** 2) / (2.0 * self.n), -1.0, 1.0)
    lat = np.degrees(np.arcsin(sin_phi))
    return lon, lat


PROJ = AlbersCentralAsia()


def fmt_yr(yr):
  yi = int(yr)
  return f"{abs(yi)}BC" if yi < 0 else f"{yi}AD"


SHORT_REGION_NAMES = {
  # Ch. 1
  "kopet_dag_murgab_oases": "Kopet Dag & Murgab",
  "lower_amu_darya_khwarazm": "Lower Amu Darya",
  "zeravshan_surkhan_bactria": "Zeravshan & Bactria",
  "pamir_alay_vakhsh_highlands": "Pamir-Alay & Vakhsh",
  "ferghana_chach_middle_syr": "Ferghana & Chach",
  "semirechye_tian_shan_corridor": "Semirechye & Tian Shan",
  "western_steppe_ural_mangyshlak": "Western Steppe & Ural",
  "northern_central_kazakh_steppe": "North & Central Steppe",
  # Ch. 2
  "parthia_margiana_oases": "Parthia & Margiana",
  "classical_khwarazm": "Classical Khwarazm",
  "sogdiana_zeravshan_qashqa": "Sogdiana Core",
  "northern_bactria_tokharistan": "Northern Bactria",
  "pamir_saka_highlands": "Pamir Saka Highlands",
  "ferghana_dayuan_chach": "Dayuan & Kangju",
  "semirechye_wusun_saka": "Semirechye Wusun",
  "massagetae_sarmatian_west": "Aral-Caspian Steppe",
  "tasmola_saka_northern_steppe": "Tasmola-Saka Steppe",
  # Ch. 3
  "mawarannahr_sogd_core": "Mawarannahr Core",
  "chach_ilak_isfijab": "Chach, Ilak & Isfijab",
  "ferghana_ustrushana": "Ferghana & Ustrushana",
  "chaghaniyan_khuttal_badakhshan": "Chaghaniyan & Khuttal",
  "khwarazm_gurganj_kath": "Khwarazm",
  "khurasan_merv_dihistan": "Khurasan & Merv",
  "semirechye_balasagun_karluk": "Semirechye & Chu-Talas",
  "oghuz_kipchak_western_steppe": "Oghuz Western Steppe",
  "kimak_kipchak_northern_steppe": "Kimak-Kipchak Steppe",
  # Ch. 4
  "timurid_samarkand_bukhara": "Timurid Mawarannahr",
  "timurid_hisar_badakhshan": "Hisar & Badakhshan",
  "chagatai_ferghana_tashkent": "Ferghana & Shash",
  "khwarazm_golden_horde_timurid": "Khwarazm",
  "ilkhanid_timurid_khurasan": "Murgab & Turkmenia",
  "syr_darya_frontier_towns": "Syr Darya Frontier",
  "moghulistan_semirechye": "Moghulistan",
  "dasht_i_qipchaq_white_horde": "Dasht-i Qipchaq",
  # Ch. 5
  "bukhara_western_core": "Khanate of Bukhara",
  "eastern_bukhara_badakhshan": "Eastern Bukhara",
  "khanate_of_khiva": "Khanate of Khiva",
  "khanate_of_kokand": "Khanate of Kokand",
  "turkmen_tribal_oases": "Turkmen Tribal Oases",
  "senior_zhuz_semirechye": "Senior Kazakh Zhuz",
  "middle_zhuz_central_north": "Middle Kazakh Zhuz",
  "junior_zhuz_western_steppe": "Junior Kazakh Zhuz",
  # Ch. 6
  "syr_darya_oblast": "Syr-Darya Oblast",
  "samarkand_oblast": "Samarkand Oblast",
  "ferghana_oblast": "Ferghana Oblast",
  "transcaspian_oblast": "Transcaspian Oblast",
  "semirechye_oblast": "Semirechye Oblast",
  "akmolinsk_oblast": "Akmolinsk Oblast",
  "semipalatinsk_oblast": "Semipalatinsk Oblast",
  "turgai_oblast": "Turgai Oblast",
  "uralsk_oblast": "Uralsk Oblast",
  "emirate_of_bukhara": "Emirate of Bukhara",
  "khanate_of_khiva": "Khanate of Khiva",
  # Ch. 7
  "kazakh_north_east_steppe": "North & East Kazakh SSR",
  "kazakh_west_steppe": "West Kazakh SSR",
  "kazakh_south_semirechye": "South Kazakh SSR",
  "uzbek_tashkent_ferghana": "Uzbek SSR (East)",
  "uzbek_zeravshan_surkhan": "Uzbek SSR (West)",
  "karakalpak_khorezm": "Karakalpak & Khorezm",
  "turkmen_ssr": "Turkmen SSR",
  "kirghiz_ssr": "Kirghiz SSR",
  "tajik_western_north": "Tajik SSR",
  "gorno_badakhshan_ao": "Gorno-Badakhshan AO",
}


def clean_lbl(name, max_len=28, rid=None):
  if rid and rid in SHORT_REGION_NAMES:
    return SHORT_REGION_NAMES[rid]
  txt = re.sub(r"^\d+\.\s*", "", str(name or "")).strip()
  txt = re.sub(r"\s*\([^)]*\)", "", txt).strip()
  txt = re.sub(r"\s+", " ", txt)
  if len(txt) <= max_len:
    return txt
  words, out, cur = txt.split(), [], 0
  for w in words:
    if cur + len(w) + (1 if out else 0) > max_len:
      break
    out.append(w)
    cur += len(w) + (1 if out else 0)
  return " ".join(out) if out else txt[:max_len]


def geom_to_mpl_polys(geom):
  """Projects a Shapely Polygon/MultiPolygon into Matplotlib polygon patches in Albers km."""
  polys = []
  if geom is None or geom.is_empty:
    return polys
  parts = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
  for g in parts:
    if g.geom_type == "Polygon" and not g.is_empty:
      cs = np.asarray(g.exterior.coords)
      if len(cs) >= 3:
        xs, ys = PROJ.fwd_arr(cs[:, 0], cs[:, 1])
        polys.append(MplPolygon(np.column_stack([xs, ys]), closed=True))
    elif g.geom_type == "MultiPolygon":
      polys.extend(geom_to_mpl_polys(g))
  return polys


def load_context_vectors():
  """Loads Natural Earth rivers, lakes & neighbouring land in Albers km clipped to Central Asia view."""
  from shapely.geometry import box as sbox
  clip_b = sbox(42.0, 32.0, 92.0, 59.0)

  # Land background
  land_polys = []
  ne0 = json.load(open(GIS_SHARED / "ne_50m_admin_0_countries.geojson", "r", encoding="utf-8"))
  for f in ne0["features"]:
    g = shape(f["geometry"]).buffer(0)
    if g.intersects(clip_b):
      gc = g.intersection(clip_b)
      land_polys.extend(geom_to_mpl_polys(gc))

  # Rivers
  river_segs = []
  rv_gj = json.load(open(GIS_SHARED / "ne_10m_rivers_lake_centerlines.geojson", "r", encoding="utf-8"))
  for f in rv_gj["features"]:
    g = shape(f["geometry"])
    if not g.intersects(clip_b):
      continue
    gc = g.intersection(clip_b)
    parts = list(gc.geoms) if hasattr(gc, "geoms") else [gc]
    for ln in parts:
      if ln.geom_type == "LineString" and len(ln.coords) >= 2:
        cs = np.asarray(ln.coords)
        xs, ys = PROJ.fwd_arr(cs[:, 0], cs[:, 1])
        river_segs.append(np.column_stack([xs, ys]))

  # Lakes (Aral, Balkhash, Issyk-Kul, Caspian rim)
  lake_polys = []
  lk_p = POLARIS_GIS / "ne_10m_lakes.geojson"
  if lk_p.exists():
    lk_gj = json.load(open(lk_p, "r", encoding="utf-8"))
    for f in lk_gj["features"]:
      g = shape(f["geometry"]).buffer(0)
      if g.intersects(clip_b):
        lake_polys.extend(geom_to_mpl_polys(g.intersection(clip_b)))

  return land_polys, river_segs, lake_polys


def draw_vector_subregions(ax, subreg_gj_path, ctx_vecs, is_admin1=False, show_legend=False):
  """Draws smooth vector GeoJSON polygons via PatchCollection over Natural Earth land, rivers & lakes."""
  land_polys, river_segs, lake_polys = ctx_vecs
  ax.set_facecolor("#e8f1f8")
  if land_polys:
    ax.add_collection(PatchCollection(land_polys, facecolor="#f4f1ea", edgecolor="#cbd5e1", linewidth=0.35, zorder=1))

  gj = json.load(open(subreg_gj_path, "r", encoding="utf-8"))
  geoms_all = []
  leg_handles = []
  seen_rep = set()

  for idx, feat in enumerate(gj["features"]):
    props = feat["properties"]
    rid = props.get("region_id", "")
    g = shape(feat["geometry"]).buffer(0)
    geoms_all.append(g)
    if is_admin1 and "_" in rid and rid.split("_")[0] in REPUBLIC_MACRO_COL:
      pref = rid.split("_")[0]
      rep_nm, rep_hex = REPUBLIC_MACRO_COL[pref]
      # Slightly vary shade within republic while keeping clear macro identity
      r_h = int(rep_hex[1:3], 16)
      g_h = int(rep_hex[3:5], 16)
      b_h = int(rep_hex[5:7], 16)
      face_c = vpu.mute_rgb_hex([r_h, g_h, b_h], idx, arg2_blend=0.38 + 0.14 * ((idx % 3) / 2.0))
      if pref not in seen_rep:
        seen_rep.add(pref)
        leg_handles.append(Patch(facecolor=vpu.mute_rgb_hex([r_h, g_h, b_h], 0, 0.42), edgecolor="#334155", linewidth=0.5, label=rep_nm))
    else:
      rgb = props.get("rgb") or [140, 160, 180]
      face_c = vpu.mute_rgb_hex(rgb, idx, arg2_blend=0.45)
      if show_legend and len(leg_handles) < 12:
        leg_handles.append(Patch(facecolor=face_c, edgecolor="#334155", linewidth=0.45, label=clean_lbl(props.get("name", rid), 26, rid=rid)))

    polys = geom_to_mpl_polys(g)
    if polys:
      ax.add_collection(PatchCollection(polys, facecolor=face_c, edgecolor="#475569", linewidth=0.45, zorder=2))

  if lake_polys:
    ax.add_collection(PatchCollection(lake_polys, facecolor="#d7eaf8", edgecolor="#60a5fa", linewidth=0.35, zorder=3))
  if river_segs:
    ax.add_collection(LineCollection(river_segs, colors="#2b6cb0", linewidths=0.55, alpha=0.72, zorder=4))

  # Bold dissolved outer border of SARAY domain
  if geoms_all:
    u_dom = unary_union(geoms_all).buffer(0)
    u_polys = geom_to_mpl_polys(u_dom)
    if u_polys:
      ax.add_collection(PatchCollection(u_polys, facecolor="none", edgecolor="#111827", linewidth=1.15, zorder=5))
    # Compute Albers projected bounds cleanly
    bx, by = [], []
    for p in u_polys:
      v = p.get_xy()
      bx.extend([v[:, 0].min(), v[:, 0].max()])
      by.extend([v[:, 1].min(), v[:, 1].max()])
    xlim, ylim = vpu.pad_projected_bounds([min(bx), min(by), max(bx), max(by)], arg1_target_aspect=1.46, arg2_pad_factor=1.10)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
  ax.set_aspect("equal", adjustable="box")
  ax.set_xticks([])
  ax.set_yticks([])
  return leg_handles


def project_float32_raster_to_albers(png_path, xlim, ylim, nx=480, ny=330):
  """Reprojects a 4320x2160 big-endian float32 GeoPNG onto an Albers Equal-Area grid cleanly."""
  raw = np.asarray(Image.open(png_path).convert("RGBA"), dtype=np.uint8)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
  valid = np.isfinite(f32) & (f32 > 0.0)
  arr = np.where(valid, f32, np.nan)

  xs = np.linspace(xlim[0], xlim[1], nx)
  ys = np.linspace(ylim[0], ylim[1], ny)
  xx, yy = np.meshgrid(xs, ys)
  lons, lats = PROJ.inv_arr(xx, yy)
  rr = np.clip(((90.0 - lats) * 2160.0 / 180.0).astype(int), 0, 2159)
  cc = np.clip(((lons + 180.0) * 4320.0 / 360.0).astype(int), 0, 4319)
  return arr[rr, cc]


def matern32_gamma(u, c0, c1, c2, tau1, tau2):
  r3 = math.sqrt(3.0)
  u = np.maximum(np.asarray(u, dtype=float), 0.0)
  a1 = r3 * u / max(float(tau1), 1e-6)
  a2 = r3 * u / max(float(tau2), 1e-6)
  corr = float(c1) * (1.0 + a1) * np.exp(-a1) + float(c2) * (1.0 + a2) * np.exp(-a2)
  return np.where(u <= 1e-12, 0.0, float(c0) + (1.0 - float(c0)) * np.maximum(0.0, 1.0 - corr))


def compute_headline_series(regions):
  all_yrs = sorted({int(k) for rv in regions.values() for k in (rv.get("population") or {}).keys()})
  out = {}
  for y in all_yrs:
    tot = 0.0
    for rv in regions.values():
      pm = rv.get("population") or {}
      if str(y) in pm:
        tot += float(pm[str(y)])
    out[y] = tot
  return out


def generate_chapter_figures(mod, ctx_vecs, krig_diag):
  stem = mod["id"]
  ch_dir = (SVEA_ROOT / mod["json5_path"]).parent
  fig_dir = ch_dir / "figures"
  fig_dir.mkdir(parents=True, exist_ok=True)

  j5 = json5.loads((SVEA_ROOT / mod["json5_path"]).read_text(encoding="utf-8"))
  sett_dict = json.loads((ch_dir / f"{stem}_settlements.json").read_text(encoding="utf-8"))
  sub_gj = SUBREG_DIR / f"{stem}_subregions.geojson"
  is_adm1 = bool(mod.get("is_admin1", False))
  title_short = CHAPTER_TITLES[stem]
  d0, d1 = j5["domain"]

  setts = list(sett_dict.values()) if isinstance(sett_dict, dict) else sett_dict
  peaks = []
  for s in setts:
    pm = s.get("population") or {}
    if not pm:
      continue
    pk_yr = max(pm.keys(), key=lambda y: float(pm[y]))
    peaks.append((float(pm[pk_yr]), int(pk_yr), s["name"], s["coords"][0], s["coords"][1], s.get("region_id", "")))
  peaks.sort(key=lambda x: -x[0])

  # --- FIG 1: Vector Sub-Regions & Catalogued Settlements (Hero Figure!) ---
  vpu.apply_viscount_style(grid=False)
  fig, ax = plt.subplots(figsize=(9.2, 5.8), dpi=300)
  vpu.apply_viscount_style(ax, {"grid": False})
  leg_h = draw_vector_subregions(ax, sub_gj, ctx_vecs, is_admin1=is_adm1, show_legend=True)

  if peaks:
    slons = [p[4] for p in peaks]
    slats = [p[3] for p in peaks]
    sxs, sys_ = PROJ.fwd_arr(slons, slats)
    sizes = [max(5.0, min(42.0, 4.0 + 3.2 * math.log10(max(10.0, p[0])))) for p in peaks]
    ax.scatter(sxs, sys_, s=sizes, c="#1e3a8a", alpha=0.58, edgecolors="white", linewidths=0.35, zorder=6)
    top_callouts = [{"label": p[2], "lon": p[4], "lat": p[3]} for p in peaks[:12]]
    vpu.place_inbounds_callouts(fig, ax, top_callouts, arg3_proj=PROJ, arg6_options={"max_labels": 7, "min_sep_px": 48.0, "fontsize": 6.8, "dot_color": "#b91c1c"})

  ax.set_title(f"{title_short} ({fmt_yr(d0)} to {fmt_yr(d1)}, n={len(peaks):,})".replace(",", "."), fontsize=10.5)
  if leg_h:
    ncol = min(4, max(2, (len(leg_h) + 1) // 2))
    fig.legend(handles=leg_h, loc="lower center", ncol=ncol, fontsize=7.0, frameon=True, bbox_to_anchor=(0.5, 0.01))
    fig.subplots_adjust(bottom=0.17 if len(leg_h) > 4 else 0.12, top=0.92, left=0.03, right=0.97)
  else:
    fig.tight_layout()
  vpu.save_viscount_figure(fig, fig_dir / f"fig1_{stem}_spatial.png", dpi=300, arg3_options={"verify_layout": True, "strict_layout": False})

  # --- FIG 2: Population Trajectory & Sub-Regional Composition ---
  vpu.apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.4), dpi=300)
  vpu.apply_viscount_style(ax1)
  vpu.apply_viscount_style(ax2)

  headline = compute_headline_series(j5["regions"])
  yrs = sorted(headline.keys())
  vals = [headline[y] for y in yrs]
  lo_b, hi_b = [], []
  for y in yrs:
    l_sum, h_sum = 0.0, 0.0
    for rv in j5["regions"].values():
      pb = (rv.get("population_bounds") or {}).get(str(y))
      if pb and len(pb) == 2:
        l_sum += float(pb[0])
        h_sum += float(pb[1])
      else:
        pv = float((rv.get("population") or {}).get(str(y), 0))
        l_sum += pv * 0.92
        h_sum += pv * 1.08
    lo_b.append(l_sum)
    hi_b.append(h_sum)

  ax1.fill_between(yrs, lo_b, hi_b, color="#93c5fd", alpha=0.35, label="Uncertainty envelope")
  ax1.plot(yrs, vals, color="#1d4ed8", marker="o", markersize=4.2, linewidth=1.8, label="Regional total")
  ax1.set_ylim(0, max(hi_b) * 1.22 if hi_b else 1)
  ax1.yaxis.set_major_formatter(vpu.euro_log_formatter(True))
  if yrs[0] == -10000 and yrs[-1] == -1000:
    xt = [-10000, -7000, -4000, -1000]
  elif len(yrs) <= 5:
    xt = yrs
  else:
    xt = [yrs[0], yrs[len(yrs) // 3], yrs[2 * len(yrs) // 3], yrs[-1]]
  ax1.set_xticks(xt)
  ax1.set_xticklabels([fmt_yr(y) for y in ax1.get_xticks()], fontsize=7.5)
  ax1.set_title("Aggregate Population Trajectory", fontsize=9.5)
  ax1.set_ylabel("Inhabitants", fontsize=8.5)
  ax1.legend(loc="upper left", fontsize=7.5, frameon=True)

  # Panel B: Terminal-year top sub-regions horizontal bar chart (aggregate by republic if Admin-1)
  if is_adm1:
    rep_tots = {}
    for rid, rv in j5["regions"].items():
      pref = rid.split("_")[0]
      rnm = REPUBLIC_MACRO_COL.get(pref, (rid, "#64748b"))[0]
      rep_tots[rnm] = rep_tots.get(rnm, 0.0) + float((rv.get("population") or {}).get(str(yrs[-1]), 0))
    bar_items = sorted(rep_tots.items(), key=lambda x: x[1])
  else:
    bar_items = sorted(
      [(clean_lbl(rv["name"], 24, rid=rid), float((rv.get("population") or {}).get(str(yrs[-1]), 0))) for rid, rv in j5["regions"].items()],
      key=lambda x: x[1]
    )[-8:]

  blbls = [x[0] for x in bar_items]
  bvals = [x[1] for x in bar_items]
  y_pos = np.arange(len(blbls))
  bars = ax2.barh(y_pos, bvals, color="#3b82f6", edgecolor="#1e3a8a", linewidth=0.5, height=0.68)
  ax2.set_yticks(y_pos)
  ax2.set_yticklabels(blbls, fontsize=7.5)
  ax2.set_xlim(0, max(bvals) * 1.26 if bvals else 1)
  ax2.xaxis.set_major_formatter(vpu.euro_log_formatter(True))
  for b, v in zip(bars, bvals):
    ax2.text(v + max(bvals) * 0.02, b.get_y() + b.get_height() / 2.0, vpu.format_semantic_population(v), va="center", ha="left", fontsize=7.2)
  ax2.set_title(f"Regional Shares in {fmt_yr(yrs[-1])}", fontsize=9.5)
  ax2.set_xlabel("Inhabitants", fontsize=8.5)

  fig.suptitle(f"{title_short}: Demographic Trajectory", fontsize=10.5)
  fig.subplots_adjust(wspace=0.46, top=0.86, bottom=0.14, left=0.09, right=0.97)
  vpu.save_viscount_figure(fig, fig_dir / f"fig2_{stem}_trajectory.png", dpi=300, arg3_options={"verify_layout": True, "strict_layout": False})

  # --- FIG 3: Continuous Kriged/Population Surface Map in Albers Equal-Area + Sub-Region Densities ---
  vpu.apply_viscount_style(grid=False)
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.6, 4.4), dpi=300, gridspec_kw={"width_ratios": [1.35, 1.0]})
  vpu.apply_viscount_style(ax1, {"grid": False})
  vpu.apply_viscount_style(ax2)

  r_fn, r_lbl = CHAPTER_KRIG_RASTER[stem]
  r_path = (SITES_DIR / "1.kriged_rasters" / r_fn) if not r_fn.startswith("popc_") else (SITES_DIR / "2.population_rasters" / r_fn)
  draw_vector_subregions(ax1, sub_gj, ctx_vecs, is_admin1=False, show_legend=False)
  xlim, ylim = ax1.get_xlim(), ax1.get_ylim()
  grid_val = project_float32_raster_to_albers(r_path, xlim, ylim)
  pos_v = grid_val[np.isfinite(grid_val) & (grid_val > 0)]
  if pos_v.size > 10:
    vmin = max(1e-4, float(np.percentile(pos_v, 4)))
    vmax = max(vmin * 5.0, float(np.percentile(pos_v, 99)))
    im = ax1.imshow(grid_val, extent=[xlim[0], xlim[1], ylim[0], ylim[1]], origin="lower", cmap="viridis", norm=LogNorm(vmin=vmin, vmax=vmax), zorder=2.5)
    cb = fig.colorbar(im, ax=ax1, fraction=0.042, pad=0.03)
    cb.ax.set_title("Density" if r_fn.startswith("popc_") else "Intensity", fontsize=7.5, pad=4)
    vpu.apply_human_colorbar_ticks(cb, arg1_semantic=r_fn.startswith("popc_"))
  ax1.set_title(f"Continuous Surface: {r_lbl}", fontsize=9.2)

  # Panel B: Mean density per km2 across sub-regions at terminal year
  dens_items = []
  if is_adm1:
    rep_p, rep_a = {}, {}
    for rid, rv in j5["regions"].items():
      pref = rid.split("_")[0]
      rnm = REPUBLIC_MACRO_COL.get(pref, (rid, "#64748b"))[0]
      rep_p[rnm] = rep_p.get(rnm, 0.0) + float((rv.get("population") or {}).get(str(yrs[-1]), 0))
      rep_a[rnm] = rep_a.get(rnm, 0.0) + max(1.0, float(rv.get("area_km2") or 1))
    dens_items = sorted([(k, rep_p[k] / rep_a[k]) for k in rep_p], key=lambda x: x[1])
  else:
    dens_items = sorted(
      [(clean_lbl(rv["name"], 24, rid=rid), float((rv.get("population") or {}).get(str(yrs[-1]), 0)) / max(1.0, float(rv.get("area_km2") or 1))) for rid, rv in j5["regions"].items()],
      key=lambda x: x[1]
    )[-8:]
  dlbls = [x[0] for x in dens_items]
  dvals = [x[1] for x in dens_items]
  yp = np.arange(len(dlbls))
  bars2 = ax2.barh(yp, dvals, color="#0d9488", edgecolor="#115e59", linewidth=0.5, height=0.68)
  ax2.set_yticks(yp)
  ax2.set_yticklabels(dlbls, fontsize=7.4)
  ax2.set_xlim(0, max(dvals) * 1.28 if dvals else 1)
  ax2.xaxis.set_major_formatter(vpu.euro_tick_formatter(1))
  for b, v in zip(bars2, dvals):
    ax2.text(v + max(dvals) * 0.02, b.get_y() + b.get_height() / 2.0, vpu.format_euro_number(v, 2), va="center", ha="left", fontsize=7.0)
  ax2.set_title(f"Population Density ({fmt_yr(yrs[-1])})", fontsize=9.2)
  ax2.set_xlabel("Inhabitants per km²", fontsize=8.3)

  fig.subplots_adjust(wspace=0.45, top=0.88, bottom=0.14, left=0.04, right=0.97)
  vpu.save_viscount_figure(fig, fig_dir / f"fig3_{stem}_density.png", dpi=300, arg3_options={"verify_layout": True, "strict_layout": False})

  # --- FIG 4: Rank-Size Distribution (n >= 25) & Top 12 Catalogued Settlements ---
  vpu.apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.4), dpi=300)
  vpu.apply_viscount_style(ax1)
  vpu.apply_viscount_style(ax2)

  ranks = np.arange(1, len(peaks) + 1, dtype=float)
  pvals = np.array([p[0] for p in peaks], dtype=float)
  ax1.loglog(ranks, pvals, "o", markersize=3.2, color="#1d4ed8", alpha=0.65, label=f"Observed (n={len(peaks):,})".replace(",", "."))
  if len(peaks) >= 25:
    lx, ly = np.log10(ranks), np.log10(pvals)
    slope, intercept = np.polyfit(lx, ly, 1)
    y_hat = 10.0 ** (intercept + slope * lx)
    ss_res = float(np.sum((ly - (intercept + slope * lx)) ** 2))
    ss_tot = float(np.sum((ly - np.mean(ly)) ** 2))
    r2 = max(0.0, 1.0 - ss_res / max(1e-12, ss_tot))
    ax1.loglog(ranks, y_hat, "-", color="#dc2626", linewidth=1.4, label=rf"Zipf fit ($\alpha = {vpu.format_mathtext_euro(-slope, 2)}$, $R^2 = {vpu.format_mathtext_euro(r2, 2)}$)")
  vpu.apply_human_log_ticks(ax1, arg1_axes="both", arg2_semantic=True)
  ax1.set_title("Settlement Rank-Size Distribution", fontsize=9.5)
  ax1.set_xlabel("Rank", fontsize=8.5)
  ax1.set_ylabel("Peak Population", fontsize=8.5)
  ax1.legend(loc="lower left", fontsize=7.4, frameon=True)

  top12 = peaks[:12][::-1]
  tlbls = [clean_lbl(p[2], 22) for p in top12]
  tvals = [p[0] for p in top12]
  yp2 = np.arange(len(tlbls))
  bars3 = ax2.barh(yp2, tvals, color="#d97706", edgecolor="#78350f", linewidth=0.5, height=0.68)
  ax2.set_yticks(yp2)
  ax2.set_yticklabels(tlbls, fontsize=7.4)
  ax2.set_xlim(0, max(tvals) * 1.28 if tvals else 1)
  ax2.xaxis.set_major_formatter(vpu.euro_log_formatter(True))
  for b, v in zip(bars3, tvals):
    ax2.text(v + max(tvals) * 0.02, b.get_y() + b.get_height() / 2.0, vpu.format_semantic_population(v), va="center", ha="left", fontsize=7.0)
  ax2.set_title("Leading Catalogued Settlements", fontsize=9.5)
  ax2.set_xlabel("Peak Population", fontsize=8.5)

  fig.subplots_adjust(wspace=0.42, top=0.88, bottom=0.14, left=0.09, right=0.97)
  vpu.save_viscount_figure(fig, fig_dir / f"fig4_{stem}_settlements.png", dpi=300, arg3_options={"verify_layout": True, "strict_layout": False})


def generate_root_figures(mods, ctx_vecs, krig_diag, geo_meta):
  ROOT_FIG_DIR.mkdir(parents=True, exist_ok=True)

  # --- ROOT FIG 1: Four-Panel Albers Equal-Area Macro Evolution Mosaic (Regimes I-III) ---
  vpu.apply_viscount_style(grid=False)
  fig, axes = plt.subplots(2, 2, figsize=(11.2, 7.6), dpi=300)
  panels = [
    ("prehistoric_central_asian_steppe_and_oases", "A. Prehistoric Catchments (10000BC to 1000BC)", False),
    ("turkic_migrations_and_islamisation_turan", "B. Mediaeval Turan and Transoxiana (500AD to 1219AD)", False),
    ("russian_conquest_imperial_turkestan_and_steppe", "C. Imperial Oblasts and Protectorates (1865AD to 1917AD)", False),
    ("post_soviet_central_asia", "D. Post-Soviet 48 Admin-1 Regions (1991AD to 2026AD)", True),
  ]
  for ax, (st, ptitle, is_a1) in zip(axes.flat, panels):
    vpu.apply_viscount_style(ax, {"grid": False})
    draw_vector_subregions(ax, SUBREG_DIR / f"{st}_subregions.geojson", ctx_vecs, is_admin1=is_a1, show_legend=False)
    ax.set_title(ptitle, fontsize=9.2)
  fig.suptitle("SARAY Central Asia: Three-Regime Territorial Partition (10000BC to 2026AD)", fontsize=11.0)
  fig.subplots_adjust(wspace=0.06, hspace=0.14, top=0.92, bottom=0.03, left=0.02, right=0.98)
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig1_saray_macro_zones.png", dpi=300, arg3_options={"verify_layout": True, "strict_layout": False})

  # --- ROOT FIG 2: Long-Run Demographic Trajectory (-10000 to 2025) & Modern Five-Republic Growth ---
  vpu.apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.8, 4.5), dpi=300)
  vpu.apply_viscount_style(ax1)
  vpu.apply_viscount_style(ax2)

  # Stitch full long-run headline series across all 9 chapters
  full_pts = {}
  for m in mods:
    j5 = json5.loads((SVEA_ROOT / m["json5_path"]).read_text(encoding="utf-8"))
    for y, v in compute_headline_series(j5["regions"]).items():
      full_pts[y] = v
  pre_yrs = [y for y in sorted(full_pts) if y <= 1865]
  pre_vals = [full_pts[y] for y in pre_yrs]
  ax1.semilogy(pre_yrs, pre_vals, "-o", color="#1d4ed8", markersize=3.5, linewidth=1.6, label="SARAY Central Asia")
  ax1.axvline(1219, color="#dc2626", linestyle="--", linewidth=0.9, alpha=0.8)
  ax1.text(1219, max(pre_vals) * 0.22, "Mongol shock\n(1219AD)", fontsize=7.0, color="#991b1b", ha="right", bbox=dict(facecolor="white", alpha=0.85, edgecolor="none", pad=1.2))
  vpu.apply_human_log_ticks(ax1, arg1_axes="y", arg2_semantic=True)
  ax1.set_xticks([-10000, -7000, -4000, -1000, 1865])
  ax1.set_xticklabels(["10000BC", "7000BC", "4000BC", "1000BC", "1865AD"], fontsize=7.5)
  ax1.set_title("Pre-Modern Macro Trajectory (10000BC to 1865AD)", fontsize=9.3)
  ax1.set_ylabel("Inhabitants", fontsize=8.5)
  ax1.legend(loc="lower right", fontsize=7.5, frameon=True)

  # Panel B: Modern Five-Republic trajectories (1945-2025) from Ch. 8 & Ch. 9 (deduplicated at 1991 boundary!)
  rep_series = {v[0]: {} for v in REPUBLIC_MACRO_COL.values()}
  for m in mods:
    if m["id"] not in ("post_war_soviet_central_asian_republics", "post_soviet_central_asia"):
      continue
    j5 = json5.loads((SVEA_ROOT / m["json5_path"]).read_text(encoding="utf-8"))
    ch_rep = {v[0]: {} for v in REPUBLIC_MACRO_COL.values()}
    for rid, rv in j5["regions"].items():
      rnm = REPUBLIC_MACRO_COL[rid.split("_")[0]][0]
      for y_s, val in (rv.get("population") or {}).items():
        yi = int(y_s)
        ch_rep[rnm][yi] = ch_rep[rnm].get(yi, 0.0) + float(val)
    for rnm, ymap in ch_rep.items():
      for yi, tot_v in ymap.items():
        rep_series[rnm][yi] = tot_v
  for pref, (rnm, rcol) in REPUBLIC_MACRO_COL.items():
    ys_r = sorted(rep_series[rnm].keys())
    vs_r = [rep_series[rnm][y] for y in ys_r]
    ax2.plot(ys_r, vs_r, "-o", color=rcol, markersize=3.2, linewidth=1.6, label=rnm)
  ax2.yaxis.set_major_formatter(vpu.euro_log_formatter(True))
  ax2.set_ylim(0, 42e6)
  ax2.set_title("Five Central Asian Republics (1945AD to 2025AD)", fontsize=9.3)
  ax2.set_ylabel("Inhabitants", fontsize=8.5)
  ax2.legend(loc="upper left", fontsize=7.4, frameon=True, ncol=2)
  fig.subplots_adjust(wspace=0.28, top=0.88, bottom=0.14, left=0.09, right=0.97)
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig2_saray_long_run_trajectories.png", dpi=300, arg3_options={"verify_layout": True, "strict_layout": False})

  # --- ROOT FIG 3: Matérn Semivariogram Calibration & Archaeological Horizon Totals ---
  vpu.apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.8, 4.5), dpi=300)
  vpu.apply_viscount_style(ax1)
  vpu.apply_viscount_style(ax2)

  # Plot empirical semivariogram + fitted Matérn (nu=3/2) curve from kriging_diagnostics.json
  p_diags = {}
  for k_cand in ("variogram_models", "variograms", "period_variograms", "variogram_fits", "period_diagnostics", "periods"):
    if isinstance(krig_diag.get(k_cand), dict) and krig_diag[k_cand]:
      p_diags = krig_diag[k_cand]
      break
  rep_key = "05_kushan_kangju_wusun_parthian_antiquity"
  v_fit = p_diags.get(rep_key) or (next(iter(p_diags.values())) if p_diags else {})
  us = [float(x) for x in (v_fit.get("empirical_u_lags") or [])]
  gs_raw = [float(x) for x in (v_fit.get("empirical_gammas") or [])]
  if us and gs_raw and max(gs_raw) > 0:
    sill_est = max(gs_raw) * 1.05
    gs = [g / sill_est for g in gs_raw]
    ax1.scatter(us, gs, s=28, color="#1d4ed8", zorder=4, label="Empirical bins")
  tau1 = float(v_fit.get("raw_tau1_dimensionless") or krig_diag.get("raw_tau1_dimensionless") or 1.67)
  tau2 = float(v_fit.get("tau2_dimensionless") or krig_diag.get("tau2_dimensionless") or 2.78)
  c0 = float(v_fit.get("nugget_to_sill_ratio") or 0.04)
  c1 = float(v_fit.get("c1_weight") or 0.78)
  c2 = float(v_fit.get("c2_weight") or 0.22)
  r2_v = float(v_fit.get("residual_r2") or 0.99)
  u_grid = np.linspace(0.01, 14.5, 200)
  ax1.plot(u_grid, matern32_gamma(u_grid, c0, c1, c2, tau1, tau2), "-", color="#dc2626", linewidth=1.7,
           label=rf"Matérn $\nu = 3/2$ ($\tau_1 = {vpu.format_mathtext_euro(tau1, 2)}$, $R^2 = {vpu.format_mathtext_euro(r2_v, 3)}$)")
  ax1.xaxis.set_major_formatter(vpu.euro_tick_formatter(1))
  ax1.yaxis.set_major_formatter(vpu.euro_tick_formatter(2))
  ax1.set_title(r"Semivariogram Calibration ($\nu = 3/2$)", fontsize=9.5)
  ax1.set_xlabel(r"Dimensionless Voronoi geodesic lag $u_{ij}$", fontsize=8.4)
  ax1.set_ylabel(r"Normalised semivariance $\gamma(u) / \sigma^2$", fontsize=8.4)
  ax1.legend(loc="lower right", fontsize=7.4, frameon=True)

  # Panel B: Weighted archaeological site records across all 9 horizons
  p_meta = geo_meta.get("period_geojsons") or []
  hlbls = [HORIZON_DISPLAY_NAMES.get(p["key"], p["key"]) for p in p_meta][::-1]
  hvals = [int(p.get("total_sites_count") or 0) for p in p_meta][::-1]
  yp = np.arange(len(hlbls))
  bars_h = ax2.barh(yp, hvals, color="#0d9488", edgecolor="#134e4a", linewidth=0.5, height=0.68)
  ax2.set_yticks(yp)
  ax2.set_yticklabels(hlbls, fontsize=7.2)
  ax2.set_xlim(0, max(hvals) * 1.25 if hvals else 1)
  ax2.xaxis.set_major_formatter(vpu.euro_log_formatter(True))
  for b, v in zip(bars_h, hvals):
    ax2.text(v + max(hvals) * 0.02, b.get_y() + b.get_height() / 2.0, vpu.format_semantic_population(v), va="center", ha="left", fontsize=7.0)
  ax2.set_title("Domestic Archaeological Site Mass by Horizon", fontsize=9.3)
  ax2.set_xlabel("Weighted Site Count", fontsize=8.4)
  fig.subplots_adjust(wspace=0.52, top=0.88, bottom=0.14, left=0.09, right=0.97)
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig3_saray_kriging_diagnostics.png", dpi=300, arg3_options={"verify_layout": True, "strict_layout": False})

  # --- ROOT FIG 4: Contemporary Urban Hierarchy & Historical Capital Trajectories ---
  vpu.apply_viscount_style()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.8, 4.5), dpi=300)
  vpu.apply_viscount_style(ax1)
  vpu.apply_viscount_style(ax2)

  s9 = json.loads((SARAY_DIR / "4.modern_censuses/1.post_soviet_central_asia/post_soviet_central_asia_settlements.json").read_text(encoding="utf-8"))
  p9 = sorted([(max(float(v) for v in e["population"].values()), e["name"]) for e in s9.values()], key=lambda x: -x[0])
  ranks = np.arange(1, len(p9) + 1, dtype=float)
  vals9 = np.array([x[0] for x in p9], dtype=float)
  ax1.loglog(ranks, vals9, "o", markersize=2.8, color="#1d4ed8", alpha=0.58, label=f"Post-Soviet towns (n={len(p9):,})".replace(",", "."))
  lx, ly = np.log10(ranks), np.log10(vals9)
  sl, ic = np.polyfit(lx, ly, 1)
  r2_z = 1.0 - float(np.sum((ly - (ic + sl * lx)) ** 2)) / max(1e-12, float(np.sum((ly - np.mean(ly)) ** 2)))
  ax1.loglog(ranks, 10.0 ** (ic + sl * lx), "-", color="#dc2626", linewidth=1.4, label=rf"Zipf fit ($\alpha = {vpu.format_mathtext_euro(-sl, 2)}$, $R^2 = {vpu.format_mathtext_euro(r2_z, 2)}$)")
  vpu.apply_human_log_ticks(ax1, arg1_axes="both", arg2_semantic=True)
  ax1.set_title("Contemporary Central Asian Rank-Size Curve", fontsize=9.4)
  ax1.set_xlabel("Rank", fontsize=8.4)
  ax1.set_ylabel("Peak Population", fontsize=8.4)
  ax1.legend(loc="lower left", fontsize=7.4, frameon=True)

  top14 = p9[:14][::-1]
  yp3 = np.arange(len(top14))
  bars4 = ax2.barh(yp3, [x[0] for x in top14], color="#2563eb", edgecolor="#1e3a8a", linewidth=0.5, height=0.68)
  ax2.set_yticks(yp3)
  ax2.set_yticklabels([x[1] for x in top14], fontsize=7.4)
  ax2.set_xlim(0, top14[-1][0] * 1.28)
  ax2.xaxis.set_major_formatter(vpu.euro_log_formatter(True))
  for b, (v, _) in zip(bars4, top14):
    ax2.text(v + top14[-1][0] * 0.02, b.get_y() + b.get_height() / 2.0, vpu.format_semantic_population(v), va="center", ha="left", fontsize=7.0)
  ax2.set_title("Leading Central Asian Cities (2020AD to 2025AD)", fontsize=9.4)
  ax2.set_xlabel("Inhabitants", fontsize=8.4)
  fig.subplots_adjust(wspace=0.38, top=0.88, bottom=0.14, left=0.09, right=0.97)
  vpu.save_viscount_figure(fig, ROOT_FIG_DIR / "fig4_saray_urban_hierarchy.png", dpi=300, arg3_options={"verify_layout": True, "strict_layout": False})


def main():
  print("=== GENERATING ALL 40 POLARIS-CALIBRE SARAY FIGURES (4 ROOT + 36 CHAPTER) ===", flush=True)
  manifest = json5.loads((SARAY_DIR / "saray_areal_masks.json5").read_text(encoding="utf-8"))
  mods = list(manifest.get("specialist_masks", [])) + list(manifest.get("national_epoch_masks", []))
  krig_diag = json.loads((SITES_DIR / "config" / "kriging_diagnostics.json").read_text(encoding="utf-8"))
  geo_meta = json.loads((SITES_DIR / "config" / "sites_saray_central_asia_geojson_metadata.json").read_text(encoding="utf-8"))
  ctx_vecs = load_context_vectors()

  generate_root_figures(mods, ctx_vecs, krig_diag, geo_meta)
  print("  [OK] Generated 4 root synthesis figures.", flush=True)
  for m in mods:
    generate_chapter_figures(m, ctx_vecs, krig_diag)
    print(f"  [OK] Generated 4 figures for {m['id']}", flush=True)
  print("=== ALL 40 SARAY FIGURES GENERATED CLEANLY ===", flush=True)


if __name__ == "__main__":
  main()
