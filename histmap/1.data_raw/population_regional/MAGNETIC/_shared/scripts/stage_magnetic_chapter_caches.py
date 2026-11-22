"""Stages pre-computed JSON summary caches for all 21 Project MAGNETIC chapters and root synthesis.

Combines:
  - Per-chapter `<stem>.json5` sub-regional population trajectories & areas
  - Per-chapter `<stem>_settlements.json` & `<stem>_source_ledger.json5`
  - Scraped historical HGIS sub-administrative enumerations (`subadmin_enumerations_for_literature_reviews.csv`)
  - Stage C `2.population_rasters/` raster sums across all 128 time steps & kriging validation stats
"""

import csv
import glob
import json
import math
import os
import re
from collections import defaultdict

import numpy as np
from PIL import Image

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC")
SHARED = os.path.join(MAG_DIR, "_shared")
ITIN_PATH = os.path.join(MAG_DIR, "magnetic_itinerary.json5")
HGIS_CSV = os.path.join(SHARED, "subadmin_hgis", "subadmin_enumerations_for_literature_reviews.csv")
POP_DIR = os.path.join(SHARED, "sites_magnetic_europe", "2.population_rasters")

GRID_W, GRID_H = 4320, 2160
CELL_LAT_RAD = math.pi / GRID_H
CELL_LON_RAD = 2.0 * math.pi / GRID_W
R_EARTH_KM = 6371.0088


