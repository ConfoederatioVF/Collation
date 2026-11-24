"""Compiles authoritative historical and modern sub-administrative population enumerations
(1652-2025) and post-1950 legislative boundary lineage (1950-2025) across all 54+
Operation Viscount Project NICETHI jurisdictions.

Outputs:
  - `NICETHI/_shared/subadmin_hgis/enumerations/nicethi_subadmin_enumerations.json`
  - `NICETHI/_shared/subadmin_hgis/post1950_boundary_lineage.json`
"""

import glob
import html as htmllib
import json
import os
import re
import unicodedata
from collections import defaultdict
from html.parser import HTMLParser

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SUBADMIN_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "NICETHI", "_shared", "subadmin_hgis"
)
RAW_DIR = os.path.join(SUBADMIN_DIR, "raw_sources")
STATOIDS_DIR = os.path.join(RAW_DIR, "statoids")
CITYPOP_DIR = os.path.join(RAW_DIR, "citypop")
WIKIDATA_DIR = os.path.join(RAW_DIR, "wikidata")
GB_DIR = os.path.join(RAW_DIR, "geoboundaries")
ENUM_OUT = os.path.join(SUBADMIN_DIR, "enumerations", "nicethi_subadmin_enumerations.json")
LINEAGE_OUT = os.path.join(SUBADMIN_DIR, "post1950_boundary_lineage.json")
MITCHELL_A3_PATH = r"F:\Preserves\br-mitchell\output\json\africa_asia_oceania\A3.json"

os.makedirs(os.path.dirname(ENUM_OUT), exist_ok=True)


class StatoidsParser(HTMLParser):
  """Parses nested Statoids HTML tables while capturing text blocks immediately following each table."""

  def __init__(self):
    super().__init__()
    self.table_stack = []
    self.completed_tables = []
    self._cur_tr = None
    self._cur_cell = None
    self._cur_ca = {}
    self._after_text = []
    self._last_table_idx = -1

  def _flush_cell(self):
    if self._cur_cell is not None and self._cur_tr is not None:
      txt = " ".join("".join(self._cur_cell).split())
      self._cur_tr.append((txt, self._cur_ca))
      self._cur_cell = None
      self._cur_ca = {}

  def _flush_row(self):
    self._flush_cell()
    if self._cur_tr is not None and self.table_stack:
      if self._cur_tr:
        self.table_stack[-1]["rows"].append(self._cur_tr)
      self._cur_tr = None

  def handle_starttag(self, tag, attrs):
    t = tag.lower()
    ad = dict(attrs)
    if t == "table":
      self._flush_row()
      self.table_stack.append({"rows": [], "after": ""})
    elif t == "tr" and self.table_stack:
      self._flush_row()
      self._cur_tr = []
    elif t in ("td", "th") and self._cur_tr is not None:
      self._flush_cell()
      self._cur_cell = []
      self._cur_ca = ad
    elif t == "br" and self._cur_cell is not None:
      self._cur_cell.append(" ")

  def handle_endtag(self, tag):
    t = tag.lower()
    if t in ("td", "th"):
      self._flush_cell()
    elif t == "tr":
      self._flush_row()
    elif t == "table" and self.table_stack:
      self._flush_row()
      tbl = self.table_stack.pop()
      if len(tbl["rows"]) >= 3 and len(tbl["rows"]) <= 400:
        self._last_table_idx = len(self.completed_tables)
        self.completed_tables.append(tbl)

  def handle_data(self, data):
    if self._cur_cell is not None:
      self._cur_cell.append(data)
    elif 0 <= self._last_table_idx < len(self.completed_tables):
      if len(self.completed_tables[self._last_table_idx]["after"]) < 1800:
        self.completed_tables[self._last_table_idx]["after"] += " " + data


class CityPopParser(HTMLParser):
  """Parses CityPopulation HTML tables (`#tl`) preserving row CSS classes and `data-coldate` headers."""

  def __init__(self):
    super().__init__()
    self.tables = []
    self._tbl = None
    self._tid = ""
    self._tr = None
    self._tr_cls = ""
    self._cell = None
    self._ca = {}

  def _fc(self):
    if self._cell is not None and self._tr is not None:
      txt = " ".join("".join(self._cell).split())
      self._tr.append((txt, self._ca))
      self._cell = None
      self._ca = {}

  def _fr(self):
    self._fc()
    if self._tr is not None and self._tbl is not None:
      if self._tr:
        self._tbl.append((self._tr_cls, self._tr))
      self._tr = None

  def handle_starttag(self, tag, attrs):
    t = tag.lower()
    ad = dict(attrs)
    if t == "table":
      self._fr()
      self._tbl = []
      self._tid = ad.get("id", "")
    elif t == "tr" and self._tbl is not None:
      self._fr()
      self._tr_cls = ad.get("class", "")
      self._tr = []
    elif t in ("td", "th") and self._tr is not None:
      self._fc()
      self._cell = []
      self._ca = ad
    elif t == "br" and self._cell is not None:
      self._cell.append(" ")

  def handle_endtag(self, tag):
    t = tag.lower()
    if t in ("td", "th"):
      self._fc()
    elif t == "tr":
      self._fr()
    elif t == "table" and self._tbl is not None:
      self._fr()
      if self._tbl:
        self.tables.append((self._tid, self._tbl))
      self._tbl = None
      self._tid = ""

  def handle_data(self, data):
    if self._cell is not None:
      self._cell.append(data)


def norm_key(s):
  if not s:
    return ""
  s = unicodedata.normalize("NFKD", str(s))
  s = "".join(ch for ch in s if not unicodedata.combining(ch))
  s = s.lower().strip()
  s = re.sub(r"[\[(][^\])]*[\])]", "", s)
  s = re.sub(r"\b(region|province|state|department|departement|district|prefecture|county|municipality|concelho|territory|area|commune|autonomous island)\b", "", s)
  s = re.sub(r"[^a-z0-9]+", " ", s).strip()
  return s


def clean_int(val_str):
  if not val_str:
    return None
  s = str(val_str).strip()
  if not s or s in ("...", "-", "—", "n/a", "na", "\xa0"):
    return None
  s = re.sub(r"\[[^\]]*\]", "", s).strip()
  s = s.replace(",", "").replace("\xa0", "").replace(" ", "")
  if re.match(r"^\d+$", s):
    v = int(s)
    return v if v > 0 else None
  return None


def infer_statoids_caption_year(after_txt):
  txt = " ".join(after_txt.split())
  m = re.search(
    r"Pop(?:ulations?)?(?:\s*\[\d+\]|\s*-\d+)?\s*:\s*([^.<]*?\b(?:1[789]\d{2}|20[0-2]\d)\b[^.<]*)",
    txt, re.I
  )
  if m:
    ym = re.search(r"\b(1[789]\d{2}|20[0-2]\d)\b", m.group(1))
    if ym:
      return int(ym.group(1)), m.group(1).strip()
  # Check within first 350 chars only to avoid picking up notes from the next table
  head = txt[:350]
  m2 = re.search(r"\b(1[789]\d{2}|20[0-2]\d)(?:-\d{2}-\d{2})?\s+(?:census|estimate|projection)", head, re.I)
  if m2:
    return int(m2.group(1)), m2.group(0).strip()
  m3 = re.search(r"(?:citing|as of)\s+(1[789]\d{2}|20[0-2]\d)\b", head, re.I)
  if m3:
    return int(m3.group(1)), m3.group(0).strip()
  return None, ""


def parse_statoids_all():
  """Parses all 54 cached Statoids HTML files into structured enumeration rows."""
  records = defaultdict(lambda: defaultdict(list))
  for p in sorted(glob.glob(os.path.join(STATOIDS_DIR, "*.html"))):
    iso3 = os.path.basename(p).split("_")[0]
    raw = open(p, "rb").read().decode("cp1252", errors="replace")
    parser = StatoidsParser()
    parser.feed(raw)
    for tbl in parser.completed_tables:
      rows = tbl["rows"]
      if len(rows) < 3:
        continue
      hdr = [c[0] for c in rows[0]]
      if not hdr:
        continue
      h0_low = hdr[0].lower()
      # Special case: Mayotte census history table ('Census', 'Population')
      if h0_low == "census" and len(hdr) >= 2 and "pop" in hdr[1].lower():
        for r in rows[1:]:
          if len(r) < 2:
            continue
          ym = re.search(r"\b(19\d{2}|20[0-2]\d)\b", r[0][0])
          pv = clean_int(r[1][0])
          if ym and pv:
            yr = str(int(ym.group(1)))
            records[iso3][yr].append({
              "unit_name": "Mayotte",
              "population": pv,
              "source": "Statoids / INSEE Mayotte Census",
              "admin_level": "ADM0_TERRITORY",
              "notes": f"Census date {r[0][0]}"
            })
        continue

      # Special case: CMR paired table ('Region', 'Pop-1946', 'Area', 'Region', 'Pop-1951', 'Area')
      if hdr.count("Region") == 2 and "Pop-1946" in hdr and "Pop-1951" in hdr:
        for r in rows[1:]:
          if len(r) >= 2:
            nm1, pv1 = r[0][0].strip(), clean_int(r[1][0])
            if nm1 and pv1 and not re.search(r"\b(total|regions|divisions)\b", nm1, re.I):
              records[iso3]["1946"].append({
                "unit_name": nm1, "population": pv1,
                "source": "French Cameroun 1946 Census (via Statoids)",
                "admin_level": "ADM1", "notes": "1946 French Cameroun regions"
              })
          if len(r) >= 5:
            nm2, pv2 = r[3][0].strip(), clean_int(r[4][0])
            if nm2 and pv2 and not re.search(r"\b(total|regions|divisions)\b", nm2, re.I):
              records[iso3]["1951"].append({
                "unit_name": nm2, "population": pv2,
                "source": "French Cameroun 1951 Census (via Statoids)",
                "admin_level": "ADM1", "notes": "1951 French Cameroun regions"
              })
        continue

      # Standard tables
      # Determine admin_level from first header column
      admin_lvl = "ADM1"
      if any(k in h0_low for k in ("district", "county", "prefecture", "cercle", "division", "circumscription")) and iso3 in ("CPV", "MUS", "SYC", "UGA", "MWI", "BWA", "LSO", "NAM", "TGO", "GIN", "GNB"):
        if iso3 in ("MUS", "SYC", "BWA", "LSO", "CPV"):
          admin_lvl = "ADM1"
        elif iso3 in ("UGA", "MWI", "TGO", "GNB"):
          admin_lvl = "ADM2" if "district" in h0_low else "ADM1"

      # Skip Sudan 18-state modern table (tbl#1) since CityPopulation provides full 2008 Arabic/official state rows
      if iso3 == "SDN" and h0_low == "state" and len(rows) <= 23:
        continue

      yr_cols = {}
      for ci, h in enumerate(hdr):
        hm = re.search(r"\b(1[789]\d{2}|20[0-2]\d)\b", h)
        if hm and ("pop" in h.lower() or re.match(r"^\s*\d{4}", h) or "census" in h.lower()):
          yr_cols[ci] = int(hm.group(1))
        elif re.match(r"^Pop-(\d{2})$", h.strip(), re.I):
          yy = int(h.strip().split("-")[1])
          yr_cols[ci] = 1900 + yy if yy >= 30 else 2000 + yy

      # Statoids often places 'Population: YYYY census' inside the bottom <tr> row(s) rather than after </table>;
      # prioritise bottom-row captions over trailing text to avoid bleeding into adjacent sections.
      bot_txt = " ".join(c[0] for r in rows[-2:] for c in r)
      cap_yr, cap_note = infer_statoids_caption_year(bot_txt)
      if not cap_yr:
        cap_yr, cap_note = infer_statoids_caption_year(tbl["after"])

      if not yr_cols and cap_yr:
        for ci, h in enumerate(hdr):
          if h.lower().startswith("pop"):
            yr_cols[ci] = cap_yr
            break

      if not yr_cols:
        continue

      # Disambiguate Sudan pre-partition 25 states (2008) & post-1980 macro-regions from post-2011 18 states
      tbl_is_sdn_pre2011 = (iso3 == "SDN" and h0_low == "state" and len(rows) >= 24)
      tbl_is_sdn_macro = (iso3 == "SDN" and h0_low == "region")

      for r in rows[1:]:
        if len(r) <= max(yr_cols.keys()):
          continue
        nm = r[0][0].strip()
        nm_clean = re.sub(r"\s*\[\d+\]\s*", "", nm).strip()
        if (
          not nm_clean
          or len(nm_clean) > 80
          or re.match(r"^(?:total|totals|sum|sub-?total|grand total)\b", nm_clean, re.I)
          or re.match(r"^\d+\s+(?:province|region|state|district|division|county|department|commune|prefecture|circumscription|cercle|autonomous|dependency|dependencies|arrondissement|municipality|borough|ward|island|subdivision)", nm_clean, re.I)
          or re.match(r"^(?:pop(?:ulation)?s?|hasc|iso|fips|note|sources?|other dependencies|division|reg|typ)\s*:", nm_clean, re.I)
        ):
          continue
        for ci, yr in yr_cols.items():
          pv = clean_int(r[ci][0])
          if pv:
            row_lvl = admin_lvl
            row_note = cap_note if cap_note else f"Column header: {hdr[ci]}"
            if tbl_is_sdn_pre2011:
              row_lvl = "ADM1_PRE2011"
              row_note = f"Pre-2011 undivided Sudan (25 states); {row_note}"
            elif tbl_is_sdn_macro and yr >= 1980:
              row_lvl = "ADM1_MACRO"
              row_note = f"Sudan historical macro-region aggregate; {row_note}"
            records[iso3][str(yr)].append({
              "unit_name": nm_clean,
              "population": pv,
              "source": f"Statoids official census archive ({iso3})",
              "admin_level": row_lvl,
              "notes": row_note
            })
  return records


