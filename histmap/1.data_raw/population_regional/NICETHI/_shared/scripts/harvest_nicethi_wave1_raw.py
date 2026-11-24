"""Stage C Wave 1 Raw Authoritative Census & Coordinate Index Harvester for Operation Viscount Project NICETHI.

Downloads and caches full-row primary census tables and secondary coordinate indexes across all 54 NICETHI
jurisdictions (<= 4 concurrent workers, polite throttling, zero LIMIT/Top-N caps):
  1. CityPopulation.de official national statistical agency (NSO) census mirrors (52 country/territory /cities/ pages
     plus non-intra-municipal provincial/regional settlement tables for ZAF, CIV, NER, KEN, MUS).
  2. UNSD Demographic Yearbook Table 8 (`unsd_citypopulation_year_both.csv`).
  3. GeoNames country dumps (`<ISO2>.zip`) strictly for secondary coordinate geocoding & homonym audit.
  4. Africapolis 2024 (`Africapolis_agglomeration_2024.xlsx`) & B.R. Mitchell A4.json & INSEE 2022 (`974` Reunion).
"""

import concurrent.futures
import os
import shutil
import time
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
NI_SHARED = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "NICETHI", "_shared")
RAW_CACHE = os.path.join(NI_SHARED, "settlement_sources", "_raw_cache")
CITYPOP_DIR = os.path.join(RAW_CACHE, "citypop")
GEONAMES_DIR = os.path.join(RAW_CACHE, "geonames")
os.makedirs(CITYPOP_DIR, exist_ok=True)
os.makedirs(GEONAMES_DIR, exist_ok=True)

HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SVEA-OperationViscount-NICETHI/1.0 (academic historical demography)"
}

