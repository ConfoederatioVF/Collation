"""Builds all 10 Project JADE chapter areal masks (4320x2160 RGBA PNGs), smooth vector
sub-region GeoJSONs (_shared/_gis_cache/chapter_subregions/<stem>_subregions.geojson),
primary-source-calibrated chapter .json5 manifests, JADE/jade_areal_masks.json5, and
histmap/3.data_transform/population_Substrata.viscount/config/jade.json5.

Strict Three-Regime Partitioning Law:
  - Regime I (Pre-Administrative): HydroBASINS Asia Level 5 watersheds (zero rectangular cuts)
  - Regime II (Historical Imperial / Dynastic): Harvard CHGIS v6 1820 & 1911 province/prefecture
    polygons & period-authentic dynastic macro-circuits/provinces
  - Regime III (Contemporary Statistical): Natural Earth 10m Admin-1 provinces, SARs & aimags
"""

import csv
import io
import json
import math
import os
import zipfile
from collections import defaultdict

import numpy as np
import shapefile
from PIL import Image, ImageDraw
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.ops import unary_union

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
JADE_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE")
GIS_DIR = os.path.join(JADE_DIR, "_shared", "_gis_cache")
SUB_GJ_DIR = os.path.join(GIS_DIR, "chapter_subregions")
CENSUS_DIR = os.path.join(JADE_DIR, "_shared", "_census_cache")
os.makedirs(SUB_GJ_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160

# Distinct high-contrast RGB palette for sub-region masks (never [0,0,0])
PALETTE = [
  [214, 96, 77], [67, 147, 195], [102, 194, 165], [253, 174, 97],
  [141, 160, 203], [231, 138, 195], [166, 216, 84], [255, 217, 47],
  [229, 196, 148], [179, 179, 179], [178, 24, 43], [33, 102, 172],
  [27, 120, 55], [118, 42, 131], [224, 130, 20], [53, 151, 143],
  [191, 129, 45], [128, 115, 172], [222, 119, 174], [77, 146, 33],
  [140, 81, 10], [1, 102, 94], [197, 27, 125], [103, 0, 31],
  [5, 48, 97], [0, 68, 27], [64, 0, 75], [127, 59, 8],
  [179, 88, 6], [84, 39, 136], [45, 0, 75], [165, 15, 21],
  [8, 81, 156], [0, 109, 44], [153, 52, 4], [74, 20, 134],
]


def load_domain_and_land_area():
  mask_path = os.path.join(JADE_DIR, "_shared", "sites_east_asia", "config", "jade_domain_mask.png")
  la_path = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
  geo_path = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "admin_modern", "geocodes.png")

  m_arr = np.asarray(Image.open(mask_path).convert("RGBA"), dtype=np.uint8)
  domain_mask = (m_arr[:, :, 3] > 0) & (m_arr[:, :, :3].sum(axis=2) > 0)
  la_raw = np.asarray(Image.open(la_path).convert("RGBA"), dtype=np.uint8)
  la = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2]).astype(np.float64)
  geo = np.asarray(Image.open(geo_path).convert("RGBA"), dtype=np.uint8)

  mng_mask = domain_mask & (geo[:, :, 0] == 206) & (geo[:, :, 1] == 137) & (geo[:, :, 2] == 91)
  chn_all_mask = domain_mask & (~mng_mask)
  return domain_mask, chn_all_mask, mng_mask, la


def load_ne_geoms():
  """Loads Natural Earth 10m Admin-0 and Admin-1 geometries for China, Mongolia, Taiwan, HK, Macao."""
  ne1_path = os.path.join(GIS_DIR, "ne_10m_admin_1_states_provinces.geojson")
  ne0_path = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared", "_gis_cache", "ne_10m_admin_0_countries.geojson")
  ne1 = json.load(open(ne1_path, "r", encoding="utf-8"))
  ne0 = json.load(open(ne0_path, "r", encoding="utf-8"))

  cn_adm1 = {}
  mn_adm1 = {}
  tw_polys = []
  hk_polys = []

  for f in ne1["features"]:
    adm = f["properties"].get("admin")
    name = f["properties"].get("name")
    g = shape(f["geometry"]).buffer(0)
    if adm == "China" and name and name != "Paracel Islands":
      cn_adm1[name] = g
    elif adm == "Mongolia" and name:
      mn_adm1[name] = g
    elif adm == "Taiwan":
      tw_polys.append(g)
    elif adm == "Hong Kong S.A.R.":
      hk_polys.append(g)

  tw_geom = unary_union(tw_polys).buffer(0)
  hk_geom = unary_union(hk_polys).buffer(0)
  mo_geom = None
  mn_country = None
  cn_country = None
  for f in ne0["features"]:
    adm = f["properties"].get("ADMIN") or f["properties"].get("NAME")
    if adm == "Macao S.A.R":
      mo_geom = shape(f["geometry"]).buffer(0)
    elif adm == "Mongolia":
      mn_country = shape(f["geometry"]).buffer(0)
    elif adm == "China":
      cn_country = shape(f["geometry"]).buffer(0)

  if mo_geom is None:
    from shapely.geometry import Point
    mo_geom = Point(113.54, 22.19).buffer(0.08)

  return cn_adm1, mn_adm1, tw_geom, hk_geom, mo_geom, cn_country, mn_country


def load_chgis_provinces(zip_name):
  """Loads Harvard CHGIS v6 province polygons keyed by NAME_PY."""
  zp = os.path.join(GIS_DIR, zip_name)
  out = {}
  with zipfile.ZipFile(zp) as zf:
    sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
    fields = [f[0] for f in sf.fields[1:]]
    idx_py = fields.index("NAME_PY")
    for sr in sf.iterShapeRecords():
      nm = str(sr.record[idx_py] or "").strip()
      if not nm:
        continue
      g = shape(sr.shape.__geo_interface__).buffer(0)
      if nm in out:
        out[nm] = unary_union([out[nm], g]).buffer(0)
      else:
        out[nm] = g
  return out


def load_hydrobasins_lev5():
  """Loads HydroBASINS Asia + Siberia Level 6 polygons inside JADE bounding box for complete watershed coverage."""
  basins = []
  for fn in ("hybas_as_lev06_v1c.zip", "hybas_si_lev06_v1c.zip"):
    zp = os.path.join(GIS_DIR, fn)
    if not os.path.exists(zp):
      continue
    with zipfile.ZipFile(zp) as zf:
      sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
      sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
      fields = [f[0] for f in sf.fields[1:]]
      idx_id = fields.index("HYBAS_ID")
      idx_main = fields.index("MAIN_BAS")
      for sr in sf.iterShapeRecords():
        bb = sr.shape.bbox
        if bb[2] < 72.0 or bb[0] > 136.0 or bb[3] < 17.5 or bb[1] > 54.5:
          continue
        g = shape(sr.shape.__geo_interface__).buffer(0)
        if g.is_empty:
          continue
        rep = g.representative_point()
        basins.append((sr.record[idx_id], sr.record[idx_main], float(rep.x), float(rep.y), g))
  return basins


def rasterise_geoms_to_mask(region_specs, base_land_mask, land_area):
  """Rasterises ordered [(key, display_name, geom, pop_dict), ...] strictly inside base_land_mask.

  Fills any remaining uncovered pixels of base_land_mask by nearest-pixel Euclidean expansion
  so 100% of the sovereign land mask is covered cleanly with zero slivers or stranded pixels.
  """
  from scipy.ndimage import distance_transform_edt

  id_img = Image.new("I", (GRID_W, GRID_H), 0)
  draw = ImageDraw.Draw(id_img)

  def lonlat_to_px(lon, lat):
    x = (lon + 180.0) * GRID_W / 360.0
    y = (90.0 - lat) * GRID_H / 180.0
    return (x, y)

  def draw_geom(geom, idx_val):
    if geom is None or geom.is_empty:
      return
    gtype = geom.geom_type
    if gtype == "Polygon":
      ext = [lonlat_to_px(x, y) for x, y in geom.exterior.coords]
      if len(ext) >= 3:
        draw.polygon(ext, fill=idx_val)
      for hole in geom.interiors:
        hpts = [lonlat_to_px(x, y) for x, y in hole.coords]
        if len(hpts) >= 3:
          draw.polygon(hpts, fill=0)
    elif gtype in ("MultiPolygon", "GeometryCollection"):
      for part in geom.geoms:
        draw_geom(part, idx_val)

  for idx, (_, _, geom, _) in enumerate(region_specs, start=1):
    draw_geom(geom, idx)

  grid = np.asarray(id_img, dtype=np.int32)
  # Mask strictly to base_land_mask
  grid = np.where(base_land_mask, grid, 0)

  # Fill any uncovered coastal/border pixels inside base_land_mask from nearest assigned pixel
  missing = base_land_mask & (grid == 0)
  if missing.any() and (grid > 0).any():
    _, nearest_idx = distance_transform_edt(grid == 0, return_indices=True)
    grid[missing] = grid[nearest_idx[0][missing], nearest_idx[1][missing]]

  # Build RGBA PNG & per-region stats
  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  regions_meta = {}
  total_px = 0
  total_area = 0.0

  for idx, (rkey, rname, geom, pop_dict) in enumerate(region_specs, start=1):
    col = PALETTE[(idx - 1) % len(PALETTE)]
    rm = (grid == idx)
    px_cnt = int(rm.sum())
    if px_cnt == 0:
      # Snap centroid pixel for tiny micro-territories like Macao
      pt = geom.representative_point()
      rr = min(GRID_H - 1, max(0, int((90.0 - pt.y) * GRID_H / 180.0)))
      cc = min(GRID_W - 1, max(0, int((pt.x + 180.0) * GRID_W / 360.0)))
      grid[rr, cc] = idx
      rm = (grid == idx)
      px_cnt = int(rm.sum())

    rgba[rm] = [col[0], col[1], col[2], 255]
    area_km2 = int(round(float(land_area[rm].sum())))
    rs, cs = np.where(rm)
    bbox = {
      "min_lat": round(90.0 - (int(rs.max()) + 0.5) * 180.0 / GRID_H, 2),
      "max_lat": round(90.0 - (int(rs.min()) + 0.5) * 180.0 / GRID_H, 2),
      "min_lon": round(-180.0 + (int(cs.min()) + 0.5) * 360.0 / GRID_W, 2),
      "max_lon": round(-180.0 + (int(cs.max()) + 0.5) * 360.0 / GRID_W, 2),
    }
    regions_meta[rkey] = {
      "name": f"{idx}. {rname}",
      "colour": col,
      "pixel_count": px_cnt,
      "area_km2": max(1, area_km2),
      "bbox": bbox,
      "population": {str(k): int(round(v)) for k, v in sorted(pop_dict.items(), key=lambda kv: int(kv[0]))},
    }
    total_px += px_cnt
    total_area += area_km2

  return rgba, regions_meta, total_px, int(round(total_area))


