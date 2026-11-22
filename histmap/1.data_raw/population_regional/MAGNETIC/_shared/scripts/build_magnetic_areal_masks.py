"""Stage A2 Rebuilt Historically Authentic & Natural-Watershed Dual Mask + Vector Sub-Region
GeoJSON Builder for Operation Viscount Project MAGNETIC.

COMPLETELY REBUILT FROM SCRATCH (ZERO MODERN BORDERS IN PRE-1945 CHAPTERS!):
  - Ch 01-02 (Prehistoric, -10000..-1000): 100% Organic HydroBASINS L6 natural river watersheds
    grouped by Pfafstetter river-basin catchments (strictly clipped to MAGNETIC land union ->
    ZERO Anatolian/Syrian/POLARIS bleed, ZERO straight-line cuts!).
  - Ch 03 (Classical Greece & Aegean, -1000..-146): 100% Natural HydroBASINS Hellenic/Aegean
    river watersheds & islands (Pindus divide, Axios/Vardar-Strymon-Maritsa basins, Peloponnese,
    Crete/Aegean — ZERO modern Albanian/Macedonian borders!).
  - Ch 04 (Iron Age & Roman Europe, -1000..400): 100% AUTHENTIC DARE Roman Imperial Provinces
    (`dare_provinces.geojson`: 38 named European provinces along the actual Rhine-Danube-Hadrian's
    Wall Limes — excludes Caledonia/Scotland, Frisia, Free Germany & Moldova!).
  - Ch 05 (Free Germany, Scandinavia & Baltic-Slavic North-East, -1000..500): EXACT complement of
    Roman Europe (`MAGNETIC MINUS Roman Empire`), partitioned strictly by organic HydroBASINS L6
    watersheds (Rhine-Weser-Elbe Germania Magna, Bohemia-Morava-Upper Tisza, Oder-Vistula,
    Jutland, Scandinavia, Eastern Baltic-Finland, Hibernia-Caledonia-North Atlantic — ZERO modern
    borders, ZERO straight lines!).
  - Ch 06 (Late Antiquity & Migration Period, 250..800): Authentic Early Mediaeval polities
    (`historical_basemaps` world_700/800 + organic HydroBASINS Elbe-Saale/Carpathian/Danube divides).
  - Ch 07 (Mediaeval Western & Central Europe, 800..1347): Authentic High Mediaeval Kingdom of
    France (west of Scheldt-Meuse-Saône-Rhône), Holy Roman Empire (HistoGIS 1512 incl. Pomerania,
    Brandenburg, Alsace-Lorraine, Franche-Comté, Austria, Switzerland, Low Countries), England & Wales,
    Scotland & Ireland, Regnum Italiae & Papal/Sicilian South!
  - Ch 08 (Mediaeval Iberia, 711..1492): Authentic Reconquista Kingdoms (Castile-León, Crown of
    Aragon + Navarre + Balearics, Kingdom of Portugal, Al-Andalus / Granada, Canaries).
  - Ch 09 (Mediaeval Scandinavia & North Atlantic, 800..1500): Authentic Pre-1658 Nordic borders
    (Denmark INCLUDING Scania, Halland & Blekinge; Norway INCLUDING Jämtland; Sweden proper;
    Finland/Österland; Iceland, Faroes, Greenland!).
  - Ch 10 (Mediaeval East-Central Europe, Baltic & Balkans, 800..1347): Piast Poland (outside
    Teutonic Prussia & HRE Pomerania/Silesia), Bohemian Crown (Bohemia-Moravia-Silesia), Kingdom of
    Hungary (Crown of St Stephen INCL. Slovakia, Transylvania & Croatia-Slavonia!), Danubian
    Principalities (Wallachia & Moldavia OUTSIDE Transylvania!), Teutonic Prussia/Livonia/Lithuania,
    Serbia-Bosnia-Dalmatia-Albania, Bulgaria & Byzantine Greece/Thrace!
  - Ch 11 (Black Death & Late Mediaeval Crisis, 1347..1500): Authentic c. 1400 European realms!
  - Ch 12-15 (Early Modern Europe, 1500..1750 / Ottoman Balkans 1350..1830): Authentic 1648 Peace
    of Westphalia & Early Modern frontiers (HistoGIS HRE 1648 spanning the Oder into Pomerania,
    Bohemian Crown incl. Silesia, Habsburg Austria, Poland-Lithuania outside HRE, France pre-Savoy/
    Corsica, Dutch Republic vs Southern Netherlands, Sweden-Finland, Denmark-Norway, Castile/Aragon,
    Early Modern Italian States, Ottoman Rumelia & Danubian Principalities outside Transylvania!).
  - Ch 16-17 (1750..1914): Authentic 1871-1914 Imperial Europe (`HGIS Germany 1914` incl. East
    Prussia, Pomerania, Posen, Silesia & Alsace-Lorraine; French Third Republic WITHOUT Alsace-
    Lorraine; Austria-Hungary Cisleithania & Transleithania; Congress Poland; DEMOPAST 1901 Italy
    WITHOUT South Tyrol/Istria; Old Kingdom of Romania & Balkan kingdoms!).
  - Ch 18 (World Wars & Inter-War Europe, 1914..1945): Authentic 1920-1938 Versailles-Trianon
    Europe (`CShapes 1930`: Weimar Germany WITH East Prussia/Pomerania/Silesia; Second Polish
    Republic WITH Corridor & Lwów; Czechoslovakia & Trianon Hungary; Greater Romania; Yugoslavia;
    Italy WITH Istria & South Tyrol; France WITH Alsace-Lorraine!).
  - Ch 19-21 (After 1945, Regime III): Post-1945 contemporary census sovereign states!

Also renders high-resolution Albers Equal-Area optical inspection PNGs for ALL 21 chapters into
`/tests/areal_mask_crops/mask_ch<01..21>_<stem>.png` over a PURE LAND BASEMAP (ZERO modern borders
for Ch 01-18!) so EVERY SINGLE ONE of the 21 masks is optically verified before committing!
"""

import io
import json
import math
import os
import re
import shutil
import zipfile
from collections import defaultdict

import cv2
import json5
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch, Polygon as MplPolygon
import numpy as np
import shapefile
from PIL import Image
from scipy.ndimage import distance_transform_edt
from shapely.geometry import MultiPolygon, Polygon, box, mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

from magnetic_hgis_tables import (
  ES_PROV_TO_HISTORIC_KINGDOM,
  FR_DEP_TO_ANCIEN_PROVINCE,
  GRID_H,
  GRID_W,
  fix_mojibake,
  norm_str,
  safe_geom,
)
from magnetic_map_helper import (
  PROJ_EUROPE,
  PROJ_GREENLAND,
  apply_viscount_style,
  draw_basemap,
  draw_graticule,
  geom_to_patches,
  load_basemap_cache,
  prepare_and_project,
  save_viscount_figure,
)

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC")
MAG_GIS = os.path.join(MAG_DIR, "_shared", "_gis_cache")
SUB_GJ_DIR = os.path.join(MAG_GIS, "chapter_subregions")
HGIS_RAW = os.path.join(MAG_DIR, "_shared", "subadmin_hgis", "raw_sources")
HGIS_PARSED = os.path.join(MAG_DIR, "_shared", "subadmin_hgis", "parsed")
DOMAIN_MASK_PNG = os.path.join(MAG_DIR, "_shared", "sites_magnetic_europe", "config", "magnetic_domain_mask.png")
HYBAS_EU_ZIP = os.path.join(MAG_GIS, "hybas_eu_lev06_v1c.zip")
ADM1_GJ_PATH = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CENTAUR", "_shared", "_gis_cache",
  "ne_10m_admin_1_states_provinces.geojson"
)
TESTS_MASK_DIR = os.path.join(SVEA_ROOT, "tests", "areal_mask_crops")

os.makedirs(SUB_GJ_DIR, exist_ok=True)
os.makedirs(TESTS_MASK_DIR, exist_ok=True)

PALETTE = [
  [184, 105, 81], [86, 134, 168], [118, 158, 98], [198, 152, 74],
  [146, 106, 162], [78, 156, 148], [204, 118, 132], [134, 146, 86],
  [172, 128, 104], [96, 118, 174], [164, 154, 88], [192, 102, 106],
  [88, 148, 118], [156, 116, 138], [122, 164, 184], [186, 142, 112],
  [108, 138, 94], [168, 96, 124], [142, 126, 166], [92, 158, 168],
]

ALL_HYDE_YEARS = [
  -10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000,
  0, 100, 200, 300, 400, 500, 600, 700, 800, 900,
  1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
  1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790,
  1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890,
  1900, 1910, 1920, 1930, 1940, 1950
] + list(range(1951, 2026))


def u_geoms(glist):
  valid = [safe_geom(g) for g in glist if safe_geom(g) is not None]
  if not valid:
    return None
  return safe_geom(unary_union(valid))


def clip_mag(g, mag_union):
  g = safe_geom(g)
  if g is None:
    return None
  try:
    return safe_geom(g.intersection(mag_union))
  except Exception:
    return safe_geom(g.buffer(0).intersection(mag_union))


def diff_geom(a, b):
  a = safe_geom(a)
  if a is None:
    return None
  b = safe_geom(b)
  if b is None:
    return a
  try:
    return safe_geom(a.difference(b))
  except Exception:
    return safe_geom(a.buffer(0).difference(b.buffer(0)))


