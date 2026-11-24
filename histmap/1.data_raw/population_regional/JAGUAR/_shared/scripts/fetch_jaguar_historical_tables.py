"""Fetch remaining citypopulation.de Admin-1 pages + statoids.com historical sub-admin census tables."""

import html
import json
import os
import re
import time
import urllib.request
from html.parser import HTMLParser

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\subadmin_hgis\raw_sources"
CP2_DIR = os.path.join(RAW_DIR, "citypop2_html")
ST_DIR = os.path.join(RAW_DIR, "statoids_html")
os.makedirs(CP2_DIR, exist_ok=True)
os.makedirs(ST_DIR, exist_ok=True)

# Multi-census Admin-1 pages + missing territories on citypopulation.de
CP2_PAGES = {
  "guatemala_adm1": "https://www.citypopulation.de/en/guatemala/cities/",
  "elsalvador_adm1": "https://www.citypopulation.de/en/elsalvador/cities/",
  "honduras_adm1": "https://www.citypopulation.de/en/honduras/cities/",
  "nicaragua_adm1": "https://www.citypopulation.de/en/nicaragua/cities/",
  "costarica_adm1": "https://www.citypopulation.de/en/costarica/cities/",
  "panama_adm1": "https://www.citypopulation.de/en/panama/cities/",
  "cuba_adm1": "https://www.citypopulation.de/en/cuba/cities/",
  "domrep_adm1": "https://www.citypopulation.de/en/domrep/cities/",
  "puertorico": "https://www.citypopulation.de/en/puertorico/",
  "trinidad": "https://www.citypopulation.de/en/trinidad/cities/",
  "bahamas": "https://www.citypopulation.de/en/bahamas/cities/",
  "guadeloupe": "https://www.citypopulation.de/en/guadeloupe/",
  "martinique": "https://www.citypopulation.de/en/martinique/",
  "saintmartin": "https://www.citypopulation.de/en/saintmartin/",
  "saintbarthelemy": "https://www.citypopulation.de/en/saintbarthelemy/",
  "curacao": "https://www.citypopulation.de/en/curacao/cities/",
  "aruba": "https://www.citypopulation.de/en/aruba/cities/",
  "usvi": "https://www.citypopulation.de/en/usvirginislands/",
  "stkitts": "https://www.citypopulation.de/en/stkitts/cities/",
  "stlucia": "https://www.citypopulation.de/en/stlucia/cities/",
  "cayman": "https://www.citypopulation.de/en/cayman/cities/",
  "turks": "https://www.citypopulation.de/en/turks/cities/",
}

STATOIDS_ISO2 = [
  "mx", "gt", "sv", "hn", "ni", "cr", "pa", "bz",
  "cu", "do", "ht", "jm", "pr",
  "bb", "tt", "bs", "bm", "gp", "mq", "mf", "bl",
  "cw", "aw", "sx", "bq", "vi", "vg", "ai", "ag",
  "kn", "dm", "lc", "vc", "gd", "ms", "ky", "tc",
]


