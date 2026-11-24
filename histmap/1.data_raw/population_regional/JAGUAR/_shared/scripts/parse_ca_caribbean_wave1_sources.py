import os
import csv
import json
import zipfile
import io
import openpyxl

BASE = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\settlement_sources"
RAW = os.path.join(BASE, "raw")
PARSED = os.path.join(BASE, "parsed")
os.makedirs(PARSED, exist_ok=True)

summary = {}

# 1. US Census Bureau Puerto Rico 2020 PL 94-171 (SUMLEV 050 Municipios + SUMLEV 160 Places/Zonas Urbanas/Comunidades)
def parse_pr_pl2020(zip_path):
    rows = []
    with zipfile.ZipFile(zip_path) as z:
        # Build LOGRECNO -> P1_001N (total pop) from pr000012020.pl (pipe delimited; col 4=LOGRECNO, col 5=P0010001)
        pop_map = {}
        with z.open("pr000012020.pl") as f:
            for line in f:
                parts = line.decode("latin-1", errors="replace").rstrip("\r\n").split("|")
                if len(parts) > 5:
                    pop_map[parts[4]] = parts[5]
        # Read prgeo2020.pl (pipe delimited; col 2=SUMLEV, col 7=LOGRECNO, col 8=GEOID, col 87=NAME, col 92=INTPTLAT, col 93=INTPTLON)
        with z.open("prgeo2020.pl") as f:
            for line in f:
                parts = line.decode("latin-1", errors="replace").rstrip("\r\n").split("|")
                if len(parts) < 94:
                    continue
                sumlev = parts[2]
                if sumlev not in ("050", "160", "060"):
                    continue
                logrecno = parts[7]
                geoid = parts[8]
                name = parts[87]
                lat = parts[92].replace("+", "")
                lon = parts[93].replace("+", "")
                pop = pop_map.get(logrecno, "")
                scope = "municipio" if sumlev == "050" else ("place_urban_community" if sumlev == "160" else "barrio")
                rows.append({
                    "jurisdiction": "caribbean",
                    "territory": "Puerto Rico",
                    "year": 2020,
                    "sumlev": sumlev,
                    "geo_type": scope,
                    "geoid": geoid,
                    "name": name,
                    "population": int(pop) if pop.isdigit() else "",
                    "lat": float(lat) if lat else "",
                    "lon": float(lon) if lon else "",
                    "source": "US Census Bureau 2020 Decennial Census PL 94-171 (Puerto Rico)",
                })
    return rows

def parse_pr_pl2010(zip_path):
    """2010 PL 94-171 uses fixed-width prgeo2010.pl + comma-separated pr000012010.pl."""
    rows = []
    with zipfile.ZipFile(zip_path) as z:
        pop_map = {}
        p1_name = [n for n in z.namelist() if "000012010" in n][0]
        geo_name = [n for n in z.namelist() if "geo2010" in n][0]
        with z.open(p1_name) as f:
            for line in f:
                parts = line.decode("latin-1", errors="replace").rstrip("\r\n").split(",")
                if len(parts) > 5:
                    pop_map[parts[4]] = parts[5]
        with z.open(geo_name) as f:
            for line in f:
                s = line.decode("latin-1", errors="replace")
                if len(s) < 350:
                    continue
                sumlev = s[8:11]
                if sumlev not in ("050", "160"):
                    continue
                logrecno = s[18:25]
                county = s[29:32].strip()
                place = s[45:50].strip()
                name = s[226:316].strip()
                lat = s[336:347].strip().replace("+", "")
                lon = s[347:359].strip().replace("+", "")
                pop = pop_map.get(logrecno, "")
                scope = "municipio" if sumlev == "050" else "place_urban_community"
                rows.append({
                    "jurisdiction": "caribbean",
                    "territory": "Puerto Rico",
                    "year": 2010,
                    "sumlev": sumlev,
                    "geo_type": scope,
                    "geoid": f"72{county}{place}",
                    "name": name,
                    "population": int(pop) if pop.isdigit() else "",
                    "lat": float(lat) if lat else "",
                    "lon": float(lon) if lon else "",
                    "source": "US Census Bureau 2010 Decennial Census PL 94-171 (Puerto Rico)",
                })
    return rows

