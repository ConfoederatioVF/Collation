"""Stage A2 Dual Mask & Vector Sub-Region GeoJSON Builder for Operation Viscount Project HANDBOOK.

Builds:
  1. `handbook_domain_mask.png` (4320x2160 RGBA) covering all 27 HANDBOOK countries/territories
     (North Africa, Near East, Iran, Afghanistan, Cyprus, Transcaucasia) from Natural Earth 10m Admin-0
     intersected with `land_area.png`.
  2. Smooth vector sub-region GeoJSONs (`_shared/_gis_cache/chapter_subregions/<stem>_subregions.geojson`)
     + 4320x2160 RGBA pipeline areal masks (`<chapter_dir>/<stem>_areal_mask.png`)
     + chapter regional population JSON5 files (`<chapter_dir>/<stem>.json5`) across all 27 canonical
     HANDBOOK chapters (-10000 to 2026 AD), strictly adhering to the Three-Regime Spatiotemporal Partitioning Law:
       - Regime I (Chapter 1, -10000..-3200): Dissolved HydroBASINS Level 6 ecological/hydrological
         macro-catchments across MENA, Anatolia, Iran, Afghanistan, Cyprus and Transcaucasia (0 synthetic boxes).
       - Regime II (Chapters 2..17, -3500..1975): Period-authentic kingdoms, empires, satrapies, junds,
         vilayets, governorates, colonial territories and mandates built from dissolved Natural Earth 10m
         Admin-1 & HydroBASINS polygons (0 synthetic boxes).
       - Regime III (Chapters 18..27, 1917..2026, is_admin1=true): Exact Natural Earth 10m Admin-1
         provinces, governorates, wilayas, oblasts and districts (incl. West Bank / Gaza disjoint polygons
         and Cyprus divided regions).
  3. Master manifests: `handbook_areal_masks.json5` and `handbook_gazetteers.json5`.
"""

import io
import json
import math
import os
import zipfile

import numpy as np
import shapefile
from PIL import Image
from shapely.geometry import Point, MultiPolygon, Polygon, mapping, shape
from shapely.ops import unary_union
from shapely.prepared import prep

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
HB_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "HANDBOOK")
SUB_GJ_DIR = os.path.join(HB_DIR, "_shared", "_gis_cache", "chapter_subregions")
HB_GIS_DIR = os.path.join(HB_DIR, "_shared", "_gis_cache")
JADE_GIS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "_gis_cache")
SHARED_GIS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared", "_gis_cache")
DOMAIN_CFG_DIR = os.path.join(HB_DIR, "_shared", "sites_handbook_mena", "config")
DOMAIN_MASK_PNG = os.path.join(DOMAIN_CFG_DIR, "handbook_domain_mask.png")
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")

