"""Programmatic Full-Row Census & Gazetteer Harvester for Operation Viscount Project SARAY.

Downloads 100% full-row official census tables, historical town series, and national
gazetteers (zero Top-N caps) for all 5 sovereign republics of SARAY (Kazakhstan, Uzbekistan,
Turkmenistan, Kyrgyzstan, Tajikistan):
  1. Full GeoNames country dumps (KZ, UZ, TM, KG, TJ) + admin1/admin2 code tables.
  2. Tim Bespyatov (pop-stat.mashke.org) official census archives (1926, 1939, 1959, 1970,
     1979, 1989 All-Union Soviet Censuses + 1995/1999/2000/2009/2010/2012/2020/2021/2022
     post-Soviet national censuses across all cities, towns, urban-type settlements, and oblasts).
  3. Demoscope Weekly 1897 First All-Russian Empire Census + 1926/1939/1959/1970/1979/1989
     oblast/republic tables for Russian Turkestan, Steppe Governorates, and Soviet SSRs.
  4. Wikidata multi-year town census series (P1082 + P585 point-in-time + P571 inception +
     P1566 GeoNames ID + multilingual EN/RU/KK/UZ/KY/TK/TG labels) for all 5 republics.
"""

import json
import os
import re
import time

import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SARAY_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "SARAY")
CENSUS_DIR = os.path.join(SARAY_DIR, "_shared", "_census_cache")
os.makedirs(CENSUS_DIR, exist_ok=True)

HEADERS = {
  "User-Agent": "SVEA-OperationViscount-SARAY/1.0 (academic demography; contact: austkaeztchen@confoederatio.org)"
}


def fetch_file(url, dest, timeout=120):
  if os.path.exists(dest) and os.path.getsize(dest) > 500:
    print(f"  [SKIP] Cached {os.path.basename(dest)} ({os.path.getsize(dest):,} B)", flush=True)
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


def harvest_geonames():
  print("[1] Downloading full GeoNames country dumps (KZ, UZ, TM, KG, TJ)...", flush=True)
  for cc in ["KZ", "UZ", "TM", "KG", "TJ"]:
    fetch_file(f"https://download.geonames.org/export/dump/{cc}.zip", os.path.join(CENSUS_DIR, f"geonames_{cc}.zip"), timeout=180)
  fetch_file("https://download.geonames.org/export/dump/admin1CodesASCII.txt", os.path.join(CENSUS_DIR, "geonames_admin1CodesASCII.txt"))
  fetch_file("https://download.geonames.org/export/dump/admin2Codes.txt", os.path.join(CENSUS_DIR, "geonames_admin2Codes.txt"))


def harvest_popstat_central_asia():
  print("[2] Downloading pop-stat.mashke.org full census tables for all 5 Central Asian republics...", flush=True)
  # Discover all Central Asian HTML pages from pop-stat index
  idx_path = os.path.join(CENSUS_DIR, "popstat_index.htm")
  fetch_file("http://pop-stat.mashke.org/index.htm", idx_path, timeout=45)
  pages = set([
    "kazakhstan-cities.htm", "kazakhstan-division2021.htm", "kazakhstan-division2009.htm", "kazakhstan-division1999.htm",
    "kyrgyzstan-cities.htm", "kyrgyzstan-division2022.htm", "kyrgyzstan-division2009.htm",
    "tajikistan-cities.htm", "tajikistan-division2020.htm", "tajikistan-division2010.htm",
    "turkmenistan-cities.htm", "turkmenistan-division2022.htm", "turkmenistan-division1995.htm",
    "uzbekistan-cities.htm", "uzbekistan-cities-new.htm", "uzbekistan-division.htm",
  ])
  if os.path.exists(idx_path):
    txt = open(idx_path, "r", encoding="utf-8", errors="replace").read()
    for m in re.findall(r'href=["\']([^"\']*(?:kazakh|uzbek|turkmen|kyrgyz|tajik|ussr|soviet)[^"\']*\.htm)["\']', txt, flags=re.I):
      clean_m = m.lstrip("./")
      if "ethnic" not in clean_m.lower() and "lang" not in clean_m.lower() and "relig" not in clean_m.lower():
        pages.add(clean_m)
  # Also crawl each republic's hub page if present
  for rep in ["kazakhstan", "uzbekistan", "turkmenistan", "kyrgyzstan", "tajikistan"]:
    hub = os.path.join(CENSUS_DIR, f"popstat_{rep}_hub.htm")
    if fetch_file(f"http://pop-stat.mashke.org/{rep}.htm", hub, timeout=30):
      txt = open(hub, "r", encoding="utf-8", errors="replace").read()
      for m in re.findall(r'href=["\']([^"\']+\.htm)["\']', txt, flags=re.I):
        clean_m = m.lstrip("./")
        if rep in clean_m.lower() and not any(k in clean_m.lower() for k in ("ethnic", "lang", "relig", "age")):
          pages.add(clean_m)

  print(f"  Discovered {len(pages)} pop-stat pages to fetch...", flush=True)
  for pg in sorted(pages):
    safe = "popstat_" + re.sub(r"[^A-Za-z0-9._-]+", "_", pg)
    fetch_file(f"http://pop-stat.mashke.org/{pg}", os.path.join(CENSUS_DIR, safe), timeout=45)
    time.sleep(0.25)


