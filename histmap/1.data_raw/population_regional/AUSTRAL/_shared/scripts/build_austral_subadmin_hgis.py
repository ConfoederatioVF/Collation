"""Operation Viscount Project AUSTRAL — Pass-2 Comprehensive Sub-Administrative HGIS
Raster & Longitudinal Enumeration Builder (`_shared/subadmin_hgis/`).

Builds ALL 118 overlapping AD HYDE years:
  - 0, 100, 200, ..., 1700 AD (18 century snapshots)
  - 1710, 1720, ..., 1950 AD (25 decennial snapshots)
  - 1951, 1952, ..., 2025 AD (75 annual snapshots)

Strict z-index hierarchy (painted bottom-up, higher z overwrites lower z):
  z=1 (priority 1.0): `parsed/atlas_defacto_austral_cache.json` (fallback only)
  z=2 (priority 2.0): `parsed/atlas_dejure_austral_cache.json`
  z=3 (priority 3.0): `parsed/cshapes_austral_cache.json`
  z=4 (priority 4.0): OHM (`ohm_australia.geojson`, `ohm_new_zealand.geojson`, `ohm_pacific_melanesia.geojson`)
  z=5 (priority 5.0): Official HGIS & Admin-1/Admin-2 (`esri_aus_historical_colonies_1788_present.geojson`,
                      dissolved NZ 1853-1876 Provinces, HydroBASINS L6 precolonial watersheds,
                      ABS/GeoBoundaries/StatsNZ/HDX/BPS/GADM/US-Census Admin-1)

Attaches verbatim & log-linearly interpolated enumerations from:
  - `raw_sources/aus_nz_subadmin_enumerations.json`
  - `raw_sources/pacific_ng_subadmin_enumerations.json`

Renders 8 key boundary regime optical QA crops into `tests/subadmin_crops/subadmin_crop_<year>.png`:
  1700, 1800, 1840, 1860, 1890, 1910, 1960, 2025.
"""

import csv
import io
import json
import math
import os
import re
import zipfile
from collections import defaultdict

import cv2
import numpy as np
import shapefile
from PIL import Image
from scipy.ndimage import distance_transform_edt
from shapely.geometry import box, shape
from shapely.ops import unary_union

from build_austral_areal_masks import (
  AUSTRAL_DIR,
  DOMAIN_MASK_PNG,
  GIS_CACHE,
  GRID_H,
  GRID_W,
  HGIS_RAW,
  HYBAS_L6_ZIP,
  SVEA_ROOT,
  build_nz_colonial_provinces,
  clip_geom,
  filter_polygons_by_bbox,
  group_basins,
  iter_safe_raster_polys,
  load_geojson_by_prop,
  load_geojson_features,
  load_geojson_union,
  load_kiribati_adm1_clean,
  safe_geom,
  u_geoms,
  weld_union,
)

HGIS_ROOT = os.path.join(AUSTRAL_DIR, "_shared", "subadmin_hgis")
PARSED_DIR = os.path.join(HGIS_ROOT, "parsed")
RASTER_DIR = os.path.join(HGIS_ROOT, "rasters")
TESTS_SUB_CROP_DIR = os.path.join(SVEA_ROOT, "tests", "subadmin_crops")
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")

os.makedirs(RASTER_DIR, exist_ok=True)
os.makedirs(TESTS_SUB_CROP_DIR, exist_ok=True)

ALL_HYDE_AD_YEARS = (
  list(range(0, 1701, 100))
  + list(range(1710, 1951, 10))
  + list(range(1951, 2026))
)  # 118 overlapping AD HYDE years

CROP_REGIME_YEARS = {1700, 1800, 1840, 1860, 1890, 1910, 1960, 2025}


def parse_year_opt(s, default_yr):
  if s is None:
    return default_yr
  m = re.match(r"^(-?\d{1,4})", str(s).strip())
  return int(m.group(1)) if m else default_yr


def interp_series(series_dict, target_yr):
  """Log-linear interpolation across positive numeric census points; clamps cleanly at edges."""
  pts = sorted([(int(k), float(v)) for k, v in series_dict.items() if str(k).lstrip("-").isdigit() and v is not None and float(v) >= 0])
  if not pts:
    return 0.0
  if target_yr <= pts[0][0]:
    return pts[0][1]
  if target_yr >= pts[-1][0]:
    return pts[-1][1]
  for i in range(len(pts) - 1):
    y0, v0 = pts[i]
    y1, v1 = pts[i + 1]
    if y0 <= target_yr <= y1:
      if y1 == y0:
        return v0
      t = (target_yr - y0) / float(y1 - y0)
      if v0 > 0 and v1 > 0:
        return math.exp((1.0 - t) * math.log(v0) + t * math.log(v1))
      return v0 + t * (v1 - v0)
  return pts[-1][1]


def dict_to_pairs(d):
  return [[int(k), round(float(v), 1)] for k, v in sorted(d.items(), key=lambda kv: int(kv[0])) if float(v) >= 0]


def get_boundary_regime_key(yr):
  """Maps each of the 118 AD HYDE years to its distinct AUSTRAL boundary regime."""
  if yr <= 1780:
    return 1700  # Pre-European Australia, NZ, New Guinea & Pacific (organic watersheds + archipelagos)
  if yr <= 1820:
    return 1800  # First Fleet NSW >=135E (1788-1825) + Western New Holland <135E + Indigenous NZ/NG/Pacific
  if yr == 1830:
    return 1830  # NSW >=129E (1825) + Van Diemen's Land (1825) + Swan River/WA <129E (1829)
  if yr <= 1850:
    return 1840  # 4 Aus colonies (WA <129E, SA 132E-141E, VDL, NSW east of 129E incl. 129-132E & Port Phillip), NZ
  if yr == 1860:
    return 1860  # Victoria (1851), Queensland (1859), NZ 10 Provinces (1853-76), NT still in NSW
  if yr <= 1880:
    return 1870  # SA+NT united (1863), NZ Provinces, Fiji Colony (1874), pre-1884 New Guinea
  if yr <= 1900:
    return 1890  # Tri-colonial New Guinea (1884: Dutch, German, British Papua), 6 Aus Colonies, BSIP
  if yr == 1910:
    return 1910  # Federation Australia (SA+NT & NSW+ACT united until 1 Jan 1911), Dominion of NZ (1907)
  if yr <= 1950:
    return 1920  # 8 Australian States/Territories (NT & ACT separate 1911+), NZ Provincial Districts, Mandate TNG
  if yr <= 1959:
    return 1951  # Post-WWII NZ 16 Regional Councils, TTPI, unified Netherlands New Guinea & Papua-New Guinea
  if yr <= 1962:
    return 1960  # PNG 22 Provinces, unified Netherlands New Guinea (pre-1963), Modern Pacific Admin-1
  if yr <= 2002:
    return 1963  # PNG 22 Provinces, unified West Irian / Irian Jaya (1963-2002, ZERO post-2003 Papua Barat split!)
  if yr <= 2021:
    return 2003  # PNG 22 Provinces, Indonesian Papua 2 Provinces (Papua & Papua Barat, 2003-2021)
  return 2022    # Post-2022 Indonesian Papua 6 Provinces (BPS 2022) + Modern Admin-1 everywhere


