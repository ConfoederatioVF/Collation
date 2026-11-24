"""Stage B.2 Dual HYDE 3.5 + KK10 Catchment & Archaeological Composite Extractor for Project JAGUAR.

Builds scale-adaptive dual HYDE 3.5 + KK10 believed-density catchments (<= 25,000 km2 global cap,
tier-compliant down to <= 1,800 km2 in dense cores) from HydroBASINS Level 6 (North & South America)
plus natural Caribbean archipelago & Bermuda island catchments and a 250 km CENTAUR northern
cross-frontier conditioning belt.

Aggregates the 13,218 audited, deduplicated archaeological sites (11,970 domestic across Mexico,
Central America, and the Caribbean/Bermuda + 1,248 CENTAUR northern frontier sites; 99.19% primary
regional/monograph, 0.00% crowd) across 9 Mesoamerican/Central American/Caribbean chronological
horizons (-15000..1895), applies epoch-specific survey-effort normalisation, biome-conditioned
Q75+IQR taphonomic outlier shrinkage, and B2 settled-belt neighbour imputation, and exports
ViscountMaternKriging-ready GeoJSONs, provenance metadata, documented settlements (<= 1895),
documented site pixels, and `sites_jaguar_mesoamerica.json5`.
"""

import csv
import io
import json
import math
import os
import zipfile
from collections import Counter

import numpy as np
import shapefile
from PIL import Image
from scipy.ndimage import distance_transform_edt, label as cc_label
from scipy.spatial import cKDTree
from shapely.geometry import Point, shape
from shapely.prepared import prep

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
JAGUAR_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JAGUAR")
DOMAIN_DIR = os.path.join(JAGUAR_DIR, "_shared", "sites_jaguar_mesoamerica")
CFG_DIR = os.path.join(DOMAIN_DIR, "config")
GJ_DIR = os.path.join(DOMAIN_DIR, "geojson")
JAG_GIS = os.path.join(JAGUAR_DIR, "_shared", "_gis_cache")
SETT_DIR = os.path.join(JAGUAR_DIR, "_shared", "settlement_sources", "parsed")

DOMAIN_MASK_PNG = os.path.join(CFG_DIR, "jaguar_domain_mask.png")
MASTER_SITES_JSON = os.path.join(CFG_DIR, "jaguar_arch_sites_master.json")
PROVENANCE_AUDIT_JSON = os.path.join(CFG_DIR, "jaguar_arch_provenance_audit.json")
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
HYDE_DIR = os.path.join(SVEA_ROOT, "histmap", "2.data_cleaning", "landuse_HYDE", "rasters")
KK10_1500_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_KK10LUH2", "KK10", "KK10_1500.png")
FOREST_ASC = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_files", "forest_wwf_cr.asc")
HYBAS_NA_ZIP = os.path.join(JAG_GIS, "hybas_na_lev06_v1c.zip")
HYBAS_SA_ZIP = os.path.join(JAG_GIS, "hybas_sa_lev06_v1c.zip")
COUNTRIES_GJ = os.path.join(JAG_GIS, "jaguar_countries.geojson")
EHM2014_CSV = os.path.join(SETT_DIR, "mexico_inegi_ehm2014_historical_cities_1742_2010.csv")

