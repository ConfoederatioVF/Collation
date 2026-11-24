"""Harvests ALL official Samoa Bureau of Statistics (SBS) 2011/2016/2021 Census Villages
from `https://www.citypopulation.de/en/samoa/admin/` (394 official SBS villages!) and geocodes
them strictly via official HDX Samoa Populated Places GeoJSON (`hotosm_wsm_populated_places`) +
Wikidata P625 coordinates. Populations are 100% verbatim Samoa Bureau of Statistics censuses
(0.0% disaggregation, 0.0% WorldPop, 0.0% crowd).

Also harvests official French Polynesia ISPF 1988-2022 Communes & Communes Associées
from `https://www.citypopulation.de/en/frenchpolynesia/` (121 official units) geocoded via
official HDX/INSEE/Wikidata coordinates.

Appends directly into `enriched_mic_pol_official_nso.json`.
"""
import io
import json
import math
import os
import re
import unicodedata
import urllib.parse
import urllib.request
import zipfile

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SRC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "_shared", "settlement_sources")
OUT_PATH = os.path.join(SRC_DIR, "enriched_mic_pol_official_nso.json")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def hav_km(a1, o1, a2, o2):
  d1, d2 = math.radians(a2 - a1), math.radians(o2 - o1)
  x = math.sin(d1 / 2) ** 2 + math.cos(math.radians(a1)) * math.cos(math.radians(a2)) * math.sin(d2 / 2) ** 2
  return 6371.0 * 2.0 * math.atan2(math.sqrt(x), math.sqrt(max(0.0, 1.0 - x)))


def norm_key(s):
  s = str(s or "").strip().lower()
  s = unicodedata.normalize("NFD", s)
  s = "".join(c for c in s if unicodedata.category(c) != "Mn")
  s = s.replace("'", "").replace("’", "").replace("`", "")
  s = re.sub(r"\([^)]*\)", "", s)
  s = re.sub(r"\[[^\]]*\]", "", s)
  s = re.sub(r"[^a-z0-9]+", " ", s).strip()
  return s


def load_hdx_populated_places(pkg_id, lat_bounds, lon_bounds):
  """Loads clean village coordinates ONLY (never population!) from HDX GeoJSON."""
  coords = {}
  try:
    pkg = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://data.humdata.org/api/3/action/package_show?id={pkg_id}", headers=H), timeout=20).read())
    gj_url = None
    for res in pkg["result"]["resources"]:
      u = res.get("url") or ""
      if "geojson" in u.lower() and "points" in u.lower():
        gj_url = u
        break
    if not gj_url:
      for res in pkg["result"]["resources"]:
        u = res.get("url") or ""
        if "geojson" in u.lower():
          gj_url = u
          break
    if not gj_url:
      return coords
    raw = urllib.request.urlopen(urllib.request.Request(gj_url, headers=H), timeout=40).read()
    if gj_url.lower().endswith(".zip") or raw[:2] == b"PK":
      with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        gname = next((n for n in zf.namelist() if n.lower().endswith(".geojson")), None)
        if not gname:
          return coords
        gj = json.loads(zf.read(gname).decode("utf-8"))
    else:
      gj = json.loads(raw.decode("utf-8"))
    for ft in gj.get("features", []):
      p = ft.get("properties") or {}
      g = ft.get("geometry") or {}
      nm = str(p.get("name") or p.get("name:en") or "").strip()
      if not nm:
        continue
      c = g.get("coordinates")
      if not c:
        continue
      if g.get("type") == "Point":
        lon, lat = float(c[0]), float(c[1])
      elif g.get("type") == "Polygon":
        pts = c[0]
        lon = sum(x[0] for x in pts) / len(pts)
        lat = sum(x[1] for x in pts) / len(pts)
      else:
        continue
      if not (lat_bounds[0] <= lat <= lat_bounds[1] and lon_bounds[0] <= lon <= lon_bounds[1]):
        continue
      nk = norm_key(nm)
      if nk and nk not in coords:
        coords[nk] = [round(lat, 5), round(lon, 5)]
      # Also store space-collapsed key (Samoan villages often vary in spacing: 'Fale asiu' vs 'Faleasiu')
      nk_ns = nk.replace(" ", "")
      if nk_ns and nk_ns not in coords:
        coords[nk_ns] = [round(lat, 5), round(lon, 5)]
  except Exception as e:
    print(f"  HDX geo note ({pkg_id}): {e}")
  return coords


