//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * Region-agnostic biophysical suitability, urban-masked HYDE 3.5 rural habitation and constrained WLS
   * Non-Negative Least Squares (NNLS) residual kriging covariate utilities ported from POLARIS
   * `SitesIARASGridUtils` / `SitesIARASResidualKriging` for `ViscountMaternKriging`.
   *
   * @class ViscountResidualCovariates
   */
  global.ViscountResidualCovariates = class {
    /**
     * Computes composite de-cliffed urban-masked HYDE 3.5 rural habitation field `u_hab(x)` for a period
     * by averaging across representative HYDE benchmark years spanning its documented date range.
     * @alias ViscountResidualCovariates.computeCompositeHabitationField
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_obs_bundle
     * @param {Object} arg2_bio_covs
     * @param {Object} arg3_period_config
     * @param {Object} arg4_config
     * @param {Map} [arg5_hab_cache]
     *
     * @returns {Float32Array}
     */
    static computeCompositeHabitationField (arg0_mask_data, arg1_obs_bundle, arg2_bio_covs, arg3_period_config, arg4_config, arg5_hab_cache) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let obs_bundle = arg1_obs_bundle;
      let bio_covs = arg2_bio_covs;
      let period_config = (arg3_period_config) ? arg3_period_config : {};
      let config = (arg4_config) ? arg4_config : {};
      let hab_cache = arg5_hab_cache;

      //Declare local instance variables
      let composite_hab = new Float32Array(mask_data.valid_cell_count);
      let default_hyde_years = [-10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000, 0, 500, 1000, 1400, 1600, 1750, 1850, 1900];
      let hyde_years = (config.kriging_config && Array.isArray(config.kriging_config.all_hyde_years)) ?
        config.kriging_config.all_hyde_years :
        ((config.kriging_config && Array.isArray(config.kriging_config.hyde_years)) ? config.kriging_config.hyde_years : default_hyde_years);
      let matched_years = [];
      let n_valid = mask_data.valid_cell_count;
      let p_end = (period_config.approx_end_year !== undefined) ? period_config.approx_end_year : period_config.representative_year;
      let p_start = (period_config.approx_start_year !== undefined) ? period_config.approx_start_year : period_config.representative_year;
      let rep_years = [];

      //Guard clauses
      if (!mask_data || !bio_covs) {
        console.error("[ViscountResidualCovariates] Missing mask_data or bio_covs in computeCompositeHabitationField.");
        return new Float32Array(0);
      }

      //Function body
      if (p_start !== null && p_start !== undefined && p_end !== null && p_end !== undefined) {
        for (let i = 0; i < hyde_years.length; i++)
          if (hyde_years[i] >= p_start && hyde_years[i] <= p_end)
            matched_years.push(hyde_years[i]);
      }
      if (matched_years.length === 0) matched_years = [0, 900, 1500];

      rep_years.push(matched_years[0]);
      if (matched_years.length > 2)
        rep_years.push(matched_years[Math.floor(matched_years.length/2)]);
      if (matched_years.length > 1)
        rep_years.push(matched_years[matched_years.length - 1]);

      for (let i = 0; i < rep_years.length; i++) {
        let local_u_hab = this.computeDeCliffedHabitationField(
          mask_data,
          obs_bundle,
          bio_covs,
          rep_years[i],
          config,
          hab_cache
        );

        for (let x = 0; x < n_valid; x++)
          composite_hab[x] += local_u_hab[x]/rep_years.length;
      }

      //Return statement
      return composite_hab;
    }


    /**
     * Computes the within-partition de-cliffed Freeman-Tukey urban-masked HYDE 3.5 rural habitation field `u_hab(x)`,
     * preserving 5-arcminute fluvial and topographic valleys while eliminating administrative partition walls.
     * @alias ViscountResidualCovariates.computeDeCliffedHabitationField
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_obs_bundle
     * @param {Object} arg2_bio_covs
     * @param {number} arg3_year
     * @param {Object} arg4_config
     * @param {Map} [arg5_hab_cache]
     *
     * @returns {Float32Array}
     */
    static computeDeCliffedHabitationField (arg0_mask_data, arg1_obs_bundle, arg2_bio_covs, arg3_year, arg4_config, arg5_hab_cache) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let obs_bundle = arg1_obs_bundle;
      let bio_covs = arg2_bio_covs;
      let year = Number(arg3_year) || 0;
      let config = (arg4_config) ? arg4_config : {};
      let hab_cache = arg5_hab_cache;

      //Guard clauses
      if (hab_cache && hab_cache.has(year)) return hab_cache.get(year);

      //Declare local instance variables
      let cell_area = mask_data.cell_land_area;
      let cell_obs = obs_bundle.cell_nearest_obs;
      let decliffed_d;
      let f_hab_smooth;
      let hab_ind = new Float32Array(mask_data.valid_cell_count);
      let hyde_rur = this.loadUrbanMaskedHYDEPopcRaster(mask_data, year, hab_cache, config);
      let hyde_rur_1900 = bio_covs.hyde_rur_1900;
      let min_hyde_area = 0.75*mask_data.mean_cell_land_area_km2;
      let n_obs = obs_bundle.obs_count;
      let n_parts = bio_covs.partition_count;
      let n_valid = mask_data.valid_cell_count;
      let obs_has_hab = new Uint8Array(n_obs);
      let part_cnt = new Int32Array(n_parts);
      let part_id = bio_covs.part_id;
      let part_sum = new Float64Array(n_parts);
      let raw_sqrt_d = new Float32Array(mask_data.valid_cell_count);
      let u_hab = new Float32Array(mask_data.valid_cell_count);

      //Function body
      for (let i = 0; i < n_valid; i++)
        if (hyde_rur[i] > 0.05) obs_has_hab[cell_obs[i]] = 1;

      for (let i = 0; i < n_valid; i++) {
        let local_area = Math.max(min_hyde_area, cell_area[i]);
        let local_d = hyde_rur[i]/local_area;
        let local_r = cell_obs[i];

        if (local_d <= 0 && obs_has_hab[local_r] === 0 && bio_covs.obs_has_any_sites[local_r] === 1 && hyde_rur_1900)
          local_d = 0.15*(hyde_rur_1900[i]/local_area);

        if (local_d < 0.002 && bio_covs.obs_has_any_sites[local_r] === 0)
          local_d = 0;

        if (local_d > 0) {
          let local_pid = part_id[i];
          let local_s = Math.sqrt(local_d);

          hab_ind[i] = 1;
          raw_sqrt_d[i] = local_s;
          part_cnt[local_pid]++;
          part_sum[local_pid] += local_s;
        }
      }

      f_hab_smooth = this.smoothValidFieldOnGrid(mask_data, hab_ind, Math.max(1, bio_covs.catchment_px));
      decliffed_d = this.smoothWithinPartitionPositive(
        mask_data,
        raw_sqrt_d,
        part_id,
        part_sum,
        part_cnt,
        Math.max(5, bio_covs.meso_px)
      );

      for (let i = 0; i < n_valid; i++)
        if (decliffed_d[i] > 0) {
          let local_prior = (bio_covs.prior_weight) ? bio_covs.prior_weight[i] : 1.0;

          u_hab[i] = Math.sqrt(Math.max(0, f_hab_smooth[i]))*decliffed_d[i]*local_prior;
        }

      if (hab_cache) hab_cache.set(year, u_hab);

      //Return statement
      return u_hab;
    }


    /**
     * Fits constrained non-negative WLS regression predicting observed catchment amplitudes `z_obs`
     * from `[u_hab, u_hab*u_nat, u_hab*u_eco]` and returns trend betas plus multiplicative cell weights.
     * @alias ViscountResidualCovariates.computeResidualKrigingWeights
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_obs_bundle
     * @param {Object} arg2_bio_covs
     * @param {Float32Array} arg3_u_hab
     * @param {Float64Array|Float32Array} arg4_z_obs
     * @param {number} arg5_meso_px
     * @param {Float64Array|Float32Array} [arg6_s_obs]
     *
     * @returns {Object}
     */
    static computeResidualKrigingWeights (arg0_mask_data, arg1_obs_bundle, arg2_bio_covs, arg3_u_hab, arg4_z_obs, arg5_meso_px, arg6_s_obs) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let obs_bundle = arg1_obs_bundle;
      let bio_covs = arg2_bio_covs;
      let u_hab = arg3_u_hab;
      let z_obs = arg4_z_obs;
      let meso_px = Number(arg5_meso_px) || 12;
      let s_obs = arg6_s_obs;

      //Declare local instance variables
      let b0_eff;
      let b1_eff;
      let b2_eff;
      let b_sum;
      let beta = new Float64Array(3);
      let cell_area = mask_data.cell_land_area;
      let cell_obs = obs_bundle.cell_nearest_obs;
      let dom_count = obs_bundle.obs_count;
      let m_cell = new Float32Array(mask_data.valid_cell_count);
      let m_macro;
      let macro_rad = Math.max(4, Math.round(0.75*meso_px));
      let n_covs = 3;
      let n_valid = mask_data.valid_cell_count;
      let r_eco_mean = new Float64Array(dom_count);
      let r_hab_area = new Float64Array(dom_count);
      let r_hab_mean = new Float64Array(dom_count);
      let r_nat_mean = new Float64Array(dom_count);
      let u_eco = bio_covs.u_eco;
      let u_nat = bio_covs.u_nat;
      let weights = new Float32Array(mask_data.valid_cell_count);
      let xtx = new Float64Array(9);
      let xty = new Float64Array(3);

      //Guard clauses
      if (!mask_data || !obs_bundle || !bio_covs || !u_hab || !z_obs) {
        console.error("[ViscountResidualCovariates] Missing inputs in computeResidualKrigingWeights.");
        return { beta: [0, 0, 0], weights: new Float32Array(mask_data ? mask_data.valid_cell_count : 0).fill(1) };
      }

      //Function body
      for (let i = 0; i < n_valid; i++) {
        let local_uh = u_hab[i];
        if (local_uh <= 0) continue;

        let local_a = cell_area[i];
        let local_r = cell_obs[i];
        if (local_r >= dom_count) continue;

        r_hab_area[local_r] += local_a;
        r_hab_mean[local_r] += local_a*local_uh;
        r_nat_mean[local_r] += local_a*local_uh*u_nat[i];
        r_eco_mean[local_r] += local_a*local_uh*u_eco[i];
      }

      for (let i = 0; i < dom_count; i++) {
        let local_ha = r_hab_area[i];
        if (local_ha > 0) {
          r_hab_mean[i] /= local_ha;
          r_nat_mean[i] /= local_ha;
          r_eco_mean[i] /= local_ha;
        }
      }

      for (let i = 0; i < dom_count; i++) {
        let local_sk = (s_obs) ? Math.max(0, s_obs[i]) : 0;
        let local_w = r_hab_area[i]*(1 + Math.sqrt(local_sk));
        if (local_w <= 0) continue;

        let local_xvec = [r_hab_mean[i], r_nat_mean[i], r_eco_mean[i]];
        let local_y = z_obs[i];

        for (let x = 0; x < n_covs; x++) {
          xty[x] += local_w*local_xvec[x]*local_y;
          for (let y = 0; y < n_covs; y++)
            xtx[x*n_covs + y] += local_w*local_xvec[x]*local_xvec[y];
        }
      }

      for (let i = 0; i < 400; i++)
        for (let x = 0; x < n_covs; x++) {
          let local_diag = xtx[x*n_covs + x];
          let local_rhs = xty[x];

          for (let y = 0; y < n_covs; y++)
            if (y !== x) local_rhs -= xtx[x*n_covs + y]*beta[y];

          beta[x] = (local_diag > 1e-12) ? Math.max(1e-4, local_rhs/local_diag) : 1e-4;
        }

      b_sum = Math.max(1e-8, beta[0] + beta[1] + beta[2]);
      b0_eff = 0.50*(beta[0]/b_sum) + 0.22;
      b1_eff = 0.50*(beta[1]/b_sum) + 0.20;
      b2_eff = 0.50*(beta[2]/b_sum) + 0.08;

      for (let i = 0; i < n_valid; i++)
        if (u_hab[i] > 0)
          m_cell[i] = u_hab[i]*(b0_eff + b1_eff*u_nat[i] + b2_eff*u_eco[i]);

      m_macro = this.smoothPositiveFieldOnGrid(mask_data, m_cell, macro_rad);

      for (let i = 0; i < n_valid; i++)
        if (m_cell[i] > 0 && m_macro[i] > 0) {
          let local_ratio = Math.min(3.2, m_cell[i]/m_macro[i]);
          weights[i] = Math.pow(local_ratio, 2.25);
        } else {
          weights[i] = 1.0;
        }

      //Return statement
      return {
        beta: [
          Number(beta[0].toFixed(6)),
          Number(beta[1].toFixed(6)),
          Number(beta[2].toFixed(6))
        ],
        m_cell: m_cell,
        weights: weights
      };
    }


    /**
     * Builds the 1-pixel buffered modern urban settlement mask from HYDE 3.5 `uopp_2023AD.png`.
     * @alias ViscountResidualCovariates.getModernUrbanMask
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_config
     * @param {Map} [arg2_cache]
     *
     * @returns {Uint8Array}
     */
    static getModernUrbanMask (arg0_mask_data, arg1_config, arg2_cache) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let config = (arg1_config) ? arg1_config : {};
      let cache = arg2_cache;

      //Guard clauses
      if (cache && cache.has("__modern_urban_mask__")) return cache.get("__modern_urban_mask__");

      //Declare local instance variables
      let cov_paths = (config.kriging_config && config.kriging_config.covariate_paths) ? config.kriging_config.covariate_paths : {};
      let buffer_radius = (cov_paths.urban_mask_buffer_radius !== undefined) ? cov_paths.urban_mask_buffer_radius : 1;
      let dilated_mask;
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let raw_mask = new Uint8Array(grid_w*grid_h);
      let total_pixels = grid_w*grid_h;
      let uopp_grid;
      let uopp_path = path.join(
        mask_data.project_root,
        cov_paths.hyde_uopp_raster || "histmap/2.data_cleaning/landuse_HYDE/rasters/uopp_2023AD.png"
      );
      let uopp_threshold = (cov_paths.urban_uopp_threshold !== undefined) ? cov_paths.urban_uopp_threshold : 10.0;

      //Function body
      uopp_grid = this.readGlobalFloat32Raster(uopp_path, total_pixels);
      for (let i = 0; i < total_pixels; i++)
        if (uopp_grid[i] > uopp_threshold) raw_mask[i] = 1;

      if (buffer_radius <= 0) {
        if (cache) cache.set("__modern_urban_mask__", raw_mask);
        return raw_mask;
      }

      dilated_mask = new Uint8Array(total_pixels);
      for (let i = 0; i < grid_h; i++)
        for (let x = 0; x < grid_w; x++)
          if (raw_mask[i*grid_w + x] === 1)
            for (let y = -buffer_radius; y <= buffer_radius; y++) {
              let local_ny = i + y;
              if (local_ny >= 0 && local_ny < grid_h)
                for (let z = -buffer_radius; z <= buffer_radius; z++) {
                  let local_nx = (x + z + grid_w) % grid_w;
                  dilated_mask[local_ny*grid_w + local_nx] = 1;
                }
            }

      if (cache) cache.set("__modern_urban_mask__", dilated_mask);

      //Return statement
      return dilated_mask;
    }


    /**
     * Inpaints masked urban settlement cells via inverse-distance weighting from surrounding rural land pixels.
     * @alias ViscountResidualCovariates.inpaintUrbanMaskGrid
     *
     * @param {Float32Array} arg0_popc_grid
     * @param {Uint8Array} arg1_urban_mask
     * @param {Float32Array} arg2_land_area_grid
     * @param {Float32Array} arg3_fallback_grid
     * @param {number} arg4_grid_width
     * @param {number} arg5_grid_height
     * @param {number} [arg6_inpaint_radius=3]
     * @param {Int32Array} [arg7_target_indices]
     *
     * @returns {Float32Array}
     */
    static inpaintUrbanMaskGrid (arg0_popc_grid, arg1_urban_mask, arg2_land_area_grid, arg3_fallback_grid, arg4_grid_width, arg5_grid_height, arg6_inpaint_radius, arg7_target_indices) {
      //Convert from parameters
      let popc_grid = arg0_popc_grid;
      let urban_mask = arg1_urban_mask;
      let land_area_grid = arg2_land_area_grid;
      let fallback_grid = arg3_fallback_grid;
      let grid_w = arg4_grid_width;
      let grid_h = arg5_grid_height;
      let radius = (arg6_inpaint_radius !== undefined) ? arg6_inpaint_radius : 3;
      let target_indices = arg7_target_indices;

      //Declare local instance variables
      let n_targets = (target_indices) ? target_indices.length : grid_w*grid_h;
      let out_grid = new Float32Array(popc_grid);
      let wide_radius = radius*2;

      //Function body
      for (let i = 0; i < n_targets; i++) {
        let local_idx = (target_indices) ? target_indices[i] : i;
        if (urban_mask[local_idx] < 1) continue;
        if (land_area_grid[local_idx] <= 0) {
          out_grid[local_idx] = 0;
          continue;
        }

        let local_cx = local_idx % grid_w;
        let local_cy = Math.floor(local_idx/grid_w);
        let local_val_sum = 0;
        let local_w_sum = 0;

        for (let x = -radius; x <= radius; x++) {
          let local_ny = local_cy + x;
          if (local_ny >= 0 && local_ny < grid_h)
            for (let y = -radius; y <= radius; y++) {
              if (x === 0 && y === 0) continue;
              let local_nx = (local_cx + y + grid_w) % grid_w;
              let local_nidx = local_ny*grid_w + local_nx;
              if (urban_mask[local_nidx] === 0 && land_area_grid[local_nidx] > 0) {
                let local_w = 1/Math.max(1, x*x + y*y);
                local_val_sum += popc_grid[local_nidx]*local_w;
                local_w_sum += local_w;
              }
            }
        }

        if (local_w_sum > 0) {
          out_grid[local_idx] = local_val_sum/local_w_sum;
        } else {
          for (let x = -wide_radius; x <= wide_radius; x++) {
            let local_ny = local_cy + x;
            if (local_ny >= 0 && local_ny < grid_h)
              for (let y = -wide_radius; y <= wide_radius; y++) {
                let local_nx = (local_cx + y + grid_w) % grid_w;
                let local_nidx = local_ny*grid_w + local_nx;
                if (urban_mask[local_nidx] === 0 && land_area_grid[local_nidx] > 0) {
                  let local_w = 1/Math.max(1, x*x + y*y);
                  local_val_sum += popc_grid[local_nidx]*local_w;
                  local_w_sum += local_w;
                }
              }
          }

          if (local_w_sum > 0)
            out_grid[local_idx] = local_val_sum/local_w_sum;
          else if (popc_grid[local_idx] > 0 && fallback_grid && fallback_grid[local_idx] > 0)
            out_grid[local_idx] = fallback_grid[local_idx];
          else
            out_grid[local_idx] = 0;
        }
      }

      //Return statement
      return out_grid;
    }


    /**
     * Loads CLIMBER-3 `maxln_cr.asc` cultivable suitability, WWF `forest_wwf_cr.asc` forest ecotone,
     * `sub_iso_cr.asc` + `nelson_regions.png` partition IDs and 1900 urban-masked HYDE rural fallback.
     * @alias ViscountResidualCovariates.loadBiophysicalCovariates
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_obs_bundle
     * @param {Object} arg2_config
     * @param {number} arg3_meso_px
     *
     * @returns {Object|null}
     */
    static loadBiophysicalCovariates (arg0_mask_data, arg1_obs_bundle, arg2_config, arg3_meso_px) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let obs_bundle = arg1_obs_bundle;
      let config = (arg2_config) ? arg2_config : {};
      let meso_px = Number(arg3_meso_px) || 12;

      //Guard clauses
      if (!mask_data || !obs_bundle || !mask_data.project_root) {
        console.error("[ViscountResidualCovariates] Missing mask_data or obs_bundle in loadBiophysicalCovariates.");
        return null;
      }

      //Declare local instance variables
      let catchment_px = Math.max(2, Math.round((obs_bundle.median_radius_km || 30)/9.2));
      let cov_paths = (config.kriging_config && config.kriging_config.covariate_paths) ? config.kriging_config.covariate_paths : {};
      let f_forest_smooth;
      let f_pass1;
      let f_raw = new Float32Array(mask_data.valid_cell_count);
      let forest_path = path.join(mask_data.project_root, cov_paths.forest_asc || "histmap/1.data_raw/metadata_HYDE/general_files/forest_wwf_cr.asc");
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let maxln_path = path.join(mask_data.project_root, cov_paths.maxln_asc || "histmap/1.data_raw/metadata_HYDE/general_files/maxln_cr.asc");
      let mean_maxln = 0;
      let n_obs = obs_bundle.obs_count;
      let n_valid = mask_data.valid_cell_count;
      let nelson_path = path.join(mask_data.project_root, cov_paths.nelson_regions_png || "histmap/2.data_cleaning/population_KK10LUH2/config/nelson_regions.png");
      let next_pid = 1;
      let obs_has_any_sites = new Uint8Array(n_obs);
      let obs_list = obs_bundle.obs_list || [];
      let part_id = new Int32Array(n_valid);
      let part_map = new Map();
      let period_configs = Array.isArray(config.periods) ? config.periods : [];
      let prior_grid = null;
      let prior_path = cov_paths.prior_density_raster_png ? path.join(mask_data.project_root, cov_paths.prior_density_raster_png) : "";
      let prior_weight = null;
      let sub_iso_path = path.join(mask_data.project_root, cov_paths.sub_iso_asc || "histmap/1.data_raw/metadata_HYDE/general_files/sub_iso_cr.asc");
      let total_pixels = grid_w*grid_h;
      let u_eco = new Float32Array(n_valid);
      let u_nat = new Float32Array(n_valid);
      let valid_indices = mask_data.valid_indices;

      if (!fs.existsSync(maxln_path) || !fs.existsSync(forest_path) || !fs.existsSync(sub_iso_path)) {
        console.error("[ViscountResidualCovariates] Biophysical .asc covariates unavailable; skipping WLS trend.");
        return null;
      }

      //Function body
      let forest_grid = this.readAscGrid(forest_path, total_pixels);
      let hyde_rur_1900 = this.loadUrbanMaskedHYDEPopcRaster(mask_data, 1900, null, config);
      let maxln_grid = this.readAscGrid(maxln_path, total_pixels);
      let nelson_png = fs.existsSync(nelson_path) ? PNG.sync.read(fs.readFileSync(nelson_path)) : null;
      let sub_iso_grid = this.readAscGrid(sub_iso_path, total_pixels);

      if (prior_path && fs.existsSync(prior_path)) {
        prior_grid = this.readGlobalFloat32Raster(prior_path, total_pixels);
        prior_weight = new Float32Array(n_valid);
      }

      for (let i = 0; i < n_obs; i++)
        for (let x = 0; x < period_configs.length; x++)
          if ((obs_list[i].periods[period_configs[x].key] || 0) > 0) {
            obs_has_any_sites[i] = 1;
            break;
          }

      for (let i = 0; i < n_valid; i++) {
        let local_gidx = valid_indices[i];
        let local_f = (forest_grid[local_gidx] > 0) ? 1 : 0;
        let local_idx = local_gidx*4;
        let local_nid = nelson_png ?
          ((nelson_png.data[local_idx] << 16) | (nelson_png.data[local_idx + 1] << 8) | nelson_png.data[local_idx + 2]) : 0;
        let local_p = Math.round(sub_iso_grid[local_gidx]);
        let local_key = `${local_p}_${local_nid}`;
        let local_pid = part_map.get(local_key);

        if (!local_pid) {
          local_pid = next_pid++;
          part_map.set(local_key, local_pid);
        }
        part_id[i] = local_pid;
        f_raw[i] = local_f;
        mean_maxln += Math.pow(Math.max(0, maxln_grid[local_gidx]), 0.80);
      }
      mean_maxln = Math.max(1e-4, mean_maxln/Math.max(1, n_valid));

      f_pass1 = this.smoothValidFieldOnGrid(mask_data, f_raw, Math.max(2, catchment_px));
      f_forest_smooth = this.smoothValidFieldOnGrid(mask_data, f_pass1, Math.max(2, catchment_px));

      for (let i = 0; i < n_valid; i++) {
        let local_ff = Math.max(0, Math.min(1, f_forest_smooth[i]));
        let local_gidx = valid_indices[i];
        let local_unat = Math.pow(Math.max(0, maxln_grid[local_gidx]), 0.80)/mean_maxln;

        u_nat[i] = local_unat;
        u_eco[i] = 4*local_ff*(1 - local_ff);
        if (prior_weight && prior_grid)
          prior_weight[i] = Math.max(0.25, Math.min(2.5, prior_grid[local_gidx]));
      }

      //Return statement
      return {
        catchment_px: catchment_px,
        forest_grid: forest_grid,
        hyde_rur_1900: hyde_rur_1900,
        meso_px: meso_px,
        obs_has_any_sites: obs_has_any_sites,
        part_id: part_id,
        partition_count: next_pid,
        prior_weight: prior_weight,
        sub_iso_grid: sub_iso_grid,
        u_eco: u_eco,
        u_nat: u_nat
      };
    }


    /**
     * Loads a benchmark year's HYDE 3.5 `popc` raster and removes urban footprint + 8x isolated spikes via IDW inpainting.
     * @alias ViscountResidualCovariates.loadUrbanMaskedHYDEPopcRaster
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
      let year = Number(arg1_year) || 0;
      let cache = arg2_cache;
      let config = (arg3_config) ? arg3_config : {};

      //Guard clauses
      let cache_key = `hyde_urban_masked_${year}`;
      if (cache && cache.has(cache_key)) return cache.get(cache_key);

      //Declare local instance variables
      let cov_paths = (config.kriging_config && config.kriging_config.covariate_paths) ? config.kriging_config.covariate_paths : {};
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let inpaint_radius = (cov_paths.urban_mask_inpaint_radius !== undefined) ? cov_paths.urban_mask_inpaint_radius : 4;
      let kk10_grid = null;
      let kk10_path;
      let land_area_grid = mask_data.land_area_grid;
      let modern_urban_mask;
      let n_valid = mask_data.valid_cell_count;
      let out_arr = new Float32Array(n_valid);
      let popc_grid;
      let popc_path;
      let root = mask_data.project_root;
      let spike_ratio = (cov_paths.urban_outlier_spike_ratio !== undefined) ? cov_paths.urban_outlier_spike_ratio : 8.0;
      let total_pixels = grid_w*grid_h;
      let urbc_path;
      let valid_indices = mask_data.valid_indices;
      let year_label = (year < 0) ? `${Math.abs(year)}BC` : `${year}AD`;
      let year_urban_mask;

      //Function body
      popc_path = path.join(root, cov_paths.hyde_popc_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters_scaled_to_global", `popc_${year}.png`);
      if (!fs.existsSync(popc_path))
        popc_path = path.join(root, cov_paths.hyde_raw_rasters_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters", `popc_${year_label}.png`);
      if (!fs.existsSync(popc_path)) return out_arr;

      popc_grid = this.readGlobalFloat32Raster(popc_path, total_pixels);
      modern_urban_mask = this.getModernUrbanMask(mask_data, config, cache);
      year_urban_mask = new Uint8Array(modern_urban_mask);

      urbc_path = path.join(root, cov_paths.hyde_mcevedy_rasters_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters_mcevedy", `urbc_${year}.png`);
      if (!fs.existsSync(urbc_path))
        urbc_path = path.join(root, cov_paths.hyde_raw_rasters_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters", `urbc_${year_label}.png`);

      if (fs.existsSync(urbc_path)) {
        let urbc_grid = this.readGlobalFloat32Raster(urbc_path, total_pixels);
        for (let i = 0; i < total_pixels; i++)
          if (urbc_grid[i] > 0) year_urban_mask[i] = 1;
      }

      for (let i = 0; i < n_valid; i++) {
        let local_gidx = valid_indices[i];
        if (year_urban_mask[local_gidx] >= 1 || popc_grid[local_gidx] <= 0) continue;

        let local_cx = local_gidx % grid_w;
        let local_cy = Math.floor(local_gidx/grid_w);
        let local_ncnt = 0;
        let local_nsum = 0;

        for (let x = -1; x <= 1; x++) {
          let local_ny = local_cy + x;
          if (local_ny >= 0 && local_ny < grid_h)
            for (let y = -1; y <= 1; y++) {
              if (x === 0 && y === 0) continue;
              let local_nx = (local_cx + y + grid_w) % grid_w;
              let local_nidx = local_ny*grid_w + local_nx;
              if (year_urban_mask[local_nidx] === 0 && land_area_grid[local_nidx] > 0 && popc_grid[local_nidx] > 0) {
                local_nsum += popc_grid[local_nidx];
                local_ncnt++;
              }
            }
        }

        if (local_ncnt >= 3 && popc_grid[local_gidx] > spike_ratio*(local_nsum/local_ncnt))
          year_urban_mask[local_gidx] = 1;
      }

      kk10_path = path.join(root, cov_paths.kk10_fallback_folder || "histmap/2.data_cleaning/population_KK10LUH2/rasters_KK10LUH2_2._global_scaling", `popc_${year}.png`);
      if (fs.existsSync(kk10_path)) kk10_grid = this.readGlobalFloat32Raster(kk10_path, total_pixels);

      let cleaned_grid = this.inpaintUrbanMaskGrid(popc_grid, year_urban_mask, land_area_grid, kk10_grid, grid_w, grid_h, inpaint_radius, valid_indices);
      for (let i = 0; i < n_valid; i++) {
        let local_val = cleaned_grid[valid_indices[i]];
        if (Number.isFinite(local_val) && local_val > 0) out_arr[i] = local_val;
      }

      if (cache) cache.set(cache_key, out_arr);

      //Return statement
      return out_arr;
    }


    /**
     * Reads a 6-header-line Esri ASCII grid into a flat Float32Array.
     * @alias ViscountResidualCovariates.readAscGrid
     *
     * @param {string} arg0_file_path
     * @param {number} arg1_total_pixels
     *
     * @returns {Float32Array}
     */
    static readAscGrid (arg0_file_path, arg1_total_pixels) {
      //Convert from parameters
      let file_path = arg0_file_path;
      let total_pixels = arg1_total_pixels;

      //Guard clauses
      if (!fs.existsSync(file_path)) {
        console.error(`[ViscountResidualCovariates] Missing ASC grid: ${file_path}`);
        return new Float32Array(total_pixels);
      }

      //Declare local instance variables
      let out_grid = new Float32Array(total_pixels);
      let tokens = fs.readFileSync(file_path, "utf8").trim().split(/\s+/);

      //Function body
      for (let i = 0; i < total_pixels && (12 + i) < tokens.length; i++)
        out_grid[i] = parseFloat(tokens[12 + i]) || 0;

      //Return statement
      return out_grid;
    }


    /**
     * Reads a full global big-endian float32 GeoPNG into a flat Float32Array.
     * @alias ViscountResidualCovariates.readGlobalFloat32Raster
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

      //Guard clauses
      if (!fs.existsSync(file_path)) return new Float32Array(total_pixels);

      //Declare local instance variables
      let png_data = PNG.sync.read(fs.readFileSync(file_path)).data;
      let data_view = new DataView(png_data.buffer, png_data.byteOffset, png_data.byteLength);
      let out_grid = new Float32Array(total_pixels);

      //Function body
      for (let i = 0; i < total_pixels; i++) {
        let local_px = i*4;
        if (png_data[local_px] === 0 && png_data[local_px + 1] === 0 && png_data[local_px + 2] === 0 && png_data[local_px + 3] === 0)
          continue;

        let local_val = data_view.getFloat32(local_px, false);
        if (Number.isFinite(local_val) && local_val > 0) out_grid[i] = local_val;
      }

      //Return statement
      return out_grid;
    }


    /**
     * Separable 2D box smooth over strictly positive mask cells (`field[i] > 0`).
     * @alias ViscountResidualCovariates.smoothPositiveFieldOnGrid
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

      //Return statement
      return this.smoothPositiveMaskedPass(mask_data, valid_field, null, null, null, radius_px);
    }


    /**
     * Shared separable 2D box mean / within-partition normalisation helper for positive cells.
     * @alias ViscountResidualCovariates.smoothPositiveMaskedPass
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_valid_field
     * @param {Int32Array|null} arg2_part_id
     * @param {Float64Array|null} arg3_part_sum
     * @param {Int32Array|null} arg4_part_cnt
     * @param {number} arg5_radius_px
     *
     * @returns {Float32Array}
     */
    static smoothPositiveMaskedPass (arg0_mask_data, arg1_valid_field, arg2_part_id, arg3_part_sum, arg4_part_cnt, arg5_radius_px) {
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
      let has_part = Boolean(part_id);
      let n_valid = mask_data.valid_cell_count;
      let horiz_cnt = new Int32Array(n_valid);
      let horiz_sum = new Float32Array(n_valid);
      let out_pass = new Float32Array(n_valid);
      let px_to_valid = mask_data.pixel_to_valid_idx;
      let valid_indices = mask_data.valid_indices;

      //Function body
      for (let i = 0; i < n_valid; i++) {
        if (valid_field[i] <= 0) continue;
        let local_cnt = 0;
        let local_cx = valid_indices[i] % grid_w;
        let local_pid = has_part ? part_id[i] : 0;
        let local_row = Math.floor(valid_indices[i]/grid_w)*grid_w;
        let local_sum = 0;
        let local_x0 = Math.max(0, local_cx - radius_px);
        let local_x1 = Math.min(grid_w - 1, local_cx + radius_px);

        for (let x = local_x0; x <= local_x1; x++) {
          let local_v_idx = px_to_valid[local_row + x];
          if (local_v_idx >= 0 && valid_field[local_v_idx] > 0 && (!has_part || part_id[local_v_idx] === local_pid)) {
            local_sum += valid_field[local_v_idx];
            local_cnt++;
          }
        }
        horiz_cnt[i] = local_cnt;
        horiz_sum[i] = local_sum;
      }

      for (let i = 0; i < n_valid; i++) {
        if (valid_field[i] <= 0) continue;
        let local_cnt = 0;
        let local_cx = valid_indices[i] % grid_w;
        let local_cy = Math.floor(valid_indices[i]/grid_w);
        let local_pid = has_part ? part_id[i] : 0;
        let local_ref_mean = valid_field[i];
        let local_sum = 0;
        let local_y0 = Math.max(0, local_cy - radius_px);
        let local_y1 = Math.min(grid_h - 1, local_cy + radius_px);

        for (let y = local_y0; y <= local_y1; y++) {
          let local_v_idx = px_to_valid[y*grid_w + local_cx];
          if (local_v_idx >= 0 && horiz_cnt[local_v_idx] > 0 && (!has_part || part_id[local_v_idx] === local_pid)) {
            local_sum += horiz_sum[local_v_idx];
            local_cnt += horiz_cnt[local_v_idx];
          }
        }

        if (has_part) {
          if (local_cnt >= 4) local_ref_mean = local_sum/local_cnt;
          else if (part_cnt && part_cnt[local_pid] > 0) local_ref_mean = part_sum[local_pid]/part_cnt[local_pid];
          else local_ref_mean = 1;
          out_pass[i] = valid_field[i]/Math.max(1e-6, local_ref_mean);
        } else {
          out_pass[i] = (local_cnt > 0) ? local_sum/local_cnt : valid_field[i];
        }
      }

      //Return statement
      return out_pass;
    }


    /**
     * Separable 2D box smooth across valid land mask cells.
     * @alias ViscountResidualCovariates.smoothValidFieldOnGrid
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
      let horiz_pass = new Float32Array(n_valid);
      let out_pass = new Float32Array(n_valid);
      let px_to_valid = mask_data.pixel_to_valid_idx;
      let valid_indices = mask_data.valid_indices;

      //Function body
      for (let i = 0; i < n_valid; i++) {
        let local_cnt = 0;
        let local_idx = valid_indices[i];
        let local_row = Math.floor(local_idx/grid_w)*grid_w;
        let local_sum = 0;
        let local_x = local_idx % grid_w;

        for (let x = -radius_px; x <= radius_px; x++) {
          let local_nx = (local_x + x + grid_w) % grid_w;
          let local_v_idx = px_to_valid[local_row + local_nx];
          if (local_v_idx >= 0) {
            local_sum += valid_field[local_v_idx];
            local_cnt++;
          }
        }
        horiz_pass[i] = (local_cnt > 0) ? local_sum/local_cnt : valid_field[i];
      }

      for (let i = 0; i < n_valid; i++) {
        let local_cnt = 0;
        let local_idx = valid_indices[i];
        let local_sum = 0;
        let local_x = local_idx % grid_w;
        let local_y = Math.floor(local_idx/grid_w);

        for (let y = -radius_px; y <= radius_px; y++) {
          let local_ny = local_y + y;
          if (local_ny >= 0 && local_ny < grid_h) {
            let local_v_idx = px_to_valid[local_ny*grid_w + local_x];
            if (local_v_idx >= 0) {
              local_sum += horiz_pass[local_v_idx];
              local_cnt++;
            }
          }
        }
        out_pass[i] = (local_cnt > 0) ? local_sum/local_cnt : horiz_pass[i];
      }

      //Return statement
      return out_pass;
    }


    /**
     * Normalises a positive field by its within-partition local positive mean using a separable filter,
     * eliminating administrative scaling walls while retaining fluvial and topographic structure.
     * @alias ViscountResidualCovariates.smoothWithinPartitionPositive
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

      //Return statement
      return this.smoothPositiveMaskedPass(mask_data, valid_field, part_id, part_sum, part_cnt, radius_px);
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountResidualCovariates: global.ViscountResidualCovariates };
