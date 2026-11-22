"""Dedicated loader for ALL genuinely scraped open-access European Historical GIS (HGIS)
shapefiles & historical sub-administrative enumerations in `_shared/subadmin_hgis/raw_sources/scraped_*`.

Provides period-authentic WGS84 Shapely polygons & archival census tables across all 6 European macro-blocs:
  - France & Low Countries: Brette/Gay 1789 Bailliages (435) & Généralités (33), Larhra 1560-1678 borders,
    Ancien Régime Customs (95), Savoy c.1780 (8), Chambru 1790/1794 Départements (83/89),
    TRF-GIS 1870/1872/1914/1920/1939 Départements, KNAW DANS NLGis 1830-1980 Provinces (11/12, pre-Flevoland).
  - PLC, Poland & Baltics: IH PAN Late Mediaeval Voivodeships (21), AHP 16th-c. Voivodeships (23),
    PLC 1619 Peak Voivodeships (53 incl. GDL/Courland/Livonia), Szady/IH PAN 1772 Palatinates (43),
    1802-1806 Prussian Partitions, 1811 Duchy of Warsaw (10), 1816/1830/1867 Congress Poland (8/10),
    1900 All-3-Partitions Gubernias (25 w/ embedded 1897/1900 census!), Galicia 1857-1910,
    Interwar II RP 1921/1931 Voivodeships (17 w/ embedded 1921/1931 census!),
    PRL 1950 17 Voivodeships (19) & PRL 1975 49 Voivodeships (49), Latvia 5 Historical Lands, Estonia KNR.
  - Balkans, Ottoman & Danube: OHM Ottoman Eyalets/Vilayets/Sanjaks (19) & Danubian Polities (126),
    GISta Hungarorum 1910 ALL 63 Vármegyék & 8 Croatia-Slavonia Counties,
    RoHGIS Greater Romania 1930 ALL 71 Interwar Județe (w/ embedded Pop_tot!),
    SFR Yugoslavia 1953/1961/1971/1981/1991 Municipalities (355-774 units!).
  - Central Europe, Germany & Czechia: Oxford HRE Pre-1648 (124) & Post-1648 (463) Territories,
    HGIS German Confederation 1848 (37) & Empire 1871 (27), MPIDR German Empire 1871 Districts (1.005),
    Univie Cisleithania 1910 Political Districts (94), Weimar 1926/1930/1933 & Reich 1937 States/Districts,
    Official BKG VG-Hist 1955/1970/1980 FRG Regierungsbezirke + 15 GDR Bezirke & 1989 Länder/Bezirke (26),
    Czechoslovakia 1850 Kraje, 1920 Župy (15), 1921/1930 Okresy, 1949-1960 19 Kraje, 1960-1990 11 Kraje.
  - Nordics, UK & Ireland: Historic Counties Trust UK ALL 92 Historic Counties (defA pre-1844 & defB post-1844,
    incl. ALL 34 Scottish Shires + Shetland/Orkney!), Ireland ALL 32 Historic Counties,
    Denmark DigDag 19 Amter (1793-1920) & 23 Amter (1920-1970 incl. 4 N. Schleswig!) + 1787-1921/1971-2002 censuses,
    Norway Kartverket 20 Amt (1831-1972 incl. Bergen!) & 19 Fylker (1972-2017) + SSB 1801-2001 census,
    Sweden Riksarkivet swehist 1800/1900/1970, Finland KOTUS 1938 Pre-War Parishes (w/ Karelia/Viipuri!)
    & MML 20 Maakunta / 6 Lääni, Iceland 9 traditional umdæmi.
  - Southern Europe & Classical/Mediaeval: DARMC Diocletian 303-324 CE (97 filled!), AWMC Notitia Dignitatum
    400 CE (121 filled!), DARMC Late Roman 500 CE (64 filled!), DARMC Mediaeval Dioceses 1250 (666) & 1450 (706),
    Harvard WorldMap Europe 2nd-Level Divisions 1500 (614), Spain 1500 19 Reinos, Spain 1812 Antiguo Régimen
    33 Provinces (w/ 11M Floridablanca/Godoy pop!), Portugal 1500 6 Províncias, Italy 1500 46 States/Giustizierati!
"""

import csv
import json
import os
import re
from collections import defaultdict

from shapely.geometry import shape
from shapely.ops import unary_union

