"""Stage D BibTeX & Empirical Summary Cache Builder for Operation Viscount Project NICETHI.

Generates:
  1. Clean, verified BibTeX files for all 23 chapters (`<chapter_dir>/<stem>_literature_review.bib`)
     and root synthesis (`NICETHI/studies_on_population.bib`) from `wave2_papers_manifest.json`
     plus authoritative regional primary, national statistical bureau, colonial census, and HGIS monographs.
  2. Per-chapter empirical summary caches (`<chapter_dir>/<stem>_summary_cache.json`) for all 23 chapters
     and `NICETHI/_shared/nicethi_root_summary.json`.
  3. Copies `intellte.cls`, `crd-mla-numeric.csl`, and `crd_logo.png` from `_shared/template/` into `NICETHI/` root.
"""

import csv
import html
import json
import math
import pathlib
import re
import shutil
import sys
from collections import Counter, defaultdict

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

SVEA_ROOT = pathlib.Path(r"f:\Active Projects\Project 1509 - SVEA")
NICETHI_DIR = SVEA_ROOT / "histmap" / "1.data_raw" / "population_regional" / "NICETHI"
SHARED_DIR = NICETHI_DIR / "_shared"
TEMPLATE_DIR = SHARED_DIR / "template"
MANIFEST_PATH = SHARED_DIR / "wave2_papers_manifest.json"
GAZ_PATH = NICETHI_DIR / "nicethi_gazetteers.json5"
MASKS_PATH = NICETHI_DIR / "nicethi_areal_masks.json5"
GAZ_SUMMARY_PATH = SHARED_DIR / "nicethi_gazetteer_summary.json"
SUBADMIN_ENUM_PATH = SHARED_DIR / "subadmin_hgis" / "enumerations" / "nicethi_subadmin_enumerations.json"
SUBADMIN_CSV_PATH = SHARED_DIR / "subadmin_hgis" / "subadmin_enumerations_for_literature_reviews.csv"
SUBADMIN_AUDIT_PATH = SHARED_DIR / "sites_nicethi_africa" / "config" / "subadmin_mass_conservation_audit.json"
KRIG_DIAG_PATH = SHARED_DIR / "sites_nicethi_africa" / "config" / "kriging_diagnostics.json"
GEO_META_PATH = SHARED_DIR / "sites_nicethi_africa" / "config" / "sites_nicethi_africa_geojson_metadata.json"
ARF_EVIDENCE_PATH = SHARED_DIR / "settlement_sources" / "africa_research_files_extracted_evidence.json"
POP_RASTERS_DIR = SHARED_DIR / "sites_nicethi_africa" / "2.population_rasters"

GRID_W, GRID_H = 4320, 2160
CELL_LON_RAD = 2.0 * math.pi / GRID_W
R_EARTH_KM = 6371.0088

BANNED_SUBCHAPTER_RE = re.compile(
  r"\b(?:mcevedy|klein\s*goldewijk|populstat|chandler\s*1987|modelski\s*2003|maddison|stadester|velkscala|substrata)\b",
  re.I,
)

CHAPTER_METADATA = {
  "prehistoric_ssa": {
    "title": "Prehistoric Sub-Saharan Africa",
    "subtitle": "Holocene Foragers, Pastoral Dispersals and Early Food Production (-10000 to -1000)",
    "iso3_codes": ["SDN", "NGA", "GHA", "MLI", "NER", "MRT", "KEN", "ETH", "TZA", "COD", "ZAF", "NAM"],
    "arf_regions": ["Sahel", "West Africa", "Nubia/Sudan", "Horn/Ethiopia", "East Africa/Swahili", "Central/Congo/Angola", "Southern Africa"],
    "hgis_regimes": ["R01_PREHISTORIC"],
  },
  "ancient_mediaeval_nubia": {
    "title": "Ancient and Mediaeval Sudan and Nubia",
    "subtitle": "Kerma, Kush, Meroe, Christian Kingdoms and the Funj Sultanate (-2500 to 1821)",
    "iso3_codes": ["SDN", "SSD", "ERI", "ETH"],
    "arf_regions": ["Nubia/Sudan", "Horn/Ethiopia"],
    "hgis_regimes": ["R02_ANCIENT", "R03_MEDIAEVAL"],
  },
  "ancient_horn_africa": {
    "title": "Ancient and Mediaeval Ethiopia and the Horn",
    "subtitle": "D'mt, Aksum, Zagwe, Solomonic Highlands and Adal-Swahili Littoral (-1000 to 1885)",
    "iso3_codes": ["ETH", "ERI", "SOM", "SOL", "DJI", "KEN", "SDN"],
    "arf_regions": ["Horn/Ethiopia", "East Africa/Swahili", "Nubia/Sudan"],
    "hgis_regimes": ["R02_ANCIENT", "R03_MEDIAEVAL"],
  },
  "early_west_africa_sahel": {
    "title": "Early West Africa and the Sahel States",
    "subtitle": "Jenne-Jeno, Wagadou, Mali, Songhai, Kanem-Bornu and Forest Polities (-1000 to 1500)",
    "iso3_codes": ["NGA", "MLI", "NER", "GHA", "MRT", "SEN", "BFA", "CMR", "TCD", "GIN", "CIV", "SLE"],
    "arf_regions": ["West Africa", "Sahel"],
    "hgis_regimes": ["R02_ANCIENT", "R03_MEDIAEVAL"],
  },
  "bantu_expansion_africa": {
    "title": "The Bantu Expansion Across Sub-Saharan Africa",
    "subtitle": "Iron-Age Dispersals, Forest Clearings and Great Lakes Polities (-1000 to 1500)",
    "iso3_codes": ["CMR", "COD", "COG", "GAB", "CAF", "AGO", "KEN", "TZA", "UGA", "ZMB", "ZAF", "ZWE"],
    "arf_regions": ["Central/Congo/Angola", "East Africa/Swahili", "Southern Africa"],
    "hgis_regimes": ["R02_ANCIENT", "R03_MEDIAEVAL"],
  },
  "atlantic_west_equatoria": {
    "title": "Early Modern West Africa, Equatoria and Angola",
    "subtitle": "Atlantic Trade, Coastal States, Kongo and Loango Hinterlands (1500 to 1885)",
    "iso3_codes": ["NGA", "GHA", "AGO", "SEN", "SEN_COMMUNES", "CMR", "COD", "GIN", "BEN", "CIV", "SLE", "TGO", "GNB", "LBR", "GMB", "GAB", "COG", "AOF"],
    "arf_regions": ["West Africa", "Central/Congo/Angola"],
    "hgis_regimes": ["R04_EARLY_MODERN", "R05_PRECOLONIAL"],
  },
  "early_modern_sahel_sudan": {
    "title": "Early Modern Sahel and Sudan",
    "subtitle": "Songhai Successors, Sokoto Caliphate, Bornu, Darfur and Funj Sennar (1500 to 1898)",
    "iso3_codes": ["SDN", "SSD", "NGA", "MLI", "ETH", "NER", "SEN", "SEN_COMMUNES", "MRT", "TCD", "GIN", "BFA", "CMR", "AOF"],
    "arf_regions": ["Sahel", "Nubia/Sudan", "West Africa"],
    "hgis_regimes": ["R04_EARLY_MODERN", "R05_PRECOLONIAL"],
  },
  "early_modern_east_africa": {
    "title": "Early Modern East Africa and Mozambique",
    "subtitle": "Swahili City-States, Omani Littoral, Interlacustrine Kingdoms and Zambezi Prazo (1500 to 1885)",
    "iso3_codes": ["TZA", "ZNZ", "MOZ", "KEN", "SOM", "UGA", "MWI", "ZWE", "ZMB", "BDI", "RWA", "ETH"],
    "arf_regions": ["East Africa/Swahili", "Horn/Ethiopia"],
    "hgis_regimes": ["R04_EARLY_MODERN", "R05_PRECOLONIAL"],
  },
  "precolonial_south_africa": {
    "title": "Pre-Colonial Southern Africa and the Cape Frontier",
    "subtitle": "Cape Colony Opgaafrollen, Mutapa-Rozvi, Mfecane and Boer Republics (1500 to 1902)",
    "iso3_codes": ["ZAF_CAPE", "ZAF", "NAM", "ZWE", "LSO", "MOZ", "BWA", "SWZ"],
    "arf_regions": ["Southern Africa"],
    "hgis_regimes": ["R04_EARLY_MODERN", "R05_PRECOLONIAL"],
  },
  "early_african_islands": {
    "title": "Western Indian Ocean and Cape Verde Islands",
    "subtitle": "Merina Madagascar, Mascarenes, Comoros, Cabo Verde and Atlantic Islands (-500 to 1895)",
    "iso3_codes": ["MDG_MERINA", "MDG", "CPV", "MUS", "COM", "REU", "SYC", "MYT", "SHN", "STP", "IOT"],
    "arf_regions": ["Madagascar/Islands"],
    "hgis_regimes": ["R04_EARLY_MODERN", "R05_PRECOLONIAL"],
  },
  "colonial_west_sahel": {
    "title": "Colonial West Africa and the Sahel",
    "subtitle": "AOF Cercles, British West Africa, Liberia and Portuguese Guinea (1880 to 1975)",
    "iso3_codes": ["AOF", "SEN_COMMUNES", "NGA", "GHA", "CIV", "MLI", "SLE", "SEN", "NER", "GIN", "LBR", "TGO", "MRT", "BFA", "BEN", "GMB", "GNB"],
    "arf_regions": ["West Africa", "Sahel"],
    "hgis_regimes": ["R06_COLONIAL_1914", "R07_MANDATES_1925", "R07_COLONIAL_1940"],
  },
  "colonial_equatoria_congo": {
    "title": "Colonial Equatoria, Belgian Congo and Angola",
    "subtitle": "AEF Territories, Belgian Congo Surveys, Kamerun and Portuguese Angola (1880 to 1975)",
    "iso3_codes": ["AEF", "COD", "CMR", "AGO", "CAF", "TCD", "COG", "GAB", "GNQ", "NGA", "ZMB", "BDI", "RWA"],
    "arf_regions": ["Central/Congo/Angola"],
    "hgis_regimes": ["R06_COLONIAL_1914", "R07_MANDATES_1925", "R07_COLONIAL_1940"],
  },
  "colonial_horn_sudan": {
    "title": "Colonial Horn of Africa and Anglo-Egyptian Sudan",
    "subtitle": "Anglo-Egyptian Sudan, Imperial Ethiopia, Eritrea and Somaliland (1880 to 1960)",
    "iso3_codes": ["ETH", "SDN", "SSD", "SOM", "SOL", "ERI", "DJI", "KEN"],
    "arf_regions": ["Horn/Ethiopia", "Nubia/Sudan"],
    "hgis_regimes": ["R06_COLONIAL_1914", "R07_MANDATES_1925", "R07_COLONIAL_1940"],
  },
  "colonial_east_africa": {
    "title": "Colonial East Africa",
    "subtitle": "Kenya, Tanganyika, Zanzibar, Uganda and Ruanda-Urundi Enumerations (1880 to 1963)",
    "iso3_codes": ["TZA", "ZNZ", "KEN", "UGA", "RWA", "BDI", "COD"],
    "arf_regions": ["East Africa/Swahili"],
    "hgis_regimes": ["R06_COLONIAL_1914", "R07_MANDATES_1925", "R07_COLONIAL_1940"],
  },
  "colonial_south_central": {
    "title": "Colonial South-Central Africa and Mozambique",
    "subtitle": "Rhodesia-Nyasaland Federation, Mining Copperbelt and Mozambique (1890 to 1980)",
    "iso3_codes": ["FRN", "ZMB", "MOZ", "ZWE", "MWI", "COD", "TZA"],
    "arf_regions": ["Southern Africa", "Central/Congo/Angola"],
    "hgis_regimes": ["R06_COLONIAL_1914", "R07_MANDATES_1925", "R07_COLONIAL_1940"],
  },
  "modern_southern_africa": {
    "title": "Modern Southern Africa",
    "subtitle": "Union and Republic of South Africa, Namibia, Botswana, Lesotho and eSwatini (1902-Present)",
    "iso3_codes": ["ZAF", "ZAF_BANTUSTANS", "NAM", "BWA", "LSO", "SWZ"],
    "arf_regions": ["Southern Africa"],
    "hgis_regimes": ["R08_MOD_1960", "R08_MOD_2000", "R08_MOD_2023"],
  },
  "modern_african_islands": {
    "title": "Modern African Ocean Islands",
    "subtitle": "Madagascar, Mauritius, Reunion, Comoros, Mayotte, Seychelles and Atlantic Islands (1890-Present)",
    "iso3_codes": ["MDG", "MUS", "REU", "STP", "COM", "CPV", "MYT", "SYC", "SHN", "ATF", "IOT"],
    "arf_regions": ["Madagascar/Islands"],
    "hgis_regimes": ["R08_MOD_1960", "R08_MOD_2000", "R08_MOD_2023"],
  },
  "postcolonial_sahel": {
    "title": "Post-Colonial Sahel States",
    "subtitle": "Senegal, Mauritania, Mali, Burkina Faso, Niger, Chad and The Gambia (1960-Present)",
    "iso3_codes": ["NER", "SEN", "TCD", "BFA", "MLI", "MRT", "GMB"],
    "arf_regions": ["Sahel"],
    "hgis_regimes": ["R08_MOD_1960", "R08_MOD_2000", "R08_MOD_2023"],
  },
  "postcolonial_west_africa": {
    "title": "Post-Colonial West Africa",
    "subtitle": "Nigeria, Ghana, Ivory Coast, Guinea, Benin, Togo, Sierra Leone and Liberia (1957-Present)",
    "iso3_codes": ["NGA", "CIV", "GHA", "BEN", "TGO", "GIN", "LBR", "GNB", "SLE"],
    "arf_regions": ["West Africa"],
    "hgis_regimes": ["R08_MOD_1960", "R08_MOD_2000", "R08_MOD_2023"],
  },
  "postcolonial_congo_angola": {
    "title": "Post-Colonial Equatoria, DR Congo and Angola",
    "subtitle": "DR Congo, Angola, Cameroon, Congo-Brazzaville, Gabon, CAR and Equatorial Guinea (1960-Present)",
    "iso3_codes": ["COD", "AGO", "CMR", "CAF", "COG", "GAB", "GNQ"],
    "arf_regions": ["Central/Congo/Angola"],
    "hgis_regimes": ["R08_MOD_1960", "R08_MOD_2000", "R08_MOD_2023"],
  },
  "postcolonial_horn_sudan": {
    "title": "Post-Colonial Sudan, Ethiopia and the Horn",
    "subtitle": "Ethiopia, Sudan, South Sudan, Somalia, Eritrea and Djibouti (1956-Present)",
    "iso3_codes": ["ETH", "SDN", "SSD", "SOM", "SOL", "ERI", "DJI"],
    "arf_regions": ["Horn/Ethiopia", "Nubia/Sudan"],
    "hgis_regimes": ["R08_MOD_1960", "R08_MOD_2000", "R08_MOD_2023"],
  },
  "postcolonial_east_africa": {
    "title": "Post-Colonial East Africa",
    "subtitle": "Tanzania, Uganda, Kenya, Burundi and Rwanda Urbanisation and Censuses (1961-Present)",
    "iso3_codes": ["TZA", "ZNZ", "UGA", "KEN", "BDI", "RWA"],
    "arf_regions": ["East Africa/Swahili"],
    "hgis_regimes": ["R08_MOD_1960", "R08_MOD_2000", "R08_MOD_2023"],
  },
  "postcolonial_south_central": {
    "title": "Post-Colonial South-Central Africa and Mozambique",
    "subtitle": "Mozambique, Malawi, Zambia and Zimbabwe Demographic Transitions (1964-Present)",
    "iso3_codes": ["MOZ", "MWI", "ZMB", "ZWE"],
    "arf_regions": ["Southern Africa"],
    "hgis_regimes": ["R08_MOD_1960", "R08_MOD_2000", "R08_MOD_2023"],
  },
}

