//Initialise functions
{
  if (!global.population_Stadester_rasters) global.population_Stadester_rasters = {};
  
  /**
   * Converts decimal coordinates [lat, lng] to equirectangular pixel coordinates with -2 y-offset fix.
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
    let y_offset = (cfg && cfg.stadester_y_offset !== undefined) ? cfg.stadester_y_offset : -2;
    
    //Guard clauses
    if (!coords || isNaN(coords[0]) || isNaN(coords[1])) return [0, 0];
    
    lat = Math.max(-90, Math.min(90, coords[0]));
    lng = ((coords[1] + 180) % 360 + 360) % 360 - 180;
    
    x = Math.round(((lng + 180)/360)*width);
    y = Math.round(((90 - lat)/180)*height) + y_offset;
    
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
   * Generates Stadestér Base raster for a single year in float32 format.
   * @alias population_Stadester_rasters.generateStadesterBaseRaster
   * 
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   * 
   * @returns {Promise<string>} output file path
   */
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
    
    //Resolve substrata path: GHS_POP from 1975, otherwise HYDE popc_
    if (year >= 1975) {
      substrata_file_path = `${h1}/population_GHSL/population_rasters/2.rasters/GHS_POP_${year}.png`;
    } else {
      substrata_file_path = `${h2}/landuse_HYDE/rasters_scaled_to_global/popc_${year}.png`;
      if (!fs.existsSync(substrata_file_path)) {
        let hyde_name = (typeof landuse_HYDE !== "undefined" && landuse_HYDE._getHYDEYearName) ?
          landuse_HYDE._getHYDEYearName(year) : `${Math.abs(year)}${year >= 0 ? "AD" : "BC"}`;
        substrata_file_path = `${h2}/landuse_HYDE/rasters/popc_${hyde_name}_number.png`;
      }
    }
    
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
   * Generates Stadestér Urban raster for a single year by merging Base with GHSL in float32.
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
    let ghsl_file_path = `${h1}/population_GHSL/urban_rasters/GHSL_${year}.png`;
    let ghsl_raster = null;
    let output_file_path = path.join(options.input_urbc_folder || `${h2}/population_Stadester/stadester_urban_rasters/`, `stadester_urban_${year}.png`);
    
    if (fs.existsSync(base_file_path))
      base_raster = GeoPNG.loadNumberRasterImage(base_file_path, { format: "float32" });
    if (fs.existsSync(ghsl_file_path))
      ghsl_raster = GeoPNG.loadNumberRasterImage(ghsl_file_path, { format: "float32" });
    
    GeoPNG.saveNumberRasterImage({
      file_path: output_file_path,
      format: "float32",
      height: 2160,
      width: 4320,
      function: function (local_index) {
        let ghsl_val = (ghsl_raster && ghsl_raster.data[local_index]) ? ghsl_raster.data[local_index] : 0;
        if (ghsl_val > 0) return ghsl_val;
        let base_val = (base_raster && base_raster.data[local_index]) ? base_raster.data[local_index] : 0;
        return base_val;
      }
    });
    
    console.log(`- Saved Stadestér Urban raster for ${year}: ${output_file_path}`);
    
    //Return statement
    return output_file_path;
  };
  
  /**
   * Generates Stadestér Rural raster for a single year by subtracting Urban from substrata in float32.
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
    let output_file_path = path.join(options.input_rurc_folder || `${h2}/population_Stadester/stadester_rural_rasters/`, `stadester_rural_${year}.png`);
    let substrata_file_path = (year >= 1975) ?
      `${h1}/population_GHSL/population_rasters/2.rasters/GHS_POP_${year}.png` :
      `${h2}/landuse_HYDE/rasters_scaled_to_global/popc_${year}.png`;
    let substrata_raster = null;
    let urban_file_path = path.join(options.input_urbc_folder || `${h2}/population_Stadester/stadester_urban_rasters/`, `stadester_urban_${year}.png`);
    let urban_raster = null;
    
    if (!fs.existsSync(substrata_file_path) && year < 1975) {
      let hyde_name = (typeof landuse_HYDE !== "undefined" && landuse_HYDE._getHYDEYearName) ?
        landuse_HYDE._getHYDEYearName(year) : `${Math.abs(year)}${year >= 0 ? "AD" : "BC"}`;
      substrata_file_path = `${h2}/landuse_HYDE/rasters/popc_${hyde_name}_number.png`;
    }
    
    if (options.substrata_raster) {
      substrata_raster = options.substrata_raster;
    } else if (fs.existsSync(substrata_file_path)) {
      substrata_raster = GeoPNG.loadNumberRasterImage(substrata_file_path, { format: "float32" });
    }
    if (options.urban_raster) {
      urban_raster = options.urban_raster;
    } else if (fs.existsSync(urban_file_path)) {
      urban_raster = GeoPNG.loadNumberRasterImage(urban_file_path, { format: "float32" });
    }
    
    GeoPNG.saveNumberRasterImage({
      file_path: output_file_path,
      format: "float32",
      height: 2160,
      width: 4320,
      function: function (local_index) {
        let sub_val = (substrata_raster && substrata_raster.data[local_index]) ? substrata_raster.data[local_index] : 0;
        let urb_val = (urban_raster && urban_raster.data[local_index]) ? urban_raster.data[local_index] : 0;
        return Math.max(0, sub_val - urb_val);
      }
    });
    
    console.log(`- Saved Stadestér Rural raster for ${year}: ${output_file_path}`);
    
    //Return statement
    return output_file_path;
  };
  
  /**
   * Generates Stadestér Population raster and reconciles rural population to global targets in float32.
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
    let output_file_path = path.join(options.input_popc_folder || `${h2}/population_Stadester/stadester_population_rasters/`, `stadester_population_${year}.png`);
    let rural_file_path = path.join(options.input_rurc_folder || `${h2}/population_Stadester/stadester_rural_rasters/`, `stadester_rural_${year}.png`);
    let rural_raster = null;
    let target_pop = null;
    let urban_file_path = path.join(options.input_urbc_folder || `${h2}/population_Stadester/stadester_urban_rasters/`, `stadester_urban_${year}.png`);
    let urban_raster = null;
    let world_pop_obj = options.world_pop_obj;
    
    if (!world_pop_obj && typeof population_Global !== "undefined" && population_Global.A_getWorldPopulationObject)
      world_pop_obj = population_Global.A_getWorldPopulationObject();
    
    if (world_pop_obj && world_pop_obj[year])
      target_pop = world_pop_obj[year];
    
    if (options.urban_raster) {
      urban_raster = options.urban_raster;
    } else if (fs.existsSync(urban_file_path)) {
      urban_raster = GeoPNG.loadNumberRasterImage(urban_file_path, { format: "float32" });
    }
    if (options.rural_raster) {
      rural_raster = options.rural_raster;
    } else if (fs.existsSync(rural_file_path)) {
      rural_raster = GeoPNG.loadNumberRasterImage(rural_file_path, { format: "float32" });
    }
    
    if (year < 1975) {
      //Save initial combined population
      GeoPNG.saveNumberRasterImage({
        file_path: output_file_path,
        format: "float32",
        height: 2160,
        width: 4320,
        function: function (local_index) {
          let r = (rural_raster && rural_raster.data[local_index]) ? rural_raster.data[local_index] : 0;
          let u = (urban_raster && urban_raster.data[local_index]) ? urban_raster.data[local_index] : 0;
          return r + u;
        }
      });
      
      //Scale to world population estimate
      if (target_pop) {
        let cur_sum = GeoPNG.getImageSum(output_file_path, { format: "float32" });
        if (cur_sum > 0) {
          let scalar = target_pop/cur_sum;
          let pop_raster = GeoPNG.loadNumberRasterImage(output_file_path, { format: "float32" });
          
          GeoPNG.saveNumberRasterImage({
            file_path: output_file_path,
            format: "float32",
            height: 2160,
            width: 4320,
            function: function (local_index) {
              return (pop_raster.data[local_index] || 0)*scalar;
            }
          });
          
          //Regenerate rural as Total - Urban
          let final_pop_raster = GeoPNG.loadNumberRasterImage(output_file_path, { format: "float32" });
          GeoPNG.saveNumberRasterImage({
            file_path: rural_file_path,
            format: "float32",
            height: 2160,
            width: 4320,
            function: function (local_index) {
              let p = (final_pop_raster && final_pop_raster.data[local_index]) ? final_pop_raster.data[local_index] : 0;
              let u = (urban_raster && urban_raster.data[local_index]) ? urban_raster.data[local_index] : 0;
              return Math.max(0, p - u);
            }
          });
        }
      }
    } else {
      //From 1975 onwards: Urban is rigid baseline, scale Rural to match target_pop - global_urban_pop
      let global_urban_pop = urban_raster ? GeoPNG.getImageSum(urban_file_path, { format: "float32" }) : 0;
      let target_rural = target_pop ? Math.max(0, target_pop - global_urban_pop) : null;
      let raw_rural_sum = rural_raster ? GeoPNG.getImageSum(rural_file_path, { format: "float32" }) : 0;
      let rural_scalar = (target_rural !== null && raw_rural_sum > 0) ? (target_rural/raw_rural_sum) : 1;
      
      //Write scaled Rural raster
      GeoPNG.saveNumberRasterImage({
        file_path: rural_file_path,
        format: "float32",
        height: 2160,
        width: 4320,
        function: function (local_index) {
          let r = (rural_raster && rural_raster.data[local_index]) ? rural_raster.data[local_index] : 0;
          return r*rural_scalar;
        }
      });
      
      //Write Total Population: Urban + Scaled Rural
      let scaled_rural_raster = GeoPNG.loadNumberRasterImage(rural_file_path, { format: "float32" });
      GeoPNG.saveNumberRasterImage({
        file_path: output_file_path,
        format: "float32",
        height: 2160,
        width: 4320,
        function: function (local_index) {
          let u = (urban_raster && urban_raster.data[local_index]) ? urban_raster.data[local_index] : 0;
          let r = (scaled_rural_raster && scaled_rural_raster.data[local_index]) ? scaled_rural_raster.data[local_index] : 0;
          return u + r;
        }
      });
    }
    
    console.log(`- Saved Stadestér Total Population raster for ${year}: ${output_file_path}`);
    
    //Return statement
    return output_file_path;
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
      landarea_raster = GeoPNG.loadNumberRasterImage(landarea_file, { format: "float32" });
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
        if (km2 <= 0) return 0;
        return p/km2;
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
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};
    let default_concurrency = (typeof require !== "undefined") ? Math.min(4, require("os").cpus().length || 4) : 4;
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Base Rasters",
      handler: async (year) => population_Stadester_rasters.generateStadesterBaseRaster(year, options)
    });
  };
  
  population_Stadester_rasters.generateUrbanRastersParallel = async function (arg0_years, arg1_options) {
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};
    let default_concurrency = (typeof require !== "undefined") ? Math.min(4, require("os").cpus().length || 4) : 4;
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Urban Rasters",
      handler: async (year) => population_Stadester_rasters.generateStadesterUrbanRaster(year, options)
    });
  };
  
  population_Stadester_rasters.generateRuralRastersParallel = async function (arg0_years, arg1_options) {
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};
    let default_concurrency = (typeof require !== "undefined") ? Math.min(4, require("os").cpus().length || 4) : 4;
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Rural Rasters",
      handler: async (year) => population_Stadester_rasters.generateStadesterRuralRaster(year, options)
    });
  };
  
  population_Stadester_rasters.generatePopulationRastersParallel = async function (arg0_years, arg1_options) {
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};
    let default_concurrency = (typeof require !== "undefined") ? Math.min(4, require("os").cpus().length || 4) : 4;
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Population Rasters",
      handler: async (year) => population_Stadester_rasters.generateStadesterPopulationRaster(year, options)
    });
  };
  
  population_Stadester_rasters.prepareDensityRastersParallel = async function (arg0_years, arg1_options) {
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};
    let default_concurrency = (typeof require !== "undefined") ? Math.min(4, require("os").cpus().length || 4) : 4;
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Density Rasters",
      handler: async (year) => population_Stadester_rasters.prepareDensityRaster(year, options)
    });
  };
}
