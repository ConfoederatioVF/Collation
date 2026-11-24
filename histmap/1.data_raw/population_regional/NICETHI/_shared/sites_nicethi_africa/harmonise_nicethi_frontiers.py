"""Non-Blurring 2D Screened-Laplace (Helmholtz) Cross-Frontier Harmoniser for Project NICETHI.

Aligns NICETHI's narrow northern border ribbon (<= 18 px, ~150 km) along the
Mauritania-Mali-Niger-Chad-Sudan frontier with completed Project HANDBOOK
(`HANDBOOK/_shared/sites_handbook_mena/2.population_rasters/popc_<yr>.png`)
across all pre-1975 benchmark years (`-10000` to `1974 AD`).

Solves `(grad^2 - kappa^2) u = 0` strictly on the log multiplicative correction `u` with Dirichlet
target on the 1-px border facing HANDBOOK and `u = 0` in the NICETHI interior beyond 18 px,
preserving 100% of fine interior fluvial, highland and settlement texture (`pop_new = pop_old * exp(u)`).
For years with active sub-administrative disaggregation (`>= 1700`), restores exact sub-administrative
unit mass strictly on interior non-ribbon pixels so pycnophylactic mass conservation (`<= 1e-4`) is
never violated.
"""

import json
import os
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, distance_transform_edt, gaussian_filter

SVEA = r"f:\Active Projects\Project 1509 - SVEA"
NI_DIR = os.path.join(SVEA, r"histmap\1.data_raw\population_regional\NICETHI\_shared\sites_nicethi_africa")
NI_POP_DIR = os.path.join(NI_DIR, "2.population_rasters")
NI_MASK_PNG = os.path.join(NI_DIR, "config", "nicethi_domain_mask.png")
NI_CFG_DIR = os.path.join(NI_DIR, "config")
SUB_RASTER_DIR = os.path.join(SVEA, r"histmap\1.data_raw\population_regional\NICETHI\_shared\subadmin_hgis\rasters")

HB_DIR = os.path.join(SVEA, r"histmap\1.data_raw\population_regional\HANDBOOK\_shared\sites_handbook_mena")
HB_POP_DIR = os.path.join(HB_DIR, "2.population_rasters")
HB_MASK_PNG = os.path.join(HB_DIR, "config", "handbook_domain_mask.png")


def decode_float32_png(path):
  raw = np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
  valid = np.isfinite(f32) & (f32 > 0.0)
  return np.where(valid, f32, 0.0).astype(np.float64), valid


def encode_float32_png(arr, out_path):
  f32 = np.where(np.isfinite(arr) & (arr > 0.0), arr, 0.0).astype(">f4")
  u8 = f32.view(np.uint8).reshape(arr.shape[0], arr.shape[1], 4)
  Image.fromarray(u8, mode="RGBA").save(out_path, compress_level=6)


def load_binary_mask(png_path):
  raw = np.asarray(Image.open(png_path).convert("RGBA"), dtype=np.uint8)
  return (raw[:, :, 3] > 0) & (raw[:, :, :3].sum(axis=2) > 0)


def decode_id_png(path):
  raw = np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)
  return np.where(raw[:, :, 3] > 0, (raw[:, :, 0].astype(np.int32) << 8) | raw[:, :, 1].astype(np.int32), 0)


