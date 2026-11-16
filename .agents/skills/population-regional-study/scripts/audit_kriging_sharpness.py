"""Gatekeeper C: Audits Matérn (nu = 3/2) residual kriging diagnostics and GeoPNG rasters
to prevent blurry/over-smoothed surfaces (`tau1 > 1,8` or `nugget_to_sill >= 0,45`).
Supports both `ViscountMaternKriging` (`kriging_diagnostics.json`) and legacy POLARIS
(`oanmap_kriging_metadata.json`) schemas.
"""

import argparse
import json
import os
import sys


def audit_diagnostics(arg0_diag_path, arg1_max_tau1=1.8, arg2_max_nugget=0.45):
  """Inspects kriging diagnostics JSON for sharpness and non-degenerate covariates."""
  errors = []
  warnings = []

  if not os.path.isfile(arg0_diag_path):
    errors.append(f"Diagnostics JSON not found: {arg0_diag_path}")
    return errors, warnings, {}

  with open(arg0_diag_path, "r", encoding="utf-8") as fh:
    data = json.load(fh)

  models = data.get("variogram_models") or data.get("variogram_parameters")
  if not isinstance(models, dict) or len(models) == 0:
    errors.append("Diagnostics JSON missing `variogram_models` / `variogram_parameters` mapping.")
    return errors, warnings, {}

  checked = 0
  raster_stats = data.get("kriged_raster_stats", {})

  for period_key, model in models.items():
    if not isinstance(model, dict):
      continue
    checked += 1

    tau1 = model.get("tau1_dimensionless", data.get("tau1_dimensionless"))
    if tau1 is None or float(tau1) <= 0.0 or float(tau1) > arg1_max_tau1:
      errors.append(
        f"Period {period_key!r}: tau1_dimensionless={tau1} exceeds sharpness threshold ({arg1_max_tau1})."
      )

    ratio = model.get("nugget_to_sill_ratio")
    if ratio is None:
      c0 = float(model.get("c0_nugget", 0.0))
      sill = float(model.get("total_sill", 0.0))
      ratio = (c0 / sill) if sill > 0.0 else model.get("eta_nugget_ratio")

    if ratio is None or float(ratio) >= arg2_max_nugget:
      if period_key == "unspecified" and float(ratio or 0.0) < 0.55:
        warnings.append(f"Period {period_key!r}: nugget-to-sill {ratio} is elevated but tolerated for undifferentiated sites.")
      else:
        errors.append(
          f"Period {period_key!r}: nugget-to-sill ratio={ratio} indicates noisy/blurry smoothing (>= {arg2_max_nugget})."
        )

    p_stat = raster_stats.get(period_key)
    if isinstance(p_stat, dict):
      max_val = float(p_stat.get("max_value", 0.0))
      active = int(p_stat.get("active_cells", 0))
      if max_val <= 0.0 or active == 0:
        errors.append(f"Period {period_key!r}: raster stats show flat/zero surface (active={active}, max={max_val}).")

  if checked == 0:
    errors.append("No variogram period entries were evaluated.")

  return errors, warnings, {"periods_checked": checked, "tau1_global": data.get("tau1_dimensionless")}


def main():
  parser = argparse.ArgumentParser(description="Audit Operation Viscount Matérn kriging sharpness diagnostics.")
  parser.add_argument("diagnostics_json", help="Path to kriging_diagnostics.json or oanmap_kriging_metadata.json")
  parser.add_argument("--max-tau1", type=float, default=1.8, help="Maximum allowed dimensionless tau1 (default 1.8)")
  parser.add_argument("--max-nugget", type=float, default=0.45, help="Maximum allowed nugget-to-sill ratio (default 0.45)")
  parsed = parser.parse_args()

  errors, warnings, summary = audit_diagnostics(parsed.diagnostics_json, parsed.max_tau1, parsed.max_nugget)
  for w in warnings:
    print(f"[WARN] {w}")
  for e in errors:
    print(f"[FAIL] {e}", file=sys.stderr)

  print(f"[audit_kriging_sharpness] Summary: {json.dumps(summary)}")
  sys.exit(1 if errors else 0)


if __name__ == "__main__":
  main()
