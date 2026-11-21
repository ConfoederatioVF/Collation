"""Tests parsing DPRK 2008 PDF Table 2 (pages 24-28), Japan SSDSE-A-2026 + localgovjp + citypop, and South Korea submunicipalities + citypop."""

import csv
import io
import json
import os
import re
import zipfile
import pymupdf

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CEN_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE", "_shared", "_census_cache")


def main():
  # 1. Inspect DPRK 2008 PDF Table 2 pages 24..28 raw lines
  doc = pymupdf.open(os.path.join(CEN_DIR, "dprk_2008_census_national_report.pdf"))
  for pno in range(23, 28):
    t = doc[pno].get_text()
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    print(f"=== DPRK p.{pno+1} ({len(lines)} lines) ===")
    print(" ", lines[15:45])
    break

  # 2. Inspect localgovjp CSV columns
  with zipfile.ZipFile(os.path.join(CEN_DIR, "gh_localgovjp.zip")) as zf:
    cands = sorted([n for n in zf.namelist() if "localgovjp-utf8.csv" in n])
    print("\n=== localgovjp latest ===", cands[-1])
    raw = zf.read(cands[-1]).decode("utf-8-sig", errors="replace").splitlines()
    print("  lines:", len(raw))
    for ln in raw[:4]:
      print(" ", ln[:160])

  # 3. Inspect piuccio municipalities.json
  with zipfile.ZipFile(os.path.join(CEN_DIR, "gh_piuccio_jp_municipalities.zip")) as zf:
    mj = json.loads(zf.read("open-data-jp-municipalities-master/municipalities.json").decode("utf-8"))
    print(f"\n=== piuccio municipalities.json: {len(mj)} entries ===")
    if isinstance(mj, list):
      print("  sample:", mj[0])
    elif isinstance(mj, dict):
      k0 = next(iter(mj))
      print("  sample:", k0, mj[k0])

  # 4. Inspect southkorea-population codebook-translation & submunicipalities total rows
  with zipfile.ZipFile(os.path.join(CEN_DIR, "gh_southkorea_population.zip")) as zf:
    tr = json.loads(zf.read("southkorea-population-master/codebook/codebook-20100401-06-translation.json").decode("utf-8"))
    print(f"\n=== SK translation.json: {type(tr)} len={len(tr)} ===")
    if isinstance(tr, dict):
      for k in list(tr.keys())[:5]:
        print(" ", k, tr[k])
    elif isinstance(tr, list):
      print("  sample:", tr[:3])
    # Count unique submunicipalities where age=='계'
    raw = zf.read("southkorea-population-master/data/2010/submunicipalities_utf8.csv").decode("utf-8-sig", errors="replace")
    tot_rows = 0
    eup_cnt, myeon_cnt, dong_cnt = 0, 0, 0
    for row in csv.reader(io.StringIO(raw)):
      if len(row) >= 6 and row[3].strip() == "계":
        nm = row[1].strip()
        tot_rows += 1
        if nm.endswith("읍"):
          eup_cnt += 1
        elif nm.endswith("면"):
          myeon_cnt += 1
        elif nm.endswith("동") or nm.endswith("가"):
          dong_cnt += 1
    print(f"  SK 2010 submunicipalities total rows (age=계): {tot_rows:,} (eup={eup_cnt}, myeon={myeon_cnt}, dong={dong_cnt})")


if __name__ == "__main__":
  main()