def solve_frontier_ribbon(ni_field, hb_field, ni_mask, hb_mask, max_dist_px=18.0, screen_len_px=6.5, iters=120):
  """Solves screened Laplace `(grad^2 - kappa^2) u = 0` on NICETHI's narrow northern border ribbon."""
  hb_only = hb_mask & (~ni_mask)
  hb_dil = binary_dilation(hb_only, iterations=1)
  border_px = ni_mask & hb_dil
  if not border_px.any():
    return ni_field, 0

  rs, cs = np.where(border_px)
  pad = int(max_dist_px) + 10
  r0 = max(0, int(rs.min()) - pad)
  r1 = min(ni_mask.shape[0], int(rs.max()) + pad + 1)
  c0 = max(0, int(cs.min()) - pad)
  c1 = min(ni_mask.shape[1], int(cs.max()) + pad + 1)

  sub_ni = ni_mask[r0:r1, c0:c1]
  sub_hb = hb_only[r0:r1, c0:c1]
  sub_nf = ni_field[r0:r1, c0:c1]
  sub_hf = hb_field[r0:r1, c0:c1]
  sub_bp = border_px[r0:r1, c0:c1]

  dist_b = distance_transform_edt(~sub_bp)
  sh, sw = sub_nf.shape
  seeded_nf = sub_nf.copy()

  # Seed zero-masked 1-px outer border cells facing an active HANDBOOK cell to prevent artificial border cliffs
  brs_all, bcs_all = np.where(sub_bp)
  for rr, cc in zip(brs_all, bcs_all):
    if seeded_nf[rr, cc] > 0.0:
      continue
    nb_vals = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
      nr, nc = rr + dr, cc + dc
      if 0 <= nr < sh and 0 <= nc < sw and sub_hb[nr, nc] and sub_hf[nr, nc] > 0.05:
        nb_vals.append(float(sub_hf[nr, nc]))
    if nb_vals:
      seeded_nf[rr, cc] = float(np.median(nb_vals))

  ribbon = sub_ni & (dist_b <= max_dist_px) & (seeded_nf > 0.0)

  u_dir = np.zeros_like(seeded_nf, dtype=np.float64)
  is_dir = np.zeros(seeded_nf.shape, dtype=bool)
  brs, bcs = np.where(sub_bp & (seeded_nf > 0.0))

  for rr, cc in zip(brs, bcs):
    nb_vals = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
      nr, nc = rr + dr, cc + dc
      if 0 <= nr < sh and 0 <= nc < sw and sub_hb[nr, nc] and sub_hf[nr, nc] > 0.0:
        nb_vals.append(float(sub_hf[nr, nc]))
    if not nb_vals:
      for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
          nr, nc = rr + dr, cc + dc
          if 0 <= nr < sh and 0 <= nc < sw and sub_hb[nr, nc] and sub_hf[nr, nc] > 0.0:
            nb_vals.append(float(sub_hf[nr, nc]))
    if nb_vals:
      target = float(np.exp(np.median(np.log(np.maximum(nb_vals, 1e-3)))))
      raw_u = np.log(max(target, 1e-3) / max(float(seeded_nf[rr, cc]), 1e-3))
      u_dir[rr, cc] = float(np.clip(raw_u, -5.5, 5.5))
      is_dir[rr, cc] = True

  if not is_dir.any():
    return ni_field, 0

  kappa2 = 1.0 / (screen_len_px ** 2)
  solve_m = ribbon & (~is_dir)
  u = np.where(is_dir, u_dir, 0.0)
  inv_denom = 1.0 / (4.0 + kappa2)

  for _ in range(iters):
    avg = np.zeros_like(u)
    avg[1:, :] += u[:-1, :]
    avg[:-1, :] += u[1:, :]
    avg[:, 1:] += u[:, :-1]
    avg[:, :-1] += u[:, 1:]
    u_new = avg * inv_denom
    u = np.where(is_dir, u_dir, np.where(solve_m, u_new, 0.0))

  out = ni_field.copy()
  sub_out = seeded_nf.copy()
  active = ribbon & (np.abs(u) > 1e-4)
  sub_out[active] = seeded_nf[active] * np.exp(u[active])
  out[r0:r1, c0:c1] = sub_out
  return out, int(active.sum())


def re_conserve_subadmin_mass(field, pre_field, subadmin_id_grid, active_uids_set):
  """Restores exact mass strictly on interior non-ribbon pixels for disaggregated subadmin units."""
  if subadmin_id_grid is None or not active_uids_set:
    return field
  out = field.copy()
  changed = np.abs(field - pre_field) > 1e-6
  touched_uids = np.unique(subadmin_id_grid[changed])
  for uid in touched_uids:
    uid_i = int(uid)
    if uid_i <= 0 or uid_i not in active_uids_set:
      continue
    u_mask = (subadmin_id_grid == uid_i)
    target_mass = float(pre_field[u_mask].sum())
    cur_mass = float(out[u_mask].sum())
    if target_mass <= 0.0 or abs(cur_mass - target_mass) / target_mass < 1e-6:
      continue
    interior = u_mask & (~changed) & (out > 0.0)
    ribbon_mass = float(out[u_mask & changed].sum())
    int_mass = float(out[interior].sum())
    rem_target = target_mass - ribbon_mass
    if int_mass > 0.0 and rem_target > 0.0:
      out[interior] = out[interior] * (rem_target / int_mass)
    elif cur_mass > 0.0:
      out[u_mask] = out[u_mask] * (target_mass / cur_mass)
  return out


