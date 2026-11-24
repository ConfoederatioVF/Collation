"""Stage C Wave 2 Archival PDF Harvester for Operation Viscount Project JAGUAR.

Downloads and verifies >= 15 (target 18) SHA-256-unique valid %PDF- scholarly
monographs, journal articles, archaeological reports, and official census
publications (> 12 kB, pymupdf-readable >= 1 page, filename <= 68 chars,
repo-relative path <= 176 chars) into every one of the 14 JAGUAR chapter
`papers/` folders, with >= 5 distinct scholarly publisher domains per chapter,
0% Zenodo, 0% crowd sources, and zero prohibited global compilations.

Sources queried:
  1. OpenAlex OA API (academic journals, university presses, SciELO, Redalyc,
     UNAM, COLMEX, Cambridge, Nature, PNAS, Antiquity, World Bank, PAHO, etc.)
  2. DOAJ API (Latin American, Caribbean & international OJS open-access journals)
  3. EuropePMC / PMC (direct open-access PDF render for paleodemography, aDNA,
     epidemics, cocoliztli, Caribbean & Mesoamerican population studies)
  4. PLOS API (PLOS ONE / PLOS Genetics / PLOS Pathogens direct printable PDFs)
  5. HAL Archives Ouvertes (CNRS / CEMCA / French Caribbean & Mesoamerican studies)
  6. CEPAL / CELADE Digital Repository (official UN demographic & census reports)
  7. Demographic Research (MPIDR Rostock) & curated US Census Bureau historical PDFs
"""

import hashlib
import json
import os
import re
import time
import unicodedata
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import pymupdf
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
JAGUAR_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JAGUAR"
)
ITIN_PATH = os.path.join(JAGUAR_DIR, "jaguar_itinerary.json5")
MANIFEST_PATH = os.path.join(JAGUAR_DIR, "_shared", "wave2_papers_manifest.json")

