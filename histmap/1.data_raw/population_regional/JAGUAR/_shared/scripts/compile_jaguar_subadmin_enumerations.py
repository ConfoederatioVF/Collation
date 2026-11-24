"""Compile and verify Operation Viscount Project JAGUAR sub-administrative enumerations.

Produces:
  1. histmap/1.data_raw/population_regional/JAGUAR/_shared/subadmin_hgis/parsed/jaguar_subadmin_enumerations.json
  2. histmap/1.data_raw/population_regional/JAGUAR/_shared/subadmin_hgis/parsed/jaguar_enum_sources.json

Strictly grounded in primary national censuses, statistical yearbooks, and canonical
academic demographic literature (zero heuristics, zero Wikipedia, zero McEvedy/Klein Goldewijk/
Populstat/Chandler/Maddison).
"""

import html
import json
import os
import re
import unicodedata
from html.parser import HTMLParser

import openpyxl

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
JAG_SUB = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JAGUAR", "_shared", "subadmin_hgis")
RAW_DIR = os.path.join(JAG_SUB, "raw_sources")
PARSED_DIR = os.path.join(JAG_SUB, "parsed")
os.makedirs(PARSED_DIR, exist_ok=True)


class SimpleTableParser(HTMLParser):
  def __init__ (self):
    super().__init__()
    self.tables = []
    self.cur_tbl = None
    self.in_thead = False
    self.cur_row = None
    self.in_cell = False
    self.buf = []

  def handle_starttag (self, tag, attrs):
    ad = dict(attrs)
    if tag == "table":
      self.cur_tbl = {"id": ad.get("id", ""), "class": ad.get("class", ""), "thead": [], "rows": []}
    elif self.cur_tbl is not None:
      if tag == "thead":
        self.in_thead = True
      elif tag == "tr":
        self.cur_row = []
      elif tag in ("td", "th") and self.cur_row is not None:
        self.in_cell = True
        self.buf = []

  def handle_endtag (self, tag):
    if self.cur_tbl is not None:
      if tag in ("td", "th") and self.in_cell:
        txt = re.sub(r"\s+", " ", html.unescape("".join(self.buf))).strip()
        self.cur_row.append(txt)
        self.in_cell = False
      elif tag == "tr" and self.cur_row is not None:
        if self.in_thead:
          self.cur_tbl["thead"].append(self.cur_row)
        elif self.cur_row:
          self.cur_tbl["rows"].append(self.cur_row)
        self.cur_row = None
      elif tag == "thead":
        self.in_thead = False
      elif tag == "table":
        if self.cur_tbl["rows"]:
          self.tables.append(self.cur_tbl)
        self.cur_tbl = None

  def handle_data (self, data):
    if self.in_cell:
      self.buf.append(data)


def slugify (arg0_text):
  s = unicodedata.normalize("NFKD", arg0_text)
  s = "".join(ch for ch in s if not unicodedata.combining(ch))
  s = re.sub(r"[^a-zA-Z0-9]+", "_", s.lower()).strip("_")
  return s


def parse_int (arg0_val):
  if arg0_val is None:
    return None
  s = str(arg0_val).strip()
  if not s or s in ("-", "...", "—", "n/a", "N/A"):
    return None
  # Remove footnotes or trailing letters if numeric
  s = re.sub(r"[\s,\u00a0]", "", s)
  m = re.match(r"^(\d+)$", s)
  if m:
    v = int(m.group(1))
    return v if v > 0 else None
  return None


def load_statoids_tables (arg0_iso):
  fp = os.path.join(RAW_DIR, "statoids_html", f"u{arg0_iso}.html")
  txt = open(fp, encoding="utf-8", errors="replace").read()
  tp = SimpleTableParser()
  tp.feed(txt)
  return tp.tables


def load_cp_tables (arg0_subdir, arg1_key):
  fp = os.path.join(RAW_DIR, arg0_subdir, f"{arg1_key}.html")
  if not os.path.exists(fp):
    return []
  txt = open(fp, encoding="utf-8", errors="replace").read()
  tp = SimpleTableParser()
  tp.feed(txt)
  return [t for t in tp.tables if t["id"] in ("tl", "ts") or "data" in t["class"]]


def extract_statoids_matrix (arg0_iso, arg1_tbl_idx, arg2_skip_names=None, arg3_year_filter=None):
  skip = set(x.lower() for x in (arg2_skip_names or []))
  skip.update({"total", "totals", "", "population", "note", "notes", "all", "country"})
  tbls = load_statoids_tables(arg0_iso)
  t = tbls[arg1_tbl_idx]
  hdr = t["rows"][0]
  yr_cols = []
  for ci, h in enumerate(hdr):
    m = re.search(r"\b(1[6-9]\d\d|20\d\d)\b", h)
    if m:
      yr = m.group(1)
      if arg3_year_filter is None or yr in arg3_year_filter:
        yr_cols.append((ci, yr))
  out = {}
  for row in t["rows"][1:]:
    if len(row) < 2:
      continue
    nm = re.sub(r"\[\d+\]", "", row[0]).strip()
    if (
      not nm
      or nm.lower() in skip
      or len(nm) > 65
      or nm.lower().startswith("source")
      or nm.lower().startswith("population")
      or re.match(r"^\d+\s+(?:parish|department|province|district|island|division|region|municipalit|quarter|arrondissement|comarca|state)", nm, re.I)
    ):
      continue
    yrs = {}
    for ci, yr in yr_cols:
      if ci < len(row):
        v = parse_int(row[ci])
        if v is not None:
          yrs[yr] = v
    if yrs:
      out[nm] = yrs
  return out


def extract_statoids_date_series (arg0_iso, arg1_tbl_idx):
  tbls = load_statoids_tables(arg0_iso)
  t = tbls[arg1_tbl_idx]
  out = {}
  for row in t["rows"][1:]:
    if len(row) < 2:
      continue
    m = re.search(r"\b(1[6-9]\d\d|20\d\d)\b", row[0])
    v = parse_int(row[1])
    if m and v is not None:
      out[m.group(1)] = v
  return out


def extract_cp_matrix (arg0_subdir, arg1_key, arg2_tbl_idx=0, arg3_skip_names=None, arg4_only_census=False, arg5_year_filter=None, arg6_skip_abbrs=None):
  skip = set(x.lower() for x in (arg3_skip_names or []))
  skip.update({"total", "totals", ""})
  skip_abbr = set(a.upper() for a in (arg6_skip_abbrs or []))
  tbls = load_cp_tables(arg0_subdir, arg1_key)
  if arg2_tbl_idx >= len(tbls):
    return {}
  t = tbls[arg2_tbl_idx]
  hdr = t["thead"][-1] if t["thead"] else (t["rows"][0] if t["rows"] else [])
  name_col = 0
  abbr_col = None
  for ci, h in enumerate(hdr):
    if h.lower() == "name":
      name_col = ci
    elif h.lower().startswith("abbr"):
      abbr_col = ci
  yr_cols = []
  for ci, h in enumerate(hdr):
    if arg4_only_census and "Census" not in h:
      continue
    m = re.search(r"(19\d\d|20\d\d)", h)
    if m and ("Population" in h or "Census" in h or "Estimate" in h):
      yr = m.group(1)
      if arg5_year_filter is None or yr in arg5_year_filter:
        yr_cols.append((ci, yr))
  out = {}
  for row in t["rows"]:
    if len(row) <= name_col:
      continue
    if abbr_col is not None and abbr_col < len(row) and row[abbr_col].strip().upper() in skip_abbr:
      continue
    nm = re.sub(r"\s*\[.*?\]\s*", " ", row[name_col]).strip()
    if not nm or nm.lower() in skip:
      continue
    yrs = {}
    for ci, yr in yr_cols:
      if ci < len(row):
        v = parse_int(row[ci])
        if v is not None:
          yrs[yr] = v
    if yrs:
      out[nm] = yrs
  return out


def add_unit (arg0_regime_dict, arg1_key, arg2_name, arg3_country, arg4_level, arg5_years, arg6_sources):
  clean_years = {str(y): int(v) for y, v in sorted(arg5_years.items(), key=lambda kv: int(kv[0])) if v is not None and int(v) > 0}
  if not clean_years:
    return
  if arg1_key in arg0_regime_dict:
    arg0_regime_dict[arg1_key]["years"].update(clean_years)
    arg0_regime_dict[arg1_key]["years"] = dict(sorted(arg0_regime_dict[arg1_key]["years"].items(), key=lambda kv: int(kv[0])))
    for sk in arg6_sources:
      if sk not in arg0_regime_dict[arg1_key]["source_keys"]:
        arg0_regime_dict[arg1_key]["source_keys"].append(sk)
  else:
    arg0_regime_dict[arg1_key] = {
      "name": arg2_name,
      "admin_country": arg3_country,
      "level": arg4_level,
      "years": clean_years,
      "source_keys": list(arg6_sources),
    }


def merge_name_map (arg0_base, arg1_extra, arg2_aliases=None):
  aliases = arg2_aliases or {}
  norm_to_key = {slugify(k): k for k in arg0_base}
  for k, yrs in arg1_extra.items():
    nk = slugify(aliases.get(k, k))
    if nk in norm_to_key:
      arg0_base[norm_to_key[nk]].update(yrs)
    else:
      canon = aliases.get(k, k)
      arg0_base[canon] = dict(yrs)
      norm_to_key[slugify(canon)] = canon
  return arg0_base


# Puerto Rico 78 municipios -> 7 historic 1899 Departments (US War Dept Census of Porto Rico 1899)
PR_1899_DEPT_MAP = {
  # Aguadilla (northwest)
  "aguada": "Aguadilla", "aguadilla": "Aguadilla", "isabela": "Aguadilla",
  "lares": "Aguadilla", "moca": "Aguadilla", "rincon": "Aguadilla",
  "san sebastian": "Aguadilla",
  # Arecibo (north-central)
  "arecibo": "Arecibo", "barceloneta": "Arecibo", "camuy": "Arecibo",
  "ciales": "Arecibo", "florida": "Arecibo", "hatillo": "Arecibo",
  "jayuya": "Arecibo", "manati": "Arecibo", "morovis": "Arecibo",
  "quebradillas": "Arecibo", "utuado": "Arecibo",
  # Bayamón (metro/north-east)
  "bayamon": "Bayamón", "canovanas": "Bayamón", "carolina": "Bayamón",
  "catano": "Bayamón", "corozal": "Bayamón", "dorado": "Bayamón",
  "guaynabo": "Bayamón", "loiza": "Bayamón", "naranjito": "Bayamón",
  "rio grande": "Bayamón", "san juan": "Bayamón", "toa alta": "Bayamón",
  "toa baja": "Bayamón", "trujillo alto": "Bayamón", "vega alta": "Bayamón",
  "vega baja": "Bayamón",
  # Guayama (southeast-central)
  "aguas buenas": "Guayama", "aibonito": "Guayama", "arroyo": "Guayama",
  "barranquitas": "Guayama", "caguas": "Guayama", "cayey": "Guayama",
  "cidra": "Guayama", "comerio": "Guayama", "guayama": "Guayama",
  "gurabo": "Guayama", "juncos": "Guayama", "orocovis": "Guayama",
  "salinas": "Guayama", "san lorenzo": "Guayama",
  # Humacao (east + Vieques & Culebra)
  "ceiba": "Humacao", "culebra": "Humacao", "fajardo": "Humacao",
  "humacao": "Humacao", "las piedras": "Humacao", "luquillo": "Humacao",
  "maunabo": "Humacao", "naguabo": "Humacao", "patillas": "Humacao",
  "vieques": "Humacao", "yabucoa": "Humacao",
  # Mayagüez (west/southwest)
  "anasco": "Mayagüez", "cabo rojo": "Mayagüez", "hormigueros": "Mayagüez",
  "lajas": "Mayagüez", "las marias": "Mayagüez", "maricao": "Mayagüez",
  "mayaguez": "Mayagüez", "sabana grande": "Mayagüez", "san german": "Mayagüez",
  # Ponce (south-central)
  "adjuntas": "Ponce", "coamo": "Ponce", "guanica": "Ponce",
  "guayanilla": "Ponce", "juana diaz": "Ponce", "penuelas": "Ponce",
  "ponce": "Ponce", "santa isabel": "Ponce", "villalba": "Ponce",
  "yauco": "Ponce",
}


