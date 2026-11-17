//Initialise functions
{
  if (!global.population_Stadester_rasters) global.population_Stadester_rasters = {};
  if (!global.population_Stadester_config && typeof require !== "undefined")
    try { require(path.join(__dirname, "config", "stadester_config.js")); } catch (e) {}
  if (!global.StadesterPartitionIO && typeof require !== "undefined")
    try { require(path.join(__dirname, "StadesterPartitionIO.js")); } catch (e) {}
  
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
    let all_city_keys;
    let cfg = global.population_Stadester_config;
    let min_urban_population = (options.min_urban_raster_population !== undefined) ?
      options.min_urban_raster_population :
      ((cfg && cfg.min_urban_raster_population !== undefined) ? cfg.min_urban_raster_population : 5000);
    let stadester_obj = population_Stadester_rasters.loadStadesterObject(options);
    let sub_urban_data = new Float32Array(4320*2160);

    //Guard clauses
    if (year < -10000 || !stadester_obj) return sub_urban_data;

    //Function body
    all_city_keys = Object.keys(stadester_obj);
    for (let i = 0; i < all_city_keys.length; i++) {
      let city = stadester_obj[all_city_keys[i]];
      if (!city || !city.coords || !city.population) continue;

      let city_pop = population_Stadester_rasters.getCityPopulationAtYear(city, year);
      if (city_pop <= 0 || city_pop >= min_urban_population) continue;

      let px = city._px || (city._px = population_Stadester_rasters.getCoordsPixel(city.coords));
      let center_idx = px[1]*4320 + px[0];
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
    let all_city_keys;
    let cfg = global.population_Stadester_config;
    let min_urban_population = (options.min_urban_raster_population !== undefined) ?
      options.min_urban_raster_population :
      ((cfg && cfg.min_urban_raster_population !== undefined) ? cfg.min_urban_raster_population : 5000);
    let stadester_obj = population_Stadester_rasters.loadStadesterObject(options);
    let urban_data = new Float32Array(4320*2160);

    //Guard clauses
    if (year < -10000 || !stadester_obj) return urban_data;

    //Function body
    all_city_keys = Object.keys(stadester_obj);
    for (let i = 0; i < all_city_keys.length; i++) {
      let city = stadester_obj[all_city_keys[i]];
      if (!city || !city.coords || !city.population) continue;

      let city_pop = population_Stadester_rasters.getCityPopulationAtYear(city, year);
      if (city_pop < min_urban_population) continue;

      let px = city._px || (city._px = population_Stadester_rasters.getCoordsPixel(city.coords));
      let center_idx = px[1]*4320 + px[0];
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