HEADERS = {
  "User-Agent": (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36 "
    "(OperationViscount-JAGUAR-Harvester/1.0; mailto:research@confoederatio.org)"
  ),
  "Accept": "application/pdf,text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}

API_HEADERS = {
  "User-Agent": "OperationViscount-JAGUAR-Harvester/1.0 (mailto:research@confoederatio.org)"
}

TARGET_PER_CHAPTER = 18
MIN_BYTES = 12288
MAX_BYTES = 28 * 1024 * 1024
MAX_WORKERS = 4
MAX_FILENAME_LEN = 68
MAX_RELPATH_LEN = 176

BANNED_AUTHORS = (
  "mcevedy",
  "colin mcevedy",
  "richard jones",
  "klein goldewijk",
  "goldewijk",
  "maddison",
  "angus maddison",
  "tertia",
  "tertius chandler",
  "chandler, tertius",
  "modelski",
  "george modelski",
  "populstat",
)

BANNED_TITLE_PHRASES = (
  "hyde 3",
  "hyde 2",
  "populstat",
  "maddison project",
  "atlas of world population history",
  "four thousand years of urban growth",
  "world cities: -3000 to 2000",
)

BANNED_HOSTS = (
  "zenodo.org",
  "wikidata.org",
  "wikipedia.org",
  "wikimedia.org",
  "openstreetmap.org",
  "geonames.org",
  "researchgate.net",
  "academia.edu",
  "scribd.com",
  "slideshare.net",
  "github.com",
  "githubusercontent.com",
  "osf.io",
  "figshare.com",
  "ssrn.com",
)

OFFTOPIC_TERMS = (
  "mouse", "mice", "murine", "zebrafish", "drosophila", "arabidopsis",
  "carcinoma", "chemotherapy", "in vitro", "canine", "feline", "bovine",
  "porcine", "equine", "new species of", "phylogeny of", "taxonomy of",
  "taxonomic revision", "butterfly", "butterflies", "beetle", "beetles",
  "lepidoptera", "coleoptera", "hymenoptera", "amphibian", "lizard",
  "snake", "bird species", "avian", "fish species", "coral reef", "shark",
  "echolocation", "orchid", "cactus", "fern ", "fungus", "fungi", "mycorrhiz",
  "soil bacteria", "microbiome", "clinical trial", "randomized controlled",
  "alzheimer", "parkinson", "breast cancer", "prostate cancer", "leukemia",
  "schizophrenia", "pesticide", "wastewater", "photovoltaic", "solar cell",
  "concrete", "asphalt", "polymer", "nanoparticle", "catalysis", "quantum",
  "superconductor", "seismology", "earthquake rupture", "volcanic ash petrology",
  "tectonic subduction", "heavy metal toxicity", "rat model", "wistar",
  "sars-cov-2", "covid-19 vaccine", "monkeypox", "zika virus mosquito",
  "dengue mosquito", "aedes aegypti", "malaria vector anopheles",
  "mangrove carbon", "seagrass", "phytoplankton", "zooplankton",
  "benthic", "foraminifera", "ostracod", "trilobite", "ammonite", "dinosaur",
  "cretaceous", "jurassic", "miocene", "pliocene", "eocene", "oligocene",
)

# Per-chapter tailored queries & positive relevance keywords
CHAPTER_CONFIG = {
  "precolumbian_mesoamerica": {
    "openalex": [
      "Teotihuacan population urbanism demography archaeology",
      "Monte Alban Zapotec Oaxaca Valley settlement population",
      "Olmec San Lorenzo La Venta Gulf Coast Mesoamerica settlement",
      "Basin of Mexico Formative Classic archaeology population",
      "Toltec Tula Cholula Cantona Mesoamerica urban population",
      "Mesoamerica paleodemography prehispanic population archaeology",
    ],
    "doaj": [
      "Teotihuacan poblacion arqueologia",
      "Oaxaca Monte Alban zapoteca arqueologia",
      "Olmeca Mesoamerica asentamiento poblacion",
      "Mesoamerica clasico preclasico demografia",
    ],
    "epmc": [
      "Teotihuacan archaeology population Mesoamerica",
      "Oaxaca Zapotec Olmec Mesoamerica archaeology settlement",
    ],
    "plos": [
      "Teotihuacan Mesoamerica population archaeology",
      "Oaxaca Olmec Formative Classic Mesoamerica settlement",
    ],
    "hal": [
      "Teotihuacan Mesoamerique archeologie population",
      "Olmec Zapotec Mexique prehispanique peuplement",
    ],
    "cepal": [],
    "pos_geo": (
      "teotihuacan", "olmec", "olmeca", "zapotec", "zapoteca", "monte alban",
      "toltec", "tolteca", "tula", "cholula", "cantona", "mesoamerica",
      "mesoamerican", "basin of mexico", "oaxaca", "veracruz", "tabasco",
      "gulf coast", "san lorenzo", "la venta", "tres zapotes", "cuicuilco",
      "xochicalco", "el tajin", "tehuacan", "tlaxcala", "puebla", "mexico",
      "prehispanic", "pre-hispanic", "precolumbian", "pre-columbian", "formative",
    ),
    "pos_topic": (
      "population", "poblacion", "demograph", "demograf", "urban", "settlement",
      "asentamiento", "city", "ciudad", "household", "archaeolog", "arqueolog",
      "paleodemograph", "state", "chiefdom", "monument", "survey", "density",
      "densidad", "subsistence", "agriculture", "obsidian", "radiocarbon",
      "chronology", "isotop", "migration", "burial", "skeleton", "bioarchaeolog",
    ),
  },
  "classic_postclassic_maya": {
    "openalex": [
      "Classic Maya population LiDAR settlement Peten Tikal",
      "Maya collapse demographic decline paleodemography",
      "Copan Palenque Calakmul Caracol Maya population settlement",
      "Postclassic Maya Yucatan Mayapan Chichen Itza demography",
      "Belize Maya lowlands settlement archaeology population",
      "Guatemala highlands El Salvador Maya archaeology settlement",
    ],
    "doaj": [
      "Maya poblacion asentamiento arqueologia",
      "Cultura Maya demografia Yucatan Peten",
      "Classic Maya settlement archaeology",
      "Mayapan Chichen Itza Tikal Copan",
    ],
    "epmc": [
      "Classic Maya population settlement LiDAR",
      "Maya paleodemography collapse archaeology",
    ],
    "plos": [
      "Classic Maya population settlement LiDAR",
      "Maya lowlands Yucatan Belize Guatemala archaeology",
    ],
    "hal": [
      "Maya peuplement archeologie Peten Yucatan",
      "Classic Maya Guatemala Mexique archeologie",
    ],
    "cepal": [],
    "pos_geo": (
      "maya", "mayan", "peten", "tikal", "calakmul", "copan", "palenque",
      "caracol", "mayapan", "chichen itza", "yucatan", "belize", "guatemala",
      "chiapas", "campeche", "quintana roo", "uxmal", "piedras negras",
      "ceibal", "seibal", "el mirador", "quirigua", "joya de ceren",
      "tazumal", "kaminaljuyu", "lowlands", "usumacinta", "mopan",
    ),
    "pos_topic": (
      "population", "poblacion", "demograph", "demograf", "settlement",
      "asentamiento", "lidar", "urban", "collapse", "colapso", "household",
      "archaeolog", "arqueolog", "density", "densidad", "agriculture",
      "maize", "drought", "polity", "kingdom", "city", "ciudad", "bioarchaeolog",
      "paleodemograph", "radiocarbon", "classic", "postclassic", "preclassic",
    ),
  },
  "aztec_late_postclassic_mexico": {
    "openalex": [
      "Aztec Tenochtitlan Basin of Mexico population urbanism",
      "Late Postclassic Central Mexico Aztec settlement demography",
      "Tarascan Purepecha Tzintzuntzan Michoacan archaeology population",
      "Mixtec Oaxaca Postclassic settlement archaeology demography",
      "Aztec empire tribute population chinampa agriculture",
      "Morelos Tlaxcala Teotihuacan Valley Aztec demography",
    ],
    "doaj": [
      "Azteca Mexica Tenochtitlan poblacion",
      "Postclasico Mesoamerica demografia asentamiento",
      "Tarasco Purepecha Michoacan arqueologia",
      "Mixteca Oaxaca posclasico arqueologia",
    ],
    "epmc": [
      "Aztec Tenochtitlan Basin of Mexico population",
      "Postclassic Mexico Purepecha Mixtec archaeology",
    ],
    "plos": [
      "Aztec Basin of Mexico urbanism population",
      "Postclassic Mexico Tarascan Mixtec archaeology",
    ],
    "hal": [
      "Azteque Tenochtitlan Mexique postclassique",
      "Tarasque Michoacan Mexique prehispanique",
    ],
    "cepal": [],
    "pos_geo": (
      "aztec", "azteca", "mexica", "tenochtitlan", "texcoco", "tlaxcala",
      "basin of mexico", "cuenca de mexico", "tarascan", "tarasco", "purepecha",
      "tzintzuntzan", "michoacan", "mixtec", "mixteca", "postclassic",
      "posclasico", "morelos", "chalco", "xochimilco", "tlatelolco",
      "huastec", "totonac", "nahua", "nahuatl", "central mexico", "jalisco",
      "colima", "nayarit", "sinaloa", "paquime", "casas grandes",
    ),
    "pos_topic": (
      "population", "poblacion", "demograph", "demograf", "urban", "city",
      "ciudad", "settlement", "asentamiento", "empire", "imperio", "tribute",
      "tributo", "chinampa", "agriculture", "household", "market", "mercado",
      "archaeolog", "arqueolog", "codex", "codice", "state", "polity",
      "altepetl", "calpulli", "density", "densidad", "bioarchaeolog",
    ),
  },
  "precolumbian_lower_central_america": {
    "openalex": [
      "Precolumbian Panama Gran Cocle Darien archaeology settlement",
      "Precolumbian Costa Rica Guanacaste Diquis archaeology settlement",
      "Prehispanic Nicaragua Gran Nicoya archaeology settlement",
      "Honduras Ulua Valley Naco Lenca precolumbian archaeology",
      "Lower Central America Isthmo-Colombian archaeology population",
      "Chiefdoms Panama Costa Rica archaeology demography",
    ],
    "doaj": [
      "arqueologia Costa Rica precolombina",
      "arqueologia Panama precolombino",
      "arqueologia Nicaragua Honduras prehispanica",
      "Isthmo-Colombian Lower Central America archaeology",
    ],
    "epmc": [
      "Panama Costa Rica pre-Columbian archaeology population",
      "Lower Central America ancient DNA archaeology settlement",
    ],
    "plos": [
      "Panama Costa Rica pre-Columbian archaeology",
      "Honduras Nicaragua pre-Columbian archaeology settlement",
    ],
    "hal": [
      "archeologie Costa Rica Panama precolombien",
      "Nicaragua Honduras prehispanique archeologie",
    ],
    "cepal": [],
    "pos_geo": (
      "panama", "costa rica", "nicaragua", "honduras", "lower central america",
      "isthmo-colombian", "gran cocle", "cocle", "darien", "chiriqui",
      "veraguas", "guanacaste", "nicoya", "diquis", "guayabo", "ulua",
      "naco", "mosquitia", "lenca", "chibcha", "chibchan", "isthmus",
      "centroamerica", "central america", "el salvador", "sitio conte",
      "el cano", "cerro juan diaz", "ometepe", "managua",
    ),
    "pos_topic": (
      "archaeolog", "arqueolog", "precolumbian", "pre-columbian", "prehispanic",
      "pre-hispanic", "prehistoric", "settlement", "asentamiento", "chiefdom",
      "cacicazgo", "population", "poblacion", "demograph", "ceramic", "ceramica",
      "burial", "gold", "metallurgy", "agriculture", "maize", "radiocarbon",
      "ancient", "indigenous", "indigena", "site", "sitio", "landscape",
    ),
  },
  "precolumbian_caribbean_islands": {
    "openalex": [
      "Precolumbian Caribbean Taino population archaeology",
      "Saladoid Archaic Ceramic Age Caribbean settlement demography",
      "Ancient DNA Caribbean pre-Columbian population size",
      "Lucayan Bahamas Ciboney Cuba precolumbian archaeology",
      "Hispaniola Puerto Rico Jamaica Taino archaeology chiefdom",
      "Lesser Antilles Kalinago Carib precolumbian archaeology settlement",
    ],
    "doaj": [
      "Taino arqueologia Caribe precolombino",
      "Cuba Puerto Rico Dominicana arqueologia indigena",
      "Caribbean archaeology Saladoid Ceramic Age",
      "Antilles precolumbian archaeology settlement",
    ],
    "epmc": [
      "pre-Columbian Caribbean ancient DNA population Taino",
      "Caribbean archaeology Saladoid Ceramic Age settlement",
    ],
    "plos": [
      "Caribbean pre-Columbian archaeology Taino population",
      "Antilles Puerto Rico Cuba Hispaniola archaeology",
    ],
    "hal": [
      "Antilles precolombien archeologie Caraibes",
      "Martinique Guadeloupe Saladoid archeologie",
    ],
    "cepal": [],
    "pos_geo": (
      "caribbean", "caribe", "antilles", "antillas", "taino", "taíno",
      "arawak", "saladoid", "ostionoid", "ciboney", "guanahatabey", "lucayan",
      "kalinago", "carib", "hispaniola", "puerto rico", "cuba", "jamaica",
      "bahamas", "dominican republic", "haiti", "trinidad", "barbados",
      "guadeloupe", "martinique", "grenada", "st lucia", "antigua", "barbuda",
      "st kitts", "nevis", "dominica", "st vincent", "virgin islands", "aruba",
      "curacao", "bonaire", "saba", "montserrat", "anguilla",
    ),
    "pos_topic": (
      "precolumbian", "pre-columbian", "prehispanic", "prehistoric", "archaeolog",
      "arqueolog", "population", "poblacion", "demograph", "settlement",
      "asentamiento", "ancient dna", "paleogenom", "genetic", "migration",
      "colonization", "ceramic", "archaic", "radiocarbon", "chiefdom",
      "cacique", "cacicazgo", "isotop", "diet", "shell", "midden", "island",
    ),
  },
  "conquest_collapse_mesoamerica": {
    "openalex": [
      "Cocoliztli 1545 1576 Mexico epidemic mortality demography",
      "Spanish conquest Mesoamerica indigenous demographic collapse",
      "Colonial Mexico sixteenth century epidemics smallpox population",
      "Congregaciones reducciones New Spain indigenous population",
      "Relaciones Geograficas New Spain colonial demography",
      "Guatemala Central America sixteenth century conquest depopulation",
    ],
    "doaj": [
      "cocoliztli epidemia Mexico siglo XVI",
      "colapso demografico conquista Mesoamerica",
      "congregaciones indigenas Nueva Espana siglo XVI",
      "Relaciones Geograficas poblacion indigena Mexico",
    ],
    "epmc": [
      "cocoliztli 1545 1576 Mexico epidemic Salmonella",
      "Spanish conquest Mexico epidemic mortality indigenous population",
    ],
    "plos": [
      "cocoliztli Mexico epidemic colonial mortality",
      "Spanish conquest Mesoamerica indigenous population decline",
    ],
    "hal": [
      "conquete Mexique epidemie demographie XVIe",
      "Nouvelle-Espagne population indigene XVIe siecle",
    ],
    "cepal": [],
    "pos_geo": (
      "mexico", "new spain", "nueva espana", "mesoamerica", "guatemala",
      "central america", "centroamerica", "yucatan", "oaxaca", "michoacan",
      "tlaxcala", "chiapas", "tenochtitlan", "teposcolula", "nahua", "maya",
      "aztec", "spanish america", "americas", "honduras", "nicaragua",
      "el salvador", "veracruz", "hidalgo", "puebla", "jalisco",
    ),
    "pos_topic": (
      "cocoliztli", "epidemic", "epidem", "smallpox", "viruela", "measles",
      "salmonella", "collapse", "colapso", "conquest", "conquista",
      "depopulation", "despoblacion", "mortality", "mortalidad", "congregacion",
      "reduccion", "relaciones geograficas", "encomienda", "tribute", "tributo",
      "demographic", "demograf", "population", "poblacion", "sixteenth century",
      "siglo xvi", "1519", "1520", "1545", "1576", "colonial", "indigenous",
    ),
  },
  "viceroyalty_of_new_spain": {
    "openalex": [
      "New Spain colonial Mexico historical demography parish registers",
      "Nueva Espana poblacion demografia historica siglo XVIII",
      "Revillagigedo census 1790 New Spain Mexico population",
      "Colonial Mexico silver mining Bajio Zacatecas Guanajuato population",
      "Mexico City colonial population 17th 18th century demography",
      "Yucatan Oaxaca Guadalajara colonial Mexico historical demography",
    ],
    "doaj": [
      "Nueva Espana demografia historica poblacion",
      "registros parroquiales Nueva Espana siglo XVIII",
      "poblacion colonial Mexico censo 1790",
      "ciudad de Mexico colonial poblacion mortalidad",
    ],
    "epmc": [
      "New Spain colonial Mexico mortality epidemic 18th century",
      "colonial Mexico historical demography parish population",
    ],
    "plos": [
      "colonial Mexico New Spain population demography",
      "New Spain 18th century mortality epidemic Mexico",
    ],
    "hal": [
      "Nouvelle-Espagne Mexique colonial demographie XVIIIe",
      "Mexique XVIIe XVIIIe siecle population paroisse",
    ],
    "cepal": [],
    "pos_geo": (
      "new spain", "nueva espana", "mexico", "mexican", "bajio", "zacatecas",
      "guanajuato", "guadalajara", "puebla", "oaxaca", "yucatan", "veracruz",
      "michoacan", "san luis potosi", "durango", "sonora", "chihuahua",
      "tlaxcala", "queretaro", "jalisco", "nuevo leon", "campeche", "merida",
      "valladolid", "antequera", "acapulco", "coahuila", "sinaloa",
    ),
    "pos_topic": (
      "colonial", "viceroyalty", "virreinato", "revillagigedo", "padron",
      "parish", "parroquial", "baptism", "bautismo", "burial", "defuncion",
      "marriage", "matrimonio", "census", "censo", "demograph", "demograf",
      "population", "poblacion", "mortality", "mortalidad", "epidemic",
      "matlazahuatl", "casta", "mestizo", "indigena", "silver", "mining",
      "mineria", "hacienda", "siglo xvii", "siglo xviii", "18th century",
      "17th century", "1790", "1793", "bourbon", "borbon", "intendencia",
    ),
  },
  "captaincy_general_guatemala": {
    "openalex": [
      "Captaincy General Guatemala colonial Central America population",
      "Reino de Guatemala demografia historica poblacion colonial",
      "Colonial Costa Rica Nicaragua Honduras El Salvador population",
      "Colonial Panama Darien Portobelo historical population demography",
      "British Honduras Belize colonial settlement population history",
      "Chiapas Guatemala colonial parish tribute historical demography",
    ],
    "doaj": [
      "Reino de Guatemala poblacion colonial demografia",
      "Costa Rica colonial poblacion demografia historica",
      "Centroamerica colonial poblacion tributo",
      "Panama Belice colonial poblacion historia",
    ],
    "epmc": [
      "colonial Guatemala Central America population mortality",
      "colonial Costa Rica Panama historical demography",
    ],
    "plos": [
      "colonial Guatemala Central America population history",
      "Central America colonial demography indigenous",
    ],
    "hal": [
      "Guatemala colonial Amerique centrale population",
      "Costa Rica Nicaragua Panama colonial demographie",
    ],
    "cepal": [],
    "pos_geo": (
      "guatemala", "central america", "centroamerica", "costa rica",
      "nicaragua", "honduras", "el salvador", "panama", "belize", "belice",
      "british honduras", "chiapas", "soconusco", "verapaz", "antigua",
      "cartago", "leon", "granada", "comayagua", "tegucigalpa", "sonsonate",
      "san salvador", "portobelo", "darien", "mosquitia", "reino de guatemala",
      "audiencia de guatemala", "capitania general",
    ),
    "pos_topic": (
      "colonial", "demograph", "demograf", "population", "poblacion", "tribute",
      "tributo", "parish", "parroquial", "padron", "census", "censo",
      "encomienda", "repartimiento", "epidemic", "mortalidad", "mortality",
      "indigenous", "indigena", "ladino", "mestizo", "mulato", "slavery",
      "esclavitud", "siglo xvi", "siglo xvii", "siglo xviii", "16th century",
      "17th century", "18th century", "audiencia", "capitania", "provincia",
    ),
  },
  "conquest_indigenous_caribbean": {
    "openalex": [
      "Hispaniola Taino demographic collapse 1492 Columbus population",
      "Indigenous Caribbean conquest depopulation sixteenth century",
      "Encomienda Hispaniola Cuba Puerto Rico Jamaica indigenous population",
      "Taino survival indigenous ancestry Caribbean colonial conquest",
      "Early colonial Cuba Puerto Rico Jamaica population 1500 1650",
      "Lesser Antilles Kalinago Carib early colonial contact population",
    ],
    "doaj": [
      "Taino conquista Caribe poblacion siglo XVI",
      "Espanola Cuba Puerto Rico poblacion indigena colonial",
      "encomienda Antillas Caribe siglo XVI",
      "Kalinago Caribes Antillas colonizacion",
    ],
    "epmc": [
      "Taino indigenous ancestry Caribbean conquest survival",
      "Hispaniola Caribbean 1492 epidemic depopulation",
    ],
    "plos": [
      "Taino Caribbean indigenous ancestry conquest population",
      "Hispaniola Puerto Rico Cuba indigenous colonial",
    ],
    "hal": [
      "Antilles Caraibes Kalinago colonisation XVIe XVIIe",
      "Hispaniola Cuba conquete indigenes demographie",
    ],
    "cepal": [],
    "pos_geo": (
      "hispaniola", "espanola", "santo domingo", "cuba", "puerto rico",
      "boriken", "jamaica", "bahamas", "lucayan", "caribbean", "caribe",
      "antilles", "antillas", "taino", "taíno", "kalinago", "carib",
      "dominica", "st vincent", "guadeloupe", "martinique", "trinidad",
      "barbados", "margarita", "cubagua", "west indies",
    ),
    "pos_topic": (
      "conquest", "conquista", "columbus", "colon", "1492", "collapse",
      "colapso", "depopulation", "despoblacion", "extinction", "extincion",
      "survival", "supervivencia", "encomienda", "repartimiento", "epidemic",
      "smallpox", "viruela", "population", "poblacion", "demograph", "demograf",
      "indigenous", "indigena", "ancestry", "admixture", "sixteenth century",
      "siglo xvi", "early colonial", "slavery", "esclavitud", "gold",
    ),
  },
  "colonial_caribbean_plantation": {
    "openalex": [
      "Caribbean slave trade plantation demography mortality fertility",
      "Saint-Domingue Haiti colonial population slavery revolution",
      "Jamaica Barbados British West Indies slave demography plantation",
      "Cuba Puerto Rico slavery colonial census 18th 19th century",
      "Martinique Guadeloupe French Antilles slavery colonial population",
      "Danish West Indies Dutch Caribbean Curacao colonial slavery demography",
    ],
    "doaj": [
      "esclavitud Caribe Cuba Puerto Rico poblacion siglo XVIII XIX",
      "Saint-Domingue Haiti esclavage population coloniale",
      "plantation slavery Caribbean Jamaica Barbados demography",
      "Antilles esclavage demographie XVIIIe XIXe",
    ],
    "epmc": [
      "Caribbean plantation slavery mortality demography Jamaica Barbados",
      "transatlantic slave trade Caribbean historical demography",
    ],
    "plos": [
      "Caribbean slavery plantation Jamaica Barbados Cuba",
      "transatlantic slave trade Caribbean population genetics history",
    ],
    "hal": [
      "Saint-Domingue esclavage population XVIIIe",
      "Martinique Guadeloupe Antilles esclavage demographie",
    ],
    "cepal": [],
    "pos_geo": (
      "caribbean", "caribe", "west indies", "antilles", "saint-domingue",
      "saint domingue", "haiti", "jamaica", "barbados", "cuba", "puerto rico",
      "martinique", "guadeloupe", "trinidad", "tobago", "grenada", "st lucia",
      "antigua", "st kitts", "nevis", "montserrat", "dominica", "st vincent",
      "curacao", "suriname", "danish west indies", "st croix", "virgin islands",
      "bahamas", "bermuda", "santo domingo", "leeward", "windward",
    ),
    "pos_topic": (
      "slave", "slavery", "esclav", "plantation", "plantacion", "sugar",
      "azucar", "sucre", "colonial", "emancipation", "abolition", "abolici",
      "mortality", "mortalidad", "mortalite", "fertility", "fecundidad",
      "demograph", "demograf", "population", "poblacion", "census", "censo",
      "recensement", "revolution", "atlantic", "middle passage", "marron",
      "maroon", "freed", "manumission", "18th century", "19th century",
      "siglo xviii", "siglo xix", "17th century",
    ),
  },
  "mexico_after_independence": {
    "openalex": [
      "Mexico population census demographic transition 19th 20th century",
      "Mexican Revolution 1910 1920 demographic impact mortality population",
      "Mexico urbanization metropolitan population growth 20th century",
      "Mexico fertility decline mortality demographic transition INEGI",
      "Mexico City population growth urbanization census demography",
      "Mexico internal migration emigration demographic history",
    ],
    "doaj": [
      "transicion demografica Mexico poblacion censo",
      "urbanizacion crecimiento poblacional Mexico siglo XX",
      "fecundidad mortalidad Mexico demografia INEGI",
      "Revolucion Mexicana poblacion demografia siglo XIX XX",
    ],
    "epmc": [
      "Mexico demographic transition mortality fertility census",
      "Mexico population aging urbanization mortality",
    ],
    "plos": [
      "Mexico population demographic transition urbanization",
      "Mexico fertility mortality migration census",
    ],
    "hal": [
      "Mexique transition demographique population urbanisation",
      "Mexique recensement fecondite mortalite XXe",
    ],
    "cepal": [
      "Mexico poblacion censo transicion demografica",
      "Mexico urbanizacion migracion fecundidad mortalidad",
    ],
    "pos_geo": (
      "mexico", "mexican", "mexicano", "mexicana", "ciudad de mexico",
      "mexico city", "inegi", "conapo", "jalisco", "monterrey", "guadalajara",
      "veracruz", "chiapas", "oaxaca", "yucatan", "sonora", "chihuahua",
      "tijuana", "puebla", "guanajuato", "michoacan", "nuevo leon",
    ),
    "pos_topic": (
      "population", "poblacion", "census", "censo", "demograph", "demograf",
      "fertility", "fecundidad", "mortality", "mortalidad", "life expectancy",
      "esperanza de vida", "urbanization", "urbanizacion", "metropolitan",
      "migration", "migracion", "transition", "transicion", "aging",
      "envejecimiento", "revolution", "revolucion", "1895", "1910", "1930",
      "1950", "1970", "1990", "2000", "2010", "2020", "household", "hogar",
    ),
  },
  "central_american_republics": {
    "openalex": [
      "Central America demographic transition population census Guatemala El Salvador",
      "Costa Rica historical demography mortality fertility longevity census",
      "Panama population census urbanization Canal Zone demography",
      "Honduras Nicaragua population census demographic transition",
      "Belize population census demographic growth migration",
      "Guatemala El Salvador indigenous demography fertility migration",
    ],
    "doaj": [
      "Centroamerica transicion demografica poblacion censo",
      "Costa Rica demografia mortalidad fecundidad censo",
      "Guatemala El Salvador Honduras Nicaragua poblacion censo",
      "Panama Belice poblacion demografia urbanizacion",
    ],
    "epmc": [
      "Costa Rica Guatemala Central America demographic transition mortality",
      "El Salvador Honduras Nicaragua Panama population fertility",
    ],
    "plos": [
      "Central America Guatemala Costa Rica Panama population demography",
      "El Salvador Honduras Nicaragua Belize demographic",
    ],
    "hal": [
      "Amerique centrale Costa Rica Guatemala demographie population",
      "Panama Nicaragua Salvador population recensement",
    ],
    "cepal": [
      "Centroamerica poblacion censo demografia",
      "Guatemala El Salvador Honduras Nicaragua Costa Rica Panama poblacion",
    ],
    "pos_geo": (
      "central america", "centroamerica", "guatemala", "el salvador",
      "honduras", "nicaragua", "costa rica", "panama", "belize", "belice",
      "canal zone", "san jose", "managua", "tegucigalpa", "san salvador",
      "guatemala city", "istmo centroamericano",
    ),
    "pos_topic": (
      "population", "poblacion", "census", "censo", "demograph", "demograf",
      "fertility", "fecundidad", "mortality", "mortalidad", "longevity",
      "life expectancy", "esperanza de vida", "urbanization", "urbanizacion",
      "migration", "migracion", "transition", "transicion", "aging",
      "envejecimiento", "growth", "crecimiento", "republic", "modern",
      "19th century", "20th century", "siglo xix", "siglo xx",
    ),
  },
  "greater_antilles_modern": {
    "openalex": [
      "Cuba demographic transition aging fertility population census",
      "Puerto Rico population census migration fertility decline",
      "Jamaica post-emancipation population census demographic transition",
      "Haiti population census fertility mortality demographic transition",
      "Dominican Republic population census fertility urbanization migration",
      "Greater Antilles Caribbean demographic transition mortality fertility",
    ],
    "doaj": [
      "Cuba poblacion censo transicion demografica envejecimiento",
      "Republica Dominicana Haiti poblacion censo demografia",
      "Puerto Rico poblacion censo migracion fecundidad",
      "Jamaica Cuba Caribbean population census demography",
    ],
    "epmc": [
      "Cuba Puerto Rico Jamaica demographic transition mortality fertility",
      "Haiti Dominican Republic population fertility mortality",
    ],
    "plos": [
      "Puerto Rico Cuba Jamaica Haiti Dominican Republic population demography",
      "Greater Antilles Caribbean fertility mortality migration",
    ],
    "hal": [
      "Haiti Cuba Republique dominicaine demographie population",
      "Grandes Antilles Jamaique Porto Rico population",
    ],
    "cepal": [
      "Cuba Republica Dominicana Haiti poblacion censo demografia",
      "Jamaica Caribe poblacion transicion demografica",
    ],
    "pos_geo": (
      "cuba", "cuban", "cubano", "haiti", "haitian", "haitiano",
      "dominican republic", "republica dominicana", "dominican", "jamaica",
      "jamaican", "puerto rico", "puerto rican", "puertorriquen",
      "greater antilles", "grandes antillas", "hispaniola", "havana",
      "habana", "kingston", "san juan", "port-au-prince", "santo domingo",
    ),
    "pos_topic": (
      "population", "poblacion", "census", "censo", "demograph", "demograf",
      "fertility", "fecundidad", "mortality", "mortalidad", "aging",
      "envejecimiento", "life expectancy", "migration", "migracion",
      "emigration", "urbanization", "urbanizacion", "transition", "transicion",
      "emancipation", "growth", "decline", "household", "hogar", "birth",
    ),
  },
  "lesser_antilles_bahamas_bermuda": {
    "openalex": [
      "Trinidad and Tobago population census demographic transition",
      "Barbados population census fertility mortality demographic history",
      "Bahamas Bermuda population census demographic history migration",
      "Martinique Guadeloupe demographic transition population census",
      "Eastern Caribbean Lesser Antilles Saint Lucia Grenada Dominica population census",
      "US Virgin Islands Curacao Aruba Caribbean population census demography",
    ],
    "doaj": [
      "Trinidad Tobago Barbados population demography",
      "Caribbean small island states population census migration",
      "Martinique Guadeloupe population demographie",
      "Bahamas Bermuda Lesser Antilles population demography",
    ],
    "epmc": [
      "Barbados Trinidad Tobago Bahamas Bermuda population mortality fertility",
      "Eastern Caribbean Lesser Antilles demographic transition",
    ],
    "plos": [
      "Trinidad Tobago Barbados Bahamas Caribbean population demography",
      "Martinique Guadeloupe Eastern Caribbean population",
    ],
    "hal": [
      "Martinique Guadeloupe demographie population recensement",
      "Petites Antilles Caraibes population transition demographique",
    ],
    "cepal": [
      "Caribbean population census aging fertility Trinidad Barbados",
      "Caribe anglofono poblacion censo demografia",
    ],
    "pos_geo": (
      "trinidad", "tobago", "barbados", "bahamas", "bermuda", "martinique",
      "guadeloupe", "saint lucia", "st lucia", "grenada", "dominica",
      "st vincent", "saint vincent", "antigua", "barbuda", "st kitts",
      "saint kitts", "nevis", "montserrat", "anguilla", "virgin islands",
      "cayman", "turks and caicos", "aruba", "curacao", "bonaire",
      "st maarten", "sint maarten", "lesser antilles", "eastern caribbean",
      "west indies", "caribbean", "caribe", "oecs", "caricom",
    ),
    "pos_topic": (
      "population", "poblacion", "census", "censo", "recensement",
      "demograph", "demograf", "fertility", "fecundidad", "fecondite",
      "mortality", "mortalidad", "mortalite", "aging", "vieillissement",
      "migration", "emigration", "immigration", "indentured", "emancipation",
      "urbanization", "transition", "growth", "island", "household",
    ),
  },
}

# Curated authoritative official US Census Bureau PDFs (Puerto Rico, USVI, Panama Canal Zone)
CURATED_DIRECT_PDFS = {
  "central_american_republics": [
    {
      "title": "1950 Census of Population: Volume II, Part 54, Territories and Possessions (Alaska, Hawaii, Puerto Rico, Canal Zone, Virgin Islands)",
      "authors": ["United States Bureau of the Census"],
      "year": 1953,
      "journal_or_publisher": "U.S. Department of Commerce, Bureau of the Census",
      "publisher_domain": "census.gov",
      "doi": "",
      "url": "https://www2.census.gov/library/publications/decennial/1950/population-volume-2/37781529v2p54ch1.pdf",
      "pdf_url": "https://www2.census.gov/library/publications/decennial/1950/population-volume-2/37781529v2p54ch1.pdf",
    },
    {
      "title": "1970 Census of Population: Number of Inhabitants, Canal Zone (PC(1)-A57)",
      "authors": ["United States Bureau of the Census"],
      "year": 1971,
      "journal_or_publisher": "U.S. Department of Commerce, Bureau of the Census",
      "publisher_domain": "census.gov",
      "doi": "",
      "url": "https://www2.census.gov/library/publications/decennial/1970/population-volume-1/1970a_cz-01.pdf",
      "pdf_url": "https://www2.census.gov/library/publications/decennial/1970/population-volume-1/1970a_cz-01.pdf",
    },
  ],
  "greater_antilles_modern": [
    {
      "title": "2010 Census of Population and Housing: Puerto Rico Summary Population and Housing Characteristics (CPH-1-53)",
      "authors": ["United States Census Bureau"],
      "year": 2012,
      "journal_or_publisher": "U.S. Department of Commerce, Economics and Statistics Administration",
      "publisher_domain": "census.gov",
      "doi": "",
      "url": "https://www2.census.gov/library/publications/2012/dec/cph-1-53.pdf",
      "pdf_url": "https://www2.census.gov/library/publications/2012/dec/cph-1-53.pdf",
    },
    {
      "title": "1940 Census of Population: Puerto Rico Bulletin No. 1, Number of Inhabitants",
      "authors": ["United States Bureau of the Census"],
      "year": 1942,
      "journal_or_publisher": "U.S. Department of Commerce, Bureau of the Census",
      "publisher_domain": "census.gov",
      "doi": "",
      "url": "https://www2.census.gov/library/publications/decennial/1940/population-puerto-rico-b1/41727531ch1.pdf",
      "pdf_url": "https://www2.census.gov/library/publications/decennial/1940/population-puerto-rico-b1/41727531ch1.pdf",
    },
  ],
  "lesser_antilles_bahamas_bermuda": [
    {
      "title": "2010 Census of Population and Housing: U.S. Virgin Islands Demographic Profile Summary",
      "authors": ["United States Census Bureau"],
      "year": 2013,
      "journal_or_publisher": "U.S. Department of Commerce, Economics and Statistics Administration",
      "publisher_domain": "census.gov",
      "doi": "",
      "url": "https://www2.census.gov/library/publications/2013/dec/cph-2-55.pdf",
      "pdf_url": "https://www2.census.gov/library/publications/2013/dec/cph-2-55.pdf",
    },
    {
      "title": "1970 Census of Population: Number of Inhabitants, Virgin Islands of the United States (PC(1)-A55)",
      "authors": ["United States Bureau of the Census"],
      "year": 1971,
      "journal_or_publisher": "U.S. Department of Commerce, Bureau of the Census",
      "publisher_domain": "census.gov",
      "doi": "",
      "url": "https://www2.census.gov/library/publications/decennial/1970/population-volume-1/1970a_vi-01.pdf",
      "pdf_url": "https://www2.census.gov/library/publications/decennial/1970/population-volume-1/1970a_vi-01.pdf",
    },
  ],
}


def load_itinerary():
  txt = open(ITIN_PATH, encoding="utf-8").read()
  txt = re.sub(r"//.*", "", txt)
  txt = re.sub(r"(\{|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', txt)
  return json.loads(txt)


def clean_text(s):
  return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", str(s or ""))).strip()


def ascii_slug(s):
  norm = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")
  return re.sub(r"[^a-z0-9]+", "_", norm.lower()).strip("_")


def norm_domain(url):
  host = urllib.parse.urlparse(str(url or "")).netloc.lower()
  if host.startswith("www."):
    host = host[4:]
  if ":" in host:
    host = host.split(":")[0]
  # Collapse obvious subdomains to canonical publisher domain where appropriate
  parts = host.split(".")
  if len(parts) >= 3:
    if host.endswith(".scielo.org") or host.endswith(".scielo.br") or host.endswith(".scielo.org.mx"):
      return host
    if parts[-2] in ("co", "com", "org", "edu", "gob", "gov", "ac") and len(parts[-1]) == 2:
      return ".".join(parts[-3:])
    if parts[0] in ("www2", "api", "cdn", "static", "files", "download", "downloads", "pdf", "media"):
      return ".".join(parts[1:])
  return host or "unknown"


def is_banned(title, authors, url):
  tl = clean_text(title).lower()
  aj = " ".join(str(a) for a in (authors or [])).lower()
  ul = str(url or "").lower()
  if any(b in aj for b in BANNED_AUTHORS):
    return True
  if any(b in tl for b in BANNED_TITLE_PHRASES):
    return True
  if any(h in ul for h in BANNED_HOSTS):
    return True
  if any(t in tl for t in OFFTOPIC_TERMS):
    return True
  return False


def relevance_score(stem, title, journal=""):
  cfg = CHAPTER_CONFIG[stem]
  tl = unicodedata.normalize("NFKD", f"{title} {journal}").encode("ascii", "ignore").decode("ascii").lower()
  geo_hits = sum(1 for g in cfg["pos_geo"] if g in tl)
  top_hits = sum(1 for t in cfg["pos_topic"] if t in tl)
  if geo_hits == 0:
    return 0
  if top_hits == 0:
    return 0
  return geo_hits * 3 + top_hits * 2


def search_openalex(q, per_page=25):
  url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
    "search": q,
    "filter": "open_access.is_oa:true,type:article|book|book-chapter|report|preprint",
    "per-page": str(per_page),
    "sort": "relevance_score:desc",
  })
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=20)
    if r.status_code != 200:
      return out
    results = r.json().get("results") or []
    for w in results:
      title = clean_text(w.get("display_name") or w.get("title"))
      yr = w.get("publication_year")
      if not (title and yr and 1800 <= int(yr) <= 2026):
        continue
      auths = []
      for au in (w.get("authorships") or [])[:6]:
        nm = clean_text((au.get("author") or {}).get("display_name"))
        if nm:
          auths.append(nm)
      if not auths:
        continue
      doi_raw = str(w.get("doi") or "").strip()
      doi = doi_raw.replace("https://doi.org/", "").replace("http://doi.org/", "")
      # Gather candidate PDF URLs from best_oa_location and locations
      pdf_urls = []
      landing_urls = []
      best = w.get("best_oa_location") or {}
      if best.get("pdf_url"):
        pdf_urls.append(best["pdf_url"])
      if best.get("landing_page_url"):
        landing_urls.append(best["landing_page_url"])
      for loc in (w.get("locations") or []):
        pu = loc.get("pdf_url")
        lu = loc.get("landing_page_url")
        if pu and pu not in pdf_urls:
          pdf_urls.append(pu)
        if lu and lu not in landing_urls:
          landing_urls.append(lu)
      # Filter out banned hosts from pdf_urls
      pdf_urls = [u for u in pdf_urls if u.startswith("http") and not any(bh in u.lower() for bh in BANNED_HOSTS)]
      landing_urls = [u for u in landing_urls if u.startswith("http") and not any(bh in u.lower() for bh in BANNED_HOSTS)]
      if not pdf_urls and not landing_urls:
        continue
      primary_pdf = pdf_urls[0] if pdf_urls else landing_urls[0]
      src = (w.get("primary_location") or {}).get("source") or (best.get("source") or {})
      journal = clean_text(src.get("display_name") or "") or norm_domain(primary_pdf)
      dom = norm_domain(primary_pdf)
      if is_banned(title, auths, primary_pdf):
        continue
      out.append({
        "title": title,
        "authors": auths,
        "year": int(yr),
        "journal_or_publisher": journal,
        "publisher_domain": dom,
        "doi": doi,
        "url": f"https://doi.org/{doi}" if doi else (landing_urls[0] if landing_urls else primary_pdf),
        "pdf_url": primary_pdf,
        "alt_pdf_urls": pdf_urls[1:3] + landing_urls[:1],
        "cited_by": int(w.get("cited_by_count") or 0),
        "source_api": "openalex",
      })
  except Exception:
    pass
  return out


