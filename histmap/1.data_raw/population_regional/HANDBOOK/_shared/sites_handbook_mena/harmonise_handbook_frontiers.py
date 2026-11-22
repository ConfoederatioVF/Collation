"""Non-Blurring 2D Screened-Laplace (Helmholtz) Cross-Frontier Harmoniser for Project HANDBOOK.

Aligns HANDBOOK's narrow border ribbons (<= 18 px, ~150 km) along:
  1. The Greater Caucasus crest bordering completed Project POLARIS (Georgia/Azerbaijan <-> Russia)
  2. The Sulaiman/Makran/Durand frontier bordering completed Project INDUS (Afghanistan/SE Iran <-> Pakistan)
in `2.population_rasters/popc_<yr>.png` across all pre-1975 benchmark years (`-10000` to `1970 AD`).

Solves `(grad^2 - kappa^2) u = 0` strictly on the log10 multiplicative correction `u` with Dirichlet
target on the 1-px border facing POLARIS/INDUS (reading canonical `rasters_2.scaled_to_regions/popc_<yr>.png`
read-only!) and `u = 0` in the HANDBOOK interior beyond 18 px, preserving 100% of fine fluvial, valley
and settlement texture (`u` is smooth while `pop_new = pop_old * exp(u)` keeps every ridge/river intact).
"""

import os
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, distance_transform_edt

sys.path.insert(0, r"f:\Active Projects\Project 1509 - SVEA\.agents\skills\population-regional-study\scripts")
import audit_border_cliffs as abc

SVEA = r"f:\Active Projects\Project 1509 - SVEA"
HB_POP_DIR = os.path.join(SVEA, r"histmap\1.data_raw\population_regional\HANDBOOK\_shared\sites_handbook_mena\2.population_rasters")
PROD_R2 = os.path.join(SVEA, r"histmap\3.data_transform\population_Substrata.outlier_removal\rasters_2.scaled_to_regions")
HB_MASK_PNG = os.path.join(SVEA, r"histmap\1.data_raw\population_regional\HANDBOOK\_shared\sites_handbook_mena\config\handbook_domain_mask.png")


def encode_float32_png(arr, out_path):
  f32 = np.where(np.isfinite(arr) & (arr > 0.0), arr, 0.0).astype(">f4")
  u8 = f32.view(np.uint8).reshape(arr.shape[0], arr.shape[1], 4)
  Image.fromarray(u8, mode="RGBA").save(out_path, compress_level=6)


