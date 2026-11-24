import os
import re
import csv
import io
import json
import shutil
import zipfile
import pymupdf

BASE = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\settlement_sources"
RAW = os.path.join(BASE, "raw")
PARSED = os.path.join(BASE, "parsed")
os.makedirs(PARSED, exist_ok=True)

# 0. Copy official INEGI EHM 2014 PDF into raw/ so settlement_sources/raw/ is 100% self-contained
EHM_SRC = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\subadmin_hgis\raw_sources\inegi_ehm2014_1_poblacion.pdf"
EHM_DST = os.path.join(RAW, "mexico_inegi_ehm2014_1_poblacion.pdf")
if os.path.exists(EHM_SRC) and not os.path.exists(EHM_DST):
    shutil.copy2(EHM_SRC, EHM_DST)

# ---------------------------------------------------------------------------
# PART 1: Parse INEGI EHM 2014 Historical City Population Tables (Cuadro 1.51+)
# ---------------------------------------------------------------------------
def extract_ehm_city_tables(pdf_path):
    doc = pymupdf.open(pdf_path)
    city_rows = []
    current_cuadro = None
    current_city = None
    tables_found = {}

    for pno in range(len(doc)):
        page = doc[pno]
        words = page.get_text("words")  # (x0, y0, x1, y1, word, block, line, word_no)
        full_text = page.get_text("text")

        # Check if this page starts or continues a city table (Cuadro 1.51 .. 1.99)
        m_cuadros = list(re.finditer(r"Cuadro\s+(1\.(\d+))", full_text))
        # Use y-ordered line reconstruction by splitting page into top/bottom sections if 2 tables per page!
        # Group words into visual lines by rounded y0 (tolerance 3pt)
        page_w = page.rect.width
        # Detect exact x-coordinate of the second 'Año' column header if present
        ano_xs = sorted(w[0] for w in words if w[4].strip() == "Año")
        if len(ano_xs) >= 2 and (ano_xs[-1] - ano_xs[0]) > 100:
            mid_x = ano_xs[-1] - 8.0
        else:
            mid_x = page_w * 0.48

        # Detect Cuadro headers and their y-coordinates
        headers_on_page = []
        lines_by_y = {}
        for w in words:
            ykey = round(w[1] / 3.0) * 3.0
            lines_by_y.setdefault(ykey, []).append(w)

        sorted_ys = sorted(lines_by_y.keys())
        # First pass: locate all "Población total de ..." / "Cuadro 1.XX" headers
        for idx, yk in enumerate(sorted_ys):
            ws = sorted(lines_by_y[yk], key=lambda x: x[0])
            line_txt = " ".join(x[4] for x in ws)
            mc = re.search(r"Cuadro\s+(1\.(\d+))", line_txt)
            if mc:
                cnum = int(mc.group(2))
                # Look at 1-2 lines above for title
                title_parts = []
                for back in range(max(0, idx - 3), idx + 1):
                    btxt = " ".join(x[4] for x in sorted(lines_by_y[sorted_ys[back]], key=lambda x: x[0]))
                    if "Población total" in btxt or (title_parts and "Cuadro" not in btxt and "Años" not in btxt):
                        title_parts.append(btxt)
                title = re.sub(r"\s*Cuadro\s+1\.\d+.*", "", " ".join(title_parts)).strip()
                headers_on_page.append((yk, mc.group(1), cnum, title))

        # Only process city tables (Cuadro 1.51 onward; 1.20-1.50 are state tables)
        # Assign each y-band to its active Cuadro
        def get_active_cuadro(y_val):
            act_c, act_num, act_title = current_cuadro, (int(current_cuadro.split(".")[1]) if current_cuadro else 0), current_city
            for hy, cid, cnum, ctitle in headers_on_page:
                if y_val >= hy - 2:
                    act_c, act_num, act_title = cid, cnum, ctitle
            return act_c, act_num, act_title

        # Parse left half (x < mid_x) and right half (x >= mid_x) per y-line
        # Track active multi-line source continuation per half
        for half_idx, (xmin, xmax) in enumerate([(0, mid_x), (mid_x, page_w + 10)]):
            last_rec = None
            for yk in sorted_ys:
                act_c, act_num, act_title = get_active_cuadro(yk)
                if act_num < 51:
                    continue
                if not act_title or "estado de" in act_title.lower() or "distrito federal" in act_title.lower():
                    # Keep Ciudad de Mexico (Cuadro 1.54), exclude state-level tables
                    if "ciudad de" not in (act_title or "").lower():
                        continue
                ws = [w for w in sorted(lines_by_y[yk], key=lambda x: x[0]) if xmin <= w[0] < xmax]
                if not ws:
                    continue
                ltxt = " ".join(w[4] for w in ws).strip()
                if any(ltxt.startswith(k) for k in ("Año", "Población", "Cuadro", "Años seleccionados", "Nota:", "Fuente:", "INEGI.", "(Continúa)", "(Concluye)", "a Se refiere", "b Se refiere", "c Se refiere")):
                    last_rec = None
                    continue

                # Match: YEAR [footnote_letter]  POP_DIGITS_WITH_SPACES  SOURCE_TEXT
                m = re.match(r"^(\d{4})(?:\s+[a-z])?\s+([\d][\d\s]{1,12}?)\s+([A-Za-z0-9ÁÉÍÓÚÑáéíóúñ].*)$", ltxt)
                if m:
                    yr = int(m.group(1))
                    pop_str = re.sub(r"\s+", "", m.group(2))
                    src = m.group(3).strip()
                    # Guard against matching a digit inside pop as source if source starts with single digit unless Roman/II/III/IV/etc.
                    if src and src[0].isdigit():
                        m2 = re.match(r"^(\d{4})(?:\s+[a-z])?\s+([\d\s]+?)\s+([A-Za-zÁÉÍÓÚÑáéíóúñ].*)$", ltxt)
                        if m2:
                            pop_str = re.sub(r"\s+", "", m2.group(2))
                            src = m2.group(3).strip()
                    if 1500 <= yr <= 2025 and pop_str.isdigit():
                        city_clean = re.sub(r"^Población total de (?:la )?(?:ciudad de )?", "", act_title, flags=re.I).strip()
                        if act_c == "1.54":
                            city_clean = "Ciudad de México"
                        rec = {
                            "jurisdiction": "mexico",
                            "cuadro": act_c,
                            "city_label": city_clean,
                            "year": yr,
                            "population": int(pop_str),
                            "primary_source": src,
                            "publication": "INEGI Estadísticas Históricas de México 2014 (2015)",
                        }
                        city_rows.append(rec)
                        tables_found[act_c] = city_clean
                        last_rec = rec
                elif last_rec is not None and not re.match(r"^\d", ltxt) and len(ltxt) < 60:
                    # Continuation line of source name
                    if not any(x in ltxt for x in ("Nota", "Población total", "INEGI")):
                        last_rec["primary_source"] = (last_rec["primary_source"] + " " + ltxt).strip()

        if headers_on_page:
            current_cuadro = headers_on_page[-1][1]
            current_city = headers_on_page[-1][3]

    doc.close()
    # Sort neatly by cuadro, year
    city_rows.sort(key=lambda r: (float(r["cuadro"]), r["year"]))
    return city_rows, tables_found