# All 52 NICETHI countries/territories with CityPopulation.de urban/settlement tables
# Format: (tag, iso3, url, nso_label)
CITYPOP_MAIN_PAGES = [
  ("BEN_cities", "BEN", "https://www.citypopulation.de/en/benin/cities/", "INStaD Benin Censuses (RGPH 1979-2013)"),
  ("CIV_cities", "CIV", "https://www.citypopulation.de/en/ivorycoast/cities/", "INS Cote d'Ivoire Censuses (RGPH 1975-2021)"),
  ("GMB_cities", "GMB", "https://www.citypopulation.de/en/gambia/cities/", "GBoS The Gambia Censuses (1993-2013)"),
  ("GHA_cities", "GHA", "https://www.citypopulation.de/en/ghana/cities/", "GSS Ghana Censuses (1970-2021)"),
  ("GIN_cities", "GIN", "https://www.citypopulation.de/en/guinea/cities/", "INS Guinea Censuses (RGPH 1983-2014)"),
  ("GNB_cities", "GNB", "https://www.citypopulation.de/en/guineabissau/cities/", "INE Guinea-Bissau Censuses (RGPH 1979-2009)"),
  ("LBR_cities", "LBR", "https://www.citypopulation.de/en/liberia/cities/", "LISGIS Liberia Censuses (1974-2022)"),
  ("NGA_cities", "NGA", "https://www.citypopulation.de/en/nigeria/cities/", "NPC / NBS Nigeria Censuses (1991-2006)"),
  ("SEN_cities", "SEN", "https://www.citypopulation.de/en/senegal/cities/", "ANSD Senegal Censuses (RGPH 1976-2023)"),
  ("SLE_cities", "SLE", "https://www.citypopulation.de/en/sierraleone/cities/", "Stats SL Sierra Leone Censuses (1974-2015)"),
  ("TGO_cities", "TGO", "https://www.citypopulation.de/en/togo/cities/", "INSEED Togo Censuses (RGPH 1981-2022)"),
  ("BFA_cities", "BFA", "https://www.citypopulation.de/en/burkinafaso/cities/", "INSD Burkina Faso Censuses (RGPH 1985-2019)"),
  ("TCD_cities", "TCD", "https://www.citypopulation.de/en/chad/cities/", "INSEED Chad Censuses (RGPH 1993-2009)"),
  ("MLI_cities", "MLI", "https://www.citypopulation.de/en/mali/cities/", "INSTAT Mali Censuses (RGPH 1976-2009)"),
  ("MRT_cities", "MRT", "https://www.citypopulation.de/en/mauritania/cities/", "ANSADE Mauritania Censuses (RGPH 1977-2023)"),
  ("NER_cities", "NER", "https://www.citypopulation.de/en/niger/cities/", "INS Niger Censuses (RGPH 1977-2012)"),
  ("AGO_cities", "AGO", "https://www.citypopulation.de/en/angola/cities/", "INE Angola Censuses (1970-2014)"),
  ("CMR_cities", "CMR", "https://www.citypopulation.de/en/cameroon/cities/", "BUCREP Cameroon Censuses (RGPH 1976-2005)"),
  ("CAF_cities", "CAF", "https://www.citypopulation.de/en/centralafrica/cities/", "ICASEES Central African Republic Censuses (1975-2003)"),
  ("COG_cities", "COG", "https://www.citypopulation.de/en/congo/cities/", "INS Congo Censuses (RGPH 1984-2023)"),
  ("COD_cities", "COD", "https://www.citypopulation.de/en/drcongo/cities/", "INS DR Congo Censuses (1984) & Official Estimates"),
  ("GNQ_cities", "GNQ", "https://www.citypopulation.de/en/equatorialguinea/cities/", "INEGE Equatorial Guinea Censuses (1983-2015)"),
  ("GAB_cities", "GAB", "https://www.citypopulation.de/en/gabon/cities/", "DGS Gabon Censuses (RGPL 1993-2013)"),
  ("STP_cities", "STP", "https://www.citypopulation.de/en/saotome/cities/", "INE Sao Tome and Principe Censuses (1991-2012)"),
  ("DJI_cities", "DJI", "https://www.citypopulation.de/en/djibouti/cities/", "INSTAD Djibouti Censuses (2009-2024)"),
  ("ERI_cities", "ERI", "https://www.citypopulation.de/en/eritrea/cities/", "NSO Eritrea / 1984 Census & Official Estimates"),
  ("ETH_cities", "ETH", "https://www.citypopulation.de/en/ethiopia/cities/", "CSA / ESS Ethiopia Censuses (1984-2007) & Projections"),
  ("SOM_cities", "SOM", "https://www.citypopulation.de/en/somalia/cities/", "SNBS Somalia & Somaliland Census/Estimates (1975-2014)"),
  ("SSD_cities", "SSD", "https://www.citypopulation.de/en/southsudan/cities/", "SSNBS / CBS South Sudan Censuses (1973-2008)"),
  ("SDN_cities", "SDN", "https://www.citypopulation.de/en/sudan/cities/", "CBS Sudan Censuses (1973-2008)"),
  ("BDI_cities", "BDI", "https://www.citypopulation.de/en/burundi/cities/", "INSBU / ISTEEBU Burundi Censuses (1979-2008)"),
  ("KEN_cities", "KEN", "https://www.citypopulation.de/en/kenya/cities/", "KNBS Kenya Censuses (1969-2019)"),
  ("RWA_cities", "RWA", "https://www.citypopulation.de/en/rwanda/cities/", "NISR Rwanda Censuses (1978-2022)"),
  ("TZA_cities", "TZA", "https://www.citypopulation.de/en/tanzania/cities/", "NBS Tanzania & OCGS Zanzibar Censuses (1978-2022)"),
  ("UGA_cities", "UGA", "https://www.citypopulation.de/en/uganda/cities/", "UBOS Uganda Censuses (1969-2024)"),
  ("MWI_cities", "MWI", "https://www.citypopulation.de/en/malawi/cities/", "NSO Malawi Censuses (1977-2018)"),
  ("MOZ_cities", "MOZ", "https://www.citypopulation.de/en/mozambique/cities/", "INE Mozambique Censuses (1980-2017)"),
  ("ZMB_cities", "ZMB", "https://www.citypopulation.de/en/zambia/cities/", "ZamStats Zambia Censuses (1980-2022)"),
  ("ZWE_cities", "ZWE", "https://www.citypopulation.de/en/zimbabwe/cities/", "ZIMSTAT Zimbabwe Censuses (1982-2022)"),
  ("BWA_cities", "BWA", "https://www.citypopulation.de/en/botswana/cities/", "Statistics Botswana Censuses (1981-2022)"),
  ("SWZ_cities", "SWZ", "https://www.citypopulation.de/en/eswatini/cities/", "CSO Eswatini Censuses (1976-2017)"),
  ("LSO_cities", "LSO", "https://www.citypopulation.de/en/lesotho/cities/", "BOS Lesotho Censuses (1976-2016)"),
  ("NAM_cities", "NAM", "https://www.citypopulation.de/en/namibia/cities/", "NSA Namibia Censuses (1991-2023)"),
  ("ZAF_cities", "ZAF", "https://www.citypopulation.de/en/southafrica/cities/", "Stats SA South Africa Censuses (1996-2022)"),
  ("CPV_cities", "CPV", "https://www.citypopulation.de/en/capeverde/cities/", "INE Cabo Verde Censuses (1990-2021)"),
  ("COM_cities", "COM", "https://www.citypopulation.de/en/comoros/cities/", "INSEED Comoros Censuses (1980-2017)"),
  ("MDG_cities", "MDG", "https://www.citypopulation.de/en/madagascar/cities/", "INSTAT Madagascar Censuses (1975-2018)"),
  ("MUS_cities", "MUS", "https://www.citypopulation.de/en/mauritius/cities/", "Statistics Mauritius Censuses (1983-2022)"),
  ("MYT_cities", "MYT", "https://www.citypopulation.de/en/france/cities/mayotte/", "INSEE Mayotte Censuses (1978-2017)"),
  ("REU_cities", "REU", "https://www.citypopulation.de/en/france/cities/reunion/", "INSEE Reunion Censuses (1982-2023)"),
  ("SYC_cities", "SYC", "https://www.citypopulation.de/en/seychelles/cities/", "NBS Seychelles Censuses (1987-2022)"),
  ("SHN_main",   "SHN", "https://www.citypopulation.de/en/sthelena/", "St Helena Statistics Office Censuses (1976-2021)"),
]

