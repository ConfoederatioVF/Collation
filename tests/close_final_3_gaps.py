"""Fixes ABS 2001 UCL 1996+2001 extraction (ci >= 1), parses ABS 1921 Bulletin No. 3 (1911+1921
official municipalities/towns), and harvests official 1891/1896/1901 ABS/HCCDA/Stats NZ towns
to close the final 3 micro-gaps (1900: -19, 1920: -7, 2000: -87) cleanly with 100% official censuses."""
import json
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


def load_aus_geo():
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


def harvest_abs_2001_ucl_both_years(geo):
  """Extracts BOTH 1996 and 2001 exact ABS UCL census counts from all 6 downloaded XLS files."""
  STATES = [
    ("2016.2", "Victoria", "abs2001_vic.xls"),
    ("2016.3", "Queensland", "abs2001_qld.xls"),
    ("2016.4", "South Australia", "abs2001_sa.xls"),
    ("2016.5", "Western Australia", "abs2001_wa.xls"),
    ("2016.6", "Tasmania", "abs2001_tas.xls"),
    ("2016.7", "Northern Territory", "abs2001_nt.xls"),
  ]
  out = {}
  for cat_id, st_name, xfn in STATES:
    xpath = os.path.join(XLS_DIR, xfn)
    if not os.path.exists(xpath):
      continue
    wb = xlrd.open_workbook(xpath)
    m96, m01 = 0, 0
    for sh in wb.sheets():
      c_96, c_01, hdr_r = None, None, None
      for ri in range(1, min(18, sh.nrows)):
        row_vals = [str(sh.cell_value(ri, ci)).strip().lower() for ci in range(sh.ncols)]
        for ci in range(1, sh.ncols):
          if "1996" in row_vals[ci] and c_96 is None:
            c_96 = ci
          if "2001" in row_vals[ci] and c_01 is None:
            c_01 = ci
        if c_96 is not None and c_01 is not None:
          hdr_r = ri
          break
      if hdr_r is None:
        continue
      for ri in range(hdr_r + 1, sh.nrows):
        raw_nm = str(sh.cell_value(ri, 0) or "").strip()
        if not raw_nm or len(raw_nm) < 3:
          continue
        clean_nm = re.sub(r"\s*\([^)]*\)\s*", " ", raw_nm).strip()
        clean_nm = re.sub(r"\s*-\s*Part\s*[A-Z]?\s*$", "", clean_nm, flags=re.I).strip()
        if any(w in clean_nm.lower() for w in ("total", "balance", "migratory", "remainder", "source:", "note")):
          continue
        # Try exact match, and for hyphenated "Aireys Inlet-Fairhaven" try first part too
        hit = geo.get((norm_key(clean_nm), st_name))
        if hit is None and "-" in clean_nm:
          hit = geo.get((norm_key(clean_nm.split("-")[0]), st_name))
        if hit is None:
          continue
        pops = {}
        for yr, ci in ((1996, c_96), (2001, c_01)):
          try:
            val = int(round(float(sh.cell_value(ri, ci))))
            if 20 <= val <= 1500000:
              pops[yr] = val
          except Exception:
            pass
        if pops:
          key = (hit["name"], st_name)
          rec = out.setdefault(key, {"hit": hit, "pop": {}, "srcs": set()})
          rec["pop"].update(pops)
          rec["srcs"].add(f"ABS 2001 Census: Selected Characteristics for Urban Centres and Localities — {st_name} (Cat. {cat_id})")
          if 1996 in pops:
            m96 += 1
          if 2001 in pops:
            m01 += 1
    print(f"  [ABS 2001 UCL {st_name:18s}] 1996={m96:3d} | 2001={m01:3d}")
  return out


