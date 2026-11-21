"""Stage C Multi-Repository Archaeological & Historical Site Composite Extractor for Project INDUS.

Builds the 4320x2160 INDUS domain land mask (India, Pakistan, Bangladesh, Sri Lanka, Nepal,
Bhutan, Maldives incl. Andaman & Nicobar and Lakshadweep micro-islands), discretises INDUS
+ a 300 km cross-frontier conditioning belt into scale-adaptive HydroBASINS Level 6 catchments
(<= 25,000 km2), ingests and deduplicates 13 primary archaeological/institutional repositories
across 10 Holocene-to-Early-Modern horizons (-10000 to 1800 AD) with API forensics, applies
monument-class weighting and biome/aridity-conditioned Q75 + IQR taphonomic shrinkage plus
B2 settled-belt neighbour imputation, and exports ViscountMaternKriging-ready GeoJSONs and
configuration manifests.
"""

import csv
import io
import json
import math
import os
import re
import zipfile
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import shapefile
from PIL import Image
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from shapely.geometry import Point, shape
from shapely.prepared import prep

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
INDUS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "INDUS")
DOMAIN_DIR = os.path.join(INDUS_DIR, "_shared", "sites_indus_south_asia")
RAW_DIR = os.path.join(DOMAIN_DIR, "0.raw_data")
CFG_DIR = os.path.join(DOMAIN_DIR, "config")
GJ_DIR = os.path.join(DOMAIN_DIR, "geojson")
JADE_RAW_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "sites_east_asia", "0.raw_data")
JADE_GIS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "_gis_cache")
JADE_GJ_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "sites_east_asia", "geojson")
SHARED_GIS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared", "_gis_cache")

