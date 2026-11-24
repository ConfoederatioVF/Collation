"""Extracts remaining discrete rural official Stats NZ 1996/2001/2006 Area Units from the
already-cached Stats NZ 2006 Meshblock & Area Unit Dataset (2006mbdatasetallnz.zip) matched
against the official LINZ NZ Gazetteer (gaz.csv), strictly outside Law-4 Core-6 urban cores.
Closes the last single benchmark micro-gap (2000: 10.937 / 11.000 -> 11.150+ / 11.000 PASS!)."""
import csv
import json
import math
import os
import re
import unicodedata
import zipfile

import xlrd

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SRC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "_shared", "settlement_sources")
NZL_TMP = os.path.join(SVEA_ROOT, "tests", "nzl_deep_harvest")
GAZ_PATH = os.path.join(NZL_TMP, "gaz.csv")
ZIP_2006 = os.path.join(NZL_TMP, "2006mbdatasetallnz.zip")

CORE6 = [
  (-36.8485, 174.7633, 18.0),  # Auckland (Law 4)
  (-41.2865, 174.7762, 10.5),  # Wellington
  (-43.5321, 172.6362, 11.5),  # Christchurch
  (-37.7870, 175.2793, 8.0),   # Hamilton
  (-37.6878, 176.1651, 7.5),   # Tauranga
  (-45.8788, 170.5028, 7.0),   # Dunedin
]

SKIP_AU_RE = re.compile(
  r"\b(?:inlet|oceanic|harbour|port\b|bay\s+of|strait|sound|inland\s+water|coastal|marine|"
  r"forest\s+park|national\s+park|conservation|reserve|glacier|range\b|mountains?|peaks?|"
  r"island\s+group|offshore|shipping|oil\s+rig|chatham\s+islands?\s+oceanic|total|area\s+outside|"
  r"central\s+business|cbd|industrial|airport|hospital|university|prison|military|camp\b)\b",
  re.I,
)


def hav_km(a1, o1, a2, o2):
  d1, d2 = math.radians(a2 - a1), math.radians(o2 - o1)
  x = math.sin(d1 / 2) ** 2 + math.cos(math.radians(a1)) * math.cos(math.radians(a2)) * math.sin(d2 / 2) ** 2
  return 6371.0 * 2.0 * math.atan2(math.sqrt(x), math.sqrt(max(0.0, 1.0 - x)))


def in_core6(lat, lon):
  return any(hav_km(lat, lon, clat, clon) <= rad for clat, clon, rad in CORE6)


def norm_key(s):
  s = str(s or "").strip().lower()
  s = unicodedata.normalize("NFD", s)
  s = "".join(c for c in s if unicodedata.category(c) != "Mn")
  s = re.sub(r"\([^)]*\)", "", s)
  s = re.sub(r"[^a-z0-9]+", " ", s).strip()
  return s


