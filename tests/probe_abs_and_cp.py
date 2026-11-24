import os, re, urllib.request, zipfile

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch(u, timeout=15):
  req = urllib.request.Request(u, headers=H)
  with urllib.request.urlopen(req, timeout=timeout) as r:
    return r.read().decode("utf-8", "ignore")

print("=== 1. CITYPOPULATION.DE TABLE STRUCTURE CHECK ===")
for slug in [
  "papuanewguinea/admin/",
  "papuanewguinea/cities/",
  "fiji/admin/",
  "solomonislands/admin/",
  "vanuatu/admin/",
  "newcaledonia/admin/",
  "frenchpolynesia/admin/",
  "samoa/admin/",
  "tonga/admin/",
  "kiribati/admin/",
  "micronesia/admin/",
  "marshallislands/admin/",
  "palau/admin/",
  "guam/admin/",
  "northernmarianas/admin/",
  "cookislands/admin/",
  "tuvalu/admin/",
  "wallisandfutuna/admin/",
  "indonesia/papua/admin/",
]:
  u = "https://www.citypopulation.de/en/" + slug
  try:
    h = fetch(u, timeout=10)
    trs = re.findall(r'<tr[^>]*id="t\d+"[^>]*>.*?</tr>', h, re.S)
    if not trs:
      trs = re.findall(r'<tr[^>]*class="[^"]*(?:rname|adm|city)[^"]*"[^>]*>.*?</tr>', h, re.S)
    rpop_tds = len(re.findall(r'class="rpop', h))
    yrs = sorted(set(re.findall(r'<th[^>]*>[^<]*?(19\d\d|20\d\d)', h)))
    sub_links = sorted(set(re.findall(r'href="(/en/' + slug.split("/")[0] + r'/[^"]+)"', h)))
    print(f"  {slug:28s} | len={len(h):6d} | rpop_tds={rpop_tds:5d} | yrs={yrs[:10]} | sub={len(sub_links)}")
  except Exception as e:
    print(f"  {slug:28s} | ERR {str(e)[:50]}")

print("\n=== 2. ABS HISTORIC CENSUS 1911-1996 PDF/XLS CHECK ===")
abs_pages = [
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2112.0",
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2111.0",
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2110.0",
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2109.0",
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2108.0",
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2107.0",
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2106.0",
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2105.0",
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2104.0",
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2103.0",
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2102.0",
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2101.0",
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2016.0",
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2001.0",
  "https://www.abs.gov.au/ausstats/abs@.nsf/mf/2909.0",
]
for u in abs_pages:
  try:
    h = fetch(u, timeout=10)
    t = re.findall(r"<title>(.*?)</title>", h, re.I | re.S)
    pdfs = len(re.findall(r'\.pdf', h, re.I))
    xls = len(re.findall(r'\.xlsx?|\.zip|\.csv', h, re.I))
    loc = len(re.findall(r'localit', h, re.I))
    print(f"  {u.split('/mf/')[1]:8s} | pdf={pdfs:3d} xls/zip={xls:3d} loc={loc:3d} | {(t[0].strip() if t else '')[:60]}")
  except Exception as e:
    print(f"  {u.split('/mf/')[1]:8s} | ERR {str(e)[:45]}")
