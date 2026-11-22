"""Downloads authentic, period-accurate European Historical GIS (HGIS) boundaries & enumerations
across 1500-2025 into `MAGNETIC/_shared/subadmin_hgis/raw_sources/` (ZERO anachronistic NUTS!)."""
import json
import os
import urllib.parse
import urllib.request

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC",
  "_shared", "subadmin_hgis", "raw_sources"
)
os.makedirs(RAW_DIR, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def download_file(url, dest_rel, min_bytes=50):
  dest = os.path.join(RAW_DIR, dest_rel)
  os.makedirs(os.path.dirname(dest), exist_ok=True)
  if os.path.isfile(dest) and os.path.getsize(dest) >= min_bytes:
    print(f"  [SKIP] {dest_rel} ({os.path.getsize(dest):,} B)", flush=True)
    return True
  try:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
      data = r.read()
    if len(data) < min_bytes:
      print(f"  [SMALL] {dest_rel}: {len(data)} B", flush=True)
      return False
    with open(dest, "wb") as fh:
      fh.write(data)
    print(f"  [OK]   {dest_rel} ({len(data):,} B)", flush=True)
    return True
  except Exception as e:
    print(f"  [ERR]  {dest_rel}: {e}", flush=True)
    return False


def download_histogis_source(source_name, out_rel):
  dest = os.path.join(RAW_DIR, out_rel)
  os.makedirs(os.path.dirname(dest), exist_ok=True)
  if os.path.isfile(dest) and os.path.getsize(dest) > 500:
    print(f"  [SKIP] {out_rel} ({os.path.getsize(dest):,} B)", flush=True)
    return True
  q = urllib.parse.quote(source_name)
  url = f"https://histogis.acdh.oeaw.ac.at/api/tempspatial/?format=json&source_name={q}&limit=500"
  all_feats = []
  try:
    while url:
      req = urllib.request.Request(url, headers=HEADERS)
      with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode("utf-8", errors="ignore"))
      if "features" in d:
        all_feats.extend(d["features"])
        url = d.get("next")
      elif "results" in d and isinstance(d["results"], dict) and "features" in d["results"]:
        all_feats.extend(d["results"]["features"])
        url = d.get("next")
      else:
        print(f"  [UNEXPECTED] {source_name}: keys={list(d.keys())}", flush=True)
        return False
      if len(all_feats) > 3000:
        break
    if not all_feats:
      print(f"  [EMPTY] {source_name}", flush=True)
      return False
    fc = {"type": "FeatureCollection", "source": source_name, "features": all_feats}
    with open(dest, "w", encoding="utf-8") as fh:
      json.dump(fc, fh, ensure_ascii=False)
    print(f"  [OK]   {out_rel} ({len(all_feats)} features, {os.path.getsize(dest):,} B)", flush=True)
    return True
  except Exception as e:
    print(f"  [ERR]  {out_rel}: {e}", flush=True)
    return False