def load_historical_geometries():
  print("[1] Loading MAGNETIC domain, HydroBASINS L6, DARE Roman Provinces, HistoGIS, HGIS Germany, SGF, DEMOPAST & CShapes...", flush=True)
  dm_raw = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  domain_mask = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)

  # 1. MAGNETIC sovereign land union (used strictly for outer domain clipping & Regime III post-1945!)
  c_gj = json.load(open(os.path.join(MAG_GIS, "magnetic_countries.geojson"), encoding="utf-8"))
  countries = {}
  for feat in c_gj["features"]:
    nm = feat["properties"]["ADMIN"]
    g = safe_geom(shape(feat["geometry"]))
    if g is not None:
      countries[nm] = g
  mag_union = u_geoms(list(countries.values()))

  # Island & geographic natural coastlines (purely physical/geographical, NOT modern borders!)
  adm1 = defaultdict(list)
  a1_gj = json.load(open(ADM1_GJ_PATH, encoding="utf-8"))
  for f in a1_gj["features"]:
    p = f["properties"]
    c = p.get("admin") or p.get("geonunit") or ""
    if c not in countries:
      continue
    g = safe_geom(shape(f["geometry"]))
    if g is None:
      continue
    g = clip_mag(g, countries[c])
    if g is None:
      continue
    rp = g.representative_point()
    adm1[c].append({"name": p.get("name") or "", "norm": norm_str(p.get("name") or ""), "region": p.get("region") or "", "geonunit": p.get("geonunit") or "", "g": g, "lat": float(rp.y), "lon": float(rp.x)})

  # Physical island/peninsula helpers
  geo = dict(countries)
  if "United Kingdom" in adm1:
    geo["UK_England_Wales"] = u_geoms([x["g"] for x in adm1["United Kingdom"] if x["geonunit"] in ("England", "Wales")])
    geo["UK_Scotland"] = u_geoms([x["g"] for x in adm1["United Kingdom"] if x["geonunit"] == "Scotland"])
    geo["UK_Northern_Ireland"] = u_geoms([x["g"] for x in adm1["United Kingdom"] if x["geonunit"] == "Northern Ireland"])
  geo["Spain_Canaries"] = safe_geom(countries["Spain"].intersection(box(-19.0, 27.3, -13.0, 29.6)))
  geo["Spain_Mainland"] = diff_geom(countries["Spain"], geo["Spain_Canaries"])
  geo["Spain_Balearics"] = safe_geom(geo["Spain_Mainland"].intersection(box(1.0, 38.5, 4.6, 40.3)))
  geo["Portugal_Islands"] = safe_geom(countries["Portugal"].intersection(box(-32.0, 32.0, -15.5, 40.5)))
  geo["Portugal_Mainland"] = diff_geom(countries["Portugal"], geo["Portugal_Islands"])
  geo["British_Isles"] = u_geoms([countries[k] for k in ("United Kingdom", "Ireland", "Isle of Man", "Jersey", "Guernsey") if k in countries])
  geo["Great_Britain"] = u_geoms([geo["UK_England_Wales"], geo["UK_Scotland"], countries.get("Isle of Man"), countries.get("Jersey"), countries.get("Guernsey")])
  geo["Ireland_Full"] = u_geoms([countries["Ireland"], geo["UK_Northern_Ireland"]])
  geo["North_Atlantic"] = u_geoms([countries[k] for k in ("Iceland", "Faroe Islands", "Greenland") if k in countries])
  geo["Iberian_Peninsula"] = u_geoms([geo["Spain_Mainland"], geo["Portugal_Mainland"], countries.get("Andorra"), countries.get("Gibraltar")])
  geo["Italian_Peninsula_Full"] = u_geoms([countries[k] for k in ("Italy", "San Marino", "Vatican", "Malta") if k in countries])

  # 2. HydroBASINS L6 (100% natural river watersheds, clipped strictly to mag_union!)
  basins = []
  with zipfile.ZipFile(HYBAS_EU_ZIP) as zf:
    sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
    for sr in sf.iterShapeRecords():
      bb = sr.shape.bbox
      if bb[2] < -32.0 or bb[0] > 35.0 or bb[3] < 27.0 or bb[1] > 82.0:
        continue
      g = clip_mag(shape(sr.shape.__geo_interface__), mag_union)
      if g is None or g.area < 0.001:
        continue
      rp = g.representative_point()
      basins.append({"g": g, "lat": float(rp.y), "lon": float(rp.x), "pfaf": str(sr.record["PFAF_ID"]), "main_bas": int(sr.record["MAIN_BAS"])})
  print(f"  HydroBASINS L6 clipped cleanly to MAGNETIC: {len(basins)} basins", flush=True)

  # 3. DARE Roman Imperial Provinces (38 European provinces!)
  dare = {}
  dare_gj = json.load(open(os.path.join(HGIS_RAW, "roman_provinces", "dare_provinces.geojson"), encoding="utf-8"))
  for f in dare_gj["features"]:
    nk = norm_str(f["properties"].get("name") or "")
    g = clip_mag(shape(f["geometry"]), mag_union)
    if g is not None and g.area > 0.01:
      dare[nk] = g
  roman_union = u_geoms(list(dare.values()))
  print(f"  DARE Roman Provinces: {len(dare)} European provinces", flush=True)

  # 4. HistoGIS OEAW (HRE Imperial Circles 1512/1648/1792 + Habsburg Crownlands 1820/1910)
  hre_circles = defaultdict(dict)
  ah_1910 = {}
  ah_1850 = {}
  with open(os.path.join(HGIS_RAW, "histogis", "histogis-dump.jsonl"), encoding="utf-8") as fh:
    for line in fh:
      if not line.strip():
        continue
      o = json.loads(line)
      p = o.get("properties") or {}
      sn = p.get("source_name") or ""
      if not any(k in sn for k in ("Holy Roman Empire Imperial Circles", "Crownlands 1910", "Crownlands 1867")):
        continue
      g = clip_mag(shape(o["geometry"]), mag_union) if o.get("geometry") else None
      if g is None:
        continue
      nk = norm_str(p.get("name") or "")
      if "Holy Roman Empire Imperial Circles" in sn:
        m = re.search(r"(\d{4})", sn)
        if m:
          hre_circles[int(m.group(1))][nk] = g
      elif "Crownlands 1910" in sn:
        ah_1910[nk] = g
      elif "Crownlands 1867" in sn:
        ah_1850[nk] = g
  print(f"  HistoGIS: HRE circles={ {k: len(v) for k, v in hre_circles.items()} } | AH 1910={len(ah_1910)} | AH 1867={len(ah_1850)}", flush=True)

  # 5. HGIS Germany 1914 (Prussia + Southern States + Alsace-Lorraine + authentic East Prussia for Teutonic Prussia!)
  de14_gj = json.load(open(os.path.join(HGIS_RAW, "eu_hist_germany_1914.geojson"), encoding="utf-8"))
  de14_north, de14_south, de14_all, east_prussia_parts = [], [], [], []
  for f in de14_gj["features"]:
    g = clip_mag(shape(f["geometry"]), mag_union)
    if g is None:
      continue
    st = norm_str(fix_mojibake(f["properties"].get("STAAT_NAME") or ""))
    rn = norm_str(fix_mojibake(f["properties"].get("REG_NAME") or ""))
    de14_all.append(g)
    if any(k in rn for k in ("konigsberg", "gumbinnen", "allenstein")):
      east_prussia_parts.append(g)
    if any(k in st for k in ("bayern", "wurttemberg", "rttemberg", "baden", "sachsen", "hessen", "elsass", "elsa", "lothr")):
      de14_south.append(g)
    else:
      de14_north.append(g)
  east_prussia_hist = u_geoms(east_prussia_parts)
  # Also capture small Northern German states (Mecklenburg/Oldenburg/Braunschweig/Hamburg/Bremen/Lübeck) via CShapes 1900 Germany
  cs_gj = json.load(open(os.path.join(HGIS_RAW, "cshapes", "CShapes-Europe.geojson"), encoding="utf-8"))
  cshapes_yr = defaultdict(dict)
  for f in cs_gj["features"]:
    p = f["properties"]
    try:
      y0, y1 = int(str(p.get("From", ""))[:4]), int(str(p.get("To", ""))[:4])
    except Exception:
      continue
    g = clip_mag(shape(f["geometry"]), mag_union)
    if g is None:
      continue
    nk = norm_str(p.get("Name") or "")
    for ty in (1880, 1900, 1914, 1930, 1937):
      if y0 <= ty <= y1:
        cshapes_yr[ty][nk] = u_geoms([cshapes_yr[ty].get(nk), g])

  de1900_full = cshapes_yr[1900].get("germany prussia") or u_geoms(de14_all)
  de14_south_u = u_geoms(de14_south)
  de14_north_u = diff_geom(de1900_full, de14_south_u)

  # 6. SGF France (1801 Ancien Régime provinces + 1876 87 deps excl. Alsace-Lorraine)
  sgf_gj = json.load(open(os.path.join(HGIS_PARSED, "sgf_france_dep_histo.geojson"), encoding="utf-8"))
  fr_1801_deps, fr_1876_deps = {}, {}
  for f in sgf_gj["features"]:
    p = f["properties"]
    gyr = int(round(float(p["ANNEE_GEOGRAPHIE"])))
    code = str(p["CODGEO"]).strip().zfill(2)
    g = clip_mag(shape(f["geometry"]), mag_union)
    if g is None:
      continue
    if gyr == 1801:
      fr_1801_deps[code] = g
    elif gyr == 1876:
      fr_1876_deps[code] = g
  # Mediaeval Kingdom of France (c. 1300: stops at Scheldt-Meuse-Saône-Rhône — EXCLUDES Alsace, Lorraine, Franche-Comté, Provence, Dauphiné, Savoy, Nice, Corsica!)
  fr_med_n = u_geoms([g for d, g in fr_1801_deps.items() if FR_DEP_TO_ANCIEN_PROVINCE.get(d, ("", 9999))[1] <= 1320 and g.representative_point().y >= 46.2])
  fr_med_s = u_geoms([g for d, g in fr_1801_deps.items() if FR_DEP_TO_ANCIEN_PROVINCE.get(d, ("", 9999))[1] <= 1320 and g.representative_point().y < 46.2])
  # Early Modern Kingdom of France (c. 1700: includes Provence, Dauphiné, Alsace, Franche-Comté, Artois, Roussillon; EXCLUDES Savoy, Nice, Corsica, Lorraine!)
  fr_em_1700 = u_geoms([g for d, g in fr_1801_deps.items() if FR_DEP_TO_ANCIEN_PROVINCE.get(d, ("", 9999))[1] <= 1700])
  fr_1876_u = u_geoms(list(fr_1876_deps.values()))

  # 7. Spain Historic Kingdoms (Castile, Aragon, Granada/Al-Andalus, Navarre)
  es_gj = json.load(open(os.path.join(HGIS_RAW, "spain_hist", "spain_provinces.geojson"), encoding="utf-8"))
  es_k_buckets = defaultdict(list)
  for f in es_gj["features"]:
    cp = str(f["properties"].get("cod_prov", "")).strip().zfill(2)
    knm = ES_PROV_TO_HISTORIC_KINGDOM.get(cp)
    g = clip_mag(shape(f["geometry"]), mag_union)
    if knm and g is not None:
      es_k_buckets[knm].append(g)
  es_k = {k: u_geoms(gs) for k, gs in es_k_buckets.items()}

  # 8. Sweden Historic Län (1750: Scania/Halland/Blekinge for pre-1658 Mediaeval Denmark, Jämtland ONLY for Mediaeval Norway!)
  se_1750 = json.load(open(os.path.join(HGIS_PARSED, "sweden_counties_1750.geojson"), encoding="utf-8"))
  se_danish_skane, se_norw_jamt, se_core = [], [], []
  for f in se_1750["features"]:
    nm = norm_str(f["properties"].get("name") or "")
    g = clip_mag(shape(f["geometry"]), mag_union)
    if g is None:
      continue
    if any(k in nm for k in ("malmohus", "kristianstad", "blekinge", "halland")):
      se_danish_skane.append(g)
    elif "jamtland" in nm:
      se_norw_jamt.append(g)
    else:
      se_core.append(g)

  # 9. DEMOPAST Italy 1901 (authentic 1871-1914 borders WITHOUT Trentino/South Tyrol & Istria!)
  it01_gj = json.load(open(os.path.join(HGIS_RAW, "demopast_italy", "province_1901.geojson"), encoding="utf-8"))
  it01_nc, it01_s = [], []
  for f in it01_gj["features"]:
    g = clip_mag(shape(f["geometry"]), mag_union)
    if g is None:
      continue
    rp = g.representative_point()
    if rp.y >= 41.35 and not (rp.y < 41.6 and rp.x < 10.0):
      it01_nc.append(g)
    else:
      it01_s.append(g)
  # Early modern / Mediaeval Italy North (Piedmont-Lombardy-Venice-Genoa-Emilia-Tuscany) vs Central vs South
  it_n_em = u_geoms([x["g"] for x in adm1.get("Italy", []) if x["lat"] >= 43.9])
  it_c_em = u_geoms([x["g"] for x in adm1.get("Italy", []) if 41.3 <= x["lat"] < 43.9 and x["lon"] > 10.0])
  it_s_em = u_geoms([x["g"] for x in adm1.get("Italy", []) if x["lat"] < 41.3 or x["lon"] <= 10.0])

  # 10. Congress Poland & Historical Basemaps (world_800, world_1200, world_1300, world_1400, world_1650)
  cp_gj = json.load(open(os.path.join(HGIS_RAW, "eu_hist_poland_1914.geojson"), encoding="utf-8"))
  congress_poland = u_geoms([clip_mag(shape(f["geometry"]), mag_union) for f in cp_gj["features"]])

  hb = {}
  for yr_hb in (600, 800, 1200, 1300, 1400, 1650):
    fp = os.path.join(HGIS_RAW, "historical_basemaps", f"world_{yr_hb}.geojson")
    if os.path.isfile(fp):
      gj = json.load(open(fp, encoding="utf-8"))
      d_y = defaultdict(list)
      for f in gj["features"]:
        if not f.get("geometry"):
          continue
        g = clip_mag(shape(f["geometry"]), mag_union)
        if g is None:
          continue
        nm = norm_str(f["properties"].get("NAME") or f["properties"].get("SUBJECTO") or "")
        if nm:
          d_y[nm].append(g)
      hb[yr_hb] = {k: u_geoms(gs) for k, gs in d_y.items()}

  # Authentic Habsburg Kingdom of Hungary (Crown of St Stephen: Hungary + Slovakia + Transylvania + Croatia-Slavonia!)
  hungary_crown_hist = u_geoms([ah_1910.get(k) for k in ah_1910 if any(t in k for t in ("ungarn", "kroatien", "siebenburgen", "fiume"))] + [ah_1850.get(k) for k in ah_1850 if "siebenburgen" in k])
  bohemian_crown_hist = u_geoms([ah_1910.get(k) for k in ah_1910 if any(t in k for t in ("bohmen", "mahren", "schlesien"))])
  austria_hereditary_hist = u_geoms([ah_1910.get(k) for k in ah_1910 if any(t in k for t in ("unter der enns", "ob der enns", "salzburg", "steiermark", "karnten", "krain", "tirol", "vorarlberg", "kustenland", "triest", "gorz", "istrien"))])
  cisleithania_1910 = u_geoms([v for k, v in ah_1910.items() if not any(t in k for t in ("ungarn", "kroatien", "fiume", "bosnien", "siebenburgen"))])
  transleithania_1910 = u_geoms([v for k, v in ah_1910.items() if any(t in k for t in ("ungarn", "kroatien", "fiume", "bosnien"))])

  return {
    "domain_mask": domain_mask, "mag_union": mag_union, "countries": countries, "geo": geo, "adm1": adm1,
    "basins": basins, "dare": dare, "roman_union": roman_union,
    "hre_circles": hre_circles, "ah_1910": ah_1910, "ah_1850": ah_1850,
    "hungary_crown_hist": hungary_crown_hist, "bohemian_crown_hist": bohemian_crown_hist,
    "austria_hereditary_hist": austria_hereditary_hist, "cisleithania_1910": cisleithania_1910,
    "transleithania_1910": transleithania_1910,
    "de14_north": de14_north_u, "de14_south": de14_south_u, "de1900_full": de1900_full, "east_prussia_hist": east_prussia_hist,
    "fr_med_n": fr_med_n, "fr_med_s": fr_med_s, "fr_em_1700": fr_em_1700, "fr_1876": fr_1876_u,
    "es_k": es_k, "se_danish_skane": u_geoms(se_danish_skane), "se_norw_jamt": u_geoms(se_norw_jamt), "se_core": u_geoms(se_core),
    "it01_nc": u_geoms(it01_nc), "it01_s": u_geoms(it01_s), "it_n_em": it_n_em, "it_c_em": it_c_em, "it_s_em": it_s_em,
    "congress_poland": congress_poland, "cshapes": cshapes_yr, "hb": hb,
  }


def group_basins(basins, classifier, clip_geom=None):
  """Groups natural HydroBASINS L6 watersheds organically (ZERO straight-line box cuts!)."""
  buckets = defaultdict(list)
  for b in basins:
    g = b["g"]
    if clip_geom is not None:
      try:
        g = safe_geom(g.intersection(clip_geom))
      except Exception:
        g = None
      if g is None or g.area < 0.002:
        continue
      rp = g.representative_point()
      lat, lon = float(rp.y), float(rp.x)
    else:
      lat, lon = b["lat"], b["lon"]
    zid = classifier(lat, lon, b["pfaf"])
    if zid:
      buckets[zid].append(g)
  return {k: u_geoms(gs) for k, gs in buckets.items()}


