//Initialise Viscount Kriging OpenCL 3.0 Kernel Source (FP32 Local-Memory Tiled & WDDM-Safe)
{
  let VISCOUNT_OPENCL_KERNELS = `
#pragma OPENCL EXTENSION cl_khr_fp64 : enable

/* -- Geodesic Voronoi nearest-catchment assignment (Step B, FP32 Local-Memory Tiled) -- */
__kernel void viscount_voronoi_nearest (
  __global const float* cell_ux,
  __global const float* cell_uy,
  __global const float* cell_uz,
  __global const float* obs_ux,
  __global const float* obs_uy,
  __global const float* obs_uz,
  __global int* cell_nearest,
  const uint offset,
  const uint count,
  const uint n_obs
) {
  __local float s_ox[256];
  __local float s_oy[256];
  __local float s_oz[256];

  uint gid = get_global_id(0);
  uint lid = get_local_id(0);
  uint active = (gid < count) ? 1u : 0u;
  uint i = offset + gid;

  float cx = active ? cell_ux[i] : 0.0f;
  float cy = active ? cell_uy[i] : 0.0f;
  float cz = active ? cell_uz[i] : 0.0f;
  float best_dot = -2.0f;
  int best_idx = 0;

  for (uint base = 0u; base < n_obs; base += 256u) {
    uint load_idx = base + lid;
    if (load_idx < n_obs) {
      s_ox[lid] = obs_ux[load_idx];
      s_oy[lid] = obs_uy[load_idx];
      s_oz[lid] = obs_uz[load_idx];
    }
    barrier(CLK_LOCAL_MEM_FENCE);

    if (active) {
      uint tile_end = min(256u, n_obs - base);
      for (uint k = 0u; k < tile_end; k++) {
        float d = fma(cx, s_ox[k], fma(cy, s_oy[k], cz*s_oz[k]));
        if (d > best_dot) {
          best_dot = d;
          best_idx = (int)(base + k);
        }
      }
    }
    barrier(CLK_LOCAL_MEM_FENCE);
  }

  if (active) cell_nearest[i] = best_idx;
}

/* -- Pairwise non-stationary u_matrix and scale_pref_mat (Step C, cancellation-free chord-squared FP32) -- */
__kernel void viscount_pairwise_u_pref (
  __global const float* obs_ux,
  __global const float* obs_uy,
  __global const float* obs_uz,
  __global const float* obs_r,
  __global float* u_matrix,
  __global float* scale_pref_mat,
  const uint offset,
  const uint count,
  const uint n_obs,
  const float earth_r
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

  float dx = obs_ux[i] - obs_ux[x];
  float dy = obs_uy[i] - obs_uy[x];
  float dz = obs_uz[i] - obs_uz[x];
  float c2 = fmax(0.0f, fma(dx, dx, fma(dy, dy, dz*dz)));
  float h = earth_r*sqrt(c2)*(1.0f + c2*(1.0f/24.0f) + (3.0f/640.0f)*c2*c2);
  float ri = obs_r[i];
  float rx = obs_r[x];
  float r2_sum = fma(ri, ri, rx*rx);
  float r_eff = sqrt(0.5f*r2_sum);
  float pref = (2.0f*ri*rx)/fmax(1e-8f, r2_sum);
  float u = h/fmax(1e-6f, r_eff);

  u_matrix[idx] = u;
  scale_pref_mat[idx] = pref;
}

/* -- Pairwise two-scale Matern nu=3/2 kernel fill (Step C, FP32 transcendentals -> FP64 linear solver output) -- */
__kernel void viscount_fill_matern_kernels (
  __global const float* u_matrix,
  __global const float* scale_pref_mat,
  __global double* m1_mat,
  __global double* m2_mat,
  const uint offset,
  const uint count,
  const uint n_obs,
  const float inv_t1_s3,
  const float inv_t2_s3
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

  float pref = scale_pref_mat[idx];
  float u = u_matrix[idx];
  float s1 = u*inv_t1_s3;
  float s2 = u*inv_t2_s3;

  m1_mat[idx] = (double)(pref*(1.0f + s1)*exp(-s1));
  m2_mat[idx] = (double)(pref*(1.0f + s2)*exp(-s2));
}

/* -- Two-scale non-stationary Paciorek-Schervish Matern potential evaluation (Step E, FP32 Local-Memory Tiled) -- */
__kernel void viscount_matern_eval_potentials (
  __global const float* cell_ux,
  __global const float* cell_uy,
  __global const float* cell_uz,
  __global const float* cell_r,
  __global const float* cell_area,
  __global const float* obs_ux,
  __global const float* obs_uy,
  __global const float* obs_uz,
  __global const float* obs_r,
  __global const float* min_dot_per_obs,
  __global const float* w_packed,
  __global const float* c1_arr,
  __global const float* c2_arr,
  __global const float* inv_tau1_arr,
  __global const float* inv_tau2_arr,
  __global const float* var_restore_arr,
  __global const float* lut,
  __global float* out_pot,
  const uint offset,
  const uint count,
  const uint n_valid,
  const uint n_obs,
  const uint n_active,
  const uint shared_tau,
  const float earth_r
) {
  __local float s_ox[256];
  __local float s_oy[256];
  __local float s_oz[256];
  __local float s_or[256];
  __local float s_md[256];

  uint gid = get_global_id(0);
  uint lid = get_local_id(0);
  uint active = (gid < count) ? 1u : 0u;
  uint i = offset + gid;

  float a_i = active ? cell_area[i] : 0.0f;
  float cx = active ? cell_ux[i] : 0.0f;
  float cy = active ? cell_uy[i] : 0.0f;
  float cz = active ? cell_uz[i] : 0.0f;
  float ri = active ? cell_r[i] : 1.0f;
  float ri2 = ri*ri;
  float inv_t1_sh = inv_tau1_arr[0];
  float inv_t2_sh = inv_tau2_arr[0];
  float lut_scale = 8191.0f/8.0f;

  for (uint p_base = 0u; p_base < n_active; p_base += 16u) {
    uint p_end = min(n_active, p_base + 16u);
    uint p_cnt = p_end - p_base;
    float z_acc[16];
    float lc1[16];
    float lc2[16];
    float lit1[16];
    float lit2[16];

    for (uint lp = 0u; lp < p_cnt; lp++) {
      uint p = p_base + lp;
      z_acc[lp] = 0.0f;
      lc1[lp] = c1_arr[p];
      lc2[lp] = c2_arr[p];
      lit1[lp] = inv_tau1_arr[p];
      lit2[lp] = inv_tau2_arr[p];
    }

    for (uint base = 0u; base < n_obs; base += 256u) {
      uint load_idx = base + lid;
      if (load_idx < n_obs) {
        s_ox[lid] = obs_ux[load_idx];
        s_oy[lid] = obs_uy[load_idx];
        s_oz[lid] = obs_uz[load_idx];
        s_or[lid] = obs_r[load_idx];
        s_md[lid] = min_dot_per_obs[load_idx] - 1e-4f;
      }
      barrier(CLK_LOCAL_MEM_FENCE);

      if (active) {
        uint tile_end = min(256u, n_obs - base);
        for (uint k = 0u; k < tile_end; k++) {
          float ox = s_ox[k];
          float oy = s_oy[k];
          float oz = s_oz[k];
          float dot = fma(cx, ox, fma(cy, oy, cz*oz));
          if (dot <= s_md[k]) continue;

          float dx = cx - ox;
          float dy = cy - oy;
          float dz = cz - oz;
          float c2_c = fmax(0.0f, fma(dx, dx, fma(dy, dy, dz*dz)));
          float h = earth_r*sqrt(c2_c)*(1.0f + c2_c*(1.0f/24.0f));
          float rx = s_or[k];
          float r2_sum = fma(rx, rx, ri2);
          float u = h*rsqrt(fmax(1e-12f, 0.5f*r2_sum));
          float pref = (2.0f*ri*rx)/fmax(1e-8f, r2_sum);
          uint w_row = (base + k)*n_active + p_base;

          if (shared_tau != 0u) {
            float v2 = u*inv_t2_sh;
            if (v2 >= 7.99f) continue;
            float m1 = 0.0f;
            float v1 = u*inv_t1_sh;

            if (v1 < 7.99f) {
              float sv1 = v1*lut_scale;
              uint i1 = (uint)sv1;
              float f1 = sv1 - (float)i1;
              m1 = pref*fma(lut[i1 + 1u] - lut[i1], f1, lut[i1]);
            }
            float sv2 = v2*lut_scale;
            uint i2 = (uint)sv2;
            float f2 = sv2 - (float)i2;
            float m2 = pref*fma(lut[i2 + 1u] - lut[i2], f2, lut[i2]);

            for (uint lp = 0u; lp < p_cnt; lp++)
              z_acc[lp] = fma(w_packed[w_row + lp], fma(lc1[lp], m1, lc2[lp]*m2), z_acc[lp]);
          } else {
            for (uint lp = 0u; lp < p_cnt; lp++) {
              float wp = w_packed[w_row + lp];
              if (wp <= 0.0f) continue;
              float v2 = u*lit2[lp];
              if (v2 >= 7.99f) continue;
              float m1 = 0.0f;
              float v1 = u*lit1[lp];

              if (v1 < 7.99f) {
                float sv1 = v1*lut_scale;
                uint i1 = (uint)sv1;
                float f1 = sv1 - (float)i1;
                m1 = pref*fma(lut[i1 + 1u] - lut[i1], f1, lut[i1]);
              }
              float sv2 = v2*lut_scale;
              uint i2 = (uint)sv2;
              float f2 = sv2 - (float)i2;
              float m2 = pref*fma(lut[i2 + 1u] - lut[i2], f2, lut[i2]);

              z_acc[lp] = fma(wp, fma(lc1[lp], m1, lc2[lp]*m2), z_acc[lp]);
            }
          }
        }
      }
      barrier(CLK_LOCAL_MEM_FENCE);
    }

    if (active) {
      for (uint lp = 0u; lp < p_cnt; lp++) {
        uint p = p_base + lp;
        float z_val = fmax(0.0f, var_restore_arr[p]*z_acc[lp]);
        out_pot[p*n_valid + i] = a_i*pow(z_val, 2.25f);
      }
    }
  }
}

/* -- Terrain-barrier-aware multi-period signed residual Matern evaluation (FP32 Local-Memory Tiled) -- */
__kernel void viscount_residual_matern_multi (
  __global const float* cell_ux,
  __global const float* cell_uy,
  __global const float* cell_uz,
  __global const float* cell_r,
  __global const float* cell_area,
  __global const float* elev_valid,
  __global const int* cell_obs,
  __global const float* obs_ux,
  __global const float* obs_uy,
  __global const float* obs_uz,
  __global const float* obs_r,
  __global const float* obs_elev_m,
  __global const float* min_dot,
  __global const float* v_packed,
  __global const float* prior_dens_packed,
  __global const float* lut,
  __global float* out_r,
  __global float* out_pop,
  const uint offset,
  const uint count,
  const uint n_valid,
  const uint n_obs,
  const uint n_p,
  const uint flags,
  const float earth_r,
  const float c1,
  const float c2,
  const float inv_tau1,
  const float inv_tau2,
  const float inv_eb,
  const float cross_catch_mult,
  const float r_gain,
  const float r_clamp_min,
  const float r_clamp_max
) {
  __local float s_ox[256];
  __local float s_oy[256];
  __local float s_oz[256];
  __local float s_or[256];
  __local float s_oe[256];
  __local float s_md[256];

  uint gid = get_global_id(0);
  uint lid = get_local_id(0);
  uint active = (gid < count) ? 1u : 0u;
  uint i = offset + gid;

  float a_i = active ? cell_area[i] : 0.0f;
  float cx = active ? cell_ux[i] : 0.0f;
  float cy = active ? cell_uy[i] : 0.0f;
  float cz = active ? cell_uz[i] : 0.0f;
  float ei = (active && (flags & 1u) != 0u) ? elev_valid[i] : 150.0f;
  int own_obs = (active && (flags & 2u) != 0u) ? cell_obs[i] : -1;
  float ri = active ? cell_r[i] : 1.0f;
  float ri2 = ri*ri;
  float lut_scale = 8191.0f/8.0f;

  for (uint p_base = 0u; p_base < n_p; p_base += 16u) {
    uint p_end = min(n_p, p_base + 16u);
    uint p_cnt = p_end - p_base;
    float r_acc[16];

    for (uint lp = 0u; lp < p_cnt; lp++) r_acc[lp] = 0.0f;

    for (uint base = 0u; base < n_obs; base += 256u) {
      uint load_idx = base + lid;
      if (load_idx < n_obs) {
        s_ox[lid] = obs_ux[load_idx];
        s_oy[lid] = obs_uy[load_idx];
        s_oz[lid] = obs_uz[load_idx];
        s_or[lid] = obs_r[load_idx];
        s_oe[lid] = obs_elev_m[load_idx];
        s_md[lid] = min_dot[load_idx] - 1e-4f;
      }
      barrier(CLK_LOCAL_MEM_FENCE);

      if (active) {
        uint tile_end = min(256u, n_obs - base);
        for (uint k = 0u; k < tile_end; k++) {
          float ox = s_ox[k];
          float oy = s_oy[k];
          float oz = s_oz[k];
          float dot = fma(cx, ox, fma(cy, oy, cz*oz));
          if (dot <= s_md[k]) continue;

          float dx = cx - ox;
          float dy = cy - oy;
          float dz = cz - oz;
          float c2_c = fmax(0.0f, fma(dx, dx, fma(dy, dy, dz*dz)));
          float h = earth_r*sqrt(c2_c)*(1.0f + c2_c*(1.0f/24.0f));
          float rx = s_or[k];
          float r2_sum = fma(rx, rx, ri2);
          float u = h*rsqrt(fmax(1e-12f, 0.5f*r2_sum));
          float v2 = u*inv_tau2;
          if (v2 >= 7.99f) continue;

          float pref = (2.0f*ri*rx)/fmax(1e-8f, r2_sum);
          float m1 = 0.0f;
          float v1 = u*inv_tau1;

          if (v1 < 7.99f) {
            float sv1 = v1*lut_scale;
            uint i1 = (uint)sv1;
            float f1 = sv1 - (float)i1;
            m1 = pref*fma(lut[i1 + 1u] - lut[i1], f1, lut[i1]);
          }
          float sv2 = v2*lut_scale;
          uint i2 = (uint)sv2;
          float f2 = sv2 - (float)i2;
          float m2 = pref*fma(lut[i2 + 1u] - lut[i2], f2, lut[i2]);

          float de_norm = fabs(ei - s_oe[k])*inv_eb;
          float elev_att = (de_norm > 0.05f) ? exp(-pow(de_norm, 1.6f)) : 1.0f;
          float catch_att = (own_obs == (int)(base + k)) ? 1.0f : cross_catch_mult;
          float kern = catch_att*elev_att*fma(c1, m1, c2*m2);
          uint v_row = (base + k)*n_p + p_base;

          for (uint lp = 0u; lp < p_cnt; lp++) {
            float vx = v_packed[v_row + lp];
            if (vx != 0.0f) r_acc[lp] = fma(vx, kern, r_acc[lp]);
          }
        }
      }
      barrier(CLK_LOCAL_MEM_FENCE);
    }

    if (active) {
      for (uint lp = 0u; lp < p_cnt; lp++) {
        uint p = p_base + lp;
        uint out_idx = p*n_valid + i;
        float r_val = r_acc[lp];
        float pd = prior_dens_packed[out_idx];

        out_r[out_idx] = r_val;
        if (pd > 0.0f) {
          float clamped = fmax(r_clamp_min, fmin(r_clamp_max, r_gain*r_val));
          out_pop[out_idx] = a_i*pd*exp(clamped);
        } else {
          out_pop[out_idx] = 0.0f;
        }
      }
    }
  }
}

/* -- Separable horizontal tent/Gaussian blur with partition & elevation gating (FP32) -- */
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
  float ei = (has_elev != 0u) ? elev_v[i] : 0.0f;
  float acc = 0.0f;
  float wsum = 0.0f;

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

    float wt = (float)(rad + 1 - abs(dx));
    if (has_elev != 0u) {
      float de = fabs(ei - elev_v[nv]);
      if (de > 450.0f) wt *= exp(-(de - 450.0f)*(1.0f/220.0f));
    }
    acc = fma(cv, wt, acc);
    wsum += wt;
  }

  tmp_out[i] = (wsum > 0.0f) ? (acc/wsum) : cur_i;
}

/* -- Separable vertical tent/Gaussian blur with partition & elevation gating (FP32) -- */
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
  float ei = (has_elev != 0u) ? elev_v[i] : 0.0f;
  float acc = 0.0f;
  float wsum = 0.0f;

  for (int dy = -rad; dy <= rad; dy++) {
    int nr = cy + dy;
    if (nr < 0 || nr >= grid_h) continue;
    int nv = p2v[nr*grid_w + cx];

    if (nv < 0) continue;
    if (has_gate != 0u && gate[nv] <= 0.0f) continue;
    float tv = tmp_in[nv];
    if (pos_only != 0u && tv <= 0.0f) continue;
    if (has_part != 0u && pid > 0 && part_ids[nv] != pid) continue;

    float wt = (float)(rad + 1 - abs(dy));
    if (has_elev != 0u) {
      float de = fabs(ei - elev_v[nv]);
      if (de > 450.0f) wt *= exp(-(de - 450.0f)*(1.0f/220.0f));
    }
    acc = fma(tv, wt, acc);
    wsum += wt;
  }

  cur_out[i] = (wsum > 0.0f) ? (acc/wsum) : tmp_i;
}
`;

  global.VISCOUNT_OPENCL_KERNELS = VISCOUNT_OPENCL_KERNELS;
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { VISCOUNT_OPENCL_KERNELS: global.VISCOUNT_OPENCL_KERNELS };
