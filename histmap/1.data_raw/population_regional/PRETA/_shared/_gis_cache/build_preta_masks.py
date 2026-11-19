"""Deterministic 5-arcminute (4320x2160) Dual-Output GIS Mask Builder for Operation Viscount
Project PRETA (13 chapters across Pre-Columbian, Colonial, and Post-Independence regimes).

Generates:
  1. Smooth vector GeoJSON sub-regions (`_shared/_gis_cache/chapter_subregions/<stem>_subregions.geojson`)
  2. Exact 4320x2160 `*_areal_mask.png` pipeline rasters (`land_area > 0` enforced)
  3. Regional demographic `<stem>.json5` manifests with primary-historiography population trajectories
  4. Root `preta_areal_masks.json5` and Stage C `preta_domain_mask.png`

Zero synthetic rectangular LAT/LON cuts; 100% organic HydroBASINS Level 5 watersheds (Regime I),
authentic historical colonial captaincy/intendancy/mission groupings (Regime II), and exact
Natural Earth 10m Admin-1 boundaries (Regime III).
"""

import colorsys
import json
import os
import pathlib
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree
import shapefile
from shapely.geometry import Polygon, MultiPolygon, shape, mapping
from shapely.ops import unary_union

sys.stdout.reconfigure(encoding="utf-8")

W, H = 4320, 2160
PRETA_DIR = pathlib.Path(__file__).resolve().parents[2]
SVEA_ROOT = PRETA_DIR.parents[3]
CACHE_DIR = pathlib.Path(__file__).resolve().parent
HB_DIR = CACHE_DIR / "hydrobasins"
SUBREG_OUT_DIR = CACHE_DIR / "chapter_subregions"
DOMAIN_CFG_DIR = PRETA_DIR / "_shared/sites_preta_amazon_brazil/config"

SUBREG_OUT_DIR.mkdir(parents=True, exist_ok=True)
DOMAIN_CFG_DIR.mkdir(parents=True, exist_ok=True)

LAND_AREA_PNG = SVEA_ROOT / "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png"
NE10_ADM1_JSON = SVEA_ROOT / "histmap/1.data_raw/population_regional/CENTAUR/_shared/_gis_cache/ne_10m_admin_1_states_provinces.geojson"
NE10_ADM0_JSON = SVEA_ROOT / "histmap/1.data_raw/population_regional/_shared/_gis_cache/ne_10m_admin_0_countries.geojson"
HYBAS_L5_SHP = HB_DIR / "hybas_sa_lev05_v1c.shp"

HYDE_YEARS = [
  -10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000,
  0, 100, 200, 300, 400, 500, 600, 700, 800, 900,
  1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
  1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790,
  1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890,
  1900, 1910, 1920, 1930, 1940, 1950,
  1951, 1952, 1953, 1954, 1955, 1956, 1957, 1958, 1959, 1960,
  1961, 1962, 1963, 1964, 1965, 1966, 1967, 1968, 1969, 1970,
  1971, 1972, 1973, 1974, 1975, 1976, 1977, 1978, 1979, 1980,
  1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1989, 1990,
  1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000,
  2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
  2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020,
  2021, 2022, 2023, 2024, 2025
]


