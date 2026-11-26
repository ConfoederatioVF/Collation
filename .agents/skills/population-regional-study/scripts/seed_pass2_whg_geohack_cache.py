#!/usr/bin/env python3
"""
Deterministic Pass-2 Gazetteer Pre-Seeder (0 LLM Agents, INV-09).

Populates `histmap/1.data_raw/population_regional/_shared/_gis_cache/whg_geohack_cache.json`
from:
  1. Bulk Wikidata SPARQL `P1448` official historical names (`P580` start time + `P625` coords)
  2. Pleiades places + `pleiades-names-latest.csv.gz` ancient/medieval attestations
  3. Local `wikidata_europe_attestations.json` and `mexico_ahl_historical_names.json`
  4. Local GeoNames `feature_class == 'P'` gazetteer dumps across `population_regional/`
"""

import csv
import gzip
import html
import io
import json
import math
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile

SVEA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
TOPO_DIR = os.path.join(SVEA_ROOT, "tests", "toponymy_batches")
POP_REG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional")
GIS_CACHE_DIR = os.path.join(POP_REG_DIR, "_shared", "_gis_cache")
CACHE_PATH = os.path.join(GIS_CACHE_DIR, "whg_geohack_cache.json")
WD_SPARQL_CACHE_PATH = os.path.join(GIS_CACHE_DIR, "wikidata_p1448_settlements.json")
PLEIADES_PLACES_PATH = os.path.join(POP_REG_DIR, "MAGNETIC", "_shared", "settlement_sources", "pleiades_places_latest.csv.gz")
PLEIADES_NAMES_PATH = os.path.join(GIS_CACHE_DIR, "pleiades_names_latest.csv.gz")
WD_EU_PATH = os.path.join(POP_REG_DIR, "MAGNETIC", "_shared", "settlement_sources", "wikidata_europe_attestations.json")
MEX_AHL_PATH = os.path.join(POP_REG_DIR, "JAGUAR", "_shared", "settlement_sources", "parsed", "mexico_ahl_historical_names.json")

USER_AGENT = "SVEA-Viscount-Pass2-Toponymy/3.0 (https://confoederatio.org; deterministic-seeder)"
NON_LATIN_RE = re.compile(r"[\u0370-\u03FF\u0400-\u04FF\u0530-\u058F\u0590-\u05FF\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u10A0-\u10FF\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]")
EXCEL_ERROR_RE = re.compile(r"#(?:N/A|REF!|VALUE!|DIV/0!|NAME\?|NUM!|NULL!)\b", re.IGNORECASE)
POINT_RE = re.compile(r"Point\(\s*([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)\s*\)", re.IGNORECASE)

CYRILLIC_MAP = {
  "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ё": "Yo", "Ж": "Zh", "З": "Z", "И": "I",
  "Й": "Y", "К": "K", "Л": "L", "М": "M", "Н": "N", "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T",
  "У": "U", "Ф": "F", "Х": "Kh", "Ц": "Ts", "Ч": "Ch", "Ш": "Sh", "Щ": "Shch", "Ъ": "", "Ы": "Y", "Ь": "",
  "Э": "E", "Ю": "Yu", "Я": "Ya", "І": "I", "Ї": "Yi", "Є": "Ye", "Ґ": "G", "Ў": "U",
  "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
  "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
  "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
  "э": "e", "ю": "yu", "я": "ya", "і": "i", "ї": "yi", "є": "ye", "ґ": "g", "ў": "u"
}

GREEK_MAP = {
  "Α": "A", "Β": "V", "Γ": "G", "Δ": "D", "Ε": "E", "Ζ": "Z", "Η": "I", "Θ": "Th", "Ι": "I", "Κ": "K",
  "Λ": "L", "Μ": "M", "Ν": "N", "Ξ": "X", "Ο": "O", "Π": "P", "Ρ": "R", "Σ": "S", "Τ": "T", "Υ": "Y",
  "Φ": "F", "Χ": "Ch", "Ψ": "Ps", "Ω": "O",
  "α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i", "θ": "th", "ι": "i", "κ": "k",
  "λ": "l", "μ": "m", "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t",
  "υ": "y", "φ": "f", "χ": "ch", "ψ": "ps", "ω": "o"
}