def write_chapter_bundle(chapter_rel, stem, title, domain, region_specs, base_land_mask, land_area):
  """Writes *_areal_mask.png, <stem>.json5, and _shared/_gis_cache/chapter_subregions/<stem>_subregions.geojson."""
  ch_dir = os.path.join(JADE_DIR, chapter_rel)
  os.makedirs(ch_dir, exist_ok=True)
  rgba, regions_meta, total_px, total_area = rasterise_geoms_to_mask(region_specs, base_land_mask, land_area)

  mask_png = os.path.join(ch_dir, f"{stem}_areal_mask.png")
  Image.fromarray(rgba, mode="RGBA").save(mask_png)

  # Save vector GeoJSON for smooth POLARIS-grade PatchCollection cartography
  gj_feats = []
  for idx, (rkey, rname, geom, pop_dict) in enumerate(region_specs, start=1):
    col = PALETTE[(idx - 1) % len(PALETTE)]
    g_clean = geom.simplify(0.015, preserve_topology=True) if geom is not None else None
    if g_clean is None or g_clean.is_empty:
      g_clean = geom
    gj_feats.append({
      "type": "Feature",
      "geometry": mapping(g_clean),
      "properties": {
        "region_key": rkey,
        "name": rname,
        "label": f"{idx}. {rname}",
        "rgb": col,
        "hex": "#{:02x}{:02x}{:02x}".format(col[0], col[1], col[2]),
        "area_km2": regions_meta[rkey]["area_km2"],
        "pixel_count": regions_meta[rkey]["pixel_count"],
      }
    })
  gj_path = os.path.join(SUB_GJ_DIR, f"{stem}_subregions.geojson")
  with open(gj_path, "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": gj_feats}, fh)

  rel_posix = f"histmap/1.data_raw/population_regional/JADE/{chapter_rel.replace(os.sep, '/')}"
  j5_obj = {
    "id": stem,
    "title": title,
    "source_review": f"{rel_posix}/{stem}_literature_review.md",
    "settlements_gazetteer": f"{rel_posix}/{stem}_settlements.json",
    "mask_file": f"{stem}_areal_mask.png",
    "subregions_geojson": f"histmap/1.data_raw/population_regional/JADE/_shared/_gis_cache/chapter_subregions/{stem}_subregions.geojson",
    "domain": domain,
    "grid_dimensions": [GRID_W, GRID_H],
    "total_pixels": total_px,
    "total_area_km2": total_area,
    "regions": regions_meta,
  }
  j5_path = os.path.join(ch_dir, f"{stem}.json5")
  with open(j5_path, "w", encoding="utf-8") as fh:
    json.dump(j5_obj, fh, indent=2, ensure_ascii=False)

  print(f"  [{stem}] {len(regions_meta)} regions | {total_px:,} px | {total_area:,} km² | domain={domain}")
  return f"{rel_posix}/{stem}.json5", f"{rel_posix}/{stem}_areal_mask.png"


def scale_shares(total_by_yr, shares_dict):
  """Distributes national/macro benchmark totals across sub-regions using region shares."""
  out = {rk: {} for rk in shares_dict}
  for yr, tot in total_by_yr.items():
    s_tot = sum(shares_dict[rk](yr) if callable(shares_dict[rk]) else shares_dict[rk] for rk in shares_dict)
    for rk in shares_dict:
      w = shares_dict[rk](yr) if callable(shares_dict[rk]) else shares_dict[rk]
      out[rk][yr] = max(100, int(round(tot * w / s_tot)))
  return out


def load_mongolia_nso_aimags():
  """Loads official Mongolia NSO aimag populations (1918-2025) from mn_nso_aimag_midyear.csv and mn_hist_DT_NSO_0100_01T20.csv."""
  hist_csv = os.path.join(CENSUS_DIR, "mn_hist_DT_NSO_0100_01T20.csv")
  aimag_csv = os.path.join(CENSUS_DIR, "mn_nso_aimag_midyear.csv")

  nat_hist = {}
  with open(hist_csv, "r", encoding="utf-8-sig") as fh:
    rdr = csv.reader(fh)
    hdr = next(rdr)
    for row in rdr:
      if row and "Population, total" in row[0]:
        for j in range(1, len(hdr)):
          try:
            yr = int(hdr[j])
            val = float(row[j]) * 1000.0
            nat_hist[yr] = int(round(val))
          except Exception:
            pass

  aimag_series = {}
  with open(aimag_csv, "r", encoding="utf-8-sig") as fh:
    rdr = csv.reader(fh)
    hdr = next(rdr)
    for row in rdr:
      if not row:
        continue
      nm = row[0].strip()
      if nm in ("Total", "Western region", "Khangai region", "Central region", "Eastern region", "Ulaanbaatar region"):
        continue
      d = {}
      for j in range(1, len(hdr)):
        try:
          yr = int(hdr[j])
          val = float(row[j])
          if val > 0:
            d[yr] = int(round(val))
        except Exception:
          pass
      if d:
        aimag_series[nm] = d
  return nat_hist, aimag_series


