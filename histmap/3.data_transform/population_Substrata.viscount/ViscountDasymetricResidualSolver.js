//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { ViscountKrigingGPU } = global.ViscountKrigingGPU ? global : require("./ViscountKrigingGPU.js");

//Initialise functions
{
  /**
   * Terrain-Barrier-Aware Tightened Signed Residual Matérn (`nu = 3/2`) Solver & Multi-Period Evaluator
   * for Operation Viscount Dasymetric Residual Kriging across all macro-regions.
   *
   * Applies symmetric elevation-break attenuation (`exp(-(|E_i - E_j| / H_break)^1.6)`) and
   * catchment-step tightening so archaeological residuals never bleed diffusely across mountain ranges
   * or hydrological catchment divides.
   *
   * @class ViscountDasymetricResidualSolver
   */
  global.ViscountDasymetricResidualSolver = class {
    /**
     * Step A: Builds and caches the sparse terrain-barrier-aware Matérn (`nu = 3/2`) covariance matrix
     * and representative catchment elevations for fast signed Gauss-Seidel residual kriging.
     * @alias ViscountDasymetricResidualSolver.A_getOrBuildSparseMaternMatrix
     *
     * @param {Object} arg0_bundle
     *
     * @returns {Object}
     */
    static A_getOrBuildSparseMaternMatrix (arg0_bundle) {
      //Convert from parameters
      let bundle = arg0_bundle;

      //Guard clauses
      if (bundle._sparse_matern_ctx) return bundle._sparse_matern_ctx;

      //Declare local instance variables
      let bio_covs = bundle._bio_covs || null;
      let cell_area = bundle.mask_data.cell_land_area;
      let cell_obs = bundle.obs_bundle.cell_nearest_obs;
      let elev_valid = (bio_covs && bio_covs.elev_valid) ? bio_covs.elev_valid : null;
      let hu_ctx = bundle._hu_ctx || null;
      let k_cfg = (bundle.config && bundle.config.kriging_config) ? bundle.config.kriging_config : {};
      let c1 = Number.isFinite(k_cfg.residual_c1_weight) ? Number(k_cfg.residual_c1_weight) : 0.84;
      let c2 = Math.max(0.0, 1.0 - c1);
      let earth_r = bundle.mask_data.earth_radius_km || 6371;
      let elev_barrier_m = Number(
        (hu_ctx && hu_ctx.elevation_barrier_m) || k_cfg.elevation_barrier_m || 650.0
      );
      let eta = 0.10;
      let tau1_eff = Math.max(0.72, Math.min(1.15, 0.78*(bundle.tau1_dimensionless || 1.30)));
      let tau2_eff = Math.max(1.50, Math.min(2.25, 0.74*(bundle.tau2_dimensionless || 2.80)));
      let inv_tau1 = 1/tau1_eff;
      let inv_tau2 = 1/tau2_eff;
      let n_obs = bundle.obs_bundle.obs_count;
      let n_valid = bundle.mask_data.valid_cell_count;
      let obs_elev_m = new Float32Array(n_obs);
      let obs_r = bundle.obs_bundle.obs_radius_km;
      let obs_ux = bundle.obs_bundle.obs_ux;
      let obs_uy = bundle.obs_bundle.obs_uy;
      let obs_uz = bundle.obs_bundle.obs_uz;
      let sqrt3 = Math.sqrt(3);
      let max_cell_r = 0;

      //Function body
      //Compute area-weighted representative elevation per observation catchment
      if (elev_valid && cell_obs) {
        let e_area = new Float64Array(n_obs);
        let e_sum = new Float64Array(n_obs);

        for (let i = 0; i < n_valid; i++) {
          let o = cell_obs[i];

          if (o >= 0 && o < n_obs) {
            let a = Math.max(1.0, cell_area[i]);

            e_area[o] += a;
            e_sum[o] += a*elev_valid[i];
          }
        }
        for (let o = 0; o < n_obs; o++)
          obs_elev_m[o] = (e_area[o] > 0) ? (e_sum[o]/e_area[o]) : 150.0;
      } else {
        obs_elev_m.fill(150.0);
      }

      for (let i = 0; i < n_valid; i++)
        if (bundle.obs_bundle.cell_radius_km[i] > max_cell_r) max_cell_r = bundle.obs_bundle.cell_radius_km[i];

      let min_dot = new Float64Array(n_obs);

      for (let x = 0; x < n_obs; x++) {
        let h_max = 7.99/inv_tau2*Math.sqrt(0.5*(max_cell_r*max_cell_r + obs_r[x]*obs_r[x]));

        min_dot[x] = (h_max >= Math.PI*earth_r) ? -2.0 : (Math.cos(h_max/earth_r) - 1e-4);
      }

      let diag = new Float64Array(n_obs);
      let inv_eb = 1.0/Math.max(150.0, elev_barrier_m);
      let nbr_idx = new Array(n_obs);
      let nbr_val = new Array(n_obs);

      for (let i = 0; i < n_obs; i++) {
        diag[i] = 1.0 + eta;
        nbr_idx[i] = [];
        nbr_val[i] = [];
      }

      for (let i = 0; i < n_obs; i++) {
        let ei = obs_elev_m[i];
        let ri = obs_r[i];

        for (let j = i + 1; j < n_obs; j++) {
          let dot = Math.max(-1, Math.min(1, obs_ux[i]*obs_ux[j] + obs_uy[i]*obs_uy[j] + obs_uz[i]*obs_uz[j]));
          let c2_c = Math.max(0, 2 - 2*dot);
          let h = earth_r*Math.sqrt(c2_c)*(1 + c2_c/24);
          let rj = obs_r[j];
          let r2_sum = ri*ri + rj*rj;
          let u = h/Math.sqrt(0.5*r2_sum);
          let v2 = u*inv_tau2;

          if (v2 >= 7.99) continue;
          let pref = (2*ri*rj)/Math.max(1e-8, r2_sum);
          let s1 = sqrt3*u*inv_tau1;
          let s2 = sqrt3*v2;
          let de_norm = Math.abs(ei - obs_elev_m[j])*inv_eb;
          let elev_att = (de_norm > 0.05) ? Math.exp(-Math.pow(de_norm, 1.6)) : 1.0;
          let kval = elev_att*pref*(c1*(1 + s1)*Math.exp(-s1) + c2*(1 + s2)*Math.exp(-s2));

          if (kval >= 0.001) {
            nbr_idx[i].push(j);
            nbr_val[i].push(kval);
            nbr_idx[j].push(i);
            nbr_val[j].push(kval);
          }
        }
      }
      bundle._sparse_matern_ctx = {
        c1: c1,
        c2: c2,
        diag: diag,
        elev_barrier_m: elev_barrier_m,
        inv_tau1: inv_tau1,
        inv_tau2: inv_tau2,
        min_dot: min_dot,
        nbr_idx: nbr_idx,
        nbr_val: nbr_val,
        obs_elev_m: obs_elev_m
      };

      //Return statement
      return bundle._sparse_matern_ctx;
    }


    /**
     * Step B: Solves shrinkage-weighted signed catchment log-residual dual weights (`v_vec`) around
     * `prior_dens` via sparse Gauss-Seidel iterations.
     * @alias ViscountDasymetricResidualSolver.B_solveResidualDualWeights
     *
     * @param {Object} arg0_kriging_bundle
     * @param {Object} arg1_prior_bundle
     * @param {Float64Array} arg2_z_obs
     * @param {Float64Array} arg3_s_obs
     *
     * @returns {Float64Array}
     */
    static B_solveResidualDualWeights (arg0_kriging_bundle, arg1_prior_bundle, arg2_z_obs, arg3_s_obs) {
      //Convert from parameters
      let bundle = arg0_kriging_bundle;
      let prior_bundle = arg1_prior_bundle;
      let z_obs = arg2_z_obs;
      let s_obs = arg3_s_obs;

      //Declare local instance variables
      let cell_area = bundle.mask_data.cell_land_area;
      let cell_obs = bundle.obs_bundle.cell_nearest_obs;
      let mask_data = bundle.mask_data;
      let n_obs = bundle.obs_bundle.obs_count;
      let n_valid = mask_data.valid_cell_count;
      let obs_list = bundle.obs_bundle.obs_list;
      let perm_ice = (bundle._bio_covs && bundle._bio_covs.perm_ice) ? bundle._bio_covs.perm_ice : null;
      let prior_dens = prior_bundle.prior_dens;
      let r_area = new Float64Array(n_obs);
      let r_hab_area = new Float64Array(n_obs);
      let r_prior_sum = new Float64Array(n_obs);
      let r_set_sum = new Float64Array(n_obs);
      let sp_ctx = this.A_getOrBuildSparseMaternMatrix(bundle);
      let u_set = prior_bundle.u_set || null;

      //Function body
      for (let i = 0; i < n_valid; i++) {
        let o = cell_obs[i];

        if (o < 0 || o >= n_obs) continue;
        let a = cell_area[i]*(perm_ice ? perm_ice[i] : 1.0);

        if (a <= 0) continue;
        r_area[o] += a;
        if (prior_dens[i] > 0) {
          r_hab_area[o] += a;
          r_prior_sum[o] += a*prior_dens[i];
          if (u_set) r_set_sum[o] += a*u_set[i];
        }
      }

      let obs_prior_z = new Float64Array(n_obs);
      let p_z_sum = 0;
      let tot_r_area = 0;
      let z_o_sum = 0;

      for (let o = 0; o < n_obs; o++) {
        if (obs_list[o].is_frontier_buffer || r_hab_area[o] <= 0 || r_prior_sum[o] <= 0) continue;
        //Pycnophylactic catchment-area denominator (capped at 10x habitable area to avoid Arctic/desert single-pixel blowups)
        let eff_area = Math.min(r_area[o], 10.0*r_hab_area[o]);
        let pz = Math.sqrt(Math.max(1e-7, r_prior_sum[o]/eff_area));

        obs_prior_z[o] = pz;
        p_z_sum += eff_area*pz;
        tot_r_area += eff_area;
        z_o_sum += eff_area*z_obs[o];
      }
      let mean_z_obs = (tot_r_area > 0) ? (z_o_sum/tot_r_area) : 0.05;
      let scale_p2z = (p_z_sum > 1e-8) ? (z_o_sum/p_z_sum) : 1.0;

      for (let o = 0; o < n_obs; o++) {
        if (r_hab_area[o] > 0 && r_prior_sum[o] > 0) {
          let eff_area = Math.min(r_area[o], 10.0*r_hab_area[o]);

          obs_prior_z[o] = Math.sqrt(Math.max(1e-7, r_prior_sum[o]/eff_area))*scale_p2z;
        }
      }

      let hu_ctx = bundle._hu_ctx || {};
      let r_lo = Number.isFinite(hu_ctx.residual_clamp_min) ? Number(hu_ctx.residual_clamp_min) : -2.10;
      let r_hi = Number.isFinite(hu_ctx.residual_clamp_max) ? Number(hu_ctx.residual_clamp_max) : 2.10;
      let delta_z = Math.max(1e-4, 0.12*mean_z_obs);
      let r_vec = new Float64Array(n_obs);

      for (let o = 0; o < n_obs; o++) {
        if (r_hab_area[o] <= 0 || r_prior_sum[o] <= 0) continue;
        let raw_s = Math.max(0, (s_obs && Number.isFinite(s_obs[o])) ? s_obs[o] : 0);
        let tot_s = Math.max(0, Number(obs_list[o].total_sites_all_periods) || 0);
        let eff_s = raw_s;

        if (raw_s > 0 && obs_list[o].has_documented_settlement) eff_s = Math.max(eff_s, 6.0);
        //Surveyed catchment with zero sites in this specific epoch carries genuine negative residual evidence
        if (eff_s <= 0 && tot_s > 0 && !obs_list[o].is_frontier_buffer)
          eff_s = Math.min(8.0, 0.35*tot_s);
        if (eff_s <= 0) continue;
        let shrink = eff_s/(eff_s + 2.5);
        //Exact density-space log-residual: log(D_arch / P_prior) = 2 * log(sqrt(D_arch) / sqrt(P_prior))
        let lr = 2.0*Math.log((z_obs[o] + delta_z)/(obs_prior_z[o] + delta_z));

        //Guard against sparse cross-border survey bias falsely erasing active contemporary Stadestér towns (e.g. Tiwanaku/Cusco/Lhasa)
        if (lr < 0 && u_set && (r_set_sum[o]/Math.max(1.0, r_hab_area[o])) > 0.10)
          lr *= 0.25;
        r_vec[o] = shrink*Math.max(r_lo, Math.min(r_hi, lr));
      }

      let diag = sp_ctx.diag;
      let n_nbr = sp_ctx.nbr_idx;
      let n_val = sp_ctx.nbr_val;
      let v_vec = new Float64Array(n_obs);

      for (let o = 0; o < n_obs; o++) v_vec[o] = r_vec[o]/diag[o];
      for (let iter = 0; iter < 80; iter++) {
        for (let o = 0; o < n_obs; o++) {
          let idxs = n_nbr[o];
          let rhs = r_vec[o];
          let vals = n_val[o];

          for (let k = 0; k < idxs.length; k++)
            rhs -= vals[k]*v_vec[idxs[k]];
          v_vec[o] = rhs/diag[o];
        }
      }

      //Return statement
      return v_vec;
    }


    /**
     * Step C: Evaluates terrain-barrier-aware signed residual Matérn (`nu = 3/2`) fields across 1 or more
     * dual-weight vectors in a single shared pass, applying contour elevation breaks and catchment-step
     * tightening before multiplying into `prior_dens`.
     * @alias ViscountDasymetricResidualSolver.C_evaluateMultiDualMaternFields
     *
     * @param {Object} arg0_kriging_bundle
     * @param {Array<Object>} arg1_prior_bundles
     * @param {Array<Float64Array>} arg2_v_vecs
     * @param {Array<number>} arg3_years
     * @param {Function} [arg4_cap_urban_fn]
     *
     * @returns {Object}
     */
    static C_evaluateMultiDualMaternFields (arg0_kriging_bundle, arg1_prior_bundles, arg2_v_vecs, arg3_years, arg4_cap_urban_fn) {
      //Convert from parameters
      let bundle = arg0_kriging_bundle;
      let prior_bundles = arg1_prior_bundles;
      let v_vecs = arg2_v_vecs;
      let years = arg3_years;
      let cap_urban_fn = arg4_cap_urban_fn || null;

      //Declare local instance variables
      let bio_covs = bundle._bio_covs || null;
      let cell_area = bundle.mask_data.cell_land_area;
      let cell_obs = bundle.obs_bundle.cell_nearest_obs;
      let cell_r = bundle.obs_bundle.cell_radius_km;
      let cell_ux = bundle.mask_data.cell_ux;
      let cell_uy = bundle.mask_data.cell_uy;
      let cell_uz = bundle.mask_data.cell_uz;
      let earth_r = bundle.mask_data.earth_radius_km || 6371;
      let elev_valid = (bio_covs && bio_covs.elev_valid) ? bio_covs.elev_valid : null;
      let hu_ctx = bundle._hu_ctx || {};
      let lut = bundle.matern_lut;
      let lut_scale = 8191/8;
      let mask_data = bundle.mask_data;
      let n_obs = bundle.obs_bundle.obs_count;
      let n_p = v_vecs.length;
      let n_valid = mask_data.valid_cell_count;
      let obs_r = bundle.obs_bundle.obs_radius_km;
      let obs_ux = bundle.obs_bundle.obs_ux;
      let obs_uy = bundle.obs_bundle.obs_uy;
      let obs_uz = bundle.obs_bundle.obs_uz;
      let pop_fields = new Array(n_p);
      let r_acc = new Float64Array(n_p);
      let r_clamp_max = Number.isFinite(hu_ctx.residual_clamp_max) ? Number(hu_ctx.residual_clamp_max) : 1.30;
      let r_clamp_min = Number.isFinite(hu_ctx.residual_clamp_min) ? Number(hu_ctx.residual_clamp_min) : -1.20;
      let r_fields = new Array(n_p);
      let r_gain = Number.isFinite(hu_ctx.residual_gain) ? Number(hu_ctx.residual_gain) : 0.88;
      let sp_ctx = this.A_getOrBuildSparseMaternMatrix(bundle);
      let strict_cut = Number.isFinite(hu_ctx.strict_hab_cutoff_year) ? Number(hu_ctx.strict_hab_cutoff_year) : 1650;

      //Function body
      let c1 = sp_ctx.c1;
      let c2 = sp_ctx.c2;
      let cross_catch_mult = Number.isFinite(hu_ctx.cross_catchment_attenuation) ?
        Number(hu_ctx.cross_catchment_attenuation) : 0.82;
      let inv_eb = 1.0/Math.max(150.0, sp_ctx.elev_barrier_m || 650.0);
      let inv_tau1 = sp_ctx.inv_tau1;
      let inv_tau2 = sp_ctx.inv_tau2;
      let min_dot = sp_ctx.min_dot;
      let obs_elev_m = sp_ctx.obs_elev_m;

      for (let p = 0; p < n_p; p++) {
        pop_fields[p] = new Float32Array(n_valid);
        r_fields[p] = new Float32Array(n_valid);
      }

      let used_gpu_res = (hu_ctx.use_gpu !== false && global.ViscountKrigingGPU) ? ViscountKrigingGPU.evaluateResidualMaternMulti({
        c1: c1, c2: c2, cell_area: cell_area, cell_obs: cell_obs, cell_r: cell_r,
        cell_ux: cell_ux, cell_uy: cell_uy, cell_uz: cell_uz, cross_catch_mult: cross_catch_mult,
        earth_r: earth_r, elev_valid: elev_valid, inv_eb: inv_eb, inv_tau1: inv_tau1, inv_tau2: inv_tau2,
        lut: lut, min_dot: min_dot, n_obs: n_obs, n_p: n_p, n_valid: n_valid,
        obs_elev_m: obs_elev_m, obs_r: obs_r, obs_ux: obs_ux, obs_uy: obs_uy, obs_uz: obs_uz,
        pop_fields: pop_fields, prior_bundles: prior_bundles, r_clamp_max: r_clamp_max,
        r_clamp_min: r_clamp_min, r_fields: r_fields, r_gain: r_gain, v_vecs: v_vecs
      }) : false;

      if (!used_gpu_res) for (let i = 0; i < n_valid; i++) {
        let a_i = cell_area[i];
        let cx = cell_ux[i];
        let cy = cell_uy[i];
        let cz = cell_uz[i];
        let ei = elev_valid ? elev_valid[i] : 150.0;
        let own_obs = cell_obs ? cell_obs[i] : -1;
        let ri = cell_r[i];
        let ri2 = ri*ri;

        for (let p = 0; p < n_p; p++) r_acc[p] = 0;

        for (let x = 0; x < n_obs; x++) {
          let dot = cx*obs_ux[x] + cy*obs_uy[x] + cz*obs_uz[x];

          if (dot <= min_dot[x]) continue;
          if (dot > 1) dot = 1;
          else if (dot < -1) dot = -1;
          let c2_c = Math.max(0, 2 - 2*dot);
          let h = earth_r*Math.sqrt(c2_c)*(1 + c2_c/24);
          let rx = obs_r[x];
          let r2_sum = ri2 + rx*rx;
          let u = h/Math.sqrt(0.5*r2_sum);
          let v2 = u*inv_tau2;

          if (v2 >= 7.99) continue;
          let pref = (2*ri*rx)/Math.max(1e-8, r2_sum);
          let m1 = 0;
          let v1 = u*inv_tau1;

          if (v1 < 7.99) {
            let i1 = (v1*lut_scale) | 0;
            let f1 = v1*lut_scale - i1;

            m1 = pref*(lut[i1]*(1 - f1) + lut[i1 + 1]*f1);
          }
          let i2 = (v2*lut_scale) | 0;
          let f2 = v2*lut_scale - i2;
          let m2 = pref*(lut[i2]*(1 - f2) + lut[i2 + 1]*f2);
          let de_norm = Math.abs(ei - obs_elev_m[x])*inv_eb;
          let elev_att = (de_norm > 0.05) ? Math.exp(-Math.pow(de_norm, 1.6)) : 1.0;
          let catch_att = (own_obs === x) ? 1.0 : cross_catch_mult;
          let kern = catch_att*elev_att*(c1*m1 + c2*m2);

          for (let p = 0; p < n_p; p++) {
            let vx = v_vecs[p][x];

            if (vx !== 0) r_acc[p] += vx*kern;
          }
        }

        for (let p = 0; p < n_p; p++) {
          let r_val = r_acc[p];

          r_fields[p][i] = r_val;
          if (prior_bundles[p].prior_dens[i] > 0)
            pop_fields[p][i] = a_i*prior_bundles[p].prior_dens[i]*Math.exp(Math.max(r_clamp_min, Math.min(r_clamp_max, r_gain*r_val)));
        }
      }

      if (cap_urban_fn && bio_covs && bio_covs.uopp_valid) {
        for (let p = 0; p < n_p; p++) {
          if (years[p] <= strict_cut)
            cap_urban_fn(mask_data, pop_fields[p], bio_covs.uopp_valid, 1.02);
        }
      }

      //Return statement
      return { pop_fields: pop_fields, r_fields: r_fields };
    }


    /**
     * Step D: Adapter bridging POLARIS (`sites_IA_RAS` & `sites_belarus_ukraine`) raion bundles directly
     * onto the unified Operation Viscount dasymetric residual kriging engine (`ViscountBiophysicalCovariates`
     * + `ViscountHUResidualKriging`), enforcing elevation/slope step bands, tightened terrain-gated rivers,
     * Wild Fields steppe suppression, and the strict Stadestér + HYDE 3.5 union habitability mask.
     * @alias ViscountDasymetricResidualSolver.D_evaluatePolarisDasymetricDomain
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_raion_data
     * @param {Object} arg2_kriging_bundle
     * @param {Object} arg3_config
     * @param {string} arg4_domain_dir
     *
     * @returns {Object}
     */
    static D_evaluatePolarisDasymetricDomain (arg0_mask_data, arg1_raion_data, arg2_kriging_bundle, arg3_config, arg4_domain_dir) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let raion_data = arg1_raion_data;
      let kriging_bundle = arg2_kriging_bundle;
      let config = arg3_config;
      let domain_dir = arg4_domain_dir;

      //Declare local instance variables
      let { ViscountBiophysicalCovariates } = global.ViscountBiophysicalCovariates ?
        global : require(path.join(__dirname, "ViscountBiophysicalCovariates.js"));
      let { ViscountHUResidualKriging } = global.ViscountHUResidualKriging ?
        global : require(path.join(__dirname, "centaur/ViscountHUResidualKriging.js"));
      let hab_cache = new Map();
      let n_periods = config.periods.length;
      let obs_bundle = {
        cell_nearest_obs: raion_data.cell_nearest_raion,
        cell_radius_km: raion_data.cell_radius_km,
        obs_count: raion_data.raion_count,
        obs_list: raion_data.raion_list,
        obs_radius_km: raion_data.raion_radius_km,
        obs_ux: raion_data.raion_ux,
        obs_uy: raion_data.raion_uy,
        obs_uz: raion_data.raion_uz,
        period_totals: raion_data.period_totals
      };

      //Function body
      mask_data.domain_dir = domain_dir;
      let bio_covs = ViscountBiophysicalCovariates.buildStaticCovariates(mask_data, config, obs_bundle);
      let active_periods = [];

      for (let i = 0; i < n_periods; i++) {
        let p_cfg = config.periods[i];
        let pkey = p_cfg.key;
        let model = kriging_bundle.kriging_models[pkey];

        if (!model) continue;
        active_periods.push({
          c1: model.c1_weight,
          c2: model.c2_weight,
          cfg: p_cfg,
          inv_tau1: 1/Math.max(0.4, model.tau1_dimensionless || kriging_bundle.tau1_dimensionless),
          inv_tau2: 1/Math.max(0.8, model.tau2_dimensionless || kriging_bundle.tau2_dimensionless),
          model: model,
          pkey: pkey
        });
      }

      let unified_bundle = {
        config: config,
        kriging_models: kriging_bundle.kriging_models,
        mask_data: mask_data,
        matern_lut: kriging_bundle.matern_lut,
        obs_bundle: obs_bundle,
        tau1_dimensionless: kriging_bundle.tau1_dimensionless,
        tau2_dimensionless: kriging_bundle.tau2_dimensionless
      };
      let hu_out = ViscountHUResidualKriging.evaluateAllPeriodResidualSurfaces(
        unified_bundle,
        bio_covs,
        active_periods,
        hab_cache
      );

      //Return statement
      return {
        bio_covs: bio_covs,
        fields: hu_out.fields,
        hab_cache: hab_cache,
        hu_ctx: unified_bundle._hu_ctx,
        kriging_bundle: unified_bundle,
        residual_fields: hu_out.residual_fields,
        wls_betas_by_period: hu_out.wls_betas_by_period
      };
    }


    /**
     * Step E: Evaluates a single historical benchmark year (`yr`) on a POLARIS dasymetric surface bundle
     * using interpolated signed residual fields, elevation/slope step-bands, Wild Fields suppression, and
     * strict union habitability masking (`hab_mask`).
     * @alias ViscountDasymetricResidualSolver.E_evaluatePolarisYearField
     *
     * @param {Object} arg0_surface
     * @param {Array<Object>} arg1_horizon_residuals
     * @param {number} arg2_year
     * @param {number} arg3_target_mass
     *
     * @returns {Float32Array}
     */
    static E_evaluatePolarisYearField (arg0_surface, arg1_horizon_residuals, arg2_year, arg3_target_mass) {
      //Convert from parameters
      let surface = arg0_surface;
      let h_r_list = arg1_horizon_residuals;
      let yr = Number(arg2_year) || 0;
      let target_mass = Number(arg3_target_mass) || 0;

      //Declare local instance variables
      let { ViscountCentaurDasymetricDetail } = global.ViscountCentaurDasymetricDetail ?
        global : require(path.join(__dirname, "centaur/ViscountCentaurDasymetricDetail.js"));
      let { ViscountHUResidualHelpers } = global.ViscountHUResidualHelpers ?
        global : require(path.join(__dirname, "centaur/ViscountHUResidualHelpers.js"));
      let { ViscountHUResidualKriging } = global.ViscountHUResidualKriging ?
        global : require(path.join(__dirname, "centaur/ViscountHUResidualKriging.js"));
      let bio_covs = surface.bio_covs;
      let bundle = surface.kriging_bundle;
      let cdd_cfg = (surface.hu_ctx && surface.hu_ctx.centaur_dasymetric_detail && surface.hu_ctx.centaur_dasymetric_detail.enabled) ?
        surface.hu_ctx.centaur_dasymetric_detail : null;
      let cell_area = bundle.mask_data.cell_land_area;
      let hab_mask = bio_covs.hab_mask;
      let hu_ctx = surface.hu_ctx;
      let n_valid = bundle.mask_data.valid_cell_count;
      let out_field = new Float32Array(n_valid);
      let r_clamp_max = Number.isFinite(hu_ctx.residual_clamp_max) ? Number(hu_ctx.residual_clamp_max) : 1.30;
      let r_clamp_min = Number.isFinite(hu_ctx.residual_clamp_min) ? Number(hu_ctx.residual_clamp_min) : -1.20;
      let r_gain = Number.isFinite(hu_ctx.residual_gain) ? Number(hu_ctx.residual_gain) : 0.88;

      //Function body
      ViscountHUResidualHelpers.trimRasterCache(surface.hab_cache, 20, 14);
      let prior_b = ViscountHUResidualKriging.C_evaluatePriorTrendField(
        bundle.mask_data,
        bio_covs,
        hu_ctx,
        yr,
        bundle.config,
        surface.hab_cache
      );
      let alpha = 0;
      let r_a = h_r_list[0].r;
      let r_b = h_r_list[0].r;

      if (yr >= h_r_list[h_r_list.length - 1].year) {
        r_a = h_r_list[h_r_list.length - 1].r;
        r_b = r_a;
      } else if (yr > h_r_list[0].year) {
        for (let k = 0; k < h_r_list.length - 1; k++) {
          if (yr >= h_r_list[k].year && yr <= h_r_list[k + 1].year) {
            r_a = h_r_list[k].r;
            r_b = h_r_list[k + 1].r;
            alpha = (yr - h_r_list[k].year)/Math.max(1, h_r_list[k + 1].year - h_r_list[k].year);
            break;
          }
        }
      }

      let raw_sum = 0;

      for (let i = 0; i < n_valid; i++) {
        if (hab_mask && hab_mask[i] === 0) continue;
        if (prior_b.prior_dens[i] <= 0) continue;
        let r_val = (1 - alpha)*r_a[i] + alpha*r_b[i];
        let v = cell_area[i]*prior_b.prior_dens[i]*Math.exp(Math.max(r_clamp_min, Math.min(r_clamp_max, r_gain*r_val)));

        out_field[i] = v;
        raw_sum += v;
      }
      if (cdd_cfg)
        ViscountCentaurDasymetricDetail.D_applyPycnophylacticDasymetricSharpening(bundle.mask_data, bio_covs, hu_ctx, out_field, prior_b.d_decliff, cdd_cfg);
      if (yr <= 1850 && bio_covs.uopp_valid)
        ViscountHUResidualHelpers.capUrbanCoreSmooth(bundle.mask_data, out_field, bio_covs.uopp_valid, 0.94);
      if (hab_mask)
        ViscountHUResidualHelpers.closeZeroPinholes(bundle.mask_data, out_field, hab_mask, 5, 0.45, 2, 1e-4);

      raw_sum = 0;
      for (let i = 0; i < n_valid; i++) {
        if (hab_mask && hab_mask[i] === 0) out_field[i] = 0;
        raw_sum += out_field[i];
      }
      if (raw_sum > 0 && target_mass > 0) {
        let sc = target_mass/raw_sum;

        for (let i = 0; i < n_valid; i++) out_field[i] *= sc;
      }

      //Return statement
      return out_field;
    }


    /**
     * Step F: Builds elevation- and latitude-gated lowland Terra Preta (ADE) weights and normalised spatial
     * mass density (`tp_lat_w`, `tp_norm`) restricted strictly below the Andean cordillera (`<= 650..1150 m`).
     * @alias ViscountDasymetricResidualSolver.F_prepareTerraPretaWeights
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_bio_covs
     * @param {Float32Array} arg2_tp_src
     *
     * @returns {Object}
     */
    static F_prepareTerraPretaWeights (arg0_mask_data, arg1_bio_covs, arg2_tp_src) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let bio_covs = arg1_bio_covs || {};
      let tp_src = arg2_tp_src;

      //Guard clauses
      if (!mask_data || !tp_src) return { tp_lat_w: null, tp_norm: null };

      //Declare local instance variables
      let elev_valid = bio_covs.elev_valid || null;
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let hab_mask = bio_covs.hab_mask || null;
      let n_valid = mask_data.valid_cell_count;
      let tp_lat_w = new Float32Array(n_valid);
      let tp_norm = new Float32Array(n_valid);
      let tp_sum = 0;
      let valid_indices = mask_data.valid_indices;

      //Function body
      for (let i = 0; i < n_valid; i++) {
        let e_i = elev_valid ? elev_valid[i] : 150.0;
        let lat = 90 - (Math.floor(valid_indices[i]/grid_w) + 0.5)*180/grid_h;
        let we = (e_i <= 650.0) ? 1.0 : ((e_i >= 1150.0) ? 0.0 : (1150.0 - e_i)/500.0);
        let wl = we*((lat >= -14.0) ? 1.0 : ((lat <= -19.0) ? 0.0 : (lat + 19.0)/5.0));

        tp_lat_w[i] = wl;
        if (wl > 0 && (!hab_mask || hab_mask[i] === 1)) {
          let v = Math.max(0, tp_src[i])*wl;

          tp_norm[i] = v;
          tp_sum += v;
        }
      }
      if (tp_sum > 0)
        for (let i = 0; i < n_valid; i++) tp_norm[i] /= tp_sum;

      //Return statement
      return { tp_lat_w: tp_lat_w, tp_norm: tp_norm };
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountDasymetricResidualSolver: global.ViscountDasymetricResidualSolver };
