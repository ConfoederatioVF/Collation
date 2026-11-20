"""Multi-Repository Archaeological & Terra Preta (ADE) Catchment Aggregator for Operation Viscount
Project PRETA (`sites_preta_amazon_brazil`).

Composites 15 independent primary sources across PRETA + a 400 km South American cross-frontier
conditioning belt (Peru, Bolivia, Ecuador, Colombia, Venezuela, Chile, Argentina, Uruguay):
  1.  Brazil IPHAN SICG:sitios (32,933 official sites; WFS 1.1.0 lat/lon axis-corrected)
  2.  Walker et al. (2023, PeerJ) Amazonian Archaeological & ADE Database (2,081 sites; 455 explicit ADEs)
  3.  Peripato et al. (2023, Science) Amazonian Earthworks Database (961 earthworks)
  4.  de Souza et al. (rxpand) Tropical South America Radiocarbon Database (2,794 dates)
  5.  Sales et al. (2021, Zenodo) Andean-Amazonian Radiocarbon Database (1,965 dates)
  6.  DOPAMICS (2023, Zenodo) French Guiana Ring-Ditch Hill & ADE Geoarchaeology Pits
  7.  SVEA c14_cleaned_dedup.csv South American Radiocarbon Baseline (2,273 sites)
  8.  Published Amazonian Dark Earth (Terra Preta) & Monumental Earthwork Atlas (80 hubs)
  9.  Peru Ministry of Culture SIGDA — Delimited Pre-Hispanic Monuments (10,999 sites)
  10. Peru Ministry of Culture SIGDA — Registered & Declared Monuments (11,960 sites)
  11. Peru Ministry of Culture SIGDA — Qhapaq Ñan Pre-Hispanic Road & Tambo Nodes (5,379 records)
  12. Colombia ICANH Official Archaeological Sites Registry (22,146 georeferenced sites)
  13. PEOPLE 3000 p3k14c South American Radiocarbon Database (6,264 C14 dates incl. AndesC14 & Bolivia)
  14. Wikidata Georeferenced Andean Archaeological Monuments (621 sites across Peru, Bolivia, Colombia, Ecuador)
  15. Published Central Andean & Bolivian Altiplano Survey Atlas (Tiwanaku, Lake Titicaca, Cusco, Wari,
      Chavín, Mantaro, Cajamarca, Chachapoyas, Cochabamba, Potosí, Chuquisaca, Upano & Quito)

Aggregates onto scale-adaptive HydroBASINS Level 6 catchments (subdividing any basin > 25,000 km²),
applies macro-biome-stratified (Central Andean Highlands vs Lowland Amazonia/Brazil) Q75 + 2.0*IQR
taphonomic outlier shrinkage + hydrological B2 zero-hole imputation (adm2_coverage_ratio >= 0.72),
and emits:
  - 8 chronological Holocene period GeoJSONs (`01_...` through `08_...`)
  - 1 dedicated Terra Preta (ADE) anthropogenic soil GeoJSON (`09_terra_preta_ade_anthrosol.geojson`)
  - 1 composite `00_all_periods.geojson` + `config/sites_preta_geojson_metadata.json`
"""

import csv
import json
import math
import os
import pathlib
import re
import sys
import numpy as np
import openpyxl
from PIL import Image
from scipy.ndimage import binary_dilation
from scipy.spatial import cKDTree
import shapefile
from shapely.geometry import Point, shape

sys.stdout.reconfigure(encoding="utf-8")

W, H = 4320, 2160
DOMAIN_DIR = pathlib.Path(__file__).resolve().parent
PRETA_DIR = DOMAIN_DIR.parents[1]
SVEA_ROOT = PRETA_DIR.parents[3]
RAW_DIR = DOMAIN_DIR / "raw_sources"
ANDEAN_DIR = RAW_DIR / "andean"
GEOJSON_DIR = DOMAIN_DIR / "geojson"
CFG_DIR = DOMAIN_DIR / "config"
GEOJSON_DIR.mkdir(parents=True, exist_ok=True)
CFG_DIR.mkdir(parents=True, exist_ok=True)

DOMAIN_MASK_PNG = CFG_DIR / "preta_domain_mask.png"
HYBAS_L6_SHP = PRETA_DIR / "_shared/_gis_cache/hydrobasins/hybas_sa_lev06_v1c.shp"
C14_CSV = SVEA_ROOT / "histmap/1.data_raw/population_c14bazAAR/c14_cleaned_dedup.csv"
LAND_AREA_PNG = SVEA_ROOT / "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png"
ELEV_PNG = SVEA_ROOT / "histmap/1.data_raw/metadata_HYDE/general_rasters/elev_5m_m.png"

PERIODS = [
  ("01_palaeoindian_early_holocene", -13000, -6000),
  ("02_middle_holocene_archaic_sambaqui", -6000, -3000),
  ("03_late_archaic_early_formative", -3000, -1000),
  ("04_formative_early_ade", -1000, 0),
  ("05_classic_amazonian_ade_expansion", 0, 500),
  ("06_polychrome_mound_chiefdoms", 500, 1000),
  ("07_late_precolumbian_chiefdoms", 1000, 1400),
  ("08_contact_horizon", 1400, 1542),
]

# Empirical Holocene Terra Preta (ADE) formation weight curve (Neves 2004; Arroyo-Kalin 2010; Maezumi 2018; de Souza 2018)
ADE_HORIZON_WEIGHTS = {
  "01_palaeoindian_early_holocene": 0.0,
  "02_middle_holocene_archaic_sambaqui": 0.06,
  "03_late_archaic_early_formative": 0.12,
  "04_formative_early_ade": 0.28,
  "05_classic_amazonian_ade_expansion": 0.55,
  "06_polychrome_mound_chiefdoms": 0.85,
  "07_late_precolumbian_chiefdoms": 1.00,
  "08_contact_horizon": 0.95,
}

# Central Andean chronological curves (Formative Chavín/Chiripa -> Early Intermediate -> Middle Horizon Wari/Tiwanaku -> LIP -> Inca)
ANDEAN_GENERAL_WEIGHTS = {
  "01_palaeoindian_early_holocene": 0.05,
  "02_middle_holocene_archaic_sambaqui": 0.12,
  "03_late_archaic_early_formative": 0.24,
  "04_formative_early_ade": 0.48,
  "05_classic_amazonian_ade_expansion": 0.68,
  "06_polychrome_mound_chiefdoms": 0.88,
  "07_late_precolumbian_chiefdoms": 0.96,
  "08_contact_horizon": 1.00,
}

ANDEAN_INCA_QHAPAQ_WEIGHTS = {
  "01_palaeoindian_early_holocene": 0.0,
  "02_middle_holocene_archaic_sambaqui": 0.0,
  "03_late_archaic_early_formative": 0.04,
  "04_formative_early_ade": 0.12,
  "05_classic_amazonian_ade_expansion": 0.22,
  "06_polychrome_mound_chiefdoms": 0.45,
  "07_late_precolumbian_chiefdoms": 0.72,
  "08_contact_horizon": 1.00,
}

ANDEAN_MIDDLE_HORIZON_WEIGHTS = {
  "01_palaeoindian_early_holocene": 0.02,
  "02_middle_holocene_archaic_sambaqui": 0.08,
  "03_late_archaic_early_formative": 0.28,
  "04_formative_early_ade": 0.60,
  "05_classic_amazonian_ade_expansion": 0.88,
  "06_polychrome_mound_chiefdoms": 1.00,
  "07_late_precolumbian_chiefdoms": 0.78,
  "08_contact_horizon": 0.82,
}

ANDEAN_FORMATIVE_WEIGHTS = {
  "01_palaeoindian_early_holocene": 0.10,
  "02_middle_holocene_archaic_sambaqui": 0.35,
  "03_late_archaic_early_formative": 0.85,
  "04_formative_early_ade": 1.00,
  "05_classic_amazonian_ade_expansion": 0.70,
  "06_polychrome_mound_chiefdoms": 0.55,
  "07_late_precolumbian_chiefdoms": 0.50,
  "08_contact_horizon": 0.48,
}

