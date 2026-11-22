"""Stage C Archaeological Harvester (Part 4): France Base Merimee (Ministere de la Culture)
+ France full INRAP CSV + Italy MiC/ICCD ArCo (exact a-loc:hasCoordinates SPARQL)
+ Belgium Flanders VIOE (axis-order-safe WFS).
"""

import csv
import io
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
HEADERS = {"User-Agent": "SVEA-OperationViscount-MAGNETIC/1.0 (academic historical demography)"}


def harvest_france_merimee_and_inrap():
  outp = os.path.join(RAW_DIR, "france_merimee_pop.json")
  if not (os.path.exists(outp) and os.path.getsize(outp) > 200000):
    print("[1] Downloading France Ministere de la Culture Base Merimee (POP S3)...", flush=True)
    r = requests.get("https://ministere-culture.s3.sbg.io.cloud.ovh.net/POP/merimee.csv", headers=HEADERS, timeout=180, stream=True)
    if r.status_code == 200:
      raw_bytes = r.content
      print(f"    Downloaded merimee.csv: {len(raw_bytes):,} B", flush=True)
      txt = raw_bytes.decode("utf-8", errors="replace")
      # Detect delimiter
      first_line = txt.splitlines()[0] if txt else ""
      delim = ";" if first_line.count(";") > first_line.count(",") else ","
      rows = []
      reader = csv.DictReader(io.StringIO(txt), delimiter=delim)
      for row in reader:
        # Look for WGS84 coordinates column (coordonnees_au_format_wgs84 or POP_COORDONNEES)
        cval = (
          row.get("POP_COORDONNEES") or row.get("coordonnees_au_format_wgs84")
          or row.get("Coordonnees_finales") or ""
        )
        m = re.search(r"([45]\d\.\d+)[,\s;]+([\-]?\d+\.\d+)", str(cval))
        if not m:
          continue
        lat, lon = float(m.group(1)), float(m.group(2))
        if not (41.3 <= lat <= 51.2 and -5.2 <= lon <= 9.6):
          continue
        siecle = str(row.get("SCLE") or row.get("Siecle_de_la_campagne_principale_de_construction") or "")
        tico = str(row.get("TICO") or row.get("Titre_editorial_de_la_notice") or "")
        deno = str(row.get("DENO") or row.get("Denomination_de_l_edifice") or "")
        # Keep strictly pre-1870 historic/archaeological monuments (exclude 20th c.)
        s_low = f"{siecle} {tico} {deno}".lower()
        if any(k in s_low for k in ("20e", "21e", "xxe", "xxie", "190", "191", "192", "193", "194", "195", "196", "197", "198", "199")):
          if not any(k in s_low for k in ("néolith", "mégalith", "dolmen", "menhir", "gallo", "romain", "antique", "moyen âge", "méroving", "caroling", "11e", "12e", "13e", "14e", "15e", "16e", "17e", "18e", "protohist", "âge du", "paléolith")):
            continue
        rows.append({
          "name": tico[:120],
          "type": deno[:80],
          "period": siecle[:100],
          "lat": round(lat, 5),
          "lon": round(lon, 5),
        })
      with open(outp, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False)
      print(f"  France Base Merimee pre-1870 monuments & arch sites: {len(rows):,}", flush=True)

  # Also full INRAP CSV
  inrap_out = os.path.join(RAW_DIR, "france_inrap_national.json")
  if not (os.path.exists(inrap_out) and os.path.getsize(inrap_out) > 20000):
    print("[2] Downloading France INRAP national excavations CSV...", flush=True)
    r = requests.get("https://static.data.gouv.fr/72/1f16b181f9711e5781ad01d9773d2de877051c1c5f68db2b4dfcd09e667e0c.csv", headers=HEADERS, timeout=60)
    if r.status_code == 200:
      txt = r.content.decode("utf-8", errors="replace")
      delim = ";" if (txt.splitlines()[0].count(";") > txt.splitlines()[0].count(",")) else ","
      rows = []
      for row in csv.DictReader(io.StringIO(txt), delimiter=delim):
        lat, lon = None, None
        for k, v in row.items():
          kl = (k or "").lower()
          if "lat" in kl and v:
            try: lat = float(str(v).replace(",", "."))
            except: pass
          elif ("lon" in kl or "lng" in kl) and v:
            try: lon = float(str(v).replace(",", "."))
            except: pass
        if lat is not None and lon is not None and 41.3 <= lat <= 51.2 and -5.2 <= lon <= 9.6:
          rows.append({
            "name": str(row.get("Nom du site") or row.get("Commune") or row.get("commune") or "")[:120],
            "period": str(row.get("Périodes") or row.get("Periodes") or row.get("periodes") or "")[:140],
            "type": str(row.get("Thèmes") or row.get("Themes") or row.get("themes") or "")[:120],
            "lat": round(lat, 5),
            "lon": round(lon, 5),
          })
      with open(inrap_out, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False)
      print(f"  France INRAP national excavations: {len(rows):,}", flush=True)