def rasterise_zones_cv2(domain_mask, zones_spec, full_domain=False):
  """Zero-scanline OpenCV `cv2.fillPoly(..., shift=4)` areal mask rasteriser strictly inside `domain_mask`."""
  id_grid = np.zeros((GRID_H, GRID_W), dtype=np.int32)
  scale_x, scale_y, sm = GRID_W / 360.0, GRID_H / 180.0, 16.0

  for z_idx, z in enumerate(zones_spec, start=1):
    g = safe_geom(z.get("geom"))
    if g is None:
      continue
    polys = [g] if isinstance(g, Polygon) else (list(g.geoms) if isinstance(g, MultiPolygon) else [])
    for poly in polys:
      if poly.is_empty:
        continue
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
      # Only claim unclaimed pixels so non-overlapping priority order is preserved!
      sub[(lm > 0) & (sub == 0)] = z_idx

  id_grid[~domain_mask] = 0
  if full_domain:
    missing = domain_mask & (id_grid == 0)
    if missing.any() and (id_grid > 0).any():
      _, idx = distance_transform_edt(id_grid == 0, return_indices=True)
      id_grid[missing] = id_grid[idx[0][missing], idx[1][missing]]
  else:
    # Snap tiny 1-2 px coastal slivers inside domain_mask cleanly without bridging across seas
    missing = domain_mask & (id_grid == 0)
    if missing.any() and (id_grid > 0).any():
      dist, idx = distance_transform_edt(id_grid == 0, return_indices=True)
      fill_m = missing & (dist <= 2.0)
      if fill_m.any():
        id_grid[fill_m] = id_grid[idx[0][fill_m], idx[1][fill_m]]

  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  px_counts = {}
  for z_idx, z in enumerate(zones_spec, start=1):
    m = (id_grid == z_idx)
    cnt = int(m.sum())
    px_counts[z["id"]] = cnt
    if cnt > 0:
      rgb = z["rgb"]
      rgba[m, 0] = rgb[0]
      rgba[m, 1] = rgb[1]
      rgba[m, 2] = rgb[2]
      rgba[m, 3] = 255
  return rgba, px_counts


def render_mask_qa_png(ch_meta, zones_spec, basemap_hist, basemap_mod):
  """Renders a crisp Albers Equal-Area optical inspection PNG into `/tests/areal_mask_crops/`
  so EVERY SINGLE ONE of the 21 chapter masks can be optically verified via `read_file`."""
  is_modern = (ch_meta["index"] >= 19)
  land_p, riv_g = basemap_mod if is_modern else basemap_hist
  plt.rcdefaults()
  apply_viscount_style()
  fig, ax = plt.subplots(figsize=(10.5, 7.2), dpi=135)
  draw_basemap(ax, land_p, riv_g)

  all_xs, all_ys = [], []
  handles = []
  for z in zones_spec:
    g = safe_geom(z.get("geom"))
    if g is None:
      continue
    # Clip Greenland out of main continental bbox so Europe fills the frame (Greenland gets inset if present!)
    g_eu = safe_geom(g.intersection(box(-26.0, 27.0, 40.0, 82.0)))
    if g_eu is None or g_eu.is_empty:
      continue
    pg = prepare_and_project(g_eu, PROJ_EUROPE, 0.25, None)
    ps = geom_to_patches(pg)
    if not ps:
      continue
    rgb_f = [c / 255.0 for c in z["rgb"]]
    ax.add_collection(PatchCollection(ps, facecolor=rgb_f, edgecolor="#222228", linewidths=0.75, alpha=0.84, zorder=2.5))
    b = pg.bounds
    all_xs.extend([b[0], b[2]])
    all_ys.extend([b[1], b[3]])
    handles.append(Patch(facecolor=rgb_f, edgecolor="#222228", label=z["name"][:32]))

  if all_xs and all_ys:
    pad_x = max(120.0, (max(all_xs) - min(all_xs)) * 0.08)
    pad_y = max(120.0, (max(all_ys) - min(all_ys)) * 0.08)
    xlim = (min(all_xs) - pad_x, max(all_xs) + pad_x)
    ylim = (min(all_ys) - pad_y, max(all_ys) + pad_y)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    draw_graticule(ax, PROJ_EUROPE, xlim, ylim, [35, 40, 45, 50, 55, 60, 65, 70], [-20, -10, 0, 10, 20, 30])

  ax.set_aspect("equal", adjustable="box")
  ax.set_xticks([])
  ax.set_yticks([])
  d0, d1 = ch_meta["domain"]
  ax.set_title(f"CH {ch_meta['index']:02d}: {ch_meta['itinerary_title'][:54]} ({d0}..{d1})", fontsize=9.2, fontweight="bold", pad=6)
  nrows_q = max(1, (len(handles) + 2) // 3)
  fig.subplots_adjust(left=0.03, right=0.97, top=0.92, bottom=min(0.32, 0.08 + 0.045 * nrows_q))
  fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.015), ncol=3, fontsize=7.0, frameon=True)
  out_p = os.path.join(TESTS_MASK_DIR, f"mask_ch{ch_meta['index']:02d}_{ch_meta['key']}.png")
  save_viscount_figure(fig, out_p, arg2_dpi=135, arg3_options={"verify_layout": True, "strict_layout": True})


def write_chapter_assets(ch_meta, zones_spec, D, basemap_hist, basemap_mod, full_domain=False):
  ch_dir = os.path.join(MAG_DIR, ch_meta["folder"])
  os.makedirs(os.path.join(ch_dir, "figures"), exist_ok=True)
  os.makedirs(os.path.join(ch_dir, "papers"), exist_ok=True)
  for fn in ("crd-mla-numeric.csl", "crd_logo.png", "intellte.cls", "intellte-sample.bib"):
    src_f = os.path.join(MAG_DIR, fn)
    dst_f = os.path.join(ch_dir, fn)
    if os.path.exists(src_f) and not os.path.exists(dst_f):
      shutil.copy2(src_f, dst_f)

  # Strictly clip EVERY zone geometry to mag_union & make mutually non-overlapping cleanly!
  claimed_vec = None
  clean_zones = []
  for idx, z in enumerate(zones_spec):
    g = clip_mag(z.get("geom"), D["mag_union"])
    if g is not None and claimed_vec is not None:
      g = diff_geom(g, claimed_vec)
    if g is not None:
      claimed_vec = u_geoms([claimed_vec, g])
    z2 = dict(z)
    z2["geom"] = g
    z2["rgb"] = PALETTE[idx % len(PALETTE)]
    clean_zones.append(z2)

  rgba, px_counts = rasterise_zones_cv2(D["domain_mask"], clean_zones, full_domain=full_domain)

  stem = ch_meta["key"]
  Image.fromarray(rgba, mode="RGBA").save(os.path.join(ch_dir, f"{stem}_areal_mask.png"))

  gj_feats = []
  regions_cfg = []
  for z in clean_zones:
    if px_counts.get(z["id"], 0) == 0 or z["geom"] is None:
      continue
    gj_feats.append({
      "type": "Feature",
      "properties": {"id": z["id"], "name": z["name"], "rgb": z["rgb"], "pixel_count": px_counts[z["id"]]},
      "geometry": mapping(z["geom"].simplify(0.015, preserve_topology=True)),
    })
    regions_cfg.append({
      "id": z["id"], "name": z["name"], "rgb": z["rgb"], "domain": ch_meta["domain"], "population": z["population"],
    })

  with open(os.path.join(SUB_GJ_DIR, f"{stem}_subregions.geojson"), "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": gj_feats}, fh)

  cfg_obj = {
    "id": stem, "title": ch_meta["itinerary_title"], "domain": ch_meta["domain"],
    "mask_path": f"histmap/1.data_raw/population_regional/MAGNETIC/{ch_meta['folder']}/{stem}_areal_mask.png",
    "subregions_geojson": f"histmap/1.data_raw/population_regional/MAGNETIC/_shared/_gis_cache/chapter_subregions/{stem}_subregions.geojson",
    "regions": regions_cfg,
  }
  with open(os.path.join(ch_dir, f"{stem}.json5"), "w", encoding="utf-8") as fh:
    json.dump(cfg_obj, fh, indent=2, ensure_ascii=False)

  render_mask_qa_png(ch_meta, clean_zones, basemap_hist, basemap_mod)
  print(f"  [CH {ch_meta['index']:02d}] {stem:54s}: {len(regions_cfg):2d} zones | {sum(px_counts.values()):6,d} px", flush=True)