pr2020_rows = parse_pr_pl2020(os.path.join(RAW, "caribbean_pr_uscensus_2020_pl94171.zip"))
pr2010_rows = parse_pr_pl2010(os.path.join(RAW, "caribbean_pr_uscensus_pr2010.pl.zip"))
pr_all = pr2010_rows + pr2020_rows
pr_out = os.path.join(PARSED, "caribbean_pr_uscensus_2010_2020_full.csv")
with open(pr_out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(pr_all[0].keys()))
    w.writeheader()
    w.writerows(pr_all)
print(f"PR US Census PL 2010+2020: {len(pr2010_rows)} (2010) + {len(pr2020_rows)} (2020) = {len(pr_all)} rows")
summary["caribbean_pr_uscensus_2010_2020"] = {
    "rows_2010": len(pr2010_rows),
    "rows_2020": len(pr2020_rows),
    "rows_2020_municipios": len([r for r in pr2020_rows if r["sumlev"] == "050"]),
    "rows_2020_places": len([r for r in pr2020_rows if r["sumlev"] == "160"]),
    "rows_2020_barrios": len([r for r in pr2020_rows if r["sumlev"] == "060"]),
}

# 2. US Virgin Islands PHC Tables 01, 02, 03, 04 (2010 & 2020)
usvi_rows = []
for tbl_num, geo_lvl in [("01", "island_subdistrict"), ("02", "estate"), ("03", "place_town")]:
    fp = os.path.join(RAW, f"caribbean_usvi_uscensus_us-virgin-islands-phc-table{tbl_num}.csv")
    if not os.path.exists(fp):
        continue
    with open(fp, encoding="utf-8-sig", errors="replace") as f:
        r = csv.reader(f)
        for row in r:
            if not row or not row[0].strip():
                continue
            name = row[0].strip()
            if any(name.lower().startswith(x) for x in ("population", "geographic", "2020 census", "island and", "source", "note", "table")):
                continue
            vals = [c.strip().replace(",", "") for c in row[1:] if c.strip()]
            nums = [int(v) for v in vals if v.isdigit()]
            if not nums:
                continue
            if tbl_num == "01" and len(nums) >= 2:
                usvi_rows.append({"jurisdiction": "caribbean", "territory": "United States Virgin Islands", "geo_level": geo_lvl, "name": name, "pop_2010": nums[0], "pop_2020": nums[1], "source": "US Census Bureau 2020 Island Areas PHC Table 01"})
            elif tbl_num == "03" and len(nums) >= 2:
                usvi_rows.append({"jurisdiction": "caribbean", "territory": "United States Virgin Islands", "geo_level": geo_lvl, "name": name, "pop_2010": nums[0], "pop_2020": nums[1], "source": "US Census Bureau 2020 Island Areas PHC Table 03"})
            else:
                usvi_rows.append({"jurisdiction": "caribbean", "territory": "United States Virgin Islands", "geo_level": geo_lvl, "name": name, "pop_2010": "", "pop_2020": nums[0], "source": f"US Census Bureau 2020 Island Areas PHC Table {tbl_num}"})

usvi_out = os.path.join(PARSED, "caribbean_usvi_uscensus_2010_2020.csv")
with open(usvi_out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["jurisdiction", "territory", "geo_level", "name", "pop_2010", "pop_2020", "source"])
    w.writeheader()
    w.writerows(usvi_rows)
print(f"USVI US Census 2010+2020: {len(usvi_rows)} rows")
summary["caribbean_usvi_uscensus_2010_2020"] = {"rows": len(usvi_rows)}

