"""Parses Excel-HTML pop-stat tables (handling unclosed <td>/<tr> tags) to inspect headers & row counts."""
import os
from html.parser import HTMLParser
CENSUS_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\SARAY\_shared\_census_cache"

class LooseTableParser(HTMLParser):
  def __init__(self):
    super().__init__()
    self.rows, self.cur_row, self.cur_cell = [], None, None
  def flush_cell(self):
    if self.cur_cell is not None and self.cur_row is not None:
      self.cur_row.append(" ".join("".join(self.cur_cell).split()))
      self.cur_cell = None
  def handle_starttag(self, tag, attrs):
    t = tag.lower()
    if t == "tr":
      self.flush_cell()
      self.cur_row = []
      self.rows.append(self.cur_row)
    elif t in ("td", "th"):
      self.flush_cell()
      if self.cur_row is None:
        self.cur_row = []
        self.rows.append(self.cur_row)
      self.cur_cell = []
  def handle_endtag(self, tag):
    t = tag.lower()
    if t in ("td", "th", "tr", "table"):
      self.flush_cell()
  def handle_data(self, data):
    if self.cur_cell is not None:
      self.cur_cell.append(data)

for fn in ["popstat_kazakhstan-cities.htm", "popstat_kyrgyzstan-cities.htm", "popstat_tajikistan-cities.htm", "popstat_turkmenistan-cities.htm", "popstat_kazakhstan-census2021.htm", "popstat_kyrgyzstan-census.htm", "popstat_turkmenistan-census.htm"]:
  txt = open(os.path.join(CENSUS_DIR, fn), "r", encoding="utf-8", errors="replace").read()
  tp = LooseTableParser()
  tp.feed(txt)
  non_empty = [r for r in tp.rows if any(c for c in r)]
  print(f"\n=== {fn}: {len(non_empty)} non-empty rows ===")
  for r in non_empty[:7]:
    print("  ", r[:15])