# Additional full-row provincial/regional settlement tables (strictly excluding single-city ward/arrondissement pages)
CITYPOP_REGIONAL_PAGES = [
  # South Africa 9 provinces (Main Places 2001, 2011)
  ("ZAF_westerncape", "ZAF", "https://www.citypopulation.de/en/southafrica/westerncape/", "Stats SA Western Cape Main Places"),
  ("ZAF_easterncape", "ZAF", "https://www.citypopulation.de/en/southafrica/easterncape/", "Stats SA Eastern Cape Main Places"),
  ("ZAF_northerncape", "ZAF", "https://www.citypopulation.de/en/southafrica/northerncape/", "Stats SA Northern Cape Main Places"),
  ("ZAF_freestate", "ZAF", "https://www.citypopulation.de/en/southafrica/freestate/", "Stats SA Free State Main Places"),
  ("ZAF_kwazulunatal", "ZAF", "https://www.citypopulation.de/en/southafrica/kwazulunatal/", "Stats SA KwaZulu-Natal Main Places"),
  ("ZAF_northwest", "ZAF", "https://www.citypopulation.de/en/southafrica/northwest/", "Stats SA North West Main Places"),
  ("ZAF_gauteng", "ZAF", "https://www.citypopulation.de/en/southafrica/gauteng/", "Stats SA Gauteng Main Places"),
  ("ZAF_mpumalanga", "ZAF", "https://www.citypopulation.de/en/southafrica/mpumalanga/", "Stats SA Mpumalanga Main Places"),
  ("ZAF_limpopo", "ZAF", "https://www.citypopulation.de/en/southafrica/limpopo/", "Stats SA Limpopo Main Places"),
  # Cote d'Ivoire 13 districts (excl. Abidjan intra-municipal communes)
  ("CIV_bassassandra", "CIV", "https://www.citypopulation.de/en/ivorycoast/bassassandra/", "INS Cote d'Ivoire Bas-Sassandra Localities"),
  ("CIV_comoe", "CIV", "https://www.citypopulation.de/en/ivorycoast/comoe/", "INS Cote d'Ivoire Comoe Localities"),
  ("CIV_denguele", "CIV", "https://www.citypopulation.de/en/ivorycoast/denguele/", "INS Cote d'Ivoire Denguele Localities"),
  ("CIV_gohdjiboua", "CIV", "https://www.citypopulation.de/en/ivorycoast/gohdjiboua/", "INS Cote d'Ivoire Goh-Djiboua Localities"),
  ("CIV_lacs", "CIV", "https://www.citypopulation.de/en/ivorycoast/lacs/", "INS Cote d'Ivoire Lacs Localities"),
  ("CIV_lagunes", "CIV", "https://www.citypopulation.de/en/ivorycoast/lagunes/", "INS Cote d'Ivoire Lagunes Localities"),
  ("CIV_montagnes", "CIV", "https://www.citypopulation.de/en/ivorycoast/montagnes/", "INS Cote d'Ivoire Montagnes Localities"),
  ("CIV_sassandramarahoue", "CIV", "https://www.citypopulation.de/en/ivorycoast/sassandramarahoue/", "INS Cote d'Ivoire Sassandra-Marahoue Localities"),
  ("CIV_savanes", "CIV", "https://www.citypopulation.de/en/ivorycoast/savanes/", "INS Cote d'Ivoire Savanes Localities"),
  ("CIV_valleedubandama", "CIV", "https://www.citypopulation.de/en/ivorycoast/valleedubandama/", "INS Cote d'Ivoire Vallee du Bandama Localities"),
  ("CIV_woroba", "CIV", "https://www.citypopulation.de/en/ivorycoast/woroba/", "INS Cote d'Ivoire Woroba Localities"),
  ("CIV_yamoussoukro", "CIV", "https://www.citypopulation.de/en/ivorycoast/yamoussoukro/", "INS Cote d'Ivoire Yamoussoukro Localities"),
  ("CIV_zanzan", "CIV", "https://www.citypopulation.de/en/ivorycoast/zanzan/", "INS Cote d'Ivoire Zanzan Localities"),
  # Niger 7 regions (excl. Niamey intra-municipal)
  ("NER_agadez", "NER", "https://www.citypopulation.de/en/niger/agadez/", "INS Niger Agadez Localities"),
  ("NER_diffa", "NER", "https://www.citypopulation.de/en/niger/diffa/", "INS Niger Diffa Localities"),
  ("NER_dosso", "NER", "https://www.citypopulation.de/en/niger/dosso/", "INS Niger Dosso Localities"),
  ("NER_maradi", "NER", "https://www.citypopulation.de/en/niger/maradi/", "INS Niger Maradi Localities"),
  ("NER_tahoua", "NER", "https://www.citypopulation.de/en/niger/tahoua/", "INS Niger Tahoua Localities"),
  ("NER_tillaberi", "NER", "https://www.citypopulation.de/en/niger/tillaberi/", "INS Niger Tillaberi Localities"),
  ("NER_zinder", "NER", "https://www.citypopulation.de/en/niger/zinder/", "INS Niger Zinder Localities"),
  # Kenya 7 provinces (excl. Nairobi intra-municipal)
  ("KEN_central", "KEN", "https://www.citypopulation.de/en/kenya/central/", "KNBS Kenya Central Urban Centers"),
  ("KEN_coast", "KEN", "https://www.citypopulation.de/en/kenya/coast/", "KNBS Kenya Coast Urban Centers"),
  ("KEN_eastern", "KEN", "https://www.citypopulation.de/en/kenya/eastern/", "KNBS Kenya Eastern Urban Centers"),
  ("KEN_northeastern", "KEN", "https://www.citypopulation.de/en/kenya/northeastern/", "KNBS Kenya North Eastern Urban Centers"),
  ("KEN_nyanza", "KEN", "https://www.citypopulation.de/en/kenya/nyanza/", "KNBS Kenya Nyanza Urban Centers"),
  ("KEN_riftvalley", "KEN", "https://www.citypopulation.de/en/kenya/riftvalley/", "KNBS Kenya Rift Valley Urban Centers"),
  ("KEN_western", "KEN", "https://www.citypopulation.de/en/kenya/western/", "KNBS Kenya Western Urban Centers"),
  # Mauritius Rodrigues
  ("MUS_rodrigues", "MUS", "https://www.citypopulation.de/en/mauritius/rodrigues/", "Statistics Mauritius Rodrigues Regions"),
]

