import os
import sys
import re
import csv
import io
import json
import zipfile
import subprocess
import numpy as np
import pandas as pd
from PIL import Image

def get_base_dirs():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    raw_dir = os.path.join(base_dir, "histmap", "1.data_raw", "population_c14bazAAR")
    clean_dir = os.path.join(base_dir, "histmap", "2.data_cleaning", "population_c14bazAAR")
    raw_cache_dir = os.path.join(raw_dir, "raw_databases")
    config_dir = os.path.join(clean_dir, "config")
    os.makedirs(raw_cache_dir, exist_ok=True)
    os.makedirs(config_dir, exist_ok=True)
    return base_dir, raw_dir, clean_dir, raw_cache_dir, config_dir

def load_wmobb_raster(config_dir):
    raster_path = os.path.join(config_dir, "wmobb_raster.png")
    if not os.path.exists(raster_path):
        raise FileNotFoundError(f"wmobb_raster.png not found at {raster_path}. Run setup_c14_prerequisites.py first.")
    
    with Image.open(raster_path) as im:
        rgba = np.array(im, dtype=np.uint8)
    
    arr_u32 = (rgba[..., 0].astype(np.uint32) << 24) | \
              (rgba[..., 1].astype(np.uint32) << 16) | \
              (rgba[..., 2].astype(np.uint32) << 8) | \
              rgba[..., 3].astype(np.uint32)
    return arr_u32.astype(np.int32)

def download_file_cached(url, dest_path, force=False):
    if os.path.exists(dest_path) and not force and os.path.getsize(dest_path) > 500:
        return dest_path
    print(f"Downloading {url} -> {dest_path} ...")
    cmd = ["curl.exe", "-s", "-L", "-k", "-m", "180", "-o", dest_path, url]
    try:
        subprocess.run(cmd, check=True)
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 500:
            print(f"Downloaded {dest_path} ({os.path.getsize(dest_path)} bytes)")
            return dest_path
        else:
            print(f"Warning: Downloaded file {dest_path} is empty or invalid.")
            return None
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def normalize_labnr(lab):
    if not lab or pd.isna(lab):
        return ""
    lab_str = str(lab).strip().upper()
    cleaned = re.sub(r'[^A-Z0-9]', '', lab_str)
    has_alpha = bool(re.search(r'[A-Z]', cleaned))
    has_digit = bool(re.search(r'[0-9]', cleaned))
    if len(cleaned) >= 3 and has_alpha and has_digit:
        return cleaned
    return ""

def parse_float(val, default=None):
    if val is None or pd.isna(val):
        return default
    try:
        s = str(val).strip().replace(',', '.')
        f = float(s)
        return f if not np.isnan(f) else default
    except (ValueError, TypeError):
        return default

def add_record(records, lab, age, err, lat, lon, site, country, sourcedb):
    age_f = parse_float(age)
    err_f = parse_float(err)
    lat_f = parse_float(lat)
    lon_f = parse_float(lon)

    if age_f is None or err_f is None or lat_f is None or lon_f is None:
        return False
    if age_f <= 0 or age_f > 50000:
        return False
    if err_f <= 0 or err_f > 600:
        return False
    if lat_f < -90 or lat_f > 90 or lon_f < -180 or lon_f > 180:
        return False
    if abs(lat_f) < 0.0001 and abs(lon_f) < 0.0001:
        return False

    records.append({
        'labnr': str(lab).strip() if lab and not pd.isna(lab) else '',
        'c14age': round(age_f),
        'c14std': round(err_f),
        'lat': round(lat_f, 5),
        'lon': round(lon_f, 5),
        'site': str(site).strip() if site and not pd.isna(site) else '',
        'country': str(country).strip() if country and not pd.isna(country) else '',
        'sourcedb': sourcedb
    })
    return True

