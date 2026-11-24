# -*- coding: utf-8 -*-
"""Probes official open-data CKAN portals (datos.gob.do, one.gob.do, onei.gob.cu, stats.gov.gd) & GitHub for DOM DM pop, HND Aldeas pop, CUB Asentamientos pop, GRD villages."""
import json, re, ssl, urllib.request, urllib.parse

ctx = ssl._create_unverified_context()

def fetch_text(url, timeout=20):
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
  with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
    return r.read().decode("utf-8", errors="replace")

#1. Dominican Republic Open Data Portal (datos.gob.do CKAN) & ONE geoportal
print("=== 1. DATOS.GOB.DO (OFFICIAL DR OPEN DATA CKAN) ===")
for q in ("censo poblacion distrito municipal", "censo 2022 poblacion", "censo 2010 poblacion"):
  try:
    u = "https://datos.gob.do/api/3/action/package_search?" + urllib.parse.urlencode({"q": q, "rows": 5})
    d = json.loads(fetch_text(u))
    for pkg in d.get("result", {}).get("results", []):
      res = [(r.get("name"), r.get("format"), r.get("url")) for r in pkg.get("resources", []) if (r.get("format") or "").upper() in ("CSV", "XLSX", "XLS", "JSON", "GEOJSON")][:4]
      if res:
        print(f"  PKG: {pkg.get('title')}")
        for rn, rf, ru in res: print(f"    [{rf}] {rn}: {ru}")
  except Exception as e:
    print(f"  datos.gob.do ({q}): ERR {e}")

#2. ONEI Cuba Censo 2012 page
print("\n=== 2. ONEI CUBA ===")
for u in (
  "https://www.onei.gob.cu/publicaciones-tipo-anual/censo-de-poblacion-y-viviendas-2012",
  "https://www.onei.gob.cu/node/13815",
):
  try:
    t = fetch_text(u, timeout=20)
    links = re.findall(r'href=["\']([^"\']+\.(?:xlsx?|csv|pdf|zip))["\']', t, flags=re.I)
    print(f"  {u}: len={len(t)}, links={len(links)}, sample={links[:8]}")
  except Exception as e:
    print(f"  {u}: ERR {e}")

#3. GitHub API search for open CSV/JSON copies of official INE Honduras 2013 aldeas, ONE DR 2010/2022 distritos municipales, ONEI Cuba 2012 asentamientos
print("\n=== 3. GITHUB OPEN OFFICIAL CENSUS DATASETS ===")
for lbl, q in [
  ("DOM_DM_GH", "distritos municipales poblacion censo republica dominicana"),
  ("HND_ALD_GH", "honduras aldeas censo 2013 poblacion"),
  ("CUB_ASE_GH", "cuba asentamientos censo 2012 poblacion"),
  ("GRD_POP_GH", "grenada census 2011 population villages OR towns"),
]:
  try:
    u = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({"q": q, "per_page": 4})
    d = json.loads(fetch_text(u))
    print(f"  [{lbl}] total={d.get('total_count')}")
    for r in d.get("items", []):
      print(f"    {r.get('full_name')} ({r.get('stargazers_count')}*): {r.get('description')} -> {r.get('html_url')}")
  except Exception as e:
    print(f"  [{lbl}] ERR {e}")

#4. Check Grenada_Enumeration_Areas (agol_grd_ea.json) to see what town/community names or parish totals it has
import os
grd_fp = r"histmap/1.data_raw/population_regional/JAGUAR/_shared/settlement_sources/raw/nso_open_data/agol_grd_ea.json"
if os.path.exists(grd_fp):
  gd = json.load(open(grd_fp, encoding="utf-8"))
  print(f"\n=== 4. GRENADA EA SAMPLE ({len(gd)} rows) ===")
  for row in gd[:5]:
    print(" ", row)
