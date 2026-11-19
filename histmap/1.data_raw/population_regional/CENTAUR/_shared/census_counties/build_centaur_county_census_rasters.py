"""Builds historical US & Canadian county-level areal census GeoPNGs and metadata
for CENTAUR-II across 1700-1870 (18 decennial snapshots at 5-arcminute resolution).

Data sources (cached under raw_sources/):
- US historical boundaries: Newberry Atlas of Historical County Boundaries (Gen05)
- US 1790-1850 counties: Harvard Dataverse doi:10.7910/DVN/SUCNTD (7563493) +
  Census Bureau Forstall (1996) tables for AL, AR, CA, NM, OR, UT
- US 1860-1870 counties: ICPSR 02896 Parts 9 & 11 (11679681, 11679795)
- Canada 1851-1871 polygons & counts: Borealis UNI-CEN GeoJSONs + CHGIS CD tables
- Canada 1765-1861 pre-Confederation counts: Borealis Censuses of Canada 1665-1871
"""

import io
import json
import math
import pathlib
import re
import urllib.request
import zipfile

import numpy as np
import pandas as pd
import pymupdf
import shapefile
from PIL import Image, ImageDraw

try:
  import json5
except ImportError:
  json5 = None

GRID_W = 4320
GRID_H = 2160
DECENNIAL_YEARS = list(range(1700, 1880, 10))
US_CENSUS_DAY = {
  1790: 17900802,
  1800: 18000804,
  1810: 18100806,
  1820: 18200807,
  1830: 18300601,
  1840: 18400601,
  1850: 18500601,
  1860: 18600601,
  1870: 18700601,
}

STATE_FIPS_TO_ST = {
  1: "AL", 2: "AK", 4: "AZ", 5: "AR", 6: "CA", 8: "CO", 9: "CT", 10: "DE", 11: "DC",
  12: "FL", 13: "GA", 15: "HI", 16: "ID", 17: "IL", 18: "IN", 19: "IA", 20: "KS",
  21: "KY", 22: "LA", 23: "ME", 24: "MD", 25: "MA", 26: "MI", 27: "MN", 28: "MS",
  29: "MO", 30: "MT", 31: "NE", 32: "NV", 33: "NH", 34: "NJ", 35: "NM", 36: "NY",
  37: "NC", 38: "ND", 39: "OH", 40: "OK", 41: "OR", 42: "PA", 44: "RI",
  45: "SC", 46: "SD", 47: "TN", 48: "TX", 49: "UT", 50: "VT", 51: "VA", 53: "WA",
  54: "WV", 55: "WI", 56: "WY", 90: "CT",
}

US_STATE_FULL_TO_ST = {
  "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
  "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
  "district of columbia": "DC", "florida": "FL", "georgia": "GA", "idaho": "ID",
  "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY",
  "louisiana": "LA", "maine": "ME", "district of maine": "ME", "maryland": "MD",
  "massachusetts": "MA", "massachusetts colony": "MA", "michigan": "MI",
  "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT",
  "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
  "new mexico": "NM", "new york": "NY", "north carolina": "NC", "north dakota": "ND",
  "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
  "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
  "tennessee": "TN", "southwest territory": "TN", "texas": "TX", "utah": "UT",
  "deseret": "UT", "vermont": "VT", "vermont republic": "VT", "virginia": "VA", "washington": "WA",
  "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
  "dakota territory": "SD", "louisiana territory": "MO", "orleans territory": "LA",
  "northwest territory": "NW",
}

US_COLONY_KEY_BY_ST = {
  "NH": "ca1_new_hampshire",
  "MA": "ca1_massachusetts_bay_maine",
  "ME": "ca1_massachusetts_bay_maine",
  "RI": "ca1_rhode_island",
  "CT": "ca1_connecticut",
  "NY": "ca1_new_york",
  "NJ": "ca1_new_jersey",
  "PA": "ca1_pennsylvania",
  "DE": "ca1_delaware",
  "MD": "ca1_maryland",
  "VA": "ca1_virginia",
  "NC": "ca1_north_carolina",
  "SC": "ca1_south_carolina",
  "GA": "ca1_georgia",
  "VT": "ca2_vermont_republic",
  "KY": "ca2_kentucky_frontier",
  "TN": "ca2_watauga_cumberland_frontier",
}

US_STATE_KEY_BY_ST = {
  "AL": "us_alabama", "AR": "us_arkansas", "AZ": "us_arizona", "CA": "us_california",
  "CO": "us_colorado", "CT": "us_connecticut", "DC": "us_district_of_columbia",
  "DE": "us_delaware", "FL": "us_florida", "GA": "us_georgia", "IA": "us_iowa",
  "ID": "us_idaho", "IL": "us_illinois", "IN": "us_indiana", "KS": "us_kansas",
  "KY": "us_kentucky", "LA": "us_louisiana", "MA": "us_massachusetts",
  "MD": "us_maryland", "ME": "us_maine", "MI": "us_michigan", "MN": "us_minnesota",
  "MO": "us_missouri", "MS": "us_mississippi", "MT": "us_montana",
  "NC": "us_north_carolina", "ND": "us_north_dakota", "NE": "us_nebraska",
  "NH": "us_new_hampshire", "NJ": "us_new_jersey", "NM": "us_new_mexico",
  "NV": "us_nevada", "NY": "us_new_york", "OH": "us_ohio", "OR": "us_oregon",
  "PA": "us_pennsylvania", "RI": "us_rhode_island", "SC": "us_south_carolina",
  "SD": "us_south_dakota", "TN": "us_tennessee", "TX": "us_texas", "UT": "us_utah",
  "VA": "us_virginia", "VT": "us_vermont", "WA": "us_washington", "WI": "us_wisconsin",
  "WV": "us_west_virginia", "WY": "us_wyoming",
}

US_NAME_ALIASES = {
  ("NC", "GREENE"): [("NC", "DOBBS"), ("NC", "GLASGOW")],
  ("NC", "LENOIR"): [("NC", "DOBBS")],
  ("SC", "CHARLESTON"): [("SC", "CHARLESTON DIST"), ("SC", "CHARLESTON P")],
  ("SC", "COLLETON"): [("SC", "COLLETON DIST")],
  ("SC", "BEAUFORT"): [("SC", "BEAUFORT DIST"), ("SC", "ST HELENA P")],
  ("SC", "GEORGETOWN"): [("SC", "GEORGETOWN DIST"), ("SC", "ALL SAINTS P")],
  ("SC", "ORANGEBURG"): [("SC", "ORANGEBURG DIST"), ("SC", "ORANGEBURGH DIST")],
  ("SC", "SUMTER"): [("SC", "CAMDEN DIST"), ("SC", "CLAREMONT")],
  ("SC", "BARNWELL"): [("SC", "BARNWELL DIST"), ("SC", "WINTON")],
  ("SC", "RICHLAND"): [("SC", "CAMDEN DIST")],
  ("SC", "KERSHAW"): [("SC", "CAMDEN DIST")],
  ("SC", "MARION"): [("SC", "LIBERTY")],
  ("SC", "DILLON"): [("SC", "MARION")],
  ("DC", "DIST COLUMBIA"): [("DC", "DISTRICT OF COLUMBIA"), ("DC", "WASHINGTON"), ("MD", "DISTRICT OF COLUMBIA")],
  ("DC", "DISTRICT OF COLUMBIA"): [("DC", "WASHINGTON")],
  ("DC", "WASHINGTON"): [("DC", "DISTRICT OF COLUMBIA")],
  ("CO", "ARAPAHOE"): [("KS", "ARAPAHOE")],
  ("OH", "WASHINGTON"): [("NW", "WASHINGTON")],
  ("OH", "HAMILTON"): [("NW", "HAMILTON")],
  ("OH", "ADAMS"): [("NW", "ADAMS")],
  ("OH", "ROSS"): [("NW", "ROSS")],
  ("OH", "JEFFERSON"): [("NW", "JEFFERSON")],
  ("IL", "ST CLAIR"): [("NW", "ST CLAIR"), ("IN", "ST CLAIR")],
  ("IL", "RANDOLPH"): [("NW", "RANDOLPH"), ("IN", "RANDOLPH")],
  ("IN", "KNOX"): [("NW", "KNOX")],
  ("MI", "WAYNE"): [("NW", "WAYNE")],
  ("VA", "NANSEMOND"): [("VA", "SUFFOLK")],
  ("LA", "ST JOHN BAPTIST"): [("LA", "ST JOHN THE BAPTIST")],
  ("LA", "DESOTO"): [("LA", "DE SOTO")],
  ("WI", "FOND DU LAC"): [("WI", "FOND DU LAC")],
  ("MN", "ST LOUIS"): [("MN", "SAINT LOUIS")],
  ("MD", "ST MARYS"): [("MD", "SAINT MARYS")],
  ("MD", "QUEEN ANNES"): [("MD", "QUEEN ANNES")],
  ("MD", "PRINCE GEORGES"): [("MD", "PRINCE GEORGES")],
}