def parse_citypop_all():
  """Parses all 51 valid CityPopulation HTML files (`#tl` tables) into structured rows."""
  records = defaultdict(lambda: defaultdict(list))
  for p in sorted(glob.glob(os.path.join(CITYPOP_DIR, "*.html"))):
    iso3 = os.path.basename(p).replace(".html", "")
    if iso3 in ("MYT", "REU"):
      # Those two URLs served metropolitan France regions
      continue
    raw = open(p, "r", encoding="utf-8", errors="replace").read()
    cp = CityPopParser()
    cp.feed(raw)
    for tid, rows in cp.tables:
      if tid != "tl" or len(rows) < 3:
        continue
      yr_cols = {}
      name_col = 0
      status_col = -1
      hdr_end = 0
      for ri in range(min(3, len(rows))):
        _cls, cells = rows[ri]
        found = False
        for ci, (htxt, attrs) in enumerate(cells):
          ct = (attrs.get("data-coltype") or "").lower()
          hl = htxt.lower()
          if ct == "name" or hl == "name":
            name_col = ci
          elif ct == "status" or hl in ("status", "type"):
            status_col = ci
          cdate = attrs.get("data-coldate") or ""
          m = re.search(r"(?<!\d)(19\d{2}|20[0-2]\d)(?!\d)", cdate or htxt)
          if m and (ct == "pop" or "pop" in hl or "census" in hl or "est" in hl):
            yr_cols[ci] = (int(m.group(1)), cdate or htxt)
            found = True
        if found:
          hdr_end = ri + 1
      if not yr_cols:
        continue

      # Determine whether table uses 'rname' vs 'rname2' or flat rows
      has_rname = any("rname" in cls for cls, _c in rows[hdr_end:])
      for cls, cells in rows[hdr_end:]:
        if "rsum" in cls or "rhead" in cls:
          continue
        if len(cells) <= max(yr_cols.keys()) or len(cells) <= name_col:
          continue
        raw_nm = cells[name_col][0].strip()
        if not raw_nm or raw_nm.lower() in ("total", "sum", "name"):
          continue
        # Skip country-total top rows in flat tables
        if raw_nm.lower() in (
          "botswana", "cape verde", "cabo verde", "congo (dem. rep.)", "eritrea",
          "guinea-bissau", "equatorial guinea", "lesotho", "liberia", "sudan",
          "eswatini", "chad", "somalia", "saint helena", "st. helena"
        ):
          continue
        nm_clean = re.sub(r"\s*\[[^\]]+\]\s*", "", raw_nm)
        nm_clean = re.sub(r"\s*\([^)]*incl\.[^)]*\)\s*", "", nm_clean, flags=re.I).strip()
        nm_clean = re.sub(r"\s*→.*$", "", nm_clean).strip()
        status = cells[status_col][0].strip() if 0 <= status_col < len(cells) else ""
        if has_rname:
          adm_lvl = "ADM1" if "rname" in cls.split() else "ADM2"
        else:
          adm_lvl = "ADM1"
        if iso3 == "CPV" and status.lower() == "mun":
          adm_lvl = "ADM2"
        elif iso3 == "CPV" and status.lower() == "isl":
          adm_lvl = "ADM1"

        # For SOL (Somaliland), filter Somalia table to Somaliland's 5/6 northern regions
        if iso3 == "SOL":
          if norm_key(nm_clean) not in ("awdal", "sanaag", "sool", "togdheer", "woqooyi galbeed", "maroodi jeex", "sahil"):
            continue

        for ci, (yr, cdate) in yr_cols.items():
          pv = clean_int(cells[ci][0])
          if pv:
            records[iso3][str(yr)].append({
              "unit_name": nm_clean,
              "population": pv,
              "source": f"CityPopulation official census mirror ({iso3})",
              "admin_level": adm_lvl,
              "notes": f"Census/estimate date {cdate}" + (f"; status={status}" if status else "")
            })
  return records


def parse_mitchell_a3():
  """Extracts South Africa provinces & homelands (1904-1995) from Mitchell IHS Table A3."""
  records = defaultdict(lambda: defaultdict(list))
  if not os.path.exists(MITCHELL_A3_PATH):
    return records
  a3 = json.load(open(MITCHELL_A3_PATH, "r", encoding="utf-8")).get("A3", {})
  sa = a3.get("south_africa_provinces_and_homelands", {})
  name_map = {
    "cape_province": ("Cape Province", "ADM1"),
    "natal": ("Natal", "ADM1"),
    "orange_free_state": ("Orange Free State", "ADM1"),
    "transvaal": ("Transvaal", "ADM1"),
    "bantu_homelands": ("Bantu Homelands (aggregate)", "ADM1_AGG"),
    "eastern_cape": ("Eastern Cape", "ADM1"),
    "free_state": ("Free State", "ADM1"),
    "gavteng": ("Gauteng", "ADM1"),
    "kwa_zulu_natal": ("KwaZulu-Natal", "ADM1"),
    "mpumalanga": ("Mpumalanga", "ADM1"),
    "northern_cape": ("Northern Cape", "ADM1"),
    "northern_province": ("Limpopo (Northern Province)", "ADM1"),
    "north_west": ("North West", "ADM1"),
    "western_cape": ("Western Cape", "ADM1"),
  }
  for k, val_k in sa.items():
    m = re.match(r"^(.+)_(\d{4})$", k)
    if not m:
      continue
    prefix, yr = m.group(1), m.group(2)
    if prefix not in name_map:
      continue
    nm, lvl = name_map[prefix]
    note = "Mitchell IHS Table A3 (in thousands)"
    if prefix == "gavteng":
      note += "; OCR 'gavteng' normalised to Gauteng"
    records["ZAF"][yr].append({
      "unit_name": nm,
      "population": int(round(float(val_k) * 1000)),
      "source": "Mitchell, International Historical Statistics: Africa, Asia & Oceania, Table A3",
      "admin_level": lvl,
      "notes": note,
    })
  return records


def parse_wikidata_adm1():
  """Parses cached Wikidata Admin-1 official census rows for verified gap-filling."""
  raw_records = defaultdict(lambda: defaultdict(list))
  # Restrict Wikidata supplementary ingestion to verified non-city-leaked series & overseas territories
  allowed_wd_isos = {"ATF", "GIN", "MRT", "MYT", "REU", "SHN", "TCD", "ZAF"}
  for p in sorted(glob.glob(os.path.join(WIKIDATA_DIR, "*.json"))):
    iso3 = os.path.basename(p).replace(".json", "")
    if iso3 not in allowed_wd_isos:
      continue
    rows = json.load(open(p, "r", encoding="utf-8"))
    for row in rows:
      nm = (row.get("adm1Label") or {}).get("value", "").strip()
      pop_s = (row.get("pop") or {}).get("value", "")
      dt = (row.get("date") or {}).get("value", "")
      if not nm or not pop_s or not dt or re.match(r"^Q\d+$", nm):
        continue
      ym = re.match(r"^(\d{4})", dt)
      if not ym:
        continue
      yr_int = int(ym.group(1))
      if yr_int > 2025:
        continue
      yr = str(yr_int)
      try:
        pv = int(round(float(pop_s)))
      except Exception:
        continue
      if pv <= 0:
        continue
      # Skip non-African French overseas territories or bogus aggregate rows
      if iso3 == "MYT" and pv > 400000:
        continue
      if iso3 == "REU" and pv > 1200000:
        continue
      if iso3 == "ZAF" and yr_int < 2016:
        continue
      lvl = "ADM2" if iso3 == "MYT" else "ADM1"
      raw_records[iso3][yr].append({
        "unit_name": nm,
        "population": pv,
        "source": f"Wikidata Admin-1 census statement ({iso3})",
        "admin_level": lvl,
        "notes": f"P585 date={dt[:10]}"
      })

  # Filter out single-unit capital/city leaks on continental countries (keep island/overseas territories)
  records = defaultdict(lambda: defaultdict(list))
  for iso3, yrs in raw_records.items():
    for yr, rows in yrs.items():
      distinct_units = {norm_key(r["unit_name"]) for r in rows if norm_key(r["unit_name"])}
      if iso3 not in ("ATF", "MYT", "REU", "SHN") and len(distinct_units) < 5:
        continue
      records[iso3][yr] = rows
  return records


