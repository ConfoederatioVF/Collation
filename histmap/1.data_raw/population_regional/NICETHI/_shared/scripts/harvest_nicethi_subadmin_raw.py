"""Downloads authoritative sub-administrative enumeration and boundary-lineage raw sources
for all 54+ Operation Viscount Project NICETHI jurisdictions into
`NICETHI/_shared/subadmin_hgis/raw_sources/`.

Sources harvested:
  1. Statoids (Gwillim Law) administrative division tables & legislative change histories.
  2. CityPopulation (Thomas Brinkhoff) official national census mirrors (`/admin/` or country tables).
  3. Wikidata SPARQL Admin-1 official census population statements (`P1082` + `P585`).
  4. geoBoundaries `gbOpen` ADM1 feature names & GeoNames `admin1CodesASCII.txt`.
"""

import concurrent.futures
import json
import os
import re
import time
import urllib.parse
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "NICETHI",
  "_shared", "subadmin_hgis", "raw_sources"
)
STATOIDS_DIR = os.path.join(RAW_DIR, "statoids")
CITYPOP_DIR = os.path.join(RAW_DIR, "citypop")
WIKIDATA_DIR = os.path.join(RAW_DIR, "wikidata")
GB_DIR = os.path.join(RAW_DIR, "geoboundaries")

for d in (RAW_DIR, STATOIDS_DIR, CITYPOP_DIR, WIKIDATA_DIR, GB_DIR):
  os.makedirs(d, exist_ok=True)

HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SVEA-OperationViscount-NICETHI/1.0 (academic historical demography)"
}

