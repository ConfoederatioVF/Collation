"""Audit Operation Viscount Project NICETHI pre-modern (<1950AD) settlement counts
against the scholarly estimate series and peer-calibrated benchmark-year and
macro-subregion auditor targets in `nicethi_enrichment_quotas.json5`."""
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
NICETHI_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "NICETHI")
QUOTAS_PATH = os.path.join(NICETHI_DIR, "_shared", "nicethi_enrichment_quotas.json5")
MANIFEST_PATH = os.path.join(NICETHI_DIR, "nicethi_gazetteers.json5")

COUNTRY_TO_MACRO = {
  # West Africa Forest & Coast
  "Nigeria": "west_africa_forest_coast",
  "Ghana": "west_africa_forest_coast",
  "Ivory Coast": "west_africa_forest_coast",
  "Benin": "west_africa_forest_coast",
  "Togo": "west_africa_forest_coast",
  "Guinea": "west_africa_forest_coast",
  "Sierra Leone": "west_africa_forest_coast",
  "Liberia": "west_africa_forest_coast",
  "Guinea-Bissau": "west_africa_forest_coast",
  "Gambia": "west_africa_forest_coast",
  # Sahel & Western Sudan
  "Senegal": "sahel_western_sudan",
  "Mali": "sahel_western_sudan",
  "Burkina Faso": "sahel_western_sudan",
  "Niger": "sahel_western_sudan",
  "Mauritania": "sahel_western_sudan",
  "Chad": "sahel_western_sudan",
  # Nubia, Sudan & Horn of Africa
  "Sudan": "nubia_sudan_horn",
  "South Sudan": "nubia_sudan_horn",
  "Ethiopia": "nubia_sudan_horn",
  "Eritrea": "nubia_sudan_horn",
  "Somalia": "nubia_sudan_horn",
  "Somaliland": "nubia_sudan_horn",
  "Djibouti": "nubia_sudan_horn",
  # Central Africa, Equatoria, Congo & Angola
  "Cameroon": "central_africa_congo_angola",
  "Central African Republic": "central_africa_congo_angola",
  "Equatorial Guinea": "central_africa_congo_angola",
  "Gabon": "central_africa_congo_angola",
  "Republic of the Congo": "central_africa_congo_angola",
  "Democratic Republic of the Congo": "central_africa_congo_angola",
  "Angola": "central_africa_congo_angola",
  "Sao Tome and Principe": "central_africa_congo_angola",
  # East Africa, Swahili Coast & Great Lakes
  "Kenya": "east_africa_swahili_great_lakes",
  "United Republic of Tanzania": "east_africa_swahili_great_lakes",
  "Uganda": "east_africa_swahili_great_lakes",
  "Rwanda": "east_africa_swahili_great_lakes",
  "Burundi": "east_africa_swahili_great_lakes",
  # Southern Africa, Madagascar & Ocean Islands
  "South Africa": "southern_africa_madagascar_islands",
  "Zimbabwe": "southern_africa_madagascar_islands",
  "Zambia": "southern_africa_madagascar_islands",
  "Malawi": "southern_africa_madagascar_islands",
  "Mozambique": "southern_africa_madagascar_islands",
  "Namibia": "southern_africa_madagascar_islands",
  "Botswana": "southern_africa_madagascar_islands",
  "Lesotho": "southern_africa_madagascar_islands",
  "eSwatini": "southern_africa_madagascar_islands",
  "Madagascar": "southern_africa_madagascar_islands",
  "Mauritius": "southern_africa_madagascar_islands",
  "Reunion": "southern_africa_madagascar_islands",
  "Comoros": "southern_africa_madagascar_islands",
  "Mayotte": "southern_africa_madagascar_islands",
  "Seychelles": "southern_africa_madagascar_islands",
  "Cabo Verde": "southern_africa_madagascar_islands",
  "Saint Helena": "southern_africa_madagascar_islands",
  "British Indian Ocean Territory": "southern_africa_madagascar_islands",
  "French Southern and Antarctic Lands": "southern_africa_madagascar_islands",
}


