"""Probes NRICH North Korea heritage API, Japan/Korea census CSVs (SSDSE, GitHub, citypopulation.de), and inspects downloaded files."""

import os
import re
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CASTLE_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE")
RAW_ARCH = os.path.join(CASTLE_DIR, "_shared", "sites_korea_japan", "0.raw_data")
RAW_CEN = os.path.join(CASTLE_DIR, "_shared", "_census_cache")
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OperationViscount/2.0"}


def main():
  print("=== Current 0.raw_data files ===")
  for fn in sorted(os.listdir(RAW_ARCH)):
    print(f"  {fn}: {os.path.getsize(os.path.join(RAW_ARCH, fn)):,} bytes")
  print("=== Current _census_cache files ===")
  for fn in sorted(os.listdir(RAW_CEN)):
    print(f"  {fn}: {os.path.getsize(os.path.join(RAW_CEN, fn)):,} bytes")

  urls = [
    ("NRICH_NK", "https://portal.nrich.go.kr/kor/originalTotalApi.do?bunya_cd=412&firstindex=1&recordcountperpage=5"),
    ("GH_CZ_JP", "https://api.github.com/repos/daisukeadachi/commuting_zone_japan/contents"),
    ("GH_LOCALGOV", "https://api.github.com/repos/code4fukui/localgovjp/contents"),
    ("GH_SUANLAB", "https://api.github.com/repos/suanlab/dataset/contents"),
    ("SSDSE_PAGE", "https://www.nstac.go.jp/use/literacy/ssdse/"),
    ("CP_JP", "https://www.citypopulation.de/en/japan/admin/"),
    ("CP_KR", "https://www.citypopulation.de/en/southkorea/admin/"),
    ("CP_KP", "https://www.citypopulation.de/en/northkorea/admin/"),
  ]
  for name, url in urls:
    try:
      r = requests.get(url, headers=HDR, timeout=25)
      prev = r.text[:220].replace("\n", " ").replace("\r", " ")
      print(f"[{name}] HTTP {r.status_code} len={len(r.content)} prev={prev!r}")
      if name == "SSDSE_PAGE" and r.status_code == 200:
        csvs = re.findall(r'href="([^"]*(?:SSDSE-A|SSDSE-B|SSDSE-C)[^"]*\.(?:csv|xlsx))"', r.text, flags=re.I)
        print("  SSDSE links:", csvs[:10])
    except Exception as e:
      print(f"[{name}] ERR: {e}")


if __name__ == "__main__":
  main()

