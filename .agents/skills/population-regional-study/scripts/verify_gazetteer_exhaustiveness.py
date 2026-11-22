"""Gatekeeper A: Verifies exhaustive settlement inclusion (anti-stub guardrails +
asymptotic maximum-saturation checks), temporal decennial census continuity,
spatial boundary validity, and schema integrity (`_settlements.json` + `_source_ledger.json5`
or compiled Stadestér 2.0 shards).
"""

import argparse
import csv
import glob
import json
import math
import os
import re
import sys

import numpy as np
from PIL import Image

try:
  import json5
except ImportError:
  json5 = None

try:
  from shapely.geometry import Point, box, shape
  from shapely.strtree import STRtree
except ImportError:
  Point = None
  box = None
  shape = None
  STRtree = None


CANONICAL_VISCOUNT_PROJECTS = {
  "CENTAUR",
  "POLARIS",
  "PRETA",
  "JADE",
  "INDUS",
  "CASTLE",
  "MANDALA",
  "SARAY",
  "HANDBOOK",
  "MAGNETIC",
  "QUIPU",
  "JAGUAR",
  "AUSTRAL",
  "NICETHI",
}

VALID_EXCLUDE_REASONS = {
  "outside_study_bounds",
  "subordinate_suburb_merged",
  "unlocated_historical_toponym",
  "duplicate_alias",
  "seasonal_encampment_unquantified",
  "superseded_by_higher_priority_tier",
}

DUMMY_EXCLUSION_PAT = re.compile(
  r"(?:unnamed|unlocated)\s+seasonal\s+camp|generic\s+camp|placeholder\s+camp|stub\s+entry",
  flags=re.IGNORECASE,
)

SCRIPT_TRUNCATION_PATTERNS = [
  (r"\btwps0027\b", "Gibson Top-100 US cities compendium (`twps0027`) used instead of full census"),
  (r"\btop_100_cities\b|\btop100_us\b", "Top-100 city compendium shortcut"),
  (r"\bLIMIT\s+(?:50|100|120|150|200|250)\b", "SQL LIMIT <= 250 cap"),
  (r"\bmax_settlements\s*=\s*(?:[1-9]\d?|1\d\d|2[0-4]\d|250)\b", "Hard max_settlements <= 250 quota cap"),
]

def load_skill_profiles(arg0_svea_root=None):
  """Loads 14-region skill profiles (`viscount_skill_profiles.json5`) for dynamic ADM0, census and qualifier rules."""
  candidates = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config/viscount_skill_profiles.json5"),
  ]
  if arg0_svea_root:
    candidates.append(
      os.path.join(arg0_svea_root, ".agents/skills/population-regional-study/config/viscount_skill_profiles.json5")
    )
  for cand in candidates:
    if os.path.isfile(cand):
      return load_json_or_json5(cand)
  return {}


def infer_project_from_paths(arg0_paths, arg1_svea_root):
  """Infers canonical Viscount project key and defaults from shard filenames or paths."""
  if not arg1_svea_root:
    return None, {}
  prec_p = os.path.join(arg1_svea_root, "histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5")
  profiles = load_skill_profiles(arg1_svea_root)
  if not os.path.isfile(prec_p):
    return None, {}
  prec = load_json_or_json5(prec_p)
  defaults = profiles.get("macro_region_defaults") or {}
  for sp in arg0_paths:
    norm = os.path.abspath(sp).replace("\\", "/")
    base = os.path.basename(norm).lower()
    for p in prec.get("projects", []):
      k = str(p.get("key") or "").upper()
      pref = str(p.get("shard_prefix") or "").lower()
      if (pref and base.startswith(pref)) or (k and f"/{k}/" in norm.upper()):
        return k, defaults.get(k, {})
  return None, {}


def _haversine_km(arg0_lat1, arg1_lon1, arg2_lat2, arg3_lon2):
  """Great-circle distance in km."""
  dlat = math.radians(arg2_lat2 - arg0_lat1)
  dlon = math.radians(arg3_lon2 - arg1_lon1)
  a = (
    math.sin(dlat / 2.0) ** 2
    + math.cos(math.radians(arg0_lat1)) * math.cos(math.radians(arg2_lat2)) * math.sin(dlon / 2.0) ** 2
  )
  return 6371.0 * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def _normalise_entity_stem(arg0_name):
  """Normalises a settlement name across diacritics and common historical romanisations."""
  import unicodedata
  base = str(arg0_name or "").split(";")[0].split("(")[0].strip().lower()
  base = unicodedata.normalize("NFD", base)
  base = "".join(ch for ch in base if unicodedata.category(ch) != "Mn")
  for src, dst in (("ł", "l"), ("đ", "d"), ("ø", "o"), ("ß", "ss"), ("æ", "ae"), ("œ", "oe")):
    base = base.replace(src, dst)
  base = re.sub(r"^(?:st\.?|saint|san|santa|sao|al-|el-)\s+", "saint ", base)
  for src, dst in (("kh", "k"), ("gh", "g"), ("ph", "f"), ("dj", "j"), ("ou", "u"), ("ts", "c")):
    base = base.replace(src, dst)
  base = re.sub(r"[jy]", "i", base)
  base = re.sub(r"[cq]", "k", base)
  return re.sub(r"[^a-z0-9]+", "", base)


def _bigram_dice(arg0_a, arg1_b):
  """Computes Sørensen-Dice bigram similarity between two normalised stems."""
  a = str(arg0_a or "")
  b = str(arg1_b or "")
  if not a or not b:
    return 0.0
  if a == b:
    return 1.0
  if len(a) < 2 or len(b) < 2:
    return 0.0
  bg_a = [a[i:i + 2] for i in range(len(a) - 1)]
  bg_b = [b[i:i + 2] for i in range(len(b) - 1)]
  inter = 0
  for tok in bg_a:
    if tok in bg_b:
      inter += 1
      bg_b.remove(tok)
  return (2.0 * inter) / (len(bg_a) + (len(b) - 1))


def _are_equivalent_exonyms(arg0_name_a, arg1_name_b, arg2_profiles):
  """Returns True when two names share a normalised stem or declared romanisation equivalence class."""
  a = _normalise_entity_stem(arg0_name_a)
  b = _normalise_entity_stem(arg1_name_b)
  if not a or not b:
    return False
  if a == b:
    return True
  for grp in (arg2_profiles or {}).get("romanisation_equivalences") or []:
    if isinstance(grp, list) and a in grp and b in grp:
      return True
  return False


def is_suspicious_toponym(arg0_name, arg1_profiles, arg2_is_arch_site=False):
  """Detects non-settlement temples, shrines, monuments or raw admin-unit suffixes."""
  raw = str(arg0_name or "").strip()
  if not raw:
    return None
  low = raw.lower()
  cfg = (arg1_profiles or {}).get("suspicious_toponym_patterns") or {}
  allow = {str(x).strip().lower() for x in (cfg.get("allowlist") or [])}
  if low in allow:
    return None
  qualifiers = [str(q).lower() for q in ((arg1_profiles or {}).get("arch_site_qualifiers") or [])]
  if arg2_is_arch_site and any(re.search(rf"\b{re.escape(q)}\b", low) for q in qualifiers):
    return None
  for pat in (cfg.get("religious_monument_regexes") or []):
    if re.search(pat, low, flags=re.IGNORECASE):
      return f"religious/monumental non-settlement pattern `{pat}`"
  for pat in (cfg.get("admin_unit_suffix_regexes") or []):
    if re.search(pat, low, flags=re.IGNORECASE):
      return f"raw administrative-unit suffix pattern `{pat}`"
  return None


