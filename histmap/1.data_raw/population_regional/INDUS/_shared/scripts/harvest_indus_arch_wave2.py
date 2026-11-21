"""Wave 2 Multi-Repository Archaeological Harvester for Project INDUS.

Queries Wikidata ASI Monument IDs (P1371, ~3,700 centrally protected monuments across India),
state-protected Indian/Pakistani/Sri Lankan/Nepali/Bangladeshi/Bhutanese/Maldivian heritage
registers, ancient temples/stupas/forts with pre-1750 inception, and open GitHub/Zenodo
Cholistan/Indus/Deccan/South Indian megalithic archaeological corpora.
"""

import json
import os
import time
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional",
  "INDUS", "_shared", "sites_indus_south_asia", "0.raw_data"
)
os.makedirs(RAW_DIR, exist_ok=True)
HEADERS = {"User-Agent": "SVEA-OperationViscount-INDUS/1.0 (academic research; contact: austkaeztchen@confoederatio.org)"}
ENDPOINT = "https://query.wikidata.org/sparql"


def run_sparql(query, out_name, label):
  outp = os.path.join(RAW_DIR, out_name)
  if os.path.exists(outp) and os.path.getsize(outp) > 1000:
    print(f"  [SKIP] {label} already cached ({os.path.getsize(outp):,} B)", flush=True)
    return
  for attempt in range(3):
    try:
      r = requests.get(
        ENDPOINT,
        params={"query": query, "format": "json"},
        headers={**HEADERS, "Accept": "application/sparql-results+json"},
        timeout=95
      )
      if r.status_code == 200:
        rows = r.json().get("results", {}).get("bindings", [])
        with open(outp, "w", encoding="utf-8") as fh:
          json.dump(rows, fh, ensure_ascii=False)
        print(f"  [OK] {label}: {len(rows):,} rows", flush=True)
        return
      print(f"  [WARN] {label} HTTP {r.status_code} (attempt {attempt+1})", flush=True)
      time.sleep(5 * (attempt + 1))
    except Exception as e:
      print(f"  [ERR] {label}: {e}", flush=True)
      time.sleep(5)


