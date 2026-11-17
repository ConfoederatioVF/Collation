"""Downloads and catalogues open-access Northern American, Arctic, Greenlandic, Hawaiian
and Polynesian archaeological & heritage site registries into `_shared/sites_northern_america/raw_sources/`
and `_shared/sites_hawaii_polynesia/raw_sources/`.

Never accesses or bypasses any anti-bot/PoW-gated service; relies strictly on direct
HTTP 200 open archives and government REST services.
"""

import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

THIS_DIR = pathlib.Path(__file__).resolve().parent
CENTAUR_DIR = THIS_DIR.parents[1]
RAW_NA_DIR = THIS_DIR / "raw_sources"
RAW_HP_DIR = CENTAUR_DIR / "_shared" / "sites_hawaii_polynesia" / "raw_sources"
CENSUS_RAW_DIR = CENTAUR_DIR / "_shared" / "census_ingest" / "raw_sources"

RAW_NA_DIR.mkdir(parents=True, exist_ok=True)
RAW_HP_DIR.mkdir(parents=True, exist_ok=True)
CENSUS_RAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "SVEA-CENTAUR-Research/2.0"}


def download_file(arg0_urls, arg1_dest, arg2_min_bytes=64):
  """Downloads a file from the first working URL in arg0_urls if not already cached."""
  dest = pathlib.Path(arg1_dest)
  if dest.exists() and dest.stat().st_size >= arg2_min_bytes:
    return dest.stat().st_size, True
  urls = [arg0_urls] if isinstance(arg0_urls, str) else list(arg0_urls)
  last_err = None
  for url in urls:
    try:
      req = urllib.request.Request(url, headers=HEADERS)
      with urllib.request.urlopen(req, timeout=90) as resp:
        data = resp.read()
      if len(data) < arg2_min_bytes:
        raise RuntimeError(f"Download too small ({len(data)} bytes) from {url}")
      dest.parent.mkdir(parents=True, exist_ok=True)
      dest.write_bytes(data)
      return len(data), False
    except Exception as exc:
      last_err = exc
  raise RuntimeError(f"Failed all mirrors for {dest.name}: {last_err}")


