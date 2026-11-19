//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");
let drs_p = (typeof __dirname !== "undefined" && fs.existsSync(path.resolve(__dirname, "../ViscountDasymetricResidualSolver.js"))) ?
  path.resolve(__dirname, "../ViscountDasymetricResidualSolver.js") :
  path.resolve(process.cwd(), "histmap/3.data_transform/population_Substrata.viscount/ViscountDasymetricResidualSolver.js");
let um_p = (typeof __dirname !== "undefined" && fs.existsSync(path.resolve(__dirname, "../ViscountUrbanMask.js"))) ?
  path.resolve(__dirname, "../ViscountUrbanMask.js") :
  path.resolve(process.cwd(), "histmap/3.data_transform/population_Substrata.viscount/ViscountUrbanMask.js");
let ViscountDasymetricResidualSolver = global.ViscountDasymetricResidualSolver || require(drs_p).ViscountDasymetricResidualSolver;
let ViscountUrbanMask = global.ViscountUrbanMask || require(um_p).ViscountUrbanMask;

//Initialise functions
{
  /**
   * Low-level Gaussian de-cliffing, sparse Matérn residual covariance, series interpolation,
   * modern Census/GHSL rural compositing and C1 WLS diagnostics helpers for `ViscountHUResidualKriging`.
   *
   * @class ViscountHUResidualHelpers
   */
  global.ViscountHUResidualHelpers = class {
    /**
     * Applies smooth harmonic Laplacian log-density infill and soft-knee capping on pre-industrial urban-core
     * footprints (`uopp > 3.5`), eliminating both modern megacity spikes and flat-top urban mask plateaus/edges.
     * @alias ViscountHUResidualHelpers.capUrbanCoreSmooth
     */
    static capUrbanCoreSmooth (arg0_mask_data, arg1_field, arg2_uopp_valid, arg3_max_mult) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let field = arg1_field;
      let uopp = arg2_uopp_valid;
      let max_mult = (arg3_max_mult !== undefined) ? arg3_max_mult : 0.88;

      //Guard clauses
      if (!mask_data || !field || !uopp) return;

      //Declare local instance variables
      let cell_area = mask_data.cell_land_area;
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let rural_dens_in = new Float32Array(n_valid);
      let rural_wt_in = new Float32Array(n_valid);
      let urb_list = [];
      let v_idx = mask_data.valid_indices;

      //Function body
      for (let i = 0; i < n_valid; i++) {
        if (field[i] <= 0) continue;
        let local_a = (cell_area && cell_area[i] > 1.0) ? cell_area[i] : 1.0;

        if (uopp[i] <= 3.5) {
          rural_dens_in[i] = field[i]/local_a;
          rural_wt_in[i] = 1.0;
        } else {
          urb_list.push(i);
        }
      }
      if (urb_list.length === 0) return;

      let r_dens = this.smoothGaussianGrid(mask_data, rural_dens_in, 8, 3, null, false);
      let r_wt = this.smoothGaussianGrid(mask_data, rural_wt_in, 8, 3, null, false);
      let r_dens_wide = this.smoothGaussianGrid(mask_data, rural_dens_in, 15, 3, null, false);
      let r_wt_wide = this.smoothGaussianGrid(mask_data, rural_wt_in, 15, 3, null, false);
      let log_dens = new Float32Array(n_valid);
      let has_val = new Uint8Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        if (field[i] <= 0) continue;
        let local_a = (cell_area && cell_area[i] > 1.0) ? cell_area[i] : 1.0;

        has_val[i] = 1;
        if (uopp[i] <= 3.5) {
          log_dens[i] = Math.log(Math.max(1e-7, field[i]/local_a));
        } else {
          //Initialise interior from smooth rural-ring blend so harmonic infill converges rapidly
          let w_loc = Math.max(0, Math.min(1, (r_wt[i] - 0.04)/0.26));
          let d_loc = (r_wt[i] > 1e-4) ? (r_dens[i]/r_wt[i]) : 0;
          let d_wid = (r_wt_wide[i] > 1e-4) ? (r_dens_wide[i]/r_wt_wide[i]) : d_loc;
          let d_init = (d_loc > 0 && d_wid > 0) ? (w_loc*d_loc + (1.0 - w_loc)*d_wid) : (d_loc || d_wid || (field[i]/local_a));

          log_dens[i] = Math.log(Math.max(1e-7, d_init));
        }
      }

      //28-pass Gauss-Seidel harmonic Laplacian infill on log-density inside urban footprints (C^1 boundary continuity, zero flat mesas)
      for (let iter = 0; iter < 28; iter++) {
        for (let k = 0; k < urb_list.length; k++) {
          let i = urb_list[k];
          let g = v_idx[i];
          let cx = g % grid_w;
          let cy = Math.floor(g/grid_w);
          let acc = 0;
          let wt_s = 0;

          for (let dy = -1; dy <= 1; dy++) {
            let nr = cy + dy;

            if (nr < 0 || nr >= grid_h) continue;
            for (let dx = -1; dx <= 1; dx++) {
              if (dx === 0 && dy === 0) continue;
              let nv = p2v[nr*grid_w + ((cx + dx + grid_w) % grid_w)];

              if (nv >= 0 && has_val[nv] === 1) {
                let w_n = (dx === 0 || dy === 0) ? 1.0 : 0.5;

                acc += w_n*log_dens[nv];
                wt_s += w_n;
              }
            }
          }
          if (wt_s > 0) log_dens[i] = acc/wt_s;
        }
      }

      //Soft-knee harmonic blend preserving surrounding gradients & micro-texture without flat urban mesas or boundary cliffs
      let eff_ceil = Math.min(1.04, Math.max(0.55, max_mult));
      let knee = 0.94*eff_ceil;

      for (let k = 0; k < urb_list.length; k++) {
        let i = urb_list[k];
        let local_a = (cell_area && cell_area[i] > 1.0) ? cell_area[i] : 1.0;
        let harm_pop = Math.exp(log_dens[i])*local_a;

        if (!(harm_pop > 0)) continue;
        let u_t = Math.max(0, Math.min(1, (uopp[i] - 3.5)/6.0));
        let t_ramp = u_t*u_t*(3.0 - 2.0*u_t);
        let ratio = field[i]/harm_pop;
        let soft_ratio = (ratio <= knee) ?
          (0.65*ratio + 0.35*Math.min(1.0, eff_ceil)) :
          (knee + 0.14*eff_ceil*Math.tanh((ratio - knee)/(0.35*eff_ceil)));
        let target_pop = harm_pop*soft_ratio;

        field[i] = field[i]*(1.0 - t_ramp) + target_pop*t_ramp;
      }
    }


    /**
     * Fills isolated zero-pinholes on eligible valid land cells surrounded by positive Moore neighbours.
     * @alias ViscountHUResidualHelpers.closeZeroPinholes
     */
    static closeZeroPinholes (arg0_mask_data, arg1_field, arg2_eligible_mask, arg3_min_nbrs, arg4_scale, arg5_passes, arg6_floor) {
      let mask_data = arg0_mask_data;
      let field = arg1_field;
      let eligible = arg2_eligible_mask;
      let min_nbrs = (arg3_min_nbrs !== undefined) ? arg3_min_nbrs : 5;
      let scale = (arg4_scale !== undefined) ? arg4_scale : 0.45;
      let passes = (arg5_passes !== undefined) ? arg5_passes : 2;
      let min_floor = (arg6_floor !== undefined) ? arg6_floor : 0;
      let h = mask_data.grid_height;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let v_idx = mask_data.valid_indices;
      let w = mask_data.grid_width;

      for (let p = 0; p < passes; p++) {
        let updates = [];

        for (let i = 0; i < n_valid; i++) {
          if (field[i] > 0 || (eligible && eligible[i] === 0)) continue;
          let g = v_idx[i];
          let cx = g % w;
          let cy = Math.floor(g/w);
          let cnt = 0;
          let sum = 0;

          for (let dy = -1; dy <= 1; dy++) {
            let nr = cy + dy;

            if (nr < 0 || nr >= h) continue;
            for (let dx = -1; dx <= 1; dx++) {
              if (dx === 0 && dy === 0) continue;
              let nv = p2v[nr*w + ((cx + dx + w) % w)];

              if (nv >= 0 && field[nv] > 0) {
                cnt++;
                sum += field[nv];
              }
            }
          }
          if (cnt >= min_nbrs)
            updates.push([i, Math.max(min_floor, scale*(sum/cnt))]);
        }
        for (let u = 0; u < updates.length; u++)
          field[updates[u][0]] = updates[u][1];
      }
    }


    /**
     * Computes lat-lon bounding box of valid mask pixels with 2° padding.
     * @alias ViscountHUResidualHelpers.computeMaskBBox
     */
    static computeMaskBBox (arg0_mask_data) {
      let h = arg0_mask_data.grid_height;
      let max_lat = -90;
      let max_lon = -180;
      let min_lat = 90;
      let min_lon = 180;
      let v_idx = arg0_mask_data.valid_indices;
      let w = arg0_mask_data.grid_width;

      for (let i = 0; i < v_idx.length; i++) {
        let lat = 90 - (Math.floor(v_idx[i]/w) + 0.5)*180/h;
        let lon = -180 + ((v_idx[i] % w) + 0.5)*360/w;

        if (lat < min_lat) min_lat = lat;
        if (lat > max_lat) max_lat = lat;
        if (lon < min_lon) min_lon = lon;
        if (lon > max_lon) max_lon = lon;
      }

      //Return statement
      return {
        max_lat: Math.min(90, max_lat + 2),
        max_lon: Math.min(180, max_lon + 2),
        min_lat: Math.max(-90, min_lat - 2),
        min_lon: Math.max(-180, min_lon - 2)
      };
    }


    /**
     * Step E: Evaluates un-flattened modern census HYDE 3.5 rural + GHSL satellite rural density (`1730..2025 AD`).
     * @alias ViscountHUResidualHelpers.evaluateModernCensusAndSatelliteRural
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_bio_covs
     * @param {number} arg2_year
     * @param {Object} arg3_config
     * @param {Map} [arg4_cache]
     *
     * @returns {Float32Array}
     */
    static evaluateModernCensusAndSatelliteRural (arg0_mask_data, arg1_bio_covs, arg2_year, arg3_config, arg4_cache) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let bio_covs = arg1_bio_covs;
      let year = Number(arg2_year) || 0;
      let config = (arg3_config) ? arg3_config : {};
      let cache = arg4_cache;

      //Declare local instance variables
      let cell_area = mask_data.cell_land_area;
      let cov_paths = (config.kriging_config && config.kriging_config.covariate_paths) ?
        config.kriging_config.covariate_paths : {};
      let ghs_dir = path.resolve(mask_data.project_root || ".", "histmap/2.data_cleaning/population_GHSL/cleaned_rasters");
      let ghsl_urb_dir = path.resolve(mask_data.project_root || ".", cov_paths.ghsl_urban_folder || "histmap/1.data_raw/population_GHSL/urban_rasters");
      let ghsl_yr = Math.max(1975, Math.min(2025, Math.round(year)));
      let hyde_lbl = this.resolveHYDEYearLabel(year);
      let hyde_raw_dir = path.resolve(mask_data.project_root || ".", cov_paths.hyde_raw_rasters_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters");
      let hyde_rur_path = path.join(hyde_raw_dir, `rurc_${hyde_lbl}.png`);
      let n_valid = mask_data.valid_cell_count;
      let out_rur = new Float32Array(n_valid);
      let perm_ice = bio_covs.perm_ice;
      let total_px = mask_data.grid_width*mask_data.grid_height;
      let uopp = bio_covs.uopp_valid;
      let valid_indices = mask_data.valid_indices;

      //Function body
      let hyde_rur_grid = fs.existsSync(hyde_rur_path) ?
        this.readCachedGlobalFloat(hyde_rur_path, total_px, cache) : null;
      let popc_masked = (year < 1975) ?
        ViscountUrbanMask.loadUrbanMaskedHYDEPopcRaster(mask_data, year, cache, config) : null;
      let hyde_dens = new Float32Array(n_valid);

      if (hyde_rur_grid || popc_masked) {
        for (let i = 0; i < n_valid; i++) {
          if (perm_ice[i] <= 0.05) continue;
          let gidx = valid_indices[i];
          let r_raw = hyde_rur_grid ? hyde_rur_grid[gidx] : 0;

          if (popc_masked && popc_masked[i] > 0 && (r_raw <= 0 || (uopp && uopp[i] > 3.5 && r_raw < 0.45*popc_masked[i])))
            r_raw = popc_masked[i];
          hyde_dens[i] = Math.max(0, r_raw)/Math.max(1.0, cell_area[i]);
        }
        if (year <= 1890 && n_valid >= 2000 && bio_covs.sub_iso_valid) {
          if (year > 1870)
            hyde_dens = this.removeSubIsoCliffs(mask_data, hyde_dens, bio_covs.sub_iso_valid, 0.005, 4, 0.02, 2.5, false);
          else
            hyde_dens = this.removeSubIsoCliffs(mask_data, hyde_dens, bio_covs.sub_iso_valid, 0.005, 8, 0.06, 6.0, false);
        }
      }

      let h_pop_arr = new Float32Array(n_valid);

      for (let i = 0; i < n_valid; i++)
        h_pop_arr[i] = perm_ice[i]*hyde_dens[i]*cell_area[i];
      if (year <= 1780) {
        for (let i = 0; i < n_valid; i++) out_rur[i] = h_pop_arr[i];

        //Return statement
        return out_rur;
      }

      let ghs_pop_path = path.join(ghs_dir, `GHS_POP_${ghsl_yr}.png`);
      let ghsl_urb_path = path.join(ghsl_urb_dir, `GHSL_${ghsl_yr}.png`);
      let ghs_pop_grid = fs.existsSync(ghs_pop_path) ?
        this.readCachedGlobalFloat(ghs_pop_path, total_px, cache) : null;
      let ghsl_urb_grid = fs.existsSync(ghsl_urb_path) ?
        this.readCachedGlobalUint(ghsl_urb_path, total_px, cache) : null;
      let ghsl_rur = new Float32Array(n_valid);

      if (ghs_pop_grid) {
        let core_mask = new Uint8Array(total_px);
        let full_rur = new Float32Array(total_px);

        for (let i = 0; i < n_valid; i++) {
          if (perm_ice[i] <= 0.05) continue;
          let gidx = valid_indices[i];
          let tot_p = Math.max(0, ghs_pop_grid[gidx]);
          let urb_p = ghsl_urb_grid ? Math.max(0, ghsl_urb_grid[gidx]) : 0;
          let r_raw = Math.max(0, tot_p - Math.min(tot_p*0.88, urb_p));
          let is_heavy_core = (urb_p >= 25000) || (uopp && uopp[i] > 18.0 && tot_p > 15000);

          if (is_heavy_core) core_mask[gidx] = 1;
          else full_rur[gidx] = r_raw;
        }
        let clean_ghsl = ViscountUrbanMask.inpaintUrbanMaskGrid(
          full_rur,
          core_mask,
          mask_data.land_area_grid,
          null,
          mask_data.grid_width,
          mask_data.grid_height,
          3,
          valid_indices,
          null
        );

        for (let i = 0; i < n_valid; i++)
          ghsl_rur[i] = perm_ice[i]*Math.max(0, clean_ghsl[valid_indices[i]]);
      }

      let macro_rad = (year > 1870 && year <= 1890) ? 6 : 12;
      let macro_pass = (year > 1870 && year <= 1890) ? 2 : 3;
      let g_macro = (ghs_pop_grid && year <= 1890) ?
        this.smoothGaussianGrid(mask_data, ghsl_rur, macro_rad, macro_pass, null, false) : null;
      let h_macro = (ghs_pop_grid && year <= 1890) ?
        this.smoothGaussianGrid(mask_data, h_pop_arr, macro_rad, macro_pass, null, false) : null;
      let w_sat = 0.0;

      if (ghs_pop_grid) {
        if (year >= 1975) w_sat = 1.0;
        else if (year <= 1850) w_sat = 0.18*(year - 1780)/70.0;
        else w_sat = 0.18 + 0.82*Math.pow((year - 1850)/125.0, 1.15);
      }
      for (let i = 0; i < n_valid; i++) {
        let h_pop = h_pop_arr[i];

        if (h_pop <= 0 && year < 1900) {
          out_rur[i] = 0;
          continue;
        }
        let g_pop = ghsl_rur[i];

        if (year <= 1890 && g_macro && h_macro)
          g_pop = (g_macro[i] > 1e-4 && h_macro[i] > 0) ? (ghsl_rur[i]*(h_macro[i]/g_macro[i])) : h_pop;
        if (w_sat >= 0.999) {
          out_rur[i] = g_pop;
        } else if (h_pop > 0 && g_pop > 0) {
          out_rur[i] = Math.exp((1 - w_sat)*Math.log(h_pop) + w_sat*Math.log(g_pop));
        } else {
          out_rur[i] = (1 - w_sat)*h_pop + w_sat*g_pop;
        }
      }

      //Return statement
      return out_rur;
    }


    /**
     * Fits nonnegative WLS diagnostic betas (`beta_0_hab > 0`) for Gatekeeper C1 auditability.
     * @alias ViscountHUResidualHelpers.fitDiagnosticsWLSBetas
     */
    static fitDiagnosticsWLSBetas (arg0_bundle, arg1_d_decliff, arg2_z_obs) {
      let bio_covs = arg0_bundle._bio_covs;
      let cell_area = arg0_bundle.mask_data.cell_land_area;
      let cell_obs = arg0_bundle.obs_bundle.cell_nearest_obs;
      let d_decliff = arg1_d_decliff;
      let n_obs = arg0_bundle.obs_bundle.obs_count;
      let n_valid = arg0_bundle.mask_data.valid_cell_count;
      let obs_list = arg0_bundle.obs_bundle.obs_list;
      let r_area = new Float64Array(n_obs);
      let r_x = [new Float64Array(n_obs), new Float64Array(n_obs), new Float64Array(n_obs), new Float64Array(n_obs), new Float64Array(n_obs)];
      let xtx = new Float64Array(25);
      let xty = new Float64Array(5);
      let beta = new Float64Array(5);
      let prior = [0.42, 0.20, 0.12, 0.14, 0.12];

      for (let i = 0; i < n_valid; i++) {
        let o = cell_obs[i];

        if (o < 0 || o >= n_obs || obs_list[o].is_frontier_buffer || d_decliff[i] <= 0) continue;
        let a = cell_area[i];
        let uh = Math.min(3.5, Math.sqrt(d_decliff[i]));

        r_area[o] += a;
        r_x[0][o] += a*uh;
        r_x[1][o] += a*uh*bio_covs.u_nat[i];
        r_x[2][o] += a*uh*bio_covs.u_eco[i];
        r_x[3][o] += a*uh*bio_covs.u_fluvial[i];
        r_x[4][o] += a*uh*bio_covs.u_coastal[i];
      }
      let tot_w = 0;

      for (let o = 0; o < n_obs; o++) {
        if (obs_list[o].is_frontier_buffer || r_area[o] <= 0) continue;
        let inv = 1.0/r_area[o];
        let xv = [r_x[0][o]*inv, r_x[1][o]*inv, r_x[2][o]*inv, r_x[3][o]*inv, r_x[4][o]*inv];

        tot_w += r_area[o];
        for (let r = 0; r < 5; r++) {
          xty[r] += r_area[o]*xv[r]*arg2_z_obs[o];
          for (let c = 0; c < 5; c++) xtx[r*5 + c] += r_area[o]*xv[r]*xv[c];
        }
      }
      let ridge = 0.08*Math.max(1.0, tot_w);

      for (let r = 0; r < 5; r++) {
        xtx[r*5 + r] += ridge;
        xty[r] += ridge*prior[r];
      }
      for (let it = 0; it < 120; it++) {
        for (let r = 0; r < 5; r++) {
          let rhs = xty[r];

          for (let c = 0; c < 5; c++)
            if (c !== r) rhs -= xtx[r*5 + c]*beta[c];
          beta[r] = Math.max(0.01, rhs/Math.max(1e-8, xtx[r*5 + r]));
        }
      }

      //Return statement
      return {
        beta_0_hab: Number(beta[0].toFixed(4)),
        beta_1_nat: Number(beta[1].toFixed(4)),
        beta_2_eco: Number(beta[2].toFixed(4)),
        beta_3_fluvial: Number(beta[3].toFixed(4)),
        beta_4_coastal: Number(beta[4].toFixed(4))
      };
    }


    /**
     * Smooths Laurentide/Cordilleran palaeoglacial envelope for `<= -5500`.
     * @alias ViscountHUResidualHelpers.getLaurentideCordilleranIceFactor
     */
    static getLaurentideCordilleranIceFactor (arg0_mask_data, arg1_vidx, arg2_year) {
      let gidx = arg0_mask_data.valid_indices[arg1_vidx];
      let gw = arg0_mask_data.grid_width;
      let lat = 90 - (Math.floor(gidx/gw) + 0.5)*180/arg0_mask_data.grid_height;
      let lon = -180 + ((gidx % gw) + 0.5)*360/gw;
      let t_r = Math.max(0, Math.min(1, (arg2_year + 10000)/4500));
      let min_lat = 48.0 + t_r*10.5;
      let west_e = -132.0 + t_r*26.0;
      let east_e = -54.0 - t_r*6.0;
      let ds = Math.max(0, Math.min(1, (lat - min_lat)/4.0));
      let dw = Math.max(0, Math.min(1, (lon - (west_e - 8.0))/10.0));
      let de = Math.max(0, Math.min(1, (east_e + 4.0 - lon)/8.0));
      let dn = Math.max(0, Math.min(1, (76.0 - lat)/4.0));
      let core = (0.5*(1 - Math.cos(Math.PI*ds)))*(0.5*(1 - Math.cos(Math.PI*dw)))*de*dn;

      //Return statement
      return Math.max(0.02, 1.0 - 0.96*core);
    }


    /**
     * Delegate: invokes `ViscountDasymetricResidualSolver.A_getOrBuildSparseMaternMatrix`.
     * @alias ViscountHUResidualHelpers.getOrBuildSparseMaternMatrix
     */
    static getOrBuildSparseMaternMatrix (arg0_bundle) {
      return ViscountDasymetricResidualSolver.A_getOrBuildSparseMaternMatrix(arg0_bundle);
    }


    /**
     * Computes cached 8-neighbour chamfer distance in pixels from valid cells to the nearest `sub_iso` border.
     * @alias ViscountHUResidualHelpers.getOrComputeSubIsoBorderDist
     *
     * @param {Object} arg0_mask_data
     * @param {Uint16Array|Uint32Array|Int32Array} arg1_sub_iso
     *
     * @returns {Float32Array}
     */
    static getOrComputeSubIsoBorderDist (arg0_mask_data, arg1_sub_iso) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let sub_iso = arg1_sub_iso;

      //Guard clauses
      if (!mask_data || !sub_iso) return null;
      if (mask_data._sub_iso_border_dist && mask_data._sub_iso_border_dist.length === mask_data.valid_cell_count)
        return mask_data._sub_iso_border_dist;

      //Declare local instance variables
      let buckets = [];
      let d_max = 72;
      let h = mask_data.grid_height;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let tent = new Uint8Array(n_valid).fill(d_max);
      let v_idx = mask_data.valid_indices;
      let w = mask_data.grid_width;

      //Function body
      for (let d = 0; d < d_max; d++) buckets.push([]);
      for (let i = 0; i < n_valid; i++) {
        let pid = sub_iso[i];

        if (pid <= 0) continue;
        let g = v_idx[i];
        let cx = g % w;
        let cy = Math.floor(g/w);
        let is_border = false;
        let nbs = [
          p2v[cy*w + ((cx + w - 1) % w)],
          p2v[cy*w + ((cx + 1) % w)],
          (cy > 0) ? p2v[(cy - 1)*w + cx] : -1,
          (cy + 1 < h) ? p2v[(cy + 1)*w + cx] : -1
        ];

        for (let k = 0; k < 4; k++) {
          let nv = nbs[k];

          if (nv >= 0 && sub_iso[nv] > 0 && sub_iso[nv] !== pid) {
            is_border = true;
            break;
          }
        }
        if (is_border) {
          tent[i] = 0;
          buckets[0].push(i);
        }
      }

      for (let d = 0; d < d_max; d++) {
        let q = buckets[d];

        for (let q_i = 0; q_i < q.length; q_i++) {
          let cur = q[q_i];

          if (d > tent[cur]) continue;
          let g = v_idx[cur];
          let cx = g % w;
          let cy = Math.floor(g/w);

          for (let dy = -1; dy <= 1; dy++) {
            let nr = cy + dy;

            if (nr < 0 || nr >= h) continue;
            for (let dx = -1; dx <= 1; dx++) {
              if (dx === 0 && dy === 0) continue;
              let nv = p2v[nr*w + ((cx + dx + w) % w)];

              if (nv < 0 || sub_iso[nv] <= 0) continue;
              let nd = d + ((dx === 0 || dy === 0) ? 3 : 4);

              if (nd < d_max && nd < tent[nv]) {
                tent[nv] = nd;
                buckets[nd].push(nv);
              }
            }
          }
        }
      }

      let dist = new Float32Array(n_valid);

      for (let i = 0; i < n_valid; i++) dist[i] = tent[i]/3.0;
      mask_data._sub_iso_border_dist = dist;

      //Return statement
      return dist;
    }


    /**
     * Builds and caches a smooth ecological forest-steppe ecotone weight (`0` in forest, `1` in open steppe,
     * feathered across ~110 km with `rad = 12, passes = 3`) so Wild Fields suppression never creates an abrupt
     * binary cliff along the forest-steppe boundary.
     * @alias ViscountHUResidualHelpers.getSmoothOpenSteppeField
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_bio_covs
     *
     * @returns {Float32Array}
     */
    static getSmoothOpenSteppeField (arg0_mask_data, arg1_bio_covs) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let bio_covs = arg1_bio_covs;

      //Guard clauses
      if (!mask_data || !bio_covs || !bio_covs.forest_valid) return null;
      if (bio_covs._smooth_open_steppe) return bio_covs._smooth_open_steppe;

      //Declare local instance variables
      let forest_valid = bio_covs.forest_valid;
      let n_valid = mask_data.valid_cell_count;
      let raw_open = new Float32Array(n_valid);

      //Function body
      for (let i = 0; i < n_valid; i++)
        raw_open[i] = (forest_valid[i] === 0) ? 1.0 : 0.0;
      let smooth_open = this.smoothGaussianGrid(mask_data, raw_open, 12, 3, null, false);

      bio_covs._smooth_open_steppe = smooth_open;

      //Return statement
      return smooth_open;
    }


    /**
     * Interpolates a sorted `[[year, value], ...]` series cleanly with endpoint taper across `tail_years`.
     * @alias ViscountHUResidualHelpers.interpolateSeries
     */
    static interpolateSeries (arg0_series, arg1_year, arg2_tail_years) {
      let pts = arg0_series;
      let yr = arg1_year;
      let tail = (arg2_tail_years !== undefined) ? arg2_tail_years : 80;

      if (!Array.isArray(pts) || pts.length === 0) return 0;
      let y0 = pts[0][0];
      let y1 = pts[pts.length - 1][0];

      if (yr < y0 - tail || yr > y1 + tail) return 0;
      if (yr < y0) {
        let t = (yr - (y0 - tail))/Math.max(1, tail);

        return pts[0][1]*0.5*(1 - Math.cos(Math.PI*t));
      }
      if (yr > y1) {
        let t = (y1 + tail - yr)/Math.max(1, tail);

        return pts[pts.length - 1][1]*0.5*(1 - Math.cos(Math.PI*t));
      }
      for (let i = 0; i < pts.length - 1; i++) {
        let a = pts[i];
        let b = pts[i + 1];

        if (yr >= a[0] && yr <= b[0]) {
          let span = Math.max(1, b[0] - a[0]);

          if (span > 400 && (yr - a[0] > tail && b[0] - yr > tail)) return 0;
          let t = (yr - a[0])/span;

          return a[1]*(1 - t) + b[1]*t;
        }
      }

      //Return statement
      return pts[0][1];
    }


    /**
     * Reads and caches global big-endian float32 raster via `ViscountUrbanMask`.
     * @alias ViscountHUResidualHelpers.readCachedGlobalFloat
     */
    static readCachedGlobalFloat (arg0_path, arg1_total_px, arg2_cache) {
      let ckey = `f32_${arg0_path}`;

      if (arg2_cache && arg2_cache.has(ckey)) return arg2_cache.get(ckey);
      let arr = ViscountUrbanMask.readGlobalFloat32Raster(arg0_path, arg1_total_px);

      if (arg2_cache) {
        this.trimRasterCache(arg2_cache, 20, 14);
        arg2_cache.set(ckey, arr);
      }

      //Return statement
      return arr;
    }


    /**
     * Reads and caches global big-endian uint32 raster via `ViscountUrbanMask`.
     * @alias ViscountHUResidualHelpers.readCachedGlobalUint
     */
    static readCachedGlobalUint (arg0_path, arg1_total_px, arg2_cache) {
      let ckey = `u32_${arg0_path}`;

      if (arg2_cache && arg2_cache.has(ckey)) return arg2_cache.get(ckey);
      let arr = ViscountUrbanMask.readGlobalUint32Raster(arg0_path, arg1_total_px);

      if (arg2_cache) {
        this.trimRasterCache(arg2_cache, 20, 14);
        arg2_cache.set(ckey, arr);
      }

      //Return statement
      return arr;
    }


    /**
     * Removes straight `sub_iso` state/province cliffs using isotropic cross-border Gaussian smoothing
     * feathered by chamfer distance from internal borders (`w_b = 1,0` right on every border) without
     * subtracting state interiors, preventing inverted border steps and urban-inpaint tier spikes.
     * @alias ViscountHUResidualHelpers.removeSubIsoCliffs
     */
    static removeSubIsoCliffs (arg0_mask_data, arg1_field, arg2_sub_iso, arg3_eps, arg4_rad_px, arg5_interior_weight, arg6_border_sigma, arg7_remove_state_offsets, arg8_elev_valid) {
      let border_sigma = (arg6_border_sigma !== undefined) ? arg6_border_sigma : 6.0;
      let elev_valid = arg8_elev_valid || null;
      let eps_cap = (arg3_eps !== undefined) ? arg3_eps : 0.004;
      let field = arg1_field;
      let mask_data = arg0_mask_data;
      let rad_px = (arg4_rad_px !== undefined) ? arg4_rad_px : 14;
      let remove_offsets = (arg7_remove_state_offsets !== undefined) ? Boolean(arg7_remove_state_offsets) : true;
      let sub_iso = arg2_sub_iso;
      let w_int_base = (arg5_interior_weight !== undefined) ? arg5_interior_weight : 0.04;
      let n_valid = mask_data.valid_cell_count;
      let log_f = new Float32Array(n_valid);
      let out = new Float32Array(n_valid);
      let pos_cnt = 0;
      let pos_sum = 0;

      for (let i = 0; i < n_valid; i++) {
        if (field[i] > 0) {
          pos_sum += field[i];
          pos_cnt++;
        }
      }
      if (pos_cnt === 0) return field;
      let dist_b = this.getOrComputeSubIsoBorderDist(mask_data, sub_iso);
      let work_field = field;

      if (remove_offsets && sub_iso) {
        work_field = ViscountUrbanMask.harmoniseSubIsoStateOffsets(mask_data, field, sub_iso, dist_b);
        pos_cnt = 0;
        pos_sum = 0;
        for (let i = 0; i < n_valid; i++) {
          if (work_field[i] > 0) {
            pos_sum += work_field[i];
            pos_cnt++;
          }
        }
      }
      let eps_eff = Math.max(1e-5, Math.min(eps_cap, 0.06*(pos_sum/Math.max(1, pos_cnt))));

      for (let i = 0; i < n_valid; i++)
        if (work_field[i] > 0) log_f[i] = Math.log(work_field[i] + eps_eff);
      let l_iso = this.smoothGaussianGrid(mask_data, log_f, rad_px, 3, null, false, work_field, elev_valid);

      for (let i = 0; i < n_valid; i++) {
        if (work_field[i] <= 0) {
          out[i] = 0;
          continue;
        }
        let d_b = dist_b ? dist_b[i] : 24.0;
        let w_b = w_int_base + (1.0 - w_int_base)*Math.exp(-(d_b*d_b)/(2.0*border_sigma*border_sigma));
        let l_corr = w_b*l_iso[i] + (1.0 - w_b)*log_f[i];

        out[i] = Math.max(0, Math.exp(Math.max(-14, Math.min(12, l_corr))) - eps_eff);
      }

      //Return statement
      return out;
    }


    /**
     * Resolves closest available HYDE raster year suffix (`<year>BC` / `<year>AD`).
     * @alias ViscountHUResidualHelpers.resolveHYDEYearLabel
     */
    static resolveHYDEYearLabel (arg0_year) {
      let yr = Number(arg0_year) || 0;
      let best = -10000;
      let best_d = 1e9;
      let y_list = [
        -10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000,
        0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
        1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790, 1800, 1810, 1820, 1830, 1840, 1850,
        1860, 1870, 1880, 1890, 1900, 1910, 1920, 1930, 1940, 1950
      ];

      for (let y = 1951; y <= 2023; y++) y_list.push(y);
      for (let i = 0; i < y_list.length; i++) {
        let d = Math.abs(y_list[i] - yr);

        if (d < best_d) {
          best_d = d;
          best = y_list[i];
        }
      }

      //Return statement
      return (best < 0) ? `${Math.abs(best)}BC` : `${best}AD`;
    }


    /**
     * Separable multi-pass tent filter (`C^2` isotropic Gaussian approximation) eliminating rectilinear Mach bands.
     * @alias ViscountHUResidualHelpers.smoothGaussianGrid
     */
    static smoothGaussianGrid (arg0_mask_data, arg1_field, arg2_rad_px, arg3_passes, arg4_part_ids, arg5_pos_only, arg6_active_gate, arg7_elev_valid) {
      let mask_data = arg0_mask_data;
      let rad = Math.max(1, arg2_rad_px || 4);
      let passes = Math.max(1, arg3_passes || 3);
      let part_ids = arg4_part_ids;
      let pos_only = Boolean(arg5_pos_only);
      let gate = arg6_active_gate;
      let elev_v = arg7_elev_valid || null;
      let h = mask_data.grid_height;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let v_idx = mask_data.valid_indices;
      let w = mask_data.grid_width;
      let cur = Float32Array.from(arg1_field);
      let tmp = new Float32Array(n_valid);

      for (let p = 0; p < passes; p++) {
        for (let i = 0; i < n_valid; i++) {
          if (gate && gate[i] <= 0) { tmp[i] = cur[i]; continue; }
          if (pos_only && cur[i] <= 0) { tmp[i] = 0; continue; }
          let cx = v_idx[i] % w;
          let ei = elev_v ? elev_v[i] : 0;
          let row = Math.floor(v_idx[i]/w)*w;
          let pid = part_ids ? part_ids[i] : 0;
          let acc = 0;
          let wsum = 0;

          for (let dx = -rad; dx <= rad; dx++) {
            let nv = p2v[row + ((cx + dx + w) % w)];

            if (nv < 0) continue;
            if (gate && gate[nv] <= 0) continue;
            if (pos_only && cur[nv] <= 0) continue;
            if (part_ids && pid > 0 && part_ids[nv] !== pid) continue;
            let wt = rad + 1 - Math.abs(dx);

            if (elev_v) {
              let de = Math.abs(ei - elev_v[nv]);

              if (de > 450.0) wt *= Math.exp(-(de - 450.0)/220.0);
            }
            acc += cur[nv]*wt;
            wsum += wt;
          }
          tmp[i] = (wsum > 0) ? (acc/wsum) : cur[i];
        }
        for (let i = 0; i < n_valid; i++) {
          if (gate && gate[i] <= 0) { cur[i] = tmp[i]; continue; }
          if (pos_only && arg1_field[i] <= 0) { cur[i] = 0; continue; }
          let cx = v_idx[i] % w;
          let cy = Math.floor(v_idx[i]/w);
          let ei = elev_v ? elev_v[i] : 0;
          let pid = part_ids ? part_ids[i] : 0;
          let acc = 0;
          let wsum = 0;

          for (let dy = -rad; dy <= rad; dy++) {
            let nr = cy + dy;

            if (nr < 0 || nr >= h) continue;
            let nv = p2v[nr*w + cx];

            if (nv < 0) continue;
            if (gate && gate[nv] <= 0) continue;
            if (pos_only && tmp[nv] <= 0) continue;
            if (part_ids && pid > 0 && part_ids[nv] !== pid) continue;
            let wt = rad + 1 - Math.abs(dy);

            if (elev_v) {
              let de = Math.abs(ei - elev_v[nv]);

              if (de > 450.0) wt *= Math.exp(-(de - 450.0)/220.0);
            }
            acc += tmp[nv]*wt;
            wsum += wt;
          }
          cur[i] = (wsum > 0) ? (acc/wsum) : tmp[i];
        }
      }

      //Return statement
      return cur;
    }


    /**
     * Delegate: invokes `ViscountDasymetricResidualSolver.B_solveResidualDualWeights`.
     * @alias ViscountHUResidualHelpers.solveResidualDualWeights
     */
    static solveResidualDualWeights (arg0_kriging_bundle, arg1_prior_bundle, arg2_z_obs, arg3_s_obs) {
      return ViscountDasymetricResidualSolver.B_solveResidualDualWeights(arg0_kriging_bundle, arg1_prior_bundle, arg2_z_obs, arg3_s_obs);
    }


    /**
     * Blends precomputed Terra Preta (ADE) anthropogenic dark-earth density into tropical Amazonia/Guianas
     * (`-5000..1750 AD`, `lat >= -19`), strictly conserving Amazonian mass within `hab_mask`.
     * @alias ViscountHUResidualHelpers.blendTerraPretaSurface
     */
    static blendTerraPretaSurface (arg0_rk_pop, arg1_tp_norm, arg2_tp_lat_w, arg3_year) {
      let rk_pop = arg0_rk_pop;
      let tp_norm = arg1_tp_norm;
      let tp_lat_w = arg2_tp_lat_w;
      let yr = Number(arg3_year) || 0;

      if (!rk_pop || !tp_norm || !tp_lat_w || yr < -5000 || yr > 1750) return;
      let w_tp = 0.0;

      if (yr < -1000) w_tp = 0.14*(yr + 5000)/4000;
      else if (yr < 1000) w_tp = 0.14 + 0.22*(yr + 1000)/2000;
      else if (yr <= 1550) w_tp = 0.36;
      else w_tp = 0.36*Math.max(0, (1750 - yr)/200);
      if (w_tp <= 0) return;

      let amz_sum = 0;

      for (let i = 0; i < rk_pop.length; i++)
        if (tp_lat_w[i] > 0) amz_sum += rk_pop[i]*tp_lat_w[i];
      if (amz_sum <= 0) return;
      for (let i = 0; i < rk_pop.length; i++) {
        let wl = tp_lat_w[i];

        if (wl > 0) rk_pop[i] = rk_pop[i]*(1 - w_tp*wl) + tp_norm[i]*amz_sum*w_tp;
      }
    }


    /**
     * Writes a valid-cell Float32Array to a big-endian IEEE-754 float32 RGBA GeoPNG.
     * @alias ViscountHUResidualHelpers.writeFloat32GeoPNG
     */
    static writeFloat32GeoPNG (arg0_mask_data, arg1_field, arg2_out_path) {
      let mask_data = arg0_mask_data;
      let field = arg1_field;
      let f_buf = new ArrayBuffer(4);
      let f_dv = new DataView(f_buf);
      let img = new PNG({ colorType: 6, height: mask_data.grid_height, width: mask_data.grid_width });
      let valid_indices = mask_data.valid_indices;

      for (let i = 0; i < mask_data.valid_cell_count; i++) {
        if (field[i] > 0) {
          let px = valid_indices[i]*4;

          f_dv.setFloat32(0, field[i], false);
          img.data[px] = f_dv.getUint8(0);
          img.data[px + 1] = f_dv.getUint8(1);
          img.data[px + 2] = f_dv.getUint8(2);
          img.data[px + 3] = f_dv.getUint8(3);
        }
      }
      fs.writeFileSync(arg2_out_path, PNG.sync.write(img, { colorType: 6, deflateLevel: 6 }));
    }


    /**
     * Evicts oldest transient raster buffers from the shared cache whilst preserving `__modern_urban_mask__`.
     * @alias ViscountHUResidualHelpers.trimRasterCache
     */
    static trimRasterCache (arg0_cache, arg1_max_size, arg2_target_size) {
      let cache = arg0_cache;
      let max_size = (arg1_max_size !== undefined) ? arg1_max_size : 20;
      let target_size = (arg2_target_size !== undefined) ? arg2_target_size : 14;

      if (!cache || cache.size <= max_size) return;
      let keys = Array.from(cache.keys());

      for (let i = 0; i < keys.length; i++) {
        if (cache.size <= target_size) break;
        if (keys[i] !== "__modern_urban_mask__")
          cache.delete(keys[i]);
      }
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountHUResidualHelpers: global.ViscountHUResidualHelpers };
