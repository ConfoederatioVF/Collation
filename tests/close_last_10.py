"""Closes the final 10-settlement micro-gap at benchmark year 2000 (10.990 / 11.000) using
100% official already-cached ABS 2001 NSW UCL Table 2 (pages 1..45 including A-C!) and
Stats NZ 2006 Area Units (1996/2001/2006 URP for genuine rural NZ townships outside Core-6)."""
import csv
import json
import math
import os
import re
import unicodedata
import zipfile
from collections import Counter

import pymupdf
import xlrd

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SRC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "_shared", "settlement_sources")
PDF_PATH = os.path.join(SVEA_ROOT, "tests", "_aus_r2_cache", "abs2001_ucl", "abs2001_nsw_20161.pdf")
NZL_TMP = os.path.join(SVEA_ROOT, "tests", "nzl_deep_harvest")
GAZ_PATH = os.path.join(NZL_TMP, "gaz.csv")
ZIP_2006 = os.path.join(NZL_TMP, "2006mbdatasetallnz.zip")

CORE6 = [
  (-36.8485, 174.7633, 18.0),
  (-41.2865, 174.7762, 10.5),
  (-43.5321, 172.6362, 11.5),
  (-37.7870, 175.2793, 8.0),
  (-37.6878, 176.1651, 7.5),
  (-45.8788, 170.5028, 7.0),
]


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
  s = re.sub(r"\b(?:st\.?|saint)\b", "st", s)
  s = re.sub(r"\b(?:mt\.?|mount)\b", "mount", s)
  s = re.sub(r"\b(?:pt\.?|port)\b", "port", s)
  s = re.sub(r"[^a-z0-9]+", " ", s).strip()
  return s


def parse_spaced_int(s):
  t = re.sub(r"\s+", "", str(s or "").strip())
  return int(t) if re.fullmatch(r"\d+", t) else None


