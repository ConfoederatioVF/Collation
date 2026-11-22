"""Stage C Archaeological Harvester (Part 2): Western Europe & Northern Europe
Primary National Registers for Project MAGNETIC.

Harvests into `_shared/sites_magnetic_europe/0.raw_data/`:
  1. Historic England NHLE Scheduled Monuments (ArcGIS REST, ~20,006 sites, WGS84)
  2. Ireland National Monuments Service SMR (ArcGIS REST, paginated full ~151,308 sites, WGS84)
  3. France INRAP Sites de Fouilles Archeologiques (direct GeoJSON export)
  4. Belgium Flanders VIOE Inventaris Onroerend Erfgoed (WFS GeoJSON)
  5. Netherlands RCE Cultural Heritage Agency (SPARQL geocoordinated ArcheologischComplex)
  6. Denmark Slots- og Kulturstyrelsen Fund og Fortidsminder (WFS GeoJSON, fredet + ikkefredet)
  7. Finland Museovirasto Muinaisjaannosrekisteri (WFS GeoJSON, WGS84)
  8. Sweden Riksantikvarieambetet Fornsok (direct national GeoPackage `lamningar_sverige.gpkg`)
"""

import json
import os
import re
import time
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional",
  "MAGNETIC", "_shared", "sites_magnetic_europe", "0.raw_data"
)
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {
  "User-Agent": "SVEA-OperationViscount-MAGNETIC/1.0 (academic historical demography; contact: austkaeztchen@confoederatio.org)"
}


def safe_get(arg0_url, arg1_params=None, arg2_timeout=60, arg3_headers=None, arg4_verify=True):
  hdr = dict(HEADERS)
  if arg3_headers:
    hdr.update(arg3_headers)
  for att in range(3):
    try:
      r = requests.get(arg0_url, params=arg1_params, headers=hdr, timeout=arg2_timeout, verify=arg4_verify)
      if r.status_code == 200:
        return r
      if r.status_code in (429, 500, 502, 503, 504):
        time.sleep(4 * (att + 1))
        continue
      return r
    except Exception as e:
      if att == 2:
        print(f"  [WARN] GET failed {arg0_url[:80]}: {e}", flush=True)
      time.sleep(3)
  return None


def geom_centroid(arg0_geom):
  if not isinstance(arg0_geom, dict):
    return None, None
  gt = arg0_geom.get("type")
  co = arg0_geom.get("coordinates")
  if not co:
    return None, None
  if gt == "Point" and len(co) >= 2:
    return float(co[1]), float(co[0])
  pts = []
  def walk(node):
    if isinstance(node, list) and len(node) >= 2 and isinstance(node[0], (int, float)):
      pts.append((float(node[1]), float(node[0])))
    elif isinstance(node, list):
      for c in node:
        walk(c)
  walk(co)
  if not pts:
    return None, None
  return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def harvest_historic_england():
  outp = os.path.join(RAW_DIR, "uk_historic_england_sm.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[1] Historic England cached: {outp}", flush=True)
    return
  print("[1] Harvesting Historic England NHLE Scheduled Monuments (~20,006 sites)...", flush=True)
  base = "https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/National_Heritage_List_for_England_NHLE_v02_VIEW/FeatureServer/6/query"
  rows = []
  offset = 0
  while True:
    r = safe_get(
      base,
      arg1_params={
        "where": "1=1",
        "outFields": "OBJECTID,ListEntry,Name,area_ha",
        "outSR": "4326",
        "returnCentroid": "true",
        "returnGeometry": "true",
        "geometryPrecision": "4",
        "resultOffset": offset,
        "resultRecordCount": 2000,
        "f": "json",
      },
      arg2_timeout=60
    )
    if not r or r.status_code != 200:
      break
    d = r.json()
    feats = d.get("features") or []
    if not feats:
      break
    for f in feats:
      attr = f.get("attributes") or {}
      cent = f.get("centroid") or {}
      lat, lon = cent.get("y"), cent.get("x")
      if lat is None or lon is None:
        rings = (f.get("geometry") or {}).get("rings") or []
        if rings and rings[0]:
          lon = sum(p[0] for p in rings[0]) / len(rings[0])
          lat = sum(p[1] for p in rings[0]) / len(rings[0])
      if lat is not None and lon is not None and 49.5 <= float(lat) <= 56.0 and -6.5 <= float(lon) <= 2.2:
        rows.append({
          "id": attr.get("ListEntry") or attr.get("OBJECTID"),
          "name": (attr.get("Name") or "")[:160],
          "lat": round(float(lat), 5),
          "lon": round(float(lon), 5),
        })
    offset += len(feats)
    if len(feats) < 2000 and not d.get("exceededTransferLimit"):
      break
    time.sleep(0.2)
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Historic England Scheduled Monuments: {len(rows):,}", flush=True)


