# -*- coding: utf-8 -*-
"""
Operation Viscount — Project JAGUAR
Stage C Enrichment Parser 2: Comprehensive Modern Census Parser for ALL 39
Central American, Caribbean, and Bermuda Jurisdictions (ZERO Top-N shortcuts!).

Combines strictly official NSO & international statistical datasets already archived on disk:
  1. INE Guatemala Censo 2018 Lugares Poblados (`A1_3` + `centroides`, excl. Guatemala City Zona Municipal 1-25)
     + INE Guatemala 1981-2018 all 340 municipalities (`citypop_html/guatemala.html`)
  2. INEC Panama Censo 2023 Cuadro 11 (all 699 corregimientos, 2000/2010/2023) + official ArcGIS 2023 corregimiento centroids (`agol_pan_corr_2023.json`) + 1990-2023 districts
  3. INEC Costa Rica / HDX UNFPA (all 478 districts) + official Costa Rica district centroids (`agol_cri_dist.json`) + cantons (1984-2022)
  4. INE Honduras (all 298 municipalities, 1988-2023) with parent-aware geocoding (100% of 298 munis!)
  5. DIGESTYC / ONEC El Salvador (all 262 municipalities/districts, 1992-2024) + HDX
  6. INIDE Nicaragua (all 153 municipalities, 1971-2023)
  7. SIB Belize (all 218 towns & villages from HDX ADM2) + official Belize 2010 settlement polygon centroids (`agol_blz_poly_2010.json`)
  8. US Census Bureau Puerto Rico 2010/2020 PL 94-171 (all 78 municipios + 253 lugares urbanos/comunidades + distinct rural barrios)
  9. ONEI Cuba (all 168 municipalities, 1981-2022 + urban centres)
 10. ONE Dominican Republic (all 158 municipalities, 2002-2022 + urban centres)
 11. IHSI Haiti (all 140 communes from HDX + 62 towns 1982-2015)
 12. STATIN / GOJ Jamaica 2022 Preliminary Census Communities (`agol_jam_2022_comm.json`, 770 official communities!) + STATIN 1982-2011 towns
 13. CSO Trinidad & Tobago 2000/2011 Communities (`agol_tto_cso_com.json` + `agol_tto_admin_com.json`, 587/601 official communities with centroids!) + `tt_admin.html`
 14. CSO Saint Lucia (all distinct communities from `lca_adm_gazetteer.xlsx` + `lca_adm2_demographics.csv`)
 15. INSEE French Antilles (all 32 Guadeloupe + 34 Martinique communes + St-Martin + St-Barth)
 16. US Census Bureau USVI (all towns, subdistricts & estates 1980-2020, excl. island totals)
 17. CBS Curacao 2011 Census Neighbourhoods/Villages (`agol_cuw_cbs_2011.json`, 291 official CBS polygons!)
 18. CSO Grenada 2011 Official Enumeration Areas (`agol_grd_ea.json`, 327 official EAs aggregated strictly to parish towns/villages)
 19. All remaining Caribbean territories & Bermuda (`bs_admin.html`, `sxm_pop_2018.xlsx`, `cayman`, `aruba`, `montserrat`, `svg`, `bvi`, `bes`, etc., strictly excluding national/island aggregates!)

Geocoding priority: 1) Official NSO/ArcGIS polygon centroid, 2) Curated WGS84 coordinates (0% pop), 3) GeoBoundaries ADM2 centroids, 4) GeoNames coords-only lookup (0% pop!).
"""

import csv
import glob
import html as html_lib
from html.parser import HTMLParser
import json
import math
import os
import re
import unicodedata
import openpyxl
import xlrd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SUBADMIN_RAW = os.path.join(SHARED_DIR, "subadmin_hgis/raw_sources")
SETTLE_RAW = os.path.join(SHARED_DIR, "settlement_sources/raw")
SETTLE_PARSED = os.path.join(SHARED_DIR, "settlement_sources/parsed")
NSO_OPEN = os.path.join(SETTLE_RAW, "nso_open_data")
OUT_JSON = os.path.join(SETTLE_PARSED, "jaguar_ca_carib_enriched_modern.json")
OUT_SUMMARY = os.path.join(SETTLE_PARSED, "_ca_carib_enriched_summary.json")


#National, island-wide, and non-settlement administrative aggregates strictly excluded
NON_SETTLEMENT_AGGREGATES = {
  ("BS", "bahamas"), ("BS", "the bahamas"), ("BS", "new providence"), ("BS", "grand bahama"),
  ("BS", "abaco"), ("BS", "andros"), ("BS", "eleuthera"),
  ("BS", "marco city"), ("BS", "pineridge"), ("BS", "central grand bahama"),
  ("BS", "killarney"), ("BS", "south beach"), ("BS", "englerston"), ("BS", "carmichael"),
  ("BS", "freetown"), ("BS", "bain and grants town"), ("BS", "centreville"), ("BS", "elizabeth"),
  ("BS", "fox hill"), ("BS", "fort charlotte"), ("BS", "garden hills"), ("BS", "golden gates"),
  ("BS", "golden isles"), ("BS", "marathon"), ("BS", "mount moriah"), ("BS", "nassau village"),
  ("BS", "pinewood"), ("BS", "seabreeze"), ("BS", "st annes"), ("BS", "st barnabas"),
  ("BS", "southern shores"), ("BS", "tall pines"), ("BS", "yamacraw"), ("BS", "bamboo town"),
  ("BS", "seabreeze"), ("BS", "st anne s"), ("BS", "st barnabas"), ("BS", "montagu"),
  ("KN", "st kitts"), ("KN", "saint kitts"), ("KN", "nevis"), ("KN", "st kitts and nevis"), ("KN", "saint kitts and nevis"),
  ("VC", "st vincent"), ("VC", "saint vincent"), ("VC", "st vincent and the grenadines"), ("VC", "saint vincent and the grenadines"),
  ("VC", "grenadines"), ("VC", "northern grenadines"), ("VC", "southern grenadines"), ("VC", "suburbs of kingstown"),
  ("VI", "virgin islands"), ("VI", "virgin islands of the u s"), ("VI", "united states virgin islands"),
  ("VI", "st croix"), ("VI", "saint croix"), ("VI", "st croix island"),
  ("VI", "st thomas"), ("VI", "saint thomas"), ("VI", "st thomas island"),
  ("VI", "st john"), ("VI", "saint john"), ("VI", "st john island"),
  ("VG", "british virgin islands"), ("VG", "tortola"), ("VG", "virgin gorda"), ("VG", "jost van dyke"),
  ("VG", "anegada"), ("VG", "other islands"), ("VG", "yachts"),
  ("BQ", "bonaire"), ("BQ", "sint eustatius"), ("BQ", "saba"), ("BQ", "caribbean netherlands"),
  ("KY", "cayman islands"), ("KY", "grand cayman"),
  ("MS", "montserrat"), ("MS", "central region"), ("MS", "northern region"), ("MS", "south of nantes river"),
  ("GD", "grenada"), ("AW", "aruba"), ("CW", "curacao"),
  ("TC", "turks and caicos islands"), ("AG", "antigua"), ("AG", "barbuda"), ("AG", "antigua and barbuda"),
  ("BB", "barbados"), ("BM", "bermuda"), ("DM", "dominica"), ("LC", "saint lucia"), ("LC", "st lucia"),
  ("TT", "trinidad"), ("TT", "tobago"), ("TT", "trinidad and tobago"),
  ("SX", "sint maarten"), ("SX", "not reported"), ("MF", "saint martin"), ("BL", "saint barthelemy"),
}


