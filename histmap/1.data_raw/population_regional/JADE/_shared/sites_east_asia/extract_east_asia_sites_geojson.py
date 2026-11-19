"""Stage C Multi-Repository Archaeological & Historical Site Composite Extractor for Project JADE.

Builds the 4320x2160 JADE domain land mask (China, Mongolia, Taiwan, Hong Kong, Macao),
discretises JADE + a 300 km cross-frontier conditioning belt into HydroBASINS Level 6
watershed catchments, ingests and deduplicates 10 primary archaeological/historical
repositories across 10 Holocene-to-Imperial horizons (-10000 to 1911 AD), applies
monument-class weighting and biome/aridity-conditioned Q75 + IQR taphonomic shrinkage,
and exports ViscountMaternKriging-ready GeoJSONs and configuration manifests.
"""

import csv
import io
import json
import math
import os
import re
import zipfile
from collections import Counter, defaultdict

import numpy as np
import openpyxl
import pandas as pd
import shapefile
from PIL import Image
from scipy.spatial import cKDTree
from shapely.geometry import Point, shape
from shapely.prepared import prep

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
JADE_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE")
DOMAIN_DIR = os.path.join(JADE_DIR, "_shared", "sites_east_asia")
RAW_DIR = os.path.join(DOMAIN_DIR, "0.raw_data")
GIS_DIR = os.path.join(JADE_DIR, "_shared", "_gis_cache")
CFG_DIR = os.path.join(DOMAIN_DIR, "config")
GJ_DIR = os.path.join(DOMAIN_DIR, "geojson")

os.makedirs(CFG_DIR, exist_ok=True)
os.makedirs(GJ_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160
EARTH_R_KM = 6371.0

# 10 Chronological Horizons calibrated to East Asian & Mongolian prehistory and dynastic history
PERIODS = [
  {
    "epoch_id": 1, "key": "palaeolithic_early_neolithic",
    "filename": "01_palaeolithic_early_neolithic_h1.png",
    "geojson_filename": "01_palaeolithic_early_neolithic_h1.geojson",
    "approx_start_year": -13000, "approx_end_year": -5000, "representative_year": -7500,
    "name_en": "Late Palaeolithic and Early Neolithic",
    "name_de": "Spätpaläolithikum und Frühneolithikum",
    "name_fr": "Paléolithique final et Néolithique ancien",
    "date_range_en": "c. 13000-5000BC (Nanzhuangtou, Pengtoushan, Peiligang, Cishan, Xinglongwa and Early Mongolian Neolithic)"
  },
  {
    "epoch_id": 2, "key": "middle_neolithic_yangshao",
    "filename": "02_middle_neolithic_yangshao_h2.png",
    "geojson_filename": "02_middle_neolithic_yangshao_h2.geojson",
    "approx_start_year": -5000, "approx_end_year": -3000, "representative_year": -4000,
    "name_en": "Middle Neolithic (Yangshao and Hemudu)",
    "name_de": "Mittelneolithikum (Yangshao und Hemudu)",
    "name_fr": "Néolithique moyen (Yangshao et Hemudu)",
    "date_range_en": "c. 5000-3000BC (Yangshao, Hemudu, Dawenkou, Hongshan, Daxi, Dabenkeng and Tamsagbulag)"
  },
  {
    "epoch_id": 3, "key": "late_neolithic_longshan",
    "filename": "03_late_neolithic_longshan_h3.png",
    "geojson_filename": "03_late_neolithic_longshan_h3.geojson",
    "approx_start_year": -3000, "approx_end_year": -2000, "representative_year": -2500,
    "name_en": "Late Neolithic (Longshan and Liangzhu)",
    "name_de": "Spätneolithikum (Longshan und Liangzhu)",
    "name_fr": "Néolithique récent (Longshan et Liangzhu)",
    "date_range_en": "c. 3000-2000BC (Longshan, Liangzhu, Shijiahe, Majiayao, Qijia, Karuo and Afanasievo-Chemurchek)"
  },
  {
    "epoch_id": 4, "key": "bronze_age_shang_zhou",
    "filename": "04_bronze_age_shang_zhou_h4.png",
    "geojson_filename": "04_bronze_age_shang_zhou_h4.geojson",
    "approx_start_year": -2000, "approx_end_year": -770, "representative_year": -1300,
    "name_en": "Bronze Age (Erlitou, Shang and Western Zhou)",
    "name_de": "Bronzezeit (Erlitou, Shang und Westliche Zhou)",
    "name_fr": "Âge du Bronze (Erlitou, Shang et Zhou occidentaux)",
    "date_range_en": "c. 2000-770BC (Erlitou, Shang, Western Zhou, Sanxingdui, Lower Xiajiadian and Deer Stone-Khirigsuur)"
  },
  {
    "epoch_id": 5, "key": "spring_autumn_warring_states",
    "filename": "05_spring_autumn_warring_states_h5.png",
    "geojson_filename": "05_spring_autumn_warring_states_h5.geojson",
    "approx_start_year": -770, "approx_end_year": -221, "representative_year": -450,
    "name_en": "Spring and Autumn to Warring States",
    "name_de": "Frühlings- und Herbst- bis Streitende Reiche",
    "name_fr": "Printemps et Automnes aux Royaumes combattants",
    "date_range_en": "c. 770-221BC (Eastern Zhou walled states, early iron agriculture, Slab Burial and Chandman-Pazyryk)"
  },
  {
    "epoch_id": 6, "key": "qin_han_xiongnu",
    "filename": "06_qin_han_xiongnu_h6.png",
    "geojson_filename": "06_qin_han_xiongnu_h6.geojson",
    "approx_start_year": -221, "approx_end_year": 220, "representative_year": 2,
    "name_en": "Qin, Han and Xiongnu Horizon",
    "name_de": "Qin-, Han- und Xiongnu-Horizont",
    "name_fr": "Horizon Qin, Han et Xiongnu",
    "date_range_en": "221BC-220AD (Qin-Han commanderies and counties, Xiongnu Empire and Tarim Basin oases)"
  },
  {
    "epoch_id": 7, "key": "wei_jin_northern_southern",
    "filename": "07_wei_jin_northern_southern_h7.png",
    "geojson_filename": "07_wei_jin_northern_southern_h7.geojson",
    "approx_start_year": 220, "approx_end_year": 589, "representative_year": 400,
    "name_en": "Wei, Jin and Northern-Southern Dynasties",
    "name_de": "Wei-, Jin- und Südliche-Nördliche Dynastien",
    "name_fr": "Wei, Jin et Dynasties du Nord et du Sud",
    "date_range_en": "220-589AD (Three Kingdoms, Jin, Sixteen Kingdoms, Xianbei, Rouran and Jiangnan expansion)"
  },
  {
    "epoch_id": 8, "key": "sui_tang_five_dynasties",
    "filename": "08_sui_tang_five_dynasties_h8.png",
    "geojson_filename": "08_sui_tang_five_dynasties_h8.geojson",
    "approx_start_year": 589, "approx_end_year": 960, "representative_year": 750,
    "name_en": "Sui, Tang and Five Dynasties",
    "name_de": "Sui-, Tang- und Fünf-Dynastien-Zeit",
    "name_fr": "Sui, Tang et Cinq Dynasties",
    "date_range_en": "589-960AD (Sui-Tang Ten Circuits, Göktürk and Uyghur Khaganates, Tibetan Empire and Nanzhao)"
  },
  {
    "epoch_id": 9, "key": "liao_song_jin_yuan",
    "filename": "09_liao_song_jin_yuan_h9.png",
    "geojson_filename": "09_liao_song_jin_yuan_h9.geojson",
    "approx_start_year": 960, "approx_end_year": 1368, "representative_year": 1150,
    "name_en": "Liao, Song, Jin and Yuan",
    "name_de": "Liao-, Song-, Jin- und Yuan-Zeit",
    "name_fr": "Liao, Song, Jin et Yuan",
    "date_range_en": "960-1368AD (Northern and Southern Song, Liao, Western Xia, Jin, Dali and Mongol-Yuan Empire)"
  },
  {
    "epoch_id": 10, "key": "ming_qing_imperial",
    "filename": "10_ming_qing_imperial_h10.png",
    "geojson_filename": "10_ming_qing_imperial_h10.geojson",
    "approx_start_year": 1368, "approx_end_year": 1911, "representative_year": 1750,
    "name_en": "Ming and Qing Imperial Era",
    "name_de": "Ming- und Qing-Kaiserzeit",
    "name_fr": "Époque impériale Ming et Qing",
    "date_range_en": "1368-1911AD (Ming-Qing prefectural and county network, Khalkha banners, Taiwan and Manchurian frontier)"
  }
]

PERIOD_KEYS = [p["key"] for p in PERIODS]


def latlon_to_rc(lat, lon):
  r = min(GRID_H - 1, max(0, int((90.0 - lat) * GRID_H / 180.0)))
  c = min(GRID_W - 1, max(0, int((lon + 180.0) * GRID_W / 360.0)))
  return r, c


def latlon_to_xyz(lat, lon):
  lr = math.radians(lat)
  nr = math.radians(lon)
  cl = math.cos(lr)
  return (cl * math.cos(nr), cl * math.sin(nr), math.sin(lr))


def assign_periods_by_span(start_yr, end_yr):
  """Returns list of (period_key, overlap_weight) for a calendar year interval [start_yr, end_yr]."""
  if start_yr is None or end_yr is None:
    return []
  if start_yr > end_yr:
    start_yr, end_yr = end_yr, start_yr
  if end_yr < -13000 or start_yr > 1920:
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
    # Clamp single-point outliers just outside edges
    mid = 0.5 * (start_yr + end_yr)
    if mid < -13000:
      return [(PERIODS[0]["key"], 1.0)]
    if mid > 1911 and mid <= 1950:
      return [(PERIODS[-1]["key"], 1.0)]
    return []
  tot = sum(w for _, w in hits)
  return [(k, w / tot) for k, w in hits]


def build_jade_domain_mask():
  """Builds 4320x2160 JADE land mask from admin_modern/geocodes.png (CHN, HKG, MNG, TWN + Macao)."""
  geo_path = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "admin_modern", "geocodes.png")
  la_path = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
  geo = np.asarray(Image.open(geo_path).convert("RGBA"), dtype=np.uint8)
  la_raw = np.asarray(Image.open(la_path).convert("RGBA"), dtype=np.uint8)
  la = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2])

  # CHN (173,62,62), HKG (124,163,170), MNG (206,137,91), TWN (45,68,99)
  target_rgbs = [(173, 62, 62), (124, 163, 170), (206, 137, 91), (45, 68, 99)]
  mask = np.zeros((GRID_H, GRID_W), dtype=bool)
  for r, g, b in target_rgbs:
    mask |= (geo[:, :, 3] > 0) & (geo[:, :, 0] == r) & (geo[:, :, 1] == g) & (geo[:, :, 2] == b)

  # Ensure Macao & coastal islets (e.g. Zhoushan, Kinmen, Matsu, Penghu, Hainan) within land_area > 0 are included
  # Macao pixel: 22.19 N, 113.54 E
  mr, mc = latlon_to_rc(22.19, 113.54)
  if la[mr, mc] > 0:
    mask[mr, mc] = True

  mask &= (la > 0)

  # Save RGBA mask PNG (white where valid, transparent elsewhere)
  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  rgba[mask] = [255, 255, 255, 255]
  out_png = os.path.join(CFG_DIR, "jade_domain_mask.png")
  Image.fromarray(rgba, mode="RGBA").save(out_png)
  rs, cs = np.where(mask)
  print(f"[A] Built jade_domain_mask.png: {int(mask.sum()):,} land pixels | rows {rs.min()}..{rs.max()}, cols {cs.min()}..{cs.max()} | area={float(la[mask].sum()):,.0f} km²")
  return mask, la


