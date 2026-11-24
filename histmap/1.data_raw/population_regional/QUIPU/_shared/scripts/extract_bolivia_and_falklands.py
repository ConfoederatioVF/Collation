"""Generates raw_setts_andean_bolivia.json (100% harmonised with PRETA) and
raw_setts_falklands.json (Falkland Islands Government censuses 1851-2021 +
South Georgia whaling & scientific stations 1904-2021).
"""

import json
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SVEA_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "..", ".."))
OUT_DIR = os.path.join(BASE_DIR, "settlement_sources")

PRETA_BOL_PATH = os.path.join(
    os.path.abspath(os.path.join(BASE_DIR, "..", "..")),
    "PRETA", "3.post_independence", "2.bolivia_after_independence",
    "bolivia_after_independence_settlements.json",
)
EDA_PART3_PATH = os.path.join(BASE_DIR, "subadmin_hgis", "raw_sources", "eda_part3_enumerations.json")

ANDEAN_DEPTS = {
    "bol_la_paz": "La Paz",
    "bol_oruro": "Oruro",
    "bol_potosi": "Potosí",
    "bol_cochabamba": "Cochabamba",
    "bol_chuquisaca": "Chuquisaca",
    "bol_tarija": "Tarija",
}


def extract_andean_bolivia():
    with open(PRETA_BOL_PATH, "r", encoding="utf-8") as f:
        preta_bol = json.load(f)

    out_settlements = {}
    by_dept = {d: 0 for d in ANDEAN_DEPTS.values()}
    years_seen = set()

    for key, rec in preta_bol.items():
        rid = rec.get("region_id") or rec.get("region")
        if rid not in ANDEAN_DEPTS:
            continue
        dept = ANDEAN_DEPTS[rid]
        by_dept[dept] += 1
        pop = rec.get("population", {})
        for y in pop:
            try:
                years_seen.add(int(y))
            except ValueError:
                pass
        entry = dict(rec)
        entry["department"] = dept
        entry["jurisdiction"] = "andean_bolivia"
        entry["population_scope"] = rec.get("population_scope", "city_proper")
        entry["harmonised_with"] = "PRETA/3.post_independence/2.bolivia_after_independence/bolivia_after_independence_settlements.json"
        out_settlements[key] = entry

    out_path = os.path.join(OUT_DIR, "raw_setts_andean_bolivia.json")
    payload = {
        "metadata": {
            "jurisdiction": "andean_bolivia",
            "source": "PRETA harmonised Bolivia gazetteer (INE Bolivia Censuses 1900-2024 + historical series; strictly 6 Andean departments: La Paz, Oruro, Potosí, Cochabamba, Chuquisaca, Tarija)",
            "total_settlements": len(out_settlements),
            "by_department": by_dept,
            "year_span": [min(years_seen), max(years_seen)] if years_seen else [],
            "excluded_lowland_departments": ["Santa Cruz", "El Beni", "Pando"],
        },
        "settlements": out_settlements,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[ANDEAN BOLIVIA] Saved {len(out_settlements)} settlements -> {out_path}")


def extract_falklands_south_atlantic():
    with open(EDA_PART3_PATH, "r", encoding="utf-8") as f:
        eda = json.load(f)
    fk_block = eda["post_independence_censuses"]["falklands_and_south_atlantic"]
    nat_cens = fk_block["falkland_islands_censuses_1851_2021"]
    sub_cens = fk_block["falkland_islands_subregions_1986_2021"]

    # Verified Falkland Islands settlements + South Georgia stations
    # Coordinates verified against Falkland Islands Govt / SGSSI gazetteers
    settlements = {
        "Stanley-Falkland Islands": {
            "name": "Stanley",
            "other_names": ["Port Stanley", "Puerto Argentino"],
            "coords": [-51.6938, -57.857],
            "country": "Falkland Islands",
            "territory": "East Falkland",
            "population_scope": "city_proper",
            "foundation_year": 1843,
            "is_capital": True,
            "population": {
                "1986": sub_cens["1986"]["Stanley"],
                "1991": sub_cens["1991"]["Stanley"],
                "1996": sub_cens["1996"]["Stanley"],
                "2001": sub_cens["2001"]["Stanley"],
                "2006": sub_cens["2006"]["Stanley"],
                "2012": sub_cens["2012"]["Stanley"],
                "2016": sub_cens["2016"]["Stanley"],
                "2021": 2964,  # 2021 Census Stanley (2,538 census-night excl. temporarily absent vs 2,964 usual resident incl. Stanley urban)
            },
            "population_census_night": {
                "2021": sub_cens["2021"]["Stanley"],
            },
            "sources": [
                "Falkland Islands Government Census Reports (1986-2021)",
                "UNSD Demographic Yearbook Table 8 (Stanley)",
            ],
        },
        "RAF Mount Pleasant-Falkland Islands": {
            "name": "RAF Mount Pleasant",
            "other_names": ["Mount Pleasant Complex", "MPC", "MPA"],
            "coords": [-51.8228, -58.4472],
            "country": "Falkland Islands",
            "territory": "East Falkland",
            "population_scope": "city_proper",
            "foundation_year": 1985,
            "population": {
                "1996": sub_cens["1996"]["RAF_Mount_Pleasant"],
                "2001": sub_cens["2001"]["RAF_Mount_Pleasant"],
                "2006": sub_cens["2006"]["RAF_Mount_Pleasant"],
                "2012": sub_cens["2012"]["RAF_Mount_Pleasant"],
                "2016": sub_cens["2016"]["RAF_Mount_Pleasant"],
                "2021": sub_cens["2021"]["RAF_Mount_Pleasant"],
            },
            "notes": "Civilian/contractor census count at Mount Pleasant Complex (excludes rotating UK military garrison).",
            "sources": ["Falkland Islands Government Census Reports (1996-2021)"],
        },
        "Goose Green-Falkland Islands": {
            "name": "Goose Green",
            "other_names": ["Pradera del Ganso"],
            "coords": [-51.8286, -58.9694],
            "country": "Falkland Islands",
            "territory": "East Falkland (Camp)",
            "population_scope": "city_proper",
            "foundation_year": 1875,
            "population": {"2021": 40},
            "sources": ["Falkland Islands Government Census 2021"],
        },
        "Fox Bay-Falkland Islands": {
            "name": "Fox Bay",
            "other_names": ["Bahía Zorro", "Fox Bay East", "Fox Bay West"],
            "coords": [-51.9817, -60.0569],
            "country": "Falkland Islands",
            "territory": "West Falkland (Camp)",
            "population_scope": "city_proper",
            "foundation_year": 1883,
            "population": {"2021": 22},
            "sources": ["Falkland Islands Government Census 2021"],
        },
        "Port Howard-Falkland Islands": {
            "name": "Port Howard",
            "other_names": ["Puerto Mitre"],
            "coords": [-51.615, -59.5208],
            "country": "Falkland Islands",
            "territory": "West Falkland (Camp)",
            "population_scope": "city_proper",
            "foundation_year": 1866,
            "population": {"2021": 22},
            "sources": ["Falkland Islands Government Census 2021"],
        },
        "Pebble Island-Falkland Islands": {
            "name": "Pebble Island",
            "other_names": ["Pebble Island Settlement", "Isla Borbón"],
            "coords": [-51.3092, -59.6122],
            "country": "Falkland Islands",
            "territory": "Outer Islands (Camp)",
            "population_scope": "city_proper",
            "foundation_year": 1846,
            "population": {"2021": 5},
            "sources": ["Falkland Islands Government Census 2021"],
        },
        "Darwin-Falkland Islands": {
            "name": "Darwin",
            "other_names": ["Puerto Darwin"],
            "coords": [-51.8006, -58.9539],
            "country": "Falkland Islands",
            "territory": "East Falkland (Camp)",
            "population_scope": "city_proper",
            "foundation_year": 1859,
            "population": {"2021": 7},
            "sources": ["Falkland Islands Government Census 2021"],
        },
        "Port Louis-Falkland Islands": {
            "name": "Port Louis",
            "other_names": ["Puerto Soledad", "Puerto Luis", "Anson"],
            "coords": [-51.5317, -58.1286],
            "country": "Falkland Islands",
            "territory": "East Falkland (Camp)",
            "population_scope": "city_proper",
            "foundation_year": 1764,
            "population": {"1842": 49},
            "notes": "First permanent settlement (1764) and capital until 1845 when government moved to Stanley; now small sheep farm.",
            "sources": ["Falkland Islands Colonial Blue Books / Government Historical Census Archive"],
        },
        # South Georgia & South Sandwich Islands (whaling era 1904-1965 & BAS scientific era 1965+)
        "Grytviken-South Georgia": {
            "name": "Grytviken",
            "other_names": [],
            "coords": [-54.2814, -36.5081],
            "country": "South Georgia and the South Sandwich Islands",
            "territory": "South Georgia",
            "population_scope": "city_proper",
            "foundation_year": 1904,
            "abandonment_year": 1964,
            "population": {"1904": 60, "1964": 0},
            "notes": "First Antarctic whaling station (C.A. Larsen, Compañía Argentina de Pesca, 1904-1964); summer heritage/museum staff only post-1992.",
            "sources": ["South Georgia Heritage Trust", "Headland (1984) The Island of South Georgia"],
        },
        "Leith Harbour-South Georgia": {
            "name": "Leith Harbour",
            "other_names": [],
            "coords": [-54.1333, -36.6833],
            "country": "South Georgia and the South Sandwich Islands",
            "territory": "South Georgia",
            "population_scope": "city_proper",
            "foundation_year": 1909,
            "abandonment_year": 1965,
            "population": {"1965": 0},
            "notes": "Largest whaling station on South Georgia (Salvesen & Co., 1909-1965); up to ~600-800 summer workers in peak seasons.",
            "sources": ["Government of South Georgia and the South Sandwich Islands (gov.gs)", "Headland (1984)"],
        },
        "Husvik-South Georgia": {
            "name": "Husvik",
            "other_names": ["Husvik Harbour"],
            "coords": [-54.1797, -36.7097],
            "country": "South Georgia and the South Sandwich Islands",
            "territory": "South Georgia",
            "population_scope": "city_proper",
            "foundation_year": 1907,
            "abandonment_year": 1960,
            "population": {"1960": 0},
            "notes": "Whaling station operated 1907-1960 (Tønsbergs Hvalfangeri).",
            "sources": ["South Georgia Heritage Trust", "Headland (1984)"],
        },
        "Stromness-South Georgia": {
            "name": "Stromness",
            "other_names": ["Stromness Harbour"],
            "coords": [-54.1583, -36.7167],
            "country": "South Georgia and the South Sandwich Islands",
            "territory": "South Georgia",
            "population_scope": "city_proper",
            "foundation_year": 1907,
            "abandonment_year": 1961,
            "population": {"1961": 0},
            "notes": "Whaling station (1907-1931) and ship-repair yard (1931-1961).",
            "sources": ["South Georgia Heritage Trust", "Headland (1984)"],
        },
        "Ocean Harbour-South Georgia": {
            "name": "Ocean Harbour",
            "other_names": [],
            "coords": [-54.3333, -36.2667],
            "country": "South Georgia and the South Sandwich Islands",
            "territory": "South Georgia",
            "population_scope": "city_proper",
            "foundation_year": 1909,
            "abandonment_year": 1920,
            "population": {"1920": 0},
            "notes": "Whaling station operated 1909-1920 (Ocean Whaling Company).",
            "sources": ["South Georgia Heritage Trust", "Headland (1984)"],
        },
        "Prince Olav Harbour-South Georgia": {
            "name": "Prince Olav Harbour",
            "other_names": [],
            "coords": [-54.0667, -37.1333],
            "country": "South Georgia and the South Sandwich Islands",
            "territory": "South Georgia",
            "population_scope": "city_proper",
            "foundation_year": 1911,
            "abandonment_year": 1931,
            "population": {"1931": 0},
            "notes": "Whaling station operated 1911-1931 (Southern Whaling & Sealing Co.).",
            "sources": ["South Georgia Heritage Trust", "Headland (1984)"],
        },
        "King Edward Point-South Georgia": {
            "name": "King Edward Point",
            "other_names": ["KEP"],
            "coords": [-54.2833, -36.4944],
            "country": "South Georgia and the South Sandwich Islands",
            "territory": "South Georgia",
            "population_scope": "city_proper",
            "foundation_year": 1909,
            "is_capital": True,
            "population": {"2001": 18, "2011": 16, "2021": 16},
            "notes": "Administrative seat and British Antarctic Survey (BAS) research station (typically 12-19 winter, ~30 summer staff).",
            "sources": ["Government of South Georgia and the South Sandwich Islands (gov.gs)", "British Antarctic Survey"],
        },
    }

    out_path = os.path.join(OUT_DIR, "raw_setts_falklands.json")
    payload = {
        "metadata": {
            "jurisdiction": "falklands",
            "source": "Falkland Islands Government Census Reports (1851-2021) & SGSSI / South Georgia Heritage Trust / BAS records",
            "total_settlements": len(settlements),
            "territory_census_totals_1851_2021": {y: v["total_population"] for y, v in nat_cens.items()},
            "subregional_census_totals_1986_2021": sub_cens,
            "south_georgia_whaling_era_notes": fk_block["south_georgia"],
        },
        "settlements": settlements,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[FALKLANDS & SGSSI] Saved {len(settlements)} settlements + 1851-2021 census series -> {out_path}")


if __name__ == "__main__":
    extract_andean_bolivia()
    extract_falklands_south_atlantic()
