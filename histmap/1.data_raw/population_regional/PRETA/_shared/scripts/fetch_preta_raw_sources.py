"""Downloads primary archaeological, Terra Preta (ADE), GeoNames, and official
national census raw datasets for Operation Viscount Project PRETA.
"""

import io
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib3
import zipfile
import requests

urllib3.disable_warnings()
sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OperationViscount/PRETA/1.0"}
PRETA_DIR = pathlib.Path(__file__).resolve().parents[2]
RAW_ARCH = PRETA_DIR / "_shared/sites_preta_amazon_brazil/raw_sources"
RAW_CENSUS = PRETA_DIR / "_shared/census_ingest"
RAW_ARCH.mkdir(parents=True, exist_ok=True)
RAW_CENSUS.mkdir(parents=True, exist_ok=True)


def fetch_file(arg0_url, arg1_out_path, arg2_verify=True, arg3_timeout=120):
  """Downloads a single URL to disk if not already present and non-empty."""
  out_p = pathlib.Path(arg1_out_path)
  if out_p.exists() and out_p.stat().st_size > 100:
    print(f"  [SKIP] {out_p.name} ({out_p.stat().st_size:,} B)")
    return True
  try:
    r = requests.get(arg0_url, headers=HEADERS, timeout=arg3_timeout, verify=arg2_verify)
    if r.status_code == 200 and len(r.content) > 50:
      out_p.write_bytes(r.content)
      print(f"  [OK] {out_p.name} ({len(r.content):,} B)")
      return True
    print(f"  [FAIL {r.status_code}] {arg0_url}")
    return False
  except Exception as exc:
    print(f"  [ERR] {arg0_url}: {exc}")
    return False


def fetch_iphan_sicg_wfs():
  """Fetches full Brazil IPHAN SICG:sitios archaeological site registry via paged WFS GeoJSON."""
  out_json = RAW_ARCH / "iphan_sicg_sitios.geojson"
  if out_json.exists() and out_json.stat().st_size > 1_000_000:
    print(f"[IPHAN] Already present: {out_json.name} ({out_json.stat().st_size:,} B)")
    return

  print("[IPHAN] Fetching SICG:sitios via WFS GeoJSON...")
  base = "https://geoserver.iphan.gov.br/geoserver/wfs"
  # Try direct GeoJSON bulk pull or 2.0.0 startIndex pagination
  all_features = []
  page_size = 5000
  start = 0
  while True:
    params = {
      "service": "WFS",
      "version": "1.0.0",
      "request": "GetFeature",
      "typeName": "SICG:sitios",
      "outputFormat": "application/json",
      "maxFeatures": str(page_size),
      "startIndex": str(start),
    }
    try:
      r = requests.get(base, params=params, headers=HEADERS, verify=False, timeout=120)
      if r.status_code != 200:
        print(f"  [IPHAN] HTTP {r.status_code} at start={start}: {r.text[:400]}")
        # Try without startIndex (bulk single request)
        if start == 0:
          r2 = requests.get(base, params={"service": "WFS", "version": "1.0.0", "request": "GetFeature", "typeName": "SICG:sitios", "outputFormat": "application/json"}, headers=HEADERS, verify=False, timeout=180)
          if r2.status_code == 200:
            data = r2.json()
            all_features.extend(data.get("features", []))
            print(f"  [IPHAN] Bulk fetched {len(all_features)} features")
          else:
            print(f"  [IPHAN bulk] HTTP {r2.status_code}: {r2.text[:400]}")
        break
      data = r.json()
      feats = data.get("features", [])
      if not feats:
        break
      all_features.extend(feats)
      print(f"  [IPHAN] Fetched {len(feats)} features (total={len(all_features)})")
      if len(feats) < page_size:
        break
      start += page_size
    except Exception as exc:
      print(f"  [IPHAN] Exception at start={start}: {exc}")
      break

  if all_features:
    with open(out_json, "w", encoding="utf-8") as fh:
      json.dump({"type": "FeatureCollection", "features": all_features}, fh, ensure_ascii=False)
    print(f"[IPHAN] Saved {len(all_features):,} sites to {out_json.name}")


