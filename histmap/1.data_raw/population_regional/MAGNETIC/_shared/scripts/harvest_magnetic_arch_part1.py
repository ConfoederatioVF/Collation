"""Stage C Archaeological Harvester (Part 1): Pan-European, Southern Europe,
Central Europe and Balkans Primary Institutional Registers for Project MAGNETIC.

Harvests into `_shared/sites_magnetic_europe/0.raw_data/`:
  1. Pleiades Ancient World Gazetteer (full European + 300 km frontier dump)
  2. DARE - Digital Atlas of the Roman Empire (Lund Univ., tiled zoom=11 across Europe + frontier)
  3. Italy MiC/ICCD ArCo Archaeological Knowledge Graph (geocoordinated sites + dating via SPARQL)
  4. Greece Chronique des Fouilles en ligne (EfA/BSA OAI-PMH)
  5. Czechia AMCR (Czech Academy of Sciences OAI-PMH archaeological sites)
  6. Poland NID Rejestr Zabytkow Archeologicznych (REST API + voivodeship/commune coords)
  7. Germany / Pan-Europe iDAI.gazetteer (DAI archaeological-site records)
  8. Romania / Balkans / Central / Southern European targeted primary registers & OpenArchaeo / Zenodo
"""

import csv
import gzip
import io
import json
import os
import re
import time
import urllib3
import xml.etree.ElementTree as ET

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


def harvest_pleiades():
  outp = os.path.join(RAW_DIR, "pleiades_europe.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[1] Pleiades cached: {outp}", flush=True)
    return
  print("[1] Harvesting Pleiades Ancient World Gazetteer (Europe + 300 km belt)...", flush=True)
  r = safe_get("https://atlantides.org/downloads/pleiades/dumps/pleiades-places-latest.csv.gz", arg2_timeout=150)
  if not r or r.status_code != 200:
    print("  [WARN] Pleiades download failed", flush=True)
    return
  txt = gzip.decompress(r.content).decode("utf-8", errors="replace")
  rows = []
  for row in csv.DictReader(io.StringIO(txt)):
    try:
      lat = float(row.get("reprLat") or "")
      lon = float(row.get("reprLong") or "")
    except Exception:
      continue
    if 26.0 <= lat <= 72.0 and -20.0 <= lon <= 38.0:
      rows.append({
        "id": row.get("id"),
        "title": row.get("title"),
        "lat": lat,
        "lon": lon,
        "minDate": row.get("minDate"),
        "maxDate": row.get("maxDate"),
        "timePeriods": row.get("timePeriods"),
        "featureTypes": row.get("featureTypes"),
        "description": (row.get("description") or "")[:200],
      })
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Pleiades Europe + frontier: {len(rows):,} sites", flush=True)


def harvest_dare():
  outp = os.path.join(RAW_DIR, "dare_roman_empire.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[2] DARE cached: {outp}", flush=True)
    return
  print("[2] Harvesting DARE (Digital Atlas of the Roman Empire, Lund Univ.)...", flush=True)
  seen = {}
  # Tile Europe + Mediterranean frontier (-11..35E, 34..60N) in 4x3 deg tiles at zoom=11
  for lon0 in range(-11, 35, 4):
    for lat0 in range(34, 60, 3):
      bbox = f"{lon0},{lat0},{lon0 + 4},{lat0 + 3}"
      r = safe_get(
        "http://imperium.ahlfeldt.se/api/geojson.php",
        arg1_params={"bbox": bbox, "zoom": "11"},
        arg2_timeout=35
      )
      if not r or r.status_code != 200:
        continue
      try:
        gj = r.json()
      except Exception:
        continue
      for feat in gj.get("features", []):
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if geom.get("type") != "Point" or len(coords) < 2:
          continue
        props = feat.get("properties") or {}
        fid = str(props.get("id") or f"{coords[0]:.4f}_{coords[1]:.4f}")
        if fid in seen:
          continue
        seen[fid] = {
          "id": fid,
          "name": props.get("name") or props.get("ancient") or "",
          "ancient": props.get("ancient") or "",
          "country": props.get("country") or "",
          "type": props.get("type") or "",
          "lat": float(coords[1]),
          "lon": float(coords[0]),
        }
      time.sleep(0.15)
  rows = list(seen.values())
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  DARE Roman & Late Antique Europe + belt: {len(rows):,} sites", flush=True)