def search_doaj(q, page_size=25):
  url = "https://doaj.org/api/search/articles/" + urllib.parse.quote(q) + f"?pageSize={page_size}"
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=20)
    if r.status_code != 200:
      return out
    for item in (r.json().get("results") or []):
      bj = item.get("bibjson") or {}
      title = clean_text(bj.get("title"))
      yr = str(bj.get("year") or "")
      auths = [clean_text(a.get("name")) for a in (bj.get("author") or []) if a.get("name")][:6]
      if not (title and auths and yr.isdigit()):
        continue
      doi = ""
      for ident in (bj.get("identifier") or []):
        if ident.get("type") == "doi" and ident.get("id"):
          doi = ident["id"].strip()
          break
      links = [l.get("url") for l in (bj.get("link") or []) if l.get("url") and l.get("url").startswith("http")]
      links = [u for u in links if not any(bh in u.lower() for bh in BANNED_HOSTS)]
      if not links:
        continue
      ft_url = links[0]
      if is_banned(title, auths, ft_url):
        continue
      dom = norm_domain(ft_url)
      journal = clean_text((bj.get("journal") or {}).get("title") or dom)
      pdf_url = ft_url
      if "demographic-research.org/volumes/vol" in ft_url:
        m = re.search(r"vol(\d+)/(\d+)", ft_url)
        if m:
          pdf_url = f"https://www.demographic-research.org/volumes/vol{m.group(1)}/{m.group(2)}/{m.group(1)}-{m.group(2)}.pdf"
      elif "plos.org" in dom and doi:
        pdf_url = f"https://journals.plos.org/plosone/article/file?id={urllib.parse.quote(doi)}&type=printable"
      out.append({
        "title": title,
        "authors": auths,
        "year": int(yr),
        "journal_or_publisher": journal,
        "publisher_domain": dom,
        "doi": doi,
        "url": f"https://doi.org/{doi}" if doi else ft_url,
        "pdf_url": pdf_url,
        "alt_pdf_urls": links[1:2],
        "cited_by": 5,
        "source_api": "doaj",
      })
  except Exception:
    pass
  return out