def main():
  print("=== WAVE 2 SOUTH ASIA INSTITUTIONAL ARCHAEOLOGY HARVEST ===", flush=True)

  # 1. ALL ASI Centrally Protected Monuments via P1371 (official ASI Monument ID)
  run_sparql("""
  SELECT DISTINCT ?item ?itemLabel ?asi_id ?coord ?inception ?periodLabel ?cultureLabel ?typeLabel WHERE {
    ?item wdt:P1371 ?asi_id ;
          wdt:P625 ?coord .
    OPTIONAL { ?item wdt:P571 ?inception . }
    OPTIONAL { ?item wdt:P2348 ?period . }
    OPTIONAL { ?item wdt:P2596 ?culture . }
    OPTIONAL { ?item wdt:P31 ?type . }
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
  }
  """, "wikidata_asi_p1371_monuments.json", "ASI P1371 Centrally Protected Monuments")
  time.sleep(2)

  # 2. India State Protected Monuments (Q26940768) & Archaeological Sites (Q839954) & Ancient Cities (Q15661340) & Megaliths & Rock Shelters
  run_sparql("""
  SELECT DISTINCT ?item ?itemLabel ?coord ?inception ?periodLabel ?cultureLabel ?typeLabel WHERE {
    ?item wdt:P17 wd:Q668 ;
          wdt:P625 ?coord .
    {
      VALUES ?type { wd:Q839954 wd:Q15661340 wd:Q180987 wd:Q164240 wd:Q193514 wd:Q109607 wd:Q1542758 wd:Q57821 wd:Q23413 wd:Q11755880 }
      ?item wdt:P31 ?type .
    } UNION {
      ?item wdt:P1435 wd:Q26940768 .
      BIND(wd:Q26940768 AS ?type)
    }
    OPTIONAL { ?item wdt:P571 ?inception . }
    OPTIONAL { ?item wdt:P2348 ?period . }
    OPTIONAL { ?item wdt:P2596 ?culture . }
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
  }
  """, "wikidata_india_arch_and_state_monuments.json", "India Arch Sites & State Monuments")
  time.sleep(2)

  # 3. India Pre-1750 Dated Temples, Mosques, Palaces, Viharas, Caves (architectural/settlement horizon proxies)
  run_sparql("""
  SELECT DISTINCT ?item ?itemLabel ?coord ?inception ?periodLabel ?typeLabel WHERE {
    ?item wdt:P17 wd:Q668 ;
          wdt:P625 ?coord ;
          wdt:P571 ?inception .
    FILTER(YEAR(?inception) < 1750)
    VALUES ?type { wd:Q842402 wd:Q44539 wd:Q32815 wd:Q44613 wd:Q35509 wd:Q16560 wd:Q2065736 wd:Q5393308 }
    ?item wdt:P31 ?type .
    OPTIONAL { ?item wdt:P2348 ?period . }
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
  }
  """, "wikidata_india_pre1750_monuments.json", "India Pre-1750 Dated Temples/Mosques/Caves")
  time.sleep(2)

  # 4. Pakistan, Bangladesh, Sri Lanka, Nepal, Bhutan, Maldives comprehensive heritage/archaeological sites
  for slug, qid, label in [
    ("pakistan", "Q843", "Pakistan Arch & Heritage"),
    ("bangladesh", "Q902", "Bangladesh Arch & Heritage"),
    ("sri_lanka", "Q854", "Sri Lanka Arch & Heritage"),
    ("nepal", "Q837", "Nepal Arch & Heritage"),
    ("bhutan", "Q917", "Bhutan Arch & Heritage"),
    ("maldives", "Q826", "Maldives Arch & Heritage"),
    ("afghanistan", "Q889", "Afghanistan Frontier Arch"),
    ("myanmar", "Q836", "Myanmar Frontier Arch"),
  ]:
    run_sparql(f"""
    SELECT DISTINCT ?item ?itemLabel ?coord ?inception ?periodLabel ?cultureLabel ?typeLabel ?heritageLabel WHERE {{
      ?item wdt:P17 wd:{qid} ;
            wdt:P625 ?coord .
      {{
        VALUES ?type {{ wd:Q839954 wd:Q15661340 wd:Q180987 wd:Q164240 wd:Q109607 wd:Q1081138 wd:Q57821 wd:Q23413 wd:Q44613 wd:Q842402 wd:Q32815 wd:Q16560 wd:Q44539 wd:Q35509 }}
        ?item wdt:P31 ?type .
      }} UNION {{
        ?item wdt:P1435 ?heritage .
        OPTIONAL {{ ?item wdt:P31 ?type . }}
      }}
      OPTIONAL {{ ?item wdt:P571 ?inception . }}
      OPTIONAL {{ ?item wdt:P2348 ?period . }}
      OPTIONAL {{ ?item wdt:P2596 ?culture . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 10000
    """, f"wikidata_w2_{slug}.json", label)
    time.sleep(2)

  # 5. Open GitHub / Zenodo / Figshare archaeological mound & Indus datasets (e.g. fconesa/AgriExp2022, Orengo PNAS, etc.)
  for repo in ["fconesa/AgriExp2022", "fconesa/IndusSites", "achp-project/mahsa"]:
    r = requests.get(f"https://api.github.com/repos/{repo}/git/trees/main?recursive=1", headers=HEADERS, timeout=20)
    if r.status_code != 200:
      r = requests.get(f"https://api.github.com/repos/{repo}/git/trees/master?recursive=1", headers=HEADERS, timeout=20)
    if r.status_code == 200:
      tree = r.json().get("tree", [])
      data_files = [t["path"] for t in tree if any(t["path"].lower().endswith(e) for e in (".csv",".geojson",".json",".kml",".kmz",".gpkg",".shp"))]
      print(f"  GH {repo}: {len(data_files)} data files: {data_files[:10]}", flush=True)
      for df in data_files[:8]:
        for br in ("main", "master"):
          u = f"https://raw.githubusercontent.com/{repo}/{br}/{df}"
          dr = requests.get(u, headers=HEADERS, timeout=45)
          if dr.status_code == 200 and len(dr.content) > 100:
            safe = f"gh_{repo.replace('/','_')}_{os.path.basename(df)}"
            with open(os.path.join(RAW_DIR, safe), "wb") as out:
              out.write(dr.content)
            print(f"    Saved {safe} ({len(dr.content):,} B)", flush=True)
            break

  print("=== DONE WAVE 2 ARCHAEOLOGY HARVEST ===", flush=True)


if __name__ == "__main__":
  main()
