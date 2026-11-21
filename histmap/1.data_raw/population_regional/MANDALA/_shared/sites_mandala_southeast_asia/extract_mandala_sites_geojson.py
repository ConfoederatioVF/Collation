"""Stage C Multi-Repository Archaeological & Historical Site Composite Extractor for Project MANDALA.

Uses `mandala_domain_mask.png` (Mainland & Maritime South-East Asia strictly excluding West New Guinea),
discretises MANDALA + a 300 km cross-frontier conditioning belt (Yunnan, Guangxi, Hainan, NE India,
Bangladesh, West New Guinea fringe) into scale-adaptive HydroBASINS Level 6 catchments (combining
`hybas_as_lev06_v1c.zip` + `hybas_au_lev06_v1c.zip`, <= 25,000 km2 + micro-island anchors), ingests
and deduplicates 11+ institutional/open-science archaeological repositories across 10 South-East Asian
horizons (-13000 to 1860 AD), applies monument-class weighting and biome-conditioned Q75 + IQR
taphonomic shrinkage + B2 settled-belt neighbour imputation, and exports ViscountMaternKriging-ready
GeoJSONs and configuration manifests.
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
from shapely.prepared import prep

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MANDALA_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MANDALA")
DOMAIN_DIR = os.path.join(MANDALA_DIR, "_shared", "sites_mandala_southeast_asia")
RAW_DIR = os.path.join(DOMAIN_DIR, "0.raw_data")
CFG_DIR = os.path.join(DOMAIN_DIR, "config")
GJ_DIR = os.path.join(DOMAIN_DIR, "geojson")
MANDALA_GIS = os.path.join(MANDALA_DIR, "_shared", "_gis_cache")
JADE_GIS = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "_gis_cache")
JADE_RAW = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "sites_east_asia", "0.raw_data")
JADE_GJ = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "sites_east_asia", "geojson")
INDUS_GJ = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "INDUS", "_shared", "sites_indus_south_asia", "geojson")

os.makedirs(CFG_DIR, exist_ok=True)
os.makedirs(GJ_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160
EARTH_R_KM = 6371.0

PERIODS = [
  {
    "epoch_id": 1, "key": "01_palaeolithic_hoabinhian_toalean",
    "filename": "01_palaeolithic_hoabinhian_toalean.png",
    "geojson_filename": "01_palaeolithic_hoabinhian_toalean.geojson",
    "approx_start_year": -13000, "approx_end_year": -4000, "representative_year": -7500,
    "name_en": "Late Palaeolithic, Hoabinhian and Wallacean Foragers",
    "name_de": "Spätpaläolithikum, Hoabinhien und Wallacea-Wildbeuter",
    "name_fr": "Paléolithique final, Hoabinhien et chasseurs-cueilleurs de Wallacea",
    "date_range_en": "c. 13000-4000BC (Hoabinhian, Bacsonian, Niah, Tabon, Song Terus, Toalean and Lene Hara)"
  },
  {
    "epoch_id": 2, "key": "02_neolithic_austronesian_dispersal",
    "filename": "02_neolithic_austronesian_dispersal.png",
    "geojson_filename": "02_neolithic_austronesian_dispersal.geojson",
    "approx_start_year": -4000, "approx_end_year": -1500, "representative_year": -2500,
    "name_en": "Mainland Wet-Rice Neolithic and Austronesian Maritime Dispersal",
    "name_de": "Festland-Neolithikum und Austronesische Ausbreitung",
    "name_fr": "Néolithique continental et expansion maritime austronésienne",
    "date_range_en": "c. 4000-1500BC (Khok Phanom Di, Phung Nguyen, Man Bac, Ban Chiang, Nagsabaran and Kalumpang)"
  },
  {
    "epoch_id": 3, "key": "03_bronze_age_dongson_banchiang",
    "filename": "03_bronze_age_dongson_banchiang.png",
    "geojson_filename": "03_bronze_age_dongson_banchiang.geojson",
    "approx_start_year": -1500, "approx_end_year": -500, "representative_year": -900,
    "name_en": "Bronze Age Chiefdoms and Early Metallurgy",
    "name_de": "Bronzezeitliche Häuptlingstümer und Frühe Metallurgie",
    "name_fr": "Chefferies de l'Âge du Bronze et métallurgie ancienne",
    "date_range_en": "c. 1500-500BC (Ban Non Wat, Ban Chiang, Dong Dau, Go Mun, Khao Wong Prachan and Sepon)"
  },
  {
    "epoch_id": 4, "key": "04_iron_age_sa_huynh_early_pyu",
    "filename": "04_iron_age_sa_huynh_early_pyu.png",
    "geojson_filename": "04_iron_age_sa_huynh_early_pyu.geojson",
    "approx_start_year": -500, "approx_end_year": 100, "representative_year": -200,
    "name_en": "Iron Age, Dong Son, Sa Huynh and Early Maritime Trade",
    "name_de": "Eisenzeit, Dong Son, Sa Huynh und Früher Seehandel",
    "name_fr": "Âge du Fer, Dong Son, Sa Huynh et commerce maritime ancien",
    "date_range_en": "500BC-100AD (Co Loa, Dong Son, Sa Huynh, Khao Sam Kaeo, Ban Don Ta Phet, Buni and Sembiran)"
  },
  {
    "epoch_id": 5, "key": "05_funan_pyu_dvaravati_champa",
    "filename": "05_funan_pyu_dvaravati_champa.png",
    "geojson_filename": "05_funan_pyu_dvaravati_champa.geojson",
    "approx_start_year": 100, "approx_end_year": 650, "representative_year": 400,
    "name_en": "Funan, Pyu Walled Cities, Dvaravati, Early Champa and Tarumanagara",
    "name_de": "Funan, Pyu-Städte, Dvaravati, Frühes Champa und Tarumanagara",
    "name_fr": "Funan, cités Pyu, Dvaravati, Champa ancien et Tarumanagara",
    "date_range_en": "100-650AD (Oc Eo, Angkor Borei, Sri Ksetra, Beikthano, Halin, Nakhon Pathom, Tra Kieu and Bujang Valley)"
  },
  {
    "epoch_id": 6, "key": "06_chenla_srivijaya_sailendra_mataram",
    "filename": "06_chenla_srivijaya_sailendra_mataram.png",
    "geojson_filename": "06_chenla_srivijaya_sailendra_mataram.geojson",
    "approx_start_year": 650, "approx_end_year": 950, "representative_year": 800,
    "name_en": "Chenla, Srivijaya, Sailendra and Central Javanese Mataram",
    "name_de": "Chenla, Srivijaya, Sailendra und Zentraljava-Mataram",
    "name_fr": "Chenla, Srivijaya, Sailendra et Mataram de Java central",
    "date_range_en": "650-950AD (Sambor Prei Kuk, Hariharalaya, Palembang, Muaro Jambi, Borobudur, Prambanan and Si Thep)"
  },
  {
    "epoch_id": 7, "key": "07_angkor_pagan_dai_viet_kediri",
    "filename": "07_angkor_pagan_dai_viet_kediri.png",
    "geojson_filename": "07_angkor_pagan_dai_viet_kediri.geojson",
    "approx_start_year": 950, "approx_end_year": 1300, "representative_year": 1150,
    "name_en": "Classical Angkor, Pagan Burma, Ly-Tran Dai Viet and Kediri-Singhasari",
    "name_de": "Klassisches Angkor, Pagan, Dai Viet und Kediri-Singhasari",
    "name_fr": "Angkor classique, Pagan, Dai Viet et Kediri-Singhasari",
    "date_range_en": "950-1300AD (Greater Angkor, Bagan, Thang Long, Vijaya Champa, Phimai, Kediri, Kota Cina and Butuan)"
  },
  {
    "epoch_id": 8, "key": "08_majapahit_sukhothai_early_ayutthaya",
    "filename": "08_majapahit_sukhothai_early_ayutthaya.png",
    "geojson_filename": "08_majapahit_sukhothai_early_ayutthaya.geojson",
    "approx_start_year": 1300, "approx_end_year": 1500, "representative_year": 1400,
    "name_en": "Majapahit, Sukhothai, Early Ayutthaya, Lan Xang and Melaka",
    "name_de": "Majapahit, Sukhothai, Frühes Ayutthaya, Lan Xang und Malakka",
    "name_fr": "Majapahit, Sukhothai, Ayutthaya ancien, Lan Xang et Malacca",
    "date_range_en": "1300-1500AD (Trowulan, Sukhothai, Ayutthaya, Chiang Mai, Luang Prabang, Ava, Pegu, Melaka and Brunei)"
  },
  {
    "epoch_id": 9, "key": "09_sultanates_toungoo_le_nguyen_iberian",
    "filename": "09_sultanates_toungoo_le_nguyen_iberian.png",
    "geojson_filename": "09_sultanates_toungoo_le_nguyen_iberian.geojson",
    "approx_start_year": 1500, "approx_end_year": 1680, "representative_year": 1600,
    "name_en": "Age of Commerce Sultanates, Toungoo, Ayutthaya and Iberian-VOC Ports",
    "name_de": "Sultanate des Handelszeitalters, Toungoo, Ayutthaya und frühe Kolonialhäfen",
    "name_fr": "Sultanats marchands, Toungoo, Ayutthaya et comptoirs ibériques et VOC",
    "date_range_en": "1500-1680AD (Aceh, Banten, Mataram, Makassar, Ternate, Sulu, Manila, Batavia, Toungoo, Hoi An and Longvek)"
  },
  {
    "epoch_id": 10, "key": "10_late_precolonial_colonial_transition",
    "filename": "10_late_precolonial_colonial_transition.png",
    "geojson_filename": "10_late_precolonial_colonial_transition.geojson",
    "approx_start_year": 1680, "approx_end_year": 1860, "representative_year": 1780,
    "name_en": "Konbaung, Rattanakosin, Nguyen and Early Colonial Transition",
    "name_de": "Konbaung, Rattanakosin, Nguyen und Kolonialer Übergang",
    "name_fr": "Konbaung, Rattanakosin, Nguyen et transition coloniale",
    "date_range_en": "1680-1860AD (Amarapura, Mandalay, Bangkok, Hue, Gia Dinh, Batavia, Surabaya, Penang, Singapore and Dili)"
  }
]
PERIOD_KEYS = [p["key"] for p in PERIODS]


def latlon_to_rc(lat, lon):
  r = min(GRID_H - 1, max(0, int((90.0 - lat) * GRID_H / 180.0)))
  c = min(GRID_W - 1, max(0, int((lon + 180.0) * GRID_W / 360.0)))
  return r, c


def latlon_to_xyz(lat, lon):
  lr = math.radians(lat)
  nr = math.radians(lon)
  cl = math.cos(lr)
  return (cl * math.cos(nr), cl * math.sin(nr), math.sin(lr))


def assign_periods_by_span(start_yr, end_yr):
  if start_yr is None or end_yr is None:
    return []
  if start_yr > end_yr:
    start_yr, end_yr = end_yr, start_yr
  if end_yr < -16000 or start_yr > 1885:
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
    if 1860 < mid <= 1900:
      return [(PERIODS[-1]["key"], 1.0)]
    return []
  tot = sum(w for _, w in hits)
  return [(k, w / tot) for k, w in hits]


def classify_text_to_periods(text):
  s = (text or "").lower()
  if not s:
    return []
  m_bc = re.findall(r"(\d{3,5})\s*(?:bc|bce|b\.c\.)", s)
  if m_bc:
    yrs = [-int(x) for x in m_bc if 50 <= int(x) <= 16000]
    if yrs:
      return assign_periods_by_span(min(yrs), max(yrs))
  m_ad = re.findall(r"(?:ad|ce)\s*(\d{3,4})|(\d{3,4})\s*(?:ad|ce)", s)
  yrs_ad = [int(a or b) for a, b in m_ad if 1 <= int(a or b) <= 1880]
  if yrs_ad:
    return assign_periods_by_span(min(yrs_ad), max(yrs_ad))
  m_c_bc = re.search(r"(\d{1,2})(?:st|nd|rd|th)\s+century\s+(?:bc|bce)", s)
  if m_c_bc:
    c = int(m_c_bc.group(1))
    return assign_periods_by_span(-c * 100, -(c - 1) * 100)
  m_c_ad = re.search(r"(\d{1,2})(?:st|nd|rd|th)\s+century(?:\s+(?:ad|ce))?", s)
  if m_c_ad:
    c = int(m_c_ad.group(1))
    if 1 <= c <= 19:
      return assign_periods_by_span((c - 1) * 100, c * 100)

  hits = []
  kw_rules = [
    (["palaeolithic", "paleolithic", "pleistocene", "hoabinhian", "bacsonian", "toalean", "rock art", "gua ", "leang ", "liang ", "cave", "rock shelter", "shell midden"], "01_palaeolithic_hoabinhian_toalean"),
    (["neolithic", "austronesian", "lapita", "phung nguyen", "khok phanom", "kalumpang", "nagsabaran"], "02_neolithic_austronesian_dispersal"),
    (["bronze age", "ban chiang", "ban non wat", "dong dau", "go mun", "non nok tha", "megalith", "jar burial", "plain of jars", "dolmen", "menhir"], "03_bronze_age_dongson_banchiang"),
    (["iron age", "dong son", "sa huynh", "co loa", "buni", "kalanay", "sembiran", "gilimanuk", "ban don ta phet"], "04_iron_age_sa_huynh_early_pyu"),
    (["funan", "oc eo", "pyu", "beikthano", "sri ksetra", "halin", "dvaravati", "tarumanagara", "kutai", "bujang", "early champa", "tra kieu"], "05_funan_pyu_dvaravati_champa"),
    (["chenla", "sambor", "srivijaya", "sriwijaya", "sailendra", "syailendra", "borobudur", "prambanan", "dieng", "muaro jambi", "muara takus", "hariphunchai", "si thep", "barus", "candi"], "06_chenla_srivijaya_sailendra_mataram"),
    (["angkor", "khmer", "prasat", "bagan", "pagan", "ly dynasty", "tran dynasty", "champa", "cham tower", "thap ", "kediri", "kadiri", "singhasari", "singosari", "kota cina", "padang lawas", "butuan"], "07_angkor_pagan_dai_viet_kediri"),
    (["majapahit", "trowulan", "sukhothai", "si satchanalai", "lan na", "lanna", "lan xang", "hanthawaddy", "mrauk", "ava ", "melaka", "malacca", "pasai", "brunei"], "08_majapahit_sukhothai_early_ayutthaya"),
    (["ayutthaya", "toungoo", "sultanate", "aceh", "banten", "demak", "mataram", "makassar", "gowa", "ternate", "tidore", "sulu", "maguindanao", "intramuros", "spanish", "portuguese", "voc", "batavia", "fort ", "benteng", "keraton", "kraton", "istana", "mosque", "masjid", "church", "simbahan", "citadel", "thanh "], "09_sultanates_toungoo_le_nguyen_iberian"),
    (["konbaung", "mandalay", "amarapura", "rattanakosin", "bangkok", "nguyen", "hue", "colonial", "dutch east indies", "straits settlements", "penang", "singapore", "dili", "wat ", "pagoda", "paya", "stupa", "zedi", "monastery", "temple"], "10_late_precolonial_colonial_transition"),
  ]
  for kws, pk in kw_rules:
    if any(k in s for k in kws):
      hits.append(pk)
  if hits:
    w = 1.0 / len(hits)
    return [(pk, w) for pk in hits]
  return []


def parse_wd_coord(val):
  m = re.search(r"Point\(\s*([0-9.\-]+)\s+([0-9.\-]+)\s*\)", str(val or ""))
  if not m:
    return None, None
  return float(m.group(2)), float(m.group(1))


def parse_wd_year(val):
  m = re.match(r"^\+?(-?\d{1,5})-", str(val or ""))
  return int(m.group(1)) if m else None


def load_domain_and_land():
  dm_path = os.path.join(CFG_DIR, "mandala_domain_mask.png")
  la_path = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
  dm_raw = np.asarray(Image.open(dm_path).convert("RGBA"), dtype=np.uint8)
  mask = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)
  la_raw = np.asarray(Image.open(la_path).convert("RGBA"), dtype=np.uint8)
  la = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2])
  print(f"[A] Loaded mandala_domain_mask.png: {int(mask.sum()):,} px | area={float(la[mask].sum()):,.0f} km2", flush=True)
  return mask, la


def build_catchments(domain_mask, land_area):
  """Combines HydroBASINS Level 6 (AS + AU) inside MANDALA + 300 km conditioning belt + micro-islands."""
  dist_px = distance_transform_edt(~domain_mask)
  in_frontier_band = (~domain_mask) & (dist_px <= 44.0) & (land_area > 0)

  catchments = []
  seen_ids = set()
  for prefix, zp in (
    ("as", os.path.join(JADE_GIS, "hybas_as_lev06_v1c.zip")),
    ("au", os.path.join(MANDALA_GIS, "hybas_au_lev06_v1c.zip")),
  ):
    with zipfile.ZipFile(zp) as zf:
      sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
      sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
      fields = [f[0] for f in sf.fields[1:]]
      idx_id = fields.index("HYBAS_ID")
      idx_area = fields.index("SUB_AREA")

      for sr in sf.iterShapeRecords():
        bb = sr.shape.bbox
        if bb[2] < 89.0 or bb[0] > 138.0 or bb[3] < -13.0 or bb[1] > 31.0:
          continue
        geom = shape(sr.shape.__geo_interface__)
        if geom.is_empty:
          continue
        rep = geom.representative_point()
        lon, lat = float(rep.x), float(rep.y)
        area_km2 = max(120.0, float(sr.record[idx_area] or 1000.0))
        r_c, c_c = latlon_to_rc(lat, lon)

        is_dom = bool(domain_mask[r_c, c_c])
        is_fr = bool(in_frontier_band[r_c, c_c])
        if not is_dom and not is_fr:
          p_geom = prep(geom)
          r0, c0 = latlon_to_rc(bb[3], bb[0])
          r1, c1 = latlon_to_rc(bb[1], bb[2])
          sub_dom = domain_mask[r0:r1 + 1, c0:c1 + 1]
          if sub_dom.any():
            drs, dcs = np.where(sub_dom)
            step = max(1, len(drs) // 25)
            for k in range(0, len(drs), step):
              plat = 90.0 - (r0 + drs[k] + 0.5) * 180.0 / GRID_H
              plon = -180.0 + (c0 + dcs[k] + 0.5) * 360.0 / GRID_W
              if p_geom.contains(Point(plon, plat)):
                is_dom = True
                lat, lon = plat, plon
                break
          if not is_dom:
            sub_fr = in_frontier_band[r0:r1 + 1, c0:c1 + 1]
            if sub_fr.any():
              is_fr = True
        if not is_dom and not is_fr:
          continue

        hid = f"hyb_{prefix}_{sr.record[idx_id]}"
        if hid in seen_ids:
          continue
        seen_ids.add(hid)

        if area_km2 > 25000.0:
          p_geom = prep(geom)
          lat_steps = np.arange(math.floor(bb[1]) + 0.65, bb[3], 1.35)
          lon_steps = np.arange(math.floor(bb[0]) + 0.65, bb[2], 1.35)
          sub_pts = []
          for la_s in lat_steps:
            for lo_s in lon_steps:
              if p_geom.contains(Point(lo_s, la_s)):
                rr, cc = latlon_to_rc(la_s, lo_s)
                if domain_mask[rr, cc] or in_frontier_band[rr, cc]:
                  sub_pts.append((float(la_s), float(lo_s), bool(domain_mask[rr, cc])))
          if len(sub_pts) >= 2:
            sub_area = area_km2 / len(sub_pts)
            for j, (la_s, lo_s, sub_dom_flag) in enumerate(sub_pts):
              catchments.append({
                "region_id": f"{hid}_s{j}", "lat": la_s, "lon": lo_s,
                "area_km2": round(sub_area, 1), "is_frontier_buffer": not sub_dom_flag,
                "xyz": latlon_to_xyz(la_s, lo_s),
              })
            continue

        catchments.append({
          "region_id": hid, "lat": lat, "lon": lon,
          "area_km2": round(area_km2, 1), "is_frontier_buffer": not is_dom,
          "xyz": latlon_to_xyz(lat, lon),
        })

  # Dedicated Insular SE Asia micro-island & spice-island catchments
  island_anchors = [
    ("mandala_singapore_riau", 1.352, 103.820, 750.0),
    ("mandala_penang_langkawi", 5.414, 100.329, 450.0),
    ("mandala_phuket_andaman", 7.880, 98.392, 600.0),
    ("mandala_phu_quoc", 10.227, 103.957, 580.0),
    ("mandala_batanes", 20.448, 121.970, 220.0),
    ("mandala_sulu_jolo", 6.052, 121.002, 1600.0),
    ("mandala_tawi_tawi", 5.133, 120.133, 1080.0),
    ("mandala_ternate_tidore", 0.790, 127.360, 420.0),
    ("mandala_ambon_lease", -3.695, 128.181, 800.0),
    ("mandala_banda_islands", -4.525, 129.895, 180.0),
    ("mandala_kei_islands", -5.640, 132.750, 1430.0),
    ("mandala_tanimbar_islands", -7.980, 131.300, 5400.0),
    ("mandala_aru_islands", -6.150, 134.250, 8500.0),
    ("mandala_nias_simeulue", 1.100, 97.600, 5100.0),
    ("mandala_mentawai", -2.100, 99.650, 6000.0),
    ("mandala_natuna_anambas", 3.960, 108.380, 2000.0),
    ("mandala_sangihe_talaud", 3.550, 125.550, 1250.0),
    ("mandala_oecusse_timor", -9.200, 124.370, 815.0),
    ("mandala_dili_atabae", -8.556, 125.560, 1800.0),
    ("mandala_baucau_lautem", -8.470, 126.450, 3200.0),
  ]
  for rid, la_i, lo_i, ar_i in island_anchors:
    catchments.append({
      "region_id": rid, "lat": la_i, "lon": lo_i,
      "area_km2": ar_i, "is_frontier_buffer": False,
      "xyz": latlon_to_xyz(la_i, lo_i),
    })

  dom_n = sum(1 for c in catchments if not c["is_frontier_buffer"])
  fr_n = len(catchments) - dom_n
  print(f"[B] Built scale-adaptive HydroBASINS (AS+AU) catchments: {dom_n} domestic + {fr_n} frontier = {len(catchments)} total", flush=True)
  return catchments


def build_curated_southeast_asia_catalogue():
  """Scholarly South-East Asian archaeological & historical urban complexes (Bellwood, Higham,
  Stark, Evans, Miksic, Manguin, Moore, Luce, Glover, O'Connor, Coedes, Reid, Lieberman, Scott)."""
  raw_sites = [
    # --- PALAEOLITHIC / HOABINHIAN / WALLACEAN ---
    (19.567, 98.117, 3.5, -12000, -5500, "Spirit Cave (Tham Phi Maen)", 250),
    (20.800, 105.330, 3.5, -13000, -4000, "Xom Trai & Hang Muoi (Hoabinhian)", 350),
    (21.880, 106.320, 3.5, -11000, -5000, "Bac Son Caves (Bacsonian)", 300),
    (20.320, 105.620, 3.5, -12000, -4000, "Con Moong Cave (Thanh Hoa)", 350),
    (4.800, 101.980, 3.5, -10000, -1000, "Gua Cha (Kelantan)", 300),
    (5.120, 100.970, 3.5, -13000, -3000, "Lenggong Valley (Gua Gunung Runtuh)", 350),
    (3.814, 113.784, 4.5, -13000, -500, "Niah Great Cave (Sarawak)", 600),
    (9.277, 117.980, 4.0, -13000, -200, "Tabon Caves Complex (Palawan)", 500),
    (17.703, 121.824, 3.5, -13000, -1500, "Callao Cave (Cagayan)", 300),
    (-8.120, 110.970, 3.5, -13000, -2000, "Song Terus & Gua Braholo (Gunung Sewu)", 400),
    (-5.000, 119.670, 4.0, -13000, -1500, "Leang Burung & Maros-Pangkep Karst (Toalean)", 500),
    (-8.400, 127.290, 4.0, -13000, -1000, "Lene Hara & Jerimalai (Tutuala, Timor-Leste)", 400),
    (21.133, 96.333, 3.5, -11000, -2500, "Padah-Lin Caves (Shan State)", 300),
    (12.230, 102.980, 3.5, -9000, -2000, "Laang Spean (Battambang)", 350),
    (19.950, 102.250, 3.5, -13000, -3000, "Tam Pa Ling & Tam Hang (Laos)", 300),
    (-8.530, 120.440, 3.5, -13000, -2000, "Liang Bua (Flores)", 350),
    (5.150, 97.100, 3.0, -9000, -2500, "Sumatralith Shell Middens (Aceh-Medan)", 350),
    # --- NEOLITHIC / AUSTRONESIAN / BRONZE AGE ---
    (13.567, 101.133, 4.5, -2000, -1400, "Khok Phanom Di (Chon Buri)", 1200),
    (17.406, 103.241, 4.5, -2100, 200, "Ban Chiang (Udon Thani)", 2200),
    (15.265, 102.273, 4.5, -1750, 500, "Ban Non Wat (Nakhon Ratchasima)", 2500),
    (16.717, 102.233, 4.0, -2500, -500, "Non Nok Tha (Khon Kaen)", 1500),
    (21.333, 105.333, 4.5, -2000, -1000, "Phung Nguyen & Dong Dau (Red River)", 2500),
    (20.120, 105.980, 4.0, -2000, -1500, "Man Bac (Ninh Binh)", 1200),
    (14.950, 100.650, 4.0, -1500, -300, "Khao Wong Prachan & Non Pa Wai (Lop Buri)", 1800),
    (16.950, 105.980, 4.0, -1200, 200, "Sepon Copper Complex (Savannakhet)", 1500),
    (19.430, 103.150, 4.5, -1200, 500, "Plain of Jars (Xiangkhoang)", 2500),
    (18.180, 121.660, 4.0, -2200, 500, "Nagsabaran & Lal-lo Shell Middens (Cagayan)", 1400),
    (-2.450, 119.450, 4.0, -1800, -500, "Minanga Sipakko & Kamassi (Kalumpang, Sulawesi)", 1200),
    (4.480, 118.620, 3.5, -2500, -500, "Bukit Tengkorak (Sabah)", 900),
    (1.180, 110.480, 3.5, -2500, -500, "Gua Sireh (Sarawak)", 700),
    (-8.200, 122.900, 3.5, -1500, -300, "Pain Haka (Flores Neolithic)", 800),
    (21.750, 95.150, 3.5, -1200, -300, "Nyaunggan & Oakaie (Chindwin Bronze Age)", 1200),
    (21.180, 95.970, 4.0, -800, 200, "Samon Valley Bronze-Iron Sites", 2000),
    (11.330, 106.150, 4.0, -2000, -500, "Mimotien Circular Earthworks (Memot-Binh Phuoc)", 1800),
    # --- IRON AGE / DONG SON / SA HUYNH / EARLY TRADE ---
    (21.113, 105.873, 5.0, -400, 500, "Co Loa Citadel (Au Lac)", 18000),
    (19.830, 105.780, 4.5, -600, 200, "Dong Son Type-Site (Ma River, Thanh Hoa)", 6000),
    (14.660, 109.050, 4.5, -600, 200, "Sa Huynh & Go Ma Voi (Quang Ngai)", 5000),
    (10.520, 99.180, 4.5, -400, 100, "Khao Sam Kaeo (Chumphon Isthmus)", 6000),
    (14.070, 99.680, 4.0, -400, 100, "Ban Don Ta Phet (Kanchanaburi)", 3000),
    (11.420, 105.510, 4.0, -300, 200, "Prohear & Phum Snay (Cambodia Iron Age)", 3000),
    (-6.130, 107.030, 4.5, -400, 500, "Buni Complex & Batujaya (West Java)", 7000),
    (-8.120, 115.270, 4.5, -200, 600, "Sembiran & Pacung (North Bali)", 4500),
    (-8.160, 114.440, 4.0, -200, 400, "Gilimanuk (West Bali)", 3000),
    (6.040, 124.500, 3.5, -200, 400, "Ayub Cave Maitum (Sarangani)", 1200),
    (12.230, 123.500, 3.5, -400, 500, "Kalanay Cave (Masbate)", 1200),
    # --- FUNAN / PYU / DVARAVATI / CHAMPA / TARUMANAGARA ---
    (10.249, 105.149, 5.0, 50, 650, "Oc Eo (Funan Port Metropolis)", 28000),
    (10.993, 104.978, 5.0, -400, 700, "Angkor Borei (Funan Capital)", 22000),
    (18.817, 95.283, 5.0, 100, 950, "Sri Ksetra (Pyu Capital)", 35000),
    (20.008, 95.382, 4.5, -200, 650, "Beikthano (Pyu Walled City)", 18000),
    (22.472, 95.819, 4.5, 100, 832, "Halin (Pyu Walled City)", 16000),
    (21.280, 96.200, 4.0, 100, 800, "Maingmaw / Pinle (Pyu City)", 12000),
    (20.800, 92.970, 4.5, 300, 1000, "Dhanyawadi & Vesali (Early Arakan)", 18000),
    (15.820, 108.230, 4.5, 192, 1000, "Tra Kieu / Simhapura (Early Champa)", 15000),
    (15.764, 108.124, 4.5, 350, 1400, "My Son Sanctuary (Champa)", 8000),
    (15.650, 108.420, 4.5, 875, 1000, "Dong Duong / Indrapura (Champa)", 14000),
    (13.820, 109.120, 5.0, 1000, 1471, "Vijaya / Cha Ban (Champa Capital)", 25000),
    (12.265, 109.195, 4.0, 600, 1653, "Kauthara / Po Nagar (Nha Trang)", 10000),
    (11.564, 108.990, 4.0, 750, 1832, "Panduranga / Phan Rang (Champa)", 12000),
    (13.819, 100.060, 5.0, 300, 1100, "Nakhon Pathom (Dvaravati Capital)", 25000),
    (14.375, 99.892, 4.5, 200, 900, "U Thong (Dvaravati)", 14000),
    (13.485, 99.818, 4.0, 500, 1000, "Ku Bua (Ratchaburi Dvaravati)", 12000),
    (15.467, 101.145, 4.5, 300, 1250, "Si Thep (Phetchabun Dvaravati-Khmer)", 18000),
    (16.310, 103.520, 4.0, 600, 1100, "Muang Fa Daet (Kalasin Dvaravati)", 12000),
    (13.883, 101.400, 4.0, 400, 1100, "Si Mahosot (Prachin Buri)", 10000),
    (18.575, 99.008, 4.5, 700, 1292, "Hariphunchai / Lamphun", 18000),
    (16.925, 97.370, 4.5, 400, 1100, "Thaton / Suvannabhumi (Mon)", 18000),
    (21.033, 106.050, 4.5, -100, 600, "Luy Lau (Han-Tang Jiaozhi Capital)", 25000),
    (5.736, 100.415, 4.5, 200, 1300, "Bujang Valley / Sungai Batu (Kedah)", 15000),
    (-6.130, 106.870, 4.5, 350, 700, "Tarumanagara / Tugu (West Java)", 15000),
    (-0.420, 116.980, 4.0, 350, 1600, "Kutai Martadipura (Muara Kaman, Borneo)", 10000),
    # --- CHENLA / SRIVIJAYA / SAILENDRA / MATARAM ---
    (12.868, 105.043, 5.0, 600, 900, "Sambor Prei Kuk / Isanapura (Chenla)", 28000),
    (13.317, 103.972, 4.5, 780, 950, "Hariharalaya / Roluos (Early Angkor)", 25000),
    (-2.989, 104.756, 5.0, 670, 1860, "Palembang (Srivijaya Capital)", 45000),
    (-1.477, 103.668, 5.0, 700, 1400, "Muaro Jambi / Malayu (Batang Hari)", 30000),
    (0.335, 100.642, 4.0, 800, 1200, "Muara Takus (Kampar, Sumatra)", 10000),
    (2.012, 98.404, 4.5, 700, 1500, "Barus / Fansur (North Sumatra Camphor Port)", 12000),
    (3.727, 98.655, 4.5, 1050, 1350, "Kota Cina (Deli, North Sumatra)", 15000),
    (1.300, 99.830, 4.0, 1000, 1400, "Padang Lawas / Bahal (Pannai)", 10000),
    (-7.206, 109.907, 4.5, 680, 950, "Dieng Plateau (Early Mataram)", 12000),
    (-7.608, 110.204, 5.0, 770, 1000, "Borobudur & Kedu Plain (Sailendra)", 35000),
    (-7.752, 110.491, 5.0, 800, 1000, "Prambanan & Ratu Boko (Mataram)", 40000),
    (20.285, 105.908, 4.5, 968, 1010, "Hoa Lu (Dinh-Early Le Capital)", 20000),
    # --- CLASSICAL ANGKOR / PAGAN / DAI VIET / MAJAPAHIT / SUKHOTHAI / AYUTTHAYA ---
    (13.412, 103.867, 5.0, 889, 1431, "Greater Angkor / Yasodharapura", 750000),
    (13.783, 104.537, 4.5, 921, 1050, "Koh Ker / Lingapura (Khmer)", 35000),
    (14.071, 103.095, 4.5, 1150, 1350, "Banteay Chhmar (Khmer)", 25000),
    (13.438, 104.749, 4.5, 1050, 1350, "Preah Khan of Kompong Svay", 30000),
    (15.221, 102.494, 4.5, 1000, 1350, "Phimai / Vimayapura (Khorat Khmer)", 25000),
    (14.532, 102.940, 4.0, 1000, 1300, "Phanom Rung (Buriram Khmer)", 12000),
    (14.848, 105.818, 4.5, 500, 1350, "Vat Phou / Shresthapura (Champasak)", 18000),
    (21.172, 94.858, 5.0, 849, 1300, "Pagan / Bagan (Pagan Kingdom Capital)", 120000),
    (21.028, 105.854, 5.0, 1010, 1860, "Thang Long / Hanoi (Dai Viet Capital)", 130000),
    (20.070, 105.600, 4.5, 1397, 1500, "Citadel of the Ho Dynasty & Lam Kinh", 25000),
    (-7.817, 112.017, 5.0, 1042, 1527, "Kadiri / Daha (East Java)", 40000),
    (-7.889, 112.664, 4.5, 1222, 1350, "Singhasari / Tumapel (East Java)", 30000),
    (-7.560, 112.382, 5.0, 1293, 1527, "Trowulan / Majapahit Capital", 100000),
    (-7.158, 112.655, 4.5, 1300, 1860, "Gresik & Tuban (Java Pasisir Ports)", 35000),
    (-8.540, 115.320, 4.5, 900, 1860, "Bedulu & Gelgel / Klungkung (Bali)", 25000),
    (1.717, 110.317, 4.0, 900, 1400, "Santubong (Sarawak Iron-Trade Port)", 8000),
    (8.947, 125.540, 4.5, 800, 1600, "Butuan / Balangay (Mindanao)", 18000),
    (14.618, 120.968, 5.0, 900, 1860, "Tondo & Maynila / Manila", 150000),
    (10.316, 123.885, 5.0, 1200, 1860, "Cebu / Sugbu", 45000),
    (17.019, 99.703, 5.0, 1238, 1584, "Sukhothai & Si Satchanalai", 40000),
    (14.353, 100.568, 5.0, 1351, 1767, "Ayutthaya (Siam Capital)", 300000),
    (18.788, 98.985, 5.0, 1296, 1860, "Chiang Mai (Lan Na Capital)", 55000),
    (19.886, 102.135, 4.5, 1353, 1860, "Luang Prabang (Lan Xang)", 30000),
    (17.975, 102.633, 4.5, 1560, 1860, "Vientiane (Lan Xang)", 45000),
    (21.853, 95.978, 5.0, 1364, 1841, "Inwa / Ava & Sagaing", 90000),
    (17.335, 96.481, 5.0, 1369, 1757, "Pegu / Bago (Hanthawaddy & Toungoo)", 150000),
    (18.940, 96.430, 4.5, 1510, 1860, "Toungoo / Ketumati", 40000),
    (20.596, 93.193, 5.0, 1430, 1785, "Mrauk-U (Arakan Capital)", 120000),
    (2.189, 102.250, 5.0, 1400, 1860, "Melaka / Malacca", 100000),
    (5.133, 97.200, 4.5, 1267, 1524, "Samudera Pasai (North Sumatra)", 25000),
    (5.548, 95.324, 5.0, 1496, 1860, "Banda Aceh / Kutaraja (Aceh Sultanate)", 90000),
    (4.890, 114.960, 4.5, 1368, 1860, "Kota Batu / Brunei", 35000),
    # --- AGE OF COMMERCE SULTANATES & COLONIAL TRANSITION ---
    (-6.890, 110.639, 4.5, 1475, 1860, "Demak & Kudus (Java Sultanate)", 45000),
    (-6.036, 106.154, 5.0, 1526, 1813, "Banten Lama (Banten Sultanate)", 100000),
    (-6.175, 106.827, 5.0, 1527, 1860, "Jayakarta / Batavia (Jakarta)", 150000),
    (-7.801, 110.365, 5.0, 1586, 1860, "Kotagede, Plered & Yogyakarta (Mataram)", 120000),
    (-7.567, 110.828, 5.0, 1680, 1860, "Kartasura & Surakarta (Mataram)", 110000),
    (-7.257, 112.752, 5.0, 1400, 1860, "Surabaya", 130000),
    (-6.967, 110.417, 4.5, 1476, 1860, "Semarang", 65000),
    (-6.706, 108.557, 4.5, 1445, 1860, "Cirebon", 50000),
    (-5.148, 119.433, 5.0, 1511, 1860, "Makassar / Somba Opu (Gowa-Tallo)", 100000),
    (0.790, 127.360, 4.5, 1257, 1860, "Ternate (Maluku Sultanate)", 25000),
    (0.680, 127.400, 4.5, 1300, 1860, "Tidore (Maluku Sultanate)", 20000),
    (-3.695, 128.181, 4.5, 1512, 1860, "Ambon / Victoria", 25000),
    (-4.525, 129.895, 4.0, 1400, 1860, "Banda Neira", 15000),
    (-3.319, 114.591, 4.5, 1526, 1860, "Banjarmasin (Banjar Sultanate)", 40000),
    (6.052, 121.002, 4.5, 1450, 1860, "Jolo (Sulu Sultanate)", 25000),
    (7.224, 124.246, 4.5, 1515, 1860, "Cotabato / Maguindanao", 22000),
    (17.575, 120.387, 4.0, 1572, 1860, "Vigan / Villa Fernandina", 18000),
    (10.720, 122.562, 4.5, 1566, 1860, "Iloilo / Arevalo", 35000),
    (15.880, 108.338, 4.5, 1595, 1860, "Hoi An / Faifo", 35000),
    (16.463, 107.590, 5.0, 1687, 1860, "Phu Xuan / Hue (Nguyen Capital)", 80000),
    (10.777, 106.701, 5.0, 1698, 1860, "Gia Dinh / Saigon", 100000),
    (11.860, 104.750, 4.5, 1528, 1866, "Longvek & Oudong (Post-Angkor Cambodia)", 35000),
    (11.556, 104.928, 5.0, 1434, 1860, "Chaktomuk / Phnom Penh", 50000),
    (13.756, 100.502, 5.0, 1767, 1860, "Thonburi & Bangkok (Rattanakosin)", 250000),
    (16.805, 96.156, 5.0, 1755, 1860, "Dagon / Yangon (Rangoon)", 100000),
    (21.900, 96.050, 5.0, 1783, 1860, "Amarapura & Mandalay (Konbaung)", 150000),
    (5.414, 100.329, 4.5, 1786, 1860, "George Town (Penang)", 45000),
    (1.290, 103.852, 5.0, 1300, 1860, "Temasek / Singapore", 80000),
    (-9.200, 124.370, 4.0, 1556, 1860, "Lifau (Oecusse, Portuguese Timor)", 8000),
    (-8.556, 125.560, 4.5, 1769, 1860, "Dili (Portuguese Timor Capital)", 15000),
  ]
  out = []
  for la, lo, wt, sy, ey, nm, mp in raw_sites:
    pw = assign_periods_by_span(sy, ey)
    if pw:
      out.append((la, lo, wt, pw, "mandala_scholarly_catalogue", True, mp))
  return out


def ingest_all_repositories():
  records = []  # (lat, lon, weight, [(pk, frac)], source_tag, is_sett, max_pop)
  source_stats = Counter()

  # --- REPO 1: SVEA c14_cleaned_dedup + p3k14c + austarch ---
  c14_base = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_c14bazAAR")
  for fn, tag in [
    ("c14_cleaned_dedup.csv", "c14bazAAR_dedup"),
    (os.path.join("raw_databases", "p3k14c.csv"), "p3k14c_radiocarbon"),
    (os.path.join("raw_databases", "austarch.csv"), "austarch_radiocarbon"),
  ]:
    fp = os.path.join(c14_base, fn)
    if not os.path.exists(fp):
      continue
    with open(fp, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        try:
          lat = float(row.get("lat") or row.get("Lat") or row.get("Latitude") or "")
          lon = float(row.get("lon") or row.get("Long") or row.get("Longitude") or "")
        except Exception:
          continue
        if not (-13.0 <= lat <= 31.0 and 89.0 <= lon <= 138.0):
          continue
        bp_s = row.get("c14age") or row.get("Age") or row.get("AGE") or ""
        try:
          bp = float(bp_s)
        except Exception:
          continue
        if bp < 50 or bp > 18000:
          continue
        cal_yr = int(round(1950 - bp * 1.07))
        pw = assign_periods_by_span(cal_yr - 180, cal_yr + 180)
        if pw:
          records.append((lat, lon, 1.8, pw, tag, True, 0))
          source_stats[tag] += 1

  # --- REPO 2: XRONOS Radiocarbon API (all 11 MANDALA states + frontier) ---
  for fn in sorted(os.listdir(RAW_DIR)):
    if not fn.startswith("xronos_") or not fn.endswith(".json"):
      continue
    try:
      data = json.load(open(os.path.join(RAW_DIR, fn), "r", encoding="utf-8"))
    except Exception:
      continue
    rows = data if isinstance(data, list) else (data.get("data") or data.get("results") or [])
    for r in rows:
      if not isinstance(r, dict):
        continue
      try:
        lat = float(r.get("lat") or r.get("latitude") or "")
        lon = float(r.get("lng") or r.get("lon") or r.get("longitude") or "")
        bp = float(r.get("bp") or r.get("c14age") or r.get("age") or "")
      except Exception:
        continue
      if not (-13.0 <= lat <= 31.0 and 89.0 <= lon <= 138.0) or bp < 50 or bp > 18000:
        continue
      cal_yr = int(round(1950 - bp * 1.07))
      pw = assign_periods_by_span(cal_yr - 180, cal_yr + 180)
      if pw:
        records.append((lat, lon, 1.8, pw, "xronos_radiocarbon", True, 0))
        source_stats["xronos_radiocarbon"] += 1

  # --- REPO 3: Pleiades Ancient World Gazetteer ---
  pl_p = os.path.join(RAW_DIR, "pleiades_southeast_asia.json")
  if os.path.exists(pl_p):
    for r in json.load(open(pl_p, "r", encoding="utf-8")):
      try:
        lat, lon = float(r["lat"]), float(r["lon"])
      except Exception:
        continue
      syr = int(float(r["minDate"])) if str(r.get("minDate") or "").lstrip("-").replace(".", "").isdigit() else -300
      eyr = int(float(r["maxDate"])) if str(r.get("maxDate") or "").lstrip("-").replace(".", "").isdigit() else 600
      pw = assign_periods_by_span(syr, eyr) or [("05_funan_pyu_dvaravati_champa", 1.0)]
      records.append((lat, lon, 2.2, pw, "pleiades_emporia", True, 3000))
      source_stats["pleiades_emporia"] += 1

  # --- REPO 4: Zenodo Open-Science SE Asian Archaeological Datasets ---
  for fn in sorted(os.listdir(RAW_DIR)):
    if not fn.startswith("zenodo_"):
      continue
    fp = os.path.join(RAW_DIR, fn)
    try:
      if fn.lower().endswith((".csv", ".tsv")):
        sep = "\t" if fn.lower().endswith(".tsv") else ","
        with open(fp, "r", encoding="utf-8", errors="replace") as fh:
          for row in csv.DictReader(fh, delimiter=sep):
            lk = {str(k or "").strip().lower(): v for k, v in row.items()}
            lat_s = lk.get("lat") or lk.get("latitude") or lk.get("y") or lk.get("decimal_latitude")
            lon_s = lk.get("lon") or lk.get("long") or lk.get("longitude") or lk.get("lng") or lk.get("x") or lk.get("decimal_longitude")
            if not lat_s or not lon_s:
              continue
            try:
              lat, lon = float(lat_s), float(lon_s)
            except Exception:
              continue
            if not (-13.0 <= lat <= 31.0 and 89.0 <= lon <= 138.0):
              continue
            bp_s = lk.get("c14age") or lk.get("age") or lk.get("bp") or lk.get("c14_age") or lk.get("cra")
            pw = []
            if bp_s:
              try:
                bp = float(bp_s)
                if 50 <= bp <= 18000:
                  yr = int(round(1950 - bp * 1.07))
                  pw = assign_periods_by_span(yr - 180, yr + 180)
              except Exception:
                pass
            if not pw:
              txt = " ".join(str(v) for v in lk.values())
              pw = classify_text_to_periods(txt) or [("02_neolithic_austronesian_dispersal", 0.5), ("04_iron_age_sa_huynh_early_pyu", 0.5)]
            records.append((lat, lon, 1.6, pw, "zenodo_open_archaeology", True, 0))
            source_stats["zenodo_open_archaeology"] += 1
      elif fn.lower().endswith(".geojson"):
        gj = json.load(open(fp, "r", encoding="utf-8", errors="replace"))
        for feat in gj.get("features", []):
          geom = feat.get("geometry") or {}
          coords = geom.get("coordinates")
          if geom.get("type") == "Point" and isinstance(coords, list) and len(coords) >= 2:
            lon, lat = float(coords[0]), float(coords[1])
            if -13.0 <= lat <= 31.0 and 89.0 <= lon <= 138.0:
              txt = json.dumps(feat.get("properties") or {})
              pw = classify_text_to_periods(txt) or [("07_angkor_pagan_dai_viet_kediri", 0.5), ("08_majapahit_sukhothai_early_ayutthaya", 0.5)]
              records.append((lat, lon, 1.6, pw, "zenodo_open_archaeology", True, 0))
              source_stats["zenodo_open_archaeology"] += 1
    except Exception:
      pass

  # --- REPO 5: Wikidata Institutional Heritage & Archaeological Registries (11 MANDALA countries) ---
  for fn in sorted(os.listdir(RAW_DIR)):
    if not fn.startswith("wikidata_arch_") or not fn.endswith(".json"):
      continue
    try:
      rows = json.load(open(os.path.join(RAW_DIR, fn), "r", encoding="utf-8"))
    except Exception:
      continue
    seen_q = set()
    for r in rows:
      qid = (r.get("item") or {}).get("value") or ""
      if qid in seen_q:
        continue
      seen_q.add(qid)
      lat, lon = parse_wd_coord((r.get("coord") or {}).get("value"))
      if lat is None or not (-13.0 <= lat <= 31.0 and 89.0 <= lon <= 138.0):
        continue
      inc = parse_wd_year((r.get("inception") or {}).get("value"))
      # API forensics: exclude clearly modern post-1885 buildings unless archaeological site
      lbl = (r.get("itemLabel") or {}).get("value") or ""
      tlbl = (r.get("typeLabel") or {}).get("value") or ""
      plbl = (r.get("periodLabel") or {}).get("value") or ""
      clbl = (r.get("cultureLabel") or {}).get("value") or ""
      hlbl = (r.get("heritageLabel") or {}).get("value") or ""
      txt = f"{lbl} {tlbl} {plbl} {clbl} {hlbl}"
      is_arch = any(k in txt.lower() for k in ("archaeolog", "ancient", "ruin", "candi", "prasat", "pyu", "angkor", "stupa", "cave", "megalith", "prehistoric", "dvaravati", "srivijaya", "majapahit", "champa", "dong son", "hoabinhian"))
      if inc is not None and inc > 1885 and not is_arch:
        continue
      pw = []
      if inc is not None and -15000 <= inc <= 1885:
        pw = assign_periods_by_span(inc, min(1860, inc + 250))
      if not pw:
        pw = classify_text_to_periods(txt)
      if not pw:
        # Dated/monumental heritage fallback strictly by type
        tl = tlbl.lower()
        if any(k in tl for k in ("cave", "rock", "megalith")):
          pw = [("01_palaeolithic_hoabinhian_toalean", 0.5), ("02_neolithic_austronesian_dispersal", 0.5)]
        elif any(k in tl for k in ("candi", "prasat", "ancient city", "archaeological site", "ruins")):
          pw = [("06_chenla_srivijaya_sailendra_mataram", 0.30), ("07_angkor_pagan_dai_viet_kediri", 0.40), ("08_majapahit_sukhothai_early_ayutthaya", 0.30)]
        elif any(k in tl for k in ("fort", "castle", "palace", "citadel")):
          pw = [("08_majapahit_sukhothai_early_ayutthaya", 0.25), ("09_sultanates_toungoo_le_nguyen_iberian", 0.45), ("10_late_precolonial_colonial_transition", 0.30)]
        elif any(k in tl for k in ("church", "cathedral", "mosque")):
          pw = [("09_sultanates_toungoo_le_nguyen_iberian", 0.45), ("10_late_precolonial_colonial_transition", 0.55)]
        else:
          pw = [("07_angkor_pagan_dai_viet_kediri", 0.25), ("08_majapahit_sukhothai_early_ayutthaya", 0.25), ("09_sultanates_toungoo_le_nguyen_iberian", 0.25), ("10_late_precolonial_colonial_transition", 0.25)]
      wt = 2.0 if "ancient city" in tlbl.lower() else (1.5 if is_arch else 0.9)
      records.append((lat, lon, wt, pw, f"wikidata_{fn[14:-5]}", is_arch, 0))
      source_stats["wikidata_national_heritage"] += 1

  # --- REPO 6: OSM Overpass Archaeological & Heritage Sites (12 SE Asian Tiles) ---
  for fn in sorted(os.listdir(RAW_DIR)):
    if not fn.startswith("osm_arch_") or not fn.endswith(".json"):
      continue
    try:
      els = json.load(open(os.path.join(RAW_DIR, fn), "r", encoding="utf-8"))
    except Exception:
      continue
    for el in els:
      lat, lon = el.get("lat"), el.get("lon")
      if lat is None or lon is None:
        continue
      h = str(el.get("historic") or "")
      st = str(el.get("site_type") or "")
      sd = str(el.get("start_date") or "")
      txt = f"{el.get('name','')} {el.get('name_local','')} {h} {st} {el.get('heritage','')} {sd} {el.get('religion','')}"
      m_yr = re.search(r"\b(19\d\d|20\d\d)\b", sd)
      if m_yr and h not in ("archaeological_site", "megalith", "tumulus"):
        continue
      pw = classify_text_to_periods(txt)
      if not pw:
        if h in ("megalith", "tumulus"):
          pw = [("03_bronze_age_dongson_banchiang", 0.5), ("04_iron_age_sa_huynh_early_pyu", 0.5)]
        elif h in ("archaeological_site", "ruins"):
          pw = [("05_funan_pyu_dvaravati_champa", 0.20), ("06_chenla_srivijaya_sailendra_mataram", 0.25), ("07_angkor_pagan_dai_viet_kediri", 0.30), ("08_majapahit_sukhothai_early_ayutthaya", 0.25)]
        elif h in ("fort", "citywalls", "castle", "palace"):
          pw = [("08_majapahit_sukhothai_early_ayutthaya", 0.20), ("09_sultanates_toungoo_le_nguyen_iberian", 0.45), ("10_late_precolonial_colonial_transition", 0.35)]
        else:
          pw = [("09_sultanates_toungoo_le_nguyen_iberian", 0.40), ("10_late_precolonial_colonial_transition", 0.60)]
      wt = 1.4 if h in ("archaeological_site", "citywalls", "megalith") else 0.85
      records.append((float(lat), float(lon), wt, pw, "osm_overpass_heritage", h in ("archaeological_site", "citywalls", "fort"), 0))
      source_stats["osm_overpass_heritage"] += 1

  # --- REPO 7: AADR v66 Ancient DNA (from JADE raw cache) ---
  anno_p = os.path.join(JADE_RAW, "aadr_v66.p1_1240K.aadr.PUB.anno")
  if os.path.exists(anno_p):
    seen_a = set()
    with open(anno_p, "r", encoding="utf-8", errors="replace") as fh:
      fh.readline()
      for line in fh:
        p = line.strip().split("\t")
        if len(p) <= 18:
          continue
        try:
          lat, lon, bp = float(p[17]), float(p[18]), float(p[10])
        except Exception:
          continue
        if not (-13.0 <= lat <= 31.0 and 89.0 <= lon <= 138.0):
          continue
        ka = (round(lat, 2), round(lon, 2), int(bp // 200))
        if ka in seen_a:
          continue
        seen_a.add(ka)
        yr = int(round(1950 - bp))
        pw = assign_periods_by_span(yr - 180, yr + 180)
        if pw:
          records.append((lat, lon, 2.2, pw, "aadr_v66_ancient_dna", True, 0))
          source_stats["aadr_v66_ancient_dna"] += 1

  # --- REPO 8 & 9: JADE Northern Frontier + INDUS Western Frontier Cross-Conditioning (Zero Border Cliffs!) ---
  jade_map = {
    "01_palaeolithic_early_neolithic_h1.geojson": [("01_palaeolithic_hoabinhian_toalean", 1.0)],
    "02_middle_neolithic_yangshao_h2.geojson": [("02_neolithic_austronesian_dispersal", 1.0)],
    "03_late_neolithic_longshan_h3.geojson": [("02_neolithic_austronesian_dispersal", 1.0)],
    "04_bronze_age_shang_zhou_h4.geojson": [("03_bronze_age_dongson_banchiang", 1.0)],
    "05_spring_autumn_warring_states_h5.geojson": [("04_iron_age_sa_huynh_early_pyu", 1.0)],
    "06_qin_han_xiongnu_h6.geojson": [("04_iron_age_sa_huynh_early_pyu", 0.5), ("05_funan_pyu_dvaravati_champa", 0.5)],
    "07_wei_jin_northern_southern_h7.geojson": [("05_funan_pyu_dvaravati_champa", 1.0)],
    "08_sui_tang_five_dynasties_h8.geojson": [("06_chenla_srivijaya_sailendra_mataram", 1.0)],
    "09_liao_song_jin_yuan_h9.geojson": [("07_angkor_pagan_dai_viet_kediri", 1.0)],
    "10_ming_qing_imperial_h10.geojson": [("08_majapahit_sukhothai_early_ayutthaya", 0.3), ("09_sultanates_toungoo_le_nguyen_iberian", 0.35), ("10_late_precolonial_colonial_transition", 0.35)],
  }
  for fn, pw in jade_map.items():
    fp = os.path.join(JADE_GJ, fn)
    if not os.path.exists(fp):
      continue
    for feat in json.load(open(fp, "r", encoding="utf-8")).get("features", []):
      coords = (feat.get("geometry") or {}).get("coordinates") or []
      if len(coords) >= 2:
        lon, lat = float(coords[0]), float(coords[1])
        if 18.0 <= lat <= 31.0 and 94.0 <= lon <= 114.0:
          cnt = float((feat.get("properties") or {}).get("site_count") or 0.0)
          if cnt > 0:
            records.append((lat, lon, min(cnt, 18.0), pw, "jade_yunnan_guangxi_frontier", True, 0))
            source_stats["jade_yunnan_guangxi_frontier"] += 1

  indus_map = {
    "01_palaeolithic_mesolithic_early_neolithic.geojson": [("01_palaeolithic_hoabinhian_toalean", 1.0)],
    "02_pre_harappan_chalcolithic_neolithic.geojson": [("02_neolithic_austronesian_dispersal", 1.0)],
    "04_late_harappan_vedic_megalithic.geojson": [("03_bronze_age_dongson_banchiang", 1.0)],
    "05_mahajanapadas_nanda_maurya.geojson": [("04_iron_age_sa_huynh_early_pyu", 1.0)],
    "07_gupta_vakataka_pallava_classical.geojson": [("05_funan_pyu_dvaravati_champa", 1.0)],
    "08_early_mediaeval_tripartite_chola.geojson": [("06_chenla_srivijaya_sailendra_mataram", 0.5), ("07_angkor_pagan_dai_viet_kediri", 0.5)],
    "09_sultanate_vijayanagara_regional.geojson": [("08_majapahit_sukhothai_early_ayutthaya", 1.0)],
    "10_mughal_maratha_early_colonial.geojson": [("09_sultanates_toungoo_le_nguyen_iberian", 0.5), ("10_late_precolonial_colonial_transition", 0.5)],
  }
  for fn, pw in indus_map.items():
    fp = os.path.join(INDUS_GJ, fn)
    if not os.path.exists(fp):
      continue
    for feat in json.load(open(fp, "r", encoding="utf-8")).get("features", []):
      coords = (feat.get("geometry") or {}).get("coordinates") or []
      if len(coords) >= 2:
        lon, lat = float(coords[0]), float(coords[1])
        if 19.0 <= lat <= 30.0 and 89.0 <= lon <= 97.5:
          cnt = float((feat.get("properties") or {}).get("site_count") or 0.0)
          if cnt > 0:
            records.append((lat, lon, min(cnt, 18.0), pw, "indus_assam_bengal_frontier", True, 0))
            source_stats["indus_assam_bengal_frontier"] += 1

  # --- REPO 10: Curated South-East Asian Scholarly Catalogue ---
  curated = build_curated_southeast_asia_catalogue()
  records.extend(curated)
  source_stats["mandala_scholarly_catalogue"] = len(curated)

  # Spatial-temporal deduplication (collapse identical coords within ~1 km per source class)
  dedup_map = {}
  for lat, lon, wt, pw, tag, is_sett, mpop in records:
    kd = (round(lat, 2), round(lon, 2), tag)
    if kd not in dedup_map:
      dedup_map[kd] = [lat, lon, wt, list(pw), tag, is_sett, mpop]
    else:
      dedup_map[kd][2] = min(16.0, dedup_map[kd][2] + wt * 0.35)
      dedup_map[kd][6] = max(dedup_map[kd][6], mpop)
  dedup_records = [tuple(v) for v in dedup_map.values()]

  print("\n[C] Multi-Repository Ingestion Breakdown (MANDALA):", flush=True)
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

  assigned_dom = 0
  assigned_fr = 0
  for i, r in enumerate(records):
    if dists_km[i] > 200.0:
      continue
    ci = int(idxs[i])
    lat, lon, wt, pw, src_tag, is_sett, mpop = r
    for pk, frac in pw:
      per_counts[pk][ci] += wt * frac
    total_raw[ci] += wt
    if is_sett:
      has_sett[ci] = True
    if mpop > max_pop[ci]:
      max_pop[ci] = mpop
    rr, cc = latlon_to_rc(lat, lon)
    if domain_mask[rr, cc]:
      cr, c_col = latlon_to_rc(catchments[ci]["lat"], catchments[ci]["lon"])
      if hyde_dens[rr, cc] >= 0.002 or ((rr - cr) ** 2 + (cc - c_col) ** 2) <= 25:
        doc_pixels.add(rr * GRID_W + cc)
      assigned_dom += 1
      if mpop >= 1000 or wt >= 2.0:
        doc_settlements.append({"lat": round(lat, 4), "lon": round(lon, 4), "weight": round(wt, 2), "max_pop": int(mpop)})
    else:
      assigned_fr += 1

  # Biome/Aridity/Canopy-conditioned Q75 + IQR taphonomic outlier shrinkage
  dom_mask_c = np.array([not c["is_frontier_buffer"] for c in catchments], dtype=bool)
  c_areas = np.array([c["area_km2"] for c in catchments], dtype=np.float64)
  c_hyde = np.array([hyde_dens[latlon_to_rc(c["lat"], c["lon"])] for c in catchments], dtype=np.float64)
  is_sparse = c_hyde < 4.0

  for pk in PERIOD_KEYS:
    vals = per_counts[pk]
    dens = vals / np.maximum(120.0, c_areas)
    # Tighter urban-heritage salvage shrinkage on Periods 09-10 where modern OSM/Wikidata mapping clusters heavily in colonial capitals
    is_late = pk in ("09_sultanates_toungoo_le_nguyen_iberian", "10_late_precolonial_colonial_transition")
    c_sp, c_dn = (0.9, 1.1) if is_late else (1.5, 2.5)
    for grp_mask, cap_mult in [(dom_mask_c & is_sparse, c_sp), (dom_mask_c & (~is_sparse), c_dn)]:
      pos = dens[grp_mask & (dens > 0)]
      if pos.size >= 15:
        q25, q75 = np.percentile(pos, [25, 75])
        iqr = max(1e-7, q75 - q25)
        cap = q75 + cap_mult * iqr
        excess = grp_mask & (dens > cap)
        if excess.any():
          shrunk = cap + iqr * np.log1p((dens[excess] - cap) / iqr)
          vals[excess] = shrunk * np.maximum(120.0, c_areas[excess])
    per_counts[pk] = vals

  # B2 Neighbour zero-hole imputation + late-period volunteer-survey-bias Empirical Bayes pooling
  k_nbr = min(11, n_c)
  ndists, nidxs = tree.query(c_xyz, k=k_nbr)
  for pk in PERIOD_KEYS:
    vals = per_counts[pk].copy()
    is_late = pk in ("09_sultanates_toungoo_le_nguyen_iberian", "10_late_precolonial_colonial_transition")
    hyde_thr = 1.2 if is_late else 2.5
    for ci in range(n_c):
      if vals[ci] > 0 or c_hyde[ci] < hyde_thr:
        continue
      nbrs = nidxs[ci, 1:]
      nvals = vals[nbrs]
      pos_n = nvals[nvals > 0]
      if pos_n.size >= 2:
        ndens = pos_n / np.maximum(120.0, c_areas[nbrs[nvals > 0]])
        vals[ci] = (0.55 if is_late else 0.42) * float(np.median(ndens)) * c_areas[ci]
    if is_late:
      # Empirical Bayes shrinkage toward local 6-neighbour median density to suppress OSM/Wikidata mapping patchiness nugget
      dens_arr = vals / np.maximum(120.0, c_areas)
      eb_vals = vals.copy()
      for ci in range(n_c):
        nbrs = nidxs[ci, 1:7]
        loc_med = float(np.median(dens_arr[nbrs]))
        w_eb = 0.52 if dens_arr[ci] > 0 else 0.65
        eb_dens = (1.0 - w_eb) * dens_arr[ci] + w_eb * loc_med
        eb_vals[ci] = eb_dens * np.maximum(120.0, c_areas[ci])
      vals = eb_vals
    per_counts[pk] = vals

  period_meta = []
  for p in PERIODS:
    pk = p["key"]
    feats = []
    dom_sum = 0.0
    dom_active = 0
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
          "region_id": c["region_id"],
          "area_km2": c["area_km2"],
          "site_count": round(cnt, 3),
          "total_sites_all_periods": round(float(total_raw[ci]), 2),
          "is_frontier_buffer": c["is_frontier_buffer"],
          "has_documented_settlement": bool(has_sett[ci]),
          "max_settlement_pop": int(max_pop[ci]),
          "period_key": pk
        }
      })
    with open(os.path.join(GJ_DIR, p["geojson_filename"]), "w", encoding="utf-8") as fh:
      json.dump({"type": "FeatureCollection", "features": feats}, fh)
    period_meta.append({
      "key": pk,
      "geojson_filename": p["geojson_filename"],
      "total_sites_count": int(round(dom_sum)),
      "active_domestic_catchments": dom_active,
    })
    print(f"  Exported {p['geojson_filename']}: dom_weighted={dom_sum:,.1f} | active_dom={dom_active}/{int(dom_mask_c.sum())}", flush=True)

  all_feats = []
  for ci, c in enumerate(catchments):
    all_feats.append({
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [round(c["lon"], 5), round(c["lat"], 5)]},
      "properties": {
        "region_id": c["region_id"],
        "area_km2": c["area_km2"],
        "site_count": round(float(total_raw[ci]), 2),
        "total_sites_all_periods": round(float(total_raw[ci]), 2),
        "is_frontier_buffer": c["is_frontier_buffer"],
        "has_documented_settlement": bool(has_sett[ci]),
        "max_settlement_pop": int(max_pop[ci])
      }
    })
  with open(os.path.join(GJ_DIR, "00_all_periods.geojson"), "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": all_feats}, fh)

  with open(os.path.join(CFG_DIR, "documented_site_pixels.json"), "w", encoding="utf-8") as fh:
    json.dump({"grid_width": GRID_W, "grid_height": GRID_H, "pixel_indices": sorted(doc_pixels)}, fh)

  with open(os.path.join(CFG_DIR, "documented_settlements.json"), "w", encoding="utf-8") as fh:
    json.dump({"count": len(doc_settlements), "settlements": doc_settlements}, fh)

  meta_obj = {
    "domain": "MANDALA",
    "macro_scope": "Mainland and Maritime South-East Asia (excl. West New Guinea)",
    "sources": list(source_stats.keys()),
    "source_record_counts": source_stats,
    "domestic_assigned_records": assigned_dom,
    "frontier_assigned_records": assigned_fr,
    "catchment_counts": {"domestic": int(dom_mask_c.sum()), "frontier_buffer": int((~dom_mask_c).sum())},
    "documented_site_pixels": len(doc_pixels),
    "period_geojsons": period_meta
  }
  with open(os.path.join(CFG_DIR, "sites_mandala_southeast_asia_geojson_metadata.json"), "w", encoding="utf-8") as fh:
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
    "geojson_metadata_filename": "config/sites_mandala_southeast_asia_geojson_metadata.json",
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
      "elevation_barrier_m": 500,
      "habitability_filter": {
        "arctic_lat_cut": 50.0,
        "extreme_elev_cut_m": 3800.0,
        "hyde_core_min_dens": 0.003,
        "hyde_marginal_min_dens": 0.14,
        "site_radius_px": 1.8,
        "stadester_max_first_year": 1860,
        "stadester_radius_px": 2.0
      },
      "hu_admixture_config": "histmap/3.data_transform/population_Substrata.viscount/config/mandala_dasymetric_admixture.json5",
      "residual_kriging_mode": "hu_hyde_residual",
      "covariate_paths": {
        "documented_settlements_json": "histmap/1.data_raw/population_regional/MANDALA/_shared/sites_mandala_southeast_asia/config/documented_settlements.json",
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/MANDALA/_shared/sites_mandala_southeast_asia/config/documented_site_pixels.json",
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
        "urban_mask_buffer_radius": 3,
        "urban_mask_inpaint_radius": 6,
        "urban_uopp_threshold": 3.8
      },
      "dimensionless_lag_bins": [0.85, 1.45, 2.10, 2.95, 4.10, 5.60, 7.80, 10.80, 14.50],
      "domain_mask_png": "histmap/1.data_raw/population_regional/MANDALA/_shared/sites_mandala_southeast_asia/config/mandala_domain_mask.png",
      "earth_radius_km": 6371,
      "frontier_conditioning_max_dist_km": 300,
      "grid_height": GRID_H,
      "grid_width": GRID_W,
      "target_domestic_catchments": int(dom_mask_c.sum()),
      "chronological_horizons": [
        {"active_periods": [p["key"]], "key": p["key"] + "_horizon", "year": p["representative_year"]}
        for p in PERIODS
      ]
    },
    "periods": PERIODS
  }
  with open(os.path.join(CFG_DIR, "sites_mandala_southeast_asia.json5"), "w", encoding="utf-8") as fh:
    json.dump(cfg_obj, fh, indent=2, ensure_ascii=False)

  print(f"\n[D] Completed MANDALA multi-repository extraction: {assigned_dom:,} domestic + {assigned_fr:,} frontier records across {len(doc_pixels):,} documented pixels.", flush=True)


if __name__ == "__main__":
  domain_mask, land_area = load_domain_and_land()
  catchments = build_catchments(domain_mask, land_area)
  records, source_stats = ingest_all_repositories()
  aggregate_and_export(domain_mask, land_area, catchments, records, source_stats)
