"""Extracts HGIS de las Indias (1701-1808) colonial demographic observations and
gazetteer settlements strictly filtered to QUIPU South America.

Sources:
  - demografia_lugares.gpkg (6,973 rows)
  - da_dem_lugares.csv (7,211 rows)
  - gazetteer-2023-10-26.zip (GZ.shp, 16,148 points)
  - fuentes.tab (1,319 archival/monograph citations)
  - cabeceras.tab (colonial administrative seats)
"""

import csv
import json
import os
import re
import sqlite3
import struct
import zipfile
import shapefile
from shapely.geometry import Point, shape

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HGIS_DIR = os.path.join(BASE_DIR, "subadmin_hgis", "raw_sources", "hgis_indias")
GEO_DIR = os.path.join(BASE_DIR, "subadmin_hgis", "raw_sources", "geoboundaries")
OUT_PATH = os.path.join(BASE_DIR, "settlement_sources", "hgis_indias_colonial_raw.json")

QUIPU_PAISES = {"COL", "VEN", "ECU", "PER", "BOL", "CHL", "ARG", "URY", "FLK"}
ANDEAN_BOL_DEPTS = {"La Paz", "Oruro", "Potosí", "Potosi", "Cochabamba", "Chuquisaca", "Tarija"}
LON_MIN, LON_MAX = -95.0, -52.0
LAT_MIN, LAT_MAX = -57.0, 13.0


def parse_gpkg_point(blob):
    """Parse GeoPackage StandardGeoPackageBinary Point."""
    if not blob or len(blob) < 29 or blob[0:2] != b"GP":
        return None, None
    flags = blob[3]
    env_ind = (flags >> 1) & 0x07
    env_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    offset = 8 + env_sizes.get(env_ind, 0)
    if offset + 21 > len(blob):
        return None, None
    endian = "<" if blob[offset] == 1 else ">"
    wkb_type = struct.unpack(endian + "I", blob[offset + 1 : offset + 5])[0]
    if (wkb_type & 0xFF) == 1:
        x, y = struct.unpack(endian + "dd", blob[offset + 5 : offset + 21])
        return round(y, 6), round(x, 6)
    return None, None


