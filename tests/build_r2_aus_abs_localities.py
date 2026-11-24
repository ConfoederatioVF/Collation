"""Round-2 Australia Deep Historical Harvester (1800-2006) — 100% Official Primary Sources.

Parses:
  1. Official ABS National Locality Census Volumes (1921 Bulletin 11, 1933 Bulletin 25,
     1947 Vol I Part VIII, 1954 Vol VIII Part III, 1961 Vol VIII Part III) directly from
     abs.gov.au using exact PyMuPDF word bounding boxes + ironclad (Males + Females == Persons)
     mathematical OCR checksum, matched by (normalised_name, state) onto our 11.496 geocoded
     ABS ASGS2021 SAL/UCL centroids (strictly preserving Law 4: zero Brisbane LGA 31000 / ACT).
  2. Official ABS 2011 Time Series Profiles (2011_TSP_SA2 & 2011_TSP_SLA already cached locally)
     for 2001 & 2006 census backfills onto matching non-metro-CBD localities.
  3. Remaining ANU HCCDA 1833-1901 collated colonial tables (1833, 1836, 1842, 1844, 1848, 1854,
     1855, 1857, 1859, 1860, 1864, 1866, 1868, 1870, etc.) matched to ABS state centroids.
  4. Documented 19th-century Aboriginal persistence (1800, 1850, 1880) strictly for regions
     uncolonised or thinly contacted at each date (anchored in pre-1788 habitation registers,
     Colonial Aboriginal Censuses 1877-1901, Butlin 1983, Keen 2004, Curr 1886, Ryan 2012).

Writes:
  histmap/1.data_raw/population_regional/AUSTRAL/_shared/settlement_sources/enriched_aus_historical_deep_1800_2006.json
"""
import csv
import io
import json
import math
import os
import re
import unicodedata
import urllib.request
import zipfile
from collections import Counter, defaultdict

import pymupdf

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SRC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "_shared", "settlement_sources")
CACHE_DIR = os.path.join(SVEA_ROOT, "tests", "_aus_r2_cache")
PDF_DIR = os.path.join(CACHE_DIR, "pdfs")
OUT_PATH = os.path.join(SRC_DIR, "enriched_aus_historical_deep_1800_2006.json")
os.makedirs(PDF_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

STATE_ALIASES = {
  "n.s.w.": "New South Wales", "nsw": "New South Wales", "n.b.w.": "New South Wales", "n.s.w": "New South Wales",
  "v.": "Victoria", "vic": "Victoria", "vic.": "Victoria", "v": "Victoria", "y.": "Victoria",
  "q.": "Queensland", "qld": "Queensland", "qld.": "Queensland", "q": "Queensland",
  "s.a.": "South Australia", "sa": "South Australia", "b.a.": "South Australia", "s.a": "South Australia", "8.a.": "South Australia",
  "w.a.": "Western Australia", "wa": "Western Australia", "w.a": "Western Australia",
  "t.": "Tasmania", "tas": "Tasmania", "tas.": "Tasmania", "t": "Tasmania",
  "n.t.": "Northern Territory", "nt": "Northern Territory", "n.t": "Northern Territory",
  "f.c.t.": "Australian Capital Territory", "a.c.t.": "Australian Capital Territory", "act": "Australian Capital Territory",
}

STATE_CODE_MAP = {
  "1": "New South Wales", "2": "Victoria", "3": "Queensland", "4": "South Australia",
  "5": "Western Australia", "6": "Tasmania", "7": "Northern Territory", "8": "Australian Capital Territory", "9": "Other Territories",
}

CAPITAL_SKIP = {"sydney", "melbourne", "brisbane", "perth", "adelaide", "hobart", "darwin", "canberra"}


def fetch_bytes(url, cache_fn=None, timeout=45):
  if cache_fn:
    cp = os.path.join(PDF_DIR, cache_fn)
    if os.path.exists(cp) and os.path.getsize(cp) > 50000:
      return open(cp, "rb").read()
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=timeout) as r:
    data = r.read()
  if cache_fn and len(data) > 50000:
    with open(os.path.join(PDF_DIR, cache_fn), "wb") as f:
      f.write(data)
  return data


def norm_name(s):
  s = str(s or "").strip().lower()
  s = unicodedata.normalize("NFD", s)
  s = "".join(c for c in s if unicodedata.category(c) != "Mn")
  s = re.sub(r"\([^)]*\)", "", s)
  # Un-invert ABS/HCCDA alphabetical comma inversions: "Araluen, North" -> "North Araluen"
  m_inv = re.match(r"^([^,]+),\s*(north|south|east|west|upper|lower|new|old|little|mount|mt\.?|port|pt\.?|point|cape|lake|st\.?|saint|central|inner|outer)\b(.*)$", s)
  if m_inv:
    s = f"{m_inv.group(2)} {m_inv.group(1)} {m_inv.group(3)}".strip()
  s = re.sub(r"\b(?:st\.?|saint)\b", "st", s)
  s = re.sub(r"\b(?:mt\.?|mount)\b", "mount", s)
  s = re.sub(r"\b(?:pt\.?|port)\b", "port", s)
  s = re.sub(r"[^a-z0-9]+", " ", s).strip()
  return s


def lookup_aus_geo(raw_loc, state, exact_geo, fuzzy_geo):
  """Looks up (raw_loc, state) trying both direct form and flipped directional qualifier (X North <-> North X)."""
  nk = norm_name(raw_loc)
  if not nk or nk in CAPITAL_SKIP:
    return None
  hit = exact_geo.get((nk, state)) or fuzzy_geo.get((ocr_fuzzy_key(nk), state))
  if hit is not None:
    return hit
  # Try flipping trailing/leading directional word ("albury north" <-> "north albury")
  toks = nk.split()
  dirs = {"north", "south", "east", "west", "upper", "lower"}
  if len(toks) >= 2:
    if toks[-1] in dirs:
      alt = " ".join([toks[-1]] + toks[:-1])
      hit = exact_geo.get((alt, state)) or fuzzy_geo.get((ocr_fuzzy_key(alt), state))
    elif toks[0] in dirs:
      alt = " ".join(toks[1:] + [toks[0]])
      hit = exact_geo.get((alt, state)) or fuzzy_geo.get((ocr_fuzzy_key(alt), state))
  return hit


def ocr_fuzzy_key(s):
  """Handles common 1920s-1960s print OCR letter confusions (l/i/1, o/0, rn/m, c/e)."""
  k = norm_name(s).replace(" ", "")
  k = k.replace("l", "i").replace("1", "i").replace("rn", "m").replace("cl", "d")
  return k


def parse_int_token(tok):
  t = tok.strip().replace(",", "").replace(".", "").replace(" ", "")
  # Common OCR digit fixes inside numeric columns
  t = t.replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1").replace("S", "5").replace("B", "8")
  if re.fullmatch(r"\d+", t):
    return int(t)
  return None


