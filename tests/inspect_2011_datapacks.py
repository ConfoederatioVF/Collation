import csv
import io
import json
import os
import zipfile
import openpyxl

cache = r"f:\Active Projects\Project 1509 - SVEA\tests\_aus_r2_cache"
src_dir = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\AUSTRAL\_shared\settlement_sources"

sal = json.load(open(os.path.join(src_dir, "enriched_aus_sal_modern.json"), encoding="utf-8"))["settlements"]
ucl = json.load(open(os.path.join(src_dir, "aus_official_ucl_lga_timeseries.json"), encoding="utf-8"))
if "settlements" in ucl:
  ucl = ucl["settlements"]

print(f"Existing SAL: {len(sal)} (2011={sum(1 for v in sal.values() if '2011' in v['population'])}, 2016={sum(1 for v in sal.values() if '2016' in v['population'])}, 2021={sum(1 for v in sal.values() if '2021' in v['population'])})")

# Inspect 2011_BCP_SSC
zf = zipfile.ZipFile(os.path.join(cache, "2011_BCP_SSC_for_AUST_short-header.zip"))
b01_name = [n for n in zf.namelist() if n.endswith("B01_AUST_SSC_short.csv")][0]
rows = list(csv.DictReader(io.TextIOWrapper(zf.open(b01_name), encoding="utf-8")))
print(f"\n2011_BCP_SSC rows: {len(rows)}, cols sample: {list(rows[0].keys())[:10]}")
pos = [r for r in rows if int(r.get("Tot_P_P", 0) or 0) > 0]
print(f"2011_BCP_SSC Tot_P_P > 0: {len(pos)}")

# Read geog desc xlsx for SSC names
geo_name = [n for n in zf.namelist() if "geog_desc" in n][0]
wb = openpyxl.load_workbook(io.BytesIO(zf.read(geo_name)), read_only=True, data_only=True)
ws = wb.active
ssc_names = {}
for i, r in enumerate(ws.iter_rows(values_only=True)):
  if i == 0:
    print("Geog header:", r)
    continue
  if r[0] == "SSC":
    ssc_names[str(r[1])] = str(r[2])
print(f"2011 SSC names loaded: {len(ssc_names)}, samples: {list(ssc_names.items())[:5]}")

# Check TSP SA2, SLA, LGA
for zfn, geo in [
  ("2011_TSP_SA2_for_AUST_short-header.zip", "SA2"),
  ("2011_TSP_SLA_for_AUST_short-header.zip", "SLA"),
  ("2011_TSP_LGA_for_AUST_short-header.zip", "LGA"),
]:
  zf2 = zipfile.ZipFile(os.path.join(cache, zfn))
  t01 = [n for n in zf2.namelist() if f"T01_AUST_{geo}_short.csv" in n][0]
  r2 = list(csv.DictReader(io.TextIOWrapper(zf2.open(t01), encoding="utf-8")))
  tot_cols = [c for c in r2[0].keys() if "Tot_P" in c or "Total" in c]
  print(f"{zfn}: {len(r2)} rows, tot_cols={tot_cols[:10]}")
