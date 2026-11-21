"""Programmatic Full-Row Census & Gazetteer Harvester for Operation Viscount Project MANDALA.

Downloads 100% full-row official census tables, HDX COD-PS subnational enumerations,
GitHub official municipal/district census repositories, GeoNames full country dumps
(zero Top-N caps), and Wikidata multi-decade P1082 settlement census series across all 11
MANDALA sovereign states (Myanmar, Thailand, Laos, Cambodia, Vietnam, Malaysia, Singapore,
Brunei, Indonesia less West New Guinea, Philippines and Timor-Leste).
"""

import json
import os
import time
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MANDALA_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MANDALA")
CENSUS_DIR = os.path.join(MANDALA_DIR, "_shared", "_census_cache")
os.makedirs(CENSUS_DIR, exist_ok=True)

HEADERS = {"User-Agent": "SVEA-OperationViscount-MANDALA/1.0 (academic historical demography; contact: austkaeztchen@confoederatio.org)"}
WD_ENDPOINT = "https://query.wikidata.org/sparql"


def fetch_file(url, dest, timeout=180):
  if os.path.exists(dest) and os.path.getsize(dest) > 500:
    print(f"  [SKIP] Cached: {os.path.basename(dest)} ({os.path.getsize(dest):,} B)", flush=True)
    return True
  for att in range(3):
    try:
      r = requests.get(url, headers=HEADERS, timeout=timeout)
      if r.status_code == 200 and len(r.content) > 200:
        with open(dest, "wb") as fh:
          fh.write(r.content)
        print(f"  [OK] {os.path.basename(dest)}: {len(r.content):,} B", flush=True)
        return True
      if r.status_code in (429, 502, 503, 504):
        time.sleep(4 * (att + 1))
        continue
      print(f"  [WARN] {url} -> HTTP {r.status_code}", flush=True)
      return False
    except Exception as e:
      print(f"  [ERR] {url}: {e}", flush=True)
      time.sleep(3)
  return False


def harvest_geonames_all_11():
  print("[1] Harvesting 100% full GeoNames country dumps for all 11 MANDALA states...", flush=True)
  for cc in ["MM", "TH", "LA", "KH", "VN", "MY", "SG", "BN", "ID", "PH", "TL"]:
    fetch_file(f"https://download.geonames.org/export/dump/{cc}.zip", os.path.join(CENSUS_DIR, f"geonames_{cc}.zip"))
  # Reuse or download admin1/admin2 codes
  indus_c = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "INDUS", "_shared", "_census_cache")
  for fn in ("geonames_admin1CodesASCII.txt", "geonames_admin2Codes.txt"):
    dst = os.path.join(CENSUS_DIR, fn)
    src = os.path.join(indus_c, fn)
    if not os.path.exists(dst) and os.path.exists(src):
      with open(src, "rb") as s, open(dst, "wb") as d:
        d.write(s.read())
      print(f"  [COPY] {fn} ({os.path.getsize(dst):,} B)", flush=True)
    else:
      gn_fn = fn.replace("geonames_", "")
      fetch_file(f"https://download.geonames.org/export/dump/{gn_fn}", dst)