# Published Amazonian Dark Earth (Terra Preta) & earthwork hubs (McMichael 2014; Neves 2004; Clement 2015; Palace 2017; Lombardo 2020; Prümers 2022)
CANONICAL_TERRA_PRETA_HUBS = [
  # Lower Amazon, Marajó, Santarém, Tapajós, Trombetas, Xingu
  (-2.433, -54.717, 5.0), (-2.421, -54.742, 4.5), (-2.503, -54.956, 3.8), (-2.636, -54.938, 4.0),
  (-2.443, -54.280, 3.5), (-1.918, -55.518, 4.0), (-1.766, -55.866, 3.5), (-2.186, -56.713, 3.5),
  (-2.628, -56.736, 4.2), (-2.152, -56.092, 3.8), (-1.942, -54.738, 3.6), (-1.523, -52.582, 3.2),
  (-1.405, -51.640, 3.5), (-1.737, -51.456, 3.4), (-0.667, -49.667, 4.5), (-0.717, -49.550, 3.8),
  (-3.203, -52.206, 3.5), (-12.558, -53.111, 4.5), (-12.480, -53.210, 4.0), (-12.610, -53.050, 3.6),
  (-4.276, -55.984, 3.5), (-3.766, -49.673, 3.2), (-5.369, -49.118, 3.0), (-2.230, -49.500, 3.0),
  (-1.456, -48.504, 3.2), (-0.223, -51.454, 2.8), (-2.800, -55.100, 3.5), (-3.100, -55.300, 3.2),
  # Central Amazon, Encontro das Águas, Rio Negro, Solimões
  (-3.275, -60.207, 5.0), (-3.096, -60.352, 4.8), (-3.255, -60.151, 4.2), (-3.210, -60.320, 4.0),
  (-3.250, -60.220, 4.2), (-3.130, -59.980, 4.5), (-3.143, -58.444, 4.4), (-3.300, -60.621, 4.2),
  (-3.354, -64.711, 4.2), (-4.085, -63.141, 3.8), (-0.975, -62.924, 3.5), (-0.130, -67.089, 3.2),
  (-3.465, -62.216, 3.6), (-3.900, -64.000, 3.4), (-3.500, -66.100, 3.5), (-3.150, -67.950, 3.6),
  (-4.215, -69.941, 4.0), (-2.850, -58.200, 3.6), (-2.600, -57.700, 3.4), (-1.950, -61.400, 3.2),
  # Madeira, Guaporé, Rondônia, Purus, Juruá, Acre
  (-8.862, -64.063, 4.8), (-12.533, -63.183, 3.8), (-4.388, -59.594, 4.0), (-5.810, -61.300, 3.8),
  (-7.506, -63.021, 3.8), (-9.874, -67.530, 4.2), (-9.962, -67.495, 3.8), (-9.815, -67.152, 3.6),
  (-7.259, -64.798, 3.4), (-7.631, -72.670, 3.2), (-10.900, -61.950, 3.4), (-10.450, -65.340, 3.5),
  # Llanos de Moxos, Beni, Mamoré, Casarabe (Bolivia)
  (-14.841, -64.598, 5.0), (-14.798, -64.678, 4.5), (-14.950, -64.717, 4.0), (-14.883, -64.733, 3.8),
  (-13.980, -65.180, 3.5), (-13.270, -63.700, 4.0), (-14.996, -65.640, 4.0), (-11.007, -66.063, 3.5),
  # Upper Amazon (Colombia, Ecuador, Peru)
  (-0.683, -72.100, 3.8), (-0.600, -72.383, 3.8), (-3.749, -73.254, 4.0), (-3.829, -73.318, 3.6),
  (-8.500, -74.550, 3.5), (-8.350, -74.580, 3.5), (-2.017, -78.117, 4.5), (-0.950, -75.400, 3.4),
  # Guianas (ADE & anthropogenic raised-field dark soils)
  (5.883, -56.667, 3.6), (5.833, -55.283, 3.2), (5.160, -52.650, 3.4), (4.867, -52.350, 3.5),
  (5.378, -52.960, 3.2), (3.740, -53.980, 2.8), (1.833, -58.550, 2.8), (4.367, -57.950, 3.0),
]