def find_svea_root(arg0_start_path):
  """Walks upward from start path or script location to find SVEA workspace root."""
  candidates = [
    os.path.abspath(arg0_start_path or "."),
    os.path.abspath(os.path.dirname(__file__)),
    os.getcwd(),
  ]
  for base in candidates:
    cur = base if os.path.isdir(base) else os.path.dirname(base)
    for _ in range(10):
      if os.path.isdir(os.path.join(cur, "histmap")) and os.path.isdir(os.path.join(cur, ".agents")):
        return cur
      parent = os.path.dirname(cur)
      if parent == cur:
        break
      cur = parent
  return None


def load_json_or_json5(arg0_path):
  """Loads JSON via stdlib first, falling back to json5 or comment-stripped JSON."""
  with open(arg0_path, "r", encoding="utf-8") as fh:
    text = fh.read()
  try:
    return json.loads(text)
  except (json.JSONDecodeError, ValueError):
    if json5 is not None:
      return json5.loads(text)
    stripped = re.sub(r"//.*?$|/\*.*?\*/", "", text, flags=re.MULTILINE | re.DOTALL)
    stripped = re.sub(r",(\s*[}\]])", r"\1", stripped)
    return json.loads(stripped)


def is_corrupt_name(arg0_name, arg1_allow_backtick=False):
  """Mirrors Dataview city name validation rules, optionally allowing legacy backtick carons."""
  if not isinstance(arg0_name, str):
    return True
  s = arg0_name.strip()
  if not s or s in {"0", "Unknown", "Settlement"}:
    return True
  if re.match(r"^[?\s\-_.,]+$", s):
    return True
  forbidden = ("?", "\ufffd", "\u00ef\u00bf\u00bd") if arg1_allow_backtick else ("?", "\ufffd", "\u00ef\u00bf\u00bd", "`")
  if any(ch in s for ch in forbidden):
    return True
  return False


def resolve_audit_mode(arg0_paths, arg1_mode=None, arg2_require_sources=False):
  """Resolves whether validation enforces regional literature-review rules or compiled Stadestér rules."""
  if arg1_mode in ("regional", "compiled"):
    return arg1_mode
  for p in arg0_paths:
    norm_path = str(p or "").replace("\\", "/").lower()
    if "population_regional" in norm_path:
      return "regional"
  if arg2_require_sources:
    return "compiled"
  return "compiled"


def validate_city_sources(arg0_city, arg1_ckey, arg2_idx, arg3_mode, arg4_require_sources):
  """Validates `.sources` array schema and rejects legacy `.type` or disallowed source identifiers."""
  has_legacy_type = "type" in arg0_city
  missing_sources = False
  source_error = None

  if "sources" not in arg0_city:
    if arg4_require_sources:
      missing_sources = True
    return has_legacy_type, missing_sources, source_error

  sources = arg0_city.get("sources")
  if not isinstance(sources, list) or len(sources) == 0:
    source_error = f"Settlement {arg1_ckey!r} (index {arg2_idx}) has invalid 'sources': expected a non-empty list, got {sources!r}."
    return has_legacy_type, missing_sources, source_error

  seen = set()
  for item in sources:
    if not isinstance(item, str) or not item.strip():
      source_error = f"Settlement {arg1_ckey!r} (index {arg2_idx}) has invalid non-empty string entry in 'sources': {item!r}."
      break
    if item.strip().lower() == "viscount_regional":
      source_error = f"Settlement {arg1_ckey!r} (index {arg2_idx}) uses forbidden source tag 'viscount_regional'; cite canonical Viscount project name instead."
      break
    if item in seen:
      source_error = f"Settlement {arg1_ckey!r} (index {arg2_idx}) has duplicate entry {item!r} in 'sources'."
      break
    seen.add(item)
    if arg3_mode == "regional" and item not in CANONICAL_VISCOUNT_PROJECTS:
      source_error = (
        f"Regional settlement {arg1_ckey!r} (index {arg2_idx}) has non-project source {item!r}; "
        "regional _settlements.json .sources must cite only canonical Viscount project names."
      )
      break

  return has_legacy_type, missing_sources, source_error


def count_c14_sites_in_mask(arg0_svea_root, arg1_mask_png):
  """Counts unique c14_cleaned_dedup sites lying inside a 4320x2160 regional mask PNG."""
  if not arg0_svea_root or not arg1_mask_png or not os.path.isfile(arg1_mask_png):
    return None
  c14_path = os.path.join(arg0_svea_root, "histmap/1.data_raw/population_c14bazAAR/c14_cleaned_dedup.csv")
  if not os.path.isfile(c14_path):
    return None
  mask_arr = np.asarray(Image.open(arg1_mask_png).convert("RGBA"), dtype=np.uint8)
  h, w = mask_arr.shape[:2]
  valid = (mask_arr[:, :, 3] > 0) & ((mask_arr[:, :, :3].sum(axis=2)) > 0)
  seen = set()
  in_mask = 0
  with open(c14_path, "r", encoding="utf-8", errors="replace") as fh:
    reader = csv.DictReader(fh)
    for row in reader:
      try:
        lat = float(row.get("lat") or 0.0)
        lon = float(row.get("lon") or 0.0)
      except (TypeError, ValueError):
        continue
      site = str(row.get("site") or "").strip().lower()
      key = (round(lat, 3), round(lon, 3), site)
      if key in seen:
        continue
      seen.add(key)
      r_idx = min(h - 1, max(0, int((90.0 - lat) * h / 180.0)))
      c_idx = min(w - 1, max(0, int((lon + 180.0) * w / 360.0)))
      if valid[r_idx, c_idx]:
        in_mask += 1
  return in_mask


