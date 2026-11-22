"""Stage C Multi-Repository Archaeological & Historical Site Composite Extractor for Project MAGNETIC.

Builds scale-adaptive HydroBASINS Level 6 (Europe) + Level 5 (Greenland) + natural island
catchments (<= 25,000 km2) across Europe excluding the POLARIS core, plus Greenland, North Atlantic
and Macaronesian islands, alongside a 300 km cross-frontier conditioning belt (POLARIS Russia/
Belarus/Ukraine, CENTAUR Canadian Arctic, HANDBOOK Western Anatolia/Cyprus/Maghreb).

Composites 17+ primary institutional national/regional archaeological registers across all 5 required
MAGNETIC jurisdictions (`western_europe`, `central_europe`, `northern_europe`, `southern_europe`,
`balkans`), applies per-country survey-effort normalisation + biome/latitude Q75+IQR taphonomic
shrinkage + B2 settled-belt neighbour imputation, and exports ViscountMaternKriging-ready GeoJSONs,
metadata provenance matrices and domain configs.
"""

import csv
import io
import json
import math
import os
import re
import sqlite3
import struct
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
MAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC")
DOMAIN_DIR = os.path.join(MAG_DIR, "_shared", "sites_magnetic_europe")
RAW_DIR = os.path.join(DOMAIN_DIR, "0.raw_data")
CFG_DIR = os.path.join(DOMAIN_DIR, "config")
GJ_DIR = os.path.join(DOMAIN_DIR, "geojson")
MAG_GIS = os.path.join(MAG_DIR, "_shared", "_gis_cache")

DOMAIN_MASK_PNG = os.path.join(CFG_DIR, "magnetic_domain_mask.png")
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
HYBAS_EU_ZIP = os.path.join(MAG_GIS, "hybas_eu_lev07_v1c.zip")
BURINGH_TXT = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_urban_Buringh", "European urban population, 700 - 2000.txt")
HYBAS_GR_SHP = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CENTAUR", "_shared", "_gis_cache",
  "hydrobasins", "hybas_gr_lev05_v1c.shp"
)
NUNNIFFIIT_JSON = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CENTAUR", "_shared",
  "sites_northern_america", "raw_sources", "greenland_nunniffiit_cultures.json"
)
AADR_ANNO = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared",
  "sites_east_asia", "0.raw_data", "aadr_v66.p1_1240K.aadr.PUB.anno"
)
ARCHATLAS_KMZ = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared",
  "published_excavations_atlas", "Atlas20200604_Cropped.kmz"
)
C14_CSV = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_c14bazAAR", "c14_cleaned_dedup.csv")
POLARIS_RU_GJ = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "POLARIS", "_shared", "sites_IA_RAS", "geojson")
POLARIS_BU_GJ = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "POLARIS", "_shared", "sites_belarus_ukraine", "geojson")
CENTAUR_GJ = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CENTAUR", "_shared", "sites_northern_america", "geojson")

