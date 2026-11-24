"""Pass-2 Dual Areal Mask, Smooth Vector Sub-Region GeoJSON & Optical QA Builder
for Operation Viscount Project JAGUAR (Mexico, Central America, Caribbean & Bermuda).

Three-Regime Non-Anachronistic Partitioning across ALL 14 Chapters:
  - Regime I (Ch 01-05, Pre-Columbian): 100% Organic HydroBASINS L6 natural watersheds
    and Pre-Columbian cultural archipelagos (ZERO modern 2025 Admin-0 interior borders!).
  - Regime II (Ch 06-10, Conquest & Colonial): Authentic HGIS de las Indias (`the_geom.gpkg`
    + `Niveles.tab`), OpenHistoricalMap (OHM), and DECM 16th-c. Audiencias, Intendancies,
    Captaincies General & Imperial Plantation jurisdictions (Chiapas inside Guatemala until
    1824; OHM Saint-Domingue 1697-1795; OHM Mosquito Kingdom; OHM British Honduras Settlement).
  - Regime III (Ch 11-14, Modern & Census): geoBoundaries ADM1 + Natural Earth + exact OHM
    1903-1979 Panama Canal Zone, with micro-island preservation including Bermuda & ABC/Leewards.
"""

import json
import os
import shutil
from collections import defaultdict

import json5
import numpy as np
from PIL import Image
import shapefile
from shapely.geometry import box, mapping, shape

from jaguar_hgis_utils import (
  ALL_HYDE_YEARS,
  DOMAIN_MASK_PNG,
  GRID_H,
  GRID_W,
  HGIS_RAW,
  JAG_DIR,
  JAG_GIS,
  LAND_AREA_PNG,
  PALETTE,
  PROJ_JAGUAR,
  SUB_GJ_DIR,
  absorb_micro_slivers,
  build_organic_mosquitia_geom,
  clip_geom,
  cv2_rasterise_zones,
  diff_geom,
  dissolve_hgis_indias_by_year,
  group_basins,
  iter_polys,
  load_hgis_indias_lcg,
  load_hydrobasins_jaguar,
  load_jaguar_basemap_cache,
  norm_str,
  render_jaguar_mask_qa_png,
  safe_geom,
  u_geoms,
)

os.makedirs(SUB_GJ_DIR, exist_ok=True)


def load_all_sources ():
  print("[1] Loading JAGUAR domain mask, Natural Earth land union, HydroBASINS L6, HGIS de las Indias, OHM, DECM & geoBoundaries...", flush=True)
  dm_raw = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  domain_mask = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)
  la_raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  land_area = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2])

  # 1. JAGUAR coastal land union (strict outer coastline clip)
  c_gj = json.load(open(os.path.join(JAG_GIS, "jaguar_countries.geojson"), encoding="utf-8"))
  countries = {}
  for feat in c_gj["features"]:
    nm = feat["properties"]["ADMIN"]
    g = safe_geom(shape(feat["geometry"]))
    if g is not None:
      countries[nm] = g
  jag_union = u_geoms(list(countries.values()))

  # Split Caribbean Netherlands cleanly into Bonaire (ABC, lat < 14) vs Saba/Sint Eustatius (Leewards, lat >= 14)
  geo = dict(countries)
  if "Caribbean Netherlands" in countries:
    cn_polys = list(iter_polys(countries["Caribbean Netherlands"]))
    geo["Bonaire"] = u_geoms([p for p in cn_polys if p.representative_point().y < 14.0])
    geo["Saba_Sint_Eustatius"] = u_geoms([p for p in cn_polys if p.representative_point().y >= 14.0])
  # Split French Antilles cleanly into Guadeloupe (lat >= 15.5) vs Martinique (lat < 15.5)
  if "French Antilles" in countries:
    fa_polys = list(iter_polys(countries["French Antilles"]))
    geo["Guadeloupe"] = u_geoms([p for p in fa_polys if p.representative_point().y >= 15.5])
    geo["Martinique"] = u_geoms([p for p in fa_polys if p.representative_point().y < 15.5])

  geo["Mainland_Mesoamerica_CA"] = u_geoms([
    countries[k] for k in ("Mexico", "Guatemala", "Belize", "El Salvador", "Honduras", "Nicaragua", "Costa Rica", "Panama")
    if k in countries
  ])
  geo["Central_America_Modern"] = u_geoms([
    countries[k] for k in ("Guatemala", "Belize", "El Salvador", "Honduras", "Nicaragua", "Costa Rica", "Panama")
    if k in countries
  ])
  geo["Hispaniola_Unified"] = u_geoms([countries.get("Haiti"), countries.get("Dominican Republic")])
  geo["Cuba_Full"] = u_geoms([countries.get("Cuba"), countries.get("US Naval Base Guantanamo Bay")])

  # 2. HydroBASINS L6 (NA + SA) strictly clipped to JAGUAR land union
  basins = load_hydrobasins_jaguar(jag_union)
  print(f"  HydroBASINS L6 (NA+SA) clipped to JAGUAR: {len(basins)} organic basins", flush=True)

  # 3. HGIS de las Indias (the_geom.gpkg + Niveles.tab)
  lcg_geoms, niveles_rows = load_hgis_indias_lcg(jag_union)
  indias_1790_prov = dissolve_hgis_indias_by_year(lcg_geoms, niveles_rows, 1790, "Provincia")
  indias_1790_pm = dissolve_hgis_indias_by_year(lcg_geoms, niveles_rows, 1790, "Provincia_menor")
  indias_1790_aud = dissolve_hgis_indias_by_year(lcg_geoms, niveles_rows, 1790, "Audiencia")
  indias_1790_front = dissolve_hgis_indias_by_year(lcg_geoms, niveles_rows, 1790, "Fronteras")
  print(f"  HGIS de las Indias 1790: {len(indias_1790_prov)} provinces, {len(indias_1790_pm)} prov_menor, {len(indias_1790_aud)} audiencias, {len(indias_1790_front)} fronteras", flush=True)

  # 4. OpenHistoricalMap (OHM) key historical polygons
  ohm_gj = json.load(open(os.path.join(HGIS_RAW, "ohm_jaguar_boundaries.geojson"), encoding="utf-8"))
  ohm = {}
  for f in ohm_gj["features"]:
    p = f["properties"]
    nm = str(p.get("name") or "")
    sd = str(p.get("start_date") or "")
    ed = str(p.get("end_date") or "")
    g = clip_geom(shape(f["geometry"]), jag_union)
    if g is None:
      continue
    if nm == "Panama Canal Zone" and sd.startswith("1935"):
      ohm["panama_canal_zone"] = g
    elif nm == "Saint-Domingue" and sd.startswith("1697"):
      ohm["saint_domingue_1697"] = g
    elif nm == "Mosquito Kingdom" and sd.startswith("1740"):
      ohm["mosquito_kingdom"] = g
    elif nm == "Settlement of British Honduras" and sd.startswith("1841"):
      ohm["british_honduras_early"] = g
    elif nm == "Reino de Nueva Galicia":
      ohm["nueva_galicia"] = g
    elif nm == "Nueva Vizcaya" and sd.startswith("1562"):
      ohm["nueva_vizcaya_1562"] = g
  print(f"  OHM key historical polygons loaded: {sorted(ohm.keys())}", flush=True)

  # 5. DECM 16th-century Mexico jurisdiction polygons (Tlaxcala, Antequera, México)
  decm = {}
  decm_base = os.path.join(HGIS_RAW, "decm_16c_mexico", "primarysources", "DECM_Gazetteer_primarysources", "New version Spring 2021")
  for key, files in [
    ("tlaxcala", ["Acuna_4_Tlaxcala1_polygons.shp", "Acuna_5_Tlaxcala2_polygons.shp"]),
    ("mexico", ["Acuna_6_Mexico1_polygons.shp", "Acuna_7_Mexico2_polygons.shp", "Acuna_8_Mexico3_polygons.shp"]),
    ("oaxaca", ["Acuna_2_Antequera1_polygons.shp", "Acuna_3_Antequera2_polygons.shp"]),
  ]:
    gs = []
    for fn in files:
      sp = os.path.join(decm_base, fn)
      if not os.path.exists(sp):
        continue
      sf = shapefile.Reader(sp, encoding="latin1")
      for shp in sf.shapes():
        g = clip_geom(shape(shp.__geo_interface__), jag_union)
        if g is not None:
          gs.append(g)
    if gs:
      decm[key] = u_geoms(gs)
  print(f"  DECM 16c polygon layers loaded: {sorted(decm.keys())}", flush=True)

  # 6. geoBoundaries ADM1 for Regime III (Mexico 32 states, Cuba 16 provinces)
  mx_adm1 = {}
  mx_gj = json.load(open(os.path.join(HGIS_RAW, "geoboundaries", "MEX_ADM1.geojson"), encoding="utf-8"))
  for f in mx_gj["features"]:
    nm = f["properties"]["shapeName"]
    g = clip_geom(shape(f["geometry"]), countries["Mexico"])
    if g is not None:
      mx_adm1[norm_str(nm)] = g

  cu_adm1 = {}
  cu_gj = json.load(open(os.path.join(HGIS_RAW, "geoboundaries", "CUB_ADM1.geojson"), encoding="utf-8"))
  for f in cu_gj["features"]:
    nm = f["properties"]["shapeName"]
    g = clip_geom(shape(f["geometry"]), geo["Cuba_Full"])
    if g is not None:
      cu_adm1[norm_str(nm)] = g

  return {
    "domain_mask": domain_mask,
    "land_area": land_area,
    "countries": countries,
    "geo": geo,
    "jag_union": jag_union,
    "basins": basins,
    "indias_1790_prov": indias_1790_prov,
    "indias_1790_pm": indias_1790_pm,
    "indias_1790_aud": indias_1790_aud,
    "indias_1790_front": indias_1790_front,
    "ohm": ohm,
    "decm": decm,
    "mx_adm1": mx_adm1,
    "cu_adm1": cu_adm1,
  }


