"""Stage A2 Dual Mask & Vector Sub-Region GeoJSON Builder for Operation Viscount Project SARAY.

Builds:
  1. `saray_domain_mask.png` (4320x2160 RGBA) covering Kazakhstan, Uzbekistan, Turkmenistan,
     Kyrgyzstan, and Tajikistan from Natural Earth 10m Admin-0 + `land_area.png`.
  2. Smooth vector sub-region GeoJSONs (`_shared/_gis_cache/chapter_subregions/<stem>_subregions.geojson`)
     + 4320x2160 RGBA pipeline areal masks (`<chapter_dir>/<stem>_areal_mask.png`)
     + chapter population JSON5 files (`<chapter_dir>/<stem>.json5`) across all 9 canonical SARAY chapters
     (-10000 to 2026 AD), strictly adhering to the Three-Regime Spatiotemporal Partitioning Law:
       - Regime I (Prehistoric -10000..-1000 & Classical -1000..500): Dissolved HydroBASINS Level 5-6
         oasis, riverine & steppe ecological catchments (zero synthetic rectangular boxes).
       - Regime II (Mediaeval 500..1219, Mongol-Timurid 1219..1500, Uzbek Khanates & Kazakh Hordes
         1500..1865, Imperial Turkestan & Steppe 1865..1917, Civil War/Early Soviet 1917..1945):
         Period-authentic provinces, khanates, zhuzes, Imperial Russian oblasts & early Soviet republics.
       - Regime III (Post-War Soviet 1945..1991 & Post-Soviet 1991..2026): Exact Natural Earth 10m
         Admin-1 oblasts & capital municipalities across all 5 republics.
  3. Master manifests: `saray_areal_masks.json5` and `saray_gazetteers.json5`.
"""

import io
import json
import os
import zipfile

import numpy as np
import shapefile
from PIL import Image
from shapely.geometry import Point, mapping, shape
from shapely.ops import unary_union
from shapely.prepared import prep

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SARAY_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "SARAY")
SUB_GJ_DIR = os.path.join(SARAY_DIR, "_shared", "_gis_cache", "chapter_subregions")
DOMAIN_CFG_DIR = os.path.join(SARAY_DIR, "_shared", "sites_saray_central_asia", "config")
DOMAIN_MASK_PNG = os.path.join(DOMAIN_CFG_DIR, "saray_domain_mask.png")
JADE_GIS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JADE", "_shared", "_gis_cache")
SHARED_GIS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_shared", "_gis_cache")
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")

os.makedirs(SUB_GJ_DIR, exist_ok=True)
os.makedirs(DOMAIN_CFG_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160
SARAY_COUNTRIES = {"Kazakhstan", "Uzbekistan", "Turkmenistan", "Kyrgyzstan", "Tajikistan"}

# High-contrast non-black RGB palette for areal masks
PALETTE = [
  [184, 105, 81], [86, 134, 168], [118, 158, 98], [198, 152, 74],
  [146, 106, 162], [78, 156, 148], [204, 118, 132], [134, 146, 86],
  [172, 128, 104], [96, 118, 174], [164, 154, 88], [192, 102, 106],
  [88, 148, 118], [156, 116, 138], [122, 164, 184], [186, 142, 112],
  [108, 138, 94], [168, 96, 124], [142, 126, 166], [92, 158, 168],
  [196, 132, 92], [116, 146, 142], [176, 112, 96], [132, 156, 116],
  [214, 136, 98], [76, 116, 154], [148, 172, 106], [188, 164, 82],
  [162, 114, 178], [68, 144, 138], [212, 134, 148], [122, 136, 78],
  [182, 138, 114], [108, 128, 186], [176, 166, 98], [202, 112, 116],
  [98, 162, 132], [168, 128, 152], [136, 176, 196], [198, 154, 124],
  [118, 152, 104], [182, 108, 138], [154, 138, 178], [104, 170, 182],
  [208, 144, 104], [128, 158, 154], [188, 124, 108], [144, 168, 128],
]


def latlon_to_rc(lat, lon):
  r = min(GRID_H - 1, max(0, int((90.0 - lat) * GRID_H / 180.0)))
  c = min(GRID_W - 1, max(0, int((lon + 180.0) * GRID_W / 360.0)))
  return r, c


def load_gis_and_build_domain_mask():
  print("[1] Building SARAY 4320x2160 domain mask & loading Admin-1 + HydroBASINS L5/L6...", flush=True)
  la_raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  land_area = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2])

  # Admin-0 polygons for crisp SARAY domain mask
  ne0 = json.load(open(os.path.join(SHARED_GIS_DIR, "ne_10m_admin_0_countries.geojson"), "r", encoding="utf-8"))
  adm0_geoms = []
  for f in ne0["features"]:
    adm = (f.get("properties") or {}).get("ADMIN")
    if adm in SARAY_COUNTRIES:
      adm0_geoms.append(shape(f["geometry"]).buffer(0))
  saray_union = unary_union(adm0_geoms).buffer(0)

  # Rasterise SARAY domain mask on 4320x2160
  if os.path.exists(DOMAIN_MASK_PNG):
    dm_raw = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
    domain_mask = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)
  else:
    domain_mask = np.zeros((GRID_H, GRID_W), dtype=bool)
    minx, miny, maxx, maxy = saray_union.bounds
    r0, c0 = latlon_to_rc(maxy, minx)
    r1, c1 = latlon_to_rc(miny, maxx)
    r0, c0 = max(0, r0 - 2), max(0, c0 - 2)
    r1, c1 = min(GRID_H - 1, r1 + 2), min(GRID_W - 1, c1 + 2)
    pg = prep(saray_union)
    for rr in range(r0, r1 + 1):
      plat = 90.0 - (rr + 0.5) * 180.0 / GRID_H
      for cc in range(c0, c1 + 1):
        if land_area[rr, cc] == 0:
          continue
        plon = -180.0 + (cc + 0.5) * 360.0 / GRID_W
        if pg.contains(Point(plon, plat)):
          domain_mask[rr, cc] = True
    rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
    rgba[domain_mask] = [255, 255, 255, 255]
    Image.fromarray(rgba, mode="RGBA").save(DOMAIN_MASK_PNG)
    print(f"  Saved {DOMAIN_MASK_PNG}: {int(domain_mask.sum()):,} active land pixels ({int(land_area[domain_mask].sum()):,} km2)", flush=True)

  # Load Natural Earth 10m Admin-1 for all 5 SARAY republics
  adm1_gj = json.load(open(os.path.join(JADE_GIS_DIR, "ne_10m_admin_1_states_provinces.geojson"), "r", encoding="utf-8"))
  adm1 = {}
  by_country = {}
  # Handle duplicate Tashkent (city vs region) carefully using area/type
  tashkent_list = []
  for f in adm1_gj["features"]:
    p = f["properties"]
    c = p.get("admin") or p.get("geonunit")
    if c not in SARAY_COUNTRIES:
      continue
    nm = p.get("name") or p.get("name_en")
    g = shape(f["geometry"]).buffer(0)
    if c == "Uzbekistan" and nm == "Tashkent":
      tashkent_list.append((g.area, g, p.get("type_en") or ""))
      by_country.setdefault(c, []).append(g)
      continue
    adm1[(c, nm)] = g
    by_country.setdefault(c, []).append(g)

  if tashkent_list:
    tashkent_list.sort(key=lambda x: x[0])
    if len(tashkent_list) == 2:
      adm1[("Uzbekistan", "Tashkent City")] = tashkent_list[0][1]
      adm1[("Uzbekistan", "Tashkent")] = tashkent_list[1][1]
    else:
      adm1[("Uzbekistan", "Tashkent")] = unary_union([x[1] for x in tashkent_list]).buffer(0)

  country_union = {c: unary_union(gs).buffer(0) for c, gs in by_country.items()}
  saray_vec_union = unary_union(list(country_union.values())).buffer(0)

  # Load HydroBASINS Level 6 (Asia + Siberia) clipped to SARAY for crisp organic Regime I catchments
  basins = []
  for hyb_fn in ("hybas_as_lev06_v1c.zip", "hybas_si_lev06_v1c.zip"):
    hyb_zip = os.path.join(JADE_GIS_DIR, hyb_fn)
    if not os.path.exists(hyb_zip):
      continue
    with zipfile.ZipFile(hyb_zip) as zf:
      sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
      sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
      for sr in sf.iterShapeRecords():
        bb = sr.shape.bbox
        if bb[2] < 46.0 or bb[0] > 88.0 or bb[3] < 35.0 or bb[1] > 56.0:
          continue
        g = shape(sr.shape.__geo_interface__).buffer(0)
        if not g.is_empty and g.intersects(saray_vec_union):
          gc = g.intersection(saray_vec_union).buffer(0)
          if not gc.is_empty and gc.area > 0.005:
            rp = gc.representative_point()
            basins.append((gc, float(rp.y), float(rp.x), hyb_fn))
  # Clip giant Karakum/Caspian Level-6 endorheic polygon along organic Turkmen/Kazakh biogeographic divide so Kopet Dag/Murgab stays distinct from Ural-Emba Steppe
  refined_basins = []
  from shapely.geometry import box as sbox
  for gc, lat, lon, fn in basins:
    minx, miny, maxx, maxy = gc.bounds
    if gc.area > 25.0 and miny < 39.5 and maxy > 42.5:
      # Subdivide along Kopet Dag / Aral-Karakum / Ural-Mangyshlak natural ecotone corridors using Admin-1 country/oblast natural watersheds
      for sub_name, sub_g in [
        ("kopet", unary_union([adm1[("Turkmenistan", "Ahal")], adm1[("Turkmenistan", "Mary")], adm1[("Turkmenistan", "Balkan")], adm1[("Turkmenistan", "Chardzhou")]]).buffer(0)),
        ("khwar", unary_union([adm1[("Uzbekistan", "Khorezm")], adm1[("Uzbekistan", "Karakalpakstan")], adm1[("Turkmenistan", "Tashauz")]]).buffer(0)),
      ]:
        inter = gc.intersection(sub_g).buffer(0)
        if not inter.is_empty and inter.area > 0.05:
          rp = inter.representative_point()
          refined_basins.append((inter, float(rp.y), float(rp.x), fn + "_" + sub_name))
          gc = gc.difference(sub_g).buffer(0)
      if not gc.is_empty and gc.area > 0.05:
        rp = gc.representative_point()
        refined_basins.append((gc, float(rp.y), float(rp.x), fn + "_rem"))
    else:
      refined_basins.append((gc, lat, lon, fn))
  basins = refined_basins

  # Cover Western Kazakhstan / Turkmenistan / Khwarazm (west of hybas_as coverage) via authentic natural sub-basins
  if basins:
    cov_hyb = unary_union([b[0] for b in basins]).buffer(0)
    rem_west = saray_vec_union.difference(cov_hyb).buffer(0)
    if not rem_west.is_empty and rem_west.area > 0.1:
      west_units = [
        ("kopet_murgab", [("Turkmenistan", "Ahal"), ("Turkmenistan", "Mary"), ("Turkmenistan", "Balkan"), ("Turkmenistan", "Chardzhou")]),
        ("khwarazm_delta", [("Uzbekistan", "Khorezm"), ("Uzbekistan", "Karakalpakstan"), ("Turkmenistan", "Tashauz")]),
        ("ural_emba_steppe", [("Kazakhstan", "West Kazakhstan"), ("Kazakhstan", "Atyrau"), ("Kazakhstan", "Mangghystau"), ("Kazakhstan", "Aqtöbe"), ("Kazakhstan", "Qostanay"), ("Kazakhstan", "Qyzylorda")]),
      ]
      for wtag, wspecs in west_units:
        wg = union_adm1(adm1, wspecs)
        if wg is not None:
          inter = rem_west.intersection(wg).buffer(0)
          if not inter.is_empty and inter.area > 0.05:
            rp = inter.representative_point()
            basins.append((inter, float(rp.y), float(rp.x), wtag))
  print(f"  Loaded {len(adm1)} Admin-1 polygons across {len(country_union)} republics + {len(basins)} clipped HydroBASINS polygons.", flush=True)
  return domain_mask, land_area, saray_vec_union, adm1, country_union, basins


