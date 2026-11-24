import json
import os
import ssl
import urllib.parse
import urllib.request

ctx = ssl.create_default_context()
cache = r"f:\Active Projects\Project 1509 - SVEA\tests\_aus_r2_cache"
os.makedirs(cache, exist_ok=True)


def fetch_json(url, timeout=20):
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
  with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
    return json.loads(r.read().decode("utf-8", errors="replace"))


print("=== 1. INTERNET ARCHIVE SEARCH ===")
for q in [
  "abs 2006 census datapack ssc",
  "abs 2001 census suburb",
  "census commonwealth australia 1911 localities",
  "census commonwealth australia 1921 localities",
  "census commonwealth australia 1933 localities",
  "census commonwealth australia 1947 localities",
  "census commonwealth australia 1954 localities",
  "census commonwealth australia 1961 localities",
  "census commonwealth australia 1966 localities",
  "census commonwealth australia 1971 localities",
  "census commonwealth australia 1976 localities",
  "census commonwealth australia 1981 localities",
  "census commonwealth australia 1986 localities",
  "census commonwealth australia 1991 localities",
  "2006_BCP_SSC",
]:
  u = "https://archive.org/advancedsearch.php?q=" + urllib.parse.quote(q) + "&fl[]=identifier,title,year&rows=5&output=json"
  try:
    d = fetch_json(u, timeout=15)
    resp = d.get("response", {})
    docs = resp.get("docs", [])
    print(f"IA [{q}]: {resp.get('numFound', 0)} hits ->", [(x.get("identifier"), str(x.get("title", ""))[:55]) for x in docs[:3]])
  except Exception as e:
    print(f"IA ERR [{q}]:", e)

print("\n=== 2. WAYBACK CDX FOR ABS 2006/2001 DATAPACKS & COMMUNITY PROFILES ===")
for pat in [
  "abs.gov.au/census/find-census-data/datapacks/download/2006*",
  "datapacks.censusdata.abs.gov.au/datapacks/2006*",
  "abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2001.0*",
  "abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/210*",
  "abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/211*",
  "abs.gov.au/websitedbs/censushome.nsf/home/historicaldata*",
]:
  u = "https://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(pat) + "&output=json&limit=15&filter=statuscode:200&collapse=urlkey"
  try:
    d = fetch_json(u, timeout=20)
    print(f"CDX [{pat}]: {max(0, len(d)-1)} rows")
    for row in d[1:8]:
      print("  ", row[1], row[2][:110])
  except Exception as e:
    print(f"CDX ERR [{pat}]:", e)

print("\n=== 3. ABS WEBSITE SEARCH API / SITEMAP ===")
for u in [
  "https://www.abs.gov.au/census/find-census-data/community-profiles/2006/0",
  "https://www.abs.gov.au/census/find-census-data/community-profiles/2001/0",
  "https://www.abs.gov.au/census/find-census-data/community-profiles/2006/SSC11001",
  "https://www.abs.gov.au/census/find-census-data/community-profiles/2001/SSC11001",
  "https://www.abs.gov.au/census/find-census-data/quickstats/2006/SSC11001",
  "https://www.abs.gov.au/census/find-census-data/quickstats/2001/SSC11001",
  "https://www.abs.gov.au/census/find-census-data/quickstats/1996/UCL100200",
]:
  try:
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
      txt = r.read().decode("utf-8", errors="replace")
      print(f"  OK {r.status} len={len(txt)} {u}")
  except Exception as e:
    print(f"  ERR {str(e)[:50]} {u}")