# Canonical 54+ NICETHI jurisdictions:
# (ISO3, name, statoids_slug, citypop_urls, wikidata_qid)
JURISDICTIONS = [
  ("AGO", "Angola", "uao", ["https://www.citypopulation.de/en/angola/admin/"], "Q916"),
  ("ATF", "French Southern Territories", "utf", [], "Q129003"),
  ("BDI", "Burundi", "ubi", ["https://www.citypopulation.de/en/burundi/admin/"], "Q967"),
  ("BEN", "Benin", "ubj", ["https://www.citypopulation.de/en/benin/admin/"], "Q962"),
  ("BFA", "Burkina Faso", "ubf", ["https://www.citypopulation.de/en/burkinafaso/admin/"], "Q965"),
  ("BWA", "Botswana", "ubw", ["https://www.citypopulation.de/en/botswana/"], "Q963"),
  ("CAF", "Central African Republic", "ucf", ["https://www.citypopulation.de/en/centralafrica/admin/"], "Q929"),
  ("CIV", "Côte d'Ivoire", "uci", ["https://www.citypopulation.de/en/ivorycoast/admin/"], "Q1008"),
  ("CMR", "Cameroon", "ucm", ["https://www.citypopulation.de/en/cameroon/admin/"], "Q1009"),
  ("COD", "Democratic Republic of the Congo", "ucd", ["https://www.citypopulation.de/en/drcongo/cities/"], "Q974"),
  ("COG", "Republic of the Congo", "ucg", ["https://www.citypopulation.de/en/congo/admin/"], "Q971"),
  ("COM", "Comoros", "ukm", ["https://www.citypopulation.de/en/comoros/admin/"], "Q970"),
  ("CPV", "Cabo Verde", "ucv", ["https://www.citypopulation.de/en/capeverde/"], "Q1011"),
  ("DJI", "Djibouti", "udj", ["https://www.citypopulation.de/en/djibouti/admin/"], "Q977"),
  ("ERI", "Eritrea", "uer", ["https://www.citypopulation.de/en/eritrea/"], "Q986"),
  ("ETH", "Ethiopia", "uet", ["https://www.citypopulation.de/en/ethiopia/admin/"], "Q115"),
  ("GAB", "Gabon", "uga", ["https://www.citypopulation.de/en/gabon/admin/"], "Q1000"),
  ("GHA", "Ghana", "ugh", ["https://www.citypopulation.de/en/ghana/admin/"], "Q117"),
  ("GIN", "Guinea", "ugn", ["https://www.citypopulation.de/en/guinea/admin/"], "Q1006"),
  ("GMB", "The Gambia", "ugm", ["https://www.citypopulation.de/en/gambia/admin/"], "Q1005"),
  ("GNB", "Guinea-Bissau", "ugw", ["https://www.citypopulation.de/en/guineabissau/"], "Q1007"),
  ("GNQ", "Equatorial Guinea", "ugq", ["https://www.citypopulation.de/en/equatorialguinea/"], "Q983"),
  ("IOT", "British Indian Ocean Territory", "uio", [], "Q43448"),
  ("KEN", "Kenya", "uke", ["https://www.citypopulation.de/en/kenya/admin/"], "Q114"),
  ("LBR", "Liberia", "ulr", ["https://www.citypopulation.de/en/liberia/"], "Q1014"),
  ("LSO", "Lesotho", "uls", ["https://www.citypopulation.de/en/lesotho/"], "Q1013"),
  ("MDG", "Madagascar", "umg", ["https://www.citypopulation.de/en/madagascar/admin/"], "Q1019"),
  ("MLI", "Mali", "uml", ["https://www.citypopulation.de/en/mali/admin/"], "Q912"),
  ("MOZ", "Mozambique", "umz", ["https://www.citypopulation.de/en/mozambique/admin/"], "Q1029"),
  ("MRT", "Mauritania", "umr", ["https://www.citypopulation.de/en/mauritania/admin/"], "Q1025"),
  ("MUS", "Mauritius", "umu", ["https://www.citypopulation.de/en/mauritius/admin/"], "Q1027"),
  ("MWI", "Malawi", "umw", ["https://www.citypopulation.de/en/malawi/admin/"], "Q1020"),
  ("MYT", "Mayotte", "uyt", ["https://www.citypopulation.de/en/france/reg/mayotte/"], "Q17063"),
  ("NAM", "Namibia", "una", ["https://www.citypopulation.de/en/namibia/admin/"], "Q1030"),
  ("NER", "Niger", "une", ["https://www.citypopulation.de/en/niger/admin/"], "Q1032"),
  ("NGA", "Nigeria", "ung", ["https://www.citypopulation.de/en/nigeria/admin/"], "Q1033"),
  ("REU", "Réunion", "ure", ["https://www.citypopulation.de/en/france/reg/reunion/"], "Q17070"),
  ("RWA", "Rwanda", "urw", ["https://www.citypopulation.de/en/rwanda/admin/"], "Q1037"),
  ("SDN", "Sudan", "usd", ["https://www.citypopulation.de/en/sudan/"], "Q1049"),
  ("SEN", "Senegal", "usn", ["https://www.citypopulation.de/en/senegal/admin/"], "Q1041"),
  ("SHN", "Saint Helena, Ascension and Tristan da Cunha", "ush", ["https://www.citypopulation.de/en/sthelena/"], "Q192184"),
  ("SLE", "Sierra Leone", "usl", ["https://www.citypopulation.de/en/sierraleone/admin/"], "Q1044"),
  ("SOL", "Somaliland", None, ["https://www.citypopulation.de/en/somalia/"], "Q34754"),
  ("SOM", "Somalia", "uso", ["https://www.citypopulation.de/en/somalia/admin/", "https://www.citypopulation.de/en/somalia/"], "Q1045"),
  ("SSD", "South Sudan", "uss", ["https://www.citypopulation.de/en/southsudan/admin/"], "Q958"),
  ("STP", "São Tomé and Príncipe", "ust", ["https://www.citypopulation.de/en/saotome/admin/"], "Q1039"),
  ("SWZ", "Eswatini", "usz", ["https://www.citypopulation.de/en/eswatini/"], "Q1050"),
  ("SYC", "Seychelles", "usc", ["https://www.citypopulation.de/en/seychelles/admin/"], "Q1042"),
  ("TCD", "Chad", "utd", ["https://www.citypopulation.de/en/chad/"], "Q657"),
  ("TGO", "Togo", "utg", ["https://www.citypopulation.de/en/togo/admin/"], "Q945"),
  ("TZA", "Tanzania", "utz", ["https://www.citypopulation.de/en/tanzania/admin/"], "Q924"),
  ("UGA", "Uganda", "uug", ["https://www.citypopulation.de/en/uganda/admin/"], "Q1036"),
  ("ZAF", "South Africa", "uza", ["https://www.citypopulation.de/en/southafrica/admin/"], "Q258"),
  ("ZMB", "Zambia", "uzm", ["https://www.citypopulation.de/en/zambia/admin/"], "Q953"),
  ("ZWE", "Zimbabwe", "uzw", ["https://www.citypopulation.de/en/zimbabwe/admin/"], "Q954"),
]


def fetch_url(url, dest, min_bytes=500, timeout=30):
  if os.path.exists(dest) and os.path.getsize(dest) >= min_bytes:
    return True
  for att in range(3):
    try:
      r = requests.get(url, headers=HEADERS, timeout=timeout)
      if r.status_code == 200 and len(r.content) >= min_bytes and len(r.content) != 8316:
        with open(dest, "wb") as fh:
          fh.write(r.content)
        return True
      if r.status_code in (429, 502, 503, 504):
        time.sleep(2 * (att + 1))
        continue
      return False
    except Exception:
      time.sleep(1.5 * (att + 1))
  return False


