"""Extracts exact verified benchmark totals, sub-regional shares, top settlements, ledger counts,
kriging diagnostics and valid BibTeX keys across all 13 CASTLE chapters into
CASTLE/_shared/_gis_cache/castle_stage_d_facts.json for Stage D RMarkdown authoring.
"""

import json
import os
import pathlib
import re
import json5

CASTLE_DIR = pathlib.Path(__file__).resolve().parents[2]
DIAG_P = CASTLE_DIR / "_shared/sites_korea_japan/config/kriging_diagnostics.json"
GEO_P = CASTLE_DIR / "_shared/sites_korea_japan/config/sites_korea_japan_geojson_metadata.json"


def main():
  cfg = json5.loads((CASTLE_DIR / "castle_areal_masks.json5").read_text(encoding="utf-8"))
  mods = list(cfg.get("specialist_masks", [])) + list(cfg.get("national_epoch_masks", []))
  diag = json.loads(DIAG_P.read_text(encoding="utf-8"))
  geo = json.loads(GEO_P.read_text(encoding="utf-8"))

  chapters = []
  for m in mods:
    mid = m["id"]
    j5_rel = pathlib.Path(m["json5_path"])
    j5_abs = CASTLE_DIR.parents[3] / j5_rel if j5_rel.parts[0] == "histmap" else CASTLE_DIR / j5_rel
    ch_dir = j5_abs.parent
    data = json5.loads(j5_abs.read_text(encoding="utf-8"))
    setts = json.loads((ch_dir / f"{mid}_settlements.json").read_text(encoding="utf-8"))
    ledger = json5.loads((ch_dir / f"{mid}_source_ledger.json5").read_text(encoding="utf-8"))
    bib_p = ch_dir / f"{mid}_literature_review.bib"
    bib_txt = bib_p.read_text(encoding="utf-8") if bib_p.exists() else ""
    bib_keys = re.findall(r"@\w+\{([^,\s]+),", bib_txt)
    bib_titles = dict(re.findall(r"@\w+\{([^,\s]+),.*?title\s*=\s*\{\{?([^}]+)\}?\}", bib_txt, flags=re.S))

    regs = data.get("regions", {})
    all_yrs = sorted({int(k) for rv in regs.values() for k in (rv.get("population") or {}).keys()})
    totals = {}
    for y in all_yrs:
      totals[str(y)] = round(sum(float((rv.get("population") or {}).get(str(y), 0.0)) for rv in regs.values()))

    reg_summary = []
    for rk, rv in regs.items():
      pm = rv.get("population") or {}
      ys = sorted(int(k) for k in pm.keys())
      pk_y = max(ys, key=lambda y: float(pm[str(y)])) if ys else None
      reg_summary.append({
        "key": rk,
        "name": rv.get("name", rk),
        "area_km2": rv.get("area_km2"),
        "start_pop": pm.get(str(ys[0])) if ys else 0,
        "end_pop": pm.get(str(ys[-1])) if ys else 0,
        "peak_pop": pm.get(str(pk_y)) if pk_y is not None else 0,
        "peak_yr": pk_y,
      })

    ranked_setts = []
    for s in setts.values():
      pm = s.get("population") or {}
      if not pm:
        continue
      pk_y = max(pm.keys(), key=lambda k: float(pm[k]))
      ranked_setts.append({
        "name": s.get("name"),
        "country": s.get("country"),
        "region_id": s.get("region_id"),
        "peak_pop": float(pm[pk_y]),
        "peak_yr": int(pk_y),
        "coords": s.get("coords"),
      })
    ranked_setts.sort(key=lambda x: (-x["peak_pop"], x["name"]))

    chapters.append({
      "id": mid,
      "rel_dir": str(ch_dir.relative_to(CASTLE_DIR)).replace("\\", "/"),
      "domain": data.get("domain"),
      "n_regions": len(regs),
      "n_settlements": len(setts),
      "n_excluded": len(ledger.get("excluded_candidates") or []),
      "n_pdfs": len([f for f in os.listdir(ch_dir / "papers") if f.lower().endswith(".pdf")]) if (ch_dir / "papers").exists() else 0,
      "benchmark_totals": totals,
      "regions": reg_summary,
      "top20_settlements": ranked_setts[:20],
      "bib_keys": bib_keys,
      "bib_titles": {k: bib_titles.get(k, "")[:100] for k in bib_keys},
    })

  out = {
    "kriging_summary": {
      "tau1": diag.get("tau1_dimensionless"),
      "tau2": diag.get("tau2_dimensionless"),
      "valid_cells": diag.get("valid_cells"),
      "horizons": list((diag.get("variogram_models") or {}).keys()),
      "total_raw_records": geo.get("total_raw_records"),
      "domestic_catchments": geo.get("domestic_catchments"),
      "frontier_catchments": geo.get("frontier_catchments"),
    },
    "chapters": chapters,
  }
  out_p = CASTLE_DIR / "_shared/_gis_cache/castle_stage_d_facts.json"
  out_p.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
  print(f"Wrote {out_p} covering {len(chapters)} chapters.")


if __name__ == "__main__":
  main()