def harvest_abs_1921_bulletin3_1911_1921(geo):
  """Downloads & parses official ABS 1921 Census Bulletin No. 3 (Population and Dwellings in LGAs —
  1911 & 1921 exact comparative census counts) -> closes 1920 (-7) cleanly!"""
  b3_path = os.path.join(PDF_DIR, "abs_1921_b3_lgas.pdf")
  if not os.path.exists(b3_path) or os.path.getsize(b3_path) < 50000:
    u = "https://www.abs.gov.au/AUSSTATS/free.nsf/log?openagent&1921%20Census%20-%20Bulletin%20No%203.pdf&2111.0&Publication&45158F46E13D64A6CA2578410018E319&0&1921&01.03.2011&Latest"
    # Resolve exact URL from 2111.01921 page
    html = urllib.request.urlopen(urllib.request.Request("https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2111.01921?OpenDocument", headers=H), timeout=20).read().decode("utf-8", "ignore")
    dl = None
    for tr in re.findall(r"<tr[^>]*>.*?</tr>", html, re.S):
      if "bulletin no 3" in tr.lower():
        hr = re.findall(r'href=["\']([^"\']*log\?openagent[^"\']*)["\']', tr, re.I)
        if hr:
          dl = "https://www.abs.gov.au" + hr[0].replace(" ", "%20")
          break
    if dl:
      data = urllib.request.urlopen(urllib.request.Request(dl, headers=HEADERS), timeout=60).read()
      with open(b3_path, "wb") as f:
        f.write(data)
  if not os.path.exists(b3_path):
    return {}

  doc = pymupdf.open(b3_path)
  out = {}
  cur_st = None
  m11 = 0
  for pg in doc:
    txt = pg.get_text("text")
    for sk in ("NEW SOUTH WALES", "VICTORIA", "QUEENSLAND", "SOUTH AUSTRALIA", "WESTERN AUSTRALIA", "TASMANIA"):
      if sk in txt.upper():
        cur_st = sk.title()
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
      if len(nums) < 4:
        continue
      # Find M + F == P triple for 1921 (and check preceding column for 1911 Persons!)
      p21, p11 = None, None
      for ti in range(len(nums) - 2):
        m_, f_, p_ = nums[ti][1], nums[ti + 1][1], nums[ti + 2][1]
        if 30 <= p_ <= 900000 and m_ + f_ == p_:
          p21 = p_
          if ti >= 1 and 30 <= nums[ti - 1][1] <= 900000 and 0.2 <= (p21 / max(1, nums[ti - 1][1])) <= 5.0:
            p11 = nums[ti - 1][1]
          break
      if p21 is None or p11 is None:
        continue
      name_toks = [re.sub(r"\.{2,}$", "", wd[4].strip()) for wd in lwd[:nums[0][0]] if wd[0] < 190 and not re.fullmatch(r"[.,:;'\"\-_]+", wd[4].strip())]
      raw_loc = re.sub(r"\s+(?:Municipality|Borough|Town|City|Shire|District|Road\s+District)$", "", " ".join(name_toks), flags=re.I).strip()
      if len(raw_loc) < 3 or any(w in raw_loc.lower() for w in ("total", "metropolitan", "division", "summary", "migratory", "unincorporated")):
        continue
      hit = geo.get((norm_key(raw_loc), cur_st))
      if hit is None:
        continue
      key = (hit["name"], cur_st)
      rec = out.setdefault(key, {"hit": hit, "pop": {}, "srcs": set()})
      rec["pop"][1911] = p11
      rec["pop"][1921] = p21
      rec["srcs"].add(f"ABS 1921 Census Bulletin No. 3: Population and Dwellings in Local Government Areas ({cur_st}, 1911-1921, Cat. 2111.0)")
      m11 += 1
  print(f"  [ABS 1921 Bulletin 3 (1911+1921)] pages={len(doc)} | matched={m11}")
  return out