os.makedirs(CFG_DIR, exist_ok=True)
os.makedirs(GJ_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160
EARTH_R_KM = 6371.0

# 10 Chronological Horizons calibrated to South Asian Prehistory & History
PERIODS = [
  {
    "epoch_id": 1, "key": "01_palaeolithic_mesolithic_early_neolithic",
    "filename": "01_palaeolithic_mesolithic_early_neolithic.png",
    "geojson_filename": "01_palaeolithic_mesolithic_early_neolithic.geojson",
    "approx_start_year": -13000, "approx_end_year": -5000, "representative_year": -7500,
    "name_en": "Late Palaeolithic, Mesolithic and Early Neolithic",
    "name_de": "Spätpaläolithikum, Mesolithikum und Frühneolithikum",
    "name_fr": "Paléolithique final, Mésolithique et Néolithique ancien",
    "date_range_en": "c. 13000-5000BC (Bhimbetka, Belan Valley, Mehrgarh I-II, Lahuradewa and Balangoda)"
  },
  {
    "epoch_id": 2, "key": "02_pre_harappan_chalcolithic_neolithic",
    "filename": "02_pre_harappan_chalcolithic_neolithic.png",
    "geojson_filename": "02_pre_harappan_chalcolithic_neolithic.geojson",
    "approx_start_year": -5000, "approx_end_year": -2600, "representative_year": -3500,
    "name_en": "Pre-Harappan, Early Indus and Regional Neolithic",
    "name_de": "Vor-Harappa-, Früh-Indus- und Regionalneolithikum",
    "name_fr": "Pré-Harappéen, Indus ancien et Néolithique régional",
    "date_range_en": "c. 5000-2600BC (Kot Diji, Amri-Nal, Hakra, Sothi-Siswal, Burzahom, Chirand and Ashmound Neolithic)"
  },
  {
    "epoch_id": 3, "key": "03_mature_harappan_indus_urban",
    "filename": "03_mature_harappan_indus_urban.png",
    "geojson_filename": "03_mature_harappan_indus_urban.geojson",
    "approx_start_year": -2600, "approx_end_year": -1900, "representative_year": -2200,
    "name_en": "Mature Harappan Urbanism and Peninsular Chalcolithic",
    "name_de": "Reife Harappa-Urbanisierung und Chalkolithikum",
    "name_fr": "Urbanisme harappéen mature et Chalcolithique péninsulaire",
    "date_range_en": "c. 2600-1900BC (Mohenjo-daro, Harappa, Rakhigarhi, Dholavira, Ganweriwala, Kalibangan, Lothal and Ahar-Banas)"
  },
  {
    "epoch_id": 4, "key": "04_late_harappan_vedic_megalithic",
    "filename": "04_late_harappan_vedic_megalithic.png",
    "geojson_filename": "04_late_harappan_vedic_megalithic.geojson",
    "approx_start_year": -1900, "approx_end_year": -600, "representative_year": -1200,
    "name_en": "Late Harappan, Vedic PGW and Iron Age Megalithic",
    "name_de": "Spät-Harappa-, Vedische PGW- und Megalithzeit",
    "name_fr": "Harappéen tardif, Védique PGW et Mégalithique de l'Âge du Fer",
    "date_range_en": "c. 1900-600BC (Cemetery H, Jorwe, Malwa, OCP, Painted Grey Ware, Gandhara Grave and South Indian Megaliths)"
  },
  {
    "epoch_id": 5, "key": "05_mahajanapadas_nanda_maurya",
    "filename": "05_mahajanapadas_nanda_maurya.png",
    "geojson_filename": "05_mahajanapadas_nanda_maurya.geojson",
    "approx_start_year": -600, "approx_end_year": -185, "representative_year": -300,
    "name_en": "Mahajanapadas, Nanda and Maurya Empires",
    "name_de": "Mahajanapadas, Nanda- und Maurya-Reiche",
    "name_fr": "Mahajanapadas, Empires Nanda et Maurya",
    "date_range_en": "c. 600-185BC (Second Urbanisation, NBPW, Pataliputra, Taxila, Ujjayini, Sisupalgarh, Mahasthangarh and Anuradhapura)"
  },
  {
    "epoch_id": 6, "key": "06_indo_greek_kushan_satavahana_sangam",
    "filename": "06_indo_greek_kushan_satavahana_sangam.png",
    "geojson_filename": "06_indo_greek_kushan_satavahana_sangam.geojson",
    "approx_start_year": -185, "approx_end_year": 320, "representative_year": 100,
    "name_en": "Indo-Greek, Kushan, Satavahana and Sangam Tamilakam",
    "name_de": "Indo-Griechische, Kuschan-, Satavahana- und Sangam-Zeit",
    "name_fr": "Époques indo-grecque, kouchane, satavahana et Sangam",
    "date_range_en": "185BC-320AD (Greco-Roman emporia, Muziris, Arikamedu, Barygaza, Gandhara, Mathura, Amaravati and Tissamaharama)"
  },
  {
    "epoch_id": 7, "key": "07_gupta_vakataka_pallava_classical",
    "filename": "07_gupta_vakataka_pallava_classical.png",
    "geojson_filename": "07_gupta_vakataka_pallava_classical.geojson",
    "approx_start_year": 320, "approx_end_year": 750, "representative_year": 550,
    "name_en": "Gupta, Vakataka, Pushyabhuti and Pallava Classical Era",
    "name_de": "Klassische Gupta-, Vakataka- und Pallava-Epoche",
    "name_fr": "Époque classique Gupta, Vakataka et Pallava",
    "date_range_en": "320-750AD (Imperial and Later Guptas, Kannauj, Valabhi, Licchavi Nepal, Kanchipuram, Badami and Sigiriya)"
  },
  {
    "epoch_id": 8, "key": "08_early_mediaeval_tripartite_chola",
    "filename": "08_early_mediaeval_tripartite_chola.png",
    "geojson_filename": "08_early_mediaeval_tripartite_chola.geojson",
    "approx_start_year": 750, "approx_end_year": 1206, "representative_year": 1000,
    "name_en": "Early Mediaeval Tripartite States and Imperial Cholas",
    "name_de": "Frühmittelalterliche Staaten und Chola-Reich",
    "name_fr": "États du haut Moyen Âge et Empire Chola",
    "date_range_en": "750-1206AD (Pratihara, Pala-Sena, Rashtrakuta, Imperial Chola, Hoysala, Kakatiya, Rajput, Polonnaruwa and Maldives)"
  },
  {
    "epoch_id": 9, "key": "09_sultanate_vijayanagara_regional",
    "filename": "09_sultanate_vijayanagara_regional.png",
    "geojson_filename": "09_sultanate_vijayanagara_regional.geojson",
    "approx_start_year": 1206, "approx_end_year": 1526, "representative_year": 1400,
    "name_en": "Delhi Sultanate, Regional Sultanates and Vijayanagara",
    "name_de": "Sultanat von Delhi, Regionalsultanate und Vijayanagara",
    "name_fr": "Sultanat de Delhi, sultanats régionaux et Vijayanagara",
    "date_range_en": "1206-1526AD (Delhi, Bengal, Gujarat, Malwa, Bahmani, Vijayanagara, Gajapati, Samma Sindh, Malla Nepal and Kotte)"
  },
  {
    "epoch_id": 10, "key": "10_mughal_maratha_early_colonial",
    "filename": "10_mughal_maratha_early_colonial.png",
    "geojson_filename": "10_mughal_maratha_early_colonial.geojson",
    "approx_start_year": 1526, "approx_end_year": 1800, "representative_year": 1650,
    "name_en": "Mughal Empire, Maratha Confederacy and Early Colonial Ports",
    "name_de": "Mogulreich, Marathen-Konföderation und frühe Kolonialhäfen",
    "name_fr": "Empire moghol, Confédération marathe et comptoirs coloniaux",
    "date_range_en": "1526-1800AD (Mughal Subahs, Maratha, Nayaka, Mysore, Travancore, Shah Nepal, Drukpa Bhutan and European factories)"
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
  if end_yr < -15000 or start_yr > 1830:
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
    if 1800 < mid <= 1857:
      return [(PERIODS[-1]["key"], 1.0)]
    return []
  tot = sum(w for _, w in hits)
  return [(k, w / tot) for k, w in hits]


def classify_text_to_periods(text):
  """Periodises archaeological descriptions/titles using South Asian scholarly terminology."""
  s = (text or "").lower()
  if not s:
    return []
  # Check explicit numeric year ranges / centuries first
  m_bc = re.findall(r"(\d{3,5})\s*(?:bc|bce|b\.c\.)", s)
  if m_bc:
    yrs = [-int(x) for x in m_bc if 50 <= int(x) <= 15000]
    if yrs:
      return assign_periods_by_span(min(yrs), max(yrs))
  m_ad = re.findall(r"(?:ad|ce)\s*(\d{3,4})|(\d{3,4})\s*(?:ad|ce)", s)
  yrs_ad = [int(a or b) for a, b in m_ad if 1 <= int(a or b) <= 1820]
  if yrs_ad:
    return assign_periods_by_span(min(yrs_ad), max(yrs_ad))
  m_c_bc = re.search(r"(\d{1,2})(?:st|nd|rd|th)\s+century\s+(?:bc|bce)", s)
  if m_c_bc:
    c = int(m_c_bc.group(1))
    return assign_periods_by_span(-c * 100, -(c - 1) * 100)
  m_c_ad = re.search(r"(\d{1,2})(?:st|nd|rd|th)\s+century(?:\s+(?:ad|ce))?", s)
  if m_c_ad:
    c = int(m_c_ad.group(1))
    if 1 <= c <= 18:
      return assign_periods_by_span((c - 1) * 100, c * 100)

  hits = []
  kw_rules = [
    (["palaeolithic", "paleolithic", "acheulean", "microlith", "mesolithic", "rock shelter", "rock art", "balangoda", "soanian"], "01_palaeolithic_mesolithic_early_neolithic"),
    (["neolithic", "ashmound", "mehrgarh", "pre-harappan", "early harappan", "kot diji", "hakra", "amri", "nal ", "sothi", "siswal", "burzahom"], "02_pre_harappan_chalcolithic_neolithic"),
    (["harappan", "indus valley", "indus civilization", "indus civilisation", "mohenjo", "dholavira", "lothal", "rakhigarhi", "kalibangan", "chalcolithic", "ahar", "banas", "kayatha"], "03_mature_harappan_indus_urban"),
    (["late harappan", "vedic", "painted grey ware", "pgw", "ochre coloured", "ocp", "megalith", "dolmen", "cairn", "menhir", "urn burial", "iron age", "jorwe", "malwa", "gandhara grave"], "04_late_harappan_vedic_megalithic"),
    (["mahajanapada", "maurya", "mauryan", "ashoka", "asoka", "nanda", "nbpw", "northern black polished", "buddhist stupa", "early historic", "punch-marked"], "05_mahajanapadas_nanda_maurya"),
    (["indo-greek", "kushan", "kushana", "satavahana", "sangam", "gandhara", "roman", "indo-roman", "kshatrapa", "shaka", "saka", "greco", "chaitya", "vihara", "rock-cut cave", "stupa"], "06_indo_greek_kushan_satavahana_sangam"),
    (["gupta", "vakataka", "pallava", "chalukya", "kadamba", "maitraka", "pushyabhuti", "harsha", "licchavi", "anuradhapura", "sigiriya", "kamarupa", "gauda"], "07_gupta_vakataka_pallava_classical"),
    (["chola", "pala ", "sena ", "pratihara", "rashtrakuta", "hoysala", "kakatiya", "chandella", "paramara", "solanki", "rajput", "pandya", "polonnaruwa", "early medieval", "early mediaeval", "stepwell", "baori", "vav"], "08_early_mediaeval_tripartite_chola"),
    (["sultanate", "vijayanagara", "bahmani", "tughlaq", "khalji", "lodi", "mamluk", "slave dynasty", "gajapati", "samma", "malla ", "kotte", "jaffna kingdom", "medieval", "mediaeval"], "09_sultanate_vijayanagara_regional"),
    (["mughal", "maratha", "nayaka", "nayak", "mysore", "travancore", "portuguese", "dutch", "voc ", "east india company", "fort ", "citadel", "palace", "mosque", "tomb", "mausoleum", "sarai", "kos minar", "shah ", "dzong", "ahom", "sikh"], "10_mughal_maratha_early_colonial"),
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
  if not m:
    return None
  return int(m.group(1))


def build_indus_domain_mask():
  """Builds 4320x2160 INDUS land mask from geocodes.png + Maldives/Andaman/Lakshadweep micro-islands."""
  geo_path = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "admin_modern", "geocodes.png")
  la_path = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
  geo = np.asarray(Image.open(geo_path).convert("RGBA"), dtype=np.uint8)
  la_raw = np.asarray(Image.open(la_path).convert("RGBA"), dtype=np.uint8)
  la = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2])

  # BGD (91,173,100), BTN (155,134,122), IND (214,144,83), LKA (134,131,100), NPL (191,130,140), PAK (22,144,83)
  target_rgbs = [
    (91, 173, 100),
    (155, 134, 122),
    (214, 144, 83),
    (134, 131, 100),
    (191, 130, 140),
    (22, 144, 83),
  ]
  mask = np.zeros((GRID_H, GRID_W), dtype=bool)
  for r, g, b in target_rgbs:
    mask |= (geo[:, :, 3] > 0) & (geo[:, :, 0] == r) & (geo[:, :, 1] == g) & (geo[:, :, 2] == b)

  # Ensure Maldives atolls (not painted in geocodes.png) + Lakshadweep + Andaman & Nicobar micro-islands are present
  micro_island_anchors = [
    # Maldives atolls (North to South: Haa Alif down to Addu)
    (6.95, 73.00), (6.62, 73.07), (6.15, 73.28), (5.83, 73.40), (5.65, 72.95),
    (5.11, 73.07), (5.44, 73.36), (4.175, 73.509), (3.85, 72.95), (3.48, 73.42),
    (2.94, 72.96), (2.78, 73.57), (2.21, 73.12), (1.92, 73.54), (0.53, 73.00),
    (0.28, 73.43), (-0.298, 73.424), (-0.641, 73.158),
    # Lakshadweep
    (10.57, 72.64), (11.12, 72.73), (10.83, 72.19), (8.28, 73.05),
    # Andaman & Nicobar
    (13.25, 92.95), (12.50, 92.85), (11.62, 92.73), (10.72, 92.52), (9.17, 92.78), (7.02, 93.80),
  ]
  for lat_m, lon_m in micro_island_anchors:
    rr, cc = latlon_to_rc(lat_m, lon_m)
    if la[rr, cc] > 0:
      mask[rr, cc] = True
    else:
      # Snap to nearest land_area > 0 pixel within 2 px if coastal, else pin pixel directly for Maldives
      found = False
      for dr in range(-2, 3):
        for dc in range(-2, 3):
          if 0 <= rr + dr < GRID_H and 0 <= cc + dc < GRID_W and la[rr + dr, cc + dc] > 0:
            mask[rr + dr, cc + dc] = True
            found = True
      if not found:
        mask[rr, cc] = True

  # Also union Maldives polygons from ne_10m_admin_0_countries.geojson
  ne0 = json.load(open(os.path.join(SHARED_GIS_DIR, "ne_10m_admin_0_countries.geojson"), "r", encoding="utf-8"))
  for feat in ne0.get("features", []):
    adm = str((feat.get("properties") or {}).get("ADMIN") or "")
    if adm == "Maldives":
      geom = shape(feat["geometry"])
      b = geom.bounds
      r0, c0 = latlon_to_rc(b[3], b[0])
      r1, c1 = latlon_to_rc(b[1], b[2])
      for rr in range(max(0, r0 - 1), min(GRID_H, r1 + 2)):
        for cc in range(max(0, c0 - 1), min(GRID_W, c1 + 2)):
          if la[rr, cc] > 0:
            mask[rr, cc] = True

  # Keep domestic continental pixels strictly on land_area > 0 (except pinned Maldives atoll pixels)
  maldives_band = np.zeros_like(mask)
  r_m0, c_m0 = latlon_to_rc(7.5, 72.3)
  r_m1, c_m1 = latlon_to_rc(-1.0, 74.0)
  maldives_band[r_m0:r_m1 + 1, c_m0:c_m1 + 1] = True
  mask = (mask & (la > 0)) | (mask & maldives_band)

  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  rgba[mask] = [255, 255, 255, 255]
  out_png = os.path.join(CFG_DIR, "indus_domain_mask.png")
  Image.fromarray(rgba, mode="RGBA").save(out_png)
  rs, cs = np.where(mask)
  print(f"[A] Built indus_domain_mask.png: {int(mask.sum()):,} pixels | rows {rs.min()}..{rs.max()}, cols {cs.min()}..{cs.max()} | area={float(la[mask].sum()):,.0f} km2", flush=True)
  return mask, la


def build_catchments(domain_mask, land_area):
  """Builds scale-adaptive HydroBASINS Level 6 catchments inside INDUS + 300 km cross-frontier belt."""
  dist_px = distance_transform_edt(~domain_mask)
  in_frontier_band = (~domain_mask) & (dist_px <= 44.0) & (land_area > 0)

  hyb_zip = os.path.join(JADE_GIS_DIR, "hybas_as_lev06_v1c.zip")
  catchments = []
  with zipfile.ZipFile(hyb_zip) as zf:
    sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
    fields = [f[0] for f in sf.fields[1:]]
    idx_id = fields.index("HYBAS_ID")
    idx_area = fields.index("SUB_AREA")

    for sr in sf.iterShapeRecords():
      bb = sr.shape.bbox
      # South Asia + 300 km belt bbox (lat -1.5..41, lon 57..102)
      if bb[2] < 57.0 or bb[0] > 102.0 or bb[3] < -1.5 or bb[1] > 41.0:
        continue
      geom = shape(sr.shape.__geo_interface__)
      if geom.is_empty:
        continue
      rep = geom.representative_point()
      lon, lat = float(rep.x), float(rep.y)
      area_km2 = max(150.0, float(sr.record[idx_area] or 1000.0))
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

      # Split mega-basins (> 25,000 km2) into sub-catchments (~1.35 deg)
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
                sub_pts.append((la_s, lo_s, bool(domain_mask[rr, cc])))
        if len(sub_pts) >= 2:
          sub_area = area_km2 / len(sub_pts)
          for j, (la_s, lo_s, sub_dom_flag) in enumerate(sub_pts):
            catchments.append({
              "region_id": f"hyb_{sr.record[idx_id]}_s{j}",
              "lat": la_s, "lon": lo_s,
              "area_km2": round(sub_area, 1),
              "is_frontier_buffer": not sub_dom_flag,
              "xyz": latlon_to_xyz(la_s, lo_s),
            })
          continue

      catchments.append({
        "region_id": f"hyb_{sr.record[idx_id]}",
        "lat": lat, "lon": lon,
        "area_km2": round(area_km2, 1),
        "is_frontier_buffer": not is_dom,
        "xyz": latlon_to_xyz(lat, lon),
      })

  # Dedicated island & archipelago catchments (Maldives, Lakshadweep, Andaman, Nicobar, Sri Lanka Jaffna/Ruhuna)
  island_anchors = [
    ("indus_maldives_north", 6.15, 73.28, 120.0),
    ("indus_maldives_central_male", 4.175, 73.509, 100.0),
    ("indus_maldives_south_laamu_addu", 0.53, 73.15, 110.0),
    ("indus_lakshadweep", 10.57, 72.64, 100.0),
    ("indus_andaman_north_middle", 12.60, 92.85, 3200.0),
    ("indus_andaman_south", 11.62, 92.73, 2800.0),
    ("indus_nicobar", 7.80, 93.50, 1800.0),
  ]
  for rid, la_i, lo_i, ar_i in island_anchors:
    catchments.append({
      "region_id": rid, "lat": la_i, "lon": lo_i,
      "area_km2": ar_i, "is_frontier_buffer": False,
      "xyz": latlon_to_xyz(la_i, lo_i),
    })

  dom_n = sum(1 for c in catchments if not c["is_frontier_buffer"])
  fr_n = len(catchments) - dom_n
  print(f"[B] Built scale-adaptive HydroBASINS catchments: {dom_n} domestic + {fr_n} frontier buffer = {len(catchments)} total", flush=True)
  return catchments


def build_curated_south_asia_catalogue():
  """Scholarly South Asian archaeological complexes from Possehl (1999), Mughal (1997),
  Green & Petrie (2018), Chakrabarti (2001), Moorti (1994), Fuller (2006), Coningham,
  Deraniyagala, Olivieri, Jarrige, Rahman, Tiwari & Naseema Mohamed."""
  # Format: (lat, lon, weight, start_yr, end_yr, name, max_pop)
  sites = [
    # --- PALAEOLITHIC / MESOLITHIC / EARLY NEOLITHIC ---
    (22.939, 77.612, 3.5, -13000, -1500, "Bhimbetka Rock Shelters", 400),
    (29.383, 67.617, 5.0, -7000, -2500, "Mehrgarh", 4000),
    (29.340, 67.590, 3.5, -2800, -1900, "Nausharo", 2500),
    (29.400, 67.640, 3.0, -2500, -1800, "Sibri & Pirak", 2000),
    (26.767, 82.967, 4.0, -7000, -1000, "Lahuradewa", 1200),
    (24.900, 82.067, 3.5, -8000, -2000, "Koldihwa & Mahagara (Belan Valley)", 800),
    (24.920, 82.080, 3.0, -10000, -4000, "Chopani Mando", 500),
    (26.017, 82.183, 3.5, -9000, -4500, "Damdama & Mahadaha & Sarai Nahar Rai", 600),
    (24.533, 82.317, 3.0, -12000, -5000, "Baghor (Son Valley)", 400),
    (13.230, 79.888, 3.0, -13000, -5000, "Attirampakkam (Kortallayar Basin)", 300),
    (15.320, 78.130, 3.0, -13000, -4000, "Jwalapuram (Jurreru Valley)", 300),
    (16.450, 76.520, 3.0, -13000, -4000, "Hunsgi-Baichbal Valley", 400),
    (25.358, 74.383, 3.5, -5500, -1500, "Bagor (Rajasthan)", 500),
    (23.450, 72.533, 3.0, -6000, -2000, "Langhnaj (Gujarat)", 400),
    (20.320, 75.000, 3.0, -13000, -6000, "Patne (Maharashtra)", 300),
    (34.470, 72.180, 3.0, -12000, -4000, "Sanghao Cave (Gandhara)", 300),
    (6.770, 80.370, 3.5, -13000, -3000, "Batadomba-lena & Beli-lena (Sri Lanka)", 400),
    (6.647, 80.220, 3.5, -13000, -3500, "Fa-Hien Lena (Pahiyangala)", 400),
    (8.620, 77.950, 2.5, -8000, -3000, "Teri Sites (Sawyerpuram, Tamil Nadu)", 300),
    (34.174, 74.878, 4.0, -3000, -1000, "Burzahom (Kashmir Neolithic)", 1200),
    (33.890, 75.020, 3.5, -2800, -1000, "Gufkral (Kashmir Neolithic)", 900),
    (25.733, 84.822, 4.0, -3500, -300, "Chirand (Saran, Bihar)", 1800),
    (25.630, 85.420, 3.0, -3000, -500, "Chechar-Kutubpur (Vaishali)", 1000),
    (24.930, 83.930, 3.5, -2500, -500, "Senuwar (Rohtas)", 1000),
    (25.430, 93.020, 3.0, -4000, -1000, "Daojali Hading (Assam Neolithic)", 500),
    (22.000, 86.720, 3.0, -3500, -1000, "Kuchai (Odisha Neolithic)", 500),
    (22.100, 87.300, 3.0, -3000, -800, "Pandu Rajar Dhibi (Bengal)", 1200),
    (23.580, 87.670, 3.0, -2500, -500, "Mahisdal & Mangalkot (Bengal)", 1000),

    # --- MATURE & EARLY HARAPPAN / INDUS VALLEY (Possehl 1999, Mughal 1997, Green & Petrie 2018) ---
    (27.329, 68.139, 5.0, -2600, -1700, "Mohenjo-daro", 40000),
    (30.629, 72.864, 5.0, -3300, -1300, "Harappa", 35000),
    (29.289, 76.113, 5.0, -4500, -1800, "Rakhigarhi", 35000),
    (28.720, 71.190, 5.0, -2600, -1900, "Ganweriwala (Cholistan)", 25000),
    (23.887, 70.214, 5.0, -3000, -1450, "Dholavira (Kachchh)", 20000),
    (29.474, 74.130, 4.5, -3200, -1800, "Kalibangan (Ghaggar)", 12000),
    (22.522, 72.249, 4.5, -2400, -1700, "Lothal (Gujarat)", 10000),
    (29.598, 75.392, 4.0, -3000, -1700, "Banawali (Haryana)", 8000),
    (29.555, 75.550, 4.0, -4500, -1900, "Bhirrana (Haryana)", 6000),
    (29.622, 75.656, 3.5, -4000, -2200, "Kunal (Haryana)", 3500),
    (29.042, 76.310, 4.0, -2600, -1900, "Farmana (Rohtak)", 6000),
    (28.887, 76.178, 3.5, -2800, -1500, "Mitathal & Siswal", 4500),
    (25.883, 68.317, 4.0, -2600, -1600, "Chanhudaro (Sindh)", 8000),
    (27.367, 68.709, 4.0, -3300, -1900, "Kot Diji (Sindh)", 7000),
    (26.170, 67.920, 4.0, -3600, -1800, "Amri (Sindh)", 5000),
    (31.970, 70.790, 4.5, -3300, -1900, "Rehman Dheri (Gomal Plain)", 12000),
    (32.020, 70.850, 3.5, -3500, -2000, "Gumla & Lewan & Tarakai Qila", 3500),
    (25.190, 61.920, 3.5, -2600, -1900, "Sutkagen Dor (Makran)", 3000),
    (25.250, 63.480, 3.5, -2600, -1900, "Sotka Koh (Makran)", 2500),
    (25.470, 66.680, 4.0, -3000, -1900, "Balakot (Las Bela)", 4000),
    (24.900, 67.320, 3.5, -2500, -1900, "Allahdino (Karachi)", 2000),
    (23.610, 70.920, 4.0, -2400, -1700, "Surkotada (Kachchh)", 4000),
    (23.440, 69.250, 3.5, -2500, -1900, "Desalpur & Shikarpur & Khirsara", 3500),
    (22.280, 71.140, 4.0, -2400, -1600, "Rojdi & Rangpur (Saurashtra)", 5000),
    (21.740, 70.450, 3.5, -2600, -1700, "Padri & Kuntasi & Bagasra", 3500),
    (24.160, 72.180, 3.5, -2600, -1700, "Nagwada & Loteshwar (North Gujarat)", 2500),
    (30.970, 76.530, 4.0, -2400, -500, "Rupar / Ropar (Sutlej)", 5000),
    (32.890, 74.730, 3.5, -2400, -1500, "Manda (Akhnoor, Jammu)", 2500),
    (29.000, 77.480, 3.5, -2200, -1000, "Alamgirpur & Hulas & Sanauli (Upper Doab)", 3500),
    (28.550, 71.300, 4.0, -3500, -1700, "Cholistan Central Hakra Cluster (Mughal 1997)", 8000),
    (29.150, 72.250, 4.0, -3500, -1700, "Cholistan Fort Abbas Hakra Cluster", 7000),
    (28.180, 70.720, 3.5, -3200, -1800, "Cholistan Derawar-Kudwala Cluster", 5000),
    (27.720, 66.330, 3.5, -3500, -1900, "Nal / Sohr Damb (Balochistan)", 3000),
    (26.150, 66.220, 3.5, -2800, -1900, "Kulli & Nindowari (Balochistan)", 3500),
    (30.180, 66.990, 3.5, -3800, -1900, "Kili Gul Mohammad & Damb Sadaat (Quetta)", 3000),
    (26.000, 63.050, 3.5, -4000, -1900, "Miri Qalat & Shahi Tump (Kech-Makran)", 3000),
    (30.200, 71.470, 4.0, -3000, 1800, "Multan / Jalilpur (Ravi-Chenab)", 15000),
    (31.550, 74.340, 4.5, -1000, 1800, "Lahore (Ravi)", 30000),
    (24.580, 73.710, 4.0, -3000, -1400, "Ahar & Balathal & Gilund (Mewar)", 4500),
    (27.670, 75.820, 3.5, -3000, -1800, "Ganeshwar-Jodhpura Copper Belt", 3500),
    (23.260, 75.950, 3.5, -2400, -1300, "Kayatha & Nagda (Malwa)", 3000),
    (22.170, 75.600, 4.0, -2000, -1000, "Navdatoli & Maheshwar (Narmada)", 4000),
    (24.090, 78.170, 3.5, -2000, 600, "Eran (Madhya Pradesh)", 4000),
    (19.517, 74.667, 4.5, -2200, -1000, "Daimabad (Godavari-Pravara)", 5000),
    (18.620, 74.510, 4.0, -1600, -700, "Inamgaon (Bhima Basin)", 2500),
    (19.550, 74.930, 3.5, -1500, 400, "Nevasa & Jorwe & Prakash", 3000),

    # --- SOUTH INDIAN NEOLITHIC / ASHMOUND & MEGALITHIC (Fuller 2006, Moorti 1994) ---
    (16.050, 77.650, 3.5, -2800, -1200, "Utnur & Budihal & Kodekal (Ashmounds)", 1500),
    (16.120, 76.570, 3.5, -2800, -1000, "Piklihal & Maski (Raichur Doab)", 2000),
    (15.160, 76.980, 4.0, -2800, -1000, "Sanganakallu & Hiregudda & Tekkalakota", 2500),
    (14.810, 76.810, 4.0, -2500, 200, "Brahmagiri (Chitradurga)", 3000),
    (14.340, 75.620, 3.5, -2200, -600, "Hallur (Tungabhadra)", 1800),
    (12.220, 76.900, 3.5, -2200, -300, "T. Narsipur & Hemmige (Kaveri)", 1800),
    (12.500, 78.570, 3.5, -2000, -300, "Paiyampalli (North Tamil Nadu)", 1800),
    (8.630, 77.880, 4.5, -1500, 200, "Adichanallur & Sivakalai (Thamirabarani)", 4500),
    (11.110, 77.520, 4.5, -800, 400, "Kodumanal (Noyyal, Kongu)", 5000),
    (9.840, 78.190, 4.5, -600, 300, "Keeladi / Keezhadi (Vaigai)", 6000),
    (10.630, 76.080, 3.5, -1000, 300, "Porkalam & Cheramanangad (Kerala Megaliths)", 2000),
    (12.560, 79.900, 3.5, -1000, 200, "Sanur & Amirthamangalam (Tondaimandalam)", 2000),
    (21.210, 78.830, 4.0, -1100, 300, "Mahurjhari & Naikund & Takalghat (Vidarbha Megaliths)", 3000),
    (17.160, 79.580, 3.5, -1000, 200, "Nagarjunakonda & Yelleswaram Megaliths", 3000),

    # --- VEDIC / PGW / MAHAJANAPADAS / NANDA / MAURYA / CLASSICAL ---
    (29.160, 78.000, 4.5, -1200, 300, "Hastinapura (Upper Ganga)", 15000),
    (28.370, 79.130, 4.5, -1200, 1100, "Ahichhatra (Panchala)", 20000),
    (27.580, 78.660, 4.0, -1800, 600, "Atranjikhera (Etah, Doab)", 10000),
    (27.620, 79.280, 4.0, -1000, 600, "Kampilya (South Panchala)", 10000),
    (27.492, 77.674, 5.0, -1000, 1800, "Mathura (Surasena / Kushan)", 50000),
    (28.609, 77.243, 5.0, -1100, 1800, "Indraprastha / Purana Qila / Delhi", 80000),
    (25.344, 81.394, 5.0, -1000, 600, "Kaushambi (Vatsa)", 40000),
    (25.317, 83.010, 5.0, -900, 1800, "Varanasi / Rajghat (Kashi)", 60000),
    (25.611, 85.144, 5.0, -550, 1800, "Pataliputra / Patna (Magadha-Nanda-Maurya-Gupta)", 150000),
    (25.028, 85.420, 4.5, -700, 600, "Rajagriha / Rajgir (Magadha)", 35000),
    (25.990, 85.130, 4.5, -700, 600, "Vaishali (Vajji)", 30000),
    (25.250, 86.950, 4.5, -700, 1200, "Champa / Bhagalpur (Anga)", 25000),
    (27.510, 82.050, 4.5, -700, 800, "Shravasti / Saheth-Maheth (Kosala)", 35000),
    (26.792, 82.194, 4.5, -800, 1800, "Ayodhya / Saketa (Kosala)", 30000),
    (27.575, 83.052, 4.0, -800, 600, "Tilaurakot / Kapilavastu (Nepal Terai)", 15000),
    (27.469, 83.275, 4.0, -600, 1200, "Lumbini (Nepal Terai)", 8000),
    (26.740, 83.880, 4.0, -600, 1000, "Kushinagar (Malla)", 10000),
    (23.182, 75.777, 5.0, -700, 1800, "Ujjayini / Ujjain (Avanti)", 50000),
    (23.525, 77.808, 4.5, -600, 1000, "Vidisha / Besnagar & Sanchi", 30000),
    (33.746, 72.787, 5.0, -1000, 500, "Taxila / Bhir Mound & Sirkap (Gandhara)", 50000),
    (34.145, 71.730, 4.5, -1200, 600, "Pushkalavati / Charsadda (Gandhara)", 30000),
    (34.015, 71.580, 5.0, -400, 1800, "Purushapura / Peshawar (Kushan)", 60000),
    (34.770, 72.360, 4.0, -1500, 1000, "Barikot / Bazira & Butkara (Swat)", 15000),
    (32.495, 74.531, 4.5, -500, 1800, "Sagala / Sialkot (Indo-Greek)", 25000),
    (20.232, 85.853, 5.0, -500, 400, "Sisupalgarh & Dhauli (Kalinga)", 30000),
    (19.530, 84.830, 4.0, -400, 400, "Jaugada (South Kalinga)", 15000),
    (22.290, 87.920, 4.5, -400, 800, "Tamralipti / Tamluk (Bengal Port)", 25000),
    (22.700, 88.680, 4.5, -400, 1200, "Chandraketugarh (Lower Bengal)", 25000),
    (24.961, 89.343, 5.0, -400, 1400, "Mahasthangarh / Pundranagara (Bangladesh)", 35000),
    (24.095, 90.822, 4.5, -500, 200, "Wari-Bateshwar (Bangladesh)", 20000),
    (25.031, 88.977, 4.5, 700, 1200, "Somapura Mahavihara / Paharpur (Bangladesh)", 12000),
    (23.428, 91.137, 4.5, 600, 1300, "Mainamati / Devaparvata (Bangladesh)", 15000),
    (23.545, 90.483, 4.5, 900, 1600, "Vikrampur & Sonargaon (Bangladesh)", 25000),
    (26.183, 91.733, 4.5, -300, 1800, "Pragjyotishpura / Guwahati (Kamarupa-Assam)", 20000),
    (26.633, 92.800, 4.0, 500, 1700, "Tezpur / Haruppesvara (Assam)", 12000),
    (26.980, 94.630, 4.0, 1250, 1800, "Sivasagar / Garhgaon / Charaideo (Ahom)", 15000),

    # --- GRECO-ROMAN EMPORIA, DECCAN, TAMILAKAM, SRI LANKA, NEPAL, BHUTAN, MALDIVES ---
    (21.705, 72.996, 4.5, -500, 1800, "Barygaza / Bharuch (Gujarat Emporium)", 30000),
    (19.415, 72.815, 4.0, -400, 1300, "Sopara / Supparaka (Konkan Port)", 15000),
    (24.750, 67.520, 4.5, -300, 1200, "Barbarikon / Banbhore / Debal (Indus Delta)", 25000),
    (27.690, 68.930, 4.5, 300, 1100, "Alor / Aror (Sindh Capital)", 25000),
    (25.880, 68.780, 4.5, 500, 1100, "Brahmanabad / Mansura (Sindh)", 35000),
    (24.747, 67.924, 4.5, 1340, 1800, "Thatta / Makli (Samma-Mughal Sindh)", 50000),
    (10.158, 76.208, 4.5, -300, 500, "Muziris / Pattanam (Kerala Roman Emporium)", 25000),
    (11.905, 79.819, 4.5, -200, 400, "Arikamedu / Poduke (Coromandel Roman Emporium)", 20000),
    (11.144, 79.855, 4.5, -300, 600, "Kaveripattinam / Puhar (Chola Port)", 30000),
    (8.642, 78.060, 4.0, -600, 600, "Korkai (Pandya Pearl Port)", 15000),
    (9.354, 78.972, 4.0, -400, 500, "Alagankulam (Vaigai Roman Port)", 12000),
    (9.920, 78.120, 5.0, -400, 1800, "Madurai (Pandya-Nayaka Capital)", 60000),
    (10.825, 78.675, 4.5, -300, 1800, "Uraiyur / Tiruchirappalli (Chola)", 35000),
    (10.787, 79.138, 5.0, 850, 1800, "Thanjavur (Imperial Chola-Nayaka-Maratha)", 80000),
    (11.206, 79.449, 4.5, 1025, 1300, "Gangaikonda Cholapuram (Chola Capital)", 40000),
    (12.834, 79.704, 5.0, -200, 1800, "Kanchipuram (Pallava-Chola Capital)", 60000),
    (10.228, 76.197, 4.5, 800, 1500, "Mahodayapuram / Kodungallur (Chera Perumal)", 25000),
    (11.258, 75.780, 4.5, 1100, 1800, "Calicut / Kozhikode (Zamorin)", 40000),
    (8.893, 76.614, 4.0, 800, 1800, "Quilon / Kollam (Venad Port)", 25000),
    (19.480, 75.380, 4.5, -300, 1400, "Pratishthana / Paithan (Satavahana)", 35000),
    (16.573, 80.358, 4.5, -300, 1200, "Amaravati / Dhanyakataka (Satavahana)", 35000),
    (16.533, 79.233, 4.5, 100, 600, "Nagarjunakonda / Vijayapuri (Ikshvaku)", 25000),
    (15.335, 76.460, 5.0, 1336, 1565, "Vijayanagara / Hampi", 250000),
    (15.919, 75.676, 4.5, 500, 1200, "Badami, Aihole & Pattadakal (Chalukya)", 25000),
    (17.190, 77.150, 4.5, 750, 1100, "Manyakheta / Malkhed (Rashtrakuta)", 40000),
    (17.970, 79.600, 4.5, 1100, 1600, "Warangal / Orugallu (Kakatiya)", 40000),
    (13.213, 75.994, 4.5, 1050, 1340, "Dwarasamudra / Halebidu & Belur (Hoysala)", 30000),
    (19.942, 75.213, 4.5, 1150, 1750, "Devagiri / Daulatabad (Yadava-Sultanate)", 50000),
    (17.330, 76.830, 4.5, 1347, 1750, "Gulbarga & Bidar (Bahmani)", 50000),
    (16.824, 75.715, 5.0, 1490, 1750, "Bijapur (Adil Shahi)", 100000),
    (17.383, 78.401, 5.0, 1518, 1800, "Golconda & Hyderabad (Qutb Shahi-Nizam)", 150000),
    (27.050, 79.920, 5.0, 400, 1500, "Kannauj / Kanyakubja (Harsha-Pratihara)", 70000),
    (21.880, 71.880, 4.5, 450, 800, "Valabhi (Maitraka Gujarat)", 30000),
    (23.850, 72.120, 4.5, 750, 1500, "Anahilavada / Patan (Solanki Gujarat)", 50000),
    (23.023, 72.571, 5.0, 1411, 1800, "Ahmedabad (Gujarat Sultanate-Mughal)", 150000),
    (21.170, 72.831, 5.0, 1500, 1800, "Surat (Mughal Port)", 120000),
    (27.176, 78.008, 5.0, 1504, 1800, "Agra & Fatehpur Sikri (Mughal Capital)", 250000),
    (24.868, 88.133, 5.0, 750, 1575, "Gaur & Pandua / Lakhnauti (Pala-Sena-Bengal Sultanate)", 120000),
    (23.710, 90.407, 5.0, 1608, 1800, "Dhaka / Jahangirnagar (Mughal Bengal)", 150000),
    (24.180, 88.270, 5.0, 1704, 1800, "Murshidabad (Nawab Bengal)", 150000),
    (22.572, 88.364, 5.0, 1690, 1800, "Calcutta / Fort William", 120000),
    (13.082, 80.270, 5.0, 1639, 1800, "Madras / Fort St George", 120000),
    (18.938, 72.835, 5.0, 1534, 1800, "Bombay / Mumbai", 100000),
    (15.500, 73.912, 4.5, 1300, 1800, "Old Goa / Velha Goa (Estado da India)", 75000),
    (11.934, 79.830, 4.5, 1674, 1800, "Pondicherry (French India)", 40000),
    (8.350, 80.403, 5.0, -500, 1050, "Anuradhapura (Sri Lanka)", 60000),
    (7.940, 81.000, 5.0, 993, 1300, "Polonnaruwa (Sri Lanka)", 45000),
    (7.957, 80.760, 4.0, 477, 600, "Sigiriya (Sri Lanka)", 12000),
    (8.958, 79.953, 4.5, -300, 1100, "Mantai / Mahatittha (Sri Lanka Emporium)", 20000),
    (6.283, 81.288, 4.5, -400, 1100, "Tissamaharama / Mahagama (Ruhuna)", 25000),
    (7.291, 80.634, 4.5, 1469, 1815, "Kandy / Senkadagalapura (Sri Lanka)", 25000),
    (9.662, 80.025, 4.5, 1215, 1800, "Nallur / Jaffna (Sri Lanka)", 30000),
    (6.927, 79.861, 4.5, 1400, 1800, "Kotte & Colombo (Sri Lanka)", 35000),
    (27.705, 85.307, 5.0, 200, 1800, "Kathmandu, Patan & Bhaktapur (Licchavi-Malla-Shah)", 60000),
    (29.320, 82.160, 4.0, 1100, 1500, "Sinja Valley (Khasa Malla, West Nepal)", 12000),
    (28.000, 84.630, 4.0, 1559, 1800, "Gorkha (Shah Dynasty)", 10000),
    (29.180, 83.950, 3.5, -1000, 1600, "Upper Mustang Sky Caves & Lo Manthang", 5000),
    (27.583, 89.863, 4.0, 1637, 1800, "Punakha Dzong (Bhutan)", 8000),
    (27.472, 89.639, 4.0, 1200, 1800, "Thimphu / Tashichho & Simtokha Dzong (Bhutan)", 8000),
    (27.430, 89.413, 3.5, 700, 1800, "Paro / Kyichu Lhakhang & Rinpung Dzong (Bhutan)", 6000),
    (27.550, 90.730, 3.5, 700, 1800, "Bumthang / Jambay Lhakhang & Jakar (Bhutan)", 6000),
    (27.500, 90.505, 3.5, 1543, 1800, "Trongsa Dzong (Bhutan)", 5000),
    (4.175, 73.509, 4.0, -300, 1800, "Male (Maldives Sultanate Capital)", 10000),
    (1.916, 73.543, 3.5, 200, 1400, "Gan & Isdhoo Hawitta Stupas (Laamu Atoll, Maldives)", 2500),
    (0.530, 73.000, 3.0, 300, 1500, "Kaashidhoo & Nilandhoo & Huvadhu Hawitta (Maldives)", 2000),
    (-0.298, 73.424, 3.0, 400, 1800, "Fuvahmulah Havitta (Maldives)", 2500),
    (-0.641, 73.158, 3.0, 500, 1800, "Addu Atoll / Meedhoo (Maldives)", 2500),
  ]
  out = []
  for lat, lon, wt, sy, ey, nm, mpop in sites:
    pw = assign_periods_by_span(sy, ey)
    if pw:
      out.append((lat, lon, wt, pw, "south_asia_scholarly_catalogue", True, mpop))
  return out


def ingest_all_repositories():
  records = []
  source_stats = Counter()

  # --- REPO 1: Archaeological Atlas of Published Excavations 2020 KMZ (6,513 records in South Asia+belt!) ---
  kmz_path = os.path.join(JADE_RAW_DIR, "arch_atlas_excavations_2020.kmz")
  if os.path.exists(kmz_path):
    with zipfile.ZipFile(kmz_path) as zf:
      kml = zf.read([n for n in zf.namelist() if n.endswith(".kml")][0]).decode("utf-8", errors="replace")
    for pm in re.findall(r"<Placemark>(.*?)</Placemark>", kml, re.S):
      cm = re.search(r"<coordinates>\s*([0-9.\-]+),([0-9.\-]+)", pm)
      if not cm:
        continue
      lon, lat = float(cm.group(1)), float(cm.group(2))
      if not (-1.5 <= lat <= 41.0 and 57.0 <= lon <= 102.0):
        continue
      nm_m = re.search(r"<name>(.*?)</name>", pm, re.S)
      ds_m = re.search(r"<description>(.*?)</description>", pm, re.S)
      txt = (nm_m.group(1) if nm_m else "") + " " + (ds_m.group(1) if ds_m else "")
      pw = classify_text_to_periods(txt)
      if not pw:
        # Published excavation site without explicit century string in reference: distribute smoothly across Holocene/Early Historic
        pw = [
          ("02_pre_harappan_chalcolithic_neolithic", 0.12),
          ("03_mature_harappan_indus_urban", 0.16),
          ("04_late_harappan_vedic_megalithic", 0.18),
          ("05_mahajanapadas_nanda_maurya", 0.18),
          ("06_indo_greek_kushan_satavahana_sangam", 0.16),
          ("07_gupta_vakataka_pallava_classical", 0.10),
          ("08_early_mediaeval_tripartite_chola", 0.10),
        ]
      records.append((lat, lon, 1.5, pw, "arch_atlas_excavations_2020", True, 0))
      source_stats["arch_atlas_excavations_2020"] += 1

  # --- REPO 2: ASI P1371 Centrally Protected Monuments (4,858 rows) ---
  asi_path = os.path.join(RAW_DIR, "wikidata_asi_p1371_monuments.json")
  if os.path.exists(asi_path):
    rows = json.load(open(asi_path, "r", encoding="utf-8"))
    seen_asi = set()
    for row in rows:
      qid = (row.get("item") or {}).get("value", "")
      if qid in seen_asi:
        continue
      lat, lon = parse_wd_coord((row.get("coord") or {}).get("value"))
      if lat is None or not (5.0 <= lat <= 37.5 and 67.5 <= lon <= 98.0):
        continue
      seen_asi.add(qid)
      inc = parse_wd_year((row.get("inception") or {}).get("value"))
      txt = " ".join([
        (row.get("itemLabel") or {}).get("value", ""),
        (row.get("periodLabel") or {}).get("value", ""),
        (row.get("cultureLabel") or {}).get("value", ""),
        (row.get("typeLabel") or {}).get("value", ""),
      ])
      if inc is not None and inc > 1830:
        continue  # Skip British colonial/modern post-1830 monuments
      pw = assign_periods_by_span(inc, min(1800, inc + 250)) if inc is not None else classify_text_to_periods(txt)
      if not pw:
        # Undated ASI protected monument: architectural heritage overwhelmingly spans Gupta-to-Mughal eras
        pw = [
          ("07_gupta_vakataka_pallava_classical", 0.15),
          ("08_early_mediaeval_tripartite_chola", 0.30),
          ("09_sultanate_vijayanagara_regional", 0.30),
          ("10_mughal_maratha_early_colonial", 0.25),
        ]
      wt = 2.0 if any(k in txt.lower() for k in ("fort", "mound", "site", "city", "ruins", "stupa", "cave", "megalith")) else 1.2
      records.append((lat, lon, wt, pw, "asi_p1371_monuments", True, 0))
      source_stats["asi_p1371_monuments"] += 1

  # --- REPO 3-8: Wikidata Multi-Country Archaeological & Heritage Registers (IN, PK, BD, LK, NP, BT, MV, AF, MM) ---
  wd_files = [
    ("wikidata_india_arch_and_state_monuments.json", "wd_india_arch_state"),
    ("wikidata_india_pre1750_monuments.json", "wd_india_pre1750"),
    ("wikidata_arch_india.json", "wd_india_arch_w1"),
    ("wikidata_w2_pakistan.json", "wd_pakistan_arch"),
    ("wikidata_arch_pakistan.json", "wd_pakistan_arch_w1"),
    ("wikidata_w2_bangladesh.json", "wd_bangladesh_arch"),
    ("wikidata_w2_sri_lanka.json", "wd_sri_lanka_arch"),
    ("wikidata_w2_nepal.json", "wd_nepal_arch"),
    ("wikidata_w2_bhutan.json", "wd_bhutan_arch"),
    ("wikidata_w2_maldives.json", "wd_maldives_arch"),
    ("wikidata_w2_afghanistan.json", "wd_afghanistan_frontier"),
    ("wikidata_w2_myanmar.json", "wd_myanmar_frontier"),
  ]
  seen_wd_global = set()
  for fn, tag in wd_files:
    fp = os.path.join(RAW_DIR, fn)
    if not os.path.exists(fp):
      continue
    try:
      rows = json.load(open(fp, "r", encoding="utf-8"))
    except Exception:
      continue
    for row in rows:
      qid = (row.get("item") or {}).get("value", "")
      if qid in seen_wd_global:
        continue
      lat, lon = parse_wd_coord((row.get("coord") or {}).get("value"))
      if lat is None or not (-1.5 <= lat <= 41.0 and 57.0 <= lon <= 102.0):
        continue
      seen_wd_global.add(qid)
      inc = parse_wd_year((row.get("inception") or {}).get("value"))
      if inc is not None and inc > 1830:
        continue
      txt = " ".join([
        (row.get("itemLabel") or {}).get("value", ""),
        (row.get("periodLabel") or {}).get("value", ""),
        (row.get("cultureLabel") or {}).get("value", ""),
        (row.get("typeLabel") or {}).get("value", ""),
        (row.get("classLabel") or {}).get("value", ""),
      ])
      pw = assign_periods_by_span(inc, min(1800, inc + 250)) if inc is not None else classify_text_to_periods(txt)
      if not pw:
        if any(k in txt.lower() for k in ("archaeological", "ancient", "stupa", "mound", "megalith", "ruins")):
          pw = [
            ("04_late_harappan_vedic_megalithic", 0.15),
            ("05_mahajanapadas_nanda_maurya", 0.25),
            ("06_indo_greek_kushan_satavahana_sangam", 0.25),
            ("07_gupta_vakataka_pallava_classical", 0.20),
            ("08_early_mediaeval_tripartite_chola", 0.15),
          ]
        else:
          pw = [
            ("08_early_mediaeval_tripartite_chola", 0.25),
            ("09_sultanate_vijayanagara_regional", 0.35),
            ("10_mughal_maratha_early_colonial", 0.40),
          ]
      wt = 2.0 if any(k in txt.lower() for k in ("ancient city", "archaeological", "fort", "stupa")) else 1.2
      records.append((lat, lon, wt, pw, tag, True, 0))
      source_stats[tag] += 1

  # --- REPO 9: Pleiades Ancient World Gazetteer (Classical / Maurya / Indo-Greek / Roman Emporia) ---
  pl_path = os.path.join(RAW_DIR, "pleiades_south_asia.json")
  if os.path.exists(pl_path):
    for row in json.load(open(pl_path, "r", encoding="utf-8")):
      lat, lon = float(row["lat"]), float(row["lon"])
      try:
        mn = int(float(row["minDate"])) if row.get("minDate") else -330
        mx = int(float(row["maxDate"])) if row.get("maxDate") else 500
      except Exception:
        mn, mx = -330, 500
      pw = assign_periods_by_span(mn, mx)
      if not pw:
        pw = [("05_mahajanapadas_nanda_maurya", 0.4), ("06_indo_greek_kushan_satavahana_sangam", 0.6)]
      ft = str(row.get("featureTypes") or "").lower()
      wt = 2.5 if any(k in ft for k in ("settlement", "port", "fort", "urban")) else 1.0
      records.append((lat, lon, wt, pw, "pleiades_ancient_south_asia", "settlement" in ft or "port" in ft, 0))
      source_stats["pleiades_ancient_south_asia"] += 1

  # --- REPO 10: Zenodo 3667657 & 3670055 Vidarbha Archaeological Census (Maharashtra Megaliths & Settlements) ---
  vid_master = os.path.join(RAW_DIR, "zenodo_3667657_Vidarbha_SiteMasterList.csv")
  vid_coords = {}
  if os.path.exists(vid_master):
    with open(vid_master, "r", encoding="utf-8-sig", errors="replace") as fh:
      for row in csv.DictReader(fh):
        sc = (row.get("SiteCode") or "").strip()
        try:
          lat = float(row.get("YCoord") or "")
          lon = float(row.get("Xcoord") or "")
          if 18.0 <= lat <= 23.0 and 76.0 <= lon <= 82.0:
            vid_coords[sc] = (lat, lon)
        except Exception:
          pass
  vid_zip = os.path.join(RAW_DIR, "zenodo_3670055_Vidarbha_2016Survey_SiteRecords.zip")
  if os.path.exists(vid_zip):
    with zipfile.ZipFile(vid_zip) as zf:
      for nm in zf.namelist():
        if nm.endswith("AllSites.csv") and "__MACOSX" not in nm:
          txt_data = zf.read(nm).decode("utf-8-sig", errors="replace")
          for row in csv.DictReader(io.StringIO(txt_data)):
            try:
              lat = float(row.get("Latitude") or row.get("YCoord") or row.get("Lat") or "")
              lon = float(row.get("Longitude") or row.get("Xcoord") or row.get("Lon") or "")
              if 18.0 <= lat <= 23.0 and 76.0 <= lon <= 82.0:
                pw = [
                  ("04_late_harappan_vedic_megalithic", 0.45),
                  ("05_mahajanapadas_nanda_maurya", 0.30),
                  ("06_indo_greek_kushan_satavahana_sangam", 0.25),
                ]
                records.append((lat, lon, 1.5, pw, "zenodo_vidarbha_census", True, 0))
                source_stats["zenodo_vidarbha_census"] += 1
            except Exception:
              pass
  for sc, (lat, lon) in vid_coords.items():
    pw = [
      ("04_late_harappan_vedic_megalithic", 0.40),
      ("05_mahajanapadas_nanda_maurya", 0.30),
      ("06_indo_greek_kushan_satavahana_sangam", 0.20),
      ("07_gupta_vakataka_pallava_classical", 0.10),
    ]
    records.append((lat, lon, 1.8, pw, "zenodo_vidarbha_census", True, 0))
    source_stats["zenodo_vidarbha_census"] += 1

  # --- REPO 11: Zenodo 18796737 Harappan Sites + fconesa AgriExp2022 ---
  har_csv = os.path.join(RAW_DIR, "zenodo_18796737_Zenodo_Final_Harappan_sitess.csv")
  if os.path.exists(har_csv):
    with open(har_csv, "r", encoding="utf-8-sig", errors="replace") as fh:
      for row in csv.DictReader(fh):
        try:
          lat = float(row.get("lat_updated") or row.get("lat_legacy") or "")
          lon = float(row.get("lon_updated") or row.get("lon_legacy") or "")
          if 20.0 <= lat <= 34.0 and 66.0 <= lon <= 79.0:
            pw = [("02_pre_harappan_chalcolithic_neolithic", 0.25), ("03_mature_harappan_indus_urban", 0.55), ("04_late_harappan_vedic_megalithic", 0.20)]
            records.append((lat, lon, 2.2, pw, "zenodo_harappan_sites", True, 0))
            source_stats["zenodo_harappan_sites"] += 1
        except Exception:
          pass

  # --- REPO 12: c14_cleaned_dedup.csv + XRONOS + AADR v66 (STRICT API FORENSICS!) ---
  # Known corrupted coordinates in XRONOS/p3k14c caught during Stage C0 API Forensics:
  # - Køge Bugt (Denmark, 55.5, 12.33) mis-tagged IN
  # - Hiregudda / Sannarachamma / Piklihal (Karnataka) mis-plotted at 24.784, 70.183 (Thar Desert)
  corrupted_pts = [(24.784, 70.183), (29.501, 86.469)]

  c14_path = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_c14bazAAR", "c14_cleaned_dedup.csv")
  if os.path.exists(c14_path):
    with open(c14_path, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        try:
          lat, lon = float(row["lat"]), float(row["lon"])
          bp = float(row["c14age"])
        except Exception:
          continue
        if not (-1.5 <= lat <= 41.0 and 57.0 <= lon <= 102.0):
          continue
        if any(abs(lat - cla) < 0.02 and abs(lon - clo) < 0.02 for cla, clo in corrupted_pts):
          continue
        cal_yr = int(round(1950 - bp * 1.07))
        pw = assign_periods_by_span(cal_yr - 150, cal_yr + 150)
        if pw:
          records.append((lat, lon, 1.5, pw, "c14_cleaned_dedup", True, 0))
          source_stats["c14_cleaned_dedup"] += 1

  xr_in = os.path.join(RAW_DIR, "xronos_in.json")
  if os.path.exists(xr_in):
    for item in json.load(open(xr_in, "r", encoding="utf-8")):
      m = item.get("measurement", {}) if isinstance(item, dict) else {}
      try:
        lat, lon = float(m.get("lat")), float(m.get("lng"))
        bp = float(m.get("bp"))
      except Exception:
        continue
      if not (5.0 <= lat <= 37.5 and 67.5 <= lon <= 98.0):
        continue
      if any(abs(lat - cla) < 0.02 and abs(lon - clo) < 0.02 for cla, clo in corrupted_pts):
        continue
      cal_yr = int(round(1950 - bp * 1.07))
      pw = assign_periods_by_span(cal_yr - 150, cal_yr + 150)
      if pw:
        records.append((lat, lon, 1.5, pw, "xronos_radiocarbon", True, 0))
        source_stats["xronos_radiocarbon"] += 1

  anno_path = os.path.join(JADE_RAW_DIR, "aadr_v66.p1_1240K.aadr.PUB.anno")
  if os.path.exists(anno_path):
    with open(anno_path, "r", encoding="utf-8", errors="replace") as fh:
      fh.readline()
      seen_aadr = set()
      for line in fh:
        p = line.strip().split("\t")
        if len(p) <= 18:
          continue
        try:
          lat, lon = float(p[17]), float(p[18])
          bp = float(p[10])
        except Exception:
          continue
        if not (-1.5 <= lat <= 41.0 and 57.0 <= lon <= 102.0):
          continue
        key_a = (round(lat, 2), round(lon, 2), int(bp // 200))
        if key_a in seen_aadr:
          continue
        seen_aadr.add(key_a)
        yr = int(round(1950 - bp))
        pw = assign_periods_by_span(yr - 150, yr + 150)
        if pw:
          records.append((lat, lon, 2.0, pw, "aadr_v66_ancient_dna", True, 0))
          source_stats["aadr_v66_ancient_dna"] += 1

  # --- REPO 13: JADE Northern Frontier Cross-Conditioning (Tibet / Xinjiang / Yunnan <= 300 km from INDUS) ---
  jade_to_indus = {
    "01_palaeolithic_early_neolithic_h1.geojson": [("01_palaeolithic_mesolithic_early_neolithic", 1.0)],
    "02_middle_neolithic_yangshao_h2.geojson": [("02_pre_harappan_chalcolithic_neolithic", 1.0)],
    "03_late_neolithic_longshan_h3.geojson": [("03_mature_harappan_indus_urban", 1.0)],
    "04_bronze_age_shang_zhou_h4.geojson": [("04_late_harappan_vedic_megalithic", 1.0)],
    "05_spring_autumn_warring_states_h5.geojson": [("05_mahajanapadas_nanda_maurya", 1.0)],
    "06_qin_han_xiongnu_h6.geojson": [("06_indo_greek_kushan_satavahana_sangam", 1.0)],
    "07_wei_jin_northern_southern_h7.geojson": [("07_gupta_vakataka_pallava_classical", 1.0)],
    "08_sui_tang_five_dynasties_h8.geojson": [("08_early_mediaeval_tripartite_chola", 1.0)],
    "09_liao_song_jin_yuan_h9.geojson": [("09_sultanate_vijayanagara_regional", 1.0)],
    "10_ming_qing_imperial_h10.geojson": [("10_mughal_maratha_early_colonial", 1.0)],
  }
  for fn, pw in jade_to_indus.items():
    fp = os.path.join(JADE_GJ_DIR, fn)
    if not os.path.exists(fp):
      continue
    gj = json.load(open(fp, "r", encoding="utf-8"))
    for feat in gj.get("features", []):
      coords = (feat.get("geometry") or {}).get("coordinates") or []
      if len(coords) < 2:
        continue
      lon, lat = float(coords[0]), float(coords[1])
      if 24.0 <= lat <= 41.0 and 72.0 <= lon <= 102.0:
        cnt = float((feat.get("properties") or {}).get("site_count") or 0.0)
        if cnt > 0:
          records.append((lat, lon, min(cnt, 20.0), pw, "jade_himalayan_frontier", True, 0))
          source_stats["jade_himalayan_frontier"] += 1

  # --- REPO 14: OSM Overpass archaeological sites (if cached) ---
  for fn in sorted(os.listdir(RAW_DIR)):
    if not fn.startswith("osm_arch_") or not fn.endswith(".json"):
      continue
    try:
      els = json.load(open(os.path.join(RAW_DIR, fn), "r", encoding="utf-8"))
    except Exception:
      continue
    for el in els:
      lat = el.get("lat") or (el.get("center") or {}).get("lat")
      lon = el.get("lon") or (el.get("center") or {}).get("lon")
      if lat is None or lon is None:
        continue
      tags = el.get("tags") or {}
      if tags.get("historic") not in ("archaeological_site", "megalith", "tumulus", "fort"):
        continue
      txt = " ".join([str(tags.get(k, "")) for k in ("name", "site_type", "historic:civilization", "historic:period", "start_date", "description")])
      pw = classify_text_to_periods(txt)
      if not pw:
        if tags.get("historic") in ("megalith", "tumulus"):
          pw = [("04_late_harappan_vedic_megalithic", 0.7), ("05_mahajanapadas_nanda_maurya", 0.3)]
        elif tags.get("historic") == "fort":
          pw = [("09_sultanate_vijayanagara_regional", 0.45), ("10_mughal_maratha_early_colonial", 0.55)]
        else:
          pw = [
            ("05_mahajanapadas_nanda_maurya", 0.20),
            ("06_indo_greek_kushan_satavahana_sangam", 0.25),
            ("07_gupta_vakataka_pallava_classical", 0.25),
            ("08_early_mediaeval_tripartite_chola", 0.30),
          ]
      records.append((float(lat), float(lon), 1.0, pw, "osm_archaeological_sites", True, 0))
      source_stats["osm_archaeological_sites"] += 1

  # --- REPO 15: Curated South Asian Regional Archaeological Complexes Catalogue ---
  curated = build_curated_south_asia_catalogue()
  records.extend(curated)
  source_stats["south_asia_scholarly_catalogue"] = len(curated)

  # Spatial-temporal deduplication (collapse identical coordinates within 0.015 deg per source_class)
  dedup_map = {}
  for lat, lon, wt, pw, tag, is_sett, mpop in records:
    key_d = (round(lat, 2), round(lon, 2), tag)
    if key_d not in dedup_map:
      dedup_map[key_d] = [lat, lon, wt, list(pw), tag, is_sett, mpop]
    else:
      dedup_map[key_d][2] = min(15.0, dedup_map[key_d][2] + wt * 0.35)
      dedup_map[key_d][6] = max(dedup_map[key_d][6], mpop)
  dedup_records = [tuple(v) for v in dedup_map.values()]

  print("\n[C] Multi-Repository Ingestion Breakdown (INDUS):", flush=True)
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
    if dists_km[i] > 180.0:
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

  # Biome/Aridity-conditioned Q75 + IQR taphonomic outlier shrinkage
  dom_mask_c = np.array([not c["is_frontier_buffer"] for c in catchments], dtype=bool)
  c_areas = np.array([c["area_km2"] for c in catchments], dtype=np.float64)
  c_hyde = np.array([hyde_dens[latlon_to_rc(c["lat"], c["lon"])] for c in catchments], dtype=np.float64)
  is_arid = c_hyde < 5.0

  for pk in PERIOD_KEYS:
    vals = per_counts[pk]
    dens = vals / np.maximum(150.0, c_areas)
    for grp_mask, cap_mult in [(dom_mask_c & is_arid, 1.5), (dom_mask_c & (~is_arid), 2.5)]:
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

  # B2 Neighbour zero-hole imputation inside densely settled alluvial belts (HYDE >= 4.0 inh/km2)
  k_nbr = min(9, n_c)
  ndists, nidxs = tree.query(c_xyz, k=k_nbr)
  for pk in PERIOD_KEYS:
    vals = per_counts[pk].copy()
    for ci in range(n_c):
      if vals[ci] > 0 or c_hyde[ci] < 4.0:
        continue
      nbrs = nidxs[ci, 1:]
      nvals = vals[nbrs]
      pos_n = nvals[nvals > 0]
      if pos_n.size >= 3:
        ndens = pos_n / np.maximum(150.0, c_areas[nbrs[nvals > 0]])
        vals[ci] = 0.38 * float(np.median(ndens)) * c_areas[ci]
    per_counts[pk] = vals

  # Export period GeoJSONs
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

  # Export 00_all_periods.geojson
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
    "domain": "INDUS",
    "macro_scope": "India, Pakistan, Bangladesh, Sri Lanka, Nepal, Bhutan and Maldives",
    "sources": list(source_stats.keys()),
    "source_record_counts": source_stats,
    "domestic_assigned_records": assigned_dom,
    "frontier_assigned_records": assigned_fr,
    "catchment_counts": {"domestic": int(dom_mask_c.sum()), "frontier_buffer": int((~dom_mask_c).sum())},
    "documented_site_pixels": len(doc_pixels),
    "period_geojsons": period_meta
  }
  with open(os.path.join(CFG_DIR, "sites_indus_south_asia_geojson_metadata.json"), "w", encoding="utf-8") as fh:
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
    "geojson_metadata_filename": "config/sites_indus_south_asia_geojson_metadata.json",
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
      "elevation_barrier_m": 600,
      "habitability_filter": {
        "arctic_lat_cut": 50.0,
        "extreme_elev_cut_m": 4400.0,
        "hyde_core_min_dens": 0.003,
        "hyde_marginal_min_dens": 0.14,
        "site_radius_px": 1.8,
        "stadester_max_first_year": 1850,
        "stadester_radius_px": 2.0
      },
      "hu_admixture_config": "histmap/3.data_transform/population_Substrata.viscount/config/indus_dasymetric_admixture.json5",
      "residual_kriging_mode": "hu_hyde_residual",
      "covariate_paths": {
        "documented_settlements_json": "histmap/1.data_raw/population_regional/INDUS/_shared/sites_indus_south_asia/config/documented_settlements.json",
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/INDUS/_shared/sites_indus_south_asia/config/documented_site_pixels.json",
        "forest_asc": "histmap/1.data_raw/metadata_HYDE/general_files/forest_wwf_cr.asc",
        "ghsl_urban_2020_raster": "histmap/1.data_raw/population_GHSL/urban_rasters/GHSL_2020.png",
        "ghsl_urban_folder": "histmap/1.data_raw/population_GHSL/urban_rasters",
        "ghsl_urban_pop_threshold": 35000,
        "hyde_mcevedy_rasters_folder": "histmap/2.data_cleaning/landuse_HYDE/rasters_mcevedy",
        "hyde_popc_folder": "histmap/2.data_cleaning/landuse_HYDE/rasters_scaled_to_global",
        "hyde_raw_rasters_folder": "histmap/2.data_cleaning/landuse_HYDE/rasters",
        "hyde_uopp_raster": "histmap/2.data_raw/landuse_HYDE/rasters/uopp_2023AD.png",
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
      "domain_mask_png": "histmap/1.data_raw/population_regional/INDUS/_shared/sites_indus_south_asia/config/indus_domain_mask.png",
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
  # Fix hyde_uopp_raster path to match JADE/PRETA (2.data_cleaning/landuse_HYDE/rasters/uopp_2023AD.png)
  cfg_obj["kriging_config"]["covariate_paths"]["hyde_uopp_raster"] = "histmap/2.data_cleaning/landuse_HYDE/rasters/uopp_2023AD.png"

  with open(os.path.join(CFG_DIR, "sites_indus_south_asia.json5"), "w", encoding="utf-8") as fh:
    json.dump(cfg_obj, fh, indent=2, ensure_ascii=False)

  print(f"\n[D] Completed INDUS multi-repository extraction: {assigned_dom:,} domestic + {assigned_fr:,} frontier records across {len(doc_pixels):,} documented pixels.", flush=True)


if __name__ == "__main__":
  domain_mask, land_area = build_indus_domain_mask()
  catchments = build_catchments(domain_mask, land_area)
  records, source_stats = ingest_all_repositories()
  aggregate_and_export(domain_mask, land_area, catchments, records, source_stats)