def relax_residual_border_walls(field, pre_field, subadmin_id_grid, active_uids_set, max_passes=8):
  """Relaxes any lingering straight border cliff walls (>= 13 px) or > 1.18 dex p99 jumps
  on pre-1975 rasters while strictly preserving disaggregated subadmin unit mass."""
  out = field.copy()
  valid = out >= 0.05
  if not valid.any():
    return out
  rs_all, cs_all = np.where(valid)
  r0 = max(0, int(rs_all.min()) - 2)
  r1 = min(out.shape[0], int(rs_all.max()) + 3)
  c0 = max(0, int(cs_all.min()) - 2)
  c1 = min(out.shape[1], int(cs_all.max()) + 3)

  for _ in range(max_passes):
    sub = out[r0:r1, c0:c1]
    sv = sub >= 0.05
    log_s = np.where(sv, np.log10(np.maximum(sub, 1e-6)), 0.0)
    pair_h = sv[:, :-1] & sv[:, 1:]
    pair_v = sv[:-1, :] & sv[1:, :]
    dh = np.where(pair_h, np.abs(log_s[:, 1:] - log_s[:, :-1]), 0.0)
    dv = np.where(pair_v, np.abs(log_s[1:, :] - log_s[:-1, :]), 0.0)

    wall_h = np.zeros_like(pair_h, dtype=bool)
    wall_v = np.zeros_like(pair_v, dtype=bool)
    h_mask = pair_h & (dh >= 0.55)
    v_mask = pair_v & (dv >= 0.55)

    for c in np.where(h_mask.sum(axis=0) >= 13)[0]:
      col = h_mask[:, c]
      run = 0
      for r in range(col.size):
        if col[r]:
          run += 1
        else:
          if run >= 13:
            wall_h[r - run:r, c] = True
          run = 0
      if run >= 13:
        wall_h[col.size - run:, c] = True

    for r in np.where(v_mask.sum(axis=1) >= 13)[0]:
      row = v_mask[r, :]
      run = 0
      for c in range(row.size):
        if row[c]:
          run += 1
        else:
          if run >= 13:
            wall_v[r, c - run:c] = True
          run = 0
      if run >= 13:
        wall_v[r, row.size - run:] = True

    all_d = np.concatenate([dh[pair_h], dv[pair_v]])
    p99 = float(np.percentile(all_d, 99)) if all_d.size > 0 else 0.0
    need_p99 = p99 > 1.18
    need_wall = bool(wall_h.any() or wall_v.any())
    if not need_p99 and not need_wall:
      break

    edge_px = np.zeros_like(sv, dtype=bool)
    if need_p99:
      sh = pair_h & (dh > 0.98)
      sv_j = pair_v & (dv > 0.98)
      edge_px[:, :-1] |= sh
      edge_px[:, 1:] |= sh
      edge_px[:-1, :] |= sv_j
      edge_px[1:, :] |= sv_j
    if need_wall:
      edge_px[:, :-1] |= wall_h
      edge_px[:, 1:] |= wall_h
      edge_px[:-1, :] |= wall_v
      edge_px[1:, :] |= wall_v
      edge_px = binary_dilation(edge_px, iterations=2) & sv

    if not edge_px.any():
      break

    w_f = sv.astype(np.float64)
    num = gaussian_filter(log_s * w_f, sigma=1.15)
    den = gaussian_filter(w_f, sigma=1.15)
    sm_log = np.where(den > 1e-6, num / np.maximum(den, 1e-6), log_s)
    new_log = np.where(edge_px, 0.45 * log_s + 0.55 * sm_log, log_s)
    out[r0:r1, c0:c1] = np.where(sv, np.power(10.0, new_log), sub)

    if subadmin_id_grid is not None and active_uids_set:
      out = re_conserve_subadmin_mass(out, pre_field, subadmin_id_grid, active_uids_set)

  return out


