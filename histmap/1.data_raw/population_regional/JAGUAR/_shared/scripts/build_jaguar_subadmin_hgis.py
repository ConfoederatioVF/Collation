"""Builds ALL 118 Overlapping AD HYDE Sub-Administrative Historical GIS GeoPNG Rasters
(`subadmin_id_<year>.png`), Longitudinal Metadata (`subadmin_meta_<year>.json`),
Literature-Review Enumeration Exports, and Representative Optical QA Crop PNGs for
Operation Viscount Project JAGUAR (Mexico, Central America, Caribbean & Bermuda).

STRICT DESIGN GUARANTEES:
  1. ALL 118 OVERLAPPING AD HYDE YEARS:
     - Every 100 years 0..1700 AD (18 snapshots)
     - Every 10 years 1710..1950 AD (25 snapshots)
     - Every 1 year 1951..2025 AD (75 snapshots)
  2. STRICT Z-INDEX LAYERING:
     - z = 0.5: HydroBASINS L6 / Caribbean physical archipelago base (pre-1500 coverage floor)
     - z = 1.0: `atlas_defacto_jaguar_cache.json` (STRICTLY fallback ONLY!)
     - z = 2.0: `atlas_dejure_jaguar_cache.json` & `CShapes 2.0` (1886+)
     - z = 3.0: `ohm_jaguar_boundaries.geojson` (date-filtered start_date <= yr <= end_date)
     - z = 4.0: Period-specific academic HGIS (DECM, HGIS de las Indias, Bexar 1824 Mexico,
                Lurtz 1900 Mexico, OHM Panama Canal Zone 1903-1979, geoBoundaries ADM1/ADM0),
                joined directly with `jaguar_subadmin_enumerations.json` (543 units, 3,785 obs).
  3. ZERO SCANLINE DEFECTS & MICRO-ISLAND PRESERVATION:
     - Scanline-free OpenCV `cv2.fillPoly(..., shift=4)` with local interior-hole subtraction
       and guaranteed non-zero pixel retention for Bermuda and Lesser Antilles micro-islands.
"""

import csv
import json
import math
import os
import re
from collections import defaultdict

import numpy as np
from PIL import Image
from shapely.geometry import shape

from jaguar_hgis_utils import (
  ALL_HYDE_AD_YEARS,
  DOMAIN_MASK_PNG,
  HGIS_PARSED,
  HGIS_RASTERS,
  HGIS_RAW,
  HGIS_ROOT,
  JAG_GIS,
  LAND_AREA_PNG,
  TESTS_SUBADMIN_CROPS,
  build_organic_mosquitia_geom,
  clip_geom,
  cv2_rasterise_subadmin_units,
  diff_geom,
  dissolve_hgis_indias_by_year,
  fill_small_holes,
  group_basins,
  interp_dict,
  iter_polys,
  load_hgis_indias_lcg,
  load_hydrobasins_jaguar,
  norm_str,
  render_jaguar_subadmin_crop_png,
  safe_geom,
  u_geoms,
)

os.makedirs(HGIS_RASTERS, exist_ok=True)
os.makedirs(TESTS_SUBADMIN_CROPS, exist_ok=True)

# Representative QA crop years required for optical inspection by mask_auditor
QA_CROP_YEARS = {1500, 1600, 1790, 1824, 1850, 1900, 1920, 1950, 1975, 2000, 2020}

# Map geoBoundaries ISO3 ADM1 files -> country display name used in jaguar_subadmin_enumerations.json
GB_ADM1_COUNTRIES = {
  "MEX": "Mexico",
  "GTM": "Guatemala",
  "BLZ": "Belize",
  "HND": "Honduras",
  "SLV": "El Salvador",
  "NIC": "Nicaragua",
  "CRI": "Costa Rica",
  "PAN": "Panama",
  "CUB": "Cuba",
  "HTI": "Haiti",
  "DOM": "Dominican Republic",
  "JAM": "Jamaica",
  "TTO": "Trinidad and Tobago",
  "BRB": "Barbados",
  "BHS": "The Bahamas",
  "ATG": "Antigua and Barbuda",
  "DMA": "Dominica",
  "GRD": "Grenada",
  "KNA": "Saint Kitts and Nevis",
  "LCA": "Saint Lucia",
  "VCT": "Saint Vincent and the Grenadines",
}

GB_ADM0_TERRITORIES = {
  "BMU": "Bermuda",
  "GLP": "Guadeloupe",
  "MTQ": "Martinique",
  "CYM": "Cayman Islands",
  "TCA": "Turks and Caicos Islands",
  "VIR": "United States Virgin Islands",
  "VGB": "British Virgin Islands",
  "ABW": "Aruba",
  "CUW": "Curaçao",
  "AIA": "Anguilla",
  "MSR": "Montserrat",
  "BLM": "Saint Barthelemy",
  "BES": "Caribbean Netherlands",
}

# Colonial HGIS de las Indias entity ID -> jaguar_subadmin_enumerations key
INDIAS_TO_ENUM = {
  "PRNEMX00": ("colonial_new_spain_1570_1810", "int_mexico"),
  "PRNEPU00": ("colonial_new_spain_1570_1810", "int_puebla"),
  "PRNEVC00": ("colonial_new_spain_1570_1810", "int_veracruz"),
  "PRNEOA00": ("colonial_new_spain_1570_1810", "int_oaxaca"),
  "PRNEMI00": ("colonial_new_spain_1570_1810", "int_valladolid_michoacan"),
  "PRNEGJ00": ("colonial_new_spain_1570_1810", "int_guanajuato"),
  "PRGDGD00": ("colonial_new_spain_1570_1810", "int_guadalajara"),
  "PRGDZA00": ("colonial_new_spain_1570_1810", "int_zacatecas"),
  "PRNESL00": ("colonial_new_spain_1570_1810", "int_san_luis_potosi"),
  "PRNEYU00": ("colonial_new_spain_1570_1810", "int_merida_yucatan"),
  "PRGDDU00": ("colonial_new_spain_1570_1810", "int_durango"),
  "PRGDSS00": ("colonial_new_spain_1570_1810", "int_sonora"),
  "PRNECL00": ("colonial_new_spain_1570_1810", "prov_antigua_california"),
  "PRGUGU00": ("colonial_central_america_1778_1816", "cgg_guatemala_prov"),
  "PRGUCH00": ("colonial_central_america_1778_1816", "cgg_chiapas_prov"),
  "PRGUSS00": ("colonial_central_america_1778_1816", "cgg_el_salvador_prov"),
  "PRGUCY00": ("colonial_central_america_1778_1816", "cgg_honduras_prov"),
  "PRGUNI00": ("colonial_central_america_1778_1816", "cgg_nicaragua_prov"),
  "PRGUCR00": ("colonial_central_america_1778_1816", "cgg_costa_rica_prov"),
  "PRNGPA00": ("colonial_central_america_1778_1816", "pa_1778_panama"),
  "PRNGVE00": ("colonial_central_america_1778_1816", "pa_1778_veraguas"),
  "PRNGDA00": ("colonial_central_america_1778_1816", "pa_1778_darien"),
  "PRSDLH00": ("colonial_caribbean_bermuda_1655_1899", "cu_colonial_total"),
  "PRSDCU00": ("colonial_caribbean_bermuda_1655_1899", "cu_colonial_total"),
  "PRSDPR00": ("colonial_caribbean_bermuda_1655_1899", "pr_colonial_total"),
  "PRSDSD00": ("colonial_caribbean_bermuda_1655_1899", "do_colonial_santo_domingo"),
}


def parse_ohm_year (arg0_val, arg1_default):
  s = str(arg0_val or "").strip()
  if not s:
    return arg1_default
  m = re.match(r"^(-?\d{1,4})", s)
  return int(m.group(1)) if m else arg1_default


