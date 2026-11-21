"""Inspects Natural Earth Admin-1 names for Japan/Korea and parses official provincial/prefectural census tables from downloaded cache."""

import json
import os
import re
import pymupdf

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
NE1_PATH = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "_gis_cache", "ne_10m_admin_1_states_provinces.geojson")
RAW_CEN = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE", "_shared", "_census_cache")


def main():
  ne1 = json.load(open(NE1_PATH, encoding="utf-8"))
  for adm in ("Japan", "South Korea", "North Korea"):
    names = sorted([f["properties"].get("name") for f in ne1["features"] if f["properties"].get("admin") == adm])
    print(f"\n=== NE1 {adm} ({len(names)}) ===")
    print(names)

  # Quick inspection of citypop HTML table structure for JP, KR, KP
  for tag, fn in [("JP", "citypop_japan_admin.html"), ("KR", "citypop_southkorea_admin.html"), ("KP", "citypop_northkorea_admin.html")]:
    txt = open(os.path.join(RAW_CEN, fn), encoding="utf-8", errors="replace").read()
    # Find table headers
    theads = re.findall(r"<thead.*?</thead>", txt, flags=re.S | re.I)
    print(f"\n=== {tag} citypop tables: {len(theads)} ===")
    if theads:
      cols = [re.sub(r"<[^>]+>", " ", c).strip() for c in re.findall(r"<th[^>]*>(.*?)</th>", theads[0], flags=re.S | re.I)]
      print("  thead[0] cols:", cols)
    rows = re.findall(r"<tr[^>]*data-id=[^>]*>.*?</tr>", txt, flags=re.S | re.I)
    if not rows:
      rows = re.findall(r"<tr[^>]*class=\"rname\"[^>]*>.*?</tr>", txt, flags=re.S | re.I)
    if not rows:
      rows = re.findall(r"<tbody.*?</tbody>", txt, flags=re.S | re.I)
      if rows:
        tr_list = re.findall(r"<tr[^>]*>.*?</tr>", rows[0], flags=re.S | re.I)
        print(f"  tbody[0] rows: {len(tr_list)}")
        for r in tr_list[:4]:
          tds = [re.sub(r"<[^>]+>", " ", c).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, flags=re.S | re.I)]
          print("   ", tds)
    else:
      print(f"  matched rows: {len(rows)}")
      for r in rows[:4]:
        tds = [re.sub(r"<[^>]+>", " ", c).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, flags=re.S | re.I)]
        print("   ", tds)

  # Inspect DPRK 2008 PDF pages 15..25 for Table 4
  pdf_p = os.path.join(RAW_CEN, "dprk_2008_census_national_report.pdf")
  doc = pymupdf.open(pdf_p)
  for pno in range(len(doc)):
    t = doc[pno].get_text()
    if "Table 4" in t or "Population by Province" in t or "Ryanggang" in t and "Pyongyang" in t and "Total" in t:
      lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
      print(f"\n--- DPRK PDF p.{pno+1} ---")
      print("\n".join(lines[:18]))
      if pno > 35:
        break


if __name__ == "__main__":
  main()

