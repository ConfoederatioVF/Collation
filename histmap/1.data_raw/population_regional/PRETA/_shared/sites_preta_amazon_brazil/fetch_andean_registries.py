"""Harvests official Peruvian, Colombian, Bolivian, Ecuadorian & Pan-Andean
archaeological registries and radiocarbon databases into
`PRETA/_shared/sites_preta_amazon_brazil/raw_sources/andean/`.

Sources harvested:
  1. Peru Ministry of Culture SIGDA ArcGIS REST Services (`sigda.cultura.gob.pe`):
     - `v_3/maps_delimitado/0` (10.999 delimited pre-Hispanic monuments)
     - `v_4/registrado_v4/0` (6.073 registered pre-Hispanic reference sites)
     - `v_4/declarados_v4/0` (5.890 declared pre-Hispanic heritage sites)
     - `v_4/pqn_v4/0` (5.379 Qhapaq Nan pre-Hispanic road/tambo features)
  2. Colombia ICANH Official Open Data (`datos.gov.co` `3kq2-tnay` Sitios Arqueologicos)
  3. PEOPLE 3000 Global Radiocarbon Database (`p3k14c-2022.06.zip`, Zenodo 6633635 —
     includes AndesC14, Bolivian C14, Riris, Goldberg, Gayo, Marsh, Bandy, Capriles)
  4. Wikidata SPARQL georeferenced archaeological sites across Bolivia, Peru, Ecuador, Colombia
"""

import csv
import io
import json
import math
import pathlib
import sys
import time
import zipfile
import requests
import urllib3

urllib3.disable_warnings()
sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = pathlib.Path(__file__).resolve().parent / "raw_sources/andean"
OUT_DIR.mkdir(parents=True, exist_ok=True)

S = requests.Session()
S.headers.update({"User-Agent": "ViscountPRETA/1.0"})


def geom_centroid(arg0_geom):
  """Extracts WGS84 (lon, lat) centroid from Esri JSON Point, Polyline, or Polygon."""
  if not isinstance(arg0_geom, dict):
    return None, None
  if "x" in arg0_geom and "y" in arg0_geom:
    return float(arg0_geom["x"]), float(arg0_geom["y"])
  pts = []
  for key in ("rings", "paths"):
    arr = arg0_geom.get(key)
    if isinstance(arr, list):
      for part in arr:
        if isinstance(part, list):
          for pt in part:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
              pts.append((float(pt[0]), float(pt[1])))
  if not pts:
    return None, None
  lon = sum(p[0] for p in pts) / len(pts)
  lat = sum(p[1] for p in pts) / len(pts)
  return lon, lat


