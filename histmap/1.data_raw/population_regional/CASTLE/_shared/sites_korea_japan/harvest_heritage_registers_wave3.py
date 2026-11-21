"""Harvests North Korean & South Korean & Japanese archaeological sites, fortresses, tombs, dolmens, and National Treasures from Wikidata SPARQL (institutional heritage registers) + inspects AADR v66 in CASTLE."""

import csv
import json
import os
import time
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_ARCH = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE", "_shared", "sites_korea_japan", "0.raw_data")
JADE_RAW = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "sites_east_asia", "0.raw_data")
HDR = {"User-Agent": "OperationViscountCASTLE/2.0 (https://confoederatio.org; research@confoederatio.org)", "Accept": "application/sparql-results+json"}


def run_sparql(arg0_name, arg1_query, arg2_out):
  if os.path.exists(arg2_out) and os.path.getsize(arg2_out) > 2000:
    d = json.load(open(arg2_out, encoding="utf-8"))
    print(f"[SKIP] {arg0_name}: {len(d)} rows")
    return d
  url = "https://query.wikidata.org/sparql"
  try:
    r = requests.get(url, params={"query": arg1_query, "format": "json"}, headers=HDR, timeout=90)
    if r.status_code != 200:
      print(f"[FAIL] {arg0_name}: HTTP {r.status_code} {r.text[:150]}")
      return []
    rows = r.json().get("results", {}).get("bindings", [])
    out = []
    for b in rows:
      rec = {k: v.get("value") for k, v in b.items()}
      out.append(rec)
    with open(arg2_out, "w", encoding="utf-8") as fh:
      json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"[OK] {arg0_name}: {len(out)} rows -> {os.path.basename(arg2_out)}")
    return out
  except Exception as e:
    print(f"[ERR] {arg0_name}: {e}")
    return []


def main():
  # 1. North Korea: ALL archaeological sites, National Treasures of DPRK (Q708949 / Q1196973), tombs, fortresses, dolmens, Buddhist temples, historical sites with coordinates
  q_nk = """
SELECT DISTINCT ?item ?itemLabel ?koLabel ?typeLabel ?coord ?heritageLabel WHERE {
  ?item wdt:P17 wd:Q423 ;
        wdt:P625 ?coord .
  { ?item wdt:P31/wdt:P279* wd:Q839954 . } UNION
  { ?item wdt:P31/wdt:P279* wd:Q23413 . } UNION
  { ?item wdt:P31/wdt:P279* wd:Q57821 . } UNION
  { ?item wdt:P31/wdt:P279* wd:Q381885 . } UNION
  { ?item wdt:P31/wdt:P279* wd:Q101659 . } UNION
  { ?item wdt:P31/wdt:P279* wd:Q5393308 . } UNION
  { ?item wdt:P31/wdt:P279* wd:Q44539 . } UNION
  { ?item wdt:P1435 ?heritage . }
  OPTIONAL { ?item wdt:P31 ?type . }
  OPTIONAL { ?item wdt:P1435 ?heritage . }
  OPTIONAL { ?item rdfs:label ?koLabel . FILTER(LANG(?koLabel) = "ko") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ko". }
}
LIMIT 5000
"""
  run_sparql("WD_NK_HERITAGE", q_nk, os.path.join(RAW_ARCH, "wd_north_korea_heritage.json"))
  time.sleep(2.0)

  # 2. South Korea: archaeological sites, dolmens, shellmounds, tombs, fortresses, kiln sites (complements KHS 17,965!)
  q_sk = """
SELECT DISTINCT ?item ?itemLabel ?koLabel ?typeLabel ?coord WHERE {
  ?item wdt:P17 wd:Q884 ;
        wdt:P625 ?coord .
  { ?item wdt:P31/wdt:P279* wd:Q839954 . } UNION
  { ?item wdt:P31/wdt:P279* wd:Q101659 . } UNION
  { ?item wdt:P31/wdt:P279* wd:Q381885 . } UNION
  { ?item wdt:P31/wdt:P279* wd:Q23413 . } UNION
  { ?item wdt:P31/wdt:P279* wd:Q57821 . }
  OPTIONAL { ?item wdt:P31 ?type . }
  OPTIONAL { ?item rdfs:label ?koLabel . FILTER(LANG(?koLabel) = "ko") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ko". }
}
LIMIT 10000
"""
  run_sparql("WD_SK_ARCH", q_sk, os.path.join(RAW_ARCH, "wd_south_korea_arch.json"))
  time.sleep(2.0)

  # 3. Japan: Kofun, Japanese Castles, Shellmounds, National Historic Sites (complements JASOSR + Rekihaku + MLIT P32!)
  q_jp = """
SELECT DISTINCT ?item ?itemLabel ?jaLabel ?typeLabel ?coord WHERE {
  ?item wdt:P17 wd:Q17 ;
        wdt:P625 ?coord .
  { ?item wdt:P31/wdt:P279* wd:Q1350226 . } UNION
  { ?item wdt:P31/wdt:P279* wd:Q839954 . } UNION
  { ?item wdt:P31/wdt:P279* wd:Q92026 . } UNION
  { ?item wdt:P1435 wd:Q3174299 . }
  OPTIONAL { ?item wdt:P31 ?type . }
  OPTIONAL { ?item rdfs:label ?jaLabel . FILTER(LANG(?jaLabel) = "ja") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ja". }
}
LIMIT 15000
"""
  run_sparql("WD_JP_KOFUN_CASTLES", q_jp, os.path.join(RAW_ARCH, "wd_japan_kofun_castles.json"))

  # 4. Also count AADR v66 ancient DNA samples inside Korea & Japan
  aadr_p = os.path.join(JADE_RAW, "aadr_v66.p1_HO.aadr.PUB.anno")
  if os.path.exists(aadr_p):
    cnt_jp, cnt_kr = 0, 0
    with open(aadr_p, encoding="utf-8", errors="replace") as fh:
      rdr = csv.reader(fh, delimiter="\t")
      hdr = next(rdr, [])
      for row in rdr:
        if len(row) < 17:
          continue
        pol = row[14] if len(row) > 14 else ""
        if "Japan" in pol:
          cnt_jp += 1
        elif "Korea" in pol:
          cnt_kr += 1
    print(f"[AADR v66] Japan={cnt_jp}, Korea={cnt_kr}")


if __name__ == "__main__":
  main()