def search_epmc(q, page_size=15):
  url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode({
    "query": f"({q}) AND OPEN_ACCESS:y AND HAS_PDF:y",
    "format": "json",
    "pageSize": str(page_size),
    "sort_cited": "y",
  })
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=20)
    if r.status_code != 200:
      return out
    for d in ((r.json().get("resultList") or {}).get("result") or []):
      pmcid = d.get("pmcid") or ""
      if not pmcid.startswith("PMC"):
        continue
      title = clean_text(d.get("title"))
      yr = str(d.get("pubYear") or "")
      auth_str = clean_text(d.get("authorString"))
      auths = [a.strip().rstrip(".") for a in auth_str.split(",") if len(a.strip()) > 2][:6]
      if not (title and auths and yr.isdigit()):
        continue
      doi = clean_text(d.get("doi") or "")
      journal = clean_text(d.get("journalTitle") or "Europe PMC")
      pdf_url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"
      if is_banned(title, auths, pdf_url):
        continue
      out.append({
        "title": title,
        "authors": auths,
        "year": int(yr),
        "journal_or_publisher": journal,
        "publisher_domain": "europepmc.org",
        "doi": doi,
        "url": f"https://doi.org/{doi}" if doi else f"https://europepmc.org/article/PMC/{pmcid}",
        "pdf_url": pdf_url,
        "alt_pdf_urls": [],
        "cited_by": int(d.get("citedByCount") or 0),
        "source_api": "europepmc",
      })
  except Exception:
    pass
  return out