# Published Central Andean & Bolivian Altiplano Monumental Survey Atlas (Stanish 2003; Janusek 2008; Bauer 2004;
# Isbell & McEwan 1991; D'Altroy 2015; Capriles et al. 2023; Church 1996; Burger 1992; Albarracin-Jordan 1996)
# Format: (lat, lon, weight, curve_tag) — captures full-basin systematic survey density in Bolivia/Peru/Ecuador/Colombia
CANONICAL_ANDEAN_SURVEY_HUBS = [
  # --- Lake Titicaca Basin & Bolivian Altiplano (Tiwanaku, Katari, Taraco, Isla del Sol, Desaguadero, Oruro, Potosí) ---
  (-16.5547, -68.6736, 42.0, "mh"),   # Tiwanaku urban capital & Akapana/Kalasasaya
  (-16.4333, -68.6833, 28.0, "mh"),   # Lukurmata & Katari Valley raised fields (Kolata 1996)
  (-16.4400, -68.8380, 22.0, "form"), # Chiripa & Taraco Peninsula Formative-Tiwanaku core (Hastorf 1999)
  (-16.4550, -68.8100, 18.0, "form"), # Kala Uyuni & Taraco survey cluster
  (-16.7667, -68.8333, 24.0, "mh"),   # Khonkho Wankane & Upper Desaguadero (Janusek 2008)
  (-16.5833, -68.5667, 18.0, "mh"),   # Lower Tiwanaku Valley survey (Albarracin-Jordan 1996)
  (-16.5200, -68.3800, 16.0, "mh"),   # Upper Tiwanaku / Tambillo / Laja survey
  (-16.0170, -69.1780, 22.0, "gen"),  # Isla del Sol & Copacabana Peninsula (Bauer & Stanish 2001)
  (-16.1660, -69.0860, 20.0, "gen"),  # Copacabana & Horca del Inca
  (-16.0400, -69.0700, 16.0, "gen"),  # Isla de la Luna / Coati
  (-16.0330, -68.6830, 18.0, "gen"),  # Achacachi / Omasuyos Lake Titicaca shore
  (-15.7330, -68.9330, 16.0, "gen"),  # Carabuco / Escoma / Northern Bolivian Titicaca shore
  (-15.5500, -69.1100, 18.0, "gen"),  # Puerto Acosta / Huaycho / Mocomoco
  (-16.5660, -69.0380, 18.0, "gen"),  # Desaguadero / Guaqui
  (-16.7000, -68.8200, 16.0, "gen"),  # Jesús de Machaca / Pacajes
  (-17.1500, -68.4500, 15.0, "gen"),  # Caquiaviri / Pacajes Aymara señorío capital
  (-17.2400, -67.9200, 18.0, "gen"),  # Sica Sica / Ayo Ayo / Patacamaya Altiplano corridor
  (-17.4700, -67.7500, 16.0, "gen"),  # Caracollo / Upper Desaguadero
  (-17.8333, -67.0167, 24.0, "form"), # Paria (Inca provincial capital) & Wankarani Formative mounds (McAndrews 2005)
  (-17.9647, -67.1064, 20.0, "form"), # Oruro / Uru-Chipaya / La Joya Wankarani cluster
  (-18.3800, -66.9400, 16.0, "gen"),  # Poopó / Pazña / Lake Poopó shore
  (-18.9020, -66.7700, 18.0, "gen"),  # Challapata / Quillacas / Aullagas (Carangas-Quillacas señorío)
  (-19.2500, -66.9300, 14.0, "gen"),  # Sevaruyo / Salinas de Garci Mendoza
  (-17.7500, -68.3800, 14.0, "gen"),  # Corque / Curahuara de Carangas / Chullpas of Lauca
  (-18.1300, -68.9700, 12.0, "gen"),  # Sajama / Turco / Carangas chullpa towers
  (-19.5836, -65.7531, 24.0, "gen"),  # Potosí / Cantumarca & Pre-Hispanic metallurgy
  (-19.7760, -65.8300, 26.0, "inca"), # Porco (Inca imperial silver mine & Qhapaq Ñan hub)
  (-18.4500, -66.4300, 18.0, "gen"),  # Sacaca / Chayanta / Charcas confederation core
  (-18.8800, -66.1500, 16.0, "gen"),  # Macha / Pocoata / Northern Potosí señoríos
  (-19.5200, -65.4500, 16.0, "gen"),  # Chaqui / Betanzos / Puna
  (-20.4600, -65.6400, 14.0, "gen"),  # Cotagaita / Chichas señorío
  (-21.4400, -65.7200, 15.0, "gen"),  # Tupiza / Southern Chichas
  (-20.4700, -66.8200, 10.0, "gen"),  # Uyuni / Lípez altiplano pastoral sites
  # --- Peruvian Lake Titicaca Basin (Puno, Juliaca, Pukara, Chucuito, Juli, Ilave, Azángaro) ---
  (-15.0480, -70.3710, 26.0, "form"), # Pukara Formative ceremonial urban centre
  (-15.7210, -70.1590, 24.0, "gen"),  # Sillustani / Hatuncolla (Qolla capital)
  (-15.8930, -69.8890, 26.0, "gen"),  # Chucuito / Inka Uyu (Lupaqa capital)
  (-16.0830, -69.6330, 22.0, "gen"),  # Ilave / Cutimbo Lupaqa survey (Stanish 1997)
  (-16.2130, -69.4600, 24.0, "gen"),  # Juli / Pomata / Zepita Lupaqa core
  (-15.4900, -70.1300, 20.0, "gen"),  # Juliaca / Taraco-Puno raised fields
  (-14.9100, -70.1900, 18.0, "gen"),  # Azángaro / Asillo / Ayaviri Qolla heartland
  (-15.2000, -69.7500, 18.0, "gen"),  # Huancané / Moho / Northern Titicaca shore
  # --- Bolivian Eastern Cordillera & Inter-Andean Valleys (La Paz, Iskanwaya, Cochabamba, Chuquisaca, Samaipata, Tarija) ---
  (-16.5000, -68.1500, 28.0, "gen"),  # Chuquiabo / La Paz Valley (Tiwanaku-Inca core)
  (-16.5800, -68.0800, 18.0, "gen"),  # Mecapaca / Palca / Río La Paz terraced valley
  (-15.4375, -68.5322, 24.0, "gen"),  # Iskanwaya (Mollo Culture stone citadel, Larecaja)
  (-15.1700, -69.0000, 18.0, "gen"),  # Charazani / Kallawaya terraced highland valleys
  (-16.1900, -67.7300, 16.0, "inca"), # Coroico / Chulumani / Inca Yungas coca terraces
  (-17.3935, -66.1570, 32.0, "mh"),   # Cochabamba Valley (Sierra Mokho, Quillacollo, Cotapachi Inca qollqas!)
  (-17.4200, -66.2800, 24.0, "inca"), # Quillacollo / Cotapachi 2,400+ Inca state storehouses
  (-17.5900, -65.9100, 20.0, "mh"),   # Cliza / Tarata / Punata (Upper Cochabamba Valley)
  (-17.6130, -65.4170, 26.0, "inca"), # Incallajta (Pocona imperial Inca fortress-city)
  (-17.9400, -65.3400, 18.0, "mh"),   # Mizque / Omereque (Tiwanaku-derived valleys)
  (-18.1790, -63.8190, 24.0, "inca"), # El Fuerte de Samaipata (eastern Andean imperial sanctuary)
  (-19.0196, -65.2619, 26.0, "gen"),  # Choquechaca / Chuquisaca / Sucre (Yampara capital)
  (-19.1800, -64.9100, 18.0, "gen"),  # Tarabuco / Presto / Yampara valleys
  (-20.6400, -65.2100, 14.0, "gen"),  # Camargo / Cinti valley
  (-21.5350, -64.7300, 18.0, "gen"),  # Tarija / Tolomosa / San Lorenzo valley settlements
  # --- Peruvian Central & Southern Sierra (Cusco, Sacred Valley, Apurímac, Ayacucho/Wari, Mantaro, Junín, Huánuco, Chavín, Cajamarca, Chachapoyas) ---
  (-13.5160, -71.9780, 50.0, "inca"), # Cusco / Qorikancha / Sacsayhuamán (Inca imperial capital)
  (-13.6140, -71.7160, 34.0, "mh"),   # Pikillacta & Chokepukio (Wari provincial metropolis, Lucre Basin)
  (-13.5700, -71.7830, 22.0, "inca"), # Tipón / Oropesa / Cusco Valley survey (Bauer 2004)
  (-13.4130, -71.8440, 28.0, "inca"), # Pisac / Sacred Valley terraced urban centre
  (-13.2580, -72.2630, 30.0, "inca"), # Ollantaytambo / Urubamba imperial estate
  (-13.3900, -72.0470, 22.0, "inca"), # Chinchero / Moray / Maras agricultural terraces
  (-13.1631, -72.5450, 26.0, "inca"), # Machu Picchu & Inca Trail llactas
  (-13.3930, -72.8740, 22.0, "inca"), # Choquequirao / Apurímac gorge citadel
  (-13.1050, -72.9310, 20.0, "inca"), # Vitcos / Vilcabamba / Espíritu Pampa
  (-14.1750, -71.3700, 24.0, "inca"), # Raqchi (Temple of Wiracocha & qollqas) / Sicuani
  (-13.3200, -71.5900, 18.0, "inca"), # Paucartambo / Eastern Cusco sierra-selva gateway
  (-13.6340, -72.8810, 22.0, "gen"),  # Abancay / Saywite / Curamba
  (-13.6560, -73.3870, 26.0, "gen"),  # Andahuaylas / Sondor (Chanka confederation heartland)
  (-13.0611, -74.2061, 46.0, "mh"),   # Wari imperial capital & Conchopata (Ayacucho, Isbell 1991)
  (-13.1630, -74.2240, 28.0, "mh"),   # Ayacucho / Quinua / Huamanga Basin survey
  (-13.6530, -73.9540, 26.0, "inca"), # Vilcashuamán (Inca imperial administrative centre)
  (-12.7870, -74.9720, 20.0, "gen"),  # Huancavelica / Castrovirreyna / Uchkus-Inkañan
  (-11.7750, -75.4970, 34.0, "gen"),  # Hatun Xauxa / Tunanmarca / Yanamarca (Upper Mantaro Wanka-Inca core, D'Altroy 1992)
  (-12.0651, -75.2049, 32.0, "gen"),  # Huancayo / Wariwillka / Mantaro Valley dense agrarian belt
  (-11.4190, -75.6900, 22.0, "inca"), # Tarma / Tarmatambo (Inca provincial capital)
  (-11.1580, -76.0000, 22.0, "inca"), # Pumpu / Lake Junín imperial tambo & pastoral plateau
  (-9.8744, -76.8147, 32.0, "inca"),  # Huánuco Pampa (Inca planned metropolis, Morris & Thompson 1985)
  (-9.9310, -76.2790, 26.0, "form"),  # Kotosh / Huánuco Valley (Mito Formative & Chupaychu)
  (-9.4100, -76.6200, 20.0, "gen"),   # Tantamayo / Piruro / Garu (Upper Marañón Yarowilca towers)
  (-9.5936, -77.1775, 34.0, "form"),  # Chavín de Huántar (Pan-Andean Formative ceremonial metropolis, Burger 1992)
  (-9.2000, -77.3100, 22.0, "gen"),   # Yayno / Pomabamba / Conchucos Sierra
  (-9.5280, -77.5280, 26.0, "gen"),   # Huaraz / Honcopampa / Callejón de Huaylas (Recuay-Wari-Inca)
  (-7.8100, -78.0480, 30.0, "mh"),    # Marcahuamachuco & Wiracochapampa (Huamachuco stone metropolis)
  (-7.1617, -78.5128, 34.0, "gen"),   # Cajamarca / Cumbemayo / Layzón / Otuzco (Cajamarca-Inca capital)
  (-7.1270, -78.8440, 24.0, "form"),  # Kuntur Wasi (Formative gold/temple centre)
  (-6.3480, -79.0130, 22.0, "form"),  # Pacopampa / Chota / Northern Cajamarca Formative
  (-5.7080, -78.8070, 20.0, "form"),  # Jaén / Montegrande / Bagua (Marañón Formative-Bracamoros)
  (-6.4189, -77.9233, 34.0, "gen"),   # Kuélap (Chachapoya monumental walled citadel, Church 1996)
  (-6.2310, -77.8690, 24.0, "gen"),   # Chachapoyas / Yalape / Levanto / Cochabamba-Chachapoya
  (-6.5440, -77.8120, 22.0, "gen"),   # Revash / Leymebamba / Laguna de los Cóndores / Gran Vilaya
  (-7.7470, -77.2720, 24.0, "gen"),   # Gran Pajatén / Abiseo (Chachapoya cloud-forest complex)
  (-6.0340, -76.9720, 18.0, "gen"),   # Moyobamba / Rioja / Alto Mayo ceja de selva
  # --- Ecuadorian Andes & Amazonian Piedmont (Cuenca/Tomebamba, Ingapirca, Quito, Cochasquí, Upano, Quijos) ---
  (-2.8970, -79.0050, 28.0, "inca"),  # Tomebamba / Cuenca (Northern Inca co-capital & Cañari core)
  (-2.5480, -78.8750, 24.0, "inca"),  # Ingapirca (Cañari-Inca temple fortress)
  (-4.0000, -79.2050, 18.0, "gen"),   # Loja / Saraguro / Palta highlands
  (-4.6500, -79.1300, 18.0, "form"),  # Santa Ana-La Florida / Palanda (Mayo-Chinchipe 5300 BP cacao/Formative)
  (-2.0167, -78.1167, 28.0, "form"),  # Upano Valley / Sangay / Kilamope garden-city corridor (Rostain 2024)
  (-1.6700, -78.6500, 22.0, "gen"),   # Riobamba / Puruhá highlands
  (-1.2490, -78.6170, 20.0, "gen"),   # Ambato / Latacunga / Panzaleo
  (-0.1807, -78.4678, 30.0, "gen"),   # Quito / Rumipamba / La Florida (Quitu-Cara-Inca capital)
  (0.0550, -78.3050, 24.0, "gen"),    # Cochasquí / Zuleta / Caranqui monumental tola pyramids
  (-0.4600, -77.8900, 18.0, "gen"),   # Quijos / Baeza / Cosanga eastern piedmont
  # --- Colombian Andes & Piedmont (San Agustín, Tierradentro, Pasto, Muisca/Altiplano Cundiboyacense) ---
  (1.8880, -76.2940, 28.0, "mh"),     # San Agustín monumental funerary-agrarian chiefdoms
  (2.5730, -76.0380, 24.0, "mh"),     # Tierradentro hypogea & Páez cordillera
  (1.2130, -77.2810, 22.0, "gen"),    # Pasto / Ipiales / Quillacinga-Pasto highlands
  (1.1530, -76.6520, 16.0, "gen"),    # Sibundoy / Mocoa Andean-Amazonian corridor
  (4.7110, -74.0720, 32.0, "gen"),    # Bacatá / Bogotá / Sabana Muisca core
  (5.5350, -73.3680, 28.0, "gen"),    # Hunza / Tunja / Sogamoso Muisca confederation
]

CARIBBEAN_COL_DEPTS = {
  "LA GUAJIRA", "MAGDALENA", "ATLANTICO", "ATLÁNTICO", "BOLIVAR", "BOLÍVAR",
  "CESAR", "SUCRE", "CORDOBA", "CÓRDOBA", "SAN ANDRES", "SAN ANDRÉS"
}


def load_domain_frontier_and_elev():
  """Loads 4320x2160 PRETA domestic domain mask, 400 km (~48 px) South America frontier mask, and elevation."""
  arr = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  dom = (arr[:, :, 3] > 0) & (arr[:, :, :3].sum(axis=2) > 0)
  la_raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  la_u32 = la_raw.reshape(-1, 4).copy().view(">u4").reshape((H, W))
  land = la_u32 > 0
  # 48 px (~400 km) dilation captures the entire Peruvian, Bolivian, Ecuadorian & Colombian Andean Cordillera!
  dilated = binary_dilation(dom, iterations=48) & land
  frontier = dilated & (~dom)

  elev_raw = np.asarray(Image.open(ELEV_PNG).convert("RGBA"), dtype=np.uint8)
  elev = elev_raw.reshape(-1, 4).copy().view(">f4").reshape((H, W))
  elev = np.where(np.isfinite(elev) & (elev > 0), elev, 0.0)
  return dom, frontier, land, elev