def haversine_km(arg0_lat1, arg1_lng1, arg2_lat2, arg3_lng2):
  """Computes great-circle distance in km."""
  r = 6371.0
  p1 = math.radians(arg0_lat1)
  p2 = math.radians(arg2_lat2)
  dp = math.radians(arg2_lat2 - arg0_lat1)
  dl = math.radians(arg3_lng2 - arg1_lng1)
  a = math.sin(dp/2.0)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2.0)**2
  #Return statement
  return 2.0*r*math.asin(min(1.0, math.sqrt(a)))


def clean_to_latin(arg0_raw):
  """Cleans HTML entities, parentheticals, Cyrillic/Greek, and rejects junk tokens."""
  s = str(arg0_raw or "").strip()
  if not s or EXCEL_ERROR_RE.search(s):
    return ""
  s = s.replace("andapos;", "'").replace("&apos;", "'").replace("&#39;", "'").replace("&amp;", "&").replace("&nbsp;", " ")
  s = html.unescape(s)
  s = s.split(";")[0].strip()
  s = re.sub(r"\s*\([^)]*\)", "", s).replace("`", "").strip()
  if re.search(r"[\u0400-\u04FF]", s):
    s = "".join(CYRILLIC_MAP.get(ch, ch) for ch in s)
  if re.search(r"[\u0370-\u03FF]", s):
    norm_g = "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")
    s = "".join(GREEK_MAP.get(ch, ch) for ch in norm_g)
  s = re.sub(r"\s+", " ", s).strip()
  if not s or NON_LATIN_RE.search(s) or "?" in s or "\ufffd" in s:
    return ""
  #Return statement
  return s


def normalise_stem(arg0_raw):
  """Normalises a place name to lowercase ASCII alphanumeric stem."""
  s = clean_to_latin(arg0_raw)
  if not s:
    s = str(arg0_raw or "").strip()
  nfd = unicodedata.normalize("NFD", s)
  no_marks = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
  stem = re.sub(r"[^a-z0-9]", "", no_marks.lower())
  #Return statement
  return stem


def is_valid_year(arg0_yr):
  """Checks valid historical year excluding year 0."""
  try:
    yr = int(arg0_yr)
    return yr != 0 and -10000 <= yr <= 2026
  except Exception:
    return False


def load_residuals_grid():
  """Loads all 14 Pass-2 residual files into a 0.1-deg spatial grid."""
  grid = {}
  regions = sorted(os.listdir(TOPO_DIR))
  total = 0
  for slug in regions:
    res_path = os.path.join(TOPO_DIR, slug, "pass2", "residuals.json")
    if not os.path.isfile(res_path):
      continue
    with open(res_path, "r", encoding="utf8") as f:
      raw = json.load(f)
    items = raw.get("settlements") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
      continue
    for it in items:
      coords = it.get("coords")
      if not isinstance(coords, list) or len(coords) < 2:
        continue
      lng = float(coords[0])
      lat = float(coords[1])
      name = str(it.get("name") or "")
      ckey = f"{lng:.5f},{lat:.5f}|{name.lower()}"
      ey = it.get("earliest_year", 1900)
      try:
        ey_int = int(ey)
      except Exception:
        ey_int = 1900
      if ey_int == 0:
        ey_int = -1
      ey_int = max(-10000, min(2026, ey_int))
      entry = {
        "ckey": ckey,
        "slug": slug,
        "lat": lat,
        "lng": lng,
        "name": name,
        "non_latin": bool(NON_LATIN_RE.search(name)),
        "stem": normalise_stem(name),
        "earliest_year": ey_int,
        "existing_names": it.get("names") if isinstance(it.get("names"), dict) else {}
      }
      cell = (round(lat*10), round(lng*10))
      grid.setdefault(cell, []).append(entry)
      total += 1
  print(f"[seed_pass2] Indexed {total} Pass-2 residual(s) across {len(grid)} grid cells.")
  #Return statement
  return grid


def iter_nearby(arg0_grid, arg1_lat, arg2_lng):
  """Yields candidate residual items from the 3x3 0.1-deg neighbourhood."""
  gx = round(arg1_lat*10)
  gy = round(arg2_lng*10)
  for dx in (-1, 0, 1):
    for dy in (-1, 0, 1):
      bucket = arg0_grid.get((gx + dx, gy + dy))
      if bucket:
        for item in bucket:
          yield item


