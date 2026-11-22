"""Stage B Wave 1 Programmatic Full-Row Census & Gazetteer Harvester for Project HANDBOOK.

Harvests full-row official national census schedules and historical gazetteers (zero Top-N caps)
across all 27 countries/territories in all 7 required HANDBOOK jurisdictions:
  - turkey: TR (TUIK 1927-2024)
  - iran: IR (SCI 1956-2016)
  - egypt: EG (CAPMAS 1882-2017)
  - levant_iraq: IQ, SY, LB, JO, IL, PS, CY (COSIT, CBS Syria, CAS, DOS, CBS Israel, PCBS, CYSTAT)
  - arabia: SA, YE, OM, AE, QA, BH, KW (GASTAT, CSO, NCSI, FCSA, PSA, iGA, CSB)
  - maghreb: MA, DZ, TN, LY, EH (HCP, ONS, INS, BSC, Spanish/Moroccan censuses)
  - caucasus_afghanistan: GE, AM, AZ, AF (GeoStat, ArmStat, AzStat, 1897/1926-1989 Soviet, NSIA)

Sources:
  1. Tim Bespyatov (pop-stat.mashke.org) official census archives across MENA, Anatolia, Iran, Caucasus, North Africa.
  2. citypopulation.de official national statistical agency census tables (full multi-year city & admin-1 series).
  3. Full GeoNames country dumps (26 ISO-2 codes) for authoritative geocoding, endonyms & homonym verification.
  4. Demoscope Weekly 1897 Imperial & 1926-1989 All-Union Soviet Transcaucasia city/uezd tables.
"""

import json
import os
import re
import time
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
HB_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "HANDBOOK")
CENSUS_DIR = os.path.join(HB_DIR, "_shared", "_census_cache")
os.makedirs(CENSUS_DIR, exist_ok=True)

HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SVEA-OperationViscount-HANDBOOK/1.0 (academic historical demography)"
}

ISO2_CODES = [
  "TR", "IR", "EG", "IQ", "SY", "LB", "JO", "IL", "PS", "CY",
  "SA", "YE", "OM", "AE", "QA", "BH", "KW",
  "MA", "DZ", "TN", "LY", "EH",
  "GE", "AM", "AZ", "AF"
]

# Full citypopulation.de official census pages for all 27 HANDBOOK countries/territories
CITYPOP_PAGES = [
  ("tr_cities", "https://www.citypopulation.de/en/turkey/cities/"),
  ("tr_admin", "https://www.citypopulation.de/en/turkey/admin/"),
  ("ir_cities", "https://www.citypopulation.de/en/iran/cities/"),
  ("ir_admin", "https://www.citypopulation.de/en/iran/admin/"),
  ("eg_cities", "https://www.citypopulation.de/en/egypt/cities/"),
  ("eg_admin", "https://www.citypopulation.de/en/egypt/admin/"),
  ("iq_cities", "https://www.citypopulation.de/en/iraq/cities/"),
  ("sy_cities", "https://www.citypopulation.de/en/syria/cities/"),
  ("lb_cities", "https://www.citypopulation.de/en/lebanon/cities/"),
  ("jo_cities", "https://www.citypopulation.de/en/jordan/cities/"),
  ("il_cities", "https://www.citypopulation.de/en/israel/cities/"),
  ("ps_cities", "https://www.citypopulation.de/en/palestine/cities/"),
  ("cy_cities", "https://www.citypopulation.de/en/cyprus/cities/"),
  ("cy_north", "https://www.citypopulation.de/en/cyprus/northerncyprus/"),
  ("sa_cities", "https://www.citypopulation.de/en/saudiarabia/cities/"),
  ("ye_cities", "https://www.citypopulation.de/en/yemen/cities/"),
  ("om_cities", "https://www.citypopulation.de/en/oman/cities/"),
  ("ae_cities", "https://www.citypopulation.de/en/uae/cities/"),
  ("qa_cities", "https://www.citypopulation.de/en/qatar/cities/"),
  ("bh_cities", "https://www.citypopulation.de/en/bahrain/cities/"),
  ("kw_cities", "https://www.citypopulation.de/en/kuwait/cities/"),
  ("ma_cities", "https://www.citypopulation.de/en/morocco/cities/"),
  ("dz_cities", "https://www.citypopulation.de/en/algeria/cities/"),
  ("tn_cities", "https://www.citypopulation.de/en/tunisia/cities/"),
  ("ly_cities", "https://www.citypopulation.de/en/libya/cities/"),
  ("eh_cities", "https://www.citypopulation.de/en/westernsahara/cities/"),
  ("ge_cities", "https://www.citypopulation.de/en/georgia/cities/"),
  ("am_cities", "https://www.citypopulation.de/en/armenia/cities/"),
  ("az_cities", "https://www.citypopulation.de/en/azerbaijan/cities/"),
  ("af_cities", "https://www.citypopulation.de/en/afghanistan/cities/"),
]


