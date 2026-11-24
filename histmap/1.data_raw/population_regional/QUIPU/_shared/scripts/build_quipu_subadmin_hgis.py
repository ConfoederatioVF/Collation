"""Builds ALL 118 Overlapping AD HYDE Sub-Administrative Historical GIS GeoPNG Rasters
(`subadmin_id_<year>.png`, 24-bit RGB integer unit IDs), Longitudinal Metadata
(`subadmin_meta_<year>.json`), Literature-Review Enumeration Exports (`.json` & `.csv`),
and Representative Optical QA Crop PNGs for Operation Viscount Project QUIPU.

HYDE Temporal Coverage (118 AD rasters; strictly covers all 103 required 1500..2025 rasters + 0..1400):
  - Every 100 years: 0, 100, ..., 1500, 1600, 1700 (18 snapshots)
  - Every 10 years: 1710, 1720, ..., 1950 (25 snapshots)
  - Every 1 year: 1951, 1952, ..., 2025 (75 snapshots)

Strict Academic HGIS Z-Index Layering:
  - z = 0.5: HydroBASINS SA Level 4/5 organic watersheds (pre-1500 physical coverage floor)
  - z = 1.0: `atlas_defacto_quipu_cache.json` (STRICTLY fallback ONLY!)
  - z = 2.0: Coastal-complete `atlas_dejure_quipu_cache.json` & `CShapes-2.0` (1886..2019)
  - z = 3.0: `ohm_quipu_polities_cache.geojson` (date-filtered start_date <= yr <= end_date)
  - z = 4.0: Period-authentic sub-administrative HGIS:
      * 0..1400: HydroBASINS L4/L5 + OHM Pre-Inca polities (Moche, Wari, Tiwanaku, Chimu, Lupaca, Cusco, Chanka)
      * 1500: OHM Inca Empire Four Suyos + Cusco + HydroBASINS L4/L5 outside Tawantinsuyu
      * 1600..1810: Werner Stangl HGIS de las Indias (`the_geom.gpkg` LCG provinces/intendancies/audiencias)
      * 1820..1880: OHM Gran Colombia & pre-War of the Pacific borders (Bolivian Antofagasta, Peruvian Tarapaca/Arica)
                    + CONICET 1869 Argentina + republican sub-administrative jurisdictions
      * 1890..1930: Post-War of the Pacific borders + CONICET 1895/1914 Argentina (with Territorios Nacionales)
                    + IPUMS pre-1974 Chilean provinces + pre-1942 Rio Protocol Ecuador
      * 1940..1973: CONICET 1947/1970 Argentina + IPUMS pre-1974 Chilean provinces (25 provinces) + post-1942 Rio Protocol
      * 1974..2006: Post-CONARA 13-region Chile (pre-2007) + CONICET Argentina + contemporary ADM1
      * 2007..2017: Chile 15 regions (Arica y Parinacota & Los Rios added 2007) + Ecuador 24 provinces
      * 2018..2025: Chile 16 regions (Nuble added 2018) + CONICET 2022 Argentina (all 24 provinces incl. Entre Rios)
                    + geoBoundaries ADM1 (COL 33, VEN 25 excl. Essequibo, ECU 24 incl. Galapagos, PER 26,
                      Andean BOL 6 depts, URY 19) + NE10m FLK/SGS (4 subregions)

Zero-Scanline Rasterisation:
  - OpenCV `cv2.fillPoly(..., shift=4)` with local interior-hole subtraction, micro-island pinning,
    and coastal nearest-neighbour snapping strictly inside `quipu_domain_mask.png`.
"""

import csv
import io
import json
import math
import os
import pathlib
import re
import sqlite3
import sys
import unicodedata
import zipfile
from collections import defaultdict

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, distance_transform_edt
import shapefile
import shapely
from shapely import wkb
from shapely.geometry import MultiPolygon, Polygon, box, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

sys.stdout.reconfigure(encoding="utf-8")

GRID_W, GRID_H = 4320, 2160
SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
QUIPU_DIR = SCRIPTS_DIR.parents[1]
POP_REG_DIR = QUIPU_DIR.parent
SVEA_ROOT = POP_REG_DIR.parents[2]

HGIS_ROOT = QUIPU_DIR / "_shared/subadmin_hgis"
RAW_DIR = HGIS_ROOT / "raw_sources"
PARSED_DIR = HGIS_ROOT / "parsed"
RASTER_DIR = HGIS_ROOT / "rasters"
GIS_CACHE_DIR = QUIPU_DIR / "_shared/_gis_cache"
DOMAIN_MASK_PNG = QUIPU_DIR / "_shared/sites_quipu_andes_cone/config/quipu_domain_mask.png"
LAND_AREA_PNG = SVEA_ROOT / "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png"
SUBADMIN_CROPS_DIR = SVEA_ROOT / "tests/subadmin_crops"

RASTER_DIR.mkdir(parents=True, exist_ok=True)
SUBADMIN_CROPS_DIR.mkdir(parents=True, exist_ok=True)

NE10_ADM0_JSON = POP_REG_DIR / "_shared/_gis_cache/ne_10m_admin_0_countries.geojson"
HYBAS_L4_SHP = POP_REG_DIR / "PRETA/_shared/_gis_cache/hydrobasins/hybas_sa_lev04_v1c.shp"
OHM_CACHE_JSON = GIS_CACHE_DIR / "ohm_quipu_polities_cache.geojson"
HGIS_GPKG = RAW_DIR / "hgis_indias/the_geom.gpkg"
GB_DIR = RAW_DIR / "geoboundaries"
CONICET_ZIP = RAW_DIR / "national_hgis/conicet_arg_1869_2022/Base_deptos_1869-2022.zip"
IPUMS_DIR = RAW_DIR / "national_hgis/ipums_international"
ENUM_JSON = RAW_DIR / "eda_part3_enumerations.json"
PRETA_BOL_JSON5 = POP_REG_DIR / "PRETA/3.post_independence/2.bolivia_after_independence/bolivia_after_independence.json5"

QUIPU_CLIP_BOX = box(-95.0, -59.8, -24.0, 14.0)
ARG_TDF_CLIP_BOX = box(-76.0, -56.0, -63.0, -52.0)
CHL_CLIP_BOX = box(-95.0, -56.5, -66.0, -17.0)
ANDEAN_BOL_DEPTS = {"Chuquisaca", "Cochabamba", "La Paz", "Oruro", "Potosí", "Tarija"}

ALL_HYDE_AD_YEARS = (
  list(range(0, 1701, 100))
  + list(range(1710, 1951, 10))
  + list(range(1951, 2026, 1))
)

QA_CROP_YEARS = {1500, 1600, 1780, 1820, 1870, 1890, 1920, 1950, 1970, 2000, 2025}

CONICET_PROV_NAMES = {
  "02": "Ciudad Autónoma de Buenos Aires",
  "06": "Buenos Aires",
  "10": "Catamarca",
  "14": "Córdoba",
  "18": "Corrientes",
  "22": "Chaco",
  "26": "Chubut",
  "30": "Entre Ríos",
  "34": "Formosa",
  "38": "Jujuy",
  "42": "La Pampa",
  "46": "La Rioja",
  "50": "Mendoza",
  "54": "Misiones",
  "58": "Neuquén",
  "62": "Río Negro",
  "66": "Salta",
  "70": "San Juan",
  "74": "San Luis",
  "78": "Santa Cruz",
  "82": "Santa Fe",
  "86": "Santiago del Estero",
  "90": "Tucumán",
  "94": "Tierra del Fuego",
  "99": "Territorio Nacional de Los Andes",
}


