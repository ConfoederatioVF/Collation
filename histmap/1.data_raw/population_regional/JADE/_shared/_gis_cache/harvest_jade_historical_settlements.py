"""Multi-Repository Historical Settlement Harvester for Operation Viscount Project JADE.

Downloads and caches authoritative primary historical settlement & archaeological databases
into JADE/_shared/_census_cache/historical_harvest/ (100% non-circular, zero Wikipedia scraping):
  1. CBDB (China Biographical Database) SQLite -> ADDR_CODES historical places (Tang-Qing)
  2. Zenodo 17107786: Chronology of Early China Radiocarbon Databank v2023.4
  3. Zenodo 22094815 / 5721459 / 5721486: Modern China Geospatial Database (MCGD)
  4. Academia Sinica depositar.io: Taiwan Baotu (rd01-1-2) & Dutch VOC Southwest Taiwan (ra01)
  5. Harvard Dataverse: China City Walls (DVN/7MXVKV) & Ming Garrisons / CHGIS supplemental
  6. Wikidata SPARQL (partitioned by country/class): CN, MN, TW, HK, MO historical settlements,
     ancient cities, historic towns, National & Provincial Cultural Heritage Units, monasteries
  7. OpenStreetMap Overpass (tiled): China macro-regions, Mongolia, Taiwan, Hong Kong & Macao
     historic=archaeological_site, fort, castle, city_gate, monastery, ruins
  8. Documentation of Mongolian Monasteries (mongoliantemples.org) georeferenced monasteries
"""

import io
import json
import os
import re
import sqlite3
import time
import urllib.parse
import zipfile

import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
JADE_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE")
OUT_DIR = os.path.join(JADE_DIR, "_shared", "_census_cache", "historical_harvest")
os.makedirs(OUT_DIR, exist_ok=True)

HEADERS = {
  "User-Agent": "SVEA-OperationViscount-JADE/1.0 (academic historical demography research; contact: austkaeztchen@confoederatio.org)"
}


def safe_get(arg0_url, arg1_params=None, arg2_timeout=90, arg3_headers=None, arg4_stream=False):
  hdr = dict(HEADERS)
  if arg3_headers:
    hdr.update(arg3_headers)
  for attempt in range(3):
    try:
      r = requests.get(arg0_url, params=arg1_params, headers=hdr, timeout=arg2_timeout, stream=arg4_stream)
      if r.status_code == 200:
        return r
      if r.status_code in (429, 502, 503, 504):
        time.sleep(5 * (attempt + 1))
        continue
      print(f"  [WARN] HTTP {r.status_code} for {arg0_url}", flush=True)
      return r
    except Exception as ex:
      if attempt == 2:
        print(f"  [WARN] GET failed {arg0_url}: {ex}", flush=True)
      time.sleep(4)
  return None