# All 54 ISO2 codes for GeoNames secondary coordinate geocoding
ISO2_LIST = [
  "BJ", "CI", "GM", "GH", "GN", "GW", "LR", "NG", "SN", "SL", "TG", "BF",
  "TD", "ML", "MR", "NE",
  "AO", "CM", "CF", "CG", "CD", "GQ", "GA", "ST",
  "DJ", "ER", "ET", "SO", "SS", "SD",
  "BI", "KE", "RW", "TZ", "UG",
  "MW", "MZ", "ZM", "ZW",
  "BW", "SZ", "LS", "NA", "ZA",
  "CV", "KM", "MG", "MU", "YT", "RE", "SC", "SH", "IO", "TF"
]


def fetch_file(url, dest, min_bytes=500, timeout=45):
  if os.path.exists(dest) and os.path.getsize(dest) >= min_bytes:
    return "cached"
  for att in range(3):
    try:
      r = requests.get(url, headers=HEADERS, timeout=timeout)
      if r.status_code == 200 and len(r.content) >= min_bytes:
        with open(dest, "wb") as fh:
          fh.write(r.content)
        return "ok"
      if r.status_code in (429, 502, 503, 504):
        time.sleep(3 * (att + 1))
        continue
      return f"http_{r.status_code}"
    except Exception as e:
      if att == 2:
        return f"err:{str(e)[:60]}"
      time.sleep(2 * (att + 1))
  return "fail"


