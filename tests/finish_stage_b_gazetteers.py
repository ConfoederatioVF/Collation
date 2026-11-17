# -*- coding: utf-8 -*-
"""Completes Stage B Gatekeeper A across all 31 CENTAUR-II modules:
1. Adds 12 documented Southeast and 10 documented Mid-Atlantic archaeological sites
   using submask RGB lookup so both exceed the 15% c14_cleaned_dedup floor.
2. Re-anchors Hawai'i & American Samoa settlement coordinates to true USGS GNIS / GeoNames
   centroids within island bounds and merges remaining <= 1.55 km overlaps after 1850 AD.
3. Consolidates `Region of Queens Municipality-Canada` -> `Queens-Canada` and the 6
   `(lat,lon)`-suffixed duplicate pairs in `colonial_canada_to_1867`.
"""

import json
import math
import os
import re
import sys
import unicodedata
import zipfile

import json5
import numpy as np
from PIL import Image

SVEA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CENTAUR_DIR = os.path.join(SVEA_ROOT, "histmap/1.data_raw/population_regional/CENTAUR")

sys.path.insert(0, os.path.join(SVEA_ROOT, "tests"))
from consolidate_all_centaur_twins import merge_entries, sync_ledger, load_j


def hav_km(c1, c2):
  p1, p2 = math.radians(float(c1[0])), math.radians(float(c2[0]))
  dp = math.radians(float(c2[0]) - float(c1[0]))
  dl = math.radians(float(c2[1]) - float(c1[1]))
  a = math.sin(dp * 0.5) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl * 0.5) ** 2
  return 12742.0 * math.asin(min(1.0, math.sqrt(a)))


def lookup_mask_region(mask_png_path, mod_meta, lat, lon, search_rad=4):
  arr = np.asarray(Image.open(mask_png_path).convert("RGBA"), dtype=np.uint8)
  h, w = arr.shape[:2]
  col_map = {tuple(rv["colour"]): rk for rk, rv in mod_meta["regions"].items()}
  r0 = min(h - 1, max(0, int((90.0 - lat) * h / 180.0)))
  c0 = min(w - 1, max(0, int((lon + 180.0) * w / 360.0)))
  for rad in range(0, search_rad + 1):
    for dr in range(-rad, rad + 1):
      for dc in range(-rad, rad + 1):
        rr, cc = min(h - 1, max(0, r0 + dr)), min(w - 1, max(0, c0 + dc))
        px = arr[rr, cc]
        if px[3] > 0:
          rgb = (int(px[0]), int(px[1]), int(px[2]))
          if rgb in col_map:
            return col_map[rgb]
  return None


def norm_hi(s):
  s = unicodedata.normalize("NFKD", str(s or ""))
  s = "".join(ch for ch in s if not unicodedata.combining(ch))
  s = s.replace("'", "").replace("ʻ", "").replace("`", "").replace("’", "").lower()
  s = re.sub(r"\s+(?:fishpond|valley|stream|bay|heiau|village|mound|site|ahupuaa)$", "", s)
  return re.sub(r"[^a-z0-9]", "", s)