def fetch_json(arg0_url, arg1_timeout=45):
  """Fetches JSON from a REST endpoint with retries."""
  last_err = None
  for attempt in range(3):
    try:
      req = urllib.request.Request(arg0_url, headers=HEADERS)
      with urllib.request.urlopen(req, timeout=arg1_timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
      last_err = exc
      time.sleep(1.5 * (attempt + 1))
  raise last_err


def paginate_arcgis_layer(
  arg0_base_url,
  arg1_out_fields,
  arg2_where="1=1",
  arg3_page_size=1000,
  arg4_max_offset=None,
  arg5_geom_prec=None,
):
  """Paginates an ArcGIS MapServer/FeatureServer layer via resultOffset with WGS84 output."""
  cnt_url = f"{arg0_base_url}/query?where={urllib.parse.quote(arg2_where)}&returnCountOnly=true&f=json"
  cnt_obj = fetch_json(cnt_url)
  total_count = int(cnt_obj.get("count", 0))
  features = []
  offset = 0
  while offset < total_count:
    params = {
      "where": arg2_where,
      "outFields": arg1_out_fields,
      "returnGeometry": "true",
      "outSR": "4326",
      "resultOffset": str(offset),
      "resultRecordCount": str(arg3_page_size),
      "f": "geojson",
    }
    if arg4_max_offset is not None:
      params["maxAllowableOffset"] = str(arg4_max_offset)
    if arg5_geom_prec is not None:
      params["geometryPrecision"] = str(arg5_geom_prec)
    qs = urllib.parse.urlencode(params)
    page = fetch_json(f"{arg0_base_url}/query?{qs}", arg1_timeout=60)
    batch = page.get("features", [])
    if not batch:
      break
    features.extend(batch)
    offset += len(batch)
    print(f"    fetched {offset}/{total_count}", flush=True)
  return {"type": "FeatureCollection", "total_expected": total_count, "features": features}


def main():
  summary = {}

  # Remove stale empty placeholder from broken Layer 0 group query
  stale_hi0 = RAW_HP_DIR / "hawaii_historic_cultural.geojson"
  if stale_hi0.exists() and stale_hi0.stat().st_size < 1024:
    stale_hi0.unlink()

  # 1. Academic & GitHub archaeological datasets + US counties
  github_files = [
    (
      "https://raw.githubusercontent.com/ericknrobinson/RadiocarbonDatabaseLower48States/master/Database_10-6-21.csv",
      RAW_NA_DIR / "kelly_robinson_lower48_2021.csv",
    ),
    (
      "https://raw.githubusercontent.com/village-ecodynamics/kohler_et_al_2023_ptrsb/main/data-raw/schwindt_et_al_2016/vepii_cmv.fgb",
      RAW_NA_DIR / "vepii_cmv.fgb",
    ),
    (
      "https://raw.githubusercontent.com/village-ecodynamics/kohler_et_al_2023_ptrsb/main/data-raw/reese_2021/4-occupation-by-household-subregion.csv",
      RAW_NA_DIR / "reese_2021_occupation_by_household_subregion.csv",
    ),
    (
      "https://raw.githubusercontent.com/village-ecodynamics/kohler_et_al_2023_ptrsb/main/data-raw/reese_2021/8-region-occupation-by-population.csv",
      RAW_NA_DIR / "reese_2021_region_occupation_by_population.csv",
    ),
    (
      "https://raw.githubusercontent.com/village-ecodynamics/kohler_et_al_2023_ptrsb/main/data-raw/kohler_et_al_2020_aarhus/vepiin_momentary_population.csv",
      RAW_NA_DIR / "vepiin_momentary_population.csv",
    ),
    (
      "https://raw.githubusercontent.com/village-ecodynamics/kohler_et_al_2023_ptrsb/main/data-raw/kohler_et_al_2023_collapse/MergedGinis.csv",
      RAW_NA_DIR / "vep_merged_ginis.csv",
    ),
    (
      "https://raw.githubusercontent.com/village-ecodynamics/kohler_et_al_2023_ptrsb/main/data-raw/kohler_reese_2014/kohler_reese2014_ndt.csv",
      RAW_NA_DIR / "kohler_reese2014_ndt.csv",
    ),
    (
      "https://raw.githubusercontent.com/erikgjes/Bayes_Phylogenies/master/plains_houses_rev.csv",
      RAW_NA_DIR / "plains_houses_rev.csv",
    ),
    (
      "https://raw.githubusercontent.com/erikgjes/Bayes_Phylogenies/master/plains_house_dates.csv",
      RAW_NA_DIR / "plains_house_dates.csv",
    ),
    (
      [
        "https://raw.githubusercontent.com/mpeeples2008/CriticalScales/main/attr_all.csv",
        "https://raw.githubusercontent.com/mpeeples2008/CriticalScales/master/attr_all.csv",
      ],
      RAW_NA_DIR / "swsn_critical_scales_attr_all.csv",
    ),
    (
      [
        "https://raw.githubusercontent.com/mpeeples2008/CriticalScales/main/data_all.csv",
        "https://raw.githubusercontent.com/mpeeples2008/CriticalScales/master/data_all.csv",
      ],
      RAW_NA_DIR / "swsn_critical_scales_data_all.csv",
    ),
    (
      [
        "https://raw.githubusercontent.com/mpeeples2008/ArchNetSci/main/data/AD1050attr.csv",
        "https://raw.githubusercontent.com/mpeeples2008/ArchNetSci/master/data/AD1050attr.csv",
      ],
      RAW_NA_DIR / "swsn_AD1050attr.csv",
    ),
    (
      [
        "https://raw.githubusercontent.com/mpeeples2008/ArchNetSci/main/data/AD1300attr.csv",
        "https://raw.githubusercontent.com/mpeeples2008/ArchNetSci/master/data/AD1300attr.csv",
      ],
      RAW_NA_DIR / "swsn_AD1300attr.csv",
    ),
    (
      [
        "https://raw.githubusercontent.com/mpeeples2008/ArchNetSci/main/data/Cibola_attr.csv",
        "https://raw.githubusercontent.com/mpeeples2008/ArchNetSci/master/data/Cibola_attr.csv",
      ],
      RAW_NA_DIR / "swsn_Cibola_attr.csv",
    ),
    (
      [
        "https://raw.githubusercontent.com/mpeeples2008/ArchNetSci/main/data/Clovis.csv",
        "https://raw.githubusercontent.com/mpeeples2008/ArchNetSci/master/data/Clovis.csv",
      ],
      RAW_NA_DIR / "archnet_Clovis.csv",
    ),
    (
      [
        "https://raw.githubusercontent.com/people3k/PopulationExpansion2025/main/data/RawP3Kc14.csv",
        "https://raw.githubusercontent.com/people3k/PopulationExpansion2025/master/data/RawP3Kc14.csv",
      ],
      RAW_NA_DIR / "people3k_RawP3Kc14_2025.csv",
    ),
    (
      [
        "https://raw.githubusercontent.com/people3k/PopulationExpansion2025/main/data/SoCaldates.csv",
        "https://raw.githubusercontent.com/people3k/PopulationExpansion2025/master/data/SoCaldates.csv",
      ],
      RAW_NA_DIR / "people3k_SoCaldates.csv",
    ),
    (
      [
        "https://raw.githubusercontent.com/people3k/PopulationExpansion2025/main/data/FinalRCDTexas3.csv",
        "https://raw.githubusercontent.com/people3k/PopulationExpansion2025/master/data/FinalRCDTexas3.csv",
      ],
      RAW_NA_DIR / "people3k_FinalRCDTexas3.csv",
    ),
    (
      [
        "https://raw.githubusercontent.com/people3k/NorthAmericaAdaptiveCap/main/data/Midwest2.csv",
        "https://raw.githubusercontent.com/people3k/NorthAmericaAdaptiveCap/master/data/Midwest2.csv",
      ],
      RAW_NA_DIR / "people3k_Midwest2.csv",
    ),
    (
      [
        "https://raw.githubusercontent.com/people3k/NorthAmericaAdaptiveCap/main/data/Milner2023CultIndex.csv",
        "https://raw.githubusercontent.com/people3k/NorthAmericaAdaptiveCap/master/data/Milner2023CultIndex.csv",
      ],
      RAW_NA_DIR / "people3k_Milner2023CultIndex.csv",
    ),
    (
      "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_counties_national.zip",
      CENSUS_RAW_DIR / "2020_Gaz_counties_national.zip",
    ),
  ]

  print("[1/5] Downloading academic GitHub & US County datasets...", flush=True)
  for urls, dest in github_files:
    try:
      sz, cached = download_file(urls, dest)
      summary[dest.name] = {"bytes": sz, "cached": cached}
      print(f"  {dest.name}: {sz:,} bytes ({'cached' if cached else 'downloaded'})", flush=True)
    except Exception as exc:
      print(f"  [WARN] {dest.name}: {exc}", flush=True)

  # 2. Verify cached NPS NRHP GeoJSON
  nrhp_path = RAW_NA_DIR / "nps_nrhp_locations.geojson"
  print("[2/5] Checking NPS NRHP Locations...", flush=True)
  if nrhp_path.exists() and nrhp_path.stat().st_size > 1_000_000:
    nrhp_gj = json.loads(nrhp_path.read_text(encoding="utf-8"))
    print(f"  nps_nrhp_locations.geojson: cached ({len(nrhp_gj.get('features', [])):,} features)", flush=True)
  else:
    nrhp_url = "https://mapservices.nps.gov/arcgis/rest/services/cultural_resources/nrhp_locations/MapServer/0"
    nrhp_gj = paginate_arcgis_layer(
      nrhp_url,
      "OBJECTID,NRIS_Refnum,RESNAME,ResType,Address,City,County,State,CertDate,NumCSite,Is_NHL,MultiName",
      arg3_page_size=2000,
    )
    nrhp_path.write_text(json.dumps(nrhp_gj, ensure_ascii=False), encoding="utf-8")
  summary["nps_nrhp_locations.geojson"] = {"features": len(nrhp_gj.get("features", []))}

  # 3. Greenland National Museum Nunniffiit Cultures (layers 0..14)
  print("[3/5] Downloading Greenland Nunniffiit Archaeological & Historical Layers...", flush=True)
  nun_path = RAW_NA_DIR / "greenland_nunniffiit_cultures.json"
  if nun_path.exists() and nun_path.stat().st_size > 500_000:
    nun_data = json.loads(nun_path.read_text(encoding="utf-8"))
    tot_n = sum(len(v) for v in nun_data.values())
    print(f"  greenland_nunniffiit_cultures.json: cached ({tot_n:,} records across {len(nun_data)} layers)", flush=True)
  else:
    culture_layers = {
      0: "Colonial",
      1: "Early Dorset",
      2: "Early Paleo Eskimo",
      3: "Eskimo Undefined",
      5: "Greenlandic Dorset",
      6: "Independence I",
      8: "Late Dorset",
      9: "Late Paleo Eskimo",
      10: "Norse",
      11: "Paleo Eskimo",
      13: "Saqqaq",
      14: "Thule",
    }
    nun_data = {}
    for lid, cname in culture_layers.items():
      url = f"https://kort.nunagis.gl/server/rest/services/Nunniffiit/Cultures/MapServer/{lid}"
      gj = paginate_arcgis_layer(url, "LOCNAME,LOCDESCRIPTION,NKAH,LATLONG", arg3_page_size=1000)
      nun_data[cname] = gj["features"]
      print(f"  Nunniffiit [{cname}]: {len(gj['features']):,} sites", flush=True)
    nun_path.write_text(json.dumps(nun_data, ensure_ascii=False), encoding="utf-8")
  summary["greenland_nunniffiit_cultures.json"] = {k: len(v) for k, v in nun_data.items()}

  # 4. Hawaii Place Names Layer 2 (7,323 features)
  print("[4/5] Downloading Hawaii Statewide GIS HistoricCultural Place Names (Layer 2)...", flush=True)
  hi_pn_path = RAW_HP_DIR / "hawaii_place_names.geojson"
  if hi_pn_path.exists() and hi_pn_path.stat().st_size > 100_000:
    hi_gj = json.loads(hi_pn_path.read_text(encoding="utf-8"))
    print(f"  hawaii_place_names.geojson: cached ({len(hi_gj.get('features', [])):,} features)", flush=True)
  else:
    hi_url = "https://geodata.hawaii.gov/arcgis/rest/services/HistoricCultural/MapServer/2"
    hi_gj = paginate_arcgis_layer(
      hi_url,
      "objectid,feature_id,feature_name,feature_class,county_name,prim_lat_dec,prim_long_dec",
      arg3_page_size=1000,
    )
    hi_pn_path.write_text(json.dumps(hi_gj, ensure_ascii=False), encoding="utf-8")
    print(f"  hawaii_place_names.geojson: saved {len(hi_gj['features']):,} features", flush=True)
  summary["hawaii_place_names.geojson"] = {"features": len(hi_gj.get("features", []))}

  # 5. Statistics Canada 2021 Simplified Boundaries: Layer 4 (CD), Layer 8 (DPL), Layer 9 (CSD)
  print("[5/5] Downloading StatCan 2021 Simplified CD, DPL, and CSD GeoJSONs...", flush=True)
  statcan_layers = [
    (4, "CDUID,CDNAME,CDTYPE,PRUID,LANDAREA", "statcan_2021_cd.geojson"),
    (8, "DPLUID,DGUID,DPLNAME,DPLTYPE,PRUID,LANDAREA", "statcan_2021_dpl.geojson"),
    (9, "CSDUID,DGUID,CSDNAME,CSDTYPE,PRUID,LANDAREA", "statcan_2021_csd.geojson"),
  ]
  for lid, flds, fname in statcan_layers:
    out_p = CENSUS_RAW_DIR / fname
    if out_p.exists() and out_p.stat().st_size > 10_000:
      gj = json.loads(out_p.read_text(encoding="utf-8"))
      print(f"  {fname}: cached ({len(gj.get('features', [])):,} features)", flush=True)
    else:
      url = f"https://geo.statcan.gc.ca/geo_wa/rest/services/2021/Cartographic_boundary_files/MapServer/{lid}"
      gj = paginate_arcgis_layer(
        url,
        flds,
        arg3_page_size=1000,
        arg4_max_offset=0.05,
        arg5_geom_prec=4,
      )
      out_p.write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")
      print(f"  {fname}: saved {len(gj['features']):,} features", flush=True)
    summary[fname] = {"features": len(gj.get("features", []))}

  (THIS_DIR / "raw_sources_manifest.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
  )
  print("ALL DOWNLOADS COMPLETE.", flush=True)


if __name__ == "__main__":
  main()
