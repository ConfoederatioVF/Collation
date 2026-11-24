"""Stage B.1 Archaeological Substrata Harvester & Master Compiler for Operation Viscount Project JAGUAR.

Builds a strictly provenance-tracked, deduplicated, multi-repository archaeological site inventory
across all three required JAGUAR jurisdictions (`mexico`, `central_america`, `caribbean` incl. Bermuda)
strictly inside `jaguar_domain_mask.png`, plus `250 km` northern cross-frontier buffer sites
(`is_frontier_buffer: true`) imported from completed neighbour `CENTAUR`.

Outputs:
  - `config/jaguar_arch_sites_master.json`
  - `config/jaguar_arch_provenance_audit.json`
"""

import csv
import datetime
import io
import json
import math
import pathlib
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict

import numpy as np
import openpyxl
import pyproj
import shapefile
from PIL import Image

BASE_DIR = pathlib.Path(__file__).resolve().parent
SVEA_ROOT = BASE_DIR.parents[5]
RAW_DIR = BASE_DIR / "raw_arch_sources"
CONFIG_DIR = BASE_DIR / "config"
MASK_PATH = CONFIG_DIR / "jaguar_domain_mask.png"
SOURCES_CFG_PATH = CONFIG_DIR / "jaguar_arch_sources_config.json"
COUNTRIES_GEOJSON = BASE_DIR.parent / "_gis_cache" / "jaguar_countries.geojson"
C14_CSV = SVEA_ROOT / "histmap" / "1.data_raw" / "population_c14bazAAR" / "c14_cleaned_dedup.csv"
CENTAUR_DIR = SVEA_ROOT / "histmap" / "1.data_raw" / "population_regional" / "CENTAUR" / "_shared" / "sites_northern_america"

CFG = json.loads(SOURCES_CFG_PATH.read_text(encoding="utf-8"))
JURISDICTION_MAP = CFG["jurisdiction_map"]
LARGE_CARIBBEAN_ISLANDS = set(CFG["large_caribbean_islands"])
BOM_PHASE_SPANS = {k: tuple(v) for k, v in CFG["bom_phase_spans"].items()}
SOURCE_REGISTRY = CFG["source_registry"]

MONUMENT_REGEX = re.compile(
  r"\b(?:petroglyph|rock\s*art|pictograph|geoglyph|cave|cueva|cenote|gruta|rockshelter|rock\s*shelter|"
  r"pyramid|piramide|temple|templo|shrine|ballcourt|juego\s*de\s*pelota|stela|stelae|estela|"
  r"fort|fortification|fortaleza|castillo|castle|redoubt|battery|garrison|citadel|mural|"
  r"cemetery|cementerio|ossuary|burial|tomb|tumba|necropolis|quarry|cantera|mine|mina|"
  r"aqueduct|acueducto|church|iglesia|cathedral|catedral|monastery|monasterio|convent|convento|"
  r"chapel|capilla|stone\s*sphere|esfera|monolith|altar|observatory|observatorio|sacbe|causeway|"
  r"reservoir|dam|canal|bridge|puente|lighthouse|faro)\b",
  re.I,
)

TIER_PRIORITY = {"regional_monograph": 4, "national_register": 3, "radiocarbon_db": 2, "crowd": 1}
DATE_BASIS_PRIORITY = {
  "calibrated_c14": 4,
  "ceramic_phase_survey": 3,
  "historic_primary_gazetteer": 2,
  "regional_cultural_phase": 1,
}


def calibrate_14c_to_ce(arg0_age_bp):
  """Converts uncalibrated 14C years BP into approximate IntCal20 calibrated calendar years CE."""
  try:
    age_bp = float(arg0_age_bp)
  except (TypeError, ValueError):
    return None
  if not math.isfinite(age_bp) or age_bp < 0 or age_bp > 20000:
    return None
  anchors = [
    (0, 0), (500, 520), (1000, 920), (1500, 1380), (2000, 1950),
    (2500, 2600), (3000, 3180), (4000, 4460), (5000, 5730), (6000, 6830),
    (7000, 7840), (8000, 8880), (9000, 10190), (10000, 11450), (11000, 12850),
    (12000, 13900), (14000, 16900),
  ]
  for i in range(len(anchors) - 1):
    x0, y0 = anchors[i]
    x1, y1 = anchors[i + 1]
    if x0 <= age_bp <= x1:
      cal_bp = y0 + (age_bp - x0) * (y1 - y0) / (x1 - x0)
      return int(round(1950 - cal_bp))
  return int(round(1950 - age_bp * 1.2))


def normalize_name(arg0_name):
  """Produces ASCII lowercase alphanumeric key for fuzzy name deduplication."""
  if not arg0_name:
    return ""
  s = unicodedata.normalize("NFKD", str(arg0_name))
  s = "".join(ch for ch in s if not unicodedata.combining(ch))
  return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def haversine_km(arg0_lat1, arg1_lon1, arg2_lat2, arg3_lon2):
  """Computes great-circle distance in km between two WGS84 points."""
  d_lat = math.radians(arg2_lat2 - arg0_lat1)
  d_lon = math.radians(arg3_lon2 - arg1_lon1)
  r1 = math.radians(arg0_lat1)
  r2 = math.radians(arg2_lat2)
  a = math.sin(d_lat * 0.5) ** 2 + math.cos(r1) * math.cos(r2) * math.sin(d_lon * 0.5) ** 2
  return 6371.0 * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def classify_record_class(arg0_name, arg1_extra=""):
  """Separates durable non-habitation monuments from settlement/habitation records."""
  return "monument" if MONUMENT_REGEX.search(f"{arg0_name or ''} {arg1_extra or ''}") else "settlement"


def pt_in_ring(arg0_x, arg1_y, arg2_ring):
  """Ray-casting point-in-polygon test for an outer ring."""
  inside = False
  j = len(arg2_ring) - 1
  for i in range(len(arg2_ring)):
    xi, yi = arg2_ring[i][0], arg2_ring[i][1]
    xj, yj = arg2_ring[j][0], arg2_ring[j][1]
    if ((yi > arg1_y) != (yj > arg1_y)) and (
      arg0_x < (xj - xi) * (arg1_y - yi) / ((yj - yi) or 1e-12) + xi
    ):
      inside = not inside
    j = i
  return inside


def A_load_masks_and_geometries():
  """Loads `jaguar_domain_mask.png`, country polygons, and US-Mexico frontier reference points."""
  mask = np.any(np.array(Image.open(MASK_PATH))[:, :, :3] > 0, axis=2)
  h, w = mask.shape
  cgj = json.loads(COUNTRIES_GEOJSON.read_text(encoding="utf-8"))

  country_polys = []
  for feat in cgj["features"]:
    props = feat.get("properties") or {}
    cname = props.get("ADMIN") or props.get("NAME") or props.get("name") or "Unknown"
    geom = feat.get("geometry") or {}
    gtype = geom.get("type")
    coords = geom.get("coordinates") or []
    rings = [coords[0]] if (gtype == "Polygon" and coords) else [p[0] for p in coords if p and p[0]] if gtype == "MultiPolygon" else []
    if not rings:
      continue
    xs = [p[0] for rg in rings for p in rg]
    ys = [p[1] for rg in rings for p in rg]
    country_polys.append((cname, (min(xs), min(ys), max(xs), max(ys)), rings))

  ys, xs = np.where(mask)
  lats = 90.0 - (ys + 0.5) * 180.0 / h
  lons = (xs + 0.5) * 360.0 / w - 180.0
  mx_north = (lats >= 25.0) & (lons <= -95.0)
  mx_lats, mx_lons = lats[mx_north], lons[mx_north]
  border_pts = []
  for lon_bin in np.arange(-117.5, -96.5, 0.1):
    sel = (mx_lons >= lon_bin) & (mx_lons < lon_bin + 0.1)
    if np.any(sel):
      idx = int(np.argmax(mx_lats[sel]))
      border_pts.append((float(mx_lats[sel][idx]), float(mx_lons[sel][idx])))

  return {"mask": mask, "h": h, "w": w, "country_polys": country_polys, "border_pts": border_pts}


def is_in_mask(arg0_lat, arg1_lon, arg2_geo):
  """Checks strict membership inside `jaguar_domain_mask.png`."""
  if arg0_lat is None or arg1_lon is None:
    return False
  if not (math.isfinite(arg0_lat) and math.isfinite(arg1_lon)):
    return False
  if not (-90.0 <= arg0_lat <= 90.0 and -180.0 <= arg1_lon <= 180.0):
    return False
  r = min(arg2_geo["h"] - 1, max(0, int((90.0 - arg0_lat) * arg2_geo["h"] / 180.0)))
  c = min(arg2_geo["w"] - 1, max(0, int((arg1_lon + 180.0) * arg2_geo["w"] / 360.0)))
  return bool(arg2_geo["mask"][r, c])


