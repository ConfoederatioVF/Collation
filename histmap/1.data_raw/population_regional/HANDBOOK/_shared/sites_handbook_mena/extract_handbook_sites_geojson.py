"""Stage C Multi-Repository Archaeological & Historical Site Composite Extractor for Project HANDBOOK.

Discretises HANDBOOK (North Africa, Near East, Anatolia, Cyprus, Transcaucasia, Iran, Afghanistan
and Arabia) plus a 300 km cross-frontier conditioning belt (POLARIS Caucasus/Black Sea, SARAY
Turkmenistan/Uzbekistan/Tajikistan, INDUS Pakistan, JADE Xinjiang) into scale-adaptive HydroBASINS
Level 6 catchments (<= 25,000 km2).

Composites 12 primary scholarly & national/regional archaeological repositories across all 7 required
HANDBOOK jurisdictions (`turkey`, `iran`, `egypt`, `levant_iraq`, `arabia`, `maghreb`, `caucasus_afghanistan`)
with 0% Wikidata/OSM crowd reliance:
  1. Published Excavations Atlas (Harvard Dataverse / ArchAtlas KMZ, 26,766 HANDBOOK sites)
  2. Pleiades Ancient World Gazetteer (30,185 HANDBOOK + belt sites)
  3. Al-Thurayya Early Islamic World Gazetteer (Cornu / Romanov, 2,501 settlements)
  4. EES Delta Survey (Egypt Exploration Society official ArcGIS register, 785 sites)
  5. C-Turkey (Altinisik et al., Anatolia & Thrace chronometric register)
  6. NERD (Near East Radiocarbon Dates, Palmisano et al. 2022)
  7. DARE (Digital Atlas of the Roman Empire, 809 MENA/Anatolia/North Africa sites)
  8. EAMENA & Regional Field Surveys (Western Nafud Saudi Arabia, Khorasan Iran, Wadi Naqqat Egypt, Gaza, PKAP Cyprus, CA2)
  9. UCL CAAL (Northern Afghanistan / Khorasan / Caspian regional monuments)
  10. Canonical Excavated MENA/Iran/Afghanistan/Caucasus/Maghreb/Arabia Monograph Type-Site & Capital Catalogue
  11. Global Radiocarbon Baseline (`c14_cleaned_dedup.csv`, 2,297 HANDBOOK sites)
  12. Cross-Frontier Conditioning Belts (`is_frontier_buffer: true`) from completed Viscount siblings:
      POLARIS (`sites_IA_RAS`), SARAY (`sites_saray_central_asia`), INDUS (`sites_indus_south_asia`), JADE (`sites_east_asia`).
"""

import csv
import io
import json
import math
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter

import numpy as np
import shapefile
from PIL import Image
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from shapely.geometry import Point, box as sbox, shape
from shapely.prepared import prep

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
HB_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "HANDBOOK")
DOMAIN_DIR = os.path.join(HB_DIR, "_shared", "sites_handbook_mena")
RAW_DIR = os.path.join(DOMAIN_DIR, "0.raw_data")
CFG_DIR = os.path.join(DOMAIN_DIR, "config")
GJ_DIR = os.path.join(DOMAIN_DIR, "geojson")
HB_GIS_DIR = os.path.join(HB_DIR, "_shared", "_gis_cache")
JADE_GIS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "_gis_cache")
SHARED_GIS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared", "_gis_cache")

POLARIS_GJ_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "POLARIS", "_shared", "sites_IA_RAS", "geojson")
SARAY_GJ_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "SARAY", "_shared", "sites_saray_central_asia", "geojson")
INDUS_GJ_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "INDUS", "_shared", "sites_indus_south_asia", "geojson")
JADE_GJ_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "sites_east_asia", "geojson")
SARAY_RAW_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "SARAY", "_shared", "sites_saray_central_asia", "0.raw_data")
KMZ_PATH = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared", "published_excavations_atlas", "Atlas20200604_Cropped.kmz")
C14_PATH = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_c14bazAAR", "c14_cleaned_dedup.csv")
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
DOMAIN_MASK_PNG = os.path.join(CFG_DIR, "handbook_domain_mask.png")