os.makedirs(SUB_GJ_DIR, exist_ok=True)
os.makedirs(DOMAIN_CFG_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160

HANDBOOK_ADM0 = {
  "Afghanistan", "Algeria", "Armenia", "Azerbaijan", "Bahrain",
  "Cyprus", "Northern Cyprus", "Cyprus No Mans Area",
  "Akrotiri Sovereign Base Area", "Dhekelia Sovereign Base Area",
  "Egypt", "Georgia", "Iran", "Iraq", "Israel", "Jordan", "Kuwait", "Lebanon",
  "Libya", "Morocco", "Oman", "Palestine", "Qatar", "Saudi Arabia", "Syria",
  "Tunisia", "Turkey", "United Arab Emirates", "Western Sahara", "Yemen"
}

HYDE_YEARS = (
  [-10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000, 0]
  + list(range(100, 1700, 100))
  + list(range(1700, 1950, 10))
  + list(range(1950, 2026, 1))
)


def make_palette(n=120):
  """Deterministic high-contrast non-black unique RGB palette (all R+G+B > 120)."""
  cols = []
  used = set()
  for i in range(n * 3):
    h = (i * 0.618033988749895) % 1.0
    s = 0.48 + 0.22 * ((i % 3) / 2.0)
    v = 0.62 + 0.24 * (((i // 3) % 3) / 2.0)
    k = int(h * 6.0)
    f = h * 6.0 - k
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    if k % 6 == 0:
      r, g, b = v, t, p
    elif k % 6 == 1:
      r, g, b = q, v, p
    elif k % 6 == 2:
      r, g, b = p, v, t
    elif k % 6 == 3:
      r, g, b = p, q, v
    elif k % 6 == 4:
      r, g, b = t, p, v
    else:
      r, g, b = v, p, q
    rgb = (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))
    if rgb not in used and sum(rgb) > 150:
      used.add(rgb)
      cols.append(list(rgb))
    if len(cols) >= n:
      break
  return cols


PALETTE = make_palette(160)


def latlon_to_rc(lat, lon):
  r = min(GRID_H - 1, max(0, int((90.0 - lat) * GRID_H / 180.0)))
  c = min(GRID_W - 1, max(0, int((lon + 180.0) * GRID_W / 360.0)))
  return r, c


def rasterise_regions(regions, domain_mask, out_png, out_geojson):
  """Rasterises a list of (region_id, display_name, geom, pop_dict) to 4320x2160 RGBA + smooth GeoJSON.
  Paints largest polygons first and smallest city-enclaves last so compact urban districts never starve.
  """
  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  features = []
  meta_regions = {}
  used_rgbs = set()

  ordered = sorted(
    [r for r in regions if r[2] is not None and not r[2].is_empty],
    key=lambda x: -float(x[2].area)
  )

  for idx, (rid, rname, geom, pop_dict) in enumerate(ordered):
    rgb = PALETTE[idx % len(PALETTE)]
    while tuple(rgb) in used_rgbs:
      rgb = [(rgb[0] + 13) % 240 + 10, (rgb[1] + 29) % 240 + 10, (rgb[2] + 47) % 240 + 10]
    used_rgbs.add(tuple(rgb))

    minx, miny, maxx, maxy = geom.bounds
    r0, c0 = latlon_to_rc(maxy, minx)
    r1, c1 = latlon_to_rc(miny, maxx)
    r0, c0 = max(0, r0 - 1), max(0, c0 - 1)
    r1, c1 = min(GRID_H - 1, r1 + 1), min(GRID_W - 1, c1 + 1)

    sub_dom = domain_mask[r0:r1 + 1, c0:c1 + 1]
    drs, dcs = np.where(sub_dom)
    pg = prep(geom)
    px_count = 0
    for dr, dc in zip(drs, dcs):
      rr, cc = r0 + int(dr), c0 + int(dc)
      plat = 90.0 - (rr + 0.5) * 180.0 / GRID_H
      plon = -180.0 + (cc + 0.5) * 360.0 / GRID_W
      if pg.contains(Point(plon, plat)):
        rgba[rr, cc] = [rgb[0], rgb[1], rgb[2], 255]
        px_count += 1

    # Pin exact centroid pixel for sub-5-arcminute city-enclaves (e.g. Hawalli, Mingachevir, Shusha, Bahrain)
    if px_count == 0:
      rp = geom.representative_point()
      rr, cc = latlon_to_rc(rp.y, rp.x)
      rgba[rr, cc] = [rgb[0], rgb[1], rgb[2], 255]
      px_count = 1

    meta_regions[rid] = {
      "name": rname,
      "rgb": rgb,
      "pixel_count": px_count,
      "population": {str(k): int(v) for k, v in sorted(pop_dict.items(), key=lambda kv: int(kv[0]))}
    }
    features.append({
      "type": "Feature",
      "properties": {
        "id": rid,
        "name": rname,
        "rgb": rgb,
        "hex": "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2]),
        "pixel_count": px_count
      },
      "geometry": mapping(geom.simplify(0.015, preserve_topology=True))
    })

  os.makedirs(os.path.dirname(out_png), exist_ok=True)
  Image.fromarray(rgba, mode="RGBA").save(out_png)
  os.makedirs(os.path.dirname(out_geojson), exist_ok=True)
  with open(out_geojson, "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": features}, fh, ensure_ascii=False)
  return meta_regions


def load_gis_layers():
  print("[1] Loading Natural Earth 10m Admin-0, Admin-1 & building HANDBOOK 4320x2160 domain mask...", flush=True)
  la_raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  land_area = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2])

  ne0 = json.load(open(os.path.join(SHARED_GIS_DIR, "ne_10m_admin_0_countries.geojson"), "r", encoding="utf-8"))
  adm0 = {}
  for f in ne0["features"]:
    adm = (f.get("properties") or {}).get("ADMIN")
    if adm in HANDBOOK_ADM0:
      g = shape(f["geometry"]).buffer(0)
      adm0[adm] = unary_union([adm0[adm], g]).buffer(0) if adm in adm0 else g

  # Merge Cyprus micro-polygons under "Cyprus_All" helper while preserving individual pieces
  cyprus_parts = [adm0[k] for k in ("Cyprus", "Northern Cyprus", "Cyprus No Mans Area", "Akrotiri Sovereign Base Area", "Dhekelia Sovereign Base Area") if k in adm0]
  adm0["Cyprus_Island"] = unary_union(cyprus_parts).buffer(0)
  hb_union = unary_union(list(adm0.values())).buffer(0)

  if os.path.exists(DOMAIN_MASK_PNG):
    dm_raw = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
    domain_mask = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)
    print(f"  Loaded cached {DOMAIN_MASK_PNG}: {int(domain_mask.sum()):,} active pixels", flush=True)
  else:
    domain_mask = np.zeros((GRID_H, GRID_W), dtype=bool)
    minx, miny, maxx, maxy = hb_union.bounds
    r0, c0 = latlon_to_rc(maxy, minx)
    r1, c1 = latlon_to_rc(miny, maxx)
    r0, c0 = max(0, r0 - 2), max(0, c0 - 2)
    r1, c1 = min(GRID_H - 1, r1 + 2), min(GRID_W - 1, c1 + 2)
    pg = prep(hb_union)
    for rr in range(r0, r1 + 1):
      plat = 90.0 - (rr + 0.5) * 180.0 / GRID_H
      for cc in range(c0, c1 + 1):
        if land_area[rr, cc] == 0:
          continue
        plon = -180.0 + (cc + 0.5) * 360.0 / GRID_W
        if pg.contains(Point(plon, plat)):
          domain_mask[rr, cc] = True
    # Ensure Bahrain & small Gulf islands have >= 2 land pixels
    for tiny in ("Bahrain", "Qatar", "Kuwait", "Lebanon", "Cyprus"):
      if tiny in adm0:
        rp = adm0[tiny].representative_point()
        tr, tc = latlon_to_rc(rp.y, rp.x)
        if land_area[tr, tc] > 0:
          domain_mask[tr, tc] = True
    rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
    rgba[domain_mask] = [255, 255, 255, 255]
    Image.fromarray(rgba, mode="RGBA").save(DOMAIN_MASK_PNG)
    print(f"  Saved {DOMAIN_MASK_PNG}: {int(domain_mask.sum()):,} pixels ({int(land_area[domain_mask].sum()):,} km2)", flush=True)

  # Load Natural Earth 10m Admin-1 grouped by country
  adm1_gj = json.load(open(os.path.join(JADE_GIS_DIR, "ne_10m_admin_1_states_provinces.geojson"), "r", encoding="utf-8"))
  adm1_by_c = {}
  for f in adm1_gj["features"]:
    p = f["properties"]
    c = p.get("admin")
    if c not in HANDBOOK_ADM0:
      continue
    nm = p.get("name") or p.get("name_en") or "Unknown"
    g = shape(f["geometry"]).buffer(0)
    if g.is_empty:
      continue
    rp = g.representative_point()
    adm1_by_c.setdefault(c, []).append({
      "name": nm,
      "geom": g,
      "lat": float(rp.y),
      "lon": float(rp.x),
      "area": float(g.area)
    })

  # Split Palestine MultiPolygon into West Bank & Gaza Strip cleanly
  pal_g = adm0.get("Palestine")
  if pal_g is not None:
    polys = list(pal_g.geoms) if isinstance(pal_g, MultiPolygon) else [pal_g]
    wb = [p for p in polys if p.representative_point().x >= 34.7]
    gz = [p for p in polys if p.representative_point().x < 34.7]
    adm1_by_c["Palestine"] = []
    if wb:
      g_wb = unary_union(wb).buffer(0)
      rp = g_wb.representative_point()
      adm1_by_c["Palestine"].append({"name": "West Bank", "geom": g_wb, "lat": float(rp.y), "lon": float(rp.x), "area": float(g_wb.area)})
    if gz:
      g_gz = unary_union(gz).buffer(0)
      rp = g_gz.representative_point()
      adm1_by_c["Palestine"].append({"name": "Gaza Strip", "geom": g_gz, "lat": float(rp.y), "lon": float(rp.x), "area": float(g_gz.area)})

  # Load HydroBASINS Level 6 (Africa, Asia, Europe) clipped to HANDBOOK for crisp organic Regime I catchments
  print("[2] Loading HydroBASINS Level 6 (Africa, Asia, Europe) for Regime I ecological catchments...", flush=True)
  basins = []
  hyb_sources = [
    os.path.join(HB_GIS_DIR, "hybas_af_lev06_v1c.zip"),
    os.path.join(HB_GIS_DIR, "hybas_eu_lev06_v1c.zip"),
    os.path.join(JADE_GIS_DIR, "hybas_as_lev06_v1c.zip"),
  ]
  for hp in hyb_sources:
    if not os.path.exists(hp):
      print(f"  [WARN] Missing HydroBASINS: {hp}", flush=True)
      continue
    with zipfile.ZipFile(hp) as zf:
      sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
      sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
      for sr in sf.iterShapeRecords():
        bb = sr.shape.bbox
        if bb[2] < -18.0 or bb[0] > 76.0 or bb[3] < 11.5 or bb[1] > 44.5:
          continue
        g = shape(sr.shape.__geo_interface__).buffer(0)
        if not g.is_empty and g.intersects(hb_union):
          gc = g.intersection(hb_union).buffer(0)
          if not gc.is_empty and gc.area > 0.005:
            rp = gc.representative_point()
            basins.append((gc, float(rp.y), float(rp.x), os.path.basename(hp)))
  print(f"  Clipped {len(basins):,} HydroBASINS L6 sub-basins inside HANDBOOK", flush=True)
  return domain_mask, land_area, adm0, adm1_by_c, basins


def group_admin1(adm1_by_c, country, rules, default_key):
  """Groups Admin-1 units of a country into authentic historical macro-provinces via predicate rules."""
  buckets = {}
  for rec in adm1_by_c.get(country, []):
    key = default_key
    for rkey, pred in rules:
      if pred(rec):
        key = rkey
        break
    buckets.setdefault(key, []).append(rec["geom"])
  return {k: unary_union(gs).buffer(0) for k, gs in buckets.items() if gs}


def scale_pop_dict(base_dict, shares):
  """Distributes a total trajectory across sub-regions proportionally by weight share."""
  tot = sum(shares.values())
  out = {}
  for k, w in shares.items():
    out[k] = {yr: max(500, int(round(val * w / tot))) for yr, val in base_dict.items()}
  return out