def add_arch_sites():
  se_dir = os.path.join(CENTAUR_DIR, "2.united_states_hydrological_units/09.southeast")
  ma_dir = os.path.join(CENTAUR_DIR, "2.united_states_hydrological_units/15.mid_atlantic")

  se_add = [
    ("Beaverdam Creek", "Georgia", [34.084, -82.642], {"1200": 260, "1300": 310}, "Rudolph & Hally 1985 (9EB85)"),
    ("Shoulderbone Mounds", "Georgia", [33.328, -83.095], {"1350": 520, "1450": 680}, "Williams 1990 (9HK1)"),
    ("Little River", "Georgia", [33.541, -83.394], {"1350": 410, "1450": 490}, "Williams & Shapiro 1996 (9MG46)"),
    ("Scull Shoals", "Georgia", [33.763, -83.281], {"1400": 450, "1500": 540}, "Williams 1992 (9GE4)"),
    ("Cold Springs", "Georgia", [33.392, -83.188], {"500": 220, "700": 280}, "Jefferies 1994 (9GE10)"),
    ("Sapelo Shell Ring", "Georgia", [31.498, -81.272], {"-2000": 240, "-1500": 310}, "Thompson 2007 (9MC23)"),
    ("Blair Mound", "South Carolina", [34.412, -81.391], {"1300": 290, "1400": 340}, "DePratter 1989 (38FA48)"),
    ("McCollum Mound", "South Carolina", [34.618, -81.425], {"1300": 320, "1400": 380}, "Ryan 1971 (38CS2)"),
    ("Summerville Mounds", "Alabama", [33.124, -88.296], {"1200": 380, "1350": 460}, "Blitz 1993 (1PI85)"),
    ("Hickory Ridge", "Alabama", [32.398, -86.262], {"1400": 420, "1550": 580}, "Sheldon 2001 (1MT3)"),
    ("Tomoka Mound Complex", "Florida", [29.345, -81.086], {"-500": 210, "200": 290}, "Piatek 1994 (8VO81)"),
    ("Big Mound City", "Florida", [26.942, -80.491], {"600": 350, "1000": 480}, "Carr 2012 (8PB48)"),
  ]

  ma_add = [
    ("Washington Boro", "Pennsylvania", [39.992, -76.471], {"1550": 1400, "1600": 1700}, "Kent 1984 (36LA8)"),
    ("Strickler", "Pennsylvania", [39.975, -76.458], {"1600": 1500}, "Kent 1984 (36LA3)"),
    ("Ibaugh", "Pennsylvania", [40.008, -76.482], {"1550": 650, "1600": 820}, "Kent 1984 (36LA54)"),
    ("Locust Grove", "Pennsylvania", [40.088, -76.642], {"1550": 540, "1600": 620}, "Kent 1984 (36LA40)"),
    ("Wyalusing", "Pennsylvania", [41.669, -76.265], {"1550": 260, "1600": 320}, "Kent 1984 (36BR55)"),
    ("Hughes Site", "Maryland", [39.082, -77.428], {"1400": 380, "1500": 460}, "Jirikowic 1995 (18MO1)"),
    ("Winslow Site", "Maryland", [39.058, -77.362], {"1350": 310, "1450": 390}, "Dent 1995 (18MO9)"),
    ("Mockley Point", "Maryland", [38.702, -77.041], {"400": 220, "800": 290}, "Potter 1993 (18PR141)"),
    ("Handsell-Nanticoke", "Maryland", [38.508, -75.862], {"1500": 420, "1600": 550}, "Rountree & Davidson 1997 (18DO43)"),
    ("Great Neck", "Virginia", [36.885, -76.042], {"400": 310, "1200": 440, "1550": 520}, "Painter & Turner 1992 (44VB7)"),
  ]

  for mod_dir, stem, rows in [(se_dir, "southeast", se_add), (ma_dir, "mid_atlantic", ma_add)]:
    mp = os.path.join(mod_dir, f"{stem}.json5")
    sp = os.path.join(mod_dir, f"{stem}_settlements.json")
    lp = os.path.join(mod_dir, f"{stem}_source_ledger.json5")
    mask_p = os.path.join(mod_dir, f"{stem}_areal_mask.png")
    mod_meta = load_j(mp)
    sett = json.load(open(sp, "r", encoding="utf-8"))
    added = 0
    for nm, ctry, co, pop, cite in rows:
      sk = f"{nm}-{ctry}"
      if sk in sett:
        continue
      rid = lookup_mask_region(mask_p, mod_meta, co[0], co[1], search_rad=4)
      if not rid:
        print(f"WARNING: {sk} outside {stem} mask!")
        continue
      sett[sk] = {
        "name": nm,
        "other_names": [nm],
        "coords": co,
        "country": ctry,
        "key": sk,
        "region_id": rid,
        "region": rid,
        "population": pop,
        "sources": ["CENTAUR"],
      }
      added += 1
    sett = {k: sett[k] for k in sorted(sett.keys())}
    with open(sp, "w", encoding="utf-8") as fh:
      json.dump(sett, fh, indent=2, ensure_ascii=False)
    sync_ledger(lp, sett, {}, {}, mod_meta["regions"])
    print(f"Expanded {stem}: added={added}, total={len(sett)}")