def to_num(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() == "none":
        return None
    s = s.replace(",", ".")
    try:
        f = float(s)
        if f.is_integer():
            return int(f)
        return round(f, 3)
    except ValueError:
        return None


def parse_year(fecha_str, start_str, end_str):
    """Extract numeric year or midpoint from HGIS Fecha_Dato / START_ / END_."""
    for cand in (fecha_str, start_str):
        if cand is not None:
            m = re.findall(r"\b(1[5-9]\d{2})\b", str(cand))
            if len(m) == 1:
                return int(m[0])
            if len(m) >= 2:
                return round((int(m[0]) + int(m[-1])) / 2)
    return None


def load_bol_adm1():
    fp = os.path.join(GEO_DIR, "BOL_ADM1.geojson")
    if not os.path.exists(fp):
        return []
    gj = json.load(open(fp, "r", encoding="utf-8"))
    out = []
    for feat in gj.get("features", []):
        name = feat.get("properties", {}).get("shapeName", "")
        out.append((name, shape(feat["geometry"])))
    return out


def load_fuentes():
    fp = os.path.join(HGIS_DIR, "fuentes.tab")
    fuentes = {}
    with open(fp, "r", encoding="utf-8", errors="replace") as f:
        rd = csv.DictReader(f, delimiter="\t")
        for r in rd:
            fid = (r.get("FuenteID") or "").strip().strip('"')
            cita = (r.get("Cita completa") or "").strip().strip('"')
            url = (r.get("URL") or "").strip().strip('"')
            if fid:
                fuentes[fid] = {
                    "citation": cita,
                    "tipo": (r.get("tipo") or "").strip().strip('"'),
                    "url": "" if url == "None" else url,
                }
    return fuentes


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fuentes = load_fuentes()
    bol_polys = load_bol_adm1()

    def check_bol_andean(lat, lon):
        pt = Point(lon, lat)
        for dname, poly in bol_polys:
            if poly.contains(pt):
                return dname, (dname in ANDEAN_BOL_DEPTS)
        return None, None

    # 1. Load GZ.shp (16,148 gazetteer points)
    gz_by_id = {}
    gz_by_name_reg = {}
    with zipfile.ZipFile(os.path.join(HGIS_DIR, "gazetteer-2023-10-26.zip")) as z:
        sf = shapefile.Reader(shp=z.open("GZ.shp"), dbf=z.open("GZ.dbf"), encoding="utf-8", encodingErrors="replace")
        for sr in sf.iterShapeRecords():
            rec = sr.record.as_dict()
            gz_id = int(rec.get("gz_id") or 0)
            lat = to_num(rec.get("lat"))
            lon = to_num(rec.get("lon"))
            if (lat is None or lon is None) and sr.shape.points:
                lon, lat = round(sr.shape.points[0][0], 6), round(sr.shape.points[0][1], 6)
            rec["_lat"] = lat
            rec["_lon"] = lon
            gz_by_id[gz_id] = rec
            nm = (rec.get("nombre") or "").strip().lower()
            rg = (rec.get("region") or "").strip()
            if nm and rg:
                gz_by_name_reg.setdefault((nm, rg), []).append(rec)

    # 2. Load demografia_lugares.gpkg
    con = sqlite3.connect(os.path.join(HGIS_DIR, "demografia_lugares.gpkg"))
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    seen_it_ids = set()
    settlements = {}
    obs_count = 0

    def ensure_settlement(gz_id, name, lat, lon, pais, reg, prov, part, region_lbl, cat, nombrehoy, variantes, start_yr, end_yr, gz_fuente):
        skey = f"gz_{gz_id}" if gz_id and gz_id > 0 else f"unmatched_{reg}_{re.sub(r'[^a-z0-9]+', '_', name.lower())}_{round(lat,3)}_{round(lon,3)}"
        if skey not in settlements:
            bol_dept, is_andean_bol = (None, None)
            if pais == "BOL" and lat is not None and lon is not None:
                bol_dept, is_andean_bol = check_bol_andean(lat, lon)
            f_info = fuentes.get(gz_fuente or "", {})
            settlements[skey] = {
                "gz_id": gz_id if gz_id else None,
                "name": name,
                "modern_name": nombrehoy if nombrehoy and nombrehoy != "None" else name,
                "variants": [v.strip() for v in str(variantes or "").split(";") if v.strip() and v.strip() != "None"],
                "country_iso3": pais,
                "colonial_audiencia": reg,
                "colonial_region": region_lbl or "",
                "colonial_province": prov or "",
                "colonial_partido": part or "",
                "categoria": cat or "",
                "coords": [round(float(lat), 6), round(float(lon), 6)],
                "start_year": to_num(start_yr),
                "end_year": to_num(end_yr),
                "bol_department": bol_dept,
                "is_andean_bolivia": is_andean_bol,
                "observations": [],
                "sources": [f_info["citation"]] if f_info.get("citation") else [],
            }
        return settlements[skey]

    for r in cur.execute("SELECT * FROM demografia_lugares"):
        it_id = int(r["it_ID"])
        seen_it_ids.add(it_id)
        pais = (r["GZ_pais"] or "").strip()
        lat = to_num(r["GZ_lat"])
        lon = to_num(r["GZ_lon"])
        if lat is None or lon is None:
            lat, lon = parse_gpkg_point(r["geom"])
        if pais not in QUIPU_PAISES:
            continue
        if lat is None or lon is None or not (LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX):
            continue

        gz_id = int(r["it_GZ_ID"] or r["GZ_gz_id"] or 0)
        name = (r["GZ_nombre"] or r["it_Label"] or "").strip()
        reg = (r["it_REG"] or r["GZ_region"] or "").strip()
        st_entry = ensure_settlement(
            gz_id, name, lat, lon, pais, reg,
            r["GZ_provincia_generica"], r["GZ_partido_generico"], r["GZ_region"],
            r["GZ_categoria"], r["GZ_nombrehoy"], r["GZ_variantes"],
            r["GZ_start"], r["GZ_end_"], r["GZ_fuente_ID"],
        )

        f_id = (r["it_Fuente"] or "").strip()
        f_cit = fuentes.get(f_id, {}).get("citation", f"HGIS de las Indias fuente:{f_id}" if f_id else "HGIS de las Indias")
        if f_cit and f_cit not in st_entry["sources"]:
            st_entry["sources"].append(f_cit)

        yr = parse_year(r["it_Fecha_Dato"], r["it_START_"], r["it_END_"])
        obs = {
            "it_id": it_id,
            "year": yr,
            "fecha_dato": str(r["it_Fecha_Dato"] or ""),
            "start_year": to_num(r["it_START_"]),
            "end_year": to_num(r["it_END_"]),
            "alcance_tipo": (r["it_Alcance_tipo"] or "").strip(),
            "dato_tipo": (r["it_Dato_tipo"] or "").strip(),
            "total": to_num(r["it_Total"]),
            "total_doc": to_num(r["it_Total_doc"]),
            "vecinos_doc": to_num(r["it_Vecinos_doc"]),
            "tributarios_doc": to_num(r["it_Tributarios_doc"]),
            "familias_doc": to_num(r["it_Familias_doc"]),
            "casas_doc": to_num(r["it_Casas_doc"]),
            "blancos": to_num(r["it_Blancos"]),
            "indios": to_num(r["it_Indios"]),
            "mestizos": to_num(r["it_Mestizos"]),
            "castas": to_num(r["it_Castas"]),
            "esclavos": to_num(r["it_Esclavos"]),
            "fuente_id": f_id,
            "source_citation": f_cit,
        }
        st_entry["observations"].append(obs)
        obs_count += 1
    con.close()

    # 3. Supplement from da_dem_lugares.csv rows missing from GPKG (joined to GZ.shp)
    csv_added = 0
    with open(os.path.join(HGIS_DIR, "da_dem_lugares.csv"), "r", encoding="utf-8-sig", errors="replace") as f:
        rd = csv.DictReader(f, delimiter=";")
        for r in rd:
            it_id = int(r["ID"])
            if it_id in seen_it_ids:
                continue
            gz_id = int(to_num(r.get("GZ_ID")) or 0)
            gz_rec = gz_by_id.get(gz_id)
            if not gz_rec:
                cands = gz_by_name_reg.get(((r.get("Label") or "").strip().lower(), (r.get("REG") or "").strip()), [])
                if len(cands) == 1:
                    gz_rec = cands[0]
                    gz_id = int(gz_rec.get("gz_id") or 0)
            if not gz_rec:
                continue
            pais = (gz_rec.get("pais") or "").strip()
            lat, lon = gz_rec.get("_lat"), gz_rec.get("_lon")
            if pais not in QUIPU_PAISES or lat is None or lon is None:
                continue
            if not (LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX):
                continue

            st_entry = ensure_settlement(
                gz_id, (gz_rec.get("nombre") or r.get("Label") or "").strip(), lat, lon, pais,
                (r.get("REG") or gz_rec.get("region") or "").strip(),
                gz_rec.get("provincia_"), gz_rec.get("partido_ge"), gz_rec.get("region"),
                gz_rec.get("categoria"), gz_rec.get("nombrehoy"), gz_rec.get("variantes"),
                gz_rec.get("start"), gz_rec.get("end_"), gz_rec.get("fuente_ID"),
            )
            f_id = (r.get("Fuente") or "").strip()
            f_cit = fuentes.get(f_id, {}).get("citation", f"HGIS de las Indias fuente:{f_id}" if f_id else "HGIS de las Indias")
            if f_cit and f_cit not in st_entry["sources"]:
                st_entry["sources"].append(f_cit)
            yr = parse_year(r.get("Fecha_Dato"), r.get("START_"), r.get("END_"))
            obs = {
                "it_id": it_id,
                "year": yr,
                "fecha_dato": str(r.get("Fecha_Dato") or ""),
                "start_year": to_num(r.get("START_")),
                "end_year": to_num(r.get("END_")),
                "alcance_tipo": (r.get("Alcance-tipo") or "").strip(),
                "dato_tipo": (r.get("Dato-tipo") or "").strip(),
                "total": to_num(r.get("Total")),
                "total_doc": to_num(r.get("Total-doc")),
                "vecinos_doc": to_num(r.get("Vecinos-doc")),
                "tributarios_doc": to_num(r.get("Tributarios-doc")),
                "familias_doc": to_num(r.get("Familias-doc")),
                "casas_doc": to_num(r.get("Casas-doc")),
                "blancos": to_num(r.get("Blancos")),
                "indios": to_num(r.get("Indios")),
                "mestizos": to_num(r.get("Mestizos")),
                "castas": to_num(r.get("Castas")),
                "esclavos": to_num(r.get("Esclavos")),
                "fuente_id": f_id,
                "source_citation": f_cit,
            }
            st_entry["observations"].append(obs)
            csv_added += 1
            obs_count += 1

    # 4. Include all remaining QUIPU South America colonial places from GZ.shp
    gz_only_added = 0
    for gz_id, rec in gz_by_id.items():
        pais = (rec.get("pais") or "").strip()
        cat = (rec.get("categoria") or "").strip()
        if pais not in QUIPU_PAISES or cat in ("Doublette", "Dubleta"):
            continue
        lat, lon = rec.get("_lat"), rec.get("_lon")
        if lat is None or lon is None or not (LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX):
            continue
        skey = f"gz_{gz_id}"
        if skey not in settlements:
            ensure_settlement(
                gz_id, (rec.get("nombre") or rec.get("label") or "").strip(), lat, lon, pais,
                (rec.get("region") or "").strip(),
                rec.get("provincia_"), rec.get("partido_ge"), rec.get("region"),
                cat, rec.get("nombrehoy"), rec.get("variantes"),
                rec.get("start"), rec.get("end_"), rec.get("fuente_ID"),
            )
            gz_only_added += 1

    # Sort observations chronologically and compute summary
    by_country = {}
    with_demo = 0
    for st in settlements.values():
        st["observations"].sort(key=lambda o: (o["year"] or 9999, o["it_id"]))
        st["has_demographic_observations"] = len(st["observations"]) > 0
        if st["has_demographic_observations"]:
            with_demo += 1
        c = st["country_iso3"]
        by_country.setdefault(c, {"settlements": 0, "with_demographic_obs": 0, "observations": 0})
        by_country[c]["settlements"] += 1
        if st["has_demographic_observations"]:
            by_country[c]["with_demographic_obs"] += 1
        by_country[c]["observations"] += len(st["observations"])

    payload = {
        "metadata": {
            "source": "Stangl, Werner (2020/2023). HGIS de las Indias. University of Graz / Harvard Dataverse (doi:10.7910/DVN/FUSJDW; doi:10.7910/DVN/29XTPY).",
            "filter": {
                "lon_range": [LON_MIN, LON_MAX],
                "lat_range": [LAT_MIN, LAT_MAX],
                "included_countries": sorted(QUIPU_PAISES),
                "excluded_countries": ["BRA", "PRY", "GUY", "SUR", "GUF", "PAN", "TTO"],
            },
            "total_unique_settlements": len(settlements),
            "settlements_with_demographic_observations": with_demo,
            "gazetteer_only_settlements": gz_only_added,
            "total_demographic_observations": obs_count,
            "csv_supplemental_observations_joined": csv_added,
            "by_country": by_country,
        },
        "settlements": settlements,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[HGIS INDIAS] Saved {len(settlements)} unique settlements ({with_demo} w/ demo obs, {obs_count} total obs) -> {OUT_PATH}")
    print("  By country:", json.dumps(by_country, indent=2))


if __name__ == "__main__":
    main()