def harvest_ireland_smr():
  outp = os.path.join(RAW_DIR, "ireland_nms_smr.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 200000:
    print(f"[2] Ireland SMR cached: {outp}", flush=True)
    return
  print("[2] Harvesting Ireland National Monuments Service SMR (~151k records, geometryless LATITUDE/LONGITUDE fast pull)...", flush=True)
  base = "https://services-eu1.arcgis.com/HyjXgkV6KGMSF3jt/arcgis/rest/services/SMROpenData/FeatureServer/0/query"
  rows = []
  last_oid = 0
  while True:
    r = safe_get(
      base,
      arg1_params={
        "where": f"OBJECTID>{last_oid}",
        "orderByFields": "OBJECTID ASC",
        "outFields": "OBJECTID,ENTITY_ID,COUNTY,TOWNLAND,LONGITUDE,LATITUDE,MONUMENT_CLASS",
        "returnGeometry": "false",
        "resultRecordCount": 2000,
        "f": "json",
      },
      arg2_timeout=60
    )
    if not r or r.status_code != 200:
      break
    d = r.json()
    feats = d.get("features") or []
    if not feats:
      break
    for f in feats:
      a = f.get("attributes") or {}
      oid = int(a.get("OBJECTID") or 0)
      if oid > last_oid:
        last_oid = oid
      try:
        lat = float(a.get("LATITUDE"))
        lon = float(a.get("LONGITUDE"))
      except Exception:
        continue
      if 51.3 <= lat <= 55.5 and -10.8 <= lon <= -5.8:
        rows.append({
          "id": a.get("ENTITY_ID"),
          "cls": (a.get("MONUMENT_CLASS") or "")[:80],
          "county": a.get("COUNTY") or "",
          "lat": round(lat, 5),
          "lon": round(lon, 5),
        })
    if len(rows) % 20000 < 2000:
      print(f"    Ireland SMR progress: {len(rows):,} (last_oid={last_oid})", flush=True)
    if len(feats) < 2000 and not d.get("exceededTransferLimit"):
      break
    time.sleep(0.1)
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Ireland NMS SMR monuments: {len(rows):,}", flush=True)


def harvest_france_inrap():
  outp = os.path.join(RAW_DIR, "france_inrap_sites.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[3] France INRAP cached: {outp}", flush=True)
    return
  print("[3] Harvesting France INRAP Sites de Fouilles Archeologiques...", flush=True)
  r = safe_get(
    "https://data.iledefrance.fr/api/explore/v2.1/catalog/datasets/localisation-des-sites-de-fouille-archeologiques-de-linrap/exports/geojson",
    arg2_timeout=90
  )
  rows = []
  if r and r.status_code == 200:
    gj = r.json()
    for f in gj.get("features", []):
      lat, lon = geom_centroid(f.get("geometry"))
      if lat is None or not (41.3 <= lat <= 51.2 and -5.2 <= lon <= 9.6):
        continue
      p = f.get("properties") or {}
      rows.append({
        "name": (p.get("nom_du_site") or p.get("commune") or "")[:140],
        "period": str(p.get("periodes") or p.get("periode") or "")[:160],
        "type": str(p.get("themes") or p.get("type_de_site") or "")[:140],
        "lat": round(lat, 5),
        "lon": round(lon, 5),
      })
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  France INRAP archaeological excavations: {len(rows):,}", flush=True)


def harvest_belgium_flanders():
  outp = os.path.join(RAW_DIR, "belgium_flanders_vioe.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[4] Belgium Flanders cached: {outp}", flush=True)
    return
  print("[4] Harvesting Belgium Flanders VIOE Onroerend Erfgoed (WFS)...", flush=True)
  rows = []
  for layer in ("vioe_geoportaal:archeologisch_geheel", "vioe_geoportaal:bes_arch_site", "vioe_geoportaal:archeologisch_element"):
    start = 0
    while start < 20000:
      r = safe_get(
        "https://geo.onroerenderfgoed.be/geoserver/vioe_geoportaal/wfs",
        arg1_params={
          "service": "WFS",
          "version": "2.0.0",
          "request": "GetFeature",
          "typeNames": layer,
          "startIndex": start,
          "count": 2000,
          "outputFormat": "application/json",
          "srsName": "EPSG:4326",
        },
        arg2_timeout=60
      )
      if not r or r.status_code != 200:
        break
      try:
        feats = r.json().get("features") or []
      except Exception:
        break
      if not feats:
        break
      for f in feats:
        lat, lon = geom_centroid(f.get("geometry"))
        if lat is None or not (49.4 <= lat <= 51.6 and 2.5 <= lon <= 6.5):
          continue
        p = f.get("properties") or {}
        rows.append({
          "name": str(p.get("naam") or p.get("beschrijving") or "")[:140],
          "dating": str(p.get("datering") or p.get("typering") or "")[:140],
          "lat": round(lat, 5),
          "lon": round(lon, 5),
        })
      start += len(feats)
      if len(feats) < 2000:
        break
      time.sleep(0.2)
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Belgium Flanders VIOE sites: {len(rows):,}", flush=True)


def harvest_finland_museovirasto():
  outp = os.path.join(RAW_DIR, "finland_museovirasto.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[5] Finland Museovirasto cached: {outp}", flush=True)
    return
  print("[5] Harvesting Finland Museovirasto Muinaisjaannosrekisteri (WFS)...", flush=True)
  rows = []
  start = 0
  while start < 60000:
    r = safe_get(
      "https://geoserver.museovirasto.fi/geoserver/rajapinta_suojellut/wfs",
      arg1_params={
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": "rajapinta_suojellut:muinaisjaannos_piste",
        "startIndex": start,
        "count": 3000,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
      },
      arg2_timeout=70
    )
    if not r or r.status_code != 200:
      break
    try:
      feats = r.json().get("features") or []
    except Exception:
      break
    if not feats:
      break
    for f in feats:
      lat, lon = geom_centroid(f.get("geometry"))
      if lat is None or not (59.5 <= lat <= 70.2 and 19.0 <= lon <= 31.8):
        continue
      p = f.get("properties") or {}
      rows.append({
        "name": str(p.get("kohdenimi") or "").strip()[:120],
        "dating": str(p.get("ajoitus") or p.get("Ajoitus") or "").strip()[:120],
        "type": str(p.get("tyyppi") or p.get("Tyyppi") or p.get("Laji") or "").strip()[:120],
        "lat": round(lat, 5),
        "lon": round(lon, 5),
      })
    start += len(feats)
    print(f"    Finland progress: {len(rows):,}", flush=True)
    if len(feats) < 3000:
      break
    time.sleep(0.2)
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Finland Museovirasto ancient monuments: {len(rows):,}", flush=True)


def harvest_denmark_ff():
  outp = os.path.join(RAW_DIR, "denmark_fund_og_fortidsminder.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[6] Denmark FF cached: {outp}", flush=True)
    return
  print("[6] Harvesting Denmark Fund og Fortidsminder (WFS fredet + ikkefredet)...", flush=True)
  rows = []
  for layer, cap in [
    ("public:fundogfortidsminder_punkt_fredet", 40000),
    ("public:fundogfortidsminder_punkt_ikkefredet", 40000),
  ]:
    start = 0
    while start < cap:
      r = safe_get(
        "https://www.kulturarv.dk/ffgeoserver/public/wfs",
        arg1_params={
          "service": "WFS",
          "version": "2.0.0",
          "request": "GetFeature",
          "typeNames": layer,
          "startIndex": start,
          "count": 4000,
          "outputFormat": "application/json",
          "srsName": "EPSG:4326",
        },
        arg2_timeout=75,
        arg4_verify=False
      )
      if not r or r.status_code != 200:
        break
      try:
        feats = r.json().get("features") or []
      except Exception:
        break
      if not feats:
        break
      for f in feats:
        lat, lon = geom_centroid(f.get("geometry"))
        if lat is None or not (54.4 <= lat <= 57.9 and 7.8 <= lon <= 15.4):
          continue
        p = f.get("properties") or {}
        rows.append({
          "type": str(p.get("anlaegstype") or "")[:100],
          "dating": str(p.get("datering") or "")[:100],
          "lat": round(lat, 5),
          "lon": round(lon, 5),
        })
      start += len(feats)
      print(f"    Denmark {layer.split('_')[-1]} progress: {len(rows):,}", flush=True)
      if len(feats) < 4000:
        break
      time.sleep(0.2)
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Denmark Fund og Fortidsminder sites: {len(rows):,}", flush=True)


def harvest_sweden_raa_gpkg():
  outp = os.path.join(RAW_DIR, "lamningar_sverige.gpkg")
  if os.path.exists(outp) and os.path.getsize(outp) > 50_000_000:
    print(f"[7] Sweden RAA GeoPackage cached: {outp} ({os.path.getsize(outp):,} B)", flush=True)
    return
  print("[7] Downloading Sweden RAA Fornsok national GeoPackage (lamningar_sverige.gpkg)...", flush=True)
  url = "https://pub.raa.se/nedladdning/datauttag/lamningar_v1/l%c3%a4mningar_sverige.gpkg"
  try:
    with requests.get(url, headers=HEADERS, timeout=300, stream=True) as r:
      if r.status_code != 200:
        print(f"  [WARN] Sweden RAA status={r.status_code}", flush=True)
        return
      tmp = outp + ".part"
      tot = 0
      with open(tmp, "wb") as fh:
        for ch in r.iter_content(1024 * 512):
          if ch:
            fh.write(ch)
            tot += len(ch)
      os.replace(tmp, outp)
      print(f"  Sweden RAA GeoPackage downloaded: {tot:,} B", flush=True)
  except Exception as e:
    print(f"  [WARN] Sweden RAA download error: {e}", flush=True)


def main():
  harvest_historic_england()
  harvest_france_inrap()
  harvest_belgium_flanders()
  harvest_finland_museovirasto()
  harvest_denmark_ff()
  harvest_ireland_smr()
  harvest_sweden_raa_gpkg()
  print("=== PART 2 HARVEST COMPLETE ===", flush=True)


if __name__ == "__main__":
  main()