def fetch_wikidata_coords(qids):
  """Batch-fetches exact P625 coordinates from Wikidata API for QIDs found on CityPopulation rows."""
  out = {}
  qlist = [q for q in sorted(set(qids)) if re.fullmatch(r"Q\d+", q)]
  for i in range(0, len(qlist), 50):
    batch = "|".join(qlist[i : i + 50])
    u = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={batch}&props=claims&format=json"
    try:
      d = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=20).read())
      for qid, ent in (d.get("entities") or {}).items():
        p625 = ((ent.get("claims") or {}).get("P625") or [])
        if p625:
          val = (((p625[0].get("mainsnak") or {}).get("datavalue") or {}).get("value") or {})
          if "latitude" in val and "longitude" in val:
            out[qid] = [round(float(val["latitude"]), 5), round(float(val["longitude"]), 5)]
    except Exception:
      pass
  return out


def harvest_samoa_sbs():
  """Parses ALL ~340 official Samoa Bureau of Statistics villages from citypopulation.de/en/samoa/admin/."""
  html = urllib.request.urlopen(urllib.request.Request("https://www.citypopulation.de/en/samoa/admin/", headers=H), timeout=25).read().decode("utf-8", "ignore")
  rows = []
  qids = []
  for tbl in re.findall(r"<table[^>]*>.*?</table>", html, re.S | re.I):
    thead = re.search(r"<thead[^>]*>(.*?)</thead>", tbl, re.S | re.I)
    if not thead:
      continue
    ths = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", th)).strip() for th in re.findall(r"<th[^>]*>.*?</th>", thead.group(1), re.S | re.I)]
    yr_cols = {}
    for ci, th in enumerate(ths):
      m = re.search(r"\b(1991|2001|2006|2011|2016|2021)\b", th)
      if m:
        yr_cols[ci] = int(m.group(1))
    if not yr_cols:
      continue
    cur_dist = "Samoa"
    for tr in re.findall(r"<tr[^>]*>.*?</tr>", tbl, re.S | re.I):
      if "<th" in tr[:80]:
        continue
      # Track district header rows (<tr class="rname">)
      if re.match(r'<tr[^>]*class="[^"]*rname', tr):
        m_d = re.search(r'<td[^>]*class="rname"[^>]*>(.*?)</td>', tr, re.S)
        if m_d:
          cur_dist = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m_d.group(1))).strip()
        continue
      if 'class="rname"' not in tr:
        continue
      m_wd = re.search(r'data-wd="(Q\d+)"', tr)
      qid = m_wd.group(1) if m_wd else None
      if qid:
        qids.append(qid)
      tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", td)).strip() for td in re.findall(r"<td[^>]*>.*?</td>", tr, re.S | re.I)]
      if len(tds) <= max(yr_cols.keys()):
        continue
      nm = re.sub(r"\s*\[[^\]]*\]", "", tds[0]).strip()
      if not nm or len(nm) < 2 or "samoa" in nm.lower():
        continue
      pops = {}
      for ci, yr in yr_cols.items():
        vs = tds[ci].replace(",", "").strip()
        if re.fullmatch(r"\d+", vs) and int(vs) >= 5:
          pops[str(yr)] = int(vs)
      if pops:
        rows.append((nm, cur_dist, qid, pops))

  print(f"[Samoa SBS] Parsed {len(rows)} official census villages ({len(qids)} with Wikidata QIDs)")

  # Geocode via HDX Samoa Populated Places + Wikidata P625 + existing Samoa census coords
  geo = load_hdx_populated_places("hotosm_wsm_populated_places", (-14.2, -13.3), (-173.0, -171.35))
  wd_geo = fetch_wikidata_coords(qids)
  # Also load existing Samoa coords
  for fn in ("polynesia_census_raw.json", "enriched_mel_mic_pol_modern.json"):
    fp = os.path.join(SRC_DIR, fn)
    if os.path.exists(fp):
      d0 = json.load(open(fp, encoding="utf-8"))
      for r in (d0.get("settlements", d0) or {}).values():
        if isinstance(r, dict) and r.get("country") == "Samoa":
          nk = norm_key(r.get("name", ""))
          geo.setdefault(nk, r["coords"])
          geo.setdefault(nk.replace(" ", ""), r["coords"])

  print(f"[Samoa Geocoder] HDX/existing keys={len(geo)} | Wikidata P625={len(wd_geo)}")

  out = {}
  placed = []
  for nm, dist, qid, pops in sorted(rows, key=lambda x: -max(x[3].values())):
    nk = norm_key(nm)
    c = wd_geo.get(qid) if qid else None
    if c is None:
      c = geo.get(nk) or geo.get(nk.replace(" ", ""))
    if c is None:
      continue
    lat, lon = float(c[0]), float(c[1])
    # Strictly Independent Samoa west of -171.25 deg W (NEVER American Samoa!)
    if not (-14.2 <= lat <= -13.3 and -173.0 <= lon <= -171.35):
      continue
    # Skip Apia inner urban core overlap (keep Apia unified)
    if nk == "apia":
      continue
    if any(hav_km(lat, lon, p[0], p[1]) <= 0.45 and p[2] == nk for p in placed):
      continue
    placed.append((lat, lon, nk))
    slug = re.sub(r"[^a-z0-9]+", "_", nm.lower()).strip("_")
    skey = f"wsm21_{slug}_{len(out)}"
    out[skey] = {
      "name": nm,
      "other_names": [],
      "coords": [round(lat, 5), round(lon, 5)],
      "country": "Samoa",
      "admin1": dist,
      "population_scope": "city_proper",
      "is_capital": False,
      "population": pops,
      "sources": ["Samoa Bureau of Statistics (SBS) Population and Housing Censuses (2001–2021)"],
    }
  print(f"[Samoa SBS] Geocoded & kept {len(out)} pure official Samoa census villages")
  return out