def main():
  print("=== 1. DEMOPAST Italy (1861-1971 Historic Provinces GeoJSON + Census CSVs) ===", flush=True)
  it_years = [1861, 1871, 1881, 1901, 1911, 1921, 1931, 1936, 1951, 1961, 1971]
  for y in it_years:
    download_file(f"https://demopast.it/data/geojson/province_{y}.geojson", f"demopast_italy/province_{y}.geojson")
    download_file(f"https://demopast.it/downloads/{y}/data_census_{y}_adjusted_age.csv", f"demopast_italy/census_{y}.csv")
  download_file("https://demopast.it/downloads/citta/data_census_citta.csv", "demopast_italy/data_census_citta.csv")

  print("\n=== 2. HistoGIS OEAW (HRE 1512-1792, Habsburg 1815-1910, Germany/Prussia 1820-1914, Europe 1815-1919) ===", flush=True)
  histogis_layers = [
    ("Holy Roman Empire Imperial Circles 1512", "histogis/hre_circles_1512.geojson"),
    ("Holy Roman Empire Imperial Circles 1648", "histogis/hre_circles_1648.geojson"),
    ("Holy Roman Empire Imperial Circles 1792", "histogis/hre_circles_1792.geojson"),
    ("Austrian Empire Crownlands 1815", "histogis/austria_crownlands_1815.geojson"),
    ("Austrian Empire Crownlands 1850", "histogis/austria_crownlands_1850.geojson"),
    ("Austrian Empire Crownlands 1867", "histogis/austria_crownlands_1867.geojson"),
    ("Austro-Hungarian Empire Crownlands 1870", "histogis/austria_hungary_crownlands_1870.geojson"),
    ("Austro-Hungarian Empire Crownlands 1910", "histogis/austria_hungary_crownlands_1910.geojson"),
    ("Austro-Hungarian Empire Entities 1910", "histogis/austria_hungary_entities_1910.geojson"),
    ("German States Stateborders 1820", "histogis/german_states_1820.geojson"),
    ("German States Stateborders 1850", "histogis/german_states_1850.geojson"),
    ("German Empire Stateborders 1871 2", "histogis/german_empire_1871.geojson"),
    ("Prussia Governmental Districts 1820", "histogis/prussia_rb_1820.geojson"),
    ("Prussia Governmental Districts 1848", "histogis/prussia_rb_1848.geojson"),
    ("Prussia Governmental Districts 1867", "histogis/prussia_rb_1867.geojson"),
    ("Prussia Governmental Districts 1880", "histogis/prussia_rb_1880.geojson"),
    ("Prussia Governmental Districts 1914", "histogis/prussia_rb_1914.geojson"),
    ("Europe Stateborders 1815", "histogis/europe_states_1815.geojson"),
    ("Europe Stateborders 1850", "histogis/europe_states_1850.geojson"),
    ("Europe Stateborders 1880", "histogis/europe_states_1880.geojson"),
    ("Europe Stateborders 1900", "histogis/europe_states_1900.geojson"),
    ("Europe Stateborders 1914", "histogis/europe_states_1914.geojson"),
    ("Europe Stateborders 1919", "histogis/europe_states_1919.geojson"),
  ]
  for sname, rel in histogis_layers:
    download_histogis_source(sname, rel)

  print("\n=== 3. France SGF (1801-1925), Spain (mapSpainHist), Sweden (swehist), UK, NL, DK ===", flush=True)
  gh_files = [
    ("https://raw.githubusercontent.com/observatoire-territoires/sgf/master/geo/geo_DEP_SGF_histo.rds", "sgf_france/geo_DEP_SGF_histo.rds"),
    ("https://raw.githubusercontent.com/observatoire-territoires/sgf/master/data/geo_DEP_SGF_histo.rda", "sgf_france/geo_DEP_SGF_histo.rda"),
    ("https://raw.githubusercontent.com/observatoire-territoires/sgf/master/data/data_SGF.rda", "sgf_france/data_SGF.rda"),
    ("https://raw.githubusercontent.com/observatoire-territoires/sgf/master/data/indicateurs_SGF.rda", "sgf_france/indicateurs_SGF.rda"),
    ("https://raw.githubusercontent.com/pauvallprat/mapSpainHist/main/data/censos.rda", "spain_hist/censos.rda"),
    ("https://raw.githubusercontent.com/pauvallprat/mapSpainHist/main/data/unitats.rda", "spain_hist/unitats.rda"),
    ("https://raw.githubusercontent.com/junkka/swehist/main/data/boundaries.rda", "sweden_hist/boundaries.rda"),
    ("https://raw.githubusercontent.com/junkka/swehist/main/data/sweden.rda", "sweden_hist/sweden.rda"),
    ("https://raw.githubusercontent.com/junkka/swehist/main/data/hist_town.rda", "sweden_hist/hist_town.rda"),
    ("https://raw.githubusercontent.com/evansd/uk-ceremonial-counties/master/uk-ceremonial-counties.geojson", "uk_hist/uk_ceremonial_counties.geojson"),
    ("https://raw.githubusercontent.com/AshkanA/HarmonizedCensusData/master/JuridischAanwezige_Bevolking.xlsx", "nl_hist/nl_juridisch_bevolking_1859_1920.xlsx"),
    ("https://raw.githubusercontent.com/AshkanA/HarmonizedCensusData/master/FeitelijkAanwezige_Bevolking.xlsx", "nl_hist/nl_feitelijk_bevolking_1859_1920.xlsx"),
    ("https://raw.githubusercontent.com/christianvedels/Tracks_to_modernity/main/Data/Census_data.csv", "dk_hist/dk_census_data.csv"),
    ("https://raw.githubusercontent.com/christianvedels/Tracks_to_modernity/main/Data/Market_towns.csv", "dk_hist/dk_market_towns.csv"),
  ]
  for url, rel in gh_files:
    download_file(url, rel)

  print("\n=== 4. Historical Basemaps (1500-1994 Period-Authentic European Polity Borders) ===", flush=True)
  hb_years = ["1500", "1600", "1700", "1783", "1800", "1815", "1880", "1900", "1914", "1920", "1930", "1938", "1945", "1960", "1994"]
  for y in hb_years:
    download_file(
      f"https://raw.githubusercontent.com/aourednik/historical-basemaps/master/geojson/world_{y}.geojson",
      f"historical_basemaps/world_{y}.geojson"
    )
  print("\n[DONE] Comprehensive HGIS raw download pass complete.", flush=True)


if __name__ == "__main__":
  main()
