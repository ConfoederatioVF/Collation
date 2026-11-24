"""Stages pre-computed JSON summary caches for all 17 Project QUIPU chapters and root synthesis.

Combines:
  - Per-chapter `<stem>.json5` sub-regional population trajectories & areas
  - Per-chapter `<stem>_settlements.json` & `<stem>_source_ledger.json5`
  - Scraped historical HGIS sub-administrative enumerations (`subadmin_enumerations_for_literature_reviews.json` + `.csv`)
  - Stage C `2.population_rasters/` raster sums across benchmark epochs & `kriging_diagnostics.json` + `sites_quipu_andes_cone_geojson_metadata.json`
  - Copies Intellte RMarkdown template assets (`crd-mla-numeric.csl`, `crd_logo.png`, `intellte-sample.bib`, `intellte.cls`) into all 17 chapter directories.
"""

import csv
import glob
import json
import math
import os
import re
import shutil
from collections import defaultdict

import numpy as np
from PIL import Image

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
QUIPU_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "QUIPU")
SHARED = os.path.join(QUIPU_DIR, "_shared")
ITIN_PATH = os.path.join(QUIPU_DIR, "quipu_itinerary.json5")
HGIS_CSV = os.path.join(SHARED, "subadmin_hgis", "subadmin_enumerations_for_literature_reviews.csv")
HGIS_JSON = os.path.join(SHARED, "subadmin_hgis", "subadmin_enumerations_for_literature_reviews.json")
MC_AUDIT_JSON = os.path.join(SHARED, "subadmin_hgis", "subadmin_mass_conservation_audit.json")
SITES_CFG = os.path.join(SHARED, "sites_quipu_andes_cone", "config")
POP_DIR = os.path.join(SHARED, "sites_quipu_andes_cone", "2.population_rasters")

GRID_W, GRID_H = 4320, 2160
CELL_LON_RAD = 2.0 * math.pi / GRID_W
R_EARTH_KM = 6371.0088

TEMPLATE_ASSETS = [
  "crd-mla-numeric.csl",
  "crd_logo.png",
  "intellte-sample.bib",
  "intellte.cls",
]

