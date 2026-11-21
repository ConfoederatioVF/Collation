"""Wave 2 bulk archaeological & census harvester for Project CASTLE (Japan, South Korea, North Korea)."""

import json
import os
import time
import xml.etree.ElementTree as ET
import zipfile
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CASTLE_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE")
RAW_ARCH = os.path.join(CASTLE_DIR, "_shared", "sites_korea_japan", "0.raw_data")
RAW_CEN = os.path.join(CASTLE_DIR, "_shared", "_census_cache")
os.makedirs(RAW_ARCH, exist_ok=True)
os.makedirs(RAW_CEN, exist_ok=True)

HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OperationViscount/2.0"}


def download_file(arg0_name, arg1_url, arg2_out_path):
  if os.path.exists(arg2_out_path) and os.path.getsize(arg2_out_path) > 1024:
    print(f"[SKIP] {arg0_name} ({os.path.getsize(arg2_out_path):,} bytes)")
    return True
  try:
    r = requests.get(arg1_url, headers=HDR, timeout=180, stream=True, allow_redirects=True)
    if r.status_code != 200:
      print(f"[FAIL] {arg0_name}: HTTP {r.status_code}")
      return False
    total = 0
    with open(arg2_out_path, "wb") as fh:
      for chunk in r.iter_content(chunk_size=65536):
        if chunk:
          fh.write(chunk)
          total += len(chunk)
    print(f"[OK] {arg0_name} -> {os.path.basename(arg2_out_path)} ({total:,} bytes)")
    return True
  except Exception as e:
    print(f"[ERR] {arg0_name}: {e}")
    return False


def harvest_khs_all():
  out_p = os.path.join(RAW_ARCH, "khs_korea_heritage_all.json")
  if os.path.exists(out_p) and os.path.getsize(out_p) > 500000:
    data = json.load(open(out_p, encoding="utf-8"))
    print(f"[SKIP] KHS already harvested: {len(data)} items")
    return
  items = []
  page_unit = 1000
  page_idx = 1
  total_cnt = None
  while True:
    url = f"https://www.khs.go.kr/cha/SearchKindOpenapiList.do?pageUnit={page_unit}&pageIndex={page_idx}"
    r = requests.get(url, headers=HDR, timeout=60)
    if r.status_code != 200:
      print(f"[KHS] page {page_idx} HTTP {r.status_code}, retrying...")
      time.sleep(2)
      r = requests.get(url, headers=HDR, timeout=60)
    root = ET.fromstring(r.content)
    if total_cnt is None:
      tc_el = root.find("totalCnt")
      total_cnt = int(tc_el.text.strip()) if tc_el is not None and tc_el.text else 0
      print(f"[KHS] totalCnt = {total_cnt}")
    batch = root.findall("item")
    if not batch:
      break
    for it in batch:
      rec = {}
      for ch in it:
        rec[ch.tag] = (ch.text or "").strip()
      items.append(rec)
    print(f"[KHS] page {page_idx}: +{len(batch)} (cum {len(items)}/{total_cnt})")
    if len(items) >= total_cnt or len(batch) < page_unit:
      break
    page_idx += 1
    time.sleep(0.15)
  with open(out_p, "w", encoding="utf-8") as fh:
    json.dump(items, fh, ensure_ascii=False)
  print(f"[OK] Saved KHS all: {len(items)} items -> {out_p}")


