"""Programmatic Full-Row Census & Gazetteer Harvester for Project INDUS.

Downloads 100% full-row official census tables and national gazetteers (zero Top-N caps)
for all 7 sovereign states of INDUS (India, Pakistan, Bangladesh, Sri Lanka, Nepal, Bhutan,
Maldives) plus XRONOS radiocarbon registries and South Asian archaeological CSVs from
Zenodo/Harvard Dataverse/GitHub.
"""

import io
import json
import os
import time
import zipfile

import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
INDUS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "INDUS")
CENSUS_DIR = os.path.join(INDUS_DIR, "_shared", "_census_cache")
RAW_ARCH_DIR = os.path.join(INDUS_DIR, "_shared", "sites_indus_south_asia", "0.raw_data")
os.makedirs(CENSUS_DIR, exist_ok=True)
os.makedirs(RAW_ARCH_DIR, exist_ok=True)

HEADERS = {"User-Agent": "SVEA-OperationViscount-INDUS/1.0"}


def fetch_file(url, dest, timeout=120):
  if os.path.exists(dest) and os.path.getsize(dest) > 500:
    print(f"  [SKIP] Cached: {os.path.basename(dest)} ({os.path.getsize(dest):,} B)")
    return True
  try:
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    if r.status_code == 200 and len(r.content) > 200:
      with open(dest, "wb") as fh:
        fh.write(r.content)
      print(f"  [OK] {os.path.basename(dest)}: {len(r.content):,} B")
      return True
    print(f"  [WARN] {url} -> HTTP {r.status_code}")
  except Exception as e:
    print(f"  [ERR] {url}: {e}")
  return False


def harvest_xronos_full():
  print("[1] Harvesting XRONOS radiocarbon API by country name (full South Asia + 300 km belt)...")
  # Copy already-cached JADE xronos files for IN, NP, BT, MM, CN, TJ, KG, KZ if present
  jade_raw = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "sites_east_asia", "0.raw_data")
  for cc in ["in", "np", "bt", "mm"]:
    src = os.path.join(jade_raw, f"xronos_{cc}.json")
    dst = os.path.join(RAW_ARCH_DIR, f"xronos_{cc}.json")
    if os.path.exists(src) and not os.path.exists(dst):
      with open(src, "rb") as s, open(dst, "wb") as d:
        d.write(s.read())
      print(f"  [COPY] {os.path.basename(dst)} from JADE cache ({os.path.getsize(dst):,} B)")

  # Fetch remaining countries from xronos.ch/api/v1/data?country=<ISO2_or_name>
  for cc, cname in [
    ("pk", "PK"), ("bd", "BD"), ("lk", "LK"), ("mv", "MV"),
    ("af", "AF"), ("ir", "IR"), ("tm", "TM"), ("uz", "UZ"),
    ("in", "IN"), ("np", "NP"), ("bt", "BT"), ("mm", "MM")
  ]:
    dst = os.path.join(RAW_ARCH_DIR, f"xronos_{cc}.json")
    if os.path.exists(dst) and os.path.getsize(dst) > 50:
      continue
    for param_url in [
      f"https://xronos.ch/api/v1/data?country={cname}",
      f"https://xronos.ch/api/v1/data.json?country={cname}"
    ]:
      r = requests.get(param_url, headers=HEADERS, timeout=45)
      if r.status_code == 200:
        with open(dst, "wb") as fh:
          fh.write(r.content)
        print(f"  [OK] XRONOS {cc}: {len(r.content):,} B")
        break
    time.sleep(0.5)


