"""Fast completion script for INDUS Wave 3 Zenodo & lightweight OSM Overpass tiles."""

import json
import os
import re
import time
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional",
  "INDUS", "_shared", "sites_indus_south_asia", "0.raw_data"
)
HEADERS = {"User-Agent": "SVEA-OperationViscount-INDUS/2.0 (academic research; contact: austkaeztchen@confoederatio.org)"}


def harvest_zenodo():
  print("[1] Harvesting Zenodo South Asia archaeological datasets (13627361 IAR Palaeolithic, 8329381 Sopara, plus search)...", flush=True)
  for rid in [13627361, 8329381]:
    try:
      r = requests.get(f"https://zenodo.org/api/records/{rid}", headers=HEADERS, timeout=25)
      if r.status_code != 200:
        print(f"  [WARN] Zenodo {rid} HTTP {r.status_code}", flush=True)
        continue
      for f in r.json().get("files", []):
        fn = f.get("key", "")
        if f.get("size", 0) > 40_000_000 or f.get("size", 0) < 200:
          continue
        if any(fn.lower().endswith(e) for e in (".csv", ".tsv", ".xlsx", ".xls", ".geojson", ".json", ".zip")):
          safe_fn = re.sub(r"[^A-Za-z0-9._-]+", "_", f"zenodo_{rid}_{fn}")
          outp = os.path.join(RAW_DIR, safe_fn)
          if os.path.exists(outp) and os.path.getsize(outp) > 200:
            continue
          dr = requests.get(f["links"]["self"], headers=HEADERS, timeout=60)
          if dr.status_code == 200:
            open(outp, "wb").write(dr.content)
            print(f"  [OK] {safe_fn} ({len(dr.content):,} B)", flush=True)
    except Exception as ex:
      print(f"  [ERR] Zenodo {rid}: {ex}", flush=True)


def harvest_osm_fast():
  print("[2] Harvesting remaining OSM South Asia tiles with fast node/way regex filter...", flush=True)
  tiles = [
    ("tile04_karnataka_telangana_ap", 11.5, 74.0, 19.5, 84.8),
    ("tile05_odisha_jharkhand_bihar", 19.0, 82.0, 27.5, 88.5),
    ("tile06_wb_bangladesh_ne_bhutan", 20.5, 88.0, 29.5, 97.5),
    ("tile07_up_uttarakhand_delhi", 24.0, 76.5, 31.5, 84.5),
    ("tile08_hp_jk_ladakh_punjab", 29.5, 73.5, 37.2, 80.5),
    ("tile09_tamilnadu_kerala", 7.8, 74.5, 13.8, 80.6),
    ("tile10_sri_lanka_maldives", -1.0, 72.0, 10.2, 82.5),
    ("tile11_pakistan_sindh_baloch", 23.5, 60.8, 30.5, 71.5),
    ("tile12_pakistan_punjab_kpk_gb", 30.0, 69.0, 37.2, 76.5),
  ]
  for tname, s, w, n, e in tiles:
    outp = os.path.join(RAW_DIR, f"osm_w3_{tname}.json")
    if os.path.exists(outp) and os.path.getsize(outp) > 2000:
      print(f"  [SKIP] {tname} cached", flush=True)
      continue
    q = f"""[out:json][timeout:30];
(
  node["historic"~"^(archaeological_site|fort|castle|ruins|palace|monastery|megalith|stepwell)$"]({s},{w},{n},{e});
  way["historic"~"^(archaeological_site|fort|castle)$"]({s},{w},{n},{e});
);
out center tags;"""
    for ep in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"):
      try:
        r = requests.post(ep, data={"data": q}, headers=HEADERS, timeout=40)
        if r.status_code == 200:
          els = r.json().get("elements", [])
          json.dump(els, open(outp, "w", encoding="utf-8"), ensure_ascii=False)
          print(f"  [OK] OSM {tname}: {len(els):,} elements", flush=True)
          break
        print(f"  [WARN] OSM {tname} HTTP {r.status_code}", flush=True)
      except Exception as ex:
        print(f"  [WARN] OSM {tname}: {str(ex)[:80]}", flush=True)
      time.sleep(3)
    time.sleep(2)


if __name__ == "__main__":
  harvest_zenodo()
  harvest_osm_fast()
  print("=== WAVE 3 FAST FINISH COMPLETE ===", flush=True)
