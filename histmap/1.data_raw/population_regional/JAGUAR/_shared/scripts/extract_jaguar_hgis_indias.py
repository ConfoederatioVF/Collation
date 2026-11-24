import os
import csv
import json
import struct
import sqlite3
import zipfile

HGIS_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\subadmin_hgis\raw_sources\hgis_indias"
OUT_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\settlement_sources\raw\hgis_indias_colonial"
os.makedirs(OUT_DIR, exist_ok=True)

# JAGUAR Audiencias in HGIS de las Indias:
# NES = Nueva Espana (Central/Southern Mexico)
# GDJ = Guadalajara (Western/Northern Mexico)
# GUA = Guatemala (Central America + Chiapas)
# TFI = Tierra Firme (Panama)
# SDO = Santo Domingo (Cuba, Hispaniola, Puerto Rico, Jamaica, Trinidad, Venezuela coast -> filter by bbox!)
REG_TO_JUR = {
    "NES": "mexico",
    "GDJ": "mexico",
    "GUA": "central_america",
    "TFI": "central_america",
    "SDO": "caribbean",
}

def parse_gpkg_point(blob):
    """Parse GeoPackage StandardGeoPackageBinary Point (little/big endian WKB)."""
    if not blob or len(blob) < 29:
        return None, None
    # Magic 'GP'
    if blob[0:2] != b"GP":
        return None, None
    flags = blob[3]
    env_ind = (flags >> 1) & 0x07
    env_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    offset = 8 + env_sizes.get(env_ind, 0)
    if offset + 21 > len(blob):
        return None, None
    byte_order = blob[offset]
    endian = "<" if byte_order == 1 else ">"
    wkb_type = struct.unpack(endian + "I", blob[offset+1:offset+5])[0]
    geom_type = wkb_type & 0xFF
    if geom_type == 1:  # Point
        x, y = struct.unpack(endian + "dd", blob[offset+5:offset+21])
        return round(y, 6), round(x, 6)
    return None, None

def in_jaguar_bbox(lat, lon, reg):
    if reg not in REG_TO_JUR:
        return False
    if lat is None or lon is None:
        return True
    # Strict JAGUAR geographic envelope (Mexico <= 32.72 N, Central America >= 7.1 N, Caribbean islands excluding SA mainland)
    if lat < 7.1 or lat > 32.75 or lon < -118.5 or lon > -58.5:
        return False
    # Exclude mainland Venezuela/Colombia in SDO (Trinidad is ~10.0-10.85 N, -61.95 to -60.9 W; Margarita/Curaçao/Aruba >= 11.9 N)
    if reg == "SDO" and lat < 11.9:
        if not (10.0 <= lat <= 11.4 and -62.0 <= lon <= -60.4):
            return False
    # Exclude Colombian Choco/Darien south-east of Panama border (lon > -77.15 & lat < 9.5)
    if reg == "TFI" and lon > -77.15 and lat < 9.5:
        return False
    return True

# 1. Extract spatial + demographic places from demografia_lugares.gpkg
gpkg_path = os.path.join(HGIS_DIR, "demografia_lugares.gpkg")
con = sqlite3.connect(gpkg_path)
con.row_factory = sqlite3.Row
cur = con.cursor()
cols = [c[1] for c in cur.execute('PRAGMA table_info("demografia_lugares")').fetchall()]
keep_cols = [
    "it_ID", "it_Label", "it_GZ_ID", "it_Contexto_Sup1", "it_Contexto_Sup2",
    "it_Contexto_Sup3", "it_Contexto_Sup4", "it_REG", "it_Alcance_tipo",
    "it_START_", "it_END_", "it_Fecha_Dato", "it_Dato_tipo", "it_Fuente",
    "it_Total", "it_Blancos", "it_Indios", "it_Mestizos", "it_Castas",
    "it_Esclavos", "it_Vecinos_doc", "it_Tributarios_doc", "it_Familias_doc", "it_Total_doc"
]
avail_cols = [c for c in keep_cols if c in cols]

