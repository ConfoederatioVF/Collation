# -*- coding: utf-8 -*-
"""
Operation Viscount — Project JAGUAR
Stage C Enrichment: Comprehensive Full-Row Sub-National Census Harvester
for ALL 39 Central American, Caribbean, and Bermuda jurisdictions (ZERO Top-N caps!).

Uses Python stdlib `html.parser` (zero external dependencies) to download and parse
every sub-national municipality, district, corregimiento, commune, parish, community,
island, and locality table from official NSO census compilations (`citypopulation.de`).
"""

import html as html_lib
from html.parser import HTMLParser
import json
import os
import re
import time
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUT_RAW = os.path.join(SHARED_DIR, "settlement_sources/raw/comprehensive_censuses")
OUT_PARSED = os.path.join(SHARED_DIR, "settlement_sources/parsed")
os.makedirs(OUT_RAW, exist_ok=True)
os.makedirs(OUT_PARSED, exist_ok=True)

HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
  "Accept-Language": "en-US,en;q=0.9",
}


class CityPopTableParser(HTMLParser):
  """Lightweight stdlib HTML table extractor for citypopulation.de tables."""

  def __init__(self):
    super().__init__()
    self.tables = []
    self._cur_tbl = None
    self._in_thead = False
    self._in_tbody = False
    self._cur_row = None
    self._cur_cell = None

  def handle_starttag(self, tag, attrs):
    ad = dict(attrs)
    t = tag.lower()
    if t == "table":
      self._cur_tbl = {"id": (ad.get("id") or "").strip().lower(), "headers": [], "rows": []}
    elif self._cur_tbl is not None:
      if t == "thead":
        self._in_thead = True
      elif t == "tbody":
        self._in_tbody = True
      elif t == "tr":
        self._cur_row = {
          "class": (ad.get("class") or "").lower(),
          "lat": ad.get("data-lat") or "",
          "lon": ad.get("data-lon") or "",
          "cells": [],
        }
      elif t in ("td", "th") and self._cur_row is not None:
        self._cur_cell = []
      elif t == "meta" and self._cur_row is not None:
        ip = (ad.get("itemprop") or "").lower()
        if ip == "latitude" and ad.get("content"):
          self._cur_row["lat"] = ad.get("content")
        elif ip == "longitude" and ad.get("content"):
          self._cur_row["lon"] = ad.get("content")

  def handle_endtag(self, tag):
    t = tag.lower()
    if t == "table" and self._cur_tbl is not None:
      self.tables.append(self._cur_tbl)
      self._cur_tbl = None
      self._in_thead = False
      self._in_tbody = False
    elif self._cur_tbl is not None:
      if t == "thead":
        self._in_thead = False
      elif t == "tbody":
        self._in_tbody = False
      elif t in ("td", "th") and self._cur_cell is not None:
        txt = " ".join("".join(self._cur_cell).split())
        self._cur_row["cells"].append(txt)
        self._cur_cell = None
      elif t == "tr" and self._cur_row is not None:
        if self._in_thead:
          self._cur_tbl["headers"].append(self._cur_row["cells"])
        else:
          self._cur_tbl["rows"].append(self._cur_row)
        self._cur_row = None

  def handle_data(self, data):
    if self._cur_cell is not None:
      self._cur_cell.append(data)


def fetch_cached(arg0_url, arg1_slug):
  """Fetches URL with local HTML cache under comprehensive_censuses/."""
  url = arg0_url
  slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", arg1_slug).strip("_")[:64]
  fpath = os.path.join(OUT_RAW, f"{slug}.html")
  if os.path.exists(fpath) and os.path.getsize(fpath) > 2000:
    with open(fpath, encoding="utf-8", errors="replace") as fh:
      return fh.read()

  req = urllib.request.Request(url, headers=HEADERS)
  for attempt in range(3):
    try:
      with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read().decode("utf-8", errors="replace")
      with open(fpath, "w", encoding="utf-8") as fh:
        fh.write(data)
      time.sleep(0.20)
      return data
    except Exception as err:
      if attempt == 2:
        print(f"  [WARN] fetch failed {url}: {err}")
        return ""
      time.sleep(1.5 * (attempt + 1))
  return ""