def audit_temporal_density_and_universe(arg0_entries, arg1_mode):
  """Checks decennial point-density continuity (no census cliffs) and pre-1995 universe capture."""
  errors = []
  warnings = []
  yr_counts = {}
  post_1995_only = 0
  modern_total = 0

  for city in arg0_entries:
    pop = city.get("population")
    if not isinstance(pop, dict):
      continue
    yrs = []
    for yk, pv in pop.items():
      try:
        yi = int(yk)
        fv = float(pv)
      except (TypeError, ValueError):
        continue
      if fv > 0:
        yrs.append(yi)
        yr_counts[yi] = yr_counts.get(yi, 0) + 1
    if yrs:
      yrs.sort()
      if yrs[-1] >= 1950:
        modern_total += 1
        if yrs[0] > 1995:
          post_1995_only += 1

  major_dec = sorted((y, c) for y, c in yr_counts.items() if y >= 1850 and y % 10 == 0 and c >= 25)
  max_jump = 1.0
  max_jump_pair = None
  for i in range(len(major_dec) - 1):
    y1, n1 = major_dec[i]
    y2, n2 = major_dec[i + 1]
    if 1 <= (y2 - y1) <= 35:
      ratio = float(n2) / max(1, n1)
      if ratio > max_jump:
        max_jump = ratio
        max_jump_pair = (y1, n1, y2, n2)
      if ratio > 3.0:
        errors.append(
          f"[SATURATION] Decennial census coverage cliff between {y1}AD ({n1} cities) and {y2}AD "
          f"({n2} cities, {ratio:.2f}x jump > 3.0x max allowed): pre-{y2}AD censuses are not saturated."
        )

  post_1995_ratio = (float(post_1995_only) / modern_total) if modern_total > 0 else 0.0
  if arg1_mode == "compiled" and modern_total >= 100 and post_1995_ratio > 0.45:
    errors.append(
      f"[SATURATION] Universe capture failure: {post_1995_only}/{modern_total} ({post_1995_ratio*100:.1f}%) "
      "modern settlements exist only after 1995AD (threshold <= 45.0%; indicates uningested historical censuses)."
    )

  return errors, warnings, {
    "modern_total": modern_total,
    "post_1995_only": post_1995_only,
    "post_1995_only_ratio": round(post_1995_ratio, 4),
    "max_decennial_jump": round(max_jump, 2),
    "max_jump_pair": max_jump_pair,
  }


def load_adm0_polygons(arg0_svea_root, arg1_buffer_deg=0.28, arg2_union_bboxes=None):
  """Loads Natural Earth ADM0 country geometries with parametric coastal buffer and union overrides."""
  if not arg0_svea_root or shape is None:
    return {}, {}
  candidates = [
    os.path.join(arg0_svea_root, "histmap/1.data_raw/population_regional/_shared/_gis_cache/ne_10m_admin_0_countries.geojson"),
    os.path.join(arg0_svea_root, "histmap/1.data_raw/population_regional/CENTAUR/_shared/_gis_cache/ne_10m_admin_0_countries.geojson"),
    os.path.join(arg0_svea_root, "histmap/1.data_raw/population_regional/POLARIS/_shared/_gis_cache/ne_50m_admin_0_countries.geojson"),
  ]
  gj_path = next((p for p in candidates if os.path.isfile(p)), None)
  if not gj_path:
    return {}, {}
  gj = json.loads(open(gj_path, "r", encoding="utf-8").read())
  by_name = {}
  lower_lookup = {}
  for feat in gj.get("features", []):
    props = feat.get("properties") or {}
    geom_raw = feat.get("geometry")
    if not geom_raw:
      continue
    geom = shape(geom_raw).buffer(arg1_buffer_deg)
    canonical = str(props.get("ADMIN") or props.get("NAME") or "").strip()
    if not canonical:
      continue
    by_name[canonical] = by_name[canonical].union(geom) if canonical in by_name else geom
    for k in ("ADMIN", "NAME", "NAME_LONG", "BRK_NAME", "ABBREV", "SOVEREIGNT", "ADM0_A3"):
      nm = str(props.get(k) or "").strip()
      if nm:
        lower_lookup.setdefault(nm.lower(), canonical)
  if box is not None and isinstance(arg2_union_bboxes, dict):
    for target_country, coords in arg2_union_bboxes.items():
      if target_country in by_name and isinstance(coords, list) and len(coords) >= 4:
        by_name[target_country] = by_name[target_country].union(box(*[float(v) for v in coords[:4]]))
  return by_name, lower_lookup


def audit_spatial_bounds(arg0_entries, arg1_svea_root, arg2_mask_png=None, arg3_profiles=None, arg4_proj_defaults=None):
  """Verifies settlement coordinates lie inside sovereign country bounds and optional regional mask."""
  errors = []
  warnings = []
  profiles = arg3_profiles if isinstance(arg3_profiles, dict) else load_skill_profiles(arg1_svea_root)
  has_micro = bool((arg4_proj_defaults or {}).get("has_micro_islands", False))
  buf_deg = 0.65 if has_micro else 0.28
  adm0_map, ne_lower = load_adm0_polygons(
    arg1_svea_root, buf_deg, profiles.get("polygon_union_bboxes")
  ) if Point is not None else ({}, {})
  overrides = {str(k).lower(): v for k, v in (profiles.get("adm0_canonical_overrides") or {}).items()}
  out_of_country = []

  for city in arg0_entries:
    cname = city.get("country")
    coords = city.get("coords")
    if not cname or not isinstance(coords, list) or len(coords) < 2:
      continue
    try:
      lat = float(coords[0])
      lon = float(coords[1])
    except (TypeError, ValueError):
      continue
    clow = str(cname).strip().lower()
    if clow == "georgia":
      mapped = "United States of America" if lon < -30.0 else "Georgia"
    else:
      mapped = overrides.get(clow) or ne_lower.get(clow)
    if not mapped or mapped not in adm0_map:
      continue
    if not adm0_map[mapped].contains(Point(lon, lat)):
      out_of_country.append(f"{city.get('key', city.get('name'))}@{lat:.2f},{lon:.2f} (declared {cname})")

  if len(out_of_country) > max(5, int(0.01 * len(arg0_entries))):
    errors.append(
      f"[SPATIAL] {len(out_of_country)} settlement(s) fall outside declared country polygon (>{buf_deg:.2f} deg buffer): {out_of_country[:5]}"
    )
  elif out_of_country:
    warnings.append(
      f"[SPATIAL] {len(out_of_country)} boundary/outlier settlement(s) outside {buf_deg:.2f} deg country buffer: {out_of_country[:5]}"
    )

  if arg2_mask_png and os.path.isfile(arg2_mask_png):
    mask_arr = np.asarray(Image.open(arg2_mask_png).convert("RGBA"), dtype=np.uint8)
    h, w = mask_arr.shape[:2]
    valid = (mask_arr[:, :, 3] > 0) & ((mask_arr[:, :, :3].sum(axis=2)) > 0)
    checked = 0
    outside_mask = []
    rad = 5 if has_micro else 2
    for city in arg0_entries:
      coords = city.get("coords")
      if not isinstance(coords, list) or len(coords) < 2:
        continue
      try:
        lat = float(coords[0])
        lon = float(coords[1])
      except (TypeError, ValueError):
        continue
      checked += 1
      r_idx = min(h - 1, max(0, int((90.0 - lat) * h / 180.0)))
      c_idx = min(w - 1, max(0, int((lon + 180.0) * w / 360.0)))
      if not bool(valid[max(0, r_idx - rad):min(h, r_idx + rad + 1), max(0, c_idx - rad):min(w, c_idx + rad + 1)].any()):
        outside_mask.append(f"{city.get('name')}@{lat:.2f},{lon:.2f}")
    if checked > 0 and len(outside_mask) > max(1, int(0.05 * checked)):
      errors.append(
        f"[SPATIAL] {len(outside_mask)}/{checked} settlement(s) fall outside regional mask {os.path.basename(arg2_mask_png)}: {outside_mask[:5]}"
      )

  return errors, warnings


