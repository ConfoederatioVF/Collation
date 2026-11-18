//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");
let { ViscountRuralSuitability } = global.ViscountRuralSuitability ? global : require("./ViscountRuralSuitability.js");

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
      return ViscountRuralSuitability.computeCompositeHabitationField(arg0_mask_data, arg1_obs_bundle, arg2_covs, arg3_period_cfg, arg4_config, arg5_hab_cache);
    }


    static computeDeCliffedHabitationField (arg0_mask_data, arg1_obs_bundle, arg2_covs, arg3_year, arg4_config, arg5_hab_cache) {
      return ViscountRuralSuitability.computeDeCliffedHabitationField(arg0_mask_data, arg1_obs_bundle, arg2_covs, arg3_year, arg4_config, arg5_hab_cache);
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
      return ViscountRuralSuitability.computeResidualKrigingWeights(arg0_mask_data, arg1_obs_bundle, arg2_covs, arg3_u_hab, arg4_z_obs, arg5_meso_px, arg6_rep_year, arg7_config);
    }


    static getLaurentideCordilleranIceFactor (arg0_lat, arg1_lon, arg2_year) {
      return ViscountRuralSuitability.getLaurentideCordilleranIceFactor(arg0_lat, arg1_lon, arg2_year);
    }


    static loadUrbanMaskedHYDEPopcRaster (arg0_mask_data, arg1_year, arg2_cache, arg3_config) {
      return ViscountRuralSuitability.loadUrbanMaskedHYDEPopcRaster(arg0_mask_data, arg1_year, arg2_cache, arg3_config);
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
      return ViscountRuralSuitability.readGlobalFloat32Raster(arg0_file_path, arg1_total_pixels);
    }


    static smoothPositiveFieldOnGrid (arg0_mask_data, arg1_valid_field, arg2_radius_px) {
      return ViscountRuralSuitability.smoothPositiveFieldOnGrid(arg0_mask_data, arg1_valid_field, arg2_radius_px);
    }


    static smoothValidFieldOnGrid (arg0_mask_data, arg1_valid_field, arg2_radius_px) {
      return ViscountRuralSuitability.smoothValidFieldOnGrid(arg0_mask_data, arg1_valid_field, arg2_radius_px);
    }


    static smoothWithinPartitionPositive (arg0_mask_data, arg1_valid_field, arg2_part_id, arg3_part_sum, arg4_part_cnt, arg5_radius_px) {
      return ViscountRuralSuitability.smoothWithinPartitionPositive(arg0_mask_data, arg1_valid_field, arg2_part_id, arg3_part_sum, arg4_part_cnt, arg5_radius_px);
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountBiophysicalCovariates: global.ViscountBiophysicalCovariates };