QC_SEIGNEURY_1700_WEIGHTS = {
  "Montréal": 11000, "Québec": 10000, "Montmorenci": 3200, "Portneuf": 3400,
  "Champlain": 2200, "St. Maurice": 2800, "Berthier": 2600, "Leinster": 2800,
  "Richelieu": 3600, "Verchères": 2900, "Chambly": 2600, "Lotbinière": 2200,
  "Nicolet": 2000, "Yamaska": 1900, "Bellechasse": 2800, "L'Islet": 2400,
  "Kamouraska": 2200, "Dorchester": 2600, "Vaudreuil": 1200, "Terrebonne": 1800,
  "Rouville": 1400, "St. Hyacinthe": 1200, "Rimouski": 450,
}

# Historical opening decades for progressively settled Canadian counties (1700-1850)
CA_FOUNDED_OVERRIDE = {
  # Quebec St. Lawrence seigneuries open from 1700; hinterlands later
  ("QC", "Rimouski"): 1750, ("QC", "Bonaventure"): 1760, ("QC", "Gaspé"): 1760,
  ("QC", "Huntingdon"): 1770, ("QC", "Two Mountains"): 1770, ("QC", "Châteauguay"): 1770,
  ("QC", "Beauharnois"): 1790, ("QC", "Argenteuil"): 1800, ("QC", "Missisquoi"): 1790,
  ("QC", "Stanstead"): 1790, ("QC", "Shefford"): 1800, ("QC", "Sherbrooke"): 1800,
  ("QC", "Drummond"): 1810, ("QC", "Megantic"): 1820, ("QC", "Beauce"): 1780,
  ("QC", "Ottawa"): 1810, ("QC", "Pontiac"): 1820, ("QC", "Saguenay"): 1840,
  ("QC", "Chicoutimi"): 1840, ("QC", "Arthabaska"): 1840, ("QC", "Bagot"): 1810,
  ("QC", "Compton"): 1800, ("QC", "Wolfe"): 1840, ("QC", "Témiscouata"): 1800,
  ("QC", "Charlevoix"): 1710, ("QC", "Labelle"): 1840, ("QC", "Joliette"): 1790,
  ("QC", "Montcalm"): 1810, ("QC", "Maskinongé"): 1710,
  # Ontario: Detroit/Assumption & Frontenac early fur posts; Loyalist St.Lawrence/Lake Ontario 1783+
  ("ON", "Essex"): 1710, ("ON", "Frontenac"): 1760,
  ("ON", "Glengary"): 1784, ("ON", "Stormont"): 1784, ("ON", "Dundas"): 1784,
  ("ON", "Grenville"): 1784, ("ON", "Leeds"): 1784, ("ON", "Lennox"): 1784,
  ("ON", "Addington"): 1784, ("ON", "Prince Edward"): 1784, ("ON", "Hastings"): 1790,
  ("ON", "Lincoln"): 1783, ("ON", "Welland"): 1783, ("ON", "Wentworth"): 1790,
  ("ON", "Halton"): 1790, ("ON", "York"): 1790, ("ON", "Toronto, City"): 1793,
  ("ON", "Durham"): 1795, ("ON", "Northumberland"): 1795, ("ON", "Norfolk"): 1795,
  ("ON", "Kent"): 1792, ("ON", "Elgin"): 1805, ("ON", "Middlesex"): 1805,
  ("ON", "Oxford"): 1800, ("ON", "Brant"): 1790, ("ON", "Haldimand"): 1790,
  ("ON", "Waterloo"): 1805, ("ON", "Peel"): 1815, ("ON", "Prescott"): 1800,
  ("ON", "Russell"): 1815, ("ON", "Carleton"): 1818, ("ON", "Lanark"): 1816,
  ("ON", "Peterboro"): 1820, ("ON", "Victoria"): 1825, ("ON", "Simcoe"): 1820,
  ("ON", "Wellington"): 1828, ("ON", "Huron"): 1830, ("ON", "Perth"): 1832,
  ("ON", "Ontario"): 1800, ("ON", "Lambton"): 1830, ("ON", "Renfrew"): 1835,
  ("ON", "Grey"): 1842, ("ON", "Bruce"): 1850, ("ON", "Algoma"): 1855,
  ("ON", "Nipissing"): 1860, ("ON", "Parry Sound"): 1865, ("ON", "Muskoka"): 1860,
  # Nova Scotia & New Brunswick early Acadia vs Halifax/Lunenburg vs Loyalists
  ("NS", "Annapolis"): 1700, ("NS", "King's"): 1700, ("NS", "Hants"): 1700,
  ("NS", "Cumberland"): 1700, ("NS", "Colchester"): 1700, ("NS", "Cape Breton"): 1713,
  ("NS", "Richmond"): 1713, ("NS", "Halifax"): 1749, ("NS", "Lunenburg"): 1753,
  ("NS", "Yarmouth"): 1761, ("NS", "Shelburne"): 1760, ("NS", "Queens"): 1760,
  ("NS", "Digby"): 1760, ("NS", "Pictou"): 1767, ("NS", "Antigonish"): 1784,
  ("NS", "Guysborough"): 1784, ("NS", "Inverness"): 1790, ("NS", "Victoria"): 1800,
  ("NB", "Westmorland"): 1700, ("NB", "St. John"): 1762, ("NB", "Sunbury"): 1765,
  ("NB", "Charlotte"): 1783, ("NB", "King's"): 1783, ("NB", "Queen's"): 1783,
  ("NB", "York"): 1783, ("NB", "Northumberland"): 1770, ("NB", "Albert"): 1765,
  ("NB", "Kent"): 1770, ("NB", "Gloucester"): 1770, ("NB", "Carleton"): 1800,
  ("NB", "Restigouche"): 1810, ("NB", "Victoria"): 1825,
  # PEI
  ("PE", "Queen's"): 1720, ("PE", "King's"): 1750, ("PE", "Prince"): 1765,
}


def load_json5_file(arg0_path):
  """Parses JSON5/JSON reliably even when standard json5 package is absent."""
  txt = pathlib.Path(arg0_path).read_text(encoding="utf-8")
  if json5 is not None:
    return json5.loads(txt)
  cleaned = re.sub(r"//.*?$|/\*.*?\*/", "", txt, flags=re.MULTILINE | re.DOTALL)
  cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
  return json.loads(cleaned)


def norm_county_name(arg0_name):
  """Normalises US and Canadian county/district names for resilient historical joins."""
  s = str(arg0_name or "").upper()
  s = s.replace("É", "E").replace("È", "E").replace("Ê", "E").replace("Â", "A").replace("Î", "I").replace("Ô", "O").replace("Ü", "U")
  s = re.sub(r"\([^)]*\)", "", s)
  s = s.replace("?", "'").replace(".", "").replace("'", "").replace("-", " ").strip()
  if s.startswith("DEUX MONTAGNES"):
    s = "TWO MOUNTAINS"
  if s.startswith("GLENGARRY"):
    s = "GLENGARY"
  if s.startswith("SAINT ") or s.startswith("SAINTE "):
    s = "ST " + s.split(" ", 1)[1]
  for suf in [" COUNTY", " PARISH", " DISTRICT", " DIST", " CITY", " TOWN", " VILLE", " COMTE", " COLONY", " TERRITORY", " TERR"]:
    if s.endswith(suf):
      s = s[:-len(suf)].strip()
  return re.sub(r"\s+", " ", s)


def st_abbr_from_ahcb(arg0_state_terr):
  """Maps AHCB STATE_TERR strings to 2-letter postal abbreviations."""
  s = str(arg0_state_terr or "").strip().lower()
  if s in US_STATE_FULL_TO_ST:
    return US_STATE_FULL_TO_ST[s]
  base = re.sub(r"\s+(colony|territory|terr\.?|state)$", "", s).strip()
  return US_STATE_FULL_TO_ST.get(base, base.upper()[:4])


