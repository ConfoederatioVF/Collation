"""MAGNETIC European Historical Settlement Chronology Baseline & Exhaustiveness Test Suite.

Establishes a peer-reviewed historical-demographic baseline for discrete European settlements
across the Operation Viscount MAGNETIC macro-region (~5,45M km², 40+ European countries/territories
west of POLARIS) from 10000 BC to 2025 AD, and validates BOTH the 21 chapter gazetteers and the
compiled Stadestér 2.0 `10_magnetic_*.json` shards against:
  1. Benchmark-year continental settlement floors (10000 BC – 2025 AD) anchored to:
     - Zimmermann et al. (2009) & Bocquet-Appel et al. (2005) Palaeolithic/Mesolithic C14 sites
     - Shennan (2013) & McEvedy & Jones (1978) Neolithic/Bronze Age settlements
     - Hansen & Nielsen (2004) Greek poleis, Hanson (2016) Roman cities, Pleiades & DARE
     - Darby (1977) / Open Domesday (1086 AD: 14.334 English places)
     - Ferdinand Lot (1929) / 1328 État des paroisses et des feux (~32.500 French parishes)
     - Keyser Deutsches Städtebuch (~3.500 chartered towns) & Viabundus (1350–1650: 18.839 nodes)
     - Bairoch et al. (1988), de Vries (1984), Buringh (2021), Malanima (2009), Dupâquier (1988)
     - INSEE France (1876–2023), ISTAT Italy, INE Spain, ONS UK BUA 2022, Eurostat GISCO LAU 2021
  2. Country-specific pre-1800 and modern coverage floors (explicitly auditing modern & historic
     France, Germany, United Kingdom, Italy, Spain, Portugal, East-Central Europe, and Balkans).
  3. Temporal smoothness / anti-cliff invariants (blocking artificial >1,35x vertical cliffs at
     1700 -> 1750 AD or 1750 -> 1800 AD).
  4. Anti-anachronism checks ensuring genuine post-1750 / post-1800 planned, polder, and industrial
     new towns (e.g. Wolfsburg, Gdynia, Lelystad, Almere, Milton Keynes, La Roche-sur-Yon, Latina,
     Middlesbrough, Eisenhüttenstadt) never appear before their historical foundation dates.
"""

import argparse
import glob
import json
import os
import sys
from collections import Counter

SVEA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC")
SHARD_DIR = os.path.join(SVEA_ROOT, "histmap", "3.data_transform", "population_Stadester.transform", "stadester")

# Scholarly baseline per benchmark year:
# (year, real_europe_est_low, real_europe_est_high, gazetteer_min_floor, historical_anchor_note)
CONTINENTAL_CHRONOLOGY_BASELINE = [
  (-10000,   1500,   4000,   650, "Late Glacial refugial macro-band camps (C14 attested)"),
  ( -8000,   3000,   7000,  1000, "Early Holocene Mesolithic base camps (C14 attested)"),
  ( -6000,   6000,  12000,  2400, "Early Neolithic tells & Mesolithic littoral sites"),
  ( -4000,  15000,  28000,  5200, "Middle/Late Neolithic LBK, Vinca & Alpine lake villages"),
  ( -2500,  22000,  40000,  7800, "Chalcolithic & Early Bronze Age villages/tells"),
  ( -1000,  25000,  45000,  8000, "Late Bronze Age Urnfield, Aegean & hillforts"),
  (  -500,  35000,  60000,  9000, "Classical Greek poleis (Hansen 2006) & La Tene oppida"),
  (     1,  55000,  85000, 10500, "Early Roman Empire civitates/vici (Hanson 2016, DARE, Pleiades)"),
  (   200,  60000,  90000, 10500, "High Imperial Roman urban peak & Barbaricum centres"),
  (   400,  50000,  75000, 10000, "Late Antiquity bishoprics, civitates & fortified oppida"),
  (   600,  40000,  65000,  9000, "Post-Roman ruralisation & early Merovingian/Slavic/Saxon seats"),
  (   800,  55000,  85000, 12000, "Carolingian villae/pagi, Viking emporia & Slavic grody"),
  (  1000,  80000, 120000, 22000, "Year 1000 boom: pre-Domesday vills, Capetian parishes, Ottonian Orte"),
  (  1100,  95000, 140000, 30000, "Open Domesday 1086 (14.3k English places) + High Mediaeval wave"),
  (  1200, 110000, 160000, 38000, "Ostsiedlung, bastides, borghi franchi & Magdeburg-law towns"),
  (  1300, 135000, 190000, 46000, "High Mediaeval apogee (1328 France 32.5k parishes, HRE Stadtebuch)"),
  (  1347, 135000, 190000, 48000, "Eve of the Black Death peak European settlement lattice"),
  (  1400, 120000, 170000, 45000, "Post-Black Death contraction (DMVs/Wustungen, ~90% lattice intact)"),
  (  1500, 130000, 185000, 54000, "Renaissance recovery + Viabundus (1350-1650) + Euratlas/Buringh"),
  (  1600, 140000, 195000, 60000, "Early Modern parish & market-town consolidation"),
  (  1700, 145000, 205000, 66000, "Late Ancien Regime cadastres (pre-industrial Europe)"),
  (  1750, 155000, 215000, 72000, "Proto-industrial take-off (smooth continuity from 1700 AD)"),
  (  1800, 160000, 225000, 78000, "First national censuses (France 1793/1801, UK 1801, Spain 1787)"),
  (  1900, 170000, 240000, 82000, "Industrial peak + comprehensive rural municipal censuses"),
  (  2020, 160000, 230000, 82000, "Contemporary Europe (LAU + INSEE peak>=500 + ISTAT + INE + ONS)"),
]