def audit_universal_gazetteer_anomalies(arg0_entries, arg1_mode, arg2_profiles, arg3_options):
  """Enforces universal checks across all 14 Viscount regions: (agglomeration) ghosts, compound
  modern municipalities, foundation_year anachronisms, suspicious temple/admin names, all-era
  variant-spelling near-duplicates, modern <=1,5km close pairs and GeoNames homonyms.
  """
  errors = []
  warnings = []
  qualifiers = [str(q).lower() for q in (arg2_profiles.get("arch_site_qualifiers") or [])]
  mod_yr = int(arg3_options.get("modern_census_year") or 1850)
  by_country = {}
  all_by_country = {}
  dup_sig = {}
  aggl_hits, comp_hits, found_anach, close_pairs = [], [], [], []
  suspicious_hits, variant_dup_hits = [], []

  for idx, city in enumerate(arg0_entries):
    cname = str(city.get("name") or city.get("key") or f"entry_{idx}")
    ckey = str(city.get("key") or cname)
    country = str(city.get("country") or "").strip().lower()
    if "(agglomeration)" in ckey.lower() or "(agglomeration)" in cname.lower():
      aggl_hits.append(ckey)

    pop = city.get("population") if isinstance(city.get("population"), dict) else {}
    pos_yrs = []
    for yk, pv in pop.items():
      try:
        yi, fv = int(yk), float(pv)
        if fv > 0:
          pos_yrs.append(yi)
      except (TypeError, ValueError):
        continue
    min_yr = min(pos_yrs) if pos_yrs else 99999
    max_yr = max(pos_yrs) if pos_yrs else -99999

    if max_yr >= 1750 and " & " in cname and not any(q in cname.lower() for q in qualifiers):
      comp_hits.append(ckey)

    is_pure_arch = max_yr < 1000 and any(re.search(rf"\b{re.escape(q)}\b", cname.lower()) for q in qualifiers)
    if not city.get("verified_settlement"):
      susp_reason = is_suspicious_toponym(cname, arg2_profiles, arg2_is_arch_site=is_pure_arch)
      if susp_reason:
        suspicious_hits.append(f"{ckey} ({susp_reason})")

    fy = city.get("foundation_year")
    if fy is not None:
      try:
        fyi = int(fy)
        bad_pre = [y for y in pos_yrs if y < fyi]
        if bad_pre:
          found_anach.append(f"{ckey}(found={fyi},yr={min(bad_pre)})")
      except (TypeError, ValueError):
        pass

    coords = city.get("coords")
    if isinstance(coords, list) and len(coords) >= 2:
      try:
        la, lo = float(coords[0]), float(coords[1])
        mod_set = {y for y in pos_yrs if y >= mod_yr}
        if mod_set:
          by_country.setdefault(country, []).append((ckey, la, lo, mod_set))
        if pos_yrs:
          all_by_country.setdefault(country, []).append((ckey, cname, _normalise_entity_stem(cname), la, lo, min_yr, max_yr))
      except (TypeError, ValueError):
        pass

    if len(pos_yrs) >= 3:
      sig = (re.sub(r"[^a-z0-9]+", "", cname.lower()), tuple(sorted((int(y), round(float(pop[str(y)]), 1)) for y in pos_yrs[:6])))
      if sig in dup_sig:
        warnings.append(f"[HOMONYM] Identical multi-year trajectory on same name stem: {dup_sig[sig]!r} vs {ckey!r}.")
      else:
        dup_sig[sig] = ckey

  if aggl_hits:
    errors.append(f"[TWINS] Forbidden `(agglomeration)` ghost entry/entries ({len(aggl_hits)}): {aggl_hits[:5]}")
  if comp_hits:
    errors.append(f"[COMPOUND] Unsplit compound modern municipality `' & '` entry/entries ({len(comp_hits)}): {comp_hits[:5]}")
  if found_anach:
    errors.append(f"[FOUNDATION] Pre-foundation population anachronism(s) ({len(found_anach)}): {found_anach[:5]}")
  if suspicious_hits:
    errors.append(
      f"[SUSPICIOUS_NAME] Non-settlement temple/shrine/monument or admin-unit name(s) detected ({len(suspicious_hits)}): {suspicious_hits[:5]}"
    )

  # All-era variant-spelling near-duplicate detection (<= 25 km same country with matching stem/Dice >= 0.82 or exonym equivalence)
  for arr in all_by_country.values():
    arr.sort(key=lambda x: x[3])
    for i in range(len(arr)):
      k1, n1, s1, la1, lo1, mn1, mx1 = arr[i]
      if len(s1) < 3:
        continue
      for j in range(i + 1, len(arr)):
        k2, n2, s2, la2, lo2, mn2, mx2 = arr[j]
        if la2 - la1 > 0.25:
          break
        if len(s2) < 3 or abs(lo2 - lo1) > 0.45:
          continue
        if mx1 < mn2 - 100 or mx2 < mn1 - 100:
          continue
        dkm = _haversine_km(la1, lo1, la2, lo2)
        if dkm <= 25.0:
          is_dup_name = (s1 == s2) or _are_equivalent_exonyms(n1, n2, arg2_profiles) or (
            min(len(s1), len(s2)) >= 5 and _bigram_dice(s1, s2) >= 0.82
          )
          if is_dup_name:
            variant_dup_hits.append(f"{k1}<->{k2} ({dkm:.1f} km)")
  if variant_dup_hits:
    errors.append(
      f"[VARIANT_DUP] Variant-spelling / near-duplicate settlement pair(s) <= 25 km ({len(variant_dup_hits)}): {variant_dup_hits[:5]}"
    )

  if arg1_mode == "compiled" or arg3_options.get("check_close_pairs"):
    for arr in by_country.values():
      arr.sort(key=lambda x: x[1])
      for i in range(len(arr)):
        k1, la1, lo1, y1 = arr[i]
        for j in range(i + 1, len(arr)):
          k2, la2, lo2, y2 = arr[j]
          if la2 - la1 > 0.02:
            break
          dkm = _haversine_km(la1, lo1, la2, lo2)
          if dkm <= 1.5 and (y1 & y2):
            close_pairs.append(f"{k1}<->{k2} ({dkm:.2f} km)")
    if close_pairs:
      errors.append(f"[TWINS] Same-country active pairs <= 1,5 km after {mod_yr}AD ({len(close_pairs)}): {close_pairs[:5]}")

  # Optional GeoNames homonym-hijack cross-audit
  gn_path = arg3_options.get("geonames_audit")
  if gn_path and os.path.isfile(gn_path):
    gn_idx = {}
    with open(gn_path, "r", encoding="utf-8", errors="replace") as fh:
      for ln in fh:
        cols = ln.rstrip("\n").split("\t")
        if len(cols) >= 15:
          try:
            gn_idx.setdefault(cols[1].strip().lower(), []).append((float(cols[4]), float(cols[5]), int(cols[14] or 0)))
          except ValueError:
            continue
    gn_bad = []
    for city in arg0_entries:
      pop = city.get("population") if isinstance(city.get("population"), dict) else {}
      mx = max([float(v or 0) for v in pop.values()] or [0.0])
      coords = city.get("coords")
      if mx >= 100000 and isinstance(coords, list) and len(coords) >= 2:
        nm = str(city.get("name") or "").strip().lower()
        cands = gn_idx.get(nm) or []
        if cands and not any(_haversine_km(float(coords[0]), float(coords[1]), gla, glo) <= 50.0 for gla, glo, _ in cands):
          gn_bad.append(f"{city.get('key')} (max_pop={int(mx)})")
    if gn_bad:
      errors.append(f"[HOMONYM] High-population >=100k entry/entries absent within 50 km in GeoNames ({len(gn_bad)}): {gn_bad[:5]}")

  return errors, warnings