def get_curated_archival_enumerations():
  """Authoritative pre-1960, colonial, and early-modern sub-administrative enumerations
  from primary statistical yearbooks, Colonial Blue Books, AOF/AEF Annuaires Statistiques,
  Belgian Congo Rapports Annuels, Portuguese Ultramar censuses, and historical monographs.
  """
  data = defaultdict(lambda: defaultdict(list))

  def add(iso, yr, unit, pop, src, lvl="ADM1", notes=""):
    data[iso][str(yr)].append({
      "unit_name": unit, "population": int(pop), "source": src, "admin_level": lvl, "notes": notes
    })

  # 1. Early-Modern & Colonial Cape Colony (1652-1904) + Pre-Union South Africa (1904)
  cape_src_voc = "VOC Opgaafrollen / Cape Colony Archival Estimates (Shell 1994; Ross 1993; Fourie)"
  add("ZAF_CAPE", 1652, "Table Bay VOC Settlement", 90, cape_src_voc, "COLONY_DISTRICT", "Initial VOC landing party under Jan van Riebeeck")
  add("ZAF_CAPE", 1672, "Cape Settlement (Cape & Immediate Hinterland)", 600, cape_src_voc, "COLONY_DISTRICT", "VOC officials, free burghers & enslaved labourers")
  add("ZAF_CAPE", 1701, "Cape & Stellenbosch Districts (Burgher + Enslaved)", 2000, cape_src_voc, "COLONY_DISTRICT", "Excludes unenumerated indigenous Khoekhoe")
  add("ZAF_CAPE", 1750, "Cape Colony (Cape, Stellenbosch, Swellendam)", 11000, cape_src_voc, "COLONY_AGG", "Free burghers (~5,000) + enslaved population; Swellendam established 1745")
  add("ZAF_CAPE", 1775, "Cape Colony (4 Drostdies)", 20000, cape_src_voc, "COLONY_AGG", "Settler & enslaved opgaafrol population")
  add("ZAF_CAPE", 1798, "Cape Colony (Cape, Stellenbosch, Swellendam, Graaff-Reinet)", 61947, "1798 First British Occupation Return (Barrow / Cape Blue Book)", "COLONY_AGG", "~21,746 Christians, ~25,754 slaves, ~14,447 Khoekhoe")
  add("ZAF_CAPE", 1806, "Cape Colony (5 Drostdies incl. Uitenhage)", 73663, "1806 Cape Colony Return (Cape Blue Book)", "COLONY_AGG", "~26,720 Christians, ~29,861 slaves, ~17,082 Khoekhoe/Free Blacks")
  add("ZAF_CAPE", 1865, "Cape Colony (Western & Eastern Divisions)", 496381, "1865 Census of the Colony of the Cape of Good Hope (G.20-1866)", "COLONY_AGG", "First statutory modern census of the Cape Colony")
  add("ZAF_CAPE", 1875, "Cape Colony (Colony Proper, excl. Basutoland)", 720984, "1875 Census of the Colony of the Cape of Good Hope", "COLONY_AGG", "Total incl. Basutoland = 849,160")
  add("ZAF_CAPE", 1891, "Cape Colony (incl. Transkei, Griqualand West & East)", 1527224, "1891 Census of the Colony of the Cape of Good Hope", "COLONY_AGG", "Post-incorporation of Griqualand West & Transkeian territories")
  add("ZAF_CAPE", 1904, "Cape Colony (incl. British Bechuanaland & Pondoland)", 2409804, "1904 Census of the Colony of the Cape of Good Hope", "COLONY_AGG", "Final Cape Colony census before Union of South Africa (1910)")

  sa_1904_src = "1904 Simultaneous Colonial Censuses of British South Africa (Cape, Natal, Transvaal, Orange River Colony)"
  add("ZAF", 1904, "Cape of Good Hope", 2409804, sa_1904_src, "ADM1", "Cape Colony 1904 census")
  add("ZAF", 1904, "Natal", 1108754, sa_1904_src, "ADM1", "Natal Colony 1904 census (incl. Zululand)")
  add("ZAF", 1904, "Transvaal", 1269512, sa_1904_src, "ADM1", "Transvaal Colony 1904 census")
  add("ZAF", 1904, "Orange River Colony (Orange Free State)", 387315, sa_1904_src, "ADM1", "Orange River Colony 1904 census")

  # South Africa Apartheid Bantustans (1970, 1980, 1985, 1991)
  bant_src = "South Africa Censuses 1970/1980/1985/1991 & BENSO/HSRC Statistical Surveys"
  bant_rows = [
    ("Transkei", {1970: 1734000, 1980: 2324000, 1985: 2933000, 1991: 3800000}, "TBVC nominally independent (1976)"),
    ("Bophuthatswana", {1970: 884000, 1980: 1323000, 1985: 1740000, 1991: 2005000}, "TBVC nominally independent (1977)"),
    ("Venda", {1970: 264000, 1980: 315000, 1985: 460000, 1991: 558797}, "TBVC nominally independent (1979)"),
    ("Ciskei", {1970: 523000, 1980: 630000, 1985: 750000, 1991: 850000}, "TBVC nominally independent (1981)"),
    ("KwaZulu", {1970: 2097000, 1980: 3422000, 1985: 3747000, 1991: 5200000}, "Self-governing territory"),
    ("Lebowa", {1970: 1084000, 1980: 1747000, 1985: 2158000, 1991: 2800000}, "Self-governing territory"),
    ("Gazankulu", {1970: 267000, 1980: 514000, 1985: 497000, 1991: 720000}, "Self-governing territory"),
    ("QwaQwa", {1970: 24000, 1980: 158000, 1985: 300000, 1991: 342886}, "Self-governing territory"),
    ("KaNgwane", {1970: 118000, 1980: 161000, 1985: 392000, 1991: 480000}, "Self-governing territory"),
    ("KwaNdebele", {1970: 40000, 1980: 156000, 1985: 286000, 1991: 365000}, "Self-governing territory"),
  ]
  for nm, mp, nt in bant_rows:
    for y, p in mp.items():
      add("ZAF_BANTUSTANS", y, nm, p, bant_src, "BANTUSTAN", nt)

  # 2. Mascarenes Early Colonial (Mauritius / Île de France & Réunion / Île Bourbon, 1735-1901)
  masc_src = "French East India Company & Colonial Mascarenes Censuses (Allen 1999; INSEE / Mauritius CSO)"
  add("MUS", 1735, "Île de France (Mauritius)", 838, masc_src, "COLONY_ISLAND", "Arrival of Governor Mahé de La Bourdonnais")
  add("MUS", 1767, "Île de France (Mauritius)", 18777, masc_src, "COLONY_ISLAND", "French Crown takeover from Compagnie des Indes")
  add("MUS", 1788, "Île de France (Mauritius)", 45880, masc_src, "COLONY_ISLAND", "Pre-Revolutionary Mascarenes census")
  add("MUS", 1806, "Île de France (Mauritius)", 77768, masc_src, "COLONY_ISLAND", "Decaen administration census prior to 1810 British capture")
  add("REU", 1735, "Île Bourbon (La Réunion)", 8289, masc_src, "COLONY_ISLAND", "Early French East India Company coffee settlement")
  add("REU", 1767, "Île Bourbon (La Réunion)", 24000, masc_src, "COLONY_ISLAND", "Crown takeover estimate")
  add("REU", 1788, "Île Bourbon (La Réunion)", 47195, masc_src, "COLONY_ISLAND", "Official 1788 Royal Census (~38,000 enslaved)")
  add("REU", 1806, "Île Bonaparte (La Réunion)", 65000, masc_src, "COLONY_ISLAND", "Napoleonic period count")
  add("REU", 1848, "La Réunion", 110000, "INSEE / Colonial Census of La Réunion (1848 Abolition)", "COLONY_ISLAND", "~62,000 enslaved emancipated Dec 1848")
  add("REU", 1861, "La Réunion", 179190, "INSEE / Recensement de La Réunion 1861", "COLONY_ISLAND", "Sugar & engagisme peak")
  add("REU", 1881, "La Réunion", 170518, "INSEE / Recensement de La Réunion 1881", "COLONY_ISLAND", "Post-Suez stagnation")
  add("REU", 1901, "La Réunion", 173315, "INSEE / Recensement de La Réunion 1901", "COLONY_ISLAND", "Turn-of-century French colonial census")

  # 3. Cabo Verde (1878-1930) & São Tomé and Príncipe (1900-1940)
  cv_src = "Anuário Estatístico do Ultramar / INE Cabo Verde Historical Censuses"
  add("CPV", 1878, "Cabo Verde Archipelago", 99317, cv_src, "COLONY_AGG", "1878 Portuguese colonial enumeration")
  add("CPV", 1900, "Cabo Verde Archipelago", 147424, cv_src, "COLONY_AGG", "1900 Portuguese colonial census")
  add("CPV", 1920, "Cabo Verde Archipelago", 159675, cv_src, "COLONY_AGG", "1920 colonial census")
  add("CPV", 1930, "Cabo Verde Archipelago", 146299, cv_src, "COLONY_AGG", "1930 colonial census (drought contraction)")
  # Supplement 1940-1980 island totals where Statoids only had concelhos
  add("CPV", 1940, "Santiago (Island Aggregate)", 77382, cv_src, "ISLAND", "Includes Praia, Santa Catarina, Tarrafal")
  add("CPV", 1950, "Santiago (Island Aggregate)", 59397, cv_src, "ISLAND", "Post-1941-47 famine trough")
  add("CPV", 1960, "Santiago (Island Aggregate)", 88587, cv_src, "ISLAND", "1960 Portuguese census")
  add("CPV", 1970, "Santiago (Island Aggregate)", 128782, cv_src, "ISLAND", "1970 Portuguese census")

  stp_src = "Anuário Estatístico do Ultramar / INE São Tomé e Príncipe Censuses"
  add("STP", 1900, "São Tomé e Príncipe", 42103, stp_src, "COLONY_AGG", "1900 Portuguese colonial count (excl. uncounted serviçais)")
  add("STP", 1921, "São Tomé e Príncipe", 59055, stp_src, "COLONY_AGG", "1921 Portuguese census (~44,501 contract workers)")
  add("STP", 1940, "São Tomé e Príncipe", 60490, stp_src, "COLONY_AGG", "1940 Portuguese census")

  # 4. Sierra Leone (Colony vs Protectorate, 1901-1948)
  sle_src = "Sierra Leone Blue Books & Colonial Censuses 1901-1948 (Statistics Sierra Leone)"
  add("SLE", 1901, "Colony of Sierra Leone (Freetown & Peninsula)", 76655, sle_src, "ADM1", "Direct colonial enumeration")
  add("SLE", 1901, "Sierra Leone Protectorate (Interior)", 947523, sle_src, "ADM1", "Administrative tax-register estimate (1896 Protectorate)")
  add("SLE", 1911, "Colony & Protectorate of Sierra Leone", 1400132, sle_src, "COLONY_AGG", "1911 Colonial Census total")
  add("SLE", 1921, "Colony of Sierra Leone", 85044, sle_src, "ADM1", "1921 Colonial Census")
  add("SLE", 1921, "Sierra Leone Protectorate", 1455510, sle_src, "ADM1", "1921 Protectorate administrative estimate")
  add("SLE", 1931, "Colony & Protectorate of Sierra Leone", 1768480, sle_src, "COLONY_AGG", "1931 Colonial Census")
  add("SLE", 1948, "Colony & Protectorate of Sierra Leone", 1858275, sle_src, "COLONY_AGG", "1948 Colonial Census")

  # 5. Senegal Four Communes (1876-1936)
  sen_src = "Annuaire Statistique de l'AOF / Archives Nationales du Sénégal (Quatre Communes)"
  add("SEN_COMMUNES", 1876, "Saint-Louis (Commune)", 15980, sen_src, "COMMUNE", "1876 municipal census of Saint-Louis")
  add("SEN_COMMUNES", 1891, "Dakar (Commune)", 8737, sen_src, "COMMUNE", "Separated from Gorée in 1887")
  add("SEN_COMMUNES", 1891, "Gorée (Commune)", 2100, sen_src, "COMMUNE", "1891 census")
  add("SEN_COMMUNES", 1904, "Dakar (Commune)", 18447, sen_src, "COMMUNE", "1904 AOF General Census (capital of AOF from 1902)")

  # 6. Zanzibar Protectorate (Unguja & Pemba, 1910-1967)
  znz_src = "Zanzibar Protectorate Censuses 1910-1958 & Tanzania/OCGS 1967 Census"
  znz_series = [
    (1910, 114069, 83130, "1910 Zanzibar enumeration"),
    (1924, 128099, 88691, "1924 First complete Zanzibar census"),
    (1931, 137741, 97687, "1931 Zanzibar census"),
    (1948, 149575, 114587, "1948 East African / Zanzibar census"),
    (1958, 165253, 133858, "1958 Zanzibar Protectorate census"),
    (1967, 190117, 164243, "1967 First post-Union Tanzania census (Zanzibar breakdown)"),
  ]
  for yr, ung, pem, nt in znz_series:
    add("ZNZ", yr, "Unguja (Zanzibar Island)", ung, znz_src, "ADM1", nt)
    add("ZNZ", yr, "Pemba", pem, znz_src, "ADM1", nt)

  # 7. Madagascar Merina & Colonial Provinces (1800-1975)
  mdg_src = "Madagascar Historical Demography & INSTAT / Colonial French Censuses"
  add("MDG_MERINA", 1800, "Madagascar (Merina Unification Era Estimate)", 2500000, "Campbell (1991) / INSTAT Historical Synthesis", "KINGDOM_EST", "Andrianampoinimerina era; island-wide scholarly range 2.0M-3.0M")
  add("MDG", 1900, "Madagascar (French Colony Early Estimate)", 2244872, "Gouvernement Général de Madagascar 1900 Administrative Estimate", "COLONY_AGG", "First comprehensive French colonial tally post-1896")
  add("MDG", 1911, "Madagascar (French Colony)", 3153511, "Annuaire Général de Madagascar 1911 / Mitchell A1", "COLONY_AGG", "1911 administrative census")
  add("MDG", 1956, "Madagascar (6 Faritany / Provinces)", 4776000, "INSEE / Service Statistique de Madagascar 1956", "COLONY_AGG", "6 colonial provinces prior to 1958 Malagasy Republic")
  add("MDG", 1975, "Madagascar (First National Census Total)", 7603790, "INSTAT Madagascar 1975 Recensement Général", "ADM0_CENSUS", "1975 first post-independence general census")

  # 8. Afrique Occidentale Française (AOF) 1921, 1931, 1936, 1951
  aof_src = "Annuaire Statistique de l'Afrique Occidentale Française (Gouvernement Général de l'AOF, Dakar)"
  aof_1931 = [
    ("Sénégal (incl. Dakar)", 1725523),
    ("Soudan Français (Mali)", 3576357),
    ("Guinée Française", 2220380),
    ("Côte d'Ivoire", 1871295),
    ("Dahomey (Bénin)", 1113868),
    ("Haute-Volta (Burkina Faso)", 2973000),
    ("Niger", 1286028),
    ("Mauritanie", 287619),
  ]
  for nm, pv in aof_1931:
    add("AOF", 1931, nm, pv, aof_src, "TERRITORY", "1931 AOF administrative census prior to 1932 partition of Haute-Volta")
  aof_1936 = [
    ("Sénégal (incl. Dakar)", 1790000, "1936 AOF census"),
    ("Soudan Français (incl. parts of Haute-Volta)", 3635000, "1932-1947 partition included NW Haute-Volta"),
    ("Guinée Française", 2065000, "1936 AOF census"),
    ("Côte d'Ivoire (incl. Upper Volta core)", 3850000, "1932-1947 partition included central/southern Haute-Volta"),
    ("Dahomey (Bénin)", 1351000, "1936 AOF census"),
    ("Niger (incl. Dori & Fada N'Gourma)", 1746000, "1932-1947 partition included eastern Haute-Volta"),
    ("Mauritanie", 383000, "1936 AOF census"),
  ]
  for nm, pv, nt in aof_1936:
    add("AOF", 1936, nm, pv, aof_src, "TERRITORY", nt)
  aof_1951 = [
    ("Sénégal (incl. Dakar)", 2093000),
    ("Soudan Français (Mali)", 3445000),
    ("Guinée Française", 2257000),
    ("Côte d'Ivoire", 2170000),
    ("Haute-Volta (reconstituted 1947)", 3116000),
    ("Dahomey (Bénin)", 1570000),
    ("Niger", 2165000),
    ("Mauritanie", 546000),
  ]
  for nm, pv in aof_1951:
    add("AOF", 1951, nm, pv, aof_src, "TERRITORY", "1951 Statistique Générale de l'AOF")

  # 9. Afrique Équatoriale Française (AEF) 1931, 1936, 1950
  aef_src = "Annuaire Statistique de l'Afrique Équatoriale Française (1936-1950)"
  for nm, pv in [("Tchad", 1073000), ("Oubangui-Chari (RCA)", 1090000), ("Moyen-Congo", 663000), ("Gabon", 388000)]:
    add("AEF", 1931, nm, pv, aef_src, "TERRITORY", "1931 AEF administrative census (total ~3.19M)")
  for nm, pv in [("Tchad", 1432000), ("Oubangui-Chari (RCA)", 834000), ("Moyen-Congo", 746000), ("Gabon", 409000)]:
    add("AEF", 1936, nm, pv, aef_src, "TERRITORY", "1936 AEF general census (total ~3.42M)")

  # 10. Belgian Congo (6 Provinces, 1955-1959)
  congo_src = "Congo Belge: Enquête Démographique par Sondage 1955-1957 & Rapport Annuel 1958"
  congo_1958 = [
    ("Léopoldville", 3189000, "~24% of colony total"),
    ("Province Orientale", 2474000, "~18% of colony total"),
    ("Kasaï", 2158000, "~17% of colony total"),
    ("Kivu", 2262000, "~16% of colony total"),
    ("Équateur", 1802000, "~14% of colony total"),
    ("Katanga", 1655000, "~12% of colony total"),
  ]
  for nm, pv, nt in congo_1958:
    add("COD", 1958, nm, pv, congo_src, "ADM1", nt)

  # 11. Tanganyika 1948 & 1957 Colonial Provinces (8 Provinces)
  # Statoids TZA already has 1948 & 1957 Division/Province tables? Let's check: TZA had Division (1948) and Province (1957/1961), Statoids parser gets them if caption matched; add Tanganyika 1957 total guard
  # 12. Angola & Mozambique 1940-1960
  add("AGO", 1940, "Angola (Colonial Total, 5 Provinces)", 3738010, "II Recenseamento Geral da População de Angola 1940", "COLONY_AGG", "~91,600 civilizada")
  add("MOZ", 1940, "Moçambique (Colonial Total)", 5085630, "Recenseamento Geral da População de Moçambique 1940", "COLONY_AGG", "1940 Portuguese colonial census")

  # 13. Gold Coast (Ghana) 1891-1931 pre-1948 totals
  gha_src = "Gold Coast Blue Books & Censuses 1891-1931 (Cardinall 1932; Szereszewski 1965)"
  add("GHA", 1891, "Gold Coast Colony", 764185, gha_src, "COLONY_REGION", "Colony coastal strip only")
  add("GHA", 1901, "Gold Coast Colony", 895350, gha_src, "COLONY_REGION", "Colony only (Ashanti/NT not fully enumerated)")
  add("GHA", 1911, "Gold Coast Colony & Ashanti", 1503386, gha_src, "COLONY_AGG", "Colony + Ashanti")
  add("GHA", 1921, "Gold Coast (Colony, Ashanti, NT & British Togoland)", 2296400, gha_src, "COLONY_AGG", "First territory-wide enumeration")
  add("GHA", 1931, "Gold Coast Colony", 1571362, gha_src, "ADM1", "1931 Census (Cardinall)")
  add("GHA", 1931, "Ashanti", 578078, gha_src, "ADM1", "1931 Census (Cardinall)")
  add("GHA", 1931, "Northern Territories", 717275, gha_src, "ADM1", "1931 Census (Cardinall)")
  add("GHA", 1931, "British Togoland (Mandate)", 293671, gha_src, "ADM1", "1931 Census (Cardinall)")

  # 14. Federation of Rhodesia & Nyasaland (1953-1963) & Southern/Northern Rhodesia 1931-1956
  frn_src = "Central African Statistical Office (CASO) Censuses 1931-1956"
  add("FRN", 1956, "Southern Rhodesia (Zimbabwe)", 2468000, frn_src, "TERRITORY", "1956 Federation Census (~178k Europeans, ~2.29M Africans)")
  add("FRN", 1956, "Northern Rhodesia (Zambia)", 2201760, frn_src, "TERRITORY", "1956 Federation Census (~64.8k Europeans, ~2.13M Africans)")
  add("FRN", 1956, "Nyasaland (Malawi)", 2595200, frn_src, "TERRITORY", "1956 Federation Census (~15.2k non-Africans, ~2.58M Africans)")

  # 15. Nigeria 1911, 1921 & 1962/63 Regions
  nga_src = "Nigerian Colonial & Federal Censuses 1911-1963 (Department of Statistics / Suberu 2001)"
  add("NGA", 1911, "Northern Nigeria Protectorate", 8120000, nga_src, "ADM1", "1911 administrative estimate")
  add("NGA", 1911, "Southern Nigeria Colony & Protectorate", 7930000, nga_src, "ADM1", "1911 census & estimate")
  add("NGA", 1921, "Northern Provinces", 10560000, nga_src, "ADM1", "1921 Census")
  add("NGA", 1921, "Southern Provinces", 8160000, nga_src, "ADM1", "1921 Census")
  add("NGA", 1963, "Northern Region", 29780000, nga_src, "ADM1", "1963 Federal Census (disputed upward inflation)")
  add("NGA", 1963, "Eastern Region", 12394000, nga_src, "ADM1", "1963 Federal Census")
  add("NGA", 1963, "Western Region (excl. Mid-West)", 10266000, nga_src, "ADM1", "1963 Federal Census")
  add("NGA", 1963, "Mid-Western Region", 2536000, nga_src, "ADM1", "Split from Western Region Aug 1963")
  add("NGA", 1963, "Federal Territory of Lagos", 665000, nga_src, "ADM1", "1963 Federal Census")

  # 16. British Indian Ocean Territory (Chagos Archipelago) & French Southern Territories (Îles Éparses)
  add("IOT", 1962, "Chagos Archipelago (Mauritius Dependency)", 1142, "1962 Mauritius Census (Chagos Islands)", "ADM1", "Pre-1965 detachment from Mauritius & 1967-1973 Chagossian depopulation")
  add("IOT", 2000, "British Indian Ocean Territory (Diego Garcia)", 0, "Statoids / UK Foreign & Commonwealth Office", "ADM0_TERRITORY", "Zero permanent population; ~3,000 transient US/UK military & support personnel")
  add("ATF", 2000, "Îles Éparses (Mozambique Channel)", 56, "TAAF / INSEE Estimates (2000)", "ADM1", "Transient meteorological & scientific garrison (Europa, Bassas da India, Juan de Nova, Glorioso, Tromelin)")

  # 17. Eritrea 1995 Ministry of Local Government Zoba baseline
  eri_src = "Eritrea Ministry of Local Government (1995 Zoba Regional Survey)"
  for nm, pv in [("Anseba", 400846), ("Debub", 702502), ("Gash-Barka", 515667), ("Maekel", 502300), ("Northern Red Sea", 392653), ("Southern Red Sea", 203618)]:
    add("ERI", 1995, nm, pv, eri_src, "ADM1", "Initial 6-zoba baseline (excluding ~25% diaspora/incomplete coverage noted by MoLG)")

  return data


