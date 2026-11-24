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


print("=== 1. ABS AUSSTATS CATALOGUE 2 (CENSUS) ===")
for num in ["2", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9"]:
  u = f"https://www.abs.gov.au/AUSSTATS/abs@.nsf/ViewContent?readform&view=ProductsbyCatalogue&Action=Expand&Num={num}"
  try:
    h = fetch(u, timeout=20)
    links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', h, re.I | re.S)
    hits = []
    for href, txt in links:
      t = re.sub(r"<[^>]+>", "", txt).strip()
      t = re.sub(r"\s+", " ", t)
      if re.search(r"2\d{3}\.\d", t) or any(k in t.lower() for k in ["localit", "suburb", "census", "urban", "historical", "1911", "1921", "1933", "1947", "1954", "1961", "1966", "1971", "1976", "1981", "1986", "1991", "1996", "2001", "2006"]):
        hits.append((t[:95], href))
    print(f"Num={num}: {len(hits)} hits")
    for t, hr in hits[:25]:
      print(f"  {t} -> {hr[:100]}")
  except Exception as e:
    print(f"Num={num} ERR: {e}")

print("\n=== 2. ABS AUSSTATS HISTORIC CENSUS PUBLICATIONS (2101-2114, 2401-2499, 2001-2035) ===")
for cat in [
  "2001.0", "2002.0", "2003.0", "2004.0", "2005.0", "2015.0", "2016.0", "2016.1", "2016.2", "2016.3", "2016.4", "2016.5", "2016.6", "2016.7",
  "2035.0", "2101.0", "2102.0", "2103.0", "2104.0", "2105.0", "2106.0", "2107.0", "2108.0", "2109.0", "2110.0", "2111.0", "2112.0", "2113.0", "2114.0",
  "2443.0", "2452.0", "2453.0", "2454.0", "2455.0", "2456.0", "2457.0", "2458.0", "2459.0",
  "2901.0", "2914.0",
]:
  u = f"https://www.abs.gov.au/AUSSTATS/abs@.nsf/allprimarymainfeatures/{cat}?opendocument"
  try:
    h = fetch(u, timeout=10)
    t = re.findall(r"<title>(.*?)</title>", h, re.I | re.S)
    ts = re.sub(r"\s+", " ", t[0]).strip() if t else ""
    if "Australian Bureau of Statistics" != ts and ts:
      print(f"  {cat}: {ts[:90]}")
  except Exception:
    pass

print("\n=== 3. ABS WEBSITEDBS & CENSUS 2006/2001/1996 COMMUNITY PROFILES / DATAPACKS ===")
for u in [
  "https://www.abs.gov.au/census/find-census-data/community-profiles/2006",
  "https://www.abs.gov.au/census/find-census-data/community-profiles/2001",
  "https://www.abs.gov.au/census/find-census-data/datapacks/2006",
  "https://www.abs.gov.au/census/find-census-data/datapacks/2001",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/Lookup/2001.0main+features12006",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/ProductsbyCatalogue/A7562E9531E49980CA2578D90018E865?OpenDocument",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata1911",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata1921",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata1933",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata1947",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata1954",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata1961",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata1966",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata1971",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata1976",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata1981",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata1986",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata1991",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata1996",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata2001",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata2006",
]:
  try:
    h = fetch(u, timeout=12)
    t = re.findall(r"<title>(.*?)</title>", h, re.I | re.S)
    ts = re.sub(r"\s+", " ", t[0]).strip() if t else ""
    print(f"  OK len={len(h):6d} title={ts[:75]!r} -> {u}")
  except Exception as e:
    print(f"  ERR {str(e)[:45]} -> {u}")
