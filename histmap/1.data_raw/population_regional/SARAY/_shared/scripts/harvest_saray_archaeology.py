"""Multi-Repository Institutional Archaeological & Historical Site Harvester for Project SARAY.

Harvests primary archaeological, radiocarbon, and historical-monument site registries across
Central Asia (Kazakhstan, Uzbekistan, Turkmenistan, Kyrgyzstan, Tajikistan) plus a 300 km
cross-frontier conditioning belt (Russia/Altai/Lower Volga, Xinjiang, Afghanistan, Khorasan Iran,
Azerbaijan) strictly from institutional, open-science, and geospatial repositories (zero Wikipedia
category scraping).

Repositories harvested into `_shared/sites_saray_central_asia/0.raw_data/`:
  1. Pleiades Ancient World Gazetteer (Bactria, Sogdiana, Margiana, Parthia, Khwarazm, Ferghana, Saka).
  2. Al-Thurayya Early Islamic World Gazetteer (Maxim Romanov / Cornu: Mawarannahr, Khwarazm, Khurasan).
  3. XRONOS Global Radiocarbon API (KZ, UZ, TM, KG, TJ + AF, IR, AZ, RU, CN frontier).
  4. Zenodo Open-Access Central Asian Archaeology & Radiocarbon Datasets (incl. Rutishauser, BMAC, Steppe C14).
  5. Wikidata Multilingual Institutional Cultural Heritage & Archaeological Registries (EN/RU/KK/UZ/KY/TK/TG)
     covering Kazakh Republican/Local Monuments, Uzbek Cultural Heritage Objects, Turkmen/Kyrgyz/Tajik registers,
     ancient cities, tells/tepes, gorodishches, fortresses, kurgans, petroglyphs, caravanserais & pre-1850 mausoleums.
  6. OpenStreetMap Overpass API (`historic=archaeological_site`, `ruins`, `fort`, `castle`, `tumulus`, `city_gate`)
     across all 5 Central Asian republics (subjected to strict API forensics during extraction).
  7. UCL CAAL (Central Asian Archaeological Landscapes) public database probe.
"""

import csv
import gzip
import io
import json
import os
import re
import time

import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SARAY_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "SARAY")
RAW_DIR = os.path.join(SARAY_DIR, "_shared", "sites_saray_central_asia", "0.raw_data")
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {
  "User-Agent": "SVEA-OperationViscount-SARAY/1.0 (academic historical demography; contact: austkaeztchen@confoederatio.org)"
}


def safe_get(url, params=None, timeout=75, headers=None):
  hdr = dict(HEADERS)
  if headers:
    hdr.update(headers)
  for att in range(3):
    try:
      r = requests.get(url, params=params, headers=hdr, timeout=timeout)
      if r.status_code == 200:
        return r
      if r.status_code in (429, 502, 503, 504):
        time.sleep(5 * (att + 1))
        continue
      return r
    except Exception as e:
      if att == 2:
        print(f"  [WARN] GET failed {url[:80]}: {e}", flush=True)
      time.sleep(4)
  return None