class TableParser(HTMLParser):
  def __init__ (self):
    super().__init__()
    self.tables = []
    self.cur_tbl = None
    self.in_thead = False
    self.cur_row = None
    self.cur_row_cls = ""
    self.in_cell = False
    self.cell_buf = []
    self.in_source = False
    self.source_buf = []

  def handle_starttag (self, tag, attrs):
    ad = dict(attrs)
    if tag in ("section", "div", "p") and ad.get("id") == "source":
      self.in_source = True
    if tag == "table":
      self.cur_tbl = {"id": ad.get("id", ""), "class": ad.get("class", ""), "thead": [], "rows": []}
    elif self.cur_tbl is not None:
      if tag == "thead":
        self.in_thead = True
      elif tag == "tr":
        self.cur_row = []
        self.cur_row_cls = ad.get("class", "")
      elif tag in ("td", "th") and self.cur_row is not None:
        self.in_cell = True
        self.cell_buf = []

  def handle_endtag (self, tag):
    if tag == "section" and self.in_source:
      self.in_source = False
    if self.cur_tbl is not None:
      if tag in ("td", "th") and self.in_cell:
        txt = re.sub(r"\s+", " ", html.unescape("".join(self.cell_buf))).strip()
        self.cur_row.append(txt)
        self.in_cell = False
      elif tag == "tr" and self.cur_row is not None:
        if self.in_thead:
          self.cur_tbl["thead"].append(self.cur_row)
        elif self.cur_row:
          self.cur_tbl["rows"].append({"class": self.cur_row_cls, "cells": self.cur_row})
        self.cur_row = None
      elif tag == "thead":
        self.in_thead = False
      elif tag == "table":
        if self.cur_tbl["rows"]:
          self.tables.append(self.cur_tbl)
        self.cur_tbl = None

  def handle_data (self, data):
    if self.in_cell:
      self.cell_buf.append(data)
    if self.in_source:
      self.source_buf.append(data)


def fetch_url (arg0_fp, arg1_url):
  if os.path.exists(arg0_fp) and os.path.getsize(arg0_fp) > 1000:
    return open(arg0_fp, encoding="utf-8", errors="replace").read()
  req = urllib.request.Request(arg1_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
  with urllib.request.urlopen(req, timeout=20) as r:
    content = r.read().decode("utf-8", errors="replace")
  with open(arg0_fp, "w", encoding="utf-8") as f:
    f.write(content)
  time.sleep(0.15)
  return content


if __name__ == "__main__":
  cp2_out = {}
  print("=== CITYPOPULATION PASS 2 ===")
  for k, url in CP2_PAGES.items():
    try:
      content = fetch_url(os.path.join(CP2_DIR, f"{k}.html"), url)
      tp = TableParser()
      tp.feed(content)
      src_txt = re.sub(r"\s+", " ", html.unescape("".join(tp.source_buf))).strip()
      good_tbls = [t for t in tp.tables if t["id"] in ("tl", "ts") or "data" in t["class"]]
      cp2_out[k] = {"url": url, "source": src_txt, "tables": good_tbls}
      t_info = [(t["id"], len(t["rows"]), (t["thead"][-1] if t["thead"] else [])[:8]) for t in good_tbls[:2]]
      print(f"OK {k:20s}: {len(good_tbls)} tbls | {t_info}")
    except Exception as e:
      print(f"ERR {k:20s}: {e}")
  with open(os.path.join(RAW_DIR, "citypop2_jaguar_parsed.json"), "w", encoding="utf-8") as f:
    json.dump(cp2_out, f, ensure_ascii=False, indent=2)

  print("\n=== STATOIDS HISTORICAL CENSUSES ===")
  st_out = {}
  for iso in STATOIDS_ISO2:
    url = f"http://www.statoids.com/u{iso}.html"
    try:
      content = fetch_url(os.path.join(ST_DIR, f"u{iso}.html"), url)
      tp = TableParser()
      tp.feed(content)
      # Look for population history tables (often class='st' or containing 4-digit years)
      hist_tbls = []
      for t in tp.tables:
        r0 = t["rows"][0]["cells"] if t["rows"] else []
        if any(re.search(r"\b(18\d\d|19\d\d|20\d\d)\b", c) for c in r0) or len(t["rows"]) >= 3:
          hist_tbls.append(t)
      st_out[iso] = {"url": url, "tables": hist_tbls}
      print(f"OK u{iso}: {len(hist_tbls)} tbls | rows={[len(t['rows']) for t in hist_tbls[:4]]}")
    except Exception as e:
      print(f"ERR u{iso}: {e}")
  with open(os.path.join(RAW_DIR, "statoids_jaguar_parsed.json"), "w", encoding="utf-8") as f:
    json.dump(st_out, f, ensure_ascii=False, indent=2)