def parse_citypop_tables(arg0_html, arg1_country, arg2_iso2, arg3_source, keep_statuses=None, table_ids=None):
  """Parses all population tables from a citypopulation.de HTML page."""
  raw_html = arg0_html
  country = arg1_country
  iso2 = arg2_iso2
  nso_source = arg3_source
  table_ids = table_ids or ("tl", "ts", "tlc", "tla")

  if not raw_html:
    return []

  parser = CityPopTableParser()
  parser.feed(raw_html)

  rows_out = []
  for tbl in parser.tables:
    tid = tbl["id"]
    if tid not in table_ids:
      continue
    if not tbl["headers"]:
      continue

    hdr_cells = tbl["headers"][-1]
    pop_cols = []
    status_idx = -1
    adm_idx = -1
    name_idx = 0

    for ci, txt in enumerate(hdr_cells):
      low = txt.lower()
      if low == "name":
        name_idx = ci
      elif "status" in low:
        status_idx = ci
      elif low in ("adm.", "adm", "department", "province", "parish", "district", "region", "canton"):
        adm_idx = ci
      else:
        m = re.search(r"\b(1[789]\d\d|20[0-2]\d)\b", txt)
        if m and ("pop" in low or "census" in low or "est" in low or "proj" in low or "calc" in low or re.match(r"^(?:1[789]|20)\d\d", txt)):
          pop_cols.append((ci, int(m.group(1))))

    if not pop_cols:
      continue

    for tr in tbl["rows"]:
      cls = tr["class"]
      if "sum" in cls or "total" in cls or "head" in cls:
        continue
      cells = tr["cells"]
      if len(cells) <= name_idx:
        continue

      raw_nm = html_lib.unescape(cells[name_idx]).strip()
      if not raw_nm or raw_nm.lower() in (country.lower(), "total", "name"):
        continue

      status = html_lib.unescape(cells[status_idx]).strip() if (0 <= status_idx < len(cells)) else ""
      st_low = status.lower()
      if keep_statuses is not None:
        if not any(k in st_low for k in keep_statuses):
          continue

      adm_parent = html_lib.unescape(cells[adm_idx]).strip() if (0 <= adm_idx < len(cells)) else ""

      pops = {}
      for ci, yr in pop_cols:
        if ci < len(cells):
          raw_v = cells[ci].replace(",", "").replace(" ", "").replace("\u00a0", "")
          if raw_v.isdigit():
            iv = int(raw_v)
            if iv > 0:
              pops[str(yr)] = iv

      if not pops:
        continue

      rows_out.append({
        "country": country,
        "iso2": iso2,
        "table_id": tid,
        "name": raw_nm,
        "status": status,
        "adm_parent": adm_parent,
        "lat": tr["lat"],
        "lon": tr["lon"],
        "pops": pops,
        "source": nso_source,
      })

  return rows_out