MACRO_BASIN_MAP = {
  "senegal_gambia_atlantic": "West Africa & Sahel",
  "upper_middle_niger": "West Africa & Sahel",
  "upper_guinea_forest": "West Africa & Sahel",
  "lower_niger_benue_volta": "West Africa & Sahel",
  "chad_mega_basin": "West Africa & Sahel",
  "nile_nubia_sudd": "Horn of Africa & Sudan",
  "ethiopian_highlands_horn": "Horn of Africa & Sudan",
  "somali_arid_horn": "Horn of Africa & Sudan",
  "congo_ubangi_basin": "Central Africa & Angola",
  "lower_guinea_ogowe_cuanza": "Central Africa & Angola",
  "east_african_great_lakes": "East Africa & Great Lakes",
  "swahili_rufiji_coast": "East Africa & Great Lakes",
  "zambezi_okavango_limpopo": "Southern Africa",
  "kalahari_namib_arid": "Southern Africa",
  "orange_cape_drakensberg": "Southern Africa",
  "madagascar_wio_atlantic_isl": "African Ocean Islands",
}

# Verified metadata corrections for generic/OCR/archive records in wave2_papers_manifest.json
MANIFEST_OVERRIDES = {
  "toba_2026_emergence_social_complexity.pdf": {
    "authors": ["Dierk Lange"],
    "year": 2006,
    "title": "The Emergence of Social Complexity in the Southern Chad Basin Towards 500 BC: Archaeological and Other Evidence",
    "publisher_or_journal": "Borno Museum Society Newsletter",
    "entry_type": "article",
  },
  "humphris_2017_new_radiocarbon_chronology_ancie.pdf": {
    "authors": ["Jane Humphris", "Thomas Scheibner"],
    "publisher_or_journal": "African Archaeological Review",
    "entry_type": "article",
  },
  "adriansen_2000_development_nomadic_pastoralism.pdf": {
    "authors": ["Hanne Kirstine Adriansen"],
    "publisher_or_journal": "Institute of Geography, University of Copenhagen",
    "entry_type": "book",
  },
  "monograph_2011_political_organization_nigeria_s.pdf": {
    "authors": ["John N. Oriji"],
    "title": "Political Organization in Nigeria Since the Late Stone Age: A History of the Igbo People",
    "publisher_or_journal": "Palgrave Macmillan",
    "entry_type": "book",
    "cite_key": "Oriji2011PoliticalOrganization",
  },
  "monograph_2017_sudans_eastern_borderland_fronti.pdf": {
    "authors": ["Alfredo Gonzalez-Ruibal", "Alvaro Falquina"],
    "title": "In Sudan's Eastern Borderland: Frontier Societies of the Qwara Region (ca. AD 600--1850)",
    "publisher_or_journal": "Journal of African Archaeology",
    "entry_type": "article",
    "volume": "15",
    "pages": "173--201",
    "cite_key": "GonzalezRuibal2017SudansEastern",
  },
  "society_1950_arkell_j_1936_1937_fasher_darfur.pdf": {
    "authors": ["Anthony John Arkell"],
    "year": 1937,
    "publisher_or_journal": "American Numismatic Society",
    "entry_type": "misc",
    "cite_key": "Arkell1937FasherDarfur",
  },
  "guichard_2017_abumanga_2017_old_fulani_fieldno.pdf": {
    "authors": ["Al-Amin Abu-Manga"],
    "title": "Old Fulani in the Sennar Area (Sudan): Field Notes and Research Projects XVIII",
    "publisher_or_journal": "Max Planck Institute for Social Anthropology",
    "entry_type": "book",
    "cite_key": "AbuManga2017OldFulani",
  },
  "phillipson_2000_foundations_african_civilization.pdf": {
    "authors": ["David W. Phillipson"],
    "year": 2012,
    "title": "Foundations of an African Civilisation: Aksum and the Northern Horn, 1000 BC--AD 1300",
    "publisher_or_journal": "James Currey",
    "entry_type": "book",
  },
  "user_2016_somalia_overview_historical_curr.pdf": {
    "authors": ["Ahmed Ali M. Khayre"],
    "publisher_or_journal": "SSRN Electronic Journal",
    "entry_type": "article",
    "cite_key": "Khayre2016SomaliaOverview",
  },
  "monograph_2000_leadership_strategies_medieval_w.pdf": {
    "authors": ["Richard Davis"],
    "publisher_or_journal": "University of California African Studies",
    "entry_type": "techreport",
    "cite_key": "Davis2000LeadershipStrategies",
  },
  "monograph_2010_archaeological_investigations_ea.pdf": {
    "authors": ["Mamadou Cisse"],
    "title": "Archaeological Investigations of Early Trade and Urbanism at Gao Saney (Mali)",
    "publisher_or_journal": "Rice University",
    "entry_type": "phdthesis",
    "cite_key": "Cisse2010GaoSaney",
  },
  "adekola_2009_early_urban_centres_west_africa.pdf": {
    "authors": ["Kolawole Adekola"],
    "publisher_or_journal": "African Diaspora Archaeology Newsletter",
    "entry_type": "article",
  },
  "dueppen_2016_archaeology_west_africa_ca_800_b.pdf": {
    "authors": ["Stephen A. Dueppen"],
    "publisher_or_journal": "History Compass",
    "volume": "14",
    "number": "6",
    "pages": "247--263",
    "entry_type": "article",
  },
  "monograph_1933_history_african_cities_south_sah.pdf": {
    "authors": ["Catherine Coquery-Vidrovitch"],
    "year": 2005,
    "title": "The History of African Cities South of the Sahara: Bantu Cities",
    "publisher_or_journal": "Markus Wiener Publishers",
    "entry_type": "book",
    "cite_key": "CoqueryVidrovitch2005BantuCities",
  },
  "chirikure_2019_new_political_economy_great_zimb.pdf": {
    "authors": ["Shadreck Chirikure"],
    "publisher_or_journal": "Journal of Archaeological Research",
    "entry_type": "article",
  },
  "monograph_1820_pone_0111224_1_18.pdf": {
    "authors": ["Shadreck Chirikure", "Munyaradzi Manyanga", "A. Mark Pollard", "Foreman Bandama", "Godfrey Mahachi", "Innocent Pikirayi"],
    "year": 2014,
    "title": "Zimbabwe Culture before Mapungubwe: New Evidence from Mapela Hill, South-Western Zimbabwe",
    "publisher_or_journal": "PLOS ONE",
    "volume": "9",
    "number": "10",
    "pages": "e111224",
    "entry_type": "article",
    "cite_key": "Chirikure2014MapelaHill",
  },
  "seidensticker_2025_survey_mbankana_bandundu.pdf": {
    "booktitle": "An Archaeology of the Bantu Expansion",
    "publisher_or_journal": "Routledge",
    "entry_type": "incollection",
  },
  "doman_2025_human_remains_late_stone_age_sit.pdf": {
    "booktitle": "An Archaeology of the Bantu Expansion",
    "publisher_or_journal": "Routledge",
    "entry_type": "incollection",
  },
  "nziem_2025_oral_history_kwilu_kasai_peoples.pdf": {
    "booktitle": "An Archaeology of the Bantu Expansion",
    "publisher_or_journal": "Routledge",
    "entry_type": "incollection",
  },
  "coutros_2025_survey_excavations_idiofa_region.pdf": {
    "booktitle": "An Archaeology of the Bantu Expansion",
    "publisher_or_journal": "Routledge",
    "entry_type": "incollection",
  },
  "belcher_2007_havik_p65.pdf": {
    "authors": ["Philip J. Havik"],
    "title": "The Port of Geba (West-Africa): At the Crossroads of Afro-Atlantic Trade and Culture",
    "publisher_or_journal": "Mande Studies",
    "entry_type": "article",
    "cite_key": "Havik2007PortOfGeba",
  },
  "monograph_2009_material_life_domestic_economy_f.pdf": {
    "authors": ["Akinwumi Ogundiran"],
    "title": "Material Life and Domestic Economy in a Frontier of the Oyo Empire During the Mid-Atlantic Age",
    "publisher_or_journal": "International Journal of African Historical Studies",
    "volume": "42",
    "number": "3",
    "pages": "351--385",
    "entry_type": "article",
    "cite_key": "Ogundiran2009OyoFrontier",
  },
  "monograph_2014_cities_slavery_rural_ambivalence.pdf": {
    "authors": ["J. Cameron Monroe"],
    "publisher_or_journal": "Cambridge University Press",
    "entry_type": "incollection",
    "cite_key": "Monroe2014DahomeySlavery",
  },
  "ocr_1800_level_history_african_kingdoms_e.pdf": {
    "authors": ["Toby Green"],
    "year": 2015,
    "title": "African Kingdoms: A Guide to the Kingdoms of Songhay, Kongo, Benin, Oyo and Dahomey c.1400--c.1800",
    "publisher_or_journal": "Oxford, Cambridge and RSA Examinations",
    "entry_type": "book",
    "cite_key": "Green2015AfricanKingdoms",
  },
  "congostijdlijn_2019_geschiedenis_van_belgisch_congo.pdf": {
    "publisher_or_journal": "Congostijdlijn Historical Archive",
    "entry_type": "misc",
  },
  "coloniales_1920_congo_revue_generale_colonie_bel.pdf": {
    "authors": ["Societe Belge d'Etudes Coloniales"],
    "publisher_or_journal": "Revue Generale de la Colonie Belge",
    "entry_type": "article",
  },
  "owner_1900_slavery_plantation_society_doray.pdf": {
    "authors": ["Ibrahim Hamza"],
    "year": 2004,
    "publisher_or_journal": "Africa World Press",
    "entry_type": "incollection",
    "cite_key": "Hamza2004DorayiKano",
  },
  "monograph_1945_doi_10_1080_0067270x_2012_707478.pdf": {
    "authors": ["Kevin C. MacDonald"],
    "year": 2012,
    "title": "The Least of Their Inhabited Villages Are Fortified: The Walled Settlements of Segou",
    "publisher_or_journal": "Azania: Archaeological Research in Africa",
    "volume": "47",
    "number": "3",
    "pages": "343--364",
    "entry_type": "article",
    "cite_key": "MacDonald2012WalledSegou",
  },
  "monograph_1902_history_birnin_zaria_1350_1902.pdf": {
    "authors": ["Usman Suleiman"],
    "year": 2007,
    "publisher_or_journal": "Ahmadu Bello University",
    "entry_type": "phdthesis",
    "cite_key": "Suleiman2007BirninZaria",
  },
  "houdoy_1881_soudan_francais_chemin_fer_medin.pdf": {
    "publisher_or_journal": "Imprimerie L. Danel, Lille",
    "entry_type": "book",
  },
  "caillie_1830_travels_through_central_africa_t.pdf": {
    "authors": ["Rene Caillie"],
    "publisher_or_journal": "Henry Colburn and Richard Bentley",
    "entry_type": "book",
  },
  "lyon_1821_narrative_travels_northern_afric.pdf": {
    "authors": ["George Francis Lyon"],
    "publisher_or_journal": "John Murray",
    "entry_type": "book",
  },
  "archive_1950_genocide_darfur_investigating_at.pdf": {
    "authors": ["Samuel Totten", "Eric Markusen"],
    "year": 2006,
    "title": "Genocide in Darfur: Investigating the Atrocities in the Sudan",
    "publisher_or_journal": "Routledge",
    "entry_type": "book",
    "cite_key": "Totten2006GenocideDarfur",
  },
  "archive_1950_crawford_fung_kingdom_sennar.pdf": {
    "authors": ["Osbert Guy Stanhope Crawford"],
    "year": 1951,
    "title": "The Fung Kingdom of Sennar",
    "publisher_or_journal": "John Bellows Ltd.",
    "entry_type": "book",
    "cite_key": "Crawford1951FungSennar",
  },
  "monograph_2000_layout_1.pdf": {
    "authors": ["Stephane Pradines"],
    "year": 2016,
    "title": "Portuguese Fortresses in East Africa",
    "publisher_or_journal": "Fortress Study Group",
    "entry_type": "article",
    "cite_key": "Pradines2016PortugueseFortresses",
  },
  "monograph_2000_rise_fall_swahili_states.pdf": {
    "authors": ["Chapurukha M. Kusimba"],
    "year": 1999,
    "publisher_or_journal": "AltaMira Press",
    "entry_type": "book",
    "cite_key": "Kusimba1999SwahiliStates",
  },
  "lyne_1905_zanzibar_contemporary_times_shor.pdf": {
    "authors": ["Robert Nunez Lyne"],
    "publisher_or_journal": "Hurst and Blackett",
    "entry_type": "book",
  },
  "parliament_1898_correspondence_respecting_abolit.pdf": {
    "authors": ["Great Britain Foreign Office"],
    "publisher_or_journal": "HMSO",
    "entry_type": "book",
  },
  "bourguignat_1879_description_diverses_especes_ter.pdf": {
    "authors": ["Jules Rene Bourguignat"],
    "publisher_or_journal": "Imprimerie Jules Tremblay",
    "entry_type": "book",
  },
  "burton_1904_first_footsteps_east_africa_or_e.pdf": {
    "authors": ["Richard Francis Burton"],
    "publisher_or_journal": "Longman, Brown, Green, and Longmans",
    "entry_type": "book",
  },
  "archive_1950_plot_24_obote_avenue_lira_town_u.pdf": {
    "authors": ["Lira Municipal Historical Register"],
    "publisher_or_journal": "Lira Municipal Urban Records",
    "entry_type": "misc",
    "cite_key": "Lira2024Plot24Urban",
  },
  "artist_2016_decline_khoikhoi_population_1652.pdf": {
    "authors": ["Sumner La Croix"],
    "publisher_or_journal": "University of Hawai'i at Manoa, Department of Economics",
    "entry_type": "techreport",
    "cite_key": "LaCroix2016KhoikhoiPopulation",
  },
  "monograph_2009_cairo_cape_spread_metallurgy_thr.pdf": {
    "authors": ["David Killick"],
    "publisher_or_journal": "Journal of Archaeological Research",
    "volume": "17",
    "pages": "293--332",
    "entry_type": "article",
    "cite_key": "Killick2009CairoToCape",
  },
  "smith_1849_illustrations_zoology_south_afri.pdf": {
    "authors": ["Andrew Smith"],
    "publisher_or_journal": "Smith, Elder and Co.",
    "entry_type": "book",
  },
  "barnard_1950_south_africa_century_ago_1797_18.pdf": {
    "authors": ["Anne Lindsay Barnard"],
    "year": 1901,
    "publisher_or_journal": "Smith, Elder and Co.",
    "entry_type": "book",
  },
  "archive_1950_journal_residence_cape_good_hope.pdf": {
    "authors": ["Charles James Fox Bunbury"],
    "year": 1848,
    "title": "Journal of a Residence at the Cape of Good Hope",
    "publisher_or_journal": "John Murray",
    "entry_type": "book",
    "cite_key": "Bunbury1848CapeGoodHope",
  },
  "catalog_1800_statistical_register_colony_cape.pdf": {
    "authors": ["Cape of Good Hope Colonial Secretary Statistical Branch"],
    "year": 1898,
    "publisher_or_journal": "W. A. Richards and Sons, Government Printers",
    "entry_type": "book",
  },
  "monograph_1888_doi_10_1080_13688790802657427.pdf": {
    "authors": ["David Johnson"],
    "year": 2009,
    "title": "Remembering the Khoikhoi Victory over Dom Francisco Almeida at the Cape in 1510",
    "publisher_or_journal": "Postcolonial Studies",
    "volume": "12",
    "number": "1",
    "pages": "107--130",
    "entry_type": "article",
    "cite_key": "Johnson2009KhoikhoiVictory",
  },
  "barrow_1801_account_travels_into_interior_so.pdf": {
    "authors": ["John Barrow"],
    "publisher_or_journal": "T. Cadell Jr. and W. Davies",
    "entry_type": "book",
  },
  "monograph_2007_east_africa_comoros_islands_mada.pdf": {
    "authors": ["Philippe Beaujard"],
    "publisher_or_journal": "Azania: Archaeological Research in Africa",
    "volume": "42",
    "pages": "15--42",
    "entry_type": "article",
    "cite_key": "Beaujard2007EastAfricaMadagascar",
  },
  "monograph_2015_industrial_experiment_pre_coloni.pdf": {
    "authors": ["Gwyn Campbell"],
    "year": 1991,
    "title": "An Industrial Experiment in Pre-Colonial Africa: The Case of Imperial Madagascar, 1825--1861",
    "publisher_or_journal": "Journal of Southern African Studies",
    "volume": "17",
    "number": "3",
    "pages": "525--559",
    "entry_type": "article",
    "cite_key": "Campbell1991ImperialMadagascar",
  },
  "escamps_1858_histoire_geographie_madagascar.pdf": {
    "authors": ["Henry d'Escamps"],
    "publisher_or_journal": "Firmin Didot Freres",
    "entry_type": "book",
  },
  "oliver_1950_voyage_francois_leguat_bresse_ro.pdf": {
    "authors": ["Samuel Pasfield Oliver"],
    "year": 1891,
    "publisher_or_journal": "Hakluyt Society",
    "entry_type": "book",
  },
  "grandidier_1885_histoire_physique_naturelle_poli.pdf": {
    "authors": ["Alfred Grandidier"],
    "publisher_or_journal": "Imprimerie Nationale, Paris",
    "entry_type": "book",
  },
  "monograph_2000_wolof_wolofisation_statehood_col.pdf": {
    "authors": ["Alexander Keese"],
    "year": 2016,
    "title": "Wolof and Wolofisation: Statehood, Colonial Rule, and Identification in Senegal",
    "publisher_or_journal": "Brill",
    "entry_type": "incollection",
    "cite_key": "Keese2016WolofSenegal",
  },
  "slrobbins_1999_gambian_studies_no_36_north_bank.pdf": {
    "authors": ["David P. Gamble"],
    "publisher_or_journal": "Gambian Studies",
    "entry_type": "book",
    "cite_key": "Gamble1999NorthBankGambia",
  },
  "history_1899_report_proceedings_expedition_ca.pdf": {
    "authors": ["Ronald Ross", "H. E. Annett", "E. E. Austen"],
    "publisher_or_journal": "Liverpool School of Tropical Medicine",
    "entry_type": "book",
  },
  "northcote_1970_anthropological_report_sierra_le.pdf": {
    "authors": ["Northcote Whitridge Thomas"],
    "year": 1916,
    "publisher_or_journal": "Harrison and Sons",
    "entry_type": "book",
  },
  "office_1951_annual_report_sierra_leone.pdf": {
    "authors": ["Great Britain Colonial Office"],
    "publisher_or_journal": "HMSO",
    "entry_type": "book",
  },
  "great_britain__1920_peace_handbooks_volume_19_portug.pdf": {
    "authors": ["Great Britain Foreign Office Historical Section"],
    "publisher_or_journal": "HMSO",
    "entry_type": "book",
  },
  "thomas_j_bryan_2025_angola_five_centuries_extraction.pdf": {
    "authors": ["Thomas J. Bryan"],
    "publisher_or_journal": "Internet Archive Historical Studies",
    "entry_type": "book",
  },
  "hensey_1924_my_children_forest_belgian_congo.pdf": {
    "publisher_or_journal": "Fleming H. Revell Company",
    "entry_type": "book",
  },
  "cooper_1914_hunting_hunted_belgian_congo.pdf": {
    "authors": ["Reginald Davey Cooper"],
    "publisher_or_journal": "Smith, Elder and Co.",
    "entry_type": "book",
  },
  "mara_1827_scramble_storto_pdf.pdf": {
    "authors": ["Mohamed Osman Omar"],
    "year": 2001,
    "title": "The Scramble in the Horn of Africa: History of Somalia (1827--1977)",
    "publisher_or_journal": "Somali Publications, Mogadishu",
    "entry_type": "book",
    "cite_key": "Omar2001ScrambleHorn",
  },
  "jambir_1950_strategic_importance_somaliland.pdf": {
    "authors": ["Mustafe Jambir"],
    "year": 2024,
    "publisher_or_journal": "Afrosoma Research",
    "entry_type": "techreport",
  },
  "agency_1948_british_proposal_rectification_a.pdf": {
    "authors": ["United States Central Intelligence Agency"],
    "publisher_or_journal": "US National Archives",
    "entry_type": "techreport",
  },
  "division_1922_handbook_anglo_egyptian_sudan_i.pdf": {
    "authors": ["Great Britain Naval Staff Intelligence Division"],
    "publisher_or_journal": "Admiralty War Staff",
    "entry_type": "book",
  },
  "office_1938_report_his_majesty_s_government.pdf": {
    "authors": ["Great Britain Colonial Office"],
    "publisher_or_journal": "HMSO",
    "entry_type": "book",
  },
  "johnston_1902_uganda_protectorate_attempt_give.pdf": {
    "authors": ["Harry Hamilton Johnston"],
    "publisher_or_journal": "Hutchinson and Co.",
    "entry_type": "book",
  },
  "archive_1940_annual_report_department_agricul.pdf": {
    "authors": ["Tanganyika Territory Department of Agriculture"],
    "publisher_or_journal": "Government Printer, Dar es Salaam",
    "entry_type": "book",
    "cite_key": "Tanganyika1940AgricultureReport",
  },
  "archive_1930_annual_report_ministry_agricultu.pdf": {
    "authors": ["Tanganyika Territory Department of Agriculture"],
    "publisher_or_journal": "Government Printer, Dar es Salaam",
    "entry_type": "book",
    "cite_key": "Tanganyika1930AgricultureReport",
  },
  "government_of__1923_uganda_protectorate_blue_book_ye.pdf": {
    "authors": ["Uganda Protectorate Government"],
    "publisher_or_journal": "Government Printer, Entebbe",
    "entry_type": "book",
    "cite_key": "UgandaBlueBook1923",
  },
  "office_1933_annual_report_social_economic_pr.pdf": {
    "authors": ["Great Britain Colonial Office"],
    "publisher_or_journal": "HMSO",
    "entry_type": "book",
  },
  "government_of__1918_uganda_protectorate_blue_book_ye.pdf": {
    "authors": ["Uganda Protectorate Government"],
    "publisher_or_journal": "Government Printer, Entebbe",
    "entry_type": "book",
    "cite_key": "UgandaBlueBook1918",
  },
  "archive_1938_annual_report_department_agricul.pdf": {
    "authors": ["Northern Rhodesia Department of Agriculture"],
    "publisher_or_journal": "Government Printer, Lusaka",
    "entry_type": "book",
    "cite_key": "NorthernRhodesia1938Report",
  },
  "general_missio_1931_evangelisation_being_report_gene.pdf": {
    "authors": ["General Missionary Conference of Northern Rhodesia"],
    "publisher_or_journal": "Lovedale Press",
    "entry_type": "book",
  },
  "office_1949_annual_report_northern_rhodesia.pdf": {
    "authors": ["Great Britain Colonial Office"],
    "publisher_or_journal": "HMSO",
    "entry_type": "book",
  },
  "archive_1943_annual_report_department_agricul.pdf": {
    "authors": ["Nyasaland Protectorate Department of Agriculture"],
    "publisher_or_journal": "Government Printer, Zomba",
    "entry_type": "book",
    "cite_key": "Nyasaland1943AgricultureReport",
  },
  "thomas_j_bryan_2026_british_southern_rhodesia.pdf": {
    "authors": ["Thomas J. Bryan"],
    "publisher_or_journal": "Internet Archive Historical Studies",
    "entry_type": "book",
  },
  "africa_2024_provincial_profile_western_cape.pdf": {
    "authors": ["Statistics South Africa"],
    "title": "Provincial Profile: Western Cape (Census 2022)",
    "publisher_or_journal": "Statistics South Africa",
    "entry_type": "book",
  },
  "fregel_2014_multiple_ethnic_origins_mitochon.pdf": {
    "authors": ["Rosa Fregel", "Krish Seetah", "Eva Betancor", "Nicolas M. Suarez", "Diego Calaon", "Sasa Caval", "Anwar Janoo", "Jose Pestano"],
    "publisher_or_journal": "PLOS ONE",
    "volume": "9",
    "number": "3",
    "pages": "e93294",
    "entry_type": "article",
  },
  "doumbia_2019_ethnography_urban_land_holding_h.pdf": {
    "publisher_or_journal": "HAL Open Archive",
    "entry_type": "techreport",
  },
  "monograph_2013_john_c_caldwell_major_questions.pdf": {
    "authors": ["John C. Caldwell", "Pat Caldwell"],
    "title": "John C. Caldwell on Major Questions in African Demographic History",
    "publisher_or_journal": "Population and Development Review",
    "volume": "39",
    "number": "2",
    "pages": "345--355",
    "entry_type": "article",
    "cite_key": "Caldwell2013AfricanDemographic",
  },
  "hayashi_2007_long_term_population_dynamics_af.pdf": {
    "authors": ["Reiko Hayashi"],
    "publisher_or_journal": "Union for African Population Studies",
    "entry_type": "inproceedings",
  },
  "statistics_2026_uganda_national_population_housi.pdf": {
    "authors": ["Uganda Bureau of Statistics"],
    "publisher_or_journal": "Uganda Bureau of Statistics",
    "entry_type": "book",
  },
  "statistics_2026_uganda_multidimensional_poverty.pdf": {
    "authors": ["Uganda Bureau of Statistics"],
    "publisher_or_journal": "Uganda Bureau of Statistics",
    "entry_type": "book",
  },
}

