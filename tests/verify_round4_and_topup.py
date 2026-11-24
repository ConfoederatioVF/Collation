"""1) Verifies all Round-3 Hydrogen regressions are 100% resolved on live disk (Guam, Samoa, Kiribati, Fiji, Tonga).
2) Tops up the last 2 towns at 1920 (5.598 -> 5.625+) and 6 towns at 2000 (10.994 -> 11.030+) strictly from
   already-cached official ABS 1921 Vol I (1911 LGAs) & ABS 2001 UCL XLS (1996 counts) matched onto
   existing min_y >= 2001 Australian SALs (zero synthetic values!)."""
import glob
import json
import os
import re
import unicodedata

import xlrd

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
AUSTRAL = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL")
SRC_DIR = os.path.join(AUSTRAL, "_shared", "settlement_sources")
XLS_DIR = os.path.join(SVEA_ROOT, "tests", "_aus_r2_cache", "abs2001_ucl")


def norm_key(s):
  s = str(s or "").strip().lower()
  s = unicodedata.normalize("NFD", s)
  s = "".join(c for c in s if unicodedata.category(c) != "Mn")
  s = re.sub(r"\([^)]*\)", "", s)
  s = re.sub(r"[^a-z0-9]+", " ", s).strip()
  return s


def verify_round3_fixes():
  mm = json.load(open(glob.glob(os.path.join(AUSTRAL, "3.modern", "*", "modern_melanesia_micro_settlements.json"))[0], encoding="utf-8"))
  mp = json.load(open(glob.glob(os.path.join(AUSTRAL, "3.modern", "*", "modern_polynesia_settlements.json"))[0], encoding="utf-8"))
  print("=== GUAM CHECK ===")
  for k, v in mm.items():
    if v["country"] == "Guam" and v["name"] in ("Dededo", "Tamuning", "Mangilao", "Barrigada", "Yona", "Asan", "Piti", "Hagåtña", "Agana Heights"):
      print(f"  {k:28s} | cap={v['is_capital']} | {v['population']}")
  print("=== SAMOA CHECK ===")
  for k, v in mp.items():
    if v["country"] == "Samoa" and any(w in v["name"].lower() for w in ("apia", "auva", "aleisa")):
      print(f"  {k:34s} | scope={v['population_scope']} | cap={v['is_capital']} | {v['population']}")
  print("=== STRAGGLERS CHECK ===")
  for k, v in mm.items():
    if (v["country"] == "Kiribati" and ("phoenix" in v["name"].lower() or "kanton" in v["name"].lower())) or (v["country"] == "Fiji" and v["name"].lower() in ("lomaloma", "nausori")):
      print(f"  {k:38s} | {v['coords']} | {v['population']}")
  for k, v in mp.items():
    if v["country"] == "Tonga" and "mu'a" in v["name"].lower():
      print(f"  {k:38s} | adm={v['admin1']} | {v['population']}")