# Country / macro-zone minimum floors: (label, countries_tuple, {year: min_count})
REGIONAL_FLOORS = [
  ("France", ("France",), {1000: 4500, 1347: 13000, 1500: 16000, 1700: 19500, 1800: 21000, 2020: 21500}),
  ("United Kingdom", ("United Kingdom",), {1100: 7000, 1347: 7500, 1500: 7000, 1700: 7800, 2020: 5000}),
  ("Germany", ("Germany",), {1000: 2000, 1347: 6000, 1500: 7500, 1700: 8500, 2020: 8200}),
  ("Italy", ("Italy",), {1: 1400, 1000: 2200, 1347: 4800, 1500: 5800, 1700: 6500, 2020: 6600}),
  ("Iberia (ES+PT)", ("Spain", "Portugal"), {1: 1300, 1000: 1800, 1347: 4200, 1500: 5200, 1700: 6200, 2020: 6500}),
  ("East-Central Europe", ("Poland", "Czechia", "Czech Republic", "Slovakia", "Hungary", "Austria", "Switzerland"),
   {1000: 1500, 1347: 5500, 1500: 7500, 1700: 9500, 2020: 11500}),
  ("Balkans & Greece", ("Greece", "Romania", "Bulgaria", "Serbia", "Croatia", "Slovenia", "Bosnia and Herzegovina", "North Macedonia", "Albania", "Montenegro", "Kosovo", "Turkey-in-Europe"),
   {1: 1800, 1000: 1400, 1500: 3200, 1700: 4500, 2020: 6500}),
  ("Benelux & Ireland", ("Netherlands", "Belgium", "Luxembourg", "Ireland"),
   {1000: 700, 1347: 1800, 1500: 2200, 1700: 2600, 2020: 2900}),
  ("Nordics & Baltics", ("Denmark", "Sweden", "Norway", "Finland", "Iceland", "Greenland", "Faroe Islands", "Estonia", "Latvia", "Lithuania"),
   {1000: 1400, 1500: 2000, 1700: 2400, 2020: 2800}),
]

# Post-1750 / post-1800 genuine planned/industrial/polder new towns that MUST NOT appear pre-foundation:
# (exact_stem_lower, country, min_valid_year)
MODERN_NEW_TOWNS = [
  ("wolfsburg", "Germany", 1938),
  ("eisenhuttenstadt", "Germany", 1950),
  ("gdynia", "Poland", 1920),
  ("lelystad", "Netherlands", 1967),
  ("almere", "Netherlands", 1975),
  ("milton keynes", "United Kingdom", 1967),
  ("latina", "Italy", 1932),
  ("aprilia", "Italy", 1936),
  ("pomezia", "Italy", 1938),
  ("la roche-sur-yon", "France", 1804),
  ("middlesbrough", "United Kingdom", 1829),
  ("crewe", "United Kingdom", 1840),
  ("barrow-in-furness", "United Kingdom", 1846),
  ("salzgitter", "Germany", 1942),
]

# Maximum allowed step ratio between adjacent early-modern/modern benchmark years (prevents artificial cliffs!)
MAX_TRANSITION_RATIOS = [
  (1500, 1600, 1.35),
  (1600, 1700, 1.35),
  (1700, 1750, 1.35),
  (1750, 1800, 1.30),
  (1800, 1900, 1.25),
]


def load_settlements_from_chapters():
  """Loads and merges all 21 MAGNETIC chapter settlement JSONs by canonical key."""
  merged = {}
  for fp in sorted(glob.glob(os.path.join(MAG_DIR, "*", "*", "*_settlements.json"))):
    data = json.load(open(fp, encoding="utf-8"))
    for k, rec in data.items():
      if k not in merged:
        merged[k] = {
          "name": rec.get("name") or k,
          "country": rec.get("country") or "",
          "pop": {},
        }
      for yk, v in (rec.get("population") or {}).items():
        try:
          yi, fv = int(yk), float(v)
          if fv > 0:
            merged[k]["pop"][yi] = max(fv, merged[k]["pop"].get(yi, 0.0))
        except Exception:
          pass
  return merged


def load_settlements_from_shards():
  """Loads all compiled 10_magnetic_*.json Stadestér 2.0 shards."""
  merged = {}
  for fp in sorted(glob.glob(os.path.join(SHARD_DIR, "10_magnetic_*.json"))):
    data = json.load(open(fp, encoding="utf-8"))
    for k, rec in data.items():
      pop_i = {}
      for yk, v in (rec.get("population") or {}).items():
        try:
          yi, fv = int(yk), float(v)
          if fv > 0:
            pop_i[yi] = fv
        except Exception:
          pass
      if pop_i:
        merged[k] = {
          "name": rec.get("name") or k,
          "country": rec.get("country") or "",
          "pop": pop_i,
        }
  return merged


