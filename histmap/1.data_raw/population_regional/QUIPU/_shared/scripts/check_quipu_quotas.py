"""Audit Operation Viscount Project QUIPU settlement counts against peer-calibrated
benchmark-year and modern-jurisdiction quotas in `quipu_enrichment_quotas.json5`."""
import json
import math
import os
import re
from collections import Counter, defaultdict

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
QUIPU_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "QUIPU")
QUOTAS_PATH = os.path.join(QUIPU_DIR, "_shared", "quipu_enrichment_quotas.json5")
MANIFEST_PATH = os.path.join(QUIPU_DIR, "quipu_gazetteers.json5")


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
  gaz_list = man.get("gazetteers") or man.get("chapters") or []
  for g in gaz_list:
    rel_p = g.get("path") or g.get("settlements_path") or ""
    if not rel_p:
      continue
    gpath = rel_p if os.path.isabs(rel_p) else os.path.join(SVEA_ROOT, rel_p)
    if not os.path.exists(gpath):
      gpath = os.path.join(QUIPU_DIR, rel_p)
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
            if dist <= 1.5 or (dist <= 12.0 and e["nm"] == nm):
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

  tot_min = quotas["target_enriched_total_min"]
  print(f"UNIFIED DEDUPLICATED ENTITIES: {len(entities)} (quota min: {tot_min}) -> {'PASS' if len(entities) >= tot_min else 'SHORT by ' + str(tot_min - len(entities))}")

  print("\n=== BENCHMARK YEAR QUOTAS ===")
  print(f"{'Year':>6} | {'Quota':>6} | {'ActiveSpan':>10} | {'WithModCarry':>12} | {'Direct+-10y':>11} | Status")
  shortfalls = []
  for y_str, q in quotas["benchmark_year_quotas"].items():
    Y = int(y_str)
    active = 0
    carry = 0
    direct10 = 0
    for e in entities:
      ys = e["pop"].keys()
      y0, y1 = min(ys), max(ys)
      if y0 <= Y <= y1:
        active += 1
      if (y0 <= Y <= y1) or (Y >= 2010 and y1 >= 2005 and y0 <= Y):
        carry += 1
      if any(abs(y - Y) <= 10 for y in ys):
        direct10 += 1
    st = "PASS" if carry >= q else f"SHORT by {q - carry}"
    if carry < q:
      shortfalls.append((Y, q, active, carry, direct10))
    print(f"{Y:6d} | {q:6d} | {active:10d} | {carry:12d} | {direct10:11d} | {st}")

  jcnt = Counter()
  for e in entities:
    if max(e["pop"].keys()) < 2000:
      continue
    c = e["country"]
    if c == "Colombia":
      jcnt["colombia"] += 1
    elif c == "Venezuela":
      jcnt["venezuela"] += 1
    elif c == "Ecuador":
      jcnt["ecuador"] += 1
    elif c == "Peru":
      jcnt["peru"] += 1
    elif c == "Bolivia":
      jcnt["andean_bolivia"] += 1
    elif c == "Chile":
      jcnt["chile"] += 1
    elif c == "Argentina":
      jcnt["argentina"] += 1
    elif c == "Uruguay":
      jcnt["uruguay"] += 1
    elif c in ("Falkland Islands", "South Georgia and the South Sandwich Islands"):
      jcnt["falklands_south_atlantic"] += 1

  print("\n=== MODERN JURISDICTION QUOTAS (max_y >= 2000) ===")
  jur_short = []
  for jk, q in quotas["modern_jurisdiction_quotas"].items():
    n = jcnt[jk]
    ok = n >= q
    if not ok:
      jur_short.append((jk, q, n))
    print(f"{jk:26s} | quota={q:5d} | actual={n:6d} | {'PASS' if ok else 'SHORT by ' + str(q - n)}")

  print(f"\nSUMMARY: benchmark_shortfalls={len(shortfalls)}, jurisdiction_shortfalls={len(jur_short)}")


if __name__ == "__main__":
  main()
