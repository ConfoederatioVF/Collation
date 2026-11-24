import os
import json
import time
import zipfile
import requests

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\settlement_sources\raw"
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

DOWNLOADS = [
    # Mexico - Official INEGI ITER 1990, 2000, 2010, 2020 (ALL localities in Mexico, zero caps)
    ("mexico_inegi_iter_2020_csv.zip", "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/microdatos/iter/iter_00_cpv2020_csv.zip"),
    ("mexico_inegi_iter_2010_csv.zip", "https://www.inegi.org.mx/contenidos/programas/ccpv/2010/microdatos/iter/iter_00_cpv2010_csv.zip"),
    ("mexico_inegi_iter_2000_csv.zip", "https://www.inegi.org.mx/contenidos/programas/ccpv/2000/microdatos/iter/iter_00_cpv2000_csv.zip"),
    ("mexico_inegi_iter_1990_csv.zip", "https://www.inegi.org.mx/contenidos/programas/ccpv/1990/microdatos/iter/iter_00_cpv1990_csv.zip"),
    # Global UNSD Demographic Yearbook Table 8 / 240 (official national census city series 1948-2022)
    ("unsd_citypopulation_year_both.csv", "https://raw.githubusercontent.com/datasets/population-city/master/data/unsd-citypopulation-year-both.csv"),
    ("unsd_citypopulation_footnotes.csv", "https://raw.githubusercontent.com/datasets/population-city/master/data/unsd-citypopulation-year-both-footnotes.csv"),
    # France INSEE Official Populations de reference 2022 (covers Guadeloupe 971, Martinique 972, St-Barth 977, St-Martin 978)
    ("caribbean_insee_populations_legales_2022.zip", "https://www.insee.fr/fr/statistiques/fichier/8290591/ensemble.zip"),
    # US Census Bureau API - Puerto Rico (state 72) 2020, 2010, 2000 Municipios & Places (ALL rows)
    ("caribbean_pr_uscensus_2020_municipios.json", "https://api.census.gov/data/2020/dec/pl?get=NAME,P1_001N&for=county:*&in=state:72"),
    ("caribbean_pr_uscensus_2020_places.json", "https://api.census.gov/data/2020/dec/pl?get=NAME,P1_001N&for=place:*&in=state:72"),
    ("caribbean_pr_uscensus_2010_municipios.json", "https://api.census.gov/data/2010/dec/sf1?get=NAME,P001001&for=county:*&in=state:72"),
    ("caribbean_pr_uscensus_2010_places.json", "https://api.census.gov/data/2010/dec/sf1?get=NAME,P001001&for=place:*&in=state:72"),
    ("caribbean_pr_uscensus_2000_municipios.json", "https://api.census.gov/data/2000/dec/sf1?get=NAME,P001001&for=county:*&in=state:72"),
    ("caribbean_pr_uscensus_2000_places.json", "https://api.census.gov/data/2000/dec/sf1?get=NAME,P001001&for=place:*&in=state:72"),
    # US Census Bureau API - US Virgin Islands (state 78) 2020, 2010 Places & County Subdivisions & Islands
    ("caribbean_usvi_uscensus_2020_places.json", "https://api.census.gov/data/2020/dec/dhcvi?get=NAME,P1_001N&for=place:*"),
    ("caribbean_usvi_uscensus_2020_subdistricts.json", "https://api.census.gov/data/2020/dec/dhcvi?get=NAME,P1_001N&for=county%20subdivision:*"),
    ("caribbean_usvi_uscensus_2020_islands.json", "https://api.census.gov/data/2020/dec/dhcvi?get=NAME,P1_001N&for=county:*"),
    ("caribbean_usvi_uscensus_2010_places.json", "https://api.census.gov/data/2010/dec/vi?get=NAME,P001001&for=place:*"),
    ("caribbean_usvi_uscensus_2010_subdistricts.json", "https://api.census.gov/data/2010/dec/vi?get=NAME,P001001&for=county%20subdivision:*"),
    ("caribbean_usvi_uscensus_2010_islands.json", "https://api.census.gov/data/2010/dec/vi?get=NAME,P001001&for=county:*"),
    # GeoNames cities500 supplemental coordinate index (strictly for geocoding/matching, crowd <= 15%)
    ("supplemental_geonames_cities500.zip", "https://download.geonames.org/export/dump/cities500.zip"),
]

results = []
for fname, url in DOWNLOADS:
    out_path = os.path.join(RAW_DIR, fname)
    if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
        print(f"SKIP (exists {os.path.getsize(out_path)} B): {fname}")
        results.append({"file": fname, "status": "cached", "bytes": os.path.getsize(out_path), "url": url})
        continue
    t0 = time.time()
    try:
        with requests.get(url, headers=HEADERS, timeout=180, stream=True) as r:
            if r.status_code != 200:
                print(f"FAIL {r.status_code}: {fname} ({url})")
                results.append({"file": fname, "status": f"http_{r.status_code}", "url": url})
                continue
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=131072):
                    if chunk:
                        f.write(chunk)
        sz = os.path.getsize(out_path)
        print(f"OK ({sz:,} B in {time.time()-t0:.1f}s): {fname}")
        results.append({"file": fname, "status": "ok", "bytes": sz, "url": url})
    except Exception as e:
        print(f"ERR {fname}: {e}")
        results.append({"file": fname, "status": f"err:{e}", "url": url})

with open(os.path.join(RAW_DIR, "_core_download_log.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
print("DONE core downloads:", len([x for x in results if x["status"] in ("ok", "cached")]), "/", len(results))