by_jur = {"mexico": [], "central_america": [], "caribbean": []}
all_rows = []
for row in cur.execute('SELECT * FROM "demografia_lugares"'):
    reg = (row["it_REG"] or "").strip()
    lat, lon = parse_gpkg_point(row["geom"])
    if not in_jaguar_bbox(lat, lon, reg):
        continue
    jur = REG_TO_JUR[reg]
    # Note: Chiapas & Soconusco were under Audiencia de Guatemala (GUA) colonially, modern Mexico
    if reg == "GUA" and lat is not None and lon is not None and lon < -92.15 and lat > 14.8:
        jur = "mexico"
    if reg in ("NES", "GDJ") and lat is not None and lon is not None and lat > 32.6:
        # Alta California / New Mexico / Texas outside modern Mexico (CENTAUR domain)
        continue

    rec = {
        "jurisdiction": jur,
        "colonial_audiencia": reg,
        "lat": lat if lat is not None else "",
        "lon": lon if lon is not None else "",
    }
    for c in avail_cols:
        rec[c.replace("it_", "")] = row[c] if row[c] is not None else ""
    by_jur[jur].append(rec)
    all_rows.append(rec)
con.close()

# Write per-jurisdiction CSVs + combined JAGUAR HGIS Indias CSV
fieldnames = ["jurisdiction", "colonial_audiencia", "lat", "lon"] + [c.replace("it_", "") for c in avail_cols]
for jur, rlist in by_jur.items():
    out_csv = os.path.join(OUT_DIR, f"hgis_indias_colonial_lugares_{jur}.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rlist)
    print(f"HGIS GPKG [{jur}]: {len(rlist)} rows -> {os.path.basename(out_csv)}")

out_all = os.path.join(OUT_DIR, "hgis_indias_colonial_lugares_jaguar_all.csv")
with open(out_all, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(all_rows)

# 2. Also extract full JAGUAR rows from da_dem_lugares.csv (in case some lack geometry in GPKG)
da_csv = os.path.join(HGIS_DIR, "da_dem_lugares.csv")
da_out = os.path.join(OUT_DIR, "hgis_indias_da_dem_lugares_jaguar.csv")
da_count = 0
with open(da_csv, "r", encoding="utf-8-sig", errors="replace") as fin:
    reader = csv.DictReader(fin, delimiter=";")
    out_fields = ["jurisdiction"] + list(reader.fieldnames)
    with open(da_out, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=out_fields)
        writer.writeheader()
        for r in reader:
            reg = r.get("REG", "")
            if reg in REG_TO_JUR:
                r["jurisdiction"] = REG_TO_JUR[reg]
                writer.writerow(r)
                da_count += 1
print(f"HGIS da_dem_lugares JAGUAR rows: {da_count}")

# 3. Extract cabeceras.tab (colonial administrative seats) & fuentes.tab (primary archival bibliography!)
for tab_name in ("cabeceras.tab", "fuentes.tab"):
    src = os.path.join(HGIS_DIR, tab_name)
    if os.path.exists(src):
        with open(src, "r", encoding="utf-8", errors="replace") as fin:
            lines = fin.readlines()
        dst = os.path.join(OUT_DIR, f"hgis_indias_{tab_name.replace('.tab', '.tsv')}")
        with open(dst, "w", encoding="utf-8") as fout:
            fout.writelines(lines)
        print(f"Copied HGIS {tab_name}: {len(lines)-1} rows")

summary = {
    "source": "Stangl, Werner (2020/2023), HGIS de las Indias, Harvard Dataverse (doi:10.7910/DVN/FUSJDW)",
    "gpkg_total_jaguar": len(all_rows),
    "gpkg_by_jurisdiction": {k: len(v) for k, v in by_jur.items()},
    "da_dem_lugares_jaguar": da_count,
}
with open(os.path.join(OUT_DIR, "_hgis_indias_extract_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print("DONE HGIS de las Indias extraction:", summary)
