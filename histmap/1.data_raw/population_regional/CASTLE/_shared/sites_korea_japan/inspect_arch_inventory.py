"""Inspects downloaded Japan & Korea archaeological archives (JASOSR, R14CDB, MLIT P32, KHS, NRICH, Korean C14) and tests NRICH pagination."""

import json
import os
import zipfile
import requests
import xml.etree.ElementTree as ET

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_ARCH = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE", "_shared", "sites_korea_japan", "0.raw_data")
RAW_CEN = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE", "_shared", "_census_cache")
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OperationViscount/2.0"}


def main():
  # 1. Inspect JASOSR top-level folders and file sizes
  with zipfile.ZipFile(os.path.join(RAW_ARCH, "gh_kotdijian_JASOSR.zip")) as zf:
    by_dir = {}
    for info in zf.infolist():
      if info.is_dir():
        continue
      parts = info.filename.split("/")
      top = parts[1] if len(parts) > 1 else parts[0]
      by_dir.setdefault(top, []).append((info.filename, info.file_size))
    print(f"=== JASOSR ({len(by_dir)} folders) ===")
    for k in sorted(by_dir.keys()):
      tot_sz = sum(x[1] for x in by_dir[k])
      exts = sorted(set(os.path.splitext(x[0])[1].lower() for x in by_dir[k]))
      print(f"  {k}: {len(by_dir[k])} files, {tot_sz/1e6:.2f} MB, exts={exts}")

  # 2. Inspect R14CDB.csv, japan_c14db, yayoi_demo, NeolithicKoreaDemography, Hanseong_C14
  for zfn in [
    "gh_ercrema_japan_c14db.zip",
    "gh_ercrema_yayoi_demo.zip",
    "gh_ercrema_yayoi_rice_dispersal.zip",
    "gh_ercrema_NeolithicKoreaDemography.zip",
    "gh_ChanToRe_Hanseong_C14.zip",
    "gh_kotdijian_JPRA_DB.zip",
  ]:
    with zipfile.ZipFile(os.path.join(RAW_ARCH, zfn)) as zf:
      csvs = [i for i in zf.infolist() if any(i.filename.lower().endswith(e) for e in (".csv", ".geojson", ".xlsx", ".tsv")) and i.file_size > 1000]
      print(f"\n=== {zfn}: {len(csvs)} tables ===")
      for i in csvs[:12]:
        print(f"  {i.filename} ({i.file_size:,} B)")

  # 3. Inspect KHS categories and coordinate completeness
  khs = json.load(open(os.path.join(RAW_ARCH, "khs_korea_heritage_all.json"), encoding="utf-8"))
  valid_coords = sum(1 for x in khs if x.get("longitude") and x.get("latitude") and float(x.get("longitude") or 0) > 120 and float(x.get("latitude") or 0) > 30)
  by_cat = {}
  for x in khs:
    c = x.get("ccmaName", "?")
    by_cat[c] = by_cat.get(c, 0) + 1
  print(f"\n=== KHS: {len(khs)} total, {valid_coords} with valid coords ===")
  print("  top categories:", sorted(by_cat.items(), key=lambda kv: -kv[1])[:12])

  # 4. Test NRICH pagination (recordcountperpage=100 vs pageIndex)
  for idx in (206, 39):
    r1 = requests.get(f"https://portal.nrich.go.kr/kor/openapi.do?idx={idx}&firstindex=1&recordcountperpage=100", headers=HDR, timeout=30)
    r2 = requests.get(f"https://portal.nrich.go.kr/kor/openapi.do?idx={idx}&firstindex=101&recordcountperpage=100", headers=HDR, timeout=30)
    b1 = ET.fromstring(r1.content).findall("data")
    b2 = ET.fromstring(r2.content).findall("data")
    n1 = b1[0].find("md_data3").text if b1 else None
    n2 = b2[0].find("md_data3").text if b2 else None
    print(f"NRICH idx={idx}: page1={len(b1)} ({n1}), page2={len(b2)} ({n2})")

  # 5. Inspect southkorea-population.zip files
  with zipfile.ZipFile(os.path.join(RAW_CEN, "gh_southkorea_population.zip")) as zf:
    print("\n=== southkorea-population.zip ===")
    for i in zf.infolist():
      if not i.is_dir():
        print(f"  {i.filename} ({i.file_size:,} B)")


if __name__ == "__main__":
  main()

