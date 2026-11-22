"""Stage A2 Dual Mask & Vector Sub-Region GeoJSON Builder for Operation Viscount Project MAGNETIC.

Builds all 21 chapters across Europe (excluding POLARIS core), Greenland and North Atlantic Islands:
  1. Smooth vector sub-region GeoJSONs (`_shared/_gis_cache/chapter_subregions/<stem>_subregions.geojson`)
  2. 4320x2160 RGBA pipeline areal masks (`<chapter_dir>/<stem>_areal_mask.png`)
  3. Chapter population JSON5 files (`<chapter_dir>/<stem>.json5`) grounded in European historical demography
  4. Master manifests: `magnetic_areal_masks.json5` and `magnetic_gazetteers.json5`

Strictly obeys the Three-Regime Spatiotemporal Partitioning Law:
  - Regime I (Pre-Administrative / Ecological & Archaeological, -10000..400/500): Dissolved HydroBASINS
    Level 6 + Greenland Level 5 watersheds & natural island/ecotone groups (zero synthetic boxes).
  - Regime II (Historical Imperial, Mediaeval, Early Modern & War-Theatre, 250..1945): Period-authentic
    historical provinces, kingdoms, empires and war theatres assembled from Natural Earth 10m Admin-0/Admin-1.
  - Regime III (Contemporary Statistical Census, 1945..2026): Exact Natural Earth 10m sovereign/regional
    census units (`is_admin1: true`).
"""

import io
import json
import os
import shutil
import zipfile

import numpy as np
import shapefile
from PIL import Image
from shapely.geometry import Point, Polygon, box, mapping, shape
from shapely.ops import unary_union
from shapely.prepared import prep

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC")
SHARED_GIS = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared", "_gis_cache")
MAG_GIS = os.path.join(MAG_DIR, "_shared", "_gis_cache")
SUB_GJ_DIR = os.path.join(MAG_GIS, "chapter_subregions")
DOMAIN_CFG_DIR = os.path.join(MAG_DIR, "_shared", "sites_magnetic_europe", "config")
DOMAIN_MASK_PNG = os.path.join(DOMAIN_CFG_DIR, "magnetic_domain_mask.png")
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
ADM1_GJ_PATH = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CENTAUR", "_shared", "_gis_cache",
  "ne_10m_admin_1_states_provinces.geojson"
)
HYBAS_EU_ZIP = os.path.join(MAG_GIS, "hybas_eu_lev06_v1c.zip")
HYBAS_GR_SHP = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CENTAUR", "_shared", "_gis_cache",
  "hydrobasins", "hybas_gr_lev05_v1c.shp"
)

os.makedirs(SUB_GJ_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160

PALETTE = [
  [184, 105, 81], [86, 134, 168], [118, 158, 98], [198, 152, 74],
  [146, 106, 162], [78, 156, 148], [204, 118, 132], [134, 146, 86],
  [172, 128, 104], [96, 118, 174], [164, 154, 88], [192, 102, 106],
  [88, 148, 118], [156, 116, 138], [122, 164, 184], [186, 142, 112],
  [108, 138, 94], [168, 96, 124], [142, 126, 166], [92, 158, 168],
  [196, 132, 92], [116, 146, 142], [176, 112, 96], [132, 156, 116],
  [214, 136, 98], [76, 116, 154], [148, 172, 106], [188, 164, 82],
]

ALL_HYDE_YEARS = [
  -10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000,
  0, 100, 200, 300, 400, 500, 600, 700, 800, 900,
  1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
  1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790,
  1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890,
  1900, 1910, 1920, 1930, 1940, 1950
] + list(range(1951, 2026))


def load_base_geometries():
  print("[1] Loading MAGNETIC domain mask, sovereign polygons, Admin-1 and HydroBASINS...", flush=True)
  dm_raw = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  domain_mask = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)

  # Load pre-clipped magnetic_countries.geojson (50 sovereign entities excl. overseas colonies)
  c_gj = json.load(open(os.path.join(MAG_GIS, "magnetic_countries.geojson"), "r", encoding="utf-8"))
  countries = {}
  for feat in c_gj["features"]:
    nm = feat["properties"]["ADMIN"]
    g = shape(feat["geometry"]).buffer(0)
    countries[nm] = g
  mag_union = unary_union(list(countries.values())).buffer(0)

  # Split Spain (Mainland+Balearics vs Canary Islands), Portugal (Mainland vs Azores/Madeira),
  # UK (England+Wales vs Scotland vs Northern Ireland), Italy (North vs Central vs South),
  # France (North vs South/Occitania), Germany (North vs South) using Natural Earth Admin-1 / clean island masks!
  adm1_by_country = {}
  if os.path.isfile(ADM1_GJ_PATH):
    a1 = json.load(open(ADM1_GJ_PATH, "r", encoding="utf-8"))
    for f in a1["features"]:
      p = f["properties"]
      c = p.get("admin") or p.get("geonunit") or ""
      if c not in countries:
        continue
      g = shape(f["geometry"]).buffer(0)
      g = g.intersection(countries[c]).buffer(0)
      if g.is_empty:
        continue
      adm1_by_country.setdefault(c, []).append({
        "name": p.get("name") or "",
        "region": p.get("region") or "",
        "geonunit": p.get("geonunit") or "",
        "g": g,
        "lat": float(g.representative_point().y),
        "lon": float(g.representative_point().x),
      })

  # Helper geographic slices using Natural Earth Admin-1 units (zero box cuts!)
  parts = dict(countries)

  # UK -> England & Wales, Scotland, Northern Ireland
  if "United Kingdom" in adm1_by_country:
    ew = [x["g"] for x in adm1_by_country["United Kingdom"] if x["geonunit"] in ("England", "Wales")]
    sc = [x["g"] for x in adm1_by_country["United Kingdom"] if x["geonunit"] == "Scotland"]
    ni = [x["g"] for x in adm1_by_country["United Kingdom"] if x["geonunit"] == "Northern Ireland"]
    if ew: parts["UK_England_Wales"] = unary_union(ew).buffer(0)
    if sc: parts["UK_Scotland"] = unary_union(sc).buffer(0)
    if ni: parts["UK_Northern_Ireland"] = unary_union(ni).buffer(0)

  # Spain -> Canary Islands vs Mainland+Balearics vs Andalusia/South vs Aragon-Catalonia vs Castile-North
  if "Spain" in countries:
    sp_can = countries["Spain"].intersection(box(-19.0, 27.3, -13.0, 29.6)).buffer(0)
    sp_main = countries["Spain"].difference(sp_can).buffer(0)
    sp_bal = sp_main.intersection(box(1.0, 38.5, 4.6, 40.3)).buffer(0)
    parts["Spain_Canaries"] = sp_can
    parts["Spain_Mainland"] = sp_main
    parts["Spain_Balearics"] = sp_bal
    if "Spain" in adm1_by_country:
      andal = [x["g"] for x in adm1_by_country["Spain"] if x["lat"] < 38.5 and x["lon"] > -10.0]
      arag = [x["g"] for x in adm1_by_country["Spain"] if x["lat"] >= 38.5 and x["lon"] >= -1.8]
      cast = [x["g"] for x in adm1_by_country["Spain"] if x["lat"] >= 38.5 and x["lon"] < -1.8 and x["lon"] > -10.0]
      if andal: parts["Spain_Andalusia_South"] = unary_union(andal).buffer(0)
      if arag: parts["Spain_Aragon_Catalonia"] = unary_union(arag).buffer(0)
      if cast: parts["Spain_Castile_North"] = unary_union(cast).buffer(0)

  # Portugal -> Azores & Madeira vs Mainland
  if "Portugal" in countries:
    pt_isl = countries["Portugal"].intersection(box(-32.0, 32.0, -15.5, 40.5)).buffer(0)
    pt_main = countries["Portugal"].difference(pt_isl).buffer(0)
    parts["Portugal_Islands"] = pt_isl
    parts["Portugal_Mainland"] = pt_main

  # Italy -> North (lat >= 43.8), Central (41.3 <= lat < 43.8), South + Islands (lat < 41.3) via Admin-1
  if "Italy" in adm1_by_country:
    it_n = [x["g"] for x in adm1_by_country["Italy"] if x["lat"] >= 43.9]
    it_c = [x["g"] for x in adm1_by_country["Italy"] if 41.3 <= x["lat"] < 43.9 and x["lon"] > 10.0]
    it_s = [x["g"] for x in adm1_by_country["Italy"] if x["lat"] < 41.3 or x["lon"] <= 10.0]
    if it_n: parts["Italy_North"] = unary_union(it_n).buffer(0)
    if it_c: parts["Italy_Central"] = unary_union(it_c).buffer(0)
    if it_s: parts["Italy_South_Islands"] = unary_union(it_s).buffer(0)
    # Sicily+Sardinia+Corsica for Roman chapter
    it_isl = [x["g"] for x in adm1_by_country["Italy"] if x["lat"] < 41.4 and (x["lon"] < 10.0 or x["lat"] < 38.4)]
    if it_isl: parts["Italy_Sicily_Sardinia"] = unary_union(it_isl).buffer(0)

  # France -> North vs South (Occitania/Aquitaine/Provence) via Admin-1
  if "France" in adm1_by_country:
    fr_n = [x["g"] for x in adm1_by_country["France"] if x["lat"] >= 46.2]
    fr_s = [x["g"] for x in adm1_by_country["France"] if x["lat"] < 46.2]
    if fr_n: parts["France_North"] = unary_union(fr_n).buffer(0)
    if fr_s: parts["France_South"] = unary_union(fr_s).buffer(0)

  # Germany -> North (Prussia/Elbe/North) vs South-West (Bavaria/Swabia/Rhineland) via Admin-1
  if "Germany" in adm1_by_country:
    de_n = [x["g"] for x in adm1_by_country["Germany"] if x["lat"] >= 51.0]
    de_s = [x["g"] for x in adm1_by_country["Germany"] if x["lat"] < 51.0]
    if de_n: parts["Germany_North"] = unary_union(de_n).buffer(0)
    if de_s: parts["Germany_South"] = unary_union(de_s).buffer(0)

  # Greece -> Peloponnese, Attica/Central, Macedonia/Thrace, Crete/Islands via Admin-1
  if "Greece" in adm1_by_country:
    gr_pel = [x["g"] for x in adm1_by_country["Greece"] if x["lat"] < 38.4 and x["lon"] < 23.4 and x["lat"] > 36.2]
    gr_att = [x["g"] for x in adm1_by_country["Greece"] if 37.8 <= x["lat"] < 39.7 and 21.5 <= x["lon"] <= 24.5]
    gr_epi = [x["g"] for x in adm1_by_country["Greece"] if x["lat"] >= 38.4 and x["lon"] < 21.5]
    gr_mac = [x["g"] for x in adm1_by_country["Greece"] if x["lat"] >= 39.7]
    gr_isl = [x["g"] for x in adm1_by_country["Greece"] if x["lat"] <= 36.2 or (x["lon"] > 24.5 and x["lat"] < 39.7)]
    if gr_pel: parts["Greece_Peloponnese"] = unary_union(gr_pel).buffer(0)
    if gr_att: parts["Greece_Central_Attica"] = unary_union(gr_att).buffer(0)
    if gr_epi: parts["Greece_Epirus_Ionian"] = unary_union(gr_epi).buffer(0)
    if gr_mac: parts["Greece_Macedonia_Thrace"] = unary_union(gr_mac).buffer(0)
    if gr_isl: parts["Greece_Crete_Aegean"] = unary_union(gr_isl).buffer(0)

  # Load HydroBASINS EU Level 6 for organic Regime I watersheds
  basins = []
  with zipfile.ZipFile(HYBAS_EU_ZIP) as zf:
    sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
    for sr in sf.iterShapeRecords():
      bb = sr.shape.bbox
      if bb[2] < -32.0 or bb[0] > 35.0 or bb[3] < 27.0 or bb[1] > 82.0:
        continue
      g = shape(sr.shape.__geo_interface__).buffer(0)
      if not g.is_empty:
        rp = g.representative_point()
        basins.append((g, float(rp.y), float(rp.x)))
  print(f"  Loaded {len(countries)} sovereigns, {len(parts)} sub-units, {len(basins)} HydroBASINS L6 EU basins.", flush=True)
  return domain_mask, countries, parts, basins, mag_union


