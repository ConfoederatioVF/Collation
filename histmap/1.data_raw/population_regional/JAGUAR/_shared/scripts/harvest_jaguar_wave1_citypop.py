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

# Comprehensive official national census city/town/parish compilation pages on citypopulation.de
# Every page directly reproduces official national statistical institute census tables with exact census dates & citations.
TARGETS = [
    # --- CENTRAL AMERICA ---
    ("central_america", "guatemala", "https://www.citypopulation.de/en/guatemala/cities/", "INE Guatemala Censuses"),
    ("central_america", "belize", "https://www.citypopulation.de/en/belize/", "SIB Belize Censuses"),
    ("central_america", "el_salvador", "https://www.citypopulation.de/en/elsalvador/cities/", "DIGESTYC / BCR El Salvador Censuses"),
    ("central_america", "honduras", "https://www.citypopulation.de/en/honduras/cities/", "INE Honduras Censuses"),
    ("central_america", "nicaragua", "https://www.citypopulation.de/en/nicaragua/cities/", "INIDE Nicaragua Censuses"),
    ("central_america", "costa_rica", "https://www.citypopulation.de/en/costarica/cities/", "INEC Costa Rica Censuses"),
    ("central_america", "panama", "https://www.citypopulation.de/en/panama/cities/", "INEC Panama Censuses"),
    # --- CARIBBEAN: GREATER ANTILLES ---
    ("caribbean", "cuba", "https://www.citypopulation.de/en/cuba/cities/", "ONEI Cuba Censuses"),
    ("caribbean", "haiti", "https://www.citypopulation.de/en/haiti/", "IHSI Haiti Censuses"),
    ("caribbean", "dominican_republic", "https://www.citypopulation.de/en/domrep/cities/", "ONE Dominican Republic Censuses"),
    ("caribbean", "jamaica", "https://www.citypopulation.de/en/jamaica/cities/", "STATIN Jamaica Censuses"),
    ("caribbean", "puerto_rico", "https://www.citypopulation.de/en/usa/puertorico/", "US Census Bureau Puerto Rico Censuses"),
    # --- CARIBBEAN: LESSER ANTILLES, BAHAMAS, TRINIDAD & TOBAGO, BERMUDA ---
    ("caribbean", "barbados", "https://www.citypopulation.de/en/barbados/", "Barbados Statistical Service Censuses"),
    ("caribbean", "trinidad_tobago", "https://www.citypopulation.de/en/trinidad/cities/", "CSO Trinidad and Tobago Censuses"),
    ("caribbean", "bahamas", "https://www.citypopulation.de/en/bahamas/", "Bahamas Dept of Statistics Censuses"),
    ("caribbean", "bermuda", "https://www.citypopulation.de/en/bermuda/", "Bermuda Dept of Statistics Censuses"),
    ("caribbean", "guadeloupe", "https://www.citypopulation.de/en/guadeloupe/", "INSEE Guadeloupe Censuses"),
    ("caribbean", "martinique", "https://www.citypopulation.de/en/martinique/", "INSEE Martinique Censuses"),
    ("caribbean", "curacao", "https://www.citypopulation.de/en/curacao/", "CBS Curacao Censuses"),
    ("caribbean", "aruba", "https://www.citypopulation.de/en/aruba/", "CBS Aruba Censuses"),
    ("caribbean", "bonaire_saba_st_eustatius", "https://www.citypopulation.de/en/caribbeannetherlands/", "CBS Netherlands Caribbean Censuses"),
    ("caribbean", "sint_maarten", "https://www.citypopulation.de/en/sintmaarten/", "STAT Sint Maarten Censuses"),
    ("caribbean", "saint_martin", "https://www.citypopulation.de/en/saintmartin/", "INSEE Saint-Martin Censuses"),
    ("caribbean", "saint_barthelemy", "https://www.citypopulation.de/en/saintbarthelemy/", "INSEE Saint-Barthelemy Censuses"),
    ("caribbean", "usvi", "https://www.citypopulation.de/en/usvirginislands/", "US Census Bureau USVI Censuses"),
    ("caribbean", "bvi", "https://www.citypopulation.de/en/britishvirginislands/", "BVI Central Statistics Office Censuses"),
    ("caribbean", "antigua_barbuda", "https://www.citypopulation.de/en/antiguabarbuda/", "Statistics Division Antigua and Barbuda Censuses"),
    ("caribbean", "st_kitts_nevis", "https://www.citypopulation.de/en/stkittsnevis/", "Dept of Statistics St Kitts and Nevis Censuses"),
    ("caribbean", "dominica", "https://www.citypopulation.de/en/dominica/", "CSO Dominica Censuses"),
    ("caribbean", "st_lucia", "https://www.citypopulation.de/en/stlucia/", "CSO Saint Lucia Censuses"),
    ("caribbean", "st_vincent", "https://www.citypopulation.de/en/stvincent/", "Statistical Office St Vincent and the Grenadines Censuses"),
    ("caribbean", "grenada", "https://www.citypopulation.de/en/grenada/", "CSO Grenada Censuses"),
    ("caribbean", "montserrat", "https://www.citypopulation.de/en/montserrat/", "Statistics Dept Montserrat Censuses"),
    ("caribbean", "anguilla", "https://www.citypopulation.de/en/anguilla/", "Anguilla Statistics Dept Censuses"),
    ("caribbean", "cayman_islands", "https://www.citypopulation.de/en/caymanislands/", "ESO Cayman Islands Censuses"),
    ("caribbean", "turks_caicos", "https://www.citypopulation.de/en/turkscaicos/", "Dept of Statistics Turks and Caicos Censuses"),
    # --- MEXICO (multi-census urban & historical major cities supplement to INEGI ITER) ---
    ("mexico", "mexico_cities", "https://www.citypopulation.de/en/mexico/cities/", "INEGI Mexico Censuses (Urban Localities)"),
    ("mexico", "mexico_agglomerations", "https://www.citypopulation.de/en/mexico/agglomerations/", "INEGI / CONAPO Zonas Metropolitanas"),
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
                "cells": [],
                "is_header": False,
                "lat": ad.get("data-lat", ""),
                "lon": ad.get("data-lon", ""),
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

def parse_tables(html_text, country_slug, jur, nso_label, url):
    p = SimpleTableParser()
    p.feed(html_text)
    src_note = re.sub(r"\s+", " ", " ".join(p.source_parts)).strip()
    extracted_rows = []
    for tidx, tbl in enumerate(p.tables):
        t_id = tbl["id"] or f"table_{tidx}"
        rows = tbl["rows"]
        if len(rows) < 2:
            continue
        # Find header row (first row with >= 2 cells)
        headers = rows[0]["cells"]
        if len(headers) < 2:
            continue
        for r in rows[1:]:
            vals = r["cells"]
            if len(vals) < 2 or vals == headers:
                continue
            row_dict = {
                "jurisdiction": jur,
                "country_slug": country_slug,
                "table_id": t_id,
                "nso_source": nso_label,
                "lat": r["lat"],
                "lon": r["lon"],
            }
            for i, v in enumerate(vals):
                hname = headers[i] if i < len(headers) and headers[i] else f"col_{i}"
                row_dict[hname] = v
            extracted_rows.append(row_dict)
    return extracted_rows, src_note

log = []
for jur, slug, url, nso in TARGETS:
    html_path = os.path.join(RAW_DIR, f"{jur}_{slug}_census.html")
    csv_path = os.path.join(RAW_DIR, f"{jur}_{slug}_census.csv")
    try:
        if os.path.exists(html_path) and os.path.getsize(html_path) > 1500:
            with open(html_path, "r", encoding="utf-8", errors="replace") as f:
                html = f.read()
        else:
            r = requests.get(url, headers=HEADERS, timeout=25)
            if r.status_code != 200:
                print(f"FAIL {r.status_code}: {slug} ({url})")
                log.append({"jurisdiction": jur, "slug": slug, "url": url, "status": f"http_{r.status_code}", "rows": 0})
                continue
            html = r.text
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            time.sleep(0.35)

        rows, src_note = parse_tables(html, slug, jur, nso, url)
        # Write normalized CSV with union of all keys in stable order
        all_keys = []
        for r in rows:
            for k in r.keys():
                if k not in all_keys:
                    all_keys.append(k)
        if rows:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=all_keys)
                w.writeheader()
                w.writerows(rows)
        print(f"OK [{jur}/{slug}]: {len(rows)} rows | cols={len(all_keys)}")
        log.append({
            "jurisdiction": jur,
            "slug": slug,
            "nso_source": nso,
            "url": url,
            "status": "ok",
            "html_file": os.path.basename(html_path),
            "csv_file": os.path.basename(csv_path) if rows else None,
            "rows": len(rows),
            "columns": all_keys,
            "source_citation": src_note[:400],
        })
    except Exception as e:
        print(f"ERR [{slug}]: {e}")
        log.append({"jurisdiction": jur, "slug": slug, "url": url, "status": f"err:{e}", "rows": 0})

with open(os.path.join(RAW_DIR, "_official_census_tables_log.json"), "w", encoding="utf-8") as f:
    json.dump(log, f, indent=2, ensure_ascii=False)
print("DONE official census tables:", sum(x["rows"] for x in log), "total rows across", len([x for x in log if x["status"] == "ok"]), "pages.")
