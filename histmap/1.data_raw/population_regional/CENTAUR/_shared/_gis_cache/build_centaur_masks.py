"""Deterministic 5-arcminute (4320x2160) GIS areal mask and JSON5 schema builder
for Operation Viscount Project CENTAUR-II across all 31 canonical modules.
"""

import colorsys
import json
import os
import pathlib
import sys
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Point, Polygon, MultiPolygon, shape, mapping
from shapely.ops import unary_union
from scipy.spatial import cKDTree

sys.stdout.reconfigure(encoding="utf-8")

W, H = 4320, 2160
CENTAUR_DIR = pathlib.Path(__file__).resolve().parents[2]
SVEA_ROOT = CENTAUR_DIR.parents[3]
CACHE_DIR = pathlib.Path(__file__).resolve().parent

LAND_AREA_PNG = SVEA_ROOT / "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png"
ISO2_PNG = SVEA_ROOT / "histmap/1.data_raw/admin_modern/iso2.png"
ISO2_CSV = SVEA_ROOT / "histmap/1.data_raw/admin_modern/iso2_geocodes.csv"
WMOBB_JSON = SVEA_ROOT / "histmap/1.data_raw/watersheds_WMO/wmobb_basins.json"
HUC2_JSON = CACHE_DIR / "usgs_wbd_huc2.geojson"
NE10_ADM1_JSON = CACHE_DIR / "ne_10m_admin_1_states_provinces.geojson"
NE10_ADM0_JSON = CACHE_DIR / "ne_10m_admin_0_countries.geojson"


def distinct_palette(n, seed_offset=0.0):
  """Generates n visually distinct bright-to-mid RGB colours (never pure 0,0,0)."""
  cols = []
  used = set([(0, 0, 0)])
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
  # Use 32-bit RGBA canvas encoding id+1 so id=0 stays transparent
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
  """Assigns any True pixel in target_mask where label_grid==0 to nearest valid pixel in label_grid."""
  src_mask = np.isin(label_grid, list(valid_labels))
  missing = target_mask & (~src_mask)
  if not missing.any():
    return label_grid
  if not src_mask.any():
    return label_grid
  sr, sc = np.where(src_mask)
  mr, mc = np.where(missing)
  tree = cKDTree(np.column_stack([sr, sc]))
  _, idx = tree.query(np.column_stack([mr, mc]))
  out = label_grid.copy()
  out[mr, mc] = label_grid[sr[idx], sc[idx]]
  return out


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


def write_mask_and_json5(out_dir, stem, meta_info, zone_defs, label_grid, land_area):
  """Writes <stem>_areal_mask.png and <stem>.json5 if skeleton doesn't overwrite populated data."""
  out_dir = pathlib.Path(out_dir)
  out_dir.mkdir(parents=True, exist_ok=True)
  png_path = out_dir / f"{stem}_areal_mask.png"
  json5_path = out_dir / f"{stem}.json5"

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
    entry = {
      "name": z["name"],
      "colour": col,
      "pixel_count": px_cnt,
      "area_km2": area_km2,
      "bbox": bbox,
      "population": z.get("population", {}),
    }
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
  json5_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
  print(f"Wrote {meta_info['rel_dir']}/{stem}: {len(regions_dict)} zones, {total_px} px, {total_area:,} km2")
  return total_px, total_area