def harvest_hdx_cod_ps():
  print("[2] Harvesting official HDX COD-PS subnational census tables (all 11 countries)...", flush=True)
  iso3_list = [
    ("mmr", "Myanmar"), ("tha", "Thailand"), ("lao", "Laos"), ("khm", "Cambodia"),
    ("vnm", "Vietnam"), ("mys", "Malaysia"), ("sgp", "Singapore"), ("brn", "Brunei"),
    ("idn", "Indonesia"), ("phl", "Philippines"), ("tls", "Timor-Leste")
  ]
  for iso3, label in iso3_list:
    marker = os.path.join(CENSUS_DIR, f"_hdx_done_{iso3}.json")
    if os.path.exists(marker):
      print(f"  [SKIP] HDX {iso3} already queried", flush=True)
      continue
    try:
      r = requests.get(
        "https://data.humdata.org/api/3/action/package_search",
        params={"q": f"cod-ps-{iso3}", "rows": 5},
        headers=HEADERS, timeout=45
      )
      saved = []
      if r.status_code == 200:
        pkgs = r.json().get("result", {}).get("results", [])
        for pkg in pkgs:
          if f"cod-ps-{iso3}" not in pkg.get("name", "").lower() and "population" not in pkg.get("title", "").lower():
            continue
          for res in pkg.get("resources", []):
            fmt = (res.get("format") or "").lower()
            rname = (res.get("name") or "").lower()
            rurl = res.get("url") or res.get("download_url")
            if not rurl:
              continue
            if fmt in ("csv", "xlsx") or rname.endswith((".csv", ".xlsx")):
              # Prefer ADM2, ADM3, ADM4, ADM1 population CSVs
              if any(k in rname for k in ("adm2", "adm3", "adm1", "adm4", "pop", "census", iso3)):
                safe = f"hdx_{iso3}_{os.path.basename(rname.split('?')[0])}"
                if not safe.lower().endswith((".csv", ".xlsx")):
                  safe += f".{fmt or 'csv'}"
                dst = os.path.join(CENSUS_DIR, safe)
                if len(saved) < 6 and fetch_file(rurl, dst, timeout=90):
                  saved.append(safe)
      with open(marker, "w", encoding="utf-8") as fh:
        json.dump({"iso3": iso3, "saved": saved}, fh, indent=2)
      print(f"  HDX {label} ({iso3}): downloaded {len(saved)} census files", flush=True)
    except Exception as e:
      print(f"  [WARN] HDX {iso3}: {e}", flush=True)
    time.sleep(0.5)


def harvest_github_official_censuses():
  print("[3] Harvesting official GitHub full municipal/district census tables...", flush=True)
  targets = [
    # Vietnam 2019 GSO Census ALL 705 districts
    ("https://raw.githubusercontent.com/phuongdh/vietnam-population-by-district/main/data/vietnam_population_2019.csv", "vn_gso_2019_districts.csv"),
    ("https://raw.githubusercontent.com/phuongdh/vietnam-population-by-district/master/data/vietnam_population_2019.csv", "vn_gso_2019_districts.csv"),
    ("https://api.github.com/repos/phuongdh/vietnam-population-by-district/git/trees/main?recursive=1", "_tree_vn_pop.json"),
    # Philippines PSGC all 1,634 cities & municipalities
    ("https://raw.githubusercontent.com/altcoder/philippines-psgc-shapefiles/main/data/2023/PH_Adm3_MuniCities.csv", "ph_psgc_municities.csv"),
    ("https://api.github.com/repos/altcoder/philippines-psgc-shapefiles/git/trees/main?recursive=1", "_tree_ph_psgc.json"),
    # Indonesia all 514 kabupaten/kota
    ("https://api.github.com/repos/open-admin-data/indonesia-administrative-divisions/git/trees/main?recursive=1", "_tree_id_admin.json"),
    # Myanmar MIMU townships
    ("https://api.github.com/repos/yathit/myanmar-township/git/trees/master?recursive=1", "_tree_mm_township.json"),
  ]
  for url, fn in targets:
    fetch_file(url, os.path.join(CENSUS_DIR, fn), timeout=60)
    time.sleep(0.3)


def query_wd(q, out_fn, label):
  outp = os.path.join(CENSUS_DIR, out_fn)
  if os.path.exists(outp) and os.path.getsize(outp) > 2000:
    print(f"  [SKIP] {label} cached ({os.path.getsize(outp):,} B)", flush=True)
    return
  for att in range(3):
    try:
      r = requests.get(
        WD_ENDPOINT,
        params={"query": q, "format": "json"},
        headers={**HEADERS, "Accept": "application/sparql-results+json"},
        timeout=120
      )
      if r.status_code == 200:
        rows = r.json().get("results", {}).get("bindings", [])
        with open(outp, "w", encoding="utf-8") as fh:
          json.dump(rows, fh, ensure_ascii=False)
        print(f"  [OK] {label}: {len(rows):,} rows", flush=True)
        return
      print(f"  [WARN] {label}: HTTP {r.status_code} (att {att+1})", flush=True)
      time.sleep(5 * (att + 1))
    except Exception as e:
      print(f"  [ERR] {label}: {e}", flush=True)
      time.sleep(5)