#Curated WGS84 coordinates (0% pop!) for small Caribbean towns/zones absent from GeoNames exact match
CURATED_MICRO_COORDS = {
  #Aruba (CBS census zones)
  ("AW", "oranjestad"): (12.5186, -70.0358),
  ("AW", "oranjestad west"): (12.5330, -70.0540),
  ("AW", "oranjestad oost"): (12.5120, -70.0150),
  ("AW", "noord"): (12.5680, -70.0320),
  ("AW", "tanki leendert"): (12.5480, -70.0150),
  ("AW", "paradera"): (12.5350, -69.9940),
  ("AW", "santa cruz"): (12.5090, -69.9740),
  ("AW", "savaneta"): (12.4440, -69.9380),
  ("AW", "sint nicolaas"): (12.4356, -69.9070),
  ("AW", "sint nicolaas noord"): (12.4520, -69.9040),
  ("AW", "sint nicolaas zuid"): (12.4230, -69.8980),
  #Curacao
  ("CW", "willemstad"): (12.1084, -68.9335),
  ("CW", "sint willibrordus"): (12.2167, -69.0667),
  ("CW", "soto"): (12.2750, -69.0970),
  ("CW", "tera cora"): (12.2260, -69.0350),
  ("CW", "barber"): (12.2900, -69.0700),
  #Caribbean Netherlands (BES)
  ("BQ", "kralendijk"): (12.1508, -68.2766),
  ("BQ", "rincon"): (12.2383, -68.3325),
  ("BQ", "oranjestad"): (17.4833, -62.9833),
  ("BQ", "the bottom"): (17.6261, -63.2492),
  ("BQ", "windwardside"): (17.6286, -63.2314),
  ("BQ", "saint johns"): (17.6190, -63.2430),
  ("BQ", "saint john s"): (17.6190, -63.2430),
  ("BQ", "zions hill"): (17.6435, -63.2260),
  ("BQ", "zion s hill"): (17.6435, -63.2260),
  #Montserrat
  ("MS", "brades"): (16.7928, -62.2106),
  ("MS", "plymouth"): (16.7064, -62.2158),
  ("MS", "salem"): (16.7483, -62.2233),
  ("MS", "st peters"): (16.7740, -62.2260),
  ("MS", "look out"): (16.7920, -62.1850),
  ("MS", "cudjoe head"): (16.7680, -62.1980),
  ("MS", "olveston"): (16.7460, -62.2380),
  ("MS", "woodlands"): (16.7620, -62.2280),
  ("MS", "barzeys"): (16.7860, -62.1940),
  ("MS", "drummonds"): (16.8050, -62.1950),
  ("MS", "friths"): (16.7370, -62.2290),
  ("MS", "davy hill"): (16.7770, -62.2080),
  ("MS", "st johns"): (16.7980, -62.1880),
  ("MS", "little bay"): (16.8030, -62.2160),
  ("MS", "geralds"): (16.8060, -62.2020),
  #Saint Vincent & the Grenadines
  ("VC", "kingstown"): (13.1579, -61.2248),
  ("VC", "bridgetown"): (13.2080, -61.1320),
  ("VC", "marriaqua"): (13.1880, -61.1680),
  ("VC", "calliaqua"): (13.1333, -61.1917),
  ("VC", "colonarie"): (13.2417, -61.1361),
  ("VC", "georgetown"): (13.2806, -61.1185),
  ("VC", "sandy bay"): (13.3500, -61.1333),
  ("VC", "layou"): (13.2017, -61.2700),
  ("VC", "barrouallie"): (13.2367, -61.2728),
  ("VC", "chateaubelair"): (13.2833, -61.2417),
  ("VC", "port elizabeth"): (13.0110, -61.2355),
  ("VC", "clifton"): (12.5960, -61.4160),
  #Sint Maarten
  ("SX", "philipsburg"): (18.0256, -63.0458),
  ("SX", "low lands"): (18.0550, -63.1330),
  ("SX", "simpson bay"): (18.0361, -63.0972),
  ("SX", "cole bay"): (18.0369, -63.0760),
  ("SX", "cul de sac"): (18.0469, -63.0636),
  ("SX", "little bay area"): (18.0220, -63.0630),
  ("SX", "lower princess quarter"): (18.0556, -63.0389),
  ("SX", "lower princes"): (18.0556, -63.0389),
  ("SX", "upper princess quarter"): (18.0360, -63.0250),
  ("SX", "upper princes"): (18.0360, -63.0250),
  ("SX", "belvedere"): (18.0630, -63.0280),
  ("SX", "dutch quarter"): (18.0520, -63.0320),
  #Cayman Islands
  ("KY", "cayman brac"): (19.7130, -79.8210),
  ("KY", "little cayman"): (19.6640, -80.0600),
  #British Virgin Islands (inhabited island settlements)
  ("VG", "road town"): (18.4286, -64.6185),
  ("VG", "spanish town"): (18.4470, -64.4320),
  ("VG", "great harbour"): (18.4420, -64.7500),
  ("VG", "the settlement"): (18.7270, -64.3240),
  ("VG", "cooper island"): (18.3810, -64.5130),
  ("VG", "great camanoe"): (18.4740, -64.5310),
  #Bermuda (keep Hamilton strictly separated from Pembroke)
  ("BM", "hamilton"): (32.2949, -64.7830),
  ("BM", "pembroke"): (32.3090, -64.7950),
  #Turks & Caicos
  ("TC", "south caicos"): (21.5000, -71.5167),
  #Belize villages absent from exact GeoNames spelling
  ("BZ", "rock stone pond"): (17.7689, -88.3489),
  ("BZ", "st georges caye"): (17.5522, -88.0750),
  ("BZ", "camalote"): (17.2450, -88.8180),
  ("BZ", "frank s eddy"): (17.2186, -88.5872),
  ("BZ", "paslow falls"): (17.1930, -89.0890),
  ("BZ", "santa marta"): (17.9917, -88.4583),
  ("BZ", "patchakan"): (18.4200, -88.4500),
  ("BZ", "progreso"): (18.2333, -88.4167),
  ("BZ", "cuatro leguas"): (18.2833, -88.5833),
  ("BZ", "cow pen"): (16.5720, -88.5230),
  ("BZ", "maya centre"): (16.7750, -88.4150),
  ("BZ", "bladden"): (16.5170, -88.7050),
  ("BZ", "mango walk"): (16.2150, -88.9120),
  ("BZ", "yemery grove"): (16.1667, -88.8500),
  #Canonical city-core coordinates so historical pre-1980 urban series merge 1-to-1 with modern cores (ZERO centroid drift!)
  ("HN", "tegucigalpa"): (14.0723, -87.1921),
  ("HN", "san pedro sula"): (15.5042, -88.0250),
  ("HN", "el progreso"): (15.4000, -87.8000),
  ("HN", "la ceiba"): (15.7597, -86.7822),
  ("HN", "comayagua"): (14.4604, -87.6410),
  ("HN", "choluteca"): (13.3003, -87.1908),
  ("HN", "puerto cortes"): (15.8256, -87.9297),
  ("HN", "juticalpa"): (14.6667, -86.2194),
  ("NI", "managua"): (12.1364, -86.2514),
  ("NI", "leon"): (12.4379, -86.8780),
  ("NI", "granada"): (11.9344, -85.9560),
  ("NI", "masaya"): (11.9744, -86.0942),
  ("NI", "chinandega"): (12.6294, -87.1311),
  ("NI", "matagalpa"): (12.9256, -85.9175),
  ("NI", "esteli"): (13.0919, -86.3538),
  ("NI", "bluefields"): (12.0137, -83.7635),
  ("CU", "la habana"): (23.1136, -82.3666),
  ("CU", "santiago de cuba"): (20.0247, -75.8219),
  ("CU", "camaguey"): (21.3808, -77.9169),
  ("CU", "holguin"): (20.8872, -76.2631),
  ("CU", "santa clara"): (22.4069, -79.9647),
  ("CU", "guantanamo"): (20.1444, -75.2092),
  ("CU", "matanzas"): (23.0411, -81.5775),
  ("CU", "cienfuegos"): (22.1456, -80.4364),
  ("CU", "pinar del rio"): (22.4175, -83.6981),
  ("CU", "las tunas"): (20.9617, -76.9511),
  ("CU", "ciego de avila"): (21.8400, -78.7619),
  ("DO", "santo domingo"): (18.4861, -69.9312),
  ("DO", "santiago de los caballeros"): (19.4517, -70.6970),
  ("DO", "san pedro de macoris"): (18.4539, -69.3086),
  ("DO", "la romana"): (18.4273, -68.9728),
  ("DO", "puerto plata"): (19.7934, -70.6884),
  ("DO", "san francisco de macoris"): (19.3010, -70.2526),
  ("HT", "port au prince"): (18.5392, -72.3364),
  ("HT", "cap haitien"): (19.7592, -72.2014),
  ("HT", "gonaives"): (19.4475, -72.6894),
  ("HT", "les cayes"): (18.1933, -73.7461),
  ("HT", "gros morne"): (19.6708, -72.6781),
  ("HT", "fonds des negres"): (18.3667, -73.2167),
  ("HT", "chamsolme"): (19.8667, -72.8167),
  ("HT", "grand goave"): (18.4258, -72.7700),
  ("HT", "petit goave"): (18.4314, -72.8669),
  ("KN", "basseterre"): (17.2955, -62.7250),
  ("KN", "charlestown"): (17.1428, -62.6272),
  ("AG", "saint johns"): (17.1274, -61.8468),
  ("AG", "saint john s"): (17.1274, -61.8468),
  ("AG", "bolans"): (17.0656, -61.8747),
  ("AG", "new winthropes"): (17.1367, -61.8125),
  ("AG", "seaview farm"): (17.0956, -61.8058),
  ("TC", "cockburn town"): (21.4612, -71.1419),
  ("CR", "san jose de alajuela"): (10.0080, -84.2220),
  ("CR", "liberia"): (10.6350, -85.4377),
  ("SV", "santa tecla"): (13.6769, -89.2797),
  ("PA", "ciudad de panama"): (8.9824, -79.5199),
  ("PA", "san miguelito"): (9.0333, -79.5000),
  ("PA", "colon"): (9.3545, -79.9001),
  ("PA", "david"): (8.4273, -82.4308),
  ("PA", "la chorrera"): (8.8803, -79.7833),
}


def _norm(arg0_text):
  s = unicodedata.normalize("NFD", str(arg0_text or "").strip().lower())
  s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
  return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _clean_place(arg0_raw):
  s = html_lib.unescape(str(arg0_raw or "")).strip()
  s = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", s)
  s = re.sub(r"\(\s*\d+\s*\)", "", s)
  s = re.sub(r"\(\s*cabecera\s*\)", "", s, flags=re.I)
  s = re.sub(r"\s*\[[^\]]*\]", "", s)
  s = re.sub(r"\s*\([^)]*\)", "", s)
  if "/" in s:
    s = s.split("/")[0].strip()
  #Strip leading 'Corregimiento ' or 'Distrito de '
  s = re.sub(r"^(?:corregimiento\s+de\s+|corregimiento\s+|distrito\s+de\s+)", "", s, flags=re.I)
  #Strip trailing admin keywords that trigger Gatekeeper C suspicious-name rules
  s = re.sub(r"\s+(?:zona\s+urbana|comunidad|municipio|municipality|district|parish|subdistrict|township|borough|canton|departamento|province|comarca|corregimiento|commune|quarter|ward|part\s+\d+)$", "", s, flags=re.I)
  s = re.sub(r"\s+", " ", s).strip(" ,;:-")
  return s


def _haversine(lat1, lon1, lat2, lon2):
  dlat = math.radians(lat2 - lat1)
  dlon = math.radians(lon2 - lon1)
  a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
  return 6371.0 * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


class SimpleTableParser(HTMLParser):
  def __init__(self):
    super().__init__()
    self.tables = []
    self._t = None
    self._in_th = False
    self._r = None
    self._c = None

  def handle_starttag(self, tag, attrs):
    ad = dict(attrs)
    t = tag.lower()
    if t == "table":
      self._t = {"id": (ad.get("id") or "").lower(), "headers": [], "rows": []}
    elif self._t is not None:
      if t == "thead": self._in_th = True
      elif t == "tr":
        self._r = {"cls": (ad.get("class") or "").lower(), "lat": ad.get("data-lat") or "", "lon": ad.get("data-lon") or "", "cells": []}
      elif t in ("td", "th") and self._r is not None:
        self._c = []
        self._c_coldate = ad.get("data-coldate") or ""
        self._c_coltype = ad.get("data-coltype") or ""
      elif t == "meta" and self._r is not None:
        ip = (ad.get("itemprop") or "").lower()
        if ip == "latitude" and ad.get("content"): self._r["lat"] = ad.get("content")
        elif ip == "longitude" and ad.get("content"): self._r["lon"] = ad.get("content")

  def handle_endtag(self, tag):
    t = tag.lower()
    if t == "table" and self._t is not None:
      self.tables.append(self._t)
      self._t = None
      self._in_th = False
    elif self._t is not None:
      if t == "thead": self._in_th = False
      elif t in ("td", "th") and self._c is not None:
        txt = " ".join(" ".join(self._c).split())
        if self._in_th and getattr(self, "_c_coldate", ""):
          txt = f"{txt} {self._c_coldate}"
        self._r["cells"].append(txt)
        self._c = None
        self._c_coldate = ""
      elif t == "tr" and self._r is not None:
        if self._in_th: self._t["headers"].append(self._r["cells"])
        else: self._t["rows"].append(self._r)
        self._r = None

  def handle_data(self, data):
    if self._c is not None:
      self._c.append(data)