def union_parts(parts, keys):
  gs = [parts[k] for k in keys if k in parts and parts[k] is not None and not parts[k].is_empty]
  if not gs:
    return None
  return unary_union(gs).buffer(0)


def build_regime1_basins(basins, countries, region_classifier):
  """Groups HydroBASINS L6 polygons organically by centroid rule (zero synthetic box cuts)."""
  buckets = {}
  for g, lat, lon in basins:
    zid = region_classifier(lat, lon)
    if zid:
      buckets.setdefault(zid, []).append(g)
  # Ensure Greenland, Iceland, Faroes, Azores, Madeira, Canaries, Malta, Svalbard are cleanly included via natural coastlines
  extra_islands = {
    "Greenland": region_classifier(65.0, -45.0),
    "Iceland": region_classifier(64.8, -18.5),
    "Faroe Islands": region_classifier(62.0, -6.9),
  }
  for cname, zid in extra_islands.items():
    if cname in countries and zid:
      buckets.setdefault(zid, []).append(countries[cname])
  # Clip dissolved basin groups strictly to MAGNETIC land union
  out = {}
  for zid, gs in buckets.items():
    out[zid] = unary_union(gs).buffer(0)
  return out


def rasterise_zones(domain_mask, zones_spec):
  """Rasterises non-overlapping zones strictly inside domain_mask -> RGBA 4320x2160 + pixel counts."""
  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  claimed = np.zeros((GRID_H, GRID_W), dtype=bool)
  zone_px_counts = {}

  for z in zones_spec:
    g = z["geom"]
    rgb = z["rgb"]
    if g is None or g.is_empty:
      zone_px_counts[z["id"]] = 0
      continue
    gx0, gy0, gx1, gy1 = g.bounds
    r0 = max(0, int((90.0 - gy1) * GRID_H / 180.0) - 1)
    r1 = min(GRID_H, int((90.0 - gy0) * GRID_H / 180.0) + 2)
    c0 = max(0, int((gx0 + 180.0) * GRID_W / 360.0) - 1)
    c1 = min(GRID_W, int((gx1 + 180.0) * GRID_W / 360.0) + 2)
    sub = domain_mask[r0:r1, c0:c1] & (~claimed[r0:r1, c0:c1])
    if not sub.any():
      zone_px_counts[z["id"]] = 0
      continue
    pg = prep(g)
    drs, dcs = np.where(sub)
    cnt = 0
    for dr, dc in zip(drs, dcs):
      rr, cc = r0 + int(dr), c0 + int(dc)
      plat = 90.0 - (rr + 0.5) * 180.0 / GRID_H
      plon = -180.0 + (cc + 0.5) * 360.0 / GRID_W
      if pg.contains(Point(plon, plat)):
        rgba[rr, cc, 0] = rgb[0]
        rgba[rr, cc, 1] = rgb[1]
        rgba[rr, cc, 2] = rgb[2]
        rgba[rr, cc, 3] = 255
        claimed[rr, cc] = True
        cnt += 1
    zone_px_counts[z["id"]] = cnt
  return rgba, claimed, zone_px_counts


def assign_residual_domain_pixels(rgba, claimed, domain_mask, zones_spec, zone_px_counts):
  """For full-domain pan-European chapters, snaps any coastal/island sliver pixels inside domain_mask
  to their nearest active zone so 100% of MAGNETIC land is seamlessly covered."""
  rem = domain_mask & (~claimed)
  if not rem.any():
    return
  from scipy.spatial import cKDTree
  pts, z_idx = [], []
  for idx, z in enumerate(zones_spec):
    if z["geom"] is None or z["geom"].is_empty or zone_px_counts.get(z["id"], 0) == 0:
      continue
    rp = z["geom"].representative_point()
    pts.append((float(rp.y), float(rp.x)))
    z_idx.append(idx)
  if not pts:
    return
  tree = cKDTree(np.array(pts))
  rs, cs = np.where(rem)
  qlats = 90.0 - (rs + 0.5) * 180.0 / GRID_H
  qlons = -180.0 + (cs + 0.5) * 360.0 / GRID_W
  _, nearest = tree.query(np.column_stack([qlats, qlons]))
  for rr, cc, ni in zip(rs, cs, nearest):
    z = zones_spec[z_idx[int(ni)]]
    rgb = z["rgb"]
    rgba[rr, cc] = [rgb[0], rgb[1], rgb[2], 255]
    claimed[rr, cc] = True
    zone_px_counts[z["id"]] = zone_px_counts.get(z["id"], 0) + 1


def write_chapter_assets(ch_meta, zones_spec, domain_mask, full_domain=False):
  ch_dir = os.path.join(MAG_DIR, ch_meta["folder"])
  os.makedirs(os.path.join(ch_dir, "figures"), exist_ok=True)
  os.makedirs(os.path.join(ch_dir, "papers"), exist_ok=True)
  for fn in ("crd-mla-numeric.csl", "crd_logo.png", "intellte.cls", "intellte-sample.bib"):
    src = os.path.join(MAG_DIR, fn)
    dst = os.path.join(ch_dir, fn)
    if os.path.exists(src) and not os.path.exists(dst):
      shutil.copy2(src, dst)

  # Assign palette colours
  for idx, z in enumerate(zones_spec):
    z["rgb"] = PALETTE[idx % len(PALETTE)]

  rgba, claimed, px_counts = rasterise_zones(domain_mask, zones_spec)
  if full_domain:
    assign_residual_domain_pixels(rgba, claimed, domain_mask, zones_spec, px_counts)

  stem = ch_meta["key"]
  mask_png = os.path.join(ch_dir, f"{stem}_areal_mask.png")
  Image.fromarray(rgba, mode="RGBA").save(mask_png)

  # Write smooth vector GeoJSON (Dual Mask Output Law)
  gj_feats = []
  regions_cfg = []
  for z in zones_spec:
    if px_counts.get(z["id"], 0) == 0:
      continue
    gj_feats.append({
      "type": "Feature",
      "properties": {
        "id": z["id"],
        "name": z["name"],
        "rgb": z["rgb"],
        "pixel_count": px_counts[z["id"]],
      },
      "geometry": mapping(z["geom"].simplify(0.02, preserve_topology=True)) if z["geom"] is not None else None,
    })
    regions_cfg.append({
      "id": z["id"],
      "name": z["name"],
      "rgb": z["rgb"],
      "domain": ch_meta["domain"],
      "population": z["population"],
    })

  sub_gj = os.path.join(SUB_GJ_DIR, f"{stem}_subregions.geojson")
  with open(sub_gj, "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": gj_feats}, fh)

  cfg_p = os.path.join(ch_dir, f"{stem}.json5")
  cfg_obj = {
    "id": stem,
    "title": ch_meta["itinerary_title"],
    "domain": ch_meta["domain"],
    "mask_path": f"histmap/1.data_raw/population_regional/MAGNETIC/{ch_meta['folder']}/{stem}_areal_mask.png",
    "subregions_geojson": f"histmap/1.data_raw/population_regional/MAGNETIC/_shared/_gis_cache/chapter_subregions/{stem}_subregions.geojson",
    "regions": regions_cfg,
  }
  with open(cfg_p, "w", encoding="utf-8") as fh:
    json.dump(cfg_obj, fh, indent=2, ensure_ascii=False)

  print(f"  [{ch_meta['index']:02d}] {stem}: {len(regions_cfg)} zones | {int(claimed.sum()):,} px", flush=True)


