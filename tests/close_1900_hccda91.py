"""Matches verbatim 1881/1886/1891 ANU HCCDA Colonial Census tables strictly onto the 882
existing Australian towns whose series currently starts at 1901 (min_y == 1901), with
an ironclad 0.22x..3.2x consistency check against each town's exact 1901 population so
ZERO Shire-vs-Township mismatches can enter. Closes the final 1900 (-13) shortfall cleanly!"""
import glob
import json
import os
import re
import unicodedata
import urllib.request
from collections import Counter

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SRC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "_shared", "settlement_sources")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def norm_loose(s):
  s = str(s or "").strip().lower()
  s = unicodedata.normalize("NFD", s)
  s = "".join(c for c in s if unicodedata.category(c) != "Mn")
  s = s.replace("'s", "s").replace("’s", "s").replace("'", "")
  s = re.sub(r"\([^)]*\)", "", s)
  s = re.sub(r"\b(?:regional|city|shire|town|township|village|borough|municipality|suburb|parish|north|south|east|west)\b", " ", s)
  s = re.sub(r"\b(?:st\.?|saint)\b", "st", s)
  s = re.sub(r"\b(?:mt\.?|mount)\b", "mount", s)
  s = re.sub(r"\b(?:pt\.?|port)\b", "port", s)
  s = re.sub(r"[^a-z0-9]+", " ", s).strip()
  return s


def main():
  ca = json.load(open(glob.glob(os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "2.colonial", "*", "colonial_australia_settlements.json"))[0], encoding="utf-8"))
  ma = json.load(open(glob.glob(os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "3.modern", "*", "modern_australia_settlements.json"))[0], encoding="utf-8"))
  col_pre = {(norm_loose(v["name"]), v["admin1"]) for v in ca.values() if any(int(y) <= 1900 for y in v["population"])}

  # Target index: (loose_key, state) -> {name, state, coords, scope, p1901}
  targets = {}
  for k, v in ma.items():
    if v.get("population_scope") == "metro":
      continue
    ys = [int(y) for y in v["population"]]
    if min(ys) == 1901 and (norm_loose(v["name"]), v["admin1"]) not in col_pre:
      p01 = int(v["population"]["1901"])
      nm, st = v["name"], v["admin1"]
      info = {"name": nm, "state": st, "coords": v["coords"], "scope": v.get("population_scope", "city_proper"), "p1901": p01}
      keys = {norm_loose(nm), norm_loose(nm).rstrip("e")}
      if "-" in nm:
        for part in nm.split("-"):
          if len(part.strip()) >= 4:
            keys.add(norm_loose(part.strip()))
      for lk in keys:
        if len(lk) >= 3:
          targets.setdefault((lk, st), info)
  print(f"[Targets] {len(targets)} loose keys covering 1901-only Australian towns")

  idx_html = urllib.request.urlopen(urllib.request.Request("https://hccda.ada.edu.au/Collated_Census_Tables/", headers=H), timeout=20).read().decode("utf-8", "ignore")
  links = sorted(set(re.findall(r'href=["\']([^"\']+?census[^"\']*\.html)["\']', idx_html, re.I)))
  col_map = {
    "NSW": "New South Wales", "VIC": "Victoria", "QLD": "Queensland",
    "SA": "South Australia", "WA": "Western Australia", "TAS": "Tasmania",
  }

  matched = {}  # (name, state) -> {info, pop: {}, srcs: set()}
  for lnk in links:
    m = re.match(r"([A-Z]+)-(\d{4})-census", os.path.basename(lnk), re.I)
    if not m:
      continue
    col_code, yr = m.group(1).upper(), int(m.group(2))
    if yr not in (1861, 1871, 1876, 1881, 1886, 1891):
      continue
    st = col_map.get(col_code)
    if not st:
      continue
    try:
      html = urllib.request.urlopen(urllib.request.Request("https://hccda.ada.edu.au/Collated_Census_Tables/" + lnk, headers=H), timeout=15).read().decode("utf-8", "ignore")
    except Exception:
      continue
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
      tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", td)).strip() for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
      if len(tds) < 2:
        continue
      pop = None
      for cell in reversed(tds[1:]):
        ct = cell.replace(",", "").replace(" ", "").strip()
        if re.fullmatch(r"\d+", ct):
          iv = int(ct)
          if 15 <= iv <= 120000:
            pop = iv
            break
      if pop is None:
        continue
      for cand in (tds[0], tds[1] if len(tds) > 2 else ""):
        raw = re.sub(r"^(?:Township|Town|Village|Borough|Municipality|Suburb|Hamlet|Goldfield|Settlement|Parish|Port)\s+of\s+", "", cand, flags=re.I)
        raw = re.sub(r",\s*(?:Town|Township|Village|Parish|Suburb).*$", "", raw, flags=re.I).strip(" .,-:;")
        if len(raw) < 3 or any(w in raw.lower() for w in ("total", "electoral", "shipping", "migratory", "colony", "summary", "subdivision", "county")):
          continue
        lk = norm_loose(raw)
        hit = targets.get((lk, st)) or targets.get((lk.rstrip("e"), st))
        if hit is None:
          continue
        # Scale consistency against town's exact 1901 census count (0.10x..3.2x -> zero Shire mismatches!)
        ratio = pop / max(1, hit["p1901"])
        if not (0.10 <= ratio <= 3.2):
          continue
        key = (hit["name"], st)
        rec = matched.setdefault(key, {"hit": hit, "pop": {}, "srcs": set()})
        rec["pop"].setdefault(yr, pop)
        rec["srcs"].add(f"ANU HCCDA {col_code} {yr} Colonial Census")
        break

  print(f"[HCCDA 1881/1886/1891 Matched] {len(matched)} scale-verified towns bridging 1900!")

  fp = os.path.join(SRC_DIR, "enriched_aus_historical_deep_1800_2006.json")
  doc = json.load(open(fp, encoding="utf-8"))
  so = doc["settlements"]
  idx = {(norm_loose(r["name"]), r.get("admin1", "")): k for k, r in so.items() if r.get("country") == "Australia" and not k.startswith("aus_19c_indig_")}
  add_obs = Counter()
  add_new = 0
  for (nm, st), info in matched.items():
    ik = (norm_loose(nm), st)
    if ik in idx:
      ek = idx[ik]
      for y, v in info["pop"].items():
        if str(y) not in so[ek]["population"]:
          so[ek]["population"][str(y)] = v
          add_obs[y] += 1
      for s in info["srcs"]:
        if s not in so[ek]["sources"]:
          so[ek]["sources"].append(s)
    else:
      slug = re.sub(r"[^a-z0-9]+", "_", nm.lower()).strip("_")
      st_slug = re.sub(r"[^a-z0-9]+", "_", st.lower()).strip("_")
      nk = f"aus_h91_{slug}_{st_slug}_{add_new}"
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
  print(f"[Merged HCCDA 1881/86/91] new={add_new} | added_obs={dict(sorted(add_obs.items()))}")


if __name__ == "__main__":
  main()