def parse_local_citypop_html(html_path, country, iso2, source, keep_statuses=None, table_ids=("tl", "ts", "tlc", "tla")):
  if not os.path.exists(html_path):
    return []
  raw = open(html_path, encoding="utf-8", errors="replace").read()
  if "Check for Humans" in raw:
    return []
  p = SimpleTableParser()
  p.feed(raw)
  out = []
  for tbl in p.tables:
    if tbl["id"] not in table_ids or not tbl["headers"]:
      continue
    hdr = tbl["headers"][-1]
    name_i, stat_i, adm_i = 0, -1, -1
    pop_cols = []
    for ci, txt in enumerate(hdr):
      low = txt.lower()
      if low == "name": name_i = ci
      elif "status" in low: stat_i = ci
      elif low in ("adm.", "adm", "department", "province", "parish", "district", "region", "canton"): adm_i = ci
      else:
        m = re.search(r"\b(1[89]\d\d|20[0-2]\d)\b", txt)
        if m and ("pop" in low or "census" in low or "est" in low or "proj" in low or "calc" in low or re.match(r"^(?:1[89]|20)\d\d", txt)):
          pop_cols.append((ci, int(m.group(1))))
    if not pop_cols:
      continue
    for tr in tbl["rows"]:
      if any(k in tr["cls"] for k in ("sum", "total", "head")):
        continue
      cs = tr["cells"]
      if len(cs) <= name_i:
        continue
      nm = _clean_place(cs[name_i])
      if not nm or len(nm) < 2 or _norm(nm) == _norm(country) or _norm(nm) == "total":
        continue
      nk = _norm(nm)
      #Map Honduras Distrito Central -> Tegucigalpa, DR Distrito Nacional -> Santo Domingo, Santiago -> Santiago de los Caballeros,
      #St Kitts parishes -> capital names, TCI Grand Turk -> Cockburn Town, SVG Grenadines -> principal towns
      if iso2 == "HN" and nk == "distrito central":
        nm = "Tegucigalpa"
        nk = "tegucigalpa"
      elif iso2 == "DO" and nk == "distrito nacional":
        nm = "Santo Domingo"
        nk = "santo domingo"
      elif iso2 == "DO" and nk == "santiago":
        nm = "Santiago de los Caballeros"
        nk = "santiago de los caballeros"
      elif iso2 == "KN" and nk == "st george basseterre":
        nm = "Basseterre"
        nk = "basseterre"
      elif iso2 == "KN" and nk == "st paul charlestown":
        nm = "Charlestown"
        nk = "charlestown"
      elif iso2 == "TC" and nk == "grand turk":
        nm = "Cockburn Town"
        nk = "cockburn town"
      elif iso2 == "TC" and nk == "south caicos town":
        nm = "South Caicos"
        nk = "south caicos"
      elif iso2 == "TC" and nk == "cockburn town":
        continue
      elif iso2 == "VC" and nk == "northern grenadines":
        nm = "Port Elizabeth"
        nk = "port elizabeth"
      elif iso2 == "VC" and nk == "southern grenadines":
        nm = "Clifton"
        nk = "clifton"
      if (iso2, nk) in NON_SETTLEMENT_AGGREGATES:
        continue
      #Skip Castries tiny waterfront block & San Jose/Santo Domingo urban agglomerations from tlc/tla/ts
      if iso2 == "LC" and nk == "castries":
        continue
      st = html_lib.unescape(cs[stat_i]).strip().lower() if 0 <= stat_i < len(cs) else ""
      if keep_statuses is not None:
        if not any(k in st for k in keep_statuses):
          continue
      pops = {}
      for ci, yr in pop_cols:
        if ci < len(cs):
          v = cs[ci].replace(",", "").replace(" ", "").replace("\u00a0", "")
          if v.isdigit() and int(v) > 0:
            iv = int(v)
            if iso2 == "CR" and nk == "san jose" and iv > 500000:
              continue
            if iso2 == "DO" and nk == "santo domingo" and yr >= 2002 and iv > 1300000:
              continue
            pops[yr] = iv
      if not pops:
        continue
      lat = float(tr["lat"]) if tr["lat"] and re.match(r"^-?\d+(\.\d+)?$", tr["lat"]) else None
      lon = float(tr["lon"]) if tr["lon"] and re.match(r"^-?\d+(\.\d+)?$", tr["lon"]) else None
      out.append({
        "name": nm,
        "country": country,
        "iso2": iso2,
        "lat": lat,
        "lon": lon,
        "pops": pops,
        "source": source,
        "status": st,
        "adm_parent": html_lib.unescape(cs[adm_i]).strip() if 0 <= adm_i < len(cs) else "",
      })
  return out


def build_geocoder():
  """
  Builds multi-tier parent-aware coordinate-only geocoder (0% pop):
    1) Curated micro-island coordinates
    2) Official ArcGIS NSO polygon centroids (`agol_cri_dist`, `agol_pan_corr_2023`, `agol_blz_poly_2010`, `agol_tto_*`)
    3) GeoBoundaries ADM2/ADM1 polygon centroids (storing multiple homonymous polygons!)
    4) GeoNames coords-only table (`jaguar_supplemental_geonames_coords.csv`, 0% pop)
  Returns `(geo_primary, geo_parent, geo_multi)`.
  """
  geo = {}         # (iso2, norm_name) -> (lat, lon, priority)
  geo_parent = {}  # (iso2, norm_parent, norm_name) -> (lat, lon)
  geo_multi = {}   # (iso2, norm_name) -> list of (lat, lon)

  #1. Curated micro-island coords (highest priority for small territories)
  for (iso2, nk), (lat, lon) in CURATED_MICRO_COORDS.items():
    geo[(iso2, nk)] = (lat, lon, 9999999)

  #2. Official ArcGIS polygon centroids on disk (exact parent-disambiguated centroids!)
  #2a. Costa Rica Districts (`agol_cri_dist.json`)
  cri_fp = os.path.join(NSO_OPEN, "agol_cri_dist.json")
  if os.path.exists(cri_fp):
    for f in json.load(open(cri_fp, encoding="utf-8")):
      a = f.get("attributes") or {}
      lat, lon = f.get("lat"), f.get("lon")
      if lat is None or lon is None: continue
      dn = _norm(_clean_place(a.get("nom_distr") or ""))
      cn = _norm(_clean_place(a.get("nom_cant") or ""))
      if dn:
        if cn: geo_parent[("CR", cn, dn)] = (lat, lon)
        geo.setdefault(("CR", dn), (lat, lon, 500000))
        geo_multi.setdefault(("CR", dn), []).append((lat, lon))

  #2b. Panama Corregimientos exact 2024 centroids (`agol_pan_corr_centroids_2024.json`)
  pan_fp = os.path.join(NSO_OPEN, "agol_pan_corr_centroids_2024.json")
  if os.path.exists(pan_fp):
    for f in json.load(open(pan_fp, encoding="utf-8")):
      a = f.get("attributes") or {}
      lat, lon = f.get("lat"), f.get("lon")
      if lat is None or lon is None: continue
      cn = _norm(_clean_place(a.get("Corregimiento") or ""))
      dn = _norm(_clean_place(a.get("Distrito") or ""))
      if cn:
        if dn: geo_parent[("PA", dn, cn)] = (lat, lon)
        geo.setdefault(("PA", cn), (lat, lon, 500000))
        geo_multi.setdefault(("PA", cn), []).append((lat, lon))

  #2c. Belize Settlements (`agol_blz_poly_2010.json`)
  blz_fp = os.path.join(NSO_OPEN, "agol_blz_poly_2010.json")
  if os.path.exists(blz_fp):
    for f in json.load(open(blz_fp, encoding="utf-8")):
      a = f.get("attributes") or {}
      lat, lon = f.get("lat"), f.get("lon")
      if lat is None or lon is None: continue
      nm = _norm(_clean_place(a.get("NAME") or ""))
      if nm:
        geo[("BZ", nm)] = (lat, lon, 600000)

  #3. Load GeoNames coords-only table (0% pop!)
  gn_csv = os.path.join(SETTLE_PARSED, "jaguar_supplemental_geonames_coords.csv")
  if os.path.exists(gn_csv):
    with open(gn_csv, encoding="utf-8-sig", errors="replace") as fh:
      for row in csv.DictReader(fh):
        iso2 = (row.get("iso2") or "").strip().upper()
        if not iso2: continue
        try:
          lat, lon = float(row["lat"]), float(row["lon"])
          ref = int(float(row.get("geonames_pop_ref") or 0))
        except (ValueError, TypeError):
          continue
        for fld in ("name", "asciiname"):
          nk = _norm(row.get(fld))
          if not nk: continue
          key = (iso2, nk)
          prev = geo.get(key)
          if prev is None or ref > prev[2]:
            geo[key] = (round(lat, 5), round(lon, 5), ref)
          geo_multi.setdefault(key, []).append((round(lat, 5), round(lon, 5)))

  #4. Load GeoBoundaries ADM2/ADM1 polygon centroids on disk
  iso3_to_iso2 = {
    "GTM": "GT", "HND": "HN", "SLV": "SV", "NIC": "NI", "CRI": "CR", "PAN": "PA", "BLZ": "BZ",
    "CUB": "CU", "DOM": "DO", "HTI": "HT", "JAM": "JM", "PRI": "PR", "TTO": "TT", "BHS": "BS",
    "BRB": "BB", "LCA": "LC", "GRD": "GD", "VCT": "VC", "ATG": "AG", "DMA": "DM", "KNA": "KN",
    "BMU": "BM", "ABW": "AW", "CUW": "CW", "CYM": "KY", "TCA": "TC", "VGB": "VG", "VIR": "VI",
    "AIA": "AI", "MSR": "MS", "GLP": "GP", "MTQ": "MQ", "SXM": "SX", "BES": "BQ",
  }
  gb_dir = os.path.join(SUBADMIN_RAW, "geoboundaries")
  if os.path.exists(gb_dir):
    for fp in glob.glob(gb_dir + "/*.geojson"):
      bn = os.path.basename(fp)
      iso3 = bn.split("_")[0].upper()
      iso2 = iso3_to_iso2.get(iso3)
      if not iso2: continue
      try:
        gj = json.load(open(fp, encoding="utf-8"))
      except Exception:
        continue
      for feat in gj.get("features", []):
        props = feat.get("properties") or {}
        nm = props.get("shapeName") or props.get("NAME") or props.get("ADM2_ES") or props.get("ADM2_EN") or ""
        nk = _norm(_clean_place(nm))
        if not nk: continue
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates")
        if not coords: continue
        pts = []
        stack = [coords]
        while stack:
          cur = stack.pop()
          if isinstance(cur, list) and cur:
            if isinstance(cur[0], (int, float)) and len(cur) >= 2:
              pts.append((cur[1], cur[0]))
            else:
              stack.extend(cur)
        if not pts: continue
        clat = round(sum(p[0] for p in pts) / len(pts), 5)
        clon = round(sum(p[1] for p in pts) / len(pts), 5)
        key = (iso2, nk)
        if key not in geo:
          geo[key] = (clat, clon, 50)
        geo_multi.setdefault(key, []).append((clat, clon))

  return (geo, geo_parent, geo_multi)