def ingest_all_databases(raw_cache_dir):
    all_raw_records = []
    
    # Standard CSV / TSV databases
    standard_sources = [
        {
            'name': 'p3k14c',
            'url': 'https://raw.githubusercontent.com/people3k/p3k14c/refs/tags/2025.07/inst/p3k14c_scrubbed_fuzzed.csv',
            'filename': 'p3k14c.csv',
            'sep': ',',
            'encoding': 'utf-8-sig',
            'cols': {'labnr': 'LabID', 'c14age': 'Age', 'c14std': 'Error', 'lat': 'Lat', 'lon': 'Long', 'site': 'SiteName', 'country': 'Country'}
        },
        {
            'name': 'nerd',
            'url': 'https://raw.githubusercontent.com/apalmisano82/NERD/main/nerd.csv',
            'filename': 'nerd.csv',
            'sep': ',',
            'encoding': 'utf-8-sig',
            'cols': {'labnr': 'LabID', 'c14age': 'CRA', 'c14std': 'Error', 'lat': 'Latitude', 'lon': 'Longitude', 'site': 'SiteName', 'country': 'Country'}
        },
        {
            'name': 'aida',
            'url': 'https://raw.githubusercontent.com/apalmisano82/AIDA/main/dates.csv',
            'filename': 'aida.csv',
            'sep': ',',
            'encoding': 'utf-8-sig',
            'cols': {'labnr': 'LabID', 'c14age': 'CRA', 'c14std': 'Error', 'lat': 'Latitude', 'lon': 'Longitude', 'site': 'SiteName', 'country': 'Country'}
        },
        {
            'name': 'adrac',
            'url': 'https://raw.githubusercontent.com/dirkseidensticker/aDRAC/master/aDRAC.csv',
            'filename': 'adrac.csv',
            'sep': ',',
            'encoding': 'utf-8-sig',
            'cols': {'labnr': 'LABNR', 'c14age': 'C14AGE', 'c14std': 'C14STD', 'lat': 'LAT', 'lon': 'LONG', 'site': 'SITE', 'country': 'COUNTRY'}
        },
        {
            'name': 'calpal',
            'url': 'https://raw.githubusercontent.com/nevrome/CalPal-Database/master/CalPal_2020_08_20.tsv',
            'filename': 'calpal.tsv',
            'sep': '\t',
            'encoding': 'utf-8-sig',
            'cols': {'labnr': 'LABNR', 'c14age': 'C14AGE', 'c14std': 'C14STD', 'lat': 'LATITUDE', 'lon': 'LONGITUDE', 'site': 'SITE', 'country': 'COUNTRY'}
        },
        {
            'name': 'caribbean',
            'url': 'https://raw.githubusercontent.com/philriris/caribbean-14C/main/data/caribbean_14C.csv',
            'filename': 'caribbean.csv',
            'sep': ',',
            'encoding': 'utf-8-sig',
            'cols': {'labnr': 'LabNo', 'c14age': 'Age', 'c14std': 'Error', 'lat': 'Lat', 'lon': 'Lon', 'site': 'SiteName', 'country': 'Country.Territory'}
        },
        {
            'name': 'rxpand',
            'url': 'https://raw.githubusercontent.com/jgregoriods/rxpand/master/data/expand.csv',
            'filename': 'rxpand.csv',
            'sep': ',',
            'encoding': 'utf-8-sig',
            'cols': {'labnr': 'LabCode', 'c14age': 'C14Age', 'c14std': 'C14SD', 'lat': 'Latitude', 'lon': 'Longitude', 'site': 'Site', 'country': 'Country'}
        },
        {
            'name': 'sard',
            'url': 'https://raw.githubusercontent.com/emmaloftus/Southern-African-Radiocarbon-Database/main/SARD_Mar2021_14C.csv',
            'filename': 'sard.csv',
            'sep': ',',
            'encoding': 'utf-8-sig',
            'cols': {'labnr': 'Lab ID', 'c14age': 'Date', 'c14std': 'Uncertainty', 'lat': 'DecdegS', 'lon': 'DecdegE', 'site': 'Site', 'country': 'Country'}
        },
        {
            'name': 'tegiszhol',
            'url': 'https://zenodo.org/records/21756393/files/tegiszhol_c14bazaar.csv?download=1',
            'filename': 'tegiszhol.csv',
            'sep': ',',
            'encoding': 'utf-8',
            'cols': {'labnr': 'labnr', 'c14age': 'c14age', 'c14std': 'c14std', 'lat': 'lat', 'lon': 'lon', 'site': 'site', 'country': 'country'}
        }
    ]

    for src in standard_sources:
        dest_file = os.path.join(raw_cache_dir, src['filename'])
        try:
            download_file_cached(src['url'], dest_file)
            print(f"Parsing {src['name']} ...")
            with open(dest_file, 'r', encoding=src['encoding'], errors='ignore') as f:
                reader = csv.DictReader(f, delimiter=src['sep'])
                c_map = src['cols']
                count = 0
                for row in reader:
                    lat_val = row.get(c_map['lat'])
                    if src['name'] == 'sard':
                        f_lat = parse_float(lat_val)
                        if f_lat and f_lat > 0:
                            lat_val = -f_lat
                    ok = add_record(all_raw_records,
                                    row.get(c_map['labnr']),
                                    row.get(c_map['c14age']),
                                    row.get(c_map['c14std']),
                                    lat_val,
                                    row.get(c_map['lon']),
                                    row.get(c_map.get('site', '')),
                                    row.get(c_map.get('country', '')),
                                    src['name'])
                    if ok:
                        count += 1
                print(f"[{src['name']}] Loaded {count} valid records.")
        except Exception as e:
            print(f"[{src['name']}] Error: {e}")

    # 1. EUROEVOL (Shennan et al.)
    try:
        f_d = download_file_cached("https://discovery.ucl.ac.uk/id/eprint/1469811/7/EUROEVOL09-07-201516-34_C14Samples.csv", os.path.join(raw_cache_dir, "euroevol_dates.csv"))
        f_s = download_file_cached("https://discovery.ucl.ac.uk/id/eprint/1469811/9/EUROEVOL09-07-201516-34_CommonSites.csv", os.path.join(raw_cache_dir, "euroevol_sites.csv"))
        if f_d and f_s:
            print("Parsing euroevol ...")
            df_d = pd.read_csv(f_d, dtype=str)
            df_s = pd.read_csv(f_s, dtype=str, on_bad_lines='skip')
            merged = pd.merge(df_d, df_s[['SiteID', 'SiteName', 'Latitude', 'Longitude', 'Country']], on='SiteID', how='left')
            count = 0
            for _, r in merged.iterrows():
                if add_record(all_raw_records, r.get('LabCode'), r.get('C14Age'), r.get('C14SD'), r.get('Latitude'), r.get('Longitude'), r.get('SiteName'), r.get('Country'), 'euroevol'):
                    count += 1
            print(f"[euroevol] Loaded {count} valid records.")
    except Exception as e:
        print(f"[euroevol] Error: {e}")

    # 2. RADO.NB (Radon-B European Neolithic / Bronze Age)
    try:
        f_rad = download_file_cached("https://radonb.ufg.uni-kiel.de/radondaily.txt", os.path.join(raw_cache_dir, "radonb.txt"))
        if f_rad:
            print("Parsing rado.nb ...")
            df = pd.read_csv(f_rad, sep='\t', encoding='latin-1', dtype=str, on_bad_lines='skip')
            count = 0
            for _, r in df.iterrows():
                if add_record(all_raw_records, r.get('LABNR'), r.get('C14AGE'), r.get('C14STD'), r.get('LATITUDE'), r.get('LONGITUDE'), r.get('SITE'), r.get('COUNTRY'), 'rado.nb'):
                    count += 1
            print(f"[rado.nb] Loaded {count} valid records.")
    except Exception as e:
        print(f"[rado.nb] Error: {e}")

    # 3. 14cpalaeolithic
    try:
        f_pal = download_file_cached("https://ees.kuleuven.be/en/geography/projects/14c-palaeolithic/download/radiocarbon-palaeolithic-europe-database-v33-extract.xlsx", os.path.join(raw_cache_dir, "14cpalaeolithic.xlsx"))
        if f_pal:
            print("Parsing 14cpalaeolithic ...")
            df = pd.read_excel(f_pal, sheet_name=0, skiprows=1, dtype=str)
            df = df[df['Method'].isin(['AMS', '14C'])]
            count = 0
            for _, r in df.iterrows():
                lab = r.get('labref')
                age = r.get('Age')
                err = r.get('pm')
                if lab == 'UCIAMS-286509':
                    age, err = 40900, 1400
                elif lab == 'VERA-8488':
                    age, err = 42081, 984
                if add_record(all_raw_records, lab, age, err, r.get('Lat'), r.get('Long'), r.get('sitename'), r.get('country'), '14cpalaeolithic'):
                    count += 1
            print(f"[14cpalaeolithic] Loaded {count} valid records.")
    except Exception as e:
        print(f"[14cpalaeolithic] Error: {e}")

    # 4. EUBAR (European Bronze Age)
    try:
        f_eubar = download_file_cached("https://telearchaeology.org/EUBAR/EUBAR%20def.xlsx", os.path.join(raw_cache_dir, "eubar.xlsx"))
        if f_eubar:
            print("Parsing eubar ...")
            df = pd.read_excel(f_eubar, sheet_name=0, dtype=str)
            count = 0
            for _, r in df.iterrows():
                # Col 12: Lab Code, 13: C14 Age, 14: C14 SD, 11: Lat, 10: Lon, 0: Site, 9: Country
                if add_record(all_raw_records, r.iloc[12], r.iloc[13], r.iloc[14], r.iloc[11], r.iloc[10], r.iloc[0], r.iloc[9], 'eubar'):
                    count += 1
            print(f"[eubar] Loaded {count} valid records.")
    except Exception as e:
        print(f"[eubar] Error: {e}")

    # 5. AgriChange (Western Mediterranean Neolithic)
    try:
        f_agri = download_file_cached("https://zenodo.org/records/4541470/files/AgriChange_14Cdatabase.xlsx", os.path.join(raw_cache_dir, "agrichange.xlsx"))
        if f_agri:
            print("Parsing agrichange ...")
            df = pd.read_excel(f_agri, sheet_name=0, dtype=str)
            count = 0
            for _, r in df.iterrows():
                lat = r.get('Lat')
                lon = r.get('Lon')
                if not lat or str(lat).startswith('<') or str(lat) in ['nd', '--', '---']:
                    lat = r.get('Lat_muni')
                if not lon or str(lon).startswith('<') or str(lon) in ['nd', '--', '---']:
                    lon = r.get('Lon_muni')
                if add_record(all_raw_records, r.get('LabCode'), r.get('BP'), r.get('SD'), lat, lon, r.get('Site'), r.get('Country'), 'agrichange'):
                    count += 1
            print(f"[agrichange] Loaded {count} valid records.")
    except Exception as e:
        print(f"[agrichange] Error: {e}")

    # 6. AustArch (Australia 14C)
    try:
        f_aust = download_file_cached("https://archaeologydataservice.ac.uk/catalogue/adsdata/arch-1661-1/dissemination/csv/Austarch_1-3_and_IDASQ_28Nov13-1.csv", os.path.join(raw_cache_dir, "austarch.csv"))
        if f_aust:
            print("Parsing austarch ...")
            df = pd.read_csv(f_aust, dtype=str, on_bad_lines='skip')
            df = df[df['METHOD'] == 'Radiocarbon']
            count = 0
            for _, r in df.iterrows():
                if add_record(all_raw_records, r.get('LAB_CODE'), r.get('AGE'), r.get('ERROR'), r.get('LATITUDE'), r.get('LONGITUDE'), r.get('SITE'), 'Australia', 'austarch'):
                    count += 1
            print(f"[austarch] Loaded {count} valid records.")
    except Exception as e:
        print(f"[austarch] Error: {e}")

    # 7. IRDD (Irish Radiocarbon Dates)
    try:
        f_irdd = download_file_cached("https://zenodo.org/records/3367518/files/Chapple%2C%20RM%202019%20Catalogue%20of%20radiocarbon%20determinations%20%26%20dendrochronology%20dates%20%28August%202019%20Release%29.xlsx", os.path.join(raw_cache_dir, "irdd.xlsx"))
        if f_irdd:
            print("Parsing irdd ...")
            df = pd.read_excel(f_irdd, sheet_name=2, skiprows=1, header=None, dtype=str)
            count = 0
            for _, r in df.iterrows():
                # Col 6: Lab, Col 3: Age, Col 5: Error, Col 19: Lat, Col 20: Lon, Col 1: Site
                if add_record(all_raw_records, r.iloc[6], r.iloc[3], r.iloc[5], r.iloc[19], r.iloc[20], r.iloc[1], 'Ireland', 'irdd'):
                    count += 1
            print(f"[irdd] Loaded {count} valid records.")
    except Exception as e:
        print(f"[irdd] Error: {e}")

    # 8. Katsianis (Aegean Prehistory)
    try:
        f_kat = download_file_cached("https://api.figshare.com/v2/file/download/23166314", os.path.join(raw_cache_dir, "katsianis.zip"))
        if f_kat:
            print("Parsing katsianis ...")
            with zipfile.ZipFile(f_kat, 'r') as z:
                target = [n for n in z.namelist() if "C14Samples.txt" in n][0]
                with z.open(target) as zf:
                    df = pd.read_csv(zf, sep='\t', dtype=str)
                    count = 0
                    for _, r in df.iterrows():
                        if add_record(all_raw_records, r.get('LabID'), r.get('CRA'), r.get('Error'), r.get('Latitude'), r.get('Longitude'), r.get('SiteName'), r.get('Country'), 'katsianis'):
                            count += 1
                    print(f"[katsianis] Loaded {count} valid records.")
    except Exception as e:
        print(f"[katsianis] Error: {e}")

    # 9. KITE East Africa
    try:
        f_kite = download_file_cached("https://dataverse.harvard.edu/api/access/datafile/:persistentId?persistentId=doi:10.7910/DVN/NJLNRJ/L8KRSL", os.path.join(raw_cache_dir, "kiteeastafrica.csv"))
        if f_kite:
            print("Parsing kiteeastafrica ...")
            df = pd.read_csv(f_kite, skiprows=3, encoding='latin-1', dtype=str)
            count = 0
            for _, r in df.iterrows():
                if add_record(all_raw_records, r.get('Lab Number'), r.get('Normalized Age'), r.get('NA Sigma'), r.get('Latitude'), r.get('Longitude'), r.get('Site Identifier'), '', 'kiteeastafrica'):
                    count += 1
            print(f"[kiteeastafrica] Loaded {count} valid records.")
    except Exception as e:
        print(f"[kiteeastafrica] Error: {e}")

    # 10. MedAfriCarbon (Mediterranean Africa)
    try:
        f_med = download_file_cached("https://zenodo.org/records/3689716/files/data_v1.0.3.zip", os.path.join(raw_cache_dir, "medafricarbon.zip"))
        if f_med:
            print("Parsing medafricarbon ...")
            with zipfile.ZipFile(f_med, 'r') as z:
                f_dates = [n for n in z.namelist() if "dateTable.csv" in n][0]
                f_sites = [n for n in z.namelist() if "siteTable.csv" in n][0]
                with z.open(f_dates) as zd, z.open(f_sites) as zs:
                    df_d = pd.read_csv(zd, dtype=str)
                    df_s = pd.read_csv(zs, dtype=str)
                    merged = pd.merge(df_d, df_s, on='Site_ID', how='left')
                    count = 0
                    for _, r in merged.iterrows():
                        if add_record(all_raw_records, r.get('Lab_ID'), r.get('CRA'), r.get('Error'), r.get('Decimal_Degrees_Lat'), r.get('Decimal_Degrees_Long'), r.get('Site_Name'), r.get('Country'), 'medafricarbon'):
                            count += 1
                    print(f"[medafricarbon] Loaded {count} valid records.")
    except Exception as e:
        print(f"[medafricarbon] Error: {e}")

    # 11. NeoNet Med
    try:
        f_neo = download_file_cached("https://digitallib.unipi.it/fedora/objects/mag:2814/datastreams/MMb714bbfacf4af2ce1fd7025e3789a99b/content", os.path.join(raw_cache_dir, "neonet.csv"))
        if f_neo:
            print("Parsing neonet ...")
            df = pd.read_csv(f_neo, sep=None, engine='python', encoding='latin-1', dtype=str, on_bad_lines='skip')
            count = 0
            for _, r in df.iterrows():
                if add_record(all_raw_records, r.get('LabCode'), r.get('C14Age'), r.get('C14SD'), r.get('Latitude'), r.get('Longitude'), r.get('SiteName'), r.get('Country'), 'neonet'):
                    count += 1
            print(f"[neonet] Loaded {count} valid records.")
    except Exception as e:
        print(f"[neonet] Error: {e}")

    # 12. NeoNet Atlantic
    try:
        f_neoatl = download_file_cached("https://digitallib.unipi.it/fedora/objects/mag:2627/datastreams/MM54ff3698c0ea78b77469ce6462c2ca36/content", os.path.join(raw_cache_dir, "neonetatl.csv"))
        if f_neoatl:
            print("Parsing neonetatl ...")
            df = pd.read_csv(f_neoatl, sep='\t', encoding='latin-1', dtype=str, on_bad_lines='skip')
            count = 0
            for _, r in df.iterrows():
                if add_record(all_raw_records, r.get('LabCode'), r.get('C14Age'), r.get('C14SD'), r.get('Latitude'), r.get('Longitude'), r.get('SiteName'), r.get('Country'), 'neonetatl'):
                    count += 1
            print(f"[neonetatl] Loaded {count} valid records.")
    except Exception as e:
        print(f"[neonetatl] Error: {e}")

    # 13. PACEA (Palaeolithic & Mesolithic Europe)
    try:
        f_pacea = download_file_cached("http://www.paleoanthro.org/media/journal/content/PA20110001_S01.zip", os.path.join(raw_cache_dir, "pacea.zip"))
        if f_pacea:
            print("Parsing pacea ...")
            with zipfile.ZipFile(f_pacea, 'r') as z:
                target = [n for n in z.namelist() if "PA20110001_S01.txt" in n][0]
                with z.open(target) as zf:
                    df = pd.read_csv(zf, sep='\t', skiprows=1, encoding='latin-1', dtype=str)
                    count = 0
                    for _, r in df.iterrows():
                        if add_record(all_raw_records, r.get('Code'), r.get('Age'), r.get('s.dev.'), r.get('Latitude'), r.get('Longitude'), r.get('Site'), r.get('Country'), 'pacea'):
                            count += 1
                    print(f"[pacea] Loaded {count} valid records.")
    except Exception as e:
        print(f"[pacea] Error: {e}")

    print(f"\nTotal raw ingested radiocarbon records across all c14bazAAR archives: {len(all_raw_records)}")
    return all_raw_records

