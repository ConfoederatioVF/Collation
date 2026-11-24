"""Downloads official ABS Official Year Book 1901-1907 (1908, Cat. 1301.0 Section 4 Population)
and parses verbatim 1881/1891/1901 Australian towns + checks which Australian towns currently have
min_y == 1901 so we bridge 1900 (4.787 -> 4.830+ / 4.800) with 100% verbatim official censuses!"""
import json
import os
import re
import unicodedata
import urllib.request
from collections import Counter

import pymupdf

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SRC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "_shared", "settlement_sources")
PDF_DIR = os.path.join(SVEA_ROOT, "tests", "_aus_r2_cache", "pdfs")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


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


def main():
  # 1. Inspect Australian towns that have min_y == 1901 across modern_australia + colonial_australia
  import glob
  ca = json.load(open(glob.glob(os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "2.colonial", "*", "colonial_australia_settlements.json"))[0], encoding="utf-8"))
  ma = json.load(open(glob.glob(os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "3.modern", "*", "modern_australia_settlements.json"))[0], encoding="utf-8"))
  col_pre1900 = {norm_key(v["name"]) for v in ca.values() if any(int(y) <= 1900 for y in v["population"])}
  aus_1901_only = []
  for k, v in ma.items():
    ys = [int(y) for y in v["population"]]
    if min(ys) == 1901 and norm_key(v["name"]) not in col_pre1900:
      aus_1901_only.append((v["population"]["1901"], v["name"], v["admin1"]))
  aus_1901_only.sort(reverse=True)
  print(f"AUS towns with min_y == 1901 (no <=1900 obs): {len(aus_1901_only)}")
  for x in aus_1901_only[:25]:
    print(" ", x)

  # 2. Download official ABS Year Book 1908 & 1909 & 1910 Section 4 Population PDFs (1881, 1891, 1901 towns!)
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

  out = {}
  # Official ABS Year Book 1908 (1301.01908) & 1911 (1301.01911) + ABS Historical Cat. 2112.0 / 1891 Colonial Censuses
  for cat, cfn in [("1301.01908", "abs_1908_yb_pop.pdf"), ("1301.01909", "abs_1909_yb_pop.pdf"), ("1301.01910", "abs_1910_yb_pop.pdf")]:
    pp = os.path.join(PDF_DIR, cfn)
    if not os.path.exists(pp) or os.path.getsize(pp) < 40000:
      try:
        html = urllib.request.urlopen(urllib.request.Request(f"https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/{cat}?OpenDocument", headers=H), timeout=20).read().decode("utf-8", "ignore")
        dl = None
        for tr in re.findall(r"<tr[^>]*>.*?</tr>", html, re.S):
          if "section 4" in tr.lower() and "population" in tr.lower():
            hr = re.findall(r'href=["\']([^"\']*log\?openagent[^"\']*)["\']', tr, re.I)
            if hr:
              dl = "https://www.abs.gov.au" + hr[0].replace(" ", "%20")
              break
        if dl:
          data = urllib.request.urlopen(urllib.request.Request(dl, headers=H), timeout=60).read()
          with open(pp, "wb") as f:
            f.write(data)
      except Exception as e:
        print(f"  {cat} dl note:", e)
    if not os.path.exists(pp):
      continue
    doc = pymupdf.open(pp)
    m = 0
    for pg in doc:
      txt = pg.get_text("text")
      if "1891" not in txt and "1881" not in txt:
        continue
      cur_st = None
      for sk in ("New South Wales", "Victoria", "Queensland", "South Australia", "Western Australia", "Tasmania"):
        if sk.upper() in txt.upper():
          cur_st = sk
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
        if len(nums) < 2:
          continue
        name_toks = [re.sub(r"\.{2,}$", "", wd[4].strip()) for wd in lwd[:nums[0][0]] if wd[0] < 190 and not re.fullmatch(r"[.,:;'\"\-_]+", wd[4].strip())]
        if not name_toks:
          continue
        raw_loc = re.sub(r"\s*\([^)]*\)\s*$", "", " ".join(name_toks)).strip()
        if len(raw_loc) < 3:
          continue
        # Match across states if cur_st not set
        hit = None
        if cur_st:
          hit = geo.get((norm_key(raw_loc), cur_st))
        if hit is None:
          for sk in ("New South Wales", "Victoria", "Queensland", "South Australia", "Western Australia", "Tasmania"):
            hit = geo.get((norm_key(raw_loc), sk))
            if hit:
              break
        if hit is None:
          continue
        v81, v91 = nums[0][1], nums[1][1]
        if 200 <= v91 <= 600000 and 100 <= v81 <= 600000 and 0.2 <= v91 / max(1, v81) <= 5.0:
          key = (hit["name"], hit["state"])
          rec = out.setdefault(key, {"hit": hit, "pop": {}, "srcs": set()})
          rec["pop"].setdefault(1891, v91)
          rec["srcs"].add(f"ABS Official Year Book of the Commonwealth of Australia ({cat[-4:]}, Cat. 1301.0)")
          m += 1
    print(f"  [ABS {cat}] pages={len(doc)} | matched={m}")

  # 3. Also check official ANU HCCDA 1891 Colonial Censuses (NSW, VIC, QLD, SA, WA, TAS) via local tests/_aus_r2_cache/
  # OR official published 1891 Australian Colonial Census town counts for documented towns in aus_1901_only!
  # First check what files exist in tests/_aus_r2_cache/ or if HCCDA 1891 HTML pages work!
  hccda_91 = [
    ("New South Wales", "https://hccda.ada.edu.au/pages/NSW-1891-census-01_1"),
    ("Victoria", "https://hccda.ada.edu.au/pages/VIC-1891-census-01_1"),
    ("Queensland", "https://hccda.ada.edu.au/pages/QLD-1891-census-01_1"),
    ("South Australia", "https://hccda.ada.edu.au/pages/SA-1891-census-01_1"),
    ("Western Australia", "https://hccda.ada.edu.au/pages/WA-1891-census-01_1"),
    ("Tasmania", "https://hccda.ada.edu.au/pages/TAS-1891-census-01_1"),
  ]
  for st, u in hccda_91:
    try:
      html = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=12).read().decode("utf-8", "ignore")
      print(f"  HCCDA 1891 {st}: len={len(html)}")
    except Exception as e:
      print(f"  HCCDA 1891 {st}: {e}")


if __name__ == "__main__":
  main()
