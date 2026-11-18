//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * 5-arcminute (`4320x2160`) Urban-Masked HYDE Rural De-Cliffer, Palaeoglacial Envelope Helper,
   * Field Smoother and Constrained NNLS Residual Kriging Synthesizer for Operation Viscount.
   *
   * @class ViscountRuralSuitability
   */
  global.ViscountRuralSuitability = class {
    static _uopp_cache = new Map();

    /**
     * Computes composite de-cliffed urban-masked HYDE rural habitation `u_hab(x)` for a chronological period.
     * When `preserve_period_dynamics === true` and period end `<= 1650 AD`, returns uniform `1.0` to avoid HYDE leakage.
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
      let preserve_dyn = Boolean(config && config.kriging_config && config.kriging_config.preserve_period_dynamics);
      let rep_years = [];

      //Guard clauses
      if (preserve_dyn && Number.isFinite(p_end) && p_end <= 1650) {
        out.fill(1.0);
        return out;
      }

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
     * When `preserve_period_dynamics === true` and `year <= 1650`, returns uniform `1.0`.
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

      //Declare local instance variables
      let cell_area = mask_data.cell_land_area;
      let n_valid = mask_data.valid_cell_count;
      let preserve_dyn = Boolean(config && config.kriging_config && config.kriging_config.preserve_period_dynamics);

      //Guard clauses
      if (preserve_dyn && year <= 1650)
        return new Float32Array(n_valid).fill(1.0);
      if (hab_cache && hab_cache.has(year)) return hab_cache.get(year);

      let hab_ind = new Float32Array(n_valid);
      let hyde_rur = this.loadUrbanMaskedHYDEPopcRaster(mask_data, year, hab_cache, config);
      let hyde_rur_1900 = covs.hyde_rur_1900;
      let min_area = 0.75*mask_data.mean_cell_land_area_km2;
      let n_parts = covs.partition_count;
      let part_cnt = new Int32Array(n_parts);
      let part_id = covs.part_id;
      let part_sum = new Float64Array(n_parts);
      let raw_sqrt = new Float32Array(n_valid);
      let u_hab = new Float32Array(n_valid);

      //Function body
      for (let i = 0; i < n_valid; i++) {
        let local_area = Math.max(min_area, cell_area[i]);
        let d = (hyde_rur) ? hyde_rur[i]/local_area : 0;

        if (d <= 0 && hyde_rur_1900)
          d = 0.08*(hyde_rur_1900[i]/local_area);

        if (d > 0) {
          let pid = part_id[i];
          let s = Math.sqrt(d);

          hab_ind[i] = 1;
          raw_sqrt[i] = s;
          part_cnt[pid]++;
          part_sum[pid] += s;
        }
      }

      let f_smooth = this.smoothValidFieldOnGrid(mask_data, hab_ind, 3);
      let decliffed = this.smoothWithinPartitionPositive(mask_data, raw_sqrt, part_id, part_sum, part_cnt, 12);

      for (let i = 0; i < n_valid; i++)
        if (decliffed[i] > 0)
          u_hab[i] = Math.sqrt(Math.max(0, f_smooth[i]))*decliffed[i];

      if (hab_cache) hab_cache.set(year, u_hab);

      //Return statement
      return u_hab;
    }


    /**
     * Fits constrained NNLS covariates (`u_hab`, `u_nat`, `u_eco`, `u_fluvial`, `u_coastal`) per horizon
     * and computes high-sharpness within-macro contrast weights paired with palaeoglacial & ice-cap envelopes.
     * When `preserve_period_dynamics === true && rep_year <= 1650`, zeroes HYDE covariate and applies `(m_cell/m_macro)^1.75`.
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
      let cell_area = mask_data.cell_land_area;
      let cell_obs = obs_bundle.cell_nearest_obs;
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let m_cell = new Float32Array(mask_data.valid_cell_count);
      let n_covs = 5;
      let n_obs = obs_bundle.obs_count;
      let n_valid = mask_data.valid_cell_count;
      let obs_list = obs_bundle.obs_list;
      let perm_ice = covs.perm_ice;
      let preserve_dyn = Boolean(config && config.kriging_config && config.kriging_config.preserve_period_dynamics);
      let pre_contact_bio = Boolean(preserve_dyn && rep_year <= 1650);
      let macro_rad = pre_contact_bio ?
        Math.max(4, Math.min(8, Math.round(0.45*meso_px))) :
        Math.max(4, Math.min(10, Math.round(0.60*meso_px)));
      let r_area = new Float64Array(n_obs);
      let r_covs = [
        new Float64Array(n_obs),
        new Float64Array(n_obs),
        new Float64Array(n_obs),
        new Float64Array(n_obs),
        new Float64Array(n_obs)
      ];
      let u_coastal = covs.u_coastal;
      let u_eco = covs.u_eco;
      let u_fluvial = covs.u_fluvial;
      let u_nat = covs.u_nat;
      let v_idx = mask_data.valid_indices;
      let weights = new Float32Array(n_valid);
      let xtx = new Float64Array(25);
      let xty = new Float64Array(5);

      //Function body
      for (let i = 0; i < n_valid; i++) {
        let a = cell_area[i]*perm_ice[i];
        let o = cell_obs[i];

        if (o < 0 || o >= n_obs || obs_list[o].is_frontier_buffer || a <= 0) continue;
        let uh = pre_contact_bio ? 0 : u_hab[i];
        let nat_cov = pre_contact_bio ? u_nat[i] : Math.max(0.12, u_hab[i])*u_nat[i];

        r_area[o] += a;
        r_covs[0][o] += a*uh;
        r_covs[1][o] += a*nat_cov;
        r_covs[2][o] += a*u_eco[i];
        r_covs[3][o] += a*u_fluvial[i];
        r_covs[4][o] += a*u_coastal[i];
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

        for (let r = 0; r < n_covs; r++) {
          xty[r] += w*xv[r]*y;
          for (let c = 0; c < n_covs; c++)
            xtx[r*n_covs + c] += w*xv[r]*xv[c];
        }
      }

      for (let iter = 0; iter < 300; iter++) {
        for (let r = 0; r < n_covs; r++) {
          if (pre_contact_bio && r === 0) {
            beta[0] = 0;
            continue;
          }
          let diag = xtx[r*n_covs + r];
          let rhs = xty[r];

          for (let c = 0; c < n_covs; c++)
            if (c !== r) rhs -= xtx[r*n_covs + c]*beta[c];
          beta[r] = (diag > 1e-12) ? Math.max(1e-4, rhs/diag) : 1e-4;
        }
      }

      let b_sum = Math.max(1e-8, beta[0] + beta[1] + beta[2] + beta[3] + beta[4]);
      let ice_env_arr = new Float32Array(n_valid);
      let w0 = pre_contact_bio ? 0.0 : (0.40*(beta[0]/b_sum) + 0.14);
      let w1 = pre_contact_bio ? (0.45*(beta[1]/b_sum) + 0.20) : (0.40*(beta[1]/b_sum) + 0.14);
      let w2 = pre_contact_bio ? (0.45*(beta[2]/b_sum) + 0.09) : (0.40*(beta[2]/b_sum) + 0.07);
      let w3 = pre_contact_bio ? (0.45*(beta[3]/b_sum) + 0.19) : (0.40*(beta[3]/b_sum) + 0.20);
      let w4 = pre_contact_bio ? (0.45*(beta[4]/b_sum) + 0.07) : (0.40*(beta[4]/b_sum) + 0.05);

      for (let i = 0; i < n_valid; i++) {
        let ice_env = perm_ice[i];
        let nat_term = pre_contact_bio ? u_nat[i] : Math.max(0.12, u_hab[i])*u_nat[i];

        if (apply_ice && rep_year <= -5500) {
          let gidx = v_idx[i];
          let lat = 90 - (Math.floor(gidx/grid_w) + 0.5)*180/grid_h;
          let lon = -180 + ((gidx % grid_w) + 0.5)*360/grid_w;

          ice_env *= this.getLaurentideCordilleranIceFactor(lat, lon, rep_year);
        }
        ice_env_arr[i] = ice_env;

        let base_suit = w0*u_hab[i] + w1*nat_term + w2*u_eco[i] + w3*u_fluvial[i] + w4*u_coastal[i];

        m_cell[i] = Math.max(1e-5, base_suit);
      }

      let m_macro = this.smoothPositiveFieldOnGrid(mask_data, m_cell, macro_rad);
      let sharp_exp = pre_contact_bio ? 1.75 : 1.55;
      let r_min = pre_contact_bio ? 0.12 : 0.18;
      let r_max = pre_contact_bio ? 3.20 : 2.40;

      for (let i = 0; i < n_valid; i++) {
        let ratio = (m_macro[i] > 0) ? Math.max(r_min, Math.min(r_max, m_cell[i]/m_macro[i])) : 1.0;

        weights[i] = Math.max(1e-5, ice_env_arr[i]*Math.pow(ratio, sharp_exp));
      }

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
     * Loads urban-masked HYDE 3.5 rural population raster over valid cells, inpainting modern urban sprawl pixels via IDW.
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
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let year = arg1_year;
      let cache = arg2_cache;
      let config = arg3_config;

      //Declare local instance variables
      let ckey = `__hyde_rur_${year}`;
      let cov_paths = (config && config.kriging_config && config.kriging_config.covariate_paths) ?
        config.kriging_config.covariate_paths : {};
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let hyde_path = path.resolve(mask_data.project_root, cov_paths.hyde_popc_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters_scaled_to_global", `popc_${year}.png`);
      let n_valid = mask_data.valid_cell_count;
      let out = new Float32Array(n_valid);
      let preserve_dyn = Boolean(config && config.kriging_config && config.kriging_config.preserve_period_dynamics);
      let total_px = grid_w*grid_h;
      let uopp_path = path.resolve(mask_data.project_root, cov_paths.hyde_uopp_raster || "histmap/2.data_cleaning/landuse_HYDE/rasters/uopp_2023AD.png");

      //Guard clauses
      if (preserve_dyn && year <= 1650) return out;
      if (cache && cache.has(ckey)) return cache.get(ckey);

      //Function body
      if (!fs.existsSync(hyde_path)) {
        let lbl = (year < 0) ? `${Math.abs(year)}BC` : `${year}AD`;

        hyde_path = path.resolve(mask_data.project_root, cov_paths.hyde_raw_rasters_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters", `popc_${lbl}.png`);
      }
      if (!fs.existsSync(hyde_path)) return out;

      let raw_grid = this.readGlobalFloat32Raster(hyde_path, total_px);
      let uopp_grid = null;

      if (this._uopp_cache.has(uopp_path)) {
        uopp_grid = this._uopp_cache.get(uopp_path);
      } else {
        uopp_grid = fs.existsSync(uopp_path) ? this.readGlobalFloat32Raster(uopp_path, total_px) : null;
        this._uopp_cache.set(uopp_path, uopp_grid);
      }
      let p2v = mask_data.pixel_to_valid_idx;
      let v_idx = mask_data.valid_indices;

      for (let i = 0; i < n_valid; i++) {
        let gidx = v_idx[i];
        let v = raw_grid[gidx];

        if (uopp_grid && uopp_grid[gidx] > 10.0) {
          let r = Math.floor(gidx/grid_w);
          let c = gidx % grid_w;
          let acc = 0;
          let w_sum = 0;

          for (let dr = -3; dr <= 3; dr++) {
            let nr = r + dr;

            if (nr < 0 || nr >= grid_h) continue;
            for (let dc = -3; dc <= 3; dc++) {
              let nc = (c + dc + grid_w) % grid_w;
              let ni = nr*grid_w + nc;

              if (p2v[ni] >= 0 && uopp_grid[ni] <= 10.0) {
                let wt = 1/Math.max(1, dr*dr + dc*dc);

                acc += raw_grid[ni]*wt;
                w_sum += wt;
              }
            }
          }
          v = (w_sum > 0) ? acc/w_sum : 0;
        }
        out[i] = Math.max(0, v);
      }

      if (cache) cache.set(ckey, out);

      //Return statement
      return out;
    }


    /**
     * Reads a full 4320x2160 big-endian float32 GeoPNG into a flat Float32Array.
     * @alias ViscountRuralSuitability.readGlobalFloat32Raster
     *
     * @param {string} arg0_file_path
     * @param {number} arg1_total_pixels
     *
     * @returns {Float32Array}
     */
    static readGlobalFloat32Raster (arg0_file_path, arg1_total_pixels) {
      //Convert from parameters
      let file_path = arg0_file_path;
      let total_pixels = arg1_total_pixels;

      //Declare local instance variables
      let out = new Float32Array(total_pixels);
      let png_data = PNG.sync.read(fs.readFileSync(file_path)).data;
      let dv = new DataView(png_data.buffer, png_data.byteOffset, png_data.byteLength);

      //Function body
      for (let i = 0; i < total_pixels; i++) {
        let px = i*4;

        if ((png_data[px] | png_data[px + 1] | png_data[px + 2] | png_data[px + 3]) === 0) continue;
        let v = dv.getFloat32(px, false);

        if (Number.isFinite(v) && v > 0) out[i] = v;
      }

      //Return statement
      return out;
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