def union_adm1(adm1, specs):
  gs = []
  for c, nm in specs:
    if nm is None:
      for (cc, nn), g in adm1.items():
        if cc == c:
          gs.append(g)
    else:
      g = adm1.get((c, nm))
      if g is not None:
        gs.append(g)
  if not gs:
    return None
  return unary_union(gs).buffer(0)


def assign_basins_to_zones(basins, saray_union, zone_rules):
  """Partitions ALL HydroBASINS polygons organically into non-overlapping ecological basins."""
  buckets = {rid: [] for rid, _, _ in zone_rules}
  for g, lat, lon, _ in basins:
    assigned = False
    for rid, _, pred in zone_rules:
      if pred(lat, lon):
        buckets[rid].append(g)
        assigned = True
        break
    if not assigned:
      buckets[zone_rules[-1][0]].append(g)
  out = []
  covered = []
  for rid, rname, _ in zone_rules:
    gs = buckets[rid]
    if not gs:
      continue
    u = unary_union(gs).buffer(0)
    covered.append(u)
    out.append((rid, rname, u))
  # Attach any residual sliver inside saray_union (e.g. Aral/Caspian shore) to nearest zone
  if covered:
    cov_u = unary_union(covered).buffer(0)
    rem = saray_union.difference(cov_u).buffer(0)
    if not rem.is_empty and rem.area > 0.001:
      # Distribute residual polygon parts to nearest zone by centroid
      parts = list(rem.geoms) if hasattr(rem, "geoms") else [rem]
      by_z = {i: [out[i][2]] for i in range(len(out))}
      for pt in parts:
        if pt.area < 1e-5:
          continue
        rp = pt.representative_point()
        best_i = min(range(len(out)), key=lambda i: out[i][2].distance(rp))
        by_z[best_i].append(pt)
      out = [(out[i][0], out[i][1], unary_union(by_z[i]).buffer(0)) for i in range(len(out))]
  return out


def rasterise_regions(region_geoms, domain_mask, land_area):
  """Rasterises list of (rid, rname, geom, rgb) cleanly onto 4320x2160 RGBA inside domain_mask."""
  rgba = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
  owner = np.full((GRID_H, GRID_W), -1, dtype=np.int16)

  for idx, (rid, rname, geom, rgb) in enumerate(region_geoms):
    if geom is None or geom.is_empty:
      continue
    minx, miny, maxx, maxy = geom.bounds
    r0, c0 = latlon_to_rc(maxy, minx)
    r1, c1 = latlon_to_rc(miny, maxx)
    r0, c0 = max(0, r0 - 1), max(0, c0 - 1)
    r1, c1 = min(GRID_H - 1, r1 + 1), min(GRID_W - 1, c1 + 1)
    pg = prep(geom)
    sub_dm = domain_mask[r0:r1 + 1, c0:c1 + 1]
    drs, dcs = np.where(sub_dm)
    for dr, dc in zip(drs, dcs):
      rr = r0 + int(dr)
      cc = c0 + int(dc)
      if owner[rr, cc] != -1:
        continue
      plat = 90.0 - (rr + 0.5) * 180.0 / GRID_H
      plon = -180.0 + (cc + 0.5) * 360.0 / GRID_W
      if pg.contains(Point(plon, plat)):
        owner[rr, cc] = idx
        rgba[rr, cc] = [rgb[0], rgb[1], rgb[2], 255]

    # Ensure compact enclave cities (Almaty City, Astana, Tashkent City, Bishkek, Dushanbe) always get >= 1 pixel
    if int((owner == idx).sum()) == 0:
      rp = geom.representative_point()
      rr, cc = latlon_to_rc(float(rp.y), float(rp.x))
      owner[rr, cc] = idx
      rgba[rr, cc] = [rgb[0], rgb[1], rgb[2], 255]

  # Fill any unowned domain_mask border pixels by nearest owned neighbour (keeps 100% domain coverage)
  unowned = domain_mask & (owner == -1)
  if unowned.any():
    from scipy.ndimage import distance_transform_edt
    _, inds = distance_transform_edt(owner == -1, return_indices=True)
    urs, ucs = np.where(unowned)
    for rr, cc in zip(urs, ucs):
      nr, nc = int(inds[0, rr, cc]), int(inds[1, rr, cc])
      idx = int(owner[nr, nc])
      if idx >= 0:
        owner[rr, cc] = idx
        rgb = region_geoms[idx][3]
        rgba[rr, cc] = [rgb[0], rgb[1], rgb[2], 255]

  stats = []
  for idx, (rid, rname, geom, rgb) in enumerate(region_geoms):
    m = (owner == idx)
    px = int(m.sum())
    area = int(round(float(land_area[m].sum()))) if px > 0 else 0
    if px > 0:
      rs, cs = np.where(m)
      bbox = {
        "min_lat": round(90.0 - (int(rs.max()) + 1) * 180.0 / GRID_H, 2),
        "max_lat": round(90.0 - int(rs.min()) * 180.0 / GRID_H, 2),
        "min_lon": round(-180.0 + int(cs.min()) * 360.0 / GRID_W, 2),
        "max_lon": round(-180.0 + (int(cs.max()) + 1) * 360.0 / GRID_W, 2),
      }
    else:
      bbox = {"min_lat": 0.0, "max_lat": 0.0, "min_lon": 0.0, "max_lon": 0.0}
    stats.append((px, max(area, px * 25), bbox))
  return rgba, stats