def norm_key(arg0_text):
  if not arg0_text:
    return ""
  s = str(arg0_text)
  try:
    if "Ã" in s or "Â" in s:
      s = s.encode("latin1").decode("utf-8")
  except Exception:
    pass
  s = re.sub(r"\([^)]*\)", " ", s)
  s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
  return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def fix_mojibake(arg0_text):
  s = str(arg0_text or "")
  try:
    if "Ã" in s or "Â" in s:
      return s.encode("latin1").decode("utf-8")
  except Exception:
    pass
  return s


def slugify(arg0_text):
  return re.sub(r"[^a-z0-9]+", "_", norm_key(arg0_text)).strip("_")


def repair_geom(arg0_geom, arg1_min_area=1e-7):
  if arg0_geom is None or arg0_geom.is_empty:
    return None
  try:
    g = make_valid(arg0_geom) if not arg0_geom.is_valid else arg0_geom
    if g.is_empty:
      return None
    if g.geom_type == "GeometryCollection":
      polys = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon") and not p.is_empty]
      if not polys:
        return None
      g = unary_union(polys)
    if g.geom_type not in ("Polygon", "MultiPolygon"):
      return None
    g = shapely.set_precision(g, 1e-4)
    g = make_valid(g)
    if g.geom_type == "GeometryCollection":
      polys = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon") and not p.is_empty]
      if not polys:
        return None
      g = unary_union(polys)
    if g.geom_type == "MultiPolygon":
      parts = [p for p in g.geoms if not p.is_empty and p.area >= arg1_min_area]
      if not parts:
        parts = [p for p in g.geoms if not p.is_empty]
      if not parts:
        return None
      return MultiPolygon(parts) if len(parts) > 1 else parts[0]
    return g if (g.geom_type == "Polygon" and not g.is_empty) else None
  except Exception:
    try:
      g = arg0_geom.buffer(0)
      return g if (g is not None and not g.is_empty and g.geom_type in ("Polygon", "MultiPolygon")) else None
    except Exception:
      return None


def safe_union(arg0_geoms):
  gs = [repair_geom(g) for g in arg0_geoms if g is not None and not g.is_empty]
  gs = [g for g in gs if g is not None and not g.is_empty]
  if not gs:
    return None
  return repair_geom(unary_union(gs))


def safe_clip(arg0_geom, arg1_clip):
  if arg0_geom is None or arg1_clip is None:
    return None
  try:
    return repair_geom(arg0_geom.intersection(arg1_clip))
  except Exception:
    g0, g1 = repair_geom(arg0_geom), repair_geom(arg1_clip)
    return repair_geom(g0.intersection(g1)) if (g0 is not None and g1 is not None) else None


def iter_polys(arg0_geom):
  if arg0_geom is None or arg0_geom.is_empty:
    return
  if arg0_geom.geom_type == "Polygon":
    yield arg0_geom
  elif arg0_geom.geom_type in ("MultiPolygon", "GeometryCollection"):
    for p in arg0_geom.geoms:
      if p.geom_type == "Polygon" and not p.is_empty:
        yield p
      elif p.geom_type == "MultiPolygon":
        for sp in p.geoms:
          if not sp.is_empty:
            yield sp


def load_land_area():
  raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  u32 = raw.reshape(-1, 4).copy().view(">u4").reshape((GRID_H, GRID_W)).astype(np.float64)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape((GRID_H, GRID_W)).astype(np.float64)
  if np.nanmax(f32) > 1.0 and np.nanmax(f32) < 500.0 and np.isfinite(f32[1080, 1500]):
    la = np.where(np.isfinite(f32) & (f32 > 0), f32, 0.0)
  else:
    med = float(np.median(u32[u32 > 0])) if (u32 > 0).any() else 0.0
    if 1.0 <= med <= 500.0:
      la = u32
    else:
      lats = 90.0 - (np.arange(GRID_H) + 0.5) / 12.0
      cell = (111.32 / 12.0) * (111.32 / 12.0) * np.cos(np.radians(lats))
      la = np.where(u32 > 0, cell[:, None], 0.0)
  # Ensure positive spherical fallback area for micro-islands inside domain
  lats = 90.0 - (np.arange(GRID_H) + 0.5) / 12.0
  cell_km2 = ((111.32 / 12.0) * (111.32 / 12.0) * np.cos(np.radians(lats)))[:, None]
  return np.where(la > 0, la, cell_km2)


def parse_year(arg0_val, arg1_default):
  s = str(arg0_val or "").strip()
  if not s:
    return arg1_default
  m = re.match(r"^(-?\d{1,4})", s)
  return int(m.group(1)) if m else arg1_default


def parse_gpkg_wkb(arg0_blob):
  if not arg0_blob:
    return None
  eb = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get((arg0_blob[3] >> 1) & 0x07, 0)
  try:
    return repair_geom(wkb.loads(arg0_blob[8 + eb:]))
  except Exception:
    return None


def interp_series(arg0_series, arg1_yr):
  """Log-linear interpolation on [[yr, val], ...] sorted list."""
  if not arg0_series:
    return None
  pts = sorted([(int(y), float(v)) for y, v in arg0_series if v is not None], key=lambda x: x[0])
  if not pts:
    return None
  if arg1_yr <= pts[0][0]:
    return pts[0][1]
  if arg1_yr >= pts[-1][0]:
    return pts[-1][1]
  for i in range(len(pts) - 1):
    y0, v0 = pts[i]
    y1, v1 = pts[i + 1]
    if y0 <= arg1_yr <= y1:
      if y1 == y0:
        return v0
      t = (arg1_yr - y0) / float(y1 - y0)
      if v0 > 0 and v1 > 0:
        return math.exp(math.log(v0) * (1.0 - t) + math.log(v1) * t)
      return v0 * (1.0 - t) + v1 * t
  return pts[-1][1]


def get_regime_key(arg0_yr):
  """Maps every overlapping AD HYDE year (0..2025) to its non-anachronistic historical boundary regime."""
  yr = int(arg0_yr)
  if yr <= 400:
    return 0
  if yr <= 900:
    return 600
  if yr <= 1300:
    return 1100
  if yr == 1400:
    return 1400
  if yr == 1500:
    return 1500
  if yr == 1600:
    return 1600
  if yr <= 1770:
    return 1750
  if yr <= 1810:
    return 1780
  if yr <= 1830:
    return 1820
  if yr <= 1880:
    return 1870
  if yr <= 1910:
    return 1890
  if yr <= 1930:
    return 1920
  if yr <= 1954:
    return 1950
  if yr <= 1973:
    return 1970
  if yr <= 2006:
    return 2000
  if yr <= 2017:
    return 2010
  return 2025


def load_conicet_year(arg0_zip_path, arg1_shp_name, arg2_encoding="utf-8"):
  """Dissolves a CONICET Argentina census shapefile into provincial polygons."""
  by_prov = defaultdict(list)
  with zipfile.ZipFile(arg0_zip_path) as zf:
    sf = shapefile.Reader(
      shp=io.BytesIO(zf.read(arg1_shp_name)),
      dbf=io.BytesIO(zf.read(arg1_shp_name[:-4] + ".dbf")),
      encoding=arg2_encoding,
    )
    flds = [f[0] for f in sf.fields[1:]]
    for i, rec in enumerate(sf.records()):
      d = dict(zip(flds, rec))
      if "cpr" in d and "jur" in d:
        pc = str(d["cpr"]).zfill(2)
        pnm = str(d["jur"]).strip()
        if pnm.startswith("Tierra del Fuego"):
          pnm = "Tierra del Fuego"
      else:
        pc = str(d.get("PROV_COD") or "").strip().zfill(2)
        pnm = CONICET_PROV_NAMES.get(pc, f"Provincia {pc}")
      g = repair_geom(shape(sf.shape(i).__geo_interface__))
      if g is None:
        continue
      if pc == "94" or "Tierra del Fuego" in pnm:
        g = safe_clip(g, ARG_TDF_CLIP_BOX)
        if g is None:
          continue
      by_prov[(pc, pnm)].append(g)
  out = {}
  for (pc, pnm), gs in by_prov.items():
    u = safe_union(gs)
    if u is not None:
      out[pnm] = u
  return out


