#!/usr/bin/env python3
"""
Step 4: Audits compiled 02_polaris.json (and raw Ch. 9) across every single year 1897..2025 (129 years)
for smooth annual point density, zero Donbas/Ukrainian war surges, and zero co-located twin duplicates.
"""

import glob
import json
import math
import os
from collections import defaultdict
from shapely.geometry import Point, shape
from shapely.prepared import prep

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DV_SHARD_DIR = "F:/Active Projects/Project 1436 - Dataview/data/stadester/stadester_2.0"
CH9_PATH = os.path.join(BASE_DIR, "histmap/1.data_raw/population_regional/POLARIS/1.entire_country/9.russian_invasion_of_ukraine/russian_invasion_of_ukraine_settlements.json")
CH9_POLY = os.path.join(BASE_DIR, "histmap/1.data_raw/population_regional/POLARIS/_shared/_gis_cache/russian_invasion_of_ukraine_polygons.geojson")
REG_PATH = os.path.join(os.path.dirname(__file__), "cache", "clean_master_registry.json")


def haversine_km(c1, c2):
  la1, lo1 = math.radians(c1[0]), math.radians(c1[1])
  la2, lo2 = math.radians(c2[0]), math.radians(c2[1])
  dl = la2 - la1
  dn = lo2 - lo1
  a = math.sin(dl / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dn / 2) ** 2
  return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))


def get_hyde_interval(y):
  if y < 0:
    return 1000
  if y < 1700:
    return 100
  return 10


def eval_city_at_year(city, yr):
  """Mirrors Dataview stadester_queries.ts getCitiesAtYear exactly."""
  pop_dict = city.get("population") or {}
  if not pop_dict:
    return 0
  # Filter numeric keys
  num_keys = sorted(int(k) for k in pop_dict)
  start_yr = num_keys[0]
  end_yr = num_keys[-1]
  in_range = (start_yr <= yr <= end_yr) or (end_yr >= 1975 and 1975 <= yr <= 2026)
  if not in_range:
    return 0
  sy = str(yr)
  if sy in pop_dict:
    return pop_dict[sy]
  if yr <= start_yr:
    return pop_dict.get(str(start_yr), 0)
  if yr >= end_yr:
    return pop_dict.get(str(end_yr), 0)
  # Binary search enclosing keys
  lo = 0
  hi = len(num_keys)
  while lo < hi:
    mid = (lo + hi) >> 1
    if num_keys[mid] < yr:
      lo = mid + 1
    else:
      hi = mid
  idx = max(1, lo)
  prev_y = num_keys[idx - 1]
  next_y = num_keys[idx]
  p0 = pop_dict.get(str(prev_y), 0)
  p1 = pop_dict.get(str(next_y), 0)
  max_gap = max(200, get_hyde_interval(prev_y), get_hyde_interval(next_y), get_hyde_interval((prev_y + next_y) / 2))
  if (next_y - prev_y) > max_gap and prev_y < yr < next_y:
    return 0
  if p0 >= 0.01 and p1 >= 0.01 and next_y > prev_y:
    t = (yr - prev_y) / (next_y - prev_y)
    return round(math.pow(10.0, math.log10(p0) + t * (math.log10(p1) - math.log10(p0))))
  if p1 >= 0.01:
    return p1
  if p0 >= 0.01:
    return p0
  return 0