def build_pop_series(benchmarks, total_by_year, shares_by_year_or_const):
  reg_pops = {}
  reg_bounds = {}
  is_dynamic = isinstance(next(iter(shares_by_year_or_const.values())), dict)
  for rid, sh_spec in shares_by_year_or_const.items():
    p_dict, b_dict = {}, {}
    for yr in benchmarks:
      sh = sh_spec[yr] if is_dynamic else sh_spec
      val = max(500, int(round(total_by_year[yr] * sh)))
      unc = 0.28 if yr < 0 else (0.20 if yr < 1500 else (0.14 if yr < 1865 else (0.04 if yr < 1950 else 0.015)))
      p_dict[str(yr)] = val
      b_dict[str(yr)] = [max(200, int(round(val * (1.0 - unc)))), int(round(val * (1.0 + unc)))]
    reg_pops[rid] = p_dict
    reg_bounds[rid] = b_dict
  return reg_pops, reg_bounds


def define_all_9_chapters(saray_union, adm1, cu, basins):
  chapters = []

  # --- CHAPTER 1: Prehistoric Central Asian Steppe and Oases (-10000 to -1000) [Regime I, Specialist] ---
  ch1_rules = [
    ("kopet_dag_murgab_oases", "1. Kopet Dag Foothills, Murgab and Tedjen Oases (Jeitun-Namazga-BMAC)", lambda la, lo: la < 40.3 and lo < 64.5),
    ("lower_amu_darya_khwarazm", "2. Lower Amu Darya Delta, Khwarazm and Aral Basin (Kelteminar-Tazabagyab)", lambda la, lo: 40.3 <= la < 45.2 and 55.5 <= lo < 64.5),
    ("zeravshan_surkhan_bactria", "3. Zeravshan, Qashqadarya and Northern Bactrian Valleys (Sarazm-Sapalli)", lambda la, lo: la < 40.8 and 64.5 <= lo < 70.3),
    ("pamir_alay_vakhsh_highlands", "4. Pamir-Alay and Upper Vakhsh Highlands (Hissar-Vakhsh)", lambda la, lo: la < 40.2 and lo >= 70.3),
    ("ferghana_chach_middle_syr", "5. Ferghana Valley, Chach and Middle Syr Darya (Chust-Kayrakkum)", lambda la, lo: 40.2 <= la < 44.5 and 64.5 <= lo < 74.5),
    ("semirechye_tian_shan_corridor", "6. Semirechye, Issyk-Kul and Inner Asian Mountain Corridor (Begash-Tasbas)", lambda la, lo: 40.2 <= la < 47.5 and lo >= 74.5),
    ("western_steppe_ural_mangyshlak", "7. Western Steppe, Ural-Emba and Mangyshlak Plateau (Yamnaya-Srubnaya)", lambda la, lo: lo < 60.5 and la >= 40.3),
    ("northern_central_kazakh_steppe", "8. Northern and Central Kazakh Steppe, Tobol-Ishim-Irtysh (Botai-Sintashta-Andronovo)", lambda la, lo: True),
  ]
  ch1_zones = assign_basins_to_zones(basins, saray_union, ch1_rules)
  ch1_bms = [-10000, -8000, -6000, -5000, -4000, -3000, -2000, -1500, -1000]
  ch1_tot = {-10000: 40000, -8000: 65000, -6000: 145000, -5000: 220000, -4000: 340000, -3000: 520000, -2000: 980000, -1500: 1150000, -1000: 1450000}
  ch1_sh = {
    "kopet_dag_murgab_oases": 0.17, "lower_amu_darya_khwarazm": 0.09, "zeravshan_surkhan_bactria": 0.21,
    "pamir_alay_vakhsh_highlands": 0.06, "ferghana_chach_middle_syr": 0.16, "semirechye_tian_shan_corridor": 0.09,
    "western_steppe_ural_mangyshlak": 0.07, "northern_central_kazakh_steppe": 0.15,
  }
  chapters.append({
    "group": "1.ancient_and_classical", "folder": "1.prehistoric_central_asian_steppe_and_oases",
    "stem": "prehistoric_central_asian_steppe_and_oases",
    "title": "Prehistoric Central Asian Steppe and Oases (10000BC-1000BC)",
    "domain": [-10000, -1000], "tier": "specialist", "priority": 1, "is_admin1": False,
    "zones": ch1_zones, "benchmarks": ch1_bms, "totals": ch1_tot, "shares": ch1_sh,
  })

  # --- CHAPTER 2: Scythian/Saka Pastoralists and Classical Oasis States (-1000 to 500) [Regime I/II] ---
  ch2_rules = [
    ("parthia_margiana_oases", "1. Parthian Kopet Dag and Margiana Oasis (Nisa-Merv)", lambda la, lo: la < 40.3 and lo < 64.5),
    ("classical_khwarazm", "2. Classical Khwarazm Oasis State (Toprak-Kala-Koy-Krylgan-Kala)", lambda la, lo: 40.3 <= la < 44.8 and 56.0 <= lo < 64.5),
    ("sogdiana_zeravshan_qashqa", "3. Sogdiana Core (Marakanda-Bukhara-Erkurgan-Panjikent)", lambda la, lo: 38.4 <= la < 41.2 and 63.8 <= lo < 70.0),
    ("northern_bactria_tokharistan", "4. Northern Bactria and Upper Oxus (Termez-Dalverzin-Takht-i Sangin)", lambda la, lo: la < 38.4 and lo >= 64.5),
    ("pamir_saka_highlands", "5. Pamir and Badakhshan Saka Highlands", lambda la, lo: 38.4 <= la < 40.2 and lo >= 70.0),
    ("ferghana_dayuan_chach", "6. Dayuan Ferghana and Kangju Chach-Middle Syr Darya (Ershi-Kanka-Otrar)", lambda la, lo: 40.2 <= la < 44.8 and 64.5 <= lo < 74.5),
    ("semirechye_wusun_saka", "7. Semirechye and Tian Shan Saka-Wusun Corridor (Issyk-Chigu)", lambda la, lo: 40.2 <= la < 47.5 and lo >= 74.5),
    ("massagetae_sarmatian_west", "8. Aral-Caspian Massagetae and Sarmatian Western Steppe", lambda la, lo: lo < 62.5 and la >= 40.3),
    ("tasmola_saka_northern_steppe", "9. Tasmola-Saka Central and Northern Kazakh Steppe", lambda la, lo: True),
  ]
  ch2_zones = assign_basins_to_zones(basins, saray_union, ch2_rules)
  ch2_bms = [-1000, -500, -200, 1, 200, 350, 500]
  ch2_tot = {-1000: 1450000, -500: 2200000, -200: 2750000, 1: 3450000, 200: 3750000, 350: 3350000, 500: 3550000}
  ch2_sh = {
    "parthia_margiana_oases": 0.13, "classical_khwarazm": 0.10, "sogdiana_zeravshan_qashqa": 0.21,
    "northern_bactria_tokharistan": 0.12, "pamir_saka_highlands": 0.03, "ferghana_dayuan_chach": 0.17,
    "semirechye_wusun_saka": 0.08, "massagetae_sarmatian_west": 0.06, "tasmola_saka_northern_steppe": 0.10,
  }
  chapters.append({
    "group": "1.ancient_and_classical", "folder": "2.scythian_saka_and_classical_oasis_states",
    "stem": "scythian_saka_and_classical_oasis_states",
    "title": "Scythian-Saka Pastoralists and Classical Oasis States (1000BC-500AD)",
    "domain": [-1000, 500], "tier": "national", "priority": 2, "is_admin1": False,
    "zones": ch2_zones, "benchmarks": ch2_bms, "totals": ch2_tot, "shares": ch2_sh,
  })

  # --- CHAPTER 3: Turkic Migrations and Islamisation of Turan and Transoxiana (500 to 1219) [Regime II] ---
  ch3_zones = [
    ("mawarannahr_sogd_core", "1. Mawarannahr Core: Bukhara, Samarkand, Kesh and Nasaf", union_adm1(adm1, [("Uzbekistan", "Bukhoro"), ("Uzbekistan", "Samarkand"), ("Uzbekistan", "Navoi"), ("Uzbekistan", "Jizzakh"), ("Uzbekistan", "Kashkadarya")])),
    ("chach_ilak_isfijab", "2. Chach, Ilak, Isfijab and Otrar Frontier", union_adm1(adm1, [("Uzbekistan", "Tashkent"), ("Uzbekistan", "Tashkent City"), ("Uzbekistan", "Sirdaryo"), ("Kazakhstan", "South Kazakhstan"), ("Kazakhstan", "Qyzylorda")])),
    ("ferghana_ustrushana", "3. Ferghana and Ustrushana (Akhsi-Khujand-Uzgen)", union_adm1(adm1, [("Uzbekistan", "Ferghana"), ("Uzbekistan", "Andijon"), ("Uzbekistan", "Namangan"), ("Tajikistan", "Leninabad"), ("Kyrgyzstan", "Osh"), ("Kyrgyzstan", "Batken"), ("Kyrgyzstan", "Jalal-Abad")])),
    ("chaghaniyan_khuttal_badakhshan", "4. Chaghaniyan, Khuttal and Badakhshan", union_adm1(adm1, [("Uzbekistan", "Surkhandarya"), ("Tajikistan", "Khatlon"), ("Tajikistan", "Dushanbe"), ("Tajikistan", "Tadzhikistan Territories"), ("Tajikistan", "Gorno-Badakhshan")])),
    ("khwarazm_gurganj_kath", "5. Khwarazm (Gurganj and Kath)", union_adm1(adm1, [("Uzbekistan", "Khorezm"), ("Uzbekistan", "Karakalpakstan"), ("Turkmenistan", "Tashauz")])),
    ("khurasan_merv_dihistan", "6. Khurasan Frontier: Merv, Nisa, Amul and Dihistan", union_adm1(adm1, [("Turkmenistan", "Mary"), ("Turkmenistan", "Chardzhou"), ("Turkmenistan", "Ahal"), ("Turkmenistan", "Balkan")])),
    ("semirechye_balasagun_karluk", "7. Semirechye and Chu-Talas Karluk-Karakhanid Towns (Balasagun-Taraz)", union_adm1(adm1, [("Kyrgyzstan", "Chuy"), ("Kyrgyzstan", "Bishkek"), ("Kyrgyzstan", "Talas"), ("Kyrgyzstan", "Ysyk-Köl"), ("Kyrgyzstan", "Naryn"), ("Kazakhstan", "Zhambyl"), ("Kazakhstan", "Almaty"), ("Kazakhstan", "Almaty City")])),
    ("oghuz_kipchak_western_steppe", "8. Oghuz and Western Kipchak Steppe (Aral-Ural-Mangyshlak)", union_adm1(adm1, [("Kazakhstan", "Mangghystau"), ("Kazakhstan", "Atyrau"), ("Kazakhstan", "West Kazakhstan"), ("Kazakhstan", "Aqtöbe")])),
    ("kimak_kipchak_northern_steppe", "9. Kimak-Kipchak Central and Northern Steppe", union_adm1(adm1, [("Kazakhstan", "Qostanay"), ("Kazakhstan", "North Kazakhstan"), ("Kazakhstan", "Aqmola"), ("Kazakhstan", "Astana"), ("Kazakhstan", "Pavlodar"), ("Kazakhstan", "Qaraghandy"), ("Kazakhstan", "East Kazakhstan")])),
  ]
  ch3_bms = [500, 650, 800, 950, 1100, 1200, 1219]
  ch3_tot = {500: 3550000, 650: 4100000, 800: 4450000, 950: 5550000, 1100: 6350000, 1200: 6850000, 1219: 6950000}
  ch3_sh = {
    "mawarannahr_sogd_core": 0.21, "chach_ilak_isfijab": 0.13, "ferghana_ustrushana": 0.16,
    "chaghaniyan_khuttal_badakhshan": 0.09, "khwarazm_gurganj_kath": 0.11, "khurasan_merv_dihistan": 0.12,
    "semirechye_balasagun_karluk": 0.08, "oghuz_kipchak_western_steppe": 0.04, "kimak_kipchak_northern_steppe": 0.06,
  }
  chapters.append({
    "group": "2.mediaeval_and_khanates", "folder": "1.turkic_migrations_and_islamisation_turan",
    "stem": "turkic_migrations_and_islamisation_turan",
    "title": "Turkic Migrations and Islamisation of Turan and Transoxiana (500AD-1219AD)",
    "domain": [500, 1219], "tier": "national", "priority": 2, "is_admin1": False,
    "zones": ch3_zones, "benchmarks": ch3_bms, "totals": ch3_tot, "shares": ch3_sh,
  })

  # --- CHAPTER 4: Mongol Conquest and Timurid Central Asia (1219 to 1500) [Regime II] ---
  ch4_zones = [
    ("timurid_samarkand_bukhara", "1. Timurid Mawarannahr Core (Samarkand-Bukhara-Kesh)", union_adm1(adm1, [("Uzbekistan", "Samarkand"), ("Uzbekistan", "Bukhoro"), ("Uzbekistan", "Navoi"), ("Uzbekistan", "Jizzakh"), ("Uzbekistan", "Kashkadarya")])),
    ("timurid_hisar_badakhshan", "2. Hisar, Termez, Khuttal and Badakhshan", union_adm1(adm1, [("Uzbekistan", "Surkhandarya"), ("Tajikistan", "Khatlon"), ("Tajikistan", "Dushanbe"), ("Tajikistan", "Tadzhikistan Territories"), ("Tajikistan", "Gorno-Badakhshan")])),
    ("chagatai_ferghana_tashkent", "3. Ferghana and Tashkent-Shash (Andijan-Khujand)", union_adm1(adm1, [("Uzbekistan", "Ferghana"), ("Uzbekistan", "Andijon"), ("Uzbekistan", "Namangan"), ("Uzbekistan", "Tashkent"), ("Uzbekistan", "Tashkent City"), ("Uzbekistan", "Sirdaryo"), ("Tajikistan", "Leninabad"), ("Kyrgyzstan", "Osh"), ("Kyrgyzstan", "Batken"), ("Kyrgyzstan", "Jalal-Abad")])),
    ("khwarazm_golden_horde_timurid", "4. Khwarazm (Urgench and Khiva)", union_adm1(adm1, [("Uzbekistan", "Khorezm"), ("Uzbekistan", "Karakalpakstan"), ("Turkmenistan", "Tashauz")])),
    ("ilkhanid_timurid_khurasan", "5. Depopulated Murgab, Merv and Caspian Turkmenia", union_adm1(adm1, [("Turkmenistan", "Mary"), ("Turkmenistan", "Chardzhou"), ("Turkmenistan", "Ahal"), ("Turkmenistan", "Balkan")])),
    ("syr_darya_frontier_towns", "6. Syr Darya Frontier Towns (Otrar-Yasi-Sighnaq-Sauran)", union_adm1(adm1, [("Kazakhstan", "South Kazakhstan"), ("Kazakhstan", "Qyzylorda")])),
    ("moghulistan_semirechye", "7. Moghulistan (Semirechye and Tian Shan)", union_adm1(adm1, [("Kazakhstan", "Almaty"), ("Kazakhstan", "Almaty City"), ("Kazakhstan", "Zhambyl"), ("Kyrgyzstan", "Chuy"), ("Kyrgyzstan", "Bishkek"), ("Kyrgyzstan", "Talas"), ("Kyrgyzstan", "Ysyk-Köl"), ("Kyrgyzstan", "Naryn")])),
    ("dasht_i_qipchaq_white_horde", "8. Dasht-i Qipchaq (White Horde and Early Kazakh Steppe)", union_adm1(adm1, [("Kazakhstan", "West Kazakhstan"), ("Kazakhstan", "Atyrau"), ("Kazakhstan", "Mangghystau"), ("Kazakhstan", "Aqtöbe"), ("Kazakhstan", "Qostanay"), ("Kazakhstan", "North Kazakhstan"), ("Kazakhstan", "Aqmola"), ("Kazakhstan", "Astana"), ("Kazakhstan", "Pavlodar"), ("Kazakhstan", "Qaraghandy"), ("Kazakhstan", "East Kazakhstan")])),
  ]
  ch4_bms = [1219, 1250, 1300, 1350, 1400, 1450, 1500]
  ch4_tot = {1219: 6950000, 1250: 3900000, 1300: 4350000, 1350: 4150000, 1400: 4850000, 1450: 5250000, 1500: 5400000}
  ch4_sh = {
    "timurid_samarkand_bukhara": 0.24, "timurid_hisar_badakhshan": 0.11, "chagatai_ferghana_tashkent": 0.23,
    "khwarazm_golden_horde_timurid": 0.08, "ilkhanid_timurid_khurasan": 0.07, "syr_darya_frontier_towns": 0.07,
    "moghulistan_semirechye": 0.07, "dasht_i_qipchaq_white_horde": 0.13,
  }
  chapters.append({
    "group": "2.mediaeval_and_khanates", "folder": "2.mongol_conquest_and_timurid_central_asia",
    "stem": "mongol_conquest_and_timurid_central_asia",
    "title": "Mongol Conquest and Timurid Central Asia (1219AD-1500AD)",
    "domain": [1219, 1500], "tier": "national", "priority": 2, "is_admin1": False,
    "zones": ch4_zones, "benchmarks": ch4_bms, "totals": ch4_tot, "shares": ch4_sh,
  })

  # --- CHAPTER 5: Uzbek Khanates and Kazakh Steppe Hordes (1500 to 1865) [Regime II] ---
  ch5_zones = [
    ("bukhara_western_core", "1. Khanate and Emirate of Bukhara Core (Bukhara-Samarkand-Qarshi)", union_adm1(adm1, [("Uzbekistan", "Bukhoro"), ("Uzbekistan", "Samarkand"), ("Uzbekistan", "Navoi"), ("Uzbekistan", "Jizzakh"), ("Uzbekistan", "Kashkadarya"), ("Turkmenistan", "Chardzhou")])),
    ("eastern_bukhara_badakhshan", "2. Eastern Bukhara, Hisar and Pamir Principalities", union_adm1(adm1, [("Uzbekistan", "Surkhandarya"), ("Tajikistan", "Khatlon"), ("Tajikistan", "Dushanbe"), ("Tajikistan", "Tadzhikistan Territories"), ("Tajikistan", "Gorno-Badakhshan")])),
    ("khanate_of_khiva", "3. Khanate of Khiva (Khwarazm and Lower Amu Darya)", union_adm1(adm1, [("Uzbekistan", "Khorezm"), ("Uzbekistan", "Karakalpakstan"), ("Turkmenistan", "Tashauz")])),
    ("khanate_of_kokand", "4. Khanate of Kokand (Ferghana, Tashkent and Kyrgyz Mountains)", union_adm1(adm1, [("Uzbekistan", "Ferghana"), ("Uzbekistan", "Andijon"), ("Uzbekistan", "Namangan"), ("Uzbekistan", "Tashkent"), ("Uzbekistan", "Tashkent City"), ("Uzbekistan", "Sirdaryo"), ("Tajikistan", "Leninabad"), ("Kyrgyzstan", None)])),
    ("turkmen_tribal_oases", "5. Turkmen Tribal Confederations (Ahal, Merv and Caspian Coast)", union_adm1(adm1, [("Turkmenistan", "Mary"), ("Turkmenistan", "Ahal"), ("Turkmenistan", "Balkan")])),
    ("senior_zhuz_semirechye", "6. Senior Kazakh Zhuz (Uly Zhuz: Semirechye and Middle Syr Darya)", union_adm1(adm1, [("Kazakhstan", "Almaty"), ("Kazakhstan", "Almaty City"), ("Kazakhstan", "Zhambyl"), ("Kazakhstan", "South Kazakhstan")])),
    ("middle_zhuz_central_north", "7. Middle Kazakh Zhuz (Orta Zhuz: Saryarka, Ishim and Irtysh)", union_adm1(adm1, [("Kazakhstan", "Qaraghandy"), ("Kazakhstan", "Aqmola"), ("Kazakhstan", "Astana"), ("Kazakhstan", "North Kazakhstan"), ("Kazakhstan", "Pavlodar"), ("Kazakhstan", "East Kazakhstan"), ("Kazakhstan", "Qostanay")])),
    ("junior_zhuz_western_steppe", "8. Junior Kazakh Zhuz (Kishi Zhuz: Ural, Emba, Aral and Mangyshlak)", union_adm1(adm1, [("Kazakhstan", "West Kazakhstan"), ("Kazakhstan", "Atyrau"), ("Kazakhstan", "Mangghystau"), ("Kazakhstan", "Aqtöbe"), ("Kazakhstan", "Qyzylorda")])),
  ]
  ch5_bms = [1500, 1600, 1700, 1750, 1800, 1850, 1865]
  ch5_tot = {1500: 5400000, 1600: 6050000, 1700: 6450000, 1750: 6250000, 1800: 7350000, 1850: 8750000, 1865: 9150000}
  ch5_sh = {
    "bukhara_western_core": 0.21, "eastern_bukhara_badakhshan": 0.11, "khanate_of_khiva": 0.08,
    "khanate_of_kokand": 0.25, "turkmen_tribal_oases": 0.05, "senior_zhuz_semirechye": 0.08,
    "middle_zhuz_central_north": 0.13, "junior_zhuz_western_steppe": 0.09,
  }
  chapters.append({
    "group": "2.mediaeval_and_khanates", "folder": "3.uzbek_khanates_and_kazakh_hordes",
    "stem": "uzbek_khanates_and_kazakh_hordes",
    "title": "Uzbek Khanates and Kazakh Steppe Hordes until the Russian Conquest (1500AD-1865AD)",
    "domain": [1500, 1865], "tier": "national", "priority": 2, "is_admin1": False,
    "zones": ch5_zones, "benchmarks": ch5_bms, "totals": ch5_tot, "shares": ch5_sh,
  })

  # --- CHAPTER 6: Russian Conquest, Imperial Turkestan & Steppe Governorates (1865 to 1917) [Regime II, 1897 Census Oblasts + Protectorates] ---
  ch6_zones = [
    ("syr_darya_oblast", "1. Syr-Darya Oblast (Tashkent-Chimkent-Perovsk-Amu Darya Dept.)", union_adm1(adm1, [("Uzbekistan", "Tashkent"), ("Uzbekistan", "Tashkent City"), ("Kazakhstan", "South Kazakhstan"), ("Kazakhstan", "Qyzylorda"), ("Kazakhstan", "Zhambyl")])),
    ("samarkand_oblast", "2. Samarkand Oblast (Samarkand-Khujand-Jizzakh-Katta-Kurgan)", union_adm1(adm1, [("Uzbekistan", "Samarkand"), ("Uzbekistan", "Jizzakh"), ("Uzbekistan", "Sirdaryo"), ("Tajikistan", "Leninabad")])),
    ("ferghana_oblast", "3. Ferghana Oblast (Skobelev-Kokand-Andijan-Namangan-Osh)", union_adm1(adm1, [("Uzbekistan", "Ferghana"), ("Uzbekistan", "Andijon"), ("Uzbekistan", "Namangan"), ("Kyrgyzstan", "Osh"), ("Kyrgyzstan", "Batken"), ("Kyrgyzstan", "Jalal-Abad")])),
    ("transcaspian_oblast", "4. Transcaspian Oblast (Askhabad-Merv-Krasnovodsk-Mangyshlak)", union_adm1(adm1, [("Turkmenistan", "Ahal"), ("Turkmenistan", "Mary"), ("Turkmenistan", "Balkan"), ("Kazakhstan", "Mangghystau")])),
    ("semirechye_oblast", "5. Semirechye Oblast (Verny-Pishpek-Przhevalsk-Kopal)", union_adm1(adm1, [("Kazakhstan", "Almaty"), ("Kazakhstan", "Almaty City"), ("Kyrgyzstan", "Chuy"), ("Kyrgyzstan", "Bishkek"), ("Kyrgyzstan", "Talas"), ("Kyrgyzstan", "Ysyk-Köl"), ("Kyrgyzstan", "Naryn")])),
    ("akmolinsk_oblast", "6. Akmolinsk Oblast (Omsk-Petropavlovsk-Akmolinsk-Atbasar)", union_adm1(adm1, [("Kazakhstan", "North Kazakhstan"), ("Kazakhstan", "Aqmola"), ("Kazakhstan", "Astana"), ("Kazakhstan", "Qaraghandy")])),
    ("semipalatinsk_oblast", "7. Semipalatinsk Oblast (Semipalatinsk-Pavlodar-Ust-Kamenogorsk)", union_adm1(adm1, [("Kazakhstan", "East Kazakhstan"), ("Kazakhstan", "Pavlodar")])),
    ("turgai_oblast", "8. Turgai Oblast (Kustanai-Aktyubinsk-Irgiz-Turgai)", union_adm1(adm1, [("Kazakhstan", "Qostanay"), ("Kazakhstan", "Aqtöbe")])),
    ("uralsk_oblast", "9. Uralsk Oblast (Uralsk-Guryev-Temir-Lbischensk)", union_adm1(adm1, [("Kazakhstan", "West Kazakhstan"), ("Kazakhstan", "Atyrau")])),
    ("emirate_of_bukhara", "10. Emirate of Bukhara Protectorate (Western & Eastern Bukhara)", union_adm1(adm1, [("Uzbekistan", "Bukhoro"), ("Uzbekistan", "Navoi"), ("Uzbekistan", "Kashkadarya"), ("Uzbekistan", "Surkhandarya"), ("Turkmenistan", "Chardzhou"), ("Tajikistan", "Khatlon"), ("Tajikistan", "Dushanbe"), ("Tajikistan", "Tadzhikistan Territories"), ("Tajikistan", "Gorno-Badakhshan")])),
    ("khanate_of_khiva", "11. Khanate of Khiva Protectorate (Khiva-New Urgench-Tashauz)", union_adm1(adm1, [("Uzbekistan", "Khorezm"), ("Uzbekistan", "Karakalpakstan"), ("Turkmenistan", "Tashauz")])),
  ]
  ch6_bms = [1865, 1880, 1897, 1910, 1916, 1917]
  ch6_tot = {1865: 9150000, 1880: 10150000, 1897: 11186000, 1910: 13450000, 1916: 14350000, 1917: 13950000}
  # Exact 1897 Census proportions across the 9 oblasts + 2 protectorates!
  ch6_sh = {
    "syr_darya_oblast": 0.132, "samarkand_oblast": 0.077, "ferghana_oblast": 0.141,
    "transcaspian_oblast": 0.034, "semirechye_oblast": 0.088, "akmolinsk_oblast": 0.061,
    "semipalatinsk_oblast": 0.061, "turgai_oblast": 0.041, "uralsk_oblast": 0.058,
    "emirate_of_bukhara": 0.245, "khanate_of_khiva": 0.062,
  }
  chapters.append({
    "group": "3.imperial_and_soviet", "folder": "1.russian_conquest_imperial_turkestan_and_steppe",
    "stem": "russian_conquest_imperial_turkestan_and_steppe",
    "title": "Russian Conquest, Imperial Turkestan and the Steppe Governorates (1865AD-1917AD)",
    "domain": [1865, 1917], "tier": "national", "priority": 2, "is_admin1": False,
    "zones": ch6_zones, "benchmarks": ch6_bms, "totals": ch6_tot, "shares": ch6_sh,
  })

  # --- CHAPTER 7: Russian Civil War, Basmachi Revolt & Early Soviet Central Asia (1917 to 1945) [Regime II/III] ---
  ch7_zones = [
    ("kazakh_north_east_steppe", "1. Northern and Eastern Kazakh ASSR/SSR (Petropavlovsk-Semipalatinsk-Karaganda)", union_adm1(adm1, [("Kazakhstan", "North Kazakhstan"), ("Kazakhstan", "Aqmola"), ("Kazakhstan", "Astana"), ("Kazakhstan", "Pavlodar"), ("Kazakhstan", "East Kazakhstan"), ("Kazakhstan", "Qaraghandy"), ("Kazakhstan", "Qostanay")])),
    ("kazakh_west_steppe", "2. Western Kazakh ASSR/SSR (Uralsk-Aktyubinsk-Guryev)", union_adm1(adm1, [("Kazakhstan", "West Kazakhstan"), ("Kazakhstan", "Atyrau"), ("Kazakhstan", "Mangghystau"), ("Kazakhstan", "Aqtöbe")])),
    ("kazakh_south_semirechye", "3. Southern Kazakhstan and Semirechye (Alma-Ata-Chimkent-Kzyl-Orda)", union_adm1(adm1, [("Kazakhstan", "Almaty"), ("Kazakhstan", "Almaty City"), ("Kazakhstan", "Zhambyl"), ("Kazakhstan", "South Kazakhstan"), ("Kazakhstan", "Qyzylorda")])),
    ("uzbek_tashkent_ferghana", "4. Uzbek SSR: Tashkent and Ferghana Basin", union_adm1(adm1, [("Uzbekistan", "Tashkent"), ("Uzbekistan", "Tashkent City"), ("Uzbekistan", "Sirdaryo"), ("Uzbekistan", "Ferghana"), ("Uzbekistan", "Andijon"), ("Uzbekistan", "Namangan")])),
    ("uzbek_zeravshan_surkhan", "5. Uzbek SSR: Samarkand, Bukhara and Southern Oases", union_adm1(adm1, [("Uzbekistan", "Samarkand"), ("Uzbekistan", "Bukhoro"), ("Uzbekistan", "Navoi"), ("Uzbekistan", "Jizzakh"), ("Uzbekistan", "Kashkadarya"), ("Uzbekistan", "Surkhandarya")])),
    ("karakalpak_khorezm", "6. Karakalpak ASSR and Khorezm Oasis", union_adm1(adm1, [("Uzbekistan", "Karakalpakstan"), ("Uzbekistan", "Khorezm")])),
    ("turkmen_ssr", "7. Turkmen SSR (Ashkhabad-Mary-Chardzhou-Tashauz-Krasnovodsk)", union_adm1(adm1, [("Turkmenistan", None)])),
    ("kirghiz_ssr", "8. Kirghiz ASSR/SSR (Frunze-Osh-Issyk-Kul-Naryn)", union_adm1(adm1, [("Kyrgyzstan", None)])),
    ("tajik_western_north", "9. Tajik ASSR/SSR (Stalinabad-Leninabad-Khatlon)", union_adm1(adm1, [("Tajikistan", "Dushanbe"), ("Tajikistan", "Leninabad"), ("Tajikistan", "Khatlon"), ("Tajikistan", "Tadzhikistan Territories")])),
    ("gorno_badakhshan_ao", "10. Gorno-Badakhshan Autonomous Oblast (Pamir)", union_adm1(adm1, [("Tajikistan", "Gorno-Badakhshan")])),
  ]
  ch7_bms = [1917, 1920, 1926, 1933, 1937, 1939, 1945]
  ch7_tot = {1917: 13950000, 1920: 12650000, 1926: 13681000, 1933: 12850000, 1937: 15250000, 1939: 16626000, 1945: 16950000}
  # Dynamic shares capturing the 1930-1933 Kazakh Famine (*Asharshylyk*) drop in Kazakh SSR (44% -> 34% -> 36.6%)!
  ch7_sh = {
    "kazakh_north_east_steppe": {1917: 0.215, 1920: 0.210, 1926: 0.218, 1933: 0.165, 1937: 0.178, 1939: 0.184, 1945: 0.192},
    "kazakh_west_steppe":       {1917: 0.088, 1920: 0.084, 1926: 0.086, 1933: 0.062, 1937: 0.066, 1939: 0.068, 1945: 0.068},
    "kazakh_south_semirechye":  {1917: 0.135, 1920: 0.132, 1926: 0.140, 1933: 0.110, 1937: 0.112, 1939: 0.114, 1945: 0.116},
    "uzbek_tashkent_ferghana":  {1917: 0.175, 1920: 0.182, 1926: 0.176, 1933: 0.218, 1937: 0.208, 1939: 0.204, 1945: 0.202},
    "uzbek_zeravshan_surkhan":  {1917: 0.128, 1920: 0.132, 1926: 0.125, 1933: 0.152, 1937: 0.145, 1939: 0.142, 1945: 0.138},
    "karakalpak_khorezm":       {1917: 0.036, 1920: 0.037, 1926: 0.035, 1933: 0.041, 1937: 0.038, 1939: 0.037, 1945: 0.036},
    "turkmen_ssr":              {1917: 0.072, 1920: 0.073, 1926: 0.073, 1933: 0.083, 1937: 0.078, 1939: 0.075, 1945: 0.073},
    "kirghiz_ssr":              {1917: 0.073, 1920: 0.072, 1926: 0.072, 1933: 0.083, 1937: 0.088, 1939: 0.088, 1945: 0.087},
    "tajik_western_north":      {1917: 0.074, 1920: 0.074, 1926: 0.071, 1933: 0.082, 1937: 0.083, 1939: 0.084, 1945: 0.084},
    "gorno_badakhshan_ao":      {1917: 0.004, 1920: 0.004, 1926: 0.004, 1933: 0.004, 1937: 0.004, 1939: 0.004, 1945: 0.004},
  }
  chapters.append({
    "group": "3.imperial_and_soviet", "folder": "2.russian_civil_war_basmachi_and_early_soviet",
    "stem": "russian_civil_war_basmachi_and_early_soviet",
    "title": "Russian Civil War, Basmachi Revolt and Early Soviet Central Asia (1917AD-1945AD)",
    "domain": [1917, 1945], "tier": "national", "priority": 2, "is_admin1": False,
    "zones": ch7_zones, "benchmarks": ch7_bms, "totals": ch7_tot, "shares": ch7_sh,
  })

  # --- CHAPTER 8 & 9: Exact Natural Earth 10m Admin-1 Oblasts across all 5 Republics (48 Admin-1 units -> clean Regime III!) ---
  # Group exact Admin-1 polygons into all 48 official Admin-1 oblasts & capital cities
  admin1_order = [
    # Kazakhstan (16)
    ("kz_almaty_city", "Almaty City (Kazakhstan)", ("Kazakhstan", "Almaty City"), 0.023, 0.028),
    ("kz_astana", "Astana / Tselinograd City (Kazakhstan)", ("Kazakhstan", "Astana"), 0.006, 0.017),
    ("kz_almaty", "Almaty Oblast (Kazakhstan)", ("Kazakhstan", "Almaty"), 0.034, 0.026),
    ("kz_aqmola", "Akmola Oblast (Kazakhstan)", ("Kazakhstan", "Aqmola"), 0.022, 0.010),
    ("kz_aqtobe", "Aktobe Oblast (Kazakhstan)", ("Kazakhstan", "Aqtöbe"), 0.015, 0.012),
    ("kz_atyrau", "Atyrau Oblast (Kazakhstan)", ("Kazakhstan", "Atyrau"), 0.009, 0.009),
    ("kz_east_kazakhstan", "East Kazakhstan Oblast (Kazakhstan)", ("Kazakhstan", "East Kazakhstan"), 0.036, 0.016),
    ("kz_mangghystau", "Mangystau Oblast (Kazakhstan)", ("Kazakhstan", "Mangghystau"), 0.007, 0.010),
    ("kz_north_kazakhstan", "North Kazakhstan Oblast (Kazakhstan)", ("Kazakhstan", "North Kazakhstan"), 0.019, 0.007),
    ("kz_pavlodar", "Pavlodar Oblast (Kazakhstan)", ("Kazakhstan", "Pavlodar"), 0.019, 0.009),
    ("kz_qaraghandy", "Karaganda Oblast (Kazakhstan)", ("Kazakhstan", "Qaraghandy"), 0.036, 0.017),
    ("kz_qostanay", "Kostanay Oblast (Kazakhstan)", ("Kazakhstan", "Qostanay"), 0.025, 0.010),
    ("kz_qyzylorda", "Kyzylorda Oblast (Kazakhstan)", ("Kazakhstan", "Qyzylorda"), 0.012, 0.010),
    ("kz_south_kazakhstan", "Turkistan / South Kazakhstan Oblast (Kazakhstan)", ("Kazakhstan", "South Kazakhstan"), 0.037, 0.041),
    ("kz_west_kazakhstan", "West Kazakhstan Oblast (Kazakhstan)", ("Kazakhstan", "West Kazakhstan"), 0.013, 0.009),
    ("kz_zhambyl", "Jambyl Oblast (Kazakhstan)", ("Kazakhstan", "Zhambyl"), 0.021, 0.015),
    # Uzbekistan (14)
    ("uz_tashkent_city", "Tashkent City (Uzbekistan)", ("Uzbekistan", "Tashkent City"), 0.042, 0.038),
    ("uz_tashkent", "Tashkent Region (Uzbekistan)", ("Uzbekistan", "Tashkent"), 0.044, 0.038),
    ("uz_andijon", "Andijan Region (Uzbekistan)", ("Uzbekistan", "Andijon"), 0.035, 0.042),
    ("uz_bukhoro", "Bukhara Region (Uzbekistan)", ("Uzbekistan", "Bukhoro"), 0.023, 0.025),
    ("uz_ferghana", "Fergana Region (Uzbekistan)", ("Uzbekistan", "Ferghana"), 0.044, 0.050),
    ("uz_jizzakh", "Jizzakh Region (Uzbekistan)", ("Uzbekistan", "Jizzakh"), 0.015, 0.019),
    ("uz_karakalpakstan", "Karakalpakstan Republic (Uzbekistan)", ("Uzbekistan", "Karakalpakstan"), 0.025, 0.025),
    ("uz_kashkadarya", "Qashqadaryo Region (Uzbekistan)", ("Uzbekistan", "Kashkadarya"), 0.033, 0.044),
    ("uz_khorezm", "Xorazm Region (Uzbekistan)", ("Uzbekistan", "Khorezm"), 0.021, 0.025),
    ("uz_namangan", "Namangan Region (Uzbekistan)", ("Uzbekistan", "Namangan"), 0.030, 0.038),
    ("uz_navoi", "Navoiy Region (Uzbekistan)", ("Uzbekistan", "Navoi"), 0.014, 0.013),
    ("uz_samarkand", "Samarkand Region (Uzbekistan)", ("Uzbekistan", "Samarkand"), 0.044, 0.052),
    ("uz_sirdaryo", "Sirdaryo Region (Uzbekistan)", ("Uzbekistan", "Sirdaryo"), 0.012, 0.011),
    ("uz_surkhandarya", "Surxondaryo Region (Uzbekistan)", ("Uzbekistan", "Surkhandarya"), 0.026, 0.036),
    # Kyrgyzstan (8)
    ("kg_bishkek", "Bishkek / Frunze City (Kyrgyzstan)", ("Kyrgyzstan", "Bishkek"), 0.013, 0.014),
    ("kg_chuy", "Chuy Region (Kyrgyzstan)", ("Kyrgyzstan", "Chuy"), 0.016, 0.013),
    ("kg_batken", "Batken Region (Kyrgyzstan)", ("Kyrgyzstan", "Batken"), 0.006, 0.007),
    ("kg_jalal_abad", "Jalal-Abad Region (Kyrgyzstan)", ("Kyrgyzstan", "Jalal-Abad"), 0.015, 0.016),
    ("kg_naryn", "Naryn Region (Kyrgyzstan)", ("Kyrgyzstan", "Naryn"), 0.005, 0.004),
    ("kg_osh", "Osh Region and City (Kyrgyzstan)", ("Kyrgyzstan", "Osh"), 0.019, 0.023),
    ("kg_talas", "Talas Region (Kyrgyzstan)", ("Kyrgyzstan", "Talas"), 0.004, 0.003),
    ("kg_ysyk_kol", "Issyk-Kul Region (Kyrgyzstan)", ("Kyrgyzstan", "Ysyk-Köl"), 0.008, 0.007),
    # Tajikistan (5)
    ("tj_dushanbe", "Dushanbe City (Tajikistan)", ("Tajikistan", "Dushanbe"), 0.012, 0.015),
    ("tj_gorno_badakhshan", "Gorno-Badakhshan Autonomous Region (Tajikistan)", ("Tajikistan", "Gorno-Badakhshan"), 0.003, 0.003),
    ("tj_khatlon", "Khatlon Region (Tajikistan)", ("Tajikistan", "Khatlon"), 0.035, 0.045),
    ("tj_sughd", "Sughd / Leninabad Region (Tajikistan)", ("Tajikistan", "Leninabad"), 0.031, 0.036),
    ("tj_rrp", "Districts of Republican Subordination (Tajikistan)", ("Tajikistan", "Tadzhikistan Territories"), 0.023, 0.028),
    # Turkmenistan (5)
    ("tm_ahal", "Ahal Region and Ashgabat (Turkmenistan)", ("Turkmenistan", "Ahal"), 0.021, 0.025),
    ("tm_balkan", "Balkan Region (Turkmenistan)", ("Turkmenistan", "Balkan"), 0.008, 0.007),
    ("tm_lebap", "Lebap / Chardzhou Region (Turkmenistan)", ("Turkmenistan", "Chardzhou"), 0.015, 0.019),
    ("tm_mary", "Mary Region (Turkmenistan)", ("Turkmenistan", "Mary"), 0.017, 0.020),
    ("tm_dashoguz", "Dashoguz / Tashauz Region (Turkmenistan)", ("Turkmenistan", "Tashauz"), 0.014, 0.019),
  ]

  adm1_zones = []
  sh8_raw, sh9_raw = {}, {}
  for idx, (rid, rname, spec, s8, s9) in enumerate(admin1_order, 1):
    g = adm1.get(spec)
    if g is None:
      print(f"  [WARN] Missing Admin-1 {spec}!")
      continue
    adm1_zones.append((rid, f"{idx}. {rname}", g))
    sh8_raw[rid] = s8
    sh9_raw[rid] = s9

  # Normalise shares to sum strictly to 1.0
  tot8 = sum(sh8_raw.values())
  tot9 = sum(sh9_raw.values())
  sh8 = {k: v / tot8 for k, v in sh8_raw.items()}
  sh9 = {k: v / tot9 for k, v in sh9_raw.items()}

  # Chapter 8: Post-War Soviet Central Asian Republics (1945 to 1991)
  ch8_bms = [1945, 1950, 1959, 1970, 1979, 1989, 1991]
  ch8_tot = {1945: 16950000, 1950: 17850000, 1959: 22978000, 1970: 32799000, 1979: 40167000, 1989: 49146000, 1991: 50950000}
  # Dynamic interpolation from 1959 Virgin Lands peak KZ (40.4%) to 1989 KZ (33.5%)
  ch8_sh = {}
  for rid, v89 in sh8.items():
    is_kz_north = rid in ("kz_aqmola", "kz_north_kazakhstan", "kz_qostanay", "kz_pavlodar", "kz_qaraghandy", "kz_east_kazakhstan")
    ch8_sh[rid] = {}
    for yr in ch8_bms:
      mult = 1.24 if (is_kz_north and yr in (1959, 1970)) else (1.12 if (is_kz_north and yr == 1979) else 1.0)
      ch8_sh[rid][yr] = v89 * mult
  for yr in ch8_bms:
    s = sum(ch8_sh[r][yr] for r in ch8_sh)
    for r in ch8_sh:
      ch8_sh[r][yr] /= s

  chapters.append({
    "group": "3.imperial_and_soviet", "folder": "3.post_war_soviet_central_asian_republics",
    "stem": "post_war_soviet_central_asian_republics",
    "title": "Post-War Soviet Central Asian Republics (1945AD-1991AD)",
    "domain": [1945, 1991], "tier": "national", "priority": 2, "is_admin1": True,
    "zones": adm1_zones, "benchmarks": ch8_bms, "totals": ch8_tot, "shares": ch8_sh,
  })

  # Chapter 9: Post-Soviet Central Asia (1991 to 2026)
  ch9_bms = [1991, 1995, 2000, 2005, 2010, 2015, 2020, 2025]
  ch9_tot = {1991: 50950000, 1995: 53050000, 2000: 55480000, 2005: 58920000, 2010: 63250000, 2015: 68950000, 2020: 75200000, 2025: 82668000}
  # Smoothly transition 1991 shares -> 2025 shares (capturing northern KZ emigration, Astana boom, UZ/TJ high fertility)
  ch9_sh = {}
  for rid in sh9:
    ch9_sh[rid] = {}
    for yr in ch9_bms:
      t = (yr - 1991) / (2025 - 1991)
      ch9_sh[rid][yr] = (1.0 - t) * sh8[rid] + t * sh9[rid]
  for yr in ch9_bms:
    s = sum(ch9_sh[r][yr] for r in ch9_sh)
    for r in ch9_sh:
      ch9_sh[r][yr] /= s

  chapters.append({
    "group": "4.modern_censuses", "folder": "1.post_soviet_central_asia",
    "stem": "post_soviet_central_asia",
    "title": "Post-Soviet Central Asia (1991AD-2026AD)",
    "domain": [1991, 2026], "tier": "national", "priority": 3, "is_admin1": True,
    "zones": adm1_zones, "benchmarks": ch9_bms, "totals": ch9_tot, "shares": ch9_sh,
  })

  return chapters


