"""Gatekeeper C1: Audits Matérn (nu = 3/2) residual kriging diagnostics, WLS biophysical
covariate activity, dasymetric habitability suppression, un-clamped variogram
sharpness, and multi-repository archaeological site completeness (`>= 2,5x` global
`c14_cleaned_dedup.csv` baseline guardrail).
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
from scipy.ndimage import distance_transform_edt

try:
  import json5
except ImportError:
  json5 = None


def decode_float32_raster(arg0_png_path):
  """Decodes a big-endian float32 RGBA GeoPNG into positive finite values and a valid mask."""
  raw = np.asarray(Image.open(arg0_png_path).convert("RGBA"), dtype=np.uint8)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
  valid = np.isfinite(f32) & (f32 > 0.0)
  return np.where(valid, f32, 0.0), valid


def decode_uint32_raster(arg0_png_path):
  """Decodes a big-endian uint32 RGBA GeoPNG (e.g. `land_area.png`) into a float64 array."""
  raw = np.asarray(Image.open(arg0_png_path).convert("RGBA"), dtype=np.uint8)
  return raw.reshape(-1, 4).copy().view(">u4").reshape(raw.shape[:2]).astype(np.float64)


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


def audit_dasymetric_habitability(arg0_domain_dir, arg1_svea_root, arg2_mask, arg3_errors, arg4_warnings):
  """Audits dasymetric habitability enforcement against uninhabitable desert/arctic/alpine cells and HYDE carrying capacity."""
  if not arg1_svea_root:
    return {}

  land_area_path = os.path.join(arg1_svea_root, "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png")
  hyde_dir = os.path.join(arg1_svea_root, "histmap/2.data_cleaning/landuse_HYDE/rasters")
  p15_path = os.path.join(hyde_dir, "popc_1500AD.png")
  p10_path = os.path.join(hyde_dir, "popc_1000AD.png")
  p19_path = os.path.join(hyde_dir, "popc_1900AD.png")
  k_dir = os.path.join(arg0_domain_dir, "1.kriged_rasters")
  gj_files = sorted(glob.glob(os.path.join(arg0_domain_dir, "geojson", "*.geojson")))
  k_files = sorted(glob.glob(os.path.join(k_dir, "*.png"))) if os.path.isdir(k_dir) else []

  if not os.path.isfile(land_area_path) or not os.path.isfile(p15_path) or not k_files:
    return {}

  la = decode_uint32_raster(land_area_path)
  p15, _ = decode_float32_raster(p15_path)
  p10 = decode_float32_raster(p10_path)[0] if os.path.isfile(p10_path) else np.zeros_like(p15)
  p19 = decode_float32_raster(p19_path)[0] if os.path.isfile(p19_path) else np.zeros_like(p15)
  hyde_dens = np.maximum.reduce([p15, p10, 0.15 * p19]) / np.maximum(1.0, la)

  site_grid = np.zeros(la.shape, dtype=bool)
  h, w = la.shape
  site_count = 0
  for gj_path in gj_files:
    try:
      gj = json.loads(open(gj_path, "r", encoding="utf-8", errors="replace").read())
    except Exception:
      continue
    for feat in gj.get("features", []):
      geom = feat.get("geometry") or {}
      if geom.get("type") != "Point":
        continue
      coords = geom.get("coordinates") or []
      if len(coords) < 2:
        continue
      try:
        lon, lat = float(coords[0]), float(coords[1])
      except (TypeError, ValueError):
        continue
      r_idx = min(h - 1, max(0, int((90.0 - lat) * h / 180.0)))
      c_idx = min(w - 1, max(0, int((lon + 180.0) * w / 360.0)))
      site_grid[r_idx, c_idx] = True
      site_count += 1

  if site_count == 0:
    return {}

  dist_site = distance_transform_edt(~site_grid)
  hab = (dist_site <= 6.0) | (hyde_dens >= 0.002)

  rep_idxs = []
  for idx in (0, len(k_files) // 2, len(k_files) - 1):
    if idx not in rep_idxs:
      rep_idxs.append(idx)
  rep_files = [k_files[idx] for idx in rep_idxs]

  max_leak = 0.0
  max_mass = 0.0
  min_corr_hab = 1.0
  worst_leak_name = None
  worst_corr_name = None
  total_msk = 0
  total_unhab = 0

  for k_path in rep_files:
    kf, k_valid = decode_float32_raster(k_path)
    msk = (arg2_mask if arg2_mask is not None else k_valid) & (la > 0.0)
    total_msk = max(total_msk, int(msk.sum()))
    if total_msk < 200:
      continue
    unhab = msk & (~hab)
    n_unhab = int(unhab.sum())
    total_unhab = max(total_unhab, n_unhab)

    pos_vals = kf[msk & (kf > 0.0)]
    med_pos = float(np.median(pos_vals)) if pos_vals.size > 0 else 0.0
    if n_unhab > 0 and med_pos > 0.0:
      leak = float(np.mean(kf[unhab] > 0.05 * med_pos))
      tot_mass = float(kf[msk].sum())
      mass_share = float(kf[unhab].sum() / tot_mass) if tot_mass > 0.0 else 0.0
      if leak > max_leak:
        max_leak = leak
        worst_leak_name = os.path.basename(k_path)
      if mass_share > max_mass:
        max_mass = mass_share

    hab_m = msk & hab
    if int(hab_m.sum()) >= 500:
      x_vals = np.log10(1e-6 + kf[hab_m])
      y_vals = np.log10(1e-4 + hyde_dens[hab_m])
      if float(np.std(x_vals)) > 1e-8 and float(np.std(y_vals)) > 1e-8:
        corr_hab = float(np.corrcoef(x_vals, y_vals)[0, 1])
        if corr_hab < min_corr_hab:
          min_corr_hab = corr_hab
          worst_corr_name = os.path.basename(k_path)

  if total_unhab >= 200 and (max_leak > 0.03 or max_mass > 0.015):
    arg3_errors.append(
      f"[HABITABILITY] Uninhabitable wasteland leakage detected in `{worst_leak_name or 'kriged_raster'}` "
      f"(unhab_leak_ratio={max_leak:.4f} > 0,03 or unhab_mass_share={max_mass:.4f} > 0,015 across {total_unhab} uninhabitable pixels). "
      "Ensure `computeDeCliffedHabitationField` and `computeResidualKrigingWeights` do not bypass HYDE/settlement habitability masking."
    )

  if total_msk >= 25000 and total_unhab >= 1000 and min_corr_hab < 0.25:
    arg3_errors.append(
      f"[DASYMETRIC_WEIGHTING] Weak carrying-capacity weighting in `{worst_corr_name or 'kriged_raster'}` "
      f"(log_corr_hyde={min_corr_hab:.3f} < 0,25 on continental domain). Use macro-scale carrying capacity and settlement-hierarchy weights."
    )

  max_urb_med_ratio = None
  max_urb_p95_ratio = None
  worst_med_name = None
  worst_p95_name = None
  uopp_path = os.path.join(hyde_dir, "uopp_2023AD.png")
  if os.path.isfile(uopp_path):
    uopp_grid, _ = decode_float32_raster(uopp_path)
    base_msk = (arg2_mask if arg2_mask is not None else decode_float32_raster(k_files[0])[1]) & (la > 0.0)
    dist_uopp = distance_transform_edt(~(uopp_grid > 10.0))
    urb_core = base_msk & (uopp_grid > 10.0)
    urb_ring = base_msk & hab & (dist_uopp > 2.0) & (dist_uopp <= 5.5)
    if int(urb_core.sum()) >= 30 and int(urb_ring.sum()) >= 60:
      pop_dir = os.path.join(arg0_domain_dir, "2.population_rasters")
      pre_ind_cands = [
        os.path.join(pop_dir, name) for name in ("popc_0.png", "popc_1000.png", "popc_1500.png")
        if os.path.isfile(os.path.join(pop_dir, name))
      ]
      if not pre_ind_cands:
        pre_ind_cands = [k_files[0]]
      for cand_path in pre_ind_cands:
        arr, _ = decode_float32_raster(cand_path)
        pos = arr > 0.0
        c_vals = arr[urb_core & pos]
        r_vals = arr[urb_ring & pos]
        if c_vals.size < 15 or r_vals.size < 30:
          continue
        r_med = float(np.median(r_vals))
        if r_med <= 0.0:
          continue
        med_ratio = float(np.median(c_vals) / r_med)
        if max_urb_med_ratio is None or med_ratio > max_urb_med_ratio:
          max_urb_med_ratio = med_ratio
          worst_med_name = os.path.basename(cand_path)

      prehist_cands = [k_files[0]] + [
        os.path.join(pop_dir, name) for name in ("popc_-5000.png", "popc_-2000.png")
        if os.path.isfile(os.path.join(pop_dir, name))
      ]
      for cand_path in prehist_cands:
        arr, _ = decode_float32_raster(cand_path)
        pos = arr > 0.0
        c_vals = arr[urb_core & pos]
        r_vals = arr[urb_ring & pos]
        if c_vals.size < 15 or r_vals.size < 30:
          continue
        r_p95 = float(np.percentile(r_vals, 95))
        if r_p95 <= 0.0:
          continue
        p95_ratio = float(np.percentile(c_vals, 95) / r_p95)
        if max_urb_p95_ratio is None or p95_ratio > max_urb_p95_ratio:
          max_urb_p95_ratio = p95_ratio
          worst_p95_name = os.path.basename(cand_path)

      if (max_urb_med_ratio is not None and max_urb_med_ratio > 1.60) or (
        max_urb_p95_ratio is not None and max_urb_p95_ratio > 1.65
      ):
        offending = worst_p95_name if (max_urb_p95_ratio is not None and max_urb_p95_ratio > 1.65) else worst_med_name
        med_str = f"{max_urb_med_ratio:.3f}" if max_urb_med_ratio is not None else "n/a"
        p95_str = f"{max_urb_p95_ratio:.3f}" if max_urb_p95_ratio is not None else "n/a"
        arg3_errors.append(
          f"[URBAN_BACKPROJECTION] Modern urban sprawl backprojection detected in `{offending}` "
          f"(urban_core_med_ratio={med_str} vs <= 1,60; prehistoric urban_backproj_p95_ratio={p95_str} vs <= 1,65). "
          "Apply ViscountUrbanMask extended HYDE urban buffer + urbc + 8x spike IDW inpainting."
        )

  return {
    "unhab_leak_ratio": round(max_leak, 4),
    "unhab_mass_share": round(max_mass, 4),
    "log_corr_hyde": round(min_corr_hab, 4),
    "urban_core_med_ratio": round(max_urb_med_ratio, 3) if max_urb_med_ratio is not None else None,
    "urban_backproj_p95_ratio": round(max_urb_p95_ratio, 3) if max_urb_p95_ratio is not None else None,
  }


def audit_diagnostics(arg0_diag_path, arg1_max_tau1=1.8, arg2_max_nugget=0.45, arg3_min_baseline_mult=2.5):
  """Inspects kriging diagnostics JSON for un-clamped sharpness, WLS covariates, habitability weighting, and baseline multiplier."""
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
  top_wls_betas = data.get("residual_kriging_wls_betas") if isinstance(data.get("residual_kriging_wls_betas"), dict) else {}
  wls_active_periods = 0
  zero_hab_periods = 0
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

    betas = model.get("residual_kriging_wls_betas") or model.get("wls_beta") or top_wls_betas.get(period_key)
    if isinstance(betas, dict):
      bsum = sum(float(v or 0.0) for k, v in betas.items() if k != "kappa_drift")
      if bsum > 0.0:
        wls_active_periods += 1
      if "beta_0_hab" in betas and float(betas.get("beta_0_hab") or 0.0) <= 0.0:
        zero_hab_periods += 1

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

  if zero_hab_periods >= max(1, int(0.5 * checked)):
    errors.append(
      f"[HABITABILITY] Zero habitability weight (`beta_0_hab <= 0`) across {zero_hab_periods}/{checked} periods; "
      "unconstrained background kriging illuminates uninhabitable tundra/desert/alpine terrain."
    )

  if data.get("urban_mask_applied") is False or (
    "urban_mask_buffer_radius" in data and float(data.get("urban_mask_buffer_radius") or 0.0) <= 0.0
  ):
    errors.append(
      "[URBAN_BACKPROJECTION] Extended HYDE urban buffer mask disabled (`urban_mask_applied=false` or `urban_mask_buffer_radius <= 0`); "
      "enable ViscountUrbanMask across all historical periods."
    )

  adm2_cov = data.get("adm2_coverage_ratio")
  dom_catch = int(data.get("domestic_catchments") or 0)
  if adm2_cov is not None and dom_catch >= 200 and float(adm2_cov) < 0.65:
    warnings.append(
      f"[COVERAGE] Low ADM2 catchment coverage ratio ({float(adm2_cov):.4f} < 0,65 across {dom_catch} catchments) "
      "risks unweighted county polka-dot artefacts without B2 macro-tile zero imputation."
    )

  domain_dir = os.path.dirname(os.path.dirname(os.path.abspath(arg0_diag_path)))
  svea_root = find_svea_root(domain_dir)
  domain_sites, _ = resolve_domain_site_count(domain_dir, data)
  mask_arr, _cfg = load_domain_mask(domain_dir, svea_root)
  baseline_c14 = count_c14_in_mask(svea_root, mask_arr)
  hab_stats = audit_dasymetric_habitability(domain_dir, svea_root, mask_arr, errors, warnings)

  mult = None
  if domain_sites is not None and baseline_c14 is not None and baseline_c14 >= 50:
    mult = float(domain_sites) / baseline_c14
    if mult < arg3_min_baseline_mult:
      errors.append(
        f"[GUARDRAIL] Archaeological corpus ({domain_sites} records) is only {mult:.2f}x SVEA's global "
        f"c14_cleaned_dedup baseline ({baseline_c14} sites inside mask); must be >= {arg3_min_baseline_mult:.1f}x "
        "by compositing national/state heritage registers, GIS portals, DINAA/CARD/CyberSW, rather than p3k14c alone."
      )

  summary = {
    "periods_checked": checked,
    "tau1_global": data.get("raw_tau1_dimensionless", data.get("tau1_dimensionless")),
    "wls_active_periods": wls_active_periods,
    "zero_hab_periods": zero_hab_periods,
    "domain_sites": domain_sites,
    "baseline_c14_sites": baseline_c14,
    "baseline_multiplier": round(mult, 2) if mult is not None else None,
  }
  summary.update(hab_stats)
  return errors, warnings, summary


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
