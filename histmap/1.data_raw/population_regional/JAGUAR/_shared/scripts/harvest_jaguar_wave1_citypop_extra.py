import os
import re
import csv
import json
import time
import requests
from html.parser import HTMLParser

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\settlement_sources\raw\official_census_tables"
os.makedirs(RAW_DIR, exist_ok=True)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

EXTRA_TARGETS = [
    # Fixed URLs for the 10 zero-row countries/territories
    ("central_america", "belize_cities", "https://www.citypopulation.de/en/belize/cities/", "SIB Belize Censuses (Cities & Towns)"),
    ("central_america", "belize_admin", "https://www.citypopulation.de/en/belize/admin/", "SIB Belize Censuses (Districts & Towns)"),
    ("caribbean", "puerto_rico_cities", "https://www.citypopulation.de/en/puertorico/cities/", "US Census Bureau Puerto Rico Censuses (Cities & Urban Places)"),
    ("caribbean", "puerto_rico_admin", "https://www.citypopulation.de/en/puertorico/admin/", "US Census Bureau Puerto Rico Censuses (Municipios)"),
    ("caribbean", "bahamas_cities", "https://www.citypopulation.de/en/bahamas/cities/", "Bahamas Dept of Statistics Censuses (Settlements)"),
    ("caribbean", "bahamas_admin", "https://www.citypopulation.de/en/bahamas/admin/", "Bahamas Dept of Statistics Censuses (Islands & Districts)"),
    ("caribbean", "guadeloupe_communes", "https://www.citypopulation.de/en/france/cities/guadeloupe/", "INSEE Guadeloupe Censuses (Communes 1967-2022)"),
    ("caribbean", "martinique_communes", "https://www.citypopulation.de/en/france/cities/martinique/", "INSEE Martinique Censuses (Communes 1967-2022)"),
    ("caribbean", "curacao_cities", "https://www.citypopulation.de/en/curacao/cities/", "CBS Curacao Censuses (Towns & Zones)"),
    ("caribbean", "curacao_admin", "https://www.citypopulation.de/en/curacao/admin/", "CBS Curacao Censuses (Geozones)"),
    ("caribbean", "aruba_cities", "https://www.citypopulation.de/en/aruba/cities/", "CBS Aruba Censuses (Regions & Towns)"),
    ("caribbean", "aruba_admin", "https://www.citypopulation.de/en/aruba/admin/", "CBS Aruba Censuses (Regions)"),
    ("caribbean", "antigua_barbuda_main", "https://www.citypopulation.de/en/antigua/", "Statistics Division Antigua and Barbuda Censuses"),
    ("caribbean", "st_lucia_cities", "https://www.citypopulation.de/en/stlucia/cities/", "CSO Saint Lucia Censuses (Cities & Towns)"),
    ("caribbean", "st_lucia_admin", "https://www.citypopulation.de/en/stlucia/admin/", "CSO Saint Lucia Censuses (Districts)"),
    ("caribbean", "cayman_islands_main", "https://www.citypopulation.de/en/caymans/", "ESO Cayman Islands Censuses"),
    # Deeper multi-census full municipal rosters for Central America & Greater Antilles
    ("central_america", "guatemala_admin", "https://www.citypopulation.de/en/guatemala/mun/admin/", "INE Guatemala Censuses (All Municipalities)"),
    ("central_america", "el_salvador_admin", "https://www.citypopulation.de/en/elsalvador/mun/admin/", "DIGESTYC / BCR El Salvador Censuses (All Municipalities)"),
    ("central_america", "honduras_admin", "https://www.citypopulation.de/en/honduras/mun/admin/", "INE Honduras Censuses (All Municipalities)"),
    ("central_america", "nicaragua_admin", "https://www.citypopulation.de/en/nicaragua/mun/admin/", "INIDE Nicaragua Censuses (All Municipalities)"),
    ("central_america", "costa_rica_admin", "https://www.citypopulation.de/en/costarica/admin/", "INEC Costa Rica Censuses (All Cantons)"),
    ("central_america", "panama_admin", "https://www.citypopulation.de/en/panama/admin/", "INEC Panama Censuses (All Districts)"),
    ("caribbean", "cuba_admin", "https://www.citypopulation.de/en/cuba/admin/", "ONEI Cuba Censuses (All Municipalities)"),
    ("caribbean", "haiti_admin", "https://www.citypopulation.de/en/haiti/admin/", "IHSI Haiti Censuses (All Communes)"),
    ("caribbean", "dominican_republic_admin", "https://www.citypopulation.de/en/domrep/mun/admin/", "ONE Dominican Republic Censuses (All Municipalities)"),
    ("caribbean", "jamaica_admin", "https://www.citypopulation.de/en/jamaica/admin/", "STATIN Jamaica Censuses (All Parishes)"),
    ("caribbean", "trinidad_tobago_admin", "https://www.citypopulation.de/en/trinidad/admin/", "CSO Trinidad and Tobago Censuses (Regions & Boroughs)"),
    ("caribbean", "barbados_admin", "https://www.citypopulation.de/en/barbados/admin/", "BSS Barbados Censuses (Parishes)"),
    # Mexico official CONAPO/INEGI metro & state-level urban summary
    ("mexico", "mexico_admin", "https://www.citypopulation.de/en/mexico/admin/", "INEGI Mexico Censuses (States 1990-2020)"),
]

class SimpleTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.cur_table = None
        self.cur_row = None
        self.cur_cell = None
        self.in_source = False
        self.source_parts = []

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        if tag == "table":
            self.cur_table = {"id": ad.get("id", ""), "rows": []}
        elif tag == "tr" and self.cur_table is not None:
            self.cur_row = {
                "cells": [], "is_header": False,
                "lat": ad.get("data-lat", ""), "lon": ad.get("data-lon", ""),
            }
        elif tag in ("td", "th") and self.cur_row is not None:
            self.cur_cell = {"tag": tag, "text": []}
            if tag == "th":
                self.cur_row["is_header"] = True
            if ad.get("data-lat") and not self.cur_row["lat"]:
                self.cur_row["lat"] = ad.get("data-lat", "")
                self.cur_row["lon"] = ad.get("data-lon", "")
        elif tag in ("p", "section") and ("source" in ad.get("class", "") or ad.get("id") == "source"):
            self.in_source = True
        elif self.cur_row is not None and ad.get("data-lat") and not self.cur_row["lat"]:
            self.cur_row["lat"] = ad.get("data-lat", "")
            self.cur_row["lon"] = ad.get("data-lon", "")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cur_cell is not None and self.cur_row is not None:
            txt = re.sub(r"\s+", " ", "".join(self.cur_cell["text"])).strip()
            self.cur_row["cells"].append(txt)
            self.cur_cell = None
        elif tag == "tr" and self.cur_row is not None and self.cur_table is not None:
            if self.cur_row["cells"]:
                self.cur_table["rows"].append(self.cur_row)
            self.cur_row = None
        elif tag == "table" and self.cur_table is not None:
            self.tables.append(self.cur_table)
            self.cur_table = None
        elif tag in ("p", "section") and self.in_source:
            self.in_source = False

    def handle_data(self, data):
        if self.cur_cell is not None:
            self.cur_cell["text"].append(data)
        if self.in_source:
            self.source_parts.append(data)

def parse_tables(html_text, country_slug, jur, nso_label):
    p = SimpleTableParser()
    p.feed(html_text)
    src_note = re.sub(r"\s+", " ", " ".join(p.source_parts)).strip()
    extracted = []
    for tidx, tbl in enumerate(p.tables):
        t_id = tbl["id"] or f"table_{tidx}"
        rows = tbl["rows"]
        if len(rows) < 2:
            continue
        headers = rows[0]["cells"]
        if len(headers) < 2:
            continue
        for r in rows[1:]:
            vals = r["cells"]
            if len(vals) < 2 or vals == headers:
                continue
            row_dict = {
                "jurisdiction": jur, "country_slug": country_slug,
                "table_id": t_id, "nso_source": nso_label,
                "lat": r["lat"], "lon": r["lon"],
            }
            for i, v in enumerate(vals):
                hname = headers[i] if i < len(headers) and headers[i] else f"col_{i}"
                row_dict[hname] = v
            extracted.append(row_dict)
    return extracted, src_note

# Clean old 0-row bogus html files first
old_zeros = [
    "central_america_belize", "caribbean_puerto_rico", "caribbean_bahamas",
    "caribbean_guadeloupe", "caribbean_martinique", "caribbean_curacao",
    "caribbean_aruba", "caribbean_antigua_barbuda", "caribbean_st_lucia",
    "caribbean_cayman_islands", "mexico_mexico_agglomerations"
]
for z in old_zeros:
    fp = os.path.join(RAW_DIR, z + "_census.html")
    if os.path.exists(fp):
        os.remove(fp)

log = []
for jur, slug, url, nso in EXTRA_TARGETS:
    html_path = os.path.join(RAW_DIR, f"{jur}_{slug}_census.html")
    csv_path = os.path.join(RAW_DIR, f"{jur}_{slug}_census.csv")
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        if r.status_code != 200:
            print(f"FAIL {r.status_code}: {slug} ({url})")
            log.append({"jurisdiction": jur, "slug": slug, "url": url, "status": f"http_{r.status_code}", "rows": 0})
            continue
        html = r.text
        rows, src_note = parse_tables(html, slug, jur, nso)
        if rows:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            all_keys = []
            for row in rows:
                for k in row.keys():
                    if k not in all_keys:
                        all_keys.append(k)
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=all_keys)
                w.writeheader()
                w.writerows(rows)
            print(f"OK [{jur}/{slug}]: {len(rows)} rows")
            log.append({
                "jurisdiction": jur, "slug": slug, "nso_source": nso, "url": url,
                "status": "ok", "html_file": os.path.basename(html_path),
                "csv_file": os.path.basename(csv_path), "rows": len(rows),
                "columns": all_keys, "source_citation": src_note[:400],
            })
        else:
            print(f"ZERO [{jur}/{slug}] ({url})")
            log.append({"jurisdiction": jur, "slug": slug, "url": url, "status": "zero_rows", "rows": 0})
        time.sleep(0.3)
    except Exception as e:
        print(f"ERR [{slug}]: {e}")
        log.append({"jurisdiction": jur, "slug": slug, "url": url, "status": f"err:{e}", "rows": 0})

with open(os.path.join(RAW_DIR, "_official_census_tables_extra_log.json"), "w", encoding="utf-8") as f:
    json.dump(log, f, indent=2, ensure_ascii=False)
print("DONE extra census tables:", sum(x["rows"] for x in log), "rows across", len([x for x in log if x["status"] == "ok"]), "pages.")