def fetch_file(url, dest, timeout=90):
  if os.path.exists(dest) and os.path.getsize(dest) > 500:
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
      print(f"  [WARN] HTTP {r.status_code}: {url}", flush=True)
      return False
    except Exception as e:
      if att == 2:
        print(f"  [ERR] {url}: {e}", flush=True)
      time.sleep(3)
  return False


def harvest_geonames():
  print("[1] Downloading full GeoNames dumps for all 26 HANDBOOK ISO-2 codes (geocoding & homonym audit)...", flush=True)
  for cc in ISO2_CODES:
    fetch_file(f"https://download.geonames.org/export/dump/{cc}.zip", os.path.join(CENSUS_DIR, f"geonames_{cc}.zip"), timeout=180)
  fetch_file("https://download.geonames.org/export/dump/admin1CodesASCII.txt", os.path.join(CENSUS_DIR, "geonames_admin1CodesASCII.txt"))


def harvest_popstat_handbook():
  print("[2] Downloading Tim Bespyatov (pop-stat.mashke.org) official census pages for HANDBOOK countries...", flush=True)
  idx_p = os.path.join(CENSUS_DIR, "popstat_index.htm")
  fetch_file("http://pop-stat.mashke.org/index.htm", idx_p, timeout=45)
  keywords = (
    "georgia", "armenia", "azerbaijan", "turkey", "iran", "egypt", "iraq", "syria", "lebanon",
    "jordan", "israel", "palestine", "cyprus", "saudi", "yemen", "oman", "emirates", "uae",
    "qatar", "bahrain", "kuwait", "morocco", "algeria", "tunisia", "libya", "afghan", "sahara"
  )
  pages = set([
    "georgia-cities.htm", "armenia-cities.htm", "azerbaijan-cities.htm",
    "turkey-cities.htm", "iran-cities.htm", "egypt-cities.htm",
    "algeria-cities.htm", "morocco-cities.htm", "tunisia-cities.htm",
    "cyprus-cities.htm", "israel-cities.htm", "jordan-cities.htm",
    "iraq-cities.htm", "syria-cities.htm", "lebanon-cities.htm",
    "saudi-arabia-cities.htm", "yemen-cities.htm", "oman-cities.htm",
    "afghanistan-cities.htm", "libya-cities.htm"
  ])
  if os.path.exists(idx_p):
    txt = open(idx_p, "r", encoding="utf-8", errors="replace").read()
    for m in re.findall(r'href=["\']([^"\']+\.htm)["\']', txt, flags=re.I):
      low = m.lower()
      if "romania" in low or "germany" in low or "bulgaria" in low or "greece" in low:
        continue
      if any(re.search(rf"(?:^|/|-)({k})", low) for k in keywords) and not any(x in low for x in ("ethnic", "lang", "relig", "age", "citizenship", "birth", "absent")):
        pages.add(m.lstrip("./"))
  print(f"  Discovered {len(pages)} pop-stat pages...", flush=True)
  for pg in sorted(pages):
    url = pg if pg.startswith("http") else f"http://pop-stat.mashke.org/{pg}"
    rel_pg = re.sub(r"^https?://[^/]+/", "", url)
    safe = "popstat_" + re.sub(r"[^A-Za-z0-9._-]+", "_", rel_pg)
    fetch_file(url, os.path.join(CENSUS_DIR, safe), timeout=45)
    time.sleep(0.2)


def harvest_citypopulation():
  print("[3] Downloading full citypopulation.de official national census tables across all 27 countries...", flush=True)
  for tag, url in CITYPOP_PAGES:
    fetch_file(url, os.path.join(CENSUS_DIR, f"citypop_{tag}.html"), timeout=45)
    time.sleep(0.35)


if __name__ == "__main__":
  harvest_geonames()
  harvest_popstat_handbook()
  harvest_citypopulation()
  print("DONE harvest_handbook_censuses.py", flush=True)