def fetch_wikidata_p1448():
  """Fetches or loads cached global Wikidata P1448 official historical names with P580 + P625."""
  if os.path.isfile(WD_SPARQL_CACHE_PATH):
    with open(WD_SPARQL_CACHE_PATH, "r", encoding="utf8") as f:
      data = json.load(f)
    print(f"[seed_pass2] Loaded cached Wikidata SPARQL P1448 rows: {len(data)}")
    return data

  rows = []
  offset = 0
  limit = 15000
  max_rows = 120000
  while offset < max_rows:
    q = (
      "SELECT ?item ?coord ?name ?start WHERE { "
      "?item p:P1448 ?st . ?st ps:P1448 ?name . ?st pq:P580 ?start . ?item wdt:P625 ?coord . "
      f"}} LIMIT {limit} OFFSET {offset}"
    )
    url = "https://query.wikidata.org/sparql?query=" + urllib.parse.quote(q)
    req = urllib.request.Request(
      url,
      headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/sparql-results+json"
      }
    )
    try:
      with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf8"))
      bindings = payload.get("results", {}).get("bindings", [])
      print(f"[seed_pass2] Wikidata SPARQL offset={offset} limit={limit} -> {len(bindings)} row(s)")
      if not bindings:
        break
      for b in bindings:
        c_val = b.get("coord", {}).get("value", "")
        n_val = b.get("name", {}).get("value", "")
        s_val = b.get("start", {}).get("value", "")
        m_pt = POINT_RE.search(c_val)
        m_dt = re.match(r"^([+-]?\d+)-(\d{2})-(\d{2})", s_val)
        if not m_pt or not m_dt or not n_val:
          continue
        yr = int(m_dt.group(1))
        if not is_valid_year(yr):
          continue
        mo = max(1, int(m_dt.group(2)))
        dy = max(1, int(m_dt.group(3)))
        clean_nm = clean_to_latin(n_val)
        if not clean_nm:
          continue
        rows.append({
          "lng": float(m_pt.group(1)),
          "lat": float(m_pt.group(2)),
          "date": f"{yr}.{mo}.{dy}",
          "name": clean_nm,
          "stem": normalise_stem(clean_nm)
        })
      if len(bindings) < limit:
        break
      offset += limit
      time.sleep(1.0)
    except Exception as ex:
      print(f"[seed_pass2] Wikidata SPARQL error at offset={offset} limit={limit}: {ex}")
      if limit > 5000:
        limit = 5000
        time.sleep(2.0)
        continue
      break

  os.makedirs(GIS_CACHE_DIR, exist_ok=True)
  with open(WD_SPARQL_CACHE_PATH, "w", encoding="utf8") as f:
    json.dump(rows, f)
  print(f"[seed_pass2] Saved {len(rows)} clean Wikidata P1448 rows -> {WD_SPARQL_CACHE_PATH}")
  #Return statement
  return rows


def seed_wikidata_p1448(arg0_grid, arg1_cache):
  """Matches Wikidata P1448 historical attestations to Pass-2 residuals."""
  rows = fetch_wikidata_p1448()
  matched = 0
  for r in rows:
    lat = r["lat"]
    lng = r["lng"]
    r_stem = r["stem"]
    for item in iter_nearby(arg0_grid, lat, lng):
      d_km = haversine_km(lat, lng, item["lat"], item["lng"])
      if d_km > 6.0:
        continue
      i_stem = item["stem"]
      stem_ok = bool(r_stem and i_stem and (r_stem == i_stem or r_stem in i_stem or i_stem in r_stem))
      if not (stem_ok or d_km <= 0.35):
        continue
      ckey = item["ckey"]
      ent = arg1_cache.get(ckey)
      if not ent or ent.get("source") not in ("whg", "geohack_wikidata", "wikidata_sparql_p1448"):
        ent = {"names": {}, "source": "wikidata_sparql_p1448"}
        arg1_cache[ckey] = ent
        matched += 1
      ent["names"][r["date"]] = r["name"]
  print(f"[seed_pass2] Source 1 (Wikidata P1448) matched {matched} residual(s).")


