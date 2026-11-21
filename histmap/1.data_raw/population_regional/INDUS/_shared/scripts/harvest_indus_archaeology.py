"""Multi-Repository Archaeological Harvester for Operation Viscount Project INDUS.

Ingests primary archaeological site registers across South Asia (India, Pakistan,
Bangladesh, Sri Lanka, Nepal, Bhutan, Maldives) plus a 300 km cross-frontier
conditioning belt (Afghanistan, eastern Iran, western Myanmar, Tibet/Xinjiang)
strictly from institutional, open-science, and geospatial repositories (zero
Wikipedia category scraping).
"""

import gzip
import io
import json
import os
import re
import time
import urllib.parse

import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional",
  "INDUS", "_shared", "sites_indus_south_asia", "0.raw_data"
)
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {
  "User-Agent": "SVEA-OperationViscount-INDUS/1.0 (academic historical demography research; contact: austkaeztchen@confoederatio.org)"
}


def safe_get(url, params=None, timeout=60, headers=None):
  hdr = dict(HEADERS)
  if headers:
    hdr.update(headers)
  for attempt in range(3):
    try:
      r = requests.get(url, params=params, headers=hdr, timeout=timeout)
      if r.status_code == 200:
        return r
      if r.status_code in (429, 502, 503, 504):
        time.sleep(4 * (attempt + 1))
        continue
      return r
    except Exception as e:
      if attempt == 2:
        print(f"  [WARN] GET failed {url}: {e}")
      time.sleep(3)
  return None


def harvest_pleiades():
  out_path = os.path.join(RAW_DIR, "pleiades_south_asia.json")
  if os.path.exists(out_path) and os.path.getsize(out_path) > 5000:
    print(f"[1] Pleiades already cached: {out_path}")
    return
  print("[1] Harvesting Pleiades ancient world gazetteer...")
  url = "https://atlantides.org/downloads/pleiades/dumps/pleiades-places-latest.csv.gz"
  r = safe_get(url, timeout=120)
  if not r or r.status_code != 200:
    print(f"  [WARN] Pleiades download failed: {r.status_code if r else 'None'}")
    return
  import csv
  raw_bytes = gzip.decompress(r.content).decode("utf-8", errors="replace")
  reader = csv.DictReader(io.StringIO(raw_bytes))
  rows = []
  for row in reader:
    try:
      lat = float(row.get("reprLat") or "")
      lon = float(row.get("reprLong") or "")
    except Exception:
      continue
    if 0.0 <= lat <= 40.5 and 58.0 <= lon <= 102.0:
      rows.append({
        "id": row.get("id"),
        "title": row.get("title"),
        "lat": lat,
        "lon": lon,
        "minDate": row.get("minDate"),
        "maxDate": row.get("maxDate"),
        "timePeriods": row.get("timePeriods"),
        "featureTypes": row.get("featureTypes"),
        "description": (row.get("description") or "")[:240]
      })
  with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Pleiades South Asia + belt saved: {len(rows)} sites")