def search_plos(q, rows=10):
  url = "https://api.plos.org/search?" + urllib.parse.urlencode({
    "q": q,
    "fl": "id,title_display,journal,publication_date,author_display",
    "rows": str(rows),
    "wt": "json",
  })
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=20)
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
      slug_j = "plosone"
      jl = journal.lower()
      if "genetics" in jl:
        slug_j = "plosgenetics"
      elif "pathogens" in jl:
        slug_j = "plospathogens"
      elif "biology" in jl:
        slug_j = "plosbiology"
      elif "neglected" in jl:
        slug_j = "plosntds"
      pdf_url = f"https://journals.plos.org/{slug_j}/article/file?id={urllib.parse.quote(doi)}&type=printable"
      if is_banned(title, auths, pdf_url):
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


def search_hal(q, rows=12):
  url = "https://api.archives-ouvertes.fr/search/?" + urllib.parse.urlencode({
    "q": q,
    "fq": "submitType_s:file",
    "fl": "docid,title_s,authFullName_s,producedDateY_i,doiId_s,uri_s,fileMain_s,journalTitle_s",
    "rows": str(rows),
    "wt": "json",
  })
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=20)
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
      if is_banned(title, auths, pdf_url):
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
        "cited_by": 6,
        "source_api": "hal",
      })
  except Exception:
    pass
  return out