def solve_frontier_ribbon(hb_field, nbr_field, hb_mask, nbr_mask, max_dist_px=20.0, screen_len_px=7.5, iters=120, mosaic_scale=1.0, local_scale_grid=None):
  """Solves screened Laplace `(grad^2 - kappa^2) u = 0` on a tight bounding box around a single frontier."""
  # Identify HANDBOOK pixels adjacent (8-connected) to neighbour mask
  nbr_only = nbr_mask & (~hb_mask)
  nbr_dil = binary_dilation(nbr_only, iterations=1)
  border_px = hb_mask & nbr_dil
  if not border_px.any():
    return hb_field

  # Tight bounding box with 26 px margin
  rs, cs = np.where(border_px)
  r0 = max(0, int(rs.min()) - 28)
  r1 = min(hb_mask.shape[0], int(rs.max()) + 29)
  c0 = max(0, int(cs.min()) - 28)
  c1 = min(hb_mask.shape[1], int(cs.max()) + 29)

  sub_hb = hb_mask[r0:r1, c0:c1]
  sub_nb = nbr_only[r0:r1, c0:c1]
  sub_hf = hb_field[r0:r1, c0:c1]
  if local_scale_grid is not None:
    sub_sc = np.clip(local_scale_grid[r0:r1, c0:c1], 0.05, 25.0)
    sub_nf = nbr_field[r0:r1, c0:c1] / sub_sc
  else:
    sub_nf = nbr_field[r0:r1, c0:c1] / max(0.05, float(mosaic_scale))
  sub_bp = border_px[r0:r1, c0:c1]

  # Distance inside HANDBOOK from the border
  dist_b = distance_transform_edt(~sub_bp)
  # Seed any zero-masked 1-px outer border pixel facing an active neighbour pixel so ridge-mask mismatches don't cause 2+ dex cliffs
  sh, sw = sub_hf.shape
  seeded_hf = sub_hf.copy()
  brs_all, bcs_all = np.where(sub_bp)
  for rr, cc in zip(brs_all, bcs_all):
    if seeded_hf[rr, cc] > 0.0:
      continue
    nb_vals = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
      nr, nc = rr + dr, cc + dc
      if 0 <= nr < sh and 0 <= nc < sw and sub_nb[nr, nc] and sub_nf[nr, nc] > 0.05:
        nb_vals.append(float(sub_nf[nr, nc]))
    if nb_vals:
      seeded_hf[rr, cc] = float(np.median(nb_vals))

  ribbon = sub_hb & (dist_b <= max_dist_px) & (seeded_hf > 0.0)

  # Compute Dirichlet log-ratio target at every active border pixel using direct 4-connected neighbour first
  u_dir = np.zeros_like(seeded_hf, dtype=np.float64)
  is_dir = np.zeros(seeded_hf.shape, dtype=bool)
  brs, bcs = np.where(sub_bp & (seeded_hf > 0.0))
  for rr, cc in zip(brs, bcs):
    nb_vals = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
      nr, nc = rr + dr, cc + dc
      if 0 <= nr < sh and 0 <= nc < sw and sub_nb[nr, nc] and sub_nf[nr, nc] > 0.0:
        nb_vals.append(float(sub_nf[nr, nc]))
    if not nb_vals:
      for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
          nr, nc = rr + dr, cc + dc
          if 0 <= nr < sh and 0 <= nc < sw and sub_nb[nr, nc] and sub_nf[nr, nc] > 0.0:
            nb_vals.append(float(sub_nf[nr, nc]))
    if nb_vals:
      # Geometric median minimises worst-case log10 step across corner pixels bordering two contrasting neighbour cells
      target = float(np.exp(np.median(np.log(np.maximum(nb_vals, 1e-3)))))
      raw_u = np.log(max(target, 1e-3) / max(float(seeded_hf[rr, cc]), 1e-3))
      u_dir[rr, cc] = float(np.clip(raw_u, -6.0, 6.0))
      is_dir[rr, cc] = True

  if not is_dir.any():
    return hb_field

  # Solve screened Laplace `(u_N + u_S + u_E + u_W - (4 + kappa2) u) = 0` on ribbon interior
  kappa2 = 1.0 / (screen_len_px ** 2)
  solve_m = ribbon & (~is_dir)
  u = np.where(is_dir, u_dir, 0.0)
  inv_denom = 1.0 / (4.0 + kappa2)

  # Enforce u=0 outside ribbon (Dirichlet 0 into HANDBOOK interior)
  for _ in range(iters):
    avg = np.zeros_like(u)
    avg[1:, :] += u[:-1, :]
    avg[:-1, :] += u[1:, :]
    avg[:, 1:] += u[:, :-1]
    avg[:, :-1] += u[:, 1:]
    u_new = avg * inv_denom
    u = np.where(is_dir, u_dir, np.where(solve_m, u_new, 0.0))

  # Apply smooth multiplicative adjustment strictly on ribbon pixels
  out = hb_field.copy()
  sub_out = seeded_hf.copy()
  active = ribbon & (np.abs(u) > 1e-4)
  sub_out[active] = seeded_hf[active] * np.exp(u[active])
  out[r0:r1, c0:c1] = sub_out
  return out