def ensure_pleiades_names():
  """Downloads pleiades-names-latest.csv.gz if absent."""
  if os.path.isfile(PLEIADES_NAMES_PATH):
    return True
  url = "https://atlantides.org/downloads/pleiades/dumps/pleiades-names-latest.csv.gz"
  print(f"[seed_pass2] Downloading {url} -> {PLEIADES_NAMES_PATH}")
  req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
  try:
    with urllib.request.urlopen(req, timeout=60) as resp:
      data = resp.read()
    os.makedirs(GIS_CACHE_DIR, exist_ok=True)
    with open(PLEIADES_NAMES_PATH, "wb") as f:
      f.write(data)
    return True
  except Exception as ex:
    print(f"[seed_pass2] Warning: failed to download Pleiades names: {ex}")
    return False


def seed_pleiades(arg0_grid, arg1_cache):
  """Matches Pleiades ancient/medieval attestations to Pass-2 residuals."""
  if not os.path.isfile(PLEIADES_PLACES_PATH):
    print("[seed_pass2] Pleiades places file missing; skipping.")
    return
  has_names = ensure_pleiades_names()
  places = {}
  with gzip.open(PLEIADES_PLACES_PATH, "rt", encoding="utf8", errors="replace") as f:
    reader = csv.DictReader(f)
    for row in reader:
      pid = str(row.get("id") or "").strip()
      try:
        lat = float(row.get("reprLat") or "")
        lng = float(row.get("reprLong") or "")
      except Exception:
        continue
      title = clean_to_latin(row.get("title") or "")
      try:
        min_d = int(float(row.get("minDate") or 0))
      except Exception:
        min_d = 0
      try:
        max_d = int(float(row.get("maxDate") or 650))
      except Exception:
        max_d = 650
      sunset_yr = max(300, min(650, max_d)) if max_d > 0 else 650
      if pid and title:
        places[pid] = {"lat": lat, "lng": lng, "title": title, "min_date": min_d, "sunset_yr": sunset_yr, "names": []}

  if has_names and os.path.isfile(PLEIADES_NAMES_PATH):
    with gzip.open(PLEIADES_NAMES_PATH, "rt", encoding="utf8", errors="replace") as f:
      reader = csv.DictReader(f)
      for row in reader:
        pid = str(row.get("pid") or "").strip()
        pl = places.get(pid)
        if not pl:
          continue
        rom = clean_to_latin(row.get("romanized") or row.get("title") or "")
        if not rom:
          continue
        try:
          md = int(float(row.get("minDate") or pl["min_date"] or 0))
        except Exception:
          md = pl["min_date"]
        pl["names"].append((md, rom))

  matched = 0
  for pl in places.values():
    lat = pl["lat"]
    lng = pl["lng"]
    cand_stems = {normalise_stem(pl["title"])}
    for _, nm in pl["names"]:
      st = normalise_stem(nm)
      if st:
        cand_stems.add(st)
    cand_stems.discard("")
    if not cand_stems:
      continue
    for item in iter_nearby(arg0_grid, lat, lng):
      if item["stem"] not in cand_stems:
        continue
      if haversine_km(lat, lng, item["lat"], item["lng"]) > 8.0:
        continue
      ckey = item["ckey"]
      ent = arg1_cache.get(ckey)
      if ent and ent.get("source") in ("whg", "geohack_wikidata", "wikidata_sparql_p1448"):
        continue
      names_map = ent["names"] if ent else {}
      for md, nm in pl["names"]:
        if is_valid_year(md):
          names_map[f"{md}.1.1"] = nm
      if not names_map and is_valid_year(pl["min_date"]):
        names_map[f"{pl['min_date']}.1.1"] = pl["title"]
      sunset_yr = pl.get("sunset_yr", 650)
      mod_yr = min(sunset_yr, max(item["earliest_year"], 650))
      mod_nm = clean_to_latin(item["name"])
      if mod_nm and is_valid_year(mod_yr):
        names_map[f"{mod_yr}.1.1"] = mod_nm
      if names_map:
        arg1_cache[ckey] = {"names": names_map, "source": "pleiades_historical"}
        matched += 1
  print(f"[seed_pass2] Source 2 (Pleiades) matched {matched} residual(s).")