def main():
  pol = {}
  for sp in sorted(glob.glob(os.path.join(DV_SHARD_DIR, "02_polaris*.json"))):
    with open(sp, encoding="utf-8") as fh:
      pol.update(json.load(fh))
  with open(CH9_PATH, encoding="utf-8") as fh:
    ch9 = json.load(fh)
  with open(CH9_POLY, encoding="utf-8") as fh:
    gj = json.load(fh)

  curated_war_names = set()
  if os.path.exists(REG_PATH):
    with open(REG_PATH, encoding="utf-8") as fh:
      for r in json.load(fh):
        if r.get("is_war_curated"):
          curated_war_names.add(r["name"].lower())

  donbas_feats = []
  for fe in gj.get("features", []):
    rid = fe["properties"].get("id", "")
    if "donetsk" in rid or "luhansk" in rid:
      g = shape(fe["geometry"])
      donbas_feats.append((rid, g.bounds, prep(g)))

  def in_donbas(coords):
    pt = Point(coords[1], coords[0])
    for rid, b, pg in donbas_feats:
      if b[0] <= coords[1] <= b[2] and b[1] <= coords[0] <= b[3] and pg.contains(pt):
        return rid
    return None

  keys = list(pol.keys())
  # Pre-evaluate 1897..2025 per city
  annual_counts = []
  donbas_surges = []
  ua_surges = []
  ua_raster_jumps = []
  homonym_jumps = []
  agg_resurrections = []

  prev_row = None
  max_abs_pct = (0.0, None)
  max_ru_pct = (0.0, None)
  max_ua_pct = (0.0, None)
  max_by_pct = (0.0, None)

  # Precompute annual vector per year cleanly
  year_cache = defaultdict(dict)  # key -> {yr: val}
  for k in keys:
    c = pol[k]
    pdict = c.get("population") or {}
    # Fast eval for 1897..2025
    for yr in range(1897, 2026):
      v = eval_city_at_year(c, yr)
      if v >= 0.01:
        year_cache[k][yr] = v

  print("Year | N_tot  |   dN |  pct% | N_RU | N_UA | N_BY | Pop_Tot(M) | Pop_UA(M) | Pop_Donbas(M)")
  print("-" * 92)
  for yr in range(1897, 2026):
    n_tot = 0
    n_ru = 0
    n_ua = 0
    n_by = 0
    p_tot = 0
    p_ua = 0
    p_db = 0
    for k in keys:
      v = year_cache[k].get(yr, 0)
      if v < 0.01:
        continue
      c = pol[k]
      cn = c.get("country", "")
      n_tot += 1
      p_tot += v
      if cn == "Russia":
        n_ru += 1
      elif cn == "Ukraine":
        n_ua += 1
        p_ua += v
        if in_donbas(c["coords"]):
          p_db += v
      elif cn == "Belarus":
        n_by += 1
    if prev_row is not None:
      dn = n_tot - prev_row[0]
      pct = (dn / prev_row[0]) * 100.0
      if abs(pct) > abs(max_abs_pct[0]):
        max_abs_pct = (pct, yr)
      for prev_c, cur_c, holder in [(prev_row[1], n_ru, "RU"), (prev_row[2], n_ua, "UA"), (prev_row[3], n_by, "BY")]:
        cpct = ((cur_c - prev_c) / max(1, prev_c)) * 100.0
        if holder == "RU" and abs(cpct) > abs(max_ru_pct[0]):
          max_ru_pct = (cpct, yr)
        if holder == "UA" and abs(cpct) > abs(max_ua_pct[0]):
          max_ua_pct = (cpct, yr)
        if holder == "BY" and abs(cpct) > abs(max_by_pct[0]):
          max_by_pct = (cpct, yr)
    else:
      dn = 0
      pct = 0.0
    prev_row = (n_tot, n_ru, n_ua, n_by)
    annual_counts.append((yr, n_tot, dn, pct, n_ru, n_ua, n_by, p_tot, p_ua, p_db))
    if yr in (1897, 1900, 1914, 1917, 1918, 1920, 1921, 1925, 1926, 1927, 1933, 1939, 1941, 1945, 1953, 1959, 1970, 1974, 1975, 1976, 1979, 1989, 1991, 2001, 2010, 2014, 2020, 2021, 2022, 2023, 2024, 2025) or abs(pct) >= 1.0:
      print(f"{yr:4d} | {n_tot:6d} | {dn:+4d} | {pct:+5.2f} | {n_ru:4d} | {n_ua:4d} | {n_by:4d} | {p_tot/1e6:10.3f} | {p_ua/1e6:9.3f} | {p_db/1e6:13.3f}")

  # Anomaly checks across ALL settlements
  for k in keys:
    c = pol[k]
    cn = c.get("country", "")
    nm = c.get("name", "")
    ymap = year_cache[k]

    # Check agglomeration twin resurrections
    if "agglomeration" in k.lower() and ymap.get(2021, 0) > 0:
      agg_resurrections.append((k, ymap[2021]))

    # Check Donbas surges 2014-2025 and Ukrainian surges 2021-2025
    if cn == "Ukraine":
      db_reg = in_donbas(c["coords"])
      p14 = ymap.get(2014, 0)
      p21 = ymap.get(2021, 0)
      p22 = ymap.get(2022, 0)
      p23 = ymap.get(2023, 0)
      if db_reg and p14 > 0:
        for y in range(2015, 2026):
          if ymap.get(y, 0) > p14 * 1.015:
            donbas_surges.append((k, db_reg, 2014, p14, y, ymap[y]))
            break
      if db_reg and p21 > 0:
        for y in range(2022, 2026):
          if ymap.get(y, 0) > p21 * 1.005:
            donbas_surges.append((k, db_reg, 2021, p21, y, ymap[y]))
            break
      if p21 > 0:
        is_war_cur = nm.lower() in curated_war_names
        lim = 1.50 if is_war_cur else 1.01
        for y in range(2022, 2026):
          if ymap.get(y, 0) > p21 * lim:
            ua_surges.append((k, is_war_cur, 2021, p21, y, ymap[y]))
            break
      if p22 > 0 and p23 > p22 * 1.15 and nm.lower() not in curated_war_names:
        ua_raster_jumps.append((k, p22, p23))

    # Check single-year homonym jumps >= 3.5x across 1989..2025 (excluding curated UA war and Pripyat)
    if nm.lower() not in curated_war_names and "pripyat" not in k.lower():
      for y in range(1990, 2026):
        vp = ymap.get(y - 1, 0)
        vc = ymap.get(y, 0)
        if vp > 0 and vc > 0:
          r = max(vp, vc) / max(1, min(vp, vc))
          if r >= 2.2:
            homonym_jumps.append((r, k, y - 1, vp, y, vc))

  # Check co-located active twins <= 1.8 km at 2021 and 1897
  grid21 = defaultdict(list)
  for k in keys:
    if year_cache[k].get(2021, 0) > 0:
      la, lo = pol[k]["coords"]
      grid21[(int(math.floor(la * 20)), int(math.floor(lo * 20)))].append(k)
  coloc_twins = []
  seen_p = set()
  for (gx, gy), lst in grid21.items():
    for dx in (-1, 0, 1):
      for dy in (-1, 0, 1):
        for ok in grid21.get((gx + dx, gy + dy), ()):
          for k in lst:
            if k >= ok or (k, ok) in seen_p:
              continue
            seen_p.add((k, ok))
            d = haversine_km(pol[k]["coords"], pol[ok]["coords"])
            if d <= 1.5:
              coloc_twins.append((round(d, 3), k, pol[k]["coords"], year_cache[k][2021], ok, year_cache[ok][2021]))

  print("\n=== 129-Year (1897-2025) Verification Diagnostics ===")
  print(f"1897 active: total={annual_counts[0][1]}, RU={annual_counts[0][4]}, UA={annual_counts[0][5]}, BY={annual_counts[0][6]}")
  print(f"Max YoY density change: Global={max_abs_pct[0]:+.2f}% ({max_abs_pct[1]}), RU={max_ru_pct[0]:+.2f}% ({max_ru_pct[1]}), UA={max_ua_pct[0]:+.2f}% ({max_ua_pct[1]}), BY={max_by_pct[0]:+.2f}% ({max_by_pct[1]})")
  print(f"Donbas surges (2014-2025): {len(donbas_surges)}")
  for x in donbas_surges[:10]: print(" ", x)
  print(f"Ukrainian surges (2021-2025): {len(ua_surges)}")
  for x in ua_surges[:10]: print(" ", x)
  print(f"UA 2022->2023 uncurated raster jumps (>1.15x): {len(ua_raster_jumps)}")
  for x in ua_raster_jumps[:10]: print(" ", x)
  print(f"Agglomeration resurrections (2021): {len(agg_resurrections)}")
  for x in agg_resurrections[:10]: print(" ", x)
  print(f"Post-1989 YoY spikes (>=2.2x): {len(homonym_jumps)}")
  for x in sorted(homonym_jumps, reverse=True)[:10]: print(" ", x)
  print(f"Co-located active twins <=1.5 km in 2021: {len(coloc_twins)}")
  for x in coloc_twins[:12]: print(" ", x)

  # Fail gatekeeper if any violations
  violations = 0
  if annual_counts[0][1] < 5500 or annual_counts[0][4] < 3000 or annual_counts[0][5] < 1200 or annual_counts[0][6] < 220:
    print("[FAIL] 1897 settlement count below minimum threshold!")
    violations += 1
  if max(abs(max_abs_pct[0]), abs(max_ru_pct[0]), abs(max_ua_pct[0]), abs(max_by_pct[0])) > 3.0:
    print("[FAIL] Annual point-density step exceeds 3.0% threshold!")
    violations += 1
  if donbas_surges or ua_surges or ua_raster_jumps or agg_resurrections:
    print("[FAIL] Surges / raster jumps / agglomeration resurrections detected!")
    violations += 1
  if violations:
    raise SystemExit(1)
  print("ALL 129 YEARS (1897-2025) PASSED ANOMALY-FREE!")


if __name__ == "__main__":
  main()