def re_conserve_subadmin_mass(field, pre_field, subadmin_id_grid):
  """After harmonising narrow outer frontier ribbons, restores exact subadministrative unit mass
  strictly on interior pixels (`delta_mass == 0`) so frontier continuity never breaks mass conservation."""
  if subadmin_id_grid is None:
    return field
  out = field.copy()
  changed = np.abs(field - pre_field) > 1e-6
  touched_uids = np.unique(subadmin_id_grid[changed])
  for uid in touched_uids:
    if uid <= 0:
      continue
    u_mask = (subadmin_id_grid == uid)
    target_mass = float(pre_field[u_mask].sum())
    cur_mass = float(out[u_mask].sum())
    if target_mass <= 0.0 or abs(cur_mass - target_mass) / target_mass < 1e-6:
      continue
    # Absorb mass difference smoothly on non-border interior pixels of the same unit
    interior = u_mask & (~changed) & (out > 0.0)
    ribbon_mass = float(out[u_mask & changed].sum())
    int_mass = float(out[interior].sum())
    rem_target = target_mass - ribbon_mass
    if int_mass > 0.0 and rem_target > 0.0:
      out[interior] = out[interior] * (rem_target / int_mass)
    elif cur_mass > 0.0:
      out[u_mask] = out[u_mask] * (target_mass / cur_mass)
  return out


