import json, os, re, requests
from collections import Counter

SRC = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\AUSTRAL\_shared\settlement_sources"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# 1. Check current NZ counts per benchmark year across all existing NZ files
nz_files = [
  "enriched_nzl_modern_localities.json",
  "enriched_nzl_colonial_historical.json",
  "nzl_official_census_timeseries.json",
  "nzl_colonial_towns_1840_1907.json",
  "nzl_pre1840_maori_evidence.json",
  "enriched_precolonial_archaeological_habitations.json",
]

# Also check how many NZ entities exist in the built chapter settlements
ch_files = [
  r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\AUSTRAL\1.precolonial\5.pre_european_new_zealand\pre_european_new_zealand_settlements.json",
  r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\AUSTRAL\2.colonial\2.colonial_new_zealand\colonial_new_zealand_settlements.json",
  r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\AUSTRAL\3.modern\2.modern_new_zealand\modern_new_zealand_settlements.json",
]

for p in ch_files:
  if not os.path.exists(p):
    print("Missing:", p)
    continue
  d = json.load(open(p, encoding="utf-8"))
  yrs_active = Counter()
  yrs_direct = Counter()
  post95_only = 0
  for k, v in d.items():
    ys = [int(y) for y, val in (v.get("population") or {}).items() if float(val) > 0]
    if not ys:
      continue
    if min(ys) >= 1996:
      post95_only += 1
    y0, y1 = min(ys), max(ys)
    for by in [1800, 1840, 1850, 1860, 1870, 1880, 1890, 1900, 1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2006, 2010, 2020]:
      if y0 <= by <= y1:
        yrs_active[by] += 1
      if any(abs(y - by) <= 5 for y in ys):
        yrs_direct[by] += 1
  print(f"\n=== {os.path.basename(p)}: total={len(d)}, post1995_only={post95_only} ({100*post95_only/max(1,len(d)):.1f}%) ===")
  for by in [1800, 1840, 1850, 1860, 1880, 1900, 1920, 1950, 1970, 1980, 1990, 2000, 2006, 2010, 2020]:
    if yrs_active[by] or yrs_direct[by]:
      print(f"  {by}: span_active={yrs_active[by]:4d}, direct+-5y={yrs_direct[by]:4d}")

# 2. Check modern_localities missing 2001/2006
mod_raw = json.load(open(os.path.join(SRC, "enriched_nzl_modern_localities.json"), encoding="utf-8"))
mod = mod_raw.get("settlements", mod_raw)
miss_2001 = [k for k, v in mod.items() if "2001" not in (v.get("population") or {})]
miss_2006 = [k for k, v in mod.items() if "2006" not in (v.get("population") or {})]
print(f"\nenriched_nzl_modern_localities: total={len(mod)}, missing 2001={len(miss_2001)}, missing 2006={len(miss_2006)}")
print("Sample missing 2006:", [(k, mod[k]["name"], mod[k]["admin1"], mod[k]["coords"]) for k in miss_2006[:8]])

# 3. Probe Stats NZ 2013 & 2006 Census AU/Meshblock datasets & ArcGIS endpoints
probe_urls = [
  "https://www.stats.govt.nz/large-datasets/csv-files-for-download/",
  "https://www.stats.govt.nz/information-releases/2013-census-usually-resident-population-counts/",
  "https://archive.stats.govt.nz/Census/2013-census/data-tables/population-dwelling-tables.aspx",
  "https://archive.stats.govt.nz/Census/2006CensusHomePage/QuickStats/AboutAPlace.aspx",
  "https://services2.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services?f=json",
  "https://datafinder.stats.govt.nz/services/api/v1/layers/?q=area+unit+2013",
  "https://www.stats.govt.nz/assets/Uploads/2013-Census-usually-resident-population-counts/Download-data/2013-census-usually-resident-population-counts-tables.xlsx",
  "https://www.stats.govt.nz/assets/Uploads/2013-Census-usually-resident-population-counts/Download-data/2013-census-usually-resident-population-counts-tables.xls",
]
for u in probe_urls:
  try:
    r = requests.get(u, headers=HEADERS, timeout=12, stream=True)
    print("PROBE", r.status_code, r.headers.get("content-type","")[:40], r.headers.get("content-length",""), u)
    r.close()
  except Exception as e:
    print("PROBE ERR", u, e)
