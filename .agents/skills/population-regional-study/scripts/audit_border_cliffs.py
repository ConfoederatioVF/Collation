"""Gatekeeper C2: Audits `4320x2160` float32 GeoPNG rasters for sharp internal modern-border
steps AND inter-Viscount cross-region seam discontinuities (`--check-inter-region`) using
PNG RGBA Float32BE decoding via PIL/numpy.
"""

import argparse
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


def decode_float32_png(arg0_png_path):
  """Decodes a Big-Endian IEEE-754 float32 RGBA GeoPNG into a `(H, W)` numpy array."""
  img = Image.open(arg0_png_path).convert("RGBA")
  raw_u8 = np.asarray(img, dtype=np.uint8)
  f32_be = raw_u8.reshape(-1, 4).copy().view(">f4").reshape(raw_u8.shape[:2])
  valid = np.isfinite(f32_be) & (f32_be > 0.0)
  return np.where(valid, f32_be, 0.0), valid


def audit_raster_cliffs(arg0_png_path, arg1_max_p99_soft=1.25, arg2_mask_png=None):
  """Computes scale-normalised adjacent step discontinuities across active land pixels."""
  field, valid = decode_float32_png(arg0_png_path)
  if int(valid.sum()) == 0:
    return [f"Raster has zero positive finite cells: {arg0_png_path}"], {}

  mask_valid = valid
  if arg2_mask_png and os.path.isfile(arg2_mask_png):
    mask_img = np.asarray(Image.open(arg2_mask_png).convert("RGBA"), dtype=np.uint8)
    mask_valid = valid & (mask_img[:, :, 3] > 0) & ((mask_img[:, :, :3].sum(axis=2)) > 0)

  nz = field[mask_valid]
  p50 = float(np.percentile(nz, 50.0))
  p90 = float(np.percentile(nz, 90.0))

  # East-west and north-south valid neighbour pairs
  ew_mask = mask_valid[:, :-1] & mask_valid[:, 1:]
  ns_mask = mask_valid[:-1, :] & mask_valid[1:, :]

  diffs = []
  maxima = []
  if int(ew_mask.sum()) > 0:
    ew_a = field[:, :-1][ew_mask]
    ew_b = field[:, 1:][ew_mask]
    diffs.append(np.abs(ew_a - ew_b))
    maxima.append(np.maximum(ew_a, ew_b))
  if int(ns_mask.sum()) > 0:
    ns_a = field[:-1, :][ns_mask]
    ns_b = field[1:, :][ns_mask]
    diffs.append(np.abs(ns_a - ns_b))
    maxima.append(np.maximum(ns_a, ns_b))

  all_diff = np.concatenate(diffs) if diffs else np.array([0.0])
  all_max = np.concatenate(maxima) if maxima else np.array([1.0])

  soft_rel = all_diff / np.maximum(all_max, max(p90, 1e-6))
  p99_soft = float(np.percentile(soft_rel, 99.0))
  hi_mask = all_max >= max(p50, 1e-6)
  p99_hi = float(np.percentile(all_diff[hi_mask] / all_max[hi_mask], 99.0)) if int(hi_mask.sum()) > 0 else 0.0

  # Detect sustained straight rectilinear border-wall cliffs (consecutive >= 8x steps above significance floor)
  ew_d = np.abs(field[:, :-1] - field[:, 1:])
  ew_mx = np.maximum(field[:, :-1], field[:, 1:])
  ew_mn = np.minimum(field[:, :-1], field[:, 1:])
  ns_d = np.abs(field[:-1, :] - field[1:, :])
  ns_mx = np.maximum(field[:-1, :], field[1:, :])
  ns_mn = np.minimum(field[:-1, :], field[1:, :])

  sig_floor = max(p50, 1e-3)
  diff_floor = max(0.5 * p90, 1e-3)
  cliff_ew = ew_mask & (ew_mx >= sig_floor) & (ew_d >= diff_floor) & ((ew_mx / np.maximum(ew_mn, 1e-6)) >= 8.0)
  cliff_ns = ns_mask & (ns_mx >= sig_floor) & (ns_d >= diff_floor) & ((ns_mx / np.maximum(ns_mn, 1e-6)) >= 8.0)

  max_wall_run = 0
  for col in np.flatnonzero(cliff_ew.any(axis=0)):
    vec = cliff_ew[:, col]
    padded = np.concatenate(([False], vec, [False]))
    idx = np.flatnonzero(padded[1:] != padded[:-1])
    runs = idx[1::2] - idx[::2]
    if runs.size > 0:
      max_wall_run = max(max_wall_run, int(runs.max()))

  for row in np.flatnonzero(cliff_ns.any(axis=1)):
    vec = cliff_ns[row, :]
    padded = np.concatenate(([False], vec, [False]))
    idx = np.flatnonzero(padded[1:] != padded[:-1])
    runs = idx[1::2] - idx[::2]
    if runs.size > 0:
      max_wall_run = max(max_wall_run, int(runs.max()))

  active_cells = int(mask_valid.sum())
  total_mass = float(field[mask_valid].sum())

  errors = []
  if p99_soft > arg1_max_p99_soft:
    errors.append(
      f"Sharp grid cliff detected in {os.path.basename(arg0_png_path)}: p99_soft={p99_soft:.3f} (> {arg1_max_p99_soft})."
    )
  if max_wall_run >= 18:
    errors.append(
      f"Linear border cliff wall detected in {os.path.basename(arg0_png_path)}: aligned 8x-step run={max_wall_run} px (>= 18 px)."
    )
  if total_mass <= 0.0:
    errors.append(f"Raster has non-positive total mass inside mask: {total_mass}")

  stats = {
    "file": os.path.basename(arg0_png_path),
    "active_cells": active_cells,
    "total_mass": round(total_mass, 2),
    "p50": round(p50, 4),
    "p90": round(p90, 4),
    "p99_soft_jump": round(p99_soft, 4),
    "p99_hi_rel": round(p99_hi, 4),
    "max_wall_run_px": max_wall_run,
  }
  return errors, stats