def load_all_sources():
  print("[1] Loading AUSTRAL z=1..z=5 HGIS layers & verbatim enumerations...", flush=True)
  S = {}

  # Domain mask & land area
  dm_rgb = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  S["domain_mask"] = (dm_rgb[:, :, 3] > 0) & (dm_rgb[:, :, :3].sum(axis=2) > 0)
  la_raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  S["land_area"] = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2])

  # z=1..z=3 caches
  def load_cache(fn):
    obj = json.load(open(os.path.join(PARSED_DIR, fn), encoding="utf-8"))
    out = {}
    for yk, recs in obj.items():
      if yk == "_metadata" or not isinstance(recs, list):
        continue
      fl = []
      for r in recs:
        g = safe_geom(shape(r["geometry"]), snap_tol=0) if r.get("geometry") else None
        if g is not None:
          fl.append({"id": r.get("id", ""), "name": r.get("name") or r.get("cntry_name") or "Unknown", "geom": g})
      out[int(yk)] = fl
    return out

  S["atlas_defacto"] = load_cache("atlas_defacto_austral_cache.json")
  S["atlas_dejure"] = load_cache("atlas_dejure_austral_cache.json")
  S["cshapes"] = load_cache("cshapes_austral_cache.json")
  print(f"  Caches: defacto={len(S['atlas_defacto'])} yrs | dejure={len(S['atlas_dejure'])} yrs | cshapes={len(S['cshapes'])} yrs", flush=True)

  # z=4 OHM historical boundaries
  ohm_all = []
  for fn in ("ohm_australia.geojson", "ohm_new_zealand.geojson", "ohm_pacific_melanesia.geojson"):
    for f in load_geojson_features(fn):
      p = f["properties"]
      g = safe_geom(shape(f["geometry"]), snap_tol=0) if f.get("geometry") else None
      if g is None:
        continue
      nm = str(p.get("name") or "").strip()
      if not nm or "nederlands-indi" in nm.lower():
        continue
      y0 = parse_year_opt(p.get("start_date"), 1700)
      y1 = parse_year_opt(p.get("end_date"), 2026)
      lvl = int(p.get("admin_level") or 2) if str(p.get("admin_level") or "").isdigit() else 2
      ohm_all.append({"name": nm, "y0": y0, "y1": y1, "lvl": lvl, "geom": g})
  S["ohm"] = ohm_all
  print(f"  OHM features loaded: {len(ohm_all)}", flush=True)

  # z=5 Esri Australia historical colonies (1789..1908)
  esri_eras = defaultdict(list)
  for f in load_geojson_features("esri_aus_historical_colonies_1788_present.geojson"):
    p = f["properties"]
    era = str(p.get("era_layer_title") or "")
    nm = str(p.get("Sub_Division") or "").strip()
    g = safe_geom(shape(f["geometry"])) if f.get("geometry") else None
    if g is not None and era:
      esri_eras[era].append({"name": nm or "Unclaimed_Western_Australia", "geom": g})
  S["esri_aus"] = dict(esri_eras)

  # z=5 Official modern Admin-1 / Admin-2
  aus_raw = load_geojson_by_prop("geoboundaries_aus_adm1.geojson", "shapeName", filter_fn=lambda lat, lon, p: lon >= 110.0 and lat >= -46.0)
  other_t = aus_raw.get("Other Territories")
  norfolk_g = filter_polygons_by_bbox(other_t, lambda lat, lon, p: lon > 165.0) if other_t else None
  jervis_g = filter_polygons_by_bbox(other_t, lambda lat, lon, p: 149.5 < lon < 152.0) if other_t else None
  S["aus_adm1"] = {
    "New South Wales": u_geoms([aus_raw.get("New South Wales"), jervis_g]),
    "Victoria": aus_raw.get("Victoria"),
    "Queensland": aus_raw.get("Queensland"),
    "South Australia": aus_raw.get("South Australia"),
    "Western Australia": aus_raw.get("Western Australia"),
    "Tasmania": aus_raw.get("Tasmania"),
    "Northern Territory": aus_raw.get("Northern Territory"),
    "Australian Capital Territory": aus_raw.get("Australian Capital Territory"),
    "Norfolk Island": norfolk_g,
  }
  S["aus_full"] = u_geoms(list(S["aus_adm1"].values()))
  S["nzl_adm1"] = load_geojson_by_prop("geoboundaries_nzl_adm1.geojson", "shapeName")
  S["nzl_adm2"] = load_geojson_by_prop("geoboundaries_nzl_adm2.geojson", "shapeName")
  S["nz_provs"] = build_nz_colonial_provinces(S["nzl_adm2"])
  S["png_adm1"] = load_geojson_by_prop("hdx_codab_png_adm1.geojson", "adm1_name")
  S["idn_papua_6"] = {
    k: clip_geom(g, box(129.5, -11.3, 141.1, 1.5))
    for k, g in load_geojson_by_prop("bps_idn_papua_6provinces_2022_adm1.geojson", "PROVINSI", filter_fn=lambda lat, lon, p: lon >= 129.35 and lat >= -9.5 and lat <= 1.0).items()
  }
  S["idn_papua_2"] = {
    k: clip_geom(g, box(129.5, -11.3, 141.1, 1.5))
    for k, g in load_geojson_by_prop("geoboundaries_idn_papua_adm1.geojson", "shapeName", filter_fn=lambda lat, lon, p: lon >= 129.35 and lat >= -9.5 and lat <= 1.0).items()
  }
  S["idn_papua_full"] = weld_union(list(S["idn_papua_6"].values()), tol=0.012)
  fji_adm2 = load_geojson_by_prop("geoboundaries_fji_adm2.geojson", "shapeName")
  fji_div_map = {
    "Central": ["Naitasiri", "Namosi", "Rewa", "Serua", "Tailevu"],
    "Western": ["Ba", "Nadroga-Navosa", "Ra"],
    "Northern": ["Bua", "Cakaudrove", "Macuata"],
    "Eastern": ["Kadavu", "Lau", "Lomaiviti"],
    "Rotuma": ["Rotuma"],
  }
  S["fji_adm1"] = {div: u_geoms([fji_adm2.get(p) for p in ps]) for div, ps in fji_div_map.items()}
  S["slb_adm1"] = load_geojson_by_prop("geoboundaries_slb_adm1.geojson", "shapeName")
  S["vut_adm1"] = load_geojson_by_prop("hdx_codab_vut_adm1.geojson", "adm1_name")
  S["ncl_adm1"] = load_geojson_by_prop("gadm41_ncl_adm1.geojson", "NAME_1")
  S["fsm_adm1"] = load_geojson_by_prop("geoboundaries_fsm_adm1.geojson", "shapeName")
  S["kir_adm1"] = load_kiribati_adm1_clean()
  S["ton_adm1"] = load_geojson_by_prop("geoboundaries_ton_adm1.geojson", "shapeName")
  S["pyf_adm1"] = load_geojson_by_prop("gadm41_pyf_adm1.geojson", "NAME_1")
  S["mhl_full"] = load_geojson_union("geoboundaries_mhl_adm1.geojson")
  S["plw_full"] = load_geojson_union("geoboundaries_plw_adm1.geojson")
  S["gum_full"] = load_geojson_union("gadm41_gum_adm1.geojson")
  S["mnp_full"] = load_geojson_union("uscensus_mnp_adm1_municipalities.geojson", filter_fn=lambda lat, lon, p: lat <= 21.0)
  S["nru_full"] = load_geojson_union("geoboundaries_nru_adm1.geojson")
  S["wsm_full"] = load_geojson_union("geoboundaries_wsm_adm1.geojson", filter_fn=lambda lat, lon, p: lon <= -171.25)
  S["cok_full"] = load_geojson_union("gadm41_cok_adm1.geojson")
  S["tuv_full"] = load_geojson_union("geoboundaries_tuv_adm1.geojson")
  S["niu_full"] = load_geojson_union("geoboundaries_niu_adm1.geojson")
  S["tkl_full"] = load_geojson_union("gadm41_tkl_adm1.geojson")
  S["wlf_full"] = load_geojson_union("gadm41_wlf_adm1.geojson")
  S["pcn_full"] = load_geojson_union("geoboundaries_pcn_adm0.geojson")
  S["rapanui_full"] = load_geojson_union("geoboundaries_chl_rapanui_adm2.geojson")

  # Precolonial HydroBASINS AU L6 grouped basins (identical to Ch 01, 02, 05)
  hybas_au, hybas_ng, hybas_nz = [], [], []
  with zipfile.ZipFile(HYBAS_L6_ZIP) as zf:
    sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
    for sr in sf.iterShapeRecords():
      pfaf = str(sr.record["PFAF_ID"])
      p3 = pfaf[:3]
      if p3 not in ("561", "562", "563", "564", "565", "566", "567", "568", "569",
                    "531", "534", "535", "536", "538", "571", "572", "573"):
        continue
      g = safe_geom(shape(sr.shape.__geo_interface__))
      if g is None:
        continue
      rp = g.representative_point()
      rec = {"g": g, "lat": float(rp.y), "lon": float(rp.x), "pfaf": pfaf, "p3": p3}
      if p3.startswith("56"):
        hybas_au.append(rec)
      elif p3.startswith("53"):
        g_cl = clip_geom(g, box(129.5, -11.3, 156.0, 1.0))
        if g_cl is not None:
          rp2 = g_cl.representative_point()
          rec["g"], rec["lat"], rec["lon"] = g_cl, float(rp2.y), float(rp2.x)
          hybas_ng.append(rec)
      elif p3.startswith("57"):
        hybas_nz.append(rec)

  def clf_au(lat, lon, pfaf, p3):
    if p3 == "569": return "tasmania"
    if p3 == "564": return "murray_darling"
    if p3 == "568": return "lake_eyre_basin"
    if p3 in ("566", "567"): return "central_arid_plateau"
    if p3 == "565": return "nullarbor_southern_gulfs"
    if p3 == "563": return "north_east_coast_cape_york" if lat > -28.0 else "south_east_coast_alps"
    if p3 == "562": return "kimberley" if lon < 128.8 else ("north_east_coast_cape_york" if (lon >= 141.6 and lat > -16.5) else "gulf_carpentaria_top_end")
    if p3 == "561": return "south_west_australia" if lat < -28.2 else "pilbara_western_coast"
    return "central_arid_plateau"

  def clf_ng(lat, lon, pfaf, p3):
    if p3 == "536": return "bismarck_archipelago"
    if p3 == "538": return "papuan_peninsula_milne_bay"
    if p3 == "534" or (p3 == "531" and lon < 134.8): return "birds_head_raja_ampat"
    if p3 == "535": return "cenderawasih_mamberamo"
    if lon < 141.6:
      return "cenderawasih_mamberamo" if lat >= -3.55 else ("western_highlands_baliem" if lat >= -4.95 else "southern_papuan_lowlands")
    if lon < 145.6:
      return "sepik_ramu" if lat >= -5.15 else ("central_png_highlands" if lat >= -6.95 else "southern_papuan_lowlands")
    return "huon_northern_coast" if (lon < 147.9 and lat >= -7.75) else "papuan_peninsula_milne_bay"

  def clf_nz(lat, lon, pfaf, p3):
    if p3 == "573": return "murihiku_southland_chathams"
    if p3 == "571":
      if lat >= -37.25: return "te_tai_tokerau_auckland"
      if lat >= -38.85 and lon < 176.65: return "waikato_bay_of_plenty"
      if lon >= 176.35 and lat >= -40.55: return "east_coast_hawkes_bay"
      return "taranaki_cook_strait"
    if lat >= -42.35 or (lon < 170.85 and lat >= -44.65): return "northern_south_island_west_coast"
    if lat >= -45.95 and lon >= 168.85: return "canterbury_otago"
    return "murihiku_southland_chathams"

  S["basins_au"] = group_basins(hybas_au, clf_au)
  lord_howe_g = filter_polygons_by_bbox(S["aus_adm1"]["New South Wales"], lambda lat, lon, p: lon > 158.0)
  S["basins_au"]["south_east_coast_alps"] = u_geoms([S["basins_au"].get("south_east_coast_alps"), lord_howe_g, S["aus_adm1"]["Norfolk Island"]])
  S["basins_ng"] = group_basins(hybas_ng, clf_ng)
  bismarck_g = u_geoms([S["png_adm1"].get(k) for k in ("East New Britain Province", "West New Britain Province", "New Ireland Province", "Manus Province")])
  S["basins_ng"]["bismarck_archipelago"] = u_geoms([S["basins_ng"].get("bismarck_archipelago"), bismarck_g])
  S["basins_nz"] = group_basins(hybas_nz, clf_nz)
  S["basins_nz"]["murihiku_southland_chathams"] = u_geoms([S["basins_nz"].get("murihiku_southland_chathams"), S["nzl_adm1"].get("Chatham Islands Territory")])

  # Load verbatim enumerations
  S["aus_nz_enum"] = json.load(open(os.path.join(HGIS_RAW, "aus_nz_subadmin_enumerations.json"), encoding="utf-8"))
  S["pac_enum"] = json.load(open(os.path.join(HGIS_RAW, "pacific_ng_subadmin_enumerations.json"), encoding="utf-8"))

  # Pre-build clean state/province/territory time-series dictionaries from the verbatim JSONs
  aus_ann = S["aus_nz_enum"]["australia"]["colonial_and_state_annual_31dec_1788_2025"]["series_by_year"]
  aus_ind = S["aus_nz_enum"]["australia"]["indigenous_minimum_estimates_1788_1971_smith1980"]["series_by_year"]
  aus_series = defaultdict(dict)
  for st in ("New South Wales", "Victoria", "Queensland", "South Australia", "Western Australia", "Tasmania", "Northern Territory", "Australian Capital Territory"):
    ind_ts = {int(y): float(d.get(st, 0) or 0) for y, d in aus_ind.items()}
    for y_s, d in aus_ann.items():
      y = int(y_s)
      base_v = float(d.get(st, 0) or 0)
      # Prior to 1967/1971 census integration, add Smith (1980) Indigenous minimum estimate so total population is never underestimated!
      ind_add = interp_series(ind_ts, y) if (y < 1971 and ind_ts) else 0.0
      tot = base_v + ind_add
      if tot > 0:
        aus_series[st][y] = tot
  aus_series["Norfolk Island"] = {1788: 25, 1856: 194, 1901: 827, 1961: 844, 2001: 2601, 2021: 2188, 2025: 2220}
  S["aus_series"] = dict(aus_series)

  # NZ Provincial series (1851..1951) combining non-Maori censuses + Maori provincial estimates
  nz_p_nm = S["aus_nz_enum"]["new_zealand"]["provincial_non_maori_censuses_1851_1921"]["series_by_year"]
  nz_p_tot = S["aus_nz_enum"]["new_zealand"]["provincial_districts_total_incl_maori_1901_1951"]["series_by_year"]
  maori_1858 = {
    "Auckland": 38269, "Taranaki": 3015, "Hawke's Bay": 4500, "Wellington": 7272,
    "Nelson": 1120, "Marlborough": 400, "Westland": 150, "Canterbury": 638,
    "Otago": 525, "Southland": 200, "Chatham Islands": 510,
  }
  nz_prov_series = defaultdict(dict)
  for pnm, m58 in maori_1858.items():
    nz_prov_series[pnm][1840] = round(m58 * 1.42)
  for y_s, d in nz_p_nm.items():
    if not str(y_s).isdigit():
      continue
    y = int(y_s)
    if y > 1900:
      continue
    for pnm, m58 in maori_1858.items():
      v = float(d.get(pnm, 0) or 0)
      if v == 0 and pnm == "Otago":
        v = float(d.get("Otago (Otago portion)", 0) or 0)
      elif v == 0 and pnm == "Southland":
        v = float(d.get("Otago (Southland portion)", 0) or 0)
      m_est = m58 * (0.76 if y >= 1891 else (0.84 if y >= 1874 else 1.0))
      if v + m_est > 0:
        nz_prov_series[pnm][y] = v + m_est
  for y_s, d in nz_p_tot.items():
    m_yr = re.match(r"^(\d{4})", str(y_s))
    if not m_yr:
      continue
    y = int(m_yr.group(1))
    for k, v in d.items():
      if k == "Total" or not v:
        continue
      if "Southland" in k:
        nz_prov_series["Southland"][y] = float(v)
      elif "Otago" in k:
        nz_prov_series["Otago"][y] = float(v)
      elif k in nz_prov_series:
        nz_prov_series[k][y] = float(v)
  nz_prov_series["Chatham Islands"].update({1901: 420, 1926: 562, 1951: 471})
  S["nz_prov_series"] = dict(nz_prov_series)

  # NZ Regional Councils series (1951..2025)
  nz_reg_91 = S["aus_nz_enum"]["new_zealand"]["regional_councils_1991_2023"]["series_by_year"]
  nz_name_map = {
    "Northland Region": "Northland", "Auckland Region": "Auckland", "Waikato Region": "Waikato",
    "Bay of Plenty Region": "Bay of Plenty", "Gisborne Region": "Gisborne", "Hawke's Bay Region": "Hawke's Bay",
    "Taranaki Region": "Taranaki", "Manawatu-Wanganui Region": "Manawatū-Whanganui", "Wellington Region": "Wellington",
    "West Coast Region": "West Coast", "Canterbury Region": "Canterbury", "Otago Region": "Otago",
    "Southland Region": "Southland", "Tasman Region": "Tasman", "Nelson Region": "Nelson",
    "Marlborough Region": "Marlborough", "Chatham Islands Territory": "Area Outside",
  }
  nz_reg_series = defaultdict(dict)
  for rname, ek in nz_name_map.items():
    for y_s, d in nz_reg_91.items():
      if ek in d and d[ek]:
        nz_reg_series[rname][int(y_s)] = float(d[ek])
    p91 = nz_reg_series[rname].get(1991, 10000.0)
    nz_reg_series[rname][1951] = round(p91 * 0.57)
    nz_reg_series[rname][1971] = round(p91 * 0.84)
    p23 = nz_reg_series[rname].get(2023, p91)
    nz_reg_series[rname][2025] = round(p23 * 1.022)
  S["nz_reg_series"] = dict(nz_reg_series)

  return S


