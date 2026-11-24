"""Fetch and parse official NSO census tables via citypopulation.de (and statoids historical census tables) for JAGUAR."""

import html
import json
import os
import re
import time
import urllib.request
from html.parser import HTMLParser

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\subadmin_hgis\raw_sources"
CP_DIR = os.path.join(RAW_DIR, "citypop_html")
os.makedirs(CP_DIR, exist_ok=True)

CP_PAGES = {
  # Central America
  "guatemala": "https://www.citypopulation.de/en/guatemala/admin/",
  "elsalvador": "https://www.citypopulation.de/en/elsalvador/admin/",
  "honduras": "https://www.citypopulation.de/en/honduras/admin/",
  "nicaragua": "https://www.citypopulation.de/en/nicaragua/admin/",
  "costarica": "https://www.citypopulation.de/en/costarica/admin/",
  "panama": "https://www.citypopulation.de/en/panama/admin/",
  "belize": "https://www.citypopulation.de/en/belize/cities/",
  # Greater Antilles
  "cuba": "https://www.citypopulation.de/en/cuba/admin/",
  "domrep": "https://www.citypopulation.de/en/domrep/admin/",
  "haiti": "https://www.citypopulation.de/en/haiti/cities/",
  "jamaica": "https://www.citypopulation.de/en/jamaica/cities/",
  "puertorico": "https://www.citypopulation.de/en/usa/puertorico/admin/",
  # Lesser Antilles, Bahamas, Trinidad & Tobago, Bermuda
  "barbados": "https://www.citypopulation.de/en/barbados/",
  "trinidad": "https://www.citypopulation.de/en/trinidad/",
  "bahamas": "https://www.citypopulation.de/en/bahamas/",
  "bermuda": "https://www.citypopulation.de/en/bermuda/",
  "guadeloupe": "https://www.citypopulation.de/en/france/guadeloupe/",
  "martinique": "https://www.citypopulation.de/en/france/martinique/",
  "saintmartin": "https://www.citypopulation.de/en/france/saintmartin/",
  "saintbarthelemy": "https://www.citypopulation.de/en/france/saintbarthelemy/",
  "curacao": "https://www.citypopulation.de/en/curacao/",
  "aruba": "https://www.citypopulation.de/en/aruba/",
  "sintmaarten": "https://www.citypopulation.de/en/sintmaarten/",
  "caribbeannetherlands": "https://www.citypopulation.de/en/caribbeannetherlands/",
  "usvi": "https://www.citypopulation.de/en/usa/virginislands/",
  "bvi": "https://www.citypopulation.de/en/britishvirginislands/",
  "anguilla": "https://www.citypopulation.de/en/anguilla/",
  "antigua": "https://www.citypopulation.de/en/antigua/",
  "stkitts": "https://www.citypopulation.de/en/stkitts/",
  "dominica": "https://www.citypopulation.de/en/dominica/",
  "stlucia": "https://www.citypopulation.de/en/stlucia/",
  "stvincent": "https://www.citypopulation.de/en/stvincent/",
  "grenada": "https://www.citypopulation.de/en/grenada/",
  "montserrat": "https://www.citypopulation.de/en/montserrat/",
  "cayman": "https://www.citypopulation.de/en/cayman/",
  "turks": "https://www.citypopulation.de/en/turks/",
}


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
      tid = ad.get("id", "")
      cls = ad.get("class", "")
      if tid in ("tl", "ts") or "data" in cls:
        self.cur_tbl = {"id": tid, "class": cls, "thead": [], "rows": []}
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


def fetch_html (arg0_key, arg1_url):
  fp = os.path.join(CP_DIR, f"{arg0_key}.html")
  if os.path.exists(fp) and os.path.getsize(fp) > 2000:
    return open(fp, encoding="utf-8", errors="replace").read()
  req = urllib.request.Request(arg1_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
  with urllib.request.urlopen(req, timeout=20) as r:
    content = r.read().decode("utf-8", errors="replace")
  with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
  time.sleep(0.2)
  return content


if __name__ == "__main__":
  parsed_all = {}
  for k, url in CP_PAGES.items():
    try:
      content = fetch_html(k, url)
      tp = TableParser()
      tp.feed(content)
      src_txt = re.sub(r"\s+", " ", html.unescape("".join(tp.source_buf))).strip()
      parsed_all[k] = {"url": url, "source": src_txt, "tables": tp.tables}
      t_info = [(t["id"], len(t["rows"]), (t["thead"][-1] if t["thead"] else [])[:7]) for t in tp.tables[:2]]
      print(f"OK {k:22s}: {len(tp.tables)} tbls | {t_info}")
    except Exception as e:
      print(f"ERR {k:22s}: {e}")
  with open(os.path.join(RAW_DIR, "citypop_jaguar_parsed.json"), "w", encoding="utf-8") as f:
    json.dump(parsed_all, f, ensure_ascii=False, indent=2)
