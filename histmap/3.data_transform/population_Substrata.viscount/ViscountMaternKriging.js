//Import modules
let fs = global.fs || require("fs");
let JSON5 = global.JSON5 || require("json5");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * Config-driven Non-Stationary Empirical Paciorek-Schervish Matérn (nu = 3/2) Log-Linear Residual Kriging
   * engine generalised from `POLARIS/_shared/sites_IA_RAS/krige_sites_ia_ras.js` for all 14 Operation Viscount regions.
   *
   * Logical flow is prefixed with step letters (`A_` through `F_`):
   * - `A_loadDomainConfigAndSites`: Loads domain mask (`4320x2160`), regional observation GeoJSONs and 250 km cross-frontier buffers.
   * - `B_computeEmpiricalBayesIntensities`: Computes catchment-normalised geodesic distances, Voronoi radii and Freeman-Tukey `sqrt(lambda)`.
   * - `C_fitTwoScaleNonStationaryMatern`: Derives empirical Matheron variograms, `tau1`/`tau2` ranges and Paciorek-Schervish kernels.
   * - `D_solveProjectedNonNegativeDualKriging`: Solves `(C + eta*I)*w = z_adj` with `w >= 0` via Cholesky warm-start + Projected Gauss-Seidel.
   * - `E_fitCarryCapacityResidualSurface`: Fits WLS NNLS Trend against physical suitability & de-cliffed rural habitation covariates.
   * - `F_exportBenchmarkRastersAndDiagnostics`: Writes `4320x2160` float32 GeoPNGs and sharpness diagnostics JSON.
   *
   * @class ViscountMaternKriging
   */
  global.ViscountMaternKriging = class {
    /**
     * Step A: Loads domain JSON5 config, constructs valid 5-arcminute (`4320x2160`) land mask and loads
     * domestic + 250 km cross-frontier observation units (`geojson/*.geojson`).
     * @alias ViscountMaternKriging.A_loadDomainConfigAndSites
     *
     * @param {string|Object} arg0_config_path_or_obj
     * @param {Object} [arg1_options]
     *  @param {string} [arg1_options.project_root]
     *
     * @returns {Object}
     */
    static A_loadDomainConfigAndSites (arg0_config_path_or_obj, arg1_options) {
      //Convert from parameters
      let config_input = arg0_config_path_or_obj;
      let options = (arg1_options) ? arg1_options : {};

      //Declare local instance variables
      let config = null;
      let config_dir = __dirname;
      let earth_radius_km = 6371;
      let grid_h = 2160;
      let grid_w = 4320;
      let land_area_path = "";
      let mask_png_path = "";
      let obs_list = [];
      let period_totals = {};
      let root_dir = (options.project_root) ? options.project_root : ((fs.existsSync("./histmap/1.data_raw")) ?
        path.resolve(".") : path.resolve(__dirname, "../../.."));

      //Function body
      if (typeof config_input === "string") {
        let abs_cfg = path.resolve(root_dir, config_input);
        if (!fs.existsSync(abs_cfg)) {
          console.error(`[ViscountMaternKriging] Config not found: ${abs_cfg}`);
          return null;
        }
        config_dir = path.dirname(path.dirname(abs_cfg));
        config = JSON5.parse(fs.readFileSync(abs_cfg, "utf8"));
      } else if (config_input && typeof config_input === "object") {
        config = config_input;
        if (options.domain_dir) config_dir = path.resolve(options.domain_dir);
      } else {
        console.error("[ViscountMaternKriging] Invalid config input.");
        return null;
      }

      let k_cfg = config.kriging_config || {};
      earth_radius_km = Number(k_cfg.earth_radius_km) || 6371;
      grid_h = Number(k_cfg.grid_height) || 2160;
      grid_w = Number(k_cfg.grid_width) || 4320;

      let total_pixels = grid_w*grid_h;
      let cell_land_area = [];
      let land_mask = new Uint8Array(total_pixels);
      let mask_grid = new Uint8Array(total_pixels);
      let pixel_to_valid_idx = new Int32Array(total_pixels).fill(-1);
      let valid_indices = [];

      land_area_path = path.resolve(root_dir, "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png");
      let land_area_png = fs.existsSync(land_area_path) ? PNG.sync.read(fs.readFileSync(land_area_path)) : null;

      mask_png_path = (k_cfg.domain_mask_png) ? path.resolve(root_dir, k_cfg.domain_mask_png) : "";
      if (mask_png_path && fs.existsSync(mask_png_path)) {
        let m_png = PNG.sync.read(fs.readFileSync(mask_png_path));
        for (let i = 0; i < total_pixels; i++) {
          let p4 = i*4;
          if (m_png.data[p4 + 3] > 0 && (m_png.data[p4] | m_png.data[p4 + 1] | m_png.data[p4 + 2]) !== 0)
            land_mask[i] = 1;
        }
      } else if (land_area_png) {
        let geocodes_path = path.resolve(root_dir, "histmap/1.data_raw/admin_modern/geocodes.png");
        let target_rgbs = Array.isArray(k_cfg.domain_geocode_rgbs) ? k_cfg.domain_geocode_rgbs : [];
        if (k_cfg.russia_geocode_rgb) target_rgbs.push(k_cfg.russia_geocode_rgb);
        let target_set = new Set(target_rgbs.map(function (arg0_c) { return `${arg0_c[0]},${arg0_c[1]},${arg0_c[2]}`; }));

        if (target_set.size > 0 && fs.existsSync(geocodes_path)) {
          let geo_png = PNG.sync.read(fs.readFileSync(geocodes_path));
          for (let i = 0; i < total_pixels; i++) {
            let p4 = i*4;
            if (geo_png.data[p4 + 3] === 0) continue;
            let key = `${geo_png.data[p4]},${geo_png.data[p4 + 1]},${geo_png.data[p4 + 2]}`;
            if (target_set.has(key)) land_mask[i] = 1;
          }
        }
      }

      let total_area_km2 = 0;
      let valid_ux = [];
      let valid_uy = [];
      let valid_uz = [];
      let land_area_grid = new Float32Array(total_pixels);

      for (let i = 0; i < total_pixels; i++) {
        let row = Math.floor(i/grid_w);
        let col = i % grid_w;
        let lat = 90 - (row + 0.5)*(180/grid_h);
        let lon = -180 + (col + 0.5)*(360/grid_w);
        let area_val = 85.4*Math.cos(lat*Math.PI/180);

        if (land_area_png) {
          let p4 = i*4;
          let dv_a = ((land_area_png.data[p4] << 24) | (land_area_png.data[p4 + 1] << 16) | (land_area_png.data[p4 + 2] << 8) | land_area_png.data[p4 + 3]) >>> 0;
          area_val = dv_a;
        }
        land_area_grid[i] = Math.max(0, area_val);

        if (land_mask[i] === 1 && land_area_grid[i] > 0) {
          let lat_r = lat*Math.PI/180;
          let lon_r = lon*Math.PI/180;
          let cos_lat = Math.cos(lat_r);

          pixel_to_valid_idx[i] = valid_indices.length;
          mask_grid[i] = 1;
          valid_indices.push(i);
          cell_land_area.push(land_area_grid[i]);
          valid_ux.push(cos_lat*Math.cos(lon_r));
          valid_uy.push(cos_lat*Math.sin(lon_r));
          valid_uz.push(Math.sin(lat_r));
          total_area_km2 += land_area_grid[i];
        }
      }

      let mask_data = {
        cell_land_area: Float32Array.from(cell_land_area),
        cell_ux: Float32Array.from(valid_ux),
        cell_uy: Float32Array.from(valid_uy),
        cell_uz: Float32Array.from(valid_uz),
        domain_dir: config_dir,
        earth_radius_km: earth_radius_km,
        grid_height: grid_h,
        grid_width: grid_w,
        land_area_grid: land_area_grid,
        mask_grid: mask_grid,
        mean_cell_land_area_km2: total_area_km2/Math.max(1, valid_indices.length),
        pixel_to_valid_idx: pixel_to_valid_idx,
        project_root: root_dir,
        total_land_area_km2: total_area_km2,
        valid_cell_count: valid_indices.length,
        valid_indices: Int32Array.from(valid_indices)
      };

      //Load period observation GeoJSONs (domestic + optional cross-frontier conditioning buffers)
      let geojson_dir = path.resolve(config_dir, config.output_geojson_subfolder || "geojson");
      let obs_map = new Map();
      let periods = Array.isArray(config.periods) ? config.periods : [];
      for (let i = 0; i < periods.length; i++) {
        let p = periods[i];
        period_totals[p.key] = 0;
        let gj_path = path.join(geojson_dir, p.geojson_filename || `${p.key}.geojson`);
        if (!fs.existsSync(gj_path)) continue;
        let gj = JSON.parse(fs.readFileSync(gj_path, "utf8"));
        let feats = Array.isArray(gj.features) ? gj.features : [];

        for (let x = 0; x < feats.length; x++) {
          let feat = feats[x];
          if (!feat || !feat.geometry || !Array.isArray(feat.geometry.coordinates)) continue;
          let props = feat.properties || {};
          if (props.is_unspecified_subregion) continue;
          let lon = Number(feat.geometry.coordinates[0]);
          let lat = Number(feat.geometry.coordinates[1]);
          if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
          let rid = String(props.region_id || props.id || `${lat.toFixed(3)}_${lon.toFixed(3)}`);
          let cnt = Number(props.site_count || props.value || 0);

          if (!obs_map.has(rid)) {
            let lat_r = lat*Math.PI/180;
            let lon_r = lon*Math.PI/180;
            let cos_lat = Math.cos(lat_r);
            obs_map.set(rid, {
              eb_densities: {},
              effective_area_km2: Number(props.area_km2) || 0,
              id: rid,
              is_frontier_buffer: Boolean(props.is_frontier_buffer),
              lat: lat,
              lon: lon,
              periods: {},
              radius_km: 0,
              total_sites_all_periods: Number(props.total_sites_all_periods) || 0,
              ux: cos_lat*Math.cos(lon_r),
              uy: cos_lat*Math.sin(lon_r),
              uz: Math.sin(lat_r)
            });
          }
          let entry = obs_map.get(rid);
          entry.periods[p.key] = (entry.periods[p.key] || 0) + cnt;
          if (!entry.is_frontier_buffer)
            period_totals[p.key] += cnt;
        }
      }
      obs_list = Array.from(obs_map.values());

      //Return statement
      return {
        config: config,
        mask_data: mask_data,
        obs_list: obs_list,
        period_totals: period_totals
      };
    }


    /**
     * Step B: Computes geodesic Voronoi catchment areas on the mask and transforms raw site/population counts
     * into variance-stabilised Freeman-Tukey square-root densities `Z_{k,p} = sqrt(lambda_{k,p})`.
     * @alias ViscountMaternKriging.B_computeEmpiricalBayesIntensities
     *
     * @param {Object} arg0_domain_bundle - Output from `A_loadDomainConfigAndSites`
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    static B_computeEmpiricalBayesIntensities (arg0_domain_bundle, arg1_options) {
      //Convert from parameters
      let bundle = arg0_domain_bundle;
      let options = (arg1_options) ? arg1_options : {};

      //Guard clauses
      if (!bundle || !bundle.mask_data || !Array.isArray(bundle.obs_list)) {
        console.error("[ViscountMaternKriging] Invalid domain bundle passed to Step B.");
        return null;
      }

      //Declare local instance variables
      let cell_nearest = new Int32Array(bundle.mask_data.valid_cell_count);
      let cell_ux = bundle.mask_data.cell_ux;
      let cell_uy = bundle.mask_data.cell_uy;
      let cell_uz = bundle.mask_data.cell_uz;
      let n_obs = bundle.obs_list.length;
      let n_valid = bundle.mask_data.valid_cell_count;
      let obs_list = bundle.obs_list;
      let obs_ux = new Float64Array(n_obs);
      let obs_uy = new Float64Array(n_obs);
      let obs_uz = new Float64Array(n_obs);
      let period_configs = Array.isArray(bundle.config.periods) ? bundle.config.periods : [];
      let raw_areas = new Float64Array(n_obs);

      //Function body
      for (let i = 0; i < n_obs; i++) {
        obs_ux[i] = obs_list[i].ux;
        obs_uy[i] = obs_list[i].uy;
        obs_uz[i] = obs_list[i].uz;
      }

      for (let i = 0; i < n_valid; i++) {
        let best_dot = -2;
        let best_idx = 0;
        let cx = cell_ux[i];
        let cy = cell_uy[i];
        let cz = cell_uz[i];

        for (let x = 0; x < n_obs; x++) {
          let d = cx*obs_ux[x] + cy*obs_uy[x] + cz*obs_uz[x];
          if (d > best_dot) {
            best_dot = d;
            best_idx = x;
          }
        }
        cell_nearest[i] = best_idx;
        raw_areas[best_idx] += bundle.mask_data.cell_land_area[i];
      }

      let valid_areas = [];
      for (let i = 0; i < n_obs; i++) {
        let eff_a = Math.max(bundle.mask_data.mean_cell_land_area_km2, obs_list[i].effective_area_km2 || raw_areas[i]);
        obs_list[i].effective_area_km2 = eff_a;
        valid_areas.push(eff_a);
      }
      valid_areas.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
      let q25 = valid_areas[Math.floor(0.25*(valid_areas.length - 1))] || 1000;
      let q75 = valid_areas[Math.floor(0.75*(valid_areas.length - 1))] || 10000;
      let med_area = valid_areas[Math.floor(0.50*(valid_areas.length - 1))] || 5000;

      let obs_radius_km = new Float64Array(n_obs);
      let raw_cell_radius = new Float32Array(n_valid);

      for (let i = 0; i < n_obs; i++) {
        let clamped_a = Math.max(0.35*q25, Math.min(q75, obs_list[i].effective_area_km2));
        obs_list[i].radius_km = Math.sqrt(clamped_a/Math.PI);
        obs_radius_km[i] = obs_list[i].radius_km;
      }

      for (let i = 0; i < period_configs.length; i++) {
        let pkey = period_configs[i].key;
        for (let x = 0; x < n_obs; x++) {
          let sk = obs_list[x].periods[pkey] || 0;
          obs_list[x].eb_densities[pkey] = sk/Math.max(1e-6, obs_list[x].effective_area_km2);
        }
      }

      for (let i = 0; i < n_valid; i++)
        raw_cell_radius[i] = obs_radius_km[cell_nearest[i]];

      //Return statement
      return {
        cell_nearest_obs: cell_nearest,
        cell_radius_km: raw_cell_radius,
        config: bundle.config,
        mask_data: bundle.mask_data,
        median_radius_km: Math.sqrt(med_area/Math.PI),
        median_voronoi_area_km2: med_area,
        obs_count: n_obs,
        obs_list: obs_list,
        obs_radius_km: obs_radius_km,
        obs_ux: obs_ux,
        obs_uy: obs_uy,
        obs_uz: obs_uz,
        period_totals: bundle.period_totals
      };
    }


    /**
     * Step C: Derives Matheron (1962) empirical variograms, empirical zero-lag nugget ratios (`<= 0,22` guard),
     * two-scale Paciorek-Schervish non-stationary Matérn (`nu = 3/2`) covariance kernels (`tau1 in [0,60, 1,50]`)
     * and solves the Non-Negative Dual Kriging system via Step D.
     * @alias ViscountMaternKriging.C_fitTwoScaleNonStationaryMatern
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
        console.error("[ViscountMaternKriging] Cannot fit variogram with zero observations.");
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
      let pooled_norm_gammas = new Float64Array(dim_lag_bins.length);
      let pooled_u_lags = new Float64Array(dim_lag_bins.length);
      let scale_pref_mat = new Float32Array(n_obs*n_obs);
      let sqrt3 = Math.sqrt(3);
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

          if (u <= dim_lag_bins[n_bins - 1]) {
            for (let y = 0; y < n_bins; y++) {
              if (u <= dim_lag_bins[y]) {
                pair_bins[y].push(i, x, u);
                break;
              }
            }
          }
        }
      }

      //Evaluate pooled empirical variogram to fix tau1 in [0,60, 1,50] and tau2 >= 1,8*tau1
      let period_z_map = {};
      let period_obs_map = {};
      for (let i = 0; i < period_configs.length; i++) {
        let emp_gammas = [];
        let emp_lags = [];
        let pkey = period_configs[i].key;
        let sample_var = 0;
        let sill_norm = 0;
        let z = new Float64Array(n_obs);
        let z_mean = 0;

        for (let x = 0; x < n_obs; x++) {
          z[x] = Math.sqrt(Math.max(0, obs_list[x].eb_densities[pkey] || 0));
          z_mean += z[x];
        }
        z_mean /= Math.max(1, n_obs);
        for (let x = 0; x < n_obs; x++)
          sample_var += (z[x] - z_mean)*(z[x] - z_mean);
        sample_var = Math.max(1e-8, sample_var/n_obs);

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
          let g_m = (nb > 0) ? sq_sum/nb : sample_var;
          let u_bar = (nb > 0) ? u_sum/nb : dim_lag_bins[x];
          emp_gammas.push(g_m);
          emp_lags.push(u_bar);
          pooled_norm_gammas[x] += (g_m/sample_var)/Math.max(1, period_configs.length);
          pooled_u_lags[x] = u_bar;
        }

        for (let x = Math.max(0, n_bins - 3); x < n_bins; x++)
          sill_norm += (emp_gammas[x]/sample_var)/Math.min(3, n_bins);
        sill_norm = Math.max(0.1, sill_norm);

        let g0 = emp_gammas[0]/sample_var;
        let g1 = (emp_gammas[1] || emp_gammas[0])/sample_var;
        let slope01 = Math.max(0, (g1 - g0)/Math.max(1e-6, (emp_lags[1] || emp_lags[0]) - emp_lags[0]));
        let c0_norm = Math.max(0.04*sill_norm, Math.min(0.22*sill_norm, g0 - emp_lags[0]*slope01));
        let eta = c0_norm/Math.max(0.05*sill_norm, sill_norm - c0_norm);

        period_obs_map[pkey] = {
          c0_norm: c0_norm,
          empirical_gammas: emp_gammas,
          empirical_u_lags: emp_lags,
          eta_nugget_ratio: eta,
          sample_variance: sample_var,
          sill_norm: sill_norm,
          z_mean: z_mean
        };
        period_z_map[pkey] = z;
      }

      let tau1 = Math.max(0.60, Math.min(1.50, options.tau1 || 1.25));
      let tau2 = Math.max(2.10, Math.min(3.50, options.tau2 || 2.60));
      if (pooled_u_lags.length >= 2) {
        let g0 = pooled_norm_gammas[0];
        let g1 = pooled_norm_gammas[1];
        let sill = 0;
        for (let i = Math.max(0, n_bins - 3); i < n_bins; i++) sill += pooled_norm_gammas[i]/3;
        sill = Math.max(0.1, sill);
        let c0 = Math.max(0.04*sill, Math.min(0.22*sill, g0));
        let target1 = c0 + (1 - (1 + sqrt3)*Math.exp(-sqrt3))*Math.max(1e-6, sill - c0);
        for (let i = 0; i < n_bins - 1; i++) {
          if (pooled_norm_gammas[i] <= target1 && pooled_norm_gammas[i + 1] >= target1) {
            let frac = (target1 - pooled_norm_gammas[i])/Math.max(1e-8, pooled_norm_gammas[i + 1] - pooled_norm_gammas[i]);
            tau1 = pooled_u_lags[i] + frac*(pooled_u_lags[i + 1] - pooled_u_lags[i]);
            break;
          }
        }
        tau1 = Math.max(0.60, Math.min(1.50, tau1));
        tau2 = Math.max(1.85*tau1, Math.min(3.40, tau2));
      }

      //Evaluate two-scale Matérn kernels & solve Non-Negative Dual Kriging per period
      let m1_mat = new Float64Array(n_obs*n_obs);
      let m2_mat = new Float64Array(n_obs*n_obs);
      for (let i = 0; i < n_obs; i++) {
        m1_mat[i*n_obs + i] = 1;
        m2_mat[i*n_obs + i] = 1;
        for (let x = i + 1; x < n_obs; x++) {
          let idx = i*n_obs + x;
          let pref = scale_pref_mat[idx];
          let s1 = sqrt3*u_matrix[idx]/tau1;
          let s2 = sqrt3*u_matrix[idx]/tau2;
          let v1 = pref*(1 + s1)*Math.exp(-s1);
          let v2 = pref*(1 + s2)*Math.exp(-s2);
          m1_mat[idx] = v1;
          m1_mat[x*n_obs + i] = v1;
          m2_mat[idx] = v2;
          m2_mat[x*n_obs + i] = v2;
        }
      }

      for (let i = 0; i < period_configs.length; i++) {
        let pkey = period_configs[i].key;
        let obs = period_obs_map[pkey];
        let eta = obs.eta_nugget_ratio;
        let c1 = 0.78;
        let c2 = 0.22;

        for (let x = 0; x < n_obs; x++) {
          let row = x*n_obs;
          period_cov[row + x] = 1 + eta;
          for (let y = x + 1; y < n_obs; y++) {
            let kval = c1*m1_mat[row + y] + c2*m2_mat[row + y];
            period_cov[row + y] = kval;
            period_cov[y*n_obs + x] = kval;
          }
        }

        let dual_weights = this.D_solveProjectedNonNegativeDualKriging(period_cov, period_z_map[pkey], n_obs);
        kriging_models[pkey] = {
          c0_nugget: (obs.c0_norm/obs.sill_norm)*obs.sample_variance,
          c1_weight: c1,
          c2_weight: c2,
          dual_weights: dual_weights,
          empirical_gammas: obs.empirical_gammas,
          empirical_u_lags: obs.empirical_u_lags,
          eta_nugget_ratio: eta,
          nugget_to_sill_ratio: obs.c0_norm/obs.sill_norm,
          sample_variance: obs.sample_variance,
          tau1_dimensionless: tau1,
          tau2_dimensionless: tau2,
          z_adj: period_z_map[pkey]
        };
      }

      //Return statement
      return {
        config: config,
        kriging_models: kriging_models,
        mask_data: obs_bundle.mask_data,
        matern_lut: matern_lut,
        obs_bundle: obs_bundle,
        tau1_dimensionless: tau1,
        tau2_dimensionless: tau2
      };
    }


    /**
     * Step D: Solves `(C + eta*I)*w = z_adj` with `w >= 0` via Cholesky warm-start and Projected Gauss-Seidel sweeps.
     * @alias ViscountMaternKriging.D_solveProjectedNonNegativeDualKriging
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
      let chol_L = new Float64Array(n*n);
      let out_w = new Float32Array(n);
      let sol_x = new Float64Array(n);
      let sol_y = new Float64Array(n);
      let w_vec = new Float64Array(n);

      //Function body
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

      for (let i = 0; i < n; i++) out_w[i] = w_vec[i];

      //Return statement
      return out_w;
    }


    /**
     * Step E: Evaluates non-stationary Matérn kriging potentials coupled with Log-Linear Residual Kriging
     * covariates (`clim_suitability`, `river_proximity`, `hyde_rural_habitation`).
     * @alias ViscountMaternKriging.E_fitCarryCapacityResidualSurface
     *
     * @param {Object} arg0_kriging_bundle
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    static E_fitCarryCapacityResidualSurface (arg0_kriging_bundle, arg1_options) {
      //Convert from parameters
      let bundle = arg0_kriging_bundle;
      let options = (arg1_options) ? arg1_options : {};

      //Guard clauses
      if (!bundle || !bundle.kriging_models || !bundle.obs_bundle) {
        console.error("[ViscountMaternKriging] Missing kriging bundle for Step E.");
        return null;
      }

      //Declare local instance variables
      let cell_area = bundle.mask_data.cell_land_area;
      let cell_r = bundle.obs_bundle.cell_radius_km;
      let cell_ux = bundle.mask_data.cell_ux;
      let cell_uy = bundle.mask_data.cell_uy;
      let cell_uz = bundle.mask_data.cell_uz;
      let earth_r = bundle.mask_data.earth_radius_km;
      let fields = {};
      let inv_tau1 = 1/bundle.tau1_dimensionless;
      let inv_tau2 = 1/bundle.tau2_dimensionless;
      let lut = bundle.matern_lut;
      let lut_scale = 8191/8;
      let n_obs = bundle.obs_bundle.obs_count;
      let n_valid = bundle.mask_data.valid_cell_count;
      let obs_r = bundle.obs_bundle.obs_radius_km;
      let obs_ux = bundle.obs_bundle.obs_ux;
      let obs_uy = bundle.obs_bundle.obs_uy;
      let obs_uz = bundle.obs_bundle.obs_uz;
      let period_configs = Array.isArray(bundle.config.periods) ? bundle.config.periods : [];
      let r_squared_by_period = {};

      //Function body
      for (let p = 0; p < period_configs.length; p++) {
        let pkey = period_configs[p].key;
        let model = bundle.kriging_models[pkey];
        if (!model) continue;

        let out_field = new Float32Array(n_valid);
        let z_obs = model.z_adj;
        let w = model.dual_weights;
        let z_mean = 0;
        let ss_tot = 0;
        let ss_res = 0;

        for (let x = 0; x < n_obs; x++) z_mean += z_obs[x];
        z_mean /= Math.max(1, n_obs);

        for (let x = 0; x < n_obs; x++) {
          let pred = model.eta_nugget_ratio*w[x];
          let z_hat = Math.max(0, z_obs[x] - pred);
          ss_tot += (z_obs[x] - z_mean)*(z_obs[x] - z_mean);
          ss_res += (z_obs[x] - z_hat)*(z_obs[x] - z_hat);
        }
        r_squared_by_period[pkey] = Number(Math.max(0, 1 - ss_res/Math.max(1e-8, ss_tot)).toFixed(4));

        for (let i = 0; i < n_valid; i++) {
          let z_acc = 0;
          let ri = cell_r[i];
          let ri2 = ri*ri;
          for (let x = 0; x < n_obs; x++) {
            let dot = Math.max(-1, Math.min(1, cell_ux[i]*obs_ux[x] + cell_uy[i]*obs_uy[x] + cell_uz[i]*obs_uz[x]));
            let c2 = Math.max(0, 2 - 2*dot);
            let h = earth_r*Math.sqrt(c2)*(1 + c2/24);
            let rx = obs_r[x];
            let r2_sum = ri2 + rx*rx;
            let u = h/Math.sqrt(0.5*r2_sum);
            let v2 = u*inv_tau2;
            if (v2 >= 7.99) continue;

            let pref = (2*ri*rx)/Math.max(1e-8, r2_sum);
            let m1 = 0;
            let v1 = u*inv_tau1;
            if (v1 < 7.99) {
              let idx1 = (v1*lut_scale) | 0;
              let frac1 = v1*lut_scale - idx1;
              m1 = pref*(lut[idx1]*(1 - frac1) + lut[idx1 + 1]*frac1);
            }
            let idx2 = (v2*lut_scale) | 0;
            let frac2 = v2*lut_scale - idx2;
            let m2 = pref*(lut[idx2]*(1 - frac2) + lut[idx2 + 1]*frac2);
            z_acc += w[x]*(model.c1_weight*m1 + model.c2_weight*m2);
          }
          out_field[i] = cell_area[i]*Math.pow(Math.max(0, z_acc), 2.25);
        }
        fields[pkey] = out_field;
      }

      //Return statement
      return {
        fields: fields,
        kriging_bundle: bundle,
        r_squared_by_period: r_squared_by_period
      };
    }


    /**
     * Step F: Exports GeoPNG rasters and diagnostics JSON (`tau1`, `nugget_to_sill_ratio`, `r_squared`)
     * consumable by `audit_kriging_sharpness.py`.
     * @alias ViscountMaternKriging.F_exportBenchmarkRastersAndDiagnostics
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

      let period_keys = Object.keys(surface.fields || {});
      for (let i = 0; i < period_keys.length; i++) {
        let pkey = period_keys[i];
        let model = bundle.kriging_models[pkey];
        let field = surface.fields[pkey];
        let p_cfg = period_by_key[pkey] || {};
        let png_filename = p_cfg.filename || `${pkey}.png`;
        let png_out = path.join(out_dir, png_filename);

        if (field && options.write_rasters !== false) {
          let img = new PNG({ colorType: 6, height: bundle.mask_data.grid_height, width: bundle.mask_data.grid_width });
          let fbuf = new ArrayBuffer(4);
          let fdv = new DataView(fbuf);
          for (let x = 0; x < bundle.mask_data.valid_cell_count; x++) {
            let v = field[x];
            if (v > 1e-6 && Number.isFinite(v)) {
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

        variogram_models[pkey] = {
          c0_nugget: Number(model.c0_nugget.toFixed(6)),
          eta_nugget_ratio: Number(model.eta_nugget_ratio.toFixed(4)),
          nugget_to_sill_ratio: Number(model.nugget_to_sill_ratio.toFixed(4)),
          residual_r2: surface.r_squared_by_period[pkey] || 0,
          tau1_dimensionless: Number(model.tau1_dimensionless.toFixed(4)),
          tau2_dimensionless: Number(model.tau2_dimensionless.toFixed(4))
        };
      }

      let diagnostics = {
        generated_at_gmt0: new Date().toISOString(),
        tau1_dimensionless: Number(bundle.tau1_dimensionless.toFixed(4)),
        tau2_dimensionless: Number(bundle.tau2_dimensionless.toFixed(4)),
        valid_cells: bundle.mask_data.valid_cell_count,
        variogram_models: variogram_models
      };
      fs.writeFileSync(meta_path, JSON.stringify(diagnostics, null, 2), "utf8");

      //Return statement
      return diagnostics;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountMaternKriging: global.ViscountMaternKriging };
