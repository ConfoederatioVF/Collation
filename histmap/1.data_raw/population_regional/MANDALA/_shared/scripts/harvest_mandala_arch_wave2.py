"""Wave-2 Split Wikidata Institutional Heritage Harvester for Project MANDALA.

Splits Indonesia (Cagar Budaya + candi + archaeological sites + forts/palaces/caves) and adds
deep Khmer/Cambodia/Vietnam/Myanmar/Thailand/Philippines heritage queries so zero 504 timeouts occur.
"""

import json
import os
import time
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional",
  "MANDALA", "_shared", "sites_mandala_southeast_asia", "0.raw_data"
)
HEADERS = {"User-Agent": "SVEA-OperationViscount-MANDALA/1.0 (academic research; contact: austkaeztchen@confoederatio.org)"}
ENDPOINT = "https://query.wikidata.org/sparql"


def run_q(q, fn, label):
  outp = os.path.join(RAW_DIR, fn)
  if os.path.exists(outp) and os.path.getsize(outp) > 800:
    print(f"  [SKIP] {label} cached ({os.path.getsize(outp):,} B)", flush=True)
    return
  for att in range(3):
    try:
      r = requests.get(ENDPOINT, params={"query": q, "format": "json"}, headers={**HEADERS, "Accept": "application/sparql-results+json"}, timeout=100)
      if r.status_code == 200:
        rows = r.json().get("results", {}).get("bindings", [])
        open(outp, "w", encoding="utf-8").write(json.dumps(rows, ensure_ascii=False))
        print(f"  [OK] {label}: {len(rows):,} rows", flush=True)
        return
      print(f"  [WARN] {label} HTTP {r.status_code} (att {att+1})", flush=True)
      time.sleep(5 * (att + 1))
    except Exception as e:
      print(f"  [ERR] {label}: {e}", flush=True)
      time.sleep(5)


def main():
  print("=== WAVE-2 INDONESIA & DEEP SE ASIA INSTITUTIONAL ARCHAEOLOGY ===", flush=True)
  queries = [
    ("wikidata_arch_indonesia_candi_arch.json", "Indonesia Candi, Arch Sites, Ruins, Ancient Cities", """
    SELECT DISTINCT ?item ?itemLabel ?coord ?inception ?periodLabel ?typeLabel WHERE {
      ?item wdt:P17 wd:Q252 ; wdt:P625 ?coord .
      VALUES ?type { wd:Q1032404 wd:Q839954 wd:Q15661340 wd:Q109607 wd:Q180987 wd:Q164240 wd:Q1542758 wd:Q35509 wd:Q842402 }
      ?item wdt:P31 ?type .
      OPTIONAL { ?item wdt:P571 ?inception . }
      OPTIONAL { ?item wdt:P2348 ?period . }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,id". }
    } LIMIT 15000
    """),
    ("wikidata_arch_indonesia_cagar_budaya.json", "Indonesia Cagar Budaya National Heritage (P1435)", """
    SELECT DISTINCT ?item ?itemLabel ?coord ?inception ?typeLabel ?heritageLabel WHERE {
      ?item wdt:P17 wd:Q252 ; wdt:P625 ?coord ; wdt:P1435 ?heritage .
      OPTIONAL { ?item wdt:P571 ?inception . }
      OPTIONAL { ?item wdt:P31 ?type . }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,id". }
    } LIMIT 15000
    """),
    ("wikidata_arch_indonesia_forts_palaces.json", "Indonesia Forts, Kratons, Palaces & Historic Mosques", """
    SELECT DISTINCT ?item ?itemLabel ?coord ?inception ?typeLabel WHERE {
      ?item wdt:P17 wd:Q252 ; wdt:P625 ?coord .
      VALUES ?type { wd:Q57821 wd:Q23413 wd:Q16560 wd:Q1081138 wd:Q44539 }
      ?item wdt:P31 ?type .
      OPTIONAL { ?item wdt:P571 ?inception . }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,id". }
    } LIMIT 15000
    """),
    ("wikidata_arch_cambodia_temples.json", "Cambodia Prasat & Khmer Temples", """
    SELECT DISTINCT ?item ?itemLabel ?coord ?inception ?typeLabel WHERE {
      ?item wdt:P17 wd:Q424 ; wdt:P625 ?coord .
      ?item wdt:P31/wdt:P279* wd:Q44539 .
      OPTIONAL { ?item wdt:P571 ?inception . }
      OPTIONAL { ?item wdt:P31 ?type . }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,fr". }
    } LIMIT 10000
    """),
    ("wikidata_arch_myanmar_pagodas.json", "Myanmar Pagodas, Stupas, Monasteries & Ancient Cities", """
    SELECT DISTINCT ?item ?itemLabel ?coord ?inception ?typeLabel WHERE {
      ?item wdt:P17 wd:Q836 ; wdt:P625 ?coord .
      VALUES ?type { wd:Q200265 wd:Q180987 wd:Q5393308 wd:Q44613 wd:Q44539 wd:Q839954 wd:Q15661340 wd:Q109607 }
      ?item wdt:P31 ?type .
      OPTIONAL { ?item wdt:P571 ?inception . }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    } LIMIT 10000
    """),
    ("wikidata_arch_vietnam_temples_citadels.json", "Vietnam Pagodas, Communal Houses, Cham Towers & Citadels", """
    SELECT DISTINCT ?item ?itemLabel ?coord ?inception ?typeLabel WHERE {
      ?item wdt:P17 wd:Q881 ; wdt:P625 ?coord .
      VALUES ?type { wd:Q200265 wd:Q5393308 wd:Q44539 wd:Q57821 wd:Q23413 wd:Q16560 wd:Q839954 wd:Q109607 }
      ?item wdt:P31 ?type .
      OPTIONAL { ?item wdt:P571 ?inception . }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,vi". }
    } LIMIT 10000
    """),
  ]
  for fn, lbl, q in queries:
    run_q(q, fn, lbl)
    time.sleep(2.0)
  print("=== DONE WAVE-2 SPLIT ARCHAEOLOGY ===", flush=True)


if __name__ == "__main__":
  main()