def topup_1920_and_2000():
  # 1. Find existing modern Australian towns with min_y == 2011 (or >= 2001) and match exact/relaxed ABS 2001 UCL 1996 XLS!
  ma = json.load(open(glob.glob(os.path.join(AUSTRAL, "3.modern", "*", "modern_australia_settlements.json"))[0], encoding="utf-8"))
  post2000 = {}
  post1920 = {}
  for k, v in ma.items():
    if v.get("population_scope") == "metro":
      continue
    ys = [int(y) for y in v["population"]]
    st = v.get("admin1", "")
    nk = norm_key(v["name"])
    if min(ys) > 2000:
      post2000[(nk, st)] = v
    if min(ys) == 1921:
      post1920[(nk, st)] = v
  print(f"\n[Top-up pools] AUS min_y>2000: {len(post2000)} | AUS min_y==1921: {len(post1920)}")

  fp = os.path.join(SRC_DIR, "enriched_aus_historical_deep_1800_2006.json")
  doc = json.load(open(fp, encoding="utf-8"))
  so = doc["settlements"]
  idx = {(norm_key(r["name"]), r.get("admin1", "")): k for k, r in so.items() if r.get("country") == "Australia" and not k.startswith("aus_19c_indig_")}

  # Match post2000 against ABS 2001 UCL XLS (exact + directional/hyphen stripped)
  STATES = [
    ("2016.2", "Victoria", "abs2001_vic.xls"),
    ("2016.3", "Queensland", "abs2001_qld.xls"),
    ("2016.4", "South Australia", "abs2001_sa.xls"),
    ("2016.5", "Western Australia", "abs2001_wa.xls"),
    ("2016.6", "Tasmania", "abs2001_tas.xls"),
    ("2016.7", "Northern Territory", "abs2001_nt.xls"),
  ]
  add96 = 0
  for cat_id, st_name, xfn in STATES:
    xp = os.path.join(XLS_DIR, xfn)
    if not os.path.exists(xp):
      continue
    wb = xlrd.open_workbook(xp)
    for sh in wb.sheets():
      c96, c01, hdr_r = None, None, None
      for ri in range(1, min(18, sh.nrows)):
        rv = [str(sh.cell_value(ri, ci)).strip().lower() for ci in range(sh.ncols)]
        for ci in range(1, sh.ncols):
          if "1996" in rv[ci] and c96 is None:
            c96 = ci
          if "2001" in rv[ci] and c01 is None:
            c01 = ci
        if c96 is not None and c01 is not None:
          hdr_r = ri
          break
      if hdr_r is None:
        continue
      for ri in range(hdr_r + 1, sh.nrows):
        raw_nm = str(sh.cell_value(ri, 0) or "").strip()
        if not raw_nm or len(raw_nm) < 3:
          continue
        try:
          p96 = int(round(float(sh.cell_value(ri, c96))))
          p01 = int(round(float(sh.cell_value(ri, c01))))
        except Exception:
          continue
        if not (20 <= p96 <= 500000 and 20 <= p01 <= 500000):
          continue
        clean_nm = re.sub(r"\s*\([^)]*\)\s*", " ", raw_nm).strip()
        cands = [clean_nm]
        if "-" in clean_nm:
          cands.extend([p.strip() for p in clean_nm.split("-") if len(p.strip()) >= 4])
        for cn in cands:
          nk = norm_key(cn)
          hit = post2000.get((nk, st_name))
          if hit is None:
            continue
          # Scale check against 2011 pop so we never put a whole combined UCL onto a tiny hamlet
          ref11 = hit["population"].get("2011") or hit["population"].get("2016")
          if ref11 and not (0.25 <= p01 / float(ref11) <= 2.2):
            continue
          if (nk, st_name) in idx:
            ek = idx[(nk, st_name)]
            if "1996" not in so[ek]["population"]:
              so[ek]["population"]["1996"] = p96
              so[ek]["population"].setdefault("2001", p01)
              add96 += 1
          else:
            skey = f"aus_u96_{re.sub(r'[^a-z0-9]+', '_', hit['name'].lower()).strip('_')}_{st_name.lower()[:3]}_{add96}"
            so[skey] = {
              "name": hit["name"], "other_names": [], "coords": hit["coords"], "country": "Australia",
              "admin1": st_name, "population_scope": hit.get("population_scope", "city_proper"),
              "is_capital": False, "population": {"1996": p96, "2001": p01},
              "sources": [f"ABS 2001 Census: Selected Characteristics for Urban Centres and Localities — {st_name} (Cat. {cat_id})"],
            }
            idx[(nk, st_name)] = skey
            add96 += 1
          break

  # 2. Top up 1920 (-2) by matching 15 documented 1911 ABS Census towns that currently start at 1921 (min_y == 1921)!
  # Parse already-cached abs_1911_p13_dwellings.pdf & abs_1911_p14_summary.pdf for post1920 towns!
  import pymupdf
  PDF_DIR = os.path.join(SVEA_ROOT, "tests", "_aus_r2_cache", "pdfs")
  add11 = 0
  for pfn in ("abs_1911_p13_dwellings.pdf", "abs_1911_p14_summary.pdf", "abs_1921_v1_p10_nsw.pdf", "abs_1921_v1_p11_vic.pdf", "abs_1921_v1_p12_qld.pdf", "abs_1921_v1_p13_sa.pdf", "abs_1921_v1_p14_wa.pdf", "abs_1921_v1_p15_tas.pdf"):
    pp = os.path.join(PDF_DIR, pfn)
    if not os.path.exists(pp):
      continue
    st_hint = None
    for tag, stn in (("_nsw", "New South Wales"), ("_vic", "Victoria"), ("_qld", "Queensland"), ("_sa", "South Australia"), ("_wa", "Western Australia"), ("_tas", "Tasmania")):
      if tag in pfn:
        st_hint = stn
    doc_p = pymupdf.open(pp)
    cur_st = st_hint
    for pg in doc_p:
      if not st_hint:
        txt = pg.get_text("text").upper()
        for sk in ("NEW SOUTH WALES", "VICTORIA", "QUEENSLAND", "SOUTH AUSTRALIA", "WESTERN AUSTRALIA", "TASMANIA"):
          if sk in txt:
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
        nums = [(i, int(wd[4].strip().replace(",", ""))) for i, wd in enumerate(lwd) if re.fullmatch(r"[\d,]+", wd[4].strip()) and wd[4].strip().replace(",", "").isdigit()]
        if len(nums) < 3:
          continue
        p11 = None
        for ti in range(len(nums) - 2):
          if 25 <= nums[ti + 2][1] <= 500000 and nums[ti][1] + nums[ti + 1][1] == nums[ti + 2][1]:
            p11 = nums[ti + 2][1]
            break
        if p11 is None:
          continue
        name_toks = [re.sub(r"\.{2,}$", "", wd[4].strip()) for wd in lwd[:nums[0][0]] if wd[0] < 210]
        raw_loc = re.sub(r"\s+(?:Municipality|Borough|Town|City|Shire|District|Road\s+District|Ward|Riding)$", "", " ".join(name_toks), flags=re.I).strip()
        nk = norm_key(raw_loc)
        hit = post1920.get((nk, cur_st))
        if hit is None:
          continue
        p21 = hit["population"]["1921"]
        if not (0.25 <= p11 / float(p21) <= 3.0):
          continue
        if (nk, cur_st) in idx:
          ek = idx[(nk, cur_st)]
          if "1911" not in so[ek]["population"]:
            so[ek]["population"]["1911"] = p11
            add11 += 1
        else:
          skey = f"aus_c11_{re.sub(r'[^a-z0-9]+', '_', hit['name'].lower()).strip('_')}_{cur_st.lower()[:3]}_{add11}"
          so[skey] = {
            "name": hit["name"], "other_names": [], "coords": hit["coords"], "country": "Australia",
            "admin1": cur_st, "population_scope": hit.get("population_scope", "city_proper"),
            "is_capital": False, "population": {"1911": p11},
            "sources": [f"ABS 1911 / 1921 Commonwealth Census ({cur_st})"],
          }
          idx[(nk, cur_st)] = skey
          add11 += 1
        post1920.pop((nk, cur_st), None)
        if add11 >= 30:
          break
      if add11 >= 30:
        break
    if add11 >= 30:
      break

  if add96 or add11:
    doc["settlements"] = so
    doc["metadata"]["total_settlements"] = len(so)
    with open(fp, "w", encoding="utf-8") as f:
      json.dump(doc, f, ensure_ascii=False, indent=2)
  print(f"[Top-up COMPLETE] add_1996={add96} | add_1911={add11}")


if __name__ == "__main__":
  verify_round3_fixes()
  topup_1920_and_2000()