from magnetic_hgis_tables import fix_mojibake, norm_str, safe_geom


def _load_gj_list(fp, name_keys, pop_keys=None, extra_keys=None, min_area=0.002):
  """Generic safe WGS84 GeoJSON loader returning clean `[{'name', 'norm', 'geom', 'pop', ...}]`."""
  if not os.path.isfile(fp):
    return []
  gj = json.load(open(fp, encoding="utf-8", errors="replace"))
  out = []
  for idx, f in enumerate(gj.get("features", [])):
    if not f.get("geometry"):
      continue
    g = safe_geom(shape(f["geometry"]))
    if g is None or g.area < min_area:
      continue
    p = f.get("properties") or {}
    nm = ""
    for nk in name_keys:
      v = p.get(nk)
      if v is not None and str(v).strip() and str(v).strip().lower() not in ("none", "null", "na"):
        nm = fix_mojibake(str(v).strip())
        break
    if not nm:
      nm = f"Unit_{idx + 1}"
    pop_val = None
    if pop_keys:
      for pk in pop_keys:
        v = p.get(pk)
        if v is not None and str(v).strip() not in ("", "None", "NA", "null"):
          try:
            fv = float(str(v).replace(" ", "").replace(",", "."))
            if fv > 0:
              pop_val = fv
              break
          except Exception:
            pass
    rec = {"name": nm, "norm": norm_str(nm), "geom": g}
    if pop_val is not None:
      rec["pop"] = pop_val
    if extra_keys:
      for ek in extra_keys:
        rec[ek] = p.get(ek)
    out.append(rec)
  return out