def harvest_italy_arco():
  outp = os.path.join(RAW_DIR, "italy_iccd_arco.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[3] Italy ArCo cached: {outp}", flush=True)
    return
  print("[3] Harvesting Italy MiC/ICCD ArCo Archaeological Sites (SPARQL)...", flush=True)
  # Query geocoordinated ArchaeologicalProperty / ArchitecturalOrLandscapeHeritage with dating
  # Use geo:lat / geo:long (WGS84 standard in ArCo)
  rows = []
  page_size = 5000
  for offset in range(0, 45000, page_size):
    q = f"""
    PREFIX arco: <https://w3id.org/arco/ontology/arco/>
    PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX cd: <https://w3id.org/arco/ontology/context-description/>
    SELECT ?s ?lbl ?lat ?lon ?dt WHERE {{
      ?s a arco:ArchaeologicalProperty ;
         rdfs:label ?lbl ;
         geo:lat ?lat ;
         geo:long ?lon .
      OPTIONAL {{ ?s cd:hasDating/rdfs:label ?dt }}
    }} LIMIT {page_size} OFFSET {offset}
    """
    r = safe_get(
      "https://dati.beniculturali.it/sparql",
      arg1_params={"query": q, "format": "application/sparql-results+json"},
      arg2_timeout=70,
      arg4_verify=False
    )
    if not r or r.status_code != 200:
      break
    try:
      bindings = r.json().get("results", {}).get("bindings", [])
    except Exception:
      break
    if not bindings:
      break
    for b in bindings:
      try:
        lat = float(b["lat"]["value"])
        lon = float(b["lon"]["value"])
      except Exception:
        continue
      if 35.0 <= lat <= 47.5 and 6.0 <= lon <= 19.0:
        rows.append({
          "id": b["s"]["value"].rsplit("/", 1)[-1],
          "name": b["lbl"]["value"][:140],
          "lat": lat,
          "lon": lon,
          "dating": (b.get("dt") or {}).get("value", "")[:120],
        })
    print(f"    ArCo offset={offset} fetched={len(bindings)} total={len(rows)}", flush=True)
    if len(bindings) < page_size:
      break
    time.sleep(0.5)
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Italy ICCD ArCo geocoordinated archaeological sites: {len(rows):,}", flush=True)


def harvest_idai_gazetteer():
  outp = os.path.join(RAW_DIR, "idai_gazetteer_europe.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[4] iDAI.gazetteer cached: {outp}", flush=True)
    return
  print("[4] Harvesting German Archaeological Institute (iDAI.gazetteer) across Europe...", flush=True)
  seen = {}
  # Query by type & bounding-box/keyword slices for Central, Southern, Western, Balkan Europe
  queries = [
    "types:archaeological-site",
    "types:archaeological-area",
    "types:populated-place",
    "types:building-institution",
  ]
  for q in queries:
    for offset in range(0, 10000, 1000):
      r = safe_get(
        "https://gazetteer.dainst.org/search.json",
        arg1_params={"q": q, "offset": offset, "limit": 1000},
        arg2_timeout=45
      )
      if not r or r.status_code != 200:
        break
      try:
        res = r.json().get("result") or []
      except Exception:
        break
      if not res:
        break
      for it in res:
        loc = it.get("prefLocation") or {}
        coords = loc.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
          continue
        try:
          lon, lat = float(coords[0]), float(coords[1])
        except Exception:
          continue
        if not (34.0 <= lat <= 71.0 and -11.0 <= lon <= 33.0):
          continue
        gid = str(it.get("gazId") or it.get("@id") or "")
        if gid in seen:
          continue
        pname = (it.get("prefName") or {}).get("title") or ""
        types = it.get("types") or []
        seen[gid] = {
          "id": gid,
          "name": pname[:140],
          "lat": lat,
          "lon": lon,
          "types": types,
          "tags": it.get("tags") or [],
        }
      if len(res) < 1000:
        break
      time.sleep(0.3)
  rows = list(seen.values())
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  iDAI.gazetteer Europe sites: {len(rows):,}", flush=True)


def harvest_poland_nid():
  outp = os.path.join(RAW_DIR, "poland_nid_zra.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[5] Poland NID ZRA cached: {outp}", flush=True)
    return
  print("[5] Harvesting Poland NID Rejestr Zabytkow Archeologicznych (REST API)...", flush=True)
  rows = []
  take = 500
  for skip in range(0, 15000, take):
    r = safe_get(
      "https://api.zabytek.gov.pl/nidrestapi/api/data/geoportal/otwarteDaneZestawienieZra",
      arg1_params={"format": "json", "skip": skip, "take": take},
      arg2_timeout=40
    )
    if not r or r.status_code != 200:
      break
    try:
      data = r.json().get("data") or []
    except Exception:
      break
    if not data:
      break
    rows.extend(data)
    if len(data) < take:
      break
    time.sleep(0.2)
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Poland NID ZRA archaeological records: {len(rows):,}", flush=True)