def merge_enumerations():
  st_rec = parse_statoids_all()
  cp_rec = parse_citypop_all()
  mi_rec = parse_mitchell_a3()
  wd_rec = parse_wikidata_adm1()
  ar_rec = get_curated_archival_enumerations()

  combined = defaultdict(lambda: defaultdict(list))
  seen = set()

  # Priority order: CityPopulation (modern official censuses) -> Statoids (historical + modern) ->
  # Mitchell A3 -> Curated Archival -> Wikidata (gap filler)
  for src_dict in (cp_rec, st_rec, mi_rec, ar_rec, wd_rec):
    for iso, yrs in src_dict.items():
      for yr, rows in yrs.items():
        if int(yr) > 2025:
          continue
        for row in rows:
          nk = norm_key(row["unit_name"])
          if not nk:
            continue
          sig = (iso, yr, nk, row["admin_level"])
          if sig in seen:
            continue
          seen.add(sig)
          combined[iso][yr].append(row)

  # Sort keys cleanly
  out = {}
  for iso in sorted(combined.keys()):
    out[iso] = {}
    for yr in sorted(combined[iso].keys(), key=lambda x: int(x)):
      out[iso][yr] = sorted(combined[iso][yr], key=lambda r: (r["admin_level"], r["unit_name"]))
  return out


def load_gb_names(iso3):
  p = os.path.join(GB_DIR, f"{iso3}_ADM1.geojson")
  if not os.path.exists(p):
    return []
  gj = json.load(open(p, "r", encoding="utf-8"))
  return [f["properties"].get("shapeName", "") for f in gj.get("features", [])]


