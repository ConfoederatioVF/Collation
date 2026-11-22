"""Downloads full HistoGIS dump JSONL (acdh-oeaw/histogis-data) and inspects Spain/DK/NL/IT/SE parsed tables."""
import csv
import json
import os
import urllib.request
from collections import defaultdict

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MAGNETIC\_shared\subadmin_hgis\raw_sources"
PARSED_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MAGNETIC\_shared\subadmin_hgis\parsed"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def download_histogis_dump():
  dest = os.path.join(RAW_DIR, "histogis", "histogis-dump.jsonl")
  os.makedirs(os.path.dirname(dest), exist_ok=True)
  if os.path.isfile(dest) and os.path.getsize(dest) > 1000000:
    print(f"[SKIP] histogis-dump.jsonl ({os.path.getsize(dest):,} B)", flush=True)
    return dest
  for branch in ("main", "master"):
    # Check Git LFS pointer vs raw file
    url = f"https://media.githubusercontent.com/media/acdh-oeaw/histogis-data/{branch}/histogis-dump.jsonl"
    try:
      req = urllib.request.Request(url, headers=HEADERS)
      with urllib.request.urlopen(req, timeout=180) as r:
        with open(dest, "wb") as fh:
          tot = 0
          while True:
            chunk = r.read(1024 * 512)
            if not chunk:
              break
            fh.write(chunk)
            tot += len(chunk)
      print(f"[OK] histogis-dump.jsonl from {branch} ({tot:,} B)", flush=True)
      return dest
    except Exception as e:
      print(f"[TRY {branch}] {e}", flush=True)
  return None


def inspect_tables():
  # 1. DEMOPAST Italy 1881 header
  it_p = os.path.join(RAW_DIR, "demopast_italy", "census_1881.csv")
  with open(it_p, encoding="utf-8-sig") as fh:
    rdr = csv.reader(fh)
    print("\nDEMOPAST IT 1881 cols:", next(rdr)[:15], "row1:", next(rdr)[:15])
  # 2. Spain censos summary
  es_p = os.path.join(PARSED_DIR, "spain_hist_censos.csv")
  if os.path.isfile(es_p):
    yrs = defaultdict(float)
    provs = set()
    with open(es_p, encoding="utf-8-sig") as fh:
      for r in csv.DictReader(fh):
        y = r.get("censo")
        v = r.get("phec") or r.get("pder") or r.get("pob_serie")
        if y and v and v != "NA":
          try:
            yrs[int(float(y))] += float(v)
            provs.add(r.get("prov"))
          except Exception:
            pass
    print(f"Spain mapSpainHist: {len(provs)} provinces | years: {sorted((k, int(v)) for k, v in yrs.items())}")
  # 3. Denmark census_data header
  dk_p = os.path.join(RAW_DIR, "dk_hist", "dk_census_data.csv")
  with open(dk_p, encoding="utf-8-sig") as fh:
    rdr = csv.reader(fh)
    print("DK census cols:", next(rdr)[:15], "row1:", next(rdr)[:15])
  # 4. Sweden se_histmaps_code_counties.csv
  se_p = os.path.join(RAW_DIR, "se_histmaps_code_counties.csv")
  with open(se_p, encoding="utf-8-sig") as fh:
    rdr = csv.reader(fh)
    print("SE county csv cols:", next(rdr)[:15], "row1:", next(rdr)[:15])


if __name__ == "__main__":
  download_histogis_dump()
  inspect_tables()