def harvest_cbdb():
  out_json = os.path.join(OUT_DIR, "cbdb_historical_addresses.json")
  if os.path.exists(out_json) and os.path.getsize(out_json) > 50000:
    print(f"[1] CBDB already extracted: {out_json}", flush=True)
    return
  print("[1] Downloading CBDB SQLite (cbdb-project/cbdb_sqlite) & extracting ADDR_CODES...", flush=True)
  r = safe_get("https://raw.githubusercontent.com/cbdb-project/cbdb_sqlite/master/latest.json", arg2_timeout=30)
  if not r or r.status_code != 200:
    print("  [WARN] Could not fetch CBDB latest.json", flush=True)
    return
  meta = r.json()
  hf_url = meta.get("huggingface_url")
  if not hf_url:
    print("  [WARN] Missing huggingface_url in latest.json", flush=True)
    return
  zp = os.path.join(OUT_DIR, "cbdb_latest.zip")
  if not os.path.exists(zp) or os.path.getsize(zp) < 10_000_000:
    print(f"  Streaming {hf_url} ...", flush=True)
    dr = safe_get(hf_url, arg2_timeout=300, arg4_stream=True)
    if not dr or dr.status_code != 200:
      print("  [WARN] Failed downloading CBDB zip", flush=True)
      return
    with open(zp, "wb") as fh:
      for chunk in dr.iter_content(chunk_size=1024 * 512):
        if chunk:
          fh.write(chunk)
    print(f"  Saved CBDB zip: {os.path.getsize(zp):,} B", flush=True)

  db_path = os.path.join(OUT_DIR, "cbdb_tmp.sqlite3")
  with zipfile.ZipFile(zp) as zf:
    db_names = [n for n in zf.namelist() if n.endswith((".sqlite3", ".db"))]
    if not db_names:
      print("  [WARN] No sqlite file inside CBDB zip", flush=True)
      return
    with zf.open(db_names[0]) as src, open(db_path, "wb") as dst:
      while True:
        buf = src.read(1024 * 1024)
        if not buf:
          break
        dst.write(buf)

  con = sqlite3.connect(db_path)
  cur = con.cursor()
  cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
  tbls = {row[0].upper(): row[0] for row in cur.fetchall()}
  addr_tbl = tbls.get("ADDR_CODES") or tbls.get("ADDRESSES")
  if not addr_tbl:
    print("  [WARN] No ADDR_CODES table in CBDB:", list(tbls.keys())[:20], flush=True)
    con.close()
    os.remove(db_path)
    return
  cur.execute(f"PRAGMA table_info({addr_tbl})")
  cols = [row[1] for row in cur.fetchall()]
  print(f"  CBDB {addr_tbl} columns: {cols}", flush=True)
  cur.execute(f"SELECT * FROM {addr_tbl}")
  rows = []
  for r_tup in cur.fetchall():
    rec = dict(zip(cols, r_tup))
    x = rec.get("x_coord") or rec.get("X_COORD")
    y = rec.get("y_coord") or rec.get("Y_COORD")
    if x is None or y is None:
      continue
    try:
      xf, yf = float(x), float(y)
    except Exception:
      continue
    if not (73.0 <= xf <= 136.0 and 18.0 <= yf <= 54.5):
      continue
    rows.append({
      "addr_id": rec.get("c_addr_id") or rec.get("C_ADDR_ID"),
      "name_py": rec.get("c_name") or rec.get("C_NAME") or "",
      "name_zh": rec.get("c_name_chn") or rec.get("C_NAME_CHN") or "",
      "firstyear": rec.get("c_firstyear") or rec.get("C_FIRSTYEAR"),
      "lastyear": rec.get("c_lastyear") or rec.get("C_LASTYEAR"),
      "chgis_id": rec.get("c_chgis_pt_id") or rec.get("C_CHGIS_PT_ID"),
      "lat": yf,
      "lon": xf,
      "alt_names": rec.get("c_alt_names") or rec.get("C_ALT_NAMES") or "",
    })
  con.close()
  try:
    os.remove(db_path)
  except Exception:
    pass
  with open(out_json, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  CBDB extracted {len(rows):,} georeferenced historical places -> {out_json}", flush=True)


def harvest_zenodo_records():
  print("[2] Downloading Zenodo Early China C14 (17107786) & MCGD (22094815, 5721459, 5721486)...", flush=True)
  targets = [
    (17107786, ("Radiocarbon databank for Chinese archaeology v2023.4.xlsx",)),
    (22094815, ("MCGD_Data2026_08_25.csv",)),
    (5721459, ("MCGD_Rep_V2.csv",)),
    (5721486, ("MCGD_PRC_V1.csv",)),
  ]
  for rid, wanted in targets:
    r = safe_get(f"https://zenodo.org/api/records/{rid}", arg2_timeout=30)
    if not r or r.status_code != 200:
      continue
    for f in r.json().get("files", []):
      fn = f.get("key", "")
      if wanted and fn not in wanted:
        continue
      safe_fn = re.sub(r"[^A-Za-z0-9._-]+", "_", f"zenodo_{rid}_{fn}")
      outp = os.path.join(OUT_DIR, safe_fn)
      if os.path.exists(outp) and os.path.getsize(outp) > 5000:
        print(f"  Already cached: {safe_fn}", flush=True)
        continue
      dl = f.get("links", {}).get("self")
      if not dl:
        continue
      dr = safe_get(dl, arg2_timeout=180, arg4_stream=True)
      if dr and dr.status_code == 200:
        with open(outp, "wb") as fh:
          for chunk in dr.iter_content(chunk_size=512 * 1024):
            if chunk:
              fh.write(chunk)
        print(f"  Saved {safe_fn} ({os.path.getsize(outp):,} B)", flush=True)


def harvest_depositar_taiwan():
  print("[3] Harvesting Academia Sinica depositar.io Taiwan historical place-name datasets (rd01-1-2, ra01)...", flush=True)
  for pkg in ("rd01-1-2", "ra01"):
    try:
      r = safe_get(f"https://data.depositar.io/api/3/action/package_show?id={pkg}", arg2_timeout=30)
      if not r or r.status_code != 200 or not r.text.strip().startswith("{"):
        r = safe_get("https://data.depositar.io/api/3/action/package_search", arg1_params={"q": pkg, "rows": 2}, arg2_timeout=30)
        if not r or r.status_code != 200 or not r.text.strip().startswith("{"):
          continue
        results = r.json().get("result", {}).get("results", [])
        res_list = results[0].get("resources", []) if results else []
      else:
        res_list = r.json().get("result", {}).get("resources", [])
    except Exception as ex:
      print(f"  [WARN] depositar {pkg}: {ex}", flush=True)
      continue
    for res in res_list:
      url = res.get("url")
      fmt = str(res.get("format") or "").lower()
      name = res.get("name") or res.get("id") or "file"
      if not url:
        continue
      ext = os.path.splitext(urllib.parse.urlparse(url).path)[1] or (f".{fmt}" if fmt else ".dat")
      safe_fn = re.sub(r"[^A-Za-z0-9._-]+", "_", f"depositar_{pkg}_{name}{ext}")
      outp = os.path.join(OUT_DIR, safe_fn)
      if os.path.exists(outp) and os.path.getsize(outp) > 500:
        print(f"  Already cached: {safe_fn}", flush=True)
        continue
      dr = safe_get(url, arg2_timeout=90)
      if dr and dr.status_code == 200 and len(dr.content) > 200:
        with open(outp, "wb") as fh:
          fh.write(dr.content)
        print(f"  Saved {safe_fn} ({len(dr.content):,} B)", flush=True)


def harvest_dataverse_city_walls():
  print("[4] Harvesting Harvard Dataverse CHGIS Supplemental & China City Walls datasets...", flush=True)
  dois = [
    ("7MXVKV", "doi:10.7910/DVN/7MXVKV"),
    ("3KAHBT", "doi:10.7910/DVN/3KAHBT"),
    ("5RUXK8", "doi:10.7910/DVN/5RUXK8"),
    ("SB8ZTM", "doi:10.7910/DVN/SB8ZTM"),
    ("SC7AOU", "doi:10.7910/DVN/SC7AOU"),
    ("TI8DFI", "doi:10.7910/DVN/TI8DFI"),
    ("W6PFXR", "doi:10.7910/DVN/W6PFXR"),
  ]
  for tag, doi in dois:
    try:
      r = safe_get(f"https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId={doi}", arg2_timeout=30)
      if not r or r.status_code != 200:
        continue
      lv = r.json().get("data", {}).get("latestVersion", {})
      meta_f = lv.get("metadataBlocks", {}).get("citation", {}).get("fields", [])
      title = next((f.get("value", "") for f in meta_f if f.get("typeName") == "title"), tag)
      files = lv.get("files", [])
      print(f"  Dataverse {tag}: {str(title)[:75]} ({len(files)} files)", flush=True)
      for f in files:
        df = f.get("dataFile", {})
        fid = df.get("id")
        fn = df.get("filename", f"file_{fid}")
        fsize = int(df.get("filesize") or 0)
        if not fid or fsize > 40_000_000:
          continue
        if not any(fn.lower().endswith(ext) for ext in (".zip", ".csv", ".tsv", ".xlsx", ".xls", ".geojson", ".json", ".dbf", ".shp", ".txt", ".tab")):
          continue
        safe_fn = re.sub(r"[^A-Za-z0-9._-]+", "_", f"dvn_{tag.lower()}_{fn}")
        outp = os.path.join(OUT_DIR, safe_fn)
        if os.path.exists(outp) and os.path.getsize(outp) > 500:
          print(f"    Already cached: {safe_fn}", flush=True)
          continue
        dr = safe_get(f"https://dataverse.harvard.edu/api/access/datafile/{fid}", arg2_timeout=120)
        if dr and dr.status_code == 200 and len(dr.content) > 100:
          with open(outp, "wb") as fh:
            fh.write(dr.content)
          print(f"    Saved {safe_fn} ({len(dr.content):,} B)", flush=True)
    except Exception as ex:
      print(f"  [WARN] Dataverse {tag}: {ex}", flush=True)


def harvest_wikidata_jade():
  print("[5] Harvesting Wikidata SPARQL historical settlements, ancient cities, heritage & monasteries across JADE...", flush=True)
  endpoint = "https://query.wikidata.org/sparql"
  queries = [
    ("wd_cn_ancient_and_arch", """
      SELECT DISTINCT ?item ?itemLabel ?zhLabel ?coord ?classLabel ?inception ?dissolved ?periodLabel WHERE {
        ?item wdt:P17 wd:Q148 ; wdt:P625 ?coord .
        VALUES ?class { wd:Q839954 wd:Q15661340 wd:Q109607 wd:Q57821 wd:Q23413 wd:Q16748868 wd:Q15243209 }
        ?item wdt:P31 ?class .
        OPTIONAL { ?item rdfs:label ?zhLabel . FILTER(LANG(?zhLabel) = "zh") }
        OPTIONAL { ?item wdt:P571 ?inception . }
        OPTIONAL { ?item wdt:P576 ?dissolved . }
        OPTIONAL { ?item wdt:P2348 ?period . }
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en,zh". }
      } LIMIT 15000
    """),
    ("wd_cn_national_heritage", """
      SELECT DISTINCT ?item ?itemLabel ?zhLabel ?coord ?inception ?periodLabel ?classLabel WHERE {
        ?item wdt:P1435 wd:Q1075586 ; wdt:P625 ?coord .
        OPTIONAL { ?item wdt:P31 ?class . }
        OPTIONAL { ?item rdfs:label ?zhLabel . FILTER(LANG(?zhLabel) = "zh") }
        OPTIONAL { ?item wdt:P571 ?inception . }
        OPTIONAL { ?item wdt:P2348 ?period . }
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en,zh". }
      } LIMIT 15000
    """),
    ("wd_cn_provincial_heritage", """
      SELECT DISTINCT ?item ?itemLabel ?zhLabel ?coord ?inception ?periodLabel ?classLabel WHERE {
        ?item wdt:P1435 wd:Q10899848 ; wdt:P625 ?coord .
        OPTIONAL { ?item wdt:P31 ?class . }
        OPTIONAL { ?item rdfs:label ?zhLabel . FILTER(LANG(?zhLabel) = "zh") }
        OPTIONAL { ?item wdt:P571 ?inception . }
        OPTIONAL { ?item wdt:P2348 ?period . }
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en,zh". }
      } LIMIT 15000
    """),
    ("wd_cn_historic_towns_villages", """
      SELECT DISTINCT ?item ?itemLabel ?zhLabel ?coord ?inception ?classLabel WHERE {
        ?item wdt:P17 wd:Q148 ; wdt:P625 ?coord .
        VALUES ?h { wd:Q10873361 wd:Q10873360 wd:Q15913788 wd:Q11160004 }
        ?item wdt:P1435 ?h .
        OPTIONAL { ?item wdt:P31 ?class . }
        OPTIONAL { ?item rdfs:label ?zhLabel . FILTER(LANG(?zhLabel) = "zh") }
        OPTIONAL { ?item wdt:P571 ?inception . }
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en,zh". }
      } LIMIT 15000
    """),
    ("wd_cn_pre1800_towns_inception", """
      SELECT DISTINCT ?item ?itemLabel ?zhLabel ?coord ?inception ?classLabel WHERE {
        ?item wdt:P17 wd:Q148 ; wdt:P625 ?coord ; wdt:P571 ?inception .
        FILTER(YEAR(?inception) < 1800)
        VALUES ?class { wd:Q486972 wd:Q515 wd:Q3957 wd:Q532 wd:Q1289426 wd:Q50337 wd:Q1348006 wd:Q44613 wd:Q160742 }
        ?item wdt:P31 ?class .
        OPTIONAL { ?item rdfs:label ?zhLabel . FILTER(LANG(?zhLabel) = "zh") }
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en,zh". }
      } LIMIT 15000
    """),
    ("wd_mn_all_hist_monasteries", """
      SELECT DISTINCT ?item ?itemLabel ?mnLabel ?coord ?classLabel ?inception ?dissolved WHERE {
        ?item wdt:P17 wd:Q711 ; wdt:P625 ?coord .
        VALUES ?class { wd:Q839954 wd:Q15661340 wd:Q109607 wd:Q44613 wd:Q160742 wd:Q44539 wd:Q57821 wd:Q1081138 wd:Q486972 wd:Q3957 wd:Q532 wd:Q13410522 }
        ?item wdt:P31 ?class .
        OPTIONAL { ?item rdfs:label ?mnLabel . FILTER(LANG(?mnLabel) = "mn") }
        OPTIONAL { ?item wdt:P571 ?inception . }
        OPTIONAL { ?item wdt:P576 ?dissolved . }
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mn". }
      } LIMIT 15000
    """),
    ("wd_tw_all_hist_and_arch", """
      SELECT DISTINCT ?item ?itemLabel ?zhLabel ?coord ?classLabel ?inception ?heritageLabel WHERE {
        ?item wdt:P17 wd:Q865 ; wdt:P625 ?coord .
        {
          VALUES ?class { wd:Q839954 wd:Q15661340 wd:Q109607 wd:Q57821 wd:Q23413 wd:Q1081138 wd:Q44539 wd:Q486972 wd:Q532 wd:Q3957 }
          ?item wdt:P31 ?class .
        } UNION {
          ?item wdt:P1435 ?heritage .
        }
        OPTIONAL { ?item rdfs:label ?zhLabel . FILTER(LANG(?zhLabel) = "zh-hant" || LANG(?zhLabel) = "zh") }
        OPTIONAL { ?item wdt:P571 ?inception . }
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en,zh-hant,zh". }
      } LIMIT 15000
    """),
    ("wd_hk_mo_hist", """
      SELECT DISTINCT ?item ?itemLabel ?zhLabel ?coord ?classLabel ?inception WHERE {
        VALUES ?ctry { wd:Q8646 wd:Q14773 }
        ?item wdt:P17 ?ctry ; wdt:P625 ?coord .
        {
          VALUES ?class { wd:Q839954 wd:Q57821 wd:Q1081138 wd:Q532 wd:Q486972 wd:Q3957 wd:Q16748868 wd:Q44539 }
          ?item wdt:P31 ?class .
        } UNION {
          ?item wdt:P1435 ?h .
        }
        OPTIONAL { ?item rdfs:label ?zhLabel . FILTER(LANG(?zhLabel) = "zh-hant" || LANG(?zhLabel) = "zh") }
        OPTIONAL { ?item wdt:P571 ?inception . }
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en,zh-hant,zh". }
      } LIMIT 10000
    """),
  ]
  for tag, q in queries:
    outp = os.path.join(OUT_DIR, f"{tag}.json")
    if os.path.exists(outp) and os.path.getsize(outp) > 2000:
      print(f"  Already cached: {tag}", flush=True)
      continue
    r = safe_get(endpoint, arg1_params={"query": q, "format": "json"}, arg2_timeout=110, arg3_headers={"Accept": "application/sparql-results+json"})
    if r and r.status_code == 200:
      b = r.json().get("results", {}).get("bindings", [])
      with open(outp, "w", encoding="utf-8") as fh:
        json.dump(b, fh, ensure_ascii=False)
      print(f"  Wikidata {tag}: {len(b):,} rows", flush=True)
    else:
      print(f"  [WARN] Wikidata {tag} failed", flush=True)
    time.sleep(2.5)


def harvest_osm_overpass_jade():
  print("[6] Harvesting OpenStreetMap historic archaeological sites, forts, city gates, walled towns & monasteries across JADE...", flush=True)
  tiles = [
    ("mn_mongolia", 41.5, 87.5, 52.2, 120.0),
    ("cn_north_central", 32.0, 106.0, 41.5, 123.0),
    ("cn_yangtze_east", 26.5, 111.0, 32.0, 123.0),
    ("cn_south_hk_mo", 18.0, 106.0, 26.5, 119.5),
    ("cn_southwest_sichuan", 21.0, 97.0, 34.0, 111.0),
    ("cn_northwest_xinjiang_tibet", 27.0, 73.5, 49.5, 106.0),
    ("cn_northeast_manchuria", 38.5, 118.0, 53.6, 135.2),
    ("tw_taiwan", 21.8, 119.2, 25.5, 122.2),
  ]
  endpoints = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
  ]
  for tname, s, w, n, e in tiles:
    outp = os.path.join(OUT_DIR, f"osm_jade_{tname}.json")
    if os.path.exists(outp) and os.path.getsize(outp) > 2000:
      print(f"  Already cached: osm_jade_{tname}", flush=True)
      continue
    q = f"""
    [out:json][timeout:100];
    (
      node["historic"="archaeological_site"]({s},{w},{n},{e});
      way["historic"="archaeological_site"]({s},{w},{n},{e});
      node["historic"="city_gate"]({s},{w},{n},{e});
      node["historic"="fort"]({s},{w},{n},{e});
      way["historic"="fort"]({s},{w},{n},{e});
      node["historic"="castle"]({s},{w},{n},{e});
      way["historic"="castle"]({s},{w},{n},{e});
      node["historic"="monastery"]({s},{w},{n},{e});
      way["historic"="monastery"]({s},{w},{n},{e});
      node["historic"="ruins"]["name"]({s},{w},{n},{e});
    );
    out center tags;
    """
    ok = False
    for ep in endpoints:
      try:
        r = requests.post(ep, data={"data": q}, headers=HEADERS, timeout=120)
        if r.status_code == 200:
          els = r.json().get("elements", [])
          with open(outp, "w", encoding="utf-8") as fh:
            json.dump(els, fh, ensure_ascii=False)
          print(f"  OSM {tname}: {len(els):,} elements", flush=True)
          ok = True
          break
        else:
          print(f"  OSM {tname} via {ep}: HTTP {r.status_code}", flush=True)
      except Exception as ex:
        print(f"  OSM {tname} via {ep}: ERR {ex}", flush=True)
      time.sleep(5)
    if not ok:
      print(f"  [WARN] OSM {tname} failed on all mirrors", flush=True)
    time.sleep(3)


if __name__ == "__main__":
  harvest_cbdb()
  harvest_zenodo_records()
  harvest_depositar_taiwan()
  harvest_dataverse_city_walls()
  harvest_wikidata_jade()
  harvest_osm_overpass_jade()
  print("\n=== JADE HISTORICAL HARVEST COMPLETE ===", flush=True)