def harvest_italy_arco_fixed():
  outp = os.path.join(RAW_DIR, "italy_iccd_arco.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[3] Italy ArCo already cached: {outp}", flush=True)
    return
  print("[3] Harvesting Italy MiC/ICCD ArCo Archaeological Sites (a-loc:hasCoordinates)...", flush=True)
  # First find exact lat/lon predicate on a Geometry node
  q_p = """SELECT ?p ?o WHERE {
    <https://w3id.org/arco/resource/ArchaeologicalProperty/0900200455> <https://w3id.org/italia/onto/CLV/hasGeometry> ?g .
    ?g ?p ?o .
  } LIMIT 30"""
  r = requests.get("https://dati.beniculturali.it/sparql", params={"query": q_p, "format": "application/sparql-results+json"}, headers=HEADERS, timeout=30, verify=False)
  lat_pred, lon_pred, coord_pred = None, None, None
  if r.status_code == 200:
    for b in r.json().get("results", {}).get("bindings", []):
      p = b["p"]["value"]
      o = b["o"]["value"]
      if "lat" in p.lower():
        lat_pred = p
      elif "long" in p.lower() or "lon" in p.lower():
        lon_pred = p
      elif "coord" in p.lower() or "wkt" in p.lower() or "serialized" in p.lower():
        coord_pred = p
    print(f"    ArCo preds: lat={lat_pred} lon={lon_pred} coord={coord_pred}", flush=True)

  rows = []
  page_size = 5000
  for offset in range(0, 40000, page_size):
    if lat_pred and lon_pred:
      q = f"""
      PREFIX arco: <https://w3id.org/arco/ontology/arco/>
      PREFIX clv: <https://w3id.org/italia/onto/CLV/>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      SELECT ?s ?lbl ?lat ?lon WHERE {{
        ?s a arco:ArchaeologicalProperty ;
           rdfs:label ?lbl ;
           clv:hasGeometry ?g .
        ?g <{lat_pred}> ?lat ; <{lon_pred}> ?lon .
      }} LIMIT {page_size} OFFSET {offset}
      """
    elif coord_pred:
      q = f"""
      PREFIX arco: <https://w3id.org/arco/ontology/arco/>
      PREFIX clv: <https://w3id.org/italia/onto/CLV/>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      SELECT ?s ?lbl ?lat ?lon WHERE {{
        ?s a arco:ArchaeologicalProperty ;
           rdfs:label ?lbl ;
           clv:hasGeometry/<{coord_pred}> ?c .
        ?c <https://w3id.org/arco/ontology/location/lat> ?lat ;
           <https://w3id.org/arco/ontology/location/long> ?lon .
      }} LIMIT {page_size} OFFSET {offset}
      """
    else:
      q = f"""
      PREFIX arco: <https://w3id.org/arco/ontology/arco/>
      PREFIX clv: <https://w3id.org/italia/onto/CLV/>
      PREFIX a-loc: <https://w3id.org/arco/ontology/location/>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      SELECT ?s ?lbl ?lat ?lon WHERE {{
        ?s a arco:ArchaeologicalProperty ;
           rdfs:label ?lbl ;
           clv:hasGeometry/a-loc:hasCoordinates ?c .
        ?c a-loc:lat ?lat ; a-loc:long ?lon .
      }} LIMIT {page_size} OFFSET {offset}
      """
    try:
      r = requests.get(
        "https://dati.beniculturali.it/sparql",
        params={"query": q, "format": "application/sparql-results+json"},
        headers=HEADERS, timeout=60, verify=False
      )
      if r.status_code != 200:
        break
      bindings = r.json().get("results", {}).get("bindings", [])
    except Exception as e:
      print(f"    ArCo err at offset={offset}: {e}", flush=True)
      break
    if not bindings:
      break
    for b in bindings:
      try:
        lat = float(str(b["lat"]["value"]).replace(",", "."))
        lon = float(str(b["lon"]["value"]).replace(",", "."))
      except Exception:
        continue
      if 35.0 <= lat <= 47.5 and 6.0 <= lon <= 19.0:
        rows.append({
          "id": b["s"]["value"].rsplit("/", 1)[-1],
          "name": b["lbl"]["value"][:140],
          "lat": round(lat, 5),
          "lon": round(lon, 5),
        })
    print(f"    ArCo offset={offset} rows={len(rows):,}", flush=True)
    if len(bindings) < page_size:
      break
    time.sleep(0.4)
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Italy MiC/ICCD ArCo sites: {len(rows):,}", flush=True)


