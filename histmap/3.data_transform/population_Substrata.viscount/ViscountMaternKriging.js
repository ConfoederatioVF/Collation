//Import modules
let fs = global.fs || require("fs");
let JSON5 = global.JSON5 || require("json5");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");
let { ViscountBiophysicalCovariates } = global.ViscountBiophysicalCovariates ? global : require("./ViscountBiophysicalCovariates.js");

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

        if (k_cfg.bermuda_pixel) {
          let b_idx = k_cfg.bermuda_pixel.row*grid_w + k_cfg.bermuda_pixel.col;
          if (i === b_idx && land_area_grid[i] <= 0)
            land_area_grid[i] = Number(k_cfg.bermuda_pixel.area_km2) || 53;
        }

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
      let earth_radius_km = bundle.mask_data.earth_radius_km || 6371;
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

      let active_domestic_catchments = 0;
      let dom_obs_count = 0;
      let domestic_catchments = 0;
      let domestic_site_count_unique_sum = 0;
      let sorted_raw_areas = [];

      for (let i = 0; i < n_obs; i++) {
        let eff_a = Math.max(bundle.mask_data.mean_cell_land_area_km2, obs_list[i].effective_area_km2 || raw_areas[i]);

        obs_list[i].effective_area_km2 = eff_a;
        obs_list[i].voronoi_area_km2 = eff_a;
        if (!obs_list[i].is_frontier_buffer) {
          dom_obs_count++;
          sorted_raw_areas.push(eff_a);
          let has_any = (obs_list[i].total_sites_all_periods > 0);
          let p_keys = Object.keys(obs_list[i].periods || {});
          let obs_sum = 0;

          for (let x = 0; x < p_keys.length; x++)
            obs_sum += (obs_list[i].periods[p_keys[x]] || 0);
          if (has_any || obs_sum > 0) active_domestic_catchments++;
          domestic_site_count_unique_sum += (obs_list[i].total_sites_all_periods > 0) ? obs_list[i].total_sites_all_periods : obs_sum;
        }
      }
      domestic_catchments = dom_obs_count;
      sorted_raw_areas.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
      let q25_raw = sorted_raw_areas[Math.floor(0.25*Math.max(0, sorted_raw_areas.length - 1))] || 1000;
      let med_raw = sorted_raw_areas[Math.floor(0.50*Math.max(0, sorted_raw_areas.length - 1))] || 5000;
      let q75_raw = sorted_raw_areas[Math.floor(0.75*Math.max(0, sorted_raw_areas.length - 1))] || 10000;

      //Group observations into 3.5° x 3.5° macro-tiles (POLARIS oblast analogue), regularise area support & extreme single-county CRM salvage spikes
      let tile_deg = (med_raw >= 1000) ? 3.5 : 0.75;
      let tile_map = new Map();

      for (let i = 0; i < n_obs; i++) {
        let o = obs_list[i];
        let tile_key = (o.is_frontier_buffer) ?
          `F_${Math.floor(o.lon/tile_deg)}_${Math.floor(o.lat/tile_deg)}` :
          `D_${Math.floor(o.lon/tile_deg)}_${Math.floor(o.lat/tile_deg)}`;

        o._idx = i;
        o.tile_key = tile_key;
        if (!o.reg_periods) o.reg_periods = {};
        for (let x = 0; x < period_configs.length; x++) {
          let pkey = period_configs[x].key;

          o.reg_periods[pkey] = o.periods[pkey] || 0;
        }
        if (!tile_map.has(tile_key)) tile_map.set(tile_key, []);
        tile_map.get(tile_key).push(o);
      }

      for (let [tile_key, tile_obs] of tile_map.entries()) {
        let is_front_tile = tile_key.startsWith("F_");
        let tile_area_sum = 0;

        for (let i = 0; i < tile_obs.length; i++) {
          let raw_v = (tile_obs[i].is_frontier_buffer) ?
            Math.max(bundle.mask_data.mean_cell_land_area_km2, Math.min(q75_raw, tile_obs[i].voronoi_area_km2 || 0.78*med_raw)) :
            tile_obs[i].voronoi_area_km2;

          tile_obs[i].voronoi_area_km2 = raw_v;
          tile_area_sum += raw_v;
        }

        let mean_tile_a = tile_area_sum/Math.max(1, tile_obs.length);
        let reg_areas = new Float64Array(tile_obs.length);
        let reg_sum = 0;

        for (let i = 0; i < tile_obs.length; i++) {
          let reg_a = Math.max(0.45*mean_tile_a, Math.min(2.0*mean_tile_a, tile_obs[i].voronoi_area_km2));

          reg_areas[i] = reg_a;
          reg_sum += reg_a;
        }

        let area_scale = (reg_sum > 0) ? (tile_area_sum/reg_sum) : 1.0;

        for (let i = 0; i < tile_obs.length; i++)
          tile_obs[i].effective_area_km2 = Math.max(bundle.mask_data.mean_cell_land_area_km2, reg_areas[i]*area_scale);

        //Regularise extreme single-county CRM salvage-excavation spikes within populated tiles (POLARIS SitesIARASObservationUtils L645-658)
        if (!is_front_tile && tile_obs.length >= 4) {
          for (let i = 0; i < period_configs.length; i++) {
            let pkey = period_configs[i].key;
            let pos_vals = [];

            for (let x = 0; x < tile_obs.length; x++)
              if ((tile_obs[x].reg_periods[pkey] || 0) > 0) pos_vals.push(tile_obs[x].reg_periods[pkey]);

            if (pos_vals.length >= 4) {
              pos_vals.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
              let local_q50 = pos_vals[Math.floor(0.50*(pos_vals.length - 1))];
              let local_q75 = pos_vals[Math.floor(0.75*(pos_vals.length - 1))];
              let local_iqr = Math.max(1, local_q75 - local_q50);
              let local_cap = local_q75 + 1.35*local_iqr;

              for (let x = 0; x < tile_obs.length; x++) {
                let s_val = tile_obs[x].reg_periods[pkey] || 0;

                if (s_val > local_cap) {
                  let ex_val = s_val - local_cap;

                  tile_obs[x].reg_periods[pkey] = local_cap + (local_iqr*ex_val)/(local_iqr + ex_val);
                }
              }
            }
          }
        }
      }

      let valid_areas = [];

      for (let i = 0; i < n_obs; i++)
        valid_areas.push(obs_list[i].effective_area_km2);
      valid_areas.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
      let q25 = valid_areas[Math.floor(0.25*(valid_areas.length - 1))] || 1000;
      let q75 = valid_areas[Math.floor(0.75*(valid_areas.length - 1))] || 10000;
      let p90_area = valid_areas[Math.floor(0.90*(valid_areas.length - 1))] || q75;
      let med_area = valid_areas[Math.floor(0.50*(valid_areas.length - 1))] || 5000;

      let eval_radius_km = new Float64Array(n_obs);
      let obs_radius_km = new Float64Array(n_obs);
      let raw_cell_radius = new Float32Array(n_valid);

      for (let i = 0; i < n_obs; i++) {
        let clamped_a = Math.max(0.35*q25, Math.min(q75, obs_list[i].effective_area_km2));
        let eval_a = Math.max(0.35*q25, Math.min(Math.max(2.6*q75, p90_area*1.45), obs_list[i].effective_area_km2));

        obs_list[i].radius_km = Math.sqrt(clamped_a/Math.PI);
        obs_radius_km[i] = obs_list[i].radius_km;
        eval_radius_km[i] = Math.sqrt(eval_a/Math.PI);
      }

      //Initialise raw catchment intensities S_{k,p} / A_k without short-lag Gaussian blurring
      for (let i = 0; i < period_configs.length; i++) {
        let pkey = period_configs[i].key;

        for (let x = 0; x < n_obs; x++) {
          let sk = obs_list[x].reg_periods[pkey] || 0;
          let ak = Math.max(1e-6, obs_list[x].effective_area_km2);

          obs_list[x].eb_densities[pkey] = sk/ak;
        }
      }

      //POLARIS upward-only Cauchy spatial-neighbourhood macro-tile survey-completeness harmonisation
      if (n_obs >= 500) {
        let macro_list = [];

        for (let [tile_key, tile_obs] of tile_map.entries()) {
          let all_s = 0;
          let area_s = 0;
          let lat_s = 0;
          let lon_s = 0;
          let ux_s = 0;
          let uy_s = 0;
          let uz_s = 0;

          for (let i = 0; i < tile_obs.length; i++) {
            let o = tile_obs[i];
            let a = o.effective_area_km2;

            area_s += a;
            all_s += (o.total_sites_all_periods || 0);
            lat_s += a*o.lat;
            lon_s += a*o.lon;
            ux_s += a*o.ux;
            uy_s += a*o.uy;
            uz_s += a*o.uz;
          }
          let nrm = Math.sqrt(ux_s*ux_s + uy_s*uy_s + uz_s*uz_s) || 1;

          macro_list.push({
            all_z: Math.sqrt(Math.max(0, all_s/Math.max(1, area_s))),
            area_km2: area_s,
            is_front: tile_key.startsWith("F_"),
            lat: lat_s/Math.max(1, area_s),
            lon: lon_s/Math.max(1, area_s),
            obs: tile_obs,
            radius_km: Math.sqrt(area_s/Math.PI),
            ux: ux_s/nrm,
            uy: uy_s/nrm,
            uz: uz_s/nrm
          });
        }

        for (let i = 0; i < period_configs.length; i++) {
          let all_z_sum = 0;
          let per_z_sum = 0;
          let pkey = period_configs[i].key;
          let tile_means = new Float64Array(macro_list.length);
          let z_arr = new Float64Array(n_obs);

          for (let x = 0; x < n_obs; x++)
            z_arr[x] = Math.sqrt(Math.max(0, obs_list[x].eb_densities[pkey] || 0));

          for (let x = 0; x < macro_list.length; x++) {
            let asum = 0;
            let mc = macro_list[x];
            let zsum = 0;

            for (let y = 0; y < mc.obs.length; y++) {
              let o = mc.obs[y];
              let a = o.effective_area_km2;

              asum += a;
              zsum += a*z_arr[o._idx];
            }
            tile_means[x] = (asum > 0) ? zsum/asum : 0;
            if (!mc.is_front && mc.lat < 54.0 && mc.all_z > 0) {
              all_z_sum += mc.area_km2*mc.all_z;
              per_z_sum += mc.area_km2*tile_means[x];
            }
          }
          let per_ratio = (all_z_sum > 1e-6) ? per_z_sum/all_z_sum : 0;

          for (let x = 0; x < macro_list.length; x++) {
            let mx = macro_list[x];

            if (mx.is_front || mx.lat >= 54.0) continue;
            let r2 = mx.radius_km*mx.radius_km;
            let wsum = 0;
            let wz = 0;

            for (let y = 0; y < macro_list.length; y++) {
              if (x === y) continue;
              let my = macro_list[y];

              if (my.lat >= 56.0) continue;
              let dot = Math.max(-1, Math.min(1, mx.ux*my.ux + mx.uy*my.uy + mx.uz*my.uz));
              let d2 = earth_radius_km*earth_radius_km*Math.max(0, 2 - 2*dot);

              if (d2 > 640000) continue;
              let w = my.area_km2/(d2 + r2);

              wsum += w;
              wz += w*tile_means[y];
            }

            let nbr_prior = (wsum > 0) ? wz/wsum : tile_means[x];
            let cap_prior = Math.max(nbr_prior, 0.85*mx.all_z*per_ratio);

            if (tile_means[x] < 0.72*cap_prior) {
              let all_z_tile = Math.max(1e-6, mx.all_z);
              let mean_z_tile = Math.max(1e-6, tile_means[x]);
              let target_mean = 0.45*tile_means[x] + 0.55*cap_prior;

              for (let y = 0; y < mx.obs.length; y++) {
                let o = mx.obs[y];
                let o_all_z = Math.sqrt(Math.max(0, (o.total_sites_all_periods || 0)/Math.max(1, o.effective_area_km2)));
                let z_raw = z_arr[o._idx];
                let rel_shape = (tile_means[x] > 1e-6) ?
                  (0.55*(z_raw/mean_z_tile) + 0.45*(o_all_z/all_z_tile)) :
                  (o_all_z/all_z_tile);
                let z_new = Math.max(z_raw, target_mean*Math.max(0.18, rel_shape));

                o.eb_densities[pkey] = z_new*z_new;
              }
            }
          }
        }
      }

      //Enforce minimum catchment denominator on 1-pixel barrier islands and apply 1-ring Poisson-Gamma credibility smoothing
      let floor_area = 0.35*med_area;

      for (let i = 0; i < n_obs; i++) {
        let o = obs_list[i];

        if (o.effective_area_km2 < floor_area) {
          let a_sc = o.effective_area_km2/floor_area;

          o.effective_area_km2 = floor_area;
          for (let x = 0; x < period_configs.length; x++) {
            let pkey = period_configs[x].key;

            o.eb_densities[pkey] = (o.eb_densities[pkey] || 0)*a_sc;
          }
        }
      }

      let loc_nbr_idx = [];
      let loc_nbr_w = [];

      for (let i = 0; i < n_obs; i++) {
        let is_dom_i = !obs_list[i].is_frontier_buffer;
        let nbr_i = [];
        let ri = obs_radius_km[i];
        let uxi = obs_ux[i];
        let uyi = obs_uy[i];
        let uzi = obs_uz[i];
        let w_i = [];

        for (let x = 0; x < n_obs; x++) {
          if (x === i) continue;
          if (is_dom_i && obs_list[x].is_frontier_buffer) continue;
          let dot = Math.max(-1, Math.min(1, uxi*obs_ux[x] + uyi*obs_uy[x] + uzi*obs_uz[x]));
          let c2 = Math.max(0, 2 - 2*dot);
          let h = earth_radius_km*Math.sqrt(c2)*(1 + c2/24 + (3*c2*c2)/640);
          let rx = obs_radius_km[x];
          let u = h/Math.max(1e-6, Math.sqrt(0.5*(ri*ri + rx*rx)));

          if (u <= 1.55) {
            nbr_i.push(x);
            w_i.push(obs_list[x].effective_area_km2/(1 + Math.pow(u/0.90, 3)));
          }
        }
        loc_nbr_idx.push(nbr_i);
        loc_nbr_w.push(w_i);
      }

      for (let i = 0; i < period_configs.length; i++) {
        let new_dens = new Float64Array(n_obs);
        let pkey = period_configs[i].key;
        let raw_z = new Float64Array(n_obs);

        for (let x = 0; x < n_obs; x++)
          raw_z[x] = Math.sqrt(Math.max(0, obs_list[x].eb_densities[pkey] || 0));

        for (let x = 0; x < n_obs; x++) {
          let sk = obs_list[x].periods[pkey] || 0;
          let tot_s = obs_list[x].total_sites_all_periods || 0;

          if (tot_s === 0 && sk === 0) {
            new_dens[x] = 0;
            continue;
          }

          let idx_x = loc_nbr_idx[x];
          let w_sum = 0;
          let w_x = loc_nbr_w[x];
          let wz_sum = 0;

          for (let y = 0; y < idx_x.length; y++) {
            let wg = w_x[y];

            w_sum += wg;
            wz_sum += wg*raw_z[idx_x[y]];
          }

          let cred = (n_obs < 500) ? sk/(sk + 1.0) : sk/(sk + 3.5);
          let prior_z = (w_sum > 0) ? (wz_sum/w_sum) : raw_z[x];
          let z_post = cred*raw_z[x] + (1 - cred)*(0.78*prior_z + 0.22*raw_z[x]);

          new_dens[x] = z_post*z_post;
        }

        for (let x = 0; x < n_obs; x++)
          obs_list[x].eb_densities[pkey] = new_dens[x];
      }

      for (let i = 0; i < n_valid; i++)
        raw_cell_radius[i] = eval_radius_km[cell_nearest[i]];

      let smooth_cell_r = ViscountBiophysicalCovariates.smoothValidFieldOnGrid(bundle.mask_data, raw_cell_radius, 6);

      //Return statement
      return {
        active_domestic_catchments: active_domestic_catchments,
        adm2_coverage_ratio: Number((active_domestic_catchments/Math.max(1, domestic_catchments)).toFixed(4)),
        cell_nearest_obs: cell_nearest,
        cell_radius_km: smooth_cell_r,
        config: bundle.config,
        domestic_catchments: domestic_catchments,
        domestic_site_count_unique_sum: domestic_site_count_unique_sum,
        mask_data: bundle.mask_data,
        median_radius_km: Math.sqrt(med_area/Math.PI),
        median_voronoi_area_km2: med_area,
        obs_count: n_obs,
        obs_list: obs_list,
        obs_radius_km: obs_radius_km,
        obs_ux: obs_ux,
        obs_uy: obs_uy,
        obs_uz: obs_uz,
        p90_radius_km: Math.sqrt(p90_area/Math.PI),
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
      let pooled_hits = new Int32Array(dim_lag_bins.length);
      let pooled_norm_gammas = new Float64Array(dim_lag_bins.length);
      let pooled_pair_totals = new Int32Array(dim_lag_bins.length);
      let pooled_u_lags = new Float64Array(dim_lag_bins.length);
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
            let skip_ocean_gap = (
              obs_bundle.median_radius_km < 15.0 &&
              h > 140.0
            );

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

      //Evaluate pooled empirical variogram to fix tau1 in [0,60, 1,50] and tau2 >= 1,8*tau1
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

        //Interpolate sparse/empty bins from nearest valid populated neighbour rather than pinning to sill or single-pair outliers
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

        for (let x = 0; x < n_bins; x++) {
          if (bin_nb[x] >= min_bin_pairs) {
            pooled_norm_gammas[x] += emp_gammas[x]/sample_var;
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
        let p0 = pop_pooled[0];
        let p1 = pop_pooled[1];
        if (pop_pooled.length > 2 && pooled_norm_gammas[pop_pooled[2]] > pooled_norm_gammas[p1]) p1 = pop_pooled[2];
        let g0 = pooled_norm_gammas[p0];
        let g1 = pooled_norm_gammas[p1];
        let plateau_bins = [];

        for (let x = 0; x < pop_pooled.length; x++) {
          let bi = pop_pooled[x];

          if (pooled_u_lags[bi] >= 2.60 && pooled_u_lags[bi] <= 7.00)
            plateau_bins.push(bi);
        }
        let p_tail = (plateau_bins.length >= 2) ?
          plateau_bins :
          pop_pooled.slice(Math.min(3, Math.max(0, pop_pooled.length - 3)), Math.min(pop_pooled.length, 6));

        if (p_tail.length === 0) p_tail = pop_pooled.slice(Math.max(0, pop_pooled.length - 3));
        let sill = 0;

        for (let i = 0; i < p_tail.length; i++) sill += pooled_norm_gammas[p_tail[i]]/Math.max(1, p_tail.length);
        sill = Math.max(0.1, sill);
        let s0_pool = sqrt3*pooled_u_lags[p0]/1.20;
        let s1_pool = sqrt3*pooled_u_lags[p1]/1.20;
        let psi0_pool = 1 - (1 + s0_pool)*Math.exp(-s0_pool);
        let psi1_pool = 1 - (1 + s1_pool)*Math.exp(-s1_pool);
        let slope_p = Math.max(0, (g1 - g0)/Math.max(1e-6, psi1_pool - psi0_pool));
        let c0 = Math.max(0, g0 - psi0_pool*slope_p);
        let target1 = c0 + (1 - (1 + sqrt3)*Math.exp(-sqrt3))*Math.max(1e-6, sill - c0);
        let poly_pts = [[0, c0]];
        let crossed_t1 = false;

        for (let idx_p = 0; idx_p < pop_pooled.length; idx_p++)
          poly_pts.push([pooled_u_lags[pop_pooled[idx_p]], pooled_norm_gammas[pop_pooled[idx_p]]]);

        for (let idx_p = 0; idx_p < poly_pts.length - 1; idx_p++) {
          if (poly_pts[idx_p][1] <= target1 && poly_pts[idx_p + 1][1] >= target1) {
            let frac = (target1 - poly_pts[idx_p][1])/Math.max(1e-8, poly_pts[idx_p + 1][1] - poly_pts[idx_p][1]);

            raw_tau1 = poly_pts[idx_p][0] + frac*(poly_pts[idx_p + 1][0] - poly_pts[idx_p][0]);
            crossed_t1 = true;
            break;
          }
        }
        if (!crossed_t1) {
          raw_tau1 = (pooled_norm_gammas[p0] >= target1) ? pooled_u_lags[p0] : pooled_u_lags[pop_pooled[pop_pooled.length - 1]];
        }
        tau1 = Math.max(0.60, Math.min(1.50, raw_tau1));
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

        let raw_z = period_z_map[pkey];
        let z_adj = new Float64Array(n_obs);

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

            if (kw < 1e-3) continue;
            let r2 = kw*kw;

            sum_w += r2;
            if (raw_z[y] > 0) {
              act_w += r2;
              sum_wz += r2*raw_z[y];
            }
          }
          let act_frac = (sum_w > 1e-6) ? act_w/sum_w : 0;
          let nbr_z = (act_w > 1e-6) ? sum_wz/act_w : 0;

          z_adj[x] = 0.18*act_frac*nbr_z;
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
          effective_short_range_km: Number((raw_tau1*(obs_bundle.median_radius_km || 0)).toFixed(2)),
          empirical_gammas: obs.empirical_gammas,
          empirical_u_lags: obs.empirical_u_lags,
          eta_nugget_ratio: eta,
          nugget_to_sill_ratio: obs.c0_norm/obs.sill_norm,
          raw_nugget_to_sill_ratio: obs.raw_nugget_to_sill_ratio,
          raw_tau1_dimensionless: raw_tau1,
          s_obs: obs.s_obs,
          sample_variance: obs.sample_variance,
          tau1_dimensionless: tau1,
          tau2_dimensionless: tau2,
          total_sites: (obs_bundle.period_totals && obs_bundle.period_totals[pkey]) ? obs_bundle.period_totals[pkey] : 0,
          z_adj: z_adj
        };
      }

      //Return statement
      return {
        config: config,
        kriging_models: kriging_models,
        mask_data: obs_bundle.mask_data,
        matern_lut: matern_lut,
        obs_bundle: obs_bundle,
        raw_tau1_dimensionless: raw_tau1,
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
      let active_periods = [];
      let bio_covs = (options.disable_biophysical_covariates === true) ?
        null :
        ViscountBiophysicalCovariates.buildStaticCovariates(bundle.mask_data, bundle.config);
      let cell_area = bundle.mask_data.cell_land_area;
      let cell_r = bundle.obs_bundle.cell_radius_km;
      let cell_ux = bundle.mask_data.cell_ux;
      let cell_uy = bundle.mask_data.cell_uy;
      let cell_uz = bundle.mask_data.cell_uz;
      let earth_r = bundle.mask_data.earth_radius_km;
      let fields = {};
      let hab_cache = new Map();
      let inv_tau1 = 1/bundle.tau1_dimensionless;
      let inv_tau2 = 1/bundle.tau2_dimensionless;
      let lut = bundle.matern_lut;
      let lut_scale = 8191/8;
      let max_cell_r = 0;
      let n_obs = bundle.obs_bundle.obs_count;
      let min_dot_per_obs = new Float64Array(n_obs);
      let n_valid = bundle.mask_data.valid_cell_count;
      let obs_r = bundle.obs_bundle.obs_radius_km;
      let obs_ux = bundle.obs_bundle.obs_ux;
      let obs_uy = bundle.obs_bundle.obs_uy;
      let obs_uz = bundle.obs_bundle.obs_uz;
      let period_configs = Array.isArray(bundle.config.periods) ? bundle.config.periods : [];
      let pixel_side_km = Math.sqrt(Math.max(10, bundle.mask_data.mean_cell_land_area_km2 || 50));
      let meso_px = Math.max(4, Math.round((bundle.obs_bundle.median_radius_km || 30)/pixel_side_km));
      let r_squared_by_period = {};
      let raw_potentials = {};
      let wls_betas_by_period = {};

      //Function body
      for (let i = 0; i < n_valid; i++)
        if (cell_r[i] > max_cell_r) max_cell_r = cell_r[i];

      for (let x = 0; x < n_obs; x++) {
        let rx = obs_r[x];
        let h_max = 7.99*bundle.tau2_dimensionless*Math.sqrt(0.5*(max_cell_r*max_cell_r + rx*rx));

        min_dot_per_obs[x] = (h_max >= Math.PI*earth_r) ? -2.0 : (Math.cos(h_max/earth_r) - 1e-4);
      }

      for (let p = 0; p < period_configs.length; p++) {
        let p_cfg = period_configs[p];
        let pkey = p_cfg.key;
        let model = bundle.kriging_models[pkey];

        if (!model) continue;

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
        raw_potentials[pkey] = new Float32Array(n_valid);
        active_periods.push({
          c1: model.c1_weight,
          c2: model.c2_weight,
          cfg: p_cfg,
          model: model,
          pkey: pkey,
          pot: raw_potentials[pkey],
          var_restore: model.centroid_variance_restoration || 1.0,
          w: w
        });
      }

      let n_active = active_periods.length;
      let z_acc = new Float64Array(n_active);

      for (let i = 0; i < n_valid; i++) {
        let a_i = cell_area[i];
        let cx = cell_ux[i];
        let cy = cell_uy[i];
        let cz = cell_uz[i];
        let ri = cell_r[i];
        let ri2 = ri*ri;

        for (let p = 0; p < n_active; p++) z_acc[p] = 0;

        for (let x = 0; x < n_obs; x++) {
          let dot = cx*obs_ux[x] + cy*obs_uy[x] + cz*obs_uz[x];

          if (dot <= min_dot_per_obs[x]) continue;
          if (dot > 1) dot = 1;
          else if (dot < -1) dot = -1;

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

          for (let p = 0; p < n_active; p++) {
            let ap = active_periods[p];

            z_acc[p] += ap.w[x]*(ap.c1*m1 + ap.c2*m2);
          }
        }

        for (let p = 0; p < n_active; p++) {
          let z_val = Math.max(0, active_periods[p].var_restore*z_acc[p]);

          active_periods[p].pot[i] = a_i*Math.pow(z_val, 2.25);
        }
      }

      for (let p = 0; p < n_active; p++) {
        let ap = active_periods[p];
        let p_cfg = ap.cfg;
        let pkey = ap.pkey;
        let pot_field = ap.pot;
        let raw_pot_sum = 0;
        let target_sites = Math.max(1, (bundle.obs_bundle.period_totals && bundle.obs_bundle.period_totals[pkey]) ? bundle.obs_bundle.period_totals[pkey] : 0);

        for (let i = 0; i < n_valid; i++) raw_pot_sum += pot_field[i];

        if (bio_covs) {
          let rep_year = Number.isFinite(p_cfg.representative_year) ?
            p_cfg.representative_year :
            0.5*((p_cfg.approx_start_year || p_cfg.start_year || 0) + (p_cfg.approx_end_year || p_cfg.end_year || 0));
          let local_u_hab = ViscountBiophysicalCovariates.computeCompositeHabitationField(
            bundle.mask_data,
            bundle.obs_bundle,
            bio_covs,
            p_cfg,
            bundle.config,
            hab_cache
          );
          let local_rk = ViscountBiophysicalCovariates.computeResidualKrigingWeights(
            bundle.mask_data,
            bundle.obs_bundle,
            bio_covs,
            local_u_hab,
            ap.model.z_adj,
            meso_px,
            rep_year,
            bundle.config
          );
          let coupled_sum = 0;
          let out_field = new Float32Array(n_valid);

          wls_betas_by_period[pkey] = {
            beta_0_hab: local_rk.beta[0],
            beta_1_nat: local_rk.beta[1],
            beta_2_eco: local_rk.beta[2],
            beta_3_fluvial: local_rk.beta[3],
            beta_4_coastal: local_rk.beta[4]
          };
          for (let i = 0; i < n_valid; i++) {
            out_field[i] = pot_field[i]*local_rk.weights[i];
            coupled_sum += out_field[i];
          }

          let ref_mass = Math.max(1, target_sites || raw_pot_sum || 1);
          let norm_scale = (coupled_sum > 0) ? ref_mass/coupled_sum : 1;

          for (let i = 0; i < n_valid; i++) out_field[i] = out_field[i]*norm_scale;
          fields[pkey] = out_field;
        } else {
          fields[pkey] = pot_field;
        }
      }

      //Return statement
      return {
        bio_covs: bio_covs,
        fields: fields,
        hab_cache: hab_cache,
        kriging_bundle: bundle,
        meso_px: meso_px,
        r_squared_by_period: r_squared_by_period,
        raw_potentials: raw_potentials,
        wls_betas_by_period: wls_betas_by_period,
        wls_covariates_active: Boolean(bio_covs)
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
            let v = Number.isFinite(field[x]) ? Math.max(1e-5, field[x]) : 1e-5;
            field[x] = v;
            if (v > max_val) max_val = v;
            sum_val += v;
            active_cells++;
            sorted_vals.push(v);
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
          effective_short_range_km: model.effective_short_range_km || 0,
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
        valid_cells: bundle.mask_data.valid_cell_count,
        variogram_models: variogram_models,
        wls_covariates_active: Boolean(surface.wls_covariates_active)
      };
      fs.writeFileSync(meta_path, JSON.stringify(diagnostics, null, 2), "utf8");

      //Return statement
      return diagnostics;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountMaternKriging: global.ViscountMaternKriging };
