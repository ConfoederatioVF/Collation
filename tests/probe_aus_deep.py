import json
import re
import ssl
import urllib.parse
import urllib.request

ctx = ssl.create_default_context()


def fetch(url, timeout=25):
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
  with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
    return r.read().decode("utf-8", errors="replace")


print("=== 1. ABS CENSUS HISTORICAL & ARCHIVE PAGES ===")
for u in [
  "https://www.abs.gov.au/census/find-census-data",
  "https://www.abs.gov.au/census/find-census-data/historical-census-data",
  "https://www.abs.gov.au/census/find-census-data/community-profiles",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/ViewContent?readform&view=ProductsbyCatalogue&Action=Expand&Num=2.2",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2001.02006?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2006.02006?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2016.02001?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2101.01911?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2102.01996?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2104.01986?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2105.01981?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2106.01976?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2107.01971?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2108.01966?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2109.01961?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2110.01954?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2111.01947?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2112.01933?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2113.01921?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2114.01911?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2103.01991?OpenDocument",
]:
  try:
    h = fetch(u, timeout=15)
    title = re.findall(r"<title>(.*?)</title>", h, re.I | re.S)
    t = re.sub(r"\s+", " ", title[0]).strip() if title else ""
    pdfs = len(re.findall(r"\.(?:pdf|xls|xlsx|zip|csv)", h, re.I))
    print(f"  OK len={len(h):7d} files={pdfs:3d} title={t[:70]!r} -> {u}")
  except Exception as e:
    print(f"  ERR {type(e).__name__}: {str(e)[:60]} -> {u}")

print("\n=== 2. DATA.GOV.AU & ARCHIVE.ORG SEARCH FOR 2001/2006 SSC & HISTORIC CENSUS ===")
for q in ["ABS census 2006 SSC", "ABS census 2001 suburb", "census 1911 1921 1933 localities australia", "2006 BCP SSC"]:
  try:
    url = "https://data.gov.au/api/3/action/package_search?q=" + urllib.parse.quote(q) + "&rows=8"
    d = json.loads(fetch(url, timeout=15))
    res = d.get("result", {}).get("results", [])
    print(f"  data.gov.au [{q}]: {len(res)} hits")
    for r in res[:5]:
      print(f"    - {r.get('title','')[:75]} ({len(r.get('resources',[]))} res)")
  except Exception as e:
    print(f"  data.gov.au ERR [{q}]: {e}")

print("\n=== 3. ABS DATA API (SDMX) CHECK ===")
try:
  h = fetch("https://data.api.abs.gov.au/rest/dataflow/ABS", timeout=20)
  flows = re.findall(r'id="(CENSUS[^"]*|C\d+[^"]*|HIST[^"]*)"', h, re.I)
  print("  ABS SDMX census dataflows:", sorted(set(flows))[:40])
except Exception as e:
  print("  ABS SDMX ERR:", e)

print("\n=== 4. HCCDA INDIVIDUAL TABLES ===")
for st in ["NSW", "QLD", "SA", "TAS", "VIC", "WA"]:
  try:
    h = fetch(f"https://hccda.ada.edu.au/Individual_Census_Tables/{st}/", timeout=15)
    links = [l for l in re.findall(r'href="([^"]+)"', h) if not l.startswith("?") and not l.startswith("/") and l != "../"]
    print(f"  HCCDA Individual/{st}: {len(links)} items -> {links[:12]}")
  except Exception as e:
    print(f"  HCCDA Individual/{st} ERR:", e)
