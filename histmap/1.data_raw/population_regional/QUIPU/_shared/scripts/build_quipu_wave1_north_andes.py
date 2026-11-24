"""Builds Stage C Wave 1 raw settlement census files for Northern & Central Andes:
  - raw_setts_colombia.json
  - raw_setts_venezuela.json
  - raw_setts_ecuador.json
  - raw_setts_peru.json
"""

import csv
import json
import os
import re
import openpyxl
import pandas as pd
import rdata

from quipu_wave1_utils import (
    GEO_DIR,
    RAW_DIR,
    clean_city_name,
    load_geojson_centroids,
    load_hgis_coords_by_iso,
    load_unsd_country,
    norm_text,
    parse_citypop_html,
    to_float,
    to_int,
    write_settlements_json,
)

COL_ADM1_ABBR = {
    "AMA": "Amazonas", "ANT": "Antioquia", "ARA": "Arauca", "ATL": "Atlántico",
    "BOL": "Bolívar", "BOY": "Boyacá", "CAL": "Caldas", "CAQ": "Caquetá",
    "CAS": "Casanare", "CAU": "Cauca", "CES": "Cesar", "CHO": "Chocó",
    "COR": "Córdoba", "CUN": "Cundinamarca", "DE": "Bogotá, D.C.",
    "DC": "Bogotá, D.C.", "GUA": "Guainía", "GUV": "Guaviare", "HUI": "Huila",
    "LAG": "La Guajira", "MAG": "Magdalena", "MET": "Meta", "NAR": "Nariño",
    "NSA": "Norte de Santander", "PUT": "Putumayo", "QUI": "Quindío",
    "RIS": "Risaralda", "SAP": "San Andrés y Providencia", "SAN": "Santander",
    "SUC": "Sucre", "TOL": "Tolima", "VAC": "Valle del Cauca", "VAU": "Vaupés",
    "VID": "Vichada",
}

VEN_ADM1_ABBR = {
    "AMA": "Amazonas", "ANZ": "Anzoátegui", "APU": "Apure", "ARA": "Aragua",
    "BAR": "Barinas", "BOL": "Bolívar", "CAR": "Carabobo", "COJ": "Cojedes",
    "DC": "Distrito Capital", "DEA": "Delta Amacuro", "FAL": "Falcón",
    "GUA": "Guárico", "LAR": "Lara", "MER": "Mérida", "MIR": "Miranda",
    "MON": "Monagas", "NES": "Nueva Esparta", "POR": "Portuguesa",
    "SUC": "Sucre", "TAC": "Táchira", "TRU": "Trujillo", "VAR": "La Guaira",
    "YAR": "Yaracuy", "ZUL": "Zulia",
}


def extract_citypop_href_map(arg0_html_path):
    """Maps normalised city name -> href path segments for exact ADM2/code matching."""
    if not os.path.exists(arg0_html_path):
        return {}
    html = open(arg0_html_path, "r", encoding="utf-8", errors="replace").read()
    links = re.findall(r'href="(/en/[^"]+)"[^>]*>([^<]+)</a>', html)
    out = {}
    for href, label in links:
        parts = [p for p in href.strip("/").split("/") if p]
        out.setdefault(norm_text(label), []).append(parts)
    return out