def fetch_rxpand_and_sales_sdm():
  """Fetches Jonas Gregorio de Souza rxpand radiocarbon dates and Sales 2021 Zenodo ADE/arch SDM."""
  print("[ARCH] Fetching jgregoriods/rxpand & Sales 2021 Zenodo...")
  try:
    r = requests.get("https://api.github.com/repos/jgregoriods/rxpand/contents", headers=HEADERS, timeout=20)
    if r.status_code == 200:
      for item in r.json():
        if item.get("type") == "dir" and item.get("name") in ("data", "data-raw", "inst"):
          sub = requests.get(item["url"], headers=HEADERS, timeout=20).json()
          for sf in sub:
            if sf.get("download_url"):
              fetch_file(sf["download_url"], RAW_ARCH / f"rxpand_{sf['name']}")
        elif item.get("download_url") and item["name"].lower().endswith((".csv", ".rda", ".rds", ".json", ".txt")):
          fetch_file(item["download_url"], RAW_ARCH / f"rxpand_{item['name']}")
  except Exception as exc:
    print(f"  [rxpand ERR] {exc}")

  # Sales 2021 Zenodo 5784334
  sales_zip = RAW_ARCH / "sales_2021_sdm.zip"
  if fetch_file("https://zenodo.org/api/records/5784334/files/rachelsales14/Sales_2021_SDM-doi.zip/content", sales_zip, True, 120):
    sales_dir = RAW_ARCH / "sales_2021_sdm"
    if not sales_dir.exists():
      try:
        with zipfile.ZipFile(sales_zip) as zf:
          zf.extractall(sales_dir)
        print(f"  [OK] Extracted {sales_dir.name}")
      except Exception as exc:
        print(f"  [WARN] Unzip failed: {exc}")


def convert_rds_to_csv():
  """Uses Rscript to convert Peripato Earthworks.rds and any .rda/.rds files to CSV."""
  rscript = r"C:\Program Files\R\R-4.6.1\bin\x64\Rscript.exe"
  if not os.path.exists(rscript):
    rscript = r"C:\Program Files\R\R-4.5.0\bin\x64\Rscript.exe"
  if not os.path.exists(rscript):
    print("[R] Rscript not found, skipping RDS conversion.")
    return

  ew_rds = RAW_ARCH / "peripato_Earthworks.rds"
  ew_csv = RAW_ARCH / "peripato_Earthworks.csv"
  if ew_rds.exists() and not ew_csv.exists():
    rcmd = (
      f"x <- readRDS('{ew_rds.as_posix()}'); "
      f"cat('Class:', class(x), 'Len/Dim:', dim(x), length(x), '\\n'); "
      f"if (is.data.frame(x)) write.csv(x, '{ew_csv.as_posix()}', row.names=FALSE) "
      f"else if (inherits(x, 'SpatialPointsDataFrame') || inherits(x, 'Spatial')) {{ "
      f"  df <- as.data.frame(x); write.csv(df, '{ew_csv.as_posix()}', row.names=FALSE) "
      f"}} else if (is.list(x)) {{ print(names(x)) }}"
    )
    res = subprocess.run([rscript, "-e", rcmd], capture_output=True, text=True)
    print("[R Earthworks]", res.stdout.strip(), res.stderr.strip()[:200])

  # Convert any rxpand .rda files
  for rda in RAW_ARCH.glob("rxpand_*.rda"):
    out_c = RAW_ARCH / (rda.stem + ".csv")
    if out_c.exists():
      continue
    rcmd = (
      f"e <- new.env(); load('{rda.as_posix()}', envir=e); "
      f"for (nm in ls(e)) {{ obj <- get(nm, envir=e); "
      f"if (is.data.frame(obj)) write.csv(obj, '{out_c.as_posix()}', row.names=FALSE) }}"
    )
    res = subprocess.run([rscript, "-e", rcmd], capture_output=True, text=True)
    if out_c.exists():
      print(f"  [R OK] {out_c.name} ({out_c.stat().st_size:,} B)")


