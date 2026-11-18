//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * 5-arcminute (`4320x2160`) Extended Urban Buffer Mask, Modern/Ancient HYDE Urban Footprint Union,
   * Reservoir Zero-Hole Detector, Outlier Spike Filter and 3-Tier Boundary IDW Inpainter for Operation Viscount.
   *
   * @class ViscountUrbanMask
   */
  global.ViscountUrbanMask = class {
    /**
     * Builds or retrieves the cached extended modern urban buffer mask combining HYDE `uopp_2023AD.png`,
     * GHSL `GHSL_2020.png` (`>= 50k` inhabitants), Moore buffer dilation (default radius `2`), and 1-pass
     * contiguous suburban-sprawl fringe absorption (`uopp > 2,0 km2`).
     * @alias ViscountUrbanMask.getModernUrbanMask
     *
     * @param {Object} arg0_mask_data
     * @param {Object} [arg1_config]
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
      if (!mask_data) return new Uint8Array(0);
      if (cache && cache.has("__modern_urban_mask__")) return cache.get("__modern_urban_mask__");

      //Declare local instance variables
      let cov_paths = (config.kriging_config && config.kriging_config.covariate_paths) ?
        config.kriging_config.covariate_paths : {};
      let buffer_radius = (cov_paths.urban_mask_buffer_radius !== undefined) ?
        Number(cov_paths.urban_mask_buffer_radius) : 2;
      let dilated_mask;
      let extended_mask;
      let fringe_threshold = (cov_paths.urban_fringe_uopp_threshold !== undefined) ?
        Number(cov_paths.urban_fringe_uopp_threshold) : 2.0;
      let ghsl_2020_path;
      let ghsl_pop_threshold = (cov_paths.ghsl_urban_pop_threshold !== undefined) ?
        Number(cov_paths.ghsl_urban_pop_threshold) : 50000;
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let root = mask_data.project_root || ".";
      let total_pixels = grid_w*grid_h;
      let raw_mask = new Uint8Array(total_pixels);
      let uopp_grid;
      let uopp_path = path.resolve(
        root,
        cov_paths.hyde_uopp_raster || "histmap/2.data_cleaning/landuse_HYDE/rasters/uopp_2023AD.png"
      );
      let uopp_threshold = (cov_paths.urban_uopp_threshold !== undefined) ?
        Number(cov_paths.urban_uopp_threshold) : 10.0;

      //Function body
      uopp_grid = this.readGlobalFloat32Raster(uopp_path, total_pixels);
      for (let i = 0; i < total_pixels; i++)
        if (uopp_grid[i] > uopp_threshold)
          raw_mask[i] = 1;

      if (cov_paths.disable_ghsl_urban_union !== true) {
        ghsl_2020_path = path.resolve(
          root,
          cov_paths.ghsl_urban_2020_raster || "histmap/1.data_raw/population_GHSL/urban_rasters/GHSL_2020.png"
        );
        if (fs.existsSync(ghsl_2020_path)) {
          let ghsl_grid = this.readGlobalUint32Raster(ghsl_2020_path, total_pixels);

          for (let i = 0; i < total_pixels; i++)
            if (ghsl_grid[i] >= ghsl_pop_threshold)
              raw_mask[i] = 1;
        }
      }

      if (buffer_radius > 0) {
        let r_lim = (buffer_radius + 0.35)*(buffer_radius + 0.35);

        dilated_mask = new Uint8Array(total_pixels);
        for (let i = 0; i < grid_h; i++) {
          let lat = 90 - (i + 0.5)*180/grid_h;
          let cos_lat = Math.max(0.20, Math.cos(lat*Math.PI/180));
          let max_dz = Math.min(buffer_radius*3, Math.ceil((buffer_radius + 0.35)/cos_lat));

          for (let x = 0; x < grid_w; x++)
            if (raw_mask[i*grid_w + x] === 1)
              for (let y = -buffer_radius; y <= buffer_radius; y++) {
                let local_ny = i + y;

                if (local_ny >= 0 && local_ny < grid_h)
                  for (let z = -max_dz; z <= max_dz; z++) {
                    let dz_km = z*cos_lat;

                    if (y*y + dz_km*dz_km > r_lim) continue;
                    let local_nx = (x + z + grid_w) % grid_w;

                    dilated_mask[local_ny*grid_w + local_nx] = 1;
                  }
              }
        }
      } else {
        dilated_mask = raw_mask;
      }

      extended_mask = new Uint8Array(dilated_mask);
      if (fringe_threshold > 0) {
        for (let i = 0; i < grid_h; i++)
          for (let x = 0; x < grid_w; x++) {
            let local_idx = i*grid_w + x;

            if (dilated_mask[local_idx] === 1 || uopp_grid[local_idx] <= fringe_threshold) continue;
            let touches_buffer = false;

            for (let y = -1; y <= 1 && !touches_buffer; y++) {
              let local_ny = i + y;

              if (local_ny >= 0 && local_ny < grid_h)
                for (let z = -1; z <= 1; z++) {
                  if (y === 0 && z === 0) continue;
                  let local_nx = (x + z + grid_w) % grid_w;

                  if (dilated_mask[local_ny*grid_w + local_nx] === 1) {
                    touches_buffer = true;
                    break;
                  }
                }
            }
            if (touches_buffer) extended_mask[local_idx] = 1;
          }
      }

      if (cache) cache.set("__modern_urban_mask__", extended_mask);

      //Return statement
      return extended_mask;
    }


    /**
     * Inpaints masked urban/spike/reservoir pixels from surrounding unmasked rural land via 3-tier IDW (`r`, `2r`, `4r`)
     * with optional `KK10LUH2` deep-core fallback.
     * @alias ViscountUrbanMask.inpaintUrbanMaskGrid
     *
     * @param {Float32Array} arg0_popc_grid
     * @param {Uint8Array} arg1_urban_mask
     * @param {Float32Array} arg2_land_area_grid
     * @param {Float32Array|null} arg3_fallback_grid
     * @param {number} arg4_grid_width
     * @param {number} arg5_grid_height
     * @param {number} [arg6_inpaint_radius=4]
     * @param {Int32Array} [arg7_target_indices]
     *
     * @returns {Float32Array}
     */
    static inpaintUrbanMaskGrid (
      arg0_popc_grid,
      arg1_urban_mask,
      arg2_land_area_grid,
      arg3_fallback_grid,
      arg4_grid_width,
      arg5_grid_height,
      arg6_inpaint_radius,
      arg7_target_indices,
      arg8_sub_iso_grid
    ) {
      //Convert from parameters
      let popc_grid = arg0_popc_grid;
      let urban_mask = arg1_urban_mask;
      let land_area_grid = arg2_land_area_grid;
      let fallback_grid = arg3_fallback_grid;
      let grid_w = arg4_grid_width;
      let grid_h = arg5_grid_height;
      let radius = (arg6_inpaint_radius !== undefined) ? arg6_inpaint_radius : 4;
      let target_indices = arg7_target_indices;
      let sub_iso_grid = arg8_sub_iso_grid;

      //Declare local instance variables
      let max_radius = radius*6;
      let n_targets = (target_indices) ? target_indices.length : grid_w*grid_h;
      let out_grid = new Float32Array(popc_grid);
      let radii = [radius, radius*2, radius*4, max_radius];

      //Function body
      for (let i = 0; i < n_targets; i++) {
        let local_idx = (target_indices) ? target_indices[i] : i;

        if (urban_mask[local_idx] < 1) continue;
        if (land_area_grid[local_idx] <= 0) {
          out_grid[local_idx] = 0;
          continue;
        }

        let any_val_sum = 0;
        let any_w_sum = 0;
        let local_cx = local_idx % grid_w;
        let local_cy = Math.floor(local_idx/grid_w);
        let local_lat = 90 - (local_cy + 0.5)*180/grid_h;
        let local_cos = Math.max(0.20, Math.cos(local_lat*Math.PI/180));
        let local_pos_only = (urban_mask[local_idx] === 2);
        let same_val_sum = 0;
        let same_w_sum = 0;
        let target_iso = (sub_iso_grid && sub_iso_grid[local_idx] > 0) ? sub_iso_grid[local_idx] : 0;

        for (let r_step = 0; r_step < radii.length && same_w_sum <= 0 && any_w_sum <= 0; r_step++) {
          let local_r = radii[r_step];
          let max_dy = Math.min(local_r*2, Math.ceil((local_r + 0.35)/local_cos));
          let r_lim = (local_r + 0.35)*(local_r + 0.35);

          any_val_sum = 0;
          any_w_sum = 0;
          same_val_sum = 0;
          same_w_sum = 0;
          for (let x = -local_r; x <= local_r; x++) {
            let local_ny = local_cy + x;

            if (local_ny >= 0 && local_ny < grid_h)
              for (let y = -max_dy; y <= max_dy; y++) {
                if (x === 0 && y === 0) continue;
                let dy_eff = y*local_cos;
                let d2 = x*x + dy_eff*dy_eff;

                if (d2 > r_lim) continue;
                let local_nx = (local_cx + y + grid_w) % grid_w;
                let local_nidx = local_ny*grid_w + local_nx;

                if (
                  urban_mask[local_nidx] === 0 &&
                  land_area_grid[local_nidx] > 0 &&
                  (!local_pos_only || popc_grid[local_nidx] > 0)
                ) {
                  let local_w = 1/Math.pow(1 + d2, 1.25);

                  any_val_sum += popc_grid[local_nidx]*local_w;
                  any_w_sum += local_w;
                  if (target_iso > 0 && sub_iso_grid[local_nidx] === target_iso) {
                    same_val_sum += popc_grid[local_nidx]*local_w;
                    same_w_sum += local_w;
                  }
                }
              }
          }
        }

        if (same_w_sum > 0)
          out_grid[local_idx] = same_val_sum/same_w_sum;
        else if (any_w_sum > 0)
          out_grid[local_idx] = any_val_sum/any_w_sum;
        else if (popc_grid[local_idx] > 0 && fallback_grid && fallback_grid[local_idx] > 0)
          out_grid[local_idx] = fallback_grid[local_idx];
        else
          out_grid[local_idx] = 0;
      }

      //Return statement
      return out_grid;
    }


    /**
     * Loads a benchmark year's HYDE `popc` raster across valid domain cells after masking & IDW-inpainting
     * extended modern urban buffers, historical `urbc` pixels, `8x` Moore spikes and settled reservoir zero-holes.
     * @alias ViscountUrbanMask.loadUrbanMaskedHYDEPopcRaster
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

      //Declare local instance variables
      let cache_key = `hyde_urban_masked_${year}`;
      let cov_paths = (config.kriging_config && config.kriging_config.covariate_paths) ?
        config.kriging_config.covariate_paths : {};
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let inpaint_radius = (cov_paths.urban_mask_inpaint_radius !== undefined) ?
        cov_paths.urban_mask_inpaint_radius : 4;
      let kk10_grid = null;
      let kk10_path;
      let land_area_grid = mask_data.land_area_grid;
      let modern_urban_mask;
      let n_valid = mask_data.valid_cell_count;
      let out_arr = new Float32Array(n_valid);
      let popc_grid;
      let popc_path;
      let root = mask_data.project_root || ".";
      let spike_ratio = (cov_paths.urban_outlier_spike_ratio !== undefined) ?
        cov_paths.urban_outlier_spike_ratio : 8.0;
      let total_pixels = grid_w*grid_h;
      let urbc_path;
      let valid_indices = mask_data.valid_indices;
      let year_label = (year < 0) ? `${Math.abs(year)}BC` : `${year}AD`;
      let year_urban_mask;

      //Guard clauses
      if (cache && cache.has(cache_key)) return cache.get(cache_key);

      //Function body
      popc_path = path.resolve(
        root,
        cov_paths.hyde_popc_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters_scaled_to_global",
        `popc_${year}.png`
      );
      if (!fs.existsSync(popc_path))
        popc_path = path.resolve(
          root,
          cov_paths.hyde_raw_rasters_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters",
          `popc_${year_label}.png`
        );
      if (!fs.existsSync(popc_path)) return out_arr;

      if (!land_area_grid) {
        land_area_grid = new Float32Array(total_pixels);
        for (let i = 0; i < n_valid; i++) land_area_grid[valid_indices[i]] = 1.0;
      }

      popc_grid = this.readGlobalFloat32Raster(popc_path, total_pixels);
      modern_urban_mask = this.getModernUrbanMask(mask_data, config, cache);
      year_urban_mask = new Uint8Array(modern_urban_mask);

      urbc_path = path.resolve(
        root,
        cov_paths.hyde_mcevedy_rasters_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters_mcevedy",
        `urbc_${year}.png`
      );
      if (!fs.existsSync(urbc_path))
        urbc_path = path.resolve(
          root,
          cov_paths.hyde_raw_rasters_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters",
          `urbc_${year_label}.png`
        );

      if (fs.existsSync(urbc_path)) {
        let urbc_grid = this.readGlobalFloat32Raster(urbc_path, total_pixels);

        for (let i = 0; i < total_pixels; i++)
          if (urbc_grid[i] > 0) year_urban_mask[i] = 1;
      }

      for (let i = 0; i < n_valid; i++) {
        let local_gidx = valid_indices[i];

        if (land_area_grid[local_gidx] > 0 && popc_grid[local_gidx] <= 0) {
          let local_cx = local_gidx % grid_w;
          let local_cy = Math.floor(local_gidx/grid_w);
          let local_land_cnt = 0;
          let local_pos_area = 0;
          let local_pos_cnt = 0;
          let local_pos_sum = 0;

          for (let x = -4; x <= 4; x++) {
            let local_ny = local_cy + x;

            if (local_ny >= 0 && local_ny < grid_h)
              for (let y = -4; y <= 4; y++) {
                if (x === 0 && y === 0) continue;
                let local_nx = (local_cx + y + grid_w) % grid_w;
                let local_nidx = local_ny*grid_w + local_nx;

                if (land_area_grid[local_nidx] > 0) {
                  local_land_cnt++;
                  if (popc_grid[local_nidx] > 0) {
                    local_pos_cnt++;
                    local_pos_sum += popc_grid[local_nidx];
                    local_pos_area += land_area_grid[local_nidx];
                  }
                }
              }
          }
          if (local_land_cnt > 0 && (local_pos_cnt/local_land_cnt) >= 0.55 && (local_pos_sum/Math.max(1, local_pos_area)) >= 0.12)
            year_urban_mask[local_gidx] = 2;
          continue;
        }
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

      kk10_path = path.resolve(
        root,
        cov_paths.kk10_fallback_folder || "histmap/2.data_cleaning/population_KK10LUH2/rasters_KK10LUH2_2._global_scaling",
        `popc_${year}.png`
      );
      if (fs.existsSync(kk10_path)) kk10_grid = this.readGlobalFloat32Raster(kk10_path, total_pixels);

      let sub_iso_path = path.resolve(
        root,
        cov_paths.sub_iso_asc || "histmap/1.data_raw/metadata_HYDE/general_files/sub_iso_cr.asc"
      );
      let sub_iso_grid = this.readGlobalSubIsoGrid(sub_iso_path, total_pixels);
      let cleaned_grid = this.inpaintUrbanMaskGrid(
        popc_grid,
        year_urban_mask,
        land_area_grid,
        kk10_grid,
        grid_w,
        grid_h,
        inpaint_radius,
        valid_indices,
        sub_iso_grid
      );

      for (let i = 0; i < n_valid; i++) {
        let local_val = cleaned_grid[valid_indices[i]];

        if (Number.isFinite(local_val) && local_val > 0) out_arr[i] = local_val;
      }

      if (cache) cache.set(cache_key, out_arr);

      //Return statement
      return out_arr;
    }


    /**
     * Reads a full global big-endian float32 GeoPNG into a flat Float32Array.
     * @alias ViscountUrbanMask.readGlobalFloat32Raster
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
      if (!file_path || !fs.existsSync(file_path)) return new Float32Array(total_pixels);

      //Declare local instance variables
      let png_data = PNG.sync.read(fs.readFileSync(file_path)).data;
      let data_view = new DataView(png_data.buffer, png_data.byteOffset, png_data.byteLength);
      let out_grid = new Float32Array(total_pixels);

      //Function body
      for (let i = 0; i < total_pixels; i++) {
        let px = i*4;

        if ((png_data[px] | png_data[px + 1] | png_data[px + 2] | png_data[px + 3]) === 0) continue;
        let v = data_view.getFloat32(px, false);

        if (Number.isFinite(v) && v > 0) out_grid[i] = v;
      }

      //Return statement
      return out_grid;
    }


    /**
     * Reads and caches `sub_iso_cr.asc` subnational ISO integer codes into an `Int32Array`.
     * @alias ViscountUrbanMask.readGlobalSubIsoGrid
     *
     * @param {string} arg0_file_path
     * @param {number} arg1_total_pixels
     *
     * @returns {Int32Array|null}
     */
    static readGlobalSubIsoGrid (arg0_file_path, arg1_total_pixels) {
      //Convert from parameters
      let file_path = arg0_file_path;
      let total_pixels = arg1_total_pixels;

      //Guard clauses
      if (!file_path || !fs.existsSync(file_path)) return null;
      if (!this._sub_iso_cache) this._sub_iso_cache = new Map();
      if (this._sub_iso_cache.has(file_path)) return this._sub_iso_cache.get(file_path);

      //Declare local instance variables
      let out_grid = new Int32Array(total_pixels);
      let tokens = fs.readFileSync(file_path, "utf8").trim().split(/\s+/);

      //Function body
      for (let i = 0; i < total_pixels && (12 + i) < tokens.length; i++) {
        let v = Math.round(parseFloat(tokens[12 + i]));

        out_grid[i] = Number.isFinite(v) && v > 0 ? v : 0;
      }
      this._sub_iso_cache.set(file_path, out_grid);

      //Return statement
      return out_grid;
    }


    /**
     * Reads a full global big-endian unsigned 32-bit integer GeoPNG (e.g. `GHSL_2020.png`) into a Float32Array.
     * @alias ViscountUrbanMask.readGlobalUint32Raster
     *
     * @param {string} arg0_file_path
     * @param {number} arg1_total_pixels
     *
     * @returns {Float32Array}
     */
    static readGlobalUint32Raster (arg0_file_path, arg1_total_pixels) {
      //Convert from parameters
      let file_path = arg0_file_path;
      let total_pixels = arg1_total_pixels;

      //Guard clauses
      if (!file_path || !fs.existsSync(file_path)) return new Float32Array(total_pixels);

      //Declare local instance variables
      let png_data = PNG.sync.read(fs.readFileSync(file_path)).data;
      let out_grid = new Float32Array(total_pixels);

      //Function body
      for (let i = 0; i < total_pixels; i++) {
        let px = i*4;

        if ((png_data[px] | png_data[px + 1] | png_data[px + 2] | png_data[px + 3]) === 0) continue;
        out_grid[i] = ((png_data[px] << 24) | (png_data[px + 1] << 16) | (png_data[px + 2] << 8) | png_data[px + 3]) >>> 0;
      }

      //Return statement
      return out_grid;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountUrbanMask: global.ViscountUrbanMask };