def build_colombia():
    col_dir = os.path.join(RAW_DIR, "nso_colombia")
    divipola = json.load(open(os.path.join(col_dir, "divipola_municipios.json"), "r", encoding="utf-8"))
    div_cp = json.load(open(os.path.join(col_dir, "divipola_centros_poblados.json"), "r", encoding="utf-8"))
    coords_by_code = {}
    name_by_code = {}
    dept_by_code = {}
    cp_coords_by_norm = {}
    for r in div_cp:
        lat = to_float(r.get("latitud"))
        lon = to_float(r.get("longitud"))
        nm = (r.get("nombre_centro_poblado") or "").strip()
        dp = (r.get("nombre_departamento") or "").strip()
        if lat is not None and lon is not None and nm:
            cp_coords_by_norm.setdefault((norm_text(nm), norm_text(dp)), [lat, lon])
            cp_coords_by_norm.setdefault((norm_text(nm), ""), [lat, lon])
    for r in divipola:
        code = str(r.get("cod_mpio", "")).zfill(5)
        lat = to_float(r.get("latitud"))
        lon = to_float(r.get("longitud"))
        nom = (r.get("nom_mpio") or "").strip().title()
        dpto = (r.get("dpto") or "").strip().title()
        if lat is not None and lon is not None:
            coords_by_code[code] = [lat, lon]
        name_by_code[code] = nom
        dept_by_code[code] = dpto

    # Fallback ADM2 polygons if any DIVIPOLA point missing
    adm2_cent = load_geojson_centroids(os.path.join(GEO_DIR, "COL_ADM2.geojson"))
    target_years = {1985, 1990, 1993, 1995, 2000, 2005, 2010, 2015, 2018, 2020, 2023, 2025}

    mun_data = {}
    specs = [
        ("dane_mun_1985_1994.xlsx", "Municipal", 11, "Población"),
        ("dane_mun_1995_2004.xlsx", "Municipal", 11, "Población"),
        ("dane_mun_2005_2017.xlsx", "NuevaMpal", 11, "Población"),
        ("dane_mun_2018_2042.xlsx", "PobMunicipalxÁrea", 7, "TOTAL"),
    ]
    for fn, sh, skip, pop_col in specs:
        df = pd.read_excel(os.path.join(col_dir, fn), sheet_name=sh, skiprows=skip)
        for _, row in df.iterrows():
            yr = to_int(row.get("AÑO"))
            if yr not in target_years:
                continue
            raw_dpmp = row.get("DPMP")
            raw_mpio = row.get("MPIO")
            if pd.isna(raw_dpmp) or pd.isna(raw_mpio):
                continue
            s_dpmp = str(int(raw_dpmp)) if isinstance(raw_dpmp, (int, float)) else str(raw_dpmp).strip()
            s_mpio = str(int(raw_mpio)) if isinstance(raw_mpio, (int, float)) else str(raw_mpio).strip()
            # DANE 2005-2017 swaps DPMP and MPIO header names
            if not s_dpmp.isdigit() and s_mpio.isdigit():
                code, nm_raw = s_mpio.zfill(5), s_dpmp
            else:
                code, nm_raw = s_dpmp.zfill(5), s_mpio
            area = str(row.get("ÁREA GEOGRÁFICA", "")).strip().lower()
            pop = to_int(row.get(pop_col))
            if pop is None:
                continue
            if code not in mun_data:
                nm = name_by_code.get(code) or nm_raw.strip()
                dp = dept_by_code.get(code) or str(row.get("DPNOM") or "").strip()
                if code == "11001" or "bogot" in nm.lower():
                    nm = "Bogotá"
                mun_data[code] = {
                    "name": nm,
                    "dept": dp,
                    "pop": {},
                    "cabecera": {},
                }
            if area == "total":
                mun_data[code]["pop"][str(yr)] = pop
            elif "cabecera" in area:
                mun_data[code]["cabecera"][str(yr)] = pop

    settlements = {}
    by_norm_key = {}
    for code, info in mun_data.items():
        nm = info["name"]
        dp = info["dept"]
        coords = coords_by_code.get(code)
        csource = "DANE_DIVIPOLA" if coords else None
        if not coords:
            clean_nm = re.sub(r"\s*\(ANM\)\s*$", "", nm, flags=re.I).strip()
            coords = cp_coords_by_norm.get((norm_text(clean_nm), norm_text(dp))) or cp_coords_by_norm.get((norm_text(clean_nm), ""))
            if coords:
                csource = "DANE_DIVIPOLA_CentrosPoblados"
        if not coords and norm_text(nm) in adm2_cent:
            c0 = adm2_cent[norm_text(nm)][0]
            coords = [c0[0], c0[1]]
            csource = "geoBoundaries_COL_ADM2"
        key = f"{nm}-{dp}-Colombia" if nm in ("Armenia", "Rionegro", "San Martín", "Buenavista", "El Carmen", "Mosquera", "Ricaurte", "Santander", "Villanueva", "Guadalupe", "Pueblorrico", "Santa Rosa", "San Luis", "San Carlos", "San Pablo", "La Unión", "La Paz", "La Victoria", "Belén", "Bolívar", "Córdoba", "Granada", "Miraflores", "Palestina", "Paraíso", "San Antonio", "San José", "San Juan", "San Pedro", "Santa Bárbara", "Santa María", "Toledo", "Versalles") or f"{nm}-Colombia" in settlements else f"{nm}-Colombia"
        if key in settlements:
            key = f"{nm} ({dp})-Colombia"
        rec = {
            "name": nm,
            "other_names": ["Bogotá D.C.", "Santafé de Bogotá"] if code == "11001" else [],
            "coords": coords,
            "coord_source": csource,
            "country": "Colombia",
            "admin1": dp,
            "admin_code": code,
            "population_scope": "city_proper",
            "is_capital": code == "11001",
            "population": info["pop"],
            "urban_cabecera_population": info["cabecera"],
            "sources": ["DANE Colombia (1985-2042 Municipal Population Series, CNPV 2018 baseline)"],
        }
        settlements[key] = rec
        by_norm_key[(norm_text(nm), norm_text(dp))] = key
        by_norm_key.setdefault((norm_text(nm), ""), key)

    # Merge citypopulation Colombia urban localities + historical 1918-1973 major cities
    cp_hrefs = extract_citypop_href_map(os.path.join(RAW_DIR, "citypopulation_mirrors", "colombia_cities.html"))
    cp = parse_citypop_html(os.path.join(RAW_DIR, "citypopulation_mirrors", "colombia_cities.html"))
    for r in cp.get("ts", {}).get("rows", []):
        cells = r["cells"]
        if len(cells) < 8:
            continue
        cname, aliases = clean_city_name(cells[1])
        adm_abbr = cells[2].strip()
        dept_nm = COL_ADM1_ABBR.get(adm_abbr, adm_abbr)
        # Match via href 8-digit code (first 5 digits = DPMP)
        matched_code = None
        for parts in cp_hrefs.get(norm_text(cells[1]), []):
            if len(parts) >= 5 and re.match(r"^\d{5}", parts[-1]):
                matched_code = parts[-1][:5]
                break
        target_key = None
        if matched_code:
            for k, v in settlements.items():
                if v.get("admin_code") == matched_code:
                    target_key = k
                    break
        if not target_key:
            target_key = by_norm_key.get((norm_text(cname), norm_text(dept_nm))) or by_norm_key.get((norm_text(cname), ""))
        urban_obs = {}
        for ci, yr in cp["ts"]["year_cols"]:
            if ci < len(cells):
                val = to_int(cells[ci])
                if val is not None:
                    urban_obs[str(yr)] = val
        if target_key:
            st = settlements[target_key]
            for a in aliases:
                if a not in st["other_names"]:
                    st["other_names"].append(a)
            st.setdefault("urban_locality_census", {}).update(urban_obs)
            if "DANE Censuses 1985-2023 (via citypopulation.de)" not in st["sources"]:
                st["sources"].append("DANE Censuses 1985-2023 (via citypopulation.de)")

    # UNSD Demographic Yearbook
    unsd = load_unsd_country("Colombia")
    for (_, scope), urec in unsd.items():
        if scope == "city_proper":
            tk = by_norm_key.get((norm_text(urec["name"]), ""))
            if tk:
                settlements[tk].setdefault("unsd_population", {}).update(urec["pop"])
                if "UNSD Demographic Yearbook Table 8" not in settlements[tk]["sources"]:
                    settlements[tk]["sources"].append("UNSD Demographic Yearbook Table 8")

    # Verified DANE / Contraloría historical 1918, 1938, 1951, 1964, 1973 major cities
    hist_col = {
        "11001": {"1918": 143994, "1938": 330312, "1951": 648324, "1964": 1697311, "1973": 2571548},
        "05001": {"1918": 79146, "1938": 168266, "1951": 358189, "1964": 772887, "1973": 1093191},
        "76001": {"1918": 45525, "1938": 101883, "1951": 284186, "1964": 637929, "1973": 918057},
        "08001": {"1918": 64543, "1938": 152348, "1951": 279627, "1964": 498301, "1973": 665917},
    }
    for code, hpop in hist_col.items():
        for st in settlements.values():
            if st.get("admin_code") == code:
                for y, v in hpop.items():
                    st["population"].setdefault(y, v)
                st["sources"].append("DANE / Contraloría General de la República Historical Censuses (1918-1973)")

    write_settlements_json(
        "raw_setts_colombia.json",
        {
            "jurisdiction": "colombia",
            "country": "Colombia",
            "sources": [
                "DANE Colombia (1985-2042 Municipal Series, CNPV 2018)",
                "DANE DIVIPOLA Georeferenced Municipalities (datos.gov.co)",
                "DANE Censuses 1985-2023 (via citypopulation.de)",
                "UNSD Demographic Yearbook Table 8",
                "DANE / Contraloría Historical Censuses (1918-1973)",
            ],
            "bogota_non_decomposition": "Bogotá D.C. (11001) retained as single unified municipal city_proper entity.",
        },
        settlements,
    )


