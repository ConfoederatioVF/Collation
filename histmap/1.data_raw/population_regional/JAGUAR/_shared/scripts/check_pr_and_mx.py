"""Download US Census Bureau PR municipio CSVs and inspect Mexico 1910/1950 PDF parse."""

import csv
import json
import os
import urllib.request

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\subadmin_hgis\raw_sources"

for fn, u in [
  ("pr_est2023.csv", "https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/municipios/totals/prm-est2023-alldata.csv"),
  ("pr_est2019.csv", "https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/municipios/totals/prm-est2019-alldata.csv"),
]:
  fp = os.path.join(RAW_DIR, fn)
  try:
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
      b = r.read()
      open(fp, "wb").write(b)
      print("OK", fn, len(b))
  except Exception as e:
    print("ERR", fn, e)

if os.path.exists(os.path.join(RAW_DIR, "pr_est2023.csv")):
  rows = list(csv.DictReader(open(os.path.join(RAW_DIR, "pr_est2023.csv"), encoding="latin-1")))
  print("PR 2023 rows:", len(rows), "cols:", list(rows[0].keys())[:10])
  print("PR total row:", rows[0].get("NAME"), rows[0].get("ESTIMATESBASE2020"), rows[0].get("POPESTIMATE2020"), rows[0].get("POPESTIMATE2023"))

mx = json.load(open(os.path.join(RAW_DIR, "mexico_inegi_parsed.json"), encoding="utf-8"))["ehm2014"]
print("\n=== MEXICO 1895 / 1900 / 1910 / 1921 / 1950 ===")
for k, v in sorted(mx.items()):
  y = v["years"]
  p95 = y.get("1895", {}).get("pop")
  p00 = y.get("1900", {}).get("pop")
  p10 = y.get("1910", {}).get("pop")
  p21 = y.get("1921", {}).get("pop")
  p50 = y.get("1950", {}).get("pop")
  print(f"  {k:34s} 1895={str(p95):>10s} 1900={str(p00):>10s} 1910={str(p10):>10s} 1921={str(p21):>10s} 1950={str(p50):>10s}")
