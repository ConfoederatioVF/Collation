//Initialise functions
{
  if (!global.population_Stadester_uud) global.population_Stadester_uud = {};
  if (!global.cubic_spline) try { global.cubic_spline = require("cubic-spline"); } catch (e) {}
  
  /**
   * Evaluates cubic spline interpolation between x_values and y_values.
   * @alias population_Stadester_uud.cubicSplineInterpolation
   * 
   * @param {Array<number>} arg0_x_values
   * @param {Array<number>} arg1_y_values
   * @param {number} arg2_x_to_interpolate
   * 
   * @returns {number}
   */
  population_Stadester_uud.cubicSplineInterpolation = function (arg0_x_values, arg1_y_values, arg2_x_to_interpolate) {
    //Convert from parameters
    let x_values = Array.isArray(arg0_x_values) ? arg0_x_values : [arg0_x_values];
    let y_values = Array.isArray(arg1_y_values) ? arg1_y_values : [arg1_y_values];
    let x_to_interpolate = parseInt(arg2_x_to_interpolate);
    
    //Declare local instance variables
    let interpolated_value;
    let interpolation;
    let log_interpolated;
    let lower_bound;
    let next_known_value = Infinity;
    let prev_known_value = -Infinity;
    let upper_bound;
    
    //Guard clauses
    if (x_values.length < 2) return y_values[0] || 0;
    
    y_values = y_values.map((y) => (y > 0) ? Math.log(y) : Math.log(1e-6));
    interpolation = new cubic_spline(x_values, y_values);
    log_interpolated = interpolation.at(x_to_interpolate);
    interpolated_value = Math.exp(log_interpolated);
    
    for (let i = 0; i < x_values.length; i++) {
      if (x_values[i] <= x_to_interpolate)
        prev_known_value = Math.exp(y_values[i]);
      if (x_values[i] >= x_to_interpolate) {
        next_known_value = Math.exp(y_values[i]);
        break;
      }
    }
    
    lower_bound = Math.min(prev_known_value, next_known_value);
    upper_bound = Math.max(prev_known_value, next_known_value);
    interpolated_value = Math.max(lower_bound, Math.min(interpolated_value, upper_bound));
    
    //Return statement
    return interpolated_value;
  };
  
  /**
   * Cubic spline interpolates missing year values on a city population dictionary.
   * @alias population_Stadester_uud.cubicSplineInterpolationObject
   * 
   * @param {Object} arg0_object
   * @param {Object} [arg1_options]
   * 
   * @returns {Object}
   */
  population_Stadester_uud.cubicSplineInterpolationObject = function (arg0_object, arg1_options) {
    //Convert from parameters
    let object = arg0_object;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let all_keys;
    let max_year;
    let min_year;
    let values = [];
    let years = [];
    
    //Guard clauses
    if (!object) return {};
    all_keys = Object.keys(object).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b);
    if (all_keys.length < 2) return object;
    
    for (let i = 0; i < all_keys.length; i++) {
      let val = Array.isArray(object[all_keys[i]]) ? object[all_keys[i]][0] : object[all_keys[i]];
      years.push(all_keys[i]);
      values.push(parseFloat(val));
    }
    
    min_year = years[0];
    max_year = years[years.length - 1];
    
    let target_years = (options.years || options.all_years) ? (options.years || options.all_years) : years;
    for (let i = 0; i < target_years.length; i++) {
      let cur_year = target_years[i];
      if (cur_year >= min_year && cur_year <= max_year)
        object[cur_year] = population_Stadester_uud.cubicSplineInterpolation(years, values, cur_year);
    }
    
    //Return statement
    return object;
  };
  
  /**
   * Linear interpolates missing year values on a city population dictionary.
   * @alias population_Stadester_uud.linearInterpolationObject
   * 
   * @param {Object} arg0_object
   * @param {Object} [arg1_options]
   * 
   * @returns {Object}
   */
  population_Stadester_uud.linearInterpolationObject = function (arg0_object, arg1_options) {
    //Convert from parameters
    let object = arg0_object;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let all_keys;
    let max_year;
    let min_year;
    let values = [];
    let years = [];
    
    //Guard clauses
    if (!object) return {};
    all_keys = Object.keys(object).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b);
    if (all_keys.length < 2) return object;
    
    for (let i = 0; i < all_keys.length; i++) {
      let val = Array.isArray(object[all_keys[i]]) ? object[all_keys[i]][0] : object[all_keys[i]];
      years.push(all_keys[i]);
      values.push(parseFloat(val));
    }
    
    min_year = years[0];
    max_year = years[years.length - 1];
    
    let target_years = (options.years || options.all_years) ? (options.years || options.all_years) : years;
    for (let i = 0; i < target_years.length; i++) {
      let cur_year = target_years[i];
      if (cur_year >= min_year && cur_year <= max_year) {
        let left_idx = 0;
        for (let j = 0; j < years.length - 1; j++)
          if (cur_year >= years[j] && cur_year <= years[j + 1]) {
            left_idx = j;
            break;
          }
        let x0 = years[left_idx], x1 = years[left_idx + 1];
        let y0 = values[left_idx], y1 = values[left_idx + 1];
        if (x1 === x0) {
          object[cur_year] = y0;
        } else {
          object[cur_year] = y0 + (y1 - y0)*((cur_year - x0)/(x1 - x0));
        }
      }
    }
    
    //Return statement
    return object;
  };
  
  /**
   * Computes geometric mean of an array of positive numbers.
   * @alias population_Stadester_uud.geometricMean
   * 
   * @param {Array<number>} arg0_values
   * 
   * @returns {number}
   */
  population_Stadester_uud.geometricMean = function (arg0_values) {
    //Convert from parameters
    let values = Array.isArray(arg0_values) ? arg0_values : [arg0_values];
    
    //Declare local instance variables
    let log_sum = 0;
    let valid_count = 0;
    
    for (let i = 0; i < values.length; i++) {
      let v = parseFloat(values[i]);
      if (v > 0) {
        log_sum += Math.log(v);
        valid_count++;
      }
    }
    
    //Return statement
    return (valid_count > 0) ? Math.exp(log_sum/valid_count) : 0;
  };
  
  /**
   * Computes signed weighted geometric mean for merging city populations.
   * @alias population_Stadester_uud.weightedGeometricMean
   * 
   * @param {Array<number>} arg0_values
   * 
   * @returns {number}
   */
  population_Stadester_uud.weightedGeometricMean = function (arg0_values) {
    //Convert from parameters
    let values = Array.isArray(arg0_values) ? arg0_values : [arg0_values];
    
    //Declare local instance variables
    let negative_gm = 0;
    let negatives = [];
    let positive_gm = 0;
    let positives = [];
    
    //Guard clauses
    if (values.length === 0) return 0;
    
    negatives = values.filter(v => v < 0).map(Math.abs);
    positives = values.filter(v => v > 0);
    if (negatives.length + positives.length === 0) return 0;
    
    if (negatives.length > 0) negative_gm = population_Stadester_uud.geometricMean(negatives);
    if (positives.length > 0) positive_gm = population_Stadester_uud.geometricMean(positives);
    
    //Return statement
    return (positives.length/values.length)*positive_gm - (negatives.length/values.length)*negative_gm;
  };
  
  /**
   * Returns Euclidean distance between two decimal degree coordinates.
   * @alias population_Stadester_uud.getCoordsDistance
   * 
   * @param {Array<number>} arg0_coords
   * @param {Array<number>} arg1_coords
   * 
   * @returns {number}
   */
  population_Stadester_uud.getCoordsDistance = function (arg0_coords, arg1_coords) {
    //Convert from parameters
    let coords = arg0_coords;
    let ot_coords = arg1_coords;
    
    //Declare local instance variables
    let d_lat = ot_coords[0] - coords[0];
    let d_lng = ot_coords[1] - coords[1];
    
    //Return statement
    return Math.sqrt(d_lat*d_lat + d_lng*d_lng);
  };
  
  /**
   * Computes Haversine distance in kilometres between two coordinates.
   * @alias population_Stadester_uud.haversineDistance
   * 
   * @param {Array<number>} arg0_coords
   * @param {Array<number>} arg1_coords
   * 
   * @returns {number}
   */
  population_Stadester_uud.haversineDistance = function (arg0_coords, arg1_coords) {
    //Convert from parameters
    let coords = arg0_coords;
    let ot_coords = arg1_coords;
    
    //Declare local instance variables
    let d_lat = (ot_coords[0] - coords[0])*Math.PI/180;
    let d_lng = (ot_coords[1] - coords[1])*Math.PI/180;
    let earth_radius = 6371;
    let lat1 = coords[0]*Math.PI/180;
    let lat2 = ot_coords[0]*Math.PI/180;
    
    let a = Math.sin(d_lat/2)*Math.sin(d_lat/2) +
      Math.sin(d_lng/2)*Math.sin(d_lng/2)*Math.cos(lat1)*Math.cos(lat2);
    let c = 2*Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    
    //Return statement
    return earth_radius*c;
  };
  
  //Load source loaders and city matching helpers
  if (typeof require !== "undefined")
    try { require(path.join(__dirname, "stadester_uud_sources.js")); } catch (e) {}
  
  /**
   * Initialises and merges raw urban datasets (Populstat, Chandler-Modelski, DeVries, Buringh) into UUD.
   * @alias population_Stadester_uud.initialiseUUD
   * 
   * @param {Object} [arg0_options]
   * 
   * @returns {Object}
   */
  population_Stadester_uud.initialiseUUD = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};
    
    //Declare local instance variables
    let cannot_be_merged = [{ name: "Gibraltar", ot_name: "Línea de la Concepción" }];
    let city_grid = new Map();
    let max_explicit_precision = 0.1;
    let raw_folder = options.raw_folder ? options.raw_folder : `${h1}/population_Stadester/`;
    let return_obj = {};
    
    let db_configs = {
      populstat: { data: population_Stadester_uud.getPopulstatObject(raw_folder) },
      chandler_modelski: { data: population_Stadester_uud.getWorldcitypopObject(raw_folder), is_metro: true, precision: 0.1, semantic_precision: 1 },
      devries: { data: population_Stadester_uud.getDeVriesCitiesObject(raw_folder), precision: 0.1, semantic_precision: 1 },
      buringh: { data: population_Stadester_uud.getBuringhObject(raw_folder), precision: 0.05, semantic_precision: 1 }
    };
    
    function getGridCells(coords, radius) {
      let min_lat = Math.floor(Number(coords[0]) - radius);
      let max_lat = Math.floor(Number(coords[0]) + radius);
      let min_lng = Math.floor(Number(coords[1]) - radius);
      let max_lng = Math.floor(Number(coords[1]) + radius);
      let cells = [];
      for (let lat = min_lat; lat <= max_lat; lat++)
        for (let lng = min_lng; lng <= max_lng; lng++)
          cells.push(`${lat},${lng}`);
      return cells;
    }
    
    function addToGrid(city) {
      if (!city || !city.coords) return;
      let cell = `${Math.floor(Number(city.coords[0]))},${Math.floor(Number(city.coords[1]))}`;
      if (!city_grid.has(cell)) city_grid.set(cell, new Set());
      city_grid.get(cell).add(city.key);
    }
    
    function isAgglomeration(city) {
      if (!city) return false;
      if (city.is_agglomeration) return true;
      if (city.name) {
        let lower = city.name.toLowerCase();
        if (lower.includes("agglomeration") || lower.includes("greater")) return true;
      }
      return false;
    }
    
    let all_db_keys = Object.keys(db_configs);
    for (let i = 0; i < all_db_keys.length; i++) {
      let local_db = db_configs[all_db_keys[i]];
      let all_local_cities = Object.keys(local_db.data);
      
      for (let x = 0; x < all_local_cities.length; x++) {
        let city_obj = local_db.data[all_local_cities[x]];
        if (city_obj) {
          if (!city_obj.key) city_obj.key = all_local_cities[x];
          if (!city_obj.original_names) {
            city_obj.original_names = [];
            if (city_obj.name) {
              let proc_n = population_Stadester_uud.processCityName(city_obj.name);
              if (proc_n) city_obj.original_names.push(proc_n);
            }
          }
        }
      }
      
      if (i === 0) {
        console.log(`- Fast-adding base databank: ${all_db_keys[i]} (${all_local_cities.length} cities)`);
        for (let x = 0; x < all_local_cities.length; x++) {
          let local_city = local_db.data[all_local_cities[x]];
          local_city.type = all_db_keys[i];
          return_obj[all_local_cities[x]] = local_city;
          addToGrid(local_city);
        }
        continue;
      }
      
      for (let x = 0; x < all_local_cities.length; x++) {
        let local_city = local_db.data[all_local_cities[x]];
        let was_merged = [false, undefined];
        
        if (local_city.coords) {
          let search_radius = Math.max(local_db.precision || 0, max_explicit_precision);
          let cells_to_check = getGridCells(local_city.coords, search_radius + 0.5);
          let candidate_keys = new Set();
          
          for (let c = 0; c < cells_to_check.length; c++) {
            let keys_in_cell = city_grid.get(cells_to_check[c]);
            if (keys_in_cell) keys_in_cell.forEach(k => candidate_keys.add(k));
          }
          
          let candidate_array = Array.from(candidate_keys);
          let best_match = undefined;
          let best_score = -Infinity;
          
          for (let y = 0; y < candidate_array.length; y++) {
            let local_uud_city = return_obj[candidate_array[y]];
            if (local_uud_city && local_uud_city.coords) {
              let local_distance = population_Stadester_uud.getCoordsDistance(local_uud_city.coords, local_city.coords);
              let is_exact_name = population_Stadester_uud.checkExactNameMatch(local_uud_city, local_city);
              let pop_check = population_Stadester_uud.isPopulationRatioValid(local_uud_city.population, local_city.population);
              let is_match = false;
              
              if (local_distance < 0.01 && pop_check.valid) {
                is_match = true;
              } else if (is_exact_name && local_distance <= search_radius && pop_check.valid) {
                is_match = true;
              } else if (local_db.precision && local_distance <= local_db.precision && pop_check.valid && (is_exact_name || pop_check.overlaps)) {
                is_match = true;
              }
              
              if (is_match) {
                let score = 0;
                if (is_exact_name) score += 10000;
                if (local_distance < 0.01) score += 5000;
                score += (1.0 - (local_distance/Math.max(0.01, search_radius)))*1000;
                let peak = population_Stadester_uud.getPeakPopulation(local_uud_city.population);
                score += (peak/100);
                if (score > best_score) {
                  best_score = score;
                  best_match = local_uud_city;
                }
              }
            }
          }
          
          if (best_match) was_merged = [true, best_match];
        }
        
        if (was_merged[0] && was_merged[1]) {
          let actual_city = was_merged[1];
          population_Stadester_uud.mergeCityEntries(actual_city, local_city, local_db.is_metro);
          actual_city.type = all_db_keys[i];
          return_obj[actual_city.key] = actual_city;
          if (all_local_cities[x] !== actual_city.key) delete return_obj[all_local_cities[x]];
        } else {
          local_city.type = all_db_keys[i];
          return_obj[all_local_cities[x]] = local_city;
          addToGrid(local_city);
        }
      }
    }
    
    //Flatten array entries by taking weighted geometric mean
    let all_return_keys = Object.keys(return_obj);
    for (let i = 0; i < all_return_keys.length; i++) {
      let local_city = return_obj[all_return_keys[i]];
      if (local_city.coords && Array.isArray(local_city.coords) && !isNaN(parseFloat(local_city.coords[0]))) {
        local_city.coords = [parseFloat(local_city.coords[0]), parseFloat(local_city.coords[1])];
        if (local_city.population) {
          let pop_keys = Object.keys(local_city.population);
          for (let x = 0; x < pop_keys.length; x++) {
            let val = local_city.population[pop_keys[x]];
            if (Array.isArray(val))
              local_city.population[pop_keys[x]] = (val.length > 1) ?
                population_Stadester_uud.weightedGeometricMean(val) : val[0];
          }
        }
      } else {
        delete return_obj[all_return_keys[i]];
      }
    }
    
    //Return statement
    return return_obj;
  };
  
  /**
   * Batch interpolates missing HYDE timeline years for all cities in UUD.
   * @alias population_Stadester_uud.interpolateUUD
   * 
   * @param {Object} arg0_uud_obj
   * @param {Object} [arg1_options]
   * 
   * @returns {Object}
   */
  population_Stadester_uud.interpolateUUD = function (arg0_uud_obj, arg1_options) {
    //Convert from parameters
    let uud_obj = arg0_uud_obj;
    let options = (arg1_options) ? arg1_options : {};
    
    //Initialise options
    if (!options.mode) options.mode = "linear";
    
    //Declare local instance variables
    let all_cities = Object.keys(uud_obj);
    let hyde_years = landuse_HYDE ? landuse_HYDE.sorted_hyde_years : [
      -3000, -2500, -2000, -1500, -1000, -900, -800, -700, -600, -500,
      -400, -300, -200, -100, 0, 100, 200, 300, 400, 500, 600, 700,
      800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1710,
      1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790, 1800, 1810, 1820,
      1830, 1840, 1850, 1860, 1870, 1880, 1890, 1900, 1910, 1920, 1930,
      1940, 1950, 1960, 1970, 1980, 1990, 2000, 2005, 2010, 2015, 2020
    ];
    let target_years = hyde_years.filter(y => y >= -3000 && y <= 2025);
    
    console.log(`- Interpolating UUD for ${all_cities.length} cities over years:`, target_years.length);
    for (let i = 0; i < all_cities.length; i++) {
      let local_city = uud_obj[all_cities[i]];
      if (!local_city || !local_city.population) continue;
      
      let valid_keys = Object.keys(local_city.population).filter(k => local_city.population[k] > 0);
      if (valid_keys.length >= 2) {
        let missing_years = target_years.filter(y => local_city.population[y] === undefined);
        if (missing_years.length > 0) {
          if (options.mode === "cubic") {
            local_city.population = population_Stadester_uud.cubicSplineInterpolationObject(local_city.population, { years: missing_years });
          } else {
            local_city.population = population_Stadester_uud.linearInterpolationObject(local_city.population, { years: missing_years });
          }
        }
      }
    }
    
    //Pad modern forward
    for (let i = 0; i < all_cities.length; i++) {
      let city = uud_obj[all_cities[i]];
      if (!city || !city.population) continue;
      let pop_keys = Object.keys(city.population).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b);
      if (pop_keys.length > 0) {
        let max_year = pop_keys[pop_keys.length - 1];
        let last_val = city.population[max_year];
        if (max_year >= 1975) {
          for (let j = 0; j < target_years.length; j++) {
            if (target_years[j] > max_year && target_years[j] <= 2025)
              city.population[target_years[j]] = last_val;
          }
        }
      }
    }
    
    //Return statement
    return uud_obj;
  };
  
  /**
   * Parses flat UUD into Stadestér cities format.
   * @alias population_Stadester_uud.parseUUDToStadester
   * 
   * @param {Object} arg0_uud_obj
   * 
   * @returns {Object}
   */
  population_Stadester_uud.parseUUDToStadester = function (arg0_uud_obj) {
    //Convert from parameters
    let uud_obj = arg0_uud_obj;
    
    //Declare local instance variables
    let all_cities = Object.keys(uud_obj);
    let return_obj = {};
    
    for (let i = 0; i < all_cities.length; i++) {
      let local_city = uud_obj[all_cities[i]];
      if (!local_city.country) {
        let split_key = all_cities[i].split("-");
        local_city.country = split_key[split_key.length - 1];
      }
      if (local_city.coords !== undefined)
        local_city.coords = [parseFloat(local_city.coords[0]), parseFloat(local_city.coords[1])];
      local_city.key = all_cities[i];
      if (!local_city.name) local_city.name = all_cities[i];
      population_Stadester_uud.repairGHSLCityName(local_city);
      if (local_city.name && (local_city.name.toLowerCase().includes("agglomeration") || local_city.name.toLowerCase().includes("greater")) && !local_city.is_agglomeration_of)
        local_city.is_agglomeration_of = population_Stadester_uud.processCityName(local_city.name);
      if (local_city.name && local_city.name.includes(":")) continue;
      return_obj[all_cities[i]] = local_city;
    }
    
    //Return statement
    return return_obj;
  };
  
  /**
   * Flattens agglomerations by subtracting city proper populations from metropolitan totals.
   * @alias population_Stadester_uud.flattenStadesterMetros
   * 
   * @param {Object} arg0_stadester_obj
   * 
   * @returns {Object}
   */
  population_Stadester_uud.flattenStadesterMetros = function (arg0_stadester_obj) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    
    //Declare local instance variables
    let all_cities = Object.keys(stadester_obj);
    let cell_size = 2.5;
    let grid = new Map();
    
    for (let i = 0; i < all_cities.length; i++) {
      let city = stadester_obj[all_cities[i]];
      let is_agg = city.is_agglomeration || (city.name && (city.name.toLowerCase().includes("agglomeration") || city.name.toLowerCase().includes("greater")));
      if (is_agg && city.coords) {
        let cell = `${Math.floor(city.coords[0]/cell_size)},${Math.floor(city.coords[1]/cell_size)}`;
        if (!grid.has(cell)) grid.set(cell, []);
        grid.get(cell).push(city);
      }
    }
    
    for (let i = 0; i < all_cities.length; i++) {
      let local_city = stadester_obj[all_cities[i]];
      if (!local_city || !local_city.coords) continue;
      let is_agg = local_city.is_agglomeration || (local_city.name && (local_city.name.toLowerCase().includes("agglomeration") || local_city.name.toLowerCase().includes("greater")));
      if (is_agg) continue;
      
      let cx = Math.floor(local_city.coords[0]/cell_size);
      let cy = Math.floor(local_city.coords[1]/cell_size);
      let metro_match = null;
      
      for (let dx = -1; dx <= 1; dx++) {
        for (let dy = -1; dy <= 1; dy++) {
          let cell = `${cx + dx},${cy + dy}`;
          let aggs = grid.get(cell);
          if (aggs) {
            for (let a = 0; a < aggs.length; a++) {
              let agg = aggs[a];
              if (agg.key === local_city.key) continue;
              if (population_Stadester_uud.haversineDistance(agg.coords, local_city.coords) <= 250) {
                let name_a = population_Stadester_uud.processCityName(local_city.name);
                let name_b = population_Stadester_uud.processCityName(agg.name);
                if (name_a && name_b && (name_a === name_b || name_b.includes(name_a) || name_a.includes(name_b))) {
                  metro_match = agg;
                  break;
                }
              }
            }
          }
          if (metro_match) break;
        }
        if (metro_match) break;
      }
      
      if (metro_match && local_city.population && metro_match.population) {
        let pop_keys = Object.keys(local_city.population);
        for (let x = 0; x < pop_keys.length; x++) {
          let yr = pop_keys[x];
          let agg_pop = parseFloat(metro_match.population[yr]);
          let city_pop = parseFloat(local_city.population[yr]);
          if (!isNaN(agg_pop) && !isNaN(city_pop)) {
            local_city.metro_key = metro_match.key;
            metro_match.population[yr] = Math.max(0, agg_pop - city_pop);
          }
        }
      }
    }
    
    //Return statement
    return stadester_obj;
  };
  
  /**
   * Applies manual clerical and geolocation error fixes.
   * @alias population_Stadester_uud.fixStadesterErrors
   * 
   * @param {Object} arg0_stadester_obj
   * 
   * @returns {Object}
   */
  population_Stadester_uud.fixStadesterErrors = function (arg0_stadester_obj) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    
    //Declare local instance variables
    let all_cities = Object.keys(stadester_obj);
    
    try {
      if (stadester_obj["Washington-United States"])
        stadester_obj["Washington-United States"].coords = [38.906727075772245, -77.0366352170292];
      
      if (stadester_obj["Cardiff-United Kingdom"] && stadester_obj["Rhondda-United Kingdom"]) {
        let cardiff_pop = JSON.parse(JSON.stringify(stadester_obj["Cardiff-United Kingdom"].population));
        let rhondda_pop = JSON.parse(JSON.stringify(stadester_obj["Rhondda-United Kingdom"].population));
        stadester_obj["Cardiff-United Kingdom"].population = rhondda_pop;
        stadester_obj["Rhondda-United Kingdom"].population = cardiff_pop;
      }
      delete stadester_obj["Minneapolis-United States of America"];
    } catch (e) {
      console.warn(e);
    }
    
    for (let i = 0; i < all_cities.length; i++) {
      let city = stadester_obj[all_cities[i]];
      if (city && city.population) {
        let pop_keys = Object.keys(city.population);
        for (let x = 0; x < pop_keys.length; x++) {
          let val = city.population[pop_keys[x]];
          city.population[pop_keys[x]] = Math.max(0, Math.round(val));
        }
      }
    }
    
    population_Stadester_uud.repairGHSLCityNames(stadester_obj);
    
    //Return statement
    return stadester_obj;
  };
  
  /**
   * Generates a unified Stadestér GHSL dataset combining historical Stadestér entries and modern GHSL clusters.
   * All GHSL city names are repaired using the GHSL source file.
   * @alias population_Stadester_uud.getStadesterGHSLObject
   * 
   * @param {Object} [arg0_options]
   *  @param {string} [arg0_options.raw_folder]
   *  @param {Object} [arg0_options.stadester_obj]
   * 
   * @returns {Object}
   */
  population_Stadester_uud.getStadesterGHSLObject = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};
    
    //Declare local instance variables
    let all_stadester_cities;
    let cutoff_year = (global.population_Stadester_config && global.population_Stadester_config.cutoff_year) ?
      global.population_Stadester_config.cutoff_year : 1975;
    let raw_folder = options.raw_folder ? options.raw_folder : `${h1}/population_Stadester/`;
    let return_obj = {};
    let stadester_obj = options.stadester_obj;
    
    //Function body
    population_Stadester_uud.loadGHSLCsvNames();
    
    if (!stadester_obj) {
      let final_file = path.join(raw_folder, "uud", "stadester.json");
      if (fs.existsSync(final_file))
        stadester_obj = JSON.parse(fs.readFileSync(final_file, "utf8"));
    }
    
    if (stadester_obj) {
      all_stadester_cities = Object.keys(stadester_obj);
      for (let i = 0; i < all_stadester_cities.length; i++) {
        let local_city = JSON.parse(JSON.stringify(stadester_obj[all_stadester_cities[i]]));
        if (!local_city.coords) continue;
        
        let keys_to_truncate = ["area", "density", "population"];
        for (let x = 0; x < keys_to_truncate.length; x++) {
          if (local_city[keys_to_truncate[x]]) {
            let year_keys = Object.keys(local_city[keys_to_truncate[x]]);
            for (let y = 0; y < year_keys.length; y++) {
              if (parseInt(year_keys[y]) >= cutoff_year)
                delete local_city[keys_to_truncate[x]][year_keys[y]];
            }
          }
        }
        
        population_Stadester_uud.repairGHSLCityName(local_city);
        return_obj[`stadester-${all_stadester_cities[i]}`] = local_city;
      }
    }
    
    //Return statement
    return population_Stadester_uud.repairGHSLCityNames(return_obj);
  };
}