def harvest_wikidata_multiyear_censuses():
  print("[4] Harvesting Wikidata multi-decade P1082 settlement census series (all 11 MANDALA states)...", flush=True)
  # Smaller & medium countries: full P1082 across all human settlements / administrative entities
  small_med = [
    ("myanmar", "Q836", "Myanmar Settlements & Townships P1082"),
    ("laos", "Q819", "Laos Settlements & Districts P1082"),
    ("cambodia", "Q424", "Cambodia Settlements & Districts P1082"),
    ("vietnam", "Q881", "Vietnam Cities, Towns & Districts P1082"),
    ("malaysia", "Q833", "Malaysia Cities, Towns & Districts P1082"),
    ("singapore", "Q334", "Singapore Planning Areas & Towns P1082"),
    ("brunei", "Q921", "Brunei Towns & Mukims P1082"),
    ("timor_leste", "Q574", "Timor-Leste Municipalities & Sucos P1082"),
    ("thailand", "Q869", "Thailand Cities, Thesaban & Amphoe P1082"),
  ]
  for slug, qid, label in small_med:
    q = f"""
    SELECT ?item ?itemLabel ?coord ?pop ?date ?inception ?geonames WHERE {{
      ?item wdt:P17 wd:{qid} ;
            wdt:P625 ?coord ;
            p:P1082 ?stmt .
      ?stmt ps:P1082 ?pop .
      OPTIONAL {{ ?stmt pq:P585 ?date . }}
      OPTIONAL {{ ?item wdt:P571 ?inception . }}
      OPTIONAL {{ ?item wdt:P1566 ?geonames . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 60000
    """
    query_wd(q, f"wd_pop_{slug}.json", label)
    time.sleep(2.5)

  # Philippines: ALL 1,634 cities & municipalities (P31 = Q24764 municipality of the PH, Q106079704 / Q29946056 / Q515 city of the PH) -> huge multi-decade 1903-2020 series!
  for slug, cls_vals, label in [
    ("philippines_cities", "VALUES ?cls { wd:Q515 wd:Q106079704 wd:Q29946056 wd:Q1637706 wd:Q1549591 wd:Q17376095 }", "Philippines Cities P1082 (1903-2020)"),
    ("philippines_munis", "VALUES ?cls { wd:Q24764 }", "Philippines ALL Municipalities P1082 (1903-2020)"),
  ]:
    q = f"""
    SELECT ?item ?itemLabel ?coord ?pop ?date ?inception ?geonames WHERE {{
      ?item wdt:P17 wd:Q928 ;
            wdt:P625 ?coord ;
            p:P1082 ?stmt .
      {cls_vals}
      ?item wdt:P31 ?cls .
      ?stmt ps:P1082 ?pop .
      OPTIONAL {{ ?stmt pq:P585 ?date . }}
      OPTIONAL {{ ?item wdt:P571 ?inception . }}
      OPTIONAL {{ ?item wdt:P1566 ?geonames . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 60000
    """
    query_wd(q, f"wd_pop_{slug}.json", label)
    time.sleep(2.5)

  # Indonesia: split into kota/kabupaten/cities + kecamatan/towns to avoid timeout
  for slug, cls_vals, label in [
    ("indonesia_kota_kab", "VALUES ?cls { wd:Q3191695 wd:Q3191697 wd:Q515 wd:Q1549591 wd:Q3957 wd:Q5119 }", "Indonesia Kota & Kabupaten P1082"),
    ("indonesia_kecamatan", "VALUES ?cls { wd:Q172241 wd:Q15284 wd:Q11812394 }", "Indonesia Kecamatan & Towns P1082"),
  ]:
    q = f"""
    SELECT ?item ?itemLabel ?coord ?pop ?date ?inception ?geonames WHERE {{
      ?item wdt:P17 wd:Q252 ;
            wdt:P625 ?coord ;
            p:P1082 ?stmt .
      {cls_vals}
      ?item wdt:P31 ?cls .
      ?stmt ps:P1082 ?pop .
      OPTIONAL {{ ?stmt pq:P585 ?date . }}
      OPTIONAL {{ ?item wdt:P571 ?inception . }}
      OPTIONAL {{ ?item wdt:P1566 ?geonames . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 60000
    """
    query_wd(q, f"wd_pop_{slug}.json", label)
    time.sleep(2.5)


if __name__ == "__main__":
  harvest_geonames_all_11()
  harvest_hdx_cod_ps()
  harvest_github_official_censuses()
  harvest_wikidata_multiyear_censuses()
  print("=== DONE MANDALA FULL CENSUS & GAZETTEER HARVEST ===", flush=True)
