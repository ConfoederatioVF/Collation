//Initialise functions
{
  if (!global.population_Stadester_rasters) global.population_Stadester_rasters = {};
  if (!global.population_Stadester_config && typeof require !== "undefined")
    try { require(path.join(__dirname, "config", "stadester_config.js")); } catch (e) {}
  if (!global.StadesterPartitionIO && typeof require !== "undefined")
    try { require(path.join(__dirname, "StadesterPartitionIO.js")); } catch (e) {}
  
  /**
   * Builds the joined valid land mask combining HYDE land area (`y_offset = 0`), cleaned 2020+ GHS-POP inhabited pixels (`y_offset = 0`),
   * and pre-2020/JRC GHS-POP island pixels omitted by HYDE (`y_offset = -1`).
   * @alias population_Stadester_rasters.buildJoinedValidLandMask
   * 
   * @param {Object} [arg0_options]
   *  @param {boolean} [arg0_options.force_rebuild=false]
   *  @param {string} [arg0_options.ghs_pop_cleaned_folder]
   *  @param {string} [arg0_options.ghs_pop_raw_fallback_folder]
   *  @param {number} [arg0_options.height=2160]
   *  @param {string} [arg0_options.hyde_land_path]
   *  @param {number} [arg0_options.width=4320]
   * 
   * @returns {Uint8Array} Binary valid land mask (`1` = land/inhabited, `0` = water)
   */
  population_Stadester_rasters.buildJoinedValidLandMask = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};
    
    //Declare local instance variables
    let cfg = global.population_Stadester_config;
    let cleaned_folder = options.ghs_pop_cleaned_folder || (cfg && cfg.ghs_pop_cleaned_folder) ||
      path.join((typeof h2 !== "undefined") ? h2 : "./histmap/2.data_cleaning", "population_GHSL", "cleaned_rasters");
    let force_rebuild = Boolean(options.force_rebuild);
    let height = options.height || 2160;
    let hyde_land_path = options.hyde_land_path || path.join(
      (typeof h1 !== "undefined") ? h1 : "./histmap/1.data_raw",
      "metadata_HYDE",
      "general_rasters",
      "land_area.png"
    );
    let hyde_mask;
    let joined_mask;
    let jrc_years = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025];
    let pngjs_lib = (typeof pngjs !== "undefined") ? pngjs : (global.pngjs || require("pngjs"));
    let raw_fallback_folder = options.ghs_pop_raw_fallback_folder || (cfg && cfg.ghs_pop_raw_fallback_folder) ||
      path.join((typeof h1 !== "undefined") ? h1 : "./histmap/1.data_raw", "population_GHSL", "population_rasters", "2.rasters");
    let raw_y_offset = (cfg && cfg.raw_fallback_y_offset !== undefined) ? cfg.raw_fallback_y_offset : -1;
    let total_px = 0;
    let width = options.width || 4320;
    
    //Guard clauses
    if (!force_rebuild && population_Stadester_rasters._cached_joined_land_mask)
      return population_Stadester_rasters._cached_joined_land_mask;
    
    //Function body
    total_px = width*height;
    hyde_mask = new Uint8Array(total_px);
    joined_mask = new Uint8Array(total_px);
    
    //1. HYDE land_area (uint32 big-endian > 0, y_offset = 0)
    if (fs.existsSync(hyde_land_path)) {
      let hyde_png = pngjs_lib.PNG.sync.read(fs.readFileSync(hyde_land_path));
      let hyde_dv = new DataView(hyde_png.data.buffer, hyde_png.data.byteOffset, hyde_png.data.byteLength);
      for (let i = 0; i < total_px; i++) {
        if (hyde_dv.getUint32(i*4, false) > 0) {
          hyde_mask[i] = 1;
          joined_mask[i] = 1;
        }
      }
    }
    
    //2. Cleaned 2020..2025 GHS-POP inhabited pixels (float32 big-endian > 0, y_offset = 0)
    for (let i = 2020; i <= 2025; i++) {
      let cleaned_path = path.join(cleaned_folder, `GHS_POP_${i}.png`);
      if (!fs.existsSync(cleaned_path)) continue;
      let pop_png = pngjs_lib.PNG.sync.read(fs.readFileSync(cleaned_path));
      let pop_dv = new DataView(pop_png.data.buffer, pop_png.data.byteOffset, pop_png.data.byteLength);
      for (let x = 0; x < total_px; x++) {
        let val = pop_dv.getFloat32(x*4, false);
        if (Number.isFinite(val) && val > 0)
          joined_mask[x] = 1;
      }
    }
    
    //3. JRC / pre-2020 GHS-POP island & coastal pixels omitted by HYDE (float32 big-endian > 0, raw_fallback_y_offset = -1)
    for (let i = 0; i < jrc_years.length; i++) {
      let raw_path = path.join(raw_fallback_folder, `GHS_POP_${jrc_years[i]}.png`);
      if (!fs.existsSync(raw_path)) continue;
      let jrc_png = pngjs_lib.PNG.sync.read(fs.readFileSync(raw_path));
      let jrc_dv = new DataView(jrc_png.data.buffer, jrc_png.data.byteOffset, jrc_png.data.byteLength);
      for (let y = 0; y < height; y++) {
        let sy = Math.min(height - 1, Math.max(0, y + raw_y_offset));
        for (let x = 0; x < width; x++) {
          let s_idx = sy*width + x;
          if (hyde_mask[s_idx] > 0) continue;
          let val = jrc_dv.getFloat32(s_idx*4, false);
          if (Number.isFinite(val) && val > 0)
            joined_mask[y*width + x] = 1;
        }
      }
    }
    
    population_Stadester_rasters._cached_joined_land_mask = joined_mask;
    
    //Return statement
    return joined_mask;
  };
  
  /**
   * Detects settlements whose `[lat, lng]` coordinates fall outside the joined GHS-POP + HYDE valid land mask.
   * @alias population_Stadester_rasters.detectOutOfMaskSettlements
   * 
   * @param {Object} arg0_cities_obj
   * @param {Object} [arg1_options]
   *  @param {number} [arg1_options.height=2160]
   *  @param {Uint8Array} [arg1_options.joined_mask]
   *  @param {number} [arg1_options.max_search_px=12]
   *  @param {number} [arg1_options.width=4320]
   * 
   * @returns {{actionable: Array<Object>, all_out_of_mask: Array<Object>, subpixel_islands: Array<Object>, valid_pixel_count: number}}
   */
  population_Stadester_rasters.detectOutOfMaskSettlements = function (arg0_cities_obj, arg1_options) {
    //Convert from parameters
    let cities_obj = arg0_cities_obj;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let actionable = [];
    let all_keys;
    let all_out_of_mask = [];
    let height = options.height || 2160;
    let joined_mask = options.joined_mask || population_Stadester_rasters.buildJoinedValidLandMask(options);
    let max_search_px = (options.max_search_px !== undefined) ? options.max_search_px : 12;
    let subpixel_islands = [];
    let valid_pixel_count = 0;
    let width = options.width || 4320;
    
    //Guard clauses
    if (!cities_obj || !joined_mask) return { actionable: [], all_out_of_mask: [], subpixel_islands: [], valid_pixel_count: 0 };
    
    //Function body
    for (let i = 0; i < joined_mask.length; i++)
      if (joined_mask[i] > 0) valid_pixel_count++;
    
    all_keys = Object.keys(cities_obj);
    for (let i = 0; i < all_keys.length; i++) {
      let key = all_keys[i];
      let city = cities_obj[key];
      if (!city || !Array.isArray(city.coords) || city.coords.length < 2) continue;
      let px_pair = population_Stadester_rasters.getCoordsPixel(city.coords, options);
      let px = px_pair[0];
      let py = px_pair[1];
      if (joined_mask[py*width + px] > 0) continue;
      
      let best_dist_sq = Infinity;
      let best_nx = -1;
      let best_ny = -1;
      for (let r = 1; r <= max_search_px; r++) {
        let found_in_ring = false;
        for (let x = -r; x <= r; x++) {
          let ny = py + x;
          if (ny < 0 || ny >= height) continue;
          for (let y = -r; y <= r; y++) {
            if (Math.max(Math.abs(x), Math.abs(y)) !== r) continue;
            let nx = ((px + y) % width + width) % width;
            if (joined_mask[ny*width + nx] > 0) {
              let dist_sq = x*x + y*y;
              if (dist_sq < best_dist_sq) {
                best_dist_sq = dist_sq;
                best_nx = nx;
                best_ny = ny;
                found_in_ring = true;
              }
            }
          }
        }
        if (found_in_ring) break;
      }
      
      let is_subpixel = (best_dist_sq === Infinity);
      let nearest_px = null;
      let nearest_px_dist = Infinity;
      nearest_px = (is_subpixel) ? null : [best_nx, best_ny];
      nearest_px_dist = (is_subpixel) ? Infinity : Math.sqrt(best_dist_sq);
      let entry = {
        coords: [Number(city.coords[0]), Number(city.coords[1])],
        country: city.country || "",
        is_subpixel_unrepresented_island: is_subpixel,
        key: key,
        name: city.name || key,
        nearest_px: nearest_px,
        nearest_px_dist: nearest_px_dist,
        px: [px, py],
        sources: Array.isArray(city.sources) ? city.sources.slice() : []
      };
      all_out_of_mask.push(entry);
      if (is_subpixel) {
        subpixel_islands.push(entry);
      } else {
        actionable.push(entry);
      }
    }
    
    //Return statement
    return {
      actionable: actionable,
      all_out_of_mask: all_out_of_mask,
      subpixel_islands: subpixel_islands,
      valid_pixel_count: valid_pixel_count
    };
  };
  
  /**
   * Converts decimal coordinates [lat, lng] to equirectangular pixel coordinates.
   * @alias population_Stadester_rasters.getCoordsPixel
   * 
   * @param {Array<number>} arg0_coords
   * @param {Object} [arg1_options]
   * 
   * @returns {Array<number>} [x, y]
   */
  population_Stadester_rasters.getCoordsPixel = function (arg0_coords, arg1_options) {
    //Convert from parameters
    let coords = arg0_coords;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let cfg = global.population_Stadester_config;
    let height = options.height || 2160;
    let lat;
    let lng;
    let width = options.width || 4320;
    let x;
    let y;
    let y_offset = (cfg && cfg.stadester_y_offset !== undefined) ? cfg.stadester_y_offset : 0;
    
    //Guard clauses
    if (!coords || isNaN(coords[0]) || isNaN(coords[1])) return [0, 0];
    
    lat = Math.max(-90, Math.min(90, coords[0]));
    lng = ((coords[1] + 180) % 360 + 360) % 360 - 180;
    
    x = Math.floor(((lng + 180)/360)*width);
    y = Math.floor(((90 - lat)/180)*height) + y_offset;
    
    x = Math.min(width - 1, Math.max(0, x));
    y = Math.min(height - 1, Math.max(0, y));
    
    //Return statement
    return [x, y];
  };
  
  /**
   * Returns list of pixels [x, y] falling in the annular ring of distance r from center with longitude wrapping.
   * @alias population_Stadester_rasters.getPixelsInAnnulus
   * 
   * @param {Array<number>} arg0_pixel - [cx, cy]
   * @param {number} arg1_distance - ring radius in pixels
   * @param {Object} [arg2_options]
   * 
   * @returns {Array<Array<number>>}
   */
  population_Stadester_rasters.getPixelsInAnnulus = function (arg0_pixel, arg1_distance, arg2_options) {
    //Convert from parameters
    let pixel = arg0_pixel;
    let distance = parseInt(arg1_distance);
    let options = (arg2_options) ? arg2_options : {};
    
    //Declare local instance variables
    let cx = pixel[0];
    let cy = pixel[1];
    let height = options.height || 2160;
    let pixels = [];
    let r = distance;
    let rMax = (r + 0.5)*(r + 0.5);
    let rMin = (r - 0.5)*(r - 0.5);
    let width = options.width || 4320;
    
    for (let dx = -r - 1; dx <= r + 1; dx++) {
      for (let dy = -r - 1; dy <= r + 1; dy++) {
        let distSq = dx*dx + dy*dy;
        if (distSq > rMin && distSq <= rMax) {
          let px = ((cx + dx) % width + width) % width;
          let py = Math.min(height - 1, Math.max(0, cy + dy));
          pixels.push([px, py]);
        }
      }
    }
    
    //Return statement
    return pixels;
  };
  
  /**
   * Resolves the substrata raster file path from population_Substrata.outlier_removal in float32.
   * Checks intermediate_rasters_interpolated (1800-2025), then intermediate_rasters_scaled_to_global (pre-1800),
   * with legacy fallback to intermediate_rasters_geopng_int32.
   * @alias population_Stadester_rasters.getSubstrataRasterPath
   * 
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   *  @param {string} [arg1_options.input_substrata_folder]
   *  @param {string} [arg1_options.substrata_folder]
   * 
   * @returns {string} substrata raster file path
   */
  population_Stadester_rasters.getSubstrataRasterPath = function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let custom_folder = options.input_substrata_folder || options.substrata_folder;
    let default_folder = (typeof population_Substrata_outlier_removal !== "undefined" && population_Substrata_outlier_removal.intermediate_rasters_interpolated) ?
      population_Substrata_outlier_removal.intermediate_rasters_interpolated :
      `${h3}/population_Substrata.outlier_removal/rasters_4.interpolated_to_GHSL/`;
    let fallback_folder = (typeof population_Substrata_outlier_removal !== "undefined" && population_Substrata_outlier_removal.intermediate_rasters_scaled_to_global) ?
      population_Substrata_outlier_removal.intermediate_rasters_scaled_to_global :
      `${h3}/population_Substrata.outlier_removal/rasters_3.scaled_to_global/`;
    let file_path;
    let legacy_folder = (typeof population_Substrata_outlier_removal !== "undefined" && population_Substrata_outlier_removal.intermediate_rasters_geopng_int32) ?
      population_Substrata_outlier_removal.intermediate_rasters_geopng_int32 :
      `${h3}/population_Substrata.outlier_removal/rasters_5.geopng_int32/`;
    
    //1. Check custom folder if provided
    if (custom_folder) {
      file_path = path.join(custom_folder, `popc_${year}.png`);
      if (fs.existsSync(file_path)) return file_path;
    }
    
    //2. Check primary float32 interpolated folder (1800-2025)
    file_path = path.join(default_folder, `popc_${year}.png`);
    if (fs.existsSync(file_path)) return file_path;
    
    //3. Check fallback float32 scaled_to_global folder (pre-1800 and general)
    file_path = path.join(fallback_folder, `popc_${year}.png`);
    if (fs.existsSync(file_path)) return file_path;
    
    //4. Check legacy geopng_int32 folder
    file_path = path.join(legacy_folder, `popc_${year}.png`);
    if (fs.existsSync(file_path)) return file_path;
    
    //5. Return primary path by default even if not yet on disk
    //Return statement
    return (year < 1800) ? path.join(fallback_folder, `popc_${year}.png`) : path.join(default_folder, `popc_${year}.png`);
  };
  
  /**
   * Loads and caches the Stadestér UUD dataset (partitioned Viscount shards or legacy `stadester.json`),
   * refreshing when disk mtime changes.
   * @alias population_Stadester_rasters.loadStadesterObject
   *
   * @param {Object} [arg0_options]
   *
   * @returns {Object|null}
   */
  population_Stadester_rasters.loadStadesterObject = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let default_transform_path = (typeof h3 !== "undefined") ?
      path.join(`${h3}/population_Stadester.transform/stadester/`) :
      path.resolve(__dirname, "../../3.data_transform/population_Stadester.transform/stadester");
    let dump_mtime = 0;
    let dump_path = options.stadester_file_path || default_transform_path;
    let legacy_path = path.join(`${h1}/population_Stadester/uud/`, "stadester.json");
    let partition_io = global.StadesterPartitionIO;
    let stadester_obj = options.stadester_obj || null;

    //Guard clauses
    if (stadester_obj) return stadester_obj;
    if (partition_io) {
      if (!partition_io.hasDataset(dump_path) && partition_io.hasDataset(legacy_path))
        dump_path = legacy_path;
      if (!partition_io.hasDataset(dump_path)) return null;

      dump_mtime = partition_io.getDatasetMtimeMs(dump_path);
      if (global._cached_stadester_obj && global._cached_stadester_path === dump_path && global._cached_stadester_mtime === dump_mtime) {
        stadester_obj = global._cached_stadester_obj;
      } else {
        stadester_obj = partition_io.readPartitionedStadester(dump_path);
        global._cached_stadester_obj = stadester_obj;
        global._cached_stadester_path = dump_path;
        global._cached_stadester_mtime = dump_mtime;
      }

      //Return statement
      return stadester_obj;
    }

    if (!fs.existsSync(dump_path)) return null;

    //Function body
    dump_mtime = fs.statSync(dump_path).mtimeMs;
    if (global._cached_stadester_obj && global._cached_stadester_path === dump_path && global._cached_stadester_mtime === dump_mtime) {
      stadester_obj = global._cached_stadester_obj;
    } else {
      stadester_obj = JSON.parse(fs.readFileSync(dump_path, "utf8"));
      global._cached_stadester_obj = stadester_obj;
      global._cached_stadester_path = dump_path;
      global._cached_stadester_mtime = dump_mtime;
    }

    //Return statement
    return stadester_obj;
  };


  /**
   * Resolves a city's population at a target year from `city.population`, respecting the temporal proximity gap
   * (`Math.max(200, hyde_interval)`) so disconnected historical/archaeological clusters are never bridged across hiatuses.
   * @alias population_Stadester_rasters.getCityPopulationAtYear
   *
   * @param {Object} arg0_city
   * @param {number} arg1_year
   *
   * @returns {number}
   */
  population_Stadester_rasters.getCityPopulationAtYear = function (arg0_city, arg1_year) {
    //Convert from parameters
    let city = arg0_city;
    let year = Number(arg1_year);

    //Declare local instance variables
    let max_yr = 0;
    let min_yr = 0;
    let p_keys = [];

    //Guard clauses
    if (!city || !city.population || !Number.isFinite(year)) return 0;
    if (city.population[year] !== undefined)
      return parseFloat(city.population[year]) || 0;

    //Function body
    p_keys = city._pop_keys_sorted || (city._pop_keys_sorted = Object.keys(city.population).map(Number).sort((a, b) => a - b));
    if (p_keys.length === 0) return 0;

    min_yr = p_keys[0];
    max_yr = p_keys[p_keys.length - 1];
    if (year < min_yr) return 0;
    if (year > max_yr) {
      if (max_yr >= 1975 && year >= 1975 && (year - max_yr) <= 200)
        return parseFloat(city.population[max_yr]) || 0;
      return 0;
    }

    for (let i = 0; i < p_keys.length - 1; i++) {
      let y0 = p_keys[i];
      let y1 = p_keys[i + 1];
      if (year >= y0 && year <= y1) {
        let gap = y1 - y0;
        let max_gap = 200;
        if (typeof population_Stadester !== "undefined" && population_Stadester.getMaxTemporalProximityGap) {
          max_gap = population_Stadester.getMaxTemporalProximityGap(y0, y1);
        } else {
          let hyde_int = (y1 <= 0 || y0 < 0) ? 1000 : ((y1 <= 1700 || y0 < 1700) ? 100 : 10);
          max_gap = Math.max(200, hyde_int);
        }
        if (gap <= max_gap && gap > 0) {
          let v0 = parseFloat(city.population[y0]) || 0;
          let v1 = parseFloat(city.population[y1]) || 0;
          return v0 + ((year - y0)/gap)*(v1 - v0);
        }
        return 0;
      }
    }

    //Return statement
    return 0;
  };


  /**
   * Streams partitioned Stadestér shards one file at a time, retaining only lightweight
   * `{ coords, population, _px }` records to avoid multi-gigabyte V8 heap spikes from `radial_buffers`.
   * @alias population_Stadester_rasters.loadStadesterLiteList
   *
   * @param {Object} [arg0_options]
   *
   * @returns {Array<Object>}
   */
  population_Stadester_rasters.loadStadesterLiteList = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let default_transform_path = (typeof h3 !== "undefined") ?
      path.join(`${h3}/population_Stadester.transform/stadester/`) :
      path.resolve(__dirname, "../../3.data_transform/population_Stadester.transform/stadester");
    let dump_mtime = 0;
    let dump_path = options.stadester_file_path || default_transform_path;
    let legacy_path = path.join(`${h1}/population_Stadester/uud/`, "stadester.json");
    let lite_list = [];
    let partition_io = global.StadesterPartitionIO;
    let viscount_filter = (options.viscount_key) ? String(options.viscount_key).toUpperCase() : "";

    //Guard clauses
    if (options.stadester_obj) {
      let keys = Object.keys(options.stadester_obj);
      for (let i = 0; i < keys.length; i++) {
        let city = options.stadester_obj[keys[i]];
        if (!city || !city.coords || !city.population) continue;
        let px = city._px || (city._px = population_Stadester_rasters.getCoordsPixel(city.coords));
        lite_list.push({ _px: px, coords: city.coords, population: city.population });
      }
      return lite_list;
    }

    //Function body
    if (partition_io) {
      if (!partition_io.hasDataset(dump_path) && partition_io.hasDataset(legacy_path))
        dump_path = legacy_path;
      if (!partition_io.hasDataset(dump_path)) return lite_list;

      dump_mtime = partition_io.getDatasetMtimeMs(dump_path);
      let cache_key = `${dump_path}|${viscount_filter}`;
      if (global._cached_stadester_lite && global._cached_stadester_lite_key === cache_key && global._cached_stadester_lite_mtime === dump_mtime)
        return global._cached_stadester_lite;

      let target = partition_io.resolveDatasetTarget(dump_path);
      if (target && target.mode === "partitioned") {
        let manifest = JSON.parse(fs.readFileSync(target.manifest_path, "utf8"));
        let regions = Array.isArray(manifest.regions) ? manifest.regions : [];

        for (let i = 0; i < regions.length; i++) {
          let reg_entry = regions[i];
          if (viscount_filter && reg_entry.key !== viscount_filter) continue;
          let files = Array.isArray(reg_entry.files) ? reg_entry.files : [];

          for (let x = 0; x < files.length; x++) {
            let shard_path = path.join(target.dir_path, files[x]);
            if (!fs.existsSync(shard_path)) continue;
            let shard_obj = JSON.parse(fs.readFileSync(shard_path, "utf8"));
            let shard_keys = Object.keys(shard_obj);

            for (let y = 0; y < shard_keys.length; y++) {
              let city = shard_obj[shard_keys[y]];
              if (!city || !city.coords || !city.population) continue;
              let px = population_Stadester_rasters.getCoordsPixel(city.coords);
              lite_list.push({ _px: px, coords: city.coords, population: city.population });
            }
          }
        }
        global._cached_stadester_lite = lite_list;
        global._cached_stadester_lite_key = cache_key;
        global._cached_stadester_lite_mtime = dump_mtime;

        //Return statement
        return lite_list;
      }
    }

    let fallback_obj = population_Stadester_rasters.loadStadesterObject(options);
    if (fallback_obj) {
      let keys = Object.keys(fallback_obj);
      for (let i = 0; i < keys.length; i++) {
        let city = fallback_obj[keys[i]];
        if (!city || !city.coords || !city.population) continue;
        let px = city._px || (city._px = population_Stadester_rasters.getCoordsPixel(city.coords));
        lite_list.push({ _px: px, coords: city.coords, population: city.population });
      }
    }

    //Return statement
    return lite_list;
  };


  /**
   * Computes a `Float32Array(4320*2160)` of sub-urban settlement populations (`0 < city_pop < min_urban_raster_population`)
   * from `stadester.json` for a given year so settlements with `< 5,000` people are preserved in rural and total population rasters.
   * @alias population_Stadester_rasters.getSubUrbanSettlementsData
   *
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   *
   * @returns {Float32Array}
   */
  population_Stadester_rasters.getSubUrbanSettlementsData = function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let cfg = global.population_Stadester_config;
    let lite_list;
    let min_urban_population = (options.min_urban_raster_population !== undefined) ?
      options.min_urban_raster_population :
      ((cfg && cfg.min_urban_raster_population !== undefined) ? cfg.min_urban_raster_population : 5000);
    let sub_urban_data = new Float32Array(4320*2160);

    //Guard clauses
    if (year < -10000) return sub_urban_data;

    //Function body
    lite_list = population_Stadester_rasters.loadStadesterLiteList(options);
    for (let i = 0; i < lite_list.length; i++) {
      let city = lite_list[i];
      let city_pop = population_Stadester_rasters.getCityPopulationAtYear(city, year);
      if (city_pop <= 0 || city_pop >= min_urban_population) continue;

      let center_idx = city._px[1]*4320 + city._px[0];
      sub_urban_data[center_idx] += city_pop;
    }

    //Return statement
    return sub_urban_data;
  };


  /**
   * Computes a `Float32Array(4320*2160)` of urban settlement populations (`city_pop >= min_urban_raster_population`)
   * from `stadester.json` for a given year (useful for intermediate 100-year antiquity steps not in `stadester_years`).
   * @alias population_Stadester_rasters.getUrbanSettlementsData
   *
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   *
   * @returns {Float32Array}
   */
  population_Stadester_rasters.getUrbanSettlementsData = function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let cfg = global.population_Stadester_config;
    let lite_list;
    let min_urban_population = (options.min_urban_raster_population !== undefined) ?
      options.min_urban_raster_population :
      ((cfg && cfg.min_urban_raster_population !== undefined) ? cfg.min_urban_raster_population : 5000);
    let urban_data = new Float32Array(4320*2160);

    //Guard clauses
    if (year < -10000) return urban_data;

    //Function body
    lite_list = population_Stadester_rasters.loadStadesterLiteList(options);
    for (let i = 0; i < lite_list.length; i++) {
      let city = lite_list[i];
      let city_pop = population_Stadester_rasters.getCityPopulationAtYear(city, year);
      if (city_pop < min_urban_population) continue;

      let center_idx = city._px[1]*4320 + city._px[0];
      urban_data[center_idx] += city_pop;
    }

    //Return statement
    return urban_data;
  };


  /**
   * Generates Stadestér Base raster for a single year in float32 format.
   * @alias population_Stadester_rasters.generateStadesterBaseRaster
   * 
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   * 
   * @returns {Promise<string>} output file path
   */
  population_Stadester_rasters.generateStadesterBaseRaster = async function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let all_city_keys;
    let base_folder = options.intermediate_base_folder || `${h2}/population_Stadester/stadester_base_rasters/`;
    let base_raster_data = new Float32Array(4320*2160);
    let cfg = global.population_Stadester_config;
    let min_urban_population = (options.min_urban_raster_population !== undefined) ?
      options.min_urban_raster_population :
      ((cfg && cfg.min_urban_raster_population !== undefined) ? cfg.min_urban_raster_population : 5000);
    let output_file_path = path.join(base_folder, `stadester_base_${year}.png`);
    let pixel_dictionary = {};
    let stadester_obj = population_Stadester_rasters.loadStadesterObject(options);
    let substrata_file_path;
    let substrata_raster;
    
    //Guard clauses
    if (year < -10000) {
      if (!fs.existsSync(base_folder)) fs.mkdirSync(base_folder, { recursive: true });
      GeoPNG.saveNumberRasterImage({
        file_path: output_file_path,
        format: "float32",
        function: function (local_index) { return 0; },
        height: 2160,
        width: 4320
      });
      console.log(`- Saved blank Stadestér Base raster for ${year}: ${output_file_path}`);
      
      //Return statement
      return output_file_path;
    }
    
    //Resolve substrata path from population_Substrata.outlier_removal in float32
    substrata_file_path = population_Stadester_rasters.getSubstrataRasterPath(year, options);
    
    if (fs.existsSync(substrata_file_path))
      substrata_raster = GeoPNG.loadNumberRasterImage(substrata_file_path, { format: "float32" });
    
    if (!stadester_obj) return output_file_path;
    all_city_keys = Object.keys(stadester_obj);
    
    //Bin cities by pixel
    for (let i = 0; i < all_city_keys.length; i++) {
      let city = stadester_obj[all_city_keys[i]];
      if (!city || !city.coords || !city.population) continue;
      
      let pop_keys = city._pop_keys || (city._pop_keys = Object.keys(city.population).map(Number));
      let min_yr = (city._min_yr !== undefined) ? city._min_yr : (city._min_yr = Math.min(...pop_keys));
      let max_yr = (city._max_yr !== undefined) ? city._max_yr : (city._max_yr = Math.max(...pop_keys));
      
      if ((year >= min_yr && year <= max_yr) || (max_yr >= 1975 && year >= 1975)) {
        let px = city._px || (city._px = population_Stadester_rasters.getCoordsPixel(city.coords));
        let key = `${px[0]},${px[1]}`;
        if (!pixel_dictionary[key]) pixel_dictionary[key] = [];
        pixel_dictionary[key].push(city);
      }
    }
    
    let all_pixel_keys = Object.keys(pixel_dictionary);
    for (let i = 0; i < all_pixel_keys.length; i++) {
      let center_coords = all_pixel_keys[i].split(",").map(Number);
      let center_idx = center_coords[1]*4320 + center_coords[0];
      let local_cities = pixel_dictionary[all_pixel_keys[i]];
      if (local_cities.length === 0) continue;
      
      for (let x = 0; x < local_cities.length; x++) {
        let city = local_cities[x];
        let city_pop = population_Stadester_rasters.getCityPopulationAtYear(city, year);
        let local_pixels = {};
        let radial_buffers = [];
        
        if (city_pop < min_urban_population) continue;
        
        if (city.radial_buffers) {
          if (city.radial_buffers[year] !== undefined) {
            radial_buffers = city.radial_buffers[year];
          } else {
            let b_keys = city._buffer_keys_sorted || (city._buffer_keys_sorted = Object.keys(city.radial_buffers).map(Number).sort((a, b) => a - b));
            for (let y = 0; y < b_keys.length; y++) {
              if (b_keys[y] <= year) {
                let b_gap = year - b_keys[y];
                let max_b_gap = (typeof population_Stadester !== "undefined" && population_Stadester.getMaxTemporalProximityGap) ?
                  population_Stadester.getMaxTemporalProximityGap(b_keys[y], year) :
                  ((year <= 0 || b_keys[y] < 0) ? 1000 : 200);
                if (b_gap <= max_b_gap)
                  radial_buffers = city.radial_buffers[b_keys[y]];
              }
            }
          }
        }
        
        if (radial_buffers && radial_buffers.length > 1 && substrata_raster) {
          local_pixels[center_idx] = radial_buffers[0];
          
          for (let ring = 1; ring < radial_buffers.length; ring++) {
            let annular_pixels = population_Stadester_rasters.getPixelsInAnnulus(center_coords, ring);
            let annular_sum = 0;
            
            for (let z = 0; z < annular_pixels.length; z++) {
              let idx = annular_pixels[z][1]*4320 + annular_pixels[z][0];
              annular_sum += (substrata_raster.data[idx] || 0);
            }
            
            if (annular_sum === 0) continue;
            let annular_scalar = radial_buffers[ring]/annular_sum;
            
            for (let z = 0; z < annular_pixels.length; z++) {
              let px = annular_pixels[z][0];
              let py = annular_pixels[z][1];
              let idx = py*4320 + px;
              let scaled_val = (substrata_raster.data[idx] || 0)*annular_scalar;
              local_pixels[idx] = (local_pixels[idx] || 0) + scaled_val;
            }
          }
        } else {
          local_pixels[center_idx] = (local_pixels[center_idx] || 0) + city_pop;
        }
        
        let local_indices = Object.keys(local_pixels);
        let cur_sum = 0;
        for (let y = 0; y < local_indices.length; y++) cur_sum += local_pixels[local_indices[y]];
        let cur_scalar = (cur_sum > 0 && city_pop > 0) ? (city_pop/cur_sum) : 1;
        
        for (let y = 0; y < local_indices.length; y++) {
          let idx = parseInt(local_indices[y]);
          let v = local_pixels[idx]*cur_scalar;
          base_raster_data[idx] += v;
        }
      }
    }
    
    //Save Base raster in float32 format
    GeoPNG.saveNumberRasterImage({
      file_path: output_file_path,
      format: "float32",
      height: 2160,
      width: 4320,
      function: function (local_index) {
        return base_raster_data[local_index];
      }
    });
    
    console.log(`- Saved Stadestér Base raster for ${year}: ${output_file_path}`);
    
    //Return statement
    return output_file_path;
  };
  
  /**
   * Generates Stadestér Urban raster for a single year preserving JSON ground truth in float32.
   * @alias population_Stadester_rasters.generateStadesterUrbanRaster
   * 
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   * 
   * @returns {Promise<string>} output file path
   */
  population_Stadester_rasters.generateStadesterUrbanRaster = async function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let base_file_path = path.join(options.intermediate_base_folder || `${h2}/population_Stadester/stadester_base_rasters/`, `stadester_base_${year}.png`);
    let base_raster = null;
    let output_file_path = path.join(options.input_urbc_folder || `${h2}/population_Stadester/stadester_urban_rasters/`, `stadester_urban_${year}.png`);
    let urban_folder = path.dirname(output_file_path);
    
    //Guard clauses
    if (year < -10000) {
      if (!fs.existsSync(urban_folder)) fs.mkdirSync(urban_folder, { recursive: true });
      GeoPNG.saveNumberRasterImage({
        file_path: output_file_path,
        format: "float32",
        function: function (local_index) { return 0; },
        height: 2160,
        width: 4320
      });
      console.log(`- Saved blank Stadestér Urban raster for ${year}: ${output_file_path}`);
      
      //Return statement
      return output_file_path;
    }
    
    if (options.base_raster) {
      base_raster = options.base_raster;
    } else if (fs.existsSync(base_file_path)) {
      base_raster = GeoPNG.loadNumberRasterImage(base_file_path, { format: "float32" });
    }
    
    if (!fs.existsSync(urban_folder)) fs.mkdirSync(urban_folder, { recursive: true });
    
    //Stadestér Base preserves exact city numbers from stadester.json
    GeoPNG.saveNumberRasterImage({
      file_path: output_file_path,
      format: "float32",
      height: 2160,
      width: 4320,
      function: function (local_index) {
        let base_val = (base_raster && base_raster.data[local_index]) ? base_raster.data[local_index] : 0;
        return (base_val >= 0.01) ? base_val : 0;
      }
    });
    
    console.log(`- Saved Stadestér Urban raster for ${year}: ${output_file_path}`);
    
    //Return statement
    return output_file_path;
  };
  
  /**
   * Strips non-serialisable cached raster/dataset handles from worker options.
   * @alias population_Stadester_rasters.buildWorkerOptions
   * 
   * @param {Object} [arg0_options]
   * 
   * @returns {Object}
   */
  population_Stadester_rasters.buildWorkerOptions = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};
    
    //Declare local instance variables
    let worker_options = Object.assign({}, options);
    
    //Function body
    delete worker_options.base_raster;
    delete worker_options.pixel_to_geocode;
    delete worker_options.stadester_obj;
    delete worker_options.substrata_raster;
    delete worker_options.urban_raster;
    
    //Return statement
    return worker_options;
  };
  
  /**
   * Parallel runners using GeoPNG.processTimeseriesParallel.
   * @alias population_Stadester_rasters.processParallel
   */
  population_Stadester_rasters.generateBaseRastersParallel = async function (arg0_years, arg1_options) {
    //Convert from parameters
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let default_concurrency = (typeof require !== "undefined") ? Math.min(8, require("os").cpus().length || 4) : 4;
    let worker_options = population_Stadester_rasters.buildWorkerOptions(options);
    
    //Return statement
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Base Rasters",
      task_generator: (year) => {
        if (year < -10000) {
          let base_folder = options.intermediate_base_folder || `${h2}/population_Stadester/stadester_base_rasters/`;
          let output_file_path = path.join(base_folder, `stadester_base_${year}.png`);
          return {
            type: "blank_raster",
            format: "float32",
            height: 2160,
            output_file_path: output_file_path,
            width: 4320
          };
        }
        return {
          type: "stadester_base_raster",
          options: worker_options,
          year: year
        };
      },
      handler: async (year) => population_Stadester_rasters.generateStadesterBaseRaster(year, options)
    });
  };
  
  population_Stadester_rasters.generateUrbanRastersParallel = async function (arg0_years, arg1_options) {
    //Convert from parameters
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let default_concurrency = (typeof require !== "undefined") ? Math.min(8, require("os").cpus().length || 4) : 4;
    let worker_options = population_Stadester_rasters.buildWorkerOptions(options);
    
    //Return statement
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Urban Rasters",
      task_generator: (year) => {
        if (year < -10000) {
          let urban_folder = options.input_urbc_folder || `${h2}/population_Stadester/stadester_urban_rasters/`;
          let output_file_path = path.join(urban_folder, `stadester_urban_${year}.png`);
          return {
            type: "blank_raster",
            format: "float32",
            height: 2160,
            output_file_path: output_file_path,
            width: 4320
          };
        }
        return {
          type: "stadester_urban_raster",
          options: worker_options,
          year: year
        };
      },
      handler: async (year) => population_Stadester_rasters.generateStadesterUrbanRaster(year, options)
    });
  };
  
  if (typeof require !== "undefined")
    try { require(path.join(__dirname, "stadester_rasters_reconcile.js")); } catch (e) {}
}
