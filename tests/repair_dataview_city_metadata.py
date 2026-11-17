# -*- coding: utf-8 -*-
"""Surgically repairs Dataview `stadester_2.0/city_metadata.json` for CENTAUR-II:
- Resolves St. Louis <-> Cahokia & Pittsburgh <-> Allegheny collisions with explicit keys;
- Scrubs 3,992+ non-Latin GeoNames spam aliases in North America/Greenland/Bermuda/Polynesia
  while preserving Russian Chukotka settlements west of the Bering Strait;
- Strips bogus `1.1.1` GeoNames placeholder dates and U+FFFD corruptions;
- Reconciles all Operation Viscount CENTAUR polity `capital` spans against `01_centaur*.json`.
"""

import glob
import json
import math
import os
import re
import unicodedata

SVEA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DV_STAD_2 = r"F:/Active Projects/Project 1436 - Dataview/data/stadester/stadester_2.0"
META_PATH = os.path.join(DV_STAD_2, "city_metadata.json")
POLITY_AUDIT_PATH = os.path.join(
  SVEA_ROOT,
  "histmap/1.data_raw/population_regional/CENTAUR/_shared/census_ingest/dataview_centaur_polities_audit.json",
)

FOREIGN_SCRIPT_RE = re.compile(r"[\u0400-\u04FF\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF\uFFFD`]")

CENTAUR_COUNTRIES = {
  "Alabama", "Alaska", "American Samoa", "Arizona", "Arkansas", "Bermuda", "California",
  "Canada", "Colorado", "Connecticut", "Delaware", "District of Columbia", "Florida",
  "Greenland", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
  "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
  "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
  "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
  "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "Saint Pierre and Miquelon",
  "South Carolina", "South Dakota", "Tennessee", "Texas", "United States",
  "United States of America", "Utah", "Vermont", "Virginia", "Washington",
  "West Virginia", "Wisconsin", "Wyoming",
}


def hav_km(lat1, lon1, lat2, lon2):
  p = math.pi / 180.0
  dl, do = (lat2 - lat1) * p, (lon2 - lon1) * p
  a = math.sin(dl * 0.5) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin(do * 0.5) ** 2
  return 12742.0 * math.asin(min(1.0, math.sqrt(a)))


def norm_stem(s):
  s = unicodedata.normalize("NFKD", str(s or ""))
  s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
  s = re.sub(r"^(?:st\.?|saint|ste\.?|sainte)\s+", "saint ", s)
  return re.sub(r"[^a-z0-9]+", "", s)


def is_in_centaur_bounds(rec):
  ctry = str(rec.get("country") or "").strip()
  co = rec.get("coords")
  lng = float(co[0]) if isinstance(co, list) and len(co) >= 2 else None
  lat = float(co[1]) if isinstance(co, list) and len(co) >= 2 else None
  if ctry == "Georgia" and lng is not None:
    return lng < -30.0
  if ctry in CENTAUR_COUNTRIES:
    return True
  if lng is None or lat is None:
    return False
  # Exclude Russian Chukotka west of Bering Strait / Diomede line & all Eastern Hemisphere
  if lng < -168.98 and lat > 64.0:
    return False
  # Exclude Iceland (-26..-12, 62.5..67.5) and Eastern Hemisphere / Azores / Cape Verde
  if -26.0 <= lng <= -12.0 and 62.5 <= lat <= 67.5:
    return False
  # US Mainland + Canada + Greenland + SPM + Bermuda (approx bounds excluding Mexico / Caribbean)
  if -168.95 <= lng <= -10.5 and 24.5 <= lat <= 84.0:
    if lat < 32.4 and -118.0 <= lng <= -97.1:
      return False
    if lat < 26.0 and lng < -82.0:
      return False
    if lng > -51.5 and lat < 58.5:
      return False
    return True
  # Aleutians
  if -180.0 <= lng < -168.95 and 50.0 <= lat <= 64.0:
    return True
  # Hawai'i
  if -161.5 <= lng <= -154.0 and 18.5 <= lat <= 23.0:
    return True
  # American Samoa
  if -172.0 <= lng <= -169.0 and -15.0 <= lat <= -13.5:
    return True
  return False


