import os, re, zipfile, requests

OUT_DIR = r"f:\Active Projects\Project 1509 - SVEA\tests\nzl_deep_harvest"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 1. Inspect contents of 2006mbdatasetallnz.zip
zp = os.path.join(OUT_DIR, "2006mbdatasetallnz.zip")
with zipfile.ZipFile(zp) as z:
  print("=== 2006mbdatasetallnz.zip contents ===")
  for info in z.infolist():
    print(f"  {info.filename:60s} {info.file_size:12d}")

# 2. Check www3.stats.govt.nz/meshblock/2013/csv/ and /excel/
for sub in ("https://www3.stats.govt.nz/meshblock/2013/csv/", "https://www3.stats.govt.nz/meshblock/2013/excel/"):
  r = requests.get(sub, headers=H, timeout=15)
  hs = [x for x in re.findall(r'href=["\']([^"\']+)["\']', r.text, re.I) if not x.startswith("?")]
  print(f"\n=== {sub} ===")
  for h in hs:
    print("  ", h)

# 3. Inspect stats.govt.nz historical-census-collection & previous-censuses
for u in (
  "https://www.stats.govt.nz/census/previous-censuses/historical-census-collection/",
  "https://www.stats.govt.nz/census/previous-censuses/",
):
  r = requests.get(u, headers=H, timeout=15)
  print(f"\n=== LINKS ON {u} ===")
  links = re.findall(r'href=["\']([^"\']+)["\']', r.text, re.I)
  for l in links:
    if any(k in l.lower() for k in ("census", "192", "193", "194", "195", "196", "197", "198", "199", "2001", "2006", "2013", "pdf", "xls", "csv", "zip", "contentdm", "historic", "archive", "digit")):
      if not l.startswith("#"):
        print("  ", l)

# 4. Check New_Zealand_Official_Yearbooks years and sample directory
r = requests.get("https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/", headers=H, timeout=15)
yrs = [x for x in re.findall(r'href=["\']([^"\']+)["\']', r.text, re.I) if "New_Zealand_Official_Yearbooks/" in x]
print(f"\n=== NZOYB ({len(yrs)} dirs) ===")
print("  first 10:", yrs[:10])
print("  last 15:", yrs[-15:])
for sample in ("1927", "1937", "1951-52", "1962", "1972", "1982", "1992", "1997"):
  rr = requests.get(f"https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/{sample}/", headers=H, timeout=12)
  hs = [x for x in re.findall(r'href=["\']([^"\']+)["\']', rr.text, re.I) if not x.startswith("?")]
  print(f"  NZOYB {sample} ({rr.status_code}): {hs[:8]}")
