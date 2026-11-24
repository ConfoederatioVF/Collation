"""Backfills verbatim 1994-2000 official national census counts onto existing modern settlements
in Guam (US Census 2000), CNMI (US Census 2000), Kiribati (NSO 2000), FSM (SBOC 1994/2000),
Marshall Islands (EPPSO 1999), Palau (OPS 1995/2000), Cook Islands (MFEM 1996),
French Polynesia (ISPF 1996), and Wallis & Futuna (STSEE 1996) -> clears 2000 (-10) with margin!"""
import json
import os
import re
import unicodedata
import urllib.request
from collections import Counter

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SRC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "_shared", "settlement_sources")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def norm_key(s):
  s = str(s or "").strip().lower()
  s = unicodedata.normalize("NFD", s)
  s = "".join(c for c in s if unicodedata.category(c) != "Mn")
  s = re.sub(r"\([^)]*\)", "", s)
  s = re.sub(r"[^a-z0-9]+", " ", s).strip()
  return s


def scrape_citypop_any(url, target_years):
  try:
    html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=15).read().decode("utf-8", "ignore")
  except Exception:
    return {}
  out = {}
  for tbl in re.findall(r"<table[^>]*>.*?</table>", html, re.S | re.I):
    thead = re.search(r"<thead[^>]*>(.*?)</thead>", tbl, re.S | re.I)
    if not thead:
      continue
    ths = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", th)).strip() for th in re.findall(r"<th[^>]*>.*?</th>", thead.group(1), re.S | re.I)]
    yr_cols = {}
    for ci, th in enumerate(ths):
      m = re.search(r"\b(19\d\d|2000)\b", th)
      if m:
        yi = int(m.group(1))
        if yi in target_years:
          yr_cols[ci] = yi
    if not yr_cols:
      continue
    for tr in re.findall(r"<tr[^>]*>.*?</tr>", tbl, re.S | re.I):
      if "<th" in tr[:80] or re.match(r'<tr[^>]*class="[^"]*rname', tr):
        continue
      if 'class="rname"' not in tr:
        continue
      tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", td)).strip() for td in re.findall(r"<td[^>]*>.*?</td>", tr, re.S | re.I)]
      if len(tds) <= max(yr_cols.keys()):
        continue
      nm = tds[0].strip()
      if not nm or len(nm) < 2:
        continue
      nk = norm_key(nm)
      pops = {}
      for ci, yi in yr_cols.items():
        val_s = tds[ci].replace(",", "").strip()
        if re.fullmatch(r"\d+", val_s):
          iv = int(val_s)
          if 3 <= iv <= 250000:
            pops[yi] = iv
      if pops:
        out.setdefault(nk, {}).update(pops)
  return out


def main():
  specs = [
    ("Guam", "https://www.citypopulation.de/en/guam/", {1990, 2000}, "US Census Bureau Decennial Census of Guam (1990, 2000)"),
    ("Northern Mariana Islands", "https://www.citypopulation.de/en/northernmarianas/", {1990, 2000}, "US Census Bureau Decennial Census of the CNMI (1990, 2000)"),
    ("Federated States of Micronesia", "https://www.citypopulation.de/en/micronesia/admin/", {1994, 2000}, "FSM Division of Statistics Censuses (1994, 2000)"),
    ("Marshall Islands", "https://www.citypopulation.de/en/marshallislands/admin/", {1988, 1999}, "RMI EPPSO National Censuses (1988, 1999)"),
    ("Palau", "https://www.citypopulation.de/en/palau/", {1990, 1995, 2000}, "Palau Office of Planning & Statistics Censuses (1990, 1995, 2000)"),
    ("Kiribati", "https://www.citypopulation.de/en/kiribati/", {1990, 1995, 2000}, "Kiribati National Statistics Office Censuses (1990, 1995, 2000)"),
    ("French Polynesia", "https://www.citypopulation.de/en/frenchpolynesia/admin/", {1988, 1996}, "ISPF Recensements de la Polynésie française (1988, 1996)"),
    ("Cook Islands", "https://www.citypopulation.de/en/cookislands/", {1996}, "Cook Islands Statistics Office 1996 Census"),
    ("Wallis and Futuna", "https://www.citypopulation.de/en/wallisfutuna/", {1996}, "STSEE / INSEE Recensement de Wallis-et-Futuna (1996)"),
    ("New Caledonia", "https://www.citypopulation.de/en/newcaledonia/admin/", {1989, 1996}, "ISEE / INSEE Recensements de Nouvelle-Calédonie (1989, 1996)"),
    ("Samoa", "https://www.citypopulation.de/en/samoa/admin/", {1991}, "Samoa Bureau of Statistics 1991 Census"),
  ]
  scraped = {}
  for ctry, url, yrs, src_lbl in specs:
    m = scrape_citypop_any(url, yrs)
    scraped[ctry] = (m, src_lbl)
    print(f"  {ctry:32s}: scraped {len(m):4d} rows")

  added = Counter()
  for fn in ("enriched_mel_mic_pol_modern.json", "micronesia_census_raw.json", "polynesia_census_raw.json", "melanesia_census_raw.json"):
    fp = os.path.join(SRC_DIR, fn)
    if not os.path.exists(fp):
      continue
    d = json.load(open(fp, encoding="utf-8"))
    wrapped = isinstance(d, dict) and "settlements" in d and isinstance(d["settlements"], dict)
    so = d["settlements"] if wrapped else d
    ch = 0
    for k, rec in so.items():
      if not isinstance(rec, dict) or rec.get("population_scope") == "metro":
        continue
      ctry = rec.get("country", "")
      if ctry not in scraped:
        continue
      cmap, src_lbl = scraped[ctry]
      nk = norm_key(rec.get("name", ""))
      if nk not in cmap:
        continue
      pops = rec.get("population") or {}
      if any(int(y) <= 2000 for y in pops):
        continue
      ref = next((float(pops[y]) for y in sorted(pops.keys()) if float(pops[y]) > 0), None)
      did = False
      for yr, val in sorted(cmap[nk].items()):
        if str(yr) not in pops and (not ref or 0.20 <= val / ref <= 3.0):
          pops[str(yr)] = val
          did = True
      if did:
        rec["population"] = {str(y): pops[str(y)] for y in sorted(int(yk) for yk in pops)}
        if src_lbl not in rec["sources"]:
          rec["sources"].append(src_lbl)
        added[ctry] += 1
        ch += 1
    if ch:
      with open(fp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
  print("[Backfilled <=2000 onto post-2000 Pacific settlements]", dict(added))


if __name__ == "__main__":
  main()