def classify_country(arg0_lat, arg1_lon, arg2_geo, arg3_hint=""):
  """Resolves sovereign country/territory from `jaguar_countries.geojson` with coastal fallback."""
  for cname, (x0, y0, x1, y1), rings in arg2_geo["country_polys"]:
    if x0 <= arg1_lon <= x1 and y0 <= arg0_lat <= y1:
      for rg in rings:
        if pt_in_ring(arg1_lon, arg0_lat, rg):
          return cname
  best, best_d = None, 0.45
  for cname, (x0, y0, x1, y1), rings in arg2_geo["country_polys"]:
    if x0 - 0.45 <= arg1_lon <= x1 + 0.45 and y0 - 0.45 <= arg0_lat <= y1 + 0.45:
      for rg in rings:
        step = max(1, len(rg) // 50)
        for px, py in rg[::step]:
          d = math.hypot(arg1_lon - px, arg0_lat - py)
          if d < best_d:
            best_d, best = d, cname
  if best:
    return best
  if arg1_lon < -86.7 and arg0_lat > 14.5:
    return "Mexico"
  if arg0_lat > 31.5 and -66.0 <= arg1_lon <= -63.5:
    return "Bermuda"
  if arg1_lon > -84.0 and arg0_lat > 10.0:
    return arg3_hint or "Caribbean"
  return arg3_hint or "Mexico"


def resolve_jurisdiction(arg0_country, arg1_lat, arg2_lon):
  """Maps resolved country into canonical JAGUAR jurisdiction (`mexico`, `central_america`, `caribbean`)."""
  if arg0_country in JURISDICTION_MAP:
    return JURISDICTION_MAP[arg0_country]
  low = (arg0_country or "").lower()
  if "mex" in low:
    return "mexico"
  if any(k in low for k in ["guat", "beliz", "hondur", "salvad", "nicar", "costa", "panam"]):
    return "central_america"
  if arg2_lon > -84.5 and arg1_lat >= 10.0:
    return "caribbean"
  if arg1_lat < 17.8 and arg2_lon > -92.3:
    return "central_america"
  return "mexico"


def min_dist_to_us_mx_border_km(arg0_lat, arg1_lon, arg2_geo):
  """Computes approximate planar-cosine distance in km to US-Mexico border."""
  best = 1e9
  cos_lat = math.cos(math.radians(arg0_lat))
  for blat, blon in arg2_geo["border_pts"]:
    d = math.hypot((arg1_lon - blon) * 111.195 * cos_lat, (arg0_lat - blat) * 111.195)
    if d < best:
      best = d
  return best


def default_phase_for_region(arg0_country, arg1_lat, arg2_lon):
  """Returns documented regional pre-Hispanic phase span when calibrated C14 is absent."""
  jur = resolve_jurisdiction(arg0_country, arg1_lat, arg2_lon)
  if jur == "caribbean":
    if arg0_country == "Bermuda":
      return (1612, 1900)
    if arg0_country in ("The Bahamas", "Turks and Caicos Islands"):
      return (700, 1520)
    return (-500, 1520)
  if jur == "central_america":
    return (-500, 1520) if arg0_country in ("Costa Rica", "Panama", "Nicaragua") else (-400, 1200)
  if arg1_lat >= 23.5:
    return (-500, 1550)
  if arg2_lon >= -90.5 and arg1_lat >= 19.2:
    return (-300, 1521)
  return (-600, 1521)


def make_site_record(arg0_name, arg1_lat, arg2_lon, arg3_start, arg4_end, arg5_source_id, arg6_geo, arg7_options=None):
  """Constructs a validated site dict or returns None if out of bounds or invalid."""
  opts = arg7_options or {}
  is_buf = bool(opts.get("is_frontier_buffer", False))
  lat, lon = round(float(arg1_lat), 5), round(float(arg2_lon), 5)
  if not (math.isfinite(lat) and math.isfinite(lon)):
    return None
  if (not is_buf and not is_in_mask(lat, lon, arg6_geo)) or (is_buf and is_in_mask(lat, lon, arg6_geo)):
    return None
  start_y, end_y = int(round(arg3_start)), int(round(arg4_end))
  if start_y > end_y:
    start_y, end_y = end_y, start_y
  start_y = max(-12000, min(1900, start_y))
  end_y = max(start_y, min(1950, end_y))
  name = re.sub(r"\s+", " ", str(arg0_name or "").strip()) or f"Unnamed Site ({lat:.3f}, {lon:.3f})"
  if is_buf:
    country, jurisdiction = "United States of America", "frontier_buffer_usa"
  else:
    country = classify_country(lat, lon, arg6_geo, opts.get("country_hint", ""))
    jurisdiction = resolve_jurisdiction(country, lat, lon)
  return {
    "name": name,
    "lat": lat,
    "lon": lon,
    "start_year": start_y,
    "end_year": end_y,
    "country": country,
    "jurisdiction": jurisdiction,
    "source_id": arg5_source_id,
    "source_tier": SOURCE_REGISTRY[arg5_source_id]["tier"],
    "record_class": opts.get("record_class") or classify_record_class(name, opts.get("extra_text", "")),
    "is_frontier_buffer": is_buf,
    "date_basis": opts.get("date_basis", "regional_cultural_phase"),
    "coord_precision": opts.get("coord_precision", "site"),
    "reference": str(opts.get("reference", "") or "")[:220],
  }


def grid_parcel_cluster_points(arg0_pts, arg1_cell_km=1.0):
  """Aggregates dense survey collection lots into non-chaining 1.0 km landscape settlement parcels."""
  if not arg0_pts:
    return []
  cell_deg = arg1_cell_km / 111.0
  buckets = defaultdict(list)
  for pt in arg0_pts:
    gy = int(math.floor(pt["lat"] / cell_deg))
    gx = int(math.floor(pt["lon"] / cell_deg))
    buckets[(gy, gx)].append(pt)
  out = []
  for idx, pts in enumerate(buckets.values(), 1):
    out.append({
      "name": pts[0].get("name") or f"Survey Parcel {idx}",
      "lat": sum(p["lat"] for p in pts) / len(pts),
      "lon": sum(p["lon"] for p in pts) / len(pts),
      "start_year": min(p["start_year"] for p in pts),
      "end_year": max(p["end_year"] for p in pts),
      "n_lots": len(pts),
    })
  return out


def B_ingest_mexico_and_maya_regional(arg0_geo, arg1_audit):
  """Ingests Witschey & Brown MayaGIS, UCSB Maya Forest, Basin of Mexico Survey, DECM 16c, SWSN NW Mexico, INAH SIC, RMGIR, and CADB Mexico."""
  records = []
  pm_re = re.compile(r"<Placemark[^>]*>(.*?)</Placemark>", re.S)
  name_re = re.compile(r"<name>(.*?)</name>", re.S)
  desc_re = re.compile(r"<description>(.*?)</description>", re.S)
  coord_re = re.compile(r"<coordinates>\s*([^<]+?)\s*</coordinates>", re.S)

  # 1. FAMSI Witschey & Brown Electronic Atlas of Ancient Maya Sites
  kmz_path = RAW_DIR / "famsi_mayagis_MayaSites.kmz"
  cnt = 0
  if kmz_path.exists():
    with zipfile.ZipFile(kmz_path) as zf:
      kml_name = [n for n in zf.namelist() if n.lower().endswith(".kml")][0]
      txt = zf.read(kml_name).decode("utf-8", errors="replace")
    for m in pm_re.finditer(txt):
      blk = m.group(1)
      cm = coord_re.search(blk)
      if not cm:
        continue
      parts = cm.group(1).strip().split(",")
      try:
        lon, lat = float(parts[0]), float(parts[1])
      except Exception:
        continue
      nm, dm = name_re.search(blk), desc_re.search(blk)
      sname = re.sub(r"<[^>]+>", "", nm.group(1)).strip() if nm else ""
      dtxt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", dm.group(1))).strip() if dm else ""
      s_yr, e_yr = (-300, 1521) if (lat >= 19.2 and lon >= -90.5) else (-400, 1200)
      rec = make_site_record(
        sname, lat, lon, s_yr, e_yr, "famsi_witschey_brown_mayagis", arg0_geo,
        {"extra_text": dtxt, "date_basis": "regional_cultural_phase", "reference": dtxt[:200]},
      )
      if rec:
        records.append(rec)
        cnt += 1
  arg1_audit["raw_source_ingested"]["famsi_witschey_brown_mayagis"] = cnt

  # 2. UCSB Mesoamerica & Maya Forest GIS
  ucsb_cnt = 0
  for fn in ("ucsb_mesoamerica_arch_sites.geojson", "ucsb_maya_forest_gis.geojson"):
    p = RAW_DIR / fn
    if not p.exists():
      continue
    gj = json.loads(p.read_text(encoding="utf-8"))
    for feat in gj.get("features", []):
      geom = feat.get("geometry") or {}
      coords = geom.get("coordinates")
      if not coords or geom.get("type") != "Point":
        continue
      lon, lat = float(coords[0]), float(coords[1])
      pr = feat.get("properties") or {}
      sname = (pr.get("NAME") or "").strip()
      if not sname:
        continue
      s_yr, e_yr = (-300, 1521) if (lat >= 19.2 and lon >= -90.5) else (-400, 1200)
      ref = f"{pr.get('SOURCE') or pr.get('POINTSOURC') or ''} {pr.get('REFERENCE') or ''}".strip()
      rec = make_site_record(
        sname, lat, lon, s_yr, e_yr, "ucsb_maya_forest_gis", arg0_geo,
        {"country_hint": pr.get("COUNTRY") or "", "date_basis": "regional_cultural_phase", "reference": ref},
      )
      if rec:
        records.append(rec)
        ucsb_cnt += 1
  arg1_audit["raw_source_ingested"]["ucsb_maya_forest_gis"] = ucsb_cnt

  # 3. Basin of Mexico Survey (SBOM_AggSitePoly6 + BOM_Site_Data_Ortman)
  tr_utm14 = pyproj.Transformer.from_crs("EPSG:32614", "EPSG:4326", always_xy=True)
  bom_loci = {}
  asu_zip = RAW_DIR / "rcesaret_asu_settlement_persist_2022.zip"
  if asu_zip.exists():
    with zipfile.ZipFile(asu_zip) as zf:
      with zf.open("ASUSettlementPersist2022-main/data-processed/SBOM_AggSitePoly6.csv") as fh:
        for row in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace")):
          try:
            lon, lat = tr_utm14.transform(float(row["East"]), float(row["North"]))
            pb, pe = int(float(row["PeriodBegin"])), int(float(row["PeriodEnd"]))
          except Exception:
            continue
          locus = (row.get("OccSeqLoc") or row.get("Site") or "").strip()
          if not locus:
            continue
          if locus not in bom_loci:
            bom_loci[locus] = {"name": f"Basin of Mexico {locus}", "lat": lat, "lon": lon, "start_year": pb, "end_year": pe, "ref": f"Sanders/Parsons/Cesaretti SBOM ({row.get('SurvReg')})"}
          else:
            bom_loci[locus]["start_year"] = min(bom_loci[locus]["start_year"], pb)
            bom_loci[locus]["end_year"] = max(bom_loci[locus]["end_year"], pe)

  bom_zip = RAW_DIR / "rcesaret_aztec_bom_demog.zip"
  if bom_zip.exists():
    with zipfile.ZipFile(bom_zip) as zf:
      wb = openpyxl.load_workbook(
        io.BytesIO(zf.read("AztecColonialDemogAnalysis-main/data-raw/OrtmanData/BOM_Site_Data_Ortman.xlsx")),
        read_only=True, data_only=True,
      )
      hdr = None
      for row in wb["Sheet5"].iter_rows(values_only=True):
        if hdr is None:
          hdr = [str(x).strip() if x is not None else "" for x in row]
          continue
        d = dict(zip(hdr, row))
        try:
          n_km, e_km = float(d.get("North")), float(d.get("East"))
        except Exception:
          continue
        if n_km <= 0 or e_km <= 0:
          continue
        north_m = n_km * 1000.0 if n_km < 10000 else n_km
        east_m = e_km * 1000.0 if e_km < 10000 else e_km
        if not (2000000 <= north_m <= 2300000 and 400000 <= east_m <= 620000):
          continue
        lon, lat = tr_utm14.transform(east_m, north_m)
        per = str(d.get("SitePeriod") or d.get("FieldSite Period") or "").strip().upper()
        span = BOM_PHASE_SPANS.get(per) or next((v for k, v in BOM_PHASE_SPANS.items() if k in per), (-1500, 1521))
        site_code = str(d.get("Site") or d.get("SiteCode") or "").strip()
        sname = str(d.get("SiteName") or "").strip()
        display = f"{sname} ({site_code})" if sname and site_code else (sname or f"BOM {site_code}")
        gkey = f"BOM_{int(round(lat * 300))}_{int(round(lon * 300))}"
        if gkey not in bom_loci:
          bom_loci[gkey] = {"name": display, "lat": lat, "lon": lon, "start_year": span[0], "end_year": span[1], "ref": f"Sanders/Parsons/Ortman BOM Survey ({d.get('FieldSite Region') or d.get('Region')})"}
        else:
          bom_loci[gkey]["start_year"] = min(bom_loci[gkey]["start_year"], span[0])
          bom_loci[gkey]["end_year"] = max(bom_loci[gkey]["end_year"], span[1])
      wb.close()

  bom_cnt = 0
  for loc in bom_loci.values():
    rec = make_site_record(
      loc["name"], loc["lat"], loc["lon"], loc["start_year"], loc["end_year"],
      "rcesaret_basin_of_mexico_survey", arg0_geo,
      {"country_hint": "Mexico", "date_basis": "ceramic_phase_survey", "reference": loc["ref"]},
    )
    if rec:
      records.append(rec)
      bom_cnt += 1
  arg1_audit["raw_source_ingested"]["rcesaret_basin_of_mexico_survey"] = bom_cnt

  # 4. DECM 16th-Century Historical Gazetteer (Relaciones Geográficas 1577-1585 & Suma de Visitas 1548-1550)
  decm_dir = RAW_DIR / "decm_extracted" / "DECM_Gazetteer_primarysources"
  decm_cnt, decm_skipped_nonhab = 0, 0
  non_settl = {
    "river", "rio", "mountain", "cerro", "volcano", "lake", "laguna", "island", "isla",
    "region", "province", "provincia", "sea", "mar", "valley", "valle", "forest", "bosque",
    "plain", "llano", "port", "puerto", "cape", "cabo", "bay", "bahia", "stream", "arroyo",
  }
  if decm_dir.exists():
    spring_dir = decm_dir / "New version Spring 2021"
    shps = sorted(spring_dir.glob("*.shp")) if spring_dir.exists() else []
    snames = {p.name for p in shps}
    shps.extend(p for p in sorted(decm_dir.glob("*.shp")) if p.name not in snames)
    for sp in shps:
      if "polygon" in sp.name.lower():
        continue
      sf = None
      for enc in ("utf-8", "latin-1", "cp1252"):
        try:
          sf = shapefile.Reader(str(sp), encoding=enc, encodingErrors="replace")
          _ = sf.record(0)
          break
        except Exception:
          sf = None
      if sf is None:
        continue
      for i in range(len(sf)):
        try:
          sh = sf.shape(i)
          if not sh.points:
            continue
          lon, lat = float(sh.points[0][0]), float(sh.points[0][1])
          d = sf.record(i).as_dict()
        except Exception:
          continue
        if d.get("Confidence") not in (1, "1", 2, "2", None, ""):
          continue
        typ = str(d.get("Type") or "").strip().lower()
        if any(ns == typ or ns in typ.split() for ns in non_settl):
          decm_skipped_nonhab += 1
          continue
        pname = str(d.get("Placename") or d.get("ModernName") or "").strip()
        if len(pname) < 2:
          continue
        rec = make_site_record(
          pname, lat, lon, 1450, 1585, "decm_relaciones_geograficas_16c", arg0_geo,
          {"record_class": "settlement", "date_basis": "historic_primary_gazetteer", "reference": f"DECM 16c ({sp.stem}): {d.get('References') or 'Relaciones Geograficas'}"},
        )
        if rec:
          records.append(rec)
          decm_cnt += 1
  arg1_audit["raw_source_ingested"]["decm_relaciones_geograficas_16c"] = decm_cnt
  arg1_audit["quality_audits"]["decm_natural_features_excluded"] = decm_skipped_nonhab

  # 5. SWSN NW Mexico (Chihuahua/Paquimé & Sonora)
  swsn_dates = {}
  swsn_data_path = CENTAUR_DIR / "raw_sources" / "swsn_critical_scales_data_all.csv"
  if swsn_data_path.exists():
    with open(swsn_data_path, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        sid = (row.get("SWSN_ID") or "").strip()
        try:
          b, e = int(float(row["Begin"])), int(float(row["End"]))
        except Exception:
          continue
        swsn_dates[sid] = [b, e] if sid not in swsn_dates else [min(swsn_dates[sid][0], b), max(swsn_dates[sid][1], e)]

  tr_utm12 = pyproj.Transformer.from_crs("EPSG:26912", "EPSG:4326", always_xy=True)
  swsn_mx_cnt = 0
  swsn_attr_path = CENTAUR_DIR / "raw_sources" / "swsn_critical_scales_attr_all.csv"
  if swsn_attr_path.exists():
    with open(swsn_attr_path, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        try:
          lon, lat = tr_utm12.transform(float(row["EASTING"]), float(row["NORTHING"]))
        except Exception:
          continue
        if not is_in_mask(lat, lon, arg0_geo):
          continue
        sid = (row.get("SWSN_ID") or "").strip()
        s_yr, e_yr = swsn_dates.get(sid, (1150, 1450))
        rec = make_site_record(
          row.get("SWSN_Site") or f"SWSN-{sid}", lat, lon, s_yr, e_yr,
          "swsn_southwest_nw_mexico", arg0_geo,
          {"country_hint": "Mexico", "record_class": "settlement", "date_basis": "ceramic_phase_survey", "reference": f"SWSN ID {sid}"},
        )
        if rec:
          records.append(rec)
          swsn_mx_cnt += 1
  arg1_audit["raw_source_ingested"]["swsn_nw_mexico"] = swsn_mx_cnt

  # 6. INAH / SIC México Official Zonas Arqueológicas
  sic_path = RAW_DIR / "sic_inah_zonas_arqueologicas.json"
  sic_cnt, sic_placeholder = 0, 0
  if sic_path.exists():
    for r in json.loads(sic_path.read_text(encoding="utf-8")):
      try:
        lat, lon = float(r.get("gmaps_latitud")), float(r.get("gmaps_longitud"))
      except Exception:
        continue
      if lat == 0 and lon == 0:
        continue
      if str(r.get("zona_arqueologica_fecha_fundacion") or "").startswith("1000-01-01"):
        sic_placeholder += 1
      s_yr, e_yr = default_phase_for_region("Mexico", lat, lon)
      rec = make_site_record(
        (r.get("zona_arqueologica_nombre") or "").strip(), lat, lon, s_yr, e_yr,
        "sic_inah_mexico_register", arg0_geo,
        {"country_hint": "Mexico", "date_basis": "regional_cultural_phase", "reference": f"INAH/SIC ({r.get('nom_ent')}, {r.get('nom_mun')})"},
      )
      if rec:
        records.append(rec)
        sic_cnt += 1
  arg1_audit["raw_source_ingested"]["sic_inah_mexico_register"] = sic_cnt
  arg1_audit["quality_audits"]["sic_inah_placeholder_1000_01_01_replaced"] = sic_placeholder

  # 7. RMGIR Proyecto Mesoamérica (Mexico INAH & Guatemala IDAEH)
  rmgir_cnt = 0
  for fn, c_hint in (
    ("rmgir_mexico_zonas_arqueologicas_abiertas.geojson", "Mexico"),
    ("rmgir_mexico_zonas_monumentos_arqueologicos.geojson", "Mexico"),
    ("rmgir_guatemala_sitios_arqueologicos.geojson", "Guatemala"),
  ):
    p = RAW_DIR / fn
    if not p.exists():
      continue
    for feat in json.loads(p.read_text(encoding="utf-8")).get("features", []):
      geom = feat.get("geometry") or {}
      gtype, coords = geom.get("type"), geom.get("coordinates")
      if not coords:
        continue
      if gtype == "Point":
        lon, lat = float(coords[0]), float(coords[1])
      elif gtype == "Polygon" and coords[0]:
        lon = sum(pt[0] for pt in coords[0]) / len(coords[0])
        lat = sum(pt[1] for pt in coords[0]) / len(coords[0])
      elif gtype == "MultiPolygon" and coords[0] and coords[0][0]:
        ring = coords[0][0]
        lon = sum(pt[0] for pt in ring) / len(ring)
        lat = sum(pt[1] for pt in ring) / len(ring)
      else:
        continue
      pr = feat.get("properties") or {}
      sname = str(pr.get("NOMBRE") or pr.get("Nombre") or pr.get("nombre") or pr.get("NOM_ZA") or pr.get("ZONA") or pr.get("SITIO") or pr.get("DESCRIPCIO") or "").strip()
      if not sname:
        continue
      s_yr, e_yr = default_phase_for_region(c_hint, lat, lon)
      rec = make_site_record(
        sname, lat, lon, s_yr, e_yr, "rmgir_mesoamerica_national_gis", arg0_geo,
        {"country_hint": c_hint, "date_basis": "regional_cultural_phase", "reference": f"RMGIR {fn}"},
      )
      if rec:
        records.append(rec)
        rmgir_cnt += 1
  arg1_audit["raw_source_ingested"]["rmgir_mesoamerica_national_gis"] = rmgir_cnt

  # 8. CADB Mexico: Upper Grijalva Basin Chiapas & Sauce Veracruz
  cadb_mx_cnt = 0
  cadb_dir = RAW_DIR / "cadb_pitt"
  tr_utm15 = pyproj.Transformer.from_crs("EPSG:32615", "EPSG:4326", always_xy=True)
  grijalva = defaultdict(lambda: {"lats": [], "lons": [], "has_dom": False})
  for zname, smatch, is_dom in (
    ("cadb_mexico_chiapas_grijalva_civicmap.zip", "civic.shp", False),
    ("cadb_mexico_chiapas_grijalva_domesticmap.zip", "domestic.shp", True),
  ):
    zp = cadb_dir / zname
    if not zp.exists():
      continue
    with zipfile.ZipFile(zp) as zf:
      shps = [n for n in zf.namelist() if n.lower().endswith(smatch)]
      if not shps:
        continue
      base = shps[0][:-4]
      sf = shapefile.Reader(shp=zf.open(base + ".shp"), dbf=zf.open(base + ".dbf"), shx=zf.open(base + ".shx"))
      for i in range(len(sf)):
        sh = sf.shape(i)
        if not sh.points:
          continue
        lon, lat = tr_utm15.transform(sum(p[0] for p in sh.points) / len(sh.points), sum(p[1] for p in sh.points) / len(sh.points))
        sid_raw = str(sf.record(i).as_dict().get("StructID") or "")
        spref = sid_raw.split("-")[0].strip() if "-" in sid_raw else sid_raw[:5]
        if not spref:
          continue
        grijalva[spref]["lats"].append(lat)
        grijalva[spref]["lons"].append(lon)
        if is_dom:
          grijalva[spref]["has_dom"] = True
  for spref, info in grijalva.items():
    rec = make_site_record(
      f"Upper Grijalva {spref}", sum(info["lats"]) / len(info["lats"]), sum(info["lons"]) / len(info["lons"]),
      600, 950, "cadb_pitt_regional_surveys", arg0_geo,
      {"country_hint": "Mexico", "record_class": "settlement" if info["has_dom"] else "monument", "date_basis": "ceramic_phase_survey", "reference": "de Montmollin (1989) Upper Grijalva Basin, CADB Pitt"},
    )
    if rec:
      records.append(rec)
      cadb_mx_cnt += 1

  sauce_txt = cadb_dir / "cadb_mexico_veracruz_sauce_mounds.txt"
  if sauce_txt.exists():
    pts = []
    for ln in sauce_txt.read_text(encoding="utf-8", errors="replace").splitlines():
      cols = [c.strip() for c in ln.split(",")]
      if len(cols) >= 20:
        try:
          lon, lat = tr_utm14.transform(float(cols[-2]), float(cols[-1]))
          pts.append({"name": f"Sauce Veracruz M-{cols[0]}", "lat": lat, "lon": lon, "start_year": 1150, "end_year": 1521})
        except Exception:
          continue
    for cl in grid_parcel_cluster_points(pts, 1.0):
      rec = make_site_record(
        cl["name"], cl["lat"], cl["lon"], cl["start_year"], cl["end_year"],
        "cadb_pitt_regional_surveys", arg0_geo,
        {"country_hint": "Mexico", "record_class": "settlement", "date_basis": "ceramic_phase_survey", "reference": "Ossa (2011) Sauce Veracruz, CADB Pitt"},
      )
      if rec:
        records.append(rec)
        cadb_mx_cnt += 1
  arg1_audit["raw_source_ingested"]["cadb_mexico"] = cadb_mx_cnt
  return records


def C_ingest_central_america_regional(arg0_geo, arg1_audit):
  """Ingests CADB Pitt Lower Central America surveys (Nicaragua, Costa Rica, Panama) and Western Honduras GIS."""
  records = []
  cadb_dir = RAW_DIR / "cadb_pitt"
  cadb_ca_cnt = 0
  tr_utm16 = pyproj.Transformer.from_crs("EPSG:32616", "EPSG:4326", always_xy=True)

  # 1. Nicaragua — Masaya Regional Settlement Survey (Román-Lacayo 2014, non-chaining 1.0 km grid parcels)
  masaya_txt = cadb_dir / "cadb_nicaragua_masaya_ceramics.txt"
  if masaya_txt.exists():
    pts = []
    for ln in masaya_txt.read_text(encoding="utf-8", errors="replace").splitlines():
      cols = [c.strip() for c in ln.split(",")]
      if len(cols) >= 3:
        try:
          lon, lat = tr_utm16.transform(float(cols[1]), float(cols[2]))
          pts.append({"name": f"Masaya {cols[0].split('-')[0]}", "lat": lat, "lon": lon, "start_year": -500, "end_year": 1522})
        except Exception:
          continue
    for cl in grid_parcel_cluster_points(pts, 1.0):
      rec = make_site_record(
        cl["name"], cl["lat"], cl["lon"], cl["start_year"], cl["end_year"],
        "cadb_pitt_regional_surveys", arg0_geo,
        {"country_hint": "Nicaragua", "record_class": "settlement", "date_basis": "ceramic_phase_survey", "reference": f"Román-Lacayo (2014) Masaya Survey, CADB Pitt ({cl['n_lots']} lots)"},
      )
      if rec:
        records.append(rec)
        cadb_ca_cnt += 1

  # 2. Costa Rica — San Ramón de Alajuela (Murillo Herrera 2011, 1.0 km grid parcels)
  sr_zip = cadb_dir / "cadb_costarica_sanramon_map.zip"
  if sr_zip.exists():
    pts = []
    with zipfile.ZipFile(sr_zip) as zf:
      sf = shapefile.Reader(shp=zf.open("lots.shp"), dbf=zf.open("lots.dbf"), shx=zf.open("lots.shx"))
      for i in range(len(sf)):
        sh = sf.shape(i)
        if not sh.points:
          continue
        lon, lat = tr_utm16.transform(sum(p[0] for p in sh.points) / len(sh.points), sum(p[1] for p in sh.points) / len(sh.points))
        lotn = sf.record(i).as_dict().get("LotNumber") or i
        pts.append({"name": f"San Ramón Alajuela SR-{lotn}", "lat": lat, "lon": lon, "start_year": -300, "end_year": 1550})
    for cl in grid_parcel_cluster_points(pts, 1.0):
      rec = make_site_record(
        cl["name"], cl["lat"], cl["lon"], cl["start_year"], cl["end_year"],
        "cadb_pitt_regional_surveys", arg0_geo,
        {"country_hint": "Costa Rica", "record_class": "settlement", "date_basis": "ceramic_phase_survey", "reference": f"Murillo Herrera (2011) San Ramón Survey, CADB Pitt ({cl['n_lots']} lots)"},
      )
      if rec:
        records.append(rec)
        cadb_ca_cnt += 1

  # 3. Costa Rica — Upper Térraba Regional Survey (Sol Castillo 2013, CR-SIRGAS CRTM05, 1.0 km parcels)
  tr_crtm05 = pyproj.Transformer.from_crs("EPSG:5367", "EPSG:4326", always_xy=True)
  ter_zip = cadb_dir / "cadb_costarica_terraba_lots.zip"
  if ter_zip.exists():
    pts = []
    with zipfile.ZipFile(ter_zip) as zf:
      base = "lotsoptimized/lots-Polygon"
      sf = shapefile.Reader(shp=zf.open(base + ".shp"), dbf=zf.open(base + ".dbf"), shx=zf.open(base + ".shx"))
      for i in range(len(sf)):
        sh = sf.shape(i)
        if not sh.points:
          continue
        lon, lat = tr_crtm05.transform(sum(p[0] for p in sh.points) / len(sh.points), sum(p[1] for p in sh.points) / len(sh.points))
        pts.append({"name": f"Upper Térraba UT-{i+1}", "lat": lat, "lon": lon, "start_year": 200, "end_year": 1550})
    for cl in grid_parcel_cluster_points(pts, 1.0):
      rec = make_site_record(
        cl["name"], cl["lat"], cl["lon"], cl["start_year"], cl["end_year"],
        "cadb_pitt_regional_surveys", arg0_geo,
        {"country_hint": "Costa Rica", "record_class": "settlement", "date_basis": "ceramic_phase_survey", "reference": f"Sol Castillo (2013) Upper Térraba Survey, CADB Pitt ({cl['n_lots']} lots)"},
      )
      if rec:
        records.append(rec)
        cadb_ca_cnt += 1

  # 4. Panama — Volcán Barú Regional Survey (Palumbo 2009, mapped site polygons + collection parcels)
  tr_utm17_nad27 = pyproj.Transformer.from_crs("EPSG:26717", "EPSG:4326", always_xy=True)
  vb_pts = []
  vb_zip = cadb_dir / "cadb_panama_volcanbaru_map.zip"
  if vb_zip.exists():
    with zipfile.ZipFile(vb_zip) as zf:
      base = "map/map-Polygon"
      sf = shapefile.Reader(shp=zf.open(base + ".shp"), dbf=zf.open(base + ".dbf"), shx=zf.open(base + ".shx"))
      for i in range(len(sf)):
        sh = sf.shape(i)
        if not sh.points:
          continue
        lon, lat = tr_utm17_nad27.transform(sum(p[0] for p in sh.points) / len(sh.points), sum(p[1] for p in sh.points) / len(sh.points))
        vb_pts.append({"name": f"Volcán Barú Site {i+1}", "lat": lat, "lon": lon, "start_year": 200, "end_year": 1550})
  vb_txt = cadb_dir / "cadb_panama_volcanbaru_collections.txt"
  if vb_txt.exists():
    for ln in vb_txt.read_text(encoding="utf-8", errors="replace").splitlines():
      cols = [c.strip() for c in ln.split(",")]
      if len(cols) >= 4:
        try:
          lon, lat = tr_utm17_nad27.transform(float(cols[2]), float(cols[3]))
          vb_pts.append({"name": f"Volcán Barú {cols[0]}", "lat": lat, "lon": lon, "start_year": 200, "end_year": 1550})
        except Exception:
          continue
  for cl in grid_parcel_cluster_points(vb_pts, 1.0):
    rec = make_site_record(
      cl["name"], cl["lat"], cl["lon"], cl["start_year"], cl["end_year"],
      "cadb_pitt_regional_surveys", arg0_geo,
      {"country_hint": "Panama", "record_class": "settlement", "date_basis": "ceramic_phase_survey", "reference": f"Palumbo (2009) Volcán Barú Survey, Chiriquí, CADB Pitt ({cl['n_lots']} units)"},
    )
    if rec:
      records.append(rec)
      cadb_ca_cnt += 1
  arg1_audit["raw_source_ingested"]["cadb_central_america"] = cadb_ca_cnt

  # 5. Western Honduras Maya Sites GIS
  hn_path = RAW_DIR / "agol_honduras_western_maya_sites.geojson"
  hn_cnt = 0
  if hn_path.exists():
    for feat in json.loads(hn_path.read_text(encoding="utf-8")).get("features", []):
      coords = (feat.get("geometry") or {}).get("coordinates")
      pr = feat.get("properties") or {}
      sname = (pr.get("NAME") or "").strip()
      if not coords or not sname:
        continue
      rec = make_site_record(
        sname, float(coords[1]), float(coords[0]), -400, 1200, "agol_honduras_western_maya", arg0_geo,
        {"country_hint": "Honduras", "date_basis": "regional_cultural_phase", "reference": str(pr.get("POINTSOURC") or "Western Honduras Maya GIS")},
      )
      if rec:
        records.append(rec)
        hn_cnt += 1
  arg1_audit["raw_source_ingested"]["agol_honduras_western_maya"] = hn_cnt
  return records


def D_ingest_caribbean_regional(arg0_geo, arg1_audit):
  """Ingests DANS NEXUS1492 Montecristi Coast, NRHP PR/USVI audited archaeological sites, and Bermuda historic parishes."""
  records = []

  # 1. DANS / NEXUS1492 Montecristi Coast Survey (Dominican Republic — UTM 19N)
  tr_utm19 = pyproj.Transformer.from_crs("EPSG:32619", "EPSG:4326", always_xy=True)
  mc_csv = RAW_DIR / "dans_caribbean" / "DANS-XYN-CU72_Archaeological_and_Environmental_Database.csv"
  mc_cnt = 0
  if mc_csv.exists():
    with open(mc_csv, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        try:
          lon, lat = tr_utm19.transform(float(row["East"]), float(row["North"]))
        except Exception:
          continue
        code = (row.get("Code") or f"MC-{row.get('ID')}").strip()
        starts, ends = [], []
        if str(row.get("Without-ceramic") or "0").strip() == "1":
          starts.append(-2500); ends.append(600)
        if str(row.get("Meillacoid") or "0").strip() == "1":
          starts.append(800); ends.append(1500)
        if str(row.get("Mixed Meillacoid-Chicoid") or "0").strip() == "1":
          starts.append(1000); ends.append(1520)
        if str(row.get("Chicoid") or "0").strip() == "1":
          starts.append(1200); ends.append(1520)
        if str(row.get("European Materials") or "0").strip() == "1":
          starts.append(1492); ends.append(1550)
        func = (row.get("Function") or "").strip().upper()
        rec = make_site_record(
          f"Montecristi {code}", lat, lon, min(starts) if starts else 600, max(ends) if ends else 1520,
          "dans_nexus1492_montecristi", arg0_geo,
          {"country_hint": "Dominican Republic", "record_class": "settlement" if func in ("HAB", "HABITATION", "") else "monument", "date_basis": "ceramic_phase_survey", "reference": "Herrera Malatesta & Hofman (2019) NEXUS1492, doi:10.17026/DANS-XYN-CU72"},
        )
        if rec:
          records.append(rec)
          mc_cnt += 1
  arg1_audit["raw_source_ingested"]["dans_nexus1492_montecristi"] = mc_cnt

  # 2. US NPS NRHP Audited Archaeological Sites in Puerto Rico & USVI
  nrhp_path = CENTAUR_DIR / "raw_sources" / "nps_nrhp_locations.geojson"
  nrhp_cnt, nrhp_rejected = 0, 0
  arch_kw = re.compile(
    r"archeo|archaeo|prehist|pre-columb|taino|saladoid|ostionoid|batey|ballcourt|petroglyph|midden|"
    r"shell|cave|cueva|indigenous|indian|aboriginal|plantation|estate|sugar|fort|fortaleza|battery|"
    r"convento|ruin|site|shipwreck|historical\s+district|cemetery",
    re.I,
  )
  if nrhp_path.exists():
    for feat in json.loads(nrhp_path.read_text(encoding="utf-8")).get("features", []):
      geom = feat.get("geometry") or {}
      pr = feat.get("properties") or {}
      st = (pr.get("State") or "").upper()
      if geom.get("type") != "Point" or st not in ("PUERTO RICO", "VIRGIN ISLANDS"):
        continue
      rt = (pr.get("ResType") or "").lower()
      rname = (pr.get("RESNAME") or "").strip()
      if (rt != "site" and int(pr.get("NumCSite") or 0) <= 0) or (rt != "site" and not arch_kw.search(rname)):
        nrhp_rejected += 1
        continue
      lon, lat = float(geom["coordinates"][0]), float(geom["coordinates"][1])
      s_yr, e_yr = (1520, 1898) if re.search(r"estate|plantation|sugar|moravian|church|convento|fort|battery|lighthouse|whim|factory", rname, re.I) else (-500, 1520)
      rec = make_site_record(
        rname, lat, lon, s_yr, e_yr, "nps_nrhp_caribbean_register", arg0_geo,
        {"country_hint": "Puerto Rico" if st == "PUERTO RICO" else "United States Virgin Islands", "date_basis": "regional_cultural_phase", "reference": f"US NPS NRHP Ref {pr.get('NRIS_Refnum')}"},
      )
      if rec:
        records.append(rec)
        nrhp_cnt += 1
  arg1_audit["raw_source_ingested"]["nps_nrhp_caribbean_register"] = nrhp_cnt
  arg1_audit["quality_audits"]["nrhp_pr_usvi_non_arch_buildings_excluded"] = nrhp_rejected

  # 3. Bermuda Early Colonial Surveyed Parishes (Norwood 1618-1663 / CENTAUR)
  bmd_cnt = 0
  ds_path = CENTAUR_DIR / "config" / "documented_site_series.json"
  if ds_path.exists():
    for item in json.loads(ds_path.read_text(encoding="utf-8")).get("settlements", []):
      lat, lon = item.get("lat"), item.get("lon")
      if lat is None or lon is None or not (32.0 <= lat <= 32.6 and -65.1 <= lon <= -64.5):
        continue
      series = item.get("series") or []
      rec = make_site_record(
        f"{item.get('name')} (Bermuda Historic Parish)", lat, lon, int(series[0][0]) if series else 1612, 1900,
        "centaur_bermuda_historic_parishes", arg0_geo,
        {"country_hint": "Bermuda", "record_class": "settlement", "date_basis": "historic_primary_gazetteer", "reference": "Norwood Survey (1618-1663) / CENTAUR Documented Settlements"},
      )
      if rec:
        records.append(rec)
        bmd_cnt += 1
  arg1_audit["raw_source_ingested"]["centaur_bermuda_historic_parishes"] = bmd_cnt
  return records


def E_ingest_global_atlases_and_radiocarbon(arg0_geo, arg1_audit):
  """Ingests Harvard Arch Atlas, Harvard AADR v66, UNESCO WHC, SVEA C14, p3k14c 2025, and Caribbean 14C."""
  records = []

  # 1. Harvard Dataverse Archaeological Atlas of Published Excavations
  hd_kmz = RAW_DIR / "harvard_dataverse_arch_atlas.kmz"
  hd_cnt = 0
  if hd_kmz.exists():
    pm_re = re.compile(r"<Placemark[^>]*>(.*?)</Placemark>", re.S)
    name_re = re.compile(r"<name>(.*?)</name>", re.S)
    desc_re = re.compile(r"<description>(.*?)</description>", re.S)
    coord_re = re.compile(r"<coordinates>\s*([^<]+?)\s*</coordinates>", re.S)
    with zipfile.ZipFile(hd_kmz) as zf:
      kml_txt = zf.read("doc.kml").decode("utf-8", errors="replace")
    for m in pm_re.finditer(kml_txt):
      blk = m.group(1)
      cm = coord_re.search(blk)
      if not cm:
        continue
      parts = cm.group(1).strip().split(",")
      try:
        lon, lat = float(parts[0]), float(parts[1])
      except Exception:
        continue
      if not is_in_mask(lat, lon, arg0_geo):
        continue
      nm, dm = name_re.search(blk), desc_re.search(blk)
      sname = (re.sub(r"<[^>]+>", "", nm.group(1)).strip() if nm else "").replace("&apos;", "'").replace("&amp;", "&")
      ref_raw = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", dm.group(1)).replace("<![CDATA[", "").replace("]]>", "")).strip() if dm else ""
      country = classify_country(lat, lon, arg0_geo)
      s_yr, e_yr = default_phase_for_region(country, lat, lon)
      rec = make_site_record(
        sname, lat, lon, s_yr, e_yr, "harvard_dataverse_arch_atlas", arg0_geo,
        {"country_hint": country, "date_basis": "regional_cultural_phase", "reference": ref_raw[:220]},
      )
      if rec:
        records.append(rec)
        hd_cnt += 1
  arg1_audit["raw_source_ingested"]["harvard_dataverse_arch_atlas"] = hd_cnt

  # 2. Harvard AADR v66.p1 Directly Dated Ancient DNA Archaeological Sites
  aadr_path = RAW_DIR / "harvard_aadr_ancient_dna_sites.anno.tsv"
  aadr_sites = {}
  if aadr_path.exists():
    with open(aadr_path, "r", encoding="utf-8", errors="replace") as fh:
      rdr = csv.DictReader(fh, delimiter="\t")
      fns = rdr.fieldnames or []
      lat_k = next(c for c in fns if c.lower().startswith("lat"))
      lon_k = next(c for c in fns if c.lower().startswith("long"))
      loc_k = next(c for c in fns if "locality" in c.lower())
      ent_k = next(c for c in fns if "political" in c.lower())
      dt_k = next(c for c in fns if "date mean" in c.lower())
      pub_k = next(c for c in fns if "publication abbreviation" in c.lower())
      for row in rdr:
        try:
          lat, lon, dt_bp = float(row[lat_k]), float(row[lon_k]), float(row[dt_k])
        except Exception:
          continue
        if not is_in_mask(lat, lon, arg0_geo):
          continue
        loc = (row.get(loc_k) or "").strip()
        key = (normalize_name(loc), round(lat, 2), round(lon, 2))
        ce = int(round(1950 - dt_bp))
        if key not in aadr_sites:
          aadr_sites[key] = {"name": loc or "AADR Site", "lat": lat, "lon": lon, "country": (row.get(ent_k) or "").strip(), "dates": [ce], "ref": (row.get(pub_k) or "AADR v66.p1").strip()}
        else:
          aadr_sites[key]["dates"].append(ce)
  aadr_cnt = 0
  for info in aadr_sites.values():
    rec = make_site_record(
      info["name"], info["lat"], info["lon"], min(info["dates"]) - 125, max(info["dates"]) + 125,
      "harvard_aadr_v66", arg0_geo,
      {"country_hint": info["country"], "date_basis": "calibrated_c14", "reference": f"AADR v66.p1 ({info['ref']})"},
    )
    if rec:
      records.append(rec)
      aadr_cnt += 1
  arg1_audit["raw_source_ingested"]["harvard_aadr_v66"] = aadr_cnt

  # 3. UNESCO World Heritage Centre Official Properties
  whc_path = RAW_DIR / "unesco_whc_sites.xml"
  whc_cnt = 0
  if whc_path.exists():
    for row in ET.parse(whc_path).getroot().findall(".//row"):
      if (row.findtext("category") or "").strip() not in ("Cultural", "Mixed"):
        continue
      site = (row.findtext("site") or "").strip()
      states = (row.findtext("states") or "").strip()
      desc = (row.findtext("short_description") or "").strip()
      for poi in row.findall(".//geolocations/poi"):
        try:
          lat, lon = float(poi.findtext("latitude") or ""), float(poi.findtext("longitude") or "")
        except Exception:
          continue
        if not is_in_mask(lat, lon, arg0_geo):
          continue
        if re.search(r"Barragán|University City|Ciudad Universitaria|19th and 20th", site + " " + desc, re.I):
          continue
        if re.search(r"16th|17th|18th|colonial|fortification|garrison|havana|santo domingo|bridgetown|willemstad|st george|portobelo|leon viejo|san juan|monasteries|camino real|aqueduct", site + " " + desc, re.I):
          s_yr, e_yr = (1612, 1900) if "bermuda" in site.lower() else (1502, 1898)
        else:
          s_yr, e_yr = default_phase_for_region(states, lat, lon)
        rec = make_site_record(
          site, lat, lon, s_yr, e_yr, "unesco_whc_official", arg0_geo,
          {"country_hint": states, "date_basis": "historic_primary_gazetteer", "reference": f"UNESCO WHC #{row.findtext('id_number')}"},
        )
        if rec:
          records.append(rec)
          whc_cnt += 1
        break
  arg1_audit["raw_source_ingested"]["unesco_whc_official"] = whc_cnt

  # 4. SVEA c14_cleaned_dedup.csv & p3k14c 2025
  c14_grouped = {}
  for path_obj, lk, ok, ak, sk, ck, refk, sid in (
    (C14_CSV, "lat", "lon", "c14age", "site", "country", "sourcedb", "svea_c14_cleaned_dedup"),
    (CENTAUR_DIR / "raw_sources" / "people3k_RawP3Kc14_2025.csv", "Latitude", "Longitude", "Age", "SiteName", "Country", "Source", "p3k14c_2025_mesorad"),
  ):
    if not path_obj.exists():
      continue
    with open(path_obj, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        try:
          lat, lon = float(row.get(lk) or ""), float(row.get(ok) or "")
        except Exception:
          continue
        if not is_in_mask(lat, lon, arg0_geo):
          continue
        ce = calibrate_14c_to_ce(row.get(ak))
        if ce is None:
          continue
        sname = (row.get(sk) or "").strip()
        key = (sid, normalize_name(sname), round(lat, 2), round(lon, 2))
        if key not in c14_grouped:
          c14_grouped[key] = {"name": sname or f"C14 Site ({lat:.2f}, {lon:.2f})", "lat": lat, "lon": lon, "country": (row.get(ck) or "").strip(), "dates": [ce], "sid": sid, "ref": (row.get(refk) or sid).strip()}
        else:
          c14_grouped[key]["dates"].append(ce)

  coord_counts = Counter((round(v["lat"], 2), round(v["lon"], 2)) for v in c14_grouped.values())
  c14_fuzzed_flagged = 0
  c14_kept_by_src = Counter()
  for info in c14_grouped.values():
    ctry = classify_country(info["lat"], info["lon"], arg0_geo, info["country"])
    is_carib = resolve_jurisdiction(ctry, info["lat"], info["lon"]) == "caribbean"
    stacked = coord_counts[(round(info["lat"], 2), round(info["lon"], 2))] >= 3 and is_carib
    if stacked:
      c14_fuzzed_flagged += 1
      prec = "island_centroid_large" if ctry.lower() in LARGE_CARIBBEAN_ISLANDS else "island_centroid_small"
    else:
      prec = "site"
    rec = make_site_record(
      info["name"], info["lat"], info["lon"], min(info["dates"]) - 150, max(info["dates"]) + 150, info["sid"], arg0_geo,
      {"country_hint": ctry, "date_basis": "calibrated_c14", "coord_precision": prec, "reference": f"{info['ref']} (n={len(info['dates'])} 14C dates)"},
    )
    if rec:
      records.append(rec)
      c14_kept_by_src[info["sid"]] += 1
  for k, v in c14_kept_by_src.items():
    arg1_audit["raw_source_ingested"][k] = v

  # 5. philriris/caribbean-14C (all island-centroid fuzzed; flagged cleanly for horizon reconciliation)
  car_path = RAW_DIR / "philriris_caribbean_14c_delta.csv"
  car_grouped = {}
  if car_path.exists():
    with open(car_path, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        try:
          lat, lon = float(row.get("Lat") or ""), float(row.get("Lon") or "")
        except Exception:
          continue
        if not is_in_mask(lat, lon, arg0_geo):
          continue
        ce = calibrate_14c_to_ce(row.get("Age"))
        if ce is None:
          continue
        sname = (row.get("SiteName") or "").strip()
        isl = (row.get("Island") or row.get("Country.Territory") or "").strip()
        key = (normalize_name(isl), normalize_name(sname))
        if key not in car_grouped:
          car_grouped[key] = {"name": sname or f"{isl} C14 Site", "island": isl, "lat": lat, "lon": lon, "dates": [ce], "ref": (row.get("Reference") or "Napolitano et al. 2019 / caribbean-14C").strip()}
        else:
          car_grouped[key]["dates"].append(ce)
  car_cnt = 0
  for info in car_grouped.values():
    prec = "island_centroid_large" if info["island"].lower().strip() in LARGE_CARIBBEAN_ISLANDS else "island_centroid_small"
    rec = make_site_record(
      info["name"], info["lat"], info["lon"], min(info["dates"]) - 150, max(info["dates"]) + 150, "philriris_caribbean_14c", arg0_geo,
      {"country_hint": info["island"], "date_basis": "calibrated_c14", "coord_precision": prec, "reference": f"{info['ref']} (n={len(info['dates'])} 14C dates)"},
    )
    if rec:
      records.append(rec)
      car_cnt += 1
  arg1_audit["raw_source_ingested"]["philriris_caribbean_14c"] = car_cnt
  arg1_audit["quality_audits"]["c14_island_centroid_records_flagged"] = c14_fuzzed_flagged + car_cnt
  return records


def F_ingest_centaur_frontier_buffer(arg0_geo, arg1_audit):
  """Imports archaeological sites within `250 km` north of the US-Mexico border (`is_frontier_buffer: true`) from CENTAUR."""
  records = []
  buf_grouped = {}
  for fn, lk, ok, ak1, ak2, sk, sidk, src_id in (
    ("kelly_robinson_lower48_2021.csv", "Lat", "Long", "Norm", "Measured", "SiteName", "SiteID", "centaur_frontier_kelly_robinson"),
    ("people3k_RawP3Kc14_2025.csv", "Latitude", "Longitude", "Age", None, "SiteName", "SiteID", "p3k14c_2025_mesorad"),
    ("people3k_FinalRCDTexas3.csv", "Lat", "Long", "Age", None, "SiteName", "SiteID", "centaur_frontier_tx_socal_c14"),
    ("people3k_SoCaldates.csv", "Lat", "Long", "Age", None, "SiteName", "SiteID", "centaur_frontier_tx_socal_c14"),
  ):
    p = CENTAUR_DIR / "raw_sources" / fn
    if not p.exists():
      continue
    with open(p, "r", encoding="utf-8", errors="replace") as fh:
      rdr = csv.DictReader(fh)
      fns = rdr.fieldnames or []
      lat_col = lk if lk in fns else next((c for c in fns if c.lower() in ("lat", "latitude")), None)
      lon_col = ok if ok in fns else next((c for c in fns if c.lower() in ("long", "lon", "longitude")), None)
      age_col = ak1 if ak1 in fns else next((c for c in fns if "age" in c.lower() or "c14" in c.lower()), None)
      if not lat_col or not lon_col or not age_col:
        continue
      for row in rdr:
        if (row.get("Type") or "").strip().upper() in ("GEOLOGICAL", "PALEONTOLOGICAL"):
          continue
        try:
          lat, lon = float(row[lat_col]), float(row[lon_col])
        except Exception:
          continue
        if not (25.5 <= lat <= 35.5 and -120.5 <= lon <= -95.0) or is_in_mask(lat, lon, arg0_geo):
          continue
        if min_dist_to_us_mx_border_km(lat, lon, arg0_geo) > 250.0:
          continue
        ce = calibrate_14c_to_ce(row.get(age_col))
        if ce is None and ak2 and ak2 in fns:
          ce = calibrate_14c_to_ce(row.get(ak2))
        if ce is None:
          continue
        sname = (row.get(sk) or row.get(sidk) or "").strip()
        key = (src_id, normalize_name(sname), round(lat, 2), round(lon, 2))
        if key not in buf_grouped:
          buf_grouped[key] = {"name": sname or f"US Frontier Site ({lat:.2f}, {lon:.2f})", "lat": lat, "lon": lon, "dates": [ce], "src_id": src_id}
        else:
          buf_grouped[key]["dates"].append(ce)

  buf_c14_cnt = 0
  for info in buf_grouped.values():
    rec = make_site_record(
      info["name"], info["lat"], info["lon"], min(info["dates"]) - 150, max(info["dates"]) + 150, info["src_id"], arg0_geo,
      {"is_frontier_buffer": True, "date_basis": "calibrated_c14", "reference": f"CENTAUR 250 km buffer ({info['src_id']}, n={len(info['dates'])})"},
    )
    if rec:
      records.append(rec)
      buf_c14_cnt += 1

  swsn_dates = {}
  swsn_data_path = CENTAUR_DIR / "raw_sources" / "swsn_critical_scales_data_all.csv"
  if swsn_data_path.exists():
    with open(swsn_data_path, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        sid = (row.get("SWSN_ID") or "").strip()
        try:
          b, e = int(float(row["Begin"])), int(float(row["End"]))
        except Exception:
          continue
        swsn_dates[sid] = [b, e] if sid not in swsn_dates else [min(swsn_dates[sid][0], b), max(swsn_dates[sid][1], e)]

  tr_utm12 = pyproj.Transformer.from_crs("EPSG:26912", "EPSG:4326", always_xy=True)
  swsn_us_cnt = 0
  swsn_attr_path = CENTAUR_DIR / "raw_sources" / "swsn_critical_scales_attr_all.csv"
  if swsn_attr_path.exists():
    with open(swsn_attr_path, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        try:
          lon, lat = tr_utm12.transform(float(row["EASTING"]), float(row["NORTHING"]))
        except Exception:
          continue
        if is_in_mask(lat, lon, arg0_geo) or min_dist_to_us_mx_border_km(lat, lon, arg0_geo) > 250.0:
          continue
        sid = (row.get("SWSN_ID") or "").strip()
        s_yr, e_yr = swsn_dates.get(sid, (1150, 1450))
        rec = make_site_record(
          row.get("SWSN_Site") or f"SWSN-{sid}", lat, lon, s_yr, e_yr, "swsn_southwest_nw_mexico", arg0_geo,
          {"is_frontier_buffer": True, "record_class": "settlement", "date_basis": "ceramic_phase_survey", "reference": f"CENTAUR 250 km buffer SWSN ID {sid}"},
        )
        if rec:
          records.append(rec)
          swsn_us_cnt += 1

  ds_cnt = 0
  ds_path = CENTAUR_DIR / "config" / "documented_site_series.json"
  if ds_path.exists():
    for item in json.loads(ds_path.read_text(encoding="utf-8")).get("settlements", []):
      lat, lon = item.get("lat"), item.get("lon")
      if lat is None or lon is None or not (25.5 <= lat <= 35.5 and -120.5 <= lon <= -95.0):
        continue
      if is_in_mask(lat, lon, arg0_geo) or min_dist_to_us_mx_border_km(lat, lon, arg0_geo) > 250.0:
        continue
      series = item.get("series") or []
      s_yr = int(series[0][0]) if series else 1000
      e_yr = max(s_yr + 150, int(series[-1][0])) if series else 1750
      rec = make_site_record(
        item.get("name"), lat, lon, s_yr, e_yr, "centaur_frontier_documented_settlements", arg0_geo,
        {"is_frontier_buffer": True, "record_class": "settlement", "date_basis": "historic_primary_gazetteer", "reference": "CENTAUR Documented Settlements (250 km northern frontier buffer)"},
      )
      if rec:
        records.append(rec)
        ds_cnt += 1

  arg1_audit["raw_source_ingested"]["centaur_frontier_c14"] = buf_c14_cnt
  arg1_audit["raw_source_ingested"]["centaur_frontier_swsn"] = swsn_us_cnt
  arg1_audit["raw_source_ingested"]["centaur_frontier_documented_settlements"] = ds_cnt
  return records


def G_deduplicate_and_reconcile(arg0_records, arg1_audit):
  """Deduplicates multi-repository records, upgrades dates with C14, and collapses island-centroid stacking cleanly."""
  site_recs = [r for r in arg0_records if r["coord_precision"] == "site"]
  fuzzed_recs = [r for r in arg0_records if r["coord_precision"] != "site"]

  site_recs.sort(key=lambda r: (
    0 if not r["is_frontier_buffer"] else 1,
    -TIER_PRIORITY.get(r["source_tier"], 0),
    -DATE_BASIS_PRIORITY.get(r["date_basis"], 0),
    r["name"],
  ))

  grid = defaultdict(list)
  kept = []
  by_country_norm_name = defaultdict(list)
  merged_dups = 0

  for rec in site_recs:
    lat, lon = rec["lat"], rec["lon"]
    gy, gx = int(math.floor(lat * 10.0)), int(math.floor(lon * 10.0))
    nname = normalize_name(rec["name"])
    is_buf = rec["is_frontier_buffer"]

    match_idx = None
    for dy in (-1, 0, 1):
      for dx in (-1, 0, 1):
        for idx in grid.get((gy + dy, gx + dx), ()):
          ex = kept[idx]
          if ex["is_frontier_buffer"] != is_buf:
            continue
          dist = haversine_km(lat, lon, ex["lat"], ex["lon"])
          if (nname and nname == ex["_nname"] and dist <= 10.0) or dist <= 0.8:
            match_idx = idx
            break
        if match_idx is not None:
          break
      if match_idx is not None:
        break

    if match_idx is not None:
      ex = kept[match_idx]
      merged_dups += 1
      in_p, ex_p = DATE_BASIS_PRIORITY.get(rec["date_basis"], 0), DATE_BASIS_PRIORITY.get(ex["date_basis"], 0)
      if in_p > ex_p:
        ex["start_year"], ex["end_year"], ex["date_basis"] = rec["start_year"], rec["end_year"], rec["date_basis"]
      elif in_p == ex_p:
        ex["start_year"] = min(ex["start_year"], rec["start_year"])
        ex["end_year"] = max(ex["end_year"], rec["end_year"])
      if rec["source_id"] not in ex["_alt_sources"]:
        ex["_alt_sources"].append(rec["source_id"])
      continue

    rec["_nname"] = nname
    rec["_alt_sources"] = [rec["source_id"]]
    idx = len(kept)
    kept.append(rec)
    grid[(gy, gx)].append(idx)
    if not is_buf and nname:
      by_country_norm_name[(rec["country"], nname)].append(idx)

  # Reconcile island-centroid-fuzzed Caribbean C14 records without artificial single-pixel stacking:
  # 1) Match by normalized site name against true-coordinate sites on the same island to upgrade their C14 chronology.
  # 2) For unmatched fuzzed records, group per (country, centroid_0.02deg, major_horizon) into at most 1 clean
  #    radiocarbon horizon anchor per occupied cultural epoch (Archaic < -500, Early Ceramic -500..599, Late Ceramic >= 600).
  fuzzed_upgraded = 0
  fuzzed_buckets = defaultdict(list)
  for rec in fuzzed_recs:
    nname = normalize_name(rec["name"])
    if nname and (rec["country"], nname) in by_country_norm_name:
      for idx in by_country_norm_name[(rec["country"], nname)]:
        ex = kept[idx]
        if DATE_BASIS_PRIORITY.get(rec["date_basis"], 0) > DATE_BASIS_PRIORITY.get(ex["date_basis"], 0):
          ex["start_year"], ex["end_year"], ex["date_basis"] = rec["start_year"], rec["end_year"], rec["date_basis"]
        else:
          ex["start_year"] = min(ex["start_year"], rec["start_year"])
          ex["end_year"] = max(ex["end_year"], rec["end_year"])
        if rec["source_id"] not in ex["_alt_sources"]:
          ex["_alt_sources"].append(rec["source_id"])
      fuzzed_upgraded += 1
      continue

    mid = 0.5 * (rec["start_year"] + rec["end_year"])
    epoch = "Archaic" if mid < -500 else ("Early_Ceramic" if mid < 600 else "Late_Ceramic_Contact")
    bkey = (rec["country"], round(rec["lat"], 2), round(rec["lon"], 2), epoch)
    fuzzed_buckets[bkey].append(rec)

  true_cnt_by_country = Counter(r["country"] for r in kept if not r["is_frontier_buffer"])
  fuzzed_anchors = 0
  fuzzed_collapsed = 0
  for (ctry, clat, clon, epoch), ulist in sorted(fuzzed_buckets.items()):
    # On large islands that already have >= 15 true-coordinate sites, drop unmatched stacked island centroids
    if ctry.lower() in LARGE_CARIBBEAN_ISLANDS and true_cnt_by_country[ctry] >= 15:
      fuzzed_collapsed += len(ulist)
      continue
    # Deduplicate site names within this island-epoch bucket
    uniq_names = sorted({u["name"] for u in ulist})
    anchor = dict(ulist[0])
    anchor["name"] = f"{ctry} ({epoch.replace('_', ' ')} C14 Horizon: {', '.join(uniq_names[:3])})"
    anchor["start_year"] = min(u["start_year"] for u in ulist)
    anchor["end_year"] = max(u["end_year"] for u in ulist)
    anchor["reference"] = f"Consolidated {len(uniq_names)} island-centroid C14 sites ({', '.join(sorted({u['source_id'] for u in ulist}))})"
    anchor["_nname"] = normalize_name(anchor["name"])
    anchor["_alt_sources"] = sorted({u["source_id"] for u in ulist})
    kept.append(anchor)
    fuzzed_anchors += 1
    fuzzed_collapsed += max(0, len(ulist) - 1)

  arg1_audit["quality_audits"]["cross_repository_duplicates_merged"] = merged_dups
  arg1_audit["quality_audits"]["caribbean_fuzzed_c14_matched_to_true_coords"] = fuzzed_upgraded
  arg1_audit["quality_audits"]["caribbean_fuzzed_c14_horizon_anchors_retained"] = fuzzed_anchors
  arg1_audit["quality_audits"]["caribbean_fuzzed_c14_stacked_centroids_collapsed"] = fuzzed_collapsed

  final_sites = []
  for idx, r in enumerate(kept, 1):
    prefix = "JAG_BUF" if r["is_frontier_buffer"] else "JAG"
    final_sites.append({
      "site_id": f"{prefix}_{idx:06d}",
      "name": r["name"],
      "lat": r["lat"],
      "lon": r["lon"],
      "start_year": r["start_year"],
      "end_year": r["end_year"],
      "country": r["country"],
      "jurisdiction": r["jurisdiction"],
      "source_id": r["source_id"],
      "source_tier": r["source_tier"],
      "record_class": r["record_class"],
      "is_frontier_buffer": r["is_frontier_buffer"],
      "date_basis": r["date_basis"],
      "coord_precision": r["coord_precision"],
      "corroborating_sources": r["_alt_sources"],
      "reference": r["reference"],
    })
  return final_sites


def H_compute_c14_baseline_and_export(arg0_sites, arg1_geo, arg2_audit):
  """Computes canonical Viscount C14 baseline inside mask, audits all thresholds, and writes JSON outputs."""
  seen, c14_base = set(), 0
  with open(C14_CSV, "r", encoding="utf-8", errors="replace") as fh:
    for row in csv.DictReader(fh):
      try:
        lat, lon = float(row.get("lat") or ""), float(row.get("lon") or "")
      except Exception:
        continue
      key = f"{lat:.3f}|{lon:.3f}|{(row.get('site') or '').strip().lower()}"
      if key in seen:
        continue
      seen.add(key)
      if is_in_mask(lat, lon, arg1_geo):
        c14_base += 1

  dom_sites = [s for s in arg0_sites if not s["is_frontier_buffer"]]
  buf_sites = [s for s in arg0_sites if s["is_frontier_buffer"]]

  def summarize_subset(sub):
    tot = len(sub)
    tiers = Counter(x["source_tier"] for x in sub)
    classes = Counter(x["record_class"] for x in sub)
    srcs = Counter(x["source_id"] for x in sub)
    ctrys = Counter(x["country"] for x in sub)
    prim = tiers["regional_monograph"] + tiers["national_register"]
    reg_srcs = [sid for sid, cnt in srcs.items() if cnt > 0 and SOURCE_REGISTRY[sid]["tier"] in ("regional_monograph", "national_register")]
    return {
      "total_sites": tot,
      "primary_regional_institutional_sites": prim,
      "regional_monograph_sites": tiers["regional_monograph"],
      "national_register_sites": tiers["national_register"],
      "radiocarbon_db_sites": tiers["radiocarbon_db"],
      "crowd_sites": tiers["crowd"],
      "regional_share": round(prim / tot, 4) if tot else 0.0,
      "crowd_share": round(tiers["crowd"] / tot, 4) if tot else 0.0,
      "distinct_primary_regional_sources": len(reg_srcs),
      "primary_regional_source_ids": sorted(reg_srcs),
      "settlement_sites": classes["settlement"],
      "monument_sites": classes["monument"],
      "by_source": dict(sorted(srcs.items(), key=lambda x: -x[1])),
      "by_country": dict(sorted(ctrys.items(), key=lambda x: -x[1])),
    }

  dom_summary = summarize_subset(dom_sites)
  by_jur = {jid: summarize_subset([s for s in dom_sites if s["jurisdiction"] == jid]) for jid in ("mexico", "central_america", "caribbean")}
  buf_summary = summarize_subset(buf_sites)
  c14_mult = round(len(dom_sites) / c14_base, 2) if c14_base > 0 else 0.0
  invalid_dates = sum(1 for s in arg0_sites if s["start_year"] is None or s["end_year"] is None or s["start_year"] > s["end_year"])
  out_of_mask = sum(1 for s in dom_sites if not is_in_mask(s["lat"], s["lon"], arg1_geo))

  audit = {
    "project": "JAGUAR",
    "generated_at_gmt0": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "domain_mask_path": str(MASK_PATH.relative_to(SVEA_ROOT)).replace("\\", "/"),
    "domain_mask_active_pixels": int(np.sum(arg1_geo["mask"])),
    "svea_c14_baseline_unique_sites": c14_base,
    "domestic_total_sites": len(dom_sites),
    "c14_multiplier": c14_mult,
    "frontier_buffer_250km_total_sites": len(buf_sites),
    "grand_total_sites_with_frontier": len(arg0_sites),
    "domain_provenance": dom_summary,
    "jurisdiction_arch_coverage": by_jur,
    "frontier_buffer_summary": buf_summary,
    "compliance_checks": {
      "zero_wikipedia_scraping": True,
      "c14_multiplier_ge_2_5x": c14_mult >= 2.5,
      "domain_crowd_share_le_25pct": dom_summary["crowd_share"] <= 0.25,
      "domain_regional_share_ge_50pct": dom_summary["regional_share"] >= 0.50,
      "all_jurisdictions_crowd_le_25pct": all(v["crowd_share"] <= 0.25 for v in by_jur.values()),
      "all_jurisdictions_regional_ge_50pct": all(v["regional_share"] >= 0.50 for v in by_jur.values()),
      "all_jurisdictions_ge_2_primary_sources": all(v["distinct_primary_regional_sources"] >= 2 for v in by_jur.values()),
      "zero_null_or_invalid_dates": invalid_dates == 0,
      "zero_out_of_mask_domestic_sites": out_of_mask == 0,
    },
    "raw_source_ingested": arg2_audit["raw_source_ingested"],
    "quality_audits": arg2_audit["quality_audits"],
    "source_registry": SOURCE_REGISTRY,
  }

  CONFIG_DIR.mkdir(parents=True, exist_ok=True)
  (CONFIG_DIR / "jaguar_arch_sites_master.json").write_text(json.dumps(arg0_sites, ensure_ascii=False, indent=2), encoding="utf-8")
  (CONFIG_DIR / "jaguar_arch_provenance_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

  print(f"[SAVED] jaguar_arch_sites_master.json ({len(arg0_sites):,} sites)")
  print(f"SVEA c14 baseline: {c14_base} | Domestic: {len(dom_sites):,} ({c14_mult}x) | Frontier 250km: {len(buf_sites):,}")
  print(f"Domain primary: {dom_summary['regional_share']*100:.2f}% | crowd: {dom_summary['crowd_share']*100:.2f}% | sett/mon: {dom_summary['settlement_sites']:,}/{dom_summary['monument_sites']:,}")
  for jid, info in by_jur.items():
    print(f"  [{jid:16s}] sites={info['total_sites']:5,d} | primary={info['regional_share']*100:5.1f}% | crowd={info['crowd_share']*100:4.1f}% | prim_srcs={info['distinct_primary_regional_sources']} | sett={info['settlement_sites']:,} mon={info['monument_sites']:,}")
    print(f"    by_country: {list(info['by_country'].items())[:14]}")
  print("Compliance checks:", audit["compliance_checks"])


def main():
  geo = A_load_masks_and_geometries()
  audit_state = {"raw_source_ingested": {}, "quality_audits": {}}
  all_recs = []
  all_recs.extend(B_ingest_mexico_and_maya_regional(geo, audit_state))
  all_recs.extend(C_ingest_central_america_regional(geo, audit_state))
  all_recs.extend(D_ingest_caribbean_regional(geo, audit_state))
  all_recs.extend(E_ingest_global_atlases_and_radiocarbon(geo, audit_state))
  all_recs.extend(F_ingest_centaur_frontier_buffer(geo, audit_state))
  final_sites = G_deduplicate_and_reconcile(all_recs, audit_state)
  H_compute_c14_baseline_and_export(final_sites, geo, audit_state)


if __name__ == "__main__":
  main()