def main():
  prec = abc._load_json_or_json5(os.path.join(SVEA, r"histmap\2.data_cleaning\population_Stadester\config\viscount_precedence.json5"))
  hb_p_cfg = next(p for p in prec["projects"] if p["key"] == "HANDBOOK")
  pol_p = next(p for p in prec["projects"] if p["key"] == "POLARIS")
  ind_p = next(p for p in prec["projects"] if p["key"] == "INDUS")
  sar_p = next(p for p in prec["projects"] if p["key"] == "SARAY")
  mag_p = next((p for p in prec["projects"] if p["key"] == "MAGNETIC"), None)

  hb_mask = abc._build_project_mask(hb_p_cfg, SVEA)
  pol_mask = abc._build_project_mask(pol_p, SVEA)
  ind_mask = abc._build_project_mask(ind_p, SVEA)
  sar_mask = abc._build_project_mask(sar_p, SVEA)
  mag_mask = abc._build_project_mask(mag_p, SVEA) if mag_p is not None else None

  # Optional subadmin ID grids to preserve exact subadministrative mass conservation after frontier harmonisation
  sub_dir = os.path.join(SVEA, r"histmap\1.data_raw\population_regional\HANDBOOK\_shared\subadmin_censuses\rasters")
  def _load_id_grid(fn):
    p = os.path.join(sub_dir, fn)
    if not os.path.isfile(p):
      return None
    raw = np.asarray(Image.open(p).convert("RGBA"), dtype=np.uint8)
    return np.where(raw[:, :, 3] > 0, (raw[:, :, 0].astype(np.int32) << 8) | raw[:, :, 1].astype(np.int32), 0)
  hist_sub_id = _load_id_grid("subadmin_id_historical.png")
  mod_sub_id = _load_id_grid("subadmin_id_modern.png")

  qa_dir = os.path.join(SVEA, r"histmap\1.data_raw\population_regional\HANDBOOK\_shared\sites_handbook_mena\seam_qa_composed")
  # Measure per-year mosaic areal-scaling ratio on the Greater Caucasus border ribbon when seam_qa_composed exists
  def _estimate_mosaic_scale(hb_f_raw, qa_f, mask_b, nbr_m):
    nbr_only = nbr_m & (~mask_b)
    near_b = mask_b & binary_dilation(nbr_only, iterations=8)
    valid_r = near_b & (hb_f_raw > 0.2) & (qa_f > 0.2)
    if int(valid_r.sum()) >= 15:
      return float(np.clip(np.median(qa_f[valid_r] / hb_f_raw[valid_r]), 0.15, 8.0))
    return 1.0

  # Pre-calibrate scale anchors across QA benchmark years (-2000, 0, 1000, 1500, 1900)
  pol_scales = {}
  for byr in (-2000, 0, 1000, 1500, 1900):
    qp = os.path.join(qa_dir, f"popc_{byr}.png")
    hp = os.path.join(HB_POP_DIR, f"popc_{byr}.png")
    if os.path.isfile(qp) and os.path.isfile(hp):
      hf_b, _ = abc.decode_float32_png(hp)
      qf_b, _ = abc.decode_float32_png(qp)
      pol_scales[byr] = _estimate_mosaic_scale(hf_b, qf_b, hb_mask, pol_mask)

  def _interp_scale(yr_val, s_map):
    if not s_map:
      return 1.0
    ks = sorted(s_map.keys())
    if yr_val <= ks[0]:
      return s_map[ks[0]]
    if yr_val >= ks[-1]:
      return s_map[ks[-1]]
    for i in range(len(ks) - 1):
      if ks[i] <= yr_val <= ks[i + 1]:
        t = (yr_val - ks[i]) / float(ks[i + 1] - ks[i])
        return (1.0 - t) * s_map[ks[i]] + t * s_map[ks[i + 1]]
    return 1.0

  files = sorted(f for f in os.listdir(HB_POP_DIR) if f.startswith("popc_") and f.endswith(".png"))
  harmonised = 0
  for fn in files:
    yr = int(fn.replace("popc_", "").replace(".png", ""))
    if yr >= 1975:
      continue
    r2_p = os.path.join(PROD_R2, fn)
    hb_p = os.path.join(HB_POP_DIR, fn)
    if not os.path.exists(r2_p):
      continue
    hb_f, _ = abc.decode_float32_png(hb_p)
    r2_f, _ = abc.decode_float32_png(r2_p)
    pre_f = hb_f.copy()
    # Use QA-composed POLARIS neighbour + local per-subregion mosaic scale ratio when available
    qa_p = os.path.join(qa_dir, fn)
    pol_nbr = r2_f
    loc_sc = None
    if os.path.isfile(qa_p):
      pol_nbr, _ = abc.decode_float32_png(qa_p)
      # Local per-pixel mosaic ratio on HANDBOOK side so Georgia & Azerbaijan each get their exact areal scale
      valid_sc = hb_mask & (hb_f > 1e-3) & (pol_nbr > 1e-3)
      loc_sc = np.ones_like(hb_f, dtype=np.float64) * _interp_scale(yr, pol_scales)
      loc_sc[valid_sc] = np.clip(pol_nbr[valid_sc] / hb_f[valid_sc], 0.05, 25.0)
      # Propagate HANDBOOK border scale 1 px onto adjacent POLARIS cells for lookup
      from scipy.ndimage import maximum_filter
      loc_sc = np.where(hb_mask, loc_sc, maximum_filter(np.where(hb_mask, loc_sc, 0.0), size=3))
      loc_sc = np.where(loc_sc > 0.05, loc_sc, _interp_scale(yr, pol_scales))
    p_sc = _interp_scale(yr, pol_scales)

    # Harmonise Greater Caucasus (POLARIS), Kopet Dag / Amu Darya (SARAY), Durand/Makran (INDUS), and Thrace (MAGNETIC)
    hb_f = solve_frontier_ribbon(hb_f, pol_nbr, hb_mask, pol_mask, max_dist_px=20.0, screen_len_px=7.5, iters=120, mosaic_scale=p_sc, local_scale_grid=loc_sc)
    hb_f = solve_frontier_ribbon(hb_f, pol_nbr, hb_mask, sar_mask, max_dist_px=20.0, screen_len_px=7.5, iters=120, mosaic_scale=p_sc, local_scale_grid=loc_sc)
    hb_f = solve_frontier_ribbon(hb_f, pol_nbr, hb_mask, ind_mask, max_dist_px=18.0, screen_len_px=6.5, iters=100, mosaic_scale=p_sc, local_scale_grid=loc_sc)
    if mag_mask is not None:
      hb_f = solve_frontier_ribbon(hb_f, pol_nbr, hb_mask, mag_mask, max_dist_px=16.0, screen_len_px=6.0, iters=120, mosaic_scale=1.0, local_scale_grid=None)
    if yr >= 1880:
      hb_f = re_conserve_subadmin_mass(hb_f, pre_f, mod_sub_id if yr >= 1960 else hist_sub_id)
    encode_float32_png(hb_f, hb_p)
    harmonised += 1
  print(f"DONE harmonise_handbook_frontiers.py: harmonised {harmonised} pre-1975 benchmark rasters.", flush=True)


if __name__ == "__main__":
  main()