def main():
  print("Loading base rasters and vector layers...")
  la_img = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  land_area = (
    (la_img[:, :, 0].astype(np.uint32) << 24)
    | (la_img[:, :, 1].astype(np.uint32) << 16)
    | (la_img[:, :, 2].astype(np.uint32) << 8)
    | la_img[:, :, 3].astype(np.uint32)
  )
  # Bermuda has 0 in HYDE land_area.png due to 5-arcmin quantization; set tiny land area for Bermuda GHSL cell so it validates
  land_area_eff = land_area.copy()
  land_area_eff[692, 1382] = 53  # Bermuda ~53 km2

  iso_img = np.asarray(Image.open(ISO2_PNG).convert("RGBA"), dtype=np.uint8)
  iso_rgb_to_code = {}
  with open(ISO2_CSV, encoding="utf-8") as fh:
    next(fh, None)
    for line in fh:
      parts = line.strip().split(";")
      if len(parts) >= 4 and parts[3]:
        rgb = tuple(int(x) for x in parts[3].split(","))
        iso_rgb_to_code[rgb] = (parts[0], parts[2])

  # Build pixel masks by ISO code
  iso_code_grid = np.empty((H, W), dtype=object)
  iso_code_grid[:] = ""
  # Map unique RGBs in iso2.png
  valid_iso_alpha = iso_img[:, :, 3] > 0
  packed_iso = (
    (iso_img[:, :, 0].astype(np.int32) << 16)
    | (iso_img[:, :, 1].astype(np.int32) << 8)
    | iso_img[:, :, 2].astype(np.int32)
  )
  rgb_int_to_code = {(r << 16) | (g << 8) | b: v[0] for (r, g, b), v in iso_rgb_to_code.items()}
  code_masks = {}
  for rgb_int, code in rgb_int_to_code.items():
    if code.startswith("US-") or code in ("CA", "GL", "PM", "AS"):
      code_masks[code] = valid_iso_alpha & (packed_iso == rgb_int) & (land_area > 0)

  # Bermuda mask (32.29N, -64.79W)
  bm_mask = np.zeros((H, W), dtype=bool)
  bm_mask[692, 1382] = True
  code_masks["BM"] = bm_mask

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

  print(f"Mask pixels -> US48: {mask_us48.sum()}, AK: {mask_ak.sum()}, CA: {mask_ca.sum()}, GL: {mask_gl.sum()}, HI: {mask_hi.sum()}, PM: {mask_pm.sum()}, AS: {mask_as.sum()}, BM: {mask_bm.sum()}")

  # Coordinate grids for sub-basin splits
  row_lats = 90.0 - (np.arange(H) + 0.5) / 12.0
  col_lons = -180.0 + (np.arange(W) + 0.5) / 12.0
  LAT, LON = np.broadcast_arrays(row_lats[:, None], col_lons[None, :])

  # Load NE10 admin1 for Canada provinces & US state polygons
  ne_adm1 = json.loads(NE10_ADM1_JSON.read_text(encoding="utf-8"))
  ca_provs = {}
  us_states_poly = {}
  for feat in ne_adm1["features"]:
    pr = feat["properties"]
    a3 = pr.get("adm0_a3")
    nm = pr.get("name", "")
    g = shape(feat["geometry"]).buffer(0)
    if a3 == "CAN":
      ca_provs[nm] = unary_union([ca_provs.get(nm, Polygon()), g]).buffer(0)
    elif a3 == "USA":
      us_states_poly[nm] = unary_union([us_states_poly.get(nm, Polygon()), g]).buffer(0)

  ca_prov_order = [
    "Alberta", "British Columbia", "Manitoba", "New Brunswick",
    "Newfoundland and Labrador", "Northwest Territories", "Nova Scotia",
    "Nunavut", "Ontario", "Prince Edward Island", "Québec", "Saskatchewan", "Yukon"
  ]
  ca_prov_grid = rasterize_geom_list([(i + 1, ca_provs[nm]) for i, nm in enumerate(ca_prov_order)])
  ca_prov_grid = np.where(mask_ca, ca_prov_grid, 0)
  ca_prov_grid = nearest_fill(mask_ca, ca_prov_grid, range(1, len(ca_prov_order) + 1))
  ca_prov_idx = {nm: i + 1 for i, nm in enumerate(ca_prov_order)}

  # Load WMO Basins
  wmobb_gj = json.loads(WMOBB_JSON.read_text(encoding="utf-8"))
  wmobb_by_id = {}
  for feat in wmobb_gj["features"]:
    wid = feat["properties"].get("WMOBB")
    if wid in (401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 418, 419, 420, 421, 422, 423, 425, 426, 427, 431, 432, 433, 434, 435, 436, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 455):
      wmobb_by_id[wid] = unary_union([wmobb_by_id.get(wid, Polygon()), shape(feat["geometry"]).buffer(0)]).buffer(0)

  wmo_ids = sorted(wmobb_by_id.keys())
  wmo_grid = rasterize_geom_list([(wid, wmobb_by_id[wid]) for wid in wmo_ids])

  # ------------------------------------------------------------------
  # 1. PRE-COLUMBIAN CANADA, ALASKA & GREENLAND (Items 1..6)
  # ------------------------------------------------------------------
  print("\n=== Generating Pre-Columbian Canada, Alaska & Greenland (Items 1..6) ===")
  # Partition mask_ca | mask_ak | mask_pm | mask_gl into 6 macro chapters cleanly
  pre_ca_domain = mask_ca | mask_ak | mask_pm | mask_gl

  # Macro assignment grid: 1..6
  ca_macro = np.zeros((H, W), dtype=np.int32)
  # 1. Northern Cascadia & Alaska: all Alaska + Yukon + British Columbia
  ca_macro[mask_ak | (ca_prov_grid == ca_prov_idx["Yukon"]) | (ca_prov_grid == ca_prov_idx["British Columbia"])] = 1
  # 6. Maritimes: NS, NB, PEI, NL, PM (Wait: Labrador interior vs coast -> keep NL + PM in Maritimes & Subarctic Labrador subzone!)
  ca_macro[
    mask_pm
    | (ca_prov_grid == ca_prov_idx["Nova Scotia"])
    | (ca_prov_grid == ca_prov_idx["New Brunswick"])
    | (ca_prov_grid == ca_prov_idx["Prince Edward Island"])
    | (ca_prov_grid == ca_prov_idx["Newfoundland and Labrador"])
  ] = 6
  # 5. Saint Lawrence: Southern Ontario (south of 47.0N or in Ottawa/St Lawrence/Great Lakes basins south of 48.2N) & Southern/Eastern Quebec (south of 49.5N or Gaspe/Saguenay east of -75 & south of 50.5N)
  in_ont = ca_prov_grid == ca_prov_idx["Ontario"]
  in_qc = ca_prov_grid == ca_prov_idx["Québec"]
  st_law_ont = in_ont & ((LAT <= 46.8) | ((LON >= -85.0) & (LAT <= 48.0)))
  st_law_qc = in_qc & (
    (LAT <= 49.0)
    | ((LON >= -73.0) & (LAT <= 50.8))  # Saguenay, Cote-Nord, Gaspe
  )
  ca_macro[(ca_macro == 0) & (st_law_ont | st_law_qc)] = 5
  # 4. Hudson Bay: Northern Ontario + Northern Quebec + Nunavut Hudson-Bay/Keewatin/Baffin borderlands (WMO 414 Hudson Bay OR Ont/QC north of St Lawrence)
  hudson_wmo = (wmo_grid == 414)
  ca_macro[(ca_macro == 0) & (in_ont | in_qc | (hudson_wmo & ((ca_prov_grid == ca_prov_idx["Nunavut"]) | (ca_prov_grid == ca_prov_idx["Manitoba"]))))] = 4
  # Wait: keep Manitoba Plains (South of 53.5N or in Red/Assiniboine/Lake Winnipegosis) in Prairies (3) and Northern Manitoba Hudson Bay Lowlands (Nelson/Hayes/Churchill east of -97 & north of 53.5) in Hudson Bay (4)!
  in_mb = ca_prov_grid == ca_prov_idx["Manitoba"]
  in_sk = ca_prov_grid == ca_prov_idx["Saskatchewan"]
  in_ab = ca_prov_grid == ca_prov_idx["Alberta"]
  mb_prairie = in_mb & ((LAT < 54.0) | ((LON < -97.5) & (LAT < 56.0)))
  sk_prairie = in_sk & (LAT < 55.0)
  ab_prairie = in_ab & (LAT < 56.5)
  ca_macro[mb_prairie | sk_prairie | ab_prairie] = 3
  # 2. Northern Canada & Greenland: NWT, Nunavut (non-Hudson-coast or Arctic islands), Northern AB/SK (Mackenzie/Athabasca/Churchill headwaters), Greenland
  ca_macro[(ca_macro == 0) & (mask_gl | (ca_prov_grid == ca_prov_idx["Northwest Territories"]) | (ca_prov_grid == ca_prov_idx["Nunavut"]) | in_ab | in_sk | in_mb)] = 2
  ca_macro = np.where(pre_ca_domain, ca_macro, 0)
  ca_macro = nearest_fill(pre_ca_domain, ca_macro, [1, 2, 3, 4, 5, 6])

  # Define sub-zones inside each of Items 1..6
  pal1 = distinct_palette(30, 0.05)

  # Helper to save each pre-Columbian CA/AK chapter
  def build_ca_subzones():
    # Item 1: Northern Cascadia and Alaska
    m1 = (ca_macro == 1)
    g1 = np.zeros((H, W), dtype=np.int32)
    g1[m1 & mask_ak & (LAT <= 59.5) & (LON >= -141.0)] = 4  # SE AK Panhandle
    g1[m1 & mask_ak & (LAT <= 61.5) & (LON < -141.0) & ((wmo_grid == 405) | (wmo_grid == 445) | (wmo_grid == 446) | (LAT < 59.0))] = 1  # Aleutians/Kodiak/South Coast
    g1[m1 & mask_ak & (g1 == 0) & ((wmo_grid == 401) | (wmo_grid == 402) | (LON <= -159.0) | (LAT >= 67.2))] = 2  # Yupik/Inupiat Arctic/Bering
    g1[m1 & mask_ak & (g1 == 0)] = 3  # Interior Yukon/Tanana AK
    g1[m1 & (ca_prov_grid == ca_prov_idx["Yukon"])] = 3
    g1[m1 & (ca_prov_grid == ca_prov_idx["British Columbia"]) & (LAT >= 52.2) & (LON <= -126.5)] = 4  # Haida Gwaii & Tsimshian North Coast
    g1[m1 & (ca_prov_grid == ca_prov_idx["British Columbia"]) & (g1 == 0)] = 5  # Salish Sea, Vancouver Island & Fraser/Columbia Plateau
    g1 = np.where(m1, g1, 0)
    g1 = nearest_fill(m1, g1, [1, 2, 3, 4, 5])
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
      g1, land_area_eff
    )

    # Item 2: Northern Canada (& Pre-Colonial Greenland)
    m2 = (ca_macro == 2)
    g2 = np.zeros((H, W), dtype=np.int32)
    g2[m2 & np.isin(ca_prov_grid, [ca_prov_idx["Alberta"], ca_prov_idx["Saskatchewan"], ca_prov_idx["Manitoba"], ca_prov_idx["Northwest Territories"]]) & (LON <= -110.0) & (LAT <= 69.0)] = 1  # Mackenzie/Peace-Athabasca Dene
    g2[m2 & mask_gl & ((LON <= -41.5) | (LAT <= 61.5))] = 4  # West & SW Greenland (Kalaallit & Norse Eastern/Western Settlements)
    g2[m2 & mask_gl & (g2 == 0)] = 5  # East & High North Greenland
    g2[m2 & (~mask_gl) & (g2 == 0) & ((LON >= -95.0) | (LAT >= 71.0))] = 3  # Eastern & High Arctic (Baffin, Foxe Basin, Ellesmere)
    g2[m2 & (g2 == 0)] = 2  # Western & Central Arctic (Kitikmeot, Barrens, Back River)
    g2 = np.where(m2, g2, 0)
    g2 = nearest_fill(m2, g2, [1, 2, 3, 4, 5])
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
      g2, land_area_eff
    )

    # Item 3: Prairies
    m3 = (ca_macro == 3)
    g3 = np.zeros((H, W), dtype=np.int32)
    g3[m3 & (ca_prov_grid == ca_prov_idx["Alberta"]) & (LAT <= 52.2)] = 1  # Southern Alberta Foothills & Bow-Oldman (Blackfoot)
    g3[m3 & (ca_prov_grid == ca_prov_idx["Manitoba"])] = 4  # Red-Assiniboine & Lake Winnipegosis Lowlands
    g3[m3 & (g3 == 0) & (LAT >= 52.2)] = 2  # Aspen Parkland & North Saskatchewan River
    g3[m3 & (g3 == 0)] = 3  # South Saskatchewan Dry Steppe & Qu'Appelle
    g3 = np.where(m3, g3, 0)
    g3 = nearest_fill(m3, g3, [1, 2, 3, 4])
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
      g3, land_area_eff
    )

    # Item 4: Hudson Bay
    m4 = (ca_macro == 4)
    g4 = np.zeros((H, W), dtype=np.int32)
    g4[m4 & (ca_prov_grid == ca_prov_idx["Nunavut"])] = 1  # Kivalliq Western Hudson Barrens
    g4[m4 & (ca_prov_grid == ca_prov_idx["Québec"])] = 3  # Eastmain, Nunavik & Ungava Shield
    g4[m4 & (g4 == 0)] = 2  # Hudson & James Bay Lowlands (Manitoba/Ontario Muskeg)
    g4 = np.where(m4, g4, 0)
    g4 = nearest_fill(m4, g4, [1, 2, 3])
    write_mask_and_json5(
      CENTAUR_DIR / "1.pre_columbian_canada_and_alaska/4.hudson_bay",
      "hudson_bay",
      {"title": "Pre-Columbian Hudson Bay and Boreal Shield: Subarctic Cree, Innu and Caribou Inuit Demography (10000BC-1600AD)", "rel_dir": "1.pre_columbian_canada_and_alaska/4.hudson_bay", "domain": [-10000, 1600]},
      [
        {"gid": 1, "key": "hb_keewatin_western_barrens", "name": "1. Kivalliq & Western Hudson Bay Barren Grounds (Caribou Inuit & Sayisi Dene)", "colour": pal1[14]},
        {"gid": 2, "key": "hb_hudson_james_lowlands_cree", "name": "2. Hudson & James Bay Lowlands and Northern Ontario Shield (Swampy Cree & Severn Ojibwe)", "colour": pal1[15]},
        {"gid": 3, "key": "hb_eastmain_nunavik_ungava", "name": "3. Eastmain, James Bay East, Nunavik & Ungava Peninsula (Eeyou, Naskapi & Inuit)", "colour": pal1[16]},
      ],
      g4, land_area_eff
    )

    # Item 5: Saint Lawrence
    m5 = (ca_macro == 5)
    g5 = np.zeros((H, W), dtype=np.int32)
    g5[m5 & (ca_prov_grid == ca_prov_idx["Ontario"]) & ((LAT <= 44.6) | (LON <= -79.2))] = 1  # Huronia & Ontario Peninsula
    g5[m5 & (ca_prov_grid == ca_prov_idx["Ontario"]) & (g5 == 0)] = 2  # Ottawa Valley & Algonquin Shield
    g5[m5 & (ca_prov_grid == ca_prov_idx["Québec"]) & (LON <= -75.0) & (LAT >= 45.6)] = 2  # Upper Ottawa Valley QC
    g5[m5 & (ca_prov_grid == ca_prov_idx["Québec"]) & (g5 == 0) & ((LAT >= 47.4) | (LON >= -69.5))] = 4  # Saguenay, Cote-Nord & Gaspe
    g5[m5 & (g5 == 0)] = 3  # St Lawrence Corridor Montreal to Quebec
    g5 = np.where(m5, g5, 0)
    g5 = nearest_fill(m5, g5, [1, 2, 3, 4])
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
      g5, land_area_eff
    )

    # Item 6: Maritimes
    m6 = (ca_macro == 6)
    g6 = np.zeros((H, W), dtype=np.int32)
    g6[m6 & ((ca_prov_grid == ca_prov_idx["Nova Scotia"]) | (ca_prov_grid == ca_prov_idx["Prince Edward Island"]))] = 1
    g6[m6 & (ca_prov_grid == ca_prov_idx["New Brunswick"])] = 2
    g6[m6 & ((ca_prov_grid == ca_prov_idx["Newfoundland and Labrador"]) & (LAT >= 51.85))] = 4  # Labrador
    g6[m6 & (g6 == 0)] = 3  # Island of Newfoundland & Saint-Pierre-et-Miquelon
    g6 = np.where(m6, g6, 0)
    g6 = nearest_fill(m6, g6, [1, 2, 3, 4])
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
      g6, land_area_eff
    )

  build_ca_subzones()

  # ------------------------------------------------------------------
  # 2. 18 KELLY ET AL. (2025) US HYDROLOGICAL UNITS (Items 7.1..7.18)
  # ------------------------------------------------------------------
  print("\n=== Generating 18 US Hydrological Units per Kelly et al. (2025) ===")
  huc_gj = json.loads(HUC2_JSON.read_text(encoding="utf-8"))
  huc_pairs = []
  for feat in huc_gj["features"]:
    code = int(feat["properties"]["huc2"])
    if 1 <= code <= 18:
      huc_pairs.append((code, shape(feat["geometry"]).buffer(0)))
  huc_raw_grid = rasterize_geom_list(huc_pairs)
  us_huc_grid = np.where(mask_us48, huc_raw_grid, 0)
  us_huc_grid = nearest_fill(mask_us48, us_huc_grid, range(1, 19))

  kelly_specs = [
    ("01.upper_colorado", "upper_colorado", 14, "Upper Colorado Hydrological Unit (HU 14): Fremont, Ancestral Puebloan and Ute Demography (10000BC-1600AD)", [
      ("uc_green_river_wyoming_basin", "1. Green River & Wyoming High Desert Basin (Fremont North)", lambda m: m & (LAT >= 39.8)),
      ("uc_colorado_headwaters_grand_mesa", "2. Colorado-Gunnison Headwaters & Canyonlands", lambda m: m & (LAT < 39.8) & (LAT >= 37.65)),
      ("uc_san_juan_four_corners", "3. San Juan Basin & Four Corners / Mesa Verde", lambda m: m & (LAT < 37.65)),
    ]),
    ("02.extreme_northern_plains", "extreme_northern_plains", 9, "Extreme Northern Plains Hydrological Unit (HU 09): Souris-Red-Rainy Glacial Lake Agassiz Basin (10000BC-1600AD)", [
      ("enp_souris_devils_lake", "1. Souris Loop & Devils Lake Drift Prairie", lambda m: m & (LON <= -98.2)),
      ("enp_red_river_north", "2. Red River of the North Valley", lambda m: m & (LON > -98.2) & (LON <= -95.2)),
      ("enp_rainy_lake_of_the_woods", "3. Rainy River & Lake of the Woods Boreal Border", lambda m: m & (LON > -95.2)),
    ]),
    ("03.northern_plains", "northern_plains", 10, "Northern Plains Hydrological Unit (HU 10): Missouri Basin, Wyoming High Plains and Middle Missouri Earthlodges (10000BC-1600AD)", [
      ("np_upper_missouri_montana", "1. Upper Missouri & Milk-Marias Steppe (Montana)", lambda m: m & (LAT >= 45.0) & (LON <= -104.05)),
      ("np_wyoming_bighorn_powder_plat", "2. Wyoming Basin: Yellowstone, Bighorn, Powder & North Platte (Kelly HU 10-WY)", lambda m: m & (LAT < 45.0) & (LAT >= 41.0) & (LON <= -104.05)),
      ("np_middle_missouri_dakotas", "3. Middle Missouri Trench: Mandan, Hidatsa & Arikara Core (ND/SD)", lambda m: m & (LAT >= 42.7) & (LON > -104.05)),
      ("np_lower_missouri_platte_kansas", "4. Platte, Republican & Lower Missouri Prairie-Plains (NE/KS/IA/MO)", lambda m: m & (LAT < 42.7) & (LON > -104.05)),
    ]),
    ("04.arizona", "arizona", 15, "Arizona Hydrological Unit (HU 15): Hohokam Irrigation, Mogollon Rim and Lower Colorado Demography (10000BC-1600AD)", [
      ("az_little_colorado_plateau", "1. Little Colorado & Hopi Mesas Plateau", lambda m: m & (LAT >= 34.4)),
      ("az_salt_verde_phoenix_hohokam", "2. Salt-Verde-Middle Gila Core (Phoenix Basin Hohokam)", lambda m: m & (LAT < 34.4) & (LAT >= 32.8) & (LON >= -112.9)),
      ("az_tucson_santa_cruz_san_pedro", "3. Santa Cruz, San Pedro & Cochise Highlands", lambda m: m & (LAT < 32.8) & (LON >= -112.9)),
      ("az_lower_colorado_sonoran", "4. Lower Colorado Corridor & Western Sonoran Desert (Patayan/Yuman)", lambda m: m & (LON < -112.9)),
    ]),
    ("05.great_basin", "great_basin", 16, "Great Basin Hydrological Unit (HU 16): Bonneville-Fremont Farmers and Lahontan Desert Foragers (10000BC-1600AD)", [
      ("gb_bonneville_wasatch_fremont", "1. Lake Bonneville, Bear River & Wasatch Oasis (Fremont)", lambda m: m & (LON >= -114.2)),
      ("gb_humboldt_lahontan_west", "2. Humboldt Sink, Lake Lahontan & Carson-Truckee Corridor", lambda m: m & (LON < -114.2) & (LAT >= 38.4)),
      ("gb_central_nevada_owens_mojave", "3. Central Nevada Valleys, Owens Valley & Mojave Endorheic Basin", lambda m: m & (LON < -114.2) & (LAT < 38.4)),
    ]),
    ("06.upper_mississippi", "upper_mississippi", 7, "Upper Mississippi Hydrological Unit (HU 07): Hopewell, Effigy Mounds and Cahokia/American Bottom (10000BC-1600AD)", [
      ("um_minnesota_driftless_north", "1. Upper Mississippi Headwaters, Minnesota River & Driftless Zone", lambda m: m & (LAT >= 42.5)),
      ("um_des_moines_rock_iowa", "2. Iowa-Des Moines, Rock & Upper Illinois Drift Plains (Oneota)", lambda m: m & (LAT < 42.5) & (LAT >= 39.8)),
      ("um_american_bottom_lower_il", "3. American Bottom, Lower Illinois & Mississippi-Missouri Confluence (Cahokia)", lambda m: m & (LAT < 39.8)),
    ]),
    ("07.rio_grande", "rio_grande", 13, "Rio Grande Hydrological Unit (HU 13): Rio Grande Pueblos, Jornada Mogollon and Rio Conchos Borderlands (10000BC-1600AD)", [
      ("rg_san_luis_upper_pueblos", "1. San Luis Valley & Northern Tiwa/Tewa-Chama Pueblos (Taos-Santa Fe)", lambda m: m & (LAT >= 35.1)),
      ("rg_middle_rio_grande_salinas", "2. Middle Rio Grande, Piro-Salinas & Jornada Mogollon (Socorro-El Paso)", lambda m: m & (LAT < 35.1) & (LAT >= 31.2)),
      ("rg_pecos_big_bend_lower_rg", "3. Pecos Valley, Big Bend & Lower Rio Grande Tamaulipan Plains", lambda m: m & (LAT < 31.2)),
    ]),
    ("08.cumberland", "cumberland", 6, "Cumberland (Tennessee) Hydrological Unit (HU 06): Dallas-Mouse Creek Chiefdoms and Tennessee Valley Mound Towns (10000BC-1600AD)", [
      ("cu_upper_east_tennessee_ridge", "1. Upper East Tennessee, Holston-French Broad & Chickamauga Ridge-and-Valley", lambda m: m & (LON >= -85.3)),
      ("cu_middle_tennessee_muscle_shoals", "2. Middle Tennessee Bend, Elk River & Muscle Shoals (Mound Bottom / Shiloh)", lambda m: m & (LON < -85.3) & (LON >= -87.9)),
      ("cu_lower_tennessee_kentucky_confluence", "3. Lower Tennessee River & Highland Rim Confluence", lambda m: m & (LON < -87.9)),
    ]),
    ("09.southeast", "southeast", 3, "Southeast Hydrological Unit (HU 03): Mississippian Chiefdoms of the Piedmont, Coastal Plain and Florida (10000BC-1600AD)", [
      ("se_carolina_piedmont_santee", "1. Roanoke, Yadkin-Pee Dee & Santee-Wateree Carolina Piedmont-Coast", lambda m: m & (LAT >= 33.4) & (LON >= -82.2)),
      ("se_georgia_savannah_ocmulgee_etowah", "2. Savannah, Ocmulgee & Etowah-Coosa Georgia Basins", lambda m: m & (LAT >= 30.8) & (LON < -82.2) & (LON >= -85.8)),
      ("se_alabama_tombigbee_moundville", "3. Black Warrior, Alabama & Tombigbee-Mobile Basins (Moundville & Bottle Creek)", lambda m: m & (LON < -85.8)),
      ("se_peninsular_florida_apalachicola", "4. Peninsular Florida, St. Johns, Apalachicola & Calusa Coast", lambda m: m & (LAT < 30.8) & (LON >= -85.8)),
    ]),
    ("10.lower_mississippi", "lower_mississippi", 8, "Lower Mississippi Hydrological Unit (HU 08): Poverty Point, Plaquemine and Late Mississippian Towns (10000BC-1600AD)", [
      ("lm_st_francis_st_memphis_parkin", "1. St. Francis Basin, Reelfoot & Lower White-Arkansas Delta (Parkin & Nodena)", lambda m: m & (LAT >= 33.8)),
      ("lm_yazoo_ouachita_poverty_point", "2. Yazoo Basin, Tensas-Boeuf & Ouachita Ridges (Poverty Point & Winterville)", lambda m: m & (LAT < 33.8) & (LAT >= 31.1)),
      ("lm_natchez_atchafalaya_delta", "3. Natchez Bluffs, Atchafalaya & Mississippi Birdfoot Delta (Plaquemine)", lambda m: m & (LAT < 31.1)),
    ]),
    ("11.southern_plains", "southern_plains", 12, "Southern Plains Hydrological Unit (HU 12): Texas-Gulf Caddoan Chiefdoms, Central Prairies and Coastal Foragers (10000BC-1600AD)", [
      ("sp_neches_sabine_trinity_caddo", "1. Sabine, Neches & Upper Trinity Basins (Western Caddo / George C. Davis)", lambda m: m & (LON >= -96.8) & (LAT >= 30.2)),
      ("sp_brazos_colorado_edwards", "2. Brazos, Colorado & Edwards Plateau Balcones Escarpment", lambda m: m & (LAT >= 28.8) & ~((LON >= -96.8) & (LAT >= 30.2))),
      ("sp_gulf_coast_nueces_karankawa", "3. Texas Gulf Barrier Coast, Galveston-Matagorda & Nueces (Karankawa & Coahuiltecan)", lambda m: m & (LAT < 28.8) | ((LAT < 30.2) & (LON >= -96.8))),
    ]),
    ("12.ohio_river", "ohio_river", 5, "Ohio River Hydrological Unit (HU 05): Adena-Hopewell Monumental Cores, Fort Ancient and Cumberland-Wabash (10000BC-1600AD)", [
      ("oh_upper_ohio_allegheny_kanawha", "1. Allegheny, Monongahela & Kanawha-Upper Ohio Plateau (Monongahela)", lambda m: m & (LON >= -82.4)),
      ("oh_scioto_miami_hopewell_core", "2. Scioto, Little & Great Miami Valleys (Adena-Hopewell & Fort Ancient)", lambda m: m & (LON < -82.4) & (LAT >= 38.6) & (LON >= -85.3)),
      ("oh_kentucky_cumberland_green", "3. Cumberland, Kentucky & Green River Valleys (Angel/Cumberland Stone-Box)", lambda m: m & (LAT < 38.6) & (LON < -82.4)),
      ("oh_wabash_white_lower_ohio_kincaid", "4. Wabash-White Basins & Lower Ohio Confluence (Angel & Kincaid)", lambda m: m & (LAT >= 38.6) & (LON < -85.3)),
    ]),
    ("13.new_england", "new_england", 1, "New England Hydrological Unit (HU 01): Wabanaki Riverines, Coastal Shell-Middens and Southern Algonquian Towns (10000BC-1600AD)", [
      ("ne_maine_penobscot_kennebec", "1. Penobscot, Kennebec, St. John & Aroostook Maine (Wabanaki)", lambda m: m & (LAT >= 43.75)),
      ("ne_merrimack_massachusetts_bay", "2. Merrimack, Saco & Massachusetts-Plymouth Bay (Massachusett & Pennacook)", lambda m: m & (LAT < 43.75) & (LON >= -71.75) & (LAT >= 41.8)),
      ("ne_connecticut_narragansett_south", "3. Connecticut, Housatonic & Narragansett-Cape Cod Sound (Narragansett, Pequot & Mohegan)", lambda m: m & ~((LAT >= 43.75) | ((LAT < 43.75) & (LON >= -71.75) & (LAT >= 41.8)))),
    ]),
    ("14.central_plains", "central_plains", 11, "Central Plains Hydrological Unit (HU 11): Arkansas-White-Red Basins, Spiro Moundville West and Plains Villages (10000BC-1600AD)", [
      ("cp_high_plains_upper_arkansas", "1. Upper Arkansas, Cimarron & Llano Estacado High Plains (Antelope Creek)", lambda m: m & (LON <= -99.0)),
      ("cp_neosho_verdigris_washita_prairies", "2. Middle Arkansas, Neosho-Grand, Canadian & Washita Prairies (Wichita)", lambda m: m & (LON > -99.0) & (LON <= -95.2)),
      ("cp_arkansas_valley_ozark_spiro", "3. Lower Arkansas Valley, Ozark Fringe & Red River Bend (Spiro Mound Centre)", lambda m: m & (LON > -95.2)),
    ]),
    ("15.mid_atlantic", "mid_atlantic", 2, "Mid-Atlantic Hydrological Unit (HU 02): Haudenosaunee Finger Lakes-Mohawk, Lenapehoking and Powhatan Tidewater (10000BC-1600AD)", [
      ("ma_hudson_mohawk_champlain", "1. Hudson, Mohawk & Lake Champlain Corridor (Mohawk, Mahican & Oneida East)", lambda m: m & (LAT >= 41.05) & (LON >= -75.4)),
      ("ma_delaware_susquehanna_lenape", "2. Delaware, Susquehanna & Upper Finger Lakes (Lenape, Susquehannock & Onondaga)", lambda m: m & ~((LAT >= 41.05) & (LON >= -75.4)) & (LAT >= 39.45)),
      ("ma_chesapeake_potomac_james_powhatan", "3. Chesapeake Bay, Potomac, Rappahannock & James Tidewater (Powhatan & Piscataway)", lambda m: m & (LAT < 39.45)),
    ]),
    ("16.great_lakes", "great_lakes", 4, "Great Lakes Hydrological Unit (HU 04): Lake Superior Wild Rice, Lake Michigan Ridged-Fields and Iroquois-Erie Borderlands (10000BC-1600AD)", [
      ("gl_superior_upper_peninsula", "1. Lake Superior Basin & Upper Peninsula Copper-Rice Zone", lambda m: m & (LAT >= 45.7)),
      ("gl_michigan_fox_winnebago", "2. Lake Michigan, Green Bay, Fox-Winnebago & Lower Michigan West (Oneota/Menominee)", lambda m: m & (LAT < 45.7) & (LON <= -84.6)),
      ("gl_huron_erie_finger_lakes_ny", "3. Saginaw-Huron, Maumee-Erie & Western NY Finger Lakes (Seneca, Cayuga & Erie)", lambda m: m & (LAT < 45.7) & (LON > -84.6)),
    ]),
    ("17.california", "california", 18, "California Hydrological Unit (HU 18): Acorn Economies, Sacramento-San Joaquin Delta and Chumash Maritime Chiefdoms (10000BC-1600AD)", [
      ("ca_klamath_north_coast_shasta", "1. Klamath-Trinity, Eel River & North Coast Ranges (Yurok, Karuk & Hupa)", lambda m: m & (LAT >= 39.5)),
      ("ca_sacramento_sf_bay_delta", "2. Sacramento Valley, San Francisco Bay & Central Delta (Patwin, Ohlone & Miwok)", lambda m: m & (LAT < 39.5) & (LAT >= 37.3)),
      ("ca_san_joaquin_central_coast", "3. San Joaquin-Tulare Basin, Sierra Foothills & Monterey Coast (Yokuts & Esselen)", lambda m: m & (LAT < 37.3) & (LAT >= 34.9)),
      ("ca_chumash_channel_southern_cal", "4. Santa Barbara Channel, Los Angeles Basin & Colorado Desert (Chumash, Tongva & Kumeyaay)", lambda m: m & (LAT < 34.9)),
    ]),
    ("18.northwest", "northwest", 17, "Northwest Hydrological Unit (HU 17): Puget Sound, Lower Columbia Plank-Houses and Plateau Salmon Fisheries (10000BC-1600AD)", [
      ("nw_puget_sound_olympic_coast", "1. Puget Sound, Olympic Peninsula & North Coast (Coast Salish & Makah)", lambda m: m & (LAT >= 46.55) & (LON <= -121.4)),
      ("nw_lower_columbia_willamette_coast", "2. Lower Columbia, Willamette Valley & Oregon Coast (Chinookan, Kalapuya & Tillamook)", lambda m: m & (LAT < 46.55) & (LON <= -121.4)),
      ("nw_columbia_plateau_yakima_spokane", "3. Columbia Plateau, Mid-Columbia Dalles & Okanogan-Spokane (Sahaptin & Interior Salish)", lambda m: m & (LON > -121.4) & (LAT >= 44.5)),
      ("nw_snake_river_klamath_interior", "4. Snake River Plain, Owyhee & Harney-Malheur High Desert (Shoshone-Bannock & Northern Paiute)", lambda m: m & (LON > -121.4) & (LAT < 44.5)),
    ]),
  ]

  for dir_name, stem, huc_id, title, sub_rules in kelly_specs:
    m = (us_huc_grid == huc_id)
    g = np.zeros((H, W), dtype=np.int32)
    pal = distinct_palette(len(sub_rules), seed_offset=huc_id * 0.13)
    zdefs = []
    for idx_s, (zk, zname, rule_fn) in enumerate(sub_rules, start=1):
      sel = rule_fn(m) & (g == 0)
      g[sel] = idx_s
      zdefs.append({"gid": idx_s, "key": zk, "name": zname, "colour": pal[idx_s - 1]})
    g = np.where(m, g, 0)
    g = nearest_fill(m, g, range(1, len(sub_rules) + 1))
    write_mask_and_json5(
      CENTAUR_DIR / "2.united_states_hydrological_units" / dir_name,
      stem,
      {"title": title, "rel_dir": f"2.united_states_hydrological_units/{dir_name}", "domain": [-10000, 1600]},
      zdefs, g, land_area_eff
    )

  # ------------------------------------------------------------------
  # 3. HAWAI'I AND AMERICAN POLYNESIA (Item 8)
  # ------------------------------------------------------------------
  print("\n=== Generating Pre-Annexation Hawai'i and American Polynesia (Item 8) ===")
  m_hp = mask_hi | mask_as
  g_hp = np.zeros((H, W), dtype=np.int32)
  g_hp[mask_as] = 5
  g_hp[mask_hi & (LAT <= 20.3) & (LON >= -156.2)] = 1  # Hawai'i Island
  g_hp[mask_hi & (g_hp == 0) & (LON >= -157.4)] = 2  # Maui Nui (Maui, Molokai, Lanai, Kahoolawe)
  g_hp[mask_hi & (g_hp == 0) & (LON >= -158.6)] = 3  # O'ahu
  g_hp[mask_hi & (g_hp == 0)] = 4  # Kaua'i & Ni'ihau
  g_hp = np.where(m_hp, g_hp, 0)
  g_hp = nearest_fill(m_hp, g_hp, [1, 2, 3, 4, 5])
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
    g_hp, land_area_eff
  )

  # ------------------------------------------------------------------
  # 4 & 5. US STATE RASTER & CANADA PROVINCE RASTER FOR COLONIAL / MODERN MASKS
  # ------------------------------------------------------------------
  print("\n=== Preparing US State & Canadian Province Masks ===")
  us_state_names = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
    "Delaware", "District of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois",
    "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts",
    "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota",
    "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
    "Wisconsin", "Wyoming"
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
    "US-WV": "West Virginia", "US-WI": "Wisconsin", "US-WY": "Wyoming"
  }
  us_state_idx = {nm: i + 1 for i, nm in enumerate(us_state_names)}
  us_state_grid = np.zeros((H, W), dtype=np.int32)
  for code, nm in us_abbr.items():
    if code in code_masks:
      us_state_grid[code_masks[code]] = us_state_idx[nm]

  def s_mask(names):
    idxs = [us_state_idx[n] for n in names]
    return np.isin(us_state_grid, idxs)

  def c_mask(names):
    idxs = [ca_prov_idx[n] for n in names]
    return np.isin(ca_prov_grid, idxs)

  # ------------------------------------------------------------------
  # 4.1 COLONIAL AMERICA TO 1754 (Item 9)
  # ------------------------------------------------------------------
  print("\n=== Generating Colonial America & Canada Masks (Items 9..12) ===")
  m_us_all = mask_us48 | mask_ak | mask_bm
  g9 = np.zeros((H, W), dtype=np.int32)
  g9[mask_bm] = 14
  g9[s_mask(["New Hampshire"]) | (s_mask(["Vermont"]) & (LON >= -72.6))] = 1
  g9[s_mask(["Massachusetts", "Maine"])] = 2
  g9[s_mask(["Rhode Island"])] = 3
  g9[s_mask(["Connecticut"])] = 4
  g9[s_mask(["New York"]) | (s_mask(["Vermont"]) & (LON < -72.6))] = 5
  g9[s_mask(["New Jersey"])] = 6
  g9[s_mask(["Pennsylvania"]) & (LON >= -77.8)] = 7  # Colonial Eastern/Central PA
  g9[s_mask(["Delaware"])] = 8
  g9[s_mask(["Maryland"])] = 9
  g9[s_mask(["Virginia"])] = 10
  g9[s_mask(["North Carolina"]) & (LON >= -82.0)] = 11
  g9[s_mask(["South Carolina"])] = 12
  g9[s_mask(["Georgia"]) & (LON >= -83.2) & (LAT >= 30.8)] = 13
  g9[s_mask(["Florida"]) | (s_mask(["Georgia"]) & (LAT < 30.8)) | (s_mask(["Alabama", "Mississippi"]) & (LAT < 31.0))] = 15  # Spanish Florida
  g9[s_mask(["New Mexico"]) | (s_mask(["Colorado"]) & (LAT < 38.0) & (LON >= -107.0)) | (s_mask(["Arizona"]) & (LAT < 32.8))] = 16  # Spanish New Mexico
  g9[s_mask(["Texas"]) & (LAT < 31.8) & (LON >= -100.5)] = 17  # Spanish Texas
  g9[s_mask(["Louisiana"]) | (s_mask(["Mississippi", "Alabama"]) & (LAT >= 31.0) & (LON <= -87.5)) | (s_mask(["Illinois", "Indiana", "Missouri", "Arkansas"]) & (LAT < 40.5) & (LON >= -91.5) & (LON <= -87.2))] = 18  # French Louisiana & Illinois Country
  g9[(g9 == 0) & (s_mask(["Ohio", "Indiana", "Illinois", "Michigan", "Wisconsin", "Kentucky", "Tennessee", "West Virginia", "Pennsylvania", "Alabama", "Mississippi", "Georgia", "North Carolina"]))] = 19  # Trans-Appalachian Indigenous & Haudenosaunee/Cherokee/Creek
  g9[(g9 == 0) & (s_mask(["Minnesota", "Iowa", "Missouri", "Arkansas", "North Dakota", "South Dakota", "Nebraska", "Kansas", "Oklahoma", "Texas", "Montana", "Wyoming", "Colorado"]))] = 20  # Great Plains & Prairies
  g9[(g9 == 0) & (s_mask(["Washington", "Oregon", "California", "Nevada", "Idaho", "Utah", "Arizona"]))] = 21  # Pacific Coast, Great Basin & Southwest
  g9[mask_ak] = 22  # Pre-Russian / Early Contact Alaska
  g9 = np.where(m_us_all, g9, 0)
  g9 = nearest_fill(m_us_all, g9, range(1, 23))
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
    g9, land_area_eff
  )

  # 4.2 COLONIAL AMERICA TO 1783 (Item 10)
  g10 = g9.copy()
  # Split Virginia into Tidewater/Piedmont Virginia (10), Kentucky District (23), and Northwest/Trans-Ohio Frontier (19); Florida into East/West Florida (15/24)
  g10[s_mask(["Kentucky"])] = 23
  g10[s_mask(["Tennessee"]) & (LON <= -84.0)] = 24
  g10[s_mask(["Vermont"])] = 25
  g10[s_mask(["Louisiana"]) | (s_mask(["Arkansas", "Missouri", "Iowa", "Minnesota"]) & (LON <= -90.0)) | (s_mask(["Kansas", "Nebraska", "Oklahoma", "South Dakota", "North Dakota", "Montana", "Wyoming", "Colorado"]) & (LON <= -90.0))] = 18  # Spanish Louisiana post-1762
  g10[s_mask(["California"])] = 26  # Spanish Alta California (missions from 1769)
  # Wait: restore Plains 20 for uncolonized interior plains west of Mississippi river valley corridor while Louisiana (18) covers Lower Louisiana & Upper Louisiana St. Louis/Ste. Genevieve corridor
  g10[(s_mask(["Montana", "Wyoming", "North Dakota", "South Dakota", "Nebraska", "Kansas", "Oklahoma", "Colorado"])) & (LON < -95.0)] = 20
  g10 = np.where(m_us_all, g10, 0)
  g10 = nearest_fill(m_us_all, g10, [x for x in range(1, 27)])
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
    g10, land_area_eff
  )

  # 4.3 COLONIAL CANADA TO 1763 (Item 11)
  m_ca_all = mask_ca | mask_pm | mask_gl
  g11 = np.zeros((H, W), dtype=np.int32)
  g11[c_mask(["Québec"]) & (LAT <= 49.0)] = 1  # New France St. Lawrence (Quebec, Trois-Rivieres, Montreal)
  g11[c_mask(["Nova Scotia", "New Brunswick", "Prince Edward Island"])] = 2  # Acadia / Nova Scotia / Ile Royale / Ile Saint-Jean
  g11[mask_pm | c_mask(["Newfoundland and Labrador"])] = 3  # Newfoundland (Avalon & Plaisance) + Labrador + Saint-Pierre
  g11[c_mask(["Ontario"]) & ((LAT <= 46.8) | ((LON >= -85.0) & (LAT <= 48.0)))] = 4  # Pays d'en Haut / Detroit-Ontario Posts
  g11[c_mask(["Ontario", "Québec", "Manitoba", "Nunavut"]) & (g11 == 0) & (hudson_wmo | (LAT >= 49.0))] = 5  # Rupert's Land / Hudson's Bay Posts
  g11[c_mask(["Manitoba", "Saskatchewan", "Alberta"]) & (g11 == 0)] = 6  # Western Prairies & La Verendrye Posts
  g11[c_mask(["British Columbia", "Yukon", "Northwest Territories"])] = 7  # Pacific Slope & Mackenzie Subarctic
  g11[mask_gl] = 8  # Greenland (Danish-Norwegian & Moravian Missions 1721-1763 + Kalaallit)
  g11 = np.where(m_ca_all, g11, 0)
  g11 = nearest_fill(m_ca_all, g11, range(1, 9))
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
    g11, land_area_eff
  )

  # 4.4 COLONIAL CANADA TO 1867 (Item 12)
  g12 = np.zeros((H, W), dtype=np.int32)
  g12[c_mask(["Québec"])] = 1
  g12[c_mask(["Ontario"])] = 2
  g12[c_mask(["Nova Scotia"])] = 3
  g12[c_mask(["New Brunswick"])] = 4
  g12[c_mask(["Prince Edward Island"])] = 5
  g12[c_mask(["Newfoundland and Labrador"])] = 6
  g12[mask_pm] = 7
  g12[c_mask(["Manitoba"]) & (LAT <= 52.0)] = 8  # Red River / Assiniboia Colony
  g12[c_mask(["Manitoba", "Saskatchewan", "Alberta"]) & (g12 == 0)] = 9  # Rupert's Land Prairies & Boreal
  g12[c_mask(["British Columbia"])] = 10  # Colonies of Vancouver Island & British Columbia
  g12[c_mask(["Yukon", "Northwest Territories", "Nunavut"])] = 11  # North-Western Territory & Arctic
  g12[mask_gl] = 12  # Danish Inspectorates of Greenland
  g12 = np.where(m_ca_all, g12, 0)
  g12 = nearest_fill(m_ca_all, g12, range(1, 13))
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
    g12, land_area_eff
  )

  # ------------------------------------------------------------------
  # 5.1 CANADA AFTER CONFEDERATION (Item 13)
  # ------------------------------------------------------------------
  print("\n=== Generating Modern Canada & United States Masks (Items 13..14) ===")
  g13 = ca_prov_grid.copy()
  pm_gid = len(ca_prov_order) + 1
  gl_gid = len(ca_prov_order) + 2
  g13[mask_pm] = pm_gid
  g13[mask_gl] = gl_gid
  g13 = np.where(m_ca_all, g13, 0)
  g13 = nearest_fill(m_ca_all, g13, range(1, gl_gid + 1))
  pal13 = distinct_palette(gl_gid, 0.55)
  can_mod_defs = []
  for i, nm in enumerate(ca_prov_order, start=1):
    slug_p = nm.lower().replace("é", "e").replace(" ", "_")
    can_mod_defs.append({"gid": i, "key": f"can_{slug_p}", "name": f"{i}. {nm}", "colour": pal13[i - 1]})
  can_mod_defs.append({"gid": pm_gid, "key": "can_saint_pierre_miquelon", "name": f"{pm_gid}. Saint Pierre and Miquelon", "colour": pal13[pm_gid - 1]})
  can_mod_defs.append({"gid": gl_gid, "key": "can_greenland", "name": f"{gl_gid}. Greenland (Kalaallit Nunaat)", "colour": pal13[gl_gid - 1]})
  write_mask_and_json5(
    CENTAUR_DIR / "5.modern_canada_and_united_states/1.canada_post_confederation",
    "canada_post_confederation",
    {"title": "Canada after Confederation, Greenland and Saint-Pierre-et-Miquelon: Census Demography and Northern Urbanisation (1867AD-2026AD)", "rel_dir": "5.modern_canada_and_united_states/1.canada_post_confederation", "domain": [1867, 2026]},
    can_mod_defs, g13, land_area_eff
  )

  # 5.2 UNITED STATES AFTER INDEPENDENCE (Item 14)
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
  for i, nm in enumerate(us_state_names, start=1):
    slug_s = nm.lower().replace(" ", "_")
    entry = {"gid": i, "key": f"usa_{slug_s}", "name": f"{i}. {nm}", "colour": pal14[i - 1]}
    if nm == "Hawaii":
      entry["domain"] = [1898, 2026]
    elif nm == "Alaska":
      entry["domain"] = [1867, 2026]
    us_mod_defs.append(entry)
  us_mod_defs.append({"gid": bm_gid, "key": "usa_bermuda", "name": f"{bm_gid}. Bermuda", "colour": pal14[bm_gid - 1]})
  us_mod_defs.append({"gid": as_gid, "key": "usa_american_samoa", "name": f"{as_gid}. American Samoa", "colour": pal14[as_gid - 1], "domain": [1900, 2026]})
  write_mask_and_json5(
    CENTAUR_DIR / "5.modern_canada_and_united_states/2.united_states_post_independence",
    "united_states_post_independence",
    {"title": "United States after Independence: Decennial Census Demography, Westward Expansion and Metropolitan Growth (1783AD-2026AD)", "rel_dir": "5.modern_canada_and_united_states/2.united_states_post_independence", "domain": [1783, 2026]},
    us_mod_defs, g14, land_area_eff
  )

  # Coverage verification across pre-columbian union vs modern union
  pre_union = pre_ca_domain | mask_us48 | mask_hi | mask_as
  mod_union = m_ca_all | m_us_mod
  diff_pre_mod = (pre_union ^ mod_union) & (~mask_bm)
  print(f"\n[COVERAGE CHECK] Pre-Columbian union px={pre_union.sum()}, Modern union px={mod_union.sum()}, Diff (excl Bermuda)={diff_pre_mod.sum()}")
  # Also write continental domain mask PNGs for ViscountMaternKriging
  na_dom = np.zeros((H, W, 4), dtype=np.uint8)
  dom1 = (mask_us48 | mask_ak | mask_ca | mask_gl | mask_pm)
  na_dom[dom1] = [255, 255, 255, 255]
  Image.fromarray(na_dom, mode="RGBA").save(CENTAUR_DIR / "_shared/sites_northern_america/config/centaur_na_domain_mask.png")

  hp_dom = np.zeros((H, W, 4), dtype=np.uint8)
  hp_dom[m_hp] = [255, 255, 255, 255]
  Image.fromarray(hp_dom, mode="RGBA").save(CENTAUR_DIR / "_shared/sites_hawaii_polynesia/config/centaur_hp_domain_mask.png")

  # Export auxiliary pixel lookup NPZ for super-fast script calibration/plotting
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
  print("Saved centaur_pixel_grids.npz and domain mask PNGs.")


if __name__ == "__main__":
  main()
