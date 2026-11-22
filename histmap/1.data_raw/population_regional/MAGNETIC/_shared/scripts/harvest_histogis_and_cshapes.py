"""Downloads HistoGIS static GeoJSON exports (acdh-oeaw/histogis-data) & CShapes 2.0 GeoJSON."""
import json
import os
import re
import urllib.request

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MAGNETIC\_shared\subadmin_hgis\raw_sources"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get_bytes(url, timeout=45):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=timeout) as r:
    return r.read()


def main():
  # 1. Check acdh-oeaw/histogis-data
  print("=== 1. acdh-oeaw/histogis-data ===", flush=True)
  try:
    items = json.loads(get_bytes("https://api.github.com/repos/acdh-oeaw/histogis-data/contents").decode("utf-8"))
    print("  root:", [f"{x['name']}({x['type']})" for x in items], flush=True)
    for x in items:
      if x["type"] == "dir":
        sub = json.loads(get_bytes(x["url"]).decode("utf-8"))
        print(f"  {x['name']}/ ({len(sub)}):", [y["name"] for y in sub[:40]], flush=True)
  except Exception as e:
    print("  histogis-data err:", e, flush=True)

  # 2. Check HistoGIS direct shapes/geojson endpoint with source IDs
  print("\n=== 2. HistoGIS source IDs & direct geojson ===", flush=True)
  try:
    html = get_bytes("https://histogis.acdh.oeaw.ac.at/shapes/sources/").decode("utf-8", errors="ignore")
    matches = re.findall(r"""href=["'](/shapes/source/(\d+)/?)["'][^>]*>([^<]+)<""", html, re.I)
    print(f"  Found {len(matches)} HTML source links:", matches[:20], flush=True)
  except Exception as e:
    print("  histogis html err:", e, flush=True)

  # 3. Check CShapes 2.0 direct download URL
  print("\n=== 3. CShapes 2.0 ===", flush=True)
  try:
    html = get_bytes("https://icr.ethz.ch/data/cshapes/").decode("utf-8", errors="ignore")
    links = sorted(set(re.findall(r"""href=["']([^"']*(?:CShapes|cshapes)[^"']*(?:geojson|zip|shp|json))["']""", html, re.I)))
    print("  CShapes links:", links, flush=True)
    for l in links:
      full = l if l.startswith("http") else ("https://icr.ethz.ch" + (l if l.startswith("/") else "/data/cshapes/" + l))
      if full.lower().endswith(".geojson"):
        dest = os.path.join(RAW_DIR, "cshapes", os.path.basename(full))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if not os.path.isfile(dest):
          data = get_bytes(full, timeout=90)
          with open(dest, "wb") as fh:
            fh.write(data)
          print(f"  [OK] {os.path.basename(dest)} ({len(data):,} B)", flush=True)
        else:
          print(f"  [SKIP] {os.path.basename(dest)}", flush=True)
  except Exception as e:
    print("  CShapes err:", e, flush=True)


if __name__ == "__main__":
  main()
