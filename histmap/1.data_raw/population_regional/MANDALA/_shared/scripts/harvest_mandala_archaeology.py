"""Multi-Repository Archaeological & Historical Heritage Harvester for Operation Viscount Project MANDALA.

Ingests primary archaeological site registers across Mainland and Maritime South-East Asia
(Myanmar, Thailand, Laos, Cambodia, Vietnam, Malaysia, Singapore, Brunei, Indonesia less West New Guinea,
Philippines and Timor-Leste) plus a 300 km cross-frontier conditioning belt (Yunnan, Guangxi, Guangdong,
Hainan, Assam/NE India, Chittagong/Bangladesh, West New Guinea/Papua fringe, northern Australia/Timor Sea)
strictly from institutional, open-science and geospatial repositories (zero Wikipedia category scraping):
  1. XRONOS global radiocarbon API (all 11 MANDALA countries + frontier belt)
  2. Pleiades ancient world gazetteer (South-East Asia emporia)
  3. Zenodo open-access archaeological & radiocarbon datasets (OCSEAN, SE Asia, Angkor, Nusantara, Philippines, Myanmar, Thailand, Vietnam)
  4. Wikidata institutional heritage & archaeological registries (P1435 heritage status incl. Cagar Budaya, PRECUP, CISARK, Fine Arts Dept, Di tich quoc gia; archaeological sites Q839954, ancient cities Q15661340, ruins Q109607, candi/prasat/stupa/temples/forts/palaces/caves)
  5. OpenStreetMap Overpass historic archaeological/ruin/fort/temple-ruin features partitioned into 12 geographic tiles
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
RAW_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional",
  "MANDALA", "_shared", "sites_mandala_southeast_asia", "0.raw_data"
)
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {
  "User-Agent": "SVEA-OperationViscount-MANDALA/1.0 (academic historical demography research; contact: austkaeztchen@confoederatio.org)"
}
WD_ENDPOINT = "https://query.wikidata.org/sparql"


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
        print(f"  [WARN] GET failed {url}: {e}", flush=True)
      time.sleep(3)
  return None


def harvest_xronos():
  print("[1] Harvesting XRONOS radiocarbon API across all 11 MANDALA states + 300 km belt...", flush=True)
  # Copy cached JADE/INDUS xronos where available
  jade_raw = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "sites_east_asia", "0.raw_data")
  indus_raw = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "INDUS", "_shared", "sites_indus_south_asia", "0.raw_data")
  codes = [
    ("mm", "MM"), ("th", "TH"), ("la", "LA"), ("kh", "KH"), ("vn", "VN"),
    ("my", "MY"), ("sg", "SG"), ("bn", "BN"), ("id", "ID"), ("ph", "PH"), ("tl", "TL"),
    ("cn", "CN"), ("in", "IN"), ("bd", "BD"), ("pg", "PG"), ("au", "AU")
  ]
  for cc, iso in codes:
    dst = os.path.join(RAW_DIR, f"xronos_{cc}.json")
    if os.path.exists(dst) and os.path.getsize(dst) > 50:
      print(f"  [SKIP] xronos_{cc}.json cached ({os.path.getsize(dst):,} B)", flush=True)
      continue
    copied = False
    for src_dir in (jade_raw, indus_raw):
      src = os.path.join(src_dir, f"xronos_{cc}.json")
      if os.path.exists(src) and os.path.getsize(src) > 50:
        with open(src, "rb") as s, open(dst, "wb") as d:
          d.write(s.read())
        print(f"  [COPY] xronos_{cc}.json ({os.path.getsize(dst):,} B)", flush=True)
        copied = True
        break
    if copied:
      continue
    for url in (
      f"https://xronos.ch/api/v1/data?country={iso}",
      f"https://xronos.ch/api/v1/data.json?country={iso}"
    ):
      r = safe_get(url, timeout=60)
      if r and r.status_code == 200:
        with open(dst, "wb") as fh:
          fh.write(r.content)
        print(f"  [OK] XRONOS {cc}: {len(r.content):,} B", flush=True)
        break
    time.sleep(0.5)


def harvest_pleiades():
  outp = os.path.join(RAW_DIR, "pleiades_southeast_asia.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 200:
    print(f"[2] Pleiades already cached ({os.path.getsize(outp):,} B)", flush=True)
    return
  print("[2] Harvesting Pleiades ancient world gazetteer (SE Asia + belt)...", flush=True)
  r = safe_get("https://atlantides.org/downloads/pleiades/dumps/pleiades-places-latest.csv.gz", timeout=120)
  if not r or r.status_code != 200:
    print("  [WARN] Pleiades download failed", flush=True)
    return
  raw_text = gzip.decompress(r.content).decode("utf-8", errors="replace")
  rows = []
  for row in csv.DictReader(io.StringIO(raw_text)):
    try:
      lat = float(row.get("reprLat") or "")
      lon = float(row.get("reprLong") or "")
    except Exception:
      continue
    if -13.0 <= lat <= 31.0 and 89.0 <= lon <= 138.0:
      rows.append({
        "id": row.get("id"), "title": row.get("title"), "lat": lat, "lon": lon,
        "minDate": row.get("minDate"), "maxDate": row.get("maxDate"),
        "timePeriods": row.get("timePeriods"), "featureTypes": row.get("featureTypes"),
        "description": (row.get("description") or "")[:240]
      })
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  [OK] Pleiades SE Asia + belt: {len(rows)} places", flush=True)


def harvest_zenodo():
  print("[3] Harvesting open-access Zenodo archaeological & radiocarbon datasets for South-East Asia...", flush=True)
  queries = [
    '("Southeast Asia" OR "South-East Asia" OR "OCSEAN") AND (archaeology OR radiocarbon OR sites) AND (csv OR geojson OR dataset)',
    '("Cambodia" OR "Angkor" OR "Thailand" OR "Vietnam" OR "Myanmar" OR "Laos") AND (archaeology OR radiocarbon OR temple OR settlement) AND dataset',
    '("Indonesia" OR "Java" OR "Sumatra" OR "Borneo" OR "Sulawesi" OR "Philippines" OR "Timor" OR "Wallacea") AND (archaeology OR radiocarbon OR austronesian OR prehistoric) AND dataset',
    '("Ban Chiang" OR "Dong Son" OR "Pyu" OR "Bagan" OR "Srivijaya" OR "Majapahit" OR "Hoabinhian") AND (archaeology OR radiocarbon OR sites)'
  ]
  seen = set()
  downloaded = 0
  for q in queries:
    r = safe_get("https://zenodo.org/api/records", params={"q": q, "size": 25, "type": "dataset"}, timeout=40)
    if not r or r.status_code != 200:
      continue
    for h in r.json().get("hits", {}).get("hits", []):
      rid = h.get("id")
      if rid in seen:
        continue
      seen.add(rid)
      title = (h.get("metadata", {}).get("title") or "")
      tl = title.lower()
      if not any(k in tl for k in (
        "southeast", "south-east", "sea", "cambodia", "angkor", "thailand", "vietnam", "myanmar", "burma",
        "laos", "indonesia", "java", "sumatra", "borneo", "sulawesi", "philippines", "timor", "wallacea",
        "malaysia", "malay", "brunei", "singapore", "austronesian", "radiocarbon", "p3k14c", "archaeo",
        "khmer", "champa", "bagan", "pyu", "ocsean", "pacific", "island", "holocene", "pleistocene", "rice"
      )):
        continue
      for f in h.get("files", []):
        fn = f.get("key", "")
        fsize = f.get("size", 0)
        if fsize > 40_000_000 or fsize < 250:
          continue
        if any(fn.lower().endswith(ext) for ext in (".csv", ".tsv", ".geojson", ".json", ".xlsx", ".kml", ".kmz", ".zip")):
          dl = f.get("links", {}).get("self")
          if not dl:
            continue
          safe_fn = re.sub(r"[^A-Za-z0-9._-]+", "_", f"zenodo_{rid}_{fn}")
          outp = os.path.join(RAW_DIR, safe_fn)
          if os.path.exists(outp) and os.path.getsize(outp) > 200:
            continue
          dr = safe_get(dl, timeout=90)
          if dr and dr.status_code == 200 and len(dr.content) > 200:
            with open(outp, "wb") as out:
              out.write(dr.content)
            downloaded += 1
            print(f"  [OK] {safe_fn} ({len(dr.content):,} B) | {title[:65]}", flush=True)
    time.sleep(0.5)
  print(f"  Zenodo newly downloaded: {downloaded} files", flush=True)


def run_sparql(query, out_name, label):
  outp = os.path.join(RAW_DIR, out_name)
  if os.path.exists(outp) and os.path.getsize(outp) > 1000:
    print(f"  [SKIP] {label} cached ({os.path.getsize(outp):,} B)", flush=True)
    return
  for att in range(3):
    try:
      r = requests.get(
        WD_ENDPOINT,
        params={"query": query, "format": "json"},
        headers={**HEADERS, "Accept": "application/sparql-results+json"},
        timeout=110
      )
      if r.status_code == 200:
        rows = r.json().get("results", {}).get("bindings", [])
        with open(outp, "w", encoding="utf-8") as fh:
          json.dump(rows, fh, ensure_ascii=False)
        print(f"  [OK] {label}: {len(rows):,} rows", flush=True)
        return
      print(f"  [WARN] {label} HTTP {r.status_code} (att {att+1})", flush=True)
      time.sleep(5 * (att + 1))
    except Exception as e:
      print(f"  [ERR] {label}: {e}", flush=True)
      time.sleep(5)


def harvest_wikidata_heritage():
  print("[4] Harvesting Wikidata institutional archaeological & heritage registers (all 11 MANDALA states)...", flush=True)
  countries = [
    ("myanmar", "Q836", "Myanmar Arch & Heritage"),
    ("thailand", "Q869", "Thailand Arch & Heritage"),
    ("laos", "Q819", "Laos Arch & Heritage"),
    ("cambodia", "Q424", "Cambodia Arch & Heritage"),
    ("vietnam", "Q881", "Vietnam Arch & Heritage"),
    ("malaysia", "Q833", "Malaysia Arch & Heritage"),
    ("singapore", "Q334", "Singapore Arch & Heritage"),
    ("brunei", "Q921", "Brunei Arch & Heritage"),
    ("indonesia", "Q252", "Indonesia Arch & Heritage"),
    ("philippines", "Q928", "Philippines Arch & Heritage"),
    ("timor_leste", "Q574", "Timor-Leste Arch & Heritage"),
  ]
  # Broad archaeological, monumental, religious-historical, fort, cave, ancient-city, and national heritage registry (P1435) classes
  type_vals = (
    "wd:Q839954 wd:Q15661340 wd:Q109607 wd:Q180987 wd:Q200265 wd:Q1032404 wd:Q217102 "
    "wd:Q44539 wd:Q842402 wd:Q5393308 wd:Q32815 wd:Q44613 wd:Q57821 wd:Q23413 wd:Q16560 "
    "wd:Q35509 wd:Q164240 wd:Q1081138 wd:Q11755880 wd:Q1542758 wd:Q2065736 wd:Q16970 wd:Q2977"
  )
  for slug, qid, label in countries:
    q = f"""
    SELECT DISTINCT ?item ?itemLabel ?coord ?inception ?periodLabel ?cultureLabel ?typeLabel ?heritageLabel WHERE {{
      ?item wdt:P17 wd:{qid} ;
            wdt:P625 ?coord .
      {{
        VALUES ?type {{ {type_vals} }}
        ?item wdt:P31 ?type .
      }} UNION {{
        ?item wdt:P1435 ?heritage .
        OPTIONAL {{ ?item wdt:P31 ?type . }}
      }}
      OPTIONAL {{ ?item wdt:P571 ?inception . }}
      OPTIONAL {{ ?item wdt:P2348 ?period . }}
      OPTIONAL {{ ?item wdt:P2596 ?culture . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,id,vi,th,ms,tl,fr". }}
    }}
    LIMIT 25000
    """
    run_sparql(q, f"wikidata_arch_{slug}.json", label)
    time.sleep(2.0)


def harvest_overpass_archaeology():
  print("[5] Harvesting OpenStreetMap Overpass historic archaeological_site/ruins/fort/citywalls across SE Asia...", flush=True)
  tiles = [
    ("myanmar_n", 18.0, 92.0, 28.6, 101.5),
    ("myanmar_s_thai_w", 6.0, 94.0, 18.0, 101.5),
    ("thai_laos_n", 15.0, 101.5, 22.8, 109.5),
    ("cambodia_s_vn", 8.5, 101.5, 15.0, 109.6),
    ("vietnam_n", 15.0, 102.0, 23.5, 109.6),
    ("malay_sumatra_n", 0.0, 95.0, 7.5, 105.5),
    ("sumatra_s_java_w", -9.0, 99.0, 0.0, 110.5),
    ("java_e_bali_ntt", -11.2, 110.5, -5.0, 127.5),
    ("borneo_sulawesi", -6.0, 108.5, 7.5, 125.5),
    ("maluku_timor", -10.5, 125.0, 3.0, 135.0),
    ("philippines_n", 12.5, 117.0, 21.2, 127.0),
    ("philippines_s", 4.5, 116.5, 12.5, 127.0),
  ]
  endpoints = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
  ]
  for slug, s, w, n, e in tiles:
    outp = os.path.join(RAW_DIR, f"osm_arch_{slug}.json")
    if os.path.exists(outp) and os.path.getsize(outp) > 200:
      print(f"  [SKIP] osm_arch_{slug}.json cached ({os.path.getsize(outp):,} B)", flush=True)
      continue
    ql = (
      f"[out:json][timeout:60];("
      f'nwr["historic"~"^(archaeological_site|ruins|fort|citywalls|castle|palace|battlefield|tumulus|megalith|monument|memorial|church|wayside_shrine)$"]({s},{w},{n},{e});'
      f'nwr["heritage"]({s},{w},{n},{e});'
      f");out center tags;"
    )
    ok = False
    for ep in endpoints:
      try:
        r = requests.post(ep, data={"data": ql}, headers=HEADERS, timeout=75)
        if r.status_code == 200:
          data = r.json()
          els = data.get("elements", [])
          compact = []
          for el in els:
            tags = el.get("tags") or {}
            # Keep only genuine archaeological, ruin, fort, historic temple/heritage sites (skip modern street memorials)
            h = str(tags.get("historic") or "")
            if h in ("memorial", "monument", "wayside_shrine") and not tags.get("heritage") and not tags.get("start_date") and not tags.get("site_type"):
              continue
            lat = el.get("lat") or (el.get("center") or {}).get("lat")
            lon = el.get("lon") or (el.get("center") or {}).get("lon")
            if lat is None or lon is None:
              continue
            compact.append({
              "id": el.get("id"),
              "name": tags.get("name:en") or tags.get("name") or "",
              "name_local": tags.get("name") or "",
              "lat": round(float(lat), 5),
              "lon": round(float(lon), 5),
              "historic": h,
              "site_type": tags.get("site_type") or "",
              "heritage": tags.get("heritage") or tags.get("heritage:operator") or "",
              "start_date": tags.get("start_date") or "",
              "religion": tags.get("religion") or "",
              "wikidata": tags.get("wikidata") or ""
            })
          with open(outp, "w", encoding="utf-8") as fh:
            json.dump(compact, fh, ensure_ascii=False)
          print(f"  [OK] OSM {slug}: {len(compact):,} heritage/arch sites (from {len(els):,} raw)", flush=True)
          ok = True
          break
        else:
          print(f"  [WARN] OSM {slug} ({ep}) HTTP {r.status_code}", flush=True)
      except Exception as ex:
        print(f"  [WARN] OSM {slug} ({ep}): {ex}", flush=True)
      time.sleep(3)
    if not ok:
      print(f"  [FAIL] OSM {slug} skipped after retries", flush=True)
    time.sleep(2.5)


if __name__ == "__main__":
  harvest_xronos()
  harvest_pleiades()
  harvest_zenodo()
  harvest_wikidata_heritage()
  harvest_overpass_archaeology()
  print("=== DONE MANDALA MULTI-REPOSITORY ARCHAEOLOGY HARVEST ===", flush=True)