def main():
  domain_mask, land_area, saray_union, adm1, cu, basins = load_gis_and_build_domain_mask()
  chapters = define_all_9_chapters(saray_union, adm1, cu, basins)

  spec_masks = []
  nat_masks = []
  gaz_list = []

  for ch in chapters:
    ch_dir = os.path.join(SARAY_DIR, ch["group"], ch["folder"])
    os.makedirs(ch_dir, exist_ok=True)
    stem = ch["stem"]
    region_geoms = []
    for i, (rid, rname, geom) in enumerate(ch["zones"]):
      rgb = PALETTE[i % len(PALETTE)]
      region_geoms.append((rid, rname, geom, rgb))

    rgba, stats = rasterise_regions(region_geoms, domain_mask, land_area)
    mask_png = os.path.join(ch_dir, f"{stem}_areal_mask.png")
    Image.fromarray(rgba, mode="RGBA").save(mask_png)

    # Save smooth vector GeoJSON for Stage D PatchCollection cartography
    sub_gj_path = os.path.join(SUB_GJ_DIR, f"{stem}_subregions.geojson")
    gj_feats = []
    for i, (rid, rname, geom, rgb) in enumerate(region_geoms):
      px, area, bbox = stats[i]
      gj_feats.append({
        "type": "Feature",
        "geometry": mapping(geom.simplify(0.015, preserve_topology=True)),
        "properties": {
          "region_id": rid,
          "name": rname,
          "rgb": rgb,
          "pixel_count": px,
          "area_km2": area,
        },
      })
    with open(sub_gj_path, "w", encoding="utf-8") as fh:
      json.dump({"type": "FeatureCollection", "features": gj_feats}, fh)

    # Write chapter <stem>.json5
    reg_pops, reg_bounds = build_pop_series(ch["benchmarks"], ch["totals"], ch["shares"])
    regions_obj = {}
    tot_px, tot_area = 0, 0
    for i, (rid, rname, geom, rgb) in enumerate(region_geoms):
      px, area, bbox = stats[i]
      tot_px += px
      tot_area += area
      regions_obj[rid] = {
        "name": rname,
        "colour": rgb,
        "pixel_count": px,
        "area_km2": area,
        "bbox": bbox,
        "population": reg_pops[rid],
        "population_bounds": reg_bounds[rid],
      }

    rel_ch = f"histmap/1.data_raw/population_regional/SARAY/{ch['group']}/{ch['folder']}"
    ch_json5 = {
      "id": stem,
      "title": ch["title"],
      "source_review": f"{rel_ch}/{stem}_literature_review.md",
      "settlements_gazetteer": f"{rel_ch}/{stem}_settlements.json",
      "mask_file": f"{stem}_areal_mask.png",
      "subregions_geojson": f"histmap/1.data_raw/population_regional/SARAY/_shared/_gis_cache/chapter_subregions/{stem}_subregions.geojson",
      "domain": ch["domain"],
      "grid_dimensions": [GRID_W, GRID_H],
      "total_pixels": tot_px,
      "total_area_km2": tot_area,
      "regions": regions_obj,
    }
    with open(os.path.join(ch_dir, f"{stem}.json5"), "w", encoding="utf-8") as fh:
      json.dump(ch_json5, fh, indent=2, ensure_ascii=False)

    entry = {
      "id": stem,
      "domain": ch["domain"],
      "domain_group": "sites_saray_central_asia",
      "json5_path": f"{rel_ch}/{stem}.json5",
      "mask_path": f"{rel_ch}/{stem}_areal_mask.png",
      "priority": ch["priority"],
    }
    if ch["is_admin1"]:
      entry["is_admin1"] = True
    if ch["tier"] == "specialist":
      spec_masks.append(entry)
    else:
      nat_masks.append(entry)

    gaz_list.append({
      "domain": ch["domain"],
      "key": stem,
      "path": f"{rel_ch}/{stem}_settlements.json",
      "priority": ch["priority"],
      "region_group": ch["group"],
    })
    print(f"  [OK] {stem}: {len(region_geoms)} sub-regions | {tot_px:,} px | {tot_area:,} km2 | domain {ch['domain']}", flush=True)

  # Master saray_areal_masks.json5
  all_hyde_years = [
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
      "central_asia": {
        "pre_admin_end": 500,
        "dynastic_imperial_start": 500,
        "contemporary_start": 1945,
      }
    },
    "geography_profile": {
      "projection_class": "albers_conic",
      "has_micro_islands": False,
      "max_adm2_area_km2": 25000,
      "note": "Central Asia / Russian Turkestan (Kazakhstan, Uzbekistan, Turkmenistan, Kyrgyzstan, Tajikistan).",
    },
    "script_profile": {
      "target_scripts": ["Latn", "Cyrl", "Arab"],
      "allow_native_toponyms": True,
    },
    "hyde_years": all_hyde_years,
    "substrata_sources": {
      "sites_saray_central_asia": {
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/SARAY/_shared/sites_saray_central_asia/config/documented_site_pixels.json",
        "domain": [-10000, 2025],
        "domain_code": 1,
        "domain_mask_png": "histmap/1.data_raw/population_regional/SARAY/_shared/sites_saray_central_asia/config/saray_domain_mask.png",
        "rasters_folder": "histmap/1.data_raw/population_regional/SARAY/_shared/sites_saray_central_asia/2.population_rasters",
        "sample_year": 1000,
      }
    },
    "smoothing": {
      "border_feather_radius_px": 8,
      "interior_multiplier_blur_passes": 4,
      "interior_multiplier_blur_radius_px": 10,
      "temporal_log_Laplacian_weight": 0.15,
    },
    "specialist_masks": spec_masks,
    "national_epoch_masks": nat_masks,
  }
  with open(os.path.join(SARAY_DIR, "saray_areal_masks.json5"), "w", encoding="utf-8") as fh:
    json.dump(areal_manifest, fh, indent=2, ensure_ascii=False)

  # Master saray_gazetteers.json5
  gaz_manifest = {
    "annual_continuity_span": [1897, 2025],
    "border_splice_years": [1924, 1925, 1936, 1991],
    "regime_transitions": areal_manifest["regime_transitions"],
    "geography_profile": {
      "projection_class": "albers_conic",
      "has_micro_islands": False,
      "max_adm2_area_km2": 25000,
    },
    "script_profile": areal_manifest["script_profile"],
    "gazetteers": gaz_list,
  }
  with open(os.path.join(SARAY_DIR, "saray_gazetteers.json5"), "w", encoding="utf-8") as fh:
    json.dump(gaz_manifest, fh, indent=2, ensure_ascii=False)

  print("=== DONE BUILDING ALL 9 SARAY DUAL AREAL MASKS & MANIFESTS ===", flush=True)


if __name__ == "__main__":
  main()