def build_catchments(domain_mask, land_area):
  """Builds scale-adaptive HydroBASINS Level 6 catchments inside JADE + 300 km cross-frontier belt."""
  from scipy.ndimage import distance_transform_edt

  # Compute approximate pixel distance outside domain mask (~300 km ~ 36-45 px at mid-latitudes)
  # Use 48 px dilation for candidate search, then verify geodesic distance <= 320 km
  dist_px = distance_transform_edt(~domain_mask)
  in_frontier_band = (~domain_mask) & (dist_px <= 48.0) & (land_area > 0)

  # Load HydroBASINS Asia Level 6
  hyb_zip = os.path.join(GIS_DIR, "hybas_as_lev06_v1c.zip")
  catchments = []
  with zipfile.ZipFile(hyb_zip) as zf:
    sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
    fields = [f[0] for f in sf.fields[1:]]
    idx_id = fields.index("HYBAS_ID")
    idx_area = fields.index("SUB_AREA")

    for sr in sf.iterShapeRecords():
      bb = sr.shape.bbox
      # Broad East Asia + 300 km bbox
      if bb[2] < 69.0 or bb[0] > 141.0 or bb[3] < 15.0 or bb[1] > 57.5:
        continue
      geom = shape(sr.shape.__geo_interface__)
      if geom.is_empty:
        continue
      rep = geom.representative_point()
      lon, lat = float(rep.x), float(rep.y)
      area_km2 = max(150.0, float(sr.record[idx_area] or 1000.0))
      r_c, c_c = latlon_to_rc(lat, lon)

      # Sample polygon vertices + centroid to test domestic vs frontier
      is_dom = bool(domain_mask[r_c, c_c])
      is_fr = bool(in_frontier_band[r_c, c_c])
      if not is_dom and not is_fr:
        # Check bbox corners / sample points inside polygon
        p_geom = prep(geom)
        r0, c0 = latlon_to_rc(bb[3], bb[0])
        r1, c1 = latlon_to_rc(bb[1], bb[2])
        sub_dom = domain_mask[r0:r1 + 1, c0:c1 + 1]
        if sub_dom.any():
          # Verify at least one domestic pixel actually falls inside geom
          drs, dcs = np.where(sub_dom)
          step = max(1, len(drs) // 25)
          for k in range(0, len(drs), step):
            plat = 90.0 - (r0 + drs[k] + 0.5) * 180.0 / GRID_H
            plon = -180.0 + (c0 + dcs[k] + 0.5) * 360.0 / GRID_W
            if p_geom.contains(Point(plon, plat)):
              is_dom = True
              lat, lon = plat, plon
              break
        if not is_dom:
          sub_fr = in_frontier_band[r0:r1 + 1, c0:c1 + 1]
          if sub_fr.any():
            is_fr = True

      if not is_dom and not is_fr:
        continue

      # Split mega-basins (> 25,000 km2) into sub-catchment grid cells (~1.5 deg) so vast arid/plateau basins stay scale-adaptive
      if area_km2 > 25000.0:
        p_geom = prep(geom)
        lat_steps = np.arange(math.floor(bb[1]) + 0.75, bb[3], 1.5)
        lon_steps = np.arange(math.floor(bb[0]) + 0.75, bb[2], 1.5)
        sub_pts = []
        for la_s in lat_steps:
          for lo_s in lon_steps:
            if p_geom.contains(Point(lo_s, la_s)):
              rr, cc = latlon_to_rc(la_s, lo_s)
              if domain_mask[rr, cc] or in_frontier_band[rr, cc]:
                sub_pts.append((la_s, lo_s, bool(domain_mask[rr, cc])))
        if len(sub_pts) >= 2:
          sub_area = area_km2 / len(sub_pts)
          for j, (la_s, lo_s, sub_dom_flag) in enumerate(sub_pts):
            catchments.append({
              "region_id": f"hyb_{sr.record[idx_id]}_s{j}",
              "lat": la_s,
              "lon": lo_s,
              "area_km2": round(sub_area, 1),
              "is_frontier_buffer": not sub_dom_flag,
              "xyz": latlon_to_xyz(la_s, lo_s),
            })
          continue

      catchments.append({
        "region_id": f"hyb_{sr.record[idx_id]}",
        "lat": lat,
        "lon": lon,
        "area_km2": round(area_km2, 1),
        "is_frontier_buffer": not is_dom,
        "xyz": latlon_to_xyz(lat, lon),
      })

  # Add dedicated island/archipelago catchments for Taiwan, Hainan, Hong Kong/Macao, Zhoushan if sparse
  extra_anchors = [
    ("tw_north", 25.05, 121.52, 4200.0),
    ("tw_west_central", 24.15, 120.68, 6500.0),
    ("tw_southwest", 23.00, 120.22, 6800.0),
    ("tw_south", 22.45, 120.60, 4500.0),
    ("tw_east_hualien", 23.98, 121.58, 5200.0),
    ("tw_east_taitung", 22.76, 121.14, 4800.0),
    ("hainan_north", 19.90, 110.30, 11000.0),
    ("hainan_south", 18.60, 109.50, 12000.0),
    ("hainan_west", 19.35, 109.05, 11000.0),
    ("hk_macao_pearl_estuary", 22.30, 114.05, 2200.0),
  ]
  existing_xyz = np.array([c["xyz"] for c in catchments])
  tree_init = cKDTree(existing_xyz)
  for rid, la_e, lo_e, ar_e in extra_anchors:
    d, _ = tree_init.query(latlon_to_xyz(la_e, lo_e))
    if d * EARTH_R_KM > 35.0:
      catchments.append({
        "region_id": rid, "lat": la_e, "lon": lo_e, "area_km2": ar_e,
        "is_frontier_buffer": False, "xyz": latlon_to_xyz(la_e, lo_e)
      })

  n_dom = sum(1 for c in catchments if not c["is_frontier_buffer"])
  n_fr = sum(1 for c in catchments if c["is_frontier_buffer"])
  print(f"[B] Built {len(catchments)} HydroBASINS catchments ({n_dom} domestic, {n_fr} cross-frontier buffer)")
  return catchments


def parse_relics_era(era_str):
  """Maps Chinese National Key Cultural Relics dynasty string to calendar year intervals."""
  if not era_str:
    return []
  s = str(era_str)
  # Explicit dynasty mappings (inclusive spans)
  dyn_spans = [
    ("旧石器", -13000, -8000),
    ("新石器", -7500, -2000),
    ("夏", -2070, -1600),
    ("商", -1600, -1046),
    ("西周", -1046, -771),
    ("东周", -770, -256),
    ("春秋", -770, -476),
    ("战国", -475, -221),
    ("周", -1046, -256),
    ("先秦", -3000, -221),
    ("秦", -221, -206),
    ("西汉", -202, 8),
    ("东汉", 25, 220),
    ("汉", -202, 220),
    ("三国", 220, 280),
    ("西晋", 266, 316),
    ("东晋", 317, 420),
    ("晋", 266, 420),
    ("十六国", 304, 439),
    ("南北朝", 420, 589),
    ("北魏", 386, 534),
    ("北齐", 550, 577),
    ("北周", 557, 581),
    ("魏晋", 220, 420),
    ("南朝", 420, 589),
    ("北朝", 386, 581),
    ("隋", 581, 618),
    ("唐", 618, 907),
    ("五代", 907, 960),
    ("十国", 907, 979),
    ("北宋", 960, 1127),
    ("南宋", 1127, 1279),
    ("宋", 960, 1279),
    ("辽", 916, 1125),
    ("西夏", 1038, 1227),
    ("金", 1115, 1234),
    ("大理", 937, 1253),
    ("吐蕃", 618, 842),
    ("元", 1271, 1368),
    ("明", 1368, 1644),
    ("清", 1644, 1911),
  ]
  matched = []
  # Check range syntax like "明至清", "唐至宋", "汉至唐"
  if "至" in s:
    parts = s.split("至", 1)
    s0 = None
    e0 = None
    for tok, a, b in dyn_spans:
      if tok in parts[0] and s0 is None:
        s0 = a
      if tok in parts[1] and e0 is None:
        e0 = b
    if s0 is not None and e0 is not None:
      return assign_periods_by_span(s0, e0)

  for tok, a, b in dyn_spans:
    if tok in s:
      # Avoid matching '周' if '西周'/'东周' already matched, or '汉' if '西汉'/'东汉'
      if tok == "周" and ("西周" in s or "东周" in s or "北周" in s):
        continue
      if tok == "汉" and ("西汉" in s or "东汉" in s):
        continue
      if tok == "宋" and ("北宋" in s or "南宋" in s):
        continue
      if tok == "晋" and ("西晋" in s or "东晋" in s or "魏晋" in s):
        continue
      matched.extend(assign_periods_by_span(a, b))
  if not matched:
    return []
  agg = defaultdict(float)
  for k, w in matched:
    agg[k] += w
  tot = sum(agg.values())
  return [(k, v / tot) for k, v in agg.items()]


def ingest_all_repositories():
  """Ingests all 10 archaeological and historical repositories into a unified list of site records.

  Each record: (lat, lon, weight, period_weights_list, source_tag, is_settlement_flag, max_pop)
  """
  records = []
  source_stats = Counter()

  # Deduplication cache for radiocarbon / ancient DNA point sites (rounded 0.02 deg + period)
  c14_seen = set()

  def add_c14_point(lat, lon, cal_yr, src_tag, weight=1.0):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
      return
    if not (68.0 <= lon <= 142.0 and 14.0 <= lat <= 58.0):
      return
    pw = assign_periods_by_span(cal_yr, cal_yr)
    if not pw:
      return
    pkey = pw[0][0]
    dedup_key = (round(lat * 50), round(lon * 50), pkey)
    if dedup_key in c14_seen:
      return
    c14_seen.add(dedup_key)
    records.append((lat, lon, weight, pw, src_tag, False, 0))
    source_stats[src_tag] += 1

  # --- SOURCE 1: Hosner et al. (2016) PANGAEA (51,432 Chinese Neolithic & Bronze Age sites) ---
  hosner_path = os.path.join(RAW_DIR, "hosner_2016_china_neolithic_bronze.tab")
  with open(hosner_path, "r", encoding="utf-8", errors="replace") as fh:
    for line in fh:
      if line.startswith("*/"):
        break
    df_h = pd.read_csv(fh, sep="\t", low_memory=False)
  for row in df_h.itertuples(index=False):
    try:
      lon = float(row.Longitude)
      lat = float(row.Latitude)
      age_max = float(getattr(row, "_6", np.nan))  # Age max [ka]
      age_min = float(getattr(row, "_7", np.nan))  # Age dated min [ka]
      age_mid = float(getattr(row, "_8", np.nan))  # Age [ka BP]
    except Exception:
      continue
    if not (math.isfinite(lon) and math.isfinite(lat)):
      continue
    if math.isfinite(age_max) and math.isfinite(age_min):
      s_yr = 1950.0 - age_max * 1000.0
      e_yr = 1950.0 - age_min * 1000.0
    elif math.isfinite(age_mid):
      s_yr = e_yr = 1950.0 - age_mid * 1000.0
    else:
      continue
    pw = assign_periods_by_span(s_yr, e_yr)
    if not pw:
      continue
    cult = str(getattr(row, "_5", "")).lower()
    # Slight hierarchy boost for named urban/walled/capital cultures vs undistinguished scatters
    wt = 1.0
    if "undistinguished" in cult:
      wt = 0.85
    elif any(k in cult for k in ["erlitou", "shang", "zhou", "longshan", "liangzhu", "yangshao", "zhanguo", "chunqiu", "sanxingdui", "shijiahe"]):
      wt = 1.15
    records.append((lat, lon, wt, pw, "hosner_2016_pangaea", True, 0))
    source_stats["hosner_2016_pangaea"] += 1

  # --- SOURCE 2: China National Key Cultural Relics (RelicsAtlas, 5,060 sites) ---
  ra_path = os.path.join(RAW_DIR, "cn_relicsatlas_heritage_sites.json")
  ra_data = json.load(open(ra_path, "r", encoding="utf-8"))
  for item in ra_data:
    lon = item.get("longitude")
    lat = item.get("latitude")
    if lon is None or lat is None:
      continue
    try:
      lon, lat = float(lon), float(lat)
    except Exception:
      continue
    rtype = str(item.get("type") or "")
    if "近现代" in rtype:
      continue
    pw = parse_relics_era(item.get("era", ""))
    if not pw:
      continue
    # Settlement-hierarchy weighting: Ancient Sites (古遗址) & Ancient Architecture (古建筑) weighted above tombs/caves
    name = str(item.get("name") or "")
    if rtype == "古遗址":
      wt = 2.0 if any(k in name for k in ["故城", "古城", "城址", "都城", "遗址"]) else 1.5
      is_sett = True
    elif rtype == "古建筑":
      wt = 1.1
      is_sett = True
    elif rtype == "古墓葬":
      wt = 0.6  # Downweight durable funerary monument bias
      is_sett = False
    else:
      wt = 0.5
      is_sett = False
    records.append((lat, lon, wt, pw, "cn_national_key_relics", is_sett, 0))
    source_stats["cn_national_key_relics"] += 1

  # --- SOURCE 3: Harvard CHGIS v6 Time Series Prefectures & Counties (221 BC - 1911 AD) ---
  for zname, base_wt, is_pref in [
    ("chgis_v6_pref_pts_v6_time_pref_pts_utf_wgs84.zip", 2.5, True),
    ("chgis_v6_cnty_pts_v6_time_cnty_pts_utf_wgs84.zip", 1.2, False),
  ]:
    zp = os.path.join(GIS_DIR, zname)
    with zipfile.ZipFile(zp) as zf:
      sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
      sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
      fields = [f[0] for f in sf.fields[1:]]
      ix, iy = fields.index("X_COOR"), fields.index("Y_COOR")
      ib, ie = fields.index("BEG_YR"), fields.index("END_YR")
      # Deduplicate administrative seat renames within same (0.05 deg, horizon)
      chgis_seen = set()
      for rec in sf.iterRecords():
        try:
          lon, lat = float(rec[ix]), float(rec[iy])
          byr, eyr = int(rec[ib]), int(rec[ie])
        except Exception:
          continue
        if not (68.0 <= lon <= 142.0 and 14.0 <= lat <= 58.0):
          continue
        if byr == 0 and eyr == 0:
          continue
        if byr < -221:
          byr = -221
        if eyr > 1911:
          eyr = 1911
        # Assign to EVERY imperial horizon where this seat existed (weight = 1.0 per active horizon)
        for p in PERIODS[5:]:  # Horizons 6..10 (-221 to 1911)
          ps, pe = p["approx_start_year"], p["approx_end_year"]
          if min(eyr, pe) >= max(byr, ps):
            dkey = (round(lat * 20), round(lon * 20), p["key"], is_pref)
            if dkey not in chgis_seen:
              chgis_seen.add(dkey)
              records.append((lat, lon, base_wt, [(p["key"], 1.0)], "chgis_v6_time_series", True, 5000 if is_pref else 1000))
              source_stats["chgis_v6_time_series"] += 1

  # --- SOURCE 4: Harvard CHGIS v6 1820 Town Points (8,659 Qing towns) ---
  twn_zip = os.path.join(GIS_DIR, "chgis_v6_1820_utf8_v6_1820_twn_pts_utf.zip")
  with zipfile.ZipFile(twn_zip) as zf:
    sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
    fields = [f[0] for f in sf.fields[1:]]
    ix, iy = fields.index("X_COORD"), fields.index("Y_COORD")
    twn_seen = set()
    for rec in sf.iterRecords():
      try:
        lon, lat = float(rec[ix]), float(rec[iy])
      except Exception:
        continue
      if not (68.0 <= lon <= 142.0 and 14.0 <= lat <= 58.0):
        continue
      dkey = (round(lat * 25), round(lon * 25))
      if dkey not in twn_seen:
        twn_seen.add(dkey)
        records.append((lat, lon, 0.75, [("ming_qing_imperial", 1.0)], "chgis_v6_1820_towns", True, 500))
        source_stats["chgis_v6_1820_towns"] += 1

  # --- SOURCE 5: Allen Ancient DNA Resource v66.p1 (AADR: Mongolia 134 sites + China/Tibet/Taiwan + Frontier) ---
  aadr_path = os.path.join(RAW_DIR, "aadr_v66.p1_HO.aadr.PUB.anno")
  df_a = pd.read_csv(aadr_path, sep="\t", low_memory=False)
  lat_c = [c for c in df_a.columns if "lat" in c.lower()][0]
  lon_c = [c for c in df_a.columns if "long" in c.lower()][0]
  date_c = [c for c in df_a.columns if "date mean" in c.lower()][0]
  for row in df_a[[lat_c, lon_c, date_c]].itertuples(index=False):
    try:
      lat, lon, bp = float(row[0]), float(row[1]), float(row[2])
    except Exception:
      continue
    if math.isfinite(lat) and math.isfinite(lon) and math.isfinite(bp) and bp > 0:
      add_c14_point(lat, lon, 1950.0 - bp, "aadr_v66", weight=1.35)

  # --- SOURCE 6: XRONOS Radiocarbon API (CN, MN, TW, RU, KZ, IN) ---
  for fn in sorted(os.listdir(RAW_DIR)):
    if fn.startswith("xronos_") and fn.endswith(".json"):
      try:
        arr = json.loads(open(os.path.join(RAW_DIR, fn), "r", encoding="utf-8").read())
      except Exception:
        continue
      if not isinstance(arr, list):
        continue
      for row in arr:
        m = row.get("measurement") if isinstance(row, dict) and isinstance(row.get("measurement"), dict) else row
        if not isinstance(m, dict):
          continue
        try:
          lat = float(m.get("lat"))
          lon = float(m.get("lng"))
          bp = float(m.get("bp"))
        except Exception:
          continue
        if math.isfinite(lat) and math.isfinite(lon) and math.isfinite(bp) and 0 < bp < 16000:
          add_c14_point(lat, lon, 1950.0 - bp, "xronos_c14", weight=1.1)

  # --- SOURCE 7: p3k14c 2025 + SVEA c14_cleaned_dedup.csv ---
  p3k_path = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CENTAUR", "_shared", "sites_northern_america", "raw_sources", "people3k_RawP3Kc14_2025.csv")
  if os.path.exists(p3k_path):
    df_p3 = pd.read_csv(p3k_path, usecols=["Latitude", "Longitude", "Age"], low_memory=False)
    for row in df_p3.itertuples(index=False):
      try:
        lat, lon, bp = float(row.Latitude), float(row.Longitude), float(row.Age)
      except Exception:
        continue
      if math.isfinite(lat) and math.isfinite(lon) and math.isfinite(bp) and 0 < bp < 16000:
        add_c14_point(lat, lon, 1950.0 - bp, "p3k14c_2025", weight=1.0)

  c14_path = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_c14bazAAR", "c14_cleaned_dedup.csv")
  if os.path.exists(c14_path):
    df_c14 = pd.read_csv(c14_path, usecols=["lat", "lon", "c14age"], low_memory=False)
    for row in df_c14.itertuples(index=False):
      try:
        lat, lon, bp = float(row.lat), float(row.lon), float(row.c14age)
      except Exception:
        continue
      if math.isfinite(lat) and math.isfinite(lon) and math.isfinite(bp) and 0 < bp < 16000:
        add_c14_point(lat, lon, 1950.0 - bp, "c14bazAAR_dedup", weight=1.0)

  # --- SOURCE 8: Archaeological Atlas of Published Excavations (DVN/7MYVV7, 10,439 East Asia & Mongolia sites) ---
  kmz_path = os.path.join(RAW_DIR, "arch_atlas_excavations_2020.kmz")
  if os.path.exists(kmz_path):
    with zipfile.ZipFile(kmz_path) as zf:
      kml_name = [n for n in zf.namelist() if n.endswith(".kml")][0]
      raw_kml = zf.read(kml_name).decode("utf-8", errors="replace")
    # Parse Placemarks cleanly via regex for name/description/coordinates
    pms = re.findall(r"<Placemark>(.*?)</Placemark>", raw_kml, re.S)
    atlas_seen = set()
    for pm in pms:
      cm = re.search(r"<coordinates>\s*([+-]?\d+\.?\d*),\s*([+-]?\d+\.?\d*)", pm)
      if not cm:
        continue
      lon, lat = float(cm.group(1)), float(cm.group(2))
      if not (68.0 <= lon <= 142.0 and 14.0 <= lat <= 58.0):
        continue
      low = pm.lower()
      # Infer chronological horizon from published excavation text
      matched_h = []
      if any(k in low for k in ["paleolith", "palaeolith", "mesolith", "early neolith", "pleistocene"]):
        matched_h.append(("palaeolithic_early_neolithic", 1.0))
      if any(k in low for k in ["yangshao", "hemudu", "hongshan", "dawenkou", "middle neolith", "neolith"]):
        matched_h.append(("middle_neolithic_yangshao", 0.7))
        matched_h.append(("late_neolithic_longshan", 0.7))
      if any(k in low for k in ["longshan", "liangzhu", "majiayao", "qijia", "late neolith", "chalcolith", "eneolith"]):
        matched_h.append(("late_neolithic_longshan", 1.0))
      if any(k in low for k in ["bronze", "shang", "erlitou", "western zhou", "khirigsuur", "deer stone", "karasuk", "andronovo", "afanasievo", "slab burial"]):
        matched_h.append(("bronze_age_shang_zhou", 1.0))
      if any(k in low for k in ["warring", "spring and autumn", "eastern zhou", "iron age", "scyth", "pazyryk", "saka"]):
        matched_h.append(("spring_autumn_warring_states", 1.0))
      if any(k in low for k in ["qin", "han", "xiongnu", "silk road"]):
        matched_h.append(("qin_han_xiongnu", 1.0))
      if any(k in low for k in ["wei", "jin", "sixteen", "northern", "southern", "xianbei", "rouran", "koguryo"]):
        matched_h.append(("wei_jin_northern_southern", 1.0))
      if any(k in low for k in ["sui", "tang", "turk", "uyghur", "uighur", "tibet", "tubo", "bohai", "nanzhao"]):
        matched_h.append(("sui_tang_five_dynasties", 1.0))
      if any(k in low for k in ["song", "liao", "khitan", "jurchen", "yuan", "mongol", "karakorum", "xixia", "tangut", "medieval"]):
        matched_h.append(("liao_song_jin_yuan", 1.0))
      if any(k in low for k in ["ming", "qing", "post-medieval", "historical"]):
        matched_h.append(("ming_qing_imperial", 1.0))
      if not matched_h:
        # Undated published excavation -> weight gently across Bronze-to-Medieval prehistoric/early-historic span
        # Only retain in sparse frontier/Mongolia/Tibet/Xinjiang/Taiwan zones to prevent undated leakage in well-covered China Proper
        if lat > 41.0 or lon < 103.0 or (lon > 119.5 and lat < 25.5):
          matched_h = [
            ("bronze_age_shang_zhou", 0.25),
            ("spring_autumn_warring_states", 0.25),
            ("qin_han_xiongnu", 0.25),
            ("liao_song_jin_yuan", 0.25),
          ]
        else:
          continue
      agg = defaultdict(float)
      for k, w in matched_h:
        agg[k] += w
      tot = sum(agg.values())
      pw = [(k, v / tot) for k, v in agg.items()]
      dkey = (round(lat * 40), round(lon * 40), pw[0][0])
      if dkey in atlas_seen:
        continue
      atlas_seen.add(dkey)
      records.append((lat, lon, 1.0, pw, "arch_atlas_excavations", True, 0))
      source_stats["arch_atlas_excavations"] += 1

  # --- SOURCE 9: Taiwan Archaeological & Cultural Heritage Sites (HeritageMapTW / BOCH) ---
  tw_files = [
    ("tw_heritage_a_11.js", [("middle_neolithic_yangshao", 0.25), ("late_neolithic_longshan", 0.35), ("bronze_age_shang_zhou", 0.25), ("qin_han_xiongnu", 0.15)], 1.6),
    ("tw_heritage_a_12.js", [("middle_neolithic_yangshao", 0.25), ("late_neolithic_longshan", 0.35), ("bronze_age_shang_zhou", 0.25), ("qin_han_xiongnu", 0.15)], 2.2),
    ("tw_heritage_a_16.js", [("ming_qing_imperial", 1.0)], 1.2),
    ("tw_heritage_a_20.js", [("ming_qing_imperial", 1.0)], 0.8),
    ("tw_heritage_a_21.js", [("ming_qing_imperial", 1.0)], 1.2),
  ]
  for fn, pw, wt in tw_files:
    fp = os.path.join(RAW_DIR, fn)
    if not os.path.exists(fp):
      continue
    txt = open(fp, "r", encoding="utf-8", errors="replace").read()
    m = re.search(r"=\s*(\{.*\})\s*;?\s*$", txt, re.S)
    if not m:
      continue
    gj = json.loads(m.group(1))
    for feat in gj.get("features", []):
      geom = feat.get("geometry") or {}
      coords = geom.get("coordinates")
      if not coords:
        continue
      if geom.get("type") == "Point":
        lon, lat = float(coords[0]), float(coords[1])
      else:
        try:
          pt = shape(geom).representative_point()
          lon, lat = float(pt.x), float(pt.y)
        except Exception:
          continue
      if 118.0 <= lon <= 123.0 and 21.5 <= lat <= 26.5:
        records.append((lat, lon, wt, pw, "taiwan_boch_heritage", True, 0))
        source_stats["taiwan_boch_heritage"] += 1

  # --- SOURCE 10: Kham (Eastern Tibetan Plateau) Monasteries + POLARIS IA RAS Siberian Frontier Belt ---
  kham_xlsx = os.path.join(RAW_DIR, "kham_tibet_regional_Kham_Monasteries_version1.xlsx")
  if os.path.exists(kham_xlsx):
    wb = openpyxl.load_workbook(kham_xlsx, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if rows:
      hdr = [str(x or "").strip().lower() for x in rows[0]]
      lat_i = next((i for i, h in enumerate(hdr) if "lat" in h or h == "y"), None)
      lon_i = next((i for i, h in enumerate(hdr) if "lon" in h or "lng" in h or h == "x"), None)
      yr_i = next((i for i, h in enumerate(hdr) if "found" in h or "year" in h or "date" in h), None)
      if lat_i is not None and lon_i is not None:
        for r in rows[1:]:
          try:
            lat, lon = float(r[lat_i]), float(r[lon_i])
          except Exception:
            continue
          if not (85.0 <= lon <= 106.0 and 26.0 <= lat <= 36.0):
            continue
          yr_v = None
          if yr_i is not None and r[yr_i] is not None:
            m = re.search(r"(\d{3,4})", str(r[yr_i]))
            if m:
              yr_v = int(m.group(1))
          if yr_v and 600 <= yr_v <= 1911:
            pw = assign_periods_by_span(yr_v, 1911)
          else:
            pw = [("liao_song_jin_yuan", 0.35), ("ming_qing_imperial", 0.65)]
          if pw:
            records.append((lat, lon, 1.0, pw, "kham_tibet_monasteries", True, 0))
            source_stats["kham_tibet_monasteries"] += 1

  # POLARIS IA RAS Siberian cross-frontier sites (north of Mongolia/Manchuria/Xinjiang)
  polaris_gj_dir = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "POLARIS", "_shared", "sites_IA_RAS", "geojson")
  polaris_map = {
    "01_stone_age_e52.geojson": [("palaeolithic_early_neolithic", 0.5), ("middle_neolithic_yangshao", 0.5)],
    "02_eneolithic_e13.geojson": [("late_neolithic_longshan", 1.0)],
    "05_bronze_age_e47.geojson": [("bronze_age_shang_zhou", 1.0)],
    "06_iron_age_e36.geojson": [("spring_autumn_warring_states", 0.5), ("qin_han_xiongnu", 0.5)],
    "08_migration_period_e34.geojson": [("wei_jin_northern_southern", 1.0)],
    "09_middle_ages_e37.geojson": [("sui_tang_five_dynasties", 0.45), ("liao_song_jin_yuan", 0.55)],
    "10_early_modern_17_18c_e3.geojson": [("ming_qing_imperial", 1.0)],
  }
  for fn, pw in polaris_map.items():
    fp = os.path.join(polaris_gj_dir, fn)
    if not os.path.exists(fp):
      continue
    gj = json.load(open(fp, "r", encoding="utf-8"))
    for feat in gj.get("features", []):
      coords = (feat.get("geometry") or {}).get("coordinates") or []
      if len(coords) < 2:
        continue
      lon, lat = float(coords[0]), float(coords[1])
      if 72.0 <= lon <= 140.0 and 42.0 <= lat <= 56.5:
        cnt = max(1.0, float((feat.get("properties") or {}).get("site_count") or 1.0))
        records.append((lat, lon, min(cnt, 25.0), pw, "polaris_ia_ras_frontier", True, 0))
        source_stats["polaris_ia_ras_frontier"] += 1

  # --- SOURCE 11: Documented Mongolian Steppe Archaeological Complexes & Imperial Centres ---
  # Grounded in published Mongolian Academy of Sciences / Honeychurch / Wright / Bemmann / Rogers surveys
  mongolia_arch_sites = [
    # (lat, lon, weight, periods)
    (47.20, 102.84, 5.0, [("sui_tang_five_dynasties", 0.3), ("liao_song_jin_yuan", 0.5), ("ming_qing_imperial", 0.2)]),  # Karakorum / Erdene Zuu
    (47.43, 102.66, 4.5, [("sui_tang_five_dynasties", 0.8), ("liao_song_jin_yuan", 0.2)]),  # Khar Balgas (Ordu-Baliq, Uyghur capital)
    (47.55, 102.84, 3.5, [("sui_tang_five_dynasties", 1.0)]),  # Khoshoo Tsaidam (Bilge Khagan & Kul Tigin)
    (47.80, 109.12, 4.5, [("liao_song_jin_yuan", 0.85), ("ming_qing_imperial", 0.15)]),  # Avraga Ord (Genghis Khan's palace)
    (47.92, 106.92, 4.0, [("qin_han_xiongnu", 0.3), ("liao_song_jin_yuan", 0.3), ("ming_qing_imperial", 0.4)]),  # Tuul Valley / Urga / Ikh Khuree
    (47.74, 107.47, 3.0, [("qin_han_xiongnu", 0.7), ("sui_tang_five_dynasties", 0.3)]),  # Gua Dov & Tonyukuk Monument
    (48.12, 108.45, 3.5, [("qin_han_xiongnu", 1.0)]),  # Tereljiin Dorvoljin (Xiongnu walled city)
    (48.62, 106.48, 3.5, [("qin_han_xiongnu", 1.0)]),  # Noyon Uul (Noin-Ula Xiongnu royal tombs)
    (48.72, 106.28, 3.0, [("qin_han_xiongnu", 1.0)]),  # Boroo Gol Xiongnu settlement
    (49.45, 103.52, 4.0, [("bronze_age_shang_zhou", 0.3), ("spring_autumn_warring_states", 0.3), ("qin_han_xiongnu", 0.4)]),  # Egiin Gol valley survey
    (48.08, 101.25, 4.0, [("bronze_age_shang_zhou", 0.4), ("spring_autumn_warring_states", 0.3), ("qin_han_xiongnu", 0.3)]),  # Khanuy Valley (Khirigsuur & Deer Stones)
    (47.82, 101.95, 3.5, [("qin_han_xiongnu", 1.0)]),  # Gol Mod I & II (Xiongnu elite complex)
    (47.76, 102.50, 3.5, [("liao_song_jin_yuan", 1.0)]),  # Chin Tolgoi Balgas (Khitan Liao walled garrison)
    (47.97, 104.37, 3.5, [("liao_song_jin_yuan", 1.0)]),  # Khar Bukh Balgas (Khitan-Mongol walled town)
    (48.05, 113.35, 3.5, [("liao_song_jin_yuan", 1.0)]),  # Kherlen Bars (Khitan-Liao pagoda & walled city)
    (47.18, 117.30, 3.0, [("palaeolithic_early_neolithic", 0.5), ("middle_neolithic_yangshao", 0.5)]),  # Tamsagbulag Neolithic settlement
    (49.95, 92.10, 3.0, [("bronze_age_shang_zhou", 0.5), ("spring_autumn_warring_states", 0.5)]),  # Ulaangom / Chandman (Pazyryk-Sagly)
    (48.01, 91.64, 3.0, [("bronze_age_shang_zhou", 0.3), ("qin_han_xiongnu", 0.3), ("ming_qing_imperial", 0.4)]),  # Khovd basin / Manchu garrison
    (47.74, 96.84, 3.0, [("bronze_age_shang_zhou", 0.3), ("liao_song_jin_yuan", 0.3), ("ming_qing_imperial", 0.4)]),  # Uliastai / Zavkhan basin
    (48.98, 99.32, 3.5, [("bronze_age_shang_zhou", 0.6), ("spring_autumn_warring_states", 0.4)]),  # Uushigiin Ovör Deer Stone complex (Khövsgöl)
    (46.78, 100.72, 3.0, [("bronze_age_shang_zhou", 0.5), ("qin_han_xiongnu", 0.5)]),  # Bayankhongor / Tuin River
    (45.77, 106.27, 2.5, [("bronze_age_shang_zhou", 0.4), ("qin_han_xiongnu", 0.3), ("liao_song_jin_yuan", 0.3)]),  # Baga Gazryn Chuluu (Dundgovi)
    (44.15, 103.72, 2.5, [("palaeolithic_early_neolithic", 0.4), ("middle_neolithic_yangshao", 0.3), ("qin_han_xiongnu", 0.3)]),  # Bayanzag / Flaming Cliffs & South Gobi oases
    (46.50, 111.30, 3.0, [("bronze_age_shang_zhou", 0.5), ("spring_autumn_warring_states", 0.5)]),  # Ulaanzuukh (Sukhbaatar)
    (48.07, 114.53, 3.0, [("bronze_age_shang_zhou", 0.4), ("liao_song_jin_yuan", 0.4), ("ming_qing_imperial", 0.2)]),  # Choibalsan / Kherlen lower basin
    (49.48, 105.95, 3.0, [("bronze_age_shang_zhou", 0.3), ("qin_han_xiongnu", 0.4), ("ming_qing_imperial", 0.3)]),  # Selenge-Orkhon confluence / Darkhan
    (50.23, 106.21, 3.0, [("qin_han_xiongnu", 0.4), ("ming_qing_imperial", 0.6)]),  # Kyakhta-Altanbulag / Sukhbaatar border
    (46.37, 96.26, 2.5, [("bronze_age_shang_zhou", 0.5), ("qin_han_xiongnu", 0.5)]),  # Govi-Altai / Altai foothill valleys
    (48.97, 89.96, 2.5, [("bronze_age_shang_zhou", 0.5), ("spring_autumn_warring_states", 0.5)]),  # Bayan-Ölgii / Altai petroglyph & kurgan complexes
    (47.32, 110.65, 3.0, [("bronze_age_shang_zhou", 0.3), ("liao_song_jin_yuan", 0.5), ("ming_qing_imperial", 0.2)]),  # Undurkhaan / Khentii basin
  ]
  for la_m, lo_m, wt_m, pw_m in mongolia_arch_sites:
    records.append((la_m, lo_m, wt_m, pw_m, "mongolia_steppe_archaeology", True, 5000 if wt_m >= 4.0 else 1000))
    source_stats["mongolia_steppe_archaeology"] += 1

  print("\n[C] Multi-Repository Ingestion Breakdown:")
  for k, v in source_stats.most_common():
    print(f"    {k}: {v:,} records")
  print(f"    TOTAL COMPOSITE SITE-EPOCH RECORDS: {len(records):,}")
  return records, dict(source_stats)


def aggregate_and_export(domain_mask, land_area, catchments, records, source_stats):
  """Assigns sites to nearest HydroBASINS catchment, applies taphonomic conditioning, and exports GeoJSONs & config."""
  c_xyz = np.array([c["xyz"] for c in catchments])
  tree = cKDTree(c_xyz)

  # Load HYDE 1500AD / 1000AD density for arid/biome conditioning & documented pixels
  hyde_dir = os.path.join(SVEA_ROOT, "histmap", "2.data_cleaning", "landuse_HYDE", "rasters")
  def decode_f32(p):
    raw = np.asarray(Image.open(p).convert("RGBA"), dtype=np.uint8)
    f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
    return np.where(np.isfinite(f32) & (f32 > 0), f32, 0.0)

  p15 = decode_f32(os.path.join(hyde_dir, "popc_1500AD.png"))
  p10 = decode_f32(os.path.join(hyde_dir, "popc_1000AD.png"))
  hyde_dens = np.maximum(p15, p10) / np.maximum(1.0, land_area.astype(np.float64))

  # Aggregate per catchment
  n_c = len(catchments)
  per_counts = {pk: np.zeros(n_c, dtype=np.float64) for pk in PERIOD_KEYS}
  total_raw = np.zeros(n_c, dtype=np.float64)
  has_sett = np.zeros(n_c, dtype=bool)
  max_pop = np.zeros(n_c, dtype=np.float64)
  doc_pixels = set()
  country_breakdown = Counter()

  # Determine domestic vs frontier and snap records to catchments
  rec_xyz = np.array([latlon_to_xyz(r[0], r[1]) for r in records])
  dists, idxs = tree.query(rec_xyz, workers=-1)
  dists_km = dists * EARTH_R_KM

  assigned_dom = 0
  assigned_fr = 0
  for i, r in enumerate(records):
    if dists_km[i] > 180.0:
      continue
    ci = int(idxs[i])
    lat, lon, wt, pw, src_tag, is_sett, mpop = r
    for pk, frac in pw:
      per_counts[pk][ci] += wt * frac
    total_raw[ci] += wt
    if is_sett:
      has_sett[ci] = True
    if mpop > max_pop[ci]:
      max_pop[ci] = mpop
    rr, cc = latlon_to_rc(lat, lon)
    if domain_mask[rr, cc]:
      cr, c_col = latlon_to_rc(catchments[ci]["lat"], catchments[ci]["lon"])
      if hyde_dens[rr, cc] >= 0.002 or ((rr - cr) ** 2 + (cc - c_col) ** 2) <= 25:
        doc_pixels.add(rr * GRID_W + cc)
      assigned_dom += 1
      # Rough regional attribution for metadata summary
      if 119.5 <= lon <= 122.5 and 21.8 <= lat <= 25.5:
        country_breakdown["Taiwan"] += 1
      elif lat > 42.0 and 87.5 <= lon <= 120.0 and not (lat < 45.0 and lon > 111.5):
        country_breakdown["Mongolia_and_Steppe"] += 1
      else:
        country_breakdown["China_Mainland"] += 1
    else:
      assigned_fr += 1

  # Biome/Aridity-conditioned Q75 + IQR taphonomic outlier shrinkage per horizon
  # Prevents surface-deflation/survey hotspots (e.g. arid Qinghai-Gansu/Loess survey bands) from starving humid alluvial basins
  dom_mask_c = np.array([not c["is_frontier_buffer"] for c in catchments], dtype=bool)
  c_areas = np.array([c["area_km2"] for c in catchments], dtype=np.float64)
  c_hyde = np.array([hyde_dens[latlon_to_rc(c["lat"], c["lon"])] for c in catchments], dtype=np.float64)
  is_arid = c_hyde < 2.0

  for pk in PERIOD_KEYS:
    vals = per_counts[pk]
    dens = vals / np.maximum(200.0, c_areas)
    for grp_mask, cap_mult in [(dom_mask_c & is_arid, 1.5), (dom_mask_c & (~is_arid), 2.5)]:
      pos = dens[grp_mask & (dens > 0)]
      if pos.size >= 20:
        q25, q75 = np.percentile(pos, [25, 75])
        iqr = max(1e-7, q75 - q25)
        cap = q75 + cap_mult * iqr
        excess = grp_mask & (dens > cap)
        if excess.any():
          # Soft logarithmic compression above cap (preserves ranking while curbing survey inflation)
          shrunk = cap + iqr * np.log1p((dens[excess] - cap) / iqr)
          vals[excess] = shrunk * np.maximum(200.0, c_areas[excess])
    per_counts[pk] = vals

  # B2 Neighbour Zero-Hole Imputation inside settled belts (HYDE >= 2.0 inh/km2) where a single county/watershed lacked survey volume in Hosner
  k_nbr = min(8, n_c)
  ndists, nidxs = tree.query(c_xyz, k=k_nbr)
  for pk in PERIOD_KEYS:
    vals = per_counts[pk].copy()
    imputed_n = 0
    for ci in range(n_c):
      if vals[ci] > 0 or c_hyde[ci] < 1.5:
        continue
      nbrs = nidxs[ci, 1:]
      nvals = vals[nbrs]
      pos_n = nvals[nvals > 0]
      if pos_n.size >= 4:
        # Scale imputed density gently (0.35x median neighbour density)
        ndens = pos_n / np.maximum(200.0, c_areas[nbrs[nvals > 0]])
        imp_d = 0.35 * float(np.median(ndens))
        vals[ci] = imp_d * c_areas[ci]
        imputed_n += 1
    per_counts[pk] = vals

  # Export period GeoJSONs + 00_all_periods.geojson
  period_meta = []
  for p in PERIODS:
    pk = p["key"]
    feats = []
    dom_sum = 0.0
    dom_active = 0
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
          "period_key": pk
        }
      })
    gj_path = os.path.join(GJ_DIR, p["geojson_filename"])
    with open(gj_path, "w", encoding="utf-8") as fh:
      json.dump({"type": "FeatureCollection", "features": feats}, fh)
    period_meta.append({
      "key": pk,
      "geojson_filename": p["geojson_filename"],
      "total_sites_count": int(round(dom_sum)),
      "active_domestic_catchments": dom_active,
    })
    print(f"  Exported {p['geojson_filename']}: dom_weighted_sites={dom_sum:,.1f} | active_dom_catchments={dom_active}/{int(dom_mask_c.sum())}")

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
        "max_settlement_pop": int(max_pop[ci])
      }
    })
  with open(os.path.join(GJ_DIR, "00_all_periods.geojson"), "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": all_feats}, fh)

  # Export documented_site_pixels.json
  with open(os.path.join(CFG_DIR, "documented_site_pixels.json"), "w", encoding="utf-8") as fh:
    json.dump({"grid_width": GRID_W, "grid_height": GRID_H, "pixel_indices": sorted(doc_pixels)}, fh)

  # Export sites_east_asia_geojson_metadata.json
  meta_obj = {
    "domain": "JADE",
    "macro_scope": "China (incl. Tibet, Xinjiang, Manchuria, Inner Mongolia), Mongolia, Taiwan, Hong Kong and Macao",
    "sources": list(source_stats.keys()),
    "source_record_counts": source_stats,
    "country_breakdown": dict(country_breakdown),
    "domestic_assigned_records": assigned_dom,
    "frontier_assigned_records": assigned_fr,
    "catchment_counts": {"domestic": int(dom_mask_c.sum()), "frontier_buffer": int((~dom_mask_c).sum())},
    "documented_site_pixels": len(doc_pixels),
    "period_geojsons": period_meta
  }
  with open(os.path.join(CFG_DIR, "sites_east_asia_geojson_metadata.json"), "w", encoding="utf-8") as fh:
    json.dump(meta_obj, fh, indent=2)

  # Export sites_east_asia.json5
  all_hyde_years = [
    -10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000,
    0, 100, 200, 300, 400, 500, 600, 700, 800, 900,
    1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
    1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790,
    1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890,
    1900, 1910, 1920, 1930, 1940, 1950
  ] + list(range(1951, 2026))

  cfg_obj = {
    "geojson_metadata_filename": "config/sites_east_asia_geojson_metadata.json",
    "include_all_periods_geojson": True,
    "kriging_metadata_filename": "config/kriging_diagnostics.json",
    "output_geojson_subfolder": "geojson",
    "output_kriged_rasters_subfolder": "1.kriged_rasters",
    "output_population_rasters_subfolder": "2.population_rasters",
    "png_compression_level": 6,
    "kriging_config": {
      "all_hyde_years": all_hyde_years,
      "apply_arid_taphonomic_correction": True,
      "apply_urban_salvage_debias": True,
      "covariate_paths": {
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/JADE/_shared/sites_east_asia/config/documented_site_pixels.json",
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
        "urban_mask_buffer_radius": 3,
        "urban_mask_inpaint_radius": 6,
        "urban_uopp_threshold": 3.8
      },
      "dimensionless_lag_bins": [0.85, 1.45, 2.10, 2.95, 4.10, 5.60, 7.80, 10.80, 14.50],
      "domain_mask_png": "histmap/1.data_raw/population_regional/JADE/_shared/sites_east_asia/config/jade_domain_mask.png",
      "earth_radius_km": 6371,
      "frontier_conditioning_max_dist_km": 300,
      "grid_height": GRID_H,
      "grid_width": GRID_W,
      "target_domestic_catchments": int(dom_mask_c.sum()),
      "chronological_horizons": [
        {"active_periods": [p["key"]], "key": p["key"] + "_horizon", "year": p["representative_year"]}
        for p in PERIODS
      ]
    },
    "periods": PERIODS
  }
  with open(os.path.join(CFG_DIR, "sites_east_asia.json5"), "w", encoding="utf-8") as fh:
    json.dump(cfg_obj, fh, indent=2, ensure_ascii=False)

  print(f"\n[D] Completed JADE multi-repository extraction: {assigned_dom:,} domestic + {assigned_fr:,} frontier records across {len(doc_pixels):,} documented pixels.")


def main():
  domain_mask, land_area = build_jade_domain_mask()
  catchments = build_catchments(domain_mask, land_area)
  records, source_stats = ingest_all_repositories()
  aggregate_and_export(domain_mask, land_area, catchments, records, source_stats)


if __name__ == "__main__":
  main()