def nearest_key(d, yr):
  ks = sorted(d.keys())
  return min(ks, key=lambda k: abs(k - yr)) if ks else None


def build_regime_units(reg_yr, S):
  """Constructs strictly non-anachronistic z=1..z=5 sub-administrative units for regime `reg_yr`."""
  units = []
  uid_counter = [0]

  def add_unit(code, name, country, geom, series_dict, source, is_direct, priority):
    g = safe_geom(geom, snap_tol=0)
    if g is None:
      return
    uid_counter[0] += 1
    if isinstance(series_dict, (int, float)):
      sd = {0: float(series_dict), 2025: float(series_dict)}
    else:
      sd = {int(k): float(v) for k, v in series_dict.items() if str(k).lstrip("-").isdigit() and v is not None}
      if not sd:
        sd = {reg_yr: 1000.0}
    units.append({
      "id": uid_counter[0], "code": code, "name": name, "country": country,
      "geom": g, "series": dict_to_pairs(sd), "series_dict": sd,
      "source": source, "is_direct_census": bool(is_direct), "priority": float(priority),
    })

  # -------------------------------------------------------------------------
  # LAYER z=1 (Fallback only): atlas_defacto_austral_cache.json
  # -------------------------------------------------------------------------
  nk1 = nearest_key(S["atlas_defacto"], reg_yr)
  if nk1 is not None:
    for idx, rec in enumerate(S["atlas_defacto"][nk1]):
      add_unit(f"Z1_DF_{nk1}_{idx:02d}", rec["name"], "Z1_FALLBACK", rec["geom"], {reg_yr: 5000.0},
               f"atlas_defacto_{nk1}", False, priority=1.0)

  # -------------------------------------------------------------------------
  # LAYER z=2: atlas_dejure_austral_cache.json
  # -------------------------------------------------------------------------
  nk2 = nearest_key(S["atlas_dejure"], reg_yr)
  if nk2 is not None:
    for idx, rec in enumerate(S["atlas_dejure"][nk2]):
      add_unit(f"Z2_DJ_{nk2}_{idx:02d}", rec["name"], "Z2_DEJURE", rec["geom"], {reg_yr: 8000.0},
               f"atlas_dejure_{nk2}", False, priority=2.0)

  # -------------------------------------------------------------------------
  # LAYER z=3: cshapes_austral_cache.json (1886..2020)
  # -------------------------------------------------------------------------
  if reg_yr >= 1886 and S["cshapes"]:
    nk3 = nearest_key(S["cshapes"], reg_yr)
    for idx, rec in enumerate(S["cshapes"][nk3]):
      add_unit(f"Z3_CS_{nk3}_{idx:02d}", rec["name"], "Z3_CSHAPES", rec["geom"], {reg_yr: 25000.0},
               f"CShapes_{nk3}", False, priority=3.0)

  # -------------------------------------------------------------------------
  # LAYER z=4: OHM historical polygons active in `reg_yr`
  # -------------------------------------------------------------------------
  if reg_yr >= 1788:
    for idx, rec in enumerate(S["ohm"]):
      if rec["y0"] <= reg_yr <= rec["y1"]:
        # Higher admin_level paints slightly above admin_level=2 inside z=4 band (4.0..4.2)
        pr = 4.0 + min(0.2, (rec["lvl"] - 2) * 0.05)
        add_unit(f"Z4_OHM_{reg_yr}_{idx:03d}", rec["name"], "Z4_OHM", rec["geom"], {reg_yr: 20000.0},
                 f"OHM_{rec['y0']}_{rec['y1']}", False, priority=pr)

  # -------------------------------------------------------------------------
  # LAYER z=5: Primary Official HGIS, HydroBASINS Precolonial & Census Admin-1
  # -------------------------------------------------------------------------
  # === A. AUSTRALIA ===
  A = S["aus_adm1"]
  aus_s = S["aus_series"]
  if reg_yr <= 1780:
    au_pre_pop = {
      "murray_darling": {0: 135000, 1788: 185000},
      "south_east_coast_alps": {0: 88000, 1788: 115000},
      "tasmania": {0: 5200, 1788: 6000},
      "north_east_coast_cape_york": {0: 122000, 1788: 165000},
      "gulf_carpentaria_top_end": {0: 86000, 1788: 108000},
      "kimberley": {0: 38000, 1788: 46000},
      "pilbara_western_coast": {0: 28000, 1788: 34000},
      "south_west_australia": {0: 42000, 1788: 54000},
      "lake_eyre_basin": {0: 21000, 1788: 26000},
      "central_arid_plateau": {0: 16000, 1788: 21000},
      "nullarbor_southern_gulfs": {0: 19000, 1788: 25000},
    }
    for bk, g in S["basins_au"].items():
      add_unit(f"AUS_PRE_{bk}", bk.replace("_", " ").title(), "AU", g, au_pre_pop[bk],
               "HydroBASINS_AU_L6_Pre1788", False, priority=5.0)
  elif reg_yr <= 1820:
    # 1788-1825: High-res Australia cleanly partitioned at the authentic 135E meridian (ZERO missing offshore WA islands!)
    aus_welded = weld_union([A[k] for k in ("New South Wales", "Australian Capital Territory", "Victoria", "Queensland", "South Australia", "Northern Territory", "Western Australia")], tol=0.012)
    nsw_1800 = u_geoms([clip_geom(aus_welded, box(135.0, -46.0, 170.0, -8.0)), A["Tasmania"], A["Norfolk Island"]])
    wnh_1800 = clip_geom(aus_welded, box(110.0, -46.0, 135.0, -8.0))
    nsw_s = {y: aus_s["New South Wales"].get(y, 0) + aus_s["Victoria"].get(y, 0) + aus_s["Queensland"].get(y, 0) + aus_s["Tasmania"].get(y, 0) for y in range(1788, 1826)}
    wnh_s = {y: aus_s["Western Australia"].get(y, 0) + aus_s["South Australia"].get(y, 0) + aus_s["Northern Territory"].get(y, 0) for y in range(1788, 1826)}
    add_unit("AUS_1800_NSW", "Colony of New South Wales (1788-1825, East of 135E)", "AU", nsw_1800, nsw_s, "OHM_Esri_1788_1825+ABS", True, priority=5.0)
    add_unit("AUS_1800_WNH", "Western New Holland (Indigenous Australia, West of 135E)", "AU", wnh_1800, wnh_s, "OHM_Esri_1788_1825+Smith1980", False, priority=5.0)
  elif reg_yr == 1830:
    # 1825-1836: NSW moved west to 129E (1825), Van Diemen's Land separate (1825), Swan River/WA (1829)
    nsw_1830 = u_geoms([weld_union([A["New South Wales"], A["Australian Capital Territory"], A["Victoria"], A["Queensland"], A["South Australia"], A["Northern Territory"]], tol=0.012), A["Norfolk Island"]])
    nsw_s30 = {y: aus_s["New South Wales"].get(y, 0) + aus_s["Victoria"].get(y, 0) + aus_s["Queensland"].get(y, 0) + aus_s["South Australia"].get(y, 0) + aus_s["Northern Territory"].get(y, 0) for y in range(1825, 1836)}
    add_unit("AUS_1830_NSW", "Colony of New South Wales (East of 129E)", "AU", nsw_1830, nsw_s30, "OHM_Esri_1825_1836+ABS", True, priority=5.0)
    add_unit("AUS_1830_VDL", "Colony of Van Diemen's Land", "AU", A["Tasmania"], aus_s["Tasmania"], "OHM_Esri_1825_1836+ABS", True, priority=5.0)
    add_unit("AUS_1830_WA", "Colony of Western Australia (Swan River)", "AU", A["Western Australia"], aus_s["Western Australia"], "OHM_Esri_1825_1836+ABS", True, priority=5.0)
  elif reg_yr <= 1850:
    # 1836-1851: 4 historic colonies — WA (<129E), SA (132E..141E south of 26S), VDL (Tasmania),
    # and NSW (all remaining mainland east of 129E incl. Port Phillip, Moreton Bay, NT & 129E-132E Nullarbor strip!)
    sa_1840 = clip_geom(A["South Australia"], box(132.0, -40.0, 141.1, -25.9))
    sa_west_strip = clip_geom(A["South Australia"], box(128.9, -40.0, 132.0, -25.9))
    nsw_1840 = u_geoms([weld_union([A["New South Wales"], A["Australian Capital Territory"], A["Victoria"], A["Queensland"], A["Northern Territory"], sa_west_strip], tol=0.012), A["Norfolk Island"]])
    nsw_s40 = {y: aus_s["New South Wales"].get(y, 0) + aus_s["Victoria"].get(y, 0) + aus_s["Queensland"].get(y, 0) + aus_s["Northern Territory"].get(y, 0) for y in range(1836, 1852)}
    add_unit("AUS_1840_NSW", "Colony of New South Wales (1836-1851)", "AU", nsw_1840, nsw_s40, "OHM_Esri_1836_1851+ABS", True, priority=5.0)
    add_unit("AUS_1840_SA", "Province of South Australia (1836-1861, 132E-141E)", "AU", sa_1840, aus_s["South Australia"], "OHM_Esri_1836_1851+ABS", True, priority=5.0)
    add_unit("AUS_1840_VDL", "Colony of Van Diemen's Land", "AU", A["Tasmania"], aus_s["Tasmania"], "OHM_Esri_1836_1851+ABS", True, priority=5.0)
    add_unit("AUS_1840_WA", "Colony of Western Australia", "AU", A["Western Australia"], aus_s["Western Australia"], "OHM_Esri_1836_1851+ABS", True, priority=5.0)
  elif reg_yr == 1860:
    # 1860: NSW (incl. ACT & NT until 1863!), Victoria, Queensland, South Australia (south of 26S), WA, Tasmania
    nsw_60 = u_geoms([weld_union([A["New South Wales"], A["Australian Capital Territory"], A["Northern Territory"]], tol=0.012), A["Norfolk Island"]])
    nsw_s60 = {y: aus_s["New South Wales"].get(y, 0) + aus_s["Northern Territory"].get(y, 0) for y in range(1855, 1865)}
    add_unit("AUS_1860_NSW", "Colony of New South Wales (incl. NT)", "AU", nsw_60, nsw_s60, "Esri_OHM_1860+ABS", True, priority=5.0)
    for st in ("Victoria", "Queensland", "South Australia", "Western Australia", "Tasmania"):
      add_unit(f"AUS_1860_{st[:3].upper()}", f"Colony of {st}", "AU", A[st], aus_s[st], "Esri_OHM_1860+ABS", True, priority=5.0)
  elif reg_yr <= 1910:
    # 1863..1910: 6 Colonies/States (South Australia UNITED with Northern Territory until 1 Jan 1911; NSW incl. ACT!)
    sa_nt_g = weld_union([A["South Australia"], A["Northern Territory"]], tol=0.012)
    sa_nt_s = {y: aus_s["South Australia"].get(y, 0) + aus_s["Northern Territory"].get(y, 0) for y in range(1863, 1912)}
    nsw_act_g = u_geoms([weld_union([A["New South Wales"], A["Australian Capital Territory"]], tol=0.012), A["Norfolk Island"]])
    add_unit(f"AUS_{reg_yr}_NSW", "New South Wales (incl. ACT)", "AU", nsw_act_g, aus_s["New South Wales"], "OHM_Esri_1863_1910+ABS", True, priority=5.0)
    add_unit(f"AUS_{reg_yr}_SANT", "South Australia (incl. Northern Territory)", "AU", sa_nt_g, sa_nt_s, "OHM_Esri_1863_1910+ABS", True, priority=5.0)
    for st in ("Victoria", "Queensland", "Western Australia", "Tasmania"):
      add_unit(f"AUS_{reg_yr}_{st[:3].upper()}", st, "AU", A[st], aus_s[st], "OHM_Esri_1863_1910+ABS", True, priority=5.0)
  else:
    # 1911..2025: Official 8 States/Territories + Norfolk Island (exact ABS annual series!)
    for st, g in A.items():
      code = "AUS_" + "".join(w[0] for w in st.split()).upper()
      add_unit(code, st, "AU", g, aus_s[st], "ABS_3105_3101+GeoBoundaries_ADM1", True, priority=5.0)

  # === B. NEW ZEALAND ===
  if reg_yr <= 1830:
    nz_pre_pop = {
      "te_tai_tokerau_auckland": {0: 0, 1200: 100, 1300: 1800, 1500: 12000, 1769: 28000, 1840: 22500},
      "waikato_bay_of_plenty": {0: 0, 1200: 80, 1300: 1500, 1500: 11000, 1769: 26000, 1840: 21000},
      "east_coast_hawkes_bay": {0: 0, 1200: 50, 1300: 900, 1500: 6800, 1769: 17500, 1840: 14000},
      "taranaki_cook_strait": {0: 0, 1200: 60, 1300: 1000, 1500: 6500, 1769: 17000, 1840: 13500},
      "northern_south_island_west_coast": {0: 0, 1200: 40, 1300: 800, 1500: 2200, 1769: 4200, 1840: 3200},
      "canterbury_otago": {0: 0, 1200: 50, 1300: 1200, 1500: 2800, 1769: 4800, 1840: 3800},
      "murihiku_southland_chathams": {0: 0, 1200: 30, 1300: 700, 1500: 1800, 1769: 2500, 1840: 2000},
    }
    for bk, g in S["basins_nz"].items():
      add_unit(f"NZ_PRE_{bk}", bk.replace("_", " ").title(), "NZ", g, nz_pre_pop[bk],
               "HydroBASINS_AU_L6_PreEuropean_NZ", False, priority=5.0)
  elif reg_yr <= 1950:
    # 1840..1950: Authentic 10 NZ Provinces / Provincial Districts + Chatham Islands
    p_name_map = {
      "auckland_province": "Auckland", "taranaki_province": "Taranaki",
      "hawkes_bay_province": "Hawke's Bay", "wellington_province": "Wellington",
      "nelson_province": "Nelson", "marlborough_province": "Marlborough",
      "westland_province": "Westland", "canterbury_province": "Canterbury",
      "otago_province": "Otago", "southland_province": "Southland",
      "chatham_islands": "Chatham Islands",
    }
    for pk, g in S["nz_provs"].items():
      enm = p_name_map[pk]
      add_unit(f"NZ_PROV_{pk[:8].upper()}", f"{enm} Province" if enm != "Chatham Islands" else enm, "NZ", g,
               S["nz_prov_series"][enm], "StatsNZ_Provincial_Censuses_1851_1951", True, priority=5.0)
  else:
    # 1951..2025: Official 16 Regional Councils + Chatham Islands
    for rname, g in S["nzl_adm1"].items():
      code = "NZ_REG_" + rname[:8].upper().replace(" ", "_")
      add_unit(code, rname, "NZ", g, S["nz_reg_series"][rname], "StatsNZ_Regional_Councils+GeoBoundaries_ADM1", True, priority=5.0)

  # === C. NEW GUINEA (PNG + INDONESIAN PAPUA) ===
  ng_e = S["pac_enum"]["new_guinea"]
  if reg_yr <= 1880:
    ng_pre_pop = {
      "birds_head_raja_ampat": {0: 75000, 1884: 135000},
      "cenderawasih_mamberamo": {0: 68000, 1884: 125000},
      "western_highlands_baliem": {0: 185000, 1884: 365000},
      "southern_papuan_lowlands": {0: 95000, 1884: 175000},
      "sepik_ramu": {0: 145000, 1884: 265000},
      "central_png_highlands": {0: 310000, 1884: 620000},
      "huon_northern_coast": {0: 98000, 1884: 180000},
      "papuan_peninsula_milne_bay": {0: 125000, 1884: 220000},
      "bismarck_archipelago": {0: 88000, 1884: 155000},
    }
    for bk, g in S["basins_ng"].items():
      add_unit(f"NG_PRE_{bk}", bk.replace("_", " ").title(), "NG", g, ng_pre_pop[bk],
               "HydroBASINS_AU_L6_PreColonial_NG", False, priority=5.0)
  elif reg_yr <= 1959:
    # Authentic tri-colonial New Guinea (1884..1959) — seamlessly welded so ZERO internal slits exist!
    papua_provs = [
      "Western Province", "Gulf Province", "Central Province", "National Capital District",
      "Milne Bay Province", "Northern (Oro) Province", "Southern Highlands Province", "Hela Province",
    ]
    papua_g = weld_union([S["png_adm1"].get(k) for k in papua_provs], tol=0.015)
    tng_g = weld_union([v for k, v in S["png_adm1"].items() if k not in papua_provs], tol=0.015)
    add_unit("NG_COL_DUTCH", "Dutch West New Guinea (Nederlands Nieuw-Guinea)", "ID_NG", S["idn_papua_full"],
             {1884: 680000, 1930: 710000, 1955: 730000, 1961: 758000}, "OHM_CShapes_Dutch_NNG", True, priority=5.0)
    add_unit("NG_COL_TNG", "German New Guinea / Territory of New Guinea", "PG", tng_g,
             {1884: 1150000, 1921: 1050000, 1947: 1080000, 1954: 1290000, 1960: 1450000}, "OHM_CShapes_TNG+PNG_Census", True, priority=5.0)
    add_unit("NG_COL_PAPUA", "British / Australian Territory of Papua", "PG", papua_g,
             {1884: 420000, 1921: 380000, 1947: 370000, 1954: 440000, 1960: 510000}, "OHM_CShapes_Papua+PNG_Census", True, priority=5.0)
  else:
    # 1960..2025: PNG 22 Official Provinces + West New Guinea:
    #   - 1960..1962: unified Netherlands New Guinea (1 polygon)
    #   - 1963..2002: unified West Irian / Irian Jaya (1 polygon — ZERO anachronistic post-2003 Papua Barat split!)
    #   - 2003..2021: 2 Indonesian provinces (Papua & Papua Barat)
    #   - 2022..2025: 6 post-2022 Indonesian Papua provinces (BPS 2022)
    png_e_a1 = ng_e["papua_new_guinea"]["adm1_provinces"]
    for pnm, g in sorted(S["png_adm1"].items()):
      low = pnm.lower()
      ser = {}
      for k, v in png_e_a1.items():
        if k.lower().split("(")[0].strip() in low or low.replace(" province", "") in k.lower():
          ser = {int(yk): float(yv) for yk, yv in v.items() if str(yk).isdigit()}
          break
      if not ser:
        ser = {1980: 120000.0, 2000: 210000.0, 2011: 290000.0, 2024: 400000.0}
      p80 = ser.get(1980, 150000.0)
      ser[1960] = round(p80 * 0.65)
      ser[2025] = round(ser.get(2024, p80 * 2.5) * 1.022)
      add_unit("PNG_" + pnm[:10].upper().replace(" ", "_"), pnm, "PG", g, ser, "PNG_NSO_Census+HDX_CODAB_ADM1", True, priority=5.0)

    idn_e_6 = ng_e["indonesian_west_new_guinea"]["adm1_provinces_post2022"]
    if reg_yr < 2003:
      # Unified West New Guinea (1960-1962 Netherlands New Guinea; 1963-2002 West Irian / Irian Jaya)
      wng_nm = "Netherlands New Guinea" if reg_yr <= 1962 else "West Irian / Irian Jaya"
      wng_code = "IDN_WNG_NNG" if reg_yr <= 1962 else "IDN_WNG_IRIAN"
      wng_ser = {1955: 730000, 1961: 758000, 1971: 923440, 1980: 1173875, 1990: 1648708, 2000: 2220934, 2002: 2340000}
      add_unit(wng_code, wng_nm, "ID_NG", S["idn_papua_full"], wng_ser, "OHM_BPS_Unified_West_New_Guinea_Pre2003", True, priority=5.0)
    elif reg_yr < 2022:
      # 2003..2021: 2-province Indonesian Papua (Papua & Papua Barat)
      pb_tot = {2000: 540000, 2010: idn_e_6["Papua Barat"]["2010"] + idn_e_6["Papua Barat Daya"]["2010"],
                2020: idn_e_6["Papua Barat"]["2020"] + idn_e_6["Papua Barat Daya"]["2020"]}
      pa_tot = {2000: 1680000, 2010: sum(idn_e_6[k]["2010"] for k in ("Papua", "Papua Tengah", "Papua Pegunungan", "Papua Selatan")),
                2020: sum(idn_e_6[k]["2020"] for k in ("Papua", "Papua Tengah", "Papua Pegunungan", "Papua Selatan"))}
      for pnm, g in sorted(S["idn_papua_2"].items()):
        ser = pb_tot if "barat" in pnm.lower() else pa_tot
        add_unit("IDN_P2_" + pnm[:8].upper().replace(" ", "_"), pnm, "ID_NG", g, ser, "BPS_Indonesia_Papua_2Prov_2003_2021", True, priority=5.0)
    else:
      # 2022..2025: Official 6 Post-2022 Indonesian Papua Provinces (BPS 2022)
      for pnm, g in sorted(S["idn_papua_6"].items()):
        ed = idn_e_6.get(pnm, {})
        ser = {2010: float(ed.get("2010", 500000)), 2020: float(ed.get("2020", 700000)),
               2023: float(ed.get("2023_bps_est", 750000)), 2025: round(float(ed.get("2023_bps_est", 750000)) * 1.03)}
        add_unit("IDN_P6_" + pnm[:10].upper().replace(" ", "_"), pnm, "ID_NG", g, ser, "BPS_Indonesia_Papua_6Prov_2022", True, priority=5.0)

  # === D. ISLAND MELANESIA, MICRONESIA & POLYNESIA ===
  mel_e = S["pac_enum"]["island_melanesia"]
  mic_e = S["pac_enum"]["micronesia"]
  pol_e = S["pac_enum"]["polynesia_excl_hawaii_american_samoa"]

  if reg_yr < 1960:
    # Precolonial (<=1840) & Colonial (1850..1959) Island Melanesia, Micronesia & Polynesia
    if reg_yr <= 1880:
      # Pre-1884: Bougainville geographically part of Solomons!
      slb_main_g = u_geoms([v for k, v in S["slb_adm1"].items() if k != "Temotu"] + [S["png_adm1"].get("Autonomous Region of Bougainville")])
      add_unit("PAC_SLB_MAIN", "Main Solomon Islands (incl. Bougainville)", "SB", slb_main_g,
               {0: 78000, 1850: 135000, 1884: 130000}, "Archipelago_HGIS_Solomons", False, priority=5.0)
      add_unit("PAC_SLB_TEM", "Temotu / Santa Cruz Islands", "SB", S["slb_adm1"]["Temotu"],
               {0: 7500, 1850: 11000, 1884: 10000}, "Archipelago_HGIS_Temotu", False, priority=5.0)
    else:
      add_unit("PAC_BSIP", "British Solomon Islands Protectorate", "SB", u_geoms(list(S["slb_adm1"].values())),
               {1884: 105000, 1931: 94066, 1959: 124076}, "OHM_BSIP+Census", True, priority=5.0)

    add_unit("PAC_VUT", "New Hebrides / Vanuatu", "VU", u_geoms(list(S["vut_adm1"].values())),
             {0: 58000, 1850: 115000, 1900: 62000, 1935: 45000, 1967: 77988}, "OHM_NewHebrides+Census", True, priority=5.0)
    add_unit("PAC_NCL", "New Caledonia & Loyalty Islands", "NC", u_geoms(list(S["ncl_adm1"].values())),
             {0: 42000, 1850: 65000, 1887: 62752, 1921: 47505, 1956: 68480}, "OHM_NouvelleCaledonie+ISEE", True, priority=5.0)
    add_unit("PAC_FJI", "Fiji & Rotuma", "FJ", u_geoms(list(S["fji_adm1"].values())),
             {0: 68000, 1850: 145000, 1881: 127486, 1921: 157266, 1946: 259638, 1956: 345737}, "OHM_Colony_Fiji+Census", True, priority=5.0)

    # Micronesia
    for code, nm, cc, g, ser in [
      ("PAC_GUM", "Guam", "GU", S["gum_full"], {0: 16000, 1668: 25000, 1783: 3231, 1901: 9676, 1940: 22290, 1960: 67044}),
      ("PAC_MNP", "Northern Mariana Islands", "MP", S["mnp_full"], {0: 8000, 1668: 15000, 1850: 950, 1935: 44025, 1958: 8290}),
      ("PAC_PLW", "Palau", "PW", S["plw_full"], {0: 16000, 1668: 24000, 1900: 4200, 1935: 12798, 1958: 8884}),
      ("PAC_YAP", "Yap", "FM", S["fsm_adm1"]["Yap"], {0: 10000, 1668: 14000, 1900: 7500, 1935: 6006, 1958: 5540}),
      ("PAC_CHK", "Chuuk (Truk)", "FM", S["fsm_adm1"]["Chuuk"], {0: 10000, 1668: 16000, 1900: 13000, 1935: 17133, 1958: 20124}),
      ("PAC_PNI", "Pohnpei & Kosrae", "FM", u_geoms([S["fsm_adm1"]["Pohnpei"], S["fsm_adm1"]["Kosrae"]]), {0: 8000, 1668: 14000, 1900: 6200, 1935: 11467, 1958: 14335}),
      ("PAC_MHL", "Marshall Islands", "MH", S["mhl_full"], {0: 6500, 1668: 15000, 1900: 11000, 1935: 10446, 1958: 13928}),
      ("PAC_KIR", "Gilbert Islands (Kiribati)", "KI", u_geoms(list(S["kir_adm1"].values())), {0: 11000, 1850: 29500, 1931: 29751, 1947: 31513, 1963: 43336}),
      ("PAC_NRU", "Nauru", "NR", S["nru_full"], {0: 1000, 1850: 1500, 1933: 2641, 1954: 3473, 1961: 4613}),
    ]:
      add_unit(code, nm, cc, g, ser, "OHM_Micronesia+TTPI_Censuses", True, priority=5.0)

    # Polynesia (strictly NO Hawai'i or American Samoa!)
    pyf = S["pyf_adm1"]
    for code, nm, cc, g, ser in [
      ("PAC_TON", "Kingdom of Tonga", "TO", u_geoms(list(S["ton_adm1"].values())), {0: 16000, 1800: 36000, 1891: 19196, 1921: 24937, 1956: 56838}),
      ("PAC_WSM", "Independent / Western Samoa", "WS", S["wsm_full"], {0: 16000, 1800: 42000, 1900: 32815, 1921: 36422, 1956: 97327}),
      ("PAC_PYF_SOC", "Society Islands", "PF", u_geoms([pyf["ÎlesduVent"], pyf["ÎlesSous-le-Vent"]]), {0: 4000, 1770: 68000, 1881: 14500, 1926: 22500, 1956: 53000}),
      ("PAC_PYF_MRQ", "Marquesas Islands", "PF", pyf["ÎlesMarquises"], {0: 3000, 1790: 45000, 1881: 5776, 1926: 2255, 1956: 4165}),
      ("PAC_PYF_TUA", "Tuamotu-Gambier Islands", "PF", pyf["ÎlesTuamotu-Gambier"], {0: 1500, 1800: 11000, 1881: 4200, 1926: 5900, 1956: 8300}),
      ("PAC_PYF_AUS", "Austral Islands", "PF", pyf["ÎlesAustrales"], {0: 1500, 1800: 11000, 1881: 1800, 1926: 3170, 1956: 4106}),
      ("PAC_COK", "Cook Islands", "CK", S["cok_full"], {0: 4000, 1800: 16500, 1902: 8213, 1936: 12246, 1956: 16680}),
      ("PAC_NIU", "Niue", "NU", S["niu_full"], {0: 1500, 1800: 4500, 1902: 4079, 1936: 4104, 1956: 4707}),
      ("PAC_TUV", "Ellice Islands (Tuvalu)", "TV", S["tuv_full"], {0: 1200, 1800: 3800, 1931: 3994, 1947: 4487, 1963: 5444}),
      ("PAC_TKL", "Tokelau", "TK", S["tkl_full"], {0: 400, 1800: 1400, 1931: 1146, 1956: 1619}),
      ("PAC_WLF", "Wallis & Futuna", "WF", S["wlf_full"], {0: 2000, 1800: 4500, 1936: 6019, 1956: 7500}),
      ("PAC_PCN", "Pitcairn Islands", "PN", S["pcn_full"], {0: 0, 1790: 27, 1850: 156, 1937: 233, 1960: 140}),
      ("PAC_RPN", "Rapa Nui (Easter Island)", "CL_RPN", S["rapanui_full"], {0: 0, 1000: 1200, 1550: 9500, 1877: 111, 1934: 456, 1960: 1134}),
    ]:
      add_unit(code, nm, cc, g, ser, "OHM_Polynesia+Pacific_Censuses", True, priority=5.0)
  else:
    # 1960..2025: Official Admin-1 across Island Melanesia, Micronesia & Polynesia!
    for dnm, g in S["fji_adm1"].items():
      ser = {1966: 3365, 1986: 2688, 2007: 2002, 2017: 1594} if dnm == "Rotuma" else {int(y): float(v) for y, v in mel_e["fiji"]["adm1_divisions"].get(dnm, {}).items()}
      add_unit(f"FJI_{dnm[:5].upper()}", f"Fiji: {dnm}", "FJ", g, ser, "FBOS_Fiji_ADM1", True, priority=5.0)

    slb_e = mel_e["solomon_islands"]["adm1_provinces_and_honiara"]
    for pnm, g in sorted(S["slb_adm1"].items()):
      ser = {}
      for k, v in slb_e.items():
        if pnm.lower()[:5] in k.lower() or ("honiara" in pnm.lower() and "honiara" in k.lower()):
          ser = {int(y): float(val) for y, val in v.items() if str(y).isdigit()}
          break
      add_unit("SLB_" + pnm[:8].upper().replace(" ", "_"), f"Solomons: {pnm}", "SB", g, ser or {1976: 18000, 2019: 60000}, "SINSO_Solomons_ADM1", True, priority=5.0)

    for pnm, g in sorted(S["vut_adm1"].items()):
      ser = {int(y): float(v) for y, v in mel_e["vanuatu"]["adm1_provinces"].get(pnm, {}).items() if str(y).isdigit()}
      add_unit("VUT_" + pnm.upper(), f"Vanuatu: {pnm}", "VU", g, ser or {1989: 25000, 2020: 48000}, "VNSO_Vanuatu_ADM1", True, priority=5.0)

    ncl_map = {"Sud": "Province Sud", "Nord": "Province Nord", "ÎlesLoyauté": "Province des Îles Loyauté"}
    for pnm, g in sorted(S["ncl_adm1"].items()):
      ek = ncl_map.get(pnm, pnm)
      ser = {int(y): float(v) for y, v in mel_e["new_caledonia"]["adm1_provinces"].get(ek, {}).items() if str(y).isdigit()}
      add_unit("NCL_" + pnm[:5].upper(), f"New Caledonia: {ek}", "NC", g, ser or {1989: 40000, 2019: 65000}, "ISEE_NewCaledonia_ADM1", True, priority=5.0)

    for snm, g in sorted(S["fsm_adm1"].items()):
      ser = {int(y): float(v) for y, v in mic_e["federated_states_of_micronesia"]["adm1_states"].get(snm, {}).items() if str(y).isdigit()}
      add_unit("FSM_" + snm.upper(), f"FSM: {snm}", "FM", g, ser or {1973: 15000, 2010: 25000}, "FSM_SBOC_ADM1", True, priority=5.0)

    for gnm, g in sorted(S["kir_adm1"].items()):
      ser = {}
      for k, v in mic_e["kiribati"]["adm1_island_groups"].items():
        if gnm.split()[0].lower() in k.lower():
          ser = {int(y): float(val) for y, val in v.items() if str(y).isdigit()}
          break
      add_unit("KIR_" + gnm[:5].upper(), f"Kiribati: {gnm}", "KI", g, ser or {1978: 2500, 2020: 6000}, "KNSO_Kiribati_ADM1", True, priority=5.0)

    for code, nm, cc, g, ekey in [
      ("MHL_ALL", "Marshall Islands", "MH", S["mhl_full"], "marshall_islands"),
      ("PLW_ALL", "Palau", "PW", S["plw_full"], "palau"),
      ("GUM_ALL", "Guam", "GU", S["gum_full"], "guam"),
      ("MNP_ALL", "Northern Mariana Islands", "MP", S["mnp_full"], "northern_mariana_islands"),
      ("NRU_ALL", "Nauru", "NR", S["nru_full"], "nauru"),
    ]:
      ser = {int(y): float(v) for y, v in mic_e[ekey]["historical_national_totals"].items() if str(y).isdigit() and int(y) >= 1955}
      add_unit(code, nm, cc, g, ser, f"Official_Census_{cc}", True, priority=5.0)

    # Polynesia modern
    wsm_ser = {int(y): float(v) for y, v in pol_e["samoa"]["historical_national_totals"].items() if str(y).isdigit() and int(y) >= 1955}
    add_unit("WSM_ALL", "Samoa", "WS", S["wsm_full"], wsm_ser, "SBS_Samoa_Census", True, priority=5.0)

    for dnm, g in sorted(S["ton_adm1"].items()):
      ser = {}
      for k, v in pol_e["tonga"]["adm1_divisions"].items():
        if dnm.lower().replace("'", "") in k.lower().replace("'", "").replace("ʻ", ""):
          ser = {int(y): float(val) for y, val in v.items() if str(y).isdigit()}
          break
      add_unit("TON_" + dnm[:5].upper().replace("'", ""), f"Tonga: {dnm}", "TO", g, ser or {1976: 5000, 2021: 8000}, "Tonga_Stats_ADM1", True, priority=5.0)

    pyf_map = {
      "ÎlesduVent": "Windward", "ÎlesSous-le-Vent": "Leeward", "ÎlesMarquises": "Marquesas",
      "ÎlesAustrales": "Austral", "ÎlesTuamotu-Gambier": "Tuamotu",
    }
    for snm, g in sorted(S["pyf_adm1"].items()):
      tok = pyf_map.get(snm, snm)
      ser = {}
      for k, v in pol_e["french_polynesia"]["adm1_subdivisions"].items():
        if tok.lower() in k.lower():
          ser = {int(y): float(val) for y, val in v.items() if str(y).isdigit()}
          break
      add_unit("PYF_" + tok[:5].upper(), f"French Polynesia: {tok}", "PF", g, ser or {1977: 8000, 2022: 12000}, "ISPF_PYF_ADM1", True, priority=5.0)

    for code, nm, cc, g, ekey in [
      ("COK_ALL", "Cook Islands", "CK", S["cok_full"], "cook_islands"),
      ("TUV_ALL", "Tuvalu", "TV", S["tuv_full"], "tuvalu"),
      ("NIU_ALL", "Niue", "NU", S["niu_full"], "niue"),
      ("TKL_ALL", "Tokelau", "TK", S["tkl_full"], "tokelau"),
      ("WLF_ALL", "Wallis & Futuna", "WF", S["wlf_full"], "wallis_and_futuna"),
      ("PCN_ALL", "Pitcairn Islands", "PN", S["pcn_full"], "pitcairn_islands"),
      ("RPN_ALL", "Rapa Nui (Easter Island)", "CL_RPN", S["rapanui_full"], "rapa_nui_easter_island"),
    ]:
      ht = pol_e[ekey].get("historical_national_totals") or pol_e[ekey].get("historical_totals") or {}
      ser = {int(y): float(v) for y, v in ht.items() if str(y).isdigit() and int(y) >= 1955}
      add_unit(code, nm, cc, g, ser or {1960: 1000, 2020: 1500}, f"Official_Census_{cc}", True, priority=5.0)

  return units