# 3. INSEE Populations Legales 2022 - French Antilles (Guadeloupe 971, Martinique 972, St-Barth 977, St-Martin 978)
insee_rows = []
with zipfile.ZipFile(os.path.join(RAW, "caribbean_insee_populations_legales_2022.zip")) as z:
    with z.open("donnees_communes.csv") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"), delimiter=";")
        for r in reader:
            if r.get("DEP") in ("971", "972"):
                insee_rows.append({
                    "jurisdiction": "caribbean",
                    "territory": "Guadeloupe" if r["DEP"] == "971" else "Martinique",
                    "dep": r["DEP"],
                    "code_insee": r["COM"],
                    "name": r["Commune"],
                    "pop_municipale_2022": int(r["PMUN"]),
                    "pop_totale_2022": int(r["PTOT"]),
                    "source": "INSEE Populations de reference 2022 (communes)",
                })
    with z.open("donnees_collectivites.csv") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"), delimiter=";")
        for r in reader:
            code = r.get("CODCOM", "") or r.get("COM", "") or ""
            lib = r.get("Collectivité", "") or r.get("Commune", "") or str(r)
            if any(k in lib for k in ("Saint-Barth", "Saint-Martin")):
                insee_rows.append({
                    "jurisdiction": "caribbean",
                    "territory": lib,
                    "dep": r.get("COM", "")[:3],
                    "code_insee": r.get("COM", ""),
                    "name": lib,
                    "pop_municipale_2022": int(r.get("PMUN", 0) or 0),
                    "pop_totale_2022": int(r.get("PTOT", 0) or 0),
                    "source": "INSEE Populations de reference 2022 (collectivites d'outre-mer)",
                })

insee_out = os.path.join(PARSED, "caribbean_insee_french_antilles_2022.csv")
with open(insee_out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["jurisdiction", "territory", "dep", "code_insee", "name", "pop_municipale_2022", "pop_totale_2022", "source"])
    w.writeheader()
    w.writerows(insee_rows)
print(f"INSEE French Antilles 2022: {len(insee_rows)} rows")
summary["caribbean_insee_french_antilles_2022"] = {"rows": len(insee_rows)}

# 4. UNSD Demographic Yearbook City Population filtered to JAGUAR
UNSD_JAG_MAP = {
    "Mexico": "mexico",
    "Guatemala": "central_america", "Belize": "central_america", "Honduras": "central_america",
    "El Salvador": "central_america", "Nicaragua": "central_america", "Costa Rica": "central_america",
    "Panama": "central_america",
    "Cuba": "caribbean", "Haiti": "caribbean", "Dominican Republic": "caribbean",
    "Jamaica": "caribbean", "Puerto Rico": "caribbean", "Barbados": "caribbean",
    "Trinidad and Tobago": "caribbean", "Bahamas": "caribbean", "Bermuda": "caribbean",
    "Guadeloupe": "caribbean", "Martinique": "caribbean", "Curaçao": "caribbean",
    "Aruba": "caribbean", "Sint Maarten (Dutch part)": "caribbean",
    "Bonaire, Sint Eustatius and Saba": "caribbean",
    "United States Virgin Islands": "caribbean", "British Virgin Islands": "caribbean",
    "Antigua and Barbuda": "caribbean", "Saint Kitts and Nevis": "caribbean",
    "Dominica": "caribbean", "Saint Lucia": "caribbean",
    "Saint Vincent and the Grenadines": "caribbean", "Grenada": "caribbean",
    "Montserrat": "caribbean", "Anguilla": "caribbean", "Cayman Islands": "caribbean",
    "Turks and Caicos Islands": "caribbean", "Netherlands Antilles": "caribbean",
}
unsd_rows = []
unsd_by_jur = {"mexico": 0, "central_america": 0, "caribbean": 0}
unsd_years = set()
with open(os.path.join(RAW, "unsd_citypopulation_year_both.csv"), encoding="utf-8-sig", errors="replace") as f:
    reader = csv.DictReader(f)
    for r in reader:
        c = r.get("Country or Area", "").strip()
        if c in UNSD_JAG_MAP:
            jur = UNSD_JAG_MAP[c]
            val = r.get("Value", "").strip()
            yr = r.get("Year", "").strip()
            if yr.isdigit():
                unsd_years.add(int(yr))
            unsd_rows.append({
                "jurisdiction": jur,
                "country": c,
                "year": yr,
                "city": r.get("City", "").strip(),
                "city_type": r.get("City type", "").strip(),
                "reliability": r.get("Reliability", "").strip(),
                "source_year": r.get("Source Year", "").strip(),
                "population": val,
                "source": "UNSD Demographic Yearbook Table 8 (City Population by Sex, City and City Type)",
            })
            unsd_by_jur[jur] += 1

