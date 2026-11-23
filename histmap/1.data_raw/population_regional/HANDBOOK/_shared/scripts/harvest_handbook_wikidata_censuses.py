"""Harvests multi-decade official census & historical settlement population series
(`P1082` with `P585` point-in-time + `P571` inception + `P625` coordinates + `P1566` GeoNames ID)
from Wikidata SPARQL across all 27 Project HANDBOOK countries/territories.

Captures official national statistical agency enumerations mirrored in Wikidata (SCI Iran 2006/2011/2016,
CAPMAS Egypt 1996/2006/2017, PCBS Palestine 1997/2007/2017 & 1922/1931/1945 Mandate Village Statistics,
CBS Israel, CSO Yemen 2004, DOS Jordan 2015, COSIT Iraq, CAS Lebanon, GASTAT Saudi Arabia, NCSI Oman,
HCP Morocco, ONS Algeria, INS Tunisia, BSC Libya, CYSTAT Cyprus, TUIK Turkey, GeoStat/ArmStat/AzStat, NSIA Afghanistan).
"""

import json
import os
import time
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CENSUS_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "HANDBOOK", "_shared", "_census_cache", "wikidata_censuses"
)
os.makedirs(CENSUS_DIR, exist_ok=True)

HEADERS = {
  "User-Agent": "SVEA-OperationViscount-HANDBOOK/1.0 (academic historical demography; contact: austkaeztchen@confoederatio.org)",
  "Accept": "application/sparql-results+json",
}
ENDPOINT = "https://query.wikidata.org/sparql"


def query_wd(q, out_fn, label):
  outp = os.path.join(CENSUS_DIR, out_fn)
  if os.path.exists(outp) and os.path.getsize(outp) > 200:
    print(f"  [SKIP] {label} already cached ({os.path.getsize(outp):,} B)", flush=True)
    return True
  for att in range(3):
    try:
      r = requests.get(ENDPOINT, params={"query": q, "format": "json"}, headers=HEADERS, timeout=40)
      if r.status_code == 200:
        rows = r.json().get("results", {}).get("bindings", [])
        with open(outp, "w", encoding="utf-8") as fh:
          json.dump(rows, fh, ensure_ascii=False)
        print(f"  [OK] {label}: {len(rows):,} rows", flush=True)
        return True
      print(f"  [WARN] {label}: HTTP {r.status_code} (att {att+1})", flush=True)
      time.sleep(5 * (att + 1))
    except Exception as e:
      print(f"  [ERR] {label}: {str(e)[:80]} (att {att+1})", flush=True)
      time.sleep(5 * (att + 1))
  return False


def build_std_query(qid, extra_filter="", limit=45000):
  return f"""
  SELECT ?item ?itemLabel ?coord ?pop ?date ?inception ?geonames WHERE {{
    ?item wdt:P17 wd:{qid} ;
          wdt:P625 ?coord ;
          p:P1082 ?stmt .
    ?stmt ps:P1082 ?pop .
    {extra_filter}
    OPTIONAL {{ ?stmt pq:P585 ?date . }}
    OPTIONAL {{ ?item wdt:P571 ?inception . }}
    OPTIONAL {{ ?item wdt:P1566 ?geonames . }}
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,fr,tr,de". }}
  }}
  LIMIT {limit}
  """


