"""Harvests full Soviet 1897, 1959, 1970, 1979, 1989 urban settlement tables from Demoscope Weekly
plus Uzbekistan modern city census series (citypopulation.de / stat.uz) into _shared/_census_cache/."""

import os
import re
import time
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CENSUS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "SARAY", "_shared", "_census_cache")
os.makedirs(CENSUS_DIR, exist_ok=True)
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SVEA-SARAY/1.0"}


def fetch(url, fn, timeout=60):
  dst = os.path.join(CENSUS_DIR, fn)
  if os.path.exists(dst) and os.path.getsize(dst) > 1000:
    print(f"  [SKIP] {fn} ({os.path.getsize(dst):,} B)", flush=True)
    return True
  for att in range(3):
    try:
      r = requests.get(url, headers=HDR, timeout=timeout)
      if r.status_code == 200 and len(r.content) > 500:
        with open(dst, "wb") as fh:
          fh.write(r.content)
        print(f"  [OK] {fn}: {len(r.content):,} B", flush=True)
        return True
      print(f"  [WARN] {fn} HTTP {r.status_code} (att {att+1})", flush=True)
      time.sleep(3 * (att + 1))
    except Exception as e:
      print(f"  [ERR] {fn}: {e}", flush=True)
      time.sleep(3)
  return False


def main():
  print("=== HARVESTING SOVIET URBAN CENSUS TABLES & UZBEKISTAN CITIES ===", flush=True)
  targets = [
    ("demoscope_1959_urban.html", "https://www.demoscope.ru/weekly/ssp/ussr59_reg2.php"),
    ("demoscope_1970_urban.html", "https://www.demoscope.ru/weekly/ssp/ussr70_reg2.php"),
    ("demoscope_1979_urban.html", "https://www.demoscope.ru/weekly/ssp/ussr79_reg2.php"),
    ("demoscope_1989_urban.html", "https://www.demoscope.ru/weekly/ssp/ussr89_reg2.php"),
    ("demoscope_1926_urban_kaz.html", "https://www.demoscope.ru/weekly/ssp/ussr_26_b.php?reg=131"),
    ("demoscope_1926_urban_uzb.html", "https://www.demoscope.ru/weekly/ssp/ussr_26_b.php?reg=159"),
    ("demoscope_1926_urban_tkm.html", "https://www.demoscope.ru/weekly/ssp/ussr_26_b.php?reg=167"),
    ("citypop_uzbekistan_cities.html", "https://www.citypopulation.de/en/uzbekistan/cities/"),
    ("citypop_uzbekistan_admin.html", "https://www.citypopulation.de/en/uzbekistan/admin/"),
    ("citypop_kazakhstan_cities.html", "https://www.citypopulation.de/en/kazakhstan/cities/"),
    ("citypop_kyrgyzstan_cities.html", "https://www.citypopulation.de/en/kyrgyzstan/cities/"),
    ("citypop_tajikistan_cities.html", "https://www.citypopulation.de/en/tajikistan/cities/"),
    ("citypop_turkmenistan_cities.html", "https://www.citypopulation.de/en/turkmenistan/cities/"),
  ]
  for fn, u in targets:
    fetch(u, fn, timeout=45)
    time.sleep(0.5)
  print("=== DONE ===", flush=True)


if __name__ == "__main__":
  main()
