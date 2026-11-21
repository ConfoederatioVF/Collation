//Import modules
let fs = global.fs || require("fs");

//Initialise functions
{
  /**
   * Isotropic 8-neighbour Euclidean chamfer belt builder and 2D harmonic multiplicative log-ratio seam
   * feathering engine for Operation Viscount inverse (`z-index`) inter-project borders.
   * Eliminates directional single-pixel extrusion streaking whilst preserving 100% of 5-arcminute
   * high-frequency river, coastal, and topographic micro-detail across frontier transitions.
   *
   * @class ViscountSubstrataSeamBlend
   */
  global.ViscountSubstrataSeamBlend = class {
    /**
     * Applies one-sided isotropic harmonic multiplicative log-ratio seam feathering strictly onto a
     * lower-order project's frontier belt (`z_seam_blend`), reading locked higher-order densities from
     * the active composed raster without single-pixel directional streaking or fine-detail blurring.
     * @alias ViscountSubstrataSeamBlend.applyOneSidedSeamBlend
     *
     * @param {Object} arg0_lower_context
     * @param {Buffer|Uint8Array} arg1_png_data
     * @param {DataView} arg2_png_dv
     * @param {Object} [arg3_options]
     *
     * @returns {number} Count of frontier belt pixels blended
     */
    static applyOneSidedSeamBlend (arg0_lower_context, arg1_png_data, arg2_png_dv, arg3_options) {
      //Convert from parameters
      let context = arg0_lower_context;
      let png_data = arg1_png_data;
      let png_dv = arg2_png_dv;
      let options = (arg3_options) ? arg3_options : {};

      //Guard clauses
      if (!context || !context.z_seam_blend || !png_data || !png_dv) return 0;

      //Declare local instance variables
      let belt_v = context.z_seam_blend.belt_v_indices;
      let blended_count = 0;
      let border_v = context.z_seam_blend.border_v_indices;
      let dist_px = context.z_seam_blend.dist_px;
      let grid_h = context.height || 2160;
      let grid_w = context.width || 4320;
      let log_max = Math.log(Number(options.max_seam_ratio) || 4.0);
      let log_min = Math.log(Number(options.min_seam_ratio) || 0.25);
      let n_valid = context.valid_indices.length;
      let owner_z = context.z_seam_blend.owner_z_grid;
      let p2v = context.pixel_to_valid;
      let proj_z = Number(context.z_seam_blend.proj_z || context.z_priority || 1);
      let seam_px = Number(context.z_seam_blend.seam_px || context.seam_feather_px || 24);
      let valid_indices = context.valid_indices;

      if (!belt_v || belt_v.length === 0 || !border_v || border_v.length === 0 || !owner_z || !p2v)
        return 0;

      //Function body
      let delta = new Float32Array(n_valid);
      let disk_r = 7;
      let has_bc = new Uint8Array(n_valid);
      let inv_2sig2 = 1.0/(2.0*3.4*3.4);

      //1. Compute isotropic mesoscale Gaussian log-ratio boundary condition along the shared frontier
      for (let i = 0; i < border_v.length; i++) {
        let v = border_v[i];
        let g = valid_indices[v];
        let cx = g % grid_w;
        let cy = Math.floor(g/grid_w);
        let hi_sum = 0;
        let hi_w = 0;
        let lo_sum = 0;
        let lo_w = 0;

        for (let dy = -disk_r; dy <= disk_r; dy++) {
          let nr = cy + dy;

          if (nr < 0 || nr >= grid_h) continue;
          let dy2 = dy*dy;

          for (let dx = -disk_r; dx <= disk_r; dx++) {
            let d2 = dy2 + dx*dx;

            if (d2 > disk_r*disk_r) continue;
            let nc = (cx + dx + grid_w) % grid_w;
            let n_idx = nr*grid_w + nc;
            let oz = owner_z[n_idx];

            if (oz === 0) continue;
            let val = this.readPositiveFloat32(png_data, png_dv, n_idx*4);

            if (val <= 0) continue;
            let wt = Math.exp(-d2*inv_2sig2);
            let lv = Math.log(val);

            if (oz > proj_z) {
              hi_sum += wt*lv;
              hi_w += wt;
            } else if (oz === proj_z) {
              lo_sum += wt*lv;
              lo_w += wt;
            }
          }
        }

        if (hi_w > 0 && lo_w > 0) {
          let raw_d = (hi_sum/hi_w) - (lo_sum/lo_w);

          delta[v] = Math.max(log_min, Math.min(log_max, raw_d));
          has_bc[v] = 1;
        }
      }

      //2. Smooth boundary log-ratio tangentially along border cells so sharp frontier corners stay C^1
      let bc_tmp = new Float32Array(border_v.length);

      for (let pass = 0; pass < 4; pass++) {
        for (let i = 0; i < border_v.length; i++) {
          let v = border_v[i];
          let g = valid_indices[v];
          let cx = g % grid_w;
          let cy = Math.floor(g/grid_w);
          let acc = has_bc[v] ? 2.0*delta[v] : 0;
          let wsum = has_bc[v] ? 2.0 : 0;

          for (let dy = -1; dy <= 1; dy++) {
            let nr = cy + dy;

            if (nr < 0 || nr >= grid_h) continue;
            for (let dx = -1; dx <= 1; dx++) {
              if (dx === 0 && dy === 0) continue;
              let nv = p2v[nr*grid_w + ((cx + dx + grid_w) % grid_w)];

              if (nv >= 0 && has_bc[nv]) {
                let w_n = (dx === 0 || dy === 0) ? 1.0 : 0.5;

                acc += w_n*delta[nv];
                wsum += w_n;
              }
            }
          }
          bc_tmp[i] = (wsum > 0) ? (acc/wsum) : 0;
        }
        for (let i = 0; i < border_v.length; i++) {
          let v = border_v[i];

          delta[v] = bc_tmp[i];
          if (bc_tmp[i] !== 0) has_bc[v] = 1;
        }
      }

      //3. Solve isotropic 2D harmonic Laplace equation inside the seam belt (Dirichlet BC: delta_0 at d=0, 0 at d>=seam_px)
      let interior_v = [];

      for (let i = 0; i < belt_v.length; i++) {
        let v = belt_v[i];

        if (has_bc[v] === 0 && dist_px[v] < seam_px) interior_v.push(v);
      }

      for (let iter = 0; iter < 40; iter++) {
        for (let i = 0; i < interior_v.length; i++) {
          let v = interior_v[i];
          let g = valid_indices[v];
          let cx = g % grid_w;
          let cy = Math.floor(g/grid_w);
          let acc = 0;
          let wsum = 0;

          for (let dy = -1; dy <= 1; dy++) {
            let nr = cy + dy;

            if (nr < 0 || nr >= grid_h) continue;
            for (let dx = -1; dx <= 1; dx++) {
              if (dx === 0 && dy === 0) continue;
              let nv = p2v[nr*grid_w + ((cx + dx + grid_w) % grid_w)];

              if (nv >= 0) {
                let w_n = (dx === 0 || dy === 0) ? 1.0 : 0.5;
                let nv_val = (dist_px[nv] >= seam_px) ? 0.0 : delta[nv];

                acc += w_n*nv_val;
                wsum += w_n;
              }
            }
          }
          if (wsum > 0) delta[v] = acc/wsum;
        }
      }

      //4. Apply smooth harmonic log-ratio multiplicatively with C^1 raised-cosine envelope (100% fine-detail preservation)
      for (let i = 0; i < belt_v.length; i++) {
        let v = belt_v[i];
        let d = dist_px[v];

        if (d >= seam_px) continue;
        let idx = valid_indices[v];
        let l_val = this.readPositiveFloat32(png_data, png_dv, idx*4);

        if (l_val <= 0) continue;
        let t = Math.max(0, Math.min(1, d/Math.max(1, seam_px)));
        let env = 0.5*(1 + Math.cos(Math.PI*t));
        let eff_d = delta[v]*(0.35 + 0.65*env);
        let blended = Math.max(1e-4, l_val*Math.exp(eff_d));

        png_dv.setFloat32(idx*4, blended, false);
        blended_count++;
      }

      //Return statement
      return blended_count;
    }


    /**
     * Constructs an isotropic 8-neighbour Euclidean chamfer distance belt (`3`/`4` metric scaled by `1/3`)
     * exclusively inside a lower-order project's exterior frontier adjacent to higher-`z_priority` projects.
     * @alias ViscountSubstrataSeamBlend.buildChamferSeamBelt
     *
     * @param {Object} arg0_context
     * @param {Uint8Array} arg1_owner_z_grid
     * @param {number} arg2_proj_z
     * @param {number} arg3_seam_px
     *
     * @returns {Object}
     */
    static buildChamferSeamBelt (arg0_context, arg1_owner_z_grid, arg2_proj_z, arg3_seam_px) {
      //Convert from parameters
      let ctx = arg0_context;
      let owner_z_grid = arg1_owner_z_grid;
      let proj_z = Number(arg2_proj_z);
      let seam_px = Number(arg3_seam_px) || 24;

      //Declare local instance variables
      let belt_v_list = [];
      let border_v_list = [];
      let buckets = [];
      let d_max_cham = Math.max(3, Math.round(seam_px*3));
      let height = ctx.height || 2160;
      let kept_valid = ctx.valid_indices || [];
      let p2v = ctx.pixel_to_valid;
      let width = ctx.width || 4320;
      let cham_dist = new Uint16Array(kept_valid.length).fill(65535);

      //Function body
      for (let b = 0; b <= d_max_cham; b++) buckets.push([]);

      for (let x = 0; x < kept_valid.length; x++) {
        let idx = kept_valid[x];
        let r = Math.floor(idx/width);
        let c = idx % width;
        let touches_higher = false;

        for (let dy = -1; dy <= 1 && !touches_higher; dy++) {
          let nr = r + dy;

          if (nr < 0 || nr >= height) continue;
          for (let dx = -1; dx <= 1; dx++) {
            if (dx === 0 && dy === 0) continue;
            let nc = (c + dx + width) % width;
            let n_idx = nr*width + nc;

            if (owner_z_grid[n_idx] > proj_z) {
              touches_higher = true;
              break;
            }
          }
        }
        if (touches_higher) {
          cham_dist[x] = 0;
          buckets[0].push(x);
          border_v_list.push(x);
        }
      }

      for (let d = 0; d < d_max_cham; d++) {
        let q = buckets[d];

        for (let qi = 0; qi < q.length; qi++) {
          let cur_v = q[qi];

          if (d > cham_dist[cur_v]) continue;
          let curr = kept_valid[cur_v];
          let r = Math.floor(curr/width);
          let c = curr % width;

          for (let dy = -1; dy <= 1; dy++) {
            let nr = r + dy;

            if (nr < 0 || nr >= height) continue;
            for (let dx = -1; dx <= 1; dx++) {
              if (dx === 0 && dy === 0) continue;
              let nc = (c + dx + width) % width;
              let nv = p2v ? p2v[nr*width + nc] : -1;

              if (nv < 0) continue;
              let nd = d + ((dx === 0 || dy === 0) ? 3 : 4);

              if (nd <= d_max_cham && nd < cham_dist[nv]) {
                cham_dist[nv] = nd;
                buckets[nd].push(nv);
              }
            }
          }
        }
      }

      let dist_px = new Float32Array(kept_valid.length);

      for (let x = 0; x < kept_valid.length; x++) {
        if (cham_dist[x] <= d_max_cham) {
          dist_px[x] = cham_dist[x]/3.0;
          belt_v_list.push(x);
        } else {
          dist_px[x] = seam_px + 1.0;
        }
      }

      //Return statement
      return {
        belt_v_indices: Int32Array.from(belt_v_list),
        border_v_indices: Int32Array.from(border_v_list),
        dist_px: dist_px,
        owner_z_grid: owner_z_grid,
        proj_z: proj_z,
        seam_px: seam_px
      };
    }


    /**
     * Safely reads a positive big-endian IEEE-754 `float32` value from a PNG RGBA buffer.
     * @alias ViscountSubstrataSeamBlend.readPositiveFloat32
     *
     * @param {Buffer|Uint8Array} arg0_png_data
     * @param {DataView} arg1_data_view
     * @param {number} arg2_byte_offset
     *
     * @returns {number}
     */
    static readPositiveFloat32 (arg0_png_data, arg1_data_view, arg2_byte_offset) {
      //Convert from parameters
      let png_data = arg0_png_data;
      let data_view = arg1_data_view;
      let p4 = arg2_byte_offset;

      //Guard clauses
      if ((png_data[p4] | png_data[p4 + 1] | png_data[p4 + 2] | png_data[p4 + 3]) === 0)
        return 0;

      //Declare local instance variables
      let val = data_view.getFloat32(p4, false);

      //Return statement
      return (Number.isFinite(val) && val > 0) ? val : 0;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountSubstrataSeamBlend: global.ViscountSubstrataSeamBlend };