def build_catchments(arg0_dom_mask, arg1_front_mask, arg2_elev):
  """Builds scale-adaptive HydroBASINS Level 6 catchments (subdividing > 25,000 km²) inside PRETA + 400 km belt."""
  sf = shapefile.Reader(str(HYBAS_L6_SHP))
  flds = [f[0] for f in sf.fields[1:]]
  catchments = []

  for i, rec in enumerate(sf.records()):
    d = dict(zip(flds, rec))
    geom = shape(sf.shape(i).__geo_interface__)
    if geom.is_empty:
      continue
    area_km2 = float(d.get("SUB_AREA") or 5000.0)
    c = geom.representative_point()
    lat, lon = float(c.y), float(c.x)
    r = min(H - 1, max(0, int((90.0 - lat) * 12.0)))
    col = min(W - 1, max(0, int((lon + 180.0) * 12.0)))
    is_dom = bool(arg0_dom_mask[r, col])
    is_front = (not is_dom) and bool(arg1_front_mask[r, col])
    if not is_dom and not is_front:
      bb = geom.bounds
      c_lat, c_lon = 0.5 * (bb[1] + bb[3]), 0.5 * (bb[0] + bb[2])
      rr = min(H - 1, max(0, int((90.0 - c_lat) * 12.0)))
      cc = min(W - 1, max(0, int((c_lon + 180.0) * 12.0)))
      is_dom = bool(arg0_dom_mask[rr, cc])
      is_front = (not is_dom) and bool(arg1_front_mask[rr, cc])
      if not is_dom and not is_front:
        continue

    hid = str(d["HYBAS_ID"])
    main_bas = str(d["MAIN_BAS"])

    def sample_elev(sy, sx):
      sr = min(H - 1, max(0, int((90.0 - sy) * 12.0)))
      sc = min(W - 1, max(0, int((sx + 180.0) * 12.0)))
      return float(arg2_elev[max(0, sr - 1):min(H, sr + 2), max(0, sc - 1):min(W, sc + 2)].mean())

    if area_km2 > 25000.0:
      n_split = min(6, int(math.ceil(area_km2 / 18000.0)))
      bb = geom.bounds
      nx = int(math.ceil(math.sqrt(n_split)))
      ny = int(math.ceil(n_split / float(nx)))
      dx = (bb[2] - bb[0]) / nx
      dy = (bb[3] - bb[1]) / ny
      sub_pts = []
      for ix in range(nx):
        for iy in range(ny):
          sx = bb[0] + (ix + 0.5) * dx
          sy = bb[1] + (iy + 0.5) * dy
          if geom.contains(Point(sx, sy)):
            sub_pts.append((sy, sx))
      if not sub_pts:
        sub_pts = [(lat, lon)]
      sub_a = area_km2 / len(sub_pts)
      for s_idx, (sy, sx) in enumerate(sub_pts):
        sr = min(H - 1, max(0, int((90.0 - sy) * 12.0)))
        sc = min(W - 1, max(0, int((sx + 180.0) * 12.0)))
        s_dom = bool(arg0_dom_mask[sr, sc])
        ev = sample_elev(sy, sx)
        is_and = (ev >= 1200.0 and sx <= -63.0 and -24.0 <= sy <= 9.0)
        catchments.append({
          "region_id": f"hb6_{hid}_{s_idx}",
          "main_bas": main_bas,
          "lat": sy, "lon": sx,
          "elev_m": ev,
          "is_andean": is_and,
          "is_amazon_tp": (not is_and) and (sy >= -18.0) and (sx <= -45.5),
          "area_km2": max(400.0, sub_a),
          "is_frontier_buffer": not s_dom,
          "periods": {pk: 0.0 for pk, _, _ in PERIODS},
          "terra_preta": 0.0,
          "raw_site_count": 0,
          "ade_raw_count": 0,
          "has_documented_settlement": False,
        })
    else:
      ev = sample_elev(lat, lon)
      is_and = (ev >= 1200.0 and lon <= -63.0 and -24.0 <= lat <= 9.0)
      catchments.append({
        "region_id": f"hb6_{hid}",
        "main_bas": main_bas,
        "lat": lat, "lon": lon,
        "elev_m": ev,
        "is_andean": is_and,
        "is_amazon_tp": (not is_and) and (lat >= -18.0) and (lon <= -45.5),
        "area_km2": max(100.0, area_km2),
        "is_frontier_buffer": not is_dom,
        "periods": {pk: 0.0 for pk, _, _ in PERIODS},
        "terra_preta": 0.0,
        "raw_site_count": 0,
        "ade_raw_count": 0,
        "has_documented_settlement": False,
      })

  # Merge tiny HydroBASINS river-confluence sliver polygons (< 2,200 km²) into their nearest same-biome
  # catchment >= 2,200 km² so sliver polygons NEVER create fake 300-470 sites/1000km² density singularities!
  major_cs = [c for c in catchments if c["area_km2"] >= 2200.0]
  sliver_cs = [c for c in catchments if c["area_km2"] < 2200.0]
  if major_cs and sliver_cs:
    m_pts = np.asarray([
      [math.cos(math.radians(c["lat"])) * math.cos(math.radians(c["lon"])),
       math.cos(math.radians(c["lat"])) * math.sin(math.radians(c["lon"])),
       math.sin(math.radians(c["lat"]))]
      for c in major_cs
    ])
    mtree = cKDTree(m_pts)
    for sc in sliver_cs:
      lr, lor = math.radians(sc["lat"]), math.radians(sc["lon"])
      _, idxs = mtree.query([math.cos(lr) * math.cos(lor), math.cos(lr) * math.sin(lor), math.sin(lr)], k=min(8, len(major_cs)))
      chosen = None
      for j in (idxs if hasattr(idxs, "__iter__") else [idxs]):
        if major_cs[int(j)]["is_andean"] == sc["is_andean"]:
          chosen = major_cs[int(j)]
          break
      if chosen is None:
        chosen = major_cs[int(idxs[0] if hasattr(idxs, "__iter__") else idxs)]
      chosen["area_km2"] += sc["area_km2"]
    catchments = major_cs

  print(f"Built {len(catchments):,} sliver-merged HydroBASINS L6 catchments (folded {len(sliver_cs):,} slivers <2.200 km²; "
        f"domestic={sum(1 for c in catchments if not c['is_frontier_buffer']):,}, "
        f"frontier_400km={sum(1 for c in catchments if c['is_frontier_buffer']):,}, "
        f"andean_highland={sum(1 for c in catchments if c['is_andean']):,})")
  return catchments


def assign_dated_year(arg0_yr):
  """Maps a calibrated calendar year to its chronological horizon key."""
  for pk, y0, y1 in PERIODS:
    if y0 <= arg0_yr <= y1:
      return pk
  if arg0_yr < -13000:
    return PERIODS[0][0]
  return PERIODS[-1][0]


def classify_iphan_typology(arg0_text):
  """Classifies undated Brazilian IPHAN sites into (weight, is_ade, horizon_distribution)."""
  t = arg0_text.lower()
  if any(k in t for k in ["terra preta", "tpi", "solo escuro", "solo antr", "dark earth"]):
    return 14.0, True, ADE_HORIZON_WEIGHTS
  if any(k in t for k in ["geoglifo", "aterro", "marajo", "santar", "konduri", "xingu"]):
    return 8.5, False, {
      "01_palaeoindian_early_holocene": 0.0, "02_middle_holocene_archaic_sambaqui": 0.02,
      "03_late_archaic_early_formative": 0.06, "04_formative_early_ade": 0.25,
      "05_classic_amazonian_ade_expansion": 0.65, "06_polychrome_mound_chiefdoms": 0.95,
      "07_late_precolumbian_chiefdoms": 1.00, "08_contact_horizon": 0.85,
    }
  if any(k in t for k in ["sambaqui", "concheiro", "cerrito"]):
    return 2.5, False, {
      "01_palaeoindian_early_holocene": 0.05, "02_middle_holocene_archaic_sambaqui": 0.80,
      "03_late_archaic_early_formative": 1.00, "04_formative_early_ade": 0.65,
      "05_classic_amazonian_ade_expansion": 0.30, "06_polychrome_mound_chiefdoms": 0.15,
      "07_late_precolumbian_chiefdoms": 0.10, "08_contact_horizon": 0.05,
    }
  if any(k in t for k in ["casa subterr", "estrutura subterr", "taquara", "itarar", "anelar"]):
    return 2.5, False, {
      "01_palaeoindian_early_holocene": 0.0, "02_middle_holocene_archaic_sambaqui": 0.0,
      "03_late_archaic_early_formative": 0.05, "04_formative_early_ade": 0.15,
      "05_classic_amazonian_ade_expansion": 0.50, "06_polychrome_mound_chiefdoms": 0.90,
      "07_late_precolumbian_chiefdoms": 1.00, "08_contact_horizon": 0.90,
    }
  if any(k in t for k in ["cerâm", "ceram", "tupi", "guarani", "aratu", "aldeia", "habita", "urn", "vasilh"]):
    return 1.6, False, {
      "01_palaeoindian_early_holocene": 0.0, "02_middle_holocene_archaic_sambaqui": 0.04,
      "03_late_archaic_early_formative": 0.12, "04_formative_early_ade": 0.30,
      "05_classic_amazonian_ade_expansion": 0.55, "06_polychrome_mound_chiefdoms": 0.85,
      "07_late_precolumbian_chiefdoms": 1.00, "08_contact_horizon": 0.95,
    }
  if any(k in t for k in ["lític", "litic", "abrigo", "gruta", "caverna", "lascad", "ponta"]):
    return 0.8, False, {
      "01_palaeoindian_early_holocene": 0.65, "02_middle_holocene_archaic_sambaqui": 1.00,
      "03_late_archaic_early_formative": 0.80, "04_formative_early_ade": 0.45,
      "05_classic_amazonian_ade_expansion": 0.25, "06_polychrome_mound_chiefdoms": 0.15,
      "07_late_precolumbian_chiefdoms": 0.10, "08_contact_horizon": 0.08,
    }
  if any(k in t for k in ["rupestre", "gravura", "pintura", "petr"]):
    return 0.5, False, {
      "01_palaeoindian_early_holocene": 0.45, "02_middle_holocene_archaic_sambaqui": 0.85,
      "03_late_archaic_early_formative": 0.90, "04_formative_early_ade": 0.50,
      "05_classic_amazonian_ade_expansion": 0.30, "06_polychrome_mound_chiefdoms": 0.20,
      "07_late_precolumbian_chiefdoms": 0.15, "08_contact_horizon": 0.10,
    }
  if any(k in t for k in ["históric", "igreja", "engenho", "ferrovia", "usina", "fortaleza", "fazenda histó"]):
    return 0.0, False, {}
  return 0.9, False, {
    "01_palaeoindian_early_holocene": 0.10, "02_middle_holocene_archaic_sambaqui": 0.25,
    "03_late_archaic_early_formative": 0.35, "04_formative_early_ade": 0.50,
    "05_classic_amazonian_ade_expansion": 0.65, "06_polychrome_mound_chiefdoms": 0.80,
    "07_late_precolumbian_chiefdoms": 0.90, "08_contact_horizon": 0.85,
  }


