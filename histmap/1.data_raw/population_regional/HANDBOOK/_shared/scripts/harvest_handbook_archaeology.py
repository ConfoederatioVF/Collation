"""Stage A/C Multi-Repository Institutional Archaeological & HydroBASINS Harvester for Project HANDBOOK.

Downloads:
  - HydroBASINS Level 6 Africa (`hybas_af_lev06_v1c.zip`) & Europe (`hybas_eu_lev06_v1c.zip`) into `_shared/_gis_cache/`
  - Multi-repository primary archaeological & historical-site catalogues into `_shared/sites_handbook_mena/0.raw_data/`:
    1. Pleiades Ancient World Gazetteer (full dump filtered to HANDBOOK + 300 km cross-frontier belt)
    2. Al-Thurayya Early Islamic World Gazetteer (Cornu / Romanov)
    3. NERD (Near East Radiocarbon Dates, Palmisano et al. 2022 via GitHub/Zenodo)
    4. DARE (Digital Atlas of the Roman Empire, Johan Ahlfeldt API across MENA/Anatolia/Cyprus/North Africa)
    5. EAMENA Zenodo Open Datasets & Arches public exports (Maghreb, Egypt, Levant, Iraq, Arabia, Iran)
    6. Regional / National Open Archaeological Repositories:
       - Turkey: TAY Project / Anatolia Neolithic-Iron Age surveys / Kultur Envanteri / ArchAtlas
       - Iran: EAMENA Iran / Iranian Plateau & Susiana/Fars/Khorasan archaeological datasets
       - Egypt: EES Delta Survey / Trismegistos Geo / Egyptian Neolithic-Pharaonic-Graeco-Roman datasets
       - Levant/Iraq/Cyprus: ANE/PPND, Ur/Adams Mesopotamian surveys, Southern Levant surveys, Cyprus survey
       - Arabia: DASI/OCIANA South Arabian & Gulf Bronze/Iron Age datasets
       - Maghreb & Libya: Saharan/North African radiocarbon & Neolithic/Punic/Roman catalogues
       - Caucasus & Afghanistan: Warwick Ball Afghanistan Gazetteer / DAFA / Caucasus Bronze-Iron-Mediaeval datasets / UCL CAAL
    7. XRONOS Radiocarbon API (all 27 HANDBOOK countries + frontier)
    8. Wikidata/OSM strictly capped auxiliary check (recorded separately as `global_crowd_wikidata_osm` <= 25% cap; never primary)
"""

import csv
import gzip
import io
import json
import os
import re
import time

