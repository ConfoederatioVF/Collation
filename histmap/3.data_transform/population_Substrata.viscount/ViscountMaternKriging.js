//Import modules
let fs = global.fs || require("fs");
let JSON5 = global.JSON5 || require("json5");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");
let { ViscountBiophysicalCovariates } = global.ViscountBiophysicalCovariates ? global : require("./ViscountBiophysicalCovariates.js");
let { ViscountHUResidualKriging } = global.ViscountHUResidualKriging ? global : require("./ViscountHUResidualKriging.js");
let { ViscountMaternVariogram } = global.ViscountMaternVariogram ? global : require("./ViscountMaternVariogram.js");
let { ViscountRuralSuitability } = global.ViscountRuralSuitability ? global : require("./ViscountRuralSuitability.js");

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
              has_documented_settlement: Boolean(props.has_documented_settlement),
              id: rid,
              is_frontier_buffer: Boolean(props.is_frontier_buffer),
              lat: lat,
              lon: lon,
              max_settlement_pop: Number(props.max_settlement_pop) || 0,
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
          if (props.has_documented_settlement) entry.has_documented_settlement = true;
          if ((Number(props.max_settlement_pop) || 0) > (entry.max_settlement_pop || 0))
            entry.max_settlement_pop = Number(props.max_settlement_pop) || 0;
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

      //Compute per-catchment biome taphonomy and modern urban CRM salvage shares before spike filtering
      let apply_taph = Boolean(bundle.config && bundle.config.kriging_config && bundle.config.kriging_config.apply_arid_taphonomic_correction);
      let apply_urb_debias = Boolean(bundle.config && bundle.config.kriging_config && bundle.config.kriging_config.apply_urban_salvage_debias);

      if (apply_taph || apply_urb_debias) {
        ViscountBiophysicalCovariates.computeCatchmentTaphonomyAndUrbanShares(
          bundle.mask_data,
          obs_list,
          cell_nearest,
          bundle.config
        );
      }

      for (let [tile_key, tile_obs] of tile_map.entries()) {
        let is_front_tile = tile_key.startsWith("F_");
        let tile_area_sum = 0;

        for (let i = 0; i < tile_obs.length; i++) {
          let is_micro_island_catch = (!tile_obs[i].is_frontier_buffer && med_raw >= 1000 && tile_obs[i].voronoi_area_km2 < 0.45*med_raw);
          let raw_v = (tile_obs[i].is_frontier_buffer) ?
            Math.max(bundle.mask_data.mean_cell_land_area_km2, Math.min(q75_raw, tile_obs[i].voronoi_area_km2 || 0.78*med_raw)) :
            (is_micro_island_catch ? 0.45*med_raw : tile_obs[i].voronoi_area_km2);

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

        //Regularise extreme single-county CRM salvage-excavation spikes while sparing verified pre-Columbian hubs
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
                let is_doc_hub = Boolean(
                  tile_obs[x].has_documented_settlement &&
                  (tile_obs[x].max_settlement_pop || 0) >= 400 &&
                  (tile_obs[x].urb_core_share || 0) < 0.30
                );

                if (!is_doc_hub && s_val > local_cap) {
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
      let preserve_dyn = Boolean(bundle.config && bundle.config.kriging_config && bundle.config.kriging_config.preserve_period_dynamics);
      let raw_cell_radius = new Float32Array(n_valid);

      for (let i = 0; i < n_obs; i++) {
        let clamped_a = Math.max(0.35*q25, Math.min(q75, obs_list[i].effective_area_km2));
        let eval_a = preserve_dyn ?
          Math.max(0.28*q25, Math.min(1.15*q75, obs_list[i].effective_area_km2)) :
          Math.max(0.35*q25, Math.min(Math.max(2.6*q75, p90_area*1.45), obs_list[i].effective_area_km2));

        obs_list[i].radius_km = Math.sqrt(clamped_a/Math.PI);
        obs_radius_km[i] = obs_list[i].radius_km;
        eval_radius_km[i] = Math.sqrt(eval_a/Math.PI);
      }

      //Initialise raw catchment intensities S_{k,p} / A_k with optional arid/humid taphonomic & Greenland survey normalisation
      for (let i = 0; i < period_configs.length; i++) {
        let pkey = period_configs[i].key;

        for (let x = 0; x < n_obs; x++) {
          let o = obs_list[x];
          let sk = o.reg_periods[pkey] || 0;
          let ak = Math.max(1e-6, o.effective_area_km2);
          let taph_mult = 1.0;

          if (apply_taph && !o.is_frontier_buffer && sk > 0) {
            let mf = o.mean_forest || 0;
            let mm = o.mean_maxln || 0;

            if (o.lat >= 59.5 && o.lon >= -60.0)
              taph_mult = 0.25;
            else if (mm < 0.25 && mf < 0.15)
              taph_mult = 0.42;
            else if (mm < 0.40 && mf < 0.28)
              taph_mult = 0.68;
            else if (mf >= 0.42 || mm >= 0.48)
              taph_mult = 1.38;
          }
          o.eb_densities[pkey] = (sk/ak)*taph_mult;
        }
      }

      //De-spike modern metropolitan CRM salvage hotspots using surrounding non-urban rural catchments
      if (apply_urb_debias) {
        for (let i = 0; i < period_configs.length; i++) {
          let pkey = period_configs[i].key;

          for (let x = 0; x < n_obs; x++) {
            let ox = obs_list[x];
            let is_primate_hub = Boolean(ox.has_documented_settlement && (ox.max_settlement_pop || 0) >= 2500);

            if (ox.is_frontier_buffer || (ox.urb_core_share || 0) <= 0.08 || is_primate_hub) continue;
            let cur_d = ox.eb_densities[pkey] || 0;

            if (cur_d <= 0) continue;
            let nbr_vals = [];

            for (let y = 0; y < n_obs; y++) {
              let oy = obs_list[y];

              if (y === x || oy.is_frontier_buffer || (oy.urb_core_share || 0) > 0.06) continue;
              let dot = Math.max(-1, Math.min(1, obs_ux[x]*obs_ux[y] + obs_uy[x]*obs_uy[y] + obs_uz[x]*obs_uz[y]));
              let d_km = earth_radius_km*Math.sqrt(Math.max(0, 2 - 2*dot));

              if (d_km <= 160.0 && (oy.eb_densities[pkey] || 0) > 0)
                nbr_vals.push(oy.eb_densities[pkey]);
            }
            if (nbr_vals.length >= 2) {
              nbr_vals.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
              let r_med = nbr_vals[Math.floor(0.50*(nbr_vals.length - 1))];

              if (cur_d > 1.15*r_med) ox.eb_densities[pkey] = 1.15*r_med;
            }
          }
        }
      }

      //POLARIS upward-only Cauchy spatial-neighbourhood macro-tile survey-completeness harmonisation
      if (n_obs >= 500) {
        ViscountMaternVariogram.B2_harmoniseMacroTiles({
          earth_radius_km: earth_radius_km,
          obs_list: obs_list,
          period_configs: period_configs,
          preserve_dyn: preserve_dyn,
          tile_map: tile_map
        });
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
          let mm_x = obs_list[x].mean_maxln || 0;
          let in_settled_biome = (!obs_list[x].is_frontier_buffer && mm_x >= 0.30 && obs_list[x].lat < 55.0);

          if (tot_s === 0 && sk === 0 && !in_settled_biome) {
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

          let cred = preserve_dyn ?
            ((n_obs < 500) ? sk/(sk + 0.8) : sk/(sk + 1.2)) :
            ((n_obs < 500) ? sk/(sk + 1.0) : sk/(sk + 3.5));
          let prior_z = (w_sum > 0) ? (wz_sum/w_sum) : raw_z[x];
          let zero_bridge = in_settled_biome ? ((tot_s > 0) ? 0.72*prior_z : ((mm_x >= 0.38) ? 0.52*prior_z : 0.25*prior_z)) : ((tot_s > 0) ? 0.22*prior_z : 0);
          let z_post = preserve_dyn ?
            ((sk > 0) ? (cred*raw_z[x] + (1 - cred)*(0.60*prior_z + 0.40*raw_z[x])) : zero_bridge) :
            (cred*raw_z[x] + (1 - cred)*(0.78*prior_z + 0.22*raw_z[x]));

          new_dens[x] = z_post*z_post;
        }

        for (let x = 0; x < n_obs; x++)
          obs_list[x].eb_densities[pkey] = new_dens[x];
      }

      for (let i = 0; i < n_valid; i++)
        raw_cell_radius[i] = eval_radius_km[cell_nearest[i]];

      let smooth_cell_r = ViscountRuralSuitability.smoothValidFieldOnGrid(bundle.mask_data, raw_cell_radius, preserve_dyn ? 3 : 6);

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
    /**
     * Step C delegate: invokes `ViscountMaternVariogram.C_fitTwoScaleNonStationaryMatern`.
     * @alias ViscountMaternKriging.C_fitTwoScaleNonStationaryMatern
     */
    static C_fitTwoScaleNonStationaryMatern (arg0_obs_bundle, arg1_options) {
      return ViscountMaternVariogram.C_fitTwoScaleNonStationaryMatern(arg0_obs_bundle, arg1_options);
    }


    /**
     * Step D delegate: invokes `ViscountMaternVariogram.D_solveProjectedNonNegativeDualKriging`.
     * @alias ViscountMaternKriging.D_solveProjectedNonNegativeDualKriging
     */
    static D_solveProjectedNonNegativeDualKriging (arg0_cov_matrix, arg1_z_adj, arg2_n) {
      return ViscountMaternVariogram.D_solveProjectedNonNegativeDualKriging(arg0_cov_matrix, arg1_z_adj, arg2_n);
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
        ViscountBiophysicalCovariates.buildStaticCovariates(bundle.mask_data, bundle.config, bundle.obs_bundle);
      let cell_area = bundle.mask_data.cell_land_area;
      let cell_r = bundle.obs_bundle.cell_radius_km;
      let cell_ux = bundle.mask_data.cell_ux;
      let cell_uy = bundle.mask_data.cell_uy;
      let cell_uz = bundle.mask_data.cell_uz;
      let earth_r = bundle.mask_data.earth_radius_km;
      let fields = {};
      let hab_cache = new Map();
      let lut = bundle.matern_lut;
      let lut_scale = 8191/8;
      let max_cell_r = 0;
      let max_tau2 = bundle.tau2_dimensionless;
      let n_obs = bundle.obs_bundle.obs_count;
      let min_dot_per_obs = new Float64Array(n_obs);
      let n_valid = bundle.mask_data.valid_cell_count;
      let obs_r = bundle.obs_bundle.obs_radius_km;
      let obs_ux = bundle.obs_bundle.obs_ux;
      let obs_uy = bundle.obs_bundle.obs_uy;
      let obs_uz = bundle.obs_bundle.obs_uz;
      let period_configs = Array.isArray(bundle.config.periods) ? bundle.config.periods : [];
      let pixel_side_km = Math.sqrt(Math.max(10, bundle.mask_data.mean_cell_land_area_km2 || 50));
      let preserve_dyn = Boolean(bundle.config && bundle.config.kriging_config && bundle.config.kriging_config.preserve_period_dynamics);
      let meso_px = preserve_dyn ?
        Math.max(4, Math.min(8, Math.round(0.75*(bundle.obs_bundle.median_radius_km || 25)/pixel_side_km))) :
        Math.max(4, Math.round((bundle.obs_bundle.median_radius_km || 30)/pixel_side_km));
      let r_squared_by_period = {};
      let raw_potentials = {};
      let wls_betas_by_period = {};

      //Function body
      for (let i = 0; i < n_valid; i++)
        if (cell_r[i] > max_cell_r) max_cell_r = cell_r[i];

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

        if (model.tau2_dimensionless > max_tau2) max_tau2 = model.tau2_dimensionless;
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
          inv_tau1: 1/Math.max(0.4, model.tau1_dimensionless || bundle.tau1_dimensionless),
          inv_tau2: 1/Math.max(0.8, model.tau2_dimensionless || bundle.tau2_dimensionless),
          model: model,
          pkey: pkey,
          pot: raw_potentials[pkey],
          var_restore: model.centroid_variance_restoration || 1.0,
          w: w
        });
      }

      for (let x = 0; x < n_obs; x++) {
        let rx = obs_r[x];
        let h_max = 7.99*max_tau2*Math.sqrt(0.5*(max_cell_r*max_cell_r + rx*rx));

        min_dot_per_obs[x] = (h_max >= Math.PI*earth_r) ? -2.0 : (Math.cos(h_max/earth_r) - 1e-4);
      }

      let n_active = active_periods.length;
      let shared_tau = active_periods.every(function (arg0_ap) {
        return Math.abs(arg0_ap.inv_tau1 - active_periods[0].inv_tau1) < 1e-6 &&
          Math.abs(arg0_ap.inv_tau2 - active_periods[0].inv_tau2) < 1e-6;
      });
      let inv_tau1_shared = (n_active > 0) ? active_periods[0].inv_tau1 : 1/bundle.tau1_dimensionless;
      let inv_tau2_shared = (n_active > 0) ? active_periods[0].inv_tau2 : 1/bundle.tau2_dimensionless;
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
          let pref = (2*ri*rx)/Math.max(1e-8, r2_sum);

          if (shared_tau) {
            let v2 = u*inv_tau2_shared;

            if (v2 >= 7.99) continue;
            let m1 = 0;
            let v1 = u*inv_tau1_shared;

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
          } else {
            for (let p = 0; p < n_active; p++) {
              let ap = active_periods[p];
              let wp = ap.w[x];

              if (wp <= 0) continue;
              let v2 = u*ap.inv_tau2;

              if (v2 >= 7.99) continue;
              let m1 = 0;
              let v1 = u*ap.inv_tau1;

              if (v1 < 7.99) {
                let idx1 = (v1*lut_scale) | 0;
                let frac1 = v1*lut_scale - idx1;

                m1 = pref*(lut[idx1]*(1 - frac1) + lut[idx1 + 1]*frac1);
              }
              let idx2 = (v2*lut_scale) | 0;
              let frac2 = v2*lut_scale - idx2;
              let m2 = pref*(lut[idx2]*(1 - frac2) + lut[idx2 + 1]*frac2);

              z_acc[p] += wp*(ap.c1*m1 + ap.c2*m2);
            }
          }
        }

        for (let p = 0; p < n_active; p++) {
          let z_val = Math.max(0, active_periods[p].var_restore*z_acc[p]);

          active_periods[p].pot[i] = a_i*Math.pow(z_val, 2.25);
        }
      }

      let rk_mode = (bundle.config && bundle.config.kriging_config && bundle.config.kriging_config.residual_kriging_mode) ?
        bundle.config.kriging_config.residual_kriging_mode : "";
      let residual_fields = null;

      if (bio_covs && rk_mode === "hu_hyde_residual") {
        let hu_out = ViscountHUResidualKriging.evaluateAllPeriodResidualSurfaces(bundle, bio_covs, active_periods, hab_cache);

        fields = hu_out.fields;
        residual_fields = hu_out.residual_fields || null;
        wls_betas_by_period = hu_out.wls_betas_by_period;
      } else {
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
            let local_u_hab = ViscountRuralSuitability.computeCompositeHabitationField(
              bundle.mask_data,
              bundle.obs_bundle,
              bio_covs,
              p_cfg,
              bundle.config,
              hab_cache
            );
            let local_rk = ViscountRuralSuitability.computeResidualKrigingWeights(
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
            for (let i = 0; i < n_valid; i++)
              out_field[i] = pot_field[i]*local_rk.weights[i];

            if (rep_year <= 1650 && bio_covs.uopp_valid)
              ViscountRuralSuitability.capUrbanCoreFieldToRuralRing(bundle.mask_data, out_field, bio_covs.uopp_valid, 1.12);

            for (let i = 0; i < n_valid; i++)
              coupled_sum += out_field[i];

            let ref_mass = Math.max(1, target_sites || raw_pot_sum || 1);
            let norm_scale = (coupled_sum > 0) ? ref_mass/coupled_sum : 1;

            for (let i = 0; i < n_valid; i++) out_field[i] = out_field[i]*norm_scale;
            fields[pkey] = out_field;
          } else {
            fields[pkey] = pot_field;
          }
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
        residual_fields: residual_fields,
        wls_betas_by_period: wls_betas_by_period,
        wls_covariates_active: Boolean(bio_covs)
      };
    }


    /**
     * Step F delegate: invokes `ViscountMaternVariogram.F_exportBenchmarkRastersAndDiagnostics`.
     * @alias ViscountMaternKriging.F_exportBenchmarkRastersAndDiagnostics
     */
    static F_exportBenchmarkRastersAndDiagnostics (arg0_surface_bundle, arg1_options) {
      return ViscountMaternVariogram.F_exportBenchmarkRastersAndDiagnostics(arg0_surface_bundle, arg1_options);
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountMaternKriging: global.ViscountMaternKriging };
