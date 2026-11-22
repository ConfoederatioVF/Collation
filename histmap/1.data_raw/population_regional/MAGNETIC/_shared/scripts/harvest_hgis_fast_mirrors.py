"""Fast downloader for France SGF (1801-1925), Spain (mapSpainHist), Sweden (swehist), UK historic counties,
Netherlands (1859-1920), Denmark (1787-1916), and Historical Basemaps (1500-1994)."""
import os
import urllib.request

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC",
  "_shared", "subadmin_hgis", "raw_sources"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def download_file(url, dest_rel, min_bytes=50):
  dest = os.path.join(RAW_DIR, dest_rel)
  os.makedirs(os.path.dirname(dest), exist_ok=True)
  if os.path.isfile(dest) and os.path.getsize(dest) >= min_bytes:
    print(f"  [SKIP] {dest_rel} ({os.path.getsize(dest):,} B)", flush=True)
    return True
  try:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=45) as r:
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


def main():
  print("=== 1. National Historical GIS & Census Repositories ===", flush=True)
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

  print("\n=== 2. Historical Basemaps (1500-1994 Period-Authentic European Polity Borders) ===", flush=True)
  hb_years = ["1500", "1600", "1700", "1783", "1800", "1815", "1880", "1900", "1914", "1920", "1930", "1938", "1945", "1960", "1994"]
  for y in hb_years:
    download_file(
      f"https://raw.githubusercontent.com/aourednik/historical-basemaps/master/geojson/world_{y}.geojson",
      f"historical_basemaps/world_{y}.geojson"
    )
  print("\n[DONE]", flush=True)


if __name__ == "__main__":
  main()