def get_boundary_regime_key (arg0_yr):
  """Maps each of the 118 overlapping AD HYDE years to its distinct historical boundary regime."""
  yr = int(arg0_yr)
  if yr <= 1700:
    return yr  # Every century 0..1700 has its own regime (18 regimes)
  if yr <= 1780:
    return 1750  # Pre-Intendancy 18th-c. Bourbon Spanish America & Plantation Caribbean
  if yr <= 1810:
    return 1790  # Bourbon Intendancies (HGIS de las Indias 1790 + Saint-Domingue 1789)
  if yr <= 1840:
    return 1824  # First Federal Republic of Mexico (Bexar 1824) & Central America Federation
  if yr <= 1880:
    return 1850  # Mid-19th c. Republican Mexico (Guerrero 1849, Campeche 1858, Hidalgo/Morelos 1869)
  if yr <= 1900:
    return 1900  # Porfirian Mexico (Lurtz 1900 30 states; pre-Quintana Roo; pre-Canal Zone)
  if yr <= 1916:
    return 1910  # Quintana Roo Territory (1902+), Panama Canal Zone (1903+), Tepic Territory
  if yr <= 1930:
    return 1920  # Post-Revolution Mexico (Nayarit 1917, unified Baja California), Canal Zone
  if yr <= 1973:
    return 1950  # Mid-20th c. Census Era (Baja California N/S split, Canal Zone active, pre-1976 Cuba)
  if yr <= 1979:
    return 1975  # Quintana Roo & BCS Statehood (1974), Cuba 14-Province Reform (1976), Canal Zone
  if yr <= 2010:
    return 2000  # Post-Canal Zone Handover (1980+), Contemporary ADM1 (pre-2011 Cuba split)
  return 2020    # Contemporary 2011-2025 ADM1 (Cuba 16 provinces incl. Artemisa & Mayabeque)


