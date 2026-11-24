"""Stage C Wave 2 Part 2: Cleanup + High-Precision Top-Up Harvester for Project JAGUAR.

1. Removes any audited off-topic stray PDFs from Pass 1.
2. Tops up every single one of the 14 JAGUAR chapters to >= 17 (target 18)
   SHA-256-unique, pymupdf-verified %PDF- (> 12 kB, filename <= 68 chars,
   repo-relative path <= 176 chars) with >= 6 distinct scholarly publisher
   domains per chapter, 0% Zenodo, 0% crowd sources, and zero prohibited
   global compilations.
3. Rebuilds `JAGUAR/_shared/wave2_papers_manifest.json` and runs a full
   Gatekeeper D3 integrity & diversity audit.
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
MAG_DEMRES_CACHE = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC",
  "_shared", "demres_catalog_v2.json"
)
ITIN_PATH = os.path.join(JAGUAR_DIR, "jaguar_itinerary.json5")
MANIFEST_PATH = os.path.join(JAGUAR_DIR, "_shared", "wave2_papers_manifest.json")

HEADERS = {
  "User-Agent": (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36 "
    "(OperationViscount-JAGUAR-Harvester/2.0; mailto:research@confoederatio.org)"
  ),
  "Accept": "application/pdf,text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}
API_HEADERS = {
  "User-Agent": "OperationViscount-JAGUAR-Harvester/2.0 (mailto:research@confoederatio.org)"
}

TARGET_PER_CHAPTER = 18
MIN_BYTES = 12288
MAX_BYTES = 28 * 1024 * 1024
MAX_WORKERS = 4
MAX_FILENAME_LEN = 68
MAX_RELPATH_LEN = 176

# Exact Pass-1 off-topic strays to prune before top-up
STRAY_PRUNE = {
  "conquest_collapse_mesoamerica": {
    "garrod_1975_development_school_geography_canad.pdf",
    "olko_2019_language_attitudes_educational_opp.pdf",
  },
  "captaincy_general_guatemala": {
    "ceron_2021_mortalidad_por_diabetes_guatemala.pdf",
  },
  "conquest_indigenous_caribbean": {
    "maccarthy_2007_cuban_zarzuela_neo_colonial_imagin.pdf",
  },
  "mexico_after_independence": {
    "alvarez_maldonad_2024_dinamica_demografica_desigualdad_e.pdf",
  },
  "central_american_republics": {
    "barragan_barrera_2017_high_genetic_structure_low_mitocho.pdf",
    "cordero_2014_comercio_bienes_servicios_centroam.pdf",
    "cordero_2013_comercio_bienes_servicios_centroam.pdf",
  },
  "lesser_antilles_bahamas_bermuda": {
    "perez_2017_how_collaborative_integrated_taxon.pdf",
    "yntema_2018_records_observations_breeding_wate.pdf",
    "celade_2015_informe_ejecucion_programa_bienal.pdf",
    "celade_2016_actualizacion_informe_ejecucion_pr.pdf",
    "celade_2013_informe_actividades_realizadas_por.pdf",
  },
}

BANNED_AUTHORS = (
  "mcevedy", "colin mcevedy", "richard jones", "klein goldewijk", "goldewijk",
  "maddison", "angus maddison", "tertius chandler", "chandler, tertius",
  "modelski", "george modelski", "populstat",
)
BANNED_TITLE_PHRASES = (
  "hyde 3", "hyde 2", "populstat", "maddison project",
  "atlas of world population history", "four thousand years of urban growth",
  "world cities: -3000 to 2000", "informe de ejecucion", "programa bienal",
  "comercio de bienes", "grupos de trabajo", "waterbird", "dolphin", "spongiol",
)
BANNED_HOSTS = (
  "zenodo.org", "wikidata.org", "wikipedia.org", "wikimedia.org",
  "openstreetmap.org", "geonames.org", "researchgate.net", "academia.edu",
  "scribd.com", "slideshare.net", "github.com", "githubusercontent.com",
  "osf.io", "figshare.com", "ssrn.com", "birdscaribbean.org",
)
OFFTOPIC_TERMS = (
  "mouse", "mice", "murine", "zebrafish", "drosophila", "arabidopsis",
  "carcinoma", "chemotherapy", "in vitro", "canine", "feline", "bovine",
  "porcine", "equine", "new species of", "phylogeny of", "taxonomy of",
  "taxonomic", "butterfly", "butterflies", "beetle", "beetles", "dolphin",
  "whale", "sea turtle", "manatee", "waterbird", "bird ", "birds ", "avian",
  "fish ", "coral", "shark", "sponge", "spongiol", "orchid", "cactus",
  "fungus", "fungi", "bacteria", "microbiome", "clinical trial",
  "randomized controlled", "alzheimer", "parkinson", "breast cancer",
  "prostate cancer", "leukemia", "schizophrenia", "pesticide", "wastewater",
  "photovoltaic", "solar cell", "concrete", "asphalt", "polymer",
  "nanoparticle", "catalysis", "quantum", "superconductor", "seismology",
  "sars-cov-2", "covid-19 vaccine", "monkeypox", "zika", "dengue",
  "aedes aegypti", "malaria vector", "mangrove", "seagrass", "phytoplankton",
  "zooplankton", "benthic", "foraminifera", "dinosaur", "cretaceous",
  "jurassic", "miocene", "pliocene", "zarzuela", "music theater",
  "school geography", "diabetes en guatemala 2018", "comercio de bienes",
  "programa bienal", "grupos de trabajo", "bolivia", "peru", "chile",
  "argentina", "colombia", "venezuela", "ecuador", "brazil", "brasil",
)

# High-precision expanded queries for every chapter needing top-up (or polish)
EXTRA_QUERIES = {
  "precolumbian_mesoamerica": {
    "openalex": [
      "Teotihuacan demography urban population Mexico",
      "Monte Alban Oaxaca Formative Classic settlement population",
      "Olmec Gulf Coast San Lorenzo La Venta archaeology",
      "Cholula Tula Cantona Highland Mexico archaeology",
    ],
    "doaj": ["Teotihuacan arqueologia", "Monte Alban Oaxaca arqueologia"],
    "epmc": ["Teotihuacan population archaeology", "Oaxaca Formative archaeology"],
    "hal": ["Teotihuacan archeologie", "Mesoamerique prehispanique"],
    "cepal": [],
    "pos_geo": ("teotihuacan", "olmec", "olmeca", "zapotec", "monte alban", "toltec", "tula", "cholula", "cantona", "mesoamerica", "oaxaca", "veracruz", "tabasco", "basin of mexico", "prehispanic", "formative"),
    "pos_topic": ("population", "poblacion", "demograph", "urban", "settlement", "asentamiento", "archaeolog", "arqueolog", "household", "city", "ciudad", "state", "density", "agriculture", "burial", "isotop"),
  },
  "classic_postclassic_maya": {
    "openalex": [
      "Classic Maya demography population estimate Tikal Peten",
      "Postclassic Maya Mayapan Chichen Itza archaeology",
      "Maya Lowlands LiDAR settlement density archaeology",
    ],
    "doaj": ["Estudios de Cultura Maya", "Mayapan Tikal Copan arqueologia"],
    "epmc": ["Classic Maya population LiDAR", "Maya collapse demography"],
    "hal": ["Maya Peten Yucatan archeologie"],
    "cepal": [],
    "pos_geo": ("maya", "mayan", "peten", "tikal", "calakmul", "copan", "palenque", "caracol", "mayapan", "chichen itza", "yucatan", "belize", "guatemala", "chiapas"),
    "pos_topic": ("population", "poblacion", "demograph", "settlement", "lidar", "urban", "collapse", "household", "archaeolog", "arqueolog", "density", "agriculture", "drought", "city"),
  },
  "aztec_late_postclassic_mexico": {
    "openalex": [
      "Aztec urbanism Tenochtitlan Basin of Mexico archaeology",
      "Aztec household archaeology Morelos Basin of Mexico",
      "Tenochtitlan population Mexica empire archaeology history",
      "Tarascan Purepecha Michoacan Tzintzuntzan archaeology",
      "Mixtec Postclassic Oaxaca settlement archaeology",
      "Late Postclassic Central Mexico Aztec chinampa agriculture",
      "Tlaxcala Texcoco Chalco Xochimilco Aztec archaeology",
      "Nahua Postclassic Central Mexico codex tribute demography",
      "Aztec society economy population Michael Smith",
      "Western Mexico Postclassic Jalisco Colima Michoacan archaeology",
    ],
    "doaj": [
      "Estudios de Cultura Nahuatl",
      "Tenochtitlan Mexica arqueologia",
      "Azteca cuenca de Mexico",
      "Purepecha Michoacan arqueologia",
      "Mixteca posclasico Oaxaca",
      "Tlaxcala Texcoco posclasico",
    ],
    "epmc": [
      "Aztec Tenochtitlan archaeology Mexico",
      "Central Mexico Postclassic bioarchaeology",
      "Mesoamerica Aztec population genetics",
    ],
    "plos": [
      "Aztec Mexico archaeology",
      "Tenochtitlan Basin of Mexico",
      "Purepecha Mixtec Mexico archaeology",
    ],
    "hal": [
      "Azteque Tenochtitlan Mexique",
      "Mexica Nahuatl Mexique prehispanique",
      "Michoacan Tarasque Purepecha",
    ],
    "cepal": [],
    "pos_geo": ("aztec", "azteca", "mexica", "tenochtitlan", "texcoco", "tlaxcala", "basin of mexico", "cuenca de mexico", "tarascan", "tarasco", "purepecha", "tzintzuntzan", "angamuco", "michoacan", "mixtec", "mixteca", "postclassic", "posclasico", "morelos", "chalco", "xochimilco", "tlatelolco", "nahua", "nahuatl", "central mexico", "huastec", "totonac", "west mexico", "paquime"),
    "pos_topic": ("population", "poblacion", "demograph", "urban", "city", "ciudad", "settlement", "asentamiento", "empire", "imperio", "tribute", "tributo", "chinampa", "agriculture", "household", "market", "mercado", "archaeolog", "arqueolog", "codex", "codice", "state", "polity", "altepetl", "ceramic", "obsidian", "architecture", "pyramids", "burial", "skeleton", "bioarchaeolog", "genetic", "history", "historia", "economy", "econom"),
  },
  "conquest_collapse_mesoamerica": {
    "openalex": [
      "Cocoliztli 1545 1576 epidemic Mexico Salmonella",
      "Indigenous depopulation sixteenth century Mexico New Spain",
      "Smallpox epidemic Spanish conquest Mexico Mesoamerica 1520",
      "Congregaciones reducciones colonial Mexico sixteenth century",
      "Relaciones Geograficas sixteenth century New Spain Mexico",
      "Sixteenth century Maya demographic collapse Guatemala Yucatan",
      "Encomienda tribute indigenous population sixteenth century Mexico",
    ],
    "doaj": [
      "epidemias siglo XVI Nueva Espana Mexico",
      "poblacion indigena siglo XVI Nueva Espana",
      "conquista Mexico demografia catastrofe",
      "congregaciones pueblos indios Nueva Espana",
    ],
    "epmc": [
      "cocoliztli Mexico 1545 1576 Salmonella",
      "epidemic colonial Mexico sixteenth century smallpox",
      "demographic collapse Mesoamerica conquest",
    ],
    "plos": [
      "cocoliztli Mexico epidemic",
      "colonial Mexico indigenous population sixteenth century",
    ],
    "hal": [
      "Nouvelle-Espagne XVIe siecle indiens epidemie",
      "conquete Mexique population XVIe",
    ],
    "cepal": [],
    "pos_geo": ("mexico", "new spain", "nueva espana", "mesoamerica", "guatemala", "central america", "yucatan", "oaxaca", "michoacan", "tlaxcala", "chiapas", "tenochtitlan", "teposcolula", "nahua", "maya", "aztec", "honduras", "nicaragua", "el salvador", "puebla", "veracruz"),
    "pos_topic": ("cocoliztli", "epidemic", "epidem", "smallpox", "viruela", "measles", "salmonella", "collapse", "colapso", "conquest", "conquista", "depopulation", "despoblacion", "mortality", "mortalidad", "congregacion", "reduccion", "relaciones geograficas", "encomienda", "tribute", "tributo", "demograph", "demograf", "population", "poblacion", "sixteenth", "siglo xvi", "1519", "1520", "1545", "1576", "catastrofe", "disease", "enfermedad", "pestilence"),
  },
  "viceroyalty_of_new_spain": {
    "openalex": [
      "Colonial Mexico historical demography parish registers New Spain",
      "New Spain population eighteenth century census Revillagigedo",
      "Colonial Mexico City population mortality eighteenth century",
      "Bajio Guanajuato Zacatecas silver mining colonial Mexico population",
      "Yucatan Oaxaca Guadalajara Puebla colonial Mexico demography",
      "Matlazahuatl epidemic 1737 1779 colonial Mexico New Spain",
      "Bourbon reforms New Spain population census Mexico 1790",
    ],
    "doaj": [
      "demografia historica Nueva Espana",
      "registros parroquiales Mexico siglo XVIII",
      "poblacion Nueva Espana siglo XVII XVIII",
      "epidemias mortalidad Nueva Espana siglo XVIII",
    ],
    "epmc": [
      "New Spain colonial Mexico epidemic 18th century",
      "colonial Mexico mortality parish demography",
    ],
    "plos": [
      "New Spain colonial Mexico demography history",
    ],
    "hal": [
      "Nouvelle-Espagne XVIIIe siecle population",
      "Mexique colonial demographie paroisse",
    ],
    "cepal": [],
    "pos_geo": ("new spain", "nueva espana", "mexico", "mexican", "bajio", "zacatecas", "guanajuato", "guadalajara", "puebla", "oaxaca", "yucatan", "veracruz", "michoacan", "san luis potosi", "durango", "sonora", "chihuahua", "tlaxcala", "queretaro", "jalisco", "nuevo leon", "campeche", "merida", "valladolid"),
    "pos_topic": ("colonial", "viceroyalty", "virreinato", "revillagigedo", "padron", "parish", "parroquial", "baptism", "bautismo", "burial", "defuncion", "marriage", "matrimonio", "census", "censo", "demograph", "demograf", "population", "poblacion", "mortality", "mortalidad", "epidemic", "matlazahuatl", "casta", "mestizo", "indigena", "silver", "mining", "mineria", "hacienda", "siglo xvii", "siglo xviii", "18th century", "17th century", "1790", "bourbon", "borbon", "intendencia"),
  },
  "captaincy_general_guatemala": {
    "openalex": [
      "Colonial Guatemala population demography Maya eighteenth century",
      "Colonial Costa Rica historical demography parish population",
      "Colonial Nicaragua Honduras population indigenous demography",
      "Colonial El Salvador Guatemala tribute encomienda population",
      "Colonial Panama Portobelo Darien population slavery history",
      "Belize British Honduras colonial history settlement population",
      "Reino de Guatemala poblacion tributo siglo XVIII",
      "Chiapas Soconusco colonial Guatemala indigenous population",
    ],
    "doaj": [
      "Reino de Guatemala historia colonial poblacion",
      "Costa Rica colonial historia demografia",
      "Centroamerica colonial historia poblacion",
      "Guatemala colonial siglo XVIII poblacion",
      "Nicaragua Honduras colonial historia",
    ],
    "epmc": [
      "colonial Guatemala Maya population history",
      "colonial Central America indigenous population",
    ],
    "plos": [
      "colonial Guatemala Belize Panama history",
    ],
    "hal": [
      "Guatemala colonial XVIIIe siecle",
      "Amerique centrale coloniale population",
    ],
    "cepal": [],
    "pos_geo": ("guatemala", "central america", "centroamerica", "costa rica", "nicaragua", "honduras", "el salvador", "panama", "belize", "belice", "british honduras", "chiapas", "soconusco", "verapaz", "antigua", "cartago", "leon", "granada", "comayagua", "portobelo", "darien", "mosquitia", "moskitia", "reino de guatemala", "audiencia de guatemala"),
    "pos_topic": ("colonial", "demograph", "demograf", "population", "poblacion", "tribute", "tributo", "parish", "parroquial", "padron", "census", "censo", "encomienda", "repartimiento", "epidemic", "mortalidad", "mortality", "indigenous", "indigena", "ladino", "mestizo", "mulato", "slavery", "esclavitud", "siglo xvi", "siglo xvii", "siglo xviii", "16th century", "17th century", "18th century", "audiencia", "capitania", "history", "historia", "settlement", "migration", "migrar"),
  },
  "conquest_indigenous_caribbean": {
    "openalex": [
      "Taino Hispaniola demographic collapse 1492 conquest",
      "Indigenous Caribbean Spanish conquest depopulation sixteenth century",
      "Taino survival genetic ancestry Puerto Rico Dominican Republic Cuba",
      "Encomienda Hispaniola Cuba Puerto Rico indigenous sixteenth century",
      "Kalinago Carib Lesser Antilles European contact colonial",
      "Early Spanish colonial Hispaniola Cuba Jamaica archaeology",
      "Native Caribbean population size 1492 Columbus",
    ],
    "doaj": [
      "Taino Caribe conquista colonia siglo XVI",
      "indigenas Cuba Puerto Rico Santo Domingo siglo XVI",
      "Kalinago Caribes Antillas historia colonial",
    ],
    "epmc": [
      "Taino ancestry Puerto Rico Caribbean indigenous",
      "Caribbean indigenous genomic survival conquest",
    ],
    "plos": [
      "Taino Puerto Rico Dominican Republic Cuba ancestry",
      "Caribbean indigenous colonial contact archaeology",
    ],
    "hal": [
      "Caraibes Kalinago Antilles XVIe XVIIe siecle",
      "Antilles colonisation indiens XVIe",
    ],
    "cepal": [],
    "pos_geo": ("hispaniola", "espanola", "santo domingo", "cuba", "puerto rico", "jamaica", "bahamas", "lucayan", "caribbean", "caribe", "antilles", "antillas", "taino", "kalinago", "carib", "dominica", "st vincent", "guadeloupe", "martinique", "trinidad", "barbados", "dominican republic", "west indies"),
    "pos_topic": ("conquest", "conquista", "columbus", "colon", "1492", "collapse", "colapso", "depopulation", "despoblacion", "extinction", "extincion", "survival", "supervivencia", "encomienda", "epidemic", "smallpox", "population", "poblacion", "demograph", "demograf", "indigenous", "indigena", "ancestry", "admixture", "sixteenth", "siglo xvi", "early colonial", "contact", "archaeolog", "amerindian"),
  },
  "central_american_republics": {
    "openalex": [
      "Costa Rica demographic transition mortality fertility longevity",
      "Guatemala population census fertility indigenous demography",
      "El Salvador population migration fertility demography",
      "Honduras Nicaragua population demographic transition fertility",
      "Panama population census urbanization fertility mortality",
      "Belize population census demographic growth ethnicity",
      "Central America population growth urbanization demographic transition",
      "Central America historical demography nineteenth twentieth century",
      "Guatemala El Salvador Honduras Nicaragua fertility decline",
      "Panama Canal Zone population demographic history",
    ],
    "doaj": [
      "Poblacion y Salud en Mesoamerica",
      "Costa Rica demografia mortalidad fecundidad",
      "Guatemala El Salvador demografia poblacion",
      "Nicaragua Honduras Panama poblacion censo",
      "Centroamerica transicion demografica migracion",
    ],
    "epmc": [
      "Costa Rica longevity mortality demographic",
      "Guatemala fertility mortality population",
      "El Salvador Honduras Nicaragua Panama mortality fertility",
      "Belize population demographic health",
    ],
    "plos": [
      "Guatemala Costa Rica population mortality fertility",
      "Honduras Nicaragua El Salvador Panama population",
    ],
    "hal": [
      "Costa Rica Guatemala demographie population",
      "Amerique centrale population migration urbanisation",
    ],
    "cepal": [
      "transicion demografica Centroamerica",
      "fecundidad mortalidad Guatemala Honduras Nicaragua El Salvador Costa Rica Panama",
      "proyecciones poblacion Centroamerica CELADE",
    ],
    "pos_geo": ("central america", "centroamerica", "guatemala", "el salvador", "honduras", "nicaragua", "costa rica", "panama", "belize", "belice", "canal zone", "mesoamerica"),
    "pos_topic": ("population", "poblacion", "census", "censo", "demograph", "demograf", "fertility", "fecundidad", "mortality", "mortalidad", "longevity", "life expectancy", "esperanza de vida", "urbanization", "urbanizacion", "migration", "migracion", "emigration", "transition", "transicion", "aging", "ageing", "envejecimiento", "birth", "natalidad", "household", "hogar"),
  },
  "greater_antilles_modern": {
    "openalex": [
      "Cuba population aging fertility decline demographic transition",
      "Puerto Rico population decline migration census fertility",
      "Jamaica population census fertility mortality demographic transition",
      "Haiti population census fertility mortality urbanization",
      "Dominican Republic population census fertility migration urbanization",
      "Cuba mortality life expectancy demographic history",
      "Puerto Rico demographic transition twentieth century census",
      "Jamaica emigration fertility demographic change",
      "Haiti Dominican Republic Hispaniola demographic comparison",
      "Greater Antilles Caribbean population census twentieth century",
    ],
    "doaj": [
      "Novedades en Poblacion Cuba",
      "Cuba poblacion envejecimiento fecundidad demografia",
      "Puerto Rico poblacion censo migracion demografia",
      "Republica Dominicana poblacion fecundidad migracion",
      "Haiti Jamaica population demography fertility",
    ],
    "epmc": [
      "Cuba fertility mortality life expectancy aging",
      "Puerto Rico mortality migration population census",
      "Haiti Dominican Republic fertility mortality demographic",
      "Jamaica mortality fertility demographic transition",
    ],
    "plos": [
      "Puerto Rico population migration mortality",
      "Haiti Dominican Republic population fertility mortality",
      "Cuba Jamaica population mortality fertility",
    ],
    "hal": [
      "Haiti population demographie recensement",
      "Cuba demographie vieillissement fecondite",
    ],
    "cepal": [
      "Cuba poblacion envejecimiento fecundidad CELADE",
      "Republica Dominicana Haiti poblacion demografia CELADE",
      "Jamaica Caribe poblacion envejecimiento fecundidad",
    ],
    "pos_geo": ("cuba", "cuban", "cubano", "haiti", "haitian", "haitiano", "dominican republic", "republica dominicana", "dominican", "jamaica", "jamaican", "puerto rico", "puerto rican", "greater antilles", "hispaniola", "havana", "kingston", "san juan", "port-au-prince"),
    "pos_topic": ("population", "poblacion", "census", "censo", "demograph", "demograf", "fertility", "fecundidad", "mortality", "mortalidad", "aging", "ageing", "envejecimiento", "life expectancy", "esperanza de vida", "migration", "migracion", "emigration", "urbanization", "urbanizacion", "transition", "transicion", "growth", "decline", "household", "birth"),
  },
  "lesser_antilles_bahamas_bermuda": {
    "openalex": [
      "Trinidad and Tobago population fertility mortality demographic transition",
      "Barbados population aging fertility mortality census demography",
      "Bahamas population census migration demographic growth",
      "Bermuda population census demographic history aging",
      "Martinique Guadeloupe demographic aging population census",
      "Eastern Caribbean Saint Lucia Grenada Dominica population demography",
      "Curacao Aruba Bonaire Dutch Caribbean population demography",
      "US Virgin Islands British Virgin Islands Cayman population census",
      "British West Indies post-emancipation indentured Indian migration Trinidad",
      "Caribbean small island states demographic aging migration",
    ],
    "doaj": [
      "Trinidad Tobago Barbados demography population",
      "Caribbean fertility aging migration population",
      "Martinique Guadeloupe demographie population",
      "Bahamas Bermuda Caribbean census population",
    ],
    "epmc": [
      "Barbados Trinidad Tobago mortality aging population",
      "Caribbean population aging fertility mortality",
      "Bahamas Bermuda mortality population demographic",
    ],
    "plos": [
      "Barbados Trinidad Tobago population mortality",
      "Caribbean islands population migration aging",
    ],
    "hal": [
      "Martinique Guadeloupe population vieillissement demographie",
      "Antilles francaises demographie migration recensement",
    ],
    "cepal": [
      "Caribbean ageing fertility population census",
      "Trinidad Barbados Eastern Caribbean population",
    ],
    "pos_geo": ("trinidad", "tobago", "barbados", "bahamas", "bermuda", "martinique", "guadeloupe", "saint lucia", "st lucia", "grenada", "dominica", "st vincent", "saint vincent", "antigua", "barbuda", "st kitts", "nevis", "montserrat", "virgin islands", "cayman", "turks", "aruba", "curacao", "bonaire", "lesser antilles", "eastern caribbean", "west indies", "caribbean", "caribe", "antilles"),
    "pos_topic": ("population", "poblacion", "census", "censo", "recensement", "demograph", "demograf", "fertility", "fecundidad", "fecondite", "mortality", "mortalidad", "mortalite", "aging", "ageing", "vieillissement", "envejecimiento", "migration", "emigration", "immigration", "indentured", "emancipation", "urbanization", "transition", "growth", "decline", "life expectancy"),
  },
}

# Additional official US Census Bureau historical/modern PDFs
EXTRA_US_CENSUS = {
  "central_american_republics": [
    {
      "title": "1960 Census of Population: Volume I, Part 57, Canal Zone",
      "authors": ["United States Bureau of the Census"],
      "year": 1963,
      "journal_or_publisher": "U.S. Department of Commerce, Bureau of the Census",
      "publisher_domain": "census.gov",
      "doi": "",
      "url": "https://www2.census.gov/library/publications/decennial/1960/population-volume-1/vol-01-57-a.pdf",
      "pdf_url": "https://www2.census.gov/library/publications/decennial/1960/population-volume-1/vol-01-57-a.pdf",
    },
    {
      "title": "1940 Census of Population: Panama Canal Zone, Population",
      "authors": ["United States Bureau of the Census"],
      "year": 1941,
      "journal_or_publisher": "U.S. Department of Commerce, Bureau of the Census",
      "publisher_domain": "census.gov",
      "doi": "",
      "url": "https://www2.census.gov/library/publications/decennial/1940/population-canal-zone/41727537ch1.pdf",
      "pdf_url": "https://www2.census.gov/library/publications/decennial/1940/population-canal-zone/41727537ch1.pdf",
    },
  ],
  "greater_antilles_modern": [
    {
      "title": "2000 Census of Population and Housing: Puerto Rico Summary Population and Housing Characteristics (PHC-1-53)",
      "authors": ["United States Census Bureau"],
      "year": 2002,
      "journal_or_publisher": "U.S. Department of Commerce, Economics and Statistics Administration",
      "publisher_domain": "census.gov",
      "doi": "",
      "url": "https://www2.census.gov/library/publications/2002/dec/phc-1-53.pdf",
      "pdf_url": "https://www2.census.gov/library/publications/2002/dec/phc-1-53.pdf",
    },
    {
      "title": "1990 Census of Population and Housing: Summary Population and Housing Characteristics, Puerto Rico (1990 CPH-1-53)",
      "authors": ["United States Bureau of the Census"],
      "year": 1991,
      "journal_or_publisher": "U.S. Department of Commerce, Bureau of the Census",
      "publisher_domain": "census.gov",
      "doi": "",
      "url": "https://www2.census.gov/library/publications/decennial/1990/cph-1/cph-1-53.pdf",
      "pdf_url": "https://www2.census.gov/library/publications/decennial/1990/cph-1/cph-1-53.pdf",
    },
  ],
  "lesser_antilles_bahamas_bermuda": [
    {
      "title": "2000 Census of Population and Housing: U.S. Virgin Islands Population and Housing Profile (PHC-4-VI)",
      "authors": ["United States Census Bureau"],
      "year": 2003,
      "journal_or_publisher": "U.S. Department of Commerce, Economics and Statistics Administration",
      "publisher_domain": "census.gov",
      "doi": "",
      "url": "https://www2.census.gov/library/publications/2003/dec/phc-4-vi.pdf",
      "pdf_url": "https://www2.census.gov/library/publications/2003/dec/phc-4-vi.pdf",
    },
    {
      "title": "1990 Census of Population and Housing: Social and Economic Characteristics, Virgin Islands of the United States (1990 CP-2-55)",
      "authors": ["United States Bureau of the Census"],
      "year": 1992,
      "journal_or_publisher": "U.S. Department of Commerce, Bureau of the Census",
      "publisher_domain": "census.gov",
      "doi": "",
      "url": "https://www2.census.gov/library/publications/decennial/1990/cp-2/cp-2-55.pdf",
      "pdf_url": "https://www2.census.gov/library/publications/decennial/1990/cp-2/cp-2-55.pdf",
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
  tl = unicodedata.normalize("NFKD", clean_text(title)).encode("ascii", "ignore").decode("ascii").lower()
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
  cfg = EXTRA_QUERIES[stem]
  tl = unicodedata.normalize("NFKD", f"{title} {journal}").encode("ascii", "ignore").decode("ascii").lower()
  geo_hits = sum(1 for g in cfg["pos_geo"] if g in tl)
  top_hits = sum(1 for t in cfg["pos_topic"] if t in tl)
  if geo_hits == 0 or top_hits == 0:
    return 0
  return geo_hits * 3 + top_hits * 2


def load_demres_catalog():
  if os.path.isfile(MAG_DEMRES_CACHE):
    items = json.load(open(MAG_DEMRES_CACHE, encoding="utf-8"))
    out = []
    for it in items:
      out.append({
        "title": it["title"],
        "authors": it["authors"],
        "year": it["year"],
        "journal_or_publisher": "Demographic Research",
        "publisher_domain": "demographic-research.org",
        "doi": it.get("doi", ""),
        "url": it.get("url", ""),
        "pdf_url": it.get("pdf_url", ""),
        "alt_pdf_urls": [],
        "cited_by": 20,
        "source_api": "demres",
      })
    return out
  return []


def search_openalex(q, per_page=35):
  url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
    "search": q,
    "filter": "open_access.is_oa:true",
    "per-page": str(per_page),
    "sort": "relevance_score:desc",
  })
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=20)
    if r.status_code != 200:
      return out
    for w in (r.json().get("results") or []):
      title = clean_text(w.get("display_name") or w.get("title"))
      yr = w.get("publication_year")
      if not (title and yr and 1800 <= int(yr) <= 2026):
        continue
      auths = [clean_text((au.get("author") or {}).get("display_name")) for au in (w.get("authorships") or [])[:6]]
      auths = [a for a in auths if a]
      if not auths:
        continue
      doi_raw = str(w.get("doi") or "").strip()
      doi = doi_raw.replace("https://doi.org/", "").replace("http://doi.org/", "")
      pdf_urls, landing_urls = [], []
      best = w.get("best_oa_location") or {}
      if best.get("pdf_url"):
        pdf_urls.append(best["pdf_url"])
      if best.get("landing_page_url"):
        landing_urls.append(best["landing_page_url"])
      for loc in (w.get("locations") or []):
        if loc.get("pdf_url") and loc["pdf_url"] not in pdf_urls:
          pdf_urls.append(loc["pdf_url"])
        if loc.get("landing_page_url") and loc["landing_page_url"] not in landing_urls:
          landing_urls.append(loc["landing_page_url"])
      pdf_urls = [u for u in pdf_urls if u.startswith("http") and not any(bh in u.lower() for bh in BANNED_HOSTS)]
      landing_urls = [u for u in landing_urls if u.startswith("http") and not any(bh in u.lower() for bh in BANNED_HOSTS)]
      if not pdf_urls and not landing_urls:
        continue
      primary_pdf = pdf_urls[0] if pdf_urls else landing_urls[0]
      if is_banned(title, auths, primary_pdf):
        continue
      src = (w.get("primary_location") or {}).get("source") or (best.get("source") or {})
      journal = clean_text(src.get("display_name") or "") or norm_domain(primary_pdf)
      out.append({
        "title": title,
        "authors": auths,
        "year": int(yr),
        "journal_or_publisher": journal,
        "publisher_domain": norm_domain(primary_pdf),
        "doi": doi,
        "url": f"https://doi.org/{doi}" if doi else (landing_urls[0] if landing_urls else primary_pdf),
        "pdf_url": primary_pdf,
        "alt_pdf_urls": pdf_urls[1:4] + landing_urls[:2],
        "cited_by": int(w.get("cited_by_count") or 0),
        "source_api": "openalex",
      })
  except Exception:
    pass
  return out


def search_doaj(q, page_size=30):
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
      if "plos.org" in dom and doi:
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


def search_epmc(q, page_size=20):
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


def search_plos(q, rows=12):
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
      if "genetics" in jl: slug_j = "plosgenetics"
      elif "pathogens" in jl: slug_j = "plospathogens"
      elif "biology" in jl: slug_j = "plosbiology"
      elif "neglected" in jl: slug_j = "plosntds"
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


def search_hal(q, rows=15):
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


def search_cepal(q, size=12):
  url = "https://repositorio.cepal.org/server/api/discover/search/objects?" + urllib.parse.urlencode({
    "query": q, "size": str(size),
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
      auths = [clean_text(a.get("value")) for a in auth_entries if a.get("value")][:6] or ["CEPAL / CELADE"]
      handle = ""
      for u_ent in (md.get("dc.identifier.uri") or []):
        if u_ent.get("value"):
          handle = u_ent["value"]
          break
      bl = (it.get("_links") or {}).get("bundles", {}).get("href")
      if not bl or is_banned(title, auths, handle or bl):
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
  if not data or len(data) < MIN_BYTES or len(data) > MAX_BYTES or not data.startswith(b"%PDF-"):
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


def fetch_url_bytes(url, timeout=18):
  try:
    r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True, stream=True)
    if r.status_code != 200:
      return None, "", url
    ct = (r.headers.get("Content-Type") or "").lower()
    chunks, tot = [], 0
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
  if cand.get("is_cepal_bundles"):
    try:
      b = requests.get(cand["pdf_url"], headers=API_HEADERS, timeout=15).json()
      pdf_link = None
      for bnd in (b.get("_embedded") or {}).get("bundles") or []:
        if bnd.get("name") == "ORIGINAL":
          bs = requests.get(bnd["_links"]["bitstreams"]["href"], headers=API_HEADERS, timeout=15).json()
          for bit in (bs.get("_embedded") or {}).get("bitstreams") or []:
            if str(bit.get("name") or "").lower().endswith(".pdf"):
              pdf_link = bit["_links"]["content"]["href"]
              break
      if not pdf_link:
        return None
      data, _, final_u = fetch_url_bytes(pdf_link, timeout=22)
      pages = validate_pdf_bytes(data)
      if pages:
        c2 = dict(cand)
        c2["pdf_url"] = final_u
        c2.pop("is_cepal_bundles", None)
        return (c2, data, pages, final_u)
    except Exception:
      return None
    return None

  for u in [cand["pdf_url"]] + list(cand.get("alt_pdf_urls") or []):
    if not u or any(bh in u.lower() for bh in BANNED_HOSTS):
      continue
    data, ct, final_u = fetch_url_bytes(u, timeout=18)
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
        r'href=["\']([^"\']+/pdf/[^"\']+\.pdf(?:\?[^"\']*)?)["\']',
        r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']',
      ):
        for m in re.finditer(pat, html, re.I):
          nu = urllib.parse.urljoin(final_u, m.group(1))
          if nu not in found and not any(bh in nu.lower() for bh in BANNED_HOSTS):
            found.append(nu)
      for pdf2 in found[:2]:
        d2, _, fu2 = fetch_url_bytes(pdf2, timeout=18)
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
  surname = first_a.split(",")[0].strip() if "," in first_a else (first_a.strip().split()[-1] if first_a.strip() else "author")
  a_slug = ascii_slug(surname)[:16] or "author"
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


def prune_strays(itin):
  removed = 0
  for ch in itin["chapters"]:
    stem = ch["stem"]
    bad = STRAY_PRUNE.get(stem)
    if not bad:
      continue
    pdir = os.path.join(JAGUAR_DIR, ch["group"], ch["folder"], "papers")
    meta_p = os.path.join(pdir, "papers_metadata.json")
    if not os.path.isfile(meta_p):
      continue
    recs = json.load(open(meta_p, encoding="utf-8"))
    kept = []
    for r in recs:
      if r.get("filename") in bad:
        fp = os.path.join(pdir, r["filename"])
        if os.path.isfile(fp):
          os.remove(fp)
        removed += 1
      else:
        kept.append(r)
    with open(meta_p, "w", encoding="utf-8") as fh:
      json.dump(kept, fh, indent=2, ensure_ascii=False)
  print(f"[PRUNE] Removed {removed} off-topic stray PDFs from Pass 1.", flush=True)


def topup_chapter(ch, global_hashes, demres_all):
  stem = ch["stem"]
  rel_ch = os.path.join(ch["group"], ch["folder"])
  pdir = os.path.join(JAGUAR_DIR, rel_ch, "papers")
  meta_p = os.path.join(pdir, "papers_metadata.json")
  existing = json.load(open(meta_p, encoding="utf-8")) if os.path.isfile(meta_p) else []

  valid_existing, dom_used, seen_titles, seen_urls = [], {}, set(), set()
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
    print(f"[OK]   [CH {ch['index']:02d}] {stem:38s}: {len(valid_existing):2d} PDFs | {len(dom_used):2d} domains", flush=True)
    return valid_existing

  if stem not in EXTRA_QUERIES:
    return valid_existing

  cfg = EXTRA_QUERIES[stem]
  pool = []
  seen_cand_keys = set(seen_titles)

  def add_cand(c, forced_score=None):
    tk = ascii_slug(c.get("title", ""))[:60]
    if not tk or tk in seen_cand_keys or c.get("url") in seen_urls:
      return
    if is_banned(c.get("title", ""), c.get("authors", []), c.get("pdf_url", "")):
      return
    sc = forced_score if forced_score is not None else relevance_score(stem, c.get("title", ""), c.get("journal_or_publisher", ""))
    if sc <= 0:
      return
    seen_cand_keys.add(tk)
    c2 = dict(c)
    c2["_score"] = sc
    pool.append(c2)

  # 0. Extra official US Census Bureau PDFs
  for c in EXTRA_US_CENSUS.get(stem, []):
    add_cand(c, forced_score=50)

  # 1. Demographic Research (MPIDR) local cached catalog — instant!
  for item in demres_all:
    sc = relevance_score(stem, item["title"], "Demographic Research")
    if sc >= 5:
      add_cand(item, forced_score=sc + 6)

  # 2. OpenAlex (expanded)
  for q in cfg.get("openalex", []):
    for c in search_openalex(q, per_page=35):
      add_cand(c)

  # 3. DOAJ
  for q in cfg.get("doaj", []):
    for c in search_doaj(q, page_size=25):
      add_cand(c)

  # 4. EuropePMC
  for q in cfg.get("epmc", []):
    for c in search_epmc(q, page_size=18):
      add_cand(c)

  # 5. PLOS
  for q in cfg.get("plos", []):
    for c in search_plos(q, rows=12):
      add_cand(c)

  # 6. HAL
  for q in cfg.get("hal", []):
    for c in search_hal(q, rows=15):
      add_cand(c)

  # 7. CEPAL (strictly filtered by title relevance now!)
  for q in cfg.get("cepal", []):
    for c in search_cepal(q, size=12):
      add_cand(c)

  by_dom = {}
  for c in pool:
    by_dom.setdefault(c["publisher_domain"], []).append(c)
  for dom in by_dom:
    by_dom[dom].sort(key=lambda x: (-x["_score"], -x.get("cited_by", 0), -x.get("year", 0)))

  dom_order = sorted(by_dom.keys(), key=lambda d: (dom_used.get(d, 0), -by_dom[d][0]["_score"]))
  ordered = []
  max_len = max((len(v) for v in by_dom.values()), default=0)
  for idx in range(min(max_len, 10)):
    for dom in dom_order:
      if idx < len(by_dom[dom]):
        ordered.append(by_dom[dom][idx])

  need = max(0, TARGET_PER_CHAPTER - len(valid_existing))
  added = 0
  pos = 0
  jurisdiction = ", ".join(ch.get("jurisdictions") or [])

  while added < need and pos < len(ordered) and pos < 260:
    batch = []
    while len(batch) < 16 and pos < len(ordered):
      c = ordered[pos]
      pos += 1
      d_cap = 3 if len(dom_used) < 6 else 4
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
        d_cap = 3 if len(dom_used) < 6 else 4
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
  prune_strays(itin)
  demres_all = load_demres_catalog()
  print(f"[INIT] Loaded {len(demres_all)} cached Demographic Research articles.", flush=True)

  global_hashes = set()
  for ch in itin["chapters"]:
    pdir = os.path.join(JAGUAR_DIR, ch["group"], ch["folder"], "papers")
    for fn in os.listdir(pdir):
      if fn.lower().endswith(".pdf"):
        data = open(os.path.join(pdir, fn), "rb").read()
        if len(data) >= MIN_BYTES and data.startswith(b"%PDF-"):
          global_hashes.add(hashlib.sha256(data).hexdigest())

  all_papers = []
  summary = {}
  t0 = time.time()

  for ch in itin["chapters"]:
    recs = topup_chapter(ch, global_hashes, demres_all)
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
    f"\n[DONE] Pass 2 complete in {elapsed:.1f}s: {len(all_papers)} unique verified PDFs across 14 chapters "
    f"(min_pdfs={manifest['min_chapter_pdfs']}, min_domains={manifest['min_chapter_domains']})",
    flush=True,
  )


if __name__ == "__main__":
  main()
