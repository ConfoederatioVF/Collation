"""Deterministic 5-arcminute (4320x2160) organic watershed, ecozone, and .naissance
historical GIS areal mask builder for Operation Viscount Project CENTAUR-II (31 modules).
Zero synthetic LAT/LON straight cuts; 100% sovereign land_area > 0 coverage.
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
CENTAUR_DIR = pathlib.Path(__file__).resolve().parents[2]
SVEA_ROOT = CENTAUR_DIR.parents[3]
CACHE_DIR = pathlib.Path(__file__).resolve().parent
HIST_DIR = CACHE_DIR / "historical_layers"
HB_DIR = CACHE_DIR / "hydrobasins"
SUBREG_OUT_DIR = CACHE_DIR / "chapter_subregions"

LAND_AREA_PNG = SVEA_ROOT / "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png"
ISO2_PNG = SVEA_ROOT / "histmap/1.data_raw/admin_modern/iso2.png"
ISO2_CSV = SVEA_ROOT / "histmap/1.data_raw/admin_modern/iso2_geocodes.csv"
WMOBB_JSON = SVEA_ROOT / "histmap/1.data_raw/watersheds_WMO/wmobb_basins.json"
HUC2_JSON = CACHE_DIR / "usgs_wbd_huc2.geojson"
HUC4_JSON = CACHE_DIR / "usgs_wbd_huc4.geojson"
HUC6_EXTRA_JSON = CACHE_DIR / "usgs_wbd_huc6_extra.geojson"
CA_ECOREG_JSON = CACHE_DIR / "canada_ecoregions.geojson"
HAWAII_MOKU_JSON = CACHE_DIR / "hawaii_moku.geojson"
NE10_ADM1_JSON = CACHE_DIR / "ne_10m_admin_1_states_provinces.geojson"
NE10_ADM0_JSON = CACHE_DIR / "ne_10m_admin_0_countries.geojson"


def distinct_palette(n, seed_offset=0.0):
  """Generates n visually distinct bright-to-mid RGB colours (never pure 0,0,0)."""
  cols = []
  used = {(0, 0, 0)}
  for i in range(n):
    hue = (seed_offset + i * 0.618033988749895) % 1.0
    sat = 0.58 + 0.25 * ((i % 3) / 2.0)
    val = 0.72 + 0.20 * (((i // 3) % 3) / 2.0)
    r, g, b = [max(16, min(245, int(round(c * 255)))) for c in colorsys.hsv_to_rgb(hue, sat, val)]
    while (r, g, b) in used:
      r = (r + 17) % 230 + 20
      g = (g + 29) % 230 + 20
    used.add((r, g, b))
    cols.append([r, g, b])
  return cols


def rasterize_geom_list(geom_id_pairs):
  """Rasterizes [(int_id, shapely_geom), ...] onto (H, W) int32 array using PIL polygon fill."""
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

  for gid, geom in geom_id_pairs:
    if geom is None or geom.is_empty:
      continue
    if geom.geom_type == "Polygon":
      draw_poly(geom, gid)
    elif geom.geom_type in ("MultiPolygon", "GeometryCollection"):
      for part in geom.geoms:
        if part.geom_type == "Polygon":
          draw_poly(part, gid)
  return np.asarray(img, dtype=np.int32)


def nearest_fill(target_mask, label_grid, valid_labels):
  """Assigns any True pixel in target_mask not yet in valid_labels to nearest valid pixel."""
  src_mask = np.isin(label_grid, list(valid_labels))
  missing = target_mask & (~src_mask)
  if not missing.any() or not src_mask.any():
    return label_grid
  sr, sc = np.where(src_mask)
  mr, mc = np.where(missing)
  tree = cKDTree(np.column_stack([sr, sc]))
  _, idx = tree.query(np.column_stack([mr, mc]))
  out = label_grid.copy()
  out[mr, mc] = label_grid[sr[idx], sc[idx]]
  return out


def ordered_raster_partition(target_mask, rules):
  """Evaluates ordered [(gid, shapely_geom), ...] strictly on pixel grid without LAT/LON cuts."""
  out = np.zeros((H, W), dtype=np.int32)
  gids = [gid for gid, _ in rules]
  for gid, geom in rules:
    if geom is None or geom.is_empty:
      continue
    r_grid = rasterize_geom_list([(gid, geom)])
    sel = target_mask & (out == 0) & (r_grid == gid)
    out[sel] = gid
  out = np.where(target_mask, out, 0)
  return nearest_fill(target_mask, out, gids)


def compute_zone_stats(mask_2d, land_area):
  """Computes pixel count, exact land_area km2, and bounding box from boolean 2D mask."""
  rs, cs = np.where(mask_2d)
  if len(rs) == 0:
    return 0, 0, None
  lats = 90.0 - (rs + 0.5) / 12.0
  lons = -180.0 + (cs + 0.5) / 12.0
  px_cnt = int(len(rs))
  area_km2 = int(round(float(land_area[rs, cs].sum())))
  bbox = {
    "min_lat": round(float(lats.min()), 2),
    "max_lat": round(float(lats.max()), 2),
    "min_lon": round(float(lons.min()), 2),
    "max_lon": round(float(lons.max()), 2),
  }
  return px_cnt, area_km2, bbox


def export_vector_subregions(stem, zone_defs, geom_by_gid, clip_geom=None, priority_order=None):
  """Writes disjoint crisp vector sub-region polygons for Stage D equal-area mapping."""
  SUBREG_OUT_DIR.mkdir(parents=True, exist_ok=True)
  by_gid_def = {z["gid"]: z for z in zone_defs}
  ordered_gids = list(priority_order) if priority_order else [z["gid"] for z in zone_defs]
  claimed = Polygon()
  feats = []
  for gid in ordered_gids:
    z = by_gid_def.get(gid)
    g = geom_by_gid.get(gid)
    if z is None or g is None or g.is_empty:
      continue
    if clip_geom is not None and not clip_geom.is_empty:
      g = g.intersection(clip_geom).buffer(0)
    if not claimed.is_empty:
      g = g.difference(claimed).buffer(0)
    if g.is_empty:
      continue
    claimed = u_geoms([claimed, g])
    try:
      g_simp = g.simplify(0.015, preserve_topology=True).buffer(0)
      if not g_simp.is_empty:
        g = g_simp
    except Exception:
      pass
    feats.append({
      "type": "Feature",
      "properties": {
        "gid": gid,
        "region_id": z["key"],
        "name": z["name"],
        "colour": z["colour"],
      },
      "geometry": mapping(g),
    })
  out_p = SUBREG_OUT_DIR / f"{stem}_subregions.geojson"
  out_p.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")


def write_mask_and_json5(out_dir, stem, meta_info, zone_defs, label_grid, land_area, geom_by_gid=None, clip_geom=None, priority_order=None):
  """Writes <stem>_areal_mask.png and updates <stem>.json5 while preserving calibrated populations."""
  out_dir = pathlib.Path(out_dir)
  out_dir.mkdir(parents=True, exist_ok=True)
  png_path = out_dir / f"{stem}_areal_mask.png"
  json5_path = out_dir / f"{stem}.json5"

  prev_doc = {}
  if json5_path.is_file():
    try:
      import json5 as j5
      prev_doc = j5.loads(json5_path.read_text(encoding="utf-8"))
    except Exception:
      prev_doc = {}
  prev_regions = prev_doc.get("regions") if isinstance(prev_doc.get("regions"), dict) else {}

  rgba = np.zeros((H, W, 4), dtype=np.uint8)
  regions_dict = {}
  total_px = 0
  total_area = 0

  for z in zone_defs:
    gid = z["gid"]
    m = (label_grid == gid)
    px_cnt, area_km2, bbox = compute_zone_stats(m, land_area)
    if px_cnt == 0:
      print(f"  [WARN] Zero pixels for {stem} -> {z['key']}!")
      continue
    col = z["colour"]
    rgba[m, 0] = col[0]
    rgba[m, 1] = col[1]
    rgba[m, 2] = col[2]
    rgba[m, 3] = 255
    total_px += px_cnt
    total_area += area_km2
    prev_r = prev_regions.get(z["key"], {})
    entry = {
      "name": z["name"],
      "colour": col,
      "pixel_count": px_cnt,
      "area_km2": area_km2,
      "bbox": bbox,
      "population": z.get("population") or prev_r.get("population", {}),
    }
    if prev_r.get("population_bounds"):
      entry["population_bounds"] = prev_r["population_bounds"]
    if prev_r.get("benchmark_anchors"):
      entry["benchmark_anchors"] = prev_r["benchmark_anchors"]
    if z.get("domain"):
      entry["domain"] = z["domain"]
    regions_dict[z["key"]] = entry

  Image.fromarray(rgba, mode="RGBA").save(png_path, compress_level=6)

  doc = {
    "id": stem,
    "title": meta_info["title"],
    "source_review": f"histmap/1.data_raw/population_regional/CENTAUR/{meta_info['rel_dir']}/{stem}_literature_review.md",
    "settlements_gazetteer": f"histmap/1.data_raw/population_regional/CENTAUR/{meta_info['rel_dir']}/{stem}_settlements.json",
    "mask_file": f"{stem}_areal_mask.png",
    "domain": meta_info["domain"],
    "grid_dimensions": [W, H],
    "total_pixels": total_px,
    "total_area_km2": total_area,
    "regions": regions_dict,
  }
  if prev_doc.get("summary"):
    doc["summary"] = prev_doc["summary"]
  json5_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

  if geom_by_gid:
    export_vector_subregions(stem, zone_defs, geom_by_gid, clip_geom=clip_geom, priority_order=priority_order)

  print(f"Wrote {meta_info['rel_dir']}/{stem}: {len(regions_dict)} zones, {total_px} px, {total_area:,} km2")
  return total_px, total_area


def u_geoms(geom_list):
  """Safe shapely unary_union helper returning Polygon/MultiPolygon."""
  valid = [g.buffer(0) for g in geom_list if g is not None and not g.is_empty]
  if not valid:
    return Polygon()
  return unary_union(valid).buffer(0)


def load_hydrobasins_by_pfaf(shp_name):
  """Loads simplified (0.01 deg) HydroBASINS shapefile keyed by integer PFAF_ID -> shapely geometry."""
  sf = shapefile.Reader(str(HB_DIR / shp_name))
  raw = {}
  for rec in sf.iterShapeRecords():
    pf = int(rec.record["PFAF_ID"])
    g = shape(rec.shape.__geo_interface__).simplify(0.012, preserve_topology=True).buffer(0)
    raw.setdefault(pf, []).append(g)
  return {pf: u_geoms(lst) for pf, lst in raw.items()}


def load_naissance_map(tag):
  """Loads historical polity snapshot keyed by string ID and list by name."""
  gj = json.loads((HIST_DIR / f"atlas_na_{tag}.geojson").read_text(encoding="utf-8"))
  by_id_raw = {}
  by_name_raw = {}
  for ft in gj["features"]:
    pr = ft["properties"]
    pid = str(pr.get("id", ""))
    nm = str(pr.get("name", ""))
    g = shape(ft["geometry"]).simplify(0.012, preserve_topology=True).buffer(0)
    if pid:
      by_id_raw.setdefault(pid, []).append(g)
    if nm:
      by_name_raw.setdefault(nm, []).append(g)
  return (
    {pid: u_geoms(lst) for pid, lst in by_id_raw.items()},
    {nm: u_geoms(lst) for nm, lst in by_name_raw.items()},
  )


def main():
  print("Loading base rasters and organic GIS layers...")
  la_img = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  land_area = (
    (la_img[:, :, 0].astype(np.uint32) << 24)
    | (la_img[:, :, 1].astype(np.uint32) << 16)
    | (la_img[:, :, 2].astype(np.uint32) << 8)
    | la_img[:, :, 3].astype(np.uint32)
  )
  land_area_eff = land_area.copy()
  land_area_eff[692, 1382] = 53  # Bermuda GHSL cell

  iso_img = np.asarray(Image.open(ISO2_PNG).convert("RGBA"), dtype=np.uint8)
  iso_rgb_to_code = {}
  with open(ISO2_CSV, encoding="utf-8") as fh:
    next(fh, None)
    for line in fh:
      parts = line.strip().split(";")
      if len(parts) >= 4 and parts[3]:
        rgb = tuple(int(x) for x in parts[3].split(","))
        iso_rgb_to_code[rgb] = (parts[0], parts[2])

  valid_iso_alpha = iso_img[:, :, 3] > 0
  packed_iso = (
    (iso_img[:, :, 0].astype(np.int32) << 16)
    | (iso_img[:, :, 1].astype(np.int32) << 8)
    | iso_img[:, :, 2].astype(np.int32)
  )
  rgb_int_to_code = {(r << 16) | (g << 8) | b: v[0] for (r, g, b), v in iso_rgb_to_code.items()}

  code_masks = {}
  other_sovereign_mask = np.zeros((H, W), dtype=bool)
  for rgb_int, code in rgb_int_to_code.items():
    m = valid_iso_alpha & (packed_iso == rgb_int) & (land_area > 0)
    if code.startswith("US-") or code in ("CA", "GL", "PM", "AS"):
      code_masks[code] = m
    else:
      other_sovereign_mask |= m

  bm_mask = np.zeros((H, W), dtype=bool)
  bm_mask[692, 1382] = True
  code_masks["BM"] = bm_mask

  # Build 100% complete Natural Earth 10m sovereign country geometries (batch-union + 0.01 deg simplify for speed)
  ne0_gj = json.loads(NE10_ADM0_JSON.read_text(encoding="utf-8"))
  adm0_raw = {}
  for feat in ne0_gj["features"]:
    adm = feat["properties"].get("ADMIN", "")
    if adm in ("Canada", "United States of America", "Greenland", "Saint Pierre and Miquelon", "American Samoa", "Bermuda"):
      g = shape(feat["geometry"]).simplify(0.01, preserve_topology=True).buffer(0)
      if adm == "United States of America":
        parts = [g] if g.geom_type == "Polygon" else list(g.geoms)
        kept = []
        for p in parts:
          cx, cy = p.centroid.x, p.centroid.y
          if -70.0 < cx < 0.0 and cy < 30.0:
            continue
          if 130.0 < cx < 170.0 and 10.0 < cy < 25.0:
            continue
          kept.append(p)
        g = u_geoms(kept)
      adm0_raw.setdefault(adm, []).append(g)
  adm0_geoms = {k: u_geoms(v) for k, v in adm0_raw.items()}

  ne_adm1 = json.loads(NE10_ADM1_JSON.read_text(encoding="utf-8"))
  ca_raw, us_raw = {}, {}
  for feat in ne_adm1["features"]:
    pr = feat["properties"]
    a3 = pr.get("adm0_a3")
    nm = pr.get("name", "")
    if a3 in ("CAN", "USA"):
      g = shape(feat["geometry"]).simplify(0.01, preserve_topology=True).buffer(0)
      if a3 == "CAN":
        ca_raw.setdefault(nm, []).append(g)
      else:
        us_raw.setdefault(nm, []).append(g)
  ca_provs = {k: u_geoms(v) for k, v in ca_raw.items()}
  us_states_poly = {k: u_geoms(v) for k, v in us_raw.items()}

  us_lower48_geom = u_geoms([g for nm, g in us_states_poly.items() if nm not in ("Alaska", "Hawaii")])
  us_ak_geom = us_states_poly.get("Alaska", Polygon())
  us_hi_geom = us_states_poly.get("Hawaii", Polygon())
  ca_all_geom = adm0_geoms.get("Canada", Polygon())
  gl_all_geom = adm0_geoms.get("Greenland", Polygon())
  pm_all_geom = adm0_geoms.get("Saint Pierre and Miquelon", Polygon())
  as_all_geom = adm0_geoms.get("American Samoa", Polygon())

  # Fill any unowned land_area > 0 pixels inside sovereign NE10 country bounds into the respective iso mask
  adm0_rast = rasterize_geom_list([
    (1, us_lower48_geom),
    (2, us_ak_geom),
    (3, ca_all_geom),
    (4, gl_all_geom),
    (5, pm_all_geom),
    (6, us_hi_geom),
    (7, as_all_geom),
  ])
  # Strictly exclude pixels already owned by Mexico/Cuba/Bahamas/Russia/Iceland in iso2.png
  free_land = (land_area > 0) & (~other_sovereign_mask)

  us_lower48_codes = [c for c in code_masks if c.startswith("US-") and c not in ("US-AK", "US-HI")]
  mask_us48 = np.zeros((H, W), dtype=bool)
  for c in us_lower48_codes:
    mask_us48 |= code_masks[c]
  mask_ak = code_masks["US-AK"]
  mask_hi = code_masks["US-HI"]
  mask_ca = code_masks["CA"]
  mask_gl = code_masks["GL"]
  mask_pm = code_masks["PM"]
  mask_as = code_masks["AS"]
  mask_bm = code_masks["BM"]

  mask_us48 |= free_land & (adm0_rast == 1) & (~mask_ca)
  mask_ak |= free_land & (adm0_rast == 2)
  mask_ca |= free_land & (adm0_rast == 3) & (~mask_us48) & (~mask_ak)
  mask_gl |= free_land & (adm0_rast == 4) & (~mask_ca)
  mask_pm |= free_land & (adm0_rast == 5)
  mask_hi |= free_land & (adm0_rast == 6)
  mask_as |= free_land & (adm0_rast == 7)

  # Enforce strictly disjoint continental land masks so zero overlaps occur
  mask_ca &= ~mask_us48 & ~mask_ak
  mask_gl &= ~mask_ca
  mask_pm &= ~mask_ca
  print(
    f"De-holed pixels -> US48: {mask_us48.sum()}, AK: {mask_ak.sum()}, "
    f"CA: {mask_ca.sum()}, GL: {mask_gl.sum()}, HI: {mask_hi.sum()}, PM: {mask_pm.sum()}, AS: {mask_as.sum()}"
  )

  # Assign US state grid over full de-holed mask_us48 | mask_ak | mask_hi
  us_state_names = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
    "Delaware", "District of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois",
    "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts",
    "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota",
    "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
    "Wisconsin", "Wyoming",
  ]
  us_abbr = {
    "US-AL": "Alabama", "US-AK": "Alaska", "US-AZ": "Arizona", "US-AR": "Arkansas",
    "US-CA": "California", "US-CO": "Colorado", "US-CT": "Connecticut", "US-DE": "Delaware",
    "US-DC": "District of Columbia", "US-FL": "Florida", "US-GA": "Georgia", "US-HI": "Hawaii",
    "US-ID": "Idaho", "US-IL": "Illinois", "US-IN": "Indiana", "US-IA": "Iowa",
    "US-KS": "Kansas", "US-KY": "Kentucky", "US-LA": "Louisiana", "US-ME": "Maine",
    "US-MD": "Maryland", "US-MA": "Massachusetts", "US-MI": "Michigan", "US-MN": "Minnesota",
    "US-MS": "Mississippi", "US-MO": "Missouri", "US-MT": "Montana", "US-NE": "Nebraska",
    "US-NV": "Nevada", "US-NH": "New Hampshire", "US-NJ": "New Jersey", "US-NM": "New Mexico",
    "US-NY": "New York", "US-NC": "North Carolina", "US-ND": "North Dakota", "US-OH": "Ohio",
    "US-OK": "Oklahoma", "US-OR": "Oregon", "US-PA": "Pennsylvania", "US-RI": "Rhode Island",
    "US-SC": "South Carolina", "US-SD": "South Dakota", "US-TN": "Tennessee", "US-TX": "Texas",
    "US-UT": "Utah", "US-VT": "Vermont", "US-VA": "Virginia", "US-WA": "Washington",
    "US-WV": "West Virginia", "US-WI": "Wisconsin", "US-WY": "Wyoming",
  }
  us_state_idx = {nm: i + 1 for i, nm in enumerate(us_state_names)}
  us_state_rast = rasterize_geom_list([(us_state_idx[nm], us_states_poly[nm]) for nm in us_state_names if nm in us_states_poly])
  us_state_grid = np.zeros((H, W), dtype=np.int32)
  for code, nm in us_abbr.items():
    if code in code_masks:
      us_state_grid[code_masks[code]] = us_state_idx[nm]
  unfilled_us = (mask_us48 | mask_ak | mask_hi) & (us_state_grid == 0)
  us_state_grid[unfilled_us] = us_state_rast[unfilled_us]
  us_state_grid = nearest_fill(mask_us48 | mask_ak | mask_hi, us_state_grid, range(1, len(us_state_names) + 1))

  # Canadian provinces
  ca_prov_order = [
    "Alberta", "British Columbia", "Manitoba", "New Brunswick",
    "Newfoundland and Labrador", "Northwest Territories", "Nova Scotia",
    "Nunavut", "Ontario", "Prince Edward Island", "Québec", "Saskatchewan", "Yukon",
  ]
  ca_prov_idx = {nm: i + 1 for i, nm in enumerate(ca_prov_order)}
  ca_prov_grid = rasterize_geom_list([(i + 1, ca_provs[nm]) for i, nm in enumerate(ca_prov_order)])
  ca_prov_grid = np.where(mask_ca, ca_prov_grid, 0)
  ca_prov_grid = nearest_fill(mask_ca, ca_prov_grid, range(1, len(ca_prov_order) + 1))

  # Load organic watershed & ecozone datasets (batch unary_union for O(n log n) speed)
  print("Loading USGS HUC2/HUC4/HUC6, HydroBASINS NA/AR/GR, WMO, ECCC Ecozones, Hawaii Moku...")
  huc2_raw = {}
  for ft in json.loads(HUC2_JSON.read_text(encoding="utf-8"))["features"]:
    c = int(ft["properties"]["huc2"])
    huc2_raw.setdefault(c, []).append(shape(ft["geometry"]).simplify(0.01, preserve_topology=True).buffer(0))
  huc2_by_id = {c: u_geoms(lst) for c, lst in huc2_raw.items()}

  huc4_raw = {}
  for ft in json.loads(HUC4_JSON.read_text(encoding="utf-8"))["features"]:
    c = str(ft["properties"]["huc4"]).zfill(4)
    huc4_raw.setdefault(c, []).append(shape(ft["geometry"]).simplify(0.01, preserve_topology=True).buffer(0))
  huc4_by_id = {c: u_geoms(lst) for c, lst in huc4_raw.items()}

  huc6_raw = {}
  for ft in json.loads(HUC6_EXTRA_JSON.read_text(encoding="utf-8"))["features"]:
    c = str(ft["properties"]["huc6"]).zfill(6)
    huc6_raw.setdefault(c, []).append(shape(ft["geometry"]).simplify(0.01, preserve_topology=True).buffer(0))
  huc6_by_id = {c: u_geoms(lst) for c, lst in huc6_raw.items()}

  def h4_u(codes):
    return u_geoms([huc4_by_id.get(c) for c in codes])

  def h2_u(codes):
    return u_geoms([huc2_by_id.get(c) for c in codes])

  wmo_raw = {}
  for ft in json.loads(WMOBB_JSON.read_text(encoding="utf-8"))["features"]:
    wid = ft["properties"].get("WMOBB")
    if wid is not None and 401 <= int(wid) <= 455:
      wmo_raw.setdefault(int(wid), []).append(shape(ft["geometry"]).simplify(0.015, preserve_topology=True).buffer(0))
  wmo_by_id = {k: u_geoms(v) for k, v in wmo_raw.items()}

  cz_raw, cr_raw = {}, {}
  for ft in json.loads(CA_ECOREG_JSON.read_text(encoding="utf-8"))["features"]:
    pr = ft["properties"]
    zid = pr.get("ZONE_ID", "")
    rnm = pr.get("REG_EN", "")
    g = shape(ft["geometry"]).simplify(0.015, preserve_topology=True).buffer(0)
    cz_raw.setdefault(zid, []).append(g)
    cr_raw.setdefault(rnm, []).append(g)
  ca_ecozone_by_id = {k: u_geoms(v) for k, v in cz_raw.items()}
  ca_ecoreg_by_name = {k: u_geoms(v) for k, v in cr_raw.items()}

  hb_na4 = load_hydrobasins_by_pfaf("hybas_na_lev04_v1c.shp")
  hb_ar4 = load_hydrobasins_by_pfaf("hybas_ar_lev04_v1c.shp")
  hb_gr4 = load_hydrobasins_by_pfaf("hybas_gr_lev04_v1c.shp")

  def hb_range(hb_dict, lo, hi):
    return u_geoms([g for pf, g in hb_dict.items() if lo <= pf <= hi])

  # Separate Island of Newfoundland vs Mainland Labrador organically using NL polygon components + HB PFAF 7230
  nl_parts = [ca_provs["Newfoundland and Labrador"]] if ca_provs["Newfoundland and Labrador"].geom_type == "Polygon" else list(ca_provs["Newfoundland and Labrador"].geoms)
  nl_island_base = hb_na4.get(7230, Polygon())
  nl_island_geom = u_geoms([p for p in nl_parts if p.centroid.y < 51.7 and not nl_island_base.is_empty and p.intersects(nl_island_base.buffer(0.35))])
  nl_labrador_geom = u_geoms([p for p in nl_parts if not p.intersects(nl_island_geom.buffer(0.05))])

  # ------------------------------------------------------------------
  # 1. PRE-COLUMBIAN CANADA, ALASKA & GREENLAND (Modules 1..6)
  # ------------------------------------------------------------------
  print("\n=== Generating Organic Pre-Columbian Canada, Alaska & Greenland Masks ===")
  pre_ca_domain = mask_ca | mask_ak | mask_pm | mask_gl

  # Define organic vector boundaries for the 6 macro chapters in Canada/AK/GL
  m1_geom = u_geoms([us_ak_geom, ca_provs["Yukon"], ca_provs["British Columbia"]])
  m6_geom = u_geoms([ca_provs["Nova Scotia"], ca_provs["New Brunswick"], ca_provs["Prince Edward Island"], ca_provs["Newfoundland and Labrador"], pm_all_geom])
  # Saint Lawrence: ECCC Mixedwood Plains (CL08) + Great Lakes North / Ottawa / St Lawrence / Saguenay / Gaspe basins (HB 7238..7256 + 7260 inside QC + HUC4 0421..0431 inside CA)
  qc_geom = ca_provs["Québec"]
  on_geom = ca_provs["Ontario"]
  sl_core_on = u_geoms([ca_ecozone_by_id.get("CL08"), hb_na4.get(7254), hb_na4.get(7255), hb_na4.get(7256), hb_na4.get(7257), h4_u(["0416", "0417", "0420", "0421", "0422", "0423", "0425", "0427", "0429"])]).intersection(on_geom)
  # Keep Hudson Bay 7135..7139 strictly out of Saint Lawrence; add Saguenay / Cote-Nord / St-Maurice / Gaspe (7238..7240, 7251..7254, 7260) in QC
  sl_core_qc = u_geoms([ca_ecozone_by_id.get("CL08"), hb_range(hb_na4, 7238, 7240), hb_range(hb_na4, 7251, 7254), hb_na4.get(7260), h4_u(["0429", "0430", "0431"])]).intersection(qc_geom)
  m5_geom = u_geoms([sl_core_on, sl_core_qc])

  # Prairies: ECCC CL10 Prairies + Boreal Transition / Peace-Athabasca Parkland (7122..7129) inside AB/SK/MB + Lake Winnipeg / Manitoba Plain
  pr_ecoregs = u_geoms([
    ca_ecozone_by_id.get("CL10"),
    ca_ecoreg_by_name.get("Boreal Transition"),
    ca_ecoreg_by_name.get("Mid-Boreal Uplands"),
    ca_ecoreg_by_name.get("Mid Boreal Uplands"),
    ca_ecoreg_by_name.get("Interlake Plain"),
    ca_ecoreg_by_name.get("Lake of the Woods"),
  ])
  # Ensure Prairies stays strictly within Nelson-Saskatchewan (7121..7129) & Red-Rainy (0901..0903) inside AB/SK/MB/W-ON while Lake Winnipegosis/Manitoba join Prairies and Lower Nelson/Churchill Shield stays in Hudson Bay
  mb_sk_ab = u_geoms([ca_provs["Alberta"], ca_provs["Saskatchewan"], ca_provs["Manitoba"]])
  m3_geom = u_geoms([
    ca_ecozone_by_id.get("CL10"),
    ca_ecoreg_by_name.get("Interlake Plain"),
    ca_ecoreg_by_name.get("Boreal Transition"),
    hb_na4.get(7122).intersection(mb_sk_ab),
  ]).intersection(u_geoms([mb_sk_ab, hb_range(hb_na4, 7124, 7129), h4_u(["0901", "0902", "0903"])]))
  # Clip northern Churchill/Nelson muskeg out of Prairies using CL09 Boreal Plains vs CL06/CL15 Boreal Shield / Hudson Plains
  m3_geom = m3_geom.difference(ca_ecozone_by_id.get("CL15", Polygon())).difference(u_geoms([hb_na4.get(7118), hb_na4.get(7121), hb_na4.get(7132)]))

  # Hudson Bay: WMOBB 414 + Hudson/James/Ungava draining HydroBASINS (7111..7119, 7121, 7131..7139, 7210..7229, AR 8321..8330) minus m3/m5/m6
  m4_geom = u_geoms([
    hb_range(hb_na4, 7111, 7119),
    hb_na4.get(7121),
    hb_range(hb_na4, 7131, 7139),
    hb_range(hb_na4, 7210, 7229),
    hb_range(hb_ar4, 8321, 8330),
    wmo_by_id.get(414, Polygon()),
  ]).intersection(u_geoms([on_geom, qc_geom, ca_provs["Manitoba"], ca_provs["Saskatchewan"], ca_provs["Nunavut"]]))
  # Keep Churchill headwaters in SK Boreal Shield in Hudson Bay, while Boreal Plains Athabasca/Peace go to Northern Canada (2)
  m4_geom = m4_geom.difference(u_geoms([hb_na4.get(7124), hb_na4.get(7126), hb_na4.get(7127), hb_na4.get(7128), hb_na4.get(7129)]))

  # Northern Canada & Greenland (2): Everything else in CA + Greenland (Mackenzie 822x, Arctic Archipelago 831x/84xx/85xx/86xx, GL)
  m2_geom = u_geoms([
    gl_all_geom,
    ca_provs["Northwest Territories"],
    ca_provs["Nunavut"],
    ca_provs["Alberta"],
    ca_provs["Saskatchewan"],
    hb_range(hb_ar4, 8221, 8230),
    hb_range(hb_ar4, 8311, 8319),
    hb_range(hb_ar4, 8410, 8630),
  ])

  ca_macro = np.zeros((H, W), dtype=np.int32)
  for gid, gm in [(1, m1_geom), (6, m6_geom), (5, m5_geom), (3, m3_geom), (4, m4_geom), (2, m2_geom)]:
    rg = rasterize_geom_list([(gid, gm)])
    sel = pre_ca_domain & (ca_macro == 0) & (rg == gid)
    ca_macro[sel] = gid
  # Force Alaska & Greenland & PM strictly into their designated macro modules
  ca_macro[mask_ak] = 1
  ca_macro[mask_gl] = 2
  ca_macro[mask_pm] = 6
  ca_macro = np.where(pre_ca_domain, ca_macro, 0)
  ca_macro = nearest_fill(pre_ca_domain, ca_macro, [1, 2, 3, 4, 5, 6])

  pal1 = distinct_palette(30, 0.05)

  # Module 1.1: Northern Cascadia and Alaska
  m1 = (ca_macro == 1)
  nc1_g = h4_u(["1902", "1903"])  # South Central & SW Alaska / Aleutians
  nc2_g = h4_u(["1905", "1906", "1909"])  # Bering Delta, NW & Arctic Alaska
  nc3_g = u_geoms([h4_u(["1907", "1908"]), ca_provs["Yukon"]])  # Interior Yukon-Tanana & Yukon Territory
  nc4_g = u_geoms([
    h4_u(["1901"]),
    wmo_by_id.get(404),
    hb_range(hb_na4, 7834, 7839),
    ca_ecoreg_by_name.get("Gwaii Haanas"),
    ca_ecoreg_by_name.get("Nass Ranges"),
    ca_ecoreg_by_name.get("Coastal Gap"),
  ])
  nc5_g = u_geoms([hb_range(hb_na4, 7826, 7833), ca_provs["British Columbia"]])
  g1 = ordered_raster_partition(m1, [(4, nc4_g), (1, nc1_g), (2, nc2_g), (3, nc3_g), (5, nc5_g)])
  g1_geoms = {1: nc1_g, 2: nc2_g, 3: nc3_g, 4: nc4_g, 5: nc5_g}
  write_mask_and_json5(
    CENTAUR_DIR / "1.pre_columbian_canada_and_alaska/1.northern_cascadia_and_alaska",
    "northern_cascadia_and_alaska",
    {"title": "Pre-Columbian Northern Cascadia and Alaska: Marine Chiefdoms, Subarctic Fishers and Arctic Adaptations (10000BC-1600AD)", "rel_dir": "1.pre_columbian_canada_and_alaska/1.northern_cascadia_and_alaska", "domain": [-10000, 1600]},
    [
      {"gid": 1, "key": "nc_aleutians_kodiak_south_alaska", "name": "1. Aleutian Archipelago, Kodiak & Gulf of Alaska Coast (Unangan & Sugpiaq)", "colour": pal1[0]},
      {"gid": 2, "key": "nc_yupik_inupiat_arctic_alaska", "name": "2. Bering Sea Delta & North Slope Arctic Tundra (Yup'ik & Inupiat)", "colour": pal1[1]},
      {"gid": 3, "key": "nc_interior_yukon_tanana_athabaskan", "name": "3. Interior Yukon-Tanana Subarctic Basin (Northern Athabaskan)", "colour": pal1[2]},
      {"gid": 4, "key": "nc_tlingit_haida_outer_coast", "name": "4. Inside Passage, Haida Gwaii & Skeena-Nass Coast (Tlingit, Haida & Tsimshian)", "colour": pal1[3]},
      {"gid": 5, "key": "nc_salish_fraser_bc_plateau", "name": "5. Salish Sea, Vancouver Island & Fraser-Columbia Interior Plateau", "colour": pal1[4]},
    ],
    g1, land_area_eff, geom_by_gid=g1_geoms, clip_geom=m1_geom, priority_order=[4, 1, 2, 3, 5]
  )

  # Module 1.2: Northern Canada (& Pre-Colonial Greenland)
  m2 = (ca_macro == 2)
  gl_w_g = hb_range(hb_gr4, 9125, 9143)
  gl_e_g = u_geoms([hb_range(hb_gr4, 9111, 9124), hb_range(hb_gr4, 9144, 9149)])
  mack_g = u_geoms([wmo_by_id.get(408), hb_range(hb_ar4, 8221, 8229), ca_ecozone_by_id.get("CL04"), ca_ecozone_by_id.get("CL09")])
  earc_g = u_geoms([hb_range(hb_ar4, 8430, 8630), ca_ecozone_by_id.get("CL01")])
  warc_g = u_geoms([hb_ar4.get(8230), hb_range(hb_ar4, 8311, 8319), hb_ar4.get(8410), hb_ar4.get(8420), ca_ecozone_by_id.get("CL03"), ca_ecozone_by_id.get("CL02")])
  g2 = ordered_raster_partition(m2, [(4, gl_w_g), (5, gl_e_g), (1, mack_g), (3, earc_g), (2, warc_g)])
  # Strictly enforce Greenland pixels in 4/5 and Canada pixels in 1/2/3
  g2 = np.where(mask_gl, np.where(np.isin(g2, [4, 5]), g2, 4), np.where(np.isin(g2, [1, 2, 3]), g2, 2))
  g2 = np.where(m2, g2, 0)
  write_mask_and_json5(
    CENTAUR_DIR / "1.pre_columbian_canada_and_alaska/2.northern_canada",
    "northern_canada",
    {"title": "Pre-Columbian Northern Canada and Greenland: Dene Boreal Caribou Hunters, Palaeo-Inuit, Thule and Norse Settlers (10000BC-1600AD)", "rel_dir": "1.pre_columbian_canada_and_alaska/2.northern_canada", "domain": [-10000, 1600]},
    [
      {"gid": 1, "key": "ncan_mackenzie_dene_subarctic", "name": "1. Mackenzie & Peace-Athabasca Boreal Lowlands (Dene)", "colour": pal1[5]},
      {"gid": 2, "key": "ncan_western_central_arctic", "name": "2. Central & Western Arctic Tundra & Barrenlands (Pre-Dorset to Copper/Netsilik Inuit)", "colour": pal1[6]},
      {"gid": 3, "key": "ncan_eastern_high_arctic_baffin", "name": "3. Baffin Island, Foxe Basin & High Arctic Archipelago (Dorset & Thule)", "colour": pal1[7]},
      {"gid": 4, "key": "ncan_greenland_west_norse_kalaallit", "name": "4. West & Southwest Greenland Fjords (Kalaallit & Norse Settlements)", "colour": pal1[8]},
      {"gid": 5, "key": "ncan_greenland_east_high_north", "name": "5. East & High North Greenland (Independence & Tunumiit)", "colour": pal1[9]},
    ],
    g2, land_area_eff, geom_by_gid={1: mack_g, 2: warc_g, 3: earc_g, 4: gl_w_g, 5: gl_e_g}, clip_geom=m2_geom, priority_order=[4, 5, 1, 3, 2]
  )

  # Module 1.3: Prairies (100% ECCC Ecoregions + HydroBASINS)
  m3 = (ca_macro == 3)
  pr1_g = u_geoms([ca_ecoreg_by_name.get("Foothills Fescue"), ca_ecoreg_by_name.get("Foothills Parkland"), ca_ecoreg_by_name.get("Fescue Grass"), ca_ecoreg_by_name.get("Mixedgrass").intersection(ca_provs["Alberta"]) if "Mixedgrass" in ca_ecoreg_by_name else Polygon(), hb_na4.get(7128), hb_na4.get(7129)])
  pr4_g = u_geoms([ca_ecoreg_by_name.get("Lake Manitoba Plain"), ca_ecoreg_by_name.get("Southwest Manitoba Uplands"), ca_ecoreg_by_name.get("Interlake Plain"), ca_ecoreg_by_name.get("Lake of the Woods"), ca_provs["Manitoba"]])
  pr2_g = u_geoms([ca_ecoreg_by_name.get("Aspen Parkland"), ca_ecoreg_by_name.get("Boreal Transition"), hb_na4.get(7124)])
  pr3_g = u_geoms([ca_ecoreg_by_name.get("Dry Mixedgrass"), ca_ecoreg_by_name.get("Moist Mixed Grassland"), ca_ecoreg_by_name.get("Cypress Hills Montane"), ca_ecoreg_by_name.get("Cypress Mixedgrass"), hb_na4.get(7125), hb_na4.get(7127)])
  g3 = ordered_raster_partition(m3, [(1, pr1_g), (3, pr3_g), (2, pr2_g), (4, pr4_g)])
  write_mask_and_json5(
    CENTAUR_DIR / "1.pre_columbian_canada_and_alaska/3.prairies",
    "prairies",
    {"title": "Pre-Columbian Canadian Prairies: Bison-Hunting Nomads, Aspen Parklands and Woodland Outliers (10000BC-1600AD)", "rel_dir": "1.pre_columbian_canada_and_alaska/3.prairies", "domain": [-10000, 1600]},
    [
      {"gid": 1, "key": "pr_foothills_bow_upper_saskatchewan", "name": "1. Rocky Mountain Foothills & Bow-Oldman Plains (Niitsitapi/Blackfoot)", "colour": pal1[10]},
      {"gid": 2, "key": "pr_central_parkland_north_saskatchewan", "name": "2. Aspen Parkland & North Saskatchewan Valley (Plains Cree & Oxbow-Besant)", "colour": pal1[11]},
      {"gid": 3, "key": "pr_south_saskatchewan_palliser_steppe", "name": "3. South Saskatchewan Mixedgrass Steppe & Qu'Appelle (Assiniboine & Avonlea)", "colour": pal1[12]},
      {"gid": 4, "key": "pr_red_assiniboine_winnipeg_basin", "name": "4. Red-Assiniboine Plains & Lake Manitoba Lowlands (Laurel-Blackduck)", "colour": pal1[13]},
    ],
    g3, land_area_eff, geom_by_gid={1: pr1_g, 2: pr2_g, 3: pr3_g, 4: pr4_g}, clip_geom=m3_geom, priority_order=[1, 3, 2, 4]
  )

  # Module 1.4: Hudson Bay
  m4 = (ca_macro == 4)
  hb1_g = u_geoms([ca_provs["Nunavut"].intersection(hb_range(hb_ar4, 8321, 8330)), hb_range(hb_ar4, 8321, 8330), hb_range(hb_na4, 7111, 7117), hb_na4.get(7119)])
  hb3_g = u_geoms([hb_range(hb_na4, 7211, 7229), ca_provs["Québec"]])
  hb2_g = u_geoms([ca_ecozone_by_id.get("CL15"), hb_na4.get(7118), hb_na4.get(7121), hb_range(hb_na4, 7131, 7139)])
  g4 = ordered_raster_partition(m4, [(1, hb1_g), (3, hb3_g), (2, hb2_g)])
  write_mask_and_json5(
    CENTAUR_DIR / "1.pre_columbian_canada_and_alaska/4.hudson_bay",
    "hudson_bay",
    {"title": "Pre-Columbian Hudson Bay and Boreal Shield: Subarctic Cree, Innu and Caribou Inuit Demography (10000BC-1600AD)", "rel_dir": "1.pre_columbian_canada_and_alaska/4.hudson_bay", "domain": [-10000, 1600]},
    [
      {"gid": 1, "key": "hb_keewatin_western_barrens", "name": "1. Kivalliq & Western Hudson Bay Barren Grounds (Caribou Inuit & Sayisi Dene)", "colour": pal1[14]},
      {"gid": 2, "key": "hb_hudson_james_lowlands_cree", "name": "2. Hudson & James Bay Lowlands and Northern Ontario Shield (Swampy Cree & Severn Ojibwe)", "colour": pal1[15]},
      {"gid": 3, "key": "hb_eastmain_nunavik_ungava", "name": "3. Eastmain, James Bay East, Nunavik & Ungava Peninsula (Eeyou, Naskapi & Inuit)", "colour": pal1[16]},
    ],
    g4, land_area_eff, geom_by_gid={1: hb1_g, 2: hb2_g, 3: hb3_g}, clip_geom=m4_geom, priority_order=[1, 3, 2]
  )

  # Module 1.5: Saint Lawrence
  m5 = (ca_macro == 5)
  sl1_g = u_geoms([hb_na4.get(7255), hb_na4.get(7256), hb_na4.get(7257), ca_ecoreg_by_name.get("Lake Simcoe"), ca_ecoreg_by_name.get("Lake Erie - Lake Ontario"), h4_u(["0421", "0422", "0423", "0425", "0427"])])
  sl2_g = u_geoms([hb_na4.get(7254), h4_u(["0429"])])
  sl4_g = u_geoms([hb_range(hb_na4, 7238, 7240), hb_na4.get(7260)])
  sl3_g = u_geoms([hb_range(hb_na4, 7251, 7253), ca_ecoreg_by_name.get("St. Lawrence Lowlands"), h4_u(["0430", "0431"])])
  g5 = ordered_raster_partition(m5, [(1, sl1_g), (2, sl2_g), (4, sl4_g), (3, sl3_g)])
  write_mask_and_json5(
    CENTAUR_DIR / "1.pre_columbian_canada_and_alaska/5.saint_lawrence",
    "saint_lawrence",
    {"title": "Pre-Columbian Saint Lawrence Basin and Huronia: Maize Agriculture, Palisaded Towns and Algonquian Networks (10000BC-1600AD)", "rel_dir": "1.pre_columbian_canada_and_alaska/5.saint_lawrence", "domain": [-10000, 1600]},
    [
      {"gid": 1, "key": "sl_huronia_simcoe_ontario_peninsula", "name": "1. Huronia, Simcoe Uplands & Ontario Peninsula (Wendat, Tionontati & Neutral)", "colour": pal1[17]},
      {"gid": 2, "key": "sl_ottawa_rideau_upper_st_lawrence", "name": "2. Ottawa-Rideau Valley & Algonquin Shield (Algonquin & Nipissing)", "colour": pal1[18]},
      {"gid": 3, "key": "sl_montreal_trois_rivieres_quebec", "name": "3. St. Lawrence Lowlands: Hochelaga to Stadacona (St. Lawrence Iroquoians)", "colour": pal1[19]},
      {"gid": 4, "key": "sl_saguenay_north_shore_gaspe", "name": "4. Saguenay-Lac-Saint-Jean, Cote-Nord & Gaspe Peninsula (Innu & Gespe'gewa'gi Mi'kmaq)", "colour": pal1[20]},
    ],
    g5, land_area_eff, geom_by_gid={1: sl1_g, 2: sl2_g, 3: sl3_g, 4: sl4_g}, clip_geom=m5_geom, priority_order=[1, 2, 4, 3]
  )

  # Module 1.6: Maritimes
  m6 = (ca_macro == 6)
  mar1_g = u_geoms([ca_provs["Nova Scotia"], ca_provs["Prince Edward Island"]])
  mar2_g = ca_provs["New Brunswick"]
  mar3_g = u_geoms([nl_island_geom, pm_all_geom])
  mar4_g = nl_labrador_geom
  g6 = ordered_raster_partition(m6, [(1, mar1_g), (2, mar2_g), (3, mar3_g), (4, mar4_g)])
  g6[m6 & mask_pm] = 3
  write_mask_and_json5(
    CENTAUR_DIR / "1.pre_columbian_canada_and_alaska/6.maritimes",
    "maritimes",
    {"title": "Pre-Columbian Atlantic Maritimes, Newfoundland and Labrador: Maritime Archaic, Mi'kmaq, Beothuk and Norse Vinland (10000BC-1600AD)", "rel_dir": "1.pre_columbian_canada_and_alaska/6.maritimes", "domain": [-10000, 1600]},
    [
      {"gid": 1, "key": "mar_mikmaki_ns_pei_cape_breton", "name": "1. Nova Scotia, Unama'ki (Cape Breton) & Epekwitk (PEI) (Mi'kma'ki)", "colour": pal1[21]},
      {"gid": 2, "key": "mar_wolastoq_new_brunswick_fundy", "name": "2. Wolastoq (Saint John) Basin, Miramichi & Passamaquoddy (Wolastoqiyik & Mi'kmaq)", "colour": pal1[22]},
      {"gid": 3, "key": "mar_newfoundland_beothuk_st_pierre", "name": "3. Island of Newfoundland & Saint-Pierre-et-Miquelon (Beothuk, Dorset & L'Anse aux Meadows)", "colour": pal1[23]},
      {"gid": 4, "key": "mar_labrador_innu_nunatsiavut", "name": "4. Labrador Plateau & Nunatsiavut Coast (Maritime Archaic, Innu & Inuit)", "colour": pal1[24]},
    ],
    g6, land_area_eff, geom_by_gid={1: mar1_g, 2: mar2_g, 3: mar3_g, 4: mar4_g}, clip_geom=m6_geom
  )

  # ------------------------------------------------------------------
  # 2. 18 US HYDROLOGICAL UNITS — PURE USGS WBD HUC4/HUC6 PARTITIONS
  # ------------------------------------------------------------------
  print("\n=== Generating 18 Organic US Hydrological Units (USGS WBD HUC4/HUC6) ===")
  huc_raw_grid = rasterize_geom_list([(cid, huc2_by_id[cid]) for cid in range(1, 19)])
  us_huc_grid = np.where(mask_us48, huc_raw_grid, 0)
  us_huc_grid = nearest_fill(mask_us48, us_huc_grid, range(1, 19))

  kelly_specs = [
    ("01.upper_colorado", "upper_colorado", 14, "Upper Colorado Hydrological Unit (HU 14): Fremont, Ancestral Puebloan and Ute Demography (10000BC-1600AD)", [
      ("uc_green_river_wyoming_basin", "1. Green River & Wyoming High Desert Basin (Fremont North)", h4_u(["1404", "1405", "1406"])),
      ("uc_colorado_headwaters_grand_mesa", "2. Colorado-Gunnison Headwaters & Canyonlands", h4_u(["1401", "1402", "1403", "1407"])),
      ("uc_san_juan_four_corners", "3. San Juan Basin & Four Corners / Mesa Verde", h4_u(["1408"])),
    ]),
    ("02.extreme_northern_plains", "extreme_northern_plains", 9, "Extreme Northern Plains Hydrological Unit (HU 09): Souris-Red-Rainy Glacial Lake Agassiz Basin (10000BC-1600AD)", [
      ("enp_souris_devils_lake", "1. Souris Loop & Devils Lake Drift Prairie", u_geoms([huc4_by_id.get("0901"), huc4_by_id.get("0904"), huc6_by_id.get("090202")])),
      ("enp_red_river_north", "2. Red River of the North Valley", u_geoms([huc6_by_id.get("090201"), huc6_by_id.get("090203"), huc4_by_id.get("0902")])),
      ("enp_rainy_lake_of_the_woods", "3. Rainy River & Lake of the Woods Boreal Border", h4_u(["0903"])),
    ]),
    ("03.northern_plains", "northern_plains", 10, "Northern Plains Hydrological Unit (HU 10): Missouri Basin, Wyoming High Plains and Middle Missouri Earthlodges (10000BC-1600AD)", [
      ("np_upper_missouri_montana", "1. Upper Missouri & Milk-Marias Steppe (Montana)", h4_u(["1002", "1003", "1004", "1005", "1006"])),
      ("np_wyoming_bighorn_powder_plat", "2. Wyoming Basin: Yellowstone, Bighorn, Powder & North Platte (Kelly HU 10-WY)", h4_u(["1007", "1008", "1009", "1010", "1018"])),
      ("np_middle_missouri_dakotas", "3. Middle Missouri Trench: Mandan, Hidatsa & Arikara Core (ND/SD)", h4_u(["1011", "1012", "1013", "1014", "1015", "1016", "1017"])),
      ("np_lower_missouri_platte_kansas", "4. Platte, Republican & Lower Missouri Prairie-Plains (NE/KS/IA/MO)", h4_u(["1019", "1020", "1021", "1022", "1023", "1024", "1025", "1026", "1027", "1028", "1029", "1030"])),
    ]),
    ("04.arizona", "arizona", 15, "Arizona Hydrological Unit (HU 15): Hohokam Irrigation, Mogollon Rim and Lower Colorado Demography (10000BC-1600AD)", [
      ("az_little_colorado_plateau", "1. Little Colorado & Hopi Mesas Plateau", h4_u(["1501", "1502"])),
      ("az_salt_verde_phoenix_hohokam", "2. Salt-Verde-Middle Gila Core (Phoenix Basin Hohokam)", h4_u(["1505", "1506"])),
      ("az_tucson_santa_cruz_san_pedro", "3. Santa Cruz, San Pedro & Cochise Highlands", h4_u(["1504", "1508"])),
      ("az_lower_colorado_sonoran", "4. Lower Colorado Corridor & Western Sonoran Desert (Patayan/Yuman)", h4_u(["1503", "1507"])),
    ]),
    ("05.great_basin", "great_basin", 16, "Great Basin Hydrological Unit (HU 16): Bonneville-Fremont Farmers and Lahontan Desert Foragers (10000BC-1600AD)", [
      ("gb_bonneville_wasatch_fremont", "1. Lake Bonneville, Bear River & Wasatch Oasis (Fremont)", h4_u(["1601", "1602", "1603"])),
      ("gb_humboldt_lahontan_west", "2. Humboldt Sink, Lake Lahontan & Carson-Truckee Corridor", h4_u(["1604", "1605"])),
      ("gb_central_nevada_owens_mojave", "3. Central Nevada Valleys, Owens Valley & Mojave Endorheic Basin", h4_u(["1606"])),
    ]),
    ("06.upper_mississippi", "upper_mississippi", 7, "Upper Mississippi Hydrological Unit (HU 07): Hopewell, Effigy Mounds and Cahokia/American Bottom (10000BC-1600AD)", [
      ("um_minnesota_driftless_north", "1. Upper Mississippi Headwaters, Minnesota River & Driftless Zone", h4_u(["0701", "0702", "0703", "0704", "0705", "0707"])),
      ("um_des_moines_rock_iowa", "2. Iowa-Des Moines, Rock & Upper Illinois Drift Plains (Oneota)", h4_u(["0706", "0708", "0709", "0710", "0711", "0712"])),
      ("um_american_bottom_lower_il", "3. American Bottom, Lower Illinois & Mississippi-Missouri Confluence (Cahokia)", h4_u(["0713", "0714"])),
    ]),
    ("07.rio_grande", "rio_grande", 13, "Rio Grande Hydrological Unit (HU 13): Rio Grande Pueblos, Jornada Mogollon and Rio Conchos Borderlands (10000BC-1600AD)", [
      ("rg_san_luis_upper_pueblos", "1. San Luis Valley & Northern Tiwa/Tewa-Chama Pueblos (Taos-Santa Fe)", h4_u(["1301", "1302", "1305"])),
      ("rg_middle_rio_grande_salinas", "2. Middle Rio Grande, Piro-Salinas & Jornada Mogollon (Socorro-El Paso)", h4_u(["1303", "1306"])),
      ("rg_pecos_big_bend_lower_rg", "3. Pecos Valley, Big Bend & Lower Rio Grande Tamaulipan Plains", h4_u(["1304", "1307", "1308", "1309"])),
    ]),
    ("08.cumberland", "cumberland", 6, "Cumberland (Tennessee) Hydrological Unit (HU 06): Dallas-Mouse Creek Chiefdoms and Tennessee Valley Mound Towns (10000BC-1600AD)", [
      ("cu_upper_east_tennessee_ridge", "1. Upper East Tennessee, Holston-French Broad & Chickamauga Ridge-and-Valley", h4_u(["0601", "0602"])),
      ("cu_middle_tennessee_muscle_shoals", "2. Middle Tennessee Bend, Elk River & Muscle Shoals (Mound Bottom / Shiloh)", h4_u(["0603"])),
      ("cu_lower_tennessee_kentucky_confluence", "3. Lower Tennessee River & Highland Rim Confluence", h4_u(["0604"])),
    ]),
    ("09.southeast", "southeast", 3, "Southeast Hydrological Unit (HU 03): Mississippian Chiefdoms of the Piedmont, Coastal Plain and Florida (10000BC-1600AD)", [
      ("se_carolina_piedmont_santee", "1. Roanoke, Yadkin-Pee Dee & Santee-Wateree Carolina Piedmont-Coast", h4_u(["0301", "0302", "0303", "0304", "0305"])),
      ("se_georgia_savannah_ocmulgee_etowah", "2. Savannah, Ocmulgee & Etowah-Coosa Georgia Basins", h4_u(["0306", "0307", "0313"])),
      ("se_alabama_tombigbee_moundville", "3. Black Warrior, Alabama & Tombigbee-Mobile Basins (Moundville & Bottle Creek)", h4_u(["0314", "0315", "0316", "0317", "0318"])),
      ("se_peninsular_florida_apalachicola", "4. Peninsular Florida, St. Johns, Apalachicola & Calusa Coast", h4_u(["0308", "0309", "0310", "0311", "0312"])),
    ]),
    ("10.lower_mississippi", "lower_mississippi", 8, "Lower Mississippi Hydrological Unit (HU 08): Poverty Point, Plaquemine and Late Mississippian Towns (10000BC-1600AD)", [
      ("lm_st_francis_st_memphis_parkin", "1. St. Francis Basin, Reelfoot & Lower White-Arkansas Delta (Parkin & Nodena)", h4_u(["0801", "0802"])),
      ("lm_yazoo_ouachita_poverty_point", "2. Yazoo Basin, Tensas-Boeuf & Ouachita Ridges (Poverty Point & Winterville)", h4_u(["0803", "0804", "0805"])),
      ("lm_natchez_atchafalaya_delta", "3. Natchez Bluffs, Atchafalaya & Mississippi Birdfoot Delta (Plaquemine)", h4_u(["0806", "0807", "0808", "0809"])),
    ]),
    ("11.southern_plains", "southern_plains", 12, "Southern Plains Hydrological Unit (HU 12): Texas-Gulf Caddoan Chiefdoms, Central Prairies and Coastal Foragers (10000BC-1600AD)", [
      ("sp_neches_sabine_trinity_caddo", "1. Sabine, Neches & Upper Trinity Basins (Western Caddo / George C. Davis)", h4_u(["1201", "1202", "1203"])),
      ("sp_brazos_colorado_edwards", "2. Brazos, Colorado & Edwards Plateau Balcones Escarpment", h4_u(["1205", "1206", "1207", "1208"])),
      ("sp_gulf_coast_nueces_karankawa", "3. Texas Gulf Barrier Coast, Galveston-Matagorda & Nueces (Karankawa & Coahuiltecan)", h4_u(["1204", "1209", "1210", "1211"])),
    ]),
    ("12.ohio_river", "ohio_river", 5, "Ohio River Hydrological Unit (HU 05): Adena-Hopewell Monumental Cores, Fort Ancient and Cumberland-Wabash (10000BC-1600AD)", [
      ("oh_upper_ohio_allegheny_kanawha", "1. Allegheny, Monongahela & Kanawha-Upper Ohio Plateau (Monongahela)", h4_u(["0501", "0502", "0503", "0504", "0505", "0507"])),
      ("oh_scioto_miami_hopewell_core", "2. Scioto, Little & Great Miami Valleys (Adena-Hopewell & Fort Ancient)", h4_u(["0506", "0508", "0509"])),
      ("oh_kentucky_cumberland_green", "3. Cumberland, Kentucky & Green River Valleys (Angel/Cumberland Stone-Box)", h4_u(["0510", "0511", "0513"])),
      ("oh_wabash_white_lower_ohio_kincaid", "4. Wabash-White Basins & Lower Ohio Confluence (Angel & Kincaid)", h4_u(["0512", "0514"])),
    ]),
    ("13.new_england", "new_england", 1, "New England Hydrological Unit (HU 01): Wabanaki Riverines, Coastal Shell-Middens and Southern Algonquian Towns (10000BC-1600AD)", [
      ("ne_maine_penobscot_kennebec", "1. Penobscot, Kennebec, St. John & Aroostook Maine (Wabanaki)", h4_u(["0101", "0102", "0103", "0104", "0105"])),
      ("ne_merrimack_massachusetts_bay", "2. Merrimack, Saco & Massachusetts-Plymouth Bay (Massachusett & Pennacook)", h4_u(["0106", "0107", "0109"])),
      ("ne_connecticut_narragansett_south", "3. Connecticut, Housatonic & Narragansett-Cape Cod Sound (Narragansett, Pequot & Mohegan)", h4_u(["0108", "0110"])),
    ]),
    ("14.central_plains", "central_plains", 11, "Central Plains Hydrological Unit (HU 11): Arkansas-White-Red Basins, Spiro Moundville West and Plains Villages (10000BC-1600AD)", [
      ("cp_high_plains_upper_arkansas", "1. Upper Arkansas, Cimarron & Llano Estacado High Plains (Antelope Creek)", h4_u(["1102", "1104", "1108", "1112"])),
      ("cp_neosho_verdigris_washita_prairies", "2. Middle Arkansas, Neosho-Grand, Canadian & Washita Prairies (Wichita)", h4_u(["1103", "1105", "1106", "1107", "1109", "1110", "1113"])),
      ("cp_arkansas_valley_ozark_spiro", "3. Lower Arkansas Valley, Ozark Fringe & Red River Bend (Spiro Mound Centre)", h4_u(["1101", "1111", "1114"])),
    ]),
    ("15.mid_atlantic", "mid_atlantic", 2, "Mid-Atlantic Hydrological Unit (HU 02): Haudenosaunee Finger Lakes-Mohawk, Lenapehoking and Powhatan Tidewater (10000BC-1600AD)", [
      ("ma_hudson_mohawk_champlain", "1. Hudson, Mohawk & Lake Champlain Corridor (Mohawk, Mahican & Oneida East)", h4_u(["0202", "0203"])),
      ("ma_delaware_susquehanna_lenape", "2. Delaware, Susquehanna & Upper Finger Lakes (Lenape, Susquehannock & Onondaga)", h4_u(["0204", "0205"])),
      ("ma_chesapeake_potomac_james_powhatan", "3. Chesapeake Bay, Potomac, Rappahannock & James Tidewater (Powhatan & Piscataway)", h4_u(["0206", "0207", "0208"])),
    ]),
    ("16.great_lakes", "great_lakes", 4, "Great Lakes Hydrological Unit (HU 04): Lake Superior Wild Rice, Lake Michigan Ridged-Fields and Iroquois-Erie Borderlands (10000BC-1600AD)", [
      ("gl_superior_upper_peninsula", "1. Lake Superior Basin & Upper Peninsula Copper-Rice Zone", h4_u(["0401", "0402", "0403"])),
      ("gl_michigan_fox_winnebago", "2. Lake Michigan, Green Bay, Fox-Winnebago & Lower Michigan West (Oneota/Menominee)", h4_u(["0404", "0405", "0406"])),
      ("gl_huron_erie_finger_lakes_ny", "3. Saginaw-Huron, Maumee-Erie & Western NY Finger Lakes (Seneca, Cayuga & Erie)", h4_u(["0407", "0408", "0409", "0410", "0411", "0412", "0413", "0414", "0429", "0430"])),
    ]),
    ("17.california", "california", 18, "California Hydrological Unit (HU 18): Acorn Economies, Sacramento-San Joaquin Delta and Chumash Maritime Chiefdoms (10000BC-1600AD)", [
      ("ca_klamath_north_coast_shasta", "1. Klamath-Trinity, Eel River & North Coast Ranges (Yurok, Karuk & Hupa)", h4_u(["1801", "1808"])),
      ("ca_sacramento_sf_bay_delta", "2. Sacramento Valley, San Francisco Bay & Central Delta (Patwin, Ohlone & Miwok)", h4_u(["1802", "1805"])),
      ("ca_san_joaquin_central_coast", "3. San Joaquin-Tulare Basin, Sierra Foothills & Monterey Coast (Yokuts & Esselen)", h4_u(["1803", "1804", "1806", "1809"])),
      ("ca_chumash_channel_southern_cal", "4. Santa Barbara Channel, Los Angeles Basin & Colorado Desert (Chumash, Tongva & Kumeyaay)", h4_u(["1807", "1810"])),
    ]),
    ("18.northwest", "northwest", 17, "Northwest Hydrological Unit (HU 17): Puget Sound, Lower Columbia Plank-Houses and Plateau Salmon Fisheries (10000BC-1600AD)", [
      ("nw_puget_sound_olympic_coast", "1. Puget Sound, Olympic Peninsula & North Coast (Coast Salish & Makah)", u_geoms([huc4_by_id.get("1711"), huc6_by_id.get("171001")])),
      ("nw_lower_columbia_willamette_coast", "2. Lower Columbia, Willamette Valley & Oregon Coast (Chinookan, Kalapuya & Tillamook)", u_geoms([huc4_by_id.get("1708"), huc4_by_id.get("1709"), huc6_by_id.get("171002"), huc6_by_id.get("171003"), huc4_by_id.get("1710")])),
      ("nw_columbia_plateau_yakima_spokane", "3. Columbia Plateau, Mid-Columbia Dalles & Okanogan-Spokane (Sahaptin & Interior Salish)", h4_u(["1701", "1702", "1703", "1707"])),
      ("nw_snake_river_klamath_interior", "4. Snake River Plain, Owyhee & Harney-Malheur High Desert (Shoshone-Bannock & Northern Paiute)", h4_u(["1704", "1705", "1706", "1712"])),
    ]),
  ]

  for dir_name, stem, huc_id, title, sub_rules in kelly_specs:
    m = (us_huc_grid == huc_id)
    pal = distinct_palette(len(sub_rules), seed_offset=huc_id * 0.13)
    rules_gid = []
    geom_by_gid = {}
    zdefs = []
    for idx_s, (zk, zname, zgeom) in enumerate(sub_rules, start=1):
      rules_gid.append((idx_s, zgeom))
      geom_by_gid[idx_s] = zgeom
      zdefs.append({"gid": idx_s, "key": zk, "name": zname, "colour": pal[idx_s - 1]})
    g = ordered_raster_partition(m, rules_gid)
    write_mask_and_json5(
      CENTAUR_DIR / "2.united_states_hydrological_units" / dir_name,
      stem,
      {"title": title, "rel_dir": f"2.united_states_hydrological_units/{dir_name}", "domain": [-10000, 1600]},
      zdefs, g, land_area_eff, geom_by_gid=geom_by_gid, clip_geom=huc2_by_id[huc_id].intersection(us_lower48_geom)
    )

  # ------------------------------------------------------------------
  # 3. HAWAI'I AND AMERICAN POLYNESIA — PURE MOKU / HUC4 ISLAND POLYGONS
  # ------------------------------------------------------------------
  print("\n=== Generating Pre-Annexation Hawai'i and American Polynesia ===")
  m_hp = mask_hi | mask_as
  hp1_g = h4_u(["2001"])
  hp2_g = h4_u(["2002", "2003", "2004", "2005"])
  hp3_g = h4_u(["2006"])
  hp4_g = h4_u(["2007", "2008", "2009"])
  hp5_g = as_all_geom
  g_hp = ordered_raster_partition(m_hp, [(5, hp5_g), (1, hp1_g), (2, hp2_g), (3, hp3_g), (4, hp4_g)])
  g_hp[mask_as] = 5
  pal_hp = distinct_palette(5, 0.22)
  write_mask_and_json5(
    CENTAUR_DIR / "3.hawaii_and_american_polynesia/1.hawaii_and_american_polynesia",
    "hawaii_and_american_polynesia",
    {"title": "Pre-Annexation Hawai'i and American Polynesia: Ahupua'a Intensification, Kingdom Censuses and Tutuila-Manu'a Chiefdoms (800AD-1898AD)", "rel_dir": "3.hawaii_and_american_polynesia/1.hawaii_and_american_polynesia", "domain": [-10000, 1898]},
    [
      {"gid": 1, "key": "hp_hawaii_island", "name": "1. Hawai'i Island (Kohala, Kona, Ka'u, Puna, Hilo & Hamakua)", "colour": pal_hp[0]},
      {"gid": 2, "key": "hp_maui_nui", "name": "2. Maui Nui (Maui, Moloka'i, Lana'i & Kaho'olawe)", "colour": pal_hp[1]},
      {"gid": 3, "key": "hp_oahu", "name": "3. O'ahu (Waikiki, Ewa, Ko'olau & Wai'anae)", "colour": pal_hp[2]},
      {"gid": 4, "key": "hp_kauai_niihau", "name": "4. Kaua'i & Ni'ihau", "colour": pal_hp[3]},
      {"gid": 5, "key": "hp_american_samoa", "name": "5. Eastern Samoa / American Polynesia (Tutuila, Aunu'u & Manu'a)", "colour": pal_hp[4]},
    ],
    g_hp, land_area_eff, geom_by_gid={1: hp1_g, 2: hp2_g, 3: hp3_g, 4: hp4_g, 5: hp5_g}
  )

  # ------------------------------------------------------------------
  # 4. COLONIAL AMERICA & CANADA — .NAISSANCE POLITIES + WATERSHEDS
  # ------------------------------------------------------------------
  print("\n=== Generating .naissance + Watershed Colonial America & Canada Masks ===")
  n1750_id, _ = load_naissance_map("1750")
  n1763_id, _ = load_naissance_map("1763_mid")
  n1775_id, _ = load_naissance_map("1775_mid")
  n1782_id, _ = load_naissance_map("1782")
  n1850_id, _ = load_naissance_map("1850_mid")
  n1867_id, _ = load_naissance_map("1867_mid")

  # Appalachian & Atlantic drainage watershed crest cleanly bounds Colonial charters East of the Mountains
  atlantic_slope_w = u_geoms([
    h2_u([1, 2]),
    h4_u(["0301", "0302", "0303", "0304", "0305", "0306", "0307"]),
    h4_u(["0413", "0414", "0429", "0430"]),
  ])
  # Thirteen Colonies geometries from 1750 .naissance clipped east of Appalachian watershed divide
  c13_specs_1750 = [
    (1, "4790", u_geoms([n1750_id.get("4790"), us_states_poly.get("New Hampshire")])),
    (2, "5068", u_geoms([n1750_id.get("5068"), us_states_poly.get("Massachusetts"), us_states_poly.get("Maine")]).difference(us_states_poly.get("New Hampshire", Polygon()))),
    (3, "4962", u_geoms([n1750_id.get("4962"), us_states_poly.get("Rhode Island")])),
    (4, "4822", u_geoms([n1750_id.get("4822"), us_states_poly.get("Connecticut")])),
    (5, "4969", n1750_id.get("4969", Polygon())),
    (6, "4968", n1750_id.get("4968", Polygon())),
    (7, "5030", n1750_id.get("5030", Polygon()).intersection(atlantic_slope_w)),
    (8, "4966", n1750_id.get("4966", Polygon())),
    (9, "4808", n1750_id.get("4808", Polygon())),
    (10, "4703", n1750_id.get("4703", Polygon())),
    (11, "5191", n1750_id.get("5191", Polygon()).intersection(atlantic_slope_w)),
    (12, "5192", n1750_id.get("5192", Polygon()).intersection(atlantic_slope_w)),
    (13, "5268", n1750_id.get("5268", Polygon()).intersection(atlantic_slope_w)),
  ]
  fl_basin = h4_u(["0308", "0309", "0310", "0311", "0312", "0313", "0314"])
  sp1_fl_g = u_geoms([n1750_id.get("4191", Polygon()).intersection(fl_basin), us_states_poly.get("Florida", Polygon()).intersection(fl_basin)])
  sp1_nm_g = n1750_id.get("4191", Polygon()).intersection(u_geoms([h2_u([13]), h4_u(["1502", "1504", "1505", "1506", "1508"])]))
  sp1_tx_g = n1750_id.get("4191", Polygon()).intersection(u_geoms([h2_u([12]), h4_u(["1308", "1309"])]))
  fr1_la_g = n1750_id.get("4427", Polygon()).intersection(u_geoms([h2_u([8]), h4_u(["0317", "0318", "0512", "0514", "0713", "0714"])]))
  trans_app_g = u_geoms([
    n1750_id.get("4066"),
    n1754_w if False else Polygon(),
    h2_u([4, 5, 6]),
    h4_u(["0315", "0316", "0317", "0318"]),
    us_states_poly.get("New York", Polygon()),
  ])
  plains1_g = h2_u([7, 9, 10, 11])
  farwest1_g = u_geoms([h2_u([14, 15, 16, 17, 18]), us_states_poly.get("California", Polygon())])

  m_us_all = mask_us48 | mask_ak | mask_bm
  ca1_geoms = {gid: g for gid, _pid, g in c13_specs_1750}
  ca1_geoms.update({
    14: adm0_geoms.get("Bermuda", Polygon()),
    15: sp1_fl_g, 16: sp1_nm_g, 17: sp1_tx_g, 18: fr1_la_g,
    19: trans_app_g, 20: plains1_g, 21: farwest1_g, 22: us_ak_geom,
  })
  ca1_order = [(14, ca1_geoms[14])] + [(gid, ca1_geoms[gid]) for gid in range(1, 14)] + [
    (15, sp1_fl_g), (16, sp1_nm_g), (17, sp1_tx_g), (18, fr1_la_g),
    (19, trans_app_g), (20, plains1_g), (21, farwest1_g), (22, us_ak_geom),
  ]
  g9 = ordered_raster_partition(m_us_all, ca1_order)
  g9[mask_bm] = 14
  g9[mask_ak] = 22
  pal9 = distinct_palette(22, 0.08)
  ca1_defs = [
    (1, "ca1_new_hampshire", "1. Province of New Hampshire"),
    (2, "ca1_massachusetts_bay_maine", "2. Province of Massachusetts Bay (incl. District of Maine)"),
    (3, "ca1_rhode_island", "3. Colony of Rhode Island and Providence Plantations"),
    (4, "ca1_connecticut", "4. Colony of Connecticut"),
    (5, "ca1_new_york", "5. Province of New York (incl. Iroquois Mohawk-Hudson)"),
    (6, "ca1_new_jersey", "6. Province of New Jersey"),
    (7, "ca1_pennsylvania", "7. Province of Pennsylvania"),
    (8, "ca1_delaware", "8. Lower Counties on Delaware"),
    (9, "ca1_maryland", "9. Province of Maryland"),
    (10, "ca1_virginia", "10. Colony and Dominion of Virginia (incl. Trans-Allegheny West)"),
    (11, "ca1_north_carolina", "11. Province of North Carolina"),
    (12, "ca1_south_carolina", "12. Province of South Carolina"),
    (13, "ca1_georgia", "13. Province of Georgia"),
    (14, "ca1_bermuda", "14. Colony of Bermuda"),
    (15, "ca1_spanish_florida", "15. Spanish Florida (San Agustin & Apalachee)"),
    (16, "ca1_spanish_new_mexico", "16. Spanish New Mexico & Pimeria Alta Pueblos"),
    (17, "ca1_spanish_texas", "17. Spanish Texas (San Antonio & Presidio Missions)"),
    (18, "ca1_french_louisiana_illinois", "18. French Louisiana, Mobile & Pays des Illinois"),
    (19, "ca1_trans_appalachian_indigenous", "19. Trans-Appalachian Indigenous Nations (Cherokee, Creek, Choctaw, Chickasaw & Ohio Country)"),
    (20, "ca1_plains_indigenous_1754", "20. Great Plains & Upper Missouri Indigenous Nations"),
    (21, "ca1_far_west_indigenous_1754", "21. Far West, Great Basin, California & Columbia Plateau Indigenous Nations"),
    (22, "ca1_alaska_contact_1754", "22. Alaska & Aleutian Russian-Indigenous Early Contact"),
  ]
  write_mask_and_json5(
    CENTAUR_DIR / "4.colonial_america_and_canada/1.colonial_america_to_1754",
    "colonial_america_to_1754",
    {"title": "Colonial America until the Seven Years' War: Thirteen Colonies, Spanish Borderlands, French Louisiana and Indigenous Nations (1500AD-1754AD)", "rel_dir": "4.colonial_america_and_canada/1.colonial_america_to_1754", "domain": [1500, 1754]},
    [{"gid": gid, "key": k, "name": nm, "colour": pal9[gid - 1]} for gid, k, nm in ca1_defs],
    g9, land_area_eff, geom_by_gid=ca1_geoms, clip_geom=u_geoms([us_lower48_geom, us_ak_geom, adm0_geoms.get("Bermuda")]),
    priority_order=[gid for gid, _ in ca1_order]
  )

  # 4.2 COLONIAL AMERICA TO 1783 (1763/1775 .naissance polities + watersheds)
  # Use Transylvania 5482 + KY watershed 0510/0511, Watauga/Cumberland 0601/0513, Vermont 5493, Alta California coastal 1805/1806/1807 in 1775 Spanish America, East/West Florida 5428/5429
  ca2_geoms = dict(ca1_geoms)
  ca2_geoms[15] = u_geoms([n1775_id.get("5428"), n1775_id.get("5429"), sp1_fl_g])
  ca2_geoms[18] = u_geoms([n1775_id.get("4191", Polygon()).intersection(u_geoms([h2_u([8]), h4_u(["0714", "1114", "1101"])])), fr1_la_g])
  ca2_geoms[23] = u_geoms([n1775_id.get("5482"), h4_u(["0510", "0511"])])  # Kentucky frontier
  ca2_geoms[24] = h4_u(["0601", "0602", "0513"])  # Watauga Upper Tennessee & Cumberland Nashville Basin
  ca2_geoms[25] = u_geoms([n1782_id.get("5493"), us_states_poly.get("Vermont")])  # Republic of Vermont
  ca2_geoms[26] = n1775_id.get("4191", Polygon()).intersection(h4_u(["1805", "1806", "1807"]))  # Spanish Alta California coastal corridor

  ca2_order = [
    (14, ca2_geoms[14]), (25, ca2_geoms[25]), (23, ca2_geoms[23]), (24, ca2_geoms[24]), (26, ca2_geoms[26]),
  ] + [(gid, ca2_geoms[gid]) for gid in range(1, 14)] + [
    (15, ca2_geoms[15]), (16, ca2_geoms[16]), (17, ca2_geoms[17]), (18, ca2_geoms[18]),
    (19, ca2_geoms[19]), (20, ca2_geoms[20]), (21, ca2_geoms[21]), (22, ca2_geoms[22]),
  ]
  g10 = ordered_raster_partition(m_us_all, ca2_order)
  g10[mask_bm] = 14
  g10[mask_ak] = 22
  pal10 = distinct_palette(26, 0.14)
  ca2_defs = ca1_defs + [
    (23, "ca2_kentucky_frontier", "23. Kentucky Frontier District (Boonesborough, Harrodsburg & Louisville)"),
    (24, "ca2_watauga_cumberland_frontier", "24. Watauga & Cumberland Frontier Settlements (Tennessee)"),
    (25, "ca2_vermont_republic", "25. New Hampshire Grants / Republic of Vermont"),
    (26, "ca2_alta_california_missions", "26. Spanish Alta California Missions & Presidios (1769-1783)"),
  ]
  write_mask_and_json5(
    CENTAUR_DIR / "4.colonial_america_and_canada/2.colonial_america_to_1783",
    "colonial_america_to_1783",
    {"title": "Colonial America until the Treaty of Paris: Imperial Wars, Provincial Censuses and Revolutionary Settlement Shifts (1754AD-1783AD)", "rel_dir": "4.colonial_america_and_canada/2.colonial_america_to_1783", "domain": [1754, 1783]},
    [{"gid": gid, "key": k, "name": nm, "colour": pal10[gid - 1]} for gid, k, nm in ca2_defs],
    g10, land_area_eff, geom_by_gid=ca2_geoms, clip_geom=u_geoms([us_lower48_geom, us_ak_geom, adm0_geoms.get("Bermuda")]),
    priority_order=[gid for gid, _ in ca2_order]
  )

  # 4.3 COLONIAL CANADA TO 1763 (.naissance New France / British North America / Greenland + Watersheds)
  m_ca_all = mask_ca | mask_pm | mask_gl
  nf1750 = n1750_id.get("4427", Polygon())
  bna1750 = n1750_id.get("4684", Polygon())
  cc1_1_g = u_geoms([sl3_g, sl4_g, sl2_g, nf1750.intersection(ca_provs["Québec"])]).intersection(u_geoms([hb_range(hb_na4, 7238, 7254), hb_na4.get(7260), ca_ecozone_by_id.get("CL08")]))
  cc1_2_g = u_geoms([ca_provs["Nova Scotia"], ca_provs["New Brunswick"], ca_provs["Prince Edward Island"]])
  cc1_3_g = u_geoms([ca_provs["Newfoundland and Labrador"], pm_all_geom])
  cc1_4_g = u_geoms([sl1_g, sl2_g, h4_u(["0416", "0417", "0420", "0421", "0422", "0423", "0425", "0427", "0429"])]).intersection(ca_provs["Ontario"])
  cc1_5_g = u_geoms([bna1750, m4_geom, wmo_by_id.get(414)])
  cc1_6_g = u_geoms([m3_geom, wmo_by_id.get(413)])
  cc1_7_g = u_geoms([ca_provs["British Columbia"], ca_provs["Yukon"], ca_provs["Northwest Territories"], mack_g])
  cc1_8_g = gl_all_geom

  g11 = ordered_raster_partition(m_ca_all, [
    (8, cc1_8_g), (2, cc1_2_g), (3, cc1_3_g), (1, cc1_1_g), (4, cc1_4_g), (5, cc1_5_g), (6, cc1_6_g), (7, cc1_7_g),
  ])
  g11[mask_gl] = 8
  g11[mask_pm] = 3
  pal11 = distinct_palette(8, 0.31)
  cc1_defs = [
    (1, "cc1_new_france_st_lawrence", "1. New France: Governments of Quebec, Trois-Rivieres & Montreal"),
    (2, "cc1_acadia_nova_scotia_ile_royale", "2. Acadia, Nova Scotia, Ile Royale (Louisbourg) & Ile Saint-Jean"),
    (3, "cc1_newfoundland_labrador_st_pierre", "3. Newfoundland (Avalon & Plaisance), Labrador & Saint-Pierre"),
    (4, "cc1_pays_den_haut_ontario", "4. Pays d'en Haut & Great Lakes Fur-Trade Posts (Southern Ontario)"),
    (5, "cc1_ruperts_land_hbc", "5. Rupert's Land & Hudson's Bay Company Trading Factory Zones"),
    (6, "cc1_western_prairies_verendrye", "6. Western Prairies & French-Indigenous Saskatchewan Posts"),
    (7, "cc1_pacific_mackenzie_indigenous", "7. Pacific Northwest Coast, Yukon & Mackenzie River Nations"),
    (8, "cc1_greenland_missions_1763", "8. Greenland (Danish-Moravian Missions 1721-1763 & Independent Kalaallit)"),
  ]
  write_mask_and_json5(
    CENTAUR_DIR / "4.colonial_america_and_canada/3.colonial_canada_to_1763",
    "colonial_canada_to_1763",
    {"title": "Colonial Canada until the Seven Years' War: New France Censuses, Acadia, Newfoundland and Greenland (1500AD-1763AD)", "rel_dir": "4.colonial_america_and_canada/3.colonial_canada_to_1763", "domain": [1500, 1763]},
    [{"gid": gid, "key": k, "name": nm, "colour": pal11[gid - 1]} for gid, k, nm in cc1_defs],
    g11, land_area_eff,
    geom_by_gid={1: cc1_1_g, 2: cc1_2_g, 3: cc1_3_g, 4: cc1_4_g, 5: cc1_5_g, 6: cc1_6_g, 7: cc1_7_g, 8: cc1_8_g},
    clip_geom=u_geoms([ca_all_geom, pm_all_geom, gl_all_geom]),
    priority_order=[8, 2, 3, 1, 4, 5, 6, 7]
  )

  # 4.4 COLONIAL CANADA TO 1867 (Uses exact Red River Colony 5950 polygon from .naissance!)
  rr_geom = n1850_id.get("5950", Polygon())
  cc2_geoms = {
    1: ca_provs["Québec"], 2: ca_provs["Ontario"], 3: ca_provs["Nova Scotia"],
    4: ca_provs["New Brunswick"], 5: ca_provs["Prince Edward Island"],
    6: ca_provs["Newfoundland and Labrador"], 7: pm_all_geom,
    8: rr_geom,
    9: u_geoms([ca_provs["Manitoba"], ca_provs["Saskatchewan"], ca_provs["Alberta"]]),
    10: ca_provs["British Columbia"],
    11: u_geoms([ca_provs["Yukon"], ca_provs["Northwest Territories"], ca_provs["Nunavut"]]),
    12: gl_all_geom,
  }
  g12 = ordered_raster_partition(m_ca_all, [
    (12, cc2_geoms[12]), (7, cc2_geoms[7]), (1, cc2_geoms[1]), (2, cc2_geoms[2]),
    (3, cc2_geoms[3]), (4, cc2_geoms[4]), (5, cc2_geoms[5]), (6, cc2_geoms[6]),
    (8, cc2_geoms[8]), (9, cc2_geoms[9]), (10, cc2_geoms[10]), (11, cc2_geoms[11]),
  ])
  g12[mask_pm] = 7
  g12[mask_gl] = 12
  pal12 = distinct_palette(12, 0.42)
  cc2_defs = [
    (1, "cc2_lower_canada_quebec", "1. Lower Canada / Canada East (Province of Quebec)"),
    (2, "cc2_upper_canada_ontario", "2. Upper Canada / Canada West (Province of Ontario)"),
    (3, "cc2_nova_scotia", "3. Colony of Nova Scotia & Cape Breton"),
    (4, "cc2_new_brunswick", "4. Colony of New Brunswick"),
    (5, "cc2_prince_edward_island", "5. Colony of Prince Edward Island"),
    (6, "cc2_newfoundland_labrador", "6. Colony of Newfoundland and Labrador"),
    (7, "cc2_saint_pierre_miquelon", "7. French Colony of Saint-Pierre and Miquelon"),
    (8, "cc2_red_river_assiniboia", "8. District of Assiniboia / Red River Settlement"),
    (9, "cc2_ruperts_land_prairies", "9. Rupert's Land Prairies & Hudson's Bay Interior"),
    (10, "cc2_british_columbia_vancouver_isl", "10. Colonies of Vancouver Island & British Columbia"),
    (11, "cc2_north_western_territory_arctic", "11. North-Western Territory & High Arctic"),
    (12, "cc2_greenland_inspectorates", "12. Danish Inspectorates of North & South Greenland and East Greenland"),
  ]
  write_mask_and_json5(
    CENTAUR_DIR / "4.colonial_america_and_canada/4.colonial_canada_to_1867",
    "colonial_canada_to_1867",
    {"title": "Colonial Canada until Confederation: British North American Censuses, Assiniboia, British Columbia and Greenland (1763AD-1867AD)", "rel_dir": "4.colonial_america_and_canada/4.colonial_canada_to_1867", "domain": [1763, 1867]},
    [{"gid": gid, "key": k, "name": nm, "colour": pal12[gid - 1]} for gid, k, nm in cc2_defs],
    g12, land_area_eff, geom_by_gid=cc2_geoms, clip_geom=u_geoms([ca_all_geom, pm_all_geom, gl_all_geom]),
    priority_order=[12, 7, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11]
  )

  # ------------------------------------------------------------------
  # 5. MODERN CANADA & UNITED STATES (Regime III Admin-1)
  # ------------------------------------------------------------------
  print("\n=== Generating Modern Canada & United States Masks (Regime III) ===")
  g13 = ca_prov_grid.copy()
  pm_gid = len(ca_prov_order) + 1
  gl_gid = len(ca_prov_order) + 2
  g13[mask_pm] = pm_gid
  g13[mask_gl] = gl_gid
  g13 = np.where(m_ca_all, g13, 0)
  g13 = nearest_fill(m_ca_all, g13, range(1, gl_gid + 1))
  pal13 = distinct_palette(gl_gid, 0.55)
  can_mod_defs = []
  can_geoms = {}
  for i, nm in enumerate(ca_prov_order, start=1):
    slug_p = nm.lower().replace("é", "e").replace(" ", "_")
    can_mod_defs.append({"gid": i, "key": f"can_{slug_p}", "name": f"{i}. {nm}", "colour": pal13[i - 1]})
    can_geoms[i] = ca_provs.get(nm, Polygon())
  can_mod_defs.append({"gid": pm_gid, "key": "can_saint_pierre_miquelon", "name": f"{pm_gid}. Saint Pierre and Miquelon", "colour": pal13[pm_gid - 1]})
  can_mod_defs.append({"gid": gl_gid, "key": "can_greenland", "name": f"{gl_gid}. Greenland (Kalaallit Nunaat)", "colour": pal13[gl_gid - 1]})
  can_geoms[pm_gid] = pm_all_geom
  can_geoms[gl_gid] = gl_all_geom
  write_mask_and_json5(
    CENTAUR_DIR / "5.modern_canada_and_united_states/1.canada_post_confederation",
    "canada_post_confederation",
    {"title": "Canada after Confederation, Greenland and Saint-Pierre-et-Miquelon: Census Demography and Northern Urbanisation (1867AD-2026AD)", "rel_dir": "5.modern_canada_and_united_states/1.canada_post_confederation", "domain": [1867, 2026]},
    can_mod_defs, g13, land_area_eff, geom_by_gid=can_geoms
  )

  m_us_mod = mask_us48 | mask_ak | mask_hi | mask_bm | mask_as
  g14 = us_state_grid.copy()
  bm_gid = len(us_state_names) + 1
  as_gid = len(us_state_names) + 2
  g14[mask_bm] = bm_gid
  g14[mask_as] = as_gid
  g14 = np.where(m_us_mod, g14, 0)
  g14 = nearest_fill(m_us_mod, g14, range(1, as_gid + 1))
  pal14 = distinct_palette(as_gid, 0.72)
  us_mod_defs = []
  us_geoms = {}
  for i, nm in enumerate(us_state_names, start=1):
    slug_s = nm.lower().replace(" ", "_")
    entry = {"gid": i, "key": f"usa_{slug_s}", "name": f"{i}. {nm}", "colour": pal14[i - 1]}
    if nm == "Hawaii":
      entry["domain"] = [1898, 2026]
    elif nm == "Alaska":
      entry["domain"] = [1867, 2026]
    us_mod_defs.append(entry)
    us_geoms[i] = us_states_poly.get(nm, Polygon())
  us_mod_defs.append({"gid": bm_gid, "key": "usa_bermuda", "name": f"{bm_gid}. Bermuda", "colour": pal14[bm_gid - 1]})
  us_mod_defs.append({"gid": as_gid, "key": "usa_american_samoa", "name": f"{as_gid}. American Samoa", "colour": pal14[as_gid - 1], "domain": [1900, 2026]})
  us_geoms[bm_gid] = adm0_geoms.get("Bermuda", Polygon())
  us_geoms[as_gid] = as_all_geom
  write_mask_and_json5(
    CENTAUR_DIR / "5.modern_canada_and_united_states/2.united_states_post_independence",
    "united_states_post_independence",
    {"title": "United States after Independence: Decennial Census Demography, Westward Expansion and Metropolitan Growth (1783AD-2026AD)", "rel_dir": "5.modern_canada_and_united_states/2.united_states_post_independence", "domain": [1783, 2026]},
    us_mod_defs, g14, land_area_eff, geom_by_gid=us_geoms
  )

  # Domain coverage check & kriging domain masks
  pre_union = pre_ca_domain | mask_us48 | mask_hi | mask_as
  mod_union = m_ca_all | m_us_mod
  diff_pre_mod = (pre_union ^ mod_union) & (~mask_bm)
  print(f"\n[COVERAGE CHECK] Pre-Columbian union px={pre_union.sum()}, Modern union px={mod_union.sum()}, Diff (excl Bermuda)={diff_pre_mod.sum()}")

  na_dom = np.zeros((H, W, 4), dtype=np.uint8)
  dom1 = (mask_us48 | mask_ak | mask_ca | mask_gl | mask_pm)
  na_dom[dom1] = [255, 255, 255, 255]
  Image.fromarray(na_dom, mode="RGBA").save(CENTAUR_DIR / "_shared/sites_northern_america/config/centaur_na_domain_mask.png")

  hp_dom = np.zeros((H, W, 4), dtype=np.uint8)
  hp_dom[m_hp] = [255, 255, 255, 255]
  Image.fromarray(hp_dom, mode="RGBA").save(CENTAUR_DIR / "_shared/sites_hawaii_polynesia/config/centaur_hp_domain_mask.png")

  np.savez_compressed(
    CACHE_DIR / "centaur_pixel_grids.npz",
    us_state_grid=us_state_grid.astype(np.uint8),
    ca_prov_grid=ca_prov_grid.astype(np.uint8),
    us_huc_grid=us_huc_grid.astype(np.uint8),
    ca_macro=ca_macro.astype(np.uint8),
    pre_union=pre_union.astype(np.uint8),
    mod_union=mod_union.astype(np.uint8),
    land_area=land_area_eff.astype(np.int32),
  )
  print("Saved centaur_pixel_grids.npz, chapter_subregions/*.geojson, and domain mask PNGs.")


if __name__ == "__main__":
  main()