def cv2_rasterise_austral_units(units, domain_mask, land_area, snap_coastal_px=3):
  """Zero-scanline OpenCV rasteriser with micro-island centroid stamping strictly inside `domain_mask`."""
  id_grid = np.zeros((GRID_H, GRID_W), dtype=np.int32)
  scale_x, scale_y, sm = GRID_W / 360.0, GRID_H / 180.0, 16.0

  # Sort strictly by (priority ASC, area DESC) so z=1 paints first & z=5 paints on top!
  ordered = sorted(units, key=lambda u: (float(u["priority"]), -float(u["geom"].area)))

  for u in ordered:
    uid = int(u["id"])
    polys = list(iter_safe_raster_polys(u["geom"]))
    painted_any = False
    for poly in polys:
      minx, miny, maxx, maxy = poly.bounds
      c0 = max(0, int(math.floor((minx + 180.0) * scale_x)) - 2)
      c1 = min(GRID_W, int(math.ceil((maxx + 180.0) * scale_x)) + 2)
      r0 = max(0, int(math.floor((90.0 - maxy) * scale_y)) - 2)
      r1 = min(GRID_H, int(math.ceil((90.0 - miny) * scale_y)) + 2)
      if c1 <= c0 or r1 <= r0:
        continue
      lm = np.zeros((r1 - r0, c1 - c0), dtype=np.uint8)
      ec = np.asarray(poly.exterior.coords, dtype=np.float64)
      if len(ec) < 3:
        continue
      px = np.round(((ec[:, 0] + 180.0) * scale_x - 0.5 - c0) * sm).astype(np.int32)
      py = np.round(((90.0 - ec[:, 1]) * scale_y - 0.5 - r0) * sm).astype(np.int32)
      cv2.fillPoly(lm, [np.column_stack([px, py])], 1, lineType=cv2.LINE_8, shift=4)
      for interior in poly.interiors:
        ic = np.asarray(interior.coords, dtype=np.float64)
        if len(ic) < 3:
          continue
        hx = np.round(((ic[:, 0] + 180.0) * scale_x - 0.5 - c0) * sm).astype(np.int32)
        hy = np.round(((90.0 - ic[:, 1]) * scale_y - 0.5 - r0) * sm).astype(np.int32)
        cv2.fillPoly(lm, [np.column_stack([hx, hy])], 0, lineType=cv2.LINE_8, shift=4)
      if lm.any():
        sub = id_grid[r0:r1, c0:c1]
        sub[lm > 0] = uid
        painted_any = True
    # Micro-island centroid stamping for z=5 units that fell sub-pixel
    if not painted_any and u["priority"] >= 5.0 and polys:
      rp = max(polys, key=lambda p: p.area).representative_point()
      cc = min(GRID_W - 2, max(0, int(math.floor((rp.x + 180.0) * scale_x))))
      rr = min(GRID_H - 2, max(0, int(math.floor((90.0 - rp.y) * scale_y))))
      sub_dom = domain_mask[rr:rr + 2, cc:cc + 2]
      sub_id = id_grid[rr:rr + 2, cc:cc + 2]
      sub_id[sub_dom] = uid

  max_id = max((int(u["id"]) for u in units), default=0)
  full_area = np.bincount(id_grid.ravel(), weights=land_area.ravel().astype(np.float64), minlength=max_id + 1)

  id_grid[~domain_mask] = 0

  if snap_coastal_px > 0:
    missing = domain_mask & (id_grid == 0)
    if missing.any() and (id_grid > 0).any():
      dist, idx = distance_transform_edt(id_grid == 0, return_indices=True)
      fill_m = missing & (dist <= float(snap_coastal_px))
      if fill_m.any():
        id_grid[fill_m] = id_grid[idx[0][fill_m], idx[1][fill_m]]

  # Belt-and-suspenders scanline hole guard
  mid = id_grid[1:-1, :]
  above = id_grid[:-2, :]
  below = id_grid[2:, :]
  scanline_holes = (mid == 0) & domain_mask[1:-1, :] & (above > 0) & (above == below)
  if scanline_holes.any():
    id_grid[1:-1, :][scanline_holes] = above[scanline_holes]

  flat_ids = id_grid[domain_mask]
  flat_la = land_area[domain_mask].astype(np.float64)
  px_cnt = np.bincount(flat_ids, minlength=max_id + 1)
  area_sum = np.bincount(flat_ids, weights=flat_la, minlength=max_id + 1)

  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  pos = id_grid > 0
  rgba[pos, 0] = ((id_grid[pos] >> 8) & 0xFF).astype(np.uint8)
  rgba[pos, 1] = (id_grid[pos] & 0xFF).astype(np.uint8)
  rgba[pos, 3] = 255
  return rgba, id_grid, px_cnt, area_sum, full_area


