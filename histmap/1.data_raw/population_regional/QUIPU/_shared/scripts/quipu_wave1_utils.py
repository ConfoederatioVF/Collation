"""Shared utilities for Operation Viscount Project QUIPU Stage C Wave 1
settlement census & historical gazetteer harvesting.
"""

import csv
import json
import os
import re
import unicodedata
from html.parser import HTMLParser
from shapely.geometry import shape

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
RAW_DIR = os.path.join(SHARED_DIR, "settlement_sources", "raw")
OUT_DIR = os.path.join(SHARED_DIR, "settlement_sources")
GEO_DIR = os.path.join(SHARED_DIR, "subadmin_hgis", "raw_sources", "geoboundaries")
SVEA_ROOT = os.path.abspath(os.path.join(SHARED_DIR, "..", "..", "..", ".."))


def norm_text(arg0_s):
    """Normalises accents, whitespace, and punctuation for matching."""
    s = unicodedata.normalize("NFKD", str(arg0_s or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def clean_city_name(arg0_name):
    """Cleans settlement names, extracting parenthetical aliases."""
    raw = str(arg0_name or "").strip()
    raw = re.sub(r"\s*\[[^\]]*\]\s*$", "", raw).strip()
    aliases = []
    m = re.search(r"\s*\(([^)]+)\)\s*$", raw)
    if m:
        inner = m.group(1).strip()
        if not inner.startswith("←"):
            aliases.append(inner)
        raw = raw[: m.start()].strip()
    return raw, aliases


def to_int(arg0_val):
    """Parses integer population counts cleanly."""
    if arg0_val is None:
        return None
    s = str(arg0_val).strip().replace(",", "").replace(" ", "").replace("\xa0", "")
    if not s or s in ("...", "-", "—", "n.a.", "None", "nan"):
        return None
    try:
        return int(round(float(s)))
    except ValueError:
        return None


def to_float(arg0_val):
    """Parses European-comma or standard floats cleanly."""
    if arg0_val is None:
        return None
    s = str(arg0_val).strip().replace(",", ".")
    try:
        return round(float(s), 6)
    except ValueError:
        return None


class CityPopParser(HTMLParser):
    """Parses citypopulation.de summary HTML tables (tl, tlc, ts)."""

    def __init__(self):
        super().__init__()
        self.tables = []
        self.cur_table = None
        self.cur_row = None
        self.cur_cell = None

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        if tag == "table":
            self.cur_table = {"id": ad.get("id", ""), "rows": []}
        elif tag == "tr" and self.cur_table is not None:
            self.cur_row = {
                "cells": [],
                "lat": ad.get("data-lat", ""),
                "lon": ad.get("data-lon", ""),
            }
        elif tag in ("td", "th") and self.cur_row is not None:
            self.cur_cell = []
            if ad.get("data-lat") and not self.cur_row["lat"]:
                self.cur_row["lat"] = ad.get("data-lat", "")
                self.cur_row["lon"] = ad.get("data-lon", "")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cur_cell is not None and self.cur_row is not None:
            txt = re.sub(r"\s+", " ", "".join(self.cur_cell)).strip()
            self.cur_row["cells"].append(txt)
            self.cur_cell = None
        elif tag == "tr" and self.cur_row is not None and self.cur_table is not None:
            if self.cur_row["cells"]:
                self.cur_table["rows"].append(self.cur_row)
            self.cur_row = None
        elif tag == "table" and self.cur_table is not None:
            self.tables.append(self.cur_table)
            self.cur_table = None

    def handle_data(self, data):
        if self.cur_cell is not None:
            self.cur_cell.append(data)


def parse_citypop_html(arg0_html_path):
    """Returns dict of {table_id: {'headers': [...], 'years': [(col_idx, year), ...], 'rows': [...]}}."""
    if not os.path.exists(arg0_html_path):
        return {}
    html = open(arg0_html_path, "r", encoding="utf-8", errors="replace").read()
    parser = CityPopParser()
    parser.feed(html)
    out = {}
    for idx, t in enumerate(parser.tables):
        tid = t["id"] or f"table_{idx}"
        if len(t["rows"]) < 2:
            continue
        hdr = t["rows"][0]["cells"]
        year_cols = []
        for ci, h in enumerate(hdr):
            m = re.search(r"((?:19|20)\d{2})-\d{2}-\d{2}", h)
            if m:
                year_cols.append((ci, int(m.group(1))))
        out[tid] = {"headers": hdr, "year_cols": year_cols, "rows": t["rows"][1:]}
    return out


def load_geojson_centroids(arg0_geojson_path, arg1_name_prop="shapeName"):
    """Loads {norm_name: (lat, lon, raw_name)} from a GeoJSON file."""
    out = {}
    if not os.path.exists(arg0_geojson_path):
        return out
    gj = json.load(open(arg0_geojson_path, "r", encoding="utf-8"))
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        nm = props.get(arg1_name_prop) or props.get("ADM2_ES") or props.get("name") or ""
        if not nm or not feat.get("geometry"):
            continue
        pt = shape(feat["geometry"]).representative_point()
        lat, lon = round(pt.y, 6), round(pt.x, 6)
        nk = norm_text(nm)
        out.setdefault(nk, []).append((lat, lon, nm, props))
    return out


def load_hgis_coords_by_iso(arg0_iso3):
    """Loads {norm_name: (lat, lon)} from hgis_indias_colonial_raw.json."""
    out = {}
    hp = os.path.join(OUT_DIR, "hgis_indias_colonial_raw.json")
    if not os.path.exists(hp):
        return out
    data = json.load(open(hp, "r", encoding="utf-8"))
    for st in data.get("settlements", {}).values():
        if st.get("country_iso3") != arg0_iso3:
            continue
        coords = st.get("coords")
        if not coords or len(coords) < 2:
            continue
        for cand in [st.get("modern_name"), st.get("name")] + (st.get("variants") or []):
            nk = norm_text(cand)
            if nk and nk not in out:
                out[nk] = (coords[0], coords[1])
    return out


def load_unsd_country(arg0_country_substr):
    """Loads UNSD Demographic Yearbook city records for a given country substring."""
    unsd_path = os.path.join(
        SVEA_ROOT,
        "histmap", "1.data_raw", "population_regional", "JAGUAR",
        "_shared", "settlement_sources", "raw", "unsd_citypopulation_year_both.csv",
    )
    rows = {}
    if not os.path.exists(unsd_path):
        return rows
    with open(unsd_path, "r", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            c = r.get("Country or Area", "")
            if arg0_country_substr.lower() not in c.lower():
                continue
            city = (r.get("City") or "").strip()
            yr = to_int(r.get("Year"))
            val = to_int(r.get("Value"))
            ctype = (r.get("City type") or "").strip()
            if not city or yr is None or val is None:
                continue
            scope = "metro" if "agglomeration" in ctype.lower() else "city_proper"
            key = (norm_text(city), scope)
            rows.setdefault(key, {"name": city, "scope": scope, "pop": {}})
            rows[key]["pop"][str(yr)] = val
    return rows


def write_settlements_json(arg0_filename, arg1_metadata, arg2_settlements):
    """Writes clean raw_setts_<jurisdiction>.json and prints summary stats."""
    os.makedirs(OUT_DIR, exist_ok=True)
    years = set()
    with_coords = 0
    scope_counts = {}
    for rec in arg2_settlements.values():
        if rec.get("coords") and len(rec["coords"]) == 2:
            with_coords += 1
        sc = rec.get("population_scope", "city_proper")
        scope_counts[sc] = scope_counts.get(sc, 0) + 1
        for y in rec.get("population", {}):
            if str(y).isdigit():
                years.add(int(y))
    arg1_metadata["total_settlements"] = len(arg2_settlements)
    arg1_metadata["with_coords"] = with_coords
    arg1_metadata["coords_coverage"] = round(with_coords / max(1, len(arg2_settlements)), 4)
    arg1_metadata["year_span"] = [min(years), max(years)] if years else []
    arg1_metadata["census_years"] = sorted(years)
    arg1_metadata["population_scope_breakdown"] = scope_counts
    out_path = os.path.join(OUT_DIR, arg0_filename)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"metadata": arg1_metadata, "settlements": arg2_settlements}, f, ensure_ascii=False, indent=2)
    print(f"[{arg1_metadata.get('jurisdiction','').upper()}] {len(arg2_settlements)} settlements ({with_coords} w/ coords, {arg1_metadata['coords_coverage']*100:.1f}%), years={arg1_metadata['year_span']} -> {arg0_filename}")