def load_all_subadmin_sources ():
  print("[1] Loading ALL JAGUAR HGIS layers, Naissance caches, OHM, CShapes, HGIS Indias, Bexar 1824, Lurtz 1900 & geoBoundaries...", flush=True)
  src = {}

  # 1. Domain countries & coastal land union
  c_gj = json.load(open(os.path.join(JAG_GIS, "jaguar_countries.geojson"), encoding="utf-8"))
  countries = {}
  for f in c_gj["features"]:
    nm = f["properties"]["ADMIN"]
    g = safe_geom(shape(f["geometry"]))
    if g is not None:
      countries[nm] = g
  jag_union = u_geoms(list(countries.values()))
  src["countries"] = countries
  src["jag_union"] = jag_union

  # 2. Sub-administrative enumerations index (543 units across 9 era buckets)
  enums_raw = json.load(open(os.path.join(HGIS_PARSED, "jaguar_subadmin_enumerations.json"), encoding="utf-8"))
  src["enums"] = enums_raw
  # Build fast lookup by (country_norm, unit_name_norm) across eras
  enum_by_country = defaultdict(list)
  for era, umap in enums_raw.items():
    for ukey, urec in umap.items():
      c_norm = norm_str(urec.get("admin_country") or "")
      u_norm = norm_str(urec.get("name") or ukey)
      ser = {int(y): float(v) for y, v in (urec.get("years") or {}).items() if v is not None and float(v) >= 0}
      if not ser:
        continue
      enum_by_country[c_norm].append({
        "era": era,
        "key": ukey,
        "name": urec.get("name") or ukey,
        "norm": u_norm,
        "level": urec.get("level") or "",
        "series": ser,
      })
  src["enum_by_country"] = dict(enum_by_country)

  # 3. Naissance caches: atlas_defacto (STRICTLY z=1 fallback!) & atlas_dejure (z=2)
  def load_nc (fn):
    raw = json.load(open(os.path.join(HGIS_PARSED, fn), encoding="utf-8"))
    out = {}
    for yk, recs in raw.items():
      flist = []
      for r in recs:
        g = clip_geom(shape(r["geometry"]), jag_union)
        if g is not None and g.area > 0.0005:
          flist.append({"id": r["id"], "name": r["name"], "geom": g})
      out[int(yk)] = flist
    return out

  src["atlas_defacto"] = load_nc("atlas_defacto_jaguar_cache.json")
  src["atlas_dejure"] = load_nc("atlas_dejure_jaguar_cache.json")
  print(f"  Naissance caches: defacto={len(src['atlas_defacto'])} yrs | dejure={len(src['atlas_dejure'])} yrs", flush=True)

  # 4. HydroBASINS L6 pre-Columbian organic watersheds (z=0.5 base for yr <= 1500)
  basins = load_hydrobasins_jaguar(jag_union)
  mainland = u_geoms([countries[k] for k in ("Mexico", "Guatemala", "Belize", "El Salvador", "Honduras", "Nicaragua", "Costa Rica", "Panama") if k in countries])
  def clf_pre (lat, lon, pfaf, mb):
    if lon > -87.45 or (lon > -88.25 and lat < 13.75) or lat < 13.2:
      if lon >= -80.1: return "pre_gran_darien"
      if lon >= -81.75: return "pre_gran_cocle"
      if lat < 10.25 and lon >= -84.95: return "pre_chiriqui_central_valley"
      if lat >= 13.7: return "pre_mosquitia_honduras"
      return "pre_nicaragua_nicoya"
    if lon >= -93.85 or (lon >= -94.25 and lat < 17.6):
      if lat >= 18.65: return "pre_maya_north_yucatan"
      if lon >= -89.25 and lat >= 15.65: return "pre_maya_belize"
      if lon >= -89.85 and lat < 15.65: return "pre_maya_copan_motagua"
      if lon < -91.75 and lat < 17.65: return "pre_maya_chiapas_grijalva"
      if lat >= 15.75: return "pre_maya_peten_usumacinta"
      return "pre_maya_guatemala_highlands"
    if lon < -109.5 or lat >= 25.4 or (lon > -100.8 and lat >= 22.8): return "pre_aridoamerica_baja"
    if lon < -105.0 and lat >= 21.8: return "pre_sierra_madre_sonora"
    if (lon >= -97.6 and lat >= 17.3) or (lon >= -98.4 and 20.5 <= lat < 22.8): return "pre_gulf_olmec_huasteca"
    if lat < 17.85 and lon >= -98.65: return "pre_oaxaca_mixteca"
    if lon >= -100.55 and lat < 20.85: return "pre_basin_mexico_highlands"
    if lat >= 20.85: return "pre_bajio_north_central"
    return "pre_west_mexico_santiago_balsas"

  pre_basins = group_basins(basins, clf_pre, arg2_clip_geom=mainland)
  # Add Caribbean Pre-Columbian zones
  pre_basins["pre_cuba"] = u_geoms([countries.get("Cuba"), countries.get("US Naval Base Guantanamo Bay")])
  pre_basins["pre_hispaniola"] = u_geoms([countries.get("Haiti"), countries.get("Dominican Republic")])
  pre_basins["pre_jamaica_cayman"] = u_geoms([countries.get("Jamaica"), countries.get("Cayman Islands")])
  pre_basins["pre_puerto_rico_vi"] = u_geoms([countries.get("Puerto Rico"), countries.get("United States Virgin Islands"), countries.get("British Virgin Islands")])
  pre_basins["pre_lucayan_bahamas"] = u_geoms([countries.get("The Bahamas"), countries.get("Turks and Caicos Islands")])
  pre_basins["pre_lesser_antilles"] = u_geoms([countries.get(k) for k in ("Anguilla", "Saint Martin", "Sint Maarten", "Saint Barthelemy", "Saint Kitts and Nevis", "Antigua and Barbuda", "Montserrat", "French Antilles", "Dominica", "Saint Lucia", "Saint Vincent and the Grenadines", "Grenada", "Barbados", "Caribbean Netherlands") if k in countries])
  pre_basins["pre_trinidad_abc"] = u_geoms([countries.get("Trinidad and Tobago"), countries.get("Aruba"), countries.get("Curaçao")])
  pre_basins["pre_bermuda_uninhabited"] = countries.get("Bermuda")
  src["pre_zones"] = pre_basins

  # 5. CShapes 2.0 (1886-2019, z=2)
  cs_gj = json.load(open(os.path.join(HGIS_RAW, "cshapes_jaguar.geojson"), encoding="utf-8"))
  cshapes = []
  for f in cs_gj["features"]:
    p = f["properties"]
    g = clip_geom(shape(f["geometry"]), jag_union)
    if g is None or g.area < 0.001:
      continue
    cshapes.append({
      "name": str(p.get("cntry_name") or ""),
      "y0": int(p.get("gwsyear") or 1886),
      "y1": int(p.get("gweyear") or 2019),
      "geom": g,
    })
  src["cshapes"] = cshapes

  # 6. OHM Boundaries (z=3 + specific named polygons for z=4)
  ohm_gj = json.load(open(os.path.join(HGIS_RAW, "ohm_jaguar_boundaries.geojson"), encoding="utf-8"))
  ohm_feats = []
  ohm_special = {}
  for f in ohm_gj["features"]:
    p = f["properties"]
    nm = str(p.get("name") or "")
    sd_s = str(p.get("start_date") or "")
    ed_s = str(p.get("end_date") or "")
    y0 = parse_ohm_year(sd_s, -1000)
    y1 = parse_ohm_year(ed_s, 2026)
    lvl = str(p.get("admin_level") or "4")
    g = clip_geom(shape(f["geometry"]), jag_union)
    if g is None or g.area < 0.0005:
      continue
    ohm_feats.append({"name": nm, "y0": y0, "y1": y1, "lvl": lvl, "geom": g})
    if nm == "Panama Canal Zone" and sd_s.startswith("1935"):
      ohm_special["panama_canal_zone"] = g
    elif nm == "Saint-Domingue" and sd_s.startswith("1697"):
      ohm_special["saint_domingue_1697"] = g
    elif nm == "Mosquito Kingdom" and sd_s.startswith("1740"):
      ohm_special["mosquito_kingdom"] = g
    elif nm == "Settlement of British Honduras" and sd_s.startswith("1841"):
      ohm_special["british_honduras_early"] = g
    elif nm == "Territorio de Quintana Roo" and sd_s.startswith("1902"):
      ohm_special["quintana_roo_1902"] = g
  src["ohm"] = ohm_feats
  src["ohm_special"] = ohm_special
  print(f"  OHM clipped features: {len(ohm_feats)} | CShapes: {len(cshapes)}", flush=True)

  # 7. HGIS de las Indias (the_geom.gpkg + Niveles.tab) for 1705, 1750, 1790 + Audiencia & Fronteras
  lcg_geoms, niveles_rows = load_hgis_indias_lcg(jag_union)
  src["indias"] = {
    1705: dissolve_hgis_indias_by_year(lcg_geoms, niveles_rows, 1705, "Provincia"),
    1750: dissolve_hgis_indias_by_year(lcg_geoms, niveles_rows, 1750, "Provincia"),
    1790: dissolve_hgis_indias_by_year(lcg_geoms, niveles_rows, 1790, "Provincia"),
  }
  src["indias_aud"] = dissolve_hgis_indias_by_year(lcg_geoms, niveles_rows, 1750, "Audiencia")
  src["indias_pm90"] = dissolve_hgis_indias_by_year(lcg_geoms, niveles_rows, 1790, "Provincia_menor")
  indias_f90 = dissolve_hgis_indias_by_year(lcg_geoms, niveles_rows, 1790, "Fronteras")
  src["indias_f90"] = indias_f90
  src["organic_mosquitia"] = build_organic_mosquitia_geom(
    basins, indias_f90, u_geoms([countries["Honduras"], countries["Nicaragua"]])
  )
  print(f"  HGIS de las Indias dissolved provinces: 1705={len(src['indias'][1705])} | 1750={len(src['indias'][1750])} | 1790={len(src['indias'][1790])}", flush=True)

  # 8. Academic Mexico 1824 (Bexar) & 1900 (Lurtz)
  bex_gj = json.load(open(os.path.join(HGIS_RAW, "academic_mexico_panama", "bexar_mexico_1824_regions.geojson"), encoding="utf-8"))
  bex_list = []
  for f in bex_gj["features"]:
    nm = str(f["properties"].get("ADM1_ES") or f["properties"].get("NAME") or "")
    g = clip_geom(shape(f["geometry"]), countries["Mexico"])
    if g is not None and g.area > 0.001:
      bex_list.append({"name": nm, "norm": norm_str(nm), "geom": g})
  src["bexar_1824"] = bex_list

  lurtz_gj = json.load(open(os.path.join(HGIS_RAW, "academic_mexico_panama", "lurtz_mexico_1900_states.geojson"), encoding="utf-8"))
  lurtz_list = []
  for f in lurtz_gj["features"]:
    nm = str(f["properties"].get("St_1900") or "")
    g = clip_geom(shape(f["geometry"]), countries["Mexico"])
    if g is not None and g.area > 0.001:
      lurtz_list.append({"name": nm, "norm": norm_str(nm), "geom": g})
  src["lurtz_1900"] = lurtz_list
  print(f"  Academic Mexico: Bexar 1824={len(bex_list)} units | Lurtz 1900={len(lurtz_list)} units", flush=True)

  # 9. geoBoundaries ADM1 (21 countries) + PRI_ADM2 (dissolved to 1 PR unit) + ADM0 (13 territories)
  gb_dir = os.path.join(HGIS_RAW, "geoboundaries")
  gb_adm1 = {}
  for iso, c_nm in GB_ADM1_COUNTRIES.items():
    fp = os.path.join(gb_dir, f"{iso}_ADM1.geojson")
    if not os.path.exists(fp):
      continue
    gj = json.load(open(fp, encoding="utf-8"))
    ulist = []
    for idx, f in enumerate(gj["features"]):
      nm = str(f["properties"].get("shapeName") or f"{iso}_{idx}")
      g = clip_geom(shape(f["geometry"]), jag_union)
      if g is not None and g.area > 1e-5:
        ulist.append({"code": f"{iso}_{idx:02d}", "name": nm, "norm": norm_str(nm), "country": c_nm, "geom": g})
    gb_adm1[iso] = ulist
  src["gb_adm1"] = gb_adm1

  gb_adm0 = {}
  for iso, c_nm in GB_ADM0_TERRITORIES.items():
    fp = os.path.join(gb_dir, f"{iso}_ADM0.geojson")
    if not os.path.exists(fp):
      continue
    gj = json.load(open(fp, encoding="utf-8"))
    gs = [clip_geom(shape(f["geometry"]), jag_union) for f in gj["features"]]
    ug = u_geoms(gs)
    if ug is not None:
      gb_adm0[iso] = {"code": iso, "name": c_nm, "country": c_nm, "geom": ug}
  # Add Puerto Rico from PRI_ADM2 dissolved + Saint Martin / Sint Maarten from Natural Earth
  pri_fp = os.path.join(gb_dir, "PRI_ADM2.geojson")
  if os.path.exists(pri_fp):
    pri_gj = json.load(open(pri_fp, encoding="utf-8"))
    pri_u = u_geoms([clip_geom(shape(f["geometry"]), jag_union) for f in pri_gj["features"]])
    if pri_u is not None:
      gb_adm0["PRI"] = {"code": "PRI", "name": "Puerto Rico", "country": "Puerto Rico", "geom": pri_u}
  for iso, c_nm in [("MAF", "Saint Martin"), ("SXM", "Sint Maarten")]:
    if c_nm in countries:
      gb_adm0[iso] = {"code": iso, "name": c_nm, "country": c_nm, "geom": countries[c_nm]}
  src["gb_adm0"] = gb_adm0
  src["baja_unified"] = u_geoms([
    u["geom"] for u in gb_adm1.get("MEX", []) if u["norm"] in ("baja california", "baja california sur")
  ])
  print(f"  geoBoundaries: {len(gb_adm1)} ADM1 countries ({sum(len(v) for v in gb_adm1.values())} units) + {len(gb_adm0)} ADM0 territories", flush=True)
  return src