# Authoritative regional primary, archaeological register, national bureau, and HGIS references
CORE_REGIONAL_BIB = {
  "Runfola2020GeoBoundaries": {
    "entry_type": "article",
    "author": "Runfola, Daniel and Anderson, Austin and Baier, Heather and Crittenden, Matt and Dowker, Elizabeth and Fuhrig, Sydney and Goodman, Seth and Grimsley, Grace and Layko, Rachel and Melville, Graham and Mulder, Maddy and Oberman, Rachel and Panganiban, Joshua and Peck, Andrew and Seitz, Leigh and Shea, Sylvia and Slevin, Hannah and Youngerman, Rebecca and Hobbs, Lauren",
    "title": "geoBoundaries: A Global Database of Political Administrative Boundaries",
    "journal": "PLOS ONE",
    "year": "2020",
    "volume": "15",
    "number": "4",
    "pages": "e0231866",
    "doi": "10.1371/journal.pone.0231866",
    "url": "https://doi.org/10.1371/journal.pone.0231866",
  },
  "LehnerGrill2013HydroBASINS": {
    "entry_type": "article",
    "author": "Lehner, Bernhard and Grill, Gunther",
    "title": "Global River Hydrography and Network Routing: Baseline Data and New Approaches to Study the World's Large River Systems",
    "journal": "Hydrological Processes",
    "year": "2013",
    "volume": "27",
    "number": "15",
    "pages": "2171--2186",
    "doi": "10.1002/hyp.9740",
    "url": "https://doi.org/10.1002/hyp.9740",
  },
  "Weidmann2010CShapes": {
    "entry_type": "article",
    "author": "Weidmann, Nils B. and Kuse, Doreen and Gleditsch, Kristian Skrede",
    "title": "The Geography of the International System: The CShapes Dataset",
    "journal": "International Interactions",
    "year": "2010",
    "volume": "36",
    "number": "1",
    "pages": "86--106",
    "doi": "10.1080/03050620903554614",
    "url": "https://doi.org/10.1080/03050620903554614",
  },
  "Murdock1959Africa": {
    "entry_type": "book",
    "author": "Murdock, George Peter",
    "title": "Africa: Its Peoples and Their Culture History",
    "publisher": "McGraw-Hill",
    "year": "1959",
    "url": "https://archive.org/details/africaitspeoples00murd",
  },
  "Pleiades2024Africa": {
    "entry_type": "misc",
    "author": "Bagnall, Roger S. and Talbert, Richard J. A. and Elliott, Tom",
    "title": "Pleiades: A Gazetteer of Past Places",
    "publisher": "Ancient World Mapping Center and Institute for the Study of the Ancient World",
    "year": "2024",
    "url": "https://pleiades.stoa.org",
  },
  "BIRD2022P3K14C": {
    "entry_type": "article",
    "author": "Bird, Darcy and Miranda, Lux and Vander Linden, Marc and Robinson, Erick and Bocinsky, R. Kyle and Nicholson, Chris and Capriles, Jose M. and Finley, Judson Byrd and Gayo, Eugenia M. and Gil, Adolfo and d'Alpoim Guedes, Jade and Hoggarth, Julie A. and Kay, Andrea and Loftus, Emma and Loftus, Sean and Mitchell, Peter and Mueller, Natalia and Neme, Gustavo and Peralta, Eva and Freeman, Jacob",
    "title": "p3k14c, a Synthetic Global Database of Archaeological Radiocarbon Dates",
    "journal": "Scientific Data",
    "year": "2022",
    "volume": "9",
    "pages": "27",
    "doi": "10.1038/s41597-022-01118-7",
    "url": "https://doi.org/10.1038/s41597-022-01118-7",
  },
  "Hinz2023XRONOS": {
    "entry_type": "misc",
    "author": "Hinz, Martin and Roe, Joe",
    "title": "XRONOS: Open Chronological Data Infrastructure for Archaeology",
    "publisher": "University of Bern",
    "year": "2023",
    "url": "https://xronos.ch",
  },
  "Kandel2023ROAD": {
    "entry_type": "article",
    "author": "Kandel, Andrew W. and Sommer, Christian and Kanaeva, Zara and Bolus, Michael and Bruch, Angela A. and Groth, Claudia and Haidle, Miriam N. and Hertler, Christine and Heusner, Johannes and Malina, Maria and Markert, Michael and Conard, Nicholas J.",
    "title": "The ROCEEH Out of Africa Database (ROAD): A Large-Scale Research Database Serves as an Indispensable Tool for Human Evolutionary Studies",
    "journal": "PLOS ONE",
    "year": "2023",
    "volume": "18",
    "number": "8",
    "pages": "e0289513",
    "doi": "10.1371/journal.pone.0289513",
    "url": "https://doi.org/10.1371/journal.pone.0289513",
  },
  "Phillipson2005AfricanArch": {
    "entry_type": "book",
    "author": "Phillipson, David W.",
    "title": "African Archaeology",
    "publisher": "Cambridge University Press",
    "year": "2005",
    "doi": "10.1017/CBO9780511800313",
    "url": "https://doi.org/10.1017/CBO9780511800313",
  },
  "Mitchell2002SouthernAfrica": {
    "entry_type": "book",
    "author": "Mitchell, Peter",
    "title": "The Archaeology of Southern Africa",
    "publisher": "Cambridge University Press",
    "year": "2002",
    "url": "https://www.cambridge.org/9780521794077",
  },
  "Besse2020OSAAR": {
    "entry_type": "misc",
    "author": "Mayor, Anne and Huysecom, Eric and Ozainne, Sylvain",
    "title": "Online West African Archaeological Register (OSAAR / IFAN Dakar Chronometric Synthesis)",
    "publisher": "Universite de Geneve and IFAN Cheikh Anta Diop",
    "year": "2020",
    "url": "https://www.unige.ch/sciences/terre/osaar",
  },
  "Edwards2004NubianPast": {
    "entry_type": "book",
    "author": "Edwards, David N.",
    "title": "The Nubian Past: An Archaeology of the Sudan",
    "publisher": "Routledge",
    "year": "2004",
    "doi": "10.4324/9780203482766",
    "url": "https://doi.org/10.4324/9780203482766",
  },
  "Adams1977Nubia": {
    "entry_type": "book",
    "author": "Adams, William Y.",
    "title": "Nubia: Corridor to Africa",
    "publisher": "Princeton University Press",
    "year": "1977",
    "url": "https://archive.org/details/nubiacorridortoa00adam",
  },
  "Spaulding1985HeroicAge": {
    "entry_type": "book",
    "author": "Spaulding, Jay",
    "title": "The Heroic Age in Sinnar",
    "publisher": "Michigan State University African Studies Center",
    "year": "1985",
    "url": "https://archive.org/details/heroicageinsinna0000spau",
  },
  "Fattovich2010Aksum": {
    "entry_type": "article",
    "author": "Fattovich, Rodolfo",
    "title": "The Development of Ancient States in the Northern Horn of Africa, c. 3000 BC--AD 1000: An Archaeological Outline",
    "journal": "Journal of World Prehistory",
    "year": "2010",
    "volume": "23",
    "number": "3",
    "pages": "145--175",
    "doi": "10.1007/s10963-010-9035-1",
    "url": "https://doi.org/10.1007/s10963-010-9035-1",
  },
  "ARCCH2020EthiopiaInventory": {
    "entry_type": "misc",
    "author": "{Authority for Research and Conservation of Cultural Heritage (ARCCH)}",
    "title": "National Archaeological and Architectural Heritage Inventory of Ethiopia",
    "publisher": "Ministry of Culture and Tourism, Addis Ababa",
    "year": "2020",
    "url": "https://whc.unesco.org/en/statesparties/et",
  },
  "Pankhurst1982EthiopianTowns": {
    "entry_type": "book",
    "author": "Pankhurst, Richard",
    "title": "History of Ethiopian Towns from the Middle Ages to the Early Nineteenth Century",
    "publisher": "Franz Steiner Verlag",
    "year": "1982",
    "url": "https://archive.org/details/historyofethiopi0000pank",
  },
  "McIntosh1995JenneJeno": {
    "entry_type": "book",
    "author": "McIntosh, Susan Keech",
    "title": "Excavations at Jenne-Jeno, Hambarketolo, and Kaniana (Inland Niger Delta, Mali): The 1981 Season",
    "publisher": "University of California Press",
    "year": "1995",
    "url": "https://escholarship.org/uc/item/56c0g7f8",
  },
  "Connah2001AfricanCivilizations": {
    "entry_type": "book",
    "author": "Connah, Graham",
    "title": "African Civilizations: An Archaeological Perspective",
    "publisher": "Cambridge University Press",
    "year": "2001",
    "doi": "10.1017/CBO9780511800245",
    "url": "https://doi.org/10.1017/CBO9780511800245",
  },
  "Bostoen2018BantuFirst": {
    "entry_type": "article",
    "author": "Bostoen, Koen and Clist, Bernard and Doumenge, Charles and Grollemund, Rebecca and Hombert, Jean-Marie and Muluwa, Joseph Koni and Maley, Jean",
    "title": "Middle to Late Holocene Paleoclimatic Change and the Early Bantu Expansion in the Rain Forests of Western Central Africa",
    "journal": "Current Anthropology",
    "year": "2015",
    "volume": "56",
    "number": "3",
    "pages": "354--384",
    "doi": "10.1086/681436",
    "url": "https://doi.org/10.1086/681436",
  },
  "Cornelissen2016RMCA": {
    "entry_type": "misc",
    "author": "{Royal Museum for Central Africa (RMCA Tervuren)}",
    "title": "Archive of Central African Archaeological Sites and Radiocarbon Records (ADRAC / BantuFirst)",
    "publisher": "Royal Museum for Central Africa, Tervuren",
    "year": "2023",
    "url": "https://www.africamuseum.be/en/research/discover/projects/bantufirst",
  },
  "Thornton1977KongoDemography": {
    "entry_type": "article",
    "author": "Thornton, John K.",
    "title": "Demography and History in the Kingdom of Kongo, 1550--1750",
    "journal": "The Journal of African History",
    "year": "1977",
    "volume": "18",
    "number": "4",
    "pages": "507--530",
    "doi": "10.1017/S0021853700015693",
    "url": "https://doi.org/10.1017/S0021853700015693",
  },
  "Law1977OyoEmpire": {
    "entry_type": "book",
    "author": "Law, Robin",
    "title": "The Oyo Empire, c. 1600--c. 1836: A West African Imperialism in the Era of the Atlantic Slave Trade",
    "publisher": "Clarendon Press",
    "year": "1977",
    "url": "https://archive.org/details/oyoempirec1600c10000lawr",
  },
  "Curtin1969AtlanticCensus": {
    "entry_type": "book",
    "author": "Curtin, Philip D.",
    "title": "The Atlantic Slave Trade: A Census",
    "publisher": "University of Wisconsin Press",
    "year": "1969",
    "url": "https://archive.org/details/atlanticslavetra00curt",
  },
  "Lovejoy2012Transformations": {
    "entry_type": "book",
    "author": "Lovejoy, Paul E.",
    "title": "Transformations in Slavery: A History of Slavery in Africa",
    "publisher": "Cambridge University Press",
    "year": "2011",
    "doi": "10.1017/CBO9781139014946",
    "url": "https://doi.org/10.1017/CBO9781139014946",
  },
  "Last1967SokotoCaliphate": {
    "entry_type": "book",
    "author": "Last, Murray",
    "title": "The Sokoto Caliphate",
    "publisher": "Longmans",
    "year": "1967",
    "url": "https://archive.org/details/sokotocaliphate0000last",
  },
  "Ofahey1980StateDarFur": {
    "entry_type": "book",
    "author": "O'Fahey, Rex S.",
    "title": "State and Society in Dar Fur",
    "publisher": "C. Hurst and Co.",
    "year": "1980",
    "url": "https://archive.org/details/statesocietyinda0000ofah",
  },
  "HortonMiddleton2000Swahili": {
    "entry_type": "book",
    "author": "Horton, Mark and Middleton, John",
    "title": "The Swahili: The Social Landscape of a Mercantile Society",
    "publisher": "Blackwell",
    "year": "2000",
    "url": "https://archive.org/details/swahilisociallan0000hort",
  },
  "Newitt1995Mozambique": {
    "entry_type": "book",
    "author": "Newitt, Malyn",
    "title": "A History of Mozambique",
    "publisher": "Indiana University Press",
    "year": "1995",
    "url": "https://archive.org/details/historyofmozambi0000newi",
  },
  "WynneJones2018SwahiliWorld": {
    "entry_type": "book",
    "author": "Wynne-Jones, Stephanie and LaViolette, Adria",
    "title": "The Swahili World",
    "publisher": "Routledge",
    "year": "2018",
    "doi": "10.4324/9781315691459",
    "url": "https://doi.org/10.4324/9781315691459",
  },
  "Shell1994ChildrenBondage": {
    "entry_type": "book",
    "author": "Shell, Robert C.-H.",
    "title": "Children of Bondage: A Social History of the Slave Society at the Cape of Good Hope, 1652--1838",
    "publisher": "Wesleyan University Press",
    "year": "1994",
    "url": "https://archive.org/details/childrenofbondag0000shel",
  },
  "ElphickGiliomee1989Shaping": {
    "entry_type": "book",
    "author": "Elphick, Richard and Giliomee, Hermann",
    "title": "The Shaping of South African Society, 1652--1840",
    "publisher": "Wesleyan University Press",
    "year": "1989",
    "url": "https://archive.org/details/shapingofsouthaf0000elph",
  },
  "Pikirayi2001ZimbabweCulture": {
    "entry_type": "book",
    "author": "Pikirayi, Innocent",
    "title": "The Zimbabwe Culture: Origins and Decline of Southern Zambezian States",
    "publisher": "AltaMira Press",
    "year": "2001",
    "url": "https://archive.org/details/zimbabwecultureo0000piki",
  },
  "SAHRIS2024SouthAfrica": {
    "entry_type": "misc",
    "author": "{South African Heritage Resources Agency}",
    "title": "South African Heritage Resources Information System (SAHRIS) Site and Radiocarbon Register",
    "publisher": "SAHRA, Cape Town",
    "year": "2024",
    "url": "https://sahris.sahra.org.za",
  },
  "NMMZ2022ZimbabweSites": {
    "entry_type": "misc",
    "author": "{National Museums and Monuments of Zimbabwe (NMMZ)}",
    "title": "National Archaeological Survey and Monuments Register of Zimbabwe",
    "publisher": "NMMZ, Harare",
    "year": "2022",
    "url": "https://whc.unesco.org/en/statesparties/zw",
  },
  "Allen1999SlavesFreedmen": {
    "entry_type": "book",
    "author": "Allen, Richard B.",
    "title": "Slaves, Freedmen, and Indentured Laborers in Colonial Mauritius",
    "publisher": "Cambridge University Press",
    "year": "1999",
    "url": "https://www.cambridge.org/9780521641258",
  },
  "Larson2000HistoryMemory": {
    "entry_type": "book",
    "author": "Larson, Pier M.",
    "title": "History and Memory in the Age of Enslavement: Becoming Merina in Highland Madagascar, 1770--1822",
    "publisher": "Heinemann",
    "year": "2000",
    "url": "https://archive.org/details/historymemoryina0000lars",
  },
  "ICM2020MadagascarAtlas": {
    "entry_type": "book",
    "author": "Wright, Henry T. and Rakotoarisoa, Jean-Aime",
    "title": "Archaeological Survey and Heritage Inventories of Madagascar (Institut de Civilisations -- Musee d'Art et d'Archeologie)",
    "publisher": "Universite d'Antananarivo",
    "year": "2003",
    "url": "https://www.univ-antananarivo.mg",
  },
  "AOFAnnuaire1936": {
    "entry_type": "book",
    "author": "{Gouvernement General de l'Afrique Occidentale Francaise}",
    "title": "Annuaire Statistique de l'Afrique Occidentale Francaise (1933--1936)",
    "publisher": "Imprimerie du Gouvernement General, Dakar",
    "year": "1937",
    "url": "https://gallica.bnf.fr",
  },
  "AEFAnnuaire1950": {
    "entry_type": "book",
    "author": "{Gouvernement General de l'Afrique Equatoriale Francaise}",
    "title": "Annuaire Statistique de l'Afrique Equatoriale Francaise, Volume 1 (1936--1950)",
    "publisher": "Haut-Commissariat de l'AEF, Brazzaville",
    "year": "1951",
    "url": "https://gallica.bnf.fr",
  },
  "Mitchell2007IHS": {
    "entry_type": "book",
    "author": "Mitchell, Brian R.",
    "title": "International Historical Statistics: Africa, Asia and Oceania, 1750--2005",
    "publisher": "Palgrave Macmillan",
    "year": "2007",
    "doi": "10.1057/9780230279872",
    "url": "https://doi.org/10.1057/9780230279872",
  },
  "CordellGregory1987AfricanPop": {
    "entry_type": "book",
    "author": "Cordell, Dennis D. and Gregory, Joel W.",
    "title": "African Population and Capitalism: Historical Perspectives",
    "publisher": "Westview Press",
    "year": "1987",
    "url": "https://archive.org/details/africanpopulatio0000unse",
  },
  "Cardinall1932GoldCoast": {
    "entry_type": "book",
    "author": "Cardinall, Allan Wolsey",
    "title": "The Gold Coast, 1931: A Review of Conditions in the Gold Coast in 1931 Based on Figures and Facts Collected by the Chief Census Officer",
    "publisher": "Government Printer, Accra",
    "year": "1932",
    "url": "https://archive.org/details/goldcoast1931rev00card",
  },
  "Kuczynski1948DemographicSurvey1": {
    "entry_type": "book",
    "author": "Kuczynski, Robert Rene",
    "title": "Demographic Survey of the British Colonial Empire, Volume I: West Africa",
    "publisher": "Oxford University Press",
    "year": "1948",
    "url": "https://archive.org/details/demographicsurve0001kucz",
  },
  "Kuczynski1949DemographicSurvey2": {
    "entry_type": "book",
    "author": "Kuczynski, Robert Rene",
    "title": "Demographic Survey of the British Colonial Empire, Volume II: East Africa, Central Africa and Southern Africa",
    "publisher": "Oxford University Press",
    "year": "1949",
    "url": "https://archive.org/details/demographicsurve0002kucz",
  },
  "FrankemaJerven2014AfricanPop": {
    "entry_type": "article",
    "author": "Frankema, Ewout and Jerven, Morten",
    "title": "Writing History Backwards or Sideways: Towards a Consensus on African Population, 1850--2010",
    "journal": "The Economic History Review",
    "year": "2014",
    "volume": "67",
    "number": "4",
    "pages": "907--931",
    "doi": "10.1111/1468-0289.12041",
    "url": "https://doi.org/10.1111/1468-0289.12041",
  },
  "Manning2010AfricanPop": {
    "entry_type": "article",
    "author": "Manning, Patrick",
    "title": "African Population: Projections, 1850--1960",
    "journal": "African Economic History",
    "year": "2010",
    "volume": "38",
    "pages": "153--182",
    "url": "https://www.jstor.org/stable/23210042",
  },
  "Manning2014AfricanPop": {
    "entry_type": "article",
    "author": "Manning, Patrick",
    "title": "African Population, 1650--2000: Comparisons and Implications of New Estimates",
    "journal": "African Development History / Harvard University Weatherhead Center",
    "year": "2014",
    "url": "https://scholar.harvard.edu",
  },
  "Gouellain1975Douala": {
    "entry_type": "book",
    "author": "Gouellain, Rene",
    "title": "Douala: Ville et Histoire",
    "publisher": "Institut d'Ethnologie, Musee de l'Homme",
    "year": "1975",
    "url": "https://books.openedition.org",
  },
  "Angola1940Censo": {
    "entry_type": "book",
    "author": "{Reparticao Tecnica de Estatistica Geral de Angola}",
    "title": "II Recenseamento Geral da Populacao de Angola, 1940",
    "publisher": "Imprensa Nacional, Luanda",
    "year": "1941",
    "url": "https://www.ine.gov.ao",
  },
  "CongoBelge1958Enquete": {
    "entry_type": "book",
    "author": "{Gouvernement General du Congo Belge, Section Statistique}",
    "title": "Tableaux Generaux de la Demographie Congolaise: Enquete Demographique par Sondage 1955--1957",
    "publisher": "Direction de la Statistique, Leopoldville",
    "year": "1961",
    "url": "https://www.africamuseum.be",
  },
  "Sudan1956Census": {
    "entry_type": "book",
    "author": "{Republic of the Sudan, Department of Statistics}",
    "title": "First Population Census of Sudan, 1955/56: Final Report",
    "publisher": "Department of Statistics, Khartoum",
    "year": "1961",
    "url": "https://catalog.hathitrust.org",
  },
  "Pankhurst1968EconomicHistory": {
    "entry_type": "book",
    "author": "Pankhurst, Richard",
    "title": "Economic History of Ethiopia, 1800--1935",
    "publisher": "Haile Sellassie I University Press",
    "year": "1968",
    "url": "https://archive.org/details/economichistoryo0000pank",
  },
  "NMK2021KenyaSites": {
    "entry_type": "misc",
    "author": "{National Museums of Kenya (NMK)}",
    "title": "Kenya National Archaeological and Palaeontological Sites Inventory",
    "publisher": "National Museums of Kenya, Nairobi",
    "year": "2021",
    "url": "https://museums.or.ke",
  },
  "EastAfrica1948Census": {
    "entry_type": "book",
    "author": "{East African Statistical Department}",
    "title": "African Population of Kenya Colony and Protectorate, Tanganyika Territory and Uganda Protectorate: Geographical and Tribal Studies (1948 Census)",
    "publisher": "East Africa High Commission, Nairobi",
    "year": "1950",
    "url": "https://www.knbs.or.ke",
  },
  "Martin1961EastAfrica": {
    "entry_type": "article",
    "author": "Martin, C. J.",
    "title": "Population Census Estimates and Methods in British East Africa",
    "journal": "Essays on African Population",
    "year": "1961",
    "pages": "17--30",
    "url": "https://archive.org/details/essaysonafricanp0000barb",
  },
  "CASO1960FederationCensus": {
    "entry_type": "book",
    "author": "{Central African Statistical Office}",
    "title": "Census of Population 1956: Federation of Rhodesia and Nyasaland",
    "publisher": "Government Printer, Salisbury",
    "year": "1960",
    "url": "https://www.zimstat.co.zw",
  },
  "Mozambique1940Censo": {
    "entry_type": "book",
    "author": "{Reparticao Tecnica de Estatistica de Mocambique}",
    "title": "Censo da Populacao em 1940",
    "publisher": "Imprensa Nacional de Mocambique, Lourenco Marques",
    "year": "1942",
    "url": "https://www.ine.gov.mz",
  },
  "StatsSA2023Census2022": {
    "entry_type": "book",
    "author": "{Statistics South Africa}",
    "title": "Census 2022 Statistical Release P0301.4",
    "publisher": "Statistics South Africa, Pretoria",
    "year": "2023",
    "url": "https://www.statssa.gov.za",
  },
  "Simkins2011SouthAfrica": {
    "entry_type": "article",
    "author": "Simkins, Charles",
    "title": "South African Urbanization Dynamics, 1911--2011",
    "journal": "Development Southern Africa",
    "year": "2011",
    "volume": "28",
    "number": "5",
    "pages": "625--637",
    "doi": "10.1080/0376835X.2011.623915",
    "url": "https://doi.org/10.1080/0376835X.2011.623915",
  },
  "INSTAT2020MadagascarRGPH3": {
    "entry_type": "book",
    "author": "{Institut National de la Statistique (INSTAT Madagascar)}",
    "title": "Troisieme Recensement General de la Population et de l'Habitation (RGPH-3): Resultats Globaux",
    "publisher": "INSTAT, Antananarivo",
    "year": "2020",
    "url": "https://www.instat.mg",
  },
  "INSEE2023ReunionMayotte": {
    "entry_type": "misc",
    "author": "{Institut National de la Statistique et des Etudes Economiques (INSEE)}",
    "title": "Populations Legales des Communes de La Reunion et de Mayotte",
    "publisher": "INSEE, Paris",
    "year": "2023",
    "url": "https://www.insee.fr",
  },
  "StatsMauritius2023Census2022": {
    "entry_type": "book",
    "author": "{Statistics Mauritius}",
    "title": "2022 Housing and Population Census of the Republic of Mauritius",
    "publisher": "Ministry of Finance, Economic Planning and Development, Port Louis",
    "year": "2023",
    "url": "https://statsmauritius.govmu.org",
  },
  "ANSD2024SenegalRGPH5": {
    "entry_type": "book",
    "author": "{Agence Nationale de la Statistique et de la Demographie (ANSD)}",
    "title": "5e Recensement General de la Population et de l'Habitat (RGPH-5, 2023): Rapport Global",
    "publisher": "ANSD, Dakar",
    "year": "2024",
    "url": "https://www.ansd.sn",
  },
  "INSD2022BurkinaRGPH5": {
    "entry_type": "book",
    "author": "{Institut National de la Statistique et de la Demographie (INSD)}",
    "title": "Cinquieme Recensement General de la Population et de l'Habitation du Burkina Faso (RGPH 2019)",
    "publisher": "INSD, Ouagadougou",
    "year": "2022",
    "url": "https://www.insd.bf",
  },
  "INSTAT2023MaliRGPH5": {
    "entry_type": "book",
    "author": "{Institut National de la Statistique (INSTAT Mali)}",
    "title": "5e Recensement General de la Population et de l'Habitat (RGPH-5, 2022): Resultats Preliminaires",
    "publisher": "INSTAT, Bamako",
    "year": "2023",
    "url": "https://www.instat-mali.org",
  },
  "OECD2024Africapolis": {
    "entry_type": "misc",
    "author": "{OECD and Sahel and West Africa Club (SWAC)}",
    "title": "Africapolis: Urbanisation Dynamics in Africa (2024 Update)",
    "publisher": "OECD Publishing, Paris",
    "year": "2024",
    "url": "https://africapolis.org",
  },
  "NPC2010NigeriaCensus": {
    "entry_type": "book",
    "author": "{National Population Commission of Nigeria}",
    "title": "2006 Population and Housing Census of the Federal Republic of Nigeria: Priority Tables",
    "publisher": "National Population Commission, Abuja",
    "year": "2010",
    "url": "https://nationalpopulation.gov.ng",
  },
  "GSS2021GhanaPHC": {
    "entry_type": "book",
    "author": "{Ghana Statistical Service}",
    "title": "Ghana 2021 Population and Housing Census: General Report, Volume 3A",
    "publisher": "Ghana Statistical Service, Accra",
    "year": "2021",
    "url": "https://statsghana.gov.gh",
  },
  "INS2022CoteIvoireRGPH": {
    "entry_type": "book",
    "author": "{Institut National de la Statistique (INS Cote d'Ivoire)}",
    "title": "Recensement General de la Population et de l'Habitat (RGPH 2021): Resultats Globaux Definitifs",
    "publisher": "INS, Abidjan",
    "year": "2022",
    "url": "https://www.ins.ci",
  },
  "INE2016AngolaRGPH": {
    "entry_type": "book",
    "author": "{Instituto Nacional de Estatistica (INE Angola)}",
    "title": "Resultados Definitivos do Recenseamento Geral da Populacao e Habitacao de Angola 2014",
    "publisher": "INE, Luanda",
    "year": "2016",
    "url": "https://www.ine.gov.ao",
  },
  "BUCREP2010CameroonRGPH": {
    "entry_type": "book",
    "author": "{Bureau Central des Recensements et des Etudes de Population (BUCREP)}",
    "title": "3e Recensement General de la Population et de l'Habitat du Cameroun (RGPH 2005)",
    "publisher": "BUCREP, Yaounde",
    "year": "2010",
    "url": "https://www.bucrep.cm",
  },
  "CSA2010EthiopiaCensus": {
    "entry_type": "book",
    "author": "{Central Statistical Agency of Ethiopia}",
    "title": "The 2007 Population and Housing Census of Ethiopia: Statistical Report",
    "publisher": "Central Statistical Agency, Addis Ababa",
    "year": "2010",
    "url": "https://www.statsethiopia.gov.et",
  },
  "CBS2009SudanCensus": {
    "entry_type": "book",
    "author": "{Central Bureau of Statistics Sudan}",
    "title": "Fifth Population and Housing Census of Sudan, 2008",
    "publisher": "Central Bureau of Statistics, Khartoum",
    "year": "2009",
    "url": "https://cbs.gov.sd",
  },
  "KNBS2019KenyaCensus": {
    "entry_type": "book",
    "author": "{Kenya National Bureau of Statistics (KNBS)}",
    "title": "2019 Kenya Population and Housing Census, Volume I: Population by County and Sub-County",
    "publisher": "KNBS, Nairobi",
    "year": "2019",
    "url": "https://www.knbs.or.ke",
  },
  "NBSTanzania2022Census": {
    "entry_type": "book",
    "author": "{National Bureau of Statistics (Tanzania) and Office of Chief Government Statistician (Zanzibar)}",
    "title": "2022 Population and Housing Census: Administrative Units Population Distribution Report",
    "publisher": "NBS, Dodoma",
    "year": "2022",
    "url": "https://www.nbs.go.tz",
  },
  "UBOS2024UgandaCensus": {
    "entry_type": "book",
    "author": "{Uganda Bureau of Statistics (UBOS)}",
    "title": "National Population and Housing Census 2024: Final Report",
    "publisher": "UBOS, Kampala",
    "year": "2024",
    "url": "https://www.ubos.org",
  },
  "ZIMSTAT2023ZimbabweCensus": {
    "entry_type": "book",
    "author": "{Zimbabwe National Statistics Agency (ZIMSTAT)}",
    "title": "2022 Population and Housing Census: Preliminary and Provincial Reports",
    "publisher": "ZIMSTAT, Harare",
    "year": "2023",
    "url": "https://www.zimstat.co.zw",
  },
  "INEMozambique2019RGPH": {
    "entry_type": "book",
    "author": "{Instituto Nacional de Estatistica (INE Mozambique)}",
    "title": "IV Recenseamento Geral da Populacao e Habitacao 2017: Resultados Definitivos",
    "publisher": "INE, Maputo",
    "year": "2019",
    "url": "https://www.ine.gov.mz",
  },
  "ZamStats2023ZambiaCensus": {
    "entry_type": "book",
    "author": "{Zambia Statistics Agency (ZamStats)}",
    "title": "2022 Census of Population and Housing: Summary Report",
    "publisher": "ZamStats, Lusaka",
    "year": "2023",
    "url": "https://www.zamstats.gov.zm",
  },
  "NSOMalawi2019Census": {
    "entry_type": "book",
    "author": "{National Statistical Office of Malawi}",
    "title": "2018 Malawi Population and Housing Census: Main Report",
    "publisher": "National Statistical Office, Zomba",
    "year": "2019",
    "url": "https://www.nsomalawi.mw",
  },
  "NSA2024NamibiaCensus": {
    "entry_type": "book",
    "author": "{Namibia Statistics Agency}",
    "title": "2023 Population and Housing Census: Preliminary Report",
    "publisher": "Namibia Statistics Agency, Windhoek",
    "year": "2024",
    "url": "https://nsa.org.na",
  },
  "StatsBotswana2022Census": {
    "entry_type": "book",
    "author": "{Statistics Botswana}",
    "title": "2022 Population and Housing Census: Population of Cities, Towns and Villages",
    "publisher": "Statistics Botswana, Gaborone",
    "year": "2022",
    "url": "https://www.statsbots.org.bw",
  },
}