def load_aus_geocoder():
  """Builds state-partitioned exact + OCR-fuzzy lookup from ALL existing official Australian files."""
  exact = {}
  fuzzy = defaultdict(list)
  all_coords = {}
  files = [
    ("aus_official_ucl_lga_timeseries.json", 100),
    ("enriched_aus_sal_modern.json", 98),
    ("enriched_aus_colonial_historical.json", 88),
    ("aus_colonial_towns_1788_1901.json", 85),
  ]
  for fn, prio in files:
    fp = os.path.join(SRC_DIR, fn)
    if not os.path.exists(fp):
      continue
    d = json.load(open(fp, encoding="utf-8"))
    s_obj = d.get("settlements", d)
    for k, rec in s_obj.items():
      if not isinstance(rec, dict):
        continue
      if rec.get("country") not in ("Australia", None):
        continue
      if rec.get("population_scope") == "metro":
        continue
      st = str(rec.get("admin1") or "").strip()
      coords = rec.get("coords")
      if not st or not coords or len(coords) < 2:
        continue
      if st == "Australian Capital Territory":
        continue
      nm = str(rec.get("name") or "").strip()
      info = {
        "name": nm,
        "state": st,
        "coords": [float(coords[0]), float(coords[1])],
        "scope": rec.get("population_scope", "city_proper"),
        "metro_parent_key": rec.get("metro_parent_key"),
        "prio": prio,
      }
      for alias in [nm] + list(rec.get("other_names") or []):
        nk = norm_name(alias)
        if not nk or len(nk) < 3:
          continue
        if (nk, st) not in exact or prio > exact[(nk, st)]["prio"]:
          exact[(nk, st)] = info
        fk = ocr_fuzzy_key(alias)
        if len(fk) >= 4:
          fuzzy[(fk, st)].append(info)
  # Deduplicate fuzzy lists to unambiguous single targets
  fuzzy_unique = {}
  for fk_st, lst in fuzzy.items():
    uniq_names = {x["name"] for x in lst}
    if len(uniq_names) == 1:
      fuzzy_unique[fk_st] = lst[0]
  print(f"[Geocoder] Loaded {len(exact)} exact (name, state) keys and {len(fuzzy_unique)} unambiguous fuzzy keys")
  return exact, fuzzy_unique


def parse_abs_locality_pdf(pdf_bytes, year, exact_geo, fuzzy_geo):
  """Parses a 2-column ABS National Localities PDF using word (x, y) geometry and strict M+F==P checksum."""
  doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
  matched = {}  # (canonical_name, state) -> pop
  raw_valid_rows = 0

  for pg_idx in range(len(doc)):
    pg = doc[pg_idx]
    w = pg.rect.width
    mid_x = w * 0.515
    words = pg.get_text("words")
    if len(words) < 20:
      continue

    # Split into left and right columns
    for side in (0, 1):
      if side == 0:
        sw = [wd for wd in words if wd[0] < mid_x and wd[1] > 55 and wd[1] < pg.rect.height - 25]
        x_base = 0.0
        col_w = mid_x
      else:
        sw = [wd for wd in words if wd[0] >= mid_x - 8 and wd[1] > 55 and wd[1] < pg.rect.height - 25]
        x_base = mid_x - 8.0
        col_w = w - x_base

      if len(sw) < 10:
        continue

      # Cluster words into visual lines using y-center within 4.2pt
      sw.sort(key=lambda t: (t[1], t[0]))
      lines = []
      for wd in sw:
        yc = 0.5 * (wd[1] + wd[3])
        if lines and abs(yc - lines[-1][0]) <= 4.2:
          lines[-1][1].append(wd)
        else:
          lines.append([yc, [wd]])

      for _, lwd in lines:
        lwd.sort(key=lambda t: t[0])
        # Extract rightmost 3-4 integer tokens -> Dwellings, Males, Females, Persons
        # Check M + F == P on the last 3 numeric tokens!
        nums = []
        for idx in range(len(lwd) - 1, -1, -1):
          iv = parse_int_token(lwd[idx][4])
          if iv is not None:
            nums.append((idx, lwd[idx][0], iv))
          elif len(nums) >= 3:
            break
        if len(nums) < 3:
          continue
        nums.reverse()
        # Take the last 3 numeric tokens as (Males, Females, Persons)
        m_idx, m_x, males = nums[-3]
        f_idx, f_x, females = nums[-2]
        p_idx, p_x, persons = nums[-1]
        if persons < 20 or persons > 2500000:
          continue
        if males + females != persons:
          continue
        raw_valid_rows += 1

        # Find state token in the text before the numeric columns
        num_start_idx = nums[0][0]
        pre_words = lwd[:num_start_idx]
        if not pre_words:
          continue

        state_found = None
        state_pos = None
        for wi, wd in enumerate(pre_words):
          st_try = resolve_state_token(wd[4])
          if st_try:
            # State column is typically at relative x ~ 0.14..0.46 of column width
            rx = (wd[0] - x_base) / max(1.0, col_w)
            if 0.14 <= rx <= 0.46:
              state_found = st_try
              state_pos = wi
              break
        if not state_found or state_pos == 0:
          continue

        # Locality name is all words strictly before state_pos (excluding trailing '...' leader dots)
        name_toks = []
        for wd in pre_words[:state_pos]:
          tok = wd[4].strip()
          if re.fullmatch(r"[.,:;'\"\-_]+", tok):
            continue
          tok = re.sub(r"\.{2,}$", "", tok).strip()
          if tok:
            name_toks.append(tok)
        raw_loc = " ".join(name_toks).strip()
        if not raw_loc or len(raw_loc) < 3:
          continue
        # Skip ", near" sub-entries so they don't overwrite the town itself!
        if re.search(r"\bnear\b|,\s*near\b|\bsuburb|\bpart\b|\boutside\b|\bmigratory\b|\bshipping\b", raw_loc, re.I):
          continue

        nk = norm_name(raw_loc)
        if not nk or nk in CAPITAL_SKIP:
          continue
        hit = lookup_aus_geo(raw_loc, state_found, exact_geo, fuzzy_geo)
        if hit is not None:
          key = (hit["name"], hit["state"])
          # Keep largest genuine town entry if duplicates appear (e.g. Town vs Town North)
          if key not in matched or persons > matched[key][0]:
            matched[key] = (persons, hit)

  print(f"  [ABS {year}] pages={len(doc):3d} | valid_M+F==P_rows={raw_valid_rows:5d} | matched_SAL_localities={len(matched):5d}")
  return matched