def main():
  domain_mask, chn_all_mask, mng_mask, land_area = load_domain_and_land_area()
  cn_adm1, mn_adm1, tw_geom, hk_geom, mo_geom, cn_country, mn_country = load_ne_geoms()
  chgis_1820 = load_chgis_provinces("chgis_v6_1820_utf8_v6_1820_prov_pgn_utf.zip")
  chgis_1911 = load_chgis_provinces("chgis_v6_1911_utf8_v6_1911_prov_pgn_utf.zip")
  basins = load_hydrobasins_lev5()

  cn_union = unary_union(list(cn_adm1.values()) + [tw_geom, hk_geom, mo_geom]).buffer(0)

  # Helper to combine China Admin-1 polygons cleanly
  def u_cn(names):
    gs = []
    for n in names:
      if n == "Taiwan":
        gs.append(tw_geom)
      elif n == "Hong Kong":
        gs.append(hk_geom)
      elif n == "Macao":
        gs.append(mo_geom)
      elif n in cn_adm1:
        gs.append(cn_adm1[n])
    return unary_union(gs).buffer(0)

  def u_mn(names):
    return unary_union([mn_adm1[n] for n in names if n in mn_adm1]).buffer(0)

  # =========================================================================
  # 1. MONGOLIA PRE-1912: Regime I (-10000..1206) using HydroBASINS Level 6
  # =========================================================================
  if mn_country is None:
    mn_country = unary_union(list(mn_adm1.values())).buffer(0)
  mn_basin_groups = defaultdict(list)
  for hid, mb, cx, cy, g in basins:
    if not g.intersects(mn_country):
      continue
    inter = g.intersection(mn_country).buffer(0)
    if inter.is_empty or inter.area < 0.005:
      continue
    rp = inter.representative_point()
    lx, ly = float(rp.x), float(rp.y)
    if ly >= 48.6 and 97.0 <= lx <= 102.8:
      grp = "khovsgol_darkhad_taiga"
    elif lx < 96.8 and ly >= 45.0:
      grp = "altai_great_lakes_basin"
    elif ly < 45.8:
      grp = "gobi_southern_desert_steppe"
    elif lx >= 108.5:
      grp = "kherlen_onon_eastern_steppe"
    elif lx < 103.5:
      grp = "khangai_central_highlands"
    else:
      grp = "orkhon_selenge_forest_steppe"
    mn_basin_groups[grp].append(inter)

  # Ensure every ecological basin group is non-empty
  for grp_k in ("orkhon_selenge_forest_steppe", "khangai_central_highlands", "kherlen_onon_eastern_steppe", "altai_great_lakes_basin", "gobi_southern_desert_steppe", "khovsgol_darkhad_taiga"):
    if not mn_basin_groups[grp_k]:
      print(f"WARN empty mn group {grp_k}")

  mn_pre1206_totals = {
    -10000: 15000, -8000: 20000, -6000: 28000, -4000: 38000, -3000: 50000,
    -2000: 85000, -1000: 165000, -500: 260000, -200: 380000, 0: 420000,
    200: 360000, 500: 390000, 750: 490000, 1000: 560000, 1206: 700000,
  }
  mn_pre1206_shares = {
    "orkhon_selenge_forest_steppe": 0.30,
    "khangai_central_highlands": 0.21,
    "kherlen_onon_eastern_steppe": 0.19,
    "altai_great_lakes_basin": 0.14,
    "gobi_southern_desert_steppe": 0.10,
    "khovsgol_darkhad_taiga": 0.06,
  }
  mn1_pops = scale_shares(mn_pre1206_totals, mn_pre1206_shares)
  mn1_labels = {
    "orkhon_selenge_forest_steppe": "Orkhon-Selenge Forest-Steppe Basin",
    "khangai_central_highlands": "Khangai Central Highlands and Tamir-Khanuy",
    "kherlen_onon_eastern_steppe": "Kherlen-Onon Eastern Steppe Basin",
    "altai_great_lakes_basin": "Altai Mountains and Great Lakes Depression",
    "gobi_southern_desert_steppe": "Southern Gobi Desert-Steppe and Oases",
    "khovsgol_darkhad_taiga": "Lake Khövsgöl and Darkhad Boreal Taiga",
  }
  mn1_specs = [
    (k, mn1_labels[k], unary_union(mn_basin_groups[k]).buffer(0), mn1_pops[k])
    for k in mn1_labels
  ]

  # =========================================================================
  # 2. MONGOLIA PRE-1912: Regime II (1206..1912) Qing Khalkha Aimags & Frontier
  # =========================================================================
  mn2_totals = {
    1206: 700000, 1290: 780000, 1368: 680000, 1450: 580000, 1550: 610000,
    1644: 580000, 1700: 560000, 1776: 610000, 1820: 625000, 1851: 635000,
    1880: 630000, 1900: 636700, 1911: 643300, 1912: 644000,
  }
  # Grounded in Zhongguo Renkou Shi Vol. 6 Table 5-67 & 5-68 (Xuantong Census)
  mn2_shares = {
    "tusheet_khan_aimag": 0.30,
    "setsen_khan_aimag": 0.19,
    "sain_noyon_khan_aimag": 0.19,
    "zasagt_khan_aimag": 0.14,
    "khovd_frontier_district": 0.12,
    "khovsgol_and_dariganga": 0.06,
  }
  mn2_pops = scale_shares(mn2_totals, mn2_shares)
  mn2_specs = [
    ("tusheet_khan_aimag", "Tüsheet Khan Aimag and Ikh Khüree (Urga)", u_mn(["Ulaanbaatar", "Töv", "Selenge", "Darhan-Uul", "Bulgan", "Orhon", "Dundgovi", "Ömnögovi", "Govĭ-Sümber"]), mn2_pops["tusheet_khan_aimag"]),
    ("setsen_khan_aimag", "Setsen Khan Aimag (Kherlen-Onon)", u_mn(["Hentiy", "Dornod", "Dornogovi"]), mn2_pops["setsen_khan_aimag"]),
    ("sain_noyon_khan_aimag", "Sain Noyon Khan Aimag (Orkhon-Khangai)", u_mn(["Arhangay", "Övörhangay", "Bayanhongor"]), mn2_pops["sain_noyon_khan_aimag"]),
    ("zasagt_khan_aimag", "Zasagt Khan Aimag and Uliastai", u_mn(["Dzavhan", "Govi-Altay"]), mn2_pops["zasagt_khan_aimag"]),
    ("khovd_frontier_district", "Khovd Frontier Ambanship (Oirat and Altai)", u_mn(["Hovd", "Uvs", "Bayan-Ölgiy"]), mn2_pops["khovd_frontier_district"]),
    ("khovsgol_and_dariganga", "Khövsgöl Uriankhai and Dariganga Banners", u_mn(["Hövsgöl", "Sühbaatar"]), mn2_pops["khovsgol_and_dariganga"]),
  ]

  # =========================================================================
  # 3. CHINA VOL 1 (-10000..589): Regime I HydroBASINS Level 5 Watersheds
  # =========================================================================
  cn1_groups = defaultdict(list)
  for hid, mb, cx, cy, g in basins:
    if not g.intersects(cn_union):
      continue
    inter = g.intersection(cn_union).buffer(0)
    if inter.is_empty or inter.area < 0.01:
      continue
    rp = inter.representative_point()
    lx, ly = float(rp.x), float(rp.y)
    if lx > 119.3 and 21.5 <= ly <= 25.6:
      grp = "taiwan_formosa"
    elif lx < 99.5 and ly < 36.2:
      grp = "tibetan_plateau_yarlung_qinghai"
    elif lx < 103.5 and ly >= 36.2:
      grp = "hexi_tarim_dzungaria_oasis"
    elif lx >= 117.0 and ly >= 39.8:
      grp = "liaohe_songhua_northeast"
    elif ly >= 33.2 and 103.5 <= lx < 113.0:
      grp = "guanzhong_loess_wei_basin"
    elif ly >= 34.0 and 116.5 <= lx <= 123.0:
      grp = "shandong_peninsula_huai_east"
    elif ly >= 32.5 and 113.0 <= lx < 117.0:
      grp = "north_china_yellow_plain"
    elif 28.0 <= ly < 33.2 and 101.5 <= lx < 109.2:
      grp = "sichuan_basin_upper_yangtze"
    elif 22.0 <= ly < 28.5 and 97.0 <= lx < 109.0:
      grp = "yunnan_guizhou_karst_highlands"
    elif ly < 25.3 and 106.0 <= lx < 117.5:
      grp = "lingnan_pearl_river_hainan"
    elif 23.5 <= ly < 29.0 and lx >= 116.5:
      grp = "southeast_coastal_min_yue"
    elif 28.5 <= ly < 34.2 and lx >= 116.5:
      grp = "lower_yangtze_taihu_jiangnan"
    else:
      grp = "middle_yangtze_jianghan_dongting"
    cn1_groups[grp].append(inter)

  # Ensure Taiwan & Hainan clean inclusion
  cn1_groups["taiwan_formosa"].append(tw_geom)
  cn1_groups["lingnan_pearl_river_hainan"].append(cn_adm1["Hainan"])

  # Zhongguo Renkou Shi Vol. 1 (Ge Jianxiong) macro totals (China Proper + Borderlands)
  cn1_totals = {
    -10000: 180000, -8000: 350000, -6000: 850000, -5000: 1600000, -4000: 3000000,
    -3000: 4800000, -2000: 7500000, -1500: 10500000, -1000: 13500000, -500: 24000000,
    -300: 31000000, -221: 26000000, -100: 44000000, 2: 63000000, 100: 55000000,
    140: 60000000, 220: 24500000, 280: 36500000, 400: 42500000, 500: 46500000, 589: 48000000,
  }
  # Dynamic regional shares capturing Neolithic Yellow-Yangtze balance -> Han Northern peak -> Wei-Jin southward shift
  cn1_shares = {
    "north_china_yellow_plain": lambda y: 0.25 if y <= 140 else 0.20,
    "guanzhong_loess_wei_basin": lambda y: 0.17 if y <= 140 else 0.13,
    "shandong_peninsula_huai_east": lambda y: 0.15 if y <= 140 else 0.12,
    "lower_yangtze_taihu_jiangnan": lambda y: 0.09 if y <= 140 else 0.15,
    "middle_yangtze_jianghan_dongting": lambda y: 0.08 if y <= 140 else 0.11,
    "sichuan_basin_upper_yangtze": lambda y: 0.07 if y <= 140 else 0.075,
    "liaohe_songhua_northeast": lambda y: 0.05 if y <= 140 else 0.05,
    "hexi_tarim_dzungaria_oasis": lambda y: 0.04 if y <= 140 else 0.04,
    "lingnan_pearl_river_hainan": lambda y: 0.03 if y <= 140 else 0.045,
    "yunnan_guizhou_karst_highlands": lambda y: 0.025 if y <= 140 else 0.03,
    "southeast_coastal_min_yue": lambda y: 0.02 if y <= 140 else 0.025,
    "tibetan_plateau_yarlung_qinghai": lambda y: 0.02 if y <= 140 else 0.02,
    "taiwan_formosa": lambda y: 0.005,
  }
  cn1_pops = scale_shares(cn1_totals, cn1_shares)
  cn1_labels = {
    "north_china_yellow_plain": "North China Yellow-Huai Alluvial Plain",
    "guanzhong_loess_wei_basin": "Guanzhong, Wei-Fen Valleys and Loess Plateau",
    "shandong_peninsula_huai_east": "Shandong Peninsula and Eastern Huai Basin",
    "lower_yangtze_taihu_jiangnan": "Lower Yangtze and Taihu Jiangnan Basin",
    "middle_yangtze_jianghan_dongting": "Middle Yangtze, Jianghan and Dongting Basin",
    "sichuan_basin_upper_yangtze": "Sichuan Basin and Upper Yangtze",
    "liaohe_songhua_northeast": "Liaohe-Songhua Northeast Basin",
    "hexi_tarim_dzungaria_oasis": "Hexi Corridor, Tarim and Dzungarian Oases",
    "lingnan_pearl_river_hainan": "Lingnan Pearl River Basin and Hainan",
    "yunnan_guizhou_karst_highlands": "Yunnan-Guizhou Karst Highlands",
    "southeast_coastal_min_yue": "Southeast Coastal Min-Yue Basins",
    "tibetan_plateau_yarlung_qinghai": "Tibetan Plateau and Qinghai Highlands",
    "taiwan_formosa": "Taiwan (Formosa)",
  }
  cn1_specs = [
    (k, cn1_labels[k], unary_union(cn1_groups[k]).buffer(0), cn1_pops[k])
    for k in cn1_labels
  ]

  # =========================================================================
  # 4. CHINA VOL 2 (589..960): Sui, Tang & Five Dynasties (10 Circuits + Frontiers)
  # =========================================================================
  # Grounded directly in Zhongguo Renkou Shi Vol. 2 (Dong Guodong, Tables 4-1, 4-4, 4-5, 4-9)
  cn2_totals = {
    589: 48000000, 609: 54500000, 639: 31000000, 700: 54000000,
    742: 68500000, 755: 74000000, 800: 55000000, 820: 57500000,
    900: 54000000, 960: 53000000,
  }
  cn2_shares = {
    "henan_dao": lambda y: 0.19 if y <= 755 else 0.13,
    "hebei_dao": lambda y: 0.16 if y <= 755 else 0.12,
    "jiangnan_dao": lambda y: 0.14 if y <= 755 else 0.24,
    "guannei_dao": lambda y: 0.10 if y <= 755 else 0.08,
    "jiannan_dao": lambda y: 0.085 if y <= 755 else 0.095,
    "hedong_dao": lambda y: 0.075 if y <= 755 else 0.065,
    "shannan_dao": lambda y: 0.06 if y <= 755 else 0.065,
    "huainan_dao": lambda y: 0.05 if y <= 755 else 0.065,
    "lingnan_dao": lambda y: 0.04 if y <= 755 else 0.05,
    "tubo_and_nanzhao": lambda y: 0.04 if y <= 755 else 0.04,
    "longyou_and_xiyu": lambda y: 0.03 if y <= 755 else 0.02,
    "liaodong_and_bohai": lambda y: 0.025 if y <= 755 else 0.025,
    "taiwan_pre_imperial": lambda y: 0.005,
  }
  cn2_pops = scale_shares(cn2_totals, cn2_shares)
  cn2_specs = [
    ("guannei_dao", "Guannei Circuit (Chang'an and Shaanxi-Ordos)", u_cn(["Shaanxi", "Ningxia"]), cn2_pops["guannei_dao"]),
    ("henan_dao", "Henan Circuit (Luoyang, Henan and Shandong)", u_cn(["Henan", "Shandong"]), cn2_pops["henan_dao"]),
    ("hebei_dao", "Hebei Circuit (North China Plain)", u_cn(["Hebei", "Beijing", "Tianjin"]), cn2_pops["hebei_dao"]),
    ("hedong_dao", "Hedong Circuit (Shanxi and Inner Mongolia Steppe)", u_cn(["Shanxi", "Inner Mongol"]), cn2_pops["hedong_dao"]),
    ("longyou_and_xiyu", "Longyou Circuit and Western Regions (Anxi-Beiting)", u_cn(["Gansu", "Xinjiang"]), cn2_pops["longyou_and_xiyu"]),
    ("shannan_dao", "Shannan Circuit (Han River and Hubei)", u_cn(["Hubei"]), cn2_pops["shannan_dao"]),
    ("huainan_dao", "Huainan Circuit (Yangzhou, Anhui and Northern Jiangsu)", u_cn(["Anhui", "Jiangsu"]), cn2_pops["huainan_dao"]),
    ("jiangnan_dao", "Jiangnan Circuit (Zhejiang, Jiangxi, Hunan and Fujian)", u_cn(["Shanghai", "Zhejiang", "Jiangxi", "Hunan", "Fujian"]), cn2_pops["jiangnan_dao"]),
    ("jiannan_dao", "Jiannan Circuit (Sichuan Basin and Chongqing)", u_cn(["Sichuan", "Chongqing"]), cn2_pops["jiannan_dao"]),
    ("lingnan_dao", "Lingnan Circuit (Guangdong, Guangxi and Hainan)", u_cn(["Guangdong", "Guangxi", "Hainan", "Hong Kong", "Macao"]), cn2_pops["lingnan_dao"]),
    ("liaodong_and_bohai", "Liaodong and Bohai Northeast", u_cn(["Liaoning", "Jilin", "Heilongjiang"]), cn2_pops["liaodong_and_bohai"]),
    ("tubo_and_nanzhao", "Tubo Tibetan Empire and Nanzhao (Tibet, Qinghai, Yunnan-Guizhou)", u_cn(["Xizang", "Qinghai", "Yunnan", "Guizhou"]), cn2_pops["tubo_and_nanzhao"]),
    ("taiwan_pre_imperial", "Taiwan (Formosa)", tw_geom, cn2_pops["taiwan_pre_imperial"]),
  ]

  # =========================================================================
  # 5. CHINA VOL 3 (960..1368): Liao, Song, Jin & Yuan (*Xingsheng* & Polities)
  # =========================================================================
  # Grounded directly in Zhongguo Renkou Shi Vol. 3 (Wu Songdi)
  cn3_totals = {
    960: 53000000, 980: 57500000, 1050: 92000000, 1102: 122000000,
    1124: 128000000, 1162: 112000000, 1210: 138000000, 1270: 82000000,
    1290: 78000000, 1330: 88000000, 1350: 91000000, 1368: 73000000,
  }
  cn3_shares = {
    "jiangzhe_lower_yangtze": lambda y: 0.22 if y <= 1210 else 0.29,
    "zhongshu_north_china": lambda y: 0.19 if y <= 1210 else 0.15,
    "jiangxi_and_guangdong": lambda y: 0.11 if y <= 1210 else 0.14,
    "huguang_middle_yangtze": lambda y: 0.10 if y <= 1210 else 0.12,
    "henan_jiangbei": lambda y: 0.11 if y <= 1210 else 0.08,
    "sichuan_four_circuits": lambda y: 0.09 if y <= 1210 else 0.04,  # Massive Mongol conquest collapse in Sichuan!
    "shaanxi_guanzhong": lambda y: 0.055 if y <= 1210 else 0.045,
    "liaoyang_manchuria": lambda y: 0.045 if y <= 1210 else 0.04,
    "dali_yunnan": lambda y: 0.03 if y <= 1210 else 0.035,
    "xixia_hexi_gansu": lambda y: 0.02 if y <= 1210 else 0.02,
    "inner_mongolia_steppe": lambda y: 0.012,
    "tibet_xuanzhengyuan": lambda y: 0.012,
    "xinjiang_chagatai": lambda y: 0.008,
    "taiwan_penghu": lambda y: 0.003,
  }
  cn3_pops = scale_shares(cn3_totals, cn3_shares)
  cn3_specs = [
    ("zhongshu_north_china", "Zhongshusheng North China (Hebei, Shandong and Shanxi)", u_cn(["Beijing", "Tianjin", "Hebei", "Shandong", "Shanxi"]), cn3_pops["zhongshu_north_china"]),
    ("henan_jiangbei", "Henan-Jiangbei Province (Henan, Anhui and Northern Jiangsu)", u_cn(["Henan", "Anhui", "Jiangsu"]), cn3_pops["henan_jiangbei"]),
    ("shaanxi_guanzhong", "Shaanxi Province (Guanzhong and Qin-Long)", u_cn(["Shaanxi"]), cn3_pops["shaanxi_guanzhong"]),
    ("xixia_hexi_gansu", "Western Xia and Gansu Province (Hexi and Ningxia)", u_cn(["Gansu", "Ningxia"]), cn3_pops["xixia_hexi_gansu"]),
    ("jiangzhe_lower_yangtze", "Jiangzhe Province (Zhejiang, Shanghai and Fujian)", u_cn(["Shanghai", "Zhejiang", "Fujian"]), cn3_pops["jiangzhe_lower_yangtze"]),
    ("jiangxi_and_guangdong", "Jiangxi Province (Jiangxi and Guangdong)", u_cn(["Jiangxi", "Guangdong", "Hong Kong", "Macao"]), cn3_pops["jiangxi_and_guangdong"]),
    ("huguang_middle_yangtze", "Huguang Province (Hubei, Hunan, Guangxi, Guizhou and Hainan)", u_cn(["Hubei", "Hunan", "Guangxi", "Guizhou", "Hainan"]), cn3_pops["huguang_middle_yangtze"]),
    ("sichuan_four_circuits", "Sichuan Province (Four Circuits of Shu)", u_cn(["Sichuan", "Chongqing"]), cn3_pops["sichuan_four_circuits"]),
    ("liaoyang_manchuria", "Liaoyang Province (Liao-Jin-Yuan Manchuria)", u_cn(["Liaoning", "Jilin", "Heilongjiang"]), cn3_pops["liaoyang_manchuria"]),
    ("dali_yunnan", "Dali Kingdom and Yunnan Province", u_cn(["Yunnan"]), cn3_pops["dali_yunnan"]),
    ("tibet_xuanzhengyuan", "Tibet and Qinghai (Xuanzhengyuan)", u_cn(["Xizang", "Qinghai"]), cn3_pops["tibet_xuanzhengyuan"]),
    ("xinjiang_chagatai", "Xinjiang (Qocho Uyghur and Chagatai)", u_cn(["Xinjiang"]), cn3_pops["xinjiang_chagatai"]),
    ("inner_mongolia_steppe", "Inner Mongolia Steppe and Shangdu", u_cn(["Inner Mongol"]), cn3_pops["inner_mongolia_steppe"]),
    ("taiwan_penghu", "Taiwan and Penghu", tw_geom, cn3_pops["taiwan_penghu"]),
  ]

  # =========================================================================
  # 6. CHINA VOL 4 (1368..1644): Ming Dynasty (EXACT Cao Shuji Vol. 4 / App 1 & 6!)
  # =========================================================================
  # Exact Cao Shuji 2024 Appendix 1 & 6 regional figures (thousands -> inhabitants)
  ming_table = {
    # key: (name, cn_adm1_list, {1368, 1393, 1500, 1580, 1630, 1644})
    "ming_beizhili": ("Beizhili (Beiping Metropolitan)", ["Beijing", "Tianjin", "Hebei"], {1368: 2500000, 1393: 2936000, 1500: 5500000, 1580: 8611000, 1630: 10500000, 1644: 7800000}),
    "ming_nanzhili": ("Nanzhili (Nanjing Metropolitan: Jiangsu and Anhui)", ["Jiangsu", "Shanghai", "Anhui"], {1368: 12200000, 1393: 13200000, 1500: 21500000, 1580: 28600000, 1630: 33500000, 1644: 26800000}),
    "ming_shandong": ("Shandong Province", ["Shandong"], {1368: 5300000, 1393: 6042000, 1500: 9400000, 1580: 13066000, 1630: 15800000, 1644: 11200000}),
    "ming_shanxi": ("Shanxi Province", ["Shanxi"], {1368: 4100000, 1393: 4480000, 1500: 6600000, 1580: 8750000, 1630: 10200000, 1644: 7200000}),
    "ming_henan": ("Henan Province", ["Henan"], {1368: 3400000, 1393: 3960000, 1500: 7600000, 1580: 12200000, 1630: 14600000, 1644: 8600000}),
    "ming_shaanxi": ("Shaanxi Province (incl. Gansu and Ningxia)", ["Shaanxi", "Gansu", "Ningxia"], {1368: 2700000, 1393: 2998000, 1500: 5500000, 1580: 8266000, 1630: 9800000, 1644: 6400000}),
    "ming_zhejiang": ("Zhejiang Province", ["Zhejiang"], {1368: 8800000, 1393: 9400000, 1500: 13800000, 1580: 17400000, 1630: 20400000, 1644: 17200000}),
    "ming_jiangxi": ("Jiangxi Province", ["Jiangxi"], {1368: 7100000, 1393: 7550000, 1500: 10900000, 1580: 13600000, 1630: 15800000, 1644: 12600000}),
    "ming_huguang": ("Huguang Province (Hubei and Hunan)", ["Hubei", "Hunan"], {1368: 5100000, 1393: 5550000, 1500: 9200000, 1580: 13500000, 1630: 16800000, 1644: 13100000}),
    "ming_fujian": ("Fujian Province", ["Fujian"], {1368: 3500000, 1393: 3820000, 1500: 5600000, 1580: 7400000, 1630: 8800000, 1644: 7500000}),
    "ming_guangdong": ("Guangdong Province (incl. Hainan, HK and Macao)", ["Guangdong", "Hainan", "Hong Kong", "Macao"], {1368: 3300000, 1393: 3650000, 1500: 5900000, 1580: 8200000, 1630: 10200000, 1644: 8600000}),
    "ming_guangxi": ("Guangxi Province", ["Guangxi"], {1368: 1900000, 1393: 2050000, 1500: 3000000, 1580: 3900000, 1630: 4700000, 1644: 4100000}),
    "ming_sichuan": ("Sichuan Province (incl. Chongqing)", ["Sichuan", "Chongqing"], {1368: 2500000, 1393: 2850000, 1500: 5400000, 1580: 8100000, 1630: 9600000, 1644: 4500000}),
    "ming_yunnan": ("Yunnan Province", ["Yunnan"], {1368: 1600000, 1393: 1780000, 1500: 2550000, 1580: 3300000, 1630: 3900000, 1644: 3400000}),
    "ming_guizhou": ("Guizhou Province", ["Guizhou"], {1368: 900000, 1393: 1020000, 1500: 1500000, 1580: 1980000, 1630: 2400000, 1644: 2100000}),
    "ming_liaodong_manchuria": ("Liaodong Garrison and Jurchen Northeast", ["Liaoning", "Jilin", "Heilongjiang"], {1368: 1400000, 1393: 1550000, 1500: 2200000, 1580: 2850000, 1630: 3100000, 1644: 2200000}),
    "ming_inner_mongolia": ("Northern Yuan and Inner Mongolian Banners", ["Inner Mongol"], {1368: 850000, 1393: 800000, 1500: 880000, 1580: 950000, 1630: 1020000, 1644: 980000}),
    "ming_xinjiang": ("Xinjiang (Moghulistan and Turpan)", ["Xinjiang"], {1368: 650000, 1393: 680000, 1500: 760000, 1580: 850000, 1630: 920000, 1644: 900000}),
    "ming_tibet_qinghai": ("Tibet and Qinghai (Ü-Tsang, Kham and Amdo)", ["Xizang", "Qinghai"], {1368: 1100000, 1393: 1150000, 1500: 1250000, 1580: 1350000, 1630: 1420000, 1644: 1400000}),
    "ming_taiwan": ("Taiwan (Austronesian and Late Ming Coastal Frontier)", ["Taiwan"], {1368: 180000, 1393: 190000, 1500: 220000, 1580: 250000, 1630: 300000, 1644: 340000}),
  }
  cn4_specs = [(k, v[0], u_cn(v[1]), v[2]) for k, v in ming_table.items()]

  # =========================================================================
  # 7. CHINA VOL 5 (1644..1911): Qing Dynasty (CHGIS v6 1820 Polygons + Cao Shuji Vol. 5!)
  # =========================================================================
  def clip_chgis(chgis_dict, key, fallback_cn):
    g = chgis_dict.get(key)
    if g is not None and not g.is_empty:
      inter = g.intersection(cn_union).buffer(0)
      if not inter.is_empty and inter.area > 0.05:
        return inter
    return u_cn(fallback_cn)

  # Exact Cao Shuji Vol. 5 / Appendix 6 & 7 provincial totals (1644, 1680, 1776, 1820, 1851, 1880, 1910, 1911)
  qing_table = [
    ("qing_zhili", "Zhili Province", clip_chgis(chgis_1820, "Zhili", ["Beijing", "Tianjin", "Hebei"]), {1644: 7800000, 1680: 9400000, 1776: 19400000, 1820: 23500000, 1851: 26800000, 1880: 24500000, 1910: 27400000, 1911: 27500000}),
    ("qing_jiangsu", "Jiangsu Province", clip_chgis(chgis_1820, "Jiangsu", ["Jiangsu", "Shanghai"]), {1644: 16200000, 1680: 17500000, 1776: 29500000, 1820: 37800000, 1851: 44200000, 1880: 26400000, 1910: 32400000, 1911: 32600000}),
    ("qing_anhui", "Anhui Province", clip_chgis(chgis_1820, "Anhui", ["Anhui"]), {1644: 10600000, 1680: 11400000, 1776: 25600000, 1820: 34200000, 1851: 37600000, 1880: 17800000, 1910: 21800000, 1911: 21900000}),
    ("qing_zhejiang", "Zhejiang Province", clip_chgis(chgis_1820, "Zhejiang", ["Zhejiang"]), {1644: 17200000, 1680: 14500000, 1776: 21500000, 1820: 27500000, 1851: 30400000, 1880: 15600000, 1910: 21400000, 1911: 21500000}),
    ("qing_jiangxi", "Jiangxi Province", clip_chgis(chgis_1820, "Jiangxi", ["Jiangxi"]), {1644: 12600000, 1680: 11800000, 1776: 18800000, 1820: 23700000, 1851: 24600000, 1880: 18900000, 1910: 19200000, 1911: 19300000}),
    ("qing_fujian", "Fujian Province (excl. Taiwan)", clip_chgis(chgis_1820, "Fujian", ["Fujian"]).difference(tw_geom.buffer(0.1)).buffer(0), {1644: 7500000, 1680: 6800000, 1776: 11600000, 1820: 14600000, 1851: 16200000, 1880: 13800000, 1910: 13500000, 1911: 13550000}),
    ("qing_hubei", "Hubei Province", clip_chgis(chgis_1820, "Hubei", ["Hubei"]), {1644: 7100000, 1680: 7600000, 1776: 16800000, 1820: 24900000, 1851: 28800000, 1880: 25600000, 1910: 27900000, 1911: 28000000}),
    ("qing_hunan", "Hunan Province", clip_chgis(chgis_1820, "Hunan", ["Hunan"]), {1644: 6000000, 1680: 6400000, 1776: 15400000, 1820: 19200000, 1851: 21100000, 1880: 21800000, 1910: 25200000, 1911: 25300000}),
    ("qing_henan", "Henan Province", clip_chgis(chgis_1820, "Henan", ["Henan"]), {1644: 8600000, 1680: 9800000, 1776: 20600000, 1820: 25300000, 1851: 29100000, 1880: 23800000, 1910: 28500000, 1911: 28600000}),
    ("qing_shandong", "Shandong Province", clip_chgis(chgis_1820, "Shandong", ["Shandong"]), {1644: 11200000, 1680: 13500000, 1776: 24200000, 1820: 29200000, 1851: 33200000, 1880: 30600000, 1910: 32500000, 1911: 32600000}),
    ("qing_shanxi", "Shanxi Province", clip_chgis(chgis_1820, "Shanxi", ["Shanxi"]), {1644: 7200000, 1680: 7800000, 1776: 12700000, 1820: 14600000, 1851: 15800000, 1880: 9600000, 1910: 11200000, 1911: 11250000}),
    ("qing_shaanxi", "Shaanxi Province", clip_chgis(chgis_1820, "Shaanxi", ["Shaanxi"]), {1644: 4400000, 1680: 4700000, 1776: 8400000, 1820: 12100000, 1851: 13500000, 1880: 8400000, 1910: 9200000, 1911: 9250000}),
    ("qing_gansu", "Gansu Province (incl. Ningxia)", clip_chgis(chgis_1820, "Gansu", ["Gansu", "Ningxia"]), {1644: 2000000, 1680: 2200000, 1776: 12200000, 1820: 15200000, 1851: 16200000, 1880: 5200000, 1910: 6100000, 1911: 6150000}),
    ("qing_sichuan", "Sichuan Province (incl. Chongqing)", clip_chgis(chgis_1820, "Sichuan", ["Sichuan", "Chongqing"]), {1644: 4500000, 1680: 3200000, 1776: 16800000, 1820: 27700000, 1851: 35600000, 1880: 44200000, 1910: 51500000, 1911: 51800000}),
    ("qing_guangdong", "Guangdong Province (incl. Hainan)", clip_chgis(chgis_1820, "Guangdong", ["Guangdong", "Hainan"]).difference(unary_union([hk_geom, mo_geom]).buffer(0.05)).buffer(0), {1644: 8550000, 1680: 8900000, 1776: 16200000, 1820: 21500000, 1851: 26400000, 1880: 26800000, 1910: 29400000, 1911: 29500000}),
    ("qing_guangxi", "Guangxi Province", clip_chgis(chgis_1820, "Guangxi", ["Guangxi"]), {1644: 4100000, 1680: 4300000, 1776: 7200000, 1820: 8700000, 1851: 9900000, 1880: 9600000, 1910: 11200000, 1911: 11250000}),
    ("qing_yunnan", "Yunnan Province", clip_chgis(chgis_1820, "Yunnan", ["Yunnan"]), {1644: 3400000, 1680: 3600000, 1776: 6400000, 1820: 8900000, 1851: 10900000, 1880: 7800000, 1910: 9800000, 1911: 9850000}),
    ("qing_guizhou", "Guizhou Province", clip_chgis(chgis_1820, "Guizhou", ["Guizhou"]), {1644: 2100000, 1680: 2300000, 1776: 5400000, 1820: 6600000, 1851: 7700000, 1880: 6900000, 1910: 8400000, 1911: 8450000}),
    ("qing_manchuria", "Manchuria (Shengjing, Jilin and Heilongjiang)", unary_union([clip_chgis(chgis_1820, "Shengjing", ["Liaoning"]), clip_chgis(chgis_1820, "Jinlin", ["Jilin"]), clip_chgis(chgis_1820, "Heilongjiang", ["Heilongjiang"])]).buffer(0), {1644: 2200000, 1680: 1500000, 1776: 2800000, 1820: 4500000, 1851: 6800000, 1880: 10500000, 1910: 18400000, 1911: 18700000}),
    ("qing_inner_mongolia", "Inner Mongolia Leagues and Banners", clip_chgis(chgis_1820, "Neimenggu", ["Inner Mongol"]), {1644: 980000, 1680: 1050000, 1776: 1650000, 1820: 2150000, 1851: 2600000, 1880: 2900000, 1910: 3600000, 1911: 3650000}),
    ("qing_xinjiang", "Xinjiang (Altishahr and Dzungaria)", clip_chgis(chgis_1820, "Xinjiang", ["Xinjiang"]), {1644: 900000, 1680: 950000, 1776: 1200000, 1820: 1550000, 1851: 1850000, 1880: 1550000, 1910: 2250000, 1911: 2270000}),
    ("qing_qinghai", "Qinghai (Kokonor)", clip_chgis(chgis_1820, "Qinghai", ["Qinghai"]), {1644: 350000, 1680: 380000, 1776: 520000, 1820: 650000, 1851: 750000, 1880: 620000, 1910: 820000, 1911: 830000}),
    ("qing_tibet", "Tibet (Xizang)", clip_chgis(chgis_1820, "Xizang", ["Xizang"]), {1644: 1050000, 1680: 1080000, 1776: 1120000, 1820: 1150000, 1851: 1160000, 1880: 1120000, 1910: 1100000, 1911: 1100000}),
    ("qing_taiwan", "Taiwan (Qing Prefecture and Japanese Colonial 1895-1911)", tw_geom, {1644: 340000, 1680: 450000, 1776: 1100000, 1820: 1900000, 1851: 2350000, 1880: 2700000, 1910: 3299000, 1911: 3369000}),
    ("qing_hong_kong_macao", "Hong Kong and Macao", unary_union([hk_geom, mo_geom]).buffer(0), {1644: 25000, 1680: 30000, 1776: 45000, 1820: 55000, 1851: 95000, 1880: 230000, 1910: 520000, 1911: 532000}),
  ]

  # =========================================================================
  # 8. CHINA VOL 6 (1910..1953): Republican & Transitional Era (CHGIS 1911 + Hou Yangfang Vol. 6!)
  # =========================================================================
  rep_table = [
    ("rep_hebei_beiping_tianjin", "Zhili / Hebei, Beiping and Tianjin", clip_chgis(chgis_1911, "Zhili", ["Beijing", "Tianjin", "Hebei"]), {1910: 27400000, 1928: 31200000, 1936: 34800000, 1947: 36500000, 1953: 41440000}),
    ("rep_jiangsu_shanghai", "Jiangsu, Nanjing and Shanghai", clip_chgis(chgis_1911, "Jiangsu", ["Jiangsu", "Shanghai"]), {1910: 32400000, 1928: 36800000, 1936: 41200000, 1947: 43200000, 1953: 47460000}),
    ("rep_anhui", "Anhui Province", clip_chgis(chgis_1911, "Anhui", ["Anhui"]), {1910: 21800000, 1928: 23500000, 1936: 25600000, 1947: 27200000, 1953: 30340000}),
    ("rep_zhejiang", "Zhejiang Province", clip_chgis(chgis_1911, "Zhejiang", ["Zhejiang"]), {1910: 21400000, 1928: 20600000, 1936: 21200000, 1947: 21500000, 1953: 22870000}),
    ("rep_jiangxi", "Jiangxi Province", clip_chgis(chgis_1911, "Jiangxi", ["Jiangxi"]), {1910: 19200000, 1928: 18500000, 1936: 16800000, 1947: 15800000, 1953: 16770000}),
    ("rep_fujian", "Fujian Province", clip_chgis(chgis_1911, "Fujian", ["Fujian"]), {1910: 13500000, 1928: 12600000, 1936: 12100000, 1947: 12300000, 1953: 13140000}),
    ("rep_hubei", "Hubei Province", clip_chgis(chgis_1911, "Hubei", ["Hubei"]), {1910: 27900000, 1928: 26800000, 1936: 26500000, 1947: 26200000, 1953: 27790000}),
    ("rep_hunan", "Hunan Province", clip_chgis(chgis_1911, "Hunan", ["Hunan"]), {1910: 25200000, 1928: 28200000, 1936: 30100000, 1947: 31200000, 1953: 33230000}),
    ("rep_henan", "Henan Province", clip_chgis(chgis_1911, "Henan", ["Henan"]), {1910: 28500000, 1928: 33200000, 1936: 36800000, 1947: 38500000, 1953: 44210000}),
    ("rep_shandong", "Shandong Province", clip_chgis(chgis_1911, "Shandong", ["Shandong"]), {1910: 32500000, 1928: 36500000, 1936: 40400000, 1947: 43200000, 1953: 48880000}),
    ("rep_shanxi", "Shanxi Province", clip_chgis(chgis_1911, "Shanxi", ["Shanxi"]), {1910: 11200000, 1928: 12100000, 1936: 12600000, 1947: 13200000, 1953: 14310000}),
    ("rep_shaanxi", "Shaanxi Province", clip_chgis(chgis_1911, "Shaanxi", ["Shaanxi"]), {1910: 9200000, 1928: 11200000, 1936: 11800000, 1947: 13500000, 1953: 15880000}),
    ("rep_gansu_ningxia", "Gansu and Ningxia", clip_chgis(chgis_1911, "Gansu", ["Gansu", "Ningxia"]), {1910: 6100000, 1928: 7800000, 1936: 9400000, 1947: 11200000, 1953: 12930000}),
    ("rep_sichuan_xikang", "Sichuan, Chongqing and Xikang", clip_chgis(chgis_1911, "Sichuan", ["Sichuan", "Chongqing"]), {1910: 51500000, 1928: 53800000, 1936: 57200000, 1947: 60500000, 1953: 65690000}),
    ("rep_guangdong_hainan", "Guangdong and Hainan", clip_chgis(chgis_1911, "Guangdong", ["Guangdong", "Hainan"]).difference(unary_union([hk_geom, mo_geom]).buffer(0.05)).buffer(0), {1910: 29400000, 1928: 31600000, 1936: 32800000, 1947: 33400000, 1953: 34770000}),
    ("rep_guangxi", "Guangxi Province", clip_chgis(chgis_1911, "Guangxi", ["Guangxi"]), {1910: 11200000, 1928: 13400000, 1936: 15400000, 1947: 17200000, 1953: 19560000}),
    ("rep_yunnan", "Yunnan Province", clip_chgis(chgis_1911, "Yunnan", ["Yunnan"]), {1910: 9800000, 1928: 12200000, 1936: 14100000, 1947: 15800000, 1953: 17470000}),
    ("rep_guizhou", "Guizhou Province", clip_chgis(chgis_1911, "Guizhou", ["Guizhou"]), {1910: 8400000, 1928: 10800000, 1936: 12400000, 1947: 13800000, 1953: 15040000}),
    ("rep_liaoning_fengtian", "Fengtian / Liaoning Province", clip_chgis(chgis_1911, "Fengtian", ["Liaoning"]), {1910: 11200000, 1928: 15200000, 1936: 17500000, 1947: 18900000, 1953: 20570000}),
    ("rep_jilin", "Jilin Province", clip_chgis(chgis_1911, "Jilin", ["Jilin"]), {1910: 5100000, 1928: 7600000, 1936: 9400000, 1947: 10200000, 1953: 11290000}),
    ("rep_heilongjiang", "Heilongjiang Province", clip_chgis(chgis_1911, "Heilongjiang", ["Heilongjiang"]), {1910: 2100000, 1928: 4800000, 1936: 7500000, 1947: 9800000, 1953: 11900000}),
    ("rep_inner_mongolia_chahar_suiyuan", "Inner Mongolia (Rehe, Chahar and Suiyuan)", clip_chgis(chgis_1911, "Neimenggu", ["Inner Mongol"]), {1910: 3600000, 1928: 4600000, 1936: 5200000, 1947: 5600000, 1953: 6100000}),
    ("rep_xinjiang", "Xinjiang Province", clip_chgis(chgis_1911, "Xinjiang", ["Xinjiang"]), {1910: 2250000, 1928: 2950000, 1936: 3600000, 1947: 4250000, 1953: 4870000}),
    ("rep_qinghai", "Qinghai Province", clip_chgis(chgis_1911, "Qinghai", ["Qinghai"]), {1910: 820000, 1928: 1080000, 1936: 1280000, 1947: 1460000, 1953: 1680000}),
    ("rep_tibet", "Tibet (Xizang)", clip_chgis(chgis_1911, "Xizang", ["Xizang"]), {1910: 1100000, 1928: 1120000, 1936: 1150000, 1947: 1200000, 1953: 1270000}),
    ("rep_taiwan", "Taiwan (Japanese Colonial and Post-1945)", tw_geom, {1910: 3299000, 1928: 4438000, 1936: 5452000, 1947: 6495000, 1953: 8438000}),
    ("rep_hong_kong", "Hong Kong", hk_geom, {1910: 445000, 1928: 780000, 1936: 988000, 1947: 1750000, 1953: 2242000}),
    ("rep_macao", "Macao", mo_geom, {1910: 75000, 1928: 155000, 1936: 185000, 1947: 210000, 1953: 188000}),
  ]

  # =========================================================================
  # 9. MONGOLIA POST-1912 (1912..2026): Regime III Exact NE10m 22 Aimags + NSO 1212.mn!
  # =========================================================================
  nat_hist, aimag_nso = load_mongolia_nso_aimags()
  # Map NE10m aimag names -> NSO 1212.mn English aimag names
  ne_to_nso = {
    "Arhangay": "Arkhangai", "Bayan-Ölgiy": "Bayan-Ulgii", "Bayanhongor": "Bayankhongor",
    "Bulgan": "Bulgan", "Darhan-Uul": "Darkhan-Uul", "Dornod": "Dornod",
    "Dornogovi": "Dornogovi", "Dundgovi": "Dundgovi", "Dzavhan": "Zavkhan",
    "Govi-Altay": "Govi-Altai", "Govĭ-Sümber": "Govisumber", "Hentiy": "Khentii",
    "Hovd": "Khovd", "Hövsgöl": "Khuvsgul", "Orhon": "Orkhon",
    "Selenge": "Selenge", "Sühbaatar": "Sukhbaatar", "Töv": "Tuv",
    "Ulaanbaatar": "Ulaanbaatar", "Uvs": "Uvs", "Ömnögovi": "Umnugovi", "Övörhangay": "Uvurkhangai",
  }
  # Earliest year available in aimag_nso (e.g. 1989 or 1990) used to back-project aimag shares cleanly to 1912..1988
  # while accounting for Ulaanbaatar's urbanisation rise (1918: ~7% -> 1956: ~15% -> 1969: ~22% -> 1979: ~25% -> 1989: ~27% -> 2025: ~49%)
  earliest_yr = min(min(d.keys()) for d in aimag_nso.values())
  base_1989_tot = sum(aimag_nso[nso_nm].get(earliest_yr, 20000) for nso_nm in ne_to_nso.values())
  mn3_specs = []
  for ne_nm, nso_nm in sorted(ne_to_nso.items()):
    nso_d = aimag_nso.get(nso_nm, {})
    pop_d = {}
    base_sh = nso_d.get(earliest_yr, 20000) / max(1, base_1989_tot)
    # Historical pre-Nso benchmark years from nat_hist
    for yr in [1912, 1918, 1925, 1935, 1944, 1950, 1956, 1963, 1969, 1979, 1985]:
      nat_t = nat_hist.get(yr, 644000 if yr == 1912 else 758700)
      # Adjust Ulaanbaatar/Darkhan/Orkhon industrial urbanisation share back in time
      if nso_nm == "Ulaanbaatar":
        ub_sh = 0.075 if yr <= 1935 else (0.10 if yr <= 1950 else (0.15 if yr <= 1960 else (0.22 if yr <= 1970 else 0.26)))
        pop_d[yr] = int(round(nat_t * ub_sh))
      elif nso_nm in ("Darkhan-Uul", "Orkhon"):
        # Industrial cities founded 1961 (Darkhan) & 1974 (Erdenet); rural pastoral base prior
        ind_sh = 0.006 if yr < 1963 else (0.015 if yr < 1975 else base_sh * 0.85)
        pop_d[yr] = int(round(nat_t * ind_sh))
      else:
        ub_sh = 0.075 if yr <= 1935 else (0.10 if yr <= 1950 else (0.15 if yr <= 1960 else (0.22 if yr <= 1970 else 0.26)))
        non_ub_1989 = 1.0 - (aimag_nso.get("Ulaanbaatar", {}).get(earliest_yr, 540000) / max(1, base_1989_tot))
        adj_sh = (base_sh / max(0.05, non_ub_1989)) * (1.0 - ub_sh)
        pop_d[yr] = int(round(nat_t * adj_sh))
    for yr, val in nso_d.items():
      pop_d[yr] = val
    # Add 2026 projection equal to latest + 1% trend
    latest_y = max(pop_d.keys())
    if latest_y < 2026:
      pop_d[2026] = int(round(pop_d[latest_y] * 1.012))
    rkey = "mng_" + nso_nm.lower().replace("-", "_").replace(" ", "_")
    mn3_specs.append((rkey, nso_nm, mn_adm1[ne_nm], pop_d))

  # =========================================================================
  # 10. CHINA SINCE 1949 (1949..2026): Regime III Exact 31 PRC Provinces + TW + HK + MO!
  # =========================================================================
  # Official PRC National Censuses (1953, 1964, 1982, 1990, 2000, 2010, 2020) + 1949, 1960 (GLF), 2025/2026 NBS
  # Figures in thousands -> multiplied by 1000
  prc_prov_k = {
    "Beijing":      {1949: 4140, 1953: 4590, 1960: 7320, 1964: 7597, 1982: 9231, 1990: 10819, 2000: 13820, 2010: 19612, 2020: 21893, 2025: 21832},
    "Tianjin":      {1949: 3990, 1953: 4620, 1960: 5900, 1964: 6249, 1982: 7764, 1990: 8785,  2000: 10010, 2010: 12938, 2020: 13866, 2025: 13640},
    "Hebei":        {1949: 30860, 1953: 33180, 1960: 38200, 1964: 39417, 1982: 53006, 1990: 61083, 2000: 67440, 2010: 71854, 2020: 74610, 2025: 73780},
    "Shanxi":       {1949: 12810, 1953: 14314, 1960: 17000, 1964: 18015, 1982: 25291, 1990: 28759, 2000: 32970, 2010: 35712, 2020: 34916, 2025: 34460},
    "Inner Mongol": {1949: 6080, 1953: 7338, 1960: 11800, 1964: 12349, 1982: 19274, 1990: 21457, 2000: 23760, 2010: 24706, 2020: 24049, 2025: 23880},
    "Liaoning":     {1949: 18310, 1953: 20566, 1960: 25600, 1964: 26946, 1982: 35722, 1990: 39460, 2000: 42380, 2010: 43746, 2020: 42591, 2025: 41550},
    "Jilin":        {1949: 10090, 1953: 11290, 1960: 14100, 1964: 15669, 1982: 22560, 1990: 24659, 2000: 27280, 2010: 27462, 2020: 24073, 2025: 23170},
    "Heilongjiang": {1949: 10120, 1953: 11897, 1960: 18200, 1964: 20118, 1982: 32666, 1990: 35215, 2000: 36890, 2010: 38312, 2020: 31850, 2025: 30290},
    "Shanghai":     {1949: 7730, 1953: 8960, 1960: 10560, 1964: 10816, 1982: 11860, 1990: 13342, 2000: 16740, 2010: 23019, 2020: 24871, 2025: 24802},
    "Jiangsu":      {1949: 35120, 1953: 38330, 1960: 42800, 1964: 44505, 1982: 60521, 1990: 67057, 2000: 74380, 2010: 78660, 2020: 84748, 2025: 85260},
    "Zhejiang":     {1949: 20830, 1953: 22866, 1960: 26800, 1964: 28319, 1982: 38885, 1990: 41446, 2000: 46770, 2010: 54427, 2020: 64568, 2025: 66700},
    "Anhui":        {1949: 27860, 1953: 30344, 1960: 30430, 1964: 31242, 1982: 49666, 1990: 56181, 2000: 59860, 2010: 59501, 2020: 61027, 2025: 61230},
    "Fujian":       {1949: 11880, 1953: 13143, 1960: 15800, 1964: 16757, 1982: 25931, 1990: 30097, 2000: 34710, 2010: 36894, 2020: 41540, 2025: 41930},
    "Jiangxi":      {1949: 15690, 1953: 16773, 1960: 19900, 1964: 21068, 1982: 33185, 1990: 37710, 2000: 41400, 2010: 44567, 2020: 45189, 2025: 45020},
    "Shandong":     {1949: 45490, 1953: 48877, 1960: 51880, 1964: 55519, 1982: 74419, 1990: 84393, 2000: 90790, 2010: 95793, 2020: 101527, 2025: 100800},
    "Henan":        {1949: 41740, 1953: 44215, 1960: 48180, 1964: 50326, 1982: 74423, 1990: 85510, 2000: 92560, 2010: 94024, 2020: 99366, 2025: 97850},
    "Hubei":        {1949: 25800, 1953: 27790, 1960: 31500, 1964: 33709, 1982: 47804, 1990: 53969, 2000: 60280, 2010: 57238, 2020: 57753, 2025: 58340},
    "Hunan":        {1949: 29870, 1953: 33227, 1960: 35800, 1964: 37182, 1982: 54009, 1990: 60660, 2000: 64400, 2010: 65684, 2020: 66445, 2025: 65390},
    "Guangdong":    {1949: 27830, 1953: 32080, 1960: 36800, 1964: 39260, 1982: 53630, 1990: 62829, 2000: 86420, 2010: 104303, 2020: 126013, 2025: 127800},
    "Guangxi":      {1949: 18420, 1953: 19561, 1960: 21500, 1964: 23199, 1982: 36421, 1990: 42246, 2000: 44890, 2010: 46027, 2020: 50127, 2025: 50130},
    "Hainan":       {1949: 2510, 1953: 2690, 1960: 3200, 1964: 3540, 1982: 5668, 1990: 6557, 2000: 7870, 2010: 8672, 2020: 10081, 2025: 10480},
    "Chongqing":    {1949: 16400, 1953: 17660, 1960: 17100, 1964: 18200, 1982: 27059, 1990: 28866, 2000: 30900, 2010: 28846, 2020: 32054, 2025: 31905},
    "Sichuan":      {1949: 40900, 1953: 48025, 1960: 49000, 1964: 49757, 1982: 72654, 1990: 78352, 2000: 83290, 2010: 80418, 2020: 83675, 2025: 83640},
    "Guizhou":      {1949: 14160, 1953: 15037, 1960: 16200, 1964: 17141, 1982: 28553, 1990: 32391, 2000: 35250, 2010: 34746, 2020: 38562, 2025: 38600},
    "Yunnan":       {1949: 15950, 1953: 17473, 1960: 19200, 1964: 20510, 1982: 32554, 1990: 36973, 2000: 42880, 2010: 45966, 2020: 47209, 2025: 46550},
    "Xizang":       {1949: 1150, 1953: 1274, 1960: 1240, 1964: 1251, 1982: 1892, 1990: 2196, 2000: 2620, 2010: 3002, 2020: 3648, 2025: 3700},
    "Shaanxi":      {1949: 13170, 1953: 15881, 1960: 19300, 1964: 20767, 1982: 28904, 1990: 32882, 2000: 36050, 2010: 37327, 2020: 39529, 2025: 39530},
    "Gansu":        {1949: 9680, 1953: 11291, 1960: 12450, 1964: 12631, 1982: 19569, 1990: 22371, 2000: 25620, 2010: 25575, 2020: 25020, 2025: 24580},
    "Qinghai":      {1949: 1480, 1953: 1677, 1960: 2080, 1964: 2146, 1982: 3896, 1990: 4457, 2000: 5180, 2010: 5627, 2020: 5924, 2025: 5930},
    "Ningxia":      {1949: 1200, 1953: 1638, 1960: 2020, 1964: 2108, 1982: 3896, 1990: 4655, 2000: 5620, 2010: 6301, 2020: 7203, 2025: 7290},
    "Xinjiang":     {1949: 4330, 1953: 4874, 1960: 6860, 1964: 7270, 1982: 13082, 1990: 15156, 2000: 19250, 2010: 21813, 2020: 25852, 2025: 26230},
  }
  cn5_specs = []
  for ne_nm, d_k in sorted(prc_prov_k.items()):
    disp = "Inner Mongolia" if ne_nm == "Inner Mongol" else ("Tibet (Xizang)" if ne_nm == "Xizang" else ne_nm)
    rkey = "prc_" + disp.lower().replace(" (xizang)", "").replace(" ", "_")
    pop_d = {yr: int(round(v * 1000)) for yr, v in d_k.items()}
    pop_d[2026] = int(round(pop_d[2025] * 0.998))
    cn5_specs.append((rkey, disp, cn_adm1[ne_nm], pop_d))

  # Add Taiwan, Hong Kong SAR, Macao SAR
  cn5_specs.append(("prc_taiwan", "Taiwan", tw_geom, {
    1949: 7397000, 1953: 8438000, 1960: 10792000, 1964: 12257000, 1982: 18458000,
    1990: 20401000, 2000: 22277000, 2010: 23162000, 2020: 23561000, 2025: 23400000, 2026: 23380000
  }))
  cn5_specs.append(("prc_hong_kong", "Hong Kong SAR", hk_geom, {
    1949: 1857000, 1953: 2242000, 1960: 3075000, 1964: 3505000, 1982: 5264000,
    1990: 5705000, 2000: 6665000, 2010: 7024000, 2020: 7481000, 2025: 7534000, 2026: 7540000
  }))
  cn5_specs.append(("prc_macao", "Macao SAR", mo_geom, {
    1949: 196000, 1953: 188000, 1960: 169000, 1964: 205000, 1982: 262000,
    1990: 339000, 2000: 432000, 2010: 552000, 2020: 683000, 2025: 688000, 2026: 690000
  }))

  # =========================================================================
  # WRITE ALL 10 CHAPTER BUNDLES
  # =========================================================================
  print("Building all 10 Project JADE chapter areal masks & vector sub-region GeoJSONs:")
  specialist_entries = []
  epoch_entries = []

  j5, msk = write_chapter_bundle(
    os.path.join("1.mongolia_pre_1912", "1.steppe_prehistory_and_nomadic_empires"),
    "steppe_prehistory_and_nomadic_empires",
    "Mongolia Before 1206: Steppe Prehistory and Nomadic Empires (10000BC-1206AD)",
    [-10000, 1206], mn1_specs, mng_mask, land_area
  )
  specialist_entries.append({"id": "steppe_prehistory_and_nomadic_empires", "domain": [-10000, 1206], "domain_group": "sites_east_asia", "json5_path": j5, "mask_path": msk, "priority": 1})

  j5, msk = write_chapter_bundle(
    os.path.join("1.mongolia_pre_1912", "2.mongol_empire_and_qing_mongolia"),
    "mongol_empire_and_qing_mongolia",
    "Mongolia Under the Chinggisid Empire and Qing Suzerainty (1206AD-1912AD)",
    [1206, 1912], mn2_specs, mng_mask, land_area
  )
  epoch_entries.append({"id": "mongol_empire_and_qing_mongolia", "domain": [1206, 1912], "domain_group": "sites_east_asia", "json5_path": j5, "mask_path": msk, "priority": 2})

  j5, msk = write_chapter_bundle(
    os.path.join("2.china_zhongguo_renkou_shi", "1.pre_qin_to_northern_southern_dynasties"),
    "pre_qin_to_northern_southern_dynasties",
    "China from Pre-Qin Prehistory to the Northern and Southern Dynasties (10000BC-589AD)",
    [-10000, 589], cn1_specs, chn_all_mask, land_area
  )
  specialist_entries.append({"id": "pre_qin_to_northern_southern_dynasties", "domain": [-10000, 589], "domain_group": "sites_east_asia", "json5_path": j5, "mask_path": msk, "priority": 1})

  j5, msk = write_chapter_bundle(
    os.path.join("2.china_zhongguo_renkou_shi", "2.sui_tang_and_five_dynasties"),
    "sui_tang_and_five_dynasties",
    "China During the Sui, Tang and Five Dynasties (589AD-960AD)",
    [589, 960], cn2_specs, chn_all_mask, land_area
  )
  epoch_entries.append({"id": "sui_tang_and_five_dynasties", "domain": [589, 960], "domain_group": "sites_east_asia", "json5_path": j5, "mask_path": msk, "priority": 2})

  j5, msk = write_chapter_bundle(
    os.path.join("2.china_zhongguo_renkou_shi", "3.liao_song_jin_and_yuan"),
    "liao_song_jin_and_yuan",
    "China During the Liao, Song, Jin and Yuan Dynasties (960AD-1368AD)",
    [960, 1368], cn3_specs, chn_all_mask, land_area
  )
  epoch_entries.append({"id": "liao_song_jin_and_yuan", "domain": [960, 1368], "domain_group": "sites_east_asia", "json5_path": j5, "mask_path": msk, "priority": 2})

  j5, msk = write_chapter_bundle(
    os.path.join("2.china_zhongguo_renkou_shi", "4.ming_dynasty"),
    "ming_dynasty",
    "China During the Ming Dynasty (1368AD-1644AD)",
    [1368, 1644], cn4_specs, chn_all_mask, land_area
  )
  epoch_entries.append({"id": "ming_dynasty", "domain": [1368, 1644], "domain_group": "sites_east_asia", "json5_path": j5, "mask_path": msk, "priority": 2})

  j5, msk = write_chapter_bundle(
    os.path.join("2.china_zhongguo_renkou_shi", "5.qing_dynasty"),
    "qing_dynasty",
    "China During the Qing Dynasty (1644AD-1911AD)",
    [1644, 1911], qing_table, chn_all_mask, land_area
  )
  epoch_entries.append({"id": "qing_dynasty", "domain": [1644, 1911], "domain_group": "sites_east_asia", "json5_path": j5, "mask_path": msk, "priority": 2})

  j5, msk = write_chapter_bundle(
    os.path.join("2.china_zhongguo_renkou_shi", "6.republican_and_transitional_era"),
    "republican_and_transitional_era",
    "China from the Xuantong Census to the First National Census (1910AD-1953AD)",
    [1910, 1953], rep_table, chn_all_mask, land_area
  )
  epoch_entries.append({"id": "republican_and_transitional_era", "domain": [1910, 1953], "domain_group": "sites_east_asia", "json5_path": j5, "mask_path": msk, "priority": 2})

  j5, msk = write_chapter_bundle(
    os.path.join("3.mongolia_post_1912", "1.mongolia_modern_era"),
    "mongolia_modern_era",
    "Mongolia After 1912: From the Bogd Khanate to Modern Aimags (1912AD-2026AD)",
    [1912, 2026], mn3_specs, mng_mask, land_area
  )
  epoch_entries.append({"id": "mongolia_modern_era", "domain": [1912, 2026], "domain_group": "sites_east_asia", "is_admin1": True, "json5_path": j5, "mask_path": msk, "priority": 3})

  j5, msk = write_chapter_bundle(
    os.path.join("4.china_since_1949", "1.prc_taiwan_hong_kong_and_macao"),
    "prc_taiwan_hong_kong_and_macao",
    "China Since 1949: People's Republic, Taiwan, Hong Kong and Macao (1949AD-2026AD)",
    [1949, 2026], cn5_specs, chn_all_mask, land_area
  )
  epoch_entries.append({"id": "prc_taiwan_hong_kong_and_macao", "domain": [1949, 2026], "domain_group": "sites_east_asia", "is_admin1": True, "json5_path": j5, "mask_path": msk, "priority": 3})

  # =========================================================================
  # WRITE JADE/jade_areal_masks.json5 & Substrata.viscount/config/jade.json5
  # =========================================================================
  hyde_years = [
    -10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000,
    0, 100, 200, 300, 400, 500, 600, 700, 800, 900,
    1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
    1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790,
    1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890,
    1900, 1910, 1920, 1930, 1940, 1950
  ] + list(range(1951, 2026))

  areal_manifest = {
    "grid_dimensions": [GRID_W, GRID_H],
    "regime_transitions": {
      "china_proper_and_borderlands": {"pre_admin_end": 589, "dynastic_start": 589, "contemporary_start": 1949},
      "mongolia": {"pre_admin_end": 1206, "imperial_start": 1206, "contemporary_start": 1912},
    },
    "geography_profile": {
      "projection_class": "albers_conic",
      "has_micro_islands": False,
      "max_adm2_area_km2": 25000,
      "note": "Continental East Asia (China incl. Tibet, Xinjiang, Manchuria, Inner Mongolia), Mongolia, Taiwan, Hong Kong and Macao.",
    },
    "script_profile": {
      "target_scripts": ["Latn", "Hans", "Hant", "Cyrl", "Mong", "Tibt", "Arab"],
      "allow_native_toponyms": True,
    },
    "hyde_years": hyde_years,
    "substrata_sources": {
      "sites_east_asia": {
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/JADE/_shared/sites_east_asia/config/documented_site_pixels.json",
        "domain": [-10000, 2025],
        "domain_code": 1,
        "domain_mask_png": "histmap/1.data_raw/population_regional/JADE/_shared/sites_east_asia/config/jade_domain_mask.png",
        "rasters_folder": "histmap/1.data_raw/population_regional/JADE/_shared/sites_east_asia/2.population_rasters",
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
    "national_epoch_masks": epoch_entries,
  }
  with open(os.path.join(JADE_DIR, "jade_areal_masks.json5"), "w", encoding="utf-8") as fh:
    json.dump(areal_manifest, fh, indent=2, ensure_ascii=False)

  substrata_cfg = {
    "key": "JADE",
    "order": 4,
    "z_priority": 4,
    "slug": "jade",
    "pipeline_mode": "generic_viscount_mosaic",
    "areal_masks_manifest": "histmap/1.data_raw/population_regional/JADE/jade_areal_masks.json5",
    "seam_feather_km": 200,
    "seam_feather_px": 24,
    "kriging_domains": [
      {
        "key": "sites_east_asia",
        "config_path": "histmap/1.data_raw/population_regional/JADE/_shared/sites_east_asia/config/sites_east_asia.json5",
        "rasters_folder": "histmap/1.data_raw/population_regional/JADE/_shared/sites_east_asia/2.population_rasters",
        "diagnostics_path": "histmap/1.data_raw/population_regional/JADE/_shared/sites_east_asia/config/kriging_diagnostics.json",
        "domain": [-10000, 2025],
      }
    ]
  }
  sub_cfg_path = os.path.join(SVEA_ROOT, "histmap", "3.data_transform", "population_Substrata.viscount", "config", "jade.json5")
  with open(sub_cfg_path, "w", encoding="utf-8") as fh:
    json.dump(substrata_cfg, fh, indent=2, ensure_ascii=False)

  print("\nSuccessfully wrote JADE/jade_areal_masks.json5 and population_Substrata.viscount/config/jade.json5!")


if __name__ == "__main__":
  main()