def harvest_nrich(arg0_idx, arg1_out_name, arg2_page_size=500):
  out_p = os.path.join(RAW_ARCH, arg1_out_name)
  if os.path.exists(out_p) and os.path.getsize(out_p) > 50000:
    data = json.load(open(out_p, encoding="utf-8"))
    print(f"[SKIP] NRICH idx={arg0_idx} already harvested: {len(data)} items")
    return
  items = []
  first = 1
  while True:
    url = f"https://portal.nrich.go.kr/kor/openapi.do?idx={arg0_idx}&firstindex={first}&recordcountperpage={arg2_page_size}"
    try:
      r = requests.get(url, headers=HDR, timeout=60)
      if r.status_code != 200:
        print(f"[NRICH {arg0_idx}] first={first} HTTP {r.status_code}")
        break
      root = ET.fromstring(r.content)
      batch = root.findall("data")
      if not batch:
        break
      for d in batch:
        rec = {ch.tag: (ch.text or "").strip() for ch in d}
        # Strip bulky HTML essay text if needed? Keep truncated description for period/location extraction
        if "md_data11" in rec and len(rec["md_data11"]) > 600:
          rec["md_data11"] = rec["md_data11"][:600]
        items.append(rec)
      if len(items) % 2000 < arg2_page_size or len(batch) < arg2_page_size:
        print(f"[NRICH {arg0_idx}] first={first}: +{len(batch)} (cum {len(items)})")
      if len(batch) < arg2_page_size:
        break
      first += arg2_page_size
      if first > 80000:
        break
      time.sleep(0.1)
    except Exception as e:
      print(f"[NRICH {arg0_idx}] ERR at first={first}: {e}")
      break
  with open(out_p, "w", encoding="utf-8") as fh:
    json.dump(items, fh, ensure_ascii=False)
  print(f"[OK] Saved NRICH idx={arg0_idx}: {len(items)} items -> {out_p}")


def inspect_zips():
  print("\n=== ZIP INVENTORY ===")
  for folder in (RAW_ARCH, RAW_CEN):
    for fn in sorted(os.listdir(folder)):
      if not fn.endswith(".zip"):
        continue
      p = os.path.join(folder, fn)
      try:
        with zipfile.ZipFile(p) as zf:
          names = zf.namelist()
          data_files = [n for n in names if any(n.lower().endswith(ext) for ext in (".csv", ".tsv", ".geojson", ".json", ".shp", ".xlsx", ".xls", ".rda", ".rds", ".txt"))]
          print(f"  {fn}: {len(names)} total, {len(data_files)} data files. Sample: {data_files[:6]}")
      except Exception as e:
        print(f"  {fn}: ERR {e}")


def main():
  extra_downloads = [
    ("JPRA_DB", "https://github.com/kotdijian/JPRA-DB/archive/refs/heads/master.zip", os.path.join(RAW_ARCH, "gh_kotdijian_JPRA_DB.zip")),
    ("NEOLITHIC_KOREA", "https://github.com/ercrema/NeolithicKoreaDemography/archive/refs/heads/master.zip", os.path.join(RAW_ARCH, "gh_ercrema_NeolithicKoreaDemography.zip")),
    ("JOMON_PHASES", "https://github.com/ercrema/jomonPhasesAndPopulation/archive/refs/heads/master.zip", os.path.join(RAW_ARCH, "gh_ercrema_jomonPhasesAndPopulation.zip")),
    ("JOMON_SPD", "https://github.com/ercrema/Jomon_SPD_Comparison/archive/refs/heads/master.zip", os.path.join(RAW_ARCH, "gh_ercrema_Jomon_SPD_Comparison.zip")),
    ("K_AH_DEMO", "https://github.com/ercrema/K-Ah_Demo/archive/refs/heads/main.zip", os.path.join(RAW_ARCH, "gh_ercrema_K_Ah_Demo.zip")),
    ("YAYOI_RICE", "https://github.com/ercrema/yayoi_rice_dispersal/archive/refs/heads/master.zip", os.path.join(RAW_ARCH, "gh_ercrema_yayoi_rice_dispersal.zip")),
    ("MLIT_P32", "https://nlftp.mlit.go.jp/ksj/gml/data/P32/P32-14/P32-14_00_GML.zip", os.path.join(RAW_ARCH, "mlit_P32_14_00_GML.zip")),
  ]
  for nm, url, out_p in extra_downloads:
    download_file(nm, url, out_p)

  harvest_khs_all()
  harvest_nrich(206, "nrich_archaeology_journal.json", 500)
  harvest_nrich(39, "nrich_archaeology_dict.json", 500)
  inspect_zips()


if __name__ == "__main__":
  main()

