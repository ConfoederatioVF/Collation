import json, os, re, requests

OUT_DIR = r"f:\Active Projects\Project 1509 - SVEA\tests\nzl_deep_harvest"
SRC = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\AUSTRAL\_shared\settlement_sources"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 1. Print full source_urls from Round 1 NZ files
for fn in ("enriched_nzl_colonial_historical.json", "enriched_nzl_modern_localities.json"):
  d = json.load(open(os.path.join(SRC, fn), encoding="utf-8"))
  print(f"=== {fn} source_urls ===")
  for u in d.get("metadata", {}).get("source_urls", []):
    print("  ", u)

# 2. List Stats NZ ArcGIS FeatureServices
r = requests.get("https://services2.arcgis.com/vKb0s8tBIA3bdocZ/arcgis/rest/services?f=json", headers=H, timeout=20)
svcs = r.json().get("services", [])
print(f"\n=== STATS NZ ARCGIS SERVICES ({len(svcs)} total) ===")
for s in svcs:
  nm = s.get("name", "")
  if any(k in nm.lower() for k in ("census", "pop", "area", "unit", "urban", "rural", "mesh", "sa1", "sa2", "borough", "county", "historic", "2001", "2006", "2013", "1996", "1991", "1986")):
    print("  ", nm, "|", s.get("type"))

# 3. Check www3.stats.govt.nz subdirs for 1886-1916 and New_Zealand_Official_Yearbooks and meshblock
sub_urls = [
  "https://www3.stats.govt.nz/historic_publications/1886-census/Results-of-Census-1886/",
  "https://www3.stats.govt.nz/historic_publications/1891-census/1891-results-census/",
  "https://www3.stats.govt.nz/historic_publications/1891-census/1891-report-on-results-census/",
  "https://www3.stats.govt.nz/historic_publications/1896-census/1896-results-census/",
  "https://www3.stats.govt.nz/historic_publications/1896-census/1896-report-on-results-census/",
  "https://www3.stats.govt.nz/historic_publications/1901-census/1901-results-census/",
  "https://www3.stats.govt.nz/historic_publications/1901-census/1901-report-on-results-census/",
  "https://www3.stats.govt.nz/historic_publications/1906-census/1906-results-census/",
  "https://www3.stats.govt.nz/historic_publications/1906-census/1906-report-on-results-census/",
  "https://www3.stats.govt.nz/historic_publications/1916-census/Report%20on%20Results%20of%20Census%201916/",
  "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/",
  "https://www3.stats.govt.nz/meshblock/",
  "https://www3.stats.govt.nz/meshblock/2013/",
  "https://www3.stats.govt.nz/census/",
]
print("\n=== WWW3 SUBDIRS ===")
for u in sub_urls:
  try:
    rr = requests.get(u, headers=H, timeout=15)
    if rr.status_code == 200:
      hs = [x for x in re.findall(r'href=["\']([^"\']+)["\']', rr.text, re.I) if not x.startswith("?")]
      print(f"{u} -> 200 ({len(hs)} links): {hs[:12]}")
    else:
      print(f"{u} -> {rr.status_code}")
  except Exception as e:
    print(f"{u} -> ERR {e}")

# 4. Download 2006mbdatasetallnz.zip
zip_path = os.path.join(OUT_DIR, "2006mbdatasetallnz.zip")
if not os.path.exists(zip_path):
  print("\nDownloading 2006mbdatasetallnz.zip...")
  r = requests.get("https://www3.stats.govt.nz/meshblock/2006/excel/2006mbdatasetallnz.zip", headers=H, timeout=120)
  print("2006mbdatasetallnz.zip status:", r.status_code, "bytes:", len(r.content))
  if r.status_code == 200:
    with open(zip_path, "wb") as f:
      f.write(r.content)