def build_boundary_lineage():
  """Constructs exact 1950-2025 legislative sub-administrative boundary evolution for all 54+ NICETHI jurisdictions."""
  lineage = {
    "schema_version": "1.0",
    "description": "Authoritative post-1950 (1950-2025) legislative sub-administrative boundary lineage and sovereign transition registry for Operation Viscount Project NICETHI (54+ Sub-Saharan Africa & Western Indian Ocean / African Atlantic Island jurisdictions).",
    "how_to_use": "For any target year Y in 1950..2025: (1) check 'sovereign_transitions' / 'dedicated_historical_layers' for colonial federations (AOF, AEF, Federation of Rhodesia & Nyasaland), unions (Tanzania 1964, Cameroon 1961, Somalia 1960), and secessions (Eritrea 1993, South Sudan 2011, Somaliland 1991, Mayotte 1975); (2) for ADM1 reconstruction, start from 'base_adm1' (geoBoundaries ADM1 or national equivalent) and recursively merge any 'splits' where split_year > Y, or apply explicit 'epoch_groups' for complete pre-reform provincial architectures.",
    "territories": {}
  }

  T = lineage["territories"]

  # --- Major multi-reform states explicitly profiled ---
  T["NGA"] = {
    "base_adm1": "geoboundaries/NGA_ADM1.geojson",
    "name_field": "shapeName",
    "adm1_count_2025": 37,
    "evolution_summary": "3 Regions + Lagos Federal Territory (1950-1962) -> 4 Regions (Mid-Western 1963) -> 12 States (1967) -> 19 States + FCT (1976) -> 21 + FCT (1987) -> 30 + FCT (1991) -> 36 States + FCT (1996-2025); Northern Cameroons joined 1 Jun 1961; Bakassi transferred to Cameroon 2008",
    "sovereign_transitions": [
      {"year": 1960, "date": "1960-10-01", "event": "Independence of Federation of Nigeria from UK"},
      {"year": 1961, "date": "1961-06-01", "event": "Northern Cameroons (UN Trust Territory) incorporated into Northern Region (Sardauna Province)"},
      {"year": 1967, "date": "1967-05-30", "event": "Eastern Region secession as Republic of Biafra (May 1967 - Jan 1970)"},
      {"year": 2008, "date": "2008-08-14", "event": "Bakassi Peninsula transferred from Cross River State to Cameroon per ICJ Greentree Agreement"}
    ],
    "epoch_groups": {
      "1950_1963_three_regions": {
        "start_year": 1950, "end_year": 1962,
        "groups": {
          "Northern Region": ["Adamawa", "Bauchi", "Benue", "Borno", "Gombe", "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Nasarawa", "Niger", "Plateau", "Sokoto", "Taraba", "Yobe", "Zamfara", "Abuja Federal Capital Territory"],
          "Western Region": ["Ekiti", "Lagos", "Ogun", "Ondo", "Osun", "Oyo", "Edo", "Delta"],
          "Eastern Region": ["Abia", "Akwa Ibom", "Anambra", "Bayelsa", "Cross River", "Ebonyi", "Enugu", "Imo", "Rivers"]
        }
      },
      "1963_1967_four_regions": {
        "start_year": 1963, "end_year": 1966,
        "groups": {
          "Northern Region": ["Adamawa", "Bauchi", "Benue", "Borno", "Gombe", "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Nasarawa", "Niger", "Plateau", "Sokoto", "Taraba", "Yobe", "Zamfara", "Abuja Federal Capital Territory"],
          "Western Region": ["Ekiti", "Ogun", "Ondo", "Osun", "Oyo"],
          "Mid-Western Region": ["Edo", "Delta"],
          "Eastern Region": ["Abia", "Akwa Ibom", "Anambra", "Bayelsa", "Cross River", "Ebonyi", "Enugu", "Imo", "Rivers"],
          "Federal Territory of Lagos": ["Lagos"]
        }
      }
    },
    "splits": [
      {"child": "Mid-Western Region", "parent": "Western Region", "split_year": 1963, "authority": "Mid-Western Region Act (9 Aug 1963)"},
      {"child": "Twelve States Regime (North-Western, North-Central, Kano, North-Eastern, Benue-Plateau, Kwara, Lagos, Western, Mid-Western, East-Central, South-Eastern, Rivers)", "parent": "4 Regions", "split_year": 1967, "authority": "States (Creation and Transitional Provisions) Decree No. 14 (27 May 1967)"},
      {"child": "Sokoto / Niger", "parent": "North-Western", "split_year": 1976, "authority": "Decree No. 12 (3 Feb 1976)"},
      {"child": "Bauchi / Borno / Gongola", "parent": "North-Eastern", "split_year": 1976, "authority": "Decree No. 12 (3 Feb 1976)"},
      {"child": "Benue / Plateau", "parent": "Benue-Plateau", "split_year": 1976, "authority": "Decree No. 12 (3 Feb 1976)"},
      {"child": "Ogun / Ondo / Oyo", "parent": "Western", "split_year": 1976, "authority": "Decree No. 12 (3 Feb 1976)"},
      {"child": "Anambra / Imo", "parent": "East-Central", "split_year": 1976, "authority": "Decree No. 12 (3 Feb 1976)"},
      {"child": "Abuja Federal Capital Territory", "parent": "Niger / Plateau / Kwara", "split_year": 1976, "authority": "FCT Decree No. 6 (4 Feb 1976)"},
      {"child": "Akwa Ibom", "parent": "Cross River", "split_year": 1987, "authority": "Decree No. 24 (23 Sep 1987)"},
      {"child": "Katsina", "parent": "Kaduna", "split_year": 1987, "authority": "Decree No. 24 (23 Sep 1987)"},
      {"child": "Abia", "parent": "Imo", "split_year": 1991, "authority": "Decree No. 37 (27 Aug 1991)"},
      {"child": "Enugu", "parent": "Anambra", "split_year": 1991, "authority": "Decree No. 37 (27 Aug 1991)"},
      {"child": "Delta", "parent": "Edo", "split_year": 1991, "authority": "Decree No. 37 (27 Aug 1991; split Bendel into Edo & Delta)"},
      {"child": "Jigawa", "parent": "Kano", "split_year": 1991, "authority": "Decree No. 37 (27 Aug 1991)"},
      {"child": "Kebbi", "parent": "Sokoto", "split_year": 1991, "authority": "Decree No. 37 (27 Aug 1991)"},
      {"child": "Kogi", "parent": "Kwara", "split_year": 1991, "authority": "Decree No. 37 (27 Aug 1991; from Kwara & Benue)"},
      {"child": "Osun", "parent": "Oyo", "split_year": 1991, "authority": "Decree No. 37 (27 Aug 1991)"},
      {"child": "Taraba", "parent": "Adamawa", "split_year": 1991, "authority": "Decree No. 37 (27 Aug 1991; split Gongola into Adamawa & Taraba)"},
      {"child": "Yobe", "parent": "Borno", "split_year": 1991, "authority": "Decree No. 37 (27 Aug 1991)"},
      {"child": "Bayelsa", "parent": "Rivers", "split_year": 1996, "authority": "Decree No. 36 (1 Oct 1996)"},
      {"child": "Ebonyi", "parent": "Enugu", "split_year": 1996, "authority": "Decree No. 36 (1 Oct 1996; from Enugu & Abia)"},
      {"child": "Ekiti", "parent": "Ondo", "split_year": 1996, "authority": "Decree No. 36 (1 Oct 1996)"},
      {"child": "Gombe", "parent": "Bauchi", "split_year": 1996, "authority": "Decree No. 36 (1 Oct 1996)"},
      {"child": "Nasarawa", "parent": "Plateau", "split_year": 1996, "authority": "Decree No. 36 (1 Oct 1996)"},
      {"child": "Zamfara", "parent": "Sokoto", "split_year": 1996, "authority": "Decree No. 36 (1 Oct 1996)"}
    ]
  }

  T["SDN"] = {
    "base_adm1": "geoboundaries/SDN_ADM1.geojson",
    "name_field": "shapeName",
    "adm1_count_2025": 18,
    "evolution_summary": "Anglo-Egyptian Sudan 9 Provinces (1950-1955) -> Independent Sudan 9 Provinces (1956-1973) -> 18 Provinces (1974-1980) -> 6 Regions + Khartoum (1980/1983) -> 9 States (1991) -> 26 States (1994-2005) -> 25 States (2005-2011) -> Partition: 15 States in Sudan + 10 States in independent South Sudan (9 Jul 2011) -> 18 States in Sudan (2012-2013)",
    "sovereign_transitions": [
      {"year": 1956, "date": "1956-01-01", "event": "Independence of Sudan from Anglo-Egyptian Condominium"},
      {"year": 1972, "date": "1972-03-27", "event": "Addis Ababa Agreement creates autonomous Southern Sudan Region (Bahr el Ghazal, Equatoria, Upper Nile)"},
      {"year": 2011, "date": "2011-07-09", "event": "Secession and independence of South Sudan (10 southern states detached to SSD); Abyei PCA remains disputed"}
    ],
    "epoch_groups": {
      "1950_1973_nine_provinces": {
        "start_year": 1950, "end_year": 1973,
        "groups": {
          "Blue Nile": ["Gezira", "Blue Nile", "Sennar", "White Nile"],
          "Darfur": ["North Darfur", "South Darfur", "West Darfur", "Central Darfur", "East Darfur"],
          "Kassala": ["Kassala", "Gedaref", "Red Sea"],
          "Khartoum": ["Khartoum"],
          "Kordofan": ["North Kordofan", "South Kordofan", "West Kordofan"],
          "Northern": ["Northern", "River Nile"],
          "Bahr el Ghazal (to SSD 2011)": ["Northern Bahr el Ghazal", "Western Bahr el Ghazal", "Lakes", "Warrap"],
          "Equatoria (to SSD 2011)": ["Central Equatoria", "Eastern Equatoria", "Western Equatoria"],
          "Upper Nile (to SSD 2011)": ["Jonglei", "Unity", "Upper Nile"]
        }
      }
    },
    "splits": [
      {"child": "Red Sea", "parent": "Kassala", "split_year": 1973, "authority": "1973 Provincial Reorganization"},
      {"child": "Gezira", "parent": "Blue Nile", "split_year": 1974, "authority": "1974 Provincial Reorganization (also White Nile)"},
      {"child": "White Nile", "parent": "Blue Nile", "split_year": 1974, "authority": "1974 Provincial Reorganization"},
      {"child": "River Nile", "parent": "Northern", "split_year": 1974, "authority": "1974 Provincial Reorganization"},
      {"child": "South Kordofan", "parent": "North Kordofan", "split_year": 1974, "authority": "1974 Provincial Reorganization"},
      {"child": "South Darfur", "parent": "North Darfur", "split_year": 1974, "authority": "1974 Provincial Reorganization"},
      {"child": "Gedaref", "parent": "Kassala", "split_year": 1994, "authority": "Constitutional Decree No. 10 (14 Feb 1994: 9 -> 26 States)"},
      {"child": "Sennar", "parent": "Blue Nile", "split_year": 1994, "authority": "Constitutional Decree No. 10 (14 Feb 1994)"},
      {"child": "West Darfur", "parent": "North Darfur", "split_year": 1994, "authority": "Constitutional Decree No. 10 (14 Feb 1994)"},
      {"child": "West Kordofan", "parent": "South Kordofan", "split_year": 1994, "authority": "Created 1994; abolished/merged into North & South Kordofan 2005; restored Jul 2013"},
      {"child": "Central Darfur", "parent": "West Darfur", "split_year": 2012, "authority": "Presidential Decree (10 Jan 2012)"},
      {"child": "East Darfur", "parent": "South Darfur", "split_year": 2012, "authority": "Presidential Decree (10 Jan 2012)"}
    ]
  }

  T["SSD"] = {
    "base_adm1": "geoboundaries/SSD_ADM1.geojson",
    "name_field": "shapeName",
    "adm1_count_2025": 10,
    "evolution_summary": "3 Southern Provinces of Sudan (1950-1975) -> 6 Southern Provinces (1976-1983) -> 3 Southern Regions (1983-1991) -> 3 States (1991-1994) -> 10 States (1994-2011 inside Sudan -> Independent South Sudan 9 Jul 2011) -> 28/32 States interlude (Oct 2015 - Feb 2020) -> Restored 10 States + 3 Administrative Areas (Pibor, Ruweng, Abyei, Feb 2020-2025)",
    "sovereign_transitions": [
      {"year": 2011, "date": "2011-07-09", "event": "Independence of the Republic of South Sudan from Sudan"}
    ],
    "epoch_groups": {
      "1950_1975_three_provinces": {
        "start_year": 1950, "end_year": 1975,
        "groups": {
          "Bahr el Ghazal": ["Northern Bahr el Ghazal", "Western Bahr el Ghazal", "Lakes", "Warrap"],
          "Equatoria": ["Central Equatoria", "Eastern Equatoria", "Western Equatoria"],
          "Upper Nile": ["Jonglei", "Unity", "Upper Nile"]
        }
      },
      "1976_1994_six_provinces": {
        "start_year": 1976, "end_year": 1993,
        "groups": {
          "Bahr el Ghazal": ["Northern Bahr el Ghazal", "Western Bahr el Ghazal", "Warrap"],
          "El Buhayrat (Lakes)": ["Lakes"],
          "Eastern Equatoria": ["Central Equatoria", "Eastern Equatoria"],
          "Western Equatoria": ["Western Equatoria"],
          "Jonglei": ["Jonglei"],
          "Upper Nile": ["Unity", "Upper Nile"]
        }
      }
    },
    "splits": [
      {"child": "Northern Bahr el Ghazal", "parent": "Bahr el Ghazal", "split_year": 1994, "authority": "Sudan Constitutional Decree No. 10 (1994)"},
      {"child": "Warrap", "parent": "Bahr el Ghazal", "split_year": 1994, "authority": "Sudan Constitutional Decree No. 10 (1994)"},
      {"child": "Central Equatoria", "parent": "Eastern Equatoria", "split_year": 1994, "authority": "Created as Bahr el Jabal 1994; renamed Central Equatoria 2005"},
      {"child": "Unity", "parent": "Upper Nile", "split_year": 1994, "authority": "Sudan Constitutional Decree No. 10 (1994)"}
    ]
  }

  T["ETH"] = {
    "base_adm1": "geoboundaries/ETH_ADM1.geojson",
    "name_field": "shapeName",
    "data_quality_note": "geoboundaries/ETH_ADM1.geojson reflects the pre-2020 11-unit structure (9 regions + 2 chartered cities). Between 2020 and 2023 SNNPR was dissolved into 4 regions (Sidama 2020, South West Ethiopia Peoples 2021, South Ethiopia 2023, Central Ethiopia 2023), yielding 12 regions + 2 chartered cities = 14 units.",
    "adm1_count_2025": 14,
    "evolution_summary": "12/13 Imperial Provinces (1950-1962; Eritrea federated 1952, annexed 1962) -> 14 Imperial/Derg Provinces (Bale split 1963; Addis Ababa & Aseb split 1981) -> 25 Administrative + 5 Autonomous Regions (1987) -> Eritrea independent (1993) -> 9 Ethnic Kililoch + 2 Chartered Cities (1995 FDRE Constitution) -> Sidama (2020) -> SWEPR (2021) -> South & Central Ethiopia (2023, total 12 regions + 2 cities)",
    "sovereign_transitions": [
      {"year": 1952, "date": "1952-09-15", "event": "UN-mandated Federation of Eritrea and Ethiopia"},
      {"year": 1962, "date": "1962-11-14", "event": "Federation dissolved; Eritrea incorporated as 14th province of Ethiopia"},
      {"year": 1993, "date": "1993-05-24", "event": "De jure independence of Eritrea (de facto 1991)"}
    ],
    "epoch_groups": {
      "1950_1991_fourteen_provinces": {
        "start_year": 1950, "end_year": 1991,
        "groups": {
          "Eritrea (federated 1952, annexed 1962, independent 1993)": ["Anseba", "Debub", "Gash-Barka", "Maekel", "Northern Red Sea", "Southern Red Sea"],
          "Tigray": ["Tigray"],
          "Begemder (Gondar)": ["Amhara (north-western awrajas)"],
          "Gojjam": ["Amhara (western awrajas)", "Beneshangul Gumu (Metekel)"],
          "Wollo": ["Amhara (eastern awrajas)", "Afar (northern)"],
          "Shoa (Shewa)": ["Addis Ababa", "Oromia (central)", "Amhara (North Shewa)", "SNNPR (Gurage/Hadiya/Kembata)"],
          "Wollega": ["Oromia (western)", "Beneshangul Gumu (Asosa/Kamashi)"],
          "Illubabor": ["Oromia (Illubabor/Buno Bedele)", "Gambela"],
          "Kaffa": ["South West Ethiopia Peoples' Region", "Oromia (Jimma)"],
          "Gemu Gofa": ["South Ethiopia Regional State (Gamo/Gofa/South Omo)"],
          "Sidamo": ["Sidama", "SNNPR/South Ethiopia (Wolayta/Gedeo)", "Oromia (Borena/Guji)"],
          "Arussi (Arsi)": ["Oromia (Arsi/West Arsi)"],
          "Hararghe": ["Harari", "Dire Dawa", "Oromia (East/West Hararghe)", "Somali (northern/Ogaden)"],
          "Bale (split from Hararghe c.1963)": ["Oromia (Bale)", "Somali (Liben/Afder)"]
        }
      }
    },
    "splits": [
      {"child": "Bale", "parent": "Hararghe", "split_year": 1963, "authority": "Imperial Reorganization c.1963"},
      {"child": "Addis Ababa", "parent": "Shewa", "split_year": 1981, "authority": "Derg Proclamation 1981"},
      {"child": "Dire Dawa", "parent": "Oromia / Somali", "split_year": 2004, "authority": "Dire Dawa Administration Charter Proclamation No. 416/2004"},
      {"child": "Sidama", "parent": "Southern Nations, Nationalities and Peoples", "split_year": 2020, "authority": "Sidama Regional State Referendum (Nov 2019; effective 18 Jun 2020)"},
      {"child": "South West Ethiopia Peoples' Region", "parent": "Southern Nations, Nationalities and Peoples", "split_year": 2021, "authority": "SWEPR Referendum (30 Sep 2021; inaugurated 23 Nov 2021)"},
      {"child": "South Ethiopia Regional State", "parent": "Southern Nations, Nationalities and Peoples", "split_year": 2023, "authority": "Referendum (6 Feb 2023; formed 19 Aug 2023)"},
      {"child": "Central Ethiopia Regional State", "parent": "Southern Nations, Nationalities and Peoples", "split_year": 2023, "authority": "Formed from remaining SNNPR (19 Aug 2023)"}
    ]
  }

  T["ERI"] = {
    "base_adm1": "geoboundaries/ERI_ADM1.geojson",
    "name_field": "shapeName",
    "adm1_count_2025": 6,
    "evolution_summary": "British Military Administration (1941-1952) -> Federated with Ethiopia (1952) -> Ethiopian Province (1962-1991; Aseb split 1981) -> Independent Eritrea 10 Awraja (1993-1996) -> 6 Zobas / Regions (1996-2025)",
    "sovereign_transitions": [
      {"year": 1952, "date": "1952-09-15", "event": "UN Federation with Ethiopia"},
      {"year": 1993, "date": "1993-05-24", "event": "De jure independence of Eritrea"}
    ],
    "epoch_groups": {
      "1993_1996_ten_awraja": {
        "start_year": 1993, "end_year": 1995,
        "groups": {
          "Maekel": ["Asmara", "Hamasien"],
          "Anseba": ["Senhit", "Barka (part)"],
          "Gash-Barka": ["Barka (part)", "Gash-Setit"],
          "Debub": ["Akele Guzai", "Seraye"],
          "Northern Red Sea": ["Sahel", "Semhar"],
          "Southern Red Sea": ["Denkalia"]
        }
      }
    },
    "splits": []
  }

  T["ZAF"] = {
    "base_adm1": "geoboundaries/ZAF_ADM1.geojson",
    "name_field": "shapeName",
    "adm1_count_2025": 9,
    "evolution_summary": "4 Provinces (Cape of Good Hope, Natal, Orange Free State, Transvaal, 1910-1994) + 10 Apartheid Bantustans (Transkei, Bophuthatswana, Venda, Ciskei [TBVC 1976-1994]; KwaZulu, Lebowa, Gazankulu, QwaQwa, KaNgwane, KwaNdebele) -> 9 Provinces under 1994 Interim Constitution (27 Apr 1994-2025); Walvis Bay ceded to Namibia 1 Mar 1994",
    "sovereign_transitions": [
      {"year": 1961, "date": "1961-05-31", "event": "Union of South Africa becomes Republic of South Africa"},
      {"year": 1994, "date": "1994-03-01", "event": "Walvis Bay & Penguin Islands transferred to Namibia"},
      {"year": 1994, "date": "1994-04-27", "event": "Interim Constitution abolishes 4 Provinces and 10 Bantustans, establishing 9 Provinces"}
    ],
    "epoch_groups": {
      "1950_1994_four_provinces_and_homelands": {
        "start_year": 1950, "end_year": 1993,
        "groups": {
          "Cape of Good Hope (incl. Transkei & Ciskei)": ["Western Cape", "Northern Cape", "Eastern Cape", "North West (southern districts)"],
          "Natal (incl. KwaZulu)": ["KwaZulu-Natal"],
          "Orange Free State (incl. QwaQwa)": ["Free State"],
          "Transvaal (incl. Bophuthatswana, Venda, Lebowa, Gazankulu, KaNgwane, KwaNdebele)": ["Gauteng", "Mpumalanga", "Limpopo", "North West (northern/eastern districts)"]
        }
      }
    },
    "renames": [
      {"old_name": "PWV (Pretoria-Witwatersrand-Vereeniging)", "new_name": "Gauteng", "year": 1995, "authority": "Constitution Amendment (Jun 1995)"},
      {"old_name": "Eastern Transvaal", "new_name": "Mpumalanga", "year": 1995, "authority": "1995 Provincial Proclamation"},
      {"old_name": "Northern Transvaal / Northern Province", "new_name": "Limpopo", "year": 2003, "authority": "2003 Constitutional Amendment (Northern Province 1995-2003)"}
    ],
    "splits": []
  }

  T["COD"] = {
    "base_adm1": "geoboundaries/COD_ADM1.geojson",
    "name_field": "shapeName",
    "adm1_count_2025": 26,
    "evolution_summary": "Belgian Congo 6 Provinces (1933-1960) -> 21 Provincettes (1962-1966) -> 8 Provinces + Kinshasa (1966-1988) -> 10 Provinces + Kinshasa (1988-2015) -> 26 Provinces implemented Jul 2015 under 2006 Constitution",
    "sovereign_transitions": [
      {"year": 1960, "date": "1960-06-30", "event": "Independence of Republic of the Congo (Léopoldville); Katanga & South Kasai secessions (1960-1963)"}
    ],
    "epoch_groups": {
      "1950_1960_six_provinces": {
        "start_year": 1950, "end_year": 1961,
        "groups": {
          "Léopoldville": ["Kinshasa", "Kongo Central", "Kwango", "Kwilu", "Mai-Ndombe"],
          "Équateur": ["Équateur", "Mongala", "Nord-Ubangi", "Sud-Ubangi", "Tshuapa"],
          "Orientale": ["Bas-Uele", "Haut-Uele", "Ituri", "Tshopo"],
          "Kivu": ["Maniema", "Nord-Kivu", "Sud-Kivu"],
          "Katanga": ["Haut-Katanga", "Haut-Lomami", "Lualaba", "Tanganyika"],
          "Kasaï": ["Kasaï", "Kasaï-Central", "Kasaï-Oriental", "Lomami", "Sankuru"]
        }
      },
      "1966_2014_eleven_provinces": {
        "start_year": 1966, "end_year": 2014,
        "groups": {
          "Kinshasa": ["Kinshasa"],
          "Bas-Congo (Bas-Zaïre)": ["Kongo Central"],
          "Bandundu": ["Kwango", "Kwilu", "Mai-Ndombe"],
          "Équateur": ["Équateur", "Mongala", "Nord-Ubangi", "Sud-Ubangi", "Tshuapa"],
          "Orientale (Haut-Zaïre)": ["Bas-Uele", "Haut-Uele", "Ituri", "Tshopo"],
          "Nord-Kivu (from Kivu 1988)": ["Nord-Kivu"],
          "Sud-Kivu (from Kivu 1988)": ["Sud-Kivu"],
          "Maniema (from Kivu 1988)": ["Maniema"],
          "Katanga (Shaba)": ["Haut-Katanga", "Haut-Lomami", "Lualaba", "Tanganyika"],
          "Kasaï-Oriental": ["Kasaï-Oriental", "Lomami", "Sankuru"],
          "Kasaï-Occidental": ["Kasaï", "Kasaï-Central"]
        }
      }
    },
    "splits": [
      {"child": "Nord-Kivu / Sud-Kivu / Maniema", "parent": "Kivu", "split_year": 1988, "authority": "1988 Kivu Provincial Division"},
      {"child": "26 Provinces (découpage)", "parent": "11 Provinces", "split_year": 2015, "authority": "Constitution of 2006 Art. 2 & Programming Law No. 15/004 (28 Feb 2015; implemented Jul 2015)"}
    ]
  }

  T["KEN"] = {
    "base_adm1": "geoboundaries/KEN_ADM1.geojson",
    "name_field": "shapeName",
    "adm1_count_2025": 47,
    "evolution_summary": "6 Colonial Provinces (1948-1962) -> 7 Provinces + Nairobi Area (1963-2013) -> 47 Devolved Counties (27 Mar 2013-2025)",
    "sovereign_transitions": [
      {"year": 1963, "date": "1963-12-12", "event": "Independence of Kenya; Coastal Strip leased from Zanzibar formally integrated"}
    ],
    "epoch_groups": {
      "1963_2012_eight_provinces": {
        "start_year": 1963, "end_year": 2012,
        "groups": {
          "Nairobi": ["Nairobi"],
          "Central": ["Kiambu", "Kirinyaga", "Murang'a", "Nyandarua", "Nyeri"],
          "Coast": ["Kilifi", "Kwale", "Lamu", "Mombasa", "Taita Taveta", "Tana River"],
          "Eastern": ["Embu", "Isiolo", "Kitui", "Machakos", "Makueni", "Marsabit", "Meru", "Tharaka-Nithi"],
          "North Eastern": ["Garissa", "Mandera", "Wajir"],
          "Nyanza": ["Homa Bay", "Kisii", "Kisumu", "Migori", "Nyamira", "Siaya"],
          "Rift Valley": ["Baringo", "Bomet", "Elgeyo-Marakwet", "Kajiado", "Kericho", "Laikipia", "Nakuru", "Nandi", "Narok", "Samburu", "Trans Nzoia", "Turkana", "Uasin Gishu", "West Pokot"],
          "Western": ["Bungoma", "Busia", "Kakamega", "Vihiga"]
        }
      }
    },
    "splits": [
      {"child": "47 Counties", "parent": "8 Provinces", "split_year": 2013, "authority": "Constitution of Kenya 2010 (effective 27 Mar 2013)"}
    ]
  }

  T["GHA"] = {
    "base_adm1": "geoboundaries/GHA_ADM1.geojson",
    "name_field": "shapeName",
    "adm1_count_2025": 16,
    "evolution_summary": "Gold Coast Colony, Ashanti, Northern Territories & British Togoland (1950-1956) -> 5 Regions (1957) -> 6 (1959) -> 7 (1960) -> 8 (1970) -> 9 (1982) -> 10 (1983) -> 16 Regions (Feb 2019-2025)",
    "sovereign_transitions": [
      {"year": 1956, "date": "1956-12-13", "event": "British Togoland Trust Territory votes to unite with Gold Coast"},
      {"year": 1957, "date": "1957-03-06", "event": "Independence of Ghana"}
    ],
    "splits": [
      {"child": "Brong-Ahafo", "parent": "Ashanti", "split_year": 1959, "authority": "Brong-Ahafo Region Act (4 Apr 1959)"},
      {"child": "Upper", "parent": "Northern", "split_year": 1960, "authority": "1960 Regional Reorganization (1 Jul 1960)"},
      {"child": "Central", "parent": "Western", "split_year": 1970, "authority": "1970 Regional Split"},
      {"child": "Greater Accra", "parent": "Eastern", "split_year": 1982, "authority": "Greater Accra Region Law (PNDCL 26, 23 Jul 1982)"},
      {"child": "Upper West", "parent": "Upper East", "split_year": 1983, "authority": "1983 Upper Region Split into Upper East & Upper West"},
      {"child": "Ahafo Region", "parent": "Bono", "split_year": 2019, "authority": "C.I. 114 (Feb 2019; split Brong-Ahafo into Bono, Ahafo, Bono East)"},
      {"child": "Bono East Region", "parent": "Bono", "split_year": 2019, "authority": "C.I. 113 (Feb 2019)"},
      {"child": "North East Region", "parent": "Northern", "split_year": 2019, "authority": "C.I. 116 (Feb 2019)"},
      {"child": "Savannah Region", "parent": "Northern", "split_year": 2019, "authority": "C.I. 115 (Feb 2019)"},
      {"child": "Oti Region", "parent": "Volta", "split_year": 2019, "authority": "C.I. 112 (Feb 2019)"},
      {"child": "Western North Region", "parent": "Western", "split_year": 2019, "authority": "C.I. 117 (Feb 2019)"}
    ]
  }

  T["MLI"] = {
    "base_adm1": "geoboundaries/MLI_ADM1.geojson",
    "name_field": "shapeName",
    "data_quality_note": "geoboundaries/MLI_ADM1.geojson has 9 units (8 pre-2016 regions + Bamako). Taoudénit & Ménaka became operational 2016 (10 regions + Bamako), and Law 2023-006 expanded Mali to 19 regions + Bamako District.",
    "adm1_count_2025": 20,
    "evolution_summary": "French Sudan in AOF (1950-1958) -> Mali Federation (1959-Aug 1960) -> 6 Regions (1960-1977) -> 7 Regions + Bamako (1977) -> 8 + Bamako (1991) -> 10 + Bamako (2016) -> 19 Regions + Bamako District (2023-2025)",
    "sovereign_transitions": [
      {"year": 1959, "date": "1959-04-04", "event": "Mali Federation formed with Senegal"},
      {"year": 1960, "date": "1960-09-22", "event": "Republic of Mali proclaimed after breakup of Mali Federation (20 Aug 1960)"}
    ],
    "splits": [
      {"child": "Bamako", "parent": "Koulikoro", "split_year": 1977, "authority": "Ordinance 77-44/CMLN (12 Jul 1977)"},
      {"child": "Tombouctou", "parent": "Gao", "split_year": 1977, "authority": "Ordinance 77-44/CMLN (12 Jul 1977)"},
      {"child": "Kidal", "parent": "Gao", "split_year": 1991, "authority": "Ordinance 91-039/P-CTSP (8 Aug 1991)"},
      {"child": "Taoudénit", "parent": "Tombouctou", "split_year": 2016, "authority": "Law 2012-017 (implemented 2016)"},
      {"child": "Ménaka", "parent": "Gao", "split_year": 2016, "authority": "Law 2012-017 (implemented 2016)"},
      {"child": "9 New Regions (Bougouni, Dioïla, Douentza, Koutiala, Kita, Nioro, Nara, Bandiagara, San)", "parent": "Existing 10 Regions", "split_year": 2023, "authority": "Law 2023-006 / Decree 2023-0130 (Mar 2023)"}
    ]
  }

  T["MDG"] = {
    "base_adm1": "geoboundaries/MDG_ADM1.geojson",
    "name_field": "shapeName",
    "data_quality_note": "geoboundaries/MDG_ADM1.geojson has 22 regions; Law 2021-012 split Vatovavy-Fitovinany into Vatovavy and Fitovinany (23 regions).",
    "adm1_count_2025": 23,
    "evolution_summary": "French Colony 6 Provinces (1950-1958) -> Malagasy Republic / Madagascar 6 Provinces (1958-2009) -> 22 Regions (2004 Law / 2007 Referendum / Oct 2009 abolition of provinces) -> 23 Regions (Vatovavy & Fitovinany split Aug 2021)",
    "sovereign_transitions": [
      {"year": 1960, "date": "1960-06-26", "event": "Full independence of Malagasy Republic from France"}
    ],
    "epoch_groups": {
      "1950_2009_six_provinces": {
        "start_year": 1950, "end_year": 2009,
        "groups": {
          "Antananarivo": ["Analamanga", "Bongolava", "Itasy", "Vakinankaratra"],
          "Antsiranana": ["Diana", "Sava"],
          "Fianarantsoa": ["Amoron'i Mania", "Atsimo-Atsinanana", "Haute Matsiatra", "Ihorombe", "Vatovavy-Fitovinany"],
          "Mahajanga": ["Betsiboka", "Boeny", "Melaky", "Sofia"],
          "Toamasina": ["Alaotra-Mangoro", "Analanjirofo", "Atsinanana"],
          "Toliara": ["Androy", "Anosy", "Atsimo-Andrefana", "Menabe"]
        }
      }
    },
    "splits": [
      {"child": "Vatovavy / Fitovinany", "parent": "Vatovavy-Fitovinany", "split_year": 2021, "authority": "Law No. 2021-012 (11 Aug 2021)"}
    ]
  }

  T["TZA"] = {
    "base_adm1": "geoboundaries/TZA_ADM1.geojson",
    "name_field": "shapeName",
    "data_quality_note": "geoboundaries/TZA_ADM1.geojson has 30 regions (Songwe split from Mbeya in Jan 2016 -> 31 regions).",
    "adm1_count_2025": 31,
    "evolution_summary": "Tanganyika 8 Provinces (1950-1961) + Zanzibar Protectorate (Unguja & Pemba, 1950-1964) -> Union of Tanganyika & Zanzibar (26 Apr 1964) -> 20 Regions (1966) -> 25 Regions (1972/1975) -> 26 Regions (Manyara 2002) -> 30 Regions (2012) -> 31 Regions (Songwe 2016-2025)",
    "sovereign_transitions": [
      {"year": 1961, "date": "1961-12-09", "event": "Independence of Tanganyika"},
      {"year": 1963, "date": "1963-12-10", "event": "Independence of Sultanate of Zanzibar (Revolution 12 Jan 1964)"},
      {"year": 1964, "date": "1964-04-26", "event": "Union of Tanganyika and Zanzibar forming United Republic of Tanzania"}
    ],
    "splits": [
      {"child": "Dar es Salaam", "parent": "Pwani (Coast)", "split_year": 1974, "authority": "1974 Regional Reorganization"},
      {"child": "Rukwa", "parent": "Mbeya", "split_year": 1974, "authority": "Split from Mbeya & Tabora (1974)"},
      {"child": "Lindi", "parent": "Mtwara", "split_year": 1971, "authority": "1971 Regional Reorganization"},
      {"child": "Manyara", "parent": "Arusha", "split_year": 2002, "authority": "Government Notice (May 2002)"},
      {"child": "Geita", "parent": "Mwanza", "split_year": 2012, "authority": "Government Notice (Mar 2012; from Mwanza, Kagera, Shinyanga)"},
      {"child": "Katavi", "parent": "Rukwa", "split_year": 2012, "authority": "Government Notice (Mar 2012)"},
      {"child": "Njombe", "parent": "Iringa", "split_year": 2012, "authority": "Government Notice (Mar 2012)"},
      {"child": "Simiyu", "parent": "Shinyanga", "split_year": 2012, "authority": "Government Notice (Mar 2012)"},
      {"child": "Songwe", "parent": "Mbeya", "split_year": 2016, "authority": "Government Notice (29 Jan 2016)"}
    ]
  }

  T["CMR"] = {
    "base_adm1": "geoboundaries/CMR_ADM1.geojson",
    "name_field": "shapeName",
    "adm1_count_2025": 10,
    "evolution_summary": "French Cameroun Trust Territory + British Northern & Southern Cameroons (1950-1960) -> French Cameroun independent (1 Jan 1960) + Reunification with Southern Cameroons (1 Oct 1961) -> 6 Regions (1961-1972) -> Unitary Republic 7 Provinces (1972) -> 10 Provinces (22 Aug 1983) -> 10 Regions (12 Nov 2008-2025)",
    "sovereign_transitions": [
      {"year": 1960, "date": "1960-01-01", "event": "Independence of French Cameroun"},
      {"year": 1961, "date": "1961-10-01", "event": "British Southern Cameroons unites with Republic of Cameroon to form Federal Republic (Northern Cameroons joined Nigeria 1 Jun 1961)"},
      {"year": 2008, "date": "2008-08-14", "event": "Bakassi Peninsula transferred from Nigeria to South-West Region"}
    ],
    "splits": [
      {"child": "Centre / South", "parent": "Centre-Sud", "split_year": 1983, "authority": "Decree No. 83-392 (22 Aug 1983)"},
      {"child": "Adamaoua / Far North / North", "parent": "Nord", "split_year": 1983, "authority": "Decree No. 83-392 (22 Aug 1983)"}
    ]
  }

  T["SOM"] = {
    "base_adm1": "geoboundaries/SOM_ADM1.geojson",
    "name_field": "shapeName",
    "adm1_count_2025": 18,
    "evolution_summary": "British Somaliland Protectorate (6 Districts) + Italian Trust Territory of Somaliland (6 Regions, 1950-1960) -> Union (1 Jul 1960) into 8 Provinces -> 15/16 Regions (1974/1982) -> 18 Regions (1984-1987) -> De facto secession of Somaliland (18 May 1991, 5-6 northern regions) & Federal Member States (2012-2016)",
    "sovereign_transitions": [
      {"year": 1960, "date": "1960-07-01", "event": "Union of State of Somaliland (independent 26 Jun 1960) and Trust Territory of Somalia"},
      {"year": 1991, "date": "1991-05-18", "event": "Republic of Somaliland declares restoration of independence across former British Somaliland borders"}
    ],
    "splits": [
      {"child": "Awdal", "parent": "Woqooyi Galbeed", "split_year": 1984, "authority": "1984 Regional Reorganization"},
      {"child": "Sool", "parent": "Nugaal", "split_year": 1987, "authority": "1987 Regional Reorganization"}
    ]
  }

  T["SOL"] = {
    "base_adm1": "subset_of_SOM_ADM1",
    "name_field": "shapeName",
    "adm1_count_2025": 6,
    "evolution_summary": "British Somaliland Protectorate (1950-1960) -> Northern Provinces of Somalia (1960-1991) -> De facto independent Republic of Somaliland (18 May 1991-2025; 5 canonical pre-war regions: Awdal, Woqooyi Galbeed/Maroodi Jeex, Togdheer, Sanaag, Sool, plus Sahil split from Woqooyi Galbeed 1996)",
    "splits": [
      {"child": "Sahil", "parent": "Woqooyi Galbeed", "split_year": 1996, "authority": "Somaliland Regions & Districts Law (1996/2002)"}
    ]
  }

  T["NAM"] = {
    "base_adm1": "geoboundaries/NAM_ADM1.geojson",
    "name_field": "shapeName",
    "data_quality_note": "geoboundaries/NAM_ADM1.geojson lists 'Cunene' alongside 'Kunene' and unified 'Kavango' instead of Kavango East/Kavango West (split 2013).",
    "adm1_count_2025": 14,
    "evolution_summary": "South West Africa Class C Mandate under South Africa (1950-1990; 26 magisterial districts + Odendaal homelands 1968-1989) -> Independence (21 Mar 1990) -> 13 Regions (1992) -> 14 Regions (Kavango split into Kavango East & Kavango West, Aug 2013; Caprivi renamed Zambezi; Walvis Bay integrated 1 Mar 1994)",
    "sovereign_transitions": [
      {"year": 1990, "date": "1990-03-21", "event": "Independence of Namibia from South African administration"},
      {"year": 1994, "date": "1994-03-01", "event": "Walvis Bay integrated into Erongo Region from South Africa"}
    ],
    "splits": [
      {"child": "Kavango East / Kavango West", "parent": "Kavango", "split_year": 2013, "authority": "4th Delimitation Commission Proclamation No. 25 (8 Aug 2013)"}
    ]
  }

  # --- Colonial Federations ---
  T["AOF"] = {
    "base_adm1": "colonial_federation_envelope",
    "evolution_summary": "Afrique Occidentale Française (8 Overseas Territories 1947-1958: Côte d'Ivoire, Dahomey, Guinée, Haute-Volta [restored 4 Sep 1947], Mauritanie, Niger, Sénégal, Soudan Français) -> Guinea independent 2 Oct 1958; remaining 7 became autonomous republics Nov-Dec 1958 -> all independent Apr-Nov 1960",
    "sovereign_transitions": [
      {"year": 1958, "date": "1958-10-02", "event": "Guinea votes No in French constitutional referendum and gains independence"},
      {"year": 1960, "date": "1960-08-01", "event": "Dissolution of AOF completed as Dahomey, Niger, Upper Volta, Côte d'Ivoire, Senegal, Mali, and Mauritania (Nov 1960) achieve full independence"}
    ]
  }

  T["AEF"] = {
    "base_adm1": "colonial_federation_envelope",
    "evolution_summary": "Afrique Équatoriale Française (4 Overseas Territories 1946-1958: Gabon, Moyen-Congo, Oubangui-Chari, Tchad) -> Autonomous republics Nov-Dec 1958 -> Full independence 11-17 Aug 1960",
    "sovereign_transitions": [
      {"year": 1960, "date": "1960-08-17", "event": "All 4 AEF territories independent (Chad 11 Aug, CAR 13 Aug, Congo 15 Aug, Gabon 17 Aug)"}
    ]
  }

  T["FRN"] = {
    "base_adm1": "colonial_federation_envelope",
    "evolution_summary": "Federation of Rhodesia and Nyasaland (1953-1963: Southern Rhodesia, Northern Rhodesia, Nyasaland) -> Dissolved 31 Dec 1963 -> Malawi independent 6 Jul 1964, Zambia independent 24 Oct 1964, Southern Rhodesia UDI 11 Nov 1965 -> Zimbabwe independent 18 Apr 1980",
    "sovereign_transitions": [
      {"year": 1953, "date": "1953-09-03", "event": "Federation of Rhodesia and Nyasaland established"},
      {"year": 1963, "date": "1963-12-31", "event": "Federation formally dissolved"}
    ]
  }

  # --- All remaining 40+ NICETHI jurisdictions ---
  rest = {
    "AGO": {
      "evolution_summary": "Portuguese Angola 5 Provinces (1950) -> 13 Districts (1955) -> 15 (1961) -> 16 (1970) -> 18 Provinces (1975-2024: Bengo split 1980, Cuando Cubango, Lunda Norte/Sul) -> 21 Provinces (Law 14/24, Aug 2024: Icolo e Bengo, Moxico Leste, Cuando)",
      "splits": [
        {"child": "Lunda Norte / Lunda Sul", "parent": "Lunda", "split_year": 1978, "authority": "1978 Provincial Split"},
        {"child": "Bengo", "parent": "Luanda", "split_year": 1980, "authority": "Law 1980"},
        {"child": "Icolo e Bengo", "parent": "Luanda", "split_year": 2024, "authority": "Law No. 14/24 (14 Aug 2024)"},
        {"child": "Moxico Leste", "parent": "Moxico", "split_year": 2024, "authority": "Law No. 14/24 (14 Aug 2024)"},
        {"child": "Cuando", "parent": "Cuando Cubango", "split_year": 2024, "authority": "Law No. 14/24 (14 Aug 2024)"}
      ]
    },
    "ATF": {"evolution_summary": "Îles Éparses transferred from Madagascar to France (1960), administered by Réunion (1960-2005), transferred to TAAF (3 Jan 2005), designated 5th district (15 Mar 2007)", "splits": []},
    "BDI": {
      "evolution_summary": "Belgian Ruanda-Urundi Trust Territory (9 Urundi territories, 1950-1962) -> Independent Kingdom/Republic 8 Provinces (1962-1982) -> 15 Provinces (1982) -> 16 (1998 Mwaro) -> 17 (1991 Bujumbura split) -> 18 (2015 Rumonge) -> 5 Enlarged Provinces (Organic Law 1/05, Mar 2023 / effective 2025)",
      "splits": [
        {"child": "15 Provinces", "parent": "8 Provinces", "split_year": 1982, "authority": "Decree 24 Sep 1982"},
        {"child": "Bujumbura Mairie / Bujumbura Rural", "parent": "Bujumbura", "split_year": 1991, "authority": "1991 Reorganization"},
        {"child": "Mwaro", "parent": "Muramvya", "split_year": 1998, "authority": "1998 Decree"},
        {"child": "Rumonge", "parent": "Bururi", "split_year": 2015, "authority": "Law 26 Mar 2015 (from Bururi & Bujumbura Rural)"}
      ]
    },
    "BEN": {
      "evolution_summary": "Dahomey in AOF (1950-1960) -> 6 Provinces (1960-1999) -> 12 Départements (15 Jan 1999-2025)",
      "splits": [
        {"child": "Alibori", "parent": "Borgou", "split_year": 1999, "authority": "Law No. 97-028 (implemented 15 Jan 1999)"},
        {"child": "Collines", "parent": "Zou", "split_year": 1999, "authority": "Law No. 97-028 (15 Jan 1999)"},
        {"child": "Kouffo", "parent": "Mono", "split_year": 1999, "authority": "Law No. 97-028 (15 Jan 1999)"},
        {"child": "Donga", "parent": "Atakora", "split_year": 1999, "authority": "Law No. 97-028 (15 Jan 1999)"},
        {"child": "Littoral", "parent": "Atlantique", "split_year": 1999, "authority": "Law No. 97-028 (15 Jan 1999)"},
        {"child": "Plateau", "parent": "Ouémé", "split_year": 1999, "authority": "Law No. 97-028 (15 Jan 1999)"}
      ]
    },
    "BFA": {
      "evolution_summary": "Upper Volta in AOF (reconstituted 1947) -> 4 Departments (1960) -> 5 (1967) -> 10 (1974) -> 25/30/45 Provinces (1983-1997) -> 13 Regions (Law 013-2001, 2 Jul 2001-2024)",
      "splits": []
    },
    "BWA": {"evolution_summary": "Bechuanaland Protectorate (12 districts, 1950-1966) -> Independent Botswana 9/10 Rural Districts + 6 Urban Councils (1966-2025; Chobe split from North-West 2001)", "splits": [{"child": "Chobe", "parent": "North-West District", "split_year": 2001, "authority": "2001 Census District Split"}]},
    "CAF": {"evolution_summary": "Oubangui-Chari in AEF (1950-1960) -> 14/16 Prefectures + Bangui (1960-2020) -> 20 Prefectures (Dec 2020 Law)", "splits": []},
    "CIV": {
      "evolution_summary": "Côte d'Ivoire in AOF (1950-1960; 19 cercles) -> 4/6 Departments (1961-1969) -> 24/50 Departments (1969-1991) -> 10 Regions (1991) -> 16 (1997) -> 19 (2000) -> 12 Districts + 2 Autonomous Districts (28 Sep 2011-2025)",
      "splits": []
    },
    "COG": {"evolution_summary": "Moyen-Congo in AEF (1950-1960) -> 12 Prefectures (1960-1967) -> 9 Regions + Brazzaville (1967-2002) -> 12 Departments (Pointe-Noire 2003, Cuvette-Ouest 1995) -> 15 Departments (2024)", "splits": [{"child": "Cuvette-Ouest", "parent": "Cuvette", "split_year": 1995, "authority": "1995 Reform"}, {"child": "Pointe-Noire", "parent": "Kouilou", "split_year": 2003, "authority": "2003 Municipal Department"}]},
    "COM": {"evolution_summary": "French Overseas Territory (4 islands, 1950-1975) -> Independent Comoros (3 islands: Grande Comore, Anjouan, Mohéli; Mayotte remained French, 6 Jul 1975-2025)", "splits": []},
    "CPV": {"evolution_summary": "Portuguese Cape Verde (12 counties 1950 -> 14 counties 1975 -> 17 in 1990s -> 22 Concelhos / Municipalities 2005-2025)", "splits": []},
    "DJI": {"evolution_summary": "French Somaliland / TFAI (4/5 districts 1950-1981) -> Independent Djibouti (1977) -> Obock split (1981) -> Arta Region split from Dikhil/Djibouti (2002) = 5 Regions + Djibouti City", "splits": [{"child": "Arta", "parent": "Dikhil", "split_year": 2002, "authority": "Law 7 Jul 2002"}]},
    "GAB": {"evolution_summary": "Gabon in AEF (1950-1960) -> 9 Prefectures -> 9 Provinces (1975-2025)", "splits": []},
    "GIN": {"evolution_summary": "French Guinea in AOF (1950-1958) -> Independent Guinea (2 Oct 1958) -> 29->33 Prefectures grouped into 7 Administrative Regions + Conakry (1990-2025)", "splits": []},
    "GMB": {"evolution_summary": "Gambia Colony & Protectorate (5 divisions + Bathurst, 1950-1965) -> Independent (18 Feb 1965) -> North Bank split from Lower River (1968) -> 5 Regions + Banjul + Kanifing + Brikama LGAs (2007-2025)", "splits": [{"child": "North Bank", "parent": "Lower River", "split_year": 1968, "authority": "1968 Division Split"}]},
    "GNB": {"evolution_summary": "Portuguese Guinea (9 circumscriptions + 2 communes 1950 -> 12 circumscriptions 1973) -> Independent Guinea-Bissau (1973/1974) -> 8 Regions + Bissau Autonomous Sector (1975-2025)", "splits": []},
    "GNQ": {"evolution_summary": "Spanish Guinea (2 districts 1950 -> 2 overseas provinces 1960 -> Autonomous Region 1963) -> Independent Equatorial Guinea (12 Oct 1968) -> 7 Provinces (1990) -> 8 Provinces (Djibloho split from Wele-Nzas, Aug 2015-2025)", "splits": [{"child": "Djibloho", "parent": "Wele-Nzas", "split_year": 2015, "authority": "Law 3 Aug 2015"}]},
    "IOT": {"evolution_summary": "Chagos Archipelago administered as dependency of British Mauritius (1950-1965) -> Detached as British Indian Ocean Territory (8 Nov 1965-2025; UK-Mauritius sovereignty treaty signed 2024/2025)", "splits": []},
    "LBR": {"evolution_summary": "5 Coastal Counties + 3 Interior Provinces (1950-1964) -> 9 Counties (1964: Bong, Grand Gedeh, Lofa, Nimba) -> 13 Counties (1984-1985: Bomi, Grand Kru, Margibi, River Cess) -> 15 Counties (2000 River Gee, 2003 Gbarpolu)", "splits": [{"child": "Gbarpolu", "parent": "Lofa", "split_year": 2003, "authority": "Act 2001 (effective 2003)"}, {"child": "River Gee", "parent": "Grand Gedeh", "split_year": 2000, "authority": "Act 2000"}]},
    "LSO": {"evolution_summary": "Basutoland (9 districts 1950-1966) -> Independent Lesotho (4 Oct 1966) -> 10 Districts (Thaba-Tseka created c.1980-2025)", "splits": [{"child": "Thaba-Tseka", "parent": "Maseru / Qacha's Nek", "split_year": 1980, "authority": "1979/1980 District Act"}]},
    "MOZ": {"evolution_summary": "Portuguese Mozambique 4 Districts (1950) -> 9 Districts (1954) -> Independent Mozambique (25 Jun 1975) -> 10 Provinces (Manica & Sofala split 1978) + Maputo City (1984) = 11 Admin-1 units (1984-2025)", "splits": [{"child": "Maputo City", "parent": "Maputo", "split_year": 1984, "authority": "1980/1984 Municipal Separation"}]},
    "MRT": {"evolution_summary": "Mauritania in AOF (cercles, 1950-1960; Hodh annexed from French Sudan 1954) -> Independent Mauritania (28 Nov 1960) -> 12 Regions + Nouakchott (1969; Tiris el Gharbia annexed 1976-1979) -> 15 Wilayas (Nouakchott split into 3, Nov 2014-2025)", "splits": []},
    "MUS": {"evolution_summary": "British Mauritius (9 island districts + Rodrigues + Chagos/Agalega, 1950-1965) -> Chagos detached to BIOT (1965) -> Independent Mauritius (12 Mar 1968): 9 Districts + Rodrigues (autonomous 2002) + Outer Islands (1968-2025)", "splits": []},
    "MWI": {"evolution_summary": "Nyasaland (3 Provinces, 1950-1964; in Federation 1953-1963) -> Independent Malawi (6 Jul 1964): 3 Regions (Central, Northern, Southern) subdivided into 23 (1964) -> 24 (Mwanza 1971) -> 27 (Balaka, Phalombe, Likoma 1998) -> 28 Districts (Neno 2003-2025)", "splits": []},
    "MYT": {"evolution_summary": "Comoros Overseas Territory (1950-1975) -> Separated from Comoros (6 Jul 1975) -> French Territorial Collectivity (1976) -> French Overseas Department 976 (31 Mar 2011-2025; 17 communes)", "splits": []},
    "NER": {"evolution_summary": "Niger in AOF (16 cercles, 1950-1960) -> Independent Niger (3 Aug 1960) -> 7 Departments (17 Jul 1964) -> Tillabéri split from Niamey (1992) -> 7 Regions + Niamey Urban Community (2001-2025)", "splits": [{"child": "Tillabéri", "parent": "Niamey", "split_year": 1992, "authority": "1992 Territorial Reform"}]},
    "REU": {"evolution_summary": "French Overseas Department 974 (1946-2025): 4 Arrondissements (Saint-Benoît, Saint-Denis, Saint-Paul, Saint-Pierre; 24 communes; 2006 arrondissement boundary adjustment)", "splits": []},
    "RWA": {"evolution_summary": "Belgian Ruanda-Urundi (8/9 territories 1950-1962) -> Independent Rwanda (1 Jul 1962): 10 Prefectures -> 11 (Kigali City 1990) -> 12 (Umutara 1996) -> 5 Provinces (Organic Law 29/2005, 1 Jan 2006-2025)", "splits": []},
    "SEN": {"evolution_summary": "Senegal in AOF (1950-1958) -> Mali Federation (1959-Aug 1960) -> 7 Regions (1960) -> 8 (Louga 1976) -> 10 (Fatick & Kolda 1984) -> 11 (Matam 2002) -> 14 Regions (Kaffrine, Kédougou, Sédhiou split 10 Sep 2008-2025)", "splits": [{"child": "Kaffrine", "parent": "Kaolack", "split_year": 2008, "authority": "Law 2008-14 (10 Sep 2008)"}, {"child": "Kédougou", "parent": "Tambacounda", "split_year": 2008, "authority": "Law 2008-14 (10 Sep 2008)"}, {"child": "Sédhiou", "parent": "Kolda", "split_year": 2008, "authority": "Law 2008-14 (10 Sep 2008)"}]},
    "SHN": {"evolution_summary": "British Overseas Territory (Saint Helena, Ascension, Tristan da Cunha): 3 dependencies (1950-2025; equal status under 2009 Constitution)", "splits": []},
    "SLE": {"evolution_summary": "Colony & Protectorate of Sierra Leone (1950-1961) -> Independent (27 Apr 1961): 3 Provinces + Western Area (1961-2017) -> North West Province split from Northern Province (2017; 4 Provinces + Western Area = 5)", "splits": [{"child": "North West Province", "parent": "Northern Province", "split_year": 2017, "authority": "2017 Local Government / Provincial Reorganization"}]},
    "STP": {"evolution_summary": "Portuguese Overseas Province (2 concelhos/islands, 1950-1975) -> Independent (12 Jul 1975) -> Autonomous Region of Príncipe (1995) + 6 districts on São Tomé (2 Provinces / 7 Districts, 1975-2025)", "splits": []},
    "SWZ": {"evolution_summary": "British High Commission Territory (6 districts 1950 -> 4 districts Dec 1963) -> Independent Swaziland/Eswatini (6 Sep 1968): 4 Regions (Hhohho, Manzini, Lubombo, Shiselweni, 1968-2025)", "splits": []},
    "SYC": {"evolution_summary": "British Crown Colony (1950-1976) -> Independent Seychelles (29 Jun 1976) -> 22->25->27 Administrative Districts (1977-2025)", "splits": []},
    "TCD": {"evolution_summary": "Chad in AEF (1950-1960) -> Independent Chad (11 Aug 1960): 11->14 Prefectures (1962-1999) -> 28 Departments (1999) -> 18 Regions (2002) -> 22 Regions (2008) -> 23 Regions (Ennedi split into Ennedi-Est & Ennedi-Ouest, Sep 2012-2025)", "splits": [{"child": "Ennedi-Est / Ennedi-Ouest", "parent": "Ennedi", "split_year": 2012, "authority": "Ordinance 027/PR/2012 (4 Sep 2012)"}]},
    "TGO": {"evolution_summary": "French Togoland UN Trust Territory (6->10 cercles, 1950-1960) -> Independent Togo (27 Apr 1960) -> 4 Regions (1966) -> 5 Regions (Kara split from Centrale/Savanes, 1981-2025)", "splits": [{"child": "Kara", "parent": "Centrale", "split_year": 1981, "authority": "1981 Regional Creation"}]},
    "UGA": {"evolution_summary": "Uganda Protectorate 4 Provinces (Buganda, Eastern, Northern, Western, 1950-1962) -> Independent (9 Oct 1962) -> 4 Provinces / 18 Districts (1967) -> 10 Provinces (1974) -> 33 Districts (1980) -> 56 (2000) -> 80 (2006) -> 112 (2010) -> 135 Districts + Kampala (2020-2025)", "splits": []},
    "ZMB": {"evolution_summary": "Northern Rhodesia (7->8 Provinces, 1950-1964; in Federation 1953-1963) -> Independent Zambia (24 Oct 1964): 8 Provinces -> 9 (Lusaka split from Central 1973) -> 10 Provinces (Muchinga split from Northern & Eastern, Nov 2011-2025)", "splits": [{"child": "Lusaka", "parent": "Central", "split_year": 1973, "authority": "1973 Provincial Creation"}, {"child": "Muchinga", "parent": "Northern", "split_year": 2011, "authority": "Presidential Proclamation (Nov 2011; from Northern & Eastern)"}]},
    "ZWE": {"evolution_summary": "Southern Rhodesia (Mashonaland & Matabeleland, 1950-1963; in Federation 1953-1963) -> 7 Provinces (1960s) -> 8 Provinces (1970s) -> Independent Zimbabwe (18 Apr 1980) -> 10 Provinces (Bulawayo & Harare metropolitan provinces split 1997-2025)", "splits": [{"child": "Bulawayo", "parent": "Matabeleland North", "split_year": 1997, "authority": "1997 Metropolitan Province Split"}, {"child": "Harare", "parent": "Mashonaland East", "split_year": 1997, "authority": "1997 Metropolitan Province Split"}]},
    "ZNZ": {"evolution_summary": "Sultanate & British Protectorate of Zanzibar (Unguja & Pemba, 1950-1963) -> Independence & Revolution (1963-1964) -> Union with Tanganyika (26 Apr 1964) -> 5 Regions of Revolutionary Government of Zanzibar (Mjini Magharibi, Kaskazini Unguja, Kusini Unguja, Kaskazini Pemba, Kusini Pemba, 1967-2025)", "splits": []}
  }

  for iso, info in rest.items():
    gb_names = load_gb_names(iso)
    entry = {
      "base_adm1": f"geoboundaries/{iso}_ADM1.geojson" if gb_names else "national_or_overseas_registry",
      "name_field": "shapeName" if gb_names else "unit_name",
      "adm1_count_gb": len(gb_names),
      "evolution_summary": info["evolution_summary"],
      "splits": info["splits"]
    }
    if iso == "NAM":
      pass
    T[iso] = entry

  # Add geoBoundaries counts/notes to the major profiled states as well
  for iso in ("NGA", "SDN", "SSD", "ETH", "ERI", "ZAF", "COD", "KEN", "GHA", "MLI", "MDG", "TZA", "CMR", "SOM", "NAM"):
    T[iso]["adm1_count_gb"] = len(load_gb_names(iso))

  return lineage


def main():
  print("[1/2] Merging sub-administrative enumerations across all sources...", flush=True)
  enums = merge_enumerations()
  with open(ENUM_OUT, "w", encoding="utf-8") as fh:
    json.dump(enums, fh, indent=2, ensure_ascii=False)

  total_polities = len(enums)
  total_yr_pairs = sum(len(v) for v in enums.values())
  total_rows = sum(len(rows) for yrs in enums.values() for rows in yrs.values())
  min_yr = min(int(y) for yrs in enums.values() for y in yrs.keys())
  max_yr = max(int(y) for yrs in enums.values() for y in yrs.keys())
  print(f"  [OK] {ENUM_OUT}", flush=True)
  print(f"       Polities/ISO3={total_polities} | Polity-Years={total_yr_pairs} | Rows={total_rows} | Span={min_yr}-{max_yr}", flush=True)

  print("[2/2] Writing post1950_boundary_lineage.json...", flush=True)
  lin = build_boundary_lineage()
  with open(LINEAGE_OUT, "w", encoding="utf-8") as fh:
    json.dump(lin, fh, indent=2, ensure_ascii=False)
  print(f"  [OK] {LINEAGE_OUT} ({len(lin['territories'])} territories)", flush=True)


if __name__ == "__main__":
  main()