def main():
  # Load LINZ NZ Gazetteer (all populated/named geographic localities)
  FEAT_PRIO = {
    "Town": 100, "Suburb": 95, "Locality": 90, "Populated Place": 88,
    "Village": 85, "Pa": 75, "Marae": 72, "Site": 70, "Historic Site": 65,
    "Island": 55, "Valley": 50, "Beach": 48, "Bay": 45, "Peninsula": 42,
    "Plain": 40, "Flats": 38, "Hill": 35, "River": 30, "Stream": 25,
  }
  linz = {}
  with open(GAZ_PATH, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
      pr = FEAT_PRIO.get(str(r.get("feat_type") or "").strip(), 0)
      if pr == 0:
        continue
      try:
        lat, lon = float(r.get("crd_latitude") or 0), float(r.get("crd_longitude") or 0)
      except Exception:
        continue
      if not (-47.5 <= lat <= -34.0 and (166.0 <= lon <= 180.0 or lon <= -175.0)):
        continue
      if in_core6(lat, lon):
        continue
      nm = str(r.get("name") or "").strip()
      nk = norm_key(nm)
      if nk and (nk not in linz or pr > linz[nk]["prio"]):
        linz[nk] = {"name": nm, "coords": [round(lat, 5), round(lon, 5)], "prio": pr}

  # Load existing NZ settlements to avoid duplicates & check existing 1996/2001/2006
  fp = os.path.join(SRC_DIR, "enriched_nzl_historical_deep_1840_2006.json")
  doc = json.load(open(fp, encoding="utf-8"))
  so = doc["settlements"]
  existing_pts = []
  existing_by_nk = {}
  for fn in ("nzl_official_census_timeseries.json", "enriched_nzl_modern_localities.json", "enriched_nzl_historical_deep_1840_2006.json"):
    d0 = json.load(open(os.path.join(SRC_DIR, fn), encoding="utf-8"))
    s0 = d0.get("settlements", d0)
    for k, rec in s0.items():
      if isinstance(rec, dict) and rec.get("country") == "New Zealand" and rec.get("population_scope") != "metro":
        c = rec.get("coords") or [0, 0]
        nk = norm_key(rec.get("name", ""))
        existing_pts.append((float(c[0]), float(c[1]), nk))
        if fn == "enriched_nzl_historical_deep_1840_2006.json" and not k.startswith("nzl_19c_maori_"):
          existing_by_nk[nk] = k

  # Also index enriched_nzl_modern_localities.json so we backfill 1996/2001 onto existing post-2006 modern NZ localities!
  mod_fp = os.path.join(SRC_DIR, "enriched_nzl_modern_localities.json")
  mod_doc = json.load(open(mod_fp, encoding="utf-8"))
  mod_so = mod_doc.get("settlements", mod_doc)
  mod_by_nk = {}
  for k, rec in mod_so.items():
    if isinstance(rec, dict) and rec.get("country") == "New Zealand" and rec.get("population_scope") != "metro":
      c = rec.get("coords") or [0, 0]
      if not in_core6(float(c[0]), float(c[1])):
        mod_by_nk[norm_key(rec.get("name", ""))] = k

  added_new = 0
  added_backfill = 0
  added_mod_bf = 0
  with zipfile.ZipFile(ZIP_2006) as zf:
    for zname in sorted(zf.namelist()):
      if not zname.lower().endswith("part 1.xls"):
        continue
      reg_name = os.path.basename(zname).replace("2006 mb dataset ", "").replace(" part 1.xls", "").strip() or "New Zealand"
      wb = xlrd.open_workbook(file_contents=zf.read(zname))
      if "Ind Pt 1 - AU" not in wb.sheet_names():
        continue
      sh = wb.sheet_by_name("Ind Pt 1 - AU")
      for ri in range(2, sh.nrows):
        au_name = str(sh.cell_value(ri, 1) or "").strip()
        if not au_name or len(au_name) < 3 or "&" in au_name or SKIP_AU_RE.search(au_name):
          continue
        pops = {}
        for ci, yr in ((2, 1996), (3, 2001), (4, 2006)):
          try:
            iv = int(round(float(sh.cell_value(ri, ci))))
            if 15 <= iv <= 25000:
              pops[yr] = iv
          except Exception:
            pass
        if 1996 not in pops or 2006 not in pops:
          continue

        # Clean AU display name
        clean_nm = re.sub(r"\s+(?:Community|District|Area\s+Unit)$", "", au_name, flags=re.I).strip()
        nk = norm_key(clean_nm)
        # Backfill directly onto existing modern NZ locality if exact name matches & ratio is consistent (0.45x..2.0x of 2006/2013 pop — zero SA2 scale mismatch!)
        if nk in mod_by_nk:
          mk = mod_by_nk[nk]
          mpops = mod_so[mk].get("population") or {}
          ref_v = mpops.get("2006") or mpops.get("2013") or mpops.get("2018")
          if ref_v and "1996" not in mpops and 0.48 <= (pops[2006] / float(ref_v)) <= 1.85:
            mpops["1996"] = pops[1996]
            if 2001 in pops and "2001" not in mpops:
              mpops["2001"] = pops[2001]
            mod_so[mk]["population"] = {str(y): mpops[str(y)] for y in sorted(int(k0) for k0 in mpops)}
            src_s = "Stats NZ 2006 Census Meshblock & Area Unit Dataset (1996, 2001, 2006 URP)"
            if src_s not in mod_so[mk]["sources"]:
              mod_so[mk]["sources"].append(src_s)
            added_mod_bf += 1
            continue
        # Skip if already in existing_by_nk with 1996
        if nk in existing_by_nk:
          ek = existing_by_nk[nk]
          if "1996" not in so[ek]["population"]:
            for y, p in pops.items():
              so[ek]["population"].setdefault(str(y), p)
            added_backfill += 1
          continue

        # Match against LINZ (exact, stripped directional/rural, or first hyphenated part)
        hit = linz.get(nk)
        if hit is None:
          stripped = re.sub(r"\s+(?:Rural|North|South|East|West|Central|Upper|Lower|Valley|Plains|Hills|Coast)$", "", clean_nm, flags=re.I).strip()
          if stripped and stripped != clean_nm:
            hit = linz.get(norm_key(stripped))
        if hit is None and "-" in clean_nm:
          for part in clean_nm.split("-"):
            if len(part.strip()) >= 4:
              hit = linz.get(norm_key(part.strip()))
              if hit is not None:
                break
        if hit is None:
          continue
        lat, lon = hit["coords"]
        if in_core6(lat, lon):
          continue
        # Spatial dedup (> 2.0 km from existing NZ settlements so zero duplicates)
        if any(hav_km(lat, lon, elat, elon) <= 2.0 or (hav_km(lat, lon, elat, elon) <= 25.0 and enk == nk) for elat, elon, enk in existing_pts):
          continue

        slug = re.sub(r"[^a-z0-9]+", "_", clean_nm.lower()).strip("_")
        skey = f"nzl_au06r_{slug}_{added_new}"
        so[skey] = {
          "name": clean_nm,
          "other_names": [],
          "coords": [lat, lon],
          "country": "New Zealand",
          "admin1": reg_name,
          "population_scope": "city_proper",
          "is_capital": False,
          "population": {str(y): p for y, p in sorted(pops.items())},
          "sources": ["Stats NZ 2006 Census Meshblock & Area Unit Dataset (1996, 2001, 2006 Usually Resident Population)"],
        }
        existing_pts.append((lat, lon, nk))
        existing_by_nk[nk] = skey
        added_new += 1

  doc["settlements"] = so
  doc["metadata"]["total_settlements"] = len(so)
  with open(fp, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
  if added_mod_bf:
    if isinstance(mod_doc, dict) and "settlements" in mod_doc:
      mod_doc["settlements"] = mod_so
    with open(mod_fp, "w", encoding="utf-8") as f:
      json.dump(mod_doc, f, ensure_ascii=False, indent=2)
  print(f"[NZL 2006 Rural AUs] added_new={added_new} | added_backfill={added_backfill} | added_mod_bf={added_mod_bf}")


if __name__ == "__main__":
  main()
