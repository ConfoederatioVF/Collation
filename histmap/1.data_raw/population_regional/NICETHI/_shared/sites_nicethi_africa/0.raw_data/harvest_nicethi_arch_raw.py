"""Stage B Multi-Repository Raw Archaeological Harvester for Project NICETHI (Sub-Saharan Africa & WIO/Atlantic Islands).

Downloads open-access, peer-reviewed and institutional African archaeological repositories into
`sites_nicethi_africa/0.raw_data/` with zero crowd-scraped (Wikipedia/Wikidata/OSM) endpoints.
"""

import csv
import gzip
import io
import json
import os
import time
import zipfile
import requests

RAW_DIR = os.path.dirname(os.path.abspath(__file__))
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OperationViscount-NICETHI/2.0"}

NICETHI_ISO2 = [
    # West Africa
    "BJ", "BF", "CV", "CI", "GM", "GH", "GN", "GW", "LR", "ML", "MR", "NE", "NG", "SN", "SL", "TG",
    # Central Africa
    "AO", "CM", "CF", "TD", "CG", "CD", "GQ", "GA", "ST",
    # Horn & East Africa
    "BI", "DJ", "ER", "ET", "KE", "RW", "SO", "SS", "SD", "TZ", "UG",
    # Southern Africa & Madagascar / WIO / Atlantic Islands
    "BW", "KM", "SZ", "LS", "MG", "MW", "MU", "YT", "MZ", "NA", "RE", "SH", "SC", "ZA", "ZM", "ZW",
]


def download_file(url, dest_path, timeout=90, max_mb=600):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 64:
        print(f"  [SKIP] {os.path.basename(dest_path)} ({os.path.getsize(dest_path):,} B)", flush=True)
        return True
    try:
        with requests.get(url, headers=HDR, timeout=timeout, stream=True, allow_redirects=True) as r:
            if r.status_code != 200:
                print(f"  [HTTP {r.status_code}] {os.path.basename(dest_path)} <- {url[:80]}", flush=True)
                return False
            tmp = dest_path + ".part"
            tot = 0
            lim = max_mb * 1024 * 1024
            with open(tmp, "wb") as fh:
                for chunk in r.iter_content(chunk_size=131072):
                    if chunk:
                        fh.write(chunk)
                        tot += len(chunk)
                        if tot > lim:
                            fh.close()
                            os.remove(tmp)
                            print(f"  [TOO_LARGE>{max_mb}MB] {os.path.basename(dest_path)}", flush=True)
                            return False
            os.replace(tmp, dest_path)
            print(f"  [OK] {os.path.basename(dest_path)} ({tot:,} B)", flush=True)
            return True
    except Exception as e:
        print(f"  [ERR] {os.path.basename(dest_path)}: {str(e)[:100]}", flush=True)
        return False


def harvest_xronos():
    print("\n=== 1. XRONOS Radiocarbon API (52 NICETHI countries) ===", flush=True)
    out_path = os.path.join(RAW_DIR, "xronos_nicethi_all.json")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        data = json.load(open(out_path, "r", encoding="utf-8"))
        print(f"  [SKIP] xronos_nicethi_all.json already has {len(data):,} records", flush=True)
        return
    all_rows = []
    by_iso = {}
    for iso in NICETHI_ISO2:
        try:
            r = requests.get("https://xronos.ch/api/v1/data", params={"query_country": iso}, headers=HDR, timeout=45)
            if r.status_code == 200 and r.text.strip() not in ("", "null", "[]"):
                arr = r.json()
                if isinstance(arr, list) and arr:
                    for item in arr:
                        if isinstance(item, dict):
                            item["_query_iso2"] = iso
                            all_rows.append(item)
                    by_iso[iso] = len(arr)
                    print(f"  XRONOS {iso}: {len(arr):,} records", flush=True)
        except Exception as e:
            print(f"  XRONOS {iso}: ERR {str(e)[:70]}", flush=True)
        time.sleep(0.15)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(all_rows, fh)
    print(f"  [OK] XRONOS total: {len(all_rows):,} records across {len(by_iso)} countries", flush=True)