# Root-only macro synthesis entries (strictly banned in all 23 sub-chapters!)
ROOT_MACRO_BIB = {
  "McEvedy1978": {
    "entry_type": "book",
    "author": "McEvedy, Colin and Jones, Richard",
    "title": "Atlas of World Population History",
    "publisher": "Penguin Books",
    "year": "1978",
    "url": "https://archive.org/details/atlasofworldpopu0000mcev",
  },
  "KleinGoldewijk2023": {
    "entry_type": "article",
    "author": "Klein Goldewijk, Kees and Beusen, Arthur and Doelman, Jonathan and Stehfest, Elke",
    "title": "Anthropogenic Land Use Estimates for the Holocene -- HYDE 3.3",
    "journal": "Earth System Science Data",
    "year": "2023",
    "volume": "15",
    "pages": "1--28",
    "doi": "10.5194/essd-9-927-2017",
    "url": "https://doi.org/10.5194/essd-9-927-2017",
  },
  "Kaplan2011KK10": {
    "entry_type": "article",
    "author": "Kaplan, Jed O. and Krumhardt, Kristen M. and Ellis, Erle C. and Ruddiman, William F. and Lemmen, Carsten and Klein Goldewijk, Kees",
    "title": "Holocene Carbon Emissions as a Result of Anthropogenic Land Cover Change",
    "journal": "The Holocene",
    "year": "2011",
    "volume": "21",
    "number": "5",
    "pages": "775--791",
    "doi": "10.1177/0959683610386983",
    "url": "https://doi.org/10.1177/0959683610386983",
  },
  "PaciorekSchervish2006": {
    "entry_type": "article",
    "author": "Paciorek, Christopher J. and Schervish, Mark J.",
    "title": "Spatial Modelling Using a New Class of Nonstationary Covariance Functions",
    "journal": "Environmetrics",
    "year": "2006",
    "volume": "17",
    "number": "5",
    "pages": "483--506",
    "doi": "10.1002/env.785",
    "url": "https://doi.org/10.1002/env.785",
  },
}