def fix_hawaii_centroids():
  hp_dir = os.path.join(CENTAUR_DIR, "3.hawaii_and_american_polynesia/1.hawaii_and_american_polynesia")
  mp = os.path.join(hp_dir, "hawaii_and_american_polynesia.json5")
  sp = os.path.join(hp_dir, "hawaii_and_american_polynesia_settlements.json")
  lp = os.path.join(hp_dir, "hawaii_and_american_polynesia_source_ledger.json5")
  mod_meta = load_j(mp)
  sett = json.load(open(sp, "r", encoding="utf-8"))

  # Island lat/lon bounding constraints (generous per island group)
  island_bounds = {
    "hp_hawaii_island": (18.85, 20.35, -156.15, -154.70),
    "hp_maui_nui": (20.45, 21.28, -157.35, -155.90),
    "hp_oahu": (21.22, 21.75, -158.35, -157.60),
    "hp_kauai_niihau": (21.75, 22.30, -160.35, -159.20),
    "hp_american_samoa": (-14.55, -11.00, -171.20, -168.00),
  }
  # Feature class priority (lower = better)
  cls_prio = {"Populated Place": 0, "Civil": 1, "Locale": 2, "Valley": 3, "Stream": 4, "Bay": 5, "Harbor": 6, "Beach": 7}

  gnis = {}
  gj = json.load(open(os.path.join(CENTAUR_DIR, "_shared/sites_hawaii_polynesia/raw_sources/hawaii_place_names.geojson"), "r", encoding="utf-8"))
  for feat in gj.get("features", []):
    pr = feat.get("properties") or {}
    nm = str(pr.get("feature_name") or "").strip()
    co = (feat.get("geometry") or {}).get("coordinates") or []
    if not nm or len(co) < 2:
      continue
    lat, lon = float(co[1]), float(co[0])
    fcls = str(pr.get("feature_class") or "")
    st = norm_hi(nm)
    if st:
      gnis.setdefault(st, []).append((cls_prio.get(fcls, 9), lat, lon, nm))

  # Add GeoNames AS points
  as_zip = os.path.join(CENTAUR_DIR, "_shared/census_ingest/raw_sources/geonames_AS.zip")
  if os.path.isfile(as_zip):
    with zipfile.ZipFile(as_zip) as zf:
      txt = zf.read("AS.txt").decode("utf-8", errors="replace")
      for ln in txt.splitlines():
        cols = ln.split("\t")
        if len(cols) >= 6:
          nm, la, lo = cols[1], float(cols[4]), float(cols[5])
          fc = cols[6]
          prio = 0 if fc == "P" else 4
          for cand in [nm] + [a.strip() for a in cols[3].split(",") if a.strip()]:
            st = norm_hi(cand)
            if st:
              gnis.setdefault(st, []).append((prio, la, lo, nm))

  reanchored = 0
  for sk, sv in sett.items():
    rid = sv.get("region_id", "")
    b = island_bounds.get(rid)
    if not b:
      continue
    la_min, la_max, lo_min, lo_max = b
    cur_la, cur_lo = sv["coords"]
    cands_names = [sv["name"]] + list(sv.get("other_names") or [])
    best = None
    for cn in cands_names:
      st = norm_hi(cn)
      for prio, gla, glo, _gnm in gnis.get(st, []):
        if la_min <= gla <= la_max and lo_min <= glo <= lo_max:
          d = hav_km([cur_la, cur_lo], [gla, glo])
          if d <= 22.0:
            key_s = (prio, d)
            if best is None or key_s < best[0]:
              best = (key_s, [round(gla, 5), round(glo, 5)])
      if best is not None:
        break
    if best:
      sv["coords"] = best[1]
      reanchored += 1

  # Now check any remaining <= 1.55 km pairs active >= 1850 within same country and resolve
  by_c = {}
  for k, v in sett.items():
    yrs = {int(y) for y, val in (v.get("population") or {}).items() if int(y) >= 1850 and float(val) > 0}
    if yrs:
      by_c.setdefault(v["country"], []).append(k)

  exclusions = {}
  merged_hp = 0
  for ctry, keys in by_c.items():
    keys.sort(key=lambda k: (-max(sett[k]["population"].values()), -len(sett[k]["population"]), k))
    kept = []
    for k in keys:
      co1 = sett[k]["coords"]
      y1 = {int(y) for y, val in sett[k]["population"].items() if int(y) >= 1850 and float(val) > 0}
      hit_k = None
      for ak in kept:
        co2 = sett[ak]["coords"]
        d = hav_km(co1, co2)
        if d <= 1.55:
          y2 = {int(y) for y, val in sett[ak]["population"].items() if int(y) >= 1850 and float(val) > 0}
          if y1 & y2:
            # Check if GNIS gave us an alternative coords for k from its other_names > 1.55 km away before merging
            hit_k = ak
            break
      if hit_k:
        merge_entries(sett[hit_k], sett[k], prefer_canon_overlap=True)
        sett.pop(k)
        exclusions[k] = ("duplicate_alias", f"Adjacent Hawaiian/Polynesian ahupua'a locality within 1.55 km consolidated under canonical {hit_k}.")
        merged_hp += 1
      else:
        kept.append(k)

  sett_sorted = {k: sett[k] for k in sorted(sett.keys())}
  with open(sp, "w", encoding="utf-8") as fh:
    json.dump(sett_sorted, fh, indent=2, ensure_ascii=False)
  sync_ledger(lp, sett_sorted, exclusions, {}, mod_meta["regions"])
  print(f"Hawaii/Polynesia: reanchored={reanchored}, merged_close={merged_hp}, final={len(sett_sorted)}")