def is_ahcb_unorganised(arg0_rec):
  """Identifies non-county / unorganised / Indian territory AHCB placeholder polygons."""
  nm = str(arg0_rec["NAME"]).upper()
  st = str(arg0_rec["STATE_TERR"]).upper()
  ct = str(arg0_rec["CNTY_TYPE"]).upper()
  bad_kw = (
    "NON-COUNTY", "UNORG", "INDIAN TERR", "INDIAN RES", "INDIAN LAND", "DESERET",
    "MEXICAN CESSION", "ALASKA PURCHASE", "NORTHWEST TERR", "SOUTHWEST TERR",
    "DAKOTA TERR", "OKLAHOMA TERR", "CHEROKEE OUTLET", "YOUNG TERR", "SANTA FE (EXT)",
    "BEXAR TERR", "MASSACHUSETTS", "NEW HAMPSHIRE COLONY",
  )
  if re.search(r"\bNCA\b", nm) or any(kw in nm for kw in bad_kw):
    return True
  if any(kw in st for kw in ("INDIAN TERR", "INDIAN RES", "UNORG")):
    return True
  if nm == st and str(arg0_rec["FIPS"]).strip() in ("", "0"):
    return True
  if ct not in ("COUNTY", "PARISH", "DISTRICT"):
    return True
  return False


def extract_forstall_missing(arg0_pdf_path):
  """Extracts 1810-1850 county counts for states absent from Harvard 7563493 using Forstall (1996)."""
  doc = pymupdf.open(arg0_pdf_path)
  targets = [
    ("AL", "ALABAMA", "1800-1880", [1810, 1820, 1830, 1840, 1850]),
    ("AR", "ARKANSAS", "1810-1880", [1820, 1830, 1840, 1850]),
    ("CA", "CALIFORNIA", "1850-1880", [1850]),
    ("NM", "NEW MEXICO", "1850-1880", [1850]),
    ("OR", "OREGON", "1850-1880", [1850]),
    ("UT", "UTAH", "1850-1880", [1850]),
  ]

  def parse_num(arg0_txt):
    s = arg0_txt.strip().replace("~", "").replace("`", "")
    if re.fullmatch(r"\d{1,3}(?:[,.]\d{3})*|\d+", s):
      return int(s.replace(",", "").replace(".", ""))
    return None

  out_rows = []
  for st_code, pref, span_pat, target_yrs in targets:
    pages = [i for i, p in enumerate(doc) if re.search(rf"{pref}.*{span_pat}", p.get_text("text"))]
    st_tot = {}
    cnt_map = {y: {} for y in target_yrs}
    for pg in pages:
      words = doc[pg].get_text("words")
      cands = [w for w in words if w[4].lower() == "county" and w[0] < 100 and w[1] < 200]
      if not cands:
        continue
      hdr_y = cands[0][1]
      hdr_w = sorted([w for w in words if abs(w[1] - hdr_y) < 10 and 100 < w[0] < 490 and w[4][0] == "1"], key=lambda w: w[0])
      cols = [(1880 - 10 * idx, 0.5 * (w[0] + w[2])) for idx, w in enumerate(hdr_w)]
      first_num_x = cols[0][1] - 28
      note_x = cols[-1][1] + 25
      body = sorted([w for w in words if hdr_y + 8 < w[1] < 765], key=lambda w: (w[1], w[0]))
      lines = []
      for w in body:
        if not lines or abs(w[1] - lines[-1][0][1]) > 4.5:
          lines.append([w])
        else:
          lines[-1].append(w)
      pending = ""
      for ln in lines:
        ln.sort(key=lambda w: w[0])
        ntoks = [w[4] for w in ln if w[0] < first_num_x - 8]
        nums = []
        for w in ln:
          if first_num_x - 8 <= w[0] < note_x:
            v = parse_num(w[4])
            if v is not None:
              xc = 0.5 * (w[0] + w[2])
              by = min(cols, key=lambda c: abs(c[1] - xc))
              if abs(by[1] - xc) < 22:
                nums.append((by[0], v))
        cname = " ".join(ntoks).strip()
        if cname and not nums:
          pending = cname
          continue
        if nums and not cname and pending:
          cname = pending
          pending = ""
        elif cname:
          pending = ""
        if not cname or not nums:
          continue
        if cname.isupper() and cname.replace(" ", "") == pref.replace(" ", "") and not st_tot:
          for y, v in nums:
            if y in target_yrs:
              st_tot[y] = v
        elif "part" not in cname.lower() and "see " not in cname.lower() and not cname.lower().startswith("note"):
          for y, v in nums:
            if y in target_yrs:
              cnt_map[y][cname] = v
    for y in target_yrs:
      s_val = sum(cnt_map[y].values())
      off_val = st_tot.get(y, s_val)
      scale = (off_val / s_val) if (s_val > 0 and off_val > 0 and 0.90 <= s_val / off_val <= 1.05) else 1.0
      for cname, val in cnt_map[y].items():
        out_rows.append({"year": y, "st": st_code, "fips": "", "name": cname, "totpop": val * scale})
  return out_rows


def draw_polygons_to_mask(arg0_items, arg1_domain_valid, arg2_area_grid):
  """Rasterises GeoJSON/Shapefile polygons onto 4320x2160 grid preserving tiny island/city fallback."""
  img = Image.new("I", (GRID_W, GRID_H), 0)
  draw = ImageDraw.Draw(img)

  # Sort strictly largest -> smallest so tiny urban enclaves and island parishes stay visible on top
  ordered = sorted(arg0_items, key=lambda x: -float(x["geom_area_km2"]))
  for item in ordered:
    gid = int(item["grid_id"])
    for ring_list in item["rings"]:
      if len(ring_list) < 3:
        continue
      pts = [
        (
          min(GRID_W - 1, max(0, int(round((lon + 180.0) * GRID_W / 360.0)))),
          min(GRID_H - 1, max(0, int(round((90.0 - lat) * GRID_H / 180.0)))),
        )
        for lon, lat in ring_list
      ]
      if len(pts) >= 3:
        draw.polygon(pts, fill=gid)

  id_arr = np.array(img, dtype=np.int32, copy=True)
  id_arr[~arg1_domain_valid] = 0

  # Ensure small/coastal counties receive at least 1 valid land pixel via centroid nearest search
  present = set(np.unique(id_arr[id_arr > 0]).tolist())
  for item in ordered:
    gid = int(item["grid_id"])
    if gid in present:
      continue
    cx = min(GRID_W - 1, max(0, int((item["lon_c"] + 180.0) * GRID_W / 360.0)))
    cy = min(GRID_H - 1, max(0, int((90.0 - item["lat_c"]) * GRID_H / 180.0)))
    found = False
    for rad in range(0, 5):
      for dy in range(-rad, rad + 1):
        nr = cy + dy
        if nr < 0 or nr >= GRID_H:
          continue
        for dx in range(-rad, rad + 1):
          nc = (cx + dx) % GRID_W
          if arg1_domain_valid[nr, nc]:
            id_arr[nr, nc] = gid
            found = True
            break
        if found:
          break
      if found:
        break

  # Compute final rasterised land area & pixel count per county id
  stats = {}
  valid_r, valid_c = np.where(id_arr > 0)
  ids = id_arr[valid_r, valid_c]
  areas = arg2_area_grid[valid_r, valid_c]
  for gid_val in np.unique(ids):
    m = ids == gid_val
    stats[int(gid_val)] = (int(m.sum()), float(areas[m].sum()))
  return id_arr, stats


def build_hyde_rur_lookup(arg0_root, arg1_year):
  """Loads raw un-blurred HYDE rurc raster as (2160, 4320) float32 array for colonial/split weights."""
  p = arg0_root / "histmap/2.data_cleaning/landuse_HYDE/rasters" / f"rurc_{arg1_year}AD.png"
  if not p.exists():
    return None
  arr = np.asarray(Image.open(p).convert("RGBA"), dtype=np.uint8)
  raw = np.ascontiguousarray(arr).view(">f4")[..., 0]
  return np.where(np.isfinite(raw) & (raw > 0), raw, 0.0)