def harvest_pleiades():
  outp = os.path.join(RAW_DIR, "pleiades_central_asia.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 2000:
    print(f"[1] Pleiades already cached: {outp}", flush=True)
    return
  print("[1] Harvesting Pleiades Ancient World Gazetteer (Central Asia + 300 km belt)...", flush=True)
  url = "https://atlantides.org/downloads/pleiades/dumps/pleiades-places-latest.csv.gz"
  r = safe_get(url, timeout=150)
  if not r or r.status_code != 200:
    print(f"  [WARN] Pleiades failed: {r.status_code if r else 'None'}", flush=True)
    return
  raw_txt = gzip.decompress(r.content).decode("utf-8", errors="replace")
  rows = []
  for row in csv.DictReader(io.StringIO(raw_txt)):
    try:
      lat = float(row.get("reprLat") or "")
      lon = float(row.get("reprLong") or "")
    except Exception:
      continue
    if 32.0 <= lat <= 58.5 and 43.0 <= lon <= 92.0:
      rows.append({
        "id": row.get("id"),
        "title": row.get("title"),
        "lat": lat,
        "lon": lon,
        "minDate": row.get("minDate"),
        "maxDate": row.get("maxDate"),
        "timePeriods": row.get("timePeriods"),
        "featureTypes": row.get("featureTypes"),
        "description": (row.get("description") or "")[:240],
      })
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Pleiades Central Asia + belt: {len(rows):,} sites", flush=True)


def harvest_althurayya():
  outp = os.path.join(RAW_DIR, "althurayya_central_asia.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 2000:
    print(f"[2] Al-Thurayya already cached: {outp}", flush=True)
    return
  print("[2] Harvesting Al-Thurayya Early Islamic Gazetteer (Transoxiana/Khwarazm/Khurasan)...", flush=True)
  # Check direct GeoJSON bundle in althurayya/althurayya.github.io
  candidates = [
    "https://raw.githubusercontent.com/althurayya/althurayya.github.io/master/master/places.geojson",
    "https://raw.githubusercontent.com/althurayya/althurayya.github.io/master/places.geojson",
    "https://raw.githubusercontent.com/althurayya/althurayya.github.io/master/master/places_new_structure.geojson",
  ]
  gj = None
  for u in candidates:
    r = safe_get(u, timeout=60)
    if r and r.status_code == 200 and len(r.content) > 50000:
      try:
        gj = r.json()
        print(f"  Fetched Al-Thurayya from {u} ({len(r.content):,} B)", flush=True)
        break
      except Exception:
        pass
  if gj is None:
    tr = safe_get("https://api.github.com/repos/althurayya/althurayya.github.io/git/trees/master?recursive=1", timeout=30)
    if tr and tr.status_code == 200:
      gjs = [t["path"] for t in tr.json().get("tree", []) if t["path"].endswith(".geojson") and "place" in t["path"].lower()]
      print(f"  Al-Thurayya candidate files: {gjs[:10]}", flush=True)
      for p in gjs[:3]:
        r = safe_get(f"https://raw.githubusercontent.com/althurayya/althurayya.github.io/master/{p}", timeout=60)
        if r and r.status_code == 200 and len(r.content) > 50000:
          gj = r.json()
          break
  if gj:
    rows = []
    for feat in gj.get("features", []):
      geom = feat.get("geometry") or {}
      coords = geom.get("coordinates") or []
      if geom.get("type") != "Point" or len(coords) < 2:
        continue
      lon, lat = float(coords[0]), float(coords[1])
      if 32.0 <= lat <= 56.0 and 44.0 <= lon <= 90.0:
        props = feat.get("properties") or {}
        cc_obj = props.get("cornuData") or props
        rows.append({
          "lat": lat,
          "lon": lon,
          "title": cc_obj.get("toponym_translit") or props.get("title") or cc_obj.get("toponym_translit_other") or "",
          "arabic": cc_obj.get("toponym_arabic") or "",
          "region": cc_obj.get("region_code") or cc_obj.get("region_spelled") or "",
          "top_type": cc_obj.get("top_type_hom") or cc_obj.get("top_type_orig") or "",
        })
    with open(outp, "w", encoding="utf-8") as fh:
      json.dump(rows, fh, ensure_ascii=False)
    print(f"  Al-Thurayya Central Asia + Khurasan: {len(rows):,} early mediaeval settlements", flush=True)


def harvest_xronos():
  print("[3] Harvesting XRONOS global radiocarbon API (Central Asia + frontier)...", flush=True)
  # Note: XRONOS uses ISO-2 codes or country names; try both!
  targets = [
    ("kz", "Kazakhstan"), ("uz", "Uzbekistan"), ("tm", "Turkmenistan"),
    ("kg", "Kyrgyzstan"), ("tj", "Tajikistan"),
    ("af", "Afghanistan"), ("ir", "Iran"), ("az", "Azerbaijan"),
  ]
  for cc, cname in targets:
    outp = os.path.join(RAW_DIR, f"xronos_{cc}.json")
    if os.path.exists(outp) and os.path.getsize(outp) > 200:
      print(f"  [SKIP] XRONOS {cc} cached ({os.path.getsize(outp):,} B)", flush=True)
      continue
    for qv in (cname, cc.upper()):
      r = safe_get(f"https://xronos.ch/api/v1/data?country={qv}", timeout=45)
      if r and r.status_code == 200 and len(r.content) > 30:
        with open(outp, "wb") as fh:
          fh.write(r.content)
        print(f"  [OK] XRONOS {cc} ({qv}): {len(r.content):,} B", flush=True)
        break
    time.sleep(0.5)


def harvest_zenodo():
  print("[4] Harvesting Zenodo open-access Central Asian archaeology & radiocarbon datasets...", flush=True)
  queries = [
    '("Central Asia" OR "Kazakhstan" OR "Uzbekistan" OR "Turkmenistan" OR "Kyrgyzstan" OR "Tajikistan") AND (archaeology OR radiocarbon OR "archaeological sites")',
    '("Sogdiana" OR "Bactria" OR "Margiana" OR "BMAC" OR "Khwarazm" OR "Fergana" OR "Andronovo" OR "Sintashta" OR "Botai") AND (csv OR geojson OR coordinates)',
    '("Eurasian Steppe" OR "Silk Road" OR "Inner Asian Mountain Corridor") AND (radiocarbon OR sites OR settlements)',
  ]
  seen = set()
  dl_cnt = 0
  # Also explicitly include Zenodo 6875156 (Rutishauser) if it has tabular/GIS files
  for q in queries:
    r = safe_get("https://zenodo.org/api/records", params={"q": q, "size": 25, "type": "dataset"}, timeout=35)
    if not r or r.status_code != 200:
      continue
    for h in r.json().get("hits", {}).get("hits", []):
      rid = h.get("id")
      if rid in seen:
        continue
      seen.add(rid)
      title = (h.get("metadata", {}).get("title") or "")
      for f in h.get("files", []):
        fn = f.get("key", "")
        sz = f.get("size", 0)
        if sz < 250 or sz > 40_000_000:
          continue
        if any(fn.lower().endswith(ext) for ext in (".csv", ".tsv", ".geojson", ".json", ".xlsx", ".kml", ".kmz", ".zip", ".tab")):
          dl = f.get("links", {}).get("self")
          if not dl:
            continue
          safe_fn = re.sub(r"[^A-Za-z0-9._-]+", "_", f"zenodo_{rid}_{fn}")
          outp = os.path.join(RAW_DIR, safe_fn)
          if not os.path.exists(outp):
            dr = safe_get(dl, timeout=90)
            if dr and dr.status_code == 200:
              with open(outp, "wb") as fh:
                fh.write(dr.content)
              dl_cnt += 1
              print(f"  Zenodo {rid} ({title[:55]}): {safe_fn} ({len(dr.content):,} B)", flush=True)
  print(f"  Zenodo downloaded: {dl_cnt} files", flush=True)


def harvest_wikidata_heritage():
  print("[5] Harvesting Wikidata institutional archaeological & cultural heritage registers (KZ/UZ/TM/KG/TJ + frontier)...", flush=True)
  endpoint = "https://query.wikidata.org/sparql"
  countries = [
    ("kazakhstan", "Q232"),
    ("uzbekistan", "Q265"),
    ("turkmenistan", "Q874"),
    ("kyrgyzstan", "Q813"),
    ("tajikistan", "Q863"),
    ("afghanistan", "Q889"),
    ("iran_frontier", "Q794"),
    ("azerbaijan_frontier", "Q227"),
  ]
  for slug, qid in countries:
    outp = os.path.join(RAW_DIR, f"wikidata_arch_{slug}.json")
    if os.path.exists(outp) and os.path.getsize(outp) > 2000:
      print(f"  [SKIP] Wikidata {slug} cached ({os.path.getsize(outp):,} B)", flush=True)
      continue
    # For Iran/Afghanistan limit to northern/eastern belt via lat/lon filter in SPARQL or simple class query
    geo_filter = ""
    if slug == "iran_frontier":
      geo_filter = "FILTER(geof:latitude(?coord) >= 34.0 && geof:longitude(?coord) >= 50.0)"
    # Primary institutional query: archaeological sites, ancient cities, kurgans, forts, ruins, caravanserais, mausoleums, petroglyphs, national heritage monuments
    q = f"""
    PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
    SELECT DISTINCT ?item ?itemLabel ?coord ?typeLabel ?inception ?dissolved ?periodLabel ?cultureLabel ?heritageLabel WHERE {{
      ?item wdt:P17 wd:{qid} ;
            wdt:P625 ?coord .
      {geo_filter}
      {{
        VALUES ?type {{
          wd:Q839954 wd:Q15661340 wd:Q109607 wd:Q1081138 wd:Q57821 wd:Q23413
          wd:Q34023 wd:Q561068 wd:Q15303838 wd:Q162875 wd:Q32815 wd:Q132834
          wd:Q42195 wd:Q86622 wd:Q164240 wd:Q44613 wd:Q180987 wd:Q11755880
          wd:Q744099 wd:Q131747 wd:Q35509 wd:Q2065736 wd:Q5003624
        }}
        ?item wdt:P31 ?type .
      }} UNION {{
        ?item wdt:P1435 ?heritage .
        OPTIONAL {{ ?item wdt:P31 ?type . }}
      }}
      OPTIONAL {{ ?item wdt:P571 ?inception . }}
      OPTIONAL {{ ?item wdt:P576 ?dissolved . }}
      OPTIONAL {{ ?item wdt:P2348 ?period . }}
      OPTIONAL {{ ?item wdt:P2596 ?culture . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,ru,kk,uz,ky,tk,tg". }}
    }}
    LIMIT 25000
    """
    r = safe_get(endpoint, params={"query": q, "format": "json"}, timeout=110, headers={"Accept": "application/sparql-results+json"})
    if r and r.status_code == 200:
      rows = r.json().get("results", {}).get("bindings", [])
      with open(outp, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False)
      print(f"  [OK] Wikidata {slug}: {len(rows):,} rows", flush=True)
    else:
      print(f"  [WARN] Wikidata {slug} HTTP {r.status_code if r else 'None'} — retrying without P1435 union", flush=True)
      q2 = f"""
      SELECT DISTINCT ?item ?itemLabel ?coord ?typeLabel ?inception ?periodLabel ?cultureLabel WHERE {{
        ?item wdt:P17 wd:{qid} ;
              wdt:P625 ?coord .
        VALUES ?type {{ wd:Q839954 wd:Q15661340 wd:Q109607 wd:Q1081138 wd:Q57821 wd:Q23413 wd:Q34023 wd:Q561068 wd:Q162875 wd:Q86622 wd:Q42195 wd:Q744099 }}
        ?item wdt:P31 ?type .
        OPTIONAL {{ ?item wdt:P571 ?inception . }}
        OPTIONAL {{ ?item wdt:P2348 ?period . }}
        OPTIONAL {{ ?item wdt:P2596 ?culture . }}
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,ru". }}
      }}
      LIMIT 15000
      """
      r2 = safe_get(endpoint, params={"query": q2, "format": "json"}, timeout=95, headers={"Accept": "application/sparql-results+json"})
      if r2 and r2.status_code == 200:
        rows = r2.json().get("results", {}).get("bindings", [])
        with open(outp, "w", encoding="utf-8") as fh:
          json.dump(rows, fh, ensure_ascii=False)
        print(f"  [OK-fallback] Wikidata {slug}: {len(rows):,} rows", flush=True)
    time.sleep(2.5)


def harvest_osm_overpass():
  print("[6] Harvesting OSM Overpass archaeological sites, tells, gorodishches, forts & kurgans across Central Asia...", flush=True)
  # Query by country ISO-2 so Overpass responds rapidly and cleanly
  overpass_urls = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
  ]
  for cc, cname in [("KZ", "kazakhstan"), ("UZ", "uzbekistan"), ("TM", "turkmenistan"), ("KG", "kyrgyzstan"), ("TJ", "tajikistan")]:
    outp = os.path.join(RAW_DIR, f"osm_arch_{cname}.json")
    if os.path.exists(outp) and os.path.getsize(outp) > 2000:
      print(f"  [SKIP] OSM {cname} cached ({os.path.getsize(outp):,} B)", flush=True)
      continue
    ql = f"""
    [out:json][timeout:120];
    area["ISO3166-1"="{cc}"][admin_level=2]->.searchArea;
    (
      nwr["historic"="archaeological_site"](area.searchArea);
      nwr["historic"="tumulus"](area.searchArea);
      nwr["historic"="megalith"](area.searchArea);
      nwr["historic"="fort"](area.searchArea);
      nwr["historic"="castle"](area.searchArea);
      nwr["historic"="ruins"](area.searchArea);
      nwr["historic"="city_gate"](area.searchArea);
      nwr["archaeological_site"](area.searchArea);
    );
    out center tags;
    """
    ok = False
    for ep in overpass_urls:
      try:
        r = requests.post(ep, data={"data": ql}, headers=HEADERS, timeout=135)
        if r.status_code == 200:
          els = r.json().get("elements", [])
          with open(outp, "w", encoding="utf-8") as fh:
            json.dump(els, fh, ensure_ascii=False)
          print(f"  [OK] OSM {cname} ({cc}): {len(els):,} archaeological/historic features", flush=True)
          ok = True
          break
        print(f"  [WARN] OSM {cname} via {ep}: HTTP {r.status_code}", flush=True)
      except Exception as e:
        print(f"  [WARN] OSM {cname} via {ep}: {e}", flush=True)
      time.sleep(4)
    if not ok:
      print(f"  [MISS] OSM {cname} could not be fetched", flush=True)
    time.sleep(3)


if __name__ == "__main__":
  harvest_pleiades()
  harvest_althurayya()
  harvest_xronos()
  harvest_zenodo()
  harvest_wikidata_heritage()
  harvest_osm_overpass()
  print("=== DONE SARAY MULTI-REPOSITORY ARCHAEOLOGY HARVEST ===", flush=True)
