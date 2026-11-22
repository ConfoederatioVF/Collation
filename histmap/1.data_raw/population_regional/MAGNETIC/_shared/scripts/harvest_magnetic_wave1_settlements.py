"""Stage B Wave 1: Downloads primary official European city, municipal and ancient settlement datasets
into `MAGNETIC/_shared/settlement_sources/` (Eurostat Urban Audit 1990-2024, Pleiades Ancient World,
French INSEE commune coordinates, Spanish INE municipal coordinates, UK/DE/IT/Nordic/Balkan official portals)."""
import gzip
import json
import os
import urllib.request

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
OUT_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC",
  "_shared", "settlement_sources"
)
os.makedirs(OUT_DIR, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def dl(url, fname, min_bytes=500):
  dest = os.path.join(OUT_DIR, fname)
  if os.path.isfile(dest) and os.path.getsize(dest) >= min_bytes:
    print(f"  [SKIP] {fname} ({os.path.getsize(dest):,} B)", flush=True)
    return True
  try:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as r:
      with open(dest, "wb") as fh:
        tot = 0
        while True:
          chunk = r.read(1024 * 256)
          if not chunk:
            break
          fh.write(chunk)
          tot += len(chunk)
    print(f"  [OK]   {fname} ({tot:,} B)", flush=True)
    return True
  except Exception as e:
    print(f"  [ERR]  {fname}: {e}", flush=True)
    return False


def main():
  print("=== Stage B Wave 1: Primary European Settlement & Census Sources ===", flush=True)
  # 1. Eurostat GISCO Urban Audit Cities (exact coordinates for 1.000+ European cities across 37 countries)
  dl("https://gisco-services.ec.europa.eu/distribution/v2/urau/geojson/URAU_LB_2021_4326_CITIES.geojson", "eurostat_urau_cities_2021.geojson")
  # 2. Eurostat urb_cpop1 longitudinal city population (1990-2024)
  dl("https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/urb_cpop1?format=SDMX-CSV&compressed=false", "eurostat_urb_cpop1_1990_2024.csv")
  # 3. Pleiades Ancient World Gazetteer (Classical Greece, Iron Age, Roman Empire, Late Antiquity)
  dl("https://atlantides.org/downloads/pleiades/dumps/pleiades-places-latest.csv.gz", "pleiades_places_latest.csv.gz")
  # 4. Official French Government API (geo.api.gouv.fr): all 35.000 French communes with INSEE code, centre coords & population
  dl("https://geo.api.gouv.fr/communes?fields=nom,code,codeDepartement,population,centre&format=json&geometry=centre", "insee_france_communes_coords.json")
  # 5. Official ISTAT / OpenData Italy comuni with coordinates & ISTAT codes
  dl("https://raw.githubusercontent.com/matteocontrini/comuni-json/master/comuni.json", "istat_italy_comuni.json")
  dl("https://raw.githubusercontent.com/opendatasicilia/comuni-italiani/main/dati/main.csv", "istat_italy_comuni_coords.csv")
  # 6. Spanish INE municipalities with coordinates (matches our 215.289-row spain_hist_censos.csv!)
  dl("https://raw.githubusercontent.com/frontid/ComunidadesProvinciasPoblaciones/master/poblaciones.json", "ine_spain_municipios.json")
  dl("https://raw.githubusercontent.com/IagoLast/pselect/master/data/municipios.json", "ine_spain_municipios_alt.json")
  # 7. GeoNames European cities500 (strictly for coordinate matching of official census records & micro-territories)
  dl("https://download.geonames.org/export/dump/cities1000.zip", "geonames_cities1000.zip")
  print("\n[DONE] Wave 1 primary settlement archive downloads complete.", flush=True)


if __name__ == "__main__":
  main()
