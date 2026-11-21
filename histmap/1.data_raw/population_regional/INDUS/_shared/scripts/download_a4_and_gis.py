"""Downloads saketlab/censusindia 1941-2011 GIS releases, probes Census of India Table A-04
(1901-2011 all towns Class I-VI) from censusindia.gov.in NADA, and checks XRONOS API for PK/BD/LK/AF/IR.
"""

import os
import re
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CDIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "INDUS", "_shared", "_census_cache")
ARCH_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "INDUS", "_shared", "sites_indus_south_asia", "0.raw_data")
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SVEA-INDUS/1.0"}

# 1. saketlab/censusindia releases
rr = requests.get("https://api.github.com/repos/saketlab/censusindia/releases", headers=HDR, timeout=30)
if rr.ok:
  for rel in rr.json()[:4]:
    print("Release:", rel.get("tag_name"), "assets:", len(rel.get("assets", [])))
    for a in rel.get("assets", []):
      nm = a["name"]
      if any(k in nm for k in ("1941-states", "1941-districts", "1951-states", "2011-states", "2011-districts")):
        dst = os.path.join(CDIR, nm)
        if not os.path.exists(dst):
          dr = requests.get(a["browser_download_url"], headers=HDR, timeout=120)
          if dr.ok:
            open(dst, "wb").write(dr.content)
            print(f"  [OK] {nm}: {len(dr.content):,} B")
        else:
          print(f"  [SKIP] {nm}")

# 2. Census of India NADA Table A-04 (Class I-VI 1901-2011 ALL Towns)
for cid in range(42874, 42886):
  try:
    rc = requests.get(f"https://censusindia.gov.in/nada/index.php/catalog/{cid}", headers=HDR, timeout=25)
    if rc.ok:
      tm = re.search(r"<title>(.*?)</title>", rc.text, re.S)
      title = re.sub(r"\s+", " ", tm.group(1)).strip() if tm else ""
      dls = list(dict.fromkeys(re.findall(r"https?://censusindia\.gov\.in/nada/index\.php/catalog/\d+/download/\d+/[^\s\"\'<>]+", rc.text)))
      if not dls:
        dls = list(dict.fromkeys(re.findall(r"/nada/index\.php/catalog/\d+/download/\d+", rc.text)))
      if "A-04" in title or "A-4" in title or "Towns" in title or "CLASS" in rc.text.upper():
        print(f"NADA {cid}: {title[:90]} | dls={dls[:3]}")
        for d_i, dl in enumerate(dls[:2]):
          full_u = dl if dl.startswith("http") else f"https://censusindia.gov.in{dl}"
          dr = requests.get(full_u, headers=HDR, timeout=60)
          if dr.ok and len(dr.content) > 2000:
            cd = dr.headers.get("Content-Disposition", "")
            fm = re.search(r'filename="?([^";]+)"?', cd)
            ext = ".xlsx" if "xlsx" in (cd + full_u).lower() else (".xls" if ".xls" in (cd + full_u).lower() else ".bin")
            fname = fm.group(1) if fm else f"india_a04_nada_{cid}_{d_i}{ext}"
            fname = re.sub(r"[^A-Za-z0-9._-]+", "_", fname)
            outp = os.path.join(CDIR, f"nada_{cid}_{fname}")
            open(outp, "wb").write(dr.content)
            print(f"    [OK] Downloaded {os.path.basename(outp)} ({len(dr.content):,} B)")
  except Exception as e:
    print(f"NADA {cid} err: {e}")

# 3. XRONOS exact endpoint test (country=PK etc. via /api/v1/data?country=...)
for cc in ["PK", "BD", "LK", "MV", "AF", "IR"]:
  dst = os.path.join(ARCH_DIR, f"xronos_{cc.lower()}.json")
  if os.path.exists(dst) and os.path.getsize(dst) > 100:
    continue
  for url in [
    f"https://xronos.ch/api/v1/data?country={cc}",
    f"https://xronos.ch/api/v1/data?country_code={cc}",
  ]:
    try:
      r = requests.get(url, headers=HDR, timeout=30)
      if r.ok and len(r.content) > 50:
        open(dst, "wb").write(r.content)
        print(f"  [OK] XRONOS {cc} ({url}): {len(r.content):,} B")
        break
    except Exception:
      pass
print("DONE!")
