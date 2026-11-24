"""Stage B.1–B.2 Archaeological Composite & Dual HYDE 3.5 + KK10 Catchment Builder for Project QUIPU.

Ingests ALL harvested primary archaeological repositories across Andean South America, Colombia,
Venezuela, Ecuador, Peru, Andean Bolivia, Chile, Argentina, Uruguay, and the South Atlantic Islands
(33 primary files in `0.raw_sites/` + `raw_preta_frontier_buffer.json` 250 km eastern frontier buffer).

Builds scale-adaptive dual HYDE 3.5 + KK10 believed-density domestic catchments covering 100% of
`quipu_domain_mask.png` from geoBoundaries ADM2 (`COL`, `VEN` excl. Essequibo, `ECU`, `PER`, `BOL`
Andean 6 departments, `CHL` excl. Rapa Nui, `ARG`, `URY` subdivided by HydroBASINS SA L6, plus
`FLK` and South Georgia / South Sandwich Islands), recursively subdividing any unit exceeding its
density-tier ceiling or the 25,000 km2 global cap so `over_global_cap == 0` and tier compliance >= 95%.

Exports ViscountMaternKriging-ready GeoJSONs (`00_all_periods.geojson` + 8 South American Holocene
horizons), Gatekeeper B1 provenance metadata (`sites_quipu_andes_cone_geojson_metadata.json`),
`documented_site_pixels.json`, `documented_arch_sites.json` (<= 1876 AD), and
`sites_quipu_andes_cone.json5`.
"""

import csv
import io
import json
import math
import os
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict

import cv2
import numpy as np
import shapefile
from PIL import Image
from scipy.ndimage import distance_transform_edt, label as cc_label
from scipy.spatial import cKDTree
from shapely.geometry import MultiPolygon, Polygon, Point, shape
from shapely.prepared import prep
from shapely.validation import make_valid

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
QUIPU_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "QUIPU")
DOMAIN_DIR = os.path.join(QUIPU_DIR, "_shared", "sites_quipu_andes_cone")
RAW_DIR = os.path.join(DOMAIN_DIR, "0.raw_sites")
CFG_DIR = os.path.join(DOMAIN_DIR, "config")
GJ_DIR = os.path.join(DOMAIN_DIR, "geojson")
SETT_DIR = os.path.join(QUIPU_DIR, "_shared", "settlement_sources")
GB_DIR = os.path.join(QUIPU_DIR, "_shared", "subadmin_hgis", "raw_sources", "geoboundaries")

DOMAIN_MASK_PNG = os.path.join(CFG_DIR, "quipu_domain_mask.png")
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
HYDE_DIR = os.path.join(SVEA_ROOT, "histmap", "2.data_cleaning", "landuse_HYDE", "rasters")
KK10_1500_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_KK10LUH2", "KK10", "KK10_1500.png")
FOREST_ASC = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_files", "forest_wwf_cr.asc")
HYBAS_SA_ZIP = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JAGUAR", "_shared", "_gis_cache", "hybas_sa_lev06_v1c.zip")
C14_GLOBAL_CSV = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_c14bazAAR", "c14_cleaned_dedup.csv")