def audit_subregion_era_matrix(arg0_entries, arg1_mask_png, arg2_ledger_obj=None):
  """Cross-tabulates settlements against sibling areal-mask RGB zones across historical eras to catch unenriched sub-regions."""
  errors = []
  warnings = []
  if not arg1_mask_png or not os.path.isfile(arg1_mask_png) or not arg0_entries:
    return errors, warnings

  cfg_path = re.sub(r"_areal_mask\.png$", ".json5", arg1_mask_png, flags=re.IGNORECASE)
  if not os.path.isfile(cfg_path):
    return errors, warnings

  try:
    cfg = load_json_or_json5(cfg_path)
  except Exception:
    return errors, warnings

  sub_list = []
  for k in ("regions", "subregions", "sub_regions", "zones"):
    val_k = cfg.get(k)
    if isinstance(val_k, list):
      sub_list = [x for x in val_k if isinstance(x, dict)]
      break
    if isinstance(val_k, dict):
      sub_list = [{"id": rk, **rv} for rk, rv in val_k.items() if isinstance(rv, dict)]
      break
  if len(sub_list) < 2:
    return errors, warnings

  arr = np.asarray(Image.open(arg1_mask_png).convert("RGBA"), dtype=np.uint8)
  h, w = arr.shape[:2]
  valid = (arr[:, :, 3] > 0) & ((arr[:, :, :3].sum(axis=2)) > 0)

  sat_obj = (arg2_ledger_obj.get("saturation_audit") or {}) if isinstance(arg2_ledger_obj, dict) else {}
  exempt_zones = {
    str(z).strip().lower()
    for z in (sat_obj.get("unurbanised_zones") or sat_obj.get("exempt_subregions") or [])
  }

  rgb_to_zone = {}
  zone_px = {}
  for sub in sub_list:
    zid = str(sub.get("id") or sub.get("name") or "")
    rgb = sub.get("rgb") or sub.get("color") or sub.get("colour")
    if zid and isinstance(rgb, list) and len(rgb) >= 3:
      t = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
      px_cnt = int((valid & (arr[:, :, 0] == t[0]) & (arr[:, :, 1] == t[1]) & (arr[:, :, 2] == t[2])).sum())
      if px_cnt >= 40:
        rgb_to_zone[t] = zid
        zone_px[zid] = px_cnt

  if len(zone_px) < 2:
    return errors, warnings

  zone_total = {z: 0 for z in zone_px}
  zone_pre1900 = {z: 0 for z in zone_px}
  any_pre1900 = False
  for city in arg0_entries:
    coords = city.get("coords")
    pop = city.get("population") if isinstance(city.get("population"), dict) else {}
    if not isinstance(coords, list) or len(coords) < 2:
      continue
    try:
      r = min(h - 1, max(0, int((90.0 - float(coords[0])) * h / 180.0)))
      c = min(w - 1, max(0, int((float(coords[1]) + 180.0) * w / 360.0)))
    except (TypeError, ValueError):
      continue
    px_rgb = (int(arr[r, c, 0]), int(arr[r, c, 1]), int(arr[r, c, 2]))
    zid = rgb_to_zone.get(px_rgb)
    if not zid:
      for dr in (-2, -1, 0, 1, 2):
        for dc in (-2, -1, 0, 1, 2):
          nr, nc = min(h - 1, max(0, r + dr)), min(w - 1, max(0, c + dc))
          cand_z = rgb_to_zone.get((int(arr[nr, nc, 0]), int(arr[nr, nc, 1]), int(arr[nr, nc, 2])))
          if cand_z:
            zid = cand_z
            break
        if zid:
          break
    if not zid:
      continue
    zone_total[zid] += 1
    has_pre = any(int(yk) <= 1900 and float(pv) > 0 for yk, pv in pop.items() if str(yk).lstrip("-").isdigit())
    if has_pre:
      zone_pre1900[zid] += 1
      any_pre1900 = True

  densities = [zone_total[z] / float(zone_px[z]) for z in zone_px if zone_total[z] > 0]
  med_dens = float(np.median(densities)) if densities else 0.0
  for zid, px_cnt in zone_px.items():
    if zid.lower() in exempt_zones:
      continue
    if zone_total[zid] == 0:
      errors.append(
        f"[SUBREGION_GAP] Inhabited mask sub-region `{zid}` ({px_cnt} px) has 0 settlements; enrich before closing Stage B."
      )
    elif any_pre1900 and zone_pre1900[zid] == 0 and sum(zone_pre1900.values()) >= 15:
      errors.append(
        f"[SUBREGION_ERA_GAP] Sub-region `{zid}` has {zone_total[zid]} settlement(s) overall but 0 historical (<= 1900AD) entries; scrape historical cadastres/monographs for this sub-region."
      )
    elif med_dens > 0.0 and (zone_total[zid] / float(px_cnt)) < 0.15 * med_dens and zone_total[zid] < 5:
      warnings.append(
        f"[SUBREGION_SPARSE] Sub-region `{zid}` has very sparse settlement density ({zone_total[zid]} across {px_cnt} px vs median {med_dens * px_cnt:.1f}); verify exhaustive local scraping."
      )

  return errors, warnings


def scan_ingestion_scripts(arg0_dir):
  """Scans regional `_shared` ingestion scripts for forbidden Top-N / truncation shortcuts."""
  errors = []
  if not arg0_dir or not os.path.isdir(arg0_dir):
    return errors
  for root, _dirs, files in os.walk(arg0_dir):
    if "_gis_cache" in root or "geojson" in root or "rasters" in root:
      continue
    for fn in sorted(files):
      if not fn.lower().endswith((".py", ".js")):
        continue
      fp = os.path.join(root, fn)
      try:
        txt = open(fp, "r", encoding="utf-8", errors="replace").read()
      except OSError:
        continue
      for pat, desc in SCRIPT_TRUNCATION_PATTERNS:
        if re.search(pat, txt, flags=re.IGNORECASE):
          errors.append(f"[SATURATION] Forbidden ingestion shortcut in {os.path.relpath(fp, arg0_dir)}: {desc}")
  return errors


