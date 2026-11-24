"""Builds Stage C Wave 1 raw settlement census files for Southern Cone:
  - raw_setts_chile.json
  - raw_setts_argentina.json
  - raw_setts_uruguay.json
"""

import csv
import json
import os
import re
import zipfile
import openpyxl
import pandas as pd
import shapefile
from shapely.geometry import shape

from quipu_wave1_utils import (
    GEO_DIR,
    RAW_DIR,
    SHARED_DIR,
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


def build_chile():
    chl_dir = os.path.join(RAW_DIR, "nso_chile")
    # 1. Load official comunas coordinates from chl_admin3.geojson (excl. Rapa Nui west of -95 deg)
    coords_by_cut = {}
    reg_by_cut = {}
    with zipfile.ZipFile(os.path.join(chl_dir, "chl_admin_boundaries.geojson.zip")) as z:
        adm3 = json.loads(z.read("chl_admin3.geojson").decode("utf-8"))
        for feat in adm3.get("features", []):
            pr = feat.get("properties", {})
            pcode = str(pr.get("adm3_pcode", "")).replace("CL", "").lstrip("0")
            lat = to_float(pr.get("center_lat"))
            lon = to_float(pr.get("center_lon"))
            if lat is None or lon is None:
                continue
            if lon < -95.0:  # Exclude Rapa Nui / Isla de Pascua (AUSTRAL)
                continue
            coords_by_cut[pcode] = [lat, lon]
            reg_by_cut[pcode] = pr.get("adm1_name", "")

    # 2. Load Zenodo 12807987 Población Comunal 1952-2024 (all 346 comunas, filter lon >= -95)
    df_zen = pd.read_excel(os.path.join(chl_dir, "zenodo_chl_poblacion_comunal_1952-2024.xlsx"))
    target_yrs = {1952, 1960, 1970, 1982, 1992, 2002, 2012, 2017, 2022, 2024}
    settlements = {}
    by_cut = {}
    by_norm = {}

    for _, r in df_zen.iterrows():
        yr = to_int(r.get("year"))
        if yr not in target_yrs:
            continue
        cut = str(to_int(r.get("Comuna")) or "")
        if not cut or cut in ("5201", "12202"):  # Exclude Isla de Pascua (Rapa Nui) & Antártica
            continue
        cname = str(r.get("Nombre Comuna", "")).strip()
        if any(x in cname.lower() for x in ("isla de pascua", "rapa nui", "antártica", "antartica")):
            continue
        pop = to_int(r.get("poblacion"))
        if pop is None:
            continue
        if cut not in by_cut:
            coords = coords_by_cut.get(cut)
            if coords and coords[1] < -95.0:
                continue
            key = f"{cname}-Chile" if f"{cname}-Chile" not in settlements else f"{cname} ({cut})-Chile"
            settlements[key] = {
                "name": cname,
                "other_names": [],
                "coords": coords,
                "coord_source": "INE_SUBDERE_CODAB_ADM3" if coords else None,
                "country": "Chile",
                "admin1": reg_by_cut.get(cut, str(r.get("Region", ""))),
                "admin_code": cut.zfill(5),
                "population_scope": "city_proper",
                "is_capital": cut == "13101",
                "population": {},
                "sources": ["INE Chile Censuses & Comunal Series 1952-2024 (Zenodo doi:10.5281/zenodo.12807987)"],
            }
            by_cut[cut] = key
            by_norm[norm_text(cname)] = key
        settlements[by_cut[cut]]["population"][str(yr)] = pop

    # 3. Merge Urbano/Rural 1992 from Consolidado_informacion_censos_historicos_.xlsx
    df_con = pd.read_excel(os.path.join(chl_dir, "zenodo_chl_Consolidado_informacion_censos_historicos_.xlsx"), sheet_name="Hoja1")
    for _, r in df_con.iterrows():
        cut = str(to_int(r.get("Comuna")) or "")
        if cut in by_cut:
            urb92 = to_int(r.get("Urbano 1992"))
            if urb92 is not None:
                settlements[by_cut[cut]]["urban_population_1992"] = urb92

    # 4. Merge INE proyecciones 2002-2035 (2002, 2010, 2017, 2024)
    with open(os.path.join(chl_dir, "chile_ine_proyecciones_comuna_2002_2035.csv"), "r", encoding="utf-8-sig", errors="replace") as f:
        for r in csv.DictReader(f, delimiter=";"):
            cut = str(to_int(r.get("cut_comuna")) or "")
            yr = to_int(r.get("año"))
            pop = to_int(r.get("población"))
            if cut in by_cut and yr in (2002, 2010, 2017, 2024) and pop is not None:
                settlements[by_cut[cut]]["population"].setdefault(str(yr), pop)

    # 5. Merge citypopulation Chile (urban localities + Gran Santiago/Valparaíso/Concepción metros)
    cp = parse_citypop_html(os.path.join(RAW_DIR, "citypopulation_mirrors", "chile_cities.html"))
    for r in cp.get("tlc", {}).get("rows", []):
        cells = r["cells"]
        if len(cells) >= 4:
            cname, _ = clean_city_name(cells[1])
            pop17 = to_int(cells[3])
            if pop17:
                mkey = f"Gran {cname} (Metro)-Chile"
                settlements[mkey] = {
                    "name": f"Gran {cname} (Metro)",
                    "other_names": [f"{cname} Agglomeration"],
                    "coords": settlements[by_norm[norm_text(cname)]]["coords"] if norm_text(cname) in by_norm else None,
                    "coord_source": "INE_SUBDERE_CODAB_ADM3",
                    "country": "Chile",
                    "admin1": cells[2],
                    "population_scope": "metro",
                    "is_capital": norm_text(cname) == "santiago",
                    "population": {"2017": pop17},
                    "sources": ["INE Chile Censo 2017 Agglomeration (via citypopulation.de)"],
                }
    for r in cp.get("ts", {}).get("rows", []):
        cells = r["cells"]
        if len(cells) >= 6:
            cname, _ = clean_city_name(cells[0])
            pops = {}
            for ci, yr in cp["ts"]["year_cols"]:
                if ci < len(cells):
                    v = to_int(cells[ci])
                    if v is not None:
                        pops[str(yr)] = v
            tk = by_norm.get(norm_text(cname))
            if tk:
                settlements[tk].setdefault("urban_locality_population", {}).update(pops)
                settlements[tk]["sources"].append("INE Chile Censuses 1992-2017 (via citypopulation.de)")

    # 6. Historical 1907, 1920, 1940 major cities (INE / BCN Chile)
    hist_chl = {
        "13101": {"1907": 332724, "1920": 549292, "1940": 952075},
        "5101": {"1907": 162447, "1920": 184430, "1940": 209945},
        "8101": {"1907": 55330},
        "2101": {"1907": 32496, "1940": 88597},
        "1101": {"1907": 40171, "1940": 50824},
        "7101": {"1907": 38040},
        "9101": {"1907": 16037},
        "14101": {"1907": 15229},
    }
    for cut, hp in hist_chl.items():
        if cut in by_cut:
            for y, v in hp.items():
                settlements[by_cut[cut]]["population"].setdefault(y, v)
            settlements[by_cut[cut]]["sources"].append("INE / BCN Chile Historical Censuses (1907-1940)")

    # 7. UNSD Demographic Yearbook
    unsd = load_unsd_country("Chile")
    for (_, scope), urec in unsd.items():
        if scope == "city_proper":
            tk = by_norm.get(norm_text(urec["name"]))
            if tk:
                settlements[tk].setdefault("unsd_population", {}).update(urec["pop"])

    write_settlements_json(
        "raw_setts_chile.json",
        {
            "jurisdiction": "chile",
            "country": "Chile",
            "sources": [
                "INE Chile Comunal Series 1952-2024 (Zenodo doi:10.5281/zenodo.12807987)",
                "INE Chile Comunal Projections 2002-2035",
                "INE / SUBDERE COD-AB Admin3 Centroids (excl. Rapa Nui west of -95 deg)",
                "INE Chile Censuses 1992-2017 (via citypopulation.de)",
                "UNSD Demographic Yearbook Table 8",
                "INE / BCN Historical Censuses 1907-1940",
            ],
            "rapa_nui_excluded": True,
        },
        settlements,
    )


def build_argentina():
    arg_dir = os.path.join(RAW_DIR, "nso_argentina")
    # 1. Load IGN/INDEC Georef Localidades + Localidades Censales + Departamentos for exact coords
    geo_loc = json.load(open(os.path.join(arg_dir, "georef_localidades.json"), "r", encoding="utf-8")).get("localidades", [])
    geo_lc = json.load(open(os.path.join(arg_dir, "georef_localidades_censales.json"), "r", encoding="utf-8")).get("localidades_censales", [])
    geo_dep = json.load(open(os.path.join(arg_dir, "georef_departamentos.json"), "r", encoding="utf-8")).get("departamentos", [])

    coords_by_prov_name = {}
    coords_by_name = {}
    for item in geo_lc + geo_loc:
        nm = norm_text(item.get("nombre", ""))
        prov = norm_text((item.get("provincia") or {}).get("nombre", ""))
        cen = item.get("centroide") or {}
        lat, lon = cen.get("lat"), cen.get("lon")
        if nm and lat is not None and lon is not None:
            coords_by_prov_name.setdefault((prov, nm), [round(lat, 6), round(lon, 6)])
            coords_by_name.setdefault(nm, [round(lat, 6), round(lon, 6)])
    for item in geo_dep:
        nm = norm_text(item.get("nombre", ""))
        prov = norm_text((item.get("provincia") or {}).get("nombre", ""))
        cen = item.get("centroide") or {}
        lat, lon = cen.get("lat"), cen.get("lon")
        if nm and lat is not None and lon is not None:
            coords_by_prov_name.setdefault((prov, nm), [round(lat, 6), round(lon, 6)])
            coords_by_name.setdefault(nm, [round(lat, 6), round(lon, 6)])

    # 2. Load INDEC Censo 2022 Gobiernos Locales (consolidating CABA's 15 Comunas!)
    wb = openpyxl.load_workbook(os.path.join(arg_dir, "c2022_tp_gobierno_local_c1.xlsx"), read_only=True, data_only=True)
    ws = wb["Total del país"]
    settlements = {}
    by_norm_prov = {}
    by_norm = {}
    caba_pop_2022 = 0
    caba_comunas = 0

    for idx, r in enumerate(ws.iter_rows(values_only=True)):
        if idx <= 4:
            continue
        cod_jur = str(r[0] or "").strip()
        prov = str(r[1] or "").strip()
        cod_gl = str(r[2] or "").strip()
        cat = str(r[3] or "").strip()
        gname = str(r[4] or "").strip()
        pop22 = to_int(r[6])
        if not gname or pop22 is None:
            continue
        if any(x in gname.lower() for x in ("sin gobierno local", "indeterminado", "gobierno local")):
            continue
        if cod_jur == "02" or "ciudad autónoma de buenos aires" in prov.lower():
            caba_pop_2022 += pop22
            caba_comunas += 1
            continue

        nk = norm_text(gname)
        np = norm_text(prov)
        coords = coords_by_prov_name.get((np, nk)) or coords_by_name.get(nk)
        if not coords:
            alt_nk = re.sub(r"^(?:estacion|villa|pueblo|colonia|puerto)\s+", "", nk).replace(" sud", " sur").strip()
            if alt_nk:
                coords = coords_by_prov_name.get((np, alt_nk)) or coords_by_name.get(alt_nk)
        key = f"{gname}-Argentina" if f"{gname}-Argentina" not in settlements else f"{gname} ({prov})-Argentina"
        settlements[key] = {
            "name": gname,
            "other_names": [],
            "coords": coords,
            "coord_source": "IGN_INDEC_Georef" if coords else None,
            "country": "Argentina",
            "admin1": prov,
            "admin_code": cod_gl,
            "gl_category": cat,
            "population_scope": "city_proper",
            "population": {"2022": pop22},
            "sources": ["INDEC Argentina Censo 2022 (Total del país por gobierno local)"],
        }
        by_norm_prov[(np, nk)] = key
        by_norm.setdefault(nk, key)
    wb.close()

    # Unified Buenos Aires (CABA) entity
    settlements["Buenos Aires-Argentina"] = {
        "name": "Buenos Aires",
        "other_names": ["Ciudad Autónoma de Buenos Aires", "CABA", "Capital Federal"],
        "coords": [-34.6037, -58.3816],
        "coord_source": "IGN_INDEC_Georef",
        "country": "Argentina",
        "admin1": "Ciudad Autónoma de Buenos Aires",
        "admin_code": "02000",
        "consolidated_intra_districts": caba_comunas,
        "population_scope": "city_proper",
        "is_capital": True,
        "population": {
            "1869": 177000, "1895": 663854, "1914": 1575814, "1947": 2981043,
            "1960": 3487948, "1970": 2972453, "1980": 2922829, "1991": 2965403,
            "2001": 2776138, "2010": 2890151, "2022": caba_pop_2022,
        },
        "sources": [
            "INDEC Argentina Censo 2022 (15 CABA Comunas consolidated)",
            "INDEC Historical Censuses 1869-2010",
        ],
    }
    by_norm[norm_text("Buenos Aires")] = "Buenos Aires-Argentina"

    # 3. Merge citypopulation Argentina (1991, 2001, 2010, 2022) + agglomerations (metro)
    cp_path = os.path.join(RAW_DIR, "citypopulation_mirrors", "argentina_cities.html")
    cp = parse_citypop_html(cp_path)
    for r in cp.get("tlc", {}).get("rows", []):
        cells = r["cells"]
        if len(cells) >= 4:
            cname, _ = clean_city_name(cells[1])
            pop22 = to_int(cells[3])
            if pop22:
                mname = f"Gran {cname} (Metro)"
                settlements[f"{mname}-Argentina"] = {
                    "name": mname,
                    "other_names": [f"{cname} Agglomeration"],
                    "coords": settlements[by_norm[norm_text(cname)]]["coords"] if norm_text(cname) in by_norm else None,
                    "coord_source": "IGN_INDEC_Georef",
                    "country": "Argentina",
                    "admin1": cells[2],
                    "population_scope": "metro",
                    "is_capital": norm_text(cname) == "buenos aires",
                    "population": {"2022": pop22},
                    "sources": ["INDEC Argentina Censo 2022 Agglomeration (via citypopulation.de)"],
                }
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
        nk = norm_text(cname)
        tk = by_norm.get(nk)
        if tk:
            for y, v in pops.items():
                settlements[tk]["population"].setdefault(y, v)
            settlements[tk]["sources"].append("INDEC Argentina Censuses 1991-2022 (via citypopulation.de)")
        else:
            coords = coords_by_name.get(nk)
            key = f"{cname}-Argentina"
            settlements[key] = {
                "name": cname,
                "other_names": aliases,
                "coords": coords,
                "coord_source": "IGN_INDEC_Georef" if coords else None,
                "country": "Argentina",
                "admin1": cells[2],
                "population_scope": "city_proper",
                "population": pops,
                "sources": ["INDEC Argentina Censuses 1991-2022 (via citypopulation.de)"],
            }
            by_norm[nk] = key

    # 4. Also register CONICET historical departmental cabeceras / georef localidades not yet in GL
    conicet_zip = os.path.join(SHARED_DIR, "subadmin_hgis", "raw_sources", "national_hgis", "conicet_arg_1869_2022", "Base_deptos_1869-2022.zip")
    conicet_depts = 0
    if os.path.exists(conicet_zip):
        with zipfile.ZipFile(conicet_zip) as z:
            sf = shapefile.Reader(
                shp=z.open("Base deptos 1869-2022/Departamentos_2022_INDEC.shp"),
                dbf=z.open("Base deptos 1869-2022/Departamentos_2022_INDEC.dbf"),
                encoding="utf-8", encodingErrors="replace",
            )
            for sr in sf.iterShapeRecords():
                rec = sr.record.as_dict()
                if str(rec.get("cpr", "")) == "02":  # CABA Comunas excluded
                    continue
                dnam = str(rec.get("nam", "")).strip()
                jur = str(rec.get("jur", "")).strip()
                if not dnam:
                    continue
                nk = norm_text(dnam)
                np = norm_text(jur)
                if (np, nk) not in by_norm_prov and nk not in by_norm:
                    pt = shape(sr.shape.__geo_interface__).representative_point()
                    if pt.x < -74.0 or pt.y < -56.0:  # Exclude Antarctica
                        continue
                    key = f"{dnam} (Depto)-Argentina"
                    settlements[key] = {
                        "name": dnam,
                        "other_names": [],
                        "coords": [round(pt.y, 6), round(pt.x, 6)],
                        "coord_source": "CONICET_1869_2022_INDEC",
                        "country": "Argentina",
                        "admin1": jur,
                        "admin_code": str(rec.get("cde", "")),
                        "population_scope": "city_proper",
                        "is_conicet_department_seat": True,
                        "population": {},
                        "sources": ["CONICET Base Cartográfica de Departamentos 1869-2022 (Handle: 11336/149867)"],
                    }
                    conicet_depts += 1

    # 5. Historical 1869-1970 major cities
    hist_arg = {
        "Rosario": {"1869": 23000, "1895": 91669, "1914": 245199, "1947": 475000, "1960": 669173, "1970": 806942},
        "Córdoba": {"1869": 34000, "1895": 47609, "1914": 121982, "1947": 380000, "1960": 591563, "1970": 792925},
        "La Plata": {"1895": 45410, "1914": 137413, "1947": 266000, "1960": 404129, "1970": 485939},
        "San Miguel de Tucumán": {"1869": 17000, "1895": 34305, "1914": 92284, "1947": 194000, "1960": 297305, "1970": 366392},
        "Mendoza": {"1869": 8000, "1895": 28302, "1914": 58790, "1947": 212000, "1960": 320727, "1970": 477810},
        "Mar del Plata": {"1914": 22500, "1947": 115000, "1960": 211365, "1970": 302282},
        "Santa Fe": {"1869": 10000, "1895": 22224, "1914": 64095, "1947": 173000, "1960": 208900, "1970": 246184},
        "Salta": {"1869": 11000, "1895": 7657, "1914": 28436, "1960": 117400, "1970": 176216},
    }
    for nm, hp in hist_arg.items():
        tk = by_norm.get(norm_text(nm))
        if tk:
            for y, v in hp.items():
                settlements[tk]["population"].setdefault(y, v)
            settlements[tk]["sources"].append("INDEC Argentina Historical Censuses 1869-1970")

    unsd = load_unsd_country("Argentina")
    for (_, scope), urec in unsd.items():
        if scope == "city_proper":
            tk = by_norm.get(norm_text(urec["name"]))
            if tk:
                settlements[tk].setdefault("unsd_population", {}).update(urec["pop"])

    write_settlements_json(
        "raw_setts_argentina.json",
        {
            "jurisdiction": "argentina",
            "country": "Argentina",
            "sources": [
                "INDEC Argentina Censo 2022 (All Gobiernos Locales)",
                "IGN / INDEC Georef Localidades & Localidades Censales (4,037/4,027 points)",
                "CONICET Base Cartográfica de Departamentos 1869-2022 (Handle: 11336/149867)",
                "INDEC Censuses 1991-2022 (via citypopulation.de)",
                "UNSD Demographic Yearbook Table 8",
                "INDEC Historical Censuses 1869-1970",
            ],
            "caba_non_decomposition": f"{caba_comunas} CABA Comunas consolidated into unified Buenos Aires (city_proper); Gran Buenos Aires tagged metro.",
            "conicet_supplemental_dept_seats": conicet_depts,
        },
        settlements,
    )


def build_uruguay():
    ury_dir = os.path.join(RAW_DIR, "nso_uruguay")
    # 1. Load coordinates from IDE Uruguay areas_urbanizadas.geojson (540 urban polygons) + URY_ADM2 + HGIS
    au_coords = {}
    au_gj = json.load(open(os.path.join(ury_dir, "ury_areas_urbanizadas.geojson"), "r", encoding="utf-8"))
    for feat in au_gj.get("features", []):
        pr = feat.get("properties", {})
        nm = re.sub(r"\s+Y\s+OTROS$", "", (pr.get("nam") or "").strip(), flags=re.I).strip()
        if nm and feat.get("geometry"):
            pt = shape(feat["geometry"]).representative_point()
            au_coords.setdefault(norm_text(nm), [round(pt.y, 6), round(pt.x, 6)])
    adm2_cent = load_geojson_centroids(os.path.join(GEO_DIR, "URY_ADM2.geojson"))
    hgis_coords = load_hgis_coords_by_iso("URY")

    settlements = {}
    by_norm_dept = {}
    by_norm = {}

    def ensure_ury(name, dept, code):
        nk = norm_text(name)
        nd = norm_text(dept)
        if (nd, nk) in by_norm_dept:
            return by_norm_dept[(nd, nk)]
        coords = au_coords.get(nk)
        csource = "IDE_Uruguay_Areas_Urbanizadas" if coords else None
        if not coords and nk in adm2_cent:
            c0 = adm2_cent[nk][0]
            coords = [c0[0], c0[1]]
            csource = "geoBoundaries_URY_ADM2"
        if not coords and nk in hgis_coords:
            coords = list(hgis_coords[nk])
            csource = "HGIS_de_las_Indias"
        clean_n = name.title() if name.isupper() else name
        clean_d = dept.title() if dept.isupper() else dept
        key = f"{clean_n}-Uruguay" if f"{clean_n}-Uruguay" not in settlements else f"{clean_n} ({clean_d})-Uruguay"
        settlements[key] = {
            "name": clean_n,
            "other_names": [],
            "coords": coords,
            "coord_source": csource,
            "country": "Uruguay",
            "admin1": clean_d,
            "admin_code": str(code or ""),
            "population_scope": "city_proper",
            "is_capital": nk == "montevideo",
            "population": {},
            "sources": [],
        }
        by_norm_dept[(nd, nk)] = key
        by_norm.setdefault(nk, key)
        return key

    # 2. Load 2023 Cuadro 11, 2011, 2004 INE Uruguay Localidades Censales
    wb23 = openpyxl.load_workbook(os.path.join(ury_dir, "ine_ury_2023_cuadro11.xlsx"), read_only=True, data_only=True)
    for idx, r in enumerate(wb23["Cuadro11_CAR"].iter_rows(values_only=True)):
        if idx < 5 or not r[0] or not r[2]:
            continue
        pop = to_int(r[3])
        if pop is not None:
            k = ensure_ury(str(r[2]).strip(), str(r[1]).strip(), str(r[0]).strip())
            settlements[k]["population"]["2023"] = pop
            if "INE Uruguay Censo 2023 (Cuadro 11 Localidades)" not in settlements[k]["sources"]:
                settlements[k]["sources"].append("INE Uruguay Censo 2023 (Cuadro 11 Localidades)")
    wb23.close()

    for fn, sh, yr in [
        ("ine_ury_2011_localidades.xlsx", "Localidades Censales 2011", "2011"),
        ("ine_ury_2004_localidades.xlsx", "Localidades Censales 2004", "2004"),
    ]:
        wb = openpyxl.load_workbook(os.path.join(ury_dir, fn), read_only=True, data_only=True)
        for idx, r in enumerate(wb[sh].iter_rows(values_only=True)):
            if idx == 0 or not r[0] or not r[1]:
                continue
            pop = to_int(r[3])
            if pop is not None:
                k = ensure_ury(str(r[1]).strip(), str(r[0]).strip(), str(r[2] or "").strip())
                settlements[k]["population"][yr] = pop
                src_lbl = f"INE Uruguay Censo {yr} (Localidades Censales)"
                if src_lbl not in settlements[k]["sources"]:
                    settlements[k]["sources"].append(src_lbl)
        wb.close()

    # 3. Merge citypopulation Uruguay (1975, 1985, 1996, 2004, 2011, 2023)
    cp = parse_citypop_html(os.path.join(RAW_DIR, "citypopulation_mirrors", "uruguay_cities.html"))
    for r in cp.get("ts", {}).get("rows", []):
        cells = r["cells"]
        if len(cells) < 8:
            continue
        cname, aliases = clean_city_name(cells[0])
        nk = norm_text(cname)
        tk = by_norm.get(nk)
        if not tk:
            tk = ensure_ury(cname, cells[1], "")
        for a in aliases:
            if a not in settlements[tk]["other_names"]:
                settlements[tk]["other_names"].append(a)
        for ci, yr in cp["ts"]["year_cols"]:
            if ci < len(cells):
                v = to_int(cells[ci])
                if v is not None:
                    settlements[tk]["population"].setdefault(str(yr), v)
        settlements[tk]["sources"].append("INE Uruguay Censuses 1975-2023 (via citypopulation.de)")

    # 4. Historical 1908 & 1963 major Uruguayan cities
    hist_ury = {
        "Montevideo": {"1908": 291465, "1963": 1202890},
        "Salto": {"1908": 19700, "1963": 57975},
        "Paysandú": {"1908": 20953, "1963": 51645},
        "Rivera": {"1963": 40096},
        "Melo": {"1908": 12355, "1963": 33741},
        "Mercedes": {"1908": 15667, "1963": 31325},
        "Las Piedras": {"1908": 8109, "1963": 40658},
    }
    for nm, hp in hist_ury.items():
        tk = by_norm.get(norm_text(nm))
        if tk:
            for y, v in hp.items():
                settlements[tk]["population"].setdefault(y, v)
            settlements[tk]["sources"].append("INE Uruguay Historical Censuses (1908, 1963)")

    unsd = load_unsd_country("Uruguay")
    for (_, scope), urec in unsd.items():
        if scope == "city_proper":
            tk = by_norm.get(norm_text(urec["name"]))
            if tk:
                settlements[tk].setdefault("unsd_population", {}).update(urec["pop"])

    write_settlements_json(
        "raw_setts_uruguay.json",
        {
            "jurisdiction": "uruguay",
            "country": "Uruguay",
            "sources": [
                "INE Uruguay Censuses 2004, 2011 & 2023 (All Localidades Censales)",
                "IDE Uruguay Áreas Urbanizadas (540 urban polygons)",
                "INE Uruguay Censuses 1975-2023 (via citypopulation.de)",
                "UNSD Demographic Yearbook Table 8",
                "INE Uruguay Historical Censuses 1908 & 1963",
            ],
        },
        settlements,
    )


if __name__ == "__main__":
    build_chile()
    build_argentina()
    build_uruguay()
