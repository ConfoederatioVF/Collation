"""Stage A & Stage C0: Builds the exact 4320x2160 MANDALA Domain Land Mask (Mainland & Maritime
South-East Asia strictly excluding West New Guinea: Indonesian Papua & Papua Barat) + micro-island
pinning + baseline c14_cleaned_dedup.csv density probe.
"""

import csv
import json
import os
import numpy as np
from PIL import Image
from shapely.geometry import Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MANDALA_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MANDALA")
CFG_DIR = os.path.join(MANDALA_DIR, "_shared", "sites_mandala_southeast_asia", "config")
JADE_GIS = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "_gis_cache")
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
C14_CSV = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_c14bazAAR", "c14_cleaned_dedup.csv")

os.makedirs(CFG_DIR, exist_ok=True)
GRID_W, GRID_H = 4320, 2160

MANDALA_COUNTRIES = {
  "Myanmar", "Thailand", "Laos", "Cambodia", "Vietnam",
  "Malaysia", "Singapore", "Brunei", "Indonesia", "Philippines", "East Timor"
}
EXCLUDED_ADM1 = {("Indonesia", "Papua"), ("Indonesia", "Papua Barat")}


def main():
  print("[1] Loading Natural Earth 10m Admin-1 polygons (excluding West New Guinea)...", flush=True)
  adm1_gj = json.load(open(os.path.join(JADE_GIS, "ne_10m_admin_1_states_provinces.geojson"), "r", encoding="utf-8"))
  geoms = []
  excluded_geoms = []
  by_country_cnt = {}
  for f in adm1_gj["features"]:
    p = f["properties"]
    c = p.get("admin") or p.get("geonunit")
    nm = p.get("name") or p.get("name_en")
    if c not in MANDALA_COUNTRIES:
      continue
    g = shape(f["geometry"]).buffer(0)
    if (c, nm) in EXCLUDED_ADM1:
      excluded_geoms.append(g)
      continue
    geoms.append(g)
    by_country_cnt[c] = by_country_cnt.get(c, 0) + 1

  mandala_union = unary_union(geoms).buffer(0)
  papua_union = unary_union(excluded_geoms).buffer(0) if excluded_geoms else None
  # Cleanly subtract any overlapping edge with West New Guinea
  if papua_union is not None:
    mandala_union = mandala_union.difference(papua_union).buffer(0)

  print(f"  Included Admin-1 counts: {by_country_cnt}", flush=True)
  minx, miny, maxx, maxy = mandala_union.bounds
  print(f"  MANDALA bounds: lon=[{minx:.2f}, {maxx:.2f}], lat=[{miny:.2f}, {maxy:.2f}]", flush=True)

  # Load HYDE land_area.png so coastal/micro-island land pixels align cleanly with SVEA 5-arcmin grid
  la_raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  land_area = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2])

  r0 = max(0, int((90.0 - maxy) * GRID_H / 180.0) - 2)
  r1 = min(GRID_H - 1, int((90.0 - miny) * GRID_H / 180.0) + 2)
  c0 = max(0, int((minx + 180.0) * GRID_W / 360.0) - 2)
  c1 = min(GRID_W - 1, int((maxx + 180.0) * GRID_W / 360.0) + 2)

  # Use a 0.04 deg (~4 km) coastal micro-island tolerance restricted to HYDE land_area > 0 (and outside Papua)
  prep_exact = prep(mandala_union)
  prep_buf = prep(mandala_union.buffer(0.055))
  prep_papua = prep(papua_union.buffer(0.02)) if papua_union is not None else None

  mask = np.zeros((GRID_H, GRID_W), dtype=bool)
  for rr in range(r0, r1 + 1):
    plat = 90.0 - (rr + 0.5) * 180.0 / GRID_H
    for cc in range(c0, c1 + 1):
      plon = -180.0 + (cc + 0.5) * 360.0 / GRID_W
      pt = Point(plon, plat)
      if prep_exact.contains(pt):
        mask[rr, cc] = True
      elif land_area[rr, cc] > 0 and prep_buf.contains(pt):
        if prep_papua is None or not prep_papua.contains(pt):
          mask[rr, cc] = True

  # Also explicitly pin critical micro-islands (Singapore, Ternate, Tidore, Banda, Ambon, Batanes, Corregidor, Labuan, Pulau Tioman, Phuket, Phu Quoc, Con Dao, Sabang, Simeulue, Enggano, Nias, Mentawai, Natuna, Anambas, Sangihe, Talaud, Kei, Tanimbar, Aru)
  micro_pins = [
    (1.352, 103.820), (0.790, 127.360), (0.680, 127.400), (-4.525, 129.895),
    (-3.695, 128.181), (20.448, 121.970), (5.283, 115.230), (2.790, 104.170),
    (7.880, 98.392), (10.227, 103.957), (8.685, 106.605), (5.893, 95.320),
    (3.960, 108.380), (3.210, 106.220), (3.550, 125.550), (4.250, 126.780),
    (-5.640, 132.750), (-7.980, 131.300), (-6.150, 134.250), (-8.556, 125.560)
  ]
  for la, lo in micro_pins:
    rr = min(GRID_H - 1, max(0, int((90.0 - la) * GRID_H / 180.0)))
    cc = min(GRID_W - 1, max(0, int((lo + 180.0) * GRID_W / 360.0)))
    mask[rr, cc] = True

  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  rgba[mask] = [255, 255, 255, 255]
  out_png = os.path.join(CFG_DIR, "mandala_domain_mask.png")
  Image.fromarray(rgba, mode="RGBA").save(out_png)
  px_cnt = int(mask.sum())
  area_km2 = int(round(float(land_area[mask].sum())))
  print(f"[2] Saved {out_png}: {px_cnt:,} land pixels (~{area_km2:,} km2)", flush=True)

  # Stage C0 baseline c14_cleaned_dedup.csv probe inside exact domain mask
  seen = set()
  c14_in = 0
  with open(C14_CSV, "r", encoding="utf-8", errors="replace") as fh:
    for row in csv.DictReader(fh):
      try:
        la = float(row.get("lat") or 0)
        lo = float(row.get("lon") or 0)
      except Exception:
        continue
      site = str(row.get("site") or "").strip().lower()
      k = (round(la, 3), round(lo, 3), site)
      if k in seen:
        continue
      seen.add(k)
      rr = min(GRID_H - 1, max(0, int((90.0 - la) * GRID_H / 180.0)))
      cc = min(GRID_W - 1, max(0, int((lo + 180.0) * GRID_W / 360.0)))
      if mask[rr, cc]:
        c14_in += 1
  print(f"[3] Stage C0 Baseline c14_cleaned_dedup.csv inside MANDALA mask: {c14_in} unique sites (2.5x anti-stub floor = {int(c14_in*2.5)})", flush=True)

  with open(os.path.join(CFG_DIR, "mandala_domain_summary.json"), "w", encoding="utf-8") as fh:
    json.dump({
      "project": "MANDALA",
      "pixel_count": px_cnt,
      "area_km2": area_km2,
      "excluded_adm1": [list(x) for x in EXCLUDED_ADM1],
      "c14_baseline_unique_sites": c14_in,
      "bounds_lon_lat": [round(minx, 3), round(miny, 3), round(maxx, 3), round(maxy, 3)]
    }, fh, indent=2)


if __name__ == "__main__":
  main()
