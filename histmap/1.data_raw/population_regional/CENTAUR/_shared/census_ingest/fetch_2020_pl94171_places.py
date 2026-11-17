# -*- coding: utf-8 -*-
"""Downloads open 2020 US Census PL 94-171 state zip archives in parallel,
extracts only the geographic header table (`<st>geo2020.pl`), and caches a compact
CSV of 100% of SUMLEV 160 (Incorporated Places + CDPs), SUMLEV 060 (Minor Civil
Divisions), and SUMLEV 050 (Counties) with exact 2020 POP100, HU100, LAT, LON.
Also fetches 2010_Gaz_cousubs_national.zip and cousub2k.zip.
"""

import concurrent.futures
import csv
import io
import os
import pathlib
import re
import urllib.request
import zipfile

RAW_DIR = pathlib.Path(__file__).resolve().parent / "raw_sources"
RAW_DIR.mkdir(parents=True, exist_ok=True)
BASE_URL = "https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/"
OUT_CSV = RAW_DIR / "us_2020_pl94171_places_mcds.csv"

SKIP_FOLDERS = {"National/", "Puerto_Rico/", "../", "./"}


def fetch_state_rows(folder_href):
  st_url = BASE_URL + folder_href
  html = urllib.request.urlopen(st_url, timeout=30).read().decode("utf-8", "ignore")
  zips = re.findall(r'href="([a-z]{2}2020\.pl\.zip)"', html)
  if not zips:
    return folder_href, []
  zip_url = st_url + zips[0]
  req = urllib.request.Request(zip_url, headers={"User-Agent": "Mozilla/5.0"})
  data = urllib.request.urlopen(req, timeout=240).read()
  zf = zipfile.ZipFile(io.BytesIO(data))
  geo_names = [n for n in zf.namelist() if "geo2020" in n.lower()]
  if not geo_names:
    return folder_href, []
  rows = []
  with zf.open(geo_names[0]) as fh:
    for raw_line in fh:
      parts = raw_line.decode("latin-1", "replace").rstrip("\r\n").split("|")
      if len(parts) < 95:
        continue
      sumlev = parts[2].strip()
      if sumlev not in ("160", "060", "050"):
        continue
      rows.append([
        parts[1].strip(),   # STUSAB
        sumlev,             # SUMLEV
        parts[8].strip(),   # GEOCODE
        parts[9].strip(),   # GEOID
        parts[12].strip(),  # STATEFP
        parts[14].strip(),  # COUNTYFP
        parts[17].strip(),  # COUSUBFP
        parts[29].strip(),  # PLACEFP
        parts[94].strip(),  # LSADC
        parts[88].strip(),  # FUNCSTAT
        parts[84].strip(),  # AREALAND
        parts[85].strip(),  # AREAWATR
        parts[86].strip(),  # BASENAME
        parts[87].strip(),  # NAME
        parts[90].strip(),  # POP100
        parts[91].strip(),  # HU100
        parts[92].strip(),  # INTPTLAT
        parts[93].strip(),  # INTPTLON
      ])
  return folder_href, rows


def main():
  for fn, u in [
    ("2010_Gaz_cousubs_national.zip", "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/Gaz_cousubs_national.zip"),
    ("cousub2k.zip", "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/cousub2k.zip"),
  ]:
    dst = RAW_DIR / fn
    if not dst.exists():
      try:
        urllib.request.urlretrieve(u, dst)
        print("Downloaded", fn, dst.stat().st_size, flush=True)
      except Exception as exc:
        print("Skipped", fn, exc, flush=True)

  if OUT_CSV.exists() and OUT_CSV.stat().st_size > 1_000_000:
    print("Already cached:", OUT_CSV, OUT_CSV.stat().st_size)
    return

  html = urllib.request.urlopen(BASE_URL, timeout=20).read().decode("utf-8", "ignore")
  folders = [
    m for m in re.findall(r'href="([^"]+/)"', html)
    if not m.startswith("/") and not m.startswith("http") and m not in SKIP_FOLDERS
  ]
  print(f"Found {len(folders)} state/DC folders in 2020 PL 94-171.", flush=True)

  all_rows = []
  with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    for folder, rows in pool.map(fetch_state_rows, folders):
      all_rows.extend(rows)
      print(f"  {folder:<24} -> {len(rows):5d} rows (total={len(all_rows):6d})", flush=True)

  with open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow([
      "STUSAB", "SUMLEV", "GEOCODE", "GEOID", "STATEFP", "COUNTYFP",
      "COUSUBFP", "PLACEFP", "LSADC", "FUNCSTAT", "AREALAND", "AREAWATR",
      "BASENAME", "NAME", "POP100", "HU100", "INTPTLAT", "INTPTLON"
    ])
    w.writerows(all_rows)
  print("Wrote", OUT_CSV, "rows:", len(all_rows))


if __name__ == "__main__":
  main()
