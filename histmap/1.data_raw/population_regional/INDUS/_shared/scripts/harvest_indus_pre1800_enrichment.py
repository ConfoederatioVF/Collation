"""Wave 3 Multi-Repository Pre-1800 Historical & Archaeological Harvester for Project INDUS.

Harvests open-access primary datasets to eliminate pre-1800 South Asian settlement sparsity:
  1. Complete tiled OpenStreetMap Overpass historic forts, archaeological sites, ancient ruins,
     palaces, stepwells, monasteries, and pre-modern monuments across all 12 South Asia tiles
     (filling the previously empty Central/West/Deccan and East/Bengal/Assam/Bhutan tiles).
  2. Sharded Wikidata SPARQL queries for:
     - Pre-1800 dated towns, cities, capitals & historic settlements across all 7 INDUS states
     - Indian Princely States & historical kingdom capitals
     - Forts, citadels, stepwells, ancient temples, Buddhist stupas/viharas, Jain tirthas,
       historic mosques/dargahs, and Sri Lankan/Nepali/Bhutanese/Maldivian heritage seats
  3. Zenodo open-science archaeological datasets (Indian Palaeolithic IARs 13627361, Sopara,
     Harappan/Indus/Deccan/South Asia site gazetteers) + Bates (2019) JOAD Harappan sites.
"""

import json
import os
import re
import time
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional",
  "INDUS", "_shared", "sites_indus_south_asia", "0.raw_data"
)
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {
  "User-Agent": "SVEA-OperationViscount-INDUS/2.0 (academic historical demography; contact: austkaeztchen@confoederatio.org)"
}
WD_ENDPOINT = "https://query.wikidata.org/sparql"


def safe_get(arg0_url, arg1_params=None, arg2_timeout=90, arg3_headers=None):
  hdr = dict(HEADERS)
  if arg3_headers:
    hdr.update(arg3_headers)
  for attempt in range(3):
    try:
      r = requests.get(arg0_url, params=arg1_params, headers=hdr, timeout=arg2_timeout)
      if r.status_code == 200:
        return r
      if r.status_code in (429, 502, 503, 504):
        time.sleep(6 * (attempt + 1))
        continue
      return r
    except Exception as ex:
      print(f"    [WARN] GET {arg0_url[:70]} attempt {attempt + 1}: {ex}", flush=True)
      time.sleep(5)
  return None


def run_sparql(arg0_query, arg1_filename, arg2_label):
  outp = os.path.join(RAW_DIR, arg1_filename)
  if os.path.exists(outp) and os.path.getsize(outp) > 2000:
    print(f"  [SKIP] {arg2_label} cached ({os.path.getsize(outp):,} B)", flush=True)
    return
  r = safe_get(
    WD_ENDPOINT,
    arg1_params={"query": arg0_query, "format": "json"},
    arg2_timeout=110,
    arg3_headers={"Accept": "application/sparql-results+json"},
  )
  if r and r.status_code == 200:
    rows = r.json().get("results", {}).get("bindings", [])
    with open(outp, "w", encoding="utf-8") as fh:
      json.dump(rows, fh, ensure_ascii=False)
    print(f"  [OK] {arg2_label}: {len(rows):,} rows", flush=True)
  else:
    print(f"  [WARN] {arg2_label} failed (HTTP {r.status_code if r else 'None'})", flush=True)
  time.sleep(2.5)