def fetch_geonames_sa():
  """Downloads GeoNames official country dumps for PRETA countries & border buffer."""
  gn_dir = RAW_CENSUS / "geonames"
  gn_dir.mkdir(parents=True, exist_ok=True)
  for cc in ["BR", "BO", "PY", "GY", "SR", "GF", "CO", "PE", "EC"]:
    z_out = gn_dir / f"{cc}.zip"
    txt_out = gn_dir / f"{cc}.txt"
    if txt_out.exists() and txt_out.stat().st_size > 1000:
      print(f"  [SKIP] GeoNames {cc}.txt ({txt_out.stat().st_size:,} B)")
      continue
    if fetch_file(f"https://download.geonames.org/export/dump/{cc}.zip", z_out, True, 90):
      with zipfile.ZipFile(z_out) as zf:
        zf.extractall(gn_dir)


def fetch_ibge_and_bolivia():
  """Downloads IBGE localities + SIDRA census tables (1970-2022 + historical) & Bolivia municipalities."""
  print("[IBGE] Fetching municipalities, districts, and SIDRA census tables...")
  fetch_file("https://servicodados.ibge.gov.br/api/v1/localidades/municipios", RAW_CENSUS / "ibge_municipios.json")
  fetch_file("https://servicodados.ibge.gov.br/api/v1/localidades/distritos", RAW_CENSUS / "ibge_distritos.json")

  # SIDRA Table 200 (1970, 1980, 1991, 2000, 2010) total population per municipality (c2=0 total sex, c1=0 total situation, c58=0 total age)
  for yr in ["1970", "1980", "1991", "2000", "2010"]:
    url = f"https://apisidra.ibge.gov.br/values/t/200/n6/all/v/93/p/{yr}/c2/0/c1/0/c58/0"
    fetch_file(url, RAW_CENSUS / f"ibge_sidra_pop_{yr}.json", True, 90)
    time.sleep(0.3)

  # SIDRA Table 4709 (Censo 2022) total resident population per municipality (v=93)
  fetch_file("https://apisidra.ibge.gov.br/values/t/4709/n6/all/v/93/p/2022", RAW_CENSUS / "ibge_sidra_pop_2022.json", True, 90)

  # SIDRA Table 1286 (População nos Censos Demográficos 1872-2010 by UF!)
  fetch_file("https://apisidra.ibge.gov.br/values/t/1286/n3/all/v/631/p/all", RAW_CENSUS / "ibge_sidra_uf_1872_2010.json", True, 90)

  # Bolivia 2024 municipalities from lab-tecnosocial
  print("[BOLIVIA] Fetching lab-tecnosocial/municipios-bolivia-2024...")
  try:
    r = requests.get("https://api.github.com/repos/lab-tecnosocial/municipios-bolivia-2024/contents", headers=HEADERS, timeout=20)
    if r.status_code == 200:
      for item in r.json():
        if item.get("download_url") and item["name"].lower().endswith((".csv", ".geojson", ".json")):
          fetch_file(item["download_url"], RAW_CENSUS / f"bolivia_2024_{item['name']}")
  except Exception as exc:
    print(f"  [BOLIVIA ERR] {exc}")


if __name__ == "__main__":
  fetch_iphan_sicg_wfs()
  fetch_rxpand_and_sales_sdm()
  convert_rds_to_csv()
  fetch_geonames_sa()
  fetch_ibge_and_bolivia()
  print("ALL RAW SOURCE DOWNLOADS COMPLETED.")