def main():
  # 1. Stage local UNSD + GeoNames cities500 + INSEE 2022 into _raw_cache if available in JAGUAR
  jag_raw = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JAGUAR", "_shared", "settlement_sources", "raw")
  for fn, fallback_url in [
    ("unsd_citypopulation_year_both.csv", "https://raw.githubusercontent.com/datasets/population-city/master/data/unsd-citypopulation-year-both.csv"),
    ("supplemental_geonames_cities500.zip", "https://download.geonames.org/export/dump/cities500.zip"),
    ("caribbean_insee_populations_legales_2022.zip", "https://www.insee.fr/fr/statistiques/fichier/8290591/ensemble.zip"),
  ]:
    dst = os.path.join(RAW_CACHE, fn)
    if not os.path.exists(dst) or os.path.getsize(dst) < 1000:
      src = os.path.join(jag_raw, fn)
      if os.path.exists(src) and os.path.getsize(src) > 1000:
        shutil.copy2(src, dst)
        print(f"[COPY] {fn} from JAGUAR ({os.path.getsize(dst):,} B)", flush=True)
      else:
        st = fetch_file(fallback_url, dst, timeout=180)
        print(f"[DL] {fn}: {st}", flush=True)

  # 2. Download all CityPopulation pages with max_workers=4 (polite throttle)
  all_cp = CITYPOP_MAIN_PAGES + CITYPOP_REGIONAL_PAGES
  print(f"[CITYPOP] Fetching {len(all_cp)} official NSO census mirror pages (<=4 workers)...", flush=True)

  def _dl_cp(item):
    tag, iso3, url, label = item
    dest = os.path.join(CITYPOP_DIR, f"{tag}.html")
    st = fetch_file(url, dest, min_bytes=1000, timeout=45)
    time.sleep(0.25)
    return tag, st

  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    res = list(ex.map(_dl_cp, all_cp))
  ok_cnt = sum(1 for _, s in res if s in ("ok", "cached"))
  fails = [(t, s) for t, s in res if s not in ("ok", "cached")]
  print(f"[CITYPOP] Complete: {ok_cnt}/{len(all_cp)} ok/cached; fails={fails}", flush=True)

  # 3. Download GeoNames country dumps for secondary coordinate geocoding (<=4 workers)
  print(f"[GEONAMES] Fetching {len(ISO2_LIST)} country coordinate dumps (<=4 workers)...", flush=True)

  def _dl_gn(cc):
    dest = os.path.join(GEONAMES_DIR, f"{cc}.zip")
    st = fetch_file(f"https://download.geonames.org/export/dump/{cc}.zip", dest, min_bytes=200, timeout=120)
    time.sleep(0.15)
    return cc, st

  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    gn_res = list(ex.map(_dl_gn, ISO2_LIST))
  gn_ok = sum(1 for _, s in gn_res if s in ("ok", "cached"))
  gn_fails = [(c, s) for c, s in gn_res if s not in ("ok", "cached")]
  print(f"[GEONAMES] Complete: {gn_ok}/{len(ISO2_LIST)} ok/cached; fails={gn_fails}", flush=True)


if __name__ == "__main__":
  main()
