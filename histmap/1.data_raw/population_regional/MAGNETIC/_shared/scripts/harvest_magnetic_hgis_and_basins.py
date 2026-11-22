"""Downloads fine-grained HydroBASINS L7/L8 & open European Historical GIS sub-administrative
vector boundaries and longitudinal census enumeration datasets for Project MAGNETIC.
"""
import json
import os
import urllib.request
import urllib.error

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC")
GIS_DIR = os.path.join(MAG_DIR, "_shared", "_gis_cache")
HGIS_DIR = os.path.join(MAG_DIR, "_shared", "subadmin_hgis", "raw_sources")

os.makedirs(GIS_DIR, exist_ok=True)
os.makedirs(HGIS_DIR, exist_ok=True)

UA = {"User-Agent": "SVEA-Viscount-MAGNETIC-Research/1.0"}

DOWNLOADS = [
  # 1. Fine-grained HydroBASINS Level 7 for dense European archaeological catchments (~2,000 km2)
  (os.path.join(GIS_DIR, "hybas_eu_lev07_v1c.zip"),
   "https://data.hydrosheds.org/file/HydroBASINS/standard/hybas_eu_lev07_v1c.zip"),

  # 2. Eurostat GISCO NUTS-3 (1,166 European districts, 2021 & 2016) and NUTS-2 (2021)
  (os.path.join(HGIS_DIR, "eurostat_nuts3_2021_03m.geojson"),
   "https://raw.githubusercontent.com/eurostat/Nuts2json/master/pub/v2/2021/4326/03M/nutsrg_3.json"),
  (os.path.join(HGIS_DIR, "eurostat_nuts2_2021_10m.geojson"),
   "https://raw.githubusercontent.com/eurostat/Nuts2json/master/pub/v2/2021/4326/10M/nutsrg_2.json"),
  (os.path.join(HGIS_DIR, "eurostat_nuts3_2016_10m.geojson"),
   "https://raw.githubusercontent.com/eurostat/Nuts2json/master/pub/v2/2016/4326/10M/nutsrg_3.json"),

  # 3. Eurostat SDMX-CSV NUTS-3 longitudinal population (1990-2025)
  (os.path.join(HGIS_DIR, "eurostat_demo_r_pjanaggr3.csv"),
   "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/demo_r_pjanaggr3/A.NR.T.TOTAL.?format=SDMX-CSV&startPeriod=1990"),

  # 4. Rosés-Wolf European Regional Database (1900-2015, 173 NUTS-2 regions across 16 European countries)
  (os.path.join(HGIS_DIR, "roses_wolf_data.xlsx"),
   "https://raw.githubusercontent.com/j-jayes/Roses-Wolf-database-on-regional-GDP/main/data.xlsx"),
  (os.path.join(HGIS_DIR, "roses_wolf_regions_nuts2.shp"),
   "https://raw.githubusercontent.com/j-jayes/Roses-Wolf-database-on-regional-GDP/main/regions_nuts2.shp"),
  (os.path.join(HGIS_DIR, "roses_wolf_regions_nuts2.dbf"),
   "https://raw.githubusercontent.com/j-jayes/Roses-Wolf-database-on-regional-GDP/main/regions_nuts2.dbf"),
  (os.path.join(HGIS_DIR, "roses_wolf_regions_nuts2.shx"),
   "https://raw.githubusercontent.com/j-jayes/Roses-Wolf-database-on-regional-GDP/main/regions_nuts2.shx"),
  (os.path.join(HGIS_DIR, "roses_wolf_regions_nuts2.prj"),
   "https://raw.githubusercontent.com/j-jayes/Roses-Wolf-database-on-regional-GDP/main/regions_nuts2.prj"),

  # 5. Galloway Prussia Database (1861-1914 Kreise & Regierungsbezirke)
  (os.path.join(HGIS_DIR, "Galloway_Prussia_Database_XLS.zip"),
   "http://www.patrickrgalloway.com/Galloway_Prussia_Database_XLS.zip"),

  # 6. Historical European Empire / Province GeoJSONs (Germany 1880/1914, Hungary, Galicia, Poland 1914, Serbia)
  (os.path.join(HGIS_DIR, "eu_hist_germany_1880.geojson"),
   "https://raw.githubusercontent.com/ioggstream/europe-historical-geojson/main/data/geojson/germany-1880.geojson"),
  (os.path.join(HGIS_DIR, "eu_hist_germany_1914.geojson"),
   "https://raw.githubusercontent.com/ioggstream/europe-historical-geojson/main/data/geojson/germany-1914.geojson"),
  (os.path.join(HGIS_DIR, "eu_hist_galicia.geojson"),
   "https://raw.githubusercontent.com/ioggstream/europe-historical-geojson/main/data/geojson/map-Galizia.geojson"),
  (os.path.join(HGIS_DIR, "eu_hist_hungary.geojson"),
   "https://raw.githubusercontent.com/ioggstream/europe-historical-geojson/main/data/geojson/map-Ungheria.geojson"),
  (os.path.join(HGIS_DIR, "eu_hist_poland_1914.geojson"),
   "https://raw.githubusercontent.com/ioggstream/europe-historical-geojson/main/data/geojson/poland-1914.geojson"),

  # 7. Sweden Riksarkivet Historical Counties metadata & code tables (junkka/histmaps)
  (os.path.join(HGIS_DIR, "se_histmaps_code_counties.csv"),
   "https://raw.githubusercontent.com/junkka/histmaps/master/data-raw/data/code_counties.csv"),
  (os.path.join(HGIS_DIR, "se_histmaps_county_meta.csv"),
   "https://raw.githubusercontent.com/junkka/histmaps/master/data-raw/data/county_meta.csv"),

  # 8. OSHistory histgeodata directory (for additional open European HGIS links)
  (os.path.join(HGIS_DIR, "oshistory_histgeodata_readme.md"),
   "https://raw.githubusercontent.com/OSHistory/histgeodata/master/README.md"),
]


def download_file(dest, url):
  if os.path.isfile(dest) and os.path.getsize(dest) > 500:
    print(f"  [CACHED] {os.path.basename(dest)} ({os.path.getsize(dest):,} B)", flush=True)
    return True
  req = urllib.request.Request(url, headers=UA)
  try:
    with urllib.request.urlopen(req, timeout=120) as resp:
      tmp = dest + ".part"
      tot = 0
      with open(tmp, "wb") as f:
        while True:
          chunk = resp.read(262144)
          if not chunk:
            break
          f.write(chunk)
          tot += len(chunk)
      os.replace(tmp, dest)
      print(f"  [OK]     {os.path.basename(dest)} ({tot:,} B)", flush=True)
      return True
  except Exception as exc:
    print(f"  [FAIL]   {os.path.basename(dest)}: {exc}", flush=True)
    return False


def main():
  ok = 0
  for dest, url in DOWNLOADS:
    if download_file(dest, url):
      ok += 1
  print(f"\nCompleted {ok}/{len(DOWNLOADS)} downloads.", flush=True)


if __name__ == "__main__":
  main()