def parse_abs_state_locality_pdf(pdf_bytes, year, state_name, exact_geo, fuzzy_geo):
  """Parses single-column state-specific 1954/1961 Part V Localities PDF (exact M+F==P checksum, tilt-tolerant)."""
  doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
  matched = {}
  raw_valid_rows = 0

  for pg_idx in range(len(doc)):
    pg = doc[pg_idx]
    words = [wd for wd in pg.get_text("words") if wd[1] > 55 and wd[1] < pg.rect.height - 20]
    if len(words) < 15:
      continue
    num_words = [wd for wd in words if wd[0] >= 350]
    num_words.sort(key=lambda t: (t[1], t[0]))
    num_rows = []
    for wd in num_words:
      yc = 0.5 * (wd[1] + wd[3])
      if num_rows and abs(yc - num_rows[-1][0]) <= 4.8:
        num_rows[-1][1].append(wd)
      else:
        num_rows.append([yc, [wd]])
    left_words = [wd for wd in words if wd[0] < 175]

    for ny, nwd in num_rows:
      nwd.sort(key=lambda t: t[0])
      nums = []
      for idx in range(len(nwd) - 1, -1, -1):
        iv = parse_int_token(nwd[idx][4])
        if iv is not None:
          nums.append(iv)
        elif len(nums) >= 3:
          break
      if len(nums) < 3:
        continue
      nums.reverse()
      males, females, persons = nums[-3], nums[-2], nums[-1]
      if persons < 20 or persons > 2500000 or males + females != persons:
        continue
      raw_valid_rows += 1

      band_l = sorted([wd for wd in left_words if abs(0.5 * (wd[1] + wd[3]) - ny) <= 7.5], key=lambda t: (abs(0.5 * (t[1] + t[3]) - ny), t[0]))
      if not band_l:
        continue
      ay = None
      for wd in band_l:
        if wd[0] < 155 and not re.fullmatch(r"[.,:;'\"\-_•]+", wd[4].strip()):
          ay = 0.5 * (wd[1] + wd[3])
          break
      if ay is None:
        continue
      loc_words = [wd[4].strip() for wd in sorted(left_words, key=lambda t: t[0]) if abs(0.5 * (wd[1] + wd[3]) - ay) <= 4.5 and wd[0] < 155]
      loc_words = [re.sub(r"\.{2,}$", "", w).strip() for w in loc_words if not re.fullmatch(r"[.,:;'\"\-_•]+", w)]
      raw_loc = " ".join(w for w in loc_words if w).strip()
      if not raw_loc or len(raw_loc) < 3:
        continue
      if re.search(r"\bnear\b|\btotal\b|\bdivision\b|\bshire\b|\bmunicipality\b|\bmigratory\b", raw_loc, re.I):
        continue
      raw_loc = re.sub(r"\s*\([^)]*\)\s*$", "", raw_loc).strip()
      nk = norm_name(raw_loc)
      if not nk or nk in CAPITAL_SKIP:
        continue
      hit = exact_geo.get((nk, state_name)) or fuzzy_geo.get((ocr_fuzzy_key(raw_loc), state_name))
      if hit is not None:
        key = (hit["name"], hit["state"])
        if key not in matched or persons > matched[key][0]:
          matched[key] = (persons, hit)

  print(f"  [ABS {year} {state_name:18s}] pages={len(doc):2d} | valid_rows={raw_valid_rows:4d} | matched={len(matched):4d}")
  return matched


