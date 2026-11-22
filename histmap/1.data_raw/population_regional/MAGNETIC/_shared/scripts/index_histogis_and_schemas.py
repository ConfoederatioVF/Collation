"""Indexes the 104 MB HistoGIS dump JSONL by source_name, checks NL/UK/CShapes/Basemaps schemas."""
import json
import os
from collections import Counter

import openpyxl

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MAGNETIC\_shared\subadmin_hgis\raw_sources"


def main():
  dump_p = os.path.join(RAW_DIR, "histogis", "histogis-dump.jsonl")
  src_cnt = Counter()
  sample_by_src = {}
  with open(dump_p, encoding="utf-8") as fh:
    for line in fh:
      line = line.strip()
      if not line:
        continue
      obj = json.loads(line)
      props = obj.get("properties") or {}
      sn = props.get("source_name") or props.get("source") or "UNKNOWN"
      if isinstance(sn, dict):
        sn = sn.get("name", "UNKNOWN")
      src_cnt[sn] += 1
      if sn not in sample_by_src:
        sample_by_src[sn] = (props.get("name"), props.get("start_date"), props.get("end_date"), props.get("adm_name"))
  print(f"=== HistoGIS Dump: {sum(src_cnt.values())} features across {len(src_cnt)} sources ===")
  for sn, cnt in sorted(src_cnt.items()):
    if any(k in sn.lower() for k in ("crownland", "holy roman", "prussia", "german", "europe", "cisleith", "entities", "bavaria counties")):
      print(f"  {sn:48s}: {cnt:4d} | sample={sample_by_src[sn]}")

  # UK ceremonial counties names
  uk_p = os.path.join(RAW_DIR, "uk_hist", "uk_ceremonial_counties.geojson")
  uk_gj = json.load(open(uk_p, encoding="utf-8"))
  uk_names = [f["properties"] for f in uk_gj["features"]]
  print(f"\n=== UK Ceremonial/Historic Counties: {len(uk_names)} features ===")
  print("  props keys:", list(uk_names[0].keys()) if uk_names else None)
  print("  sample names:", [x.get("name") or x.get("NAME") or list(x.values())[0] for x in uk_names[:20]])

  # NL xlsx sheet names & top rows
  nl_p = os.path.join(RAW_DIR, "nl_hist", "nl_juridisch_bevolking_1859_1920.xlsx")
  wb = openpyxl.load_workbook(nl_p, read_only=True)
  ws = wb[wb.sheetnames[0]]
  rows = [r for _, r in zip(range(5), ws.iter_rows(values_only=True))]
  print(f"\n=== NL 1859-1920 sheets={wb.sheetnames} ===")
  for r in rows:
    print(" ", r[:12])

  # CShapes Europe sample properties
  cs_p = os.path.join(RAW_DIR, "cshapes", "CShapes-Europe.geojson")
  cs_gj = json.load(open(cs_p, encoding="utf-8"))
  print(f"\n=== CShapes-Europe: {len(cs_gj['features'])} features ===")
  print("  props keys:", list(cs_gj["features"][0]["properties"].keys()))
  yrs = sorted({str(f["properties"].get("start", ""))[:4] for f in cs_gj["features"]})
  print("  start years range:", yrs[:5], "...", yrs[-5:])


if __name__ == "__main__":
  main()