def deduplicate_and_assign_basins(records, wmobb_raster):
    print("Beginning multi-tier deduplication and watershed assignment ...")
    height, width = wmobb_raster.shape
    seen_labnr = {}
    seen_spatial = {}
    deduplicated = []

    priority = {
        'euroevol': 10,
        'rado.nb': 10,
        '14cpalaeolithic': 10,
        'agrichange': 10,
        'austarch': 10,
        'eubar': 10,
        'irdd': 10,
        'katsianis': 10,
        'kiteeastafrica': 10,
        'medafricarbon': 10,
        'neonet': 10,
        'neonetatl': 10,
        'nerd': 10,
        'aida': 10,
        'adrac': 10,
        'pacea': 10,
        'sard': 10,
        'caribbean': 10,
        'rxpand': 10,
        'tegiszhol': 10,
        'calpal': 8,
        'p3k14c': 5
    }

    # Step 1: Lab Number Deduplication
    for rec in records:
        norm_lab = normalize_labnr(rec['labnr'])
        if norm_lab:
            rec['norm_lab'] = norm_lab
            if norm_lab in seen_labnr:
                existing = seen_labnr[norm_lab]
                if priority.get(rec['sourcedb'], 1) > priority.get(existing['sourcedb'], 1):
                    seen_labnr[norm_lab] = rec
            else:
                seen_labnr[norm_lab] = rec
        else:
            rec['norm_lab'] = ''

    candidates = list(seen_labnr.values())

    # Step 2: Spatial-temporal binning for records without standard lab codes
    for rec in records:
        if not rec['norm_lab']:
            lat_bin = round(rec['lat'] / 0.05)
            lon_bin = round(rec['lon'] / 0.05)
            age_bin = round(rec['c14age'] / 100)
            key = (lat_bin, lon_bin, age_bin)

            if key in seen_spatial:
                existing = seen_spatial[key]
                if priority.get(rec['sourcedb'], 1) > priority.get(existing['sourcedb'], 1):
                    seen_spatial[key] = rec
            else:
                seen_spatial[key] = rec

    candidates.extend(list(seen_spatial.values()))
    print(f"Candidates after duplicate detection: {len(candidates)}")

    # Step 3: Assign Watershed Basins
    assigned_count = 0
    basin_counts = {}

    for rec in candidates:
        lon = rec['lon']
        lat = rec['lat']
        px = int(np.clip(np.round((lon + 180.0) / 360.0 * width), 0, width - 1))
        py = int(np.clip(np.round((90.0 - lat) / 180.0 * height), 0, height - 1))

        wmobb = int(wmobb_raster[py, px])

        if wmobb == 0:
            for radius in [1, 2, 3]:
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        ny = np.clip(py + dy, 0, height - 1)
                        nx = np.clip(px + dx, 0, width - 1)
                        if wmobb_raster[ny, nx] > 0:
                            wmobb = int(wmobb_raster[ny, nx])
                            break
                    if wmobb > 0:
                        break
                if wmobb > 0:
                    break

        if wmobb > 0:
            rec['wmobb'] = wmobb
            deduplicated.append(rec)
            assigned_count += 1
            basin_counts[wmobb] = basin_counts.get(wmobb, 0) + 1

    print(f"Deduplicated dates assigned to WMO basins: {assigned_count}")
    print(f"Basins represented with at least 1 date: {len(basin_counts)} / 516")

    deduplicated.sort(key=lambda r: (r['wmobb'], r['c14age']))
    return deduplicated, basin_counts

def main():
    base_dir, raw_dir, clean_dir, raw_cache_dir, config_dir = get_base_dirs()
    wmobb_raster = load_wmobb_raster(config_dir)

    records = ingest_all_databases(raw_cache_dir)
    dedup_records, basin_counts = deduplicate_and_assign_basins(records, wmobb_raster)

    out_csv = os.path.join(raw_dir, "c14_cleaned_dedup.csv")
    print(f"Writing deduplicated dates to {out_csv} ...")
    fieldnames = ['labnr', 'c14age', 'c14std', 'lat', 'lon', 'site', 'country', 'sourcedb', 'wmobb']
    with open(out_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(dedup_records)
    print(f"Saved {len(dedup_records)} records to {out_csv} ({os.path.getsize(out_csv)} bytes)")

    out_json = os.path.join(clean_dir, "config", "c14_dates_summary.json")
    summary = {
        'total_dates': len(dedup_records),
        'total_basins': len(basin_counts),
        'basin_counts': basin_counts
    }
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"Saved basin summary to {out_json}")
    print("Global c14bazAAR ingestion and deduplication finished successfully!")

if __name__ == '__main__':
    main()