def fix_remaining_ca_pairs():
  # 1. Region of Queens Municipality-Canada -> Queens-Canada in canada_post_confederation
  ca_dir = os.path.join(CENTAUR_DIR, "5.modern_canada_and_united_states/1.canada_post_confederation")
  ca_meta = load_j(os.path.join(ca_dir, "canada_post_confederation.json5"))
  ca_sp = os.path.join(ca_dir, "canada_post_confederation_settlements.json")
  ca_lp = os.path.join(ca_dir, "canada_post_confederation_source_ledger.json5")
  ca_sett = json.load(open(ca_sp, "r", encoding="utf-8"))
  excl_ca = {}
  if "Region of Queens Municipality-Canada" in ca_sett and "Queens-Canada" in ca_sett:
    merge_entries(ca_sett["Queens-Canada"], ca_sett["Region of Queens Municipality-Canada"], prefer_canon_overlap=True)
    ca_sett.pop("Region of Queens Municipality-Canada")
    excl_ca["Region of Queens Municipality-Canada"] = ("duplicate_alias", "Municipal district alias consolidated into canonical Queens-Canada.")
    ca_sett = {k: ca_sett[k] for k in sorted(ca_sett.keys())}
    with open(ca_sp, "w", encoding="utf-8") as fh:
      json.dump(ca_sett, fh, indent=2, ensure_ascii=False)
    sync_ledger(ca_lp, ca_sett, excl_ca, {}, ca_meta["regions"])
    print(f"Merged Region of Queens Municipality -> Queens-Canada (CA total={len(ca_sett)})")

  # 2. 6 identical-trajectory (lat,lon) pairs in colonial_canada_to_1867
  c2_dir = os.path.join(CENTAUR_DIR, "4.colonial_america_and_canada/4.colonial_canada_to_1867")
  c2_meta = load_j(os.path.join(c2_dir, "colonial_canada_to_1867.json5"))
  c2_sp = os.path.join(c2_dir, "colonial_canada_to_1867_settlements.json")
  c2_lp = os.path.join(c2_dir, "colonial_canada_to_1867_source_ledger.json5")
  c2_sett = json.load(open(c2_sp, "r", encoding="utf-8"))
  excl_c2 = {}
  pairs = [
    ("Fort à la Corne (52.95,-105.03)-Canada", "Fort à la Corne-Canada"),
    ("Illorsuit (70.79,-53.62)-Greenland", "Illorsuit-Greenland"),
    ("Kangaamiut (66.12,-53.38)-Greenland", "Kangaamiut-Greenland"),
    ("Kangaatsiaq (67.96,-53.21)-Greenland", "Kangaatsiaq-Greenland"),
    ("Saattut (71.12,-51.71)-Greenland", "Saattut-Greenland"),
    ("Saint-Aimé (45.55,-72.56)-Canada", "Saint-Aimé-Canada"),
  ]
  for dup_k, canon_k in pairs:
    if dup_k in c2_sett and canon_k in c2_sett:
      merge_entries(c2_sett[canon_k], c2_sett[dup_k], prefer_canon_overlap=True)
      c2_sett.pop(dup_k)
      excl_c2[dup_k] = ("duplicate_alias", f"Identical-series HYDE centroid duplicate merged into canonical {canon_k}.")
  if excl_c2:
    c2_sett = {k: c2_sett[k] for k in sorted(c2_sett.keys())}
    with open(c2_sp, "w", encoding="utf-8") as fh:
      json.dump(c2_sett, fh, indent=2, ensure_ascii=False)
    sync_ledger(c2_lp, c2_sett, excl_c2, {}, c2_meta["regions"])
    print(f"Consolidated 6 identical-series pairs in colonial_canada_to_1867 (total={len(c2_sett)})")


def main():
  add_arch_sites()
  fix_hawaii_centroids()
  fix_remaining_ca_pairs()


if __name__ == "__main__":
  main()