def harvest_github_and_direct():
    print("\n=== 2. Direct Institutional & Scholarly Repositories ===", flush=True)
    direct = [
        # Central Africa (RMCA Tervuren / Seidensticker / BantuFirst / Wotzka / Bostoen)
        ("adrac_central_africa.csv", "https://raw.githubusercontent.com/dirkseidensticker/aDRAC/master/aDRAC.csv"),
        ("ascac_pottery_distribution.geojson", "https://raw.githubusercontent.com/dirkseidensticker/aSCAC/master/pottery_distribution.geojson"),
        ("ascac_bayes_phases.csv", "https://raw.githubusercontent.com/dirkseidensticker/aSCAC/master/BayesPhases.csv"),
        ("bantufirst_bf.csv", "https://raw.githubusercontent.com/dirkseidensticker/BantuFirst_Shiny-Archaeology/master/bf.csv"),
        ("bantufirst_bf_chrono.csv", "https://raw.githubusercontent.com/dirkseidensticker/BantuFirst_Shiny-Archaeology/master/bf_chrono.csv"),
        ("bantufirst_s.csv", "https://raw.githubusercontent.com/dirkseidensticker/BantuFirst_Shiny-Archaeology/master/s.csv"),
        ("bandundu_survey_finds.xlsx", "https://raw.githubusercontent.com/dirkseidensticker/Bandundu_BFbookChapter/master/Tab_SurveyFinds.xlsx"),
        # Southern Africa (SARD Loftus et al. + IntChron SARD + SA Iron Age Burials)
        ("sard_mar2021_14c.csv", "https://raw.githubusercontent.com/emmaloftus/Southern-African-Radiocarbon-Database/main/SARD_Mar2021_14C.csv"),
        ("sard_mar2021.xlsx", "https://raw.githubusercontent.com/emmaloftus/Southern-African-Radiocarbon-Database/main/SARD_Mar2021.xlsx"),
        ("intchron_sard_index.json", "https://intchron.org/archive/SARD/SARD/index.json"),
        ("sa_iron_age_burials.xlsx", "https://raw.githubusercontent.com/emmaloftus/South-African-Iron-Age-burials/main/SOM_Feb2025_submission.xlsx"),
        # East Africa (KITE East Africa 2025 + v2.1 Harvard Dataverse)
        ("kite_east_africa_2025.tab", "https://dataverse.harvard.edu/api/access/datafile/10987998"),
        ("kite_east_africa_v21.csv", "https://dataverse.harvard.edu/api/access/datafile/2805729"),
        # West Africa & Pan-African (p3k14c GitHub + Cerasoni West Africa Figshare)
        ("p3k14c_western_africa_sites.csv", "https://raw.githubusercontent.com/people3k/p3k14c/main/inst/western_africa_sites.csv"),
        ("p3k14c_scrubbed_fuzzed.csv", "https://raw.githubusercontent.com/people3k/p3k14c/main/inst/p3k14c_scrubbed_fuzzed.csv"),
        # Pleiades & Al-Thurayya (Nubia, Kush, Meroe, Axum, Red Sea, Horn, Swahili, Sahel)
        ("pleiades_places_latest.csv.gz", "https://atlantides.org/downloads/pleiades/dumps/pleiades-places-latest.csv.gz"),
        ("althurayya_places.geojson", "https://raw.githubusercontent.com/althurayya/althurayya.github.io/master/master/places.geojson"),
        # UNESCO World Heritage List (official XML/GeoRSS)
        ("unesco_whc_sites.xml", "https://whc.unesco.org/en/list/xml/"),
    ]
    for fn, url in direct:
        ok = download_file(url, os.path.join(RAW_DIR, fn))
        if not ok and "/main/" in url:
            download_file(url.replace("/main/", "/master/"), os.path.join(RAW_DIR, fn))
        elif not ok and "/master/" in url:
            download_file(url.replace("/master/", "/main/"), os.path.join(RAW_DIR, fn))


def harvest_figshare():
    print("\n=== 3. Figshare Scholarly African Archaeological Datasets ===", flush=True)
    fig_ids = [
        (16895959, "cerasoni_west_africa", [".csv"]),
        (33341577, "letaba_southern_africa", [".xlsx"]),
    ]
    for fid, prefix, exts in fig_ids:
        try:
            r = requests.get(f"https://api.figshare.com/v2/articles/{fid}", headers=HDR, timeout=20)
            if r.status_code != 200:
                continue
            for f in r.json().get("files", []):
                nm = f["name"]
                if any(nm.lower().endswith(e) for e in exts):
                    dest = os.path.join(RAW_DIR, f"{prefix}_{nm}")
                    download_file(f["download_url"], dest)
        except Exception as e:
            print(f"  FIG {fid} ERR: {e}", flush=True)


def harvest_zenodo():
    print("\n=== 4. Zenodo Scholarly African Archaeological Datasets ===", flush=True)
    # (record_id, prefix, file_filter_substring_or_None, max_mb)
    z_specs = [
        (7669784, "roceeh_road", "Kandel_etal_2023.zip", 200),
        (3689716, "medafricarbon", ".zip", 20),
        (5728242, "lasoles_sa", ".csv", 20),
        (5741352, "bulbula_ethiopia", ".xlsx", 10),
        (8402444, "ona_adi_tigrai", ".xlsx", 10),
        (7738248, "mezber_tigrai", ".xlsx", 10),
        (5047577, "hixon_madagascar", ".xlsx", 20),
        (7811782, "inhambane_mozambique", ".zip", 50),
        (6676301, "chicumbane_mozambique", ".xlsx", 10),
        (15206951, "west_africa_pottery", ".xlsx", 10),
        (17183951, "west_africa_pxrf", ".csv", 10),
        (3906082, "safe_gazetteer", "gazetteer.geojson", 20),
        (7678852, "marmarica_ne_africa", ".zip", 20),
        (14792429, "east_africa_isotopes", ".zip", 50),
        (10017377, "geelbek_sa", "DATES", 10),
        (11099773, "borderscape_sudan", ".zip", 550),
    ]
    for zid, prefix, flt, max_mb in z_specs:
        try:
            r = requests.get(f"https://zenodo.org/api/records/{zid}", headers=HDR, timeout=20)
            if r.status_code != 200:
                print(f"  Z {zid}: HTTP {r.status_code}", flush=True)
                continue
            for f in r.json().get("files", []):
                key = f["key"]
                if flt and flt.lower() not in key.lower():
                    continue
                safe_key = key.replace("/", "_").replace(" ", "_")
                dest = os.path.join(RAW_DIR, f"z{zid}_{prefix}_{safe_key}")
                url = f["links"]["self"]
                download_file(url, dest, timeout=180, max_mb=max_mb)
        except Exception as e:
            print(f"  Z {zid} ERR: {e}", flush=True)


if __name__ == "__main__":
    harvest_xronos()
    harvest_github_and_direct()
    harvest_figshare()
    harvest_zenodo()
    print("\n=== HARVEST COMPLETE ===", flush=True)
