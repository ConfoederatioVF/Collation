"""Gatekeeper C1: Audits Matérn (nu = 3/2) residual kriging diagnostics, WLS biophysical
covariate activity, un-clamped variogram sharpness, and multi-repository archaeological site
completeness (`>= 2,5x` global `c14_cleaned_dedup.csv` baseline guardrail).
"""

import argparse
import csv
import glob
import json
import os
import re
import sys

import numpy as np
from PIL import Image

try:
  import json5
except ImportError:
  json5 = None


def find_svea_root(arg0_start_path):
  """Locates SVEA repository root by walking parent directories."""
  cur = os.path.abspath(arg0_start_path or ".")
  if not os.path.isdir(cur):
    cur = os.path.dirname(cur)
  for _ in range(12):
    if os.path.isdir(os.path.join(cur, "histmap")) and os.path.isdir(os.path.join(cur, ".agents")):
      return cur
    parent = os.path.dirname(cur)
    if parent == cur:
      break
    cur = parent
  return None


def load_domain_mask(arg0_domain_dir, arg1_svea_root):
  """Resolves the 4320x2160 valid land mask boolean array for a kriging domain."""
  cfg_dir = os.path.join(arg0_domain_dir, "config")
  cfg_data = None
  if os.path.isdir(cfg_dir):
    for fn in sorted(os.listdir(cfg_dir)):
      if fn.lower().endswith(".json5"):
        raw = open(os.path.join(cfg_dir, fn), "r", encoding="utf-8").read()
        try:
          cfg_data = json5.loads(raw) if json5 else json.loads(re.sub(r"//.*?$", "", raw, flags=re.MULTILINE))
        except Exception:
          cfg_data = None
        if isinstance(cfg_data, dict):
          break

  if isinstance(cfg_data, dict) and arg1_svea_root:
    k_cfg = cfg_data.get("kriging_config") or {}
    m_rel = k_cfg.get("domain_mask_png")
    if m_rel:
      m_abs = os.path.join(arg1_svea_root, m_rel)
      if os.path.isfile(m_abs):
        arr = np.asarray(Image.open(m_abs).convert("RGBA"), dtype=np.uint8)
        return (arr[:, :, 3] > 0) & ((arr[:, :, :3].sum(axis=2)) > 0), cfg_data

    geo_path = os.path.join(arg1_svea_root, "histmap/1.data_raw/admin_modern/geocodes.png")
    if os.path.isfile(geo_path):
      rgbs = []
      for src_cfg in (k_cfg, cfg_data):
        if not isinstance(src_cfg, dict):
          continue
        for k, v in src_cfg.items():
          if k.endswith("_geocode_rgb") and isinstance(v, list) and len(v) == 3:
            rgbs.append(tuple(v))
          elif k == "geocode_rgbs" and isinstance(v, list):
            for item in v:
              if isinstance(item, list) and len(item) == 3:
                rgbs.append(tuple(item))
      if rgbs:
        geo = np.asarray(Image.open(geo_path).convert("RGBA"), dtype=np.uint8)
        mask = np.zeros(geo.shape[:2], dtype=bool)
        for r, g, b in rgbs:
          mask |= (geo[:, :, 0] == r) & (geo[:, :, 1] == g) & (geo[:, :, 2] == b)
        return mask, cfg_data

  # Generic fallback: union of pixels present in 1.kriged_rasters/*.png
  kdir = os.path.join(arg0_domain_dir, "1.kriged_rasters")
  if os.path.isdir(kdir):
    for fn in sorted(os.listdir(kdir)):
      if fn.lower().endswith(".png"):
        raw = np.asarray(Image.open(os.path.join(kdir, fn)).convert("RGBA"), dtype=np.uint8)
        f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
        return np.isfinite(f32) & (f32 > 0), cfg_data

  return None, cfg_data


def count_c14_in_mask(arg0_svea_root, arg1_mask):
  """Counts unique c14_cleaned_dedup sites inside the domain land mask."""
  if not arg0_svea_root or arg1_mask is None:
    return None
  c14_path = os.path.join(arg0_svea_root, "histmap/1.data_raw/population_c14bazAAR/c14_cleaned_dedup.csv")
  if not os.path.isfile(c14_path):
    return None
  h, w = arg1_mask.shape
  seen = set()
  cnt = 0
  with open(c14_path, "r", encoding="utf-8", errors="replace") as fh:
    for row in csv.DictReader(fh):
      try:
        lat = float(row.get("lat") or 0.0)
        lon = float(row.get("lon") or 0.0)
      except (TypeError, ValueError):
        continue
      site = str(row.get("site") or "").strip().lower()
      key = (round(lat, 3), round(lon, 3), site)
      if key in seen:
        continue
      seen.add(key)
      r_idx = min(h - 1, max(0, int((90.0 - lat) * h / 180.0)))
      c_idx = min(w - 1, max(0, int((lon + 180.0) * w / 360.0)))
      if arg1_mask[r_idx, c_idx]:
        cnt += 1
  return cnt