def find_svea_root(arg0_start_path):
  """Locates SVEA root folder by walking parent directories."""
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


def _load_json_or_json5(arg0_path):
  """Loads JSON or JSON5 safely."""
  raw = open(arg0_path, "r", encoding="utf-8", errors="replace").read()
  try:
    return json.loads(raw)
  except (json.JSONDecodeError, ValueError):
    if json5 is not None:
      return json5.loads(raw)
    cleaned = re.sub(r"//.*?$|/\*.*?\*/", "", raw, flags=re.MULTILINE | re.DOTALL)
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
    return json.loads(cleaned)


def _load_mask_bool(arg0_png_path):
  """Loads a mask PNG as a boolean active-pixel array."""
  arr = np.asarray(Image.open(arg0_png_path).convert("RGBA"), dtype=np.uint8)
  return (arr[:, :, 3] > 0) & ((arr[:, :, :3].sum(axis=2)) > 0)


def _build_project_mask(arg0_proj_entry, arg1_svea_root, arg2_shape=(2160, 4320)):
  """Builds union boolean mask from a Viscount project's areal_masks_manifest."""
  am_rel = (arg0_proj_entry or {}).get("areal_masks_manifest")
  if not am_rel:
    return None
  am_abs = os.path.join(arg1_svea_root, am_rel)
  if not os.path.isfile(am_abs):
    return None
  am = _load_json_or_json5(am_abs)
  union_m = np.zeros(arg2_shape, dtype=bool)
  items = ([am["macro_mask"]] if isinstance(am.get("macro_mask"), dict) else []) + list(am.get("specialist_masks") or [])
  for it in items:
    mp = it.get("mask_path") if isinstance(it, dict) else None
    if not mp:
      continue
    m_abs = mp if os.path.isabs(mp) else os.path.join(arg1_svea_root, mp)
    if os.path.isfile(m_abs):
      m_bool = _load_mask_bool(m_abs)
      if m_bool.shape == union_m.shape:
        union_m |= m_bool
  return union_m if union_m.any() else None