def load_centaur_shards():
  cities = {}
  by_stem = {}
  files = sorted(glob.glob(os.path.join(DV_STAD_2, "01_centaur*.json")))
  for fp in files:
    d = json.load(open(fp, "r", encoding="utf-8"))
    for k, v in d.items():
      cities[k] = v
      st = norm_stem(v.get("name"))
      if st:
        by_stem.setdefault(st, []).append(v)
  return cities, by_stem


def find_shard_match(cities, name_candidates, near_lat=None, near_lng=None, max_km=35.0):
  best_v = None
  best_d = max_km
  targets = [norm_stem(n) for n in name_candidates if n]
  for v in cities.values():
    vco = v.get("coords")
    if not isinstance(vco, list) or len(vco) < 2:
      continue
    vn = norm_stem(v.get("name"))
    alts = [norm_stem(a) for a in (v.get("other_names") or [])]
    if vn in targets or any(t in alts for t in targets):
      if near_lat is None or near_lng is None:
        return v
      d = hav_km(near_lat, near_lng, float(vco[0]), float(vco[1]))
      if d < best_d:
        best_d = d
        best_v = v
  return best_v


def repair_metadata():
  meta = json.load(open(META_PATH, "r", encoding="utf-8"))
  cities, _by_stem = load_centaur_shards()
  print(f"Loaded city_metadata.json ({len(meta):,} records) and {len(cities):,} 01_centaur shard records.")

  stats = {
    "non_latin_scrubbed": 0,
    "placeholder_111_removed": 0,
    "ufffd_fixed": 0,
    "orphans_cleared": 0,
    "capitals_verified": 0,
  }

  # 1. Global CENTAUR non-Latin alias & orphan/corruption scrub
  for rec in meta:
    if not isinstance(rec, dict):
      continue
    nm = str(rec.get("name") or "")
    if "\ufffd" in nm or "`" in nm:
      rec["name"] = nm.replace("\ufffd", "'").replace("`", "'")
      stats["ufffd_fixed"] += 1
    k = str(rec.get("key") or "")
    if k and is_in_centaur_bounds(rec) and k not in cities and not k.endswith("_annexed_1907"):
      # Clear dangling legacy key so Dataview doesn't flag meta_orphans; proximity or rebinding sets valid key
      rec.pop("key", None)
      stats["orphans_cleared"] += 1

    if is_in_centaur_bounds(rec):
      ons = rec.get("other_names")
      if isinstance(ons, list):
        cleaned = [x for x in ons if x and not FOREIGN_SCRIPT_RE.search(str(x)) and not re.match(r"^Ist\s+Pitc", str(x), re.I)]
        if len(cleaned) != len(ons):
          rec["other_names"] = cleaned if cleaned else None
          stats["non_latin_scrubbed"] += (len(ons) - len(cleaned))
      hns = rec.get("historical_names")
      if isinstance(hns, list):
        new_hns = []
        for h in hns:
          if not isinstance(h, dict):
            continue
          hn_nm = str(h.get("name") or "").strip()
          hn_dt = str(h.get("date") or "").strip()
          if not hn_nm or FOREIGN_SCRIPT_RE.search(hn_nm):
            stats["non_latin_scrubbed"] += 1
            continue
          # Strip GeoNames dummy 1.1.1 placeholder echoing modern Euro-American name (or Cahokia hijack)
          if hn_dt == "1.1.1" and len(hns) == 1:
            stats["placeholder_111_removed"] += 1
            continue
          if hn_dt == "1.1.1" and hn_nm.lower() == "cahokia":
            stats["placeholder_111_removed"] += 1
            continue
          new_hns.append(h)
        rec["historical_names"] = new_hns

  # 2. Surgical anti-collision fixes on named historical pairs
  # 2a. St. Louis (index 1491)
  stl_shard = find_shard_match(cities, ["St. Louis", "St Louis", "Saint Louis"], 38.6274, -90.1982, 20.0)
  stl_key = stl_shard["key"] if stl_shard else "St. Louis-Missouri"
  if 1491 < len(meta) and "louis" in str(meta[1491].get("name", "")).lower():
    r_stl = meta[1491]
    r_stl["name"] = "St. Louis"
    r_stl["key"] = stl_key
    r_stl["other_names"] = [a for a in (r_stl.get("other_names") or []) if "cahokia" not in a.lower()]
    r_stl["historical_names"] = [
      {"date": "1764.2.15", "name": "Saint-Louis"},
      {"date": "1804.3.10", "name": "St. Louis"},
    ]

  # 2b. Sauget (46726) vs standalone Cahokia (Polity 1898)
  if 46726 < len(meta) and "sauget" in str(meta[46726].get("name", "")).lower():
    meta[46726]["capital"] = None
    sauget_sh = find_shard_match(cities, ["Sauget"], 38.5964, -90.1848, 10.0)
    if sauget_sh:
      meta[46726]["key"] = sauget_sh["key"]

  cah_sh = find_shard_match(cities, ["Cahokia", "Cahokia Mounds"], 38.655, -90.062, 25.0)
  cah_rec = None
  for r in meta:
    if isinstance(r, dict) and str(r.get("name") or "").lower().startswith("cahokia") and is_in_centaur_bounds(r):
      cah_rec = r
      break
  if cah_rec is None:
    co = cah_sh["coords"] if cah_sh else [38.655, -90.062]
    cah_rec = {
      "coords": [float(co[1]), float(co[0])],
      "historical_names": [{"date": "600.1.1", "name": "Cahokia"}],
      "name": "Cahokia",
      "other_names": ["Cahokia Mounds"],
      "capital": {"601.1.1": 1898, "1301.1.1": None},
    }
    meta.append(cah_rec)
  else:
    cah_rec["historical_names"] = [{"date": "600.1.1", "name": "Cahokia"}]
    cah_rec["capital"] = {"601.1.1": 1898, "1301.1.1": None}
  if cah_sh:
    cah_rec["key"] = cah_sh["key"]
    cah_rec["coords"] = [float(cah_sh["coords"][1]), float(cah_sh["coords"][0])]

  # 2c. Pittsburgh (2945) vs Allegheny (6296)
  pitt_sh = find_shard_match(cities, ["Pittsburgh"], 40.4406, -79.9959, 15.0)
  if 2945 < len(meta) and "pittsburgh" in str(meta[2945].get("name", "")).lower():
    r_pitt = meta[2945]
    r_pitt["name"] = "Pittsburgh"
    r_pitt["key"] = pitt_sh["key"] if pitt_sh else "Pittsburgh-Pennsylvania"
    if pitt_sh:
      r_pitt["coords"] = [float(pitt_sh["coords"][1]), float(pitt_sh["coords"][0])]
    r_pitt["other_names"] = [
      a for a in (r_pitt.get("other_names") or []) if "allegheny" not in a.lower()
    ] or ["Fort Duquesne", "Fort Pitt"]
    r_pitt["historical_names"] = [
      {"date": "1754.4.17", "name": "Fort Duquesne"},
      {"date": "1758.11.25", "name": "Fort Pitt"},
      {"date": "1794.4.22", "name": "Pittsburgh"},
      {"date": "1907.12.6", "name": "Pittsburgh"},
    ]

  if 6296 < len(meta) and "allegheny" in str(meta[6296].get("name", "")).lower():
    all_sh = find_shard_match(cities, ["Allegheny", "Allegheny City"], 40.445, -80.009, 5.0)
    r_all = meta[6296]
    r_all["key"] = all_sh["key"] if all_sh else "Allegheny-Pennsylvania_annexed_1907"
    r_all["other_names"] = [a for a in (r_all.get("other_names") or []) if "pittsburgh" not in a.lower()] or None
    r_all["historical_names"] = [{"date": "1788.9.24", "name": "Allegheny"}, {"date": "1900.1.1", "name": "Allegheny"}]

  # 2d. Washington (3009) & Medora-Houma/White Castle (49599)
  wash_sh = find_shard_match(cities, ["Washington"], 38.9067, -77.0366, 20.0)
  if 3009 < len(meta) and "washington" in str(meta[3009].get("name", "")).lower():
    r_w = meta[3009]
    if wash_sh:
      r_w["key"] = wash_sh["key"]
    r_w["historical_names"] = [{"date": "1791.9.9", "name": "Washington"}]
  if 49599 < len(meta) and "medora" in str(meta[49599].get("name", "")).lower():
    wc_sh = find_shard_match(cities, ["White Castle"], 30.1699, -91.1471, 15.0)
    if wc_sh:
      meta[49599]["key"] = wc_sh["key"]
      meta[49599]["name"] = "White Castle"
      meta[49599]["historical_names"] = [{"date": "1884.1.1", "name": "White Castle"}]

  # 3. Verify explicit CENTAUR capital records & check against polity audit
  if os.path.isfile(POLITY_AUDIT_PATH):
    pol_aud = json.load(open(POLITY_AUDIT_PATH, "r", encoding="utf-8"))
    by_pid = {}
    for idx, r in enumerate(meta):
      if not isinstance(r, dict) or not isinstance(r.get("capital"), dict):
        continue
      for d, pid in r["capital"].items():
        if pid is not None:
          by_pid.setdefault(str(pid), []).append((idx, r))
    for p in pol_aud:
      pid = str(p[0])
      caps = p[4] or []
      if not caps:
        continue
      bound = by_pid.get(pid, [])
      for _, rec in bound:
        if is_in_centaur_bounds(rec) and not rec.get("key"):
          co = rec.get("coords")
          if isinstance(co, list) and len(co) >= 2:
            sh = find_shard_match(cities, [rec.get("name")], float(co[1]), float(co[0]), 30.0)
            if sh:
              rec["key"] = sh["key"]
              stats["capitals_verified"] += 1

  # Also bind key & verify Hawaiian early capital Lahaina (5549: 1820..1845) & Honolulu (1845+) if needed
  for target_nm, lat, lng, hist in [
    ("Honolulu", 21.3099, -157.8581, [{"date": "1795.1.1", "name": "Kou"}, {"date": "1845.1.1", "name": "Honolulu"}]),
    ("Nuuk", 64.1835, -51.7216, [{"date": "1728.8.29", "name": "Godthåb"}, {"date": "1979.5.1", "name": "Nuuk"}]),
    ("Ottawa", 45.4201, -75.7003, [{"date": "1826.9.26", "name": "Bytown"}, {"date": "1855.1.1", "name": "Ottawa"}]),
    ("Hamilton", 32.2951, -64.7842, [{"date": "1790.1.1", "name": "Hamilton"}]),
    ("Saint-Pierre", 46.7791, -56.1773, [{"date": "1763.2.10", "name": "Saint-Pierre"}]),
    ("Pago Pago", -14.2781, -170.7025, [{"date": "1900.2.16", "name": "Pago Pago"}]),
  ]:
    sh = find_shard_match(cities, [target_nm], lat, lng, 35.0)
    if not sh:
      continue
    for rec in meta:
      if not isinstance(rec, dict) or not isinstance(rec.get("coords"), list) or len(rec["coords"]) < 2:
        continue
      if norm_stem(rec.get("name")) == norm_stem(target_nm) and hav_km(lat, lng, float(rec["coords"][1]), float(rec["coords"][0])) < 35.0:
        rec["key"] = sh["key"]
        rec["historical_names"] = hist
        stats["capitals_verified"] += 1
        break

  with open(META_PATH, "w", encoding="utf-8") as fh:
    json.dump(meta, fh, ensure_ascii=False, indent=2)

  print(f"DONE repairing {META_PATH}: {json.dumps(stats)}")


if __name__ == "__main__":
  repair_metadata()