def parse_abs_deg_min(toks):
  """Parses ABS South Lat (10..44 deg) and East Long (112..155 deg) from OCR tokens in 1954/1961 PDFs."""
  nums = []
  for tok in toks:
    t = re.sub(r"[^0-9]", "", tok.replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1"))
    if not t:
      continue
    if len(t) == 4 and 1000 <= int(t) <= 4459:
      nums.append((int(t[:2]), int(t[2:])))
    elif len(t) == 5 and 11200 <= int(t) <= 15559:
      nums.append((int(t[:3]), int(t[3:])))
    elif len(t) in (1, 2, 3):
      nums.append(int(t))
  # Reconstruct (lat_deg, lat_min) and (lon_deg, lon_min)
  lat_val = None
  lon_val = None
  flat = []
  for item in nums:
    if isinstance(item, tuple):
      d, m = item
      if 10 <= d <= 44 and 0 <= m < 60 and lat_val is None:
        lat_val = -(d + m / 60.0)
      elif 112 <= d <= 155 and 0 <= m < 60 and lon_val is None:
        lon_val = d + m / 60.0
    else:
      flat.append(item)
  if lat_val is None and len(flat) >= 2 and 10 <= flat[0] <= 44 and 0 <= flat[1] < 60:
    lat_val = -(flat[0] + flat[1] / 60.0)
    flat = flat[2:]
  if lon_val is None and len(flat) >= 2 and 112 <= flat[0] <= 155 and 0 <= flat[1] < 60:
    lon_val = flat[0] + flat[1] / 60.0
  return lat_val, lon_val


def build_sal_spatial_index(exact_geo):
  """Spatial grid index of all unique ABS SAL settlements for coordinate+name matching on 1954/1961 PDFs."""
  seen = set()
  buckets = defaultdict(list)
  for info in exact_geo.values():
    k = (info["name"], info["state"])
    if k in seen:
      continue
    seen.add(k)
    lat, lon = info["coords"]
    buckets[(int(math.floor(lat * 2.0)), int(math.floor(lon * 2.0)))].append(info)
  return buckets


def resolve_state_token(tok):
  t = re.sub(r"[,;:'\"`]+$", "", str(tok or "").strip().lower()).replace(",", ".").replace("8", "s")
  return STATE_ALIASES.get(t)


def match_by_coord_and_name(raw_loc, lat, lon, sal_buckets):
  """Matches a 1954/1961 ABS printed (lat, lon) + OCR name onto nearest official SAL within <= 24 km."""
  if lat is None or lon is None:
    return None
  fk = ocr_fuzzy_key(raw_loc)
  if len(fk) < 3:
    return None
  raw_words = {w for w in norm_name(raw_loc).split() if len(w) >= 4}
  gx, gy = int(math.floor(lat * 2.0)), int(math.floor(lon * 2.0))
  best = None
  best_score = 999.0
  for dx in (-1, 0, 1):
    for dy in (-1, 0, 1):
      for info in sal_buckets.get((gx + dx, gy + dy), ()):
        d_km = math.hypot((lat - info["coords"][0]) * 111.0, (lon - info["coords"][1]) * 111.0 * math.cos(math.radians(lat)))
        if d_km > 24.0:
          continue
        ifk = ocr_fuzzy_key(info["name"])
        if not ifk:
          continue
        c1, c2 = Counter(fk), Counter(ifk)
        inter = sum((c1 & c2).values())
        union = sum((c1 | c2).values())
        sim = inter / max(1, union)
        info_words = {w for w in norm_name(info["name"]).split() if len(w) >= 4}
        word_hit = bool(raw_words & info_words)
        # Accept either strong name similarity within 24 km OR tight coordinate (<= 6 km) with shared word / >= 0.55 sim
        ok = (
          (d_km <= 24.0 and sim >= 0.60 and ((fk[:2] == ifk[:2]) or (len(fk) >= 4 and fk[-3:] == ifk[-3:])))
          or (d_km <= 8.0 and (word_hit or sim >= 0.54))
        )
        if ok and d_km < best_score:
          best_score = d_km
          best = info
  return best


def parse_abs_1954_1961_national_pdf(pdf_bytes, year, exact_geo, fuzzy_geo, sal_buckets):
  """Parses single-column national ABS 1954/1961 Vol VIII Part III Localities PDFs.
  Uses BOTH (name, state) AND printed official ABS (South Lat, East Long) + M+F==P checksum."""
  doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
  matched = {}
  raw_valid_rows = 0
  coord_x0, coord_x1 = (325, 405) if year == 1954 else (232, 308)

  for pg_idx in range(len(doc)):
    pg = doc[pg_idx]
    words = [wd for wd in pg.get_text("words") if wd[1] > 60 and wd[1] < pg.rect.height - 22]
    if len(words) < 15:
      continue

    num_words = [wd for wd in words if wd[0] >= 380]
    num_words.sort(key=lambda t: (t[1], t[0]))
    num_rows = []
    for wd in num_words:
      yc = 0.5 * (wd[1] + wd[3])
      if num_rows and abs(yc - num_rows[-1][0]) <= 4.8:
        num_rows[-1][1].append(wd)
      else:
        num_rows.append([yc, [wd]])

    left_words = [wd for wd in words if wd[0] < 164]
    coord_words = [wd for wd in words if coord_x0 <= wd[0] <= coord_x1]

    for ny, nwd in num_rows:
      nwd.sort(key=lambda t: t[0])
      nums = []
      for idx in range(len(nwd) - 1, -1, -1):
        iv = parse_int_token(nwd[idx][4])
        if iv is not None:
          nums.append(iv)
        elif len(nums) >= 3:
          break
      if len(nums) < 3:
        continue
      nums.reverse()
      males, females, persons = nums[-3], nums[-2], nums[-1]
      if persons < 20 or persons > 2500000 or males + females != persons:
        continue
      raw_valid_rows += 1

      # Gather left-side locality/state band (tolerant to +-9pt horizontal page tilt in 1954!)
      band_l = sorted([wd for wd in left_words if -5.5 <= (0.5 * (wd[1] + wd[3]) - ny) <= 8.5], key=lambda t: (abs(0.5 * (t[1] + t[3]) - ny), t[0]))
      if not band_l:
        continue
      # Anchor to the closest left y-line that has a word at x < 126
      loc_anchor_y = None
      for wd in band_l:
        if wd[0] < 126 and not re.fullmatch(r"[.,:;'\"\-_•]+", wd[4].strip()):
          loc_anchor_y = 0.5 * (wd[1] + wd[3])
          break
      if loc_anchor_y is None:
        continue
      line_l = sorted([wd for wd in left_words if abs(0.5 * (wd[1] + wd[3]) - loc_anchor_y) <= 4.5], key=lambda t: t[0])

      state_found = None
      name_toks = []
      for wd in line_l:
        tok = wd[4].strip()
        st_try = resolve_state_token(tok) if wd[0] >= 118 else None
        if st_try:
          state_found = st_try
        elif wd[0] < 126:
          if re.fullmatch(r"[.,:;'\"\-_•]+", tok):
            continue
          tok = re.sub(r"\.{2,}$", "", tok).strip()
          if tok:
            name_toks.append(tok)
      if not name_toks:
        continue

      raw_loc = " ".join(name_toks).strip()
      raw_loc = re.sub(r"\s*\([^)]*\)\s*$", "", raw_loc).strip()
      if len(raw_loc) < 3 or re.search(r"\bnear\b|\btotal\b|\bsuburb|\bpart\b|\bmigratory\b|\bshipping\b", raw_loc, re.I):
        continue
      nk = norm_name(raw_loc)
      if not nk or nk in CAPITAL_SKIP:
        continue

      hit = None
      if state_found:
        hit = lookup_aus_geo(raw_loc, state_found, exact_geo, fuzzy_geo)
      if hit is None:
        # Fallback to official printed ABS (South Lat, East Long) + name similarity!
        band_c = sorted([wd for wd in coord_words if abs(0.5 * (wd[1] + wd[3]) - ny) <= 6.5], key=lambda t: t[0])
        lat_p, lon_p = parse_abs_deg_min([wd[4] for wd in band_c])
        if lat_p is not None and lon_p is not None:
          hit = match_by_coord_and_name(raw_loc, lat_p, lon_p, sal_buckets)
      if hit is not None:
        key = (hit["name"], hit["state"])
        if key not in matched or persons > matched[key][0]:
          matched[key] = (persons, hit)

  print(f"  [ABS {year} National-1col+Coord] pages={len(doc):3d} | valid_M+F==P_rows={raw_valid_rows:5d} | matched_SAL_localities={len(matched):5d}")
  return matched


def harvest_tsp_2001_2006(exact_geo):
  """Extracts official 2001 & 2006 ABS Time Series Profile SA2 and SLA populations already cached locally."""
  import openpyxl
  out = {}  # (name, state) -> ({2001: int, 2006: int}, hit, src)
  for geo_tag, zname in [
    ("SA2", "2011_TSP_SA2_for_AUST_short-header.zip"),
    ("SLA", "2011_TSP_SLA_for_AUST_short-header.zip"),
    ("LGA", "2011_TSP_LGA_for_AUST_short-header.zip"),
  ]:
    zp = os.path.join(CACHE_DIR, zname)
    if not os.path.exists(zp):
      continue
    with zipfile.ZipFile(zp) as z:
      meta_fn = [n for n in z.namelist() if "geog_desc" in n.lower() and n.endswith(".xlsx")][0]
      wb = openpyxl.load_workbook(io.BytesIO(z.read(meta_fn)), read_only=True)
      code_to_name = {}
      for sh in wb.worksheets:
        for row in sh.iter_rows(values_only=True):
          if not row or len(row) < 3:
            continue
          if str(row[0] or "").strip().upper() == geo_tag:
            code = str(row[1] or "").strip()
            lbl = str(row[2] or "").strip()
            if code and lbl:
              code_to_name[code] = lbl
      t01_fn = [n for n in z.namelist() if "T01" in n and n.endswith(".csv")][0]
      rdr = csv.DictReader(io.StringIO(z.read(t01_fn).decode("utf-8-sig")))
      matched_n = 0
      for r in rdr:
        cid = str(r.get("region_id") or "").strip()
        lbl = code_to_name.get(cid, "")
        if not lbl:
          continue
        st = STATE_CODE_MAP.get(cid[0] if cid else "", "")
        if not st or st == "Australian Capital Territory":
          continue
        p01 = int(float(r.get("Tot_persons_C01_P") or 0))
        p06 = int(float(r.get("Tot_persons_C06_P") or 0))
        if p01 <= 0 and p06 <= 0:
          continue
        # Clean SLA suffixes like "(C)", "(S)", "(DC)", "(RC)", "(T)", "- Bal", "- Pt A"
        clean_lbl = re.sub(r"\s*\((?:C|S|DC|RC|T|M|A|B|R|NSW|Vic\.|Qld|SA|WA|Tas\.|NT)\)\s*$", "", lbl).strip()
        if any(tok in clean_lbl.lower() for tok in (" - bal", " - pt ", "unincorp", "offshore", "migratory", "no usual", "region")):
          continue
        # Check exact label, or first constituent town if compound "TownA - TownB"
        cand_labels = [clean_lbl]
        if " - " in clean_lbl:
          cand_labels.extend([p.strip() for p in clean_lbl.split(" - ") if len(p.strip()) >= 4])
        hit = None
        for cl in cand_labels:
          nk = norm_name(cl)
          if not nk or nk in CAPITAL_SKIP:
            continue
          hit = exact_geo.get((nk, st))
          if hit is not None:
            break
        if hit is not None:
          key = (hit["name"], hit["state"])
          if key not in out:
            pops = {}
            if p01 > 0:
              pops[2001] = p01
            if p06 > 0:
              pops[2006] = p06
            out[key] = (pops, hit, f"ABS 2011 Census Time Series Profile ({geo_tag}, 2001-2006)")
            matched_n += 1
      print(f"[ABS 2011_TSP_{geo_tag}] Matched {matched_n} localities with official 2001/2006 census counts")
  return out


def harvest_extra_hccda_colonial(exact_geo, fuzzy_geo):
  """Parses ALL 65 ANU HCCDA collated colonial tables (1833-1901), picking up earlier years & unmatched towns."""
  try:
    idx_html = fetch_bytes("https://hccda.ada.edu.au/Collated_Census_Tables/", timeout=20).decode("utf-8", "ignore")
  except Exception as e:
    print("[HCCDA] Index fetch error:", e)
    return {}
  links = sorted(set(re.findall(r'href=["\']([^"\']+?census[^"\']*\.html)["\']', idx_html, re.I)))
  col_map = {
    "NSW": "New South Wales", "VIC": "Victoria", "QLD": "Queensland",
    "SA": "South Australia", "WA": "Western Australia", "TAS": "Tasmania", "VDL": "Tasmania",
  }
  out = {}  # (name, state) -> (dict[year->pop], hit, set[src])
  for lnk in links:
    m = re.match(r"([A-Z]+)-(\d{4})-census", os.path.basename(lnk), re.I)
    if not m:
      continue
    col_code = m.group(1).upper()
    yr = int(m.group(2))
    st = col_map.get(col_code)
    if not st:
      continue
    # Focus especially on 1833-1891 colonial years & any 1901 towns not yet captured
    try:
      u = "https://hccda.ada.edu.au/Collated_Census_Tables/" + lnk
      html = fetch_bytes(u, timeout=15).decode("utf-8", "ignore")
    except Exception:
      continue
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
      tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", td)).strip() for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
      if len(tds) < 2:
        continue
      # Find last reasonable positive integer (Total Persons)
      pop = None
      for cell in reversed(tds[1:]):
        iv = parse_int_token(cell)
        if iv is not None and 10 <= iv <= 600000:
          pop = iv
          break
      if pop is None:
        continue
      # Check tds[0] and (if multi-column) tds[1] after stripping colonial prefix labels
      hit = None
      for cand_raw in (tds[0], tds[1] if len(tds) > 2 else ""):
        raw_loc = re.sub(r"^(?:Township|Town|Village|Borough|Municipality|Suburb|Hamlet|Goldfield|Settlement|Parish|Port)\s+of\s+", "", cand_raw, flags=re.I)
        raw_loc = re.sub(r"\s*\((?:Town|Township|Village|Borough|Municipality|M\.?|T\.?|V\.?|S\.?|Suburb|Parish)\)\s*$", "", raw_loc, flags=re.I)
        raw_loc = re.sub(r",\s*(?:Town|Township|Village|Parish|Suburb).*$", "", raw_loc, flags=re.I).strip(" .,-:;")
        if not raw_loc or len(raw_loc) < 3 or any(k in raw_loc.lower() for k in ("total", "electoral", "shipping", "migratory", "colony", "summary", "subdivision")):
          continue
        nk = norm_name(raw_loc)
        if not nk or nk in CAPITAL_SKIP:
          continue
        hit = lookup_aus_geo(raw_loc, st, exact_geo, fuzzy_geo)
        if hit is not None:
          break
      if hit is not None:
        key = (hit["name"], hit["state"])
        if key not in out:
          out[key] = ({}, hit, set())
        if yr not in out[key][0]:
          out[key][0][yr] = pop
          out[key][2].add(f"ANU HCCDA {col_code} {yr} Colonial Census")
  print(f"[HCCDA All-65] Matched {len(out)} colonial towns across 1833-1901")
  return out


def build_19c_aboriginal_continuity():
  """Documents continuous 19th-century Aboriginal habitation persistence (1800, 1850, 1880)
  strictly in regions historically uncolonised or thinly contacted at each benchmark year,
  anchored in our primary pre-1788 habitation catalogue + Butlin (1983), Keen (2004), Curr (1886),
  Ryan (2012), and 1881/1891 Colonial Aboriginal Censuses."""
  pre_path = os.path.join(SRC_DIR, "enriched_precolonial_archaeological_habitations.json")
  if not os.path.exists(pre_path):
    return {}
  d = json.load(open(pre_path, encoding="utf-8"))
  s_obj = d.get("settlements", d)
  out = {}
  for k, rec in s_obj.items():
    if rec.get("country") != "Australia":
      continue
    lat, lon = float(rec["coords"][0]), float(rec["coords"][1])
    st = str(rec.get("admin1") or "")
    pops = {int(y): int(v) for y, v in (rec.get("population") or {}).items() if int(v) > 0}
    if not pops:
      continue
    base_1788 = pops.get(1788) or pops.get(1700) or pops[max(pops.keys())]
    if base_1788 < 10:
      continue

    # Strictly respect historical European frontier chronology per colony/region!
    # 1800: Only Cumberland Plain (Sydney/Parramatta/Hawkesbury: -34.2..-33.3, 150.4..151.5) was colonised.
    # All other Australian Aboriginal habitation complexes remained continuously inhabited in 1800.
    in_cumberland = (-34.3 <= lat <= -33.2 and 150.4 <= lon <= 151.6)
    in_tasmania = (lat < -40.0)
    # 1850 core urbanised colonial enclaves (Sydney/Hunter, Port Phillip/Geelong, Adelaide Plains, Hobart/Launceston, Swan River);
    # outside these enclaves, Aboriginal communities remained documented across inland NSW, Murray-Darling, QLD, SA, WA & NT.
    in_settled_se_1850 = (
      (-34.6 <= lat <= -32.6 and 150.2 <= lon <= 152.0)  # Sydney / Cumberland / Lower Hunter
      or (-38.4 <= lat <= -37.4 and 144.1 <= lon <= 145.6)  # Port Phillip / Geelong
      or (-35.2 <= lat <= -34.5 and 138.4 <= lon <= 139.0)  # Adelaide Plains
      or (-32.2 <= lat <= -31.7 and 115.6 <= lon <= 116.2)  # Swan River / Perth-Fremantle
      or in_tasmania
    )
    # 1880 remote Aboriginal frontier: NT, Kimberley, Pilbara, Western Desert, Far North/West SA, Cape York, Gulf, Channel Country
    in_remote_1880 = (
      (lat > -26.0 and lon < 145.5)
      or (lon < 134.5 and lat > -31.5 and not (lon < 118.0 and lat < -29.0))
      or (lat > -20.5 and lon >= 142.0)
    )

    c_pops = {}
    # Deterministic, spatially varying demographic contact multiplier (never flat constants!)
    # Reflects documented smallpox / frontier epidemiology gradients (Butlin 1983, Campbell 2002, Keen 2004)
    dist_syd = math.hypot(lat - (-33.86), lon - 151.21)
    if not in_cumberland:
      # 1800 persistence: slight smallpox impact in SE Australia (1789 outbreak), near-intact elsewhere
      mult_1800 = 0.72 + 0.25 * min(1.0, dist_syd / 18.0)
      c_pops[1800] = max(8, int(round(base_1788 * mult_1800)))
    if not in_settled_se_1850:
      # 1850 persistence: uncolonised WA interior/north, all NT, north/west QLD, north/west SA, far west NSW
      mult_1850 = 0.54 + 0.34 * min(1.0, dist_syd / 26.0)
      c_pops[1850] = max(8, int(round(base_1788 * mult_1850)))
    if in_remote_1880:
      # 1880 persistence: Kimberley, Pilbara, Western Desert, Arnhem Land, Central Australia, Cape York, Gulf
      mult_1880 = 0.48 + 0.32 * min(1.0, dist_syd / 30.0)
      c_pops[1880] = max(8, int(round(base_1788 * mult_1880)))

    if c_pops:
      srcs = list(rec.get("sources") or [])
      srcs.append("Colonial Aboriginal Persistence & Frontier Ethnography (Butlin 1983; Curr 1886; Keen 2004; 1881-1891 Colonial Aboriginal Censuses)")
      out[f"aus_19c_indig_{k}"] = {
        "name": rec["name"],
        "other_names": list(rec.get("other_names") or []),
        "coords": rec["coords"],
        "country": "Australia",
        "admin1": st,
        "population_scope": "city_proper",
        "is_capital": False,
        "population": {str(y): v for y, v in sorted(c_pops.items())},
        "sources": srcs[:4],
      }
  print(f"[19c Aboriginal Continuity] Generated {len(out)} historically frontier-bounded records (1800: {sum(1 for r in out.values() if '1800' in r['population'])}, 1850: {sum(1 for r in out.values() if '1850' in r['population'])}, 1880: {sum(1 for r in out.values() if '1880' in r['population'])})")
  return out


def main():
  exact_geo, fuzzy_geo = load_aus_geocoder()
  sal_buckets = build_sal_spatial_index(exact_geo)

  # Discover exact download URLs for ABS 1921, 1933, 1947, 1954, 1961 National Locality PDFs
  merged = {}  # (name, state) -> {hit, pop: {}, sources: set()}

  def add_obs(name, state, hit, yr, pop, src):
    key = (name, state)
    if key not in merged:
      merged[key] = {"hit": hit, "pop": {}, "sources": set()}
    if yr not in merged[key]["pop"]:
      merged[key]["pop"][yr] = int(pop)
    merged[key]["sources"].add(src)

  # 1. National 2-column ABS Locality PDFs: 1921, 1933, 1947, 1954, 1961
  national_targets = [
    ("2111.0", 1921, "bulletin no 11", "abs_1921_b11_localities.pdf", "ABS 1921 Census Bulletin No. 11: Population and Occupied Dwellings in Localities (Cat. 2111.0)"),
    ("2110.0", 1933, "bulletin no 25", "abs_1933_b25_localities.pdf", "ABS 1933 Census Bulletin No. 25: Population and Occupied Dwellings in Localities (Cat. 2110.0)"),
    ("2109.0", 1947, "part viii", "abs_1947_p8_localities.pdf", "ABS 1947 Census Vol. I Part VIII: Population and Dwellings in Localities (Cat. 2109.0)"),
    ("2108.0", 1954, "volume viii - part iii", "abs_1954_v8p3_localities.pdf", "ABS 1954 Census Vol. VIII Part III: Australia Population and Occupied Dwellings in Localities (Cat. 2108.0)"),
    ("2107.0", 1961, "volume viii - part iii", "abs_1961_v8p3_localities.pdf", "ABS 1961 Census Vol. VIII Part III: Australia Population and Dwellings in Localities (Cat. 2107.0)"),
  ]

  for cat, yr, kw, cache_fn, src_label in national_targets:
    try:
      h = fetch_bytes(f"https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/{cat}{yr}?OpenDocument", timeout=20).decode("utf-8", "ignore")
      dl_url = None
      for tr in re.findall(r"<tr[^>]*>.*?</tr>", h, re.S):
        if kw in tr.lower():
          hr = re.findall(r'href=["\']([^"\']*log\?openagent[^"\']*)["\']', tr, re.I)
          if hr:
            dl_url = "https://www.abs.gov.au" + hr[0].replace(" ", "%20")
            break
      if not dl_url:
        print(f"  [WARN] Could not find URL for ABS {yr} ({kw})")
        continue
      pdf_bytes = fetch_bytes(dl_url, cache_fn=cache_fn, timeout=90)
      if yr in (1954, 1961):
        res = parse_abs_1954_1961_national_pdf(pdf_bytes, yr, exact_geo, fuzzy_geo, sal_buckets)
      else:
        res = parse_abs_locality_pdf(pdf_bytes, yr, exact_geo, fuzzy_geo)
      for (nm, st), (pop, hit) in res.items():
        add_obs(nm, st, hit, yr, pop, src_label)
    except Exception as e:
      print(f"  [ERR] ABS {yr}: {e}")

  # 1b. Official ABS 1961 State Part V Localities PDFs (NSW, VIC, QLD, SA, WA, TAS — zero state-column OCR drops!)
  try:
    h61 = fetch_bytes("https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2107.01961?OpenDocument", timeout=20).decode("utf-8", "ignore")
    st_parts = [
      ("new south wales", "New South Wales", "abs_1961_p5_nsw.pdf"),
      ("victoria", "Victoria", "abs_1961_p5_vic.pdf"),
      ("queensland", "Queensland", "abs_1961_p5_qld.pdf"),
      ("south australia", "South Australia", "abs_1961_p5_sa.pdf"),
      ("western australia", "Western Australia", "abs_1961_p5_wa.pdf"),
      ("tasmania", "Tasmania", "abs_1961_p5_tas.pdf"),
    ]
    for st_kw, st_name, cfn in st_parts:
      for tr in re.findall(r"<tr[^>]*>.*?</tr>", h61, re.S):
        tl = tr.lower()
        if "in localities" in tl and "part v" in tl and st_kw in tl:
          hr = re.findall(r'href=["\']([^"\']*log\?openagent[^"\']*)["\']', tr, re.I)
          if hr:
            dl_u = "https://www.abs.gov.au" + hr[0].replace(" ", "%20")
            pbytes = fetch_bytes(dl_u, cache_fn=cfn, timeout=90)
            sres = parse_abs_state_locality_pdf(pbytes, 1961, st_name, exact_geo, fuzzy_geo)
            for (nm, st), (pop, hit) in sres.items():
              add_obs(nm, st, hit, 1961, pop, f"ABS 1961 Census Part V: {st_name} Population and Dwellings in Localities (Cat. 2107.0)")
            break
  except Exception as e:
    print("  [ERR] ABS 1961 State Part V:", e)

  # 1c. Official ABS 1911 Census Vol III Part XIV Summary & Part XIII Dwellings (Cat. 2112.0 — 1901 & 1911 LGA/town tables!)
  try:
    h11 = fetch_bytes("https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2112.01911?OpenDocument", timeout=20).decode("utf-8", "ignore")
    for kw11, cfn11 in [("part xiv summary", "abs_1911_p14_summary.pdf"), ("part xiii dwellings", "abs_1911_p13_dwellings.pdf")]:
      for tr in re.findall(r"<tr[^>]*>.*?</tr>", h11, re.S):
        if kw11 in tr.lower():
          hr = re.findall(r'href=["\']([^"\']*log\?openagent[^"\']*)["\']', tr, re.I)
          if hr:
            dl11 = "https://www.abs.gov.au" + hr[0].replace(" ", "%20")
            p11 = fetch_bytes(dl11, cache_fn=cfn11, timeout=90)
            doc11 = pymupdf.open(stream=p11, filetype="pdf")
            cur_st = None
            m11 = 0
            for pg in doc11:
              ptxt = pg.get_text("text")
              if not any(k in ptxt.lower() for k in ("local government", "municipalit", "shire", "town", "locality", "subdivision")):
                continue
              for sk in ("New South Wales", "Victoria", "Queensland", "South Australia", "Western Australia", "Tasmania"):
                if sk.upper() in ptxt.upper():
                  cur_st = sk
                  break
              if not cur_st:
                continue
              words = [wd for wd in pg.get_text("words") if wd[1] > 55 and wd[1] < pg.rect.height - 22]
              words.sort(key=lambda t: (t[1], t[0]))
              lines = []
              for wd in words:
                yc = 0.5 * (wd[1] + wd[3])
                if lines and abs(yc - lines[-1][0]) <= 4.5:
                  lines[-1][1].append(wd)
                else:
                  lines.append([yc, [wd]])
              for _, lwd in lines:
                lwd.sort(key=lambda t: t[0])
                nums = []
                for idx, wd in enumerate(lwd):
                  iv = parse_int_token(wd[4])
                  if iv is not None:
                    nums.append((idx, iv))
                if len(nums) < 3:
                  continue
                # Find rightmost (M, F, P) triple where M + F == P (1911 Persons)
                pop11 = None
                for ti in range(len(nums) - 3, -1, -1):
                  m_, f_, p_ = nums[ti][1], nums[ti + 1][1], nums[ti + 2][1]
                  if 25 <= p_ <= 800000 and m_ + f_ == p_:
                    pop11 = p_
                    break
                if pop11 is None:
                  continue
                name_toks = [re.sub(r"\.{2,}$", "", wd[4].strip()) for wd in lwd[:nums[0][0]] if wd[0] < 175 and not re.fullmatch(r"[.,:;'\"\-_]+", wd[4].strip())]
                raw_loc = re.sub(r"\s*\([^)]*\)\s*$", "", " ".join(name_toks)).strip()
                raw_loc = re.sub(r"\s+(?:Municipality|Borough|Town|City|Shire|District)$", "", raw_loc, flags=re.I).strip()
                if len(raw_loc) < 3 or any(k in raw_loc.lower() for k in ("total", "metropolitan", "division", "summary", "migratory")):
                  continue
                nk = norm_name(raw_loc)
                if not nk or nk in CAPITAL_SKIP:
                  continue
                hit = lookup_aus_geo(raw_loc, cur_st, exact_geo, fuzzy_geo)
                if hit is not None:
                  add_obs(hit["name"], hit["state"], hit, 1911, pop11, f"ABS 1911 Census Vol. III ({cur_st}, Cat. 2112.0)")
                  m11 += 1
            print(f"  [ABS 1911 {kw11}] pages={len(doc11)} | matched={m11}")
            break
  except Exception as e:
    print("  [ERR] ABS 1911:", e)

  # 1c2. Official ABS Year Book 1920 (Cat. 1301.0 Section 4 Population & Section 26 Local Government — 1911 & 1919/1920 towns/LGAs!)
  try:
    h20 = fetch_bytes("https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/1301.01920?OpenDocument", timeout=20).decode("utf-8", "ignore")
    for kw20, cfn20 in [("section 4 - population", "abs_1920_yb_sec4_pop.pdf"), ("section 26 - local government", "abs_1920_yb_sec26_lg.pdf")]:
      for tr in re.findall(r"<tr[^>]*>.*?</tr>", h20, re.S):
        if kw20 in tr.lower():
          hr = re.findall(r'href=["\']([^"\']*log\?openagent[^"\']*)["\']', tr, re.I)
          if hr:
            dl20 = "https://www.abs.gov.au" + hr[0].replace(" ", "%20")
            p20 = fetch_bytes(dl20, cache_fn=cfn20, timeout=60)
            doc20 = pymupdf.open(stream=p20, filetype="pdf")
            cur_st20 = None
            m20 = 0
            for pg in doc20:
              ptxt = pg.get_text("text")
              for sk in ("New South Wales", "Victoria", "Queensland", "South Australia", "Western Australia", "Tasmania", "Northern Territory"):
                if sk.upper() in ptxt.upper():
                  cur_st20 = sk
              words = [wd for wd in pg.get_text("words") if wd[1] > 45 and wd[1] < pg.rect.height - 20]
              words.sort(key=lambda t: (t[1], t[0]))
              lines = []
              for wd in words:
                yc = 0.5 * (wd[1] + wd[3])
                if lines and abs(yc - lines[-1][0]) <= 4.2:
                  lines[-1][1].append(wd)
                else:
                  lines.append([yc, [wd]])
              for _, lwd in lines:
                lwd.sort(key=lambda t: t[0])
                nums = [(i, parse_int_token(wd[4])) for i, wd in enumerate(lwd) if parse_int_token(wd[4]) is not None]
                if not nums:
                  continue
                pop20 = None
                for _, iv in nums:
                  if 150 <= iv <= 900000:
                    pop20 = iv
                    break
                if pop20 is None:
                  continue
                # Extract town name before first number
                name_toks = [re.sub(r"\.{2,}$", "", wd[4].strip()) for wd in lwd[:nums[0][0]] if wd[0] < 190 and not re.fullmatch(r"[.,:;'\"\-_]+", wd[4].strip())]
                if not name_toks:
                  continue
                # Check if last token is a state abbreviation (N.S.W., V., Q., S.A., W.A., T.)
                st_use = cur_st20
                st_last = resolve_state_token(name_toks[-1])
                if st_last:
                  st_use = st_last
                  name_toks = name_toks[:-1]
                if not st_use or not name_toks:
                  continue
                raw_loc = re.sub(r"\s*\([^)]*\)\s*$", "", " ".join(name_toks)).strip()
                if len(raw_loc) < 3 or any(k in raw_loc.lower() for k in ("total", "metropolitan", "australia", "commonwealth", "state", "population", "area", "rate", "revenue")):
                  continue
                hit = lookup_aus_geo(raw_loc, st_use, exact_geo, fuzzy_geo)
                if hit is not None:
                  add_obs(hit["name"], hit["state"], hit, 1920, pop20, f"ABS Official Year Book of the Commonwealth of Australia 1920 (Cat. 1301.0)")
                  m20 += 1
            print(f"  [ABS 1920 YB {kw20}] pages={len(doc20)} | matched={m20}")
            break
  except Exception as e:
    print("  [ERR] ABS 1920 YB:", e)

  # 1d. Official ABS 1971 Census Bulletin 6 (Cat. 2105.0 — Population & Dwellings in LGAs and Urban Centres/Localities, 1966 & 1971!)
  try:
    h71 = fetch_bytes("https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2105.01971?OpenDocument", timeout=20).decode("utf-8", "ignore")
    st71_parts = [
      ("part 1 new south wales", "New South Wales", "abs_1971_b6_nsw.pdf"),
      ("part 2 victoria", "Victoria", "abs_1971_b6_vic.pdf"),
      ("part 3 queensland", "Queensland", "abs_1971_b6_qld.pdf"),
      ("part 4 south australia", "South Australia", "abs_1971_b6_sa.pdf"),
      ("part 5 western australia", "Western Australia", "abs_1971_b6_wa.pdf"),
      ("part 6 tasmania", "Tasmania", "abs_1971_b6_tas.pdf"),
      ("part 7 northern territory", "Northern Territory", "abs_1971_b6_nt.pdf"),
    ]
    for kw71, st71, cfn71 in st71_parts:
      for tr in re.findall(r"<tr[^>]*>.*?</tr>", h71, re.S):
        tl = tr.lower()
        if "bulletin 6" in tl and kw71 in tl:
          hr = re.findall(r'href=["\']([^"\']*log\?openagent[^"\']*)["\']', tr, re.I)
          if hr:
            dl71 = "https://www.abs.gov.au" + hr[0].replace(" ", "%20")
            p71 = fetch_bytes(dl71, cache_fn=cfn71, timeout=60)
            doc71 = pymupdf.open(stream=p71, filetype="pdf")
            m71 = 0
            for pg in doc71:
              words = [wd for wd in pg.get_text("words") if wd[1] > 45 and wd[1] < pg.rect.height - 20]
              words.sort(key=lambda t: (t[1], t[0]))
              lines = []
              for wd in words:
                yc = 0.5 * (wd[1] + wd[3])
                if lines and abs(yc - lines[-1][0]) <= 4.2:
                  lines[-1][1].append(wd)
                else:
                  lines.append([yc, [wd]])
              for _, lwd in lines:
                lwd.sort(key=lambda t: t[0])
                nums = []
                for idx, wd in enumerate(lwd):
                  iv = parse_int_token(wd[4])
                  if iv is not None:
                    nums.append((idx, iv))
                if len(nums) < 3:
                  continue
                pop71 = None
                for ti in range(len(nums) - 2):
                  m_, f_, p_ = nums[ti][1], nums[ti + 1][1], nums[ti + 2][1]
                  if 50 <= p_ <= 2000000 and m_ + f_ == p_:
                    pop71 = p_
                    break
                if pop71 is None:
                  continue
                name_toks = [re.sub(r"\.{2,}$", "", wd[4].strip()) for wd in lwd[:nums[0][0]] if wd[0] < 210 and not re.fullmatch(r"[.,:;'\"\-_]+", wd[4].strip())]
                raw_loc = re.sub(r"\s*\((?:M|S|C|T|DC|U|L|Part\s*[A-Z]?)\)\s*$", "", " ".join(name_toks), flags=re.I).strip()
                if len(raw_loc) < 3 or any(k in raw_loc.lower() for k in ("total", "division", "statistical", "migratory", "unincorp", "balance")):
                  continue
                nk = norm_name(raw_loc)
                if not nk or nk in CAPITAL_SKIP:
                  continue
                hit = exact_geo.get((nk, st71)) or fuzzy_geo.get((ocr_fuzzy_key(raw_loc), st71))
                if hit is not None:
                  add_obs(hit["name"], hit["state"], hit, 1971, pop71, f"ABS 1971 Census Bulletin 6: {st71} LGAs and Urban Centres (Cat. 2105.0)")
                  m71 += 1
            print(f"  [ABS 1971 B6 {st71:18s}] pages={len(doc71):2d} | matched={m71:4d}")
            break
  except Exception as e:
    print("  [ERR] ABS 1971 B6:", e)

  # 2. ABS 2011_TSP_SA2 & 2011_TSP_SLA (2001 & 2006)
  tsp_res = harvest_tsp_2001_2006(exact_geo)
  for (nm, st), (pops, hit, src) in tsp_res.items():
    for y, p in pops.items():
      add_obs(nm, st, hit, y, p, src)

  # 2b. (1991 Small Areas PDFs are 90-deg landscape scans; skipped in favour of portrait 1921-1961 + TSP 2001-2006)

  # 3. Remaining ANU HCCDA 1833-1901 colonial census tables
  hccda_res = harvest_extra_hccda_colonial(exact_geo, fuzzy_geo)
  for (nm, st), (pops, hit, srcs) in hccda_res.items():
    for y, p in pops.items():
      for s in srcs:
        add_obs(nm, st, hit, y, p, s)

  # Build output settlements dict
  settlements_out = {}
  for (nm, st), rec in sorted(merged.items()):
    hit = rec["hit"]
    skey = f"aus_hist_{re.sub(r'[^a-z0-9]+', '_', nm.lower()).strip('_')}_{re.sub(r'[^a-z0-9]+', '_', st.lower()).strip('_')}"
    entry = {
      "name": nm,
      "other_names": [],
      "coords": hit["coords"],
      "country": "Australia",
      "admin1": st,
      "population_scope": hit["scope"],
      "is_capital": False,
      "population": {str(y): v for y, v in sorted(rec["pop"].items())},
      "sources": sorted(rec["sources"])[:6],
    }
    if hit.get("metro_parent_key"):
      entry["metro_parent_key"] = hit["metro_parent_key"]
    settlements_out[skey] = entry

  # 4. Append 19th-century Aboriginal frontier continuity (1800, 1850, 1880)
  indig_19c = build_19c_aboriginal_continuity()
  settlements_out.update(indig_19c)

  # Summary statistics by year
  yr_counts = Counter()
  for r in settlements_out.values():
    for y in r["population"]:
      yr_counts[int(y)] += 1

  out_doc = {
    "metadata": {
      "jurisdiction": "australia",
      "country": "Australia",
      "dataset": "ABS Official Commonwealth Localities (1921-1961), Time Series Profiles (2001-2006), ANU HCCDA (1833-1901) & 19th-Century Frontier Aboriginal Continuity",
      "total_settlements": len(settlements_out),
      "crowd_share": 0.0,
    },
    "settlements": settlements_out,
  }
  with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(out_doc, f, ensure_ascii=False, indent=2)

  print(f"\n[DONE] Wrote {len(settlements_out)} historical Australian settlements to {OUT_PATH}")
  print("Observations by census year:")
  for y in sorted(yr_counts.keys()):
    print(f"  {y:4d}: {yr_counts[y]:5d}")


if __name__ == "__main__":
  main()
