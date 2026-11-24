"""Stage C Wave-2 Archival PDF Monograph & Census Report Harvester for NICETHI (23 chapters).

Combines curated high-relevance primary monographs/articles from Africa Research Files
with novel open-access scholarly PDFs (Crossref+Unpaywall, Targeted African Journal ISSNs,
HAL, DOAJ, PLOS, World Bank WDS, Archive.org) across all 23 NICETHI chapters.

Enforces:
  - >= 18 (target 20) SHA-256-unique valid %PDF- files (> 10.24 kB, pymupdf-readable) per chapter
  - Filename <= 58 chars (clean snake_case.pdf), full repo-relative path <= 180 chars
  - 0% Zenodo (<= 10% cap), >= 6 distinct scholarly publishers/domains per chapter
  - No single author > 25% of a chapter's PDFs (capped at <= 2 per first-author surname)
  - Zero banned compendia (McEvedy, Klein Goldewijk, Chandler, Modelski, Maddison, Populstat)
  - Strict human demography/history/archaeology/census relevance (zero clinical/animal/noise)
  - Worker pool <= 4; complete metadata manifest at NICETHI/_shared/wave2_papers_manifest.json
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import time
import unicodedata
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import pymupdf
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
NICETHI_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "NICETHI")
ARF_ROOT = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_references", "Africa Research Files")
ARF_INDEX_PATH = os.path.join(NICETHI_DIR, "_shared", "africa_research_files_index.json")
MANIFEST_PATH = os.path.join(NICETHI_DIR, "_shared", "wave2_papers_manifest.json")

TARGET_PER_CHAPTER = 20
MIN_BYTES = 10241
MAX_BYTES = 26 * 1024 * 1024
MAX_WORKERS = 4
MAX_FILENAME_LEN = 58
MAX_RELPATH_LEN = 180

HEADERS = {
  "User-Agent": (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 "
    "(OperationViscount-NICETHI/1.0; mailto:austkaeztchen@confoederatio.org)"
  ),
  "Accept": "application/pdf,text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}
API_HEADERS = {
  "User-Agent": "OperationViscount-NICETHI/1.0 (mailto:austkaeztchen@confoederatio.org)"
}

BANNED_TOKENS = (
  "mcevedy", "colin mcevedy", "penguin atlas of africa",
  "klein goldewijk", "goldewijk", "maddison", "angus maddison",
  "tertius chandler", "chandler1987", "modelski", "george modelski",
  "populstat", "hyde 3", "hyde 2", "atlas of world population history",
  "four thousand years of urban growth",
  "song china", "brabant", "early modern germany", "great dying in the americas",
  "colonial costa rica", "medieval europe", "hanse", "american culture",
  "africans on american", "historical dictionary", "encyclopedia",
  "cambridge history of africa", "general history africa",
)

BANNED_HOSTS = (
  "zenodo.org", "wikidata.org", "wikipedia.org", "wikimedia.org",
  "openstreetmap.org", "geonames.org", "researchgate.net", "academia.edu",
  "scribd.com", "slideshare.net", "github.com", "githubusercontent.com",
  "osf.io", "figshare.com",
  "cran.r-project.org", "ijsab.com", "ijirset.com", "ijcsrr.org", "ijmhr.org",
  "journalijar.com", "opastpublishers.com", "austinpublishinggroup.com",
  "dovepress.com", "wjarr.com", "ijsr.net", "bjmas.org", "multiresearchjournal.com",
  "apjhs.com", "arabjournalpp.org", "europeanjournaloftaxonomy.eu", "mapress.com",
  "pachydermjournal.org", "koedoe.co.za", "ojvr.org", "jlimnol.it",
  "archimer.ifremer.fr", "agritrop.cirad.fr", "revues.cirad.fr", "assets-eu.researchsquare.com",
  "soaphys.org", "saeb.feaa.uaic.ro", "everant.org", "so03.tci-thaijo.org",
  "iiari.org", "bmjopen.bmj.com", "panafrican-med-journal.com", "ijcaonline.org",
  "ijiissh.com", "juniperpublishers.com", "pegasjournal.eu", "ijsshmr.com",
  "public.pensoft.net", "ijfmr.com", "nje.org.na", "curationis.org.za",
  "museucienciesjournals.cat", "ams-hra.org", "tropicalplantresearch.com",
  "claisse.info", "knepublishing.com",
)

OFFTOPIC_TERMS = (
  "mouse", "mice", "murine", "zebrafish", "drosophila", "arabidopsis",
  "carcinoma", "chemotherapy", "in vitro", "canine", "feline", "bovine",
  "porcine", "equine", "new species of", "phylogeny of", "taxonomy of",
  "taxonomic revision", "taxonomic monograph", "butterfly", "butterflies",
  "beetle", "beetles", "lepidoptera", "coleoptera", "hymenoptera",
  "amphibian", "lizard", "snake", "bird species", "avian", "coral reef",
  "shark", "orchid", "fungus", "fungi", "mycorrhiz", "soil bacteria",
  "microbiome", "clinical trial", "randomized controlled", "alzheimer",
  "parkinson", "breast cancer", "prostate cancer", "leukemia", "schizophrenia",
  "pesticide", "wastewater", "photovoltaic", "solar cell", "concrete",
  "asphalt", "polymer", "nanoparticle", "catalysis", "quantum",
  "superconductor", "rat model", "wistar", "sprague-dawley", "hiv-1",
  "antiretroviral", "cesarean", "caesarean", "malaria vaccine", "covid-19",
  "sars-cov-2", "tuberculosis", "machine learning", "chameleon",
  "gecko", "frog", "spider", "scorpions", "nematode", "parasitoid",
  "cia reading room", "dtic ada", "jprs id", "paranormal", "banjo",
  "coins and medals", "supermarket", "sachet water", "online marketing",
  "oil prices", "burnout", "sexual abuse", "homophobia", "electric power",
  "water quality", "particulate pollution", "tailings", "procurement",
  "poultry", "catfish", "ostracod", "fruit bat", "batrachian", "reptile",
  "crocodile", "cheetah", "elephant", "hyaena", "herbivore", "raptor",
  "cetacean", "millipede", "caddisfly", "vegetable fl", "mirid", "acalypha",
  "crustacea", "medusa", "bovid", "edible fishes", "zoological",
  "phytoecological", "coprolite", "pollen analysis", "cephalic index",
  "escherichia", "uropathogenic", "prostatic", "colostrum", "antibiotic",
  "mpox", "bilharzial", "dengue", "hepatitis", "leishmania", "cancer",
  "precancer", "diarrhea", "respiratory syncytial", "kdr mutation",
  "soil fertility", "previous legumes", "hydrological impacts", "wetlands",
  "chewing khat", "contraceptive", "abortion", "taste sensitivity", "zika",
  "arbovirus", "telemedicine", "cardiometabolic", "rearing environment",
  "cape york", "aurukun", "abs census 1991, gold coast", "french yanam",
  "irish republican army", "guinea pigs by john", "archbold expeditions",
  "malaria elimination", "dispute resolution", "food assistance",
  "sport profile", "short term financing", "microfinance", "street children",
  "small business failures", "cystic duct", "anatomical variations",
  "home gardens", "pharmaceutiques", "energy access", "transport policy note",
  "family planning uptake", "non-enrollment", "financial integration",
  "financial flows", "monetary zone", "macroeconomic", "coastal vulnerability",
  "burning island", "grey markets", "organic containers", "glass beads",
  "relevant theology", "christian movement", "native baptist",
  "dutch reformed church", "ecumenical", "african nurses", "malangatana",
  "popular music", "bamboo architecture", "tree", "trees", "forest canopy",
  "biodiversity", "mangrove crab", "aquaculture", "fisheries catch",
  "diabetes", "hypertension", "obesity", "anemia", "anaemia", "stunting",
  "underweight", "immunization", "vaccination", "antenatal", "postpartum",
  "neonatal", "cesarean", "preterm", "sepsis", "pneumonia", "asthma",
  "epilepsy", "stroke", "cardiovascular", "renal", "liver", "gastric",
  "ecotaxonom", "polymetallic", "insecticidal", "fertility awareness",
  "quantile regression", "malnutrition", "contamination", "mosquito", "larvae",
)

# Strict human demography / history / archaeology / census topic terms (accent-folded!)
STRICT_TOPIC_TERMS = (
  "population", "populacao", "census", "censo", "recensement", "recenseamento",
  "demograph", "demograf", "urbanization", "urbanisation", "urbanizacao",
  "urbanism", "urban", "city", "cities", "town", "towns", "settlement",
  "peuplement", "fertility", "fecondite", "fecundidade", "mortality",
  "mortalite", "mortalidade", "migration", "migracao", "emigration",
  "immigration", "archaeolog", "archeolog", "arqueolog", "precolonial",
  "pre-colonial", "colonial", "slavery", "slave trade", "esclavage",
  "escravidao", "kingdom", "empire", "sultanate", "emirate", "caliphate",
  "chiefdom", "iron age", "stone age", "holocene", "neolithic",
  "pleistocene", "radiocarbon", "ancient dna", "paleodemograph", "histori",
  "chronology", "gazetteer", "blue book", "statistical register",
  "nuptiality", "demographic dividend", "demographic transition",
  "life expectancy", "age structure", "household", "vital statistics",
  "opgaaf", "ethnograph", "ethnohistor", "pastoralism", "nomadic",
  "caravan", "urban growth", "spatial", "megacity", "slum", "informal settlement",
)

# Target ISSN pools by domain
DEMOGRAPHY_ISSNS = [
  "1435-9871",  # Demographic Research
  "2308-7854",  # African Population Studies
  "0850-5780",  # African Population Studies (alt)
  "2035-5556",  # Genus
  "1728-4414",  # Vienna Yearbook of Population Research
  "0032-4663",  # Population (INED)
  "2078-0389",  # Economic History of Developing Regions
  "0145-2258",  # African Economic History
]

HISTORY_ARCH_ISSNS = [
  "0067-270X",  # Azania
  "0263-0338",  # African Archaeological Review
  "1612-1651",  # Journal of African Archaeology
  "0021-8537",  # Journal of African History
  "0361-5413",  # History in Africa
  "0008-0055",  # Cahiers d'Etudes Africaines
  "0399-0346",  # Journal des Africanistes
  "0003-598X",  # Antiquity
  "0038-1969",  # South African Archaeological Bulletin
  "0259-0190",  # Kronos
  "0018-229X",  # Historia
  "0305-7070",  # Journal of Southern African Studies
  "1430-1938",  # Aethiopica
  "0066-2127",  # Annales d'Ethiopie
  "1234-5415",  # Polish Archaeology in the Mediterranean
  "2084-6762",  # Etudes et Travaux
  "1645-3794",  # Cadernos de Estudos Africanos
  "1257-0273",  # Lusotopie
  "0002-0591",  # Afro-Asia
]

CHAPTERS = [
  # --- 1.ancient_mediaeval ---
  {
    "group": "1.ancient_mediaeval", "folder": "1.prehistoric_ssa", "stem": "prehistoric_ssa",
    "arf_max": 8,
    "arf_inc": r"\b(stone age|prehistor|neolithic|holocene|pleistocene|green sahara|chad basin|middle stone|from stone to metal|hunter-gatherer|radiocarbon|pastoralism|rock art)\b",
    "arf_exc": r"\b(colonial|slave trade|19th century|20th century|apartheid|1960|1950|18th century|17th century|atlantic)\b",
    "issns": [("0067-270X", "Stone Age Neolithic"), ("0263-0338", "Holocene Stone Age"), ("0003-598X", "Africa Holocene Neolithic"), ("0038-1969", "Later Stone Age")],
    "crossref": ["Africa Later Stone Age", "Holocene Sahara pastoralism", "Africa Holocene ancient DNA"],
    "hal": ["Neolithique Sahara Afrique", "Holocene Afrique peuplement"],
    "doaj": ["Stone Age Africa archaeology", "Holocene Africa Neolithic"],
    "plos": ["Africa Holocene hunter-gatherer", "African Stone Age ancient DNA"],
    "wb": [], "ia": [],
    "pos_geo": ("africa", "african", "sahara", "sahel", "niger", "chad", "kenya", "tanzania", "ethiopia", "south africa", "kalahari", "botswana", "congo", "ghana", "mali", "sudan", "nile", "namibia", "zambia"),
    "excl_geo": ("australia", "europe", "china", "americas"),
  },
  {
    "group": "1.ancient_mediaeval", "folder": "2.ancient_mediaeval_nubia", "stem": "ancient_mediaeval_nubia",
    "arf_max": 5,
    "arf_inc": r"\b(nubia|meroe|makuria|alodia|nobatia|kerma|kush|sennar|funj|darfur|suakin|dongola|qwara|arabs in the sudan)\b",
    "arf_exc": r"\b(western sudan|french sudan|sudanic west|mali|senegal|songhai|ghana|hausa|wangara|fulbe)\b",
    "issns": [("1234-5415", "Nubia Sudan"), ("2084-6762", "Nubia Meroe Dongola"), ("0067-270X", "Nubia Sudan"), ("0263-0338", "Nubia Sudan Meroe")],
    "crossref": ["Nubia settlement archaeology", "Meroe Kerma Kush", "Makuria Dongola Alodia", "Sennar Funj Darfur"],
    "hal": ["Nubie Meroe Kerma", "Soudan Nubie archeologie", "Dongola Makuria Soudan"],
    "doaj": ["Nubia Meroe archaeology", "Sudan Nubia Kerma"],
    "plos": ["Nubia Sudan bioarchaeology"],
    "wb": [], "ia": ["title:(Nubia) AND (Meroe OR Dongola)", "title:(Sudan) AND (Sennar OR Funj)"],
    "pos_geo": ("nubia", "nubian", "sudan", "meroe", "meroitic", "kerma", "kush", "napata", "dongola", "makuria", "alodia", "soba", "nobatia", "sennar", "funj", "darfur", "kordofan", "suakin", "nile", "beja"),
    "excl_geo": ("western sudan", "mali", "senegal", "nigeria", "ghana"),
  },
  {
    "group": "1.ancient_mediaeval", "folder": "3.ancient_horn_africa", "stem": "ancient_horn_africa",
    "arf_max": 6,
    "arf_inc": r"\b(aksum|adulis|ethiopia|abyssinia|oromo|zagwe|solomonic|adal|harar|somalia|banadir|eritrea|medieval ethiopia)\b",
    "arf_exc": r"\b(19th century|1960|scramble|1827|1977|congo|west africa)\b",
    "issns": [("1430-1938", "Aksum medieval Ethiopia"), ("0066-2127", "Ethiopie Aksum Lalibela"), ("0067-270X", "Ethiopia Aksum Horn"), ("0263-0338", "Ethiopia Aksum Harar"), ("0021-8537", "Ethiopia Aksum Solomonic Adal"), ("0361-5413", "Ethiopia medieval chronicle")],
    "crossref": ["Aksum Adulis archaeology", "Medieval Ethiopia Lalibela", "Harar Adal Ethiopia", "Ethiopian Highlands archaeology settlement", "Somalia medieval archaeological"],
    "hal": ["Ethiopie Aksum archeologie", "Ethiopie medievale Lalibela", "Corne Afrique archeologie", "Harar Ethiopie histoire"],
    "doaj": ["Aksum Ethiopia archaeology", "Ethiopia medieval history"],
    "plos": [],
    "wb": [], "ia": ["title:(Abyssinia) OR title:(Aksum)"],
    "pos_geo": ("ethiopia", "ethiopie", "aksum", "axum", "adulis", "eritrea", "erythree", "abyssinia", "abyssinie", "tigray", "lalibela", "zagwe", "shewa", "harar", "adal", "ifat", "somalia", "somalie", "somaliland", "banadir", "horn of africa", "corne de l afrique", "oromo", "kaffa", "gondar"),
    "excl_geo": ("west africa", "nigeria", "senegal"),
  },
  {
    "group": "1.ancient_mediaeval", "folder": "4.early_west_africa_sahel", "stem": "early_west_africa_sahel",
    "arf_max": 12,
    "arf_inc": r"\b(jenne-jeno|jenne|gao saney|timbuktu|awdaghust|wagadou|songhai|kanem|bornu|hausa|nok|ife|benin city walls|igbo|begho|akan|sadia|inland niger delta|middle niger|early urban.*west africa|early city in west africa|hausaland|northern yoruba|southern chad basin|two thousand years of west african|archaeology of west africa|archaeology and the study of early urban)\b",
    "arf_exc": r"\b(18th|19th|20th|colonial|1960|atlantic slave|1760|1800|1848|1900)\b",
    "issns": [("0067-270X", "West Africa Mali Nigeria Ghana"), ("0263-0338", "West Africa Mali Nigeria"), ("1612-1651", "West Africa Mali Nigeria"), ("0021-8537", "Ghana Mali Songhai Kanem"), ("0399-0346", "Mali Niger Sahel"), ("0008-0055", "Mali Songhai Ghana Benin Ife"), ("0361-5413", "West Africa Ghana Mali Songhai")],
    "crossref": ["Jenne-Jeno Mali archaeology", "Timbuktu Gao Songhai", "Ile-Ife Benin archaeology", "Nok Igbo-Ukwu Nigeria", "Koumbi Saleh Awdaghust", "Ghana Empire archaeology", "Kano Katsina Hausa medieval"],
    "hal": ["Mali Jenne Gao archeologie", "Sahel Afrique Ouest archeologie", "Niger Burkina peuplement ancien", "Koumbi Saleh Ghana Mali", "Nigeria Ife Benin archeologie"],
    "doaj": ["West Africa archaeology", "Nigeria Ife Benin Nok", "Mali Ghana Songhai"],
    "plos": [], "wb": [], "ia": [],
    "pos_geo": ("west africa", "afrique de l ouest", "sahel", "mali", "niger", "jenne", "timbuktu", "tombouctou", "gao", "ghana", "wagadou", "songhai", "songhay", "kanem", "bornu", "hausa", "kano", "ife", "benin", "igbo", "nok", "nigeria", "begho", "burkina", "senegal", "mauritania", "mauritanie", "yoruba", "chad basin"),
    "excl_geo": ("australia", "south africa", "ethiopia"),
  },
  {
    "group": "1.ancient_mediaeval", "folder": "5.bantu_expansion_africa", "stem": "bantu_expansion_africa",
    "arf_max": 7,
    "arf_inc": r"\b(bantu|great zimbabwe|mapungubwe|mapela|kongo.*1390|swahili origins|early swahili|aquatic civilization|upemba|urewe|iron age)\b",
    "arf_exc": r"\b(west africa|hausa|yoruba|senegal|gambia|18th|19th|20th)\b",
    "issns": [("0067-270X", "Iron Age Bantu Swahili Zimbabwe"), ("0263-0338", "Bantu Iron Age Zimbabwe"), ("0038-1969", "Mapungubwe Great Zimbabwe Iron Age"), ("0021-8537", "Bantu expansion Iron Age")],
    "crossref": ["Bantu expansion archaeology", "Great Zimbabwe Mapungubwe", "Upemba Katanga Iron Age", "Kilwa Swahili Coast Iron Age"],
    "hal": ["Expansion bantoue Afrique centrale", "Gabon Cameroun Congo archeologie", "Afrique centrale age du fer"],
    "doaj": ["Bantu expansion Africa", "Great Zimbabwe Iron Age"],
    "plos": ["Bantu expansion genetics Africa"],
    "wb": [], "ia": [],
    "pos_geo": ("bantu", "bantou", "congo", "cameroon", "cameroun", "gabon", "angola", "great lakes", "grands lacs", "uganda", "rwanda", "kenya", "tanzania", "tanzanie", "swahili", "kilwa", "zimbabwe", "mapungubwe", "zambia", "malawi", "mozambique", "south africa", "upemba", "katanga", "zambezi", "central africa", "afrique centrale", "southern africa"),
    "excl_geo": ("west africa", "senegal", "australia"),
  },

  # --- 2.early_modern ---
  {
    "group": "2.early_modern", "folder": "1.atlantic_west_equatoria", "stem": "atlantic_west_equatoria",
    "arf_max": 10,
    "arf_inc": r"\b(elmina|dahomey|oyo|lagos|asante|fante|niger delta|benin.*1485|kongo|angola|loango|sierra leone|galinhas|geba|baule|gyaman|atlantic.*west africa|atlantic period|gold coast)\b",
    "arf_exc": r"\b(east africa|swahili|ethiopia|madagascar|zimbabwe|1960|1950)\b",
    "issns": [("0021-8537", "Kongo Angola Dahomey Asante"), ("0361-5413", "Kongo Angola Gold Coast"), ("0002-0591", "Angola Kongo escravidao"), ("0145-2258", "Atlantic Africa slave trade")],
    "crossref": ["Kingdom of Kongo Angola", "Gold Coast Elmina Asante", "Dahomey Oyo Benin", "Lunda Luba Congo"],
    "hal": ["Kongo Angola histoire", "Traite atlantique Afrique Ouest", "Dahomey Benin Asante"],
    "doaj": ["Kongo Angola slave", "West Africa Atlantic trade"],
    "plos": [], "wb": [], "ia": [],
    "pos_geo": ("west africa", "afrique de l ouest", "gold coast", "ghana", "asante", "ashanti", "elmina", "dahomey", "benin", "oyo", "yoruba", "lagos", "niger delta", "nigeria", "sierra leone", "liberia", "senegambia", "kaabu", "guinea", "guinee", "cameroon", "gabon", "loango", "kongo", "congo", "angola", "ndongo", "luba", "lunda", "ovimbundu"),
    "excl_geo": ("australia", "ethiopia", "madagascar"),
  },
  {
    "group": "2.early_modern", "folder": "2.early_modern_sahel_sudan", "stem": "early_modern_sahel_sudan",
    "arf_max": 11,
    "arf_inc": r"\b(segou|massina|maasina|hayre|fulbe|fuladu|fulani|sokoto|zazzau|kano|birnin zaria|bornu|tuareg|yatenga|mossi|soninke|northern sudan.*19th|futa toro|timbuktu.*16th|black byzantium|mande equilibrium|kotoko|fulani jihad|futa jallon)\b",
    "arf_exc": r"\b(ethiopia|swahili|zimbabwe|madagascar|1960|1994)\b",
    "issns": [("0021-8537", "Sokoto Bornu Segou Darfur"), ("0361-5413", "Timbuktu Songhai Bornu Darfur"), ("0008-0055", "Sahel Segou Mossi Peul"), ("0399-0346", "Sahel Mali Niger Tchad"), ("0373-5834", "Sahel Niger Tchad Mali")],
    "crossref": ["Sokoto Caliphate slavery", "Kanem Bornu Chad", "Darfur Sultanate Sudan", "Timbuktu Segou Massina", "Funj Sennar Sudan", "Mossi Yatenga Burkina history"],
    "hal": ["Segou Massina Mali histoire", "Tchad Bornou Ouadai histoire", "Sahel XIXe peuplement", "Fouta Toro Peul histoire", "Mossi Burkina Faso histoire"],
    "doaj": ["Sokoto Caliphate Kano", "Darfur Sennar Sudan history"],
    "plos": [], "wb": [],
    "ia": ["title:(Timbuctoo) OR title:(Bornu)", "title:(Darfur) OR title:(Sennar)"],
    "pos_geo": ("sahel", "sudan", "soudan", "sokoto", "kano", "zaria", "zazzau", "hausa", "bornu", "bornou", "kanem", "bagirmi", "wadai", "ouadai", "chad", "tchad", "darfur", "darfour", "funj", "sennar", "kordofan", "equatoria", "timbuktu", "tombouctou", "segou", "massina", "mali", "niger", "mossi", "burkina", "mauritania", "mauritanie", "futa", "fouta", "fulbe", "fulani", "peul"),
    "excl_geo": ("ethiopia", "madagascar", "australia"),
  },
  {
    "group": "2.early_modern", "folder": "3.early_modern_east_africa", "stem": "early_modern_east_africa",
    "arf_max": 8,
    "arf_inc": r"\b(mombasa|swahili|kilwa|zanzibar|mozambique|east africa|indian ocean|banadir|buganda|nyamwezi|maravi|portuguese fortresses in east|trade and polity in east africa)\b",
    "arf_exc": r"\b(west africa|senegal|gambia|yoruba|hausa|mali|ghana|1960|1970)\b",
    "issns": [("0021-8537", "Zanzibar Buganda Swahili Mozambique"), ("0067-270X", "Swahili Zanzibar Kilwa"), ("0361-5413", "Buganda Swahili East Africa"), ("0008-0055", "Afrique orientale Zanzibar Grands Lacs"), ("0145-2258", "Zanzibar East Africa slave trade")],
    "crossref": ["Zanzibar slave trade", "Buganda Bunyoro 19th century", "Rwanda Burundi precolonial", "Nyamwezi Tanzania caravan", "Zambezi prazos Mozambique"],
    "hal": ["Zanzibar Afrique orientale XIXe", "Grands Lacs Buganda Rwanda histoire", "Mozambique Zambeze histoire", "Swahili Afrique orientale"],
    "doaj": ["Zanzibar Swahili history", "East Africa precolonial"],
    "plos": [], "wb": [],
    "ia": ["title:(Zanzibar) AND (slavery OR history)", "title:(Uganda) AND (Buganda OR history) AND NOT cia"],
    "pos_geo": ("east africa", "afrique orientale", "swahili", "zanzibar", "mombasa", "kilwa", "lamu", "kenya", "tanzania", "tanzanie", "tanganyika", "uganda", "ouganda", "buganda", "bunyoro", "rwanda", "burundi", "nyamwezi", "maasai", "mozambique", "zambezi", "zambeze", "maravi", "malawi", "yao", "sofala", "gaza"),
    "excl_geo": ("west africa", "senegal", "australia"),
  },
  {
    "group": "2.early_modern", "folder": "4.precolonial_south_africa", "stem": "precolonial_south_africa",
    "arf_max": 7,
    "arf_inc": r"\b(khoikhoi|khoekhoe|dutch south africa|frontier settlement.*south africa|cape|zulu|xhosa|sotho|tswana|rozvi|ndebele|great zimbabwe|mapungubwe|sociopolitical complexity in southern|debating great zimbabwe|zimbabwe culture before)\b",
    "arf_exc": r"\b(west africa|senegal|gambia|nigeria|ethiopia|mali|1960|1970|apartheid)\b",
    "issns": [("0259-0190", "Cape Colony Khoikhoi VOC"), ("0018-229X", "Cape Colony Zulu Xhosa"), ("0305-7070", "Cape Colony Zulu precolonial"), ("0021-8537", "Cape Colony Zulu Xhosa Mfecane"), ("2078-0389", "Cape Colony VOC demography"), ("1011-7601", "Cape Colony Xhosa Zulu frontier"), ("0038-1969", "Tswana Sotho Nguni settlement")],
    "crossref": ["Cape Colony VOC demography", "Cape Colony opgaaf census", "Zulu Kingdom Mfecane", "Xhosa Eastern Cape 19th", "Tswana Sotho precolonial", "Herero Nama Namibia 19th", "Cape Colony slavery population", "South Africa 18th century population"],
    "hal": ["Colonie du Cap XVIIIe", "Afrique australe XIXe histoire"],
    "doaj": ["Cape Colony 18th century", "Zulu Xhosa Tswana history", "Namibia Herero 19th", "South Africa colonial VOC"],
    "plos": [], "wb": [],
    "ia": ["title:(Cape of Good Hope) AND (census OR statistical OR colony) AND NOT fishes AND NOT birds", "title:(Natal) AND (census OR statistical OR colony) AND NOT fishes"],
    "pos_geo": ("south africa", "afrique du sud", "cape", "cap", "khoikhoi", "khoekhoe", "xhosa", "zulu", "zoulou", "natal", "transkei", "sotho", "basuto", "tswana", "bechuanaland", "pedi", "swazi", "transvaal", "orange free state", "namibia", "herero", "ovambo", "namaqua", "ndebele", "rozvi", "mashonaland", "zimbabwe"),
    "excl_geo": ("cape york", "aurukun", "australia", "west africa"),
  },
  {
    "group": "2.early_modern", "folder": "5.early_african_islands", "stem": "early_african_islands",
    "arf_max": 4,
    "arf_inc": r"\b(madagascar|merina|comoros|mauritius|reunion|mascarenes|seychelles|cabo verde|cape verde|sao tome|saint helena|radimilahy)\b",
    "arf_exc": r"\b(west africa|gambia|nigeria|mali|1960|1970|1980|1990|2000)\b",
    "issns": [("0021-8537", "Madagascar Mauritius Cabo Verde"), ("0008-0055", "Madagascar Comores Reunion Maurice"), ("1645-3794", "Cabo Verde Sao Tome"), ("1257-0273", "Cabo Verde Sao Tome Madagascar"), ("0399-0346", "Madagascar Merina Comores"), ("0002-0591", "Cabo Verde Sao Tome Angola")],
    "crossref": ["Madagascar Imerina 19th", "Mauritius slavery census", "Reunion Mascarenes slavery", "Cabo Verde Sao Tome demography", "Comoros Seychelles history"],
    "hal": ["Madagascar Imerina histoire", "Reunion Bourbon esclavage", "Ile Maurice Mascareignes", "Comores Mayotte histoire", "Cap-Vert Sao Tome"],
    "doaj": ["Cabo Verde historia", "Sao Tome Principe historia", "Madagascar Imerina history"],
    "plos": [], "wb": [],
    "ia": ["title:(Madagascar) AND (history OR Merina OR population) AND NOT bug", "title:(Mauritius) AND (census OR slavery OR history) AND NOT coin"],
    "pos_geo": ("madagascar", "imerina", "merina", "sakalava", "betsileo", "betsimisaraka", "antananarivo", "comoros", "comores", "mayotte", "mauritius", "maurice", "ile de france", "reunion", "bourbon", "mascarene", "mascareignes", "seychelles", "cabo verde", "cape verde", "cap vert", "cap-vert", "sao tome", "principe", "saint helena", "st helena"),
    "excl_geo": ("yanam", "india", "australia"),
  },

  # --- 3.colonial_era ---
  {
    "group": "3.colonial_era", "folder": "1.colonial_west_sahel", "stem": "colonial_west_sahel",
    "arf_max": 8,
    "arf_inc": r"\b(gambian studies|soninke.*1848|wolof.*colonial|ethno-demographics of west africa|demographics of empire|writing history backwards|african population.*1650-1950|banjul|fuladu)\b",
    "arf_exc": r"\b(east africa|ethiopia|madagascar|zimbabwe|south africa)\b",
    "issns": [("0021-8537", "Nigeria Ghana Senegal colonial census"), ("0145-2258", "Nigeria Ghana colonial population"), ("0008-0055", "AOF Senegal Mali Dakar population"), ("2078-0389", "Nigeria Ghana colonial census"), ("2308-7854", "Nigeria Ghana Senegal population")],
    "crossref": ["Colonial Nigeria census", "Gold Coast colonial census", "Senegal Dakar colonial", "Sierra Leone Gambia Liberia colonial"],
    "hal": ["Afrique Occidentale Francaise population", "Senegal Dakar demographie", "Cote d'Ivoire Mali Guinee population", "Burkina Faso Niger coloniale population"],
    "doaj": ["Nigeria colonial census", "Ghana colonial population"],
    "plos": [], "wb": [],
    "ia": ["title:(Nigeria) AND (census OR population) AND NOT cia", "title:(Sierra Leone) AND (census OR report) AND NOT cia"],
    "pos_geo": ("west africa", "afrique de l ouest", "aof", "french west africa", "senegal", "dakar", "mali", "soudan", "guinea", "guinee", "ivory coast", "cote d ivoire", "upper volta", "haute volta", "burkina", "dahomey", "benin", "niger", "mauritania", "mauritanie", "nigeria", "lagos", "gold coast", "ghana", "sierra leone", "freetown", "gambia", "banjul", "liberia", "monrovia", "bissau", "togo"),
    "excl_geo": ("abs census 1991", "queensland", "australia"),
  },
  {
    "group": "3.colonial_era", "folder": "2.colonial_equatoria_congo", "stem": "colonial_equatoria_congo",
    "arf_max": 2,
    "arf_inc": r"\b(belgian congo|equatorial africa|kamerun|cameroon.*colonial|angola.*colonial|congo free state)\b",
    "arf_exc": r"\b(west africa|senegal|gambia|ethiopia|zimbabwe)\b",
    "issns": [("0021-8537", "Belgian Congo Angola Cameroon"), ("0008-0055", "Congo AEF Gabon Cameroun"), ("1645-3794", "Angola colonial populacao"), ("1257-0273", "Angola colonial population")],
    "crossref": ["Belgian Congo demography", "Angola colonial census", "Cameroon colonial population", "French Equatorial Africa"],
    "hal": ["Congo belge demographie", "AEF Gabon Congo Tchad", "Cameroun colonial population", "Angola colonial population"],
    "doaj": ["Belgian Congo population", "Angola colonial population"],
    "plos": [], "wb": [], "ia": [],
    "pos_geo": ("congo", "belgian congo", "congo belge", "leopoldville", "katanga", "kasai", "aef", "equatorial africa", "afrique equatoriale", "gabon", "libreville", "brazzaville", "ubangi", "oubangu", "central african", "centrafrique", "chad", "tchad", "cameroon", "cameroun", "kamerun", "angola", "luanda", "equatorial guinea", "fernando po"),
    "excl_geo": ("australia", "nigeria"),
  },
  {
    "group": "3.colonial_era", "folder": "3.colonial_horn_sudan", "stem": "colonial_horn_sudan",
    "arf_max": 3,
    "arf_inc": r"\b(scramble in the horn|anglo-egyptian sudan|italian eritrea|somaliland.*colonial|firearms and princely power in ethiopia)\b",
    "arf_exc": r"\b(west africa|senegal|gambia|mali|nigeria)\b",
    "issns": [("1430-1938", "Ethiopia Eritrea colonial urban"), ("0021-8537", "Sudan Ethiopia Eritrea colonial"), ("0008-0055", "Ethiopie Erythree Djibouti Somalie"), ("0361-5413", "Sudan Ethiopia Eritrea"), ("0066-2127", "Ethiopie Addis Abeba XXe"), ("0373-5834", "Djibouti Ethiopie Soudan")],
    "crossref": ["Sudan 1955 1956 census", "Anglo-Egyptian Sudan population", "Italian Eritrea Asmara", "Addis Ababa Ethiopia urban history", "Somaliland Djibouti colonial", "Sudan Gezira Khartoum colonial"],
    "hal": ["Soudan anglo-egyptien", "Erythree Ethiopie coloniale", "Somalie Djibouti histoire", "Addis Abeba Ethiopie population", "Djibouti population urbaine"],
    "doaj": ["Sudan census population", "Eritrea colonial history", "Ethiopia urban history"],
    "plos": [], "wb": [],
    "ia": ["title:(Anglo-Egyptian Sudan) AND NOT reptiles", "title:(Sudan) AND (census OR population) AND NOT cia AND NOT dtic"],
    "pos_geo": ("sudan", "soudan", "anglo-egyptian", "khartoum", "omdurman", "darfur", "kordofan", "gezira", "ethiopia", "ethiopie", "addis ababa", "addis abeba", "eritrea", "erythree", "asmara", "somaliland", "somalia", "somalie", "mogadishu", "djibouti", "horn of africa"),
    "excl_geo": ("west africa", "australia"),
  },
  {
    "group": "3.colonial_era", "folder": "4.colonial_east_africa", "stem": "colonial_east_africa",
    "arf_max": 2,
    "arf_inc": r"\b(coastal east africa and the western indian ocean|port cities and intruders)\b",
    "arf_exc": r"\b(west africa|senegal|gambia|mali|nigeria)\b",
    "issns": [("0021-8537", "Kenya Uganda Tanganyika colonial"), ("0145-2258", "Kenya Uganda Tanganyika"), ("2078-0389", "Kenya Uganda Tanganyika census"), ("0008-0055", "Rwanda Burundi Kenya Ouganda"), ("2308-7854", "Kenya Uganda Tanzania census")],
    "crossref": ["Kenya colonial census", "Uganda colonial census", "Tanganyika colonial population", "German East Africa population", "Ruanda-Urundi colonial demography", "Zanzibar colonial census"],
    "hal": ["Kenya Ouganda Tanzanie", "Ruanda-Urundi demographie", "Afrique orientale coloniale"],
    "doaj": ["Kenya colonial census", "Tanganyika colonial population", "Uganda colonial population"],
    "plos": [], "wb": [],
    "ia": ["title:(Uganda) AND (census OR blue book) AND NOT cia", "title:(Kenya) AND (census OR colony) AND NOT cia"],
    "pos_geo": ("east africa", "afrique orientale", "kenya", "nairobi", "mombasa", "uganda", "ouganda", "kampala", "tanganyika", "tanzania", "tanzanie", "dar es salaam", "german east africa", "ruanda-urundi", "rwanda", "burundi", "zanzibar"),
    "excl_geo": ("australia", "west africa"),
  },
  {
    "group": "3.colonial_era", "folder": "5.colonial_south_central", "stem": "colonial_south_central",
    "arf_max": 1,
    "arf_inc": r"\b(pre-colonial states of central malawi)\b",
    "arf_exc": r"\b(west africa|senegal|gambia|mali|nigeria)\b",
    "issns": [("0305-7070", "Rhodesia Zambia Malawi Mozambique"), ("0021-8537", "Rhodesia Nyasaland Mozambique"), ("0145-2258", "Rhodesia Zambia Malawi Mozambique"), ("1645-3794", "Mocambique colonial populacao"), ("1257-0273", "Mozambique colonial"), ("2078-0389", "Rhodesia Zambia Malawi"), ("0373-5834", "Mozambique Zambie Zimbabwe")],
    "crossref": ["Northern Rhodesia census", "Southern Rhodesia census", "Nyasaland Malawi colonial", "Mozambique colonial census", "Copperbelt Zambia migration", "Zimbabwe Rhodesia urbanization"],
    "hal": ["Mozambique colonial population", "Zambie Zimbabwe Malawi", "Lourenco Marques Maputo", "Rhodesie Zambie demographie"],
    "doaj": ["Southern Rhodesia population", "Northern Rhodesia Zambia", "Mozambique colonial population"],
    "plos": [], "wb": [],
    "ia": ["title:(Northern Rhodesia) AND (census OR report) AND NOT cia", "title:(Southern Rhodesia) AND (census OR population) AND NOT cia"],
    "pos_geo": ("northern rhodesia", "southern rhodesia", "rhodesia", "rhodesie", "zambia", "zambie", "copperbelt", "lusaka", "zimbabwe", "salisbury", "harare", "bulawayo", "nyasaland", "malawi", "mozambique", "mocambique", "lourenco marques", "maputo", "beira", "zambezia"),
    "excl_geo": ("australia", "ethiopia"),
  },
  {
    "group": "3.colonial_era", "folder": "6.modern_southern_africa", "stem": "modern_southern_africa",
    "arf_max": 2,
    "arf_inc": r"\b(historical population estimates|demographics of empire)\b",
    "arf_exc": r"\b(west africa|senegal|gambia|mali|nigeria)\b",
    "issns": [("2308-7854", "South Africa Botswana Namibia census"), ("1435-9871", "South Africa Namibia Botswana"), ("0305-7070", "South Africa urbanization census"), ("2078-0389", "South Africa census demography"), ("0259-0190", "South Africa population"), ("2035-5556", "South Africa fertility mortality")],
    "crossref": ["South Africa population census", "South Africa urbanization migration", "Namibia population census", "Botswana Lesotho Eswatini census"],
    "hal": ["Afrique du Sud recensement", "Namibie Botswana Lesotho population"],
    "doaj": ["South Africa population census", "Botswana Namibia population", "Lesotho Eswatini population"],
    "plos": [],
    "wb": ["South Africa urbanization", "Botswana urbanization", "Namibia urbanization"],
    "ia": ["title:(census) AND \"South Africa\" AND NOT cheetah AND NOT paranormal"],
    "pos_geo": ("south africa", "afrique du sud", "johannesburg", "cape town", "durban", "pretoria", "witwatersrand", "gauteng", "kwazulu", "namibia", "namibie", "south west africa", "windhoek", "botswana", "bechuanaland", "gaborone", "lesotho", "basutoland", "maseru", "eswatini", "swaziland"),
    "excl_geo": ("cape york", "australia", "niger"),
  },

  # --- 4.post_colonial ---
  {
    "group": "4.post_colonial", "folder": "1.modern_african_islands", "stem": "modern_african_islands",
    "arf_max": 1,
    "arf_inc": r"\b(perception and realization of space in merina)\b",
    "arf_exc": r"\b(16th|17th)\b",
    "issns": [("1435-9871", "Madagascar Mauritius Reunion Cabo Verde"), ("2308-7854", "Madagascar Mauritius Seychelles Comoros"), ("0032-4663", "Madagascar Reunion Mayotte Maurice"), ("1645-3794", "Cabo Verde Sao Tome populacao"), ("1257-0273", "Cabo Verde Sao Tome Madagascar"), ("2035-5556", "Mauritius Madagascar Reunion"), ("0373-5834", "Madagascar Reunion Maurice Comores"), ("0765-0752", "Cabo Verde Comores Madagascar migration"), ("1278-3986", "Madagascar Antananarivo urbanisation")],
    "crossref": ["Madagascar population census", "Mauritius demographic transition", "Reunion population INSEE", "Cabo Verde population census", "Mayotte Comoros census", "Sao Tome Seychelles population", "Antananarivo urbanization Madagascar", "Mauritius fertility mortality"],
    "hal": ["Madagascar population recensement", "Reunion INSEE population", "Mayotte Comores recensement", "Maurice Seychelles demographie", "Cap-Vert demographie", "Antananarivo urbanisation"],
    "doaj": ["Madagascar population census", "Mauritius demographic transition", "Cabo Verde Sao Tome population", "Reunion Mayotte population"],
    "plos": [],
    "wb": ["Madagascar urbanization", "Mauritius systematic country", "Cabo Verde urbanization", "Comoros population", "Sao Tome urbanization", "Seychelles population"],
    "ia": [],
    "pos_geo": ("madagascar", "antananarivo", "mauritius", "maurice", "port louis", "reunion", "la reunion", "mayotte", "comoros", "comores", "seychelles", "cabo verde", "cape verde", "cap-vert", "sao tome", "principe", "saint helena"),
    "excl_geo": ("western sahara", "australia"),
  },
  {
    "group": "4.post_colonial", "folder": "2.postcolonial_sahel", "stem": "postcolonial_sahel",
    "arf_max": 1,
    "arf_inc": r"\b(bamako)\b",
    "arf_exc": r"\b(15th|16th|17th|medieval)\b",
    "issns": [("1435-9871", "Senegal Mali Burkina Niger Sahel"), ("2308-7854", "Senegal Mali Burkina Niger Chad"), ("0032-4663", "Senegal Mali Burkina Niger Sahel"), ("2035-5556", "Senegal Mali Burkina Niger"), ("0008-0055", "Dakar Bamako Ouagadougou Niamey"), ("0373-5834", "Dakar Bamako Ouagadougou Niamey"), ("1278-3986", "Senegal Mali Burkina urbanisation"), ("0765-0752", "Senegal Mali Mauritanie migration")],
    "crossref": ["Senegal population census", "Mali Bamako urbanization", "Burkina Faso Ouagadougou population", "Niger fertility census", "Chad Mauritania Gambia population", "Dakar demographic urban"],
    "hal": ["Senegal Dakar recensement", "Mali Bamako population", "Burkina Faso Ouagadougou population", "Niger Niamey demographie", "Tchad Mauritanie Gambie population", "Ouagadougou croissance urbaine"],
    "doaj": ["Senegal Mali Burkina population", "Niger Chad Mauritania population"],
    "plos": [],
    "wb": ["Senegal urbanization", "Mali urbanization", "Burkina Faso urbanization", "Niger urbanization", "Chad urbanization", "Mauritania urbanization", "Gambia urbanization"],
    "ia": [],
    "pos_geo": ("sahel", "senegal", "dakar", "mauritania", "mauritanie", "nouakchott", "mali", "bamako", "burkina faso", "ouagadougou", "niger", "niamey", "chad", "tchad", "ndjamena", "n djamena", "gambia", "banjul"),
    "excl_geo": ("nigeria", "australia"),
  },
  {
    "group": "4.post_colonial", "folder": "3.postcolonial_west_africa", "stem": "postcolonial_west_africa",
    "arf_max": 1,
    "arf_inc": r"\b(questions in african demographic history)\b",
    "arf_exc": r"\b(15th|16th|17th|medieval)\b",
    "issns": [("1435-9871", "Nigeria Ghana Cote d'Ivoire Togo Benin"), ("2308-7854", "Nigeria Ghana Sierra Leone Liberia"), ("0032-4663", "Cote d'Ivoire Abidjan Benin Togo Guinee"), ("2035-5556", "Nigeria Ghana Cote d'Ivoire")],
    "crossref": ["Nigeria population census", "Nigeria Lagos urbanization", "Ghana population census", "Cote d'Ivoire Abidjan urbanization", "Sierra Leone Liberia Togo Benin population"],
    "hal": ["Cote d'Ivoire Abidjan population", "Benin Togo Guinee population", "Nigeria Ghana croissance urbaine"],
    "doaj": ["Nigeria population urbanization", "Ghana population census", "Cote d'Ivoire Benin population"],
    "plos": [],
    "wb": ["Nigeria urbanization", "Ghana urbanization", "Cote d'Ivoire urbanization", "Sierra Leone urbanization", "Togo Benin urbanization"],
    "ia": [],
    "pos_geo": ("nigeria", "lagos", "ibadan", "kano", "abuja", "ghana", "accra", "kumasi", "cote d ivoire", "ivory coast", "abidjan", "guinea", "guinee", "conakry", "sierra leone", "freetown", "liberia", "monrovia", "togo", "lome", "benin", "cotonou", "guinea-bissau", "bissau", "west africa"),
    "excl_geo": ("australia", "ethiopia"),
  },
  {
    "group": "4.post_colonial", "folder": "4.postcolonial_congo_angola", "stem": "postcolonial_congo_angola",
    "arf_max": 0, "arf_inc": r"$^", "arf_exc": r".*",
    "issns": [("1435-9871", "Congo Cameroon Gabon Angola"), ("2308-7854", "Cameroon Congo Gabon Angola"), ("0032-4663", "Congo Cameroun Gabon Centrafrique"), ("1645-3794", "Angola Luanda populacao"), ("1257-0273", "Angola Luanda population"), ("2035-5556", "Cameroon Congo Angola"), ("0373-5834", "Kinshasa Brazzaville Douala Yaounde Libreville"), ("1278-3986", "Kinshasa Cameroun Gabon urbanisation"), ("0008-0055", "Kinshasa Brazzaville Douala Luanda")],
    "crossref": ["Kinshasa Congo urbanization", "Angola Luanda census", "Cameroon Yaounde Douala urbanization", "Gabon Brazzaville Central African Republic", "Cameroon population census fertility", "Democratic Republic of Congo census"],
    "hal": ["Congo Kinshasa population", "Cameroun Yaounde Douala population", "Gabon Congo Brazzaville demographie", "Angola Luanda population", "Centrafrique Bangui population", "Urbanisation Kinshasa Lubumbashi"],
    "doaj": ["Congo Kinshasa urbanization", "Angola Luanda population", "Cameroon Gabon urbanization", "Cameroon fertility mortality"],
    "plos": [],
    "wb": ["Congo Democratic Republic urbanization", "Angola urbanization", "Cameroon urbanization", "Gabon urbanization", "Congo Brazzaville urbanization", "Central African Republic urbanization"],
    "ia": [],
    "pos_geo": ("congo", "kinshasa", "lubumbashi", "brazzaville", "pointe-noire", "angola", "luanda", "huambo", "cameroon", "cameroun", "yaounde", "douala", "gabon", "libreville", "central african republic", "centrafrique", "bangui", "equatorial guinea", "malabo"),
    "excl_geo": ("nigeria", "australia"),
  },
  {
    "group": "4.post_colonial", "folder": "5.postcolonial_horn_sudan", "stem": "postcolonial_horn_sudan",
    "arf_max": 0, "arf_inc": r"$^", "arf_exc": r".*",
    "issns": [("1435-9871", "Ethiopia Sudan Somalia Eritrea"), ("2308-7854", "Ethiopia Sudan South Sudan"), ("2035-5556", "Ethiopia Sudan Somalia"), ("0032-4663", "Ethiopie Soudan Djibouti Somalie"), ("0373-5834", "Addis Abeba Djibouti Khartoum"), ("1278-3986", "Ethiopie Soudan Djibouti urbanisation")],
    "crossref": ["Ethiopia population census", "Addis Ababa urbanization", "Sudan Khartoum census", "South Sudan Juba population", "Somalia Eritrea Djibouti urbanization", "Ethiopia fertility mortality"],
    "hal": ["Ethiopie Addis Abeba population", "Soudan Khartoum population", "Djibouti Somalie Erythree population"],
    "doaj": ["Ethiopia population census", "Sudan South Sudan population", "Somalia Eritrea population"],
    "plos": [],
    "wb": ["Ethiopia urbanization", "Sudan urbanization", "South Sudan urbanization", "Somalia urbanization", "Djibouti urbanization"],
    "ia": [],
    "pos_geo": ("ethiopia", "ethiopie", "addis ababa", "addis abeba", "amhara", "oromia", "tigray", "sudan", "soudan", "khartoum", "darfur", "south sudan", "juba", "somalia", "somalie", "somaliland", "mogadishu", "hargeisa", "eritrea", "erythree", "asmara", "djibouti"),
    "excl_geo": ("australia", "nigeria"),
  },
  {
    "group": "4.post_colonial", "folder": "6.postcolonial_east_africa", "stem": "postcolonial_east_africa",
    "arf_max": 1,
    "arf_inc": r"\b(long term population dynamics in africa)\b",
    "arf_exc": r"\b(15th|16th|17th|medieval)\b",
    "issns": [("1435-9871", "Kenya Tanzania Uganda Rwanda Burundi"), ("2308-7854", "Kenya Tanzania Uganda Rwanda"), ("2035-5556", "Kenya Tanzania Uganda Rwanda"), ("0032-4663", "Kenya Tanzanie Ouganda Rwanda Burundi")],
    "crossref": ["Kenya population census", "Tanzania Dar es Salaam urbanization", "Uganda Kampala census", "Rwanda Burundi census population"],
    "hal": ["Kenya Nairobi population", "Tanzanie Dar es Salaam population", "Ouganda Rwanda Burundi demographie"],
    "doaj": ["Kenya Tanzania Uganda census", "Rwanda Burundi population"],
    "plos": [],
    "wb": ["Kenya urbanization", "Tanzania urbanization", "Uganda urbanization", "Rwanda urbanization", "Burundi urbanization"],
    "ia": [],
    "pos_geo": ("kenya", "nairobi", "mombasa", "tanzania", "tanzanie", "dar es salaam", "dodoma", "zanzibar", "uganda", "ouganda", "kampala", "rwanda", "kigali", "burundi", "bujumbura", "east africa", "afrique orientale"),
    "excl_geo": ("australia", "ethiopia"),
  },
  {
    "group": "4.post_colonial", "folder": "7.postcolonial_south_central", "stem": "postcolonial_south_central",
    "arf_max": 0, "arf_inc": r"$^", "arf_exc": r".*",
    "issns": [("1435-9871", "Zambia Zimbabwe Malawi Mozambique"), ("2308-7854", "Zambia Zimbabwe Malawi Mozambique"), ("2035-5556", "Zambia Zimbabwe Malawi Mozambique"), ("1645-3794", "Mocambique Maputo populacao"), ("1257-0273", "Mozambique Maputo population")],
    "crossref": ["Zambia population census", "Zimbabwe population census", "Malawi population census", "Mozambique Maputo census", "Lusaka Harare urbanization"],
    "hal": ["Mozambique Maputo population", "Zambie Lusaka population", "Zimbabwe Malawi population"],
    "doaj": ["Zambia Zimbabwe Malawi census", "Mozambique population census"],
    "plos": [],
    "wb": ["Zambia urbanization", "Zimbabwe urbanization", "Malawi urbanization", "Mozambique urbanization"],
    "ia": [],
    "pos_geo": ("zambia", "zambie", "lusaka", "copperbelt", "zimbabwe", "harare", "bulawayo", "malawi", "lilongwe", "blantyre", "mozambique", "mocambique", "maputo", "beira", "nampula", "zambezia"),
    "excl_geo": ("ethiopia", "australia", "nigeria"),
  },
]


def fold_accents(s):
  return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii").lower()


def clean_text(s):
  if not s:
    return ""
  s = re.sub(r"<[^>]+>", " ", str(s))
  s = re.sub(r"\s+", " ", s).strip()
  return s


def ascii_slug(s):
  s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")
  s = re.sub(r"[^a-zA-Z0-9]+", "_", s.lower()).strip("_")
  return s


def norm_domain(url_or_pub):
  s = str(url_or_pub or "").strip().lower()
  if s.startswith("http"):
    netloc = urllib.parse.urlparse(s).netloc.lower()
    if netloc.startswith("www."):
      netloc = netloc[4:]
    return netloc or "unknown"
  return ascii_slug(s)[:32] or "unknown"


def is_banned(title, authors, url="", extra=""):
  blob = fold_accents(" ".join([
    str(title or ""),
    " ".join(authors) if isinstance(authors, list) else str(authors or ""),
    str(url or ""),
    str(extra or ""),
  ]))
  if any(b in blob for b in BANNED_TOKENS):
    return True
  if any(h in str(url or "").lower() for h in BANNED_HOSTS):
    return True
  if any(t in blob for t in OFFTOPIC_TERMS):
    return True
  return False


def author_surname(authors):
  first_a = authors[0] if authors else "author"
  if "," in first_a:
    s = first_a.split(",")[0].strip()
  else:
    parts = first_a.strip().split()
    s = parts[-1] if parts else "author"
  return ascii_slug(s)[:14] or "author"


def make_clean_filename(authors, year, title, pdir, h6):
  a_slug = author_surname(authors)
  stop = {
    "the", "of", "and", "in", "to", "a", "an", "for", "on", "with", "from",
    "by", "as", "at", "de", "la", "el", "en", "los", "las", "del", "y",
    "le", "les", "des", "du", "et", "dans", "sur", "pour", "par", "une",
    "un", "study", "case", "towards", "perspective", "perspectives",
  }
  words = [w for w in ascii_slug(title).split("_") if w and w not in stop]
  t_slug = "_".join(words)[:32].strip("_") or "study"
  yr_s = str(year or 2000)
  rel_dir = os.path.relpath(pdir, SVEA_ROOT).replace("\\", "/")
  max_fn = min(MAX_FILENAME_LEN, MAX_RELPATH_LEN - len(rel_dir) - 1)
  base = f"{a_slug}_{yr_s}_{t_slug}"
  fn = f"{base[:max_fn - 4].strip('_')}.pdf"
  if os.path.exists(os.path.join(pdir, fn)):
    fn = f"{base[:max_fn - 11].strip('_')}_{h6}.pdf"
  return fn


def make_bib_key(authors, year, title, used_keys):
  a = re.sub(r"[^A-Za-z]", "", author_surname(authors).title()) or "Author"
  words = [w for w in ascii_slug(title).split("_") if len(w) > 2][:2]
  tw = "".join(w.title() for w in words) or "Study"
  base = f"{a}{year or 2000}{tw}"
  key = base
  n = 2
  while key in used_keys:
    key = f"{base}_{n}"
    n += 1
  used_keys.add(key)
  return key


def validate_pdf_bytes(data):
  if not data or len(data) < MIN_BYTES or len(data) > MAX_BYTES:
    return None
  if not data.startswith(b"%PDF-"):
    return None
  try:
    doc = pymupdf.open(stream=data, filetype="pdf")
    if doc.needs_pass or len(doc) < 1:
      doc.close()
      return None
    pages = len(doc)
    _ = doc[0].get_text("text")
    doc.close()
    return pages
  except Exception:
    return None


def validate_pdf_file(fp):
  if not os.path.isfile(fp):
    return None
  sz = os.path.getsize(fp)
  if sz < MIN_BYTES or sz > MAX_BYTES:
    return None
  try:
    with open(fp, "rb") as fh:
      if not fh.read(5).startswith(b"%PDF-"):
        return None
    doc = pymupdf.open(fp)
    if doc.needs_pass or len(doc) < 1:
      doc.close()
      return None
    pages = len(doc)
    _ = doc[0].get_text("text")
    doc.close()
    return pages
  except Exception:
    return None


def extract_arf_metadata(fp, arf_entry):
  title = clean_text(arf_entry.get("pdf_title") or "")
  fn_stem = os.path.splitext(arf_entry["filename"])[0]
  if not title or len(title) < 6 or any(x in title.lower() for x in ("untitled", "sometitle", ".indd", ".doc", ".tif", "microsoft word", "c:\\", "g:\\", "article ")):
    title = clean_text(fn_stem.replace("_", "'"))
  authors = []
  if arf_entry.get("pdf_author"):
    authors = [clean_text(arf_entry["pdf_author"])]
  year = None
  pub = ""
  doi = ""
  url = ""

  try:
    doc = pymupdf.open(fp)
    txt = "\n".join(doc[i].get_text("text") for i in range(min(3, len(doc))))
    doc.close()
  except Exception:
    txt = arf_entry.get("first_page_snippet") or ""

  m_auth = re.search(r"Author\(s\):\s*([^\n\r]+?)(?:\s+Source:|\s+Published|\r|\n)", txt)
  if m_auth and not authors:
    raw_a = clean_text(m_auth.group(1))
    authors = [a.strip() for a in re.split(r"\s+and\s+|,\s+(?=[A-Z])|;", raw_a) if a.strip()][:5]
  m_src = re.search(r"Source:\s*([^\n\r]+?)(?:,\s*Vol|\s*\(\d{4}\)|\s+Published|\r|\n)", txt)
  if m_src:
    pub = clean_text(m_src.group(1))
  m_pub = re.search(r"Published by:\s*([^\n\r]+?)(?:\s+Stable URL|\r|\n)", txt)
  if m_pub and not pub:
    pub = clean_text(m_pub.group(1))
  m_jstor = re.search(r"https?://www\.jstor\.org/stable/\d+", txt)
  if m_jstor:
    url = m_jstor.group(0)
  m_hal = re.search(r"https?://hal[^\s\)]+", txt)
  if m_hal and not url:
    url = m_hal.group(0)
  m_doi = re.search(r"\b(10\.\d{4,9}/[^\s\"\'<>\]\)\,;]+)", txt)
  if m_doi:
    cand_doi = m_doi.group(1).rstrip(".,;:")
    if not cand_doi.startswith("10.5555/") and "zenodo" not in cand_doi.lower():
      doi = cand_doi
      if not url:
        url = f"https://doi.org/{doi}"

  m_yr = re.search(r"\b(18\d{2}|19\d{2}|20[0-2]\d)\b", txt[:1500]) or re.search(r"\b(18\d{2}|19\d{2}|20[0-2]\d)\b", fn_stem)
  if m_yr:
    year = int(m_yr.group(1))

  tl = txt.lower()
  if not pub:
    for p_name in (
      "Cambridge University Press", "Oxford University Press", "Journal of African History",
      "International African Institute", "Ohio University Press", "James Currey",
      "Taylor & Francis", "Routledge", "Brill", "Springer", "Elsevier", "PLOS ONE",
      "Cahiers d'Études Africaines", "EHESS", "IFAN", "ORSTOM", "IRD", "Nordic Africa Institute",
      "Historical Society of Nigeria", "South African Archaeological Society",
      "African Economic History", "Journal of African Archaeology", "History in Africa",
      "Northeast African Studies", "Azania", "African Studies Review",
    ):
      if p_name.lower() in tl:
        pub = p_name
        break
  if not pub:
    if "gambian studies" in fn_stem.lower():
      pub = "Gambian Studies (St. Mary's College / San Francisco)"
      if not authors:
        authors = ["David P. Gamble"]
    else:
      pub = f"Africa Research Files ({arf_entry['top_folder']})"

  if not doi and len(title) >= 12:
    try:
      r = requests.get(
        "https://api.crossref.org/works",
        params={"query.title": title[:140], "rows": 1},
        headers=API_HEADERS,
        timeout=8,
      )
      if r.status_code == 200:
        items = r.json().get("message", {}).get("items", [])
        if items:
          it = items[0]
          cr_t = clean_text((it.get("title") or [""])[0])
          sim = difflib.SequenceMatcher(None, ascii_slug(title), ascii_slug(cr_t)).ratio()
          if sim >= 0.84:
            cr_doi = it.get("DOI") or ""
            if cr_doi and "zenodo" not in cr_doi.lower():
              doi = cr_doi
              url = f"https://doi.org/{doi}"
            if not pub or "Africa Research Files" in pub:
              pub = clean_text((it.get("container-title") or [it.get("publisher") or ""])[0]) or pub
            if not authors and it.get("author"):
              authors = [clean_text(f"{a.get('given', '')} {a.get('family', '')}") for a in it["author"][:5] if a.get("family")]
            if not year:
              dp = ((it.get("published-print") or it.get("published-online") or it.get("issued") or {}).get("date-parts") or [[None]])[0]
              if dp and dp[0]:
                year = int(dp[0])
    except Exception:
      pass

  if not authors:
    authors = ["Archival Monograph"]
  if not year:
    year = 2000
  if not url:
    url = f"https://scholar.google.com/scholar?q={urllib.parse.quote(title[:100])}"

  dom = norm_domain(pub if (pub and not pub.startswith("Africa Research Files")) else url)
  return {
    "title": title,
    "authors": authors,
    "year": year,
    "journal_or_publisher": pub,
    "publisher_domain": dom,
    "doi": doi,
    "url": url,
  }


def select_arf_for_chapter(ch, arf_pool, global_sha, global_title_slugs):
  inc_re = re.compile(ch["arf_inc"], re.I)
  exc_re = re.compile(ch["arf_exc"], re.I)
  picked = []
  author_cnt = {}

  for x in arf_pool:
    if len(picked) >= ch["arf_max"]:
      break
    if x["sha256"] in global_sha:
      continue
    fn_title = os.path.splitext(x["filename"])[0]
    t_slug = ascii_slug(x.get("pdf_title") or fn_title)[:45]
    fn_slug = ascii_slug(re.sub(r"\(\d+\)$", "", fn_title))[:45]
    if t_slug in global_title_slugs or fn_slug in global_title_slugs:
      continue

    blob = " ".join([fn_title, x["subfolder"], x.get("pdf_title") or ""]).lower()
    if not inc_re.search(blob):
      continue
    if exc_re.search(blob):
      continue

    fp = os.path.join(ARF_ROOT, x["rel_path"])
    pages = validate_pdf_file(fp)
    if not pages:
      continue

    meta = extract_arf_metadata(fp, x)
    if is_banned(meta["title"], meta["authors"], meta["url"], meta["journal_or_publisher"]):
      continue
    a_key = author_surname(meta["authors"])
    if author_cnt.get(a_key, 0) >= 2:
      continue

    with open(fp, "rb") as fh:
      sha = hashlib.sha256(fh.read()).hexdigest()
    if sha in global_sha:
      continue

    author_cnt[a_key] = author_cnt.get(a_key, 0) + 1
    global_sha.add(sha)
    global_sha.add(x["sha256"])
    global_title_slugs.add(t_slug)
    global_title_slugs.add(fn_slug)
    picked.append((fp, sha, pages, meta))
  return picked


def relevance_score(ch, title, journal):
  t_fold = fold_accents(title)
  j_fold = fold_accents(journal)
  blob = f"{t_fold} {j_fold}"
  if any(eg in blob for eg in ch.get("excl_geo", ())):
    return 0
  geo_hits = sum(1 for g in ch["pos_geo"] if g in blob)
  top_hits = sum(1 for t in STRICT_TOPIC_TERMS if t in t_fold)
  if geo_hits == 0 or top_hits == 0:
    return 0
  return geo_hits * 3 + top_hits * 3


def resolve_crossref_items(items, ch):
  cands = []
  for it in items:
    doi = it.get("DOI") or ""
    if not doi or "zenodo" in doi.lower():
      continue
    title = clean_text((it.get("title") or [""])[0])
    if not title:
      continue
    auths = [clean_text(f"{a.get('given', '')} {a.get('family', '')}") for a in (it.get("author") or [])[:6] if a.get("family")]
    if not auths:
      continue
    dp = ((it.get("published-print") or it.get("published-online") or it.get("issued") or {}).get("date-parts") or [[None]])[0]
    yr = int(dp[0]) if dp and dp[0] else None
    if not yr:
      continue
    journal = clean_text((it.get("container-title") or [it.get("publisher") or "Journal"])[0])
    if is_banned(title, auths, doi, journal):
      continue
    if relevance_score(ch, title, journal) <= 0:
      continue
    pdf_urls = []
    for lk in (it.get("link") or []):
      if "pdf" in (lk.get("content-type") or "").lower() and lk.get("URL"):
        pdf_urls.append(lk["URL"])
    cands.append((it, doi, title, auths, yr, journal, pdf_urls))

  def resolve_up(entry):
    it, doi, title, auths, yr, journal, pdf_urls = entry
    try:
      up = requests.get(
        f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email=austkaeztchen@confoederatio.org",
        headers=API_HEADERS,
        timeout=8,
      )
      if up.status_code == 200:
        uj = up.json()
        best = uj.get("best_oa_location") or {}
        if best.get("url_for_pdf"):
          pdf_urls.insert(0, best["url_for_pdf"])
        elif best.get("url"):
          pdf_urls.append(best["url"])
        for loc in (uj.get("oa_locations") or [])[:3]:
          if loc.get("url_for_pdf") and loc["url_for_pdf"] not in pdf_urls:
            pdf_urls.append(loc["url_for_pdf"])
    except Exception:
      pass
    clean_urls = [u for u in pdf_urls if u.startswith("http") and not any(bh in u.lower() for bh in BANNED_HOSTS)]
    if not clean_urls:
      return None
    return {
      "title": title,
      "authors": auths,
      "year": yr,
      "journal_or_publisher": journal,
      "publisher_domain": norm_domain(clean_urls[0]),
      "doi": doi,
      "url": f"https://doi.org/{doi}",
      "pdf_url": clean_urls[0],
      "alt_pdf_urls": clean_urls[1:4],
      "cited_by": int(it.get("is-referenced-by-count") or 0),
      "source_api": "crossref_unpaywall",
    }

  out = []
  with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
    for res in ex.map(resolve_up, cands[:24]):
      if res:
        out.append(res)
  return out


def search_crossref_issn(issn, q, ch, rows=25):
  try:
    r = requests.get(
      f"https://api.crossref.org/journals/{issn}/works",
      params={"query": q, "rows": str(rows)},
      headers=API_HEADERS,
      timeout=12,
    )
    if r.status_code != 200:
      return []
    return resolve_crossref_items(r.json().get("message", {}).get("items", []), ch)
  except Exception:
    return []


def search_crossref_unpaywall(q, ch, rows=25):
  try:
    r = requests.get(
      "https://api.crossref.org/works",
      params={"query": q, "rows": str(rows)},
      headers=API_HEADERS,
      timeout=12,
    )
    if r.status_code != 200:
      return []
    return resolve_crossref_items(r.json().get("message", {}).get("items", []), ch)
  except Exception:
    return []


def search_hal(q, rows=25):
  url = "https://api.archives-ouvertes.fr/search/?" + urllib.parse.urlencode({
    "q": q, "fq": "submitType_s:file AND domain_s:*shs*",
    "fl": "docid,title_s,authFullName_s,producedDateY_i,doiId_s,uri_s,fileMain_s,journalTitle_s",
    "rows": str(rows), "wt": "json",
  })
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=14)
    if r.status_code != 200:
      return out
    for d in ((r.json().get("response") or {}).get("docs") or []):
      titles = d.get("title_s") or []
      title = clean_text(titles[0] if isinstance(titles, list) and titles else titles)
      auths = d.get("authFullName_s") or []
      yr = d.get("producedDateY_i")
      pdf_url = d.get("fileMain_s") or ""
      if not (title and auths and yr and pdf_url.startswith("http")):
        continue
      doi = clean_text(d.get("doiId_s") or "")
      uri = d.get("uri_s") or pdf_url
      journal = clean_text(d.get("journalTitle_s") or "HAL Archives Ouvertes")
      if is_banned(title, auths, pdf_url, journal):
        continue
      out.append({
        "title": title,
        "authors": auths[:6],
        "year": int(yr),
        "journal_or_publisher": journal,
        "publisher_domain": norm_domain(pdf_url),
        "doi": doi,
        "url": f"https://doi.org/{doi}" if doi else uri,
        "pdf_url": pdf_url,
        "alt_pdf_urls": [],
        "cited_by": 10,
        "source_api": "hal",
      })
  except Exception:
    pass
  return out


def search_doaj(q, page_size=20):
  url = f"https://doaj.org/api/search/articles/{urllib.parse.quote(q)}?pageSize={page_size}"
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=14)
    if r.status_code != 200:
      return out
    for it in (r.json().get("results") or []):
      bj = it.get("bibjson") or {}
      title = clean_text(bj.get("title"))
      auths = [clean_text(a.get("name")) for a in (bj.get("author") or [])[:6] if a.get("name")]
      yr_s = str(bj.get("year") or "")
      if not (title and auths and yr_s.isdigit()):
        continue
      doi = ""
      for ident in (bj.get("identifier") or []):
        if ident.get("type") == "doi" and ident.get("id"):
          doi = ident["id"]
          break
      links = [lk.get("url") for lk in (bj.get("link") or []) if lk.get("url")]
      if not links:
        continue
      journal = clean_text((bj.get("journal") or {}).get("title") or "DOAJ Open Access")
      if is_banned(title, auths, links[0], journal):
        continue
      out.append({
        "title": title,
        "authors": auths,
        "year": int(yr_s),
        "journal_or_publisher": journal,
        "publisher_domain": norm_domain(links[0]),
        "doi": doi,
        "url": f"https://doi.org/{doi}" if doi else links[0],
        "pdf_url": links[0],
        "alt_pdf_urls": links[1:3],
        "cited_by": 6,
        "source_api": "doaj",
      })
  except Exception:
    pass
  return out


def search_plos(q, rows=12):
  url = "https://api.plos.org/search?" + urllib.parse.urlencode({
    "q": q, "fl": "id,title_display,journal,publication_date,author_display",
    "rows": str(rows), "wt": "json",
  })
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=14)
    if r.status_code != 200:
      return out
    for d in ((r.json().get("response") or {}).get("docs") or []):
      doi = d.get("id") or ""
      if "/" not in doi or "annotation" in doi.lower():
        continue
      title = clean_text(d.get("title_display"))
      auths = d.get("author_display") or []
      yr_s = str(d.get("publication_date") or "")[:4]
      if not (title and auths and yr_s.isdigit()):
        continue
      journal = clean_text(d.get("journal") or "PLOS ONE")
      jl = journal.lower()
      slug_j = "plosgenetics" if "genetics" in jl else ("plospathogens" if "pathogens" in jl else "plosone")
      pdf_url = f"https://journals.plos.org/{slug_j}/article/file?id={urllib.parse.quote(doi)}&type=printable"
      if is_banned(title, auths, pdf_url, journal):
        continue
      out.append({
        "title": title,
        "authors": auths[:6],
        "year": int(yr_s),
        "journal_or_publisher": journal,
        "publisher_domain": "journals.plos.org",
        "doi": doi,
        "url": f"https://doi.org/{doi}",
        "pdf_url": pdf_url,
        "alt_pdf_urls": [],
        "cited_by": 10,
        "source_api": "plos",
      })
  except Exception:
    pass
  return out


def search_worldbank(q, rows=12):
  out = []
  wb_allow = ("urban", "population", "demograph", "migration", "census", "city", "cities", "spatial", "economic geography", "displacement", "systematic country")
  try:
    r = requests.get(
      "https://search.worldbank.org/api/v2/wds",
      params={"format": "json", "qterm": q, "fl": "display_title,pdfurl,docdt,docty,url,authors", "rows": str(rows)},
      headers=API_HEADERS,
      timeout=14,
    )
    if r.status_code != 200:
      return out
    for k, v in (r.json().get("documents") or {}).items():
      if not isinstance(v, dict) or not v.get("pdfurl"):
        continue
      title = clean_text(v.get("display_title"))
      if not title or not any(w in title.lower() for w in wb_allow):
        continue
      pdf_url = v["pdfurl"]
      dt = str(v.get("docdt") or "")[:4]
      yr = int(dt) if dt.isdigit() else 2018
      auths = ["World Bank"]
      if isinstance(v.get("authors"), dict):
        parsed_a = [clean_text(a.get("author")) for a in v["authors"].values() if isinstance(a, dict) and a.get("author")]
        if parsed_a:
          auths = parsed_a[:5]
      if is_banned(title, auths, pdf_url, "World Bank"):
        continue
      out.append({
        "title": title,
        "authors": auths,
        "year": yr,
        "journal_or_publisher": f"World Bank ({clean_text(v.get('docty') or 'Report')})",
        "publisher_domain": "documents.worldbank.org",
        "doi": "",
        "url": v.get("url") or pdf_url,
        "pdf_url": pdf_url,
        "alt_pdf_urls": [],
        "cited_by": 14,
        "source_api": "worldbank",
      })
  except Exception:
    pass
  return out


def search_archive_org(q, rows=6):
  out = []
  try:
    r = requests.get(
      "https://archive.org/advancedsearch.php",
      params={
        "q": f"({q}) AND mediatype:texts AND NOT (cia OR dtic OR zoology OR botany OR theology OR birds OR fishes OR australia)",
        "fl[]": ["identifier", "title", "year", "creator"],
        "output": "json", "rows": str(rows),
      },
      headers=API_HEADERS,
      timeout=12,
    )
    if r.status_code != 200:
      return out
    for d in (r.json().get("response") or {}).get("docs") or []:
      ident = d.get("identifier")
      title = clean_text(d.get("title"))
      if not (ident and title):
        continue
      yr_m = re.search(r"(\d{4})", str(d.get("year") or ""))
      yr = int(yr_m.group(1)) if yr_m else 1950
      creator = d.get("creator")
      auths = [clean_text(creator[0] if isinstance(creator, list) else creator)] if creator else ["Historical Archive"]
      if is_banned(title, auths, ident, "Archive.org"):
        continue
      meta = requests.get(f"https://archive.org/metadata/{ident}/files", timeout=10).json()
      pdfs = [
        f for f in meta.get("result", [])
        if str(f.get("name") or "").lower().endswith(".pdf")
        and MIN_BYTES < int(f.get("size") or 0) <= MAX_BYTES
      ]
      if not pdfs:
        continue
      pdfs.sort(key=lambda f: int(f.get("size") or 0))
      pdf_url = f"https://archive.org/download/{ident}/{urllib.parse.quote(pdfs[0]['name'])}"
      out.append({
        "title": title,
        "authors": auths,
        "year": yr,
        "journal_or_publisher": "Internet Archive Historical Monograph / Census",
        "publisher_domain": "archive.org",
        "doi": "",
        "url": f"https://archive.org/details/{ident}",
        "pdf_url": pdf_url,
        "alt_pdf_urls": [],
        "cited_by": 10,
        "source_api": "archive_org",
      })
  except Exception:
    pass
  return out


def fetch_url_bytes(url, timeout=20):
  try:
    r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True, stream=True)
    if r.status_code != 200:
      return None, "", url
    ct = (r.headers.get("Content-Type") or "").lower()
    chunks = []
    tot = 0
    for chunk in r.iter_content(chunk_size=65536):
      if chunk:
        chunks.append(chunk)
        tot += len(chunk)
        if tot > MAX_BYTES:
          return None, ct, r.url
    return b"".join(chunks), ct, r.url
  except Exception:
    return None, "", url


def resolve_and_download(cand):
  urls_to_try = [cand["pdf_url"]] + list(cand.get("alt_pdf_urls") or [])
  for u in urls_to_try:
    if not u or any(bh in u.lower() for bh in BANNED_HOSTS):
      continue
    data, ct, final_u = fetch_url_bytes(u)
    if not data or any(bh in final_u.lower() for bh in BANNED_HOSTS):
      continue
    pages = validate_pdf_bytes(data)
    if pages:
      c2 = dict(cand)
      d_final = norm_domain(final_u)
      if d_final and not any(bh in d_final for bh in BANNED_HOSTS):
        c2["publisher_domain"] = d_final
      return (c2, data, pages, final_u)

    if b"<html" in data[:2048].lower() or "html" in ct:
      html = data.decode("utf-8", errors="ignore")
      found = []
      for pat in (
        r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']',
        r'href=["\']([^"\']+/article/download/\d+/\d+(?:/\d+)?)["\']',
        r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']',
      ):
        for m in re.finditer(pat, html, re.I):
          nu = urllib.parse.urljoin(final_u, m.group(1))
          if nu not in found and not any(bh in nu.lower() for bh in BANNED_HOSTS):
            found.append(nu)
      for pdf2 in found[:2]:
        d2, _, fu2 = fetch_url_bytes(pdf2)
        if not d2 or any(bh in fu2.lower() for bh in BANNED_HOSTS):
          continue
        pages2 = validate_pdf_bytes(d2)
        if pages2:
          c2 = dict(cand)
          d_final = norm_domain(fu2)
          if d_final and not any(bh in d_final for bh in BANNED_HOSTS):
            c2["publisher_domain"] = d_final
          return (c2, d2, pages2, fu2)
  return None


def harvest_chapter(ch_idx, ch, arf_pool, global_sha, global_title_slugs, used_bib_keys):
  stem = ch["stem"]
  rel_ch = f"{ch['group']}/{ch['folder']}"
  pdir = os.path.join(NICETHI_DIR, ch["group"], ch["folder"], "papers")
  os.makedirs(pdir, exist_ok=True)
  meta_p = os.path.join(pdir, "papers_metadata.json")

  recs = []
  dom_used = {}
  author_used = {}
  seen_titles = set()
  seen_urls = set()

  if os.path.isfile(meta_p):
    for rec in json.load(open(meta_p, encoding="utf-8")):
      fp = os.path.join(pdir, rec.get("filename", ""))
      pages = validate_pdf_file(fp)
      if pages and len(rec.get("filename", "")) <= MAX_FILENAME_LEN:
        recs.append(rec)
        dom_used[rec["publisher_domain"]] = dom_used.get(rec["publisher_domain"], 0) + 1
        ak = author_surname(rec.get("authors", []))
        author_used[ak] = author_used.get(ak, 0) + 1
        seen_titles.add(ascii_slug(rec.get("title", ""))[:50])
        seen_urls.add(rec.get("url", ""))
        global_sha.add(rec["sha256"])
        if rec.get("suggested_bib_key"):
          used_bib_keys.add(rec["suggested_bib_key"])

  if len(recs) >= TARGET_PER_CHAPTER and len(dom_used) >= 6:
    print(f"[SKIP] [CH {ch_idx:02d}] {stem:28s}: {len(recs):2d} PDFs | {len(dom_used)} domains", flush=True)
    return recs

  # 1. Select Africa Research Files PDFs if below arf_max
  arf_cnt = sum(1 for r in recs if r.get("origin") == "africa_research_files")
  if arf_cnt < ch["arf_max"] and len(recs) < TARGET_PER_CHAPTER:
    picked_arf = select_arf_for_chapter(ch, arf_pool, global_sha, global_title_slugs)
    for src_fp, sha, pages, meta in picked_arf:
      if len(recs) >= TARGET_PER_CHAPTER or arf_cnt >= ch["arf_max"]:
        break
      tk = ascii_slug(meta["title"])[:50]
      if tk in seen_titles:
        continue
      ak = author_surname(meta["authors"])
      if author_used.get(ak, 0) >= 2:
        continue
      fn = make_clean_filename(meta["authors"], meta["year"], meta["title"], pdir, sha[:6])
      dst_fp = os.path.join(pdir, fn)
      shutil.copy2(src_fp, dst_fp)
      rel_path = os.path.relpath(dst_fp, SVEA_ROOT).replace("\\", "/")
      bib_key = make_bib_key(meta["authors"], meta["year"], meta["title"], used_bib_keys)
      rec = {
        "chapter_index": ch_idx,
        "chapter_stem": stem,
        "chapter_folder": rel_ch,
        "filename": fn,
        "rel_path": rel_path,
        "sha256": sha,
        "size_bytes": os.path.getsize(dst_fp),
        "page_count": pages,
        "origin": "africa_research_files",
        "title": meta["title"],
        "authors": meta["authors"],
        "year": meta["year"],
        "publisher_or_journal": meta["journal_or_publisher"],
        "publisher_domain": meta["publisher_domain"],
        "doi": meta["doi"],
        "url": meta["url"],
        "suggested_bib_key": bib_key,
      }
      recs.append(rec)
      arf_cnt += 1
      dom_used[rec["publisher_domain"]] = dom_used.get(rec["publisher_domain"], 0) + 1
      author_used[ak] = author_used.get(ak, 0) + 1
      seen_titles.add(tk)
      seen_urls.add(rec["url"])

  # 2. Gather Novel Open-Access Candidates
  need = max(0, TARGET_PER_CHAPTER - len(recs))
  if need > 0:
    pool = []
    seen_cand = set(seen_titles)

    def add_cand(c, forced_score=None):
      tk = ascii_slug(c.get("title", ""))[:50]
      if not tk or tk in seen_cand or tk in global_title_slugs or c.get("url") in seen_urls:
        return
      sc = forced_score if forced_score is not None else relevance_score(ch, c.get("title", ""), c.get("journal_or_publisher", ""))
      if sc <= 0:
        return
      seen_cand.add(tk)
      c2 = dict(c)
      c2["_score"] = sc
      pool.append(c2)

    for issn, iq in ch.get("issns", []):
      for c in search_crossref_issn(issn, iq, ch, rows=25):
        add_cand(c, forced_score=max(15, relevance_score(ch, c.get("title", ""), c.get("journal_or_publisher", ""))))
    for q in ch["crossref"]:
      for c in search_crossref_unpaywall(q, ch, rows=25):
        add_cand(c)
    for q in ch["hal"]:
      for c in search_hal(q, rows=25):
        add_cand(c)
    for q in ch["doaj"]:
      for c in search_doaj(q, page_size=20):
        add_cand(c)
    for q in ch["plos"]:
      for c in search_plos(q, rows=12):
        add_cand(c)
    for q in ch["wb"]:
      for c in search_worldbank(q, rows=12):
        add_cand(c, forced_score=max(14, relevance_score(ch, c.get("title", ""), "World Bank")))
    for q in ch["ia"]:
      for c in search_archive_org(q, rows=6):
        add_cand(c)

    by_dom = {}
    for c in pool:
      by_dom.setdefault(c["publisher_domain"], []).append(c)
    for d in by_dom:
      by_dom[d].sort(key=lambda x: (-x["_score"], -x.get("cited_by", 0), -x.get("year", 0)))

    dom_order = sorted(by_dom.keys(), key=lambda d: (dom_used.get(d, 0), -by_dom[d][0]["_score"]))
    ordered = []
    max_len = max((len(v) for v in by_dom.values()), default=0)
    for idx in range(min(max_len, 10)):
      for d in dom_order:
        if idx < len(by_dom[d]):
          ordered.append(by_dom[d][idx])

    pos = 0
    added = 0
    while added < need and pos < len(ordered) and pos < 220:
      batch = []
      while len(batch) < 12 and pos < len(ordered):
        c = ordered[pos]
        pos += 1
        d_cap = 4 if len(dom_used) >= 5 else 3
        if dom_used.get(c["publisher_domain"], 0) >= d_cap:
          continue
        if author_used.get(author_surname(c["authors"]), 0) >= 2:
          continue
        batch.append(c)
      if not batch:
        break

      with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(resolve_and_download, c) for c in batch]
        for fut in as_completed(futs):
          if added >= need:
            continue
          res = fut.result()
          if not res:
            continue
          cand, data, pages, final_u = res
          dom = cand["publisher_domain"]
          d_cap = 4 if len(dom_used) >= 5 else 3
          ak = author_surname(cand["authors"])
          if dom_used.get(dom, 0) >= d_cap or author_used.get(ak, 0) >= 2:
            continue
          sha = hashlib.sha256(data).hexdigest()
          if sha in global_sha:
            continue
          global_sha.add(sha)
          tk = ascii_slug(cand["title"])[:50]
          global_title_slugs.add(tk)
          fn = make_clean_filename(cand["authors"], cand["year"], cand["title"], pdir, sha[:6])
          fp = os.path.join(pdir, fn)
          with open(fp, "wb") as fh:
            fh.write(data)
          rel_path = os.path.relpath(fp, SVEA_ROOT).replace("\\", "/")
          bib_key = make_bib_key(cand["authors"], cand["year"], cand["title"], used_bib_keys)
          rec = {
            "chapter_index": ch_idx,
            "chapter_stem": stem,
            "chapter_folder": rel_ch,
            "filename": fn,
            "rel_path": rel_path,
            "sha256": sha,
            "size_bytes": len(data),
            "page_count": pages,
            "origin": "novel_oa",
            "source_api": cand.get("source_api", "oa"),
            "title": cand["title"],
            "authors": cand["authors"],
            "year": cand["year"],
            "publisher_or_journal": cand["journal_or_publisher"],
            "publisher_domain": dom,
            "doi": cand.get("doi", ""),
            "url": cand.get("url", final_u),
            "suggested_bib_key": bib_key,
          }
          recs.append(rec)
          dom_used[dom] = dom_used.get(dom, 0) + 1
          author_used[ak] = author_used.get(ak, 0) + 1
          added += 1

  with open(meta_p, "w", encoding="utf-8") as fh:
    json.dump(recs, fh, indent=2, ensure_ascii=False)

  arf_n = sum(1 for r in recs if r.get("origin") == "africa_research_files")
  oa_n = sum(1 for r in recs if r.get("origin") == "novel_oa")
  print(
    f"  [CH {ch_idx:02d}] {stem:28s}: {len(recs):2d} PDFs (ARF={arf_n:2d}, OA={oa_n:2d}) | "
    f"{len(dom_used):2d} domains",
    flush=True,
  )
  return recs


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--chapters", default="", help="Comma-separated chapter stems to process")
  args = parser.parse_args()
  only = {s.strip() for s in args.chapters.split(",") if s.strip()}

  with open(ARF_INDEX_PATH, encoding="utf-8") as fh:
    idx = json.load(fh)
  arf_raw = [x for x in idx["files"] if x.get("file_kind") == "pdf" and MIN_BYTES <= x.get("size_bytes", 0) <= MAX_BYTES]
  seen_arf = set()
  arf_pool = []
  for x in sorted(arf_raw, key=lambda z: -z.get("pop_urban_score", 0)):
    if x["sha256"] not in seen_arf:
      seen_arf.add(x["sha256"])
      blob = (x["filename"] + " " + x["subfolder"] + " " + (x.get("pdf_title") or "")).lower()
      if not any(b in blob for b in BANNED_TOKENS):
        arf_pool.append(x)

  global_sha = set()
  global_title_slugs = set()
  used_bib_keys = set()

  for ch in CHAPTERS:
    meta_p = os.path.join(NICETHI_DIR, ch["group"], ch["folder"], "papers", "papers_metadata.json")
    if os.path.isfile(meta_p):
      for rec in json.load(open(meta_p, encoding="utf-8")):
        if rec.get("sha256"):
          global_sha.add(rec["sha256"])
        if rec.get("title"):
          global_title_slugs.add(ascii_slug(rec["title"])[:50])
        if rec.get("suggested_bib_key"):
          used_bib_keys.add(rec["suggested_bib_key"])

  all_papers = []
  summary = {}
  t0 = time.time()
  print("[START] NICETHI Wave-2 Archival PDF Harvesting (Pass 3 - ISSN + HAL + Strict Relevance)...", flush=True)

  for idx_c, ch in enumerate(CHAPTERS, 1):
    if only and ch["stem"] not in only:
      meta_p = os.path.join(NICETHI_DIR, ch["group"], ch["folder"], "papers", "papers_metadata.json")
      recs = json.load(open(meta_p, encoding="utf-8")) if os.path.isfile(meta_p) else []
    else:
      recs = harvest_chapter(idx_c, ch, arf_pool, global_sha, global_title_slugs, used_bib_keys)
    all_papers.extend(recs)
    doms = sorted({r["publisher_domain"] for r in recs})
    zen = sum(1 for r in recs if "zenodo" in (r.get("url", "") + r.get("doi", "") + r.get("publisher_domain", "")).lower())
    linked = sum(1 for r in recs if r.get("doi") or str(r.get("url", "")).startswith("https://"))
    max_fn = max((len(r["filename"]) for r in recs), default=0)
    max_rp = max((len(r["rel_path"]) for r in recs), default=0)
    summary[ch["stem"]] = {
      "chapter_index": idx_c,
      "chapter_folder": f"{ch['group']}/{ch['folder']}",
      "pdf_count": len(recs),
      "arf_count": sum(1 for r in recs if r.get("origin") == "africa_research_files"),
      "novel_oa_count": sum(1 for r in recs if r.get("origin") == "novel_oa"),
      "distinct_domains": len(doms),
      "domains": doms,
      "max_filename_len": max_fn,
      "max_relpath_len": max_rp,
      "zenodo_count": zen,
      "linked_count": linked,
      "total_bytes": sum(r["size_bytes"] for r in recs),
      "total_pages": sum(r["page_count"] for r in recs),
    }

  manifest = {
    "project": "NICETHI",
    "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "total_chapters": len(CHAPTERS),
    "total_papers": len(all_papers),
    "unique_sha256": len({p["sha256"] for p in all_papers}),
    "min_chapter_pdfs": min((s["pdf_count"] for s in summary.values()), default=0),
    "min_chapter_domains": min((s["distinct_domains"] for s in summary.values()), default=0),
    "max_filename_len": max((s["max_filename_len"] for s in summary.values()), default=0),
    "max_relpath_len": max((s["max_relpath_len"] for s in summary.values()), default=0),
    "zenodo_total": sum(s["zenodo_count"] for s in summary.values()),
    "chapters_summary": summary,
    "papers": all_papers,
  }
  with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2, ensure_ascii=False)

  elapsed = time.time() - t0
  print(
    f"\n[DONE] {len(all_papers)} unique verified PDFs across 23 chapters in {elapsed:.1f}s "
    f"(min_pdfs={manifest['min_chapter_pdfs']}, min_domains={manifest['min_chapter_domains']}, "
    f"max_fn={manifest['max_filename_len']}, max_rp={manifest['max_relpath_len']}, zenodo={manifest['zenodo_total']})",
    flush=True,
  )


if __name__ == "__main__":
  main()
