"""Audit Operation Viscount Project AUSTRAL settlement counts against peer-calibrated
benchmark-year and modern-jurisdiction quotas in `austral_enrichment_quotas.json5`."""
import json
import math
import os
import re
from collections import Counter, defaultdict

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
AUSTRAL_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL")
QUOTAS_PATH = os.path.join(AUSTRAL_DIR, "_shared", "austral_enrichment_quotas.json5")
MANIFEST_PATH = os.path.join(AUSTRAL_DIR, "austral_gazetteers.json5")


def load_json5(path):
  raw = open(path, encoding="utf-8").read()
  raw = re.sub(r"//.*", "", raw)
  raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
  raw = re.sub(r",(\s*[}\]])", r"\1", raw)
  raw = re.sub(r"(\{|,|\n)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
  return json.loads(raw)


def haversine_km(a1, o1, a2, o2):
  d1, d2 = math.radians(a2 - a1), math.radians(o2 - o1)
  x = math.sin(d1 / 2) ** 2 + math.cos(math.radians(a1)) * math.cos(math.radians(a2)) * math.sin(d2 / 2) ** 2
  return 6371.0 * 2.0 * math.atan2(math.sqrt(x), math.sqrt(max(0.0, 1.0 - x)))


def main():
  quotas = load_json5(QUOTAS_PATH)
  man = json.load(open(MANIFEST_PATH, encoding="utf-8"))

  # Deduplicate in descending priority order (3.modern -> 2.colonial -> 1.precolonial) so modern capitals
  # ALWAYS retain their canonical modern display names (never hijacked by nearby pre-colonial/archaeological points!)
  entities = []
  buckets = defaultdict(list)
  for g in sorted(man["gazetteers"], key=lambda x: -int(x.get("priority", 1))):
    gpath = os.path.join(SVEA_ROOT, g["path"])
    d = json.load(open(gpath, encoding="utf-8"))
    for _, v in d.items():
      lat, lon = float(v["coords"][0]), float(v["coords"][1])
      ctry = v["country"]
      scope = v.get("population_scope", "city_proper")
      nm = v["name"].lower().strip()
      pop = {int(y): float(p) for y, p in (v.get("population") or {}).items() if float(p) > 0}
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
            # Keep distinct modern Pacific island villages separate (0.30 km), while allowing cross-era
            # colonial/precolonial records (prio <= 2) to link to their modern village twin within 1.5 km!
            prio_cur = int(g.get("priority", 1))
            twin_km = 1.5 if (ctry in ("Australia", "New Zealand", "Papua New Guinea", "Indonesia") or prio_cur <= 2) else 0.30
            if dist <= twin_km or (dist <= 12.0 and e["nm"] == nm):
              hit = e
              break
          if hit:
            break
        if hit:
          break
      if hit:
        # Backfill only uncovered years so higher-priority modern/colonial census values win on overlap
        for yk, pv in pop.items():
          if yk not in hit["pop"]:
            hit["pop"][yk] = pv
      else:
        e = {
          "name": v["name"], "nm": nm, "country": ctry, "admin1": str(v.get("admin1") or ""),
          "lat": lat, "lon": lon, "scope": scope, "pop": dict(pop),
        }
        entities.append(e)
        buckets[(gx, gy)].append(e)

  tot_min = quotas["target_enriched_total_min"]
  print(f"UNIFIED DEDUPLICATED ENTITIES: {len(entities)} (quota min: {tot_min}) -> {'PASS' if len(entities) >= tot_min else 'SHORT'}")

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

  mel = {"Fiji", "Solomon Islands", "Vanuatu", "New Caledonia"}
  micpol = {
    "Federated States of Micronesia", "Marshall Islands", "Palau", "Guam",
    "Northern Mariana Islands", "Kiribati", "Nauru", "Samoa", "Tonga",
    "French Polynesia", "Cook Islands", "Tuvalu", "Niue", "Tokelau",
    "Wallis and Futuna", "Pitcairn Islands", "Chile",
  }
  jcnt = Counter()
  for e in entities:
    if max(e["pop"].keys()) < 2000:
      continue
    c = e["country"]
    if c in ("Australia", "Norfolk Island"):
      jcnt["australia"] += 1
    elif c == "New Zealand":
      jcnt["new_zealand"] += 1
    elif c == "Papua New Guinea":
      jcnt["papua_new_guinea"] += 1
    elif c == "Indonesia":
      jcnt["indonesian_papua"] += 1
    elif c in mel:
      jcnt["island_melanesia"] += 1
    elif c in micpol:
      jcnt["micronesia_and_polynesia"] += 1

  print("\n=== MODERN JURISDICTION QUOTAS (max_y >= 2000) ===")
  jur_short = []
  for jk, q in quotas["modern_jurisdiction_quotas"].items():
    n = jcnt[jk]
    ok = n >= q
    if not ok:
      jur_short.append((jk, q, n))
    print(f"{jk:26s} | quota={q:5d} | actual={n:6d} | {'PASS' if ok else 'SHORT by ' + str(q - n)}")

  print(f"\nSUMMARY: benchmark_shortfalls={len(shortfalls)}, jurisdiction_shortfalls={len(jur_short)}")

  # Write comprehensive per-country tail distribution & Law 4 snapshot for independent Hydrogen Auditor
  by_ctry = defaultdict(list)
  for e in entities:
    if max(e["pop"].keys()) >= 2000:
      lp = int(round(e["pop"][max(e["pop"].keys())]))
      by_ctry[e["country"]].append((lp, e["name"], e.get("admin1", ""), e["scope"]))

  ctry_stats = {}
  for c, lst in sorted(by_ctry.items(), key=lambda kv: -len(kv[1])):
    lst.sort()
    ps = [x[0] for x in lst]
    n = len(ps)
    ctry_stats[c] = {
      "modern_count": n,
      "min": ps[0],
      "p10": ps[n // 10],
      "p25": ps[n // 4],
      "median": ps[n // 2],
      "p75": ps[3 * n // 4],
      "p90": ps[min(n - 1, 9 * n // 10)],
      "max": ps[-1],
      "under_500": sum(1 for p in ps if p < 500),
      "under_1000": sum(1 for p in ps if p < 1000),
      "under_5000": sum(1 for p in ps if p < 5000),
      "smallest_5": [f"{x[1]} ({x[0]})" for x in lst[:5]],
      "largest_5": [f"{x[1]} ({x[0]})" for x in lst[-5:][::-1]],
    }

  bm_out = {}
  for y_str, q in quotas["benchmark_year_quotas"].items():
    Y = int(y_str)
    active = sum(1 for e in entities if min(e["pop"]) <= Y <= max(e["pop"]))
    carry = sum(1 for e in entities if (min(e["pop"]) <= Y <= max(e["pop"])) or (Y >= 2010 and max(e["pop"]) >= 2005 and min(e["pop"]) <= Y))
    bm_out[y_str] = {"quota": q, "active_span": active, "with_mod_carry": carry, "pass": carry >= q}

  mj_out = {jk: {"quota": q, "actual": jcnt[jk], "pass": jcnt[jk] >= q} for jk, q in quotas["modern_jurisdiction_quotas"].items()}

  # Full geographic boundary leak check: Hawai'i, American Samoa, US, MANDALA/Maluku/Aru/Kei/Tanimbar!
  geo_leaks = []
  for e in entities:
    c, la, lo = e["country"], e["lat"], e["lon"]
    if c in ("American Samoa", "United States", "Hawaii"):
      geo_leaks.append((e["name"], c, la, lo, "forbidden_country"))
    elif c == "Samoa" and lo > -171.25:
      geo_leaks.append((e["name"], c, la, lo, "american_samoa_longitude"))
    elif 18.0 <= la <= 29.0 and -179.0 <= lo <= -154.0:
      geo_leaks.append((e["name"], c, la, lo, "hawaii_bbox"))
    elif c == "Indonesia" and (lo < 129.0 or (la < -4.8 and lo < 135.2)):
      geo_leaks.append((e["name"], c, la, lo, "mandala_maluku_aru_kei_tanimbar"))

  # Explicit Law 4 Municipal-Limits Non-Decomposition verification block
  bris_inner = [e["name"] for e in entities if e["country"] == "Australia" and e["scope"] != "metro" and e["nm"] != "brisbane" and max(e["pop"]) >= 2000 and haversine_km(e["lat"], e["lon"], -27.4698, 153.0251) <= 10.0]
  act_inner = [e["name"] for e in entities if e["country"] == "Australia" and e["admin1"] == "Australian Capital Territory" and e["scope"] != "metro" and max(e["pop"]) >= 2000]
  akl_inner = [e["name"] for e in entities if e["country"] == "New Zealand" and e["scope"] != "metro" and e["nm"] != "auckland" and max(e["pop"]) >= 2000 and haversine_km(e["lat"], e["lon"], -36.8485, 174.7633) <= 15.0]
  pom_inner = [e["name"] for e in entities if e["country"] == "Papua New Guinea" and e["scope"] != "metro" and e["nm"] != "port moresby" and max(e["pop"]) >= 2000 and haversine_km(e["lat"], e["lon"], -9.4438, 147.1803) <= 10.0]
  jay_inner = [e["name"] for e in entities if e["country"] == "Indonesia" and e["scope"] != "metro" and e["nm"] != "jayapura" and max(e["pop"]) >= 2000 and haversine_km(e["lat"], e["lon"], -2.5337, 140.7181) <= 8.0]
  sor_inner = [e["name"] for e in entities if e["country"] == "Indonesia" and e["scope"] != "metro" and e["nm"] != "sorong" and max(e["pop"]) >= 2000 and haversine_km(e["lat"], e["lon"], -0.8762, 131.2558) <= 6.0]

  snap_path = os.path.join(AUSTRAL_DIR, "_shared", "austral_enrichment_audit_snapshot.json")
  with open(snap_path, "w", encoding="utf-8") as sf:
    json.dump({
      "total_unified_entities": len(entities),
      "quota_total_min": tot_min,
      "benchmark_shortfalls": len(shortfalls),
      "jurisdiction_shortfalls": len(jur_short),
      "geo_leaks_count": len(geo_leaks),
      "geo_leaks": geo_leaks[:20],
      "law4_verification": {
        "brisbane_inner_10km_count": len(bris_inner),
        "brisbane_inner_10km_sample": bris_inner[:10],
        "canberra_act_modern_entities": act_inner,
        "auckland_inner_15km_count": len(akl_inner),
        "auckland_inner_15km_sample": akl_inner[:10],
        "port_moresby_inner_10km_count": len(pom_inner),
        "jayapura_inner_8km_count": len(jay_inner),
        "sorong_inner_6km_count": len(sor_inner),
      },
      "modern_jurisdictions": mj_out,
      "benchmark_years": bm_out,
      "per_country_modern_distribution": ctry_stats,
    }, sf, ensure_ascii=False, indent=2)
  print(f"Wrote audit snapshot -> {snap_path} ({len(ctry_stats)} countries, geo_leaks={len(geo_leaks)})")


if __name__ == "__main__":
  main()