def search_cepal(q, size=10):
  url = "https://repositorio.cepal.org/server/api/discover/search/objects?" + urllib.parse.urlencode({
    "query": q,
    "size": str(size),
  })
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=20)
    if r.status_code != 200:
      return out
    objs = ((r.json().get("_embedded") or {}).get("searchResult") or {}).get("_embedded", {}).get("objects") or []
    for o in objs:
      it = (o.get("_embedded") or {}).get("indexableObject") or {}
      md = it.get("metadata") or {}
      titles = md.get("dc.title") or []
      title = clean_text(titles[0].get("value")) if titles else ""
      dates = md.get("dc.date.issued") or []
      yr_m = re.search(r"(\d{4})", str(dates[0].get("value")) if dates else "")
      if not (title and yr_m):
        continue
      yr = int(yr_m.group(1))
      auth_entries = md.get("dc.contributor.author") or md.get("dc.creator") or []
      auths = [clean_text(a.get("value")) for a in auth_entries if a.get("value")][:6]
      if not auths:
        auths = ["CEPAL / CELADE"]
      handle = ""
      for u_ent in (md.get("dc.identifier.uri") or []):
        if u_ent.get("value"):
          handle = u_ent["value"]
          break
      bl = (it.get("_links") or {}).get("bundles", {}).get("href")
      if not bl:
        continue
      # Resolve ORIGINAL PDF bitstream lazily via a marker URL
      if is_banned(title, auths, handle or bl):
        continue
      out.append({
        "title": title,
        "authors": auths,
        "year": yr,
        "journal_or_publisher": "UN ECLAC / CEPAL-CELADE",
        "publisher_domain": "repositorio.cepal.org",
        "doi": "",
        "url": handle or f"https://repositorio.cepal.org/entities/publication/{it.get('uuid')}",
        "pdf_url": bl,
        "alt_pdf_urls": [],
        "cited_by": 15,
        "source_api": "cepal",
        "is_cepal_bundles": True,
      })
  except Exception:
    pass
  return out


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