def load_ipums_chile(arg0_zip_name):
  """Loads IPUMS pre-1974 Chilean provinces clipped cleanly to lon >= -95 and lat >= -56.5."""
  out = {}
  with zipfile.ZipFile(IPUMS_DIR / arg0_zip_name) as zf:
    shpn = [n for n in zf.namelist() if n.endswith(".shp")][0]
    sf = shapefile.Reader(
      shp=io.BytesIO(zf.read(shpn)),
      dbf=io.BytesIO(zf.read(shpn[:-4] + ".dbf")),
      encoding="latin1",
    )
    flds = [f[0] for f in sf.fields[1:]]
    for i, rec in enumerate(sf.records()):
      d = dict(zip(flds, rec))
      nm = fix_mojibake(str(d.get("ADMIN_NAME") or f"Prov_{i}")).strip()
      g = repair_geom(shape(sf.shape(i).__geo_interface__))
      if g is None:
        continue
      g = safe_clip(g, CHL_CLIP_BOX)
      if g is not None:
        out[nm] = safe_union([out[nm], g]) if nm in out else g
  return out


def load_all_sources():
  """Loads all authentic QUIPU HGIS & GIS sources."""
  print("[1] Loading QUIPU HGIS sources (HydroBASINS, OHM, HGIS de las Indias, CONICET, IPUMS, CShapes, geoBoundaries, NE10m, Naissance caches)...", flush=True)
  src = {}

  # 1. Contemporary ADM1 from geoBoundaries + CONICET 2022 + NE10m FLK/SGS
  adm1 = {}
  for iso in ["COL", "VEN", "ECU", "PER", "BOL", "CHL", "URY"]:
    with open(GB_DIR / f"{iso}_ADM1.geojson", "r", encoding="utf-8") as fh:
      gj = json.load(fh)
    units = {}
    for ft in gj["features"]:
      nm = fix_mojibake(ft["properties"].get("shapeName", ""))
      g = repair_geom(shape(ft["geometry"]))
      if g is None:
        continue
      if iso == "CHL":
        g = safe_clip(g, CHL_CLIP_BOX)
        if g is None:
          continue
      elif iso == "BOL" and nm not in ANDEAN_BOL_DEPTS:
        continue
      units[nm] = safe_union([units[nm], g]) if nm in units else g
    adm1[iso] = units

  adm1["ARG"] = load_conicet_year(CONICET_ZIP, "Base deptos 1869-2022/Departamentos_2022_INDEC.shp", "latin1")

  # FLK / SGS 4 geographic units
  flk_sgs = {}
  with open(NE10_ADM0_JSON, "r", encoding="utf-8") as fh:
    ne0 = json.load(fh)
  for ft in ne0["features"]:
    p = ft["properties"]
    iso = p.get("ADM0_A3") or p.get("ISO_A3") or ""
    if iso == "FLK":
      g = repair_geom(shape(ft["geometry"]))
      parts = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
      flk_sgs["East Falkland"] = safe_union([pt for pt in parts if pt.centroid.x >= -59.55])
      flk_sgs["West Falkland"] = safe_union([pt for pt in parts if pt.centroid.x < -59.55])
    elif iso == "SGS":
      g = repair_geom(shape(ft["geometry"]))
      parts = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
      flk_sgs["South Georgia"] = safe_union([pt for pt in parts if pt.centroid.x <= -34.0])
      flk_sgs["South Sandwich Islands"] = safe_union([pt for pt in parts if pt.centroid.x > -34.0])
  adm1["FLK_SGS"] = flk_sgs
  src["adm1"] = adm1

  # 2. Historical CONICET Argentina (1869, 1895, 1914, 1947, 1970)
  src["conicet"] = {
    1869: load_conicet_year(CONICET_ZIP, "Base deptos 1869-2022/Departamentos_1869.shp", "latin1"),
    1895: load_conicet_year(CONICET_ZIP, "Base deptos 1869-2022/Departamentos_1895.shp", "latin1"),
    1914: load_conicet_year(CONICET_ZIP, "Base deptos 1869-2022/Departamentos_1914.shp", "latin1"),
    1947: load_conicet_year(CONICET_ZIP, "Base deptos 1869-2022/Departamentos_1947_2026v2.shp", "latin1"),
    1970: load_conicet_year(CONICET_ZIP, "Base deptos 1869-2022/Departamentos_1970.shp", "latin1"),
  }
  print(f"  CONICET Argentina loaded: { {y: len(v) for y, v in src['conicet'].items()} }", flush=True)

  # 3. Historical IPUMS pre-1974 Chile (1960 & 1970)
  src["ipums_chl"] = {
    1960: load_ipums_chile("geo1_cl1960.zip"),
    1970: load_ipums_chile("geo1_cl1970.zip"),
  }
  print(f"  IPUMS pre-1974 Chile loaded: 1960={len(src['ipums_chl'][1960])}, 1970={len(src['ipums_chl'][1970])}", flush=True)

  # 4. HydroBASINS SA Level 4 organic catchments (clipped to QUIPU_CLIP_BOX; pixel-clipped to quipu_domain_mask at rasterisation)
  sf4 = shapefile.Reader(str(HYBAS_L4_SHP))
  flds4 = [f[0] for f in sf4.fields[1:]]
  hybas4 = []
  for i, rec in enumerate(sf4.records()):
    d = dict(zip(flds4, rec))
    bb = sf4.shape(i).bbox
    if bb[2] < -95.0 or bb[0] > -24.0 or bb[3] < -60.0 or bb[1] > 14.0:
      continue
    g = safe_clip(shape(sf4.shape(i).__geo_interface__), QUIPU_CLIP_BOX)
    if g is not None and g.area > 0.005:
      hybas4.append((str(d["PFAF_ID"]), g))
  src["hybas4"] = hybas4
  print(f"  HydroBASINS L4 loaded: {len(hybas4)} watersheds", flush=True)

  # 5. OHM Historical Polities Cache (fast box clip; exact mask clipping happens at rasterisation!)
  ohm_feats = []
  with open(OHM_CACHE_JSON, "r", encoding="utf-8") as fh:
    ohm_gj = json.load(fh)
  for ft in ohm_gj["features"]:
    p = ft["properties"]
    nm = str(p.get("name") or "")
    sd = parse_year(p.get("start_date"), -99999)
    ed = parse_year(p.get("end_date"), 99999)
    g = safe_clip(shape(ft["geometry"]), QUIPU_CLIP_BOX)
    if g is not None and g.area > 0.005:
      ohm_feats.append({"name": nm, "y0": sd, "y1": ed, "al": str(p.get("admin_level") or ""), "geom": g})
  src["ohm"] = ohm_feats
  print(f"  OHM polities loaded: {len(ohm_feats)}", flush=True)

  # 6. Werner Stangl HGIS de las Indias (the_geom.gpkg LCG provinces)
  hgis_lcg = defaultdict(list)
  con = sqlite3.connect(str(HGIS_GPKG))
  for fid, blob, reg, prov in con.execute("SELECT fid, geom, Region, Province_1 FROM LCG"):
    if reg not in ("NGR", "QUI", "VEN", "PER", "CHA", "CHL", "RPL"):
      continue
    if prov in ("Tierra Firme", "Trinidad", "Paraguay", "Chiquitos", "Moxos"):
      continue
    g = parse_gpkg_wkb(blob)
    if g is not None and g.intersects(QUIPU_CLIP_BOX):
      gc = safe_clip(g, QUIPU_CLIP_BOX)
      if gc is not None and gc.area > 0.002:
        hgis_lcg[(reg, str(prov or reg))].append(gc)
  con.close()
  src["hgis_provs"] = {k: safe_union(v) for k, v in hgis_lcg.items() if safe_union(v) is not None}
  print(f"  HGIS de las Indias SA provinces loaded: {len(src['hgis_provs'])}", flush=True)

  # 7. CShapes 2.0 (1886..2019)
  cshapes = []
  with open(PARSED_DIR / "cshapes_quipu_cache.json", "r", encoding="utf-8") as fh:
    cs_gj = json.load(fh)
  for ft in cs_gj.get("features", []):
    p = ft["properties"]
    g = safe_clip(shape(ft["geometry"]), QUIPU_CLIP_BOX)
    if g is not None and g.area > 0.002:
      cshapes.append({
        "name": str(p.get("cntry_name") or ""),
        "y0": int(p.get("gwsyear") or 1886),
        "y1": int(p.get("gweyear") or 2019),
        "geom": g,
      })
  src["cshapes"] = cshapes

  # 8. Coastal-complete atlas_dejure (z=2) & atlas_defacto (STRICTLY z=1 fallback!)
  def load_nc(fn):
    raw = json.load(open(PARSED_DIR / fn, "r", encoding="utf-8"))
    out = {}
    for yk, recs in raw.items():
      flist = []
      for r in recs:
        g = safe_clip(shape(r["geometry"]), QUIPU_CLIP_BOX)
        if g is not None and g.area > 0.002:
          flist.append({"id": r.get("id", ""), "name": r.get("name", ""), "geom": g})
      out[int(yk)] = flist
    return out

  src["atlas_defacto"] = load_nc("atlas_defacto_quipu_cache.json")
  src["atlas_dejure"] = load_nc("atlas_dejure_quipu_cache.json")
  print(f"  Naissance caches loaded: defacto={len(src['atlas_defacto'])} yrs | dejure={len(src['atlas_dejure'])} yrs | cshapes={len(cshapes)}", flush=True)

  # 9. Chapter JSON5 verified enumerations index (already harmonised from eda_part3_enumerations.json & PRETA Bolivia!)
  enum_index = {}  # (country_iso, norm_name) -> [[yr, pop], ...]
  chapter_files = [
    ("COL", "3.post_independence/1.colombia_after_independence/colombia_after_independence.json5"),
    ("VEN", "3.post_independence/2.venezuela_after_independence/venezuela_after_independence.json5"),
    ("ECU", "3.post_independence/3.ecuador_after_independence/ecuador_after_independence.json5"),
    ("PER", "3.post_independence/4.peru_after_independence/peru_after_independence.json5"),
    ("BOL", "3.post_independence/5.andean_bolivia_independence/andean_bolivia_independence.json5"),
    ("CHL", "3.post_independence/6.chile_after_independence/chile_after_independence.json5"),
    ("ARG", "3.post_independence/7.argentina_after_independence/argentina_after_independence.json5"),
    ("URY", "3.post_independence/8.uruguay_after_independence/uruguay_after_independence.json5"),
    ("FLK_SGS", "3.post_independence/9.falklands_south_atlantic/falklands_south_atlantic.json5"),
  ]
  for iso, relp in chapter_files:
    ch = json.load(open(QUIPU_DIR / relp, "r", encoding="utf-8"))
    for rid, rmeta in ch["regions"].items():
      ser = sorted([[int(y), int(v)] for y, v in rmeta["population"].items()])
      enum_index[(iso, norm_key(rmeta["name"]))] = ser
  src["enum_index"] = enum_index

  # Also load raw eda_part3_enumerations.json for pre-1974 Chilean provinces & colonial intendancies!
  with open(ENUM_JSON, "r", encoding="utf-8") as fh:
    e3 = json.load(fh)
  src["e3"] = e3
  return src