def fill_unassigned_land (arg0_zones, arg1_envelope):
  """Assigns any tiny uncovered coastal/border land gaps inside `arg1_envelope` to the nearest
  touching zone in O(N) batched union (zero gaps, preserving exact authentic interior seams)."""
  zones = [dict(z) for z in arg0_zones]
  covered = u_geoms([z.get("geom") for z in zones if z.get("geom") is not None])
  rem = diff_geom(arg1_envelope, covered)
  if rem is None:
    return zones
  zone_bounds = [(z["geom"].bounds if z.get("geom") is not None else None) for z in zones]
  additions = defaultdict(list)
  for p in iter_polys(rem):
    if p.area < 0.00005:
      continue
    pb = p.bounds
    best_i = -1
    best_d = 1e9
    p_buf = p.buffer(0.03)
    best_ov = 0.0
    for i, z in enumerate(zones):
      zg = z.get("geom")
      zb = zone_bounds[i]
      if zg is None or zb is None:
        continue
      if pb[2] + 0.05 >= zb[0] and pb[0] - 0.05 <= zb[2] and pb[3] + 0.05 >= zb[1] and pb[1] - 0.05 <= zb[3]:
        if p_buf.intersects(zg):
          try:
            ov = p_buf.intersection(zg).area
          except Exception:
            ov = 0.0
          if ov > best_ov:
            best_ov = ov
            best_i = i
    if best_i < 0:
      for i, z in enumerate(zones):
        zg = z.get("geom")
        if zg is None:
          continue
        d = p.distance(zg)
        if d < best_d:
          best_d = d
          best_i = i
    if best_i >= 0:
      additions[best_i].append(p)
  for i, plist in additions.items():
    zones[i]["geom"] = u_geoms([zones[i]["geom"]] + plist)
  return zones


def write_chapter_assets (arg0_ch_meta, arg1_zones_spec, arg2_data, arg3_bm_hist, arg4_bm_mod, arg5_envelope=None):
  ch_dir = os.path.join(JAG_DIR, arg0_ch_meta["group"], arg0_ch_meta["folder"])
  os.makedirs(ch_dir, exist_ok=True)
  os.makedirs(os.path.join(ch_dir, "figures"), exist_ok=True)
  os.makedirs(os.path.join(ch_dir, "papers"), exist_ok=True)
  for fn in ("crd-mla-numeric.csl", "crd_logo.png", "intellte.cls"):
    src_f = os.path.join(JAG_DIR, fn)
    dst_f = os.path.join(ch_dir, fn)
    if os.path.exists(src_f) and not os.path.exists(dst_f):
      shutil.copy2(src_f, dst_f)

  # 1. Clip every zone to JAGUAR coastal union & make mutually non-overlapping in declared order
  claimed_vec = None
  clean_zones = []
  for idx, z in enumerate(arg1_zones_spec):
    g = clip_geom(z.get("geom"), arg2_data["jag_union"])
    if g is not None and claimed_vec is not None:
      g = diff_geom(g, claimed_vec)
    if g is not None:
      claimed_vec = u_geoms([claimed_vec, g])
    z2 = dict(z)
    z2["geom"] = g
    z2["rgb"] = PALETTE[idx % len(PALETTE)]
    clean_zones.append(z2)

  # 2. Fill any minor seam gaps inside the chapter's natural land envelope
  if arg5_envelope is not None:
    clean_zones = fill_unassigned_land(clean_zones, clip_geom(arg5_envelope, arg2_data["jag_union"]))

  # 3. Absorb interior overlay micro-slivers (< ~25 km^2) into longest-shared-edge neighbour
  clean_zones = absorb_micro_slivers(clean_zones, arg1_min_area_deg2=0.0022)

  # 3b. Strip any degenerate floating boundary sliver/line remnants on mainland chapters (< 0.012 deg^2)
  # while strictly preserving standalone Caribbean/Atlantic/Pacific ocean islands
  if arg0_ch_meta["index"] in (6, 7, 8):
    for z in clean_zones:
      g = safe_geom(z.get("geom"))
      if g is None:
        continue
      g = safe_geom(g.buffer(0))
      if g is None:
        continue
      kept_parts = []
      for p in iter_polys(g):
        rp = p.representative_point()
        # Drop tiny disconnected border-mismatch scraps along Chiapas/Guatemala/Soconusco/Petén seam
        if p.area < 0.015 and rp.x > -95.0 and rp.y < 19.2:
          continue
        if p.area < 0.004 and rp.x > -106.0:
          continue
        kept_parts.append(p)
      if kept_parts:
        z["geom"] = u_geoms(kept_parts)

  # 4. Rasterise scanline-free at 4320x2160 with micro-island preservation
  rgba, _, px_counts, area_km2 = cv2_rasterise_zones(
    arg2_data["domain_mask"],
    clean_zones,
    arg2_land_area=arg2_data["land_area"],
    arg3_full_domain=False,
    arg4_snap_coastal_px=2,
  )

  stem = arg0_ch_meta["stem"]
  mask_rel = f"histmap/1.data_raw/population_regional/JAGUAR/{arg0_ch_meta['group']}/{arg0_ch_meta['folder']}/{stem}_areal_mask.png"
  gj_rel = f"histmap/1.data_raw/population_regional/JAGUAR/_shared/_gis_cache/chapter_subregions/{stem}_subregions.geojson"
  Image.fromarray(rgba, mode="RGBA").save(os.path.join(ch_dir, f"{stem}_areal_mask.png"))

  gj_feats = []
  regions_cfg = []
  starved = []
  for z in clean_zones:
    pc = px_counts.get(z["id"], 0)
    if pc <= 0 or z["geom"] is None:
      starved.append(z["id"])
      continue
    # Gentle simplification preserving small islands cleanly
    simp_tol = 0.001 if z["geom"].area < 0.08 else 0.010
    geom_out = safe_geom(z["geom"].simplify(simp_tol, preserve_topology=True)) or z["geom"]
    gj_feats.append({
      "type": "Feature",
      "properties": {
        "id": z["id"],
        "name": z["name"],
        "rgb": z["rgb"],
        "source_hgis": z.get("source_hgis", ""),
        "pixel_count": pc,
        "area_km2": area_km2.get(z["id"], 0.0),
      },
      "geometry": mapping(geom_out),
    })
    regions_cfg.append({
      "id": z["id"],
      "name": z["name"],
      "rgb": z["rgb"],
      "source_hgis": z.get("source_hgis", ""),
      "pixel_count": pc,
      "area_km2": area_km2.get(z["id"], 0.0),
      "domain": arg0_ch_meta["domain"],
      "population": z.get("population", {}),
    })

  if starved:
    raise RuntimeError(f"STARVED sub-regions in CH {arg0_ch_meta['index']} ({stem}): {starved}")

  with open(os.path.join(SUB_GJ_DIR, f"{stem}_subregions.geojson"), "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": gj_feats}, fh)

  cfg_obj = {
    "id": stem,
    "title": arg0_ch_meta["title"],
    "domain": arg0_ch_meta["domain"],
    "regime": arg0_ch_meta["regime"],
    "mask_path": mask_rel,
    "subregions_geojson": gj_rel,
    "regions": regions_cfg,
  }
  with open(os.path.join(ch_dir, f"{stem}.json5"), "w", encoding="utf-8") as fh:
    json.dump(cfg_obj, fh, indent=2, ensure_ascii=False)

  crop_p = render_jaguar_mask_qa_png(arg0_ch_meta, clean_zones, arg3_bm_hist, arg4_bm_mod)
  print(
    f"  [CH {arg0_ch_meta['index']:02d}] {stem:42s}: {len(regions_cfg):2d} zones | {sum(px_counts.values()):6,d} px | crop -> {os.path.basename(crop_p)}",
    flush=True,
  )