def harvest_geonames_all_7_countries():
  print("[2] Harvesting full GeoNames country dumps (100% populated places, zero Top-N cap)...")
  for cc in ["IN", "PK", "BD", "LK", "NP", "BT", "MV"]:
    zpath = os.path.join(CENSUS_DIR, f"geonames_{cc}.zip")
    fetch_file(f"https://download.geonames.org/export/dump/{cc}.zip", zpath, timeout=180)
  # Also alternateNames for South Asia historical/native names? (Wait — allCountries alt names is huge; we can fetch per-country or use Wikidata/Stage F)
  fetch_file("https://download.geonames.org/export/dump/admin1CodesASCII.txt", os.path.join(CENSUS_DIR, "geonames_admin1CodesASCII.txt"))
  fetch_file("https://download.geonames.org/export/dump/admin2Codes.txt", os.path.join(CENSUS_DIR, "geonames_admin2Codes.txt"))


def harvest_official_census_github_repos():
  print("[3] Harvesting official South Asian Census datasets from GitHub / Zenodo / HDX...")
  targets = [
    # Zenodo 3667657 Vidarbha Maharashtra Archaeology (Megalithic & Early Historic Census)
    ("https://zenodo.org/api/records/3667657/files/Vidarbha_SiteMasterList.csv/content", os.path.join(RAW_ARCH_DIR, "zenodo_3667657_Vidarbha_SiteMasterList.csv")),
    ("https://zenodo.org/api/records/3667657/files/Vidarbha_MegalithSites.csv/content", os.path.join(RAW_ARCH_DIR, "zenodo_3667657_Vidarbha_MegalithSites.csv")),
    ("https://zenodo.org/api/records/3667657/files/Vidarbha_CoinSites.csv/content", os.path.join(RAW_ARCH_DIR, "zenodo_3667657_Vidarbha_CoinSites.csv")),
    # Bates 2019 Indus Archaeobotanical Sites CSV (JOAD / Zenodo / Apollo)
    # India Census 2011 ALL towns & districts
    ("https://raw.githubusercontent.com/pigshell/india-census-2011/master/pca-full.csv", os.path.join(CENSUS_DIR, "india_2011_pca_full.csv")),
    ("https://raw.githubusercontent.com/mihirs16/Census-of-India-2011-Dataset/main/india-districts-census-2011.csv", os.path.join(CENSUS_DIR, "india_2011_districts.csv")),
    # Nepal 2021 / Administrative divisions (all 753/775 local units)
    ("https://raw.githubusercontent.com/open-admin-data/nepal-administrative-divisions/main/data/local_units.csv", os.path.join(CENSUS_DIR, "nepal_local_units.csv")),
    ("https://raw.githubusercontent.com/open-admin-data/nepal-administrative-divisions/main/data/districts.csv", os.path.join(CENSUS_DIR, "nepal_districts.csv")),
    # Pakistan 2017 & 2023 Census repos
    ("https://api.github.com/repos/cerp-analytics/pbs2017/git/trees/master?recursive=1", os.path.join(CENSUS_DIR, "_tree_pbs2017.json")),
    ("https://api.github.com/repos/colincookman/pakistan_census/git/trees/master?recursive=1", os.path.join(CENSUS_DIR, "_tree_pakistan_census.json")),
    ("https://api.github.com/repos/myaseen208/PakPC2023/git/trees/master?recursive=1", os.path.join(CENSUS_DIR, "_tree_pakpc2023.json")),
    ("https://api.github.com/repos/justinelliotmeyers/bangladesh_2022_census_gis/git/trees/main?recursive=1", os.path.join(CENSUS_DIR, "_tree_bd2022.json")),
    ("https://api.github.com/repos/saketlab/censusindia/git/trees/main?recursive=1", os.path.join(CENSUS_DIR, "_tree_censusindia.json")),
    ("https://api.github.com/repos/mihirs16/Census-of-India-2011-Dataset/git/trees/main?recursive=1", os.path.join(CENSUS_DIR, "_tree_india2011.json")),
  ]
  for url, dest in targets:
    fetch_file(url, dest, timeout=120)
    time.sleep(0.3)


if __name__ == "__main__":
  harvest_xronos_full()
  harvest_geonames_all_7_countries()
  harvest_official_census_github_repos()
  print("DONE census & XRONOS harvest!")
