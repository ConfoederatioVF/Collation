//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * Empirical Matheron (1962) Variogram Fitter, Per-Horizon Paciorek-Schervish Kernel Builder,
   * Non-Negative Dual Kriging Solver and GeoPNG Diagnostics Exporter for Operation Viscount.
   *
   * @class ViscountMaternVariogram
   */
  global.ViscountMaternVariogram = class {
    /**
     * Step B2: Applies upward-only continuous geodesic Cauchy spatial-neighbourhood survey-completeness
     * harmonisation per catchment (eliminating rectangular 3,5° lat/lon tile-boundary seams).
     * When `preserve_period_dynamics` is true, uses strictly same-period spatial neighbours without all-period injection.
     * @alias ViscountMaternVariogram.B2_harmoniseMacroTiles
     *
     * @param {Object} arg0_options
     * @param {number} [arg0_options.earth_radius_km=6371.0]
     * @param {Array<Object>} arg0_options.obs_list
     * @param {Array<Object>} arg0_options.period_configs
     * @param {boolean} [arg0_options.preserve_dyn=false]
     * @param {Map} [arg0_options.tile_map]
     */
    static B2_harmoniseMacroTiles (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let earth_radius_km = options.earth_radius_km || 6371.0;
      let n_obs = options.obs_list.length;
      let obs_all_z = new Float64Array(n_obs);
      let obs_list = options.obs_list;
      let period_configs = options.period_configs;
      let preserve_dyn = Boolean(options.preserve_dyn);

      //Function body
      //Precompute continuous geodesic Cauchy neighbourhood indices within 650 km (no rectangular tile boxes)
      let nbr_idx = new Array(n_obs);
      let nbr_w = new Array(n_obs);
      let r_scale_km = 240.0;
      let r2_scale = r_scale_km*r_scale_km;
      let max_d2 = 650.0*650.0;

      for (let i = 0; i < n_obs; i++) {
        let oi = obs_list[i];

        obs_all_z[i] = Math.sqrt(Math.max(0, (oi.total_sites_all_periods || 0)/Math.max(1, oi.effective_area_km2)));
        nbr_idx[i] = [];
        nbr_w[i] = [];
      }

      for (let i = 0; i < n_obs; i++) {
        let oi = obs_list[i];

        if (oi.is_frontier_buffer || Math.abs(oi.lat) >= 56.0) continue;
        for (let j = 0; j < n_obs; j++) {
          if (i === j) continue;
          let oj = obs_list[j];

          if (Math.abs(oj.lat) >= 58.0) continue;
          let dot = Math.max(-1, Math.min(1, oi.ux*oj.ux + oi.uy*oj.uy + oi.uz*oj.uz));
          let d2 = earth_radius_km*earth_radius_km*Math.max(0, 2 - 2*dot);

          if (d2 > max_d2) continue;
          nbr_idx[i].push(j);
          nbr_w[i].push(oj.effective_area_km2/(d2 + r2_scale));
        }
      }

      for (let i = 0; i < period_configs.length; i++) {
        let all_z_sum = 0;
        let per_z_sum = 0;
        let pkey = period_configs[i].key;
        let z_arr = new Float64Array(n_obs);

        for (let x = 0; x < n_obs; x++) {
          let o = obs_list[x];

          z_arr[x] = Math.sqrt(Math.max(0, o.eb_densities[pkey] || 0));
          if (!o.is_frontier_buffer && Math.abs(o.lat) < 54.0 && obs_all_z[x] > 0) {
            all_z_sum += o.effective_area_km2*obs_all_z[x];
            per_z_sum += o.effective_area_km2*z_arr[x];
          }
        }
        let per_ratio = (all_z_sum > 1e-6) ? per_z_sum/all_z_sum : 0;

        for (let x = 0; x < n_obs; x++) {
          let ox = obs_list[x];
          let idxs = nbr_idx[x];

          if (idxs.length === 0) continue;
          let wsum = 0;
          let wz = 0;
          let wts = nbr_w[x];

          for (let k = 0; k < idxs.length; k++) {
            wsum += wts[k];
            wz += wts[k]*z_arr[idxs[k]];
          }
          let nbr_prior = (wsum > 0) ? wz/wsum : z_arr[x];
          let z_raw = z_arr[x];

          if (preserve_dyn) {
            if (z_raw > 1e-6 && z_raw < 0.55*nbr_prior) {
              let z_new = 0.55*z_raw + 0.45*nbr_prior;

              ox.eb_densities[pkey] = z_new*z_new;
            } else if (z_raw <= 1e-6 && nbr_prior > 1e-4 && (ox.total_sites_all_periods || 0) > 0) {
              let imp_z = 0.28*nbr_prior;

              ox.eb_densities[pkey] = imp_z*imp_z;
            }
          } else {
            let cap_prior = Math.max(nbr_prior, 0.80*obs_all_z[x]*per_ratio);

            if (z_raw < 0.65*cap_prior && (obs_all_z[x] > 0 || nbr_prior > 1e-4)) {
              let z_new = Math.max(z_raw, 0.50*z_raw + 0.50*cap_prior*0.82);

              ox.eb_densities[pkey] = z_new*z_new;
            }
          }
        }
      }
    }


    /**
     * Step F: Exports GeoPNG rasters and diagnostics JSON (`tau1`, `nugget_to_sill_ratio`, `r_squared`, empirical variograms)
     * consumable by `audit_kriging_sharpness.py`.
     * @alias ViscountMaternVariogram.F_exportBenchmarkRastersAndDiagnostics
     *
     * @param {Object} arg0_surface_bundle
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    static F_exportBenchmarkRastersAndDiagnostics (arg0_surface_bundle, arg1_options) {
      //Convert from parameters
      let surface = arg0_surface_bundle;
      let options = (arg1_options) ? arg1_options : {};

      //Declare local instance variables
      let bundle = surface.kriging_bundle;
      let cfg = bundle.config;
      let dom_dir = bundle.mask_data.domain_dir;
      let meta_path = path.resolve(dom_dir, cfg.kriging_metadata_filename || "config/kriging_diagnostics.json");
      let out_dir = path.resolve(dom_dir, cfg.output_kriged_rasters_subfolder || "1.kriged_rasters");
      let variogram_models = {};

      //Function body
      if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
      if (!fs.existsSync(path.dirname(meta_path))) fs.mkdirSync(path.dirname(meta_path), { recursive: true });

      let period_configs = Array.isArray(cfg.periods) ? cfg.periods : [];
      let period_by_key = {};

      for (let i = 0; i < period_configs.length; i++)
        period_by_key[period_configs[i].key] = period_configs[i];

      let kriged_raster_stats = {};
      let period_keys = Object.keys(surface.fields || {});

      for (let i = 0; i < period_keys.length; i++) {
        let pkey = period_keys[i];
        let model = bundle.kriging_models[pkey];
        let field = surface.fields[pkey];
        let p_cfg = period_by_key[pkey] || {};
        let png_filename = p_cfg.filename || `${pkey}.png`;
        let png_out = path.join(out_dir, png_filename);
        let active_cells = 0;
        let max_val = 0;
        let sum_val = 0;
        let sorted_vals = [];

        if (field) {
          for (let x = 0; x < bundle.mask_data.valid_cell_count; x++) {
            let v = (Number.isFinite(field[x]) && field[x] > 1e-7) ? field[x] : 0;

            field[x] = v;
            if (v > 0) {
              if (v > max_val) max_val = v;
              sum_val += v;
              active_cells++;
              sorted_vals.push(v);
            }
          }
          sorted_vals.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
        }

        if (field && options.write_rasters !== false) {
          let img = new PNG({ colorType: 6, height: bundle.mask_data.grid_height, width: bundle.mask_data.grid_width });
          let fbuf = new ArrayBuffer(4);
          let fdv = new DataView(fbuf);

          for (let x = 0; x < bundle.mask_data.valid_cell_count; x++) {
            let v = field[x];

            if (v > 0 && Number.isFinite(v)) {
              let px = bundle.mask_data.valid_indices[x]*4;

              fdv.setFloat32(0, v, false);
              img.data[px] = fdv.getUint8(0);
              img.data[px + 1] = fdv.getUint8(1);
              img.data[px + 2] = fdv.getUint8(2);
              img.data[px + 3] = fdv.getUint8(3);
            }
          }
          fs.writeFileSync(png_out, PNG.sync.write(img, { colorType: 6, deflateLevel: 6 }));
        }

        kriged_raster_stats[pkey] = {
          active_cells: active_cells,
          filename: png_filename,
          max_value: Number(max_val.toFixed(6)),
          mean_value: Number((sum_val/Math.max(1, active_cells)).toFixed(6)),
          p50_value: Number((sorted_vals[Math.floor(0.50*(sorted_vals.length - 1))] || 0).toFixed(6)),
          p90_value: Number((sorted_vals[Math.floor(0.90*(sorted_vals.length - 1))] || 0).toFixed(6)),
          p99_value: Number((sorted_vals[Math.floor(0.99*(sorted_vals.length - 1))] || 0).toFixed(6)),
          valid_mask_cells: bundle.mask_data.valid_cell_count
        };

        variogram_models[pkey] = {
          c0_nugget: Number(model.c0_nugget.toFixed(6)),
          c1_weight: Number((model.c1_weight || 0.78).toFixed(4)),
          c2_weight: Number((model.c2_weight || 0.22).toFixed(4)),
          effective_short_range_km: model.effective_short_range_km || 0,
          empirical_gammas: model.empirical_gammas || [],
          empirical_u_lags: model.empirical_u_lags || [],
          eta_nugget_ratio: Number(model.eta_nugget_ratio.toFixed(4)),
          nugget_to_sill_ratio: Number(model.nugget_to_sill_ratio.toFixed(4)),
          raw_nugget_to_sill_ratio: Number((model.raw_nugget_to_sill_ratio !== undefined ? model.raw_nugget_to_sill_ratio : model.nugget_to_sill_ratio).toFixed(4)),
          raw_tau1_dimensionless: Number((model.raw_tau1_dimensionless !== undefined ? model.raw_tau1_dimensionless : model.tau1_dimensionless).toFixed(4)),
          residual_kriging_wls_betas: (surface.wls_betas_by_period && surface.wls_betas_by_period[pkey]) ? surface.wls_betas_by_period[pkey] : null,
          residual_r2: surface.r_squared_by_period[pkey] || 0,
          tau1_dimensionless: Number(model.tau1_dimensionless.toFixed(4)),
          tau2_dimensionless: Number(model.tau2_dimensionless.toFixed(4))
        };
      }

      let cov_paths = (cfg.kriging_config && cfg.kriging_config.covariate_paths) ? cfg.kriging_config.covariate_paths : {};
      let diagnostics = {
        active_domestic_catchments: bundle.obs_bundle.active_domestic_catchments || 0,
        adm2_coverage_ratio: bundle.obs_bundle.adm2_coverage_ratio || 0,
        domestic_catchments: bundle.obs_bundle.domestic_catchments || 0,
        domestic_site_count_unique_sum: bundle.obs_bundle.domestic_site_count_unique_sum || 0,
        generated_at_gmt0: new Date().toISOString(),
        kriged_raster_stats: kriged_raster_stats,
        median_voronoi_radius_km: Number((bundle.obs_bundle.median_radius_km || 0).toFixed(2)),
        p90_voronoi_radius_km: Number((bundle.obs_bundle.p90_radius_km || 0).toFixed(2)),
        raw_tau1_dimensionless: Number((bundle.raw_tau1_dimensionless !== undefined ? bundle.raw_tau1_dimensionless : bundle.tau1_dimensionless).toFixed(4)),
        residual_kriging_wls_betas: surface.wls_betas_by_period || {},
        tau1_dimensionless: Number(bundle.tau1_dimensionless.toFixed(4)),
        tau2_dimensionless: Number(bundle.tau2_dimensionless.toFixed(4)),
        urban_mask_applied: true,
        urban_mask_buffer_radius: (cov_paths.urban_mask_buffer_radius !== undefined) ? Number(cov_paths.urban_mask_buffer_radius) : 2,
        valid_cells: bundle.mask_data.valid_cell_count,
        variogram_models: variogram_models,
        wls_covariates_active: Boolean(surface.wls_covariates_active)
      };
      fs.writeFileSync(meta_path, JSON.stringify(diagnostics, null, 2), "utf8");

      //Return statement
      return diagnostics;
    }
    /**
     * Fits a dimensionless Matérn (`nu = 3/2`) `tau1` range from an empirical normalized semivariogram array.
     * @alias ViscountMaternVariogram.fitTauFromBins
     *
     * @param {Array<number>} arg0_gammas
     * @param {Array<number>} arg1_lags
     * @param {Array<number>} arg2_pop_bins
     * @param {number} arg3_default_tau1
     *
     * @returns {Object}
     */
    static fitTauFromBins (arg0_gammas, arg1_lags, arg2_pop_bins, arg3_default_tau1) {
      //Convert from parameters
      let gammas = arg0_gammas;
      let lags = arg1_lags;
      let pop_bins = arg2_pop_bins;
      let default_tau1 = arg3_default_tau1;

      //Guard clauses
      if (!Array.isArray(pop_bins) || pop_bins.length < 2)
        return { raw_tau1: default_tau1, sill: 1.0, c0: 0.08 };

      //Declare local instance variables
      let p0 = pop_bins[0];
      let p1 = pop_bins[1];
      let sqrt3 = Math.sqrt(3);

      //Function body
      if (pop_bins.length > 2 && gammas[pop_bins[2]] > gammas[p1]) p1 = pop_bins[2];
      let g0 = gammas[p0];
      let g1 = gammas[p1];
      let plateau_bins = [];

      for (let x = 0; x < pop_bins.length; x++) {
        let bi = pop_bins[x];

        if (lags[bi] >= 2.60 && lags[bi] <= 7.00)
          plateau_bins.push(bi);
      }
      let p_tail = (plateau_bins.length >= 2) ?
        plateau_bins :
        pop_bins.slice(Math.min(3, Math.max(0, pop_bins.length - 3)), Math.min(pop_bins.length, 6));

      if (p_tail.length === 0) p_tail = pop_bins.slice(Math.max(0, pop_bins.length - 3));
      let sill = 0;

      for (let i = 0; i < p_tail.length; i++) sill += gammas[p_tail[i]]/Math.max(1, p_tail.length);
      sill = Math.max(0.1, sill);

      let s0_pool = sqrt3*lags[p0]/1.20;
      let s1_pool = sqrt3*lags[p1]/1.20;
      let psi0_pool = 1 - (1 + s0_pool)*Math.exp(-s0_pool);
      let psi1_pool = 1 - (1 + s1_pool)*Math.exp(-s1_pool);
      let slope_p = Math.max(0, (g1 - g0)/Math.max(1e-6, psi1_pool - psi0_pool));
      let c0 = Math.max(0, g0 - psi0_pool*slope_p);
      let target1 = c0 + (1 - (1 + sqrt3)*Math.exp(-sqrt3))*Math.max(1e-6, sill - c0);
      let poly_pts = [[0, c0]];
      let crossed_t1 = false;
      let raw_tau1 = default_tau1;

      for (let idx_p = 0; idx_p < pop_bins.length; idx_p++)
        poly_pts.push([lags[pop_bins[idx_p]], gammas[pop_bins[idx_p]]]);

      for (let idx_p = 0; idx_p < poly_pts.length - 1; idx_p++) {
        if (poly_pts[idx_p][1] <= target1 && poly_pts[idx_p + 1][1] >= target1) {
          let frac = (target1 - poly_pts[idx_p][1])/Math.max(1e-8, poly_pts[idx_p + 1][1] - poly_pts[idx_p][1]);

          raw_tau1 = poly_pts[idx_p][0] + frac*(poly_pts[idx_p + 1][0] - poly_pts[idx_p][0]);
          crossed_t1 = true;
          break;
        }
      }
      if (!crossed_t1)
        raw_tau1 = (gammas[p0] >= target1) ? lags[p0] : lags[pop_bins[pop_bins.length - 1]];

      //Return statement
      return { raw_tau1: raw_tau1, sill: sill, c0: c0 };
    }


    /**
     * Step C: Derives Matheron (1962) empirical variograms, empirical zero-lag nugget ratios (`<= 0,22` guard),
     * two-scale Paciorek-Schervish non-stationary Matérn (`nu = 3/2`) covariance kernels (`tau1 in [0,55, 1,50]`)
     * and solves the Non-Negative Dual Kriging system via Step D.
     * When `preserve_period_dynamics === true`, fits per-period `(tau1_p, tau2_p)` from each horizon's own empirical variogram.
     * @alias ViscountMaternVariogram.C_fitTwoScaleNonStationaryMatern
     *
     * @param {Object} arg0_obs_bundle
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    static C_fitTwoScaleNonStationaryMatern (arg0_obs_bundle, arg1_options) {
      //Convert from parameters
      let obs_bundle = arg0_obs_bundle;
      let options = (arg1_options) ? arg1_options : {};

      //Guard clauses
      if (!obs_bundle || obs_bundle.obs_count === 0) {
        console.error("[ViscountMaternVariogram] Cannot fit variogram with zero observations.");
        return null;
      }

      //Declare local instance variables
      let config = obs_bundle.config;
      let dim_lag_bins = (config.kriging_config && Array.isArray(config.kriging_config.dimensionless_lag_bins)) ?
        config.kriging_config.dimensionless_lag_bins : [0.75, 1.25, 1.85, 2.60, 3.60, 5.00, 7.00, 9.50, 13.00, 18.00];
      let earth_radius_km = Number((config.kriging_config && config.kriging_config.earth_radius_km) || 6371);
      let kriging_models = {};
      let matern_lut = new Float32Array(8192);
      let n_bins = dim_lag_bins.length;
      let n_obs = obs_bundle.obs_count;
      let obs_list = obs_bundle.obs_list;
      let obs_r = obs_bundle.obs_radius_km;
      let pair_bins = [];
      let period_configs = Array.isArray(config.periods) ? config.periods : [];
      let period_cov = new Float64Array(n_obs*n_obs);
      let pooled_hits = new Int32Array(dim_lag_bins.length);
      let pooled_norm_gammas = new Float64Array(dim_lag_bins.length);
      let pooled_pair_totals = new Int32Array(dim_lag_bins.length);
      let pooled_u_lags = new Float64Array(dim_lag_bins.length);
      let preserve_dyn = Boolean(config.kriging_config && config.kriging_config.preserve_period_dynamics);
      let scale_pref_mat = new Float32Array(n_obs*n_obs);
      let sqrt3 = Math.sqrt(3);
      let total_dom_pairs = 0;
      let u_matrix = new Float32Array(n_obs*n_obs);

      //Function body
      for (let i = 0; i < n_bins; i++) pair_bins.push([]);
      for (let i = 0; i < 8192; i++) {
        let local_s = sqrt3*(8*i)/8191;

        matern_lut[i] = (1 + local_s)*Math.exp(-local_s);
      }

      for (let i = 0; i < n_obs; i++) {
        scale_pref_mat[i*n_obs + i] = 1;
        u_matrix[i*n_obs + i] = 0;
        for (let x = i + 1; x < n_obs; x++) {
          let dot = Math.max(-1, Math.min(1,
            obs_bundle.obs_ux[i]*obs_bundle.obs_ux[x] +
            obs_bundle.obs_uy[i]*obs_bundle.obs_uy[x] +
            obs_bundle.obs_uz[i]*obs_bundle.obs_uz[x]
          ));
          let c2 = Math.max(0, 2 - 2*dot);
          let h = earth_radius_km*Math.sqrt(c2)*(1 + c2/24 + (3*c2*c2)/640);
          let ri = obs_r[i];
          let rx = obs_r[x];
          let r_eff = Math.sqrt(0.5*(ri*ri + rx*rx));
          let pref = (2*ri*rx)/Math.max(1e-8, ri*ri + rx*rx);
          let u = h/Math.max(1e-6, r_eff);

          scale_pref_mat[i*n_obs + x] = pref;
          scale_pref_mat[x*n_obs + i] = pref;
          u_matrix[i*n_obs + x] = u;
          u_matrix[x*n_obs + i] = u;

          if (!obs_list[i].is_frontier_buffer && !obs_list[x].is_frontier_buffer && u <= dim_lag_bins[n_bins - 1]) {
            let both_empty_arctic = (
              (obs_list[i].total_sites_all_periods || 0) === 0 &&
              (obs_list[x].total_sites_all_periods || 0) === 0 &&
              obs_list[i].lat > 52.0 &&
              obs_list[x].lat > 52.0
            );
            let skip_ocean_gap = (obs_bundle.median_radius_km < 15.0 && h > 140.0);

            if (!both_empty_arctic && !skip_ocean_gap) {
              for (let y = 0; y < n_bins; y++) {
                if (u <= dim_lag_bins[y]) {
                  pair_bins[y].push(i, x, u);
                  total_dom_pairs++;
                  break;
                }
              }
            }
          }
        }
      }

      let min_bin_pairs = Math.max(4, Math.min(25, Math.round(0.0025*total_dom_pairs)));
      let period_z_map = {};
      let period_obs_map = {};

      for (let i = 0; i < period_configs.length; i++) {
        let dom_n = 0;
        let emp_gammas = [];
        let emp_lags = [];
        let pkey = period_configs[i].key;
        let sample_var = 0;
        let sill_norm = 0;
        let z = new Float64Array(n_obs);
        let z_mean = 0;

        for (let x = 0; x < n_obs; x++) {
          z[x] = Math.sqrt(Math.max(0, obs_list[x].eb_densities[pkey] || 0));
          if (!obs_list[x].is_frontier_buffer) {
            z_mean += z[x];
            dom_n++;
          }
        }
        z_mean /= Math.max(1, dom_n);
        for (let x = 0; x < n_obs; x++)
          if (!obs_list[x].is_frontier_buffer)
            sample_var += (z[x] - z_mean)*(z[x] - z_mean);
        sample_var = Math.max(1e-8, sample_var/Math.max(1, dom_n));

        let bin_nb = new Int32Array(n_bins);

        for (let x = 0; x < n_bins; x++) {
          let bin = pair_bins[x];
          let nb = bin.length/3;
          let sq_sum = 0;
          let u_sum = 0;

          for (let y = 0; y < bin.length; y += 3) {
            let dz = z[bin[y]] - z[bin[y + 1]];

            sq_sum += 0.5*dz*dz;
            u_sum += bin[y + 2];
          }
          bin_nb[x] = nb;
          emp_gammas.push((nb > 0) ? sq_sum/nb : -1);
          emp_lags.push((nb > 0) ? u_sum/nb : dim_lag_bins[x]);
        }

        let pop_bins = [];

        for (let x = 0; x < n_bins; x++)
          if (bin_nb[x] >= min_bin_pairs) pop_bins.push(x);
        if (pop_bins.length < 2) {
          pop_bins = [];
          for (let x = 0; x < n_bins; x++)
            if (bin_nb[x] > 0) pop_bins.push(x);
        }

        for (let x = 0; x < n_bins; x++) {
          if (bin_nb[x] >= min_bin_pairs) continue;
          let best_x = (pop_bins.length > 0) ? pop_bins[0] : -1;
          let best_d = 1e9;

          for (let y = 0; y < pop_bins.length; y++) {
            let py = pop_bins[y];

            if (Math.abs(py - x) < best_d) {
              best_d = Math.abs(py - x);
              best_x = py;
            }
          }
          if (best_x >= 0) emp_gammas[x] = emp_gammas[best_x];
          else if (emp_gammas[x] < 0) emp_gammas[x] = sample_var;
        }

        let norm_g_period = emp_gammas.map(function (arg0_g) { return arg0_g/sample_var; });

        for (let x = 0; x < n_bins; x++) {
          if (bin_nb[x] >= min_bin_pairs) {
            pooled_norm_gammas[x] += norm_g_period[x];
            pooled_hits[x]++;
            pooled_pair_totals[x] += bin_nb[x];
            pooled_u_lags[x] += emp_lags[x];
          }
        }

        let p_plateau = [];

        for (let x = 0; x < pop_bins.length; x++) {
          let bi = pop_bins[x];

          if (emp_lags[bi] >= 2.60 && emp_lags[bi] <= 7.00) p_plateau.push(bi);
        }
        let tail_bins = (p_plateau.length >= 2) ?
          p_plateau :
          pop_bins.slice(Math.min(3, Math.max(0, pop_bins.length - 3)), Math.min(pop_bins.length, 6));

        if (tail_bins.length === 0) tail_bins = pop_bins.slice(Math.max(0, pop_bins.length - 3));
        for (let x = 0; x < tail_bins.length; x++)
          sill_norm += (emp_gammas[tail_bins[x]]/sample_var)/Math.max(1, tail_bins.length);
        sill_norm = Math.max(0.1, sill_norm);

        let b0 = (pop_bins.length > 0) ? pop_bins[0] : 0;
        let b1 = (pop_bins.length > 1) ? pop_bins[1] : b0;

        if (pop_bins.length > 2 && emp_gammas[pop_bins[2]] > emp_gammas[b1]) b1 = pop_bins[2];
        let g0 = emp_gammas[b0]/sample_var;
        let g1 = emp_gammas[b1]/sample_var;
        let s0_p = sqrt3*emp_lags[b0]/1.20;
        let s1_p = sqrt3*emp_lags[b1]/1.20;
        let psi0 = 1 - (1 + s0_p)*Math.exp(-s0_p);
        let psi1 = 1 - (1 + s1_p)*Math.exp(-s1_p);
        let slope_psi = (b1 !== b0) ? Math.max(0, (g1 - g0)/Math.max(1e-6, psi1 - psi0)) : 0;
        let raw_c0_norm = Math.max(0, g0 - psi0*slope_psi);
        let raw_nugget_ratio = raw_c0_norm/Math.max(1e-6, sill_norm);
        let c0_norm = Math.max(0.04*sill_norm, Math.min(0.22*sill_norm, raw_c0_norm));
        let eta = c0_norm/Math.max(0.05*sill_norm, sill_norm - c0_norm);
        let s_obs = new Float64Array(n_obs);

        for (let x = 0; x < n_obs; x++) s_obs[x] = obs_list[x].periods[pkey] || 0;

        period_obs_map[pkey] = {
          c0_norm: c0_norm,
          empirical_gammas: emp_gammas,
          empirical_u_lags: emp_lags,
          eta_nugget_ratio: eta,
          norm_gammas: norm_g_period,
          pop_bins: pop_bins,
          raw_nugget_to_sill_ratio: raw_nugget_ratio,
          s_obs: s_obs,
          sample_variance: sample_var,
          sill_norm: sill_norm,
          z_mean: z_mean
        };
        period_z_map[pkey] = z;
      }

      let raw_tau1 = (options.tau1) ? Number(options.tau1) : 1.25;
      let tau1 = Math.max(0.60, Math.min(1.50, raw_tau1));
      let tau2 = Math.max(2.10, Math.min(3.50, options.tau2 || 2.60));
      let pop_pooled = [];

      for (let i = 0; i < n_bins; i++) {
        if (pooled_hits[i] > 0) {
          pooled_norm_gammas[i] /= pooled_hits[i];
          pooled_u_lags[i] /= pooled_hits[i];
          if (pooled_pair_totals[i] >= 3*Math.max(1, period_configs.length))
            pop_pooled.push(i);
        }
      }
      if (pop_pooled.length < 2) {
        pop_pooled = [];
        for (let i = 0; i < n_bins; i++)
          if (pooled_hits[i] > 0) pop_pooled.push(i);
      }
      if (pop_pooled.length >= 2) {
        let pooled_fit = this.fitTauFromBins(pooled_norm_gammas, pooled_u_lags, pop_pooled, raw_tau1);

        raw_tau1 = pooled_fit.raw_tau1;
        tau1 = Math.max(preserve_dyn ? 0.55 : 0.60, Math.min(preserve_dyn ? 1.35 : 1.50, raw_tau1));
        tau2 = Math.max(1.85*tau1, Math.min(3.40, tau2));
      }

      //Preallocate kernel buffers (rebuilt per period when per-period variogram dynamics enabled)
      let m1_mat = new Float64Array(n_obs*n_obs);
      let m2_mat = new Float64Array(n_obs*n_obs);
      let fillKernels = function (arg0_t1, arg1_t2) {
        for (let i = 0; i < n_obs; i++) {
          m1_mat[i*n_obs + i] = 1;
          m2_mat[i*n_obs + i] = 1;
          for (let x = i + 1; x < n_obs; x++) {
            let idx = i*n_obs + x;
            let pref = scale_pref_mat[idx];
            let s1 = sqrt3*u_matrix[idx]/arg0_t1;
            let s2 = sqrt3*u_matrix[idx]/arg1_t2;
            let v1 = pref*(1 + s1)*Math.exp(-s1);
            let v2 = pref*(1 + s2)*Math.exp(-s2);

            m1_mat[idx] = v1;
            m1_mat[x*n_obs + i] = v1;
            m2_mat[idx] = v2;
            m2_mat[x*n_obs + i] = v2;
          }
        }
      };

      if (!preserve_dyn) fillKernels(tau1, tau2);

      let tau1_sum = 0;
      let tau2_sum = 0;
      let tau_count = 0;

      for (let i = 0; i < period_configs.length; i++) {
        let pkey = period_configs[i].key;
        let obs = period_obs_map[pkey];
        let eta = obs.eta_nugget_ratio;
        let c1 = preserve_dyn ? 0.80 : 0.78;
        let c2 = preserve_dyn ? 0.20 : 0.22;
        let p_raw_tau1 = raw_tau1;
        let p_tau1 = tau1;
        let p_tau2 = tau2;

        if (preserve_dyn) {
          let p_fit = this.fitTauFromBins(obs.norm_gammas, obs.empirical_u_lags, obs.pop_bins, raw_tau1);

          p_raw_tau1 = p_fit.raw_tau1;
          p_tau1 = Math.max(0.55, Math.min(1.35, p_raw_tau1));
          p_tau2 = Math.max(1.85*p_tau1, Math.min(3.10, p_tau1*2.15));
          fillKernels(p_tau1, p_tau2);
        }
        tau1_sum += p_tau1;
        tau2_sum += p_tau2;
        tau_count++;

        for (let x = 0; x < n_obs; x++) {
          let row = x*n_obs;

          period_cov[row + x] = 1 + eta;
          for (let y = x + 1; y < n_obs; y++) {
            let kval = c1*m1_mat[row + y] + c2*m2_mat[row + y];

            period_cov[row + y] = kval;
            period_cov[y*n_obs + x] = kval;
          }
        }

        let raw_z = period_z_map[pkey];
        let z_adj = new Float64Array(n_obs);
        let bleed_k = preserve_dyn ? 0.06 : 0.18;
        let kw_floor = preserve_dyn ? 0.03 : 1e-3;

        for (let x = 0; x < n_obs; x++) {
          if (raw_z[x] > 0) {
            z_adj[x] = raw_z[x];
            continue;
          }
          let act_w = 0;
          let sum_w = 0;
          let sum_wz = 0;
          let row_x = x*n_obs;

          for (let y = 0; y < n_obs; y++) {
            if (y === x) continue;
            let kw = m2_mat[row_x + y];

            if (kw < kw_floor) continue;
            let r2 = kw*kw;

            sum_w += r2;
            if (raw_z[y] > 0) {
              act_w += r2;
              sum_wz += r2*raw_z[y];
            }
          }
          let act_frac = (sum_w > 1e-6) ? act_w/sum_w : 0;
          let nbr_z = (act_w > 1e-6) ? sum_wz/act_w : 0;

          z_adj[x] = bleed_k*act_frac*nbr_z;
        }

        let dual_weights = this.D_solveProjectedNonNegativeDualKriging(period_cov, z_adj, n_obs);
        let zh_mean = 0;
        let zh_var = 0;

        for (let x = 0; x < n_obs; x++)
          zh_mean += Math.max(0, z_adj[x] - eta*dual_weights[x]);
        zh_mean /= Math.max(1, n_obs);
        for (let x = 0; x < n_obs; x++) {
          let dzh = Math.max(0, z_adj[x] - eta*dual_weights[x]) - zh_mean;

          zh_var += dzh*dzh;
        }
        zh_var = Math.max(1e-8, zh_var/Math.max(1, n_obs));

        let structural_share = Math.max(0.1, (obs.sill_norm - obs.c0_norm)/Math.max(1e-8, obs.sill_norm));
        let var_restore = Math.max(1.0, Math.min(1.45, Math.sqrt((obs.sample_variance*structural_share)/zh_var)));

        kriging_models[pkey] = {
          c0_nugget: (obs.c0_norm/obs.sill_norm)*obs.sample_variance,
          c1_weight: c1,
          c2_weight: c2,
          centroid_variance_restoration: var_restore,
          dual_weights: dual_weights,
          effective_short_range_km: Number((p_raw_tau1*(obs_bundle.median_radius_km || 0)).toFixed(2)),
          empirical_gammas: obs.empirical_gammas.map(function (arg0_v) { return Number(Number(arg0_v).toFixed(6)); }),
          empirical_u_lags: obs.empirical_u_lags.map(function (arg0_v) { return Number(Number(arg0_v).toFixed(4)); }),
          eta_nugget_ratio: eta,
          nugget_to_sill_ratio: obs.c0_norm/obs.sill_norm,
          raw_nugget_to_sill_ratio: obs.raw_nugget_to_sill_ratio,
          raw_tau1_dimensionless: p_raw_tau1,
          s_obs: obs.s_obs,
          sample_variance: obs.sample_variance,
          tau1_dimensionless: p_tau1,
          tau2_dimensionless: p_tau2,
          total_sites: (obs_bundle.period_totals && obs_bundle.period_totals[pkey]) ? obs_bundle.period_totals[pkey] : 0,
          z_adj: z_adj
        };
      }

      let rep_tau1 = (preserve_dyn && tau_count > 0) ? (tau1_sum/tau_count) : tau1;
      let rep_tau2 = (preserve_dyn && tau_count > 0) ? (tau2_sum/tau_count) : tau2;

      //Return statement
      return {
        config: config,
        kriging_models: kriging_models,
        mask_data: obs_bundle.mask_data,
        matern_lut: matern_lut,
        obs_bundle: obs_bundle,
        raw_tau1_dimensionless: raw_tau1,
        tau1_dimensionless: rep_tau1,
        tau2_dimensionless: rep_tau2
      };
    }


    /**
     * Step D: Solves `(C + eta*I)*w = z_adj` with `w >= 0` via Cholesky warm-start and Projected Gauss-Seidel sweeps.
     * @alias ViscountMaternVariogram.D_solveProjectedNonNegativeDualKriging
     *
     * @param {Float64Array} arg0_cov_matrix
     * @param {Float64Array} arg1_z_adj
     * @param {number} arg2_n
     *
     * @returns {Float32Array}
     */
    static D_solveProjectedNonNegativeDualKriging (arg0_cov_matrix, arg1_z_adj, arg2_n) {
      //Convert from parameters
      let cov_mat = arg0_cov_matrix;
      let z_adj = arg1_z_adj;
      let n = arg2_n;

      //Declare local instance variables
      let out_w = new Float32Array(n);
      let w_vec = new Float64Array(n);

      //Function body
      if (n <= 1800) {
        let chol_L = new Float64Array(n*n);
        let sol_x = new Float64Array(n);
        let sol_y = new Float64Array(n);

        for (let i = 0; i < n; i++) {
          let row_i = i*n;

          for (let x = 0; x <= i; x++) {
            let row_x = x*n;
            let sum = cov_mat[row_i + x];

            for (let y = 0; y < x; y++)
              sum -= chol_L[row_i + y]*chol_L[row_x + y];
            if (i === x) {
              chol_L[row_i + i] = Math.sqrt(Math.max(1e-10, sum));
            } else {
              chol_L[row_i + x] = sum/chol_L[row_x + x];
            }
          }
        }

        for (let i = 0; i < n; i++) {
          let row = i*n;
          let sum = z_adj[i];

          for (let x = 0; x < i; x++) sum -= chol_L[row + x]*sol_y[x];
          sol_y[i] = sum/chol_L[row + i];
        }
        for (let i = n - 1; i >= 0; i--) {
          let sum = sol_y[i];

          for (let x = i + 1; x < n; x++) sum -= chol_L[x*n + i]*sol_x[x];
          sol_x[i] = sum/chol_L[i*n + i];
        }
        for (let i = 0; i < n; i++) w_vec[i] = Math.max(0, sol_x[i]);

        for (let iter = 0; iter < 60; iter++) {
          for (let x = 0; x < n; x++) {
            let diag = cov_mat[x*n + x];
            let rhs = z_adj[x];
            let row = x*n;

            for (let y = 0; y < n; y++)
              if (y !== x && w_vec[y] > 0) rhs -= cov_mat[row + y]*w_vec[y];
            w_vec[x] = (diag > 1e-12) ? Math.max(0, rhs/diag) : 0;
          }
        }
      } else {
        //Sparse active-neighbor Projected Gauss-Seidel solver for large continental domains (n > 1800)
        let diag_arr = new Float64Array(n);
        let nbr_idx = new Array(n);
        let nbr_val = new Array(n);

        for (let x = 0; x < n; x++) {
          let idxs = [];
          let row = x*n;
          let vals = [];

          diag_arr[x] = cov_mat[row + x];
          w_vec[x] = (diag_arr[x] > 1e-12) ? Math.max(0, z_adj[x]/diag_arr[x]) : 0;
          for (let y = 0; y < n; y++) {
            if (y !== x && cov_mat[row + y] >= 4e-4) {
              idxs.push(y);
              vals.push(cov_mat[row + y]);
            }
          }
          nbr_idx[x] = Int32Array.from(idxs);
          nbr_val[x] = Float64Array.from(vals);
        }

        for (let iter = 0; iter < 120; iter++) {
          let max_delta = 0;

          for (let x = 0; x < n; x++) {
            let diag = diag_arr[x];
            let idxs = nbr_idx[x];
            let k_len = idxs.length;
            let rhs = z_adj[x];
            let vals = nbr_val[x];

            for (let y = 0; y < k_len; y++) {
              let wy = w_vec[idxs[y]];

              if (wy > 0) rhs -= vals[y]*wy;
            }
            let nw = (diag > 1e-12) ? Math.max(0, rhs/diag) : 0;
            let diff = Math.abs(nw - w_vec[x]);

            if (diff > max_delta) max_delta = diff;
            w_vec[x] = nw;
          }
          if (max_delta < 1e-6) break;
        }
      }

      for (let i = 0; i < n; i++) out_w[i] = w_vec[i];

      //Return statement
      return out_w;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountMaternVariogram: global.ViscountMaternVariogram };