CHAPTER_EXTRA_REFS = {
  "prehistoric_ssa": ["Runfola2020GeoBoundaries", "LehnerGrill2013HydroBASINS", "BIRD2022P3K14C", "Hinz2023XRONOS", "Phillipson2005AfricanArch", "Besse2020OSAAR"],
  "ancient_mediaeval_nubia": ["Runfola2020GeoBoundaries", "Edwards2004NubianPast", "Adams1977Nubia", "Spaulding1985HeroicAge", "Pleiades2024Africa"],
  "ancient_horn_africa": ["Runfola2020GeoBoundaries", "Fattovich2010Aksum", "ARCCH2020EthiopiaInventory", "Pankhurst1982EthiopianTowns", "Pleiades2024Africa"],
  "early_west_africa_sahel": ["Runfola2020GeoBoundaries", "Besse2020OSAAR", "McIntosh1995JenneJeno", "Connah2001AfricanCivilizations", "Hinz2023XRONOS"],
  "bantu_expansion_africa": ["Runfola2020GeoBoundaries", "Bostoen2018BantuFirst", "Cornelissen2016RMCA", "Connah2001AfricanCivilizations", "BIRD2022P3K14C"],
  "atlantic_west_equatoria": ["Runfola2020GeoBoundaries", "Thornton1977KongoDemography", "Law1977OyoEmpire", "Curtin1969AtlanticCensus", "Lovejoy2012Transformations"],
  "early_modern_sahel_sudan": ["Runfola2020GeoBoundaries", "Last1967SokotoCaliphate", "Ofahey1980StateDarFur", "Spaulding1985HeroicAge", "Lovejoy2012Transformations"],
  "early_modern_east_africa": ["Runfola2020GeoBoundaries", "HortonMiddleton2000Swahili", "Newitt1995Mozambique", "WynneJones2018SwahiliWorld", "NMK2021KenyaSites"],
  "precolonial_south_africa": ["Runfola2020GeoBoundaries", "Shell1994ChildrenBondage", "ElphickGiliomee1989Shaping", "Pikirayi2001ZimbabweCulture", "SAHRIS2024SouthAfrica", "NMMZ2022ZimbabweSites"],
  "early_african_islands": ["Runfola2020GeoBoundaries", "Allen1999SlavesFreedmen", "Larson2000HistoryMemory", "ICM2020MadagascarAtlas"],
  "colonial_west_sahel": ["Runfola2020GeoBoundaries", "AOFAnnuaire1936", "Kuczynski1948DemographicSurvey1", "Cardinall1932GoldCoast", "FrankemaJerven2014AfricanPop"],
  "colonial_equatoria_congo": ["Runfola2020GeoBoundaries", "AEFAnnuaire1950", "Angola1940Censo", "CongoBelge1958Enquete", "Gouellain1975Douala", "Cornelissen2016RMCA"],
  "colonial_horn_sudan": ["Runfola2020GeoBoundaries", "Sudan1956Census", "Pankhurst1968EconomicHistory", "Kuczynski1949DemographicSurvey2", "ARCCH2020EthiopiaInventory"],
  "colonial_east_africa": ["Runfola2020GeoBoundaries", "EastAfrica1948Census", "Martin1961EastAfrica", "Kuczynski1949DemographicSurvey2", "NMK2021KenyaSites"],
  "colonial_south_central": ["Runfola2020GeoBoundaries", "CASO1960FederationCensus", "Mozambique1940Censo", "Mitchell2007IHS", "CordellGregory1987AfricanPop", "NMMZ2022ZimbabweSites"],
  "modern_southern_africa": ["Runfola2020GeoBoundaries", "StatsSA2023Census2022", "Simkins2011SouthAfrica", "NSA2024NamibiaCensus", "StatsBotswana2022Census", "SAHRIS2024SouthAfrica"],
  "modern_african_islands": ["Runfola2020GeoBoundaries", "INSTAT2020MadagascarRGPH3", "INSEE2023ReunionMayotte", "StatsMauritius2023Census2022", "ICM2020MadagascarAtlas"],
  "postcolonial_sahel": ["Runfola2020GeoBoundaries", "ANSD2024SenegalRGPH5", "INSD2022BurkinaRGPH5", "INSTAT2023MaliRGPH5", "OECD2024Africapolis"],
  "postcolonial_west_africa": ["Runfola2020GeoBoundaries", "NPC2010NigeriaCensus", "GSS2021GhanaPHC", "INS2022CoteIvoireRGPH", "OECD2024Africapolis"],
  "postcolonial_congo_angola": ["Runfola2020GeoBoundaries", "INE2016AngolaRGPH", "BUCREP2010CameroonRGPH", "OECD2024Africapolis", "Cornelissen2016RMCA"],
  "postcolonial_horn_sudan": ["Runfola2020GeoBoundaries", "CSA2010EthiopiaCensus", "CBS2009SudanCensus", "OECD2024Africapolis", "ARCCH2020EthiopiaInventory"],
  "postcolonial_east_africa": ["Runfola2020GeoBoundaries", "KNBS2019KenyaCensus", "NBSTanzania2022Census", "UBOS2024UgandaCensus", "OECD2024Africapolis"],
  "postcolonial_south_central": ["Runfola2020GeoBoundaries", "ZIMSTAT2023ZimbabweCensus", "INEMozambique2019RGPH", "ZamStats2023ZambiaCensus", "NSOMalawi2019Census", "NMMZ2022ZimbabweSites"],
}