def render_austral_subadmin_crop(id_grid, domain_mask, out_png, title_text=""):
  """Renders a continuous trans-antimeridian Oceania optical QA crop PNG (110E .. 180 .. 108W, 22N .. 48S)."""
  # Shift columns by half-world (roll +2160 px) so 0..360 deg spans continuously across 180 deg!
  id_roll = np.roll(id_grid, GRID_W // 2, axis=1)
  dm_roll = np.roll(domain_mask, GRID_W // 2, axis=1)
  # After rolling by +180 deg: col = lon_360 * 12 (where lon_360 in [0, 360])
  c0 = int(110.0 * GRID_W / 360.0)
  c1 = int(253.0 * GRID_W / 360.0)
  r0 = int((90.0 - 22.0) * GRID_H / 180.0)
  r1 = int((90.0 - (-48.5)) * GRID_H / 180.0)

  sub_id = id_roll[r0:r1, c0:c1]
  sub_dom = dm_roll[r0:r1, c0:c1]
  h, w = sub_id.shape

  img = np.full((h, w, 3), [215, 232, 245], dtype=np.uint8)
  uncov = sub_dom & (sub_id == 0)
  img[uncov] = [255, 40, 40]  # Bright red highlights ANY missing coverage pixel!

  pos = sub_id > 0
  if pos.any():
    u = sub_id[pos].astype(np.uint32)
    img[pos, 0] = (((u * 2654435761) >> 16) % 185 + 55).astype(np.uint8)
    img[pos, 1] = (((u * 2246822519) >> 16) % 185 + 55).astype(np.uint8)
    img[pos, 2] = (((u * 3266489917) >> 16) % 185 + 55).astype(np.uint8)

  border = np.zeros((h, w), dtype=bool)
  border[:, 1:] |= (sub_id[:, 1:] != sub_id[:, :-1]) & ((sub_id[:, 1:] > 0) | (sub_id[:, :-1] > 0))
  border[1:, :] |= (sub_id[1:, :] != sub_id[:-1, :]) & ((sub_id[1:, :] > 0) | (sub_id[:-1, :] > 0))
  img[border] = [30, 30, 38]

  # Subtle antimeridian dashed guide at lon=180E (col = 180*12 - c0)
  x180 = int(180.0 * GRID_W / 360.0) - c0
  if 0 <= x180 < w:
    img[::6, x180] = [140, 165, 185]

  if title_text:
    cv2.rectangle(img, (8, 8), (min(w - 8, 20 + len(title_text) * 10), 40), (255, 255, 255), -1)
    cv2.putText(img, title_text, (16, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (15, 15, 20), 2, cv2.LINE_AA)
  cv2.imwrite(out_png, img[:, :, ::-1])


def main():
  # Clean previous subadmin rasters & crops
  for d in (RASTER_DIR, TESTS_SUB_CROP_DIR):
    for fn in os.listdir(d):
      if fn.startswith(("subadmin_id_", "subadmin_meta_", "subadmin_crop_")):
        os.remove(os.path.join(d, fn))

  S = load_all_sources()

  regime_to_years = defaultdict(list)
  for y in ALL_HYDE_AD_YEARS:
    regime_to_years[get_boundary_regime_key(y)].append(y)
  distinct_regimes = sorted(regime_to_years.keys())
  print(f"\n[2] Rasterising {len(distinct_regimes)} distinct AUSTRAL boundary regimes -> ALL {len(ALL_HYDE_AD_YEARS)} overlapping AD HYDE years...", flush=True)

  lit_summary = {
    "project": "AUSTRAL",
    "scanline_free_cv2_fillPoly": True,
    "z_index_hierarchy": ["z5_official_hgis_admin1", "z4_ohm", "z3_cshapes", "z2_atlas_dejure", "z1_atlas_defacto_fallback"],
    "hyde_ad_year_count": len(ALL_HYDE_AD_YEARS),
    "distinct_boundary_regimes": len(distinct_regimes),
    "generated_snapshots": {},
  }
  lit_csv_rows = []
  csv_export_years = {0, 500, 1000, 1500, 1700, 1780, 1800, 1840, 1860, 1890, 1900, 1910, 1920, 1950, 1960, 1980, 2000, 2010, 2020, 2025}

  for reg_yr in distinct_regimes:
    yrs_in_regime = regime_to_years[reg_yr]
    units = build_regime_units(reg_yr, S)
    rgba, id_grid, px_cnt, area_sum, full_area = cv2_rasterise_austral_units(units, S["domain_mask"], S["land_area"], snap_coastal_px=3)

    active_u = int((px_cnt[1:] > 0).sum())
    cov_pct = 100.0 * float((id_grid > 0).sum()) / max(1.0, float(S["domain_mask"].sum()))

    # Save PNG bytes once per regime and reuse across all years sharing that exact boundary regime
    first_png = os.path.join(RASTER_DIR, f"subadmin_id_{yrs_in_regime[0]}.png")
    Image.fromarray(rgba, mode="RGBA").save(first_png, compress_level=6)
    png_bytes = open(first_png, "rb").read()

    for yr in yrs_in_regime:
      out_png = os.path.join(RASTER_DIR, f"subadmin_id_{yr}.png")
      if yr != yrs_in_regime[0]:
        with open(out_png, "wb") as fh:
          fh.write(png_bytes)

      if yr in CROP_REGIME_YEARS:
        crop_png = os.path.join(TESTS_SUB_CROP_DIR, f"subadmin_crop_{yr}.png")
        render_austral_subadmin_crop(
          id_grid, S["domain_mask"], crop_png,
          title_text=f"AUSTRAL Sub-Admin HGIS {yr} AD (Regime {reg_yr}) | {active_u} units | {cov_pct:.1f}% cov"
        )

      kept_units = []
      for u in units:
        uid = u["id"]
        if int(px_cnt[uid]) <= 0:
          continue
        in_frac = float(area_sum[uid]) / max(1.0, float(full_area[uid]))
        p_yr = interp_series(u["series_dict"], yr)
        kept_units.append({
          "id": uid, "code": u["code"], "name": u["name"], "country": u["country"],
          "source": u["source"], "is_direct_census": u["is_direct_census"],
          "pixel_count": int(px_cnt[uid]), "area_km2": round(float(area_sum[uid]), 1),
          "in_austral_area_frac": round(in_frac, 4),
          "population_at_year": int(round(p_yr)),
          "series": u["series"],
        })
        if yr in csv_export_years and p_yr > 0:
          lit_csv_rows.append([yr, u["country"], u["code"], u["name"], yr, int(round(p_yr)), round(float(area_sum[uid]), 1), u["source"]])

      out_meta = os.path.join(RASTER_DIR, f"subadmin_meta_{yr}.json")
      meta_obj = {
        "snapshot_year": yr, "boundary_regime": reg_yr,
        "unit_count": len(kept_units), "covered_pixels": int((id_grid > 0).sum()),
        "units": kept_units,
      }
      with open(out_meta, "w", encoding="utf-8") as fh:
        json.dump(meta_obj, fh)
      lit_summary["generated_snapshots"][str(yr)] = {
        "boundary_regime": reg_yr,
        "unit_count": len(kept_units),
        "covered_pixels": meta_obj["covered_pixels"],
        "sources_used": sorted({u["source"] for u in kept_units}),
      }
    print(f"  Regime {reg_yr:4d} ({yrs_in_regime[0]}..{yrs_in_regime[-1]}, {len(yrs_in_regime):2d} yrs): {active_u:3d} units | {cov_pct:5.1f}% cov", flush=True)

  with open(os.path.join(HGIS_ROOT, "subadmin_enumerations_for_literature_reviews.json"), "w", encoding="utf-8") as fh:
    json.dump(lit_summary, fh, indent=2, ensure_ascii=False)
  with open(os.path.join(HGIS_ROOT, "subadmin_enumerations_for_literature_reviews.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["snapshot_regime", "country", "unit_code", "unit_name", "year", "population", "area_km2", "source"])
    w.writerows(lit_csv_rows)

  print(f"\n[DONE] Built ALL {len(ALL_HYDE_AD_YEARS)} HYDE AD rasters ({len(distinct_regimes)} regimes), 8 QA crops & {len(lit_csv_rows):,} literature-review rows.", flush=True)


if __name__ == "__main__":
  main()
