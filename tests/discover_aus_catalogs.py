import re
import ssl
import urllib.request

ctx = ssl.create_default_context()


def fetch(url):
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
  with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
    return r.read().decode("utf-8", errors="replace")


print("=== 1. ABS DATAPACKS INVENTORY ===")
dp_html = fetch("https://www.abs.gov.au/census/find-census-data/datapacks")
all_dp = sorted(set(re.findall(r'/census/find-census-data/datapacks/download/[^\s"\'<>]+\.zip', dp_html, re.I)))
print(f"Total datapack zips found: {len(all_dp)}")
# Filter for AUST/AUS short-header across years/products/geos
aust_short = [u for u in all_dp if ("_for_AUST_" in u or "_for_AUS_" in u) and "short-header" in u]
print("AUST/AUS short-header zips:")
for u in aust_short:
  if any(g in u for g in ["_SSC_", "_SAL_", "_UCL_", "_LGA_", "_SA2_", "_SLA_", "_POA_", "_CD_", "_SUA_"]):
    print(" ", u)
# Check what years exist in all_dp
years_dp = sorted(set(re.findall(r'/download/(\d{4})_', " ".join(all_dp))))
print("Years in DataPacks:", years_dp)
# Check all TSP zips for AUST/AUS
print("ALL TSP AUST/AUS short-header:")
for u in aust_short:
  if "_TSP_" in u:
    print(" ", u)
# Check 2006 zips if any
z2006 = [u for u in all_dp if "/2006_" in u]
print(f"2006 zips count: {len(z2006)}", z2006[:10])

print("\n=== 2. HCCDA INVENTORY ===")
for sub in ["Collated_Census_Tables/", "Individual_Census_Tables/"]:
  u = "https://hccda.ada.edu.au/" + sub
  h = fetch(u)
  links = sorted(set(re.findall(r'href="([^"]+)"', h)))
  links = [l for l in links if not l.startswith("?") and not l.startswith("/") and l != "../"]
  print(f"{sub} ({len(links)} items):", links[:60])

print("\n=== 3. ABS HISTORIC CENSUS INDEX ===")
hist_html = fetch("https://www.abs.gov.au/AUSSTATS/abs@.nsf/allprimarymainfeatures/475C8B5C5A79862BCA25784C00158F17")
# Extract links with text
alinks = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', hist_html, re.I | re.S)
for href, txt in alinks:
  t = re.sub(r"<[^>]+>", "", txt).strip()
  t = re.sub(r"\s+", " ", t)
  if any(k in t.lower() for k in ["1911", "1921", "1933", "1947", "1954", "1961", "1966", "1971", "1976", "1981", "1986", "1991", "1996", "2001", "2006", "localit", "census", "210", "211"]):
    print(f"  [{t[:80]}] -> {href}")