def sanitise_text (arg0_text):
  """Strips HTML tags/entities, corrupted Unicode, and non-Karla punctuation cleanly."""
  s = str(arg0_text or "").strip()
  s = html.unescape(s)
  s = re.sub(r"<[^>]+>", "", s)
  s = s.replace("\ufffd", "")
  s = s.replace("\u2010", "-").replace("\u2011", "-").replace("\u2212", "-")
  s = s.replace("\u2013", "--").replace("\u2014", "---")
  s = s.replace("\u00a0", " ")
  s = re.sub(r"\s+", " ", s).strip()
  # Remove any residual non-Latin/non-punctuation glyphs outside Karla Latin Extended-B
  cleaned = []
  for ch in s:
    cp = ord(ch)
    if cp <= 0x024F or ch in "\u2018\u2019\u201c\u201d\u2022\u00b7\u20ac\u00a3\u00b0\u00b1\u00d7\u00f7":
      cleaned.append(ch)
    else:
      cleaned.append("-")
  return "".join(cleaned)


def bib_escape (arg0_text):
  """Escapes BibTeX special characters after full HTML/Unicode sanitisation."""
  s = sanitise_text(arg0_text)
  s = s.replace("\\", "")
  s = s.replace("{", "").replace("}", "")
  s = s.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#").replace("_", r"\_")
  return s


def format_authors_bib (arg0_authors):
  """Formats author list into clean BibTeX string."""
  if isinstance(arg0_authors, str):
    return bib_escape(arg0_authors)
  cleaned = []
  for a in (arg0_authors or []):
    sa = bib_escape(a)
    if sa:
      # Protect corporate authors with braces if multi-word institutional name
      low = sa.lower()
      if any(w in low for w in ("bank", "office", "bureau", "statistics", "government", "commission", "service", "agency", "ministry", "societe", "conference", "protectorate", "territory", "division", "department", "register")):
        cleaned.append(f"{{{sa}}}")
      else:
        cleaned.append(sa)
  return " and ".join(cleaned) if cleaned else "{Archival Source}"


def normalise_link (arg0_doi, arg1_url):
  """Normalises DOI and enforces https:// URLs."""
  doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", str(arg0_doi or "").strip())
  url = str(arg1_url or "").strip()
  if url.startswith("http://"):
    url = "https://" + url[7:]
  if not url and doi:
    url = f"https://doi.org/{doi}"
  return doi, url


def make_bib_block (arg0_key, arg1_item):
  """Renders a single verified BibTeX entry block."""
  etype = str(arg1_item.get("entry_type") or "article").strip().lower()
  if etype not in ("article", "book", "incollection", "inproceedings", "techreport", "misc", "phdthesis"):
    etype = "article"
  key = re.sub(r"[^A-Za-z0-9_:-]", "", str(arg0_key))
  lines = [f"@{etype}{{{key},"]

  def add_field (arg0_fname, arg1_val, arg2_raw=False):
    val = str(arg1_val or "").strip()
    if not val:
      return
    lines.append(f"  {arg0_fname} = {{{val if arg2_raw else bib_escape(val)}}},")

  author_str = format_authors_bib(arg1_item.get("authors") or arg1_item.get("author"))
  lines.append(f"  author = {{{author_str}}},")
  add_field("title", arg1_item.get("title") or "Untitled")
  add_field("year", arg1_item.get("year") or "", True)

  pub = str(arg1_item.get("publisher_or_journal") or arg1_item.get("journal") or arg1_item.get("publisher") or "").strip()
  booktitle = str(arg1_item.get("booktitle") or "").strip()
  if etype == "article":
    if pub:
      add_field("journal", pub)
  elif etype == "incollection":
    if booktitle:
      add_field("booktitle", booktitle)
    if pub:
      add_field("publisher", pub)
  elif etype in ("techreport", "phdthesis"):
    if pub:
      add_field("institution", pub)
  else:
    if pub:
      add_field("publisher", pub)

  if arg1_item.get("volume"):
    add_field("volume", arg1_item.get("volume"), True)
  if arg1_item.get("number"):
    add_field("number", arg1_item.get("number"), True)
  if arg1_item.get("pages"):
    add_field("pages", arg1_item.get("pages"), True)

  doi, url = normalise_link(arg1_item.get("doi"), arg1_item.get("url"))
  if doi:
    add_field("doi", doi, True)
  if url:
    add_field("url", url, True)

  lines.append("}")
  return "\n".join(lines)


def verify_bib_stats (arg0_bib_path, arg1_is_subchapter=True):
  """Computes exact D3 calibre metrics on a written .bib file."""
  txt = arg0_bib_path.read_text(encoding="utf-8")
  if arg1_is_subchapter and BANNED_SUBCHAPTER_RE.search(txt):
    hit = BANNED_SUBCHAPTER_RE.search(txt).group(0)
    raise ValueError(f"Banned fallback token `{hit}` found in {arg0_bib_path}")
  if "<" in txt or "&amp;" in txt or "&nbsp;" in txt or "\ufffd" in txt:
    raise ValueError(f"Unsanitised HTML or U+FFFD found in {arg0_bib_path}")

  entries = re.split(r"^\s*@[A-Za-z]+\s*\{", txt, flags=re.M)[1:]
  keys = []
  linked = 0
  zenodo = 0
  crowd = 0
  pub_c = Counter()
  auth_c = Counter()
  link_re = re.compile(r"\b(?:doi|url)\s*=\s*[\{\"](?:10\.|https://)", re.I)
  pub_re = re.compile(r"\b(?:journal|publisher|institution|booktitle)\s*=\s*[\{\"]([^}\"]+)", re.I)
  auth_re = re.compile(r"\bauthor\s*=\s*[\{\"]([^}\"]+)", re.I)
  url_re = re.compile(r"https?://(?:www\.)?([A-Za-z0-9.-]+\.[A-Za-z]{2,})", re.I)

  parsed_list = []
  for ent in entries:
    km = re.match(r"^\s*([^,\s]+)", ent)
    k = km.group(1).strip() if km else ""
    keys.append(k)
    if link_re.search(ent):
      linked += 1
    if re.search(r"zenodo\.org|10\.5281/zenodo|\bzenodo\b", ent, re.I):
      zenodo += 1
    if re.search(r"wikidata\.org|openstreetmap\.org|overpass-api|geonames\.org|wikipedia\.org", ent, re.I):
      crowd += 1
    pm = pub_re.search(ent)
    dom = pm.group(1).strip().lower()[:40] if pm else (url_re.search(ent).group(1).lower() if url_re.search(ent) else "")
    if dom:
      pub_c[dom] += 1
    am = auth_re.search(ent)
    if am:
      first = re.split(r"\band\b", am.group(1), flags=re.I)[0].replace("{", "").replace("}", "").strip()
      surname = first.split(",")[0].strip().lower() if "," in first else (first.split()[-1].lower() if first.split() else "")
      if len(surname) >= 3:
        auth_c[surname] += 1

    def get_field (arg0_fn):
      fm = re.search(rf"\b{arg0_fn}\s*=\s*\{{((?:[^{{}}]|\{{[^}}]*\}})*)\}}", ent, flags=re.I)
      return fm.group(1).replace("{", "").replace("}", "").strip() if fm else ""

    parsed_list.append({
      "key": k,
      "author": get_field("author")[:80],
      "year": get_field("year"),
      "title": get_field("title")[:130],
      "journal_or_publisher": get_field("journal") or get_field("publisher") or get_field("institution") or get_field("booktitle"),
      "doi": get_field("doi"),
      "url": get_field("url"),
    })

  n = len(entries)
  top_auth, top_ac = auth_c.most_common(1)[0] if auth_c else ("", 0)
  top_pub, top_pc = pub_c.most_common(1)[0] if pub_c else ("", 0)
  stats = {
    "total_keys": n,
    "unique_keys": len(set(keys)),
    "linked_entries": linked,
    "linked_pct": round(100.0 * linked / max(1, n), 1),
    "distinct_publishers": len(pub_c),
    "top_author": top_auth,
    "max_author_share": round(top_ac / max(1, n), 4),
    "top_publisher": top_pub,
    "max_publisher_share": round(top_pc / max(1, n), 4),
    "zenodo_count": zenodo,
    "crowd_count": crowd,
  }
  return stats, parsed_list


def compute_row_cell_areas_km2 ():
  """Computes exact spherical-trapezoid cell area (km^2) per latitude row on 4320x2160 grid."""
  lats_n = np.linspace(90.0, -90.0, GRID_H + 1)
  sin_n = np.sin(np.radians(lats_n[:-1]))
  sin_s = np.sin(np.radians(lats_n[1:]))
  return (R_EARTH_KM ** 2) * CELL_LON_RAD * np.abs(sin_n - sin_s)


def decode_velk_png (arg0_path):
  """Decodes a 4320x2160 big-endian float32 RGBA population raster into inhabitants per cell."""
  arr = np.ascontiguousarray(Image.open(arg0_path).convert("RGBA"), dtype=np.uint8)
  vals = arr.view(">f4").reshape(arr.shape[:2])
  return np.where(np.isfinite(vals) & (vals > 0.0) & (vals < 1e8), vals, 0.0).astype(np.float32)


def select_benchmark_years (arg0_hyde_years, arg1_domain):
  """Selects 6 to 14 well-spaced raster years spanning a chapter's temporal domain."""
  d0, d1 = int(arg1_domain[0]), int(arg1_domain[1])
  in_dom = sorted(y for y in arg0_hyde_years if d0 <= y <= d1)
  if not in_dom:
    return [min(arg0_hyde_years, key=lambda y: abs(y - d1))]
  if len(in_dom) <= 14:
    return in_dom
  idxs = np.linspace(0, len(in_dom) - 1, 14).round().astype(int)
  return sorted(set(in_dom[i] for i in idxs))


