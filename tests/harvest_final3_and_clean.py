"""Closes the final 3 benchmark micro-gaps (1900: -19, 1920: -6, 2000: -85) using 100% pure
official ABS primary censuses AND cleans the 6 tiny leftover anomalies spotted in the snapshot:
  1. ABS 2001 Census Cat. 2016.2-2016.7 Official UCL Excel Data Cubes (exact 1996 & 2001 counts)
     -> spans 2000 cleanly across hundreds of Australian towns/localities.
  2. ABS 1911 Census Vol. III Part XIII/XIV (already cached locally) exact 1901 & 1911 town/municipality
     columns & ABS Year Books 1918-1919 (already cached locally) -> closes 1900 (-19) and 1920 (-6).
  3. Cleans: Shelly Beach wrong-coord duplicate, PNG Madang duplicate, Fiji Bau Tikina (30.965),
     French Polynesia 'Îles Tuamotu et Gambier', Vanuatu 'South West Tanna' Area Council,
     and Marshall Islands Delap distant-coord duplicate across ALL settlement_sources/*.json.
"""
import json
import math
import os
import re
import unicodedata
import urllib.request
from collections import Counter

import pymupdf
import xlrd

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SRC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "_shared", "settlement_sources")
CACHE_DIR = os.path.join(SVEA_ROOT, "tests", "_aus_r2_cache")
PDF_DIR = os.path.join(CACHE_DIR, "pdfs")
XLS_DIR = os.path.join(CACHE_DIR, "abs2001_ucl")
os.makedirs(XLS_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


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


def clean_6_leftover_anomalies():
  """Cleans Shelly Beach dup, Madang dup, Delap dup, Bau Tikina, FP archipelagos, Vanuatu ACs across ALL source JSONs."""
  FP_BAD = ("iles du vent", "iles sous le vent", "iles marquises", "iles tuamotu", "tuamotu et gambier", "iles australes")
  VUT_BAD = {
    "south west tanna", "southwest tanna", "north west tanna", "north east tanna", "south east tanna",
    "south east santo", "southeast santo", "north west santo", "south west santo", "north east santo",
    "south efate", "north west efate", "north east malekula", "south west malekula",
  }
  fixes = Counter()
  for fn in sorted(os.listdir(SRC_DIR)):
    if not fn.endswith(".json"):
      continue
    fp = os.path.join(SRC_DIR, fn)
    d = json.load(open(fp, encoding="utf-8"))
    wrapped = isinstance(d, dict) and "settlements" in d and isinstance(d["settlements"], dict)
    so = d["settlements"] if wrapped else d
    if not isinstance(so, dict):
      continue
    changed = False
    new_so = {}
    for k, rec in so.items():
      if not isinstance(rec, dict):
        new_so[k] = rec
        continue
      ctry = str(rec.get("country") or "").strip()
      nm = str(rec.get("name") or "").strip()
      nk = norm_key(nm)
      coords = rec.get("coords") or [0, 0]
      lat, lon = float(coords[0]), float(coords[1])

      # 1. NZ Shelly Beach wrong-coord duplicate inside 15km of Auckland CBD (real is Kaipara -36.57, 174.38)
      if ctry == "New Zealand" and nk == "shelly beach" and lat < -36.70:
        fixes["nz_shelly_beach_dup"] += 1
        changed = True
        continue

      # 2. French Polynesia archipelago aggregates (incl. "Îles Tuamotu et Gambier")
      if ctry == "French Polynesia" and any(b in nk for b in FP_BAD):
        fixes["fp_archipelago"] += 1
        changed = True
        continue

      # 3. Fiji Bau Tikina (26.586 / 30.965) overwrite across ALL files
      if ctry == "Fiji" and nk == "bau":
        pops = dict(rec.get("population") or {})
        drop_bau = False
        for yk in list(pops.keys()):
          if int(yk) >= 1980 and float(pops[yk]) > 5000:
            pops.pop(yk, None)
            drop_bau = True
        if drop_bau:
          fixes["fiji_bau_tikina"] += 1
          changed = True
          if not pops:
            continue
          rec = dict(rec)
          rec["population"] = pops

      # 4. Vanuatu Area Councils (South West Tanna, etc.)
      if ctry == "Vanuatu" and nk in VUT_BAD:
        fixes["vut_area_council"] += 1
        changed = True
        continue

      # 5. Marshall Islands Delap distant wrong-coord duplicate (real Delap is [7.09, 171.38])
      if ctry == "Marshall Islands" and nk == "delap" and lon < 171.25:
        fixes["rmi_delap_dup"] += 1
        changed = True
        continue

      # 6. PNG Madang duplicate (real Madang town is [-5.22, 145.79]; any other Madang > 15 km away with 35.971 pop is duplicate)
      if ctry == "Papua New Guinea" and nk == "madang":
        pops = rec.get("population") or {}
        if abs(lat - (-5.2215)) > 0.15 or abs(lon - 145.787) > 0.15:
          if any(int(round(float(v))) == 35971 for v in pops.values()):
            fixes["png_madang_bad_coord"] += 1
            changed = True
            continue
        # Also if fn == enriched_png_wards_llgs.json and Madang has exact same 35971 as png_census_raw.json, unify coords to [-5.2215, 145.787]
        if fn == "enriched_png_wards_llgs.json":
          rec = dict(rec)
          rec["coords"] = [-5.2215, 145.787]
          changed = True

      new_so[k] = rec

    if changed:
      if wrapped:
        d["settlements"] = new_so
        if "metadata" in d and isinstance(d["metadata"], dict):
          d["metadata"]["total_settlements"] = len(new_so)
        out_obj = d
      else:
        out_obj = new_so
      with open(fp, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)
  print("[Clean 6 Anomalies]", dict(fixes))


def load_aus_sal_geocoder():
  """Loads exact (norm_name, state) -> {name, coords, state, scope} from enriched_aus_sal_modern.json & aus_official_ucl_lga_timeseries.json."""
  geo = {}
  CAP_SKIP = {"sydney", "melbourne", "brisbane", "perth", "adelaide", "hobart", "darwin", "canberra"}
  for fn in ("aus_official_ucl_lga_timeseries.json", "enriched_aus_sal_modern.json"):
    fp = os.path.join(SRC_DIR, fn)
    if not os.path.exists(fp):
      continue
    d = json.load(open(fp, encoding="utf-8"))
    so = d.get("settlements", d)
    for rec in so.values():
      if not isinstance(rec, dict) or rec.get("country") != "Australia" or rec.get("population_scope") == "metro":
        continue
      nm = str(rec.get("name") or "").strip()
      st = str(rec.get("admin1") or "").strip()
      nk = norm_key(nm)
      if not nk or nk in CAP_SKIP or not st or st == "Australian Capital Territory":
        continue
      if (nk, st) not in geo:
        geo[(nk, st)] = {"name": nm, "coords": rec["coords"], "state": st, "scope": rec.get("population_scope", "city_proper")}
  return geo


def harvest_abs_2001_ucl_1996_2001(geo):
  """Downloads official ABS Cat. 2016.2-2016.7 (2001 Census UCL Data Cubes XLS) & 2016.1 NSW PDF
  for exact verbatim 1996 & 2001 ABS census counts (spans 2000!)."""
  STATES = [
    ("2016.22001", "Victoria", "abs2001_vic.xls"),
    ("2016.32001", "Queensland", "abs2001_qld.xls"),
    ("2016.42001", "South Australia", "abs2001_sa.xls"),
    ("2016.52001", "Western Australia", "abs2001_wa.xls"),
    ("2016.62001", "Tasmania", "abs2001_tas.xls"),
    ("2016.72001", "Northern Territory", "abs2001_nt.xls"),
  ]
  out = {}  # (name, state) -> {pop: {}, hit: ..., srcs: set()}
  for cat_id, st_name, xfn in STATES:
    xpath = os.path.join(XLS_DIR, xfn)
    if not os.path.exists(xpath) or os.path.getsize(xpath) < 5000:
      pg_url = f"https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/{cat_id}?OpenDocument"
      html = urllib.request.urlopen(urllib.request.Request(pg_url, headers=HEADERS), timeout=20).read().decode("utf-8", "ignore")
      xls_links = re.findall(r'href=["\']([^"\']*census_counts\.xls[^"\']*)["\']', html, re.I)
      if not xls_links:
        print(f"  [ABS 2001 UCL] No XLS link for {st_name}")
        continue
      dl_url = "https://www.abs.gov.au" + xls_links[0].replace(" ", "%20")
      data = urllib.request.urlopen(urllib.request.Request(dl_url, headers=HEADERS), timeout=30).read()
      with open(xpath, "wb") as f:
        f.write(data)
    wb = xlrd.open_workbook(xpath)
    matched_st = 0
    for sh in wb.sheets():
      # Find header row containing '1996' and '2001'
      c_1996 = None
      c_2001 = None
      hdr_r = None
      for ri in range(min(20, sh.nrows)):
        row_vals = [str(sh.cell_value(ri, ci)).strip().lower() for ci in range(sh.ncols)]
        for ci, rv in enumerate(row_vals):
          if "1996" in rv and c_1996 is None:
            c_1996 = ci
          if "2001" in rv and ("person" in rv or "total" in rv or rv == "2001" or "count" in rv or "census" in rv):
            c_2001 = ci
        if c_1996 is not None and c_2001 is not None:
          hdr_r = ri
          break
      if hdr_r is None:
        # Try 2-row header (year on row r, 'Persons' on row r+1)
        for ri in range(min(20, sh.nrows - 1)):
          r0 = [str(sh.cell_value(ri, ci)).strip().lower() for ci in range(sh.ncols)]
          r1 = [str(sh.cell_value(ri + 1, ci)).strip().lower() for ci in range(sh.ncols)]
          for ci in range(sh.ncols):
            if "1996" in r0[ci] and c_1996 is None:
              # Check if Persons is right under or +2
              if "person" in r1[ci] or not r1[ci]:
                c_1996 = ci
              elif ci + 2 < sh.ncols and "person" in r1[ci + 2]:
                c_1996 = ci + 2
            if "2001" in r0[ci] and c_2001 is None:
              if "person" in r1[ci] or not r1[ci]:
                c_2001 = ci
              elif ci + 2 < sh.ncols and "person" in r1[ci + 2]:
                c_2001 = ci + 2
          if c_1996 is not None and c_2001 is not None:
            hdr_r = ri + 1
            break
      if hdr_r is None:
        continue
      for ri in range(hdr_r + 1, sh.nrows):
        raw_nm = str(sh.cell_value(ri, 0) or "").strip()
        if not raw_nm or len(raw_nm) < 3:
          continue
        # Strip (L) / (State) / (Part)
        clean_nm = re.sub(r"\s*\([^)]*\)\s*", " ", raw_nm).strip()
        clean_nm = re.sub(r"\s*-\s*Part\s*[A-Z]?\s*$", "", clean_nm, flags=re.I).strip()
        if any(w in clean_nm.lower() for w in ("total", "balance", "migratory", "remainder", "source:", "note")):
          continue
        nk = norm_key(clean_nm)
        hit = geo.get((nk, st_name))
        if hit is None:
          continue
        pops = {}
        for yr, col_i in ((1996, c_1996), (2001, c_2001)):
          try:
            val = int(round(float(sh.cell_value(ri, col_i))))
            if 20 <= val <= 1500000:
              pops[yr] = val
          except Exception:
            pass
        if pops:
          key = (hit["name"], st_name)
          rec = out.setdefault(key, {"hit": hit, "pop": {}, "srcs": set()})
          rec["pop"].update(pops)
          rec["srcs"].add(f"ABS 2001 Census: Selected Characteristics for Urban Centres and Localities — {st_name} (Cat. {cat_id[:6]})")
          matched_st += 1
    print(f"  [ABS 2001 UCL {st_name:18s}] matched={matched_st} localities (1996 & 2001)")
  return out


def harvest_abs_1911_1901_and_1919_cached(geo):
  """Parses already-cached local ABS 1911 Part XIII/XIV PDFs for 1901 & 1911 pairs
  and ABS Year Books 1913-1919 PDFs for 1901/1911/1919 town counts -> closes 1900 (-19) and 1920 (-6)!"""
  out = {}
  # Parse ABS 1913-1919 Year Books (already in tests/_aus_r2_cache/pdfs/) for official state/town populations
  yb_specs = [
    ("abs_1913_yb_pop.pdf", 1911, "ABS Official Year Book of the Commonwealth of Australia 1913 (Cat. 1301.0)"),
    ("abs_1914_yb_pop.pdf", 1911, "ABS Official Year Book of the Commonwealth of Australia 1914 (Cat. 1301.0)"),
    ("abs_1918_yb_pop.pdf", 1918, "ABS Official Year Book of the Commonwealth of Australia 1918 (Cat. 1301.0)"),
    ("abs_1919_yb_pop.pdf", 1919, "ABS Official Year Book of the Commonwealth of Australia 1919 (Cat. 1301.0)"),
  ]
  # Also parse abs_1911_p14_summary.pdf for exact 1901 + 1911 comparison tables!
  p14 = os.path.join(PDF_DIR, "abs_1911_p14_summary.pdf")
  if os.path.exists(p14):
    doc = pymupdf.open(p14)
    cur_st = None
    m01 = 0
    for pg in doc:
      txt = pg.get_text("text")
      if not ("1901" in txt and "1911" in txt):
        continue
      for sk in ("New South Wales", "Victoria", "Queensland", "South Australia", "Western Australia", "Tasmania"):
        if sk.upper() in txt.upper():
          cur_st = sk
      if not cur_st:
        continue
      words = [wd for wd in pg.get_text("words") if 45 < wd[1] < pg.rect.height - 20]
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
          tok = wd[4].strip().replace(",", "")
          if re.fullmatch(r"\d+", tok):
            nums.append((idx, int(tok)))
        if len(nums) < 2:
          continue
        name_toks = [re.sub(r"\.{2,}$", "", wd[4].strip()) for wd in lwd[:nums[0][0]] if wd[0] < 185 and not re.fullmatch(r"[.,:;'\"\-_]+", wd[4].strip())]
        raw_loc = re.sub(r"\s+(?:Municipality|Borough|Town|City|Shire|District)$", "", " ".join(name_toks), flags=re.I).strip()
        if len(raw_loc) < 3 or any(w in raw_loc.lower() for w in ("total", "metropolitan", "division", "summary", "migratory", "state", "commonwealth")):
          continue
        hit = geo.get((norm_key(raw_loc), cur_st))
        if hit is None:
          continue
        v01, v11 = nums[0][1], nums[1][1]
        if 40 <= v01 <= 600000 and 40 <= v11 <= 700000 and 0.25 <= (v11 / max(1, v01)) <= 4.5:
          key = (hit["name"], cur_st)
          rec = out.setdefault(key, {"hit": hit, "pop": {}, "srcs": set()})
          rec["pop"][1901] = v01
          rec["pop"][1911] = v11
          rec["srcs"].add(f"ABS 1911 Census Vol. III Part XIV Summary ({cur_st}, 1901-1911 comparative table, Cat. 2112.0)")
          m01 += 1
    print(f"  [ABS 1911 Part XIV 1901-1911 pairs] matched={m01}")

  # Also check NZ 1891/1896/1901 & 1916/1921 in enriched_nzl_colonial_historical.json vs enriched_nzl_historical_deep_1840_2006.json
  # And check HCCDA 1891-1901 in enriched_aus_colonial_historical.json: any town in abs_1921 with 1901 in HCCDA already bridges 1920!
  # What about 1891 -> 1901 in abs_1911 / HCCDA? Let's also parse abs_1918_yb_pop.pdf & abs_1919_yb_pop.pdf for 1918/1919 towns!
  for pfn, yr, src_lbl in yb_specs:
    pp = os.path.join(PDF_DIR, pfn)
    if not os.path.exists(pp):
      continue
    doc = pymupdf.open(pp)
    cur_st = None
    m_yb = 0
    for pg in doc:
      txt = pg.get_text("text")
      if not any(w in txt.lower() for w in ("chief towns", "principal towns", "population of towns", "municipalities")):
        continue
      for sk in ("New South Wales", "Victoria", "Queensland", "South Australia", "Western Australia", "Tasmania"):
        if sk.upper() in txt.upper():
          cur_st = sk
      if not cur_st:
        continue
      words = [wd for wd in pg.get_text("words") if 45 < wd[1] < pg.rect.height - 20]
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
        nums = [(i, int(wd[4].strip().replace(",", ""))) for i, wd in enumerate(lwd) if re.fullmatch(r"[\d,]+", wd[4].strip()) and wd[4].strip().replace(",", "").isdigit()]
        if not nums:
          continue
        pop_v = next((v for _, v in nums if 250 <= v <= 850000), None)
        if pop_v is None:
          continue
        name_toks = [re.sub(r"\.{2,}$", "", wd[4].strip()) for wd in lwd[:nums[0][0]] if wd[0] < 190]
        raw_loc = re.sub(r"\s*\([^)]*\)\s*$", "", " ".join(name_toks)).strip()
        if len(raw_loc) < 3:
          continue
        hit = geo.get((norm_key(raw_loc), cur_st))
        if hit is not None:
          key = (hit["name"], cur_st)
          rec = out.setdefault(key, {"hit": hit, "pop": {}, "srcs": set()})
          rec["pop"].setdefault(yr, pop_v)
          rec["srcs"].add(src_lbl)
          m_yb += 1
    print(f"  [ABS {yr} YB] matched={m_yb}")
  return out


def main():
  clean_6_leftover_anomalies()
  geo = load_aus_sal_geocoder()
  print(f"[Geocoder] {len(geo)} non-capital Australian SAL/UCL centroids")

  u2001 = harvest_abs_2001_ucl_1996_2001(geo)
  h1911 = harvest_abs_1911_1901_and_1919_cached(geo)

  # Merge both cleanly into enriched_aus_historical_deep_1800_2006.json (never overwriting higher-priority existing years)
  fp = os.path.join(SRC_DIR, "enriched_aus_historical_deep_1800_2006.json")
  doc = json.load(open(fp, encoding="utf-8"))
  so = doc["settlements"]

  # Index existing by (norm_name, state)
  idx = {}
  for k, rec in so.items():
    if rec.get("country") == "Australia" and not k.startswith("aus_19c_indig_"):
      idx[(norm_key(rec["name"]), rec.get("admin1", ""))] = k

  added_obs = Counter()
  added_new = 0
  for src_map in (u2001, h1911):
    for (nm, st), info in src_map.items():
      ik = (norm_key(nm), st)
      if ik in idx:
        ek = idx[ik]
        for y, v in info["pop"].items():
          ys = str(y)
          if ys not in so[ek]["population"]:
            so[ek]["population"][ys] = v
            added_obs[y] += 1
        for s in info["srcs"]:
          if s not in so[ek]["sources"]:
            so[ek]["sources"].append(s)
      else:
        slug = re.sub(r"[^a-z0-9]+", "_", nm.lower()).strip("_")
        st_slug = re.sub(r"[^a-z0-9]+", "_", st.lower()).strip("_")
        nk = f"aus_ucl01_{slug}_{st_slug}"
        if nk in so:
          nk += f"_{added_new}"
        so[nk] = {
          "name": nm,
          "other_names": [],
          "coords": info["hit"]["coords"],
          "country": "Australia",
          "admin1": st,
          "population_scope": info["hit"]["scope"],
          "is_capital": False,
          "population": {str(y): v for y, v in sorted(info["pop"].items())},
          "sources": sorted(info["srcs"]),
        }
        idx[ik] = nk
        added_new += 1
        for y in info["pop"]:
          added_obs[y] += 1

  doc["settlements"] = so
  doc["metadata"]["total_settlements"] = len(so)
  with open(fp, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
  print(f"[Merged ABS 2001 UCL + 1901/1911/1919] new_settlements={added_new} | added_obs={dict(sorted(added_obs.items()))}")


if __name__ == "__main__":
  main()
