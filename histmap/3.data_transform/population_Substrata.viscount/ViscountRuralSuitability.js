//Import modules
let { ViscountUrbanMask } = global.ViscountUrbanMask ? global : require("./ViscountUrbanMask.js");

//Initialise functions
{
  /**
   * 5-arcminute (`4320x2160`) Urban-Masked HYDE Rural De-Cliffer, Palaeoglacial Envelope Helper,
   * Field Smoother and Constrained NNLS Residual Kriging Synthesizer for Operation Viscount.
   *
   * @class ViscountRuralSuitability
   */
  global.ViscountRuralSuitability = class {
    /**
     * Caps prehistoric intensity inside modern urban cores (`uopp_2023AD > 8.0`) to a ceiling multiple
     * of the surrounding non-urban habitable ring (`3..7 px`) so modern CRM metropolitan salvage does not back-project.
     * @alias ViscountRuralSuitability.capUrbanCoreToRuralRing
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_field
     * @param {Float32Array} arg2_uopp_valid
     * @param {number} [arg3_max_mult=1.15]
     */
    static capUrbanCoreFieldToRuralRing (arg0_mask_data, arg1_field, arg2_uopp_valid, arg3_max_mult) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let field = arg1_field;
      let uopp_valid = arg2_uopp_valid;
      let max_mult = (arg3_max_mult !== undefined) ? arg3_max_mult : 1.15;

      //Guard clauses
      if (!mask_data || !field || !uopp_valid) return;

      //Declare local instance variables
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let rural_only = new Float32Array(n_valid);
      let v_idx = mask_data.valid_indices;

      //Function body
      for (let i = 0; i < n_valid; i++)
        if (field[i] > 0 && uopp_valid[i] <= 4.0)
          rural_only[i] = field[i];

      let rural_mean = this.smoothPositiveFieldOnGrid(mask_data, rural_only, 6);

      for (let i = 0; i < n_valid; i++) {
        if (field[i] <= 0 || uopp_valid[i] <= 8.0) continue;
        let gidx = v_idx[i];
        let cx = gidx % grid_w;
        let cy = Math.floor(gidx/grid_w);
        let ring_ref = rural_mean[i];

        if (ring_ref <= 0) {
          let acc = 0;
          let cnt = 0;

          for (let dy = -7; dy <= 7; dy++) {
            let ny = cy + dy;

            if (ny < 0 || ny >= grid_h) continue;
            for (let dx = -7; dx <= 7; dx++) {
              let nv = p2v[ny*grid_w + ((cx + dx + grid_w) % grid_w)];

              if (nv >= 0 && field[nv] > 0 && uopp_valid[nv] <= 6.0) {
                acc += field[nv];
                cnt++;
              }
            }
          }
          if (cnt > 0) ring_ref = acc/cnt;
        }
        if (ring_ref > 0 && field[i] > ring_ref*max_mult)
          field[i] = ring_ref*max_mult;
      }
    }


    /**
     * Computes composite de-cliffed urban-masked HYDE rural habitation `u_hab(x)` for a chronological period.
     * @alias ViscountRuralSuitability.computeCompositeHabitationField
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_obs_bundle
     * @param {Object} arg2_covs
     * @param {Object} arg3_period_cfg
     * @param {Object} arg4_config
     * @param {Map} arg5_hab_cache
     *
     * @returns {Float32Array}
     */
    static computeCompositeHabitationField (arg0_mask_data, arg1_obs_bundle, arg2_covs, arg3_period_cfg, arg4_config, arg5_hab_cache) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let obs_bundle = arg1_obs_bundle;
      let covs = arg2_covs;
      let period_cfg = arg3_period_cfg;
      let config = arg4_config;
      let hab_cache = arg5_hab_cache;

      //Declare local instance variables
      let hyde_years = (config.kriging_config && config.kriging_config.all_hyde_years) ?
        config.kriging_config.all_hyde_years : [0, 900, 1500];
      let matched = [];
      let n_valid = mask_data.valid_cell_count;
      let out = new Float32Array(n_valid);
      let p_end = Number.isFinite(period_cfg.approx_end_year) ? period_cfg.approx_end_year : period_cfg.end_year;
      let p_start = Number.isFinite(period_cfg.approx_start_year) ? period_cfg.approx_start_year : period_cfg.start_year;
      let rep_years = [];

      //Function body
      if (Number.isFinite(p_start) && Number.isFinite(p_end)) {
        for (let i = 0; i < hyde_years.length; i++)
          if (hyde_years[i] >= p_start && hyde_years[i] <= p_end)
            matched.push(hyde_years[i]);
      }
      if (matched.length === 0 && Number.isFinite(period_cfg.representative_year)) {
        let best_y = hyde_years[0];
        let best_d = Math.abs(best_y - period_cfg.representative_year);

        for (let i = 1; i < hyde_years.length; i++) {
          let d = Math.abs(hyde_years[i] - period_cfg.representative_year);

          if (d < best_d) {
            best_d = d;
            best_y = hyde_years[i];
          }
        }
        matched.push(best_y);
      }
      if (matched.length === 0) matched = [0, 1000];

      rep_years.push(matched[0]);
      if (matched.length > 2) rep_years.push(matched[Math.floor(matched.length/2)]);
      if (matched.length > 1) rep_years.push(matched[matched.length - 1]);

      for (let i = 0; i < rep_years.length; i++) {
        let u_yr = this.computeDeCliffedHabitationField(mask_data, obs_bundle, covs, rep_years[i], config, hab_cache);

        for (let x = 0; x < n_valid; x++)
          out[x] += u_yr[x]/rep_years.length;
      }

      //Return statement
      return out;
    }


    /**
     * Computes within-partition de-cliffed urban-masked HYDE rural habitation `u_hab,t(x)` for year t.
     * @alias ViscountRuralSuitability.computeDeCliffedHabitationField
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_obs_bundle
     * @param {Object} arg2_covs
     * @param {number} arg3_year
     * @param {Object} arg4_config
     * @param {Map} [arg5_hab_cache]
     *
     * @returns {Float32Array}
     */
    static computeDeCliffedHabitationField (arg0_mask_data, arg1_obs_bundle, arg2_covs, arg3_year, arg4_config, arg5_hab_cache) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let obs_bundle = arg1_obs_bundle;
      let covs = arg2_covs;
      let year = arg3_year;
      let config = arg4_config;
      let hab_cache = arg5_hab_cache;

      //Guard clauses
      if (hab_cache && hab_cache.has(year)) return hab_cache.get(year);

      //Declare local instance variables
      let cell_area = mask_data.cell_land_area;
      let dist_site_px = covs.dist_site_px;
      let hab_ind = new Float32Array(mask_data.valid_cell_count);
      let hab_mask = covs.hab_mask;
      let hyde_rur = this.loadUrbanMaskedHYDEPopcRaster(mask_data, year, hab_cache, config);
      let hyde_rur_1900 = covs.hyde_rur_1900;
      let is_micro_island = (mask_data.valid_cell_count < 2000);
      let min_area = 0.75*mask_data.mean_cell_land_area_km2;
      let n_parts = covs.partition_count;
      let n_valid = mask_data.valid_cell_count;
      let part_cnt = new Int32Array(n_parts);
      let part_id = covs.part_id;
      let part_sum = new Float64Array(n_parts);
      let perm_ice = covs.perm_ice;
      let raw_sqrt = new Float32Array(n_valid);
      let u_coastal = covs.u_coastal;
      let u_fluvial = covs.u_fluvial;
      let u_hab = new Float32Array(n_valid);
      let u_nat = covs.u_nat;

      //Function body
      for (let i = 0; i < n_valid; i++) {
        let is_hab = hab_mask ? (hab_mask[i] === 1) : ((perm_ice && perm_ice[i] > 0.05) && (!dist_site_px || dist_site_px[i] <= 5.5));

        if (!is_hab) continue;
        let local_area = Math.max(min_area, cell_area[i]);
        let d = (hyde_rur) ? hyde_rur[i]/local_area : 0;
        let d_site = dist_site_px ? dist_site_px[i] : 99.0;

        if (d < 0.002) {
          if (is_micro_island) {
            let r19 = hyde_rur_1900 ? (hyde_rur_1900[i]/local_area) : 0;
            let bio = (0.55*u_fluvial[i] + 0.45*u_coastal[i])*u_nat[i];

            d = Math.max(d, 0.22*r19 + 0.06*bio + 0.004);
          } else if (d_site <= 5.5) {
            let r19 = hyde_rur_1900 ? (hyde_rur_1900[i]/local_area) : 0;
            let rad_taper = Math.exp(-0.55*d_site);
            let oasis = Math.max(0.004, 0.10*r19 + 0.018*(0.65*u_fluvial[i] + 0.35*u_coastal[i]));

            d = Math.max(d, rad_taper*oasis);
          } else {
            d = 0;
          }
        }

        if (d > 0) {
          let pid = part_id[i];
          let s = Math.sqrt(d);

          hab_ind[i] = 1;
          raw_sqrt[i] = s;
          part_cnt[pid]++;
          part_sum[pid] += s;
        }
      }

      let f_smooth = this.smoothValidFieldOnGrid(mask_data, hab_ind, 2);
      let decliffed = this.smoothWithinPartitionPositive(mask_data, raw_sqrt, part_id, part_sum, part_cnt, 12);

      for (let i = 0; i < n_valid; i++)
        if (raw_sqrt[i] > 0 && decliffed[i] > 0)
          u_hab[i] = Math.sqrt(Math.max(0, f_smooth[i]))*decliffed[i];

      if (hab_cache) hab_cache.set(year, u_hab);

      //Return statement
      return u_hab;
    }


    /**
     * Fits constrained NNLS covariates (`u_hab`, `u_nat`, `u_eco`, `u_fluvial`, `u_coastal`) per horizon
     * and computes high-sharpness within-macro contrast weights paired with palaeoglacial & ice-cap envelopes.
     * @alias ViscountRuralSuitability.computeResidualKrigingWeights
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_obs_bundle
     * @param {Object} arg2_covs
     * @param {Float32Array} arg3_u_hab
     * @param {Float64Array} arg4_z_obs
     * @param {number} arg5_meso_px
     * @param {number} arg6_rep_year
     * @param {Object} arg7_config
     *
     * @returns {Object}
     */
    static computeResidualKrigingWeights (arg0_mask_data, arg1_obs_bundle, arg2_covs, arg3_u_hab, arg4_z_obs, arg5_meso_px, arg6_rep_year, arg7_config) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let obs_bundle = arg1_obs_bundle;
      let covs = arg2_covs;
      let u_hab = arg3_u_hab;
      let z_obs = arg4_z_obs;
      let meso_px = arg5_meso_px;
      let rep_year = arg6_rep_year;
      let config = arg7_config;

      //Declare local instance variables
      let apply_ice = Boolean(config && config.kriging_config && config.kriging_config.apply_ice_sheet_mask);
      let beta = new Float64Array(5);
      let beta_prior = [0.30, 0.22, 0.12, 0.22, 0.14];
      let cell_area = mask_data.cell_land_area;
      let cell_obs = obs_bundle.cell_nearest_obs;
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let hab_mask = covs.hab_mask;
      let m_cell = new Float32Array(mask_data.valid_cell_count);
      let macro_rad = Math.max(7, Math.min(13, Math.round(0.70*meso_px)));
      let n_covs = 5;
      let n_obs = obs_bundle.obs_count;
      let n_valid = mask_data.valid_cell_count;
      let obs_list = obs_bundle.obs_list;
      let perm_ice = covs.perm_ice;
      let pos_u_cnt = 0;
      let pos_u_sum = 0;
      let r_area = new Float64Array(n_obs);
      let r_covs = [
        new Float64Array(n_obs),
        new Float64Array(n_obs),
        new Float64Array(n_obs),
        new Float64Array(n_obs),
        new Float64Array(n_obs)
      ];
      let total_dom_w = 0;
      let u_coastal = covs.u_coastal;
      let u_eco = covs.u_eco;
      let u_fluvial = covs.u_fluvial;
      let u_nat = covs.u_nat;
      let uopp_valid = covs.uopp_valid;
      let v_idx = mask_data.valid_indices;
      let weights = new Float32Array(n_valid);
      let xtx = new Float64Array(25);
      let xty = new Float64Array(5);

      //Function body
      for (let i = 0; i < n_valid; i++) {
        if (u_hab[i] > 0) {
          pos_u_sum += u_hab[i];
          pos_u_cnt++;
        }
      }
      let mean_u_hab = Math.max(1e-4, pos_u_sum/Math.max(1, pos_u_cnt));

      for (let i = 0; i < n_valid; i++) {
        let a = cell_area[i]*perm_ice[i];
        let o = cell_obs[i];

        if (o < 0 || o >= n_obs || obs_list[o].is_frontier_buffer || a <= 0) continue;
        if (hab_mask && hab_mask[i] === 0) continue;
        let uh = Math.min(4.0, u_hab[i]/mean_u_hab);

        if (uh <= 0) continue;
        r_area[o] += a;
        r_covs[0][o] += a*uh;
        r_covs[1][o] += a*uh*u_nat[i];
        r_covs[2][o] += a*uh*u_eco[i];
        r_covs[3][o] += a*uh*u_fluvial[i];
        r_covs[4][o] += a*uh*u_coastal[i];
      }

      for (let o = 0; o < n_obs; o++) {
        if (obs_list[o].is_frontier_buffer || r_area[o] <= 0) continue;
        let inv_a = 1.0/r_area[o];
        let xv = [
          r_covs[0][o]*inv_a,
          r_covs[1][o]*inv_a,
          r_covs[2][o]*inv_a,
          r_covs[3][o]*inv_a,
          r_covs[4][o]*inv_a
        ];
        let y = z_obs[o];
        let w = r_area[o];

        total_dom_w += w;
        for (let r = 0; r < n_covs; r++) {
          xty[r] += w*xv[r]*y;
          for (let c = 0; c < n_covs; c++)
            xtx[r*n_covs + c] += w*xv[r]*xv[c];
        }
      }

      //Weak positive Tikhonov shrinkage toward biophysical priors ensures non-zero beta_0_hab under collinearity
      let ridge_alpha = 0.06*Math.max(1.0, total_dom_w);

      for (let r = 0; r < n_covs; r++) {
        xtx[r*n_covs + r] += ridge_alpha;
        xty[r] += ridge_alpha*beta_prior[r];
      }

      for (let iter = 0; iter < 300; iter++) {
        for (let r = 0; r < n_covs; r++) {
          let diag = xtx[r*n_covs + r];
          let rhs = xty[r];

          for (let c = 0; c < n_covs; c++)
            if (c !== r) rhs -= xtx[r*n_covs + c]*beta[c];
          beta[r] = (diag > 1e-12) ? Math.max(1e-3, rhs/diag) : 1e-3;
        }
      }

      let b_sum = Math.max(1e-8, beta[0] + beta[1] + beta[2] + beta[3] + beta[4]);
      let global_m_cnt = 0;
      let global_m_sum = 0;
      let ice_env_arr = new Float32Array(n_valid);
      let w0 = 0.45*(beta[0]/b_sum) + 0.14;
      let w1 = 0.45*(beta[1]/b_sum) + 0.14;
      let w2 = 0.45*(beta[2]/b_sum) + 0.06;
      let w3 = 0.45*(beta[3]/b_sum) + 0.16;
      let w4 = 0.45*(beta[4]/b_sum) + 0.05;

      for (let i = 0; i < n_valid; i++) {
        let ice_env = perm_ice[i];

        if (apply_ice && rep_year <= -5500) {
          let gidx = v_idx[i];
          let lat = 90 - (Math.floor(gidx/grid_w) + 0.5)*180/grid_h;
          let lon = -180 + ((gidx % grid_w) + 0.5)*360/grid_w;

          ice_env *= this.getLaurentideCordilleranIceFactor(lat, lon, rep_year);
        }
        ice_env_arr[i] = ice_env;

        if ((hab_mask && hab_mask[i] === 0) || u_hab[i] <= 0 || ice_env <= 0.04) {
          m_cell[i] = 0;
          continue;
        }

        let uh_norm = Math.min(4.0, u_hab[i]/mean_u_hab);
        let mult_env = w0 + w1*u_nat[i] + w2*u_eco[i] + w3*2.40*u_fluvial[i] + w4*1.85*u_coastal[i];
        let mc = Math.pow(Math.max(0.01, uh_norm), 0.85)*Math.max(1e-4, mult_env);

        m_cell[i] = mc;
        global_m_sum += mc;
        global_m_cnt++;
      }

      let global_m_mean = (global_m_cnt > 0) ? (global_m_sum/global_m_cnt) : 1.0;
      let m_macro = this.smoothPositiveFieldOnGrid(mask_data, m_cell, macro_rad);
      let sharp_exp = 2.15;

      for (let i = 0; i < n_valid; i++) {
        if (m_cell[i] <= 0) {
          weights[i] = 0;
          continue;
        }
        let ref_macro = (m_macro[i] > 0) ? (0.55*m_macro[i] + 0.45*global_m_mean) : global_m_mean;
        let ratio = Math.max(0.0, Math.min(3.50, m_cell[i]/Math.max(1e-6, ref_macro)));

        weights[i] = ice_env_arr[i]*Math.pow(ratio, sharp_exp);
      }

      if (rep_year <= 1650 && uopp_valid)
        this.capUrbanCoreFieldToRuralRing(mask_data, weights, uopp_valid, 1.15);

      //Return statement
      return {
        beta: [
          Number(beta[0].toFixed(4)),
          Number(beta[1].toFixed(4)),
          Number(beta[2].toFixed(4)),
          Number(beta[3].toFixed(4)),
          Number(beta[4].toFixed(4))
        ],
        weights: weights
      };
    }


    /**
     * Evaluates smooth Laurentide & Cordilleran palaeoglacial habitability factor in `[0,02, 1,0]` for `-13000..-5500`.
     * @alias ViscountRuralSuitability.getLaurentideCordilleranIceFactor
     *
     * @param {number} arg0_lat
     * @param {number} arg1_lon
     * @param {number} arg2_year
     *
     * @returns {number}
     */
    static getLaurentideCordilleranIceFactor (arg0_lat, arg1_lon, arg2_year) {
      //Convert from parameters
      let lat = arg0_lat;
      let lon = arg1_lon;
      let year = arg2_year;

      //Guard clauses
      if (year > -5500) return 1.0;

      //Declare local instance variables
      let t_retreat = Math.max(0, Math.min(1, (year + 10000)/4500));
      let min_ice_lat = 48.0 + t_retreat*10.5;
      let west_edge = -132.0 + t_retreat*26.0;
      let east_edge = -54.0 - t_retreat*6.0;

      //Function body
      let d_s = Math.max(0, Math.min(1, (lat - min_ice_lat)/4.0));
      let d_w = Math.max(0, Math.min(1, (lon - (west_edge - 8.0))/10.0));
      let d_e = Math.max(0, Math.min(1, (east_edge + 4.0 - lon)/8.0));
      let d_n = Math.max(0, Math.min(1, (76.0 - lat)/4.0));
      let core = (0.5*(1 - Math.cos(Math.PI*d_s)))*(0.5*(1 - Math.cos(Math.PI*d_w)))*d_e*d_n;

      //Return statement
      return Math.max(0.02, 1.0 - 0.96*core);
    }


    /**
     * Builds or retrieves the cached extended modern urban buffer mask via `ViscountUrbanMask`.
     * @alias ViscountRuralSuitability.getModernUrbanMask
     *
     * @param {Object} arg0_mask_data
     * @param {Object} [arg1_config]
     * @param {Map} [arg2_cache]
     *
     * @returns {Uint8Array}
     */
    static getModernUrbanMask (arg0_mask_data, arg1_config, arg2_cache) {
      return ViscountUrbanMask.getModernUrbanMask(arg0_mask_data, arg1_config, arg2_cache);
    }


    /**
     * Inpaints masked urban/spike/reservoir pixels from surrounding rural cells via `ViscountUrbanMask`.
     * @alias ViscountRuralSuitability.inpaintUrbanMaskGrid
     *
     * @param {Float32Array} arg0_popc_grid
     * @param {Uint8Array} arg1_urban_mask
     * @param {Float32Array} arg2_land_area_grid
     * @param {Float32Array|null} arg3_fallback_grid
     * @param {number} arg4_grid_width
     * @param {number} arg5_grid_height
     * @param {number} [arg6_inpaint_radius]
     * @param {Int32Array} [arg7_target_indices]
     *
     * @returns {Float32Array}
     */
    static inpaintUrbanMaskGrid (
      arg0_popc_grid,
      arg1_urban_mask,
      arg2_land_area_grid,
      arg3_fallback_grid,
      arg4_grid_width,
      arg5_grid_height,
      arg6_inpaint_radius,
      arg7_target_indices
    ) {
      return ViscountUrbanMask.inpaintUrbanMaskGrid(
        arg0_popc_grid,
        arg1_urban_mask,
        arg2_land_area_grid,
        arg3_fallback_grid,
        arg4_grid_width,
        arg5_grid_height,
        arg6_inpaint_radius,
        arg7_target_indices
      );
    }


    /**
     * Loads urban-masked HYDE 3.5 rural population raster over valid cells, inpainting modern urban sprawl pixels via `ViscountUrbanMask`.
     * @alias ViscountRuralSuitability.loadUrbanMaskedHYDEPopcRaster
     *
     * @param {Object} arg0_mask_data
     * @param {number} arg1_year
     * @param {Map} [arg2_cache]
     * @param {Object} [arg3_config]
     *
     * @returns {Float32Array}
     */
    static loadUrbanMaskedHYDEPopcRaster (arg0_mask_data, arg1_year, arg2_cache, arg3_config) {
      return ViscountUrbanMask.loadUrbanMaskedHYDEPopcRaster(arg0_mask_data, arg1_year, arg2_cache, arg3_config);
    }


    /**
     * Reads a full 4320x2160 big-endian float32 GeoPNG into a flat Float32Array via `ViscountUrbanMask`.
     * @alias ViscountRuralSuitability.readGlobalFloat32Raster
     *
     * @param {string} arg0_file_path
     * @param {number} arg1_total_pixels
     *
     * @returns {Float32Array}
     */
    static readGlobalFloat32Raster (arg0_file_path, arg1_total_pixels) {
      return ViscountUrbanMask.readGlobalFloat32Raster(arg0_file_path, arg1_total_pixels);
    }


    /**
     * Smooths positive values across valid mask cells with a two-pass separable 2D box filter.
     * @alias ViscountRuralSuitability.smoothPositiveFieldOnGrid
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_valid_field
     * @param {number} arg2_radius_px
     *
     * @returns {Float32Array}
     */
    static smoothPositiveFieldOnGrid (arg0_mask_data, arg1_valid_field, arg2_radius_px) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let valid_field = arg1_valid_field;
      let radius_px = arg2_radius_px;

      //Declare local instance variables
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let n_valid = mask_data.valid_cell_count;
      let h_cnt = new Int32Array(n_valid);
      let h_sum = new Float32Array(n_valid);
      let out = new Float32Array(n_valid);
      let p2v = mask_data.pixel_to_valid_idx;
      let v_idx = mask_data.valid_indices;

      //Function body
      for (let i = 0; i < n_valid; i++) {
        if (valid_field[i] <= 0) continue;
        let cx = v_idx[i] % grid_w;
        let row = Math.floor(v_idx[i]/grid_w)*grid_w;
        let acc = 0;
        let cnt = 0;
        let x0 = Math.max(0, cx - radius_px);
        let x1 = Math.min(grid_w - 1, cx + radius_px);

        for (let x = x0; x <= x1; x++) {
          let nv = p2v[row + x];

          if (nv >= 0 && valid_field[nv] > 0) {
            acc += valid_field[nv];
            cnt++;
          }
        }
        h_cnt[i] = cnt;
        h_sum[i] = acc;
      }

      for (let i = 0; i < n_valid; i++) {
        if (valid_field[i] <= 0) continue;
        let cx = v_idx[i] % grid_w;
        let cy = Math.floor(v_idx[i]/grid_w);
        let acc = 0;
        let cnt = 0;
        let y0 = Math.max(0, cy - radius_px);
        let y1 = Math.min(grid_h - 1, cy + radius_px);

        for (let y = y0; y <= y1; y++) {
          let nv = p2v[y*grid_w + cx];

          if (nv >= 0 && h_cnt[nv] > 0) {
            acc += h_sum[nv];
            cnt += h_cnt[nv];
          }
        }
        out[i] = (cnt > 0) ? acc/cnt : valid_field[i];
      }

      //Return statement
      return out;
    }


    /**
     * Smooths a valid-cell array over the 2D mask using a separable box filter.
     * @alias ViscountRuralSuitability.smoothValidFieldOnGrid
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_valid_field
     * @param {number} arg2_radius_px
     *
     * @returns {Float32Array}
     */
    static smoothValidFieldOnGrid (arg0_mask_data, arg1_valid_field, arg2_radius_px) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let valid_field = arg1_valid_field;
      let radius_px = arg2_radius_px;

      //Declare local instance variables
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let n_valid = mask_data.valid_cell_count;
      let h_pass = new Float32Array(n_valid);
      let out = new Float32Array(n_valid);
      let p2v = mask_data.pixel_to_valid_idx;
      let v_idx = mask_data.valid_indices;

      //Function body
      for (let i = 0; i < n_valid; i++) {
        let gidx = v_idx[i];
        let r_off = Math.floor(gidx/grid_w)*grid_w;
        let cx = gidx % grid_w;
        let acc = 0;
        let cnt = 0;

        for (let dc = -radius_px; dc <= radius_px; dc++) {
          let nv = p2v[r_off + ((cx + dc + grid_w) % grid_w)];

          if (nv >= 0) {
            acc += valid_field[nv];
            cnt++;
          }
        }
        h_pass[i] = (cnt > 0) ? acc/cnt : valid_field[i];
      }

      for (let i = 0; i < n_valid; i++) {
        let gidx = v_idx[i];
        let cx = gidx % grid_w;
        let cy = Math.floor(gidx/grid_w);
        let acc = 0;
        let cnt = 0;

        for (let dr = -radius_px; dr <= radius_px; dr++) {
          let nr = cy + dr;

          if (nr >= 0 && nr < grid_h) {
            let nv = p2v[nr*grid_w + cx];

            if (nv >= 0) {
              acc += h_pass[nv];
              cnt++;
            }
          }
        }
        out[i] = (cnt > 0) ? acc/cnt : h_pass[i];
      }

      //Return statement
      return out;
    }


    /**
     * Normalises positive values within each sub_iso/Nelson partition to eliminate HYDE administrative cliffs.
     * @alias ViscountRuralSuitability.smoothWithinPartitionPositive
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_valid_field
     * @param {Int32Array} arg2_part_id
     * @param {Float64Array} arg3_part_sum
     * @param {Int32Array} arg4_part_cnt
     * @param {number} arg5_radius_px
     *
     * @returns {Float32Array}
     */
    static smoothWithinPartitionPositive (arg0_mask_data, arg1_valid_field, arg2_part_id, arg3_part_sum, arg4_part_cnt, arg5_radius_px) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let valid_field = arg1_valid_field;
      let part_id = arg2_part_id;
      let part_sum = arg3_part_sum;
      let part_cnt = arg4_part_cnt;
      let radius_px = arg5_radius_px;

      //Declare local instance variables
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let n_valid = mask_data.valid_cell_count;
      let h_cnt = new Int32Array(n_valid);
      let h_sum = new Float32Array(n_valid);
      let out = new Float32Array(n_valid);
      let p2v = mask_data.pixel_to_valid_idx;
      let v_idx = mask_data.valid_indices;

      //Function body
      for (let i = 0; i < n_valid; i++) {
        if (valid_field[i] <= 0) continue;
        let cx = v_idx[i] % grid_w;
        let pid = part_id[i];
        let r_off = Math.floor(v_idx[i]/grid_w)*grid_w;
        let acc = 0;
        let cnt = 0;
        let x0 = Math.max(0, cx - radius_px);
        let x1 = Math.min(grid_w - 1, cx + radius_px);

        for (let x = x0; x <= x1; x++) {
          let nv = p2v[r_off + x];

          if (nv >= 0 && part_id[nv] === pid && valid_field[nv] > 0) {
            acc += valid_field[nv];
            cnt++;
          }
        }
        h_cnt[i] = cnt;
        h_sum[i] = acc;
      }

      for (let i = 0; i < n_valid; i++) {
        if (valid_field[i] <= 0) continue;
        let cx = v_idx[i] % grid_w;
        let cy = Math.floor(v_idx[i]/grid_w);
        let pid = part_id[i];
        let acc = 0;
        let cnt = 0;
        let y0 = Math.max(0, cy - radius_px);
        let y1 = Math.min(grid_h - 1, cy + radius_px);

        for (let y = y0; y <= y1; y++) {
          let nv = p2v[y*grid_w + cx];

          if (nv >= 0 && part_id[nv] === pid && h_cnt[nv] > 0) {
            acc += h_sum[nv];
            cnt += h_cnt[nv];
          }
        }
        let ref_mean = (cnt >= 4) ? (acc/cnt) : ((part_cnt[pid] > 0) ? part_sum[pid]/part_cnt[pid] : 1);

        out[i] = valid_field[i]/Math.max(1e-6, ref_mean);
      }

      //Return statement
      return out;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountRuralSuitability: global.ViscountRuralSuitability };