def build_venezuela():
    import zipfile
    hdx_csv = os.path.join(RAW_DIR, "hdx_cod_ps", "ven_admpop_adm2_2011_v3.csv")
    adm2_cent = load_geojson_centroids(os.path.join(GEO_DIR, "VEN_ADM2.geojson"))
    hgis_coords = load_hgis_coords_by_iso("VEN")

    # Exact ADM2_PCODE + adminpoint coordinates from OCHA COD-AB ven_adm_boundaries.geojson.zip
    codab_pcode_coords = {}
    codab_name_coords = {}
    ven_zip = os.path.join(RAW_DIR, "nso_venezuela", "ven_adm_boundaries.geojson.zip")
    if os.path.exists(ven_zip):
        with zipfile.ZipFile(ven_zip) as z:
            gj2 = json.loads(z.read("ven_admin2.geojson").decode("utf-8"))
            for feat in gj2.get("features", []):
                pr = feat.get("properties", {})
                pc = str(pr.get("adm2_pcode") or "").strip()
                lat, lon = to_float(pr.get("center_lat")), to_float(pr.get("center_lon"))
                if pc and lat is not None and lon is not None:
                    codab_pcode_coords[pc] = [lat, lon]
                    codab_name_coords[(norm_text(pr.get("adm1_name")), norm_text(pr.get("adm2_name")))] = [lat, lon]
                    codab_name_coords.setdefault(("", norm_text(pr.get("adm2_name"))), [lat, lon])
            pts = json.loads(z.read("ven_adminpoints.geojson").decode("utf-8"))
            for feat in pts.get("features", []):
                pr = feat.get("properties", {})
                lat, lon = to_float(pr.get("y_coord")), to_float(pr.get("x_coord"))
                nm = pr.get("name") or pr.get("adm3_name") or pr.get("adm2_name") or ""
                st = pr.get("adm1_name") or ""
                if nm and lat is not None and lon is not None:
                    codab_name_coords.setdefault((norm_text(st), norm_text(nm)), [lat, lon])
                    codab_name_coords.setdefault(("", norm_text(nm)), [lat, lon])

    settlements = {}
    by_norm_mun = {}
    by_norm_state_mun = {}

    with open(hdx_csv, "r", encoding="utf-8-sig", errors="replace") as f:
        for r in csv.DictReader(f):
            mun = (r.get("ADM2_ES") or "").strip()
            est = (r.get("ADM1_ES") or "").strip()
            pcode = (r.get("ADM2_PCODE") or "").strip()
            pop2011 = to_int(r.get("T_TL"))
            if not mun or pop2011 is None:
                continue
            coords = codab_pcode_coords.get(pcode)
            csource = "OCHA_INE_CODAB_ADM2" if coords else None
            if not coords and norm_text(mun) in adm2_cent:
                cands = adm2_cent[norm_text(mun)]
                coords = [cands[0][0], cands[0][1]]
                csource = "geoBoundaries_VEN_ADM2"
            if coords and coords[1] > -59.8:  # Exclude Essequibo outside de facto Venezuela
                continue
            is_caracas_core = pcode == "VE0101"
            disp_name = "Caracas" if is_caracas_core else mun
            other = ["Municipio Libertador", "Distrito Capital"] if is_caracas_core else []
            key = f"{disp_name}-Venezuela"
            if key in settlements:
                key = f"{disp_name} ({est})-Venezuela"
            settlements[key] = {
                "name": disp_name,
                "other_names": other,
                "coords": coords,
                "coord_source": csource,
                "country": "Venezuela",
                "admin1": est,
                "admin_code": pcode,
                "population_scope": "city_proper",
                "is_capital": is_caracas_core,
                "population": {"2011": pop2011},
                "sources": ["INE Venezuela Censo 2011 (via OCHA/HDX COD-PS ven_admpop_adm2_2011_v3)"],
            }
            by_norm_mun.setdefault(norm_text(mun), key)
            by_norm_state_mun[(norm_text(est), norm_text(mun))] = key

    # Merge citypopulation.de Venezuela 210 urban localities (1981, 1990, 2001, 2011, 2019)
    cp_path = os.path.join(RAW_DIR, "citypopulation_mirrors", "venezuela_cities.html")
    cp = parse_citypop_html(cp_path)
    hrefs = extract_citypop_href_map(cp_path)

    for r in cp.get("ts", {}).get("rows", []):
        cells = r["cells"]
        if len(cells) < 8:
            continue
        cname, aliases = clean_city_name(cells[1])
        adm_abbr = cells[2].strip()
        est = VEN_ADM1_ABBR.get(adm_abbr, adm_abbr)
        pops = {}
        for ci, yr in cp["ts"]["year_cols"]:
            if ci < len(cells):
                v = to_int(cells[ci])
                if v is not None:
                    pops[str(yr)] = v
        if not pops:
            continue

        mun_slug = ""
        for parts in hrefs.get(norm_text(cells[1]), []):
            if len(parts) >= 5:
                mun_slug = parts[3].replace("_", " ")
                break
        nk_city = norm_text(cname)
        nk_mun = norm_text(mun_slug)
        nk_est = norm_text(est)

        coords = None
        csource = None
        if nk_city in hgis_coords:
            coords = list(hgis_coords[nk_city])
            csource = "HGIS_de_las_Indias"
        elif (nk_est, nk_city) in codab_name_coords:
            coords = codab_name_coords[(nk_est, nk_city)]
            csource = "OCHA_INE_CODAB"
        elif ("", nk_city) in codab_name_coords:
            coords = codab_name_coords[("", nk_city)]
            csource = "OCHA_INE_CODAB"
        elif (nk_est, nk_mun) in codab_name_coords:
            coords = codab_name_coords[(nk_est, nk_mun)]
            csource = "OCHA_INE_CODAB_municipio"
        elif ("", nk_mun) in codab_name_coords:
            coords = codab_name_coords[("", nk_mun)]
            csource = "OCHA_INE_CODAB_municipio"
        elif nk_mun:
            for (k_est, k_mun), k_coords in codab_name_coords.items():
                if k_est == nk_est and k_mun and (nk_mun in k_mun or k_mun in nk_mun):
                    coords = k_coords
                    csource = "OCHA_INE_CODAB_municipio"
                    break

        if nk_city == "caracas":
            # Caracas in ts = Libertador/urban Caracas; keep Caracas metro in tlc
            target_k = "Caracas-Venezuela"
            settlements[target_k]["population"].update(pops)
            settlements[target_k]["sources"].append("INE Venezuela Censuses 1981-2019 (via citypopulation.de)")
            continue

        # Check if same name as municipio already exists
        existing_k = by_norm_state_mun.get((nk_est, nk_city)) or by_norm_mun.get(nk_city)
        if existing_k and settlements[existing_k]["admin1"].lower() == est.lower():
            st = settlements[existing_k]
            st.setdefault("urban_locality_population", {}).update(pops)
            for y, v in pops.items():
                st["population"].setdefault(y, v)
            st["sources"].append("INE Venezuela Censuses 1981-2019 (via citypopulation.de)")
        else:
            key = f"{cname}-Venezuela" if f"{cname}-Venezuela" not in settlements else f"{cname} ({est})-Venezuela"
            settlements[key] = {
                "name": cname,
                "other_names": aliases,
                "coords": coords,
                "coord_source": csource,
                "country": "Venezuela",
                "admin1": est,
                "population_scope": "city_proper",
                "population": pops,
                "sources": ["INE Venezuela Censuses 1981-2019 (via citypopulation.de)"],
            }

    # Historical 1950, 1961, 1971, 1981 major cities + Caracas Metro
    settlements["Caracas (Metro)-Venezuela"] = {
        "name": "Caracas (Metro)",
        "other_names": ["Área Metropolitana de Caracas", "Gran Caracas"],
        "coords": [10.4806, -66.9036],
        "coord_source": "geoBoundaries_VEN_ADM2",
        "country": "Venezuela",
        "admin1": "Distrito Capital / Miranda",
        "population_scope": "metro",
        "is_capital": True,
        "population": {"1950": 704567, "1961": 1675278, "1971": 2630260, "1981": 3379540, "2019": 2087700},
        "sources": ["INE Venezuela Censuses 1950-1981 (UCV/Fundación Polar)", "INE 2019 (via citypopulation.de)"],
    }
    hist_ven = {
        "Maracaibo": {"1950": 235000, "1961": 421000, "1971": 650000},
        "Valencia": {"1950": 115000, "1961": 163000, "1971": 367000},
        "Barquisimeto": {"1950": 105000, "1961": 196000, "1971": 325000},
        "Maracay": {"1950": 91606, "1961": 174709, "1971": 356742},
        "Ciudad Guayana": {"1961": 43000, "1971": 150000},
    }
    for nm, hp in hist_ven.items():
        tk = by_norm_mun.get(norm_text(nm)) or f"{nm}-Venezuela"
        if tk in settlements:
            for y, v in hp.items():
                settlements[tk]["population"].setdefault(y, v)
            settlements[tk]["sources"].append("INE Venezuela Historical Censuses (1950-1971)")

    unsd = load_unsd_country("Venezuela")
    for (_, scope), urec in unsd.items():
        if scope == "city_proper":
            tk = by_norm_mun.get(norm_text(urec["name"]))
            if tk:
                settlements[tk].setdefault("unsd_population", {}).update(urec["pop"])

    write_settlements_json(
        "raw_setts_venezuela.json",
        {
            "jurisdiction": "venezuela",
            "country": "Venezuela",
            "sources": [
                "INE Venezuela Censo 2011 (via HDX COD-PS all 335 municipios)",
                "INE Venezuela Censuses 1981-2019 (via citypopulation.de)",
                "UNSD Demographic Yearbook Table 8",
                "INE Venezuela Historical Censuses 1950-1971",
            ],
        },
        settlements,
    )