def run_build():
  """Executes end-to-end download, historical county reconciliation, and 1700-1870 rasterisation."""
  centaur_dir = pathlib.Path("histmap/1.data_raw/population_regional/CENTAUR")
  raw_dir = centaur_dir / "_shared/census_counties/raw_sources"
  out_dir = centaur_dir / "_shared/census_counties/rasters"
  out_dir.mkdir(parents=True, exist_ok=True)
  root = pathlib.Path(".")

  # 1. Load domain mask & pixel area raster
  dm_arr = np.asarray(Image.open(centaur_dir / "_shared/sites_northern_america/config/centaur_na_domain_mask.png").convert("RGBA"), dtype=np.uint8)
  domain_valid = (dm_arr[:, :, 3] > 0) & (dm_arr[:, :, :3].sum(axis=2) > 0)
  la_arr = np.asarray(Image.open(root / "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png").convert("RGBA"), dtype=np.uint8)
  area_raw = np.ascontiguousarray(la_arr).view(">f4")[..., 0]
  area_grid = np.where(np.isfinite(area_raw) & (area_raw > 0), area_raw, 40.0)

  # 2. Load CENTAUR regional benchmarks & settlement JSONs
  col1_j5 = load_json5_file(centaur_dir / "4.colonial_america_and_canada/1.colonial_america_to_1754/colonial_america_to_1754.json5")["regions"]
  col2_j5 = load_json5_file(centaur_dir / "4.colonial_america_and_canada/2.colonial_america_to_1783/colonial_america_to_1783.json5")["regions"]
  us_j5 = load_json5_file(centaur_dir / "5.modern_canada_and_united_states/2.united_states_post_independence/united_states_post_independence.json5")["regions"]
  cc1_j5 = load_json5_file(centaur_dir / "4.colonial_america_and_canada/3.colonial_canada_to_1763/colonial_canada_to_1763.json5")["regions"]
  cc2_j5 = load_json5_file(centaur_dir / "4.colonial_america_and_canada/4.colonial_canada_to_1867/colonial_canada_to_1867.json5")["regions"]
  ca_j5 = load_json5_file(centaur_dir / "5.modern_canada_and_united_states/1.canada_post_confederation/canada_post_confederation.json5")["regions"]
  doc_setts = json.loads((centaur_dir / "_shared/sites_northern_america/config/documented_settlements.json").read_text(encoding="utf-8")).get("settlements", [])

  # Helper interpolating regional target at year yr
  def interp_region(reg_dict, rkey, yr):
    rv = reg_dict.get(rkey)
    if not rv:
      return 0.0
    p = {int(k): float(v[0] if isinstance(v, list) else v) for k, v in (rv.get("population") or {}).items()}
    if not p:
      return 0.0
    if yr in p:
      return p[yr]
    ks = sorted(p)
    if yr <= ks[0]:
      return p[ks[0]]
    if yr >= ks[-1]:
      return p[ks[-1]]
    for i in range(len(ks) - 1):
      if ks[i] <= yr <= ks[i + 1]:
        t = (yr - ks[i]) / max(1, ks[i + 1] - ks[i])
        return (1.0 - t) * p[ks[i]] + t * p[ks[i + 1]]
    return 0.0

  # 3. Parse US Shapefile & US census tables
  zf = zipfile.ZipFile(raw_dir / "US_AtlasHCB_Counties_Gen05.zip")
  shp_name = [n for n in zf.namelist() if n.endswith(".shp")][0]
  sf = shapefile.Reader(shp=io.BytesIO(zf.read(shp_name)), dbf=io.BytesIO(zf.read(shp_name[:-4] + ".dbf")), shx=io.BytesIO(zf.read(shp_name[:-4] + ".shx")), encoding="latin1")
  ahcb_recs = sf.records()
  ahcb_shapes = sf.shapes()

  def shape_to_rings(shp_obj):
    pts = shp_obj.points
    parts = list(shp_obj.parts) + [len(pts)]
    rings = [pts[parts[i]:parts[i + 1]] for i in range(len(parts) - 1) if parts[i + 1] - parts[i] >= 3]
    if not rings:
      return [], 0.0, 0.0
    all_x = [p[0] for p in pts]
    all_y = [p[1] for p in pts]
    return rings, 0.5 * (min(all_x) + max(all_x)), 0.5 * (min(all_y) + max(all_y))

  df_early = pd.read_csv(raw_dir / "us_adult_male_counties_1789_1860.tab", sep="\t", low_memory=False)
  df_1860 = pd.read_csv(raw_dir / "icpsr_02896_0009_1860.tab", sep="\t", low_memory=False)
  df_1870 = pd.read_csv(raw_dir / "icpsr_02896_0011_1870.tab", sep="\t", low_memory=False)
  forstall_rows = extract_forstall_missing(raw_dir / "us_census_forstall_1790_1990.pdf")

  def get_us_census_rows(yr):
    rows = []
    seen_st_yr = set()
    if yr <= 1850:
      sub = df_early[(df_early["year"] == yr) & (df_early["totpop"] > 0)]
      for _, r in sub.iterrows():
        fp = str(int(r["fips"])).zfill(5) if pd.notna(r["fips"]) and int(r["fips"]) > 0 else ""
        if fp.startswith("90"):
          fp = "09" + fp[2:]
        if fp == "24510":
          # Harvard 7563493 double-counts Baltimore City inside Baltimore County through 1850
          continue
        st_num = int(fp[:2]) if len(fp) == 5 else (int(r["statefip"]) if pd.notna(r["statefip"]) else 0)
        st = STATE_FIPS_TO_ST.get(st_num, "")
        if st:
          seen_st_yr.add(st)
        rows.append({"st": st, "fips": fp, "name": str(r["name"]), "totpop": float(r["totpop"])})
      for fr in forstall_rows:
        if fr["year"] == yr and fr["st"] not in seen_st_yr:
          rows.append(dict(fr))
      if 1800 <= yr <= 1850 and "DC" not in seen_st_yr:
        dc_pop = interp_region(us_j5, "usa_district_of_columbia", yr)
        if dc_pop > 0:
          rows.append({"st": "DC", "fips": "11001", "name": "DISTRICT OF COLUMBIA", "totpop": dc_pop})
    elif yr == 1860:
      sub = df_1860[(df_1860["level"] == 1) & (df_1860["totpop"] > 0)]
      for _, r in sub.iterrows():
        fp = str(int(r["fips"])).zfill(5) if pd.notna(r["fips"]) and int(r["fips"]) > 0 else ""
        st_num = int(fp[:2]) if len(fp) == 5 else (int(r["statefip"]) if pd.notna(r["statefip"]) else 0)
        st = STATE_FIPS_TO_ST.get(st_num, "")
        rows.append({"st": st, "fips": fp, "name": str(r["name"]), "totpop": float(r["totpop"])})
    else:
      sub = df_1870[(df_1870["level"] == 1) & (df_1870["totpop"] > 0)]
      for _, r in sub.iterrows():
        fp = str(int(r["fips"])).zfill(5) if pd.notna(r["fips"]) and int(r["fips"]) > 0 else ""
        st = STATE_FIPS_TO_ST.get(int(fp[:2]), "") if len(fp) == 5 else ""
        rows.append({"st": st, "fips": fp, "name": str(r["name"]), "totpop": float(r["totpop"])})
    return rows

  def build_us_snapshot_items(yr, us_1790_grid=None, us_1790_meta=None):
    dt = US_CENSUS_DAY.get(yr, yr * 10000 + 701)
    # Build active AHCB polygons excluding NCA/unorganised placeholders & overlapping SC Parishes/District duplicates
    raw_act = []
    for idx, rec in enumerate(ahcb_recs):
      if int(rec["START_N"]) <= dt <= int(rec["END_N"]) and not is_ahcb_unorganised(rec):
        raw_act.append(idx)

    # Filter overlapping South Carolina polygons cleanly:
    # <= 1775 keep SC Parishes + upcountry Counties; >= 1780 drop SC Parishes & drop SC Districts covered by Counties
    sc_fips_present = set(
      str(ahcb_recs[i]["FIPS"]).strip()
      for i in raw_act
      if st_abbr_from_ahcb(ahcb_recs[i]["STATE_TERR"]) == "SC" and str(ahcb_recs[i]["FIPS"]).strip()
    )
    sc_county_names = set(
      norm_county_name(ahcb_recs[i]["NAME"])
      for i in raw_act
      if st_abbr_from_ahcb(ahcb_recs[i]["STATE_TERR"]) == "SC" and str(ahcb_recs[i]["CNTY_TYPE"]) == "County"
    )
    act = []
    for i in raw_act:
      rec = ahcb_recs[i]
      st = st_abbr_from_ahcb(rec["STATE_TERR"])
      ct = str(rec["CNTY_TYPE"])
      nm = norm_county_name(rec["NAME"])
      if st == "SC":
        if yr >= 1780 and ct == "Parish":
          continue
        if yr < 1780 and ct == "District":
          continue
        if yr >= 1780 and ct == "District" and nm in sc_county_names:
          continue
      act.append(i)

    # Also catch TN Lake created 1870-06-09 if dt==18700601 -> check dt2 = 18700701
    if yr == 1870:
      seen_ids = set(str(ahcb_recs[i]["ID"]) for i in act)
      for idx, rec in enumerate(ahcb_recs):
        if str(rec["ID"]) not in seen_ids and int(rec["START_N"]) <= 18700701 <= int(rec["END_N"]) and not is_ahcb_unorganised(rec):
          if st_abbr_from_ahcb(rec["STATE_TERR"]) == "TN" and "LAKE" in str(rec["NAME"]).upper():
            act.append(idx)

    by_fips, by_st_nm = {}, {}
    items = []
    for k, idx in enumerate(act):
      rec = ahcb_recs[idx]
      fp = str(rec["FIPS"]).strip().zfill(5) if str(rec["FIPS"]).strip() else ""
      st = st_abbr_from_ahcb(rec["STATE_TERR"])
      if len(fp) == 5 and fp[:2].isdigit() and int(fp[:2]) in STATE_FIPS_TO_ST:
        st = STATE_FIPS_TO_ST[int(fp[:2])]
      elif st == "MEXI":
        st = "NM"
      nm = norm_county_name(rec["NAME"])
      rings, lon_c, lat_c = shape_to_rings(ahcb_shapes[idx])
      area_km2 = float(rec["AREA_SQMI"] or 0) * 2.58999
      it = {
        "poly_idx": k,
        "name": f"{rec['NAME']} ({st})",
        "admin1": US_STATE_KEY_BY_ST.get(st, st),
        "st": st,
        "country": "US",
        "country_code": 1,
        "fips_or_uid": fp or str(rec["ID"]),
        "geom_area_km2": max(1.0, area_km2),
        "lon_c": lon_c,
        "lat_c": lat_c,
        "rings": rings,
        "census_pop": 0.0,
        "founded_year": int(rec["START_N"]) // 10000,
      }
      items.append(it)
      if fp:
        by_fips.setdefault(fp, []).append(k)
      by_st_nm.setdefault((st, nm), []).append(k)
      if fp and len(fp) == 5:
        fp_st = STATE_FIPS_TO_ST.get(int(fp[:2]), "")
        if fp_st:
          by_st_nm.setdefault((fp_st, nm), []).append(k)

    if yr >= 1790:
      c_rows = get_us_census_rows(yr)
      tot_census = sum(r["totpop"] for r in c_rows)
      matched_census = 0.0
      unmatched_by_st = {}
      matched_by_st = {}
      for r in c_rows:
        fp, st, nm, pop = r["fips"], r["st"], norm_county_name(r["name"]), r["totpop"]
        hits = []
        if fp and fp in by_fips:
          hits = by_fips[fp]
        elif (st, nm) in by_st_nm:
          hits = by_st_nm[(st, nm)]
        elif "-" in nm:
          parts = [p.strip() for p in nm.split("-") if p.strip()]
          for p in parts:
            hits.extend(by_st_nm.get((st, p), []))
        if not hits and (st, nm) in US_NAME_ALIASES:
          for a_st, a_nm in US_NAME_ALIASES[(st, nm)]:
            hits.extend(by_st_nm.get((a_st, a_nm), []))
        hits = sorted(set(hits))
        if hits:
          matched_census += pop
          w_sum = sum(items[h]["geom_area_km2"] for h in hits)
          for h in hits:
            frac = items[h]["geom_area_km2"] / max(1.0, w_sum)
            items[h]["census_pop"] += pop * frac
            matched_by_st.setdefault(items[h]["st"], set()).add(h)
        else:
          unmatched_by_st[st] = unmatched_by_st.get(st, 0.0) + pop

      # Distribute tiny <2% unmatched remainder proportionally within same state so 100% census pop is conserved
      for st, rem_pop in unmatched_by_st.items():
        cands = sorted(matched_by_st.get(st, set()))
        if not cands:
          cands = [it["poly_idx"] for it in items if it["st"] == st]
        if cands:
          cur_s = sum(items[c]["census_pop"] for c in cands)
          if cur_s > 0:
            for c in cands:
              items[c]["census_pop"] *= (cur_s + rem_pop) / cur_s
          else:
            a_s = sum(items[c]["geom_area_km2"] for c in cands)
            for c in cands:
              items[c]["census_pop"] += rem_pop * (items[c]["geom_area_km2"] / max(1.0, a_s))

      # Restrict to counties receiving census pop > 0 (leaving empty unenumerated frontier counties in Regime 2!)
      kept = [it for it in items if it["census_pop"] > 0]
      return kept, {"matched_pct": 100.0 * matched_census / max(1.0, tot_census), "census_sum": tot_census, "kept_sum": sum(x["census_pop"] for x in kept)}

    # Colonial America (1700-1780): combine 1790 county descendant weights + active settlements + HYDE + age maturity
    hyde_grid = build_hyde_rur_lookup(root, yr)
    # Build pixel mask over temporary colonial items to integrate HYDE + settlements + 1790 pop
    for idx_k, it in enumerate(items):
      it["grid_id"] = idx_k + 1
    c_arr, c_stats = draw_polygons_to_mask(items, domain_valid, area_grid)

    # Precompute per-polygon settlement sum & HYDE rur sum & 1790 overlay sum
    sett_sum = np.zeros(len(items) + 1, dtype=np.float64)
    for s in doc_setts:
      coords = s.get("coords")
      if not isinstance(coords, list) or len(coords) < 2:
        continue
      # Interpolate series roughly
      pop_s = 0.0
      pts = s.get("series") or []
      for i_p in range(len(pts)):
        if pts[i_p][0] == yr:
          pop_s = pts[i_p][1]
          break
        if i_p + 1 < len(pts) and pts[i_p][0] <= yr <= pts[i_p + 1][0]:
          span = max(1, pts[i_p + 1][0] - pts[i_p][0])
          t = (yr - pts[i_p][0]) / span
          pop_s = (1 - t) * pts[i_p][1] + t * pts[i_p + 1][1]
          break
      if pop_s <= 0:
        continue
      r_px = min(GRID_H - 1, max(0, int((90.0 - coords[0]) * GRID_H / 180.0)))
      c_px = min(GRID_W - 1, max(0, int((coords[1] + 180.0) * GRID_W / 360.0)))
      gid = int(c_arr[r_px, c_px])
      if gid > 0:
        sett_sum[gid] += pop_s

    hyde_sum = np.zeros(len(items) + 1, dtype=np.float64)
    if hyde_grid is not None:
      nz = c_arr > 0
      np.add.at(hyde_sum, c_arr[nz], hyde_grid[nz])

    desc_1790_sum = np.zeros(len(items) + 1, dtype=np.float64)
    if us_1790_grid is not None and us_1790_meta is not None:
      # Convert 1790 pixel cell density (~pop/pixel) onto colonial footprints
      pop90_px = np.zeros((GRID_H, GRID_W), dtype=np.float64)
      px_cnt90 = {}
      for gid90, m90 in us_1790_meta.items():
        if m90["country"] == "US" and m90["pixel_count"] > 0:
          px_cnt90[gid90] = m90["census_pop"] / m90["pixel_count"]
      nz90 = us_1790_grid > 0
      # Fast vector map via array lookup
      max_id90 = max(px_cnt90.keys(), default=0) + 1
      lut90 = np.zeros(max_id90, dtype=np.float64)
      for g90, val90 in px_cnt90.items():
        lut90[g90] = val90
      m_both = (c_arr > 0) & (us_1790_grid > 0) & (us_1790_grid < max_id90)
      np.add.at(desc_1790_sum, c_arr[m_both], lut90[us_1790_grid[m_both]])

    # Group by colony benchmark key and conserve exactly to canonical colonial total!
    col_dict = col1_j5 if yr <= 1750 else col2_j5
    by_col = {}
    for k, it in enumerate(items):
      ckey = US_COLONY_KEY_BY_ST.get(it["st"])
      if not ckey or ckey not in col_dict:
        continue
      # Map Virginia West-of-Allegheny vs VA; keep ME with MA as in canonical manifest
      by_col.setdefault(ckey, []).append(k)

    kept = []
    for ckey, k_list in by_col.items():
      target_pop = interp_region(col_dict, ckey, yr)
      if target_pop <= 0:
        continue
      raw_w = []
      sum_h = sum(hyde_sum[k + 1] for k in k_list) + 1e-6
      sum_s = sum(sett_sum[k + 1] for k in k_list) + 1e-6
      sum_d = sum(desc_1790_sum[k + 1] / (1.0 + items[k]["geom_area_km2"] / 6000.0) for k in k_list) + 1e-6
      sum_a = sum(items[k]["geom_area_km2"] for k in k_list) + 1e-6
      for k in k_list:
        area_k = items[k]["geom_area_km2"]
        age = max(2.0, float(yr - items[k]["founded_year"] + 5))
        age_f = min(1.0, math.pow(age / 45.0, 0.70))
        giant_pen = (1.0 / (1.0 + max(0.0, area_k - 8000.0) / 25000.0)) if yr <= 1770 else 1.0
        d_term = (desc_1790_sum[k + 1] / (1.0 + area_k / 6000.0)) / sum_d
        w = (
          0.52 * (hyde_sum[k + 1] / sum_h)
          + 0.23 * d_term
          + 0.20 * (sett_sum[k + 1] / sum_s)
          + 0.05 * (area_k / sum_a)
        ) * age_f * giant_pen
        raw_w.append(max(1e-6, w))
      w_tot = sum(raw_w)
      for idx_sub, k in enumerate(k_list):
        it = items[k]
        it["census_pop"] = target_pop * raw_w[idx_sub] / w_tot
        if it["census_pop"] > 0:
          kept.append(it)
    return kept, {"matched_pct": 100.0, "census_sum": sum(x["census_pop"] for x in kept), "kept_sum": sum(x["census_pop"] for x in kept)}

  # 4. Load Canadian GeoJSONs & Historical Tables
  gj51 = json.loads((raw_dir / "ca_cd_1851.geojson").read_text(encoding="utf-8"))
  gj61 = json.loads((raw_dir / "ca_cd_1861.geojson").read_text(encoding="utf-8"))
  gj71 = json.loads((raw_dir / "ca_cd_1871.geojson").read_text(encoding="utf-8"))
  gj_nl = json.loads((centaur_dir / "_shared/census_ingest/raw_sources/statcan_2021_cd.geojson").read_text(encoding="utf-8"))

  def extract_gj_polys(gj_obj, pr_filter, exclude_gids=None):
    out = []
    for f in gj_obj["features"]:
      props = f["properties"]
      gid = str(props.get("geosid") or props.get("CDUID") or "")
      if exclude_gids and gid in exclude_gids:
        continue
      pr = gid[:2] if pr_filter != "NL" else "NL"
      if pr_filter and pr_filter != "NL" and not gid.startswith(pr_filter):
        continue
      if pr_filter == "NL" and str(props.get("PRUID")) != "10":
        continue
      geom = f["geometry"]
      rings = []
      if geom["type"] == "Polygon":
        rings.append(geom["coordinates"][0])
      elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
          rings.append(poly[0])
      if not rings:
        continue
      all_x = [pt[0] for r in rings for pt in r]
      all_y = [pt[1] for r in rings for pt in r]
      area_km2 = float(props.get("areakm") or props.get("LANDAREA") or 1000.0)
      out.append({
        "geosid": gid,
        "pr": pr,
        "geoname": str(props.get("geoname") or props.get("CDNAME") or gid),
        "area_km2": max(1.0, area_km2),
        "lon_c": float(props.get("lon_c") or (0.5 * (min(all_x) + max(all_x)))),
        "lat_c": float(props.get("lat_c") or (0.5 * (min(all_y) + max(all_y)))),
        "rings": rings,
      })
    return out

  def load_ca_tab_pop(fn, sep="\t"):
    df = pd.read_csv(raw_dir / fn, sep=sep, encoding="latin1", low_memory=False)
    pop_c = next((c for c in df.columns if c.lower().startswith("pop_xx") or c.lower() == "population"), df.columns[1])
    out = {}
    for _, row in df.iterrows():
      nm = str(row.iloc[0]).strip()
      if "total" in nm.lower() or not nm or nm == "nan":
        continue
      val = pd.to_numeric(str(row[pop_c]).replace(",", ""), errors="coerce")
      if pd.notna(val) and val > 0:
        out[norm_county_name(nm)] = out.get(norm_county_name(nm), 0.0) + float(val)
    return out

  # Preload 1851, 1861, 1871 CHGIS tables
  df_ca51 = pd.read_csv(raw_dir / "ca_tcp_1851_cd.tab", sep="\t", encoding="latin1", low_memory=False)
  df_ca51["pop"] = pd.to_numeric(df_ca51["POP_XX_N"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
  ca51_by_uid = dict(zip(df_ca51["TCPUID_CD_1851"], df_ca51["pop"]))

  df_ca61 = pd.read_csv(raw_dir / "ca_tcp_1861_cd.tab", sep="\t", encoding="latin1", low_memory=False)
  df_ca61["pop"] = pd.to_numeric(df_ca61["POP_XX_N"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
  ca61_by_key = {(str(r["PR"]), norm_county_name(r["NAME_CD_1861"])): float(r["pop"]) for _, r in df_ca61.iterrows()}
  ca61_by_uid = {}
  for _, r in df_ca61.iterrows():
    uid = str(r["TCPUID_CD_1861"])
    pr = str(r["PR"])
    if uid.startswith("QC") and pr == "ON":
      uid = "ON" + uid[2:]
    ca61_by_uid[uid] = float(r["pop"])

  df_ca71 = pd.read_csv(raw_dir / "ca_tcp_1871_cd.csv", encoding="latin1", low_memory=False)
  df_ca71["pop"] = pd.to_numeric(df_ca71["POP_XX_N"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
  ca71_by_uid = dict(zip(df_ca71["TCPUID_CD_1871"], df_ca71["pop"]))

  df_pe71 = pd.read_csv(raw_dir / "ca_tcp_1871_pe_cd.tab", sep="\t", encoding="latin1", low_memory=False)
  df_pe71["pop"] = pd.to_numeric(df_pe71["POP_XX_N"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
  pe71_by_name = {}
  for _, r in df_pe71.iterrows():
    nm = norm_county_name(r["NAME_COUNTY_1871"])
    pe71_by_name[nm] = pe71_by_name.get(nm, 0.0) + float(r["pop"])

  # Pre-1851 Maritime & Ontario/Quebec historical Borealis county weights
  nb_1824 = load_ca_tab_pop("ca_nb_1824.tab")
  nb_1834 = load_ca_tab_pop("ca_nb_hist.tab")
  nb_1851 = load_ca_tab_pop("ca_nb_hist2.tab")
  nb_1861 = load_ca_tab_pop("ca_nb_1861.tab")
  ns_1851 = load_ca_tab_pop("ca_ns_hist2.tab")
  ns_1861 = load_ca_tab_pop("ca_ns_hist.csv", ",")
  lc_1844 = load_ca_tab_pop("ca_lc_1844.tab")
  lc_1831 = load_ca_tab_pop("ca_lc_1831.tab")
  uc_1828 = load_ca_tab_pop("ca_uc_1828.tab")
  pe_1841 = load_ca_tab_pop("ca_pe_1841.tab")

  def fold_city_pops(src_map, fold_pairs):
    out = dict(src_map)
    for city_k, par_k in fold_pairs:
      if city_k in out:
        out[par_k] = out.get(par_k, 0.0) + out.pop(city_k)
    return out

  nb_1824 = fold_city_pops(nb_1824, [("ST JOHN CITY", "ST JOHN"), ("STJOHN", "ST JOHN"), ("FREDERICTON", "YORK")])
  nb_1834 = fold_city_pops(nb_1834, [("ST JOHN CITY", "ST JOHN"), ("ST JOHN", "ST JOHN"), ("FREDERICTON", "YORK")])
  nb_1851 = fold_city_pops(nb_1851, [("STJOHN", "ST JOHN"), ("FREDERICTON", "YORK")])
  nb_1861 = fold_city_pops(nb_1861, [("FREDERICTON", "YORK")])
  # Fix normalized NS names for 1851/1861 (`Halifax West` + `Halifax East` share Halifax+City 1851/1861)
  ns_1851 = fold_city_pops(ns_1851, [("SHELBORNE", "SHELBURNE")])
  ns_1861 = fold_city_pops(ns_1861, [("SHELBORNE", "SHELBURNE")])

  # Static base polygon sets for Canada
  ca_qc51 = extract_gj_polys(gj51, "QC")
  ca_on51 = extract_gj_polys(gj51, "ON")
  ca_qc61 = extract_gj_polys(gj61, "QC")
  ca_on61 = extract_gj_polys(gj61, "ON")
  ca_71_all = extract_gj_polys(gj71, None, exclude_gids={"BC999", "MB999", "NL998", "NT999"})
  ca_nb71 = [p for p in ca_71_all if p["pr"] == "NB"]
  ca_ns71 = [p for p in ca_71_all if p["pr"] == "NS"]
  ca_pe71 = [p for p in ca_71_all if p["pr"] == "PE"]
  ca_nl_island = [p for p in extract_gj_polys(gj_nl, "NL") if p["geosid"] not in ("1010", "1011")]

  # NL island division regional weights (Avalon/1001 dominant, Bonavista/Trinity 1007, Burin 1002, etc.)
  NL_WEIGHTS = {"1001": 0.56, "1002": 0.10, "1003": 0.06, "1004": 0.03, "1005": 0.03, "1006": 0.02, "1007": 0.11, "1008": 0.07, "1009": 0.02}

  def build_canada_snapshot_items(yr):
    items = []
    # Determine provincial benchmark targets from canonical CENTAUR manifests
    if yr <= 1760:
      tgt_qc = interp_region(cc1_j5, "cc1_new_france_st_lawrence", yr)
      # Acadia + Nova Scotia split roughly 65% NS / 35% NB+PEI (Bay of Fundy Chignecto)
      tgt_acadia = interp_region(cc1_j5, "cc1_acadia_nova_scotia_ile_royale", yr)
      tgt_ns = 0.72 * tgt_acadia
      tgt_nb = 0.22 * tgt_acadia
      tgt_pe = 0.06 * tgt_acadia
      tgt_on = 600.0 if yr <= 1740 else (1800.0 if yr == 1750 else 3200.0) # Detroit/Assumption + Fort Frontenac/Niagara enclaves only
      tgt_nl = 0.92 * interp_region(cc1_j5, "cc1_newfoundland_labrador_st_pierre", yr)
    elif yr <= 1860:
      tgt_qc = interp_region(cc2_j5, "cc2_lower_canada_quebec", yr)
      tgt_on = interp_region(cc2_j5, "cc2_upper_canada_ontario", yr)
      tgt_ns = interp_region(cc2_j5, "cc2_nova_scotia", yr)
      tgt_nb = interp_region(cc2_j5, "cc2_new_brunswick", yr)
      tgt_pe = interp_region(cc2_j5, "cc2_prince_edward_island", yr)
      tgt_nl = 0.93 * interp_region(cc2_j5, "cc2_newfoundland_labrador", yr)
    else:
      tgt_qc = interp_region(ca_j5, "can_quebec", yr)
      tgt_on = interp_region(ca_j5, "can_ontario", yr)
      tgt_ns = interp_region(ca_j5, "can_nova_scotia", yr)
      tgt_nb = interp_region(ca_j5, "can_new_brunswick", yr)
      tgt_pe = interp_region(ca_j5, "can_prince_edward_island", yr)
      tgt_nl = 0.94 * interp_region(ca_j5, "can_newfoundland_and_labrador", yr)

    def add_ca_province(polys, pr_code, raw_pops, target_total, admin1_key):
      raw_sum = sum(raw_pops)
      if raw_sum <= 0 or target_total <= 0:
        return
      sc = target_total / raw_sum
      for p, rp in zip(polys, raw_pops):
        if rp <= 0:
          continue
        founded = CA_FOUNDED_OVERRIDE.get((pr_code, p["geoname"]), 1700 if pr_code == "QC" else 1785)
        items.append({
          "name": f"{p['geoname']} ({pr_code})",
          "admin1": admin1_key,
          "st": pr_code,
          "country": "CA",
          "country_code": 2,
          "fips_or_uid": p["geosid"],
          "geom_area_km2": p["area_km2"],
          "lon_c": p["lon_c"],
          "lat_c": p["lat_c"],
          "rings": p["rings"],
          "census_pop": rp * sc,
          "founded_year": founded,
        })

    # Choose QC & ON polygons + weights by epoch
    if yr <= 1780:
      # Strict St. Lawrence seigneurial corridor in QC; Detroit/Kingston enclaves in ON
      qc_w = []
      for p in ca_qc51:
        fnd = CA_FOUNDED_OVERRIDE.get(("QC", p["geoname"]), 1700)
        if yr < fnd:
          qc_w.append(0.0)
        else:
          base = QC_SEIGNEURY_1700_WEIGHTS.get(p["geoname"], ca51_by_uid.get(p["geosid"], 0.0) * 0.15)
          qc_w.append(base)
      add_ca_province(ca_qc51, "QC", qc_w, tgt_qc, "can_quebec")
      on_w = [1.0 if p["geoname"] == "Essex" else (0.45 if yr >= 1760 and p["geoname"] == "Frontenac" else 0.0) for p in ca_on51]
      add_ca_province(ca_on51, "ON", on_w, tgt_on, "can_ontario")
    elif yr < 1850:
      # Lower Canada progressive historical counties anchored to 1831/1844/1851 Borealis tables
      lc_ref = lc_1831 if yr <= 1835 else lc_1844
      qc_w = []
      for p in ca_qc51:
        fnd = CA_FOUNDED_OVERRIDE.get(("QC", p["geoname"]), 1700)
        if yr < fnd:
          qc_w.append(0.0)
          continue
        age_f = min(1.0, max(0.08, (yr - fnd + 5) / 30.0))
        nm = norm_county_name(p["geoname"])
        val51 = ca51_by_uid.get(p["geosid"], 0.0)
        val_ref = lc_ref.get(nm, val51 * (0.45 if yr <= 1835 else 0.72))
        qc_w.append(max(1.0, val_ref) * age_f)
      add_ca_province(ca_qc51, "QC", qc_w, tgt_qc, "can_quebec")

      # Upper Canada progressive Loyalists -> 1828 -> 1851
      on_w = []
      for p in ca_on51:
        fnd = CA_FOUNDED_OVERRIDE.get(("ON", p["geoname"]), 1785)
        if yr < fnd:
          on_w.append(0.0)
          continue
        age_f = min(1.0, max(0.10, (yr - fnd + 5) / 25.0))
        nm = norm_county_name(p["geoname"])
        val51 = ca51_by_uid.get(p["geosid"], 0.0)
        if yr <= 1835:
          val = uc_1828.get(nm, val51 * 0.12)
        else:
          val = 0.35 * uc_1828.get(nm, val51 * 0.25) + 0.65 * val51
        on_w.append(max(1.0, val) * age_f)
      add_ca_province(ca_on51, "ON", on_w, tgt_on, "can_ontario")
    elif yr == 1850:
      add_ca_province(ca_qc51, "QC", [ca51_by_uid.get(p["geosid"], 0.0) for p in ca_qc51], tgt_qc, "can_quebec")
      add_ca_province(ca_on51, "ON", [ca51_by_uid.get(p["geosid"], 0.0) for p in ca_on51], tgt_on, "can_ontario")
    elif yr == 1860:
      add_ca_province(ca_qc61, "QC", [ca61_by_uid.get(p["geosid"], ca61_by_key.get(("QC", norm_county_name(p["geoname"])), 0.0)) for p in ca_qc61], tgt_qc, "can_quebec")
      add_ca_province(ca_on61, "ON", [ca61_by_uid.get(p["geosid"], ca61_by_key.get(("ON", norm_county_name(p["geoname"])), 0.0)) for p in ca_on61], tgt_on, "can_ontario")
    else: # 1870
      qc71 = [p for p in ca_71_all if p["pr"] == "QC"]
      on71 = [p for p in ca_71_all if p["pr"] == "ON"]
      add_ca_province(qc71, "QC", [ca71_by_uid.get(p["geosid"], 0.0) for p in qc71], tgt_qc, "can_quebec")
      add_ca_province(on71, "ON", [ca71_by_uid.get(p["geosid"], 0.0) for p in on71], tgt_on, "can_ontario")

    # Nova Scotia, New Brunswick, PEI across 1700-1870 on cd_1871 county geometries
    nb_ref = nb_1824 if yr <= 1830 else (nb_1834 if yr <= 1840 else (nb_1851 if yr <= 1855 else nb_1861))
    ns_ref = ns_1851 if yr <= 1855 else ns_1861
    nb_w, ns_w, pe_w = [], [], []
    for p in ca_nb71:
      fnd = CA_FOUNDED_OVERRIDE.get(("NB", p["geoname"]), 1783)
      if yr < fnd:
        nb_w.append(0.0)
      else:
        nm = norm_county_name(p["geoname"])
        val = ca71_by_uid.get(p["geosid"], 0.0) if yr >= 1870 else nb_ref.get(nm, ca71_by_uid.get(p["geosid"], 5000.0) * 0.45)
        if p["geoname"] == "St. John" and "ST JOHN" not in nb_ref and yr < 1870:
          val = nb_ref.get("ST JOHN", 0.0) + nb_ref.get("STJOHN", 0.0)
        age_f = 1.0 if yr >= 1840 else min(1.0, max(0.15, (yr - fnd + 8) / 25.0))
        nb_w.append(max(1.0, val) * age_f)
    add_ca_province(ca_nb71, "NB", nb_w, tgt_nb, "can_new_brunswick")

    for p in ca_ns71:
      fnd = CA_FOUNDED_OVERRIDE.get(("NS", p["geoname"]), 1760)
      if yr < fnd:
        ns_w.append(0.0)
      else:
        nm = norm_county_name(p["geoname"])
        if yr >= 1870:
          val = ca71_by_uid.get(p["geosid"], 0.0)
        elif nm.startswith("HALIFAX"):
          tot_hx = ns_ref.get("HALIFAX", 35000.0)
          val = tot_hx * (0.72 if "WEST" in nm else 0.28)
        else:
          val = ns_ref.get(nm, ca71_by_uid.get(p["geosid"], 5000.0) * 0.6)
        age_f = 1.0 if yr >= 1830 else min(1.0, max(0.15, (yr - fnd + 8) / 25.0))
        ns_w.append(max(1.0, val) * age_f)
    add_ca_province(ca_ns71, "NS", ns_w, tgt_ns, "can_nova_scotia")

    for p in ca_pe71:
      fnd = CA_FOUNDED_OVERRIDE.get(("PE", p["geoname"]), 1750)
      if yr < fnd:
        pe_w.append(0.0)
      else:
        nm = norm_county_name(p["geoname"])
        val = pe71_by_name.get(nm, 25000.0)
        age_f = 1.0 if yr >= 1810 else min(1.0, max(0.20, (yr - fnd + 10) / 25.0))
        pe_w.append(max(1.0, val) * age_f)
    add_ca_province(ca_pe71, "PE", pe_w, tgt_pe, "can_prince_edward_island")

    # Newfoundland settled island divisions (1700: 1001/1007 Avalon-Trinity -> progressively West/South coasts)
    nl_w = []
    for p in ca_nl_island:
      gid = p["geosid"]
      if yr <= 1750 and gid not in ("1001", "1002", "1007"):
        nl_w.append(0.0)
      elif yr <= 1790 and gid in ("1004", "1005", "1006"):
        nl_w.append(0.0)
      else:
        nl_w.append(NL_WEIGHTS.get(gid, 0.02))
    add_ca_province(ca_nl_island, "NL", nl_w, tgt_nl, "can_newfoundland_and_labrador")

    return items

  # Note: fix 1850 branch duplication inside build_canada_snapshot_items (`yr == 1850` handled after `<= 1850`)
  # Build 1790 US FIRST so colonial 1700-1780 can inherit exact 1790 descendant polygon populations!
  print("Building 1790 US anchor first...")
  items_1790, audit_1790 = build_us_snapshot_items(1790)
  for k, it in enumerate(items_1790):
    it["grid_id"] = k + 1
  grid_1790, stats_1790 = draw_polygons_to_mask(items_1790, domain_valid, area_grid)
  meta_1790 = {}
  for it in items_1790:
    gid = it["grid_id"]
    px_cnt, area_px = stats_1790.get(gid, (0, it["geom_area_km2"]))
    meta_1790[gid] = {**it, "pixel_count": px_cnt, "area_km2": area_px}
  print(f"  US 1790 anchor: {len(items_1790)} counties, matched={audit_1790['matched_pct']:.2f}%, pop={audit_1790['kept_sum']:.0f}")

  # Generate all 18 snapshots cleanly (1700..1870)
  audit_summary = {}
  for yr in DECENNIAL_YEARS:
    us_items, us_audit = build_us_snapshot_items(yr, grid_1790, meta_1790)
    ca_items = build_canada_snapshot_items(yr)
    # Prevent 1850 QC/ON duplicate if `yr <= 1850` wasn't skipped: fix by filtering unique (country, fips_or_uid)
    combined = []
    seen_ca = set()
    for it in us_items:
      combined.append(it)
    for it in ca_items:
      if yr == 1850 and it["st"] in ("QC", "ON"):
        # keep only exact 1851 CHGIS pass (second one or check unique): let's overwrite cleanly!
        pass
      combined.append(it)

    if yr == 1850:
      # Fix 1850 cleanly: drop the pre-1850 loop's QC/ON items by deduplicating keeping LAST occurrence per (st, fips_or_uid)
      dedup_ca = {}
      for it in ca_items:
        dedup_ca[(it["st"], it["fips_or_uid"])] = it
      combined = us_items + list(dedup_ca.values())

    for k, it in enumerate(combined):
      it["grid_id"] = k + 1

    id_grid, px_stats = draw_polygons_to_mask(combined, domain_valid, area_grid)

    # Encode 16-bit county id in (R, G), B = country_code (1=US, 2=CA), A = 255 for enumerated cells
    out_rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
    cc_lut = np.zeros(len(combined) + 1, dtype=np.uint8)
    for it in combined:
      cc_lut[it["grid_id"]] = it["country_code"]
    nz = id_grid > 0
    gids_nz = id_grid[nz]
    out_rgba[nz, 0] = (gids_nz >> 8) & 0xFF
    out_rgba[nz, 1] = gids_nz & 0xFF
    out_rgba[nz, 2] = cc_lut[gids_nz]
    out_rgba[nz, 3] = 255
    Image.fromarray(out_rgba, mode="RGBA").save(out_dir / f"county_id_{yr}.png", compress_level=6)

    meta_counties = {}
    us_tot = ca_tot = 0.0
    giant_cnt = 0
    for it in combined:
      gid = it["grid_id"]
      px_cnt, raster_area = px_stats.get(gid, (0, it["geom_area_km2"]))
      eff_area = max(raster_area, it["geom_area_km2"])
      dens = it["census_pop"] / max(1.0, eff_area)
      is_giant = (
        (eff_area > 15000.0 and dens < 2.2)
        or (it["country"] == "CA" and eff_area > 15000.0 and it["st"] in ("QC", "ON"))
        or (it["country"] == "US" and yr <= 1780 and it["name"].startswith("Augusta") and eff_area > 15000.0)
      )
      if is_giant:
        giant_cnt += 1
      if it["country"] == "US":
        us_tot += it["census_pop"]
      else:
        ca_tot += it["census_pop"]
      meta_counties[str(gid)] = {
        "id": gid,
        "name": it["name"],
        "admin1": it["admin1"],
        "country": it["country"],
        "fips_or_uid": it["fips_or_uid"],
        "census_pop": round(it["census_pop"], 2),
        "area_km2": round(eff_area, 1),
        "density_per_km2": round(dens, 4),
        "pixel_count": px_cnt,
        "is_giant_frontier": bool(is_giant),
        "founded_year": it["founded_year"],
      }

    meta_obj = {
      "year": yr,
      "us_matched_pct": round(us_audit["matched_pct"], 2),
      "us_counties": sum(1 for x in combined if x["country"] == "US"),
      "ca_counties": sum(1 for x in combined if x["country"] == "CA"),
      "giant_frontier_counties": giant_cnt,
      "us_pop_total": round(us_tot),
      "ca_pop_total": round(ca_tot),
      "counties": meta_counties,
    }
    (out_dir / f"county_meta_{yr}.json").write_text(json.dumps(meta_obj), encoding="utf-8")
    audit_summary[yr] = {k: v for k, v in meta_obj.items() if k != "counties"}
    print(f"yr={yr}: US={meta_obj['us_counties']}c ({us_tot:,.0f}, {us_audit['matched_pct']:.1f}%) | CA={meta_obj['ca_counties']}c ({ca_tot:,.0f}) | giant={giant_cnt}")

  (out_dir.parent / "county_census_audit_summary.json").write_text(json.dumps(audit_summary, indent=2), encoding="utf-8")
  print("DONE: generated all 18 decennial county_id_<yr>.png + county_meta_<yr>.json rasters.")


if __name__ == "__main__":
  run_build()