ehm_rows, ehm_tables = extract_ehm_city_tables(EHM_DST)
ehm_csv = os.path.join(PARSED, "mexico_inegi_ehm2014_historical_cities_1742_2010.csv")
if ehm_rows:
    with open(ehm_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ehm_rows[0].keys()))
        w.writeheader()
        w.writerows(ehm_rows)
print(f"INEGI EHM 2014 Historical Cities: {len(ehm_rows)} city-year rows across {len(ehm_tables)} cities (years {min(r['year'] for r in ehm_rows)}-{max(r['year'] for r in ehm_rows)})")
for k, v in sorted(ehm_tables.items(), key=lambda x: float(x[0]))[:10]:
    print(f"  {k}: {v}")

# ---------------------------------------------------------------------------
# PART 2: FULL-ROW INEGI ITER 1990, 2000, 2010, 2020 Consolidation
# ---------------------------------------------------------------------------
def dms_to_dec(val, is_lon=False):
    if not val:
        return None
    s = str(val).strip().strip('"').replace(" ", "")
    if not s or s in ("*", "N/D", "ND"):
        return None
    # Format 1: 99°07'59.566" W  or  19°25'57.389" N
    m = re.match(r"(\d+)°(\d+)'([\d\.]+)\"([NSEW])?", s)
    if m:
        deg = float(m.group(1)) + float(m.group(2)) / 60.0 + float(m.group(3)) / 3600.0
        hemi = m.group(4) or ("W" if is_lon else "N")
        if hemi in ("S", "W") or (is_lon and deg > 0):
            deg = -abs(deg)
        return round(deg, 6)
    # Format 2: numeric DDMMSS or DDDMMSS (used in ITER 1990/2000/2010)
    digits = re.sub(r"[^\d]", "", s)
    if len(digits) in (6, 7):
        sec = float(digits[-2:])
        mn = float(digits[-4:-2])
        dg = float(digits[:-4])
        deg = dg + mn / 60.0 + sec / 3600.0
        if is_lon:
            deg = -abs(deg)
        return round(deg, 6)
    # Format 3: already decimal
    try:
        v = float(s)
        if is_lon and v > 0:
            v = -v
        if (is_lon and -120 <= v <= -85) or (not is_lon and 13 <= v <= 33):
            return round(v, 6)
    except Exception:
        pass
    return None