def main():
  print("=== HARVESTING WIKIDATA MULTI-DECADE OFFICIAL CENSUS SERIES (ALL 27 HANDBOOK TERRITORIES) ===", flush=True)

  # Direct P31 settlement class VALUES (avoids slow transitive P279* walk on Blazegraph -> 1-3s per country!)
  STD_CLS = (
    "VALUES ?cls { wd:Q515 wd:Q3957 wd:Q532 wd:Q486972 wd:Q15284 wd:Q1549591 wd:Q1637706 "
    "wd:Q5119 wd:Q200250 wd:Q174844 wd:Q22865 wd:Q257391 wd:Q5084 wd:Q3957 wd:Q137773 "
    "wd:Q2989454 wd:Q2039348 wd:Q123705 wd:Q12813115 wd:Q562061 wd:Q667509 wd:Q18511725 "
    "wd:Q2264924 wd:Q11270848 wd:Q629870 wd:Q13539802 wd:Q3191695 wd:Q22746 } "
    "?item wdt:P31 ?cls ."
  )
  standard_countries = [
    ("egypt", "Q79", "Egypt", f"{STD_CLS} FILTER(?pop >= 500)"),
    ("iraq", "Q796", "Iraq", STD_CLS),
    ("syria", "Q858", "Syria", f"{STD_CLS} FILTER(?pop >= 500)"),
    ("lebanon", "Q822", "Lebanon", STD_CLS),
    ("jordan", "Q810", "Jordan", STD_CLS),
    ("israel", "Q801", "Israel", STD_CLS),
    ("palestine", "Q219060", "Palestine", STD_CLS),
    ("mandate_palestine", "Q193714", "Mandatory Palestine (1922-1945 Village Statistics)", STD_CLS),
    ("cyprus", "Q229", "Cyprus", STD_CLS),
    ("saudi_arabia", "Q851", "Saudi Arabia", STD_CLS),
    ("oman", "Q842", "Oman", STD_CLS),
    ("uae", "Q878", "United Arab Emirates", STD_CLS),
    ("qatar", "Q846", "Qatar", STD_CLS),
    ("bahrain", "Q398", "Bahrain", STD_CLS),
    ("kuwait", "Q817", "Kuwait", STD_CLS),
    ("morocco", "Q1028", "Morocco", f"{STD_CLS} FILTER(?pop >= 500)"),
    ("algeria", "Q262", "Algeria", f"{STD_CLS} FILTER(?pop >= 500)"),
    ("tunisia", "Q948", "Tunisia", STD_CLS),
    ("libya", "Q1016", "Libya", STD_CLS),
    ("western_sahara", "Q6250", "Western Sahara", STD_CLS),
    ("georgia", "Q230", "Georgia", f"{STD_CLS} FILTER(?pop >= 500)"),
    ("armenia", "Q399", "Armenia", STD_CLS),
    ("azerbaijan", "Q227", "Azerbaijan", f"{STD_CLS} FILTER(?pop >= 500)"),
    ("afghanistan", "Q889", "Afghanistan", STD_CLS),
  ]

  for slug, qid, label, filt in standard_countries:
    query_wd(build_std_query(qid, filt, limit=45000), f"wd_pop_{slug}.json", f"{label} P1082")
    time.sleep(1.5)

  # Huge Wikidata countries (Iran has ~60k SCI villages; Yemen has ~40k CSO 2004 villages; Turkey has ~35k mahalle/villages)
  # Query by explicit settlement classes so queries finish in <10s with ZERO timeout!
  split_queries = [
    ("iran_cities", "Q794", "Iran Cities (SCI 2006/2011/2016)",
     "VALUES ?cls { wd:Q137773 wd:Q515 wd:Q3957 wd:Q1549591 wd:Q1637706 wd:Q5119 } ?item wdt:P31 ?cls ."),
    ("iran_villages_ge1000", "Q794", "Iran Large Villages >= 1000 (SCI 2006/2011/2016)",
     "VALUES ?cls { wd:Q532 wd:Q486972 } ?item wdt:P31 ?cls . FILTER(?pop >= 1000)"),
    ("yemen_cities_towns", "Q805", "Yemen Cities & Towns (CSO 2004)",
     "VALUES ?cls { wd:Q515 wd:Q3957 wd:Q1549591 wd:Q486972 wd:Q15284 } ?item wdt:P31 ?cls ."),
    ("yemen_villages_ge1000", "Q805", "Yemen Large Villages >= 1000 (CSO 2004)",
     "VALUES ?cls { wd:Q532 wd:Q2039348 } ?item wdt:P31 ?cls . FILTER(?pop >= 1000)"),
    ("turkey_cities_towns", "Q43", "Turkey Cities & District Towns (TUIK)",
     "VALUES ?cls { wd:Q515 wd:Q3957 wd:Q1549591 wd:Q1637706 wd:Q5119 wd:Q15284 wd:Q2264924 } ?item wdt:P31 ?cls ."),
  ]
  for slug, qid, label, filt in split_queries:
    query_wd(build_std_query(qid, filt, limit=50000), f"wd_pop_{slug}.json", label)
    time.sleep(2.0)

  print("=== DONE harvest_handbook_wikidata_censuses.py ===", flush=True)


if __name__ == "__main__":
  main()