def classify_sigda_monument(arg0_name, arg1_cls):
  """Classifies Peru Ministry of Culture SIGDA pre-Hispanic monuments into (weight, horizon_dist)."""
  t = (str(arg0_name or "") + " " + str(arg1_cls or "")).lower()
  if any(k in t for k in ["zona arqueológica monumental", "complejo arqueol", "ciudadela", "llacta", "centro urbano", "centro ceremonial", "fortaleza"]):
    return 4.5, ANDEAN_GENERAL_WEIGHTS
  if any(k in t for k in ["inca", "inka", "tambo", "qollqa", "colca", "ushnu", "qhapaq", "camino"]):
    return 3.0, ANDEAN_INCA_QHAPAQ_WEIGHTS
  if any(k in t for k in ["wari", "huari", "tiwanaku", "tiahuanaco", "pikillacta"]):
    return 3.6, ANDEAN_MIDDLE_HORIZON_WEIGHTS
  if any(k in t for k in ["chavín", "chavin", "kotosh", "formati", "kuntur", "pacopampa", "pukara", "conchal"]):
    return 3.2, ANDEAN_FORMATIVE_WEIGHTS
  if any(k in t for k in ["zona arqueol", "paisaje cultural", "paisaje arqueol", "huaca", "pirámide", "piramide", "montículo", "monticulo", "andén", "andenes", "pueblo"]):
    return 3.0, ANDEAN_GENERAL_WEIGHTS
  if any(k in t for k in ["quilca", "petroglifo", "rupestre", "pintura", "abrigo", "cueva"]):
    return 1.2, {
      "01_palaeoindian_early_holocene": 0.50, "02_middle_holocene_archaic_sambaqui": 0.85,
      "03_late_archaic_early_formative": 0.90, "04_formative_early_ade": 0.65,
      "05_classic_amazonian_ade_expansion": 0.45, "06_polychrome_mound_chiefdoms": 0.35,
      "07_late_precolumbian_chiefdoms": 0.30, "08_contact_horizon": 0.25,
    }
  return 2.2, ANDEAN_GENERAL_WEIGHTS


def parse_icanh_coord(arg0_raw, arg1_is_lon, arg2_dept=""):
  """Decodes Colombia ICANH decimal-stripped variable-digit lat/lon strings accurately."""
  s = str(arg0_raw or "").strip().replace(",", ".")
  if not s:
    return None
  if "." in s:
    try:
      return float(s)
    except ValueError:
      return None
  neg = s.startswith("-")
  digits = re.sub(r"\D", "", s)
  if len(digits) < 3:
    return None
  if arg1_is_lon:
    v = float(f"{'-' if neg else ''}{digits[:2]}.{digits[2:]}")
    return -abs(v)
  if (not neg) and digits[:2] in ("10", "11", "12") and (arg2_dept.upper() in CARIBBEAN_COL_DEPTS or int(digits[:2]) in (10, 11, 12)):
    return float(f"{digits[:2]}.{digits[2:]}")
  return float(f"{'-' if neg else ''}{digits[:1]}.{digits[1:]}")


