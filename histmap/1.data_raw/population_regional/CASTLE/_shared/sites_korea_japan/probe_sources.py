"""Probes live Japanese, South Korean, and North Korean archaeological & census portals for Project CASTLE."""

import os
import json
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CASTLE_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE")
RAW_ARCH = os.path.join(CASTLE_DIR, "_shared", "sites_korea_japan", "0.raw_data")
RAW_CEN = os.path.join(CASTLE_DIR, "_shared", "_census_cache")
os.makedirs(RAW_ARCH, exist_ok=True)
os.makedirs(RAW_CEN, exist_ok=True)

HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OperationViscount/2.0"}


def probe(arg0_name, arg1_url, arg2_save_path=None):
  try:
    r = requests.get(arg1_url, headers=HDR, timeout=30, allow_redirects=True)
    ct = r.headers.get("content-type", "")[:45]
    prev = r.text[:220].replace("\n", " ").replace("\r", " ")
    print(f"[{arg0_name}] HTTP {r.status_code} len={len(r.content)} ct={ct!r} prev={prev!r}")
    if arg2_save_path and r.status_code == 200 and len(r.content) > 1000:
      with open(arg2_save_path, "wb") as fh:
        fh.write(r.content)
      print(f"  -> SAVED {arg2_save_path} ({len(r.content):,} bytes)")
    return r
  except Exception as e:
    print(f"[{arg0_name}] ERR: {e}")
    return None


def main():
  probes = [
    ("GH_JASOSR", "https://api.github.com/repos/kotdijian/JASOSR/contents", None),
    ("GH_PALAEOLITHIC", "https://api.github.com/repos/kotdijian/Japanese_Palaeolithic_Sites_DB_English/contents", None),
    ("GH_JAPAN_C14", "https://api.github.com/repos/ercrema/japan_c14db/contents", None),
    ("GH_YAYOI_DEMO", "https://api.github.com/repos/ercrema/yayoi_demo/contents", None),
    ("GH_HANSEONG_C14", "https://api.github.com/repos/ChanToRe/Hanseong_C14/contents", None),
    ("GH_TIDYCENSUSKR", "https://api.github.com/repos/sigmafelix/tidycensuskr/contents", None),
    ("GH_SK_POP", "https://api.github.com/repos/southkorea/southkorea-population/contents", None),
    ("GH_ESTAT_FUKUI", "https://api.github.com/repos/code4fukui/e-stat/contents", None),
    ("GH_JP_MUNI", "https://api.github.com/repos/piuccio/open-data-jp-municipalities/contents", None),
    ("ZENODO_8377215", "https://zenodo.org/api/records/8377215", None),
    ("ZENODO_4308578", "https://zenodo.org/api/records/4308578", None),
    ("KHS_LIST", "https://www.khs.go.kr/cha/SearchKindOpenapiList.do?pageUnit=5&pageIndex=1", None),
    ("NRICH_DICT", "https://portal.nrich.go.kr/kor/openapi.do?idx=39&firstindex=1&recordcountperpage=5", None),
    ("NRICH_JOUR", "https://portal.nrich.go.kr/kor/openapi.do?idx=206&firstindex=1&recordcountperpage=5", None),
    ("XRONOS_JP", "https://xronos.ch/api/v1/data?country=Japan&format=json", None),
    ("XRONOS_KR", "https://xronos.ch/api/v1/data?country=South%20Korea&format=json", None),
    ("XRONOS_KP", "https://xronos.ch/api/v1/data?country=North%20Korea&format=json", None),
    ("UNFPA_DPRK2008", "https://unstats.un.org/unsd/demographic/sources/census/wphc/North_Korea/Final%20national%20census%20report.pdf",
     os.path.join(RAW_CEN, "dprk_2008_census_national_report.pdf")),
    ("GEONAMES_JP", "https://download.geonames.org/export/dump/JP.zip", os.path.join(RAW_CEN, "geonames_JP.zip")),
    ("GEONAMES_KR", "https://download.geonames.org/export/dump/KR.zip", os.path.join(RAW_CEN, "geonames_KR.zip")),
    ("GEONAMES_KP", "https://download.geonames.org/export/dump/KP.zip", os.path.join(RAW_CEN, "geonames_KP.zip")),
  ]
  for name, url, save_p in probes:
    probe(name, url, save_p)


if __name__ == "__main__":
  main()

