"""Stages readable QA crop sheets for all 73 Project NICETHI figures into `tests/fig_qa_crops/`.

Produces clean, high-legibility crops (pure Pillow, zero Matplotlib) so an independent
`@verifier` subagent can visually inspect every chapter map, demographic trend panel,
rank-size panel and root synthesis panel via `read_file` without writing `visual_check.json`.
"""

import json
import os
from PIL import Image, ImageDraw, ImageFont

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
NIC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "NICETHI")
CACHE_PATH = os.path.join(NIC_DIR, "_shared", "nicethi_figure_cache.json")
QA_DIR = os.path.join(SVEA_ROOT, "tests", "fig_qa_crops")


def save_resized (arg0_img, arg1_out_path, arg2_max_w=1600):
  w, h = arg0_img.size
  if w > arg2_max_w:
    scale = arg2_max_w / float(w)
    out = arg0_img.resize((int(round(w * scale)), int(round(h * scale))), Image.Resampling.LANCZOS)
  else:
    out = arg0_img
  out.save(arg1_out_path, optimize=True)


def make_contact_sheet (arg0_paths, arg1_out_path, arg2_cols=1, arg3_tile_w=1400):
  """Stacks multiple chapter figures vertically into a high-resolution inspectable QA sheet."""
  tiles = []
  for p in arg0_paths:
    if not os.path.isfile(p):
      continue
    im = Image.open(p).convert("RGB")
    w, h = im.size
    scale = arg3_tile_w / float(w)
    tiles.append(im.resize((arg3_tile_w, int(round(h * scale))), Image.Resampling.LANCZOS))
  if not tiles:
    return
  pad = 16
  total_h = sum(t.height for t in tiles) + pad * (len(tiles) + 1)
  sheet = Image.new("RGB", (arg3_tile_w + 2 * pad, total_h), (245, 247, 250))
  y_cur = pad
  for t in tiles:
    sheet.paste(t, (pad, y_cur))
    y_cur += t.height + pad
  sheet.save(arg1_out_path, optimize=True)


def main ():
  os.makedirs(QA_DIR, exist_ok=True)
  cache = json.load(open(CACHE_PATH, encoding="utf-8"))

  # 1. Root synthesis figures: full-res readable crops + 2x2 split for fig_02 kriged substrata
  root_figs = [
    ("00_root_fig01_overview_map.png", "fig_01_nicethi_overview_map.png"),
    ("00_root_fig02_kriged_substrata.png", "fig_02_nicethi_kriged_substrata.png"),
    ("00_root_fig03_macro_trajectories.png", "fig_03_nicethi_macro_trajectories.png"),
    ("00_root_fig04_urban_hierarchy.png", "fig_04_nicethi_urban_hierarchy.png"),
  ]
  staged = 0
  for dst_name, src_name in root_figs:
    sp = os.path.join(NIC_DIR, "figures", src_name)
    if os.path.isfile(sp):
      im = Image.open(sp).convert("RGB")
      save_resized(im, os.path.join(QA_DIR, dst_name), 1600)
      staged += 1
      # Split 4-panel kriged figure into 2 half-sheets (top A+B, bottom C+D) for crisp zoom
      if src_name == "fig_02_nicethi_kriged_substrata.png":
        w, h = im.size
        save_resized(im.crop((0, 0, w, int(h * 0.52))), os.path.join(QA_DIR, "00_root_fig02_AB.png"), 1600)
        save_resized(im.crop((0, int(h * 0.48), w, h)), os.path.join(QA_DIR, "00_root_fig02_CD.png"), 1600)
        staged += 2

  # 2. Per-chapter stacked 3-figure QA sheet (01_<stem>_panel.png .. 23_<stem>_panel.png)
  for ch in cache["chapters"]:
    idx = int(ch["index"])
    key = ch["key"]
    fdir = os.path.join(NIC_DIR, ch["folder"], "figures")
    paths = [
      os.path.join(fdir, "fig_01_map.png"),
      os.path.join(fdir, "fig_02_trends.png"),
      os.path.join(fdir, "fig_03_rank_size.png"),
    ]
    out_sheet = os.path.join(QA_DIR, f"{idx:02d}_{key}_panel.png")
    make_contact_sheet(paths, out_sheet, arg2_cols=1, arg3_tile_w=1400)
    staged += 1

  print(f"[DONE] Staged {staged} QA sheets in {QA_DIR}.", flush=True)


if __name__ == "__main__":
  main()