def load_json5_simple (arg0_path):
  raw = open(arg0_path, encoding="utf-8").read()
  raw = re.sub(r"//.*", "", raw)
  raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
  raw = re.sub(r",(\s*[}\]])", r"\1", raw)
  raw = re.sub(r"(\{|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
  return json.loads(raw)


def compute_row_cell_areas_km2 ():
  lats_n = np.linspace(90.0, -90.0, GRID_H + 1)
  sin_n = np.sin(np.radians(lats_n[:-1]))
  sin_s = np.sin(np.radians(lats_n[1:]))
  return (R_EARTH_KM ** 2) * CELL_LON_RAD * np.abs(sin_n - sin_s)


def decode_velk_png_sum (arg0_path):
  arr = np.ascontiguousarray(Image.open(arg0_path).convert("RGBA"), dtype=np.uint8)
  vals = arr.view(">f4").reshape(arr.shape[:2])
  vals = np.where(np.isfinite(vals) & (vals > 0.0) & (vals < 1e8), vals, 0.0)
  return int(round(float(vals.sum())))


def load_hgis_rows ():
  rows = []
  if not os.path.isfile(HGIS_CSV):
    return rows
  with open(HGIS_CSV, encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
      try:
        rows.append({
          "snapshot_regime": int(r["snapshot_regime"]),
          "country": str(r["country"]).strip(),
          "unit_code": str(r["unit_code"]).strip(),
          "unit_name": str(r["unit_name"]).strip(),
          "year": int(r["year"]),
          "population": int(round(float(r["population"]))),
          "area_km2": round(float(r["area_km2"]), 1),
          "source": str(r["source"]).strip(),
        })
      except Exception:
        continue
  return rows


# Map HGIS country codes to ISO-like European country names for chapter filtering
HGIS_COUNTRY_MATCH = {
  "FR": "France", "EM_france": "France", "CS_france": "France",
  "UK": "United Kingdom", "GB": "United Kingdom", "EM_england": "United Kingdom", "EM_scotland": "United Kingdom", "CS_united king": "United Kingdom",
  "IE": "Ireland", "CS_ireland": "Ireland",
  "NL": "Netherlands", "BE": "Belgium", "LU": "Luxembourg", "CS_netherland": "Netherlands", "CS_belgium": "Belgium",
  "SE": "Sweden", "NO": "Norway", "DK": "Denmark", "FI": "Finland", "IS": "Iceland", "FO": "Faroe Islands", "GL": "Greenland",
  "CS_sweden": "Sweden", "CS_norway": "Norway", "CS_denmark": "Denmark", "CS_finland": "Finland",
  "DE": "Germany", "HRE": "Germany", "DE_IMP": "Germany", "PRUSSIA": "Germany", "CS_german emp": "Germany", "CS_germany": "Germany",
  "AT": "Austria", "AH_IMP": "Austria", "HABSBURG": "Austria", "CS_austria": "Austria", "CH": "Switzerland", "CS_switzerlan": "Switzerland",
  "PL": "Poland", "EM_poland lit": "Poland", "CS_poland": "Poland", "CZ": "Czechia", "SK": "Slovakia", "HU": "Hungary", "CS_czechoslov": "Czechia", "CS_hungary": "Hungary",
  "IT": "Italy", "CS_italy": "Italy", "ES": "Spain", "EM_spain": "Spain", "CS_spain": "Spain", "PT": "Portugal", "EM_portugal": "Portugal", "CS_portugal": "Portugal",
  "GR": "Greece", "EL": "Greece", "MT": "Malta", "CS_greece": "Greece",
  "RO": "Romania", "BG": "Bulgaria", "RS": "Serbia", "HR": "Croatia", "SI": "Slovenia", "BA": "Bosnia and Herzegovina",
  "ME": "Montenegro", "MK": "North Macedonia", "AL": "Albania", "EM_ottoman em": "Turkey", "CS_ottoman em": "Turkey",
  "CS_romania": "Romania", "CS_bulgaria": "Bulgaria", "CS_yugoslavia": "Serbia", "CS_albania": "Albania",
  "EE": "Estonia", "LV": "Latvia", "LT": "Lithuania", "CS_estonia": "Estonia", "CS_latvia": "Latvia", "CS_lithuania": "Lithuania",
}


def interp_subregion_series (arg0_pop_dict, arg1_target_years):
  """Log-interpolates a sub-region's recorded census/benchmark series cleanly onto unified chapter years."""
  pts = sorted((int(k), float(v)) for k, v in arg0_pop_dict.items() if float(v) > 0)
  if not pts:
    return {str(y): 0 for y in arg1_target_years}
  out = {}
  for y in arg1_target_years:
    if y <= pts[0][0]:
      out[str(y)] = int(round(pts[0][1]))
    elif y >= pts[-1][0]:
      out[str(y)] = int(round(pts[-1][1]))
    else:
      for i in range(len(pts) - 1):
        y0, v0 = pts[i]
        y1, v1 = pts[i + 1]
        if y0 <= y <= y1:
          t = (y - y0) / max(1.0, float(y1 - y0))
          out[str(y)] = int(round(math.exp((1.0 - t) * math.log(v0) + t * math.log(v1))))
          break
  return out


def choose_unified_years (arg0_all_years, arg1_d0, arg2_d1):
  """Collapses staggered national census years (e.g. 1800/1801, 1910/1911) into clean unified benchmarks."""
  sy = sorted(arg0_all_years)
  if len(sy) <= 8:
    return sy
  # Merge years within <= 3 years of each other, preferring round 5/10/end benchmarks
  groups = [[sy[0]]]
  for y in sy[1:]:
    if y - groups[-1][-1] <= 4:
      groups[-1].append(y)
    else:
      groups.append([y])
  unified = []
  for g in groups:
    # Prefer exact domain boundary or multiple of 10 or median
    best = next((v for v in g if v in (arg1_d0, arg2_d1)), None)
    if best is None:
      best = next((v for v in g if v % 10 == 0), g[len(g) // 2])
    unified.append(best)
  return sorted(set(unified))


def main ():
  itin = load_json5_simple(ITIN_PATH)
  row_areas = compute_row_cell_areas_km2()
  hgis_rows = load_hgis_rows()
  print(f"[1] Loaded {len(hgis_rows)} scraped HGIS sub-admin rows across {len(set(r['snapshot_regime'] for r in hgis_rows))} regimes.", flush=True)

  chapter_overview = []
  total_settlements_all = 0
  all_hgis_sources = sorted(set(r["source"] for r in hgis_rows))

  for ch in itin["chapters"]:
    key = ch["key"]
    ch_dir = os.path.join(MAG_DIR, ch["folder"])
    d0, d1 = int(ch["domain"][0]), int(ch["domain"][1])
    j5 = load_json5_simple(os.path.join(ch_dir, f"{key}.json5"))
    setts = json.load(open(os.path.join(ch_dir, f"{key}_settlements.json"), encoding="utf-8"))
    ledger = load_json5_simple(os.path.join(ch_dir, f"{key}_source_ledger.json5"))
    mask_arr = np.asarray(Image.open(os.path.join(ch_dir, f"{key}_areal_mask.png")).convert("RGBA"), dtype=np.uint8)

    # Exact sub-region areas from areal mask
    subregion_rows = []
    tot_area_km2 = 0.0
    all_years = set()
    for reg in j5.get("regions", []):
      rgb = tuple(int(v) for v in reg["rgb"])
      m_bool = (mask_arr[:, :, 3] > 0) & (mask_arr[:, :, 0] == rgb[0]) & (mask_arr[:, :, 1] == rgb[1]) & (mask_arr[:, :, 2] == rgb[2])
      area_km2 = float((m_bool.sum(axis=1) * row_areas).sum())
      tot_area_km2 += area_km2
      pop_dict = {str(k): int(round(float(v))) for k, v in (reg.get("population") or {}).items()}
      for yk in pop_dict:
        all_years.add(int(yk))
      subregion_rows.append({
        "id": reg["id"],
        "name": reg.get("name") or reg["id"],
        "rgb": list(rgb),
        "area_km2": round(area_km2, 1),
        "population": pop_dict,
      })

    sorted_years = choose_unified_years(all_years, d0, d1)
    for sr in subregion_rows:
      sr["population_raw"] = dict(sr["population"])
      sr["population"] = interp_subregion_series(sr["population_raw"], sorted_years)
    domain_totals = {}
    for y in sorted_years:
      ys = str(y)
      domain_totals[ys] = sum(r["population"].get(ys, 0) for r in subregion_rows)

    # Settlement summary
    sett_list = list(setts.values())
    total_settlements_all += len(sett_list)
    countries_in_ch = sorted(set(s.get("country", "") for s in sett_list if s.get("country")))
    by_region_cnt = defaultdict(int)
    by_country_cnt = defaultdict(int)
    by_prov_cnt = defaultdict(int)
    top_setts = []
    for s in sett_list:
      by_region_cnt[s.get("region_id", "")] += 1
      by_country_cnt[s.get("country", "")] += 1
      by_prov_cnt[s.get("provenance_source", "MAGNETIC")] += 1
      pdict = s.get("population") or {}
      if pdict:
        yrs = sorted(int(k) for k in pdict.keys())
        pk_yr = max(yrs, key=lambda y: pdict[str(y)])
        top_setts.append({
          "name": s["name"],
          "country": s.get("country", ""),
          "region_id": s.get("region_id", ""),
          "lat": round(float(s["coords"][0]), 3),
          "lon": round(float(s["coords"][1]), 3),
          "peak_year": pk_yr,
          "peak_pop": int(pdict[str(pk_yr)]),
          "first_year": yrs[0],
          "last_year": yrs[-1],
          "provenance_source": s.get("provenance_source", ""),
          "population": pdict,
        })
    top_setts.sort(key=lambda x: -x["peak_pop"])

    # Filter HGIS sub-administrative enumerations relevant to this chapter's domain & countries!
    ch_hgis = []
    if d1 >= 1500:
      ctry_set = set(countries_in_ch)
      for hr in hgis_rows:
        if d0 <= hr["year"] <= d1:
          mapped_c = HGIS_COUNTRY_MATCH.get(hr["country"], hr["country"])
          if mapped_c in ctry_set or hr["country"] in ctry_set:
            ch_hgis.append(hr)
    # Aggregate HGIS by (snapshot_regime, source) & top 25 largest sub-admin units for clean literature-review tables!
    hgis_by_regime_src = defaultdict(lambda: {"units": 0, "pop_sum": 0, "area_sum": 0.0})
    for hr in ch_hgis:
      rk = (hr["snapshot_regime"], hr["source"])
      hgis_by_regime_src[rk]["units"] += 1
      hgis_by_regime_src[rk]["pop_sum"] += hr["population"]
      hgis_by_regime_src[rk]["area_sum"] += hr["area_km2"]
    hgis_summary_rows = [
      {
        "snapshot_regime": rk[0],
        "source": rk[1],
        "units": v["units"],
        "population_sum": v["pop_sum"],
        "area_km2_sum": round(v["area_sum"], 1),
      }
      for rk, v in sorted(hgis_by_regime_src.items())
    ]
    # Top 20 representative sub-admin units across regimes (deduped by unit_name + year, largest pop first)
    ch_hgis_sorted = sorted(ch_hgis, key=lambda x: (-x["population"], x["year"]))
    seen_u = set()
    hgis_featured = []
    for hr in ch_hgis_sorted:
      uk = (hr["unit_name"], hr["year"])
      if uk in seen_u:
        continue
      seen_u.add(uk)
      hgis_featured.append(hr)
      if len(hgis_featured) >= 24:
        break

    # Papers metadata summary
    p_meta_path = os.path.join(ch_dir, "papers", "papers_metadata.json")
    n_pdfs = len(glob.glob(os.path.join(ch_dir, "papers", "*.pdf")))
    summary_obj = {
      "index": ch["index"],
      "key": key,
      "folder": ch["folder"],
      "itinerary_title": ch["itinerary_title"],
      "subtitle": ch["subtitle"],
      "domain": [d0, d1],
      "total_area_km2": round(tot_area_km2, 1),
      "benchmark_years": sorted_years,
      "domain_totals": domain_totals,
      "subregions": subregion_rows,
      "settlement_count": len(sett_list),
      "countries": countries_in_ch,
      "settlements_by_region": dict(by_region_cnt),
      "settlements_by_country": dict(by_country_cnt),
      "provenance_counts": dict(by_prov_cnt),
      "crowd_share_overall": ledger.get("saturation_audit", {}).get("crowd_share_overall", 0.0),
      "top_settlements": top_setts[:30],
      "hgis_row_count": len(ch_hgis),
      "hgis_regime_summary": hgis_summary_rows,
      "hgis_featured_units": hgis_featured,
      "archival_pdf_count": n_pdfs,
    }
    out_p = os.path.join(ch_dir, f"{key}_summary.json")
    with open(out_p, "w", encoding="utf-8") as fh:
      json.dump(summary_obj, fh, indent=2, ensure_ascii=False)

    y_start = str(sorted_years[0]) if sorted_years else ""
    y_end = str(sorted_years[-1]) if sorted_years else ""
    chapter_overview.append({
      "index": ch["index"],
      "key": key,
      "folder": ch["folder"],
      "itinerary_title": ch["itinerary_title"],
      "domain": [d0, d1],
      "area_km2": round(tot_area_km2, 1),
      "subregions": len(subregion_rows),
      "settlements": len(sett_list),
      "hgis_rows": len(ch_hgis),
      "pop_start": domain_totals.get(y_start, 0),
      "pop_end": domain_totals.get(y_end, 0),
      "start_year": sorted_years[0] if sorted_years else d0,
      "end_year": sorted_years[-1] if sorted_years else d1,
      "archival_pdfs": n_pdfs,
    })
    print(f"  [CH {ch['index']:02d}] {key:55s}: {len(sett_list):4d} setts | {len(ch_hgis):4d} HGIS rows | {tot_area_km2/1e6:5.2f}M km²", flush=True)

  # Stage C macro raster totals for benchmark years
  macro_bench = [-10000, -8000, -6000, -4000, -2500, -1000, -500, -200, 0, 200, 400, 500, 700, 800, 1000, 1200, 1300, 1340, 1400, 1500, 1600, 1650, 1700, 1750, 1800, 1850, 1880, 1900, 1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020, 2025]
  raster_series = {}
  for y in macro_bench:
    rp = os.path.join(POP_DIR, f"popc_{y}.png")
    if os.path.isfile(rp):
      lbl_y = "1" if y == 0 else str(y)
      raster_series[lbl_y] = decode_velk_png_sum(rp)

  # Load Stage C validation summary if present
  c1_json = {}
  for cand in (
    os.path.join(SHARED, "sites_magnetic_europe", "1.kriged_rasters", "kriging_validation_report.json"),
    os.path.join(SHARED, "sites_magnetic_europe", "kriging_diagnostics.json"),
    os.path.join(POP_DIR, "subadmin_mass_conservation_report.json"),
  ):
    if os.path.isfile(cand):
      c1_json[os.path.basename(cand)] = json.load(open(cand, encoding="utf-8"))

  root_summary = {
    "project": "MAGNETIC",
    "root_title": itin["root_title"],
    "root_subtitle": itin["root_subtitle"],
    "chapter_count": len(chapter_overview),
    "total_chapter_settlement_trajectories": total_settlements_all,
    "total_hgis_rows": len(hgis_rows),
    "hgis_snapshot_count": len(set(r["snapshot_regime"] for r in hgis_rows)),
    "hgis_sources": all_hgis_sources,
    "macro_raster_series": raster_series,
    "chapters": chapter_overview,
    "stage_c_reports": c1_json,
  }
  with open(os.path.join(SHARED, "magnetic_root_summary.json"), "w", encoding="utf-8") as fh:
    json.dump(root_summary, fh, indent=2, ensure_ascii=False)
  print(f"\n[DONE] Staged 21 chapter caches + magnetic_root_summary.json ({len(raster_series)} macro raster epochs).", flush=True)


if __name__ == "__main__":
  main()