def harvest_cambridge_apollo_and_bates():
  print("[2] Probing Cambridge Apollo (Green & Petrie 2018 CAM.32727) & Bates JOAD Indus data...")
  # Resolve DOI 10.17863/CAM.32727 via DataCite / Apollo DSpace API
  for doi, tag in [
    ("10.17863/CAM.32727", "cam_32727"),
    ("10.17863/CAM.10457", "cam_10457"),
    ("10.5334/joad.50", "bates_joad_2019")
  ]:
    try:
      r = safe_get(f"https://api.datacite.org/dois/{doi}", timeout=25)
      if r and r.status_code == 200:
        d = r.json().get("data", {}).get("attributes", {})
        print(f"  DOI {doi}: url={d.get('url')} | title={str(d.get('titles',[{}])[0].get('title',''))[:70]}")
    except Exception as e:
      print(f"  DOI {doi} err: {e}")

  # Try direct Apollo DSpace 7 API search for Indus / Green Petrie / TwoRains / Bates
  try:
    r = safe_get(
      "https://www.repository.cam.ac.uk/server/api/discover/search/objects",
      params={"query": "Indus sites dataset Petrie Green", "size": 10},
      timeout=30
    )
    if r and r.status_code == 200:
      objs = r.json().get("_embedded", {}).get("searchResult", {}).get("_embedded", {}).get("objects", [])
      print(f"  Apollo DSpace search hits: {len(objs)}")
      for obj in objs[:8]:
        idx = obj.get("_embedded", {}).get("indexableObject", {})
        uuid = idx.get("uuid")
        name = idx.get("name", "")[:70]
        handle = idx.get("handle", "")
        print(f"    Apollo: {handle} | {uuid} | {name}")
        if uuid and any(k in name.lower() for k in ("indus", "site", "settlement", "harapp", "archaeobot", "petrie", "green", "mahsa")):
          br = safe_get(f"https://www.repository.cam.ac.uk/server/api/core/items/{uuid}/bundles", timeout=20)
          if br and br.status_code == 200:
            for b in br.json().get("_embedded", {}).get("bundles", []):
              if b.get("name") == "ORIGINAL":
                bs_url = b.get("_links", {}).get("bitstreams", {}).get("href")
                if bs_url:
                  bsr = safe_get(bs_url, timeout=20)
                  if bsr and bsr.status_code == 200:
                    for bs in bsr.json().get("_embedded", {}).get("bitstreams", []):
                      fn = bs.get("name", "")
                      if any(fn.lower().endswith(ext) for ext in (".csv", ".tsv", ".xlsx", ".xls", ".geojson", ".json", ".zip", ".kmz", ".kml")):
                        dl_url = bs.get("_links", {}).get("content", {}).get("href")
                        if dl_url:
                          safe_fn = re.sub(r"[^A-Za-z0-9._-]+", "_", f"apollo_{uuid[:8]}_{fn}")
                          outp = os.path.join(RAW_DIR, safe_fn)
                          if not os.path.exists(outp):
                            dr = safe_get(dl_url, timeout=90)
                            if dr and dr.status_code == 200 and len(dr.content) > 200:
                              with open(outp, "wb") as f:
                                f.write(dr.content)
                              print(f"      Downloaded Apollo file: {safe_fn} ({len(dr.content):,} B)")
  except Exception as e:
    print(f"  [WARN] Apollo API error: {e}")


def harvest_zenodo_south_asia():
  print("[3] Harvesting open-access Zenodo archaeological datasets for South Asia...")
  queries = [
    '("Indus" OR "Harappan") AND ("sites" OR "settlements") AND (archaeology OR radiocarbon)',
    '("India" OR "Pakistan" OR "Sri Lanka" OR "Nepal" OR "Bangladesh") AND "archaeological sites" AND (csv OR geojson OR coordinates)',
    '("South Asia" OR "Deccan" OR "Ganga" OR "Tamil Nadu" OR "Gandhara") AND (radiocarbon OR megalithic OR archaeology) AND dataset'
  ]
  seen_ids = set()
  downloaded = 0
  for q in queries:
    r = safe_get("https://zenodo.org/api/records", params={"q": q, "size": 20, "type": "dataset"}, timeout=30)
    if not r or r.status_code != 200:
      continue
    hits = r.json().get("hits", {}).get("hits", [])
    for h in hits:
      rid = h.get("id")
      if rid in seen_ids:
        continue
      seen_ids.add(rid)
      title = (h.get("metadata", {}).get("title") or "")
      files = h.get("files", [])
      for f in files:
        fn = f.get("key", "")
        fsize = f.get("size", 0)
        if fsize > 45_000_000 or fsize < 300:
          continue
        if any(fn.lower().endswith(ext) for ext in (".csv", ".tsv", ".geojson", ".json", ".xlsx", ".kml", ".kmz", ".zip")):
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
              downloaded += 1
              print(f"  Zenodo {rid} ({title[:55]}): saved {safe_fn} ({len(dr.content):,} B)")
  print(f"  Zenodo total downloaded: {downloaded}")


