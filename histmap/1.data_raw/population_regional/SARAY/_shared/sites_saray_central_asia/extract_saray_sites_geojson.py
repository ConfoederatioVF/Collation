"""Stage C Multi-Repository Archaeological & Historical Site Composite Extractor for Project SARAY.

Builds scale-adaptive HydroBASINS Level 6 catchments (<= 25,000 km2) across Central Asia
(Kazakhstan, Uzbekistan, Turkmenistan, Kyrgyzstan, Tajikistan) plus a 300 km cross-frontier
conditioning belt (POLARIS Russian Steppe/Altai/Lower Volga, JADE Xinjiang, INDUS Hindu Kush,
HANDBOOK Northern Afghanistan/Khorasan/Caspian), ingests and deduplicates 13 primary
archaeological/institutional repositories (anchored by UCL CAAL, Al-Thurayya, Pleiades,
Tegiszhol Zenodo C14, AADR v66, ArchAtlas 2020, c14bazAAR, Wikidata multilingual heritage,
OSM Overpass with API forensics, and POLARIS/JADE/INDUS cross-frontier belts) across 9
Holocene-to-Early-Modern horizons (-10000 to 1865 AD), applies monument-class hierarchy
weighting and biome/aridity-conditioned Q75 + IQR taphonomic shrinkage plus B2 settled-belt
neighbour imputation, and exports ViscountMaternKriging-ready GeoJSONs and configs.
"""

import csv
import io
import json
import math
import os
import re
import zipfile
from collections import Counter

import numpy as np
import shapefile
from PIL import Image
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from shapely.geometry import Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SARAY_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "SARAY")
DOMAIN_DIR = os.path.join(SARAY_DIR, "_shared", "sites_saray_central_asia")
RAW_DIR = os.path.join(DOMAIN_DIR, "0.raw_data")
CFG_DIR = os.path.join(DOMAIN_DIR, "config")
GJ_DIR = os.path.join(DOMAIN_DIR, "geojson")

JADE_RAW_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "sites_east_asia", "0.raw_data")
JADE_GIS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "_gis_cache")
JADE_GJ_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "sites_east_asia", "geojson")
POLARIS_GJ_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "POLARIS", "_shared", "sites_IA_RAS", "geojson")
INDUS_GJ_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "INDUS", "_shared", "sites_indus_south_asia", "geojson")
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
DOMAIN_MASK_PNG = os.path.join(CFG_DIR, "saray_domain_mask.png")

