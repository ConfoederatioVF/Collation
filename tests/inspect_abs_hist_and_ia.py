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


print("=== 1. ABS HISTORICAL DATA 1996 / 2001 / 2006 PAGES ===")
for u in [
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata2006",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata2001",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata1996",
  "https://www.abs.gov.au/websitedbs/censushome.nsf/home/historicaldata",
]:
  h = fetch(u)
  links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', h, re.I | re.S)
  print(f"\nPAGE: {u}")
  for hr, tx in links:
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", tx)).strip()
    if t and any(k in t.lower() or k in hr.lower() for k in ["datapack", "profile", "suburb", "localit", "urban", "2001", "2006", "1996", "1991", "1986", "1981", "1976", "1971", "1966", "1961", "1954", "1947", "1933", "1921", "1911", "210", "211", "2016", "2001.0", "2003.0", "quickstat", "cdata", "zip", "xls", "csv"]):
      print(f"  [{t[:75]}] -> {hr[:110]}")

print("\n=== 2. ABS AUSSTATS 2101.0-2112.0 DETAILS PAGES (1911-1991) ===")
cats = [
  ("1991", "2101.0"), ("1986", "2102.0"), ("1981", "2103.0"), ("1976", "2104.0"),
  ("1971", "2105.0"), ("1966", "2106.0"), ("1961", "2107.0"), ("1954", "2108.0"),
  ("1947", "2109.0"), ("1933", "2110.0"), ("1921", "2111.0"), ("1911", "2112.0"),
]
for yr, cat in cats:
  u = f"https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/{cat}{yr}?OpenDocument"
  try:
    h = fetch(u, timeout=15)
    # Find file download links mentioning localities or urban centres
    al = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', h, re.I | re.S)
    loc_hits = []
    for hr, tx in al:
      t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", tx)).strip()
      if any(k in t.lower() for k in ["localit", "urban centre", "persons and dwellings", "bulletin", "part v", "part viii", "population and dwellings", "list of", "index of"]):
        if not hr.startswith("#"):
          loc_hits.append((t[:85], hr[:100]))
    print(f"  {yr} ({cat}): len={len(h)}, loc_hits={len(loc_hits)}")
    for t, hr in loc_hits[:8]:
      print(f"    - {t} -> {hr}")
  except Exception as e:
    print(f"  {yr} ({cat}) ERR: {e}")

print("\n=== 3. INTERNET ARCHIVE ALL CBCS/ABS LOCALITIES CENSUS VOLUMES ===")
q = '(title:(localities) AND (title:(census) OR creator:("Commonwealth Bureau of Census") OR creator:("Australian Bureau of Statistics")))'
u = "https://archive.org/advancedsearch.php?q=" + urllib.parse.quote(q) + "&fl[]=identifier,title,year&rows=100&output=json"
d = json.loads(fetch(u, timeout=20))
docs = d.get("response", {}).get("docs", [])
print(f"IA Localities total found: {d.get('response',{}).get('numFound',0)}")
for x in sorted(docs, key=lambda r: str(r.get("identifier", ""))):
  tid = x.get("identifier", "")
  ttl = str(x.get("title", ""))
  if any(k in (tid + " " + ttl).lower() for k in ["cbcs", "census", "austral", "victoria", "queensland", "tasmania", "new-south-wales", "south-australia", "western-australia", "bulletin"]):
    print(f"  {tid} | {ttl[:85]}")