def match_enumeration (arg0_src, arg1_country, arg2_unit_name, arg3_preferred_eras=None):
  """Matches a sub-administrative unit to its longitudinal census/enumeration series."""
  c_norm = norm_str(arg1_country)
  u_norm = norm_str(arg2_unit_name)
  cands = arg0_src["enum_by_country"].get(c_norm, [])
  if not cands:
    return None

  # Filter by preferred eras first if supplied
  pools = []
  if arg3_preferred_eras:
    pref = [c for c in cands if c["era"] in arg3_preferred_eras]
    if pref:
      pools.append(pref)
  pools.append(cands)

  for pool in pools:
    # 1. Exact normalised name match
    for c in pool:
      if c["norm"] == u_norm:
        return c["series"]
    # 2. Substring / token match (e.g. "Veracruz" vs "Veracruz de Ignacio de la Llave", "Distrito Federal" vs "Ciudad de Mexico")
    best = None
    best_sc = 0
    u_toks = set(u_norm.split()) - {"de", "del", "la", "las", "los", "el", "y", "san", "santa", "saint", "st", "province", "state", "territorio", "departamento", "parish", "district"}
    for c in pool:
      if u_norm in c["norm"] or c["norm"] in u_norm:
        sc = min(len(u_norm), len(c["norm"])) + 10
        if sc > best_sc:
          best_sc = sc
          best = c
      elif u_toks:
        c_toks = set(c["norm"].split())
        ov = len(u_toks & c_toks)
        if ov > 0 and ov >= len(u_toks) * 0.6:
          sc = ov * 5
          if sc > best_sc:
            best_sc = sc
            best = c
    if best is not None:
      return best["series"]

  # 3. Country-level total fallback (for single-unit islands/colonies)
  for pool in pools:
    for c in pool:
      if any(t in c["key"] for t in ("total", "colony", "island", "colonial")):
        return c["series"]
  return None


def nearest_cache_year (arg0_cache, arg1_yr):
  yrs = sorted(arg0_cache.keys())
  return min(yrs, key=lambda y: abs(y - int(arg1_yr)))