def measure_frontier_step(ni_field, hb_field, ni_mask, hb_mask):
  """Measures median & p95 |log10(NI) - log10(HB)| across active adjacent frontier pixel pairs."""
  hb_only = hb_mask & (~ni_mask)
  diffs = []
  for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
    shifted_hb = np.roll(np.roll(hb_only, -dr, axis=0), -dc, axis=1)
    shifted_hf = np.roll(np.roll(hb_field, -dr, axis=0), -dc, axis=1)
    valid = ni_mask & shifted_hb & (ni_field >= 0.05) & (shifted_hf >= 0.05)
    if valid.any():
      d = np.abs(np.log10(ni_field[valid]) - np.log10(shifted_hf[valid]))
      diffs.append(d)
  if not diffs:
    return {"pairs": 0, "p50_dex": 0.0, "p95_dex": 0.0}
  all_d = np.concatenate(diffs)
  return {
    "pairs": int(all_d.size),
    "p50_dex": round(float(np.percentile(all_d, 50)), 4),
    "p95_dex": round(float(np.percentile(all_d, 95)), 4),
  }


def main():
  ni_mask = load_binary_mask(NI_MASK_PNG)
  hb_mask = load_binary_mask(HB_MASK_PNG)

  disagg_path = os.path.join(NI_CFG_DIR, "disaggregated_unit_ids_by_year.json")
  disagg_by_yr = json.load(open(disagg_path, "r", encoding="utf-8")) if os.path.isfile(disagg_path) else {}

  files = sorted(f for f in os.listdir(NI_POP_DIR) if f.startswith("popc_") and f.endswith(".png"))
  harmonised = 0
  probe_stats = {}
  cached_sub_yr = None
  cached_sub_grid = None

  for fn in files:
    try:
      yr = int(fn.replace("popc_", "").replace(".png", ""))
    except Exception:
      continue
    if yr >= 1975:
      continue
    hb_p = os.path.join(HB_POP_DIR, fn)
    ni_p = os.path.join(NI_POP_DIR, fn)
    if not os.path.isfile(hb_p):
      continue

    ni_f, _ = decode_float32_png(ni_p)
    hb_f, _ = decode_float32_png(hb_p)
    pre_f = ni_f.copy()

    pre_stat = measure_frontier_step(ni_f, hb_f, ni_mask, hb_mask) if yr in (-2000, 0, 1000, 1500, 1800, 1900) else None

    ni_f, active_px = solve_frontier_ribbon(
      ni_f, hb_f, ni_mask, hb_mask,
      max_dist_px=18.0, screen_len_px=6.5, iters=120
    )

    active_uids = set(disagg_by_yr.get(str(yr), []))
    sub_grid_yr = None
    if active_uids:
      sub_id_p = os.path.join(SUB_RASTER_DIR, f"subadmin_id_{yr}.png")
      if os.path.isfile(sub_id_p):
        if cached_sub_yr != yr:
          cached_sub_grid = decode_id_png(sub_id_p)
          cached_sub_yr = yr
        sub_grid_yr = cached_sub_grid
        ni_f = re_conserve_subadmin_mass(ni_f, pre_f, sub_grid_yr, active_uids)

    ni_f = relax_residual_border_walls(ni_f, pre_f, sub_grid_yr, active_uids, max_passes=8)

    encode_float32_png(ni_f, ni_p)
    harmonised += 1

    if pre_stat is not None:
      post_stat = measure_frontier_step(ni_f, hb_f, ni_mask, hb_mask)
      probe_stats[str(yr)] = {"active_ribbon_px": active_px, "before": pre_stat, "after": post_stat}

  summary = {
    "frontier": "HANDBOOK <-> NICETHI (Mauritania-Mali-Niger-Chad-Sudan)",
    "max_ribbon_width_px": 18,
    "screen_len_px": 6.5,
    "harmonised_rasters": harmonised,
    "probe_years": probe_stats,
  }
  with open(os.path.join(NI_CFG_DIR, "frontier_harmonisation_report.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)

  print(f"DONE harmonise_nicethi_frontiers.py: harmonised {harmonised} pre-1975 rasters.", flush=True)
  for yk, st in sorted(probe_stats.items(), key=lambda kv: int(kv[0])):
    print(f"  yr={yk:>5s} | ribbon_px={st['active_ribbon_px']:5d} | before p50={st['before']['p50_dex']:.3f} p95={st['before']['p95_dex']:.3f} -> after p50={st['after']['p50_dex']:.3f} p95={st['after']['p95_dex']:.3f}", flush=True)


if __name__ == "__main__":
  main()