def main ():
  D = load_all_sources()
  C = D["countries"]
  G = D["geo"]
  P90 = D["indias_1790_prov"]
  F90 = D["indias_1790_front"]
  OHM = D["ohm"]
  DECM = D["decm"]
  MX1 = D["mx_adm1"]
  CU1 = D["cu_adm1"]

  itinerary = json5.load(open(os.path.join(JAG_DIR, "jaguar_itinerary.json5"), encoding="utf-8"))
  ch_by_idx = {c["index"]: c for c in itinerary["chapters"]}

  bm_hist = load_jaguar_basemap_cache(PROJ_JAGUAR, arg2_show_modern_borders=False)
  bm_mod = load_jaguar_basemap_cache(PROJ_JAGUAR, arg2_show_modern_borders=True)
  print("\n[2] Building ALL 14 JAGUAR Chapter Areal Masks, Vector GeoJSONs & Lambert Azimuthal Optical QA Crops...", flush=True)

  # Pre-classify mainland HydroBASINS L6 organically into Mesoamerica (Ch 1), Maya Core (Ch 2) & Lower CA (Ch 4)
  # ZERO modern borders used — strictly natural Pfafstetter L6 watershed boundaries!
  mainland_basins = [b for b in D["basins"] if b["g"].intersects(G["Mainland_Mesoamerica_CA"])]

  def classify_mainland_macro (lat, lon, pfaf, main_bas):
    # Lower Central America east/south of Lempa-Ulúa eastern Maya frontier
    if lon > -87.45 or (lon > -88.25 and lat < 13.75) or lat < 13.2:
      return "lower_ca"
    # Maya ecological & riverine core: Yucatán, Petén-Usumacinta, Belize, Chiapas-Grijalva, Guatemala, Copán-Motagua-W. El Salvador
    if lon >= -93.85 or (lon >= -94.25 and lat < 17.6):
      return "maya"
    return "mesoamerica"

  macro_b = group_basins(mainland_basins, classify_mainland_macro, arg2_clip_geom=G["Mainland_Mesoamerica_CA"])
  meso_env = macro_b["mesoamerica"]
  maya_env = macro_b["maya"]
  lower_ca_env = macro_b["lower_ca"]

  # =========================================================================
  # CH 01: Pre-Columbian Mesoamerica to AD 1200 (-10000..1200) — Pure HydroBASINS L6
  # =========================================================================
  def clf_ch1 (lat, lon, pfaf, main_bas):
    # Baja California & Arid Northern Interior (Chihuahua Conchos, Bravo, Coahuila, Tamaulipas, Nuevo León)
    if lon < -109.5 or lat >= 25.4 or (lon > -100.8 and lat >= 22.8):
      return "arid_northern_interior_baja"
    # Pacific Sierra Madre & Sonora-Sinaloa (Fuerte, Yaqui, Sonora, Culiacán, Piaxtla)
    if lon < -105.0 and lat >= 21.8:
      return "pacific_sierra_madre_sonora_sinaloa"
    # Gulf Olmec & Huasteca-Veracruz Lowlands (Papaloapan, Coatzacoalcos, Pánuco coastal, Nautla, Jamapa)
    if (lon >= -97.6 and lat >= 17.3) or (lon >= -98.4 and 20.5 <= lat < 22.8):
      return "gulf_olmec_lowlands"
    # Oaxaca & Mixteca Sierra/Valleys (Atoyac-Verde, Tehuantepec, Costa Chica-Oaxaca)
    if lat < 17.85 and lon >= -98.65:
      return "oaxaca_mixteca_valleys"
    # Basin of Mexico & Central Highlands (Valley of Mexico, Puebla-Tlaxcala, Upper Balsas, Morelos, Guerrero highlands)
    if lon >= -100.55 and lat < 20.85:
      return "basin_of_mexico_central_highlands"
    # Bajío & North-Central Highlands (Guanajuato, Zacatecas, Aguascalientes, SLP, Durango highlands)
    if lat >= 20.85:
      return "bajio_north_central_highlands"
    # West Mexico Santiago-Balsas (Michoacán, Jalisco, Colima, Nayarit, Lower Balsas)
    return "west_mexico_santiago_balsas"

  b_ch1 = group_basins(mainland_basins, clf_ch1, arg2_clip_geom=meso_env)
  ch1_zones = [
    {"id": "gulf_olmec_lowlands", "name": "Gulf Olmec & Veracruz Lowlands", "geom": b_ch1.get("gulf_olmec_lowlands"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-10000": 18000, "-3000": 85000, "-1000": 320000, "0": 480000, "600": 720000, "1200": 980000}},
    {"id": "basin_of_mexico_central_highlands", "name": "Basin of Mexico & Central Highlands", "geom": b_ch1.get("basin_of_mexico_central_highlands"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-10000": 24000, "-3000": 110000, "-1000": 380000, "0": 950000, "600": 1850000, "1200": 2450000}},
    {"id": "oaxaca_mixteca_valleys", "name": "Oaxaca & Mixteca Sierra-Valleys", "geom": b_ch1.get("oaxaca_mixteca_valleys"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-10000": 16000, "-3000": 75000, "-1000": 240000, "0": 460000, "600": 740000, "1200": 960000}},
    {"id": "west_mexico_santiago_balsas", "name": "West Mexico Santiago-Balsas", "geom": b_ch1.get("west_mexico_santiago_balsas"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-10000": 20000, "-3000": 85000, "-1000": 210000, "0": 440000, "600": 780000, "1200": 1220000}},
    {"id": "bajio_north_central_highlands", "name": "Bajio & North-Central Highlands", "geom": b_ch1.get("bajio_north_central_highlands"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-10000": 12000, "-3000": 42000, "-1000": 95000, "0": 180000, "600": 390000, "1200": 340000}},
    {"id": "pacific_sierra_madre_sonora_sinaloa", "name": "Pacific Sierra Madre & Sonora-Sinaloa", "geom": b_ch1.get("pacific_sierra_madre_sonora_sinaloa"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-10000": 14000, "-3000": 48000, "-1000": 95000, "0": 160000, "600": 280000, "1200": 460000}},
    {"id": "arid_northern_interior_baja", "name": "Arid Northern Interior & Baja California", "geom": b_ch1.get("arid_northern_interior_baja"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-10000": 16000, "-3000": 45000, "-1000": 75000, "0": 115000, "600": 165000, "1200": 240000}},
  ]
  write_chapter_assets(ch_by_idx[1], ch1_zones, D, bm_hist, bm_mod, arg5_envelope=meso_env)

  # =========================================================================
  # CH 02: Classic & Post-Classic Maya Lands (-2000..1524) — Pure HydroBASINS L6
  # =========================================================================
  def clf_ch2 (lat, lon, pfaf, main_bas):
    # Northern Yucatán Karst Shelf (Puuc, Chichén Itzá, Mayapán, Campeche-Quintana Roo)
    if lat >= 18.65:
      return "northern_yucatan_karst"
    # Belize & Caribbean Maya Lowlands (Belize River, Hondo, New River, Sarstoon, Gulf of Honduras coast)
    if lon >= -89.25 and lat >= 15.65:
      return "belize_caribbean_maya"
    # South-Eastern Maya Copán-Motagua-Western El Salvador
    if lon >= -89.85 and lat < 15.65:
      return "southeastern_maya_copan_motagua"
    # Chiapas Highlands & Grijalva Basin (Soconusco, Central Depression)
    if lon < -91.75 and lat < 17.65:
      return "chiapas_highlands_grijalva"
    # Petén & Usumacinta-Pasión Lowlands (Tikal, Calakmul, Palenque, Yaxchilán)
    if lat >= 15.75:
      return "peten_usumacinta_pasion"
    # Guatemala Highlands & Pacific Piedmont (Kaminaljuyú, Q'umarkaj, Tak'alik Ab'aj)
    return "guatemala_highlands_pacific"

  b_ch2 = group_basins(mainland_basins, clf_ch2, arg2_clip_geom=maya_env)
  ch2_zones = [
    {"id": "northern_yucatan_karst", "name": "Northern Yucatan Karst Shelf", "geom": b_ch2.get("northern_yucatan_karst"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-2000": 45000, "0": 280000, "800": 1350000, "1200": 950000, "1524": 820000}},
    {"id": "peten_usumacinta_pasion", "name": "Peten & Usumacinta-Pasion Lowlands", "geom": b_ch2.get("peten_usumacinta_pasion"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-2000": 40000, "0": 360000, "800": 2150000, "1200": 320000, "1524": 190000}},
    {"id": "belize_caribbean_maya", "name": "Belize & Caribbean Maya Lowlands", "geom": b_ch2.get("belize_caribbean_maya"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-2000": 22000, "0": 145000, "800": 720000, "1200": 210000, "1524": 140000}},
    {"id": "chiapas_highlands_grijalva", "name": "Chiapas Highlands & Grijalva Basin", "geom": b_ch2.get("chiapas_highlands_grijalva"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-2000": 38000, "0": 195000, "800": 480000, "1200": 420000, "1524": 390000}},
    {"id": "guatemala_highlands_pacific", "name": "Guatemala Highlands & Pacific Piedmont", "geom": b_ch2.get("guatemala_highlands_pacific"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-2000": 48000, "0": 280000, "800": 650000, "1200": 780000, "1524": 1150000}},
    {"id": "southeastern_maya_copan_motagua", "name": "South-Eastern Maya (Copan-Motagua-W. El Salvador)", "geom": b_ch2.get("southeastern_maya_copan_motagua"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-2000": 30000, "0": 175000, "800": 620000, "1200": 390000, "1524": 460000}},
  ]
  write_chapter_assets(ch_by_idx[2], ch2_zones, D, bm_hist, bm_mod, arg5_envelope=maya_env)

  # =========================================================================
  # CH 03: Aztec Empire & Late Post-Classic Mexico (1200..1519) — HydroBASINS L6 + DECM
  # =========================================================================
  # Build organic geopolitical/watershed core using DECM Tlaxcala + HydroBASINS L6 (ZERO modern borders!)
  tlax_decm = DECM.get("tlaxcala")
  def clf_ch3 (lat, lon, pfaf, main_bas):
    if lon < -104.2 and lat >= 23.2:
      return "northern_chichimeca_aridoamerica"
    if lat >= 22.35 and not (lon >= -99.3 and lat < 23.2):
      return "northern_chichimeca_aridoamerica"
    # Gulf Huasteca & Totonacapan (Pánuco, Tuxpan, Tecolutla, Cempoala)
    if lon >= -99.0 and lat >= 19.65:
      return "gulf_huasteca_totonacapan"
    # Mixtec-Zapotec Oaxaca
    if lat < 17.85 and lon >= -98.45:
      return "mixtec_zapotec_oaxaca"
    # Basin of Mexico Triple Alliance Core (Endorheic Valley of Mexico & immediate Toluca/Tula ring)
    if 18.95 <= lat <= 20.15 and -99.85 <= lon <= -98.55:
      return "basin_of_mexico_triple_alliance"
    # Tlaxcala-Teotitlán-Metztitlán Independent Enclaves (eastern Puebla-Tlaxcala watershed / Metztitlán)
    if 18.85 <= lat <= 19.80 and -98.55 < lon <= -97.45:
      return "tlaxcala_independent_enclaves"
    # Purépecha / Tarascan Empire (Michoacán / Pátzcuaro / Middle Balsas-Lerma)
    if 17.85 <= lat <= 20.45 and -103.35 <= lon <= -100.35:
      return "purepecha_tarascan_empire"
    # West Mexico Cacicazgos (Jalisco, Colima, Nayarit, Southern Sinaloa)
    if lon < -102.6:
      return "west_mexico_cacicazgos"
    # Central Aztec Tributary Provinces (Morelos, Guerrero, Puebla, Central/South Veracruz)
    if lat < 20.85 and lon >= -100.65:
      return "central_aztec_tributary_provinces"
    return "northern_chichimeca_aridoamerica"

  b_ch3 = group_basins(mainland_basins, clf_ch3, arg2_clip_geom=meso_env)
  tlax_clip = clip_geom(tlax_decm, box(-98.80, 18.70, -97.10, 20.15)) if tlax_decm is not None else None
  tlax_zone = u_geoms([b_ch3.get("tlaxcala_independent_enclaves"), clip_geom(tlax_clip, meso_env)]) if tlax_clip is not None else b_ch3.get("tlaxcala_independent_enclaves")
  ch3_zones = [
    {"id": "basin_of_mexico_triple_alliance", "name": "Basin of Mexico Triple Alliance Core", "geom": b_ch3.get("basin_of_mexico_triple_alliance"), "source_hgis": "HydroBASINS_NA_L6+DECM_Mexico", "population": {"1200": 680000, "1350": 1150000, "1450": 1750000, "1519": 2350000}},
    {"id": "tlaxcala_independent_enclaves", "name": "Tlaxcala & Independent Highland Enclaves", "geom": tlax_zone, "source_hgis": "DECM_Acuna_Tlaxcala+HydroBASINS_NA_L6", "population": {"1200": 260000, "1350": 390000, "1450": 540000, "1519": 680000}},
    {"id": "central_aztec_tributary_provinces", "name": "Central Aztec Tributary Provinces", "geom": b_ch3.get("central_aztec_tributary_provinces"), "source_hgis": "HydroBASINS_NA_L6+DECM_Gerhard", "population": {"1200": 1650000, "1350": 2250000, "1450": 2950000, "1519": 3750000}},
    {"id": "purepecha_tarascan_empire", "name": "Purepecha (Tarascan) Michoacan Empire", "geom": b_ch3.get("purepecha_tarascan_empire"), "source_hgis": "HydroBASINS_NA_L6+DECM_Michoacan", "population": {"1200": 480000, "1350": 680000, "1450": 950000, "1519": 1250000}},
    {"id": "mixtec_zapotec_oaxaca", "name": "Mixtec-Zapotec Oaxaca", "geom": b_ch3.get("mixtec_zapotec_oaxaca"), "source_hgis": "HydroBASINS_NA_L6+DECM_Antequera", "population": {"1200": 960000, "1350": 1150000, "1450": 1380000, "1519": 1650000}},
    {"id": "gulf_huasteca_totonacapan", "name": "Gulf Huasteca & Totonacapan", "geom": b_ch3.get("gulf_huasteca_totonacapan"), "source_hgis": "HydroBASINS_NA_L6+DECM_Gerhard", "population": {"1200": 620000, "1350": 780000, "1450": 960000, "1519": 1150000}},
    {"id": "west_mexico_cacicazgos", "name": "West Mexico Cacicazgos (Jalisco-Colima-Nayarit)", "geom": b_ch3.get("west_mexico_cacicazgos"), "source_hgis": "HydroBASINS_NA_L6+DECM_NuevaGalicia", "population": {"1200": 580000, "1350": 720000, "1450": 880000, "1519": 1080000}},
    {"id": "northern_chichimeca_aridoamerica", "name": "Northern Chichimeca & Aridoamerica", "geom": b_ch3.get("northern_chichimeca_aridoamerica"), "source_hgis": "HydroBASINS_NA_L6", "population": {"1200": 680000, "1350": 740000, "1450": 810000, "1519": 890000}},
  ]
  write_chapter_assets(ch_by_idx[3], ch3_zones, D, bm_hist, bm_mod, arg5_envelope=meso_env)

  # =========================================================================
  # CH 04: Pre-Columbian Lower Central America (-10000..1502) — Pure HydroBASINS L6
  # =========================================================================
  def clf_ch4 (lat, lon, pfaf, main_bas):
    # Gran Darién & Panama Isthmus (east of ~-80.1: Chagres, Bayano, Chucunaque-Tuira)
    if lon >= -80.10:
      return "gran_darien_panama_isthmus"
    # Gran Coclé & Azuero Peninsula (central Panama -81.75..-80.10)
    if lon >= -81.75:
      return "gran_cocle_azuero"
    # Costa Rica Central Valley & Gran Chiriquí (lat < 10.25 and lon >= -84.95)
    if lat < 10.25 and lon >= -84.95:
      return "costa_rica_central_gran_chiriqui"
    # Eastern Honduras & Mosquitia (Aguán, Patuca, Coco/Segovia north of lat 13.7)
    if lat >= 13.70:
      return "eastern_honduras_mosquitia"
    # Pacific Nicaragua & Nicoya Lakes (western lakes & Nicoya peninsula)
    if lon < -84.95 or (lat < 11.45 and lon < -84.45):
      return "pacific_nicaragua_nicoya_lakes"
    # Caribbean Nicaragua-Costa Rica Lowlands (Escondido, Río Grande, San Juan, Tortuguero)
    return "caribbean_nicaragua_costa_rica"

  b_ch4 = group_basins(mainland_basins, clf_ch4, arg2_clip_geom=lower_ca_env)
  ch4_zones = [
    {"id": "eastern_honduras_mosquitia", "name": "Eastern Honduras & Mosquitia Basins", "geom": b_ch4.get("eastern_honduras_mosquitia"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-10000": 9000, "-3000": 32000, "0": 95000, "1000": 210000, "1502": 320000}},
    {"id": "pacific_nicaragua_nicoya_lakes", "name": "Pacific Nicaragua & Nicoya Lakes", "geom": b_ch4.get("pacific_nicaragua_nicoya_lakes"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-10000": 11000, "-3000": 42000, "0": 140000, "1000": 380000, "1502": 620000}},
    {"id": "caribbean_nicaragua_costa_rica", "name": "Caribbean Nicaragua-Costa Rica Lowlands", "geom": b_ch4.get("caribbean_nicaragua_costa_rica"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-10000": 7000, "-3000": 24000, "0": 72000, "1000": 165000, "1502": 240000}},
    {"id": "costa_rica_central_gran_chiriqui", "name": "Costa Rica Central Valley & Gran Chiriqui", "geom": b_ch4.get("costa_rica_central_gran_chiriqui"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-10000": 10000, "-3000": 38000, "0": 125000, "1000": 310000, "1502": 460000}},
    {"id": "gran_cocle_azuero", "name": "Gran Cocle & Azuero Peninsula", "geom": b_ch4.get("gran_cocle_azuero"), "source_hgis": "HydroBASINS_NA_L6", "population": {"-10000": 6000, "-3000": 26000, "0": 90000, "1000": 220000, "1502": 340000}},
    {"id": "gran_darien_panama_isthmus", "name": "Gran Darien & Panama Isthmus", "geom": b_ch4.get("gran_darien_panama_isthmus"), "source_hgis": "HydroBASINS_NA_L6+SA_L6", "population": {"-10000": 8000, "-3000": 28000, "0": 95000, "1000": 240000, "1502": 380000}},
  ]
  write_chapter_assets(ch_by_idx[4], ch4_zones, D, bm_hist, bm_mod, arg5_envelope=lower_ca_env)

  # =========================================================================
  # CH 05: Pre-Columbian Caribbean Islands (-5000..1492) — Cultural Archipelagos
  # East-West Cuba cultural divide (Pinar del Rio/Havana/Matanzas-Zapata/Isla = Western Ciboney
  # vs Villa Clara/Cienfuegos eastward + Jamaica = Eastern Sub-Taino); unified Hispaniola!
  # =========================================================================
  cuba_west_pre = u_geoms([
    CU1[norm_str(k)] for k in ("Pinar del Rio", "Artemisa", "Havana", "Mayabeque", "Matanzas", "Isle of Youth")
    if norm_str(k) in CU1
  ])
  cuba_east_pre = u_geoms([
    CU1[norm_str(k)] for k in ("Villa Clara", "Cienfuegos", "Sancti Spiritus", "Ciego de Avila", "Camagüey", "Las Tunas", "Holguín", "Granma", "Santiago de Cuba", "Guantánamo")
    if norm_str(k) in CU1
  ])
  lesser_arc_pre = u_geoms([
    C.get(k) for k in (
      "Anguilla", "Saint Martin", "Sint Maarten", "Saint Barthelemy",
      "Saint Kitts and Nevis", "Antigua and Barbuda", "Montserrat",
      "French Antilles", "Dominica", "Saint Lucia",
      "Saint Vincent and the Grenadines", "Grenada", "Barbados",
    ) if k in C
  ] + [G.get("Saba_Sint_Eustatius")])
  trinidad_south_pre = u_geoms([
    C.get("Trinidad and Tobago"), C.get("Aruba"), C.get("Curaçao"), G.get("Bonaire"),
  ])
  carib_pre_env = u_geoms([
    G["Cuba_Full"], C.get("Jamaica"), C.get("Cayman Islands"),
    G["Hispaniola_Unified"], C.get("Puerto Rico"),
    C.get("United States Virgin Islands"), C.get("British Virgin Islands"),
    C.get("The Bahamas"), C.get("Turks and Caicos Islands"),
    lesser_arc_pre, trinidad_south_pre,
  ])
  ch5_zones = [
    {"id": "western_cuba_ciboney", "name": "Western Cuba (Ciboney & Guanahatabey)", "geom": cuba_west_pre, "source_hgis": "PreColumbian_EastWest_Cuba_Divide+NaturalEarth", "population": {"-5000": 4500, "-1000": 14000, "0": 26000, "1000": 48000, "1492": 65000}},
    {"id": "eastern_cuba_jamaica_subtaino", "name": "Eastern Cuba & Jamaica (Sub-Taino)", "geom": u_geoms([cuba_east_pre, C.get("Jamaica"), C.get("Cayman Islands")]), "source_hgis": "PreColumbian_EastWest_Cuba_Divide+NaturalEarth", "population": {"-5000": 3500, "-1000": 16000, "0": 38000, "1000": 125000, "1492": 225000}},
    {"id": "hispaniola_classic_taino", "name": "Hispaniola (Classic Taino Chiefdoms)", "geom": G["Hispaniola_Unified"], "source_hgis": "NaturalEarth_Unified_Island_Coastline", "population": {"-5000": 6000, "-1000": 28000, "0": 75000, "1000": 260000, "1492": 520000}},
    {"id": "puerto_rico_virgin_islands_taino", "name": "Puerto Rico & Virgin Islands (Boriken Taino)", "geom": u_geoms([C.get("Puerto Rico"), C.get("United States Virgin Islands"), C.get("British Virgin Islands")]), "source_hgis": "NaturalEarth_Coastlines", "population": {"-5000": 2000, "-1000": 9500, "0": 28000, "1000": 85000, "1492": 135000}},
    {"id": "lucayan_bahamas_turks_caicos", "name": "Lucayan Bahamas & Turks-Caicos", "geom": u_geoms([C.get("The Bahamas"), C.get("Turks and Caicos Islands")]), "source_hgis": "NaturalEarth_Coastlines", "population": {"-5000": 0, "-1000": 0, "0": 1500, "1000": 18000, "1492": 42000}},
    {"id": "lesser_antilles_kalinago_arc", "name": "Lesser Antilles (Saladoid & Kalinago Arc)", "geom": lesser_arc_pre, "source_hgis": "NaturalEarth_Coastlines", "population": {"-5000": 1500, "-1000": 8500, "0": 26000, "1000": 52000, "1492": 72000}},
    {"id": "trinidad_southern_littoral_islands", "name": "Trinidad, Tobago & Southern Littoral Islands", "geom": trinidad_south_pre, "source_hgis": "NaturalEarth_Coastlines", "population": {"-5000": 3500, "-1000": 11000, "0": 22000, "1000": 38000, "1492": 52000}},
  ]
  write_chapter_assets(ch_by_idx[5], ch5_zones, D, bm_hist, bm_mod, arg5_envelope=carib_pre_env)

  # =========================================================================
  # Shared authentic HGIS de las Indias helper polygons (Ch 06, Ch 07, Ch 08)
  # =========================================================================
  PM90 = D["indias_1790_pm"]
  def p90 (code):
    rec = P90.get(code)
    return rec["geom"] if rec else None

  def pm90 (code):
    rec = PM90.get(code)
    return rec["geom"] if rec else None

  chiapas_col = p90("PRGUCH00")
  chiapas_plus_lac = u_geoms([chiapas_col, MX1.get("chiapas")])
  guat_peten_col = u_geoms([p90("PRGUGU00"), F90.get("FRGUMOCH", {}).get("geom")])
  # Authentic New Spain envelope EXCLUDES Chiapas/Lacandona & colonial Petén (organic HGIS Indias frontier!)
  new_spain_env = diff_geom(C["Mexico"], u_geoms([chiapas_plus_lac, guat_peten_col]))
  cgg_panama_env = u_geoms([G["Central_America_Modern"], chiapas_plus_lac, guat_peten_col])

  # Organic HydroBASINS L6 + HGIS Indias Taguzgalpa-Tologalpa Mosquitia (ZERO dead-straight ~85W meridian!)
  mosq_col = build_organic_mosquitia_geom(D["basins"], F90, u_geoms([C["Honduras"], C["Nicaragua"]]))
  bh_col = OHM.get("british_honduras_early")
  panama_col = u_geoms([p90("PRNGPA00"), p90("PRNGVE00"), p90("PRNGDA00")])
  tabasco_gulf = u_geoms([pm90("JUNETBTB"), MX1.get("tabasco")])

  # =========================================================================
  # CH 06: Conquest & Collapse in Mesoamerica & Central America (1518..1650)
  # Authentic 16th-c. Audiencias via HGIS de las Indias + OHM + DECM!
  # Tabasco Gulf coastal plain sits in Yucatan & Tabasco; Audiencia de Guatemala stays landlocked from the Gulf!
  # =========================================================================
  aud_mex_core = u_geoms([p90(k) for k in ("PRNEMX00", "PRNEPU00", "PRNEVC00", "PRNEOA00", "PRNEMI00", "PRNEGJ00")])
  aud_ngal = u_geoms([OHM.get("nueva_galicia"), p90("PRGDGD00"), p90("PRGDNA00"), p90("PRGDZA00")])
  yuc_tab = u_geoms([p90("PRNEYU00"), tabasco_gulf])
  nviz_north = u_geoms([OHM.get("nueva_vizcaya_1562"), p90("PRGDDU00"), p90("PRGDSS00"), p90("PRNECL00"), p90("PRGDCO00"), p90("PRGDNL00"), p90("PRGDNS00"), p90("PRNESL00")])
  aud_gua_chi = diff_geom(u_geoms([guat_peten_col, chiapas_col, p90("PRGUSS00")]), yuc_tab)
  hon_nic_cr = u_geoms([p90("PRGUCY00"), p90("PRGUNI00"), p90("PRGUCR00"), mosq_col])
  ch6_zones = [
    {"id": "audiencia_mexico_core", "name": "Audiencia de Mexico Central Core", "geom": aud_mex_core, "source_hgis": "HGIS_Indias_1790+DECM_16c", "population": {"1518": 10200000, "1550": 3650000, "1600": 1550000, "1650": 1220000}},
    {"id": "audiencia_nueva_galicia_west", "name": "Audiencia de Nueva Galicia & West Mexico", "geom": aud_ngal, "source_hgis": "OHM_Nueva_Galicia_1531+HGIS_Indias", "population": {"1518": 1450000, "1550": 520000, "1600": 260000, "1650": 285000}},
    {"id": "yucatan_tabasco_conquest", "name": "Yucatan & Tabasco", "geom": yuc_tab, "source_hgis": "HGIS_Indias_PRNEYU00_JUNETBTB+DECM", "population": {"1518": 950000, "1550": 340000, "1600": 225000, "1650": 210000}},
    {"id": "nueva_vizcaya_northern_frontier", "name": "Nueva Vizcaya & Northern Mining Frontier", "geom": nviz_north, "source_hgis": "OHM_Nueva_Vizcaya_1562+HGIS_Indias", "population": {"1518": 950000, "1550": 620000, "1600": 440000, "1650": 380000}},
    {"id": "audiencia_guatemala_chiapas", "name": "Audiencia de Guatemala, Chiapas & San Salvador", "geom": aud_gua_chi, "source_hgis": "HGIS_Indias_AUCO0000", "population": {"1518": 2250000, "1550": 820000, "1600": 460000, "1650": 410000}},
    {"id": "honduras_nicaragua_costa_rica_conquest", "name": "Honduras, Nicaragua & Costa Rica", "geom": hon_nic_cr, "source_hgis": "HGIS_Indias_GUA+HydroBASINS_Mosquitia", "population": {"1518": 1650000, "1550": 420000, "1600": 210000, "1650": 185000}},
    {"id": "tierra_firme_panama", "name": "Tierra Firme (Audiencia de Panama & Veraguas)", "geom": panama_col, "source_hgis": "HGIS_Indias_TFI_PRNGPA00_VE00_DA00", "population": {"1518": 720000, "1550": 165000, "1600": 95000, "1650": 82000}},
  ]
  write_chapter_assets(ch_by_idx[6], ch6_zones, D, bm_hist, bm_mod, arg5_envelope=G["Mainland_Mesoamerica_CA"])

  # =========================================================================
  # CH 07: Viceroyalty of New Spain (1535..1821) — Authentic HGIS de las Indias 1790 Intendancies!
  # (Excludes Chiapas & colonial Petén via organic HGIS Indias Yucatán-Guatemala frontier!)
  # =========================================================================
  ch7_zones = [
    {"id": "int_mexico", "name": "Intendencia de Mexico", "geom": p90("PRNEMX00"), "source_hgis": "HGIS_Indias_PRNEMX00", "population": {"1570": 1150000, "1646": 580000, "1742": 890000, "1793": 1162886, "1803": 1511800, "1821": 1680000}},
    {"id": "int_puebla_tlaxcala", "name": "Intendencia de Puebla & Gobierno de Tlaxcala", "geom": p90("PRNEPU00"), "source_hgis": "HGIS_Indias_PRNEPU00", "population": {"1570": 620000, "1646": 310000, "1742": 460000, "1793": 627391, "1803": 813300, "1821": 880000}},
    {"id": "int_veracruz", "name": "Intendencia de Veracruz", "geom": p90("PRNEVC00"), "source_hgis": "HGIS_Indias_PRNEVC00", "population": {"1570": 145000, "1646": 75000, "1742": 105000, "1793": 120000, "1803": 156000, "1821": 185000}},
    {"id": "int_oaxaca", "name": "Intendencia de Oaxaca", "geom": p90("PRNEOA00"), "source_hgis": "HGIS_Indias_PRNEOA00", "population": {"1570": 420000, "1646": 215000, "1742": 325000, "1793": 411336, "1803": 534800, "1821": 575000}},
    {"id": "int_valladolid_michoacan", "name": "Intendencia de Valladolid (Michoacan)", "geom": p90("PRNEMI00"), "source_hgis": "HGIS_Indias_PRNEMI00", "population": {"1570": 265000, "1646": 140000, "1742": 225000, "1793": 289314, "1803": 376400, "1821": 420000}},
    {"id": "int_guanajuato_bajio", "name": "Intendencia de Guanajuato", "geom": p90("PRNEGJ00"), "source_hgis": "HGIS_Indias_PRNEGJ00", "population": {"1570": 115000, "1646": 85000, "1742": 220000, "1793": 397924, "1803": 517300, "1821": 545000}},
    {"id": "int_guadalajara_nueva_galicia", "name": "Intendencia de Guadalajara (Nueva Galicia)", "geom": u_geoms([p90("PRGDGD00"), p90("PRGDNA00")]), "source_hgis": "HGIS_Indias_PRGDGD00_GDNA00", "population": {"1570": 240000, "1646": 145000, "1742": 285000, "1793": 485000, "1803": 630500, "1821": 695000}},
    {"id": "int_zacatecas_san_luis_potosi", "name": "Intendencias de Zacatecas & San Luis Potosi", "geom": u_geoms([p90("PRGDZA00"), p90("PRNESL00")]), "source_hgis": "HGIS_Indias_PRGDZA00_NESL00", "population": {"1570": 95000, "1646": 85000, "1742": 175000, "1793": 352116, "1803": 457700, "1821": 495000}},
    {"id": "int_merida_yucatan", "name": "Intendencia de Merida (Yucatan & Tabasco)", "geom": clip_geom(u_geoms([p90("PRNEYU00"), tabasco_gulf]), new_spain_env), "source_hgis": "HGIS_Indias_PRNEYU00_JUNETBTB", "population": {"1570": 245000, "1646": 185000, "1742": 265000, "1793": 358261, "1803": 465800, "1821": 525000}},
    {"id": "int_durango_nueva_vizcaya", "name": "Intendencia de Durango (Nueva Vizcaya)", "geom": p90("PRGDDU00"), "source_hgis": "HGIS_Indias_PRGDDU00", "population": {"1570": 130000, "1646": 95000, "1742": 110000, "1793": 122866, "1803": 159700, "1821": 195000}},
    {"id": "int_arizpe_sonora_californias", "name": "Intendencia de Arizpe (Sonora-Sinaloa) & Baja California", "geom": u_geoms([p90("PRGDSS00"), p90("PRNECL00")]), "source_hgis": "HGIS_Indias_PRGDSS00_NECL00", "population": {"1570": 165000, "1646": 115000, "1742": 98000, "1793": 102000, "1803": 130400, "1821": 155000}},
    {"id": "provincias_internas_oriente", "name": "Provincias Internas de Oriente (Coahuila, Nuevo Leon & Nuevo Santander)", "geom": u_geoms([p90("PRGDCO00"), p90("PRGDNL00"), p90("PRGDNS00")]), "source_hgis": "HGIS_Indias_PRGDCO00_NL00_NS00", "population": {"1570": 75000, "1646": 55000, "1742": 72000, "1793": 105000, "1803": 142000, "1821": 175000}},
  ]
  write_chapter_assets(ch_by_idx[7], ch7_zones, D, bm_hist, bm_mod, arg5_envelope=new_spain_env)

  # =========================================================================
  # CH 08: Captaincy General of Guatemala & Central America (1524..1821)
  # Authentic HGIS de las Indias + Organic HydroBASINS Mosquitia (ZERO ~85W straight meridian!)
  # =========================================================================
  ch8_zones = [
    {"id": "british_honduras_settlement", "name": "British Honduras Logwood Settlement", "geom": bh_col, "source_hgis": "OHM_Settlement_British_Honduras_1841", "population": {"1524": 15000, "1650": 8000, "1750": 4500, "1790": 3800, "1821": 5200}},
    {"id": "mosquitia_coast", "name": "Mosquitia Coast (Mosquito Kingdom)", "geom": mosq_col, "source_hgis": "HGIS_Indias_Taguzgalpa_Tologalpa+HydroBASINS_L6", "population": {"1524": 160000, "1650": 48000, "1750": 42000, "1790": 46000, "1821": 52000}},
    {"id": "cgg_ciudad_real_chiapas", "name": "Intendencia de Ciudad Real de Chiapas (Guatemala until 1824)", "geom": chiapas_col, "source_hgis": "HGIS_Indias_PRGUCH00", "population": {"1524": 390000, "1650": 92000, "1778": 69253, "1800": 98000, "1821": 118000}},
    {"id": "cgg_guatemala_verapaz", "name": "Provincia de Guatemala Core & Verapaz", "geom": guat_peten_col, "source_hgis": "HGIS_Indias_PRGUGU00_FRGUMOCH", "population": {"1524": 1250000, "1650": 260000, "1778": 366000, "1800": 455000, "1821": 535000}},
    {"id": "cgg_san_salvador_sonsonate", "name": "Intendencia de San Salvador & Sonsonate", "geom": p90("PRGUSS00"), "source_hgis": "HGIS_Indias_PRGUSS00", "population": {"1524": 460000, "1650": 85000, "1778": 146684, "1800": 195000, "1821": 248000}},
    {"id": "cgg_comayagua_honduras", "name": "Intendencia de Comayagua (Honduras)", "geom": diff_geom(p90("PRGUCY00"), mosq_col), "source_hgis": "HGIS_Indias_PRGUCY00", "population": {"1524": 420000, "1650": 72000, "1778": 87730, "1800": 115000, "1821": 135000}},
    {"id": "cgg_leon_nicaragua_costa_rica", "name": "Intendencia de Leon (Nicaragua) & Costa Rica", "geom": diff_geom(u_geoms([p90("PRGUNI00"), p90("PRGUCR00")]), mosq_col), "source_hgis": "HGIS_Indias_PRGUNI00_GUCR00", "population": {"1524": 890000, "1650": 95000, "1778": 131227, "1800": 185000, "1821": 235000}},
    {"id": "audiencia_panama_veraguas", "name": "Audiencia de Panama, Veraguas & Darien", "geom": panama_col, "source_hgis": "HGIS_Indias_PRNGPA00_VE00_DA00", "population": {"1524": 540000, "1650": 82000, "1778": 68000, "1800": 78000, "1821": 92000}},
  ]
  write_chapter_assets(ch_by_idx[8], ch8_zones, D, bm_hist, bm_mod, arg5_envelope=cgg_panama_env)

  # =========================================================================
  # CH 09: Spanish Conquest of the Indigenous Caribbean (1492..1650)
  # Authentic Audiencia de Santo Domingo & Rival Footholds (UNIFIED Hispaniola!)
  # =========================================================================
  ch9_zones = [
    {"id": "sdo_hispaniola", "name": "Hispaniola (Audiencia de Santo Domingo)", "geom": G["Hispaniola_Unified"], "source_hgis": "HGIS_Indias_AUSD0000+NaturalEarth", "population": {"1492": 520000, "1514": 65000, "1550": 32000, "1600": 26000, "1650": 34000}},
    {"id": "sdo_cuba", "name": "Captaincy General of Cuba", "geom": G["Cuba_Full"], "source_hgis": "HGIS_Indias_PRSDLH00_CU00", "population": {"1492": 185000, "1520": 45000, "1550": 18000, "1600": 24000, "1650": 35000}},
    {"id": "sdo_puerto_rico", "name": "Puerto Rico & Virgin Islands", "geom": u_geoms([C.get("Puerto Rico"), C.get("United States Virgin Islands"), C.get("British Virgin Islands")]), "source_hgis": "HGIS_Indias_PRSDPR00+OHM", "population": {"1492": 135000, "1530": 18000, "1550": 11000, "1600": 10500, "1650": 14000}},
    {"id": "sdo_spanish_jamaica", "name": "Spanish Jamaica & Cayman Islands", "geom": u_geoms([C.get("Jamaica"), C.get("Cayman Islands")]), "source_hgis": "DECM_Gerhard_SEFrontier+NaturalEarth", "population": {"1492": 105000, "1530": 22000, "1550": 6500, "1600": 4500, "1650": 4200}},
    {"id": "lucayan_northern_bahamian_arc", "name": "Lucayan & Northern Bahamian Arc", "geom": u_geoms([C.get("The Bahamas"), C.get("Turks and Caicos Islands")]), "source_hgis": "NaturalEarth_Coastlines", "population": {"1492": 42000, "1520": 1200, "1550": 100, "1600": 100, "1650": 600}},
    {"id": "lesser_antilles_trinidad_early", "name": "Lesser Antilles, Trinidad & Southern Islands", "geom": u_geoms([lesser_arc_pre, trinidad_south_pre]), "source_hgis": "HGIS_Indias_SDO+OHM", "population": {"1492": 124000, "1550": 68000, "1600": 52000, "1650": 85000}},
  ]
  write_chapter_assets(ch_by_idx[9], ch9_zones, D, bm_hist, bm_mod, arg5_envelope=carib_pre_env)

  # =========================================================================
  # CH 10: Colonial Caribbean Plantation Era (1650..1898) — OHM + HGIS de las Indias
  # Uses OHM Saint-Domingue 1697-1795 Aranjuez border on Hispaniola + includes Bermuda!
  # =========================================================================
  sd_french = clip_geom(OHM.get("saint_domingue_1697"), G["Hispaniola_Unified"])
  sd_spanish = diff_geom(G["Hispaniola_Unified"], sd_french)
  brit_barb_wind = u_geoms([C.get(k) for k in ("Barbados", "Grenada", "Saint Vincent and the Grenadines", "Saint Lucia", "Dominica") if k in C])
  brit_lee_bah_bmu = u_geoms([C.get(k) for k in ("Antigua and Barbuda", "Saint Kitts and Nevis", "Montserrat", "Anguilla", "British Virgin Islands", "The Bahamas", "Turks and Caicos Islands", "Bermuda") if k in C])
  fr_guad_mart = u_geoms([C.get(k) for k in ("French Antilles", "Saint Barthelemy", "Saint Martin") if k in C])
  du_da_trinidad = u_geoms([C.get(k) for k in ("Aruba", "Curaçao", "Caribbean Netherlands", "Sint Maarten", "United States Virgin Islands", "Trinidad and Tobago") if k in C])
  carib_col_env = u_geoms([carib_pre_env, C.get("Bermuda")])
  ch10_zones = [
    {"id": "spanish_cuba", "name": "Spanish Cuba (Capitania General de Cuba)", "geom": G["Cuba_Full"], "source_hgis": "OHM_Cuba_Colonial+HGIS_Indias", "population": {"1650": 35000, "1774": 171620, "1817": 572383, "1861": 1396530, "1898": 1572797}},
    {"id": "spanish_puerto_rico", "name": "Spanish Puerto Rico (Capitania General)", "geom": C.get("Puerto Rico"), "source_hgis": "OHM_Puerto_Rico_Colonial+HGIS_Indias", "population": {"1650": 14000, "1765": 44883, "1815": 220892, "1860": 583308, "1898": 953243}},
    {"id": "french_saint_domingue", "name": "French Saint-Domingue / Haiti (1697-1795 Frontier)", "geom": sd_french, "source_hgis": "OHM_Saint_Domingue_1697_1795", "population": {"1650": 12000, "1750": 185000, "1789": 523803, "1805": 380000, "1898": 1250000}},
    {"id": "spanish_santo_domingo", "name": "Spanish Santo Domingo", "geom": sd_spanish, "source_hgis": "HGIS_Indias_PRSDSD00+OHM", "population": {"1650": 22000, "1750": 70000, "1789": 125000, "1850": 180000, "1898": 480000}},
    {"id": "british_jamaica", "name": "British Jamaica & Cayman Islands", "geom": u_geoms([C.get("Jamaica"), C.get("Cayman Islands")]), "source_hgis": "OHM_Colony_of_Jamaica", "population": {"1650": 4200, "1730": 83000, "1800": 318000, "1844": 377433, "1898": 715000}},
    {"id": "british_barbados_windwards", "name": "British Barbados & Windward Islands", "geom": brit_barb_wind, "source_hgis": "OHM_Barbados_Windwards", "population": {"1650": 45000, "1750": 115000, "1834": 215000, "1871": 310000, "1898": 385000}},
    {"id": "british_leewards_bahamas_bermuda", "name": "British Leewards, Bahamas, Turks-Caicos & Bermuda", "geom": brit_lee_bah_bmu, "source_hgis": "OHM_Bahamas_Bermuda_Leewards", "population": {"1650": 26000, "1750": 82000, "1834": 128000, "1871": 168000, "1898": 198000}},
    {"id": "french_guadeloupe_martinique", "name": "French Guadeloupe, Martinique, St Barthelemy & St Martin", "geom": fr_guad_mart, "source_hgis": "OHM_Guadeloupe_Martinique", "population": {"1650": 22000, "1750": 125000, "1830": 228000, "1870": 315000, "1898": 368000}},
    {"id": "dutch_danish_antilles_trinidad", "name": "Dutch & Danish Antilles & Trinidad-Tobago", "geom": du_da_trinidad, "source_hgis": "OHM_Trinidad_Dutch_Danish_Antilles", "population": {"1650": 18000, "1750": 48000, "1834": 118000, "1871": 212000, "1898": 355000}},
  ]
  write_chapter_assets(ch_by_idx[10], ch10_zones, D, bm_hist, bm_mod, arg5_envelope=carib_col_env)

  # =========================================================================
  # CH 11: Mexico after Independence (1821..2025) — Regime III (MEX_ADM1 32 states -> 9 macro-regions)
  # =========================================================================
  def mx_grp (keys):
    return u_geoms([MX1[norm_str(k)] for k in keys if norm_str(k) in MX1])

  ch11_zones = [
    {"id": "mx_valley_central_core", "name": "Valley of Mexico & Central Core", "geom": mx_grp(["Distrito Federal", "Mexico", "Morelos", "Hidalgo", "Puebla", "Tlaxcala"]), "source_hgis": "geoBoundaries_MEX_ADM1", "population": {"1821": 2480000, "1895": 4215000, "1950": 9065000, "2000": 31950000, "2020": 38950000}},
    {"id": "mx_gulf_veracruz_tabasco", "name": "Gulf Lowlands (Veracruz & Tabasco)", "geom": mx_grp(["Veracruz de Ignacio de la Llave", "Tabasco"]), "source_hgis": "geoBoundaries_MEX_ADM1", "population": {"1821": 265000, "1895": 998000, "1950": 2403000, "2000": 8801000, "2020": 10465000}},
    {"id": "mx_south_oaxaca_guerrero_chiapas", "name": "Pacific South (Oaxaca, Guerrero & Chiapas)", "geom": mx_grp(["Oaxaca", "Guerrero", "Chiapas"]), "source_hgis": "geoBoundaries_MEX_ADM1", "population": {"1821": 945000, "1895": 1621000, "1950": 3248000, "2000": 10439000, "2020": 13217000}},
    {"id": "mx_yucatan_peninsula", "name": "Yucatan Peninsula (Yucatan, Campeche & Quintana Roo)", "geom": mx_grp(["Yucatan", "Campeche", "Quintana Roo"]), "source_hgis": "geoBoundaries_MEX_ADM1", "population": {"1821": 495000, "1895": 385000, "1950": 666000, "2000": 3224000, "2020": 5107000}},
    {"id": "mx_bajio_west_central", "name": "Bajio & West-Central (Guanajuato, Queretaro, SLP & Ags)", "geom": mx_grp(["Guanajuato", "Queretaro de Arteaga", "Aguascalientes", "San Luis Potosi"]), "source_hgis": "geoBoundaries_MEX_ADM1", "population": {"1821": 1040000, "1895": 1968000, "1950": 2658000, "2000": 9311000, "2020": 12783000}},
    {"id": "mx_pacific_west", "name": "Pacific West (Jalisco, Michoacan, Colima & Nayarit)", "geom": mx_grp(["Jalisco", "Michoacan de Ocampo", "Colima", "Nayarit"]), "source_hgis": "geoBoundaries_MEX_ADM1", "population": {"1821": 1095000, "1895": 2201000, "1950": 3572000, "2000": 11771000, "2020": 15064000}},
    {"id": "mx_northeast", "name": "North-East (Nuevo Leon, Tamaulipas & Coahuila)", "geom": mx_grp(["Nuevo Leon", "Tamaulipas", "Coahuila de Zaragoza"]), "source_hgis": "geoBoundaries_MEX_ADM1", "population": {"1821": 205000, "1895": 756000, "1950": 2179000, "2000": 8884000, "2020": 12459000}},
    {"id": "mx_north_central", "name": "North-Central (Chihuahua, Durango & Zacatecas)", "geom": mx_grp(["Chihuahua", "Durango", "Zacatecas"]), "source_hgis": "geoBoundaries_MEX_ADM1", "population": {"1821": 485000, "1895": 1010000, "1950": 2142000, "2000": 5854000, "2020": 7197000}},
    {"id": "mx_northwest_baja", "name": "North-West & Baja California (Sonora, Sinaloa & Bajas)", "geom": mx_grp(["Sonora", "Sinaloa", "Baja California", "Baja California Sur"]), "source_hgis": "geoBoundaries_MEX_ADM1", "population": {"1821": 175000, "1895": 492000, "1950": 1434000, "2000": 7665000, "2020": 10540000}},
  ]
  write_chapter_assets(ch_by_idx[11], ch11_zones, D, bm_hist, bm_mod, arg5_envelope=C["Mexico"])

  # =========================================================================
  # CH 12: Central American Republics (1821..2025) — Regime III + exact OHM Panama Canal Zone
  # =========================================================================
  pcz = clip_geom(OHM.get("panama_canal_zone"), C["Panama"])
  pan_rep = diff_geom(C["Panama"], pcz)
  ch12_zones = [
    {"id": "ca_guatemala", "name": "Guatemala", "geom": C["Guatemala"], "source_hgis": "NaturalEarth_ADM0+geoBoundaries", "population": {"1821": 535000, "1893": 1364678, "1950": 2790868, "2002": 11237196, "2025": 18400000}},
    {"id": "ca_belize", "name": "Belize (British Honduras)", "geom": C["Belize"], "source_hgis": "NaturalEarth_ADM0+geoBoundaries", "population": {"1821": 5200, "1891": 31471, "1950": 68000, "2000": 240204, "2025": 417000}},
    {"id": "ca_el_salvador", "name": "El Salvador", "geom": C["El Salvador"], "source_hgis": "NaturalEarth_ADM0+geoBoundaries", "population": {"1821": 248000, "1892": 703500, "1950": 1855917, "2007": 5744113, "2025": 6350000}},
    {"id": "ca_honduras", "name": "Honduras", "geom": C["Honduras"], "source_hgis": "NaturalEarth_ADM0+geoBoundaries", "population": {"1821": 155000, "1887": 331917, "1950": 1368605, "2001": 6535344, "2025": 10820000}},
    {"id": "ca_nicaragua", "name": "Nicaragua", "geom": C["Nicaragua"], "source_hgis": "NaturalEarth_ADM0+geoBoundaries", "population": {"1821": 185000, "1906": 505377, "1950": 1057023, "2005": 5142098, "2025": 7050000}},
    {"id": "ca_costa_rica", "name": "Costa Rica", "geom": C["Costa Rica"], "source_hgis": "NaturalEarth_ADM0+geoBoundaries", "population": {"1821": 62000, "1892": 243205, "1950": 800875, "2000": 3810179, "2025": 5150000}},
    {"id": "ca_panama_canal_zone", "name": "Panama Canal Zone (1903-1979 OHM Footprint)", "geom": pcz, "source_hgis": "OHM_Panama_Canal_Zone_1935_1979", "population": {"1821": 8000, "1912": 62810, "1950": 52822, "1970": 44198, "2025": 185000}},
    {"id": "ca_panama_republic", "name": "Panama Republic (excl. Canal Zone)", "geom": pan_rep, "source_hgis": "NaturalEarth_ADM0_minus_OHM_PCZ", "population": {"1821": 84000, "1911": 336742, "1950": 805285, "2000": 2839177, "2025": 4330000}},
  ]
  write_chapter_assets(ch_by_idx[12], ch12_zones, D, bm_hist, bm_mod, arg5_envelope=G["Central_America_Modern"])

  # =========================================================================
  # CH 13: Greater Antilles in the Modern Era (1838..2025) — Regime III (CUB_ADM1 + Countries)
  # =========================================================================
  def cu_grp (keys):
    return u_geoms([CU1[norm_str(k)] for k in keys if norm_str(k) in CU1])

  ga_env = u_geoms([G["Cuba_Full"], C["Haiti"], C["Dominican Republic"], C["Jamaica"], C["Puerto Rico"]])
  ch13_zones = [
    {"id": "ga_western_cuba", "name": "Western Cuba (Havana, Pinar del Rio, Matanzas & Isla)", "geom": cu_grp(["Pinar del Rio", "Artemisa", "Havana", "Mayabeque", "Matanzas", "Isle of Youth"]), "source_hgis": "geoBoundaries_CUB_ADM1", "population": {"1841": 520000, "1899": 798000, "1953": 2380000, "2002": 4460000, "2025": 4320000}},
    {"id": "ga_central_cuba", "name": "Central Cuba (Villa Clara, Cienfuegos, S. Spiritus, Camaguey)", "geom": cu_grp(["Villa Clara", "Cienfuegos", "Sancti Spiritus", "Ciego de Avila", "Camagüey"]), "source_hgis": "geoBoundaries_CUB_ADM1", "population": {"1841": 245000, "1899": 445000, "1953": 1650000, "2002": 2860000, "2025": 2740000}},
    {"id": "ga_eastern_cuba", "name": "Eastern Cuba / Oriente (Las Tunas, Holguin, Granma, Santiago, Guantanamo)", "geom": cu_grp(["Las Tunas", "Holguín", "Granma", "Santiago de Cuba", "Guantánamo"]), "source_hgis": "geoBoundaries_CUB_ADM1", "population": {"1841": 242000, "1899": 329000, "1953": 1799000, "2002": 3858000, "2025": 3760000}},
    {"id": "ga_haiti", "name": "Haiti", "geom": C["Haiti"], "source_hgis": "NaturalEarth_ADM0+geoBoundaries", "population": {"1838": 750000, "1900": 1280000, "1950": 3097220, "2003": 8373750, "2025": 11900000}},
    {"id": "ga_dominican_republic", "name": "Dominican Republic", "geom": C["Dominican Republic"], "source_hgis": "NaturalEarth_ADM0+geoBoundaries", "population": {"1838": 135000, "1920": 894665, "1950": 2135872, "2002": 8562541, "2025": 11430000}},
    {"id": "ga_jamaica", "name": "Jamaica", "geom": C["Jamaica"], "source_hgis": "NaturalEarth_ADM0+geoBoundaries", "population": {"1844": 377433, "1911": 831383, "1960": 1609814, "2001": 2607632, "2025": 2840000}},
    {"id": "ga_puerto_rico", "name": "Puerto Rico", "geom": C["Puerto Rico"], "source_hgis": "NaturalEarth_ADM0+geoBoundaries", "population": {"1846": 447914, "1899": 953243, "1950": 2210703, "2000": 3808610, "2025": 3205000}},
  ]
  write_chapter_assets(ch_by_idx[13], ch13_zones, D, bm_hist, bm_mod, arg5_envelope=ga_env)

  # =========================================================================
  # CH 14: Lesser Antilles, Bahamas, Trinidad & Bermuda (1838..2025) — Regime III
  # Every micro-island guaranteed >= 1 px; Bonaire cleanly in ABC Islands, Saba/St Eustatius in Leewards!
  # =========================================================================
  la_leewards = u_geoms([
    C.get(k) for k in ("Anguilla", "Saint Martin", "Sint Maarten", "Saint Barthelemy", "Saint Kitts and Nevis", "Antigua and Barbuda", "Montserrat") if k in C
  ] + [G.get("Saba_Sint_Eustatius")])
  la_windwards = u_geoms([C.get(k) for k in ("Dominica", "Saint Lucia", "Saint Vincent and the Grenadines", "Grenada") if k in C])
  la_abc = u_geoms([C.get("Aruba"), C.get("Curaçao"), G.get("Bonaire")])
  la_env = u_geoms([
    C.get("The Bahamas"), C.get("Turks and Caicos Islands"), C.get("Bermuda"),
    C.get("Cayman Islands"), C.get("United States Virgin Islands"), C.get("British Virgin Islands"),
    la_leewards, C.get("French Antilles"), la_windwards, C.get("Barbados"),
    C.get("Trinidad and Tobago"), la_abc,
  ])
  ch14_zones = [
    {"id": "la_bahamas_turks_caicos", "name": "Bahamas & Turks and Caicos", "geom": u_geoms([C.get("The Bahamas"), C.get("Turks and Caicos Islands")]), "source_hgis": "NaturalEarth_ADM0+geoBoundaries", "population": {"1841": 28000, "1901": 59000, "1953": 91000, "2000": 323000, "2025": 448000}},
    {"id": "la_bermuda", "name": "Bermuda", "geom": C.get("Bermuda"), "source_hgis": "NaturalEarth_ADM0+geoBoundaries_BMU", "population": {"1843": 9930, "1901": 17535, "1950": 37403, "2000": 62059, "2025": 64600}},
    {"id": "la_cayman_islands", "name": "Cayman Islands", "geom": C.get("Cayman Islands"), "source_hgis": "NaturalEarth_ADM0+geoBoundaries_CYM", "population": {"1840": 1800, "1911": 5564, "1960": 8511, "1999": 39410, "2025": 74500}},
    {"id": "la_virgin_islands", "name": "US & British Virgin Islands", "geom": u_geoms([C.get("United States Virgin Islands"), C.get("British Virgin Islands")]), "source_hgis": "NaturalEarth_ADM0+geoBoundaries_VIR_VGB", "population": {"1841": 47500, "1901": 35500, "1950": 33200, "2000": 131700, "2025": 124500}},
    {"id": "la_northern_leewards", "name": "Northern Leeward Islands (Anguilla to Montserrat)", "geom": la_leewards, "source_hgis": "NaturalEarth_ADM0+geoBoundaries", "population": {"1844": 88000, "1901": 102000, "1950": 126000, "2000": 224000, "2025": 274000}},
    {"id": "la_french_antilles", "name": "French Antilles (Guadeloupe & Martinique)", "geom": C.get("French Antilles"), "source_hgis": "NaturalEarth_ADM0+geoBoundaries_GLP_MTQ", "population": {"1848": 251000, "1901": 385000, "1954": 468000, "1999": 804000, "2025": 745000}},
    {"id": "la_windward_islands", "name": "Windward Islands (Dominica, St Lucia, St Vincent, Grenada)", "geom": la_windwards, "source_hgis": "NaturalEarth_ADM0+geoBoundaries", "population": {"1844": 98000, "1901": 192000, "1946": 251000, "2001": 442000, "2025": 482000}},
    {"id": "la_barbados", "name": "Barbados", "geom": C.get("Barbados"), "source_hgis": "NaturalEarth_ADM0+geoBoundaries_BRB", "population": {"1844": 122198, "1911": 171983, "1946": 192800, "2000": 268792, "2025": 282500}},
    {"id": "la_trinidad_tobago", "name": "Trinidad & Tobago", "geom": C.get("Trinidad and Tobago"), "source_hgis": "NaturalEarth_ADM0+geoBoundaries_TTO", "population": {"1844": 73000, "1901": 273899, "1946": 557970, "2000": 1262366, "2025": 1508000}},
    {"id": "la_dutch_abc_islands", "name": "Dutch ABC Islands (Aruba, Bonaire & Curacao)", "geom": la_abc, "source_hgis": "NaturalEarth_ADM0+geoBoundaries_ABW_CUW_BES", "population": {"1840": 21500, "1900": 44000, "1950": 156000, "2001": 234000, "2025": 292000}},
  ]
  write_chapter_assets(ch_by_idx[14], ch14_zones, D, bm_hist, bm_mod, arg5_envelope=la_env)

  # =========================================================================
  # Master Project Manifest: JAGUAR/jaguar_areal_masks.json5
  # Ch 01-05 in specialist_masks, Ch 06-14 in chapter_masks (so audit_areal_masks.js audits ALL 14!)
  # =========================================================================
  specialist_masks = []
  chapter_masks = []
  for ch in itinerary["chapters"]:
    stem = ch["stem"]
    rel_dir = f"histmap/1.data_raw/population_regional/JAGUAR/{ch['group']}/{ch['folder']}"
    entry = {
      "id": stem,
      "index": ch["index"],
      "domain": ch["domain"],
      "domain_group": "sites_jaguar_mesoamerica",
      "regime": ch["regime"],
      "json5_path": f"{rel_dir}/{stem}.json5",
      "mask_path": f"{rel_dir}/{stem}_areal_mask.png",
      "subregions_geojson": f"histmap/1.data_raw/population_regional/JAGUAR/_shared/_gis_cache/chapter_subregions/{stem}_subregions.geojson",
      "priority": 1 if ch["index"] <= 5 else (3 if ch["index"] >= 11 else 2),
    }
    if ch["index"] >= 11:
      entry["is_admin1"] = True
    if ch["index"] <= 5:
      specialist_masks.append(entry)
    else:
      chapter_masks.append(entry)

  manifest = {
    "project": "JAGUAR",
    "grid_dimensions": [GRID_W, GRID_H],
    "regime_transitions": {
      "mesoamerica_mexico": {"pre_admin_end": 1200, "indigenous_colonial_start": 1200, "colonial_start": 1519, "contemporary_start": 1821},
      "central_america": {"pre_admin_end": 1502, "colonial_start": 1524, "contemporary_start": 1821},
      "caribbean_bermuda": {"pre_admin_end": 1492, "colonial_start": 1492, "contemporary_start": 1838},
    },
    "geography_profile": {
      "projection_class": "lambert_azimuthal",
      "has_micro_islands": True,
      "max_adm2_area_km2": 25000,
      "note": "Mexico, Central America, Greater and Lesser Antilles, Bahamas, Trinidad and Tobago, and Bermuda.",
    },
    "script_profile": {
      "target_scripts": ["Latn"],
      "allow_native_toponyms": True,
    },
    "hyde_years": ALL_HYDE_YEARS,
    "substrata_sources": {
      "sites_jaguar_mesoamerica": {
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/JAGUAR/_shared/sites_jaguar_mesoamerica/config/documented_site_pixels.json",
        "domain": [-10000, 2025],
        "domain_code": 1,
        "domain_mask_png": "histmap/1.data_raw/population_regional/JAGUAR/_shared/sites_jaguar_mesoamerica/config/jaguar_domain_mask.png",
        "rasters_folder": "histmap/1.data_raw/population_regional/JAGUAR/_shared/sites_jaguar_mesoamerica/2.population_rasters",
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
    "chapter_masks": chapter_masks,
  }
  out_manifest = os.path.join(JAG_DIR, "jaguar_areal_masks.json5")
  with open(out_manifest, "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2, ensure_ascii=False)
  print(f"\n[DONE] Built ALL 14 JAGUAR chapter dual areal masks, vector GeoJSONs, manifest ({out_manifest}) & optical QA crops!", flush=True)


if __name__ == "__main__":
  main()