def nearest_cache_year(arg0_cache, arg1_yr):
  yrs = sorted(arg0_cache.keys())
  return min(yrs, key=lambda y: abs(y - int(arg1_yr)))


def build_chile_13_regions(arg0_chl16):
  """Merges post-2007/2018 Chilean regions back into the 13 historical CONARA regions (1974-2006)."""
  out = {}
  merges = {
    "Región de Arica y Parinacota": "Región de Tarapacá",
    "Región de Los Ríos": "Región de Los Lagos",
    "Región de Ñuble": "Región del Bío-Bío",
  }
  grouped = defaultdict(list)
  for nm, g in arg0_chl16.items():
    tgt = merges.get(nm, nm)
    grouped[tgt].append(g)
  for nm, gs in grouped.items():
    u = safe_union(gs)
    if u is not None:
      out[nm] = u
  return out


def build_chile_15_regions(arg0_chl16):
  """Merges 2018 Ñuble back into Bío-Bío for 2007-2017."""
  out = {}
  grouped = defaultdict(list)
  for nm, g in arg0_chl16.items():
    tgt = "Región del Bío-Bío" if nm == "Región de Ñuble" else nm
    grouped[tgt].append(g)
  for nm, gs in grouped.items():
    u = safe_union(gs)
    if u is not None:
      out[nm] = u
  return out


def build_ecuador_22_provinces(arg0_ecu24):
  """Merges post-2007 Santa Elena -> Guayas and Santo Domingo -> Pichincha for 1974-2006."""
  out = {}
  merges = {
    "Santa Elena": "Guayas",
    "Santo Domingo de los Tsáchilas": "Pichincha",
  }
  grouped = defaultdict(list)
  for nm, g in arg0_ecu24.items():
    tgt = merges.get(nm, nm)
    grouped[tgt].append(g)
  for nm, gs in grouped.items():
    u = safe_union(gs)
    if u is not None:
      out[nm] = u
  return out


def match_chl_pre1974_series(arg0_e3, arg1_prov_name):
  """Extracts documented 1895..1970 census trajectory for a pre-1974 Chilean province."""
  chl_e = arg0_e3["post_independence_censuses"]["chile"]
  nk = norm_key(arg1_prov_name)
  pts = {}
  for yr, src_d in [(1895, chl_e["census_1895_provinces"]), (1907, chl_e["census_1907_provinces"]), (1960, chl_e["census_1960_provinces"])]:
    for k, v in src_d.items():
      if norm_key(k) == nk and isinstance(v, (int, float)):
        pts[yr] = int(v)
  for k, pdict in chl_e["statoids_provinces_1910_1970"].items():
    if norm_key(k) == nk and isinstance(pdict, dict):
      for yk, yr in [("1910_est", 1910), ("1940", 1940), ("1952", 1952), ("1970", 1970)]:
        if isinstance(pdict.get(yk), (int, float)) and pdict[yk] > 0:
          pts[yr] = int(pdict[yk])
  return [[y, pts[y]] for y in sorted(pts.keys())]