def harvest_wikidata_pre1800_enriched():
  print("[1] Harvesting sharded Wikidata pre-1800 South Asian settlements, forts, capitals, temples & monuments...", flush=True)

  # 1A. Pre-1800 dated populated places / towns / cities / villages / tehsils across ALL 7 countries
  for slug, qid, label in [
    ("in", "Q668", "India Pre-1800 Inception Settlements"),
    ("pk", "Q843", "Pakistan Pre-1800 Inception Settlements"),
    ("bd", "Q902", "Bangladesh Pre-1800 Inception Settlements"),
    ("lk", "Q854", "Sri Lanka Pre-1800 Inception Settlements"),
    ("np", "Q837", "Nepal Pre-1800 Inception Settlements"),
    ("bt", "Q917", "Bhutan Pre-1800 Inception Settlements"),
    ("mv", "Q826", "Maldives Pre-1800 Inception Settlements"),
  ]:
    run_sparql(f"""
    SELECT DISTINCT ?item ?itemLabel ?coord ?inception ?dissolved ?typeLabel ?altLabel WHERE {{
      ?item wdt:P17 wd:{qid} ;
            wdt:P625 ?coord ;
            wdt:P571 ?inception .
      FILTER(YEAR(?inception) <= 1800)
      VALUES ?type {{ wd:Q515 wd:Q3957 wd:Q532 wd:Q486972 wd:Q1549591 wd:Q15661340 wd:Q839954 wd:Q2264924 wd:Q13218690 wd:Q350895 wd:Q200250 wd:Q5119 }}
      ?item wdt:P31 ?type .
      OPTIONAL {{ ?item wdt:P576 ?dissolved . }}
      OPTIONAL {{ ?item skos:altLabel ?altLabel . FILTER(LANG(?altLabel) = "en") }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 15000
    """, f"wd_pre1800_settlements_{slug}.json", label)

  # 1B. Indian Princely States & Historical Kingdoms/Empires Capitals in South Asia
  run_sparql("""
  SELECT DISTINCT ?state ?stateLabel ?cap ?capLabel ?coord ?inception ?dissolved WHERE {
    {
      ?state wdt:P31 wd:Q1336152 ;
             wdt:P36 ?cap .
    } UNION {
      ?state wdt:P31 wd:Q3024240 ;
             wdt:P36 ?cap .
      ?cap wdt:P17 ?ctry .
      VALUES ?ctry { wd:Q668 wd:Q843 wd:Q902 wd:Q854 wd:Q837 wd:Q917 wd:Q826 }
    }
    ?cap wdt:P625 ?coord .
    OPTIONAL { ?state wdt:P571 ?inception . }
    OPTIONAL { ?state wdt:P576 ?dissolved . }
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
  }
  LIMIT 10000
  """, "wd_south_asia_princely_and_kingdom_capitals.json", "South Asia Princely States & Historical Kingdom Capitals")

  # 1C. India Forts, Castles, Stepwells, Palaces, Hill Forts (major pre-1800 qasba/citadel anchors)
  run_sparql("""
  SELECT DISTINCT ?item ?itemLabel ?coord ?inception ?periodLabel ?typeLabel WHERE {
    ?item wdt:P17 wd:Q668 ;
          wdt:P625 ?coord .
    VALUES ?type { wd:Q57821 wd:Q23413 wd:Q1542758 wd:Q16560 wd:Q744099 wd:Q1785071 wd:Q188509 wd:Q12323 }
    ?item wdt:P31 ?type .
    OPTIONAL { ?item wdt:P571 ?inception . }
    OPTIONAL { ?item wdt:P2348 ?period . }
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
  }
  LIMIT 15000
  """, "wd_india_forts_stepwells_palaces.json", "India Forts, Castles, Stepwells & Palaces")

  # 1D. India Hindu, Jain & Buddhist Temples/Monasteries/Stupas/Caves (with coordinates, sharded by type so fast)
  for slug, qtype, lbl in [
    ("buddhist_stupas_viharas", "wd:Q180987 wd:Q44613 wd:Q160742 wd:Q5393308 wd:Q623525", "India Buddhist Stupas, Viharas & Monasteries"),
    ("jain_temples", "wd:Q3517488 wd:Q1929004", "India Jain Temples & ASI Heritage"),
    ("hindu_temples_dated", "wd:Q842402", "India Hindu Temples (All Georeferenced)"),
    ("historic_mosques_dargahs", "wd:Q32815 wd:Q1165822 wd:Q162875", "India Historic Mosques, Dargahs & Mausoleums"),
  ]:
    extra_filter = "OPTIONAL { ?item wdt:P571 ?inception . }" if slug != "hindu_temples_dated" else "OPTIONAL { ?item wdt:P571 ?inception . } OPTIONAL { ?item wdt:P1435 ?her . }"
    run_sparql(f"""
    SELECT DISTINCT ?item ?itemLabel ?coord ?inception ?periodLabel ?typeLabel WHERE {{
      ?item wdt:P17 wd:Q668 ;
            wdt:P625 ?coord .
      VALUES ?type {{ {qtype} }}
      ?item wdt:P31 ?type .
      {extra_filter}
      OPTIONAL {{ ?item wdt:P2348 ?period . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 18000
    """, f"wd_india_{slug}.json", lbl)


