"""Downloads CSO Ireland (1841-2016 historic counties), StatGreenland (1977-2026),
and parses Galloway Prussia BIFF2 XLS (1861-1910) & INSEE (1876-2023) départements."""
import csv
import json
import os
import struct
import urllib.request
import zipfile
from collections import defaultdict

import openpyxl

HGIS = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MAGNETIC\_shared\subadmin_hgis\raw_sources"
PARSED = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MAGNETIC\_shared\subadmin_hgis\parsed"
os.makedirs(PARSED, exist_ok=True)
UA = {"User-Agent": "SVEA-Viscount-MAGNETIC/1.0"}

# 1. Download CSO Ireland CNA13 (1841-2016 all provinces & counties!)
cso_p = os.path.join(HGIS, "cso_ireland_cna13_1841_2016.csv")
if not os.path.isfile(cso_p):
  req = urllib.request.Request("https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/CNA13/CSV/1.0/en", headers=UA)
  with urllib.request.urlopen(req, timeout=60) as r:
    data = r.read()
  with open(cso_p, "wb") as f:
    f.write(data)
  print(f"[CSO Ireland CNA13] OK {len(data):,} B", flush=True)
else:
  print(f"[CSO Ireland CNA13] CACHED {os.path.getsize(cso_p):,} B", flush=True)

# 2. Fetch StatGreenland BEXSTA metadata & query municipality/district population (1977-2026)
gl_p = os.path.join(HGIS, "statgl_bexsta_1977_2026.json")
if not os.path.isfile(gl_p):
  try:
    meta_req = urllib.request.Request("https://bank.stat.gl/api/v1/en/Greenland/BE/BE01/BE0120/BEXSTA.px", headers=UA)
    with urllib.request.urlopen(meta_req, timeout=30) as r:
      meta = json.loads(r.read().decode("utf-8"))
    print(f"[StatGL BEXSTA vars] {[(v['code'], len(v['values']), v['values'][:5]) for v in meta.get('variables', [])]}", flush=True)
    # Build minimal query: district x selected years, total sex/age/place
    q = {"query": [], "response": {"format": "json"}}
    for v in meta.get("variables", []):
      code = v["code"]
      vals = v["values"]
      if code.lower() in ("district", "municipality", "area", "place", "locality"):
        q["query"].append({"code": code, "selection": {"filter": "all", "values": ["*"]}})
      elif code.lower() in ("time", "year"):
        q["query"].append({"code": code, "selection": {"filter": "item", "values": [x for x in vals if x in ("1977","1980","1990","2000","2010","2020","2025","2026")] or vals[-5:]}})
      else:
        # pick total if present else first
        tot = [x for x in vals if x.lower() in ("t", "tot", "total", "0", "all")]
        q["query"].append({"code": code, "selection": {"filter": "item", "values": [tot[0] if tot else vals[0]]}})
    post = urllib.request.Request(
      "https://bank.stat.gl/api/v1/en/Greenland/BE/BE01/BE0120/BEXSTA.px",
      data=json.dumps(q).encode("utf-8"),
      headers={**UA, "Content-Type": "application/json"},
      method="POST",
    )
    with urllib.request.urlopen(post, timeout=45) as r:
      gdata = r.read()
    with open(gl_p, "wb") as f:
      f.write(gdata)
    print(f"[StatGL BEXSTA data] OK {len(gdata):,} B", flush=True)
  except Exception as e:
    print(f"[StatGL BEXSTA] ERR: {e}", flush=True)

# 3. Pure-Python BIFF2 parser for Galloway Prussia Database POP*.XLS (1861-1910)
def parse_biff2_xls(raw_bytes):
  """Reads BIFF2 .XLS cells (INTEGER=2, NUMBER=3, LABEL=4) into dict of {(row, col): val}."""
  pos = 0
  n = len(raw_bytes)
  cells = {}
  while pos + 4 <= n:
    rec_id, rec_len = struct.unpack_from("<HH", raw_bytes, pos)
    pos += 4
    if pos + rec_len > n:
      break
    payload = raw_bytes[pos:pos + rec_len]
    pos += rec_len
    if rec_id == 0x000A:  # EOF
      break
    elif rec_id == 0x0002 and rec_len >= 9:  # INTEGER
      r, c = struct.unpack_from("<HH", payload, 0)
      val = struct.unpack_from("<H", payload, 7)[0]
      cells[(r, c)] = val
    elif rec_id == 0x0003 and rec_len >= 15:  # NUMBER (IEEE float64)
      r, c = struct.unpack_from("<HH", payload, 0)
      val = struct.unpack_from("<d", payload, 7)[0]
      cells[(r, c)] = val
    elif rec_id == 0x0004 and rec_len >= 8:  # LABEL
      r, c = struct.unpack_from("<HH", payload, 0)
      slen = payload[7]
      txt = payload[8:8 + slen].decode("latin-1", errors="replace").strip()
      cells[(r, c)] = txt
  if not cells:
    return []
  max_r = max(r for r, _ in cells)
  max_c = max(c for _, c in cells)
  rows = []
  for r in range(max_r + 1):
    rows.append([cells.get((r, c), "") for c in range(max_c + 1)])
  return rows