def fetch_url_bytes(url, timeout=22):
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
  """Resolves candidate to a verified PDF byte payload and pymupdf page count."""
  # Handle CEPAL DSpace bundles resolution
  if cand.get("is_cepal_bundles"):
    try:
      b = requests.get(cand["pdf_url"], headers=API_HEADERS, timeout=15).json()
      pdf_link = None
      for bnd in (b.get("_embedded") or {}).get("bundles") or []:
        if bnd.get("name") == "ORIGINAL":
          bs = requests.get(bnd["_links"]["bitstreams"]["href"], headers=API_HEADERS, timeout=15).json()
          for bit in (bs.get("_embedded") or {}).get("bitstreams") or []:
            nm = str(bit.get("name") or "").lower()
            if nm.endswith(".pdf"):
              pdf_link = bit["_links"]["content"]["href"]
              break
      if not pdf_link:
        return None
      data, _, final_u = fetch_url_bytes(pdf_link, timeout=25)
      pages = validate_pdf_bytes(data)
      if pages:
        c2 = dict(cand)
        c2["pdf_url"] = final_u
        c2.pop("is_cepal_bundles", None)
        return (c2, data, pages, final_u)
    except Exception:
      return None
    return None

  urls_to_try = [cand["pdf_url"]] + list(cand.get("alt_pdf_urls") or [])
  for u in urls_to_try:
    if not u or any(bh in u.lower() for bh in BANNED_HOSTS):
      continue
    data, ct, final_u = fetch_url_bytes(u, timeout=22)
    if not data:
      continue
    if any(bh in final_u.lower() for bh in BANNED_HOSTS):
      continue
    pages = validate_pdf_bytes(data)
    if pages:
      c2 = dict(cand)
      d_final = norm_domain(final_u)
      if d_final and not any(bh in d_final for bh in BANNED_HOSTS):
        c2["publisher_domain"] = d_final
      return (c2, data, pages, final_u)

    # If HTML landing page, extract citation_pdf_url or OJS/SciELO/OpenEdition PDF link
    if b"<html" in data[:2048].lower() or "html" in ct:
      html = data.decode("utf-8", errors="ignore")
      found = []
      for pat in (
        r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']',
        r'href=["\']([^"\']+/article/download/\d+/\d+(?:/\d+)?)["\']',
        r'href=["\']([^"\']+/pdf/[^"\']+\.pdf(?:\?[^"\']*)?)["\']',
        r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']',
      ):
        for m in re.finditer(pat, html, re.I):
          nu = urllib.parse.urljoin(final_u, m.group(1))
          if nu not in found and not any(bh in nu.lower() for bh in BANNED_HOSTS):
            found.append(nu)
      for pdf2 in found[:2]:
        d2, _, fu2 = fetch_url_bytes(pdf2, timeout=22)
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


def make_clean_filename(authors, year, title, pdir, h6):
  first_a = authors[0] if authors else "author"
  # Handle "Last, First" vs "First Last"
  if "," in first_a:
    surname = first_a.split(",")[0].strip()
  else:
    parts = first_a.strip().split()
    surname = parts[-1] if parts else "author"
  a_slug = ascii_slug(surname)[:16] or "author"
  # Drop stop words from short title for informative compact filename
  stop = {"the", "of", "and", "in", "to", "a", "an", "for", "on", "de", "la", "el", "en", "los", "las", "del", "y", "le", "les", "des", "du"}
  words = [w for w in ascii_slug(title).split("_") if w and w not in stop]
  t_slug = "_".join(words)[:34].strip("_") or "study"

  rel_dir = os.path.relpath(pdir, SVEA_ROOT).replace("\\", "/")
  max_fn = min(MAX_FILENAME_LEN, MAX_RELPATH_LEN - len(rel_dir) - 1)
  base = f"{a_slug}_{year}_{t_slug}"
  fn = f"{base[:max_fn - 4]}.pdf"
  if os.path.exists(os.path.join(pdir, fn)):
    fn = f"{base[:max_fn - 11]}_{h6}.pdf"
  return fn


