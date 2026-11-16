"""Gatekeeper D: Audits `4320x2160` float32 GeoPNG rasters for sharp modern-border steps
and discontinuities using PNG RGBA Float32BE decoding via PIL/numpy.
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image


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


def main():
  parser = argparse.ArgumentParser(description="Audit Operation Viscount GeoPNG rasters for artificial border cliffs.")
  parser.add_argument("target_path", help="Path to a GeoPNG file or directory of GeoPNGs")
  parser.add_argument("--mask", default=None, help="Optional domain mask PNG")
  parser.add_argument("--max-p99-jump", type=float, default=1.25, help="Max allowed p99 p90-normalised step across adjacent valid cells")
  parsed = parser.parse_args()

  png_files = []
  if os.path.isdir(parsed.target_path):
    png_files = [
      os.path.join(parsed.target_path, f)
      for f in sorted(os.listdir(parsed.target_path))
      if f.lower().endswith(".png")
    ]
  else:
    png_files = [parsed.target_path]

  if not png_files:
    print(f"[FAIL] No PNG rasters found at {parsed.target_path}", file=sys.stderr)
    sys.exit(1)

  all_errors = []
  all_stats = []
  for fp in png_files:
    errs, st = audit_raster_cliffs(fp, parsed.max_p99_jump, parsed.mask)
    all_errors.extend(errs)
    all_stats.append(st)

  for e in all_errors:
    print(f"[FAIL] {e}", file=sys.stderr)

  print(f"[audit_border_cliffs] Checked {len(all_stats)} raster(s): {json.dumps(all_stats[:5])}")
  sys.exit(1 if all_errors else 0)


if __name__ == "__main__":
  main()