def resolve_domain_site_count(arg0_domain_dir, arg1_diag_data):
  """Resolves total domestic archaeological site-epoch records in the domain."""
  if isinstance(arg1_diag_data.get("domestic_site_count_unique_sum"), (int, float)) and arg1_diag_data["domestic_site_count_unique_sum"] > 0:
    return int(arg1_diag_data["domestic_site_count_unique_sum"]), 0

  cfg_dir = os.path.join(arg0_domain_dir, "config")
  repo_count = 0
  if os.path.isdir(cfg_dir):
    for fn in sorted(os.listdir(cfg_dir)):
      if fn.endswith("_geojson_metadata.json"):
        meta = json.loads(open(os.path.join(cfg_dir, fn), "r", encoding="utf-8").read())
        if isinstance(meta.get("country_breakdown"), dict):
          tot = sum(int(v or 0) for v in meta["country_breakdown"].values())
          if isinstance(meta.get("sources"), list):
            repo_count = len(meta["sources"])
          return tot, repo_count
        if isinstance(meta.get("period_geojsons"), list):
          tot = sum(int(p.get("total_sites_count") or 0) for p in meta["period_geojsons"] if isinstance(p, dict))
          if tot > 0:
            return tot, max(repo_count, 1)

  all_gj = os.path.join(arg0_domain_dir, "geojson/00_all_periods.geojson")
  if os.path.isfile(all_gj):
    gj = json.loads(open(all_gj, "r", encoding="utf-8").read())
    tot = 0
    for feat in gj.get("features", []):
      props = feat.get("properties") or {}
      if props.get("is_frontier_buffer"):
        continue
      tot += int(props.get("total_sites_all_periods") or props.get("site_count") or 0)
    if tot > 0:
      return tot, repo_count

  return None, repo_count