def seed_local_historical(arg0_grid, arg1_cache):
  """Matches local wikidata_europe_attestations.json and mexico_ahl_historical_names.json."""
  matched_eu = 0
  if os.path.isfile(WD_EU_PATH):
    with open(WD_EU_PATH, "r", encoding="utf8") as f:
      eu = json.load(f)
    records = []
    if isinstance(eu, dict):
      for v in eu.values():
        if isinstance(v, list):
          records.extend(v)
    elif isinstance(eu, list):
      records = eu
    for rec in records:
      if not isinstance(rec, dict):
        continue
      nm = clean_to_latin(rec.get("n") or rec.get("name") or "")
      try:
        lat = float(rec.get("la"))
        lng = float(rec.get("lo"))
        yr = int(rec.get("y"))
      except Exception:
        continue
      if not nm or not is_valid_year(yr):
        continue
      st = normalise_stem(nm)
      if not st:
        continue
      for item in iter_nearby(arg0_grid, lat, lng):
        if item["stem"] != st:
          continue
        if haversine_km(lat, lng, item["lat"], item["lng"]) > 5.0:
          continue
        ckey = item["ckey"]
        ent = arg1_cache.get(ckey)
        if ent and ent.get("source") in ("whg", "geohack_wikidata", "wikidata_sparql_p1448", "pleiades_historical"):
          continue
        names_map = dict(item["existing_names"]) if item["existing_names"] else {}
        names_map[f"{yr}.1.1"] = nm
        arg1_cache[ckey] = {"names": names_map, "source": "wikidata_europe_attestations"}
        matched_eu += 1

  matched_mx = 0
  if os.path.isfile(MEX_AHL_PATH):
    with open(MEX_AHL_PATH, "r", encoding="utf8") as f:
      mx = json.load(f)
    mx_items = mx if isinstance(mx, list) else (mx.get("cities") or mx.get("settlements") or list(mx.values()) if isinstance(mx, dict) else [])
    for rec in mx_items:
      if not isinstance(rec, dict):
        continue
      coords = rec.get("coords")
      try:
        if isinstance(coords, list) and len(coords) >= 2:
          lng, lat = float(coords[0]), float(coords[1])
        else:
          lat = float(rec.get("lat"))
          lng = float(rec.get("lng") if rec.get("lng") is not None else rec.get("lon"))
      except Exception:
        continue
      nm = clean_to_latin(rec.get("name") or rec.get("title") or "")
      st = normalise_stem(nm)
      if not st:
        continue
      for item in iter_nearby(arg0_grid, lat, lng):
        if item["stem"] != st:
          continue
        if haversine_km(lat, lng, item["lat"], item["lng"]) > 5.0:
          continue
        ckey = item["ckey"]
        ent = arg1_cache.get(ckey)
        if ent and ent.get("source") in ("whg", "geohack_wikidata", "wikidata_sparql_p1448", "pleiades_historical"):
          continue
        names_map = dict(item["existing_names"]) if item["existing_names"] else {}
        hn = rec.get("historical_names") or rec.get("names")
        if isinstance(hn, list):
          for h in hn:
            if isinstance(h, dict) and h.get("date") and h.get("name"):
              cn = clean_to_latin(h["name"])
              if cn:
                names_map[str(h["date"])] = cn
        elif isinstance(hn, dict):
          for dk, dv in hn.items():
            cn = clean_to_latin(dv)
            if cn:
              names_map[str(dk)] = cn
        if not names_map and nm:
          names_map[f"{item['earliest_year']}.1.1"] = nm
        if names_map:
          arg1_cache[ckey] = {"names": names_map, "source": "mexico_ahl_historical"}
          matched_mx += 1
  print(f"[seed_pass2] Source 3 matched EU={matched_eu}, Mexico={matched_mx}.")


def discover_geonames_files():
  """Finds unique local GeoNames zip/txt populated-place dumps under population_regional/."""
  seen_basenames = set()
  files = []
  priority = [
    os.path.join(POP_REG_DIR, "MAGNETIC", "_shared", "settlement_sources", "pale_east_prussia", "geonames_cities500.zip"),
    os.path.join(POP_REG_DIR, "MAGNETIC", "_shared", "settlement_sources", "geonames_cities1000.zip")
  ]
  for p in priority:
    if os.path.isfile(p):
      bn = os.path.basename(p).lower().replace("supplemental_", "")
      seen_basenames.add(bn)
      files.append(p)
  for root, _, fns in os.walk(POP_REG_DIR):
    for fn in sorted(fns):
      low = fn.lower()
      if not low.startswith("geonames_"):
        continue
      if "admin1" in low or "admin2" in low:
        continue
      if not (low.endswith(".zip") or low.endswith(".txt")):
        continue
      bn = low.replace("supplemental_", "")
      if bn in seen_basenames:
        continue
      seen_basenames.add(bn)
      files.append(os.path.join(root, fn))
  #Return statement
  return files