def audit_saturation_ledger(arg0_ledger, arg1_entries, arg2_settlements_path, arg3_profiles=None, arg4_project_key=None):
  """Validates `saturation_audit`, per-jurisdiction scraping completeness and source provenance diversity."""
  errors = []
  if not isinstance(arg0_ledger, dict):
    errors.append("[SATURATION] Source ledger must be an object containing `saturation_audit` when --require-saturation is active.")
    return errors

  sat = arg0_ledger.get("saturation_audit")
  if not isinstance(sat, dict):
    errors.append("[SATURATION] Missing `saturation_audit` block in `_source_ledger.json5` (required for one-shot regional studies).")
    return errors

  caps = (arg3_profiles or {}).get("provenance_caps") or {}
  max_crowd_pop = float(caps.get("max_crowd_settlement_share", 0.20))
  max_crowd_ent = float(caps.get("max_crowd_settlement_entries_share", 0.30))
  crowd_re = re.compile(r"(?<![a-z0-9])(?:wikidata|osm|openstreetmap|overpass|geonames|wikipedia|zenodo)(?![a-z0-9])", re.IGNORECASE)

  waves = sat.get("waves")
  if not isinstance(waves, list) or len(waves) < 3:
    errors.append(f"[SATURATION] Expected >= 3 discovery waves in `saturation_audit.waves`, found {len(waves) if isinstance(waves, list) else 0}.")
  else:
    source_classes = {str(w.get("source_class") or "").strip() for w in waves if isinstance(w, dict) and w.get("source_class")}
    if len(source_classes) < 3:
      errors.append(f"[SATURATION] `saturation_audit.waves` covers only {len(source_classes)} source_class tier(s); need >= 3.")
    last_wave = waves[-1] if isinstance(waves[-1], dict) else {}
    prior_cum = int(last_wave.get("prior_cumulative_included") or 0)
    new_inc = int(last_wave.get("newly_included") or 0)
    if prior_cum <= 0:
      errors.append("[SATURATION] Terminal wave `prior_cumulative_included` must be > 0.")
    else:
      gain = float(new_inc) / prior_cum
      if gain > 0.02:
        errors.append(
          f"[SATURATION] Discovery loop stopped prematurely: terminal wave added {new_inc}/{prior_cum} ({gain*100:.2f}% > 2.0% saturation threshold)."
        )

  corpora = sat.get("exhausted_corpora")
  if not isinstance(corpora, list) or len(corpora) == 0:
    errors.append("[SATURATION] Missing `saturation_audit.exhausted_corpora` confirming 100% row ingestion per dataset.")
  else:
    total_corpus_rows = 0
    crowd_corpus_rows = 0
    non_crowd_corpora = 0
    for c in corpora:
      if not isinstance(c, dict):
        continue
      tot = int(c.get("total_rows_in_bounds") or 0)
      proc = int(c.get("rows_processed") or -1)
      if tot <= 0 or proc < tot:
        errors.append(f"[SATURATION] Corpus {c.get('name')!r} incomplete: processed {proc}/{tot} rows.")
      total_corpus_rows += max(0, proc)
      cname_str = f"{c.get('name', '')} {c.get('source_tier', '')} {c.get('url', '')}"
      if crowd_re.search(cname_str) or str(c.get("source_tier") or "").lower() == "global_crowd_wikidata_osm":
        crowd_corpus_rows += max(0, proc)
      else:
        non_crowd_corpora += 1
    if non_crowd_corpora == 0:
      errors.append("[PROVENANCE] `exhausted_corpora` relies exclusively on global crowd/fallback sources (Wikidata/OSM/GeoNames/Zenodo); scrape national censuses, cadastres and monographs.")
    elif total_corpus_rows > 0 and (float(crowd_corpus_rows) / total_corpus_rows) > max_crowd_ent:
      errors.append(
        f"[PROVENANCE] Global crowd/fallback rows ({crowd_corpus_rows}/{total_corpus_rows} = {100.0 * crowd_corpus_rows / total_corpus_rows:.1f}%) exceed cap (<= {max_crowd_ent * 100:.0f}%)."
      )

  # Per-jurisdiction scraping & historical demography coverage verification
  jur_cov = sat.get("jurisdiction_coverage") or arg0_ledger.get("jurisdiction_coverage")
  if isinstance(jur_cov, dict) and jur_cov:
    for jid, jinfo in jur_cov.items():
      if not isinstance(jinfo, dict):
        continue
      prim_sources = jinfo.get("primary_sources") or jinfo.get("census_cadastre_sources") or []
      demo_lit = jinfo.get("demography_literature") or jinfo.get("papers") or []
      crowd_share = jinfo.get("crowd_fallback_share")
      if not isinstance(prim_sources, list) or len(prim_sources) == 0:
        errors.append(
          f"[JURISDICTION_SCRAPE] Jurisdiction `{jid}` lacks scraped primary census/cadastre/national registry sources in `jurisdiction_coverage`."
        )
      elif all(crowd_re.search(str(s)) for s in prim_sources):
        errors.append(
          f"[JURISDICTION_SCRAPE] Jurisdiction `{jid}` lists only global crowd/fallback sources ({prim_sources}); scrape national/regional sources."
        )
      if isinstance(demo_lit, list) and len(demo_lit) == 0 and "demography_literature" in jinfo:
        errors.append(
          f"[JURISDICTION_LIT] Jurisdiction `{jid}` has 0 archived historical demography/population papers recorded."
        )
      if crowd_share is not None and float(crowd_share) > max_crowd_pop:
        errors.append(
          f"[JURISDICTION_PROVENANCE] Jurisdiction `{jid}` crowd/global fallback share is {float(crowd_share)*100:.1f}% (> {max_crowd_pop*100:.0f}% ceiling)."
        )
    if arg4_project_key and sat.get("scope") == "project":
      matrix = ((arg3_profiles or {}).get("jurisdiction_source_matrix") or {}).get(arg4_project_key, {})
      req_jurs = [str(r.get("id")) for r in (matrix.get("required_jurisdictions") or []) if isinstance(r, dict) and r.get("id")]
      missing_jurs = [j for j in req_jurs if j not in jur_cov]
      if missing_jurs:
        errors.append(
          f"[JURISDICTION_SCRAPE] Project `{arg4_project_key}` `jurisdiction_coverage` omits required jurisdiction(s): {missing_jurs}."
        )
  elif sat.get("require_jurisdiction_coverage") is not False:
    errors.append(
      "[JURISDICTION_SCRAPE] Missing `saturation_audit.jurisdiction_coverage` mapping proving every constituent country/jurisdiction had primary national/regional sources scraped."
    )

  if sat.get("submask_coverage_complete") is not True:
    submask_cov = sat.get("submask_coverage")
    if isinstance(submask_cov, dict) and submask_cov:
      empty_masks = [k for k, v in submask_cov.items() if int(v or 0) <= 0]
      if empty_masks:
        errors.append(f"[SATURATION] Inhabited sub-region mask(s) have 0 settlements: {empty_masks}")
    else:
      errors.append("[SATURATION] Missing `submask_coverage` map in `saturation_audit`.")

  return errors


