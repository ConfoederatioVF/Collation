"""Downloads ARDECO NUTS-2/3 (1960-2025), INSEE 1876-2023 French historical communes,
and inspects Rosés-Wolf population sheets & Galloway Prussia POP*.XLS tables."""
import json
import os
import re
import urllib.request
import zipfile

HGIS = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MAGNETIC\_shared\subadmin_hgis\raw_sources"
UA = {"User-Agent": "Mozilla/5.0 (compatible; SVEA-Viscount-MAGNETIC/1.0)"}

def fetch(url, dest=None, timeout=120):
  req = urllib.request.Request(url, headers=UA)
  with urllib.request.urlopen(req, timeout=timeout) as r:
    data = r.read()
  if dest:
    with open(dest, "wb") as f:
      f.write(data)
  return data

# 1. ARDECO SNPTN (NUTS 2021, levels 2 & 3, 1960-2025)
ardeco_p = os.path.join(HGIS, "ardeco_snptn_nuts2021.csv")
if not os.path.isfile(ardeco_p):
  for ver in ("2021", "2024"):
    url = f"https://territorial.ec.europa.eu/ardeco-api-v2/rest/export/SNPTN?versions={ver}&unit=NR&level_id=0&level_id=1&level_id=2&level_id=3&format=csv-table"
    try:
      d = fetch(url, ardeco_p)
      print(f"[ARDECO {ver}] OK {len(d):,} B | head={d[:260].decode('utf-8','replace')}", flush=True)
      break
    except Exception as e:
      print(f"[ARDECO {ver}] ERR: {e}", flush=True)

# 2. INSEE 3698339 page -> find xlsx download URL
insee_p = os.path.join(HGIS, "insee_pop_hist_1876_2023.xlsx")
if not os.path.isfile(insee_p):
  try:
    html = fetch("https://www.insee.fr/fr/statistiques/3698339").decode("utf-8", errors="replace")
    links = re.findall(r'href=["\']([^"\']+\.(?:xlsx|zip))["\']', html, flags=re.I)
    print(f"[INSEE links] {links[:8]}", flush=True)
    for lk in links:
      if "1876" in lk or "pop" in lk.lower() or "hist" in lk.lower():
        full = lk if lk.startswith("http") else ("https://www.insee.fr" + lk)
        d = fetch(full, insee_p)
        print(f"[INSEE XLSX] OK {len(d):,} B from {full}", flush=True)
        break
  except Exception as e:
    print(f"[INSEE] ERR: {e}", flush=True)

# 3. Inspect Rosés-Wolf XLSX series & countries
import openpyxl
wb = openpyxl.load_workbook(os.path.join(HGIS, "roses_wolf_data.xlsx"), read_only=True)
ws = wb["Sheet1"]
series_counts = {}
pop_countries = set()
hdr = None
for idx, row in enumerate(ws.iter_rows(values_only=True)):
  if idx == 0:
    hdr = row
    continue
  s = str(row[0] or "")
  series_counts[s] = series_counts.get(s, 0) + 1
  if "pop" in s.lower():
    pop_countries.add(str(row[1] or ""))
print(f"[Rosés-Wolf] hdr={hdr}", flush=True)
for k, v in series_counts.items():
  print(f"  series: {k} -> {v} rows", flush=True)
print(f"  pop_countries ({len(pop_countries)}): {sorted(pop_countries)}", flush=True)

# 4. Inspect Galloway ZIP POP* files
with zipfile.ZipFile(os.path.join(HGIS, "Galloway_Prussia_Database_XLS.zip")) as zf:
  pop_files = [n for n in zf.namelist() if "POP" in n.upper() or "CODE" in n.upper() or "README" in n.upper() or "DOC" in n.upper()]
  print(f"[Galloway POP/CODE files] ({len(pop_files)}): {pop_files}", flush=True)