def build_all_27_chapters(domain_mask, adm0, adm1_by_c, basins):
  """Constructs all 27 HANDBOOK chapters' dual masks + JSON5 population tables + master manifests."""
  import json5 as j5
  itinerary = j5.load(open(os.path.join(HB_DIR, "handbook_itinerary.json5"), "r", encoding="utf-8"))
  ch_by_stem = {c["stem"]: c for c in itinerary["chapters"]}

  # Helper country unions
  def C(*names):
    gs = [adm0[n] for n in names if n in adm0]
    return unary_union(gs).buffer(0) if gs else None

  # --- Helper macro-province partitions (strictly organic Admin-1 dissolved unions, 0 rectangular boxes!) ---
  egypt_parts = group_admin1(adm1_by_c, "Egypt", [
    ("cairo_alex", lambda r: any(k in r["name"].lower() for k in ("cairo", "qahir", "alexandria", "iskand", "giza", "jizah", "qalyub"))),
    ("delta", lambda r: r["lat"] >= 30.25 and 29.5 <= r["lon"] <= 32.35),
    ("sinai_canal", lambda r: r["lon"] > 32.15 and r["lat"] >= 27.5),
    ("western_oases", lambda r: r["lon"] < 29.8 and r["lat"] < 30.5),
    ("middle_egypt", lambda r: r["lat"] >= 27.0 and r["lat"] < 30.25),
  ], "upper_egypt")

  iraq_parts = group_admin1(adm1_by_c, "Iraq", [
    ("assyria_mosul", lambda r: r["lat"] >= 35.15),
    ("diyala_east", lambda r: r["lat"] >= 32.8 and r["lon"] >= 44.6),
    ("upper_euphrates_anbar", lambda r: r["lon"] < 43.3 and r["lat"] < 35.15),
    ("babylonia_baghdad", lambda r: r["lat"] >= 31.8 and r["lat"] < 35.15),
  ], "sumer_basra")

  turkey_parts = group_admin1(adm1_by_c, "Turkey", [
    ("west_anatolia_thrace", lambda r: r["lon"] < 30.3),
    ("black_sea_pontus", lambda r: r["lat"] >= 40.3 and r["lon"] >= 30.3 and r["lon"] < 41.2),
    ("south_cilicia_pamphylia", lambda r: r["lat"] < 37.9 and r["lon"] >= 30.3 and r["lon"] < 37.5),
    ("east_anatolia_urartu", lambda r: r["lon"] >= 38.2),
  ], "central_anatolia")

  iran_parts = group_admin1(adm1_by_c, "Iran", [
    ("khuzestan_elam", lambda r: any(k in r["name"].lower() for k in ("khuz", "ilam", "bushehr", "kohgil"))),
    ("azerbaijan_caspian", lambda r: r["lat"] >= 36.2 and r["lon"] < 54.0),
    ("media_zagros", lambda r: r["lon"] < 50.5 and r["lat"] < 36.2),
    ("fars_persis", lambda r: r["lat"] < 31.5 and 50.5 <= r["lon"] < 55.5),
    ("khorasan_sistan", lambda r: r["lon"] >= 55.5),
  ], "central_plateau")

  afg_parts = group_admin1(adm1_by_c, "Afghanistan", [
    ("bactria_north", lambda r: r["lat"] >= 35.5 and r["lon"] >= 63.5),
    ("herat_west", lambda r: r["lon"] < 63.8 and r["lat"] >= 32.5),
    ("kandahar_helmand", lambda r: r["lat"] < 33.2),
    ("hazarajat_central", lambda r: 33.2 <= r["lat"] < 35.5 and 63.8 <= r["lon"] < 68.0),
  ], "kabul_east")

  syria_parts = group_admin1(adm1_by_c, "Syria", [
    ("aleppo_north", lambda r: r["lat"] >= 35.5 and r["lon"] < 38.5),
    ("jazira_euphrates", lambda r: r["lon"] >= 38.5),
  ], "damascus_coastal")

  saudi_parts = group_admin1(adm1_by_c, "Saudi Arabia", [
    ("hejaz_asir", lambda r: r["lon"] < 42.5),
    ("eastern_hasaa", lambda r: r["lon"] >= 47.0),
    ("north_nafud", lambda r: r["lat"] >= 27.5 and r["lon"] < 47.0),
  ], "najd_central")

  algeria_parts = group_admin1(adm1_by_c, "Algeria", [
    ("tell_coastal", lambda r: r["lat"] >= 35.2),
    ("high_plateaux", lambda r: 33.2 <= r["lat"] < 35.2),
  ], "algerian_sahara")

  libya_parts = group_admin1(adm1_by_c, "Libya", [
    ("tripolitania", lambda r: r["lat"] >= 29.0 and r["lon"] < 17.5),
    ("cyrenaica", lambda r: r["lat"] >= 28.5 and r["lon"] >= 17.5),
  ], "fezzan_sahara")

  morocco_parts = group_admin1(adm1_by_c, "Morocco", [
    ("north_rif_fez", lambda r: r["lat"] >= 33.2),
    ("atlantic_marrakech", lambda r: 30.8 <= r["lat"] < 33.2),
  ], "south_atlas_draa")

  yemen_parts = group_admin1(adm1_by_c, "Yemen", [
    ("highland_north_yemen", lambda r: r["lon"] < 45.2 and r["lat"] >= 13.4),
  ], "aden_hadramawt")

  # --- Build Chapter 1 (Regime I: Prehistoric & Neolithic HydroBASINS L6 Catchments, -10000..-3200) ---
  print("[3] Building Chapter 1 (Regime I: Dissolved HydroBASINS L6 Ecological Catchments)...", flush=True)
  eco_buckets = {}
  for g, lat, lon, src in basins:
    if lon < -8.0 and lat < 28.0:
      ek = "atlantic_sahara_basins"
    elif lon < 11.5 and lat >= 32.5:
      ek = "maghreb_tell_atlas"
    elif lon < 25.0 and lat < 32.5:
      ek = "central_sahara_fezzan"
    elif 11.5 <= lon < 25.0 and lat >= 30.0:
      ek = "tripolitania_cyrenaica_coast"
    elif 25.0 <= lon < 34.5 and lat < 32.0:
      ek = "nile_valley_delta_oases"
    elif 25.5 <= lon < 41.5 and lat >= 36.2:
      ek = "anatolian_plateau_coasts"
    elif 32.0 <= lon < 35.0 and 34.4 <= lat <= 35.8:
      ek = "cyprus_island_catchments"
    elif 34.0 <= lon < 38.8 and 29.0 <= lat < 36.5:
      ek = "levantine_fertile_crescent"
    elif 38.8 <= lon < 48.8 and 29.2 <= lat < 37.8:
      ek = "tigris_euphrates_basin"
    elif 40.0 <= lon < 50.5 and lat >= 37.8:
      ek = "transcaucasia_kura_aras"
    elif 45.0 <= lon < 54.5 and 27.0 <= lat < 38.5:
      ek = "zagros_fars_elam"
    elif 54.5 <= lon < 62.5 and 25.0 <= lat < 38.5:
      ek = "iranian_plateau_khorasan"
    elif lon >= 62.5 and lat >= 34.2:
      ek = "hindu_kush_bactria_amu"
    elif lon >= 60.5 and lat < 34.2:
      ek = "helmand_sistan_makran"
    elif 34.5 <= lon < 46.5 and 12.0 <= lat < 21.0:
      ek = "yemen_asir_highlands"
    elif 46.5 <= lon < 60.5 and 12.0 <= lat < 27.0:
      ek = "oman_gulf_hadramawt"
    else:
      ek = "arabian_steppe_wadis"
    eco_buckets.setdefault(ek, []).append(g)

  # Ensure Cyprus island catchment is present cleanly
  if "cyprus_island_catchments" not in eco_buckets:
    eco_buckets["cyprus_island_catchments"] = [adm0["Cyprus_Island"]]

  ch1_names = {
    "maghreb_tell_atlas": "Maghreb Tell and Atlas Basins",
    "atlantic_sahara_basins": "Atlantic Sahara Wadis",
    "central_sahara_fezzan": "Saharan and Fezzan Pluvial Basins",
    "tripolitania_cyrenaica_coast": "Tripolitania and Cyrenaica Coast",
    "nile_valley_delta_oases": "Nile Valley, Delta and Western Oases",
    "levantine_fertile_crescent": "Levantine Corridor and Jordan Valley",
    "tigris_euphrates_basin": "Tigris-Euphrates Alluvial Basin",
    "anatolian_plateau_coasts": "Anatolian Plateau and Coasts",
    "cyprus_island_catchments": "Cyprus Catchments",
    "transcaucasia_kura_aras": "Transcaucasia and Kura-Aras Basin",
    "zagros_fars_elam": "Zagros Piedmont, Susiana and Fars",
    "iranian_plateau_khorasan": "Iranian Plateau and Khorasan",
    "hindu_kush_bactria_amu": "Hindu Kush and Bactrian Foothills",
    "helmand_sistan_makran": "Helmand and Sistan Basin",
    "yemen_asir_highlands": "Yemen and Asir Highlands",
    "oman_gulf_hadramawt": "Oman, Gulf Coast and Hadramawt",
    "arabian_steppe_wadis": "Interior Arabian Wadis and Nefud",
  }
  ch1_weights = {
    "nile_valley_delta_oases": 0.16, "levantine_fertile_crescent": 0.12, "tigris_euphrates_basin": 0.15,
    "anatolian_plateau_coasts": 0.13, "zagros_fars_elam": 0.10, "maghreb_tell_atlas": 0.08,
    "iranian_plateau_khorasan": 0.05, "transcaucasia_kura_aras": 0.04, "hindu_kush_bactria_amu": 0.03,
    "yemen_asir_highlands": 0.035, "central_sahara_fezzan": 0.025, "tripolitania_cyrenaica_coast": 0.02,
    "oman_gulf_hadramawt": 0.02, "helmand_sistan_makran": 0.015, "arabian_steppe_wadis": 0.015,
    "cyprus_island_catchments": 0.008, "atlantic_sahara_basins": 0.002,
  }
  ch1_total = {-10000: 1_150_000, -8000: 1_850_000, -6000: 3_400_000, -5000: 5_200_000, -4000: 7_800_000, -3200: 10_600_000}
  ch1_pops = scale_pop_dict(ch1_total, {k: ch1_weights.get(k, 0.01) for k in eco_buckets})
  ch1_regions = [(k, ch1_names.get(k, k), unary_union(gs).buffer(0), ch1_pops[k]) for k, gs in sorted(eco_buckets.items())]

  # --- Helper for Regime III exact Admin-1 chapters ---
  def admin1_regions_for(countries, total_curve):
    items = []
    weights = {}
    for c in countries:
      if c == "Cyprus":
        for ck in ("Cyprus", "Northern Cyprus", "Cyprus No Mans Area", "Akrotiri Sovereign Base Area", "Dhekelia Sovereign Base Area"):
          if ck in adm0:
            rid = ck.lower().replace(" ", "_")
            items.append((rid, ck, adm0[ck]))
            weights[rid] = max(0.01, float(adm0[ck].area))
        continue
      recs = adm1_by_c.get(c) or []
      if not recs and c in adm0:
        rid = c.lower().replace(" ", "_")
        items.append((rid, c, adm0[c]))
        weights[rid] = max(0.05, float(adm0[c].area))
      else:
        for i_r, r in enumerate(recs):
          slug = f"{c.lower().replace(' ', '_')}_{i_r:02d}_{''.join(ch if ch.isalnum() else '_' for ch in r['name'].lower()).strip('_')[:28]}"
          items.append((slug, f"{r['name']} ({c})" if len(countries) > 1 else r["name"], r["geom"]))
          # Use sqrt(area) weighting initially so compact dense provinces aren't starved by desert provinces
          weights[slug] = max(0.05, math.sqrt(max(0.01, r["area"])))
    pops = scale_pop_dict(total_curve, weights)
    return [(rid, nm, g, pops[rid]) for rid, nm, g in items]

  # --- Define all 27 chapters' region sets & initial historical benchmark curves ---
  chapter_defs = {
    "prehistoric_neolithic_mena_iran_afghanistan": ch1_regions,

    "ancient_mesopotamia": [
      ("sumer_babylonia_south", "Lower Mesopotamia (Sumer and Southern Babylonia)", iraq_parts["sumer_basra"], {-3500: 420_000, -2500: 780_000, -1800: 950_000, -1000: 820_000, -539: 1_350_000}),
      ("akkad_central_babylonia", "Akkad and Central Babylonia", iraq_parts["babylonia_baghdad"], {-3500: 210_000, -2500: 460_000, -1800: 680_000, -1000: 560_000, -539: 980_000}),
      ("assyria_upper_tigris", "Assyria and Upper Tigris", iraq_parts["assyria_mosul"], {-3500: 140_000, -2500: 280_000, -1800: 420_000, -1000: 650_000, -539: 580_000}),
      ("diyala_east_tigris", "Diyala and East Tigris Piedmont", iraq_parts["diyala_east"], {-3500: 75_000, -2500: 150_000, -1800: 210_000, -1000: 190_000, -539: 290_000}),
      ("middle_euphrates_khabur", "Middle Euphrates and Khabur Jezirah", unary_union([iraq_parts["upper_euphrates_anbar"], syria_parts["jazira_euphrates"]]).buffer(0), {-3500: 110_000, -2500: 240_000, -1800: 360_000, -1000: 310_000, -539: 420_000}),
    ],

    "pharaonic_egypt": [
      ("lower_egypt_delta", "Lower Egypt (Nile Delta)", egypt_parts["delta"], {-3200: 380_000, -2500: 680_000, -1900: 920_000, -1300: 1_350_000, -525: 1_750_000}),
      ("memphis_fayum", "Memphis and Fayum Core", egypt_parts["cairo_alex"], {-3200: 160_000, -2500: 320_000, -1900: 440_000, -1300: 520_000, -525: 620_000}),
      ("middle_egypt", "Middle Egypt", egypt_parts["middle_egypt"], {-3200: 210_000, -2500: 360_000, -1900: 480_000, -1300: 640_000, -525: 760_000}),
      ("upper_egypt_thebaid", "Upper Egypt (Thebaid)", egypt_parts["upper_egypt"], {-3200: 240_000, -2500: 390_000, -1900: 540_000, -1300: 780_000, -525: 840_000}),
      ("western_oases_egypt", "Western Desert Oases", egypt_parts["western_oases"], {-3200: 25_000, -2500: 35_000, -1900: 45_000, -1300: 65_000, -525: 90_000}),
      ("sinai_eastern_desert", "Sinai and Eastern Desert", egypt_parts["sinai_canal"], {-3200: 18_000, -2500: 25_000, -1900: 35_000, -1300: 50_000, -525: 65_000}),
    ],

    "ancient_anatolia_levant_arabia": [
      ("central_anatolia_hatti", "Central Anatolia (Hatti)", turkey_parts["central_anatolia"], {-3200: 350_000, -2000: 620_000, -1300: 980_000, -800: 1_050_000, -539: 1_280_000}),
      ("west_anatolia_aegean", "Western Anatolia and Aegean Coast", turkey_parts["west_anatolia_thrace"], {-3200: 290_000, -2000: 520_000, -1300: 780_000, -800: 1_100_000, -539: 1_450_000}),
      ("pontus_north_anatolia", "Northern Anatolia and Pontus", turkey_parts["black_sea_pontus"], {-3200: 160_000, -2000: 270_000, -1300: 390_000, -800: 480_000, -539: 610_000}),
      ("south_anatolia_cilicia", "Southern Anatolia (Cilicia and Luwia)", turkey_parts["south_cilicia_pamphylia"], {-3200: 180_000, -2000: 310_000, -1300: 490_000, -800: 620_000, -539: 740_000}),
      ("cyprus_alashiya", "Cyprus (Alashiya)", adm0["Cyprus_Island"], {-3200: 28_000, -2000: 65_000, -1300: 120_000, -800: 145_000, -539: 180_000}),
      ("north_levant_aramean_phoenicia", "Northern Levant (Syria and Phoenicia)", unary_union([syria_parts["aleppo_north"], syria_parts["damascus_coastal"], adm0["Lebanon"]]).buffer(0), {-3200: 310_000, -2000: 580_000, -1300: 840_000, -800: 1_020_000, -539: 1_180_000}),
      ("south_levant_israel_judah", "Southern Levant (Israel, Judah and Transjordan)", C("Israel", "Palestine", "Jordan"), {-3200: 190_000, -2000: 340_000, -1300: 490_000, -800: 690_000, -539: 560_000}),
      ("north_central_arabia", "North and Central Arabia", C("Saudi Arabia", "Kuwait"), {-3200: 160_000, -2000: 240_000, -1300: 340_000, -800: 460_000, -539: 580_000}),
      ("south_arabian_kingdoms", "South Arabian Kingdoms (Saba, Ma'in, Qataban, Hadramawt)", adm0["Yemen"], {-3200: 220_000, -2000: 410_000, -1300: 650_000, -800: 950_000, -539: 1_250_000}),
      ("dilmun_magan_gulf", "Dilmun and Magan (Oman and Gulf)", C("Oman", "United Arab Emirates", "Qatar", "Bahrain"), {-3200: 95_000, -2000: 190_000, -1300: 240_000, -800: 280_000, -539: 340_000}),
    ],

    "ancient_iran_afghanistan_transcaucasia": [
      ("elam_susiana", "Elam and Susiana", iran_parts["khuzestan_elam"], {-3200: 240_000, -2000: 420_000, -1200: 540_000, -600: 520_000, -330: 690_000}),
      ("fars_persis", "Fars (Persis)", iran_parts["fars_persis"], {-3200: 150_000, -2000: 280_000, -1200: 380_000, -600: 620_000, -330: 920_000}),
      ("media_zagros", "Media and Western Zagros", iran_parts["media_zagros"], {-3200: 260_000, -2000: 480_000, -1200: 680_000, -600: 1_050_000, -330: 1_320_000}),
      ("atropatene_caspian", "Northwestern Iran and Caspian Littoral", iran_parts["azerbaijan_caspian"], {-3200: 220_000, -2000: 390_000, -1200: 560_000, -600: 840_000, -330: 1_080_000}),
      ("central_iranian_plateau", "Central Iranian Plateau and Kerman", iran_parts["central_plateau"], {-3200: 180_000, -2000: 340_000, -1200: 460_000, -600: 640_000, -330: 850_000}),
      ("parthia_khorasan_sistan", "Parthia, Khorasan and Sistan", iran_parts["khorasan_sistan"], {-3200: 170_000, -2000: 310_000, -1200: 440_000, -600: 660_000, -330: 880_000}),
      ("bactria_north_afghanistan", "Bactria and Northern Afghanistan", afg_parts["bactria_north"], {-3200: 130_000, -2000: 310_000, -1200: 380_000, -600: 580_000, -330: 780_000}),
      ("aria_arachosia_gandhara", "Aria, Arachosia and Kabul-Gandhara", unary_union([afg_parts["herat_west"], afg_parts["kandahar_helmand"], afg_parts["hazarajat_central"], afg_parts["kabul_east"]]).buffer(0), {-3200: 190_000, -2000: 380_000, -1200: 520_000, -600: 790_000, -330: 1_060_000}),
      ("urartu_armenia", "Urartu and Armenian Highlands", unary_union([turkey_parts["east_anatolia_urartu"], adm0["Armenia"]]).buffer(0), {-3200: 210_000, -2000: 390_000, -1200: 580_000, -600: 820_000, -330: 960_000}),
      ("colchis_iberia_albania", "Colchis, Iberia and Caucasian Albania", C("Georgia", "Azerbaijan"), {-3200: 180_000, -2000: 340_000, -1200: 480_000, -600: 680_000, -330: 840_000}),
    ],

    "hellenistic_roman_parthian_sassanid": [
      ("mauretania_numidia", "Mauretania and Numidia", C("Morocco", "Western Sahara", "Algeria"), {-539: 1_450_000, -200: 2_350_000, 1: 3_150_000, 200: 4_100_000, 500: 3_350_000, 632: 2_950_000}),
      ("africa_proconsularis", "Carthage and Africa Proconsularis", adm0["Tunisia"], {-539: 750_000, -200: 1_350_000, 1: 1_750_000, 200: 2_450_000, 500: 1_850_000, 632: 1_450_000}),
      ("tripolitania_cyrenaica", "Tripolitania, Cyrenaica and Garamantian Fezzan", adm0["Libya"], {-539: 380_000, -200: 620_000, 1: 820_000, 200: 1_050_000, 500: 760_000, 632: 640_000}),
      ("ptolemaic_roman_egypt", "Ptolemaic and Roman Egypt", adm0["Egypt"], {-539: 4_100_000, -200: 5_200_000, 1: 6_400_000, 200: 6_800_000, 500: 5_600_000, 632: 4_850_000}),
      ("roman_anatolia_cyprus", "Hellenistic and Roman Anatolia and Cyprus", C("Turkey", "Cyprus_Island"), {-539: 4_850_000, -200: 6_900_000, 1: 8_800_000, 200: 10_400_000, 500: 9_600_000, 632: 7_400_000}),
      ("seleucid_roman_levant", "Seleucid and Roman Levant", C("Syria", "Lebanon", "Jordan", "Israel", "Palestine"), {-539: 2_100_000, -200: 3_400_000, 1: 4_600_000, 200: 5_400_000, 500: 5_200_000, 632: 4_150_000}),
      ("parthian_sassanid_mesopotamia", "Parthian and Sassanid Mesopotamia (Asoristan)", adm0["Iraq"], {-539: 3_250_000, -200: 4_100_000, 1: 4_900_000, 200: 5_600_000, 500: 6_100_000, 632: 5_200_000}),
      ("parthian_sassanid_iran", "Parthian and Sassanid Iran", adm0["Iran"], {-539: 4_950_000, -200: 6_100_000, 1: 7_400_000, 200: 8_500_000, 500: 8_900_000, 632: 7_600_000}),
      ("kushan_bactrian_afghanistan", "Greco-Bactrian and Kushan Afghanistan", adm0["Afghanistan"], {-539: 1_550_000, -200: 2_150_000, 1: 2_650_000, 200: 3_100_000, 500: 2_750_000, 632: 2_550_000}),
      ("classical_transcaucasia", "Classical Armenia, Iberia and Caucasian Albania", C("Georgia", "Armenia", "Azerbaijan"), {-539: 1_150_000, -200: 1_550_000, 1: 1_950_000, 200: 2_250_000, 500: 2_150_000, 632: 1_950_000}),
      ("classical_arabia_himyar", "Himyarite Yemen, Nabataean-Gulf and Arabian Peninsula", C("Saudi Arabia", "Yemen", "Oman", "United Arab Emirates", "Qatar", "Bahrain", "Kuwait"), {-539: 2_150_000, -200: 2_650_000, 1: 3_150_000, 200: 3_550_000, 500: 3_250_000, 632: 3_100_000}),
    ],

    "early_islamic_caliphate": [
      ("al_maghrib", "Al-Maghrib al-Aqsa and al-Awsat", C("Morocco", "Western Sahara", "Algeria"), {632: 2_950_000, 750: 3_250_000, 850: 3_650_000, 1000: 4_150_000}),
      ("ifriqiya_barqa", "Ifriqiya, Tripolitania and Barqa", C("Tunisia", "Libya"), {632: 2_090_000, 750: 2_180_000, 850: 2_450_000, 1000: 2_750_000}),
      ("misr_egypt", "Misr (Early Islamic Egypt)", adm0["Egypt"], {632: 4_850_000, 750: 5_050_000, 850: 5_350_000, 1000: 5_750_000}),
      ("bilad_al_sham", "Bilad al-Sham (Umayyad and Abbasid Levant)", C("Syria", "Lebanon", "Jordan", "Israel", "Palestine"), {632: 4_150_000, 750: 4_650_000, 850: 4_350_000, 1000: 4_150_000}),
      ("iraq_sawad", "Al-Iraq (Sawad) and Al-Jazira", adm0["Iraq"], {632: 5_200_000, 750: 6_100_000, 850: 6_850_000, 1000: 5_600_000}),
      ("byzantine_anatolia_cyprus", "Byzantine Anatolia, Thughur and Cyprus", C("Turkey", "Cyprus_Island"), {632: 7_400_000, 750: 7_150_000, 850: 7_950_000, 1000: 9_150_000}),
      ("arminiya_arran", "Arminiya, Gurjistan and Arran", C("Georgia", "Armenia", "Azerbaijan"), {632: 1_950_000, 750: 2_100_000, 850: 2_350_000, 1000: 2_650_000}),
      ("jibal_fars_khurasan", "Jibal, Fars, Khuzestan and Khurasan", adm0["Iran"], {632: 7_600_000, 750: 7_950_000, 850: 8_650_000, 1000: 9_350_000}),
      ("kabulistan_ghur_tokharistan", "Tokharistan, Sistan and Kabulistan", adm0["Afghanistan"], {632: 2_550_000, 750: 2_650_000, 850: 2_850_000, 1000: 3_150_000}),
      ("hijaz_yaman_oman", "Al-Hijaz, Najd, Al-Yaman and Oman", C("Saudi Arabia", "Yemen", "Oman", "United Arab Emirates", "Qatar", "Bahrain", "Kuwait"), {632: 3_100_000, 750: 3_250_000, 850: 3_450_000, 1000: 3_650_000}),
    ],

    "mediaeval_near_east_iran_caucasia": [
      ("seljuk_beylik_anatolia", "Rum Seljuk and Beylik Anatolia", adm0["Turkey"], {1000: 8_950_000, 1150: 8_150_000, 1250: 8_450_000, 1350: 6_850_000, 1500: 7_950_000}),
      ("lusignan_venetian_cyprus", "Byzantine and Lusignan Cyprus", adm0["Cyprus_Island"], {1000: 200_000, 1150: 215_000, 1250: 225_000, 1350: 150_000, 1500: 185_000}),
      ("crusader_ayyubid_mamluk_levant", "Crusader, Ayyubid and Mamluk Levant", C("Syria", "Lebanon", "Jordan", "Israel", "Palestine"), {1000: 4_150_000, 1150: 4_050_000, 1250: 3_750_000, 1350: 2_650_000, 1500: 2_950_000}),
      ("seljuk_ilkhanid_iraq", "Seljuk, Ilkhanid and Jalayirid Iraq", adm0["Iraq"], {1000: 5_600_000, 1150: 5_100_000, 1250: 3_850_000, 1350: 2_350_000, 1500: 2_450_000}),
      ("georgian_kingdom_caucasia", "Kingdom of Georgia, Armenia and Shirvan", C("Georgia", "Armenia", "Azerbaijan"), {1000: 2_650_000, 1150: 3_150_000, 1250: 2_850_000, 1350: 2_150_000, 1500: 2_450_000}),
      ("seljuk_ilkhanid_timurid_iran", "Seljuk, Khwarazmian, Ilkhanid and Timurid Iran", adm0["Iran"], {1000: 9_350_000, 1150: 9_850_000, 1250: 6_950_000, 1350: 5_450_000, 1500: 6_350_000}),
      ("ghaznavid_ghurid_timurid_afg", "Ghaznavid, Ghurid and Timurid Afghanistan", adm0["Afghanistan"], {1000: 3_150_000, 1150: 3_450_000, 1250: 2_350_000, 1350: 2_050_000, 1500: 2_650_000}),
      ("mediaeval_arabia", "Rasulid Yemen, Nabhanid Oman and Hijaz-Najd", C("Saudi Arabia", "Yemen", "Oman", "United Arab Emirates", "Qatar", "Bahrain", "Kuwait"), {1000: 3_650_000, 1150: 3_850_000, 1250: 4_050_000, 1350: 3_350_000, 1500: 3_750_000}),
    ],

    "mediaeval_north_africa": [
      ("almoravid_marinid_morocco", "Almoravid, Almohad and Marinid Morocco and Western Sahara", C("Morocco", "Western Sahara"), {1000: 2_250_000, 1150: 2_850_000, 1300: 3_150_000, 1400: 2_350_000, 1517: 2_750_000}),
      ("hammadid_zayyanid_algeria", "Hammadid, Almohad and Zayyanid Algeria", adm0["Algeria"], {1000: 1_900_000, 1150: 2_150_000, 1300: 2_250_000, 1400: 1_750_000, 1517: 1_950_000}),
      ("zirid_hafsid_tunisia", "Zirid and Hafsid Ifriqiya (Tunisia)", adm0["Tunisia"], {1000: 1_750_000, 1150: 1_650_000, 1300: 1_750_000, 1400: 1_250_000, 1517: 1_350_000}),
      ("mediaeval_libya", "Tripolitania, Cyrenaica and Fezzan", adm0["Libya"], {1000: 1_000_000, 1150: 880_000, 1300: 820_000, 1400: 640_000, 1517: 680_000}),
      ("fatimid_mamluk_egypt", "Fatimid, Ayyubid and Mamluk Egypt", adm0["Egypt"], {1000: 5_750_000, 1150: 5_950_000, 1300: 6_450_000, 1400: 4_150_000, 1517: 4_550_000}),
    ],

    "ottoman_empire_mena": [
      ("ottoman_west_anatolia", "Anadolu, Hudavendigar and Aydin Eyalets", turkey_parts["west_anatolia_thrace"], {1300: 2_250_000, 1520: 2_650_000, 1600: 3_150_000, 1700: 2_950_000, 1800: 3_450_000, 1881: 4_650_000, 1914: 5_850_000, 1918: 5_150_000}),
      ("ottoman_central_anatolia", "Karaman, Ankara and Sivas Vilayets", turkey_parts["central_anatolia"], {1300: 2_050_000, 1520: 2_350_000, 1600: 2_750_000, 1700: 2_550_000, 1800: 2_850_000, 1881: 3_450_000, 1914: 4_150_000, 1918: 3_650_000}),
      ("ottoman_pontus_black_sea", "Trabzon and Kastamonu Vilayets", turkey_parts["black_sea_pontus"], {1300: 950_000, 1520: 1_150_000, 1600: 1_350_000, 1700: 1_250_000, 1800: 1_450_000, 1881: 1_850_000, 1914: 2_250_000, 1918: 1_850_000}),
      ("ottoman_cilicia_south", "Adana and Konya Mediterranean Vilayets", turkey_parts["south_cilicia_pamphylia"], {1300: 950_000, 1520: 1_100_000, 1600: 1_280_000, 1700: 1_180_000, 1800: 1_350_000, 1881: 1_750_000, 1914: 2_150_000, 1918: 1_850_000}),
      ("ottoman_east_anatolia", "Erzurum, Van, Bitlis and Diyarbakir Vilayets", turkey_parts["east_anatolia_urartu"], {1300: 1_350_000, 1520: 1_550_000, 1600: 1_750_000, 1700: 1_650_000, 1800: 1_950_000, 1881: 2_450_000, 1914: 2_950_000, 1918: 1_650_000}),
      ("ottoman_cyprus", "Ottoman Cyprus (Eyalet of Kibris)", adm0["Cyprus_Island"], {1300: 175_000, 1520: 185_000, 1600: 165_000, 1700: 135_000, 1800: 120_000, 1881: 186_000, 1914: 286_000, 1918: 300_000}),
      ("ottoman_levant", "Aleppo, Damascus, Beirut and Jerusalem Vilayets", C("Syria", "Lebanon", "Jordan", "Israel", "Palestine"), {1300: 2_950_000, 1520: 3_050_000, 1600: 3_350_000, 1700: 2_950_000, 1800: 2_750_000, 1881: 3_350_000, 1914: 4_150_000, 1918: 3_550_000}),
      ("ottoman_iraq", "Mosul, Baghdad and Basra Vilayets", adm0["Iraq"], {1300: 2_550_000, 1520: 2_450_000, 1600: 2_350_000, 1700: 2_150_000, 1800: 2_100_000, 1881: 2_450_000, 1914: 2_950_000, 1918: 2_850_000}),
      ("ottoman_arabia", "Hejaz, Yemen and Al-Hasa Ottoman Provinces", C("Saudi Arabia", "Yemen", "Oman", "United Arab Emirates", "Qatar", "Bahrain", "Kuwait"), {1300: 3_550_000, 1520: 3_750_000, 1600: 4_050_000, 1700: 4_250_000, 1800: 4_550_000, 1881: 5_150_000, 1914: 5_850_000, 1918: 5_750_000}),
      ("ottoman_egypt_pre1799", "Ottoman Eyalet of Misr", adm0["Egypt"], {1517: 4_550_000, 1600: 4_850_000, 1700: 4_650_000, 1799: 4_250_000}),
      ("ottoman_maghreb_regencies", "Ottoman Regencies of Algiers, Tunis and Tripoli", C("Algeria", "Tunisia", "Libya"), {1517: 3_980_000, 1600: 4_250_000, 1700: 4_350_000, 1800: 4_550_000, 1830: 4_750_000}),
    ],

    "safavid_afsharid_qajar_iran": [
      ("iran_azerbaijan_caspian", "Azerbaijan, Gilan and Mazandaran", iran_parts["azerbaijan_caspian"], {1501: 1_750_000, 1600: 2_250_000, 1722: 2_150_000, 1800: 1_950_000, 1850: 2_450_000, 1900: 3_250_000, 1925: 3_850_000}),
      ("iran_central_plateau", "Central Plateau (Isfahan, Qazvin, Tehran, Kerman)", iran_parts["central_plateau"], {1501: 1_450_000, 1600: 1_950_000, 1722: 1_750_000, 1800: 1_450_000, 1850: 1_850_000, 1900: 2_450_000, 1925: 3_050_000}),
      ("iran_zagros_west", "Western Zagros (Kermanshah, Hamadan, Luristan)", iran_parts["media_zagros"], {1501: 1_150_000, 1600: 1_350_000, 1722: 1_250_000, 1800: 1_150_000, 1850: 1_450_000, 1900: 1_850_000, 1925: 2_150_000}),
      ("iran_fars_khuzestan", "Fars, Khuzestan and Persian Gulf Littoral", unary_union([iran_parts["fars_persis"], iran_parts["khuzestan_elam"]]).buffer(0), {1501: 1_050_000, 1600: 1_350_000, 1722: 1_250_000, 1800: 1_050_000, 1850: 1_250_000, 1900: 1_550_000, 1925: 1_850_000}),
      ("iran_khorasan_sistan", "Khorasan, Sistan and Baluchestan", iran_parts["khorasan_sistan"], {1501: 950_000, 1600: 1_150_000, 1722: 1_050_000, 1800: 950_000, 1850: 1_150_000, 1900: 1_450_000, 1925: 1_750_000}),
    ],

    "durrani_barakzai_afghanistan": [
      ("kabul_eastern_afg", "Kabul and Eastern Provinces", afg_parts["kabul_east"], {1747: 980_000, 1800: 1_150_000, 1850: 1_350_000, 1900: 1_750_000, 1919: 2_050_000}),
      ("kandahar_helmand", "Kandahar and Helmand", afg_parts["kandahar_helmand"], {1747: 680_000, 1800: 780_000, 1850: 920_000, 1900: 1_150_000, 1919: 1_350_000}),
      ("herat_western_afg", "Herat and Western Provinces", afg_parts["herat_west"], {1747: 540_000, 1800: 620_000, 1850: 710_000, 1900: 880_000, 1919: 1_020_000}),
      ("afghan_turkestan", "Afghan Turkestan (Balkh and Badakhshan)", afg_parts["bactria_north"], {1747: 640_000, 1800: 740_000, 1850: 860_000, 1900: 1_100_000, 1919: 1_280_000}),
      ("hazarajat_central", "Hazarajat and Central Highlands", afg_parts["hazarajat_central"], {1747: 410_000, 1800: 460_000, 1850: 520_000, 1900: 520_000, 1919: 580_000}),
    ],

    "russian_transcaucasia": [
      ("tiflis_kutaisi_georgia", "Tiflis and Kutaisi Governorates (Georgia)", adm0["Georgia"], {1801: 780_000, 1835: 1_050_000, 1865: 1_450_000, 1897: 2_109_000, 1917: 2_650_000}),
      ("erivan_armenia", "Erivan Governorate and Armenian Highlands", adm0["Armenia"], {1801: 310_000, 1835: 420_000, 1865: 590_000, 1897: 829_000, 1917: 1_010_000}),
      ("baku_elisabethpol_azerbaijan", "Baku and Elisabethpol Governorates (Azerbaijan)", adm0["Azerbaijan"], {1801: 680_000, 1835: 890_000, 1865: 1_250_000, 1897: 1_807_000, 1917: 2_340_000}),
    ],

    "colonial_north_africa": [
      ("french_algeria_tell", "French Algeria: Tell Departements", algeria_parts["tell_coastal"], {1830: 1_950_000, 1856: 1_650_000, 1881: 2_250_000, 1911: 3_750_000, 1936: 4_950_000, 1954: 6_450_000, 1962: 7_250_000}),
      ("french_algeria_plateaux_sahara", "French Algeria: High Plateaux and Territoires du Sud", unary_union([algeria_parts["high_plateaux"], algeria_parts["algerian_sahara"]]).buffer(0), {1830: 1_050_000, 1856: 850_000, 1881: 1_060_000, 1911: 1_810_000, 1936: 2_285_000, 1954: 3_080_000, 1962: 3_650_000}),
      ("french_tunisia", "French Protectorate of Tunisia", adm0["Tunisia"], {1830: 1_150_000, 1881: 1_520_000, 1911: 1_939_000, 1936: 2_608_000, 1956: 3_783_000}),
      ("french_spanish_morocco", "French and Spanish Protectorates of Morocco", adm0["Morocco"], {1830: 3_250_000, 1881: 3_950_000, 1912: 5_150_000, 1936: 7_040_000, 1956: 10_450_000}),
      ("spanish_sahara", "Spanish Sahara (Rio de Oro and Saguia el-Hamra)", adm0["Western Sahara"], {1830: 14_000, 1881: 16_000, 1912: 18_000, 1936: 24_000, 1960: 36_000, 1975: 76_000}),
      ("italian_libya", "Italian Libya (Tripolitania, Cyrenaica and Fezzan)", adm0["Libya"], {1830: 680_000, 1881: 780_000, 1911: 860_000, 1931: 704_000, 1936: 848_000, 1951: 1_065_000}),
    ],

    "khedivate_british_egypt": [
      ("cairo_alexandria_khed", "Cairo and Alexandria Metropolises", egypt_parts["cairo_alex"], {1799: 480_000, 1846: 720_000, 1882: 1_120_000, 1897: 1_580_000, 1917: 2_180_000, 1937: 3_150_000, 1952: 4_850_000}),
      ("nile_delta_khed", "Lower Egypt (Nile Delta)", egypt_parts["delta"], {1799: 1_750_000, 1846: 2_150_000, 1882: 2_850_000, 1897: 4_050_000, 1917: 5_180_000, 1937: 6_350_000, 1952: 8_350_000}),
      ("middle_egypt_khed", "Middle Egypt and Fayum", egypt_parts["middle_egypt"], {1799: 920_000, 1846: 1_120_000, 1882: 1_380_000, 1897: 1_950_000, 1917: 2_520_000, 1937: 3_120_000, 1952: 3_950_000}),
      ("upper_egypt_khed", "Upper Egypt", egypt_parts["upper_egypt"], {1799: 1_020_000, 1846: 1_180_000, 1882: 1_360_000, 1897: 1_960_000, 1917: 2_560_000, 1937: 3_020_000, 1952: 3_820_000}),
      ("canal_sinai_deserts_khed", "Suez Canal Zone, Sinai and Desert Governorates", unary_union([egypt_parts["sinai_canal"], egypt_parts["western_oases"]]).buffer(0), {1799: 80_000, 1846: 95_000, 1882: 120_000, 1897: 194_000, 1917: 311_000, 1937: 293_000, 1952: 530_000}),
    ],

    "mandates_levant_iraq_cyprus": [
      ("mandate_syria", "French Mandate for Syria", adm0["Syria"], {1918: 1_850_000, 1922: 1_950_000, 1932: 2_250_000, 1946: 3_050_000}),
      ("mandate_lebanon", "French Mandate for Greater Lebanon", adm0["Lebanon"], {1918: 580_000, 1922: 640_000, 1932: 793_000, 1946: 1_180_000}),
      ("mandate_palestine", "British Mandate for Palestine", C("Israel", "Palestine"), {1918: 680_000, 1922: 757_000, 1931: 1_036_000, 1947: 1_970_000, 1948: 1_950_000}),
      ("mandate_transjordan", "Emirate of Transjordan", adm0["Jordan"], {1918: 225_000, 1922: 240_000, 1931: 300_000, 1946: 430_000}),
      ("mandate_iraq", "British Mandate for Mesopotamia (Iraq)", adm0["Iraq"], {1918: 2_850_000, 1920: 2_849_000, 1932: 3_450_000}),
      ("crown_colony_cyprus", "British Crown Colony of Cyprus", adm0["Cyprus_Island"], {1918: 300_000, 1921: 311_000, 1931: 348_000, 1946: 450_000, 1960: 574_000}),
    ],

    "arabian_peninsula_state_formation": [
      ("saudi_hejaz_asir", "Hejaz and Asir", saudi_parts["hejaz_asir"], {1900: 1_150_000, 1932: 1_350_000, 1950: 1_750_000, 1971: 2_950_000}),
      ("saudi_najd_north_east", "Najd, Northern Borders and Al-Hasa (Eastern Province)", unary_union([saudi_parts["najd_central"], saudi_parts["north_nafud"], saudi_parts["eastern_hasaa"]]).buffer(0), {1900: 950_000, 1932: 1_150_000, 1950: 1_550_000, 1971: 3_150_000}),
      ("north_south_yemen", "Mutawakkilite Yemen and Aden Protectorate", adm0["Yemen"], {1900: 2_850_000, 1932: 3_450_000, 1950: 4_450_000, 1971: 6_350_000}),
      ("muscat_oman", "Sultanate of Muscat and Oman", adm0["Oman"], {1900: 360_000, 1932: 410_000, 1950: 460_000, 1971: 745_000}),
      ("kuwait_sheikhdom", "Kuwait", adm0["Kuwait"], {1900: 35_000, 1932: 75_000, 1950: 155_000, 1971: 790_000}),
      ("bahrain_qatar_trucial", "Bahrain, Qatar and the Trucial States", C("Bahrain", "Qatar", "United Arab Emirates"), {1900: 145_000, 1932: 195_000, 1950: 210_000, 1971: 625_000}),
    ],

    # --- Regime III: Modern Census Chapters (Exact Natural Earth 10m Admin-1) ---
    "republic_of_turkey": admin1_regions_for(["Turkey"], {1923: 13_100_000, 1927: 13_648_000, 1940: 17_821_000, 1950: 20_947_000, 1970: 35_605_000, 1990: 56_473_000, 2000: 67_804_000, 2020: 83_614_000, 2025: 85_665_000}),
    "modern_iran": admin1_regions_for(["Iran"], {1925: 12_650_000, 1956: 18_955_000, 1966: 25_789_000, 1976: 33_709_000, 1986: 49_445_000, 1996: 60_055_000, 2006: 70_496_000, 2016: 79_926_000, 2025: 89_800_000}),
    "modern_afghanistan": admin1_regions_for(["Afghanistan"], {1919: 6_280_000, 1950: 8_150_000, 1979: 13_051_000, 2000: 20_130_000, 2015: 33_831_000, 2025: 42_650_000}),
    "soviet_postsoviet_transcaucasia": admin1_regions_for(["Georgia", "Armenia", "Azerbaijan"], {1917: 6_000_000, 1926: 5_862_000, 1939: 8_034_000, 1959: 9_505_000, 1970: 12_295_000, 1989: 15_725_000, 2000: 15_560_000, 2014: 16_310_000, 2025: 16_920_000}),
    "modern_levant_israel_palestine": admin1_regions_for(["Syria", "Lebanon", "Jordan", "Israel", "Palestine"], {1946: 6_550_000, 1960: 9_850_000, 1975: 15_250_000, 1990: 24_650_000, 2005: 37_250_000, 2015: 44_150_000, 2025: 54_800_000}),
    "modern_iraq": admin1_regions_for(["Iraq"], {1932: 3_450_000, 1947: 4_816_000, 1957: 6_340_000, 1965: 8_047_000, 1977: 12_000_000, 1987: 16_335_000, 1997: 22_046_000, 2015: 37_140_000, 2025: 46_042_000}),
    "modern_egypt": admin1_regions_for(["Egypt"], {1952: 21_500_000, 1960: 26_085_000, 1976: 36_626_000, 1986: 48_254_000, 1996: 59_313_000, 2006: 72_798_000, 2017: 94_799_000, 2025: 116_500_000}),
    "modern_maghreb_libya": admin1_regions_for(["Morocco", "Western Sahara", "Algeria", "Tunisia", "Libya"], {1951: 24_600_000, 1965: 31_850_000, 1977: 43_200_000, 1987: 55_900_000, 2004: 73_100_000, 2014: 87_400_000, 2025: 103_800_000}),
    "modern_cyprus": admin1_regions_for(["Cyprus"], {1960: 574_000, 1973: 632_000, 1982: 665_000, 1992: 785_000, 2001: 905_000, 2011: 1_126_000, 2021: 1_305_000, 2025: 1_360_000}),
    "modern_arabian_peninsula": admin1_regions_for(["Saudi Arabia", "Yemen", "Oman", "Kuwait", "Bahrain", "Qatar", "United Arab Emirates"], {1971: 14_600_000, 1980: 22_400_000, 1992: 37_800_000, 2004: 55_600_000, 2015: 76_400_000, 2022: 88_900_000, 2025: 94_800_000}),
  }

  specialist_masks = []
  national_epoch_masks = []
  gazetteer_entries = []

  print("[4] Writing dual masks (4320x2160 PNG + smooth GeoJSON) & chapter JSON5s across all 27 chapters...", flush=True)
  for ch in itinerary["chapters"]:
    stem = ch["stem"]
    rel_dir = f"histmap/1.data_raw/population_regional/HANDBOOK/{ch['group']}/{ch['folder']}"
    abs_dir = os.path.join(SVEA_ROOT, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    os.makedirs(os.path.join(abs_dir, "papers"), exist_ok=True)
    os.makedirs(os.path.join(abs_dir, "figures"), exist_ok=True)

    mask_png = os.path.join(abs_dir, f"{stem}_areal_mask.png")
    sub_gj = os.path.join(SUB_GJ_DIR, f"{stem}_subregions.geojson")
    ch_json5 = os.path.join(abs_dir, f"{stem}.json5")

    regions = chapter_defs[stem]
    meta_regions = rasterise_regions(regions, domain_mask, mask_png, sub_gj)

    ch_obj = {
      "id": stem,
      "title": ch["itinerary_title"],
      "full_scope": ch["full_scope"],
      "domain": ch["domain"],
      "regime": ch["regime"],
      "regions": meta_regions
    }
    with open(ch_json5, "w", encoding="utf-8") as fh:
      json.dump(ch_obj, fh, indent=2, ensure_ascii=False)

    entry = {
      "id": stem,
      "domain": ch["domain"],
      "domain_group": "sites_handbook_mena",
      "json5_path": f"{rel_dir}/{stem}.json5",
      "mask_path": f"{rel_dir}/{stem}_areal_mask.png",
      "priority": 1 if ch["regime"] == 1 else (2 if ch["regime"] == 2 else 3)
    }
    if ch.get("is_admin1"):
      entry["is_admin1"] = True
    if ch["regime"] == 1:
      specialist_masks.append(entry)
    else:
      national_epoch_masks.append(entry)

    gazetteer_entries.append({
      "domain": ch["domain"],
      "itinerary_title": ch["itinerary_title"],
      "key": stem,
      "path": f"{rel_dir}/{stem}_settlements.json",
      "priority": entry["priority"],
      "region_group": ch["group"]
    })
    print(f"  [{ch['index']:02d}/27] {stem}: {len(meta_regions)} sub-regions rasterised", flush=True)

  # Write handbook_areal_masks.json5
  areal_manifest = {
    "grid_dimensions": [GRID_W, GRID_H],
    "regime_transitions": {
      "mena_iran_afghanistan_caucasia": {
        "pre_admin_end": -3200,
        "dynastic_imperial_start": -3200,
        "contemporary_start": 1950
      }
    },
    "geography_profile": {
      "projection_class": "lambert_azimuthal",
      "has_micro_islands": False,
      "max_adm2_area_km2": 25000,
      "note": "North Africa, Near East, Anatolia, Cyprus, Transcaucasia, Iran, Afghanistan and Arabian Peninsula."
    },
    "script_profile": {
      "target_scripts": ["Latn", "Arab", "Hebr", "Grek", "Armn", "Geor", "Cyrl"],
      "allow_native_toponyms": True
    },
    "hyde_years": HYDE_YEARS,
    "substrata_sources": {
      "sites_handbook_mena": {
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/HANDBOOK/_shared/sites_handbook_mena/config/documented_site_pixels.json",
        "domain": [-10000, 2025],
        "domain_code": 1,
        "domain_mask_png": "histmap/1.data_raw/population_regional/HANDBOOK/_shared/sites_handbook_mena/config/handbook_domain_mask.png",
        "rasters_folder": "histmap/1.data_raw/population_regional/HANDBOOK/_shared/sites_handbook_mena/2.population_rasters",
        "sample_year": 1000
      }
    },
    "smoothing": {
      "border_feather_radius_px": 8,
      "interior_multiplier_blur_passes": 4,
      "interior_multiplier_blur_radius_px": 10,
      "temporal_log_Laplacian_weight": 0.15
    },
    "specialist_masks": specialist_masks,
    "national_epoch_masks": national_epoch_masks
  }
  with open(os.path.join(HB_DIR, "handbook_areal_masks.json5"), "w", encoding="utf-8") as fh:
    json.dump(areal_manifest, fh, indent=2, ensure_ascii=False)

  # Write handbook_gazetteers.json5
  gaz_manifest = {
    "annual_continuity_span": [1950, 2025],
    "border_splice_years": [1920, 1923, 1948, 1967, 1990, 1991],
    "regime_transitions": areal_manifest["regime_transitions"],
    "geography_profile": {
      "projection_class": "lambert_azimuthal",
      "has_micro_islands": False,
      "max_adm2_area_km2": 25000
    },
    "script_profile": areal_manifest["script_profile"],
    "gazetteers": gazetteer_entries
  }
  with open(os.path.join(HB_DIR, "handbook_gazetteers.json5"), "w", encoding="utf-8") as fh:
    json.dump(gaz_manifest, fh, indent=2, ensure_ascii=False)
  print("DONE build_handbook_areal_masks.py", flush=True)


if __name__ == "__main__":
  dm, la, adm0, adm1_by_c, basins = load_gis_layers()
  build_all_27_chapters(dm, adm0, adm1_by_c, basins)
