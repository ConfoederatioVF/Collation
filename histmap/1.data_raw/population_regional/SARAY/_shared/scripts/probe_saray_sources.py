"""Scaffolds Operation Viscount Project SARAY directory tree and probes primary
archaeological, historical, and census data endpoints for Central Asia."""

import os
import re
import shutil
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SARAY_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "SARAY")
CASTLE_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE")

CHAPTER_DIRS = [
  "1.ancient_and_classical/1.prehistoric_central_asian_steppe_and_oases",
  "1.ancient_and_classical/2.scythian_saka_and_classical_oasis_states",
  "2.mediaeval_and_khanates/1.turkic_migrations_and_islamisation_turan",
  "2.mediaeval_and_khanates/2.mongol_conquest_and_timurid_central_asia",
  "2.mediaeval_and_khanates/3.uzbek_khanates_and_kazakh_hordes",
  "3.imperial_and_soviet/1.russian_conquest_imperial_turkestan_and_steppe",
  "3.imperial_and_soviet/2.russian_civil_war_basmachi_and_early_soviet",
  "3.imperial_and_soviet/3.post_war_soviet_central_asian_republics",
  "4.modern_censuses/1.post_soviet_central_asia",
]

HEADERS = {
  "User-Agent": "SVEA-OperationViscount-SARAY/1.0 (academic research; contact: austkaeztchen@confoederatio.org)"
}


def scaffold():
  for sub in [
    "_shared/scripts",
    "_shared/_gis_cache/chapter_subregions",
    "_shared/_census_cache",
    "_shared/sites_saray_central_asia/0.raw_data",
    "_shared/sites_saray_central_asia/config",
    "_shared/sites_saray_central_asia/geojson",
    "_shared/sites_saray_central_asia/1.kriged_rasters",
    "_shared/sites_saray_central_asia/2.population_rasters",
    "_shared/sites_saray_central_asia/diagnostics_visual",
    "figures",
  ]:
    os.makedirs(os.path.join(SARAY_DIR, sub), exist_ok=True)

  for ch in CHAPTER_DIRS:
    for leaf in ["figures", "papers", "overlays_qa"]:
      os.makedirs(os.path.join(SARAY_DIR, ch, leaf), exist_ok=True)

  for d in ["_shared/template", "_shared/fonts"]:
    src = os.path.join(CASTLE_DIR, d)
    dst = os.path.join(SARAY_DIR, d)
    if os.path.exists(src) and not os.path.exists(dst):
      shutil.copytree(src, dst)

  for fn in ["intellte.cls", "crd-mla-numeric.csl", "crd_logo.png", "intellte-sample.bib"]:
    src = os.path.join(CASTLE_DIR, fn)
    dst = os.path.join(SARAY_DIR, fn)
    if os.path.exists(src) and not os.path.exists(dst):
      shutil.copy2(src, dst)
  print("Scaffolded SARAY 9-chapter directory tree cleanly.")


def probe():
  urls = [
    ("CAAL_db_page", "https://uclcaal.org/database/"),
    ("AlThurayya_tree", "https://api.github.com/repos/althurayya/althurayya.github.io/git/trees/master?recursive=1"),
    ("XRONOS_kz", "https://xronos.ch/api/v1/data?country=KZ"),
    ("XRONOS_uz", "https://xronos.ch/api/v1/data?country=UZ"),
    ("XRONOS_tm", "https://xronos.ch/api/v1/data?country=TM"),
    ("XRONOS_kg", "https://xronos.ch/api/v1/data?country=KG"),
    ("XRONOS_tj", "https://xronos.ch/api/v1/data?country=TJ"),
    ("Demoscope_1897", "https://www.demoscope.ru/weekly/ssp/emp_lan_97_uezd.php"),
    ("Demoscope_1959_kz", "https://www.demoscope.ru/weekly/ssp/ussr59_reg2.php"),
    ("PopStat_kz", "http://pop-stat.mashke.org/kazakhstan-cities.htm"),
    ("PopStat_uz", "http://pop-stat.mashke.org/uzbekistan-cities.htm"),
    ("PopStat_kg", "http://pop-stat.mashke.org/kyrgyzstan-cities.htm"),
    ("PopStat_tj", "http://pop-stat.mashke.org/tajikistan-cities.htm"),
    ("PopStat_tm", "http://pop-stat.mashke.org/turkmenistan-cities.htm"),
    ("GeoNames_KZ", "https://download.geonames.org/export/dump/KZ.zip"),
  ]
  for label, u in urls:
    try:
      if label == "GeoNames_KZ":
        r = requests.head(u, headers=HEADERS, timeout=15, allow_redirects=True)
        print(f"  {label}: HTTP {r.status_code} | cl={r.headers.get('content-length')}")
      else:
        r = requests.get(u, headers=HEADERS, timeout=20, allow_redirects=True)
        extra = ""
        if label == "CAAL_db_page" and r.status_code == 200:
          links = sorted(set(re.findall(r'https?://[^\s"\'<>]+(?:arches|caal|database|api)[^\s"\'<>]*', r.text, flags=re.I)))
          extra = f" | links={links[:8]}"
        elif label == "AlThurayya_tree" and r.status_code == 200:
          tr = r.json().get("tree", [])
          gjs = [t["path"] for t in tr if t["path"].endswith(".geojson")]
          extra = f" | geojsons={len(gjs)} sample={gjs[:5]}"
        print(f"  {label}: HTTP {r.status_code} | len={len(r.content):,}{extra}")
    except Exception as e:
      print(f"  {label}: ERR {e}")


if __name__ == "__main__":
  scaffold()
  probe()