def harvest_osm_complete_tiles():
  print("[2] Harvesting complete 12-tile OSM Overpass historic/archaeological corpus across South Asia...", flush=True)
  tiles = [
    ("tile01_rajasthan_gujarat", 20.0, 68.0, 30.2, 76.5),
    ("tile02_maharashtra_goa_konkan", 15.0, 72.5, 22.0, 80.5),
    ("tile03_mp_chhattisgarh_vidarbha", 18.0, 75.5, 26.5, 84.5),
    ("tile04_karnataka_telangana_ap", 11.5, 74.0, 19.5, 84.8),
    ("tile05_odisha_jharkhand_bihar", 19.0, 82.0, 27.5, 88.5),
    ("tile06_wb_bangladesh_ne_bhutan", 20.5, 88.0, 29.5, 97.5),
    ("tile07_up_uttarakhand_delhi", 24.0, 76.5, 31.5, 84.5),
    ("tile08_hp_jk_ladakh_punjab", 29.5, 73.5, 37.2, 80.5),
    ("tile09_tamilnadu_kerala", 7.8, 74.5, 13.8, 80.6),
    ("tile10_sri_lanka_maldives", -1.0, 72.0, 10.2, 82.5),
    ("tile11_pakistan_sindh_baloch", 23.5, 60.8, 30.5, 71.5),
    ("tile12_pakistan_punjab_kpk_gb", 30.0, 69.0, 37.2, 76.5),
  ]
  overpass_urls = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
  ]
  for tname, s, w, n, e in tiles:
    outp = os.path.join(RAW_DIR, f"osm_w3_{tname}.json")
    if os.path.exists(outp) and os.path.getsize(outp) > 2000:
      print(f"  [SKIP] OSM {tname} cached ({os.path.getsize(outp):,} B)", flush=True)
      continue
    q = f"""
    [out:json][timeout:95];
    (
      nwr["historic"="archaeological_site"]({s},{w},{n},{e});
      nwr["historic"="fort"]({s},{w},{n},{e});
      nwr["historic"="castle"]({s},{w},{n},{e});
      nwr["historic"="ruins"]({s},{w},{n},{e});
      nwr["historic"="palace"]({s},{w},{n},{e});
      nwr["historic"="monastery"]({s},{w},{n},{e});
      nwr["historic"="city_gate"]({s},{w},{n},{e});
      nwr["historic"="megalith"]({s},{w},{n},{e});
      nwr["historic"="tumulus"]({s},{w},{n},{e});
      nwr["historic"="stepwell"]({s},{w},{n},{e});
      nwr["amenity"="stepwell"]({s},{w},{n},{e});
    );
    out center tags;
    """
    ok = False
    for ep in overpass_urls:
      try:
        r = requests.post(ep, data={"data": q}, headers=HEADERS, timeout=115)
        if r.status_code == 200:
          els = r.json().get("elements", [])
          with open(outp, "w", encoding="utf-8") as fh:
            json.dump(els, fh, ensure_ascii=False)
          print(f"  [OK] OSM {tname}: {len(els):,} elements via {ep.split('/')[2]}", flush=True)
          ok = True
          break
        print(f"  [WARN] OSM {tname} via {ep.split('/')[2]}: HTTP {r.status_code}", flush=True)
      except Exception as ex:
        print(f"  [WARN] OSM {tname} via {ep.split('/')[2]}: {ex}", flush=True)
      time.sleep(4)
    if not ok:
      print(f"  [FAIL] OSM {tname} failed on all mirrors", flush=True)
    time.sleep(3)


def harvest_zenodo_wave3():
  print("[3] Harvesting Zenodo South Asian Palaeolithic (13627361), Harappan/Indus & South Asia archaeology datasets...", flush=True)
  target_records = [13627361, 8329381]
  for rid in target_records:
    r = safe_get(f"https://zenodo.org/api/records/{rid}", arg2_timeout=30)
    if not r or r.status_code != 200:
      continue
    meta = r.json()
    for f in meta.get("files", []):
      fn = f.get("key", "")
      fsize = f.get("size", 0)
      if fsize > 40_000_000 or fsize < 200:
        continue
      if any(fn.lower().endswith(ext) for ext in (".csv", ".tsv", ".xlsx", ".xls", ".geojson", ".json", ".zip")):
        dl = f.get("links", {}).get("self")
        safe_fn = re.sub(r"[^A-Za-z0-9._-]+", "_", f"zenodo_{rid}_{fn}")
        outp = os.path.join(RAW_DIR, safe_fn)
        if os.path.exists(outp) and os.path.getsize(outp) > 200:
          print(f"  [SKIP] {safe_fn} cached", flush=True)
          continue
        dr = safe_get(dl, arg2_timeout=90)
        if dr and dr.status_code == 200:
          with open(outp, "wb") as fh:
            fh.write(dr.content)
          print(f"  [OK] Saved {safe_fn} ({len(dr.content):,} B)", flush=True)

  # Also search Zenodo for Harappan / Indus / Sri Lanka / Nepal / Bengal / Megalithic CSV/GeoJSON datasets
  for q in [
    '"Harappan" OR "Indus Valley" AND (csv OR geojson) AND sites',
    '"Indian Archaeological Review" OR "megalithic" India sites',
    '"Sri Lanka" OR "Anuradhapura" OR "Nepal" archaeological sites csv OR geojson',
  ]:
    r = safe_get("https://zenodo.org/api/records", arg1_params={"q": q, "size": 10}, arg2_timeout=30)
    if not r or r.status_code != 200:
      continue
    for h in r.json().get("hits", {}).get("hits", []):
      rid = h.get("id")
      for f in h.get("files", []):
        fn = f.get("key", "")
        fsize = f.get("size", 0)
        if fsize > 25_000_000 or fsize < 500:
          continue
        if any(fn.lower().endswith(ext) for ext in (".csv", ".geojson", ".xlsx")):
          safe_fn = re.sub(r"[^A-Za-z0-9._-]+", "_", f"zenodo_{rid}_{fn}")
          outp = os.path.join(RAW_DIR, safe_fn)
          if os.path.exists(outp):
            continue
          dl = f.get("links", {}).get("self")
          if not dl:
            continue
          dr = safe_get(dl, arg2_timeout=90)
          if dr and dr.status_code == 200:
            with open(outp, "wb") as fh:
              fh.write(dr.content)
            print(f"  [OK] Zenodo search {rid}: {safe_fn} ({len(dr.content):,} B)", flush=True)


if __name__ == "__main__":
  harvest_wikidata_pre1800_enriched()
  harvest_osm_complete_tiles()
  harvest_zenodo_wave3()
  print("=== WAVE 3 PRE-1800 HARVEST COMPLETE ===", flush=True)