def main():
  all_records = []

  #1. CUBA: All 16 province locality pages (ALL settlements >= 1,000) + 168 municipalities
  cuba_provs = [
    "pinardelrio", "artemisa", "mayabeque", "matanzas", "villaclara",
    "cienfuegos", "sanctispiritus", "ciegodeavila", "camaguey", "lastunas",
    "holguin", "granma", "santiagodecuba", "guantanamo", "isladelajuventud",
  ]
  cuba_cnt = 0
  h_cu_adm = fetch_cached("https://www.citypopulation.de/en/cuba/admin/", "cuba_admin")
  recs = parse_citypop_tables(h_cu_adm, "Cuba", "CU", "ONEI Cuba Censuses (1981, 2002, 2012, 2022)", keep_statuses=["municipality"])
  all_records.extend(recs)
  cuba_cnt += len(recs)
  for prov in cuba_provs:
    h = fetch_cached(f"https://www.citypopulation.de/en/cuba/{prov}/", f"cuba_{prov}")
    r = parse_citypop_tables(h, "Cuba", "CU", "ONEI Cuba Censuses (2002, 2012, 2022 Localities)", table_ids=("ts", "tl", "tlc"))
    all_records.extend(r)
    cuba_cnt += len(r)
  print(f"Cuba harvested: {cuba_cnt} rows")

  #2. HONDURAS: All 18 department locality pages (ALL localities >= 200) + 298 municipalities
  hnd_depts = [
    "atlantida", "choluteca", "colon", "comayagua", "copan", "cortes",
    "elparaiso", "franciscomorazan", "graciasadios", "intibuca",
    "islasdelabahia", "lapaz", "lempira", "ocotepeque", "olancho",
    "santabarbara", "valle", "yoro",
  ]
  hnd_cnt = 0
  h_hn_adm = fetch_cached("https://www.citypopulation.de/en/honduras/admin/", "honduras_admin")
  r = parse_citypop_tables(h_hn_adm, "Honduras", "HN", "INE Honduras Censuses (1988, 2001, 2013, 2023)", keep_statuses=["municipality"])
  all_records.extend(r)
  hnd_cnt += len(r)
  for dept in hnd_depts:
    h = fetch_cached(f"https://www.citypopulation.de/en/honduras/{dept}/", f"honduras_{dept}")
    r = parse_citypop_tables(h, "Honduras", "HN", "INE Honduras Censuses (2001, 2013 Localities)", table_ids=("ts", "tl", "tlc"))
    all_records.extend(r)
    hnd_cnt += len(r)
  print(f"Honduras harvested: {hnd_cnt} rows")

  #3. GUATEMALA: All 340 municipalities
  h_gt_adm = fetch_cached("https://www.citypopulation.de/en/guatemala/admin/", "guatemala_admin")
  r_gt = parse_citypop_tables(h_gt_adm, "Guatemala", "GT", "INE Guatemala Censuses (1981, 1994, 2002, 2018)", keep_statuses=["municipality"])
  all_records.extend(r_gt)
  print(f"Guatemala admin municipalities: {len(r_gt)} rows")

  #4. EL SALVADOR: All 262 municipalities/districts
  h_sv = fetch_cached("https://www.citypopulation.de/en/elsalvador/mun/admin/", "elsalvador_mun_admin")
  r_sv = parse_citypop_tables(h_sv, "El Salvador", "SV", "DIGESTYC / ONEC El Salvador Censuses (1992, 2007, 2024)", keep_statuses=["district", "municipality"])
  all_records.extend(r_sv)
  print(f"El Salvador municipalities/districts: {len(r_sv)} rows")

  #5. NICARAGUA: All 153 municipalities
  h_ni = fetch_cached("https://www.citypopulation.de/en/nicaragua/admin/", "nicaragua_admin")
  r_ni = parse_citypop_tables(h_ni, "Nicaragua", "NI", "INIDE Nicaragua Censuses (1971, 1995, 2005, 2023)", keep_statuses=["municipality"])
  all_records.extend(r_ni)
  print(f"Nicaragua municipalities: {len(r_ni)} rows")

  #6. COSTA RICA: All 488 districts + urban districts
  h_cr = fetch_cached("https://www.citypopulation.de/en/costarica/distr/admin/", "costarica_distr_admin")
  r_cr = parse_citypop_tables(h_cr, "Costa Rica", "CR", "INEC Costa Rica Censuses (1984, 2000, 2011, 2022)", keep_statuses=["district"])
  all_records.extend(r_cr)
  h_cr2 = fetch_cached("https://www.citypopulation.de/en/costarica/urbandistricts/", "costarica_urbandistricts")
  r_cr2 = parse_citypop_tables(h_cr2, "Costa Rica", "CR", "INEC Costa Rica Urban Districts (2000, 2011, 2022)", table_ids=("ts", "tl", "tlc"))
  all_records.extend(r_cr2)
  print(f"Costa Rica districts: {len(r_cr)} + urban: {len(r_cr2)}")

  #7. PANAMA: All 699 townships (corregimientos) + 82 districts
  h_pa = fetch_cached("https://www.citypopulation.de/en/panama/mun/admin/", "panama_mun_admin")
  r_pa = parse_citypop_tables(h_pa, "Panama", "PA", "INEC Panama Censuses (1990, 2000, 2010, 2023)", keep_statuses=["township", "district"])
  all_records.extend(r_pa)
  print(f"Panama townships/districts: {len(r_pa)} rows")

  #8. DOMINICAN REPUBLIC: All 158 municipalities + 235 municipal districts
  h_do = fetch_cached("https://www.citypopulation.de/en/domrep/mun/admin/", "domrep_mun_admin")
  r_do = parse_citypop_tables(h_do, "Dominican Republic", "DO", "ONE Dominican Republic Censuses (2002, 2010, 2022)", keep_statuses=["municipality", "municipal district"])
  all_records.extend(r_do)
  print(f"Dominican Republic mun/dist: {len(r_do)} rows")

  #9. PUERTO RICO: All towns/comunidades
  h_pr = fetch_cached("https://www.citypopulation.de/en/puertorico/towns/", "puertorico_towns")
  r_pr = parse_citypop_tables(h_pr, "Puerto Rico", "PR", "US Census Bureau Puerto Rico Censuses (1980-2020)", table_ids=("ts", "tl"))
  all_records.extend(r_pr)
  print(f"Puerto Rico towns: {len(r_pr)} rows")

  #10. TRINIDAD AND TOBAGO: All ~600 communities
  h_tt = fetch_cached("https://www.citypopulation.de/en/trinidad/admin/", "trinidad_admin")
  r_tt = parse_citypop_tables(h_tt, "Trinidad and Tobago", "TT", "CSO Trinidad and Tobago Censuses (2000, 2011 Communities)", keep_statuses=["community", "town", "city", "borough"])
  all_records.extend(r_tt)
  print(f"Trinidad & Tobago communities: {len(r_tt)} rows")

  #11. SAINT LUCIA: All ~400 communities
  h_lc = fetch_cached("https://www.citypopulation.de/en/stlucia/communities/", "stlucia_communities")
  r_lc = parse_citypop_tables(h_lc, "Saint Lucia", "LC", "CSO Saint Lucia Censuses (2001, 2010, 2022 Communities)", table_ids=("ts", "tl"))
  all_records.extend(r_lc)
  print(f"Saint Lucia communities: {len(r_lc)} rows")

  #12. BAHAMAS: All 8 island settlement subpages
  bs_islands = [
    "abaco", "andros", "biminiandberryislands", "catisland",
    "centralbahamas", "easternbahamas", "eleuthera", "exumaandcays",
  ]
  bs_cnt = 0
  for isl in bs_islands:
    h = fetch_cached(f"https://www.citypopulation.de/en/bahamas/{isl}/", f"bahamas_{isl}")
    r = parse_citypop_tables(h, "The Bahamas", "BS", "Bahamas Dept of Statistics Censuses (1990, 2000, 2010, 2022)", table_ids=("ts", "tl"))
    all_records.extend(r)
    bs_cnt += len(r)
  print(f"Bahamas island settlements: {bs_cnt} rows")

  #13. ARUBA & CURACAO: All zones/settlements
  h_aw = fetch_cached("https://www.citypopulation.de/en/aruba/admin/", "aruba_admin")
  r_aw = parse_citypop_tables(h_aw, "Aruba", "AW", "CBS Aruba Censuses (1991, 2000, 2010, 2020)", table_ids=("tl", "ts"))
  all_records.extend(r_aw)
  h_cw = fetch_cached("https://www.citypopulation.de/en/curacao/admin/", "curacao_admin")
  r_cw = parse_citypop_tables(h_cw, "Curaçao", "CW", "CBS Curacao Censuses (2001, 2011, 2023)", table_ids=("tl", "ts"))
  all_records.extend(r_cw)
  print(f"Aruba: {len(r_aw)}, Curacao: {len(r_cw)}")

  #14. JAMAICA: Kingston metro communities
  h_jm_k = fetch_cached("https://www.citypopulation.de/en/jamaica/kingston/admin/", "jamaica_kingston_admin")
  r_jm_k = parse_citypop_tables(h_jm_k, "Jamaica", "JM", "STATIN Jamaica Censuses (1991, 2001, 2011)", table_ids=("tl", "ts"))
  all_records.extend(r_jm_k)
  print(f"Jamaica Kingston/St Andrew/St Catherine communities: {len(r_jm_k)}")

  #15. REMAINING CARIBBEAN ISLANDS & BERMUDA (ALL tables tl/tlc/tla/ts!)
  micro_pages = [
    ("Barbados", "BB", "https://www.citypopulation.de/en/barbados/", "Barbados Statistical Service Censuses (1980-2021)"),
    ("Bermuda", "BM", "https://www.citypopulation.de/en/bermuda/", "Bermuda Dept of Statistics Censuses (1980-2016)"),
    ("Grenada", "GD", "https://www.citypopulation.de/en/grenada/", "CSO Grenada Censuses (1981-2021)"),
    ("Saint Vincent and the Grenadines", "VC", "https://www.citypopulation.de/en/stvincent/", "SVG Statistical Office Censuses (1980-2012)"),
    ("Antigua and Barbuda", "AG", "https://www.citypopulation.de/en/antigua/", "Antigua and Barbuda Statistics Division Censuses (1991-2011)"),
    ("Dominica", "DM", "https://www.citypopulation.de/en/dominica/", "CSO Dominica Censuses (1981-2011)"),
    ("Saint Kitts and Nevis", "KN", "https://www.citypopulation.de/en/stkittsnevis/", "St Kitts and Nevis Dept of Statistics Censuses (1991-2011)"),
    ("Turks and Caicos Islands", "TC", "https://www.citypopulation.de/en/turkscaicos/", "TCI Statistics Dept Censuses (1990-2022)"),
    ("Anguilla", "AI", "https://www.citypopulation.de/en/anguilla/", "Anguilla Statistics Dept Censuses (1984-2011)"),
    ("Montserrat", "MS", "https://www.citypopulation.de/en/montserrat/", "Montserrat Statistics Dept Censuses (1991-2023)"),
    ("British Virgin Islands", "VG", "https://www.citypopulation.de/en/britishvirginislands/", "BVI Central Statistics Office Censuses (1991-2010)"),
    ("United States Virgin Islands", "VI", "https://www.citypopulation.de/en/usvirginislands/", "US Census Bureau USVI Censuses (1980-2020)"),
    ("Sint Maarten", "SX", "https://www.citypopulation.de/en/sintmaarten/", "STAT Sint Maarten Censuses (2001-2018)"),
    ("Caribbean Netherlands", "BQ", "https://www.citypopulation.de/en/caribbeannetherlands/", "CBS Netherlands Caribbean Censuses (2001-2024)"),
    ("Haiti", "HT", "https://www.citypopulation.de/en/haiti/", "IHSI Haiti Censuses (1982, 2003, 2015)"),
    ("Belize", "BZ", "https://www.citypopulation.de/en/belize/admin/", "SIB Belize Censuses (1980-2022)"),
  ]
  for ctry, iso2, url, src in micro_pages:
    h = fetch_cached(url, f"micro_{iso2.lower()}")
    r = parse_citypop_tables(h, ctry, iso2, src, table_ids=("tl", "tlc", "tla", "ts"))
    all_records.extend(r)
    print(f"  {ctry:34s}: {len(r)} rows")

  out_json = os.path.join(OUT_PARSED, "jaguar_comprehensive_ca_carib_censuses.json")
  with open(out_json, "w", encoding="utf-8") as fh:
    json.dump(all_records, fh, indent=2, ensure_ascii=False)
  print(f"\nTOTAL COMPREHENSIVE CA & CARIBBEAN ROWS HARVESTED: {len(all_records):,} -> {out_json}")


if __name__ == "__main__":
  main()