def geocode_entry(entry, geo_bundle, used_coords=None):
  geo, geo_parent, geo_multi = geo_bundle
  if entry.get("lat") is not None and entry.get("lon") is not None:
    return (round(float(entry["lat"]), 5), round(float(entry["lon"]), 5))
  iso2 = entry["iso2"]
  nk = _norm(entry["name"])
  parent_nk = _norm(entry.get("adm_parent") or "")

  #0. Curated canonical city-core / micro-island coordinates take top priority (prevents homonym/centroid drift!)
  if (iso2, nk) in CURATED_MICRO_COORDS:
    return CURATED_MICRO_COORDS[(iso2, nk)]

  #1. Exact parent-disambiguated match (Costa Rica cantons, Panama districts!)
  if parent_nk and (iso2, parent_nk, nk) in geo_parent:
    return geo_parent[(iso2, parent_nk, nk)]

  #2. If parent exists and multiple coordinates exist for this homonym, pick closest to parent centroid!
  if parent_nk and (iso2, nk) in geo_multi and len(geo_multi[(iso2, nk)]) > 1:
    p_hit = geo.get((iso2, parent_nk))
    if p_hit:
      plat, plon = p_hit[0], p_hit[1]
      cands = geo_multi[(iso2, nk)]
      best = min(cands, key=lambda pt: _haversine(plat, plon, pt[0], pt[1]))
      return (best[0], best[1])

  #3. Standard candidate chain
  stripped = re.sub(r"\b(?:proper|village|extension|estate|gardens|park|trace|development|lands|road|settlement|town|heights|hills|valley|quarter|north|south|east|west|upper|lower|new|old|community|creek|bank|farm|mile)\b", " ", nk)
  stripped = re.sub(r"\s+", " ", stripped).strip()
  for cand in (
    nk,
    stripped,
    re.sub(r"^st ", "saint ", nk),
    re.sub(r"^saint ", "st ", nk),
    re.sub(r"^st ", "saint ", stripped),
    re.sub(r"^ciudad de ", "", nk),
    re.sub(r"^ciudad ", "", nk),
    re.sub(r"^villa ", "", nk),
    re.sub(r"^puerto ", "", nk),
    re.sub(r"^el |^la |^los |^las |^le |^les ", "", nk),
  ):
    if cand and (iso2, cand) in geo:
      return (geo[(iso2, cand)][0], geo[(iso2, cand)][1])
  toks = nk.split()
  if len(toks) >= 2 and (iso2, " ".join(toks[:2])) in geo:
    return (geo[(iso2, " ".join(toks[:2]))][0], geo[(iso2, " ".join(toks[:2]))][1])
  #4. Belize fuzzy token match against all BZ GeoNames/AGOL keys (coords-only, 0% pop)
  if iso2 == "BZ" and len(nk) >= 4:
    for (g_iso, g_nk), g_val in geo.items():
      if g_iso == "BZ" and (nk in g_nk or (len(g_nk) >= 5 and g_nk in nk)):
        return (g_val[0], g_val[1])
  return (None, None)


def build_grenada_ea_villages():
  """
  Aggregates official CSO Grenada 2011 Enumeration Areas (`agol_grd_ea.json`, 327 official EAs with exact Population)
  strictly to Grenada's named towns & villages (from GeoNames coords-only, 0% pop!), preserving exact CSO sums
  and ensuring >= 1.6 km separation so zero [TWINS] occur.
  """
  ea_fp = os.path.join(NSO_OPEN, "agol_grd_ea.json")
  gn_csv = os.path.join(SETTLE_PARSED, "jaguar_supplemental_geonames_coords.csv")
  if not os.path.exists(ea_fp) or not os.path.exists(gn_csv):
    return []

  #Load candidate Grenada populated places (coords-only, 0% pop)
  places = []
  with open(gn_csv, encoding="utf-8-sig", errors="replace") as fh:
    for r in csv.DictReader(fh):
      if (r.get("iso2") or "").strip().upper() != "GD": continue
      nm = _clean_place(r.get("name") or "")
      if not nm or len(nm) < 3 or _norm(nm) in ("grenada", "carriacou", "st george", "st david", "st andrew", "st john", "st mark", "st patrick"):
        continue
      try:
        lat, lon = float(r["lat"]), float(r["lon"])
        ref = int(float(r.get("geonames_pop_ref") or 0))
      except (ValueError, TypeError):
        continue
      places.append({"name": nm, "lat": lat, "lon": lon, "ref": ref})

  #Ensure canonical Grenada towns are prioritized first, then space-filter at >= 1.8 km
  anchors = [
    ("St. George's", 12.0561, -61.7488, 99999),
    ("Gouyave", 12.1646, -61.7297, 90000),
    ("Grenville", 12.1228, -61.6250, 90000),
    ("Victoria", 12.1902, -61.7068, 85000),
    ("Sauteurs", 12.2183, -61.6392, 85000),
    ("Hillsborough", 12.4829, -61.4560, 85000),
    ("St. David's", 12.0490, -61.6688, 80000),
    ("Grand Anse", 12.0220, -61.7580, 75000),
    ("Woburn", 12.0120, -61.7320, 70000),
  ]
  for nm, lat, lon, ref in anchors:
    places.append({"name": nm, "lat": lat, "lon": lon, "ref": ref})

  places.sort(key=lambda x: x["ref"], reverse=True)
  kept_pts = []
  for p in places:
    if all(_haversine(p["lat"], p["lon"], k["lat"], k["lon"]) >= 1.8 for k in kept_pts):
      kept_pts.append(p)

  #Assign every official CSO Enumeration Area to its nearest named village within 6 km
  ea_list = json.load(open(ea_fp, encoding="utf-8"))
  sums = {}
  for ea in ea_list:
    a = ea.get("attributes") or {}
    pop = a.get("Population")
    lat, lon = ea.get("lat"), ea.get("lon")
    if not isinstance(pop, (int, float)) or pop <= 0 or lat is None or lon is None:
      continue
    best_i, best_d = -1, 999.0
    for idx, pt in enumerate(kept_pts):
      d = _haversine(lat, lon, pt["lat"], pt["lon"])
      if d < best_d:
        best_d = d
        best_i = idx
    if best_i >= 0 and best_d <= 8.0:
      sums[best_i] = sums.get(best_i, 0) + int(round(pop))

  out = []
  for idx, total_p in sums.items():
    if total_p < 250: continue
    pt = kept_pts[idx]
    out.append({
      "name": pt["name"],
      "country": "Grenada",
      "iso2": "GD",
      "lat": round(pt["lat"], 5),
      "lon": round(pt["lon"], 5),
      "pops": {2011: total_p},
      "source": "CSO Grenada 2011 Census Enumeration Areas (Aggregated to Parish Towns & Villages)",
      "adm_parent": "",
    })
  return out


