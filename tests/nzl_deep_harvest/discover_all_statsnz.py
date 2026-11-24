import json, os, re, requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SRC = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\AUSTRAL\_shared\settlement_sources"

# 1. Check metadata in Round-1 NZ files
for fn in ("enriched_nzl_colonial_historical.json", "enriched_nzl_modern_localities.json", "nzl_official_census_timeseries.json"):
  d = json.load(open(os.path.join(SRC, fn), encoding="utf-8"))
  if "metadata" in d:
    print(f"=== METADATA {fn} ===")
    print(json.dumps(d["metadata"], indent=2, ensure_ascii=False)[:1500])

# 2. List contents of www3.stats.govt.nz/historic_publications/ subdirectories
dirs = [
  "fenton-observations-aboriginal-inhabitants-nz/",
  "1871-census/", "1874-census/", "1878-census/", "1881-census/", "1886-census/",
  "1891-census/", "1896-census/", "1901-census/", "1906-census/", "1911-census/", "1916-census/",
  "1860-statistics-nz/", "1861-statistics-nz/", "1864-statistics-nz/", "1867-statistics-nz/",
  "statistics-new-munster-NZ-1841-1848/", "statistics-nelson-nz-1843-1854/", "statistics-new-plymouth-1853-1856/",
]
print("\n=== WWW3.STATS.GOVT.NZ DIRECTORY LISTINGS ===")
for dd in dirs:
  u = "https://www3.stats.govt.nz/historic_publications/" + dd
  try:
    r = requests.get(u, headers=HEADERS, timeout=15)
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', r.text, re.I)
    clean = [h for h in hrefs if not h.startswith("?") and h != "/historic_publications/"]
    print(f"{dd}: {clean}")
  except Exception as e:
    print(f"{dd}: ERR {e}")

# 3. Scrape download links from stats.govt.nz 2013 census & csv-files-for-download
print("\n=== STATS.GOVT.NZ 2013 CENSUS & LARGE DATASETS ===")
for u in [
  "https://www.stats.govt.nz/information-releases/2013-census-usually-resident-population-counts/",
  "https://www.stats.govt.nz/large-datasets/csv-files-for-download/",
  "https://www.stats.govt.nz/information-releases/2018-census-population-and-dwelling-counts/",
  "https://www.stats.govt.nz/information-releases/statistical-standard-for-geographic-areas-2018/",
]:
  try:
    r = requests.get(u, headers=HEADERS, timeout=15)
    links = re.findall(r'href=["\']([^"\']+(?:xlsx?|csv|zip|pdf))["\']', r.text, re.I)
    print(f"URL {u} -> {len(links)} files")
    for l in links:
      if any(k in l.lower() for k in ("census", "population", "area", "meshblock", "2001", "2006", "2013", "1996", "historic", "long")):
        print("   ", l)
  except Exception as e:
    print("ERR", u, e)

# 4. Probe Stats NZ Digital Collection (ContentDM) & Store House for 1921-1996 Vol 1
print("\n=== STATS NZ STORE HOUSE (CONTENTDM) & STATS.GOVT.NZ SEARCH ===")
cdm_probes = [
  "https://cdm20045.contentdm.oclc.org/digital/api/search/collection/p20045coll1/searchterm/Increase%20and%20Location%20of%20Population/maxRecords/50",
  "https://cdm20045.contentdm.oclc.org/digital/api/collections",
  "https://datafinder.stats.govt.nz/services/api/v1/layers/?q=2006+census",
  "https://datafinder.stats.govt.nz/services/api/v1/layers/?q=2013+census+meshblock",
  "https://datafinder.stats.govt.nz/services/api/v1/layers/?q=2013+census+area+unit",
]
for u in cdm_probes:
  try:
    r = requests.get(u, headers=HEADERS, timeout=15)
    print("API", r.status_code, len(r.text), u)
    if r.status_code == 200:
      print("  preview:", r.text[:400].replace("\n", " "))
  except Exception as e:
    print("API ERR", u, e)