def evaluate_chronology(arg0_settlements, arg1_label):
  """Evaluates all continental, regional, smoothness and anti-anachronism invariants."""
  years = [row[0] for row in CONTINENTAL_CHRONOLOGY_BASELINE]
  yr_active = Counter()
  ctry_yr = {y: Counter() for y in years}
  anachronisms = []

  new_town_map = {(nm, ctry): min_y for nm, ctry, min_y in MODERN_NEW_TOWNS}

  for k, rec in arg0_settlements.items():
    pop = rec["pop"]
    if not pop:
      continue
    mn, mx = min(pop), max(pop)
    ctry = str(rec["country"] or "")
    nm_low = str(rec["name"] or "").strip().lower()
    nm_ascii = (
      nm_low.replace("ü", "u").replace("ö", "o").replace("ä", "a").replace("ß", "ss")
    )
    if (nm_ascii, ctry) in new_town_map:
      req_y = new_town_map[(nm_ascii, ctry)]
      if mn < req_y - 25:
        anachronisms.append(f"{k}: earliest={mn} < foundation={req_y}")

    for y in years:
      if mn <= y <= mx:
        yr_active[y] += 1
        ctry_yr[y][ctry] += 1

  failures = []
  print(f"\n=== MAGNETIC CHRONOLOGY VERIFICATION ({arg1_label}: {len(arg0_settlements):,} unique settlements) ===")
  print(f"{'Year':>7s} | {'Actual':>7s} | {'Floor':>7s} | {'Real Europe Est':>17s} | {'Status':>8s} | Historical Anchor")
  print("-" * 108)
  for y, est_lo, est_hi, floor, note in CONTINENTAL_CHRONOLOGY_BASELINE:
    act = yr_active[y]
    ok = act >= floor
    if not ok:
      failures.append(f"[CHRONOLOGY] Year {y}: {act:,} < floor {floor:,} ({note})")
    st = "PASS" if ok else "FAIL"
    print(f"{y:7d} | {act:7,d} | {floor:7,d} | {est_lo:7,d}-{est_hi:7,d} | {st:>8s} | {note}")

  print("\n=== REGIONAL & NATIONAL COVERAGE FLOORS ===")
  for label, ctrys, fl_map in REGIONAL_FLOORS:
    parts = []
    for y, fl in sorted(fl_map.items()):
      act = sum(ctry_yr[y][c] for c in ctrys)
      ok = act >= fl
      if not ok:
        failures.append(f"[REGIONAL] {label} @ {y}: {act:,} < floor {fl:,}")
      parts.append(f"{y}:{act:,}/{fl:,}{'' if ok else '!'}")
    print(f"  {label:22s}: " + " | ".join(parts))

  print("\n=== SMOOTHNESS / ANTI-CLIFF TRANSITION CHECKS ===")
  for y0, y1, max_r in MAX_TRANSITION_RATIOS:
    c0, c1 = max(1, yr_active[y0]), yr_active[y1]
    ratio = c1 / float(c0)
    ok = ratio <= max_r
    if not ok:
      failures.append(f"[CLIFF] {y0}->{y1} jump ratio {ratio:.2f}x > {max_r:.2f}x ({c0:,} -> {c1:,})")
    print(f"  {y0} -> {y1}: {c0:,} -> {c1:,} ({ratio:.2f}x, max {max_r:.2f}x) -> {'PASS' if ok else 'FAIL'}")

  print("\n=== POST-1750 NEW-TOWN ANTI-ANACHRONISM CHECKS ===")
  if anachronisms:
    for a in anachronisms:
      failures.append(f"[ANACHRONISM] {a}")
      print(f"  FAIL: {a}")
  else:
    print(f"  PASS: 0 anachronistic pre-foundation appearances across {len(MODERN_NEW_TOWNS)} post-1750 planned/industrial towns.")

  print(f"\nSUMMARY ({arg1_label}): {len(failures)} failure(s).")
  return failures


def main():
  parser = argparse.ArgumentParser(description="Verify MAGNETIC historical settlement chronology against European demographic baselines.")
  parser.add_argument("--source", choices=["chapters", "shards", "both"], default="both")
  args = parser.parse_args()

  all_failures = []
  if args.source in ("chapters", "both"):
    all_failures.extend(evaluate_chronology(load_settlements_from_chapters(), "21 CHAPTERS"))
  if args.source in ("shards", "both"):
    all_failures.extend(evaluate_chronology(load_settlements_from_shards(), "COMPILED SHARDS"))

  if all_failures:
    print("\nFAILURES DETECTED:")
    for f in all_failures[:40]:
      print("  -", f)
    sys.exit(1)
  print("\nALL CHRONOLOGY, REGIONAL, SMOOTHNESS & ANTI-ANACHRONISM CHECKS PASSED!")
  sys.exit(0)


if __name__ == "__main__":
  main()