def harvest_statoids():
  print("[1/4] Harvesting Statoids pages...", flush=True)
  ok = 0
  for iso3, name, st, _cp, _qid in JURISDICTIONS:
    if not st:
      continue
    dest = os.path.join(STATOIDS_DIR, f"{iso3}_{st}.html")
    if fetch_url(f"http://www.statoids.com/{st}.html", dest, min_bytes=1000):
      ok += 1
    else:
      print(f"  [WARN] Statoids miss: {iso3} ({st})", flush=True)
  print(f"  Statoids OK: {ok}", flush=True)


def harvest_citypop():
  print("[2/4] Harvesting CityPopulation pages...", flush=True)
  ok = 0
  for iso3, name, _st, urls, _qid in JURISDICTIONS:
    for idx, url in enumerate(urls):
      suffix = "" if idx == 0 else f"_{idx}"
      dest = os.path.join(CITYPOP_DIR, f"{iso3}{suffix}.html")
      if fetch_url(url, dest, min_bytes=5000):
        ok += 1
        if idx == 0:
          break
      else:
        print(f"  [WARN] CityPop miss: {iso3} {url}", flush=True)
    time.sleep(0.2)
  print(f"  CityPopulation OK: {ok}", flush=True)


def harvest_geoboundaries_adm1():
  print("[3/4] Harvesting geoBoundaries gbOpen ADM1 metadata & GeoJSON...", flush=True)
  ok = 0

  def one(item):
    iso3 = item[0]
    if iso3 in ("SOL",):
      return iso3, False
    meta_p = os.path.join(GB_DIR, f"{iso3}_ADM1_meta.json")
    gj_p = os.path.join(GB_DIR, f"{iso3}_ADM1.geojson")
    if os.path.exists(gj_p) and os.path.getsize(gj_p) > 200:
      return iso3, True
    try:
      r = requests.get(f"https://www.geoboundaries.org/api/current/gbOpen/{iso3}/ADM1/", headers=HEADERS, timeout=25)
      if r.status_code != 200:
        return iso3, False
      meta = r.json()
      with open(meta_p, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
      dl = meta.get("simplifiedGeometryGeoJSON") or meta.get("gjDownloadURL")
      if not dl:
        return iso3, False
      r2 = requests.get(dl, headers=HEADERS, timeout=60)
      if r2.status_code == 200 and len(r2.content) > 200:
        with open(gj_p, "wb") as fh:
          fh.write(r2.content)
        return iso3, True
    except Exception:
      pass
    return iso3, False

  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    for iso3, res in ex.map(one, JURISDICTIONS):
      if res:
        ok += 1
      else:
        print(f"  [WARN] geoBoundaries ADM1 miss: {iso3}", flush=True)
  print(f"  geoBoundaries ADM1 OK: {ok}", flush=True)


def harvest_wikidata_adm1():
  print("[4/4] Harvesting Wikidata Admin-1 official census series...", flush=True)
  wd_headers = {
    "User-Agent": "SVEA-OperationViscount-NICETHI/1.0 (academic historical demography; contact: austkaeztchen@confoederatio.org)",
    "Accept": "application/sparql-results+json"
  }
  ok = 0
  for iso3, name, _st, _cp, qid in JURISDICTIONS:
    if not qid:
      continue
    out_p = os.path.join(WIKIDATA_DIR, f"{iso3}.json")
    if os.path.exists(out_p) and os.path.getsize(out_p) > 50:
      ok += 1
      continue
    q = f"""
    SELECT ?adm1 ?adm1Label ?pop ?date ?iso WHERE {{
      wd:{qid} wdt:P150 ?adm1 .
      OPTIONAL {{ ?adm1 wdt:P300 ?iso . }}
      ?adm1 p:P1082 ?st .
      ?st ps:P1082 ?pop .
      OPTIONAL {{ ?st pq:P585 ?date . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,fr,pt". }}
    }}
    LIMIT 2000
    """
    for att in range(3):
      try:
        r = requests.get(
          "https://query.wikidata.org/sparql",
          params={"query": q, "format": "json"},
          headers=wd_headers,
          timeout=30,
        )
        if r.status_code == 200:
          rows = r.json().get("results", {}).get("bindings", [])
          with open(out_p, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False)
          ok += 1
          break
        time.sleep(3 * (att + 1))
      except Exception:
        time.sleep(3 * (att + 1))
    time.sleep(0.5)
  print(f"  Wikidata ADM1 OK: {ok}", flush=True)


def harvest_geonames_adm1():
  dest = os.path.join(RAW_DIR, "geonames_admin1CodesASCII.txt")
  fetch_url("https://download.geonames.org/export/dump/admin1CodesASCII.txt", dest, min_bytes=1000)


if __name__ == "__main__":
  harvest_geonames_adm1()
  harvest_statoids()
  harvest_citypop()
  harvest_geoboundaries_adm1()
  harvest_wikidata_adm1()
  print("DONE harvest_nicethi_subadmin_raw.py", flush=True)
