"""Downloads Spain provinces, Switzerland cantons, Netherlands provinces & Belgium provinces GeoJSONs."""
import os
import urllib.request

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MAGNETIC\_shared\subadmin_hgis\raw_sources"
HEADERS = {"User-Agent": "Mozilla/5.0"}

FILES = [
  ("https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/spain-provinces.geojson", "spain_hist/spain_provinces.geojson"),
  ("https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/switzerland.geojson", "ch_hist/switzerland_cantons.geojson"),
  ("https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/the-netherlands.geojson", "nl_hist/netherlands_provinces.geojson"),
  ("https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/belgium.geojson", "be_hist/belgium_provinces.geojson"),
  ("https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/portugal.geojson", "pt_hist/portugal_distritos.geojson"),
  ("https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/norway.geojson", "no_hist/norway_counties.geojson"),
  ("https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/finland.geojson", "fi_hist/finland_regions.geojson"),
  ("https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/denmark-counties.geojson", "dk_hist/denmark_counties.geojson"),
]

for url, rel in FILES:
  dest = os.path.join(RAW_DIR, rel)
  os.makedirs(os.path.dirname(dest), exist_ok=True)
  if os.path.isfile(dest) and os.path.getsize(dest) > 500:
    print(f"[SKIP] {rel}")
    continue
  try:
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as r:
      data = r.read()
    with open(dest, "wb") as fh:
      fh.write(data)
    print(f"[OK]   {rel} ({len(data):,} B)")
  except Exception as e:
    print(f"[ERR]  {rel}: {e}")
