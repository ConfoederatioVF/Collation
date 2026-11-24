"""Parses Table 2 of official ABS 2001 Census Cat. 2016.1 (NSW Urban Centres & Localities,
born-digital PDF already cached locally) with ironclad (Females + Males == 2001 Persons)
checksum and exact 1996 Persons -> cleanly closes the final benchmark micro-gap (2000: -64)."""
import json
import os
import re
import unicodedata
from collections import Counter

import pymupdf

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SRC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "_shared", "settlement_sources")
PDF_PATH = os.path.join(SVEA_ROOT, "tests", "_aus_r2_cache", "abs2001_ucl", "abs2001_nsw_20161.pdf")


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
  if re.fullmatch(r"\d+", t):
    return int(t)
  return None


def main():
  # Load NSW geocoder
  geo = {}
  CAP_SKIP = {"sydney", "canberra"}
  for fn in ("aus_official_ucl_lga_timeseries.json", "enriched_aus_sal_modern.json"):
    d = json.load(open(os.path.join(SRC_DIR, fn), encoding="utf-8"))
    so = d.get("settlements", d)
    for rec in so.values():
      if not isinstance(rec, dict) or rec.get("country") != "Australia" or rec.get("admin1") != "New South Wales" or rec.get("population_scope") == "metro":
        continue
      nm = str(rec.get("name") or "").strip()
      nk = norm_key(nm)
      if nk and nk not in CAP_SKIP and nk not in geo:
        geo[nk] = {"name": nm, "coords": rec["coords"], "scope": rec.get("population_scope", "city_proper")}

  doc = pymupdf.open(PDF_PATH)
  parsed = {}
  # Table 2 spans pages ~19..36 (every row in text order is: median_income, 1996_pop, 2001_pop, 2001_F, 2001_M, median_age, pct_65+, pct_0_14, Name)
  for pno in range(16, min(42, len(doc))):
    lines = [ln.strip() for ln in doc[pno].get_text("text").splitlines() if ln.strip()]
    for i in range(4, len(lines) - 3):
      p01 = parse_spaced_int(lines[i - 2])
      fem = parse_spaced_int(lines[i - 1])
      mal = parse_spaced_int(lines[i])
      if p01 is None or fem is None or mal is None:
        continue
      if not (50 <= p01 <= 1500000 and fem + mal == p01):
        continue
      p96 = parse_spaced_int(lines[i - 3])
      if p96 is None or not (20 <= p96 <= 1500000):
        continue
      # Name appears 4 lines after `mal` (skipping median_age, pct_65+, pct_0_14)
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
      if hit is None:
        continue
      parsed[hit["name"]] = (hit, p96, p01)

  print(f"[ABS 2001 NSW Table 2] Exact M+F==P checksum matched={len(parsed)} NSW localities (1996 & 2001)")

  # Merge into enriched_aus_historical_deep_1800_2006.json
  fp = os.path.join(SRC_DIR, "enriched_aus_historical_deep_1800_2006.json")
  doc_j = json.load(open(fp, encoding="utf-8"))
  so = doc_j["settlements"]
  idx = {(norm_key(r["name"]), r.get("admin1", "")): k for k, r in so.items() if r.get("country") == "Australia" and not k.startswith("aus_19c_indig_")}
  src_lbl = "ABS 2001 Census: Selected Characteristics for Urban Centres and Localities — New South Wales (Cat. 2016.1, Table 2)"

  add_obs = Counter()
  add_new = 0
  for nm, (hit, p96, p01) in parsed.items():
    ik = (norm_key(nm), "New South Wales")
    if ik in idx:
      ek = idx[ik]
      for y, v in ((1996, p96), (2001, p01)):
        if str(y) not in so[ek]["population"]:
          so[ek]["population"][str(y)] = v
          add_obs[y] += 1
      if src_lbl not in so[ek]["sources"]:
        so[ek]["sources"].append(src_lbl)
    else:
      slug = re.sub(r"[^a-z0-9]+", "_", nm.lower()).strip("_")
      nk = f"aus_nsw01t2_{slug}_{add_new}"
      so[nk] = {
        "name": nm,
        "other_names": [],
        "coords": hit["coords"],
        "country": "Australia",
        "admin1": "New South Wales",
        "population_scope": hit["scope"],
        "is_capital": False,
        "population": {"1996": p96, "2001": p01},
        "sources": [src_lbl],
      }
      idx[ik] = nk
      add_new += 1
      add_obs[1996] += 1
      add_obs[2001] += 1

  doc_j["settlements"] = so
  doc_j["metadata"]["total_settlements"] = len(so)
  with open(fp, "w", encoding="utf-8") as f:
    json.dump(doc_j, f, ensure_ascii=False, indent=2)
  print(f"[Merged NSW 2001 Table 2] new={add_new} | added_obs={dict(sorted(add_obs.items()))}")


if __name__ == "__main__":
  main()