def load_scraped_european_hgis(raw_dir):
  """Loads all verified scraped European HGIS GeoJSONs and census tables into a structured dict."""
  print("  [HGIS+] Loading ALL 6 scraped European Historical GIS archives...", flush=True)
  S = {}
  p_fr = os.path.join(raw_dir, "scraped_fr_benelux")
  p_pl = os.path.join(raw_dir, "scraped_plc_baltics")
  p_bk = os.path.join(raw_dir, "scraped_balkans_ottoman")
  p_de = os.path.join(raw_dir, "scraped_central_de_cz")
  p_uk = os.path.join(raw_dir, "scraped_nordics_uk")
  p_sa = os.path.join(raw_dir, "scraped_south_ancient")

  # --- 1. Classical, Post-Diocletian & Mediaeval Europe ---
  S["diocletian_303"] = _load_gj_list(os.path.join(p_sa, "roman_medieval_hgis", "darmc_roman_provinces_303_324ce_diocletian.geojson"), ["PROV_NAME", "DIOCESE"])
  S["notitia_400"] = _load_gj_list(os.path.join(p_sa, "roman_medieval_hgis", "awmc_notitia_dignitatum_provinces_c400ce.geojson"), ["Name", "diocese"])
  S["late_roman_500"] = _load_gj_list(os.path.join(p_sa, "roman_medieval_hgis", "darmc_roman_provinces_500ce_late_roman.geojson"), ["PROV_NAME", "Name", "DIOCESE"])
  S["med_dioceses_1250"] = _load_gj_list(os.path.join(p_sa, "roman_medieval_hgis", "darmc_medieval_dioceses_1250ce.geojson"), ["DIOCESE", "NAME", "SHPFID"], min_area=0.005)
  S["med_dioceses_1450"] = _load_gj_list(os.path.join(p_sa, "roman_medieval_hgis", "darmc_medieval_dioceses_1450ce.geojson"), ["DIOCESE", "NAME", "SHPFID"], min_area=0.005)
  S["eu_2nd_level_1500"] = _load_gj_list(os.path.join(p_sa, "italy_preunification", "harvard_worldmap_europe_2nd_level_divisions_1500.geojson"), ["short_name", "long_name", "num"])

  # --- 2. Ancien Régime France & Low Countries ---
  S["fr_1789_generalites"] = _load_gj_list(os.path.join(p_fr, "fr_1789_generalites_brette_dissolved.geojson"), ["generalite_name"])
  S["fr_1789_bailliages"] = _load_gj_list(os.path.join(p_fr, "fr_1789_bailliages_brette.geojson"), ["BAIL_NS", "BAIL_NL", "GEN_N"], extra_keys=["GEN_N"], min_area=0.001)
  S["fr_ar_customs_gen"] = _load_gj_list(os.path.join(p_fr, "fr_ancien_regime_customs_general.geojson"), ["CUST_G_NS", "CUST_G_ID"])
  S["fr_larhra_1560"] = _load_gj_list(os.path.join(p_fr, "fr_16c_17c_borders_larhra_france_1560.geojson"), ["Nom", "id"])
  S["fr_larhra_1610"] = _load_gj_list(os.path.join(p_fr, "fr_16c_17c_borders_larhra_france_1610.geojson"), ["Nom", "id"])
  S["fr_savoy_1780"] = _load_gj_list(os.path.join(p_fr, "savoy_1780_historical_gis_chambru_provinces_b1780.geojson"), ["province_name", "political_entity"])
  S["fr_1790_deps"] = _load_gj_list(os.path.join(p_fr, "fr_1790_departements_chambru.geojson"), ["dept_name_1790"], extra_keys=["dept_code_1790"])
  S["fr_trf_deps"] = {}
  for fy in (1870, 1872, 1914, 1920, 1939):
    S["fr_trf_deps"][fy] = _load_gj_list(os.path.join(p_fr, f"fr_trfgis_departements_{fy}.geojson"), ["dep_name"], extra_keys=["dep_id"])
  # NLGis Historical Dutch Provinces (1830..1980, pre-Flevoland!)
  S["nl_nlgis"] = {}
  for ny in (1830, 1860, 1890, 1920, 1940, 1950, 1980):
    S["nl_nlgis"][ny] = _load_gj_list(os.path.join(p_fr, f"nl_{ny}_provinces_nlgis.geojson"), ["province_name", "NAME1_", "ID_"])

  # --- 3. PLC, Poland & Baltics ---
  S["pl_late_med_voiv"] = _load_gj_list(os.path.join(p_pl, "ihpan_poland_late_medieval_voivodeships.geojson"), ["wojewodztwo_interesanta", "region"])
  S["pl_16c_voiv"] = _load_gj_list(os.path.join(p_pl, "ihpan_ahp_16c_voivodeships.geojson"), ["woj_p", "nazwa", "woj"])
  S["plc_1619_voiv"] = _load_gj_list(os.path.join(p_pl, "ihpan_plc_1619_voivodeships.geojson"), ["woj", "prowincja"])
  S["plc_1772_voiv"] = _load_gj_list(os.path.join(p_pl, "zenodo_szady_plc_1772_woj_zbory.geojson"), ["pal_name", "woj", "nazwa", "NAME"])
  if not S["plc_1772_voiv"]:
    S["plc_1772_voiv"] = _load_gj_list(os.path.join(p_pl, "ihpan_plc_1772_voivodeships.geojson"), ["pal_name", "palat_id"])
  S["pl_warsaw_1811"] = _load_gj_list(os.path.join(p_pl, "ihpan_duchy_of_warsaw_1811_departments.geojson"), ["departamen", "nazwa"])
  S["pl_prussia_1802"] = (
    _load_gj_list(os.path.join(p_pl, "ihpan_prussia_west_1802_provinces.geojson"), ["nazwa", "prowincja", "fid"])
    + _load_gj_list(os.path.join(p_pl, "ihpan_prussia_south_1803_departments.geojson"), ["nazwa", "departamen", "fid"])
    + _load_gj_list(os.path.join(p_pl, "ihpan_prussia_new_east_1806_departments.geojson"), ["nazwa", "departamen", "fid"])
  )
  S["pl_cong_1816"] = _load_gj_list(os.path.join(p_pl, "ihpan_congress_poland_1816_voivodeships.geojson"), ["wojewodztwo", "nazwa", "fid"])
  S["pl_cong_1867"] = _load_gj_list(os.path.join(p_pl, "ihpan_congress_poland_1867_gubernias.geojson"), ["gubernia", "nazwa"])
  S["pl_1900_gub"] = _load_gj_list(os.path.join(p_pl, "ihpan_poland_1900_gubernias_stats.geojson"), ["wojewodztw", "GR_stat_B"], pop_keys=["GR_tab1_stat_C"])
  S["pl_iirp_1921"] = _load_gj_list(os.path.join(p_pl, "ihpan_iirp_1921_voivodeships_stats.geojson"), ["wojewodztw", "w_stat_b"], pop_keys=["w_tab1_stat_c"])
  S["pl_iirp_1931"] = _load_gj_list(os.path.join(p_pl, "ihpan_iirp_1931_voivodeships_stats.geojson"), ["wojewodztw", "W_stat_B"], pop_keys=["W_tab1_stat_C"])
  S["pl_prl_1950"] = _load_gj_list(os.path.join(p_pl, "ihpan_prl_1950_17voivodeships.geojson"), ["JPT_NAZWA_", "nazwa", "JPT_KOD_JE"])
  S["pl_prl_1975"] = _load_gj_list(os.path.join(p_pl, "ihpan_prl_1975_49voivodeships.geojson"), ["JPT_NAZWA_", "nazwa", "JPT_KOD_JE"])
  S["lv_hist_lands"] = _load_gj_list(os.path.join(p_pl, "latvia_historical_lands_vesturiskas_zemes.geojson"), ["name", "code"])
  S["galicia_1857"] = _load_gj_list(os.path.join(p_pl, "dv_galicia_1857_kreise_01_gal_1857_cr.geojson"), ["NAME", "KREIS", "name"])
  S["galicia_1880"] = _load_gj_list(os.path.join(p_pl, "dv_galicia_1880_political_districts_07_gal_1880_dp.geojson"), ["NAME", "DISTRICT", "name"])
  S["galicia_1910"] = _load_gj_list(os.path.join(p_pl, "dv_galicia_1910_political_districts_13_gal_1910_dp.geojson"), ["NAME", "DISTRICT", "name"])

  # --- 4. Balkans, Ottoman & Historic Hungary ---
  S["ottoman_eyalets"] = _load_gj_list(os.path.join(p_bk, "ohm_ottoman_balkans_eyalets_vilayets_sanjaks_1650_1913_wgs84.geojson"), ["name"], extra_keys=["start_date", "end_date", "border_type"])
  S["ohm_balkans_polities"] = _load_gj_list(os.path.join(p_bk, "ohm_balkans_danubian_ottoman_polities_1526_1990_wgs84.geojson"), ["name"], extra_keys=["start_date", "end_date", "admin_level"])
  S["gista_hu_1910"] = _load_gj_list(os.path.join(p_bk, "gista_hungary_1910_varmegyek_counties_wgs84.geojson"), ["Megye_1910", "IDMegye"])
  S["gista_hr_1910"] = _load_gj_list(os.path.join(p_bk, "gista_croatia_slavonia_1910_counties_wgs84.geojson"), ["Megyenev_1", "Megyenev_H"])
  S["rohgis_1930_judete"] = _load_gj_list(os.path.join(p_bk, "rohgis_rohgis_judete_1930_wgs84.geojson"), ["Nume"], pop_keys=["Pop_tot"])
  S["sfry_muni"] = {}
  for yy in (1953, 1961, 1971, 1981):
    S["sfry_muni"][yy] = _load_gj_list(os.path.join(p_bk, f"yugoslavia_sfry_municipalities_{yy}_yug{str(yy)[2:]}_wgs84.geojson"), ["NAME_2", "name"], min_area=0.001)
  S["bosnia_1991"] = _load_gj_list(os.path.join(p_bk, "dataverse_bosnia_1991_municipalities__municipalities_wgs84.geojson"), ["Municip"], min_area=0.001)

  # --- 5. Central Europe: HRE, Weimar, Divided Germany (FRG+GDR), Czechoslovakia ---
  S["hre_pre1648"] = _load_gj_list(os.path.join(p_de, "hre_oxford_pre1648_territories.geojson"), ["Name", "Controlled"])
  S["hre_post1648"] = _load_gj_list(os.path.join(p_de, "hre_oxford_post1648_territories_confessions.geojson"), ["Name", "Controlled"], min_area=0.001)
  S["de_confed_1848"] = _load_gj_list(os.path.join(p_de, "hgis_german_confederation_1848_states.geojson"), ["NAME", "STAAT_NAME", "name"])
  S["de_emp_1871"] = _load_gj_list(os.path.join(p_de, "hgis_german_empire_1871_states.geojson"), ["NAME", "STAAT_NAME", "name"])
  S["de_weimar_1926_st"] = _load_gj_list(os.path.join(p_de, "de_weimar_1926_states.geojson"), ["name", "state", "district", "id"])
  S["de_weimar_1930_td"] = _load_gj_list(os.path.join(p_de, "de_weimar_1930_taxdistricts.geojson"), ["district", "id"], min_area=0.001)
  S["de_reich_1937_td"] = _load_gj_list(os.path.join(p_de, "de_reich_1937_taxdistricts.geojson"), ["district", "id"], min_area=0.001)
  S["de_bkg_rb_bez"] = {}
  for by in (1955, 1970, 1980):
    S["de_bkg_rb_bez"][by] = _load_gj_list(os.path.join(p_de, f"de_frg_rb_gdr_bezirke_{by}_bkg.geojson"), ["SAMPLE_KREISE", "VGHID2_LAND_BEZIRK"], extra_keys=["STG", "VGHID2_LAND_BEZIRK"])
  S["de_frg_gdr_1989"] = _load_gj_list(os.path.join(p_de, "de_frg_gdr_1989_laender_bezirke.geojson"), ["GEN"], extra_keys=["STG"])
  S["cz_1850_kraje"] = _load_gj_list(os.path.join(p_de, "cz_1850_kraje.geojson"), ["NAZEV", "kraj", "name"])
  S["csr_1920_zupy"] = _load_gj_list(os.path.join(p_de, "csr_1920_zupy.geojson"), ["NAZEV"])
  S["csr_1949_kraje"] = (
    _load_gj_list(os.path.join(p_de, "csr_1949_1960_kraje_1950_naki_simpl2000.geojson"), ["kraj_nazev", "NAZEV"])
    + _load_gj_list(os.path.join(p_de, "csr_1949_1960_sr_kraje_1949_1960_simpl2000.geojson"), ["kraj_nazev", "NAZEV", "kraj", "NAME"])
  )
  S["csr_1960_kraje"] = (
    _load_gj_list(os.path.join(p_de, "csr_1960_1990_kraje_1961_naki_simpl2400.geojson"), ["NAZ_kraj", "NAZEV"])
    + _load_gj_list(os.path.join(p_de, "csr_1960_1990_sr_kraje_1960_1990.geojson"), ["NAZ_kraj", "NAZEV", "kraj", "NAME"])
  )
  S["univie_at_1910"] = _load_gj_list(os.path.join(p_de, "univie_cisleithania_austria_1910_pol_bez.geojson"), ["NAME", "POL_BEZ", "BEZIRK", "name"], min_area=0.002)

  # --- 6. Nordics, UK & Ireland ---
  S["uk_hct_defA"] = _load_gj_list(os.path.join(p_uk, "uk_historic_counties_defA_pre1844_hct.geojson"), ["NAME", "COUNTY"])
  S["uk_hct_defB"] = _load_gj_list(os.path.join(p_uk, "uk_historic_counties_defB_post1844_hct.geojson"), ["NAME", "COUNTY"])
  S["ie_32_counties"] = _load_gj_list(os.path.join(p_uk, "ireland_historic_32_counties_townlands.geojson"), ["NAME_TAG", "NAME_EN"])
  S["dk_19_amter"] = _load_gj_list(os.path.join(p_uk, "denmark_historic_19_amter_1793_1920_digdag.geojson"), ["AMT"])
  S["dk_23_amter"] = _load_gj_list(os.path.join(p_uk, "denmark_historic_23_amter_1920_1970_digdag.geojson"), ["AMT"])
  S["no_20_amt"] = _load_gj_list(os.path.join(p_uk, "norway_historic_20_fylker_amt_1831_1972_kartverket.geojson"), ["fylke_name", "historic_amt_name"], extra_keys=["fylkesnummer", "historic_amt_name"])
  S["no_19_fylker"] = _load_gj_list(os.path.join(p_uk, "norway_historic_19_fylker_1972_2017_kartverket.geojson"), ["fylke_name"], extra_keys=["fylkesnummer"])
  # Finland 1938 pre-Winter War (dissolved into ~24 clean regional clusters by first 2 letters/spatial grid or direct parishes -> dissolved by 6x5 organic clusters or loaded cleanly)
  S["fi_1938_parishes"] = _load_gj_list(os.path.join(p_uk, "finland_historic_parishes_1938_kotus_with_karelia.geojson"), ["NIMI", "PITäjÄ"], min_area=0.002)
  S["fi_mml_20"] = _load_gj_list(os.path.join(p_uk, "finland_historic_20_maakunta_1998_mml.geojson"), ["NAMEFIN", "Maakunta", "nimi", "name"])
  S["fi_mml_6"] = _load_gj_list(os.path.join(p_uk, "finland_historic_6_laani_1997_2009_mml.geojson"), ["NAMEFIN", "Laani", "nimi", "name"])
  S["is_9_umdaemi"] = _load_gj_list(os.path.join(p_uk, "iceland_districts_umdaemi_lmi.geojson"), ["nafn", "NAME", "umdami"])

  # Archival Denmark DigDag Amter Census (1787-1921)
  dk_cens = defaultdict(dict)
  dk_cp = os.path.join(p_uk, "denmark_historic_amter_census_1787_1921_digdag.csv")
  if os.path.isfile(dk_cp):
    with open(dk_cp, encoding="utf-8", errors="replace") as fh:
      for r in csv.DictReader(fh):
        try:
          yr, pop = int(float(r["year"])), float(r["population"])
          anm = norm_str(r["amt"])
          if pop > 0:
            dk_cens[anm][yr] = pop
        except Exception:
          pass
  S["dk_amt_census"] = dict(dk_cens)

  # Archival Norway SSB County Census (1801-2001)
  no_cens = defaultdict(dict)
  no_cp = os.path.join(p_uk, "norway_ssb_histstat_3_2_county_population_1801_2001.csv")
  if os.path.isfile(no_cp):
    with open(no_cp, encoding="utf-8", errors="replace") as fh:
      rdr = csv.reader(fh)
      hdr = next(rdr, [])
      yr_map = []
      for idx_c, h in enumerate(hdr):
        m = re.search(r"(18\d\d|19\d\d|20\d\d)", h)
        if m:
          yr_map.append((idx_c, int(m.group(1))))
      for r in rdr:
        if not r or not r[0] or r[0].strip().isdigit():
          continue
        cn = norm_str(r[0])
        for idx_c, yr in yr_map:
          if idx_c < len(r):
            vs = re.sub(r"[^\d.]", "", r[idx_c])
            if vs:
              try:
                v = float(vs)
                if v > 500:
                  no_cens[cn][yr] = v
              except Exception:
                pass
  S["no_amt_census"] = dict(no_cens)

  # --- 7. Spain Antiguo Régimen, Portugal Historic Províncias & Pre-Unification Italy ---
  S["es_1500_reinos"] = _load_gj_list(os.path.join(p_sa, "spain_antiguo_regimen", "spain_reinos_1500_euratlas.geojson"), ["short_name", "long_name", "num"])
  S["es_1812_33prov"] = _load_gj_list(os.path.join(p_sa, "spain_antiguo_regimen", "spain_provincias_1812_antiguo_regimen_33prov.geojson"), ["Provincia"], pop_keys=["Población"])
  S["pt_1500_provs"] = _load_gj_list(os.path.join(p_sa, "portugal_historic", "portugal_provincias_1500_euratlas.geojson"), ["short_name", "long_name", "num"])
  S["it_1500_states"] = _load_gj_list(os.path.join(p_sa, "italy_preunification", "italy_states_giustizierati_1500_euratlas.geojson"), ["short_name", "long_name", "num"])

  print(
    f"  [HGIS+] Loaded scraped vaults: FR_1789_Bail={len(S['fr_1789_bailliages'])} | HRE_1648={len(S['hre_post1648'])} | "
    f"PLC_1619={len(S['plc_1619_voiv'])} | PLC_1772={len(S['plc_1772_voiv'])} | PL_1900={len(S['pl_1900_gub'])} | "
    f"IIRP_1931={len(S['pl_iirp_1931'])} | PRL_50/75={len(S['pl_prl_1950'])}/{len(S['pl_prl_1975'])} | "
    f"GISta_HU={len(S['gista_hu_1910'])} | RoHGIS_30={len(S['rohgis_1930_judete'])} | SFRY_53={len(S['sfry_muni'][1953])} | "
    f"UK_92={len(S['uk_hct_defB'])} | DK_23={len(S['dk_23_amter'])} | NO_20={len(S['no_20_amt'])} | "
    f"ES_1812={len(S['es_1812_33prov'])} | IT_1500={len(S['it_1500_states'])} | FRG_GDR_89={len(S['de_frg_gdr_1989'])}",
    flush=True,
  )
  return S