# Extra-municipal suburban municipalities of Mexico's 3 largest metros (ZMVM, ZMG, ZMM)
# Preserved as DISTINCT settlements tagged population_scope="suburb" (outside central municipal limits!)
ZMVM_SUBURB_MUNS_EDOMEX = {
    "15002","15011","15013","15020","15023","15024","15025","15028","15029","15030","15031",
    "15033","15035","15037","15039","15044","15053","15057","15058","15059","15060","15068",
    "15069","15070","15075","15081","15083","15084","15091","15092","15093","15095","15099",
    "15100","15103","15104","15108","15109","15120","15121","15122","15125",
    "13069", # Tizayuca, Hidalgo
}
ZMG_SUBURB_MUNS = {"14120", "14098", "14101", "14097", "14070", "14044", "14051"} # Zapopan, Tlaquepaque, Tonala, Tlajomulco, El Salto, Ixtlahuacan, Juanacatlan
ZMM_SUBURB_MUNS = {"19026", "19006", "19046", "19021", "19048", "19019", "19018", "19031", "19009", "19045"} # Guadalupe, Apodaca, San Nicolas, Escobedo, Santa Catarina, San Pedro, Garcia, Juarez, Cadereyta, Salinas Victoria

iter_specs = [
    (2020, "mexico_inegi_iter_2020_csv.zip", "iter_00_cpv2020/conjunto_de_datos/conjunto_de_datos_iter_00CSV20.csv", ",", "POBTOT", "utf-8-sig"),
    (2010, "mexico_inegi_iter_2010_csv.zip", "iter_00_cpv2010/conjunto_de_datos/iter_00_cpv2010.csv", ",", "pobtot", "utf-8-sig"),
    (2000, "mexico_inegi_iter_2000_csv.zip", "cgpv2000_iter_00/conjunto_de_datos/cgpv2000_iter_00.csv", ",", "pobtot", "utf-8-sig"),
    (1990, "mexico_inegi_iter_1990_txt.zip", "ITER_NALTXT90.txt", "\t", "p_total", "latin-1"),
]

panel = {}  # cvegeo -> dict
cdmx_totals = {1990: 0, 2000: 0, 2010: 0, 2020: 0}
cdmx_alcaldia_rows_consolidated = {1990: 0, 2000: 0, 2010: 0, 2020: 0}
raw_counts = {}

for yr, zname, inner, delim, pop_col, enc in iter_specs:
    zp = os.path.join(RAW, zname)
    total_rows = 0
    valid_locs = 0
    with zipfile.ZipFile(zp) as z:
        with z.open(inner) as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding=enc, errors="replace"), delimiter=delim)
            # Normalize field names to lowercase, stripping BOM and quotes
            fmap = {k.replace("\ufeff", "").replace("ï»¿", "").strip().strip('"').lower(): k for k in reader.fieldnames}
            k_ent = fmap["entidad"]
            k_noment = fmap["nom_ent"]
            k_mun = fmap["mun"]
            k_nommun = fmap["nom_mun"]
            k_loc = fmap["loc"]
            k_nomloc = fmap["nom_loc"]
            k_lat = fmap["latitud"]
            k_lon = fmap["longitud"]
            k_pop = fmap[pop_col.lower()]

            for row in reader:
                total_rows += 1
                ent = row[k_ent].strip().zfill(2)
                mun = row[k_mun].strip().zfill(3)
                loc = row[k_loc].strip().zfill(4)
                p_str = row[k_pop].strip()
                pop = int(p_str) if p_str.isdigit() else 0

                # Capture official unified Ciudad de Mexico entity total (ENTIDAD == '09', MUN == '000', LOC == '0000')
                if ent == "09":
                    if mun == "000" and loc == "0000":
                        cdmx_totals[yr] = pop
                    elif mun != "000" and loc not in ("0000", "9998", "9999"):
                        cdmx_alcaldia_rows_consolidated[yr] += 1
                    continue  # NEVER emit CDMX alcaldias/delegaciones as separate settlements!

                # Skip national/state/municipal summary rows and confidential 1-2 dwelling aggregates
                if ent == "00" or mun == "000" or loc in ("0000", "9998", "9999"):
                    continue

                valid_locs += 1
                cvegeo = f"{ent}{mun}{loc}"
                rec = panel.get(cvegeo)
                if rec is None:
                    entmun = f"{ent}{mun}"
                    scope = "city_proper"
                    metro_parent = ""
                    if entmun in ZMVM_SUBURB_MUNS_EDOMEX:
                        scope = "suburb"
                        metro_parent = "Ciudad de México"
                    elif entmun in ZMG_SUBURB_MUNS:
                        scope = "suburb"
                        metro_parent = "Guadalajara"
                    elif entmun in ZMM_SUBURB_MUNS:
                        scope = "suburb"
                        metro_parent = "Monterrey"
                    rec = {
                        "jurisdiction": "mexico",
                        "cvegeo": cvegeo,
                        "ent": ent,
                        "nom_ent": row[k_noment].strip(),
                        "mun": mun,
                        "nom_mun": row[k_nommun].strip(),
                        "loc": loc,
                        "nom_loc": row[k_nomloc].strip(),
                        "is_cabecera_municipal": 1 if loc == "0001" else 0,
                        "population_scope": scope,
                        "metro_parent": metro_parent,
                        "lat": None,
                        "lon": None,
                        "pop_1990": "",
                        "pop_2000": "",
                        "pop_2010": "",
                        "pop_2020": "",
                        "max_pop": 0,
                    }
                    panel[cvegeo] = rec

                # Always prefer 2020/most-recent official name and coordinates
                if rec["lat"] is None:
                    lat = dms_to_dec(row[k_lat], is_lon=False)
                    lon = dms_to_dec(row[k_lon], is_lon=True)
                    if lat is not None and lon is not None:
                        rec["lat"] = lat
                        rec["lon"] = lon
                rec[f"pop_{yr}"] = pop
                if pop > rec["max_pop"]:
                    rec["max_pop"] = pop

    raw_counts[str(yr)] = {"total_raw_rows": total_rows, "valid_localities_excl_cdmx": valid_locs, "cdmx_consolidated_locality_rows": cdmx_alcaldia_rows_consolidated[yr], "cdmx_unified_pop": cdmx_totals[yr]}
    print(f"INEGI ITER {yr}: raw_rows={total_rows:,}, valid_locs={valid_locs:,}, CDMX_unified={cdmx_totals[yr]:,} (consolidated {cdmx_alcaldia_rows_consolidated[yr]} CDMX rows)")