def match_colonial_hgis_series(arg0_e3, arg1_reg, arg2_prov):
  """Matches a Werner Stangl HGIS de las Indias province to verified colonial enumerations."""
  ce = arg0_e3["colonial_enumerations"]
  pnk = norm_key(arg2_prov)
  if arg1_reg == "PER":
    gt = ce["peru_gil_de_taboada_1791_1795"]["mercurio_peruano_vollmer_1967"]
    for k, rec in gt.items():
      if norm_key(k) == pnk or (pnk == "cuzco" and norm_key(k) == "cusco"):
        return [[1795, int(rec["total"])]]
    if pnk == "puno":
      return [[1796, int(ce["peru_gil_de_taboada_1791_1795"]["puno_1796_reincorporation"]["population"])]]
  elif arg1_reg == "NGR":
    ng = ce["new_granada_carlos_iii_1778"]["provinces_igac_tovar_1778"]
    for k, rec in ng.items():
      if norm_key(k) == pnk or (pnk == "santa fe" and norm_key(k) == "santafe") or (pnk == "llanos" and "llanos" in norm_key(k)):
        if "population" in rec:
          return [[1778, int(rec["population"])]]
  elif arg1_reg == "QUI":
    if pnk == "guayaquil":
      return [[1780, 30000]]
    if pnk == "quito":
      return [[1780, 320000]]
  elif arg1_reg == "VEN":
    vh = ce["venezuela_marti_humboldt_1771_1800"]["humboldt_1800_and_brito_figueroa_provinces"]
    if pnk == "caracas":
      return [[1787, 333010], [1800, 450000]]
    if pnk == "cumana":
      return [[1800, 110000]]
    if pnk == "guayana":
      return [[1800, 40000]]
    if "margarita" in pnk:
      return [[1800, 18000]]
    if pnk == "maracaibo":
      return [[1800, 72000]]
  elif arg1_reg == "CHA":
    if pnk == "la paz":
      return [[1796, 225000]]
    if pnk == "potosi":
      return [[1796, 135000]]
    if pnk == "cochabamba":
      return [[1796, 135000]]
    if pnk == "charcas":
      return [[1796, 100000]]
  elif arg1_reg == "CHL":
    if pnk == "santiago":
      return [[1778, 240748], [1813, 465000]]
    if pnk == "concepcion":
      return [[1778, 175000], [1813, 250000]]
    if pnk == "chiloe":
      return [[1778, 25000], [1813, 36000]]
  elif arg1_reg == "RPL":
    if pnk == "buenos aires":
      return [[1778, 58000]]
    if pnk == "tucuman":
      return [[1778, 138000]]
    if pnk == "cuyo":
      return [[1778, 23411]]
    if "banda oriental" in pnk:
      return [[1778, 15000]]
  return []