def harvest_belgium_flanders_fixed():
  outp = os.path.join(RAW_DIR, "belgium_flanders_vioe.json")
  print("[4] Harvesting Belgium Flanders VIOE (axis-order-safe WFS)...", flush=True)
  rows = []
  for layer in ("vioe_geoportaal:archeologisch_geheel", "vioe_geoportaal:bes_arch_site", "vioe_geoportaal:archeologisch_element"):
    start = 0
    while start < 15000:
      try:
        r = requests.get(
          "https://geo.onroerenderfgoed.be/geoserver/vioe_geoportaal/wfs",
          params={
            "service": "WFS", "version": "2.0.0", "request": "GetFeature",
            "typeNames": layer, "startIndex": start, "count": 2000,
            "outputFormat": "application/json", "srsName": "EPSG:4326",
          },
          headers=HEADERS, timeout=60
        )
        if r.status_code != 200:
          break
        feats = r.json().get("features") or []
      except Exception:
        break
      if not feats:
        break
      for f in feats:
        geom = f.get("geometry") or {}
        pts = []
        def walk(n):
          if isinstance(n, list) and len(n) >= 2 and isinstance(n[0], (int, float)):
            pts.append((float(n[0]), float(n[1])))
          elif isinstance(n, list):
            for c in n: walk(c)
        walk(geom.get("coordinates"))
        if not pts:
          continue
        a = sum(x[0] for x in pts) / len(pts)
        b = sum(x[1] for x in pts) / len(pts)
        # Auto-detect (lon, lat) vs (lat, lon)
        if 49.4 <= b <= 51.6 and 2.5 <= a <= 6.5:
          lat, lon = b, a
        elif 49.4 <= a <= 51.6 and 2.5 <= b <= 6.5:
          lat, lon = a, b
        else:
          continue
        p = f.get("properties") or {}
        rows.append({
          "name": str(p.get("naam") or p.get("beschrijving") or "")[:120],
          "dating": str(p.get("datering") or p.get("typering") or "")[:120],
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


if __name__ == "__main__":
  harvest_france_merimee_and_inrap()
  harvest_italy_arco_fixed()
  harvest_belgium_flanders_fixed()
  print("=== PART 4 COMPLETE ===", flush=True)