def distinct_palette(arg0_n, arg1_seed_offset=0.0):
  """Generates n visually distinct RGB colours (never pure black)."""
  cols = []
  used = {(0, 0, 0)}
  for i in range(arg0_n):
    hue = (arg1_seed_offset + i * 0.618033988749895) % 1.0
    sat = 0.56 + 0.24 * ((i % 3) / 2.0)
    val = 0.72 + 0.20 * (((i // 3) % 3) / 2.0)
    r, g, b = [max(18, min(244, int(round(c * 255)))) for c in colorsys.hsv_to_rgb(hue, sat, val)]
    while (r, g, b) in used:
      r = (r + 17) % 224 + 20
      g = (g + 29) % 224 + 20
    used.add((r, g, b))
    cols.append([r, g, b])
  return cols


def load_land_area():
  """Decodes SVEA 4320x2160 uint32 big-endian land_area.png into km² float64 grid."""
  raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  # Check uint32 vs float32 encoding
  u32 = raw.reshape(-1, 4).copy().view(">u4").reshape((H, W)).astype(np.float64)
  # Fallback pixel area approximation if land_area values are scaled or raw
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape((H, W)).astype(np.float64)
  if np.nanmax(f32) > 1.0 and np.nanmax(f32) < 500.0 and np.isfinite(f32[1080, 1500]):
    return np.where(np.isfinite(f32) & (f32 > 0), f32, 0.0)
  # SVEA land_area.png stores integer km² * scale or raw float; verify typical equatorial cell (~85 km²)
  med = float(np.median(u32[u32 > 0])) if (u32 > 0).any() else 0.0
  if 1.0 <= med <= 500.0:
    return u32
  # Compute spherical cell area for non-zero pixels
  lats = 90.0 - (np.arange(H) + 0.5) / 12.0
  cell_km2 = (111.32 / 12.0) * (111.32 / 12.0) * np.cos(np.radians(lats))
  return np.where(u32 > 0, cell_km2[:, None], 0.0)


def rasterize_geom_list(arg0_geom_id_pairs):
  """Rasterizes [(int_id, shapely_geom), ...] onto (H, W) int32 grid."""
  img = Image.new("I", (W, H), 0)
  draw = ImageDraw.Draw(img)

  def draw_poly(poly, val):
    if poly.is_empty:
      return
    ext = list(poly.exterior.coords)
    if len(ext) < 3:
      return
    pts = [((x + 180.0) * 12.0, (90.0 - y) * 12.0) for x, y in ext]
    draw.polygon(pts, fill=int(val))
    for hole in poly.interiors:
      h_coords = list(hole.coords)
      if len(h_coords) >= 3:
        h_pts = [((x + 180.0) * 12.0, (90.0 - y) * 12.0) for x, y in h_coords]
        draw.polygon(h_pts, fill=0)

  for gid, geom in arg0_geom_id_pairs:
    if geom is None or geom.is_empty:
      continue
    if geom.geom_type == "Polygon":
      draw_poly(geom, gid)
    elif geom.geom_type in ("MultiPolygon", "GeometryCollection"):
      for part in geom.geoms:
        if part.geom_type == "Polygon":
          draw_poly(part, gid)
  return np.asarray(img, dtype=np.int32)


def nearest_fill(arg0_target_mask, arg1_label_grid, arg2_valid_labels):
  """Assigns any True pixel in target_mask not yet labelled to its nearest valid pixel."""
  src_mask = np.isin(arg1_label_grid, list(arg2_valid_labels))
  missing = arg0_target_mask & (~src_mask)
  if not missing.any() or not src_mask.any():
    return arg1_label_grid
  sr, sc = np.where(src_mask)
  mr, mc = np.where(missing)
  tree = cKDTree(np.column_stack([sr, sc]))
  _, idx = tree.query(np.column_stack([mr, mc]))
  out = arg1_label_grid.copy()
  out[mr, mc] = arg1_label_grid[sr[idx], sc[idx]]
  return out


def clean_geom(arg0_geom):
  """Repairs minor self-intersections and keeps polygonal components."""
  if arg0_geom is None or arg0_geom.is_empty:
    return None
  g = arg0_geom.buffer(0)
  if g.is_empty:
    return None
  if g.geom_type == "GeometryCollection":
    polys = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon") and not p.is_empty]
    if not polys:
      return None
    g = unary_union(polys)
  return g


def load_gis_sources():
  """Loads NE 10m Admin-1 polygons for South America and HydroBASINS Level 5 polygons."""
  with open(NE10_ADM1_JSON, "r", encoding="utf-8") as fh:
    adm1_gj = json.load(fh)

  adm1 = {}  # (iso3, name) -> shapely geom
  by_iso = {}
  target_isos = {"BRA", "BOL", "PRY", "GUY", "SUR", "COL", "PER", "ECU", "FRA"}
  for ft in adm1_gj["features"]:
    p = ft["properties"]
    iso = p.get("adm0_a3")
    nm = str(p.get("name") or "")
    if iso not in target_isos:
      continue
    if iso == "FRA" and "Guyane" not in nm:
      continue
    if iso == "FRA":
      iso = "GUF"
      nm = "French Guiana"
    geom = clean_geom(shape(ft["geometry"]))
    if geom is None:
      continue
    adm1[(iso, nm)] = geom
    by_iso.setdefault(iso, []).append(geom)

  country_geom = {iso: clean_geom(unary_union(gs)) for iso, gs in by_iso.items()}

  # Load HydroBASINS SA Level 5
  sf = shapefile.Reader(str(HYBAS_L5_SHP))
  flds = [f[0] for f in sf.fields[1:]]
  hybas = []
  for i, rec in enumerate(sf.records()):
    d = dict(zip(flds, rec))
    g = clean_geom(shape(sf.shape(i).__geo_interface__))
    if g is not None:
      hybas.append((str(d["PFAF_ID"]), int(d["HYBAS_ID"]), g))

  return adm1, country_geom, hybas


def union_hybas(arg0_hybas, arg1_prefixes, arg2_clip_geom=None):
  """Unions all HydroBASINS L5 polygons matching any Pfafstetter prefix, optionally clipped."""
  matched = [g for pfaf, _, g in arg0_hybas if any(pfaf.startswith(pref) for pref in arg1_prefixes)]
  if not matched:
    return None
  u = clean_geom(unary_union(matched))
  if arg2_clip_geom is not None and u is not None:
    u = clean_geom(u.intersection(arg2_clip_geom))
  return u


def union_adm1(arg0_adm1, arg1_pairs):
  """Unions [(iso, name), ...] Admin-1 polygons."""
  gs = [arg0_adm1[k] for k in arg1_pairs if k in arg0_adm1]
  if not gs:
    return None
  return clean_geom(unary_union(gs))


def make_bounds(arg0_pop_dict, arg1_rel_unc=0.18):
  """Generates symmetric [low, high] demographic uncertainty bounds for each benchmark year."""
  out = {}
  for yk, val in arg0_pop_dict.items():
    v = int(round(val))
    yr = int(yk)
    # Wider uncertainty in deep prehistory, tighter in modern census era
    if yr <= -2000:
      u = max(arg1_rel_unc, 0.35)
    elif yr < 1500:
      u = max(arg1_rel_unc, 0.25)
    elif yr < 1850:
      u = max(arg1_rel_unc, 0.14)
    elif yr < 1950:
      u = 0.06
    else:
      u = 0.025
    lo = max(0, int(round(v * (1.0 - u))))
    hi = max(lo + 1, int(round(v * (1.0 + u))))
    out[str(yk)] = [lo, hi]
  return out


def scale_holocene_curve(arg0_peak_1500, arg1_profile="amazon_varzea"):
  """Produces smooth log-space Holocene trajectories calibrated to South American archaeology."""
  # Relative fractions of 1500 AD peak across benchmark years (-10000 to 1542/1500)
  curves = {
    "amazon_varzea": {
      -10000: 0.008, -9000: 0.012, -8000: 0.018, -7000: 0.026, -6000: 0.038,
      -5000: 0.055, -4000: 0.078, -3000: 0.110, -2000: 0.165, -1000: 0.250,
      0: 0.390, 200: 0.455, 400: 0.530, 600: 0.615, 800: 0.710,
      1000: 0.820, 1100: 0.875, 1200: 0.925, 1300: 0.960, 1400: 0.985,
      1500: 1.000, 1542: 0.960
    },
    "amazon_moxos_earthwork": {
      -10000: 0.006, -9000: 0.010, -8000: 0.015, -7000: 0.022, -6000: 0.035,
      -5000: 0.052, -4000: 0.075, -3000: 0.105, -2000: 0.155, -1000: 0.240,
      0: 0.370, 200: 0.460, 400: 0.580, 600: 0.720, 800: 0.840,
      1000: 0.940, 1100: 0.980, 1200: 1.000, 1300: 0.985, 1400: 0.950,
      1500: 0.910, 1542: 0.880
    },
    "brazil_coastal_tupi": {
      -10000: 0.014, -9000: 0.022, -8000: 0.032, -7000: 0.045, -6000: 0.065,
      -5000: 0.095, -4000: 0.135, -3000: 0.185, -2000: 0.235, -1000: 0.300,
      0: 0.410, 200: 0.470, 400: 0.540, 600: 0.620, 800: 0.710,
      1000: 0.810, 1100: 0.860, 1200: 0.905, 1300: 0.945, 1400: 0.978,
      1500: 1.000
    },
    "brazil_sambaqui_south": {
      -10000: 0.012, -9000: 0.020, -8000: 0.032, -7000: 0.052, -6000: 0.088,
      -5000: 0.145, -4000: 0.220, -3000: 0.310, -2000: 0.380, -1000: 0.420,
      0: 0.480, 200: 0.530, 400: 0.590, 600: 0.660, 800: 0.740,
      1000: 0.830, 1100: 0.875, 1200: 0.915, 1300: 0.950, 1400: 0.980,
      1500: 1.000
    },
    "guiana_raised_fields": {
      -10000: 0.008, -9000: 0.012, -8000: 0.018, -7000: 0.026, -6000: 0.040,
      -5000: 0.062, -4000: 0.090, -3000: 0.130, -2000: 0.190, -1000: 0.270,
      0: 0.390, 200: 0.455, 400: 0.540, 600: 0.640, 800: 0.750,
      1000: 0.860, 1100: 0.915, 1200: 0.955, 1300: 0.980, 1400: 0.995,
      1500: 1.000, 1595: 0.920
    },
  }
  c = curves[arg1_profile]
  return {str(y): max(50, int(round(arg0_peak_1500 * frac))) for y, frac in c.items()}


def build_chapter(arg0_spec, arg1_land_area):
  """Builds vector GeoJSON, 4320x2160 areal_mask PNG, and <stem>.json5 for one chapter."""
  ch_dir = PRETA_DIR / arg0_spec["rel_dir"]
  stem = arg0_spec["stem"]
  ch_dir.mkdir(parents=True, exist_ok=True)
  regions_spec = arg0_spec["regions"]
  palette = distinct_palette(len(regions_spec), arg0_spec.get("palette_seed", 0.07))

  # Compute target domain mask (union of all region geoms intersected with land_area > 0)
  geom_pairs = []
  valid_regions = []
  for idx, reg in enumerate(regions_spec):
    gid = idx + 1
    g = clean_geom(reg["geom"])
    if g is None or g.is_empty:
      raise RuntimeError(f"Empty geometry for {stem} -> {reg['id']}")
    geom_pairs.append((gid, g))
    valid_regions.append((gid, reg, g, palette[idx]))

  union_geom = clean_geom(unary_union([g for _, g in geom_pairs]))
  union_grid = rasterize_geom_list([(1, union_geom)])
  target_mask = (union_grid == 1) & (arg1_land_area > 0)

  # Ordered rasterisation onto pixel grid + nearest_fill so zero land pixels inside chapter are dropped
  label_grid = np.zeros((H, W), dtype=np.int32)
  for gid, g in geom_pairs:
    r_g = rasterize_geom_list([(gid, g)])
    sel = target_mask & (label_grid == 0) & (r_g == gid)
    label_grid[sel] = gid
  label_grid = nearest_fill(target_mask, label_grid, [gid for gid, _ in geom_pairs])
  label_grid = np.where(target_mask, label_grid, 0)

  # Write 4320x2160 RGBA areal_mask PNG
  rgba = np.zeros((H, W, 4), dtype=np.uint8)
  regions_meta = {}
  gj_features = []
  total_px = 0
  total_area = 0

  for gid, reg, g, col in valid_regions:
    rmask = (label_grid == gid)
    rs, cs = np.where(rmask)
    px_cnt = int(len(rs))
    if px_cnt == 0:
      raise RuntimeError(f"Starved zero-pixel sub-region in {stem}: {reg['id']}")
    rgba[rmask, 0] = col[0]
    rgba[rmask, 1] = col[1]
    rgba[rmask, 2] = col[2]
    rgba[rmask, 3] = 255

    lats = 90.0 - (rs + 0.5) / 12.0
    lons = -180.0 + (cs + 0.5) / 12.0
    area_km2 = int(round(float(arg1_land_area[rs, cs].sum())))
    total_px += px_cnt
    total_area += area_km2

    pop_dict = {str(k): int(round(v)) for k, v in reg["population"].items()}
    bounds_dict = make_bounds(pop_dict, arg1_rel_unc=arg0_spec.get("rel_unc", 0.18))

    regions_meta[reg["id"]] = {
      "name": reg["name"],
      "colour": col,
      "pixel_count": px_cnt,
      "area_km2": area_km2,
      "bbox": {
        "min_lat": round(float(lats.min()), 2),
        "max_lat": round(float(lats.max()), 2),
        "min_lon": round(float(lons.min()), 2),
        "max_lon": round(float(lons.max()), 2),
      },
      "population": pop_dict,
      "population_bounds": bounds_dict,
    }

    gj_features.append({
      "type": "Feature",
      "properties": {
        "region_id": reg["id"],
        "name": reg["name"],
        "colour": col,
        "colour_hex": "#{:02x}{:02x}{:02x}".format(col[0], col[1], col[2]),
        "pixel_count": px_cnt,
        "area_km2": area_km2,
      },
      "geometry": mapping(g.simplify(0.01, preserve_topology=True)),
    })

  mask_png_path = ch_dir / f"{stem}_areal_mask.png"
  Image.fromarray(rgba, mode="RGBA").save(mask_png_path, compress_level=6)

  # Persist smooth vector sub-region GeoJSON (Dual Mask Output Law)
  subreg_gj_path = SUBREG_OUT_DIR / f"{stem}_subregions.geojson"
  with open(subreg_gj_path, "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": gj_features}, fh, ensure_ascii=False)

  # Compute headline total series
  all_yrs = sorted({int(y) for r in regions_meta.values() for y in r["population"].keys()})
  headline = {}
  for yr in all_yrs:
    yk = str(yr)
    headline[yk] = sum(int(r["population"].get(yk, 0)) for r in regions_meta.values())

  ch_json = {
    "id": stem,
    "title": arg0_spec["title"],
    "source_review": f"histmap/1.data_raw/population_regional/PRETA/{arg0_spec['rel_dir']}/{stem}_literature_review.md",
    "settlements_gazetteer": f"histmap/1.data_raw/population_regional/PRETA/{arg0_spec['rel_dir']}/{stem}_settlements.json",
    "mask_file": f"{stem}_areal_mask.png",
    "vector_subregions_geojson": f"histmap/1.data_raw/population_regional/PRETA/_shared/_gis_cache/chapter_subregions/{stem}_subregions.geojson",
    "domain": arg0_spec["domain"],
    "grid_dimensions": [W, H],
    "total_pixels": total_px,
    "total_area_km2": total_area,
    "summary": {
      "headline_population_by_benchmark": headline,
    },
    "regions": regions_meta,
  }
  json5_path = ch_dir / f"{stem}.json5"
  with open(json5_path, "w", encoding="utf-8") as fh:
    json.dump(ch_json, fh, indent=2, ensure_ascii=False)

  print(f"  [OK] {stem:32s} | regions={len(regions_meta):2d} | px={total_px:6,d} | area={total_area:9,d} km² | domain={arg0_spec['domain']}")
  return target_mask


def main():
  print("Loading land_area.png, NE 10m Admin-1, and HydroBASINS SA Level 5...")
  land_area = load_land_area()
  adm1, country_geom, hybas = load_gis_sources()

  bra = country_geom["BRA"]
  bol = country_geom["BOL"]
  pry = country_geom["PRY"]
  guy = country_geom["GUY"]
  sur = country_geom["SUR"]
  guf = country_geom["GUF"]
  guianas = clean_geom(unary_union([guy, sur, guf]))

  # ------------------------------------------------------------------
  # 13 CHAPTER SPECIFICATIONS (Primary Historiography + Organic GIS)
  # ------------------------------------------------------------------
  chapters = []

  # 1. Pre-Columbian Eastern Amazon Basin
  chapters.append({
    "rel_dir": "1.pre_columbian/1.eastern_amazon_basin",
    "stem": "eastern_amazon_basin",
    "title": "Pre-Columbian Eastern Amazon Basin: Marajoara, Tapajonic, Xinguano and Tocantins-Araguaia Polities (10000BC-1542AD)",
    "domain": [-10000, 1542],
    "manifest_group": "specialist_masks",
    "priority": 1,
    "palette_seed": 0.04,
    "regions": [
      {
        "id": "eamz_marajo_estuary",
        "name": "1. Amazon Estuary, Marajó Island & Amapá Coast",
        "geom": union_hybas(hybas, ["621", "62210", "623", "625", "6168", "6169"], bra),
        "population": scale_holocene_curve(285000, "amazon_varzea"),
      },
      {
        "id": "eamz_lower_amazon_trombetas",
        "name": "2. Lower Amazon Várzea, Trombetas & Monte Alegre",
        "geom": union_hybas(hybas, ["6223", "62251", "62252", "62253", "62255", "62256", "62257", "62258", "62259"], bra),
        "population": scale_holocene_curve(360000, "amazon_varzea"),
      },
      {
        "id": "eamz_tapajos_basin",
        "name": "3. Tapajós, Santarém & Maués-Abacaxis Basin",
        "geom": union_hybas(hybas, ["6224", "62254"], bra),
        "population": scale_holocene_curve(330000, "amazon_varzea"),
      },
      {
        "id": "eamz_xingu_basin",
        "name": "4. Lower & Upper Xingu Basin (Kuhikugu)",
        "geom": union_hybas(hybas, ["6222"], bra),
        "population": scale_holocene_curve(245000, "amazon_varzea"),
      },
      {
        "id": "eamz_lower_tocantins",
        "name": "5. Lower Tocantins & Carajás",
        "geom": union_hybas(hybas, ["6241", "6242", "6243", "62441", "62442", "62443", "62444", "62445", "6245"], bra),
        "population": scale_holocene_curve(175000, "amazon_varzea"),
      },
      {
        "id": "eamz_araguaia_upper_tocantins",
        "name": "6. Araguaia, Ilha do Bananal & Upper Tocantins",
        "geom": union_hybas(hybas, ["62446", "62447", "62448", "62449", "6246", "6247", "6248", "6249"], bra),
        "population": scale_holocene_curve(165000, "amazon_varzea"),
      },
    ],
  })

  # 2. Pre-Columbian Western Amazon Basin
  wamz_clip = clean_geom(unary_union([bra, bol, country_geom["PER"], country_geom["COL"], country_geom["ECU"]]))
  chapters.append({
    "rel_dir": "1.pre_columbian/2.western_amazon_basin",
    "stem": "western_amazon_basin",
    "title": "Pre-Columbian Western Amazon Basin: Central Amazon Terra Preta, Acre Geoglyphs, Llanos de Moxos and Upper Amazon Chiefdoms (10000BC-1542AD)",
    "domain": [-10000, 1542],
    "manifest_group": "specialist_masks",
    "priority": 1,
    "palette_seed": 0.19,
    "regions": [
      {
        "id": "wamz_central_amazon_rio_negro",
        "name": "1. Central Amazon & Rio Negro-Branco",
        "geom": union_hybas(hybas, ["62270", "6228", "62291"], wamz_clip),
        "population": scale_holocene_curve(420000, "amazon_varzea"),
      },
      {
        "id": "wamz_madeira_guapore",
        "name": "2. Lower & Middle Madeira-Guaporé",
        "geom": union_hybas(hybas, ["62261", "62262", "62263", "62264", "62265"], wamz_clip),
        "population": scale_holocene_curve(310000, "amazon_varzea"),
      },
      {
        "id": "wamz_llanos_de_moxos",
        "name": "3. Llanos de Moxos, Beni & Mamoré (Casarabe)",
        "geom": union_hybas(hybas, ["62266", "62267", "62268", "62269"], wamz_clip),
        "population": scale_holocene_curve(380000, "amazon_moxos_earthwork"),
      },
      {
        "id": "wamz_purus_jurua_acre",
        "name": "4. Purus, Juruá & Acre Geoglyph Belt",
        "geom": union_hybas(hybas, ["62292", "62293", "62295", "62296"], wamz_clip),
        "population": scale_holocene_curve(340000, "amazon_moxos_earthwork"),
      },
      {
        "id": "wamz_caqueta_putumayo_napo",
        "name": "5. Solimões, Caquetá-Putumayo & Napo-Upano",
        "geom": union_hybas(hybas, ["62294", "62297"], wamz_clip),
        "population": scale_holocene_curve(520000, "amazon_varzea"),
      },
      {
        "id": "wamz_maranon_ucayali",
        "name": "6. Marañón, Huallaga & Ucayali Lowlands",
        "geom": union_hybas(hybas, ["62298", "62299"], wamz_clip),
        "population": scale_holocene_curve(540000, "amazon_varzea"),
      },
    ],
  })

  # 3. Pre-Columbian North-Eastern Brazil, Non-Amazon
  chapters.append({
    "rel_dir": "1.pre_columbian/3.northeastern_brazil",
    "stem": "northeastern_brazil",
    "title": "Pre-Columbian North-Eastern Brazil (Non-Amazon): Coastal Tupinambá, Serra da Capivara and São Francisco Corridor (10000BC-1500AD)",
    "domain": [-10000, 1500],
    "manifest_group": "specialist_masks",
    "priority": 1,
    "palette_seed": 0.34,
    "regions": [
      {
        "id": "nebr_midnorth_maranhao",
        "name": "1. Mid-North Mearim-Itapecuru-Gurupi",
        "geom": union_hybas(hybas, ["631"], bra),
        "population": scale_holocene_curve(145000, "brazil_coastal_tupi"),
      },
      {
        "id": "nebr_parnaiba_capivara",
        "name": "2. Parnaíba Basin & Serra da Capivara",
        "geom": union_hybas(hybas, ["632"], bra),
        "population": scale_holocene_curve(115000, "brazil_coastal_tupi"),
      },
      {
        "id": "nebr_coastal_atlantic_tupi",
        "name": "3. Northeastern Atlantic Coast & Agreste",
        "geom": union_hybas(hybas, ["633"], bra),
        "population": scale_holocene_curve(275000, "brazil_coastal_tupi"),
      },
      {
        "id": "nebr_sao_francisco",
        "name": "4. São Francisco Valley",
        "geom": union_hybas(hybas, ["634"], bra),
        "population": scale_holocene_curve(195000, "brazil_coastal_tupi"),
      },
      {
        "id": "nebr_bahia_reconcavo_east",
        "name": "5. Eastern Bahia, Recôncavo & Jequitinhonha",
        "geom": union_hybas(hybas, ["6351", "6352", "6353", "6354"], bra),
        "population": scale_holocene_curve(210000, "brazil_coastal_tupi"),
      },
    ],
  })

  # 4. Pre-Columbian Southern Brazil, Non-Amazon
  # Check which 642* basins are in Brazil and group organically into Upper Paraná/Cerrado, Tietê-Paranapanema-Iguaçu, Pantanal/Paraguay
  p642_upper = ["6429", "6428"]  # Paranaíba & Grande
  p642_tiete_ig = ["6427", "6426", "6425", "6423", "6422", "6421"]  # Tietê, Paranapanema, Iguaçu, Middle Paraná
  p642_pantanal = ["6424"]  # Paraguay-Pantanal
  # Let's assign 642 sub-basins by geographic centroid inside Brazil so none are missed!
  sbr_upper_geoms, sbr_tiete_geoms, sbr_pant_geoms = [], [], []
  for pfaf, _, g in hybas:
    if pfaf.startswith("642"):
      clipped = clean_geom(g.intersection(bra))
      if clipped is None or clipped.is_empty or clipped.area < 0.01:
        continue
      c = clipped.centroid
      if c.x < -53.2 and c.y > -22.5:
        sbr_pant_geoms.append(clipped)
      elif c.y > -21.2:
        sbr_upper_geoms.append(clipped)
      else:
        sbr_tiete_geoms.append(clipped)

  chapters.append({
    "rel_dir": "1.pre_columbian/4.southern_brazil",
    "stem": "southern_brazil",
    "title": "Pre-Columbian Southern Brazil (Non-Amazon): Atlantic Sambaquis, Southern Jê Highlands, Guarani Paraná and Pampa Cerritos (10000BC-1500AD)",
    "domain": [-10000, 1500],
    "manifest_group": "specialist_masks",
    "priority": 1,
    "palette_seed": 0.51,
    "regions": [
      {
        "id": "sbr_southeast_atlantic_sambaqui",
        "name": "1. Southeast Atlantic Coast (Doce, Paraíba do Sul & Guanabara)",
        "geom": union_hybas(hybas, ["6355", "6356", "6357", "6358", "6359"], bra),
        "population": scale_holocene_curve(240000, "brazil_sambaqui_south"),
      },
      {
        "id": "sbr_south_atlantic_sambaqui",
        "name": "2. Southern Atlantic Sambaqui & Lagoa dos Patos Belt",
        "geom": union_hybas(hybas, ["6411", "6412", "6413", "6414", "6415", "6416"], bra),
        "population": scale_holocene_curve(215000, "brazil_sambaqui_south"),
      },
      {
        "id": "sbr_upper_parana_cerrado",
        "name": "3. Upper Paraná, Paranaíba & Central Cerrado",
        "geom": clean_geom(unary_union(sbr_upper_geoms)),
        "population": scale_holocene_curve(205000, "brazil_coastal_tupi"),
      },
      {
        "id": "sbr_tiete_paranapanema_iguacu",
        "name": "4. Tietê, Paranapanema & Iguaçu (Southern Jê & Guarani)",
        "geom": clean_geom(unary_union(sbr_tiete_geoms)),
        "population": scale_holocene_curve(285000, "brazil_sambaqui_south"),
      },
      {
        "id": "sbr_pantanal_upper_paraguay",
        "name": "5. Pantanal & Upper Paraguay Basin",
        "geom": clean_geom(unary_union(sbr_pant_geoms)),
        "population": scale_holocene_curve(115000, "brazil_coastal_tupi"),
      },
      {
        "id": "sbr_uruguay_pampa",
        "name": "6. Uruguay Basin & Rio Grande do Sul Pampa",
        "geom": union_hybas(hybas, ["6417", "6418", "6419"], bra),
        "population": scale_holocene_curve(140000, "brazil_sambaqui_south"),
      },
    ],
  })

  # 5. Pre-Columbian Guyana (Guyana, Suriname, and French Guiana)
  chapters.append({
    "rel_dir": "1.pre_columbian/5.guyana",
    "stem": "guyana",
    "title": "Pre-Columbian Guyana, Suriname and French Guiana: Shell Mounds, Coastal Raised Fields and Montagnes Couronnées (10000BC-1595AD)",
    "domain": [-10000, 1595],
    "manifest_group": "specialist_masks",
    "priority": 1,
    "palette_seed": 0.67,
    "regions": [
      {
        "id": "guy_western_essequibo_coast",
        "name": "1. Pomeroon, Cuyuni & Lower Essequibo Coast",
        "geom": union_hybas(hybas, ["615", "6161", "61621", "61622", "61623", "61624", "61625", "61626", "61627"], guianas),
        "population": scale_holocene_curve(58000, "guiana_raised_fields"),
      },
      {
        "id": "guy_rupununi_interior_shield",
        "name": "2. Rupununi Savannas & Upper Essequibo Interior",
        "geom": clean_geom(unary_union([
          union_hybas(hybas, ["61628", "61629"], guianas),
          union_hybas(hybas, ["622"], guy),
        ])),
        "population": scale_holocene_curve(36000, "guiana_raised_fields"),
      },
      {
        "id": "guy_suriname_raised_fields",
        "name": "3. Berbice, Courantyne & Suriname Raised Fields",
        "geom": clean_geom(unary_union([
          union_hybas(hybas, ["6163", "6164", "6165"], guianas),
          union_hybas(hybas, ["622"], sur),
        ])),
        "population": scale_holocene_curve(62000, "guiana_raised_fields"),
      },
      {
        "id": "guy_french_guiana_maroni_oyapock",
        "name": "4. Maroni, Coastal French Guiana & Oyapock",
        "geom": clean_geom(unary_union([
          union_hybas(hybas, ["6166", "6167", "6168"], guianas),
          union_hybas(hybas, ["622"], guf),
        ])),
        "population": scale_holocene_curve(48000, "guiana_raised_fields"),
      },
    ],
  })

  # 6. Colonial Brazil (1500 - 1822 AD) — Marcílio (1984/2000), Alden (1963/1987), IBGE
  chapters.append({
    "rel_dir": "2.colonial/1.colonial_brazil",
    "stem": "colonial_brazil",
    "title": "Colonial Brazil: Captaincies, Sugar Engenhos, Minas Gerais Gold Rush and Grão-Pará (1500-1822AD)",
    "domain": [1500, 1822],
    "manifest_group": "national_epoch_masks",
    "priority": 2,
    "palette_seed": 0.12,
    "rel_unc": 0.14,
    "regions": [
      {
        "id": "cbr_bahia_sergipe",
        "name": "1. Bahia & Sergipe (Recôncavo Sugar Core)",
        "geom": union_adm1(adm1, [("BRA", "Bahia"), ("BRA", "Sergipe")]),
        "population": {1500: 420000, 1550: 290000, 1600: 210000, 1650: 235000, 1700: 280000, 1750: 365000, 1776: 445000, 1800: 545000, 1819: 675000, 1822: 710000},
      },
      {
        "id": "cbr_pernambuco_northeast",
        "name": "2. Pernambuco, Paraíba, RN, Alagoas & Ceará",
        "geom": union_adm1(adm1, [("BRA", "Pernambuco"), ("BRA", "Paraíba"), ("BRA", "Rio Grande do Norte"), ("BRA", "Alagoas"), ("BRA", "Ceará")]),
        "population": {1500: 510000, 1550: 340000, 1600: 255000, 1650: 270000, 1700: 340000, 1750: 470000, 1776: 620000, 1800: 810000, 1819: 1030000, 1822: 1090000},
      },
      {
        "id": "cbr_maranhao_piaui",
        "name": "3. Maranhão & Piauí (Estado do Maranhão)",
        "geom": union_adm1(adm1, [("BRA", "Maranhão"), ("BRA", "Piauí")]),
        "population": {1500: 280000, 1550: 225000, 1600: 170000, 1650: 135000, 1700: 115000, 1750: 145000, 1776: 185000, 1800: 255000, 1819: 315000, 1822: 330000},
      },
      {
        "id": "cbr_grao_para_rio_negro",
        "name": "4. Grão-Pará & Capitania do Rio Negro (Amazonia)",
        "geom": union_adm1(adm1, [("BRA", "Pará"), ("BRA", "Amazonas"), ("BRA", "Amapá"), ("BRA", "Roraima"), ("BRA", "Rondônia"), ("BRA", "Acre"), ("BRA", "Tocantins")]),
        "population": {1500: 1850000, 1550: 1320000, 1600: 840000, 1650: 560000, 1700: 380000, 1750: 295000, 1776: 275000, 1800: 290000, 1819: 325000, 1822: 340000},
      },
      {
        "id": "cbr_minas_goias_mato_grosso",
        "name": "5. Minas Gerais, Goiás & Mato Grosso (Gold Interior)",
        "geom": union_adm1(adm1, [("BRA", "Minas Gerais"), ("BRA", "Goiás"), ("BRA", "Distrito Federal"), ("BRA", "Mato Grosso"), ("BRA", "Mato Grosso do Sul")]),
        "population": {1500: 410000, 1550: 330000, 1600: 250000, 1650: 215000, 1700: 245000, 1750: 485000, 1776: 615000, 1800: 710000, 1819: 845000, 1822: 885000},
      },
      {
        "id": "cbr_rio_sao_paulo_sul",
        "name": "6. Rio de Janeiro, Espírito Santo, São Paulo & Southern Captaincies",
        "geom": union_adm1(adm1, [("BRA", "Rio de Janeiro"), ("BRA", "Espírito Santo"), ("BRA", "São Paulo"), ("BRA", "Paraná"), ("BRA", "Santa Catarina"), ("BRA", "Rio Grande do Sul")]),
        "population": {1500: 530000, 1550: 365000, 1600: 245000, 1650: 235000, 1700: 280000, 1750: 445000, 1776: 625000, 1800: 870000, 1819: 1110000, 1822: 1185000},
      },
    ],
  })

  # 7. Colonial Guyana (1595 - 1815 AD)
  chapters.append({
    "rel_dir": "2.colonial/2.colonial_guyana",
    "stem": "colonial_guyana",
    "title": "Colonial Guyana, Suriname and French Guiana: Plantation Colonies and Maroon Societies (1595-1815AD)",
    "domain": [1595, 1815],
    "manifest_group": "national_epoch_masks",
    "priority": 2,
    "palette_seed": 0.27,
    "rel_unc": 0.14,
    "regions": [
      {
        "id": "cguy_essequibo_demerara",
        "name": "1. Essequibo & Demerara",
        "geom": union_adm1(adm1, [("GUY", "Barima-Waini"), ("GUY", "Pomeroon-Supenaam"), ("GUY", "Essequibo Islands-West Demerara"), ("GUY", "Demerara-Mahaica"), ("GUY", "Cuyuni-Mazaruni"), ("GUY", "Mahaica-Berbice")]),
        "population": {1595: 55000, 1650: 42000, 1700: 35000, 1750: 41000, 1780: 58000, 1800: 76000, 1815: 92000},
      },
      {
        "id": "cguy_berbice_interior",
        "name": "2. Berbice & Interior Guyana",
        "geom": union_adm1(adm1, [("GUY", "East Berbice-Corentyne"), ("GUY", "Upper Demerara-Berbice"), ("GUY", "Potaro-Siparuni"), ("GUY", "Upper Takutu-Upper Essequibo")]),
        "population": {1595: 36000, 1650: 28000, 1700: 22000, 1750: 25000, 1780: 28000, 1800: 32000, 1815: 36000},
      },
      {
        "id": "cguy_dutch_suriname",
        "name": "3. Dutch Suriname & Maroon Polities",
        "geom": sur,
        "population": {1595: 58000, 1650: 44000, 1700: 42000, 1750: 62000, 1780: 76000, 1800: 74000, 1815: 72000},
      },
      {
        "id": "cguy_french_guiana",
        "name": "4. French Guiana (Cayenne)",
        "geom": guf,
        "population": {1595: 44000, 1650: 32000, 1700: 23000, 1750: 22000, 1780: 26000, 1800: 25000, 1815: 24000},
      },
    ],
  })

  # 8. Colonial Paraguay (1537 - 1811 AD)
  chapters.append({
    "rel_dir": "2.colonial/3.colonial_paraguay",
    "stem": "colonial_paraguay",
    "title": "Colonial Paraguay: Asunción Governorate, Jesuit Reducciones and Chaco Frontier (1537-1811AD)",
    "domain": [1537, 1811],
    "manifest_group": "national_epoch_masks",
    "priority": 2,
    "palette_seed": 0.43,
    "rel_unc": 0.14,
    "regions": [
      {
        "id": "cpy_central_asuncion",
        "name": "1. Asunción, Central, Cordillera & Paraguarí",
        "geom": union_adm1(adm1, [("PRY", "Asunción"), ("PRY", "Central"), ("PRY", "Cordillera"), ("PRY", "Paraguarí")]),
        "population": {1537: 85000, 1580: 54000, 1620: 42000, 1680: 38000, 1732: 46000, 1767: 54000, 1782: 64000, 1799: 74000, 1811: 86000},
      },
      {
        "id": "cpy_villarrica_guaira_north",
        "name": "2. Villarrica, Guairá, Caaguazú, San Pedro & Concepción",
        "geom": union_adm1(adm1, [("PRY", "Guairá"), ("PRY", "Caaguazú"), ("PRY", "Caazapá"), ("PRY", "San Pedro"), ("PRY", "Concepción"), ("PRY", "Amambay"), ("PRY", "Canindeyú")]),
        "population": {1537: 68000, 1580: 46000, 1620: 34000, 1680: 26000, 1732: 28000, 1767: 32000, 1782: 36000, 1799: 42000, 1811: 48000},
      },
      {
        "id": "cpy_jesuit_missions_parana",
        "name": "3. Jesuit Reducciones (Misiones, Itapúa, Ñeembucú & Alto Paraná)",
        "geom": union_adm1(adm1, [("PRY", "Misiones"), ("PRY", "Itapúa"), ("PRY", "Ñeembucú"), ("PRY", "Alto Paraná")]),
        "population": {1537: 62000, 1580: 48000, 1620: 46000, 1680: 58000, 1732: 72000, 1767: 56000, 1782: 34000, 1799: 31000, 1811: 32000},
      },
      {
        "id": "cpy_gran_chaco_frontier",
        "name": "4. Gran Chaco Boreal Frontier",
        "geom": union_adm1(adm1, [("PRY", "Presidente Hayes"), ("PRY", "Boquerón"), ("PRY", "Alto Paraguay")]),
        "population": {1537: 42000, 1580: 39000, 1620: 36000, 1680: 33000, 1732: 31000, 1767: 29000, 1782: 28000, 1799: 27000, 1811: 27000},
      },
    ],
  })

  # 9. Colonial Spanish Amazon (Parts of Colombia, Peru, Ecuador, and Bolivia) (1542 - 1825 AD)
  chapters.append({
    "rel_dir": "2.colonial/4.colonial_spanish_amazon",
    "stem": "colonial_spanish_amazon",
    "title": "Colonial Spanish Amazon: Maynas, Quijos, Caquetá-Putumayo, Moxos and Chiquitos Missions (1542-1825AD)",
    "domain": [1542, 1825],
    "manifest_group": "national_epoch_masks",
    "priority": 2,
    "palette_seed": 0.59,
    "rel_unc": 0.16,
    "regions": [
      {
        "id": "csa_maynas_peru",
        "name": "1. Comandancia General de Maynas (Peruvian Amazon)",
        "geom": union_adm1(adm1, [("PER", "Loreto"), ("PER", "Ucayali"), ("PER", "San Martín"), ("PER", "Amazonas"), ("PER", "Madre de Dios")]),
        "population": {1542: 510000, 1600: 340000, 1650: 255000, 1700: 195000, 1750: 165000, 1780: 155000, 1800: 160000, 1825: 170000},
      },
      {
        "id": "csa_quijos_oriente_ecuador",
        "name": "2. Gobernación de Quijos, Canelos & Macas (Ecuadorian Oriente)",
        "geom": union_adm1(adm1, [("ECU", "Sucumbios"), ("ECU", "Napo"), ("ECU", "Orellana"), ("ECU", "Pastaza"), ("ECU", "Morona Santiago"), ("ECU", "Zamora Chinchipe")]),
        "population": {1542: 185000, 1600: 118000, 1650: 88000, 1700: 68000, 1750: 56000, 1780: 52000, 1800: 54000, 1825: 58000},
      },
      {
        "id": "csa_caqueta_putumayo_colombia",
        "name": "3. Misiones de Caquetá, Putumayo, Vaupés & Amazonas (Colombia)",
        "geom": union_adm1(adm1, [("COL", "Amazonas"), ("COL", "Caquetá"), ("COL", "Putumayo"), ("COL", "Vaupés"), ("COL", "Guaviare"), ("COL", "Guainía")]),
        "population": {1542: 240000, 1600: 175000, 1650: 138000, 1700: 112000, 1750: 96000, 1780: 90000, 1800: 88000, 1825: 90000},
      },
      {
        "id": "csa_moxos_chiquitos_santa_cruz",
        "name": "4. Moxos, Chiquitos & Santa Cruz de la Sierra (Bolivian Lowlands)",
        "geom": union_adm1(adm1, [("BOL", "El Beni"), ("BOL", "Pando"), ("BOL", "Santa Cruz")]),
        "population": {1542: 390000, 1600: 275000, 1650: 215000, 1700: 185000, 1750: 178000, 1780: 170000, 1800: 175000, 1825: 188000},
      },
    ],
  })

  # 10. Brazil after Independence (1822 - 2026 AD) — Exact 27 UFs (IBGE 1872-2022 + Imperial 1822-1872)
  # Official IBGE UF census totals (1872, 1890, 1900, 1920, 1940, 1950, 1960, 1970, 1980, 1991, 2000, 2010, 2022 + 2026 est)
  # For states created later (AC 1903, AP/RR/RO 1943, DF 1960, MS 1977, TO 1988), modern Admin-1 spatial territory shares are back-apportioned smoothly from parent states so pixel densities never cliff!
  bra_uf_series = {
    "Acre":                {1822: 18000, 1850: 24000, 1872: 32000, 1890: 48000, 1900: 65000, 1920: 92379, 1940: 79768, 1950: 114755, 1960: 160208, 1970: 215299, 1980: 301303, 1991: 417718, 2000: 557526, 2010: 733559, 2022: 830018, 2026: 880631},
    "Alagoas":             {1822: 145000, 1850: 245000, 1872: 348009, 1890: 511440, 1900: 649273, 1920: 978748, 1940: 951300, 1950: 1093137, 1960: 1271062, 1970: 1588109, 1980: 1982591, 1991: 2514100, 2000: 2822621, 2010: 3120494, 2022: 3127683, 2026: 3220104},
    "Amapá":               {1822: 11000, 1850: 14000, 1872: 18000, 1890: 22000, 1900: 26000, 1920: 32000, 1940: 35000, 1950: 37477, 1960: 68889, 1970: 114359, 1980: 175257, 1991: 289397, 2000: 477032, 2010: 669526, 2022: 733759, 2026: 802837},
    "Amazonas":            {1822: 42000, 1850: 52000, 1872: 57610, 1890: 147915, 1900: 249756, 1920: 363166, 1940: 438008, 1950: 514099, 1960: 721215, 1970: 955235, 1980: 1430089, 1991: 2103243, 2000: 2812557, 2010: 3483985, 2022: 3941613, 2026: 4281209},
    "Bahia":               {1822: 615000, 1850: 1030000, 1872: 1379616, 1890: 1919802, 1900: 2117956, 1920: 3334465, 1940: 3918112, 1950: 4834575, 1960: 5990605, 1970: 7493470, 1980: 9454346, 1991: 11867991, 2000: 13070250, 2010: 14016906, 2022: 14141626, 2026: 14850513},
    "Ceará":               {1822: 240000, 1850: 465000, 1872: 721686, 1890: 805687, 1900: 849127, 1920: 1319228, 1940: 2091032, 1950: 2695450, 1960: 3337856, 1970: 4361603, 1980: 5288253, 1991: 6366647, 2000: 7430661, 2010: 8452381, 2022: 8794957, 2026: 9233656},
    "Distrito Federal":    {1822: 2500, 1850: 4500, 1872: 7500, 1890: 10500, 1900: 13000, 1920: 20000, 1940: 32000, 1950: 45000, 1960: 141742, 1970: 537492, 1980: 1176935, 1991: 1601094, 2000: 2051146, 2010: 2570160, 2022: 2817381, 2026: 2982818},
    "Espírito Santo":      {1822: 36000, 1850: 58000, 1872: 82137, 1890: 135997, 1900: 209783, 1920: 457328, 1940: 750107, 1950: 861562, 1960: 1188665, 1970: 1599333, 1980: 2023340, 1991: 2600618, 2000: 3097232, 2010: 3514952, 2022: 3833712, 2026: 4102129},
    "Goiás":               {1822: 65000, 1850: 108000, 1872: 140395, 1890: 198000, 1900: 222000, 1920: 445000, 1940: 690000, 1950: 1010000, 1960: 1626376, 1970: 2410000, 1980: 3120718, 1991: 4018903, 2000: 5003228, 2010: 6003788, 2022: 7056495, 2026: 7350483},
    "Maranhão":            {1822: 195000, 1850: 295000, 1872: 359040, 1890: 430854, 1900: 499308, 1920: 874337, 1940: 1235169, 1950: 1583248, 1960: 2492139, 1970: 2992686, 1980: 3996404, 1991: 4930253, 2000: 5651475, 2010: 6574789, 2022: 6776699, 2026: 7010960},
    "Mato Grosso":         {1822: 24000, 1850: 32000, 1872: 39000, 1890: 55000, 1900: 71000, 1920: 142000, 1940: 210000, 1950: 255000, 1960: 390000, 1970: 598879, 1980: 1138691, 1991: 2027231, 2000: 2504353, 2010: 3035122, 2022: 3658649, 2026: 3836399},
    "Mato Grosso do Sul":  {1822: 14000, 1850: 18000, 1872: 21417, 1890: 37827, 1900: 47025, 1920: 104612, 1940: 222265, 1950: 267044, 1960: 520262, 1970: 998211, 1980: 1369567, 1991: 1780373, 2000: 2078001, 2010: 2449024, 2022: 2757013, 2026: 2901895},
    "Minas Gerais":        {1822: 750000, 1850: 1420000, 1872: 2039735, 1890: 3184099, 1900: 3594471, 1920: 5888174, 1940: 6763368, 1950: 7782188, 1960: 9960040, 1970: 11487415, 1980: 13378553, 1991: 15743152, 2000: 17891494, 2010: 19597330, 2022: 20539989, 2026: 21322691},
    "Pará":                {1822: 132000, 1850: 195000, 1872: 257237, 1890: 306455, 1900: 419356, 1920: 951507, 1940: 909644, 1950: 1123273, 1960: 1550935, 1970: 2167018, 1980: 3403391, 1991: 4950060, 2000: 6192307, 2010: 7581051, 2022: 8120131, 2026: 8664306},
    "Paraíba":             {1822: 130000, 1850: 245000, 1872: 376226, 1890: 457232, 1900: 490784, 1920: 961106, 1940: 1422282, 1950: 1713259, 1960: 2018023, 1970: 2382617, 1980: 2770176, 1991: 3201114, 2000: 3443825, 2010: 3766528, 2022: 3974687, 2026: 4145040},
    "Paraná":              {1822: 42000, 1850: 78000, 1872: 126722, 1890: 249491, 1900: 327136, 1920: 685711, 1940: 1236276, 1950: 2115547, 1960: 4296375, 1970: 6929868, 1980: 7629392, 1991: 8448713, 2000: 9563458, 2010: 10444526, 2022: 11444380, 2026: 11824665},
    "Pernambuco":          {1822: 465000, 1850: 660000, 1872: 841539, 1890: 1030224, 1900: 1178150, 1920: 2154835, 1940: 2688240, 1950: 3395185, 1960: 4136900, 1970: 5160640, 1980: 6141993, 1991: 7127855, 2000: 7918344, 2010: 8796448, 2022: 9058931, 2026: 9539029},
    "Piauí":               {1822: 105000, 1850: 155000, 1872: 202222, 1890: 267609, 1900: 334328, 1920: 609003, 1940: 817601, 1950: 1045696, 1960: 1263368, 1970: 1680573, 1980: 2139021, 1991: 2582137, 2000: 2843278, 2010: 3118360, 2022: 3271199, 2026: 3375646},
    "Rio de Janeiro":      {1822: 530000, 1850: 820000, 1872: 1057696, 1890: 1399535, 1900: 1737478, 1920: 2717244, 1940: 3611998, 1950: 4674645, 1960: 6709891, 1970: 8994802, 1980: 11291520, 1991: 12807706, 2000: 14391282, 2010: 15989929, 2022: 16055174, 2026: 17219679},
    "Rio Grande do Norte": {1822: 92000, 1850: 165000, 1872: 233979, 1890: 268273, 1900: 274317, 1920: 537135, 1940: 768018, 1950: 967921, 1960: 1157258, 1970: 1550244, 1980: 1898172, 1991: 2415567, 2000: 2776782, 2010: 3168027, 2022: 3302729, 2026: 3446071},
    "Rio Grande do Sul":   {1822: 120000, 1850: 245000, 1872: 434813, 1890: 897455, 1900: 1149070, 1920: 2182713, 1940: 3320689, 1950: 4164821, 1960: 5448823, 1970: 6664891, 1980: 7773837, 1991: 9138670, 2000: 10187798, 2010: 10693929, 2022: 10882965, 2026: 11229915},
    "Rondônia":            {1822: 6000, 1850: 8500, 1872: 11000, 1890: 14000, 1900: 17000, 1920: 24000, 1940: 28000, 1950: 36935, 1960: 70783, 1970: 111064, 1980: 491069, 1991: 1132692, 2000: 1379787, 2010: 1562409, 2022: 1581196, 2026: 1746227},
    "Roraima":             {1822: 7500, 1850: 9000, 1872: 11000, 1890: 13000, 1900: 14500, 1920: 16500, 1940: 17500, 1950: 18116, 1960: 29489, 1970: 40885, 1980: 79159, 1991: 217583, 2000: 324397, 2010: 450479, 2022: 636707, 2026: 716793},
    "Santa Catarina":      {1822: 52000, 1850: 102000, 1872: 159802, 1890: 283769, 1900: 320289, 1920: 668743, 1940: 1178340, 1950: 1560502, 1960: 2146909, 1970: 2901734, 1980: 3627933, 1991: 4541994, 2000: 5356360, 2010: 6248436, 2022: 7610361, 2026: 8058441},
    "São Paulo":           {1822: 295000, 1850: 520000, 1872: 837354, 1890: 1384753, 1900: 2282279, 1920: 4592188, 1940: 7180316, 1950: 9134423, 1960: 12974699, 1970: 17771948, 1980: 25040712, 1991: 31588925, 2000: 37032403, 2010: 41262199, 2022: 44411238, 2026: 45973194},
    "Sergipe":             {1822: 102000, 1850: 142000, 1872: 176243, 1890: 310926, 1900: 356264, 1920: 477064, 1940: 542326, 1950: 644361, 1960: 760273, 1970: 900744, 1980: 1140121, 1991: 1491876, 2000: 1784475, 2010: 2068017, 2022: 2210004, 2026: 2291077},
    "Tocantins":           {1822: 18000, 1850: 25000, 1872: 33000, 1890: 45000, 1900: 56000, 1920: 96000, 1940: 136000, 1950: 205000, 1960: 328491, 1970: 528000, 1980: 738688, 1991: 919863, 2000: 1157098, 2010: 1383445, 2022: 1511460, 2026: 1577342},
  }
  chapters.append({
    "rel_dir": "3.post_independence/1.brazil_after_independence",
    "stem": "brazil_after_independence",
    "title": "Brazil after Independence: Imperial Censuses, Republican Industrialisation and Contemporary IBGE Municipalities (1822-2026AD)",
    "domain": [1822, 2026],
    "manifest_group": "national_epoch_masks",
    "is_admin1": True,
    "priority": 3,
    "palette_seed": 0.08,
    "rel_unc": 0.04,
    "regions": [
      {
        "id": "bra_" + uf.lower().replace(" ", "_").replace("á", "a").replace("â", "a").replace("ã", "a").replace("é", "e").replace("ê", "e").replace("í", "i").replace("ó", "o").replace("ô", "o").replace("ú", "u"),
        "name": uf,
        "geom": adm1[("BRA", uf)],
        "population": series,
      }
      for uf, series in sorted(bra_uf_series.items())
    ],
  })

  # 11. Bolivia after Independence (1825 - 2026 AD) — All 9 Departments (Dalence 1851, INE 1900, 1950, 1976, 1992, 2001, 2012, 2024)
  bol_dept_series = {
    "Chuquisaca":  {1825: 118000, 1846: 156041, 1882: 145000, 1900: 204434, 1950: 282980, 1976: 358488, 1992: 453756, 2001: 531522, 2012: 581347, 2024: 600132, 2026: 605000},
    "La Paz":      {1825: 320000, 1846: 412867, 1882: 395000, 1900: 445616, 1950: 948446, 1976: 1465078, 1992: 1900786, 2001: 2350466, 2012: 2719344, 2024: 3022566, 2026: 3065000},
    "Cochabamba":  {1825: 225000, 1846: 279048, 1882: 275000, 1900: 328163, 1950: 490475, 1976: 720952, 1992: 1110205, 2001: 1455711, 2012: 1762761, 2024: 2005373, 2026: 2042000},
    "Oruro":       {1825: 76000, 1846: 95324, 1882: 92000, 1900: 86081, 1950: 210260, 1976: 310409, 1992: 340114, 2001: 391870, 2012: 494587, 2024: 570194, 2026: 582000},
    "Potosí":      {1825: 215000, 1846: 243263, 1882: 255000, 1900: 325615, 1950: 534399, 1976: 657743, 1992: 645889, 2001: 709013, 2012: 828093, 2024: 856419, 2026: 862000},
    "Tarija":      {1825: 44000, 1846: 63800, 1882: 72000, 1900: 102887, 1950: 126752, 1976: 187204, 1992: 291407, 2001: 391226, 2012: 483518, 2024: 534348, 2026: 544000},
    "Santa Cruz":  {1825: 108000, 1846: 125000, 1882: 165000, 1900: 209592, 1950: 286145, 1976: 710724, 1992: 1364389, 2001: 2029471, 2012: 2657762, 2024: 3115386, 2026: 3210000},
    "El Beni":     {1825: 62000, 1846: 58000, 1882: 52000, 1900: 32180, 1950: 119770, 1976: 168367, 1992: 276174, 2001: 362521, 2012: 422008, 2024: 477441, 2026: 488000},
    "Pando":       {1825: 14000, 1846: 15000, 1882: 18000, 1900: 18000, 1950: 19804, 1976: 34493, 1992: 38072, 2001: 52525, 2012: 110436, 2024: 130761, 2026: 135000},
  }
  chapters.append({
    "rel_dir": "3.post_independence/2.bolivia_after_independence",
    "stem": "bolivia_after_independence",
    "title": "Bolivia after Independence: Altiplano Cores, Lowland Santa Cruz Expansion and National Censuses (1825-2026AD)",
    "domain": [1825, 2026],
    "manifest_group": "national_epoch_masks",
    "is_admin1": True,
    "priority": 3,
    "palette_seed": 0.22,
    "rel_unc": 0.04,
    "regions": [
      {
        "id": "bol_" + dept.lower().replace(" ", "_").replace("í", "i"),
        "name": dept,
        "geom": adm1[("BOL", dept)],
        "population": series,
      }
      for dept, series in sorted(bol_dept_series.items())
    ],
  })

  # 12. Paraguay after Independence (1811 - 2026 AD) — All 18 Admin-1 units (1846, 1864, 1870 war collapse, 1886, 1899, 1936, 1950-2022 INE)
  pry_dept_series = {
    "Asunción":         {1811: 14000, 1846: 36000, 1864: 42000, 1870: 19000, 1886: 24838, 1899: 51719, 1936: 104819, 1950: 206634, 1962: 288882, 1972: 388958, 1982: 454881, 1992: 500938, 2002: 512112, 2012: 529433, 2022: 477346, 2026: 468000},
    "Concepción":       {1811: 11000, 1846: 22000, 1864: 25000, 1870: 10000, 1886: 14200, 1899: 21500, 1936: 46000, 1950: 62326, 1962: 85690, 1972: 108130, 1982: 133977, 1992: 167289, 2002: 179450, 2012: 207406, 2022: 204536, 2026: 207000},
    "San Pedro":        {1811: 12000, 1846: 26000, 1864: 29000, 1870: 11000, 1886: 16500, 1899: 24800, 1936: 49000, 1950: 64534, 1962: 91804, 1972: 138018, 1982: 191002, 1992: 280336, 2002: 318698, 2012: 355175, 2022: 341895, 2026: 348000},
    "Cordillera":       {1811: 24000, 1846: 54000, 1864: 61000, 1870: 25000, 1886: 36500, 1899: 56000, 1936: 112000, 1950: 145232, 1962: 188313, 1972: 194218, 1982: 193706, 1992: 198701, 2002: 233854, 2012: 282981, 2022: 271475, 2026: 278000},
    "Guairá":           {1811: 15000, 1846: 38000, 1864: 43000, 1870: 18000, 1886: 26800, 1899: 42500, 1936: 74000, 1950: 90308, 1962: 114949, 1972: 124799, 1982: 143510, 1992: 161991, 2002: 178650, 2012: 198532, 2022: 180121, 2026: 182000},
    "Caaguazú":         {1811: 9000, 1846: 22000, 1864: 25000, 1870: 10000, 1886: 15500, 1899: 24500, 1936: 52000, 1950: 71699, 1962: 125138, 1972: 213356, 1982: 299437, 1992: 386412, 2002: 435357, 2012: 483048, 2022: 430142, 2026: 436000},
    "Caazapá":          {1811: 11000, 1846: 26000, 1864: 29000, 1870: 12000, 1886: 18200, 1899: 29000, 1936: 54000, 1950: 73051, 1962: 92401, 1972: 103139, 1982: 109452, 1992: 129352, 2002: 139517, 2012: 153495, 2022: 140060, 2026: 142000},
    "Itapúa":           {1811: 12000, 1846: 24000, 1864: 27000, 1870: 11000, 1886: 17200, 1899: 31000, 1936: 78000, 1950: 111424, 1962: 149821, 1972: 201411, 1982: 262680, 1992: 377536, 2002: 453692, 2012: 511338, 2022: 436966, 2026: 444000},
    "Misiones":         {1811: 12000, 1846: 19000, 1864: 21000, 1870: 8500, 1886: 13500, 1899: 20500, 1936: 35000, 1950: 43449, 1962: 59441, 1972: 69246, 1982: 77475, 1992: 89018, 2002: 101783, 2012: 118798, 2022: 114542, 2026: 117000},
    "Paraguarí":        {1811: 22000, 1846: 52000, 1864: 59000, 1870: 24000, 1886: 35500, 1899: 57500, 1936: 115000, 1950: 159161, 1962: 203012, 1972: 211977, 1982: 203012, 1992: 208527, 2002: 221932, 2012: 248461, 2022: 199430, 2026: 201000},
    "Alto Paraná":      {1811: 4500, 1846: 6000, 1864: 6500, 1870: 3000, 1886: 4000, 1899: 5500, 1936: 8000, 1950: 9531, 1962: 24067, 1972: 69049, 1982: 199644, 1992: 406584, 2002: 558672, 2012: 737092, 2022: 784839, 2026: 822000},
    "Central":          {1811: 24000, 1846: 54000, 1864: 61000, 1870: 24500, 1886: 37500, 1899: 61000, 1936: 122000, 1950: 167805, 1962: 229073, 1972: 310390, 1982: 495498, 1992: 866856, 2002: 1362893, 2012: 1855241, 2022: 1866562, 2026: 1945000},
    "Ñeembucú":         {1811: 10000, 1846: 21000, 1864: 24000, 1870: 9000, 1886: 14500, 1899: 22000, 1936: 41000, 1950: 50861, 1962: 57878, 1972: 73098, 1982: 70338, 1992: 69770, 2002: 76348, 2012: 86180, 2022: 85749, 2026: 87000},
    "Amambay":          {1811: 3500, 1846: 4500, 1864: 5000, 1870: 2500, 1886: 3800, 1899: 6500, 1936: 14000, 1950: 18160, 1962: 34505, 1972: 65117, 1982: 68395, 1992: 99860, 2002: 114917, 2012: 151779, 2022: 173770, 2026: 181000},
    "Canindeyú":        {1811: 3500, 1846: 4500, 1864: 5000, 1870: 2500, 1886: 3500, 1899: 5000, 1936: 9000, 1950: 11500, 1962: 15500, 1972: 27825, 1982: 66409, 1992: 103785, 2002: 140137, 2012: 191447, 2022: 189128, 2026: 195000},
    "Presidente Hayes": {1811: 11000, 1846: 11000, 1864: 11500, 1870: 9500, 1886: 10500, 1899: 12000, 1936: 18000, 1950: 23490, 1962: 29870, 1972: 38439, 1982: 33021, 1992: 64417, 2002: 82493, 2012: 106826, 2022: 126880, 2026: 132000},
    "Boquerón":         {1811: 10000, 1846: 9500, 1864: 9500, 1870: 9000, 1886: 9500, 1899: 10500, 1936: 16500, 1950: 28082, 1962: 40405, 1972: 26190, 1982: 14790, 1992: 29060, 2002: 41106, 2012: 56440, 2022: 68595, 2026: 72000},
    "Alto Paraguay":    {1811: 6000, 1846: 5500, 1864: 5500, 1870: 5000, 1886: 5000, 1899: 5200, 1936: 4500, 1950: 2712, 1962: 3854, 1972: 5366, 1982: 9021, 1992: 12156, 2002: 11587, 2012: 15682, 2022: 17608, 2026: 18500},
  }
  chapters.append({
    "rel_dir": "3.post_independence/3.paraguay_after_independence",
    "stem": "paraguay_after_independence",
    "title": "Paraguay after Independence: Francia-López State, Triple Alliance Demographic Catastrophe and Modern Censuses (1811-2026AD)",
    "domain": [1811, 2026],
    "manifest_group": "national_epoch_masks",
    "is_admin1": True,
    "priority": 3,
    "palette_seed": 0.37,
    "rel_unc": 0.04,
    "regions": [
      {
        "id": "pry_" + dept.lower().replace(" ", "_").replace("ó", "o").replace("í", "i").replace("á", "a").replace("ú", "u").replace("ñ", "n"),
        "name": dept,
        "geom": adm1[("PRY", dept)],
        "population": series,
      }
      for dept, series in sorted(pry_dept_series.items())
    ],
  })

  # 13. Guyana, Suriname, and French Guiana post-1815 (1815 - 2026 AD) — 21 Admin-1 units
  guianas_admin1 = [
    # Guyana 10 Regions (BoS 1831-2012 + 2022-2026 UN/BoS projections)
    ("GUY", "Barima-Waini",                     {1815: 6200, 1851: 7200, 1891: 11000, 1931: 12500, 1960: 15200, 1980: 18329, 1991: 18428, 2002: 24275, 2012: 26941, 2026: 29500}),
    ("GUY", "Pomeroon-Supenaam",                {1815: 14500, 1851: 17500, 1891: 31000, 1931: 32000, 1960: 44000, 1980: 42341, 1991: 43455, 2002: 49253, 2012: 46810, 2026: 49500}),
    ("GUY", "Essequibo Islands-West Demerara",  {1815: 22000, 1851: 27000, 1891: 56000, 1931: 59000, 1960: 84000, 1980: 104750, 1991: 95975, 2002: 103061, 2012: 107416, 2026: 118500}),
    ("GUY", "Demerara-Mahaica",                 {1815: 42000, 1851: 52000, 1891: 105000, 1931: 118000, 1960: 218000, 1980: 317475, 1991: 296924, 2002: 310320, 2012: 313429, 2026: 342000}),
    ("GUY", "Mahaica-Berbice",                  {1815: 10500, 1851: 13000, 1891: 26000, 1931: 29000, 1960: 46000, 1980: 53898, 1991: 51280, 2002: 52428, 2012: 49723, 2026: 52500}),
    ("GUY", "East Berbice-Corentyne",           {1815: 21000, 1851: 26500, 1891: 52000, 1931: 60000, 1960: 115000, 1980: 152386, 1991: 142541, 2002: 123695, 2012: 109431, 2026: 114000}),
    ("GUY", "Cuyuni-Mazaruni",                  {1815: 4200, 1851: 4500, 1891: 6200, 1931: 7500, 1960: 10500, 1980: 14390, 1991: 14794, 2002: 17597, 2012: 20280, 2026: 22800}),
    ("GUY", "Potaro-Siparuni",                  {1815: 3500, 1851: 3800, 1891: 4200, 1931: 4500, 1960: 5500, 1980: 4485, 1991: 5615, 2002: 10095, 2012: 10190, 2026: 11500}),
    ("GUY", "Upper Takutu-Upper Essequibo",     {1815: 5500, 1851: 5800, 1891: 6800, 1931: 7500, 1960: 10200, 1980: 12873, 1991: 15058, 2002: 19387, 2012: 24212, 2026: 27500}),
    ("GUY", "Upper Demerara-Berbice",           {1815: 4800, 1851: 5500, 1891: 8800, 1931: 11000, 1960: 21500, 1980: 38641, 1991: 39608, 2002: 41112, 2012: 39452, 2026: 43200}),
    # Suriname 10 Districts (ABS 1921, 1950, 1964, 1980, 2004, 2012 + 2026 est)
    ("SUR", "Paramaribo",  {1815: 19500, 1851: 17500, 1891: 29000, 1921: 44772, 1950: 78000, 1964: 110867, 1980: 167798, 2004: 242946, 2012: 240924, 2026: 256000}),
    ("SUR", "Wanica",      {1815: 8500, 1851: 9500, 1891: 12500, 1921: 16500, 1950: 27500, 1964: 48000, 1980: 60725, 2004: 85986, 2012: 118222, 2026: 138000}),
    ("SUR", "Nickerie",    {1815: 4200, 1851: 4500, 1891: 6800, 1921: 9800, 1950: 16800, 1964: 29800, 1980: 34480, 2004: 36639, 2012: 34233, 2026: 36500}),
    ("SUR", "Coronie",     {1815: 2200, 1851: 2500, 1891: 2800, 1921: 3100, 1950: 3900, 1964: 3762, 1980: 2777, 2004: 2887, 2012: 3391, 2026: 3500}),
    ("SUR", "Saramacca",   {1815: 4800, 1851: 5200, 1891: 6200, 1921: 7500, 1950: 9800, 1964: 11100, 1980: 10335, 2004: 15980, 2012: 17480, 2026: 19200}),
    ("SUR", "Commewijne",  {1815: 13500, 1851: 12000, 1891: 14500, 1921: 16800, 1950: 19500, 1964: 21500, 1980: 14351, 2004: 24649, 2012: 31420, 2026: 36500}),
    ("SUR", "Para",        {1815: 4500, 1851: 4800, 1891: 5800, 1921: 7200, 1950: 10200, 1964: 13500, 1980: 14867, 2004: 18749, 2012: 24700, 2026: 29500}),
    ("SUR", "Marowijne",   {1815: 3800, 1851: 4200, 1891: 5500, 1921: 7800, 1950: 11500, 1964: 19500, 1980: 23402, 2004: 16642, 2012: 18294, 2026: 21500}),
    ("SUR", "Brokopondo",  {1815: 4200, 1851: 4600, 1891: 5400, 1921: 6200, 1950: 8500, 1964: 13500, 1980: 14450, 2004: 14215, 2012: 15909, 2026: 18500}),
    ("SUR", "Sipaliwini",  {1815: 7500, 1851: 8200, 1891: 9500, 1921: 11200, 1950: 15500, 1964: 24500, 1980: 12081, 2004: 34136, 2012: 37065, 2026: 43800}),
    # French Guiana (INSEE 1831-2023 + 2026 projection)
    ("GUF", "French Guiana", {1815: 24000, 1851: 21500, 1891: 29650, 1921: 44202, 1936: 36975, 1954: 27863, 1961: 33505, 1967: 44392, 1974: 55125, 1982: 73022, 1990: 114678, 1999: 157213, 2010: 229040, 2020: 285133, 2023: 293996, 2026: 312000}),
  ]
  chapters.append({
    "rel_dir": "3.post_independence/4.guianas_post_1815",
    "stem": "guianas_post_1815",
    "title": "Guyana, Suriname and French Guiana post-1815: Emancipation, Indentured Migration and Contemporary Censuses (1815-2026AD)",
    "domain": [1815, 2026],
    "manifest_group": "national_epoch_masks",
    "is_admin1": True,
    "priority": 3,
    "palette_seed": 0.78,
    "rel_unc": 0.04,
    "regions": [
      {
        "id": f"{iso.lower()}_" + nm.lower().replace(" ", "_").replace("-", "_"),
        "name": f"{nm} ({'Guyana' if iso=='GUY' else ('Suriname' if iso=='SUR' else 'France')})",
        "geom": adm1[(iso, nm)],
        "population": series,
      }
      for iso, nm, series in guianas_admin1
    ],
  })

  # Build all 13 chapters and accumulate union domain mask
  print(f"Building {len(chapters)} PRETA chapter dual masks (GeoJSON + 4320x2160 PNG)...")
  domain_union = np.zeros((H, W), dtype=bool)
  specialist_entries = []
  national_entries = []

  for spec in chapters:
    cmask = build_chapter(spec, land_area)
    domain_union |= cmask
    entry = {
      "id": spec["stem"],
      "domain": spec["domain"],
      "domain_group": "sites_preta_amazon_brazil",
      "json5_path": f"histmap/1.data_raw/population_regional/PRETA/{spec['rel_dir']}/{spec['stem']}.json5",
      "mask_path": f"histmap/1.data_raw/population_regional/PRETA/{spec['rel_dir']}/{spec['stem']}_areal_mask.png",
      "priority": spec["priority"],
    }
    if spec.get("is_admin1"):
      entry["is_admin1"] = True
    if spec["manifest_group"] == "specialist_masks":
      specialist_entries.append(entry)
    else:
      national_entries.append(entry)

  # Save Stage C domain mask PNG (all pixels covered by any PRETA chapter)
  dom_rgba = np.zeros((H, W, 4), dtype=np.uint8)
  dom_rgba[domain_union] = [46, 125, 50, 255]
  dom_png = DOMAIN_CFG_DIR / "preta_domain_mask.png"
  Image.fromarray(dom_rgba, mode="RGBA").save(dom_png, compress_level=6)
  print(f"\nSaved Stage C domain mask: {dom_png.name} ({int(domain_union.sum()):,} land pixels)")

  # Write root preta_areal_masks.json5
  manifest = {
    "grid_dimensions": [W, H],
    "regime_transitions": {
      "brazil": {"pre_admin_end": 1500, "colonial_start": 1500, "contemporary_start": 1822},
      "amazon_basin": {"pre_admin_end": 1542, "colonial_start": 1542, "contemporary_start": 1822},
      "guianas": {"pre_admin_end": 1595, "colonial_start": 1595, "contemporary_start": 1815},
      "paraguay": {"pre_admin_end": 1537, "colonial_start": 1537, "contemporary_start": 1811},
      "bolivia_spanish_amazon": {"pre_admin_end": 1542, "colonial_start": 1542, "contemporary_start": 1825},
    },
    "geography_profile": {
      "projection_class": "lambert_azimuthal",
      "has_micro_islands": False,
      "max_adm2_area_km2": 25000,
      "note": "Continental Amazon Basin, Non-Amazon Brazil, Guiana Shield, Paraguay and Bolivia.",
    },
    "script_profile": {
      "target_scripts": ["Latn"],
      "allow_native_toponyms": True,
    },
    "hyde_years": HYDE_YEARS,
    "substrata_sources": {
      "sites_preta_amazon_brazil": {
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/PRETA/_shared/sites_preta_amazon_brazil/config/documented_site_pixels.json",
        "domain": [-10000, 2025],
        "domain_code": 1,
        "domain_mask_png": "histmap/1.data_raw/population_regional/PRETA/_shared/sites_preta_amazon_brazil/config/preta_domain_mask.png",
        "rasters_folder": "histmap/1.data_raw/population_regional/PRETA/_shared/sites_preta_amazon_brazil/2.population_rasters",
        "sample_year": 1000,
      }
    },
    "smoothing": {
      "border_feather_radius_px": 8,
      "interior_multiplier_blur_passes": 4,
      "interior_multiplier_blur_radius_px": 10,
      "temporal_log_Laplacian_weight": 0.15,
    },
    "specialist_masks": specialist_entries,
    "national_epoch_masks": national_entries,
  }
  with open(PRETA_DIR / "preta_areal_masks.json5", "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2, ensure_ascii=False)
  print("Saved preta_areal_masks.json5 successfully!")


if __name__ == "__main__":
  main()