def build_regime_units(arg0_reg_yr, arg1_src):
  """Constructs strictly non-anachronistic z-indexed sub-administrative units for arg0_reg_yr."""
  reg_yr = int(arg0_reg_yr)
  units = []
  next_id = [1]

  def add_unit(code, name, country, geom, series, source, is_direct, priority):
    g = repair_geom(geom)
    if g is None:
      return
    uid = next_id[0]
    next_id[0] += 1
    units.append({
      "id": uid,
      "code": str(code),
      "name": str(name),
      "country": str(country),
      "geom": g,
      "series": series if series else [],
      "source": str(source),
      "is_direct_census": bool(is_direct and series),
      "priority": float(priority),
    })

  # =========================================================================
  # LAYER z = 1.5 (Pre-Columbian <= 1500): HydroBASINS L4 organic catchments
  # (sits cleanly above z=1.0 atlas_defacto fallback, below z=2.0 atlas_dejure & z=3.0+ OHM)
  # =========================================================================
  if reg_yr <= 1500:
    for pf, g in arg1_src["hybas4"]:
      add_unit(f"HB4_{pf}", f"HydroBASINS L4 {pf}", "PRE_COLUMBIAN", g, [], "HydroBASINS_SA_L4", False, priority=1.5)

  # =========================================================================
  # LAYER z = 1.0 (STRICTLY LOWEST FALLBACK ONLY!): atlas_defacto_quipu_cache.json
  # =========================================================================
  df_y = nearest_cache_year(arg1_src["atlas_defacto"], reg_yr)
  for idx, r in enumerate(arg1_src["atlas_defacto"].get(df_y, [])):
    add_unit(f"DEF_{reg_yr}_{idx}", r["name"], "FALLBACK", r["geom"], [], f"atlas_defacto_fallback_{df_y}", False, priority=1.0)

  # =========================================================================
  # LAYER z = 2.0: Coastal-complete atlas_dejure & CShapes 2.0 (1886..2019)
  # =========================================================================
  dj_y = nearest_cache_year(arg1_src["atlas_dejure"], reg_yr)
  for idx, r in enumerate(arg1_src["atlas_dejure"].get(dj_y, [])):
    add_unit(f"DEJ_{reg_yr}_{idx}", r["name"], "DEJURE", r["geom"], [], f"atlas_dejure_{dj_y}", False, priority=2.0)

  if reg_yr >= 1886:
    cs_y = min(2019, reg_yr)
    for idx, cs in enumerate(arg1_src["cshapes"]):
      if cs["y0"] <= cs_y <= cs["y1"]:
        add_unit(f"CSH_{reg_yr}_{idx}", cs["name"], cs["name"], cs["geom"], [], f"CShapes_2_0_{cs_y}", False, priority=2.2)

  # =========================================================================
  # LAYER z = 3.0: OHM Historical Polities (strictly date-filtered!)
  # =========================================================================
  for idx, ft in enumerate(arg1_src["ohm"]):
    if ft["y0"] <= reg_yr <= ft["y1"]:
      # Skip non-QUIPU empires like New Spain / Brazil / Portugal / Dutch / British Guiana
      nm_low = ft["name"].lower()
      if any(skip in nm_low for skip in ("new spain", "brazil", "portugal", "guiana", "suriname", "barbados", "trinidad", "windward", "curaçao", "panama", "paraguay", "united states")):
        continue
      # Keep Inca Empire overarching polity below its 4 Suyos + Cusco
      prio = 3.0 if nm_low == "inca empire" else (3.6 if nm_low in ("chinchaysuyo", "antisuyo", "contisuyo", "collasuyo") else (3.8 if nm_low == "cuzco" and reg_yr == 1500 else 3.1))
      add_unit(f"OHM_{reg_yr}_{idx}_{slugify(ft['name'])[:18]}", ft["name"], "OHM_HISTORICAL", ft["geom"], [], f"OHM_{ft['y0']}_{ft['y1']}", False, priority=prio)

  # =========================================================================
  # LAYER z = 4.0: Period-Specific High-Resolution Sub-Administrative HGIS
  # =========================================================================
  adm1 = arg1_src["adm1"]
  enum_idx = arg1_src["enum_index"]

  # Pre-Columbian Era (0..1500): strictly HydroBASINS L4 + atlas_dejure + OHM (Moche/Wari/Tiwanaku/Chimu/Inca 4 Suyos)
  if reg_yr <= 1500:
    return units

  # A. Colonial Era (1600..1810): Werner Stangl HGIS de las Indias (the_geom.gpkg LCG!)
  if 1600 <= reg_yr <= 1810:
    for (reg, prov), g in sorted(arg1_src["hgis_provs"].items()):
      ser = match_colonial_hgis_series(arg1_src["e3"], reg, prov)
      add_unit(
        f"HGIS_{reg}_{slugify(prov)}_{reg_yr}",
        f"{prov} ({reg})",
        f"Spanish_America_{reg}",
        g, ser,
        f"HGIS_de_las_Indias_{reg_yr}",
        bool(ser),
        priority=4.2,
      )
    if reg_yr >= 1764:
      for nm, g in sorted(adm1["FLK_SGS"].items()):
        ser = enum_idx.get(("FLK_SGS", norm_key(nm)), [])
        add_unit(f"FLK_{slugify(nm)}_{reg_yr}", nm, "Falkland Islands & South Atlantic", g, ser, "NE10m_FLK_SGS", bool(ser), priority=4.3)
    return units

  # B. Early Independence & Pre-War of the Pacific (1820..1880)
  if 1820 <= reg_yr <= 1880:
    # 1820: Gran Colombia (OHM 1820 at z=3.1) + HGIS provincial subdivisions for COL/VEN/ECU/PER/BOL/CHL/URY
    if reg_yr == 1820:
      for (reg, prov), g in sorted(arg1_src["hgis_provs"].items()):
        ser = match_colonial_hgis_series(arg1_src["e3"], reg, prov)
        add_unit(f"IND_{reg}_{slugify(prov)}_1820", f"{prov} ({reg})", f"Early_Republic_{reg}", g, ser, "HGIS_Indias_Independence_1820", bool(ser), priority=4.1)
    else:
      # 1870: CONICET 1869 Argentina (14 provinces + Indigenous Patagonia/Chaco territories)
      for nm, g in sorted(arg1_src["conicet"][1869].items()):
        ser = enum_idx.get(("ARG", norm_key(nm)), [])
        add_unit(f"ARG1869_{slugify(nm)}", nm, "Argentina", g, ser, "CONICET_Argentina_1869", bool(ser), priority=4.4)
      # Pre-1883 Bolivia (incl. Antofagasta Litoral!), Pre-1883 Peru (incl. Tarapaca/Arica!), Pre-1883 Chile via OHM envelopes!
      ohm_1870_bol = safe_union([f["geom"] for f in arg1_src["ohm"] if f["name"] == "Bolivia" and f["y0"] <= 1870 <= f["y1"]])
      ohm_1870_per = safe_union([f["geom"] for f in arg1_src["ohm"] if f["name"] == "Peru" and f["y0"] <= 1870 <= f["y1"]])
      ohm_1870_chl = safe_union([f["geom"] for f in arg1_src["ohm"] if f["name"] == "Chile" and f["y0"] <= 1870 <= f["y1"]])
      # Clip Bolivian Antofagasta litoral cleanly from CHL Antofagasta if OHM Bolivia covers it
      if ohm_1870_bol is not None:
        g_litoral = safe_clip(adm1["CHL"].get("Región de Antofagasta"), ohm_1870_bol)
        if g_litoral is not None and g_litoral.area > 0.05:
          add_unit("BOL1870_litoral_antofagasta", "Departamento del Litoral (Antofagasta, Bolivia)", "Bolivia", g_litoral, [[1870, 15000]], "OHM_Pre1883_Bolivian_Litoral", True, priority=4.5)
      if ohm_1870_per is not None:
        for chl_n in ["Región de Tarapacá", "Región de Arica y Parinacota"]:
          g_tp = safe_clip(adm1["CHL"].get(chl_n), ohm_1870_per)
          if g_tp is not None and g_tp.area > 0.05:
            add_unit(f"PER1870_{slugify(chl_n)}", f"{chl_n.replace('Región de ', '')} (Peru pre-1883)", "Peru", g_tp, [[1876, 38225]], "OHM_Pre1883_Peruvian_Tarapaca_Arica", True, priority=4.5)
      # Pre-1974 Chilean provinces clipped to pre-1883 OHM Chile (excludes Bolivian Antofagasta & Peruvian Tarapaca!)
      for pnm, g in sorted(arg1_src["ipums_chl"][1960].items()):
        if norm_key(pnm) in ("tarapaca", "antofagasta"):
          continue
        gc = safe_clip(g, ohm_1870_chl) if ohm_1870_chl is not None else g
        if gc is not None:
          ser = match_chl_pre1974_series(arg1_src["e3"], pnm)
          add_unit(f"CHL1870_{slugify(pnm)}", pnm, "Chile", gc, ser, "IPUMS_Chile_Pre1883_Clipped", bool(ser), priority=4.3)
      # Andean Bolivia, Peru, Colombia, Venezuela, Ecuador, Uruguay ADM1
      for iso, cname in [("BOL", "Bolivia"), ("PER", "Peru"), ("COL", "Colombia"), ("VEN", "Venezuela"), ("ECU", "Ecuador"), ("URY", "Uruguay")]:
        for nm, g in sorted(adm1[iso].items()):
          ser = enum_idx.get((iso, norm_key(nm)), [])
          add_unit(f"{iso}1870_{slugify(nm)}", nm, cname, g, ser, f"geoBoundaries_ADM1_{iso}_1870", bool(ser), priority=4.2)

    for nm, g in sorted(adm1["FLK_SGS"].items()):
      ser = enum_idx.get(("FLK_SGS", norm_key(nm)), [])
      add_unit(f"FLK_{slugify(nm)}_{reg_yr}", nm, "Falkland Islands & South Atlantic", g, ser, "NE10m_FLK_SGS", bool(ser), priority=4.5)
    return units

  # C. Post-War of the Pacific to Pre-CONARA Reform (1890..1973)
  if 1890 <= reg_yr <= 1973:
    # Argentina: exact period CONICET shapefile!
    arg_yr = 1895 if reg_yr == 1890 else (1914 if reg_yr == 1920 else (1947 if reg_yr == 1950 else 1970))
    for nm, g in sorted(arg1_src["conicet"][arg_yr].items()):
      ser = enum_idx.get(("ARG", norm_key(nm)), [])
      add_unit(f"ARG{arg_yr}_{slugify(nm)}", nm, "Argentina", g, ser, f"CONICET_Argentina_{arg_yr}", bool(ser), priority=4.4)

    # Chile: exact IPUMS pre-1974 25 historical provinces (NEVER post-1974 CONARA regions!)
    chl_yr = 1960 if reg_yr <= 1950 else 1970
    for pnm, g in sorted(arg1_src["ipums_chl"][chl_yr].items()):
      ser = match_chl_pre1974_series(arg1_src["e3"], pnm)
      add_unit(f"CHL{chl_yr}_{slugify(pnm)}", pnm, "Chile", g, ser, f"IPUMS_Chile_Pre1974_{chl_yr}", bool(ser), priority=4.4)

    # Other QUIPU countries (pre-2007 Ecuador 22 provinces!)
    ecu_map = build_ecuador_22_provinces(adm1["ECU"])
    for iso, cname, umap in [
      ("COL", "Colombia", adm1["COL"]),
      ("VEN", "Venezuela", adm1["VEN"]),
      ("ECU", "Ecuador", ecu_map),
      ("PER", "Peru", adm1["PER"]),
      ("BOL", "Bolivia", adm1["BOL"]),
      ("URY", "Uruguay", adm1["URY"]),
    ]:
      for nm, g in sorted(umap.items()):
        ser = enum_idx.get((iso, norm_key(nm)), [])
        add_unit(f"{iso}{reg_yr}_{slugify(nm)}", nm, cname, g, ser, f"geoBoundaries_ADM1_{iso}_{reg_yr}", bool(ser), priority=4.2)

    for nm, g in sorted(adm1["FLK_SGS"].items()):
      ser = enum_idx.get(("FLK_SGS", norm_key(nm)), [])
      add_unit(f"FLK_{slugify(nm)}_{reg_yr}", nm, "Falkland Islands & South Atlantic", g, ser, "NE10m_FLK_SGS", bool(ser), priority=4.5)
    return units

  # D. Contemporary Regimes (1974..2025: exact legislative lineage for Chile 13->15->16 & Ecuador 22->24!)
  if reg_yr == 2000:
    chl_map = build_chile_13_regions(adm1["CHL"])
    ecu_map = build_ecuador_22_provinces(adm1["ECU"])
  elif reg_yr == 2010:
    chl_map = build_chile_15_regions(adm1["CHL"])
    ecu_map = adm1["ECU"]
  else:
    chl_map = adm1["CHL"]
    ecu_map = adm1["ECU"]

  for iso, cname, umap, src_lbl in [
    ("COL", "Colombia", adm1["COL"], f"geoBoundaries_ADM1_COL_{reg_yr}"),
    ("VEN", "Venezuela", adm1["VEN"], f"geoBoundaries_ADM1_VEN_{reg_yr}"),
    ("ECU", "Ecuador", ecu_map, f"geoBoundaries_ADM1_ECU_{reg_yr}"),
    ("PER", "Peru", adm1["PER"], f"geoBoundaries_ADM1_PER_{reg_yr}"),
    ("BOL", "Bolivia", adm1["BOL"], f"geoBoundaries_ADM1_BOL_Andean_{reg_yr}"),
    ("CHL", "Chile", chl_map, f"geoBoundaries_ADM1_CHL_{len(chl_map)}reg_{reg_yr}"),
    ("ARG", "Argentina", adm1["ARG"], f"CONICET_Argentina_2022_{reg_yr}"),
    ("URY", "Uruguay", adm1["URY"], f"geoBoundaries_ADM1_URY_{reg_yr}"),
    ("FLK_SGS", "Falkland Islands & South Atlantic", adm1["FLK_SGS"], f"NE10m_FLK_SGS_{reg_yr}"),
  ]:
    for nm, g in sorted(umap.items()):
      ser = enum_idx.get((iso, norm_key(nm)), [])
      add_unit(f"{iso}{reg_yr}_{slugify(nm)}", nm, cname, g, ser, src_lbl, bool(ser), priority=4.4)

  return units


