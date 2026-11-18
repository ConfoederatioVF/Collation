# -*- coding: utf-8 -*-
"""Export authoritative post-Stage-B/C/E metrics for all 31 CENTAUR modules for Stage D prose sync."""

import json
import pathlib
import json5

SVEA_ROOT = pathlib.Path(__file__).resolve().parents[1]
CENTAUR_DIR = SVEA_ROOT / "histmap/1.data_raw/population_regional/CENTAUR"


def main ():
  cfg = json5.loads((CENTAUR_DIR / "centaur_areal_masks.json5").read_text(encoding="utf-8"))
  mods = list(cfg.get("specialist_masks", [])) + list(cfg.get("national_epoch_masks", []))
  kd_na = json.loads((CENTAUR_DIR / "_shared/sites_northern_america/config/kriging_diagnostics.json").read_text(encoding="utf-8"))
  kd_hi = json.loads((CENTAUR_DIR / "_shared/sites_hawaii_polynesia/config/kriging_diagnostics.json").read_text(encoding="utf-8"))

  chapters = {}
  total_setts = 0
  total_cand = 0
  total_excl = 0

  for m in mods:
    mid = m["id"]
    j5_rel = pathlib.Path(m["json5_path"])
    j5_p = SVEA_ROOT / j5_rel if j5_rel.parts[0] == "histmap" else CENTAUR_DIR / j5_rel
    ch_dir = j5_p.parent
    d = json5.loads(j5_p.read_text(encoding="utf-8"))
    s_p = ch_dir / f"{mid}_settlements.json"
    l_p = ch_dir / f"{mid}_source_ledger.json5"
    setts = json.loads(s_p.read_text(encoding="utf-8"))
    led = json5.loads(l_p.read_text(encoding="utf-8"))
    items = setts.values() if isinstance(setts, dict) else setts
    n_s = len(setts)
    cands = led.get("candidates", [])
    n_ex = sum(1 for c in cands if c.get("status") == "excluded")
    n_in = sum(1 for c in cands if c.get("status") == "included")
    total_setts += n_s
    total_cand += len(cands)
    total_excl += n_ex

    ranked_s = []
    for s in items:
      pk = max((float(v) for v in (s.get("population") or {}).values()), default=0.0)
      ranked_s.append((pk, str(s.get("name", ""))))
    ranked_s.sort(key=lambda t: (-t[0], t[1]))

    hl = d.get("summary", {}).get("headline_population_by_benchmark", {})
    ys = sorted(int(k) for k in hl.keys())
    chapters[mid] = {
      "rel_dir": str(ch_dir.relative_to(CENTAUR_DIR)).replace("\\", "/"),
      "settlements_count": n_s,
      "ledger_candidates": len(cands),
      "ledger_included": n_in,
      "ledger_excluded": n_ex,
      "regions_count": len(d.get("regions", {})),
      "headline_start": [ys[0], hl[str(ys[0])]] if ys else None,
      "headline_end": [ys[-1], hl[str(ys[-1])]] if ys else None,
      "headline_peak": max(([float(hl[str(y)]), y] for y in ys), default=[0, 0]),
      "top5_settlements": [{"name": nm, "peak": pk} for pk, nm in ranked_s[:5]]
    }

  out = {
    "totals": {
      "modules": len(mods),
      "settlements_included": total_setts,
      "ledger_candidates": total_cand,
      "ledger_excluded": total_excl
    },
    "kriging_na": {
      "domestic_catchments": kd_na.get("n_catchments_domestic") or kd_na.get("domestic_catchments"),
      "buffer_catchments": kd_na.get("n_catchments_frontier_buffer"),
      "unique_site_periods": kd_na.get("total_site_periods") or kd_na.get("unique_site_periods"),
      "baseline_multiplier": kd_na.get("baseline_multiplier"),
      "tau1_mean": kd_na.get("tau1_mean") or (sum(v["tau1_dimensionless"] for v in kd_na["variogram_models"].values()) / len(kd_na["variogram_models"])),
      "tau2_mean": kd_na.get("tau2_mean") or (sum(v["tau2_dimensionless"] for v in kd_na["variogram_models"].values()) / len(kd_na["variogram_models"]))
    },
    "kriging_hi": {
      "domestic_catchments": kd_hi.get("n_catchments_domestic") or kd_hi.get("domestic_catchments"),
      "tau1_mean": sum(v["tau1_dimensionless"] for v in kd_hi["variogram_models"].values()) / len(kd_hi["variogram_models"]),
      "tau2_mean": sum(v["tau2_dimensionless"] for v in kd_hi["variogram_models"].values()) / len(kd_hi["variogram_models"])
    },
    "chapters": chapters
  }
  out_p = SVEA_ROOT / "tests/centaur_stage_d_facts.json"
  out_p.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
  print("Wrote", out_p, "totals=", out["totals"])


if __name__ == "__main__":
  main()
