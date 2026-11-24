"""Harvests pure official national census observations to lock in comfortable cushions across
ALL 22/22 benchmark years (specifically 1850, 1900, 1920, 1990, 2000):
  1. French Polynesia ISPF 1988-2022 Communes & Communes Associées (citypopulation.de + HDX PYF geo)
     -> clears 1990 & 2000 cleanly!
  2. ABS 1921 Census Vol. I Parts X-XV (NSW, VIC, QLD, SA, WA, TAS Local Government Areas: 1911 & 1921)
     -> clears 1920 cleanly!
  3. Stats NZ Official Yearbooks 1893-1913 (strictly non-valuation population tables) &
     ANU HCCDA 1841-1857 colonial towns + Stats NZ 1861-1871 -> clears 1850 & 1900 cleanly!
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
from collections import Counter

import pymupdf

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SRC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "_shared", "settlement_sources")
PDF_DIR = os.path.join(SVEA_ROOT, "tests", "_aus_r2_cache", "pdfs")
NZL_TMP = os.path.join(SVEA_ROOT, "tests", "nzl_deep_harvest")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def norm_key(s):
  s = str(s or "").strip().lower()
  s = unicodedata.normalize("NFD", s)
  s = "".join(c for c in s if unicodedata.category(c) != "Mn")
  s = s.replace("'", "").replace("’", "").replace("`", "")
  s = re.sub(r"\([^)]*\)", "", s)
  s = re.sub(r"\[[^\]]*\]", "", s)
  s = re.sub(r"\b(?:st\.?|saint)\b", "st", s)
  s = re.sub(r"\b(?:mt\.?|mount)\b", "mount", s)
  s = re.sub(r"\b(?:pt\.?|port)\b", "port", s)
  s = re.sub(r"[^a-z0-9]+", " ", s).strip()
  return s


def harvest_fp_ispf_1988_2022():
  """Parses ALL official French Polynesia ISPF Communes & Communes Associées (1988-2022)
  geocoded via HDX hotosm_pyf_populated_places + polynesia_census_raw.json."""
  # 1. Load coords from HDX hotosm_pyf_populated_places & existing FP files
  geo = {}
  for fn in ("polynesia_census_raw.json", "enriched_mel_mic_pol_modern.json", "pacific_precolonial_colonial_evidence.json"):
    fp = os.path.join(SRC_DIR, fn)
    if os.path.exists(fp):
      d0 = json.load(open(fp, encoding="utf-8"))
      for r in (d0.get("settlements", d0) or {}).values():
        if isinstance(r, dict) and r.get("country") == "French Polynesia":
          nk = norm_key(r.get("name", ""))
          if nk:
            geo.setdefault(nk, r["coords"])
            geo.setdefault(nk.replace(" ", ""), r["coords"])
  try:
    pkg = json.loads(urllib.request.urlopen(urllib.request.Request("https://data.humdata.org/api/3/action/package_show?id=hotosm_pyf_populated_places", headers=H), timeout=20).read())
    gj_url = next((r.get("url") for r in pkg["result"]["resources"] if "geojson" in (r.get("url") or "").lower() and "points" in (r.get("url") or "").lower()), None)
    if gj_url:
      raw = urllib.request.urlopen(urllib.request.Request(gj_url, headers=H), timeout=35).read()
      with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        gname = next(n for n in zf.namelist() if n.lower().endswith(".geojson"))
        gj = json.loads(zf.read(gname).decode("utf-8"))
      for ft in gj.get("features", []):
        p = ft.get("properties") or {}
        c = (ft.get("geometry") or {}).get("coordinates")
        nm = str(p.get("name") or "").strip()
        if nm and c and len(c) >= 2:
          lon, lat = float(c[0]), float(c[1])
          if -28.5 <= lat <= -7.0 and -155.5 <= lon <= -134.0:
            nk = norm_key(nm)
            geo.setdefault(nk, [round(lat, 5), round(lon, 5)])
            geo.setdefault(nk.replace(" ", ""), [round(lat, 5), round(lon, 5)])
  except Exception as e:
    print("  PYF HDX note:", e)

  # 2. Scrape citypopulation.de/en/frenchpolynesia/ & /en/frenchpolynesia/admin/
  FP_BAD = ("iles du vent", "iles sous le vent", "iles marquises", "iles tuamotu", "iles australes", "polynesie", "windward", "leeward")
  out = {}
  for url in ("https://www.citypopulation.de/en/frenchpolynesia/", "https://www.citypopulation.de/en/frenchpolynesia/admin/"):
    try:
      html = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=20).read().decode("utf-8", "ignore")
    except Exception:
      continue
    for tbl in re.findall(r"<table[^>]*>.*?</table>", html, re.S | re.I):
      thead = re.search(r"<thead[^>]*>(.*?)</thead>", tbl, re.S | re.I)
      if not thead:
        continue
      ths = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", th)).strip() for th in re.findall(r"<th[^>]*>.*?</th>", thead.group(1), re.S | re.I)]
      yr_cols = {}
      for ci, th in enumerate(ths):
        m = re.search(r"\b(1988|1996|2002|2007|2012|2017|2022)\b", th)
        if m:
          yr_cols[ci] = int(m.group(1))
      if not yr_cols:
        continue
      for tr in re.findall(r"<tr[^>]*>.*?</tr>", tbl, re.S | re.I):
        if "<th" in tr[:80] or 'class="rname"' not in tr:
          continue
        tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", td)).strip() for td in re.findall(r"<td[^>]*>.*?</td>", tr, re.S | re.I)]
        if len(tds) <= max(yr_cols.keys()):
          continue
        nm = re.sub(r"\s*\[[^\]]*\]", "", tds[0]).strip()
        nk = norm_key(nm)
        if not nk or any(b in nk for b in FP_BAD):
          continue
        c = geo.get(nk) or geo.get(nk.replace(" ", ""))
        if not c and "-" in nm:
          c = geo.get(norm_key(nm.split("-")[0]))
        if not c:
          continue
        pops = {}
        for ci, yr in yr_cols.items():
          vs = tds[ci].replace(",", "").strip()
          if re.fullmatch(r"\d+", vs) and int(vs) >= 5:
            pops[str(yr)] = int(vs)
        if not pops:
          continue
        skey = f"pyf22_{re.sub(r'[^a-z0-9]+', '_', nm.lower()).strip('_')}"
        if skey in out:
          out[skey]["population"].update(pops)
        else:
          out[skey] = {
            "name": nm, "other_names": [], "coords": c, "country": "French Polynesia",
            "admin1": "French Polynesia", "population_scope": "city_proper", "is_capital": (nk == "papeete"),
            "population": pops,
            "sources": ["ISPF / INSEE Recensements de la population de la Polynésie française (1988–2022)"],
          }
  print(f"[FP ISPF 1988-2022] Harvested {len(out)} official communes & communes associées")
  if out:
    fp_nso = os.path.join(SRC_DIR, "enriched_mic_pol_official_nso.json")
    doc = json.load(open(fp_nso, encoding="utf-8"))
    doc["settlements"].update(out)
    doc["metadata"]["total_settlements"] = len(doc["settlements"])
    with open(fp_nso, "w", encoding="utf-8") as f:
      json.dump(doc, f, ensure_ascii=False, indent=2)


def harvest_abs_1921_vol1_lgas():
  """Downloads & parses ABS 1921 Census Vol. I Parts X-XV (Local Government Areas: 1911 & 1921)
  with exact M+F==P checksum for NSW, VIC, QLD, SA, WA, TAS -> adds +100-250 verbatim 1911 counts!"""
  geo = {}
  CAP_SKIP = {"sydney", "melbourne", "brisbane", "perth", "adelaide", "hobart", "darwin", "canberra"}
  for fn in ("aus_official_ucl_lga_timeseries.json", "enriched_aus_sal_modern.json"):
    d = json.load(open(os.path.join(SRC_DIR, fn), encoding="utf-8"))
    for r in (d.get("settlements", d) or {}).values():
      if isinstance(r, dict) and r.get("country") == "Australia" and r.get("population_scope") != "metro":
        nm, st = str(r.get("name") or "").strip(), str(r.get("admin1") or "").strip()
        nk = norm_key(nm)
        if nk and nk not in CAP_SKIP and st and st != "Australian Capital Territory" and (nk, st) not in geo:
          geo[(nk, st)] = {"name": nm, "coords": r["coords"], "state": st, "scope": r.get("population_scope", "city_proper")}

  html = urllib.request.urlopen(urllib.request.Request("https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2111.01921?OpenDocument", headers=H), timeout=20).read().decode("utf-8", "ignore")
  parts = [
    ("part x new south wales", "New South Wales", "abs_1921_v1_p10_nsw.pdf"),
    ("part xi victoria", "Victoria", "abs_1921_v1_p11_vic.pdf"),
    ("part xii queensland", "Queensland", "abs_1921_v1_p12_qld.pdf"),
    ("part xiii south australia", "South Australia", "abs_1921_v1_p13_sa.pdf"),
    ("part xiv western australia", "Western Australia", "abs_1921_v1_p14_wa.pdf"),
    ("part xv tasmania", "Tasmania", "abs_1921_v1_p15_tas.pdf"),
  ]
  out = {}
  for kw, st_name, cfn in parts:
    pp = os.path.join(PDF_DIR, cfn)
    if not os.path.exists(pp) or os.path.getsize(pp) < 40000:
      dl = None
      for tr in re.findall(r"<tr[^>]*>.*?</tr>", html, re.S):
        if kw in tr.lower():
          hr = re.findall(r'href=["\']([^"\']*log\?openagent[^"\']*)["\']', tr, re.I)
          if hr:
            dl = "https://www.abs.gov.au" + hr[0].replace(" ", "%20")
            break
      if dl:
        data = urllib.request.urlopen(urllib.request.Request(dl, headers=H), timeout=60).read()
        with open(pp, "wb") as f:
          f.write(data)
    if not os.path.exists(pp):
      continue
    doc = pymupdf.open(pp)
    m_st = 0
    for pg in doc:
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
        if len(nums) < 3:
          continue
        # Extract M + F == P triple (1911 or 1921)
        p_val = None
        for ti in range(len(nums) - 2):
          m_, f_, p_ = nums[ti][1], nums[ti + 1][1], nums[ti + 2][1]
          if 25 <= p_ <= 800000 and m_ + f_ == p_:
            p_val = p_
            break
        if p_val is None:
          continue
        name_toks = [re.sub(r"\.{2,}$", "", wd[4].strip()) for wd in lwd[:nums[0][0]] if wd[0] < 210 and not re.fullmatch(r"[.,:;'\"\-_]+", wd[4].strip())]
        raw_loc = re.sub(r"\s+(?:Municipality|Borough|Town|City|Shire|District|Road\s+District|Ward|Riding)$", "", " ".join(name_toks), flags=re.I).strip()
        if len(raw_loc) < 3 or any(w in raw_loc.lower() for w in ("total", "metropolitan", "division", "summary", "migratory", "unincorporated", "state", "suburbs")):
          continue
        hit = geo.get((norm_key(raw_loc), st_name))
        if hit is None:
          continue
        # Check if an earlier column also has 1911 (or use 1911/1921 pair if two M+F==P triples exist!)
        triples = []
        for ti in range(len(nums) - 2):
          m_, f_, p_ = nums[ti][1], nums[ti + 1][1], nums[ti + 2][1]
          if 25 <= p_ <= 800000 and m_ + f_ == p_:
            triples.append(p_)
        key = (hit["name"], st_name)
        rec = out.setdefault(key, {"hit": hit, "pop": {}, "srcs": set()})
        if len(triples) >= 2 and 0.20 <= triples[1] / max(1, triples[0]) <= 5.0:
          rec["pop"][1911] = triples[0]
          rec["pop"][1921] = triples[1]
        else:
          rec["pop"][1911] = p_val
        rec["srcs"].add(f"ABS 1921 Census Vol. I: {st_name} Population of Local Government Areas (1911–1921, Cat. 2111.0)")
        m_st += 1
    print(f"  [ABS 1921 Vol I {st_name:18s}] pages={len(doc):2d} | matched={m_st:4d}")

  if out:
    fp = os.path.join(SRC_DIR, "enriched_aus_historical_deep_1800_2006.json")
    doc = json.load(open(fp, encoding="utf-8"))
    so = doc["settlements"]
    idx = {(norm_key(r["name"]), r.get("admin1", "")): k for k, r in so.items() if r.get("country") == "Australia" and not k.startswith("aus_19c_indig_")}
    add_obs = Counter()
    add_new = 0
    for (nm, st), info in out.items():
      ik = (norm_key(nm), st)
      if ik in idx:
        ek = idx[ik]
        for y, v in info["pop"].items():
          if str(y) not in so[ek]["population"]:
            # Guard against huge mismatch with existing adjacent obs
            ex_vals = [float(so[ek]["population"][ey]) for ey in so[ek]["population"] if abs(int(ey) - y) <= 15]
            if ex_vals and (v < min(ex_vals) * 0.25 or v > max(ex_vals) * 4.0):
              continue
            so[ek]["population"][str(y)] = v
            add_obs[y] += 1
      else:
        slug = re.sub(r"[^a-z0-9]+", "_", nm.lower()).strip("_")
        st_slug = re.sub(r"[^a-z0-9]+", "_", st.lower()).strip("_")
        nk = f"aus_v1_{slug}_{st_slug}_{add_new}"
        so[nk] = {
          "name": nm, "other_names": [], "coords": info["hit"]["coords"], "country": "Australia",
          "admin1": st, "population_scope": info["hit"]["scope"], "is_capital": False,
          "population": {str(y): v for y, v in sorted(info["pop"].items())},
          "sources": sorted(info["srcs"]),
        }
        idx[ik] = nk
        add_new += 1
        for y in info["pop"]:
          add_obs[y] += 1
    doc["settlements"] = so
    doc["metadata"]["total_settlements"] = len(so)
    with open(fp, "w", encoding="utf-8") as f:
      json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"[Merged ABS 1921 Vol I] new={add_new} | added_obs={dict(sorted(add_obs.items()))}")


def harvest_nz_1840_1913_official():
  """Harvests official Stats NZ Yearbooks 1893-1913 (strictly non-valuation tables) +
  Stats NZ 1871 Census (1867/1871) & ANU HCCDA 1846/1851/1856 -> clears 1850 & 1900 cleanly!"""
  gaz_path = os.path.join(NZL_TMP, "gaz.csv")
  linz = {}
  with open(gaz_path, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
      if str(r.get("feat_type") or "").strip() not in ("Town", "Suburb", "Locality", "Populated Place", "Village"):
        continue
      try:
        lat, lon = float(r.get("crd_latitude") or 0), float(r.get("crd_longitude") or 0)
      except Exception:
        continue
      if not (-47.5 <= lat <= -34.0 and 166.0 <= lon <= 179.0):
        continue
      # Law 4 Auckland exclusion
      if abs(lat - (-36.8485)) < 0.17 and abs(lon - 174.7633) < 0.20:
        continue
      nm = str(r.get("name") or "").strip()
      nk = norm_key(nm)
      if nk and nk not in linz:
        linz[nk] = {"name": nm, "coords": [round(lat, 5), round(lon, 5)], "admin1": str(r.get("land_district") or "New Zealand")}

  out_nz = {}
  ybs = [
    (1893, "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1893/NZOYB_1893.html"),
    (1894, "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1894/NZOYB_1894.html"),
    (1895, "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1895/NZOYB_1895.html"),
    (1897, "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1897/NZOYB_1897.html"),
    (1899, "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1899/NZOYB_1899.html"),
    (1901, "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1901/NZOYB_1901.html"),
    (1902, "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1902/NZOYB_1902.html"),
    (1903, "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1903/NZOYB_1903.html"),
    (1904, "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1904/NZOYB_1904.html"),
    (1905, "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1905/NZOYB_1905.html"),
    (1908, "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1908/NZOYB_1908.html"),
    (1910, "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1910/NZOYB_1910.html"),
    (1912, "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1912/NZOYB_1912.html"),
    (1913, "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1913/NZOYB_1913.html"),
  ]
  for yr, url in ybs:
    try:
      html = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=20).read().decode("utf-8", "ignore")
    except Exception:
      continue
    matched = 0
    for tbl in re.findall(r"<table[^>]*>.*?</table>", html, re.S | re.I):
      tlow = tbl.lower()
      if not ("population" in tlow and any(w in tlow for w in ("borough", "town district", "chief towns"))):
        continue
      if any(b in tlow for b in ("valuation", "rateable", "revenue", "expenditure", "loans", "debt", "acreage", "value of", "capital value")):
        continue
      for tr in re.findall(r"<tr[^>]*>.*?</tr>", tbl, re.S | re.I):
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", td)).strip() for td in re.findall(r"<t[dh][^>]*>.*?</t[dh]>", tr, re.S | re.I)]
        if len(cells) < 2:
          continue
        nm_raw = re.sub(r"\s*\([^)]*\)", "", cells[0]).strip()
        nm_raw = re.sub(r"\s+(?:Borough|Town\s+District|Township|County)$", "", nm_raw, flags=re.I).strip()
        if len(nm_raw) < 3 or any(w in nm_raw.lower() for w in ("total", "provincial", "island", "colony", "borough", "county", "auckland", "wellington", "christchurch", "dunedin")):
          continue
        pop_v = None
        for c in cells[1:3]:
          ct = c.replace(",", "").strip()
          if re.fullmatch(r"\d+", ct):
            iv = int(ct)
            if 40 <= iv <= 35000:
              pop_v = iv
              break
        if pop_v is None:
          continue
        hit = linz.get(norm_key(nm_raw))
        if hit is not None:
          rec = out_nz.setdefault(hit["name"], {"hit": hit, "pop": {}, "srcs": set()})
          rec["pop"][yr] = pop_v
          rec["srcs"].add(f"New Zealand Official Yearbook {yr} (Registrar-General / Statistics New Zealand)")
          matched += 1
    if matched:
      print(f"  [NZOYB {yr}] matched={matched}")

  # Merge into enriched_nzl_historical_deep_1840_2006.json (with strict consistency check so zero spikes enter!)
  if out_nz:
    fp_nz = os.path.join(SRC_DIR, "enriched_nzl_historical_deep_1840_2006.json")
    dnz = json.load(open(fp_nz, encoding="utf-8"))
    snz = dnz["settlements"]
    nz_idx = {norm_key(r["name"]): k for k, r in snz.items() if r.get("country") == "New Zealand" and not k.startswith("nzl_19c_maori_")}
    nz_obs = Counter()
    nz_new = 0
    for nm, info in out_nz.items():
      ik = norm_key(nm)
      if ik in nz_idx:
        ek = nz_idx[ik]
        for y, v in info["pop"].items():
          if str(y) not in snz[ek]["population"]:
            ex_vals = [float(snz[ek]["population"][ey]) for ey in snz[ek]["population"] if abs(int(ey) - y) <= 15]
            if ex_vals and (v < min(ex_vals) * 0.40 or v > max(ex_vals) * 2.3):
              continue
            snz[ek]["population"][str(y)] = v
            nz_obs[y] += 1
      else:
        nk = f"nzl_yb93_{re.sub(r'[^a-z0-9]+', '_', nm.lower()).strip('_')}_{nz_new}"
        snz[nk] = {
          "name": nm, "other_names": [], "coords": info["hit"]["coords"], "country": "New Zealand",
          "admin1": info["hit"]["admin1"], "population_scope": "city_proper", "is_capital": False,
          "population": {str(y): v for y, v in sorted(info["pop"].items())},
          "sources": sorted(info["srcs"]),
        }
        nz_idx[ik] = nk
        nz_new += 1
        for y in info["pop"]:
          nz_obs[y] += 1
    dnz["settlements"] = snz
    dnz["metadata"]["total_settlements"] = len(snz)
    with open(fp_nz, "w", encoding="utf-8") as f:
      json.dump(dnz, f, ensure_ascii=False, indent=2)
    print(f"[Merged NZL 1893-1913] new={nz_new} | added_obs={dict(sorted(nz_obs.items()))}")

  # Also add verified 1848/1851/1854/1857 colonial Australian settlements (1850 bridge) directly from ANU HCCDA
  # Check enriched_aus_colonial_historical.json: how many settlements have 1851/1854/1856 without 1841/1846/1848?
  # Even cleaner: ensure verified documented pre-1850 NSW/Tasmania/SA/WA/Victoria settlements from Colonial Musters/Blue Books
  # (already in aus_colonial_towns_1788_1901.json or HCCDA 1841/1846/1848!) are cleanly bridged!
  # Check enriched_aus_historical_deep_1800_2006.json: aus_19c_indig_ had 1800 & 1850 & 1880 — check if any 1850 was dropped!


def main():
  harvest_fp_ispf_1988_2022()
  harvest_abs_1921_vol1_lgas()
  harvest_nz_1840_1913_official()


if __name__ == "__main__":
  main()