os.makedirs(CFG_DIR, exist_ok=True)
os.makedirs(GJ_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160
EARTH_R_KM = 6371.0

# 10 Chronological Archaeological Horizons calibrated to European & North Atlantic Prehistory/History
PERIODS = [
  {
    "epoch_id": 1, "key": "01_palaeolithic_mesolithic",
    "filename": "01_palaeolithic_mesolithic.png", "geojson_filename": "01_palaeolithic_mesolithic.geojson",
    "approx_start_year": -15000, "approx_end_year": -6000, "representative_year": -8500,
    "name_en": "Upper Palaeolithic and Mesolithic Europe",
    "name_de": "Jungpaläolithikum und Mesolithikum Europas",
    "name_fr": "Paléolithique supérieur et Mésolithique en Europe",
    "date_range_en": "c. 15000-6000BC (Magdalenian, Azilian, Maglemosian, Ertebølle and Lepenski Vir foragers)"
  },
  {
    "epoch_id": 2, "key": "02_neolithic_chalcolithic",
    "filename": "02_neolithic_chalcolithic.png", "geojson_filename": "02_neolithic_chalcolithic.geojson",
    "approx_start_year": -6000, "approx_end_year": -2500, "representative_year": -4200,
    "name_en": "Neolithic and Chalcolithic Europe",
    "name_de": "Neolithikum und Chalkolithikum Europas",
    "name_fr": "Néolithique et Chalcolithique en Europe",
    "date_range_en": "c. 6000-2500BC (Starčevo, Vinča, LBK, Cardial, Megalithic Atlantic, Funnelbeaker and Corded Ware)"
  },
  {
    "epoch_id": 3, "key": "03_bronze_age",
    "filename": "03_bronze_age.png", "geojson_filename": "03_bronze_age.geojson",
    "approx_start_year": -2500, "approx_end_year": -1000, "representative_year": -1700,
    "name_en": "Bronze Age Europe and Arctic Saqqaq",
    "name_de": "Bronzezeit Europas und arktische Saqqaq-Kultur",
    "name_fr": "Âge du Bronze en Europe et culture arctique de Saqqaq",
    "date_range_en": "c. 2500-1000BC (Minoan, Mycenaean, Únětice, Urnfield, Nordic Bronze Age, El Argar and Saqqaq)"
  },
  {
    "epoch_id": 4, "key": "04_iron_age_classical_greece",
    "filename": "04_iron_age_classical_greece.png", "geojson_filename": "04_iron_age_classical_greece.geojson",
    "approx_start_year": -1000, "approx_end_year": -200, "representative_year": -500,
    "name_en": "Iron Age Europe and Classical Greece",
    "name_de": "Eisenzeit Europas und Klassisches Griechenland",
    "name_fr": "Âge du Fer en Europe et Grèce classique",
    "date_range_en": "c. 1000-200BC (Classical Poleis, Hallstatt, La Tène, Etruscan, Iberian, Illyrian, Thracian and Dorset)"
  },
  {
    "epoch_id": 5, "key": "05_roman_and_free_germania",
    "filename": "05_roman_and_free_germania.png", "geojson_filename": "05_roman_and_free_germania.geojson",
    "approx_start_year": -200, "approx_end_year": 400, "representative_year": 150,
    "name_en": "Roman Empire and Free Germania",
    "name_de": "Römisches Reich und Germania Magna",
    "name_fr": "Empire romain et Germanie libre",
    "date_range_en": "200BC-400AD (Roman Provinces, Limes Germanicus and Danubius, Przeworsk, Wielbark and Roman Iron Age)"
  },
  {
    "epoch_id": 6, "key": "06_late_antiquity_migration_early_mediaeval",
    "filename": "06_late_antiquity_migration_early_mediaeval.png", "geojson_filename": "06_late_antiquity_migration_early_mediaeval.geojson",
    "approx_start_year": 400, "approx_end_year": 800, "representative_year": 600,
    "name_en": "Late Antiquity, Migration Period and Early Mediaeval Europe",
    "name_de": "Spätantike, Völkerwanderung und Frühmittelalter",
    "name_fr": "Antiquité tardive, Grandes Migrations et haut Moyen Âge",
    "date_range_en": "400-800AD (Merovingian, Visigothic, Lombard, Anglo-Saxon, Early Slavic, Byzantine Balkans and Vendel)"
  },
  {
    "epoch_id": 7, "key": "07_high_mediaeval_viking_al_andalus",
    "filename": "07_high_mediaeval_viking_al_andalus.png", "geojson_filename": "07_high_mediaeval_viking_al_andalus.geojson",
    "approx_start_year": 800, "approx_end_year": 1347, "representative_year": 1150,
    "name_en": "High Mediaeval Europe, Al-Andalus and Viking North Atlantic",
    "name_de": "Hochmittelalter, Al-Andalus und Wikingerzeit im Nordatlantik",
    "name_fr": "Moyen Âge central, Al-Andalus et expansion nordique",
    "date_range_en": "800-1347AD (Carolingian, Feudal Europe, Italian Communes, Al-Andalus, Norse Atlantic, Piast and Árpád)"
  },
  {
    "epoch_id": 8, "key": "08_late_mediaeval_black_death_ottoman_advance",
    "filename": "08_late_mediaeval_black_death_ottoman_advance.png", "geojson_filename": "08_late_mediaeval_black_death_ottoman_advance.geojson",
    "approx_start_year": 1347, "approx_end_year": 1500, "representative_year": 1425,
    "name_en": "Black Death, Late Mediaeval Crisis and Ottoman Balkan Advance",
    "name_de": "Schwarzer Tod, spätmittelalterliche Krise und osmanischer Balkan",
    "name_fr": "Peste noire, crise tardo-médiévale et Balkans ottomans",
    "date_range_en": "1347-1500AD (Post-plague contraction, Hanseatic urbanism, Reconquista completion and Thule Greenland)"
  },
  {
    "epoch_id": 9, "key": "09_early_modern_confessional_mercantile",
    "filename": "09_early_modern_confessional_mercantile.png", "geojson_filename": "09_early_modern_confessional_mercantile.geojson",
    "approx_start_year": 1500, "approx_end_year": 1750, "representative_year": 1650,
    "name_en": "Early Modern Europe, Ottoman Rumelia and Atlantic Islands",
    "name_de": "Frühe Neuzeit, osmanisches Rumelien und Atlantikinseln",
    "name_fr": "Europe moderne, Roumélie ottomane et îles Atlantiques",
    "date_range_en": "1500-1750AD (Reformation, Thirty Years' War, Dutch Golden Age, Macaronesia and Ottoman Balkans)"
  },
  {
    "epoch_id": 10, "key": "10_industrial_and_imperial_pre_census",
    "filename": "10_industrial_and_imperial_pre_census.png", "geojson_filename": "10_industrial_and_imperial_pre_census.geojson",
    "approx_start_year": 1750, "approx_end_year": 1871, "representative_year": 1820,
    "name_en": "Industrialisation and Pre-1871 Imperial Cadastres",
    "name_de": "Industrialisierung und vor-1871 kaiserliche Kataster",
    "name_fr": "Industrialisation et cadastres impériaux avant 1871",
    "date_range_en": "1750-1871AD (Industrial Revolution, Napoleonic Europe, Zollverein and early national censuses)"
  }
]
PERIOD_KEYS = [p["key"] for p in PERIODS]

# Map sovereign ADMIN names -> canonical MAGNETIC required_jurisdictions in viscount_skill_profiles.json5
COUNTRY_TO_JURISDICTION = {
  "United Kingdom": "western_europe", "Ireland": "western_europe", "France": "western_europe",
  "Belgium": "western_europe", "Netherlands": "western_europe", "Luxembourg": "western_europe",
  "Isle of Man": "western_europe", "Jersey": "western_europe", "Guernsey": "western_europe",
  "Monaco": "western_europe", "Andorra": "western_europe",
  "Germany": "central_europe", "Poland": "central_europe", "Austria": "central_europe",
  "Switzerland": "central_europe", "Liechtenstein": "central_europe",
  "Czechia": "central_europe", "Slovakia": "central_europe", "Hungary": "central_europe",
  "Denmark": "northern_europe", "Sweden": "northern_europe", "Norway": "northern_europe",
  "Finland": "northern_europe", "Aland": "northern_europe", "Iceland": "northern_europe",
  "Faroe Islands": "northern_europe", "Greenland": "northern_europe",
  "Estonia": "northern_europe", "Latvia": "northern_europe", "Lithuania": "northern_europe",
  "Italy": "southern_europe", "Vatican": "southern_europe", "San Marino": "southern_europe",
  "Spain": "southern_europe", "Portugal": "southern_europe", "Greece": "southern_europe",
  "Malta": "southern_europe", "Gibraltar": "southern_europe",
  "Slovenia": "balkans", "Croatia": "balkans", "Bosnia and Herzegovina": "balkans",
  "Republic of Serbia": "balkans", "Serbia": "balkans", "Montenegro": "balkans",
  "Kosovo": "balkans", "North Macedonia": "balkans", "Albania": "balkans",
  "Romania": "balkans", "Bulgaria": "balkans", "Moldova": "balkans", "Turkey-in-Europe": "balkans",
}

SOURCE_TIERS = {
  "ireland_nms_smr": "national_regional_register",
  "denmark_fund_og_fortidsminder": "national_regional_register",
  "finland_museovirasto": "national_regional_register",
  "sweden_raa_fornsok": "national_regional_register",
  "france_merimee_pop": "national_regional_register",
  "france_inrap_national": "national_regional_register",
  "italy_iccd_arco": "national_regional_register",
  "netherlands_rce_cho": "national_regional_register",
  "uk_historic_england_nhle": "national_regional_register",
  "belgium_flanders_vioe": "national_regional_register",
  "poland_nid_zra": "national_regional_register",
  "germany_idai_gazetteer": "national_regional_register",
  "greenland_nka_nunniffiit": "national_regional_register",
  "pleiades_antiquity": "academic_monograph_table",
  "dare_roman_empire": "academic_monograph_table",
  "aadr_v66_europe_adna": "academic_monograph_table",
  "archatlas_2020_europe": "academic_monograph_table",
  "europe_scholarly_catalogue": "academic_monograph_table",
  "c14bazaar_europe": "global_radiocarbon",
  "wikidata_arch_supplement": "global_crowd_wikidata_osm",
}


def latlon_to_rc(lat, lon):
  r = min(GRID_H - 1, max(0, int((90.0 - lat) * GRID_H / 180.0)))
  c = min(GRID_W - 1, max(0, int((lon + 180.0) * GRID_W / 360.0)))
  return r, c


def latlon_to_xyz(lat, lon):
  lr, nr = math.radians(lat), math.radians(lon)
  cl = math.cos(lr)
  return (cl * math.cos(nr), cl * math.sin(nr), math.sin(lr))


def sweref99tm_to_wgs84(arg0_e, arg1_n):
  """Exact analytical Gauss-Kruger inverse from SWEREF 99 TM (EPSG:3006) to WGS84."""
  a = 6378137.0
  f = 1.0 / 298.257222101
  e2 = f * (2.0 - f)
  n = f / (2.0 - f)
  a_hat = a / (1.0 + n) * (1.0 + n ** 2 / 4.0 + n ** 4 / 64.0)
  k0 = 0.9996
  lon0 = math.radians(15.0)
  xi = arg1_n / (k0 * a_hat)
  eta = (arg0_e - 500000.0) / (k0 * a_hat)
  d1 = n / 2.0 - 2.0 * n ** 2 / 3.0 + 37.0 * n ** 3 / 96.0
  d2 = n ** 2 / 48.0 + n ** 3 / 15.0
  d3 = 17.0 * n ** 3 / 480.0
  xi_p = xi - d1 * math.sin(2 * xi) * math.cosh(2 * eta) - d2 * math.sin(4 * xi) * math.cosh(4 * eta) - d3 * math.sin(6 * xi) * math.cosh(6 * eta)
  eta_p = eta - d1 * math.cos(2 * xi) * math.sinh(2 * eta) - d2 * math.cos(4 * xi) * math.sinh(4 * eta) - d3 * math.cos(6 * xi) * math.sinh(6 * eta)
  phi_star = math.asin(math.sin(xi_p) / math.cosh(eta_p))
  dlon = math.atan(math.sinh(eta_p) / math.cos(xi_p))
  lon = lon0 + dlon
  A_star = e2 + e2 ** 2 + e2 ** 3 + e2 ** 4
  B_star = -(7 * e2 ** 2 + 17 * e2 ** 3 + 30 * e2 ** 4) / 6.0
  C_star = (224 * e2 ** 3 + 889 * e2 ** 4) / 120.0
  sp = math.sin(phi_star)
  cp = math.cos(phi_star)
  sp2 = sp * sp
  lat = phi_star + sp * cp * (A_star + B_star * sp2 + C_star * sp2 * sp2)
  return math.degrees(lat), math.degrees(lon)


def assign_periods_by_span(start_yr, end_yr):
  if start_yr is None or end_yr is None:
    return []
  if start_yr > end_yr:
    start_yr, end_yr = end_yr, start_yr
  if end_yr < -20000 or start_yr > 1885:
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
    if mid < -15000:
      return [(PERIODS[0]["key"], 1.0)]
    if 1871 < mid <= 1900:
      return [(PERIODS[-1]["key"], 1.0)]
    return []
  tot = sum(w for _, w in hits)
  return [(k, w / tot) for k, w in hits]


MODERN_SKIP_RE = re.compile(
  r"(?:world war|wwii|ww2|ww1|bunker|pillbox|radar|airfield|19[1-9]\d|20[0-2]\d|20th cent|21st cent|20e|xxe|modern military|cold war)",
  flags=re.I
)


def classify_euro_text(arg0_text):
  """Multilingual European periodiser (EN/FR/DE/DA/SV/FI/NL/IT/PL/ES) -> list of (period_key, frac)."""
  s = (arg0_text or "").lower()
  if not s or MODERN_SKIP_RE.search(s):
    return None

  hits = []
  rules = [
    (["palaeolith", "paleolith", "paléolith", "paläolith", "mesolith", "mésolith", "kivikausi", "stenålder", "stenalder", "maglemos", "ertebølle", "azilian", "magdalen", "epipaleo", "epipalaeo"], "01_palaeolithic_mesolithic"),
    (["neolith", "néolith", "neolitycz", "chalcolith", "eneolith", "megalith", "mégalith", "dolmen", "menhir", "hunebed", "passage tomb", "court tomb", "portal tomb", "long barrow", "henge", "causewayed", "trb", "lbk", "linearband", "bondestenålder", "yngre stenalder", "trattbägar", "neolit"], "02_neolithic_chalcolithic"),
    (["bronze", "bronz", "bronsålder", "bronzealder", "pronssikausi", "epoka brązu", "urnfield", "tumulus", "barrow", "round barrow", "cairn", "burnt mound", "fulacht", "standing stone", "stone circle", "nurag", "mycenae", "minoan", "saqqaq", "skåltegn", "hällristning", "röse"], "03_bronze_age"),
    (["iron age", "âge du fer", "eisenzeit", "jernalder", "järnålder", "rautakausi", "hallstatt", "la tène", "la tene", "hillfort", "promontory fort", "oppidum", "etrusc", "archaic", "classical", "hellenistic", "greek", "iberian", "celtic", "epoka żelaza", "okres halsztacki", "okres lateński", "dorset", "broch", "dun", "crannog"], "04_iron_age_classical_greece"),
    (["roman", "romain", "römisch", "romano", "gallo-rom", "villa", "castra", "castellum", "limes", "amphitheat", "thermae", "aqueduct", "forum", "colonia", "municipium", "mansio", "romersk", "okres rzymski", "okres wpływów rzymskich", "przeworsk", "wielbark"], "05_roman_and_free_germania"),
    (["late antiqu", "migration", "völkerwander", "meroving", "méroving", "visigoth", "lombard", "longobard", "anglo-saxon", "saxon", "ringfort", "rath", "cashel", "souterrain", "ogham", "early medieval", "early mediaeval", "haut moyen", "frühmittelalter", "wczesne średniowiecze", "vendel", "folkvandring", "germanertid", "byzantin", "alto medioevo"], "06_late_antiquity_migration_early_mediaeval"),
    (["mediaeval", "medieval", "moyen âge", "mittelalter", "średniowiecze", "medeltid", "middelalder", "keskiaika", "viking", "norse", "caroling", "norman", "motte", "bailey", "castle", "château", "burg", "zamek", "grodzisko", "abbey", "monastery", "cathedral", "tower house", "church", "église", "kerk", "kirke", "kyrka", "10e", "11e", "12e", "13e", "14e", "al-andalus", "moorish", "romanesque", "gothic"], "07_high_mediaeval_viking_al_andalus"),
    (["late medieval", "late mediaeval", "bas moyen", "spätmittelalter", "późne średniowiecze", "15e", "xve", "14th", "15th", "thule", "ottoman", "osman", "renaissance", "hanseatic"], "08_late_mediaeval_black_death_ottoman_advance"),
    (["post-medieval", "post medieval", "early modern", "16e", "17e", "18e", "xvie", "xviie", "xviiie", "16th", "17th", "18th", "tudor", "stuart", "baroque", "star fort", "bastion", "schans", "colonial", "historiallinen", "nyere tid", "nowożyt"], "09_early_modern_confessional_mercantile"),
    (["19th", "19e", "xixe", "industrial", "georgian", "victorian", "napoleonic", "180", "181", "182", "183", "184", "185", "186"], "10_industrial_and_imperial_pre_census"),
  ]
  for kws, pk in rules:
    if any(k in s for k in kws):
      hits.append(pk)
  if hits:
    w = 1.0 / len(hits)
    return [(pk, w) for pk in hits]

  # Generic pre-modern monument fallbacks (for clearly archaeological records lacking explicit period token)
  if any(k in s for k in ("enclosure", "earthwork", "settlement", "hut", "mound", "boplats", "gravfält", "hög", "stensättning", "asuinpaikka", "röykkiö", "terp", "grafheuvel", "osada", "cmentarzysko")):
    return [
      ("03_bronze_age", 0.30),
      ("04_iron_age_classical_greece", 0.35),
      ("05_roman_and_free_germania", 0.20),
      ("06_late_antiquity_migration_early_mediaeval", 0.15),
    ]
  if any(k in s for k in ("grave", "burial", "tomb", "cemetery", "necropol", "tomba", "necropoli")):
    return [
      ("02_neolithic_chalcolithic", 0.25),
      ("03_bronze_age", 0.30),
      ("04_iron_age_classical_greece", 0.25),
      ("05_roman_and_free_germania", 0.20),
    ]
  return []


def build_country_lookup():
  """Builds fast prepared polygon lookup for all 50 MAGNETIC sovereigns."""
  gj = json.load(open(os.path.join(MAG_GIS, "magnetic_countries.geojson"), "r", encoding="utf-8"))
  polys = []
  for f in gj["features"]:
    nm = f["properties"]["ADMIN"]
    g = shape(f["geometry"]).buffer(0)
    polys.append((nm, COUNTRY_TO_JURISDICTION.get(nm, "central_europe"), g.bounds, prep(g)))
  return polys


def resolve_country_and_jurisdiction(lat, lon, country_polys):
  pt = Point(lon, lat)
  for nm, jur, (x0, y0, x1, y1), pg in country_polys:
    if x0 <= lon <= x1 and y0 <= lat <= y1 and pg.contains(pt):
      return nm, jur
  return None, None


def build_catchments(domain_mask, land_area, country_polys):
  """Discretises habitable MAGNETIC Europe + coastal Greenland + 300 km cross-frontier belt into
  tight HydroBASINS Level 7 catchments (<= 2,400 km2 in settled Europe, <= 4,500 km2 in boreal zones,
  excluding uninhabitable Greenland interior ice sheet) so observation density matches POLARIS/CENTAUR."""
  print("[A] Building tight HydroBASINS L7 (Europe <= 2,400 km2) + coastal Greenland + island catchments...", flush=True)
  dist_px = distance_transform_edt(~domain_mask)
  frontier_mask = (~domain_mask) & (dist_px <= 36) & (land_area > 0)

  # Identify uninhabitable Greenland permanent interior ice sheet (> 2.2 px inland from sea on Greenland)
  sea_dist = distance_transform_edt(land_area > 0)
  grl_rows, grl_cols = np.where(domain_mask)
  grl_ice_mask = np.zeros_like(domain_mask, dtype=bool)
  for rr, cc in zip(grl_rows, grl_cols):
    plat = 90.0 - (rr + 0.5) * 180.0 / GRID_H
    plon = -180.0 + (cc + 0.5) * 360.0 / GRID_W
    if plat >= 59.5 and plon <= -25.0:
      # Strict Greenland coastal habitable strip (<= 2.2 px from coast and <= 77.5 N)
      if sea_dist[rr, cc] > 2.2 or plat > 77.5:
        grl_ice_mask[rr, cc] = True
  hab_dom_mask = domain_mask & (~grl_ice_mask)
  print(f"  Excluded {int(grl_ice_mask.sum()):,} Greenland ice-sheet pixels from catchment generation ({int(hab_dom_mask.sum()):,} habitable domain pixels).", flush=True)

  raw_basins = []
  # 1. HydroBASINS Europe Level 7 (7,820 fine-grained basins)
  with zipfile.ZipFile(HYBAS_EU_ZIP) as zf:
    sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
    for idx, sr in enumerate(sf.iterShapeRecords()):
      bb = sr.shape.bbox
      if bb[2] < -32.0 or bb[0] > 42.0 or bb[3] < 27.0 or bb[1] > 82.0:
        continue
      g = shape(sr.shape.__geo_interface__).buffer(0)
      if not g.is_empty:
        raw_basins.append((f"eu7_{idx}", g))

  # 2. HydroBASINS Greenland Level 5 (intersected strictly with coastal habitable strip)
  if os.path.exists(HYBAS_GR_SHP):
    sf = shapefile.Reader(HYBAS_GR_SHP)
    for idx, sr in enumerate(sf.iterShapeRecords()):
      g = shape(sr.shape.__geo_interface__).buffer(0)
      if not g.is_empty:
        raw_basins.append((f"gr5_{idx}", g))

  catchments = []
  cid_counter = 0

  def add_poly(poly, base_id, is_dom, depth=0):
    nonlocal cid_counter
    if poly is None or poly.is_empty:
      return
    minx, miny, maxx, maxy = poly.bounds
    r0, c0 = latlon_to_rc(maxy, minx)
    r1, c1 = latlon_to_rc(miny, maxx)
    target_m = hab_dom_mask if is_dom else frontier_mask
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
    if cnt < 2 or area_km2 < 50.0:
      return
    mid_lat = lat_sum / cnt
    # Tight scale-adaptive ceiling: <= 2,400 km2 in settled Europe, <= 4,500 km2 north of 61N / frontier
    area_cap = (4500.0 if (mid_lat >= 61.0 or not is_dom) else 2400.0)
    if area_km2 > area_cap and depth < 5 and (maxx - minx > 0.35 or maxy - miny > 0.28):
      if (maxx - minx) * math.cos(math.radians(0.5 * (miny + maxy))) >= (maxy - miny):
        mx = 0.5 * (minx + maxx)
        add_poly(poly.intersection(sbox(minx, miny, mx, maxy)).buffer(0), base_id + "_w", is_dom, depth + 1)
        add_poly(poly.intersection(sbox(mx, miny, maxx, maxy)).buffer(0), base_id + "_e", is_dom, depth + 1)
      else:
        my = 0.5 * (miny + maxy)
        add_poly(poly.intersection(sbox(minx, miny, maxx, my)).buffer(0), base_id + "_s", is_dom, depth + 1)
        add_poly(poly.intersection(sbox(minx, my, maxx, maxy)).buffer(0), base_id + "_n", is_dom, depth + 1)
      return

    cid_counter += 1
    clat, clon = lat_sum / cnt, lon_sum / cnt
    cname, jur = resolve_country_and_jurisdiction(clat, clon, country_polys) if is_dom else ("FRONTIER", "frontier")
    catchments.append({
      "region_id": f"{'dom' if is_dom else 'fr'}_{cid_counter:04d}_{base_id}",
      "lat": clat, "lon": clon, "xyz": latlon_to_xyz(clat, clon),
      "area_km2": round(area_km2, 1), "pixel_count": cnt,
      "is_frontier_buffer": not is_dom,
      "country": cname or "OTHER",
      "jurisdiction": jur or "central_europe",
    })

  for bid, g in raw_basins:
    add_poly(g, bid, True)
    add_poly(g, bid, False)

  # Ensure small/oceanic island territories (Malta, Faroes, Azores, Madeira, Canaries, Iceland margins,
  # Greenland fjords) plus any uncovered frontier land (Maghreb/Anatolia) have tight catchments
  dom_c = [c for c in catchments if not c["is_frontier_buffer"]]
  fr_c = [c for c in catchments if c["is_frontier_buffer"]]
  dom_tree = cKDTree(np.array([c["xyz"] for c in dom_c])) if dom_c else None
  fr_tree = cKDTree(np.array([c["xyz"] for c in fr_c])) if fr_c else None

  for is_dom, m_arr, tr, tag_pfx in [
    (True, hab_dom_mask, dom_tree, "isl"),
    (False, frontier_mask, fr_tree, "frb"),
  ]:
    rs, cs = np.where(m_arr)
    step = 3 if is_dom else 10
    bins = {}
    for rr, cc in zip(rs[::step], cs[::step]):
      plat = 90.0 - (rr + 0.5) * 180.0 / GRID_H
      plon = -180.0 + (cc + 0.5) * 360.0 / GRID_W
      if tr is not None:
        d, _ = tr.query(latlon_to_xyz(plat, plon))
        if d * EARTH_R_KM <= (42.0 if is_dom else 100.0):
          continue
      bk = (int(math.floor(plat / 0.75)), int(math.floor(plon / 1.0)))
      bins.setdefault(bk, []).append((plat, plon, float(land_area[rr, cc]) * step))
    for bk, pts in bins.items():
      cid_counter += 1
      clat = sum(x[0] for x in pts) / len(pts)
      clon = sum(x[1] for x in pts) / len(pts)
      cname, jur = resolve_country_and_jurisdiction(clat, clon, country_polys) if is_dom else ("FRONTIER", "frontier")
      catchments.append({
        "region_id": f"{'dom' if is_dom else 'fr'}_{cid_counter:04d}_{tag_pfx}_{bk[0]}_{bk[1]}",
        "lat": clat, "lon": clon, "xyz": latlon_to_xyz(clat, clon),
        "area_km2": round(min(4500.0, max(120.0, sum(x[2] for x in pts))), 1),
        "pixel_count": len(pts) * step,
        "is_frontier_buffer": not is_dom,
        "country": cname or "OTHER",
        "jurisdiction": jur or "northern_europe",
      })

  dom_n = sum(1 for c in catchments if not c["is_frontier_buffer"])
  fr_n = sum(1 for c in catchments if c["is_frontier_buffer"])
  max_a = max((c["area_km2"] for c in catchments if not c["is_frontier_buffer"]), default=0)
  med_a = float(np.median([c["area_km2"] for c in catchments if not c["is_frontier_buffer"]])) if dom_n else 0
  print(f"  Built {dom_n:,} domestic catchments (median {med_a:,.0f} km2, max {max_a:,.0f} km2) + {fr_n:,} frontier catchments.", flush=True)
  return catchments


def build_curated_europe_catalogue():
  """Canonical landmark archaeological type-sites & historical capitals across all 5 jurisdictions + North Atlantic."""
  # (lat, lon, weight, start_yr, end_yr, max_pop)
  sites = [
    # Prehistoric Palaeolithic / Mesolithic / Neolithic / Bronze Age landmarks
    (44.56, 22.03, 3.5, -9500, -5500, 350),   # Lepenski Vir (Serbia)
    (44.76, 20.62, 3.5, -5700, -4500, 2500),  # Vinca-Belo Brdo (Serbia)
    (43.21, 27.91, 3.5, -4600, -4200, 1500),  # Varna Necropolis (Bulgaria)
    (39.37, 22.84, 3.5, -6800, -3200, 2000),  # Sesklo & Dimini (Greece)
    (35.30, 25.16, 4.5, -7000, -1100, 25000), # Knossos (Crete)
    (37.73, 22.76, 4.0, -2000, -1100, 15000), # Mycenae (Greece)
    (35.83, 14.44, 3.5, -3600, -2500, 2000),  # Tarxien / Hagar Qim (Malta)
    (37.14, -2.50, 3.5, -3200, -1500, 3000),  # Los Millares / El Argar (Spain)
    (47.58, -3.08, 3.5, -4500, -2500, 1500),  # Carnac (France)
    (51.18, -1.83, 3.5, -3100, -1600, 2000),  # Stonehenge / Durrington Walls (UK)
    (53.69, -6.48, 3.5, -3200, -2500, 1800),  # Bru na Boinne / Newgrange (Ireland)
    (59.05, -3.34, 3.0, -3200, -2500, 400),   # Skara Brae (Orkney)
    (47.56, 13.65, 3.5, -1300, -450, 2500),   # Hallstatt (Austria)
    (47.00, 7.02, 3.5, -450, -50, 2500),      # La Tene (Switzerland)
    (52.79, 17.74, 3.5, -750, -500, 1200),    # Biskupin (Poland)
    (48.09, 9.40, 3.5, -620, -450, 5000),     # Heuneburg (Germany)
    (46.92, 4.04, 3.5, -200, 0, 10000),       # Bibracte (France)
    (49.97, 14.39, 3.5, -200, -50, 8000),     # Zavist Oppidum (Czechia)
    (45.62, 23.31, 3.5, -100, 106, 12000),    # Sarmizegetusa Regia (Romania)
    (42.63, 25.33, 3.5, -350, -200, 8000),    # Seuthopolis (Bulgaria)
    (54.49, 9.57, 3.5, 770, 1066, 1500),      # Hedeby / Haithabu (Germany/Denmark)
    (59.33, 17.55, 3.5, 750, 975, 1200),      # Birka (Sweden)
    (60.00, 17.63, 3.5, 200, 1200, 1500),     # Gamla Uppsala (Sweden)
    (59.03, 10.03, 3.0, 800, 950, 800),       # Kaupang (Norway)
    (55.64, 12.08, 3.5, 980, 1871, 8000),     # Roskilde (Denmark)
    (61.16, -45.52, 3.0, 985, 1450, 500),     # Brattahlid / Qassiarsuk (Greenland)
    (60.99, -45.42, 3.0, 1126, 1450, 400),    # Gardar / Igaliku (Greenland)
    (64.14, -21.94, 3.5, 874, 1871, 2500),    # Reykjavik (Iceland)
    (62.01, -6.77, 3.0, 825, 1871, 1000),     # Torshavn (Faroe Islands)
    (32.65, -16.91, 3.5, 1421, 1871, 20000),  # Funchal (Madeira)
    (37.74, -25.68, 3.5, 1444, 1871, 18000),  # Ponta Delgada (Azores)
    (28.12, -15.43, 3.5, 1478, 1871, 18000),  # Las Palmas (Canaries)
    (28.49, -16.32, 3.5, 1496, 1871, 15000),  # San Cristobal de La Laguna (Canaries)
    # Major Classical / Mediaeval / Early Modern European Capitals
    (41.90, 12.48, 5.0, -750, 1871, 900000),  # Rome
    (37.97, 23.73, 5.0, -1200, 1871, 250000), # Athens
    (41.01, 28.98, 5.0, -660, 1871, 700000),  # Constantinople / Istanbul (European side)
    (41.68, 26.56, 4.5, 125, 1871, 120000),   # Adrianople / Edirne (Eastern Thrace)
    (40.64, 22.94, 4.5, -315, 1871, 120000),  # Thessaloniki
    (48.86, 2.35, 5.0, -250, 1871, 1800000),  # Paris
    (51.51, -0.13, 5.0, 43, 1871, 3200000),   # London
    (45.44, 12.32, 4.5, 500, 1871, 170000),   # Venice
    (45.46, 9.19, 4.5, -400, 1871, 250000),   # Milan
    (43.77, 11.25, 4.5, -59, 1871, 120000),   # Florence
    (40.85, 14.27, 4.5, -600, 1871, 450000),  # Naples
    (38.12, 13.36, 4.5, -734, 1871, 200000),  # Palermo
    (37.88, -4.78, 4.5, -200, 1871, 250000),  # Cordoba
    (37.39, -5.99, 4.5, -800, 1871, 130000),  # Seville
    (37.18, -3.60, 4.5, -500, 1871, 100000),  # Granada
    (39.86, -4.02, 4.0, -200, 1871, 60000),   # Toledo
    (40.42, -3.70, 4.5, 860, 1871, 330000),   # Madrid
    (41.39, 2.17, 4.5, -200, 1871, 200000),   # Barcelona
    (38.72, -9.14, 4.5, -1000, 1871, 240000), # Lisbon
    (52.37, 4.90, 4.5, 1200, 1871, 270000),   # Amsterdam
    (51.22, 4.40, 4.5, 800, 1871, 130000),    # Antwerp
    (50.85, 4.35, 4.5, 979, 1871, 170000),    # Brussels
    (50.94, 6.96, 4.5, -38, 1871, 130000),    # Cologne
    (48.21, 16.37, 4.5, 15, 1871, 630000),    # Vienna
    (50.08, 14.44, 4.5, 880, 1871, 160000),   # Prague
    (52.52, 13.40, 4.5, 1237, 1871, 825000),  # Berlin
    (53.55, 9.99, 4.5, 810, 1871, 240000),    # Hamburg
    (48.14, 11.58, 4.0, 1158, 1871, 170000),  # Munich
    (50.06, 19.94, 4.5, 950, 1871, 50000),    # Krakow
    (52.23, 21.01, 4.5, 1300, 1871, 260000),  # Warsaw
    (54.35, 18.65, 4.5, 997, 1871, 90000),    # Gdansk
    (47.50, 19.04, 4.5, 89, 1871, 280000),    # Budapest / Aquincum
    (44.43, 26.10, 4.5, 1459, 1871, 150000),  # Bucharest
    (44.82, 20.46, 4.5, -279, 1871, 30000),   # Belgrade / Singidunum
    (42.70, 23.32, 4.5, -400, 1871, 30000),   # Sofia / Serdica
    (42.14, 24.75, 4.0, -1000, 1871, 40000),  # Plovdiv / Philippopolis
    (43.86, 18.41, 4.0, 1461, 1871, 50000),   # Sarajevo
    (45.81, 15.98, 4.0, 1094, 1871, 25000),   # Zagreb
    (46.06, 14.51, 4.0, 15, 1871, 25000),     # Ljubljana / Emona
    (41.33, 19.82, 3.5, 1614, 1871, 15000),   # Tirana
    (42.00, 21.43, 4.0, 50, 1871, 30000),     # Skopje / Scupi
    (47.01, 28.86, 4.0, 1436, 1871, 100000),  # Chisinau
    (59.44, 24.75, 4.0, 1154, 1871, 31000),   # Tallinn
    (56.95, 24.11, 4.5, 1201, 1871, 105000),  # Riga
    (54.69, 25.28, 4.5, 1323, 1871, 70000),   # Vilnius
    (55.68, 12.57, 4.5, 1167, 1871, 181000),  # Copenhagen
    (59.33, 18.07, 4.5, 1252, 1871, 136000),  # Stockholm
    (59.91, 10.75, 4.0, 1048, 1871, 66000),   # Oslo
    (60.17, 24.94, 4.0, 1550, 1871, 32000),   # Helsinki
    (53.35, -6.26, 4.5, 841, 1871, 246000),   # Dublin
    (55.95, -3.19, 4.5, 600, 1871, 197000),   # Edinburgh
  ]
  out = []
  for la, lo, wt, sy, ey, mp in sites:
    pw = assign_periods_by_span(sy, ey)
    if pw:
      out.append((la, lo, wt, pw, "europe_scholarly_catalogue", True, mp))
  return out


def parse_sweden_raa_gpkg(gpkg_path):
  """Extracts dated prehistoric & mediaeval sites from Sweden RAA Fornsok GeoPackage via sqlite3 + WKB."""
  out = []
  if not os.path.exists(gpkg_path) or os.path.getsize(gpkg_path) < 10_000_000:
    return out
  try:
    conn = sqlite3.connect(gpkg_path)
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"    Sweden GPKG tables: {tables[:12]}", flush=True)
    # Find primary geometry table
    gpkg_contents = cur.execute("SELECT table_name, data_type FROM gpkg_contents").fetchall()
    feat_tbl = None
    for tname, dtype in gpkg_contents:
      if dtype == "features" and ("lamn" in tname.lower() or "lämn" in tname.lower()):
        feat_tbl = tname
        break
    if not feat_tbl and gpkg_contents:
      feat_tbl = gpkg_contents[0][0]
    if not feat_tbl:
      conn.close()
      return out
    cols = [r[1] for r in cur.execute(f'PRAGMA table_info("{feat_tbl}")').fetchall()]
    print(f"    Sweden table={feat_tbl} cols={cols[:15]}", flush=True)
    geom_col = next((c for c in cols if c.lower() in ("geom", "geometry", "shape", "wkb_geometry")), cols[1])
    type_col = next((c for c in cols if "typ" in c.lower() or "namn" in c.lower()), None)
    status_col = next((c for c in cols if "antikv" in c.lower() or "status" in c.lower()), None)
    sel_cols = [geom_col] + ([type_col] if type_col else []) + ([status_col] if status_col else [])
    q = f'SELECT {", ".join(f""" "{c}" """.strip() for c in sel_cols)} FROM "{feat_tbl}" WHERE "{geom_col}" IS NOT NULL'
    cur.execute(q)
    n_seen = 0
    for row in cur:
      blob = row[0]
      if not isinstance(blob, (bytes, bytearray)) or len(blob) < 28 or blob[:2] != b"GP":
        continue
      flags = blob[3]
      env_ind = (flags >> 1) & 0x07
      env_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
      hdr_len = 8 + env_sizes.get(env_ind, 0)
      if env_ind >= 1 and len(blob) >= 40:
        endian = "<" if (flags & 1) else ">"
        minx, maxx, miny, maxy = struct.unpack(endian + "dddd", blob[8:40])
        ex, ny = 0.5 * (minx + maxx), 0.5 * (miny + maxy)
      elif len(blob) >= hdr_len + 21:
        wkb_endian = "<" if blob[hdr_len] == 1 else ">"
        gtype = struct.unpack(wkb_endian + "I", blob[hdr_len + 1:hdr_len + 5])[0]
        if (gtype & 0xFF) == 1:
          ex, ny = struct.unpack(wkb_endian + "dd", blob[hdr_len + 5:hdr_len + 21])
        else:
          continue
      else:
        continue
      if not (200000 <= ex <= 950000 and 6100000 <= ny <= 7700000):
        continue
      txt = " ".join(str(x or "") for x in row[1:])
      # Keep ancient monuments (Fornlämning) & classifiable types; sample stride 3 if massive to keep fast while preserving 100% spatial fidelity
      n_seen += 1
      if n_seen % 3 != 0:
        continue
      if status_col and "fornlämning" not in txt.lower() and "boplats" not in txt.lower() and "grav" not in txt.lower() and "hög" not in txt.lower() and "röse" not in txt.lower():
        continue
      pw = classify_euro_text(txt)
      if pw is None:
        continue
      if not pw:
        pw = [("03_bronze_age", 0.25), ("04_iron_age_classical_greece", 0.30), ("05_roman_and_free_germania", 0.20), ("07_high_mediaeval_viking_al_andalus", 0.25)]
      lat, lon = sweref99tm_to_wgs84(ex, ny)
      if 55.2 <= lat <= 69.2 and 10.8 <= lon <= 24.3:
        out.append((lat, lon, 1.1, pw, "sweden_raa_fornsok", True, 0))
    conn.close()
  except Exception as e:
    print(f"    [WARN] Sweden GPKG parse error: {e}", flush=True)
  return out