def build_regime_units (arg0_reg_yr, arg1_src):
  """Constructs strictly non-anachronistic z-indexed sub-admin units for `arg0_reg_yr`."""
  reg_yr = int(arg0_reg_yr)
  C = arg1_src["countries"]
  enums = arg1_src["enums"]
  units = []
  next_id = [1]

  def add_unit (code, name, country, geom, series_or_val, source, is_direct, priority):
    g = safe_geom(geom)
    if g is None:
      return
    if isinstance(series_or_val, dict):
      ser = [[int(k), round(float(v), 1)] for k, v in sorted(series_or_val.items()) if v is not None]
    elif isinstance(series_or_val, list):
      ser = series_or_val
    elif series_or_val is not None:
      ser = [[reg_yr, round(float(series_or_val), 1)]]
    else:
      ser = [[reg_yr, round(max(1500.0, g.area * 25000.0), 1)]]
    if not ser:
      ser = [[reg_yr, round(max(1500.0, g.area * 25000.0), 1)]]
    uid = next_id[0]
    next_id[0] += 1
    units.append({
      "id": uid,
      "code": str(code),
      "name": str(name),
      "country": str(country),
      "geom": g,
      "series": ser,
      "source": str(source),
      "is_direct_census": bool(is_direct),
      "priority": float(priority),
    })

  # =========================================================================
  # LAYER z = 1.0 (STRICTLY FALLBACK ONLY!): atlas_defacto_jaguar_cache.json
  # =========================================================================
  df_y = nearest_cache_year(arg1_src["atlas_defacto"], reg_yr)
  for r in arg1_src["atlas_defacto"].get(df_y, []):
    add_unit(f"DEF_{reg_yr}_{r['id']}", r["name"], "FALLBACK", r["geom"], None, f"atlas_defacto_fallback_{df_y}", False, priority=1.0)

  # =========================================================================
  # LAYER z = 2.0: atlas_dejure_jaguar_cache.json & CShapes 2.0 (1886+)
  # =========================================================================
  dj_y = nearest_cache_year(arg1_src["atlas_dejure"], reg_yr)
  for r in arg1_src["atlas_dejure"].get(dj_y, []):
    add_unit(f"DEJ_{reg_yr}_{r['id']}", r["name"], "DEJURE", r["geom"], None, f"atlas_dejure_{dj_y}", False, priority=2.0)

  if reg_yr >= 1886:
    cs_y = min(2019, reg_yr)
    for idx, cs in enumerate(arg1_src["cshapes"]):
      if cs["y0"] <= cs_y <= cs["y1"]:
        add_unit(f"CS_{reg_yr}_{idx:02d}", cs["name"], cs["name"], cs["geom"], None, f"CShapes_2_0_{cs_y}", False, priority=2.2)

  # =========================================================================
  # LAYER z = 3.0: OpenHistoricalMap (date-filtered start_date <= reg_yr <= end_date)
  # =========================================================================
  if reg_yr >= 1500:
    for idx, o in enumerate(arg1_src["ohm"]):
      if o["y0"] <= reg_yr <= o["y1"]:
        # Paint admin_level 2 at 3.0, level 3 at 3.1, level 4+ at 3.2
        prio = 3.0 if o["lvl"] == "2" else (3.1 if o["lvl"] == "3" else 3.2)
        add_unit(f"OHM_{reg_yr}_{idx:04d}", o["name"], "OHM", o["geom"], None, f"OHM_boundaries_{reg_yr}", False, priority=prio)

  # =========================================================================
  # ERA 1 (0..1500 AD): Pre-Columbian HydroBASINS L6 + Cultural Archipelagos
  # =========================================================================
  if reg_yr <= 1500:
    # Fill all JAGUAR land at z = 0.5 underneath atlas_defacto/dejure so coverage = 100%
    for zk, zg in arg1_src["pre_zones"].items():
      if zg is not None:
        add_unit(f"PRE_{reg_yr}_{zk}", zk.replace("pre_", "").replace("_", " ").title(), "PRECOLUMBIAN", zg, None, "HydroBASINS_L6_PreColumbian_Base", False, priority=0.5)
    # At 1500 AD (Eve of Contact), place organic Late Post-Classic cultural zones on top at z = 4.0
    if reg_yr == 1500:
      for zk, zg in arg1_src["pre_zones"].items():
        if zg is not None and zk != "pre_bermuda_uninhabited":
          add_unit(f"LPOST_{zk}", zk.replace("pre_", "").replace("_", " ").title(), "PRECOLUMBIAN_1500", zg, None, "HydroBASINS_L6_DECM_1500", False, priority=4.0)
    return units

  # Helper: add Colonial Caribbean & Bermuda territories at z = 4.0
  def add_colonial_caribbean (yr_snap, unified_hispaniola=False):
    hisp = u_geoms([C.get("Haiti"), C.get("Dominican Republic")])
    cuba = u_geoms([C.get("Cuba"), C.get("US Naval Base Guantanamo Bay")])
    sd_fr = clip_geom(arg1_src["ohm_special"].get("saint_domingue_1697"), hisp)
    sd_es = diff_geom(hisp, sd_fr)

    carib_defs = [
      ("CU_COL", "Capitania General de Cuba", "Cuba", cuba, "cu_colonial_total"),
      ("PR_COL", "Capitania General de Puerto Rico", "Puerto Rico", C.get("Puerto Rico"), "pr_colonial_total"),
      ("JM_COL", "Jamaica", "Jamaica", u_geoms([C.get("Jamaica"), C.get("Cayman Islands")]), "jm_colonial_total"),
      ("BB_COL", "Barbados", "Barbados", C.get("Barbados"), "bb_colonial_total"),
      ("TT_COL", "Trinidad & Tobago", "Trinidad and Tobago", C.get("Trinidad and Tobago"), "tt_colonial_trinidad"),
      ("BS_COL", "Bahamas & Turks-Caicos", "The Bahamas", u_geoms([C.get("The Bahamas"), C.get("Turks and Caicos Islands")]), "bs_colonial_total"),
      ("BM_COL", "Colony of Bermuda", "Bermuda", C.get("Bermuda"), "bm_colonial_total"),
      ("GD_COL", "Grenada", "Grenada", C.get("Grenada"), "gd_colonial_19c"),
      ("LC_COL", "Saint Lucia", "Saint Lucia", C.get("Saint Lucia"), "lc_colonial_19c"),
      ("VC_COL", "Saint Vincent", "Saint Vincent and the Grenadines", C.get("Saint Vincent and the Grenadines"), "vc_colonial_19c"),
      ("DM_COL", "Dominica", "Dominica", C.get("Dominica"), "dm_colonial_19c"),
      ("AG_COL", "Antigua & Barbuda", "Antigua and Barbuda", C.get("Antigua and Barbuda"), "ag_colonial_19c"),
      ("KN_COL", "Saint Kitts & Nevis", "Saint Kitts and Nevis", u_geoms([C.get("Saint Kitts and Nevis"), C.get("Anguilla"), C.get("British Virgin Islands")]), "kn_colonial_19c"),
      ("MS_COL", "Montserrat", "Montserrat", C.get("Montserrat"), "ms_colonial_19c"),
      ("VI_COL", "Danish West Indies (USVI)", "United States Virgin Islands", C.get("United States Virgin Islands"), "dwi_st_croix"),
      ("NL_COL", "Dutch Antilles (ABC & SSS)", "Curaçao", u_geoms([C.get("Aruba"), C.get("Curaçao"), C.get("Caribbean Netherlands"), C.get("Sint Maarten")]), "dutch_antilles_1863"),
    ]
    # Split French Antilles into Guadeloupe vs Martinique
    if "French Antilles" in C:
      fa_ps = list(iter_polys(C["French Antilles"]))
      glp = u_geoms([p for p in fa_ps if p.representative_point().y >= 15.5] + [C.get("Saint Barthelemy"), C.get("Saint Martin")])
      mtq = u_geoms([p for p in fa_ps if p.representative_point().y < 15.5])
      carib_defs.append(("GP_COL", "Guadeloupe", "Guadeloupe", glp, "gp_colonial_total"))
      carib_defs.append(("MQ_COL", "Martinique", "Martinique", mtq, "mq_colonial_total"))

    if unified_hispaniola:
      carib_defs.append(("HISP_COL", "Hispaniola (Santo Domingo)", "Dominican Republic", hisp, "do_colonial_santo_domingo"))
    else:
      # Combine 1789 Saint-Domingue 3 provinces into total if pre-1804, else Haiti
      sd_tot = {1789: 523803, 1805: 380000}
      carib_defs.append(("HT_COL", "Saint-Domingue / Haiti", "Haiti", sd_fr if yr_snap < 1804 else C.get("Haiti"), None))
      carib_defs.append(("DO_COL", "Santo Domingo / Dominican Republic", "Dominican Republic", sd_es if yr_snap < 1804 else C.get("Dominican Republic"), "do_colonial_santo_domingo"))

    col_enum = enums.get("colonial_caribbean_bermuda_1655_1899", {})
    for code, nm, ctry, g, ekey in carib_defs:
      if g is None:
        continue
      ser = None
      if ekey and ekey in col_enum:
        ser = col_enum[ekey]["years"]
      elif code == "HT_COL":
        ser = {1789: 523803, 1805: 380000, 1850: 850000, 1890: 1180000}
      add_unit(f"{code}_{yr_snap}", nm, ctry, g, ser, f"HGIS_Colonial_Caribbean_{yr_snap}", bool(ser), priority=4.0)

  # =========================================================================
  # ERA 2 (1600..1810 AD): 1600 Audiencias/Gobernaciones & 1700-1810 HGIS de las Indias
  # =========================================================================
  if reg_yr <= 1810:
    p90_d = arg1_src["indias"][1790]
    pm90_d = arg1_src["indias_pm90"]
    f90_d = arg1_src["indias_f90"]
    def g90 (k):
      return p90_d[k]["geom"] if k in p90_d else None

    if reg_yr <= 1650:
      # Authentic 1600 AD Spanish Audiencias & Gobernaciones (ZERO 1705 interior speckles, ZERO Belize wedge, ONE unified Baja!)
      ns_tot = enums.get("colonial_new_spain_1570_1810", {}).get("viceroyalty_new_spain_total", {}).get("years")
      cgg_en = enums.get("colonial_central_america_1778_1816", {})
      tab_g = pm90_d.get("JUNETBTB", {}).get("geom")
      aud_1600 = [
        ("AUD1600_MEX", "Audiencia de Mexico (Central New Spain)", "Mexico", u_geoms([g90(k) for k in ("PRNEMX00", "PRNEPU00", "PRNEVC00", "PRNEOA00", "PRNEMI00", "PRNEGJ00", "PRNESL00")]), {1570: 2700000, 1600: 1550000, 1646: 1320000}, "HGIS_Indias_Audiencia_Mexico_1600"),
        ("AUD1600_NGAL", "Reino de Nueva Galicia (Guadalajara & Zacatecas)", "Mexico", u_geoms([g90(k) for k in ("PRGDGD00", "PRGDNA00", "PRGDZA00")]), {1570: 310000, 1600: 260000, 1646: 215000}, "HGIS_Indias_Nueva_Galicia_1600"),
        ("AUD1600_NVIZ", "Nueva Vizcaya, Sonora & Northern Frontier", "Mexico", u_geoms([g90(k) for k in ("PRGDDU00", "PRGDSS00", "PRGDCO00", "PRGDNL00", "PRGDNS00")] + [arg1_src["pre_zones"].get("pre_aridoamerica_baja")]), {1570: 320000, 1600: 270000, 1646: 225000}, "HGIS_Indias_Nueva_Vizcaya_1600"),
        ("AUD1600_YUC", "Gobernacion de Yucatan & Tabasco", "Mexico", u_geoms([g90("PRNEYU00"), tab_g]), {1570: 245000, 1600: 215000, 1646: 185000}, "HGIS_Indias_Yucatan_Tabasco_1600"),
        ("AUD1600_BAJA", "Baja California Peninsula (Indigenous)", "Mexico", arg1_src.get("baja_unified"), {1570: 45000, 1600: 42000, 1646: 36000}, "Unified_Baja_California_Peninsula_1600"),
        ("AUD1600_GUA", "Audiencia de Guatemala, Chiapas, Peten & San Salvador", "Guatemala", u_geoms([g90("PRGUGU00"), g90("PRGUCH00"), g90("PRGUSS00"), f90_d.get("FRGUMOCH", {}).get("geom"), C.get("Belize")]), {1570: 620000, 1600: 460000, 1646: 410000}, "HGIS_Indias_Audiencia_Guatemala_1600"),
        ("AUD1600_HON", "Gobernacion de Honduras & Taguzgalpa", "Honduras", u_geoms([g90("PRGUCY00"), f90_d.get("FRGUCYTA", {}).get("geom"), C.get("Honduras")]), {1570: 145000, 1600: 95000, 1646: 75000}, "HGIS_Indias_Honduras_1600"),
        ("AUD1600_NIC", "Gobernacion de Nicaragua & Tologalpa", "Nicaragua", u_geoms([g90("PRGUNI00"), f90_d.get("FRGUNITO", {}).get("geom"), C.get("Nicaragua")]), {1570: 135000, 1600: 85000, 1646: 72000}, "HGIS_Indias_Nicaragua_1600"),
        ("AUD1600_CR", "Gobernacion de Costa Rica", "Costa Rica", u_geoms([g90("PRGUCR00"), C.get("Costa Rica")]), {1570: 38000, 1600: 26000, 1646: 22000}, "HGIS_Indias_Costa_Rica_1600"),
        ("AUD1600_PAN", "Audiencia de Panama, Veraguas & Darien", "Panama", u_geoms([g90("PRNGPA00"), g90("PRNGVE00"), g90("PRNGDA00"), C.get("Panama")]), {1570: 115000, 1600: 95000, 1646: 82000}, "HGIS_Indias_Tierra_Firme_1600"),
      ]
      for code, nm, ctry, geom, ser, src_nm in aud_1600:
        if geom is not None:
          g_clean = fill_small_holes(geom, arg1_max_hole_area=0.45)
          prio = 4.35 if code in ("AUD1600_BAJA", "AUD1600_YUC") else (4.25 if code == "AUD1600_GUA" else 4.15)
          add_unit(code, nm, ctry, g_clean, ser, src_nm, True, priority=prio)
      add_colonial_caribbean(reg_yr, unified_hispaniola=True)
      return units

    # 1700..1810 AD: Seamless HGIS de las Indias 1790/1750 Provincias + Audiencia Base + Organic Mosquitia!
    if reg_yr <= 1700 and arg1_src["pre_zones"].get("pre_aridoamerica_baja") is not None:
      add_unit(f"FRON_{reg_yr}_NORTH", "Northern Aridoamerica Frontier (Indigenous)", "Mexico", arg1_src["pre_zones"]["pre_aridoamerica_baja"], {1600: 45000, 1700: 32000}, "HydroBASINS_Northern_Frontier_PreMission", False, priority=0.5)
    for aeid, arec in sorted(arg1_src["indias_aud"].items()):
      if aeid in ("AUMX0000", "AUGD0000", "AUCO0000"):
        add_unit(f"AUD_{reg_yr}_{aeid}", f"Audiencia de {arec['nombre']}", "Mexico" if aeid != "AUCO0000" else "Central America", fill_small_holes(arec["geom"], 0.45), None, "HGIS_de_las_Indias_Audiencia_Base", False, priority=4.0)
    # Use 1790 complete provincial tessellation (with Tabasco folded into Yucatan) so zero 1705 interior gaps exist
    ind_yr = 1750 if reg_yr <= 1750 else 1790
    ind_provs = arg1_src["indias"][1790]
    for eid, rec in sorted(ind_provs.items()):
      if not any(eid.startswith(p) for p in ("PRNE", "PRGD", "PRGU", "PRSD", "PRNGPA", "PRNGVE", "PRNGDA")):
        continue
      if eid in ("PRSDLU00", "PRSDFL00", "PRGDNM00", "PRGDTX00"):
        continue
      g_use = rec["geom"]
      if eid == "PRNEYU00" and "JUNETBTB" in pm90_d:
        g_use = u_geoms([g_use, pm90_d["JUNETBTB"]["geom"]])
      if eid == "PRGUGU00" and "FRGUMOCH" in f90_d:
        g_use = u_geoms([g_use, f90_d["FRGUMOCH"]["geom"]])
      # Fill tiny colonial cabecera/marquesado/lakebed interior holes (< 0.35 deg^2) so zero speckles poke through!
      g_use = fill_small_holes(g_use, arg1_max_hole_area=0.35)
      ser = None
      is_dir = False
      if eid in INDIAS_TO_ENUM:
        era_k, u_k = INDIAS_TO_ENUM[eid]
        erec = enums.get(era_k, {}).get(u_k)
        if erec and erec.get("years"):
          ser = erec["years"]
          is_dir = True
      ctry = "Mexico" if eid.startswith(("PRNE", "PRGD")) else ("Central America" if eid.startswith(("PRGU", "PRNG")) else "Caribbean")
      add_unit(f"IND_{ind_yr}_{eid}", rec["nombre"], ctry, g_use, ser, f"HGIS_de_las_Indias_{ind_yr}", is_dir, priority=4.1)

    if reg_yr <= 1700 and arg1_src.get("baja_unified") is not None:
      add_unit(f"BAJA_{reg_yr}", "Baja California Peninsula (Indigenous / Early Missions)", "Mexico", arg1_src["baja_unified"], {1700: 28000}, "Unified_Baja_California_Peninsula_1700", False, priority=4.35)

    # Organic Taguzgalpa-Tologalpa + HydroBASINS L6 Mosquitia (ZERO ~85W straight meridian!) & British Honduras
    if reg_yr >= 1750:
      if arg1_src.get("organic_mosquitia") is not None:
        add_unit(f"MOSQ_{reg_yr}", "Mosquito Kingdom (Taguzgalpa & Tologalpa)", "Nicaragua", arg1_src["organic_mosquitia"], {1750: 42000, 1790: 46000}, "HGIS_Indias_Taguzgalpa_Tologalpa+HydroBASINS_L6", False, priority=4.25)
      if "british_honduras_early" in arg1_src["ohm_special"]:
        bz_ser = enums.get("colonial_central_america_1778_1816", {}).get("bz_colonial_settlement", {}).get("years")
        add_unit(f"BH_{reg_yr}", "British Honduras Settlement", "Belize", arg1_src["ohm_special"]["british_honduras_early"], bz_ser, "OHM_British_Honduras_Settlement", bool(bz_ser), priority=4.25)

    add_colonial_caribbean(reg_yr, unified_hispaniola=False)
    return units

  # =========================================================================
  # ERA 3 (1824): First Federal Republic of Mexico (Bexar 1824) + Central America + Caribbean
  # =========================================================================
  if reg_yr == 1824:
    for idx, b in enumerate(arg1_src["bexar_1824"]):
      ser = match_enumeration(arg1_src, "Mexico", b["name"], arg3_preferred_eras={"mexico_republic_19c_1820_1889"})
      add_unit(f"MX1824_{idx:02d}", b["name"], "Mexico", b["geom"], ser, "Bexar_Mexico_1824_Constitution_States", bool(ser), priority=4.2)
    # Central America: Provincial Republics + British Honduras + Mosquitia
    ca_map = [
      ("GT", "Guatemala", "cgg_guatemala_prov"),
      ("SV", "El Salvador", "cgg_el_salvador_prov"),
      ("HN", "Honduras", "cgg_honduras_prov"),
      ("NI", "Nicaragua", "cgg_nicaragua_prov"),
      ("CR", "Costa Rica", "cgg_costa_rica_prov"),
      ("PA", "Panama (Gran Colombia)", "pa_1778_panama"),
      ("BZ", "British Honduras", "bz_colonial_settlement"),
    ]
    ca_en = enums.get("colonial_central_america_1778_1816", {})
    for cc, nm, ek in ca_map:
      if nm.split(" (")[0] in C:
        g = C[nm.split(" (")[0]]
        ser = ca_en.get(ek, {}).get("years")
        add_unit(f"CA1824_{cc}", nm, nm.split(" (")[0], g, ser, "Central_America_1824_Federal_Provinces", bool(ser), priority=4.1)
    add_colonial_caribbean(1824, unified_hispaniola=True)
    return units

  # =========================================================================
  # ERA 4 (1850..1880): Mid-19th Century Republican Mexico, Central America ADM1 & Caribbean
  # =========================================================================
  if reg_yr == 1850:
    # Assemble period-authentic mid-19c Mexican states (pre-Quintana Roo, unified Baja California, Tepic inside Jalisco!)
    lurtz_by_n = {u["norm"]: u for u in arg1_src["lurtz_1900"]}
    jal_tepic = u_geoms([lurtz_by_n.get("jalisco", {}).get("geom"), lurtz_by_n.get("territorio de tepic", {}).get("geom")])
    for idx, u in enumerate(arg1_src["lurtz_1900"]):
      if u["norm"] == "territorio de tepic":
        continue  # Part of Jalisco until 1884
      g_use = jal_tepic if u["norm"] == "jalisco" else u["geom"]
      ser = match_enumeration(arg1_src, "Mexico", u["name"], arg3_preferred_eras={"mexico_republic_19c_1820_1889"})
      add_unit(f"MX1850_{idx:02d}", u["name"], "Mexico", g_use, ser, "Mexico_19c_Republican_States_Pre1884", bool(ser), priority=4.2)

    for iso in ("GTM", "BLZ", "HND", "SLV", "NIC", "CRI", "PAN"):
      for u in arg1_src["gb_adm1"].get(iso, []):
        ser = match_enumeration(arg1_src, u["country"], u["name"], arg3_preferred_eras={"central_america_modern_1864_2024"})
        add_unit(f"CA1850_{u['code']}", u["name"], u["country"], u["geom"], ser, f"Central_America_19c_Depts_{iso}", bool(ser), priority=4.1)
    add_colonial_caribbean(1850, unified_hispaniola=False)
    return units

  # =========================================================================
  # ERA 5 (1900, 1910, 1920): Porfirian Mexico (Lurtz 1900) + Early Canal Zone (1903+)
  # =========================================================================
  if reg_yr in (1900, 1910, 1920):
    qroo_g = arg1_src["ohm_special"].get("quintana_roo_1902")
    for idx, u in enumerate(arg1_src["lurtz_1900"]):
      g_use = u["geom"]
      nm_use = u["name"]
      if reg_yr >= 1910 and u["norm"] == "yucatan" and qroo_g is not None:
        g_use = diff_geom(g_use, qroo_g)
      if reg_yr >= 1920 and u["norm"] == "territorio de tepic":
        nm_use = "Nayarit"
      ser = match_enumeration(arg1_src, "Mexico", nm_use, arg3_preferred_eras={"mexico_inegi_1895_2020"})
      add_unit(f"MX{reg_yr}_{idx:02d}", nm_use, "Mexico", g_use, ser, f"Lurtz_Mexico_1900_States_{reg_yr}", bool(ser), priority=4.3)
    if reg_yr >= 1910 and qroo_g is not None:
      qr_ser = enums.get("mexico_inegi_1895_2020", {}).get("mx_quintana_roo", {}).get("years")
      add_unit(f"MX{reg_yr}_QROO", "Territorio de Quintana Roo", "Mexico", qroo_g, qr_ser, f"OHM_Territorio_Quintana_Roo_{reg_yr}", bool(qr_ser), priority=4.4)

    for iso in ("GTM", "BLZ", "HND", "SLV", "NIC", "CRI", "PAN"):
      for u in arg1_src["gb_adm1"].get(iso, []):
        ser = match_enumeration(arg1_src, u["country"], u["name"], arg3_preferred_eras={"central_america_modern_1864_2024"})
        add_unit(f"{u['code']}_{reg_yr}", u["name"], u["country"], u["geom"], ser, f"geoBoundaries_ADM1_{iso}_{reg_yr}", bool(ser), priority=4.1)
    if reg_yr >= 1910 and "panama_canal_zone" in arg1_src["ohm_special"]:
      pcz_ser = {1912: 62810, 1920: 22858, 1930: 39467, 1940: 51827, 1950: 52822, 1960: 42122, 1970: 44198}
      add_unit(f"PCZ_{reg_yr}", "Panama Canal Zone", "Panama", arg1_src["ohm_special"]["panama_canal_zone"], pcz_ser, "OHM_Panama_Canal_Zone_1903_1979", True, priority=4.5)

    # Greater Antilles + Lesser Antilles + Bahamas + Bermuda
    for iso in ("CUB", "HTI", "DOM", "JAM", "TTO", "BRB", "BHS", "ATG", "DMA", "GRD", "KNA", "LCA", "VCT"):
      for u in arg1_src["gb_adm1"].get(iso, []):
        # Merge Cuba Artemisa+Mayabeque into La Habana prior to 2011!
        if iso == "CUB" and u["norm"] in ("artemisa", "mayabeque"):
          continue
        g_use = u["geom"]
        if iso == "CUB" and u["norm"] == "havana":
          g_use = u_geoms([x["geom"] for x in arg1_src["gb_adm1"]["CUB"] if x["norm"] in ("havana", "artemisa", "mayabeque")])
        ser = match_enumeration(arg1_src, u["country"], u["name"], arg3_preferred_eras={"greater_antilles_historic_1899_1979", "greater_antilles_modern_1935_2023", "lesser_antilles_bahamas_bermuda_1900_2025"})
        add_unit(f"{u['code']}_{reg_yr}", u["name"], u["country"], g_use, ser, f"geoBoundaries_ADM1_{iso}_{reg_yr}", bool(ser), priority=4.1)
    for iso, t in arg1_src["gb_adm0"].items():
      ser = match_enumeration(arg1_src, t["country"], t["name"], arg3_preferred_eras={"greater_antilles_historic_1899_1979", "lesser_antilles_bahamas_bermuda_1900_2025", "colonial_caribbean_bermuda_1655_1899"})
      add_unit(f"{iso}_{reg_yr}", t["name"], t["country"], t["geom"], ser, f"geoBoundaries_ADM0_{iso}_{reg_yr}", bool(ser), priority=4.2)
    return units

  # =========================================================================
  # ERA 6 (1950, 1975, 2000, 2020): Modern Census ADM1 + Period-Exact Splits
  # - Panama Canal Zone active strictly <= 1979 (dissolved 1980+)!
  # - Cuba Artemisa/Mayabeque created strictly >= 2011 (unified La Habana <= 2010)!
  # =========================================================================
  for iso, ulist in arg1_src["gb_adm1"].items():
    for u in ulist:
      if iso == "CUB" and reg_yr < 2011 and u["norm"] in ("artemisa", "mayabeque"):
        continue
      g_use = u["geom"]
      nm_use = u["name"]
      if iso == "CUB" and reg_yr < 2011 and u["norm"] == "havana":
        g_use = u_geoms([x["geom"] for x in ulist if x["norm"] in ("havana", "artemisa", "mayabeque")])
        nm_use = "La Habana (Unified pre-2011)"
      pref = (
        {"mexico_inegi_1895_2020"} if iso == "MEX" else
        {"central_america_modern_1864_2024"} if iso in ("GTM", "BLZ", "HND", "SLV", "NIC", "CRI", "PAN") else
        {"greater_antilles_modern_1935_2023", "greater_antilles_historic_1899_1979"} if iso in ("CUB", "HTI", "DOM", "JAM") else
        {"lesser_antilles_bahamas_bermuda_1900_2025"}
      )
      ser = match_enumeration(arg1_src, u["country"], nm_use, arg3_preferred_eras=pref)
      add_unit(f"{u['code']}_{reg_yr}", nm_use, u["country"], g_use, ser, f"geoBoundaries_ADM1_{iso}_{reg_yr}", bool(ser), priority=4.2)

  # Exact OHM Panama Canal Zone strictly for 1903..1979 (NEVER anachronistically present in 1980+!)
  if 1903 <= reg_yr <= 1979 and "panama_canal_zone" in arg1_src["ohm_special"]:
    pcz_ser = {1912: 62810, 1920: 22858, 1930: 39467, 1940: 51827, 1950: 52822, 1960: 42122, 1970: 44198, 1979: 44000}
    add_unit(f"PCZ_{reg_yr}", "Panama Canal Zone", "Panama", arg1_src["ohm_special"]["panama_canal_zone"], pcz_ser, "OHM_Panama_Canal_Zone_1903_1979", True, priority=4.6)

  for iso, t in arg1_src["gb_adm0"].items():
    ser = match_enumeration(arg1_src, t["country"], t["name"], arg3_preferred_eras={"lesser_antilles_bahamas_bermuda_1900_2025", "greater_antilles_historic_1899_1979", "colonial_caribbean_bermuda_1655_1899"})
    add_unit(f"{iso}_{reg_yr}", t["name"], t["country"], t["geom"], ser, f"geoBoundaries_ADM0_{iso}_{reg_yr}", bool(ser), priority=4.3)

  return units