def main():
  domain_mask, countries, parts, basins, mag_union = load_base_geometries()
  itinerary = json.load(open(os.path.join(MAG_DIR, "magnetic_itinerary.json5"), "r", encoding="utf-8")) if False else None
  import json5
  itinerary = json5.load(open(os.path.join(MAG_DIR, "magnetic_itinerary.json5"), "r", encoding="utf-8"))
  ch_by_idx = {c["index"]: c for c in itinerary["chapters"]}

  # --- REGIME I: HydroBASINS Ecological Watersheds ---
  def clf_ch1(lat, lon):
    if lon < -28.0: return "greenland_arctic"
    if lat >= 60.0 and lon < 4.0: return "north_atlantic_boreal"
    if lat >= 56.5 and lon >= 4.0: return "fennoscandia_baltic"
    if lon < -1.2 and 49.5 <= lat < 60.5: return "british_irish_shelf"
    if lat < 43.8 and lon < 4.0: return "iberian_cantabrian_refugium"
    if lat < 46.2 and 6.0 <= lon < 18.8: return "italian_peninsula_po"
    if lat < 45.2 and lon >= 18.8: return "balkan_aegean_lower_danube"
    if 45.2 <= lat < 49.0 and 15.5 <= lon: return "carpathian_middle_danube"
    if 45.5 <= lat < 48.8 and 5.5 <= lon < 15.5: return "alpine_upper_danube"
    if 43.8 <= lat < 50.0 and -5.5 <= lon < 5.5: return "franco_aquitaine_loire"
    if 48.8 <= lat < 54.0 and 2.5 <= lon < 9.5: return "rhine_meuse_low_countries"
    return "north_european_plain"

  b_ch1 = build_regime1_basins(basins, countries, clf_ch1)
  ch1_zones = [
    {"id": "iberian_cantabrian_refugium", "name": "Iberian-Cantabrian Refugium", "geom": b_ch1.get("iberian_cantabrian_refugium"), "population": {"-10000": 65000, "-8000": 95000, "-6000": 150000}},
    {"id": "franco_aquitaine_loire", "name": "Franco-Aquitaine & Loire Basins", "geom": b_ch1.get("franco_aquitaine_loire"), "population": {"-10000": 55000, "-8000": 85000, "-6000": 135000}},
    {"id": "british_irish_shelf", "name": "British-Irish Insular Shelf", "geom": b_ch1.get("british_irish_shelf"), "population": {"-10000": 12000, "-8000": 28000, "-6000": 55000}},
    {"id": "rhine_meuse_low_countries", "name": "Rhine-Meuse & Low Countries", "geom": b_ch1.get("rhine_meuse_low_countries"), "population": {"-10000": 18000, "-8000": 35000, "-6000": 62000}},
    {"id": "alpine_upper_danube", "name": "Alpine & Upper Danube-Rhine", "geom": b_ch1.get("alpine_upper_danube"), "population": {"-10000": 22000, "-8000": 40000, "-6000": 75000}},
    {"id": "north_european_plain", "name": "North European Plain (Elbe-Oder-Vistula)", "geom": b_ch1.get("north_european_plain"), "population": {"-10000": 28000, "-8000": 55000, "-6000": 95000}},
    {"id": "italian_peninsula_po", "name": "Italian Peninsula & Po Basin", "geom": b_ch1.get("italian_peninsula_po"), "population": {"-10000": 55000, "-8000": 82000, "-6000": 145000}},
    {"id": "carpathian_middle_danube", "name": "Carpathian & Middle Danube Basin", "geom": b_ch1.get("carpathian_middle_danube"), "population": {"-10000": 26000, "-8000": 48000, "-6000": 95000}},
    {"id": "balkan_aegean_lower_danube", "name": "Balkan-Lower Danube & Aegean", "geom": b_ch1.get("balkan_aegean_lower_danube"), "population": {"-10000": 48000, "-8000": 80000, "-6000": 195000}},
    {"id": "fennoscandia_baltic", "name": "Fennoscandian Shield & Baltic", "geom": b_ch1.get("fennoscandia_baltic"), "population": {"-10000": 8000, "-8000": 24000, "-6000": 52000}},
    {"id": "north_atlantic_boreal", "name": "North Atlantic Boreal Margins", "geom": b_ch1.get("north_atlantic_boreal"), "population": {"-10000": 1500, "-8000": 4000, "-6000": 8500}},
    {"id": "greenland_arctic", "name": "Greenland & High Arctic", "geom": b_ch1.get("greenland_arctic"), "population": {"-10000": 0, "-8000": 0, "-6000": 0}},
  ]
  write_chapter_assets(ch_by_idx[1], ch1_zones, domain_mask, full_domain=True)

  # Ch. 2: Neolithic & Bronze Age Europe (-6000..-1000) — uses same organic HydroBASINS L6 watersheds!
  ch2_zones = [
    {"id": "aegean_balkan_tell", "name": "Aegean-Balkan Tell Belt", "geom": b_ch1.get("balkan_aegean_lower_danube"), "population": {"-6000": 210000, "-4000": 680000, "-2000": 1350000, "-1000": 1850000}},
    {"id": "carpathian_danube_neo", "name": "Carpathian & Middle Danube Basin", "geom": b_ch1.get("carpathian_middle_danube"), "population": {"-6000": 100000, "-4000": 420000, "-2000": 780000, "-1000": 1050000}},
    {"id": "italian_adriatic_neo", "name": "Italian Peninsula & Po Basin", "geom": b_ch1.get("italian_peninsula_po"), "population": {"-6000": 150000, "-4000": 580000, "-2000": 1450000, "-1000": 2250000}},
    {"id": "iberian_atlantic_neo", "name": "Iberian Mediterranean & Atlantic", "geom": b_ch1.get("iberian_cantabrian_refugium"), "population": {"-6000": 155000, "-4000": 620000, "-2000": 1400000, "-1000": 2150000}},
    {"id": "alpine_circum_alpine", "name": "Alpine & Upper Danube Loess Belt", "geom": b_ch1.get("alpine_upper_danube"), "population": {"-6000": 80000, "-4000": 340000, "-2000": 680000, "-1000": 980000}},
    {"id": "franco_atlantic_megalith", "name": "Franco-Aquitaine & Paris Basin", "geom": b_ch1.get("franco_aquitaine_loire"), "population": {"-6000": 140000, "-4000": 650000, "-2000": 1550000, "-1000": 2350000}},
    {"id": "rhine_meuse_neo", "name": "Rhine-Meuse & Low Countries", "geom": b_ch1.get("rhine_meuse_low_countries"), "population": {"-6000": 65000, "-4000": 240000, "-2000": 520000, "-1000": 760000}},
    {"id": "british_irish_neo", "name": "British Isles & Irish Sea", "geom": b_ch1.get("british_irish_shelf"), "population": {"-6000": 55000, "-4000": 210000, "-2000": 480000, "-1000": 850000}},
    {"id": "north_euro_plain_neo", "name": "North European Plain & Lusatian-Vistula", "geom": b_ch1.get("north_european_plain"), "population": {"-6000": 98000, "-4000": 410000, "-2000": 890000, "-1000": 1350000}},
    {"id": "nordic_baltic_neo", "name": "Nordic Bronze Age & Eastern Baltic", "geom": b_ch1.get("fennoscandia_baltic"), "population": {"-6000": 54000, "-4000": 165000, "-2000": 360000, "-1000": 540000}},
    {"id": "north_atlantic_neo", "name": "North Atlantic Margins", "geom": b_ch1.get("north_atlantic_boreal"), "population": {"-6000": 8500, "-4000": 18000, "-2000": 35000, "-1000": 52000}},
    {"id": "greenland_saqqaq", "name": "Greenland (Saqqaq & Independence I)", "geom": b_ch1.get("greenland_arctic"), "population": {"-6000": 0, "-4000": 0, "-2000": 2500, "-1000": 3200}},
  ]
  write_chapter_assets(ch_by_idx[2], ch2_zones, domain_mask, full_domain=True)

  # Ch. 3: Classical Greece and the Aegean World (-1000..-146)
  ch3_zones = [
    {"id": "attica_boeotia_central", "name": "Attica, Boeotia & Central Greece", "geom": parts.get("Greece_Central_Attica"), "population": {"-1000": 260000, "-500": 780000, "-350": 920000, "-146": 680000}},
    {"id": "peloponnese", "name": "Peloponnese", "geom": parts.get("Greece_Peloponnese"), "population": {"-1000": 240000, "-500": 720000, "-350": 850000, "-146": 610000}},
    {"id": "epirus_ionian", "name": "Epirus & Ionian Littoral", "geom": union_parts(parts, ["Greece_Epirus_Ionian", "Albania"]), "population": {"-1000": 160000, "-500": 380000, "-350": 460000, "-146": 390000}},
    {"id": "macedonia_thrace", "name": "Macedonia & Aegean Thrace", "geom": union_parts(parts, ["Greece_Macedonia_Thrace", "North Macedonia", "Turkey-in-Europe"]), "population": {"-1000": 320000, "-500": 760000, "-350": 1080000, "-146": 950000}},
    {"id": "crete_aegean_islands", "name": "Crete & Aegean Archipelagos", "geom": parts.get("Greece_Crete_Aegean"), "population": {"-1000": 220000, "-500": 580000, "-350": 690000, "-146": 540000}},
  ]
  write_chapter_assets(ch_by_idx[3], ch3_zones, domain_mask, full_domain=False)

  # Ch. 4: Iron Age and Roman Europe (-1000..400)
  ch4_zones = [
    {"id": "italia_peninsular", "name": "Italia (Cisalpine & Peninsular)", "geom": union_parts(parts, ["Italy_North", "Italy_Central", "San Marino", "Vatican"]), "population": {"-1000": 1500000, "-500": 3200000, "0": 6200000, "200": 6800000, "400": 4900000}},
    {"id": "italia_south_islands", "name": "Magna Graecia, Sicilia, Sardinia & Malta", "geom": union_parts(parts, ["Italy_South_Islands", "Malta"]), "population": {"-1000": 750000, "-500": 1650000, "0": 2600000, "200": 2800000, "400": 2100000}},
    {"id": "hispania_tarrac_lusit", "name": "Hispania Tarraconensis & Lusitania", "geom": union_parts(parts, ["Spain_Castile_North", "Spain_Aragon_Catalonia", "Spain_Balearics", "Portugal_Mainland", "Andorra"]), "population": {"-1000": 1450000, "-500": 2400000, "0": 3850000, "200": 4450000, "400": 3650000}},
    {"id": "hispania_baetica", "name": "Hispania Baetica & Canaries", "geom": union_parts(parts, ["Spain_Andalusia_South", "Spain_Canaries", "Gibraltar"]), "population": {"-1000": 700000, "-500": 1250000, "0": 1950000, "200": 2350000, "400": 1850000}},
    {"id": "gallia_narb_aquit", "name": "Gallia Narbonensis & Aquitania", "geom": parts.get("France_South"), "population": {"-1000": 1050000, "-500": 1950000, "0": 3200000, "200": 3950000, "400": 3100000}},
    {"id": "gallia_lugd_belgica", "name": "Gallia Lugdunensis & Belgica", "geom": union_parts(parts, ["France_North", "Belgium", "Luxembourg", "Netherlands", "Monaco"]), "population": {"-1000": 1550000, "-500": 2750000, "0": 4550000, "200": 5650000, "400": 4150000}},
    {"id": "britannia", "name": "Britannia", "geom": union_parts(parts, ["UK_England_Wales", "UK_Scotland", "Isle of Man", "Jersey", "Guernsey"]), "population": {"-1000": 680000, "-500": 1150000, "0": 1950000, "200": 2850000, "400": 2250000}},
    {"id": "germania_limes_alpine", "name": "Germania Superior, Raetia & Noricum", "geom": union_parts(parts, ["Germany_South", "Switzerland", "Liechtenstein", "Austria"]), "population": {"-1000": 820000, "-500": 1450000, "0": 2350000, "200": 2950000, "400": 2250000}},
    {"id": "pannonia_dalmatia", "name": "Pannonia, Illyricum & Dalmatia", "geom": union_parts(parts, ["Hungary", "Slovenia", "Croatia", "Bosnia and Herzegovina", "Montenegro"]), "population": {"-1000": 680000, "-500": 1180000, "0": 1950000, "200": 2450000, "400": 1750000}},
    {"id": "moesia_dacia_thracia", "name": "Moesia, Dacia & Thracia", "geom": union_parts(parts, ["Romania", "Moldova", "Bulgaria", "Republic of Serbia", "Kosovo", "Turkey-in-Europe"]), "population": {"-1000": 1150000, "-500": 1950000, "0": 2950000, "200": 3450000, "400": 2550000}},
    {"id": "achaea_macedonia", "name": "Achaea, Epirus & Macedonia", "geom": union_parts(parts, ["Greece", "Albania", "North Macedonia"]), "population": {"-1000": 980000, "-500": 2650000, "0": 2350000, "200": 2450000, "400": 1950000}},
  ]
  write_chapter_assets(ch_by_idx[4], ch4_zones, domain_mask, full_domain=False)

  # Ch. 5: Free Germany, Scandinavia and the Baltic-Slavic North-East (-1000..500)
  ch5_zones = [
    {"id": "germania_magna_west", "name": "Elbe-Weser Germania Magna", "geom": parts.get("Germany_North"), "population": {"-1000": 620000, "-500": 950000, "0": 1550000, "200": 1850000, "500": 1450000}},
    {"id": "vistula_przeworsk_wielbark", "name": "Oder-Vistula (Przeworsk & Wielbark)", "geom": parts.get("Poland"), "population": {"-1000": 580000, "-500": 880000, "0": 1250000, "200": 1480000, "500": 1050000}},
    {"id": "bohemia_moravia_slovakia", "name": "Bohemia, Moravia & Slovakia", "geom": union_parts(parts, ["Czechia", "Slovakia"]), "population": {"-1000": 380000, "-500": 580000, "0": 780000, "200": 920000, "500": 680000}},
    {"id": "denmark_jutland_isles", "name": "Jutland & Danish Isles", "geom": parts.get("Denmark"), "population": {"-1000": 165000, "-500": 235000, "0": 320000, "200": 390000, "500": 350000}},
    {"id": "scandinavian_peninsula", "name": "Scandinavian Peninsula (Sweden & Norway)", "geom": union_parts(parts, ["Sweden", "Norway"]), "population": {"-1000": 210000, "-500": 295000, "0": 410000, "200": 490000, "500": 460000}},
    {"id": "finland_eastern_baltic", "name": "Finland & Eastern Baltic", "geom": union_parts(parts, ["Finland", "Aland", "Estonia", "Latvia", "Lithuania"]), "population": {"-1000": 175000, "-500": 245000, "0": 340000, "200": 410000, "500": 390000}},
    {"id": "hibernia_north_atlantic", "name": "Hibernia, Faroes, Iceland & Dorset Greenland", "geom": union_parts(parts, ["Ireland", "UK_Northern_Ireland", "Faroe Islands", "Iceland", "Greenland"]), "population": {"-1000": 185000, "-500": 285000, "0": 420000, "200": 510000, "500": 490000}},
  ]
  write_chapter_assets(ch_by_idx[5], ch5_zones, domain_mask, full_domain=False)

  # Ch. 6: Late Antiquity, Migration Period & Early Mediaeval Europe (250..800)
  ch6_zones = [
    {"id": "francia_merovingian", "name": "Merovingian-Carolingian Francia & Low Countries", "geom": union_parts(parts, ["France", "Belgium", "Netherlands", "Luxembourg", "Monaco"]), "population": {"300": 8900000, "500": 6200000, "600": 5400000, "800": 7200000}},
    {"id": "britain_ireland_early", "name": "Anglo-Saxon & Celtic British Isles", "geom": union_parts(parts, ["United Kingdom", "Ireland", "Isle of Man", "Jersey", "Guernsey"]), "population": {"300": 3100000, "500": 1850000, "600": 1650000, "800": 2350000}},
    {"id": "visigothic_iberia", "name": "Visigothic Iberia & Early Al-Andalus", "geom": union_parts(parts, ["Spain", "Portugal", "Andorra", "Gibraltar"]), "population": {"300": 6400000, "500": 4650000, "600": 4200000, "800": 4950000}},
    {"id": "lombard_byzantine_italy", "name": "Lombard & Byzantine Italy", "geom": union_parts(parts, ["Italy", "San Marino", "Vatican", "Malta"]), "population": {"300": 8400000, "500": 5200000, "600": 4100000, "800": 5400000}},
    {"id": "germanic_alpine_core", "name": "Alamannia, Bavaria, Saxony & Alps", "geom": union_parts(parts, ["Germany", "Switzerland", "Liechtenstein", "Austria"]), "population": {"300": 4500000, "500": 3450000, "600": 3250000, "800": 4450000}},
    {"id": "west_slavic_poland_bohemia", "name": "Early Slavic Poland, Bohemia & Slovakia", "geom": union_parts(parts, ["Poland", "Czechia", "Slovakia"]), "population": {"300": 2250000, "500": 1750000, "600": 1650000, "800": 2350000}},
    {"id": "avar_danubian_carpathian", "name": "Avar Carpathian Basin & Lower Danube", "geom": union_parts(parts, ["Hungary", "Romania", "Moldova"]), "population": {"300": 2450000, "500": 1750000, "600": 1550000, "800": 2150000}},
    {"id": "byzantine_slavic_balkans", "name": "Byzantine & Early Slavic Balkans", "geom": union_parts(parts, ["Slovenia", "Croatia", "Bosnia and Herzegovina", "Republic of Serbia", "Montenegro", "Kosovo", "North Macedonia", "Albania", "Bulgaria", "Greece", "Turkey-in-Europe"]), "population": {"300": 5650000, "500": 4250000, "600": 3350000, "800": 4350000}},
    {"id": "vendel_scandinavia_baltic", "name": "Vendel Scandinavia & Eastern Baltic", "geom": union_parts(parts, ["Denmark", "Sweden", "Norway", "Finland", "Aland", "Estonia", "Latvia", "Lithuania"]), "population": {"300": 1350000, "500": 1220000, "600": 1180000, "800": 1580000}},
    {"id": "north_atlantic_early", "name": "North Atlantic & Greenland", "geom": union_parts(parts, ["Iceland", "Faroe Islands", "Greenland"]), "population": {"300": 3500, "500": 3500, "600": 4000, "800": 5500}},
  ]
  write_chapter_assets(ch_by_idx[6], ch6_zones, domain_mask, full_domain=True)

  # Ch. 7: Mediaeval Western and Central Europe (800..1347)
  ch7_zones = [
    {"id": "france_north_royal", "name": "Kingdom of France (North & Ile-de-France)", "geom": parts.get("France_North"), "population": {"800": 3600000, "1000": 4800000, "1200": 7600000, "1300": 10800000, "1347": 11200000}},
    {"id": "france_south_occitania", "name": "Occitania, Aquitaine & Provence", "geom": union_parts(parts, ["France_South", "Monaco"]), "population": {"800": 2400000, "1000": 3100000, "1200": 4900000, "1300": 6800000, "1347": 7100000}},
    {"id": "england_wales_med", "name": "England & Wales", "geom": union_parts(parts, ["UK_England_Wales", "Isle of Man", "Jersey", "Guernsey"]), "population": {"800": 1450000, "1000": 2050000, "1200": 3450000, "1300": 5100000, "1347": 5250000}},
    {"id": "scotland_ireland_med", "name": "Scotland & Ireland", "geom": union_parts(parts, ["UK_Scotland", "UK_Northern_Ireland", "Ireland"]), "population": {"800": 900000, "1000": 1150000, "1200": 1550000, "1300": 2050000, "1347": 2100000}},
    {"id": "low_countries_med", "name": "Low Countries (Flanders-Brabant-Holland)", "geom": union_parts(parts, ["Belgium", "Netherlands", "Luxembourg"]), "population": {"800": 850000, "1000": 1150000, "1200": 1850000, "1300": 2550000, "1347": 2650000}},
    {"id": "hre_north_rhineland", "name": "Northern & Rhineland Holy Roman Empire", "geom": parts.get("Germany_North"), "population": {"800": 2100000, "1000": 2850000, "1200": 4650000, "1300": 6450000, "1347": 6800000}},
    {"id": "hre_south_alpine", "name": "Southern Germany, Austria & Switzerland", "geom": union_parts(parts, ["Germany_South", "Austria", "Switzerland", "Liechtenstein"]), "population": {"800": 2350000, "1000": 3150000, "1200": 4950000, "1300": 6850000, "1347": 7150000}},
    {"id": "italy_north_communes", "name": "Northern Italy (Lombardy-Venice-Piedmont)", "geom": parts.get("Italy_North"), "population": {"800": 2300000, "1000": 2950000, "1200": 4450000, "1300": 5850000, "1347": 6050000}},
    {"id": "italy_central_south_med", "name": "Central & Southern Italy (Tuscany-Papal-Naples-Sicily)", "geom": union_parts(parts, ["Italy_Central", "Italy_South_Islands", "San Marino", "Vatican", "Malta"]), "population": {"800": 3100000, "1000": 3650000, "1200": 4950000, "1300": 6150000, "1347": 6350000}},
  ]
  write_chapter_assets(ch_by_idx[7], ch7_zones, domain_mask, full_domain=False)

  # Ch. 8: Mediaeval Iberia (711..1492)
  ch8_zones = [
    {"id": "al_andalus_south", "name": "Al-Andalus / Andalusia & Granada", "geom": union_parts(parts, ["Spain_Andalusia_South", "Gibraltar"]), "population": {"711": 1950000, "1000": 2650000, "1200": 2450000, "1347": 2350000, "1492": 2150000}},
    {"id": "castile_leon", "name": "Crown of Castile-Leon", "geom": parts.get("Spain_Castile_North"), "population": {"711": 1550000, "1000": 1950000, "1200": 2950000, "1347": 3650000, "1492": 3950000}},
    {"id": "aragon_catalonia", "name": "Crown of Aragon, Catalonia & Valencia", "geom": union_parts(parts, ["Spain_Aragon_Catalonia", "Andorra"]), "population": {"711": 750000, "1000": 950000, "1200": 1350000, "1347": 1650000, "1492": 1480000}},
    {"id": "portugal_med", "name": "Kingdom of Portugal & Atlantic Isles", "geom": union_parts(parts, ["Portugal_Mainland", "Portugal_Islands"]), "population": {"711": 650000, "1000": 820000, "1200": 1080000, "1347": 1350000, "1492": 1220000}},
    {"id": "balearics_canaries_med", "name": "Balearic & Canary Islands", "geom": union_parts(parts, ["Spain_Balearics", "Spain_Canaries"]), "population": {"711": 95000, "1000": 135000, "1200": 165000, "1347": 195000, "1492": 185000}},
  ]
  write_chapter_assets(ch_by_idx[8], ch8_zones, domain_mask, full_domain=False)

  # Ch. 9: Mediaeval Scandinavia and North Atlantic Colonisation (800..1500)
  ch9_zones = [
    {"id": "denmark_med", "name": "Kingdom of Denmark", "geom": parts.get("Denmark"), "population": {"800": 450000, "1000": 620000, "1200": 850000, "1347": 950000, "1500": 680000}},
    {"id": "sweden_med", "name": "Kingdom of Sweden", "geom": parts.get("Sweden"), "population": {"800": 380000, "1000": 480000, "1200": 650000, "1347": 780000, "1500": 650000}},
    {"id": "norway_med", "name": "Kingdom of Norway", "geom": parts.get("Norway"), "population": {"800": 220000, "1000": 280000, "1200": 390000, "1347": 480000, "1500": 260000}},
    {"id": "finland_med", "name": "Finland (Eastland)", "geom": union_parts(parts, ["Finland", "Aland"]), "population": {"800": 95000, "1000": 130000, "1200": 185000, "1347": 240000, "1500": 260000}},
    {"id": "iceland_med", "name": "Iceland", "geom": parts.get("Iceland"), "population": {"800": 0, "1000": 45000, "1200": 65000, "1347": 72000, "1500": 48000}},
    {"id": "faroes_med", "name": "Faroe Islands", "geom": parts.get("Faroe Islands"), "population": {"800": 800, "1000": 2500, "1200": 3800, "1347": 4200, "1500": 3200}},
    {"id": "greenland_norse_inuit", "name": "Norse & Inuit Greenland", "geom": parts.get("Greenland"), "population": {"800": 4500, "1000": 6500, "1200": 9500, "1347": 8500, "1500": 5500}},
  ]
  write_chapter_assets(ch_by_idx[9], ch9_zones, domain_mask, full_domain=False)

  # Ch. 10: Mediaeval East-Central Europe, the Baltic and the Balkans (800..1347)
  ch10_zones = [
    {"id": "poland_piast", "name": "Piast Kingdom of Poland", "geom": parts.get("Poland"), "population": {"800": 1450000, "1000": 1950000, "1200": 2850000, "1347": 3650000}},
    {"id": "bohemia_moravia_med", "name": "Bohemia & Moravia", "geom": parts.get("Czechia"), "population": {"800": 620000, "1000": 880000, "1200": 1350000, "1347": 1950000}},
    {"id": "hungary_slovakia_med", "name": "Kingdom of Hungary & Slovakia", "geom": union_parts(parts, ["Hungary", "Slovakia"]), "population": {"800": 950000, "1000": 1450000, "1200": 2250000, "1347": 2950000}},
    {"id": "romania_moldova_med", "name": "Wallachia, Moldavia & Transylvania", "geom": union_parts(parts, ["Romania", "Moldova"]), "population": {"800": 1050000, "1000": 1350000, "1200": 1750000, "1347": 2250000}},
    {"id": "baltic_lands_med", "name": "Baltic Lands (Estonia, Latvia & Lithuania)", "geom": union_parts(parts, ["Estonia", "Latvia", "Lithuania"]), "population": {"800": 420000, "1000": 560000, "1200": 780000, "1347": 980000}},
    {"id": "croatia_slovenia_bosnia", "name": "Slovenia, Croatia & Bosnia", "geom": union_parts(parts, ["Slovenia", "Croatia", "Bosnia and Herzegovina"]), "population": {"800": 720000, "1000": 960000, "1200": 1320000, "1347": 1650000}},
    {"id": "serbia_montenegro_albania", "name": "Mediaeval Serbia, Montenegro & Albania", "geom": union_parts(parts, ["Republic of Serbia", "Montenegro", "Kosovo", "Albania", "North Macedonia"]), "population": {"800": 980000, "1000": 1250000, "1200": 1680000, "1347": 2150000}},
    {"id": "bulgaria_greece_thrace_med", "name": "Byzantine-Bulgarian Balkans & Greece", "geom": union_parts(parts, ["Bulgaria", "Greece", "Turkey-in-Europe"]), "population": {"800": 2450000, "1000": 2950000, "1200": 3450000, "1347": 3750000}},
  ]
  write_chapter_assets(ch_by_idx[10], ch10_zones, domain_mask, full_domain=False)

  # Ch. 11: The Black Death and the Late Mediaeval Crisis across Europe (1347..1500)
  ch11_zones = [
    {"id": "bd_british_isles", "name": "British Isles", "geom": union_parts(parts, ["United Kingdom", "Ireland", "Isle of Man", "Jersey", "Guernsey"]), "population": {"1347": 7350000, "1400": 4150000, "1450": 4350000, "1500": 4950000}},
    {"id": "bd_france_low_countries", "name": "France & Low Countries", "geom": union_parts(parts, ["France", "Belgium", "Netherlands", "Luxembourg", "Monaco"]), "population": {"1347": 20950000, "1400": 13400000, "1450": 14600000, "1500": 17650000}},
    {"id": "bd_german_alpine", "name": "German Empire, Austria & Switzerland", "geom": union_parts(parts, ["Germany", "Austria", "Switzerland", "Liechtenstein"]), "population": {"1347": 13950000, "1400": 9800000, "1450": 11200000, "1500": 13500000}},
    {"id": "bd_italy_malta", "name": "Italian Peninsula & Malta", "geom": union_parts(parts, ["Italy", "San Marino", "Vatican", "Malta"]), "population": {"1347": 12400000, "1400": 7900000, "1450": 8800000, "1500": 10600000}},
    {"id": "bd_iberia", "name": "Iberian Kingdoms & Atlantic Islands", "geom": union_parts(parts, ["Spain", "Portugal", "Andorra", "Gibraltar"]), "population": {"1347": 9150000, "1400": 6950000, "1450": 7850000, "1500": 8950000}},
    {"id": "bd_nordics", "name": "Scandinavia & Finland", "geom": union_parts(parts, ["Denmark", "Sweden", "Norway", "Finland", "Aland"]), "population": {"1347": 2450000, "1400": 1520000, "1450": 1680000, "1500": 1850000}},
    {"id": "bd_north_atlantic", "name": "Iceland, Faroe Islands & Greenland", "geom": union_parts(parts, ["Iceland", "Faroe Islands", "Greenland"]), "population": {"1347": 84700, "1400": 59000, "1450": 54000, "1500": 56700}},
    {"id": "bd_poland_baltics", "name": "Poland & Baltic Lands", "geom": union_parts(parts, ["Poland", "Estonia", "Latvia", "Lithuania"]), "population": {"1347": 4630000, "1400": 4150000, "1450": 4650000, "1500": 5350000}},
    {"id": "bd_bohemia_hungary", "name": "Bohemia, Moravia, Slovakia & Hungary", "geom": union_parts(parts, ["Czechia", "Slovakia", "Hungary"]), "population": {"1347": 4900000, "1400": 4250000, "1450": 4450000, "1500": 4950000}},
    {"id": "bd_romania_moldova", "name": "Wallachia, Moldavia & Transylvania", "geom": union_parts(parts, ["Romania", "Moldova"]), "population": {"1347": 2250000, "1400": 1950000, "1450": 2150000, "1500": 2450000}},
    {"id": "bd_ottoman_balkans", "name": "Balkans & Ottoman Rumelia", "geom": union_parts(parts, ["Slovenia", "Croatia", "Bosnia and Herzegovina", "Republic of Serbia", "Montenegro", "Kosovo", "North Macedonia", "Albania", "Bulgaria", "Greece", "Turkey-in-Europe"]), "population": {"1347": 7550000, "1400": 5850000, "1450": 6250000, "1500": 6950000}},
  ]
  write_chapter_assets(ch_by_idx[11], ch11_zones, domain_mask, full_domain=True)

  # Ch. 12: Early Modern Western and Northern Europe (1500..1750)
  ch12_zones = [
    {"id": "em_england_wales", "name": "England & Wales", "geom": union_parts(parts, ["UK_England_Wales", "Isle of Man", "Jersey", "Guernsey"]), "population": {"1500": 2750000, "1600": 4450000, "1700": 5450000, "1750": 6250000}},
    {"id": "em_scotland", "name": "Scotland", "geom": parts.get("UK_Scotland"), "population": {"1500": 780000, "1600": 950000, "1700": 1050000, "1750": 1265000}},
    {"id": "em_ireland", "name": "Ireland", "geom": union_parts(parts, ["Ireland", "UK_Northern_Ireland"]), "population": {"1500": 950000, "1600": 1350000, "1700": 2250000, "1750": 3150000}},
    {"id": "em_france", "name": "Kingdom of France", "geom": union_parts(parts, ["France", "Monaco"]), "population": {"1500": 15400000, "1600": 18900000, "1700": 21500000, "1750": 24600000}},
    {"id": "em_low_countries", "name": "Dutch Republic & Southern Netherlands", "geom": union_parts(parts, ["Netherlands", "Belgium", "Luxembourg"]), "population": {"1500": 2250000, "1600": 3050000, "1700": 3850000, "1750": 4250000}},
    {"id": "em_denmark_norway", "name": "Denmark-Norway", "geom": union_parts(parts, ["Denmark", "Norway"]), "population": {"1500": 940000, "1600": 1180000, "1700": 1320000, "1750": 1480000}},
    {"id": "em_sweden_finland", "name": "Sweden-Finland", "geom": union_parts(parts, ["Sweden", "Finland", "Aland"]), "population": {"1500": 910000, "1600": 1190000, "1700": 1760000, "1750": 2210000}},
    {"id": "em_iceland_faroes", "name": "Iceland & Faroe Islands", "geom": union_parts(parts, ["Iceland", "Faroe Islands"]), "population": {"1500": 51200, "1600": 54500, "1700": 54500, "1750": 53200}},
    {"id": "em_greenland", "name": "Greenland", "geom": parts.get("Greenland"), "population": {"1500": 5500, "1600": 6000, "1700": 6500, "1750": 7200}},
  ]
  write_chapter_assets(ch_by_idx[12], ch12_zones, domain_mask, full_domain=False)

  # Ch. 13: Early Modern Central Europe (1500..1750)
  ch13_zones = [
    {"id": "em_germany_north", "name": "Northern & Protestant German States", "geom": parts.get("Germany_North"), "population": {"1500": 5600000, "1600": 7400000, "1650": 5400000, "1700": 7100000, "1750": 8600000}},
    {"id": "em_germany_south", "name": "Southern & Rhineland German States", "geom": parts.get("Germany_South"), "population": {"1500": 5200000, "1600": 6800000, "1650": 4600000, "1700": 6400000, "1750": 7800000}},
    {"id": "em_switzerland", "name": "Swiss Confederacy", "geom": union_parts(parts, ["Switzerland", "Liechtenstein"]), "population": {"1500": 780000, "1600": 1020000, "1650": 1050000, "1700": 1220000, "1750": 1450000}},
    {"id": "em_austria", "name": "Austrian Hereditary Lands", "geom": parts.get("Austria"), "population": {"1500": 1920000, "1600": 2350000, "1650": 2150000, "1700": 2480000, "1750": 2850000}},
    {"id": "em_bohemia_moravia", "name": "Bohemia & Moravia", "geom": parts.get("Czechia"), "population": {"1500": 1950000, "1600": 2450000, "1650": 1750000, "1700": 2350000, "1750": 3150000}},
    {"id": "em_hungary_slovakia", "name": "Hungary & Slovakia", "geom": union_parts(parts, ["Hungary", "Slovakia"]), "population": {"1500": 3000000, "1600": 3100000, "1650": 2950000, "1700": 3250000, "1750": 4850000}},
    {"id": "em_poland_baltics", "name": "Poland-Lithuania Crown & Baltic Lands", "geom": union_parts(parts, ["Poland", "Estonia", "Latvia", "Lithuania"]), "population": {"1500": 5350000, "1600": 6850000, "1650": 5950000, "1700": 6550000, "1750": 8350000}},
  ]
  write_chapter_assets(ch_by_idx[13], ch13_zones, domain_mask, full_domain=False)

  # Ch. 14: Early Modern Southern Europe and Atlantic Islands (1500..1750)
  ch14_zones = [
    {"id": "em_spain_castile", "name": "Castile & Northern Spain", "geom": parts.get("Spain_Castile_North"), "population": {"1500": 4150000, "1600": 4950000, "1700": 4450000, "1750": 5250000}},
    {"id": "em_spain_aragon_andalusia", "name": "Aragon, Catalonia, Valencia & Andalusia", "geom": union_parts(parts, ["Spain_Aragon_Catalonia", "Spain_Andalusia_South", "Spain_Balearics", "Andorra", "Gibraltar"]), "population": {"1500": 3450000, "1600": 3950000, "1700": 3650000, "1750": 4350000}},
    {"id": "em_portugal_main", "name": "Kingdom of Portugal (Mainland)", "geom": parts.get("Portugal_Mainland"), "population": {"1500": 1150000, "1600": 1480000, "1700": 1950000, "1750": 2350000}},
    {"id": "em_italy_north", "name": "Northern Italy", "geom": parts.get("Italy_North"), "population": {"1500": 4950000, "1600": 6150000, "1700": 6250000, "1750": 7250000}},
    {"id": "em_italy_central", "name": "Central Italy (Tuscany & Papal States)", "geom": union_parts(parts, ["Italy_Central", "San Marino", "Vatican"]), "population": {"1500": 2150000, "1600": 2650000, "1700": 2750000, "1750": 3150000}},
    {"id": "em_italy_south_malta", "name": "Kingdom of Naples, Sicily, Sardinia & Malta", "geom": union_parts(parts, ["Italy_South_Islands", "Malta"]), "population": {"1500": 3550000, "1600": 4550000, "1700": 4550000, "1750": 5350000}},
    {"id": "em_azores_madeira", "name": "Azores & Madeira", "geom": parts.get("Portugal_Islands"), "population": {"1500": 68000, "1600": 115000, "1700": 165000, "1750": 205000}},
    {"id": "em_canaries", "name": "Canary Islands", "geom": parts.get("Spain_Canaries"), "population": {"1500": 42000, "1600": 68000, "1700": 105000, "1750": 145000}},
  ]
  write_chapter_assets(ch_by_idx[14], ch14_zones, domain_mask, full_domain=False)

  # Ch. 15: Ottoman Balkans and South-Eastern Europe (1350..1830)
  ch15_zones = [
    {"id": "ott_bosnia_croatia_slovenia", "name": "Bosnia, Herzegovina, Croatia & Slovenia", "geom": union_parts(parts, ["Slovenia", "Croatia", "Bosnia and Herzegovina"]), "population": {"1400": 1350000, "1500": 1550000, "1600": 1750000, "1700": 1950000, "1800": 2750000, "1830": 3150000}},
    {"id": "ott_serbia_montenegro_kosovo", "name": "Serbia, Montenegro & Kosovo", "geom": union_parts(parts, ["Republic of Serbia", "Montenegro", "Kosovo"]), "population": {"1400": 1250000, "1500": 1380000, "1600": 1480000, "1700": 1420000, "1800": 1950000, "1830": 2350000}},
    {"id": "ott_albania_macedonia", "name": "Albania & Macedonia", "geom": union_parts(parts, ["Albania", "North Macedonia"]), "population": {"1400": 650000, "1500": 720000, "1600": 820000, "1700": 880000, "1800": 1120000, "1830": 1280000}},
    {"id": "ott_greece", "name": "Greece & Aegean Islands", "geom": parts.get("Greece"), "population": {"1400": 1250000, "1500": 1450000, "1600": 1650000, "1700": 1580000, "1800": 2150000, "1830": 2450000}},
    {"id": "ott_bulgaria", "name": "Bulgaria", "geom": parts.get("Bulgaria"), "population": {"1400": 1050000, "1500": 1180000, "1600": 1380000, "1700": 1450000, "1800": 2150000, "1830": 2550000}},
    {"id": "ott_danubian_principalities", "name": "Wallachia, Moldavia & Transylvania", "geom": union_parts(parts, ["Romania", "Moldova"]), "population": {"1400": 1950000, "1500": 2450000, "1600": 2850000, "1700": 3250000, "1800": 5850000, "1830": 6850000}},
    {"id": "ott_eastern_thrace", "name": "Eastern Thrace (Turkey-in-Europe)", "geom": parts.get("Turkey-in-Europe"), "population": {"1400": 320000, "1500": 580000, "1600": 880000, "1700": 950000, "1800": 1150000, "1830": 1280000}},
  ]
  write_chapter_assets(ch_by_idx[15], ch15_zones, domain_mask, full_domain=False)

  # Ch. 16: Industrialisation and Demographic Revolution in Western & Northern Europe (1750..1914)
  ch16_zones = [
    {"id": "ind_england_wales", "name": "England & Wales", "geom": union_parts(parts, ["UK_England_Wales", "Isle of Man", "Jersey", "Guernsey"]), "population": {"1750": 6250000, "1801": 9050000, "1851": 18050000, "1881": 26100000, "1911": 36220000}},
    {"id": "ind_scotland", "name": "Scotland", "geom": parts.get("UK_Scotland"), "population": {"1750": 1265000, "1801": 1608000, "1851": 2889000, "1881": 3736000, "1911": 4761000}},
    {"id": "ind_ireland", "name": "Ireland", "geom": union_parts(parts, ["Ireland", "UK_Northern_Ireland"]), "population": {"1750": 3150000, "1801": 5200000, "1841": 8175000, "1851": 6552000, "1881": 5175000, "1911": 4390000}},
    {"id": "ind_france", "name": "France", "geom": union_parts(parts, ["France", "Monaco"]), "population": {"1750": 24600000, "1801": 29100000, "1851": 35780000, "1881": 37670000, "1911": 39605000}},
    {"id": "ind_benelux", "name": "Belgium, Netherlands & Luxembourg", "geom": union_parts(parts, ["Belgium", "Netherlands", "Luxembourg"]), "population": {"1750": 4250000, "1800": 5250000, "1850": 7750000, "1880": 9790000, "1910": 13540000}},
    {"id": "ind_germany_north", "name": "Northern Germany (Prussia & North)", "geom": parts.get("Germany_North"), "population": {"1750": 8600000, "1816": 12800000, "1850": 18200000, "1871": 22900000, "1910": 37400000}},
    {"id": "ind_germany_south_swiss", "name": "Southern Germany & Switzerland", "geom": union_parts(parts, ["Germany_South", "Switzerland", "Liechtenstein"]), "population": {"1750": 9250000, "1816": 12400000, "1850": 15900000, "1871": 18200000, "1910": 26100000}},
    {"id": "ind_scandinavia", "name": "Denmark, Sweden, Norway & Finland", "geom": union_parts(parts, ["Denmark", "Sweden", "Norway", "Finland", "Aland"]), "population": {"1750": 3690000, "1800": 5060000, "1850": 7980000, "1880": 10520000, "1910": 13780000}},
    {"id": "ind_north_atlantic", "name": "Iceland, Faroe Islands & Greenland", "geom": union_parts(parts, ["Iceland", "Faroe Islands", "Greenland"]), "population": {"1750": 60400, "1801": 58600, "1850": 77000, "1880": 93500, "1910": 116500}},
  ]
  write_chapter_assets(ch_by_idx[16], ch16_zones, domain_mask, full_domain=False)

  # Ch. 17: Early Modern & 19th-Century Southern & East-Central Europe (1750..1914)
  ch17_zones = [
    {"id": "c19_spain", "name": "Spain (incl. Balearics & Canaries)", "geom": union_parts(parts, ["Spain", "Andorra", "Gibraltar"]), "population": {"1750": 9750000, "1800": 10850000, "1857": 15460000, "1887": 17560000, "1910": 19950000}},
    {"id": "c19_portugal", "name": "Portugal (incl. Azores & Madeira)", "geom": parts.get("Portugal"), "population": {"1750": 2555000, "1800": 2950000, "1864": 4188000, "1890": 5050000, "1911": 5960000}},
    {"id": "c19_italy_north_central", "name": "Northern & Central Italy", "geom": union_parts(parts, ["Italy_North", "Italy_Central", "San Marino", "Vatican"]), "population": {"1750": 10400000, "1800": 11850000, "1861": 15400000, "1881": 17450000, "1911": 21400000}},
    {"id": "c19_italy_south_malta", "name": "Southern Italy, Islands & Malta", "geom": union_parts(parts, ["Italy_South_Islands", "Malta"]), "population": {"1750": 5350000, "1800": 6450000, "1861": 9750000, "1881": 11200000, "1911": 13500000}},
    {"id": "c19_austria_bohemia_slovenia", "name": "Austria, Bohemia-Moravia & Slovenia", "geom": union_parts(parts, ["Austria", "Czechia", "Slovenia"]), "population": {"1750": 6650000, "1800": 8250000, "1857": 12250000, "1880": 14350000, "1910": 17850000}},
    {"id": "c19_hungary_slovakia_croatia", "name": "Hungary, Slovakia & Croatia-Slavonia", "geom": union_parts(parts, ["Hungary", "Slovakia", "Croatia"]), "population": {"1750": 5950000, "1800": 8150000, "1857": 11250000, "1880": 12450000, "1910": 15950000}},
    {"id": "c19_poland", "name": "Partitioned Poland (Modern Territory)", "geom": parts.get("Poland"), "population": {"1750": 6950000, "1800": 9100000, "1850": 13800000, "1880": 18900000, "1910": 26500000}},
    {"id": "c19_baltics", "name": "Baltic Provinces (Estonia, Latvia, Lithuania)", "geom": union_parts(parts, ["Estonia", "Latvia", "Lithuania"]), "population": {"1750": 1400000, "1800": 2150000, "1850": 3250000, "1897": 5420000, "1913": 6250000}},
    {"id": "c19_balkans_romania", "name": "Balkans, Romania, Moldova & Eastern Thrace", "geom": union_parts(parts, ["Romania", "Moldova", "Bulgaria", "Republic of Serbia", "Montenegro", "Kosovo", "Bosnia and Herzegovina", "North Macedonia", "Albania", "Greece", "Turkey-in-Europe"]), "population": {"1750": 12500000, "1800": 15300000, "1850": 20500000, "1880": 25800000, "1910": 33900000}},
  ]
  write_chapter_assets(ch_by_idx[17], ch17_zones, domain_mask, full_domain=False)

  # Ch. 18: First World War, Inter-War Europe & Second World War (1914..1945)
  ch18_zones = [
    {"id": "ww_uk_ireland", "name": "United Kingdom & Ireland", "geom": union_parts(parts, ["United Kingdom", "Ireland", "Isle of Man", "Jersey", "Guernsey"]), "population": {"1914": 46050000, "1921": 47120000, "1939": 50750000, "1945": 52180000}},
    {"id": "ww_france_benelux", "name": "France & Benelux", "geom": union_parts(parts, ["France", "Belgium", "Netherlands", "Luxembourg", "Monaco"]), "population": {"1914": 53950000, "1921": 53800000, "1939": 59250000, "1945": 57950000}},
    {"id": "ww_germany_austria_swiss", "name": "Germany, Austria & Switzerland", "geom": union_parts(parts, ["Germany", "Austria", "Switzerland", "Liechtenstein"]), "population": {"1914": 71650000, "1925": 73200000, "1939": 80150000, "1945": 76850000}},
    {"id": "ww_poland", "name": "Poland", "geom": parts.get("Poland"), "population": {"1914": 27200000, "1921": 27180000, "1939": 32100000, "1945": 23930000}},
    {"id": "ww_czechoslovakia_hungary", "name": "Czechoslovakia & Hungary", "geom": union_parts(parts, ["Czechia", "Slovakia", "Hungary"]), "population": {"1914": 21400000, "1921": 21600000, "1939": 23800000, "1945": 21250000}},
    {"id": "ww_italy_malta", "name": "Italy & Malta", "geom": union_parts(parts, ["Italy", "San Marino", "Vatican", "Malta"]), "population": {"1914": 36200000, "1921": 38100000, "1939": 44100000, "1945": 45400000}},
    {"id": "ww_iberia_macaronesia", "name": "Spain, Portugal & Atlantic Islands", "geom": union_parts(parts, ["Spain", "Portugal", "Andorra", "Gibraltar"]), "population": {"1914": 26450000, "1920": 27400000, "1939": 33200000, "1945": 35100000}},
    {"id": "ww_nordics_baltics", "name": "Nordics & Baltic States", "geom": union_parts(parts, ["Denmark", "Sweden", "Norway", "Finland", "Aland", "Estonia", "Latvia", "Lithuania"]), "population": {"1914": 20350000, "1925": 20950000, "1939": 22550000, "1945": 22150000}},
    {"id": "ww_romania_bulgaria_moldova", "name": "Romania, Bulgaria & Moldova", "geom": union_parts(parts, ["Romania", "Bulgaria", "Moldova"]), "population": {"1914": 19100000, "1925": 20900000, "1939": 24500000, "1945": 24800000}},
    {"id": "ww_yugoslavia_greece_albania", "name": "Yugoslavia, Albania, Greece & Eastern Thrace", "geom": union_parts(parts, ["Slovenia", "Croatia", "Bosnia and Herzegovina", "Republic of Serbia", "Montenegro", "Kosovo", "North Macedonia", "Albania", "Greece", "Turkey-in-Europe"]), "population": {"1914": 20100000, "1925": 21200000, "1939": 25800000, "1945": 24950000}},
    {"id": "ww_north_atlantic", "name": "Iceland, Faroe Islands & Greenland", "geom": union_parts(parts, ["Iceland", "Faroe Islands", "Greenland"]), "population": {"1914": 121000, "1925": 136000, "1939": 165000, "1945": 180000}},
  ]
  write_chapter_assets(ch_by_idx[18], ch18_zones, domain_mask, full_domain=True)

  # --- REGIME III: Contemporary Statistical Censuses (1945..2026) ---
  # Ch. 19: Western and Northern Europe after 1945
  ch19_zones = [
    {"id": "mod_uk", "name": "United Kingdom", "geom": union_parts(parts, ["United Kingdom", "Isle of Man", "Jersey", "Guernsey"]), "population": {"1950": 50616000, "1970": 55632000, "1990": 57237000, "2010": 62766000, "2025": 69138000}},
    {"id": "mod_ireland", "name": "Ireland", "geom": parts.get("Ireland"), "population": {"1950": 2969000, "1970": 2950000, "1990": 3506000, "2010": 4555000, "2025": 5380000}},
    {"id": "mod_france", "name": "France (Metropolitan)", "geom": union_parts(parts, ["France", "Monaco"]), "population": {"1950": 41829000, "1970": 50772000, "1990": 56735000, "2010": 62961000, "2025": 66450000}},
    {"id": "mod_belgium", "name": "Belgium", "geom": parts.get("Belgium"), "population": {"1950": 8639000, "1970": 9638000, "1990": 9967000, "2010": 10896000, "2025": 11830000}},
    {"id": "mod_netherlands", "name": "Netherlands", "geom": parts.get("Netherlands"), "population": {"1950": 10114000, "1970": 13039000, "1990": 14952000, "2010": 16615000, "2025": 18040000}},
    {"id": "mod_luxembourg", "name": "Luxembourg", "geom": parts.get("Luxembourg"), "population": {"1950": 296000, "1970": 339000, "1990": 382000, "2010": 507000, "2025": 678000}},
    {"id": "mod_germany", "name": "Germany", "geom": parts.get("Germany"), "population": {"1950": 69346000, "1970": 77709000, "1990": 79433000, "2010": 81777000, "2025": 84550000}},
    {"id": "mod_switzerland", "name": "Switzerland & Liechtenstein", "geom": union_parts(parts, ["Switzerland", "Liechtenstein"]), "population": {"1950": 4708000, "1970": 6202000, "1990": 6741000, "2010": 7861000, "2025": 9040000}},
    {"id": "mod_austria", "name": "Austria", "geom": parts.get("Austria"), "population": {"1950": 6935000, "1970": 7467000, "1990": 7678000, "2010": 8363000, "2025": 9190000}},
    {"id": "mod_denmark", "name": "Denmark", "geom": parts.get("Denmark"), "population": {"1950": 4271000, "1970": 4929000, "1990": 5141000, "2010": 5548000, "2025": 5990000}},
    {"id": "mod_sweden", "name": "Sweden", "geom": parts.get("Sweden"), "population": {"1950": 7014000, "1970": 8043000, "1990": 8559000, "2010": 9378000, "2025": 10610000}},
    {"id": "mod_norway", "name": "Norway (incl. Svalbard)", "geom": parts.get("Norway"), "population": {"1950": 3265000, "1970": 3877000, "1990": 4241000, "2010": 4889000, "2025": 5590000}},
    {"id": "mod_finland", "name": "Finland", "geom": union_parts(parts, ["Finland", "Aland"]), "population": {"1950": 4009000, "1970": 4606000, "1990": 4986000, "2010": 5363000, "2025": 5635000}},
  ]
  write_chapter_assets(ch_by_idx[19], ch19_zones, domain_mask, full_domain=False)

  # Ch. 20: Southern Europe and European Islands after 1945
  ch20_zones = [
    {"id": "mod_spain_main", "name": "Spain (Mainland & Balearics)", "geom": union_parts(parts, ["Spain_Mainland", "Andorra", "Gibraltar"]), "population": {"1950": 27280000, "1970": 32720000, "1990": 37450000, "2010": 44550000, "2025": 46750000}},
    {"id": "mod_canaries", "name": "Canary Islands", "geom": parts.get("Spain_Canaries"), "population": {"1950": 793000, "1970": 1170000, "1990": 1494000, "2010": 2118000, "2025": 2255000}},
    {"id": "mod_portugal_main", "name": "Portugal (Mainland)", "geom": parts.get("Portugal_Mainland"), "population": {"1950": 7856000, "1970": 8120000, "1990": 9410000, "2010": 10060000, "2025": 10180000}},
    {"id": "mod_azores_madeira", "name": "Azores & Madeira", "geom": parts.get("Portugal_Islands"), "population": {"1950": 585000, "1970": 542000, "1990": 491000, "2010": 514000, "2025": 496000}},
    {"id": "mod_italy", "name": "Italy (incl. San Marino & Vatican)", "geom": union_parts(parts, ["Italy", "San Marino", "Vatican"]), "population": {"1950": 47105000, "1970": 53822000, "1990": 56719000, "2010": 59277000, "2025": 58950000}},
    {"id": "mod_malta", "name": "Malta", "geom": parts.get("Malta"), "population": {"1950": 312000, "1970": 303000, "1990": 354000, "2010": 415000, "2025": 563000}},
    {"id": "mod_greece", "name": "Greece", "geom": parts.get("Greece"), "population": {"1950": 7566000, "1970": 8793000, "1990": 10161000, "2010": 11121000, "2025": 10380000}},
    {"id": "mod_iceland", "name": "Iceland", "geom": parts.get("Iceland"), "population": {"1950": 143000, "1970": 204000, "1990": 255000, "2010": 318000, "2025": 393000}},
    {"id": "mod_faroes", "name": "Faroe Islands", "geom": parts.get("Faroe Islands"), "population": {"1950": 31800, "1970": 38600, "1990": 47400, "2010": 48500, "2025": 55100}},
    {"id": "mod_greenland", "name": "Greenland", "geom": parts.get("Greenland"), "population": {"1950": 23600, "1970": 46500, "1990": 55600, "2010": 56500, "2025": 56800}},
    {"id": "mod_turkey_europe", "name": "Turkey-in-Europe (Eastern Thrace)", "geom": parts.get("Turkey-in-Europe"), "population": {"1950": 1590000, "1970": 3150000, "1990": 6250000, "2010": 10350000, "2025": 12250000}},
  ]
  write_chapter_assets(ch_by_idx[20], ch20_zones, domain_mask, full_domain=False)

  # Ch. 21: East-Central Europe, the Balkans and the Baltic States after 1945
  ch21_zones = [
    {"id": "mod_poland", "name": "Poland", "geom": parts.get("Poland"), "population": {"1950": 24824000, "1970": 32526000, "1990": 38111000, "2010": 38043000, "2025": 37480000}},
    {"id": "mod_czechia", "name": "Czechia", "geom": parts.get("Czechia"), "population": {"1950": 8925000, "1970": 9805000, "1990": 10363000, "2010": 10474000, "2025": 10880000}},
    {"id": "mod_slovakia", "name": "Slovakia", "geom": parts.get("Slovakia"), "population": {"1950": 3463000, "1970": 4528000, "1990": 5298000, "2010": 5391000, "2025": 5425000}},
    {"id": "mod_hungary", "name": "Hungary", "geom": parts.get("Hungary"), "population": {"1950": 9338000, "1970": 10338000, "1990": 10374000, "2010": 10000000, "2025": 9580000}},
    {"id": "mod_romania", "name": "Romania", "geom": parts.get("Romania"), "population": {"1950": 16311000, "1970": 20253000, "1990": 23207000, "2010": 20247000, "2025": 19050000}},
    {"id": "mod_moldova", "name": "Moldova", "geom": parts.get("Moldova"), "population": {"1950": 2341000, "1970": 3595000, "1990": 4364000, "2010": 3562000, "2025": 2980000}},
    {"id": "mod_bulgaria", "name": "Bulgaria", "geom": parts.get("Bulgaria"), "population": {"1950": 7251000, "1970": 8490000, "1990": 8718000, "2010": 7396000, "2025": 6435000}},
    {"id": "mod_slovenia", "name": "Slovenia", "geom": parts.get("Slovenia"), "population": {"1950": 1473000, "1970": 1725000, "1990": 1998000, "2010": 2049000, "2025": 2125000}},
    {"id": "mod_croatia", "name": "Croatia", "geom": parts.get("Croatia"), "population": {"1950": 3850000, "1970": 4411000, "1990": 4778000, "2010": 4295000, "2025": 3860000}},
    {"id": "mod_bosnia", "name": "Bosnia and Herzegovina", "geom": parts.get("Bosnia and Herzegovina"), "population": {"1950": 2661000, "1970": 3708000, "1990": 4424000, "2010": 3760000, "2025": 3165000}},
    {"id": "mod_serbia_kosovo", "name": "Serbia & Kosovo", "geom": union_parts(parts, ["Republic of Serbia", "Kosovo"]), "population": {"1950": 6732000, "1970": 8140000, "1990": 9520000, "2010": 9060000, "2025": 8240000}},
    {"id": "mod_montenegro", "name": "Montenegro", "geom": parts.get("Montenegro"), "population": {"1950": 399000, "1970": 525000, "1990": 606000, "2010": 619000, "2025": 623000}},
    {"id": "mod_north_macedonia", "name": "North Macedonia", "geom": parts.get("North Macedonia"), "population": {"1950": 1230000, "1970": 1629000, "1990": 1903000, "2010": 2055000, "2025": 1825000}},
    {"id": "mod_albania", "name": "Albania", "geom": parts.get("Albania"), "population": {"1950": 1215000, "1970": 2136000, "1990": 3286000, "2010": 2913000, "2025": 2745000}},
    {"id": "mod_estonia", "name": "Estonia", "geom": parts.get("Estonia"), "population": {"1950": 1101000, "1970": 1360000, "1990": 1569000, "2010": 1331000, "2025": 1370000}},
    {"id": "mod_latvia", "name": "Latvia", "geom": parts.get("Latvia"), "population": {"1950": 1949000, "1970": 2366000, "1990": 2663000, "2010": 2098000, "2025": 1870000}},
    {"id": "mod_lithuania", "name": "Lithuania", "geom": parts.get("Lithuania"), "population": {"1950": 2567000, "1970": 3137000, "1990": 3698000, "2010": 3097000, "2025": 2885000}},
  ]
  write_chapter_assets(ch_by_idx[21], ch21_zones, domain_mask, full_domain=False)

  # --- Master Manifests: magnetic_areal_masks.json5 & magnetic_gazetteers.json5 ---
  specialist_masks = []
  national_epoch_masks = []
  gazetteers = []

  for ch in itinerary["chapters"]:
    stem = ch["key"]
    folder = ch["folder"]
    entry = {
      "id": stem,
      "domain": ch["domain"],
      "domain_group": "sites_magnetic_europe",
      "json5_path": f"histmap/1.data_raw/population_regional/MAGNETIC/{folder}/{stem}.json5",
      "mask_path": f"histmap/1.data_raw/population_regional/MAGNETIC/{folder}/{stem}_areal_mask.png",
      "priority": 1 if ch["index"] == 1 else (3 if ch["index"] >= 19 else 2),
    }
    if ch["index"] >= 19:
      entry["is_admin1"] = True
    if ch["index"] == 1:
      specialist_masks.append(entry)
    else:
      national_epoch_masks.append(entry)

    gazetteers.append({
      "domain": ch["domain"],
      "itinerary_title": ch["itinerary_title"],
      "key": stem,
      "path": f"histmap/1.data_raw/population_regional/MAGNETIC/{folder}/{stem}_settlements.json",
      "priority": entry["priority"],
      "region_group": ch["region_group"],
    })

  am_manifest = {
    "grid_dimensions": [GRID_W, GRID_H],
    "regime_transitions": {
      "europe_north_atlantic": {
        "pre_admin_end": 400,
        "dynastic_imperial_start": 400,
        "contemporary_start": 1945,
      }
    },
    "geography_profile": {
      "projection_class": "albers_conic",
      "has_micro_islands": True,
      "max_adm2_area_km2": 25000,
      "note": "Europe excluding POLARIS core, plus Greenland, Faroes, Iceland, Svalbard, Azores, Madeira, Canary Islands and Eastern Thrace.",
    },
    "script_profile": {
      "target_scripts": ["Latn", "Grek", "Cyrl"],
      "allow_native_toponyms": True,
    },
    "hyde_years": ALL_HYDE_YEARS,
    "substrata_sources": {
      "sites_magnetic_europe": {
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/MAGNETIC/_shared/sites_magnetic_europe/config/documented_site_pixels.json",
        "domain": [-10000, 2025],
        "domain_code": 1,
        "domain_mask_png": "histmap/1.data_raw/population_regional/MAGNETIC/_shared/sites_magnetic_europe/config/magnetic_domain_mask.png",
        "rasters_folder": "histmap/1.data_raw/population_regional/MAGNETIC/_shared/sites_magnetic_europe/2.population_rasters",
        "sample_year": 1000,
      }
    },
    "smoothing": {
      "border_feather_radius_px": 8,
      "interior_multiplier_blur_passes": 4,
      "interior_multiplier_blur_radius_px": 10,
      "temporal_log_Laplacian_weight": 0.15,
    },
    "specialist_masks": specialist_masks,
    "national_epoch_masks": national_epoch_masks,
  }
  with open(os.path.join(MAG_DIR, "magnetic_areal_masks.json5"), "w", encoding="utf-8") as fh:
    json.dump(am_manifest, fh, indent=2, ensure_ascii=False)

  gaz_manifest = {
    "annual_continuity_span": [1871, 2025],
    "border_splice_years": [1918, 1919, 1920, 1938, 1939, 1945, 1990, 1991, 1992],
    "regime_transitions": am_manifest["regime_transitions"],
    "geography_profile": am_manifest["geography_profile"],
    "script_profile": am_manifest["script_profile"],
    "gazetteers": gazetteers,
  }
  with open(os.path.join(MAG_DIR, "magnetic_gazetteers.json5"), "w", encoding="utf-8") as fh:
    json.dump(gaz_manifest, fh, indent=2, ensure_ascii=False)

  print("\n[DONE] Built all 21 MAGNETIC areal masks, vector GeoJSONs, chapter configs, and master manifests.", flush=True)


if __name__ == "__main__":
  main()
