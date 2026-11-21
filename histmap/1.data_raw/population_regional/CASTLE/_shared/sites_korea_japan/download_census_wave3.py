"""Downloads full-enumeration Japan, South Korea, and North Korea municipal census files & inspects DPRK 2008 Table 4."""

import os
import re
import time
import requests
import pymupdf

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_CEN = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE", "_shared", "_census_cache")
os.makedirs(RAW_CEN, exist_ok=True)
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OperationViscount/2.0"}


def dl(arg0_name, arg1_url, arg2_out):
  if os.path.exists(arg2_out) and os.path.getsize(arg2_out) > 1000:
    print(f"[SKIP] {arg0_name} ({os.path.getsize(arg2_out):,} bytes)")
    return True
  try:
    r = requests.get(arg1_url, headers=HDR, timeout=90, allow_redirects=True)
    if r.status_code != 200:
      print(f"[FAIL] {arg0_name}: HTTP {r.status_code}")
      return False
    with open(arg2_out, "wb") as fh:
      fh.write(r.content)
    print(f"[OK] {arg0_name} -> {os.path.basename(arg2_out)} ({len(r.content):,} bytes)")
    return True
  except Exception as e:
    print(f"[ERR] {arg0_name}: {e}")
    return False


def main():
  targets = [
    ("SSDSE_A_2026", "https://www.nstac.go.jp/files/SSDSE-A-2026.csv", os.path.join(RAW_CEN, "japan_SSDSE_A_2026.csv")),
    ("SSDSE_B_2026", "https://www.nstac.go.jp/files/SSDSE-B-2026.csv", os.path.join(RAW_CEN, "japan_SSDSE_B_2026.csv")),
    ("GH_CZ_JP", "https://github.com/daisukeadachi/commuting_zone_japan/archive/refs/heads/main.zip", os.path.join(RAW_CEN, "gh_commuting_zone_japan.zip")),
    ("GH_LOCALGOV_JP", "https://github.com/code4fukui/localgovjp/archive/refs/heads/master.zip", os.path.join(RAW_CEN, "gh_localgovjp.zip")),
    ("CP_JP_ADMIN", "https://www.citypopulation.de/en/japan/admin/", os.path.join(RAW_CEN, "citypop_japan_admin.html")),
    ("CP_JP_CITIES", "https://www.citypopulation.de/en/japan/cities/", os.path.join(RAW_CEN, "citypop_japan_cities.html")),
    ("CP_KR_ADMIN", "https://www.citypopulation.de/en/southkorea/admin/", os.path.join(RAW_CEN, "citypop_southkorea_admin.html")),
    ("CP_KR_CITIES", "https://www.citypopulation.de/en/southkorea/cities/", os.path.join(RAW_CEN, "citypop_southkorea_cities.html")),
    ("CP_KP_ADMIN", "https://www.citypopulation.de/en/northkorea/admin/", os.path.join(RAW_CEN, "citypop_northkorea_admin.html")),
    ("CP_KP_CITIES", "https://www.citypopulation.de/en/northkorea/cities/", os.path.join(RAW_CEN, "citypop_northkorea_cities.html")),
  ]
  for nm, url, out_p in targets:
    dl(nm, url, out_p)
    time.sleep(0.25)

  # Also harvest South Korea sub-municipal (eup/myeon/dong) links from citypop_southkorea_admin.html
  kr_html_p = os.path.join(RAW_CEN, "citypop_southkorea_admin.html")
  if os.path.exists(kr_html_p):
    txt = open(kr_html_p, encoding="utf-8", errors="replace").read()
    sub_links = sorted(set(re.findall(r'href="(/en/southkorea/[^"]*admin/[^"]+/)"', txt)))
    print(f"Found {len(sub_links)} South Korea provincial/municipal sub-pages on citypopulation.de: {sub_links[:10]}")

  # Inspect DPRK 2008 PDF for Table 4 pages
  pdf_p = os.path.join(RAW_CEN, "dprk_2008_census_national_report.pdf")
  if os.path.exists(pdf_p):
    doc = pymupdf.open(pdf_p)
    print(f"\nDPRK 2008 PDF: {len(doc)} pages")
    for pno in range(min(45, len(doc))):
      t = doc[pno].get_text()
      if "Table 4" in t or "Ryanggang" in t or "Pyongyang" in t and "Urban" in t and "Rural" in t:
        first_line = t.strip().splitlines()[0] if t.strip() else ""
        print(f"  Page {pno+1}: {first_line[:95]}")


if __name__ == "__main__":
  main()

