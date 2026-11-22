"""Harvests France Ministere de la Culture Base Merimee (pipe-delimited POP S3)
and France INRAP National Preventive Archaeology Excavations CSV (Lambert-93 -> WGS84).
"""

import csv
import io
import json
import math
import os
import re
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional",
  "MAGNETIC", "_shared", "sites_magnetic_europe", "0.raw_data"
)
os.makedirs(RAW_DIR, exist_ok=True)
HEADERS = {"User-Agent": "SVEA-OperationViscount-MAGNETIC/1.0 (academic historical demography)"}


def lambert93_to_wgs84(arg0_x, arg1_y):
  """Exact analytical inverse projection from French RGF93 / Lambert-93 (EPSG:2154) to WGS84 (lat, lon)."""
  c = 11754255.426096
  e = 0.0818191910428158
  n = 0.725607765053267
  xs = 700000.0
  ys = 12655612.049876
  lon0 = math.radians(3.0)
  dx = arg0_x - xs
  dy = arg1_y - ys
  r = math.hypot(dx, dy)
  gamma = math.atan2(dx, -dy)
  lon = lon0 + gamma / n
  lat_iso = -(1.0 / n) * math.log(abs(r / c))
  # Iterate isometric latitude -> geodetic latitude
  lat = 2.0 * math.atan(math.exp(lat_iso)) - math.pi / 2.0
  for _ in range(7):
    esin = e * math.sin(lat)
    lat = 2.0 * math.atan(((1.0 + esin) / (1.0 - esin)) ** (e / 2.0) * math.exp(lat_iso)) - math.pi / 2.0
  return math.degrees(lat), math.degrees(lon)


def harvest_france_inrap():
  outp = os.path.join(RAW_DIR, "france_inrap_national.json")
  print("[1] Harvesting France INRAP National Preventive Excavations (Lambert-93 -> WGS84)...", flush=True)
  r = requests.get("https://static.data.gouv.fr/72/1f16b181f9711e5781ad01d9773d2de877051c1c5f68db2b4dfcd09e667e0c.csv", headers=HEADERS, timeout=90)
  if r.status_code != 200:
    print(f"  [WARN] INRAP status={r.status_code}", flush=True)
    return
  txt = r.content.decode("latin-1", errors="replace")
  rows = []
  reader = csv.reader(io.StringIO(txt), delimiter=";")
  header = next(reader, None)
  for cols in reader:
    if len(cols) < 10:
      continue
    try:
      x = float(cols[0].replace(",", "."))
      y = float(cols[1].replace(",", "."))
    except Exception:
      continue
    if not (50000 <= x <= 1300000 and 6000000 <= y <= 7200000):
      continue
    lat, lon = lambert93_to_wgs84(x, y)
    if 41.3 <= lat <= 51.2 and -5.2 <= lon <= 9.6:
      rows.append({
        "name": f"{cols[5]} ({cols[4]})"[:120],
        "period": cols[8][:140],
        "type": cols[9][:120],
        "lat": round(lat, 5),
        "lon": round(lon, 5),
      })
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  France INRAP national excavations: {len(rows):,}", flush=True)


def harvest_france_merimee():
  outp = os.path.join(RAW_DIR, "france_merimee_pop.json")
  print("[2] Harvesting France Base Merimee (pipe-delimited POP S3)...", flush=True)
  r = requests.get("https://ministere-culture.s3.sbg.io.cloud.ovh.net/POP/merimee.csv", headers=HEADERS, timeout=180)
  if r.status_code != 200:
    print(f"  [WARN] Merimee status={r.status_code}", flush=True)
    return
  txt = r.content.decode("utf-8", errors="replace")
  csv.field_size_limit(2_000_000)
  reader = csv.DictReader(io.StringIO(txt), delimiter="|")
  cols = reader.fieldnames or []
  coord_cols = [c for c in cols if c and ("coord" in c.lower() or "wgs" in c.lower())]
  print(f"    Merimee coord columns: {coord_cols}", flush=True)
  rows = []
  for row in reader:
    cval = ""
    for cc in coord_cols:
      if row.get(cc):
        cval = row.get(cc)
        break
    m = re.search(r"([45]\d\.\d+)[,\s;]+([\-]?\d+\.\d+)", str(cval))
    if not m:
      continue
    lat, lon = float(m.group(1)), float(m.group(2))
    if not (41.3 <= lat <= 51.2 and -5.2 <= lon <= 9.6):
      continue
    siecle = str(row.get("Siecle_de_la_campagne_principale_de_construction") or row.get("Datation_de_l_edifice") or "")
    tico = str(row.get("Titre_editorial_de_la_notice") or "")
    deno = str(row.get("Denomination_de_l_edifice") or "")
    s_low = f"{siecle} {tico} {deno}".lower()
    if any(k in s_low for k in ("20e", "21e", "xxe", "xxie", "190", "191", "192", "193", "194", "195", "196", "197", "198", "199")):
      if not any(k in s_low for k in ("néolith", "mégalith", "dolmen", "menhir", "gallo", "romain", "antique", "moyen âge", "méroving", "caroling", "11e", "12e", "13e", "14e", "15e", "16e", "17e", "18e", "protohist", "âge du", "paléolith")):
        continue
    rows.append({
      "name": tico[:120],
      "type": deno[:80],
      "period": siecle[:100],
      "lat": round(lat, 5),
      "lon": round(lon, 5),
    })
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  France Base Merimee pre-1870 monuments & arch sites: {len(rows):,}", flush=True)


if __name__ == "__main__":
  harvest_france_inrap()
  harvest_france_merimee()
  print("=== FRANCE HARVEST COMPLETE ===", flush=True)