def iter_geonames_lines(arg0_path):
  """Yields decoded TSV lines from a GeoNames .zip or .txt file."""
  if arg0_path.lower().endswith(".zip"):
    with zipfile.ZipFile(arg0_path, "r") as zf:
      for zi in zf.infolist():
        if zi.filename.lower().endswith(".txt") and "readme" not in zi.filename.lower():
          with zf.open(zi, "r") as member:
            for raw_line in io.TextIOWrapper(member, encoding="utf8", errors="replace"):
              yield raw_line
  else:
    with open(arg0_path, "r", encoding="utf8", errors="replace") as f:
      for raw_line in f:
        yield raw_line


def seed_geonames(arg0_grid, arg1_cache):
  """Matches local GeoNames feature_class=='P' populated places to Pass-2 residuals."""
  gn_files = discover_geonames_files()
  print(f"[seed_pass2] Source 4 scanning {len(gn_files)} unique GeoNames dump(s)...")
  seen_gid = set()
  matched = 0
  for path in gn_files:
    try:
      for line in iter_geonames_lines(path):
        parts = line.rstrip("\r\n").split("\t")
        if len(parts) < 8 or parts[6] != "P":
          continue
        gid = parts[0]
        if gid in seen_gid:
          continue
        seen_gid.add(gid)
        try:
          lat = float(parts[4])
          lng = float(parts[5])
        except Exception:
          continue
        nm_main = clean_to_latin(parts[1]) or clean_to_latin(parts[2])
        if not nm_main:
          continue
        cand_stems = set()
        for raw_cand in (parts[1], parts[2]):
          st = normalise_stem(raw_cand)
          if st:
            cand_stems.add(st)
        if parts[3]:
          for alt in parts[3].split(","):
            st = normalise_stem(alt)
            if st:
              cand_stems.add(st)
        for item in iter_nearby(arg0_grid, lat, lng):
          d_km = haversine_km(lat, lng, item["lat"], item["lng"])
          if d_km > 5.0:
            continue
          if not (item["stem"] in cand_stems or (item["non_latin"] and d_km <= 0.35)):
            continue
          ckey = item["ckey"]
          if ckey in arg1_cache:
            continue
          names_map = {}
          for dk, dv in item["existing_names"].items():
            cn = clean_to_latin(dv)
            if cn:
              names_map[dk] = cn
          names_map[f"{item['earliest_year']}.1.1"] = nm_main
          arg1_cache[ckey] = {"names": names_map, "source": "geonames_gazetteer"}
          matched += 1
    except Exception as ex:
      print(f"[seed_pass2] Warning reading {os.path.basename(path)}: {ex}")
  print(f"[seed_pass2] Source 4 (GeoNames) matched {matched} residual(s) across {len(seen_gid)} unique P-class places.")


def main():
  t0 = time.time()
  cache = {}
  if os.path.isfile(CACHE_PATH):
    try:
      with open(CACHE_PATH, "r", encoding="utf8") as f:
        cache = json.load(f)
    except Exception:
      cache = {}
  grid = load_residuals_grid()
  seed_wikidata_p1448(grid, cache)
  seed_pleiades(grid, cache)
  seed_local_historical(grid, cache)
  seed_geonames(grid, cache)

  os.makedirs(GIS_CACHE_DIR, exist_ok=True)
  with open(CACHE_PATH, "w", encoding="utf8") as f:
    json.dump(cache, f)

  by_src = {}
  for v in cache.values():
    s = v.get("source", "unknown")
    by_src[s] = by_src.get(s, 0) + 1
  print(f"[seed_pass2] Done in {time.time() - t0:.1f}s. Total cache entries: {len(cache)}. Breakdown: {json.dumps(by_src)}")


if __name__ == "__main__":
  main()