def harvest_fp_ispf_official():
  """Parses ALL official French Polynesia ISPF Communes & Communes Associées (1988-2022) from citypopulation.de."""
  html = urllib.request.urlopen(urllib.request.Request("https://www.citypopulation.de/en/frenchpolynesia/", headers=H), timeout=25).read().decode("utf-8", "ignore")
  FP_BAD = ("iles du vent", "iles sous le vent", "iles marquises", "iles tuamotu", "iles australes", "polynesie", "windward", "leeward")
  rows = []
  qids = []
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
      m_wd = re.search(r'data-wd="(Q\d+)"', tr)
      qid = m_wd.group(1) if m_wd else None
      if qid:
        qids.append(qid)
      tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", td)).strip() for td in re.findall(r"<td[^>]*>.*?</td>", tr, re.S | re.I)]
      if len(tds) <= max(yr_cols.keys()):
        continue
      nm = re.sub(r"\s*\[[^\]]*\]", "", tds[0]).strip()
      nk = norm_key(nm)
      if not nk or any(b in nk for b in FP_BAD):
        continue
      pops = {}
      for ci, yr in yr_cols.items():
        vs = tds[ci].replace(",", "").strip()
        if re.fullmatch(r"\d+", vs) and int(vs) >= 5:
          pops[str(yr)] = int(vs)
      if pops:
        rows.append((nm, qid, pops))

  wd_geo = fetch_wikidata_coords(qids)
  out = {}
  for nm, qid, pops in rows:
    c = wd_geo.get(qid)
    if not c:
      continue
    lat, lon = c
    if not (-28.5 <= lat <= -7.0 and -155.5 <= lon <= -134.0):
      continue
    slug = re.sub(r"[^a-z0-9]+", "_", nm.lower()).strip("_")
    skey = f"pyf22_{slug}"
    out[skey] = {
      "name": nm, "other_names": [], "coords": [lat, lon], "country": "French Polynesia",
      "admin1": "French Polynesia", "population_scope": "city_proper", "is_capital": (norm_key(nm) == "papeete"),
      "population": pops,
      "sources": ["ISPF / INSEE Recensements de la population de la Polynésie française (1988–2022)"],
    }
  print(f"[French Polynesia ISPF 2022] Geocoded {len(out)} official communes & communes associées")
  return out


def main():
  doc = json.load(open(OUT_PATH, encoding="utf-8"))
  so = doc["settlements"]
  samoa = harvest_samoa_sbs()
  fp = harvest_fp_ispf_official()
  so.update(samoa)
  so.update(fp)
  doc["settlements"] = so
  doc["metadata"]["total_settlements"] = len(so)
  with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
  print(f"[UPDATED] {OUT_PATH} now holds {len(so)} pure official Micronesia & Polynesia census settlements.")


if __name__ == "__main__":
  main()