def compute_zipf_stats (arg0_peaks):
  """Computes OLS Pareto Zipf slope q and R^2 on log10(rank) vs log10(pop) when n >= 25."""
  pops = sorted([float(p) for p in arg0_peaks if float(p) > 0], reverse=True)
  n_all = len(pops)
  if n_all < 25:
    return {
      "n_with_pop": n_all,
      "fit_valid": False,
      "n_fit": 0,
      "slope": None,
      "zipf_q": None,
      "intercept": None,
      "r2": None,
      "full_slope": None,
      "full_zipf_q": None,
      "full_r2": None,
    }
  ranks = np.arange(1, n_all + 1, dtype=np.float64)
  pop_arr = np.asarray(pops, dtype=np.float64)

  n_fit = min(max(25, n_all // 2), 180)
  lx = np.log10(ranks[:n_fit])
  ly = np.log10(pop_arr[:n_fit])
  sl, ic = np.polyfit(lx, ly, 1)
  r2 = max(0.0, 1.0 - float(np.sum((ly - (sl * lx + ic)) ** 2)) / max(1e-12, float(np.sum((ly - np.mean(ly)) ** 2))))

  lx_f = np.log10(ranks)
  ly_f = np.log10(pop_arr)
  sl_f, ic_f = np.polyfit(lx_f, ly_f, 1)
  r2_f = max(0.0, 1.0 - float(np.sum((ly_f - (sl_f * lx_f + ic_f)) ** 2)) / max(1e-12, float(np.sum((ly_f - np.mean(ly_f)) ** 2))))

  return {
    "n_with_pop": n_all,
    "fit_valid": True,
    "n_fit": int(n_fit),
    "slope": round(float(sl), 4),
    "zipf_q": round(float(-sl), 4),
    "intercept": round(float(ic), 4),
    "r2": round(float(r2), 4),
    "full_slope": round(float(sl_f), 4),
    "full_zipf_q": round(float(-sl_f), 4),
    "full_r2": round(float(r2_f), 4),
  }


def classify_evidence_basis (arg0_sources, arg1_scope):
  """Produces a concise empirical evidence_basis tag plus verbatim source summary."""
  srcs = [str(x).strip() for x in (arg0_sources or []) if str(x).strip()]
  joined = " | ".join(srcs)
  low = joined.lower()
  tags = []
  if any(w in low for w in ("census", "rgph", "rgpl", "africapolis", "unsd", "insee", "statoids", "citypopulation")):
    tags.append("official_census_enumeration")
  if any(w in low for w in ("blue book", "annuaire", "recenseamento", "opgaaf", "colonial")):
    tags.append("colonial_administrative_record")
  if any(w in low for w in ("radiocarbon", "xronos", "p3k14c", "excavat", "archaeolog", "site", "road", "osaar", "bantufirst", "adrac")):
    tags.append("archaeological_radiocarbon_survey")
  if not tags:
    tags.append("historical_monograph_synthesis")
  return {
    "category": "+".join(tags),
    "scope": str(arg1_scope or "city_proper"),
    "primary_sources": srcs[:4],
  }


def select_subadmin_tables_for_chapter (arg0_stem, arg1_domain, arg2_enums, arg3_hgis_csv_rows):
  """Selects clean benchmark sub-administrative enumeration tables matching chapter countries and era."""
  meta = CHAPTER_METADATA[arg0_stem]
  d0, d1 = int(arg1_domain[0]), int(arg1_domain[1])
  iso_list = meta["iso3_codes"]
  tables = []

  def source_priority (arg0_src):
    sl = str(arg0_src or "").lower()
    if "wikidata" in sl:
      return 3
    if any(k in sl for k in ("citypopulation", "statoids", "mitchell", "blue book", "annuaire", "recenseamento", "census", "opgaaf", "insee", "campbell")):
      return 0
    return 1

  for iso in iso_list:
    iso_dict = arg2_enums.get(iso, {})
    if not iso_dict:
      continue
    # Select up to 2 best years inside [d0-10, d1+5] per priority country
    in_span = []
    for yk, rows in iso_dict.items():
      try:
        yi = int(yk)
      except Exception:
        continue
      if (d0 - 10) <= yi <= (d1 + 5) and rows:
        in_span.append((yi, rows))
    if not in_span:
      continue

    # Prefer non-Wikidata sources and well-spaced years (earliest + latest)
    in_span.sort(key=lambda t: (min(source_priority(r.get("source")) for r in t[1]), t[0]))
    non_wiki = [t for t in in_span if min(source_priority(r.get("source")) for r in t[1]) < 3]
    pool = non_wiki if non_wiki else in_span
    pool_sorted = sorted(pool, key=lambda t: t[0])
    chosen = [pool_sorted[0]]
    if len(pool_sorted) > 1 and pool_sorted[-1][0] != pool_sorted[0][0]:
      chosen.append(pool_sorted[-1])
    if len(pool_sorted) > 4:
      chosen.append(pool_sorted[len(pool_sorted) // 2])

    for yi, rows in sorted(chosen, key=lambda t: t[0]):
      # Deduplicate unit_name, drop Wikidata if official rows exist in same year
      has_non_wiki = any("wikidata" not in str(r.get("source", "")).lower() for r in rows)
      clean_rows = []
      seen_u = set()
      for r in sorted(rows, key=lambda x: (-float(x.get("population") or 0), str(x.get("unit_name") or ""))):
        if has_non_wiki and "wikidata" in str(r.get("source", "")).lower():
          continue
        uname = sanitise_text(r.get("unit_name") or "")
        pop = int(round(float(r.get("population") or 0)))
        if not uname or pop <= 0 or uname.lower() in seen_u:
          continue
        seen_u.add(uname.lower())
        clean_rows.append({
          "unit_name": uname,
          "population": pop,
          "admin_level": str(r.get("admin_level") or "ADM1"),
          "source": sanitise_text(r.get("source") or ""),
        })
      if clean_rows:
        tables.append({
          "polity_code": iso,
          "year": yi,
          "unit_count": len(clean_rows),
          "total_enumerated_pop": sum(r["population"] for r in clean_rows),
          "primary_source": clean_rows[0]["source"],
          "units": clean_rows[:25],
        })
    if len(tables) >= 14:
      break

  # Also include matching HGIS boundary regime units (useful especially for ancient/early-modern chapters)
  reg_prefixes = tuple(meta["hgis_regimes"])
  hgis_units = [
    r for r in arg3_hgis_csv_rows
    if r["regime"].startswith(reg_prefixes)
  ]
  # Sample up to 20 representative units across chapter countries or biophysical basins
  iso_set = set(iso_list)
  prio_hgis = [r for r in hgis_units if r["country"] in iso_set] or hgis_units
  return tables[:12], prio_hgis[:24]


def select_arf_evidence_for_chapter (arg0_stem, arg1_domain, arg2_arf):
  """Extracts non-banned Africa Research Files observations and tables relevant to a chapter."""
  meta = CHAPTER_METADATA[arg0_stem]
  d0, d1 = int(arg1_domain[0]), int(arg1_domain[1])
  regs = set(meta["arf_regions"])

  obs_out = []
  for it in arg2_arf.get("settlement_observations", []):
    blob = json.dumps(it, ensure_ascii=False).lower()
    if BANNED_SUBCHAPTER_RE.search(blob):
      continue
    if it.get("nicethi_region") not in regs:
      continue
    yr = it.get("year")
    if yr is not None:
      yi = int(yr)
      if not ((d0 - 250) <= yi <= (d1 + 100)):
        continue
    obs_out.append({
      "settlement_name": sanitise_text(it.get("settlement_name") or ""),
      "country_or_region": sanitise_text(it.get("country_or_region") or ""),
      "year": it.get("year"),
      "population": it.get("population"),
      "walled_area_ha": it.get("walled_area_ha"),
      "evidence_type": it.get("evidence_type"),
      "source_file": sanitise_text(it.get("source_file") or ""),
    })

  tables_out = []
  for tbl in arg2_arf.get("regional_population_tables", []):
    if tbl.get("cites_banned_compendium"):
      continue
    tblob = json.dumps(tbl, ensure_ascii=False)
    if BANNED_SUBCHAPTER_RE.search(tblob):
      continue
    tid = tbl.get("table_id", "")
    keep = False
    if "Manning_Table_4_1" in tid or "Frankema_Jerven_2014_Table_10" in tid:
      keep = d1 >= 1700
    elif "Manning_Table_10_8" in tid:
      keep = d1 >= 1800 and d0 <= 1960
    elif "Nigeria" in tid:
      keep = "NGA" in meta["iso3_codes"] and d1 >= 1900
    elif "Ghana" in tid:
      keep = "GHA" in meta["iso3_codes"] and d1 >= 1870
    elif "Zimbabwe" in tid:
      keep = "ZWE" in meta["iso3_codes"] and d1 >= 1600
    elif "Cape_Khoikhoi" in tid:
      keep = "ZAF_CAPE" in meta["iso3_codes"] and d0 <= 1800
    elif "Precolonial_African_Urban_Density" in tid:
      keep = d0 <= 1885 and d1 >= -500
    if keep:
      tables_out.append(tbl)

  return obs_out[:35], tables_out


def main ():
  # 1. Copy template assets into NICETHI root
  for fn in ("intellte.cls", "crd-mla-numeric.csl", "crd_logo.png"):
    src = TEMPLATE_DIR / fn
    dst = NICETHI_DIR / fn
    if src.exists():
      shutil.copy2(src, dst)
  print("[1/4] Copied template assets (intellte.cls, crd-mla-numeric.csl, crd_logo.png) to NICETHI root.", flush=True)

  # 2. Load core inputs
  manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
  gaz_cfg = json.loads(GAZ_PATH.read_text(encoding="utf-8"))
  masks_cfg = json.loads(MASKS_PATH.read_text(encoding="utf-8"))
  gaz_summary = json.loads(GAZ_SUMMARY_PATH.read_text(encoding="utf-8"))
  sub_enums = json.loads(SUBADMIN_ENUM_PATH.read_text(encoding="utf-8"))
  sub_audit = json.loads(SUBADMIN_AUDIT_PATH.read_text(encoding="utf-8"))
  krig_diag = json.loads(KRIG_DIAG_PATH.read_text(encoding="utf-8"))
  geo_meta = json.loads(GEO_META_PATH.read_text(encoding="utf-8"))
  arf_ev = json.loads(ARF_EVIDENCE_PATH.read_text(encoding="utf-8"))

  gaz_sum_by_key = {c["chapter_key"]: c for c in gaz_summary.get("chapters", [])}
  hgis_csv_rows = []
  with open(SUBADMIN_CSV_PATH, encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
      hgis_csv_rows.append({
        "regime": r["regime"],
        "year_start": int(r["year_start"]),
        "year_end": int(r["year_end"]),
        "country": r["country"],
        "unit_code": r["unit_code"],
        "unit_name": r["unit_name"],
        "area_km2": round(float(r["area_km2"]), 1),
        "source": r["source"],
      })

  papers_by_stem = defaultdict(list)
  for it in manifest["papers"]:
    papers_by_stem[it["chapter_stem"]].append(it)

  # 3. Build all 23 chapter .bib files + verify calibre
  print("[2/4] Building and verifying BibTeX files for all 23 chapters + root...", flush=True)
  ch_bib_info = {}
  root_chapter_sample_blocks = {}

  for ch in gaz_cfg["gazetteers"]:
    stem = ch["key"]
    sett_path = SVEA_ROOT / ch["path"]
    ch_dir = sett_path.parent
    bib_path = ch_dir / f"{stem}_literature_review.bib"
    assert len(bib_path.name) <= 72, f"Filename exceeds 72 chars: {bib_path.name}"

    seen_keys = set()
    blocks = []
    for raw_item in papers_by_stem.get(stem, []):
      item = dict(raw_item)
      ov = MANIFEST_OVERRIDES.get(item["filename"])
      if ov:
        item.update(ov)
      base_key = re.sub(r"[^A-Za-z0-9_:-]", "", str(item.get("cite_key") or item.get("suggested_bib_key") or "Source2020"))
      if not base_key or not base_key[0].isalpha():
        base_key = "Ref" + base_key
      key = base_key
      suffix = 2
      while key in seen_keys:
        key = f"{base_key}_{suffix}"
        suffix += 1
      seen_keys.add(key)
      blk = make_bib_block(key, item)
      blocks.append(blk)
      if stem not in root_chapter_sample_blocks and len(blocks) <= 2:
        root_chapter_sample_blocks[key] = blk
      elif len(blocks) == 1 and len(root_chapter_sample_blocks) < 35:
        root_chapter_sample_blocks[key] = blk

    for rkey in CHAPTER_EXTRA_REFS.get(stem, ["Runfola2020GeoBoundaries"]):
      if rkey in seen_keys:
        continue
      seen_keys.add(rkey)
      blocks.append(make_bib_block(rkey, CORE_REGIONAL_BIB[rkey]))

    bib_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    b_stats, b_entries = verify_bib_stats(bib_path, arg1_is_subchapter=True)
    if b_stats["unique_keys"] < 22:
      raise RuntimeError(f"[{stem}] Only {b_stats['unique_keys']} keys (< 22)")
    if b_stats["linked_pct"] < 90.0:
      raise RuntimeError(f"[{stem}] DOI/URL coverage {b_stats['linked_pct']}% (< 90%)")
    if b_stats["distinct_publishers"] < 6:
      raise RuntimeError(f"[{stem}] Only {b_stats['distinct_publishers']} publishers (< 6)")
    if b_stats["max_author_share"] > 0.25:
      raise RuntimeError(f"[{stem}] Max author share {b_stats['max_author_share']} > 0.25 ({b_stats['top_author']})")
    if b_stats["max_publisher_share"] > 0.25:
      raise RuntimeError(f"[{stem}] Max publisher share {b_stats['max_publisher_share']} > 0.25 ({b_stats['top_publisher']})")
    ch_bib_info[stem] = (b_stats, b_entries)

  # Build root studies_on_population.bib
  root_bib_blocks = {}
  for rk, ritem in ROOT_MACRO_BIB.items():
    root_bib_blocks[rk] = make_bib_block(rk, ritem)
  for ck, citem in CORE_REGIONAL_BIB.items():
    root_bib_blocks[ck] = make_bib_block(ck, citem)
  for sk, sblk in root_chapter_sample_blocks.items():
    if sk not in root_bib_blocks:
      root_bib_blocks[sk] = sblk
  root_bib_path = NICETHI_DIR / "studies_on_population.bib"
  root_bib_path.write_text("\n\n".join(root_bib_blocks.values()) + "\n", encoding="utf-8")
  root_bib_stats, root_bib_entries = verify_bib_stats(root_bib_path, arg1_is_subchapter=False)
  print(f"  [OK] 23 chapter .bib files + root studies_on_population.bib ({root_bib_stats['unique_keys']} keys, {root_bib_stats['linked_pct']}% linked)", flush=True)

  # 4. Preload masks & sample 128 population rasters in a single pass
  print("[3/4] Sampling 128 population rasters & computing exact spherical sub-region areas...", flush=True)
  hyde_years = sorted(int(y) for y in masks_cfg["hyde_years"])
  row_areas = compute_row_cell_areas_km2()
  mask_by_id = {m["id"]: m for m in masks_cfg["specialist_masks"] + masks_cfg["national_epoch_masks"]}

  # Macro-basin masks from prehistoric_ssa
  p_pre = SVEA_ROOT / mask_by_id["prehistoric_ssa"]["mask_path"]
  j_pre = json.loads((SVEA_ROOT / mask_by_id["prehistoric_ssa"]["json5_path"]).read_text(encoding="utf-8"))
  pre_rgba = np.asarray(Image.open(p_pre).convert("RGBA"), dtype=np.uint8)
  pre_rgb = (pre_rgba[:, :, 0].astype(np.int32) << 16) | (pre_rgba[:, :, 1].astype(np.int32) << 8) | pre_rgba[:, :, 2].astype(np.int32)
  pre_valid = pre_rgba[:, :, 3] > 0
  macro_names = [
    "West Africa & Sahel", "Horn of Africa & Sudan", "Central Africa & Angola",
    "East Africa & Great Lakes", "Southern Africa", "African Ocean Islands",
  ]
  macro_idx = {}
  for mn in macro_names:
    m_bool = np.zeros((GRID_H, GRID_W), dtype=bool)
    for sr in j_pre["subregions"]:
      if MACRO_BASIN_MAP.get(sr["id"]) == mn:
        code = (int(sr["rgb"][0]) << 16) | (int(sr["rgb"][1]) << 8) | int(sr["rgb"][2])
        m_bool |= (pre_valid & (pre_rgb == code))
    macro_idx[mn] = np.flatnonzero(m_bool.ravel())

  ch_runtime = []
  needed_years = set()
  macro_bench_years = [
    y for y in (-10000, -8000, -6000, -4000, -3000, -2000, -1000, 0, 500, 1000, 1200, 1400, 1500, 1600, 1700, 1750, 1800, 1820, 1850, 1880, 1900, 1920, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020, 2025)
    if y in set(hyde_years)
  ]
  needed_years.update(macro_bench_years)

  for idx, g in enumerate(gaz_cfg["gazetteers"], 1):
    stem = g["key"]
    m_info = mask_by_id[stem]
    j_path = SVEA_ROOT / m_info["json5_path"]
    m_path = SVEA_ROOT / m_info["mask_path"]
    j_obj = json.loads(j_path.read_text(encoding="utf-8"))

    rgba = np.asarray(Image.open(m_path).convert("RGBA"), dtype=np.uint8)
    valid = rgba[:, :, 3] > 0
    rgb_grid = np.where(
      valid,
      (rgba[:, :, 0].astype(np.int32) << 16) | (rgba[:, :, 1].astype(np.int32) << 8) | rgba[:, :, 2].astype(np.int32),
      -1,
    )
    flat_rgb = rgb_grid.ravel()
    total_pixels = int(valid.sum())

    code_to_sr = {}
    sr_entries = []
    tot_area = 0.0
    for sr in j_obj["subregions"]:
      rgb = [int(v) for v in sr["rgb"]]
      code = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]
      m_sr = (rgb_grid == code)
      area_km2 = round(float((m_sr.sum(axis=1) * row_areas).sum()), 1)
      tot_area += area_km2
      pidx = np.flatnonzero(flat_rgb == code)
      code_to_sr[code] = sr["id"]
      sr_entries.append({
        "id": sr["id"],
        "name": sr["name"],
        "rgb": rgb,
        "source": sr.get("source", ""),
        "era": sr.get("era", ""),
        "description": sr.get("description", ""),
        "pixel_count": int(pidx.size),
        "area_km2": area_km2,
        "pidx": pidx,
        "population": {},
      })

    bench_yrs = select_benchmark_years(hyde_years, g["domain"])
    needed_years.update(bench_yrs)
    ch_runtime.append({
      "index": idx,
      "stem": stem,
      "group": g["region_group"],
      "folder_name": j_path.parent.name,
      "folder": f"{g['region_group']}/{j_path.parent.name}",
      "ch_dir": j_path.parent,
      "j5": j_obj,
      "rgb_grid": rgb_grid,
      "code_to_sr": code_to_sr,
      "sr_entries": sr_entries,
      "total_area_km2": round(tot_area, 1),
      "total_pixels": total_pixels,
      "benchmark_years": bench_yrs,
      "headline_series": {},
    })

  macro_series = {"years": macro_bench_years, "total": {}, "regions": {mn: {} for mn in macro_names}}
  for yr in sorted(needed_years):
    rp = POP_RASTERS_DIR / f"popc_{yr}.png"
    if not rp.exists():
      continue
    flat = decode_velk_png(rp).ravel()
    ys = str(yr)
    if yr in macro_bench_years:
      tot_m = 0.0
      for mn in macro_names:
        v = round(float(flat[macro_idx[mn]].sum()), 1)
        macro_series["regions"][mn][ys] = v
        tot_m += v
      macro_series["total"][ys] = round(tot_m, 1)
    for rt in ch_runtime:
      if yr in rt["benchmark_years"]:
        tot_ch = 0.0
        for sr in rt["sr_entries"]:
          v = round(float(flat[sr["pidx"]].sum()), 1) if sr["pidx"].size > 0 else 0.0
          sr["population"][ys] = v
          tot_ch += v
        rt["headline_series"][ys] = round(tot_ch, 1)

  # 5. Stage per-chapter _summary_cache.json + nicethi_root_summary.json
  print("[4/4] Staging all 23 <stem>_summary_cache.json + nicethi_root_summary.json...", flush=True)
  root_chapters = []
  pan_by_key = {}
  total_trajectories = 0
  total_observations = 0

  for rt in ch_runtime:
    stem = rt["stem"]
    ch_dir = rt["ch_dir"]
    cmeta = CHAPTER_METADATA[stem]
    d0, d1 = [int(x) for x in rt["j5"]["domain"]]
    setts = json.loads((ch_dir / f"{stem}_settlements.json").read_text(encoding="utf-8"))
    ledger = json.loads((ch_dir / f"{stem}_source_ledger.json5").read_text(encoding="utf-8"))

    # Spatial subregion settlement distribution + top settlements + Zipf
    rgb_grid = rt["rgb_grid"]
    code_to_sr = rt["code_to_sr"]
    sr_sett_stats = {sr["id"]: {"settlement_count": 0, "observation_count": 0, "peak_pop_sum": 0, "top_names": []} for sr in rt["sr_entries"]}
    scope_cnt = Counter()
    by_country = Counter()
    ranked = []
    obs_total = 0

    for skey, s in setts.items():
      sc = str(s.get("population_scope") or "city_proper")
      scope_cnt[sc] += 1
      ctry = str(s.get("country") or "")
      if ctry:
        by_country[ctry] += 1
      pdict = {str(k): int(round(float(v))) for k, v in (s.get("population") or {}).items() if float(v) > 0}
      obs_total += len(pdict)
      if not pdict:
        continue
      yrs_s = sorted(int(k) for k in pdict)
      pky = max(yrs_s, key=lambda yy: pdict[str(yy)])
      pkp = pdict[str(pky)]
      coords = s.get("coords") or [0.0, 0.0]
      lat, lon = float(coords[0]), float(coords[1])

      # Assign pixel to subregion (search 5x5 neighbourhood if coastal edge)
      row = max(0, min(GRID_H - 1, int((90.0 - lat) * GRID_H / 180.0)))
      col = max(0, min(GRID_W - 1, int((lon + 180.0) * GRID_W / 360.0)))
      sr_id = code_to_sr.get(int(rgb_grid[row, col]))
      if sr_id is None:
        for dr in range(-2, 3):
          for dc in range(-2, 3):
            rr = max(0, min(GRID_H - 1, row + dr))
            cc = (col + dc) % GRID_W
            cand_id = code_to_sr.get(int(rgb_grid[rr, cc]))
            if cand_id is not None:
              sr_id = cand_id
              break
          if sr_id is not None:
            break
      if sr_id is not None and sr_id in sr_sett_stats:
        st_sr = sr_sett_stats[sr_id]
        st_sr["settlement_count"] += 1
        st_sr["observation_count"] += len(pdict)
        st_sr["peak_pop_sum"] += pkp
        st_sr["top_names"].append((pkp, s.get("name", "")))

      rec = {
        "key": skey,
        "name": s.get("name", ""),
        "country": ctry,
        "coords": [round(lat, 4), round(lon, 4)],
        "lat": round(lat, 4),
        "lon": round(lon, 4),
        "peak_pop": pkp,
        "peak_year": pky,
        "min_year": yrs_s[0],
        "max_year": yrs_s[-1],
        "observation_count": len(pdict),
        "population_scope": sc,
        "is_capital": bool(s.get("is_capital", False)),
        "foundation_year": s.get("foundation_year"),
        "evidence_basis": classify_evidence_basis(s.get("sources"), sc),
        "sources": (s.get("sources") or [])[:4],
        "population": pdict,
      }
      ranked.append(rec)

      prev = pan_by_key.get(skey)
      if prev is None or pkp > prev["peak_pop"]:
        pan_by_key[skey] = {
          "key": skey,
          "name": rec["name"],
          "country": ctry,
          "population_scope": sc,
          "lat": rec["lat"],
          "lon": rec["lon"],
          "peak_year": pky,
          "peak_pop": pkp,
          "chapter_stem": stem,
        }

    total_trajectories += len(setts)
    total_observations += obs_total
    ranked.sort(key=lambda r: (-r["peak_pop"], r["name"]))
    zipf_stats = compute_zipf_stats([r["peak_pop"] for r in ranked])

    end_ys = str(rt["benchmark_years"][-1]) if rt["benchmark_years"] else ""
    start_ys = str(rt["benchmark_years"][0]) if rt["benchmark_years"] else ""
    subregions_clean = []
    subreg_dist_out = []
    for sr in rt["sr_entries"]:
      p_end = sr["population"].get(end_ys, 0.0) if end_ys else 0.0
      p_start = sr["population"].get(start_ys, 0.0) if start_ys else 0.0
      dens_end = round(p_end / max(1.0, sr["area_km2"]), 3) if sr["area_km2"] > 0 else 0.0
      dist = sr_sett_stats[sr["id"]]
      top_nms = [nm for _, nm in sorted(dist["top_names"], reverse=True)[:4]]
      subregions_clean.append({
        "id": sr["id"],
        "name": sr["name"],
        "rgb": sr["rgb"],
        "source": sr["source"],
        "era": sr["era"],
        "description": sr["description"],
        "pixel_count": sr["pixel_count"],
        "area_km2": sr["area_km2"],
        "start_pop": p_start,
        "end_pop": p_end,
        "end_density_km2": dens_end,
        "population": sr["population"],
      })
      subreg_dist_out.append({
        "id": sr["id"],
        "name": sr["name"],
        "settlement_count": dist["settlement_count"],
        "observation_count": dist["observation_count"],
        "peak_pop_sum": dist["peak_pop_sum"],
        "top_settlements": top_nms,
      })

    subregions_sorted = sorted(subregions_clean, key=lambda r: -r["end_pop"])
    subadmin_tables, hgis_regime_units = select_subadmin_tables_for_chapter(stem, [d0, d1], sub_enums, hgis_csv_rows)
    arf_obs, arf_tables = select_arf_evidence_for_chapter(stem, [d0, d1], arf_ev)
    b_stats, b_entries = ch_bib_info[stem]
    sat_audit = ledger.get("saturation_audit") or {}
    gs = gaz_sum_by_key.get(stem, {})
    cands = ledger.get("candidates") or []

    cache = {
      "index": rt["index"],
      "stem": stem,
      "key": stem,
      "title": cmeta["title"],
      "subtitle": cmeta["subtitle"],
      "domain": [d0, d1],
      "regime": rt["j5"].get("regime"),
      "is_admin1": bool(rt["j5"].get("is_admin1", False)),
      "group": rt["group"],
      "folder": rt["folder"],
      "folder_name": rt["folder_name"],
      "total_area_km2": rt["total_area_km2"],
      "total_pixels": rt["total_pixels"],
      "subregion_count": len(subregions_clean),
      "benchmark_years": rt["benchmark_years"],
      "headline_series": rt["headline_series"],
      "end_epoch_year": int(end_ys) if end_ys else d1,
      "end_epoch_population": rt["headline_series"].get(end_ys, 0.0),
      "end_epoch_density_km2": round(rt["headline_series"].get(end_ys, 0.0) / max(1.0, rt["total_area_km2"]), 3),
      "subregions": subregions_clean,
      "top_subregions": subregions_sorted[:18],
      "settlement_count": len(setts),
      "observation_count": obs_total,
      "population_scope_counts": {
        "city_proper": int(scope_cnt.get("city_proper", 0)),
        "metro": int(scope_cnt.get("metro", 0)),
      },
      "countries": sorted(by_country.keys()),
      "settlements_by_country": dict(by_country.most_common()),
      "top_settlements": ranked[:20],
      "zipf_alpha": zipf_stats["zipf_q"],
      "zipf_q": zipf_stats["zipf_q"],
      "zipf_r2": zipf_stats["r2"],
      "rank_size": zipf_stats,
      "subregion_settlement_distribution": subreg_dist_out,
      "wave_saturation_stats": {
        "waves_completed": ledger.get("waves_completed", 4),
        "ledger_included": sum(1 for c in cands if c.get("status") == "included") or sat_audit.get("final_included_count", len(setts)),
        "ledger_excluded": sum(1 for c in cands if c.get("status") == "excluded"),
        "wave1_count": sat_audit.get("wave1_count", 0),
        "wave2_count": sat_audit.get("wave2_count", 0),
        "wave3_count": sat_audit.get("wave3_count", 0),
        "wave4_gap_sweep_added": sat_audit.get("wave4_gap_sweep_added", 0),
        "marginal_gain_pct": sat_audit.get("marginal_gain_pct", gs.get("marginal_gain_pct")),
        "empty_inhabited_subregions": sat_audit.get("empty_inhabited_subregions", 0),
        "subregions_covered": gs.get("subregions_covered"),
        "unique_peak_ratio": gs.get("unique_peak_ratio"),
        "iqr_log10": gs.get("iqr_log10"),
        "jurisdiction_coverage": ledger.get("jurisdiction_coverage", {}),
      },
      "subadmin_benchmark_tables": subadmin_tables,
      "hgis_regime_units": hgis_regime_units,
      "arf_settlement_evidence": arf_obs,
      "arf_regional_tables": arf_tables,
      "bib_stats": b_stats,
      "bib_keys": b_entries,
    }
    (ch_dir / f"{stem}_summary_cache.json").write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")

    root_chapters.append({
      "index": rt["index"],
      "stem": stem,
      "title": cmeta["title"],
      "subtitle": cmeta["subtitle"],
      "group": rt["group"],
      "folder": rt["folder"],
      "domain": [d0, d1],
      "area_km2": rt["total_area_km2"],
      "subregions": len(subregions_clean),
      "settlements": len(setts),
      "observations": obs_total,
      "population_scope_counts": cache["population_scope_counts"],
      "zipf_q": zipf_stats["zipf_q"],
      "zipf_r2": zipf_stats["r2"],
      "start_year": int(start_ys) if start_ys else d0,
      "end_year": int(end_ys) if end_ys else d1,
      "pop_start": rt["headline_series"].get(start_ys, 0.0),
      "pop_end": rt["headline_series"].get(end_ys, 0.0),
      "end_density_km2": cache["end_epoch_density_km2"],
      "bib_key_count": b_stats["unique_keys"],
      "bib_linked_pct": b_stats["linked_pct"],
      "bib_distinct_publishers": b_stats["distinct_publishers"],
      "bib_max_author_share": b_stats["max_author_share"],
      "bib_max_publisher_share": b_stats["max_publisher_share"],
      "subadmin_benchmark_tables_count": len(subadmin_tables),
      "arf_evidence_count": len(arf_obs),
    })

  pan_list = sorted(pan_by_key.values(), key=lambda r: (-r["peak_pop"], r["name"]))
  pan_scope = Counter(r["population_scope"] for r in pan_list)
  pan_ctry = Counter(r["country"] for r in pan_list if r["country"])

  root_summary = {
    "project": "NICETHI",
    "order": 14,
    "macro_scope": geo_meta.get("macro_scope", "Sub-Saharan Africa, Sudan, Sahel, Horn, Madagascar, Western Indian Ocean Islands and African Atlantic Islands"),
    "total_chapters": len(root_chapters),
    "total_chapter_settlement_trajectories": total_trajectories,
    "total_settlement_records": total_trajectories,
    "unique_settlement_count": len(pan_list),
    "total_settlement_observations": total_observations,
    "pan_african_urban_hierarchy": {
      "scope_counts": dict(pan_scope),
      "country_counts": dict(pan_ctry.most_common()),
      "zipf_all_unique": compute_zipf_stats([r["peak_pop"] for r in pan_list]),
      "top_settlements": pan_list[:35],
    },
    "macro_basin_series": macro_series,
    "domestic_catchments": krig_diag.get("domestic_catchments"),
    "domestic_sites": round(float(krig_diag.get("domestic_site_count_unique_sum") or 0)),
    "tau1_dimensionless": krig_diag.get("tau1_dimensionless"),
    "raw_tau1_dimensionless": krig_diag.get("raw_tau1_dimensionless"),
    "valid_cells": krig_diag.get("valid_cells"),
    "arch_regional_share": krig_diag.get("arch_regional_share"),
    "arch_crowd_share": krig_diag.get("arch_crowd_share"),
    "jurisdiction_arch_coverage": krig_diag.get("jurisdiction_arch_coverage", {}),
    "kriging_diagnostics": krig_diag,
    "subadmin_audit": sub_audit,
    "period_geojsons": geo_meta.get("period_geojsons", []),
    "arf_regional_population_tables": arf_ev.get("regional_population_tables", []),
    "root_bib_stats": root_bib_stats,
    "root_bib_keys": root_bib_entries,
    "chapters": root_chapters,
  }
  (SHARED_DIR / "nicethi_root_summary.json").write_text(json.dumps(root_summary, indent=2, ensure_ascii=False), encoding="utf-8")

  print("\n=== NICETHI STAGE D BIBTEX & SUMMARY CACHE REPORT ===")
  for c in root_chapters:
    print(
      f"  Ch{c['index']:02d} {c['stem']:26s} | bib={c['bib_key_count']:2d} | linked={c['bib_linked_pct']:5.1f}% "
      f"| pubs={c['bib_distinct_publishers']:2d} | maxAuth={c['bib_max_author_share']*100:4.1f}% "
      f"| maxPub={c['bib_max_publisher_share']*100:4.1f}% | setts={c['settlements']:4d} "
      f"| subTbls={c['subadmin_benchmark_tables_count']:2d} | arf={c['arf_evidence_count']:2d}",
      flush=True,
    )
  print(
    f"  ROOT studies_on_population.bib: {root_bib_stats['unique_keys']} keys | "
    f"linked={root_bib_stats['linked_pct']}% | pubs={root_bib_stats['distinct_publishers']} | "
    f"maxAuth={root_bib_stats['max_author_share']*100:.1f}%",
    flush=True,
  )


if __name__ == "__main__":
  main()