def audit_settlements(arg0_paths, arg1_ledger_path=None, arg2_require_sources=False, arg3_mode=None, arg4_options=None):
  """Validates regional `_settlements.json` or compiled Stadestér 2.0 shard(s)."""
  options = arg4_options or {}
  errors = []
  warnings = []
  resolved_mode = resolve_audit_mode(arg0_paths, arg3_mode, arg2_require_sources)
  svea_root = find_svea_root(arg0_paths[0] if arg0_paths else ".")

  entries = []
  for spath in arg0_paths:
    if not os.path.isfile(spath):
      errors.append(f"Settlements file not found: {spath}")
      continue
    data = load_json_or_json5(spath)
    if isinstance(data, dict):
      entries.extend({"key": k, **v} for k, v in data.items() if isinstance(v, dict))
    elif isinstance(data, list):
      entries.extend(x for x in data if isinstance(x, dict))
    else:
      errors.append(f"Unsupported top-level settlements structure in {spath}")

  if errors and not entries:
    return errors, warnings, {}

  count = len(entries)
  if count == 0:
    errors.append("Settlement gazetteer is empty (0 settlements).")

  by_key = {}
  bad_coords = 0
  corrupt_names = 0
  zero_pop_cities = 0
  legacy_type_cities = 0
  missing_sources_cities = 0
  invalid_sources_cities = 0
  viscount_regional_keys = 0
  max_year = -99999

  for idx, city in enumerate(entries):
    cname = city.get("name") or city.get("key") or f"entry_{idx}"
    ckey = str(city.get("key") or cname)
    by_key[ckey] = city

    if "_viscount_regional" in ckey or ckey.endswith("viscount_regional"):
      viscount_regional_keys += 1
      if viscount_regional_keys <= 5:
        errors.append(f"Forbidden key suffix '_viscount_regional' in key {ckey!r} (index {idx}).")

    if is_corrupt_name(str(cname), arg1_allow_backtick=(resolved_mode == "compiled")):
      corrupt_names += 1
      if corrupt_names <= 5:
        errors.append(f"Corrupted city name detected at index {idx}: {cname!r}")

    has_legacy_type, missing_sources, source_error = validate_city_sources(
      city, ckey, idx, resolved_mode, arg2_require_sources
    )
    if has_legacy_type:
      legacy_type_cities += 1
      if legacy_type_cities <= 5:
        errors.append(f"Legacy 'type' key detected on settlement {ckey!r} at index {idx}; replace with 'sources' list.")
    if missing_sources:
      missing_sources_cities += 1
      if missing_sources_cities <= 5:
        errors.append(f"Missing required 'sources' list on settlement {ckey!r} at index {idx}.")
    if source_error:
      invalid_sources_cities += 1
      if invalid_sources_cities <= 5:
        errors.append(source_error)

    coords = city.get("coords")
    if not isinstance(coords, list) or len(coords) < 2:
      bad_coords += 1
    else:
      try:
        lat = float(coords[0])
        lng = float(coords[1])
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
          bad_coords += 1
      except (TypeError, ValueError):
        bad_coords += 1

    pop = city.get("population")
    if not isinstance(pop, dict) or len(pop) == 0:
      zero_pop_cities += 1
    else:
      valid_pos = 0
      for yk, pv in pop.items():
        try:
          yi = int(yk)
          fv = float(pv)
          if fv > 0:
            valid_pos += 1
            if yi > max_year:
              max_year = yi
          elif resolved_mode == "regional":
            errors.append(f"Non-positive population {pv!r} at year {yk!r} in regional settlement {ckey!r}.")
            break
        except (TypeError, ValueError):
          pass
      if valid_pos == 0:
        zero_pop_cities += 1

  if viscount_regional_keys > 5:
    errors.append(f"Total keys containing '_viscount_regional': {viscount_regional_keys}")
  if bad_coords > 0:
    errors.append(f"{bad_coords} settlement(s) have missing or out-of-range coordinates.")
  if corrupt_names > 5:
    errors.append(f"Total corrupted city names: {corrupt_names}")
  if legacy_type_cities > 5:
    errors.append(f"Total settlements with legacy 'type' key: {legacy_type_cities}")
  if missing_sources_cities > 5:
    errors.append(f"Total settlements missing required 'sources' list: {missing_sources_cities}")
  if invalid_sources_cities > 5:
    errors.append(f"Total settlements with invalid 'sources' list: {invalid_sources_cities}")
  if zero_pop_cities > 0:
    if resolved_mode == "compiled":
      warnings.append(f"{zero_pop_cities} settlement(s) lack positive population year observations.")
    else:
      errors.append(f"{zero_pop_cities} settlement(s) lack positive population year observations.")

  # Auto-discover sibling areal mask if not explicitly provided
  primary_path = arg0_paths[0]
  mask_png = options.get("mask")
  if not mask_png and resolved_mode == "regional":
    stem = re.sub(r"_settlements\.json$", "", os.path.basename(primary_path))
    cand_mask = os.path.join(os.path.dirname(primary_path), f"{stem}_areal_mask.png")
    if os.path.isfile(cand_mask):
      mask_png = cand_mask

  ledger_stats = {"total_candidates": 0, "included": 0, "excluded": 0, "unaccounted": 0}
  ledger_obj = None
  if arg1_ledger_path:
    if not os.path.isfile(arg1_ledger_path):
      errors.append(f"Required source ledger missing: {arg1_ledger_path}")
    else:
      ledger_obj = load_json_or_json5(arg1_ledger_path)
      candidates = ledger_obj.get("candidates", []) if isinstance(ledger_obj, dict) else ledger_obj
      if not isinstance(candidates, list) or len(candidates) == 0:
        errors.append(f"Source ledger has no candidate entries: {arg1_ledger_path}")
      else:
        ledger_stats["total_candidates"] = len(candidates)
        for cand in candidates:
          status = str(cand.get("status", "")).strip().lower()
          ckey = str(cand.get("settlement_key") or cand.get("key") or cand.get("name") or "")
          justif = str(cand.get("justification", "")).strip()
          if status == "included":
            ledger_stats["included"] += 1
            if ckey not in by_key and not any(
              str(e.get("name", "")).strip().lower() == str(cand.get("name", "")).strip().lower()
              for e in entries
            ):
              errors.append(f"Ledger marks {ckey!r} as included, but it is absent from {os.path.basename(primary_path)}.")
          elif status == "excluded":
            ledger_stats["excluded"] += 1
            reason = str(cand.get("reason", "")).strip()
            if reason not in VALID_EXCLUDE_REASONS or len(justif) < 8:
              errors.append(f"Excluded candidate {ckey!r} lacks a valid reason ({VALID_EXCLUDE_REASONS}) or justification.")
            if DUMMY_EXCLUSION_PAT.search(ckey) or DUMMY_EXCLUSION_PAT.search(str(cand.get("name", ""))):
              errors.append(f"[GUARDRAIL] Synthetic catch-all exclusion placeholder detected in ledger: {ckey!r}.")
          else:
            ledger_stats["unaccounted"] += 1
            errors.append(f"Candidate {ckey!r} in ledger has invalid or pending status: {status!r}")
  elif count in {100, 120, 150, 200, 250} and resolved_mode != "compiled":
    errors.append(f"Settlement count ({count}) lands on a round quota cap without a verified _source_ledger.json5.")
  elif resolved_mode == "regional":
    warnings.append("No --ledger supplied; verified structural validity only.")

  # Anti-stub guardrails in regional mode
  mask_c14_sites = None
  if resolved_mode == "regional" and not options.get("skip_baseline"):
    if count < 35:
      errors.append(
        f"[GUARDRAIL] Regional gazetteer contains only {count} settlements (< 35 anti-stub floor; "
        "goal is 100% exhaustive regional coverage - POLARIS baseline is 148-281 pre-modern and 3.694-8.053 census)."
      )
    if mask_png:
      mask_c14_sites = count_c14_sites_in_mask(svea_root, mask_png)
      if mask_c14_sites is not None and max_year <= 1700:
        cand_floor = min(120, max(40, int(0.15 * mask_c14_sites)))
        obs_cands = ledger_stats["total_candidates"] if arg1_ledger_path else count
        if obs_cands < cand_floor and count < cand_floor:
          errors.append(
            f"[GUARDRAIL] Pre-modern basin/region has {mask_c14_sites} unique c14_cleaned_dedup sites inside "
            f"{os.path.basename(mask_png)}, yet ledger/gazetteer records only {obs_cands} candidate(s) (< {cand_floor} floor)."
          )

  profiles = load_skill_profiles(svea_root)
  proj_key, proj_defaults = infer_project_from_paths(arg0_paths, svea_root)

  if options.get("require_saturation") and resolved_mode == "regional":
    if ledger_obj is None:
      errors.append("[SATURATION] --require-saturation requires --ledger <_source_ledger.json5>.")
    else:
      errors.extend(audit_saturation_ledger(ledger_obj, entries, primary_path, profiles, proj_key))
    if mask_png:
      sm_errs, sm_warns = audit_subregion_era_matrix(entries, mask_png, ledger_obj)
      errors.extend(sm_errs)
      warnings.extend(sm_warns)

  # Script truncation scanner in regional mode or explicit --scan-scripts
  scan_dir = options.get("scan_scripts")
  if not scan_dir and resolved_mode == "regional" and not options.get("skip_script_scan"):
    # Check ancestor _shared folder if present
    cur = os.path.dirname(os.path.abspath(primary_path))
    for _ in range(4):
      shared_cand = os.path.join(cur, "_shared")
      if os.path.isdir(shared_cand):
        scan_dir = shared_cand
        break
      cur = os.path.dirname(cur)
  if scan_dir:
    errors.extend(scan_ingestion_scripts(scan_dir))

  opts_merged = dict(options)
  if not opts_merged.get("modern_census_year"):
    opts_merged["modern_census_year"] = proj_defaults.get("default_modern_census_year", 1850)

  u_errs, u_warns = audit_universal_gazetteer_anomalies(entries, resolved_mode, profiles, opts_merged)
  errors.extend(u_errs)
  warnings.extend(u_warns)

  temporal_stats = {}
  run_temporal = options.get("audit_temporal_density") or (resolved_mode == "compiled" and not options.get("skip_temporal_density"))
  if run_temporal:
    t_errs, t_warns, temporal_stats = audit_temporal_density_and_universe(entries, resolved_mode)
    errors.extend(t_errs)
    warnings.extend(t_warns)

  run_spatial = options.get("audit_spatial_bounds") or (resolved_mode == "compiled" and not options.get("skip_spatial_bounds"))
  if run_spatial:
    s_errs, s_warns = audit_spatial_bounds(entries, svea_root, options.get("mask"), profiles, proj_defaults)
    errors.extend(s_errs)
    warnings.extend(s_warns)

  stats = {
    "settlements_count": count,
    "viscount_regional_keys": viscount_regional_keys,
    "bad_coords": bad_coords,
    "corrupt_names": corrupt_names,
    "zero_pop_cities": zero_pop_cities,
    "legacy_type_cities": legacy_type_cities,
    "missing_sources_cities": missing_sources_cities,
    "invalid_sources_cities": invalid_sources_cities,
    "mask_c14_sites": mask_c14_sites,
    "mode": resolved_mode,
    **ledger_stats,
    **temporal_stats,
  }
  return errors, warnings, stats