def build_ecuador():
    ecu_dir = os.path.join(RAW_DIR, "nso_ecuador")
    adm2_cent = load_geojson_centroids(os.path.join(GEO_DIR, "ECU_ADM2.geojson"))
    hgis_coords = load_hgis_coords_by_iso("ECU")

    # Build ADM2 Pcode -> coords from ECU_ADM2.geojson (check ADM2_PCODE if present)
    pob_cant = rdata.conversion.convert(rdata.parser.parse_file(os.path.join(ecu_dir, "pobecu_pob_cantones.rda")))["pob_cantones"]
    dpa_pob = rdata.conversion.convert(rdata.parser.parse_file(os.path.join(ecu_dir, "pobecu_dpa_pob.rda")))["dpa_pob"]

    # Map dpa_canton -> (canton_name, provincia_name, cabecera_2010, cabecera_2022)
    cant_meta = {}
    for _, r in dpa_pob.iterrows():
        dc = str(r["dpa_canton"]).zfill(4)
        if dc not in cant_meta:
            cant_meta[dc] = {"canton": str(r["canton"]).strip(), "provincia": str(r["provincia"]).strip(), "cab": {}}
        if str(r["tipo"]).strip().lower() == "cabecera cantonal":
            if pd.notna(r["censo_2010"]):
                cant_meta[dc]["cab"]["2010"] = int(r["censo_2010"])
            if pd.notna(r["censo_2022"]):
                cant_meta[dc]["cab"]["2022"] = int(r["censo_2022"])

    # Aggregate pob_cantones by (dpa_canton, anio) for benchmark years
    target_yrs = {2010, 2015, 2020, 2022, 2025}
    grp = pob_cant[pob_cant["anio"].isin(target_yrs)].groupby(["dpa_canton", "anio"], as_index=False)["poblacion"].sum()

    cant_pops = {}
    for _, r in grp.iterrows():
        dc = str(r["dpa_canton"]).zfill(4)
        yr = str(int(r["anio"]))
        cant_pops.setdefault(dc, {})[yr] = int(round(float(r["poblacion"])))

    # Load ECU_AdminBoundaries_TabularData.xlsx ADM2 for exact ECxxxx -> ADM2_ES/ADM2ALT matching
    wb_ecu = openpyxl.load_workbook(os.path.join(RAW_DIR, "hdx_cod_ps", "ECU_AdminBoundaries_TabularData.xlsx"), read_only=True, data_only=True)
    ws_adm2 = wb_ecu["ADM2"]
    ec_to_name = {}
    ec_to_coords = {}
    for idx, r in enumerate(ws_adm2.iter_rows(values_only=True)):
        if idx == 0:
            continue
        if r[0] and r[1]:
            pcode = str(r[1]).strip()
            ec_to_name[pcode] = str(r[0]).strip()
            for cand_nm in (r[0], r[2], r[3], r[4]):
                if cand_nm and norm_text(cand_nm) in adm2_cent:
                    c0 = adm2_cent[norm_text(cand_nm)][0]
                    ec_to_coords[pcode] = [c0[0], c0[1]]
                    break
    wb_ecu.close()

    settlements = {}
    by_code = {}
    by_norm = {}
    for dc, pops in cant_pops.items():
        meta = cant_meta.get(dc, {"canton": ec_to_name.get(f"EC{dc}", dc), "provincia": "", "cab": {}})
        cname = meta["canton"]
        prov = meta["provincia"]
        nk = norm_text(cname)
        coords = ec_to_coords.get(f"EC{dc}")
        csource = "geoBoundaries_ECU_ADM2" if coords else None
        if not coords and nk in adm2_cent:
            c0 = adm2_cent[nk][0]
            coords = [c0[0], c0[1]]
            csource = "geoBoundaries_ECU_ADM2"
        if not coords and nk in hgis_coords:
            coords = list(hgis_coords[nk])
            csource = "HGIS_de_las_Indias"
        key = f"{cname}-Ecuador" if f"{cname}-Ecuador" not in settlements else f"{cname} ({prov})-Ecuador"
        rec = {
            "name": cname,
            "other_names": [],
            "coords": coords,
            "coord_source": csource,
            "country": "Ecuador",
            "admin1": prov,
            "admin_code": f"EC{dc}",
            "population_scope": "city_proper",
            "is_capital": dc == "1701",
            "population": pops,
            "cabecera_cantonal_population": meta["cab"],
            "sources": ["INEC Ecuador Censo 2010 & 2022 / Revision 2024 (via pobecu)"],
        }
        settlements[key] = rec
        by_code[dc] = key
        by_norm[(nk, norm_text(prov))] = key
        by_norm.setdefault((nk, ""), key)

    # Merge citypopulation Ecuador (1982, 1990, 2001, 2010, 2022)
    cp_path = os.path.join(RAW_DIR, "citypopulation_mirrors", "ecuador_cities.html")
    cp = parse_citypop_html(cp_path)
    hrefs = extract_citypop_href_map(cp_path)
    for r in cp.get("ts", {}).get("rows", []):
        cells = r["cells"]
        if len(cells) < 7:
            continue
        cname, aliases = clean_city_name(cells[0])
        pops = {}
        for ci, yr in cp["ts"]["year_cols"]:
            if ci < len(cells):
                v = to_int(cells[ci])
                if v is not None:
                    pops[str(yr)] = v
        if not pops:
            continue
        cant_code = ""
        for parts in hrefs.get(norm_text(cells[0]), []):
            if len(parts) >= 5 and re.match(r"^\d{4}", parts[-1]):
                cant_code = parts[-1][:4]
                break
        tk = by_norm.get((norm_text(cname), ""))
        if tk:
            settlements[tk].setdefault("urban_locality_population", {}).update(pops)
            for y, v in pops.items():
                settlements[tk]["population"].setdefault(y, v)
            settlements[tk]["sources"].append("INEC Ecuador Censuses 1982-2022 (via citypopulation.de)")
        else:
            coords = None
            csource = None
            if norm_text(cname) in hgis_coords:
                coords = list(hgis_coords[norm_text(cname)])
                csource = "HGIS_de_las_Indias"
            elif cant_code in by_code:
                coords = settlements[by_code[cant_code]]["coords"]
                csource = "geoBoundaries_ECU_ADM2_canton"
            key = f"{cname}-Ecuador" if f"{cname}-Ecuador" not in settlements else f"{cname} ({cells[1]})-Ecuador"
            settlements[key] = {
                "name": cname,
                "other_names": aliases,
                "coords": coords,
                "coord_source": csource,
                "country": "Ecuador",
                "admin1": cells[1],
                "admin_code": f"EC{cant_code}" if cant_code else "",
                "population_scope": "city_proper",
                "population": pops,
                "sources": ["INEC Ecuador Censuses 1982-2022 (via citypopulation.de)"],
            }

    # Historical 1950, 1962, 1974, 1982 major cantones
    hist_ecu = {
        "1701": {"1950": 209942, "1962": 354683, "1974": 599829, "1982": 817398},
        "0901": {"1950": 258966, "1962": 510804, "1974": 823219, "1982": 1199344},
        "0101": {"1950": 99193, "1962": 122434, "1974": 159776, "1982": 206962},
    }
    for dc, hp in hist_ecu.items():
        if dc in by_code:
            st = settlements[by_code[dc]]
            for y, v in hp.items():
                st["population"].setdefault(y, v)
            st["sources"].append("INEC Ecuador Historical Censuses (1950-1982)")

    unsd = load_unsd_country("Ecuador")
    for (_, scope), urec in unsd.items():
        if scope == "city_proper":
            tk = by_norm.get((norm_text(urec["name"]), ""))
            if tk:
                settlements[tk].setdefault("unsd_population", {}).update(urec["pop"])

    write_settlements_json(
        "raw_setts_ecuador.json",
        {
            "jurisdiction": "ecuador",
            "country": "Ecuador",
            "sources": [
                "INEC Ecuador Censo 2010 & 2022 / Revision 2024 (all 221 cantones incl. Galápagos via pobecu)",
                "INEC Ecuador Censuses 1982-2022 (via citypopulation.de)",
                "UNSD Demographic Yearbook Table 8",
                "INEC Ecuador Historical Censuses 1950-1982",
            ],
        },
        settlements,
    )


