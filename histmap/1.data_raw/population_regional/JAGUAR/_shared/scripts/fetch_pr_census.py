"""Fetch US Census Bureau Puerto Rico 2020 (and 2010) municipio populations."""

import csv
import io
import json
import os
import re
import urllib.request

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\subadmin_hgis\raw_sources"

for u in [
  "https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/municipios/totals/",
  "https://www2.census.gov/programs-surveys/popest/tables/2020-2023/municipios/totals/",
  "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/municipios/totals/",
]:
  try:
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
      txt = r.read().decode("utf-8", errors="replace")
      links = [l for l in re.findall(r'href="([^"]+)"', txt) if not l.startswith("?") and not l.startswith("/")]
      print("OK", u, links)
      for l in links:
        if l.endswith(".csv") or l.endswith(".xlsx"):
          dl_u = u + l
          fp = os.path.join(RAW_DIR, l)
          with urllib.request.urlopen(urllib.request.Request(dl_u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r2:
            open(fp, "wb").write(r2.read())
          print("  DOWNLOADED", l, os.path.getsize(fp))
  except Exception as e:
    print("ERR", u, e)
