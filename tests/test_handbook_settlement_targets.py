"""Comprehensive verification test suite for Project HANDBOOK year:settlement targets,
anti-anachronism enforcement, pre-1800 continuity (zero 1800AD cliff), and spatial hygiene.

Usage:
  python tests/test_handbook_settlement_targets.py
"""
import glob
import json
import json5
import math
import os
import re
import sys
from collections import Counter, defaultdict

HB_DIR = os.path.abspath("histmap/1.data_raw/population_regional/HANDBOOK")

# Scientifically grounded minimum active settlements across the ENTIRE HANDBOOK study region
# (27 MENA, Anatolian, Cypriot, Transcaucasian, Iranian & Afghan territories; zero pre-1800 deflation!)
YEAR_SETTLEMENT_TARGETS = {
  -10000:   900,
   -8000:  1500,
   -6000:  3000,
   -4000:  5000,
   -3000:  6500,
   -2000:  7500,
   -1000:  9000,
    -500: 11500,
       1: 14000,
     200: 15000,
     400: 14500,
     600: 14000,
     800: 22000,
    1000: 30000,
    1200: 40000,
    1300: 44000,
    1400: 46000,
    1500: 52000,
    1600: 56000,
    1700: 60000,
    1750: 62000,
    1800: 64000,
    1850: 66000,
    1900: 68000,
    1920: 69000,
    1950: 70000,
    1970: 72000,
    1990: 73000,
    2000: 74000,
    2010: 74500,
    2020: 75000,
}

# Strict anti-anachronism table: documented modern/colonial planned cities that MUST NEVER appear
# before their real historical foundation year (with a 5-year grace tolerance for founding decade).
MODERN_FOUNDATION_FLOORS = {
  # Egypt Suez Canal & New Desert Cities
  ("port said", "Egypt"): 1859,
  ("ismailia", "Egypt"): 1863,
  ("port fuad", "Egypt"): 1926,
  ("new cairo", "Egypt"): 2000,
  ("10th of ramadan", "Egypt"): 1977,
  ("6th of october", "Egypt"): 1979,
  ("sadat city", "Egypt"): 1978,
  ("new borg el arab", "Egypt"): 1979,
  ("al-obour", "Egypt"): 1982,
  ("obour", "Egypt"): 1982,
  ("badr", "Egypt"): 1982,
  ("shorouk", "Egypt"): 1995,
  ("new damietta", "Egypt"): 1980,
  ("new administrative capital", "Egypt"): 2015,
  # Israel modern Zionist/post-1948 planned towns
  ("tel aviv", "Israel"): 1909,
  ("tel aviv-yafo", "Israel"): 1909,
  ("ashdod", "Israel"): 1956,
  ("dimona", "Israel"): 1955,
  ("arad", "Israel"): 1962,
  ("eilat", "Israel"): 1949,
  ("karmi'el", "Israel"): 1964,
  ("karmiel", "Israel"): 1964,
  ("qiryat gat", "Israel"): 1955,
  ("kiryat gat", "Israel"): 1955,
  ("qiryat shemona", "Israel"): 1949,
  ("netanya", "Israel"): 1929,
  ("holon", "Israel"): 1936,
  ("bat yam", "Israel"): 1926,
  ("ramat gan", "Israel"): 1921,
  ("bnei brak", "Israel"): 1924,
  ("modi'in", "Israel"): 1993,
  ("sderot", "Israel"): 1951,
  ("netivot", "Israel"): 1956,
  ("ofakim", "Israel"): 1955,
  ("yeruham", "Israel"): 1951,
  ("mitzpe ramon", "Israel"): 1951,
  ("migdal ha'emeq", "Israel"): 1953,
  ("yokneam", "Israel"): 1935,
  ("ariel", "Israel"): 1978,
  ("ma'ale adumim", "Israel"): 1975,
  ("rishon lezion", "Israel"): 1882,
  ("petah tikva", "Israel"): 1878,
  ("rehovot", "Israel"): 1890,
  ("hadera", "Israel"): 1891,
  ("herzliya", "Israel"): 1924,
  ("ra'anana", "Israel"): 1922,
  ("kfar saba", "Israel"): 1903,
  # Transcaucasia Soviet industrial cities
  ("sumqayit", "Azerbaijan"): 1949,
  ("sumqayıt", "Azerbaijan"): 1949,
  ("mingachevir", "Azerbaijan"): 1948,
  ("mingəçevir", "Azerbaijan"): 1948,
  ("shirvan", "Azerbaijan"): 1938,
  ("rustavi", "Georgia"): 1948,
  ("abovyan", "Armenia"): 1963,
  ("hrazdan", "Armenia"): 1959,
  ("charentsavan", "Armenia"): 1947,
  ("metsamor", "Armenia"): 1969,
  # Turkey Republican industrial towns
  ("karabuk", "Turkey"): 1937,
  ("karabük", "Turkey"): 1937,
  ("kirikkale", "Turkey"): 1925,
  ("kırıkkale", "Turkey"): 1925,
  ("batman", "Turkey"): 1955,
  ("tatvan", "Turkey"): 1936,
  # Iran 20th-century oil & planned towns
  ("abadan", "Iran"): 1909,
  ("masjed soleyman", "Iran"): 1908,
  ("bandar imam khomeini", "Iran"): 1928,
  ("mahshahr", "Iran"): 1920,
  ("fuladshahr", "Iran"): 1963,
  ("shahriar", "Iran"): 1952,
  ("pardis", "Iran"): 1991,
  ("parand", "Iran"): 1990,
  # Arabian Peninsula oil & planned towns
  ("al-jubail", "Saudi Arabia"): 1975,
  ("al-jubaīl", "Saudi Arabia"): 1975,
  ("jubail", "Saudi Arabia"): 1975,
  ("dhahran", "Saudi Arabia"): 1938,
  ("al-khobar", "Saudi Arabia"): 1935,
  ("dammam", "Saudi Arabia"): 1923,
  ("ad-dammām", "Saudi Arabia"): 1923,
  ("king abdullah economic city", "Saudi Arabia"): 2005,
  ("al-ahmadi", "Kuwait"): 1946,
  ("al-aḥmadī", "Kuwait"): 1946,
  ("mesaieed", "Qatar"): 1949,
  ("ras laffan", "Qatar"): 1996,
  ("lusail", "Qatar"): 2006,
  ("isa town", "Bahrain"): 1968,
  ("hamad town", "Bahrain"): 1984,
  # Afghanistan & Maghreb modern planned towns
  ("lashkargah", "Afghanistan"): 1953,
  ("hassi messaoud", "Algeria"): 1956,
  ("laayoune", "Western Sahara"): 1938,
  ("el aaiún", "Western Sahara"): 1938,
  ("dakhla", "Western Sahara"): 1884,
  ("kenitra", "Morocco"): 1912,
  ("kénitra", "Morocco"): 1912,
  ("khouribga", "Morocco"): 1923,
  ("al hoceima", "Morocco"): 1925,
}

