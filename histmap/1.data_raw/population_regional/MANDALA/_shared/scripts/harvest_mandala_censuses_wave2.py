"""Wave-2 Census Supplement Harvester for Project MANDALA.

Fetches:
  1. Myanmar MIMU 2014 Census (all 330 townships) from HDX & GitHub (`yathit/myanmar-township`)
  2. Philippines HDX ADM3 (all 1,634 cities & municipalities) + PSGC CSVs
  3. Indonesia BPS 2010/2020 Kabupaten/Kota/Kecamatan & Wikidata all Indonesian human settlements P1082
  4. Vietnam, Cambodia, Laos, Malaysia, Thailand, Timor-Leste HDX ADM2/ADM3 population CSVs
"""

import json
import os
import time
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CENSUS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MANDALA", "_shared", "_census_cache")
HEADERS = {"User-Agent": "SVEA-OperationViscount-MANDALA/1.0"}
WD_ENDPOINT = "https://query.wikidata.org/sparql"


def fetch(url, fn, timeout=120):
  dst = os.path.join(CENSUS_DIR, fn)
  if os.path.exists(dst) and os.path.getsize(dst) > 400:
    return True
  try:
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    if r.status_code == 200 and len(r.content) > 200:
      open(dst, "wb").write(r.content)
      print(f"  [OK] {fn}: {len(r.content):,} B", flush=True)
      return True
    print(f"  [WARN] {fn} HTTP {r.status_code}", flush=True)
  except Exception as e:
    print(f"  [ERR] {fn}: {e}", flush=True)
  return False


def main():
  print("[1] Fetching Myanmar MIMU 2014 townships & HDX ADM3 CSVs across MANDALA...", flush=True)
  # Parse _tree_mm_township.json & _tree_ph_psgc.json
  mm_tree_p = os.path.join(CENSUS_DIR, "_tree_mm_township.json")
  if os.path.exists(mm_tree_p):
    for t in json.load(open(mm_tree_p, "r", encoding="utf-8")).get("tree", []):
      p = t.get("path", "")
      if p.lower().endswith((".csv", ".json")) and any(k in p.lower() for k in ("pop", "census", "town", "mmr")):
        fetch(f"https://raw.githubusercontent.com/yathit/myanmar-township/master/{p}", f"mm_gh_{os.path.basename(p)}")

  ph_tree_p = os.path.join(CENSUS_DIR, "_tree_ph_psgc.json")
  if os.path.exists(ph_tree_p):
    for t in json.load(open(ph_tree_p, "r", encoding="utf-8")).get("tree", []):
      p = t.get("path", "")
      if p.lower().endswith(".csv") and "municit" in p.lower():
        fetch(f"https://raw.githubusercontent.com/altcoder/philippines-psgc-shapefiles/main/{p}", f"ph_psgc_{os.path.basename(p)}")

  # Direct HDX queries for Myanmar 2014 Census, Philippines ADM3, Vietnam ADM2, Cambodia ADM2, Laos ADM2, Indonesia ADM2/ADM3, Timor-Leste ADM3
  hdx_queries = [
    ("mmr_2014", "myanmar 2014 census township population"),
    ("phl_adm3", "philippines subnational population statistics"),
    ("vnm_adm2", "viet nam subnational population statistics"),
    ("khm_adm2", "cambodia subnational population statistics"),
    ("lao_adm2", "lao subnational population statistics"),
    ("idn_adm2", "indonesia subnational population statistics"),
    ("mys_adm2", "malaysia subnational population statistics"),
    ("tls_adm3", "timor-leste subnational population statistics"),
  ]
  for tag, q in hdx_queries:
    try:
      r = requests.get("https://data.humdata.org/api/3/action/package_search", params={"q": q, "rows": 4}, headers=HEADERS, timeout=40)
      if r.status_code != 200:
        continue
      got = 0
      for pkg in r.json().get("result", {}).get("results", []):
        for res in pkg.get("resources", []):
          rurl = res.get("url") or res.get("download_url")
          rname = (res.get("name") or "").lower()
          if not rurl or not any(rname.endswith(e) for e in (".csv", ".xlsx")):
            continue
          if any(k in rname for k in ("adm2", "adm3", "township", "muni", "district", "census", "pop")):
            safe = f"hdx2_{tag}_{os.path.basename(rname.split('?')[0])}"
            if got < 4 and fetch(rurl, safe, timeout=90):
              got += 1
    except Exception as e:
      print(f"  [WARN] HDX2 {tag}: {e}", flush=True)
    time.sleep(0.4)

  # Wikidata Indonesia settlements (kecamatan Q15284/Q24764/Q172241/Q3191695/Q3191697 + kelurahan/desa with pop >= 2000)
  print("[2] Harvesting Wikidata Indonesia + Vietnam + Myanmar multi-year P1082 settlement series...", flush=True)
  wd_extra = [
    ("wd_pop_indonesia_all_setts.json", """
    SELECT ?item ?itemLabel ?coord ?pop ?date ?inception ?geonames WHERE {
      ?item wdt:P17 wd:Q252 ;
            wdt:P625 ?coord ;
            p:P1082 ?stmt .
      ?stmt ps:P1082 ?pop .
      FILTER(?pop >= 1500)
      OPTIONAL { ?stmt pq:P585 ?date . }
      OPTIONAL { ?item wdt:P571 ?inception . }
      OPTIONAL { ?item wdt:P1566 ?geonames . }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,id". }
    }
    LIMIT 60000
    """),
    ("wd_pop_vietnam_all.json", """
    SELECT ?item ?itemLabel ?coord ?pop ?date ?inception ?geonames WHERE {
      ?item wdt:P17 wd:Q881 ;
            wdt:P625 ?coord ;
            p:P1082 ?stmt .
      ?stmt ps:P1082 ?pop .
      OPTIONAL { ?stmt pq:P585 ?date . }
      OPTIONAL { ?item wdt:P571 ?inception . }
      OPTIONAL { ?item wdt:P1566 ?geonames . }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,vi". }
    }
    LIMIT 60000
    """),
  ]
  for fn, q in wd_extra:
    outp = os.path.join(CENSUS_DIR, fn)
    if os.path.exists(outp) and os.path.getsize(outp) > 2000:
      continue
    try:
      r = requests.get(WD_ENDPOINT, params={"query": q, "format": "json"}, headers={**HEADERS, "Accept": "application/sparql-results+json"}, timeout=120)
      if r.status_code == 200:
        rows = r.json().get("results", {}).get("bindings", [])
        open(outp, "w", encoding="utf-8").write(json.dumps(rows, ensure_ascii=False))
        print(f"  [OK] {fn}: {len(rows):,} rows", flush=True)
      else:
        print(f"  [WARN] {fn} HTTP {r.status_code}", flush=True)
    except Exception as e:
      print(f"  [ERR] {fn}: {e}", flush=True)
    time.sleep(2.5)
  print("=== DONE WAVE-2 CENSUS SUPPLEMENT ===", flush=True)


if __name__ == "__main__":
  main()
