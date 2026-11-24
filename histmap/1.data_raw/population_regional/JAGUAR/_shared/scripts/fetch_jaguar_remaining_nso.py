"""Fetch remaining 9 Caribbean NSO pages and inspect Mexico Statoids 1879/1900/1910 reconciliation."""

import html
import json
import os
import re
import time
import urllib.request
from html.parser import HTMLParser

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\subadmin_hgis\raw_sources"
OUT_DIR = os.path.join(RAW_DIR, "citypop3_html")
os.makedirs(OUT_DIR, exist_ok=True)


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


URLS = {
  "pr_admin": "https://www.citypopulation.de/en/usa/puertorico/",
  "gp_admin": "https://www.citypopulation.de/en/france/guadeloupe/admin/",
  "mq_admin": "https://www.citypopulation.de/en/france/martinique/admin/",
  "kn_admin": "https://www.citypopulation.de/en/saintkitts/",
  "ky_admin": "https://www.citypopulation.de/en/cayman/",
  "tc_admin": "https://www.citypopulation.de/en/turks/",
  "ht_admin": "https://www.citypopulation.de/en/haiti/",
  "jm_admin": "https://www.citypopulation.de/en/jamaica/",
  "bz_admin": "https://www.citypopulation.de/en/belize/",
  "tt_admin": "https://www.citypopulation.de/en/trinidad/admin/",
  "bs_admin": "https://www.citypopulation.de/en/bahamas/admin/",
}

res = {}
for k, u in URLS.items():
  fp = os.path.join(OUT_DIR, f"{k}.html")
  try:
    if os.path.exists(fp) and os.path.getsize(fp) > 2000:
      b = open(fp, encoding="utf-8", errors="replace").read()
    else:
      req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
      with urllib.request.urlopen(req, timeout=20) as r:
        b = r.read().decode("utf-8", errors="replace")
      open(fp, "w", encoding="utf-8").write(b)
      time.sleep(0.15)
    tp = TableParser()
    tp.feed(b)
    good = [t for t in tp.tables if t["id"] in ("tl", "ts") or "data" in t["class"]]
    src = re.sub(r"\s+", " ", html.unescape("".join(tp.source_buf))).strip()
    res[k] = {"url": u, "source": src, "tables": good}
    tinfo = [(t["id"], len(t["rows"]), (t["thead"][-1] if t["thead"] else [])[:7]) for t in good[:2]]
    print(f"OK {k:12s}: {len(good)} tbls | {tinfo}")
  except Exception as e:
    print(f"ERR {k:12s}: {e}")

with open(os.path.join(RAW_DIR, "citypop3_jaguar_parsed.json"), "w", encoding="utf-8") as f:
  json.dump(res, f, ensure_ascii=False, indent=2)

# Also inspect Mexico Statoids 1879/1900 & EHM 2014 1910 check
st = json.load(open(os.path.join(RAW_DIR, "statoids_jaguar_parsed.json"), encoding="utf-8"))
mx_t2 = st["mx"]["tables"][2]["rows"]
print("\nMexico Statoids T2 header:", mx_t2[0]["cells"])
for r in mx_t2[1:]:
  if any(x in r["cells"][0] for x in ["Baja", "Quintana", "Distrito", "Total", "TOTAL"]):
    print(" ", r["cells"][:6])