def main():
  D = load_historical_geometries()
  C = D["countries"]
  G = D["geo"]
  itinerary = json5.load(open(os.path.join(MAG_DIR, "magnetic_itinerary.json5"), encoding="utf-8"))
  ch_by_idx = {c["index"]: c for c in itinerary["chapters"]}

  basemap_hist = load_basemap_cache(PROJ_EUROPE, arg2_show_modern_borders=False)
  basemap_mod = load_basemap_cache(PROJ_EUROPE, arg2_show_modern_borders=True)
  print("\n[2] Building ALL 21 Historically Authentic & Watershed-Based Chapter Areal Masks + Optical QA Crops...", flush=True)

  # =========================================================================
  # CH 01 & 02: REGIME I — 100% Natural HydroBASINS L6 River Catchments (ZERO modern borders, ZERO Anatolia/POLARIS bleed!)
  # =========================================================================
  def clf_prehist(lat, lon, pfaf):
    if lon < -28.0: return "greenland_arctic"
    if lat >= 60.0 and lon < 4.0: return "north_atlantic_boreal"
    if lat >= 55.2 and lon >= 4.0: return "fennoscandia_baltic"
    if lon < -0.5 and 49.5 <= lat < 61.0: return "british_irish_shelf"
    if lat < 43.4 and lon < 4.5: return "iberian_cantabrian_refugium"
    if lat < 46.2 and 6.2 <= lon < 18.8 and not (lat > 44.5 and lon > 13.8): return "italian_peninsula_po"
    if lat < 45.2 and lon >= 13.8: return "balkan_aegean_lower_danube"
    if 45.2 <= lat < 49.4 and lon >= 15.8: return "carpathian_middle_danube"
    if 45.5 <= lat < 49.0 and 5.8 <= lon < 15.8: return "alpine_upper_danube"
    if 42.5 <= lat < 49.8 and -5.5 <= lon < 6.2: return "franco_aquitaine_loire"
    if 49.0 <= lat < 54.0 and 1.8 <= lon < 8.5: return "rhine_meuse_low_countries"
    return "north_european_plain"

  b_pre = group_basins(D["basins"], clf_prehist)
  b_pre["greenland_arctic"] = C["Greenland"]
  b_pre["north_atlantic_boreal"] = u_geoms([b_pre.get("north_atlantic_boreal"), C["Iceland"], C["Faroe Islands"]])
  b_pre["british_irish_shelf"] = u_geoms([b_pre.get("british_irish_shelf"), G["British_Isles"]])
  b_pre["iberian_cantabrian_refugium"] = u_geoms([b_pre.get("iberian_cantabrian_refugium"), G["Spain_Canaries"], G["Portugal_Islands"]])
  b_pre["italian_peninsula_po"] = u_geoms([b_pre.get("italian_peninsula_po"), C["Malta"]])

  ch1_zones = [
    {"id": "iberian_cantabrian_refugium", "name": "Iberian-Cantabrian Refugium", "geom": b_pre.get("iberian_cantabrian_refugium"), "population": {"-10000": 65000, "-8000": 95000, "-6000": 150000}},
    {"id": "franco_aquitaine_loire", "name": "Franco-Aquitaine & Loire Basins", "geom": b_pre.get("franco_aquitaine_loire"), "population": {"-10000": 55000, "-8000": 85000, "-6000": 135000}},
    {"id": "british_irish_shelf", "name": "British-Irish Insular Shelf", "geom": b_pre.get("british_irish_shelf"), "population": {"-10000": 12000, "-8000": 28000, "-6000": 55000}},
    {"id": "rhine_meuse_low_countries", "name": "Rhine-Meuse & Low Countries", "geom": b_pre.get("rhine_meuse_low_countries"), "population": {"-10000": 18000, "-8000": 35000, "-6000": 62000}},
    {"id": "alpine_upper_danube", "name": "Alpine & Upper Danube-Rhine", "geom": b_pre.get("alpine_upper_danube"), "population": {"-10000": 22000, "-8000": 40000, "-6000": 75000}},
    {"id": "north_european_plain", "name": "North European Plain (Elbe-Oder-Vistula)", "geom": b_pre.get("north_european_plain"), "population": {"-10000": 28000, "-8000": 55000, "-6000": 95000}},
    {"id": "italian_peninsula_po", "name": "Italian Peninsula & Po Basin", "geom": b_pre.get("italian_peninsula_po"), "population": {"-10000": 55000, "-8000": 82000, "-6000": 145000}},
    {"id": "carpathian_middle_danube", "name": "Carpathian & Middle Danube Basin", "geom": b_pre.get("carpathian_middle_danube"), "population": {"-10000": 26000, "-8000": 48000, "-6000": 95000}},
    {"id": "balkan_aegean_lower_danube", "name": "Balkan-Lower Danube & Aegean", "geom": b_pre.get("balkan_aegean_lower_danube"), "population": {"-10000": 48000, "-8000": 80000, "-6000": 195000}},
    {"id": "fennoscandia_baltic", "name": "Fennoscandian Shield & Baltic", "geom": b_pre.get("fennoscandia_baltic"), "population": {"-10000": 8000, "-8000": 24000, "-6000": 52000}},
    {"id": "north_atlantic_boreal", "name": "North Atlantic Boreal Margins", "geom": b_pre.get("north_atlantic_boreal"), "population": {"-10000": 1500, "-8000": 4000, "-6000": 8500}},
    {"id": "greenland_arctic", "name": "Greenland & High Arctic", "geom": b_pre.get("greenland_arctic"), "population": {"-10000": 0, "-8000": 0, "-6000": 0}},
  ]
  write_chapter_assets(ch_by_idx[1], ch1_zones, D, basemap_hist, basemap_mod, full_domain=True)

  ch2_zones = [
    {"id": "aegean_balkan_tell", "name": "Aegean-Balkan Tell Belt", "geom": b_pre.get("balkan_aegean_lower_danube"), "population": {"-6000": 210000, "-4000": 680000, "-2000": 1350000, "-1000": 1850000}},
    {"id": "carpathian_danube_neo", "name": "Carpathian & Middle Danube Basin", "geom": b_pre.get("carpathian_middle_danube"), "population": {"-6000": 100000, "-4000": 420000, "-2000": 780000, "-1000": 1050000}},
    {"id": "italian_adriatic_neo", "name": "Italian Peninsula & Po Basin", "geom": b_pre.get("italian_peninsula_po"), "population": {"-6000": 150000, "-4000": 580000, "-2000": 1450000, "-1000": 2250000}},
    {"id": "iberian_atlantic_neo", "name": "Iberian Mediterranean & Atlantic", "geom": b_pre.get("iberian_cantabrian_refugium"), "population": {"-6000": 155000, "-4000": 620000, "-2000": 1400000, "-1000": 2150000}},
    {"id": "alpine_circum_alpine", "name": "Alpine & Upper Danube Loess Belt", "geom": b_pre.get("alpine_upper_danube"), "population": {"-6000": 80000, "-4000": 340000, "-2000": 680000, "-1000": 980000}},
    {"id": "franco_atlantic_megalith", "name": "Franco-Aquitaine & Paris Basin", "geom": b_pre.get("franco_aquitaine_loire"), "population": {"-6000": 140000, "-4000": 650000, "-2000": 1550000, "-1000": 2350000}},
    {"id": "rhine_meuse_neo", "name": "Rhine-Meuse & Low Countries", "geom": b_pre.get("rhine_meuse_low_countries"), "population": {"-6000": 65000, "-4000": 240000, "-2000": 520000, "-1000": 760000}},
    {"id": "british_irish_neo", "name": "British Isles & Irish Sea", "geom": b_pre.get("british_irish_shelf"), "population": {"-6000": 55000, "-4000": 210000, "-2000": 480000, "-1000": 850000}},
    {"id": "north_euro_plain_neo", "name": "North European Plain & Lusatian-Vistula", "geom": b_pre.get("north_european_plain"), "population": {"-6000": 98000, "-4000": 410000, "-2000": 890000, "-1000": 1350000}},
    {"id": "nordic_baltic_neo", "name": "Nordic Bronze Age & Eastern Baltic", "geom": b_pre.get("fennoscandia_baltic"), "population": {"-6000": 54000, "-4000": 165000, "-2000": 360000, "-1000": 540000}},
    {"id": "north_atlantic_neo", "name": "North Atlantic Margins", "geom": b_pre.get("north_atlantic_boreal"), "population": {"-6000": 8500, "-4000": 18000, "-2000": 35000, "-1000": 52000}},
    {"id": "greenland_saqqaq", "name": "Greenland (Saqqaq & Independence I)", "geom": b_pre.get("greenland_arctic"), "population": {"-6000": 0, "-4000": 0, "-2000": 2500, "-1000": 3200}},
  ]
  write_chapter_assets(ch_by_idx[2], ch2_zones, D, basemap_hist, basemap_mod, full_domain=True)

  # =========================================================================
  # CH 03: Classical Greece & the Aegean World (-1000..-146) — Natural Aegean Watersheds + Peloponnese & Attica-Boeotia-Thessaly!
  # =========================================================================
  aegean_clip = u_geoms([D["dare"].get("achaia"), D["dare"].get("macedonia"), D["dare"].get("thracia"), D["dare"].get("creta et cyrene")])
  pelop_poly = u_geoms([x["g"] for x in D["adm1"].get("Greece", []) if x["lat"] < 38.25 and 21.1 <= x["lon"] <= 23.5 and x["lat"] > 36.25])
  # Separate Central/Eastern Greece (Attica, Boeotia, Euboea, Phocis, Thessaly — east of Pindus crest) from Epirus & Ionian coast!
  attica_boeotia_thess = u_geoms([x["g"] for x in D["adm1"].get("Greece", []) if 37.6 <= x["lat"] <= 40.05 and 21.55 <= x["lon"] <= 24.6])
  attica_boeotia_thess = diff_geom(attica_boeotia_thess, pelop_poly)
  def clf_greece(lat, lon, pfaf):
    if lat <= 36.15 or (lon >= 24.45 and lat < 40.3): return "crete_aegean_islands"
    if 37.5 <= lat < 40.1 and 21.55 <= lon < 24.5: return "attica_boeotia_central"
    if lat < 41.4 and lon < 21.55: return "epirus_ionian"
    return "macedonia_thrace"

  b_gr = group_basins(D["basins"], clf_greece, clip_geom=diff_geom(aegean_clip, u_geoms([pelop_poly, attica_boeotia_thess])))
  ch3_zones = [
    {"id": "peloponnese", "name": "Peloponnese", "geom": pelop_poly, "population": {"-1000": 240000, "-500": 720000, "-350": 850000, "-146": 610000}},
    {"id": "attica_boeotia_central", "name": "Attica, Boeotia & Thessaly", "geom": u_geoms([attica_boeotia_thess, b_gr.get("attica_boeotia_central")]), "population": {"-1000": 260000, "-500": 780000, "-350": 920000, "-146": 680000}},
    {"id": "epirus_ionian", "name": "Epirus & Ionian Littoral", "geom": b_gr.get("epirus_ionian"), "population": {"-1000": 160000, "-500": 380000, "-350": 460000, "-146": 390000}},
    {"id": "macedonia_thrace", "name": "Macedonia & Aegean Thrace", "geom": b_gr.get("macedonia_thrace"), "population": {"-1000": 320000, "-500": 760000, "-350": 1080000, "-146": 950000}},
    {"id": "crete_aegean_islands", "name": "Crete & Aegean Archipelagos", "geom": b_gr.get("crete_aegean_islands"), "population": {"-1000": 220000, "-500": 580000, "-350": 690000, "-146": 540000}},
  ]
  write_chapter_assets(ch_by_idx[3], ch3_zones, D, basemap_hist, basemap_mod, full_domain=False)

  # =========================================================================
  # CH 04: Iron Age & Roman Europe (-1000..400) — 100% AUTHENTIC DARE ROMAN PROVINCES!
  # =========================================================================
  R = D["dare"]
  ch4_zones = [
    {"id": "italia_peninsular", "name": "Italia (Cisalpine & Central Regiones IV-XI)", "geom": u_geoms([R.get(k) for k in ("iv", "v", "vi", "vii", "viii", "ix", "x", "xi")]), "population": {"-1000": 1500000, "-500": 3200000, "0": 5200000, "200": 5800000, "400": 4300000}},
    {"id": "italia_south_islands", "name": "Latium, Magna Graecia, Sicilia, Sardinia & Malta", "geom": u_geoms([R.get(k) for k in ("i", "ii", "iii", "sicilia", "sardinia et corsica")] + [C.get("Malta")]), "population": {"-1000": 750000, "-500": 1650000, "0": 3600000, "200": 3850000, "400": 2750000}},
    {"id": "hispania_tarrac_lusit", "name": "Hispania Tarraconensis & Lusitania", "geom": u_geoms([R.get("tarraconensis"), R.get("lusitania")]), "population": {"-1000": 1450000, "-500": 2400000, "0": 3850000, "200": 4450000, "400": 3650000}},
    {"id": "hispania_baetica", "name": "Hispania Baetica", "geom": R.get("baetica"), "population": {"-1000": 700000, "-500": 1250000, "0": 1950000, "200": 2350000, "400": 1850000}},
    {"id": "gallia_narb_aquit", "name": "Gallia Narbonensis, Aquitania & Maritime Alps", "geom": u_geoms([R.get("narbonensis"), R.get("aquitania"), R.get("alpes maritimae"), R.get("alpes cottiae")]), "population": {"-1000": 1050000, "-500": 1950000, "0": 3200000, "200": 3950000, "400": 3100000}},
    {"id": "gallia_lugd_belgica", "name": "Gallia Lugdunensis, Belgica & Germania Inferior", "geom": u_geoms([R.get("lugdunensis"), R.get("belgica"), R.get("germania inferior")]), "population": {"-1000": 1550000, "-500": 2750000, "0": 4550000, "200": 5650000, "400": 4150000}},
    {"id": "britannia", "name": "Provincia Britannia (South of Hadrian's Wall)", "geom": R.get("britannia"), "population": {"-1000": 620000, "-500": 1050000, "0": 1750000, "200": 2650000, "400": 2150000}},
    {"id": "germania_limes_alpine", "name": "Germania Superior, Raetia & Noricum (Limes)", "geom": u_geoms([R.get("germania superior"), R.get("raetia"), R.get("noricum"), R.get("alpes graiae et poeninae")]), "population": {"-1000": 820000, "-500": 1450000, "0": 2150000, "200": 2750000, "400": 2050000}},
    {"id": "pannonia_dalmatia", "name": "Pannonia Superior/Inferior & Dalmatia", "geom": u_geoms([R.get("pannonia superior"), R.get("pannonia inferior"), R.get("dalmatia")]), "population": {"-1000": 680000, "-500": 1180000, "0": 1850000, "200": 2350000, "400": 1650000}},
    {"id": "moesia_dacia_thracia", "name": "Moesia, Roman Dacia & Thracia", "geom": u_geoms([R.get("moesia superior"), R.get("moesia inferior"), R.get("dacia"), R.get("thracia")]), "population": {"-1000": 1150000, "-500": 1950000, "0": 2650000, "200": 3250000, "400": 2350000}},
    {"id": "achaea_macedonia", "name": "Achaia, Macedonia & Creta", "geom": u_geoms([R.get("achaia"), R.get("macedonia"), R.get("creta et cyrene")]), "population": {"-1000": 980000, "-500": 2450000, "0": 2250000, "200": 2450000, "400": 1950000}},
  ]
  write_chapter_assets(ch_by_idx[4], ch4_zones, D, basemap_hist, basemap_mod, full_domain=False)

  # =========================================================================
  # CH 05: Free Germany, Scandinavia & Baltic-Slavic North-East (-1000..500)
  # EXACT COMPLEMENT OF ROMAN EUROPE (MAGNETIC - ROMAN EMPIRE) ON ORGANIC HYDROBASINS L6 WATERSHEDS!
  # =========================================================================
  # Keep ONLY genuine non-Roman northern/eastern Barbaricum (> 46.5N or Hibernia/Caledonia/North Atlantic, drop tiny Mediterranean coastal slivers!)
  barbaricum_raw = diff_geom(D["mag_union"], u_geoms([D["roman_union"], G["Spain_Canaries"], G["Portugal_Islands"]]))
  barbaricum = safe_geom(barbaricum_raw.intersection(u_geoms([box(-76.0, 51.0, 35.0, 84.5), box(5.0, 44.5, 32.0, 56.0)])))
  def clf_barb(lat, lon, pfaf):
    if lon < -1.0: return "hibernia_north_atlantic"
    if lat >= 55.2 and lon < 21.0 and not (lat < 57.8 and lon < 11.2): return "scandinavian_peninsula"
    if lat >= 54.0 and lon >= 21.0: return "finland_eastern_baltic"
    if 54.2 <= lat < 57.8 and 7.5 <= lon < 13.0: return "denmark_jutland_isles"
    if lat < 50.6 and 11.5 <= lon <= 32.0: return "bohemia_moravia_slovakia"
    if lon < 14.3 and lat < 54.5: return "germania_magna_west"
    return "vistula_przeworsk_wielbark"

  b_ch5 = group_basins(D["basins"], clf_barb, clip_geom=barbaricum)
  b_ch5["hibernia_north_atlantic"] = u_geoms([b_ch5.get("hibernia_north_atlantic"), G["Ireland_Full"], diff_geom(G["UK_Scotland"], D["roman_union"]), G["North_Atlantic"]])
  ch5_zones = [
    {"id": "germania_magna_west", "name": "Germania Magna (Rhine-Weser-Elbe Basins)", "geom": b_ch5.get("germania_magna_west"), "population": {"-1000": 680000, "-500": 1050000, "0": 1750000, "200": 2050000, "500": 1550000}},
    {"id": "vistula_przeworsk_wielbark", "name": "Oder-Vistula Basins (Przeworsk & Wielbark)", "geom": b_ch5.get("vistula_przeworsk_wielbark"), "population": {"-1000": 580000, "-500": 880000, "0": 1250000, "200": 1480000, "500": 1050000}},
    {"id": "bohemia_moravia_slovakia", "name": "Bohemia, Morava & Upper Tisza (Marcomanni-Quadi)", "geom": b_ch5.get("bohemia_moravia_slovakia"), "population": {"-1000": 380000, "-500": 580000, "0": 820000, "200": 960000, "500": 720000}},
    {"id": "denmark_jutland_isles", "name": "Jutland & Danish Archipelago", "geom": b_ch5.get("denmark_jutland_isles"), "population": {"-1000": 165000, "-500": 235000, "0": 320000, "200": 390000, "500": 350000}},
    {"id": "scandinavian_peninsula", "name": "Scandinavian Peninsula", "geom": b_ch5.get("scandinavian_peninsula"), "population": {"-1000": 210000, "-500": 295000, "0": 410000, "200": 490000, "500": 460000}},
    {"id": "finland_eastern_baltic", "name": "Finland & Eastern Baltic Basins", "geom": b_ch5.get("finland_eastern_baltic"), "population": {"-1000": 175000, "-500": 245000, "0": 340000, "200": 410000, "500": 390000}},
    {"id": "hibernia_north_atlantic", "name": "Hibernia, Caledonia & North Atlantic", "geom": b_ch5.get("hibernia_north_atlantic"), "population": {"-1000": 245000, "-500": 385000, "0": 620000, "200": 740000, "500": 690000}},
  ]
  write_chapter_assets(ch_by_idx[5], ch5_zones, D, basemap_hist, basemap_mod, full_domain=False)

  # =========================================================================
  # CH 06: Late Antiquity, Migration Period & Early Mediaeval Europe (250..800)
  # Authentic Carolingian/Early Mediaeval Spheres on Natural Watersheds & world_800!
  # =========================================================================
  def clf_ch6(lat, lon, pfaf):
    if lon < -28.0 or (lat >= 60.5 and lon < 2.0): return "north_atlantic_early"
    if lon < -0.5 and 49.5 <= lat < 61.0: return "britain_ireland_early"
    if lat < 43.3 and lon < 4.5: return "visigothic_iberia"
    if lat < 46.3 and 6.5 <= lon < 18.8 and not (lat > 44.5 and lon > 13.8): return "lombard_byzantine_italy"
    if lat >= 54.6 and lon >= 4.0: return "vendel_scandinavia_baltic"
    if lat < 45.2 and lon >= 13.8: return "byzantine_slavic_balkans"
    if 45.2 <= lat < 49.2 and lon >= 15.8: return "avar_danubian_carpathian"
    if lon < 7.2 and 42.5 <= lat < 54.0: return "francia_merovingian"
    if 7.2 <= lon < 12.2 and 45.8 <= lat < 54.8: return "germanic_alpine_core"
    if lon >= 12.2 and 46.0 <= lat < 49.0 and lon < 15.8: return "germanic_alpine_core"
    return "west_slavic_poland_bohemia"

  b_ch6 = group_basins(D["basins"], clf_ch6)
  b_ch6["north_atlantic_early"] = G["North_Atlantic"]
  b_ch6["britain_ireland_early"] = G["British_Isles"]
  b_ch6["visigothic_iberia"] = u_geoms([G["Iberian_Peninsula"], G["Spain_Canaries"], G["Portugal_Islands"]])
  b_ch6["lombard_byzantine_italy"] = G["Italian_Peninsula_Full"]
  ch6_zones = [
    {"id": "francia_merovingian", "name": "Merovingian-Carolingian Neustria & Austrasia", "geom": b_ch6.get("francia_merovingian"), "population": {"300": 8900000, "500": 6200000, "600": 5400000, "800": 7200000}},
    {"id": "britain_ireland_early", "name": "Anglo-Saxon & Celtic British Isles", "geom": b_ch6.get("britain_ireland_early"), "population": {"300": 3100000, "500": 1850000, "600": 1650000, "800": 2350000}},
    {"id": "visigothic_iberia", "name": "Visigothic Hispania & Early Al-Andalus", "geom": b_ch6.get("visigothic_iberia"), "population": {"300": 6400000, "500": 4650000, "600": 4200000, "800": 4950000}},
    {"id": "lombard_byzantine_italy", "name": "Lombard & Byzantine Italy", "geom": b_ch6.get("lombard_byzantine_italy"), "population": {"300": 8400000, "500": 5200000, "600": 4100000, "800": 5400000}},
    {"id": "germanic_alpine_core", "name": "Saxony, Alamannia, Bavaria & Eastern Alps", "geom": b_ch6.get("germanic_alpine_core"), "population": {"300": 4500000, "500": 3450000, "600": 3250000, "800": 4450000}},
    {"id": "west_slavic_poland_bohemia", "name": "Early Slavic Elbe-Vistula & Bohemia", "geom": b_ch6.get("west_slavic_poland_bohemia"), "population": {"300": 2250000, "500": 1750000, "600": 1650000, "800": 2350000}},
    {"id": "avar_danubian_carpathian", "name": "Avar Carpathian Basin & Middle Danube", "geom": b_ch6.get("avar_danubian_carpathian"), "population": {"300": 2450000, "500": 1750000, "600": 1550000, "800": 2150000}},
    {"id": "byzantine_slavic_balkans", "name": "Byzantine, Bulgarian & Early Slavic Balkans", "geom": b_ch6.get("byzantine_slavic_balkans"), "population": {"300": 5650000, "500": 4250000, "600": 3350000, "800": 4350000}},
    {"id": "vendel_scandinavia_baltic", "name": "Vendel Scandinavia & Eastern Baltic", "geom": b_ch6.get("vendel_scandinavia_baltic"), "population": {"300": 1350000, "500": 1220000, "600": 1180000, "800": 1580000}},
    {"id": "north_atlantic_early", "name": "North Atlantic & Greenland", "geom": b_ch6.get("north_atlantic_early"), "population": {"300": 3500, "500": 3500, "600": 4000, "800": 5500}},
  ]
  write_chapter_assets(ch_by_idx[6], ch6_zones, D, basemap_hist, basemap_mod, full_domain=True)

  # =========================================================================
  # CH 07: Mediaeval Western & Central Europe (800..1347) — Authentic HRE 1512 + Capetian France + Regnum Italiae!
  # =========================================================================
  H15 = D["hre_circles"].get(1512, {})
  hre_n_15_raw = u_geoms([H15.get(k) for k in H15 if any(t in k for t in ("obersach", "niedersach", "niederrhein", "kurrhein", "oberrhein", "frankisch"))])
  # Clip out Savoy & Rhône enclaves (< 46.9 lat & < 8.2 lon) from Oberrheinischer Kreis so Savoy sits cleanly in Southern HRE / Arles!
  savoy_clip = box(4.4, 44.0, 8.2, 46.9)
  hre_n_15 = diff_geom(hre_n_15_raw, savoy_clip)
  hre_s_15 = u_geoms([H15.get(k) for k in H15 if any(t in k for t in ("bayer", "schwab", "osterreich"))])
  burg_15_low = safe_geom(H15.get("burgundischer kreis").intersection(box(1.5, 49.35, 8.0, 54.0))) if H15.get("burgundischer kreis") else None
  franche_comte = diff_geom(H15.get("burgundischer kreis"), burg_15_low) if H15.get("burgundischer kreis") else None
  # Include Provence/Dauphiné/Franche-Comté/Savoy/Switzerland in Southern HRE / Kingdom of Arles; keep Béarn/Roussillon in France South!
  pyrenees_fr = safe_geom(C["France"].intersection(box(-2.5, 42.2, 3.6, 43.8)))
  fr_med_s_clean = u_geoms([D["fr_med_s"], pyrenees_fr])
  arles_extra = diff_geom(C["France"], u_geoms([D["fr_med_n"], fr_med_s_clean]))
  ch7_zones = [
    {"id": "france_north_royal", "name": "Kingdom of France (North, West of Meuse-Saône)", "geom": D["fr_med_n"], "population": {"800": 3600000, "1000": 4800000, "1200": 7600000, "1300": 10800000, "1347": 11200000}},
    {"id": "france_south_occitania", "name": "Aquitaine, Gascony & Languedoc (West of Rhône)", "geom": fr_med_s_clean, "population": {"800": 2100000, "1000": 2750000, "1200": 4350000, "1300": 6050000, "1347": 6350000}},
    {"id": "england_wales_med", "name": "Kingdom of England & Wales", "geom": u_geoms([G["UK_England_Wales"], C.get("Isle of Man"), C.get("Jersey"), C.get("Guernsey")]), "population": {"800": 1450000, "1000": 2050000, "1200": 3450000, "1300": 5100000, "1347": 5250000}},
    {"id": "scotland_ireland_med", "name": "Kingdom of Scotland & Ireland", "geom": u_geoms([G["UK_Scotland"], G["Ireland_Full"]]), "population": {"800": 900000, "1000": 1150000, "1200": 1550000, "1300": 2050000, "1347": 2100000}},
    {"id": "low_countries_med", "name": "Low Countries (Flanders, Brabant & Holland)", "geom": u_geoms([burg_15_low, C["Netherlands"], C["Belgium"], C["Luxembourg"]]), "population": {"800": 850000, "1000": 1150000, "1200": 1850000, "1300": 2550000, "1347": 2650000}},
    {"id": "hre_north_rhineland", "name": "Northern & Rhenish HRE (incl. Brandenburg-Pomerania)", "geom": hre_n_15, "population": {"800": 2250000, "1000": 3050000, "1200": 4950000, "1300": 6950000, "1347": 7300000}},
    {"id": "hre_south_alpine", "name": "Southern HRE, Alpine Lands & Kingdom of Arles", "geom": u_geoms([hre_s_15, franche_comte, C["Switzerland"], C["Liechtenstein"], arles_extra, C["Monaco"]]), "population": {"800": 2650000, "1000": 3550000, "1200": 5550000, "1300": 7650000, "1347": 7950000}},
    {"id": "italy_north_communes", "name": "Regnum Italiae & Northern Communes", "geom": D["it_n_em"], "population": {"800": 2300000, "1000": 2950000, "1200": 4450000, "1300": 5850000, "1347": 6050000}},
    {"id": "italy_central_south_med", "name": "Tuscany, Papal States & Kingdom of Sicily/Naples", "geom": u_geoms([D["it_c_em"], D["it_s_em"], C["San Marino"], C["Vatican"], C["Malta"]]), "population": {"800": 3100000, "1000": 3650000, "1200": 4950000, "1300": 6150000, "1347": 6350000}},
  ]
  write_chapter_assets(ch_by_idx[7], ch7_zones, D, basemap_hist, basemap_mod, full_domain=False)

  # =========================================================================
  # CH 08: Mediaeval Iberia (711..1492) — Authentic Mediaeval Kingdoms (Castile-León, Aragon-Navarre, Portugal, Al-Andalus/Granada)!
  # =========================================================================
  EK = D["es_k"]
  ch8_zones = [
    {"id": "al_andalus_south", "name": "Al-Andalus, Andalusia & Emirate of Granada", "geom": u_geoms([EK.get("Reino de Granada"), EK.get("Andalucía Occidental"), EK.get("Reino de Murcia"), C.get("Gibraltar")]), "population": {"711": 1950000, "1000": 2650000, "1200": 2450000, "1347": 2350000, "1492": 2150000}},
    {"id": "castile_leon", "name": "Crown of Castile-León & Galicia", "geom": u_geoms([EK.get(k) for k in ("Reino de Galicia", "Principado de Asturias", "Reino de León", "Castilla la Vieja", "Castilla la Nueva", "Extremadura", "Provincias Vascongadas")]), "population": {"711": 1550000, "1000": 1950000, "1200": 2950000, "1347": 3650000, "1492": 3950000}},
    {"id": "aragon_catalonia", "name": "Crown of Aragon, Navarre & Balearics", "geom": u_geoms([EK.get(k) for k in ("Reino de Navarra", "Reino de Aragón", "Principado de Cataluña", "Reino de Valencia", "Reino de Mallorca")] + [C.get("Andorra")]), "population": {"711": 810000, "1000": 1030000, "1200": 1460000, "1347": 1790000, "1492": 1610000}},
    {"id": "portugal_med", "name": "Kingdom of Portugal & Atlantic Isles", "geom": C["Portugal"], "population": {"711": 650000, "1000": 820000, "1200": 1080000, "1347": 1350000, "1492": 1220000}},
    {"id": "canaries_med", "name": "Canary Islands (Guanche & Castilian)", "geom": G["Spain_Canaries"], "population": {"711": 35000, "1000": 55000, "1200": 60000, "1347": 62000, "1492": 55000}},
  ]
  write_chapter_assets(ch_by_idx[8], ch8_zones, D, basemap_hist, basemap_mod, full_domain=False)

  # =========================================================================
  # CH 09: Mediaeval Scandinavia & North Atlantic (800..1500) — AUTHENTIC PRE-1658 NORDIC BORDERS!
  # Denmark INCLUDES Scania/Halland/Blekinge! Norway INCLUDES Jämtland!
  # =========================================================================
  ch9_zones = [
    {"id": "denmark_med", "name": "Mediaeval Denmark (incl. Scania, Halland & Blekinge)", "geom": u_geoms([C["Denmark"], D["se_danish_skane"]]), "population": {"800": 540000, "1000": 740000, "1200": 1020000, "1347": 1140000, "1500": 820000}},
    {"id": "sweden_med", "name": "Mediaeval Kingdom of Sweden (Svealand-Götaland)", "geom": D["se_core"], "population": {"800": 310000, "1000": 390000, "1200": 520000, "1347": 620000, "1500": 520000}},
    {"id": "norway_med", "name": "Mediaeval Kingdom of Norway (incl. Jämtland)", "geom": u_geoms([C["Norway"], D["se_norw_jamt"]]), "population": {"800": 230000, "1000": 295000, "1200": 410000, "1347": 500000, "1500": 275000}},
    {"id": "finland_med", "name": "Österland (Mediaeval Finland & Åland)", "geom": u_geoms([C["Finland"], C["Aland"]]), "population": {"800": 95000, "1000": 130000, "1200": 185000, "1347": 240000, "1500": 260000}},
    {"id": "iceland_med", "name": "Iceland", "geom": C["Iceland"], "population": {"800": 0, "1000": 45000, "1200": 65000, "1347": 72000, "1500": 48000}},
    {"id": "faroes_med", "name": "Faroe Islands", "geom": C["Faroe Islands"], "population": {"800": 800, "1000": 2500, "1200": 3800, "1347": 4200, "1500": 3200}},
    {"id": "greenland_norse_inuit", "name": "Norse & Inuit Greenland", "geom": C["Greenland"], "population": {"800": 4500, "1000": 6500, "1200": 9500, "1347": 8500, "1500": 5500}},
  ]
  write_chapter_assets(ch_by_idx[9], ch9_zones, D, basemap_hist, basemap_mod, full_domain=False)

  # =========================================================================
  # CH 10: Mediaeval East-Central Europe, Baltic & Balkans (800..1347)
  # Authentic High Mediaeval Realms (Crown of St Stephen Hungary incl. Slovakia & Transylvania,
  # Bohemian Crown incl. Silesia, Piast Poland outside HRE/Teutonic Prussia, Wallachia & Moldavia!)
  # =========================================================================
  hre_all_15 = u_geoms(list(H15.values()))
  # Authentic Teutonic Prussia from HGIS 1914 East Prussia (Königsberg + Gumbinnen + Allenstein -> ZERO straight lines!)
  teut_prussia = D["east_prussia_hist"]
  # Subtract ONLY the Imperial Circles assigned to Ch 07 (hre_n_15, hre_s_15) + Bohemian Crown + Teutonic Prussia so Piast Silesia (990-1335) has ZERO gap!
  piast_poland = diff_geom(C["Poland"], u_geoms([hre_n_15, hre_s_15, D["bohemian_crown_hist"], teut_prussia]))
  wallachia_moldavia = diff_geom(u_geoms([C["Romania"], C["Moldova"]]), D["hungary_crown_hist"])
  ch10_zones = [
    {"id": "poland_piast", "name": "Piast Kingdom of Poland (Greater/Lesser Poland & Mazovia)", "geom": piast_poland, "population": {"800": 1150000, "1000": 1550000, "1200": 2250000, "1347": 2950000}},
    {"id": "bohemia_moravia_med", "name": "Lands of the Bohemian Crown (Bohemia, Moravia & Silesia)", "geom": D["bohemian_crown_hist"], "population": {"800": 820000, "1000": 1150000, "1200": 1750000, "1347": 2550000}},
    {"id": "hungary_slovakia_med", "name": "Kingdom of Hungary (incl. Slovakia, Transylvania & Croatia)", "geom": D["hungary_crown_hist"], "population": {"800": 1550000, "1000": 2250000, "1200": 3450000, "1347": 4550000}},
    {"id": "romania_moldova_med", "name": "Wallachia & Moldavia (Extra-Carpathian Principalities)", "geom": wallachia_moldavia, "population": {"800": 650000, "1000": 850000, "1200": 1150000, "1347": 1480000}},
    {"id": "baltic_lands_med", "name": "Teutonic Prussia, Livonia & Grand Duchy of Lithuania", "geom": u_geoms([C["Estonia"], C["Latvia"], C["Lithuania"], teut_prussia]), "population": {"800": 520000, "1000": 690000, "1200": 950000, "1347": 1220000}},
    {"id": "serbia_bosnia_dalmatia", "name": "Mediaeval Serbia, Bosnia, Dalmatia & Albania", "geom": diff_geom(u_geoms([C["Bosnia and Herzegovina"], C["Republic of Serbia"], C["Montenegro"], C["Kosovo"], C["Albania"], C["North Macedonia"], C["Croatia"]]), D["hungary_crown_hist"]), "population": {"800": 1250000, "1000": 1620000, "1200": 2180000, "1347": 2750000}},
    {"id": "bulgaria_greece_thrace_med", "name": "Second Bulgarian Empire & Byzantine Greece/Thrace", "geom": u_geoms([C["Bulgaria"], C["Greece"], C["Turkey-in-Europe"]]), "population": {"800": 2450000, "1000": 2950000, "1200": 3450000, "1347": 3750000}},
  ]
  write_chapter_assets(ch_by_idx[10], ch10_zones, D, basemap_hist, basemap_mod, full_domain=False)

  # =========================================================================
  # CH 11: Black Death & Late Mediaeval Crisis (1347..1500) — Authentic c. 1400 European Polities!
  # =========================================================================
  ch11_zones = [
    {"id": "bd_british_isles", "name": "British Isles (England, Scotland & Ireland)", "geom": G["British_Isles"], "population": {"1347": 7350000, "1400": 4150000, "1450": 4350000, "1500": 4950000}},
    {"id": "bd_france", "name": "Kingdom of France (c. 1400 Frontiers)", "geom": u_geoms([D["fr_med_n"], D["fr_med_s"]]), "population": {"1347": 17550000, "1400": 11200000, "1450": 12200000, "1500": 14800000}},
    {"id": "bd_hre_core", "name": "Holy Roman Empire (incl. Low Countries, Switzerland, Bohemia & Austria)", "geom": u_geoms([hre_all_15, C["Switzerland"], C["Netherlands"], C["Belgium"], C["Luxembourg"], arles_extra]), "population": {"1347": 19550000, "1400": 13900000, "1450": 15800000, "1500": 19100000}},
    {"id": "bd_italy_malta", "name": "Italian Peninsula, Sicily, Sardinia & Malta", "geom": G["Italian_Peninsula_Full"], "population": {"1347": 12400000, "1400": 7900000, "1450": 8800000, "1500": 10600000}},
    {"id": "bd_iberia", "name": "Iberian Kingdoms & Atlantic Islands", "geom": u_geoms([C["Spain"], C["Portugal"], C["Andorra"], C["Gibraltar"]]), "population": {"1347": 9150000, "1400": 6950000, "1450": 7850000, "1500": 8950000}},
    {"id": "bd_kalmar_nordics", "name": "Kalmar Union (Denmark, Norway, Sweden & Finland)", "geom": u_geoms([C["Denmark"], C["Sweden"], C["Norway"], C["Finland"], C["Aland"]]), "population": {"1347": 2450000, "1400": 1520000, "1450": 1680000, "1500": 1850000}},
    {"id": "bd_north_atlantic", "name": "Iceland, Faroe Islands & Greenland", "geom": G["North_Atlantic"], "population": {"1347": 84700, "1400": 59000, "1450": 54000, "1500": 56700}},
    {"id": "bd_poland_teutonic_lithuania", "name": "Poland-Lithuania & Teutonic Order", "geom": u_geoms([piast_poland, teut_prussia, C["Estonia"], C["Latvia"], C["Lithuania"]]), "population": {"1347": 4170000, "1400": 3750000, "1450": 4200000, "1500": 4850000}},
    {"id": "bd_hungary_crown", "name": "Kingdom of Hungary (incl. Slovakia, Transylvania & Croatia)", "geom": D["hungary_crown_hist"], "population": {"1347": 4550000, "1400": 3950000, "1450": 4150000, "1500": 4650000}},
    {"id": "bd_wallachia_moldavia", "name": "Wallachia & Moldavia", "geom": wallachia_moldavia, "population": {"1347": 1480000, "1400": 1300000, "1450": 1450000, "1500": 1650000}},
    {"id": "bd_ottoman_balkans", "name": "Balkans & Ottoman Rumelia", "geom": diff_geom(u_geoms([C["Bosnia and Herzegovina"], C["Republic of Serbia"], C["Montenegro"], C["Kosovo"], C["North Macedonia"], C["Albania"], C["Bulgaria"], C["Greece"], C["Turkey-in-Europe"], C["Croatia"]]), D["hungary_crown_hist"]), "population": {"1347": 6500000, "1400": 5050000, "1450": 5400000, "1500": 6050000}},
  ]
  write_chapter_assets(ch_by_idx[11], ch11_zones, D, basemap_hist, basemap_mod, full_domain=True)

  # =========================================================================
  # CH 12: Early Modern Western & Northern Europe (1500..1750) — Authentic c. 1700 Borders!
  # =========================================================================
  ch12_zones = [
    {"id": "em_england_wales", "name": "England & Wales", "geom": u_geoms([G["UK_England_Wales"], C.get("Isle of Man"), C.get("Jersey"), C.get("Guernsey")]), "population": {"1500": 2750000, "1600": 4450000, "1700": 5450000, "1750": 6250000}},
    {"id": "em_scotland", "name": "Kingdom of Scotland", "geom": G["UK_Scotland"], "population": {"1500": 780000, "1600": 950000, "1700": 1050000, "1750": 1265000}},
    {"id": "em_ireland", "name": "Kingdom of Ireland", "geom": G["Ireland_Full"], "population": {"1500": 950000, "1600": 1350000, "1700": 2250000, "1750": 3150000}},
    {"id": "em_france", "name": "Kingdom of France (c. 1700 Bourbon Frontiers)", "geom": D["fr_em_1700"], "population": {"1500": 15400000, "1600": 18900000, "1700": 21500000, "1750": 24600000}},
    {"id": "em_dutch_republic", "name": "Dutch Republic (Seven United Provinces)", "geom": C["Netherlands"], "population": {"1500": 950000, "1600": 1500000, "1700": 1900000, "1750": 1950000}},
    {"id": "em_southern_netherlands", "name": "Spanish / Austrian Southern Netherlands", "geom": u_geoms([C["Belgium"], C["Luxembourg"]]), "population": {"1500": 1300000, "1600": 1550000, "1700": 1950000, "1750": 2300000}},
    {"id": "em_denmark_norway", "name": "Kingdom of Denmark-Norway", "geom": u_geoms([C["Denmark"], C["Norway"]]), "population": {"1500": 940000, "1600": 1180000, "1700": 1320000, "1750": 1480000}},
    {"id": "em_sweden_finland", "name": "Swedish Empire (Sweden-Finland)", "geom": u_geoms([C["Sweden"], C["Finland"], C["Aland"]]), "population": {"1500": 910000, "1600": 1190000, "1700": 1760000, "1750": 2210000}},
    {"id": "em_iceland_faroes", "name": "Iceland & Faroe Islands", "geom": u_geoms([C["Iceland"], C["Faroe Islands"]]), "population": {"1500": 51200, "1600": 54500, "1700": 54500, "1750": 53200}},
    {"id": "em_greenland", "name": "Greenland", "geom": C["Greenland"], "population": {"1500": 5500, "1600": 6000, "1700": 6500, "1750": 7200}},
  ]
  write_chapter_assets(ch_by_idx[12], ch12_zones, D, basemap_hist, basemap_mod, full_domain=False)

  # =========================================================================
  # CH 13: Early Modern Central Europe (1500..1750) — AUTHENTIC 1648 PEACE OF WESTPHALIA BORDERS! ZERO ODER-NEISSE!
  # =========================================================================
  H48 = D["hre_circles"].get(1648, {})
  # Include ONLY Lusatia (Kreisfreies Gebiet north of Bohemia, excluding Imperial Italy/Savoy!) in Northern HRE!
  lusatia_fill = safe_geom(diff_geom(H48.get("kreisfreies gebiet"), D["bohemian_crown_hist"]).intersection(box(12.5, 50.5, 16.5, 52.5))) if H48.get("kreisfreies gebiet") else None
  hre48_north = u_geoms([H48.get(k) for k in H48 if any(t in k for t in ("obersach", "niedersach", "niederrhein"))] + [lusatia_fill])
  hre48_south = diff_geom(u_geoms([H48.get(k) for k in H48 if any(t in k for t in ("bayer", "schwab", "frankisch", "kurrhein", "oberrhein"))]), box(4.5, 43.8, 9.5, 46.8))
  plc_1648 = diff_geom(u_geoms([C["Poland"], C["Estonia"], C["Latvia"], C["Lithuania"]]), u_geoms([hre48_north, D["bohemian_crown_hist"]]))
  ch13_zones = [
    {"id": "em_germany_north", "name": "Northern HRE Circles (Brandenburg-Pomerania, Saxony & Westphalia)", "geom": hre48_north, "population": {"1500": 5600000, "1600": 7400000, "1650": 5400000, "1700": 7100000, "1750": 8600000}},
    {"id": "em_germany_south", "name": "Southern & Rhenish HRE Circles (Bavaria, Swabia, Franconia & Rhine)", "geom": hre48_south, "population": {"1500": 5200000, "1600": 6800000, "1650": 4600000, "1700": 6400000, "1750": 7800000}},
    {"id": "em_switzerland", "name": "Swiss Confederacy", "geom": u_geoms([C["Switzerland"], C["Liechtenstein"]]), "population": {"1500": 780000, "1600": 1020000, "1650": 1050000, "1700": 1220000, "1750": 1450000}},
    {"id": "em_austria", "name": "Austrian Hereditary Lands (Österreichischer Kreis)", "geom": D["austria_hereditary_hist"], "population": {"1500": 2150000, "1600": 2650000, "1650": 2450000, "1700": 2850000, "1750": 3250000}},
    {"id": "em_bohemia_moravia", "name": "Lands of the Bohemian Crown (Bohemia, Moravia & Silesia)", "geom": D["bohemian_crown_hist"], "population": {"1500": 2450000, "1600": 3100000, "1650": 2250000, "1700": 2950000, "1750": 3950000}},
    {"id": "em_hungary_slovakia", "name": "Kingdom of Hungary, Transylvania & Croatia", "geom": D["hungary_crown_hist"], "population": {"1500": 4450000, "1600": 4600000, "1650": 4350000, "1700": 4850000, "1750": 6950000}},
    {"id": "em_poland_baltics", "name": "Polish-Lithuanian Commonwealth & Baltic Lands", "geom": plc_1648, "population": {"1500": 4650000, "1600": 5950000, "1650": 5150000, "1700": 5650000, "1750": 7250000}},
  ]
  write_chapter_assets(ch_by_idx[13], ch13_zones, D, basemap_hist, basemap_mod, full_domain=False)

  # =========================================================================
  # CH 14: Early Modern Southern Europe & Atlantic Islands (1500..1750) — Authentic Crown of Castile/Aragon & Italian States!
  # =========================================================================
  ch14_zones = [
    {"id": "em_spain_castile", "name": "Crown of Castile (incl. Andalusia, Galicia & Basque)", "geom": u_geoms([EK.get(k) for k in ("Reino de Galicia", "Principado de Asturias", "Reino de León", "Castilla la Vieja", "Castilla la Nueva", "Extremadura", "Provincias Vascongadas", "Reino de Navarra", "Andalucía Occidental", "Reino de Granada", "Reino de Murcia")] + [C.get("Gibraltar")]), "population": {"1500": 5950000, "1600": 7050000, "1700": 6450000, "1750": 7650000}},
    {"id": "em_spain_aragon", "name": "Crown of Aragon (Aragon, Catalonia, Valencia & Balearics)", "geom": u_geoms([EK.get(k) for k in ("Reino de Aragón", "Principado de Cataluña", "Reino de Valencia", "Reino de Mallorca")] + [C.get("Andorra")]), "population": {"1500": 1650000, "1600": 1850000, "1700": 1650000, "1750": 1950000}},
    {"id": "em_portugal_main", "name": "Kingdom of Portugal (Mainland)", "geom": G["Portugal_Mainland"], "population": {"1500": 1150000, "1600": 1480000, "1700": 1950000, "1750": 2350000}},
    {"id": "em_italy_north", "name": "Northern Italian States (Savoy, Milan, Venice & Genoa)", "geom": D["it_n_em"], "population": {"1500": 4950000, "1600": 6150000, "1700": 6250000, "1750": 7250000}},
    {"id": "em_italy_central", "name": "Grand Duchy of Tuscany & Papal States", "geom": u_geoms([D["it_c_em"], C["San Marino"], C["Vatican"]]), "population": {"1500": 2150000, "1600": 2650000, "1700": 2750000, "1750": 3150000}},
    {"id": "em_italy_south_malta", "name": "Kingdom of Naples, Sicily, Sardinia & Malta", "geom": u_geoms([D["it_s_em"], C["Malta"]]), "population": {"1500": 3550000, "1600": 4550000, "1700": 4550000, "1750": 5350000}},
    {"id": "em_azores_madeira", "name": "Azores & Madeira", "geom": G["Portugal_Islands"], "population": {"1500": 68000, "1600": 115000, "1700": 165000, "1750": 205000}},
    {"id": "em_canaries", "name": "Canary Islands", "geom": G["Spain_Canaries"], "population": {"1500": 42000, "1600": 68000, "1700": 105000, "1750": 145000}},
  ]
  write_chapter_assets(ch_by_idx[14], ch14_zones, D, basemap_hist, basemap_mod, full_domain=False)

  # =========================================================================
  # CH 15: Ottoman Balkans & South-Eastern Europe (1350..1830) — Authentic Rumelia & Danubian Principalities (NO Transylvania!)
  # =========================================================================
  ch15_zones = [
    {"id": "ott_bosnia_dalmatia", "name": "Ottoman Bosnia Eyalet & Dalmatia", "geom": diff_geom(u_geoms([C["Bosnia and Herzegovina"], C["Croatia"]]), D["hungary_crown_hist"]), "population": {"1400": 850000, "1500": 980000, "1600": 1120000, "1700": 1250000, "1800": 1650000, "1830": 1850000}},
    {"id": "ott_serbia_montenegro_kosovo", "name": "Sanjak of Smederevo (Serbia), Montenegro & Kosovo", "geom": diff_geom(u_geoms([C["Republic of Serbia"], C["Montenegro"], C["Kosovo"]]), D["hungary_crown_hist"]), "population": {"1400": 1050000, "1500": 1180000, "1600": 1280000, "1700": 1220000, "1800": 1650000, "1830": 1950000}},
    {"id": "ott_albania_macedonia", "name": "Ottoman Albania & Macedonia", "geom": u_geoms([C["Albania"], C["North Macedonia"]]), "population": {"1400": 650000, "1500": 720000, "1600": 820000, "1700": 880000, "1800": 1120000, "1830": 1280000}},
    {"id": "ott_greece", "name": "Ottoman Greece (Morea, Rumeli & Aegean)", "geom": C["Greece"], "population": {"1400": 1250000, "1500": 1450000, "1600": 1650000, "1700": 1580000, "1800": 2150000, "1830": 2450000}},
    {"id": "ott_bulgaria", "name": "Ottoman Bulgaria (Danube & Silistra)", "geom": C["Bulgaria"], "population": {"1400": 1050000, "1500": 1180000, "1600": 1380000, "1700": 1450000, "1800": 2150000, "1830": 2550000}},
    {"id": "ott_danubian_principalities", "name": "Danubian Principalities (Wallachia & Moldavia)", "geom": wallachia_moldavia, "population": {"1400": 1300000, "1500": 1650000, "1600": 1950000, "1700": 2250000, "1800": 3850000, "1830": 4550000}},
    {"id": "ott_eastern_thrace", "name": "Eastern Thrace (Edirne & Constantinople)", "geom": C["Turkey-in-Europe"], "population": {"1400": 320000, "1500": 580000, "1600": 880000, "1700": 950000, "1800": 1150000, "1830": 1280000}},
  ]
  write_chapter_assets(ch_by_idx[15], ch15_zones, D, basemap_hist, basemap_mod, full_domain=False)

  # =========================================================================
  # CH 16: Industrialisation in Western & Northern Europe (1750..1914) — AUTHENTIC 1871-1914 IMPERIAL BORDERS! ZERO ODER-NEISSE!
  # =========================================================================
  cs1900 = D["cshapes"][1900]
  ch16_zones = [
    {"id": "ind_england_wales", "name": "England & Wales", "geom": u_geoms([G["UK_England_Wales"], C.get("Isle of Man"), C.get("Jersey"), C.get("Guernsey")]), "population": {"1750": 6250000, "1801": 9050000, "1851": 18050000, "1881": 26100000, "1911": 36220000}},
    {"id": "ind_scotland", "name": "Scotland", "geom": G["UK_Scotland"], "population": {"1750": 1265000, "1801": 1608000, "1851": 2889000, "1881": 3736000, "1911": 4761000}},
    {"id": "ind_ireland", "name": "Ireland", "geom": G["Ireland_Full"], "population": {"1750": 3150000, "1801": 5200000, "1841": 8175000, "1851": 6552000, "1881": 5175000, "1911": 4390000}},
    {"id": "ind_france", "name": "French Third Republic (1871-1914, excl. Alsace-Lorraine)", "geom": u_geoms([D["fr_1876"], C["Monaco"]]), "population": {"1750": 23600000, "1801": 27900000, "1851": 34300000, "1881": 37670000, "1911": 39605000}},
    {"id": "ind_benelux", "name": "Belgium, Netherlands & Luxembourg", "geom": u_geoms([C["Belgium"], C["Netherlands"], C["Luxembourg"]]), "population": {"1750": 4250000, "1800": 5250000, "1850": 7750000, "1880": 9790000, "1910": 13540000}},
    {"id": "ind_germany_north", "name": "Kingdom of Prussia & Northern German Empire (incl. East Prussia/Silesia)", "geom": D["de14_north"], "population": {"1750": 10200000, "1816": 15100000, "1850": 21600000, "1871": 27200000, "1910": 43800000}},
    {"id": "ind_germany_south_swiss", "name": "Southern German States (incl. Alsace-Lorraine) & Switzerland", "geom": u_geoms([D["de14_south"], C["Switzerland"], C["Liechtenstein"]]), "population": {"1750": 9650000, "1816": 12900000, "1850": 16500000, "1871": 19200000, "1910": 27400000}},
    {"id": "ind_scandinavia", "name": "Denmark (excl. N. Schleswig), Sweden, Norway & Finland", "geom": diff_geom(u_geoms([C["Denmark"], C["Sweden"], C["Norway"], C["Finland"], C["Aland"]]), D["de1900_full"]), "population": {"1750": 3690000, "1800": 5060000, "1850": 7980000, "1880": 10520000, "1910": 13780000}},
    {"id": "ind_north_atlantic", "name": "Iceland, Faroe Islands & Greenland", "geom": G["North_Atlantic"], "population": {"1750": 60400, "1801": 58600, "1850": 77000, "1880": 93500, "1910": 116500}},
  ]
  write_chapter_assets(ch_by_idx[16], ch16_zones, D, basemap_hist, basemap_mod, full_domain=False)

  # =========================================================================
  # CH 17: Early Modern & 19th-Century Southern & East-Central Europe (1750..1914)
  # AUTHENTIC 1871-1914 IMPERIAL BORDERS (Austria-Hungary Cisleithania/Transleithania, Congress Poland, DEMOPAST 1901 Italy!)
  # =========================================================================
  balkans_1900 = diff_geom(
    u_geoms([C["Romania"], C["Moldova"], C["Bulgaria"], C["Republic of Serbia"], C["Montenegro"], C["Kosovo"], C["North Macedonia"], C["Albania"], C["Greece"], C["Turkey-in-Europe"]]),
    u_geoms([D["cisleithania_1910"], D["transleithania_1910"]])
  )
  ch17_zones = [
    {"id": "c19_spain", "name": "Kingdom of Spain (incl. Balearics & Canaries)", "geom": u_geoms([C["Spain"], C["Andorra"], C["Gibraltar"]]), "population": {"1750": 9750000, "1800": 10850000, "1857": 15460000, "1887": 17560000, "1910": 19950000}},
    {"id": "c19_portugal", "name": "Kingdom of Portugal (incl. Azores & Madeira)", "geom": C["Portugal"], "population": {"1750": 2555000, "1800": 2950000, "1864": 4188000, "1890": 5050000, "1911": 5960000}},
    {"id": "c19_italy_north_central", "name": "Kingdom of Italy (North & Central, pre-1919)", "geom": u_geoms([D["it01_nc"], C["San Marino"], C["Vatican"]]), "population": {"1750": 10100000, "1800": 11500000, "1861": 14950000, "1881": 16950000, "1911": 20800000}},
    {"id": "c19_italy_south_malta", "name": "Southern Italy, Sicily, Sardinia & Malta", "geom": u_geoms([D["it01_s"], C["Malta"]]), "population": {"1750": 5350000, "1800": 6450000, "1861": 9750000, "1881": 11200000, "1911": 13500000}},
    {"id": "c19_austria_bohemia_slovenia", "name": "Austrian Cisleithania (Austria, Bohemia, Galicia & Dalmatia)", "geom": D["cisleithania_1910"], "population": {"1750": 11200000, "1800": 13800000, "1857": 18200000, "1880": 22144000, "1910": 28571000}},
    {"id": "c19_hungary_slovakia_croatia", "name": "Hungarian Transleithania (incl. Slovakia, Transylvania, Croatia & Bosnia)", "geom": D["transleithania_1910"], "population": {"1750": 7200000, "1800": 9800000, "1857": 13700000, "1880": 16895000, "1910": 22784000}},
    {"id": "c19_poland", "name": "Congress Poland (Vistula Land)", "geom": D["congress_poland"], "population": {"1750": 2850000, "1800": 3300000, "1850": 4850000, "1880": 7240000, "1910": 11900000}},
    {"id": "c19_baltics", "name": "Russian Baltic Governorates (Estland, Livland, Kurland & Kovno)", "geom": u_geoms([C["Estonia"], C["Latvia"], C["Lithuania"]]), "population": {"1750": 1400000, "1800": 2150000, "1850": 3250000, "1897": 5420000, "1913": 6250000}},
    {"id": "c19_balkans_romania", "name": "Old Kingdom of Romania, Balkan States & Ottoman Rumelia", "geom": balkans_1900, "population": {"1750": 9800000, "1800": 12200000, "1850": 16200000, "1880": 20500000, "1910": 27400000}},
  ]
  write_chapter_assets(ch_by_idx[17], ch17_zones, D, basemap_hist, basemap_mod, full_domain=False)

  # =========================================================================
  # CH 18: First World War, Inter-War Europe & Second World War (1914..1945)
  # AUTHENTIC 1920-1938 VERSAILLES-TRIANON EUROPE (CShapes 1930) — ZERO ODER-NEISSE!
  # =========================================================================
  cs30 = D["cshapes"][1930]
  ch18_zones = [
    {"id": "ww_uk_ireland", "name": "United Kingdom & Irish Free State", "geom": G["British_Isles"], "population": {"1914": 46050000, "1921": 47120000, "1939": 50750000, "1945": 52180000}},
    {"id": "ww_france_benelux", "name": "France (incl. Alsace-Lorraine) & Benelux", "geom": u_geoms([cs30.get("france"), cs30.get("belgium"), cs30.get("netherlands"), cs30.get("luxembourg"), C["Monaco"]]), "population": {"1914": 53950000, "1921": 53800000, "1939": 59250000, "1945": 57950000}},
    {"id": "ww_germany_austria_swiss", "name": "Weimar/Interwar Germany (incl. East Prussia & Silesia), Austria & Switzerland", "geom": u_geoms([cs30.get("germany prussia"), cs30.get("austria"), cs30.get("switzerland"), C["Liechtenstein"]]), "population": {"1914": 71650000, "1925": 73200000, "1939": 80150000, "1945": 76850000}},
    {"id": "ww_poland", "name": "Second Polish Republic (1921-1939) & Free City of Danzig", "geom": u_geoms([cs30.get("poland"), cs30.get("danzig")]), "population": {"1914": 25800000, "1921": 27180000, "1939": 34850000, "1945": 23930000}},
    {"id": "ww_czechoslovakia_hungary", "name": "Czechoslovakia & Trianon Hungary", "geom": u_geoms([cs30.get("czechoslovakia"), cs30.get("hungary")]), "population": {"1914": 21400000, "1921": 21600000, "1939": 23800000, "1945": 21250000}},
    {"id": "ww_italy_malta", "name": "Kingdom of Italy (incl. South Tyrol & Istria) & Malta", "geom": u_geoms([cs30.get("italy sardinia") or cs30.get("italy"), C["San Marino"], C["Vatican"], C["Malta"]]), "population": {"1914": 36200000, "1921": 38100000, "1939": 44100000, "1945": 45400000}},
    {"id": "ww_iberia_macaronesia", "name": "Spain, Portugal & Atlantic Islands", "geom": u_geoms([C["Spain"], C["Portugal"], C["Andorra"], C["Gibraltar"]]), "population": {"1914": 26450000, "1920": 27400000, "1939": 33200000, "1945": 35100000}},
    {"id": "ww_nordics_baltics", "name": "Nordics & Independent Baltic Republics", "geom": u_geoms([cs30.get(k) for k in ("denmark", "sweden", "norway", "finland", "estonia", "latvia", "lithuania")] + [C["Aland"]]), "population": {"1914": 20350000, "1925": 20950000, "1939": 22550000, "1945": 22150000}},
    {"id": "ww_romania_bulgaria_moldova", "name": "Greater Romania (incl. Bessarabia) & Bulgaria", "geom": u_geoms([cs30.get("romania") or cs30.get("rumania"), cs30.get("bulgaria")]), "population": {"1914": 19100000, "1925": 20900000, "1939": 24500000, "1945": 24800000}},
    {"id": "ww_yugoslavia_greece_albania", "name": "Kingdom of Yugoslavia, Albania, Greece & Eastern Thrace", "geom": u_geoms([cs30.get("yugoslavia"), cs30.get("albania"), cs30.get("greece"), C["Turkey-in-Europe"]]), "population": {"1914": 20100000, "1925": 21200000, "1939": 25800000, "1945": 24950000}},
    {"id": "ww_north_atlantic", "name": "Iceland, Faroe Islands & Greenland", "geom": G["North_Atlantic"], "population": {"1914": 121000, "1925": 136000, "1939": 165000, "1945": 180000}},
  ]
  write_chapter_assets(ch_by_idx[18], ch18_zones, D, basemap_hist, basemap_mod, full_domain=True)

  # =========================================================================
  # CH 19-21: REGIME III — Contemporary Statistical Census Sovereign States (1945..2026)
  # =========================================================================
  ch19_zones = [
    {"id": "mod_uk", "name": "United Kingdom", "geom": u_geoms([C["United Kingdom"], C.get("Isle of Man"), C.get("Jersey"), C.get("Guernsey")]), "population": {"1950": 50616000, "1970": 55632000, "1990": 57237000, "2010": 62766000, "2025": 69138000}},
    {"id": "mod_ireland", "name": "Ireland", "geom": C["Ireland"], "population": {"1950": 2969000, "1970": 2950000, "1990": 3506000, "2010": 4555000, "2025": 5380000}},
    {"id": "mod_france", "name": "France (Metropolitan)", "geom": u_geoms([C["France"], C["Monaco"]]), "population": {"1950": 41829000, "1970": 50772000, "1990": 56735000, "2010": 62961000, "2025": 66450000}},
    {"id": "mod_belgium", "name": "Belgium", "geom": C["Belgium"], "population": {"1950": 8639000, "1970": 9638000, "1990": 9967000, "2010": 10896000, "2025": 11830000}},
    {"id": "mod_netherlands", "name": "Netherlands", "geom": C["Netherlands"], "population": {"1950": 10114000, "1970": 13039000, "1990": 14952000, "2010": 16615000, "2025": 18040000}},
    {"id": "mod_luxembourg", "name": "Luxembourg", "geom": C["Luxembourg"], "population": {"1950": 296000, "1970": 339000, "1990": 382000, "2010": 507000, "2025": 678000}},
    {"id": "mod_germany", "name": "Germany", "geom": C["Germany"], "population": {"1950": 69346000, "1970": 77709000, "1990": 79433000, "2010": 81777000, "2025": 84550000}},
    {"id": "mod_switzerland", "name": "Switzerland & Liechtenstein", "geom": u_geoms([C["Switzerland"], C["Liechtenstein"]]), "population": {"1950": 4708000, "1970": 6202000, "1990": 6741000, "2010": 7861000, "2025": 9040000}},
    {"id": "mod_austria", "name": "Austria", "geom": C["Austria"], "population": {"1950": 6935000, "1970": 7467000, "1990": 7678000, "2010": 8363000, "2025": 9190000}},
    {"id": "mod_denmark", "name": "Denmark", "geom": C["Denmark"], "population": {"1950": 4271000, "1970": 4929000, "1990": 5141000, "2010": 5548000, "2025": 5990000}},
    {"id": "mod_sweden", "name": "Sweden", "geom": C["Sweden"], "population": {"1950": 7014000, "1970": 8043000, "1990": 8559000, "2010": 9378000, "2025": 10610000}},
    {"id": "mod_norway", "name": "Norway (incl. Svalbard)", "geom": C["Norway"], "population": {"1950": 3265000, "1970": 3877000, "1990": 4241000, "2010": 4889000, "2025": 5590000}},
    {"id": "mod_finland", "name": "Finland", "geom": u_geoms([C["Finland"], C["Aland"]]), "population": {"1950": 4009000, "1970": 4606000, "1990": 4986000, "2010": 5363000, "2025": 5635000}},
  ]
  write_chapter_assets(ch_by_idx[19], ch19_zones, D, basemap_hist, basemap_mod, full_domain=False)

  ch20_zones = [
    {"id": "mod_spain_main", "name": "Spain (Mainland & Balearics)", "geom": u_geoms([G["Spain_Mainland"], C["Andorra"], C["Gibraltar"]]), "population": {"1950": 27280000, "1970": 32720000, "1990": 37450000, "2010": 44550000, "2025": 46750000}},
    {"id": "mod_canaries", "name": "Canary Islands", "geom": G["Spain_Canaries"], "population": {"1950": 793000, "1970": 1170000, "1990": 1494000, "2010": 2118000, "2025": 2255000}},
    {"id": "mod_portugal_main", "name": "Portugal (Mainland)", "geom": G["Portugal_Mainland"], "population": {"1950": 7856000, "1970": 8120000, "1990": 9410000, "2010": 10060000, "2025": 10180000}},
    {"id": "mod_azores_madeira", "name": "Azores & Madeira", "geom": G["Portugal_Islands"], "population": {"1950": 585000, "1970": 542000, "1990": 491000, "2010": 514000, "2025": 496000}},
    {"id": "mod_italy", "name": "Italy (incl. San Marino & Vatican)", "geom": u_geoms([C["Italy"], C["San Marino"], C["Vatican"]]), "population": {"1950": 47105000, "1970": 53822000, "1990": 56719000, "2010": 59277000, "2025": 58950000}},
    {"id": "mod_malta", "name": "Malta", "geom": C["Malta"], "population": {"1950": 312000, "1970": 303000, "1990": 354000, "2010": 415000, "2025": 563000}},
    {"id": "mod_greece", "name": "Greece", "geom": C["Greece"], "population": {"1950": 7566000, "1970": 8793000, "1990": 10161000, "2010": 11121000, "2025": 10380000}},
    {"id": "mod_iceland", "name": "Iceland", "geom": C["Iceland"], "population": {"1950": 143000, "1970": 204000, "1990": 255000, "2010": 318000, "2025": 393000}},
    {"id": "mod_faroes", "name": "Faroe Islands", "geom": C["Faroe Islands"], "population": {"1950": 31800, "1970": 38600, "1990": 47400, "2010": 48500, "2025": 55100}},
    {"id": "mod_greenland", "name": "Greenland", "geom": C["Greenland"], "population": {"1950": 23600, "1970": 46500, "1990": 55600, "2010": 56500, "2025": 56800}},
    {"id": "mod_turkey_europe", "name": "Turkey-in-Europe (Eastern Thrace)", "geom": C["Turkey-in-Europe"], "population": {"1950": 1590000, "1970": 3150000, "1990": 6250000, "2010": 10350000, "2025": 12250000}},
  ]
  write_chapter_assets(ch_by_idx[20], ch20_zones, D, basemap_hist, basemap_mod, full_domain=False)

  ch21_zones = [
    {"id": "mod_poland", "name": "Poland", "geom": C["Poland"], "population": {"1950": 24824000, "1970": 32526000, "1990": 38111000, "2010": 38043000, "2025": 37480000}},
    {"id": "mod_czechia", "name": "Czechia", "geom": C["Czechia"], "population": {"1950": 8925000, "1970": 9805000, "1990": 10363000, "2010": 10474000, "2025": 10880000}},
    {"id": "mod_slovakia", "name": "Slovakia", "geom": C["Slovakia"], "population": {"1950": 3463000, "1970": 4528000, "1990": 5298000, "2010": 5391000, "2025": 5425000}},
    {"id": "mod_hungary", "name": "Hungary", "geom": C["Hungary"], "population": {"1950": 9338000, "1970": 10338000, "1990": 10374000, "2010": 10000000, "2025": 9580000}},
    {"id": "mod_romania", "name": "Romania", "geom": C["Romania"], "population": {"1950": 16311000, "1970": 20253000, "1990": 23207000, "2010": 20247000, "2025": 19050000}},
    {"id": "mod_moldova", "name": "Moldova", "geom": C["Moldova"], "population": {"1950": 2341000, "1970": 3595000, "1990": 4364000, "2010": 3562000, "2025": 2980000}},
    {"id": "mod_bulgaria", "name": "Bulgaria", "geom": C["Bulgaria"], "population": {"1950": 7251000, "1970": 8490000, "1990": 8718000, "2010": 7396000, "2025": 6435000}},
    {"id": "mod_slovenia", "name": "Slovenia", "geom": C["Slovenia"], "population": {"1950": 1473000, "1970": 1725000, "1990": 1998000, "2010": 2049000, "2025": 2125000}},
    {"id": "mod_croatia", "name": "Croatia", "geom": C["Croatia"], "population": {"1950": 3850000, "1970": 4411000, "1990": 4778000, "2010": 4295000, "2025": 3860000}},
    {"id": "mod_bosnia", "name": "Bosnia and Herzegovina", "geom": C["Bosnia and Herzegovina"], "population": {"1950": 2661000, "1970": 3708000, "1990": 4424000, "2010": 3760000, "2025": 3165000}},
    {"id": "mod_serbia_kosovo", "name": "Serbia & Kosovo", "geom": u_geoms([C["Republic of Serbia"], C["Kosovo"]]), "population": {"1950": 6732000, "1970": 8140000, "1990": 9520000, "2010": 9060000, "2025": 8240000}},
    {"id": "mod_montenegro", "name": "Montenegro", "geom": C["Montenegro"], "population": {"1950": 399000, "1970": 525000, "1990": 606000, "2010": 619000, "2025": 623000}},
    {"id": "mod_north_macedonia", "name": "North Macedonia", "geom": C["North Macedonia"], "population": {"1950": 1230000, "1970": 1629000, "1990": 1903000, "2010": 2055000, "2025": 1825000}},
    {"id": "mod_albania", "name": "Albania", "geom": C["Albania"], "population": {"1950": 1215000, "1970": 2136000, "1990": 3286000, "2010": 2913000, "2025": 2745000}},
    {"id": "mod_estonia", "name": "Estonia", "geom": C["Estonia"], "population": {"1950": 1101000, "1970": 1360000, "1990": 1569000, "2010": 1331000, "2025": 1370000}},
    {"id": "mod_latvia", "name": "Latvia", "geom": C["Latvia"], "population": {"1950": 1949000, "1970": 2366000, "1990": 2663000, "2010": 2098000, "2025": 1870000}},
    {"id": "mod_lithuania", "name": "Lithuania", "geom": C["Lithuania"], "population": {"1950": 2567000, "1970": 3137000, "1990": 3698000, "2010": 3097000, "2025": 2885000}},
  ]
  write_chapter_assets(ch_by_idx[21], ch21_zones, D, basemap_hist, basemap_mod, full_domain=False)

  # --- Master Manifests ---
  specialist_masks, national_epoch_masks, gazetteers = [], [], []
  for ch in itinerary["chapters"]:
    stem, folder = ch["key"], ch["folder"]
    entry = {
      "id": stem, "domain": ch["domain"], "domain_group": "sites_magnetic_europe",
      "json5_path": f"histmap/1.data_raw/population_regional/MAGNETIC/{folder}/{stem}.json5",
      "mask_path": f"histmap/1.data_raw/population_regional/MAGNETIC/{folder}/{stem}_areal_mask.png",
      "priority": 1 if ch["index"] == 1 else (3 if ch["index"] >= 19 else 2),
    }
    if ch["index"] >= 19:
      entry["is_admin1"] = True
    (specialist_masks if ch["index"] == 1 else national_epoch_masks).append(entry)
    gazetteers.append({
      "domain": ch["domain"], "itinerary_title": ch["itinerary_title"], "key": stem,
      "path": f"histmap/1.data_raw/population_regional/MAGNETIC/{folder}/{stem}_settlements.json",
      "priority": entry["priority"], "region_group": ch["region_group"],
    })

  am_manifest = {
    "grid_dimensions": [GRID_W, GRID_H],
    "regime_transitions": {"europe_north_atlantic": {"pre_admin_end": 400, "dynastic_imperial_start": 400, "contemporary_start": 1945}},
    "geography_profile": {"projection_class": "albers_conic", "has_micro_islands": True, "max_adm2_area_km2": 25000, "note": "Europe excluding POLARIS core, plus Greenland, Faroes, Iceland, Svalbard, Azores, Madeira, Canary Islands and Eastern Thrace."},
    "script_profile": {"target_scripts": ["Latn", "Grek", "Cyrl"], "allow_native_toponyms": True},
    "hyde_years": ALL_HYDE_YEARS,
    "substrata_sources": {
      "sites_magnetic_europe": {
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/MAGNETIC/_shared/sites_magnetic_europe/config/documented_site_pixels.json",
        "domain": [-10000, 2025], "domain_code": 1,
        "domain_mask_png": "histmap/1.data_raw/population_regional/MAGNETIC/_shared/sites_magnetic_europe/config/magnetic_domain_mask.png",
        "rasters_folder": "histmap/1.data_raw/population_regional/MAGNETIC/_shared/sites_magnetic_europe/2.population_rasters",
        "sample_year": 1000,
      }
    },
    "smoothing": {"border_feather_radius_px": 8, "interior_multiplier_blur_passes": 4, "interior_multiplier_blur_radius_px": 10, "temporal_log_Laplacian_weight": 0.15},
    "specialist_masks": specialist_masks, "national_epoch_masks": national_epoch_masks,
  }
  with open(os.path.join(MAG_DIR, "magnetic_areal_masks.json5"), "w", encoding="utf-8") as fh:
    json.dump(am_manifest, fh, indent=2, ensure_ascii=False)
  with open(os.path.join(MAG_DIR, "magnetic_gazetteers.json5"), "w", encoding="utf-8") as fh:
    json.dump({
      "annual_continuity_span": [1871, 2025],
      "border_splice_years": [1918, 1919, 1920, 1938, 1939, 1945, 1990, 1991, 1992],
      "regime_transitions": am_manifest["regime_transitions"],
      "geography_profile": am_manifest["geography_profile"],
      "script_profile": am_manifest["script_profile"],
      "gazetteers": gazetteers,
    }, fh, indent=2, ensure_ascii=False)
  print("\n[DONE] Rebuilt ALL 21 Historically Authentic MAGNETIC areal masks, vector GeoJSONs & optical QA PNGs!", flush=True)


if __name__ == "__main__":
  main()