HGIS_COUNTRY_MATCH = {
  "Argentina": ["Argentina"],
  "Bolivia": ["Bolivia"],
  "Chile": ["Chile"],
  "Colombia": ["Colombia"],
  "Ecuador": ["Ecuador"],
  "Falkland Islands & South Atlantic": ["Falkland Islands", "South Georgia and the Islands"],
  "Peru": ["Peru"],
  "Uruguay": ["Uruguay"],
  "Venezuela": ["Venezuela"],
  "Spanish_America_PER": ["Peru"],
  "Early_Republic_PER": ["Peru"],
  "Spanish_America_CHA": ["Bolivia"],
  "Early_Republic_CHA": ["Bolivia"],
  "Spanish_America_NGR": ["Colombia"],
  "Early_Republic_NGR": ["Colombia"],
  "Spanish_America_QUI": ["Ecuador"],
  "Early_Republic_QUI": ["Ecuador"],
  "Spanish_America_VEN": ["Venezuela"],
  "Early_Republic_VEN": ["Venezuela"],
  "Spanish_America_CHL": ["Chile"],
  "Early_Republic_CHL": ["Chile"],
  "Spanish_America_RPL": ["Argentina", "Uruguay"],
  "Early_Republic_RPL": ["Argentina", "Uruguay"],
}


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
        pop_raw = str(r.get("interpolated_population", "")).strip()
        pop_val = int(round(float(pop_raw))) if pop_raw else 0
        rows.append({
          "snapshot_regime": int(r["boundary_regime"]),
          "country": str(r["country"]).strip(),
          "unit_code": str(r["unit_code"]).strip(),
          "unit_name": str(r["unit_name"]).strip(),
          "year": int(r["year"]),
          "population": pop_val,
          "area_km2": round(float(r["area_km2"]), 1),
          "source": str(r["source"]).strip(),
        })
      except Exception:
        continue
  return rows


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
  """Collapses staggered census years into clean unified benchmarks."""
  sy = sorted(arg0_all_years)
  if len(sy) <= 10:
    return sy
  groups = [[sy[0]]]
  for y in sy[1:]:
    if y - groups[-1][-1] <= 4:
      groups[-1].append(y)
    else:
      groups.append([y])
  unified = []
  for g in groups:
    best = next((v for v in g if v in (arg1_d0, arg2_d1)), None)
    if best is None:
      best = next((v for v in g if v % 10 == 0), g[len(g) // 2])
    unified.append(best)
  return sorted(set(unified))


def extract_regions_list (arg0_j5):
  """Normalises chapter `.json5` `regions` field (dict or list) into a canonical list of dicts."""
  regs_raw = arg0_j5.get("regions")
  out = []
  if isinstance(regs_raw, dict):
    for rid, robj in regs_raw.items():
      item = dict(robj)
      item["id"] = str(item.get("id") or rid)
      out.append(item)
  elif isinstance(regs_raw, list):
    for robj in regs_raw:
      out.append(dict(robj))
  return out


def stage_template_assets (arg0_chapter_dir):
  """Copies shared Intellte LaTeX/CSL assets into a chapter directory when missing."""
  copied = 0
  for fn in TEMPLATE_ASSETS:
    src = os.path.join(QUIPU_DIR, fn)
    if not os.path.isfile(src):
      src = os.path.join(SHARED, "template", fn)
    dst = os.path.join(arg0_chapter_dir, fn)
    if os.path.isfile(src) and not os.path.isfile(dst):
      shutil.copy2(src, dst)
      copied += 1
  return copied


def main ():
  itin = load_json5_simple(ITIN_PATH)
  row_areas = compute_row_cell_areas_km2()
  hgis_rows = load_hgis_rows()
  hgis_meta = json.load(open(HGIS_JSON, encoding="utf-8")) if os.path.isfile(HGIS_JSON) else {}
  print(f"[1] Loaded {len(hgis_rows)} HGIS sub-admin rows across {len(set(r['snapshot_regime'] for r in hgis_rows))} regimes.", flush=True)

  chapter_overview = []
  compact_chapters = {}
  total_settlements_all = 0
  all_hgis_sources = sorted(set(r["source"] for r in hgis_rows))
  total_assets_copied = 0

  for ch in itin["chapters"]:
    key = ch["key"]
    ch_dir = os.path.join(QUIPU_DIR, ch["folder"])
    total_assets_copied += stage_template_assets(ch_dir)

    d0, d1 = int(ch["domain"][0]), int(ch["domain"][1])
    j5 = load_json5_simple(os.path.join(ch_dir, f"{key}.json5"))
    setts = json.load(open(os.path.join(ch_dir, f"{key}_settlements.json"), encoding="utf-8"))
    ledger = load_json5_simple(os.path.join(ch_dir, f"{key}_source_ledger.json5"))
    mask_arr = np.asarray(Image.open(os.path.join(ch_dir, f"{key}_areal_mask.png")).convert("RGBA"), dtype=np.uint8)

    subregion_rows = []
    tot_area_km2 = 0.0
    all_years = set()
    for reg in extract_regions_list(j5):
      rgb_raw = reg.get("colour") or reg.get("rgb") or [120, 140, 160]
      rgb = tuple(int(v) for v in rgb_raw[:3])
      m_bool = (mask_arr[:, :, 3] > 0) & (mask_arr[:, :, 0] == rgb[0]) & (mask_arr[:, :, 1] == rgb[1]) & (mask_arr[:, :, 2] == rgb[2])
      area_km2 = float((m_bool.sum(axis=1) * row_areas).sum())
      if area_km2 < 1.0 and reg.get("area_km2"):
        area_km2 = float(reg["area_km2"])
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

    sett_list = list(setts.values()) if isinstance(setts, dict) else list(setts)
    total_settlements_all += len(sett_list)
    countries_in_ch = sorted(set(s.get("country", "") for s in sett_list if s.get("country")))
    by_region_cnt = defaultdict(int)
    by_country_cnt = defaultdict(int)
    by_prov_cnt = defaultdict(int)
    top_setts = []
    for s in sett_list:
      by_region_cnt[s.get("region_id", "")] += 1
      by_country_cnt[s.get("country", "")] += 1
      by_prov_cnt[s.get("provenance_source", s.get("source", "QUIPU"))] += 1
      pdict = s.get("population") or {}
      if pdict:
        yrs = sorted(int(k) for k in pdict.keys() if float(pdict[k]) > 0)
        if yrs:
          pk_yr = max(yrs, key=lambda y: float(pdict[str(y)]))
          top_setts.append({
            "name": s["name"],
            "country": s.get("country", ""),
            "region_id": s.get("region_id", ""),
            "lat": round(float(s["coords"][0]), 3),
            "lon": round(float(s["coords"][1]), 3),
            "peak_year": pk_yr,
            "peak_pop": int(round(float(pdict[str(pk_yr)]))),
            "first_year": yrs[0],
            "last_year": yrs[-1],
            "provenance_source": s.get("provenance_source", s.get("source", "")),
            "population": pdict,
          })
    top_setts.sort(key=lambda x: -x["peak_pop"])

    # Filter HGIS sub-administrative enumerations relevant to this chapter's domain & countries
    ch_hgis = []
    if d1 >= 1500:
      ctry_set = set(countries_in_ch)
      for hr in hgis_rows:
        if d0 <= hr["year"] <= d1:
          matched = HGIS_COUNTRY_MATCH.get(hr["country"], [hr["country"]])
          if any(mc in ctry_set for mc in matched):
            ch_hgis.append(hr)

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

    n_pdfs = len(glob.glob(os.path.join(ch_dir, "papers", "*.pdf")))
    sat = ledger.get("saturation_audit") or {}
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
      "crowd_share_overall": float(sat.get("crowd_share_overall", 0.0)),
      "saturation_marginal_gain_pct": float(sat.get("marginal_gain_pct", 0.0)),
      "ledger_total_included": int(ledger.get("total_included", len(sett_list))),
      "ledger_total_excluded": int(ledger.get("total_excluded", 0)),
      "top_settlements": top_setts[:30],
      "hgis_row_count": len(ch_hgis),
      "hgis_regime_summary": hgis_summary_rows,
      "hgis_featured_units": hgis_featured,
      "archival_pdf_count": n_pdfs,
    }
    out_p = os.path.join(ch_dir, f"{key}_summary.json")
    with open(out_p, "w", encoding="utf-8") as fh:
      json.dump(summary_obj, fh, indent=2, ensure_ascii=False)

    compact_chapters[key] = {
      "index": ch["index"],
      "key": key,
      "folder": ch["folder"],
      "itinerary_title": ch["itinerary_title"],
      "subtitle": ch["subtitle"],
      "domain": [d0, d1],
      "total_area_km2": round(tot_area_km2, 1),
      "benchmark_years": sorted_years,
      "domain_totals": domain_totals,
      "subregion_count": len(subregion_rows),
      "subregions_compact": [
        {
          "id": r["id"],
          "name": r["name"],
          "area_km2": r["area_km2"],
          "pop_start": r["population"].get(str(sorted_years[0]), 0) if sorted_years else 0,
          "pop_end": r["population"].get(str(sorted_years[-1]), 0) if sorted_years else 0,
        }
        for r in subregion_rows
      ],
      "settlement_count": len(sett_list),
      "countries": countries_in_ch,
      "crowd_share_overall": summary_obj["crowd_share_overall"],
      "saturation_marginal_gain_pct": summary_obj["saturation_marginal_gain_pct"],
      "top_10_settlements": [
        {
          "name": t["name"],
          "country": t["country"],
          "peak_year": t["peak_year"],
          "peak_pop": t["peak_pop"],
        }
        for t in top_setts[:10]
      ],
      "hgis_row_count": len(ch_hgis),
      "archival_pdf_count": n_pdfs,
    }

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
    print(f"  [CH {ch['index']:02d}] {key:36s}: {len(sett_list):4d} setts | {len(ch_hgis):4d} HGIS | {tot_area_km2/1e6:5.2f}M km²", flush=True)

  # Stage C macro raster totals for benchmark years
  macro_bench = [
    -10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000,
    0, 200, 400, 600, 800, 1000, 1200, 1300, 1400, 1500, 1600, 1700,
    1750, 1780, 1800, 1820, 1850, 1870, 1890, 1900, 1910, 1920, 1930,
    1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020, 2025,
  ]
  raster_series = {}
  for y in macro_bench:
    rp = os.path.join(POP_DIR, f"popc_{y}.png")
    if os.path.isfile(rp):
      lbl_y = "1" if y == 0 else str(y)
      raster_series[lbl_y] = decode_velk_png_sum(rp)

  # Load Stage C kriging diagnostics, archaeological metadata & mass conservation audit
  kriging_diag = {}
  kd_path = os.path.join(SITES_CFG, "kriging_diagnostics.json")
  if os.path.isfile(kd_path):
    kriging_diag = json.load(open(kd_path, encoding="utf-8"))

  geo_meta = {}
  gm_path = os.path.join(SITES_CFG, "sites_quipu_andes_cone_geojson_metadata.json")
  if os.path.isfile(gm_path):
    geo_meta = json.load(open(gm_path, encoding="utf-8"))

  mc_audit = {}
  if os.path.isfile(MC_AUDIT_JSON):
    mc_audit = json.load(open(MC_AUDIT_JSON, encoding="utf-8"))

  root_summary = {
    "project": "QUIPU",
    "root_title": itin["root_title"],
    "root_subtitle": itin["root_subtitle"],
    "chapter_count": len(chapter_overview),
    "total_chapter_settlement_trajectories": total_settlements_all,
    "total_hgis_rows": len(hgis_rows),
    "hgis_snapshot_count": len(set(r["snapshot_regime"] for r in hgis_rows)),
    "hgis_hyde_ad_year_count": hgis_meta.get("hyde_ad_year_count", 118),
    "hgis_distinct_boundary_regimes": hgis_meta.get("distinct_boundary_regimes", []),
    "hgis_sources": all_hgis_sources,
    "macro_raster_series": raster_series,
    "chapters": chapter_overview,
    "kriging_diagnostics_summary": {
      "domestic_catchments": kriging_diag.get("domestic_catchments"),
      "active_domestic_catchments": kriging_diag.get("active_domestic_catchments"),
      "adm2_coverage_ratio": kriging_diag.get("adm2_coverage_ratio"),
      "domestic_site_count_unique_sum": kriging_diag.get("domestic_site_count_unique_sum"),
      "arch_regional_share": kriging_diag.get("arch_regional_share"),
      "arch_crowd_share": kriging_diag.get("arch_crowd_share"),
      "median_voronoi_radius_km": kriging_diag.get("median_voronoi_radius_km"),
      "p90_voronoi_radius_km": kriging_diag.get("p90_voronoi_radius_km"),
      "tau1_dimensionless": kriging_diag.get("tau1_dimensionless"),
      "tau2_dimensionless": kriging_diag.get("tau2_dimensionless"),
      "valid_cells": kriging_diag.get("valid_cells"),
      "jurisdiction_arch_coverage": kriging_diag.get("jurisdiction_arch_coverage", {}),
      "source_provenance_breakdown": {
        k: v for k, v in (kriging_diag.get("source_provenance_breakdown") or {}).items()
        if k != "by_source"
      },
      "subadmin_hgis_mass_conservation": kriging_diag.get("subadmin_hgis_mass_conservation", {}),
    },
    "geojson_metadata_summary": {
      "domestic_site_count_unique_sum": geo_meta.get("domestic_site_count_unique_sum"),
      "svea_c14_baseline_unique_sites": geo_meta.get("svea_c14_baseline_unique_sites"),
      "c14_multiplier": geo_meta.get("c14_multiplier"),
      "frontier_preta_catchments": geo_meta.get("frontier_preta_catchments"),
      "documented_site_pixels": geo_meta.get("documented_site_pixels"),
      "period_geojsons": geo_meta.get("period_geojsons", []),
    },
    "subadmin_mass_conservation_audit": mc_audit,
  }

  with open(os.path.join(SHARED, "quipu_root_summary.json"), "w", encoding="utf-8") as fh:
    json.dump(root_summary, fh, indent=2, ensure_ascii=False)
  with open(os.path.join(SHARED, "quipu_chapter_summaries.json"), "w", encoding="utf-8") as fh:
    json.dump(compact_chapters, fh, indent=2, ensure_ascii=False)

  print(f"\n[DONE] Staged 17 chapter caches + quipu_chapter_summaries.json + quipu_root_summary.json ({len(raster_series)} macro epochs; copied {total_assets_copied} template assets).", flush=True)


if __name__ == "__main__":
  main()