def main():
  parser = argparse.ArgumentParser(description="Verify exhaustive Viscount settlement gazetteer inclusion & saturation.")
  parser.add_argument("settlements", nargs="+", help="Path(s) to *_settlements.json or compiled Stadestér 2.0 shard(s)")
  parser.add_argument("--ledger", default=None, help="Path to *_source_ledger.json5")
  parser.add_argument("--require-sources", action="store_true", help="Require non-empty 'sources' array on every settlement.")
  parser.add_argument("--mode", choices=["regional", "compiled"], default=None, help="Validation mode ('regional' or 'compiled').")
  parser.add_argument("--require-saturation", action="store_true", help="Enforce multi-wave saturation_audit ledger verification.")
  parser.add_argument("--scan-scripts", default=None, help="Directory of ingestion scripts to scan for Top-N truncation shortcuts.")
  parser.add_argument("--mask", default=None, help="Regional 4320x2160 areal mask PNG for spatial point-in-mask verification.")
  parser.add_argument("--modern-census-year", type=int, default=None, help="Override modern census anchor year for close-pair duplicate checks.")
  parser.add_argument("--check-close-pairs", action="store_true", help="Enforce same-country <= 1.5 km duplicate check even in regional mode.")
  parser.add_argument("--geonames-audit", default=None, help="Optional path to GeoNames TSV dump for >= 100k homonym cross-audit.")
  parser.add_argument("--audit-temporal-density", action="store_true", help="Enforce decennial continuity & pre-1995 universe capture.")
  parser.add_argument("--audit-spatial-bounds", action="store_true", help="Enforce point-in-polygon sovereign bounds check.")
  parser.add_argument("--skip-baseline", action="store_true", help="Skip regional anti-stub baseline floors (unit-testing only).")
  parser.add_argument("--skip-temporal-density", action="store_true", help="Skip temporal density continuity check.")
  parser.add_argument("--skip-spatial-bounds", action="store_true", help="Skip point-in-polygon spatial check.")
  parser.add_argument("--skip-script-scan", action="store_true", help="Skip automatic _shared script truncation scan.")
  parsed = parser.parse_args()

  errors, warnings, stats = audit_settlements(
    parsed.settlements,
    parsed.ledger,
    parsed.require_sources,
    parsed.mode,
    vars(parsed),
  )
  for w in warnings[:40]:
    print(f"[WARN] {w}")
  for e in errors[:40]:
    print(f"[FAIL] {e}", file=sys.stderr)

  print(f"[verify_gazetteer_exhaustiveness] Summary: {json.dumps(stats)}")
  sys.exit(1 if errors else 0)


if __name__ == "__main__":
  main()
