"""Stages per-chapter summary JSON caches (`<stem>_summary_cache.json`) and enriches chapter
BibTeX files with the geoBoundaries subadministrative GIS reference (Runfola et al. 2020) and
exact historical & modern subadministrative enumerations for Stage D non-heuristic RMarkdown authoring.
"""

import json
import os
import pathlib
import re
from collections import defaultdict

import json5
import numpy as np

HB_DIR = pathlib.Path(r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\HANDBOOK")
SUBADMIN_DIR = HB_DIR / "_shared" / "subadmin_censuses"
SITES_DIR = HB_DIR / "_shared" / "sites_handbook_mena"

CHAPTER_ISO3 = {
  "prehistoric_neolithic_mena_iran_afghanistan": ["EGY", "IRQ", "SYR", "TUR", "IRN", "AFG", "MAR", "DZA", "TUN", "LBY", "JOR", "ISR", "PSE", "LBN", "SAU", "YEM", "OMN"],
  "ancient_mesopotamia": ["IRQ", "SYR"],
  "pharaonic_egypt": ["EGY"],
  "ancient_anatolia_levant_arabia": ["TUR", "CYP", "SYR", "LBN", "JOR", "ISR", "PSE", "SAU", "YEM", "OMN", "ARE", "QAT", "BHR", "KWT"],
  "ancient_iran_afghanistan_transcaucasia": ["IRN", "AFG", "TUR", "ARM", "GEO", "AZE"],
  "hellenistic_roman_parthian_sassanid": ["EGY", "MAR", "DZA", "TUN", "LBY", "TUR", "SYR", "LBN", "JOR", "ISR", "PSE", "CYP", "IRQ", "IRN", "AFG", "GEO", "ARM", "AZE", "YEM"],
  "early_islamic_caliphate": ["IRQ", "SYR", "EGY", "IRN", "AFG", "TUR", "MAR", "DZA", "TUN", "LBY", "SAU", "YEM", "OMN", "JOR", "ISR", "PSE", "LBN", "ARM", "AZE", "GEO"],
  "mediaeval_near_east_iran_caucasia": ["TUR", "CYP", "SYR", "LBN", "JOR", "ISR", "PSE", "IRQ", "IRN", "AFG", "GEO", "ARM", "AZE", "SAU", "YEM", "OMN"],
  "mediaeval_north_africa": ["EGY", "MAR", "DZA", "TUN", "LBY", "ESH"],
  "ottoman_empire_mena": ["TUR", "CYP", "SYR", "LBN", "JOR", "ISR", "PSE", "IRQ", "EGY", "DZA", "TUN", "LBY", "SAU", "YEM", "KWT", "QAT", "BHR"],
  "safavid_afsharid_qajar_iran": ["IRN"],
  "durrani_barakzai_afghanistan": ["AFG"],
  "russian_transcaucasia": ["GEO", "ARM", "AZE"],
  "colonial_north_africa": ["MAR", "DZA", "TUN", "LBY", "ESH"],
  "khedivate_british_egypt": ["EGY"],
  "mandates_levant_iraq_cyprus": ["SYR", "LBN", "JOR", "ISR", "PSE", "IRQ", "CYP"],
  "arabian_peninsula_state_formation": ["SAU", "YEM", "OMN", "ARE", "QAT", "BHR", "KWT"],
  "republic_of_turkey": ["TUR"],
  "modern_iran": ["IRN"],
  "modern_afghanistan": ["AFG"],
  "soviet_postsoviet_transcaucasia": ["GEO", "ARM", "AZE"],
  "modern_levant_israel_palestine": ["SYR", "LBN", "JOR", "ISR", "PSE"],
  "modern_iraq": ["IRQ"],
  "modern_egypt": ["EGY"],
  "modern_maghreb_libya": ["MAR", "DZA", "TUN", "LBY", "ESH"],
  "modern_cyprus": ["CYP"],
  "modern_arabian_peninsula": ["SAU", "YEM", "OMN", "ARE", "QAT", "BHR", "KWT"],
}

GEOBOUNDARIES_BIB = """
@article{Runfola2020GeoBoundaries,
  author = {Daniel Runfola and Austin Anderson and Heather Baier and Matt Crittenden and Elizabeth Dowker and Sydney Fuhrig and Seth Goodman and Grace Grimsley and Rachel Layko and Graham Melville and Maddy Mulder and Rachel Oberman and Joshua Panganiban and Andrew Peck and Leigh Seitz and Sylvia Shea and Hannah Slevin and Rebecca Youngerman and Lauren Hobbs},
  title = {geoBoundaries: A global database of political administrative boundaries},
  journal = {PLOS ONE},
  year = {2020},
  doi = {10.1371/journal.pone.0231866},
  url = {https://doi.org/10.1371/journal.pone.0231866}
}
"""

SUPPLEMENTAL_BOSWORTH_BIB = """
@book{Bosworth2007Historic,
  author = {Clifford Edmund Bosworth},
  title = {Historic Cities of the Islamic World},
  publisher = {Brill},
  year = {2007},
  doi = {10.1163/ej.9789004153882.i-616},
  url = {https://doi.org/10.1163/ej.9789004153882.i-616}
}
"""


def parse_bib_keys(bib_path):
  txt = bib_path.read_text(encoding="utf-8")
  entries = []
  for m in re.finditer(r"@\w+\{([^,\s]+),(.*?)\n\}", txt, flags=re.S):
    key = m.group(1).strip()
    body = m.group(2)
    def getf(f):
      fm = re.search(rf"{f}\s*=\s*\{{([^}}]*)\}}", body, flags=re.I)
      return fm.group(1).strip() if fm else ""
    entries.append({
      "key": key,
      "author": getf("author")[:60],
      "year": getf("year"),
      "title": getf("title")[:100],
      "journal": getf("journal") or getf("publisher"),
    })
  return entries


def main():
  itinerary = json5.loads((HB_DIR / "handbook_itinerary.json5").read_text(encoding="utf-8"))
  sub_summary = json.loads((SUBADMIN_DIR / "subadmin_enumerations_summary.json").read_text(encoding="utf-8"))
  hist_meta = json.loads((SUBADMIN_DIR / "rasters" / "subadmin_meta_historical.json").read_text(encoding="utf-8"))["units"]
  mod_meta = json.loads((SUBADMIN_DIR / "rasters" / "subadmin_meta_modern.json").read_text(encoding="utf-8"))["units"]
  sub_audit = json.loads((SITES_DIR / "config" / "subadmin_mass_conservation_audit.json").read_text(encoding="utf-8"))
  krig_diag = json.loads((SITES_DIR / "config" / "kriging_diagnostics.json").read_text(encoding="utf-8"))
  geo_meta = json.loads((SITES_DIR / "config" / "sites_handbook_mena_geojson_metadata.json").read_text(encoding="utf-8"))

  hist_by_iso = defaultdict(list)
  for u in hist_meta.values():
    hist_by_iso[u["iso3"]].append(u)
  mod_by_iso = defaultdict(list)
  for u in mod_meta.values():
    mod_by_iso[u["iso3"]].append(u)

  root_chapters_summary = []

  for ch in itinerary["chapters"]:
    stem = ch["stem"]
    ch_dir = HB_DIR / ch["group"] / ch["folder"]
    j5 = json5.loads((ch_dir / f"{stem}.json5").read_text(encoding="utf-8"))
    setts = json.loads((ch_dir / f"{stem}_settlements.json").read_text(encoding="utf-8"))
    ledger = json5.loads((ch_dir / f"{stem}_source_ledger.json5").read_text(encoding="utf-8"))
    bib_p = ch_dir / f"{stem}_literature_review.bib"

    # Ensure geoBoundaries (and Bosworth 2007 supplemental for Islamic/Early Modern chapters) appear in .bib
    bib_txt = bib_p.read_text(encoding="utf-8")
    if "Runfola2020GeoBoundaries" not in bib_txt:
      bib_txt = bib_txt.rstrip() + "\n" + GEOBOUNDARIES_BIB
    if ch["index"] in (7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17) and "Bosworth2007Historic" not in bib_txt:
      bib_txt = bib_txt.rstrip() + "\n" + SUPPLEMENTAL_BOSWORTH_BIB
    bib_p.write_text(bib_txt, encoding="utf-8")
    bib_entries = parse_bib_keys(bib_p)

    # Headline series & region breakdown
    regions = j5.get("regions") or {}
    all_yrs = sorted({int(y) for rv in regions.values() for y in (rv.get("population") or {}).keys()})
    headline = {str(y): round(sum(float((rv.get("population") or {}).get(str(y), 0)) for rv in regions.values()), 1) for y in all_yrs}
    tot_area = round(sum(float(rv.get("area_km2") or 0) for rv in regions.values()), 1)
    tot_px = sum(int(rv.get("pixel_count") or 0) for rv in regions.values())

    reg_rows = []
    for rid, rv in regions.items():
      pm = rv.get("population") or {}
      reg_rows.append({
        "id": rid,
        "name": rv.get("name", rid),
        "area_km2": round(float(rv.get("area_km2") or 0), 1),
        "start_pop": round(float(pm.get(str(all_yrs[0]), 0)), 1) if all_yrs else 0,
        "end_pop": round(float(pm.get(str(all_yrs[-1]), 0)), 1) if all_yrs else 0,
        "population": pm,
      })
    reg_rows.sort(key=lambda r: -r["end_pop"])

    # Settlement stats & top 45
    peaks = []
    for sk, s in setts.items():
      pm = s.get("population") or {}
      if not pm:
        continue
      pky = max(pm.keys(), key=lambda y: float(pm[y]))
      peaks.append({
        "key": sk, "name": s["name"], "country": s["country"],
        "coords": s["coords"], "peak_year": int(pky), "peak_pop": int(pm[pky]),
        "min_year": min(int(y) for y in pm), "max_year": max(int(y) for y in pm),
        "foundation_year": s.get("foundation_year"),
      })
    peaks.sort(key=lambda x: -x["peak_pop"])

    # Zipf slope
    zipf_alpha, zipf_r2 = None, None
    if len(peaks) >= 25:
      lx = np.log10(np.arange(1, len(peaks) + 1, dtype=float))
      ly = np.log10(np.array([p["peak_pop"] for p in peaks], dtype=float))
      sl, ic = np.polyfit(lx, ly, 1)
      zipf_alpha = round(float(-sl), 3)
      zipf_r2 = round(float(1.0 - np.sum((ly - (ic + sl * lx)) ** 2) / max(1e-12, np.sum((ly - np.mean(ly)) ** 2))), 3)

    # Historical & Modern Subadministrative Enumerations relevant to this chapter's countries!
    isos = CHAPTER_ISO3.get(stem, [])
    ch_hist_sub = []
    ch_mod_sub_stats = {}
    ch_mod_top_units = []
    for iso in isos:
      for hu in hist_by_iso.get(iso, []):
        ch_hist_sub.append({"iso3": iso, "name": hu["name"], "source": hu["source"], "pops": hu["pops"]})
      if iso in sub_summary.get("country_match_stats", {}):
        ch_mod_sub_stats[iso] = sub_summary["country_match_stats"][iso]
      m_list = sorted(mod_by_iso.get(iso, []), key=lambda u: -max((float(v) for v in u["pops"].values()), default=0))
      for mu in m_list[:6]:
        ch_mod_top_units.append({"iso3": iso, "name": mu["name"], "level": mu["level"], "area_km2": mu.get("area_km2"), "pops": mu["pops"]})
    ch_mod_top_units.sort(key=lambda u: -max((float(v) for v in u["pops"].values()), default=0))

    cands = ledger.get("candidates") or []
    n_inc = sum(1 for c in cands if c.get("status") == "included")
    n_exc = sum(1 for c in cands if c.get("status") == "excluded")

    cache = {
      "index": ch["index"],
      "stem": stem,
      "group": ch["group"],
      "folder": ch["folder"],
      "itinerary_title": ch["itinerary_title"],
      "full_scope": ch["full_scope"],
      "domain": ch["domain"],
      "regime": ch["regime"],
      "total_area_km2": tot_area,
      "total_pixels": tot_px,
      "subregion_count": len(reg_rows),
      "headline_series": headline,
      "top_subregions": reg_rows[:18],
      "settlement_count": len(peaks),
      "ledger_included": n_inc,
      "ledger_excluded": n_exc,
      "zipf_alpha": zipf_alpha,
      "zipf_r2": zipf_r2,
      "top_settlements": peaks[:30],
      "subadmin_mass_audit": {
        "historical_units_domain": sub_audit["historical_subadmin_units_rasterised"],
        "modern_units_domain": sub_audit["modern_subadmin_units_rasterised"],
        "unit_year_checks": sub_audit["total_unit_year_checks"],
        "max_unit_rel_err": sub_audit["global_max_unit_rel_err"],
      },
      "chapter_historical_subadmin": ch_hist_sub[:20],
      "chapter_modern_subadmin_stats": ch_mod_sub_stats,
      "chapter_modern_top_units": ch_mod_top_units[:18],
      "bib_keys": bib_entries,
    }
    (ch_dir / f"{stem}_summary_cache.json").write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    root_chapters_summary.append({
      "index": ch["index"], "stem": stem, "title": ch["itinerary_title"], "domain": ch["domain"],
      "area_km2": tot_area, "subregions": len(reg_rows), "settlements": len(peaks),
      "start_pop": headline[str(all_yrs[0])] if all_yrs else 0,
      "end_pop": headline[str(all_yrs[-1])] if all_yrs else 0,
    })

  root_cache = {
    "project": "HANDBOOK",
    "total_chapters": len(root_chapters_summary),
    "total_settlement_records": sum(c["settlements"] for c in root_chapters_summary),
    "domestic_catchments": krig_diag["domestic_catchments"],
    "domestic_sites": round(krig_diag["domestic_site_count_unique_sum"]),
    "tau1_dimensionless": krig_diag["tau1_dimensionless"],
    "raw_tau1_dimensionless": krig_diag["raw_tau1_dimensionless"],
    "valid_cells": krig_diag["valid_cells"],
    "subadmin_audit": sub_audit,
    "period_geojsons": geo_meta.get("period_geojsons", []),
    "chapters": root_chapters_summary,
  }
  (HB_DIR / "_shared" / "handbook_root_summary.json").write_text(json.dumps(root_cache, indent=2, ensure_ascii=False), encoding="utf-8")
  print(f"DONE staged 27 chapter caches + root summary cache + geoBoundaries BibTeX enrichment.", flush=True)


if __name__ == "__main__":
  main()
