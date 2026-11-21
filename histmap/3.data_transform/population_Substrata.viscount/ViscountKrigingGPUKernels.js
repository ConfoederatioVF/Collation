//Initialise Viscount Kriging OpenCL 3.0 Kernel Source
{
  let VISCOUNT_OPENCL_KERNELS = `
#pragma OPENCL EXTENSION cl_khr_fp64 : enable

/* -- Geodesic Voronoi nearest-catchment assignment (Step B) -- */
__kernel void viscount_voronoi_nearest (
  __global const float* cell_ux,
  __global const float* cell_uy,
  __global const float* cell_uz,
  __global const double* obs_ux,
  __global const double* obs_uy,
  __global const double* obs_uz,
  __global int* cell_nearest,
  const uint offset,
  const uint count,
  const uint n_obs
) {
  uint gid = get_global_id(0);
  if (gid >= count) return;
  uint i = offset + gid;

  double cx = (double)cell_ux[i];
  double cy = (double)cell_uy[i];
  double cz = (double)cell_uz[i];
  double best_dot = -2.0;
  int best_idx = 0;

  for (uint x = 0; x < n_obs; x++) {
    double d = cx*obs_ux[x] + cy*obs_uy[x] + cz*obs_uz[x];
    if (d > best_dot) {
      best_dot = d;
      best_idx = (int)x;
    }
  }
  cell_nearest[i] = best_idx;
}

/* -- Pairwise non-stationary u_matrix and scale_pref_mat (Step C) -- */
__kernel void viscount_pairwise_u_pref (
  __global const double* obs_ux,
  __global const double* obs_uy,
  __global const double* obs_uz,
  __global const double* obs_r,
  __global float* u_matrix,
  __global float* scale_pref_mat,
  const uint offset,
  const uint count,
  const uint n_obs,
  const double earth_r
) {
  uint gid = get_global_id(0);
  if (gid >= count) return;
  uint idx = offset + gid;
  uint i = idx/n_obs;
  uint x = idx - i*n_obs;

  if (i == x) {
    u_matrix[idx] = 0.0f;
    scale_pref_mat[idx] = 1.0f;
    return;
  }

  double dot = obs_ux[i]*obs_ux[x] + obs_uy[i]*obs_uy[x] + obs_uz[i]*obs_uz[x];
  dot = fmax(-1.0, fmin(1.0, dot));
  double c2 = fmax(0.0, 2.0 - 2.0*dot);
  double h = earth_r*sqrt(c2)*(1.0 + c2/24.0 + (3.0*c2*c2)/640.0);
  double ri = obs_r[i];
  double rx = obs_r[x];
  double r2_sum = ri*ri + rx*rx;
  double r_eff = sqrt(0.5*r2_sum);
  double pref = (2.0*ri*rx)/fmax(1e-8, r2_sum);
  double u = h/fmax(1e-6, r_eff);

  u_matrix[idx] = (float)u;
  scale_pref_mat[idx] = (float)pref;
}

/* -- Pairwise two-scale Matern nu=3/2 kernel fill (Step C) -- */
__kernel void viscount_fill_matern_kernels (
  __global const float* u_matrix,
  __global const float* scale_pref_mat,
  __global double* m1_mat,
  __global double* m2_mat,
  const uint offset,
  const uint count,
  const uint n_obs,
  const double inv_t1_s3,
  const double inv_t2_s3
) {
  uint gid = get_global_id(0);
  if (gid >= count) return;
  uint idx = offset + gid;
  uint i = idx/n_obs;
  uint x = idx - i*n_obs;

  if (i == x) {
    m1_mat[idx] = 1.0;
    m2_mat[idx] = 1.0;
    return;
  }

  double pref = (double)scale_pref_mat[idx];
  double u = (double)u_matrix[idx];
  double s1 = u*inv_t1_s3;
  double s2 = u*inv_t2_s3;

  m1_mat[idx] = pref*(1.0 + s1)*exp(-s1);
  m2_mat[idx] = pref*(1.0 + s2)*exp(-s2);
}

/* -- Two-scale non-stationary Paciorek-Schervish Matern potential evaluation (Step E) -- */
__kernel void viscount_matern_eval_potentials (
  __global const float* cell_ux,
  __global const float* cell_uy,
  __global const float* cell_uz,
  __global const float* cell_r,
  __global const float* cell_area,
  __global const double* obs_ux,
  __global const double* obs_uy,
  __global const double* obs_uz,
  __global const double* obs_r,
  __global const double* min_dot_per_obs,
  __global const double* w_packed,
  __global const double* c1_arr,
  __global const double* c2_arr,
  __global const double* inv_tau1_arr,
  __global const double* inv_tau2_arr,
  __global const double* var_restore_arr,
  __global const double* lut,
  __global float* out_pot,
  const uint offset,
  const uint count,
  const uint n_valid,
  const uint n_obs,
  const uint n_active,
  const uint shared_tau,
  const double earth_r
) {
  uint gid = get_global_id(0);
  if (gid >= count) return;
  uint i = offset + gid;

  double a_i = (double)cell_area[i];
  double cx = (double)cell_ux[i];
  double cy = (double)cell_uy[i];
  double cz = (double)cell_uz[i];
  double ri = (double)cell_r[i];
  double ri2 = ri*ri;
  double inv_t1_sh = inv_tau1_arr[0];
  double inv_t2_sh = inv_tau2_arr[0];
  double lut_scale = 8191.0/8.0;

  for (uint p_base = 0; p_base < n_active; p_base += 16) {
    uint p_end = min(n_active, p_base + 16u);
    uint p_cnt = p_end - p_base;
    double z_acc[16];

    for (uint lp = 0; lp < p_cnt; lp++) z_acc[lp] = 0.0;

    for (uint x = 0; x < n_obs; x++) {
      double dot = cx*obs_ux[x] + cy*obs_uy[x] + cz*obs_uz[x];
      if (dot <= min_dot_per_obs[x]) continue;
      dot = fmax(-1.0, fmin(1.0, dot));

      double c2_c = fmax(0.0, 2.0 - 2.0*dot);
      double h = earth_r*sqrt(c2_c)*(1.0 + c2_c/24.0);
      double rx = obs_r[x];
      double r2_sum = ri2 + rx*rx;
      double u = h/sqrt(0.5*r2_sum);
      double pref = (2.0*ri*rx)/fmax(1e-8, r2_sum);
      uint w_row = x*n_active + p_base;

      if (shared_tau != 0u) {
        double v2 = u*inv_t2_sh;
        if (v2 >= 7.99) continue;
        double m1 = 0.0;
        double v1 = u*inv_t1_sh;

        if (v1 < 7.99) {
          double sv1 = v1*lut_scale;
          uint i1 = (uint)sv1;
          double f1 = sv1 - (double)i1;
          m1 = pref*(lut[i1]*(1.0 - f1) + lut[i1 + 1u]*f1);
        }
        double sv2 = v2*lut_scale;
        uint i2 = (uint)sv2;
        double f2 = sv2 - (double)i2;
        double m2 = pref*(lut[i2]*(1.0 - f2) + lut[i2 + 1u]*f2);

        for (uint lp = 0; lp < p_cnt; lp++) {
          uint p = p_base + lp;
          z_acc[lp] += w_packed[w_row + lp]*(c1_arr[p]*m1 + c2_arr[p]*m2);
        }
      } else {
        for (uint lp = 0; lp < p_cnt; lp++) {
          uint p = p_base + lp;
          double wp = w_packed[w_row + lp];
          if (wp <= 0.0) continue;
          double v2 = u*inv_tau2_arr[p];
          if (v2 >= 7.99) continue;
          double m1 = 0.0;
          double v1 = u*inv_tau1_arr[p];

          if (v1 < 7.99) {
            double sv1 = v1*lut_scale;
            uint i1 = (uint)sv1;
            double f1 = sv1 - (double)i1;
            m1 = pref*(lut[i1]*(1.0 - f1) + lut[i1 + 1u]*f1);
          }
          double sv2 = v2*lut_scale;
          uint i2 = (uint)sv2;
          double f2 = sv2 - (double)i2;
          double m2 = pref*(lut[i2]*(1.0 - f2) + lut[i2 + 1u]*f2);

          z_acc[lp] += wp*(c1_arr[p]*m1 + c2_arr[p]*m2);
        }
      }
    }

    for (uint lp = 0; lp < p_cnt; lp++) {
      uint p = p_base + lp;
      double z_val = fmax(0.0, var_restore_arr[p]*z_acc[lp]);
      out_pot[p*n_valid + i] = (float)(a_i*pow(z_val, 2.25));
    }
  }
}

/* -- Terrain-barrier-aware multi-period signed residual Matern evaluation -- */
__kernel void viscount_residual_matern_multi (
  __global const float* cell_ux,
  __global const float* cell_uy,
  __global const float* cell_uz,
  __global const float* cell_r,
  __global const float* cell_area,
  __global const float* elev_valid,
  __global const int* cell_obs,
  __global const double* obs_ux,
  __global const double* obs_uy,
  __global const double* obs_uz,
  __global const double* obs_r,
  __global const double* obs_elev_m,
  __global const double* min_dot,
  __global const double* v_packed,
  __global const float* prior_dens_packed,
  __global const double* lut,
  __global float* out_r,
  __global float* out_pop,
  const uint offset,
  const uint count,
  const uint n_valid,
  const uint n_obs,
  const uint n_p,
  const uint flags,
  const double earth_r,
  const double c1,
  const double c2,
  const double inv_tau1,
  const double inv_tau2,
  const double inv_eb,
  const double cross_catch_mult,
  const double r_gain,
  const double r_clamp_min,
  const double r_clamp_max
) {
  uint gid = get_global_id(0);
  if (gid >= count) return;
  uint i = offset + gid;

  double a_i = (double)cell_area[i];
  double cx = (double)cell_ux[i];
  double cy = (double)cell_uy[i];
  double cz = (double)cell_uz[i];
  double ei = ((flags & 1u) != 0u) ? (double)elev_valid[i] : 150.0;
  int own_obs = ((flags & 2u) != 0u) ? cell_obs[i] : -1;
  double ri = (double)cell_r[i];
  double ri2 = ri*ri;
  double lut_scale = 8191.0/8.0;

  for (uint p_base = 0; p_base < n_p; p_base += 16) {
    uint p_end = min(n_p, p_base + 16u);
    uint p_cnt = p_end - p_base;
    double r_acc[16];

    for (uint lp = 0; lp < p_cnt; lp++) r_acc[lp] = 0.0;

    for (uint x = 0; x < n_obs; x++) {
      double dot = cx*obs_ux[x] + cy*obs_uy[x] + cz*obs_uz[x];
      if (dot <= min_dot[x]) continue;
      dot = fmax(-1.0, fmin(1.0, dot));

      double c2_c = fmax(0.0, 2.0 - 2.0*dot);
      double h = earth_r*sqrt(c2_c)*(1.0 + c2_c/24.0);
      double rx = obs_r[x];
      double r2_sum = ri2 + rx*rx;
      double u = h/sqrt(0.5*r2_sum);
      double v2 = u*inv_tau2;
      if (v2 >= 7.99) continue;

      double pref = (2.0*ri*rx)/fmax(1e-8, r2_sum);
      double m1 = 0.0;
      double v1 = u*inv_tau1;

      if (v1 < 7.99) {
        double sv1 = v1*lut_scale;
        uint i1 = (uint)sv1;
        double f1 = sv1 - (double)i1;
        m1 = pref*(lut[i1]*(1.0 - f1) + lut[i1 + 1u]*f1);
      }
      double sv2 = v2*lut_scale;
      uint i2 = (uint)sv2;
      double f2 = sv2 - (double)i2;
      double m2 = pref*(lut[i2]*(1.0 - f2) + lut[i2 + 1u]*f2);

      double de_norm = fabs(ei - obs_elev_m[x])*inv_eb;
      double elev_att = (de_norm > 0.05) ? exp(-pow(de_norm, 1.6)) : 1.0;
      double catch_att = (own_obs == (int)x) ? 1.0 : cross_catch_mult;
      double kern = catch_att*elev_att*(c1*m1 + c2*m2);
      uint v_row = x*n_p + p_base;

      for (uint lp = 0; lp < p_cnt; lp++) {
        double vx = v_packed[v_row + lp];
        if (vx != 0.0) r_acc[lp] += vx*kern;
      }
    }

    for (uint lp = 0; lp < p_cnt; lp++) {
      uint p = p_base + lp;
      uint out_idx = p*n_valid + i;
      double r_val = r_acc[lp];
      double pd = (double)prior_dens_packed[out_idx];

      out_r[out_idx] = (float)r_val;
      if (pd > 0.0) {
        double clamped = fmax(r_clamp_min, fmin(r_clamp_max, r_gain*r_val));
        out_pop[out_idx] = (float)(a_i*pd*exp(clamped));
      } else {
        out_pop[out_idx] = 0.0f;
      }
    }
  }
}

/* -- Separable horizontal tent/Gaussian blur with partition & elevation gating -- */
__kernel void viscount_smooth_grid_h (
  __global const float* cur_in,
  __global float* tmp_out,
  __global const int* v_idx,
  __global const int* p2v,
  __global const int* part_ids,
  __global const float* gate,
  __global const float* elev_v,
  const uint offset,
  const uint count,
  const int grid_w,
  const int rad,
  const uint flags
) {
  uint gid = get_global_id(0);
  if (gid >= count) return;
  uint i = offset + gid;

  uint has_gate = flags & 1u;
  uint pos_only = flags & 2u;
  uint has_part = flags & 4u;
  uint has_elev = flags & 8u;

  float cur_i = cur_in[i];
  if (has_gate != 0u && gate[i] <= 0.0f) { tmp_out[i] = cur_i; return; }
  if (pos_only != 0u && cur_i <= 0.0f) { tmp_out[i] = 0.0f; return; }

  int vi = v_idx[i];
  int cx = vi % grid_w;
  int row = (vi/grid_w)*grid_w;
  int pid = (has_part != 0u) ? part_ids[i] : 0;
  double ei = (has_elev != 0u) ? (double)elev_v[i] : 0.0;
  double acc = 0.0;
  double wsum = 0.0;

  for (int dx = -rad; dx <= rad; dx++) {
    int col = cx + dx;
    if (col < 0) col += grid_w;
    else if (col >= grid_w) col -= grid_w;
    int nv = p2v[row + col];

    if (nv < 0) continue;
    if (has_gate != 0u && gate[nv] <= 0.0f) continue;
    float cv = cur_in[nv];
    if (pos_only != 0u && cv <= 0.0f) continue;
    if (has_part != 0u && pid > 0 && part_ids[nv] != pid) continue;

    double wt = (double)(rad + 1 - abs(dx));
    if (has_elev != 0u) {
      double de = fabs(ei - (double)elev_v[nv]);
      if (de > 450.0) wt *= exp(-(de - 450.0)/220.0);
    }
    acc += (double)cv*wt;
    wsum += wt;
  }

  tmp_out[i] = (wsum > 0.0) ? (float)(acc/wsum) : cur_i;
}

/* -- Separable vertical tent/Gaussian blur with partition & elevation gating -- */
__kernel void viscount_smooth_grid_v (
  __global const float* tmp_in,
  __global const float* orig_in,
  __global float* cur_out,
  __global const int* v_idx,
  __global const int* p2v,
  __global const int* part_ids,
  __global const float* gate,
  __global const float* elev_v,
  const uint offset,
  const uint count,
  const int grid_w,
  const int grid_h,
  const int rad,
  const uint flags
) {
  uint gid = get_global_id(0);
  if (gid >= count) return;
  uint i = offset + gid;

  uint has_gate = flags & 1u;
  uint pos_only = flags & 2u;
  uint has_part = flags & 4u;
  uint has_elev = flags & 8u;

  float tmp_i = tmp_in[i];
  if (has_gate != 0u && gate[i] <= 0.0f) { cur_out[i] = tmp_i; return; }
  if (pos_only != 0u && orig_in[i] <= 0.0f) { cur_out[i] = 0.0f; return; }

  int vi = v_idx[i];
  int cx = vi % grid_w;
  int cy = vi/grid_w;
  int pid = (has_part != 0u) ? part_ids[i] : 0;
  double ei = (has_elev != 0u) ? (double)elev_v[i] : 0.0;
  double acc = 0.0;
  double wsum = 0.0;

  for (int dy = -rad; dy <= rad; dy++) {
    int nr = cy + dy;
    if (nr < 0 || nr >= grid_h) continue;
    int nv = p2v[nr*grid_w + cx];

    if (nv < 0) continue;
    if (has_gate != 0u && gate[nv] <= 0.0f) continue;
    float tv = tmp_in[nv];
    if (pos_only != 0u && tv <= 0.0f) continue;
    if (has_part != 0u && pid > 0 && part_ids[nv] != pid) continue;

    double wt = (double)(rad + 1 - abs(dy));
    if (has_elev != 0u) {
      double de = fabs(ei - (double)elev_v[nv]);
      if (de > 450.0) wt *= exp(-(de - 450.0)/220.0);
    }
    acc += (double)tv*wt;
    wsum += wt;
  }

  cur_out[i] = (wsum > 0.0) ? (float)(acc/wsum) : tmp_i;
}
`;

  global.VISCOUNT_OPENCL_KERNELS = VISCOUNT_OPENCL_KERNELS;
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { VISCOUNT_OPENCL_KERNELS: global.VISCOUNT_OPENCL_KERNELS };