def main():
  print("Loading domain, 400 km South America frontier masks, and 5-arcminute DEM...")
  dom_mask, front_mask, _, elev_grid = load_domain_frontier_and_elev()
  catchments = build_catchments(dom_mask, front_mask, elev_grid)

  # Build 3D unit-sphere KDTree over catchments for exact geodesic snapping
  pts_3d = []
  for c in catchments:
    lr, lor = math.radians(c["lat"]), math.radians(c["lon"])
    pts_3d.append([math.cos(lr) * math.cos(lor), math.cos(lr) * math.sin(lor), math.sin(lr)])
  tree = cKDTree(np.asarray(pts_3d))

  def snap_catchment(lat, lon, max_km=160.0):
    lr, lor = math.radians(lat), math.radians(lon)
    dist_chord, idx = tree.query([math.cos(lr) * math.cos(lor), math.cos(lr) * math.sin(lor), math.sin(lr)])
    dist_km = 2.0 * 6371.0 * math.asin(min(1.0, dist_chord * 0.5))
    if dist_km <= max_km:
      return catchments[idx]
    return None

  source_counts = {}
  total_ade_records = 0

  # 1. IPHAN SICG:sitios (32,933 official Brazilian sites; spatially deduplicated at ~1.2 km to curb highway CRM bias)
  iphan_n, iphan_ade = 0, 0
  iphan_cells = {}
  with open(RAW_DIR / "iphan_sicg_sitios.csv", encoding="utf-8", errors="replace") as fh:
    for r in csv.DictReader(fh):
      m = re.search(r"POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)", str(r.get("ponto") or ""))
      if not m:
        continue
      la, lo = float(m.group(1)), float(m.group(2))
      if not (-34.0 <= la <= 6.0 and -74.5 <= lo <= -34.0):
        continue
      txt = str(r.get("identificacao_bem") or "") + " " + str(r.get("sintese_bem") or "")
      wt, is_ade, hdist = classify_iphan_typology(txt)
      if wt <= 0:
        continue
      # Deduplicate non-ADE modern CRM highway/dam clusters at ~1.2 km (comparable to SIGDA/ICANH); retain all explicit ADE sites
      if is_ade:
        ck = ("ade", round(la, 4), round(lo, 4))
      else:
        ck = ("crm", int(round(la * 90)), int(round(lo * 90)))
      prev = iphan_cells.get(ck)
      if prev is None or wt > prev[2]:
        iphan_cells[ck] = (la, lo, wt, is_ade, hdist)

  for la, lo, wt, is_ade, hdist in iphan_cells.values():
    c = snap_catchment(la, lo)
    if not c:
      continue
    c["raw_site_count"] += 1
    iphan_n += 1
    for pk, frac in hdist.items():
      if frac > 0:
        c["periods"][pk] += wt * frac
    if is_ade:
      c["terra_preta"] += wt
      c["ade_raw_count"] += 1
      iphan_ade += 1
      total_ade_records += 1
  source_counts["IPHAN_SICG_Brazil"] = iphan_n
  print(f"  [ 1] IPHAN SICG Brazil: {iphan_n:,} deduplicated pre-Columbian sites (explicit Terra Preta: {iphan_ade})")

  # 2. Walker et al. (2023, PeerJ) — 2,081 Amazonian sites (upweighted for ADE; earthworks deduplicated with Peripato!)
  walker_n, walker_ade = 0, 0
  ew_seen = set()
  with open(RAW_DIR / "walker_submit.csv", encoding="utf-8", errors="replace") as fh:
    for r in csv.DictReader(fh):
      try:
        lo, la = float(r["x"]), float(r["y"])
      except (TypeError, ValueError):
        continue
      c = snap_catchment(la, lo)
      if not c:
        continue
      tp = str(r.get("type") or "").strip().lower()
      c["raw_site_count"] += 1
      walker_n += 1
      if tp == "ade":
        wt = 13.5
        c["terra_preta"] += wt
        c["ade_raw_count"] += 1
        walker_ade += 1
        total_ade_records += 1
        for pk, frac in ADE_HORIZON_WEIGHTS.items():
          c["periods"][pk] += wt * frac
      elif tp == "earthwork":
        ek = (int(round(la * 70)), int(round(lo * 70)))
        if ek in ew_seen:
          continue
        ew_seen.add(ek)
        # Monumental Llanos de Moxos Casarabe lomas (lat < -12.8 in Beni/Moxos) carry denser permanent urban population
        # than seasonal ceremonial Acre/Pando ring-ditch geoglyphs (Schaan 2012; Watling et al. 2017; Prümers et al. 2022)
        wt = 5.5 if (la < -12.8 and -67.5 <= lo <= -62.0) else 2.6
        for pk, frac in [
          ("04_formative_early_ade", 0.30), ("05_classic_amazonian_ade_expansion", 0.70),
          ("06_polychrome_mound_chiefdoms", 1.00), ("07_late_precolumbian_chiefdoms", 0.95), ("08_contact_horizon", 0.75)
        ]:
          c["periods"][pk] += wt * frac
      else:
        wt = 2.2
        for pk, frac in ADE_HORIZON_WEIGHTS.items():
          c["periods"][pk] += wt * max(0.15, frac)
  source_counts["Walker_2023_Amazonia_ADE_Earthworks"] = walker_n
  print(f"  [ 2] Walker et al. (2023): {walker_n:,} sites (explicit ADE Terra Preta: {walker_ade})")

  # 3. Peripato et al. (2023, Science) — 961 Amazonian earthworks (spatially deduplicated against Walker at ~1.5 km!)
  peri_n = 0
  with open(RAW_DIR / "peripato_Earthworks.csv", encoding="utf-8", errors="replace") as fh:
    for r in csv.DictReader(fh):
      try:
        lo, la = float(r["Longitude"]), float(r["Latitude"])
      except (TypeError, ValueError):
        continue
      ek = (int(round(la * 70)), int(round(lo * 70)))
      if ek in ew_seen:
        continue
      ew_seen.add(ek)
      c = snap_catchment(la, lo)
      if not c:
        continue
      c["raw_site_count"] += 1
      peri_n += 1
      wt = 5.5 if (la < -12.8 and -67.5 <= lo <= -62.0) else 2.4
      for pk, frac in [
        ("04_formative_early_ade", 0.25), ("05_classic_amazonian_ade_expansion", 0.65),
        ("06_polychrome_mound_chiefdoms", 1.00), ("07_late_precolumbian_chiefdoms", 0.95), ("08_contact_horizon", 0.75)
      ]:
        c["periods"][pk] += wt * frac
  source_counts["Peripato_2023_Science_Earthworks"] = peri_n
  print(f"  [ 3] Peripato et al. (2023): {peri_n:,} deduplicated earthworks")

  # 4. de Souza rxpand_expand.csv — 2,794 dated South American sites
  rx_n, rx_ade = 0, 0
  with open(RAW_DIR / "rxpand_expand.csv", encoding="utf-8", errors="replace") as fh:
    for r in csv.DictReader(fh):
      try:
        la, lo = float(r["Latitude"]), float(r["Longitude"])
        c14 = float(r["C14Age"])
      except (TypeError, ValueError):
        continue
      c = snap_catchment(la, lo)
      if not c:
        continue
      yr = int(round(1950 - c14 * 1.05))
      pk = assign_dated_year(yr)
      desc = (str(r.get("Description") or "") + " " + str(r.get("Culture") or "") + " " + str(r.get("Site") or "")).lower()
      is_ade = any(k in desc for k in ["terra preta", "dark earth", "ade", "anthrosol", "anthropogenic soil", "black earth"])
      wt = 12.0 if is_ade else 2.0
      c["raw_site_count"] += 1
      c["periods"][pk] += wt
      rx_n += 1
      if is_ade:
        c["terra_preta"] += wt
        c["ade_raw_count"] += 1
        rx_ade += 1
        total_ade_records += 1
  source_counts["deSouza_rxpand_Radiocarbon"] = rx_n
  print(f"  [ 4] de Souza rxpand: {rx_n:,} dated records (explicit ADE: {rx_ade})")

  # 5. Sales et al. (2021) — 1,965 dated Andean-Amazonian sites
  sales_n = 0
  sales_p = RAW_DIR / "sales_2021_sdm/rachelsales14-Sales_2021_SDM-d752bd6/Data/ArcheologicalSites.csv"
  if sales_p.exists():
    with open(sales_p, encoding="utf-8", errors="replace") as fh:
      for r in csv.DictReader(fh):
        try:
          la, lo = float(r["Latitude"]), float(r["Longitude"])
          c14 = float(r["C14_date"])
        except (TypeError, ValueError):
          continue
        c = snap_catchment(la, lo)
        if not c:
          continue
        yr = int(round(1950 - c14 * 1.05))
        pk = assign_dated_year(yr)
        c["raw_site_count"] += 1
        c["periods"][pk] += 1.8
        sales_n += 1
  source_counts["Sales_2021_Andean_Amazon_C14"] = sales_n
  print(f"  [ 5] Sales et al. (2021): {sales_n:,} dated records")

  # 6. DOPAMICS (2023) French Guiana ADE & Ring-Ditch Pits
  dop_n = 0
  dop_p = RAW_DIR / "dopamics_Geoarchaeology_data_2023_10_13_clean.xlsx"
  if dop_p.exists():
    wb = openpyxl.load_workbook(dop_p, read_only=True)
    if "Pits" in wb.sheetnames:
      for row in wb["Pits"].iter_rows(min_row=2, values_only=True):
        if not row or len(row) < 5 or row[3] is None or row[4] is None:
          continue
        try:
          la, lo = float(row[3]), float(row[4])
        except (TypeError, ValueError):
          continue
        c = snap_catchment(la, lo)
        if not c:
          continue
        c["raw_site_count"] += 1
        c["terra_preta"] += 10.0
        c["ade_raw_count"] += 1
        dop_n += 1
        total_ade_records += 1
        for pk, frac in ADE_HORIZON_WEIGHTS.items():
          c["periods"][pk] += 10.0 * frac
  source_counts["DOPAMICS_2023_FrenchGuiana_ADE"] = dop_n
  print(f"  [ 6] DOPAMICS French Guiana ADEs: {dop_n:,} pits")

  # 7. SVEA c14_cleaned_dedup.csv
  c14_n = 0
  with open(C14_CSV, encoding="utf-8", errors="replace") as fh:
    for r in csv.DictReader(fh):
      try:
        la, lo = float(r.get("lat") or 999), float(r.get("lon") or 999)
        c14 = float(r.get("c14age") or 1200)
      except (TypeError, ValueError):
        continue
      if not (-38.0 <= la <= 12.0 and -82.0 <= lo <= -33.0):
        continue
      c = snap_catchment(la, lo)
      if not c:
        continue
      yr = int(round(1950 - c14 * 1.05))
      pk = assign_dated_year(yr)
      c["raw_site_count"] += 1
      c["periods"][pk] += 1.5
      c14_n += 1
  source_counts["SVEA_c14bazAAR_SouthAmerica"] = c14_n
  print(f"  [ 7] c14_cleaned_dedup South America: {c14_n:,} records")

  # 8. Canonical Terra Preta (ADE) Literature Atlas hubs (2.5x biomass multiplier for multi-hectare anthropogenic dark earths)
  for la, lo, wt in CANONICAL_TERRA_PRETA_HUBS:
    c = snap_catchment(la, lo)
    if not c:
      continue
    w_ade = wt * 2.5
    c["raw_site_count"] += 1
    c["terra_preta"] += w_ade
    c["ade_raw_count"] += 1
    c["has_documented_settlement"] = True
    total_ade_records += 1
    for pk, frac in ADE_HORIZON_WEIGHTS.items():
      c["periods"][pk] += w_ade * frac
  source_counts["Canonical_ADE_Literature_Atlas"] = len(CANONICAL_TERRA_PRETA_HUBS)
  print(f"  [ 8] Canonical Terra Preta Atlas: {len(CANONICAL_TERRA_PRETA_HUBS)} hubs (total ADE records: {total_ade_records:,})")

  # 9 & 10. Peru Ministry of Culture SIGDA — Delimited, Registered & Declared Pre-Hispanic Monuments (22,959 raw)
  # Spatially deduplicate across the 3 SIGDA monument layers at ~0.008 deg (~900 m) keeping highest weight!
  sigda_cells = {}
  sigda_raw_loaded = 0
  for fn in ["peru_sigda_maps_delimitado.csv", "peru_sigda_declarados.csv", "peru_sigda_registrado.csv"]:
    fp = ANDEAN_DIR / fn
    if not fp.exists():
      continue
    with open(fp, encoding="utf-8", errors="replace") as fh:
      for r in csv.DictReader(fh):
        try:
          la, lo = float(r["lat"]), float(r["lon"])
        except (TypeError, ValueError):
          continue
        if not (-19.0 <= la <= 0.5 and -82.0 <= lo <= -68.0):
          continue
        sigda_raw_loaded += 1
        wt, hdist = classify_sigda_monument(r.get("name"), r.get("classification"))
        cell_k = (int(round(la * 125)), int(round(lo * 125)))
        prev = sigda_cells.get(cell_k)
        if prev is None or wt > prev[2]:
          sigda_cells[cell_k] = (la, lo, wt, hdist)

  sigda_n = 0
  for la, lo, wt, hdist in sigda_cells.values():
    c = snap_catchment(la, lo)
    if not c:
      continue
    c["raw_site_count"] += 1
    c["has_documented_settlement"] = True
    sigda_n += 1
    for pk, frac in hdist.items():
      if frac > 0:
        c["periods"][pk] += wt * frac
  source_counts["Peru_SIGDA_PreHispanic_Monuments"] = sigda_n
  print(f"  [ 9] Peru Ministry of Culture SIGDA monuments: {sigda_n:,} deduplicated sites (from {sigda_raw_loaded:,} raw)")

  # 11. Peru Ministry of Culture SIGDA — Qhapaq Ñan Road & Tambo Nodes (5,379 raw)
  qn_n = 0
  qn_seen = set()
  qn_p = ANDEAN_DIR / "peru_sigda_qhapaq_nan.csv"
  if qn_p.exists():
    with open(qn_p, encoding="utf-8", errors="replace") as fh:
      for r in csv.DictReader(fh):
        try:
          la, lo = float(r["lat"]), float(r["lon"])
        except (TypeError, ValueError):
          continue
        if not (-19.0 <= la <= 0.5 and -82.0 <= lo <= -68.0):
          continue
        ck = (int(round(la * 50)), int(round(lo * 50)))
        if ck in qn_seen:
          continue
        qn_seen.add(ck)
        c = snap_catchment(la, lo)
        if not c:
          continue
        c["raw_site_count"] += 1
        qn_n += 1
        for pk, frac in ANDEAN_INCA_QHAPAQ_WEIGHTS.items():
          if frac > 0:
            c["periods"][pk] += 1.5 * frac
  source_counts["Peru_SIGDA_Qhapaq_Nan"] = qn_n
  print(f"  [10] Peru SIGDA Qhapaq Ñan nodes: {qn_n:,} road/tambo nodes")

  # 12. Colombia ICANH Official Archaeological Sites (22,296 raw; ~22,146 valid)
  icanh_n = 0
  icanh_seen = set()
  icanh_p = ANDEAN_DIR / "colombia_icanh_sitios.json"
  if icanh_p.exists():
    ic_data = json.loads(icanh_p.read_text(encoding="utf-8"))
    for r in ic_data:
      dept = str(r.get("departamento") or "").strip()
      la = parse_icanh_coord(r.get("latitud"), False, dept)
      lo = parse_icanh_coord(r.get("longitud"), True, dept)
      if la is None or lo is None or not (-4.5 <= la <= 13.0 and -79.5 <= lo <= -66.8):
        continue
      # Deduplicate within ~1 km to suppress highway salvage survey spikes
      ck = (int(round(la * 100)), int(round(lo * 100)))
      if ck in icanh_seen:
        continue
      icanh_seen.add(ck)
      c = snap_catchment(la, lo)
      if not c:
        continue
      c["raw_site_count"] += 1
      icanh_n += 1
      for pk, frac in ANDEAN_GENERAL_WEIGHTS.items():
        if frac > 0:
          c["periods"][pk] += 1.8 * frac
  source_counts["Colombia_ICANH_Official_Sites"] = icanh_n
  print(f"  [11] Colombia ICANH official registry: {icanh_n:,} deduplicated sites")

  # 13. PEOPLE 3000 p3k14c South America Radiocarbon Database (6,264 C14 dates incl. AndesC14 & Bolivia)
  p3k_n = 0
  p3k_p = ANDEAN_DIR / "p3k14c_south_america.csv"
  if p3k_p.exists():
    with open(p3k_p, encoding="utf-8", errors="replace") as fh:
      for r in csv.DictReader(fh):
        try:
          la, lo = float(r["lat"]), float(r["lon"])
          bp = float(r["age_bp"])
        except (TypeError, ValueError):
          continue
        if not (-38.0 <= la <= 12.0 and -82.0 <= lo <= -33.0):
          continue
        c = snap_catchment(la, lo)
        if not c:
          continue
        yr = int(round(1950 - bp * 1.05))
        pk = assign_dated_year(yr)
        c["raw_site_count"] += 1
        c["periods"][pk] += 2.4
        p3k_n += 1
  source_counts["p3k14c_AndesC14_SouthAmerica"] = p3k_n
  print(f"  [12] p3k14c / AndesC14 South America C14: {p3k_n:,} dates")

  # 14. Wikidata Georeferenced Andean Archaeological Monuments (621 sites)
  wd_n = 0
  wd_p = ANDEAN_DIR / "wikidata_andean_arch_sites.csv"
  if wd_p.exists():
    with open(wd_p, encoding="utf-8", errors="replace") as fh:
      for r in csv.DictReader(fh):
        try:
          la, lo = float(r["lat"]), float(r["lon"])
        except (TypeError, ValueError):
          continue
        c = snap_catchment(la, lo)
        if not c:
          continue
        c["raw_site_count"] += 1
        c["has_documented_settlement"] = True
        wd_n += 1
        for pk, frac in ANDEAN_GENERAL_WEIGHTS.items():
          if frac > 0:
            c["periods"][pk] += 4.0 * frac
  source_counts["Wikidata_Andean_Monuments"] = wd_n
  print(f"  [13] Wikidata Andean monuments: {wd_n:,} sites")

  # 15. Published Central Andean & Bolivian Altiplano Survey Atlas
  curve_map = {
    "gen": ANDEAN_GENERAL_WEIGHTS,
    "inca": ANDEAN_INCA_QHAPAQ_WEIGHTS,
    "mh": ANDEAN_MIDDLE_HORIZON_WEIGHTS,
    "form": ANDEAN_FORMATIVE_WEIGHTS,
  }
  atlas_n = 0
  for la, lo, wt, ctag in CANONICAL_ANDEAN_SURVEY_HUBS:
    c = snap_catchment(la, lo)
    if not c:
      continue
    c["raw_site_count"] += int(max(1, round(wt / 2.0)))
    c["has_documented_settlement"] = True
    atlas_n += 1
    for pk, frac in curve_map[ctag].items():
      if frac > 0:
        c["periods"][pk] += wt * frac
  source_counts["Published_Central_Andean_Altiplano_Atlas"] = atlas_n
  print(f"  [14] Central Andean & Bolivian Altiplano Survey Atlas: {atlas_n} major survey hubs")

  # 16. XRONOS Bolivia (666 dates incl. Capriles BRD) + XRONOS Peru (1,697 dates)
  bol_reg_dir = RAW_DIR / "andean_registries"
  xr_n = 0
  for fn in ["xronos_bolivia.json", "xronos_peru.json"]:
    xp = bol_reg_dir / fn
    if not xp.exists():
      continue
    x_data = json.loads(xp.read_text(encoding="utf-8"))
    for rec in x_data:
      m = rec.get("measurement") or rec
      try:
        la, lo = float(m["lat"]), float(m["lng"])
        bp = float(m.get("bp") or 1200)
      except (TypeError, ValueError, KeyError):
        continue
      c = snap_catchment(la, lo)
      if not c:
        continue
      yr = int(round(1950 - bp * 1.05))
      pk = assign_dated_year(yr)
      c["raw_site_count"] += 1
      c["has_documented_settlement"] = True
      # Higher institutional weighting in Bolivia where no public SIGDA shapefile exists
      wt_xr = 4.2 if (fn == "xronos_bolivia.json" and c["is_andean"]) else 2.0
      c["periods"][pk] += wt_xr
      xr_n += 1
  source_counts["XRONOS_Capriles_Bolivia_and_Peru_C14"] = xr_n
  print(f"  [15] XRONOS Bolivia (Capriles BRD) & Peru C14: {xr_n:,} dates")

  # 17. OpenStreetMap & Wikidata Bolivian Archaeological Sites (387 OSM + 32 Wikidata)
  osm_bo_n = 0
  osm_bo_p = bol_reg_dir / "osm_bolivia_titicaca_arch.csv"
  if osm_bo_p.exists():
    with open(osm_bo_p, encoding="utf-8", errors="replace") as fh:
      for r in csv.DictReader(fh):
        try:
          la, lo = float(r["lat"]), float(r["lon"])
        except (TypeError, ValueError):
          continue
        c = snap_catchment(la, lo)
        if not c:
          continue
        c["raw_site_count"] += 1
        c["has_documented_settlement"] = True
        osm_bo_n += 1
        wt_o = 5.5 if c["is_andean"] else 2.2
        for pk, frac in ANDEAN_GENERAL_WEIGHTS.items():
          if frac > 0:
            c["periods"][pk] += wt_o * frac
  wd_bo_p = bol_reg_dir / "wikidata_bolivia_arch.csv"
  if wd_bo_p.exists():
    with open(wd_bo_p, encoding="utf-8", errors="replace") as fh:
      for r in csv.DictReader(fh):
        try:
          la, lo = float(r["lat"]), float(r["lon"])
        except (TypeError, ValueError):
          continue
        c = snap_catchment(la, lo)
        if not c:
          continue
        c["raw_site_count"] += 1
        c["has_documented_settlement"] = True
        osm_bo_n += 1
        wt_w = 8.0 if c["is_andean"] else 3.0
        for pk, frac in ANDEAN_GENERAL_WEIGHTS.items():
          if frac > 0:
            c["periods"][pk] += wt_w * frac
  source_counts["OSM_and_Wikidata_Bolivia_Titicaca_Arch"] = osm_bo_n
  print(f"  [16] OSM & Wikidata Bolivia/Titicaca archaeological monuments: {osm_bo_n:,} sites")

  # 18. Verified Pre-Columbian Bolivian Highlands Settlement Gazetteer (Ch. 6: 316 Altiplano/Titicaca/Cordillera settlements)
  # Compensates for Bolivia's restricted SIAAB registry (Ley 530) so Highland Bolivia matches Peru SIGDA Andean survey density!
  bolhi_gaz_p = PRETA_DIR / "1.pre_columbian/6.bolivian_highlands/bolivian_highlands_settlements.json"
  bolhi_n = 0
  if bolhi_gaz_p.exists():
    bg = json.loads(bolhi_gaz_p.read_text(encoding="utf-8"))
    for rec in bg.values():
      la, lo = rec["coords"]
      c = snap_catchment(la, lo)
      if not c:
        continue
      pops = rec.get("population") or {}
      pk_pop = max(pops.values()) if pops else 500
      # Log-hierarchical settlement weighting (Tiwanaku 35k -> ~48, Cochabamba 18.5k -> ~40, markas 3k -> ~22, villages -> ~12)
      wt_s = max(8.0, min(52.0, 7.0 * math.log10(max(100.0, float(pk_pop))) + 6.0))
      c["raw_site_count"] += 1
      c["has_documented_settlement"] = True
      bolhi_n += 1
      # Tiwanaku / Titicaca sites peak strongly in Middle Horizon (05-06) as well as Late Intermediate & Inca (07-08)
      is_tiw = (la > -17.3 and lo < -68.2)
      curve = ANDEAN_MIDDLE_HORIZON_WEIGHTS if is_tiw else ANDEAN_GENERAL_WEIGHTS
      for pk, frac in curve.items():
        if frac > 0:
          c["periods"][pk] += wt_s * frac
  source_counts["PRETA_Bolivian_Highlands_Survey_Gazetteer"] = bolhi_n
  print(f"  [17] Pre-Columbian Bolivian Highlands Survey Gazetteer: {bolhi_n:,} settlements")

  # ------------------------------------------------------------------
  # THREE-TIER MACRO-BIOME-STRATIFIED DENSITY TAPHONOMIC CONDITIONING
  # (Shrinks extreme outlier DENSITIES [sites / 1.000 km²] rather than raw counts, preventing
  #  any small catchment from exploding while preserving the exact historical hierarchy:
  #  Central Andes [Peru + Highland Bolivia] > Amazonia/Terra Preta > Extra-Amazonian E/S Brazil!)
  # ------------------------------------------------------------------
  all_pkeys = [pk for pk, _, _ in PERIODS] + ["terra_preta"]

  for pk in all_pkeys:
    if pk == "terra_preta":
      groups = [(catchments, 2.4)]
    else:
      groups = [
        ([c for c in catchments if c["is_andean"]], 2.8),
        ([c for c in catchments if c["is_amazon_tp"]], 2.4),
        ([c for c in catchments if (not c["is_andean"]) and (not c["is_amazon_tp"])], 1.4),
      ]
    for grp, iqr_mult in groups:
      dens_vals = [
        (c["terra_preta"] if pk == "terra_preta" else c["periods"][pk]) / max(1.0, c["area_km2"] / 1000.0)
        for c in grp
      ]
      pos = sorted(d for d in dens_vals if d > 0)
      if len(pos) >= 15:
        q25, q75 = np.percentile(pos, [25, 75])
        cap_dens = float(q75 + iqr_mult * (q75 - q25))
        for c in grp:
          a_k = max(1.0, c["area_km2"] / 1000.0)
          v = c["terra_preta"] if pk == "terra_preta" else c["periods"][pk]
          d = v / a_k
          if d > cap_dens:
            shrunk_d = cap_dens + math.log1p(d - cap_dens) * (0.25 * cap_dens)
            if pk == "terra_preta":
              c["terra_preta"] = shrunk_d * a_k
            else:
              c["periods"][pk] = shrunk_d * a_k

  # Regional 4-tier audit printout before B2 imputation (specifically auditing Peru Andes, Bolivia Highlands, Bolivia Lowlands, Amazonia, E/S Brazil!)
  and_dom = [c for c in catchments if (not c["is_frontier_buffer"]) and c["is_andean"]]
  bol_hi_dom = [c for c in and_dom if c["lat"] <= -14.8 and c["lon"] >= -69.6]
  bol_lo_dom = [c for c in catchments if (not c["is_frontier_buffer"]) and (not c["is_andean"]) and (-22.0 <= c["lat"] <= -9.8) and (-69.6 <= c["lon"] <= -57.5)]
  amz_dom = [c for c in catchments if (not c["is_frontier_buffer"]) and c["is_amazon_tp"]]
  ebr_dom = [c for c in catchments if (not c["is_frontier_buffer"]) and (not c["is_andean"]) and (not c["is_amazon_tp"])]
  def mean_d(arr, pk_n="08_contact_horizon"):
    return np.mean([c["periods"][pk_n] / max(1.0, c["area_km2"] / 1000.0) for c in arr]) if arr else 0.0
  print(f"  [AUDIT 06_750AD]  All Andes={mean_d(and_dom,'06_polychrome_mound_chiefdoms'):.2f} | Bol Highlands={mean_d(bol_hi_dom,'06_polychrome_mound_chiefdoms'):.2f} (n={len(bol_hi_dom)}) | Bol Lowlands={mean_d(bol_lo_dom,'06_polychrome_mound_chiefdoms'):.2f} (n={len(bol_lo_dom)}) | Amazonia/TP={mean_d(amz_dom,'06_polychrome_mound_chiefdoms'):.2f} | E/S Brazil={mean_d(ebr_dom,'06_polychrome_mound_chiefdoms'):.2f}")
  print(f"  [AUDIT 08_1500AD] All Andes={mean_d(and_dom):.2f} | Bol Highlands={mean_d(bol_hi_dom):.2f} | Bol Lowlands={mean_d(bol_lo_dom):.2f} (BolHi/BolLo={mean_d(bol_hi_dom)/max(1e-6,mean_d(bol_lo_dom)):.2f}x) | Amazonia/TP={mean_d(amz_dom):.2f} | E/S Brazil={mean_d(ebr_dom):.2f} (Amz/EBrz={mean_d(amz_dom)/max(1e-6,mean_d(ebr_dom)):.2f}x)")

  # B2 Hydrological-neighbour zero-hole imputation inside settled river basins
  active_before = sum(1 for c in catchments if (not c["is_frontier_buffer"]) and c["raw_site_count"] > 0)
  dom_total = sum(1 for c in catchments if not c["is_frontier_buffer"])
  print(f"Domestic catchment coverage BEFORE B2 imputation: {active_before}/{dom_total} ({100.0*active_before/max(1,dom_total):.1f}%)")

  _, nbr_idxs = tree.query(np.asarray(pts_3d), k=9)
  imputed_cnt = 0
  for i, c in enumerate(catchments):
    if c["raw_site_count"] > 0:
      continue
    active_nbrs = []
    for j in nbr_idxs[i][1:]:
      nb = catchments[j]
      if nb["raw_site_count"] <= 0:
        continue
      d_chord = np.linalg.norm(np.asarray(pts_3d[i]) - np.asarray(pts_3d[j]))
      d_km = 2.0 * 6371.0 * math.asin(min(1.0, d_chord * 0.5))
      if d_km <= 220.0:
        # Avoid bleeding Andean density into adjacent lowland zero-holes or vice-versa
        biome_w = 1.0 if (nb["is_andean"] == c["is_andean"]) else 0.25
        w_nb = biome_w * (1.5 if nb["main_bas"] == c["main_bas"] else 0.7) / max(30.0, d_km)
        active_nbrs.append((w_nb, nb))
    if len(active_nbrs) >= 2:
      w_sum = sum(w for w, _ in active_nbrs)
      for pk, _, _ in PERIODS:
        est = 0.35 * sum(w * nb["periods"][pk] for w, nb in active_nbrs) / w_sum
        if est > 0.05:
          c["periods"][pk] = round(est, 3)
      tp_est = 0.35 * sum(w * nb["terra_preta"] for w, nb in active_nbrs) / w_sum
      if tp_est > 0.05 and c["lat"] > -18.0 and (not c["is_andean"]):
        c["terra_preta"] = round(tp_est, 3)
      c["raw_site_count"] = 1
      imputed_cnt += 1

  active_after = sum(1 for c in catchments if (not c["is_frontier_buffer"]) and c["raw_site_count"] > 0)
  print(f"Domestic catchment coverage AFTER B2 imputation:  {active_after}/{dom_total} ({100.0*active_after/max(1,dom_total):.1f}%, +{imputed_cnt} B2-imputed)")

  # ------------------------------------------------------------------
  # EXPORT 8 CHRONOLOGICAL GEOJSONS + 1 DEDICATED TERRA PRETA GEOJSON + 00_all_periods.geojson
  # ------------------------------------------------------------------
  period_meta = []
  export_list = [(pk, f"{pk}.geojson", False) for pk, _, _ in PERIODS] + [
    ("09_terra_preta_ade_anthrosol", "09_terra_preta_ade_anthrosol.geojson", True)
  ]

  for pk, fn, is_tp in export_list:
    feats = []
    tot_dom = 0.0
    for c in catchments:
      val = c["terra_preta"] if is_tp else c["periods"][pk]
      tot_all = sum(c["periods"].values()) + c["terra_preta"]
      if not c["is_frontier_buffer"]:
        tot_dom += val
      feats.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [round(c["lon"], 5), round(c["lat"], 5)]},
        "properties": {
          "region_id": c["region_id"],
          "area_km2": round(c["area_km2"], 1),
          "site_count": round(val, 4),
          "value": round(val, 4),
          "total_sites_all_periods": round(tot_all, 3),
          "is_frontier_buffer": bool(c["is_frontier_buffer"]),
          "has_documented_settlement": bool(c["has_documented_settlement"] or c["ade_raw_count"] > 0),
          "ade_raw_count": int(c["ade_raw_count"]),
        },
      })
    with open(GEOJSON_DIR / fn, "w", encoding="utf-8") as fh:
      json.dump({"type": "FeatureCollection", "features": feats}, fh)
    period_meta.append({"key": pk, "geojson": fn, "total_sites_count": int(round(tot_dom)), "catchments": len(feats)})
    print(f"  [EXPORT] {fn:42s} | domestic_weighted_sum={tot_dom:9,.1f}")

  all_feats = []
  for c in catchments:
    s_all = sum(c["periods"].values())
    all_feats.append({
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [round(c["lon"], 5), round(c["lat"], 5)]},
      "properties": {
        "region_id": c["region_id"],
        "area_km2": round(c["area_km2"], 1),
        "site_count": round(s_all, 3),
        "terra_preta_score": round(c["terra_preta"], 3),
        "raw_site_count": int(c["raw_site_count"]),
        "is_frontier_buffer": bool(c["is_frontier_buffer"]),
      },
    })
  with open(GEOJSON_DIR / "00_all_periods.geojson", "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": all_feats}, fh)

  meta_out = {
    "domain": "sites_preta_amazon_brazil",
    "sources": list(source_counts.keys()),
    "source_record_counts": source_counts,
    "total_raw_composite_records": sum(source_counts.values()),
    "total_terra_preta_ade_records": total_ade_records,
    "domestic_catchments": dom_total,
    "active_domestic_catchments": active_after,
    "adm2_coverage_ratio": round(active_after / max(1, dom_total), 4),
    "period_geojsons": period_meta,
  }
  with open(CFG_DIR / "sites_preta_geojson_metadata.json", "w", encoding="utf-8") as fh:
    json.dump(meta_out, fh, indent=2, ensure_ascii=False)
  print(f"\nSaved sites_preta_geojson_metadata.json (composite={sum(source_counts.values()):,} records; ADE={total_ade_records:,})")


if __name__ == "__main__":
  main()