with zipfile.ZipFile(os.path.join(HGIS, "Galloway_Prussia_Database_XLS.zip")) as zf:
  galloway_summary = {}
  for fn in sorted(zf.namelist()):
    if fn.upper().startswith("POP") and fn.upper().endswith(".XLS"):
      yr = int(fn[3:7])
      rows = parse_biff2_xls(zf.read(fn))
      if rows:
        galloway_summary[yr] = {"nrows": len(rows), "hdr": rows[0], "sample1": rows[1] if len(rows) > 1 else []}
        out_csv = os.path.join(PARSED, f"galloway_prussia_{yr}.csv")
        with open(out_csv, "w", newline="", encoding="utf-8") as cf:
          csv.writer(cf).writerows(rows)
  print(f"[Galloway Prussia BIFF2] Parsed {len(galloway_summary)} censuses ({sorted(galloway_summary.keys())})", flush=True)
  if 1871 in galloway_summary:
    print(f"  1871: rows={galloway_summary[1871]['nrows']} hdr={galloway_summary[1871]['hdr'][:10]} r1={galloway_summary[1871]['sample1'][:10]}", flush=True)
  if 1910 in galloway_summary:
    print(f"  1910: rows={galloway_summary[1910]['nrows']} hdr={galloway_summary[1910]['hdr'][:10]} r1={galloway_summary[1910]['sample1'][:10]}", flush=True)

# 4. Aggregate INSEE 1876-2023 communes -> 96 French départements CSV
wb = openpyxl.load_workbook(os.path.join(HGIS, "insee_pop_hist_1876_2023.xlsx"), read_only=True)
ws = wb["pop_1876_2023"]
hdr_codes = None
dep_totals = defaultdict(lambda: defaultdict(float))
yr_cols = []
for idx, row in enumerate(ws.iter_rows(values_only=True)):
  if idx == 5:
    hdr_codes = list(row)
    for ci, col in enumerate(hdr_codes):
      cs = str(col or "")
      if cs.startswith(("PMUN", "PSDC", "PTOT")):
        yr_str = cs[-4:]
        if yr_str.isdigit():
          yr_cols.append((ci, int(yr_str)))
    continue
  if idx < 6 or not hdr_codes:
    continue
  dep = str(row[2] or "").strip()
  if not dep or dep.startswith("97"):  # exclude overseas DOMs outside Europe
    continue
  for ci, yr in yr_cols:
    val = row[ci]
    if isinstance(val, (int, float)) and val > 0:
      dep_totals[dep][yr] += float(val)

all_yrs = sorted({yr for _, yr in yr_cols})
out_fr = os.path.join(PARSED, "insee_france_departements_1876_2023.csv")
with open(out_fr, "w", newline="", encoding="utf-8") as cf:
  w = csv.writer(cf)
  w.writerow(["DEP"] + [str(y) for y in all_yrs])
  for dep in sorted(dep_totals.keys()):
    w.writerow([dep] + [int(round(dep_totals[dep].get(y, 0))) for y in all_yrs])
print(f"[INSEE France Départements] Aggregated {len(dep_totals)} metropolitan départements across {len(all_yrs)} censuses ({all_yrs[0]}..{all_yrs[-1]})", flush=True)
print(f"  France metropolitan totals: 1876={sum(d.get(1876,0) for d in dep_totals.values()):,.0f} | 1911={sum(d.get(1911,0) for d in dep_totals.values()):,.0f} | 1962={sum(d.get(1962,0) for d in dep_totals.values()):,.0f} | 2021={sum(d.get(2021,0) for d in dep_totals.values()):,.0f}", flush=True)