os.makedirs(CFG_DIR, exist_ok=True)
os.makedirs(GJ_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160
EARTH_R_KM = 6371.0

LAT_MIN, LAT_MAX = 9.5, 46.5
LON_MIN, LON_MAX = -19.5, 77.5

PERIODS = [
  {"epoch_id": 1, "key": "01_epipalaeolithic_early_neolithic", "filename": "01_epipalaeolithic_early_neolithic.png", "geojson_filename": "01_epipalaeolithic_early_neolithic.geojson", "approx_start_year": -13000, "approx_end_year": -6500, "representative_year": -8500},
  {"epoch_id": 2, "key": "02_late_neolithic_chalcolithic", "filename": "02_late_neolithic_chalcolithic.png", "geojson_filename": "02_late_neolithic_chalcolithic.geojson", "approx_start_year": -6500, "approx_end_year": -3200, "representative_year": -4800},
  {"epoch_id": 3, "key": "03_early_middle_bronze_age", "filename": "03_early_middle_bronze_age.png", "geojson_filename": "03_early_middle_bronze_age.geojson", "approx_start_year": -3200, "approx_end_year": -1600, "representative_year": -2300},
  {"epoch_id": 4, "key": "04_late_bronze_iron_age", "filename": "04_late_bronze_iron_age.png", "geojson_filename": "04_late_bronze_iron_age.geojson", "approx_start_year": -1600, "approx_end_year": -539, "representative_year": -1050},
  {"epoch_id": 5, "key": "05_achaemenid_hellenistic", "filename": "05_achaemenid_hellenistic.png", "geojson_filename": "05_achaemenid_hellenistic.geojson", "approx_start_year": -539, "approx_end_year": -30, "representative_year": -280},
  {"epoch_id": 6, "key": "06_roman_parthian_kushan", "filename": "06_roman_parthian_kushan.png", "geojson_filename": "06_roman_parthian_kushan.geojson", "approx_start_year": -30, "approx_end_year": 300, "representative_year": 135},
  {"epoch_id": 7, "key": "07_late_antiquity_sassanid_byzantine", "filename": "07_late_antiquity_sassanid_byzantine.png", "geojson_filename": "07_late_antiquity_sassanid_byzantine.geojson", "approx_start_year": 300, "approx_end_year": 632, "representative_year": 475},
  {"epoch_id": 8, "key": "08_early_islamic_caliphate", "filename": "08_early_islamic_caliphate.png", "geojson_filename": "08_early_islamic_caliphate.geojson", "approx_start_year": 632, "approx_end_year": 1000, "representative_year": 820},
  {"epoch_id": 9, "key": "09_mediaeval_seljuk_mamluk_timurid", "filename": "09_mediaeval_seljuk_mamluk_timurid.png", "geojson_filename": "09_mediaeval_seljuk_mamluk_timurid.geojson", "approx_start_year": 1000, "approx_end_year": 1517, "representative_year": 1280},
  {"epoch_id": 10, "key": "10_early_modern_ottoman_safavid_qajar", "filename": "10_early_modern_ottoman_safavid_qajar.png", "geojson_filename": "10_early_modern_ottoman_safavid_qajar.geojson", "approx_start_year": 1517, "approx_end_year": 1900, "representative_year": 1720},
]
PERIOD_KEYS = [p["key"] for p in PERIODS]

# Source tier classification for Gatekeeper C1 `source_provenance_breakdown`
SOURCE_TIERS = {
  "published_excavations_atlas": "academic_monograph_table",
  "pleiades_ancient_gazetteer": "national_regional_register",
  "althurayya_early_islamic": "academic_monograph_table",
  "ees_delta_survey_egypt": "national_regional_register",
  "cturkey_chronometric_register": "national_regional_register",
  "nerd_near_east_radiocarbon": "national_regional_register",
  "dare_roman_empire_atlas": "national_regional_register",
  "eamena_western_nafud_arabia": "national_regional_register",
  "eamena_khorasan_iran": "national_regional_register",
  "eamena_wadi_naqqat_egypt": "national_regional_register",
  "eamena_gaza_levant": "national_regional_register",
  "pkap_cyprus_survey": "national_regional_register",
  "ca2_mena_archaeological_sites": "academic_monograph_table",
  "ucl_caal_afghanistan_khorasan": "national_regional_register",
  "handbook_monograph_catalogue": "academic_monograph_table",
  "c14_cleaned_dedup_global": "global_radiocarbon",
  "polaris_caucasus_frontier": "national_regional_register",
  "saray_central_asia_frontier": "national_regional_register",
  "indus_pakistan_frontier": "national_regional_register",
  "jade_xinjiang_frontier": "national_regional_register",
}

COUNTRY_TO_JURISDICTION = {
  "Turkey": "turkey",
  "Iran": "iran",
  "Egypt": "egypt",
  "Iraq": "levant_iraq", "Syria": "levant_iraq", "Lebanon": "levant_iraq", "Jordan": "levant_iraq",
  "Israel": "levant_iraq", "Palestine": "levant_iraq", "Cyprus": "levant_iraq",
  "Northern Cyprus": "levant_iraq", "Cyprus No Mans Area": "levant_iraq",
  "Akrotiri Sovereign Base Area": "levant_iraq", "Dhekelia Sovereign Base Area": "levant_iraq",
  "Saudi Arabia": "arabia", "Yemen": "arabia", "Oman": "arabia",
  "United Arab Emirates": "arabia", "Qatar": "arabia", "Bahrain": "arabia", "Kuwait": "arabia",
  "Morocco": "maghreb", "Algeria": "maghreb", "Tunisia": "maghreb", "Libya": "maghreb", "Western Sahara": "maghreb",
  "Armenia": "caucasus_afghanistan", "Azerbaijan": "caucasus_afghanistan",
  "Georgia": "caucasus_afghanistan", "Afghanistan": "caucasus_afghanistan",
}


def latlon_to_rc(lat, lon):
  r = min(GRID_H - 1, max(0, int((90.0 - lat) * GRID_H / 180.0)))
  c = min(GRID_W - 1, max(0, int((lon + 180.0) * GRID_W / 360.0)))
  return r, c


def latlon_to_xyz(lat, lon):
  lr, nr = math.radians(lat), math.radians(lon)
  cl = math.cos(lr)
  return (cl * math.cos(nr), cl * math.sin(nr), math.sin(lr))


def assign_periods_by_span(start_yr, end_yr):
  if start_yr is None or end_yr is None:
    return []
  if start_yr > end_yr:
    start_yr, end_yr = end_yr, start_yr
  if end_yr < -16000 or start_yr > 1920:
    return []
  hits = []
  for p in PERIODS:
    ps, pe = p["approx_start_year"], p["approx_end_year"]
    if start_yr == end_yr:
      if ps <= start_yr <= pe:
        hits.append((p["key"], 1.0))
    else:
      ov = min(end_yr, pe) - max(start_yr, ps)
      if ov > 0:
        hits.append((p["key"], float(ov)))
  if not hits:
    mid = 0.5 * (start_yr + end_yr)
    if mid < -13000:
      return [(PERIODS[0]["key"], 1.0)]
    if 1900 < mid <= 1940:
      return [(PERIODS[-1]["key"], 1.0)]
    return []
  tot = sum(w for _, w in hits)
  return [(k, w / tot) for k, w in hits]


def classify_mena_text(text):
  s = (text or "").lower()
  if not s:
    return []
  hits = []
  rules = [
    (["natufian", "epipalaeolithic", "epipaleolithic", "ppna", "ppnb", "pre-pottery", "capsian", "iberomaurusian", "mesolithic", "palaeolithic", "paleolithic", "early neolithic", "gobekli", "zarzian", "kebaran"], "01_epipalaeolithic_early_neolithic"),
    (["halaf", "ubaid", "uruk", "chalcolithic", "eneolithic", "predynastic", "badarian", "naqada", "merimde", "late neolithic", "ceramic neolithic", "shulaveri", "hassuna", "samarra", "ghassulian", "susiana", "bakun", "sialk", "neolithic"], "02_late_neolithic_chalcolithic"),
    (["early bronze", "middle bronze", "sumer", "akkad", "old kingdom", "middle kingdom", "first intermediate", "early dynastic", "kura-aras", "elam", "dilmun", "magan", "umm an-nar", "bmac", "eb ", "mb ", "eba", "mba", "third dynasty", "babylon"], "03_early_middle_bronze_age"),
    (["late bronze", "iron age", "new kingdom", "hittite", "assyria", "neo-assyrian", "neo-babylonian", "phoenician", "israelite", "judah", "urartu", "phrygian", "lydian", "medes", "saba", "sabaean", "minean", "qataban", "lb ", "lba", "ia ", "ramesside", "amarna", "third intermediate", "late period", "punic", "carthag"], "04_late_bronze_iron_age"),
    (["achaemenid", "persian", "hellenistic", "ptolemaic", "seleucid", "greco-bactrian", "nabataean", "garamant", "numidian", "classical", "archaic", "mauretania"], "05_achaemenid_hellenistic"),
    (["roman", "parthian", "kushan", "himyar", "imperial", "palmyra", "petra", "greco-roman", "graeco-roman", "hadramawt"], "06_roman_parthian_kushan"),
    (["byzantine", "late antique", "late antiquity", "sassanid", "sasanian", "late roman", "coptic", "christian", "monastery", "basilica", "ghassanid", "lakhmid"], "07_late_antiquity_sassanid_byzantine"),
    (["umayyad", "abbasid", "early islamic", "rashidun", "fatimid", "tulunid", "aghlabid", "idrisid", "samanid", "saffarid", "buyid", "hamdanid"], "08_early_islamic_caliphate"),
    (["seljuk", "ayyubid", "mamluk", "crusader", "ilkhanid", "timurid", "almoravid", "almohad", "marinid", "hafsid", "zayyanid", "mediaeval", "medieval", "middle islamic", "khwarazm", "ghaznavid", "ghurid", "lusignan", "rasulid", "bagratid", "georgian"], "09_mediaeval_seljuk_mamluk_timurid"),
    (["ottoman", "safavid", "qajar", "afsharid", "durrani", "post-medieval", "late islamic", "saadian", "alaouite", "khediv", "caravanserai", "qanat"], "10_early_modern_ottoman_safavid_qajar"),
  ]
  for kws, pk in rules:
    if any(k in s for k in kws):
      hits.append(pk)
  if hits:
    w = 1.0 / len(hits)
    return [(pk, w) for pk in hits]
  return []


def build_catchments(domain_mask, land_area, hyde_dens):
  """Discretises HANDBOOK + 300 km cross-frontier belt into tight, scale-adaptive HydroBASINS L6 catchments
  (<= 4,800 km2 in settled/agricultural zones; <= 14,000 km2 in hyper-arid desert interior)."""
  print("[A] Building tight scale-adaptive HydroBASINS Level 6 catchments (settled <= 4,800 km2; arid <= 14,000 km2)...", flush=True)
  dist_px = distance_transform_edt(~domain_mask)
  frontier_mask = (~domain_mask) & (dist_px <= 36) & (land_area > 0)

  raw_basins = []
  hyb_files = [
    ("af", os.path.join(HB_GIS_DIR, "hybas_af_lev06_v1c.zip")),
    ("eu", os.path.join(HB_GIS_DIR, "hybas_eu_lev06_v1c.zip")),
    ("as", os.path.join(JADE_GIS_DIR, "hybas_as_lev06_v1c.zip")),
  ]
  for tag, hp in hyb_files:
    if not os.path.exists(hp):
      continue
    with zipfile.ZipFile(hp) as zf:
      sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
      sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
      for idx, sr in enumerate(sf.iterShapeRecords()):
        bb = sr.shape.bbox
        if bb[2] < LON_MIN or bb[0] > LON_MAX or bb[3] < LAT_MIN or bb[1] > LAT_MAX:
          continue
        g = shape(sr.shape.__geo_interface__).buffer(0)
        if not g.is_empty:
          raw_basins.append((f"{tag}_{idx}", g))

  catchments = []
  cid_counter = 0

  def add_polygon_catchment(poly, base_id, is_dom, depth=0):
    nonlocal cid_counter
    if poly is None or poly.is_empty:
      return
    minx, miny, maxx, maxy = poly.bounds
    r0, c0 = latlon_to_rc(maxy, minx)
    r1, c1 = latlon_to_rc(miny, maxx)
    target_m = domain_mask if is_dom else frontier_mask
    sub = target_m[r0:r1 + 1, c0:c1 + 1]
    if not sub.any():
      return
    pg = prep(poly)
    drs, dcs = np.where(sub)
    area_km2 = 0.0
    hyde_sum = 0.0
    lat_sum, lon_sum, cnt = 0.0, 0.0, 0
    for dr, dc in zip(drs, dcs):
      rr, cc = r0 + int(dr), c0 + int(dc)
      plat = 90.0 - (rr + 0.5) * 180.0 / GRID_H
      plon = -180.0 + (cc + 0.5) * 360.0 / GRID_W
      if pg.contains(Point(plon, plat)):
        a_cell = float(land_area[rr, cc])
        area_km2 += a_cell
        hyde_sum += float(hyde_dens[rr, cc]) * a_cell
        lat_sum += plat
        lon_sum += plon
        cnt += 1
    if cnt < 3 or area_km2 < 100.0:
      return
    mean_h = hyde_sum / max(1.0, area_km2)
    area_cap = (4800.0 if mean_h >= 0.08 else 14000.0) if is_dom else 15000.0
    if area_km2 > area_cap and depth < 6 and (maxx - minx > 0.35 or maxy - miny > 0.35):
      if (maxx - minx) * math.cos(math.radians(0.5 * (miny + maxy))) >= (maxy - miny):
        mx = 0.5 * (minx + maxx)
        add_polygon_catchment(poly.intersection(sbox(minx, miny, mx, maxy)).buffer(0), base_id + "w", is_dom, depth + 1)
        add_polygon_catchment(poly.intersection(sbox(mx, miny, maxx, maxy)).buffer(0), base_id + "e", is_dom, depth + 1)
      else:
        my = 0.5 * (miny + maxy)
        add_polygon_catchment(poly.intersection(sbox(minx, miny, maxx, my)).buffer(0), base_id + "s", is_dom, depth + 1)
        add_polygon_catchment(poly.intersection(sbox(minx, my, maxx, maxy)).buffer(0), base_id + "n", is_dom, depth + 1)
      return

    cid_counter += 1
    clat, clon = lat_sum / cnt, lon_sum / cnt
    catchments.append({
      "region_id": f"{'dom' if is_dom else 'fr'}_{cid_counter:04d}_{base_id}",
      "lat": clat,
      "lon": clon,
      "xyz": latlon_to_xyz(clat, clon),
      "area_km2": round(area_km2, 1),
      "pixel_count": cnt,
      "is_frontier_buffer": not is_dom,
    })

  for bid, g in raw_basins:
    add_polygon_catchment(g, bid, True)
    add_polygon_catchment(g, bid, False)

  # Ensure small islands (Cyprus, Bahrain, Socotra) have explicit catchments if missed by coarse basins
  dom_c = [c for c in catchments if not c["is_frontier_buffer"]]
  if dom_c:
    dom_tree = cKDTree(np.array([c["xyz"] for c in dom_c]))
    rs, cs = np.where(domain_mask)
    step = 10
    uncov = {}
    for rr, cc in zip(rs[::step], cs[::step]):
      plat = 90.0 - (rr + 0.5) * 180.0 / GRID_H
      plon = -180.0 + (cc + 0.5) * 360.0 / GRID_W
      d, _ = dom_tree.query(latlon_to_xyz(plat, plon))
      if d * EARTH_R_KM > 125.0:
        bk = (int(math.floor(plat / 1.25)), int(math.floor(plon / 1.5)))
        uncov.setdefault(bk, []).append((plat, plon, float(land_area[rr, cc]) * step))
    for bk, pts in uncov.items():
      cid_counter += 1
      catchments.append({
        "region_id": f"dom_{cid_counter:04d}_isl_{bk[0]}_{bk[1]}",
        "lat": sum(x[0] for x in pts) / len(pts),
        "lon": sum(x[1] for x in pts) / len(pts),
        "xyz": latlon_to_xyz(sum(x[0] for x in pts) / len(pts), sum(x[1] for x in pts) / len(pts)),
        "area_km2": round(min(22000.0, max(600.0, sum(x[2] for x in pts))), 1),
        "pixel_count": len(pts) * step,
        "is_frontier_buffer": False,
      })

  dom_n = sum(1 for c in catchments if not c["is_frontier_buffer"])
  fr_n = sum(1 for c in catchments if c["is_frontier_buffer"])
  max_a = max((c["area_km2"] for c in catchments if not c["is_frontier_buffer"]), default=0)
  print(f"  Built {dom_n} domestic catchments (max area {max_a:,.0f} km2) + {fr_n} frontier catchments.", flush=True)
  return catchments


def build_curated_handbook_monograph_catalogue():
  """Canonical excavated archaeological type-sites & historic capitals across all 7 HANDBOOK jurisdictions."""
  # (lat, lon, weight, start_yr, end_yr, max_pop)
  sites = [
    # --- TURKEY (Anatolia & Thrace) ---
    (37.22, 38.92, 4.0, -9600, -8000, 1000),   # Gobekli Tepe
    (37.67, 32.83, 4.5, -7500, -5700, 8000),   # Catalhoyuk
    (38.35, 34.23, 3.5, -8200, -7300, 1500),   # Asikli Hoyuk
    (38.12, 39.77, 3.5, -9000, -6800, 1200),   # Cayonu
    (39.96, 26.24, 4.5, -3000, 500, 25000),    # Troy (Hisarlik)
    (40.02, 34.62, 5.0, -2500, -1180, 45000),  # Hattusa (Bogazkale)
    (38.85, 35.63, 4.0, -2500, -1700, 20000),  # Kanesh (Kultepe)
    (38.38, 38.36, 4.0, -4500, -700, 15000),   # Arslantepe (Malatya)
    (39.65, 31.99, 4.0, -2300, 100, 35000),    # Gordion
    (38.49, 28.04, 4.5, -1200, 1400, 60000),   # Sardis
    (37.94, 27.34, 5.0, -1000, 1400, 200000),  # Ephesus
    (37.53, 27.28, 4.5, -1500, 1400, 80000),   # Miletus
    (39.13, 27.18, 4.5, -400, 1400, 120000),   # Pergamon
    (36.20, 36.16, 5.0, -300, 1900, 250000),   # Antioch on the Orontes (Antakya)
    (41.01, 28.98, 5.0, -660, 1900, 900000),   # Byzantium / Constantinople / Istanbul
    (38.42, 27.14, 4.5, -1000, 1900, 200000),  # Smyrna / Izmir
    (39.93, 32.86, 4.5, -800, 1900, 50000),    # Ancyra / Ankara
    (37.87, 32.48, 4.5, -2500, 1900, 90000),   # Iconium / Konya
    (38.50, 43.34, 4.5, -850, 1900, 50000),    # Tushpa / Van (Urartu)
    (40.19, 29.06, 4.5, -200, 1900, 120000),   # Prusa / Bursa
    (41.00, 39.72, 4.5, -756, 1900, 60000),    # Trapezus / Trabzon
    (37.91, 40.24, 4.5, -1300, 1900, 75000),   # Amida / Diyarbakir
    (39.91, 41.27, 4.0, 400, 1900, 60000),     # Theodosiopolis / Erzurum
    # --- MESOPOTAMIA & LEVANT & CYPRUS ---
    (31.32, 45.64, 5.0, -4200, 700, 80000),    # Uruk (Warka)
    (30.96, 46.10, 5.0, -4500, -400, 65000),   # Ur (Tell el-Muqayyar)
    (30.82, 45.99, 4.0, -5400, -600, 10000),   # Eridu
    (31.61, 46.17, 4.5, -3000, -1700, 40000),  # Girsu / Lagash
    (32.13, 45.23, 4.5, -4500, 800, 35000),    # Nippur
    (32.54, 44.42, 5.0, -2300, 200, 200000),   # Babylon
    (33.10, 44.58, 5.0, -305, 800, 450000),    # Seleucia-Ctesiphon
    (33.31, 44.37, 5.0, 762, 1900, 900000),    # Baghdad
    (34.20, 43.87, 4.5, 836, 1200, 250000),    # Samarra
    (35.46, 43.26, 4.5, -2600, 250, 45000),    # Assur (Qal'at Sherqat)
    (36.36, 43.15, 5.0, -6000, 1900, 150000),  # Nineveh / Mosul
    (36.10, 43.33, 4.5, -1300, -612, 75000),   # Nimrud (Kalhu)
    (36.19, 44.01, 4.5, -5000, 1900, 45000),   # Arbela / Erbil
    (30.51, 47.81, 4.5, 636, 1900, 200000),    # Basra
    (32.03, 44.40, 4.5, 638, 1300, 150000),    # Kufa
    (34.55, 40.89, 4.5, -2900, -1759, 45000),  # Mari (Tell Hariri)
    (35.80, 36.63, 4.5, -3000, -1600, 40000),  # Ebla (Tell Mardikh)
    (35.60, 35.78, 4.5, -6000, -1185, 25000),  # Ugarit (Ras Shamra)
    (36.20, 37.16, 5.0, -3000, 1900, 250000),  # Aleppo (Halab)
    (33.51, 36.29, 5.0, -7000, 1900, 220000),  # Damascus
    (34.55, 38.27, 4.5, -2000, 1100, 120000),  # Palmyra (Tadmor)
    (36.67, 41.06, 4.0, -5000, -1200, 25000),  # Tell Brak (Nagar)
    (33.27, 35.20, 4.5, -2750, 1900, 60000),   # Tyre
    (33.56, 35.37, 4.5, -4000, 1900, 50000),   # Sidon
    (34.12, 35.65, 4.5, -6000, 1900, 25000),   # Byblos
    (33.89, 35.50, 4.5, -1500, 1900, 120000),  # Berytus / Beirut
    (31.87, 35.44, 4.5, -9500, 1900, 15000),   # Jericho (Tell es-Sultan)
    (31.78, 35.23, 5.0, -3500, 1900, 85000),   # Jerusalem
    (32.50, 35.18, 4.0, -4000, -350, 18000),   # Megiddo
    (33.02, 35.57, 4.0, -2800, -732, 30000),   # Hazor
    (32.50, 34.89, 4.5, -22, 1265, 100000),    # Caesarea Maritima
    (31.50, 34.47, 4.5, -1500, 1900, 45000),   # Gaza
    (31.95, 35.93, 4.5, -7200, 1900, 45000),   # Ain Ghazal / Rabbath Ammon / Amman
    (30.33, 35.44, 4.5, -400, 700, 30000),     # Petra
    (32.28, 35.89, 4.0, -300, 900, 25000),     # Gerasa (Jerash)
    (34.79, 33.34, 3.5, -7000, -5500, 1500),   # Khirokitia (Cyprus)
    (35.17, 33.89, 4.5, -1600, 700, 60000),    # Enkomi / Salamis (Cyprus)
    (34.76, 32.41, 4.0, -1200, 1900, 30000),   # Paphos (Cyprus)
    (35.17, 33.36, 4.5, -700, 1900, 35000),    # Ledra / Nicosia (Cyprus)
    # --- EGYPT ---
    (29.85, 31.25, 5.0, -3100, 641, 120000),   # Memphis
    (25.70, 32.64, 5.0, -3200, 641, 100000),   # Thebes (Luxor / Karnak)
    (26.18, 31.92, 4.5, -3500, 300, 35000),    # Abydos
    (25.10, 32.78, 4.0, -3800, -2500, 12000),  # Hierakonpolis (Nekhen)
    (27.64, 30.90, 4.5, -1346, -1332, 35000),  # Amarna (Akhetaten)
    (30.79, 31.82, 4.5, -1700, -1069, 90000),  # Avaris / Pi-Ramesses
    (30.98, 31.88, 4.5, -1070, 300, 50000),    # Tanis
    (31.20, 29.92, 5.0, -331, 1900, 500000),   # Alexandria
    (30.04, 31.24, 5.0, 641, 1900, 550000),    # Fustat / Cairo
    (29.31, 30.84, 4.5, -4500, 1900, 60000),   # Crocodilopolis / Fayum
    (27.18, 31.18, 4.5, -2500, 1900, 55000),   # Lykopolis / Asyut
    (24.09, 32.90, 4.0, -3000, 1900, 30000),   # Elephantine / Aswan
    (25.44, 30.55, 3.5, -3000, 1900, 12000),   # Kharga Oasis (Hibis)
    (29.20, 25.52, 3.5, -1000, 1900, 8000),    # Siwa Oasis
    # --- IRAN ---
    (32.19, 48.24, 5.0, -4200, 1200, 120000),  # Susa (Shush)
    (32.28, 48.52, 4.0, -1250, -640, 20000),   # Chogha Zanbil (Dur-Untash)
    (29.94, 52.89, 5.0, -518, -330, 80000),    # Persepolis & Istakhr
    (30.20, 53.17, 4.0, -550, -330, 25000),    # Pasargadae
    (34.80, 48.51, 5.0, -700, 1900, 90000),    # Ecbatana / Hamadan
    (35.59, 51.43, 5.0, -6000, 1900, 250000),  # Rayy / Tehran
    (33.97, 51.40, 4.0, -6000, -700, 12000),   # Tepe Sialk (Kashan)
    (32.65, 51.67, 5.0, -500, 1900, 500000),   # Spadana / Isfahan
    (29.59, 52.58, 4.5, 693, 1900, 150000),    # Shiraz
    (38.08, 46.29, 5.0, -800, 1900, 250000),   # Tabriz
    (36.21, 58.79, 5.0, 250, 1900, 200000),    # Nishapur
    (36.26, 59.62, 5.0, 818, 1900, 180000),    # Tus / Mashhad
    (30.60, 61.33, 4.5, -3200, -1800, 25000),  # Shahr-i Sokhta (Sistan)
    (28.67, 57.74, 4.0, -3000, -2000, 15000),  # Jiroft (Konar Sandal)
    (36.13, 54.39, 4.0, -4500, 1400, 35000),   # Tepe Hissar / Damghan (Hecatompylos)
    (31.90, 54.37, 4.0, -500, 1900, 65000),    # Yazd
    (30.28, 57.08, 4.5, 230, 1900, 80000),     # Kerman
    (37.28, 49.58, 4.0, 1000, 1900, 65000),    # Rasht / Gilan
    (36.84, 54.44, 4.5, -3500, 1900, 75000),   # Tureng Tepe / Gorgan / Astarabad
    # --- AFGHANISTAN (Warwick Ball Gazetteer & DAFA benchmark sites) ---
    (36.76, 66.90, 5.0, -2000, 1900, 180000),  # Balkh (Bactra)
    (37.17, 69.41, 4.5, -300, -145, 45000),    # Ai-Khanoum
    (34.34, 62.20, 5.0, -500, 1900, 200000),   # Herat (Aria)
    (31.62, 65.71, 4.5, -1000, 1900, 100000),  # Kandahar (Old Kandahar / Arachosia)
    (31.83, 65.43, 4.0, -3500, -1500, 15000),  # Mundigak
    (34.53, 69.17, 5.0, -1500, 1900, 150000),  # Kabul
    (34.99, 69.29, 4.5, -500, 650, 55000),     # Begram (Kapisa)
    (34.83, 67.83, 4.0, 200, 1221, 35000),     # Bamiyan
    (33.55, 68.42, 4.5, 600, 1900, 120000),    # Ghazni
    (31.59, 64.36, 4.5, -500, 1383, 75000),    # Bost / Lashkari Bazar
    (30.97, 61.86, 4.5, -500, 1383, 80000),    # Zaranj (Drangiana / Sistan)
    (34.43, 70.45, 4.5, -300, 1900, 45000),    # Hadda / Jalalabad (Nagarahara)
    (36.73, 68.86, 4.0, -300, 1900, 35000),    # Kunduz / Shortugai
    (36.98, 66.22, 4.0, -2000, 1220, 25000),   # Dashli / Sheberghan / Tillya Tepe
    (34.39, 64.52, 3.5, 1100, 1222, 20000),    # Firuzkuh / Jam (Ghurid Capital)
    (32.37, 62.12, 3.5, -500, 1900, 18000),    # Farah (Phrada)
    # --- TRANSCAUCASIA (Georgia, Armenia, Azerbaijan) ---
    (41.72, 44.78, 5.0, -3000, 1900, 160000),  # Tbilisi
    (41.84, 44.72, 4.5, -1000, 1500, 45000),   # Mtskheta (Iberian Capital)
    (42.27, 42.70, 4.5, -1500, 1900, 50000),   # Kutaisi (Colchis)
    (41.97, 44.21, 3.5, -1000, 1300, 15000),   # Uplistsikhe
    (41.36, 44.34, 3.5, -5500, 1300, 12000),   # Dmanisi / Shulaveri
    (40.14, 44.54, 4.5, -782, 1900, 65000),    # Erebuni / Yerevan
    (40.51, 43.57, 4.5, 961, 1350, 100000),    # Ani (Bagratid Capital)
    (40.00, 44.57, 4.5, -176, 500, 60000),     # Artaxata (Artashat)
    (40.00, 44.58, 4.5, 335, 1236, 75000),     # Dvin
    (40.17, 44.29, 4.0, -500, 1900, 25000),    # Vagharshapat / Metsamor
    (40.41, 49.87, 4.5, 500, 1900, 180000),    # Baku
    (40.68, 46.36, 4.5, 859, 1900, 120000),    # Ganja
    (40.37, 47.13, 4.5, 450, 1200, 80000),     # Barda (Partav, Caucasian Albania)
    (40.98, 47.85, 4.0, -400, 1000, 35000),    # Kabala (Qabala)
    (40.63, 48.64, 4.5, 500, 1900, 55000),     # Shamakhi (Shirvan)
    (39.21, 45.41, 4.0, -1500, 1900, 25000),   # Nakhchivan / Kultepe
    # --- ARABIAN PENINSULA ---
    (15.42, 45.34, 5.0, -1200, 600, 55000),    # Marib (Sabaean Capital)
    (15.35, 44.21, 5.0, 100, 1900, 65000),     # Sana'a
    (14.21, 44.40, 4.5, -110, 550, 40000),     # Zafar (Himyarite Capital)
    (15.01, 45.82, 4.0, -800, 200, 20000),     # Timna (Qataban)
    (15.37, 47.02, 4.0, -600, 400, 22000),     # Shabwa (Hadramawt)
    (16.17, 44.78, 4.0, -800, -100, 18000),    # Qarnaw / Baraqish (Ma'in)
    (12.79, 45.03, 4.5, -500, 1900, 50000),    # Aden
    (14.20, 43.32, 4.5, 820, 1900, 40000),     # Zabid
    (21.42, 39.83, 5.0, 400, 1900, 80000),     # Mecca
    (24.47, 39.61, 5.0, -500, 1900, 55000),    # Yathrib / Medina
    (21.49, 39.19, 4.5, 647, 1900, 45000),     # Jeddah
    (26.79, 37.95, 4.5, -600, 400, 25000),     # Dedan / Al-Ula / Hegra (Mada'in Salih)
    (27.63, 38.54, 4.5, -2000, 1200, 22000),   # Tayma
    (29.81, 39.87, 4.0, -1000, 1900, 15000),   # Dumat al-Jandal
    (17.49, 44.13, 4.0, -600, 1900, 20000),    # Najran (Al-Ukhdud)
    (19.79, 45.16, 4.0, -400, 400, 18000),     # Qaryat al-Faw (Kinda)
    (24.73, 46.57, 4.5, 1446, 1900, 35000),    # Diriyah / Riyadh (Najd)
    (25.38, 49.59, 4.5, -500, 1900, 45000),    # Al-Hasa / Hofuf / Gerrha
    (26.23, 50.52, 4.5, -2500, 1900, 40000),   # Qal'at al-Bahrain (Dilmun)
    (24.36, 56.74, 4.5, -2500, 1900, 50000),   # Sohar (Magan / Oman)
    (23.61, 58.59, 4.5, 200, 1900, 45000),     # Muscat
    (22.93, 57.53, 4.0, 600, 1900, 25000),     # Nizwa / Bat (Oman)
    (17.03, 54.43, 4.0, -300, 1500, 20000),    # Sumhuram / Khor Rori / Salalah
    (24.21, 55.77, 4.0, -3000, 1900, 18000),   # Hili / Al-Ain (UAE)
    (25.79, 55.94, 4.0, 500, 1900, 25000),     # Julfar / Ras al-Khaimah
    (29.44, 48.33, 4.0, -2300, 1900, 25000),   # Failaka / Kuwait
    (25.98, 51.03, 3.5, 1760, 1900, 12000),    # Al Zubarah (Qatar)
    # --- MAGHREB & LIBYA ---
    (36.85, 10.32, 5.0, -814, 1900, 350000),   # Carthage / Tunis
    (35.68, 10.10, 5.0, 670, 1900, 100000),    # Kairouan
    (36.42, 9.22, 4.0, -500, 650, 20000),      # Dougga (Thugga)
    (35.83, 10.64, 4.5, -900, 1900, 40000),    # Hadrumetum / Sousse
    (34.74, 10.76, 4.0, -300, 1900, 35000),    # Sfax / Taparura
    (32.64, 14.29, 5.0, -700, 650, 100000),    # Leptis Magna
    (32.89, 13.19, 4.5, -700, 1900, 60000),    # Oea / Tripoli
    (32.82, 21.86, 4.5, -631, 643, 85000),     # Cyrene (Shahat)
    (32.12, 20.07, 4.0, -525, 1900, 35000),    # Berenice / Benghazi
    (26.55, 13.06, 4.5, -500, 1200, 20000),    # Garama (Jarma, Garamantes Fezzan)
    (30.13, 9.50, 3.5, -100, 1900, 12000),     # Ghadames (Cydamus)
    (36.36, 6.61, 4.5, -300, 1900, 75000),     # Cirta / Constantine
    (36.60, 2.45, 4.5, -500, 1900, 50000),     # Caesarea (Cherchell) / Tipasa
    (35.48, 6.47, 4.0, 100, 650, 25000),       # Timgad (Thamugadi)
    (36.75, 3.06, 5.0, -600, 1900, 120000),    # Icosium / Algiers
    (34.88, -1.32, 4.5, 200, 1900, 95000),     # Pomaria / Tlemcen
    (36.75, 5.08, 4.5, 1067, 1900, 70000),     # Bejaia (Saldae)
    (35.70, -0.63, 4.5, 903, 1900, 75000),     # Oran
    (34.07, -5.55, 4.5, -300, 1050, 30000),    # Volubilis
    (34.06, -4.98, 5.0, 789, 1900, 180000),    # Fez
    (31.63, -8.00, 5.0, 1070, 1900, 160000),   # Marrakech
    (31.28, -4.28, 4.5, 757, 1400, 45000),     # Sijilmasa (Tafilalt)
    (35.78, -5.81, 4.5, -500, 1900, 55000),    # Tingis / Tangier
    (34.02, -6.84, 4.5, -600, 1900, 65000),    # Chellah / Sala / Rabat
    (33.90, -5.55, 4.5, 1000, 1900, 90000),    # Meknes
    (26.74, -11.68, 3.0, -5000, 1850, 5000),   # Smara / Saguia el-Hamra (Western Sahara)
  ]
  out = []
  for la, lo, wt, sy, ey, mp in sites:
    pw = assign_periods_by_span(sy, ey)
    if pw:
      out.append((la, lo, wt, pw, "handbook_monograph_catalogue", True, mp))
  return out


def ingest_all_repositories():
  print("[B] Ingesting 12 primary institutional & scholarly archaeological repositories across HANDBOOK...", flush=True)
  records = []
  source_stats = Counter()

  # --- REPO 1: Published Excavations Atlas (ArchAtlas KMZ, 26,766 sites in HANDBOOK) ---
  if os.path.exists(KMZ_PATH):
    with zipfile.ZipFile(KMZ_PATH) as zf:
      kml_name = [n for n in zf.namelist() if n.endswith(".kml")][0]
      root = ET.fromstring(zf.read(kml_name))
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    for pm in root.findall(".//kml:Placemark", ns):
      ct = (pm.findtext(".//kml:coordinates", "", ns) or "").strip()
      if not ct:
        continue
      parts = ct.split()[0].split(",")
      if len(parts) < 2:
        continue
      try:
        lo, la = float(parts[0]), float(parts[1])
      except Exception:
        continue
      if not (LAT_MIN <= la <= LAT_MAX and LON_MIN <= lo <= LON_MAX):
        continue
      nm = pm.findtext("kml:name", "", ns) or ""
      desc = pm.findtext("kml:description", "", ns) or ""
      pw = classify_mena_text(f"{nm} {desc}")
      if not pw:
        # Multi-period published Near Eastern/North African excavation fallback (weighted across Bronze-Islamic core)
        pw = [
          ("02_late_neolithic_chalcolithic", 0.12),
          ("03_early_middle_bronze_age", 0.18),
          ("04_late_bronze_iron_age", 0.18),
          ("05_achaemenid_hellenistic", 0.14),
          ("06_roman_parthian_kushan", 0.16),
          ("07_late_antiquity_sassanid_byzantine", 0.12),
          ("08_early_islamic_caliphate", 0.10),
        ]
      records.append((la, lo, 1.8, pw, "published_excavations_atlas", True, 0))
      source_stats["published_excavations_atlas"] += 1

  # --- REPO 2: Pleiades Ancient World Gazetteer (30,185 sites) ---
  pl_p = os.path.join(RAW_DIR, "pleiades_handbook.json")
  if os.path.exists(pl_p):
    for row in json.load(open(pl_p, "r", encoding="utf-8")):
      la, lo = float(row["lat"]), float(row["lon"])
      if not (LAT_MIN <= la <= LAT_MAX and LON_MIN <= lo <= LON_MAX):
        continue
      ft = (row.get("featureTypes") or "").lower()
      if any(skip in ft for skip in ("water-open", "region", "mountain", "river", "cape", "bay", "gulf", "strait", "island-group")):
        continue
      try:
        sy = int(float(row["minDate"])) if row.get("minDate") not in (None, "") else -500
        ey = int(float(row["maxDate"])) if row.get("maxDate") not in (None, "") else 500
      except Exception:
        sy, ey = -500, 500
      pw = assign_periods_by_span(sy, ey)
      if not pw:
        continue
      is_s = any(k in ft for k in ("settlement", "city", "urban", "port", "fort", "villa", "station", "oasis", "village"))
      wt = 2.0 if is_s else 1.2
      records.append((la, lo, wt, pw, "pleiades_ancient_gazetteer", is_s, 0))
      source_stats["pleiades_ancient_gazetteer"] += 1

  # --- REPO 3: Al-Thurayya Early Islamic Gazetteer (2,501 settlements) ---
  at_p = os.path.join(RAW_DIR, "althurayya_handbook.json")
  if os.path.exists(at_p):
    for row in json.load(open(at_p, "r", encoding="utf-8")):
      la, lo = float(row["lat"]), float(row["lon"])
      if not (LAT_MIN <= la <= LAT_MAX and LON_MIN <= lo <= LON_MAX):
        continue
      tt = (row.get("top_type") or "").lower()
      wt = 3.0 if "metrop" in tt else (2.4 if "capit" in tt else (1.8 if "town" in tt else 1.3))
      pw = [
        ("07_late_antiquity_sassanid_byzantine", 0.10),
        ("08_early_islamic_caliphate", 0.45),
        ("09_mediaeval_seljuk_mamluk_timurid", 0.30),
        ("10_early_modern_ottoman_safavid_qajar", 0.15),
      ]
      records.append((la, lo, wt, pw, "althurayya_early_islamic", True, 5000 if wt >= 2.4 else 0))
      source_stats["althurayya_early_islamic"] += 1

  # --- REPO 4: EES Delta Survey (Egypt Exploration Society official ArcGIS register) ---
  for fn in ("ees_delta_wfl1_L1.geojson", "ees_outside_delta_L20.geojson"):
    ep = os.path.join(RAW_DIR, fn)
    if not os.path.exists(ep):
      continue
    for feat in json.load(open(ep, "r", encoding="utf-8")).get("features", []):
      coords = (feat.get("geometry") or {}).get("coordinates") or []
      if len(coords) < 2:
        continue
      lo, la = float(coords[0]), float(coords[1])
      props = feat.get("properties") or {}
      txt = f"{props.get('Name', '')} {props.get('Periods', '')} {props.get('Other_Name', '')}"
      pw = classify_mena_text(txt)
      if not pw:
        pw = [
          ("02_late_neolithic_chalcolithic", 0.10),
          ("03_early_middle_bronze_age", 0.25),
          ("04_late_bronze_iron_age", 0.25),
          ("05_achaemenid_hellenistic", 0.20),
          ("06_roman_parthian_kushan", 0.20),
        ]
      records.append((la, lo, 2.2, pw, "ees_delta_survey_egypt", True, 0))
      source_stats["ees_delta_survey_egypt"] += 1

  # --- REPO 5: C-Turkey (Altinisik et al., Anatolia & Thrace chronometric register) ---
  ct_p = os.path.join(RAW_DIR, "cturkey_v1.tsv")
  if os.path.exists(ct_p):
    seen_ct = set()
    with open(ct_p, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh, delimiter="\t"):
        try:
          la = float(row.get("lat") or "")
          lo = float(row.get("lon") or "")
        except Exception:
          continue
        if not (35.5 <= la <= 42.5 and 25.5 <= lo <= 45.0):
          continue
        try:
          bp = float(row.get("c14age") or "")
          yr = int(round(1950.0 - bp * 1.07))
          pw = assign_periods_by_span(yr - 150, yr + 150)
        except Exception:
          pw = classify_mena_text(f"{row.get('period', '')} {row.get('culture', '')} {row.get('site', '')}")
        if not pw:
          continue
        sk = (round(la, 3), round(lo, 3), pw[0][0])
        if sk in seen_ct:
          continue
        seen_ct.add(sk)
        records.append((la, lo, 2.0, pw, "cturkey_chronometric_register", True, 0))
        source_stats["cturkey_chronometric_register"] += 1

  # --- REPO 6: NERD (Near East Radiocarbon Dates, Palmisano et al. 2022) ---
  nerd_p = os.path.join(RAW_DIR, "nerd_radiocarbon.csv")
  if os.path.exists(nerd_p):
    seen_n = set()
    with open(nerd_p, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        try:
          la = float(row.get("Latitude") or "")
          lo = float(row.get("Longitude") or "")
          cra = float(row.get("CRA") or "")
        except Exception:
          continue
        if not (LAT_MIN <= la <= LAT_MAX and LON_MIN <= lo <= LON_MAX):
          continue
        yr = int(round(1950.0 - cra * 1.08))
        pw = assign_periods_by_span(yr - 150, yr + 150)
        if not pw:
          continue
        sk = (round(la, 3), round(lo, 3), pw[0][0])
        if sk in seen_n:
          continue
        seen_n.add(sk)
        records.append((la, lo, 2.0, pw, "nerd_near_east_radiocarbon", True, 0))
        source_stats["nerd_near_east_radiocarbon"] += 1

  # --- REPO 7: DARE (Digital Atlas of the Roman Empire, 809 MENA/Anatolia/North Africa sites) ---
  dare_p = os.path.join(RAW_DIR, "dare_roman_mena.json")
  if os.path.exists(dare_p):
    for row in json.load(open(dare_p, "r", encoding="utf-8")):
      la, lo = float(row["lat"]), float(row["lon"])
      if not (LAT_MIN <= la <= LAT_MAX and LON_MIN <= lo <= LON_MAX):
        continue
      pw = [
        ("05_achaemenid_hellenistic", 0.15),
        ("06_roman_parthian_kushan", 0.55),
        ("07_late_antiquity_sassanid_byzantine", 0.30),
      ]
      records.append((la, lo, 2.0, pw, "dare_roman_empire_atlas", True, 0))
      source_stats["dare_roman_empire_atlas"] += 1

  # --- REPO 8: EAMENA & Regional Field Surveys (Western Nafud, Khorasan, Wadi Naqqat, Gaza, CA2, PKAP) ---
  def ingest_geojson_features(feats, tag, default_pw, wt=2.0):
    for feat in feats:
      geom = feat.get("geometry") or {}
      gtype = geom.get("type")
      coords = geom.get("coordinates")
      if not coords:
        continue
      try:
        if gtype == "Point":
          lo, la = float(coords[0]), float(coords[1])
        else:
          rp = shape(geom).representative_point()
          lo, la = float(rp.x), float(rp.y)
      except Exception:
        continue
      if not (LAT_MIN <= la <= LAT_MAX and LON_MIN <= lo <= LON_MAX):
        continue
      props = feat.get("properties") or {}
      txt = " ".join(str(v) for v in props.values() if isinstance(v, (str, int, float)))[:300]
      pw = classify_mena_text(txt) or default_pw
      records.append((la, lo, wt, pw, tag, True, 0))
      source_stats[tag] += 1

  zips_spec = [
    ("eamena_nafud_mapping_the_archaeological_landscapes_of_the_western_nafud.zip", "eamena_western_nafud_arabia",
     [("01_epipalaeolithic_early_neolithic", 0.25), ("02_late_neolithic_chalcolithic", 0.35), ("03_early_middle_bronze_age", 0.25), ("04_late_bronze_iron_age", 0.15)]),
    ("iran_khorasan_dataset_on_caravanserais_and_qanat_networks_in_khorasan_iran.zip", "eamena_khorasan_iran",
     [("08_early_islamic_caliphate", 0.20), ("09_mediaeval_seljuk_mamluk_timurid", 0.35), ("10_early_modern_ottoman_safavid_qajar", 0.45)]),
    ("egypt_wadi_naqqat_monastic_heritage_places_in_wadi_naqqat_eastern_desert_egypt.zip", "eamena_wadi_naqqat_egypt",
     [("07_late_antiquity_sassanid_byzantine", 0.65), ("08_early_islamic_caliphate", 0.35)]),
    ("eamena_gaza_destruction_of_the_culturalarchaeological_landscape_in_the_gaza_strip.zip", "eamena_gaza_levant",
     [("06_roman_parthian_kushan", 0.25), ("07_late_antiquity_sassanid_byzantine", 0.25), ("09_mediaeval_seljuk_mamluk_timurid", 0.25), ("10_early_modern_ottoman_safavid_qajar", 0.25)]),
  ]
  for zfn, tag, dpw in zips_spec:
    zp = os.path.join(RAW_DIR, zfn)
    if os.path.exists(zp):
      with zipfile.ZipFile(zp) as zf:
        gns = [n for n in zf.namelist() if n.endswith(".geojson")]
        if gns:
          gj = json.loads(zf.read(gns[0]))
          ingest_geojson_features(gj.get("features", []), tag, dpw, wt=2.0)

  ca2_p = os.path.join(RAW_DIR, "reg_arabia_arch_6862013_CA2_sites_zenodo_DOI6862012.geojson")
  if os.path.exists(ca2_p):
    gj = json.load(open(ca2_p, "r", encoding="utf-8"))
    ingest_geojson_features(gj.get("features", []), "ca2_mena_archaeological_sites",
                            [("03_early_middle_bronze_age", 0.3), ("04_late_bronze_iron_age", 0.4), ("05_achaemenid_hellenistic", 0.3)], wt=2.0)

  # --- REPO 9: UCL CAAL (Afghanistan / Khorasan / Caspian monuments from SARAY cache) ---
  caal_p = os.path.join(SARAY_RAW_DIR, "caal_all_monuments.json")
  if os.path.exists(caal_p):
    caal = json.load(open(caal_p, "r", encoding="utf-8"))
    rows = caal if isinstance(caal, list) else (caal.get("features") or caal.get("results") or [])
    for rec in rows:
      la, lo = None, None
      if isinstance(rec, dict):
        if "lat" in rec and "lon" in rec:
          la, lo = rec.get("lat"), rec.get("lon")
        elif "geometry" in rec and isinstance(rec["geometry"], dict):
          c = rec["geometry"].get("coordinates") or []
          if len(c) >= 2 and isinstance(c[0], (int, float)):
            lo, la = c[0], c[1]
      try:
        la, lo = float(la), float(lo)
      except Exception:
        continue
      if LAT_MIN <= la <= LAT_MAX and LON_MIN <= lo <= LON_MAX:
        pw = [
          ("04_late_bronze_iron_age", 0.15), ("05_achaemenid_hellenistic", 0.15),
          ("06_roman_parthian_kushan", 0.20), ("08_early_islamic_caliphate", 0.25),
          ("09_mediaeval_seljuk_mamluk_timurid", 0.25),
        ]
        records.append((la, lo, 1.8, pw, "ucl_caal_afghanistan_khorasan", True, 0))
        source_stats["ucl_caal_afghanistan_khorasan"] += 1

  # --- REPO 10: Canonical Excavated MENA/Iran/Afghanistan/Caucasus/Maghreb/Arabia Monograph Catalogue ---
  curated = build_curated_handbook_monograph_catalogue()
  records.extend(curated)
  source_stats["handbook_monograph_catalogue"] = len(curated)

  # --- REPO 11: Global Radiocarbon Baseline (`c14_cleaned_dedup.csv`) ---
  if os.path.exists(C14_PATH):
    seen_c14 = set()
    with open(C14_PATH, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        try:
          la = float(row.get("lat") or "")
          lo = float(row.get("lon") or "")
          age = float(row.get("c14age") or "")
        except Exception:
          continue
        if not (LAT_MIN <= la <= LAT_MAX and LON_MIN <= lo <= LON_MAX):
          continue
        yr = int(round(1950.0 - age * 1.07))
        pw = assign_periods_by_span(yr - 150, yr + 150)
        if not pw:
          continue
        sk = (round(la, 3), round(lo, 3), pw[0][0])
        if sk in seen_c14:
          continue
        seen_c14.add(sk)
        records.append((la, lo, 1.5, pw, "c14_cleaned_dedup_global", False, 0))
        source_stats["c14_cleaned_dedup_global"] += 1

  # --- REPO 12: Cross-Frontier Conditioning Belts (POLARIS, SARAY, INDUS, JADE <= 300 km) ---
  def ingest_sibling_domain(gj_dir, period_map, tag, bbox):
    if not os.path.isdir(gj_dir):
      return
    la0, lo0, la1, lo1 = bbox
    for fn, pw in period_map.items():
      fp = os.path.join(gj_dir, fn)
      if not os.path.exists(fp):
        continue
      for feat in json.load(open(fp, "r", encoding="utf-8")).get("features", []):
        coords = (feat.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
          continue
        lo, la = float(coords[0]), float(coords[1])
        if la0 <= la <= la1 and lo0 <= lo <= lo1:
          cnt = float((feat.get("properties") or {}).get("site_count") or (feat.get("properties") or {}).get("value") or 0.0)
          if cnt > 0:
            records.append((la, lo, min(cnt, 18.0), pw, tag, True, 0))
            source_stats[tag] += 1

  ingest_sibling_domain(POLARIS_GJ_DIR, {
    "01_stone_age_e52.geojson": [("01_epipalaeolithic_early_neolithic", 1.0)],
    "02_eneolithic_e13.geojson": [("02_late_neolithic_chalcolithic", 1.0)],
    "05_bronze_age_e47.geojson": [("03_early_middle_bronze_age", 0.55), ("04_late_bronze_iron_age", 0.45)],
    "06_iron_age_e36.geojson": [("04_late_bronze_iron_age", 0.5), ("05_achaemenid_hellenistic", 0.5)],
    "07_classical_antiquity_e6.geojson": [("06_roman_parthian_kushan", 1.0)],
    "08_migration_period_e34.geojson": [("07_late_antiquity_sassanid_byzantine", 0.5), ("08_early_islamic_caliphate", 0.5)],
    "09_middle_ages_e37.geojson": [("09_mediaeval_seljuk_mamluk_timurid", 1.0)],
    "10_early_modern_17_18c_e3.geojson": [("10_early_modern_ottoman_safavid_qajar", 1.0)],
  }, "polaris_caucasus_frontier", (41.0, 36.0, 46.5, 51.0))

  ingest_sibling_domain(SARAY_GJ_DIR, {
    "01_epipalaeolithic_mesolithic_early_neolithic.geojson": [("01_epipalaeolithic_early_neolithic", 0.6), ("02_late_neolithic_chalcolithic", 0.4)],
    "02_chalcolithic_namazga_sarazm_botai.geojson": [("02_late_neolithic_chalcolithic", 0.6), ("03_early_middle_bronze_age", 0.4)],
    "03_bronze_age_bmac_sintashta_andronovo.geojson": [("03_early_middle_bronze_age", 0.6), ("04_late_bronze_iron_age", 0.4)],
    "04_iron_age_saka_achaemenid_hellenistic.geojson": [("04_late_bronze_iron_age", 0.4), ("05_achaemenid_hellenistic", 0.6)],
    "05_kushan_kangju_wusun_parthian_antiquity.geojson": [("06_roman_parthian_kushan", 0.6), ("07_late_antiquity_sassanid_byzantine", 0.4)],
    "06_sogdian_turkic_early_islamic.geojson": [("07_late_antiquity_sassanid_byzantine", 0.3), ("08_early_islamic_caliphate", 0.7)],
    "07_samanid_karakhanid_seljuk_khwarazmshah.geojson": [("08_early_islamic_caliphate", 0.35), ("09_mediaeval_seljuk_mamluk_timurid", 0.65)],
    "08_mongol_chagatai_timurid.geojson": [("09_mediaeval_seljuk_mamluk_timurid", 1.0)],
    "09_uzbek_khanates_kazakh_zhuzes.geojson": [("10_early_modern_ottoman_safavid_qajar", 1.0)],
  }, "saray_central_asia_frontier", (35.0, 52.0, 42.5, 76.0))

  ingest_sibling_domain(INDUS_GJ_DIR, {
    "01_palaeolithic_mesolithic_early_neolithic.geojson": [("01_epipalaeolithic_early_neolithic", 1.0)],
    "02_pre_harappan_chalcolithic_neolithic.geojson": [("02_late_neolithic_chalcolithic", 1.0)],
    "03_mature_late_harappan_bronze_age.geojson": [("03_early_middle_bronze_age", 1.0)],
    "04_vedic_iron_age_mahajanapada.geojson": [("04_late_bronze_iron_age", 1.0)],
    "05_maurya_shunga_satavahana.geojson": [("05_achaemenid_hellenistic", 1.0)],
    "06_kushan_sangam_early_classical.geojson": [("06_roman_parthian_kushan", 1.0)],
    "07_gupta_vakataka_classical_zenith.geojson": [("07_late_antiquity_sassanid_byzantine", 1.0)],
    "08_early_mediaeval_regional_kingdoms.geojson": [("08_early_islamic_caliphate", 1.0)],
    "09_delhi_sultanate_vijayanagara_late_mediaeval.geojson": [("09_mediaeval_seljuk_mamluk_timurid", 1.0)],
    "10_mughal_maratha_early_modern.geojson": [("10_early_modern_ottoman_safavid_qajar", 1.0)],
  }, "indus_pakistan_frontier", (24.0, 60.5, 38.0, 76.0))

  ingest_sibling_domain(JADE_GJ_DIR, {
    "01_palaeolithic_early_neolithic_h1.geojson": [("01_epipalaeolithic_early_neolithic", 1.0)],
    "06_qin_han_xiongnu_h6.geojson": [("06_roman_parthian_kushan", 1.0)],
    "08_sui_tang_five_dynasties_h8.geojson": [("08_early_islamic_caliphate", 1.0)],
    "10_ming_qing_imperial_h10.geojson": [("10_early_modern_ottoman_safavid_qajar", 1.0)],
  }, "jade_xinjiang_frontier", (35.0, 73.0, 40.0, 78.0))

  # Spatial-source deduplication (~1 km per source tag)
  dedup_map = {}
  for la, lo, wt, pw, tag, is_s, mp in records:
    kd = (round(la, 2), round(lo, 2), tag)
    if kd not in dedup_map:
      dedup_map[kd] = [la, lo, wt, list(pw), tag, is_s, mp]
    else:
      dedup_map[kd][2] = min(18.0, dedup_map[kd][2] + wt * 0.30)
      dedup_map[kd][6] = max(dedup_map[kd][6], mp)
  dedup_records = [tuple(v) for v in dedup_map.values()]

  print("\n[C] Multi-Repository Ingestion Breakdown (HANDBOOK):", flush=True)
  for k, v in source_stats.most_common():
    print(f"    {k} ({SOURCE_TIERS.get(k, 'regional')}): {v:,} raw", flush=True)
  print(f"    TOTAL RAW: {len(records):,} | DEDUP SITE-COMPLEXES: {len(dedup_records):,}", flush=True)
  return dedup_records, dict(source_stats)


def aggregate_and_export(domain_mask, land_area, catchments, records, source_stats):
  c_xyz = np.array([c["xyz"] for c in catchments])
  tree = cKDTree(c_xyz)

  # Load Admin-0 polygons for exact per-jurisdiction provenance attribution (`jurisdiction_arch_coverage`)
  ne0 = json.load(open(os.path.join(SHARED_GIS_DIR, "ne_10m_admin_0_countries.geojson"), "r", encoding="utf-8"))
  jur_polys = []
  for f in ne0["features"]:
    adm = (f.get("properties") or {}).get("ADMIN")
    if adm in COUNTRY_TO_JURISDICTION:
      g = shape(f["geometry"]).buffer(0)
      jur_polys.append((COUNTRY_TO_JURISDICTION[adm], adm, prep(g), g.bounds))

  hyde_dir = os.path.join(SVEA_ROOT, "histmap", "2.data_cleaning", "landuse_HYDE", "rasters")
  def decode_f32(p):
    raw = np.asarray(Image.open(p).convert("RGBA"), dtype=np.uint8)
    f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
    return np.where(np.isfinite(f32) & (f32 > 0), f32, 0.0)

  p15 = decode_f32(os.path.join(hyde_dir, "popc_1500AD.png"))
  p10 = decode_f32(os.path.join(hyde_dir, "popc_1000AD.png"))
  hyde_dens = np.maximum(p15, p10) / np.maximum(1.0, land_area.astype(np.float64))

  n_c = len(catchments)
  per_counts = {pk: np.zeros(n_c, dtype=np.float64) for pk in PERIOD_KEYS}
  total_raw = np.zeros(n_c, dtype=np.float64)
  has_sett = np.zeros(n_c, dtype=bool)
  max_pop = np.zeros(n_c, dtype=np.float64)
  doc_pixels = set()
  doc_settlements = []

  dom_source_counts = Counter()
  country_breakdown = Counter()
  jur_cov = {
    jid: {"total_sites": 0, "regional_register_sites": 0, "monograph_sites": 0, "global_c14_sites": 0, "crowd_sites": 0, "regional_sources": set()}
    for jid in ("turkey", "iran", "egypt", "levant_iraq", "arabia", "maghreb", "caucasus_afghanistan")
  }

  rec_xyz = np.array([latlon_to_xyz(r[0], r[1]) for r in records])
  dists, idxs = tree.query(rec_xyz, workers=4)
  dists_km = dists * EARTH_R_KM

  assigned_dom, assigned_fr = 0, 0
  for i, r in enumerate(records):
    if dists_km[i] > 180.0:
      continue
    ci = int(idxs[i])
    la, lo, wt, pw, src_tag, is_s, mp = r
    for pk, frac in pw:
      per_counts[pk][ci] += wt * frac
    total_raw[ci] += wt
    if is_s:
      has_sett[ci] = True
    if mp > max_pop[ci]:
      max_pop[ci] = mp
    rr, cc = latlon_to_rc(la, lo)
    if domain_mask[rr, cc]:
      cr, c_col = latlon_to_rc(catchments[ci]["lat"], catchments[ci]["lon"])
      cos_l = max(0.18, math.cos(math.radians(la)))
      rad_d2 = (rr - cr) ** 2 + ((cc - c_col) * cos_l) ** 2
      # Exclude prehistoric hyper-arid desert kite/hearth scatters (e.g. Western Nafud) from historical habitability mask
      # unless pixel has HYDE agricultural/pastoral carrying capacity OR is a verified historical oasis/settlement
      is_desert_scatter = (src_tag in ("eamena_western_nafud_arabia", "eamena_wadi_naqqat_egypt", "c14_cleaned_dedup_global") and hyde_dens[rr, cc] < 0.002)
      if not is_desert_scatter and (hyde_dens[rr, cc] >= 0.002 or (is_s and rad_d2 <= 16.0)):
        doc_pixels.add(rr * GRID_W + cc)
      assigned_dom += 1
      dom_source_counts[src_tag] += 1

      # Attribute to jurisdiction for Gatekeeper C1 provenance table
      pt = Point(lo, la)
      matched_j, matched_c = None, None
      for jid, cname, pg, bb in jur_polys:
        if bb[0] <= lo <= bb[2] and bb[1] <= la <= bb[3] and pg.contains(pt):
          matched_j, matched_c = jid, cname
          break
      if matched_j:
        country_breakdown[matched_c] += 1
        jd = jur_cov[matched_j]
        jd["total_sites"] += 1
        tier = SOURCE_TIERS.get(src_tag, "national_regional_register")
        if tier == "national_regional_register":
          jd["regional_register_sites"] += 1
          jd["regional_sources"].add(src_tag)
        elif tier == "academic_monograph_table":
          jd["monograph_sites"] += 1
          jd["regional_sources"].add(src_tag)
        elif tier == "global_radiocarbon":
          jd["global_c14_sites"] += 1
        else:
          jd["crowd_sites"] += 1
    else:
      assigned_fr += 1

  # Populate documented_settlements.json with real multi-epoch time-series (`series: [[yr, pop], ...]`)
  # from HANDBOOK chapter settlement gazetteers + canonical archaeological/historical capitals
  sett_merged = {}
  for root_d, _dirs, files in os.walk(HB_DIR):
    for fn in files:
      if fn.endswith("_settlements.json") and "_shared" not in root_d:
        try:
          obj = json.load(open(os.path.join(root_d, fn), "r", encoding="utf-8"))
        except Exception:
          continue
        for s in (obj.get("settlements") or []):
          try:
            sla, slo = float(s["lat"]), float(s["lon"])
          except Exception:
            continue
          rr_s, cc_s = latlon_to_rc(sla, slo)
          if not domain_mask[rr_s, cc_s]:
            continue
          pts = []
          pop_obj = s.get("population") or {}
          if isinstance(pop_obj, dict):
            for yk, pv in pop_obj.items():
              try:
                yr_i = int(float(yk))
                pv_i = int(round(float(pv)))
                if pv_i > 0:
                  pts.append((yr_i, pv_i))
              except Exception:
                continue
          if not pts:
            continue
          skey = (round(sla * 25) / 25.0, round(slo * 25) / 25.0)
          entry = sett_merged.setdefault(skey, {"lat": sla, "lon": slo, "pts": {}})
          for yr_i, pv_i in pts:
            if yr_i not in entry["pts"] or pv_i > entry["pts"][yr_i]:
              entry["pts"][yr_i] = pv_i

  # Also add canonical archaeological/historical capitals with chronological trajectories across [start_yr, end_yr]
  for la, lo, wt, pw, src_tag, is_s, mp in build_curated_handbook_monograph_catalogue():
    if mp < 1000:
      continue
    rr_s, cc_s = latlon_to_rc(la, lo)
    if not domain_mask[rr_s, cc_s]:
      continue
    skey = (round(la * 25) / 25.0, round(lo * 25) / 25.0)
    entry = sett_merged.setdefault(skey, {"lat": la, "lon": lo, "pts": {}})
    for pk, _frac in pw:
      p_obj = next((p for p in PERIODS if p["key"] == pk), None)
      if p_obj:
        ry = p_obj["representative_year"]
        est_p = int(round(max(1200.0, mp * 0.65)))
        if ry not in entry["pts"] or est_p > entry["pts"][ry]:
          entry["pts"][ry] = est_p

  doc_settlements = []
  for skey, entry in sett_merged.items():
    sorted_pts = sorted(entry["pts"].items())
    if not sorted_pts:
      continue
    min_yr = sorted_pts[0][0]
    max_p = max(v for _, v in sorted_pts)
    doc_settlements.append({
      "lat": round(entry["lat"], 4),
      "lon": round(entry["lon"], 4),
      "min_year": int(min_yr),
      "max_pop": int(max_p),
      "series": [[int(y), int(v)] for y, v in sorted_pts],
    })

  # Biome/Aridity-conditioned Q75 + IQR taphonomic outlier shrinkage (NO redundant B2 smoothing!)
  dom_mask_c = np.array([not c["is_frontier_buffer"] for c in catchments], dtype=bool)
  c_areas = np.array([c["area_km2"] for c in catchments], dtype=np.float64)
  c_hyde = np.array([hyde_dens[latlon_to_rc(c["lat"], c["lon"])] for c in catchments], dtype=np.float64)
  is_arid = c_hyde < 2.5

  for pk in PERIOD_KEYS:
    vals = per_counts[pk]
    dens = vals / np.maximum(150.0, c_areas)
    for grp_mask, cap_mult in [(dom_mask_c & is_arid, 1.5), (dom_mask_c & (~is_arid), 2.8)]:
      pos = dens[grp_mask & (dens > 0)]
      if pos.size >= 15:
        q25, q75 = np.percentile(pos, [25, 75])
        iqr = max(1e-7, q75 - q25)
        cap = q75 + cap_mult * iqr
        excess = grp_mask & (dens > cap)
        if excess.any():
          shrunk = cap + iqr * np.log1p((dens[excess] - cap) / iqr)
          vals[excess] = shrunk * np.maximum(150.0, c_areas[excess])
    per_counts[pk] = vals

  period_meta = []
  for p in PERIODS:
    pk = p["key"]
    feats = []
    dom_sum, dom_active = 0.0, 0
    for ci, c in enumerate(catchments):
      cnt = float(per_counts[pk][ci])
      if not c["is_frontier_buffer"]:
        dom_sum += cnt
        if cnt > 0:
          dom_active += 1
      feats.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [round(c["lon"], 5), round(c["lat"], 5)]},
        "properties": {
          "region_id": c["region_id"], "area_km2": c["area_km2"],
          "site_count": round(cnt, 3), "total_sites_all_periods": round(float(total_raw[ci]), 2),
          "is_frontier_buffer": c["is_frontier_buffer"], "has_documented_settlement": bool(has_sett[ci]),
          "max_settlement_pop": int(max_pop[ci]), "period_key": pk,
        },
      })
    with open(os.path.join(GJ_DIR, p["geojson_filename"]), "w", encoding="utf-8") as fh:
      json.dump({"type": "FeatureCollection", "features": feats}, fh)
    period_meta.append({
      "key": pk, "geojson_filename": p["geojson_filename"],
      "total_sites_count": int(round(dom_sum)), "active_domestic_catchments": dom_active,
    })
    print(f"  Exported {p['geojson_filename']}: dom_weighted={dom_sum:,.1f} | active_dom={dom_active}/{int(dom_mask_c.sum())}", flush=True)

  all_feats = []
  for ci, c in enumerate(catchments):
    all_feats.append({
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [round(c["lon"], 5), round(c["lat"], 5)]},
      "properties": {
        "region_id": c["region_id"], "area_km2": c["area_km2"],
        "site_count": round(float(total_raw[ci]), 2), "total_sites_all_periods": round(float(total_raw[ci]), 2),
        "is_frontier_buffer": c["is_frontier_buffer"], "has_documented_settlement": bool(has_sett[ci]),
        "max_settlement_pop": int(max_pop[ci]),
      },
    })
  with open(os.path.join(GJ_DIR, "00_all_periods.geojson"), "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": all_feats}, fh)

  with open(os.path.join(CFG_DIR, "documented_site_pixels.json"), "w", encoding="utf-8") as fh:
    json.dump({"grid_width": GRID_W, "grid_height": GRID_H, "pixel_indices": sorted(doc_pixels)}, fh)

  with open(os.path.join(CFG_DIR, "documented_settlements.json"), "w", encoding="utf-8") as fh:
    json.dump({"count": len(doc_settlements), "settlements": doc_settlements}, fh)

  # Serialise Gatekeeper C1 provenance breakdown & per-jurisdiction coverage
  prov_breakdown = {
    k: {"count": int(v), "source_tier": SOURCE_TIERS.get(k, "national_regional_register")}
    for k, v in dom_source_counts.most_common()
  }
  jur_cov_out = {}
  print("\n[D] Per-Jurisdiction Archaeological Provenance Coverage (HANDBOOK):", flush=True)
  for jid, jd in jur_cov.items():
    jur_cov_out[jid] = {
      "total_sites": jd["total_sites"],
      "regional_register_sites": jd["regional_register_sites"],
      "monograph_sites": jd["monograph_sites"],
      "global_c14_sites": jd["global_c14_sites"],
      "crowd_sites": jd["crowd_sites"],
      "regional_sources": sorted(jd["regional_sources"]),
    }
    print(f"    {jid:22s}: total={jd['total_sites']:6,d} | reg={jd['regional_register_sites']:6,d} | mono={jd['monograph_sites']:6,d} | c14={jd['global_c14_sites']:4,d} | crowd={jd['crowd_sites']} | srcs={len(jd['regional_sources'])}", flush=True)

  meta_obj = {
    "domain": "HANDBOOK",
    "macro_scope": "North Africa, Near East, Anatolia, Cyprus, Transcaucasia, Iran, Afghanistan and Arabian Peninsula",
    "sources": list(dom_source_counts.keys()),
    "source_record_counts": source_stats,
    "source_provenance_breakdown": prov_breakdown,
    "jurisdiction_arch_coverage": jur_cov_out,
    "country_breakdown": dict(country_breakdown.most_common()),
    "domestic_assigned_records": assigned_dom,
    "frontier_assigned_records": assigned_fr,
    "catchment_counts": {"domestic": int(dom_mask_c.sum()), "frontier_buffer": int((~dom_mask_c).sum())},
    "documented_site_pixels": len(doc_pixels),
    "period_geojsons": period_meta,
  }
  with open(os.path.join(CFG_DIR, "sites_handbook_mena_geojson_metadata.json"), "w", encoding="utf-8") as fh:
    json.dump(meta_obj, fh, indent=2, ensure_ascii=False)

  # Update target_domestic_catchments in sites_handbook_mena.json5
  cfg_p = os.path.join(CFG_DIR, "sites_handbook_mena.json5")
  if os.path.exists(cfg_p):
    cfg = json.load(open(cfg_p, "r", encoding="utf-8"))
    cfg["kriging_config"]["target_domestic_catchments"] = int(dom_mask_c.sum())
    with open(cfg_p, "w", encoding="utf-8") as fh:
      json.dump(cfg, fh, indent=2, ensure_ascii=False)

  print(f"\n[E] Completed HANDBOOK extraction: {assigned_dom:,} domestic + {assigned_fr:,} frontier records across {len(doc_pixels):,} documented pixels.", flush=True)


if __name__ == "__main__":
  dm_raw = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  domain_mask = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)
  la_raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  land_area = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2])
  hyde_dir = os.path.join(SVEA_ROOT, "histmap", "2.data_cleaning", "landuse_HYDE", "rasters")
  def _dec_f32(p):
    raw = np.asarray(Image.open(p).convert("RGBA"), dtype=np.uint8)
    f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
    return np.where(np.isfinite(f32) & (f32 > 0), f32, 0.0)
  hyde_dens_init = np.maximum(
    _dec_f32(os.path.join(hyde_dir, "popc_1500AD.png")),
    _dec_f32(os.path.join(hyde_dir, "popc_1000AD.png")),
  ) / np.maximum(1.0, land_area.astype(np.float64))
  catchments = build_catchments(domain_mask, land_area, hyde_dens_init)
  records, source_stats = ingest_all_repositories()
  aggregate_and_export(domain_mask, land_area, catchments, records, source_stats)