def harvest_wikidata_south_asia():
  print("[4] Harvesting Wikidata georeferenced archaeological & pre-modern heritage sites across South Asia + frontier...")
  endpoint = "https://query.wikidata.org/sparql"
  # Countries: India Q668, Pakistan Q843, Bangladesh Q902, Sri Lanka Q854, Nepal Q837, Bhutan Q917, Maldives Q826, Afghanistan Q889, Myanmar Q836
  countries = [
    ("india", "Q668"),
    ("pakistan", "Q843"),
    ("bangladesh", "Q902"),
    ("sri_lanka", "Q854"),
    ("nepal", "Q837"),
    ("bhutan", "Q917"),
    ("maldives", "Q826"),
    ("afghanistan", "Q889"),
    ("myanmar", "Q836")
  ]
  # Classes: archaeological site Q839954, ancient city Q15661340, stupa Q180987, megalith Q164240,
  # rock art/cave Q35509, historic fort Q57821, ruined city/ruins Q109607, stepwell Q1542758,
  # Buddhist monastery/vihara Q44613, historic site Q1081138
  for slug, qid in countries:
    outp = os.path.join(RAW_DIR, f"wikidata_arch_{slug}.json")
    if os.path.exists(outp) and os.path.getsize(outp) > 2000:
      print(f"  Wikidata {slug} already cached")
      continue
    query = f"""
    SELECT DISTINCT ?item ?itemLabel ?coord ?classLabel ?inception ?dissolved ?periodLabel ?cultureLabel ?heritageLabel WHERE {{
      ?item wdt:P17 wd:{qid} ;
            wdt:P625 ?coord .
      {{
        VALUES ?class {{ wd:Q839954 wd:Q15661340 wd:Q180987 wd:Q164240 wd:Q109607 wd:Q1081138 wd:Q57821 wd:Q1542758 wd:Q23413 wd:Q12280 }}
        ?item wdt:P31/wdt:P279* ?class .
      }} UNION {{
        ?item wdt:P1435 wd:Q1929004 .
        BIND(wd:Q1929004 AS ?class)
      }}
      OPTIONAL {{ ?item wdt:P571 ?inception . }}
      OPTIONAL {{ ?item wdt:P576 ?dissolved . }}
      OPTIONAL {{ ?item wdt:P2348 ?period . }}
      OPTIONAL {{ ?item wdt:P2596 ?culture . }}
      OPTIONAL {{ ?item wdt:P1435 ?heritage . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 15000
    """
    r = safe_get(endpoint, params={"query": query, "format": "json"}, timeout=90, headers={"Accept": "application/sparql-results+json"})
    if r and r.status_code == 200:
      bindings = r.json().get("results", {}).get("bindings", [])
      with open(outp, "w", encoding="utf-8") as fh:
        json.dump(bindings, fh, ensure_ascii=False)
      print(f"  Wikidata {slug}: {len(bindings):,} rows")
    else:
      print(f"  [WARN] Wikidata {slug} failed (HTTP {r.status_code if r else 'None'}) — retrying split query")
      # Split query without P279* for huge countries like India
      bindings_all = []
      for sub_name, clause in [
        ("arch", "VALUES ?class { wd:Q839954 wd:Q15661340 wd:Q180987 wd:Q164240 wd:Q109607 wd:Q1081138 wd:Q1542758 wd:Q23413 wd:Q57821 } ?item wdt:P31 ?class ."),
        ("asi", "?item wdt:P1435 wd:Q1929004 . BIND(wd:Q1929004 AS ?class)"),
        ("temples_old", "?item wdt:P31 wd:Q842402 ; wdt:P571 ?inception . FILTER(YEAR(?inception) < 1750) BIND(wd:Q842402 AS ?class)")
      ]:
        q2 = f"""
        SELECT DISTINCT ?item ?itemLabel ?coord ?classLabel ?inception ?dissolved ?periodLabel ?cultureLabel ?heritageLabel WHERE {{
          ?item wdt:P17 wd:{qid} ;
                wdt:P625 ?coord .
          {clause}
          OPTIONAL {{ ?item wdt:P571 ?inception . }}
          OPTIONAL {{ ?item wdt:P576 ?dissolved . }}
          OPTIONAL {{ ?item wdt:P2348 ?period . }}
          OPTIONAL {{ ?item wdt:P2596 ?culture . }}
          OPTIONAL {{ ?item wdt:P1435 ?heritage . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 15000
        """
        r2 = safe_get(endpoint, params={"query": q2, "format": "json"}, timeout=90, headers={"Accept": "application/sparql-results+json"})
        if r2 and r2.status_code == 200:
          b2 = r2.json().get("results", {}).get("bindings", [])
          bindings_all.extend(b2)
          print(f"    Wikidata {slug}/{sub_name}: {len(b2):,} rows")
        time.sleep(2)
      if bindings_all:
        with open(outp, "w", encoding="utf-8") as fh:
          json.dump(bindings_all, fh, ensure_ascii=False)
    time.sleep(2)


