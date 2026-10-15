//Initialise functions
{
  if (!global.population_Stadester_rasters) global.population_Stadester_rasters = {};
  
  /**
   * Converts decimal coordinates [lat, lng] to equirectangular pixel coordinates with -1 y-offset fix.
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
    let y_offset = (cfg && cfg.stadester_y_offset !== undefined) ? cfg.stadester_y_offset : -1;
    
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
    let output_file_path = path.join(base_folder, `stadester_base_${year}.png`);
    let pixel_dictionary = {};
    let stadester_obj = options.stadester_obj;
    let substrata_file_path;
    let substrata_raster;
    
    //Guard clauses
    if (year < -3000) {
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
    
    if (!stadester_obj) {
      let dump_path = path.join(`${h1}/population_Stadester/uud/`, "stadester.json");
      if (fs.existsSync(dump_path))
        stadester_obj = JSON.parse(fs.readFileSync(dump_path, "utf8"));
    }
    
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
        let city_pop = 0;
        let local_pixels = {};
        let radial_buffers = [];
        
        if (city.population) {
          let p_keys = city._pop_keys_sorted || (city._pop_keys_sorted = Object.keys(city.population).map(Number).sort((a, b) => a - b));
          for (let y = 0; y < p_keys.length; y++)
            if (p_keys[y] <= year) city_pop = parseFloat(city.population[p_keys[y]]) || 0;
        }
        
        if (city.radial_buffers) {
          let b_keys = city._buffer_keys_sorted || (city._buffer_keys_sorted = Object.keys(city.radial_buffers).map(Number).sort((a, b) => a - b));
          for (let y = 0; y < b_keys.length; y++)
            if (b_keys[y] <= year) radial_buffers = city.radial_buffers[b_keys[y]];
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
  /**
   * Caches and returns a flat pixel index to ISO3 country code mapping.
   * @alias population_Stadester_rasters.getPixelToGeocodeMapping
   * 
   * @returns {Array<string|null>}
   */
  population_Stadester_rasters.getPixelToGeocodeMapping = function () {
    //Declare local instance variables
    let colourcodes;
    let geocode_img;
    let geocode_path;
    let pixel_map;
    let rgb_to_iso3;
    
    if (global._cached_stadester_pixel_to_geocode)
      return global._cached_stadester_pixel_to_geocode;
    
    geocode_path = (typeof admin_modern !== "undefined" && admin_modern.input_geocodes_raster) ?
      admin_modern.input_geocodes_raster : `${h1}/admin_modern/geocodes.png`;
    
    if (!fs.existsSync(geocode_path)) return null;
    
    colourcodes = (typeof admin_modern !== "undefined" && admin_modern.getISO3ColourcodesObject) ?
      admin_modern.getISO3ColourcodesObject() : {};
    geocode_img = GeoPNG.loadImage(geocode_path);
    pixel_map = new Array(4320*2160);
    rgb_to_iso3 = {};
    
    for (let colour in colourcodes) {
      let codes = colourcodes[colour];
      if (codes && codes.length > 0) {
        let rgb = colour.split(",").slice(0, 3).join(",");
        rgb_to_iso3[rgb] = codes[0];
      }
    }
    
    for (let i = 0; i < 4320*2160; i++) {
      let b = i*4;
      let rgb = `${geocode_img.data[b]},${geocode_img.data[b + 1]},${geocode_img.data[b + 2]}`;
      pixel_map[i] = rgb_to_iso3[rgb] || null;
    }
    
    global._cached_stadester_pixel_to_geocode = pixel_map;
    
    //Return statement
    return pixel_map;
  };
  
  population_Stadester_rasters.getPixelToISO2Mapping = population_Stadester_rasters.getPixelToGeocodeMapping;


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
    if (year < -3000) {
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
   * Reconciles Rural and Total Population rasters using national dasymetric rural scaling in float32.
   * Preserves exact urban city populations from stadester.json and calibrates rural to national totals.
   * @alias population_Stadester_rasters.reconcileStadesterDemographics
   * 
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   * 
   * @returns {Promise<Object>} { pop_file_path, rural_file_path }
   */
  population_Stadester_rasters.reconcileStadesterDemographics = async function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let country_raw_rur = {};
    let country_scalar_r = {};
    let country_scalar_u = {};
    let country_sub = {};
    let country_urb = {};
    let fallback_scalar_r = 1;
    let fallback_scalar_u = 1;
    let global_raw_rur = 0;
    let global_sub = 0;
    let global_urb = 0;
    let pixel_to_geocode = (options.pixel_to_geocode) ?
      options.pixel_to_geocode : population_Stadester_rasters.getPixelToGeocodeMapping();
    let pop_file_path = path.join(options.input_popc_folder || `${h2}/population_Stadester/stadester_population_rasters/`, `stadester_population_${year}.png`);
    let pop_folder = path.dirname(pop_file_path);
    let raw_rural_data = new Float32Array(4320*2160);
    let rural_data = new Float32Array(4320*2160);
    let rural_file_path = path.join(options.input_rurc_folder || `${h2}/population_Stadester/stadester_rural_rasters/`, `stadester_rural_${year}.png`);
    let rural_folder = path.dirname(rural_file_path);
    let substrata_file_path = population_Stadester_rasters.getSubstrataRasterPath(year, options);
    let substrata_raster = null;
    let total_data = new Float32Array(4320*2160);
    let total_pixels = 4320*2160;
    let urban_data = new Float32Array(4320*2160);
    let urban_file_path = path.join(options.input_urbc_folder || `${h2}/population_Stadester/stadester_urban_rasters/`, `stadester_urban_${year}.png`);
    let urban_folder = path.dirname(urban_file_path);
    let urban_raster = null;
    
    //Ensure destination directories exist
    if (!fs.existsSync(pop_folder)) fs.mkdirSync(pop_folder, { recursive: true });
    if (!fs.existsSync(rural_folder)) fs.mkdirSync(rural_folder, { recursive: true });
    if (!fs.existsSync(urban_folder)) fs.mkdirSync(urban_folder, { recursive: true });
    
    //Guard clauses
    if (year < -3000) {
      if (fs.existsSync(substrata_file_path)) {
        fs.copyFileSync(substrata_file_path, rural_file_path);
        fs.copyFileSync(substrata_file_path, pop_file_path);
        console.log(`- Copied Stadestér Rural & Pop rasters from substrata for ${year}`);
      }
      return { pop_file_path: pop_file_path, rural_file_path: rural_file_path, urban_file_path: urban_file_path };
    }
    
    //Load substrata raster
    if (options.substrata_raster) {
      substrata_raster = options.substrata_raster;
    } else if (fs.existsSync(substrata_file_path)) {
      substrata_raster = GeoPNG.loadNumberRasterImage(substrata_file_path, { format: "float32" });
    }
    
    //Ensure urban raster is loaded (generate if missing)
    if (options.urban_raster) {
      urban_raster = options.urban_raster;
    } else if (fs.existsSync(urban_file_path)) {
      urban_raster = GeoPNG.loadNumberRasterImage(urban_file_path, { format: "float32" });
    } else {
      await population_Stadester_rasters.generateStadesterUrbanRaster(year, options);
      if (fs.existsSync(urban_file_path))
        urban_raster = GeoPNG.loadNumberRasterImage(urban_file_path, { format: "float32" });
    }
    
    //Pass 1: Accumulate Substrata target, Urban ground truth, and Raw Rural per country
    for (let i = 0; i < total_pixels; i++) {
      let s = (substrata_raster && substrata_raster.data[i]) ? substrata_raster.data[i] : 0;
      let u = (urban_raster && urban_raster.data[i]) ? urban_raster.data[i] : 0;
      let rr = Math.max(0, s - u);
      raw_rural_data[i] = rr;
      
      global_sub += s;
      global_urb += u;
      global_raw_rur += rr;
      
      if (pixel_to_geocode) {
        let c = pixel_to_geocode[i];
        if (c) {
          country_sub[c] = (country_sub[c] || 0) + s;
          country_urb[c] = (country_urb[c] || 0) + u;
          country_raw_rur[c] = (country_raw_rur[c] || 0) + rr;
        }
      }
    }
    
    //Compute per-country scalars:
    //If U < S: Preserve exact urban ground truth from stadester.json and dasymetrically calibrate rural: TargetRural = S - U
    //If U >= S: Urban alone meets or exceeds national baseline S; scale (urban + rural) proportionally by S / (U + RR) to eliminate zeroes
    if (pixel_to_geocode) {
      let all_countries = Object.keys(country_sub);
      for (let i = 0; i < all_countries.length; i++) {
        let c = all_countries[i];
        let raw_r = country_raw_rur[c] || 0;
        let s = country_sub[c];
        let u = country_urb[c] || 0;
        
        if (u < s) {
          let target_r = s - u;
          country_scalar_r[c] = (raw_r > 0) ? (target_r/raw_r) : 0;
          country_scalar_u[c] = 1;
        } else {
          let combined = u + raw_r;
          let sc = (combined > 0) ? (s/combined) : 1;
          country_scalar_r[c] = sc;
          country_scalar_u[c] = sc;
        }
      }
    }
    
    if (global_urb < global_sub) {
      let fallback_target_r = global_sub - global_urb;
      fallback_scalar_r = (global_raw_rur > 0) ? (fallback_target_r/global_raw_rur) : 1;
      fallback_scalar_u = 1;
    } else {
      let global_combined = global_urb + global_raw_rur;
      let sc = (global_combined > 0) ? (global_sub/global_combined) : 1;
      fallback_scalar_r = sc;
      fallback_scalar_u = sc;
    }
    
    //Pass 2: Apply scalars and construct strictly consistent Total = Urban + Rural
    for (let i = 0; i < total_pixels; i++) {
      let c = pixel_to_geocode ? pixel_to_geocode[i] : null;
      let sc_r = (c && country_scalar_r[c] !== undefined) ? country_scalar_r[c] : fallback_scalar_r;
      let sc_u = (c && country_scalar_u[c] !== undefined) ? country_scalar_u[c] : fallback_scalar_u;
      let r = raw_rural_data[i]*sc_r;
      let u = (urban_raster && urban_raster.data[i]) ? urban_raster.data[i]*sc_u : 0;
      
      rural_data[i] = (r >= 0.01) ? r : 0;
      urban_data[i] = (u >= 0.01) ? u : 0;
      let tot = urban_data[i] + rural_data[i];
      total_data[i] = (tot >= 0.01) ? tot : 0;
    }
    
    //Save Rural, Total Population, and synchronised Urban rasters
    GeoPNG.saveNumberRasterImage({
      file_path: rural_file_path,
      format: "float32",
      height: 2160,
      width: 4320,
      function: function (local_index) { return rural_data[local_index]; }
    });
    
    GeoPNG.saveNumberRasterImage({
      file_path: pop_file_path,
      format: "float32",
      height: 2160,
      width: 4320,
      function: function (local_index) { return total_data[local_index]; }
    });
    
    GeoPNG.saveNumberRasterImage({
      file_path: urban_file_path,
      format: "float32",
      height: 2160,
      width: 4320,
      function: function (local_index) { return urban_data[local_index]; }
    });
    
    console.log(`- Saved reconciled Stadestér Urban, Rural & Pop rasters for ${year}: Total=${pop_file_path}`);
    
    //Return statement
    return { pop_file_path: pop_file_path, rural_file_path: rural_file_path, urban_file_path: urban_file_path };
  };
  
  /**
   * Generates Stadestér Rural raster for a single year by reconciling with national targets in float32.
   * @alias population_Stadester_rasters.generateStadesterRuralRaster
   * 
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   * 
   * @returns {Promise<string>} output file path
   */
  population_Stadester_rasters.generateStadesterRuralRaster = async function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let result = await population_Stadester_rasters.reconcileStadesterDemographics(year, options);
    
    //Return statement
    return result.rural_file_path;
  };
  
  /**
   * Generates Stadestér Population raster and reconciles rural population to targets in float32.
   * @alias population_Stadester_rasters.generateStadesterPopulationRaster
   * 
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   * 
   * @returns {Promise<string>} output file path
   */
  population_Stadester_rasters.generateStadesterPopulationRaster = async function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let result = await population_Stadester_rasters.reconcileStadesterDemographics(year, options);
    
    //Return statement
    return result.pop_file_path;
  };
  
  /**
   * Prepares density raster (population / land area) in float32.
   * @alias population_Stadester_rasters.prepareDensityRaster
   * 
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   * 
   * @returns {Promise<string>} output file path
   */
  population_Stadester_rasters.prepareDensityRaster = async function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let landarea_file = (typeof metadata_HYDE !== "undefined" && metadata_HYDE.input_raster_land_area) ?
      metadata_HYDE.input_raster_land_area : `${h1}/metadata_HYDE/general_rasters/land_area.png`;
    let landarea_raster = null;
    let output_file_path = path.join(options.intermediate_popd_folder || `${h2}/population_Stadester/stadester_density_rasters/`, `stadester_density_${year}.png`);
    let pop_file_path = path.join(options.input_popc_folder || `${h2}/population_Stadester/stadester_population_rasters/`, `stadester_population_${year}.png`);
    let pop_raster = null;
    
    if (fs.existsSync(landarea_file))
      landarea_raster = GeoPNG.loadNumberRasterImage(landarea_file, { format: "int32" });
    if (fs.existsSync(pop_file_path))
      pop_raster = GeoPNG.loadNumberRasterImage(pop_file_path, { format: "float32" });
    
    GeoPNG.saveNumberRasterImage({
      file_path: output_file_path,
      format: "float32",
      height: 2160,
      width: 4320,
      function: function (local_index) {
        let km2 = (landarea_raster && landarea_raster.data[local_index]) ? landarea_raster.data[local_index] : 0;
        let p = (pop_raster && pop_raster.data[local_index]) ? pop_raster.data[local_index] : 0;
        if (km2 <= 0 || p < 0.01) return 0;
        let val = p/km2;
        return isFinite(val) ? val : 0;
      }
    });
    
    console.log(`- Saved Stadestér Density raster for ${year}: ${output_file_path}`);
    
    //Return statement
    return output_file_path;
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
    
    //Return statement
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Base Rasters",
      task_generator: (year) => {
        if (year < -3000) {
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
          options: options,
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
    
    //Return statement
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Urban Rasters",
      task_generator: (year) => {
        if (year < -3000) {
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
          options: options,
          year: year
        };
      },
      handler: async (year) => population_Stadester_rasters.generateStadesterUrbanRaster(year, options)
    });
  };
  
  population_Stadester_rasters.generateRuralRastersParallel = async function (arg0_years, arg1_options) {
    //Convert from parameters
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let default_concurrency = (typeof require !== "undefined") ? Math.min(8, require("os").cpus().length || 4) : 4;
    
    //Return statement
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Rural Rasters",
      task_generator: (year) => {
        if (year < -3000) {
          let rural_folder = options.input_rurc_folder || `${h2}/population_Stadester/stadester_rural_rasters/`;
          let output_file_path = path.join(rural_folder, `stadester_rural_${year}.png`);
          let substrata_file_path = population_Stadester_rasters.getSubstrataRasterPath(year, options);
          if (fs.existsSync(substrata_file_path)) {
            return {
              type: "copy",
              from_file_path: substrata_file_path,
              output_file_path: output_file_path
            };
          }
        }
        return {
          type: "stadester_rural_raster",
          options: options,
          year: year
        };
      },
      handler: async (year) => population_Stadester_rasters.generateStadesterRuralRaster(year, options)
    });
  };
  
  population_Stadester_rasters.generatePopulationRastersParallel = async function (arg0_years, arg1_options) {
    //Convert from parameters
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let default_concurrency = (typeof require !== "undefined") ? Math.min(8, require("os").cpus().length || 4) : 4;
    
    //Return statement
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Population Rasters",
      task_generator: (year) => {
        if (year < -3000) {
          let pop_folder = options.input_popc_folder || `${h2}/population_Stadester/stadester_population_rasters/`;
          let output_file_path = path.join(pop_folder, `stadester_population_${year}.png`);
          let substrata_file_path = population_Stadester_rasters.getSubstrataRasterPath(year, options);
          if (fs.existsSync(substrata_file_path)) {
            return {
              type: "copy",
              from_file_path: substrata_file_path,
              output_file_path: output_file_path
            };
          }
        }
        return {
          type: "stadester_population_raster",
          options: options,
          year: year
        };
      },
      handler: async (year) => population_Stadester_rasters.generateStadesterPopulationRaster(year, options)
    });
  };
  
  population_Stadester_rasters.prepareDensityRastersParallel = async function (arg0_years, arg1_options) {
    //Convert from parameters
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let default_concurrency = (typeof require !== "undefined") ? Math.min(8, require("os").cpus().length || 4) : 4;
    let input_popc = options.input_popc_folder || `${h2}/population_Stadester/stadester_population_rasters/`;
    let intermediate_popd = options.intermediate_popd_folder || `${h2}/population_Stadester/stadester_density_rasters/`;
    let landarea_file = (typeof metadata_HYDE !== "undefined" && metadata_HYDE.input_raster_land_area) ?
      metadata_HYDE.input_raster_land_area : `${h1}/metadata_HYDE/general_rasters/land_area.png`;

    if (!fs.existsSync(intermediate_popd)) fs.mkdirSync(intermediate_popd, { recursive: true });

    //Return statement
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Density Rasters",
      task_generator: (year) => {
        let output_file_path = path.join(intermediate_popd, `stadester_density_${year}.png`);
        let pop_file_path = path.join(input_popc, `stadester_population_${year}.png`);
        if (!fs.existsSync(pop_file_path) || !fs.existsSync(landarea_file)) return null;

        return {
          type: "raster_operation",
          format: "float32",
          format_1: "float32",
          format_2: "int32",
          input_path_1: pop_file_path,
          input_path_2: landarea_file,
          op: "divide",
          operation: "divide",
          output_path: output_file_path
        };
      },
      handler: async (year) => population_Stadester_rasters.prepareDensityRaster(year, options)
    });
  };
}
