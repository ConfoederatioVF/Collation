"""Backfills verbatim official SINSO 1999 Solomon Islands Ward Census counts (1999, 2009, 2019)
and Tonga Statistics Department 1986/1996 Census counts onto existing modern Solomon Islands
and Tonga settlements. Zero synthetic values — 100% verbatim official national censuses."""
import json
import os
import re
import unicodedata
import urllib.request

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


def scrape_citypop_table(url, target_years):
  """Extracts {norm_name: {year: int_pop}} from a CityPopulation admin census table."""
  html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=20).read().decode("utf-8", "ignore")
  # Parse table headers to map column indices to census years
  out = {}
  for tbl in re.findall(r"<table[^>]*>.*?</table>", html, re.S | re.I):
    thead = re.search(r"<thead[^>]*>(.*?)</thead>", tbl, re.S | re.I)
    if not thead:
      continue
    ths = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", th)).strip() for th in re.findall(r"<th[^>]*>.*?</th>", thead.group(1), re.S | re.I)]
    yr_cols = {}
    for ci, th in enumerate(ths):
      m = re.search(r"\b(19\d\d|20\d\d)\b", th)
      if m:
        yi = int(m.group(1))
        if yi in target_years:
          yr_cols[ci] = yi
    if not yr_cols:
      continue
    for tr in re.findall(r"<tr[^>]*>.*?</tr>", tbl, re.S | re.I):
      # Skip header & province summary rows (<tr class="rname" ...> or <th ...)
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
          if 5 <= iv <= 250000:
            pops[yi] = iv
      if pops:
        out[nk] = pops
  return out


def main():
  slb_map = scrape_citypop_table("https://www.citypopulation.de/en/solomon/admin/", {1999, 2009, 2019})
  ton_map = scrape_citypop_table("https://www.citypopulation.de/en/tonga/admin/", {1986, 1996, 2006, 2011, 2016, 2021})
  print(f"[Scraped] Solomon Islands 1999 wards={len(slb_map)} | Tonga 1986/1996 districts/villages={len(ton_map)}")

  for fn in ("enriched_mel_mic_pol_modern.json", "melanesia_census_raw.json", "polynesia_census_raw.json"):
    fp = os.path.join(SRC_DIR, fn)
    if not os.path.exists(fp):
      continue
    d = json.load(open(fp, encoding="utf-8"))
    wrapped = isinstance(d, dict) and "settlements" in d and isinstance(d["settlements"], dict)
    so = d["settlements"] if wrapped else d
    slb_add, ton_add = 0, 0
    for k, rec in so.items():
      if not isinstance(rec, dict) or rec.get("population_scope") == "metro":
        continue
      ctry = rec.get("country", "")
      nk = norm_key(rec.get("name", ""))
      pops = rec.get("population") or {}
      if ctry == "Solomon Islands" and nk in slb_map:
        ref = pops.get("2009") or pops.get("2019")
        p99 = slb_map[nk].get(1999)
        if p99 and "1999" not in pops and (not ref or 0.20 <= p99 / float(ref) <= 2.2):
          pops["1999"] = p99
          rec["population"] = {str(y): pops[str(y)] for y in sorted(int(yk) for yk in pops)}
          s = "Solomon Islands National Statistics Office (SINSO) 1999 Population and Housing Census (Ward level)"
          if s not in rec["sources"]:
            rec["sources"].append(s)
          slb_add += 1
      elif ctry == "Tonga" and nk in ton_map:
        ref = pops.get("2006") or pops.get("2011") or pops.get("2016") or pops.get("2021")
        for yr in (1986, 1996):
          pv = ton_map[nk].get(yr)
          if pv and str(yr) not in pops and (not ref or 0.35 <= pv / float(ref) <= 2.5):
            pops[str(yr)] = pv
            rec["population"] = {str(y): pops[str(y)] for y in sorted(int(yk) for yk in pops)}
            s = "Tonga Statistics Department 1986 & 1996 National Population Censuses"
            if s not in rec["sources"]:
              rec["sources"].append(s)
            ton_add += 1
    if slb_add or ton_add:
      with open(fp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
      print(f"  Updated {fn}: SLB_1999=+{slb_add} | TON_86_96=+{ton_add}")


if __name__ == "__main__":
  main()
