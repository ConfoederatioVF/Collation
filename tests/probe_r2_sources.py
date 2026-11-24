import json, os, re, urllib.request, urllib.parse, zipfile

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch(u, timeout=15):
  req = urllib.request.Request(u, headers=H)
  with urllib.request.urlopen(req, timeout=timeout) as r:
    return r.read().decode("utf-8", "ignore")

print("=== 1. NZL 2006MBDATASETALLNZ.ZIP ===")
zf = r"tests\nzl_deep_harvest\2006mbdatasetallnz.zip"
if os.path.exists(zf):
  with zipfile.ZipFile(zf) as z:
    for n in z.namelist():
      print(" ", n, z.getinfo(n).file_size)

print("\n=== 2. ANU HCCDA CATALOG (CHECK 1911-1971 & ALL COLONIAL TABLES) ===")
try:
  h = fetch("https://hccda.ada.edu.au/Collated_Census_Tables/")
  links = sorted(set(re.findall(r'href=["\']([^"\']+?census[^"\']*\.html)["\']', h, re.I)))
  print("  Collated census htmls:", len(links))
  for l in links:
    if any(y in l for y in ("1828","1833","1836","1841","1846","1851","1854","1856","1861","1871","1881","1891","1901","1911","1921","1933")):
      pass
  print("  Years present:", sorted(set(re.findall(r'(1[89]\d\d)', " ".join(links)))))
  # Check HCCDA browse for Commonwealth censuses
  h2 = fetch("https://hccda.ada.edu.au/browse")
  print("  HCCDA browse years:", sorted(set(re.findall(r'\b(1[89]\d\d)\b', h2)))[:40])
except Exception as e:
  print("  HCCDA err:", e)

print("\n=== 3. CITYPOPULATION.DE OCEANIA HISTORICAL TABLES ===")
cp_urls = [
  "https://www.citypopulation.de/en/papuanewguinea/admin/",
  "https://www.citypopulation.de/en/indonesia/papua/admin/",
  "https://www.citypopulation.de/en/fiji/admin/",
  "https://www.citypopulation.de/en/solomonislands/admin/",
  "https://www.citypopulation.de/en/vanuatu/admin/",
  "https://www.citypopulation.de/en/newcaledonia/admin/",
  "https://www.citypopulation.de/en/frenchpolynesia/admin/",
  "https://www.citypopulation.de/en/samoa/admin/",
  "https://www.citypopulation.de/en/tonga/admin/",
  "https://www.citypopulation.de/en/kiribati/admin/",
  "https://www.citypopulation.de/en/micronesia/admin/",
  "https://www.citypopulation.de/en/marshallislands/admin/",
  "https://www.citypopulation.de/en/palau/admin/",
  "https://www.citypopulation.de/en/guam/admin/",
  "https://www.citypopulation.de/en/northernmarianas/admin/",
  "https://www.citypopulation.de/en/cookislands/admin/",
  "https://www.citypopulation.de/en/tuvalu/admin/",
  "https://www.citypopulation.de/en/wallisandfutuna/admin/",
  "https://www.citypopulation.de/en/niue/",
]
for u in cp_urls:
  try:
    h = fetch(u, timeout=12)
    yrs = sorted(set(re.findall(r'rpop\d+[^>]*>.*?(19\d\d|20\d\d)', h)))
    rows = len(re.findall(r'<tr[^>]*data-lat=', h))
    th_yrs = sorted(set(re.findall(r'<th[^>]*class=["\'][^"\']*rpop[^"\']*["\'][^>]*>[^<]*(19\d\d|20\d\d)', h)))
    print(f"  {u.split('/en/')[1]:30s} | rows={rows:4d} | th_yrs={th_yrs}")
  except Exception as e:
    print(f"  {u.split('/en/')[1]:30s} | ERR {str(e)[:50]}")

print("\n=== 4. ABS HISTORIC CENSUS 2101-2112 LOCALITIES CHECK ===")
for cat in ["2102.0", "2103.0", "2104.0", "2105.0", "2106.0", "2107.0", "2108.0", "2109.0", "2110.0", "2111.0", "2112.0"]:
  u = f"https://www.abs.gov.au/AUSSTATS/abs@.nsf/allprimarymainfeatures/CENSUS_{cat}"
  # Better: Lookup URL
  u2 = f"https://www.abs.gov.au/AUSSTATS/abs@.nsf/Lookup/{cat}main+features1"
  try:
    req = urllib.request.Request(u2, headers=H)
    with urllib.request.urlopen(req, timeout=8) as r:
      txt = r.read().decode("utf-8","ignore")
      title = re.findall(r"<title>(.*?)</title>", txt, re.I | re.S)
      print(f"  {cat}: {title[0].strip()[:75] if title else 'no title'}")
  except Exception as e:
    print(f"  {cat}: ERR {str(e)[:45]}")