unsd_out = os.path.join(PARSED, "jaguar_unsd_citypopulation_parsed.csv")
with open(unsd_out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(unsd_rows[0].keys()))
    w.writeheader()
    w.writerows(unsd_rows)
print(f"UNSD JAGUAR: {len(unsd_rows)} rows ({unsd_by_jur}), years {min(unsd_years)}-{max(unsd_years)}")
summary["jaguar_unsd_citypopulation"] = {
    "rows": len(unsd_rows), "by_jurisdiction": unsd_by_jur,
    "min_year": min(unsd_years), "max_year": max(unsd_years),
}

# 5. GeoNames cities500 filtered strictly to JAGUAR (SUPPLEMENTAL COORDINATES ONLY)
GEO_ISO2 = {
    "MX": "mexico",
    "GT": "central_america", "BZ": "central_america", "HN": "central_america",
    "SV": "central_america", "NI": "central_america", "CR": "central_america", "PA": "central_america",
    "CU": "caribbean", "HT": "caribbean", "DO": "caribbean", "JM": "caribbean", "PR": "caribbean",
    "BB": "caribbean", "TT": "caribbean", "BS": "caribbean", "BM": "caribbean",
    "GP": "caribbean", "MQ": "caribbean", "CW": "caribbean", "AW": "caribbean", "BQ": "caribbean",
    "SX": "caribbean", "MF": "caribbean", "BL": "caribbean", "VI": "caribbean", "VG": "caribbean",
    "AG": "caribbean", "KN": "caribbean", "DM": "caribbean", "LC": "caribbean", "VC": "caribbean",
    "GD": "caribbean", "MS": "caribbean", "AI": "caribbean", "KY": "caribbean", "TC": "caribbean",
}
geo_rows = []
geo_by_jur = {"mexico": 0, "central_america": 0, "caribbean": 0}
with zipfile.ZipFile(os.path.join(RAW, "supplemental_geonames_cities500.zip")) as z:
    with z.open("cities500.txt") as f:
        for line in f:
            parts = line.decode("utf-8", errors="replace").rstrip("\r\n").split("\t")
            if len(parts) < 15:
                continue
            cc = parts[8]
            if cc not in GEO_ISO2:
                continue
            jur = GEO_ISO2[cc]
            geo_rows.append({
                "jurisdiction": jur,
                "iso2": cc,
                "geonameid": parts[0],
                "name": parts[1],
                "asciiname": parts[2],
                "lat": parts[4],
                "lon": parts[5],
                "feature_code": parts[7],
                "admin1": parts[10],
                "admin2": parts[11],
                "geonames_pop_ref": parts[14],
                "role": "supplemental_coordinates_only",
            })
            geo_by_jur[jur] += 1

geo_out = os.path.join(PARSED, "jaguar_supplemental_geonames_coords.csv")
with open(geo_out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(geo_rows[0].keys()))
    w.writeheader()
    w.writerows(geo_rows)
print(f"GeoNames JAGUAR coord lookup (supplemental only): {len(geo_rows)} rows ({geo_by_jur})")
summary["jaguar_supplemental_geonames_coords"] = {
    "rows": len(geo_rows), "by_jurisdiction": geo_by_jur, "role": "supplemental_coordinates_only"
}

with open(os.path.join(PARSED, "_ca_caribbean_parse_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print("DONE parsing PR, USVI, INSEE, UNSD, GeoNames.")