def audit_inter_region_seam_on_raster(
  arg0_raster_path,
  arg1_self_mask,
  arg2_neighbour_mask,
  arg3_label,
  arg4_max_median_dex=0.35,
  arg5_max_p95_dex=0.85,
  arg6_max_wall_px=8,
):
  """Measures log10 step ratios and aligned cliff walls strictly along the shared boundary between two masks."""
  field, valid = decode_float32_png(arg0_raster_path)
  if field.shape != arg1_self_mask.shape or field.shape != arg2_neighbour_mask.shape:
    return [f"[SEAM] Shape mismatch on {os.path.basename(arg0_raster_path)}"], {}

  a_m = arg1_self_mask & valid
  b_m = arg2_neighbour_mask & (~arg1_self_mask) & valid

  ew_ab = a_m[:, :-1] & b_m[:, 1:]
  ew_ba = b_m[:, :-1] & a_m[:, 1:]
  ns_ab = a_m[:-1, :] & b_m[1:, :]
  ns_ba = b_m[:-1, :] & a_m[1:, :]

  pairs_a = []
  pairs_b = []
  for m_pair, left_f, right_f in (
    (ew_ab, field[:, :-1], field[:, 1:]),
    (ew_ba, field[:, 1:], field[:, :-1]),
    (ns_ab, field[:-1, :], field[1:, :]),
    (ns_ba, field[1:, :], field[:-1, :]),
  ):
    if int(m_pair.sum()) > 0:
      pairs_a.append(left_f[m_pair])
      pairs_b.append(right_f[m_pair])

  if not pairs_a:
    return [], {"seam_pairs": 0}

  va = np.concatenate(pairs_a)
  vb = np.concatenate(pairs_b)
  hab = np.maximum(va, vb) >= 1.0
  if int(hab.sum()) < 10:
    return [], {"seam_pairs": int(va.size), "habitable_pairs": int(hab.sum())}

  va_h = np.maximum(va[hab], 1e-3)
  vb_h = np.maximum(vb[hab], 1e-3)
  log_diffs = np.abs(np.log10(va_h / vb_h))
  med_dex = float(np.median(log_diffs))
  p95_dex = float(np.percentile(log_diffs, 95.0))

  # Aligned >= 4x seam cliff wall check along E-W and N-S seam segments
  ew_seam = ew_ab | ew_ba
  ns_seam = ns_ab | ns_ba
  ew_ratio = np.maximum(field[:, :-1], field[:, 1:]) / np.maximum(np.minimum(field[:, :-1], field[:, 1:]), 1e-3)
  ns_ratio = np.maximum(field[:-1, :], field[1:, :]) / np.maximum(np.minimum(field[:-1, :], field[1:, :]), 1e-3)
  ew_cliff = ew_seam & (np.maximum(field[:, :-1], field[:, 1:]) >= 1.0) & (ew_ratio >= 4.0)
  ns_cliff = ns_seam & (np.maximum(field[:-1, :], field[1:, :]) >= 1.0) & (ns_ratio >= 4.0)

  max_wall = 0
  for col in np.flatnonzero(ew_cliff.any(axis=0)):
    padded = np.concatenate(([False], ew_cliff[:, col], [False]))
    idx = np.flatnonzero(padded[1:] != padded[:-1])
    runs = idx[1::2] - idx[::2]
    if runs.size > 0:
      max_wall = max(max_wall, int(runs.max()))
  for row in np.flatnonzero(ns_cliff.any(axis=1)):
    padded = np.concatenate(([False], ns_cliff[row, :], [False]))
    idx = np.flatnonzero(padded[1:] != padded[:-1])
    runs = idx[1::2] - idx[::2]
    if runs.size > 0:
      max_wall = max(max_wall, int(runs.max()))

  errors = []
  if med_dex > arg4_max_median_dex:
    errors.append(
      f"[INTER_REGION_SEAM] {arg3_label} ({os.path.basename(arg0_raster_path)}): median cross-seam log10 step={med_dex:.3f} dex (> {arg4_max_median_dex:.2f}); "
      "condition across 250 km frontier belt and run ViscountSubstrataSeamBlend."
    )
  if p95_dex > arg5_max_p95_dex:
    errors.append(
      f"[INTER_REGION_SEAM] {arg3_label} ({os.path.basename(arg0_raster_path)}): p95 cross-seam log10 step={p95_dex:.3f} dex (> {arg5_max_p95_dex:.2f})."
    )
  if max_wall >= arg6_max_wall_px:
    errors.append(
      f"[INTER_REGION_SEAM] {arg3_label} ({os.path.basename(arg0_raster_path)}): aligned >= 4x inter-region cliff wall={max_wall} px (>= {arg6_max_wall_px} px)."
    )

  return errors, {
    "file": os.path.basename(arg0_raster_path),
    "habitable_pairs": int(hab.sum()),
    "max_wall_px": max_wall,
    "median_dex": round(med_dex, 4),
    "p95_dex": round(p95_dex, 4),
    "seam": arg3_label,
  }