def audit_diagnostics(arg0_diag_path, arg1_max_tau1=1.8, arg2_max_nugget=0.45, arg3_min_baseline_mult=2.5):
  """Inspects kriging diagnostics JSON for un-clamped sharpness, WLS covariates, and baseline multiplier."""
  errors = []
  warnings = []

  if os.path.isdir(arg0_diag_path):
    cfg_dir = os.path.join(arg0_diag_path, "config")
    candidates = [os.path.join(cfg_dir, "kriging_diagnostics.json")] + sorted(glob.glob(os.path.join(cfg_dir, "*_kriging_metadata.json")))
    found_diag = next((p for p in candidates if os.path.isfile(p)), None)
    if found_diag:
      arg0_diag_path = found_diag

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
  clamped_periods = 0
  has_raw_nugget = False
  wls_active_periods = 0
  valid_cells = int(data.get("valid_cells") or 0)

  for period_key, model in models.items():
    if not isinstance(model, dict):
      continue
    checked += 1

    raw_tau1 = model.get("raw_tau1_dimensionless")
    tau1 = raw_tau1 if raw_tau1 is not None else model.get("tau1_dimensionless", data.get("tau1_dimensionless"))
    if tau1 is None or float(tau1) <= 0.0 or float(tau1) > arg1_max_tau1:
      errors.append(
        f"Period {period_key!r}: un-clamped tau1_dimensionless={tau1} exceeds sharpness threshold ({arg1_max_tau1})."
      )

    raw_ratio = model.get("raw_nugget_to_sill_ratio")
    if raw_ratio is not None:
      has_raw_nugget = True
      ratio = raw_ratio
    else:
      ratio = model.get("nugget_to_sill_ratio")
      if ratio is None:
        c0 = float(model.get("c0_nugget", 0.0))
        sill = float(model.get("total_sill", 0.0))
        ratio = (c0 / sill) if sill > 0.0 else model.get("eta_nugget_ratio")

    if raw_ratio is None and tau1 is not None and ratio is not None:
      if abs(float(tau1) - 1.25) < 1e-3 and abs(float(ratio) - 0.22) < 1e-3:
        clamped_periods += 1

    if ratio is None or float(ratio) >= arg2_max_nugget:
      if period_key == "unspecified" and float(ratio or 0.0) < 0.55:
        warnings.append(f"Period {period_key!r}: nugget-to-sill {ratio} is elevated for undifferentiated sites.")
      else:
        errors.append(
          f"Period {period_key!r}: nugget-to-sill ratio={ratio} indicates noisy/blurry smoothing (>= {arg2_max_nugget})."
        )

    betas = model.get("residual_kriging_wls_betas") or model.get("wls_beta")
    if isinstance(betas, dict):
      bsum = sum(float(v or 0.0) for k, v in betas.items() if k != "kappa_drift")
      if bsum > 0.0:
        wls_active_periods += 1

    p_stat = raster_stats.get(period_key)
    if isinstance(p_stat, dict):
      max_val = float(p_stat.get("max_value", 0.0))
      active = int(p_stat.get("active_cells", 0))
      valid_cells = max(valid_cells, int(p_stat.get("valid_mask_cells", 0)))
      if max_val <= 0.0 or active == 0:
        errors.append(f"Period {period_key!r}: raster stats show flat/zero surface (active={active}, max={max_val}).")

  if checked == 0:
    errors.append("No variogram period entries were evaluated.")
    return errors, warnings, {}

  if not has_raw_nugget and clamped_periods >= max(2, int(0.7 * checked)):
    errors.append(
      f"[SHARPNESS] Clamp-masked diagnostics detected ({clamped_periods}/{checked} periods pinned at tau1=1.25, "
      "nugget=0.22 without `raw_nugget_to_sill_ratio`). Re-run using upgraded ViscountMaternKriging."
    )

  if data.get("wls_covariates_active") is False or (valid_cells >= 500 and wls_active_periods == 0):
    errors.append(
      "[COVARIATES] No active WLS biophysical / de-cliffed rural habitation covariates (`residual_kriging_wls_betas`) reported; "
      "pure unconditioned Voronoi kriging produces blurry blobs."
    )

  domain_dir = os.path.dirname(os.path.dirname(os.path.abspath(arg0_diag_path)))
  svea_root = find_svea_root(domain_dir)
  domain_sites, _ = resolve_domain_site_count(domain_dir, data)
  mask_arr, _cfg = load_domain_mask(domain_dir, svea_root)
  baseline_c14 = count_c14_in_mask(svea_root, mask_arr)

  mult = None
  if domain_sites is not None and baseline_c14 is not None and baseline_c14 >= 50:
    mult = float(domain_sites) / baseline_c14
    if mult < arg3_min_baseline_mult:
      errors.append(
        f"[GUARDRAIL] Archaeological corpus ({domain_sites} records) is only {mult:.2f}x SVEA's global "
        f"c14_cleaned_dedup baseline ({baseline_c14} sites inside mask); must be >= {arg3_min_baseline_mult:.1f}x "
        "by compositing national/state heritage registers, GIS portals, DINAA/CARD/CyberSW, rather than p3k14c alone."
      )

  return errors, warnings, {
    "periods_checked": checked,
    "tau1_global": data.get("raw_tau1_dimensionless", data.get("tau1_dimensionless")),
    "wls_active_periods": wls_active_periods,
    "domain_sites": domain_sites,
    "baseline_c14_sites": baseline_c14,
    "baseline_multiplier": round(mult, 2) if mult is not None else None,
  }


def main():
  parser = argparse.ArgumentParser(description="Audit Operation Viscount Matérn kriging sharpness & corpus depth.")
  parser.add_argument("diagnostics_json", help="Path to kriging_diagnostics.json or oanmap_kriging_metadata.json")
  parser.add_argument("--max-tau1", type=float, default=1.8, help="Maximum allowed un-clamped tau1 (default 1.8)")
  parser.add_argument("--max-nugget", type=float, default=0.45, help="Maximum allowed nugget-to-sill ratio (default 0.45)")
  parser.add_argument("--min-baseline-multiplier", type=float, default=2.5, help="Min domain sites vs c14_cleaned_dedup in mask (default 2.5)")
  parsed = parser.parse_args()

  errors, warnings, summary = audit_diagnostics(
    parsed.diagnostics_json,
    parsed.max_tau1,
    parsed.max_nugget,
    parsed.min_baseline_multiplier,
  )
  for w in warnings:
    print(f"[WARN] {w}")
  for e in errors:
    print(f"[FAIL] {e}", file=sys.stderr)

  print(f"[audit_kriging_sharpness] Summary: {json.dumps(summary)}")
  sys.exit(1 if errors else 0)


if __name__ == "__main__":
  main()
