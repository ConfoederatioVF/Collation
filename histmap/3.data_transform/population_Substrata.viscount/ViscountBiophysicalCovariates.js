//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");
let { ViscountRuralSuitability } = global.ViscountRuralSuitability ? global : require("./ViscountRuralSuitability.js");
let { ViscountTerrainSuitability } = global.ViscountTerrainSuitability ? global : require("./ViscountTerrainSuitability.js");

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
     * permanent Greenland ice mask `perm_ice`, strict `hab_mask`, `dist_site_px`, and partition IDs `part_id`).
     * @alias ViscountBiophysicalCovariates.buildStaticCovariates
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_config
     * @param {Object} [arg2_obs_bundle]
     *
     * @returns {Object}
     */
    static buildStaticCovariates (arg0_mask_data, arg1_config, arg2_obs_bundle) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let config = arg1_config;
      let obs_bundle = arg2_obs_bundle;

      //Declare local instance variables
      let bbox = this.computeMaskBBox(mask_data);
      let cov_paths = (config && config.kriging_config && config.kriging_config.covariate_paths) ?
        config.kriging_config.covariate_paths : {};
      let doc_sites_json = cov_paths.documented_site_pixels_json ? path.resolve(mask_data.project_root, cov_paths.documented_site_pixels_json) : "";
      let forest_asc = cov_paths.forest_asc ? path.resolve(mask_data.project_root, cov_paths.forest_asc) : "";
      let forest_grid = (forest_asc && fs.existsSync(forest_asc)) ?
        this.readAscGrid(forest_asc, mask_data.grid_width*mask_data.grid_height) : null;
      let forest_valid = new Float32Array(mask_data.valid_cell_count);
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let hyde_hab_dens = new Float32Array(mask_data.valid_cell_count);
      let hyde_rur_1000;
      let hyde_rur_1500;
      let hyde_rur_1900;
      let lakes_path = cov_paths.lakes_geojson ? path.resolve(mask_data.project_root, cov_paths.lakes_geojson) : "";
      let maxln_asc = cov_paths.maxln_asc ? path.resolve(mask_data.project_root, cov_paths.maxln_asc) : "";
      let maxln_grid = (maxln_asc && fs.existsSync(maxln_asc)) ?
        this.readAscGrid(maxln_asc, grid_w*grid_h) : null;
      let maxln_valid = new Float32Array(mask_data.valid_cell_count);
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
      let sub_iso_valid = new Int32Array(n_valid);
      let temp_cache = new Map();
      let u_coastal;
      let u_eco = new Float32Array(n_valid);
      let u_fluvial;
      let u_nat = new Float32Array(n_valid);
      let uopp_path = path.resolve(
        mask_data.project_root || ".",
        cov_paths.hyde_uopp_raster || "histmap/2.data_cleaning/landuse_HYDE/rasters/uopp_2023AD.png"
      );
      let uopp_raw = this.readGlobalFloat32Raster(uopp_path, grid_w*grid_h);
      let uopp_valid = new Float32Array(n_valid);
      let valid_indices = mask_data.valid_indices;

      //Function body
      hyde_rur_1500 = this.loadUrbanMaskedHYDEPopcRaster(mask_data, 1500, temp_cache, config);
      hyde_rur_1000 = this.loadUrbanMaskedHYDEPopcRaster(mask_data, 1000, temp_cache, config);
      hyde_rur_1900 = this.loadUrbanMaskedHYDEPopcRaster(mask_data, 1900, temp_cache, config);

      //1. Partition IDs + forest indicator + agricultural suitability (maxln_cr.asc) + static HYDE habitability
      let f_raw = new Float32Array(n_valid);
      let mean_maxln = 0;
      let min_area = 0.75*mask_data.mean_cell_land_area_km2;
      let next_pid = 1;

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let f_val = (forest_grid && forest_grid[gidx] > 0) ? 1 : 0;
        let max_v = (maxln_grid && maxln_grid[gidx] > 0) ? maxln_grid[gidx] : 0;
        let iso_p = (sub_iso_grid) ? Math.round(sub_iso_grid[gidx]) : 0;
        let local_area = Math.max(min_area, mask_data.cell_land_area[i]);
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
        sub_iso_valid[i] = (iso_p > 0) ? iso_p : 0;
        f_raw[i] = f_val;
        forest_valid[i] = f_val;
        maxln_valid[i] = max_v;
        uopp_valid[i] = uopp_raw[gidx] || 0;
        hyde_hab_dens[i] = Math.max(
          hyde_rur_1500 ? hyde_rur_1500[i]/local_area : 0,
          hyde_rur_1000 ? hyde_rur_1000[i]/local_area : 0,
          hyde_rur_1900 ? 0.15*(hyde_rur_1900[i]/local_area) : 0
        );
        mean_maxln += Math.pow(max_v, 0.80);
      }
      mean_maxln = Math.max(1e-4, mean_maxln/Math.max(1, n_valid));

      let f_p1 = this.smoothValidFieldOnGrid(mask_data, f_raw, 2);
      let f_smooth = this.smoothValidFieldOnGrid(mask_data, f_p1, 2);

      let u_nat_raw = new Float32Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let max_v = (maxln_grid && maxln_grid[gidx] > 0) ? Math.pow(maxln_grid[gidx], 0.80)/mean_maxln : 0.35;
        let ff = Math.max(0, Math.min(1, f_smooth[i]));
        let ecotone = 4*ff*(1 - ff);

        u_nat_raw[i] = Math.max(0.03, Math.min(3.5, max_v));
        u_eco[i] = Math.max(0.05, 0.45*ecotone + 0.55*ff);
      }

      //Smooth single-pixel binary noise in Climber3 maxln suitability while preserving valley/ridge gradients
      let u_nat_sm = this.smoothValidFieldOnGrid(mask_data, u_nat_raw, 1);

      for (let i = 0; i < n_valid; i++)
        u_nat[i] = 0.45*u_nat_raw[i] + 0.55*u_nat_sm[i];

      //2. Load 5-arcminute terrain (elevation, Horn macro-slope, TRI) and compute crisp contour step-bands
      let terrain_raw = ViscountTerrainSuitability.A_loadTerrainArrays(mask_data, config);
      let terrain_bands = ViscountTerrainSuitability.B_computeTerrainStepBands(mask_data, terrain_raw, config);

      //3. Fluvial & coastal proximity tightened into crisp terrain-gated valley/coastal step bands
      let u_coastal_raw = this.computeCoastalProximityField(mask_data, bbox, lakes_path);
      let u_fluvial_raw = this.computeFluvialProximityField(mask_data, bbox, rivers_path, lakes_path);
      let tight_hydro = ViscountTerrainSuitability.C_tightenFluvialAndCoastalFields(
        mask_data,
        u_fluvial_raw,
        u_coastal_raw,
        terrain_bands
      );

      u_coastal = tight_hydro.u_coastal;
      u_fluvial = tight_hydro.u_fluvial;

      //4. Identify permanent Greenland interior ice sheet with sharp fjord decay & High-Arctic polar attenuation
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

            for (let dr = -4; dr <= 4; dr++) {
              let nr = r + dr;

              if (nr < 0 || nr >= grid_h) continue;
              for (let dc = -8; dc <= 8; dc++) {
                let nc = (c + dc + grid_w) % grid_w;

                if (la_grid[nr*grid_w + nc] <= 0) {
                  let dist_px = Math.sqrt(dr*dr + (dc*cos_lat)*(dc*cos_lat));

                  if (dist_px < min_d) min_d = dist_px;
                }
              }
            }
            let coast_env = (min_d > 2.1) ? 0.0 : Math.max(0.0, Math.min(1.0, Math.exp(-1.75*Math.max(0, min_d - 0.35))));
            let lat_att = (lat > 78.5 || (lat > 71.5 && lon > -30.0)) ? 0.02 : Math.max(0.04, Math.min(1.0, (75.0 - lat)/12.5));

            perm_ice[i] = coast_env*lat_att;
          }
        }
      }

      //5. Compute strict union habitability mask (Documented Stadestér Settlements Proximity + HYDE 3.5 Inhabited Areas)
      let raw_hyde_dir = path.resolve(mask_data.project_root || ".", cov_paths.hyde_raw_rasters_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters");
      let raw_1500 = this.readGlobalFloat32Raster(path.join(raw_hyde_dir, "popc_1500AD.png"), grid_w*grid_h);
      let raw_1000 = this.readGlobalFloat32Raster(path.join(raw_hyde_dir, "popc_1000AD.png"), grid_w*grid_h);
      let raw_1900 = this.readGlobalFloat32Raster(path.join(raw_hyde_dir, "popc_1900AD.png"), grid_w*grid_h);
      let raw_hyde_dens = new Float32Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let la_i = Math.max(1.0, mask_data.cell_land_area[i]);
        let mv = Math.max(raw_1500[gidx], raw_1000[gidx], 0.15*raw_1900[gidx]);

        raw_hyde_dens[i] = mv/la_i;
      }

      let hab_bundle = ViscountTerrainSuitability.D_buildUnionHabitabilityMask(
        mask_data,
        {
          elev_valid: terrain_raw.elev_valid,
          forest_valid: forest_valid,
          maxln_valid: maxln_valid,
          perm_ice: perm_ice,
          raw_hyde_dens: raw_hyde_dens,
          u_elev: terrain_bands.u_elev,
          u_terrain: terrain_bands.u_terrain,
          uopp_valid: uopp_valid
        },
        config,
        obs_bundle,
        this.computeBfsPixelDistance.bind(this)
      );

      //Return statement
      return {
        dist_catch_px: hab_bundle.dist_catch_px,
        dist_site_px: hab_bundle.dist_site_px,
        dist_stadester_px: hab_bundle.dist_stadester_px,
        elev_valid: terrain_raw.elev_valid,
        forest_valid: forest_valid,
        hab_mask: hab_bundle.hab_mask,
        hyde_hab_dens: hyde_hab_dens,
        hyde_rur_1900: hyde_rur_1900,
        maxln_valid: maxln_valid,
        part_id: part_id,
        partition_count: next_pid,
        perm_ice: perm_ice,
        raw_hyde_dens: raw_hyde_dens,
        slope_valid: terrain_raw.slope_valid,
        sub_iso_valid: sub_iso_valid,
        tri_valid: terrain_raw.tri_valid,
        u_coastal: u_coastal,
        u_eco: u_eco,
        u_elev: terrain_bands.u_elev,
        u_fluvial: u_fluvial,
        u_nat: u_nat,
        u_slope: terrain_bands.u_slope,
        u_terrain: terrain_bands.u_terrain,
        uopp_valid: uopp_valid
      };
    }


    /**
     * Computes exact metric-isotropic radial Euclidean pixel distance (`sqrt(dr^2 + (dc * cos(lat))^2)`)
     * from seed pixel indices on valid mask cells (eliminating 4-neighbour Manhattan/taxicab diamond artefacts).
     * @alias ViscountBiophysicalCovariates.computeBfsPixelDistance
     *
     * @param {Object} arg0_mask_data
     * @param {Array<number>} arg1_seed_indices
     * @param {number} [arg2_max_steps=8]
     *
     * @returns {Float32Array}
     */
    static computeBfsPixelDistance (arg0_mask_data, arg1_seed_indices, arg2_max_steps) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let seed_indices = Array.isArray(arg1_seed_indices) ? arg1_seed_indices : [];
      let max_steps = (arg2_max_steps !== undefined) ? arg2_max_steps : 8;

      //Guard clauses
      if (seed_indices.length === 0) return new Float32Array(mask_data.valid_cell_count).fill(99.0);

      //Declare local instance variables
      let h = mask_data.grid_height;
      let max_r = Math.ceil(max_steps);
      let max_steps2 = max_steps*max_steps;
      let n_valid = mask_data.valid_cell_count;
      let out = new Float32Array(n_valid).fill(99.0);
      let p2v = mask_data.pixel_to_valid_idx;
      let seen_seeds = new Set();
      let w = mask_data.grid_width;

      //Function body
      for (let i = 0; i < seed_indices.length; i++) {
        let idx = seed_indices[i];

        if (idx < 0 || idx >= w*h || seen_seeds.has(idx)) continue;
        seen_seeds.add(idx);
        let sr = Math.floor(idx/w);
        let sc = idx % w;
        let lat = 90 - (sr + 0.5)*180/h;
        let cos_lat = Math.max(0.18, Math.cos(lat*Math.PI/180));
        let cos_lat2 = cos_lat*cos_lat;
        let max_dc = Math.min(Math.ceil(max_steps*4), Math.ceil(max_steps/cos_lat));

        for (let dr = -max_r; dr <= max_r; dr++) {
          let nr = sr + dr;

          if (nr < 0 || nr >= h) continue;
          let dr2 = dr*dr;
          let row_off = nr*w;

          for (let dc = -max_dc; dc <= max_dc; dc++) {
            let d2 = dr2 + dc*dc*cos_lat2;

            if (d2 > max_steps2) continue;
            let nc = (sc + dc + w) % w;
            let nv = p2v[row_off + nc];

            if (nv < 0) continue;
            let d_rad = Math.sqrt(d2);

            if (d_rad < out[nv]) out[nv] = d_rad;
          }
        }
      }

      //Return statement
      return out;
    }


    /**
     * Computes per-catchment mean forest cover, Climber3 agricultural suitability (`maxln_cr`) and
     * modern `uopp_2023AD` urban core share for biome/aridity taphonomic & CRM salvage de-biasing.
     * @alias ViscountBiophysicalCovariates.computeCatchmentTaphonomyAndUrbanShares
     *
     * @param {Object} arg0_mask_data
     * @param {Array<Object>} arg1_obs_list
     * @param {Int32Array} arg2_cell_nearest
     * @param {Object} arg3_config
     *
     * @returns {Object}
     */
    static computeCatchmentTaphonomyAndUrbanShares (arg0_mask_data, arg1_obs_list, arg2_cell_nearest, arg3_config) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let obs_list = arg1_obs_list;
      let cell_nearest = arg2_cell_nearest;
      let config = (arg3_config) ? arg3_config : {};

      //Declare local instance variables
      let cov_paths = (config.kriging_config && config.kriging_config.covariate_paths) ?
        config.kriging_config.covariate_paths : {};
      let forest_asc = cov_paths.forest_asc ? path.resolve(mask_data.project_root, cov_paths.forest_asc) : "";
      let forest_grid = (forest_asc && fs.existsSync(forest_asc)) ?
        this.readAscGrid(forest_asc, mask_data.grid_width*mask_data.grid_height) : null;
      let maxln_asc = cov_paths.maxln_asc ? path.resolve(mask_data.project_root, cov_paths.maxln_asc) : "";
      let maxln_grid = (maxln_asc && fs.existsSync(maxln_asc)) ?
        this.readAscGrid(maxln_asc, mask_data.grid_width*mask_data.grid_height) : null;
      let n_obs = obs_list.length;
      let n_valid = mask_data.valid_cell_count;
      let o_area = new Float64Array(n_obs);
      let o_for = new Float64Array(n_obs);
      let o_max = new Float64Array(n_obs);
      let o_urb = new Float64Array(n_obs);
      let total_pixels = mask_data.grid_width*mask_data.grid_height;
      let uopp_path = path.resolve(
        mask_data.project_root || ".",
        cov_paths.hyde_uopp_raster || "histmap/2.data_cleaning/landuse_HYDE/rasters/uopp_2023AD.png"
      );
      let uopp_grid = fs.existsSync(uopp_path) ? this.readGlobalFloat32Raster(uopp_path, total_pixels) : null;
      let valid_indices = mask_data.valid_indices;

      //Function body
      for (let i = 0; i < n_valid; i++) {
        let o = cell_nearest[i];

        if (o < 0 || o >= n_obs) continue;
        let a = Math.max(1, mask_data.cell_land_area[i]);
        let gidx = valid_indices[i];

        o_area[o] += a;
        if (forest_grid && forest_grid[gidx] > 0) o_for[o] += a;
        if (maxln_grid && maxln_grid[gidx] > 0) o_max[o] += a*maxln_grid[gidx];
        if (uopp_grid && uopp_grid[gidx] > 10.0) o_urb[o] += a;
      }

      for (let i = 0; i < n_obs; i++) {
        let denom = Math.max(1, o_area[i]);

        obs_list[i].mean_forest = o_for[i]/denom;
        obs_list[i].mean_maxln = o_max[i]/denom;
        obs_list[i].urb_core_share = o_urb[i]/denom;
      }

      //Return statement
      return { loaded_forest: Boolean(forest_grid), loaded_maxln: Boolean(maxln_grid), loaded_uopp: Boolean(uopp_grid) };
    }


    /**
     * Computes marine & large inland-sea coastal proximity `exp(-d_km / 22.0)` across valid mask cells
     * via 8-neighbour Euclidean chamfer BFS (eliminating 4-neighbour diamond ridges).
     * @alias ViscountBiophysicalCovariates.computeCoastalProximityField
     *
     * @param {Object} arg0_mask_data
     * @param {Object} [arg1_bbox]
     * @param {string} [arg2_lakes_path]
     *
     * @returns {Float32Array}
     */
    static computeCoastalProximityField (arg0_mask_data, arg1_bbox, arg2_lakes_path) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let bbox = arg1_bbox;
      let lakes_path = arg2_lakes_path;

      //Declare local instance variables
      let dist_grid = new Uint16Array(mask_data.grid_width*mask_data.grid_height).fill(65535);
      let h = mask_data.grid_height;
      let la_grid = mask_data.land_area_grid;
      let mask_grid = mask_data.mask_grid;
      let n_valid = mask_data.valid_cell_count;
      let nbr_offsets = [
        [-1, 0, 10], [1, 0, 10], [0, -1, 10], [0, 1, 10],
        [-1, -1, 14], [-1, 1, 14], [1, -1, 14], [1, 1, 14]
      ];
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

      //Seed major inland lakes (e.g. Great Lakes, Great Bear/Slave, Winnipeg, Okeechobee) without linear seams
      if (lakes_path && fs.existsSync(lakes_path)) {
        let lj = JSON.parse(fs.readFileSync(lakes_path, "utf8"));
        let feats = Array.isArray(lj.features) ? lj.features : [];
        let markLakeRing = (arg0_coords) => {
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
              let lon = x0 + t*(x1 - x0);
              let lat = y0 + t*(y1 - y0);

              if (bbox && (lon < bbox.min_lon || lon > bbox.max_lon || lat < bbox.min_lat || lat > bbox.max_lat)) continue;
              let c = Math.max(0, Math.min(w - 1, Math.floor((lon + 180)*w/360)));
              let r = Math.max(0, Math.min(h - 1, Math.floor((90 - lat)*h/180)));
              let lidx = r*w + c;

              if (mask_grid[lidx] === 1 && dist_grid[lidx] > 0) {
                dist_grid[lidx] = 0;
                queue.push(lidx);
              }
            }
          }
        };

        for (let i = 0; i < feats.length; i++) {
          let geom = feats[i].geometry;

          if (!geom || !geom.coordinates) continue;
          let ring = (geom.type === "Polygon") ? geom.coordinates[0] :
            ((geom.type === "MultiPolygon" && geom.coordinates[0]) ? geom.coordinates[0][0] : null);

          if (!ring || ring.length < 3) continue;
          let max_x = -180;
          let max_y = -90;
          let min_x = 180;
          let min_y = 90;

          for (let k = 0; k < ring.length; k++) {
            let rx = Number(ring[k][0]);
            let ry = Number(ring[k][1]);

            if (rx < min_x) min_x = rx;
            if (rx > max_x) max_x = rx;
            if (ry < min_y) min_y = ry;
            if (ry > max_y) max_y = ry;
          }
          if ((max_x - min_x) < 1.2 && (max_y - min_y) < 1.2) continue;
          if (geom.type === "Polygon" && geom.coordinates[0]) {
            markLakeRing(geom.coordinates[0]);
          } else if (geom.type === "MultiPolygon") {
            for (let k = 0; k < geom.coordinates.length; k++)
              if (geom.coordinates[k] && geom.coordinates[k][0]) markLakeRing(geom.coordinates[k][0]);
          }
        }
      }

      let dist_km_valid = this.computeBfsPixelDistance(mask_data, queue, 15.0);

      for (let i = 0; i < n_valid; i++) {
        let d_px = dist_km_valid[i];

        if (d_px < 90.0)
          out[i] = Math.exp(-(d_px*9.26)/22.0);
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

      let dist_fluv_px = this.computeBfsPixelDistance(mask_data, queue, 20.0);

      for (let i = 0; i < n_valid; i++) {
        let d_px = dist_fluv_px[i];

        if (d_px < 90.0)
          out[i] = 0.25 + 0.75*Math.exp(-(d_px*9.26)/26.0);
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


    static getModernUrbanMask (arg0_mask_data, arg1_config, arg2_cache) {
      return ViscountRuralSuitability.getModernUrbanMask(arg0_mask_data, arg1_config, arg2_cache);
    }


    static inpaintUrbanMaskGrid (arg0_popc_grid, arg1_urban_mask, arg2_land_area_grid, arg3_fallback_grid, arg4_grid_width, arg5_grid_height, arg6_inpaint_radius, arg7_target_indices) {
      return ViscountRuralSuitability.inpaintUrbanMaskGrid(arg0_popc_grid, arg1_urban_mask, arg2_land_area_grid, arg3_fallback_grid, arg4_grid_width, arg5_grid_height, arg6_inpaint_radius, arg7_target_indices);
    }


    static loadUrbanMaskedHYDEPopcRaster (arg0_mask_data, arg1_year, arg2_cache, arg3_config) {
      return ViscountRuralSuitability.loadUrbanMaskedHYDEPopcRaster(arg0_mask_data, arg1_year, arg2_cache, arg3_config);
    }


    /**
     * Reads a 6-header-line Esri ASCII raster (.asc) into a flat Float32Array using native C++ AVX2
     * parsing (32 ms vs 5.500 ms JS split) with an mtime-keyed cache and zero-alloc JS byte-scanner fallback.
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
      let cache = (global._cached_viscount_asc_grids) ? global._cached_viscount_asc_grids : (global._cached_viscount_asc_grids = new Map());
      let resolved_path = path.resolve(file_path);
      let stat_mtime = 0;

      //Guard clause: serve from mtime-validated global cache (0 ms on repeated Viscount covariate loads)
      try {
        stat_mtime = fs.statSync(resolved_path).mtimeMs;
        let hit = cache.get(resolved_path);
        if (hit && hit.mtime === stat_mtime && hit.grid.length === total_pixels)
          return hit.grid;
      } catch (e) {}

      //Function body: 1. Native C++20 byte scanner (~32 ms)
      let out_grid = null;
      let raw_buf = fs.readFileSync(resolved_path);

      if (global.GeoPNG && GeoPNG.native && GeoPNG.native.isAvailable()) {
        out_grid = GeoPNG.native.parseAscGrid(raw_buf, total_pixels);
      }

      //2. Zero-alloc JS byte-scanner fallback (~142 ms vs 5.500 ms .split(/\s+/))
      if (!out_grid) {
        out_grid = new Float32Array(total_pixels);
        let len = raw_buf.length;
        let out_idx = 0;
        let pos = 0;
        let tok_count = 0;

        while (pos < len && out_idx < total_pixels) {
          while (pos < len && raw_buf[pos] <= 32) pos++;
          if (pos >= len) break;
          if (tok_count < 12) {
            while (pos < len && raw_buf[pos] > 32) pos++;
            tok_count++;
            continue;
          }
          let neg = false;
          if (raw_buf[pos] === 45) { neg = true; pos++; }
          else if (raw_buf[pos] === 43) { pos++; }

          let val = 0;
          while (pos < len && raw_buf[pos] >= 48 && raw_buf[pos] <= 57) {
            val = val*10 + (raw_buf[pos] - 48);
            pos++;
          }
          if (pos < len && raw_buf[pos] === 46) {
            pos++;
            let scale = 0.1;
            while (pos < len && raw_buf[pos] >= 48 && raw_buf[pos] <= 57) {
              val += (raw_buf[pos] - 48)*scale;
              scale *= 0.1;
              pos++;
            }
          }
          if (pos < len && (raw_buf[pos] === 101 || raw_buf[pos] === 69)) {
            pos++;
            let eneg = false;
            if (pos < len && raw_buf[pos] === 45) { eneg = true; pos++; }
            else if (pos < len && raw_buf[pos] === 43) { pos++; }
            let exp_v = 0;
            while (pos < len && raw_buf[pos] >= 48 && raw_buf[pos] <= 57) {
              exp_v = exp_v*10 + (raw_buf[pos] - 48);
              pos++;
            }
            val *= Math.pow(10, eneg ? -exp_v : exp_v);
          }
          while (pos < len && raw_buf[pos] > 32) pos++;
          out_grid[out_idx++] = neg ? -val : val;
        }
      }

      if (stat_mtime > 0) {
        if (cache.size >= 8) cache.delete(cache.keys().next().value);
        cache.set(resolved_path, { grid: out_grid, mtime: stat_mtime });
      }

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