def load_json5(arg0_path):
  raw = open(arg0_path, encoding="utf-8").read()
  raw = re.sub(r"//.*", "", raw)
  raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
  raw = re.sub(r",(\s*[}\]])", r"\1", raw)
  raw = re.sub(r"(\{|,|\n)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
  return json.loads(raw)


def haversine_km(arg0_a1, arg1_o1, arg2_a2, arg3_o2):
  d1, d2 = math.radians(arg2_a2 - arg0_a1), math.radians(arg3_o2 - arg1_o1)
  x = (
    math.sin(d1 / 2.0) ** 2
    + math.cos(math.radians(arg0_a1)) * math.cos(math.radians(arg2_a2)) * math.sin(d2 / 2.0) ** 2
  )
  return 6371.0 * 2.0 * math.atan2(math.sqrt(x), math.sqrt(max(0.0, 1.0 - x)))


def main():
  quotas = load_json5(QUOTAS_PATH)
  man = load_json5(MANIFEST_PATH)

  entities = []
  buckets = defaultdict(list)
  for g in man.get("gazetteers") or []:
    rel_p = g.get("path") or ""
    if not rel_p:
      continue
    gpath = rel_p if os.path.isabs(rel_p) else os.path.join(SVEA_ROOT, rel_p)
    if not os.path.exists(gpath):
      continue
    d = json.load(open(gpath, encoding="utf-8"))
    items = d.values() if isinstance(d, dict) else d
    for v in items:
      if not isinstance(v, dict) or not v.get("coords"):
        continue
      lat, lon = float(v["coords"][0]), float(v["coords"][1])
      ctry = str(v.get("country") or "").strip()
      scope = v.get("population_scope", "city_proper")
      nm = str(v.get("name") or "").lower().strip()
      pop = {}
      for y, p in (v.get("population") or {}).items():
        try:
          fp = float(p)
          if fp > 0:
            pop[int(float(str(y).split(".")[0]))] = fp
        except Exception:
          pass
      if not pop:
        continue
      gx, gy = int(math.floor(lat * 4)), int(math.floor(lon * 4))
      hit = None
      for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
          for e in buckets.get((gx + dx, gy + dy), ()):
            if e["country"] != ctry:
              continue
            if (scope == "metro") != (e["scope"] == "metro"):
              continue
            dist = haversine_km(lat, lon, e["lat"], e["lon"])
            if dist <= 1.5 or (dist <= 15.0 and e["nm"] == nm):
              hit = e
              break
          if hit:
            break
        if hit:
          break
      if hit:
        hit["pop"].update(pop)
      else:
        e = {"name": v.get("name", ""), "nm": nm, "country": ctry, "lat": lat, "lon": lon, "scope": scope, "pop": dict(pop)}
        entities.append(e)
        buckets[(gx, gy)].append(e)

  pre50_entities = [e for e in entities if min(e["pop"].keys()) < 1950]
  tot_min = quotas["target_unified_total_min"]
  pre_min = quotas["target_pre1950_unique_min"]
  print(f"UNIFIED DEDUPLICATED ENTITIES : {len(entities):6d} (min {tot_min:5d}) -> {'PASS' if len(entities) >= tot_min else 'SHORT by ' + str(tot_min - len(entities))}")
  print(f"UNIQUE PRE-1950 ENTITIES      : {len(pre50_entities):6d} (min {pre_min:5d}) -> {'PASS' if len(pre50_entities) >= pre_min else 'SHORT by ' + str(pre_min - len(pre50_entities))}")

  est_b = (quotas.get("estimated_historical_settlements_series") or {}).get("benchmarks") or {}
  print("\n=== PRE-MODERN BENCHMARK YEAR AUDITOR TARGETS ===")
  print(f"{'Year':>6} | {'EstTotal':>8} | {'Target':>6} | {'ActiveSpan':>10} | {'Direct+-25y':>11} | {'Recov%':>6} | Status")
  shortfalls = []
  for y_str, q in quotas["benchmark_year_quotas"].items():
    Y = int(y_str)
    active = 0
    direct25 = 0
    for e in entities:
      ys = e["pop"].keys()
      y0, y1 = min(ys), max(ys)
      if y0 <= Y <= y1:
        active += 1
      if any(abs(y - Y) <= 25 for y in ys):
        direct25 += 1
    est_tot = (est_b.get(y_str) or {}).get("estimated_total_settlements", 0)
    recov = (100.0 * active / est_tot) if est_tot > 0 else 0.0
    st = "PASS" if active >= q else f"SHORT by {q - active}"
    if active < q:
      shortfalls.append((Y, q, active))
    print(f"{Y:6d} | {est_tot:8d} | {q:6d} | {active:10d} | {direct25:11d} | {recov:5.2f}% | {st}")

  mcnt = Counter()
  for e in pre50_entities:
    mk = COUNTRY_TO_MACRO.get(e["country"], "unmapped")
    mcnt[mk] += 1

  print("\n=== PRE-1950 MACRO-SUBREGION AUDITOR TARGETS ===")
  sub_short = []
  for mk, q in quotas["pre1950_subregion_quotas"].items():
    n = mcnt[mk]
    ok = n >= q
    if not ok:
      sub_short.append((mk, q, n))
    print(f"{mk:36s} | target={q:5d} | actual={n:5d} | {'PASS' if ok else 'SHORT by ' + str(q - n)}")

  print(f"\nSUMMARY: benchmark_shortfalls={len(shortfalls)}, subregion_shortfalls={len(sub_short)}")
  sys.exit(0 if (not shortfalls and not sub_short and len(pre50_entities) >= pre_min) else 1)


if __name__ == "__main__":
  main()
