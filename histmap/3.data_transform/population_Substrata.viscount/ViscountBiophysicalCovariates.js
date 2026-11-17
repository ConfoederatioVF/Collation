//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * 5-arcminute (`4320x2160`) Biophysical Covariate Loader, Fluvial/Coastal Proximity Distance Engine,
   * Palaeoglacial Envelope Generator, Urban-Masked HYDE Rural De-Cliffer and Non-Negative Least Squares (NNLS)
   * Residual Kriging Synthesizer for all Operation Viscount regional domains.
   *
   * @class ViscountBiophysicalCovariates
   */
  global.ViscountBiophysicalCovariates = class {
    static _uopp_cache = new Map();

    /**
     * Builds or loads static 5-arcminute biophysical covariates (`u_nat`, `u_eco`, `u_fluvial`, `u_coastal`,
     * permanent Greenland ice mask `perm_ice_mask`, and sub-national de-cliffing partition IDs `part_id`).
     * @alias ViscountBiophysicalCovariates.buildStaticCovariates
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_config
     *
     * @returns {Object}
     */
    static buildStaticCovariates (arg0_mask_data, arg1_config) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let config = arg1_config;

      //Declare local instance variables
      let bbox = this.computeMaskBBox(mask_data);
      let cov_paths = (config && config.kriging_config && config.kriging_config.covariate_paths) ?
        config.kriging_config.covariate_paths : {};
      let forest_asc = cov_paths.forest_asc ? path.resolve(mask_data.project_root, cov_paths.forest_asc) : "";
      let forest_grid = (forest_asc && fs.existsSync(forest_asc)) ?
        this.readAscGrid(forest_asc, mask_data.grid_width*mask_data.grid_height) : null;
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let hyde_rur_1900;
      let lakes_path = cov_paths.lakes_geojson ? path.resolve(mask_data.project_root, cov_paths.lakes_geojson) : "";
      let maxln_asc = cov_paths.maxln_asc ? path.resolve(mask_data.project_root, cov_paths.maxln_asc) : "";
      let maxln_grid = (maxln_asc && fs.existsSync(maxln_asc)) ?
        this.readAscGrid(maxln_asc, grid_w*grid_h) : null;
      let n_valid = mask_data.valid_cell_count;
      let nelson_path = cov_paths.nelson_regions_png ? path.resolve(mask_data.project_root, cov_paths.nelson_regions_png) : "";
      let nelson_png = (nelson_path && fs.existsSync(nelson_path)) ? PNG.sync.read(fs.readFileSync(nelson_path)) : null;
      let part_id = new Int32Array(n_valid);
      let part_map = new Map();
      let perm_ice = new Float32Array(n_valid).fill(1.0);
      let rivers_path = cov_paths.rivers_geojson ? path.resolve(mask_data.project_root, cov_paths.rivers_geojson) : "";
      let sub_iso_asc = cov_paths.sub_iso_asc ? path.resolve(mask_data.project_root, cov_paths.sub_iso_asc) : "";
      let sub_iso_grid = (sub_iso_asc && fs.existsSync(sub_iso_asc)) ?
        this.readAscGrid(sub_iso_asc, grid_w*grid_h) : null;
      let u_coastal;
      let u_eco = new Float32Array(n_valid);
      let u_fluvial;
      let u_nat = new Float32Array(n_valid);
      let valid_indices = mask_data.valid_indices;

      //Function body
      hyde_rur_1900 = this.loadUrbanMaskedHYDEPopcRaster(mask_data, 1900, null, config);

      //1. Partition IDs + forest indicator + agricultural suitability (maxln_cr.asc)
      let f_raw = new Float32Array(n_valid);
      let mean_maxln = 0;
      let next_pid = 1;

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let f_val = (forest_grid && forest_grid[gidx] > 0) ? 1 : 0;
        let max_v = (maxln_grid && maxln_grid[gidx] > 0) ? maxln_grid[gidx] : 0;
        let iso_p = (sub_iso_grid) ? Math.round(sub_iso_grid[gidx]) : 0;
        let nid = 0;

        if (nelson_png) {
          let p4 = gidx*4;

          nid = (nelson_png.data[p4] << 16) | (nelson_png.data[p4 + 1] << 8) | nelson_png.data[p4 + 2];
        }
        let p_key = `${iso_p}_${nid}`;
        let pid = part_map.get(p_key);

        if (!pid) {
          pid = next_pid++;
          part_map.set(p_key, pid);
        }
        part_id[i] = pid;
        f_raw[i] = f_val;
        mean_maxln += Math.pow(max_v, 0.80);
      }
      mean_maxln = Math.max(1e-4, mean_maxln/Math.max(1, n_valid));

      let f_p1 = this.smoothValidFieldOnGrid(mask_data, f_raw, 2);
      let f_smooth = this.smoothValidFieldOnGrid(mask_data, f_p1, 2);

      let u_nat_raw = new Float32Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let max_v = (maxln_grid && maxln_grid[gidx] > 0) ? Math.pow(maxln_grid[gidx], 0.80)/mean_maxln : 0.45;
        let ff = Math.max(0, Math.min(1, f_smooth[i]));
        let ecotone = 4*ff*(1 - ff);

        u_nat_raw[i] = Math.max(0.04, Math.min(3.5, max_v));
        u_eco[i] = Math.max(0.05, 0.45*ecotone + 0.55*ff);
      }

      //Smooth single-pixel binary noise in Climber3 maxln suitability while preserving valley/ridge gradients
      let u_nat_sm = this.smoothValidFieldOnGrid(mask_data, u_nat_raw, 1);

      for (let i = 0; i < n_valid; i++)
        u_nat[i] = 0.45*u_nat_raw[i] + 0.55*u_nat_sm[i];

      //2. Fluvial & lake proximity (u_fluvial) + ocean coastal proximity (u_coastal)
      u_coastal = this.computeCoastalProximityField(mask_data);
      u_fluvial = this.computeFluvialProximityField(mask_data, bbox, rivers_path, lakes_path);

      //3. Identify permanent Greenland interior ice sheet with isotropic ocean-distance fjord decay & polar attenuation
      if (config && config.kriging_config && config.kriging_config.apply_ice_sheet_mask) {
        let la_grid = mask_data.land_area_grid;

        for (let i = 0; i < n_valid; i++) {
          let gidx = valid_indices[i];
          let r = Math.floor(gidx/grid_w);
          let c = gidx % grid_w;
          let lat = 90 - (r + 0.5)*180/grid_h;
          let lon = -180 + (c + 0.5)*360/grid_w;
          let grl_west = -74.0;

          if (lat < 68.0) grl_west = -56.0;
          else if (lat < 74.0) grl_west = -56.0 - (lat - 68.0)*3.0;
          else if (lat >= 78.2) grl_west = -74.0 + (lat - 78.2)*3.4;

          if (lat >= 59.5 && lon >= grl_west && lon <= -10.0) {
            let cos_lat = Math.max(0.18, Math.cos(lat*Math.PI/180));
            let min_d = 9.0;

            for (let dr = -5; dr <= 5; dr++) {
              let nr = r + dr;

              if (nr < 0 || nr >= grid_h) continue;
              for (let dc = -10; dc <= 10; dc++) {
                let nc = (c + dc + grid_w) % grid_w;

                if (la_grid[nr*grid_w + nc] <= 0) {
                  let dist_px = Math.sqrt(dr*dr + (dc*cos_lat)*(dc*cos_lat));

                  if (dist_px < min_d) min_d = dist_px;
                }
              }
            }
            let coast_env = Math.max(0.002, Math.min(1.0, Math.exp(-1.35*Math.max(0, min_d - 0.8))));
            let lat_att = Math.max(0.05, Math.min(1.0, (74.5 - lat)/12.5));

            perm_ice[i] = coast_env*lat_att;
          }
        }
      }

      //Return statement
      return {
        hyde_rur_1900: hyde_rur_1900,
        part_id: part_id,
        partition_count: next_pid,
        perm_ice: perm_ice,
        u_coastal: u_coastal,
        u_eco: u_eco,
        u_fluvial: u_fluvial,
        u_nat: u_nat
      };
    }


    /**
     * Computes marine coastal proximity `exp(-d_km / 18.0)` across valid mask cells via fast 2D chamfer BFS.
     * @alias ViscountBiophysicalCovariates.computeCoastalProximityField
     *
     * @param {Object} arg0_mask_data
     *
     * @returns {Float32Array}
     */
    static computeCoastalProximityField (arg0_mask_data) {
      //Convert from parameters
      let mask_data = arg0_mask_data;

      //Declare local instance variables
      let dist_grid = new Uint16Array(mask_data.grid_width*mask_data.grid_height).fill(65535);
      let h = mask_data.grid_height;
      let la_grid = mask_data.land_area_grid;
      let mask_grid = mask_data.mask_grid;
      let n_valid = mask_data.valid_cell_count;
      let out = new Float32Array(n_valid);
      let queue = [];
      let valid_indices = mask_data.valid_indices;
      let w = mask_data.grid_width;

      //Function body
      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let r = Math.floor(gidx/w);
        let c = gidx % w;
        let touches_sea = false;

        if (r > 0 && la_grid[gidx - w] <= 0) touches_sea = true;
        else if (r + 1 < h && la_grid[gidx + w] <= 0) touches_sea = true;
        else if (la_grid[r*w + ((c + w - 1) % w)] <= 0) touches_sea = true;
        else if (la_grid[r*w + ((c + 1) % w)] <= 0) touches_sea = true;

        if (touches_sea) {
          dist_grid[gidx] = 0;
          queue.push(gidx);
        }
      }

      let head = 0;

      while (head < queue.length) {
        let curr = queue[head++];
        let d = dist_grid[curr];

        if (d >= 12) continue;
        let r = Math.floor(curr/w);
        let c = curr % w;
        let nbrs = [
          (r > 0) ? curr - w : -1,
          (r + 1 < h) ? curr + w : -1,
          r*w + ((c + w - 1) % w),
          r*w + ((c + 1) % w)
        ];

        for (let k = 0; k < 4; k++) {
          let ni = nbrs[k];

          if (ni >= 0 && mask_grid[ni] === 1 && dist_grid[ni] > d + 1) {
            dist_grid[ni] = d + 1;
            queue.push(ni);
          }
        }
      }

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let d_px = dist_grid[gidx];

        if (d_px < 65535) {
          let lat = 90 - (Math.floor(gidx/w) + 0.5)*180/h;
          let km_per_px = 9.26*Math.max(0.25, Math.sqrt(Math.max(0.08, Math.cos(lat*Math.PI/180))));

          out[i] = Math.exp(-(d_px*km_per_px)/18.0);
        }
      }

      //Return statement
      return out;
    }


    /**
     * Computes composite de-cliffed urban-masked HYDE rural habitation `u_hab(x)` for a chronological period.
     * @alias ViscountBiophysicalCovariates.computeCompositeHabitationField
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
      let rep_years = [];

      let p_start = Number.isFinite(period_cfg.approx_start_year) ? period_cfg.approx_start_year : period_cfg.start_year;
      let p_end = Number.isFinite(period_cfg.approx_end_year) ? period_cfg.approx_end_year : period_cfg.end_year;

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
     * @alias ViscountBiophysicalCovariates.computeDeCliffedHabitationField
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
      let hyde_rur = this.loadUrbanMaskedHYDEPopcRaster(mask_data, year, hab_cache, config);
      let hyde_rur_1900 = covs.hyde_rur_1900;
      let min_area = 0.75*mask_data.mean_cell_land_area_km2;
      let n_parts = covs.partition_count;
      let n_valid = mask_data.valid_cell_count;
      let part_cnt = new Int32Array(n_parts);
      let part_id = covs.part_id;
      let part_sum = new Float64Array(n_parts);
      let raw_sqrt = new Float32Array(n_valid);
      let hab_ind = new Float32Array(n_valid);
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
     * Rasterises Natural Earth 10m rivers and lakes over the mask domain and computes exponential fluvial proximity `exp(-d_km / 24.0)`.
     * @alias ViscountBiophysicalCovariates.computeFluvialProximityField
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_bbox
     * @param {string} arg2_rivers_path
     * @param {string} arg3_lakes_path
     *
     * @returns {Float32Array}
     */
    static computeFluvialProximityField (arg0_mask_data, arg1_bbox, arg2_rivers_path, arg3_lakes_path) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let bbox = arg1_bbox;
      let rivers_path = arg2_rivers_path;
      let lakes_path = arg3_lakes_path;

      //Declare local instance variables
      let h = mask_data.grid_height;
      let w = mask_data.grid_width;
      let dist_grid = new Uint16Array(w*h).fill(65535);
      let mask_grid = mask_data.mask_grid;
      let n_valid = mask_data.valid_cell_count;
      let out = new Float32Array(n_valid).fill(0.05);
      let queue = [];
      let valid_indices = mask_data.valid_indices;

      let markCell = (arg0_lon, arg1_lat) => {
        if (arg0_lon < bbox.min_lon || arg0_lon > bbox.max_lon || arg1_lat < bbox.min_lat || arg1_lat > bbox.max_lat) return;
        let c = Math.max(0, Math.min(w - 1, Math.floor((arg0_lon + 180)*w/360)));
        let r = Math.max(0, Math.min(h - 1, Math.floor((90 - arg1_lat)*h/180)));
        let idx = r*w + c;

        if (mask_grid[idx] === 1 && dist_grid[idx] > 0) {
          dist_grid[idx] = 0;
          queue.push(idx);
        }
      };

      let rasteriseLine = (arg0_coords) => {
        for (let i = 0; i < arg0_coords.length - 1; i++) {
          let x0 = Number(arg0_coords[i][0]);
          let y0 = Number(arg0_coords[i][1]);
          let x1 = Number(arg0_coords[i + 1][0]);
          let y1 = Number(arg0_coords[i + 1][1]);
          let dx = Math.abs(x1 - x0);
          let dy = Math.abs(y1 - y0);

          if (dx > 180) continue;
          let steps = Math.max(1, Math.ceil(Math.max(dx, dy)/0.04));

          for (let s = 0; s <= steps; s++) {
            let t = s/steps;

            markCell(x0 + t*(x1 - x0), y0 + t*(y1 - y0));
          }
        }
      };

      //Function body
      if (rivers_path && fs.existsSync(rivers_path)) {
        let gj = JSON.parse(fs.readFileSync(rivers_path, "utf8"));
        let feats = Array.isArray(gj.features) ? gj.features : [];

        for (let i = 0; i < feats.length; i++) {
          let geom = feats[i].geometry;

          if (!geom || !geom.coordinates) continue;
          if (geom.type === "LineString") {
            rasteriseLine(geom.coordinates);
          } else if (geom.type === "MultiLineString") {
            for (let k = 0; k < geom.coordinates.length; k++)
              rasteriseLine(geom.coordinates[k]);
          }
        }
      }

      if (lakes_path && fs.existsSync(lakes_path)) {
        let lj = JSON.parse(fs.readFileSync(lakes_path, "utf8"));
        let feats = Array.isArray(lj.features) ? lj.features : [];

        for (let i = 0; i < feats.length; i++) {
          let geom = feats[i].geometry;

          if (!geom || !geom.coordinates) continue;
          if (geom.type === "Polygon" && geom.coordinates[0]) {
            rasteriseLine(geom.coordinates[0]);
          } else if (geom.type === "MultiPolygon") {
            for (let k = 0; k < geom.coordinates.length; k++)
              if (geom.coordinates[k] && geom.coordinates[k][0]) rasteriseLine(geom.coordinates[k][0]);
          }
        }
      }

      let head = 0;

      while (head < queue.length) {
        let curr = queue[head++];
        let d = dist_grid[curr];

        if (d >= 18) continue;
        let r = Math.floor(curr/w);
        let c = curr % w;
        let nbrs = [
          (r > 0) ? curr - w : -1,
          (r + 1 < h) ? curr + w : -1,
          r*w + ((c + w - 1) % w),
          r*w + ((c + 1) % w)
        ];

        for (let k = 0; k < 4; k++) {
          let ni = nbrs[k];

          if (ni >= 0 && mask_grid[ni] === 1 && dist_grid[ni] > d + 1) {
            dist_grid[ni] = d + 1;
            queue.push(ni);
          }
        }
      }

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let d_px = dist_grid[gidx];

        if (d_px < 65535) {
          let lat = 90 - (Math.floor(gidx/w) + 0.5)*180/h;
          let km_per_px = 9.26*Math.max(0.25, Math.sqrt(Math.max(0.08, Math.cos(lat*Math.PI/180))));

          out[i] = Math.max(0.04, Math.exp(-(d_px*km_per_px)/13.5));
        }
      }

      //Return statement
      return out;
    }


    /**
     * Computes geographic bounding box of the domain mask in WGS84 degrees with a 2-degree margin.
     * @alias ViscountBiophysicalCovariates.computeMaskBBox
     *
     * @param {Object} arg0_mask_data
     *
     * @returns {Object}
     */
    static computeMaskBBox (arg0_mask_data) {
      //Convert from parameters
      let mask_data = arg0_mask_data;

      //Declare local instance variables
      let h = mask_data.grid_height;
      let max_lat = -90;
      let max_lon = -180;
      let min_lat = 90;
      let min_lon = 180;
      let v_idx = mask_data.valid_indices;
      let w = mask_data.grid_width;

      //Function body
      for (let i = 0; i < v_idx.length; i++) {
        let r = Math.floor(v_idx[i]/w);
        let c = v_idx[i] % w;
        let lat = 90 - (r + 0.5)*180/h;
        let lon = -180 + (c + 0.5)*360/w;

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
     * Fits 5-covariate constrained NNLS (`u_hab`, `u_hab*u_nat`, `u_eco`, `u_fluvial`, `u_coastal`) per horizon
     * and computes high-sharpness within-macro contrast weights paired with palaeoglacial & ice-cap envelopes.
     * @alias ViscountBiophysicalCovariates.computeResidualKrigingWeights
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
      let dom_obs = 0;
      let m_cell = new Float32Array(mask_data.valid_cell_count);
      let macro_rad = Math.max(4, Math.min(10, Math.round(0.60*meso_px)));
      let n_covs = 5;
      let n_obs = obs_bundle.obs_count;
      let n_valid = mask_data.valid_cell_count;
      let obs_list = obs_bundle.obs_list;
      let perm_ice = covs.perm_ice;
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
      let weights = new Float32Array(n_valid);
      let xtx = new Float64Array(25);
      let xty = new Float64Array(5);

      //Function body
      for (let k = 0; k < n_obs; k++)
        if (!obs_list[k].is_frontier_buffer) dom_obs++;

      for (let i = 0; i < n_valid; i++) {
        let a = cell_area[i]*perm_ice[i];
        let o = cell_obs[i];

        if (o < 0 || o >= n_obs || obs_list[o].is_frontier_buffer || a <= 0) continue;
        let uh = u_hab[i];
        let uh_soft = Math.max(0.12, uh);

        r_area[o] += a;
        r_covs[0][o] += a*uh;
        r_covs[1][o] += a*uh_soft*u_nat[i];
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
          let diag = xtx[r*n_covs + r];
          let rhs = xty[r];

          for (let c = 0; c < n_covs; c++)
            if (c !== r) rhs -= xtx[r*n_covs + c]*beta[c];
          beta[r] = (diag > 1e-12) ? Math.max(1e-4, rhs/diag) : 1e-4;
        }
      }

      let b_sum = Math.max(1e-8, beta[0] + beta[1] + beta[2] + beta[3] + beta[4]);
      let w0 = 0.40*(beta[0]/b_sum) + 0.14;
      let w1 = 0.40*(beta[1]/b_sum) + 0.14;
      let w2 = 0.40*(beta[2]/b_sum) + 0.07;
      let w3 = 0.40*(beta[3]/b_sum) + 0.20;
      let w4 = 0.40*(beta[4]/b_sum) + 0.05;
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let v_idx = mask_data.valid_indices;

      let ice_env_arr = new Float32Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let uh = u_hab[i];
        let uh_soft = Math.max(0.12, uh);
        let ice_env = perm_ice[i];

        if (apply_ice && rep_year <= -5500) {
          let gidx = v_idx[i];
          let lat = 90 - (Math.floor(gidx/grid_w) + 0.5)*180/grid_h;
          let lon = -180 + ((gidx % grid_w) + 0.5)*360/grid_w;
          let ice_fac = this.getLaurentideCordilleranIceFactor(lat, lon, rep_year);

          ice_env *= ice_fac;
        }
        ice_env_arr[i] = ice_env;

        let base_suit = w0*uh + w1*uh_soft*u_nat[i] + w2*u_eco[i] + w3*u_fluvial[i] + w4*u_coastal[i];

        //Keep m_macro ice-free so Greenland/ice margins do not blow up local ratio to the upper cap
        m_cell[i] = Math.max(1e-5, base_suit);
      }

      let m_macro = this.smoothPositiveFieldOnGrid(mask_data, m_cell, macro_rad);

      for (let i = 0; i < n_valid; i++) {
        let ratio = (m_macro[i] > 0) ? Math.max(0.18, Math.min(2.40, m_cell[i]/m_macro[i])) : 1.0;

        weights[i] = Math.max(1e-5, ice_env_arr[i]*Math.pow(ratio, 1.55));
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
     * @alias ViscountBiophysicalCovariates.getLaurentideCordilleranIceFactor
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

      //Function body (smooth western Cordilleran / Beringian ramp, southern Laurentide ramp & eastern shelf ramp)
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
     * @alias ViscountBiophysicalCovariates.loadUrbanMaskedHYDEPopcRaster
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

      //Guard clauses
      let ckey = `__hyde_rur_${year}`;

      if (cache && cache.has(ckey)) return cache.get(ckey);

      //Declare local instance variables
      let cov_paths = (config && config.kriging_config && config.kriging_config.covariate_paths) ?
        config.kriging_config.covariate_paths : {};
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let hyde_path = path.resolve(mask_data.project_root, cov_paths.hyde_popc_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters_scaled_to_global", `popc_${year}.png`);
      let n_valid = mask_data.valid_cell_count;
      let out = new Float32Array(n_valid);
      let total_px = grid_w*grid_h;
      let uopp_path = path.resolve(mask_data.project_root, cov_paths.hyde_uopp_raster || "histmap/2.data_cleaning/landuse_HYDE/rasters/uopp_2023AD.png");

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
     * Reads a 6-header-line Esri ASCII raster (.asc) into a flat Float32Array.
     * @alias ViscountBiophysicalCovariates.readAscGrid
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

      //Declare local instance variables
      let out_grid = new Float32Array(total_pixels);
      let tokens = fs.readFileSync(file_path, "utf8").trim().split(/\s+/);

      //Function body
      for (let i = 0; i < total_pixels && (12 + i) < tokens.length; i++)
        out_grid[i] = parseFloat(tokens[12 + i]);

      //Return statement
      return out_grid;
    }


    /**
     * Reads a full 4320x2160 big-endian float32 GeoPNG into a flat Float32Array.
     * @alias ViscountBiophysicalCovariates.readGlobalFloat32Raster
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
     * @alias ViscountBiophysicalCovariates.smoothPositiveFieldOnGrid
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
     * @alias ViscountBiophysicalCovariates.smoothValidFieldOnGrid
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
     * @alias ViscountBiophysicalCovariates.smoothWithinPartitionPositive
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
  module.exports = { ViscountBiophysicalCovariates: global.ViscountBiophysicalCovariates };
