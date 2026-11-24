"""Stage C Wave 2 Part 3: Precision Lucene/Title-Scoped Top-Up + Gatekeeper D3 Audit for Project JAGUAR.

Tops up the remaining chapters below 17 PDFs (Ch 03, 06, 07, 08, 09, 12, 13)
using zero-rate-limit, high-precision title-scoped scholarly APIs:
  1. DOAJ Lucene `bibjson.title:` queries (UNAM, COLMEX, UCR, SciELO, Caribbean & European OA journals)
  2. HAL Archives Ouvertes `title_t:` queries (CNRS / CEMCA / French Antilles & Mesoamerican studies)
  3. Crossref `query.title=` with full-text PDF resolution (open-access university presses & journals)
  4. PLOS `title:` queries
  5. CEPAL/CELADE & World Bank Open Knowledge Repository (DSpace 7)
  6. Demographic Research (MPIDR) & US Census Bureau official PDFs

Then runs a comprehensive Gatekeeper D3 verification across all 14 chapters and
writes the final `JAGUAR/_shared/wave2_papers_manifest.json`.
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
    "(OperationViscount-JAGUAR-Harvester/3.0; mailto:research@confoederatio.org)"
  ),
  "Accept": "application/pdf,text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}
API_HEADERS = {
  "User-Agent": "OperationViscount-JAGUAR-Harvester/3.0 (mailto:research@confoederatio.org)"
}

TARGET_PER_CHAPTER = 17
MIN_BYTES = 12288
MAX_BYTES = 28 * 1024 * 1024
MAX_WORKERS = 4
MAX_FILENAME_LEN = 68
MAX_RELPATH_LEN = 176

BANNED_AUTHORS = (
  "mcevedy", "colin mcevedy", "richard jones", "klein goldewijk", "goldewijk",
  "maddison", "angus maddison", "tertius chandler", "chandler, tertius",
  "modelski", "george modelski", "populstat",
)
BANNED_TITLE_PHRASES = (
  "hyde 3", "hyde 2", "populstat", "maddison project",
  "atlas of world population history", "four thousand years of urban growth",
  "world cities: -3000 to 2000", "azteca ant", "azteca ants", "cecropia",
  "siluriformes", "auchenipter", "crustaceo", "chironomidae", "k-ras",
  "binaural beat", "voltaic battery", "informe de ejecucion", "programa bienal",
  "comercio de bienes", "grupos de trabajo",
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
  "porcine", "equine", "new species", "phylogeny", "taxonomy", "taxonomic",
  "butterfly", "beetle", "ant ", "ants ", "cecropia", "dolphin", "whale",
  "turtle", "manatee", "bird", "avian", "fish", "coral", "shark", "sponge",
  "orchid", "cactus", "fungus", "fungi", "bacteria", "microbiome",
  "clinical trial", "randomized", "alzheimer", "parkinson", "cancer",
  "leukemia", "schizophrenia", "pesticide", "wastewater", "photovoltaic",
  "solar cell", "concrete", "asphalt", "polymer", "nanoparticle", "catalysis",
  "quantum", "seismology", "covid-19", "sars-cov-2", "monkeypox", "zika",
  "dengue", "aedes", "anopheles", "mangrove", "seagrass", "phytoplankton",
  "zooplankton", "benthic", "dinosaur", "cretaceous", "jurassic", "miocene",
  "buenos aires", "arica", "peru", "chile", "bolivia", "argentina",
  "colombia", "venezuela", "ecuador", "brazil", "brasil", "uruguay", "paraguay",
  "tunisia", "nigeria", "kenya", "india", "china", "taiwan", "nordic",
  "clausulas relativas", "phonology", "syntax", "morphosyntax", "bancarizacion",
  "diabetes", "hypertension", "obesity", "asthma", "epilepsy", "dental caries",
  "orthodontic", "ophthalmolog", "dermatolog", "radiology", "nursing",
  "tourism", "hotel", "football", "soccer", "baseball", "music", "cinema",
  "novel ", "poetry", "literature", "literatura",
)

PART3_SPEC = {
  "aztec_late_postclassic_mexico": {
    "doaj_lucene": [
      'bibjson.title:((Tenochtitlan OR Mexica OR Aztec OR Azteca) AND (archaeology OR arqueologia OR urban OR ciudad OR empire OR imperio OR tributo OR tribute OR poblacion OR population OR chinampa OR historia OR history OR asentamiento OR settlement OR agricultura OR mercado OR calpulli OR altepetl OR templos OR excavacion))',
      'bibjson.title:((Purepecha OR Tarascan OR Tarasco OR Michoacan OR Mixtec OR Mixteca OR Tlaxcala OR Texcoco OR Chalco OR Xochimilco OR Morelos) AND (arqueologia OR archaeology OR posclasico OR postclassic OR prehispanico OR prehispanic OR poblacion OR asentamiento OR settlement OR ciudad OR urban))',
      'bibjson.title:((Mesoamerica OR "Cuenca de Mexico" OR "Basin of Mexico" OR Nahua) AND (posclasico OR postclassic OR chinampa OR urbanismo OR urbanism OR poblacion OR demografia OR asentamiento))',
    ],
    "hal": [
      'title_t:(Tenochtitlan OR Mexica OR Azteque OR Tarasque OR Purepecha OR Mixteque)',
      'title_t:(Mexique AND (prehispanique OR postclassique OR archeologie))',
    ],
    "crossref": [
      "Aztec Tenochtitlan urbanism population Basin of Mexico",
      "Postclassic Central Mexico Aztec household archaeology Morelos",
      "Tarascan Purepecha Tzintzuntzan Michoacan archaeology",
      "Mixtec Postclassic Oaxaca archaeology settlement",
      "Aztec empire chinampa agriculture population",
    ],
    "plos": [
      'title:"Aztec" OR title:"Tenochtitlan" OR title:"Mexica" OR title:"Purepecha" OR title:"Postclassic"',
    ],
    "cepal": [],
    "worldbank": [],
    "pos_geo": ("aztec", "azteca", "mexica", "tenochtitlan", "texcoco", "tlaxcala", "basin of mexico", "cuenca de mexico", "tarascan", "tarasco", "purepecha", "tzintzuntzan", "angamuco", "michoacan", "mixtec", "mixteca", "postclassic", "posclasico", "morelos", "chalco", "xochimilco", "tlatelolco", "nahua", "nahuatl", "central mexico", "mesoamerica", "mexique", "templo mayor"),
    "pos_topic": ("population", "poblacion", "demograph", "urban", "city", "ciudad", "settlement", "asentamiento", "empire", "imperio", "tribute", "tributo", "chinampa", "agricult", "household", "market", "mercado", "archaeolog", "arqueolog", "archeolog", "codex", "codice", "state", "polity", "altepetl", "ceramic", "obsidian", "architecture", "temple", "templo", "burial", "expansion", "conquest", "history", "historia", "econom", "territor", "prehispan"),
  },
  "conquest_collapse_mesoamerica": {
    "doaj_lucene": [
      'bibjson.title:((Mexico OR "Nueva Espana" OR "New Spain" OR Mesoamerica OR Guatemala OR Yucatan OR Oaxaca) AND (cocoliztli OR viruela OR smallpox OR epidemia OR epidemic OR "colapso demografico" OR "demographic collapse" OR despoblacion OR depopulation OR congregaciones OR "Relaciones Geograficas"))',
      'bibjson.title:((conquista OR conquest OR "siglo XVI" OR "sixteenth century") AND (Mexico OR "Nueva Espana" OR Mesoamerica OR Guatemala OR Yucatan OR Chiapas) AND (poblacion OR population OR mortalidad OR mortality OR indigena OR indigenous OR demografia OR demography OR tributo OR encomienda))',
    ],
    "hal": [
      'title_t:(("Nouvelle-Espagne" OR Mexique OR Mesoamerique) AND (XVIe OR conquete OR epidemie OR population))',
    ],
    "crossref": [
      "Cocoliztli 1545 1576 Mexico epidemic mortality",
      "Spanish conquest Mexico sixteenth century indigenous depopulation",
      "Congregaciones indigenous resettlement colonial Mexico sixteenth century",
      "Relaciones Geograficas sixteenth century New Spain population",
    ],
    "plos": [
      'title:"cocoliztli" OR (title:"colonial Mexico" AND (title:"epidemic" OR title:"population" OR title:"conquest"))',
    ],
    "cepal": [],
    "worldbank": [],
    "pos_geo": ("mexico", "new spain", "nueva espana", "mesoamerica", "guatemala", "central america", "yucatan", "oaxaca", "michoacan", "tlaxcala", "chiapas", "tenochtitlan", "teposcolula", "nahua", "maya", "aztec", "honduras", "nicaragua", "el salvador", "puebla", "veracruz", "nouvelle-espagne", "mexique"),
    "pos_topic": ("cocoliztli", "epidemic", "epidem", "smallpox", "viruela", "measles", "salmonella", "collapse", "colapso", "conquest", "conquista", "conquete", "depopulation", "despoblacion", "mortality", "mortalidad", "congregacion", "reduccion", "relaciones geograficas", "encomienda", "tribute", "tributo", "demograph", "demograf", "population", "poblacion", "sixteenth", "siglo xvi", "1519", "1520", "1545", "1576", "catastrofe", "disease", "enfermedad", "pestilence"),
  },
  "viceroyalty_of_new_spain": {
    "doaj_lucene": [
      'bibjson.title:(("Nueva Espana" OR "New Spain" OR "Mexico colonial" OR "colonial Mexico") AND (poblacion OR population OR demografia OR demography OR censo OR census OR padron OR parroquial OR parish OR mortalidad OR mortality OR epidemia OR matlazahuatl OR bautismo OR matrimonio OR defuncion))',
      'bibjson.title:((Revillagigedo OR Bajio OR Guanajuato OR Zacatecas OR Guadalajara OR Puebla OR Yucatan OR Oaxaca OR Michoacan) AND ("siglo XVIII" OR "siglo XVII" OR colonial OR "18th century" OR 1790) AND (poblacion OR population OR demografia OR censo OR padron OR mortalidad OR epidemia OR mineria OR indigena))',
    ],
    "hal": [
      'title_t:(("Nouvelle-Espagne" OR Mexique) AND (XVIIIe OR XVIIe OR colonial) AND (population OR demographie OR ville OR paroisse OR recensement))',
    ],
    "crossref": [
      "New Spain colonial Mexico eighteenth century population parish registers",
      "Revillagigedo census 1790 colonial Mexico population",
      "Colonial Mexico City eighteenth century mortality demography",
      "Matlazahuatl epidemic eighteenth century New Spain Mexico",
    ],
    "plos": [],
    "cepal": [],
    "worldbank": [],
    "pos_geo": ("new spain", "nueva espana", "nouvelle-espagne", "mexico", "mexique", "mexican", "bajio", "zacatecas", "guanajuato", "guadalajara", "puebla", "oaxaca", "yucatan", "veracruz", "michoacan", "san luis potosi", "durango", "sonora", "chihuahua", "tlaxcala", "queretaro", "jalisco", "nuevo leon", "campeche", "merida"),
    "pos_topic": ("colonial", "viceroyalty", "virreinato", "revillagigedo", "padron", "parish", "parroquial", "paroisse", "baptism", "bautismo", "burial", "defuncion", "marriage", "matrimonio", "census", "censo", "recensement", "demograph", "demograf", "population", "poblacion", "mortality", "mortalidad", "epidemic", "epidem", "matlazahuatl", "casta", "mestizo", "indigena", "silver", "mining", "mineria", "siglo xvii", "siglo xviii", "18th century", "17th century", "1790", "bourbon", "borbon"),
  },
  "captaincy_general_guatemala": {
    "doaj_lucene": [
      'bibjson.title:(("Reino de Guatemala" OR "Audiencia de Guatemala" OR "Capitania General" OR "Guatemala colonial" OR "Costa Rica colonial" OR "Nicaragua colonial" OR "Honduras colonial" OR "Panama colonial" OR "Centroamerica colonial") AND (poblacion OR population OR demografia OR tributo OR indigena OR epidemia OR mortalidad OR censo OR padron OR parroquia OR esclavitud OR historia))',
      'bibjson.title:((Guatemala OR "Costa Rica" OR Nicaragua OR Honduras OR "El Salvador" OR Panama OR Belice OR Belize OR Chiapas) AND ("siglo XVI" OR "siglo XVII" OR "siglo XVIII" OR colonial OR "18th century") AND (poblacion OR population OR demografia OR tributo OR encomienda OR indigena OR parroquia OR epidemia))',
    ],
    "hal": [
      'title_t:((Guatemala OR "Costa Rica" OR Nicaragua OR Honduras OR Panama OR "Amerique centrale") AND (colonial OR XVIIIe OR XVIIe OR XVIe))',
    ],
    "crossref": [
      "Colonial Guatemala population demography eighteenth century",
      "Colonial Costa Rica historical demography parish population",
      "Colonial Central America Nicaragua Honduras indigenous population",
      "Colonial Panama British Honduras Belize population history",
    ],
    "plos": [],
    "cepal": [],
    "worldbank": [],
    "pos_geo": ("guatemala", "central america", "centroamerica", "amerique centrale", "costa rica", "nicaragua", "honduras", "el salvador", "panama", "belize", "belice", "british honduras", "chiapas", "soconusco", "verapaz", "antigua", "cartago", "leon", "granada", "comayagua", "portobelo", "darien", "mosquitia", "reino de guatemala", "audiencia de guatemala"),
    "pos_topic": ("colonial", "demograph", "demograf", "population", "poblacion", "tribute", "tributo", "parish", "parroquial", "padron", "census", "censo", "encomienda", "repartimiento", "epidemic", "epidem", "mortalidad", "mortality", "indigenous", "indigena", "ladino", "mestizo", "mulato", "slavery", "esclavitud", "siglo xvi", "siglo xvii", "siglo xviii", "16th century", "17th century", "18th century", "audiencia", "capitania", "settlement", "migration", "migrar"),
  },
  "conquest_indigenous_caribbean": {
    "doaj_lucene": [
      'bibjson.title:((Taino OR Kalinago OR Carib OR Caribes OR Hispaniola OR "La Espanola" OR "Santo Domingo" OR Cuba OR "Puerto Rico" OR Jamaica OR Antillas OR Caribe) AND (conquista OR conquest OR encomienda OR despoblacion OR depopulation OR "siglo XVI" OR "sixteenth century" OR 1492 OR colapso OR indigena OR indigenous OR supervivencia OR survival OR ancestralidad OR ancestry))',
      'bibjson.title:((Caribbean OR Caribe OR "Puerto Rico" OR Cuba OR "Dominican Republic") AND (Taino OR Amerindian OR indigenous) AND (colonial OR conquest OR genetic OR ancestry OR demography OR population OR archaeology))',
    ],
    "hal": [
      'title_t:((Antilles OR Caraibes OR Kalinago OR Hispaniola OR Cuba OR Taino) AND (XVIe OR XVIIe OR conquete OR colonisation OR indiens OR population))',
    ],
    "crossref": [
      "Hispaniola Taino demographic collapse 1492 conquest",
      "Indigenous Caribbean Spanish conquest depopulation sixteenth century",
      "Taino survival ancestry Puerto Rico Dominican Republic Cuba",
      "Kalinago Carib Lesser Antilles colonial contact sixteenth century",
    ],
    "plos": [
      'title:"Taino" OR (title:"Caribbean" AND title:"indigenous" AND (title:"ancestry" OR title:"colonial" OR title:"conquest"))',
    ],
    "cepal": [],
    "worldbank": [],
    "pos_geo": ("hispaniola", "espanola", "santo domingo", "cuba", "puerto rico", "jamaica", "bahamas", "lucayan", "caribbean", "caribe", "caraibe", "antilles", "antillas", "taino", "kalinago", "carib", "dominica", "st vincent", "guadeloupe", "martinique", "trinidad", "barbados", "dominican republic", "west indies"),
    "pos_topic": ("conquest", "conquista", "conquete", "columbus", "colon", "1492", "collapse", "colapso", "depopulation", "despoblacion", "extinction", "extincion", "survival", "supervivencia", "encomienda", "epidemic", "smallpox", "population", "poblacion", "demograph", "demograf", "indigenous", "indigena", "indien", "ancestry", "ancestral", "admixture", "sixteenth", "siglo xvi", "xvie", "xviie", "colonial", "contact", "archaeolog", "amerindian"),
  },
  "central_american_republics": {
    "doaj_lucene": [
      'bibjson.title:((Guatemala OR "El Salvador" OR Honduras OR Nicaragua OR "Costa Rica" OR Panama OR Belize OR Belice OR Centroamerica) AND (fecundidad OR fertility OR mortalidad OR mortality OR "esperanza de vida" OR "life expectancy" OR envejecimiento OR aging OR ageing OR "transicion demografica" OR "demographic transition" OR censo OR census OR urbanizacion OR urbanization))',
      'bibjson.title:((Guatemala OR "El Salvador" OR Honduras OR Nicaragua OR "Costa Rica" OR Panama OR Centroamerica) AND (migracion OR migration OR emigracion OR emigration OR demografia OR demography OR "crecimiento poblacional" OR "population growth"))',
    ],
    "hal": [
      'title_t:((Guatemala OR "Costa Rica" OR Nicaragua OR Honduras OR Salvador OR Panama OR "Amerique centrale") AND (population OR demographie OR migration OR urbanisation OR fecondite OR mortalite))',
    ],
    "crossref": [
      "Costa Rica demographic transition mortality fertility longevity",
      "Guatemala fertility mortality population census demography",
      "El Salvador Honduras Nicaragua demographic transition migration",
      "Panama Belize population census urbanization demography",
    ],
    "plos": [
      '(title:"Guatemala" OR title:"Costa Rica" OR title:"Honduras" OR title:"Nicaragua" OR title:"El Salvador" OR title:"Panama" OR title:"Belize") AND (title:"mortality" OR title:"fertility" OR title:"population" OR title:"migration" OR title:"demographic")',
    ],
    "cepal": [
      "fecundidad mortalidad envejecimiento Centroamerica",
      "censo poblacion Guatemala Honduras Nicaragua El Salvador Costa Rica Panama",
    ],
    "worldbank": [
      "Central America urbanization population demographic Guatemala Honduras",
      "Costa Rica Panama El Salvador Nicaragua demographic aging population",
    ],
    "pos_geo": ("central america", "centroamerica", "amerique centrale", "guatemala", "el salvador", "salvador", "honduras", "nicaragua", "costa rica", "panama", "belize", "belice", "canal zone", "mesoamerica"),
    "pos_topic": ("population", "poblacion", "census", "censo", "recensement", "demograph", "demograf", "fertility", "fecundidad", "fecondite", "mortality", "mortalidad", "mortalite", "longevity", "life expectancy", "esperanza de vida", "urbanization", "urbanizacion", "urbanisation", "migration", "migracion", "emigration", "emigracion", "transition", "transicion", "aging", "ageing", "envejecimiento", "vieillissement", "birth", "natalidad", "household", "hogar"),
  },
  "greater_antilles_modern": {
    "doaj_lucene": [
      'bibjson.title:((Cuba OR "Puerto Rico" OR Jamaica OR Haiti OR "Republica Dominicana" OR "Dominican Republic") AND (envejecimiento OR aging OR ageing OR fecundidad OR fertility OR mortalidad OR mortality OR "esperanza de vida" OR "life expectancy" OR "transicion demografica" OR "demographic transition"))',
      'bibjson.title:((Cuba OR "Puerto Rico" OR Jamaica OR Haiti OR "Republica Dominicana" OR "Dominican Republic") AND (poblacion OR population OR demografia OR demography OR censo OR census OR migracion OR migration OR emigracion OR emigration OR urbanizacion OR urbanization))',
    ],
    "hal": [
      'title_t:((Haiti OR Cuba OR Jamaique OR "Porto Rico" OR "Republique dominicaine") AND (population OR demographie OR migration OR urbanisation OR fecondite OR mortalite OR recensement OR vieillissement))',
    ],
    "crossref": [
      "Cuba population aging fertility decline demographic transition",
      "Puerto Rico population decline migration census fertility",
      "Jamaica population census fertility mortality demographic transition",
      "Haiti population census fertility mortality demographic",
      "Dominican Republic population census fertility migration urbanization",
      "Greater Antilles Cuba Haiti Jamaica Puerto Rico demography",
    ],
    "plos": [
      '(title:"Puerto Rico" OR title:"Cuba" OR title:"Jamaica" OR title:"Haiti" OR title:"Dominican Republic") AND (title:"mortality" OR title:"fertility" OR title:"population" OR title:"migration" OR title:"demographic" OR title:"aging")',
    ],
    "cepal": [
      "envejecimiento fecundidad poblacion Cuba",
      "poblacion demografia migracion Republica Dominicana Haiti",
      "fecundidad mortalidad envejecimiento Jamaica Caribe",
    ],
    "worldbank": [
      "Haiti Dominican Republic Jamaica urbanization population demographic",
      "Jamaica Haiti demographic aging migration fertility",
    ],
    "pos_geo": ("cuba", "cuban", "cubano", "haiti", "haitian", "haitiano", "dominican republic", "republica dominicana", "republique dominicaine", "dominican", "jamaica", "jamaique", "jamaican", "puerto rico", "porto rico", "puerto rican", "greater antilles", "grandes antillas", "hispaniola", "havana", "habana", "kingston", "san juan", "port-au-prince"),
    "pos_topic": ("population", "poblacion", "census", "censo", "recensement", "demograph", "demograf", "fertility", "fecundidad", "fecondite", "mortality", "mortalidad", "mortalite", "aging", "ageing", "envejecimiento", "vieillissement", "life expectancy", "esperanza de vida", "migration", "migracion", "emigration", "emigracion", "urbanization", "urbanizacion", "urbanisation", "transition", "transicion", "growth", "decline", "household", "birth", "natalidad"),
  },
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
  cfg = PART3_SPEC[stem]
  tl = unicodedata.normalize("NFKD", f"{title} {journal}").encode("ascii", "ignore").decode("ascii").lower()
  geo_hits = sum(1 for g in cfg["pos_geo"] if g in tl)
  top_hits = sum(1 for t in cfg["pos_topic"] if t in tl)
  if geo_hits == 0 or top_hits == 0:
    return 0
  return geo_hits * 3 + top_hits * 2


def search_doaj_lucene(q, page_size=40):
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
        "alt_pdf_urls": links[1:2] + ([f"https://doi.org/{doi}"] if doi else []),
        "cited_by": 8,
        "source_api": "doaj",
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
        "cited_by": 8,
        "source_api": "hal",
      })
  except Exception:
    pass
  return out


def search_crossref(q, rows=20):
  url = "https://api.crossref.org/works?" + urllib.parse.urlencode({
    "query.title": q,
    "filter": "has-full-text:true",
    "rows": str(rows),
    "mailto": "research@confoederatio.org",
  })
  out = []
  try:
    r = requests.get(url, headers=API_HEADERS, timeout=20)
    if r.status_code != 200:
      return out
    for it in ((r.json().get("message") or {}).get("items") or []):
      titles = it.get("title") or []
      title = clean_text(titles[0]) if titles else ""
      if not title:
        continue
      yr = None
      for dk in ("published-print", "published-online", "issued", "created"):
        dp = ((it.get(dk) or {}).get("date-parts") or [[]])[0]
        if dp and dp[0]:
          yr = int(dp[0])
          break
      if not yr or not (1800 <= yr <= 2026):
        continue
      auths = []
      for a in (it.get("author") or [])[:6]:
        nm = clean_text(f"{a.get('given', '')} {a.get('family', '')}")
        if nm:
          auths.append(nm)
      if not auths:
        continue
      doi = clean_text(it.get("DOI") or "")
      links = []
      for l in (it.get("link") or []):
        lu = l.get("URL") or ""
        ct = str(l.get("content-type") or "").lower()
        if lu.startswith("http") and ("pdf" in ct or lu.lower().endswith(".pdf") or "unspecified" in ct):
          if not any(bh in lu.lower() for bh in BANNED_HOSTS):
            links.append(lu)
      doi_u = f"https://doi.org/{doi}" if doi else ""
      if not links and not doi_u:
        continue
      primary = links[0] if links else doi_u
      if is_banned(title, auths, primary):
        continue
      ct_list = it.get("container-title") or []
      journal = clean_text(ct_list[0] if ct_list else (it.get("publisher") or norm_domain(primary)))
      out.append({
        "title": title,
        "authors": auths,
        "year": yr,
        "journal_or_publisher": journal,
        "publisher_domain": norm_domain(primary),
        "doi": doi,
        "url": doi_u or primary,
        "pdf_url": primary,
        "alt_pdf_urls": links[1:2] + ([doi_u] if doi_u and doi_u != primary else []),
        "cited_by": int(it.get("is-referenced-by-count") or 0),
        "source_api": "crossref",
      })
  except Exception:
    pass
  return out


def search_plos(q, rows=15):
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


def search_dspace7(base_url, domain, publisher_name, q, size=12):
  url = f"{base_url}/server/api/discover/search/objects?" + urllib.parse.urlencode({
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
      auths = [clean_text(a.get("value")) for a in auth_entries if a.get("value")][:6] or [publisher_name]
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
        "journal_or_publisher": publisher_name,
        "publisher_domain": domain,
        "doi": "",
        "url": handle or f"{base_url}/entities/publication/{it.get('uuid')}",
        "pdf_url": bl,
        "alt_pdf_urls": [],
        "cited_by": 15,
        "source_api": domain.split(".")[0],
        "is_dspace_bundles": True,
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


def fetch_url_bytes(url, timeout=16):
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
  if cand.get("is_dspace_bundles"):
    try:
      b = requests.get(cand["pdf_url"], headers=API_HEADERS, timeout=14).json()
      pdf_link = None
      for bnd in (b.get("_embedded") or {}).get("bundles") or []:
        if bnd.get("name") == "ORIGINAL":
          bs = requests.get(bnd["_links"]["bitstreams"]["href"], headers=API_HEADERS, timeout=14).json()
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
        c2.pop("is_dspace_bundles", None)
        return (c2, data, pages, final_u)
    except Exception:
      return None
    return None

  for u in [cand["pdf_url"]] + list(cand.get("alt_pdf_urls") or []):
    if not u or any(bh in u.lower() for bh in BANNED_HOSTS):
      continue
    data, ct, final_u = fetch_url_bytes(u, timeout=16)
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
        d2, _, fu2 = fetch_url_bytes(pdf2, timeout=16)
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


def topup_chapter(ch, global_hashes):
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

  if stem not in PART3_SPEC:
    return valid_existing

  cfg = PART3_SPEC[stem]
  pool = []
  seen_cand_keys = set(seen_titles)

  def add_cand(c):
    tk = ascii_slug(c.get("title", ""))[:60]
    if not tk or tk in seen_cand_keys or c.get("url") in seen_urls:
      return
    if is_banned(c.get("title", ""), c.get("authors", []), c.get("pdf_url", "")):
      return
    sc = relevance_score(stem, c.get("title", ""), c.get("journal_or_publisher", ""))
    if sc <= 0:
      return
    seen_cand_keys.add(tk)
    c2 = dict(c)
    c2["_score"] = sc
    pool.append(c2)

  for q in cfg.get("doaj_lucene", []):
    for c in search_doaj_lucene(q, page_size=40):
      add_cand(c)
  for q in cfg.get("hal", []):
    for c in search_hal(q, rows=20):
      add_cand(c)
  for q in cfg.get("crossref", []):
    for c in search_crossref(q, rows=20):
      add_cand(c)
  for q in cfg.get("plos", []):
    for c in search_plos(q, rows=15):
      add_cand(c)
  for q in cfg.get("cepal", []):
    for c in search_dspace7("https://repositorio.cepal.org", "repositorio.cepal.org", "UN ECLAC / CEPAL-CELADE", q, size=12):
      add_cand(c)
  for q in cfg.get("worldbank", []):
    for c in search_dspace7("https://openknowledge.worldbank.org", "openknowledge.worldbank.org", "World Bank", q, size=10):
      add_cand(c)

  by_dom = {}
  for c in pool:
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

  need = max(0, TARGET_PER_CHAPTER - len(valid_existing))
  added = 0
  pos = 0
  jurisdiction = ", ".join(ch.get("jurisdictions") or [])

  while added < need and pos < len(ordered) and pos < 300:
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


def audit_and_write_manifest(itin):
  all_papers = []
  summary = {}
  seen_hashes = set()
  errors = []

  for ch in itin["chapters"]:
    stem = ch["stem"]
    rel_ch = os.path.join(ch["group"], ch["folder"])
    pdir = os.path.join(JAGUAR_DIR, rel_ch, "papers")
    meta_p = os.path.join(pdir, "papers_metadata.json")
    recs = json.load(open(meta_p, encoding="utf-8")) if os.path.isfile(meta_p) else []

    verified = []
    for rec in recs:
      fn = rec["filename"]
      fp = os.path.join(pdir, fn)
      if not os.path.isfile(fp):
        errors.append(f"Missing file: {fp}")
        continue
      data = open(fp, "rb").read()
      pages = validate_pdf_bytes(data)
      if not pages:
        errors.append(f"Invalid PDF: {fp}")
        continue
      h = hashlib.sha256(data).hexdigest()
      if h in seen_hashes:
        errors.append(f"Duplicate SHA-256: {fp}")
        continue
      seen_hashes.add(h)
      rel_path = os.path.relpath(fp, SVEA_ROOT).replace("\\", "/")
      if len(fn) > 72:
        errors.append(f"Filename > 72 chars ({len(fn)}): {fn}")
      if len(rel_path) > 180:
        errors.append(f"Relpath > 180 chars ({len(rel_path)}): {rel_path}")
      rec["sha256"] = h
      rec["bytes"] = len(data)
      rec["pages"] = pages
      rec["rel_path"] = rel_path
      verified.append(rec)

    doms = sorted({r["publisher_domain"] for r in verified})
    if len(verified) < 15:
      errors.append(f"Chapter {stem} has < 15 PDFs ({len(verified)})")
    if len(doms) < 5:
      errors.append(f"Chapter {stem} has < 5 distinct domains ({len(doms)})")

    summary[stem] = {
      "chapter_index": ch["index"],
      "chapter_folder": rel_ch.replace("\\", "/"),
      "pdf_count": len(verified),
      "distinct_domains": len(doms),
      "domains": doms,
      "total_bytes": sum(r["bytes"] for r in verified),
      "total_pages": sum(r["pages"] for r in verified),
    }
    all_papers.extend(verified)

  zenodo_count = sum(1 for r in all_papers if "zenodo" in r["publisher_domain"].lower())
  manifest = {
    "project": "JAGUAR",
    "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "total_chapters": len(itin["chapters"]),
    "total_papers": len(all_papers),
    "unique_sha256": len(seen_hashes),
    "min_chapter_pdfs": min((s["pdf_count"] for s in summary.values()), default=0),
    "min_chapter_domains": min((s["distinct_domains"] for s in summary.values()), default=0),
    "zenodo_count": zenodo_count,
    "audit_errors": errors,
    "chapters_summary": summary,
    "papers": all_papers,
  }
  with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2, ensure_ascii=False)

  print(f"\n[AUDIT] Total verified unique PDFs: {len(all_papers)} | min_pdfs={manifest['min_chapter_pdfs']} | min_domains={manifest['min_chapter_domains']} | zenodo={zenodo_count} | errors={len(errors)}", flush=True)
  for e in errors:
    print("  ERR:", e, flush=True)


def main():
  itin = load_itinerary()
  global_hashes = set()
  for ch in itin["chapters"]:
    pdir = os.path.join(JAGUAR_DIR, ch["group"], ch["folder"], "papers")
    for fn in os.listdir(pdir):
      if fn.lower().endswith(".pdf"):
        data = open(os.path.join(pdir, fn), "rb").read()
        if len(data) >= MIN_BYTES and data.startswith(b"%PDF-"):
          global_hashes.add(hashlib.sha256(data).hexdigest())

  t0 = time.time()
  print("[START] Pass 3 Title-Scoped Top-Up for remaining JAGUAR chapters...", flush=True)
  for ch in itin["chapters"]:
    topup_chapter(ch, global_hashes)

  audit_and_write_manifest(itin)
  print(f"[DONE] Elapsed: {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
  main()