def cv2_rasterise_subadmin_units(arg0_units, arg1_domain_mask, arg2_land_area):
  """Scanline-free, local-hole-aware OpenCV shift=4 rasteriser encoding 24-bit RGB integer unit IDs."""
  id_grid = np.zeros((GRID_H, GRID_W), dtype=np.int32)
  scale_x = GRID_W / 360.0
  scale_y = GRID_H / 180.0
  sm = 16.0

  # Paint strictly by z-index ascending (z=0.5 -> z=1.0 fallback -> z=2 -> z=3 -> z=4 on top!),
  # and within same z-index paint largest polygons first so small enclaves (CABA, Callao, Bogota) win!
  ordered = sorted(arg0_units, key=lambda u: (float(u["priority"]), -float(u["geom"].area)))

  for u in ordered:
    uid = int(u["id"])
    for poly in iter_polys(u["geom"]):
      minx, miny, maxx, maxy = poly.bounds
      c0 = max(0, int(math.floor((minx + 180.0) * scale_x)) - 2)
      c1 = min(GRID_W, int(math.ceil((maxx + 180.0) * scale_x)) + 2)
      r0 = max(0, int(math.floor((90.0 - maxy) * scale_y)) - 2)
      r1 = min(GRID_H, int(math.ceil((90.0 - miny) * scale_y)) + 2)
      if c1 <= c0 or r1 <= r0:
        continue
      lm = np.zeros((r1 - r0, c1 - c0), dtype=np.uint8)
      ec = np.asarray(poly.exterior.coords, dtype=np.float64)
      if len(ec) < 3:
        continue
      px = np.round(((ec[:, 0] + 180.0) * scale_x - 0.5 - c0) * sm).astype(np.int32)
      py = np.round(((90.0 - ec[:, 1]) * scale_y - 0.5 - r0) * sm).astype(np.int32)
      cv2.fillPoly(lm, [np.column_stack([px, py])], 1, lineType=cv2.LINE_8, shift=4)
      for interior in poly.interiors:
        ic = np.asarray(interior.coords, dtype=np.float64)
        if len(ic) < 3:
          continue
        hx = np.round(((ic[:, 0] + 180.0) * scale_x - 0.5 - c0) * sm).astype(np.int32)
        hy = np.round(((90.0 - ic[:, 1]) * scale_y - 0.5 - r0) * sm).astype(np.int32)
        cv2.fillPoly(lm, [np.column_stack([hx, hy])], 0, lineType=cv2.LINE_8, shift=4)
      sub = id_grid[r0:r1, c0:c1]
      sub[lm > 0] = uid

    # Pin tiny micro-islands/enclaves at representative point so zero-pixel starvation never happens
    if u["priority"] >= 4.0 and u["geom"].area < 0.08:
      rp = u["geom"].representative_point()
      col = min(GRID_W - 1, max(0, int((rp.x + 180.0) * scale_x)))
      row = min(GRID_H - 1, max(0, int((90.0 - rp.y) * scale_y)))
      if arg1_domain_mask[row, col]:
        id_grid[row, col] = uid

  id_grid[~arg1_domain_mask] = 0

  # Nearest-neighbour fill any tiny unlabelled coastal edge pixels strictly inside quipu_domain_mask
  missing = arg1_domain_mask & (id_grid == 0)
  if missing.any() and (id_grid > 0).any():
    _, idx = distance_transform_edt(id_grid == 0, return_indices=True)
    id_grid[missing] = id_grid[idx[0][missing], idx[1][missing]]

  max_id = max((int(u["id"]) for u in arg0_units), default=0)
  flat_ids = id_grid[arg1_domain_mask]
  flat_la = arg2_land_area[arg1_domain_mask]
  px_cnt = np.bincount(flat_ids, minlength=max_id + 1)
  area_sum = np.bincount(flat_ids, weights=flat_la, minlength=max_id + 1)

  # 24-bit RGB integer encoding: uid = (R << 16) | (G << 8) | B
  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  pos = id_grid > 0
  rgba[pos, 0] = ((id_grid[pos] >> 16) & 0xFF).astype(np.uint8)
  rgba[pos, 1] = ((id_grid[pos] >> 8) & 0xFF).astype(np.uint8)
  rgba[pos, 2] = (id_grid[pos] & 0xFF).astype(np.uint8)
  rgba[pos, 3] = 255
  return rgba, id_grid, px_cnt, area_sum


def detect_scanline_gaps(arg0_id_grid):
  """Counts horizontal scanline gap rows (empty row strictly between two populated rows)."""
  valid = arg0_id_grid > 0
  rs = np.where(valid.any(axis=1))[0]
  if len(rs) < 3:
    return 0
  gaps = 0
  for r in range(int(rs[0]) + 1, int(rs[-1])):
    if int(valid[r].sum()) == 0 and int(valid[r - 1].sum()) >= 15 and int(valid[r + 1].sum()) >= 15:
      gaps += 1
  return gaps


def render_subadmin_crop_png(arg0_id_grid, arg1_domain_mask, arg2_out_path, arg3_title):
  """Renders a crisp, deterministic false-colour QA crop of a subadmin_hgis regime."""
  rs, cs = np.where(arg1_domain_mask)
  r0 = max(0, int(rs.min()) - 14)
  r1 = min(GRID_H, int(rs.max()) + 15)
  c0 = max(0, int(cs.min()) - 18)
  c1 = min(GRID_W, int(cs.max()) + 19)

  sub_id = arg0_id_grid[r0:r1, c0:c1]
  sub_dom = arg1_domain_mask[r0:r1, c0:c1]

  img = np.full((r1 - r0, c1 - c0, 3), [228, 238, 246], dtype=np.uint8)
  edge = binary_dilation(sub_dom, iterations=1) & (~sub_dom)
  img[edge] = [45, 55, 70]

  pos = sub_id > 0
  u = sub_id[pos].astype(np.uint64)
  img[pos, 0] = (((u * 2654435761) >> 16) % 185 + 50).astype(np.uint8)
  img[pos, 1] = (((u * 2246822519) >> 16) % 185 + 50).astype(np.uint8)
  img[pos, 2] = (((u * 3266489917) >> 16) % 185 + 50).astype(np.uint8)

  # Highlight internal borders crisply
  int_edge = np.zeros_like(sub_dom)
  int_edge[:-1, :] |= (sub_id[:-1, :] != sub_id[1:, :]) & sub_dom[:-1, :] & sub_dom[1:, :]
  int_edge[:, :-1] |= (sub_id[:, :-1] != sub_id[:, 1:]) & sub_dom[:, :-1] & sub_dom[:, 1:]
  img[int_edge] = (img[int_edge].astype(np.float32) * 0.45).astype(np.uint8)

  lon_min = -180.0 + c0 / 12.0
  lon_max = -180.0 + c1 / 12.0
  lat_max = 90.0 - r0 / 12.0
  lat_min = 90.0 - r1 / 12.0

  plt.rcdefaults()
  plt.style.use("default")
  fig, ax = plt.subplots(figsize=(9.5, 11.0), dpi=135)
  ax.imshow(img, extent=[lon_min, lon_max, lat_min, lat_max], interpolation="nearest", aspect="equal")
  ax.set_aspect("equal", adjustable="box")
  ax.set_xlabel("Longitude (°E)", fontsize=9)
  ax.set_ylabel("Latitude (°N)", fontsize=9)
  ax.set_title(arg3_title, fontsize=10.5, fontweight="bold")
  ax.grid(True, linestyle=":", linewidth=0.45, color="#556677", alpha=0.55)
  plt.tight_layout()
  fig.savefig(arg2_out_path, dpi=135, bbox_inches="tight")
  plt.close(fig)