def verify_zero_anachronisms (arg0_yr, arg1_kept_units):
  yr = int(arg0_yr)
  if yr < 1902:
    bad_qr = [u["name"] for u in arg1_kept_units if "quintana roo" in u["name"].lower()]
    assert not bad_qr, f"ANACHRONISM FAIL in {yr}: Quintana Roo created in 1902: {bad_qr}"
  if yr < 1903 or yr >= 1980:
    bad_pcz = [u["name"] for u in arg1_kept_units if "panama canal zone" in u["name"].lower()]
    assert not bad_pcz, f"ANACHRONISM FAIL in {yr}: Panama Canal Zone existed 1903-1979 only: {bad_pcz}"
  if yr < 2011:
    bad_cu = [u["name"] for u in arg1_kept_units if u["country"] == "Cuba" and any(t in u["name"].lower() for t in ("artemisa", "mayabeque"))]
    assert not bad_cu, f"ANACHRONISM FAIL in {yr}: Cuba Artemisa/Mayabeque created in 2011: {bad_cu}"


def main ():
  for d in (HGIS_RASTERS, TESTS_SUBADMIN_CROPS):
    for fn in os.listdir(d):
      if fn.startswith(("subadmin_id_", "subadmin_meta_", "subadmin_crop_")):
        os.remove(os.path.join(d, fn))

  dm_raw = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  domain_mask = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)
  la_raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  land_area = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2])

  src = load_all_subadmin_sources()

  regime_to_years = defaultdict(list)
  for y in ALL_HYDE_AD_YEARS:
    regime_to_years[get_boundary_regime_key(y)].append(y)
  distinct_regimes = sorted(regime_to_years.keys())
  print(f"\n[2] Rasterising {len(distinct_regimes)} distinct boundary regimes -> ALL {len(ALL_HYDE_AD_YEARS)} overlapping AD HYDE years (0..2025)...", flush=True)

  lit_summary = {
    "project": "JAGUAR",
    "anti_anachronism_verified": True,
    "scanline_free_cv2_fillPoly": True,
    "atlas_defacto_lowest_z_index_fallback": True,
    "hyde_ad_year_count": len(ALL_HYDE_AD_YEARS),
    "distinct_boundary_regimes": len(distinct_regimes),
    "generated_snapshots": {},
  }
  lit_csv_rows = []
  csv_export_years = {0, 500, 1000, 1500, 1600, 1700, 1750, 1790, 1800, 1820, 1850, 1880, 1900, 1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020, 2025}

  for reg_yr in distinct_regimes:
    yrs_in_regime = regime_to_years[reg_yr]
    units = build_regime_units(reg_yr, src)
    confetti_px = 14 if 1550 <= reg_yr <= 1810 else (4 if reg_yr <= 1850 else 0)
    rgba, id_grid, px_cnt, area_sum, full_area = cv2_rasterise_subadmin_units(
      units, domain_mask, land_area, arg3_snap_coastal_px=3, arg4_clean_confetti_px=confetti_px
    )

    active_u = int((px_cnt[1:] > 0).sum())
    cov_pct = 100.0 * float((id_grid > 0).sum()) / max(1.0, float(domain_mask.sum()))

    # Render optical QA crop PNGs for all required representative regime years!
    if reg_yr in QA_CROP_YEARS:
      crop_png = os.path.join(TESTS_SUBADMIN_CROPS, f"subadmin_crop_{reg_yr:04d}.png")
      render_jaguar_subadmin_crop_png(
        id_grid, domain_mask, crop_png,
        arg3_title=f"JAGUAR Sub-Admin HGIS Regime {reg_yr} AD ({yrs_in_regime[0]}..{yrs_in_regime[-1]}) | {active_u} units | {cov_pct:.1f}% cov",
      )

    # Save PNG bytes once per regime and write for every HYDE year in this regime
    png_img = Image.fromarray(rgba, mode="RGBA")
    first_png = os.path.join(HGIS_RASTERS, f"subadmin_id_{yrs_in_regime[0]}.png")
    png_img.save(first_png, compress_level=6)
    png_bytes = open(first_png, "rb").read()

    for yr in yrs_in_regime:
      out_png = os.path.join(HGIS_RASTERS, f"subadmin_id_{yr}.png")
      if yr != yrs_in_regime[0]:
        with open(out_png, "wb") as fh:
          fh.write(png_bytes)

      kept_units = []
      for u in units:
        uid = u["id"]
        if int(px_cnt[uid]) <= 0:
          continue
        in_frac = float(area_sum[uid]) / max(1.0, float(full_area[uid]))
        kept_units.append({
          "id": uid,
          "code": u["code"],
          "name": u["name"],
          "country": u["country"],
          "source": u["source"],
          "is_direct_census": u["is_direct_census"],
          "pixel_count": int(px_cnt[uid]),
          "area_km2": round(float(area_sum[uid]), 1),
          "in_jaguar_area_frac": round(in_frac, 4),
          "series": u["series"],
        })
        if yr in csv_export_years:
          ser_d = {int(a): float(b) for a, b in u["series"]}
          p_yr = interp_dict(ser_d, yr) or 0.0
          if p_yr > 0:
            lit_csv_rows.append([yr, u["country"], u["code"], u["name"], yr, int(round(p_yr)), round(float(area_sum[uid]), 1), u["source"]])

      verify_zero_anachronisms(yr, kept_units)
      out_meta = os.path.join(HGIS_RASTERS, f"subadmin_meta_{yr}.json")
      meta_obj = {
        "snapshot_year": yr,
        "boundary_regime": reg_yr,
        "anti_anachronism_verified": True,
        "unit_count": len(kept_units),
        "covered_pixels": int((id_grid > 0).sum()),
        "units": kept_units,
      }
      with open(out_meta, "w", encoding="utf-8") as fh:
        json.dump(meta_obj, fh)
      lit_summary["generated_snapshots"][str(yr)] = {
        "boundary_regime": reg_yr,
        "unit_count": len(kept_units),
        "covered_pixels": meta_obj["covered_pixels"],
        "sources_used": sorted({u["source"] for u in kept_units}),
      }

    print(
      f"  Regime {reg_yr:4d} ({yrs_in_regime[0]}..{yrs_in_regime[-1]}, {len(yrs_in_regime):2d} yrs): {active_u:4d} units | {cov_pct:5.1f}% cov",
      flush=True,
    )

  with open(os.path.join(HGIS_ROOT, "subadmin_enumerations_for_literature_reviews.json"), "w", encoding="utf-8") as fh:
    json.dump(lit_summary, fh, indent=2, ensure_ascii=False)
  with open(os.path.join(HGIS_ROOT, "subadmin_enumerations_for_literature_reviews.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["snapshot_regime", "country", "unit_code", "unit_name", "year", "population", "area_km2", "source"])
    w.writerows(lit_csv_rows)
  print(f"\n[DONE] Built ALL {len(ALL_HYDE_AD_YEARS)} HYDE AD rasters ({len(distinct_regimes)} regimes) & {len(lit_csv_rows):,} literature-review rows.", flush=True)


if __name__ == "__main__":
  main()