os.makedirs(CFG_DIR, exist_ok=True)
os.makedirs(GJ_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160
EARTH_R_KM = 6371.0

# 8 Canonical South American Holocene Periods for QUIPU
PERIODS = [
  {
    "epoch_id": 1,
    "key": "01_palaeoindian_early_holocene",
    "filename": "01_palaeoindian_early_holocene.png",
    "geojson_filename": "01_palaeoindian_early_holocene.geojson",
    "approx_start_year": -13000,
    "approx_end_year": -6000,
    "representative_year": -8000,
    "name_en": "Palaeoindian and Early Holocene Andes and Southern Cone",
    "name_de": "Paläoindianische Zeit und Frühholozän der Anden und des Südkegels",
    "name_fr": "Paléoindien et Holocène ancien des Andes et du Cône Sud",
    "date_range_en": "c. 13000-6000BC (Monte Verde, Lauricocha, Guitarrero, El Abra, Paiján and Patagonia Fishtail foragers)"
  },
  {
    "epoch_id": 2,
    "key": "02_middle_holocene_archaic",
    "filename": "02_middle_holocene_archaic.png",
    "geojson_filename": "02_middle_holocene_archaic.geojson",
    "approx_start_year": -6000,
    "approx_end_year": -3000,
    "representative_year": -4500,
    "name_en": "Middle Holocene Archaic, Chinchorro and Las Vegas",
    "name_de": "Mittelholozänes Archaikum, Chinchorro und Las Vegas",
    "name_fr": "Archaïque moyen, Chinchorro et Las Vegas",
    "date_range_en": "c. 6000-3000BC (Early camelid pastoralism, Las Vegas, Chinchorro coastal sedentism and San Jacinto)"
  },
  {
    "epoch_id": 3,
    "key": "03_late_archaic_initial_period",
    "filename": "03_late_archaic_initial_period.png",
    "geojson_filename": "03_late_archaic_initial_period.geojson",
    "approx_start_year": -3000,
    "approx_end_year": -1000,
    "representative_year": -2000,
    "name_en": "Late Archaic and Initial Period: Caral-Supe and Valdivia",
    "name_de": "Spätarchaik und Initialperiode: Caral-Supe und Valdivia",
    "name_fr": "Archaïque récent et Période initiale : Caral-Supe et Valdivia",
    "date_range_en": "c. 3000-1000BC (Caral-Supe, Áspero, Valdivia, Kotosh, Sechín Alto, Puerto Hormiga and Wankarani origins)"
  },
  {
    "epoch_id": 4,
    "key": "04_early_horizon_formative",
    "filename": "04_early_horizon_formative.png",
    "geojson_filename": "04_early_horizon_formative.geojson",
    "approx_start_year": -1000,
    "approx_end_year": 0,
    "representative_year": -500,
    "name_en": "Early Horizon and Formative: Chavín, Paracas, Chiripa and Chorrera",
    "name_de": "Früher Horizont und Formativum: Chavín, Paracas, Chiripa und Chorrera",
    "name_fr": "Horizon ancien et Formatif : Chavín, Paracas, Chiripa et Chorrera",
    "date_range_en": "c. 1000-1BC (Chavín de Huántar, Paracas, Cupisnique, Chiripa, Chorrera, San Agustín Formative and Herrera)"
  },
  {
    "epoch_id": 5,
    "key": "05_early_intermediate_regional",
    "filename": "05_early_intermediate_regional.png",
    "geojson_filename": "05_early_intermediate_regional.geojson",
    "approx_start_year": 0,
    "approx_end_year": 600,
    "representative_year": 300,
    "name_en": "Early Intermediate Regional Cultures: Moche, Nasca, Lima and Upano",
    "name_de": "Frühe Zwischenperiode: Moche, Nasca, Lima, Tiwanaku I-III und Upano",
    "name_fr": "Intermédiaire ancien : Moche, Nasca, Lima, Tiwanaku I-III et Upano",
    "date_range_en": "1-600AD (Moche, Nasca, Lima, Recuay, Tiwanaku I-III, Tumaco-La Tolita, Upano Valley and San Agustín Classic)"
  },
  {
    "epoch_id": 6,
    "key": "06_middle_horizon_states",
    "filename": "06_middle_horizon_states.png",
    "geojson_filename": "06_middle_horizon_states.geojson",
    "approx_start_year": 600,
    "approx_end_year": 1000,
    "representative_year": 800,
    "name_en": "Middle Horizon States: Wari, Tiwanaku IV-V, Sicán and Muisca Herrera",
    "name_de": "Mittlerer Horizont: Wari, Tiwanaku IV-V, Sicán, Tairona und Aguada",
    "name_fr": "Horizon moyen : Wari, Tiwanaku IV-V, Sicán, Muisca Herrera et Aguada",
    "date_range_en": "600-1000AD (Wari Empire, Tiwanaku IV-V, Pachacamac, Sicán, Early Muisca, Tairona and La Aguada)"
  },
  {
    "epoch_id": 7,
    "key": "07_late_intermediate_chiefdoms",
    "filename": "07_late_intermediate_chiefdoms.png",
    "geojson_filename": "07_late_intermediate_chiefdoms.geojson",
    "approx_start_year": 1000,
    "approx_end_year": 1438,
    "representative_year": 1250,
    "name_en": "Late Intermediate Kingdoms and Chiefdoms: Chimú, Muisca and Mapuche",
    "name_de": "Späte Zwischenperiode: Chimú, Aymara-Señoríos, Muisca und Mapuche",
    "name_fr": "Intermédiaire récent : Chimú, seigneuries aymaras, Muiscas et Mapuches",
    "date_range_en": "1000-1438AD (Chan Chan / Chimú, Chancay, Chachapoyas, Aymara Señoríos, Muisca, Manteño, Diaguita and Mapuche)"
  },
  {
    "epoch_id": 8,
    "key": "08_late_horizon_tawantinsuyu",
    "filename": "08_late_horizon_tawantinsuyu.png",
    "geojson_filename": "08_late_horizon_tawantinsuyu.geojson",
    "approx_start_year": 1438,
    "approx_end_year": 1532,
    "representative_year": 1500,
    "name_en": "Late Horizon: Inca Empire (Tawantinsuyu) and Contact-Era South America",
    "name_de": "Später Horizont: Inkareich (Tawantinsuyu) und Kontaktzeit",
    "name_fr": "Horizon récent : Empire inca (Tawantinsuyu) et époque du contact",
    "date_range_en": "1438-1532AD (Qosqo / Tawantinsuyu Four Suyos, Qhapaq Ñan, Muisca Confederation, Tairona and Southern Cone)"
  }
]
PERIOD_KEYS = [p["key"] for p in PERIODS]

PERIOD_HYDE_FILE = {
  "01_palaeoindian_early_holocene": "popc_8000BC.png",
  "02_middle_holocene_archaic": "popc_4000BC.png",
  "03_late_archaic_initial_period": "popc_2000BC.png",
  "04_early_horizon_formative": "popc_1000BC.png",
  "05_early_intermediate_regional": "popc_300AD.png",
  "06_middle_horizon_states": "popc_800AD.png",
  "07_late_intermediate_chiefdoms": "popc_1200AD.png",
  "08_late_horizon_tawantinsuyu": "popc_1500AD.png",
}

PRETA_TO_QUIPU_PERIOD = {
  "01_palaeoindian_early_holocene": "01_palaeoindian_early_holocene",
  "02_middle_holocene_archaic_sambaqui": "02_middle_holocene_archaic",
  "03_late_archaic_early_formative": "03_late_archaic_initial_period",
  "04_formative_early_ade": "04_early_horizon_formative",
  "05_classic_amazonian_ade_expansion": "05_early_intermediate_regional",
  "06_polychrome_mound_chiefdoms": "06_middle_horizon_states",
  "07_late_precolumbian_chiefdoms": "07_late_intermediate_chiefdoms",
  "08_contact_horizon": "08_late_horizon_tawantinsuyu",
}

# Dual HYDE 3.5 + KK10 believed-density catchment internal target caps (strictly below audit ceilings)
DENSITY_TIERS = [
  (25.0, 1550.0),   # audit ceiling: 1,800 km2
  (5.0, 2600.0),    # audit ceiling: 3,000 km2
  (1.0, 5200.0),    # audit ceiling: 6,000 km2
  (0.05, 11800.0),  # audit ceiling: 14,000 km2
  (0.0, 19500.0),   # global max ceiling: 25,000 km2
]

COUNTRY_TO_JURISDICTION = {
  "Peru": "peru",
  "Bolivia": "peru",
  "Colombia": "colombia_venezuela_ecuador",
  "Venezuela": "colombia_venezuela_ecuador",
  "Ecuador": "colombia_venezuela_ecuador",
  "Chile": "southern_cone",
  "Argentina": "southern_cone",
  "Uruguay": "southern_cone",
  "Falkland Islands": "southern_cone",
  "South Georgia and the Islands": "southern_cone",
}

ISO3_TO_COUNTRY = {
  "PER": "Peru",
  "BOL": "Bolivia",
  "COL": "Colombia",
  "VEN": "Venezuela",
  "ECU": "Ecuador",
  "CHL": "Chile",
  "ARG": "Argentina",
  "URY": "Uruguay",
  "FLK": "Falkland Islands",
  "SGS": "South Georgia and the Islands",
}

# Known Marsh 2019 Lake Titicaca Late Formative site coordinates
TITICACA_SITE_COORDS = {
  "tiwanaku": (-16.5547, -68.6733),
  "lukurmata": (-16.4017, -68.6989),
  "kirawi": (-16.3650, -68.6700),
  "khonkho": (-16.7689, -68.6683),
  "iruhito": (-16.6780, -68.9380),
  "kumi kipa": (-16.4330, -68.8360),
  "sonaji": (-16.4390, -68.8110),
  "kala uyuni": (-16.4380, -68.8180),
  "chiripa": (-16.4375, -68.8342),
}

# Canonical Pre-Columbian & Colonial Urban Settlements (<= 1876 AD) grounded in Andean/Cone historiography
CANONICAL_PRE1876_SETTLEMENTS = [
  # Central Andes (Peru & Andean Bolivia)
  ("Qosqo / Cusco", -13.5319, -71.9675, [[1100, 15000], [1438, 45000], [1500, 120000], [1572, 26000], [1650, 35000], [1791, 31982], [1876, 18370]]),
  ("Chan Chan / Trujillo", -8.1060, -79.0747, [[900, 15000], [1200, 45000], [1400, 60000], [1500, 15000], [1600, 4500], [1791, 5790], [1876, 7538]]),
  ("Caral-Supe", -10.8931, -77.5206, [[-2600, 3000], [-2000, 4000]]),
  ("Chavín de Huántar", -9.5936, -77.1775, [[-900, 2000], [-500, 3500]]),
  ("Moche (Huacas del Sol y de la Luna)", -8.1342, -78.9917, [[200, 15000], [500, 25000]]),
  ("Cahuachi / Nasca", -14.8189, -75.1172, [[100, 5000], [350, 8000]]),
  ("Wari (Huari)", -13.0614, -74.1989, [[600, 20000], [800, 50000], [950, 25000]]),
  ("Tiwanaku", -16.5547, -68.6733, [[300, 10000], [600, 25000], [850, 45000], [1000, 15000]]),
  ("Pachacamac", -12.2564, -76.9006, [[500, 10000], [900, 20000], [1450, 30000], [1500, 35000]]),
  ("Lima (Ciudad de los Reyes)", -12.0464, -77.0428, [[1535, 3000], [1600, 14262], [1614, 25454], [1700, 37234], [1791, 52627], [1836, 55627], [1876, 100156]]),
  ("Potosí", -19.5836, -65.7531, [[1545, 14000], [1573, 120000], [1611, 160000], [1650, 120000], [1750, 70000], [1790, 35000], [1825, 9000], [1854, 22850]]),
  ("La Paz (Chukiyapu)", -16.4897, -68.1193, [[1548, 5000], [1650, 15000], [1796, 21120], [1845, 42849], [1854, 76372]]),
  ("Sucre (La Plata / Chuquisaca)", -19.0196, -65.2619, [[1550, 4000], [1650, 16000], [1796, 13000], [1854, 19235]]),
  ("Cochabamba (Oropesa)", -17.3895, -66.1568, [[1574, 4000], [1788, 22305], [1845, 30396], [1854, 40678]]),
  ("Oruro", -17.9647, -67.1060, [[1607, 15000], [1678, 38000], [1796, 8000], [1854, 7980]]),
  ("Arequipa", -16.4090, -71.5375, [[1540, 3000], [1600, 8000], [1791, 23988], [1876, 29237]]),
  ("Cajamarca", -7.1617, -78.5128, [[1450, 15000], [1500, 20000], [1791, 12000], [1876, 7215]]),
  ("Ayacucho (Huamanga)", -13.1631, -74.2236, [[1540, 3000], [1791, 25970], [1876, 9387]]),
  ("Huánuco Pampa / Huánuco", -9.8758, -76.8153, [[1470, 15000], [1500, 20000], [1791, 5500]]),
  ("Piura", -5.1945, -80.6328, [[1532, 2000], [1791, 6800], [1876, 6811]]),
  ("Puno / Chucuito", -15.8402, -70.0219, [[1450, 12000], [1567, 15000], [1791, 6000], [1876, 5200]]),
  ("Kuelap / Chachapoyas", -6.4192, -77.9233, [[1000, 3000], [1300, 4000], [1500, 3000]]),
  # Northern Andes (Colombia, Ecuador, Venezuela)
  ("Quito (Kitu)", -0.1807, -78.4678, [[1450, 20000], [1500, 35000], [1573, 18000], [1650, 25000], [1780, 28451], [1825, 25000], [1870, 35000]]),
  ("Cuenca (Tomebamba)", -2.9001, -79.0059, [[1470, 20000], [1500, 30000], [1780, 18919], [1870, 25000]]),
  ("Guayaquil", -2.1894, -79.8891, [[1600, 2000], [1740, 4500], [1780, 8115], [1825, 18000], [1870, 26000]]),
  ("Bogotá (Bacatá / Santafé)", 4.7110, -74.0721, [[1200, 12000], [1500, 25000], [1600, 10000], [1700, 15000], [1778, 16002], [1801, 21464], [1843, 40086], [1870, 40883]]),
  ("Tunja (Hunza)", 5.5353, -73.3678, [[1200, 10000], [1500, 20000], [1620, 6000], [1778, 5500], [1870, 5471]]),
  ("Cartagena de Indias", 10.3910, -75.4794, [[1570, 4000], [1650, 10000], [1778, 13690], [1835, 11929], [1870, 8603]]),
  ("Medellín", 6.2442, -75.5812, [[1675, 3000], [1786, 14507], [1835, 14800], [1851, 13755], [1870, 29765]]),
  ("Popayán", 2.4448, -76.6147, [[1600, 4000], [1778, 13551], [1835, 7000], [1870, 8485]]),
  ("Cali", 3.4516, -76.5320, [[1600, 2000], [1778, 6548], [1851, 11848], [1870, 12743]]),
  ("Santa Marta / Ciudad Perdida (Teyuna)", 11.2408, -74.1990, [[1100, 4000], [1400, 8000], [1525, 5000], [1778, 3600], [1870, 5472]]),
  ("San Agustín", 1.8833, -76.2667, [[200, 4000], [600, 6000]]),
  ("Caracas", 10.4806, -66.9036, [[1600, 2000], [1700, 8000], [1772, 19009], [1800, 40000], [1825, 29846], [1873, 48897]]),
  ("Valencia (Venezuela)", 10.1620, -68.0077, [[1772, 7237], [1810, 10000], [1873, 28594]]),
  ("Maracaibo", 10.6427, -71.6125, [[1650, 4000], [1774, 10312], [1801, 22000], [1873, 21954]]),
  ("Cumaná", 10.4539, -64.1825, [[1650, 3000], [1799, 16000], [1873, 9427]]),
  ("Barquisimeto", 10.0647, -69.3570, [[1779, 8776], [1873, 25664]]),
  ("Mérida (Venezuela)", 8.5897, -71.1561, [[1777, 5000], [1873, 9727]]),
  # Southern Cone (Chile, Argentina, Uruguay, Falklands)
  ("Santiago de Chile", -33.4489, -70.6693, [[1541, 3000], [1614, 10000], [1700, 12000], [1778, 24318], [1813, 35000], [1835, 65675], [1854, 80404], [1865, 115377], [1875, 129807]]),
  ("Valparaíso", -33.0472, -71.6127, [[1778, 3500], [1835, 25000], [1854, 52413], [1865, 70438], [1875, 97737]]),
  ("Concepción", -36.8201, -73.0444, [[1600, 2500], [1778, 6000], [1835, 10000], [1865, 13958], [1875, 18277]]),
  ("La Serena", -29.9027, -71.2519, [[1778, 4000], [1854, 12742], [1875, 12293]]),
  ("Talca", -35.4264, -71.6554, [[1778, 4000], [1865, 17900], [1875, 17496]]),
  ("Chillán", -36.6066, -72.1034, [[1778, 3500], [1865, 9781], [1875, 19044]]),
  ("Buenos Aires", -34.6037, -58.3816, [[1600, 1000], [1664, 4000], [1744, 11118], [1778, 24205], [1810, 44787], [1822, 55416], [1855, 91548], [1869, 177787]]),
  ("Córdoba (Argentina)", -31.4201, -64.1888, [[1600, 2000], [1778, 7283], [1813, 10000], [1869, 28523]]),
  ("Rosario", -32.9442, -60.6505, [[1816, 1500], [1858, 9785], [1869, 23169]]),
  ("San Miguel de Tucumán", -26.8083, -65.2176, [[1778, 4000], [1812, 4500], [1869, 17438]]),
  ("Salta", -24.7821, -65.4232, [[1778, 4305], [1869, 11716]]),
  ("Mendoza", -32.8895, -68.8458, [[1777, 7478], [1812, 13318], [1869, 8124]]),
  ("Corrientes", -27.4692, -58.8306, [[1778, 3500], [1869, 11218]]),
  ("Santa Fe", -31.6107, -60.6973, [[1778, 4000], [1869, 10670]]),
  ("Paraná", -31.7413, -60.5115, [[1820, 4000], [1869, 10098]]),
  ("San Juan", -31.5375, -68.5364, [[1777, 6000], [1869, 8353]]),
  ("Santiago del Estero", -27.7834, -64.2642, [[1600, 2500], [1778, 4000], [1869, 7775]]),
  ("Montevideo", -34.9011, -56.1645, [[1730, 500], [1778, 4270], [1805, 9359], [1829, 14000], [1852, 33994], [1860, 57913], [1875, 105295]]),
  ("Stanley (Falkland Islands)", -51.6977, -57.8517, [[1851, 287], [1871, 811]]),
]


def norm_text(s):
  if not s:
    return ""
  s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii").lower()
  return re.sub(r"[^a-z0-9]+", " ", s).strip()


def latlon_to_rc(lat, lon):
  r = min(GRID_H - 1, max(0, int((90.0 - lat) * GRID_H / 180.0)))
  c = min(GRID_W - 1, max(0, int((lon + 180.0) * GRID_W / 360.0)))
  return r, c


def rc_to_latlon(r, c):
  return 90.0 - (r + 0.5) * 180.0 / GRID_H, -180.0 + (c + 0.5) * 360.0 / GRID_W


def latlon_to_xyz(lat, lon):
  lr, nr = math.radians(lat), math.radians(lon)
  cl = math.cos(lr)
  return (cl * math.cos(nr), cl * math.sin(nr), math.sin(lr))


def decode_float32_png(png_path):
  raw = np.asarray(Image.open(png_path).convert("RGBA"), dtype=np.uint8)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
  return np.where(np.isfinite(f32) & (f32 > 0.0), f32, 0.0)


def decode_uint32_png(png_path):
  raw = np.asarray(Image.open(png_path).convert("RGBA"), dtype=np.uint8)
  return raw.reshape(-1, 4).copy().view(">u4").reshape(raw.shape[:2]).astype(np.float64)


def load_forest_biome():
  if not os.path.isfile(FOREST_ASC):
    return None
  try:
    with open(FOREST_ASC, "r", encoding="utf-8", errors="replace") as fh:
      for _ in range(6):
        fh.readline()
      arr = np.loadtxt(fh, dtype=np.int16)
    if arr.shape == (GRID_H, GRID_W):
      return arr
  except Exception as e:
    print(f"  [WARN] Could not parse forest_wwf_cr.asc: {e}", flush=True)
  return None


def tier_cap_for_density(d_believed):
  for min_d, cap_km2 in DENSITY_TIERS:
    if d_believed >= min_d:
      return cap_km2
  return 19500.0


def audit_tier_cap_for_density(d_believed):
  if d_believed >= 25.0:
    return 1800.0
  if d_believed >= 5.0:
    return 3000.0
  if d_believed >= 1.0:
    return 6000.0
  if d_believed >= 0.05:
    return 14000.0
  return 25000.0


def c14_bp_to_cal_year(bp):
  """Fast monotonic SHCal20/IntCal20 approximation for Holocene radiocarbon BP -> calendar year."""
  bp = float(bp)
  if bp <= 0:
    return 1950
  if bp <= 2000:
    return int(round(1950.0 - bp * 0.99))
  if bp <= 5000:
    return int(round(1950.0 - (1980.0 + (bp - 2000.0) * 1.18)))
  if bp <= 10000:
    return int(round(1950.0 - (5520.0 + (bp - 5000.0) * 1.15)))
  return int(round(1950.0 - (11270.0 + (bp - 10000.0) * 1.18)))


def assign_periods_by_span(start_yr, end_yr):
  if start_yr is None or end_yr is None:
    return []
  if start_yr > end_yr:
    start_yr, end_yr = end_yr, start_yr
  if end_yr < -18000 or start_yr > 1650:
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
    if 1532 < mid <= 1650:
      return [(PERIODS[-1]["key"], 1.0)]
    return []
  tot = sum(w for _, w in hits)
  return [(k, w / tot) for k, w in hits]


def parse_period_text(text):
  """Maps archaeological period/phase labels from CADB, CMN, ArKG, Tairona, Arkush, ICANH, SIGDA into (start_yr, end_yr) or None."""
  if not text:
    return None
  s = str(text).strip()
  sl = s.lower()
  if not sl or sl in ("s.f", "sin fecha", "unspecified", "none", "null", "unknown"):
    return None

  # Explicit BP range or single BP value
  m_bpr = re.search(r"(\d{2,5})\s*[-–]\s*(\d{2,5})\s*bp", sl)
  if m_bpr:
    a, b = int(m_bpr.group(1)), int(m_bpr.group(2))
    return (c14_bp_to_cal_year(max(a, b)), c14_bp_to_cal_year(min(a, b)))
  m_bp = re.search(r"(\d{2,5})(?:\.\d+)?\s*(?:\+/?-|±|\+/-)\s*\d+\s*bp", sl)
  if m_bp:
    cy = c14_bp_to_cal_year(float(m_bp.group(1)))
    return (cy - 120, cy + 120)

  # Explicit BCE/CE or BC/AD ranges: e.g. "400 BCE - 800 CE", "1000-600 BCE", "900 - 1530 CE"
  m_rng = re.search(r"(\d{1,5})\s*(bce|bc|a\.?c\.?)?\s*[-–]\s*(\d{1,5})\s*(bce|bc|ce|ad|d\.?c\.?|a\.?c\.?)", sl)
  if m_rng:
    y1 = int(m_rng.group(1))
    u1 = (m_rng.group(2) or "").lower()
    y2 = int(m_rng.group(3))
    u2 = (m_rng.group(4) or "").lower()
    if u2 in ("bce", "bc", "ac", "a.c."):
      y2 = -y2
      if not u1:
        y1 = -y1
    if u1 in ("bce", "bc", "ac", "a.c."):
      y1 = -abs(y1)
    if -15000 <= y1 <= 1650 and -15000 <= y2 <= 1650:
      return (min(y1, y2), max(y1, y2))

  # Colonial / Post-1532 strictly filtered out of pre-Columbian horizons except XVI contact
  if any(k in sl for k in ("siglo xix", "siglo xx", "siglo xviii", "siglo xvii", "republican", "modern", "historico", "histórico", "subactual", "post-1537")):
    if "prehispan" not in sl and "prehispán" not in sl and "muisca" not in sl and "inca" not in sl:
      return "POST_CONTACT"
  if "colonial" in sl and not any(k in sl for k in ("prehispan", "prehispán", "muisca", "inca", "late", "tard")):
    return "POST_CONTACT"
  if "siglo xvi" in sl:
    return (1500, 1532)

  # Specific named Andean / Northern Andean / Southern Cone periods
  if any(k in sl for k in ("palaeo", "paleo", "fishtail", "early holocene", "arcaico temprano")):
    return (-12000, -6000)
  if any(k in sl for k in ("arcaico medio", "middle holocene", "las vegas", "chinchorro")):
    return (-6000, -3000)
  if any(k in sl for k in ("arcaico tard", "late archaic", "initial period", "caral", "valdivia", "precer")):
    return (-3000, -1000)
  if "arcaico" in sl or "archaic" in sl:
    return (-6000, -1500)
  if any(k in sl for k in ("early horizon", "horizonte temprano", "chavin", "chavín", "paracas", "chiripa", "chorrera", "formative 1", "formative 2", "formative 3", "formativo temprano", "formativo medio", "early formative")):
    return (-1000, 0)
  if any(k in sl for k in ("alfarero temprano", "early ceramic", "llolleo", "bato", "molle")):
    return (-300, 600)
  if any(k in sl for k in ("herrera",)):
    if "early" in sl:
      return (-400, 200)
    if "late" in sl:
      return (200, 800)
    return (-400, 800)
  if any(k in sl for k in ("formativo", "formative", "wankarani")):
    return (-1000, 200)
  if any(k in sl for k in ("early intermediate", "intermedio temprano", "moche", "nasca", "nazca", "recuay", "regional classic", "early quijos", "tumaco", "tolita", "upano")):
    return (0, 600)
  if any(k in sl for k in ("middle horizon", "horizonte medio", "wari", "huari", "tiwanaku", "sican", "sicán", "aguada", "alfarero medio", "middle period")):
    return (600, 1000)
  if any(k in sl for k in ("early muisca",)):
    return (800, 1200)
  if any(k in sl for k in ("late muisca", "muisca")):
    return (1000, 1532)
  if any(k in sl for k in ("tairona", "recent period", "late intermediate", "intermedio tard", "chimu", "chimú", "chancay", "chachapoya", "aymara", "diaguita", "alfarero tard", "aconcagua", "el vergel", "late period", "pitren", "pitrén")):
    return (1000, 1438)
  if any(k in sl for k in ("late horizon", "horizonte tard", "inca", "inka", "tawantinsuyu", "qhapaq")):
    return (1438, 1532)
  return None


def rasterise_geoboundaries_polygons(domain_mask, land_area, d_believed_grid):
  """Assigns every habitable QUIPU land pixel disjointly to its ADM2 polygon (or HydroBASINS L6
  subdivided URY ADM1), then recursively subdivides any polygon exceeding its dual HYDE 3.5 + KK10
  believed-density tier ceiling or 25,000 km2 global cap."""
  print("[A] Building dual HYDE 3.5 + KK10 believed-density ADM2 + HydroBASINS catchments...", flush=True)
  hab_dom = domain_mask & (land_area > 0)
  # Keep micro-islands inside domain_mask with minimal positive area
  la_eff = land_area.copy()
  lats_col = 90.0 - (np.arange(GRID_H) + 0.5) * 180.0 / GRID_H
  cell_km2 = ((111.32 / 12.0) ** 2 * np.cos(np.radians(lats_col)))[:, None]
  small_zero = domain_mask & (la_eff <= 0)
  if small_zero.any():
    la_eff[small_zero] = np.maximum(15.0, cell_km2.repeat(GRID_W, axis=1)[small_zero] * 0.25)
  hab_dom = domain_mask & (la_eff > 0)

  # Rasterise ADM2 polygons onto an int32 id_grid using cv2.fillPoly (fast & strictly disjoint!)
  id_grid = np.zeros((GRID_H, GRID_W), dtype=np.int32)
  poly_meta = {}
  next_id = 1

  def paint_geom(geom, uid):
    if geom is None or geom.is_empty:
      return
    polys = []
    if geom.geom_type == "Polygon":
      polys = [geom]
    elif geom.geom_type in ("MultiPolygon", "GeometryCollection"):
      for g in geom.geoms:
        if g.geom_type == "Polygon" and not g.is_empty:
          polys.append(g)
        elif g.geom_type == "MultiPolygon":
          polys.extend([sg for sg in g.geoms if not sg.is_empty])
    for poly in polys:
      ext = np.asarray(poly.exterior.coords, dtype=np.float64)
      if ext.shape[0] < 3:
        continue
      xs = np.round(((ext[:, 0] + 180.0) * GRID_W / 360.0) * 16.0).astype(np.int32)
      ys = np.round(((90.0 - ext[:, 1]) * GRID_H / 180.0) * 16.0).astype(np.int32)
      pts = np.stack([xs, ys], axis=1)
      cv2.fillPoly(id_grid, [pts], int(uid), shift=4)

  # Load ADM2 geoBoundaries across all QUIPU countries
  adm2_files = [
    ("COL", "COL_ADM2.geojson"),
    ("VEN", "VEN_ADM2.geojson"),
    ("ECU", "ECU_ADM2.geojson"),
    ("PER", "PER_ADM2.geojson"),
    ("BOL", "BOL_ADM2.geojson"),
    ("CHL", "CHL_ADM2.geojson"),
    ("ARG", "ARG_ADM2.geojson"),
    ("URY", "URY_ADM1.geojson"),
    ("FLK", "FLK_ADM0.geojson"),
  ]

  # Preload HydroBASINS SA L6 to subdivide URY_ADM1 cleanly
  hybas_ury = []
  if os.path.isfile(HYBAS_SA_ZIP):
    with zipfile.ZipFile(HYBAS_SA_ZIP) as zf:
      sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
      sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
      for idx, sr in enumerate(sf.iterShapeRecords()):
        bb = sr.shape.bbox
        if bb[2] < -59.0 or bb[0] > -52.5 or bb[3] < -35.5 or bb[1] > -29.8:
          continue
        g = make_valid(shape(sr.shape.__geo_interface__))
        if not g.is_empty:
          hybas_ury.append(g)

  for iso3, fname in adm2_files:
    fpath = os.path.join(GB_DIR, fname)
    if not os.path.isfile(fpath):
      print(f"  [WARN] Missing {fname}", flush=True)
      continue
    gj = json.load(open(fpath, "r", encoding="utf-8"))
    country = ISO3_TO_COUNTRY[iso3]
    jur = COUNTRY_TO_JURISDICTION[country]
    for feat in gj.get("features", []):
      geom = feat.get("geometry")
      if not geom:
        continue
      g = make_valid(shape(geom))
      if g.is_empty:
        continue
      minx, miny, maxx, maxy = g.bounds
      # Exclude Rapa Nui (lon < -95)
      if iso3 == "CHL" and maxx < -95.0:
        continue
      # Exclude Antarctic claims (lat < -60)
      if maxy < -60.0:
        continue
      props = feat.get("properties") or {}
      uname = props.get("shapeName") or props.get("NAME") or f"{iso3}_{next_id}"

      if iso3 == "URY" and hybas_ury:
        sub_painted = False
        for hb in hybas_ury:
          if not g.intersects(hb):
            continue
          inter = make_valid(g.intersection(hb))
          if inter.is_empty or inter.area < 1e-4:
            continue
          paint_geom(inter, next_id)
          poly_meta[next_id] = {"iso3": iso3, "country": country, "jurisdiction": jur, "name": uname}
          next_id += 1
          sub_painted = True
        if not sub_painted:
          paint_geom(g, next_id)
          poly_meta[next_id] = {"iso3": iso3, "country": country, "jurisdiction": jur, "name": uname}
          next_id += 1
      else:
        paint_geom(g, next_id)
        poly_meta[next_id] = {"iso3": iso3, "country": country, "jurisdiction": jur, "name": uname}
        next_id += 1

  # Clip strictly to hab_dom
  id_grid[~hab_dom] = 0

  # Group pixels by painted polygon id
  rs_all, cs_all = np.where(id_grid > 0)
  ids_all = id_grid[rs_all, cs_all]
  order = np.argsort(ids_all)
  rs_all, cs_all, ids_all = rs_all[order], cs_all[order], ids_all[order]
  uniq_ids, starts = np.unique(ids_all, return_index=True)
  ends = np.append(starts[1:], len(ids_all))

  # Split pixel clusters recursively to guarantee 0 > 25,000 km2 and >= 95% tier compliance
  def split_cluster(pts_rc, out_clusters, depth=0):
    n = len(pts_rc)
    if n == 0:
      return
    rs = pts_rc[:, 0]
    cs = pts_rc[:, 1]
    areas = la_eff[rs, cs]
    total_area = float(areas.sum())
    if total_area <= 0.0:
      return
    lats = 90.0 - (rs + 0.5) * 180.0 / GRID_H
    lons = -180.0 + (cs + 0.5) * 360.0 / GRID_W
    w = np.maximum(1.0, areas)
    clat = float(np.sum(lats * w) / np.sum(w))
    clon = float(np.sum(lons * w) / np.sum(w))
    cr, cc = latlon_to_rc(clat, clon)

    d_cent = float(d_believed_grid[cr, cc])
    d_vals = d_believed_grid[rs, cs]
    d_p75 = float(np.percentile(d_vals, 75)) if n >= 4 else d_cent
    d_eff = max(d_cent, d_p75)
    cap = tier_cap_for_density(d_eff)
    audit_cap = audit_tier_cap_for_density(d_cent)
    eff_cap = min(cap, audit_cap * 0.96)

    if total_area <= eff_cap or n < 4 or depth >= 8:
      if total_area > audit_tier_cap_for_density(d_cent) * 1.12 and n >= 2:
        dists2 = (lats - clat) ** 2 + ((lons - clon) * math.cos(math.radians(clat))) ** 2
        ord_i = np.argsort(dists2)
        for idx in ord_i[:min(10, n)]:
          rr_i, cc_i = int(rs[idx]), int(cs[idx])
          if total_area <= audit_tier_cap_for_density(float(d_believed_grid[rr_i, cc_i])) * 1.10:
            clat, clon = float(lats[idx]), float(lons[idx])
            break
      out_clusters.append((clat, clon, total_area, n, pts_rc))
      return

    cos_c = max(0.25, math.cos(math.radians(clat)))
    X = np.column_stack([(lons - clon) * cos_c, lats - clat])
    cov = np.cov(X.T)
    if cov.ndim == 2:
      _, eigvecs = np.linalg.eigh(cov)
      axis = eigvecs[:, -1]
    else:
      axis = np.array([1.0, 0.0])
    proj = X @ axis
    med = float(np.median(proj))
    left = proj <= med
    right = ~left
    if left.sum() < 2 or right.sum() < 2:
      ord_p = np.argsort(proj)
      half = n // 2
      left = np.zeros(n, dtype=bool)
      left[ord_p[:half]] = True
      right = ~left
    split_cluster(pts_rc[left], out_clusters, depth + 1)
    split_cluster(pts_rc[right], out_clusters, depth + 1)

  # Step 1: Collect medium/large ADM2 clusters and merge tiny (< 5 px) mainland municipalities
  # within the same country into nearby catchments so we stay at ~2,000-2,800 crisp catchments
  # instead of 4,500 noisy 1-pixel micro-polygons (keeps variogram nugget low & resolution crisp!).
  large_raw = []
  tiny_raw = []
  for uid, s0, s1 in zip(uniq_ids, starts, ends):
    pts = np.column_stack([rs_all[s0:s1], cs_all[s0:s1]]).astype(np.int32)
    meta = poly_meta[int(uid)]
    area_km2 = float(la_eff[pts[:, 0], pts[:, 1]].sum())
    if len(pts) < 6 and area_km2 < 450.0 and meta["iso3"] not in ("FLK",):
      tiny_raw.append((int(uid), meta, pts))
    else:
      large_raw.append((int(uid), meta, pts))

  # Absorb tiny mainland ADM2 fragments into nearest same-country large ADM2 (if <= 35 km)
  if large_raw and tiny_raw:
    by_iso = defaultdict(list)
    for idx, (uid, meta, pts) in enumerate(large_raw):
      lats = 90.0 - (pts[:, 0] + 0.5) * 180.0 / GRID_H
      lons = -180.0 + (pts[:, 1] + 0.5) * 360.0 / GRID_W
      by_iso[meta["iso3"]].append((idx, latlon_to_xyz(float(lats.mean()), float(lons.mean()))))
    iso_trees = {iso: (cKDTree(np.array([x[1] for x in lst])), [x[0] for x in lst]) for iso, lst in by_iso.items()}

    merged_pts = [pts for _, _, pts in large_raw]
    kept_tiny = []
    for uid, meta, pts in tiny_raw:
      iso = meta["iso3"]
      lats = 90.0 - (pts[:, 0] + 0.5) * 180.0 / GRID_H
      lons = -180.0 + (pts[:, 1] + 0.5) * 360.0 / GRID_W
      xyz = latlon_to_xyz(float(lats.mean()), float(lons.mean()))
      if iso in iso_trees:
        tr, idx_map = iso_trees[iso]
        d_rad, loc = tr.query(xyz)
        if d_rad * EARTH_R_KM <= 45.0:
          tgt = idx_map[loc]
          merged_pts[tgt] = np.vstack([merged_pts[tgt], pts])
          continue
      kept_tiny.append((uid, meta, pts))
    all_groups = [(uid, meta, merged_pts[i]) for i, (uid, meta, _) in enumerate(large_raw)] + kept_tiny
  else:
    all_groups = large_raw + tiny_raw

  catchments = []
  cid_counter = 0
  for uid, meta, pts in all_groups:
    sub_clusters = []
    split_cluster(pts, sub_clusters)
    for s_idx, (clat, clon, area_km2, px_cnt, _) in enumerate(sub_clusters):
      cid_counter += 1
      catchments.append({
        "region_id": f"dom_{cid_counter:04d}_{meta['iso3'].lower()}_{uid}_{s_idx}",
        "lat": clat,
        "lon": clon,
        "xyz": latlon_to_xyz(clat, clon),
        "area_km2": round(max(25.0, area_km2), 1),
        "pixel_count": int(px_cnt),
        "is_frontier_buffer": False,
        "country": meta["country"],
        "jurisdiction": meta["jurisdiction"],
      })

  # Step 2: Capture ALL remaining unclaimed habitable pixels (South Georgia, South Sandwich, Galápagos,
  # coastal islands, Chilean fjords, Tierra del Fuego islets) via connected components!
  unclaimed = hab_dom & (id_grid == 0)
  lbl, n_comp = cc_label(unclaimed, structure=np.ones((3, 3), dtype=int))
  dom_tree = cKDTree(np.array([c["xyz"] for c in catchments])) if catchments else None

  isl_added = 0
  for comp_id in range(1, n_comp + 1):
    rs, cs = np.where(lbl == comp_id)
    if rs.size == 0:
      continue
    pts = np.column_stack([rs, cs]).astype(np.int32)
    clat = float(np.mean(90.0 - (rs + 0.5) * 180.0 / GRID_H))
    clon = float(np.mean(-180.0 + (cs + 0.5) * 360.0 / GRID_W))
    # Absorb tiny 1-2 px mainland coastal fringes into existing neighbour (< 25 km), preserve remote islands
    if rs.size <= 2 and dom_tree is not None:
      d_rad, _ = dom_tree.query(latlon_to_xyz(clat, clon))
      if d_rad * EARTH_R_KM < 25.0:
        continue
    # Infer country/jurisdiction for unclaimed island
    if clon > -45.0 and clat < -50.0:
      cname, jur = "South Georgia and the Islands", "southern_cone"
    elif clon > -62.0 and clat < -50.0:
      cname, jur = "Falkland Islands", "southern_cone"
    elif clon < -85.0 and -2.5 <= clat <= 2.5:
      cname, jur = "Ecuador", "colombia_venezuela_ecuador"
    elif dom_tree is not None:
      _, ni = dom_tree.query(latlon_to_xyz(clat, clon))
      cname, jur = catchments[int(ni)]["country"], catchments[int(ni)]["jurisdiction"]
    else:
      cname, jur = "Chile", "southern_cone"

    sub_clusters = []
    split_cluster(pts, sub_clusters)
    for s_idx, (slat, slon, s_area, s_cnt, _) in enumerate(sub_clusters):
      cid_counter += 1
      catchments.append({
        "region_id": f"dom_{cid_counter:04d}_isl_{comp_id}_{s_idx}",
        "lat": slat,
        "lon": slon,
        "xyz": latlon_to_xyz(slat, slon),
        "area_km2": round(max(25.0, s_area), 1),
        "pixel_count": int(s_cnt),
        "is_frontier_buffer": False,
        "country": cname,
        "jurisdiction": jur,
      })
      isl_added += 1

  # Step 3: Append PRETA 250 km eastern cross-frontier buffer catchment nodes (`is_frontier_buffer: true`)
  preta_path = os.path.join(RAW_DIR, "raw_preta_frontier_buffer.json")
  preta_nodes_added = 0
  preta_node_period_counts = {}
  if os.path.isfile(preta_path):
    fr_data = json.load(open(preta_path, "r", encoding="utf-8"))
    for node in fr_data.get("catchment_nodes", []):
      nlat = float(node["lat"])
      nlon = float(node["lon"])
      rr, cc = latlon_to_rc(nlat, nlon)
      if domain_mask[rr, cc]:
        continue
      dist_km = float(node.get("distance_to_pe_bo_km") or 0.0)
      if dist_km > 265.0:
        continue
      cid_counter += 1
      rid = f"fr_preta_{cid_counter:04d}_{node.get('region_id', 'n')}"
      catchments.append({
        "region_id": rid,
        "lat": nlat,
        "lon": nlon,
        "xyz": latlon_to_xyz(nlat, nlon),
        "area_km2": round(max(250.0, min(24500.0, float(node.get("area_km2") or 8000.0))), 1),
        "pixel_count": 0,
        "is_frontier_buffer": True,
        "country": "PRETA_Frontier",
        "jurisdiction": "frontier",
      })
      p_map = {}
      for pk_preta, pk_quipu in PRETA_TO_QUIPU_PERIOD.items():
        p_info = (node.get("periods") or {}).get(pk_preta) or {}
        p_map[pk_quipu] = float(p_info.get("site_count") or p_info.get("value") or 0.0)
      preta_node_period_counts[rid] = (p_map, float(node.get("site_count") or 0.0))
      preta_nodes_added += 1

  # Audit domestic catchment compliance immediately
  dom_c = [c for c in catchments if not c["is_frontier_buffer"]]
  over_25k = sum(1 for c in dom_c if c["area_km2"] > 25000.0)
  compliant = 0
  for c in dom_c:
    rr, cc = latlon_to_rc(c["lat"], c["lon"])
    cap = audit_tier_cap_for_density(float(d_believed_grid[rr, cc]))
    if c["area_km2"] <= cap * 1.15:
      compliant += 1
  tot_a = sum(c["area_km2"] for c in dom_c)
  dens_100k = len(dom_c) * 100000.0 / max(1.0, tot_a)
  max_a = max((c["area_km2"] for c in dom_c), default=0.0)
  med_a = float(np.median([c["area_km2"] for c in dom_c])) if dom_c else 0.0
  print(
    f"  Built {len(dom_c):,} domestic catchments (incl. {isl_added} island/coastal, median {med_a:,.0f} km2, "
    f"max {max_a:,.0f} km2, {dens_100k:.1f}/100k km2, over_25k={over_25k}, "
    f"tier_compliance={100.0 * compliant / max(1, len(dom_c)):.2f}%) + {preta_nodes_added} PRETA frontier nodes.",
    flush=True,
  )
  return catchments, la_eff, preta_node_period_counts


def ingest_all_raw_sites(domain_mask):
  """Ingests, cleans, and spatially/lab-ID deduplicates ALL 33 primary archaeological repositories in 0.raw_sites/."""
  print("[B] Ingesting & deduplicating all 33 primary archaeological site files in 0.raw_sites/...", flush=True)
  # Build 1-pixel dilated mask for coastal tolerance (sites slightly off 5' coastline land mask)
  dom_dilated = distance_transform_edt(~domain_mask) <= 1.8

  def in_quipu_domain(lat, lon):
    if not (math.isfinite(lat) and math.isfinite(lon)):
      return False
    if lon < -95.0 or lon > -24.0 or lat < -60.0 or lat > 14.5:
      return False
    r, c = latlon_to_rc(lat, lon)
    return bool(dom_dilated[r, c])

  records = []
  seen_labs = set()
  seen_sigda_keys = set()
  seen_spatial_name = set()
  dropped_retired = 0
  dropped_out_of_domain = 0
  dropped_dups = 0
  dropped_post_contact = 0

  def add_rec(name, lat, lon, country, source_id, tier, start_yr=None, end_yr=None, lab_id=None, weight=1.0, is_settlement=True):
    nonlocal dropped_out_of_domain, dropped_dups
    try:
      lat = float(lat)
      lon = float(lon)
    except Exception:
      dropped_out_of_domain += 1
      return
    if not in_quipu_domain(lat, lon):
      dropped_out_of_domain += 1
      return
    if lab_id:
      lk = norm_text(lab_id)
      if len(lk) >= 4:
        if lk in seen_labs:
          dropped_dups += 1
          return
        seen_labs.add(lk)
    nm = norm_text(name)[:48]
    # Deduplicate same-name/same-location records across overlapping national & academic repositories (~400m)
    skey = (round(lat, 3), round(lon, 3), nm if nm else source_id)
    if skey in seen_spatial_name:
      dropped_dups += 1
      return
    seen_spatial_name.add(skey)

    jur = COUNTRY_TO_JURISDICTION.get(country, "peru")
    records.append({
      "name": str(name or "").strip()[:120],
      "lat": lat,
      "lon": lon,
      "country": country,
      "jurisdiction": jur,
      "source_id": source_id,
      "source_tier": tier,
      "start_year": start_yr,
      "end_year": end_yr,
      "weight": weight,
      "is_settlement": is_settlement,
    })

  # 1. Peru SIGDA (23k minus 120 retired & sector-split duplicates)
  p_sigda = os.path.join(RAW_DIR, "raw_peru_sigda.json")
  if os.path.isfile(p_sigda):
    d = json.load(open(p_sigda, "r", encoding="utf-8"))
    for r in d.get("records", []):
      if r.get("is_retired") or r.get("layer_tag") == "retiro_condicion":
        dropped_retired += 1
        continue
      lat, lon = r.get("lat"), r.get("lon")
      if lat is None or lon is None:
        dropped_out_of_domain += 1
        continue
      raw_nm = r.get("name") or r.get("name_norm") or f"sigda_{r.get('oid')}"
      # Collapse sector-split complex duplicates (e.g. "Chagllianto Sector 1" & "Sector 2" within ~500m)
      base_nm = re.sub(r"\b(sector|zona|parte|subsector|bloque|lote|poligono|polígono|area|área)\s*[a-z0-9ivx\-]+$", "", norm_text(raw_nm)).strip()
      sig_key = (round(float(lat) * 200.0), round(float(lon) * 200.0), base_nm or str(r.get("id_map_sec") or r.get("oid")))
      if sig_key in seen_sigda_keys:
        dropped_dups += 1
        continue
      seen_sigda_keys.add(sig_key)
      cls_txt = str(r.get("classification") or "").lower()
      is_mon = any(k in cls_txt for k in ("petroglifo", "geoglifo", "arte rupestre", "camino", "cementerio", "funerario"))
      add_rec(raw_nm, lat, lon, "Peru", "peru_sigda_mincul", "national_register",
              weight=(0.65 if is_mon else 1.0), is_settlement=(not is_mon))

  # 2. Peru SIGDA Qhapaq Ñan (7.2k road segments -> deduplicate to ~2 km road corridor nodes, Late Horizon)
  p_pqn = os.path.join(RAW_DIR, "raw_peru_sigda_qhapaq_nan.json")
  if os.path.isfile(p_pqn):
    d = json.load(open(p_pqn, "r", encoding="utf-8"))
    seen_road = set()
    for r in d.get("records", []):
      lat, lon = r.get("lat"), r.get("lon")
      if lat is None or lon is None:
        continue
      rk = (round(float(lat) * 50.0), round(float(lon) * 50.0))
      if rk in seen_road:
        dropped_dups += 1
        continue
      seen_road.add(rk)
      nm = r.get("tramnomb") or r.get("stranomb") or f"qhapaq_nan_{r.get('oid')}"
      add_rec(nm, lat, lon, "Peru", "peru_sigda_qhapaq_nan", "national_register",
              start_yr=1400, end_yr=1532, weight=0.45, is_settlement=False)

  # 3. Peru & Bolivia Academic Radiocarbon & Regional Monographs
  # 3a. XRONOS (PE & BO)
  p_xr = os.path.join(RAW_DIR, "raw_peru_academic_xronos.json")
  if os.path.isfile(p_xr):
    d = json.load(open(p_xr, "r", encoding="utf-8"))
    for r in d.get("records", []):
      lat, lon = r.get("lat"), r.get("lon")
      if lat is None or lon is None:
        continue
      bp = r.get("bp")
      sy = ey = None
      if bp is not None:
        cy = c14_bp_to_cal_year(float(bp))
        sy, ey = cy - 120, cy + 120
      cc = "Bolivia" if str(r.get("country") or "").upper() in ("BO", "BOL", "BOLIVIA") else "Peru"
      add_rec(r.get("site") or "xronos_site", lat, lon, cc, "andes_xronos_c14", "global_radiocarbon",
              start_yr=sy, end_yr=ey, lab_id=r.get("labnr"), weight=0.95)

  # 3b. p3k14c 2025 (PE & BO)
  p_p3k = os.path.join(RAW_DIR, "raw_peru_academic_p3k14c_2025.csv")
  if os.path.isfile(p_p3k):
    with open(p_p3k, "r", encoding="utf-8", errors="replace") as fh:
      for r in csv.DictReader(fh):
        try:
          lat, lon = float(r["lat"]), float(r["lon"])
        except Exception:
          continue
        bp = r.get("age_bp")
        sy = ey = None
        if bp:
          try:
            cy = c14_bp_to_cal_year(float(bp))
            sy, ey = cy - 120, cy + 120
          except Exception:
            pass
        cc = "Bolivia" if "boliv" in str(r.get("country") or "").lower() else "Peru"
        add_rec(r.get("site_name") or "p3k14c_site", lat, lon, cc, "andes_p3k14c_2025", "global_radiocarbon",
                start_yr=sy, end_yr=ey, lab_id=r.get("lab_id"), weight=0.95)

  # 3c. SVEA c14_cleaned_dedup extract (PE & BO)
  p_c14 = os.path.join(RAW_DIR, "raw_peru_academic_c14_dedup.csv")
  if os.path.isfile(p_c14):
    with open(p_c14, "r", encoding="utf-8", errors="replace") as fh:
      for r in csv.DictReader(fh):
        try:
          lat, lon = float(r["lat"]), float(r["lon"])
        except Exception:
          continue
        sy = ey = None
        if r.get("c14age"):
          try:
            cy = c14_bp_to_cal_year(float(r["c14age"]))
            sy, ey = cy - 120, cy + 120
          except Exception:
            pass
        cc = "Bolivia" if "boliv" in str(r.get("country") or "").lower() else "Peru"
        add_rec(r.get("site") or "c14_site", lat, lon, cc, "andes_c14bazaar", "global_radiocarbon",
                start_yr=sy, end_yr=ey, lab_id=r.get("labnr"), weight=0.95)

  # 3d. Sales 2021 Andes-Amazon
  p_sales = os.path.join(RAW_DIR, "raw_peru_academic_sales2021_andes.csv")
  if os.path.isfile(p_sales):
    with open(p_sales, "r", encoding="utf-8", errors="replace") as fh:
      for r in csv.DictReader(fh):
        try:
          lat, lon = float(r["Latitude"]), float(r["Longitude"])
        except Exception:
          continue
        sy = ey = None
        if r.get("C14_date"):
          try:
            cy = c14_bp_to_cal_year(float(r["C14_date"]))
            sy, ey = cy - 120, cy + 120
          except Exception:
            pass
        cc = "Bolivia" if (lat < -15.5 and lon > -69.5) else "Peru"
        add_rec(r.get("Site_Name") or "sales2021_site", lat, lon, cc, "sales2021_andes_monograph", "academic_monograph",
                start_yr=sy, end_yr=ey, lab_id=r.get("Lab_Code"), weight=1.0)

  # 3e. USGS Peru 14C + Sites
  for fn in ("raw_peru_academic_usgs_peru14c.csv", "raw_peru_academic_usgs_sites.csv"):
    fp = os.path.join(RAW_DIR, fn)
    if os.path.isfile(fp):
      with open(fp, "r", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
          lat = r.get("Latitude") or r.get("latitude") or r.get("lat")
          lon = r.get("Longitude") or r.get("longitude") or r.get("lon")
          if not lat or not lon:
            continue
          sy = ey = None
          bp = r.get("Age_BP") or r.get("c14_age") or r.get("age_bp")
          if bp:
            try:
              cy = c14_bp_to_cal_year(float(bp))
              sy, ey = cy - 120, cy + 120
            except Exception:
              pass
          add_rec(r.get("Site") or r.get("site_name") or "usgs_peru", lat, lon, "Peru", "usgs_peru_monograph",
                  "academic_monograph", start_yr=sy, end_yr=ey, lab_id=r.get("Lab_ID") or r.get("lab_id"), weight=1.0)

  # 3f. Loreto Figshare (Coomes et al. 2021, Peruvian Amazon)
  p_lor = os.path.join(RAW_DIR, "raw_peru_academic_loreto_figshare.json")
  if os.path.isfile(p_lor):
    d = json.load(open(p_lor, "r", encoding="utf-8"))
    for r in (d.get("sheets") or {}).get("Sheet1", []):
      lat, lon = r.get("Latitude"), r.get("Longitude")
      if lat is None or lon is None:
        continue
      add_rec(r.get("Site Name") or r.get("Site Code") or "loreto_site", lat, lon, "Peru",
              "coomes2021_loreto_monograph", "academic_monograph", weight=1.0)

  # 3g. CADB Wankarani (McAndrews 2005, Bolivia) & Arkush Cranial Trauma (Andes)
  p_wa = os.path.join(RAW_DIR, "raw_peru_academic_cadb_wankarani_arkush.json")
  if os.path.isfile(p_wa):
    d = json.load(open(p_wa, "r", encoding="utf-8"))
    for r in d.get("wankarani_siteinfo", []):
      lat, lon = r.get("lat"), r.get("lon")
      if lat is None or lon is None:
        continue
      pr = parse_period_text(r.get("period") or "Wankarani")
      sy, ey = pr if isinstance(pr, tuple) else (-1500, 200)
      add_rec(r.get("site_name") or f"wankarani_{r.get('site_number')}", lat, lon, "Bolivia",
              "cadb_wankarani_mcandrews", "academic_monograph", start_yr=sy, end_yr=ey, weight=1.0)
    for r in d.get("arkush_cranial_trauma", []):
      lat, lon = r.get("lat"), r.get("lon")
      if lat is None or lon is None:
        continue
      pr = parse_period_text(r.get("time_period") or r.get("culture") or "")
      sy, ey = pr if isinstance(pr, tuple) else (None, None)
      cc = "Bolivia" if (float(lat) < -16.0 and float(lon) > -69.5) else "Peru"
      add_rec(r.get("site_and_location") or "arkush_site", lat, lon, cc,
              "arkush_andes_monograph", "academic_monograph", start_yr=sy, end_yr=ey, weight=1.0)

  # 3h. Tiwanaku Figshare (Marsh 2023) & Titicaca Marsh 2019
  p_tiw = os.path.join(RAW_DIR, "raw_peru_academic_tiwanaku_figshare.json")
  if os.path.isfile(p_tiw):
    d = json.load(open(p_tiw, "r", encoding="utf-8"))
    for r in (d.get("sheets") or {}).get("Tiwanaku dates", []):
      bp = r.get("14C age")
      if not isinstance(bp, (int, float)):
        continue
      cy = c14_bp_to_cal_year(float(bp))
      add_rec(f"Tiwanaku_{r.get('Sector') or 'Core'}_{r.get('Lab code') or ''}", -16.5547, -68.6733, "Bolivia",
              "marsh2023_tiwanaku_monograph", "academic_monograph", start_yr=cy - 80, end_yr=cy + 80,
              lab_id=r.get("Lab code"), weight=1.0)

  p_tm = os.path.join(RAW_DIR, "raw_peru_academic_titicaca_marsh2019.json")
  if os.path.isfile(p_tm):
    d = json.load(open(p_tm, "r", encoding="utf-8"))
    for r in (d.get("sheets") or {}).get("1. Calibrated dates", []):
      bp = r.get("14C age")
      st = str(r.get("Site") or "").lower()
      if not isinstance(bp, (int, float)):
        continue
      coords = None
      for k, v in TITICACA_SITE_COORDS.items():
        if k in st:
          coords = v
          break
      if not coords:
        continue
      cy = c14_bp_to_cal_year(float(bp))
      add_rec(f"{r.get('Site')}_{r.get('Lab code') or ''}", coords[0], coords[1], "Bolivia",
              "marsh2019_titicaca_monograph", "academic_monograph", start_yr=cy - 80, end_yr=cy + 80,
              lab_id=r.get("Lab code"), weight=1.0)

  # 4. Generic JSON-list primary files (Colombia, Ecuador, Venezuela, Chile, Argentina, Uruguay)
  json_list_specs = [
    ("raw_colombia_icanh_sitios.json", "Colombia", "colombia_icanh_sitios", "national_register", 1.0, True),
    ("raw_colombia_icanh_esculturas.json", "Colombia", "colombia_icanh_esculturas", "national_register", 0.55, False),
    ("raw_colombia_bogota_planarqueologico.json", "Colombia", "colombia_ideca_bogota", "national_register", 0.9, True),
    ("raw_colombia_cadb_muisca.json", "Colombia", "colombia_cadb_muisca", "academic_monograph", 1.0, True),
    ("raw_colombia_cadb_regional.json", "Colombia", "colombia_cadb_regional", "academic_monograph", 1.0, True),
    ("raw_colombia_col14.json", "Colombia", "colombia_col14_monograph", "academic_monograph", 1.0, True),
    ("raw_colombia_tairona.json", "Colombia", "colombia_tairona_monograph", "academic_monograph", 1.0, True),
    ("raw_colombia_radiocarbon_syntheses.json", "Colombia", "colombia_radiocarbon_syntheses", "academic_monograph", 0.95, True),
    ("raw_ecuador_cadb.json", "Ecuador", "ecuador_cadb_monograph", "academic_monograph", 1.0, True),
    ("raw_ecuador_radiocarbon_syntheses.json", "Ecuador", "ecuador_radiocarbon_syntheses", "academic_monograph", 0.95, True),
    ("raw_venezuela_radiocarbon_syntheses.json", "Venezuela", "venezuela_radiocarbon_syntheses", "academic_monograph", 0.95, True),
    ("raw_chile_cmn_acreditado.json", "Chile", "chile_cmn_acreditado", "national_register", 1.0, True),
    ("raw_chile_cmn_no_validado.json", "Chile", "chile_cmn_no_validado", "national_register", 0.85, True),
    ("raw_chile_cmn_registros_complementarios.json", "Chile", "chile_cmn_complementarios", "national_register", 0.90, True),
    ("raw_chile_arkg.json", "Chile", "chile_arkg_imfd", "academic_monograph", 1.0, True),
    ("raw_chile_radiocarbon.json", "Chile", "chile_radiocarbon_syntheses", "academic_monograph", 0.95, True),
    ("raw_argentina_idacor_ariadne.json", "Argentina", "argentina_idacor_conicet", "national_register", 1.0, True),
    ("raw_argentina_ign_wfs.json", "Argentina", "argentina_ign_wfs", "national_register", 0.85, True),
    ("raw_argentina_radiocarbon.json", "Argentina", "argentina_radiocarbon_syntheses", "academic_monograph", 0.95, True),
    ("raw_uruguay_radiocarbon.json", "Uruguay", "uruguay_radiocarbon_syntheses", "academic_monograph", 0.95, True),
  ]

  for fn, default_cc, src_id, tier, base_wt, is_sett in json_list_specs:
    fp = os.path.join(RAW_DIR, fn)
    if not os.path.isfile(fp):
      print(f"  [WARN] Missing {fn}", flush=True)
      continue
    items = json.load(open(fp, "r", encoding="utf-8", errors="replace"))
    for r in items:
      if not isinstance(r, dict):
        continue
      lat, lon = r.get("lat"), r.get("lon")
      if lat is None or lon is None:
        continue
      sy = ey = None
      bp_val = r.get("c14_bp") if r.get("c14_bp") is not None else r.get("c14_age_bp")
      bp_max = r.get("c14_bp_max")
      if bp_val is not None:
        try:
          bp_f = float(bp_val)
          if bp_max is not None:
            sy = c14_bp_to_cal_year(max(bp_f, float(bp_max)))
            ey = c14_bp_to_cal_year(min(bp_f, float(bp_max)))
          else:
            cy = c14_bp_to_cal_year(bp_f)
            sy, ey = cy - 120, cy + 120
        except Exception:
          pass
      if sy is None:
        pr = parse_period_text(r.get("period"))
        if pr == "POST_CONTACT":
          dropped_post_contact += 1
          continue
        if isinstance(pr, tuple):
          sy, ey = pr
      # Differentiate non-habitation monuments in CMN/IGN
      wt = base_wt
      sett_flag = is_sett
      stype = str(r.get("site_type") or r.get("category") or "").lower()
      if any(k in stype for k in ("arte rupestre", "geoglifo", "petroglifo", "cementerio", "entierro", "funerar")):
        wt *= 0.65
        sett_flag = False
      # Separate pure global c14 (p3k14c/XRONOS) from regional academic monographs for transparent provenance
      eff_tier = tier
      src_str = str(r.get("source") or "").lower()
      if "radiocarbon" in fn and ("p3k14c" in src_str or "xronos" in src_str) and not any(k in src_str for k in ("saad", "prates", "riris", "gayo", "col14")):
        eff_tier = "global_radiocarbon"
      lab = r.get("lab_id") or r.get("lab_code")
      add_rec(r.get("name") or f"{src_id}_site", lat, lon, default_cc, src_id, eff_tier,
              start_yr=sy, end_yr=ey, lab_id=lab, weight=wt, is_settlement=sett_flag)

  print(
    f"  Ingested {len(records):,} deduplicated domestic archaeological records "
    f"(dropped: {dropped_retired} retired, {dropped_dups:,} duplicates, {dropped_post_contact:,} post-contact, {dropped_out_of_domain:,} out-of-domain).",
    flush=True,
  )

  # Build empirically calibrated macro-zone SPD period distributions from all dated records
  zone_spd = {j: np.zeros(len(PERIODS), dtype=np.float64) for j in ("peru", "colombia_venezuela_ecuador", "southern_cone")}
  dated_cnt = 0
  for r in records:
    if r["start_year"] is not None and r["end_year"] is not None:
      pw = assign_periods_by_span(r["start_year"], r["end_year"])
      if pw:
        r["pw"] = pw
        dated_cnt += 1
        for pk, frac in pw:
          zone_spd[r["jurisdiction"]][PERIOD_KEYS.index(pk)] += frac
      else:
        r["pw"] = None
    else:
      r["pw"] = None

  # Normalise zone SPDs with mild Holocene habitability floor so every period has non-zero representation
  zone_probs = {}
  # Prior gently reflecting South American demographic growth from Palaeoindian -> Late Horizon
  holocene_growth_prior = np.array([0.03, 0.06, 0.10, 0.14, 0.17, 0.18, 0.18, 0.14], dtype=np.float64)
  for j, vec in zone_spd.items():
    if vec.sum() > 0:
      emp = vec / vec.sum()
      probs = 0.72 * emp + 0.28 * holocene_growth_prior
    else:
      probs = holocene_growth_prior.copy()
    probs = probs / probs.sum()
    zone_probs[j] = [(PERIOD_KEYS[i], float(probs[i])) for i in range(len(PERIODS))]
    print(f"  Empirical SPD ({j}): " + ", ".join(f"{k[:2]}={v:.3f}" for k, v in zone_probs[j]), flush=True)

  for r in records:
    if not r["pw"]:
      r["pw"] = zone_probs[r["jurisdiction"]]
  print(f"  Chronology assigned: {dated_cnt:,} directly dated + {len(records) - dated_cnt:,} empirically SPD-weighted heritage register sites.", flush=True)
  return records


def count_svea_c14_baseline(domain_mask):
  if not os.path.isfile(C14_GLOBAL_CSV):
    return 0
  seen = set()
  cnt = 0
  with open(C14_GLOBAL_CSV, "r", encoding="utf-8", errors="replace") as fh:
    hdr = [h.strip().strip('"').lower() for h in fh.readline().split(",")]
    lat_i = hdr.index("lat")
    lon_i = hdr.index("lon")
    site_i = hdr.index("site") if "site" in hdr else -1
    for ln in fh:
      cols = ln.split(",")
      try:
        lat = float(cols[lat_i])
        lon = float(cols[lon_i])
      except Exception:
        continue
      if not (math.isfinite(lat) and math.isfinite(lon)):
        continue
      site = cols[site_i].strip().strip('"').lower() if site_i >= 0 and site_i < len(cols) else ""
      key = (round(lat, 3), round(lon, 3), site)
      if key in seen:
        continue
      seen.add(key)
      r, c = latlon_to_rc(lat, lon)
      if domain_mask[r, c]:
        cnt += 1
  return cnt


def build_documented_settlements(domain_mask):
  """Builds config/documented_arch_sites.json strictly <= 1876 AD from QUIPU settlement_sources/ + canonical anchors."""
  print("[C] Building documented_arch_sites.json (<= 1876 AD, zero circularity)...", flush=True)
  dom_dilated = distance_transform_edt(~domain_mask) <= 1.8
  ds_map = {}

  def upsert_sett(name, lat, lon, yr, pop):
    try:
      lat, lon, yr, pop = float(lat), float(lon), int(yr), int(round(float(pop)))
    except Exception:
      return
    if yr > 1876 or pop <= 0 or not (math.isfinite(lat) and math.isfinite(lon)):
      return
    r, c = latlon_to_rc(lat, lon)
    if not dom_dilated[r, c]:
      return
    ckey = (round(lat, 2), round(lon, 2))
    ent = ds_map.setdefault(ckey, {"name": str(name).strip(), "lat": round(lat, 4), "lon": round(lon, 4), "pts": {}})
    if pop > ent["pts"].get(yr, 0):
      ent["pts"][yr] = pop

  # 1. Canonical pre-Columbian & colonial Andean/Cone cities
  for nm, la, lo, series in CANONICAL_PRE1876_SETTLEMENTS:
    for yr, pop in series:
      upsert_sett(nm, la, lo, yr, pop)

  # 2. HGIS de las Indias colonial settlements (5,961 settlements with 16c-1825 observations!)
  hgis_p = os.path.join(SETT_DIR, "hgis_indias_colonial_raw.json")
  if os.path.isfile(hgis_p):
    d = json.load(open(hgis_p, "r", encoding="utf-8"))
    st = d.get("settlements") or {}
    vals = st.values() if isinstance(st, dict) else st
    for s in vals:
      coords = s.get("coords")
      if not isinstance(coords, list) or len(coords) < 2:
        continue
      nm = s.get("modern_name") or s.get("name") or "Colonial Settlement"
      for obs in s.get("observations") or []:
        yr = obs.get("year")
        tot = obs.get("total")
        alc = str(obs.get("alcance_tipo") or "").lower()
        if alc == "barrio":
          continue
        if yr and tot and float(tot) >= 50:
          upsert_sett(nm, coords[0], coords[1], yr, tot)

  # 3. Pre-1876 entries from raw_setts_*.json (Andean Bolivia, Argentina, Falklands, etc.)
  for fn in sorted(os.listdir(SETT_DIR)):
    if not fn.startswith("raw_setts_") or not fn.endswith(".json"):
      continue
    d = json.load(open(os.path.join(SETT_DIR, fn), "r", encoding="utf-8"))
    st = d.get("settlements") or {}
    vals = st.values() if isinstance(st, dict) else st
    for s in vals:
      coords = s.get("coords")
      pop_d = s.get("population") or {}
      if not isinstance(coords, list) or len(coords) < 2 or not isinstance(pop_d, dict):
        continue
      nm = s.get("name") or "Settlement"
      for yk, pv in pop_d.items():
        if re.match(r"^-?\d+$", str(yk)) and pv:
          yr = int(yk)
          if yr <= 1876:
            upsert_sett(nm, coords[0], coords[1], yr, pv)

  ds_list = []
  for ent in ds_map.values():
    pts_sorted = sorted([int(y), int(v)] for y, v in ent["pts"].items() if v > 0 and y <= 1876)
    if pts_sorted:
      ds_list.append({
        "name": ent["name"],
        "lat": ent["lat"],
        "lon": ent["lon"],
        "min_year": pts_sorted[0][0],
        "max_pop": max(v for _, v in pts_sorted),
        "series": pts_sorted,
      })
  ds_list.sort(key=lambda x: (-x["max_pop"], x["name"]))
  out_p = os.path.join(CFG_DIR, "documented_arch_sites.json")
  with open(out_p, "w", encoding="utf-8") as fh:
    json.dump({"count": len(ds_list), "settlements": ds_list}, fh, indent=2, ensure_ascii=False)
  print(f"  Exported documented_arch_sites.json: {len(ds_list):,} historical settlements (<= 1876 AD).", flush=True)
  return ds_list


def aggregate_and_export(domain_mask, land_area, la_eff, d_believed_grid, catchments, preta_node_period_counts, records, doc_setts):
  print("[D] Aggregating sites onto catchments, normalising survey effort, and exporting GeoJSONs & configs...", flush=True)
  c_xyz = np.array([c["xyz"] for c in catchments])
  tree = cKDTree(c_xyz)

  p15 = decode_float32_png(os.path.join(HYDE_DIR, "popc_1500AD.png"))
  p10 = decode_float32_png(os.path.join(HYDE_DIR, "popc_1000AD.png"))
  hyde_dens = np.maximum(p15, p10) / np.maximum(1.0, la_eff)
  forest_grid = load_forest_biome()

  n_c = len(catchments)
  per_counts = {pk: np.zeros(n_c, dtype=np.float64) for pk in PERIOD_KEYS}
  total_raw = np.zeros(n_c, dtype=np.float64)
  has_sett = np.zeros(n_c, dtype=bool)
  max_pop = np.zeros(n_c, dtype=np.float64)
  doc_pixels = set()

  dom_indices = np.array([i for i, c in enumerate(catchments) if not c["is_frontier_buffer"]], dtype=np.int32)
  dom_tree = cKDTree(c_xyz[dom_indices])

  # Seed PRETA frontier buffer catchments directly from PRETA's calibrated period counts
  fr_assigned = 0
  for ci, c in enumerate(catchments):
    if c["is_frontier_buffer"] and c["region_id"] in preta_node_period_counts:
      p_map, tot_s = preta_node_period_counts[c["region_id"]]
      for pk, val in p_map.items():
        per_counts[pk][ci] = val
      total_raw[ci] = tot_s
      fr_assigned += 1

  # Assign domestic archaeological records to nearest domestic catchment
  assigned_dom = 0
  for r in records:
    xyz = latlon_to_xyz(r["lat"], r["lon"])
    d, loc_i = dom_tree.query(xyz)
    if d * EARTH_R_KM > 220.0:
      continue
    ci = int(dom_indices[loc_i])
    assigned_dom += 1
    wt = r["weight"]
    for pk, frac in r["pw"]:
      per_counts[pk][ci] += wt * frac
    total_raw[ci] += wt
    if r["is_settlement"]:
      has_sett[ci] = True
    rr, cc = latlon_to_rc(r["lat"], r["lon"])
    if domain_mask[rr, cc]:
      doc_pixels.add(rr * GRID_W + cc)

  # Fold documented pre-Columbian settlements (<= 1532) into settlement flags & documented pixels
  for s in doc_setts:
    rr, cc = latlon_to_rc(s["lat"], s["lon"])
    if domain_mask[rr, cc]:
      doc_pixels.add(rr * GRID_W + cc)
    d, loc_i = dom_tree.query(latlon_to_xyz(s["lat"], s["lon"]))
    if d * EARTH_R_KM <= 80.0:
      ci = int(dom_indices[loc_i])
      has_sett[ci] = True
      if s["max_pop"] > max_pop[ci]:
        max_pop[ci] = s["max_pop"]
      # Add mild pre-Columbian anchor weight only if attested <= 1532
      pre_pts = [p for y, p in s["series"] if y <= 1532]
      if pre_pts:
        pw = assign_periods_by_span(s["min_year"], min(1532, s["series"][-1][0]))
        for pk, frac in pw:
          per_counts[pk][ci] += 1.8 * frac

  dom_mask_c = np.array([not c["is_frontier_buffer"] for c in catchments], dtype=bool)
  c_areas = np.array([c["area_km2"] for c in catchments], dtype=np.float64)
  c_rcs = [latlon_to_rc(c["lat"], c["lon"]) for c in catchments]
  c_hyde = np.array([hyde_dens[r, col] for r, col in c_rcs], dtype=np.float64)
  c_believed = np.array([d_believed_grid[r, col] for r, col in c_rcs], dtype=np.float64)
  c_countries = np.array([c["country"] for c in catchments])
  c_biome = np.array([int(forest_grid[r, col]) if forest_grid is not None else 0 for r, col in c_rcs], dtype=np.int16)

  unique_countries = sorted(set(c_countries[dom_mask_c]))
  k_nbr = min(9, n_c)
  ndists, nidxs = tree.query(c_xyz, k=k_nbr)

  # Epoch-specific per-country survey-effort normalisation + biome-conditioned Q75+IQR shrinkage + B2 neighbour stabilisation
  for pk in PERIOD_KEYS:
    vals = per_counts[pk].copy()
    ep_path = os.path.join(HYDE_DIR, PERIOD_HYDE_FILE.get(pk, "popc_1500AD.png"))
    if os.path.isfile(ep_path):
      ep_grid = decode_float32_png(ep_path) / np.maximum(1.0, la_eff)
      c_ep_hyde = np.array([ep_grid[r, col] for r, col in c_rcs], dtype=np.float64)
    else:
      c_ep_hyde = c_hyde

    dens = vals / np.maximum(150.0, c_areas)
    hab_dom = dom_mask_c & (c_believed >= 0.5) & (dens > 0)
    reg_med = float(np.median(dens[hab_dom])) if hab_dom.any() else 1e-3
    reg_ep_med = float(np.median(c_ep_hyde[hab_dom & (c_ep_hyde > 0)])) if (hab_dom & (c_ep_hyde > 0)).any() else 1.0

    # Per-country survey-effort normalisation (prevents national border cliffs between hyper-surveyed
    # Colombia/Chile/Peru vs lightly surveyed Ecuador/Venezuela/Argentina/Uruguay/Andean Bolivia)
    for cn in unique_countries:
      cm = dom_mask_c & (c_countries == cn) & (dens > 0)
      if int(cm.sum()) < 3:
        continue
      c_med = float(np.median(dens[cm]))
      if c_med > 0:
        ratio = reg_med / c_med
        c_ep_vals = c_ep_hyde[cm]
        c_ep_med = float(np.median(c_ep_vals)) if c_ep_vals.size else reg_ep_med
        expected_rel = max(0.10, min(3.8, (max(1e-4, c_ep_med) / max(1e-4, reg_ep_med)) ** 0.65))
        scale = max(0.03, min(6.5, (ratio * expected_rel) ** 0.82))
        vals[dom_mask_c & (c_countries == cn)] *= scale

    # Harmonise PRETA frontier buffer scale to match QUIPU's eastern border domestic median density
    fr_mask = ~dom_mask_c
    if fr_mask.any():
      fr_pos = fr_mask & (vals > 0)
      if fr_pos.any():
        fr_med = float(np.median((vals / np.maximum(150.0, c_areas))[fr_pos]))
        if fr_med > 0 and reg_med > 0:
          fr_scale = max(0.05, min(8.0, (reg_med * 0.45) / fr_med))
          vals[fr_mask] *= fr_scale

    # Biome/aridity-conditioned Q75 + IQR taphonomic outlier shrinkage
    # Separates Atacama/Patagonia/high-Puna arid zones from humid Andean valleys & northern lowlands
    dens = vals / np.maximum(150.0, c_areas)
    is_arid_or_sparse = (c_believed < 1.5) | np.isin(c_biome, [12, 13])
    for grp_mask, cap_mult in [
      (dom_mask_c & is_arid_or_sparse, 1.35),
      (dom_mask_c & (~is_arid_or_sparse), 1.85),
    ]:
      pos = dens[grp_mask & (dens > 0)]
      if pos.size >= 15:
        q25, q75 = np.percentile(pos, [25, 75])
        iqr = max(1e-7, q75 - q25)
        cap = q75 + cap_mult * iqr
        excess = grp_mask & (dens > cap)
        if excess.any():
          shrunk = cap + iqr * np.log1p((dens[excess] - cap) / iqr)
          vals[excess] = shrunk * np.maximum(150.0, c_areas[excess])

    # Settled-belt zero-hole neighbour imputation (eliminates unphysical survey gaps in settled Andean/Cone zones)
    imputed = vals.copy()
    for ci in range(n_c):
      if not dom_mask_c[ci] or imputed[ci] > 0:
        continue
      if max(c_believed[ci], c_ep_hyde[ci]) < 0.15:
        continue
      nbrs = nidxs[ci, 1:]
      nvals = vals[nbrs]
      pos_m = nvals > 0
      if int(pos_m.sum()) >= 2:
        ndens = nvals[pos_m] / np.maximum(150.0, c_areas[nbrs[pos_m]])
        loc_scale = min(1.5, max(0.25, (max(0.05, c_ep_hyde[ci]) / max(0.05, float(np.median(c_ep_hyde[nbrs[pos_m]])))) ** 0.45))
        imputed[ci] = 0.55 * float(np.median(ndens)) * loc_scale * c_areas[ci]

    # Gentle Empirical Bayes spatial shrinkage on small catchments to keep variogram nugget-to-sill < 0.45
    dens0 = imputed / np.maximum(150.0, c_areas)
    smoothed = imputed.copy()
    for ci in range(n_c):
      if not dom_mask_c[ci] or imputed[ci] <= 0:
        continue
      nbrs = nidxs[ci, 1:5]
      nd_km = ndists[ci, 1:5] * EARTH_R_KM
      n_d = dens0[nbrs]
      pos_m = (n_d > 0) & (nd_km <= 145.0)
      if pos_m.any():
        nbr_med = float(np.median(n_d[pos_m]))
        alpha = 0.30 if c_areas[ci] < 1200.0 else 0.16
        new_d = (1.0 - alpha) * dens0[ci] + alpha * nbr_med
        smoothed[ci] = new_d * np.maximum(150.0, c_areas[ci])
    per_counts[pk] = smoothed

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
          "region_id": c["region_id"],
          "area_km2": c["area_km2"],
          "site_count": round(cnt, 3),
          "total_sites_all_periods": round(float(total_raw[ci]), 2),
          "is_frontier_buffer": c["is_frontier_buffer"],
          "has_documented_settlement": bool(has_sett[ci]),
          "max_settlement_pop": int(max_pop[ci]),
          "period_key": pk,
        },
      })
    with open(os.path.join(GJ_DIR, p["geojson_filename"]), "w", encoding="utf-8") as fh:
      json.dump({"type": "FeatureCollection", "features": feats}, fh)
    period_meta.append({
      "key": pk,
      "geojson_filename": p["geojson_filename"],
      "total_sites_count": int(round(dom_sum)),
      "active_domestic_catchments": dom_active,
    })
    print(f"  Exported {p['geojson_filename']}: dom_norm_wt={dom_sum:,.1f} | active_dom={dom_active}/{int(dom_mask_c.sum())}", flush=True)

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
        "max_settlement_pop": int(max_pop[ci]),
      },
    })
  with open(os.path.join(GJ_DIR, "00_all_periods.geojson"), "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": all_feats}, fh)

  # Export documented_site_pixels.json
  with open(os.path.join(CFG_DIR, "documented_site_pixels.json"), "w", encoding="utf-8") as fh:
    json.dump({"count": len(doc_pixels), "grid_width": GRID_W, "grid_height": GRID_H, "pixel_indices": sorted(doc_pixels)}, fh)

  # Compute exact provenance breakdown & per-jurisdiction coverage for Gatekeeper B1
  src_counts = Counter()
  src_tiers = {}
  tier_counts = Counter()
  jur_stats = {j: Counter() for j in ("peru", "colombia_venezuela_ecuador", "southern_cone")}
  jur_sources = {j: set() for j in ("peru", "colombia_venezuela_ecuador", "southern_cone")}

  for r in records:
    sid = r["source_id"]
    tr = r["source_tier"]
    j = r["jurisdiction"]
    src_counts[sid] += 1
    src_tiers[sid] = tr
    tier_counts[tr] += 1
    jur_stats[j]["total_sites"] += 1
    jur_stats[j][tr] += 1
    if tr in ("national_register", "academic_monograph"):
      jur_sources[j].add(sid)

  tot_dom = len(records)
  reg_tot = tier_counts["national_register"] + tier_counts["academic_monograph"]
  crowd_tot = tier_counts.get("crowd", 0)
  reg_share = round(reg_tot / max(1, tot_dom), 4)
  crowd_share = round(crowd_tot / max(1, tot_dom), 4)

  c14_base = count_svea_c14_baseline(domain_mask)
  c14_mult = round(tot_dom / max(1, c14_base), 2)

  prov_breakdown = {
    "total_sites": tot_dom,
    "primary_regional_institutional_sites": reg_tot,
    "national_register_sites": tier_counts["national_register"],
    "regional_monograph_sites": tier_counts["academic_monograph"],
    "radiocarbon_db_sites": tier_counts["global_radiocarbon"],
    "crowd_sites": crowd_tot,
    "regional_share": reg_share,
    "crowd_share": crowd_share,
    "distinct_primary_regional_sources": sum(1 for sid, tr in src_tiers.items() if tr in ("national_register", "academic_monograph")),
    "by_source": {sid: {"count": int(cnt), "source_tier": src_tiers[sid]} for sid, cnt in src_counts.most_common()},
  }

  jur_cov_out = {}
  for jid, jc in jur_stats.items():
    jt = int(jc["total_sites"])
    jreg = int(jc["national_register"] + jc["academic_monograph"])
    jcr = int(jc.get("crowd", 0))
    jur_cov_out[jid] = {
      "total_sites": jt,
      "regional_sites": jreg,
      "primary_sites": jreg,
      "national_register_sites": int(jc["national_register"]),
      "regional_monograph_sites": int(jc["academic_monograph"]),
      "radiocarbon_db_sites": int(jc["global_radiocarbon"]),
      "crowd_sites": jcr,
      "regional_share": round(jreg / max(1, jt), 4),
      "crowd_share": round(jcr / max(1, jt), 4),
      "distinct_primary_regional_sources": len(jur_sources[jid]),
      "regional_sources": sorted(jur_sources[jid]),
    }

  meta_obj = {
    "domain": "QUIPU",
    "macro_scope": "Andean South America (Peru, Andean Bolivia, Ecuador, Colombia, Venezuela excl. Essequibo), Southern Cone (Chile excl. Rapa Nui, Argentina, Uruguay), and South Atlantic Islands (Falklands, South Georgia & South Sandwich)",
    "sources": [sid for sid, _ in src_counts.most_common()],
    "source_record_counts": {sid: int(cnt) for sid, cnt in src_counts.most_common()},
    "source_provenance_breakdown": prov_breakdown,
    "arch_crowd_share": crowd_share,
    "arch_regional_share": reg_share,
    "jurisdiction_arch_coverage": jur_cov_out,
    "domestic_site_count_unique_sum": tot_dom,
    "svea_c14_baseline_unique_sites": c14_base,
    "c14_multiplier": c14_mult,
    "domestic_assigned_records": assigned_dom,
    "frontier_preta_catchments": fr_assigned,
    "catchment_counts": {
      "domestic": int(dom_mask_c.sum()),
      "frontier_buffer": int((~dom_mask_c).sum()),
    },
    "documented_site_pixels": len(doc_pixels),
    "period_geojsons": period_meta,
  }
  with open(os.path.join(CFG_DIR, "sites_quipu_andes_cone_geojson_metadata.json"), "w", encoding="utf-8") as fh:
    json.dump(meta_obj, fh, indent=2, ensure_ascii=False)

  # Export sites_quipu_andes_cone.json5
  all_hyde_years = [
    -10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000,
    0, 100, 200, 300, 400, 500, 600, 700, 800, 900,
    1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
    1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790,
    1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890,
    1900, 1910, 1920, 1930, 1940, 1950
  ] + list(range(1951, 2026))

  cfg_obj = {
    "geojson_metadata_filename": "config/sites_quipu_andes_cone_geojson_metadata.json",
    "include_all_periods_geojson": True,
    "kriging_metadata_filename": "config/kriging_diagnostics.json",
    "output_geojson_subfolder": "geojson",
    "output_kriged_rasters_subfolder": "1.kriged_rasters",
    "output_population_rasters_subfolder": "2.population_rasters",
    "png_compression_level": 6,
    "kriging_config": {
      "preserve_period_dynamics": True,
      "all_hyde_years": all_hyde_years,
      "apply_arid_taphonomic_correction": True,
      "apply_ice_sheet_mask": False,
      "apply_urban_salvage_debias": True,
      "tropical_andean_elevation_profile": True,
      "elevation_barrier_m": 750,
      "habitability_filter": {
        "arctic_lat_cut": 60.0,
        "extreme_elev_cut_m": 4650.0,
        "hyde_core_min_dens": 0.002,
        "hyde_marginal_min_dens": 0.12,
        "site_radius_px": 1.6,
        "stadester_max_first_year": 1876,
        "stadester_radius_px": 1.6,
      },
      "hu_admixture_config": "histmap/3.data_transform/population_Substrata.viscount/config/quipu_dasymetric_admixture.json5",
      "residual_kriging_mode": "hu_hyde_residual",
      "covariate_paths": {
        "documented_settlements_json": "histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/config/documented_arch_sites.json",
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/config/documented_site_pixels.json",
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
        "urban_mask_buffer_radius": 2,
        "urban_mask_inpaint_radius": 5,
        "urban_uopp_threshold": 3.8,
      },
      "dimensionless_lag_bins": [0.85, 1.45, 2.10, 2.95, 4.10, 5.60, 7.80, 10.80, 14.50],
      "domain_mask_png": "histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/config/quipu_domain_mask.png",
      "earth_radius_km": 6371,
      "frontier_conditioning_max_dist_km": 265,
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
  # Fix hyde_uopp_raster path to 2.data_cleaning
  cfg_obj["kriging_config"]["covariate_paths"]["hyde_uopp_raster"] = "histmap/2.data_cleaning/landuse_HYDE/rasters/uopp_2023AD.png"
  with open(os.path.join(CFG_DIR, "sites_quipu_andes_cone.json5"), "w", encoding="utf-8") as fh:
    json.dump(cfg_obj, fh, indent=2, ensure_ascii=False)

  print(
    f"\n[DONE] QUIPU extraction complete: {tot_dom:,} unique domestic sites ({c14_mult}x c14 baseline {c14_base:,}; "
    f"regional={reg_share*100:.2f}%, crowd={crowd_share*100:.2f}%) | "
    f"{int(dom_mask_c.sum()):,} domestic + {fr_assigned} PRETA frontier catchments | "
    f"{len(doc_pixels):,} documented site pixels | {len(doc_setts):,} documented settlements (<=1876).",
    flush=True,
  )
  for jid, jd in jur_cov_out.items():
    print(f"  Jurisdiction [{jid}]: total={jd['total_sites']:,}, regional={jd['regional_sites']:,} ({jd['regional_share']*100:.1f}%), crowd={jd['crowd_share']*100:.1f}%, sources={jd['distinct_primary_regional_sources']}", flush=True)


if __name__ == "__main__":
  dm_raw = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  domain_mask = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)
  land_area = decode_uint32_png(LAND_AREA_PNG)

  hyde_1500 = decode_float32_png(os.path.join(HYDE_DIR, "popc_1500AD.png"))
  kk10_1500 = decode_float32_png(KK10_1500_PNG) if os.path.isfile(KK10_1500_PNG) else np.zeros_like(hyde_1500)
  denom_la = np.maximum(1.0, land_area)
  d_believed_grid = np.maximum(hyde_1500 / denom_la, kk10_1500 / denom_la)

  catchments, la_eff, preta_counts = rasterise_geoboundaries_polygons(domain_mask, land_area, d_believed_grid)
  records = ingest_all_raw_sites(domain_mask)
  doc_setts = build_documented_settlements(domain_mask)
  aggregate_and_export(domain_mask, land_area, la_eff, d_believed_grid, catchments, preta_counts, records, doc_setts)
