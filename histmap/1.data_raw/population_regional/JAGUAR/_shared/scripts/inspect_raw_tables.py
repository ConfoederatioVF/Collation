"""Inspect exact table headers and sample rows across all downloaded raw sources."""

import json
import os
import openpyxl

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\subadmin_hgis\raw_sources"

wb = openpyxl.load_workbook(os.path.join(RAW_DIR, "prm-est2023-pop.xlsx"), read_only=True, data_only=True)
ws = wb.active
print("=== PRM-EST2023-POP.XLSX ===")
for idx, r in enumerate(ws.iter_rows(values_only=True)):
  if idx < 10 or (r[0] and "Yauco" in str(r[0])):
    print(f"  R{idx}: {list(r)[:8]}")

st = json.load(open(os.path.join(RAW_DIR, "statoids_jaguar_parsed.json"), encoding="utf-8"))
print("\n=== STATOIDS SAMPLE ROWS FOR KEY COUNTRIES ===")
for iso in ["gt", "sv", "hn", "ni", "cr", "pa", "bz", "cu", "do", "ht", "jm", "pr", "bb", "bm", "gp", "vi", "ag", "kn", "dm", "lc", "vc", "gd", "ms", "ky", "tc", "mf", "bl", "cw", "aw", "sx", "vg", "ai"]:
  tbls = st[iso]["tables"]
  # pick table with most year headers
  best = None
  for ti, t in enumerate(tbls):
    if len(t["rows"]) >= 3:
      hdr = t["rows"][0]["cells"]
      if any(x[:2] in ("18", "19", "20") or "Pop" in x or "Date" in x or "Census" in x for x in hdr):
        best = (ti, t)
        if ti >= 2:
          break
  if best:
    ti, t = best
    print(f"  {iso} T{ti} ({len(t['rows'])}r): hdr={t['rows'][0]['cells'][:10]} | r1={t['rows'][1]['cells'][:10]} | last={t['rows'][-1]['cells'][:6]}")
  else:
    print(f"  {iso}: NO MATCH")

cp2 = json.load(open(os.path.join(RAW_DIR, "citypop2_jaguar_parsed.json"), encoding="utf-8"))
print("\n=== CITYPOP2 MAIN TABLES ===")
for k, v in cp2.items():
  if v["tables"]:
    t = v["tables"][0]
    hdr = t["thead"][-1] if t["thead"] else []
    r0 = t["rows"][0]["cells"] if t["rows"] else []
    rl = t["rows"][-1]["cells"] if t["rows"] else []
    print(f"  {k:18s}: n={len(t['rows']):3d} | hdr={hdr} | r0={r0[:8]} | rl={rl[:8]}")