def harvest_osm_overpass_archaeology():
  print("[5] Harvesting OpenStreetMap historic=archaeological_site & megalithic/ancient forts across South Asia tiles...")
  # Tile South Asia into 6 manageable bounding boxes so Overpass never times out
  tiles = [
    ("nw_pakistan_punjab_indus", 23.0, 60.5, 37.5, 78.5),
    ("gangetic_nepal_north_india", 22.0, 78.5, 32.0, 89.0),
    ("east_india_bangladesh_bhutan", 20.0, 88.5, 30.0, 97.5),
    ("central_west_india_deccan", 15.0, 68.0, 23.5, 88.5),
    ("south_india_tamilakam_kerala", 7.5, 73.5, 15.5, 82.0),
    ("sri_lanka_maldives", -1.0, 72.0, 10.2, 82.5),
  ]
  overpass_urls = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
  ]
  for tname, s, w, n, e in tiles:
    outp = os.path.join(RAW_DIR, f"osm_arch_{tname}.json")
    if os.path.exists(outp) and os.path.getsize(outp) > 2000:
      print(f"  OSM {tname} already cached")
      continue
    q = f"""
    [out:json][timeout:90];
    (
      node["historic"="archaeological_site"]({s},{w},{n},{e});
      way["historic"="archaeological_site"]({s},{w},{n},{e});
      relation["historic"="archaeological_site"]({s},{w},{n},{e});
      node["historic"="megalith"]({s},{w},{n},{e});
      node["historic"="tumulus"]({s},{w},{n},{e});
      node["historic"="ruins"]["archaeological_site"]({s},{w},{n},{e});
      node["historic"="fort"]({s},{w},{n},{e});
      way["historic"="fort"]({s},{w},{n},{e});
    );
    out center tags;
    """
    ok = False
    for ep in overpass_urls:
      try:
        r = requests.post(ep, data={"data": q}, headers=HEADERS, timeout=110)
        if r.status_code == 200:
          els = r.json().get("elements", [])
          with open(outp, "w", encoding="utf-8") as fh:
            json.dump(els, fh, ensure_ascii=False)
          print(f"  OSM {tname}: {len(els):,} elements")
          ok = True
          break
        else:
          print(f"  OSM {tname} via {ep}: HTTP {r.status_code}")
      except Exception as ex:
        print(f"  OSM {tname} via {ep}: ERR {ex}")
      time.sleep(5)
    if not ok:
      print(f"  [WARN] OSM {tname} failed on all mirrors")
    time.sleep(4)


def harvest_p3k14c():
  outp = os.path.join(RAW_DIR, "p3k14c_south_asia.csv")
  if os.path.exists(outp) and os.path.getsize(outp) > 500:
    print("[6] p3k14c already cached")
    return
  print("[6] Harvesting p3k14c global radiocarbon dataset & filtering South Asia...")
  for url in [
    "https://raw.githubusercontent.com/people3k/p3k14c/master/data/p3k14c_2022.06.csv",
    "https://raw.githubusercontent.com/people3k/p3k14c/main/data/p3k14c_2022.06.csv"
  ]:
    r = safe_get(url, timeout=90)
    if r and r.status_code == 200 and len(r.content) > 10000:
      import csv
      rows = []
      reader = csv.DictReader(io.StringIO(r.text))
      fnames = reader.fieldnames
      for row in reader:
        try:
          lat = float(row.get("Lat") or row.get("lat") or "")
          lon = float(row.get("Long") or row.get("lon") or "")
        except Exception:
          continue
        if 0.0 <= lat <= 40.5 and 58.0 <= lon <= 102.0:
          rows.append(row)
      with open(outp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fnames)
        w.writeheader()
        w.writerows(rows)
      print(f"  p3k14c South Asia + belt saved: {len(rows)} rows")
      return
  print("  [WARN] p3k14c direct GitHub raw not found")


if __name__ == "__main__":
  harvest_pleiades()
  harvest_cambridge_apollo_and_bates()
  harvest_zenodo_south_asia()
  harvest_wikidata_south_asia()
  harvest_osm_overpass_archaeology()
  harvest_p3k14c()
  print("DONE harvesting multi-repository archaeology!")