def harvest_demoscope_imperial_and_soviet():
  print("[3] Downloading Demoscope Weekly 1897 Imperial & Soviet census tables...", flush=True)
  targets = [
    ("demoscope_1897_emp_lan.html", "https://www.demoscope.ru/weekly/ssp/emp_lan_97_uezd.php"),
    ("demoscope_1897_cities.html", "https://www.demoscope.ru/weekly/ssp/rus_gub_97.php"),
    ("demoscope_1926_ussr.html", "https://www.demoscope.ru/weekly/ssp/sng_nac_26.php"),
    ("demoscope_1939_ussr.html", "https://www.demoscope.ru/weekly/ssp/sng_nac_39.php"),
    ("demoscope_1959_ussr.html", "https://www.demoscope.ru/weekly/ssp/sng_nac_59.php"),
    ("demoscope_1970_ussr.html", "https://www.demoscope.ru/weekly/ssp/sng_nac_70.php"),
    ("demoscope_1979_ussr.html", "https://www.demoscope.ru/weekly/ssp/sng_nac_79.php"),
    ("demoscope_1989_ussr.html", "https://www.demoscope.ru/weekly/ssp/sng_nac_89.php"),
  ]
  for fn, u in targets:
    fetch_file(u, os.path.join(CENSUS_DIR, fn), timeout=45)
    time.sleep(0.5)


def harvest_wikidata_town_censuses():
  print("[4] Harvesting Wikidata multi-year town census series (P1082 + P585 + P571 + P1566) for all 5 SARAY republics...", flush=True)
  endpoint = "https://query.wikidata.org/sparql"
  for slug, qid, label in [
    ("kazakhstan", "Q232", "Kazakhstan Settlements P1082"),
    ("uzbekistan", "Q265", "Uzbekistan Settlements P1082"),
    ("turkmenistan", "Q874", "Turkmenistan Settlements P1082"),
    ("kyrgyzstan", "Q813", "Kyrgyzstan Settlements P1082"),
    ("tajikistan", "Q863", "Tajikistan Settlements P1082"),
  ]:
    outp = os.path.join(CENSUS_DIR, f"wd_pop_{slug}.json")
    if os.path.exists(outp) and os.path.getsize(outp) > 2000:
      print(f"  [SKIP] {label} cached ({os.path.getsize(outp):,} B)", flush=True)
      continue
    q = f"""
    SELECT ?item ?itemLabel ?ruLabel ?coord ?pop ?date ?inception ?geonames WHERE {{
      ?item wdt:P17 wd:{qid} ;
            wdt:P625 ?coord ;
            p:P1082 ?stmt .
      ?stmt ps:P1082 ?pop .
      OPTIONAL {{ ?stmt pq:P585 ?date . }}
      OPTIONAL {{ ?item wdt:P571 ?inception . }}
      OPTIONAL {{ ?item wdt:P1566 ?geonames . }}
      ?item wdt:P31/wdt:P279* wd:Q486972 .
      OPTIONAL {{ ?item rdfs:label ?ruLabel . FILTER(LANG(?ruLabel) = "ru") }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,ru,kk,uz,ky,tk,tg". }}
    }}
    LIMIT 45000
    """
    for att in range(3):
      try:
        r = requests.get(
          endpoint,
          params={"query": q, "format": "json"},
          headers={**HEADERS, "Accept": "application/sparql-results+json"},
          timeout=115,
        )
        if r.status_code == 200:
          rows = r.json().get("results", {}).get("bindings", [])
          with open(outp, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False)
          print(f"  [OK] {label}: {len(rows):,} rows", flush=True)
          break
        print(f"  [WARN] {label}: HTTP {r.status_code} (att {att+1})", flush=True)
        time.sleep(6 * (att + 1))
      except Exception as e:
        print(f"  [ERR] {label}: {e}", flush=True)
        time.sleep(6)
    time.sleep(2.5)


if __name__ == "__main__":
  harvest_geonames()
  harvest_popstat_central_asia()
  harvest_demoscope_imperial_and_soviet()
  harvest_wikidata_town_censuses()
  print("=== DONE SARAY CENSUS & GAZETTEER HARVEST ===", flush=True)