def build_peru():
    per_dir = os.path.join(RAW_DIR, "nso_peru")
    cens = json.load(open(os.path.join(per_dir, "peru_censos_2007_2025.json"), "r", encoding="utf-8"))
    coords_by_ubigeo = {}
    cap_by_ubigeo = {}
    prov_by_ubigeo = {}
    with open(os.path.join(per_dir, "peru_ubigeo_distrito.csv"), "r", encoding="utf-8-sig", errors="replace") as f:
        for r in csv.DictReader(f):
            ub = str(r.get("inei", "")).strip().zfill(6)
            lat = to_float(r.get("latitude"))
            lon = to_float(r.get("longitude"))
            if lat is not None and lon is not None:
                coords_by_ubigeo[ub] = [lat, lon]
            cap_by_ubigeo[ub] = (r.get("capital") or "").strip()
            prov_by_ubigeo[ub] = (r.get("provincia") or "").strip()

    D = cens["D"]
    years_idx = [(0, "2007"), (1, "2017"), (2, "2025")]
    lima_agg = {"2007": 0, "2017": 0, "2025": 0}
    callao_agg = {"2007": 0, "2017": 0, "2025": 0}
    lima_cnt, callao_cnt = 0, 0

    settlements = {}
    by_norm = {}

    for i, ub in enumerate(D["u"]):
        ub = str(ub).zfill(6)
        reg = D["r"][i]
        dname = D["n"][i]
        pob_arr = D["v"]["POB"][i]
        urb_arr = D["v"]["URB"][i]
        pops = {yr: to_int(pob_arr[idx]) for idx, yr in years_idx if pob_arr[idx] is not None}
        urbs = {yr: to_int(urb_arr[idx]) for idx, yr in years_idx if urb_arr[idx] is not None}
        if not pops:
            continue

        # Consolidate intra-municipal districts of Lima Province (1501*) & Callao (0701*)
        if ub.startswith("1501"):
            lima_cnt += 1
            for y, v in pops.items():
                lima_agg[y] += v
            continue
        if ub.startswith("0701"):
            callao_cnt += 1
            for y, v in pops.items():
                callao_agg[y] += v
            continue

        prov = prov_by_ubigeo.get(ub, "")
        coords = coords_by_ubigeo.get(ub)
        key = f"{dname}-Peru" if f"{dname}-Peru" not in settlements else f"{dname} ({prov or reg})-Peru"
        settlements[key] = {
            "name": dname,
            "other_names": [cap_by_ubigeo[ub]] if cap_by_ubigeo.get(ub) and cap_by_ubigeo[ub].lower() != dname.lower() else [],
            "coords": coords,
            "coord_source": "INEI_UBIGEO" if coords else None,
            "country": "Peru",
            "admin1": reg,
            "admin2": prov,
            "admin_code": ub,
            "population_scope": "city_proper",
            "population": pops,
            "urban_population": urbs,
            "sources": ["INEI Peru Censuses 2007, 2017 & 2025 (all districts)"],
        }
        by_norm[(norm_text(dname), norm_text(reg))] = key
        by_norm.setdefault((norm_text(dname), ""), key)

    # Add unified Lima (1501), Callao (0701), and Lima Metropolitana (metro)
    settlements["Lima-Peru"] = {
        "name": "Lima",
        "other_names": ["Lima Province", "Ciudad de los Reyes"],
        "coords": coords_by_ubigeo.get("150101", [-12.0464, -77.0428]),
        "coord_source": "INEI_UBIGEO",
        "country": "Peru",
        "admin1": "Lima",
        "admin_code": "150100",
        "consolidated_intra_districts": lima_cnt,
        "population_scope": "city_proper",
        "is_capital": True,
        "population": lima_agg,
        "sources": ["INEI Peru Censuses 2007, 2017 & 2025 (43 Lima Province districts consolidated)"],
    }
    settlements["Callao-Peru"] = {
        "name": "Callao",
        "other_names": ["Provincia Constitucional del Callao"],
        "coords": coords_by_ubigeo.get("070101", [-12.0566, -77.1181]),
        "coord_source": "INEI_UBIGEO",
        "country": "Peru",
        "admin1": "Callao",
        "admin_code": "070100",
        "consolidated_intra_districts": callao_cnt,
        "population_scope": "suburb",
        "population": callao_agg,
        "sources": ["INEI Peru Censuses 2007, 2017 & 2025 (7 Callao districts consolidated)"],
    }
    settlements["Lima Metropolitana (Metro)-Peru"] = {
        "name": "Lima Metropolitana (Metro)",
        "other_names": ["Lima-Callao"],
        "coords": [-12.0464, -77.0428],
        "coord_source": "INEI_UBIGEO",
        "country": "Peru",
        "admin1": "Lima / Callao",
        "population_scope": "metro",
        "is_capital": True,
        "population": {
            "1940": 645172,
            "1961": 1845910,
            "1972": 3302523,
            "1981": 4573227,
            "2007": lima_agg["2007"] + callao_agg["2007"],
            "2017": lima_agg["2017"] + callao_agg["2017"],
            "2022": 11166200,
            "2025": lima_agg["2025"] + callao_agg["2025"],
        },
        "sources": ["INEI Historical Censuses 1940-1981", "INEI Censuses 2007-2025", "INEI 2022 (via citypopulation.de)"],
    }

    # Merge citypopulation.de Peru urban centres (1993, 2007, 2017, 2022)
    cp = parse_citypop_html(os.path.join(RAW_DIR, "citypopulation_mirrors", "peru_cities.html"))
    for r in cp.get("ts", {}).get("rows", []):
        cells = r["cells"]
        if len(cells) < 7:
            continue
        cname, _ = clean_city_name(cells[0])
        if norm_text(cname) == "lima":
            continue
        pops = {}
        for ci, yr in cp["ts"]["year_cols"]:
            if ci < len(cells):
                v = to_int(cells[ci])
                if v is not None:
                    pops[str(yr)] = v
        tk = by_norm.get((norm_text(cname), ""))
        if tk:
            settlements[tk].setdefault("urban_locality_population", {}).update(pops)
            if "1993" in pops:
                settlements[tk]["population"].setdefault("1993", pops["1993"])
            if "2022" in pops:
                settlements[tk]["population"].setdefault("2022", pops["2022"])
            settlements[tk]["sources"].append("INEI Peru Censuses 1993-2022 (via citypopulation.de)")

    # Historical 1940, 1961, 1972, 1981 major Peruvian cities
    hist_per = {
        "Arequipa": {"1940": 80947, "1961": 158685, "1972": 309094, "1981": 446942},
        "Trujillo": {"1940": 36957, "1961": 103020, "1972": 240322, "1981": 354301},
        "Chiclayo": {"1940": 31539, "1961": 95667, "1972": 177321, "1981": 279527},
        "Chimbote": {"1940": 4243, "1961": 59990, "1972": 160430, "1981": 216579},
        "Piura": {"1940": 27919, "1961": 72096, "1972": 126010, "1981": 207934},
        "Cusco": {"1940": 40657, "1961": 79857, "1972": 120881, "1981": 184550},
        "Iquitos": {"1940": 31828, "1961": 57772, "1972": 110242, "1981": 178738},
        "Huancayo": {"1940": 26729, "1961": 64153, "1972": 126754, "1981": 164954},
    }
    for nm, hp in hist_per.items():
        tk = by_norm.get((norm_text(nm), ""))
        if tk:
            for y, v in hp.items():
                settlements[tk]["population"].setdefault(y, v)
            settlements[tk]["sources"].append("INEI Peru Historical Censuses (1940-1981)")

    write_settlements_json(
        "raw_setts_peru.json",
        {
            "jurisdiction": "peru",
            "country": "Peru",
            "sources": [
                "INEI Peru Censuses 2007, 2017 & 2025 (all 1,893 districts)",
                "INEI UBIGEO District Coordinates",
                "INEI Censuses 1993-2022 (via citypopulation.de)",
                "INEI Historical City Censuses 1940-1981",
            ],
            "lima_callao_non_decomposition": "43 Lima Province districts (1501) consolidated into Lima (city_proper); 7 Callao districts (0701) consolidated into Callao (suburb); combined Lima-Callao tagged Lima Metropolitana (metro).",
        },
        settlements,
    )


if __name__ == "__main__":
    build_colombia()
    build_venezuela()
    build_ecuador()
    build_peru()