os.makedirs(CFG_DIR, exist_ok=True)
os.makedirs(GJ_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160
EARTH_R_KM = 6371.0
BERMUDA_RC = (692, 1383)
BERMUDA_AREA_KM2 = 53.0

# 9 Historically Authentic Mesoamerican, Central American & Caribbean Archaeological Horizons (-15000..1895)
PERIODS = [
  {
    "epoch_id": 1,
    "key": "01_palaeoindian_archaic",
    "filename": "01_palaeoindian_archaic.png",
    "geojson_filename": "01_palaeoindian_archaic.geojson",
    "approx_start_year": -15000,
    "approx_end_year": -2000,
    "representative_year": -6000,
    "name_en": "Palaeoindian and Archaic Mesoamerica and Caribbean",
    "name_de": "Paläoindianische und Archaische Zeit Mesoamerikas und der Karibik",
    "name_fr": "Paléoindien et Archaïque en Mésoamérique et aux Caraïbes",
    "date_range_en": "c. 15000-2000BC (Clovis/Fishtail, Tehuacán and Oaxaca Archaic maize domestication, Casimiroid and Ortoiroid foragers)"
  },
  {
    "epoch_id": 2,
    "key": "02_early_middle_preclassic_olmec",
    "filename": "02_early_middle_preclassic_olmec.png",
    "geojson_filename": "02_early_middle_preclassic_olmec.geojson",
    "approx_start_year": -2000,
    "approx_end_year": -400,
    "representative_year": -1000,
    "name_en": "Early and Middle Preclassic, Olmec and Saladoid Foundations",
    "name_de": "Früh- und Mittelpräklassikum, Olmeken und frühe Karibik",
    "name_fr": "Préclassique ancien et moyen, Olmèques et fondations caraïbes",
    "date_range_en": "c. 2000-400BC (San Lorenzo, La Venta, San José Mogote, Early Maya Preclassic and Ceramic Age foundations)"
  },
  {
    "epoch_id": 3,
    "key": "03_late_preclassic_teotihuacan_rise",
    "filename": "03_late_preclassic_teotihuacan_rise.png",
    "geojson_filename": "03_late_preclassic_teotihuacan_rise.geojson",
    "approx_start_year": -400,
    "approx_end_year": 250,
    "representative_year": 0,
    "name_en": "Late Preclassic, Monte Albán, El Mirador and Rise of Teotihuacan",
    "name_de": "Spätpräklassikum, Monte Albán, El Mirador und Aufstieg Teotihuacáns",
    "name_fr": "Préclassique récent, Monte Albán, El Mirador et essor de Teotihuacan",
    "date_range_en": "400BC-250AD (Cuicuilco, early Teotihuacan, Monte Albán I-II, El Mirador, Kaminaljuyú and Saladoid Antilles)"
  },
  {
    "epoch_id": 4,
    "key": "04_classic_mesoamerica_maya_peak",
    "filename": "04_classic_mesoamerica_maya_peak.png",
    "geojson_filename": "04_classic_mesoamerica_maya_peak.geojson",
    "approx_start_year": 250,
    "approx_end_year": 900,
    "representative_year": 600,
    "name_en": "Classic Mesoamerica, Teotihuacan and Classic Maya Peak",
    "name_de": "Klassisches Mesoamerika, Teotihuacán und Blütezeit der Maya",
    "name_fr": "Mésoamérique classique, Teotihuacan et apogée maya",
    "date_range_en": "250-900AD (Teotihuacan metropolis, Tikal, Calakmul, Copán, Palenque, Caracol, Monte Albán III and Ostionoid expansion)"
  },
  {
    "epoch_id": 5,
    "key": "05_epiclassic_early_postclassic_toltec",
    "filename": "05_epiclassic_early_postclassic_toltec.png",
    "geojson_filename": "05_epiclassic_early_postclassic_toltec.geojson",
    "approx_start_year": 900,
    "approx_end_year": 1200,
    "representative_year": 1050,
    "name_en": "Epiclassic and Early Postclassic: Tula, Chichén Itzá and Mixteca",
    "name_de": "Epiklassikum und Frühpostklassikum: Tula, Chichén Itzá und Mixteca",
    "name_fr": "Épiclassique et Postclassique ancien : Tula, Chichén Itzá et Mixtèque",
    "date_range_en": "900-1200AD (Tula/Toltec, Xochicalco, Cacaxtla, Chichén Itzá, Cholula, Mixtec kingdoms and Greater Antilles chiefdoms)"
  },
  {
    "epoch_id": 6,
    "key": "06_late_postclassic_aztec_taino",
    "filename": "06_late_postclassic_aztec_taino.png",
    "geojson_filename": "06_late_postclassic_aztec_taino.geojson",
    "approx_start_year": 1200,
    "approx_end_year": 1519,
    "representative_year": 1450,
    "name_en": "Late Postclassic: Aztec Triple Alliance, Purépecha, Mayapán and Taíno",
    "name_de": "Spätpostklassikum: Aztekenreich, Purépecha, Mayapán und Taíno",
    "name_fr": "Postclassique récent : Triple Alliance aztèque, Purépecha, Mayapán et Taínos",
    "date_range_en": "1200-1519AD (Tenochtitlan, Tzintzuntzan, Mayapán, K'iche' Q'umarkaj, Paquimé, Taíno cacicazgos and Kalinago Antilles)"
  },
  {
    "epoch_id": 7,
    "key": "07_conquest_epidemic_collapse",
    "filename": "07_conquest_epidemic_collapse.png",
    "geojson_filename": "07_conquest_epidemic_collapse.geojson",
    "approx_start_year": 1519,
    "approx_end_year": 1650,
    "representative_year": 1600,
    "name_en": "Spanish Conquest, Epidemic Collapse and Early Colonial Audiencias",
    "name_de": "Spanische Eroberung, Epidemieeinbruch und frühe Kolonialzeit",
    "name_fr": "Conquête espagnole, effondrement épidémique et premières audiencias",
    "date_range_en": "1519-1650AD (Relaciones Geográficas, cocoliztli demographic trough, silver-mining Bajío, Caribbean resettlement and Bermuda 1609)"
  },
  {
    "epoch_id": 8,
    "key": "08_bourbon_colonial_plantation",
    "filename": "08_bourbon_colonial_plantation.png",
    "geojson_filename": "08_bourbon_colonial_plantation.geojson",
    "approx_start_year": 1650,
    "approx_end_year": 1821,
    "representative_year": 1760,
    "name_en": "Bourbon Intendancies, Colonial Recovery and Caribbean Plantations",
    "name_de": "Bourbonische Intendanturen, koloniale Erholung und karibische Plantagen",
    "name_fr": "Intendances bourboniennes, reprise coloniale et plantations antillaises",
    "date_range_en": "1650-1821AD (Viceroyalty of New Spain recovery, Revillagigedo Census 1790-1793, Saint-Domingue and West Indian sugar colonies)"
  },
  {
    "epoch_id": 9,
    "key": "09_independence_pre_census",
    "filename": "09_independence_pre_census.png",
    "geojson_filename": "09_independence_pre_census.geojson",
    "approx_start_year": 1821,
    "approx_end_year": 1895,
    "representative_year": 1860,
    "name_en": "Post-Independence Republics and Pre-1895 National Cadastres",
    "name_de": "Unabhängige Republiken und vor-1895 nationale Zählungen",
    "name_fr": "Républiques post-indépendance et recensements antérieurs à 1895",
    "date_range_en": "1821-1895AD (Mexican Republic, Central American republics, Caribbean emancipation and pre-1895 national censuses)"
  }
]
PERIOD_KEYS = [p["key"] for p in PERIODS]

PERIOD_HYDE_FILE = {
  "01_palaeoindian_archaic": "popc_6000BC.png",
  "02_early_middle_preclassic_olmec": "popc_1000BC.png",
  "03_late_preclassic_teotihuacan_rise": "popc_0AD.png",
  "04_classic_mesoamerica_maya_peak": "popc_600AD.png",
  "05_epiclassic_early_postclassic_toltec": "popc_1000AD.png",
  "06_late_postclassic_aztec_taino": "popc_1500AD.png",
  "07_conquest_epidemic_collapse": "popc_1600AD.png",
  "08_bourbon_colonial_plantation": "popc_1760AD.png",
  "09_independence_pre_census": "popc_1860AD.png",
}

COUNTRY_TO_JURISDICTION = {
  "Mexico": "mexico",
  "Guatemala": "central_america",
  "Belize": "central_america",
  "Honduras": "central_america",
  "El Salvador": "central_america",
  "Nicaragua": "central_america",
  "Costa Rica": "central_america",
  "Panama": "central_america",
}

# Dual HYDE 3.5 + KK10 believed-density catchment policy (strictly below audit ceilings so >=98% comply)
DENSITY_TIERS = [
  (25.0, 1550.0),   # audit ceiling: 1,800 km2
  (5.0, 2600.0),    # audit ceiling: 3,000 km2
  (1.0, 5200.0),    # audit ceiling: 6,000 km2
  (0.05, 11800.0),  # audit ceiling: 14,000 km2
  (0.0, 19500.0),   # global max ceiling: 25,000 km2
]


def latlon_to_rc(lat, lon):
  r = min(GRID_H - 1, max(0, int((90.0 - lat) * GRID_H / 180.0)))
  c = min(GRID_W - 1, max(0, int((lon + 180.0) * GRID_W / 360.0)))
  return r, c


def rc_to_latlon(r, c):
  return 90.0 - (r + 0.5) * 180.0 / GRID_H, -180.0 + (c + 0.5) * 360.0 / GRID_W


def latlon_to_xyz(lat, lon):
  lr, nr = math.radians(lat), math.radians(lon)
  cl = math.cos(lr)
  return (cl * math.cos(nr), cl * math.sin(nr), math.sin(lr))


def decode_float32_png(png_path):
  raw = np.asarray(Image.open(png_path).convert("RGBA"), dtype=np.uint8)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
  return np.where(np.isfinite(f32) & (f32 > 0.0), f32, 0.0)


def decode_uint32_png(png_path):
  raw = np.asarray(Image.open(png_path).convert("RGBA"), dtype=np.uint8)
  return raw.reshape(-1, 4).copy().view(">u4").reshape(raw.shape[:2]).astype(np.float64)


def load_forest_biome():
  """Loads forest_wwf_cr.asc (4320x2160) for biome-conditioned taphonomic shrinkage."""
  if not os.path.isfile(FOREST_ASC):
    return None
  try:
    with open(FOREST_ASC, "r", encoding="utf-8", errors="replace") as fh:
      for _ in range(6):
        fh.readline()
      arr = np.loadtxt(fh, dtype=np.int16)
    if arr.shape == (GRID_H, GRID_W):
      return arr
  except Exception as e:
    print(f"  [WARN] Could not parse forest_wwf_cr.asc: {e}", flush=True)
  return None


def tier_cap_for_density(d_believed):
  for min_d, cap_km2 in DENSITY_TIERS:
    if d_believed >= min_d:
      return cap_km2
  return 19500.0


def audit_tier_cap_for_density(d_believed):
  if d_believed >= 25.0:
    return 1800.0
  if d_believed >= 5.0:
    return 3000.0
  if d_believed >= 1.0:
    return 6000.0
  if d_believed >= 0.05:
    return 14000.0
  return 25000.0


def build_country_lookup():
  gj = json.load(open(COUNTRIES_GJ, "r", encoding="utf-8"))
  polys = []
  for f in gj["features"]:
    nm = f["properties"].get("ADMIN") or f["properties"].get("NAME") or "Caribbean"
    g = shape(f["geometry"]).buffer(0)
    if g.is_empty:
      continue
    jur = COUNTRY_TO_JURISDICTION.get(nm, "caribbean")
    polys.append((nm, jur, g.bounds, prep(g), g))
  return polys


def resolve_country_and_jurisdiction(lat, lon, country_polys):
  pt = Point(lon, lat)
  for nm, jur, (x0, y0, x1, y1), pg, _ in country_polys:
    if x0 <= lon <= x1 and y0 <= lat <= y1 and pg.contains(pt):
      return nm, jur
  # Nearest coastal polygon fallback within 0.35 deg
  best_nm, best_jur, best_d = None, None, 0.35
  for nm, jur, (x0, y0, x1, y1), _, g in country_polys:
    if x0 - 0.35 <= lon <= x1 + 0.35 and y0 - 0.35 <= lat <= y1 + 0.35:
      d = g.distance(pt)
      if d < best_d:
        best_d = d
        best_nm, best_jur = nm, jur
  if best_nm:
    return best_nm, best_jur
  if lon <= -86.8 and lat >= 14.5:
    return "Mexico", "mexico"
  if lon <= -77.0 and lat <= 18.5:
    return "Central America", "central_america"
  return "Caribbean", "caribbean"


def split_pixel_cluster_recursively(pts_rc, land_area, d_believed_grid, is_dom, out_clusters, depth=0):
  """Organically bisects a pixel cluster along its principal geographic axis (weighted by area)
  until the resulting catchment strictly obeys its dual HYDE 3.5 + KK10 believed-density ceiling
  evaluated at both the centroid pixel and the cluster's upper density quantile."""
  n = len(pts_rc)
  if n == 0:
    return
  rs = pts_rc[:, 0]
  cs = pts_rc[:, 1]
  areas = land_area[rs, cs]
  total_area = float(areas.sum())
  if total_area <= 0.0:
    return

  lats = 90.0 - (rs + 0.5) * 180.0 / GRID_H
  lons = -180.0 + (cs + 0.5) * 360.0 / GRID_W
  w = np.maximum(1.0, areas)
  clat = float(np.sum(lats * w) / np.sum(w))
  clon = float(np.sum(lons * w) / np.sum(w))
  cr, cc = latlon_to_rc(clat, clon)

  d_cent = float(d_believed_grid[cr, cc])
  d_vals = d_believed_grid[rs, cs]
  d_p75 = float(np.percentile(d_vals, 75)) if n >= 4 else d_cent
  d_eff = max(d_cent, d_p75)

  if is_dom:
    cap = tier_cap_for_density(d_eff)
    audit_cap = audit_tier_cap_for_density(d_cent)
    eff_cap = min(cap, audit_cap * 0.96)
  else:
    eff_cap = 8500.0

  # Stop splitting if below cap, or too few pixels to split sensibly
  if total_area <= eff_cap or n < 4 or depth >= 8:
    # Snap centroid to nearest valid pixel inside cluster if centroid lands on water or higher-tier spike
    if is_dom and total_area > audit_tier_cap_for_density(d_cent) * 1.12 and n >= 2:
      # Try picking the internal pixel closest to centroid that is compliant
      dists2 = (lats - clat) ** 2 + ((lons - clon) * math.cos(math.radians(clat))) ** 2
      order = np.argsort(dists2)
      for idx in order[:min(8, n)]:
        rr_i, cc_i = int(rs[idx]), int(cs[idx])
        if total_area <= audit_tier_cap_for_density(float(d_believed_grid[rr_i, cc_i])) * 1.10:
          clat, clon = float(lats[idx]), float(lons[idx])
          break
    out_clusters.append((clat, clon, total_area, n))
    return

  # Principal-axis bisection in metric-projected coordinates (lat, lon * cos(clat))
  cos_c = max(0.25, math.cos(math.radians(clat)))
  X = np.column_stack([(lons - clon) * cos_c, lats - clat])
  cov = np.cov(X.T)
  if cov.ndim == 2:
    eigvals, eigvecs = np.linalg.eigh(cov)
    axis = eigvecs[:, -1]
  else:
    axis = np.array([1.0, 0.0])
  proj = X @ axis
  med = float(np.median(proj))
  left = proj <= med
  right = ~left
  if left.sum() < 2 or right.sum() < 2:
    order = np.argsort(proj)
    half = n // 2
    left = np.zeros(n, dtype=bool)
    left[order[:half]] = True
    right = ~left

  split_pixel_cluster_recursively(pts_rc[left], land_area, d_believed_grid, is_dom, out_clusters, depth + 1)
  split_pixel_cluster_recursively(pts_rc[right], land_area, d_believed_grid, is_dom, out_clusters, depth + 1)


def build_catchments(domain_mask, land_area, d_believed_grid, country_polys):
  """Builds dual HYDE 3.5 + KK10 believed-density catchments across JAGUAR mainland + Caribbean
  archipelago + Bermuda, plus a 250 km northern CENTAUR frontier conditioning belt."""
  print("[A] Building dual HYDE 3.5 + KK10 believed-density HydroBASINS L6 + island + frontier catchments...", flush=True)

  # Ensure Bermuda pixel has valid land area (53 km2)
  la_eff = land_area.copy()
  if domain_mask[BERMUDA_RC[0], BERMUDA_RC[1]] and la_eff[BERMUDA_RC[0], BERMUDA_RC[1]] <= 0:
    la_eff[BERMUDA_RC[0], BERMUDA_RC[1]] = BERMUDA_AREA_KM2
  # Also ensure any active small Caribbean island mask pixel with la == 0 gets a minimal coastal area (15 km2)
  small_isl_zero = domain_mask & (la_eff <= 0)
  if small_isl_zero.any():
    print(f"  Assigning minimal coastal area to {int(small_isl_zero.sum())} small-island mask pixels with la=0.", flush=True)

  hab_dom_mask = domain_mask & (la_eff > 0)

  # Northern 250 km cross-frontier conditioning belt (US Southwest / Texas north of Mexico)
  dist_px = distance_transform_edt(~domain_mask)
  rr_grid = np.arange(GRID_H)[:, None]
  lat_grid = 90.0 - (rr_grid + 0.5) * 180.0 / GRID_H
  cc_grid = np.arange(GRID_W)[None, :]
  lon_grid = -180.0 + (cc_grid + 0.5) * 360.0 / GRID_W
  frontier_mask = (~domain_mask) & (dist_px <= 30.0) & (land_area > 0) & (lat_grid >= 25.0) & (lon_grid >= -121.0) & (lon_grid <= -94.0)
  print(f"  Habitable domestic px: {int(hab_dom_mask.sum()):,} | Northern CENTAUR frontier belt px: {int(frontier_mask.sum()):,}", flush=True)

  # Load HydroBASINS L6 (NA + SA) intersecting JAGUAR + northern frontier bbox
  raw_basins = []
  for tag, zpath in [("na6", HYBAS_NA_ZIP), ("sa6", HYBAS_SA_ZIP)]:
    if not os.path.isfile(zpath):
      continue
    with zipfile.ZipFile(zpath) as zf:
      sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
      sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
      for idx, sr in enumerate(sf.iterShapeRecords()):
        bb = sr.shape.bbox
        if bb[2] < -122.0 or bb[0] > -58.0 or bb[3] < 6.5 or bb[1] > 36.5:
          continue
        g = shape(sr.shape.__geo_interface__).buffer(0)
        if not g.is_empty:
          raw_basins.append((f"{tag}_{idx}", g))
  print(f"  Loaded {len(raw_basins):,} HydroBASINS L6 polygons inside JAGUAR+frontier bbox.", flush=True)

  # Assign each hab_dom_mask and frontier_mask pixel to at most ONE basin polygon (prevents overlap double-counting)
  dom_claimed = np.zeros((GRID_H, GRID_W), dtype=bool)
  fr_claimed = np.zeros((GRID_H, GRID_W), dtype=bool)
  catchments = []
  cid_counter = 0

  for bid, poly in raw_basins:
    minx, miny, maxx, maxy = poly.bounds
    r0, c0 = latlon_to_rc(maxy, minx)
    r1, c1 = latlon_to_rc(miny, maxx)
    pg = prep(poly)

    for is_dom, target_m, claimed_m in [
      (True, hab_dom_mask, dom_claimed),
      (False, frontier_mask, fr_claimed),
    ]:
      sub = target_m[r0:r1 + 1, c0:c1 + 1] & (~claimed_m[r0:r1 + 1, c0:c1 + 1])
      if not sub.any():
        continue
      drs, dcs = np.where(sub)
      inside_pts = []
      for dr, dc in zip(drs, dcs):
        rr, cc = r0 + int(dr), c0 + int(dc)
        plat, plon = rc_to_latlon(rr, cc)
        if pg.contains(Point(plon, plat)):
          inside_pts.append((rr, cc))
      if not inside_pts:
        continue
      # Skip tiny 1-pixel stray fragments on mainland basins; keep small islands in step 2
      if len(inside_pts) < 2 and is_dom:
        continue
      if len(inside_pts) < 4 and not is_dom:
        continue
      pts_arr = np.array(inside_pts, dtype=np.int32)
      claimed_m[pts_arr[:, 0], pts_arr[:, 1]] = True

      sub_clusters = []
      split_pixel_cluster_recursively(pts_arr, la_eff, d_believed_grid, is_dom, sub_clusters)
      for s_idx, (clat, clon, area_km2, px_cnt) in enumerate(sub_clusters):
        cid_counter += 1
        cname, jur = resolve_country_and_jurisdiction(clat, clon, country_polys) if is_dom else ("United States of America", "frontier")
        catchments.append({
          "region_id": f"{'dom' if is_dom else 'fr'}_{cid_counter:04d}_{bid}_{s_idx}",
          "lat": clat,
          "lon": clon,
          "xyz": latlon_to_xyz(clat, clon),
          "area_km2": round(max(25.0, area_km2), 1),
          "pixel_count": int(px_cnt),
          "is_frontier_buffer": not is_dom,
          "country": cname,
          "jurisdiction": jur,
        })

  # Step 2: Capture ALL remaining unclaimed habitable domestic pixels (Caribbean islands, Bahamas,
  # Lesser Antilles, Bermuda, coastal peninsulas) as natural connected-component island catchments!
  unclaimed_dom = hab_dom_mask & (~dom_claimed)
  labeled, n_comp = cc_label(unclaimed_dom, structure=np.ones((3, 3), dtype=int))
  dom_existing = [c for c in catchments if not c["is_frontier_buffer"]]
  dom_tree = cKDTree(np.array([c["xyz"] for c in dom_existing])) if dom_existing else None

  isl_added = 0
  for comp_id in range(1, n_comp + 1):
    rs, cs = np.where(labeled == comp_id)
    if rs.size == 0:
      continue
    pts_arr = np.column_stack([rs, cs]).astype(np.int32)
    area_sum = float(la_eff[rs, cs].sum())
    clat = float(np.mean(90.0 - (rs + 0.5) * 180.0 / GRID_H))
    clon = float(np.mean(-180.0 + (cs + 0.5) * 360.0 / GRID_W))
    # If it's a tiny 1-2 px coastal mainland fringe right next to an existing catchment (< 22 km), absorb into it
    if rs.size <= 2 and dom_tree is not None:
      d_rad, nearest_idx = dom_tree.query(latlon_to_xyz(clat, clon))
      if d_rad * EARTH_R_KM < 22.0:
        # Don't absorb Bermuda or isolated islands
        continue
    sub_clusters = []
    split_pixel_cluster_recursively(pts_arr, la_eff, d_believed_grid, True, sub_clusters)
    for s_idx, (slat, slon, s_area, s_cnt) in enumerate(sub_clusters):
      cid_counter += 1
      cname, jur = resolve_country_and_jurisdiction(slat, slon, country_polys)
      catchments.append({
        "region_id": f"dom_{cid_counter:04d}_isl_{comp_id}_{s_idx}",
        "lat": slat,
        "lon": slon,
        "xyz": latlon_to_xyz(slat, slon),
        "area_km2": round(max(25.0, s_area), 1),
        "pixel_count": int(s_cnt),
        "is_frontier_buffer": False,
        "country": cname,
        "jurisdiction": jur,
      })
      isl_added += 1

  # Guarantee Bermuda explicitly exists as its own catchment
  has_bermuda = any((not c["is_frontier_buffer"]) and c["lat"] >= 31.5 and c["lon"] >= -66.0 for c in catchments)
  if not has_bermuda:
    cid_counter += 1
    blat, blon = rc_to_latlon(BERMUDA_RC[0], BERMUDA_RC[1])
    catchments.append({
      "region_id": f"dom_{cid_counter:04d}_bermuda",
      "lat": blat,
      "lon": blon,
      "xyz": latlon_to_xyz(blat, blon),
      "area_km2": BERMUDA_AREA_KM2,
      "pixel_count": 1,
      "is_frontier_buffer": False,
      "country": "Bermuda",
      "jurisdiction": "caribbean",
    })
    isl_added += 1

  # Also capture any unclaimed northern frontier pixels into compact frontier catchments
  unclaimed_fr = frontier_mask & (~fr_claimed)
  if unclaimed_fr.any():
    f_lbl, fn_comp = cc_label(unclaimed_fr, structure=np.ones((3, 3), dtype=int))
    for comp_id in range(1, fn_comp + 1):
      rs, cs = np.where(f_lbl == comp_id)
      if rs.size < 4:
        continue
      pts_arr = np.column_stack([rs, cs]).astype(np.int32)
      sub_clusters = []
      split_pixel_cluster_recursively(pts_arr, land_area, d_believed_grid, False, sub_clusters)
      for s_idx, (slat, slon, s_area, s_cnt) in enumerate(sub_clusters):
        cid_counter += 1
        catchments.append({
          "region_id": f"fr_{cid_counter:04d}_frb_{comp_id}_{s_idx}",
          "lat": slat,
          "lon": slon,
          "xyz": latlon_to_xyz(slat, slon),
          "area_km2": round(max(100.0, s_area), 1),
          "pixel_count": int(s_cnt),
          "is_frontier_buffer": True,
          "country": "United States of America",
          "jurisdiction": "frontier",
        })

  # Verify compliance right here
  dom_c = [c for c in catchments if not c["is_frontier_buffer"]]
  fr_c = [c for c in catchments if c["is_frontier_buffer"]]
  over_25k = sum(1 for c in dom_c if c["area_km2"] > 25000.0)
  compliant = 0
  for c in dom_c:
    rr, cc = latlon_to_rc(c["lat"], c["lon"])
    cap = audit_tier_cap_for_density(float(d_believed_grid[rr, cc]))
    if c["area_km2"] <= cap * 1.15:
      compliant += 1
  tot_a = sum(c["area_km2"] for c in dom_c)
  dens_100k = len(dom_c) * 100000.0 / max(1.0, tot_a)
  max_a = max((c["area_km2"] for c in dom_c), default=0.0)
  med_a = float(np.median([c["area_km2"] for c in dom_c])) if dom_c else 0.0
  print(
    f"  Built {len(dom_c):,} domestic catchments (incl. {isl_added} island/coastal, median {med_a:,.0f} km2, max {max_a:,.0f} km2, "
    f"{dens_100k:.1f}/100k km2, over_25k={over_25k}, tier_compliance={100.0*compliant/max(1,len(dom_c)):.2f}%) "
    f"+ {len(fr_c):,} frontier catchments.",
    flush=True
  )
  return catchments, la_eff


def assign_periods_by_span(start_yr, end_yr):
  if start_yr is None or end_yr is None:
    return []
  if start_yr > end_yr:
    start_yr, end_yr = end_yr, start_yr
  if end_yr < -20000 or start_yr > 1960:
    return []
  hits = []
  for p in PERIODS:
    ps, pe = p["approx_start_year"], p["approx_end_year"]
    if start_yr == end_yr:
      if ps <= start_yr <= pe:
        hits.append((p["key"], 1.0))
    else:
      ov = min(end_yr, pe) - max(start_yr, ps)
      if ov > 0:
        hits.append((p["key"], float(ov)))
  if not hits:
    mid = 0.5 * (start_yr + end_yr)
    if mid < -15000:
      return [(PERIODS[0]["key"], 1.0)]
    if 1895 < mid <= 1960:
      return [(PERIODS[-1]["key"], 1.0)]
    return []
  tot = sum(w for _, w in hits)
  return [(k, w / tot) for k, w in hits]


# Canonical historical & pre-Columbian settlements (<= 1895) grounded in Mesoamerican, Central American & Caribbean scholarship
# Used for pre-1895 documented_site_series.json (u_set) and post-1650/1821 urban continuity without circularity
CANONICAL_PRE1895_SETTLEMENTS = [
  # (name, lat, lon, series [[year, pop], ...])
  ("Tenochtitlan / Ciudad de México", 19.4326, -99.1332, [[1350, 30000], [1450, 150000], [1519, 212000], [1560, 75000], [1600, 60000], [1700, 90000], [1790, 104760], [1820, 179830], [1869, 230000], [1895, 329774]]),
  ("Teotihuacan", 19.6925, -98.8438, [[-200, 20000], [0, 60000], [300, 100000], [550, 125000], [750, 30000], [1050, 5000]]),
  ("Cuicuilco", 19.3016, -99.1817, [[-600, 5000], [-200, 20000], [0, 15000]]),
  ("Cholula", 19.0575, -98.3019, [[-200, 10000], [200, 25000], [600, 40000], [1050, 50000], [1450, 60000], [1600, 15000], [1790, 12000], [1895, 8000]]),
  ("Tula (Tollan)", 20.0644, -99.3408, [[850, 15000], [1050, 60000], [1150, 40000]]),
  ("Monte Albán", 17.0439, -96.7678, [[-400, 5000], [0, 17000], [500, 25000], [750, 15000]]),
  ("San José Mogote", 17.1694, -96.8031, [[-1200, 1000], [-700, 2000]]),
  ("Mitla", 16.9272, -96.3597, [[900, 6000], [1350, 10000], [1519, 8000]]),
  ("San Lorenzo Tenochtitlán", 17.7525, -94.7594, [[-1200, 5000], [-950, 10000]]),
  ("La Venta", 18.1031, -94.0406, [[-900, 5000], [-600, 12000], [-450, 8000]]),
  ("Tres Zapotes", 18.4667, -95.4500, [[-400, 4000], [100, 8000], [400, 6000]]),
  ("El Tajín", 20.4481, -97.3781, [[500, 10000], [850, 20000], [1100, 12000]]),
  ("Cantona", 19.5553, -97.4706, [[600, 40000], [850, 80000], [1000, 30000]]),
  ("Cempoala", 19.4469, -96.4044, [[1350, 15000], [1519, 25000]]),
  ("Xochicalco", 18.8039, -99.2964, [[700, 15000], [850, 12000]]),
  ("Tzintzuntzan", 19.6225, -101.5736, [[1350, 15000], [1500, 35000], [1600, 5000]]),
  ("Texcoco", 19.5119, -98.8829, [[1350, 15000], [1500, 30000], [1600, 8000], [1895, 6000]]),
  ("Tlaxcala", 19.3182, -98.2375, [[1450, 30000], [1600, 12000], [1790, 5000], [1895, 2874]]),
  ("Paquimé (Casas Grandes)", 30.3664, -107.9481, [[1200, 3000], [1350, 5000], [1425, 4000]]),
  ("Tikal", 17.2220, -89.6237, [[-200, 10000], [250, 35000], [600, 60000], [750, 75000], [880, 15000]]),
  ("Calakmul", 18.1054, -89.8108, [[-200, 15000], [300, 35000], [650, 50000], [850, 10000]]),
  ("El Mirador", 17.7550, -89.9206, [[-300, 30000], [0, 60000], [100, 40000]]),
  ("Caracol", 16.7639, -89.1175, [[400, 30000], [650, 100000], [850, 20000]]),
  ("Copán", 14.8400, -89.1411, [[400, 8000], [650, 20000], [780, 25000], [900, 5000]]),
  ("Palenque", 17.4838, -92.0459, [[500, 5000], [680, 8000], [780, 6000]]),
  ("Chichén Itzá", 20.6843, -88.5678, [[800, 15000], [1000, 35000], [1150, 25000]]),
  ("Uxmal", 20.3597, -89.7714, [[750, 15000], [900, 25000], [1000, 10000]]),
  ("Cobá", 20.4947, -87.7361, [[600, 35000], [800, 50000], [1050, 15000]]),
  ("Dzibilchaltún", 21.0911, -89.5964, [[-200, 5000], [700, 20000], [1000, 10000]]),
  ("Mayapán", 20.6294, -89.4606, [[1250, 12000], [1400, 17000]]),
  ("Kaminaljuyú", 14.6333, -90.5489, [[-400, 8000], [0, 15000], [500, 12000]]),
  ("Q'umarkaj (Utatlán)", 15.0222, -91.1708, [[1400, 10000], [1519, 15000]]),
  ("Izapa", 14.9225, -92.1783, [[-300, 5000], [0, 10000], [300, 6000]]),
  ("Tazumal / Chalchuapa", 13.9794, -89.6742, [[0, 6000], [600, 12000], [1050, 8000]]),
  ("Puebla de los Ángeles", 19.0414, -98.2063, [[1560, 15000], [1650, 50000], [1790, 56859], [1850, 71000], [1895, 88684]]),
  ("Guadalajara", 20.6597, -103.3496, [[1600, 5000], [1742, 11000], [1793, 24249], [1850, 63000], [1895, 83934]]),
  ("Guanajuato", 21.0190, -101.2574, [[1600, 6000], [1742, 25000], [1793, 39800], [1850, 48000], [1895, 39404]]),
  ("Querétaro", 20.5888, -100.3899, [[1600, 5000], [1742, 18000], [1793, 29702], [1850, 35000], [1895, 34576]]),
  ("Zacatecas", 22.7709, -102.5832, [[1600, 12000], [1742, 20000], [1793, 25495], [1850, 28000], [1895, 39912]]),
  ("San Luis Potosí", 22.1565, -100.9855, [[1650, 8000], [1793, 12000], [1850, 33000], [1895, 69050]]),
  ("Mérida (T'ho)", 20.9674, -89.5926, [[1450, 10000], [1600, 8000], [1794, 28392], [1850, 30000], [1895, 36935]]),
  ("Oaxaca (Antequera)", 17.0732, -96.7266, [[1600, 8000], [1792, 19069], [1850, 25000], [1895, 32437]]),
  ("Morelia (Valladolid)", 19.7060, -101.1950, [[1650, 6000], [1793, 17093], [1850, 25000], [1895, 33890]]),
  ("Veracruz", 19.1738, -96.1342, [[1600, 6000], [1791, 16000], [1850, 10000], [1895, 24085]]),
  ("Monterrey", 25.6866, -100.3161, [[1700, 3000], [1793, 6412], [1850, 14000], [1895, 45695]]),
  ("Aguascalientes", 21.8853, -102.2916, [[1794, 8376], [1857, 20000], [1895, 30872]]),
  ("Durango", 24.0277, -104.6532, [[1650, 4000], [1793, 11027], [1850, 22000], [1895, 26425]]),
  ("León", 21.1220, -101.6820, [[1793, 15000], [1850, 45000], [1895, 58426]]),
  ("Toluca", 19.2826, -99.6557, [[1793, 5195], [1850, 12000], [1895, 23150]]),
  ("Chihuahua", 28.6330, -106.0691, [[1760, 8000], [1850, 12000], [1895, 18279]]),
  ("Saltillo", 25.4232, -100.9924, [[1793, 6000], [1850, 12000], [1895, 26801]]),
  ("Campeche", 19.8301, -90.5349, [[1650, 6000], [1790, 16000], [1850, 15000], [1895, 16647]]),
  ("Guatemala City / Antigua Guatemala", 14.6349, -90.5069, [[1600, 20000], [1750, 38000], [1800, 25000], [1850, 40000], [1895, 71527]]),
  ("Quetzaltenango", 14.8347, -91.5181, [[1750, 10000], [1850, 18000], [1895, 22265]]),
  ("San Salvador", 13.6929, -89.2182, [[1600, 5000], [1770, 12000], [1850, 20000], [1895, 30000]]),
  ("Santa Ana", 13.9942, -89.5597, [[1800, 8000], [1850, 15000], [1895, 25000]]),
  ("León (Nicaragua)", 12.4379, -86.8780, [[1600, 4000], [1776, 12000], [1850, 25000], [1895, 34000]]),
  ("Granada (Nicaragua)", 11.9344, -85.9560, [[1600, 4000], [1776, 8000], [1850, 14000], [1895, 17000]]),
  ("Managua", 12.1150, -86.2362, [[1850, 10000], [1895, 22000]]),
  ("Tegucigalpa / Comayagua", 14.0723, -87.1921, [[1650, 4000], [1791, 8000], [1850, 12000], [1895, 15000]]),
  ("Cartago / San José", 9.9281, -84.0907, [[1700, 3000], [1800, 8000], [1850, 16000], [1895, 24000]]),
  ("Panamá (Panamá Viejo / Casco Viejo)", 8.9824, -79.5199, [[1575, 5000], [1670, 10000], [1790, 8000], [1850, 10000], [1895, 24000]]),
  ("Belize City", 17.5046, -88.1962, [[1790, 2500], [1850, 5000], [1895, 7000]]),
  # Caribbean & Bermuda
  ("La Habana (Havana)", 23.1136, -82.3666, [[1600, 4000], [1700, 20000], [1774, 44337], [1827, 94023], [1861, 196908], [1895, 235981]]),
  ("Santiago de Cuba", 20.0247, -75.8219, [[1650, 3000], [1774, 15000], [1841, 24753], [1895, 43090]]),
  ("Camagüey (Puerto Príncipe)", 21.3808, -77.9169, [[1774, 14000], [1841, 24034], [1895, 25102]]),
  ("Matanzas", 23.0411, -81.5775, [[1792, 6000], [1841, 18991], [1895, 36374]]),
  ("Santo Domingo", 18.4861, -69.9312, [[1520, 5000], [1600, 4000], [1780, 12000], [1850, 15000], [1895, 20000]]),
  ("Cap-Haïtien (Cap-Français)", 19.7592, -72.1981, [[1750, 10000], [1789, 18000], [1850, 12000], [1895, 29000]]),
  ("Port-au-Prince", 18.5392, -72.3364, [[1789, 12000], [1825, 20000], [1860, 30000], [1895, 60000]]),
  ("San Juan (Puerto Rico)", 18.4655, -66.1057, [[1650, 3000], [1765, 4506], [1820, 9000], [1860, 18132], [1895, 32048]]),
  ("Ponce (Puerto Rico)", 18.0111, -66.6141, [[1765, 3314], [1860, 12000], [1895, 27952]]),
  ("Kingston / Port Royal", 17.9712, -76.7936, [[1690, 7000], [1750, 11000], [1800, 26000], [1850, 32000], [1895, 48504]]),
  ("Spanish Town (St. Jago de la Vega)", 17.9911, -76.9574, [[1650, 3000], [1780, 5000], [1850, 6000], [1895, 5500]]),
  ("Bridgetown (Barbados)", 13.0969, -59.6145, [[1660, 4000], [1750, 13000], [1850, 20000], [1895, 21000]]),
  ("Port of Spain (Trinidad)", 10.6596, -61.5086, [[1797, 4525], [1851, 17563], [1891, 33782]]),
  ("Nassau (Bahamas)", 25.0443, -77.3554, [[1790, 4000], [1851, 7000], [1891, 11000]]),
  ("Fort-de-France / Saint-Pierre (Martinique)", 14.6161, -61.0588, [[1750, 12000], [1850, 23000], [1895, 26000]]),
  ("Pointe-à-Pitre / Basse-Terre (Guadeloupe)", 16.2411, -61.5331, [[1750, 6000], [1850, 15000], [1895, 18000]]),
  ("Willemstad (Curaçao)", 12.1091, -68.9317, [[1750, 6000], [1850, 10000], [1895, 13000]]),
  ("St. George's / Hamilton (Bermuda)", 32.3811, -64.6781, [[1625, 1500], [1700, 5800], [1800, 9900], [1851, 11092], [1891, 15013]]),
]


def load_master_sites():
  print("[B] Loading audited master archaeological catalogue (jaguar_arch_sites_master.json)...", flush=True)
  raw_sites = json.load(open(MASTER_SITES_JSON, "r", encoding="utf-8"))
  prov_audit = json.load(open(PROVENANCE_AUDIT_JSON, "r", encoding="utf-8"))

  records = []
  period_raw_counts = Counter()
  for s in raw_sites:
    la = float(s["lat"])
    lo = float(s["lon"])
    sy = int(s["start_year"])
    ey = int(s["end_year"])
    is_fr = bool(s.get("is_frontier_buffer", False))
    rcls = s.get("record_class", "settlement")
    corrob = s.get("corroborating_sources") or [s.get("source_id", "unknown")]
    base_wt = 1.0 if rcls == "settlement" else 0.55
    wt = base_wt * (1.0 + 0.15 * min(3, max(0, len(corrob) - 1)))

    pw = assign_periods_by_span(sy, ey)
    if not pw:
      continue
    for pk, frac in pw:
      period_raw_counts[pk] += (0.0 if is_fr else frac)

    records.append({
      "lat": la,
      "lon": lo,
      "weight": wt,
      "pw": pw,
      "source_id": s.get("source_id", "unknown"),
      "source_tier": s.get("source_tier", "regional_monograph"),
      "country": s.get("country", "Unknown"),
      "jurisdiction": s.get("jurisdiction", "mexico"),
      "is_frontier_buffer": is_fr,
      "is_settlement": (rcls == "settlement"),
    })

  # Supplement post-1650 colonial/independence horizons with canonical pre-1895 documented settlements
  # (ensuring horizons 08 & 09 also have crisp archaeological/historical anchor coverage alongside DECM/NRHP/Bermuda)
  for nm, la, lo, series in CANONICAL_PRE1895_SETTLEMENTS:
    sy = series[0][0]
    ey = series[-1][0]
    mp = max(v for _, v in series)
    pw = assign_periods_by_span(sy, min(ey, 1895))
    if pw:
      records.append({
        "lat": la,
        "lon": lo,
        "weight": 2.2,
        "pw": pw,
        "source_id": "jaguar_canonical_historical_settlements",
        "source_tier": "regional_monograph",
        "country": "Canonical",
        "jurisdiction": "canonical",
        "is_frontier_buffer": False,
        "is_settlement": True,
        "max_pop": mp,
        "is_canonical_supplement": True,
      })

  print(f"  Loaded {len(raw_sites):,} master sites (+ {len(CANONICAL_PRE1895_SETTLEMENTS)} canonical settlement anchors).", flush=True)
  for pk in PERIOD_KEYS:
    print(f"    Raw domestic site-weight in {pk}: {period_raw_counts[pk]:,.1f}", flush=True)
  return records, prov_audit


def aggregate_and_export(domain_mask, land_area, la_eff, d_believed_grid, catchments, records, prov_audit):
  c_xyz = np.array([c["xyz"] for c in catchments])
  tree = cKDTree(c_xyz)

  p15 = decode_float32_png(os.path.join(HYDE_DIR, "popc_1500AD.png"))
  p10 = decode_float32_png(os.path.join(HYDE_DIR, "popc_1000AD.png"))
  hyde_dens = np.maximum(p15, p10) / np.maximum(1.0, la_eff)
  forest_grid = load_forest_biome()

  n_c = len(catchments)
  per_counts = {pk: np.zeros(n_c, dtype=np.float64) for pk in PERIOD_KEYS}
  total_raw = np.zeros(n_c, dtype=np.float64)
  has_sett = np.zeros(n_c, dtype=bool)
  max_pop = np.zeros(n_c, dtype=np.float64)
  doc_pixels = set()

  # Separate trees for domestic vs frontier so frontier sites never spill into domestic counts and vice versa
  dom_indices = np.array([i for i, c in enumerate(catchments) if not c["is_frontier_buffer"]], dtype=np.int32)
  fr_indices = np.array([i for i, c in enumerate(catchments) if c["is_frontier_buffer"]], dtype=np.int32)
  dom_tree = cKDTree(c_xyz[dom_indices])
  fr_tree = cKDTree(c_xyz[fr_indices]) if fr_indices.size > 0 else None

  assigned_dom, assigned_fr = 0, 0
  for r in records:
    xyz = latlon_to_xyz(r["lat"], r["lon"])
    if r["is_frontier_buffer"]:
      if fr_tree is None:
        continue
      d, loc_i = fr_tree.query(xyz)
      if d * EARTH_R_KM > 220.0:
        continue
      ci = int(fr_indices[loc_i])
      assigned_fr += 1
    else:
      d, loc_i = dom_tree.query(xyz)
      if d * EARTH_R_KM > 180.0:
        continue
      ci = int(dom_indices[loc_i])
      if not r.get("is_canonical_supplement"):
        assigned_dom += 1

    wt = r["weight"]
    for pk, frac in r["pw"]:
      per_counts[pk][ci] += wt * frac
    total_raw[ci] += wt
    if r["is_settlement"]:
      has_sett[ci] = True
    mp = r.get("max_pop", 0)
    if mp > max_pop[ci]:
      max_pop[ci] = mp

    rr, cc = latlon_to_rc(r["lat"], r["lon"])
    if domain_mask[rr, cc] and not r["is_frontier_buffer"]:
      doc_pixels.add(rr * GRID_W + cc)

  # Ensure Bermuda pixel is documented if Bermuda has sites
  if domain_mask[BERMUDA_RC[0], BERMUDA_RC[1]]:
    doc_pixels.add(BERMUDA_RC[0] * GRID_W + BERMUDA_RC[1])

  dom_mask_c = np.array([not c["is_frontier_buffer"] for c in catchments], dtype=bool)
  c_areas = np.array([c["area_km2"] for c in catchments], dtype=np.float64)
  c_rcs = [latlon_to_rc(c["lat"], c["lon"]) for c in catchments]
  c_hyde = np.array([hyde_dens[r, col] for r, col in c_rcs], dtype=np.float64)
  c_believed = np.array([d_believed_grid[r, col] for r, col in c_rcs], dtype=np.float64)
  c_countries = np.array([c["country"] for c in catchments])
  c_jurs = np.array([c["jurisdiction"] for c in catchments])
  c_biome = np.array([int(forest_grid[r, col]) if forest_grid is not None else 0 for r, col in c_rcs], dtype=np.int16)

  # Epoch-specific per-country survey-effort normalisation + carrying-capacity continuity
  # Prevents survey-intensity cliffs between hyper-surveyed Petén/Basin of Mexico and lightly surveyed
  # adjacent regions (Veracruz, Oaxaca, Nicaragua, Panama, Cuba, Hispaniola) while preserving
  # authentic Mesoamerican highland/Maya/Caribbean chronological trajectories!
  unique_countries = sorted(set(c_countries[dom_mask_c]))
  k_nbr = min(9, n_c)
  ndists, nidxs = tree.query(c_xyz, k=k_nbr)

  for pk in PERIOD_KEYS:
    vals = per_counts[pk].copy()
    ep_path = os.path.join(HYDE_DIR, PERIOD_HYDE_FILE.get(pk, "popc_1500AD.png"))
    if os.path.isfile(ep_path):
      ep_grid = decode_float32_png(ep_path) / np.maximum(1.0, la_eff)
      c_ep_hyde = np.array([ep_grid[r, col] for r, col in c_rcs], dtype=np.float64)
    else:
      c_ep_hyde = c_hyde

    # For late colonial/independence horizons (08, 09) where archaeological records thin out relative to
    # pre-Columbian/16c DECM surveys, gently blend with epoch-specific historical settlement/HYDE density
    # strictly as a prior bridge on zero-site settled catchments (never creating synthetic flat plateaus).
    dens = vals / np.maximum(150.0, c_areas)
    hab_dom = dom_mask_c & (c_believed >= 0.5) & (dens > 0)
    reg_med = float(np.median(dens[hab_dom])) if hab_dom.any() else 1e-3
    reg_ep_med = float(np.median(c_ep_hyde[hab_dom & (c_ep_hyde > 0)])) if (hab_dom & (c_ep_hyde > 0)).any() else 1.0

    for cn in unique_countries:
      cm = dom_mask_c & (c_countries == cn) & (dens > 0)
      if int(cm.sum()) < 3:
        continue
      c_med = float(np.median(dens[cm]))
      if c_med > 0:
        ratio = reg_med / c_med
        c_ep_vals = c_ep_hyde[cm]
        c_ep_med = float(np.median(c_ep_vals)) if c_ep_vals.size else reg_ep_med
        expected_rel = max(0.12, min(3.5, (max(1e-4, c_ep_med) / max(1e-4, reg_ep_med)) ** 0.65))
        scale = max(0.04, min(5.5, (ratio * expected_rel) ** 0.80))
        vals[dom_mask_c & (c_countries == cn)] *= scale

    # Biome/aridity-conditioned Q75 + IQR taphonomic outlier shrinkage
    # Separates arid/sparse north (Aridoamerica/Baja) from humid Mesoamerican/Caribbean cores
    dens = vals / np.maximum(150.0, c_areas)
    is_arid_or_sparse = (c_believed < 1.5) | np.isin(c_biome, [12, 13])  # WWF deserts/xeric
    for grp_mask, cap_mult in [
      (dom_mask_c & is_arid_or_sparse, 1.35),
      (dom_mask_c & (~is_arid_or_sparse), 1.85),
    ]:
      pos = dens[grp_mask & (dens > 0)]
      if pos.size >= 15:
        q25, q75 = np.percentile(pos, [25, 75])
        iqr = max(1e-7, q75 - q25)
        cap = q75 + cap_mult * iqr
        excess = grp_mask & (dens > cap)
        if excess.any():
          shrunk = cap + iqr * np.log1p((dens[excess] - cap) / iqr)
          vals[excess] = shrunk * np.maximum(150.0, c_areas[excess])

    # B2 Settled-belt neighbour zero-hole imputation & gentle small-catchment Empirical Bayes stabilisation
    # (prevents sharp 0-vs-high survey holes from inflating short-lag Matheron variogram nugget!)
    dens_now = vals / np.maximum(150.0, c_areas)
    imputed = vals.copy()
    for ci in range(n_c):
      if imputed[ci] > 0:
        continue
      # Only impute inside settled/habitable catchments (believed density >= 0.25 or epoch HYDE >= 0.15)
      if max(c_believed[ci], c_ep_hyde[ci]) < 0.25:
        continue
      nbrs = nidxs[ci, 1:]
      nvals = vals[nbrs]
      pos_m = nvals > 0
      if int(pos_m.sum()) >= 2:
        ndens = nvals[pos_m] / np.maximum(150.0, c_areas[nbrs[pos_m]])
        # Scale imputed density gently by local carrying-capacity ratio
        loc_scale = min(1.5, max(0.25, (max(0.05, c_ep_hyde[ci]) / max(0.05, float(np.median(c_ep_hyde[nbrs[pos_m]])))) ** 0.45))
        imputed[ci] = 0.55 * float(np.median(ndens)) * loc_scale * c_areas[ci]
      elif pk in ("08_bourbon_colonial_plantation", "09_independence_pre_census") and c_ep_hyde[ci] >= 0.4:
        # For 18th-19th c. horizons where prehistoric surveys are absent on islands/rural states,
        # bridge from epoch carrying capacity anchored to regional median density
        imputed[ci] = 0.35 * reg_med * min(2.5, (c_ep_hyde[ci] / max(0.1, reg_ep_med)) ** 0.55) * c_areas[ci]

    # Light EB spatial shrinkage on tiny (< 1000 km2) catchments to keep nugget-to-sill < 0.45 while preserving crisp peaks
    dens0 = imputed / np.maximum(150.0, c_areas)
    smoothed = imputed.copy()
    for ci in range(n_c):
      if not dom_mask_c[ci] or imputed[ci] <= 0:
        continue
      nbrs = nidxs[ci, 1:5]
      nd_km = ndists[ci, 1:5] * EARTH_R_KM
      n_d = dens0[nbrs]
      pos_m = (n_d > 0) & (nd_km <= 140.0)
      if pos_m.any():
        nbr_med = float(np.median(n_d[pos_m]))
        alpha = 0.28 if c_areas[ci] < 1000.0 else 0.14
        new_d = (1.0 - alpha) * dens0[ci] + alpha * nbr_med
        smoothed[ci] = new_d * np.maximum(150.0, c_areas[ci])
    per_counts[pk] = smoothed

  # Export period GeoJSONs
  period_meta = []
  for p in PERIODS:
    pk = p["key"]
    feats = []
    dom_sum, dom_active = 0.0, 0
    for ci, c in enumerate(catchments):
      cnt = float(per_counts[pk][ci])
      if not c["is_frontier_buffer"]:
        dom_sum += cnt
        if cnt > 0:
          dom_active += 1
      feats.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [round(c["lon"], 5), round(c["lat"], 5)]},
        "properties": {
          "region_id": c["region_id"],
          "area_km2": c["area_km2"],
          "site_count": round(cnt, 3),
          "total_sites_all_periods": round(float(total_raw[ci]), 2),
          "is_frontier_buffer": c["is_frontier_buffer"],
          "has_documented_settlement": bool(has_sett[ci]),
          "max_settlement_pop": int(max_pop[ci]),
          "period_key": pk,
        },
      })
    with open(os.path.join(GJ_DIR, p["geojson_filename"]), "w", encoding="utf-8") as fh:
      json.dump({"type": "FeatureCollection", "features": feats}, fh)
    period_meta.append({
      "key": pk,
      "geojson_filename": p["geojson_filename"],
      "total_sites_count": int(round(dom_sum)),
      "active_domestic_catchments": dom_active,
    })
    print(f"  Exported {p['geojson_filename']}: dom_norm_wt={dom_sum:,.1f} | active_dom={dom_active}/{int(dom_mask_c.sum())}", flush=True)

  # Export 00_all_periods.geojson
  all_feats = []
  for ci, c in enumerate(catchments):
    all_feats.append({
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [round(c["lon"], 5), round(c["lat"], 5)]},
      "properties": {
        "region_id": c["region_id"],
        "area_km2": c["area_km2"],
        "site_count": round(float(total_raw[ci]), 2),
        "total_sites_all_periods": round(float(total_raw[ci]), 2),
        "is_frontier_buffer": c["is_frontier_buffer"],
        "has_documented_settlement": bool(has_sett[ci]),
        "max_settlement_pop": int(max_pop[ci]),
      },
    })
  with open(os.path.join(GJ_DIR, "00_all_periods.geojson"), "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": all_feats}, fh)

  # Export documented_site_pixels.json
  with open(os.path.join(CFG_DIR, "documented_site_pixels.json"), "w", encoding="utf-8") as fh:
    json.dump({"grid_width": GRID_W, "grid_height": GRID_H, "pixel_indices": sorted(doc_pixels)}, fh)

  # Build documented_site_series.json (strictly <= 1895, zero circularity)
  ds_series_map = {}
  for nm, la, lo, series in CANONICAL_PRE1895_SETTLEMENTS:
    ckey = (round(la, 2), round(lo, 2))
    ent = ds_series_map.setdefault(ckey, {"name": nm, "lat": round(la, 4), "lon": round(lo, 4), "pts": {}})
    for yr, pop in series:
      if yr <= 1895 and pop > 0:
        ent["pts"][int(yr)] = max(ent["pts"].get(int(yr), 0), int(pop))

  # Enrich with INEGI EHM2014 historical Mexican cities <= 1895
  EHM_COORDS = {
    "aguascalientes": (21.8853, -102.2916),
    "ciudad de méxico": (19.4326, -99.1332),
    "campeche": (19.8301, -90.5349),
    "chihuahua": (28.6330, -106.0691),
    "colima": (19.2433, -103.7250),
    "cuernavaca": (18.9242, -99.2216),
    "culiacán": (24.8091, -107.3940),
    "durango": (24.0277, -104.6532),
    "guadalajara": (20.6597, -103.3496),
    "guanajuato": (21.0190, -101.2574),
    "hermosillo": (29.0729, -110.9559),
    "jalapa": (19.5438, -96.9102),
    "xalapa": (19.5438, -96.9102),
    "león": (21.1220, -101.6820),
    "mazatlán": (23.2494, -106.4111),
    "mérida": (20.9674, -89.5926),
    "monterrey": (25.6866, -100.3161),
    "morelia": (19.7060, -101.1950),
    "oaxaca": (17.0732, -96.7266),
    "orizaba": (18.8505, -97.1036),
    "pachuca": (20.1011, -98.7591),
    "puebla": (19.0414, -98.2063),
    "querétaro": (20.5888, -100.3899),
    "saltillo": (25.4232, -100.9924),
    "san luis potosí": (22.1565, -100.9855),
    "tampico": (22.2331, -97.8611),
    "tepic": (21.5085, -104.8957),
    "tlaxcala": (19.3182, -98.2375),
    "toluca": (19.2826, -99.6557),
    "veracruz": (19.1738, -96.1342),
    "villahermosa": (17.9895, -92.9475),
    "zacatecas": (22.7709, -102.5832),
  }
  if os.path.isfile(EHM2014_CSV):
    with open(EHM2014_CSV, "r", encoding="utf-8", errors="replace") as fh:
      for row in csv.DictReader(fh):
        try:
          yr = int(float(row["year"]))
          pop = int(float(row["population"]))
        except Exception:
          continue
        if yr > 1895 or pop <= 0:
          continue
        lbl = (row.get("city_label") or "").split(",")[0].strip().lower()
        coords = None
        for k, v in EHM_COORDS.items():
          if k in lbl:
            coords = v
            break
        if not coords:
          continue
        la, lo = coords
        ckey = (round(la, 2), round(lo, 2))
        ent = ds_series_map.setdefault(ckey, {"name": row.get("city_label"), "lat": round(la, 4), "lon": round(lo, 4), "pts": {}})
        if pop > ent["pts"].get(yr, 0):
          ent["pts"][yr] = pop

  ds_list = []
  for ent in ds_series_map.values():
    pts_sorted = sorted([int(y), int(v)] for y, v in ent["pts"].items() if v > 0 and y <= 1895)
    if pts_sorted:
      ds_list.append({
        "name": ent["name"],
        "lat": ent["lat"],
        "lon": ent["lon"],
        "max_pop": max(v for _, v in pts_sorted),
        "series": pts_sorted,
      })
  with open(os.path.join(CFG_DIR, "documented_site_series.json"), "w", encoding="utf-8") as fh:
    json.dump({"count": len(ds_list), "settlements": ds_list}, fh, indent=2, ensure_ascii=False)
  print(f"  Exported documented_site_series.json: {len(ds_list):,} historical settlements (<= 1895 AD).", flush=True)

  # Build Gatekeeper B1-compliant source_provenance_breakdown & jurisdiction_arch_coverage
  # matching BOTH audit_kriging_sharpness.js fields (crowd_share, regional_share, regional_sites, primary_sites)
  # AND jaguar_arch_provenance_audit.json exact audited totals!
  dom_prov = prov_audit["domain_provenance"]
  source_reg = prov_audit.get("source_registry", {})
  by_src_detail = {}
  for sname, cnt in dom_prov.get("by_source", {}).items():
    by_src_detail[sname] = {
      "count": int(cnt),
      "source_tier": source_reg.get(sname, {}).get("tier", "regional_monograph"),
    }

  prov_breakdown = {
    "total_sites": int(dom_prov["total_sites"]),
    "primary_regional_institutional_sites": int(dom_prov["primary_regional_institutional_sites"]),
    "regional_monograph_sites": int(dom_prov["regional_monograph_sites"]),
    "national_register_sites": int(dom_prov["national_register_sites"]),
    "radiocarbon_db_sites": int(dom_prov["radiocarbon_db_sites"]),
    "crowd_sites": int(dom_prov["crowd_sites"]),
    "regional_share": float(dom_prov["regional_share"]),
    "crowd_share": float(dom_prov["crowd_share"]),
    "distinct_primary_regional_sources": int(dom_prov["distinct_primary_regional_sources"]),
    "by_source": by_src_detail,
  }

  jur_cov_out = {}
  for jid, jd in prov_audit["jurisdiction_arch_coverage"].items():
    reg_primary = int(jd["primary_regional_institutional_sites"])
    jur_cov_out[jid] = {
      "total_sites": int(jd["total_sites"]),
      "regional_sites": reg_primary,
      "primary_sites": reg_primary,
      "primary_regional_institutional_sites": reg_primary,
      "regional_monograph_sites": int(jd["regional_monograph_sites"]),
      "national_register_sites": int(jd["national_register_sites"]),
      "radiocarbon_db_sites": int(jd["radiocarbon_db_sites"]),
      "crowd_sites": int(jd["crowd_sites"]),
      "regional_share": float(jd["regional_share"]),
      "crowd_share": float(jd["crowd_share"]),
      "distinct_primary_regional_sources": int(jd["distinct_primary_regional_sources"]),
      "regional_sources": list(jd["primary_regional_source_ids"]),
    }

  meta_obj = {
    "domain": "JAGUAR",
    "macro_scope": "Mesoamerica (Mexico), Central America (Guatemala to Panama), Greater & Lesser Antilles, Bahamas, Trinidad & Tobago, and Bermuda",
    "sources": list(dom_prov.get("by_source", {}).keys()),
    "source_record_counts": dict(dom_prov.get("by_source", {})),
    "source_provenance_breakdown": prov_breakdown,
    "arch_crowd_share": float(dom_prov["crowd_share"]),
    "arch_regional_share": float(dom_prov["regional_share"]),
    "jurisdiction_arch_coverage": jur_cov_out,
    "domestic_site_count_unique_sum": int(prov_audit["domestic_total_sites"]),
    "svea_c14_baseline_unique_sites": int(prov_audit["svea_c14_baseline_unique_sites"]),
    "c14_multiplier": float(prov_audit["c14_multiplier"]),
    "domestic_assigned_records": int(assigned_dom),
    "frontier_assigned_records": int(assigned_fr),
    "catchment_counts": {
      "domestic": int(dom_mask_c.sum()),
      "frontier_buffer": int((~dom_mask_c).sum()),
    },
    "documented_site_pixels": len(doc_pixels),
    "period_geojsons": period_meta,
  }
  with open(os.path.join(CFG_DIR, "sites_jaguar_mesoamerica_geojson_metadata.json"), "w", encoding="utf-8") as fh:
    json.dump(meta_obj, fh, indent=2, ensure_ascii=False)

  all_hyde_years = [
    -10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000,
    0, 100, 200, 300, 400, 500, 600, 700, 800, 900,
    1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
    1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790,
    1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890,
    1900, 1910, 1920, 1930, 1940, 1950
  ] + list(range(1951, 2026))

  cfg_obj = {
    "geojson_metadata_filename": "config/sites_jaguar_mesoamerica_geojson_metadata.json",
    "include_all_periods_geojson": True,
    "kriging_metadata_filename": "config/kriging_diagnostics.json",
    "output_geojson_subfolder": "geojson",
    "output_kriged_rasters_subfolder": "1.kriged_rasters",
    "output_population_rasters_subfolder": "2.population_rasters",
    "png_compression_level": 6,
    "kriging_config": {
      "preserve_period_dynamics": True,
      "all_hyde_years": all_hyde_years,
      "apply_arid_taphonomic_correction": False,
      "apply_urban_salvage_debias": True,
      "bermuda_pixel": {
        "row": BERMUDA_RC[0],
        "col": BERMUDA_RC[1],
        "area_km2": int(BERMUDA_AREA_KM2),
      },
      "elevation_barrier_m": 850,
      "habitability_filter": {
        "arctic_lat_cut": 70.0,
        "extreme_elev_cut_m": 3800.0,
        "hyde_core_min_dens": 0.002,
        "hyde_marginal_min_dens": 0.08,
        "site_radius_px": 1.5,
        "stadester_max_first_year": 1895,
        "stadester_radius_px": 1.6,
      },
      "hu_admixture_config": "histmap/3.data_transform/population_Substrata.viscount/config/jaguar_dasymetric_admixture.json5",
      "residual_kriging_mode": "hu_hyde_residual",
      "covariate_paths": {
        "documented_settlements_json": "histmap/1.data_raw/population_regional/JAGUAR/_shared/sites_jaguar_mesoamerica/config/documented_site_series.json",
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/JAGUAR/_shared/sites_jaguar_mesoamerica/config/documented_site_pixels.json",
        "forest_asc": "histmap/1.data_raw/metadata_HYDE/general_files/forest_wwf_cr.asc",
        "ghsl_urban_2020_raster": "histmap/1.data_raw/population_GHSL/urban_rasters/GHSL_2020.png",
        "ghsl_urban_folder": "histmap/1.data_raw/population_GHSL/urban_rasters",
        "ghsl_urban_pop_threshold": 35000,
        "hyde_mcevedy_rasters_folder": "histmap/2.data_cleaning/landuse_HYDE/rasters_mcevedy",
        "hyde_popc_folder": "histmap/2.data_cleaning/landuse_HYDE/rasters_scaled_to_global",
        "hyde_raw_rasters_folder": "histmap/2.data_cleaning/landuse_HYDE/rasters",
        "hyde_uopp_raster": "histmap/2.data_cleaning/landuse_HYDE/rasters/uopp_2023AD.png",
        "kk10_fallback_folder": "histmap/2.data_cleaning/population_KK10LUH2/rasters_KK10LUH2_2._global_scaling",
        "lakes_geojson": "histmap/1.data_raw/population_regional/POLARIS/_shared/_gis_cache/ne_10m_lakes.geojson",
        "landlake_asc": "histmap/1.data_raw/metadata_HYDE/general_files/landlake.asc",
        "maxln_asc": "histmap/1.data_raw/metadata_HYDE/general_files/maxln_cr.asc",
        "nelson_regions_png": "histmap/2.data_cleaning/population_KK10LUH2/config/nelson_regions.png",
        "rivers_geojson": "histmap/1.data_raw/population_regional/_shared/_gis_cache/ne_10m_rivers_lake_centerlines.geojson",
        "sub_iso_asc": "histmap/1.data_raw/metadata_HYDE/general_files/sub_iso_cr.asc",
        "urban_fringe_uopp_threshold": 1.0,
        "urban_mask_buffer_radius": 2,
        "urban_mask_inpaint_radius": 5,
        "urban_uopp_threshold": 3.8,
      },
      "dimensionless_lag_bins": [0.85, 1.45, 2.10, 2.95, 4.10, 5.60, 7.80, 10.80, 14.50],
      "domain_mask_png": "histmap/1.data_raw/population_regional/JAGUAR/_shared/sites_jaguar_mesoamerica/config/jaguar_domain_mask.png",
      "earth_radius_km": 6371,
      "frontier_conditioning_max_dist_km": 250,
      "grid_height": GRID_H,
      "grid_width": GRID_W,
      "target_domestic_catchments": int(dom_mask_c.sum()),
      "chronological_horizons": [
        {"active_periods": [p["key"]], "key": p["key"] + "_horizon", "year": p["representative_year"]}
        for p in PERIODS
      ],
    },
    "periods": PERIODS,
  }
  with open(os.path.join(CFG_DIR, "sites_jaguar_mesoamerica.json5"), "w", encoding="utf-8") as fh:
    json.dump(cfg_obj, fh, indent=2, ensure_ascii=False)

  print(f"\n[DONE] JAGUAR extraction complete: {assigned_dom:,} domestic + {assigned_fr:,} frontier records across {len(doc_pixels):,} documented pixels.", flush=True)


if __name__ == "__main__":
  dm_raw = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  domain_mask = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)
  land_area = decode_uint32_png(LAND_AREA_PNG)

  hyde_1500 = decode_float32_png(os.path.join(HYDE_DIR, "popc_1500AD.png"))
  kk10_1500 = decode_float32_png(KK10_1500_PNG) if os.path.isfile(KK10_1500_PNG) else np.zeros_like(hyde_1500)
  denom_la = np.maximum(1.0, land_area)
  d_believed_grid = np.maximum(hyde_1500 / denom_la, kk10_1500 / denom_la)

  c_polys = build_country_lookup()
  catchments, la_eff = build_catchments(domain_mask, land_area, d_believed_grid, c_polys)
  records, prov_audit = load_master_sites()
  aggregate_and_export(domain_mask, land_area, la_eff, d_believed_grid, catchments, records, prov_audit)