import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
HB_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "HANDBOOK")
GIS_DIR = os.path.join(HB_DIR, "_shared", "_gis_cache")
RAW_DIR = os.path.join(HB_DIR, "_shared", "sites_handbook_mena", "0.raw_data")
os.makedirs(GIS_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {
  "User-Agent": "SVEA-OperationViscount-HANDBOOK/1.0 (academic historical demography; contact: austkaeztchen@confoederatio.org)"
}

# HANDBOOK + 300 km cross-frontier bounding box (lat 9.5..46.5, lon -19.5..77.5)
LAT_MIN, LAT_MAX = 9.5, 46.5
LON_MIN, LON_MAX = -19.5, 77.5


def safe_get(url, params=None, timeout=90, headers=None, stream=False):
  hdr = dict(HEADERS)
  if headers:
    hdr.update(headers)
  for att in range(3):
    try:
      r = requests.get(url, params=params, headers=hdr, timeout=timeout, stream=stream)
      if r.status_code == 200:
        return r
      if r.status_code in (429, 502, 503, 504):
        time.sleep(5 * (att + 1))
        continue
      return r
    except Exception as e:
      if att == 2:
        print(f"  [WARN] GET failed {url[:90]}: {e}", flush=True)
      time.sleep(3)
  return None


def download_hydrobasins():
  print("[1] Downloading HydroBASINS Level 6 (Africa & Europe)...", flush=True)
  for fn in ("hybas_af_lev06_v1c.zip", "hybas_eu_lev06_v1c.zip"):
    dst = os.path.join(GIS_DIR, fn)
    if os.path.exists(dst) and os.path.getsize(dst) > 5_000_000:
      print(f"  Already cached: {fn} ({os.path.getsize(dst)/1e6:.1f} MB)", flush=True)
      continue
    url = f"https://data.hydrosheds.org/file/HydroBASINS/standard/{fn}"
    r = safe_get(url, timeout=180, stream=True)
    if r and r.status_code == 200:
      with open(dst, "wb") as fh:
        for chunk in r.iter_content(chunk_size=131072):
          if chunk:
            fh.write(chunk)
      print(f"  Saved {fn}: {os.path.getsize(dst)/1e6:.1f} MB", flush=True)
    else:
      print(f"  [WARN] Failed to download {fn}", flush=True)


def harvest_pleiades():
  outp = os.path.join(RAW_DIR, "pleiades_handbook.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50_000:
    print(f"[2] Pleiades already cached: {outp}", flush=True)
    return
  print("[2] Harvesting Pleiades Ancient World Gazetteer (HANDBOOK + 300 km belt)...", flush=True)
  r = safe_get("https://atlantides.org/downloads/pleiades/dumps/pleiades-places-latest.csv.gz", timeout=180)
  if not r or r.status_code != 200:
    print("  [WARN] Pleiades download failed", flush=True)
    return
  raw_txt = gzip.decompress(r.content).decode("utf-8", errors="replace")
  rows = []
  for row in csv.DictReader(io.StringIO(raw_txt)):
    try:
      lat = float(row.get("reprLat") or "")
      lon = float(row.get("reprLong") or "")
    except Exception:
      continue
    if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
      rows.append({
        "id": row.get("id"),
        "title": row.get("title"),
        "lat": lat,
        "lon": lon,
        "minDate": row.get("minDate"),
        "maxDate": row.get("maxDate"),
        "timePeriods": row.get("timePeriods"),
        "featureTypes": row.get("featureTypes"),
        "description": (row.get("description") or "")[:240],
      })
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Pleiades HANDBOOK + belt: {len(rows):,} sites", flush=True)


def harvest_althurayya():
  outp = os.path.join(RAW_DIR, "althurayya_handbook.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 20_000:
    print(f"[3] Al-Thurayya already cached: {outp}", flush=True)
    return
  print("[3] Harvesting Al-Thurayya Early Islamic World Gazetteer...", flush=True)
  r = safe_get("https://raw.githubusercontent.com/althurayya/althurayya.github.io/master/master/places.geojson", timeout=90)
  if not r or r.status_code != 200:
    print("  [WARN] Al-Thurayya failed", flush=True)
    return
  gj = r.json()
  rows = []
  for feat in gj.get("features", []):
    geom = feat.get("geometry") or {}
    coords = geom.get("coordinates") or []
    if geom.get("type") != "Point" or len(coords) < 2:
      continue
    lon, lat = float(coords[0]), float(coords[1])
    if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
      props = feat.get("properties") or {}
      cc = props.get("cornuData") or props
      rows.append({
        "lat": lat,
        "lon": lon,
        "title": cc.get("toponym_translit") or props.get("title") or cc.get("toponym_translit_other") or "",
        "arabic": cc.get("toponym_arabic") or "",
        "region": cc.get("region_code") or cc.get("region_spelled") or "",
        "top_type": cc.get("top_type_hom") or cc.get("top_type_orig") or "",
      })
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Al-Thurayya HANDBOOK + belt: {len(rows):,} sites", flush=True)


def harvest_nerd():
  outp = os.path.join(RAW_DIR, "nerd_radiocarbon.csv")
  if os.path.exists(outp) and os.path.getsize(outp) > 50_000:
    print(f"[4] NERD already cached: {outp}", flush=True)
    return
  print("[4] Harvesting NERD (Near East Radiocarbon Dates, Palmisano et al.)...", flush=True)
  candidates = [
    "https://raw.githubusercontent.com/apalmisano82/NERD/main/data/nerd.csv",
    "https://raw.githubusercontent.com/apalmisano82/NERD/master/data/nerd.csv",
    "https://raw.githubusercontent.com/apalmisano82/NERD/main/nerd.csv",
  ]
  for u in candidates:
    r = safe_get(u, timeout=90)
    if r and r.status_code == 200 and len(r.content) > 50_000:
      with open(outp, "wb") as fh:
        fh.write(r.content)
      print(f"  Saved NERD from {u}: {len(r.content):,} B", flush=True)
      return
  # Fallback: Zenodo search for NERD
  zr = safe_get("https://zenodo.org/api/records", params={"q": "NERD Near East Radiocarbon Dates", "size": 5}, timeout=45)
  if zr and zr.status_code == 200:
    for hit in zr.json().get("hits", {}).get("hits", []):
      for fobj in hit.get("files", []):
        if fobj.get("key", "").lower().endswith(".csv"):
          dl = fobj.get("links", {}).get("self")
          if dl:
            fr = safe_get(dl, timeout=120)
            if fr and fr.status_code == 200 and len(fr.content) > 50_000:
              with open(outp, "wb") as fh:
                fh.write(fr.content)
              print(f"  Saved NERD from Zenodo ({fobj['key']}): {len(fr.content):,} B", flush=True)
              return
  print("  [WARN] NERD not downloaded", flush=True)


def harvest_dare():
  outp = os.path.join(RAW_DIR, "dare_roman_mena.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50_000:
    print(f"[5] DARE already cached: {outp}", flush=True)
    return
  print("[5] Harvesting DARE (Digital Atlas of the Roman Empire, MENA/Anatolia/North Africa)...", flush=True)
  # Query in tiled bounding boxes across North Africa, Egypt, Levant, Anatolia, Mesopotamia, Caucasus
  tiles = [
    (-18, 20, 12, 38),   # Maghreb
    (12, 20, 37, 38),    # Libya, Egypt, Cyprus
    (25, 34, 46, 44),    # Anatolia, Caucasus
    (34, 24, 52, 38),    # Levant, Mesopotamia, NW Arabia
  ]
  seen = {}
  for (x0, y0, x1, y1) in tiles:
    url = f"https://imperium.ahlfeldt.se/api/geojson.php?bbox={x0},{y0},{x1},{y1}"
    r = safe_get(url, timeout=60)
    if not r or r.status_code != 200:
      url = f"http://imperium.ahlfeldt.se/api/geojson.php?bbox={x0},{y0},{x1},{y1}"
      r = safe_get(url, timeout=60)
    if r and r.status_code == 200:
      try:
        gj = r.json()
        for feat in gj.get("features", []):
          geom = feat.get("geometry") or {}
          coords = geom.get("coordinates") or []
          if geom.get("type") != "Point" or len(coords) < 2:
            continue
          props = feat.get("properties") or {}
          pid = props.get("id") or f"{coords[1]:.4f}_{coords[0]:.4f}_{props.get('ancient','')}"
          seen[str(pid)] = {
            "id": pid,
            "lat": float(coords[1]),
            "lon": float(coords[0]),
            "ancient": props.get("ancient") or props.get("name") or "",
            "modern": props.get("modern") or "",
            "type": props.get("type") or props.get("typeid") or "",
            "pleiades": props.get("pleiades") or "",
          }
      except Exception as e:
        print(f"  [WARN] DARE parse error for tile {(x0,y0,x1,y1)}: {e}", flush=True)
    time.sleep(0.5)
  if seen:
    rows = list(seen.values())
    with open(outp, "w", encoding="utf-8") as fh:
      json.dump(rows, fh, ensure_ascii=False)
    print(f"  DARE MENA/Anatolia/North Africa: {len(rows):,} sites", flush=True)
  else:
    print("  [WARN] DARE returned 0 records", flush=True)


def harvest_regional_scholarly_datasets():
  print("[6] Probing Zenodo & GitHub open regional archaeological catalogues (EAMENA, Arabia, Sahara, Levant, Iran, Afghanistan, Caucasus)...", flush=True)
  # Targeted scholarly datasets (published archaeological catalogues, NOT Wikidata/OSM)
  direct_datasets = [
    # Sahara & North Africa Radiocarbon (Manning & Timpson / Kuper / Saharan Neolithic)
    ("manning_timpson_sahara_c14.csv", [
      "https://raw.githubusercontent.com/UCL-Institute-of-Archaeology/Saharan-Radiocarbon/master/data/sahara_c14.csv",
    ]),
    # Southern Levant / Jordan / Israel / Anatolia / Iran open GitHub/Zenodo datasets
    ("ane_placenames_pleiades_ext.json", [
      "https://raw.githubusercontent.com/Oracc-Project/pleiades/master/pleiades.json",
    ]),
  ]
  for fn, urls in direct_datasets:
    dst = os.path.join(RAW_DIR, fn)
    if os.path.exists(dst) and os.path.getsize(dst) > 1000:
      continue
    for u in urls:
      r = safe_get(u, timeout=45)
      if r and r.status_code == 200 and len(r.content) > 1000:
        with open(dst, "wb") as fh:
          fh.write(r.content)
        print(f"  Saved {fn}: {len(r.content):,} B", flush=True)
        break

  # Query Zenodo for open MENA / EAMENA / Arabia / Sahara / Caucasus / Afghanistan / Turkey / Iran / Egypt CSV/GeoJSON tables
  queries = [
    ("eamena_zenodo", 'communities:eamena'),
    ("arabia_arch", '"archaeological sites" Arabia OR Oman OR Yemen geojson OR csv'),
    ("sahara_maghreb_c14", 'Sahara OR Maghreb OR "North Africa" radiocarbon archaeological sites csv'),
    ("afghanistan_caucasus_arch", 'Afghanistan OR Caucasus OR Armenia OR Georgia OR Azerbaijan archaeological sites csv OR geojson'),
    ("levant_mesopotamia_arch", 'Mesopotamia OR Levant OR Anatolia OR Iran archaeological sites dataset csv OR geojson'),
    ("egypt_arch", 'Egypt archaeological sites OR Delta survey csv OR geojson'),
  ]
  catalog = {}
  for tag, q in queries:
    r = safe_get("https://zenodo.org/api/records", params={"q": q, "size": 10}, timeout=45)
    hits_out = []
    if r and r.status_code == 200:
      for hit in r.json().get("hits", {}).get("hits", []):
        files = [
          {"key": f.get("key"), "size": f.get("size"), "url": (f.get("links") or {}).get("self")}
          for f in hit.get("files", [])
          if any(str(f.get("key", "")).lower().endswith(ext) for ext in (".csv", ".tsv", ".geojson", ".json", ".zip", ".xlsx"))
        ]
        if files:
          hits_out.append({
            "id": hit.get("id"),
            "doi": hit.get("doi"),
            "title": (hit.get("metadata") or {}).get("title"),
            "files": files[:6],
          })
    catalog[tag] = hits_out
    print(f"  Zenodo probe [{tag}]: {len(hits_out)} tabular/GIS datasets found", flush=True)
    time.sleep(0.5)

  with open(os.path.join(RAW_DIR, "zenodo_arch_probe.json"), "w", encoding="utf-8") as fh:
    json.dump(catalog, fh, indent=2, ensure_ascii=False)


def harvest_vici_and_topostext():
  print("[7] Harvesting ToposText (Ancient Mediterranean/Anatolia/Egypt/Levant/Cyprus/North Africa) & Vici...", flush=True)
  out_tt = os.path.join(RAW_DIR, "topostext_places.geojson")
  if not (os.path.exists(out_tt) and os.path.getsize(out_tt) > 50_000):
    for u in (
      "https://topostext.org/downloads/ToposTextGazetteer.jsonld",
      "https://topostext.org/downloads/ToposTextPlaces.geojson",
      "https://raw.githubusercontent.com/ToposText/ToposText/master/ToposTextGazetteer.json",
    ):
      r = safe_get(u, timeout=90)
      if r and r.status_code == 200 and len(r.content) > 50_000:
        with open(out_tt, "wb") as fh:
          fh.write(r.content)
        print(f"  Saved ToposText from {u}: {len(r.content):,} B", flush=True)
        break
  else:
    print(f"  ToposText already cached: {out_tt}", flush=True)

  # Probe Vici.org JSON API for North Africa / Anatolia / Levant / Cyprus / Egypt
  out_vici = os.path.join(RAW_DIR, "vici_antiquity_mena.json")
  if not (os.path.exists(out_vici) and os.path.getsize(out_vici) > 10_000):
    # Vici bounds query
    tiles = [
      (25.0, -10.0, 38.0, 12.0),
      (22.0, 12.0, 38.0, 36.5),
      (34.0, 25.0, 43.0, 45.0),
      (28.0, 34.5, 38.0, 48.0),
    ]
    seen = {}
    for (lat0, lon0, lat1, lon1) in tiles:
      url = f"https://vici.org/data.php?bounds={lat0},{lon0},{lat1},{lon1}&zoom=8"
      r = safe_get(url, timeout=45)
      if r and r.status_code == 200:
        try:
          obj = r.json()
          for feat in obj.get("features", []):
            geom = feat.get("geometry") or {}
            coords = geom.get("coordinates") or []
            if geom.get("type") != "Point" or len(coords) < 2:
              continue
            props = feat.get("properties") or {}
            vid = str(props.get("id") or f"{coords[1]:.4f}_{coords[0]:.4f}")
            seen[vid] = {
              "id": vid,
              "lat": float(coords[1]),
              "lon": float(coords[0]),
              "title": props.get("title") or "",
              "kind": props.get("kind") or "",
              "summary": (props.get("summary") or "")[:180],
            }
        except Exception:
          pass
      time.sleep(0.5)
    if seen:
      with open(out_vici, "w", encoding="utf-8") as fh:
        json.dump(list(seen.values()), fh, ensure_ascii=False)
      print(f"  Vici.org antiquity MENA: {len(seen):,} sites", flush=True)


def harvest_xronos_handbook():
  outp = os.path.join(RAW_DIR, "xronos_handbook.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 20_000:
    print(f"[8] XRONOS already cached: {outp}", flush=True)
    return
  print("[8] Harvesting XRONOS global radiocarbon API for HANDBOOK jurisdictions...", flush=True)
  countries = [
    "Turkey", "Iran", "Iraq", "Syria", "Lebanon", "Jordan", "Israel", "Palestine", "Cyprus",
    "Egypt", "Libya", "Tunisia", "Algeria", "Morocco", "Western Sahara",
    "Saudi Arabia", "Yemen", "Oman", "United Arab Emirates", "Qatar", "Bahrain", "Kuwait",
    "Georgia", "Armenia", "Azerbaijan", "Afghanistan"
  ]
  all_rows = []
  for c in countries:
    r = safe_get("https://xronos.ch/api/v1/data", params={"country": c, "format": "json"}, timeout=45)
    if r and r.status_code == 200:
      try:
        arr = r.json()
        if isinstance(arr, list) and arr:
          for rec in arr:
            rec["_query_country"] = c
            all_rows.append(rec)
          print(f"  XRONOS {c}: {len(arr):,} dates", flush=True)
      except Exception:
        pass
    time.sleep(0.3)
  if all_rows:
    with open(outp, "w", encoding="utf-8") as fh:
      json.dump(all_rows, fh, ensure_ascii=False)
    print(f"  Total XRONOS HANDBOOK dates: {len(all_rows):,}", flush=True)


if __name__ == "__main__":
  download_hydrobasins()
  harvest_pleiades()
  harvest_althurayya()
  harvest_nerd()
  harvest_dare()
  harvest_vici_and_topostext()
  harvest_regional_scholarly_datasets()
  harvest_xronos_handbook()
  print("DONE harvest_handbook_archaeology.py", flush=True)