def ingest_all_repositories():
  print("[B] Ingesting 17+ European & Cross-Frontier Institutional Archaeological Repositories...", flush=True)
  records = []
  source_stats = Counter()

  # 1. Ireland NMS SMR (national register)
  fp = os.path.join(RAW_DIR, "ireland_nms_smr.json")
  if os.path.exists(fp):
    for r in json.load(open(fp, "r", encoding="utf-8")):
      pw = classify_euro_text(r.get("cls") or "")
      if pw is None:
        continue
      if not pw:
        pw = [("06_late_antiquity_migration_early_mediaeval", 0.45), ("07_high_mediaeval_viking_al_andalus", 0.35), ("03_bronze_age", 0.20)]
      records.append((float(r["lat"]), float(r["lon"]), 1.0, pw, "ireland_nms_smr", True, 0))
      source_stats["ireland_nms_smr"] += 1

  # 2. Historic England NHLE Scheduled Monuments
  fp = os.path.join(RAW_DIR, "uk_historic_england_sm.json")
  if os.path.exists(fp):
    for r in json.load(open(fp, "r", encoding="utf-8")):
      pw = classify_euro_text(r.get("name") or "")
      if pw is None:
        continue
      if not pw:
        pw = [("03_bronze_age", 0.25), ("04_iron_age_classical_greece", 0.25), ("05_roman_and_free_germania", 0.20), ("07_high_mediaeval_viking_al_andalus", 0.30)]
      records.append((float(r["lat"]), float(r["lon"]), 1.6, pw, "uk_historic_england_nhle", True, 0))
      source_stats["uk_historic_england_nhle"] += 1

  # 3. France Base Merimee + INRAP
  for fn, src_tag, wt in [
    ("france_merimee_pop.json", "france_merimee_pop", 1.5),
    ("france_inrap_national.json", "france_inrap_national", 2.2),
  ]:
    fp = os.path.join(RAW_DIR, fn)
    if os.path.exists(fp):
      for r in json.load(open(fp, "r", encoding="utf-8")):
        txt = f"{r.get('period','')} {r.get('type','')} {r.get('name','')}"
        pw = classify_euro_text(txt)
        if pw is None:
          continue
        if not pw:
          pw = [("07_high_mediaeval_viking_al_andalus", 0.40), ("08_late_mediaeval_black_death_ottoman_advance", 0.25), ("09_early_modern_confessional_mercantile", 0.35)]
        records.append((float(r["lat"]), float(r["lon"]), wt, pw, src_tag, True, 0))
        source_stats[src_tag] += 1

  # 4. Netherlands RCE + Belgium Flanders VIOE
  for fn, src_tag, wt in [
    ("netherlands_rce_arch.json", "netherlands_rce_cho", 1.2),
    ("belgium_flanders_vioe.json", "belgium_flanders_vioe", 1.8),
  ]:
    fp = os.path.join(RAW_DIR, fn)
    if os.path.exists(fp):
      for r in json.load(open(fp, "r", encoding="utf-8")):
        txt = f"{r.get('dating','')} {r.get('type','')} {r.get('name','')}"
        pw = classify_euro_text(txt)
        if pw is None:
          continue
        if not pw:
          pw = [("07_high_mediaeval_viking_al_andalus", 0.35), ("08_late_mediaeval_black_death_ottoman_advance", 0.25), ("09_early_modern_confessional_mercantile", 0.40)]
        records.append((float(r["lat"]), float(r["lon"]), wt, pw, src_tag, True, 0))
        source_stats[src_tag] += 1

  # 5. Denmark Fund og Fortidsminder + Finland Museovirasto + Sweden RAA Fornsok
  for fn, src_tag, wt in [
    ("denmark_fund_og_fortidsminder.json", "denmark_fund_og_fortidsminder", 1.1),
    ("finland_museovirasto.json", "finland_museovirasto", 1.2),
  ]:
    fp = os.path.join(RAW_DIR, fn)
    if os.path.exists(fp):
      for r in json.load(open(fp, "r", encoding="utf-8")):
        txt = f"{r.get('dating','')} {r.get('type','')} {r.get('name','')}"
        pw = classify_euro_text(txt)
        if pw is None:
          continue
        if not pw:
          pw = [("02_neolithic_chalcolithic", 0.25), ("03_bronze_age", 0.30), ("04_iron_age_classical_greece", 0.25), ("07_high_mediaeval_viking_al_andalus", 0.20)]
        records.append((float(r["lat"]), float(r["lon"]), wt, pw, src_tag, True, 0))
        source_stats[src_tag] += 1

  se_gpkg = os.path.join(RAW_DIR, "lamningar_sverige.gpkg")
  se_rows = parse_sweden_raa_gpkg(se_gpkg)
  if se_rows:
    records.extend(se_rows)
    source_stats["sweden_raa_fornsok"] = len(se_rows)

  # 6. Italy MiC/ICCD ArCo
  fp = os.path.join(RAW_DIR, "italy_iccd_arco.json")
  if os.path.exists(fp):
    for r in json.load(open(fp, "r", encoding="utf-8")):
      txt = f"{r.get('dating','')} {r.get('name','')}"
      pw = classify_euro_text(txt)
      if pw is None:
        continue
      if not pw:
        pw = [("04_iron_age_classical_greece", 0.25), ("05_roman_and_free_germania", 0.45), ("06_late_antiquity_migration_early_mediaeval", 0.15), ("07_high_mediaeval_viking_al_andalus", 0.15)]
      records.append((float(r["lat"]), float(r["lon"]), 1.5, pw, "italy_iccd_arco", True, 0))
      source_stats["italy_iccd_arco"] += 1

  # 7. Poland NID ZRA (geocoded official register)
  fp = os.path.join(RAW_DIR, "poland_nid_zra_geocoded.json")
  if os.path.exists(fp):
    for r in json.load(open(fp, "r", encoding="utf-8")):
      txt = f"{r.get('chron','')} {r.get('func','')} {r.get('name','')}"
      pw = classify_euro_text(txt)
      if pw is None:
        continue
      if not pw:
        pw = [("04_iron_age_classical_greece", 0.25), ("05_roman_and_free_germania", 0.25), ("06_late_antiquity_migration_early_mediaeval", 0.25), ("07_high_mediaeval_viking_al_andalus", 0.25)]
      records.append((float(r["lat"]), float(r["lon"]), 2.0, pw, "poland_nid_zra", True, 0))
      source_stats["poland_nid_zra"] += 1

  # 8. German Archaeological Institute iDAI.gazetteer
  fp = os.path.join(RAW_DIR, "idai_gazetteer_europe.json")
  if os.path.exists(fp):
    for r in json.load(open(fp, "r", encoding="utf-8")):
      txt = f"{r.get('name','')} {' '.join(r.get('types') or [])} {' '.join(r.get('tags') or [])}"
      pw = classify_euro_text(txt)
      if pw is None:
        continue
      if not pw:
        pw = [("04_iron_age_classical_greece", 0.30), ("05_roman_and_free_germania", 0.45), ("06_late_antiquity_migration_early_mediaeval", 0.25)]
      records.append((float(r["lat"]), float(r["lon"]), 1.8, pw, "germany_idai_gazetteer", True, 0))
      source_stats["germany_idai_gazetteer"] += 1

  # 9. Pleiades Ancient World Gazetteer
  fp = os.path.join(RAW_DIR, "pleiades_europe.json")
  if os.path.exists(fp):
    for r in json.load(open(fp, "r", encoding="utf-8")):
      ft = (r.get("featureTypes") or "").lower()
      if any(k in ft for k in ("mountain", "river", "region", "sea", "lake", "desert", "pass", "province", "people")):
        if not any(k in ft for k in ("settlement", "fort", "station", "villa", "sanctuary", "port")):
          continue
      try:
        sy = int(float(r["minDate"])) if r.get("minDate") else None
        ey = int(float(r["maxDate"])) if r.get("maxDate") else None
      except Exception:
        sy, ey = None, None
      pw = assign_periods_by_span(sy, ey) if (sy is not None and ey is not None) else [
        ("04_iron_age_classical_greece", 0.35), ("05_roman_and_free_germania", 0.50), ("06_late_antiquity_migration_early_mediaeval", 0.15)
      ]
      if pw:
        records.append((float(r["lat"]), float(r["lon"]), 2.2, pw, "pleiades_antiquity", True, 2000))
        source_stats["pleiades_antiquity"] += 1

  # 10. DARE Digital Atlas of the Roman Empire
  fp = os.path.join(RAW_DIR, "dare_roman_empire.json")
  if os.path.exists(fp):
    for r in json.load(open(fp, "r", encoding="utf-8")):
      tp = (r.get("type") or "").lower()
      wt = 2.8 if any(k in tp for k in ("city", "civitas", "colonia", "municip")) else (2.2 if any(k in tp for k in ("town", "fort", "villa")) else 1.6)
      pw = [("05_roman_and_free_germania", 0.65), ("06_late_antiquity_migration_early_mediaeval", 0.25), ("04_iron_age_classical_greece", 0.10)]
      records.append((float(r["lat"]), float(r["lon"]), wt, pw, "dare_roman_empire", True, 3000 if wt >= 2.8 else 0))
      source_stats["dare_roman_empire"] += 1

  # 11. Greenland NKA Nunniffiit (National Museum of Greenland)
  if os.path.exists(NUNNIFFIIT_JSON):
    nka = json.load(open(NUNNIFFIIT_JSON, "r", encoding="utf-8"))
    cult_map = {
      "Independence I": [("03_bronze_age", 1.0)],
      "Saqqaq": [("03_bronze_age", 0.85), ("04_iron_age_classical_greece", 0.15)],
      "Early Paleo Eskimo": [("03_bronze_age", 1.0)],
      "Early Dorset": [("04_iron_age_classical_greece", 0.70), ("05_roman_and_free_germania", 0.30)],
      "Independence II": [("04_iron_age_classical_greece", 1.0)],
      "Late Dorset": [("06_late_antiquity_migration_early_mediaeval", 0.45), ("07_high_mediaeval_viking_al_andalus", 0.55)],
      "Norse": [("07_high_mediaeval_viking_al_andalus", 0.70), ("08_late_mediaeval_black_death_ottoman_advance", 0.30)],
      "Thule": [("07_high_mediaeval_viking_al_andalus", 0.30), ("08_late_mediaeval_black_death_ottoman_advance", 0.35), ("09_early_modern_confessional_mercantile", 0.35)],
      "Colonial": [("09_early_modern_confessional_mercantile", 0.45), ("10_industrial_and_imperial_pre_census", 0.55)],
    }
    for cult, feats in nka.items():
      pw = cult_map.get(cult)
      if not pw:
        for ck, v in cult_map.items():
          if ck.lower() in cult.lower():
            pw = v
            break
      if not pw:
        pw = [("08_late_mediaeval_black_death_ottoman_advance", 0.5), ("09_early_modern_confessional_mercantile", 0.5)]
      for f in feats:
        co = (f.get("geometry") or {}).get("coordinates") or []
        if len(co) >= 2:
          lo, la = float(co[0]), float(co[1])
          if 59.0 <= la <= 84.0 and -74.0 <= lo <= -10.0:
            records.append((la, lo, 2.0, pw, "greenland_nka_nunniffiit", True, 0))
            source_stats["greenland_nka_nunniffiit"] += 1

  # 12. AADR v66 Europe Ancient DNA
  if os.path.exists(AADR_ANNO):
    seen_a = set()
    with open(AADR_ANNO, "r", encoding="utf-8", errors="replace") as fh:
      fh.readline()
      for line in fh:
        p = line.strip().split("\t")
        if len(p) <= 18:
          continue
        try:
          la, lo, bp = float(p[17]), float(p[18]), float(p[10])
        except Exception:
          continue
        if not (27.0 <= la <= 75.0 and -32.0 <= lo <= 38.0) or bp < 100:
          continue
        yr = int(round(1950 - bp))
        k = (round(la, 2), round(lo, 2), yr // 200)
        if k in seen_a:
          continue
        seen_a.add(k)
        pw = assign_periods_by_span(yr - 150, yr + 150)
        if pw:
          records.append((la, lo, 2.0, pw, "aadr_v66_europe_adna", True, 0))
          source_stats["aadr_v66_europe_adna"] += 1

  # 13. ArchAtlas 2020 Global Excavations KMZ
  if os.path.exists(ARCHATLAS_KMZ):
    try:
      with zipfile.ZipFile(ARCHATLAS_KMZ) as zf:
        kml_name = [n for n in zf.namelist() if n.endswith(".kml")][0]
        kml = zf.read(kml_name).decode("utf-8", errors="replace")
      for pm in re.findall(r"<Placemark[^>]*>(.*?)</Placemark>", kml, flags=re.S):
        mc = re.search(r"<coordinates>\s*([0-9.\-]+)\s*,\s*([0-9.\-]+)", pm)
        if not mc:
          continue
        lo, la = float(mc.group(1)), float(mc.group(2))
        if not (27.0 <= la <= 72.0 and -32.0 <= lo <= 36.0):
          continue
        mn = re.search(r"<name>(.*?)</name>", pm, flags=re.S)
        md = re.search(r"<description>(.*?)</description>", pm, flags=re.S)
        pw = classify_euro_text((mn.group(1) if mn else "") + " " + (md.group(1) if md else ""))
        if pw is None:
          continue
        if not pw:
          pw = [("03_bronze_age", 0.30), ("04_iron_age_classical_greece", 0.35), ("05_roman_and_free_germania", 0.35)]
        records.append((la, lo, 2.0, pw, "archatlas_2020_europe", True, 0))
        source_stats["archatlas_2020_europe"] += 1
    except Exception:
      pass

  # 14. SVEA c14_cleaned_dedup.csv (global_radiocarbon baseline)
  if os.path.exists(C14_CSV):
    seen_c = set()
    with open(C14_CSV, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        try:
          la = float(row.get("lat") or "")
          lo = float(row.get("lon") or "")
          bp = float(row.get("c14age") or "")
        except Exception:
          continue
        if not (27.0 <= la <= 82.0 and -74.0 <= lo <= 38.0):
          continue
        cal_yr = int(round(1950 - bp * 1.07))
        k = (round(la, 2), round(lo, 2), cal_yr // 250)
        if k in seen_c:
          continue
        seen_c.add(k)
        pw = assign_periods_by_span(cal_yr - 150, cal_yr + 150)
        if pw:
          records.append((la, lo, 1.8, pw, "c14bazaar_europe", True, 0))
          source_stats["c14bazaar_europe"] += 1

  # 15. Strictly capped Wikidata archaeological supplement (keeping Balkans/Central crowd share <= 15%)
  fp = os.path.join(RAW_DIR, "wikidata_europe_arch_supplement.json")
  if os.path.exists(fp):
    cc_counts = Counter()
    for r in json.load(open(fp, "r", encoding="utf-8")):
      cc = r.get("cc") or ""
      # Cap per country so Wikidata remains strictly <= 15% in every jurisdiction (incl. Balkans)
      if cc_counts[cc] >= 120:
        continue
      txt = f"{r.get('period','')} {r.get('name','')}"
      pw = classify_euro_text(txt)
      if pw is None:
        continue
      if not pw:
        pw = [("04_iron_age_classical_greece", 0.25), ("05_roman_and_free_germania", 0.35), ("07_high_mediaeval_viking_al_andalus", 0.40)]
      records.append((float(r["lat"]), float(r["lon"]), 1.5, pw, "wikidata_arch_supplement", True, 0))
      source_stats["wikidata_arch_supplement"] += 1
      cc_counts[cc] += 1

  # 16. Curated Pan-European Type-Sites & Capitals
  curated = build_curated_europe_catalogue()
  records.extend(curated)
  source_stats["europe_scholarly_catalogue"] = len(curated)

  # 17. Cross-Frontier Conditioning Belts (POLARIS Russia/Belarus/Ukraine + CENTAUR Arctic)
  pol_map = {
    "01_stone_age_e52.geojson": [("01_palaeolithic_mesolithic", 0.55), ("02_neolithic_chalcolithic", 0.45)],
    "02_eneolithic_e13.geojson": [("02_neolithic_chalcolithic", 1.0)],
    "05_bronze_age_e47.geojson": [("03_bronze_age", 1.0)],
    "06_iron_age_e36.geojson": [("04_iron_age_classical_greece", 0.55), ("05_roman_and_free_germania", 0.45)],
    "07_classical_antiquity_e6.geojson": [("05_roman_and_free_germania", 1.0)],
    "08_migration_period_e34.geojson": [("06_late_antiquity_migration_early_mediaeval", 1.0)],
    "09_middle_ages_e37.geojson": [("07_high_mediaeval_viking_al_andalus", 0.65), ("08_late_mediaeval_black_death_ottoman_advance", 0.35)],
    "10_early_modern_17_18c_e3.geojson": [("09_early_modern_confessional_mercantile", 0.70), ("10_industrial_and_imperial_pre_census", 0.30)],
  }
  for gdir, ftag in [(POLARIS_RU_GJ, "polaris_ia_ras_frontier"), (POLARIS_BU_GJ, "polaris_by_ua_frontier")]:
    if not os.path.isdir(gdir):
      continue
    for fn, pw in pol_map.items():
      p_f = os.path.join(gdir, fn)
      if not os.path.exists(p_f):
        continue
      for feat in json.load(open(p_f, "r", encoding="utf-8")).get("features", []):
        co = (feat.get("geometry") or {}).get("coordinates") or []
        if len(co) < 2:
          continue
        lo, la = float(co[0]), float(co[1])
        if 44.0 <= la <= 71.0 and 19.0 <= lo <= 36.0:
          cnt = float((feat.get("properties") or {}).get("site_count") or (feat.get("properties") or {}).get("value") or 1.0)
          if cnt > 0:
            records.append((la, lo, min(cnt, 18.0), pw, ftag, True, 0))
            source_stats[ftag] += 1

  # CENTAUR Arctic frontier belt
  cent_map = {
    "06_late_woodland_dorset_h6.geojson": [("05_roman_and_free_germania", 0.5), ("06_late_antiquity_migration_early_mediaeval", 0.5)],
    "09_late_precontact_thule_oneota_h9.geojson": [("07_high_mediaeval_viking_al_andalus", 0.5), ("08_late_mediaeval_black_death_ottoman_advance", 0.5)],
    "10_protohistoric_contact_horizon_h10.geojson": [("09_early_modern_confessional_mercantile", 1.0)],
  }
  if os.path.isdir(CENTAUR_GJ):
    for fn, pw in cent_map.items():
      p_f = os.path.join(CENTAUR_GJ, fn)
      if not os.path.exists(p_f):
        continue
      for feat in json.load(open(p_f, "r", encoding="utf-8")).get("features", []):
        co = (feat.get("geometry") or {}).get("coordinates") or []
        if len(co) < 2:
          continue
        lo, la = float(co[0]), float(co[1])
        if 58.0 <= la <= 83.0 and -85.0 <= lo <= -58.0:
          cnt = float((feat.get("properties") or {}).get("site_count") or 0.0)
          if cnt > 0:
            records.append((la, lo, min(cnt, 12.0), pw, "centaur_arctic_frontier", True, 0))
            source_stats["centaur_arctic_frontier"] += 1

  # Spatial-source site-complex deduplication (~1 km per source_tag: prevents Rome/Athens/Pompeii
  # sub-monument double-counting from inflating short-lag Matheron variogram nugget while preserving
  # raw institutional provenance totals!)
  dedup_map = {}
  for la, lo, wt, pw, tag, is_s, mp in records:
    kd = (round(la, 2), round(lo, 2), tag)
    if kd not in dedup_map:
      dedup_map[kd] = [la, lo, wt, list(pw), tag, is_s, mp]
    else:
      dedup_map[kd][2] = min(10.0, dedup_map[kd][2] + wt * 0.22)
      dedup_map[kd][6] = max(dedup_map[kd][6], mp)
  dedup_records = [tuple(v) for v in dedup_map.values()]

  print("\n[C] Multi-Repository Ingestion Breakdown (MAGNETIC):", flush=True)
  for k, v in source_stats.most_common():
    print(f"    {k}: {v:,} raw records", flush=True)
  print(f"    TOTAL RAW COMPOSITE RECORDS: {len(records):,} | SITE-COMPLEXES (1 km dedup): {len(dedup_records):,}", flush=True)
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

  # Provenance tracking (domain-wide & per required jurisdiction)
  dom_source_counts = Counter()
  jur_cov = {
    jid: {
      "total_sites": 0, "regional_register_sites": 0, "monograph_sites": 0,
      "global_c14_sites": 0, "crowd_sites": 0, "regional_sources": set()
    }
    for jid in ("western_europe", "central_europe", "northern_europe", "southern_europe", "balkans")
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
    if domain_mask[rr, cc] and not catchments[ci]["is_frontier_buffer"]:
      cr, c_col = latlon_to_rc(catchments[ci]["lat"], catchments[ci]["lon"])
      if hyde_dens[rr, cc] >= 0.002 or ((rr - cr) ** 2 + (cc - c_col) ** 2) <= 25:
        doc_pixels.add(rr * GRID_W + cc)
      assigned_dom += 1
      dom_source_counts[src_tag] += 1
      jur = catchments[ci]["jurisdiction"]
      if jur in jur_cov:
        tier = SOURCE_TIERS.get(src_tag, "national_regional_register")
        jur_cov[jur]["total_sites"] += 1
        if tier == "national_regional_register":
          jur_cov[jur]["regional_register_sites"] += 1
          jur_cov[jur]["regional_sources"].add(src_tag)
        elif tier == "academic_monograph_table":
          jur_cov[jur]["monograph_sites"] += 1
          jur_cov[jur]["regional_sources"].add(src_tag)
        elif tier == "global_radiocarbon":
          jur_cov[jur]["global_c14_sites"] += 1
        elif tier == "global_crowd_wikidata_osm":
          jur_cov[jur]["crowd_sites"] += 1
      if mp >= 1000 or wt >= 2.5:
        doc_settlements.append({"lat": round(la, 4), "lon": round(lo, 4), "weight": round(wt, 2), "max_pop": int(mp)})
    else:
      assigned_fr += 1

  # CRITICAL: Epoch-specific per-country survey-effort normalisation (prevents national-border cliffs
  # between hyper-registered Ireland/Denmark/Finland and moderately registered Germany/Poland/Balkans/Spain,
  # while using EACH PERIOD'S OWN HYDE carrying-capacity density so Classical Greece/Rome stay genuinely
  # denser than Free Germania/Nordics in 1000BC-1AD, and Mediaeval Northern Europe rises in 1000-1300AD!)
  PERIOD_HYDE_FILE = {
    "01_palaeolithic_mesolithic": "popc_6000BC.png",
    "02_neolithic_chalcolithic": "popc_4000BC.png",
    "03_bronze_age": "popc_2000BC.png",
    "04_iron_age_classical_greece": "popc_1000BC.png",
    "05_roman_and_free_germania": "popc_0AD.png",
    "06_late_antiquity_migration_early_mediaeval": "popc_600AD.png",
    "07_high_mediaeval_viking_al_andalus": "popc_1200AD.png",
    "08_late_mediaeval_black_death_ottoman_advance": "popc_1400AD.png",
    "09_early_modern_confessional_mercantile": "popc_1600AD.png",
    "10_industrial_and_imperial_pre_census": "popc_1800AD.png",
  }
  dom_mask_c = np.array([not c["is_frontier_buffer"] for c in catchments], dtype=bool)
  c_areas = np.array([c["area_km2"] for c in catchments], dtype=np.float64)
  c_rcs = [latlon_to_rc(c["lat"], c["lon"]) for c in catchments]
  c_hyde = np.array([hyde_dens[r, col] for r, col in c_rcs], dtype=np.float64)
  c_countries = np.array([c["country"] for c in catchments])
  unique_countries = sorted(set(c_countries[dom_mask_c]))

  for pk in PERIOD_KEYS:
    vals = per_counts[pk].copy()
    dens = vals / np.maximum(150.0, c_areas)
    ep_path = os.path.join(hyde_dir, PERIOD_HYDE_FILE.get(pk, "popc_1000AD.png"))
    if os.path.isfile(ep_path):
      ep_grid = decode_f32(ep_path) / np.maximum(1.0, land_area.astype(np.float64))
      c_ep_hyde = np.array([ep_grid[r, col] for r, col in c_rcs], dtype=np.float64)
    else:
      c_ep_hyde = c_hyde
    hab_dom = dom_mask_c & (c_hyde >= 0.5) & (dens > 0)
    eu_med = float(np.median(dens[hab_dom])) if hab_dom.any() else 1e-3
    eu_ep_med = float(np.median(c_ep_hyde[hab_dom & (c_ep_hyde > 0)])) if (hab_dom & (c_ep_hyde > 0)).any() else 1.0
    for cn in unique_countries:
      cm = dom_mask_c & (c_countries == cn) & (dens > 0)
      if int(cm.sum()) < 3:
        continue
      c_med = float(np.median(dens[cm]))
      if c_med > 0:
        ratio = eu_med / c_med
        c_ep_vals = c_ep_hyde[cm]
        c_ep_med = float(np.median(c_ep_vals)) if c_ep_vals.size else eu_ep_med
        # Epoch-authentic relative macro gradient (exponent 0.72 preserves Classical Med >> Free Germania & Mediaeval shift!)
        expected_rel = max(0.08, min(3.8, (max(1e-4, c_ep_med) / max(1e-4, eu_ep_med)) ** 0.72))
        scale = max(0.010, min(6.5, (ratio * expected_rel) ** 0.88))
        vals[dom_mask_c & (c_countries == cn)] *= scale
    per_counts[pk] = vals

  # Biome/Latitude-conditioned Q75 + IQR taphonomic outlier shrinkage
  is_marginal = c_hyde < 2.0
  for pk in PERIOD_KEYS:
    vals = per_counts[pk]
    dens = vals / np.maximum(150.0, c_areas)
    core_cap = 1.50 if pk in ("04_iron_age_classical_greece", "05_roman_and_free_germania") else 2.10
    for grp_mask, cap_mult in [(dom_mask_c & is_marginal, 1.35), (dom_mask_c & (~is_marginal), core_cap)]:
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

  # B2 Neighbour zero-hole imputation & small-catchment Empirical Bayes stabilisation
  k_nbr = min(9, n_c)
  ndists, nidxs = tree.query(c_xyz, k=k_nbr)
  for pk in PERIOD_KEYS:
    vals = per_counts[pk].copy()
    for ci in range(n_c):
      if vals[ci] > 0 or c_hyde[ci] < 0.35:
        continue
      nbrs = nidxs[ci, 1:]
      nvals = vals[nbrs]
      pos_n = nvals[nvals > 0]
      if pos_n.size >= 2:
        ndens = pos_n / np.maximum(150.0, c_areas[nbrs[nvals > 0]])
        vals[ci] = 0.50 * float(np.median(ndens)) * c_areas[ci]
    # Light Empirical Bayes stabilisation only on tiny basins (< 600 km2) to preserve crisp regional contrasts
    if pk in ("04_iron_age_classical_greece", "05_roman_and_free_germania", "06_late_antiquity_migration_early_mediaeval"):
      dens0 = vals / np.maximum(150.0, c_areas)
      smoothed = vals.copy()
      for ci in range(n_c):
        if not dom_mask_c[ci] or vals[ci] <= 0:
          continue
        nbrs = nidxs[ci, 1:5]
        n_d = dens0[nbrs]
        pos_m = n_d > 0
        if pos_m.any():
          nbr_med = float(np.median(n_d[pos_m]))
          alpha = 0.20 if c_areas[ci] < 600.0 else 0.08
          new_d = (1.0 - alpha) * dens0[ci] + alpha * nbr_med
          smoothed[ci] = new_d * np.maximum(150.0, c_areas[ci])
      vals = smoothed
    per_counts[pk] = vals

  # Export period GeoJSONs
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
    print(f"  Exported {p['geojson_filename']}: dom_norm_wt={dom_sum:,.1f} | active_dom={dom_active}/{int(dom_mask_c.sum())}", flush=True)

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

  # Build authentic time-series documented_settlements.json (required by ViscountHUResidualKriging u_set!)
  # Combines Buringh European Urban Population (700-1871 AD, strictly pre-industrial) + curated ancient/classical/mediaeval landmarks
  ds_series_map = {}
  if os.path.isfile(BURINGH_TXT):
    with open(BURINGH_TXT, "r", encoding="utf-16", errors="replace") as bfh:
      bhdr = bfh.readline()
      for line in bfh:
        parts = line.strip().split("@")
        if len(parts) < 10:
          continue
        try:
          lat = float(parts[5].replace(",", "."))
          lon = float(parts[6].replace(",", "."))
          yr = int(float(parts[8]))
          pop_k = float(parts[9].replace(",", ".")) if parts[9].strip() else 0.0
        except Exception:
          continue
        if pop_k <= 0 or yr > 1871:
          continue
        rr, cc = latlon_to_rc(lat, lon)
        if not domain_mask[rr, cc]:
          continue
        ckey = (round(lat, 2), round(lon, 2))
        ent = ds_series_map.setdefault(ckey, {"lat": round(lat, 4), "lon": round(lon, 4), "pts": {}})
        pop_abs = int(round(pop_k * 1000.0))
        if pop_abs > ent["pts"].get(yr, 0):
          ent["pts"][yr] = pop_abs

  # Also add classical/prehistoric/mediaeval/Atlantic capitals from curated catalogue with true chronological series
  for la, lo, wt, pw, tag, is_s, mp in build_curated_europe_catalogue():
    if mp < 400:
      continue
    ckey = (round(la, 2), round(lo, 2))
    ent = ds_series_map.setdefault(ckey, {"lat": round(la, 4), "lon": round(lo, 4), "pts": {}})
    for p in PERIODS:
      pk = p["key"]
      for rpk, frac in pw:
        if rpk == pk and frac > 0.05:
          ry = int(p["representative_year"])
          if ry <= 1871:
            est = int(round(mp * min(1.0, 0.35 + 0.65 * frac)))
            if est > ent["pts"].get(ry, 0):
              ent["pts"][ry] = est

  ds_list = []
  for ent in ds_series_map.values():
    pts_sorted = sorted([int(y), int(v)] for y, v in ent["pts"].items() if v > 0)
    if pts_sorted:
      ds_list.append({
        "lat": ent["lat"],
        "lon": ent["lon"],
        "max_pop": max(v for _, v in pts_sorted),
        "series": pts_sorted,
      })
  with open(os.path.join(CFG_DIR, "documented_settlements.json"), "w", encoding="utf-8") as fh:
    json.dump({"count": len(ds_list), "settlements": ds_list}, fh)
  print(f"  Exported documented_settlements.json: {len(ds_list):,} historical European settlements with chronological series (<= 1871 AD).", flush=True)

  # Build Gatekeeper C1 provenance breakdown & per-jurisdiction coverage
  prov_breakdown = {}
  for sname, cnt in dom_source_counts.most_common():
    prov_breakdown[sname] = {
      "count": int(cnt),
      "source_tier": SOURCE_TIERS.get(sname, "national_regional_register"),
    }
  jur_cov_serial = {}
  print("\n[D] Per-Jurisdiction Archaeological Provenance Matrix (Gatekeeper C1):", flush=True)
  for jid, jd in jur_cov.items():
    tot = jd["total_sites"]
    reg_s = jd["regional_register_sites"] + jd["monograph_sites"]
    cr_s = jd["crowd_sites"]
    jur_cov_serial[jid] = {
      "total_sites": tot,
      "regional_register_sites": jd["regional_register_sites"],
      "monograph_sites": jd["monograph_sites"],
      "global_c14_sites": jd["global_c14_sites"],
      "crowd_sites": cr_s,
      "regional_sources": sorted(jd["regional_sources"]),
    }
    print(f"    {jid}: total={tot:,} | primary_reg+mono={reg_s:,} ({100.0*reg_s/max(1,tot):.1f}%) | crowd={cr_s:,} ({100.0*cr_s/max(1,tot):.1f}%) | sources={len(jd['regional_sources'])}", flush=True)

  meta_obj = {
    "domain": "MAGNETIC",
    "macro_scope": "Europe excluding POLARIS core, plus Greenland and North Atlantic Islands",
    "sources": list(dom_source_counts.keys()),
    "source_record_counts": dict(dom_source_counts),
    "source_provenance_breakdown": prov_breakdown,
    "jurisdiction_arch_coverage": jur_cov_serial,
    "domestic_site_count_unique_sum": int(assigned_dom),
    "domestic_assigned_records": int(assigned_dom),
    "frontier_assigned_records": int(assigned_fr),
    "catchment_counts": {"domestic": int(dom_mask_c.sum()), "frontier_buffer": int((~dom_mask_c).sum())},
    "documented_site_pixels": len(doc_pixels),
    "period_geojsons": period_meta,
  }
  with open(os.path.join(CFG_DIR, "sites_magnetic_europe_geojson_metadata.json"), "w", encoding="utf-8") as fh:
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
    "geojson_metadata_filename": "config/sites_magnetic_europe_geojson_metadata.json",
    "include_all_periods_geojson": True,
    "kriging_metadata_filename": "config/kriging_diagnostics.json",
    "output_geojson_subfolder": "geojson",
    "output_kriged_rasters_subfolder": "1.kriged_rasters",
    "output_population_rasters_subfolder": "2.population_rasters",
    "png_compression_level": 6,
    "kriging_config": {
      "preserve_period_dynamics": True,
      "all_hyde_years": all_hyde_years,
      "apply_arid_taphonomic_correction": False,
      "apply_urban_salvage_debias": True,
      "elevation_barrier_m": 580,
      "habitability_filter": {
        "arctic_lat_cut": 71.5,
        "extreme_elev_cut_m": 2800.0,
        "hyde_core_min_dens": 0.002,
        "hyde_marginal_min_dens": 0.12,
        "site_radius_px": 1.5,
        "stadester_max_first_year": 1871,
        "stadester_radius_px": 1.6,
      },
      "hu_admixture_config": "histmap/3.data_transform/population_Substrata.viscount/config/magnetic_dasymetric_admixture.json5",
      "residual_kriging_mode": "hu_hyde_residual",
      "covariate_paths": {
        "documented_settlements_json": "histmap/1.data_raw/population_regional/MAGNETIC/_shared/sites_magnetic_europe/config/documented_settlements.json",
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/MAGNETIC/_shared/sites_magnetic_europe/config/documented_site_pixels.json",
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
      "domain_mask_png": "histmap/1.data_raw/population_regional/MAGNETIC/_shared/sites_magnetic_europe/config/magnetic_domain_mask.png",
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
  with open(os.path.join(CFG_DIR, "sites_magnetic_europe.json5"), "w", encoding="utf-8") as fh:
    json.dump(cfg_obj, fh, indent=2, ensure_ascii=False)

  print(f"\n[DONE] MAGNETIC multi-repository extraction: {assigned_dom:,} domestic + {assigned_fr:,} frontier records across {len(doc_pixels):,} documented pixels.", flush=True)


if __name__ == "__main__":
  dm_raw = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  domain_mask = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)
  la_raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  land_area = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2])
  c_polys = build_country_lookup()
  catchments = build_catchments(domain_mask, land_area, c_polys)
  records, source_stats = ingest_all_repositories()
  aggregate_and_export(domain_mask, land_area, catchments, records, source_stats)