def harvest_chapter(ch, global_hashes):
  stem = ch["stem"]
  rel_ch = os.path.join(ch["group"], ch["folder"])
  pdir = os.path.join(JAGUAR_DIR, rel_ch, "papers")
  os.makedirs(pdir, exist_ok=True)
  meta_p = os.path.join(pdir, "papers_metadata.json")
  existing = json.load(open(meta_p, encoding="utf-8")) if os.path.isfile(meta_p) else []

  # Verify existing entries still exist and are valid
  valid_existing = []
  dom_used = {}
  seen_titles = set()
  seen_urls = set()
  for rec in existing:
    fp = os.path.join(pdir, rec.get("filename", ""))
    if os.path.isfile(fp) and os.path.getsize(fp) >= MIN_BYTES:
      valid_existing.append(rec)
      d = rec.get("publisher_domain") or "unknown"
      dom_used[d] = dom_used.get(d, 0) + 1
      seen_titles.add(ascii_slug(rec.get("title", ""))[:60])
      seen_urls.add(rec.get("url", ""))
      if rec.get("sha256"):
        global_hashes.add(rec["sha256"])

  if len(valid_existing) >= TARGET_PER_CHAPTER and len(dom_used) >= 6:
    print(f"[SKIP] [CH {ch['index']:02d}] {stem:38s}: {len(valid_existing):2d} PDFs | {len(dom_used)} domains", flush=True)
    return valid_existing

  cfg = CHAPTER_CONFIG[stem]
  pool = []
  seen_cand_keys = set(seen_titles)

  def add_cand(c, forced_score=None):
    tk = ascii_slug(c.get("title", ""))[:60]
    if not tk or tk in seen_cand_keys or c.get("url") in seen_urls:
      return
    sc = forced_score if forced_score is not None else relevance_score(stem, c.get("title", ""), c.get("journal_or_publisher", ""))
    if sc <= 0:
      return
    seen_cand_keys.add(tk)
    c2 = dict(c)
    c2["_score"] = sc
    pool.append(c2)

  # 0. Curated authoritative US Census PDFs if defined for this chapter
  for c in CURATED_DIRECT_PDFS.get(stem, []):
    add_cand(c, forced_score=50)

  # 1. OpenAlex (broadest scholarly & Latin American OA publisher diversity)
  for q in cfg["openalex"]:
    for c in search_openalex(q, per_page=20):
      add_cand(c)

  # 2. DOAJ (OJS journals: COLMEX, UNAM, UCR, SciELO, Caribbean, Spanish/French)
  for q in cfg["doaj"]:
    for c in search_doaj(q, page_size=20):
      add_cand(c)

  # 3. EuropePMC
  for q in cfg["epmc"]:
    for c in search_epmc(q, page_size=12):
      add_cand(c)

  # 4. PLOS
  for q in cfg["plos"]:
    for c in search_plos(q, rows=8):
      add_cand(c)

  # 5. HAL
  for q in cfg["hal"]:
    for c in search_hal(q, rows=10):
      add_cand(c)

  # 6. CEPAL / CELADE (for modern census chapters)
  for q in cfg["cepal"]:
    for c in search_cepal(q, size=10):
      add_cand(c, forced_score=max(12, relevance_score(stem, c.get("title", ""), c.get("journal_or_publisher", ""))))

  # Sort within each publisher_domain by (relevance_score, cited_by), then round-robin across domains!
  by_dom = {}
  for c in pool:
    by_dom.setdefault(c["publisher_domain"], []).append(c)
  for dom in by_dom:
    by_dom[dom].sort(key=lambda x: (-x["_score"], -x.get("cited_by", 0), -x.get("year", 0)))

  # Prioritise domains we haven't used yet, and interleave round-robin
  dom_order = sorted(by_dom.keys(), key=lambda d: (dom_used.get(d, 0), -by_dom[d][0]["_score"]))
  ordered = []
  max_len = max((len(v) for v in by_dom.values()), default=0)
  for idx in range(min(max_len, 8)):
    for dom in dom_order:
      if idx < len(by_dom[dom]):
        ordered.append(by_dom[dom][idx])

  need = max(0, TARGET_PER_CHAPTER - len(valid_existing))
  added = 0
  # Try candidates in chunks of 16 using <= 4 polite workers
  chunk_size = 16
  pos = 0
  jurisdiction = ", ".join(ch.get("jurisdictions") or [])

  while added < need and pos < len(ordered) and pos < 160:
    batch = []
    while len(batch) < chunk_size and pos < len(ordered):
      c = ordered[pos]
      pos += 1
      # Enforce strict domain diversity cap (max 3 per domain while building >= 7 domains, max 4 absolute)
      d_cap = 3 if len(dom_used) < 7 else 4
      if dom_used.get(c["publisher_domain"], 0) >= d_cap:
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
        d_cap = 3 if len(dom_used) < 7 else 4
        if dom_used.get(dom, 0) >= d_cap:
          continue
        h = hashlib.sha256(data).hexdigest()
        if h in global_hashes:
          continue
        global_hashes.add(h)
        fn = make_clean_filename(cand["authors"], cand["year"], cand["title"], pdir, h[:6])
        fp = os.path.join(pdir, fn)
        with open(fp, "wb") as fh:
          fh.write(data)
        rel_path = os.path.relpath(fp, SVEA_ROOT).replace("\\", "/")
        rec = {
          "chapter_index": ch["index"],
          "chapter_stem": stem,
          "chapter_folder": rel_ch.replace("\\", "/"),
          "filename": fn,
          "rel_path": rel_path,
          "sha256": h,
          "bytes": len(data),
          "pages": pages,
          "title": cand["title"],
          "authors": cand["authors"],
          "year": cand["year"],
          "journal_or_publisher": cand["journal_or_publisher"],
          "publisher_domain": dom,
          "doi": cand.get("doi", ""),
          "url": cand.get("url", final_u),
          "pdf_url": final_u,
          "jurisdiction": jurisdiction,
          "source_api": cand.get("source_api", "direct"),
        }
        valid_existing.append(rec)
        dom_used[dom] = dom_used.get(dom, 0) + 1
        added += 1

  with open(meta_p, "w", encoding="utf-8") as fh:
    json.dump(valid_existing, fh, indent=2, ensure_ascii=False)

  print(
    f"  [CH {ch['index']:02d}] {stem:38s}: {len(valid_existing):2d} PDFs (+{added:2d}) | "
    f"{len(dom_used):2d} domains {list(dom_used.keys())[:5]}",
    flush=True,
  )
  return valid_existing


def main():
  itin = load_itinerary()
  global_hashes = set()

  # Pre-scan existing verified PDFs so hashes stay globally unique on re-run
  for ch in itin["chapters"]:
    pdir = os.path.join(JAGUAR_DIR, ch["group"], ch["folder"], "papers")
    os.makedirs(pdir, exist_ok=True)
    for fn in os.listdir(pdir):
      if fn.lower().endswith(".pdf"):
        fp = os.path.join(pdir, fn)
        data = open(fp, "rb").read()
        if len(data) >= MIN_BYTES and data.startswith(b"%PDF-"):
          global_hashes.add(hashlib.sha256(data).hexdigest())

  all_papers = []
  summary = {}
  t0 = time.time()
  print("[START] Harvesting Project JAGUAR Wave 2 Archival PDFs across 14 chapters...", flush=True)

  for ch in itin["chapters"]:
    recs = harvest_chapter(ch, global_hashes)
    all_papers.extend(recs)
    doms = sorted({r["publisher_domain"] for r in recs})
    summary[ch["stem"]] = {
      "chapter_index": ch["index"],
      "chapter_folder": f"{ch['group']}/{ch['folder']}",
      "pdf_count": len(recs),
      "distinct_domains": len(doms),
      "domains": doms,
      "total_bytes": sum(r["bytes"] for r in recs),
      "total_pages": sum(r["pages"] for r in recs),
    }

  manifest = {
    "project": "JAGUAR",
    "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "total_chapters": len(itin["chapters"]),
    "total_papers": len(all_papers),
    "min_chapter_pdfs": min((s["pdf_count"] for s in summary.values()), default=0),
    "min_chapter_domains": min((s["distinct_domains"] for s in summary.values()), default=0),
    "chapters_summary": summary,
    "papers": all_papers,
  }
  with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2, ensure_ascii=False)

  elapsed = time.time() - t0
  print(
    f"\n[DONE] {len(all_papers)} unique verified PDFs across 14 chapters in {elapsed:.1f}s "
    f"(min_pdfs={manifest['min_chapter_pdfs']}, min_domains={manifest['min_chapter_domains']})",
    flush=True,
  )


if __name__ == "__main__":
  main()