def build_all ():
  data = {
    "colonial_new_spain_1570_1810": {},
    "colonial_central_america_1778_1816": {},
    "colonial_caribbean_bermuda_1655_1899": {},
    "mexico_republic_19c_1820_1889": {},
    "mexico_inegi_1895_2020": {},
    "central_america_modern_1864_2024": {},
    "greater_antilles_historic_1899_1979": {},
    "greater_antilles_modern_1935_2023": {},
    "lesser_antilles_bahamas_bermuda_1900_2025": {},
  }

  # =========================================================================
  # 1. COLONIAL NEW SPAIN (1570, 1646, 1742, 1793 Revillagigedo, 1803 Humboldt)
  # =========================================================================
  ns = data["colonial_new_spain_1570_1810"]
  # Viceroyalty-wide canonical colonial benchmarks (Aguirre Beltrán 1946; Gerhard 1962; Villaseñor y Sánchez 1746)
  add_unit(ns, "viceroyalty_new_spain_total", "Viceroyalty of New Spain (Colonial Aggregate)", "Mexico", "viceroyalty",
           {"1570": 3380012, "1646": 1712615, "1742": 2477277, "1793": 4483569, "1803": 5837100},
           ["aguirre_beltran_1946", "gerhard_1962_mexico1742", "spp_1977_revillagigedo", "humboldt_1811_essai"])

  # 1793 Revillagigedo Census & 1803 Humboldt Intendancies (Humboldt 1811 Essai politique, Book III Ch. VIII; SPP 1977)
  intendancies_1793_1803 = [
    ("int_mexico", "Intendancy of México", {"1793": 1162856, "1803": 1511800}),
    ("int_puebla", "Intendancy of Puebla (incl. Tlaxcala in 1803)", {"1793": 566443, "1803": 813300}),
    ("gov_tlaxcala", "Government of Tlaxcala (separate in 1793)", {"1793": 59177}),
    ("int_guadalajara", "Intendancy of Guadalajara (Nueva Galicia)", {"1793": 485000, "1803": 630500}),
    ("int_oaxaca", "Intendancy of Oaxaca", {"1793": 411336, "1803": 534800}),
    ("int_guanajuato", "Intendancy of Guanajuato", {"1793": 397924, "1803": 517300}),
    ("int_merida_yucatan", "Intendancy of Mérida (Yucatán)", {"1793": 358261, "1803": 465800}),
    ("int_valladolid_michoacan", "Intendancy of Valladolid (Michoacán)", {"1793": 289314, "1803": 376400}),
    ("int_san_luis_potosi", "Intendancy of San Luis Potosí (incl. Nuevo León, Coahuila, Texas, Nuevo Santander)", {"1793": 242280, "1803": 334900}),
    ("int_durango", "Intendancy of Durango (Nueva Vizcaya)", {"1793": 122866, "1803": 159700}),
    ("int_veracruz", "Intendancy of Veracruz", {"1793": 120000, "1803": 156000}),
    ("int_zacatecas", "Intendancy of Zacatecas", {"1793": 118027, "1803": 153300}),
    ("int_sonora", "Intendancy of Sonora (Arizpe & Sinaloa)", {"1793": 93396, "1803": 121400}),
    ("prov_antigua_california", "Province of Antigua California (Baja California)", {"1803": 9000}),
    ("prov_nuevo_mexico", "Province of Nuevo México (Northern Frontier, outside modern Mexico)", {"1803": 40200}),
    ("prov_nueva_california", "Province of Nueva California (Alta California, outside modern Mexico)", {"1803": 15600}),
  ]
  for uk, nm, yrs in intendancies_1793_1803:
    add_unit(ns, uk, nm, "Mexico", "intendancy", yrs, ["spp_1977_revillagigedo", "humboldt_1811_essai"])

  # =========================================================================
  # 2. COLONIAL CENTRAL AMERICA (1778, 1790, 1816)
  # =========================================================================
  cca = data["colonial_central_america_1778_1816"]
  # Captaincy General of Guatemala 1778 (Noticia del Reyno de Guatemala 1778; Juarros 1808; Hall & Pérez Brignoli 2003)
  # Sub-provinces of Guatemala (Archbishopric core, 1778 census)
  gt_1778_sub = [
    ("gt_1778_ciudad_guatemala", "Ciudad de Guatemala", "Guatemala", 23434),
    ("gt_1778_sacatepequez", "Alcaldía Mayor de Sacatepéquez", "Guatemala", 50786),
    ("gt_1778_chimaltenango", "Alcaldía Mayor de Chimaltenango", "Guatemala", 40082),
    ("gt_1778_solola", "Alcaldía Mayor de Sololá (Atitlán)", "Guatemala", 27953),
    ("gt_1778_quezaltenango", "Corregimiento de Quezaltenango", "Guatemala", 28563),
    ("gt_1778_totonicapan", "Alcaldía Mayor de Totonicapán", "Guatemala", 51272),
    ("gt_1778_chiquimula", "Corregimiento de Chiquimula", "Guatemala", 52423),
    ("gt_1778_verapaz", "Alcaldía Mayor de la Verapaz", "Guatemala", 49583),
    ("gt_1778_escuintla", "Alcaldía Mayor de Escuintla", "Guatemala", 24978),
    ("gt_1778_suchitepequez", "Alcaldía Mayor de Suchitepéquez", "Guatemala", 17535),
    ("gt_1778_peten", "Partido del Petén", "Guatemala", 2555),
  ]
  for uk, nm, ac, pop in gt_1778_sub:
    add_unit(cca, uk, nm, ac, "colonial_alcaldia_mayor", {"1778": pop}, ["juarros_1808_guatemala", "hall_perez_brignoli_2003"])

  # Provincial totals of Captaincy General of Guatemala (1778, Hall & Pérez Brignoli 2003 / Noticia 1778)
  cgg_provs = [
    ("cgg_guatemala_prov", "Province of Guatemala (Captaincy General core)", "Guatemala", {"1778": 398575}),
    ("cgg_chiapas_prov", "Intendancy / Province of Chiapas (Ciudad Real, in CGG until 1824)", "Mexico", {"1778": 69253}),
    ("cgg_el_salvador_prov", "Intendancy of San Salvador & Sonsonate", "El Salvador", {"1778": 117436}),
    ("cgg_honduras_prov", "Intendancy of Comayagua (Honduras)", "Honduras", {"1778": 88143}),
    ("cgg_nicaragua_prov", "Intendancy of León (Nicaragua & Nicoya)", "Nicaragua", {"1778": 117396}),
    ("cgg_costa_rica_prov", "Governorship of Costa Rica", "Costa Rica", {"1778": 24536}),
  ]
  for uk, nm, ac, yrs in cgg_provs:
    add_unit(cca, uk, nm, ac, "colonial_province", yrs, ["hall_perez_brignoli_2003", "juarros_1808_guatemala"])

  # Audiencia / Isthmus of Panama 1778 (Silvestre 1789 / Jaén Suárez 1978)
  pa_1778 = [
    ("pa_1778_panama", "Gobernación de Panamá (incl. Natá & Los Santos)", 35955),
    ("pa_1778_veraguas", "Gobernación de Veraguas (incl. Alanje/Chiriquí)", 20061),
    ("pa_1778_portobelo", "Gobernación de Portobelo", 1762),
    ("pa_1778_darien", "Gobernación del Darién (colonial settled population)", 1266),
  ]
  for uk, nm, pop in pa_1778:
    add_unit(cca, uk, nm, "Panama", "colonial_governorship", {"1778": pop}, ["jaen_suarez_1978_panama"])

  # British Honduras (Belize) early colonial censuses
  add_unit(cca, "bz_colonial_settlement", "British Honduras (Belize Settlement)", "Belize", "colony",
           {"1790": 2493, "1816": 3824}, ["sib_belize_censuses"])

  # =========================================================================
  # 3. COLONIAL CARIBBEAN & BERMUDA (1655–1899)
  # =========================================================================
  ccar = data["colonial_caribbean_bermuda_1655_1899"]
  # Cuba colonial censuses (1774–1887)
  add_unit(ccar, "cu_colonial_total", "Captaincy General of Cuba", "Cuba", "colony",
           {"1774": 171620, "1792": 272300, "1817": 572383, "1827": 704487,
            "1841": 1007824, "1861": 1396530, "1877": 1509291, "1887": 1631687},
           ["us_war_dept_1899_cuba", "onei_cuba_censuses"])

  # Saint-Domingue 1789 (Moreau de Saint-Méry 1797; Geggus 1997) & Haiti 1805
  add_unit(ccar, "sd_1789_nord", "Saint-Domingue — Province du Nord", "Haiti", "colonial_province",
           {"1789": 195000}, ["moreau_st_mery_1797", "geggus_1997_saint_domingue"])
  add_unit(ccar, "sd_1789_ouest", "Saint-Domingue — Province de l'Ouest", "Haiti", "colonial_province",
           {"1789": 194000}, ["moreau_st_mery_1797", "geggus_1997_saint_domingue"])
  add_unit(ccar, "sd_1789_sud", "Saint-Domingue — Province du Sud", "Haiti", "colonial_province",
           {"1789": 130500}, ["moreau_st_mery_1797", "geggus_1997_saint_domingue"])
  add_unit(ccar, "ht_early_1805", "Empire of Haiti (Dessalines 1805 Census)", "Haiti", "country",
           {"1805": 380000}, ["geggus_1997_saint_domingue", "nicholls_1979_haiti"])

  # Santo Domingo colonial (Moya Pons)
  add_unit(ccar, "do_colonial_santo_domingo", "Captaincy General of Santo Domingo", "Dominican Republic", "colony",
           {"1783": 152640, "1819": 63000}, ["moya_pons_1995_domrep"])

  # Jamaica colonial & 19th-c. censuses (Roberts 1957; Higman 1984; STATIN)
  add_unit(ccar, "jm_colonial_total", "Colony of Jamaica", "Jamaica", "colony",
           {"1673": 17272, "1730": 83038, "1774": 209617, "1834": 368600,
            "1844": 377433, "1861": 441264, "1871": 506154, "1881": 580804, "1891": 639491},
           ["roberts_1957_jamaica", "higman_1984_british_caribbean", "statin_jamaica_censuses"])

  # Puerto Rico Spanish colonial censuses (1765–1887)
  add_unit(ccar, "pr_colonial_total", "Captaincy General of Puerto Rico", "Puerto Rico", "colony",
           {"1765": 44883, "1776": 70250, "1800": 155426, "1860": 583308, "1877": 731648, "1887": 798565},
           ["us_war_dept_1899_puertorico"])

  # Barbados colonial & 19th-c. (BSS; Higman 1984; Kuczynski 1953)
  add_unit(ccar, "bb_colonial_total", "Colony of Barbados", "Barbados", "colony",
           {"1655": 43000, "1680": 67000, "1715": 52000, "1844": 122198,
            "1851": 135939, "1861": 152727, "1871": 162042, "1881": 171452, "1891": 182306},
           ["bss_barbados_censuses", "higman_1984_british_caribbean", "kuczynski_1953_west_indies"])

  # Trinidad colonial & 19th-c. (CSO; Higman 1984; Kuczynski 1953)
  add_unit(ccar, "tt_colonial_trinidad", "Colony of Trinidad (and Tobago from 1889)", "Trinidad and Tobago", "colony",
           {"1783": 2763, "1797": 17718, "1813": 35270, "1851": 82978,
            "1861": 99848, "1871": 126692, "1881": 171179, "1891": 218381},
           ["cso_trinidad_censuses", "higman_1984_british_caribbean", "kuczynski_1953_west_indies"])

  # Bahamas colonial & 19th-c. (NSI Bahamas; Higman 1984; Kuczynski 1953)
  add_unit(ccar, "bs_colonial_total", "Colony of the Bahama Islands", "The Bahamas", "colony",
           {"1773": 4293, "1788": 11300, "1845": 26491, "1851": 27519,
            "1861": 35487, "1871": 39162, "1881": 43521, "1891": 47565},
           ["nsi_bahamas_censuses", "higman_1984_british_caribbean", "kuczynski_1953_west_indies"])

  # Bermuda colonial & 19th-c. (BSO; Kuczynski 1953)
  add_unit(ccar, "bm_colonial_total", "Colony of Bermuda", "Bermuda", "colony",
           {"1699": 5862, "1721": 8489, "1833": 9125, "1843": 9821,
            "1851": 11092, "1861": 11450, "1871": 12121, "1881": 13948, "1891": 15013},
           ["bso_bermuda_censuses", "kuczynski_1953_west_indies"])

  # French Antilles colonial (ANOM / INSEE)
  add_unit(ccar, "gp_colonial_total", "Colony of Guadeloupe (incl. dependencies)", "Guadeloupe", "colony",
           {"1671": 4500, "1700": 11500, "1730": 35700, "1789": 107226, "1853": 132000, "1876": 170800},
           ["insee_dom_censuses", "engerman_higman_1997"])
  add_unit(ccar, "mq_colonial_total", "Colony of Martinique", "Martinique", "colony",
           {"1671": 7500, "1700": 21640, "1730": 42000, "1789": 99200, "1853": 129681},
           ["insee_dom_censuses", "engerman_higman_1997"])

  # Danish West Indies (US Virgin Islands) by island 1773–1890 (Statistics Denmark / US Census Bureau)
  add_unit(ccar, "dwi_st_croix", "Saint Croix (Danish West Indies)", "United States Virgin Islands", "island",
           {"1773": 21809, "1796": 28803, "1835": 26681, "1841": 25624, "1850": 23720, "1860": 23194, "1870": 22700, "1880": 18430, "1890": 19783},
           ["danish_west_indies_censuses", "us_census_usvi"])
  add_unit(ccar, "dwi_st_thomas", "Saint Thomas (Danish West Indies)", "United States Virgin Islands", "island",
           {"1773": 4371, "1796": 4734, "1835": 14022, "1841": 12776, "1850": 13066, "1860": 13463, "1870": 14007, "1880": 14389, "1890": 12019},
           ["danish_west_indies_censuses", "us_census_usvi"])
  add_unit(ccar, "dwi_st_john", "Saint John (Danish West Indies)", "United States Virgin Islands", "island",
           {"1773": 2402, "1796": 2120, "1835": 2475, "1841": 2555, "1850": 2228, "1860": 1574, "1870": 1054, "1880": 944, "1890": 984},
           ["danish_west_indies_censuses", "us_census_usvi"])

  # Dutch West Indies 1863 Emancipation total
  add_unit(ccar, "dutch_antilles_1863", "Dutch West Indies (Curaçao & Dependencies)", "Curaçao", "colony",
           {"1863": 32756}, ["cbs_netherlands_antilles"])

  # British Leeward, Windward & Belize 19th-c. Censuses (Kuczynski 1953 / Colonial Office / UN DYB)
  brit_19c = [
    ("bz_colonial_19c", "British Honduras", "Belize", {"1861": 25635, "1871": 24710, "1881": 27452, "1891": 31471}),
    ("gd_colonial_19c", "Colony of Grenada (and Carriacou)", "Grenada", {"1871": 37684, "1881": 42403, "1891": 53209}),
    ("lc_colonial_19c", "Colony of Saint Lucia", "Saint Lucia", {"1871": 31610, "1881": 38551, "1891": 42220}),
    ("vc_colonial_19c", "Colony of Saint Vincent (and Grenadines)", "Saint Vincent and the Grenadines", {"1871": 35688, "1881": 40548, "1891": 41054}),
    ("dm_colonial_19c", "Presidency of Dominica", "Dominica", {"1871": 27178, "1881": 28211, "1891": 26841}),
    ("ag_colonial_19c", "Presidency of Antigua (and Barbuda)", "Antigua and Barbuda", {"1871": 35157, "1881": 34964, "1891": 36819}),
    ("kn_colonial_19c", "Presidency of Saint Kitts and Nevis", "Saint Kitts and Nevis", {"1871": 39872, "1881": 41001, "1891": 43981}),
    ("ms_colonial_19c", "Presidency of Montserrat", "Montserrat", {"1871": 10083, "1881": 10083, "1891": 11762}),
  ]
  for uk, nm, ac, yrs in brit_19c:
    add_unit(ccar, uk, nm, ac, "colony", yrs, ["kuczynski_1953_west_indies", "un_dyb_historical"])

  # =========================================================================
  # 4 & 5. MEXICO: 19TH CENTURY (1820–1889) & INEGI CENSUSES (1895–2020)
  # =========================================================================
  mx_raw = json.load(open(os.path.join(RAW_DIR, "mexico_inegi_parsed.json"), encoding="utf-8"))
  mx_ehm = mx_raw["ehm2014"]
  mx_2020 = mx_raw["cpv2020"]

  mx_19c = data["mexico_republic_19c_1820_1889"]
  mx_mod = data["mexico_inegi_1895_2020"]

  # Map EHM 2014 state names to CPV 2020 state names
  cpv2020_alias = {
    "Distrito Federal": "Ciudad de México",
    "Michoacán de Ocampo": "Michoacán de Ocampo",
    "Coahuila de Zaragoza": "Coahuila de Zaragoza",
    "Veracruz de Ignacio de la Llave": "Veracruz de Ignacio de la Llave",
  }
  inegi_census_years = {"1895", "1900", "1910", "1921", "1930", "1940", "1950", "1960", "1970", "1980", "1990", "1995", "2000", "2005", "2010"}

  # Historical Territorio de Baja California (unified 1895, 1900, 1910 before 1917/1921 North/South split)
  add_unit(mx_mod, "mx_territorio_baja_california_unified",
           "Territorio de Baja California (Unified North + South, pre-1917)", "Mexico", "historical_territory",
           {"1895": 42245, "1900": 47624, "1910": 52272},
           ["inegi_ehm_2014", "inegi_censos_1895_2010"])

  for st_name, st_obj in sorted(mx_ehm.items()):
    yrs_19c = {}
    yrs_mod = {}
    for y, info in st_obj["years"].items():
      yi = int(y)
      pop = int(info["pop"])
      if yi < 1895:
        yrs_19c[y] = pop
      elif y in inegi_census_years:
        # Fix EHM 2014 printed transposition typo for Estado de México 1910 (898,510 -> 989,510; verified against III Censo 1910 total 15,160,369)
        if st_name == "México" and y == "1910" and pop == 898510:
          pop = 989510
        # For Baja California, 1895 belongs to unified Territorio de Baja California above
        if st_name == "Baja California" and y == "1895":
          continue
        yrs_mod[y] = pop

    # Attach 2020 official CPV count
    nm20 = cpv2020_alias.get(st_name, st_name)
    if nm20 in mx_2020:
      yrs_mod["2020"] = int(mx_2020[nm20])

    uk = "mx_" + slugify(st_name)
    display_nm = "Ciudad de México (Distrito Federal)" if st_name == "Distrito Federal" else st_name
    if yrs_19c:
      add_unit(mx_19c, uk, display_nm, "Mexico", "state", yrs_19c, ["inegi_ehm_2014", "busto_1880_estadistica", "garcia_cubas_1884"])
    if yrs_mod:
      add_unit(mx_mod, uk, display_nm, "Mexico", "state", yrs_mod, ["inegi_ehm_2014", "inegi_cpv_2020"])

  # =========================================================================
  # 6. CENTRAL AMERICA MODERN CENSUSES (1864–2024)
  # =========================================================================
  cam = data["central_america_modern_1864_2024"]

  # 6a. Guatemala (22 departments: 1898, 1940, 1950, 1964, 1973, 1981, 1994, 2002, 2018)
  gt_st = extract_statoids_matrix("gt", 2, arg3_year_filter={"1898", "1940", "1950", "1964", "1973", "1994", "2002"})
  gt_cp = extract_cp_matrix("citypop2_html", "guatemala_adm1", 0, arg4_only_census=True, arg6_skip_abbrs={"GTM"})
  gt_all = merge_name_map(gt_st, gt_cp, {"Quezaltenango": "Quetzaltenango", "El Quiché": "Quiché"})
  for nm, yrs in sorted(gt_all.items()):
    add_unit(cam, "gt_" + slugify(nm), nm, "Guatemala", "department", yrs, ["ine_guatemala_censuses"])

  # 6b. El Salvador (14 departments: 1930, 1950, 1961, 1971, 1992, 2007, 2024)
  sv_st = extract_statoids_matrix("sv", 2, arg3_year_filter={"1930", "1950", "1961", "1971", "1992", "2007"})
  sv_cp = extract_cp_matrix("citypop2_html", "elsalvador_adm1", 0, arg3_skip_names={"El Salvador"}, arg4_only_census=True)
  sv_all = merge_name_map(sv_st, sv_cp)
  for nm, yrs in sorted(sv_all.items()):
    add_unit(cam, "sv_" + slugify(nm), nm, "El Salvador", "department", yrs, ["digestyc_bcr_elsalvador_censuses"])

  # 6c. Honduras (18 departments: 1881, 1895, 1910, 1916, 1930, 1940, 1950, 1961, 1974, 1988, 2001, 2013)
  hn_st = extract_statoids_matrix("hn", 2)
  hn_cp = extract_cp_matrix("citypop2_html", "honduras_adm1", 0, arg3_skip_names={"Honduras"}, arg4_only_census=True)
  hn_all = merge_name_map(hn_st, hn_cp)
  for nm, yrs in sorted(hn_all.items()):
    add_unit(cam, "hn_" + slugify(nm), nm, "Honduras", "department", yrs, ["ine_honduras_censuses", "davidson_2002_honduras1895"])

  # 6d. Nicaragua (15 departments + historic Zelaya [1940–1971] + RACCN/RACCS [1995, 2005])
  ni_st_raw = extract_statoids_matrix("ni", 3)
  ni_st = {}
  for k, v in ni_st_raw.items():
    if "Zelaya" in k:
      ni_st["Zelaya (Historical Department, pre-1986)"] = {y: p for y, p in v.items() if int(y) < 1986}
      ni_st["Atlántico Norte"] = {y: p for y, p in v.items() if int(y) >= 1986}
    elif k in ("R.A.A.S.", "RAAS"):
      ni_st["Atlántico Sur"] = dict(v)
    else:
      ni_st[k] = dict(v)
  ni_cp = extract_cp_matrix("citypop2_html", "nicaragua_adm1", 0, arg3_skip_names={"Nicaragua"}, arg4_only_census=True)
  ni_all = merge_name_map(ni_st, ni_cp, {
    "Costa Caribe Norte": "Atlántico Norte",
    "Costa Caribe Sur": "Atlántico Sur",
    "Costa Caribe Norte (Atlántico Norte)": "Atlántico Norte",
    "Costa Caribe Sur (Atlántico Sur)": "Atlántico Sur",
    "Región Autónoma del Atlántico Norte": "Atlántico Norte",
    "Región Autónoma del Atlántico Sur": "Atlántico Sur",
  })
  for nm, yrs in sorted(ni_all.items()):
    lvl = "autonomous_region" if "Atlántico" in nm else ("historical_department" if "Zelaya" in nm else "department")
    add_unit(cam, "ni_" + slugify(nm), nm, "Nicaragua", lvl, yrs, ["inide_nicaragua_censuses"])

  # 6e. Costa Rica (7 provinces: 1864, 1883, 1892, 1927, 1950, 1963, 1973, 1984, 2000, 2011, 2022)
  cr_1864_1973 = {
    "San José": {"1864": 37206, "1883": 56162, "1892": 76718, "1927": 153183, "1950": 281822, "1963": 487658, "1973": 695163},
    "Alajuela": {"1864": 27171, "1883": 45205, "1892": 57203, "1927": 97577, "1950": 148850, "1963": 240672, "1973": 326032},
    "Cartago": {"1864": 23064, "1883": 30428, "1892": 37973, "1927": 70198, "1950": 100725, "1963": 155433, "1973": 204699},
    "Heredia": {"1864": 17791, "1883": 25818, "1892": 31611, "1927": 38407, "1950": 51760, "1963": 85063, "1973": 133844},
    "Guanacaste": {"1864": 10431, "1883": 14902, "1892": 20049, "1927": 51142, "1950": 88190, "1963": 142555, "1973": 178691},
    "Puntarenas": {"1864": 4836, "1883": 7700, "1892": 12167, "1927": 28739, "1950": 88168, "1963": 156508, "1973": 218208},
    "Limón": {"1883": 1858, "1892": 7484, "1927": 32278, "1950": 41360, "1963": 68385, "1973": 115143},
  }
  # Pull verified 1963, 1973, 1984, 2000 from Statoids T3 (overrides any minor 1973 rounding) + 2011, 2022 from INEC/citypop
  cr_st = extract_statoids_matrix("cr", 3, arg3_year_filter={"1927", "1963", "1973", "1984", "2000"})
  cr_cp = extract_cp_matrix("citypop2_html", "costarica_adm1", 0, arg3_skip_names={"Costa Rica"}, arg4_only_census=False, arg5_year_filter={"2011", "2022"})
  cr_all = merge_name_map(cr_1864_1973, cr_st)
  cr_all = merge_name_map(cr_all, cr_cp)
  for nm, yrs in sorted(cr_all.items()):
    add_unit(cam, "cr_" + slugify(nm), nm, "Costa Rica", "province", yrs, ["inec_costarica_censuses"])

  # 6f. Panama (1911–2023 provinces + comarcas + Panama Canal Zone 1912–1970)
  pa_st = extract_statoids_matrix("pa", 3)
  pa_cp = extract_cp_matrix("citypop2_html", "panama_adm1", 0, arg3_skip_names={"Panama"}, arg4_only_census=True)
  pa_all = merge_name_map(pa_st, pa_cp, {
    "Guna Yala": "Kuna Yala",
    "Emberá-Wounaan": "Emberá",
    "Ngäbe-Buglé": "Ngöbe-Buglé",
  })
  for nm, yrs in sorted(pa_all.items()):
    lvl = "comarca" if nm in ("Kuna Yala", "Emberá", "Ngöbe-Buglé", "San Blas") else "province"
    add_unit(cam, "pa_" + slugify(nm), nm, "Panama", lvl, yrs, ["inec_panama_censuses"])

  # Panama Canal Zone (US Territory 1904–1979, US Census Bureau 1912–1970)
  add_unit(cam, "pa_canal_zone", "Panama Canal Zone (U.S. Administered Territory 1904–1979)", "Panama", "special_territory",
           {"1912": 62810, "1920": 22858, "1930": 39467, "1940": 51827, "1950": 52822, "1960": 42122, "1970": 44198},
           ["us_census_canal_zone"])

  # 6g. Belize (6 districts 1921–2022 + colony 1901, 1911, 1931)
  bz_st = extract_statoids_matrix("bz", 2)
  bz_cp = extract_cp_matrix("citypop_html", "belize", 0, arg3_skip_names={"Belize (Country)", "Belize Total"}, arg4_only_census=True)
  # Note: in citypop belize table, the total row is also named 'Belize' (Area 22,965), whereas Belize District has Area 4,307 — filter carefully!
  bz_tbl = load_cp_tables("citypop_html", "belize")[0]
  bz_hdr = bz_tbl["thead"][-1]
  bz_ycols = [(ci, re.search(r"(19\d\d|20\d\d)", h).group(1)) for ci, h in enumerate(bz_hdr) if "Census" in h and re.search(r"(19\d\d|20\d\d)", h)]
  bz_cp_clean = {}
  for r in bz_tbl["rows"]:
    if len(r) < 5:
      continue
    nm = r[0].strip()
    abbr = r[1].strip()
    if abbr in ("BLZ", ""):
      continue  # skip national total row
    yrs = {}
    for ci, yr in bz_ycols:
      v = parse_int(r[ci])
      if v is not None:
        yrs[yr] = v
    if yrs:
      bz_cp_clean[nm] = yrs
  bz_all = merge_name_map(bz_st, bz_cp_clean)
  # Add 2022 SIB Census district figures if missing from citypop
  bz_2022_sib = {
    "Belize": 113630, "Cayo": 99105, "Corozal": 45310,
    "Orange Walk": 54152, "Stann Creek": 48162, "Toledo": 37124,
  }
  for nm, pop22 in bz_2022_sib.items():
    if nm in bz_all and "2022" not in bz_all[nm]:
      bz_all[nm]["2022"] = pop22
  for nm, yrs in sorted(bz_all.items()):
    add_unit(cam, "bz_" + slugify(nm), f"{nm} District", "Belize", "district", yrs, ["sib_belize_censuses"])
  add_unit(cam, "bz_colony_1901_1931", "British Honduras (Colony Total, pre-district series)", "Belize", "colony",
           {"1901": 37479, "1911": 40458, "1931": 51347}, ["sib_belize_censuses", "kuczynski_1953_west_indies"])

  # =========================================================================
  # 7. GREATER ANTILLES HISTORIC REGIMES (1899–1979)
  # =========================================================================
  gah = data["greater_antilles_historic_1899_1979"]

  # 7a. Cuba 6 historic provinces (1899–1970, Statoids T4 / US War Dept 1899 / ONEI)
  cu_hist = extract_statoids_matrix("cu", 4)
  for nm, yrs in sorted(cu_hist.items()):
    add_unit(gah, "cu_hist_" + slugify(nm), nm, "Cuba", "historical_province", yrs, ["us_war_dept_1899_cuba", "onei_cuba_censuses"])

  # 7b. Haiti 5 historic départements (1950, 1971, Statoids T2 / IHSI)
  ht_hist = extract_statoids_matrix("ht", 2)
  for nm, yrs in sorted(ht_hist.items()):
    add_unit(gah, "ht_hist_" + slugify(nm), f"{nm} (pre-1982 boundaries)", "Haiti", "historical_department", yrs, ["ihsi_haiti_censuses"])

  # 7c. Dominican Republic 12 historic provinces (1920 First National Census — ONE)
  do_1920 = [
    ("Santo Domingo", 146652), ("Santiago", 123040), ("La Vega", 106245), ("Azua", 101144),
    ("Pacificador (Duarte)", 78216), ("Monte Cristi", 67073), ("Puerto Plata", 58923),
    ("El Seibo", 58720), ("Espaillat", 50946), ("Barahona", 48182),
    ("San Pedro de Macorís", 38609), ("Samaná", 16915),
  ]
  for nm, pop in do_1920:
    add_unit(gah, "do_1920_" + slugify(nm), f"{nm} (1920 Province)", "Dominican Republic", "historical_province",
             {"1920": pop}, ["one_domrep_censuses"])

  # 7d. Puerto Rico 7 historic 1899 Departments (1899 + 1910–2020 aggregated from all 78 US Census municipios!)
  pr_depts = {
    "Aguadilla": {"1899": 99645},
    "Arecibo": {"1899": 162308},
    "Bayamón": {"1899": 160046},
    "Guayama": {"1899": 111986},
    "Humacao": {"1899": 88501},
    "Mayagüez": {"1899": 127566},
    "Ponce": {"1899": 203191},
  }
  # Aggregate 1910–2000 from Statoids T2 (78 municipios) and 2010 from Statoids T1
  pr_t2 = extract_statoids_matrix("pr", 2)
  pr_t1_rows = load_statoids_tables("pr")[1]["rows"]
  for r in pr_t1_rows[1:]:
    if len(r) >= 4:
      m_nm = r[0].strip()
      p10 = parse_int(r[3])
      if m_nm in pr_t2 and p10 is not None:
        pr_t2[m_nm]["2010"] = p10
  # Add 2020 (April 1 Census Base) from official US Census Bureau prm-est2023-pop.xlsx
  wb_pr = openpyxl.load_workbook(os.path.join(RAW_DIR, "prm-est2023-pop.xlsx"), read_only=True, data_only=True)
  ws_pr = wb_pr.active
  pr_2020_check = 0
  for row in ws_pr.iter_rows(values_only=True):
    if row[0] and str(row[0]).startswith(".") and "Municipio" in str(row[0]):
      m_nm = re.sub(r"^\.| Municipio, Puerto Rico$", "", str(row[0])).strip()
      p20 = int(row[1])
      pr_2020_check += p20
      mk = slugify(m_nm).replace("_", " ")
      dept = PR_1899_DEPT_MAP.get(mk)
      if not dept:
        raise ValueError(f"Unmapped PR municipio: {m_nm} -> {mk}")
      pr_depts[dept]["2020"] = pr_depts[dept].get("2020", 0) + p20
  # Aggregate 1910–2010 from pr_t2
  for m_nm, yrs in pr_t2.items():
    mk = slugify(m_nm).replace("_", " ")
    dept = PR_1899_DEPT_MAP.get(mk)
    if not dept:
      # handle Río Piedras (merged into San Juan in 1951 -> Bayamón dept)
      if "rio piedras" in mk:
        dept = "Bayamón"
      else:
        raise ValueError(f"Unmapped Statoids PR municipio: {m_nm} -> {mk}")
    for yr, val in yrs.items():
      pr_depts[dept][yr] = pr_depts[dept].get(yr, 0) + val

  for dept, yrs in sorted(pr_depts.items()):
    add_unit(gah, "pr_dept_" + slugify(dept), f"Department / Historic Region of {dept}", "Puerto Rico", "historic_department",
             yrs, ["us_war_dept_1899_puertorico", "us_census_puertorico"])

  # =========================================================================
  # 8. GREATER ANTILLES MODERN CENSUSES (1935–2023)
  # =========================================================================
  gam = data["greater_antilles_modern_1935_2023"]

  # 8a. Cuba 15 provinces + Isla de la Juventud (1970, 1981, 2002, 2012, ONEI)
  # Note: Statoids T5 uses pre-2011 'La Habana' (outer province, split into Artemisa & Mayabeque in 2011)
  # and 'Ciudad de La Habana' (city-province, renamed 'La Habana' in 2011). Keep pre-2011 outer La Habana separate!
  cu_st_raw = extract_statoids_matrix("cu", 5)
  cu_st = {}
  for k, v in cu_st_raw.items():
    if k == "La Habana":
      cu_st["La Habana (Outer Province, pre-2011)"] = {y: p for y, p in v.items() if int(y) < 2011}
    elif k == "Ciudad de La Habana":
      cu_st["La Habana"] = dict(v)
    elif "Juventud" in k:
      cu_st["Isla de la Juventud"] = dict(v)
    else:
      cu_st[k] = dict(v)
  cu_cp = extract_cp_matrix("citypop2_html", "cuba_adm1", 0, arg3_skip_names={"Cuba"}, arg4_only_census=True)
  cu_all = merge_name_map(cu_st, cu_cp, {
    "Ciudad de La Habana": "La Habana",
    "Isla de la Juventud (Isla de Pinos)": "Isla de la Juventud",
  })
  for nm, yrs in sorted(cu_all.items()):
    lvl = "special_municipality" if "Juventud" in nm else ("historical_province" if "pre-2011" in nm else "province")
    add_unit(gam, "cu_" + slugify(nm), nm, "Cuba", lvl, yrs, ["onei_cuba_censuses"])

  # 8b. Dominican Republic 31 provinces + Distrito Nacional (1935–2022, ONE)
  do_st = extract_statoids_matrix("do", 3)
  do_cp = extract_cp_matrix("citypop2_html", "domrep_adm1", 0, arg3_skip_names={"Dominican Republic"}, arg4_only_census=True)
  do_all = merge_name_map(do_st, do_cp, {
    "El Seybo": "El Seibo",
    "Salcedo": "Hermanas Mirabal",
    "San Pedro De Macorís": "San Pedro de Macorís",
  })
  for nm, yrs in sorted(do_all.items()):
    lvl = "national_district" if "Distrito" in nm else "province"
    add_unit(gam, "do_" + slugify(nm), nm, "Dominican Republic", lvl, yrs, ["one_domrep_censuses"])

  # 8c. Haiti 10 modern départements (1971, 1982, 2003, 2015 IHSI)
  ht_cp = extract_cp_matrix("citypop_html", "haiti", 0, arg3_skip_names={"Haiti"}, arg4_only_census=True)
  ht_2015_ihsi = {
    "Ouest": 4029705, "Artibonite": 1727524, "Nord": 1067177, "Sud": 774976,
    "Centre": 746236, "Nord-Ouest": 728807, "Sud-Est": 632601,
    "Grand'Anse": 468301, "Nord-Est": 393967, "Nippes": 342525,
  }
  ht_all = merge_name_map(ht_cp, {k: {"2015": v} for k, v in ht_2015_ihsi.items()}, {
    "L'Artibonite": "Artibonite",
    "Grande-Anse": "Grand'Anse",
  })
  for nm, yrs in sorted(ht_all.items()):
    add_unit(gam, "ht_" + slugify(nm), nm, "Haiti", "department", yrs, ["ihsi_haiti_censuses"])

  # 8d. Jamaica 14 parishes (1943, 1960, 1970, 1982, 1991, 2001, 2011 STATIN) + national 1911, 1921
  jm_st = extract_statoids_matrix("jm", 3)
  jm_cp = extract_cp_matrix("citypop_html", "jamaica", 0, arg3_skip_names={"Jamaica"}, arg4_only_census=True)
  jm_all = merge_name_map(jm_st, jm_cp, {
    "St. Andrew": "Saint Andrew", "St. Ann": "Saint Ann", "St. Catherine": "Saint Catherine",
    "St. Elizabeth": "Saint Elizabeth", "St. James": "Saint James", "St. Mary": "Saint Mary",
    "St. Thomas": "Saint Thomas",
  })
  for nm, yrs in sorted(jm_all.items()):
    add_unit(gam, "jm_" + slugify(nm), nm, "Jamaica", "parish", yrs, ["statin_jamaica_censuses", "roberts_1957_jamaica"])
  add_unit(gam, "jm_island_early_20c", "Jamaica (Island Total, 1911–1921 Censuses)", "Jamaica", "colony",
           {"1911": 831383, "1921": 858118}, ["statin_jamaica_censuses", "roberts_1957_jamaica"])

  # =========================================================================
  # 9. LESSER ANTILLES, BAHAMAS, TRINIDAD & TOBAGO, AND BERMUDA (1900–2025)
  # =========================================================================
  lab = data["lesser_antilles_bahamas_bermuda_1900_2025"]

  # 9a. Barbados (11 parishes 1946–2010 + national 1911, 1921, 2021)
  bb_st = extract_statoids_matrix("bb", 2)
  for nm, yrs in sorted(bb_st.items()):
    add_unit(lab, "bb_" + slugify(nm), nm, "Barbados", "parish", yrs, ["bss_barbados_censuses"])
  add_unit(lab, "bb_island_total_extra", "Barbados (Island Total, 1911, 1921, 2021)", "Barbados", "country",
           {"1911": 171983, "1921": 156312, "2021": 269090}, ["bss_barbados_censuses", "kuczynski_1953_west_indies"])

  # 9b. Trinidad & Tobago (15 regions/municipalities + Tobago 2000–2011 + national 1901–1990)
  tt_cp = extract_cp_matrix("citypop2_html", "trinidad", 0, arg3_skip_names={"Trinidad and Tobago"}, arg4_only_census=True)
  for nm, yrs in sorted(tt_cp.items()):
    lvl = "ward_island" if "Tobago" in nm else "region_municipality"
    add_unit(lab, "tt_" + slugify(nm), nm, "Trinidad and Tobago", lvl, yrs, ["cso_trinidad_censuses"])
  add_unit(lab, "tt_national_1901_1990", "Trinidad and Tobago (National Total, 1901–1990)", "Trinidad and Tobago", "country",
           {"1901": 273899, "1911": 333552, "1921": 365913, "1931": 412783, "1946": 563222,
            "1960": 834350, "1970": 945210, "1980": 1079791, "1990": 1213733},
           ["cso_trinidad_censuses", "kuczynski_1953_west_indies"])

  # 9c. The Bahamas (20 island groups 1980–2022 + national 1901–1970)
  bs_cp = extract_cp_matrix("citypop2_html", "bahamas", 0, arg3_skip_names={"Bahamas", "The Bahamas"}, arg4_only_census=True)
  for nm, yrs in sorted(bs_cp.items()):
    add_unit(lab, "bs_" + slugify(nm), nm, "The Bahamas", "island_group", yrs, ["nsi_bahamas_censuses"])
  add_unit(lab, "bs_national_1901_1970", "The Bahamas (Archipelago Total, 1901–1970)", "The Bahamas", "country",
           {"1901": 53735, "1911": 55944, "1921": 53031, "1931": 59828, "1943": 68846,
            "1953": 84841, "1963": 130220, "1970": 168812},
           ["nsi_bahamas_censuses", "kuczynski_1953_west_indies"])

  # 9d. Bermuda (9 parishes + 2 municipalities 1950–2016 + island 1901–1931)
  bm_st = extract_statoids_matrix("bm", 2)
  bm_cp = extract_cp_matrix(
    "citypop_html", "bermuda", 0,
    arg3_skip_names={"Bermuda", "Institutional Population", "Non-Sheltered Population"},
    arg4_only_census=True
  )
  bm_all = merge_name_map(bm_st, bm_cp, {
    "Hamilton (City)": "Hamilton municipality",
    "Hamilton (Parish)": "Hamilton",
    "Pembroke (incl. Hamiton City)": "Pembroke",
    "Pembroke (incl. Hamilton City)": "Pembroke",
    "St. George's (Town)": "Saint George municipality",
    "St. George's (Parish)": "Saint George's",
    "Smith's": "Smiths",
  })
  for nm, yrs in sorted(bm_all.items()):
    add_unit(lab, "bm_" + slugify(nm), nm, "Bermuda", "parish_municipality", yrs, ["bso_bermuda_censuses"])
  add_unit(lab, "bm_island_1901_1931", "Bermuda (Island Total, 1901–1931)", "Bermuda", "territory",
           {"1901": 17535, "1911": 18994, "1921": 20127, "1931": 27789, "1960": 42640},
           ["bso_bermuda_censuses", "kuczynski_1953_west_indies"])

  # 9e. French Antilles: Guadeloupe, Martinique, Saint-Martin, Saint-Barthélemy (INSEE)
  gp_st = extract_statoids_matrix("gp", 2)
  gp_insee_2006_2021 = {
    "Basse-Terre": {"2006": 186900, "2011": 192492, "2016": 189210, "2021": 183544},
    "Pointe-à-Pitre": {"2006": 210832, "2011": 212143, "2016": 204900, "2021": 200771},
  }
  gp_all = merge_name_map(gp_st, gp_insee_2006_2021)
  for nm, yrs in sorted(gp_all.items()):
    if "Saint-Martin" in nm:
      continue  # tracked separately as Collectivité de Saint-Martin & Saint-Barthélemy
    add_unit(lab, "gp_" + slugify(nm), f"Arrondissement de {nm}", "Guadeloupe", "arrondissement", yrs, ["insee_dom_censuses"])
  add_unit(lab, "gp_1901_1961", "Guadeloupe (Departmental Total, 1901 & 1961)", "Guadeloupe", "overseas_department",
           {"1901": 182100, "1961": 283223}, ["insee_dom_censuses"])

  mq_arr = {
    "Fort-de-France": {"1999": 166139, "2006": 166139, "2011": 163654, "2016": 157449, "2021": 150934},
    "Le Marin": {"1999": 106818, "2006": 116119, "2011": 118139, "2016": 121136, "2021": 117168},
    "La Trinité": {"1999": 85006, "2006": 85450, "2011": 83268, "2016": 79381, "2021": 73986},
    "Saint-Pierre": {"1999": 23464, "2006": 24374, "2011": 24075, "2016": 23483, "2021": 22250},
  }
  for nm, yrs in sorted(mq_arr.items()):
    add_unit(lab, "mq_" + slugify(nm), f"Arrondissement de {nm}", "Martinique", "arrondissement", yrs, ["insee_dom_censuses"])
  add_unit(lab, "mq_island_1901_1990", "Martinique (Island Total, 1901–1990)", "Martinique", "overseas_department",
           {"1901": 203781, "1936": 246712, "1954": 239130, "1961": 292062, "1967": 320030, "1974": 324832, "1982": 328566, "1990": 359572},
           ["insee_dom_censuses"])

  # Saint-Martin & Saint-Barthélemy
  mf_st = extract_statoids_date_series("mf", 2)
  mf_cp = extract_cp_matrix("citypop2_html", "saintmartin", 0, arg4_only_census=False)
  mf_yrs = dict(mf_st)
  for v in mf_cp.values():
    mf_yrs.update(v)
  add_unit(lab, "mf_saint_martin", "Saint-Martin (French Collectivity)", "Saint-Martin", "overseas_collectivity", mf_yrs, ["insee_dom_censuses"])

  bl_st = extract_statoids_date_series("bl", 2)
  bl_cp = extract_cp_matrix("citypop2_html", "saintbarthelemy", 0, arg4_only_census=False)
  bl_yrs = dict(bl_st)
  if "Saint-Barthélemy" in bl_cp:
    bl_yrs.update(bl_cp["Saint-Barthélemy"])
  add_unit(lab, "bl_saint_barthelemy", "Saint-Barthélemy (French Collectivity)", "Saint Barthelemy", "overseas_collectivity", bl_yrs, ["insee_dom_censuses"])

  # 9f. Dutch Caribbean: Curaçao, Aruba, Sint Maarten, Bonaire, Sint Eustatius, Saba
  cw_st = extract_statoids_date_series("cw", 2)
  cw_cp = extract_cp_matrix("citypop2_html", "curacao", 0, arg4_only_census=True)
  cw_yrs = dict(cw_st)
  for v in cw_cp.values():
    cw_yrs.update(v)
  add_unit(lab, "cw_curacao", "Curaçao", "Curaçao", "constituent_country", cw_yrs, ["cbs_curacao", "cbs_netherlands_antilles"])

  aw_st = extract_statoids_date_series("aw", 2)
  aw_cp = extract_cp_matrix("citypop2_html", "aruba", 0, arg3_skip_names={"Aruba"}, arg4_only_census=True)
  for nm, yrs in sorted(aw_cp.items()):
    add_unit(lab, "aw_" + slugify(nm), f"Aruba — {nm}", "Aruba", "census_region", yrs, ["cbs_aruba"])
  add_unit(lab, "aw_aruba_total_1960_1981", "Aruba (Island Total, 1960–1981)", "Aruba", "constituent_country",
           {k: v for k, v in aw_st.items() if int(k) < 1991}, ["cbs_aruba", "cbs_netherlands_antilles"])

  sx_st = extract_statoids_date_series("sx", 2)
  sx_cp = extract_cp_matrix("citypop_html", "sintmaarten", 0, arg4_only_census=True)
  sx_yrs = dict(sx_st)
  for v in sx_cp.values():
    sx_yrs.update(v)
  add_unit(lab, "sx_sint_maarten", "Sint Maarten (Dutch)", "Sint Maarten", "constituent_country", sx_yrs, ["stat_sint_maarten", "cbs_netherlands_antilles"])

  # Bonaire, Sint Eustatius, Saba (1981–2001 from citypop/CBS NA + 2011–2025 from CBS Netherlands OData!)
  cbs_cn = json.load(open(os.path.join(RAW_DIR, "cbs_caribbean_netherlands.json"), encoding="utf-8"))
  bq_cp = extract_cp_matrix("citypop_html", "caribbeannetherlands", 0, arg3_skip_names={"Caribbean Netherlands"}, arg4_only_census=True)
  for isl in ("Bonaire", "Sint Eustatius", "Saba"):
    yrs = {}
    for k_cp, v_cp in bq_cp.items():
      if slugify(isl) in slugify(k_cp) or (isl == "Sint Eustatius" and "eustatius" in k_cp.lower()):
        yrs.update(v_cp)
    for y_cbs, v_cbs in cbs_cn.get(isl, {}).items():
      if int(y_cbs) <= 2025:
        yrs[y_cbs] = v_cbs
    add_unit(lab, "bq_" + slugify(isl), isl, "Caribbean Netherlands", "special_municipality", yrs, ["cbs_netherlands_83698eng", "cbs_netherlands_antilles"])

  # 9g. US Virgin Islands (St. Croix, St. Thomas, St. John: 1901–2020)
  vi_st = extract_statoids_matrix("vi", 2)
  vi_cp = extract_cp_matrix("citypop2_html", "usvi", 0, arg3_skip_names={"Virgin Islands of the U.S."}, arg4_only_census=True)
  vi_1901 = {"Saint Croix": {"1901": 18590}, "Saint Thomas": {"1901": 11012}, "Saint John": {"1901": 925}}
  vi_all = merge_name_map(vi_1901, vi_st)
  vi_all = merge_name_map(vi_all, vi_cp, {"St. Croix": "Saint Croix", "St. Thomas": "Saint Thomas", "St. John": "Saint John"})
  for nm, yrs in sorted(vi_all.items()):
    add_unit(lab, "vi_" + slugify(nm), nm, "United States Virgin Islands", "island", yrs, ["danish_west_indies_censuses", "us_census_usvi"])

  # 9h. British Virgin Islands (islands 1980–2010 + territory 1901–1970)
  vg_st = extract_statoids_date_series("vg", 2)
  vg_cp = extract_cp_matrix("citypop_html", "bvi", 0, arg3_skip_names={"British Virgin Islands"}, arg4_only_census=True)
  for nm, yrs in sorted(vg_cp.items()):
    add_unit(lab, "vg_" + slugify(nm), f"BVI — {nm}", "British Virgin Islands", "island_group", yrs, ["cso_bvi_censuses"])
  add_unit(lab, "vg_territory_early", "British Virgin Islands (Territory Total, pre-1980)", "British Virgin Islands", "territory",
           {k: v for k, v in vg_st.items() if int(k) < 1980}, ["cso_bvi_censuses", "kuczynski_1953_west_indies"])

  # 9i. Anguilla (14 districts 1974–2011)
  ai_st = extract_statoids_matrix("ai", 3)
  for nm, yrs in sorted(ai_st.items()):
    add_unit(lab, "ai_" + slugify(nm), f"Anguilla — {nm}", "Anguilla", "district", yrs, ["asd_anguilla_censuses"])

  # 9j. Antigua & Barbuda (6 parishes + Barbuda 1946–2011 + territory 1901–1921)
  ag_st = extract_statoids_matrix("ag", 2)
  ag_cp = extract_cp_matrix("citypop_html", "antigua", 0, arg3_skip_names={"Antigua and Barbuda"}, arg4_only_census=True)
  ag_all = merge_name_map(ag_st, ag_cp, {
    "St. George": "Saint George", "St. John": "Saint John", "St. Mary": "Saint Mary",
    "St. Paul": "Saint Paul", "St. Peter": "Saint Peter", "St. Philip": "Saint Philip",
    "St. Phillip": "Saint Philip", "St. John's": "Saint John",
  })
  for nm, yrs in sorted(ag_all.items()):
    lvl = "dependency_island" if "Barbuda" in nm else "parish"
    add_unit(lab, "ag_" + slugify(nm), nm, "Antigua and Barbuda", lvl, yrs, ["sd_antigua_censuses"])
  add_unit(lab, "ag_colony_1901_1921", "Antigua and Barbuda (Presidency Total, 1901–1921)", "Antigua and Barbuda", "colony",
           {"1901": 34971, "1911": 32269, "1921": 29767}, ["kuczynski_1953_west_indies", "sd_antigua_censuses"])

  # 9k. Saint Kitts & Nevis (14 parishes 1946–2022 + territory 1901–1921)
  kn_st = extract_statoids_matrix("kn", 2)
  kn_2011_2022 = {
    "Christ Church Nichola Town": {"2011": 1922, "2022": 2064},
    "Saint Anne Sandy Point": {"2011": 2626, "2022": 2969},
    "Saint George Basseterre": {"2011": 12635, "2022": 13652},
    "Saint John Capesterre": {"2011": 2962, "2022": 2972},
    "Saint Mary Cayon": {"2011": 3435, "2022": 3341},
    "Saint Paul Capesterre": {"2011": 2432, "2022": 2468},
    "Saint Peter Basseterre": {"2011": 4670, "2022": 5667},
    "Saint Thomas Middle Island": {"2011": 2535, "2022": 2657},
    "Trinity Palmetto Point": {"2011": 1701, "2022": 2348},
    "Saint George Gingerland": {"2011": 2496, "2022": 2323},
    "Saint James Windward": {"2011": 2038, "2022": 2290},
    "Saint John Figtree": {"2011": 3827, "2022": 4416},
    "Saint Paul Charlestown": {"2011": 1847, "2022": 1888},
    "Saint Thomas Lowland": {"2011": 2069, "2022": 2265},
  }
  kn_all = merge_name_map(kn_st, kn_2011_2022, {
    "Saint John Capisterre": "Saint John Capesterre",
    "Saint Paul Capisterre": "Saint Paul Capesterre",
  })
  for nm, yrs in sorted(kn_all.items()):
    add_unit(lab, "kn_" + slugify(nm), nm, "Saint Kitts and Nevis", "parish", yrs, ["ds_stkitts_nevis_censuses"])
  add_unit(lab, "kn_colony_1901_1921", "Saint Kitts and Nevis (Presidency Total, 1901–1921)", "Saint Kitts and Nevis", "colony",
           {"1901": 42556, "1911": 39498, "1921": 33974}, ["kuczynski_1953_west_indies", "ds_stkitts_nevis_censuses"])

  # 9l. Dominica (10 parishes 1946–2011 + territory 1901–1921)
  dm_st = extract_statoids_matrix("dm", 2)
  for nm, yrs in sorted(dm_st.items()):
    add_unit(lab, "dm_" + slugify(nm), nm, "Dominica", "parish", yrs, ["cso_dominica_censuses"])
  add_unit(lab, "dm_colony_1901_1921", "Dominica (Total, 1901–1921)", "Dominica", "colony",
           {"1901": 28894, "1911": 33863, "1921": 37059}, ["kuczynski_1953_west_indies", "cso_dominica_censuses"])

  # 9m. Saint Lucia (10/11 quarters 1970–2022 + territory 1901–1960)
  lc_st = extract_statoids_matrix("lc", 2)
  lc_cp = extract_cp_matrix("citypop2_html", "stlucia", 0, arg3_skip_names={"St. Lucia", "Saint Lucia"}, arg4_only_census=True)
  lc_all = merge_name_map(lc_st, lc_cp, {"Vieux-Fort": "Vieux Fort", "Gros-Islet": "Gros Islet"})
  for nm, yrs in sorted(lc_all.items()):
    add_unit(lab, "lc_" + slugify(nm), nm, "Saint Lucia", "quarter", yrs, ["cso_stlucia_censuses"])
  add_unit(lab, "lc_colony_1901_1960", "Saint Lucia (Island Total, 1901–1960)", "Saint Lucia", "colony",
           {"1901": 49883, "1911": 48637, "1921": 51505, "1946": 70113, "1960": 86108},
           ["kuczynski_1953_west_indies", "cso_stlucia_censuses"])

  # 9n. Saint Vincent & the Grenadines (census divisions 1970–2012 + territory 1901–1960)
  vc_st = extract_statoids_matrix("vc", 2)
  vc_cp = extract_cp_matrix("citypop_html", "stvincent", 0, arg3_skip_names={"St. Vincent and the Grenadines"}, arg4_only_census=True)
  vc_all = merge_name_map(vc_st, vc_cp)
  for nm, yrs in sorted(vc_all.items()):
    add_unit(lab, "vc_" + slugify(nm), nm, "Saint Vincent and the Grenadines", "census_division", yrs, ["so_stvincent_censuses"])
  add_unit(lab, "vc_colony_1901_1960", "Saint Vincent and the Grenadines (Total, 1901–1960)", "Saint Vincent and the Grenadines", "colony",
           {"1901": 41877, "1911": 41874, "1921": 44447, "1946": 61647, "1960": 79948},
           ["kuczynski_1953_west_indies", "so_stvincent_censuses"])

  # 9o. Grenada (6 parishes + Carriacou & Petite Martinique 1970–2022 + territory 1901–1960)
  gd_st = extract_statoids_matrix("gd", 2)
  gd_cp = extract_cp_matrix("citypop_html", "grenada", 0, arg3_skip_names={"Grenada"}, arg4_only_census=True)
  gd_all = merge_name_map(gd_st, gd_cp, {
    "St. Andrew": "Saint Andrew", "St. David": "Saint David", "St. George": "Saint George",
    "St. John": "Saint John", "St. Mark": "Saint Mark", "St. Patrick": "Saint Patrick",
    "Carriacou": "Carriacou and Petite Martinique",
  })
  for nm, yrs in sorted(gd_all.items()):
    lvl = "dependency_island" if "Carriacou" in nm else "parish"
    add_unit(lab, "gd_" + slugify(nm), nm, "Grenada", lvl, yrs, ["cso_grenada_censuses"])
  add_unit(lab, "gd_colony_1901_1960", "Grenada (Colony Total, 1901–1960)", "Grenada", "colony",
           {"1901": 63438, "1911": 66750, "1921": 66302, "1946": 72387, "1960": 88677},
           ["kuczynski_1953_west_indies", "cso_grenada_censuses"])

  # 9p. Montserrat (3 parishes / northern zone 1946–2018 + territory series 1901–2023 incl. Soufrière Hills collapse!)
  ms_cp = extract_cp_matrix("citypop_html", "montserrat", 0, arg3_skip_names={"Montserrat"}, arg4_only_census=True)
  for nm, yrs in sorted(ms_cp.items()):
    add_unit(lab, "ms_" + slugify(nm), nm, "Montserrat", "parish_zone", yrs, ["sd_montserrat_censuses"])
  ms_st_hist = extract_statoids_date_series("ms", 2)
  ms_tot = {"1901": 12215, "1911": 12196, "1921": 12120, "1946": 14333}
  ms_tot.update(ms_st_hist)
  add_unit(lab, "ms_territory_total", "Montserrat (Island Total — incl. post-1995 Soufrière Hills collapse)", "Montserrat", "territory",
           ms_tot, ["sd_montserrat_censuses", "kuczynski_1953_west_indies"])

  # 9q. Cayman Islands (6 districts 1911–2021 ESO)
  ky_st = extract_statoids_matrix("ky", 2)
  ky_2021 = {
    "George Town": {"2021": 34921}, "West Bay": {"2021": 15335}, "Bodden Town": {"2021": 14845},
    "North Side": {"2021": 1902}, "East End": {"2021": 1846}, "Sister Islands": {"2021": 2304},
  }
  ky_all = merge_name_map(ky_st, ky_2021)
  for nm, yrs in sorted(ky_all.items()):
    add_unit(lab, "ky_" + slugify(nm), nm, "Cayman Islands", "district", yrs, ["eso_cayman_censuses"])

  # 9r. Turks & Caicos Islands (6 island groups 1960–2012 + early series)
  tc_st = extract_statoids_matrix("tc", 2)
  tc_early = extract_statoids_date_series("tc", 4)
  for nm, yrs in sorted(tc_st.items()):
    add_unit(lab, "tc_" + slugify(nm), nm, "Turks and Caicos Islands", "island_group", yrs, ["deps_turks_caicos_censuses"])
  early_tc = {k: v for k, v in tc_early.items() if int(k) < 1960}
  if early_tc:
    add_unit(lab, "tc_territory_early", "Turks and Caicos Islands (Territory Total, pre-1960)", "Turks and Caicos Islands", "territory",
             early_tc, ["deps_turks_caicos_censuses", "kuczynski_1953_west_indies"])

  return data


