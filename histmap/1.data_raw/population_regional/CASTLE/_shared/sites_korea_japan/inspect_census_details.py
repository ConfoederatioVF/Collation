"""Inspects Japan SSDSE-A-2026 CSV, South Korea submunicipalities_utf8.csv, DPRK 2008 PDF Table 2 (pages 24-28), and GeoNames JP/KR/KP counts."""

import csv
import io
import os
import zipfile
import pymupdf

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CEN_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE", "_shared", "_census_cache")


def main():
  # 1. SSDSE-A-2026.csv
  ssdse_p = os.path.join(CEN_DIR, "japan_SSDSE_A_2026.csv")
  raw = open(ssdse_p, "rb").read()
  for enc in ("cp932", "utf-8-sig", "utf-8"):
    try:
      txt = raw.decode(enc)
      break
    except Exception:
      continue
  lines = txt.splitlines()
  print(f"=== SSDSE-A-2026.csv: {len(lines)} lines (enc={enc}) ===")
  for ln in lines[:5]:
    print(" ", ln[:160])

  # 2. southkorea-population submunicipalities_utf8.csv & municipalities_utf8.csv
  with zipfile.ZipFile(os.path.join(CEN_DIR, "gh_southkorea_population.zip")) as zf:
    for fn in ("southkorea-population-master/data/2010/municipalities_utf8.csv", "southkorea-population-master/data/2010/submunicipalities_utf8.csv"):
      data = zf.read(fn).decode("utf-8-sig", errors="replace").splitlines()
      print(f"\n=== {os.path.basename(fn)}: {len(data)} lines ===")
      for ln in data[:4]:
        print(" ", ln[:160])

  # 3. DPRK 2008 PDF Table 2 (pages 24-29, 0-indexed 23..28)
  doc = pymupdf.open(os.path.join(CEN_DIR, "dprk_2008_census_national_report.pdf"))
  print("\n=== DPRK 2008 PDF Table 2 sample (page 24) ===")
  for pno in range(23, 29):
    t = doc[pno].get_text()
    if "Table 2" in t:
      ls = [x.strip() for x in t.splitlines() if x.strip()]
      print(f"  Page {pno+1}: {len(ls)} lines. First 18:")
      for x in ls[:18]:
        print("   ", x)
      break

  # 4. GeoNames JP, KR, KP populated place counts
  for cc in ("JP", "KR", "KP"):
    with zipfile.ZipFile(os.path.join(CEN_DIR, f"geonames_{cc}.zip")) as zf:
      txt = zf.read(f"{cc}.txt").decode("utf-8", errors="replace")
      ppl, adm = 0, 0
      pop_gt0 = 0
      for ln in txt.splitlines():
        cols = ln.split("\t")
        if len(cols) < 15:
          continue
        fcl = cols[6]
        if fcl == "P":
          ppl += 1
          if int(cols[14] or 0) > 0:
            pop_gt0 += 1
        elif fcl == "A":
          adm += 1
      print(f"[GeoNames {cc}] P(populated)={ppl:,} (pop>0: {pop_gt0:,}), A(admin)={adm:,}")


if __name__ == "__main__":
  main()

