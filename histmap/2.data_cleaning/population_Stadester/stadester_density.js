//Initialise functions
{
  if (!global.population_Stadester_density) global.population_Stadester_density = {};
  if (!global.population_Stadester_config && typeof require !== "undefined")
    try { require(path.join(__dirname, "config", "stadester_config.js")); } catch (e) {}
  
  /**
   * Calculates global mean urban density across years 1800-2000 from Angel decadal rates.
   * @alias population_Stadester_density.getGlobalPopulationDensityObject
   * 
   * @returns {Object}
   */
  population_Stadester_density.getGlobalPopulationDensityObject = function () {
    //Declare local instance variables
    let all_angel_density_keys;
    let all_angel_years = [];
    let cfg = global.population_Stadester_config;
    let last_angel_year;
    let previous_value;
    let return_obj = {};
    
    previous_value = (cfg.baseline_density_per_ha[0] + cfg.baseline_density_per_ha[1])/2;
    return_obj[cfg.baseline_year] = previous_value;
    
    all_angel_density_keys = Object.keys(cfg.angel_density_change_per_decade);
    last_angel_year = parseInt(all_angel_density_keys[all_angel_density_keys.length - 1]);
    
    for (let i = 0; i < all_angel_density_keys.length; i++) {
      let decadal_rate = cfg.angel_density_change_per_decade[all_angel_density_keys[i]];
      previous_value = previous_value*(1 + decadal_rate);
      return_obj[all_angel_density_keys[i]] = previous_value;
    }
    
    for (let i = cfg.baseline_year; i <= last_angel_year; i++)
      all_angel_years.push(i);
    
    let interpolated_obj = population_Stadester_uud.cubicSplineInterpolationObject(return_obj, { years: all_angel_years });
    for (let i = last_angel_year + 1; i <= cfg.end_year; i++)
      interpolated_obj[i] = interpolated_obj[last_angel_year];
    
    //Return statement
    return interpolated_obj;
  };
  
  /**
   * Distance in kilometres using equirectangular projection.
   * @alias population_Stadester_density.equirectangularDistance
   * 
   * @param {Array<number>} arg0_coords
   * @param {Array<number>} arg1_ot_coords
   * 
   * @returns {number}
   */
  population_Stadester_density.equirectangularDistance = function (arg0_coords, arg1_ot_coords) {
    //Convert from parameters
    let coords = arg0_coords;
    let ot_coords = arg1_ot_coords;
    
    //Declare local instance variables
    let cfg = global.population_Stadester_config;
    let local_x = (ot_coords[1] - coords[1])*cfg.deg_to_radians*Math.cos(((coords[0] + ot_coords[0])/2)*cfg.deg_to_radians);
    let local_y = (ot_coords[0] - coords[0])*cfg.deg_to_radians;
    
    //Return statement
    return cfg.earth_radius*Math.sqrt(local_x*local_x + local_y*local_y);
  };
  
  /**
   * Area in square kilometres for a single equirectangular pixel at a given latitude.
   * @alias population_Stadester_density.getPixelAreaAtLatitude
   * 
   * @param {number} arg0_latitude
   * 
   * @returns {number}
   */
  population_Stadester_density.getPixelAreaAtLatitude = function (arg0_latitude) {
    //Convert from parameters
    let latitude = parseFloat(arg0_latitude);
    
    //Declare local instance variables
    let cfg = global.population_Stadester_config;
    let dx = cfg.pixel_deg*cfg.deg_to_radians*cfg.earth_radius*Math.cos(latitude*cfg.deg_to_radians);
    let dy = cfg.pixel_deg*cfg.deg_to_radians*cfg.earth_radius;
    
    //Return statement
    return Math.abs(dx*dy);
  };
  
  /**
   * Projects city area and RNI forward from a starting anchor year using path-independent Angel density and bounded city-size scaling.
   * @alias population_Stadester_density.projectCityAreaFromYear
   * 
   * @param {Object} arg0_city_obj
   * @param {number} arg1_start_year
   * @param {number} arg2_start_area
   * @param {Object} [arg3_global_pop_density_obj]
   * 
   * @returns {Object}
   */
  population_Stadester_density.projectCityAreaFromYear = function (arg0_city_obj, arg1_start_year, arg2_start_area, arg3_global_pop_density_obj) {
    //Convert from parameters
    let city_obj = arg0_city_obj;
    let global_pop_density_obj = (arg3_global_pop_density_obj) ?
      arg3_global_pop_density_obj : population_Stadester_density.getGlobalPopulationDensityObject();
    let start_area = parseFloat(arg2_start_area) || 0;
    let start_year = parseInt(arg1_start_year);
    
    //Declare local instance variables
    let all_population_keys;
    let baseline_density;
    let cfg = global.population_Stadester_config;
    let current_area;
    let ref_start_ha;
    let rni_obj = {};
    let start_density_km2;
    let start_lookup_yr;
    let start_pop;
    
    //Guard clauses
    if (!city_obj || !city_obj.population) return city_obj;
    
    //Function body
    baseline_density = (cfg.baseline_density_per_ha[0] + cfg.baseline_density_per_ha[1])/2;
    if (!city_obj.area) city_obj.area = {};
    
    current_area = Math.max(0.01, start_area);
    city_obj.area[start_year] = current_area;
    start_pop = Math.max(0, parseFloat(city_obj.population[start_year]) || 0);
    start_lookup_yr = Math.max(cfg.baseline_year, Math.min(cfg.end_year, start_year));
    ref_start_ha = (global_pop_density_obj && global_pop_density_obj[start_lookup_yr]) ?
      global_pop_density_obj[start_lookup_yr] : baseline_density;
    start_density_km2 = (start_pop > 0 && current_area > 0) ? (start_pop/current_area) : (baseline_density*100);
    all_population_keys = Object.keys(city_obj.population).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b);
    
    for (let i = 1; i < all_population_keys.length; i++) {
      let yr = all_population_keys[i];
      if (yr <= start_year) continue;
      
      let prev_yr = all_population_keys[i - 1];
      let cur_val = Math.max(0, parseFloat(city_obj.population[yr]) || 0);
      let prev_val = Math.max(0, parseFloat(city_obj.population[prev_yr]) || 0);
      let rni = (prev_val > 0) ? (cur_val - prev_val)/prev_val : 0;
      rni_obj[prev_yr] = rni;
      
      if (cur_val <= 0) {
        city_obj.area[yr] = 0;
      } else {
        let lookup_yr = Math.max(cfg.baseline_year, Math.min(cfg.end_year, yr));
        let ref_yr_ha = (global_pop_density_obj && global_pop_density_obj[lookup_yr]) ?
          global_pop_density_obj[lookup_yr] : ref_start_ha;
        let angel_ratio = (ref_start_ha > 0) ? (ref_yr_ha/ref_start_ha) : 1;
        let scale_factor = (start_pop > 0) ? Math.pow(Math.max(1, cur_val/start_pop), 0.15) : 1;
        let target_density_km2 = Math.min(100000, Math.max(500, (start_density_km2*angel_ratio)/scale_factor));
        city_obj.area[yr] = Math.max(0.01, cur_val/target_density_km2);
      }
    }
    city_obj.rni = rni_obj;
    
    //Return statement
    return city_obj;
  };
  
  /**
   * Estimates baseline city area in square kilometres at baseline year (1800) and projects via RNI.
   * @alias population_Stadester_density.estimateBaselineCityArea
   * 
   * @param {Object} arg0_city_obj
   * @param {Object} [arg1_global_pop_density_obj]
   * 
   * @returns {Object}
   */
  population_Stadester_density.estimateBaselineCityArea = function (arg0_city_obj, arg1_global_pop_density_obj) {
    //Convert from parameters
    let city_obj = arg0_city_obj;
    let global_pop_density_obj = (arg1_global_pop_density_obj) ?
      arg1_global_pop_density_obj : population_Stadester_density.getGlobalPopulationDensityObject();
    
    //Declare local instance variables
    let baseline_density;
    let cfg = global.population_Stadester_config;
    let city_baseline_population;
    let start_area;
    
    //Guard clauses
    if (!city_obj || !city_obj.population) return city_obj;
    
    baseline_density = (cfg.baseline_density_per_ha[0] + cfg.baseline_density_per_ha[1])/2;
    
    if (!city_obj.population[cfg.baseline_year])
      city_obj.population = population_Stadester_uud.cubicSplineInterpolationObject(city_obj.population, {
        years: [cfg.baseline_year]
      });
    
    city_baseline_population = Math.abs(parseFloat(city_obj.population[cfg.baseline_year]) || 0);
    if (!city_obj.area) city_obj.area = {};
    
    if (city_baseline_population > 0) {
      start_area = (city_baseline_population/baseline_density)/100;
      population_Stadester_density.projectCityAreaFromYear(city_obj, cfg.baseline_year, start_area, global_pop_density_obj);
    }
    
    //Return statement
    return city_obj;
  };
  
  /**
   * Projects remaining city areas for cities entering after 1800 using rolling Angel density.
   * @alias population_Stadester_density.calculateRemainderCityArea
   * 
   * @param {Object} arg0_city_obj
   * @param {Object} [arg1_global_pop_density_obj]
   * 
   * @returns {Object}
   */
  population_Stadester_density.calculateRemainderCityArea = function (arg0_city_obj, arg1_global_pop_density_obj) {
    //Convert from parameters
    let city_obj = arg0_city_obj;
    let global_pop_density_obj = (arg1_global_pop_density_obj) ?
      arg1_global_pop_density_obj : population_Stadester_density.getGlobalPopulationDensityObject();
    
    //Declare local instance variables
    let all_population_keys;
    let density_val;
    let entry_year = null;
    let pop_val;
    let start_area;
    
    //Guard clauses
    if (!city_obj || !city_obj.population) return city_obj;
    if (city_obj.area && Object.keys(city_obj.area).length >= 1) return city_obj;
    
    if (!city_obj.area) city_obj.area = {};
    all_population_keys = Object.keys(city_obj.population).map(Number).sort((a, b) => a - b);
    
    for (let i = 0; i < all_population_keys.length; i++) {
      let yr = all_population_keys[i];
      if (yr >= 1800 && parseFloat(city_obj.population[yr]) > 0) {
        entry_year = yr;
        break;
      }
    }
    
    if (entry_year !== null) {
      pop_val = parseFloat(city_obj.population[entry_year]);
      density_val = global_pop_density_obj[entry_year] || 180;
      start_area = Math.max(0.01, (pop_val/density_val)/100);
      population_Stadester_density.projectCityAreaFromYear(city_obj, entry_year, start_area, global_pop_density_obj);
    }
    
    //Return statement
    return city_obj;
  };
  
  /**
   * Estimates baseline areas across all cities in Stadestér dataset.
   * @alias population_Stadester_density.estimateBaselineCityAreas
   * 
   * @param {Object} arg0_stadester_obj
   * 
   * @returns {Object}
   */
  population_Stadester_density.estimateBaselineCityAreas = function (arg0_stadester_obj) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    
    //Declare local instance variables
    let all_cities = Object.keys(stadester_obj);
    let global_density = population_Stadester_density.getGlobalPopulationDensityObject();
    
    for (let i = 0; i < all_cities.length; i++)
      stadester_obj[all_cities[i]] = population_Stadester_density.estimateBaselineCityArea(stadester_obj[all_cities[i]], global_density);
    
    //Return statement
    return stadester_obj;
  };
  
  /**
   * Calculates remainder areas across all cities in Stadestér dataset.
   * @alias population_Stadester_density.calculateRemainderCityAreas
   * 
   * @param {Object} arg0_stadester_obj
   * 
   * @returns {Object}
   */
  population_Stadester_density.calculateRemainderCityAreas = function (arg0_stadester_obj) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    
    //Declare local instance variables
    let all_cities = Object.keys(stadester_obj);
    let global_density = population_Stadester_density.getGlobalPopulationDensityObject();
    
    for (let i = 0; i < all_cities.length; i++)
      stadester_obj[all_cities[i]] = population_Stadester_density.calculateRemainderCityArea(stadester_obj[all_cities[i]], global_density);
    
    //Return statement
    return stadester_obj;
  };
  
  /**
   * Applies GHSL areal anchors (1975-2025) and fixes anomalous or negative city areas.
   * @alias population_Stadester_density.fixCityAreas
   * 
   * @param {Object} arg0_stadester_obj
   * 
   * @returns {Object}
   */
  population_Stadester_density.fixCityAreas = function (arg0_stadester_obj) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    
    //Declare local instance variables
    let all_cities = Object.keys(stadester_obj);
    
    for (let i = 0; i < all_cities.length; i++) {
      let city = stadester_obj[all_cities[i]];
      if (!city) continue;
      
      if (city.area) {
        let area_keys = Object.keys(city.area);
        for (let x = 0; x < area_keys.length; x++) {
          let yr = area_keys[x];
          let pop_val = (city.population && city.population[yr] !== undefined) ?
            parseFloat(city.population[yr]) : null;
          let val = parseFloat(city.area[yr]);
          if (pop_val !== null && (!isNaN(pop_val) && pop_val <= 0)) {
            city.area[yr] = 0;
          } else if (isNaN(val) || val <= 0) {
            city.area[yr] = 0.01;
          }
        }
      }
      
      if (city._ghsl_area) {
        if (!city.area) city.area = {};
        let ghsl_area_keys = Object.keys(city._ghsl_area);
        for (let x = 0; x < ghsl_area_keys.length; x++) {
          let yr = ghsl_area_keys[x];
          let pop_val = (city.population && city.population[yr] !== undefined) ?
            parseFloat(city.population[yr]) : 0;
          let g_area = parseFloat(city._ghsl_area[yr]);
          if (pop_val <= 0) {
            city.area[yr] = 0;
          } else if (!isNaN(g_area) && g_area > 0) {
            city.area[yr] = Math.max(0.01, g_area);
          }
        }
        delete city._ghsl_area;
      }
      
      if (city._ghsl_area_partial) {
        if (!city.area) city.area = {};
        let partial_keys = Object.keys(city._ghsl_area_partial);
        for (let x = 0; x < partial_keys.length; x++) {
          let yr = partial_keys[x];
          let p_obj = city._ghsl_area_partial[yr];
          let pop_val = (city.population && city.population[yr] !== undefined) ?
            parseFloat(city.population[yr]) : 0;
          if (pop_val <= 0) {
            city.area[yr] = 0;
          } else if (p_obj && p_obj.weight > 0) {
            let est_area = Math.max(0.01, parseFloat(city.area[yr]) || 0.01);
            city.area[yr] = Math.max(0.01, (1 - p_obj.weight)*est_area + p_obj.area);
          }
        }
        delete city._ghsl_area_partial;
      }
    }
    
    //Return statement
    return stadester_obj;
  };
  
  /**
   * Computes city density (population / area) for each year.
   * @alias population_Stadester_density.calculateCityDensities
   * 
   * @param {Object} arg0_stadester_obj
   * 
   * @returns {Object}
   */
  population_Stadester_density.calculateCityDensities = function (arg0_stadester_obj) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    
    //Declare local instance variables
    let all_cities = Object.keys(stadester_obj);
    
    for (let i = 0; i < all_cities.length; i++) {
      let city = stadester_obj[all_cities[i]];
      if (city && city.area && city.population) {
        let area_keys = Object.keys(city.area);
        let density_obj = {};
        for (let x = 0; x < area_keys.length; x++) {
          let yr = area_keys[x];
          let a = parseFloat(city.area[yr]);
          let p = parseFloat(city.population[yr]);
          if (!isNaN(a) && a > 0 && !isNaN(p) && p > 0)
            density_obj[yr] = p/a;
        }
        city.density = density_obj;
      }
    }
    
    //Return statement
    return stadester_obj;
  };
  
  /**
   * Assigns regional typology classifications (.angel_region, .clark_region) by sampling raster masks.
   * @alias population_Stadester_density.assignRegionsToCities
   * 
   * @param {Object} arg0_stadester_obj
   * @param {Object} [arg1_options]
   * 
   * @returns {Object}
   */
  population_Stadester_density.assignRegionsToCities = function (arg0_stadester_obj, arg1_options) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let all_cities = Object.keys(stadester_obj);
    let angel_png;
    let cfg = global.population_Stadester_config;
    let clark_png;
    let raw_folder = options.raw_folder ? options.raw_folder : `${h1}/population_Stadester/`;
    
    let angel_file = path.join(raw_folder, "angel", "angel_subdivisions.png");
    let clark_file = path.join(raw_folder, "clark", "clark_subdivisions.png");
    
    if (fs.existsSync(angel_file))
      angel_png = pngjs.PNG.sync.read(fs.readFileSync(angel_file));
    if (fs.existsSync(clark_file))
      clark_png = pngjs.PNG.sync.read(fs.readFileSync(clark_file));
    
    for (let i = 0; i < all_cities.length; i++) {
      let city = stadester_obj[all_cities[i]];
      if (!city || !city.coords) continue;
      
      let lat = city.coords[0];
      let lng = city.coords[1];
      
      if (angel_png) {
        let px_coords = (typeof population_Stadester_rasters !== "undefined") ?
          population_Stadester_rasters.getCoordsPixel(city.coords, { height: angel_png.height, width: angel_png.width }) :
          [
            Math.min(angel_png.width - 1, Math.max(0, Math.floor(((lng + 180)/360)*angel_png.width))),
            Math.min(angel_png.height - 1, Math.max(0, Math.floor(((90 - lat)/180)*angel_png.height)))
          ];
        let px = px_coords[0];
        let py = px_coords[1];
        let idx = (py*angel_png.width + px)*4;
        let r = angel_png.data[idx], g = angel_png.data[idx + 1], b = angel_png.data[idx + 2];
        
        let all_regions = Object.keys(cfg.angel_regions);
        for (let x = 0; x < all_regions.length; x++) {
          let reg = cfg.angel_regions[all_regions[x]];
          if (reg.colour && reg.colour[0] === r && reg.colour[1] === g && reg.colour[2] === b) {
            city.angel_region = all_regions[x];
            break;
          }
        }
      }
      
      if (clark_png) {
        let px_coords = (typeof population_Stadester_rasters !== "undefined") ?
          population_Stadester_rasters.getCoordsPixel(city.coords, { height: clark_png.height, width: clark_png.width }) :
          [
            Math.min(clark_png.width - 1, Math.max(0, Math.floor(((lng + 180)/360)*clark_png.width))),
            Math.min(clark_png.height - 1, Math.max(0, Math.floor(((90 - lat)/180)*clark_png.height)))
          ];
        let px = px_coords[0];
        let py = px_coords[1];
        let idx = (py*clark_png.width + px)*4;
        let r = clark_png.data[idx], g = clark_png.data[idx + 1], b = clark_png.data[idx + 2];
        
        let all_regions = Object.keys(cfg.clark_equations[1970] || {});
        for (let x = 0; x < all_regions.length; x++) {
          let reg_key = all_regions[x];
          let reg_cfg = cfg.regions[reg_key];
          if (reg_cfg && reg_cfg.colour && reg_cfg.colour[0] === r && reg_cfg.colour[1] === g && reg_cfg.colour[2] === b) {
            city.clark_region = reg_key;
            break;
          }
        }
      }
      
      if (!city.angel_region) city.angel_region = "europe";
      if (!city.clark_region) city.clark_region = "europe";
    }
    
    //Return statement
    return stadester_obj;
  };
  
  /**
   * Returns a map of city keys to rank ordinals of population density for a specific year.
   * @alias population_Stadester_density.calculateDensityOrdinalsForYear
   * 
   * @param {number} arg0_year
   * @param {Object} arg1_stadester_obj
   * 
   * @returns {Object}
   */
  population_Stadester_density.calculateDensityOrdinalsForYear = function (arg0_year, arg1_stadester_obj) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let stadester_obj = arg1_stadester_obj;
    
    //Declare local instance variables
    let all_cities = Object.keys(stadester_obj);
    let density_list = [];
    let ordinals_obj = {};
    
    for (let i = 0; i < all_cities.length; i++) {
      let city = stadester_obj[all_cities[i]];
      if (city && city.density) {
        let d_keys = city._density_keys || Object.keys(city.density).map(Number).sort((a, b) => a - b);
        let cur_density = null;
        for (let x = 0; x < d_keys.length; x++)
          if (d_keys[x] <= year) cur_density = city.density[d_keys[x]];
        if (cur_density !== null && cur_density > 0)
          density_list.push({ key: city.key, density: cur_density });
      }
    }
    
    density_list.sort((a, b) => b.density - a.density);
    for (let i = 0; i < density_list.length; i++)
      ordinals_obj[density_list[i].key] = i + 1;
    
    //Return statement
    return ordinals_obj;
  };
  
  /**
   * Precomputes regional walkability ratios across years 1800-2000.
   * @alias population_Stadester_density.getWalkabilityRatioObject
   * 
   * @returns {Object}
   */
  population_Stadester_density.getWalkabilityRatioObject = function () {
    //Declare local instance variables
    let angel_regions = JSON.parse(JSON.stringify(global.population_Stadester_config.angel_regions));
    let cfg = global.population_Stadester_config;
    let region_keys = Object.keys(angel_regions);
    
    for (let i = 0; i < region_keys.length; i++) {
      let reg = angel_regions[region_keys[i]];
      let city_keys = Object.keys(reg.cities);
      let reg_walkability = {};
      
      for (let x = 0; x < city_keys.length; x++) {
        let city = reg.cities[city_keys[x]];
        let c_keys = Object.keys(city).map(Number).sort((a, b) => a - b);
        let years_to_interp = [];
        for (let y = c_keys[0]; y <= c_keys[c_keys.length - 1]; y++) years_to_interp.push(y);
        city = population_Stadester_uud.cubicSplineInterpolationObject(city, { years: years_to_interp });
        for (let y = c_keys[c_keys.length - 1]; y <= cfg.end_year; y++)
          city[y] = city[c_keys[c_keys.length - 1]];
        reg.cities[city_keys[x]] = city;
      }
      
      for (let yr = cfg.baseline_year; yr <= cfg.end_year; yr++) {
        let sum = 0;
        let count = 0;
        for (let x = 0; x < city_keys.length; x++) {
          let v = reg.cities[city_keys[x]][yr];
          if (v !== undefined) { sum += v; count++; }
        }
        let mean = (count > 0) ? sum/count : 1.0;
        reg_walkability[yr] = Math.max(0.1, 1 - (mean - 1));
      }
      reg.walkability_ratio = reg_walkability;
    }
    
    //Return statement
    return angel_regions;
  };
  
  /**
   * Imputes Clark centre density parameters (A) for each city based on rank ordinals and Angel trend.
   * @alias population_Stadester_density.calculateCitiesCentreDensities
   * 
   * @param {Object} arg0_stadester_obj
   * 
   * @returns {Object}
   */
  population_Stadester_density.calculateCitiesCentreDensities = function (arg0_stadester_obj) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    
    //Declare local instance variables
    let all_cities = Object.keys(stadester_obj);
    let cfg = global.population_Stadester_config;
    let city_timeline_list = [];
    let global_density = population_Stadester_density.getGlobalPopulationDensityObject();
    
    //Prepare sorted density keys and timelines for each city once
    for (let i = 0; i < all_cities.length; i++) {
      let city = stadester_obj[all_cities[i]];
      if (city) city.centre_density = {};
      if (city && city.density) {
        let keys = Object.keys(city.density).map(Number).sort((a, b) => a - b);
        let vals = [];
        for (let x = 0; x < keys.length; x++) vals.push(city.density[keys[x]]);
        city_timeline_list.push({
          city: city,
          cur_idx: -1,
          cur_val: null,
          keys: keys,
          vals: vals
        });
      }
    }
    
    //Chronological sweep across years assigning centre densities directly without retaining per-year ordinal maps
    for (let yr = cfg.baseline_year; yr <= cfg.end_year; yr++) {
      let density_list = [];
      let g_dens = global_density[yr] || 180;
      
      for (let i = 0; i < city_timeline_list.length; i++) {
        let entry = city_timeline_list[i];
        while (entry.cur_idx + 1 < entry.keys.length && entry.keys[entry.cur_idx + 1] <= yr) {
          entry.cur_idx++;
          entry.cur_val = entry.vals[entry.cur_idx];
        }
        if (entry.cur_val !== null && entry.cur_val > 0)
          density_list.push({ city: entry.city, density: entry.cur_val });
      }
      
      density_list.sort((a, b) => b.density - a.density);
      let total_cities = density_list.length;
      for (let i = 0; i < total_cities; i++) {
        let local_city = density_list[i].city;
        if (!local_city.population || local_city.population[yr] === undefined) continue;
        let rank = i + 1;
        let a_val = 130*Math.log(total_cities/120/rank) + 506 + g_dens;
        local_city.centre_density[yr] = Math.max(10, a_val);
      }
    }
    
    //Return statement
    return stadester_obj;
  };
  
  /**
   * Sub-samples pixel area inside annulus ring.
   * @alias population_Stadester_density.getPixelFractionInRing
   * 
   * @param {Array<number>} arg0_city_coords
   * @param {Array<number>} arg1_pixel_coords
   * @param {number} arg2_inner_radius
   * @param {number} arg3_outer_radius
   * 
   * @returns {number}
   */
  population_Stadester_density.getPixelFractionInRing = function (arg0_city_coords, arg1_pixel_coords, arg2_inner_radius, arg3_outer_radius) {
    //Convert from parameters
    let city_coords = arg0_city_coords;
    let pixel_coords = arg1_pixel_coords;
    let inner_radius = arg2_inner_radius;
    let outer_radius = arg3_outer_radius;
    
    //Declare local instance variables
    let cfg = global.population_Stadester_config;
    let d_lat_km;
    let d_lng_km;
    let diag;
    let dist;
    let half = cfg.pixel_deg/2;
    let inside = 0;
    let subsamples = 10;
    let total = subsamples*subsamples;
    
    //Fast envelope bounding check
    dist = population_Stadester_density.equirectangularDistance(city_coords, pixel_coords);
    d_lat_km = cfg.pixel_deg*111.32;
    d_lng_km = cfg.pixel_deg*111.32*Math.cos(pixel_coords[0]*Math.PI/180);
    diag = 0.5*Math.sqrt(d_lat_km*d_lat_km + d_lng_km*d_lng_km)*1.05;
    
    if (dist + diag < outer_radius && dist - diag >= inner_radius) return 1.0;
    if (dist - diag >= outer_radius || dist + diag < inner_radius) return 0.0;
    
    for (let i = 0; i < subsamples; i++) {
      for (let x = 0; x < subsamples; x++) {
        let d_lat = (i + 0.5)/subsamples*cfg.pixel_deg - half;
        let d_lng = (x + 0.5)/subsamples*cfg.pixel_deg - half;
        let d = population_Stadester_density.equirectangularDistance(city_coords, [pixel_coords[0] + d_lat, pixel_coords[1] + d_lng]);
        if (d >= inner_radius && d < outer_radius) inside++;
      }
    }
    
    //Return statement
    return inside/total;
  };
  
  /**
   * Retrieves grid of decimal coordinates surrounding city within max distance.
   * @alias population_Stadester_density.getRasterPixels
   * 
   * @param {Object} arg0_city_obj
   * @param {number} arg1_max_distance_km
   * 
   * @returns {Array<Array<number>>}
   */
  population_Stadester_density.getRasterPixels = function (arg0_city_obj, arg1_max_distance_km) {
    //Convert from parameters
    let city_obj = arg0_city_obj;
    let max_distance_km = parseFloat(arg1_max_distance_km);
    
    //Declare local instance variables
    let cfg = global.population_Stadester_config;
    let delta_deg = max_distance_km*(1/111.32);
    let pixels = [];
    
    for (let lat = city_obj.coords[0] - delta_deg; lat <= city_obj.coords[0] + delta_deg; lat += cfg.pixel_deg)
      for (let lng = city_obj.coords[1] - delta_deg; lng <= city_obj.coords[1] + delta_deg; lng += cfg.pixel_deg)
        pixels.push([lat, lng]);
    
    //Return statement
    return pixels;
  };
  
  /**
   * Computes concentric pixel ring populations using regional Clark equations.
   * @alias population_Stadester_density.getCityPopulationByPixelRing
   * 
   * @param {Object} arg0_city_obj
   * @param {number} arg1_year
   * @param {Object} [arg2_options]
   * 
   * @returns {Array<number>}
   */
  population_Stadester_density.getCityPopulationByPixelRing = function (arg0_city_obj, arg1_year, arg2_options) {
    //Convert from parameters
    let city_obj = arg0_city_obj;
    let year = parseInt(arg1_year);
    let options = (arg2_options) ? arg2_options : {};
    
    //Declare local instance variables
    let A;
    let area;
    let b = 1.0;
    let cfg = global.population_Stadester_config;
    let clark_equations = cfg.clark_equations;
    let max_distance_km;
    let max_ring;
    let pixel_width_km;
    let population;
    let raster_pixels;
    let results;
    let walkability_ratio_obj = options.walkability_ratio_obj;
    
    //Guard clauses
    if (!city_obj || !city_obj.population || city_obj.population[year] === undefined) return [];
    population = parseFloat(city_obj.population[year]);
    area = city_obj.area ? parseFloat(city_obj.area[year]) : 0;
    if (isNaN(population) || population <= 0 || isNaN(area) || area <= 0) return [Math.max(0, population || 0)];
    
    A = (city_obj.centre_density && city_obj.centre_density[year]) ?
      parseFloat(city_obj.centre_density[year])*100 : 18000;
    
    if (walkability_ratio_obj && city_obj.angel_region && walkability_ratio_obj[city_obj.angel_region])
      b = walkability_ratio_obj[city_obj.angel_region].walkability_ratio[year] || 1.0;
    
    max_distance_km = Math.sqrt(area/Math.PI);
    pixel_width_km = population_Stadester_density.equirectangularDistance(city_obj.coords, [
      city_obj.coords[0], city_obj.coords[1] + cfg.pixel_deg
    ]);
    max_ring = Math.max(1, Math.ceil(max_distance_km/pixel_width_km));
    raster_pixels = population_Stadester_density.getRasterPixels(city_obj, max_distance_km);
    results = new Array(max_ring).fill(0);
    
    for (let i = 0; i < raster_pixels.length; i++) {
      let local_pixel = raster_pixels[i];
      let dist = population_Stadester_density.equirectangularDistance(city_obj.coords, local_pixel);
      let ring_idx = Math.floor(dist/pixel_width_km);
      if (ring_idx < 0 || ring_idx >= max_ring) continue;
      
      let fraction = population_Stadester_density.getPixelFractionInRing(city_obj.coords, local_pixel, ring_idx*pixel_width_km, (ring_idx + 1)*pixel_width_km);
      if (fraction <= 0) continue;
      
      let pixel_area = population_Stadester_density.getPixelAreaAtLatitude(local_pixel[0]);
      let pixel_density;
      
      if (year >= 1970 && clark_equations[1970] && clark_equations[1970][city_obj.clark_region]) {
        pixel_density = clark_equations[1970][city_obj.clark_region]({ A: A/100, b: b, x: dist });
      } else {
        pixel_density = clark_equations[1800].default({ A: A/100, b: b, x: dist });
      }
      
      results[ring_idx] += fraction*pixel_area*pixel_density;
    }
    
    let raw_sum = results.reduce((acc, v) => acc + v, 0);
    let scalar = (raw_sum > 0) ? (population/raw_sum) : 1;
    
    //Return statement
    return results.map(v => Math.round(v*scalar));
  };
  
  /**
   * Evaluates and caches radial buffers across all cities and years.
   * @alias population_Stadester_density.cacheRadialBuffers
   * 
   * @param {Object} arg0_stadester_obj
   * 
   * @returns {Object}
   */
  population_Stadester_density.cacheRadialBuffers = function (arg0_stadester_obj) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    
    //Declare local instance variables
    let all_cities = Object.keys(stadester_obj);
    let cfg = global.population_Stadester_config;
    let walkability_ratio_obj = population_Stadester_density.getWalkabilityRatioObject();
    
    console.log(`- Caching radial buffers for ${all_cities.length} cities...`);
    for (let i = 0; i < all_cities.length; i++) {
      let city = stadester_obj[all_cities[i]];
      if (!city || !city.area || !city.coords || !city.population) continue;
      
      let area_years = Object.keys(city.area).map(Number).sort((a, b) => a - b);
      if (area_years.length === 0) continue;
      
      let px_area = population_Stadester_density.getPixelAreaAtLatitude(city.coords[0]);
      
      for (let yr = cfg.baseline_year; yr <= cfg.end_year; yr++) {
        if (city.population[yr]) {
          let city_area = parseFloat(city.area[yr]) || 0;
          let pixel_size = Math.ceil(city_area/px_area);
          
          if (!city.radial_buffers) city.radial_buffers = {};
          if (pixel_size > 1) {
            city.radial_buffers[yr] = population_Stadester_density.getCityPopulationByPixelRing(city, yr, {
              walkability_ratio_obj: walkability_ratio_obj
            });
            if (isNaN(city.radial_buffers[yr][0]))
              city.radial_buffers[yr] = [parseFloat(city.population[yr]) || 0];
          } else {
            city.radial_buffers[yr] = [parseFloat(city.population[yr]) || 0];
          }
        }
      }
    }
    
    //Return statement
    return stadester_obj;
  };
  
  /**
   * Master pipeline execution for city area and density computations.
   * @alias population_Stadester_density.processCitiesAreas
   * 
   * @param {Object} arg0_stadester_obj
   * @param {Object} [arg1_options]
   * 
   * @returns {Object}
   */
  population_Stadester_density.processCitiesAreas = function (arg0_stadester_obj, arg1_options) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    console.log(`- Estimating baseline city areas...`);
    stadester_obj = population_Stadester_density.estimateBaselineCityAreas(stadester_obj);
    
    console.log(`- Calculating remainder city areas...`);
    stadester_obj = population_Stadester_density.calculateRemainderCityAreas(stadester_obj);
    
    console.log(`- Fixing city areas...`);
    stadester_obj = population_Stadester_density.fixCityAreas(stadester_obj);
    
    console.log(`- Calculating city densities...`);
    stadester_obj = population_Stadester_density.calculateCityDensities(stadester_obj);
    
    console.log(`- Assigning regions to cities...`);
    stadester_obj = population_Stadester_density.assignRegionsToCities(stadester_obj, options);
    
    console.log(`- Calculating city centre densities...`);
    stadester_obj = population_Stadester_density.calculateCitiesCentreDensities(stadester_obj);
    
    //Return statement
    return stadester_obj;
  };
}