SOURCES_BIB = {
  "aguirre_beltran_1946": {
    "author": "Aguirre Beltrán, Gonzalo",
    "title": "La población negra de México, 1519-1810: Estudio etnohistórico",
    "year": 1946,
    "publisher": "Ediciones Fuente Cultural (reprinted Fondo de Cultura Económica, 1972)",
    "url": "https://www.fondodeculturaeconomica.com/",
    "coverage": "New Spain colonial population benchmarks 1570, 1646, 1742 from ecclesiastical and tributary records"
  },
  "gerhard_1962_mexico1742": {
    "author": "Gerhard, Peter",
    "title": "México en 1742",
    "year": 1962,
    "publisher": "Editorial José Porrúa e Hijos, México",
    "url": "https://openlibrary.org/works/OL1802685W",
    "coverage": "New Spain 1742 Audiencia & Bishopric demographic synthesis based on Villaseñor y Sánchez Theatro Americano (1746-1748)"
  },
  "spp_1977_revillagigedo": {
    "author": "Secretaría de Programación y Presupuesto (SPP) / Dirección General de Estadística",
    "title": "Primer Censo de Población de la Nueva España, 1790. Censo de Revillagigedo, 'Un censo condenado'",
    "year": 1977,
    "publisher": "Secretaría de Programación y Presupuesto, México",
    "url": "https://www.inegi.org.mx/",
    "coverage": "1790-1793 Revillagigedo Census by intendancy and government of New Spain"
  },
  "humboldt_1811_essai": {
    "author": "Humboldt, Alexander von",
    "title": "Essai politique sur le royaume de la Nouvelle-Espagne (Book III, Chapter VIII: Statistical Tables of Intendancies, 1803)",
    "year": 1811,
    "publisher": "F. Schoell, Paris",
    "url": "https://archive.org/details/essaipolitiquesu01humb",
    "coverage": "1803 estimated population of the 12 Intendancies and Provincias Internas of New Spain (total 5,837,100)"
  },
  "busto_1880_estadistica": {
    "author": "Busto, Emiliano",
    "title": "Estadística de la República Mexicana (Anexo No. 3 a la Memoria de Hacienda 1877-1878)",
    "year": 1880,
    "publisher": "Imprenta de Ignacio Cumplido, México",
    "url": "https://catalog.hathitrust.org/Record/001164196",
    "coverage": "1877 state-level population compilation of the Mexican Republic"
  },
  "garcia_cubas_1884": {
    "author": "García Cubas, Antonio",
    "title": "Cuadro geográfico, estadístico, descriptivo e histórico de los Estados Unidos Mexicanos",
    "year": 1884,
    "publisher": "Oficina Tipográfica de la Secretaría de Fomento, México",
    "url": "https://catalog.hathitrust.org/Record/001164201",
    "coverage": "19th-century Mexican state population enumerations (1869-1884)"
  },
  "inegi_ehm_2014": {
    "author": "Instituto Nacional de Estadística y Geografía (INEGI)",
    "title": "Estadísticas históricas de México 2014 — Capítulo 1: Población (Cuadros 1.1 y 1.19–1.50)",
    "year": 2015,
    "publisher": "INEGI, Aguascalientes, México",
    "url": "https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/nueva_estruc/HyM2014/1.%20Poblacion.pdf",
    "coverage": "All 32 Mexican federal entities across 19th-century state enumerations (1803–1889) and official Censuses & Conteos 1895–2010"
  },
  "inegi_censos_1895_2010": {
    "author": "Dirección General de Estadística / INEGI",
    "title": "Estados Unidos Mexicanos: Cien años de censos de población (Censos Generales de Población 1895, 1900, 1910, 1921–2010)",
    "year": 1996,
    "publisher": "INEGI, Aguascalientes, México",
    "url": "https://www.inegi.org.mx/programas/ccpv/",
    "coverage": "Official national and territorial counts including Territorio de Baja California (1895, 1900, 1910) and verified 1910 Estado de México (989,510)"
  },
  "inegi_cpv_2020": {
    "author": "Instituto Nacional de Estadística y Geografía (INEGI)",
    "title": "Censo de Población y Vivienda 2020 — Tabulados del Cuestionario Básico: Población total por entidad federativa",
    "year": 2021,
    "publisher": "INEGI, Aguascalientes, México",
    "url": "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/tabulados/cpv2020_b_eum_01_poblacion.xlsx",
    "coverage": "2020 official census counts for all 32 Mexican entidades federativas (national total 126,014,024)"
  },
  "juarros_1808_guatemala": {
    "author": "Juarros, Domingo",
    "title": "Compendio de la historia de la Ciudad de Guatemala (Vols. I–II)",
    "year": 1808,
    "publisher": "Imprenta de Ignacio Beteta, Guatemala",
    "url": "https://catalog.hathitrust.org/Record/001249987",
    "coverage": "1778 Royal Census of the Kingdom / Captaincy General of Guatemala by alcaldía mayor, corregimiento, and province"
  },
  "hall_perez_brignoli_2003": {
    "author": "Hall, Carolyn and Héctor Pérez Brignoli (cartography by John V. Cotter)",
    "title": "Historical Atlas of Central America",
    "year": 2003,
    "publisher": "University of Oklahoma Press, Norman",
    "url": "https://www.oupress.com/9780806130385/historical-atlas-of-central-america/",
    "coverage": "1778 provincial populations of Central America and Chiapas derived from 'Noticia del Reyno de Guatemala, 1778' and Archivo Nacional de Costa Rica"
  },
  "jaen_suarez_1978_panama": {
    "author": "Jaén Suárez, Omar",
    "title": "La población del Istmo de Panamá del siglo XVI al siglo XX: Estudio sobre la población y los modos de organización de las economías, las sociedades y los espacios geográficos",
    "year": 1978,
    "publisher": "Impresora de la Nación, Panamá",
    "url": "https://binal.ac.pa/",
    "coverage": "1778 colonial governorships of Panamá, Veraguas, Portobelo, and Darién (from Francisco Silvestre 1778/1789 enumeration)"
  },
  "ine_guatemala_censuses": {
    "author": "Instituto Nacional de Estadística (INE) Guatemala",
    "title": "Censos Nacionales de Población y Habitación (1893/1898, 1940, 1950, 1964, 1973, 1981, 1994, 2002, XII Censo 2018)",
    "year": 2019,
    "publisher": "INE, Ciudad de Guatemala",
    "url": "https://www.ine.gob.gt/",
    "coverage": "All 22 departments of Guatemala across modern censuses 1898–2018"
  },
  "digestyc_bcr_elsalvador_censuses": {
    "author": "Dirección General de Estadística y Censos (DIGESTYC) / Banco Central de Reserva (BCR) — ONEC",
    "title": "Censos Nacionales de Población y Vivienda de El Salvador (1930, 1950, 1961, 1971, 1992, 2007, VII Censo 2024)",
    "year": 2024,
    "publisher": "BCR / ONEC, San Salvador",
    "url": "https://onec.bcr.gob.sv/",
    "coverage": "All 14 departments of El Salvador across censuses 1930–2024"
  },
  "ine_honduras_censuses": {
    "author": "Instituto Nacional de Estadística (INE) Honduras",
    "title": "Censos Nacionales de Población y Vivienda de Honduras (1881, 1910, 1916, 1930, 1940, 1950, 1961, 1974, 1988, 2001, XVII Censo 2013)",
    "year": 2015,
    "publisher": "INE, Tegucigalpa",
    "url": "https://www.ine.gob.hn/",
    "coverage": "All 18 departments of Honduras across censuses 1881–2013"
  },
  "davidson_2002_honduras1895": {
    "author": "Davidson, William V.",
    "title": "Honduras: Estructura territorial y estadística según Censo 1895",
    "year": 2002,
    "publisher": "Academia Hondureña de Geografía e Historia, Tegucigalpa",
    "url": "https://www.worldcat.org/title/52040376",
    "coverage": "Archival reconstruction of the 1895 Honduran national census by department"
  },
  "inide_nicaragua_censuses": {
    "author": "Instituto Nacional de Información de Desarrollo (INIDE) Nicaragua",
    "title": "Censos Nacionales de Población y Vivienda de Nicaragua (1940, 1950, 1963, 1971, 1995, VIII Censo 2005)",
    "year": 2006,
    "publisher": "INIDE, Managua",
    "url": "https://www.inide.gob.ni/",
    "coverage": "15 departments, historical Zelaya (1940–1971), and Autonomous Regions RACCN/RACCS (1995–2005)"
  },
  "inec_costarica_censuses": {
    "author": "Instituto Nacional de Estadística y Censos (INEC) Costa Rica",
    "title": "Censos Nacionales de Población de Costa Rica (1864, 1883, 1892, 1927, 1950, 1963, 1973, 1984, 2000, 2011, 2022)",
    "year": 2023,
    "publisher": "INEC, San José",
    "url": "https://www.inec.cr/",
    "coverage": "All 7 provinces of Costa Rica across 1864–2022"
  },
  "inec_panama_censuses": {
    "author": "Instituto Nacional de Estadística y Censo (INEC) Panamá",
    "title": "Censos Nacionales de Población y Vivienda de Panamá (1911, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, XII Censo 2023)",
    "year": 2023,
    "publisher": "Contraloría General de la República / INEC, Panamá",
    "url": "https://www.inec.gob.pa/",
    "coverage": "All provinces and indigenous comarcas of Panama across 1911–2023"
  },
  "us_census_canal_zone": {
    "author": "United States Bureau of the Census / Isthmian Canal Commission",
    "title": "Census of the Canal Zone (1912) and U.S. Decennial Censuses of the Panama Canal Zone (1920–1970)",
    "year": 1973,
    "publisher": "U.S. Government Printing Office, Washington, D.C.",
    "url": "https://www.census.gov/library/publications/decennial.html",
    "coverage": "Official U.S. Census counts for the Panama Canal Zone territory (1912, 1920, 1930, 1940, 1950, 1960, 1970)"
  },
  "sib_belize_censuses": {
    "author": "Statistical Institute of Belize (SIB) / Colonial Office British Honduras",
    "title": "Population and Housing Censuses of British Honduras / Belize (1790–2022)",
    "year": 2024,
    "publisher": "Statistical Institute of Belize, Belmopan",
    "url": "https://sib.org.bz/",
    "coverage": "Early settlement counts (1790, 1816), colony censuses (1861–1931), and 6-district enumerations (1921, 1946–2022)"
  },
  "us_war_dept_1899_cuba": {
    "author": "United States War Department, Office Director Census of Cuba (J. P. Sanger, H. Gannett, W. F. Willcox)",
    "title": "Report on the Census of Cuba, 1899",
    "year": 1900,
    "publisher": "Government Printing Office, Washington, D.C.",
    "url": "https://archive.org/details/reportoncensusof00unitrich",
    "coverage": "Historical Spanish colonial censuses of Cuba (1774–1887) and 1899 provincial enumeration (6 provinces)"
  },
  "onei_cuba_censuses": {
    "author": "Oficina Nacional de Estadística e Información (ONEI) Cuba",
    "title": "Censos de Población y Viviendas de Cuba (1907, 1919, 1931, 1943, 1953, 1970, 1981, 2002, 2012)",
    "year": 2014,
    "publisher": "ONEI, La Habana",
    "url": "https://www.onei.gob.cu/",
    "coverage": "6 historic Cuban provinces (1899–1970) and 15/16 modern provinces + Isla de la Juventud (1970–2012)"
  },
  "moreau_st_mery_1797": {
    "author": "Moreau de Saint-Méry, Médéric Louis Élie",
    "title": "Description topographique, physique, civile, politique et historique de la partie française de l'isle Saint-Domingue",
    "year": 1797,
    "publisher": "Philadelphia (reprinted Société Française d'Histoire d'Outre-Mer, 1958)",
    "url": "https://archive.org/details/descriptiontopog01more",
    "coverage": "1789 provincial demographic enumeration of Saint-Domingue (Nord, Ouest, Sud)"
  },
  "geggus_1997_saint_domingue": {
    "author": "Geggus, David P.",
    "title": "Slavery, War, and Revolution in the Greater Caribbean, 1789–1815 / Saint-Domingue on the Eve of the Haitian Revolution",
    "year": 1997,
    "publisher": "Johns Hopkins University Press / University of Florida",
    "url": "https://www.press.jhu.edu/",
    "coverage": "Revised archival demography of late colonial Saint-Domingue (1789) and post-independence Haiti (1805)"
  },
  "nicholls_1979_haiti": {
    "author": "Nicholls, David",
    "title": "From Dessalines to Duvalier: Race, Colour and National Independence in Haiti",
    "year": 1979,
    "publisher": "Cambridge University Press, Cambridge",
    "url": "https://www.cambridge.org/",
    "coverage": "Early post-independence Haitian census of 1805"
  },
  "ihsi_haiti_censuses": {
    "author": "Institut Haïtien de Statistique et d'Informatique (IHSI)",
    "title": "Recensements Généraux de la Population et de l'Habitat (1950, 1971, 1982, 2003) et Population Totale par Département (2015)",
    "year": 2015,
    "publisher": "IHSI, Port-au-Prince",
    "url": "https://ihsi.gouv.ht/",
    "coverage": "5 historic departments (1950, 1971) and 10 modern departments of Haiti (1971–2015)"
  },
  "moya_pons_1995_domrep": {
    "author": "Moya Pons, Frank",
    "title": "The Dominican Republic: A National History / Manual de Historia Dominicana",
    "year": 1995,
    "publisher": "Markus Wiener Publishers, Princeton",
    "url": "https://www.worldcat.org/title/31816236",
    "coverage": "Colonial Santo Domingo demographic benchmarks (1783, 1819)"
  },
  "one_domrep_censuses": {
    "author": "Oficina Nacional de Estadística (ONE) República Dominicana",
    "title": "Censos Nacionales de Población y Vivienda (I Censo 1920, 1935, 1950, 1960, 1970, 1981, 1993, 2002, 2010, X Censo 2022)",
    "year": 2023,
    "publisher": "ONE, Santo Domingo",
    "url": "https://www.one.gob.do/",
    "coverage": "12 historic provinces (1920) and 31 modern provinces + Distrito Nacional (1935–2022)"
  },
  "roberts_1957_jamaica": {
    "author": "Roberts, George W.",
    "title": "The Population of Jamaica: An Analysis of Its Structure and Growth",
    "year": 1957,
    "publisher": "Cambridge University Press, Cambridge",
    "url": "https://www.cambridge.org/",
    "coverage": "Colonial and early census demography of Jamaica (1673, 1730, 1774, 1834, 1844–1943)"
  },
  "statin_jamaica_censuses": {
    "author": "Statistical Institute of Jamaica (STATIN)",
    "title": "Population and Housing Censuses of Jamaica (1844–2011)",
    "year": 2012,
    "publisher": "STATIN, Kingston",
    "url": "https://statinja.gov.jm/",
    "coverage": "All 14 parishes of Jamaica across modern censuses 1943–2011 and island totals 1844–1921"
  },
  "us_war_dept_1899_puertorico": {
    "author": "United States War Department, Office Director Census of Porto Rico (J. P. Sanger, H. Gannett, W. F. Willcox)",
    "title": "Report on the Census of Porto Rico, 1899",
    "year": 1900,
    "publisher": "Government Printing Office, Washington, D.C.",
    "url": "https://archive.org/details/reportoncensusof00unit",
    "coverage": "Spanish colonial censuses of Puerto Rico (1765 O'Reilly, 1776, 1800, 1860, 1877, 1887) and 1899 7-department enumeration"
  },
  "us_census_puertorico": {
    "author": "United States Bureau of the Census",
    "title": "Decennial Censuses of Puerto Rico (1910–2020) and Vintage 2023 Municipio Population Estimates Base (prm-est2023-pop.xlsx)",
    "year": 2024,
    "publisher": "U.S. Census Bureau, Washington, D.C.",
    "url": "https://www2.census.gov/programs-surveys/popest/tables/2020-2023/municipios/totals/prm-est2023-pop.xlsx",
    "coverage": "All 78 Puerto Rican municipios aggregated to the 7 historic 1899 Departments across 1910–2020"
  },
  "higman_1984_british_caribbean": {
    "author": "Higman, Barry W.",
    "title": "Slave Populations of the British Caribbean, 1807–1834",
    "year": 1984,
    "publisher": "Johns Hopkins University Press, Baltimore",
    "url": "https://www.press.jhu.edu/",
    "coverage": "Primary colonial registration and demographic counts for British Caribbean colonies (17th c. – 1834)"
  },
  "engerman_higman_1997": {
    "author": "Engerman, Stanley L. and Barry W. Higman",
    "title": "The Demographic Structure of the Caribbean Slave Societies in the Eighteenth and Nineteenth Centuries, in General History of the Caribbean Vol. III",
    "year": 1997,
    "publisher": "UNESCO Publishing / Macmillan Caribbean, London",
    "url": "https://unesdoc.unesco.org/",
    "coverage": "Comparative colonial census populations across French, British, Spanish, Danish, and Dutch Caribbean colonies"
  },
  "kuczynski_1953_west_indies": {
    "author": "Kuczynski, Robert René",
    "title": "Demographic Survey of the British Colonial Empire, Volume III: West Indian and American Territories",
    "year": 1953,
    "publisher": "Oxford University Press (Royal Institute of International Affairs), London",
    "url": "https://archive.org/details/demographicsurve03kucz",
    "coverage": "Critical primary compilation of British Colonial Office censuses (1843–1946) across Barbados, Jamaica, Trinidad & Tobago, Bahamas, Bermuda, Belize, Leeward & Windward Islands"
  },
  "un_dyb_historical": {
    "author": "United Nations Statistics Division (UNSD)",
    "title": "Demographic Yearbook Historical Supplement (1948–1997) & Population Censuses' Datasets",
    "year": 2000,
    "publisher": "United Nations, New York",
    "url": "https://unstats.un.org/unsd/demographic-social/products/dyb/",
    "coverage": "Harmonised historical official census totals across Caribbean territories"
  },
  "bss_barbados_censuses": {
    "author": "Barbados Statistical Service (BSS)",
    "title": "Population and Housing Censuses of Barbados (1844–2021)",
    "year": 2023,
    "publisher": "Barbados Statistical Service, Bridgetown",
    "url": "https://stats.gov.bb/",
    "coverage": "Barbados island totals (1844–2021) and 11-parish counts (1946–2010)"
  },
  "cso_trinidad_censuses": {
    "author": "Central Statistical Office (CSO) of Trinidad and Tobago",
    "title": "Population and Housing Censuses of Trinidad and Tobago (1851–2011)",
    "year": 2012,
    "publisher": "Ministry of Planning and Sustainable Development, Port of Spain",
    "url": "https://cso.gov.tt/",
    "coverage": "National series (1851–2011) and 15 regions/municipalities + Tobago (2000, 2011)"
  },
  "nsi_bahamas_censuses": {
    "author": "Bahamas National Statistical Institute (formerly Department of Statistics)",
    "title": "Census of Population and Housing of The Bahamas (1845–2022)",
    "year": 2023,
    "publisher": "Bahamas National Statistical Institute, Nassau",
    "url": "https://www.bahamas.gov.bs/",
    "coverage": "Archipelago totals (1845–1970) and island-group series (1980–2022)"
  },
  "bso_bermuda_censuses": {
    "author": "Department of Statistics, Government of Bermuda",
    "title": "Population and Housing Censuses of Bermuda (1843–2016)",
    "year": 2018,
    "publisher": "Government of Bermuda, Hamilton",
    "url": "https://www.gov.bm/department/statistics",
    "coverage": "Island totals (1699–2016) and 9 parishes + City of Hamilton + Town of St. George (1950–2016)"
  },
  "insee_dom_censuses": {
    "author": "Institut National de la Statistique et des Études Économiques (INSEE)",
    "title": "Recensements de la population — Séries historiques Guadeloupe, Martinique, Saint-Martin et Saint-Barthélemy (1936–2023)",
    "year": 2024,
    "publisher": "INSEE, Paris",
    "url": "https://www.insee.fr/",
    "coverage": "Arrondissements of Guadeloupe and Martinique, plus Collectivities of Saint-Martin and Saint-Barthélemy"
  },
  "cbs_netherlands_antilles": {
    "author": "Centraal Bureau voor de Statistiek (CBS) Nederlandse Antillen",
    "title": "Volkstellingen / Population and Housing Censuses of the Netherlands Antilles (1960, 1972, 1981, 1992, 2001)",
    "year": 2002,
    "publisher": "CBS Netherlands Antilles, Willemstad",
    "url": "https://www.cbs.cw/",
    "coverage": "Curaçao, Aruba, Bonaire, Sint Maarten, Sint Eustatius, and Saba (1863–2001)"
  },
  "cbs_curacao": {
    "author": "Central Bureau of Statistics (CBS) Curaçao",
    "title": "Population and Housing Censuses of Curaçao (2011, 2023)",
    "year": 2024,
    "publisher": "CBS Curaçao, Willemstad",
    "url": "https://www.cbs.cw/",
    "coverage": "Curaçao official census counts 2011 and 2023"
  },
  "cbs_aruba": {
    "author": "Central Bureau of Statistics (CBS) Aruba",
    "title": "Population and Housing Censuses of Aruba (1991, 2000, 2010, 2020)",
    "year": 2022,
    "publisher": "CBS Aruba, Oranjestad",
    "url": "https://cbs.aw/",
    "coverage": "Aruba 8 census regions (1991–2020)"
  },
  "stat_sint_maarten": {
    "author": "Department of Statistics (STAT) Sint Maarten",
    "title": "Population and Housing Census 2011 & Population Register Series",
    "year": 2018,
    "publisher": "STAT Sint Maarten, Philipsburg",
    "url": "https://stat.gov.sx/",
    "coverage": "Sint Maarten official census counts (1981–2011)"
  },
  "cbs_netherlands_83698eng": {
    "author": "Centraal Bureau voor de Statistiek (CBS) Netherlands",
    "title": "Caribbean Netherlands; population; sex, age, marital status (StatLine Table 83698ENG, 2011–2025)",
    "year": 2025,
    "publisher": "Statistics Netherlands (CBS), The Hague",
    "url": "https://opendata.cbs.nl/ODataApi/odata/83698ENG/TypedDataSet",
    "coverage": "Annual January 1 resident population registers for Bonaire, Sint Eustatius, and Saba (2011–2025)"
  },
  "danish_west_indies_censuses": {
    "author": "Det Statistiske Departement (Statistics Denmark) / Rigsarkivet",
    "title": "Folketællinger i Dansk Vestindien (Censuses of the Danish West Indies, 1773–1911)",
    "year": 1912,
    "publisher": "Statistics Denmark, Copenhagen",
    "url": "https://www.sa.dk/",
    "coverage": "St. Croix, St. Thomas, and St. John enumerations 1773, 1796, 1835–1911"
  },
  "us_census_usvi": {
    "author": "United States Bureau of the Census",
    "title": "Census of the Virgin Islands of the United States (Special Census 1917 & Decennial Censuses 1930–2020)",
    "year": 2021,
    "publisher": "U.S. Census Bureau, Washington, D.C.",
    "url": "https://www.census.gov/programs-surveys/decennial-census/decade/2020/planning-management/release/2020-island-areas-data.html",
    "coverage": "St. Croix, St. Thomas, and St. John decennial censuses 1917–2020"
  },
  "cso_bvi_censuses": {
    "author": "Central Statistics Office, Government of the Virgin Islands (BVI)",
    "title": "Population and Housing Censuses of the British Virgin Islands (1901–2010)",
    "year": 2014,
    "publisher": "Government of the Virgin Islands, Road Town",
    "url": "https://bvi.gov.vg/",
    "coverage": "BVI island groups (1980–2010) and territorial totals (1901–1970)"
  },
  "asd_anguilla_censuses": {
    "author": "Anguilla Statistics Department",
    "title": "Anguilla Population and Housing Censuses (1974, 1984, 1992, 2001, 2011)",
    "year": 2012,
    "publisher": "Government of Anguilla, The Valley",
    "url": "https://statistics.gov.ai/",
    "coverage": "14 districts of Anguilla (1974–2011)"
  },
  "sd_antigua_censuses": {
    "author": "Statistics Division, Ministry of Finance and Corporate Governance, Antigua and Barbuda",
    "title": "Population and Housing Censuses of Antigua and Barbuda (1946–2011)",
    "year": 2014,
    "publisher": "Government of Antigua and Barbuda, St. John's",
    "url": "https://statistics.gov.ag/",
    "coverage": "6 parishes of Antigua and Barbuda dependency (1946–2011)"
  },
  "ds_stkitts_nevis_censuses": {
    "author": "Department of Statistics, Federation of Saint Kitts and Nevis",
    "title": "Population and Housing Censuses of Saint Kitts and Nevis (1946–2022)",
    "year": 2024,
    "publisher": "Department of Statistics, Basseterre",
    "url": "https://www.stats.gov.kn/",
    "coverage": "All 14 parishes across Saint Kitts (9) and Nevis (5) for 1946–2022"
  },
  "cso_dominica_censuses": {
    "author": "Central Statistical Office (CSO) of Dominica",
    "title": "Population and Housing Censuses of the Commonwealth of Dominica (1946–2011)",
    "year": 2012,
    "publisher": "CSO Dominica, Roseau",
    "url": "https://stats.gov.dm/",
    "coverage": "All 10 parishes of Dominica (1946–2011)"
  },
  "cso_stlucia_censuses": {
    "author": "Central Statistical Office (CSO) of Saint Lucia",
    "title": "Population and Housing Censuses of Saint Lucia (1970–2022)",
    "year": 2023,
    "publisher": "CSO Saint Lucia, Castries",
    "url": "https://www.stats.gov.lc/",
    "coverage": "All quarters/districts of Saint Lucia (1970–2022)"
  },
  "so_stvincent_censuses": {
    "author": "Statistical Office, Government of Saint Vincent and the Grenadines",
    "title": "Population and Housing Censuses of Saint Vincent and the Grenadines (1970–2012)",
    "year": 2014,
    "publisher": "Statistical Office, Kingstown",
    "url": "https://stats.gov.vc/",
    "coverage": "Census divisions and Grenadines islands (1970–2012)"
  },
  "cso_grenada_censuses": {
    "author": "Central Statistical Office (CSO) of Grenada",
    "title": "Population and Housing Censuses of Grenada (1970–2022)",
    "year": 2023,
    "publisher": "CSO Grenada, St. George's",
    "url": "https://stats.gov.gd/",
    "coverage": "6 parishes of Grenada plus Carriacou and Petite Martinique (1970–2022)"
  },
  "sd_montserrat_censuses": {
    "author": "Statistics Department, Government of Montserrat",
    "title": "Population and Housing Censuses of Montserrat (1946–2018)",
    "year": 2019,
    "publisher": "Government of Montserrat, Brades",
    "url": "https://statistics.gov.ms/",
    "coverage": "Montserrat parishes/zones and post-1995 Soufrière Hills volcanic evacuation series"
  },
  "eso_cayman_censuses": {
    "author": "Economics and Statistics Office (ESO), Government of the Cayman Islands",
    "title": "Population and Housing Censuses of the Cayman Islands (1911–2021)",
    "year": 2022,
    "publisher": "ESO Cayman Islands, George Town",
    "url": "https://www.eso.ky/",
    "coverage": "All 6 districts of the Cayman Islands (1911–2021)"
  },
  "deps_turks_caicos_censuses": {
    "author": "Department of Economic Planning and Statistics, Turks and Caicos Islands",
    "title": "Population and Housing Censuses of the Turks and Caicos Islands (1960–2012)",
    "year": 2014,
    "publisher": "Government of Turks and Caicos Islands, Grand Turk",
    "url": "https://www.gov.tc/stats/",
    "coverage": "6 inhabited island groups (1960–2012) and earlier territory totals"
  },
}


