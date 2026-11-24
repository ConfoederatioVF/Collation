"""Stage C Wave 2 Archival PDF & Bibliography Harvester — Part 2 (QUIPU Ch. 9-17).

Harvests >= 17 (target 18) SHA-256-unique valid %PDF- files (> 15 kB, pymupdf-readable,
concise snake_case.pdf <= 64 chars, repo-rel path <= 180 chars) into each of the 9
post-independence QUIPU chapters, generates <stem>_literature_review.bib (>= 24 unique
BibTeX keys, >= 90% DOI/URL coverage, >= 6 distinct publisher domains, <= 25% per
author/publisher/domain, 0% Zenodo/crowd/banned fallbacks), and writes
QUIPU/_shared/wave2_papers_part2_summary.json.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import html as html_lib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse

import pymupdf
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
QUIPU_DIR = os.path.join(
    SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "QUIPU"
)
POST_IND_DIR = os.path.join(QUIPU_DIR, "3.post_independence")
SUMMARY_PATH = os.path.join(
    QUIPU_DIR, "_shared", "wave2_papers_part2_summary.json"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}

API_HEADERS = {
    "User-Agent": "OperationViscount-QUIPU-Harvester/1.0 (mailto:research@confoederatio.org)"
}

TARGET_PDFS = 18
TARGET_BIB_KEYS = 28
MIN_BYTES = 15400  # strictly > 15 kB (15360 bytes)
MAX_BYTES = 45 * 1024 * 1024
MAX_WORKERS = 5
MAX_FILENAME_LEN = 64
MAX_RELPATH_LEN = 180

CHAPTERS = [
    {"index": 9, "folder": "1.colombia_after_independence", "stem": "colombia_after_independence", "jurisdiction": "Colombia", "country_term": "Colombia"},
    {"index": 10, "folder": "2.venezuela_after_independence", "stem": "venezuela_after_independence", "jurisdiction": "Venezuela", "country_term": "Venezuela"},
    {"index": 11, "folder": "3.ecuador_after_independence", "stem": "ecuador_after_independence", "jurisdiction": "Ecuador", "country_term": "Ecuador"},
    {"index": 12, "folder": "4.peru_after_independence", "stem": "peru_after_independence", "jurisdiction": "Peru", "country_term": "Peru"},
    {"index": 13, "folder": "5.andean_bolivia_independence", "stem": "andean_bolivia_independence", "jurisdiction": "Bolivia", "country_term": "Bolivia"},
    {"index": 14, "folder": "6.chile_after_independence", "stem": "chile_after_independence", "jurisdiction": "Chile", "country_term": "Chile"},
    {"index": 15, "folder": "7.argentina_after_independence", "stem": "argentina_after_independence", "jurisdiction": "Argentina", "country_term": "Argentina"},
    {"index": 16, "folder": "8.uruguay_after_independence", "stem": "uruguay_after_independence", "jurisdiction": "Uruguay", "country_term": "Uruguay"},
    {"index": 17, "folder": "9.falklands_south_atlantic", "stem": "falklands_south_atlantic", "jurisdiction": "Falkland Islands, South Georgia and South Sandwich Islands", "country_term": "Falkland"},
]

BANNED_AUTHORS = (
    "mcevedy", "colin mcevedy", "richard jones", "klein goldewijk", "goldewijk",
    "maddison", "angus maddison", "tertius chandler", "chandler, tertius",
    "chandler1987", "modelski", "george modelski", "modelski2003", "populstat",
)

BANNED_TITLE_PHRASES = (
    "hyde 3", "hyde 2", "populstat", "maddison project",
    "atlas of world population history", "four thousand years of urban growth",
    "world cities: -3000 to 2000",
)

BANNED_HOSTS = (
    "zenodo.org", "wikidata.org", "wikipedia.org", "wikimedia.org",
    "openstreetmap.org", "geonames.org", "overpass-api", "researchgate.net",
    "academia.edu", "scribd.com", "slideshare.net", "github.com",
    "githubusercontent.com", "osf.io", "figshare.com", "ssrn.com",
)

OFFTOPIC_TERMS = (
    "mouse", "mice", "murine", "zebrafish", "drosophila", "arabidopsis",
    "carcinoma", "chemotherapy", "in vitro", "canine", "feline", "bovine",
    "porcine", "equine", "new species of", "phylogeny of", "taxonomy of",
    "taxonomic revision", "butterfly", "butterflies", "beetle", "beetles",
    "lepidoptera", "coleoptera", "hymenoptera", "amphibian", "lizard",
    "snake", "bird species", "avian", "penguin", "albatross", "petrel",
    "fur seal", "elephant seal", "sea lion", "krill", "copepod", "foraminifera",
    "ostracod", "coral reef", "shark", "echolocation", "orchid", "cactus",
    "fern ", "fungus", "fungi", "mycorrhiz", "soil bacteria", "microbiome",
    "clinical trial", "randomized controlled", "alzheimer", "parkinson",
    "breast cancer", "prostate cancer", "leukemia", "schizophrenia",
    "pesticide", "wastewater", "photovoltaic", "solar cell", "concrete",
    "asphalt", "polymer", "nanoparticle", "catalysis", "quantum",
    "superconductor", "seismology", "earthquake rupture", "volcanic ash",
    "tectonic subduction", "heavy metal toxicity", "rat model", "wistar",
    "sars-cov-2", "covid-19", "monkeypox", "zika", "dengue", "aedes aegypti",
    "anopheles", "malaria", "mangrove", "seagrass", "phytoplankton",
    "zooplankton", "benthic", "trilobite", "ammonite", "dinosaur", "cretaceous",
    "jurassic", "miocene", "pliocene", "eocene", "oligocene", "genome-wide",
    "transcriptome", "mitochondrial dna", "baleen whale", "humpback whale",
    "fin whale", "southern right whale", "blue whale", "sei whale",
    "sperm whale", "kelp gull", "cancer", "tumor", "tumores", "hipertensos",
    "hipertension", "hypertension", "diabetes", "cardiovascular", "odontolog",
    "mordida", "dental", "caries", "pacientes", "patients", "hospitaliz",
    "chagas", "leishmania", "tuberculosis", "asthma", "asma", "obesity",
    "obesidad", "sobrepeso", "overweight", "nutricional", "malnutrition",
    "desnutricion", "anemia", "parasit", "helminth", "protozoa", "bacteria",
    "virus", "fungal", "trout", "salmon", "squid", "octopus", "kelp",
    "macroalgae", "bryophyte", "lichen", "spider", "mosquito", "tick ",
    "flea ", "sediment", "stratigraph", "diatom", "pollen", "palynolog",
    "geochem", "isotope", "isotop", "petrolog", "mineralog", "glacier",
    "ice core", "permafrost", "seafloor", "bathymetr", "hydrograph",
    # Extra surgical exclusions found in Wave 2 Part 2 audit:
    "hipopotam", "megaherbivoro", "peces", "bagre", "brachyplatystoma",
    "crocodile", "crocodylus", "dolphin", "sotalia", "becerro", "cabra",
    "caprin", "ovino", "ovinos", "canes vagabundos", "burrowing owl",
    "athene cunicularia", "pampas cat", "leopardus", "aves del area",
    "argopecten", "insuetophrynus", "frog", "entomofauna", "vector",
    "trypanosoma", "streptococcus", "hepatitis", "vih", "hiv", "sepsis",
    "colecistect", "quirurg", "cirugia", "periodontal", "protesic",
    "estilohioideo", "apendicitis", "burnout", "dinamometria", "fuerza de agarre",
    "trastornos alimentario", "trastornos mentales", "depresion mayor",
    "polimorfismo", "slc6a4", "bdnf", "microsatelite", "forense",
    "sindrome metabolico", "presion arterial", "mortalidad perinatal",
    "mortalidad materna", "mortalidad perioperatoria", "hydrocarbon",
    "petroleum", "hybridization", "gene flow", "rabies", "intramuestral",
    "prehistoric", "prehispanic", "pre-columbian", "casarabe", "cattle",
    "livestock", "porcino", "bovino", "acuicola", "pesquera", "biodivers",
    "flora", "fauna", "zoolog", "clinica", "epidemiol", "morbilidad empresarial",
    "pymes", "censo nacional de psicologia", "caminabilidad",
    "amor en una poblacion", "alimentacion familiar", "antropometrico",
    "discapacidad en poblacion", "violencia urbana", "recluida en las carceles",
    "poblacion votante", "imaginarios de turistas", "mineralizacion",
    "primeros auxilios psicologicos", "portador nasofaringeo",
    "amamantamiento", "intervalo entre partos", "oral health",
    "daily observational record", "1600-1765", "viceroyalty", "testamentos indigenas",
    "bmwp", "physico-chemical", "reino de valencia", "severe depression",
    "stunting", "vaccination coverage", "annelid", "brachiopod", "ordovician",
    "adolescent pregnancy", "embarazo adolescente", "san luis potosi",
    "especies arboreas", "liquenes", "copistas musicales", "emprendimiento",
    "aguilucho", "buteo",
)

OFFTOPIC_JOURNAL_TERMS = (
    "medic", "cirug", "odon", "aves ", "avesargentinas", "ecologia", "biomed", "hospital",
    "zootec", "veterin", "marine", "biodiv", "geol", "petrol", "psico",
    "entom", "lillo", "fecolsog", "ciencias marinas", "pensoft", "raccefyn",
    "humboldt", "fder", "salud publica", "enfermer", "nutric", "cardiol",
    "oncol", "pediatr", "ginecol", "obstetr", "neuro", "farmac",
    "maternofetal", "polibotanica", "bmj", "f1000",
)

CURATED_DIRECT_PDFS = {
    "colombia_after_independence": [
        {
            "title": "Informe técnico de caracterización poblacional en páramos a partir del Censo Nacional de Población y Vivienda CNPV 2018",
            "authors": ["Departamento Administrativo Nacional de Estadística (DANE)"],
            "year": 2021,
            "journal_or_publisher": "DANE Colombia",
            "publisher_domain": "dane.gov.co",
            "doi": "",
            "url": "https://www.dane.gov.co/files/censo2018/informacion-tecnica/Informe-tecnico-caracterizacion-poblacional-paramos-CNPV2018.pdf",
            "pdf_url": "https://www.dane.gov.co/files/censo2018/informacion-tecnica/Informe-tecnico-caracterizacion-poblacional-paramos-CNPV2018.pdf",
            "bib_type": "techreport",
        },
        {
            "title": "Censo Nacional de Población y Vivienda 2018: Lecciones aprendidas",
            "authors": ["Departamento Administrativo Nacional de Estadística (DANE)"],
            "year": 2020,
            "journal_or_publisher": "DANE Colombia",
            "publisher_domain": "dane.gov.co",
            "doi": "",
            "url": "https://www.dane.gov.co/files/censo2018/informacion-tecnica/CNPV-2018-lecciones-aprendidas-NTCE-PE-1000.pdf",
            "pdf_url": "https://www.dane.gov.co/files/censo2018/informacion-tecnica/CNPV-2018-lecciones-aprendidas-NTCE-PE-1000.pdf",
            "bib_type": "techreport",
        },
    ],
    "ecuador_after_independence": [
        {
            "title": "Evolución de las variables investigadas en los censos de población y vivienda del Ecuador 1950-2010",
            "authors": ["Instituto Nacional de Estadística y Censos (INEC)"],
            "year": 2014,
            "journal_or_publisher": "INEC Ecuador",
            "publisher_domain": "ecuadorencifras.gob.ec",
            "doi": "",
            "url": "https://www.ecuadorencifras.gob.ec/documentos/web-inec/Publicaciones/Evolucion_variables_1950_2010_24_04_2014.pdf",
            "pdf_url": "https://www.ecuadorencifras.gob.ec/documentos/web-inec/Publicaciones/Evolucion_variables_1950_2010_24_04_2014.pdf",
            "bib_type": "techreport",
        },
        {
            "title": "Resultados Nacionales del VII Censo de Población y VI de Vivienda 2010",
            "authors": ["Instituto Nacional de Estadística y Censos (INEC)"],
            "year": 2011,
            "journal_or_publisher": "INEC Ecuador",
            "publisher_domain": "ecuadorencifras.gob.ec",
            "doi": "",
            "url": "https://www.ecuadorencifras.gob.ec/documentos/web-inec/Poblacion_y_Demografia/CPV_aplicativos/datos_generales_cpv/resultados_nacionales_cpv2010.pdf",
            "pdf_url": "https://www.ecuadorencifras.gob.ec/documentos/web-inec/Poblacion_y_Demografia/CPV_aplicativos/datos_generales_cpv/resultados_nacionales_cpv2010.pdf",
            "bib_type": "techreport",
        },
        {
            "title": "Conciliación Demográfica del Ecuador 1950-2022",
            "authors": ["Instituto Nacional de Estadística y Censos (INEC)"],
            "year": 2023,
            "journal_or_publisher": "INEC Ecuador",
            "publisher_domain": "ecuadorencifras.gob.ec",
            "doi": "",
            "url": "https://www.ecuadorencifras.gob.ec/documentos/web-inec/Bibliotecas/Libros/cuadernos_trabajo/Conciliacion_Demogr%C3%A1fica.pdf",
            "pdf_url": "https://www.ecuadorencifras.gob.ec/documentos/web-inec/Bibliotecas/Libros/cuadernos_trabajo/Conciliacion_Demogr%C3%A1fica.pdf",
            "bib_type": "techreport",
        },
    ],
    "chile_after_independence": [
        {
            "title": "Los Censos de Población en Chile y su evolución histórica hacia el Bicentenario",
            "authors": ["Biblioteca Nacional de Chile"],
            "year": 2010,
            "journal_or_publisher": "Memoria Chilena",
            "publisher_domain": "memoriachilena.gob.cl",
            "doi": "",
            "url": "https://www.memoriachilena.gob.cl/602/w3-article-10433.html",
            "pdf_url": "https://www.memoriachilena.gob.cl/archivos2/pdfs/MC0054244.pdf",
            "bib_type": "book",
        },
        {
            "title": "Informe Demográfico de Chile según resultados del Censo de 1992",
            "authors": ["Instituto Nacional de Estadísticas de Chile (INE)"],
            "year": 1995,
            "journal_or_publisher": "Memoria Chilena / INE",
            "publisher_domain": "memoriachilena.gob.cl",
            "doi": "",
            "url": "https://www.memoriachilena.gob.cl/602/w3-article-93116.html",
            "pdf_url": "https://www.memoriachilena.gob.cl/archivos2/pdfs/MC0056306.pdf",
            "bib_type": "book",
        },
        {
            "title": "Síntesis de Resultados del Censo de Población y Vivienda 2017 de Chile",
            "authors": ["Instituto Nacional de Estadísticas de Chile (INE)"],
            "year": 2018,
            "journal_or_publisher": "INE Chile",
            "publisher_domain": "ine.gob.cl",
            "doi": "",
            "url": "https://www.ine.gob.cl/estadisticas/sociales/censos-de-poblacion-y-vivienda/informacion-historica-censo-de-poblacion-y-vivienda",
            "pdf_url": "http://www.ine.gob.cl/docs/default-source/censo-de-poblacion-y-vivienda/publicaciones-y-anuarios/2017/publicaci%C3%B3n-de-resultados/sintesis-de-resultados-censo2017.pdf",
            "bib_type": "techreport",
        },
    ],
    "falklands_south_atlantic": [
        {
            "title": "Falkland Islands Census Report 2021",
            "authors": ["Falkland Islands Policy and Economic Development Directorate"],
            "year": 2022,
            "journal_or_publisher": "Falkland Islands Government",
            "publisher_domain": "gov.fk",
            "doi": "",
            "url": "https://www.gov.fk/policy/2021-census/",
            "pdf_url": "https://www.gov.fk/policy/wp-content/uploads/sites/33/2026/05/Falkland-Islands-Census-Report-2021.pdf",
            "bib_type": "techreport",
        },
        {
            "title": "Falkland Islands Census 2016: Full Report",
            "authors": ["Falkland Islands Policy Unit"],
            "year": 2017,
            "journal_or_publisher": "Falkland Islands Government",
            "publisher_domain": "gov.fk",
            "doi": "",
            "url": "https://www.gov.fk/policy/downloads/",
            "pdf_url": "https://www.gov.fk/policy/wp-content/uploads/sites/33/2026/05/Falkland_Islands_Census_2016_-_Full_Report.pdf",
            "bib_type": "techreport",
        },
        {
            "title": "Falkland Islands Census 2012: Headline Results and Data Tables",
            "authors": ["Falkland Islands Statistics Office"],
            "year": 2013,
            "journal_or_publisher": "Falkland Islands Government",
            "publisher_domain": "gov.fk",
            "doi": "",
            "url": "https://www.gov.fk/policy/downloads/",
            "pdf_url": "https://www.gov.fk/policy/wp-content/uploads/sites/33/2026/05/Falkland-Islands-Census-2012-Data-Tables-and-Stats.pdf",
            "bib_type": "techreport",
        },
        {
            "title": "South Georgia and the South Sandwich Islands Heritage Baseline Assessment",
            "authors": ["Government of South Georgia and the South Sandwich Islands (GSGSSI)"],
            "year": 2020,
            "journal_or_publisher": "GSGSSI",
            "publisher_domain": "gov.gs",
            "doi": "",
            "url": "https://gov.gs/",
            "pdf_url": "https://gov.gs/wp-content/uploads/2026/05/ITT-Heritage-Baseline-Assessment-.pdf",
            "bib_type": "techreport",
        },
    ],
}

CURATED_CANONICAL_BIB = {
    "chile_after_independence": [
        {
            "title": "Censo jeneral de la República de Chile levantado el 19 de abril de 1865",
            "authors": ["Oficina Central de Estadística de Chile"],
            "year": 1866,
            "journal_or_publisher": "Imprenta Nacional / Memoria Chilena",
            "publisher_domain": "memoriachilena.gob.cl",
            "doi": "",
            "url": "https://www.memoriachilena.gob.cl/602/w3-article-82446.html",
            "bib_type": "book",
        },
        {
            "title": "Sesto Censo Jeneral de la Población de Chile levantado el 26 de noviembre de 1885",
            "authors": ["Oficina Central de Estadística de Chile"],
            "year": 1889,
            "journal_or_publisher": "Imprenta de la Patria / Memoria Chilena",
            "publisher_domain": "memoriachilena.gob.cl",
            "doi": "",
            "url": "https://www.memoriachilena.gob.cl/602/w3-article-82447.html",
            "bib_type": "book",
        },
        {
            "title": "Memoria presentada al Supremo Gobierno por la Comisión Central del Censo de 1907",
            "authors": ["Comisión Central del Censo de Chile"],
            "year": 1908,
            "journal_or_publisher": "Imprenta Universo / Memoria Chilena",
            "publisher_domain": "memoriachilena.gob.cl",
            "doi": "",
            "url": "https://www.memoriachilena.gob.cl/602/w3-article-8117.html",
            "bib_type": "book",
        },
        {
            "title": "Censo de población de la República de Chile levantado el 15 de diciembre de 1920",
            "authors": ["Dirección General de Estadística de Chile"],
            "year": 1925,
            "journal_or_publisher": "Sociedad Imprenta y Litografía Universo",
            "publisher_domain": "memoriachilena.gob.cl",
            "doi": "",
            "url": "https://www.memoriachilena.gob.cl/602/w3-article-82449.html",
            "bib_type": "book",
        },
    ],
}

DEMO_JOURNALS_Q = (
    '("Revista Latinoamericana de Población" OR "Papeles de Población" '
    'OR "Estudios Demográficos y Urbanos" OR "EURE" OR "Demographic Research" '
    'OR "Notas de Población" OR "Historia Crítica" '
    'OR "Bulletin de l\'Institut français d\'études andines" '
    'OR "Anuario Colombiano de Historia Social y de la Cultura" '
    'OR "Revista de Demografía Histórica" OR "Migraciones Internacionales" '
    'OR "Desarrollo y Sociedad" OR "Cuadernos de Economía" '
    'OR "Revista Uruguaya de Historia Económica" OR "Mundo Agrario" '
    'OR "Revista de Historia" OR "Estudios Migratorios")'
)

CHAPTER_CONFIG = {
    "colombia_after_independence": {
        "crossref": [
            ("Colombia", "population census historical demography"),
            ("Colombia", "urbanization Bogota Medellin Cali population"),
            ("Colombia", "demografia historica censo poblacion"),
            ("Nueva Granada", "poblacion censo siglo XIX"),
        ],
        "doaj": [
            f"bibjson.journal.title:{DEMO_JOURNALS_Q} AND Colombia",
            "bibjson.title:Colombia AND (bibjson.title:demografia OR bibjson.title:demografica OR bibjson.title:censo OR bibjson.title:urbanizacion)",
            "bibjson.title:Colombia AND (bibjson.title:fecundidad OR bibjson.title:envejecimiento OR bibjson.title:transicion OR bibjson.title:poblamiento)",
            "(bibjson.title:Bogota OR bibjson.title:Medellin OR bibjson.title:Cali OR bibjson.title:Antioquia) AND (bibjson.title:poblacion OR bibjson.title:urbana OR bibjson.title:demografia OR bibjson.title:censo)",
            "bibjson.title:Colombia AND (bibjson.title:demographic OR bibjson.title:census OR bibjson.title:urbanization)",
        ],
        "hal": ["Colombie population demographie", "Colombie urbanisation Bogota"],
        "cepal": ["Colombia censo poblacion", "Colombia fecundidad mortalidad", "Colombia urbanizacion proyecciones"],
        "conicet": ["Colombia poblacion censo demografia"],
        "banrep": ["censo poblacion Colombia", "demografia historica Colombia", "crecimiento urbano Colombia"],
        "ia": ['title:(Colombia) AND title:(censo OR poblacion OR census OR population)'],
        "plos": ["Colombia demographic migration urbanization"],
        "pos_geo": (
            "colombia", "colombian", "colombiana", "colombiano", "bogota", "medellin",
            "cali", "barranquilla", "cartagena", "bucaramanga", "antioquia",
            "cundinamarca", "valle del cauca", "boyaca", "santander", "cauca",
            "tolima", "huila", "narino", "new granada", "nueva granada",
            "gran colombia", "choco", "magdalena", "bolivar", "popayan",
            "tunja", "manizales", "pereira", "colombie",
        ),
        "pos_topic": (
            "population", "poblacion", "census", "censo", "demograph", "demograf",
            "urban", "urbaniz", "migration", "migracion", "fertility", "fecundidad",
            "mortality", "mortalidad", "growth", "crecimiento", "settlement",
            "asentamiento", "colonization", "colonizacion", "city", "ciudad",
            "statist", "estadist", "natalidad", "envejecimiento", "peuplement",
            "recensement", "poblamiento", "siglo xix", "siglo xx", "historia",
        ),
    },
    "venezuela_after_independence": {
        "crossref": [
            ("Venezuela", "population census historical demography"),
            ("Venezuela", "Caracas Maracaibo urbanization population"),
            ("Venezuela", "censo poblacion demografia migracion"),
            ("Venezuela", "fertility mortality demographic transition"),
        ],
        "doaj": [
            f"bibjson.journal.title:{DEMO_JOURNALS_Q} AND Venezuela",
            "bibjson.title:Venezuela AND (bibjson.title:demografia OR bibjson.title:demografica OR bibjson.title:censo OR bibjson.title:urbanizacion)",
            "bibjson.title:Venezuela AND (bibjson.title:migracion OR bibjson.title:fecundidad OR bibjson.title:envejecimiento OR bibjson.title:transicion)",
            "(bibjson.title:Caracas OR bibjson.title:Maracaibo OR bibjson.title:Zulia OR bibjson.title:Valencia) AND (bibjson.title:poblacion OR bibjson.title:urbana OR bibjson.title:demografia OR bibjson.title:censo)",
            "bibjson.title:Venezuela AND (bibjson.title:demographic OR bibjson.title:census OR bibjson.title:migration)",
        ],
        "hal": ["Venezuela population demographie", "Venezuela Caracas urbanisation migration"],
        "cepal": ["Venezuela censo poblacion", "Venezuela demografia proyecciones", "Venezuela fecundidad mortalidad"],
        "conicet": ["Venezuela migracion poblacion demografia"],
        "banrep": ["migracion Venezuela Colombia poblacion"],
        "ia": ['title:(Venezuela) AND title:(censo OR poblacion OR census OR population)'],
        "plos": ["Venezuela migration demographic urbanization"],
        "pos_geo": (
            "venezuela", "venezuelan", "venezolana", "venezolano", "caracas",
            "maracaibo", "valencia", "barquisimeto", "maracay", "ciudad guayana",
            "zulia", "carabobo", "miranda", "lara", "aragua", "merida", "tachira",
            "trujillo", "sucre", "bolivar", "orinoco", "llanos", "angostura",
            "cumana", "coro", "falcon", "anzoategui", "monagas", "guayana",
        ),
        "pos_topic": (
            "population", "poblacion", "census", "censo", "demograph", "demograf",
            "urban", "urbaniz", "migration", "migracion", "fertility", "fecundidad",
            "mortality", "mortalidad", "growth", "crecimiento", "settlement",
            "statist", "estadist", "city", "ciudad", "peuplement", "recensement",
            "envejecimiento", "natalidad", "poblamiento", "siglo xix", "siglo xx",
        ),
    },
    "ecuador_after_independence": {
        "crossref": [
            ("Ecuador", "population census historical demography"),
            ("Ecuador", "Quito Guayaquil urbanization population"),
            ("Ecuador", "censo poblacion demografia migracion"),
            ("Ecuador", "fertility mortality demographic transition"),
        ],
        "doaj": [
            f"bibjson.journal.title:{DEMO_JOURNALS_Q} AND Ecuador",
            "bibjson.title:Ecuador AND (bibjson.title:demografia OR bibjson.title:demografica OR bibjson.title:censo OR bibjson.title:urbanizacion)",
            "bibjson.title:Ecuador AND (bibjson.title:migracion OR bibjson.title:fecundidad OR bibjson.title:envejecimiento OR bibjson.title:poblamiento)",
            "(bibjson.title:Quito OR bibjson.title:Guayaquil OR bibjson.title:Cuenca OR bibjson.title:Guayas) AND (bibjson.title:poblacion OR bibjson.title:urbana OR bibjson.title:demografia OR bibjson.title:censo)",
            "bibjson.title:Ecuador AND (bibjson.title:demographic OR bibjson.title:census OR bibjson.title:migration)",
        ],
        "hal": ["Equateur population demographie", "Equateur Quito Guayaquil urbanisation"],
        "cepal": ["Ecuador censo poblacion", "Ecuador demografia proyecciones", "Ecuador indigena afrodescendiente censo"],
        "conicet": ["Ecuador poblacion censo migracion"],
        "banrep": [],
        "ia": ['title:(Ecuador) AND title:(censo OR poblacion OR census OR population)'],
        "plos": ["Ecuador demographic migration urbanization"],
        "pos_geo": (
            "ecuador", "ecuadorian", "ecuatoriana", "ecuatoriano", "quito",
            "guayaquil", "cuenca", "ambato", "riobamba", "loja", "machala",
            "manta", "portoviejo", "esmeraldas", "ibarra", "latacunga",
            "guayas", "pichincha", "azuay", "manabi", "tungurahua", "chimborazo",
            "imbabura", "cotopaxi", "galapagos", "oriente", "equateur",
        ),
        "pos_topic": (
            "population", "poblacion", "census", "censo", "demograph", "demograf",
            "urban", "urbaniz", "migration", "migracion", "fertility", "fecundidad",
            "mortality", "mortalidad", "growth", "crecimiento", "settlement",
            "statist", "estadist", "indigenous", "indigena", "city", "ciudad",
            "envejecimiento", "peuplement", "recensement", "poblamiento",
        ),
    },
    "peru_after_independence": {
        "crossref": [
            ("Peru", "population census historical demography"),
            ("Peru", "Lima Arequipa Cusco urbanization population"),
            ("Peru", "censo poblacion demografia migracion"),
            ("Peru", "fertility mortality demographic transition"),
        ],
        "doaj": [
            f"bibjson.journal.title:{DEMO_JOURNALS_Q} AND Peru",
            "bibjson.title:Peru AND (bibjson.title:demografia OR bibjson.title:demografica OR bibjson.title:censo OR bibjson.title:urbanizacion)",
            "bibjson.title:Peru AND (bibjson.title:migracion OR bibjson.title:fecundidad OR bibjson.title:envejecimiento OR bibjson.title:poblamiento)",
            "(bibjson.title:Lima OR bibjson.title:Cusco OR bibjson.title:Arequipa OR bibjson.title:Puno) AND (bibjson.title:poblacion OR bibjson.title:urbana OR bibjson.title:demografia OR bibjson.title:censo OR bibjson.title:migracion)",
            "bibjson.title:Peru AND (bibjson.title:demographic OR bibjson.title:census OR bibjson.title:urbanization)",
            "bibjson.title:Perú AND (bibjson.title:historia OR bibjson.title:siglo OR bibjson.title:población OR bibjson.title:migración)",
        ],
        "hal": ["Perou population demographie", "Perou Lima Andes migration urbanisation"],
        "cepal": ["Peru censo poblacion", "Peru demografia proyecciones", "Peru migracion urbanizacion"],
        "conicet": ["Peru poblacion censo demografia"],
        "banrep": [],
        "ia": ['title:(Peru) AND title:(censo OR poblacion OR census OR population)'],
        "plos": ["Peru demographic migration Lima"],
        "pos_geo": (
            "peru", "peruvian", "peruana", "peruano", "perou", "lima", "arequipa",
            "cusco", "cuzco", "trujillo", "chiclayo", "piura", "iquitos", "huancayo",
            "tacna", "puno", "ayacucho", "cajamarca", "ancash", "junin", "loreto",
            "lambayeque", "la libertad", "callao", "moquegua", "apurimac",
        ),
        "pos_topic": (
            "population", "poblacion", "census", "censo", "demograph", "demograf",
            "urban", "urbaniz", "migration", "migracion", "fertility", "fecundidad",
            "mortality", "mortalidad", "growth", "crecimiento", "settlement",
            "statist", "estadist", "indigenous", "indigena", "city", "ciudad",
            "peuplement", "recensement", "envejecimiento", "poblamiento",
        ),
    },
    "andean_bolivia_independence": {
        "crossref": [
            ("Bolivia", "population census historical demography"),
            ("Bolivia", "La Paz Cochabamba Santa Cruz urbanization population"),
            ("Bolivia", "censo poblacion demografia migracion"),
            ("Bolivia", "fertility mortality demographic transition"),
        ],
        "doaj": [
            f"bibjson.journal.title:{DEMO_JOURNALS_Q} AND Bolivia",
            "bibjson.title:Bolivia AND (bibjson.title:demografia OR bibjson.title:demografica OR bibjson.title:censo OR bibjson.title:urbanizacion)",
            "bibjson.title:Bolivia AND (bibjson.title:migracion OR bibjson.title:fecundidad OR bibjson.title:envejecimiento OR bibjson.title:poblamiento)",
            "(bibjson.title:\"La Paz\" OR bibjson.title:Cochabamba OR bibjson.title:Potosi OR bibjson.title:\"Santa Cruz\") AND (bibjson.title:poblacion OR bibjson.title:urbana OR bibjson.title:demografia OR bibjson.title:censo OR bibjson.title:migracion)",
            "bibjson.title:Bolivia AND (bibjson.title:demographic OR bibjson.title:census OR bibjson.title:migration)",
        ],
        "hal": ["Bolivie population demographie", "Bolivie altiplano migration urbanisation"],
        "cepal": ["Bolivia censo poblacion", "Bolivia demografia proyecciones", "Bolivia pueblos indigenas censo"],
        "conicet": ["Bolivia poblacion censo demografia"],
        "banrep": [],
        "ia": ['title:(Bolivia) AND title:(censo OR poblacion OR census OR population)'],
        "plos": ["Bolivia demographic migration urbanization"],
        "pos_geo": (
            "bolivia", "bolivian", "boliviana", "boliviano", "bolivie",
            "la paz", "el alto", "cochabamba", "sucre", "potosi", "oruro",
            "tarija", "santa cruz", "altiplano", "titicaca", "chuquisaca",
            "beni", "pando", "yungas", "upper peru", "alto peru", "charcas",
        ),
        "pos_topic": (
            "population", "poblacion", "census", "censo", "demograph", "demograf",
            "urban", "urbaniz", "migration", "migracion", "fertility", "fecundidad",
            "mortality", "mortalidad", "growth", "crecimiento", "settlement",
            "statist", "estadist", "indigenous", "indigena", "city", "ciudad",
            "peuplement", "recensement", "envejecimiento", "poblamiento",
        ),
    },
    "chile_after_independence": {
        "crossref": [
            ("Chile", "population census historical demography"),
            ("Chile", "Santiago Valparaiso urbanization population"),
            ("Chile", "censo poblacion demografia migracion"),
            ("Chile", "fertility mortality demographic transition"),
        ],
        "doaj": [
            f"bibjson.journal.title:{DEMO_JOURNALS_Q} AND Chile",
            "bibjson.title:Chile AND (bibjson.title:demografia OR bibjson.title:demografica OR bibjson.title:censo OR bibjson.title:urbanizacion)",
            "bibjson.title:Chile AND (bibjson.title:migracion OR bibjson.title:inmigracion OR bibjson.title:fecundidad OR bibjson.title:envejecimiento)",
            "(bibjson.title:Santiago OR bibjson.title:Valparaiso OR bibjson.title:Concepcion OR bibjson.title:Magallanes OR bibjson.title:Araucania) AND (bibjson.title:poblacion OR bibjson.title:urbana OR bibjson.title:demografia OR bibjson.title:censo)",
            "bibjson.title:Chile AND (bibjson.title:demographic OR bibjson.title:census OR bibjson.title:migration)",
        ],
        "hal": ["Chili population demographie", "Chili Santiago urbanisation migration"],
        "cepal": ["Chile censo poblacion", "Chile demografia proyecciones", "Chile fecundidad mortalidad"],
        "conicet": ["Chile poblacion censo demografia"],
        "banrep": [],
        "ia": ['title:(Chile) AND title:(censo OR poblacion OR census OR population)'],
        "plos": ["Chile demographic migration urbanization"],
        "pos_geo": (
            "chile", "chilean", "chilena", "chileno", "chili", "santiago",
            "valparaiso", "concepcion", "antofagasta", "temuco", "valdivia",
            "puerto montt", "punta arenas", "iquique", "la serena", "talca",
            "chillan", "osorno", "araucania", "magallanes", "tarapaca", "atacama",
            "biobio", "los lagos", "patagonia", "tierra del fuego", "chiloe",
        ),
        "pos_topic": (
            "population", "poblacion", "census", "censo", "demograph", "demograf",
            "urban", "urbaniz", "migration", "migracion", "fertility", "fecundidad",
            "mortality", "mortalidad", "growth", "crecimiento", "settlement",
            "statist", "estadist", "immigra", "inmigra", "city", "ciudad",
            "peuplement", "recensement", "envejecimiento", "poblamiento",
        ),
    },
    "argentina_after_independence": {
        "crossref": [
            ("Argentina", "population census historical demography"),
            ("Argentina", "Buenos Aires Rosario Cordoba urbanization population"),
            ("Argentina", "censo poblacion demografia inmigracion"),
            ("Argentina", "fertility mortality demographic transition"),
        ],
        "doaj": [
            f"bibjson.journal.title:{DEMO_JOURNALS_Q} AND Argentina",
            "bibjson.title:Argentina AND (bibjson.title:demografia OR bibjson.title:demografica OR bibjson.title:censo OR bibjson.title:urbanizacion)",
            "bibjson.title:Argentina AND (bibjson.title:migracion OR bibjson.title:inmigracion OR bibjson.title:fecundidad OR bibjson.title:envejecimiento OR bibjson.title:poblamiento)",
            "(bibjson.title:\"Buenos Aires\" OR bibjson.title:Rosario OR bibjson.title:Cordoba OR bibjson.title:Patagonia OR bibjson.title:Pampa) AND (bibjson.title:poblacion OR bibjson.title:demografia OR bibjson.title:censo OR bibjson.title:inmigracion OR bibjson.title:poblamiento)",
            "bibjson.title:Argentina AND (bibjson.title:demographic OR bibjson.title:census OR bibjson.title:immigration)",
        ],
        "hal": ["Argentine population demographie", "Argentine Buenos Aires immigration urbanisation"],
        "cepal": ["Argentina censo poblacion", "Argentina demografia proyecciones", "Argentina fecundidad mortalidad"],
        "conicet": ["censo poblacion Argentina", "demografia historica Argentina", "poblamiento Patagonia Buenos Aires"],
        "banrep": [],
        "ia": ['title:(Argentina) AND title:(censo OR poblacion OR census OR population)'],
        "plos": ["Argentina demographic migration urbanization"],
        "pos_geo": (
            "argentina", "argentine", "argentinian", "buenos aires", "rosario",
            "cordoba", "mendoza", "tucuman", "la plata", "mar del plata",
            "salta", "santa fe", "bahia blanca", "san juan", "corrientes",
            "entre rios", "pampas", "pampa", "patagonia", "chaco", "misiones",
            "neuquen", "rio negro", "chubut", "santa cruz", "tierra del fuego",
            "jujuy", "catamarca", "la rioja", "san luis", "santiago del estero",
        ),
        "pos_topic": (
            "population", "poblacion", "census", "censo", "demograph", "demograf",
            "urban", "urbaniz", "migration", "migracion", "immigra", "inmigra",
            "fertility", "fecundidad", "mortality", "mortalidad", "growth",
            "crecimiento", "settlement", "poblamiento", "statist", "estadist",
            "peuplement", "recensement", "envejecimiento", "siglo xix", "siglo xx",
        ),
    },
    "uruguay_after_independence": {
        "crossref": [
            ("Uruguay", "population census historical demography"),
            ("Uruguay", "Montevideo urbanization immigration population"),
            ("Uruguay", "censo poblacion demografia fecundidad"),
            ("Uruguay", "demographic transition aging mortality"),
        ],
        "doaj": [
            f"bibjson.journal.title:{DEMO_JOURNALS_Q} AND Uruguay",
            "bibjson.title:Uruguay AND (bibjson.title:demografia OR bibjson.title:demografica OR bibjson.title:censo OR bibjson.title:urbanizacion)",
            "bibjson.title:Uruguay AND (bibjson.title:migracion OR bibjson.title:inmigracion OR bibjson.title:fecundidad OR bibjson.title:envejecimiento OR bibjson.title:transicion)",
            "(bibjson.title:Montevideo OR bibjson.title:Salto OR bibjson.title:Paysandu OR bibjson.title:\"Banda Oriental\") AND (bibjson.title:poblacion OR bibjson.title:demografia OR bibjson.title:censo OR bibjson.title:urbana OR bibjson.title:inmigracion)",
            "bibjson.title:Uruguay AND (bibjson.title:demographic OR bibjson.title:census OR bibjson.title:migration)",
        ],
        "hal": ["Uruguay population demographie", "Uruguay Montevideo immigration urbanisation"],
        "cepal": ["Uruguay censo poblacion", "Uruguay demografia proyecciones", "Uruguay envejecimiento fecundidad"],
        "conicet": ["Uruguay poblacion censo demografia", "Montevideo Rio de la Plata poblacion"],
        "banrep": [],
        "ia": ['title:(Uruguay) AND title:(censo OR poblacion OR census OR population)'],
        "plos": ["Uruguay demographic migration aging"],
        "pos_geo": (
            "uruguay", "uruguayan", "uruguaya", "uruguayo", "montevideo",
            "salto", "paysandu", "maldonado", "canelones", "rivera", "tacuarembo",
            "melo", "mercedes", "minas", "colonia", "rocha", "florida",
            "durazno", "artigas", "san jose", "soriano", "rio negro", "treinta y tres",
            "banda oriental", "rio de la plata",
        ),
        "pos_topic": (
            "population", "poblacion", "census", "censo", "demograph", "demograf",
            "urban", "urbaniz", "migration", "migracion", "immigra", "inmigra",
            "fertility", "fecundidad", "mortality", "mortalidad", "aging",
            "envejecimiento", "growth", "crecimiento", "settlement", "statist",
            "peuplement", "recensement", "fecundite", "poblamiento",
        ),
    },
    "falklands_south_atlantic": {
        "crossref": [
            ("Falkland", "population census settlement history"),
            ("Falkland", "society economy demographic migration"),
            ("Malvinas", "historia poblacion colonizacion"),
            ("South Georgia", "whaling station Grytviken history heritage"),
        ],
        "doaj": [
            "(bibjson.title:Falkland OR bibjson.title:Malvinas) AND (bibjson.title:population OR bibjson.title:poblacion OR bibjson.title:census OR bibjson.title:history OR bibjson.title:historia OR bibjson.title:society OR bibjson.title:economy OR bibjson.title:settlement)",
            "(bibjson.title:Falkland OR bibjson.title:Malvinas) AND (bibjson.title:islands OR bibjson.title:islas OR bibjson.title:colonial OR bibjson.title:sovereignty OR bibjson.title:community OR bibjson.title:migration)",
            "bibjson.title:\"South Georgia\" AND (bibjson.title:whaling OR bibjson.title:heritage OR bibjson.title:history OR bibjson.title:station OR bibjson.title:Grytviken)",
            "bibjson.title:\"South Atlantic\" AND (bibjson.title:whaling OR bibjson.title:islands OR bibjson.title:settlement OR bibjson.title:colonial)",
        ],
        "hal": [
            "Malouines Falkland histoire",
            "Falkland Islands history settlement",
            "South Georgia whaling history",
        ],
        "cepal": [],
        "conicet": ["Malvinas poblacion historia", "Islas del Atlantico Sur historia"],
        "banrep": [],
        "nora": ["South Georgia Grytviken heritage", "South Georgia whaling history"],
        "ia": [
            'title:("Falkland Islands") AND (history OR population OR census OR colony OR settlement)',
            'title:("South Georgia") AND (whaling OR Grytviken OR history OR Shackleton)',
        ],
        "plos": ["Falkland Islands community"],
        "pos_geo": (
            "falkland", "falklands", "malvinas", "port stanley", "stanley",
            "south georgia", "grytviken", "stromness", "leith harbour",
            "husvik", "south sandwich", "south atlantic", "mount pleasant",
            "goose green", "west falkland", "east falkland", "malouines",
        ),
        "pos_topic": (
            "population", "poblacion", "census", "censo", "demograph", "demograf",
            "settlement", "settled", "settler", "inhabitant", "resident",
            "colony", "colonial", "islanders", "whaling", "whaler", "station",
            "heritage", "history", "historical", "historia", "socioeconomic",
            "migration", "immigra", "labour", "labor", "employment", "community",
            "economy", "sheep", "wool", "govern", "sovereignty", "territory",
            "camp", "town", "village", "crew", "expedition", "society", "sociedad",
            "ocupacion", "poblamiento", "colonizacion", "island", "isla",
        ),
    },
}


def clean_text(s):
  if isinstance(s, dict):
    s = next((v for v in s.values() if isinstance(v, str) and v.strip()), "")
  elif isinstance(s, list):
    s = s[0] if s else ""
  txt = html_lib.unescape(str(s or ""))
  if txt.startswith("{") and ("'en_US':" in txt or '"en_US":' in txt):
    m = re.search(r"['\"][a-z]{2}_[A-Z]{2}['\"]\s*:\s*['\"](.+?)['\"]\s*}", txt)
    if m:
      txt = m.group(1)
  txt = re.sub(r"<[^>]+>", " ", txt)
  return re.sub(r"\s+", " ", txt).strip().rstrip("'") if txt.endswith("century'") else re.sub(r"\s+", " ", txt).strip()


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


def first_author_surname(authors):
  if not authors:
    return "unknown"
  first = clean_text(authors[0])
  first = re.sub(r"\([^)]*\)", "", first).strip()
  if "," in first:
    s = first.split(",")[0].strip().lower()
  else:
    parts = first.split()
    s = parts[-1].lower() if parts else "unknown"
  return ascii_slug(s) or "unknown"


def is_banned(title, authors, url, journal=""):
  tl = unicodedata.normalize("NFKD", clean_text(title)).encode("ascii", "ignore").decode("ascii").lower()
  aj = " ".join(str(a) for a in (authors or [])).lower()
  jl = unicodedata.normalize("NFKD", clean_text(journal)).encode("ascii", "ignore").decode("ascii").lower()
  ul = str(url or "").lower()
  if any(b in aj or b in tl for b in BANNED_AUTHORS):
    return True
  if any(b in tl for b in BANNED_TITLE_PHRASES):
    return True
  if any(h in ul for h in BANNED_HOSTS):
    return True
  if "zenodo" in jl or "zenodo" in ul:
    return True
  if any(t in tl for t in OFFTOPIC_TERMS):
    return True
  if any(j in jl or j in ul for j in OFFTOPIC_JOURNAL_TERMS):
    return True
  return False


def relevance_score(stem, title, journal="", abstract=""):
  cfg = CHAPTER_CONFIG[stem]
  tl = unicodedata.normalize("NFKD", f"{title} {journal}").encode("ascii", "ignore").decode("ascii").lower()
  if any(t in tl for t in OFFTOPIC_TERMS) or any(j in tl for j in OFFTOPIC_JOURNAL_TERMS):
    return 0
  blob = unicodedata.normalize("NFKD", f"{title} {journal} {abstract}").encode("ascii", "ignore").decode("ascii").lower()
  if any(t in blob for t in OFFTOPIC_TERMS):
    return 0
  geo_hits = sum(1 for g in cfg["pos_geo"] if re.search(r"\b" + re.escape(g), blob))
  top_hits = sum(1 for t in cfg["pos_topic"] if t in blob)
  if geo_hits == 0 or top_hits == 0:
    return 0
  title_geo = sum(1 for g in cfg["pos_geo"] if re.search(r"\b" + re.escape(g), tl))
  title_top = sum(1 for t in cfg["pos_topic"] if t in tl)
  if title_geo == 0 and title_top == 0:
    return 0
  if stem == "falklands_south_atlantic" and title_geo == 0:
    return 0
  return title_geo * 5 + geo_hits * 3 + top_hits * 2


def search_crossref_and_unpaywall(title_q, broad_q, rows=16):
  out = []
  try:
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode({
        "query.title": title_q,
        "query": broad_q,
        "rows": str(rows),
        "mailto": "research@confoederatio.org",
    })
    r = requests.get(url, headers=API_HEADERS, timeout=18)
    if r.status_code != 200:
      return out
    items = (r.json().get("message") or {}).get("items") or []
  except Exception:
    return out

  def enrich(it):
    titles = it.get("title") or []
    title = clean_text(titles[0] if titles else "")
    if not title:
      return None
    yr = None
    for fld in ("published-print", "published-online", "issued"):
      dp = (it.get(fld) or {}).get("date-parts") or []
      if dp and dp[0] and isinstance(dp[0][0], int):
        yr = dp[0][0]
        break
    if not yr or not (1810 <= yr <= 2026):
      return None
    auths = []
    for a in (it.get("author") or [])[:6]:
      fam = clean_text(a.get("family"))
      giv = clean_text(a.get("given"))
      if fam:
        auths.append(f"{giv} {fam}".strip())
    if not auths:
      return None
    doi = clean_text(it.get("DOI") or "")
    if not doi:
      return None
    c_titles = it.get("container-title") or []
    journal = clean_text(c_titles[0] if c_titles else (it.get("publisher") or "Crossref"))
    u_main = f"https://doi.org/{doi}"
    if is_banned(title, auths, u_main, journal):
      return None

    pdf_urls = []
    land_urls = []
    for l in (it.get("link") or []):
      lu = l.get("URL") or ""
      if lu.startswith("http") and not any(bh in lu.lower() for bh in BANNED_HOSTS):
        if "pdf" in str(l.get("content-type", "")).lower() or lu.lower().endswith(".pdf"):
          pdf_urls.append(lu)
        else:
          land_urls.append(lu)

    try:
      ru = requests.get(
          f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email=research@confoederatio.org",
          headers=API_HEADERS,
          timeout=10,
      )
      if ru.status_code == 200:
        ju = ru.json()
        if ju.get("is_oa"):
          best = ju.get("best_oa_location") or {}
          if best.get("url_for_pdf"):
            pdf_urls.insert(0, best["url_for_pdf"])
          if best.get("url_for_landing_page"):
            land_urls.insert(0, best["url_for_landing_page"])
          for loc in (ju.get("oa_locations") or [])[:4]:
            if loc.get("url_for_pdf"):
              pdf_urls.append(loc["url_for_pdf"])
            if loc.get("url_for_landing_page"):
              land_urls.append(loc["url_for_landing_page"])
    except Exception:
      pass

    pdf_urls = [u for u in dict.fromkeys(pdf_urls) if u.startswith("http") and not any(bh in u.lower() for bh in BANNED_HOSTS)]
    land_urls = [u for u in dict.fromkeys(land_urls) if u.startswith("http") and not any(bh in u.lower() for bh in BANNED_HOSTS)]
    primary_pdf = pdf_urls[0] if pdf_urls else (land_urls[0] if land_urls else "")
    if primary_pdf and is_banned(title, auths, primary_pdf, journal):
      return None
    return {
        "title": title,
        "authors": auths,
        "year": int(yr),
        "journal_or_publisher": journal,
        "publisher_domain": norm_domain(primary_pdf) if primary_pdf else norm_domain(it.get("URL") or u_main),
        "doi": doi,
        "url": u_main,
        "pdf_url": primary_pdf,
        "alt_pdf_urls": pdf_urls[1:3] + land_urls[:2],
        "cited_by": int(it.get("is-referenced-by-count") or 0),
        "source_api": "crossref_unpaywall",
        "abstract": clean_text(it.get("abstract") or "")[:400],
        "bib_type": "article" if it.get("type") == "journal-article" else "book",
    }

  with ThreadPoolExecutor(max_workers=4) as ex:
    for res in ex.map(enrich, items):
      if res:
        out.append(res)
  return out


def search_doaj(q, page_size=40):
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
          doi = ident["id"].strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
          break
      links = [l.get("url") for l in (bj.get("link") or []) if l.get("url") and l.get("url").startswith("http")]
      links = [u for u in links if not any(bh in u.lower() for bh in BANNED_HOSTS)]
      if not links:
        continue
      ft_url = links[0]
      dom = norm_domain(ft_url)
      journal = clean_text((bj.get("journal") or {}).get("title") or dom)
      if is_banned(title, auths, ft_url, journal):
        continue
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
          "alt_pdf_urls": links[1:3],
          "cited_by": 5,
          "source_api": "doaj",
          "abstract": clean_text(bj.get("abstract") or "")[:400],
          "bib_type": "article",
      })
  except Exception:
    pass
  return out


def search_plos(q, rows=8):
  url = "https://api.plos.org/search?" + urllib.parse.urlencode({
      "q": q,
      "fl": "id,title_display,journal,publication_date,author_display",
      "rows": str(rows),
      "wt": "json",
  })
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=16)
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
          "abstract": "",
          "bib_type": "article",
      })
  except Exception:
    pass
  return out


def search_hal(q, rows=20):
  url = "https://api.archives-ouvertes.fr/search/?" + urllib.parse.urlencode({
      "q": q,
      "fq": "submitType_s:file",
      "fl": "docid,title_s,authFullName_s,producedDateY_i,doiId_s,uri_s,fileMain_s,journalTitle_s",
      "rows": str(rows),
      "wt": "json",
  })
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=16)
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
          "cited_by": 6,
          "source_api": "hal",
          "abstract": "",
          "bib_type": "article",
      })
  except Exception:
    pass
  return out


def search_dspace7(base_url, publisher_label, publisher_dom, q, size=18):
  url = f"{base_url}/server/api/discover/search/objects?" + urllib.parse.urlencode({
      "query": q,
      "size": str(size),
  })
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=18)
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
        auths = [publisher_label]
      handle = ""
      for u_ent in (md.get("dc.identifier.uri") or []):
        if u_ent.get("value"):
          handle = u_ent["value"]
          break
      bl = (it.get("_links") or {}).get("bundles", {}).get("href")
      if not bl:
        continue
      abs_parts = []
      for fld in ("dc.description.abstract", "dc.coverage.spatial", "dc.subject"):
        for v in (md.get(fld) or [])[:3]:
          if v.get("value"):
            abs_parts.append(clean_text(v["value"]))
      abstract = " ".join(abs_parts)[:400]
      if is_banned(title, auths, handle or bl, publisher_label):
        continue
      out.append({
          "title": title,
          "authors": auths,
          "year": yr,
          "journal_or_publisher": publisher_label,
          "publisher_domain": publisher_dom,
          "doi": "",
          "url": handle or f"{base_url}/entities/publication/{it.get('uuid')}",
          "pdf_url": bl,
          "alt_pdf_urls": [],
          "cited_by": 12,
          "source_api": publisher_dom,
          "is_dspace_bundles": True,
          "abstract": abstract,
          "bib_type": "techreport",
      })
  except Exception:
    pass
  return out


def search_nora(q, max_rows=15):
  url = "https://nora.nerc.ac.uk/cgi/search/simple?" + urllib.parse.urlencode({
      "q": q,
      "_action_search": "1",
      "output": "JSON",
  })
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=18)
    if r.status_code != 200:
      return out
    items = r.json()
    if not isinstance(items, list):
      return out
    for it in items[:max_rows]:
      title = clean_text(it.get("title"))
      yr_m = re.search(r"(\d{4})", str(it.get("date") or ""))
      if not (title and yr_m):
        continue
      yr = int(yr_m.group(1))
      auths = []
      for c in (it.get("creators") or [])[:6]:
        nm = c.get("name") or {}
        fam = clean_text(nm.get("family"))
        giv = clean_text(nm.get("given"))
        if fam:
          auths.append(f"{giv} {fam}".strip())
      if not auths:
        continue
      pdfs = []
      for doc in (it.get("documents") or []):
        for f in (doc.get("files") or []):
          fu = f.get("uri") or ""
          if fu.lower().endswith(".pdf"):
            pdfs.append(fu)
      if not pdfs:
        continue
      doi = clean_text(it.get("id_number") or "")
      if not doi.startswith("10."):
        doi = ""
      journal = clean_text(it.get("publication") or it.get("publisher") or "NERC Open Research Archive")
      if is_banned(title, auths, pdfs[0], journal):
        continue
      out.append({
          "title": title,
          "authors": auths,
          "year": yr,
          "journal_or_publisher": journal,
          "publisher_domain": "nora.nerc.ac.uk",
          "doi": doi,
          "url": f"https://doi.org/{doi}" if doi else (it.get("uri") or pdfs[0]),
          "pdf_url": pdfs[0],
          "alt_pdf_urls": pdfs[1:2],
          "cited_by": 8,
          "source_api": "nora",
          "abstract": clean_text(it.get("abstract") or "")[:400],
          "bib_type": "article",
      })
  except Exception:
    pass
  return out


def search_internet_archive(q, rows=10):
  url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode({
      "q": f"({q}) AND mediatype:texts AND format:pdf",
      "fl[]": ["identifier", "title", "year", "creator", "publisher"],
      "rows": str(rows),
      "output": "json",
  }, doseq=True)
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=16)
    if r.status_code != 200:
      return out
    for d in ((r.json().get("response") or {}).get("docs") or []):
      ident = d.get("identifier") or ""
      title = clean_text(d.get("title") or "")
      yr_m = re.search(r"(\d{4})", str(d.get("year") or ""))
      if not (ident and title and yr_m):
        continue
      yr = int(yr_m.group(1))
      if not (1810 <= yr <= 2026):
        continue
      cr = d.get("creator")
      if isinstance(cr, list):
        auths = [clean_text(x) for x in cr if x][:4]
      elif isinstance(cr, str) and cr.strip():
        auths = [clean_text(cr)]
      else:
        auths = ["Internet Archive Historical Collection"]
      pub = clean_text(d.get("publisher") or "Internet Archive")
      if is_banned(title, auths, f"https://archive.org/details/{ident}", pub):
        continue
      out.append({
          "title": title,
          "authors": auths,
          "year": yr,
          "journal_or_publisher": pub,
          "publisher_domain": "archive.org",
          "doi": "",
          "url": f"https://archive.org/details/{ident}",
          "pdf_url": f"https://archive.org/download/{ident}/{ident}.pdf",
          "alt_pdf_urls": [],
          "cited_by": 5,
          "source_api": "archive_org",
          "abstract": "",
          "bib_type": "book",
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
    cl = r.headers.get("Content-Length")
    if cl and cl.isdigit() and int(cl) > MAX_BYTES:
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
  if not cand.get("pdf_url") and not cand.get("alt_pdf_urls"):
    return None
  if cand.get("is_dspace_bundles"):
    try:
      b = requests.get(cand["pdf_url"], headers=API_HEADERS, timeout=14).json()
      pdf_link = None
      for bnd in (b.get("_embedded") or {}).get("bundles") or []:
        if bnd.get("name") == "ORIGINAL":
          bs = requests.get(bnd["_links"]["bitstreams"]["href"], headers=API_HEADERS, timeout=14).json()
          for bit in (bs.get("_embedded") or {}).get("bitstreams") or []:
            nm = str(bit.get("name") or "").lower()
            if nm.endswith(".pdf"):
              pdf_link = bit["_links"]["content"]["href"]
              break
      if not pdf_link:
        return None
      data, _, final_u = fetch_url_bytes(pdf_link, timeout=24)
      pages = validate_pdf_bytes(data)
      if pages:
        c2 = dict(cand)
        c2["pdf_url"] = final_u
        c2.pop("is_dspace_bundles", None)
        return (c2, data, pages, final_u)
    except Exception:
      return None
    return None

  urls_to_try = [cand["pdf_url"]] + list(cand.get("alt_pdf_urls") or [])
  for u in urls_to_try:
    if not u or any(bh in u.lower() for bh in BANNED_HOSTS):
      continue
    data, ct, final_u = fetch_url_bytes(u, timeout=22)
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
  a_slug = first_author_surname(authors)[:14] or "author"
  stop = {
      "the", "of", "and", "in", "to", "a", "an", "for", "on", "de", "la",
      "el", "en", "los", "las", "del", "y", "le", "les", "des", "du", "un",
      "una", "por", "para", "con", "su", "sus", "al",
  }
  words = [w for w in ascii_slug(title).split("_") if w and w not in stop]
  t_slug = "_".join(words)[:34].strip("_") or "study"
  rel_dir = os.path.relpath(pdir, SVEA_ROOT).replace("\\", "/")
  max_fn = min(MAX_FILENAME_LEN, MAX_RELPATH_LEN - len(rel_dir) - 1)
  base = f"{a_slug}_{year}_{t_slug}"
  fn = f"{base[:max_fn - 4]}.pdf".replace("__", "_").strip("_")
  if os.path.exists(os.path.join(pdir, fn)):
    fn = f"{base[:max_fn - 11]}_{h6}.pdf"
  return fn


def escape_bib(s):
  txt = clean_text(s)
  txt = txt.replace("\\", "").replace("{", "").replace("}", "")
  txt = txt.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#").replace("_", r"\_")
  return txt


def make_bib_key(authors, year, title, used_keys):
  sur = first_author_surname(authors)
  sur_cap = re.sub(r"[^a-zA-Z0-9]", "", sur).capitalize() or "Author"
  stop = {"the", "of", "and", "in", "a", "an", "de", "la", "el", "en", "los", "las", "on", "for"}
  words = [w for w in ascii_slug(title).split("_") if w and w not in stop and len(w) >= 3]
  w_cap = (words[0].capitalize() if words else "Study")[:14]
  base = f"{sur_cap}{year}{w_cap}"
  key = base
  idx = 2
  while key in used_keys:
    key = f"{base}{chr(96 + idx)}" if idx <= 26 else f"{base}_{idx}"
    idx += 1
  used_keys.add(key)
  return key


def format_authors_bib(authors):
  cleaned = []
  for a in (authors or ["Unknown"]):
    c = escape_bib(a)
    if c:
      if any(k in c.lower() for k in ("instituto", "departamento", "oficina", "comision", "government", "falkland", "cepal", "gsgssi", "biblioteca", "collection", "archive")):
        cleaned.append("{" + c + "}")
      else:
        cleaned.append(c)
  return " and ".join(cleaned[:6]) if cleaned else "{Unknown}"


def write_chapter_bib(ch_dir, stem, pdf_recs, extra_bib_cands):
  bib_path = os.path.join(ch_dir, f"{stem}_literature_review.bib")
  used_keys = set()
  entries = []
  pub_counts = {}
  auth_counts = {}
  seen_titles = set()
  seen_urls = set()

  def can_add(rec, is_downloaded=False):
    tk = ascii_slug(rec.get("title", ""))[:60]
    u = rec.get("url") or ""
    if not tk or (not is_downloaded and tk in seen_titles) or (not is_downloaded and u in seen_urls):
      return False
    doi = str(rec.get("doi") or "").strip()
    if not doi.startswith("10.") and not u.startswith("http"):
      return False
    pub_key = clean_text(rec.get("journal_or_publisher") or norm_domain(u)).lower()[:40]
    au_key = first_author_surname(rec.get("authors") or [])
    if not is_downloaded:
      if pub_counts.get(pub_key, 0) >= 3:
        return False
      if auth_counts.get(au_key, 0) >= 2:
        return False
    return True

  def add_entry(rec, is_downloaded=False):
    seen_titles.add(ascii_slug(rec.get("title", ""))[:60])
    u = rec.get("url") or ""
    if u:
      seen_urls.add(u)
    pub_raw = clean_text(rec.get("journal_or_publisher") or norm_domain(u))
    pub_key = pub_raw.lower()[:40]
    au_key = first_author_surname(rec.get("authors") or [])
    pub_counts[pub_key] = pub_counts.get(pub_key, 0) + 1
    auth_counts[au_key] = auth_counts.get(au_key, 0) + 1

    key = make_bib_key(rec.get("authors") or [], rec.get("year") or 2000, rec.get("title") or "", used_keys)
    btype = rec.get("bib_type") or "article"
    if btype not in ("article", "book", "techreport", "incollection", "misc"):
      btype = "article"

    lines = [f"@{btype}{{{key},"]
    lines.append(f"  author = {{{format_authors_bib(rec.get('authors'))}}},")
    lines.append(f"  title = {{{{{escape_bib(rec.get('title'))}}}}},")
    if btype == "article":
      lines.append(f"  journal = {{{escape_bib(pub_raw)}}},")
    elif btype == "techreport":
      lines.append(f"  institution = {{{escape_bib(pub_raw)}}},")
    else:
      lines.append(f"  publisher = {{{escape_bib(pub_raw)}}},")
    lines.append(f"  year = {{{int(rec.get('year') or 2000)}}},")
    doi = str(rec.get("doi") or "").strip()
    if doi.startswith("10."):
      lines.append(f"  doi = {{{doi}}},")
    if u.startswith("http"):
      u_https = u.replace("http://", "https://", 1) if u.startswith("http://www.memoriachilena") or u.startswith("http://www.ine.gob.cl") else u
      lines.append(f"  url = {{{u_https}}},")
    if is_downloaded and rec.get("filename"):
      lines.append(f"  note = {{Archival PDF: papers/{rec['filename']}}},")
    lines.append("}")
    entries.append("\n".join(lines))

  for r in pdf_recs:
    if can_add(r, is_downloaded=True):
      add_entry(r, is_downloaded=True)

  for c in extra_bib_cands:
    if len(entries) >= TARGET_BIB_KEYS:
      break
    if can_add(c, is_downloaded=False):
      add_entry(c, is_downloaded=False)

  with open(bib_path, "w", encoding="utf-8") as fh:
    fh.write("\n\n".join(entries) + "\n")

  return bib_path, len(entries)


def purge_offtopic():
  removed = 0
  for ch in CHAPTERS:
    stem = ch["stem"]
    pdir = os.path.join(POST_IND_DIR, ch["folder"], "papers")
    meta_p = os.path.join(pdir, "papers_metadata.json")
    if not os.path.isfile(meta_p):
      continue
    recs = json.load(open(meta_p, encoding="utf-8"))
    kept = []
    for r in recs:
      title = r.get("title", "")
      journal = r.get("journal_or_publisher", "")
      url = r.get("pdf_url") or r.get("url") or ""
      bad = is_banned(title, r.get("authors"), url, journal) or relevance_score(stem, title, journal) == 0
      # Also purge dengue epidemiology paper in Colombia so all 18 are pure demo/urban/census
      if "dengue" in title.lower():
        bad = True
      if bad:
        fp = os.path.join(pdir, r.get("filename", ""))
        if os.path.isfile(fp):
          os.remove(fp)
        removed += 1
        print(f"  [PURGE {stem}] {r.get('filename')} | {title[:65]}", flush=True)
      else:
        r["title"] = clean_text(r.get("title", ""))
        d_raw = str(r.get("doi") or "").strip()
        if d_raw:
          r["doi"] = d_raw.replace("https://doi.org/", "").replace("http://doi.org/", "")
        u_raw = str(r.get("url") or "").strip()
        if "https://doi.org/https://doi.org/" in u_raw:
          r["url"] = u_raw.replace("https://doi.org/https://doi.org/", "https://doi.org/")
        kept.append(r)
    with open(meta_p, "w", encoding="utf-8") as fh:
      json.dump(kept, fh, indent=2, ensure_ascii=False)
  print(f"[PURGE DONE] Removed {removed} off-topic PDF(s).", flush=True)


def harvest_chapter(ch, global_hashes):
  stem = ch["stem"]
  ch_dir = os.path.join(POST_IND_DIR, ch["folder"])
  pdir = os.path.join(ch_dir, "papers")
  os.makedirs(pdir, exist_ok=True)
  meta_p = os.path.join(pdir, "papers_metadata.json")
  existing = json.load(open(meta_p, encoding="utf-8")) if os.path.isfile(meta_p) else []

  valid_existing = []
  dom_used = {}
  auth_used = {}
  seen_titles = set()
  seen_urls = set()
  for rec in existing:
    fp = os.path.join(pdir, rec.get("filename", ""))
    if os.path.isfile(fp) and os.path.getsize(fp) >= MIN_BYTES:
      data = open(fp, "rb").read()
      if validate_pdf_bytes(data):
        valid_existing.append(rec)
        d = rec.get("publisher_domain") or "unknown"
        dom_used[d] = dom_used.get(d, 0) + 1
        au = first_author_surname(rec.get("authors") or [])
        auth_used[au] = auth_used.get(au, 0) + 1
        seen_titles.add(ascii_slug(rec.get("title", ""))[:60])
        seen_urls.add(rec.get("url", ""))
        if rec.get("sha256"):
          global_hashes.add(rec["sha256"])

  cfg = CHAPTER_CONFIG[stem]
  pool = []
  seen_cand_keys = set(seen_titles)

  def add_cand(c, forced_score=None):
    tk = ascii_slug(c.get("title", ""))[:60]
    if not tk or tk in seen_cand_keys or c.get("url") in seen_urls:
      return
    if is_banned(c.get("title", ""), c.get("authors", []), c.get("pdf_url") or c.get("url", ""), c.get("journal_or_publisher", "")):
      return
    sc = forced_score if forced_score is not None else relevance_score(
        stem, c.get("title", ""), c.get("journal_or_publisher", ""), c.get("abstract", "")
    )
    if sc <= 0:
      return
    seen_cand_keys.add(tk)
    c2 = dict(c)
    c2["_score"] = sc
    pool.append(c2)

  for c in CURATED_DIRECT_PDFS.get(stem, []):
    add_cand(c, forced_score=60)

  for q in cfg["doaj"]:
    for c in search_doaj(q, page_size=40):
      add_cand(c)

  cr_pool = []
  for tq, bq in cfg["crossref"]:
    for c in search_crossref_and_unpaywall(tq, bq, rows=18):
      cr_pool.append(c)
      add_cand(c)

  for q in cfg["hal"]:
    for c in search_hal(q, rows=20):
      add_cand(c)

  for q in cfg["cepal"]:
    for c in search_dspace7("https://repositorio.cepal.org", "UN ECLAC / CEPAL-CELADE", "repositorio.cepal.org", q, size=18):
      add_cand(c, forced_score=max(14, relevance_score(stem, c.get("title", ""), c.get("journal_or_publisher", ""), c.get("abstract", ""))))

  for q in cfg["conicet"]:
    for c in search_dspace7("https://ri.conicet.gov.ar", "CONICET Digital", "ri.conicet.gov.ar", q, size=15):
      add_cand(c)

  for q in cfg.get("banrep", []):
    for c in search_dspace7("https://repositorio.banrep.gov.co", "Banco de la República de Colombia", "repositorio.banrep.gov.co", q, size=15):
      add_cand(c)

  for q in cfg["plos"]:
    for c in search_plos(q, rows=8):
      add_cand(c)

  for q in cfg.get("nora", []):
    for c in search_nora(q, max_rows=15):
      add_cand(c)

  for q in cfg.get("ia", []):
    for c in search_internet_archive(q, rows=10):
      add_cand(c)

  if len(valid_existing) < TARGET_PDFS:
    pdf_cands = [c for c in pool if c.get("pdf_url") or c.get("alt_pdf_urls")]
    by_dom = {}
    for c in pdf_cands:
      by_dom.setdefault(c["publisher_domain"], []).append(c)
    for dom in by_dom:
      by_dom[dom].sort(key=lambda x: (-x["_score"], -x.get("cited_by", 0), -x.get("year", 0)))

    dom_order = sorted(by_dom.keys(), key=lambda d: (dom_used.get(d, 0), -by_dom[d][0]["_score"]))
    ordered = []
    max_len = max((len(v) for v in by_dom.values()), default=0)
    for idx in range(min(max_len, 12)):
      for dom in dom_order:
        if idx < len(by_dom[dom]):
          ordered.append(by_dom[dom][idx])

    need = TARGET_PDFS - len(valid_existing)
    added = 0
    pos = 0
    while added < need and pos < len(ordered) and pos < 220:
      batch = []
      while len(batch) < 16 and pos < len(ordered):
        c = ordered[pos]
        pos += 1
        d_cap = 3 if len(dom_used) < 7 else 4
        au = first_author_surname(c.get("authors") or [])
        if dom_used.get(c["publisher_domain"], 0) >= d_cap:
          continue
        if auth_used.get(au, 0) >= 3:
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
          au = first_author_surname(cand.get("authors") or [])
          d_cap = 3 if len(dom_used) < 7 else 4
          if dom_used.get(dom, 0) >= d_cap or auth_used.get(au, 0) >= 3:
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
              "chapter_folder": f"3.post_independence/{ch['folder']}",
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
              "jurisdiction": ch["jurisdiction"],
              "source_api": cand.get("source_api", "direct"),
              "bib_type": cand.get("bib_type", "article"),
          }
          valid_existing.append(rec)
          dom_used[dom] = dom_used.get(dom, 0) + 1
          auth_used[au] = auth_used.get(au, 0) + 1
          added += 1

  with open(meta_p, "w", encoding="utf-8") as fh:
    json.dump(valid_existing, fh, indent=2, ensure_ascii=False)

  filtered_extra = []
  for c in CURATED_CANONICAL_BIB.get(stem, []):
    c2 = dict(c)
    c2["_score"] = 60
    filtered_extra.append(c2)
  for c in pool + cr_pool:
    sc = c.get("_score") or relevance_score(stem, c.get("title", ""), c.get("journal_or_publisher", ""), c.get("abstract", ""))
    if sc > 0 and not is_banned(c.get("title", ""), c.get("authors", []), c.get("url", ""), c.get("journal_or_publisher", "")):
      c2 = dict(c)
      c2["_score"] = sc
      filtered_extra.append(c2)
  filtered_extra.sort(key=lambda x: (-x["_score"], -x.get("cited_by", 0), -x.get("year", 0)))

  bib_path, bib_count = write_chapter_bib(ch_dir, stem, valid_existing, filtered_extra)

  print(
      f"  [CH {ch['index']:02d}] {stem:32s}: {len(valid_existing):2d} PDFs | "
      f"{len(dom_used):2d} domains | {bib_count:2d} bib keys",
      flush=True,
  )
  return valid_existing, bib_path, bib_count


def main():
  if "--purge-offtopic" in sys.argv:
    purge_offtopic()

  global_hashes = set()
  for root, _, files in os.walk(QUIPU_DIR):
    if os.path.basename(root) == "papers":
      for fn in files:
        if fn.lower().endswith(".pdf"):
          fp = os.path.join(root, fn)
          try:
            data = open(fp, "rb").read()
            if len(data) >= MIN_BYTES and data.startswith(b"%PDF-"):
              global_hashes.add(hashlib.sha256(data).hexdigest())
          except Exception:
            pass

  t0 = time.time()
  print("[START] Harvesting QUIPU Stage C Wave 2 Part 2 (Chapters 9-17)...", flush=True)
  summary_chapters = {}

  for ch in CHAPTERS:
    recs, bib_path, bib_count = harvest_chapter(ch, global_hashes)
    dom_counts = {}
    for r in recs:
      d = r["publisher_domain"]
      dom_counts[d] = dom_counts.get(d, 0) + 1
    zen_cnt = sum(1 for r in recs if "zenodo" in r["publisher_domain"].lower() or "zenodo" in r.get("url", "").lower())
    summary_chapters[ch["stem"]] = {
        "chapter_index": ch["index"],
        "chapter_folder": f"3.post_independence/{ch['folder']}",
        "pdf_count": len(recs),
        "sha256_unique_count": len({r["sha256"] for r in recs}),
        "sha256_all_unique": len(recs) == len({r["sha256"] for r in recs}),
        "min_pdf_bytes": min((r["bytes"] for r in recs), default=0),
        "max_filename_len": max((len(r["filename"]) for r in recs), default=0),
        "max_rel_path_len": max((len(r["rel_path"]) for r in recs), default=0),
        "bib_file": os.path.relpath(bib_path, SVEA_ROOT).replace("\\", "/"),
        "bib_key_count": bib_count,
        "publisher_domain_count": len(dom_counts),
        "domains": dom_counts,
        "max_domain_share": round(max(dom_counts.values()) / len(recs), 4) if recs else 0.0,
        "zenodo_count": zen_cnt,
        "zenodo_share": round(zen_cnt / len(recs), 4) if recs else 0.0,
    }

  out = {
      "project": "QUIPU",
      "part": "part2_post_independence_ch9_to_ch17",
      "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
      "total_chapters": len(CHAPTERS),
      "total_pdfs": sum(v["pdf_count"] for v in summary_chapters.values()),
      "total_bib_keys": sum(v["bib_key_count"] for v in summary_chapters.values()),
      "min_chapter_pdfs": min((v["pdf_count"] for v in summary_chapters.values()), default=0),
      "min_chapter_bib_keys": min((v["bib_key_count"] for v in summary_chapters.values()), default=0),
      "min_chapter_domains": min((v["publisher_domain_count"] for v in summary_chapters.values()), default=0),
      "max_zenodo_share": max((v["zenodo_share"] for v in summary_chapters.values()), default=0.0),
      "chapters": summary_chapters,
  }
  with open(SUMMARY_PATH, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2, ensure_ascii=False)

  elapsed = time.time() - t0
  print(
      f"\n[DONE] {out['total_pdfs']} PDFs | {out['total_bib_keys']} bib keys across 9 chapters in {elapsed:.1f}s "
      f"(min_pdfs={out['min_chapter_pdfs']}, min_bib={out['min_chapter_bib_keys']}, min_domains={out['min_chapter_domains']})",
      flush=True,
  )


if __name__ == "__main__":
  main()