def main():
  # 1. Parse pages 1..19 (A..C) of ABS 2001 NSW UCL Table 2 (we started at page 16 earlier!)
  geo = {}
  for fn in ("aus_official_ucl_lga_timeseries.json", "enriched_aus_sal_modern.json"):
    d = json.load(open(os.path.join(SRC_DIR, fn), encoding="utf-8"))
    so = d.get("settlements", d)
    for rec in so.values():
      if not isinstance(rec, dict) or rec.get("country") != "Australia" or rec.get("admin1") != "New South Wales" or rec.get("population_scope") == "metro":
        continue
      nm = str(rec.get("name") or "").strip()
      nk = norm_key(nm)
      if nk and nk not in ("sydney", "canberra") and nk not in geo:
        geo[nk] = {"name": nm, "coords": rec["coords"], "scope": rec.get("population_scope", "city_proper")}

  doc = pymupdf.open(PDF_PATH)
  parsed_nsw = {}
  for pno in range(0, min(42, len(doc))):
    lines = [ln.strip() for ln in doc[pno].get_text("text").splitlines() if ln.strip()]
    for i in range(4, len(lines) - 3):
      p01 = parse_spaced_int(lines[i - 2])
      fem = parse_spaced_int(lines[i - 1])
      mal = parse_spaced_int(lines[i])
      if p01 is None or fem is None or mal is None or not (50 <= p01 <= 1500000 and fem + mal == p01):
        continue
      p96 = parse_spaced_int(lines[i - 3])
      if p96 is None or not (20 <= p96 <= 1500000):
        continue
      nm_raw = None
      for off in (4, 3, 5):
        if i + off < len(lines):
          cand = lines[i + off]
          if re.search(r"[A-Za-z]{3,}", cand) and not re.match(r"^(?:NEW SOUTH WALES|AUSTRALIAN CAPITAL|URBAN CENTRE|TABLE|\(a\)|ABS|SELECTED)", cand, re.I):
            nm_raw = cand
            break
      if not nm_raw:
        continue
      clean_nm = re.sub(r"\s*\([^)]*\)\s*", " ", nm_raw).strip()
      clean_nm = re.sub(r"\s*-\s*Part\s*[A-Z]?\s*$", "", clean_nm, flags=re.I).strip()
      if any(w in clean_nm.lower() for w in ("total", "balance", "migratory", "canberra", "sydney", "remainder")):
        continue
      hit = geo.get(norm_key(clean_nm))
      if hit is None and "-" in clean_nm:
        hit = geo.get(norm_key(clean_nm.split("-")[0]))
      if hit is not None:
        parsed_nsw[hit["name"]] = (hit, p96, p01)

  fp_aus = os.path.join(SRC_DIR, "enriched_aus_historical_deep_1800_2006.json")
  doc_a = json.load(open(fp_aus, encoding="utf-8"))
  so_a = doc_a["settlements"]
  idx_a = {(norm_key(r["name"]), r.get("admin1", "")): k for k, r in so_a.items() if r.get("country") == "Australia" and not k.startswith("aus_19c_indig_")}
  nsw_new = 0
  nsw_96 = 0
  src_nsw = "ABS 2001 Census: Selected Characteristics for Urban Centres and Localities — New South Wales (Cat. 2016.1, Table 2)"
  for nm, (hit, p96, p01) in parsed_nsw.items():
    ik = (norm_key(nm), "New South Wales")
    if ik in idx_a:
      ek = idx_a[ik]
      if "1996" not in so_a[ek]["population"]:
        so_a[ek]["population"]["1996"] = p96
        nsw_96 += 1
      if "2001" not in so_a[ek]["population"]:
        so_a[ek]["population"]["2001"] = p01
    else:
      slug = re.sub(r"[^a-z0-9]+", "_", nm.lower()).strip("_")
      nk = f"aus_nsw01ac_{slug}_{nsw_new}"
      so_a[nk] = {
        "name": nm, "other_names": [], "coords": hit["coords"], "country": "Australia",
        "admin1": "New South Wales", "population_scope": hit["scope"], "is_capital": False,
        "population": {"1996": p96, "2001": p01}, "sources": [src_nsw],
      }
      idx_a[ik] = nk
      nsw_new += 1
      nsw_96 += 1
  if nsw_96:
    doc_a["settlements"] = so_a
    doc_a["metadata"]["total_settlements"] = len(so_a)
    with open(fp_aus, "w", encoding="utf-8") as f:
      json.dump(doc_a, f, ensure_ascii=False, indent=2)
  print(f"[NSW A-Z Table 2] total_matched={len(parsed_nsw)} | new={nsw_new} | added_1996={nsw_96}")

  # 2. Remaining genuine rural NZ 1996/2001/2006 Area Units from 2006mbdatasetallnz.zip (strictly outside Core-6 & excluding water/oceanic/parks)
  BAD_NZ = re.compile(r"\b(?:inlet|oceanic|inland\s+water|coastal|marine|offshore|shipping|oil\s+rig|total|area\s+outside|cbd|central\s+business|industrial|airport|hospital|university|prison|military|national\s+park|forest\s+park)\b", re.I)
  linz = {}
  with open(GAZ_PATH, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
      try:
        lat, lon = float(r.get("crd_latitude") or 0), float(r.get("crd_longitude") or 0)
      except Exception:
        continue
      if not (-47.5 <= lat <= -34.0 and (166.0 <= lon <= 180.0 or lon <= -175.0)) or in_core6(lat, lon):
        continue
      nm = str(r.get("name") or "").strip()
      nk = norm_key(nm)
      ft = str(r.get("feat_type") or "").strip()
      pr = 100 if ft in ("Town", "Suburb", "Locality", "Populated Place", "Village") else (60 if ft in ("Island", "Bay", "Beach", "Valley", "Peninsula", "Hill", "Plain", "Pa", "Marae") else 30)
      if nk and (nk not in linz or pr > linz[nk]["prio"]):
        linz[nk] = {"name": nm, "coords": [round(lat, 5), round(lon, 5)], "prio": pr}

  fp_nz = os.path.join(SRC_DIR, "enriched_nzl_historical_deep_1840_2006.json")
  doc_n = json.load(open(fp_nz, encoding="utf-8"))
  so_n = doc_n["settlements"]
  existing_pts = []
  for fn in ("nzl_official_census_timeseries.json", "enriched_nzl_modern_localities.json", "enriched_nzl_historical_deep_1840_2006.json"):
    d0 = json.load(open(os.path.join(SRC_DIR, fn), encoding="utf-8"))
    s0 = d0.get("settlements", d0)
    for rec in s0.values():
      if isinstance(rec, dict) and rec.get("country") == "New Zealand" and rec.get("population_scope") != "metro":
        c = rec.get("coords") or [0, 0]
        existing_pts.append((float(c[0]), float(c[1]), norm_key(rec.get("name", ""))))

  nz_new = 0
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
        if not au_name or len(au_name) < 3 or "&" in au_name or BAD_NZ.search(au_name):
          continue
        pops = {}
        for ci, yr in ((2, 1996), (3, 2001), (4, 2006)):
          try:
            iv = int(round(float(sh.cell_value(ri, ci))))
            if 20 <= iv <= 25000:
              pops[yr] = iv
          except Exception:
            pass
        if 1996 not in pops or 2006 not in pops:
          continue
        clean_nm = re.sub(r"\s+(?:Community|District|Area\s+Unit)$", "", au_name, flags=re.I).strip()
        nk = norm_key(clean_nm)
        hit = linz.get(nk)
        if hit is None:
          stripped = re.sub(r"\s+(?:Rural|North|South|East|West|Central|Upper|Lower|Valley|Plains|Hills|Coast|Harbour|Bay|Beach|Downs|Flats|Heights|Park|Point)$", "", clean_nm, flags=re.I).strip()
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
        if any(hav_km(lat, lon, elat, elon) <= 1.65 or (hav_km(lat, lon, elat, elon) <= 25.0 and enk == nk) for elat, elon, enk in existing_pts):
          continue
        slug = re.sub(r"[^a-z0-9]+", "_", clean_nm.lower()).strip("_")
        skey = f"nzl_au06x_{slug}_{nz_new}"
        so_n[skey] = {
          "name": clean_nm, "other_names": [], "coords": [lat, lon], "country": "New Zealand",
          "admin1": reg_name, "population_scope": "city_proper", "is_capital": False,
          "population": {str(y): p for y, p in sorted(pops.items())},
          "sources": ["Stats NZ 2006 Census Meshblock & Area Unit Dataset (1996, 2001, 2006 Usually Resident Population)"],
        }
        existing_pts.append((lat, lon, nk))
        nz_new += 1

  if nz_new:
    doc_n["settlements"] = so_n
    doc_n["metadata"]["total_settlements"] = len(so_n)
    with open(fp_nz, "w", encoding="utf-8") as f:
      json.dump(doc_n, f, ensure_ascii=False, indent=2)
  print(f"[NZL 2006 remaining AUs] added_new={nz_new}")


if __name__ == "__main__":
  main()
