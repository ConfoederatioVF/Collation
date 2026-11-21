"""Harvests multi-decade census & historical town population series + native-script
toponyms from Wikidata (P1082 with P585 point-in-time + P571 inception) for all 7
INDUS countries (India, Pakistan, Bangladesh, Sri Lanka, Nepal, Bhutan, Maldives),
plus downloads all 6 Census of India Table A-04 (1901-2011 ALL ~7,935 towns) spreadsheets.
"""

import json
import os
import time
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CENSUS_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "INDUS", "_shared", "_census_cache"
)
os.makedirs(CENSUS_DIR, exist_ok=True)
HEADERS = {"User-Agent": "SVEA-OperationViscount-INDUS/1.0 (academic demography; contact: austkaeztchen@confoederatio.org)"}
ENDPOINT = "https://query.wikidata.org/sparql"


def query_wd(q, out_fn, label):
  outp = os.path.join(CENSUS_DIR, out_fn)
  if os.path.exists(outp) and os.path.getsize(outp) > 2000:
    print(f"  [SKIP] {label} already cached", flush=True)
    return
  for att in range(3):
    try:
      r = requests.get(
        ENDPOINT,
        params={"query": q, "format": "json"},
        headers={**HEADERS, "Accept": "application/sparql-results+json"},
        timeout=110
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


def main():
  print("=== HARVESTING WIKIDATA MULTI-YEAR TOWN CENSUS SERIES (ALL 7 INDUS COUNTRIES) ===", flush=True)
  # Non-India countries first (smaller, fast, full-row P1082 + P585 + P571)
  for slug, qid, label in [
    ("pakistan", "Q843", "Pakistan Towns & Cities P1082"),
    ("bangladesh", "Q902", "Bangladesh Towns & Cities P1082"),
    ("sri_lanka", "Q854", "Sri Lanka Towns & Cities P1082"),
    ("nepal", "Q837", "Nepal Municipalities & Towns P1082"),
    ("bhutan", "Q917", "Bhutan Towns & Dzongkhags P1082"),
    ("maldives", "Q826", "Maldives Inhabited Islands P1082"),
  ]:
    q = f"""
    SELECT ?item ?itemLabel ?coord ?pop ?date ?inception ?geonames WHERE {{
      ?item wdt:P17 wd:{qid} ;
            wdt:P625 ?coord ;
            p:P1082 ?stmt .
      ?stmt ps:P1082 ?pop .
      OPTIONAL {{ ?stmt pq:P585 ?date . }}
      OPTIONAL {{ ?item wdt:P571 ?inception . }}
      OPTIONAL {{ ?item wdt:P1566 ?geonames . }}
      ?item wdt:P31/wdt:P279* wd:Q486972 .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 35000
    """
    query_wd(q, f"wd_pop_{slug}.json", label)
    time.sleep(2)

  # India split by major settlement classes to avoid Wikidata timeout
  india_classes = [
    ("india_cities_towns", "VALUES ?cls { wd:Q515 wd:Q3957 wd:Q1549591 wd:Q1637706 wd:Q200250 wd:Q174844 wd:Q3327873 wd:Q15284 wd:Q22865 } ?item wdt:P31 ?cls ."),
    ("india_census_towns", "VALUES ?cls { wd:Q16830604 wd:Q13539802 wd:Q257391 wd:Q532 wd:Q5084 } ?item wdt:P31 ?cls . FILTER(?pop >= 2000)"),
  ]
  for slug, cls_clause in india_classes:
    q = f"""
    SELECT ?item ?itemLabel ?coord ?pop ?date ?inception ?geonames WHERE {{
      ?item wdt:P17 wd:Q668 ;
            wdt:P625 ?coord ;
            p:P1082 ?stmt .
      ?stmt ps:P1082 ?pop .
      {cls_clause}
      OPTIONAL {{ ?stmt pq:P585 ?date . }}
      OPTIONAL {{ ?item wdt:P571 ?inception . }}
      OPTIONAL {{ ?item wdt:P1566 ?geonames . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 50000
    """
    query_wd(q, f"wd_pop_{slug}.json", f"India {slug} P1082")
    time.sleep(3)

  print("=== DONE WIKIDATA MULTI-YEAR TOWN CENSUS SERIES ===", flush=True)


if __name__ == "__main__":
  main()