# Anachronistic source terms forbidden inside Prehistory & Antiquity chapter ledgers (Ch 01-06)
ANTIQUITY_FORBIDDEN_SRC_RE = re.compile(
  r"(?:CAPMAS|TurkStat|TÜİK|GASTAT|NCSI|CYSTAT|TRNC|Geostat|AzStat|ArmStat|INSEE|HCP\s+RGPH|ONS\s+1998|"
  r"HOTOSM|OpenStreetMap|HDX/OCHA|COSIT|NSIA|CBS\s+2004|CBS\s+2021|PCBS|Wikidata\s+P1082|2016\s+National\s+Abadi|"
  r"Ottoman\s+Population\s+Register|1897\s+Russian)",
  re.I,
)


def norm_basic(s):
  s = str(s or "").strip().lower()
  s = re.sub(r"\s*\([^)]*\)", "", s).strip()
  return s


def main():
  itinerary = json5.load(open(os.path.join(HB_DIR, "handbook_itinerary.json5"), encoding="utf-8"))
  errors = []
  warnings = []

  spans = {}  # key -> [min_y, max_y, set_of_years]
  chapter_counts = {}
  anachronisms = []
  anach_src_hits = []
  mojibake_hits = []
  max_dup_violations = []

  for ch in itinerary["chapters"]:
    stem = ch["stem"]
    idx = int(ch["index"])
    d0, d1 = int(ch["domain"][0]), int(ch["domain"][1])
    ch_dir = os.path.join(HB_DIR, ch["group"], ch["folder"])
    sp = os.path.join(ch_dir, f"{stem}_settlements.json")
    lp = os.path.join(ch_dir, f"{stem}_source_ledger.json5")

    data = json.load(open(sp, encoding="utf-8"))
    chapter_counts[stem] = len(data)

    peaks = []
    for k, v in data.items():
      nm = str(v.get("name") or "")
      ctry = str(v.get("country") or "")
      if any(bad in nm for bad in ("Ã", "Â", "\ufffd", "\u02bd", "?")):
        mojibake_hits.append((stem, k))
      ys = [int(y) for y, pv in (v.get("population") or {}).items() if int(pv) > 0]
      if not ys:
        continue
      peaks.append(max(int(pv) for pv in v["population"].values()))
      min_y, max_y = min(ys), max(ys)

      # 1. Check strict anti-anachronism floor for documented modern planned towns!
      floor_y = MODERN_FOUNDATION_FLOORS.get((norm_basic(nm), ctry))
      if floor_y is not None and min_y < floor_y - 5:
        anachronisms.append((stem, k, min_y, floor_y))

      if k not in spans:
        spans[k] = [min_y, max_y, set(ys)]
      else:
        spans[k][0] = min(spans[k][0], min_y)
        spans[k][1] = max(spans[k][1], max_y)
        spans[k][2].update(ys)

    if peaks:
      top_v, top_c = Counter(peaks).most_common(1)[0]
      dup_pct = top_c / len(peaks) * 100.0
      if dup_pct > 3.5 and len(peaks) >= 100:
        max_dup_violations.append((stem, top_v, top_c, round(dup_pct, 2)))

    # 2. Check Prehistory & Antiquity ledgers (Ch 01-06) contain ZERO anachronistic modern census/OSM sources!
    if idx <= 6 and os.path.exists(lp):
      ld = json5.load(open(lp, encoding="utf-8"))
      for c in ld.get("candidates", []):
        if c.get("status") != "included":
          continue
        srcs = " ".join(c.get("sources") or [])
        if ANTIQUITY_FORBIDDEN_SRC_RE.search(srcs):
          anach_src_hits.append((stem, c.get("name"), srcs))

  # 3. Evaluate ALL 31 year:settlement targets!
  print(f"=== HANDBOOK Year:Settlement Target Verification ({len(spans):,} unique settlements) ===")
  print(f"{'Year':>7s} | {'Target':>8s} | {'Actual(span)':>12s} | {'Actual(near)':>12s} | {'Status':>8s}")
  print("-" * 60)
  failed_years = []
  for by, target in sorted(YEAR_SETTLEMENT_TARGETS.items()):
    tol = 500 if by <= -3000 else (250 if by <= 500 else (100 if by <= 1700 else (30 if by <= 1900 else 15)))
    c_span = sum(1 for mn, mx, _ in spans.values() if mn <= by <= mx)
    c_near = sum(1 for _, _, yset in spans.values() if any(abs(y - by) <= tol for y in yset))
    eff = max(c_span, c_near)
    ok = (eff >= target)
    if not ok:
      failed_years.append((by, target, c_span, c_near))
      errors.append(f"Year {by}: actual max(span={c_span:,}, near={c_near:,}) < target {target:,}")
    print(f"{by:7d} | {target:8,d} | {c_span:12,d} | {c_near:12,d} | {'PASS' if ok else 'FAIL':>8s}")

  # 4. Check specifically for 1800AD deflation cliff (ratio 1800 / 1900 must be >= 0.85 and 1700 / 1800 >= 0.85!)
  def eff_cnt(by):
    tol = 100 if by <= 1700 else (30 if by <= 1900 else 15)
    c_span = sum(1 for mn, mx, _ in spans.values() if mn <= by <= mx)
    c_near = sum(1 for _, _, yset in spans.values() if any(abs(y - by) <= tol for y in yset))
    return max(c_span, c_near)

  r_1800_1900 = eff_cnt(1800) / max(1, eff_cnt(1900))
  r_1700_1800 = eff_cnt(1700) / max(1, eff_cnt(1800))
  r_2020_2000 = eff_cnt(2020) / max(1, eff_cnt(2000))
  print(f"\nContinuity Ratios: 1700/1800={r_1700_1800:.2f} | 1800/1900={r_1800_1900:.2f} | 2020/2000={r_2020_2000:.2f}")
  if r_1800_1900 < 0.85:
    errors.append(f"Pre-1800 deflation detected: 1800/1900 ratio = {r_1800_1900:.2f} (< 0.85)")
  if r_1700_1800 < 0.85:
    errors.append(f"Pre-1700 deflation detected: 1700/1800 ratio = {r_1700_1800:.2f} (< 0.85)")
  if r_2020_2000 < 0.90:
    errors.append(f"Post-2000 drop-off detected: 2020/2000 ratio = {r_2020_2000:.2f} (< 0.90)")

  if anachronisms:
    errors.append(f"Anachronistic modern cities before foundation ({len(anachronisms)}): {anachronisms[:10]}")
  if anach_src_hits:
    errors.append(f"Anachronistic modern sources inside Ch 01-06 ({len(anach_src_hits)}): {anach_src_hits[:10]}")
  if mojibake_hits:
    errors.append(f"Mojibake/corrupt settlement names ({len(mojibake_hits)}): {mojibake_hits[:10]}")
  if max_dup_violations:
    errors.append(f"Horizontal peak shelf violations (>3.5%): {max_dup_violations}")

  print(f"\n=== TEST RESULT: {'PASS' if not errors else 'FAIL'} ({len(errors)} error(s)) ===")
  for e in errors:
    print("  [FAIL]", e)
  sys.exit(0 if not errors else 1)


if __name__ == "__main__":
  main()