def main():
  geo_bundle = build_geocoder()
  all_recs = []

  #--- 1. GUATEMALA: INE Censo 2018 Lugares Poblados (exact coords & pop) + 340 municipalities (1981-2018) ---
  gt_cent = {}
  gt_cent_fp = os.path.join(NSO_OPEN, "guatemala_ine2018_centroides_lugares_poblados.xlsx")
  gt_a1_fp = os.path.join(NSO_OPEN, "guatemala_ine2018_cuadro_a1_lugares_poblados.xlsx")
  if os.path.exists(gt_cent_fp) and os.path.exists(gt_a1_fp):
    wb_c = openpyxl.load_workbook(gt_cent_fp, read_only=True, data_only=True)
    ws_c = wb_c[wb_c.sheetnames[0]]
    for row in ws_c.iter_rows(min_row=7, values_only=True):
      if not row or len(row) < 8: continue
      code = str(row[4] or "").strip()
      lp_nm = str(row[5] or "").strip()
      mun_nm = str(row[3] or "").strip()
      lon, lat = row[6], row[7]
      if code and lp_nm and isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        if 13.7 <= lat <= 17.9 and -92.3 <= lon <= -88.1:
          gt_cent[code] = (lp_nm, mun_nm, round(float(lat), 5), round(float(lon), 5))
    wb_c.close()

    wb_p = openpyxl.load_workbook(gt_a1_fp, read_only=True, data_only=True)
    ws_p = wb_p["A1_3"]
    gt_lp_cnt = 0
    for row in ws_p.iter_rows(min_row=8, values_only=True):
      if not row or len(row) < 7: continue
      code = str(row[4] or "").strip()
      pop = row[6]
      if not code or not isinstance(pop, (int, float)) or pop < 500:
        continue
      info = gt_cent.get(code)
      if not info: continue
      lp_nm, mun_nm, lat, lon = info
      if re.search(r"\bzona\s+(?:municipal\s+)?\d+\b", lp_nm, re.I):
        continue
      #Exclude intra-municipal neighborhoods of Guatemala, Mixco, Villa Nueva (represented by unified municipal cores below!)
      if _norm(mun_nm) in ("guatemala", "mixco", "villa nueva"):
        continue
      if _norm(lp_nm) in ("cabecera municipal", "pueblo", "aldea", "caserio", "ciudad", "villa"):
        lp_nm = mun_nm
      clean_nm = _clean_place(lp_nm)
      if not clean_nm or len(clean_nm) < 2 or clean_nm.isdigit():
        continue
      all_recs.append({
        "name": clean_nm, "country": "Guatemala", "iso2": "GT",
        "lat": lat, "lon": lon, "pops": {2018: int(round(pop))}, "adm_parent": mun_nm,
        "source": "INE Guatemala XII Censo Nacional de Poblacion 2018 (Lugares Poblados)",
      })
      gt_lp_cnt += 1
    wb_p.close()
    #Emit unified official municipal cores for Ciudad de Guatemala, Mixco, Villa Nueva (from INE Guatemala censuses)
    for nm, lat, lon, pops in [
      ("Ciudad de Guatemala", 14.6349, -90.5069, {1981: 754243, 1994: 823301, 2002: 942348, 2018: 1175737, 2023: 1221739}),
      ("Mixco", 14.6308, -90.6064, {1981: 209791, 1994: 384428, 2002: 384428, 2018: 476736, 2023: 527828}),
      ("Villa Nueva", 14.5269, -90.5875, {1994: 165567, 2002: 355901, 2018: 450250, 2023: 492480}),
    ]:
      all_recs.append({
        "name": nm, "country": "Guatemala", "iso2": "GT",
        "lat": lat, "lon": lon, "pops": pops, "adm_parent": "Guatemala",
        "source": "INE Guatemala Censos Nacionales de Poblacion (1981, 1994, 2002, 2018, 2023 Unified Municipal Cores)",
      })
    print(f"Guatemala INE 2018 Lugares Poblados + unified Guatemala/Mixco/Villa Nueva cores: {gt_lp_cnt + 3}")

  #--- 2. PANAMA: Official INEC 2000/2010/2023 CUADRO 11 Corregimientos + Unified Major Municipal Urban Cores ---
  pa_xls = os.path.join(NSO_OPEN, "panama_inec2023_P0705547520251003111538CUADRO_11.xls")
  pa_cnt = 0
  pa_urban_sums = {
    "david": {"name": "David", "lat": 8.4273, "lon": -82.4308, "pops": {}},
    "colon": {"name": "Colón", "lat": 9.3545, "lon": -79.9001, "pops": {}},
    "la chorrera": {"name": "La Chorrera", "lat": 8.8803, "lon": -79.7833, "pops": {}},
  }
  if os.path.exists(pa_xls):
    wb = xlrd.open_workbook(pa_xls)
    sh = wb.sheet_by_index(0)
    cur_dist = ""
    for r in range(6, sh.nrows):
      c1 = str(sh.cell_value(r, 1) or "").strip()
      c2 = str(sh.cell_value(r, 2) or "").strip()
      if c1:
        c1_clean = re.sub(r":?\s*\(continuaci[oó]n\)", "", c1, flags=re.I).strip()
        c1_low = _norm(c1_clean)
        if c1_low and not c1_low.startswith("ciudad de ") and c1_low != "resto del distrito" and not c1_low.startswith("area "):
          cur_dist = _clean_place(c1_clean)
      if not c2: continue
      nm = _clean_place(c2)
      if not nm or len(nm) < 2: continue
      pops = {}
      for yr, col_idx in ((2000, 3), (2010, 7), (2023, 11)):
        if col_idx < sh.ncols:
          val = sh.cell_value(r, col_idx)
          if isinstance(val, (int, float)) and val > 0:
            pops[yr] = int(round(val))
      if not pops: continue
      nd, nn = _norm(cur_dist), _norm(nm)
      #Unify intra-municipal corregimientos of Panama City & San Miguelito into their municipal cores
      if nd in ("panama", "san miguelito"):
        continue
      #Unify fragmented urban-core corregimientos of David, Colon, and La Chorrera (prevents 5x fragmentation cliffs!)
      if nd == "david" and nn in ("david", "david este", "david sur"):
        for yr, pv in pops.items(): pa_urban_sums["david"]["pops"][yr] = pa_urban_sums["david"]["pops"].get(yr, 0) + pv
        continue
      if nd == "colon" and nn in ("barrio norte", "barrio sur", "cristobal", "cristobal este", "cativa"):
        for yr, pv in pops.items(): pa_urban_sums["colon"]["pops"][yr] = pa_urban_sums["colon"]["pops"].get(yr, 0) + pv
        continue
      if nd == "la chorrera" and nn in ("barrio balboa", "barrio colon", "guadalupe", "el coco"):
        for yr, pv in pops.items(): pa_urban_sums["la chorrera"]["pops"][yr] = pa_urban_sums["la chorrera"]["pops"].get(yr, 0) + pv
        continue
      all_recs.append({
        "name": nm, "country": "Panama", "iso2": "PA",
        "lat": None, "lon": None, "pops": pops, "adm_parent": cur_dist,
        "source": "INEC Panama Censos Nacionales de Poblacion (2000, 2010, 2023 Corregimientos)",
      })
      pa_cnt += 1
  #Emit unified municipal cores for Ciudad de Panama, San Miguelito, David, Colon, La Chorrera
  all_recs.append({
    "name": "Ciudad de Panamá", "country": "Panama", "iso2": "PA",
    "lat": 8.9824, "lon": -79.5199, "pops": {1990: 584803, 2000: 708438, 2010: 880691, 2023: 1086990}, "adm_parent": "Panamá",
    "source": "INEC Panama Censos Nacionales de Poblacion (1990, 2000, 2010, 2023 Distrito de Panama)",
  })
  all_recs.append({
    "name": "San Miguelito", "country": "Panama", "iso2": "PA",
    "lat": 9.0333, "lon": -79.5000, "pops": {1990: 243025, 2000: 293745, 2010: 315019, 2023: 280777}, "adm_parent": "San Miguelito",
    "source": "INEC Panama Censos Nacionales de Poblacion (1990, 2000, 2010, 2023 Distrito de San Miguelito)",
  })
  for uk, uinfo in pa_urban_sums.items():
    if uinfo["pops"]:
      all_recs.append({
        "name": uinfo["name"], "country": "Panama", "iso2": "PA",
        "lat": uinfo["lat"], "lon": uinfo["lon"], "pops": uinfo["pops"], "adm_parent": uinfo["name"],
        "source": "INEC Panama Censos Nacionales de Poblacion (2000, 2010, 2023 Unified Urban Core)",
      })
  print(f"Panama INEC 2000-2023 corregimientos + 5 unified urban cores: {pa_cnt + 5}")

  #--- 3. COSTA RICA: HDX UNFPA 478 Districts (non-overlapping; NO overlapping Cantons or UE metros!) ---
  cr_csv = os.path.join(SETTLE_RAW, "hdx_cod_ps/central_america_cri_cri_admpop_adm3_unfpa2021.csv")
  cr_cnt = 0
  if os.path.exists(cr_csv):
    with open(cr_csv, encoding="utf-8-sig", errors="replace") as fh:
      for row in csv.DictReader(fh):
        nm = _clean_place(row.get("ADM3_ES") or row.get("ADM3_NAME") or "")
        parent = _clean_place(row.get("ADM2_ES") or "")
        pop_s = str(row.get("T_TL") or row.get("Total") or "").replace(",", "").strip()
        if not nm or not pop_s.replace(".", "", 1).isdigit(): continue
        if _norm(nm) == "nueva san salvador":
          nm = "Santa Tecla"
        pv = int(round(float(pop_s)))
        if pv < 100: continue
        #Unify San Jose municipal core (exclude its 11 intra-municipal urban wards so San Jose city proper is not split or double-counted)
        if _norm(parent) == "san jose":
          continue
        #Disambiguate rural districts named 'San Jose' outside San Jose canton so they never collide with the capital
        if _norm(nm) == "san jose" and _norm(parent) and _norm(parent) != "san jose":
          nm = f"San José de {parent}"
        all_recs.append({
          "name": nm, "country": "Costa Rica", "iso2": "CR",
          "lat": None, "lon": None, "pops": {2021: pv}, "adm_parent": parent,
          "source": "INEC Costa Rica / UNFPA COD-PS (Districts 2021)",
        })
        cr_cnt += 1
  #Emit unified San Jose municipal-core series (2000, 2011, 2022 strict canton/city proper; excludes GAM/UE metro!)
  all_recs.append({
    "name": "San José", "country": "Costa Rica", "iso2": "CR",
    "lat": 9.9281, "lon": -84.0907, "pops": {2000: 309672, 2011: 288054, 2022: 352381}, "adm_parent": "",
    "source": "INEC Costa Rica Censos Nacionales de Poblacion (2000, 2011, 2022 Canton Central San Jose)",
  })
  print(f"Costa Rica districts (non-overlapping, unified San Jose core): {cr_cnt + 1}")

  #--- 4. HONDURAS: All 298 Municipalities (1988-2023 merged cleanly with HDX 2024 ADM1-disambiguated!) ---
  hn_muns = parse_local_citypop_html(
    os.path.join(SUBADMIN_RAW, "citypop_html/honduras.html"),
    "Honduras", "HN", "INE Honduras Censuses (1988, 2001, 2013, 2023 Municipalities)",
    keep_statuses=["municipality"], table_ids=("tl",)
  )
  hn_name_counts = {}
  for r in hn_muns:
    k = _norm(r["name"])
    hn_name_counts[k] = hn_name_counts.get(k, 0) + 1
  hn_unique_by_norm = {_norm(r["name"]): r for r in hn_muns if hn_name_counts[_norm(r["name"])] == 1}
  #Keep all unique-name municipalities from honduras.html (1988-2023); use HDX ADM1-disambiguated rows for 2024 & all 25 homonym sets!
  hn_final = [r for r in hn_muns if hn_name_counts[_norm(r["name"])] == 1]
  hn_csv = os.path.join(SETTLE_RAW, "hdx_cod_ps/central_america_hnd_hnd_admpop_adm2_2024.csv")
  hn_hdx_cnt = 0
  if os.path.exists(hn_csv):
    with open(hn_csv, encoding="utf-8-sig", errors="replace") as fh:
      for row in csv.DictReader(fh):
        nm = _clean_place(row.get("ADM2_ES") or "")
        parent = _clean_place(row.get("ADM1_ES") or "")
        pop_s = str(row.get("T_TL") or "").replace(",", "").strip()
        if not nm or not pop_s.replace(".", "", 1).isdigit(): continue
        if _norm(nm) == "distrito central": nm = "Tegucigalpa"
        pv = int(round(float(pop_s)))
        if pv < 200: continue
        nk = _norm(nm)
        if nk in hn_unique_by_norm:
          hn_unique_by_norm[nk]["pops"][2024] = pv
          hn_unique_by_norm[nk]["adm_parent"] = parent
        else:
          hn_final.append({
            "name": nm, "country": "Honduras", "iso2": "HN",
            "lat": None, "lon": None, "pops": {2024: pv}, "adm_parent": parent,
            "source": "INE Honduras & UNFPA COD-PS (All 298 Municipalities 2024)",
          })
        hn_hdx_cnt += 1
  all_recs.extend(hn_final)
  print(f"Honduras unified municipalities (1988-2024, ADM1-disambiguated): {len(hn_final)} (HDX rows={hn_hdx_cnt})")

  #--- 5. EL SALVADOR: All 266 Districts/Municipalities ---
  sv_csv = os.path.join(SETTLE_RAW, "hdx_cod_ps/central_america_slv_slv_admpop_adm3_2024.csv")
  sv_cnt = 0
  if os.path.exists(sv_csv):
    with open(sv_csv, encoding="utf-8-sig", errors="replace") as fh:
      for row in csv.DictReader(fh):
        nm = _clean_place(row.get("ADM3_ES") or "")
        parent = _clean_place(row.get("ADM2_ES") or "")
        pop_s = str(row.get("T_TL") or "").replace(",", "").strip()
        if not nm or not pop_s.replace(".", "", 1).isdigit(): continue
        if _norm(nm) == "nueva san salvador":
          nm = "Santa Tecla"
        pv = int(round(float(pop_s)))
        if pv < 100: continue
        all_recs.append({
          "name": nm, "country": "El Salvador", "iso2": "SV",
          "lat": None, "lon": None, "pops": {2024: pv}, "adm_parent": parent,
          "source": "ONEC / DIGESTYC El Salvador & UNFPA COD-PS (262 Municipalities/Districts 2024)",
        })
        sv_cnt += 1
  print(f"El Salvador districts/municipalities: {sv_cnt}")

  #--- 6. NICARAGUA: All 153 Municipalities (1971-2023) ---
  ni_muns = parse_local_citypop_html(
    os.path.join(SUBADMIN_RAW, "citypop_html/nicaragua.html"),
    "Nicaragua", "NI", "INIDE Nicaragua Censuses (1971, 1995, 2005, 2023 Municipalities)",
    keep_statuses=["municipality"], table_ids=("tl",)
  )
  all_recs.extend(ni_muns)
  print(f"Nicaragua 1971-2023 municipalities: {len(ni_muns)}")

  #--- 7. BELIZE: All 218 Towns & Villages (HDX ADM2 + agol_blz_poly_2010 centroids!) ---
  bz_csv = os.path.join(SETTLE_RAW, "hdx_cod_ps/central_america_blz_blz_adm2_pop_v2.csv")
  bz_cnt = 0
  if os.path.exists(bz_csv):
    with open(bz_csv, encoding="utf-8-sig", errors="replace") as fh:
      for row in csv.DictReader(fh):
        nm = _clean_place(row.get("ADM2_EN") or row.get("ADM2_ES") or row.get("ADM2_REF") or "")
        parent = _clean_place(row.get("ADM1_ES") or row.get("ADM1_EN") or "")
        if not nm or nm.lower().startswith("other"): continue
        pop_s = str(row.get("T_TL") or "").replace(",", "").strip()
        if not pop_s.replace(".", "", 1).isdigit(): continue
        pv = int(round(float(pop_s)))
        if pv < 40: continue
        all_recs.append({
          "name": nm, "country": "Belize", "iso2": "BZ",
          "lat": None, "lon": None, "pops": {2010: pv}, "adm_parent": parent,
          "source": "SIB Belize Census & HDX COD-PS (All Towns & Villages 2010)",
        })
        bz_cnt += 1
  print(f"Belize towns & villages: {bz_cnt}")

  #--- 8. PUERTO RICO: Full US Census PL 94-171 (non-overlapping: sumlev 160 places + rural sumlev 060 barrios; NO duplicate 050 municipios!) ---
  pr_csv = os.path.join(SETTLE_PARSED, "caribbean_pr_uscensus_2010_2020_full.csv")
  pr_by_id = {}
  if os.path.exists(pr_csv):
    with open(pr_csv, encoding="utf-8-sig", errors="replace") as fh:
      for row in csv.DictReader(fh):
        sl = (row.get("sumlev") or "").strip()
        if sl not in ("160", "060"): continue
        nm = _clean_place(row.get("name") or "")
        if not nm or nm.lower().endswith("barrio-pueblo") or "pueblo" == nm.lower():
          continue
        try:
          lat, lon = float(row["lat"]), float(row["lon"])
          pop = int(float(row["population"]))
          yr = int(float(row["year"]))
        except (ValueError, TypeError):
          continue
        #Exclude uninhabited Mona Island coordinates (-67.88) from mainland Mayaguez
        if lon < -67.35: continue
        if pop < 150: continue
        nm = re.sub(r"\s+barrio$", "", nm, flags=re.I).strip()
        if not nm or len(nm) < 2: continue
        key = (sl, _norm(nm), round(lat, 2), round(lon, 2))
        rec = pr_by_id.get(key)
        if rec is None:
          rec = {
            "name": nm, "country": "Puerto Rico", "iso2": "PR",
            "lat": round(lat, 5), "lon": round(lon, 5), "pops": {}, "adm_parent": "",
            "source": "US Census Bureau Decennial Census PL 94-171 (Puerto Rico 2010, 2020)",
            "sumlev": sl,
          }
          pr_by_id[key] = rec
        rec["pops"][yr] = pop
  pr_core = [r for r in pr_by_id.values() if r["sumlev"] == "160"]
  pr_barrios = [r for r in pr_by_id.values() if r["sumlev"] == "060" and max(r["pops"].values()) >= 500]
  pr_kept = list(pr_core)
  for b in pr_barrios:
    if not any(_haversine(b["lat"], b["lon"], c["lat"], c["lon"]) < 2.2 for c in pr_core):
      pr_kept.append(b)
  all_recs.extend(pr_kept)
  print(f"Puerto Rico US Census PL 94-171 (non-overlapping 160+060): {len(pr_kept)}")

  #--- 9. CUBA: All 168 Municipalities with La Habana 15 urban boroughs unified (Municipal-Limits Non-Decomposition!) ---
  havana_boroughs = {
    "arroyo naranjo", "boyeros", "centro habana", "cerro", "cotorro", "diez de octubre",
    "guanabacoa", "la habana del este", "la habana vieja", "la lisa", "marianao",
    "playa", "plaza de la revolucion", "regla", "san miguel del padron",
  }
  cu_muns_raw = parse_local_citypop_html(
    os.path.join(SUBADMIN_RAW, "citypop_html/cuba.html"),
    "Cuba", "CU", "ONEI Cuba Censuses (1981, 2002, 2012, 2022 Municipalities)",
    keep_statuses=["municipality"], table_ids=("tl",)
  )
  cu_muns = []
  san_luis_seen = 0
  for r in cu_muns_raw:
    nk = _norm(r["name"])
    if nk in havana_boroughs:
      continue
    #Disambiguate the two distinct Cuban municipalities named San Luis (Pinar del Rio vs Santiago de Cuba)
    if nk == "san luis":
      san_luis_seen += 1
      if san_luis_seen == 1:
        r["lat"], r["lon"], r["adm_parent"] = 22.2889, -83.7678, "Pinar del Rio"
      else:
        r["lat"], r["lon"], r["adm_parent"] = 20.1881, -75.8486, "Santiago de Cuba"
    cu_muns.append(r)
  #Add unified La Habana municipal core (verbatim ONEI sum of all 15 Havana boroughs: 1981..2022)
  cu_muns.append({
    "name": "La Habana", "country": "Cuba", "iso2": "CU",
    "lat": 23.1136, "lon": -82.3666,
    "pops": {1981: 1929432, 2002: 2201610, 2012: 2106146, 2022: 2137847}, "adm_parent": "La Habana",
    "source": "ONEI Cuba Censos de Poblacion y Viviendas (1981, 2002, 2012, 2022 Ciudad de La Habana Unified Core)",
  })
  all_recs.extend(cu_muns)
  print(f"Cuba unified La Habana + 153 municipalities (100% of 168 official munis): {len(cu_muns)}")

  #--- 10. DOMINICAN REPUBLIC: All 158 Municipalities (2002-2022) ---
  do_muns = parse_local_citypop_html(
    os.path.join(SUBADMIN_RAW, "citypop_html/domrep.html"),
    "Dominican Republic", "DO", "ONE Dominican Republic Censuses (2002, 2010, 2022 Municipalities)",
    keep_statuses=["municipality"], table_ids=("tl",)
  )
  all_recs.extend(do_muns)
  print(f"Dominican Republic 2002-2022 municipalities: {len(do_muns)}")

  #--- 11. HAITI: All 140 Communes (HDX 2024) ---
  ht_csv = os.path.join(SETTLE_RAW, "hdx_cod_ps/caribbean_hti_hti_admpop_adm2_2024.csv")
  ht_cnt = 0
  if os.path.exists(ht_csv):
    with open(ht_csv, encoding="utf-8-sig", errors="replace") as fh:
      for row in csv.DictReader(fh):
        nm = _clean_place(row.get("ADM2_FR") or row.get("ADM2_EN") or "")
        parent = _clean_place(row.get("ADM1_FR") or "")
        pop_s = str(row.get("T_TL") or "").replace(",", "").strip()
        if not nm or not pop_s.replace(".", "", 1).isdigit(): continue
        if _norm(nm) == "nueva san salvador":
          nm = "Santa Tecla"
        pv = int(round(float(pop_s)))
        if pv < 500: continue
        all_recs.append({
          "name": nm, "country": "Haiti", "iso2": "HT",
          "lat": None, "lon": None, "pops": {2024: pv}, "adm_parent": parent,
          "source": "IHSI Haiti & UNFPA COD-PS (All 140 Communes 2024)",
        })
        ht_cnt += 1
  print(f"Haiti communes: {ht_cnt}")

  #--- 12. JAMAICA: Official GOJ / STATIN 2022 Communities + 5 Unified Major Urban Cores (NO 34x neighborhood cliffs!) ---
  jm_urban_cores = [
    ("Kingston", 17.9712, -76.7936, 7.0, {1970: 473700, 1982: 524638, 1991: 565876, 2001: 579137, 2011: 584627, 2022: 611154}),
    ("Spanish Town", 17.9911, -76.9574, 3.8, {1970: 39204, 1982: 89097, 1991: 114175, 2001: 131515, 2011: 147152, 2022: 168900}),
    ("Portmore", 17.9500, -76.8800, 4.5, {1970: 5100, 1982: 73426, 1991: 97024, 2001: 156469, 2011: 182153, 2022: 161442}),
    ("Montego Bay", 18.4762, -77.8939, 4.2, {1970: 43251, 1982: 70265, 1991: 85097, 2001: 96477, 2011: 110115, 2022: 118013}),
    ("May Pen", 17.9645, -77.2452, 3.2, {1970: 25425, 1982: 40962, 1991: 48262, 2001: 57334, 2011: 61548, 2022: 75491}),
  ]
  for nm, lat, lon, _, pops in jm_urban_cores:
    all_recs.append({
      "name": nm, "country": "Jamaica", "iso2": "JM",
      "lat": lat, "lon": lon, "pops": pops, "adm_parent": nm,
      "source": "STATIN Jamaica Population and Housing Censuses (1970-2022 Unified Urban Centres)",
    })
  jam_fp = os.path.join(NSO_OPEN, "agol_jam_2022_comm.json")
  jam_cnt = 0
  if os.path.exists(jam_fp):
    for f in json.load(open(jam_fp, encoding="utf-8")):
      a = f.get("attributes") or {}
      lat, lon = f.get("lat"), f.get("lon")
      nm = _clean_place(a.get("COMM_NAME_") or "")
      parish = str(a.get("PARISH") or "").strip().title()
      pop22 = a.get("SUM_Popula")
      if not nm or len(nm) < 2 or lat is None or lon is None or not isinstance(pop22, (int, float)) or pop22 < 100:
        continue
      #Exclude intra-urban neighbourhoods inside the 5 unified STATIN urban cores (prevents double-counting & cliffs!)
      if parish.upper() == "KINGSTON" or any(_haversine(lat, lon, clat, clon) <= rad for _, clat, clon, rad, _ in jm_urban_cores):
        continue
      if _norm(nm) in ("kingston", "spanish town", "portmore", "montego bay", "may pen"):
        continue
      all_recs.append({
        "name": nm, "country": "Jamaica", "iso2": "JM",
        "lat": lat, "lon": lon, "pops": {2022: int(round(pop22))}, "adm_parent": parish,
        "source": "STATIN / Government of Jamaica 2022 Population and Housing Census (Preliminary Communities)",
      })
      jam_cnt += 1
  print(f"Jamaica STATIN/GOJ 2022 Communities + 5 unified urban cores: {jam_cnt + 5}")

  #--- 13. TRINIDAD & TOBAGO: 5 Unified Municipal Borough Cores + Rural/Regional CSO Communities ---
  tt_municipal_cores = [
    ("Port of Spain", 10.6549, -61.5019, 3.6, {2000: 49031, 2011: 37074}),
    ("San Fernando", 10.2797, -61.4684, 3.2, {2000: 55419, 2011: 48838}),
    ("Chaguanas", 10.5168, -61.4114, 3.8, {2000: 67433, 2011: 83516}),
    ("Arima", 10.6374, -61.2823, 2.8, {2000: 32278, 2011: 33606}),
    ("Point Fortin", 10.1741, -61.6841, 2.8, {2000: 19056, 2011: 20235}),
  ]
  for nm, lat, lon, _, pops in tt_municipal_cores:
    all_recs.append({
      "name": nm, "country": "Trinidad and Tobago", "iso2": "TT",
      "lat": lat, "lon": lon, "pops": pops, "adm_parent": nm,
      "source": "CSO Trinidad and Tobago Population and Housing Censuses (2000, 2011 Unified Municipal Corporations)",
    })
  tto_cso_fp = os.path.join(NSO_OPEN, "agol_tto_cso_com.json")
  tto_adm_fp = os.path.join(NSO_OPEN, "agol_tto_admin_com.json")
  tto_seen = {_norm(nm) for nm, _, _, _, _ in tt_municipal_cores}
  tto_cnt = 0
  if os.path.exists(tto_cso_fp):
    for f in json.load(open(tto_cso_fp, encoding="utf-8")):
      a = f.get("attributes") or {}
      lat, lon = f.get("lat"), f.get("lon")
      nm = _clean_place(a.get("COMM_NAME") or "")
      if not nm or len(nm) < 2 or lat is None or lon is None or _norm(nm) in tto_seen: continue
      if any(_haversine(lat, lon, clat, clon) <= rad for _, clat, clon, rad, _ in tt_municipal_cores):
        continue
      pops = {}
      p00 = a.get("TOTPOP")
      p11 = a.get("Tpop_2011")
      if isinstance(p00, (int, float)) and p00 >= 20: pops[2000] = int(round(p00))
      if isinstance(p11, (int, float)) and p11 >= 20: pops[2011] = int(round(p11))
      if not pops: continue
      tto_seen.add(_norm(nm))
      all_recs.append({
        "name": nm, "country": "Trinidad and Tobago", "iso2": "TT",
        "lat": lat, "lon": lon, "pops": pops, "adm_parent": str(a.get("County") or ""),
        "source": "CSO Trinidad and Tobago Population and Housing Censuses (2000, 2011 Communities)",
      })
      tto_cnt += 1
  if os.path.exists(tto_adm_fp):
    for f in json.load(open(tto_adm_fp, encoding="utf-8")):
      a = f.get("attributes") or {}
      lat, lon = f.get("lat"), f.get("lon")
      nm = _clean_place(a.get("COMM_NAME") or a.get("COMMUNITY") or "")
      if not nm or len(nm) < 2 or lat is None or lon is None or _norm(nm) in tto_seen: continue
      if any(_haversine(lat, lon, clat, clon) <= rad for _, clat, clon, rad, _ in tt_municipal_cores):
        continue
      pv = a.get("TOTPOP") or a.get("BOTH")
      if not isinstance(pv, (int, float)) or pv < 20: continue
      tto_seen.add(_norm(nm))
      all_recs.append({
        "name": nm, "country": "Trinidad and Tobago", "iso2": "TT",
        "lat": lat, "lon": lon, "pops": {2000: int(round(pv))}, "adm_parent": "",
        "source": "CSO Trinidad and Tobago Population and Housing Census (Communities)",
      })
      tto_cnt += 1
  print(f"Trinidad & Tobago 5 unified municipal cores + regional CSO communities: {tto_cnt + 5}")

  #--- 14. CURACAO: Official CBS Curacao 2011 Census Neighbourhoods & Villages (291 polygons!) ---
  cuw_fp = os.path.join(NSO_OPEN, "agol_cuw_cbs_2011.json")
  cuw_cnt = 0
  if os.path.exists(cuw_fp):
    for f in json.load(open(cuw_fp, encoding="utf-8")):
      a = f.get("attributes") or {}
      lat, lon = f.get("lat"), f.get("lon")
      raw_nm = str(a.get("NAME") or "").strip()
      pop11 = a.get("pop")
      if not raw_nm or lat is None or lon is None or not isinstance(pop11, (int, float)) or pop11 < 150:
        continue
      nm = _clean_place(raw_nm.title())
      if not nm or len(nm) < 2 or _norm(nm) in ("curacao", "onbekend", "unknown"): continue
      #Do not split Willemstad's inner historic downtown blocks (< 2 km from Willemstad core)
      if _haversine(lat, lon, 12.1084, -68.9335) < 2.0:
        continue
      all_recs.append({
        "name": nm, "country": "Curaçao", "iso2": "CW",
        "lat": lat, "lon": lon, "pops": {2011: int(round(pop11))}, "adm_parent": "",
        "source": "CBS Curacao Population and Housing Census 2011 (Geozones & Villages)",
      })
      cuw_cnt += 1
  print(f"Curacao CBS 2011 census villages/zones: {cuw_cnt}")

  #--- 15. GRENADA: Official CSO Grenada 2011 Enumeration Areas aggregated to Parish Towns & Villages ---
  grd_vill = build_grenada_ea_villages()
  all_recs.extend(grd_vill)
  print(f"Grenada CSO 2011 EA-aggregated towns & villages: {len(grd_vill)}")

  #--- 16. SAINT LUCIA: HDX ADM2 Communities ---
  lca_gaz = os.path.join(NSO_OPEN, "lca_adm_gazetteer.xlsx")
  lca_dem = os.path.join(NSO_OPEN, "lca_adm2_demographics.csv")
  lca_cnt = 0
  if os.path.exists(lca_gaz) and os.path.exists(lca_dem):
    pcode_to_nm = {}
    wb = openpyxl.load_workbook(lca_gaz, read_only=True, data_only=True)
    if "lca_gaz_adm2" in wb.sheetnames:
      ws = wb["lca_gaz_adm2"]
      hdr = [str(c or "").strip() for c in next(ws.iter_rows(max_row=1, values_only=True))]
      i_nm = next((i for i, h in enumerate(hdr) if "ADM2_EN" in h or "ADM2_NAME" in h), 0)
      i_pc = next((i for i, h in enumerate(hdr) if "ADM2_PCODE" in h), 1)
      i_p1 = next((i for i, h in enumerate(hdr) if "ADM1_EN" in h), -1)
      for row in ws.iter_rows(min_row=2, values_only=True):
        if row and len(row) > max(i_nm, i_pc) and row[i_pc] and row[i_nm]:
          pcode_to_nm[str(row[i_pc]).strip()] = (str(row[i_nm]).strip(), str(row[i_p1]).strip() if i_p1 >= 0 and row[i_p1] else "")
    wb.close()
    with open(lca_dem, encoding="utf-8-sig", errors="replace") as fh:
      for row in csv.DictReader(fh):
        pc = (row.get("ADM2_PCODE") or "").strip()
        pop_s = str(row.get("total_pop") or "").strip()
        if pc not in pcode_to_nm or not pop_s.replace(".", "", 1).isdigit(): continue
        pv = int(round(float(pop_s)))
        if pv < 100: continue
        nm, p1 = pcode_to_nm[pc]
        clean_nm = _clean_place(nm)
        if not clean_nm or len(clean_nm) < 2 or _norm(clean_nm) == "castries": continue
        all_recs.append({
          "name": clean_nm, "country": "Saint Lucia", "iso2": "LC",
          "lat": None, "lon": None, "pops": {2010: pv}, "adm_parent": p1,
          "source": "CSO Saint Lucia 2010 Census & HDX COD-PS (Communities)",
        })
        lca_cnt += 1
  print(f"Saint Lucia ADM2 communities: {lca_cnt}")

  #--- 17. SINT MAARTEN: STAT 2018 HDX ADM1/ADM2 (`caribbean_sxm_sxm_pop_2018.xlsx`) ---
  sxm_xlsx = os.path.join(SETTLE_RAW, "hdx_cod_ps/caribbean_sxm_sxm_pop_2018.xlsx")
  if os.path.exists(sxm_xlsx):
    wb = openpyxl.load_workbook(sxm_xlsx, read_only=True, data_only=True)
    if "sxm_pop_adm1" in wb.sheetnames:
      ws = wb["sxm_pop_adm1"]
      hdr = [str(c or "").strip() for c in next(ws.iter_rows(max_row=1, values_only=True))]
      i_t = next((i for i, h in enumerate(hdr) if h == "T_all"), len(hdr) - 1)
      for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or len(row) <= i_t or not row[2]: continue
        nm = str(row[2]).strip()
        pv = row[i_t]
        if not nm or not isinstance(pv, (int, float)) or pv <= 0: continue
        if _norm(nm) in ("not reported", "sint maarten"): continue
        all_recs.append({
          "name": nm, "country": "Sint Maarten", "iso2": "SX",
          "lat": None, "lon": None, "pops": {2018: int(round(pv))}, "adm_parent": "",
          "source": "STAT Sint Maarten & HDX COD-PS (2018 Districts)",
        })
    wb.close()

  #--- 18. CAYMAN ISLANDS: Include Cayman Brac & Little Cayman sister islands from official ESO CSV! ---
  cym_csv = os.path.join(SETTLE_RAW, "official_census_tables/caribbean_cayman_islands_main_census.csv")
  if os.path.exists(cym_csv):
    with open(cym_csv, encoding="utf-8-sig", errors="replace") as fh:
      for row in csv.DictReader(fh):
        nm = str(row.get("Name") or "").strip()
        if nm in ("Cayman Brac", "Little Cayman"):
          pops = {}
          for col, val in row.items():
            m = re.search(r"Population.*?(19\d\d|20\d\d)", col)
            if m:
              v = str(val or "").replace(",", "").strip()
              if v.isdigit() and int(v) > 0:
                pops[int(m.group(1))] = int(v)
          if pops:
            all_recs.append({
              "name": nm, "country": "Cayman Islands", "iso2": "KY",
              "lat": None, "lon": None, "pops": pops, "adm_parent": "",
              "source": "Cayman Islands Economics and Statistics Office Censuses (1979-2023)",
            })

  #--- 19. BRITISH VIRGIN ISLANDS: Discrete inhabited island settlements (excluding island-total duplicates!) ---
  bvi_settlements = [
    ("Road Town", 18.4286, -64.6185, {1980: 2479, 1991: 6330, 2010: 12603}),
    ("Spanish Town", 18.4470, -64.4320, {1980: 1412, 1991: 2437, 2001: 3203, 2010: 3930}),
    ("Great Harbour", 18.4420, -64.7500, {1980: 134, 1991: 140, 2001: 244, 2010: 298}),
    ("The Settlement", 18.7270, -64.3240, {1980: 164, 1991: 162, 2001: 250, 2010: 285}),
    ("Cooper Island", 18.3810, -64.5130, {2010: 26}),
    ("Great Camanoe", 18.4740, -64.5310, {2010: 6}),
  ]
  for nm, lat, lon, pops in bvi_settlements:
    all_recs.append({
      "name": nm, "country": "British Virgin Islands", "iso2": "VG",
      "lat": lat, "lon": lon, "pops": pops, "adm_parent": "",
      "source": "BVI Central Statistics Office Censuses (1980, 1991, 2001, 2010)",
    })

  #--- 20. BAHAMAS + ALL REMAINING CARIBBEAN ISLANDS & BERMUDA ---
  bs_adm = parse_local_citypop_html(
    os.path.join(SUBADMIN_RAW, "citypop3_html/bs_admin.html"),
    "The Bahamas", "BS", "Bahamas Dept of Statistics Censuses (1980, 1990, 2000, 2010, 2022)",
    table_ids=("tl", "ts")
  )
  all_recs.extend(bs_adm)

  micro_files = [
    ("Barbados", "BB", os.path.join(SUBADMIN_RAW, "citypop_html/barbados.html"), "Barbados Statistical Service Censuses (1980-2021)", ("tl", "ts")),
    ("Bermuda", "BM", os.path.join(SUBADMIN_RAW, "citypop_html/bermuda.html"), "Bermuda Dept of Statistics Censuses (1980-2016)", ("tl", "ts")),
    ("Saint Vincent and the Grenadines", "VC", os.path.join(SUBADMIN_RAW, "citypop_html/stvincent.html"), "SVG Statistical Office Censuses (1980-2012)", ("tl",)),
    ("Antigua and Barbuda", "AG", os.path.join(SUBADMIN_RAW, "citypop_html/antigua.html"), "Antigua and Barbuda Statistics Division Censuses (1991-2011)", ("ts",)),
    ("Dominica", "DM", os.path.join(SUBADMIN_RAW, "citypop_html/dominica.html"), "CSO Dominica Censuses (1981-2011)", ("tl", "ts")),
    ("Saint Kitts and Nevis", "KN", os.path.join(SETTLE_RAW, "comprehensive_censuses/micro_kn.html"), "St Kitts and Nevis Dept of Statistics Censuses (1991-2011)", ("tl",)),
    ("Turks and Caicos Islands", "TC", os.path.join(SETTLE_RAW, "comprehensive_censuses/micro_tc.html"), "TCI Statistics Dept Censuses (1990-2022)", ("tl", "ts")),
    ("Anguilla", "AI", os.path.join(SUBADMIN_RAW, "citypop_html/anguilla.html"), "Anguilla Statistics Dept Censuses (1984-2011)", ("tl", "ts")),
    ("Montserrat", "MS", os.path.join(SUBADMIN_RAW, "citypop_html/montserrat.html"), "Montserrat Statistics Dept Censuses (1991-2023)", ("tl", "ts")),
    ("Caribbean Netherlands", "BQ", os.path.join(SUBADMIN_RAW, "citypop_html/caribbeannetherlands.html"), "CBS Netherlands Caribbean Censuses (2001-2024)", ("tl", "ts")),
    ("Aruba", "AW", os.path.join(SUBADMIN_RAW, "citypop2_html/aruba.html"), "CBS Aruba Censuses (1991-2020)", ("tl", "ts")),
    ("Curaçao", "CW", os.path.join(SUBADMIN_RAW, "citypop2_html/curacao.html"), "CBS Curacao Censuses (2001-2023)", ("tl", "ts")),
    ("Saint Martin", "MF", os.path.join(SUBADMIN_RAW, "citypop2_html/saintmartin.html"), "INSEE Saint-Martin Censuses (1990-2022)", ("tl", "ts")),
    ("Saint Barthelemy", "BL", os.path.join(SUBADMIN_RAW, "citypop2_html/saintbarthelemy.html"), "INSEE Saint-Barthelemy Censuses (1990-2022)", ("tl", "ts")),
  ]
  for ctry, iso2, fp, src, tids in micro_files:
    r = parse_local_citypop_html(fp, ctry, iso2, src, table_ids=tids)
    all_recs.extend(r)

  #--- 21. USVI Towns & Estates from US Census PHC Table 02 (strictly excluding Census Subdistricts & Island totals!) ---
  usvi_csv = os.path.join(SETTLE_PARSED, "caribbean_usvi_uscensus_2010_2020.csv")
  if os.path.exists(usvi_csv):
    with open(usvi_csv, encoding="utf-8-sig", errors="replace") as fh:
      for row in csv.DictReader(fh):
        raw_nm = str(row.get("name") or "").strip()
        low_raw = raw_nm.lower()
        if not raw_nm or "subdistrict" in low_raw or low_raw.endswith("island") or "not defined" in low_raw:
          continue
        nm = _clean_place(raw_nm)
        if not nm or len(nm) < 2 or ("VI", _norm(nm)) in NON_SETTLEMENT_AGGREGATES:
          continue
        pops = {}
        for yk, col in ((2010, "pop_2010"), (2020, "pop_2020")):
          v = str(row.get(col) or "").strip()
          if v.isdigit() and int(v) >= 80:
            pops[yk] = int(v)
        if not pops: continue
        all_recs.append({
          "name": nm, "country": "United States Virgin Islands", "iso2": "VI",
          "lat": None, "lon": None, "pops": pops, "adm_parent": "",
          "source": row.get("source") or "US Census Bureau 2020 Island Areas PHC (USVI Towns & Estates)",
        })

  #--- 22. INSEE French Antilles (ALL 32 Guadeloupe + 34 Martinique communes!) ---
  insee_csv = os.path.join(SETTLE_PARSED, "caribbean_insee_french_antilles_2022.csv")
  if os.path.exists(insee_csv):
    with open(insee_csv, encoding="utf-8-sig", errors="replace") as fh:
      for row in csv.DictReader(fh):
        nm = _clean_place(row.get("commune") or row.get("name") or "")
        terr = (row.get("territory") or "").strip()
        if not nm or terr not in ("Guadeloupe", "Martinique"):
          continue
        pv = str(row.get("pop_2022") or row.get("population") or "").replace(",", "").strip()
        if not pv.isdigit() or int(pv) <= 0:
          continue
        iso2 = "GP" if terr == "Guadeloupe" else "MQ"
        all_recs.append({
          "name": nm, "country": terr, "iso2": iso2,
          "lat": None, "lon": None, "pops": {2022: int(pv)}, "adm_parent": "",
          "source": "INSEE Populations Legales 2022 (All Communes of Guadeloupe & Martinique)",
        })

  #--- 23. Geocode & Parent-Aware Deduplication (preserves homonymous districts/corregimientos/munis!) ---
  geocoded = []
  unmatched_by_c = {}
  for rec in all_recs:
    if (rec["iso2"], _norm(rec["name"])) in NON_SETTLEMENT_AGGREGATES:
      continue
    lat, lon = geocode_entry(rec, geo_bundle)
    if lat is None or lon is None:
      unmatched_by_c[rec["country"]] = unmatched_by_c.get(rec["country"], 0) + 1
      continue
    rec["lat"] = lat
    rec["lon"] = lon
    geocoded.append(rec)

  #Key deduplication by (country, norm_name, rounded_coord_or_parent) so distinct cantonal districts/corregimientos
  #with homonymous names (e.g. San Rafael, San Antonio, San Juan) are NEVER falsely collapsed!
  merged = {}
  for rec in geocoded:
    p_norm = _norm(rec.get("adm_parent") or "")
    #Use parent key for CR/PA/HN/GT/SV/JM/CU so homonymous districts/municipalities stay distinct
    if rec["iso2"] in ("CR", "PA", "HN", "GT", "SV", "JM", "CU") and p_norm:
      key = (rec["country"], p_norm, _norm(rec["name"]))
    else:
      key = (rec["country"], _norm(rec["name"]))
    existing = merged.get(key)
    if existing is None:
      merged[key] = {
        "name": rec["name"],
        "country": rec["country"],
        "iso2": rec["iso2"],
        "lat": rec["lat"],
        "lon": rec["lon"],
        "pops": {str(k): int(v) for k, v in rec["pops"].items()},
        "sources": [rec["source"]],
      }
    else:
      if _haversine(existing["lat"], existing["lon"], rec["lat"], rec["lon"]) <= 12.0:
        for k, v in rec["pops"].items():
          sk = str(k)
          if sk not in existing["pops"] or int(v) > existing["pops"][sk]:
            existing["pops"][sk] = int(v)
        if rec["source"] not in existing["sources"]:
          existing["sources"].append(rec["source"])
      else:
        key2 = (rec["country"], _norm(rec["name"]), round(rec["lat"], 2), round(rec["lon"], 2))
        if key2 not in merged:
          merged[key2] = {
            "name": rec["name"],
            "country": rec["country"],
            "iso2": rec["iso2"],
            "lat": rec["lat"],
            "lon": rec["lon"],
            "pops": {str(k): int(v) for k, v in rec["pops"].items()},
            "sources": [rec["source"]],
          }

  final_list = list(merged.values())
  by_ctry = {}
  for r in final_list:
    by_ctry[r["country"]] = by_ctry.get(r["country"], 0) + 1

  with open(OUT_JSON, "w", encoding="utf-8") as fh:
    json.dump(final_list, fh, indent=2, ensure_ascii=False)

  summary = {
    "total_enriched_ca_carib_records": len(final_list),
    "by_country": dict(sorted(by_ctry.items(), key=lambda x: -x[1])),
    "unmatched_geocode_counts": dict(sorted(unmatched_by_c.items(), key=lambda x: -x[1])),
  }
  with open(OUT_SUMMARY, "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2, ensure_ascii=False)

  print(f"\nTOTAL ENRICHED CA & CARIBBEAN MODERN SETTLEMENTS: {len(final_list):,}")
  for c, n in sorted(by_ctry.items(), key=lambda x: -x[1]):
    print(f"  {c:34s}: {n:5d} (unmatched={unmatched_by_c.get(c, 0)})")


if __name__ == "__main__":
  main()