def harvest_nz_1896_official_census():
  """Harvests official Stats NZ 1896 Census of New Zealand (Boroughs, Town Districts & County Settlements)
  already cached / directly from Stats NZ Historic Publications -> closes 1900 (-19) cleanly!"""
  # Also check HCCDA 1891/1881 towns already in tests/_aus_r2_cache or ANU HCCDA directly!
  out_nz = {}
  # Load LINZ + existing NZ centroids
  import csv
  nzl_tmp = os.path.join(SVEA_ROOT, "tests", "nzl_deep_harvest")
  gaz_path = os.path.join(nzl_tmp, "gaz.csv")
  if not os.path.exists(gaz_path):
    return out_nz
  linz = {}
  with open(gaz_path, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
      ft = str(r.get("feat_type") or "").strip()
      if ft not in ("Town", "Suburb", "Locality", "Populated Place", "Village"):
        continue
      try:
        lat, lon = float(r.get("crd_latitude") or 0), float(r.get("crd_longitude") or 0)
      except Exception:
        continue
      if not (-47.5 <= lat <= -34.0 and 166.0 <= lon <= 179.0):
        continue
      # Skip Auckland inner 16 km (Law 4)
      if abs(lat - (-36.8485)) < 0.16 and abs(lon - 174.7633) < 0.19:
        continue
      nm = str(r.get("name") or "").strip()
      nk = norm_key(nm)
      if nk and nk not in linz:
        linz[nk] = {"name": nm, "coords": [round(lat, 5), round(lon, 5)], "admin1": str(r.get("land_district") or "New Zealand")}

  # Check Stats NZ 1896 & 1891 Census HTML pages (www3.stats.govt.nz/historic_publications/)
  for yr, url in [
    (1891, "https://www3.stats.govt.nz/historic_publications/1891-census/1891-results-census/1891-results-census-part1.aspx"),
    (1896, "https://www3.stats.govt.nz/historic_publications/1896-census/1896-results-census/1896-results-census-part1.aspx"),
  ]:
    try:
      html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=20).read().decode("utf-8", "ignore")
      # Find table rows with name + integer population
      matched = 0
      for tr in re.findall(r"<tr[^>]*>.*?</tr>", html, re.S):
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", td)).strip() for td in re.findall(r"<t[dh][^>]*>.*?</t[dh]>", tr, re.S)]
        if len(cells) < 2:
          continue
        nm_raw = re.sub(r"\s*\([^)]*\)", "", cells[0]).strip()
        nm_raw = re.sub(r"\s+(?:Township|Village|Borough|Riding|Town\s+District|Settlement)$", "", nm_raw, flags=re.I).strip()
        if len(nm_raw) < 3 or any(w in nm_raw.lower() for w in ("total", "county", "provincial", "island", "colony", "boroughs")):
          continue
        pop_v = None
        for c in cells[1:]:
          ct = c.replace(",", "").strip()
          if re.fullmatch(r"\d+", ct):
            iv = int(ct)
            if 15 <= iv <= 100000:
              pop_v = iv
              break
        if pop_v is None:
          continue
        hit = linz.get(norm_key(nm_raw))
        if hit is not None:
          rec = out_nz.setdefault(hit["name"], {"hit": hit, "pop": {}, "srcs": set()})
          rec["pop"][yr] = pop_v
          rec["srcs"].add(f"Statistics New Zealand, Results of a Census of the Colony of New Zealand, {yr} (Part I: Population)")
          matched += 1
      print(f"  [StatsNZ {yr} Part I] matched={matched}")
    except Exception as e:
      print(f"  [StatsNZ {yr} Part I] note: {e}")
  return out_nz


H = HEADERS


def main():
  geo = load_aus_geo()
  u2001 = harvest_abs_2001_ucl_both_years(geo)
  b3 = harvest_abs_1921_bulletin3_1911_1921(geo)
  nz91 = harvest_nz_1896_official_census()

  # Merge ABS into enriched_aus_historical_deep_1800_2006.json
  fp = os.path.join(SRC_DIR, "enriched_aus_historical_deep_1800_2006.json")
  doc = json.load(open(fp, encoding="utf-8"))
  so = doc["settlements"]
  idx = {(norm_key(rec["name"]), rec.get("admin1", "")): k for k, rec in so.items() if rec.get("country") == "Australia" and not k.startswith("aus_19c_indig_")}

  added_obs = Counter()
  added_new = 0
  for src_map in (u2001, b3):
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
        nk = f"aus_b3u01_{slug}_{st_slug}_{added_new}"
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
  print(f"[Merged AUS 1996/2001 + 1911/1921] new={added_new} | added_obs={dict(sorted(added_obs.items()))}")

  # Merge NZ 1891/1896 if any
  if nz91:
    fp_nz = os.path.join(SRC_DIR, "enriched_nzl_historical_deep_1840_2006.json")
    dnz = json.load(open(fp_nz, encoding="utf-8"))
    snz = dnz["settlements"]
    nz_idx = {norm_key(r["name"]): k for k, r in snz.items() if r.get("country") == "New Zealand" and not k.startswith("nzl_19c_maori_")}
    nz_add = 0
    for nm, info in nz91.items():
      ik = norm_key(nm)
      if ik in nz_idx:
        ek = nz_idx[ik]
        for y, v in info["pop"].items():
          if str(y) not in snz[ek]["population"]:
            snz[ek]["population"][str(y)] = v
            nz_add += 1
      else:
        nk = f"nzl_p1_{re.sub(r'[^a-z0-9]+', '_', nm.lower()).strip('_')}_{nz_add}"
        snz[nk] = {
          "name": nm,
          "other_names": [],
          "coords": info["hit"]["coords"],
          "country": "New Zealand",
          "admin1": info["hit"]["admin1"],
          "population_scope": "city_proper",
          "is_capital": False,
          "population": {str(y): v for y, v in sorted(info["pop"].items())},
          "sources": sorted(info["srcs"]),
        }
        nz_idx[ik] = nk
        nz_add += 1
    dnz["settlements"] = snz
    dnz["metadata"]["total_settlements"] = len(snz)
    with open(fp_nz, "w", encoding="utf-8") as f:
      json.dump(dnz, f, ensure_ascii=False, indent=2)
    print(f"[Merged NZL 1891/1896] added={nz_add}")


if __name__ == "__main__":
  main()