def audit_inter_region_continuity(arg0_project_key, arg1_domain_dir=None, arg2_opts=None):
  """Audits inter-Viscount cross-region seam continuity against all adjacent completed macro-regions."""
  opts = arg2_opts or {}
  svea_root = opts.get("svea_root") or find_svea_root(arg1_domain_dir or os.getcwd())
  errors = []
  stats = []
  if not svea_root:
    return ["Unable to locate SVEA repository root for inter-region seam audit."], stats

  # Direct mask-pair mode (for targeted checks & unit testing)
  if opts.get("self_mask") and opts.get("neighbour_mask") and opts.get("target_raster"):
    sm = _load_mask_bool(opts["self_mask"])
    nm = _load_mask_bool(opts["neighbour_mask"])
    errs, st = audit_inter_region_seam_on_raster(
      opts["target_raster"],
      sm,
      nm,
      f"{arg0_project_key}<->NEIGHBOUR",
      float(opts.get("max_seam_median_dex", 0.35)),
      float(opts.get("max_seam_p95_dex", 0.85)),
      int(opts.get("max_seam_wall_px", 8)),
    )
    return errs, [st]

  prec_p = os.path.join(svea_root, "histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5")
  if not os.path.isfile(prec_p):
    return [f"Missing viscount_precedence.json5: {prec_p}"], stats
  prec = _load_json_or_json5(prec_p)
  projects = prec.get("projects") or []
  key_up = str(arg0_project_key or "").upper()
  self_proj = next((p for p in projects if str(p.get("key") or "").upper() == key_up), None)
  if not self_proj:
    return [f"Unknown Viscount project key: {arg0_project_key}"], stats

  self_mask = _build_project_mask(self_proj, svea_root)
  if self_mask is None:
    return [f"Could not construct union mask for project {key_up}."], stats

  composed_dirs = [
    opts.get("composed_dir"),
    os.path.join(svea_root, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_2.scaled_to_regions"),
    os.path.join(svea_root, "histmap/2.data_cleaning/population_Velkscala/population_rasters"),
  ]
  composed_dir = next((d for d in composed_dirs if d and os.path.isdir(d)), None)
  if not composed_dir:
    return [f"No composed global raster directory found for inter-region seam audit of {key_up}."], stats

  years = [int(y.strip()) for y in str(opts.get("years") or "-2000,0,1000,1500,1900").split(",") if y.strip()]
  rasters = []
  for yr in years:
    for pat in (f"popc_{yr}.png", f"population_{yr}.png", f"popc_{yr}AD.png", f"popc_{abs(yr)}BC.png" if yr < 0 else ""):
      if pat:
        cand = os.path.join(composed_dir, pat)
        if os.path.isfile(cand):
          rasters.append(cand)
          break
  if not rasters:
    return [f"No benchmark rasters found in {composed_dir} for years {years}."], stats

  total_shared_seam_px = 0
  for nbr in projects:
    nkey = str(nbr.get("key") or "").upper()
    if nkey == key_up or str(nbr.get("status") or "").lower() != "complete":
      continue
    nbr_mask = _build_project_mask(nbr, svea_root)
    if nbr_mask is None:
      continue
    # Quick adjacency check
    touch = (
      (self_mask[:, :-1] & nbr_mask[:, 1:]).any()
      or (nbr_mask[:, :-1] & self_mask[:, 1:]).any()
      or (self_mask[:-1, :] & nbr_mask[1:, :]).any()
      or (nbr_mask[:-1, :] & self_mask[1:, :]).any()
    )
    if not touch:
      continue
    for rp in rasters:
      errs, st = audit_inter_region_seam_on_raster(
        rp,
        self_mask,
        nbr_mask,
        f"{key_up}<->{nkey}",
        float(opts.get("max_seam_median_dex", 0.35)),
        float(opts.get("max_seam_p95_dex", 0.85)),
        int(opts.get("max_seam_wall_px", 8)),
      )
      errors.extend(errs)
      if st.get("habitable_pairs", 0) > 0:
        total_shared_seam_px += int(st["habitable_pairs"])
        stats.append(st)

  # Verify cross-frontier conditioning sites exist in domain geojson whenever land seams exist
  if total_shared_seam_px >= 25 and arg1_domain_dir and os.path.isdir(os.path.join(arg1_domain_dir, "geojson")):
    frontier_sites = 0
    for gjp in sorted(glob.glob(os.path.join(arg1_domain_dir, "geojson", "*.geojson"))):
      try:
        gj = json.loads(open(gjp, "r", encoding="utf-8", errors="replace").read())
      except Exception:
        continue
      for feat in gj.get("features", []):
        props = feat.get("properties") or {}
        if props.get("is_frontier_buffer"):
          frontier_sites += 1
    if frontier_sites == 0:
      errors.append(
        f"[FRONTIER_CONDITIONING] Project {key_up} shares land seams ({total_shared_seam_px} habitable seam pairs) with neighbouring Viscount region(s) "
        "but has 0 `is_frontier_buffer: true` cross-border conditioning sites in `geojson/`."
      )

  return errors, stats


def main():
  parser = argparse.ArgumentParser(description="Audit Operation Viscount GeoPNG rasters for artificial internal & inter-region border cliffs.")
  parser.add_argument("target_path", nargs="?", default=None, help="Path to a GeoPNG file, raster directory or domain directory")
  parser.add_argument("--mask", default=None, help="Optional domain mask PNG")
  parser.add_argument("--max-p99-jump", type=float, default=1.25, help="Max allowed p99 p90-normalised step across adjacent valid cells")
  parser.add_argument("--check-inter-region", action="store_true", help="Audit cross-region seam continuity against adjacent completed Viscount regions")
  parser.add_argument("--project", default=None, help="Viscount project key for --check-inter-region")
  parser.add_argument("--composed-dir", default=None, help="Override composed global raster directory")
  parser.add_argument("--years", default="-2000,0,1000,1500,1900", help="Benchmark years for inter-region seam audit")
  parser.add_argument("--self-mask", default=None, help="Direct self mask PNG for targeted seam check")
  parser.add_argument("--neighbour-mask", default=None, help="Direct neighbour mask PNG for targeted seam check")
  parser.add_argument("--target-raster", default=None, help="Direct composed raster PNG for targeted seam check")
  parser.add_argument("--max-seam-median-dex", type=float, default=0.35)
  parser.add_argument("--max-seam-p95-dex", type=float, default=0.85)
  parser.add_argument("--max-seam-wall-px", type=int, default=8)
  parsed = parser.parse_args()

  all_errors = []
  all_stats = []

  if parsed.target_path:
    png_files = []
    if os.path.isdir(parsed.target_path):
      k_sub = os.path.join(parsed.target_path, "1.kriged_rasters")
      scan_dir = k_sub if os.path.isdir(k_sub) else parsed.target_path
      png_files = [
        os.path.join(scan_dir, f)
        for f in sorted(os.listdir(scan_dir))
        if f.lower().endswith(".png")
      ]
    else:
      png_files = [parsed.target_path]

    if not png_files and not parsed.check_inter_region:
      print(f"[FAIL] No PNG rasters found at {parsed.target_path}", file=sys.stderr)
      sys.exit(1)

    for fp in png_files:
      errs, st = audit_raster_cliffs(fp, parsed.max_p99_jump, parsed.mask)
      all_errors.extend(errs)
      all_stats.append(st)

  if parsed.check_inter_region:
    if not parsed.project:
      print("[FAIL] --check-inter-region requires --project <KEY>.", file=sys.stderr)
      sys.exit(1)
    seam_errs, seam_stats = audit_inter_region_continuity(parsed.project, parsed.target_path, vars(parsed))
    all_errors.extend(seam_errs)
    all_stats.extend(seam_stats)

  for e in all_errors:
    print(f"[FAIL] {e}", file=sys.stderr)

  print(f"[audit_border_cliffs] Checked {len(all_stats)} item(s): {json.dumps(all_stats[:6])}")
  sys.exit(1 if all_errors else 0)


if __name__ == "__main__":
  main()