def harvest_greece_chronique():
  outp = os.path.join(RAW_DIR, "greece_chronique_efa.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[6] Greece Chronique cached: {outp}", flush=True)
    return
  print("[6] Harvesting Greece Chronique des Fouilles en ligne (EfA/BSA OAI-PMH)...", flush=True)
  rows = []
  token = None
  ns_oai = "{http://www.openarchives.org/OAI/2.0/}"
  ns_dc = "{http://purl.org/dc/elements/1.1/}"
  for page in range(120):
    params = {"verb": "ListRecords", "resumptionToken": token} if token else {"verb": "ListRecords", "metadataPrefix": "oai_dc"}
    r = safe_get("https://chronique.efa.gr/oai_pmh.php", arg1_params=params, arg2_timeout=45, arg4_verify=False)
    if not r or r.status_code != 200:
      break
    try:
      root = ET.fromstring(r.content)
    except Exception:
      break
    recs = root.findall(f".//{ns_oai}record")
    for rec in recs:
      titles = [e.text.strip() for e in rec.findall(f".//{ns_dc}title") if e.text]
      covs = [e.text.strip() for e in rec.findall(f".//{ns_dc}coverage") if e.text]
      subjs = [e.text.strip() for e in rec.findall(f".//{ns_dc}subject") if e.text]
      lat, lon = None, None
      for c in covs:
        m = re.search(r"([34]\d\.\d+)[,\s;]+([12]\d\.\d+)", c)
        if m:
          lat, lon = float(m.group(1)), float(m.group(2))
          break
      if lat is not None and 34.5 <= lat <= 42.0 and 19.0 <= lon <= 29.8:
        rows.append({
          "title": " ".join(titles)[:160],
          "lat": lat,
          "lon": lon,
          "subjects": " | ".join(subjs)[:200],
          "coverage": " | ".join(covs)[:200],
        })
    rt = root.find(f".//{ns_oai}resumptionToken")
    if rt is None or not (rt.text and rt.text.strip()):
      break
    token = rt.text.strip()
    if page % 10 == 0:
      print(f"    Chronique page={page} georef_rows={len(rows)}", flush=True)
    time.sleep(0.2)
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Greece Chronique des Fouilles geocoordinated records: {len(rows):,}", flush=True)


def harvest_cz_amcr():
  outp = os.path.join(RAW_DIR, "czechia_amcr_oai.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[7] Czechia AMCR cached: {outp}", flush=True)
    return
  print("[7] Harvesting Czechia AMCR (Czech Academy of Sciences OAI-PMH, set=lokalita/akce)...", flush=True)
  # First inspect available sets from ListSets
  r = safe_get("https://api.aiscr.cz/oai", arg1_params={"verb": "ListSets"}, arg2_timeout=30)
  target_set = None
  if r and r.status_code == 200:
    specs = re.findall(r"<setSpec>([^<]+)</setSpec>", r.text)
    print(f"    AMCR sets sample: {specs[:12]}", flush=True)
    for pref in ("lokalita", "pian", "projekt", "akce"):
      hit = next((s for s in specs if pref in s.lower()), None)
      if hit:
        target_set = hit
        break
  rows = []
  token = None
  for page in range(60):
    params = {"verb": "ListRecords", "resumptionToken": token} if token else {"verb": "ListRecords", "metadataPrefix": "oai_amcr"}
    if not token and target_set:
      params["set"] = target_set
    r = safe_get("https://api.aiscr.cz/oai", arg1_params=params, arg2_timeout=45)
    if not r or r.status_code != 200 or "<error " in r.text[:400]:
      if not token and params.get("metadataPrefix") == "oai_amcr":
        params["metadataPrefix"] = "oai_dc"
        r = safe_get("https://api.aiscr.cz/oai", arg1_params=params, arg2_timeout=45)
      if not r or r.status_code != 200:
        break
    txt = r.text
    # Fast regex extraction of WGS84 POINT(lon lat) and period/dating tokens
    for rec_blk in re.findall(r"<record>.*?</record>", txt, flags=re.S):
      m_pt = re.search(r"POINT\s*\(\s*([0-9.\-]+)\s+([0-9.\-]+)\s*\)", rec_blk)
      if not m_pt:
        m_lat = re.search(r"<[^>]*geom_sjtsk_y[^>]*>([0-9.\-]+)</", rec_blk)
        continue
      lon, lat = float(m_pt.group(1)), float(m_pt.group(2))
      if not (48.4 <= lat <= 51.2 and 12.0 <= lon <= 19.0):
        continue
      obs = re.findall(r"<[^>]*obdobi[^>]*>([^<]+)</", rec_blk)
      areal = re.findall(r"<[^>]*areal[^>]*>([^<]+)</", rec_blk)
      kat = re.findall(r"<[^>]*katastr[^>]*>([^<]+)</", rec_blk)
      rows.append({
        "lat": lat,
        "lon": lon,
        "obdobi": " | ".join(obs[:6]),
        "areal": " | ".join(areal[:4]),
        "katastr": kat[0] if kat else "",
      })
    m_rt = re.search(r"<resumptionToken[^>]*>([^<]+)</resumptionToken>", txt)
    if not m_rt:
      break
    token = m_rt.group(1).strip()
    if page % 10 == 0:
      print(f"    AMCR page={page} rows={len(rows)}", flush=True)
    time.sleep(0.2)
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Czechia AMCR georeferenced records: {len(rows):,}", flush=True)


def main():
  harvest_pleiades()
  harvest_dare()
  harvest_italy_arco()
  harvest_idai_gazetteer()
  harvest_poland_nid()
  harvest_greece_chronique()
  harvest_cz_amcr()
  print("=== PART 1 HARVEST COMPLETE ===", flush=True)


if __name__ == "__main__":
  main()