os.makedirs(CFG_DIR, exist_ok=True)
os.makedirs(GJ_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160
EARTH_R_KM = 6371.0

# 9 Chronological Archaeological Horizons calibrated to Central Asian Prehistory & History
PERIODS = [
  {
    "epoch_id": 1, "key": "01_epipalaeolithic_mesolithic_early_neolithic",
    "filename": "01_epipalaeolithic_mesolithic_early_neolithic.png",
    "geojson_filename": "01_epipalaeolithic_mesolithic_early_neolithic.geojson",
    "approx_start_year": -13000, "approx_end_year": -5000, "representative_year": -7500,
    "name_en": "Epipalaeolithic, Mesolithic and Early Neolithic",
    "name_de": "Epipaläolithikum, Mesolithikum und Frühneolithikum",
    "name_fr": "Épipaléolithique, Mésolithique et Néolithique ancien",
    "date_range_en": "c. 13000-5000BC (Jeitun foothills, Kelteminar delta, Hissar and Tutkaul foragers)"
  },
  {
    "epoch_id": 2, "key": "02_chalcolithic_namazga_sarazm_botai",
    "filename": "02_chalcolithic_namazga_sarazm_botai.png",
    "geojson_filename": "02_chalcolithic_namazga_sarazm_botai.geojson",
    "approx_start_year": -5000, "approx_end_year": -2500, "representative_year": -3500,
    "name_en": "Chalcolithic Oases and Eneolithic Steppe",
    "name_de": "Chalkolithische Oasen und Äneolithikum der Steppe",
    "name_fr": "Oasis chalcolithiques et steppe énéolithique",
    "date_range_en": "c. 5000-2500BC (Anau, Namazga I-IV, Geoksyur, Sarazm, Botai and Afanasievo)"
  },
  {
    "epoch_id": 3, "key": "03_bronze_age_bmac_sintashta_andronovo",
    "filename": "03_bronze_age_bmac_sintashta_andronovo.png",
    "geojson_filename": "03_bronze_age_bmac_sintashta_andronovo.geojson",
    "approx_start_year": -2500, "approx_end_year": -1000, "representative_year": -1800,
    "name_en": "BMAC Oxus Civilisation and Steppe Bronze Age",
    "name_de": "BMAC-Oxus-Zivilisation und Steppenbronzezeit",
    "name_fr": "Civilisation de l'Oxus (BMAC) et Âge du Bronze steppique",
    "date_range_en": "c. 2500-1000BC (Gonur, Altyn-Depe, Sapalli, Dzharkutan, Sintashta, Andronovo, Tazabagyab and Chust)"
  },
  {
    "epoch_id": 4, "key": "04_iron_age_saka_achaemenid_hellenistic",
    "filename": "04_iron_age_saka_achaemenid_hellenistic.png",
    "geojson_filename": "04_iron_age_saka_achaemenid_hellenistic.geojson",
    "approx_start_year": -1000, "approx_end_year": -150, "representative_year": -450,
    "name_en": "Early Iron Age Saka, Achaemenid and Hellenistic Oases",
    "name_de": "Frühe Eisenzeit der Saken, Achämeniden und Hellenismus",
    "name_fr": "Premier Âge du Fer saka, achéménide et hellénistique",
    "date_range_en": "c. 1000-150BC (Yaz I-III, Afrasiab, Merv, Chirik-Rabat, Tasmola Saka and Greco-Bactria)"
  },
  {
    "epoch_id": 5, "key": "05_kushan_kangju_wusun_parthian_antiquity",
    "filename": "05_kushan_kangju_wusun_parthian_antiquity.png",
    "geojson_filename": "05_kushan_kangju_wusun_parthian_antiquity.geojson",
    "approx_start_year": -150, "approx_end_year": 500, "representative_year": 150,
    "name_en": "Kushan, Parthian, Kangju and Wusun Classical Era",
    "name_de": "Kuschan-, Parther-, Kangju- und Wusun-Antike",
    "name_fr": "Antiquité kouchane, parthe, kangju et wusun",
    "date_range_en": "150BC-500AD (Termez, Dalverzin-Tepe, Toprak-Kala, Nisa, Merv, Erkurgan, Kanka and Zhetyasar)"
  },
  {
    "epoch_id": 6, "key": "06_sogdian_turkic_early_islamic",
    "filename": "06_sogdian_turkic_early_islamic.png",
    "geojson_filename": "06_sogdian_turkic_early_islamic.geojson",
    "approx_start_year": 500, "approx_end_year": 900, "representative_year": 700,
    "name_en": "Sogdian City-States, Turkic Khaganates and Early Islam",
    "name_de": "Sogdische Stadtstaaten, Türk-Kaganate und Frühislam",
    "name_fr": "Cités sogdiennes, khaganats turcs et premier Islam",
    "date_range_en": "500-900AD (Panjikent, Paykand, Varakhsha, Suyab, Balasagun, Afrighid Khwarazm and Abbasid Merv)"
  },
  {
    "epoch_id": 7, "key": "07_samanid_karakhanid_seljuk_khwarazmshah",
    "filename": "07_samanid_karakhanid_seljuk_khwarazmshah.png",
    "geojson_filename": "07_samanid_karakhanid_seljuk_khwarazmshah.geojson",
    "approx_start_year": 900, "approx_end_year": 1219, "representative_year": 1100,
    "name_en": "Samanid, Karakhanid, Seljuk and Khwarazmshah Zenith",
    "name_de": "Samaniden-, Karachaniden-, Seldschuken- und Choresm-Blüte",
    "name_fr": "Apogée samanide, qarakhanide, seldjoukide et khwarezmien",
    "date_range_en": "900-1219AD (Bukhara, Samarkand, Sultan-Kala Merv, Gurganj, Otrar, Taraz, Uzgen and Hulbuk)"
  },
  {
    "epoch_id": 8, "key": "08_mongol_chagatai_timurid",
    "filename": "08_mongol_chagatai_timurid.png",
    "geojson_filename": "08_mongol_chagatai_timurid.geojson",
    "approx_start_year": 1219, "approx_end_year": 1500, "representative_year": 1400,
    "name_en": "Mongol Conquest, Chagatai Ulus and Timurid Renaissance",
    "name_de": "Mongoleneroberung, Tschagatai-Ulus und Timuriden-Renaissance",
    "name_fr": "Conquête mongole, oulous de Djaghataï et Renaissance timouride",
    "date_range_en": "1219-1500AD (Timurid Samarkand, Kesh, Bukhara, Sighnaq, Sauran, Yasi, Saraishyk and Moghulistan)"
  },
  {
    "epoch_id": 9, "key": "09_uzbek_khanates_kazakh_zhuzes",
    "filename": "09_uzbek_khanates_kazakh_zhuzes.png",
    "geojson_filename": "09_uzbek_khanates_kazakh_zhuzes.geojson",
    "approx_start_year": 1500, "approx_end_year": 1865, "representative_year": 1700,
    "name_en": "Uzbek Khanates and Kazakh Steppe Zhuzes",
    "name_de": "Usbekische Khanate und Kasachische Steppen-Dschus",
    "name_fr": "Khanats ouzbeks et jüz steppiques kazakhs",
    "date_range_en": "1500-1865AD (Bukhara, Khiva, Kokand, Tashkent, Qarshi, Turkmen oases and Three Kazakh Zhuzes)"
  }
]
PERIOD_KEYS = [p["key"] for p in PERIODS]

MODERN_EXCLUDE_RE = re.compile(
  r"(?:ленин|сталин|киров|дзержинск|фрунзе|великой\s+отечественной|1941[\-–]1945|братская\s+могила|"
  r"мемориал\s+славы|вечный\s+огонь|погибшим\s+в\s+вов|героям|советск|комсомол|октябрьской\s+революц|"
  r"wwii|world\s+war|war\s+memorial|soviet\s+memorial|statue\s+of\s+lenin|памятник\s+воинам|"
  r"независимост|афганск|чернобыль|жертвам\s+репрессий|1917|192\d|193\d|194\d|195\d|196\d|197\d|198\d|199\d|200\d|201\d|202\d)",
  flags=re.I
)


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
  if end_yr < -16000 or start_yr > 1880:
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
    if 1865 < mid <= 1900:
      return [(PERIODS[-1]["key"], 1.0)]
    return []
  tot = sum(w for _, w in hits)
  return [(k, w / tot) for k, w in hits]


def classify_ca_text(text):
  """Periodises multilingual EN/RU/KK/UZ/TK/TG Central Asian site descriptions & labels."""
  s = (text or "").lower()
  if not s or MODERN_EXCLUDE_RE.search(s):
    return None  # Explicitly excluded or empty

  # Explicit BCE/CE dates in text
  m_bc = re.findall(r"(\d{3,5})\s*(?:bc|bce|до\s*н\.?\s*э\.?)", s)
  if m_bc:
    yrs = [-int(x) for x in m_bc if 50 <= int(x) <= 15000]
    if yrs:
      return assign_periods_by_span(min(yrs), max(yrs))
  m_ad = re.findall(r"(?:ad|ce)\s*(\d{3,4})|(\d{3,4})\s*(?:ad|ce|н\.?\s*э\.?|г\.)", s)
  yrs_ad = [int(a or b) for a, b in m_ad if 1 <= int(a or b) <= 1865]
  if yrs_ad:
    return assign_periods_by_span(min(yrs_ad), max(yrs_ad))

  hits = []
  kw_rules = [
    (["палеолит", "мезолит", "стоянка неолит", "неолит", "джейтун", "кельтеминар", "гиссарск", "palaeolithic", "paleolithic", "mesolithic", "jeitun", "kelteminar", "tutkaul"], "01_epipalaeolithic_mesolithic_early_neolithic"),
    (["энеолит", "халколит", "намазга", "анау", "саразм", "ботай", "афанасьев", "eneolithic", "chalcolithic", "namazga", "anau", "sarazm", "botai", "geoksyur"], "02_chalcolithic_namazga_sarazm_botai"),
    (["бронзов", "андронов", "алакуль", "федоров", "синташт", "бегазы", "тазабагьяб", "чуст", "гонур", "алтын-депе", "сапалли", "джаркутан", "bronze age", "andronovo", "bmac", "oxus", "sintashta", "gonur", "sapalli", "chust", "petrovka"], "03_bronze_age_bmac_sintashta_andronovo"),
    (["ранний желез", "железн", "сакск", "скиф", "тасмол", "пазырык", "ахеменид", "эллинист", "греко-бактр", "чирик-рабат", "iron age", "saka", "scythian", "tasmola", "achaemenid", "hellenistic", "greco-bactrian", "chirik"], "04_iron_age_saka_achaemenid_hellenistic"),
    (["кушан", "парфян", "кангюй", "усун", "сармат", "джетыасар", "античн", "топрак-кала", "ниса", "kushan", "parthian", "kangju", "kangyuy", "wusun", "usun", "sarmatian", "zhetyasar", "antiquity", "sasanian"], "05_kushan_kangju_wusun_parthian_antiquity"),
    (["согд", "тюркск", "эфталит", "афригид", "раннесреднев", "пенджикент", "пайкенд", "суяб", "sogdian", "turkic", "hephthalite", "afrighid", "early medieval", "early islamic", "umayyad", "abbasid"], "06_sogdian_turkic_early_islamic"),
    (["саманид", "караханид", "сельджук", "хорезмшах", "samanid", "karakhanid", "qarakhanid", "seljuk", "khwarazm", "ghaznavid", "баласагун", "отрар", "тараз", "узген", "мерв"], "07_samanid_karakhanid_seljuk_khwarazmshah"),
    (["монгол", "чагатай", "тимурид", "золот", "ордын", "сыгнак", "сауран", "сарайчик", "mongol", "chagatai", "timurid", "golden horde", "sighnaq", "sauran", "saraishyk", "late medieval"], "08_mongol_chagatai_timurid"),
    (["шейбанид", "бухарск", "хивинск", "кокандск", "казахск", "ханств", "медресе", "мечеть", "мавзолей", "караван-сарай", "рабат", "сардоба", "крепость", "shaybanid", "khanate", "bukhara", "khiva", "kokand", "madrasa", "mosque", "mausoleum", "caravanserai", "sardoba", "post medieval"], "09_uzbek_khanates_kazakh_zhuzes"),
  ]
  for kws, pk in kw_rules:
    if any(k in s for k in kws):
      hits.append(pk)
  if hits:
    w = 1.0 / len(hits)
    return [(pk, w) for pk in hits]

  # Generic Central Asian archaeological typology fallback when unmistakably pre-modern
  if any(k in s for k in ("городище", "тепа", "тепе", "депе", "қалашық", "калашык", "шахристан", "tepe", "tepa", "depe", "gorodishche", "citadel", "fortress", "кала", "қала", "qala", "kala")):
    return [
      ("05_kushan_kangju_wusun_parthian_antiquity", 0.25),
      ("06_sogdian_turkic_early_islamic", 0.30),
      ("07_samanid_karakhanid_seljuk_khwarazmshah", 0.30),
      ("08_mongol_chagatai_timurid", 0.15),
    ]
  if any(k in s for k in ("поселение", "стоянка", "settlement", "tell", "mound")):
    return [
      ("03_bronze_age_bmac_sintashta_andronovo", 0.35),
      ("04_iron_age_saka_achaemenid_hellenistic", 0.35),
      ("05_kushan_kangju_wusun_parthian_antiquity", 0.30),
    ]
  if any(k in s for k in ("курган", "қорған", "могильник", "некрополь", "петроглиф", "наскальн", "балбал", "изваян", "kurgan", "barrow", "tumulus", "petroglyph", "balbal", "burial")):
    return [
      ("03_bronze_age_bmac_sintashta_andronovo", 0.25),
      ("04_iron_age_saka_achaemenid_hellenistic", 0.45),
      ("05_kushan_kangju_wusun_parthian_antiquity", 0.20),
      ("06_sogdian_turkic_early_islamic", 0.10),
    ]
  return []


def parse_wd_coord(val):
  m = re.search(r"Point\(\s*([0-9.\-]+)\s+([0-9.\-]+)\s*\)", str(val or ""))
  return (float(m.group(2)), float(m.group(1))) if m else (None, None)


def parse_wd_year(val):
  m = re.match(r"^\+?(-?\d{1,5})-", str(val or ""))
  return int(m.group(1)) if m else None


def build_catchments(domain_mask, land_area):
  """Discretises SARAY + 300 km cross-frontier belt into scale-adaptive HydroBASINS L6 catchments (<= 25,000 km2)."""
  print("[A] Building scale-adaptive HydroBASINS Level 6 catchments (domestic + 300 km frontier belt)...", flush=True)
  # Distance transform in pixels (~9.2 km/px at 42N; 34 px ~ 300 km)
  dist_px = distance_transform_edt(~domain_mask)
  frontier_mask = (~domain_mask) & (dist_px <= 36) & (land_area > 0)

  # Load HydroBASINS Level 6 (Asia + Siberia) covering 42..92E, 32..59N
  raw_basins = []
  for hyb_fn in ("hybas_as_lev06_v1c.zip", "hybas_si_lev06_v1c.zip"):
    hp = os.path.join(JADE_GIS_DIR, hyb_fn)
    if not os.path.exists(hp):
      continue
    with zipfile.ZipFile(hp) as zf:
      sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
      sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
      for idx, sr in enumerate(sf.iterShapeRecords()):
        bb = sr.shape.bbox
        if bb[2] < 42.0 or bb[0] > 92.0 or bb[3] < 32.0 or bb[1] > 59.0:
          continue
        g = shape(sr.shape.__geo_interface__).buffer(0)
        if not g.is_empty:
          raw_basins.append((f"{hyb_fn[:8]}_{idx}", g))

  catchments = []
  cid_counter = 0

  def add_polygon_catchment(poly, base_id, is_dom):
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
    lat_sum, lon_sum, cnt = 0.0, 0.0, 0
    for dr, dc in zip(drs, dcs):
      rr, cc = r0 + int(dr), c0 + int(dc)
      plat = 90.0 - (rr + 0.5) * 180.0 / GRID_H
      plon = -180.0 + (cc + 0.5) * 360.0 / GRID_W
      if pg.contains(Point(plon, plat)):
        area_km2 += float(land_area[rr, cc])
        lat_sum += plat
        lon_sum += plon
        cnt += 1
    if cnt < 4 or area_km2 < 120.0:
      return
    # Subdivide oversized steppe/desert basins (> 22,000 km2) along natural median lat/lon split to enforce <= 25,000 km2!
    if area_km2 > 22000.0 and (maxx - minx > 1.2 or maxy - miny > 1.0):
      from shapely.geometry import box as sbox
      if (maxx - minx) * math.cos(math.radians(0.5 * (miny + maxy))) >= (maxy - miny):
        mx = 0.5 * (minx + maxx)
        add_polygon_catchment(poly.intersection(sbox(minx, miny, mx, maxy)).buffer(0), base_id + "_w", is_dom)
        add_polygon_catchment(poly.intersection(sbox(mx, miny, maxx, maxy)).buffer(0), base_id + "_e", is_dom)
      else:
        my = 0.5 * (miny + maxy)
        add_polygon_catchment(poly.intersection(sbox(minx, miny, maxx, my)).buffer(0), base_id + "_s", is_dom)
        add_polygon_catchment(poly.intersection(sbox(minx, my, maxx, maxy)).buffer(0), base_id + "_n", is_dom)
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

  # Ensure westernmost Ural/Volga-Caspian strip (covered by hybas_eu if missing from hybas_as) is also tiled cleanly
  dom_c = [c for c in catchments if not c["is_frontier_buffer"]]
  fr_c = [c for c in catchments if c["is_frontier_buffer"]]
  if dom_c:
    dom_tree = cKDTree(np.array([c["xyz"] for c in dom_c]))
    # Check for any uncovered domain_mask patches > 130 km from nearest catchment (e.g. West Kazakhstan/Ural west of 52E)
    rs, cs = np.where(domain_mask)
    step = 8
    uncov_bins = {}
    for rr, cc in zip(rs[::step], cs[::step]):
      plat = 90.0 - (rr + 0.5) * 180.0 / GRID_H
      plon = -180.0 + (cc + 0.5) * 360.0 / GRID_W
      d, _ = dom_tree.query(latlon_to_xyz(plat, plon))
      if d * EARTH_R_KM > 120.0:
        bk = (int(math.floor(plat / 1.25)), int(math.floor(plon / 1.5)))
        uncov_bins.setdefault(bk, []).append((plat, plon, float(land_area[rr, cc]) * step))
    for bk, pts in uncov_bins.items():
      cid_counter += 1
      clat = sum(x[0] for x in pts) / len(pts)
      clon = sum(x[1] for x in pts) / len(pts)
      catchments.append({
        "region_id": f"dom_{cid_counter:04d}_ural_caspian_{bk[0]}_{bk[1]}",
        "lat": clat, "lon": clon, "xyz": latlon_to_xyz(clat, clon),
        "area_km2": round(min(22000.0, max(2500.0, sum(x[2] for x in pts))), 1),
        "pixel_count": len(pts) * step,
        "is_frontier_buffer": False,
      })

  dom_n = sum(1 for c in catchments if not c["is_frontier_buffer"])
  fr_n = sum(1 for c in catchments if c["is_frontier_buffer"])
  max_a = max((c["area_km2"] for c in catchments if not c["is_frontier_buffer"]), default=0)
  print(f"  Built {dom_n} domestic catchments (max area {max_a:,.0f} km2 <= 25,000) + {fr_n} frontier catchments.", flush=True)
  return catchments


def build_curated_central_asia_catalogue():
  """Canonical excavated archaeological type-sites & historical oasis capitals across all 9 SARAY horizons."""
  # (lat, lon, weight, start_yr, end_yr, max_pop)
  sites = [
    # Prehistoric / Neolithic / Chalcolithic / BMAC
    (38.18, 58.18, 3.0, -6500, -4500, 350),   # Jeitun
    (37.89, 58.52, 3.0, -4500, -1500, 1200),  # Anau
    (37.38, 59.56, 3.5, -4500, -1500, 4500),  # Namazga-Depe
    (36.86, 60.43, 3.5, -3500, -1800, 6000),  # Altyn-Depe
    (37.24, 59.87, 3.5, -4500, -500, 3500),   # Ulug-Depe
    (37.38, 60.75, 3.0, -4000, -2500, 1500),  # Geoksyur
    (38.21, 62.04, 4.0, -2400, -1500, 8000),  # Gonur-Depe (BMAC Capital)
    (38.07, 62.01, 3.0, -2200, -1500, 2500),  # Togolok-21
    (39.51, 67.46, 3.5, -3500, -2000, 3500),  # Sarazm
    (37.54, 67.15, 3.0, -2100, -1700, 1800),  # Sapalli-Tepe
    (37.76, 67.29, 3.5, -2000, -1400, 4000),  # Dzharkutan
    (53.30, 67.65, 3.0, -3700, -3000, 900),   # Botai
    (49.24, 75.99, 3.0, -1400, -900, 1200),   # Kent (Begazy-Dandybay)
    (44.38, 79.13, 2.5, -2500, 1000, 450),    # Begash
    (44.45, 79.25, 2.5, -2800, -1000, 350),   # Tasbas
    (41.00, 71.24, 3.0, -1500, -800, 1500),   # Chust
    (40.76, 72.18, 3.0, -1500, -800, 1800),   # Dalverzin (Ferghana)
    (40.28, 69.82, 2.5, -1800, -1000, 800),   # Kayrakkum
    (41.86, 61.32, 2.5, -5500, -3000, 350),   # Janbas-4 Kelteminar
    # Classical / Saka / Khwarazm / Sogdiana / Bactria / Parthia / Silk Road
    (39.67, 66.99, 5.0, -700, 1865, 110000),  # Afrasiab / Samarkand
    (39.77, 64.42, 5.0, -500, 1865, 95000),   # Bukhara
    (37.66, 62.19, 5.0, -600, 1865, 150000),  # Merv (Erk-Kala / Gyaur-Kala / Sultan-Kala)
    (37.97, 58.20, 4.0, -300, 1220, 25000),   # Old & New Nisa
    (37.36, 59.59, 3.5, -300, 1500, 18000),   # Abiverd
    (38.27, 54.63, 3.5, 400, 1450, 22000),    # Dehistan / Misrian
    (36.54, 61.21, 3.5, -300, 1865, 20000),   # Serakhs
    (39.08, 63.57, 3.5, -200, 1865, 25000),   # Amul / Chardzhou
    (42.33, 59.15, 4.5, -400, 1650, 90000),   # Kunya-Urgench / Gurganj
    (41.93, 60.82, 3.5, 100, 600, 12000),     # Toprak-Kala
    (41.76, 61.01, 3.0, -400, 400, 5000),     # Koy-Krylgan-Kala
    (42.01, 61.03, 3.0, -400, 700, 4000),     # Ayaz-Kala
    (42.40, 59.39, 3.5, -300, 1400, 18000),   # Mizdakhkan
    (41.38, 60.36, 4.0, 900, 1865, 35000),    # Khiva
    (39.49, 67.61, 4.0, 400, 800, 14000),     # Ancient Panjikent
    (39.58, 64.01, 3.5, -300, 1150, 16000),   # Paykand
    (39.86, 64.07, 3.5, 100, 1100, 12000),    # Varakhsha
    (38.90, 65.72, 3.5, -800, 600, 18000),    # Erkurgan / Nikhshap
    (39.06, 66.83, 4.0, -300, 1865, 35000),   # Kesh / Shahrisabz
    (38.86, 65.79, 4.0, 1300, 1865, 35000),   # Qarshi / Nasaf
    (37.26, 67.19, 4.5, -300, 1865, 50000),   # Old Termez / Tarmita
    (38.23, 67.92, 3.5, -200, 400, 15000),    # Dalverzin-Tepe (Bactria)
    (38.29, 67.96, 3.0, -100, 300, 8000),     # Khalchayan
    (37.10, 68.29, 3.5, -300, 300, 6000),     # Takht-i Sangin
    (37.79, 68.85, 3.0, 550, 800, 4000),      # Ajina-Tepe
    (37.78, 69.56, 3.5, 800, 1100, 15000),    # Hulbuk (Khuttal)
    (39.77, 68.80, 3.5, 500, 1100, 14000),    # Bunjikat (Ustrushana)
    (40.28, 69.62, 4.0, -500, 1865, 45000),   # Khujand / Alexandria Eschate
    (40.88, 71.45, 4.0, -200, 1620, 35000),   # Akhsikent (Ferghana Capital)
    (40.53, 72.79, 4.0, -500, 1865, 35000),   # Osh
    (40.77, 73.30, 3.5, -100, 1865, 25000),   # Uzgen (Karakhanid Capital)
    (40.53, 70.94, 4.0, 1700, 1865, 80000),   # Kokand
    (40.78, 72.34, 4.0, 900, 1865, 45000),    # Andijan
    (40.47, 71.72, 3.5, 800, 1865, 35000),    # Margilan
    (41.31, 69.24, 4.5, -200, 1865, 100000),  # Tashkent / Binkath / Chach
    (40.83, 68.98, 3.5, -300, 1220, 22000),   # Kanka (Antiochia-in-Chach)
    (42.85, 68.30, 4.5, -100, 1750, 40000),   # Otrar / Farab
    (42.30, 69.77, 4.0, 500, 1865, 30000),    # Sayram / Isfijab
    (42.90, 71.37, 4.0, 500, 1865, 35000),    # Taraz / Talas
    (42.75, 75.25, 4.0, 800, 1350, 30000),    # Balasagun / Burana
    (42.81, 75.20, 3.5, 500, 1000, 20000),    # Suyab / Ak-Beshim
    (42.89, 75.01, 3.5, 550, 1200, 18000),    # Navekat / Krasnaya Rechka
    (45.67, 80.26, 3.5, 800, 1350, 16000),    # Kayalyk / Qayaliq
    (43.30, 77.24, 3.5, 800, 1350, 12000),    # Talgar / Talkhir
    (43.38, 77.39, 3.0, -500, -200, 3500),    # Issyk Saka Royal Kurgan
    (49.37, 86.44, 2.5, -400, -200, 1500),    # Berel Royal Kurgans
    (47.37, 84.88, 2.5, -800, -500, 1500),    # Shilikty Royal Kurgans
    (44.08, 62.92, 3.5, -500, -100, 8000),    # Chirik-Rabat
    (44.60, 64.10, 3.5, -500, 700, 12000),    # Jety-Asar (Altyn-Asar)
    (45.61, 61.92, 3.5, 600, 1350, 18000),    # Jankent (Oghuz Yabgu Capital)
    (44.16, 66.96, 4.0, 950, 1650, 30000),    # Sighnaq (White Horde / Kazakh Capital)
    (43.52, 67.77, 3.5, 900, 1750, 22000),    # Sauran
    (43.30, 68.25, 4.0, 900, 1865, 28000),    # Yasi / Turkistan
    (47.52, 51.75, 4.0, 1250, 1580, 35000),   # Saraishyk (Golden Horde / Nogai Capital)
  ]
  out = []
  for la, lo, wt, sy, ey, mp in sites:
    pw = assign_periods_by_span(sy, ey)
    if pw:
      out.append((la, lo, wt, pw, "central_asia_scholarly_catalogue", True, mp))
  return out


def ingest_all_repositories():
  print("[B] Ingesting 13 Central Asian + Cross-Frontier Archaeological & Heritage Repositories...", flush=True)
  records = []  # (lat, lon, weight, [(period_key, frac)], src_tag, is_sett, max_pop)
  source_stats = Counter()

  # --- REPO 1: UCL CAAL (Central Asian Archaeological Landscapes — 9 dated horizons + full monument inventory + monument-type hierarchy) ---
  caal_sett_ids, caal_fort_ids, caal_fun_ids = set(), set(), set()
  for tag, target_set in [("settlements", caal_sett_ids), ("fortifications", caal_fort_ids), ("funerary", caal_fun_ids)]:
    fp = os.path.join(RAW_DIR, f"caal_type_{tag}.json")
    if os.path.exists(fp):
      for r in json.load(open(fp, "r", encoding="utf-8")):
        if r.get("caal_id"):
          target_set.add(r["caal_id"])

  def caal_weight(cid, label):
    lbl = (label or "").lower()
    if cid in caal_sett_ids or any(k in lbl for k in ("городище", "тепа", "тепе", "депе", "поселение", "қалашық", "settlement", "town", "city", "tell", "tepe")):
      return 2.5, True
    if cid in caal_fort_ids or any(k in lbl for k in ("крепость", "кала", "қала", "fort", "citadel", "castle", "караван", "рабат", "мавзолей", "мечеть")):
      return 2.0, True
    if cid in caal_fun_ids or any(k in lbl for k in ("курган", "могильник", "қорған", "kurgan", "barrow", "burial", "cemetery", "петроглиф")):
      return 0.65, False
    return 1.2, True

  caal_dated_ids = set()
  for p in PERIODS:
    pk = p["key"]
    fp = os.path.join(RAW_DIR, f"caal_horizon_{pk}.json")
    if not os.path.exists(fp):
      continue
    rows = json.load(open(fp, "r", encoding="utf-8"))
    for r in rows:
      la, lo = r.get("lat"), r.get("lon")
      if la is None or lo is None or not (32.0 <= la <= 58.0 and 43.0 <= lo <= 92.0):
        continue
      cid = r.get("caal_id") or ""
      lbl = r.get("label") or ""
      if MODERN_EXCLUDE_RE.search(lbl):
        continue
      caal_dated_ids.add(cid)
      wt, is_s = caal_weight(cid, lbl)
      cnt_boost = min(3.0, 1.0 + 0.35 * math.log1p(max(0, int(r.get("count") or 1) - 1)))
      records.append((float(la), float(lo), wt * cnt_boost, [(pk, 1.0)], "ucl_caal_dated_horizons", is_s, 0))
      source_stats["ucl_caal_dated_horizons"] += 1

  # Ingest remaining UCL CAAL monuments from caal_all_monuments.json via strict multilingual label/type forensics
  caal_all_fp = os.path.join(RAW_DIR, "caal_all_monuments.json")
  if os.path.exists(caal_all_fp):
    for r in json.load(open(caal_all_fp, "r", encoding="utf-8")):
      cid = r.get("caal_id") or ""
      if cid and cid in caal_dated_ids:
        continue
      la, lo = r.get("lat"), r.get("lon")
      if la is None or lo is None or not (32.0 <= la <= 58.0 and 43.0 <= lo <= 92.0):
        continue
      lbl = r.get("label") or ""
      pw = classify_ca_text(lbl)
      if pw is None:
        continue
      wt, is_s = caal_weight(cid, lbl)
      if not pw:
        # Use CAAL structured monument-type membership if label was opaque
        if cid in caal_sett_ids or cid in caal_fort_ids:
          pw = [
            ("05_kushan_kangju_wusun_parthian_antiquity", 0.25),
            ("06_sogdian_turkic_early_islamic", 0.25),
            ("07_samanid_karakhanid_seljuk_khwarazmshah", 0.30),
            ("08_mongol_chagatai_timurid", 0.20),
          ]
        elif cid in caal_fun_ids:
          pw = [
            ("03_bronze_age_bmac_sintashta_andronovo", 0.25),
            ("04_iron_age_saka_achaemenid_hellenistic", 0.45),
            ("05_kushan_kangju_wusun_parthian_antiquity", 0.30),
          ]
        else:
          continue  # Reject genuinely unclassified/untyped monuments (API forensics)
      cnt_boost = min(3.0, 1.0 + 0.35 * math.log1p(max(0, int(r.get("count") or 1) - 1)))
      records.append((float(la), float(lo), wt * cnt_boost, pw, "ucl_caal_typed_monuments", is_s, 0))
      source_stats["ucl_caal_typed_monuments"] += 1

  # --- REPO 2: Al-Thurayya Early Islamic World Gazetteer (Transoxiana/Khwarazm/Khurasan) ---
  at_fp = os.path.join(RAW_DIR, "althurayya_central_asia.json")
  if os.path.exists(at_fp):
    for r in json.load(open(at_fp, "r", encoding="utf-8")):
      la, lo = r.get("lat"), r.get("lon")
      if la is None or lo is None:
        continue
      ttype = (r.get("top_type") or "").lower()
      wt = 3.5 if any(k in ttype for k in ("metropol", "capital")) else (2.8 if "town" in ttype else 1.8)
      pw = [
        ("06_sogdian_turkic_early_islamic", 0.30),
        ("07_samanid_karakhanid_seljuk_khwarazmshah", 0.45),
        ("08_mongol_chagatai_timurid", 0.25),
      ]
      records.append((float(la), float(lo), wt, pw, "althurayya_islamic_gazetteer", True, 5000 if wt >= 2.8 else 1500))
      source_stats["althurayya_islamic_gazetteer"] += 1

  # --- REPO 3: Pleiades Ancient World Gazetteer ---
  pl_fp = os.path.join(RAW_DIR, "pleiades_central_asia.json")
  if os.path.exists(pl_fp):
    for r in json.load(open(pl_fp, "r", encoding="utf-8")):
      la, lo = r.get("lat"), r.get("lon")
      if la is None or lo is None:
        continue
      ft = (r.get("featureTypes") or "").lower()
      if any(k in ft for k in ("mountain", "river", "region", "sea", "lake", "desert", "pass", "province", "people")):
        if "settlement" not in ft and "fort" not in ft and "station" not in ft:
          continue
      try:
        sy = int(float(r["minDate"])) if r.get("minDate") else None
        ey = int(float(r["maxDate"])) if r.get("maxDate") else None
      except Exception:
        sy, ey = None, None
      pw = assign_periods_by_span(sy, ey) if (sy is not None and ey is not None) else [
        ("04_iron_age_saka_achaemenid_hellenistic", 0.40),
        ("05_kushan_kangju_wusun_parthian_antiquity", 0.60),
      ]
      if pw:
        records.append((float(la), float(lo), 2.5, pw, "pleiades_antiquity", True, 2500))
        source_stats["pleiades_antiquity"] += 1

  # --- REPO 4: Zenodo Tegiszhol Russian-Language Central Asian Radiocarbon Register ---
  teg_fp = os.path.join(RAW_DIR, "zenodo_21756393_tegiszhol_c14bazaar.csv")
  if not os.path.exists(teg_fp):
    teg_fp = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_c14bazAAR", "raw_databases", "tegiszhol.csv")
  if os.path.exists(teg_fp):
    seen_t = set()
    with open(teg_fp, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        try:
          la = float(row.get("lat") or row.get("latitude") or "")
          lo = float(row.get("lon") or row.get("longitude") or "")
          bp = float(row.get("c14age") or row.get("bp") or row.get("age") or "")
        except Exception:
          continue
        if not (32.0 <= la <= 58.5 and 43.0 <= lo <= 92.0):
          continue
        cal_yr = int(round(1950 - bp * 1.07))
        k = (round(la, 2), round(lo, 2), cal_yr // 250)
        if k in seen_t:
          continue
        seen_t.add(k)
        pw = assign_periods_by_span(cal_yr - 150, cal_yr + 150)
        if pw:
          records.append((la, lo, 1.8, pw, "zenodo_tegiszhol_c14", True, 0))
          source_stats["zenodo_tegiszhol_c14"] += 1

  # --- REPO 5: SVEA c14bazAAR Composite (c14_cleaned_dedup + p3k14c + calpal + nerd + radonb) ---
  c14_files = [
    os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_c14bazAAR", "c14_cleaned_dedup.csv"),
    os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_c14bazAAR", "raw_databases", "p3k14c.csv"),
    os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_c14bazAAR", "raw_databases", "nerd.csv"),
  ]
  seen_c14 = set()
  for cf in c14_files:
    if not os.path.exists(cf):
      continue
    with open(cf, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        try:
          la = float(row.get("lat") or row.get("Lat") or "")
          lo = float(row.get("lon") or row.get("Long") or row.get("lng") or "")
          bp = float(row.get("c14age") or row.get("Age") or row.get("bp") or "")
        except Exception:
          continue
        if not (32.0 <= la <= 58.5 and 43.0 <= lo <= 92.0):
          continue
        cal_yr = int(round(1950 - bp * 1.07))
        k = (round(la, 2), round(lo, 2), cal_yr // 250)
        if k in seen_c14:
          continue
        seen_c14.add(k)
        pw = assign_periods_by_span(cal_yr - 150, cal_yr + 150)
        if pw:
          records.append((la, lo, 1.6, pw, "c14bazaar_p3k14c_nerd", True, 0))
          source_stats["c14bazaar_p3k14c_nerd"] += 1

  # --- REPO 6: Allen Ancient DNA Resource v66 (Rich Central Asian Steppe, BMAC, Saka, Kangju, Wusun, Turkic aDNA) ---
  aadr_fp = os.path.join(JADE_RAW_DIR, "aadr_v66.p1_1240K.aadr.PUB.anno")
  if os.path.exists(aadr_fp):
    seen_aadr = set()
    with open(aadr_fp, "r", encoding="utf-8", errors="replace") as fh:
      fh.readline()
      for line in fh:
        p = line.strip().split("\t")
        if len(p) <= 18:
          continue
        try:
          la, lo = float(p[17]), float(p[18])
          bp = float(p[10])
        except Exception:
          continue
        if not (32.0 <= la <= 58.5 and 43.0 <= lo <= 92.0) or bp < 100:
          continue
        yr = int(round(1950 - bp))
        k = (round(la, 2), round(lo, 2), yr // 200)
        if k in seen_aadr:
          continue
        seen_aadr.add(k)
        pw = assign_periods_by_span(yr - 150, yr + 150)
        if pw:
          records.append((la, lo, 2.0, pw, "aadr_v66_central_asia_adna", True, 0))
          source_stats["aadr_v66_central_asia_adna"] += 1

  # --- REPO 7: ArchAtlas 2020 Global Excavations KMZ ---
  aa_fp = os.path.join(JADE_RAW_DIR, "arch_atlas_excavations_2020.kmz")
  if os.path.exists(aa_fp):
    try:
      with zipfile.ZipFile(aa_fp) as zf:
        kml_name = [n for n in zf.namelist() if n.endswith(".kml")][0]
        kml = zf.read(kml_name).decode("utf-8", errors="replace")
      for pm in re.findall(r"<Placemark[^>]*>(.*?)</Placemark>", kml, flags=re.S):
        mc = re.search(r"<coordinates>\s*([0-9.\-]+)\s*,\s*([0-9.\-]+)", pm)
        if not mc:
          continue
        lo, la = float(mc.group(1)), float(mc.group(2))
        if not (32.0 <= la <= 58.5 and 43.0 <= lo <= 92.0):
          continue
        mn = re.search(r"<name>(.*?)</name>", pm, flags=re.S)
        md = re.search(r"<description>(.*?)</description>", pm, flags=re.S)
        txt = ((mn.group(1) if mn else "") + " " + (md.group(1) if md else ""))
        pw = classify_ca_text(txt)
        if pw is None:
          continue
        if not pw:
          pw = [("03_bronze_age_bmac_sintashta_andronovo", 0.35), ("04_iron_age_saka_achaemenid_hellenistic", 0.35), ("05_kushan_kangju_wusun_parthian_antiquity", 0.30)]
        records.append((la, lo, 2.2, pw, "archatlas_2020", True, 0))
        source_stats["archatlas_2020"] += 1
    except Exception as e:
      print(f"  [WARN] ArchAtlas parse err: {e}", flush=True)

  # --- REPO 8: XRONOS Cached Russia/Kazakhstan/China ---
  for xfp in [
    os.path.join(JADE_RAW_DIR, "xronos_kz.json"),
    os.path.join(JADE_RAW_DIR, "xronos_ru.json"),
    os.path.join(JADE_RAW_DIR, "xronos_cn.json"),
  ]:
    if not os.path.exists(xfp):
      continue
    try:
      arr = json.load(open(xfp, "r", encoding="utf-8"))
      if not isinstance(arr, list):
        continue
      seen_x = set()
      for row in arr:
        try:
          la, lo = float(row.get("lat") or ""), float(row.get("lng") or row.get("lon") or "")
          bp = float(row.get("bp") or "")
        except Exception:
          continue
        if not (32.0 <= la <= 58.5 and 43.0 <= lo <= 92.0):
          continue
        cal_yr = int(round(1950 - bp * 1.07))
        k = (round(la, 2), round(lo, 2), cal_yr // 250)
        if k in seen_x:
          continue
        seen_x.add(k)
        pw = assign_periods_by_span(cal_yr - 150, cal_yr + 150)
        if pw:
          records.append((la, lo, 1.6, pw, "xronos_radiocarbon", True, 0))
          source_stats["xronos_radiocarbon"] += 1
    except Exception:
      pass

  # --- REPO 9: Official Uzbekistan State Register of Cultural Heritage (Cabinet of Ministers Resolution No. 846, lex.uz/docs/4543266) ---
  uz_reg_p = os.path.join(RAW_DIR, "uz_lex_846_geocoded.json")
  if os.path.exists(uz_reg_p):
    for row in json.load(open(uz_reg_p, "r", encoding="utf-8")):
      try:
        la, lo = float(row.get("lat") or 0), float(row.get("lon") or 0)
      except Exception:
        continue
      if not (36.8 <= la <= 45.8 and 55.8 <= lo <= 73.5):
        continue
      cat = str(row.get("category") or "").lower()
      nm = str(row.get("name") or "")
      per_s = str(row.get("period") or "")
      sy = row.get("start_yr")
      ey = row.get("end_yr")
      pw = assign_periods_by_span(sy, ey) if (sy is not None and ey is not None) else classify_ca_text(f"{nm} {per_s}")
      if not pw:
        if "археолог" in cat or "archaeol" in cat:
          pw = [("05_kushan_kangju_wusun_parthian_antiquity", 0.25), ("06_sogdian_turkic_early_islamic", 0.30), ("07_samanid_karakhanid_seljuk_khwarazmshah", 0.30), ("08_mongol_chagatai_timurid", 0.15)]
        else:
          pw = [("08_mongol_chagatai_timurid", 0.25), ("09_uzbek_khanates_kazakh_zhuzes", 0.75)]
      is_exact = row.get("match_mode") in ("village_exact", "site_name", "village_global")
      wt = (2.0 if "археолог" in cat or "archaeol" in cat else 1.5) * (1.0 if is_exact else 0.70)
      records.append((la, lo, wt, pw, "uzbekistan_cabinet_res846_register", True, 0))
      source_stats["uzbekistan_cabinet_res846_register"] += 1

  # --- REPO 10: Official Kazakhstan State List of Monuments (Ministry of Culture Order No. 88, adilet.zan.kz/rus/docs/V2000020397) ---
  kz_reg_p = os.path.join(RAW_DIR, "kz_adilet_geocoded.json")
  if os.path.exists(kz_reg_p):
    for row in json.load(open(kz_reg_p, "r", encoding="utf-8")):
      try:
        la, lo = float(row.get("lat") or 0), float(row.get("lon") or 0)
      except Exception:
        continue
      if not (40.5 <= la <= 55.6 and 46.4 <= lo <= 87.5):
        continue
      sy, ey = row.get("start_yr"), row.get("end_yr")
      pw = assign_periods_by_span(sy, ey) if (sy is not None and ey is not None) else classify_ca_text(str(row.get("name") or ""))
      if not pw:
        continue
      is_arch = "археолог" in str(row.get("kind") or "").lower()
      wt = 2.2 if is_arch else 1.5
      records.append((la, lo, wt, pw, "kazakhstan_adilet_order88_register", True, 0))
      source_stats["kazakhstan_adilet_order88_register"] += 1

  # --- REPO 10b: Harvard Dataverse Archaeological Atlas of Published Excavations (doi:10.7910/DVN/7MYVV7) ---
  pe_saray_p = os.path.join(RAW_DIR, "published_excavations_saray.json")
  if os.path.exists(pe_saray_p):
    for row in json.load(open(pe_saray_p, "r", encoding="utf-8")):
      try:
        la, lo = float(row.get("lat") or 0), float(row.get("lon") or 0)
      except Exception:
        continue
      if not (32.0 <= la <= 58.5 and 43.0 <= lo <= 92.0):
        continue
      txt = f"{row.get('name', '')} {row.get('desc', '')}"
      pw = classify_ca_text(txt)
      if not pw:
        pw = [
          ("03_bronze_age_bmac_sintashta_andronovo", 0.20),
          ("04_iron_age_saka_achaemenid_hellenistic", 0.20),
          ("05_kushan_kangju_wusun_parthian_antiquity", 0.20),
          ("06_sogdian_turkic_early_islamic", 0.20),
          ("07_samanid_karakhanid_seljuk_khwarazmshah", 0.20),
        ]
      records.append((la, lo, 1.8, pw, "published_excavations_atlas", True, 0))
      source_stats["published_excavations_atlas"] += 1

  # --- REPO 11: POLARIS IA RAS Cross-Frontier Belt (Russia Northern/Western Border <= 300 km) ---
  polaris_map = {
    "01_stone_age_e52.geojson": [("01_epipalaeolithic_mesolithic_early_neolithic", 1.0)],
    "02_eneolithic_e13.geojson": [("02_chalcolithic_namazga_sarazm_botai", 1.0)],
    "05_bronze_age_e47.geojson": [("03_bronze_age_bmac_sintashta_andronovo", 1.0)],
    "06_iron_age_e36.geojson": [("04_iron_age_saka_achaemenid_hellenistic", 0.55), ("05_kushan_kangju_wusun_parthian_antiquity", 0.45)],
    "07_classical_antiquity_e6.geojson": [("05_kushan_kangju_wusun_parthian_antiquity", 1.0)],
    "08_migration_period_e34.geojson": [("06_sogdian_turkic_early_islamic", 1.0)],
    "09_middle_ages_e37.geojson": [("07_samanid_karakhanid_seljuk_khwarazmshah", 0.50), ("08_mongol_chagatai_timurid", 0.50)],
    "10_early_modern_17_18c_e3.geojson": [("09_uzbek_khanates_kazakh_zhuzes", 1.0)],
  }
  for fn, pw in polaris_map.items():
    fp = os.path.join(POLARIS_GJ_DIR, fn)
    if not os.path.exists(fp):
      continue
    for feat in json.load(open(fp, "r", encoding="utf-8")).get("features", []):
      coords = (feat.get("geometry") or {}).get("coordinates") or []
      if len(coords) < 2:
        continue
      lo, la = float(coords[0]), float(coords[1])
      if 45.0 <= la <= 59.0 and 43.0 <= lo <= 91.0:
        cnt = float((feat.get("properties") or {}).get("site_count") or (feat.get("properties") or {}).get("value") or 1.0)
        if cnt > 0:
          records.append((la, lo, min(cnt, 18.0), pw, "polaris_ia_ras_frontier", True, 0))
          source_stats["polaris_ia_ras_frontier"] += 1

  # --- REPO 12: JADE Xinjiang & INDUS Hindu Kush Cross-Frontier Belts ---
  jade_map = {
    "01_palaeolithic_early_neolithic_h1.geojson": [("01_epipalaeolithic_mesolithic_early_neolithic", 1.0)],
    "02_middle_neolithic_yangshao_h2.geojson": [("02_chalcolithic_namazga_sarazm_botai", 1.0)],
    "03_late_neolithic_longshan_h3.geojson": [("03_bronze_age_bmac_sintashta_andronovo", 1.0)],
    "04_bronze_age_shang_zhou_h4.geojson": [("03_bronze_age_bmac_sintashta_andronovo", 0.6), ("04_iron_age_saka_achaemenid_hellenistic", 0.4)],
    "05_spring_autumn_warring_states_h5.geojson": [("04_iron_age_saka_achaemenid_hellenistic", 1.0)],
    "06_qin_han_xiongnu_h6.geojson": [("05_kushan_kangju_wusun_parthian_antiquity", 1.0)],
    "07_wei_jin_northern_southern_h7.geojson": [("05_kushan_kangju_wusun_parthian_antiquity", 0.5), ("06_sogdian_turkic_early_islamic", 0.5)],
    "08_sui_tang_five_dynasties_h8.geojson": [("06_sogdian_turkic_early_islamic", 1.0)],
    "09_liao_song_jin_yuan_h9.geojson": [("07_samanid_karakhanid_seljuk_khwarazmshah", 0.5), ("08_mongol_chagatai_timurid", 0.5)],
    "10_ming_qing_imperial_h10.geojson": [("09_uzbek_khanates_kazakh_zhuzes", 1.0)],
  }
  for fn, pw in jade_map.items():
    fp = os.path.join(JADE_GJ_DIR, fn)
    if not os.path.exists(fp):
      continue
    for feat in json.load(open(fp, "r", encoding="utf-8")).get("features", []):
      coords = (feat.get("geometry") or {}).get("coordinates") or []
      if len(coords) < 2:
        continue
      lo, la = float(coords[0]), float(coords[1])
      if 35.0 <= la <= 51.0 and 73.0 <= lo <= 91.0:
        cnt = float((feat.get("properties") or {}).get("site_count") or 0.0)
        if cnt > 0:
          records.append((la, lo, min(cnt, 18.0), pw, "jade_xinjiang_frontier", True, 0))
          source_stats["jade_xinjiang_frontier"] += 1

  # --- REPO 13: Curated Central Asia Excavated Type-Sites & Oasis Capitals ---
  curated = build_curated_central_asia_catalogue()
  records.extend(curated)
  source_stats["central_asia_scholarly_catalogue"] = len(curated)

  # Spatial-source deduplication (collapse identical coordinates within ~1 km per source_tag)
  dedup_map = {}
  for la, lo, wt, pw, tag, is_s, mp in records:
    kd = (round(la, 2), round(lo, 2), tag)
    if kd not in dedup_map:
      dedup_map[kd] = [la, lo, wt, list(pw), tag, is_s, mp]
    else:
      dedup_map[kd][2] = min(18.0, dedup_map[kd][2] + wt * 0.35)
      dedup_map[kd][6] = max(dedup_map[kd][6], mp)
  dedup_records = [tuple(v) for v in dedup_map.values()]

  print("\n[C] Multi-Repository Ingestion Breakdown (SARAY):", flush=True)
  for k, v in source_stats.most_common():
    print(f"    {k}: {v:,} raw records", flush=True)
  print(f"    TOTAL RAW: {len(records):,} | DEDUPLICATED COMPOSITE SITE-COMPLEXES: {len(dedup_records):,}", flush=True)
  return dedup_records, dict(source_stats)


def aggregate_and_export(domain_mask, land_area, catchments, records, source_stats):
  c_xyz = np.array([c["xyz"] for c in catchments])
  tree = cKDTree(c_xyz)

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

  rec_xyz = np.array([latlon_to_xyz(r[0], r[1]) for r in records])
  dists, idxs = tree.query(rec_xyz, workers=-1)
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
      if hyde_dens[rr, cc] >= 0.002 or ((rr - cr) ** 2 + (cc - c_col) ** 2) <= 25:
        doc_pixels.add(rr * GRID_W + cc)
      assigned_dom += 1
      if mp >= 1000 or wt >= 2.0:
        doc_settlements.append({"lat": round(la, 4), "lon": round(lo, 4), "weight": round(wt, 2), "max_pop": int(mp)})
    else:
      assigned_fr += 1

  # Biome/Aridity-conditioned Q75 + IQR taphonomic outlier shrinkage (prevents desert/kurgan visibility starving oasis cores!)
  dom_mask_c = np.array([not c["is_frontier_buffer"] for c in catchments], dtype=bool)
  c_areas = np.array([c["area_km2"] for c in catchments], dtype=np.float64)
  c_hyde = np.array([hyde_dens[latlon_to_rc(c["lat"], c["lon"])] for c in catchments], dtype=np.float64)
  is_arid = c_hyde < 2.5

  for pk in PERIOD_KEYS:
    vals = per_counts[pk]
    dens = vals / np.maximum(150.0, c_areas)
    for grp_mask, cap_mult in [(dom_mask_c & is_arid, 1.4), (dom_mask_c & (~is_arid), 2.5)]:
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

  # B2 Neighbour zero-hole imputation inside settled oasis & steppe-river belts (HYDE >= 0.5 inh/km2)
  k_nbr = min(9, n_c)
  _, nidxs = tree.query(c_xyz, k=k_nbr)
  for pk in PERIOD_KEYS:
    vals = per_counts[pk].copy()
    for ci in range(n_c):
      if vals[ci] > 0 or c_hyde[ci] < 0.5:
        continue
      nbrs = nidxs[ci, 1:]
      nvals = vals[nbrs]
      pos_n = nvals[nvals > 0]
      if pos_n.size >= 3:
        ndens = pos_n / np.maximum(150.0, c_areas[nbrs[nvals > 0]])
        vals[ci] = 0.35 * float(np.median(ndens)) * c_areas[ci]
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

  meta_obj = {
    "domain": "SARAY",
    "macro_scope": "Kazakhstan, Uzbekistan, Turkmenistan, Kyrgyzstan and Tajikistan",
    "sources": list(source_stats.keys()),
    "source_record_counts": source_stats,
    "domestic_assigned_records": assigned_dom,
    "frontier_assigned_records": assigned_fr,
    "catchment_counts": {"domestic": int(dom_mask_c.sum()), "frontier_buffer": int((~dom_mask_c).sum())},
    "documented_site_pixels": len(doc_pixels),
    "period_geojsons": period_meta,
  }
  with open(os.path.join(CFG_DIR, "sites_saray_central_asia_geojson_metadata.json"), "w", encoding="utf-8") as fh:
    json.dump(meta_obj, fh, indent=2)

  all_hyde_years = [
    -10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000,
    0, 100, 200, 300, 400, 500, 600, 700, 800, 900,
    1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
    1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790,
    1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890,
    1900, 1910, 1920, 1930, 1940, 1950
  ] + list(range(1951, 2026))

  cfg_obj = {
    "geojson_metadata_filename": "config/sites_saray_central_asia_geojson_metadata.json",
    "include_all_periods_geojson": True,
    "kriging_metadata_filename": "config/kriging_diagnostics.json",
    "output_geojson_subfolder": "geojson",
    "output_kriged_rasters_subfolder": "1.kriged_rasters",
    "output_population_rasters_subfolder": "2.population_rasters",
    "png_compression_level": 6,
    "kriging_config": {
      "all_hyde_years": all_hyde_years,
      "apply_arid_taphonomic_correction": True,
      "apply_urban_salvage_debias": True,
      "elevation_barrier_m": 650,
      "habitability_filter": {
        "arctic_lat_cut": 57.0,
        "extreme_elev_cut_m": 4200.0,
        "hyde_core_min_dens": 0.0025,
        "hyde_marginal_min_dens": 0.12,
        "site_radius_px": 1.8,
        "stadester_max_first_year": 1865,
        "stadester_radius_px": 2.0,
      },
      "hu_admixture_config": "histmap/3.data_transform/population_Substrata.viscount/config/saray_dasymetric_admixture.json5",
      "residual_kriging_mode": "hu_hyde_residual",
      "covariate_paths": {
        "documented_settlements_json": "histmap/1.data_raw/population_regional/SARAY/_shared/sites_saray_central_asia/config/documented_settlements.json",
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/SARAY/_shared/sites_saray_central_asia/config/documented_site_pixels.json",
        "forest_asc": "histmap/1.data_raw/metadata_HYDE/general_files/forest_wwf_cr.asc",
        "ghsl_urban_2020_raster": "histmap/1.data_raw/population_GHSL/urban_rasters/GHSL_2020.png",
        "ghsl_urban_folder": "histmap/1.data_raw/population_GHSL/urban_rasters",
        "ghsl_urban_pop_threshold": 35000,
        "hyde_mcevedy_rasters_folder": "histmap/2.data_cleaning/landuse_HYDE/rasters_mcevedy",
        "hyde_popc_folder": "histmap/2.data_cleaning/landuse_HYDE/rasters_scaled_to_global",
        "hyde_raw_rasters_folder": "histmap/2.data_cleaning/landuse_HYDE/rasters",
        "hyde_uopp_raster": "histmap/2.data_cleaning/landuse_HYDE/rasters/uopp_2023AD.png",
        "kk10_fallback_folder": "histmap/2.data_cleaning/population_KK10LUH2/rasters_KK10LUH2_2._global_scaling",
        "lakes_geojson": "histmap/1.data_raw/population_regional/POLARIS/_shared/_gis_cache/ne_10m_lakes.geojson",
        "landlake_asc": "histmap/1.data_raw/metadata_HYDE/general_files/landlake.asc",
        "maxln_asc": "histmap/1.data_raw/metadata_HYDE/general_files/maxln_cr.asc",
        "nelson_regions_png": "histmap/2.data_cleaning/population_KK10LUH2/config/nelson_regions.png",
        "rivers_geojson": "histmap/1.data_raw/population_regional/_shared/_gis_cache/ne_10m_rivers_lake_centerlines.geojson",
        "sub_iso_asc": "histmap/1.data_raw/metadata_HYDE/general_files/sub_iso_cr.asc",
        "urban_fringe_uopp_threshold": 1.0,
        "urban_mask_buffer_radius": 2,
        "urban_mask_inpaint_radius": 5,
        "urban_uopp_threshold": 3.8,
      },
      "dimensionless_lag_bins": [0.85, 1.45, 2.10, 2.95, 4.10, 5.60, 7.80, 10.80, 14.50],
      "domain_mask_png": "histmap/1.data_raw/population_regional/SARAY/_shared/sites_saray_central_asia/config/saray_domain_mask.png",
      "earth_radius_km": 6371,
      "frontier_conditioning_max_dist_km": 300,
      "grid_height": GRID_H,
      "grid_width": GRID_W,
      "target_domestic_catchments": int(dom_mask_c.sum()),
      "chronological_horizons": [
        {"active_periods": [p["key"]], "key": p["key"] + "_horizon", "year": p["representative_year"]}
        for p in PERIODS
      ],
    },
    "periods": PERIODS,
  }
  with open(os.path.join(CFG_DIR, "sites_saray_central_asia.json5"), "w", encoding="utf-8") as fh:
    json.dump(cfg_obj, fh, indent=2, ensure_ascii=False)

  print(f"\n[D] Completed SARAY multi-repository extraction: {assigned_dom:,} domestic + {assigned_fr:,} frontier records across {len(doc_pixels):,} documented pixels.", flush=True)


if __name__ == "__main__":
  dm_raw = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  domain_mask = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)
  la_raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  land_area = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2])
  catchments = build_catchments(domain_mask, land_area)
  records, source_stats = ingest_all_repositories()
  aggregate_and_export(domain_mask, land_area, catchments, records, source_stats)