# Add ONE unified Ciudad de Mexico city_proper record!
cdmx_rec = {
    "jurisdiction": "mexico",
    "cvegeo": "090000000",
    "ent": "09",
    "nom_ent": "Ciudad de México",
    "mun": "000",
    "nom_mun": "Ciudad de México (16 alcaldías unified)",
    "loc": "0000",
    "nom_loc": "Ciudad de México",
    "is_cabecera_municipal": 1,
    "population_scope": "city_proper",
    "metro_parent": "Ciudad de México",
    "lat": 19.432608,
    "lon": -99.133209,
    "pop_1990": cdmx_totals[1990],
    "pop_2000": cdmx_totals[2000],
    "pop_2010": cdmx_totals[2010],
    "pop_2020": cdmx_totals[2020],
    "max_pop": max(cdmx_totals.values()),
}

# Filter consolidated CSV to ALL localities >= 1,000 inh OR cabecera municipal (LOC == '0001') — zero Top-N cap!
filtered = [cdmx_rec] + [r for r in panel.values() if r["max_pop"] >= 1000 or r["is_cabecera_municipal"] == 1]
filtered.sort(key=lambda r: -r["max_pop"])

iter_out = os.path.join(PARSED, "mexico_inegi_iter_1990_2020_consolidated.csv")
with open(iter_out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(cdmx_rec.keys()))
    w.writeheader()
    w.writerows(filtered)

suburb_cnt = len([r for r in filtered if r["population_scope"] == "suburb"])
print(f"CONSOLIDATED MEXICO PANEL (>=1,000 inh OR cabecera municipal): {len(filtered):,} settlements (suburbs={suburb_cnt:,}; total unique raw localities scanned={len(panel):,})")

summary = {
    "inegi_iter_raw_counts": raw_counts,
    "total_unique_raw_localities_1990_2020": len(panel) + 1,
    "consolidated_panel_rows_ge1000_or_cabecera": len(filtered),
    "cdmx_non_decomposition": {
        "unified_entity": "Ciudad de México",
        "cvegeo": "090000000",
        "alcaldias_consolidated": 16,
        "pop_1990": cdmx_totals[1990],
        "pop_2000": cdmx_totals[2000],
        "pop_2010": cdmx_totals[2010],
        "pop_2020": cdmx_totals[2020],
        "preserved_extra_municipal_suburbs_count": suburb_cnt,
    },
    "inegi_ehm2014_historical_cities": {
        "rows": len(ehm_rows),
        "unique_cities": len(ehm_tables),
        "min_year": min(r["year"] for r in ehm_rows) if ehm_rows else None,
        "max_year": max(r["year"] for r in ehm_rows) if ehm_rows else None,
        "cities": list(ehm_tables.values()),
    },
}
with open(os.path.join(PARSED, "_mexico_parse_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
print("DONE Mexico Wave 1 parsing.")