def verify_zero_anachronisms(arg0_yr, arg1_kept_units):
  yr = int(arg0_yr)
  if yr < 1974:
    bad_chl = [u["name"] for u in arg1_kept_units if u["country"] == "Chile" and "Región" in u["name"]]
    assert not bad_chl, f"ANACHRONISM FAIL in {yr}: post-1974 Chilean CONARA region present: {bad_chl[:4]}"
  if yr < 2007:
    bad_2007 = [u["name"] for u in arg1_kept_units if u["country"] == "Chile" and any(k in u["name"] for k in ("Arica y Parinacota", "Los Ríos"))]
    assert not bad_2007, f"ANACHRONISM FAIL in {yr}: post-2007 Chilean region present: {bad_2007}"
  if yr < 2018:
    bad_2018 = [u["name"] for u in arg1_kept_units if u["country"] == "Chile" and "Ñuble" in u["name"] and "Región" in u["name"]]
    assert not bad_2018, f"ANACHRONISM FAIL in {yr}: post-2018 Chilean Ñuble region present: {bad_2018}"


def main():
  print("=== Operation Viscount Project QUIPU — Sub-Admin HGIS Raster Builder (118 AD HYDE Years) ===", flush=True)
  for d in (RASTER_DIR, SUBADMIN_CROPS_DIR):
    for fn in os.listdir(d):
      if fn.startswith(("subadmin_id_", "subadmin_meta_", "quipu_subadmin_")):
        os.remove(os.path.join(d, fn))

  dm_raw = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  domain_mask = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)
  land_area = load_land_area()
  total_dom_px = int(domain_mask.sum())
  print(f"  Loaded quipu_domain_mask.png: {total_dom_px:,} land pixels", flush=True)

  src = load_all_sources()

  regime_to_years = defaultdict(list)
  for y in ALL_HYDE_AD_YEARS:
    regime_to_years[get_regime_key(y)].append(y)
  distinct_regimes = sorted(regime_to_years.keys())
  print(f"\n[2] Rasterising {len(distinct_regimes)} distinct Academic-HGIS regimes -> ALL {len(ALL_HYDE_AD_YEARS)} AD HYDE years...", flush=True)

  lit_summary = {
    "project": "QUIPU",
    "version": "1.0_academic_hgis_cv2_rgb24",
    "id_encoding": "rgb24_big_endian",
    "anti_anachronism_verified": True,
    "scanline_free_cv2_fillPoly": True,
    "atlas_defacto_lowest_z_index_fallback": True,
    "hyde_ad_year_count": len(ALL_HYDE_AD_YEARS),
    "distinct_boundary_regimes": len(distinct_regimes),
    "generated_snapshots": {},
  }
  lit_csv_rows = []
  csv_export_years = {0, 600, 1100, 1400, 1500, 1600, 1700, 1750, 1780, 1800, 1820, 1850, 1870, 1890, 1900, 1920, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020, 2025}

  total_scanline_gaps = 0
  for reg_yr in distinct_regimes:
    yrs_in_regime = regime_to_years[reg_yr]
    units = build_regime_units(reg_yr, src)
    rgba, id_grid, px_cnt, area_sum = cv2_rasterise_subadmin_units(units, domain_mask, land_area)

    gaps = detect_scanline_gaps(id_grid)
    total_scanline_gaps += gaps
    cov_px = int((id_grid > 0).sum())
    cov_pct = 100.0 * cov_px / max(1, total_dom_px)

    kept_units = []
    for u in units:
      uid = u["id"]
      if int(px_cnt[uid]) <= 0:
        continue
      kept_units.append({
        "id": uid,
        "code": u["code"],
        "name": u["name"],
        "country": u["country"],
        "source": u["source"],
        "z_index": round(float(u["priority"]), 2),
        "is_direct_census": bool(u["is_direct_census"]),
        "pixel_count": int(px_cnt[uid]),
        "area_km2": round(float(area_sum[uid]), 1),
        "series": u["series"],
      })

    # Render optical QA crops for every requested key year inside this regime!
    for qa_yr in sorted(QA_CROP_YEARS):
      if qa_yr in yrs_in_regime:
        crop_png = SUBADMIN_CROPS_DIR / f"quipu_subadmin_{qa_yr}.png"
        render_subadmin_crop_png(
          id_grid, domain_mask, crop_png,
          f"QUIPU Sub-Admin HGIS — {qa_yr} AD (Regime {reg_yr}: {yrs_in_regime[0]}..{yrs_in_regime[-1]}) | {len(kept_units)} units | {cov_pct:.2f}% cov",
        )

    # Save PNG bytes once per regime and write for every HYDE year in this regime
    buf = io.BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(buf, format="PNG", compress_level=6)
    png_bytes = buf.getvalue()

    for yr in yrs_in_regime:
      verify_zero_anachronisms(yr, kept_units)
      with open(RASTER_DIR / f"subadmin_id_{yr}.png", "wb") as fh:
        fh.write(png_bytes)

      meta_obj = {
        "snapshot_year": yr,
        "boundary_regime": reg_yr,
        "id_encoding": "rgb24_big_endian",
        "anti_anachronism_verified": True,
        "scanline_glitches": gaps,
        "unit_count": len(kept_units),
        "covered_pixels": cov_px,
        "coverage_pct": round(cov_pct, 3),
        "units": kept_units,
      }
      with open(RASTER_DIR / f"subadmin_meta_{yr}.json", "w", encoding="utf-8") as fh:
        json.dump(meta_obj, fh)

      lit_summary["generated_snapshots"][str(yr)] = {
        "boundary_regime": reg_yr,
        "unit_count": len(kept_units),
        "covered_pixels": cov_px,
        "coverage_pct": round(cov_pct, 3),
        "scanline_glitches": gaps,
        "sources_used": sorted({u["source"] for u in kept_units}),
      }

      if yr in csv_export_years:
        for ku in kept_units:
          p_yr = interp_series(ku["series"], yr) if ku["series"] else None
          lit_csv_rows.append([
            yr, reg_yr, ku["country"], ku["code"], ku["name"],
            int(round(p_yr)) if p_yr is not None else "",
            ku["pixel_count"], ku["area_km2"], ku["z_index"], ku["source"],
          ])

    print(
      f"  Regime {reg_yr:4d} ({yrs_in_regime[0]:4d}..{yrs_in_regime[-1]:4d}, {len(yrs_in_regime):2d} yrs): "
      f"{len(kept_units):3d} units | cov={cov_pct:6.2f}% | scanlines={gaps}",
      flush=True,
    )

  with open(HGIS_ROOT / "subadmin_enumerations_for_literature_reviews.json", "w", encoding="utf-8") as fh:
    json.dump(lit_summary, fh, indent=2, ensure_ascii=False)
  with open(HGIS_ROOT / "subadmin_enumerations_for_literature_reviews.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["year", "boundary_regime", "country", "unit_code", "unit_name", "interpolated_population", "pixel_count", "area_km2", "z_index", "source"])
    w.writerows(lit_csv_rows)

  print(
    f"\n[DONE] Built ALL {len(ALL_HYDE_AD_YEARS)} QUIPU AD HYDE rasters ({len(distinct_regimes)} regimes) | "
    f"total_scanlines={total_scanline_gaps} | CSV rows={len(lit_csv_rows):,} | "
    f"QA crops emitted: {len(QA_CROP_YEARS)} PNGs in {SUBADMIN_CROPS_DIR}",
    flush=True,
  )


if __name__ == "__main__":
  main()