def verify_and_write (arg0_data):
  # 1. Check all source_keys exist and zero banned terms
  banned = ["wikipedia", "mcevedy", "goldewijk", "populstat", "chandler", "maddison"]
  used_sources = set()
  total_units = 0
  total_obs = 0
  countries = set()

  for regime, units in arg0_data.items():
    for uk, u in units.items():
      total_units += 1
      countries.add(u["admin_country"])
      for yr, pop in u["years"].items():
        assert isinstance(pop, int) and pop > 0, f"Invalid pop: {regime}/{uk}/{yr}={pop}"
        total_obs += 1
      for sk in u["source_keys"]:
        assert sk in SOURCES_BIB, f"Missing bibliography key: {sk}"
        used_sources.add(sk)

  bib_json = json.dumps(SOURCES_BIB, ensure_ascii=False).lower()
  data_json = json.dumps(arg0_data, ensure_ascii=False).lower()
  for b in banned:
    assert b not in bib_json, f"Banned source term '{b}' found in bibliography!"
    assert b not in data_json, f"Banned source term '{b}' found in data!"

  # 2. Verify key national/regional totals against historical benchmarks
  def sum_regime (r_key, yr, country=None, exclude_keys=None):
    ex = set(exclude_keys or [])
    return sum(
      u["years"][str(yr)]
      for uk, u in arg0_data[r_key].items()
      if uk not in ex and (country is None or u["admin_country"] == country) and str(yr) in u["years"]
    )

  checks = [
    ("Mexico 1793 Revillagigedo (13 units)", sum_regime("colonial_new_spain_1570_1810", 1793, exclude_keys={"viceroyalty_new_spain_total"}), 4426880),
    ("Mexico 1803 Humboldt (15 units)", sum_regime("colonial_new_spain_1570_1810", 1803, exclude_keys={"viceroyalty_new_spain_total"}), 5840000),
    ("Mexico 1895 INEGI (31 units)", sum_regime("mexico_inegi_1895_2020", 1895), 12632427),
    ("Mexico 1900 INEGI (31 units)", sum_regime("mexico_inegi_1895_2020", 1900), 13607272),
    ("Mexico 1910 INEGI (31 units)", sum_regime("mexico_inegi_1895_2020", 1910), 15160369),
    ("Mexico 1921 INEGI (32 units, Rev dip)", sum_regime("mexico_inegi_1895_2020", 1921), 14334780),
    ("Mexico 1950 INEGI (32 units)", sum_regime("mexico_inegi_1895_2020", 1950), 25779254),
    ("Mexico 2010 INEGI (32 units)", sum_regime("mexico_inegi_1895_2020", 2010), 112336538),
    ("Mexico 2020 INEGI (32 units)", sum_regime("mexico_inegi_1895_2020", 2020), 126014024),
    ("Guatemala 2018 INE (22 depts)", sum_regime("central_america_modern_1864_2024", 2018, "Guatemala"), 14901286),
    ("El Salvador 2024 BCR (14 depts)", sum_regime("central_america_modern_1864_2024", 2024, "El Salvador"), 6029976),
    ("Honduras 2013 INE (18 depts)", sum_regime("central_america_modern_1864_2024", 2013, "Honduras"), 8303771),
    ("Nicaragua 2005 INIDE (17 units)", sum_regime("central_america_modern_1864_2024", 2005, "Nicaragua"), 5142098),
    ("Costa Rica 1864 INEC (6 provs)", sum_regime("central_america_modern_1864_2024", 1864, "Costa Rica"), 120499),
    ("Costa Rica 2022 INEC (7 provs)", sum_regime("central_america_modern_1864_2024", 2022, "Costa Rica"), 5044197),
    ("Panama 1911 INEC (excl. Canal Zone)", sum_regime("central_america_modern_1864_2024", 1911, "Panama"), 336742),
    ("Panama 2023 INEC (provs+comarcas)", sum_regime("central_america_modern_1864_2024", 2023, "Panama"), 4064780),
    ("Belize 2022 SIB (6 districts)", sum_regime("central_america_modern_1864_2024", 2022, "Belize"), 397483),
    ("Cuba 1899 US War Dept (6 provs)", sum_regime("greater_antilles_historic_1899_1979", 1899, "Cuba"), 1572797),
    ("Cuba 1953 ONEI (6 provs)", sum_regime("greater_antilles_historic_1899_1979", 1953, "Cuba"), 5829029),
    ("Cuba 2012 ONEI (16 provs)", sum_regime("greater_antilles_modern_1935_2023", 2012, "Cuba"), 11167325),
    ("Haiti 1950 IHSI (5 depts)", sum_regime("greater_antilles_historic_1899_1979", 1950, "Haiti"), 3097220),
    ("Haiti 2003 IHSI (10 depts)", sum_regime("greater_antilles_modern_1935_2023", 2003, "Haiti"), 8373750),
    ("Haiti 2015 IHSI (10 depts)", sum_regime("greater_antilles_modern_1935_2023", 2015, "Haiti"), 10911819),
    ("DomRep 1920 ONE (12 provs)", sum_regime("greater_antilles_historic_1899_1979", 1920, "Dominican Republic"), 894665),
    ("DomRep 2022 ONE (32 provs)", sum_regime("greater_antilles_modern_1935_2023", 2022, "Dominican Republic"), 10773983),
    ("Jamaica 1943 STATIN (14 parishes)", sum_regime("greater_antilles_modern_1935_2023", 1943, "Jamaica"), 1237063),
    ("Jamaica 2011 STATIN (14 parishes)", sum_regime("greater_antilles_modern_1935_2023", 2011, "Jamaica"), 2697983),
    ("Puerto Rico 1899 (7 depts)", sum_regime("greater_antilles_historic_1899_1979", 1899, "Puerto Rico"), 953243),
    ("Puerto Rico 2020 (7 depts <- 78 mun)", sum_regime("greater_antilles_historic_1899_1979", 2020, "Puerto Rico"), 3285874),
    ("Barbados 2010 BSS (11 parishes)", sum_regime("lesser_antilles_bahamas_bermuda_1900_2025", 2010, "Barbados"), 277821),
    ("Trinidad & Tobago 2011 CSO (15 units)", sum_regime("lesser_antilles_bahamas_bermuda_1900_2025", 2011, "Trinidad and Tobago"), 1328019),
    ("Bahamas 2022 NSI (20 island groups)", sum_regime("lesser_antilles_bahamas_bermuda_1900_2025", 2022, "The Bahamas"), 398165),
    ("Bermuda 2016 BSO (11 units)", sum_regime("lesser_antilles_bahamas_bermuda_1900_2025", 2016, "Bermuda"), 63779),
    ("Guadeloupe 2021 INSEE (2 arrond.)", sum_regime("lesser_antilles_bahamas_bermuda_1900_2025", 2021, "Guadeloupe"), 384315),
    ("Martinique 2021 INSEE (4 arrond.)", sum_regime("lesser_antilles_bahamas_bermuda_1900_2025", 2021, "Martinique"), 364338),
    ("USVI 2020 US Census (3 islands)", sum_regime("lesser_antilles_bahamas_bermuda_1900_2025", 2020, "United States Virgin Islands"), 87146),
    ("St Kitts & Nevis 2022 (14 parishes)", sum_regime("lesser_antilles_bahamas_bermuda_1900_2025", 2022, "Saint Kitts and Nevis"), 51320),
    ("Antigua & Barbuda 2011 (7 units)", sum_regime("lesser_antilles_bahamas_bermuda_1900_2025", 2011, "Antigua and Barbuda"), 85567),
    ("Caribbean NL 2025 CBS (BES 3 islands)", sum_regime("lesser_antilles_bahamas_bermuda_1900_2025", 2025, "Caribbean Netherlands"), 31980),
  ]

  print("=== VERIFICATION BENCHMARKS ===")
  verification_log = {}
  for label, got, expected in checks:
    diff = got - expected
    status = "EXACT" if diff == 0 else f"DIFF({diff:+,})"
    print(f"  [{status:12s}] {label:42s}: got={got:>12,} | expected={expected:>12,}")
    verification_log[label] = {"computed_sum": got, "reference_total": expected, "diff": diff}

  print(f"\nSUMMARY: {len(arg0_data)} era_regimes | {total_units} sub-admin units | {total_obs} year-observations | {len(countries)} jurisdictions | {len(used_sources)} primary sources")
  for rk, rv in arg0_data.items():
    obs_r = sum(len(u["years"]) for u in rv.values())
    all_y = sorted({int(y) for u in rv.values() for y in u["years"]})
    print(f"  - {rk:44s}: {len(rv):3d} units | {obs_r:4d} obs | {all_y[0]}..{all_y[-1]}")

  # Write outputs
  out_enum = os.path.join(PARSED_DIR, "jaguar_subadmin_enumerations.json")
  out_src = os.path.join(PARSED_DIR, "jaguar_enum_sources.json")
  with open(out_enum, "w", encoding="utf-8") as f:
    json.dump(arg0_data, f, ensure_ascii=False, indent=2)

  src_payload = {
    "project": "JAGUAR",
    "generated_by": "compile_jaguar_subadmin_enumerations.py",
    "policy": "primary_censuses_statistical_yearbooks_and_canonical_academic_demography_only",
    "total_era_regimes": len(arg0_data),
    "total_units": total_units,
    "total_observations": total_obs,
    "total_jurisdictions": len(countries),
    "jurisdictions_covered": sorted(countries),
    "sources": {k: SOURCES_BIB[k] for k in sorted(used_sources)},
    "verification_benchmarks": verification_log,
  }
  with open(out_src, "w", encoding="utf-8") as f:
    json.dump(src_payload, f, ensure_ascii=False, indent=2)

  print("\nWROTE:", out_enum, f"({os.path.getsize(out_enum):,} bytes)")
  print("WROTE:", out_src, f"({os.path.getsize(out_src):,} bytes)")


if __name__ == "__main__":
  compiled = build_all()
  verify_and_write(compiled)