def harvest_sigda_layer(arg0_svc_path, arg1_out_csv):
  """Downloads all features from a Peru SIGDA ArcGIS REST MapServer layer via objectid cursor pagination."""
  out_path = OUT_DIR / arg1_out_csv
  base_url = f"https://sigda.cultura.gob.pe/sigda/rest/services/{arg0_svc_path}/query"
  print(f"[SIGDA] Harvesting {arg0_svc_path} via objectid cursor pagination...", flush=True)

  rows = []
  last_oid = 0
  page_size = 500
  page_num = 0
  while True:
    feats = None
    cur_limit = page_size
    for attempt in range(4):
      try:
        res = S.get(base_url, params={
          "where": f"objectid > {last_oid}",
          "orderByFields": "objectid ASC",
          "outFields": "*",
          "returnGeometry": "true",
          "outSR": "4326",
          "resultRecordCount": str(cur_limit),
          "f": "json"
        }, timeout=45, verify=False)
        res.raise_for_status()
        data = res.json()
        if "error" in data:
          raise RuntimeError(str(data["error"]))
        feats = data.get("features") or []
        break
      except Exception as exc:
        cur_limit = max(50, cur_limit // 2)
        if attempt == 3:
          print(f"  [WARN] page {page_num} (oid>{last_oid}) failed: {exc}", flush=True)
        time.sleep(1.0)
    if not feats:
      break

    max_oid_in_page = last_oid
    for ft in feats:
      attrs = ft.get("attributes") or {}
      oid_val = attrs.get("objectid")
      if oid_val is None:
        oid_val = attrs.get("OBJECTID")
      if oid_val is not None:
        try:
          max_oid_in_page = max(max_oid_in_page, int(oid_val))
        except (TypeError, ValueError):
          pass
      lon, lat = geom_centroid(ft.get("geometry"))
      if lon is None or lat is None:
        continue
      if not (-20.0 <= lat <= 1.0 and -82.0 <= lon <= -68.0):
        continue
      name = (
        attrs.get("nomb_map") or attrs.get("nombre") or attrs.get("nombre_map") or
        attrs.get("tramnomb") or attrs.get("stranomb") or attrs.get("NOMBRE") or
        attrs.get("NOM_MAP") or attrs.get("cod_plano") or ""
      )
      dept = (
        attrs.get("dpto") or attrs.get("departamento") or attrs.get("dptonomb") or
        attrs.get("DEPARTAMENTO") or attrs.get("DPTO") or ""
      )
      prov = (
        attrs.get("prov") or attrs.get("provincia") or attrs.get("provnomb") or
        attrs.get("PROVINCIA") or attrs.get("PROV") or ""
      )
      dist = (
        attrs.get("distrito") or attrs.get("distnomb") or attrs.get("DISTRITO") or ""
      )
      clasif = (
        attrs.get("clas_map") or attrs.get("clasificac") or attrs.get("d_camclasv") or
        attrs.get("finalidad") or attrs.get("CLASIFICACION") or ""
      )
      rows.append({
        "source_layer": arg0_svc_path,
        "oid": oid_val if oid_val is not None else "",
        "name": str(name).strip(),
        "classification": str(clasif).strip(),
        "department": str(dept).strip(),
        "province": str(prov).strip(),
        "district": str(dist).strip(),
        "lat": round(lat, 6),
        "lon": round(lon, 6),
      })

    page_num += 1
    if page_num % 4 == 0:
      print(f"  -> {arg0_svc_path}: page {page_num}, rows={len(rows)}, last_oid={max_oid_in_page}", flush=True)
    if max_oid_in_page <= last_oid or len(feats) < page_size:
      break
    last_oid = max_oid_in_page

  with open(out_path, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["source_layer", "oid", "name", "classification", "department", "province", "district", "lat", "lon"])
    w.writeheader()
    w.writerows(rows)
  print(f"  [SAVED] {out_path.name}: {len(rows)} rows", flush=True)
  return len(rows)


def harvest_colombia_icanh():
  """Downloads official ICANH Colombia archaeological sites from datos.gov.co (3kq2-tnay)."""
  out_path = OUT_DIR / "colombia_icanh_sitios.json"
  all_rows = []
  offset = 0
  limit = 2000
  print("[ICANH] Harvesting Colombia Sitios Arqueologicos (3kq2-tnay)...", flush=True)
  while True:
    r = S.get("https://www.datos.gov.co/resource/3kq2-tnay.json", params={"$limit": limit, "$offset": offset}, timeout=30)
    if r.status_code != 200:
      print(f"  [WARN] HTTP {r.status_code}", flush=True)
      break
    batch = r.json()
    if not batch:
      break
    all_rows.extend(batch)
    offset += len(batch)
    if len(batch) < limit:
      break
  out_path.write_text(json.dumps(all_rows, ensure_ascii=False), encoding="utf-8")
  print(f"  [SAVED] {out_path.name}: {len(all_rows)} rows", flush=True)
  return len(all_rows)


def harvest_p3k14c_south_america():
  """Downloads Zenodo p3k14c-2022.06.zip and extracts all South American C14 records."""
  zip_path = OUT_DIR / "p3k14c_2022_06.zip"
  out_csv = OUT_DIR / "p3k14c_south_america.csv"
  if not zip_path.exists() or zip_path.stat().st_size < 10_000_000:
    print("[p3k14c] Downloading Zenodo record 6633635 (35.7 MB)...", flush=True)
    meta = S.get("https://zenodo.org/api/records/6633635", timeout=20).json()
    dl_url = meta["files"][0]["links"]["self"]
    with S.get(dl_url, stream=True, timeout=120) as r:
      r.raise_for_status()
      with open(zip_path, "wb") as f:
        for ch in r.iter_content(262144):
          f.write(ch)
    print(f"  -> Downloaded {zip_path.stat().st_size // 1024} kB", flush=True)

  sa_countries = {
    "peru", "bolivia", "ecuador", "colombia", "brazil", "paraguay", "chile",
    "argentina", "venezuela", "uruguay", "guyana", "suriname", "french guiana"
  }
  kept = []
  with zipfile.ZipFile(zip_path) as zf:
    csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    print("  -> CSVs inside p3k14c zip:", csv_names, flush=True)
    for cname in csv_names:
      with zf.open(cname) as f:
        txt = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
        reader = csv.DictReader(txt)
        for row in reader:
          ctry = str(row.get("Country") or row.get("country") or "").strip().lower()
          try:
            lat = float(row.get("Lat") or row.get("lat") or "nan")
            lon = float(row.get("Long") or row.get("Lon") or row.get("lon") or "nan")
          except ValueError:
            lat, lon = float("nan"), float("nan")
          in_sa = (ctry in sa_countries) or (
            math.isfinite(lat) and math.isfinite(lon) and -56.0 <= lat <= 13.0 and -82.0 <= lon <= -34.0
          )
          if in_sa and math.isfinite(lat) and math.isfinite(lon):
            kept.append({
              "source_file": cname,
              "site_name": (row.get("SiteName") or row.get("site_name") or "").strip(),
              "country": (row.get("Country") or row.get("country") or "").strip(),
              "province": (row.get("Province") or row.get("province") or "").strip(),
              "age_bp": row.get("Age") or row.get("age") or "",
              "error": row.get("Error") or row.get("error") or "",
              "source_db": row.get("Source") or row.get("source") or "",
              "lat": round(lat, 6),
              "lon": round(lon, 6),
            })
  with open(out_csv, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["source_file", "site_name", "country", "province", "age_bp", "error", "source_db", "lat", "lon"])
    w.writeheader()
    w.writerows(kept)
  print(f"  [SAVED] {out_csv.name}: {len(kept)} South American C14 rows", flush=True)
  return len(kept)


def harvest_wikidata_andean():
  """Queries Wikidata SPARQL for georeferenced archaeological sites in Bolivia, Peru, Ecuador, Colombia."""
  out_csv = OUT_DIR / "wikidata_andean_arch_sites.csv"
  countries = [
    ("Q750", "Bolivia"),
    ("Q419", "Peru"),
    ("Q736", "Ecuador"),
    ("Q739", "Colombia"),
  ]
  rows = []
  print("[Wikidata] Querying archaeological sites across BO, PE, EC, CO...", flush=True)
  for qid, cname in countries:
    sparql = f"""
    SELECT ?item ?itemLabel ?coord WHERE {{
      ?item wdt:P31/wdt:P279* wd:Q839954 .
      ?item wdt:P17 wd:{qid} .
      ?item wdt:P625 ?coord .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en" . }}
    }}
    """
    try:
      r = S.get("https://query.wikidata.org/sparql", params={"query": sparql, "format": "json"},
                headers={"Accept": "application/sparql-results+json", "User-Agent": "ViscountPRETA/1.0 (mailto:research@confoederatio.org)"},
                timeout=45)
      if r.status_code == 200:
        b = r.json().get("results", {}).get("bindings", [])
        cnt = 0
        for item in b:
          wkt = item.get("coord", {}).get("value", "")
          if wkt.startswith("Point(") and wkt.endswith(")"):
            parts = wkt[6:-1].split()
            if len(parts) == 2:
              lon, lat = float(parts[0]), float(parts[1])
              rows.append({
                "qid": item["item"]["value"].rsplit("/", 1)[-1],
                "name": item.get("itemLabel", {}).get("value", ""),
                "country": cname,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
              })
              cnt += 1
        print(f"  -> {cname}: {cnt} Wikidata archaeological sites", flush=True)
      else:
        print(f"  [WARN] Wikidata {cname} HTTP {r.status_code}", flush=True)
    except Exception as exc:
      print(f"  [WARN] Wikidata {cname} ERR: {exc}", flush=True)
    time.sleep(1.0)

  with open(out_csv, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["qid", "name", "country", "lat", "lon"])
    w.writeheader()
    w.writerows(rows)
  print(f"  [SAVED] {out_csv.name}: {len(rows)} rows", flush=True)
  return len(rows)


def main():
  harvest_sigda_layer("v_3/maps_delimitado/MapServer/0", "peru_sigda_maps_delimitado.csv")
  harvest_sigda_layer("v_4/registrado_v4/MapServer/0", "peru_sigda_registrado.csv")
  harvest_sigda_layer("v_4/declarados_v4/MapServer/0", "peru_sigda_declarados.csv")
  harvest_sigda_layer("v_4/pqn_v4/MapServer/0", "peru_sigda_qhapaq_nan.csv")
  harvest_colombia_icanh()
  harvest_p3k14c_south_america()
  harvest_wikidata_andean()
  print("=== ANDEAN ARCHAEOLOGICAL HARVEST COMPLETE ===", flush=True)


if __name__ == "__main__":
  main()
