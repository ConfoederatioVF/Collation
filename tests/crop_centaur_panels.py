# -*- coding: utf-8 -*-
"""Crop multi-panel CENTAUR figures into tests/centaur_panel_crops for 1:1 visual inspection."""

import os
from PIL import Image


SVEA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CENTAUR_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CENTAUR")
CROP_DIR = os.path.join(os.path.dirname(__file__), "centaur_panel_crops")


def crop_grid (arg0_rel_path, arg1_prefix, arg2_cols, arg3_rows, arg4_names=None):
  """Crops a figure PNG into a grid of slightly overlapping panels."""
  src_path = os.path.join(CENTAUR_DIR, arg0_rel_path)
  if not os.path.isfile(src_path):
    print(f"[SKIP] Missing {src_path}")
    return []

  im = Image.open(src_path)
  w, h = im.size
  out_paths = []
  idx = 0
  for r in range(arg3_rows):
    for c in range(arg2_cols):
      x0 = max(0, int((c / arg2_cols) * w - 0.02 * w))
      x1 = min(w, int(((c + 1) / arg2_cols) * w + 0.02 * w))
      y0 = max(0, int((r / arg3_rows) * h - 0.02 * h))
      y1 = min(h, int(((r + 1) / arg3_rows) * h + 0.02 * h))
      if arg4_names and idx < len(arg4_names):
        tag = arg4_names[idx]
      else:
        tag = f"r{r + 1}c{c + 1}"
      out_path = os.path.join(CROP_DIR, f"{arg1_prefix}_{tag}.png")
      im.crop((x0, y0, x1, y1)).save(out_path)
      out_paths.append(out_path)
      idx += 1
  return out_paths


def main ():
  """Creates cropped panels for composite multi-panel CENTAUR figures."""
  os.makedirs(CROP_DIR, exist_ok=True)
  targets = [
    ("figures/fig1_centaur_macro_zones.png", "root_fig1", 2, 2, ["mainland", "alaska", "hawaii", "samoa"]),
    ("figures/fig5_kriging_validation.png", "root_fig5", 2, 2, ["panel_A", "panel_B", "panel_C", "panel_D"]),
    ("5.modern_canada_and_united_states/2.united_states_post_independence/figures/fig1_united_states_post_independence_spatial.png", "us_post_indep_fig1", 2, 2, ["panel_A", "panel_B", "panel_C", "panel_D"]),
    ("3.hawaii_and_american_polynesia/1.hawaii_and_american_polynesia/figures/fig1_hawaii_and_american_polynesia_spatial.png", "hawaii_fig1", 2, 1, ["panel_A_hawaii", "panel_B_samoa"]),
    ("4.colonial_america_and_canada/1.colonial_america_to_1754/figures/fig1_colonial_america_to_1754_spatial.png", "col1754_fig1", 2, 1, ["panel_A_east", "panel_B_alaska"]),
    ("4.colonial_america_and_canada/2.colonial_america_to_1783/figures/fig1_colonial_america_to_1783_spatial.png", "col1783_fig1", 2, 1, ["panel_A_east", "panel_B_alaska"])
  ]
  total = 0
  for rel_p, prefix, cols, rows, names in targets:
    res = crop_grid(rel_p, prefix, cols, rows, names)
    total += len(res)
    print(f"[CROPPED] {prefix}: {len(res)} panels")
  print(f"[DONE] Wrote {total} crops to {CROP_DIR}")


if __name__ == "__main__":
  main()
