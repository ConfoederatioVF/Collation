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
              
              if (local_distance < 0.01 && (is_exact_name || pop_check.valid)) {
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
    
    //Inject manual records into UUD database after initial merging
    if (!return_obj["Vaduz-Liechtenstein"])
      return_obj["Vaduz-Liechtenstein"] = {
        name: "Vaduz",
        country: "Liechtenstein",
        elevation: 455,
        key: "Vaduz-Liechtenstein",
        coords: [47.141, 9.521],
        original_names: ["vaduz"],
        other_names: ["Vaduz"],
        population: {
          "1400": 300,
          "1500": 400,
          "1600": 500,
          "1700": 600,
          "1800": 800,
          "1900": 1000,
          "1910": 1300,
          "1920": 1400,
          "1930": 1600,
          "1940": 2000,
          "1950": 2700,
          "1960": 3400,
          "1970": 3900,
          "1980": 4600,
          "1990": 4900,
          "2000": 5000,
          "2010": 5200,
          "2020": 5700
        },
        type: "manual"
      };
    
    //Ensure Lamphun geolocation is fixed to authoritative coordinates
    if (return_obj["Lamphun-Thailand"])
      return_obj["Lamphun-Thailand"].coords = [18.5744357, 99.00369719999999];
    
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
   * Removes duplicate city entries sharing coordinates and merges their historical populations.
   * @alias population_Stadester_uud.removeStadesterDuplicates
   * 
   * @param {Object} arg0_stadester_obj
   * 
   * @returns {Object}
   */
  population_Stadester_uud.removeStadesterDuplicates = function (arg0_stadester_obj) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    
    //Declare local instance variables
    let grouped = {};
    let result = {};
    
    for (let key in stadester_obj) {
      let city = stadester_obj[key];
      if (!city || !Array.isArray(city.coords) || city.coords.length < 2) continue;
      let lat = Number(city.coords[0]).toFixed(3);
      let lng = Number(city.coords[1]).toFixed(3);
      
      let is_agg = (city.is_agglomeration || (city.name && (city.name.toLowerCase().includes("agglomeration") || city.name.toLowerCase().includes("greater")))) ? "agg" : "city";
      let group_key = `${lat},${lng},${is_agg}`;
      
      if (!grouped[group_key]) grouped[group_key] = [];
      grouped[group_key].push({ key: key, city: city });
    }
    
    for (let group_key in grouped) {
      let group = grouped[group_key];
      group.sort((a, b) => {
        let num_years_a = (a.city && a.city.population) ? Object.keys(a.city.population).length : 0;
        let num_years_b = (b.city && b.city.population) ? Object.keys(b.city.population).length : 0;
        return num_years_b - num_years_a;
      });
      
      let best = group[0].city;
      if (!best || !best.population) continue;
      
      let had_merged_keys = false;
      for (let i = 1; i < group.length; i++) {
        let duplicate = group[i].city;
        if (!duplicate || !duplicate.population) continue;
        for (let pop_key in duplicate.population) {
          if (!best.population.hasOwnProperty(pop_key)) {
            best.population[pop_key] = duplicate.population[pop_key];
            had_merged_keys = true;
          }
        }
      }
      
      //Re-interpolate across all keys if duplicate points were incorporated to avoid sawtooth drops
      if (had_merged_keys) {
        let all_pop_keys = Object.keys(best.population).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b);
        if (all_pop_keys.length >= 2) {
          best.population = population_Stadester_uud.linearInterpolationObject(best.population, {
            years: all_pop_keys
          });
        }
      }
      
      result[group[0].key] = best;
    }
    
    //Return statement
    return result;
  };

  /**
   * Flattens agglomerations by subtracting city proper populations from metropolitan totals.
   * @alias population_Stadester_uud.flattenStadesterMetros
   * 
   * @param {Object} arg0_stadester_obj
   * @param {boolean} [arg1_do_not_flatten_metros=false]
   * 
   * @returns {Object}
   */
  population_Stadester_uud.flattenStadesterMetros = function (arg0_stadester_obj, arg1_do_not_flatten_metros) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    let do_not_flatten_metros = arg1_do_not_flatten_metros;
    
    //Deduplicate and merge population first
    stadester_obj = population_Stadester_uud.removeStadesterDuplicates(stadester_obj);
    if (do_not_flatten_metros) return stadester_obj;
    
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
      
      //Lamphun, Thailand geolocation fix
      if (stadester_obj["Lamphun-Thailand"])
        stadester_obj["Lamphun-Thailand"].coords = [18.5744357, 99.00369719999999];
      
      //Inject Vaduz, Liechtenstein if missing
      if (!stadester_obj["Vaduz-Liechtenstein"])
        stadester_obj["Vaduz-Liechtenstein"] = {
          name: "Vaduz",
          country: "Liechtenstein",
          elevation: 455,
          key: "Vaduz-Liechtenstein",
          coords: [47.141, 9.521],
          original_names: ["vaduz"],
          other_names: ["Vaduz"],
          population: {
            "1400": 300,
            "1500": 400,
            "1600": 500,
            "1700": 600,
            "1800": 800,
            "1900": 1000,
            "1910": 1300,
            "1920": 1400,
            "1930": 1600,
            "1940": 2000,
            "1950": 2700,
            "1960": 3400,
            "1970": 3900,
            "1980": 4600,
            "1990": 4900,
            "2000": 5000,
            "2010": 5200,
            "2020": 5700
          },
          type: "manual"
        };
      
      if (stadester_obj["Cardiff-United Kingdom"] && stadester_obj["Rhondda-United Kingdom"]) {
        let cardiff_pop = JSON.parse(JSON.stringify(stadester_obj["Cardiff-United Kingdom"].population));
        let rhondda_pop = JSON.parse(JSON.stringify(stadester_obj["Rhondda-United Kingdom"].population));
        stadester_obj["Cardiff-United Kingdom"].population = rhondda_pop;
        stadester_obj["Rhondda-United Kingdom"].population = cardiff_pop;
      }
      delete stadester_obj["Minneapolis-United States of America"];
      
      //Taipei anachronistic antiquity cleanup
      let taipei_names = ["T'aipei-Taiwan", "Taipei-Taiwan", "Taipei-China"];
      for (let t = 0; t < taipei_names.length; t++) {
        let t_city = stadester_obj[taipei_names[t]];
        if (t_city) {
          let props = ["area", "density", "population", "rni", "radial_buffers", "centre_density"];
          for (let p = 0; p < props.length; p++) {
            if (t_city[props[p]]) {
              let yr_keys = Object.keys(t_city[props[p]]);
              for (let y = 0; y < yr_keys.length; y++) {
                if (parseInt(yr_keys[y]) < 1700)
                  delete t_city[props[p]][yr_keys[y]];
              }
            }
          }
        }
      }
      
      //Maydanets Ukrainian archaeological megasite lapse
      let maydanets_names = ["Maydanets-Ukraine", "Maidanets-Ukraine"];
      for (let m = 0; m < maydanets_names.length; m++) {
        let m_city = stadester_obj[maydanets_names[m]];
        if (m_city) {
          let props = ["area", "density", "population", "rni", "radial_buffers", "centre_density"];
          for (let p = 0; p < props.length; p++) {
            if (m_city[props[p]]) {
              let yr_keys = Object.keys(m_city[props[p]]);
              for (let y = 0; y < yr_keys.length; y++) {
                if (parseInt(yr_keys[y]) >= 0)
                  delete m_city[props[p]][yr_keys[y]];
              }
            }
          }
          if (m_city.population) {
            m_city.population["-999"] = 0;
          }
        }
      }
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
   * All GHSL and historical city names are repaired, and .region strings are assigned via Voronoi sampling.
   * @alias population_Stadester_uud.getStadesterGHSLObject
   * 
   * @param {Object} [arg0_options]
   *  @param {string} [arg0_options.ghsl_file]
   *  @param {Object} [arg0_options.ghsl_obj]
   *  @param {string} [arg0_options.raw_folder]
   *  @param {Object} [arg0_options.stadester_obj]
   *  @param {string} [arg0_options.voronoi_file]
   * 
   * @returns {Object}
   */
  population_Stadester_uud.getStadesterGHSLObject = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};
    
    //Declare local instance variables
    let all_ghsl_cities;
    let all_region_keys;
    let all_return_keys;
    let all_stadester_cities;
    let colour_to_region = {};
    let cutoff_year = (global.population_Stadester_config && global.population_Stadester_config.cutoff_year) ?
      global.population_Stadester_config.cutoff_year : 1975;
    let ghsl_candidates = [];
    let ghsl_obj = options.ghsl_obj;
    let pngjs_lib = (typeof pngjs !== "undefined") ? pngjs : (global.pngjs || require("pngjs"));
    let raw_folder = options.raw_folder ? options.raw_folder : `${h1}/population_Stadester/`;
    let region_defines;
    let return_obj = {};
    let stadester_candidates = [];
    let stadester_obj = options.stadester_obj;
    let voronoi_candidates = [];
    let voronoi_png = null;
    
    //Function body
    population_Stadester_uud.loadGHSLCsvNames();
    
    //1. Load GHSL dataset (modern clusters 1975-2025)
    if (!ghsl_obj) {
      ghsl_candidates = [
        options.ghsl_file,
        path.join(raw_folder, "ghsl", "ghsl.json"),
        path.join(h1, "population_GHSL", "ghsl.json"),
        path.join(h1, "population_Stadester", "ghsl", "ghsl.json"),
        "E:/Active Projects/Project 2136 - Stadestér/output/ghsl.json",
        "D:/Project 1436 - Dataview/data/stadester/ghsl.json"
      ];
      for (let i = 0; i < ghsl_candidates.length; i++) {
        if (ghsl_candidates[i] && fs.existsSync(ghsl_candidates[i])) {
          try {
            ghsl_obj = JSON.parse(fs.readFileSync(ghsl_candidates[i], "utf8"));
            console.log(`- Loaded GHSL modern clusters from ${ghsl_candidates[i]}.`);
            break;
          } catch (e) {
            console.warn(`- Failed to read GHSL from ${ghsl_candidates[i]}:`, e);
          }
        }
      }
    }
    
    if (ghsl_obj) {
      all_ghsl_cities = Object.keys(ghsl_obj);
      for (let i = 0; i < all_ghsl_cities.length; i++) {
        let key_str = all_ghsl_cities[i].startsWith("ghsl-") ?
          all_ghsl_cities[i] : `ghsl-${all_ghsl_cities[i]}`;
        let local_city = JSON.parse(JSON.stringify(ghsl_obj[all_ghsl_cities[i]]));
        local_city.key = key_str;
        return_obj[key_str] = local_city;
      }
      console.log(`- Appended ${all_ghsl_cities.length} modern GHSL entries.`);
    }
    
    //2. Load historical Stadestér dataset
    if (!stadester_obj) {
      stadester_candidates = [
        "E:/Active Projects/Project 2136 - Stadestér/input/uud/stadester.json",
        path.join(raw_folder, "uud", "stadester.json"),
        path.join(raw_folder, "uud", "stadester_areas.json"),
        "E:/Active Projects/Project 2136 - Stadestér/output/stadester.json"
      ];
      let best_candidate_obj = null;
      let chosen_candidate_path = "";
      let max_candidate_cities = 0;
      
      for (let i = 0; i < stadester_candidates.length; i++) {
        if (stadester_candidates[i] && fs.existsSync(stadester_candidates[i])) {
          try {
            let candidate_data = JSON.parse(fs.readFileSync(stadester_candidates[i], "utf8"));
            let candidate_count = Object.keys(candidate_data).length;
            if (candidate_count > max_candidate_cities) {
              best_candidate_obj = candidate_data;
              chosen_candidate_path = stadester_candidates[i];
              max_candidate_cities = candidate_count;
            }
          } catch (e) {
            console.warn(`- Failed to read Stadestér cities from ${stadester_candidates[i]}:`, e);
          }
        }
      }
      if (best_candidate_obj) {
        stadester_obj = best_candidate_obj;
        console.log(`- Loaded historical Stadestér cities from ${chosen_candidate_path} (${max_candidate_cities} cities).`);
      }
    }
    
    if (stadester_obj) {
      all_stadester_cities = Object.keys(stadester_obj);
      for (let i = 0; i < all_stadester_cities.length; i++) {
        let key_str = all_stadester_cities[i].startsWith("stadester-") ?
          all_stadester_cities[i] : `stadester-${all_stadester_cities[i]}`;
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
        
        //Lamphun, Thailand geolocation fix
        if (key_str === "stadester-Lamphun-Thailand" || key_str.toLowerCase().includes("lamphun")) {
          if (local_city.coords && local_city.coords[0] < 10)
            local_city.coords = [18.5744357, 99.00369719999999];
        }
        
        //Regularize Trujillo, Peru historical curve to remove cubic spline vacuum sawtooth
        if (key_str.toLowerCase().includes("trujillo") && (key_str.includes("Peru") || key_str.includes("peru"))) {
          if (local_city.population) {
            let trujillo_anchors = {
              1200: 20000,
              1300: 20000,
              1400: 26666,
              1791: 9000,
              1861: 8000,
              1876: 11000,
              1890: 14000,
              1896: 45000,
              1900: 48372,
              1910: 56803,
              1920: 65234,
              1925: 70000,
              1930: 73665,
              1940: 82095,
              1950: 90526,
              1961: 99800,
              1971: 242000,
              1974: 331100
            };
            let anchor_years = Object.keys(trujillo_anchors).map(Number).sort((a, b) => a - b);
            let pop_years = Object.keys(local_city.population).map(Number).sort((a, b) => a - b);
            for (let y = 0; y < pop_years.length; y++) {
              let yr = pop_years[y];
              if (yr >= cutoff_year) continue;
              if (trujillo_anchors[yr] !== undefined) {
                local_city.population[yr] = trujillo_anchors[yr];
              } else if (yr <= anchor_years[0]) {
                local_city.population[yr] = trujillo_anchors[anchor_years[0]];
              } else if (yr >= anchor_years[anchor_years.length - 1]) {
                local_city.population[yr] = trujillo_anchors[anchor_years[anchor_years.length - 1]];
              } else {
                let low = anchor_years[0], high = anchor_years[anchor_years.length - 1];
                for (let a = 0; a < anchor_years.length - 1; a++) {
                  if (yr >= anchor_years[a] && yr <= anchor_years[a + 1]) {
                    low = anchor_years[a]; high = anchor_years[a + 1]; break;
                  }
                }
                let frac = (yr - low)/(high - low);
                local_city.population[yr] = Math.round(trujillo_anchors[low] + frac*(trujillo_anchors[high] - trujillo_anchors[low]));
              }
            }
          }
        }
        
        //Remove anachronistic antiquity entries (-500, 0) from Taipei
        if (key_str.toLowerCase().includes("taipei") || key_str.toLowerCase().includes("t'aipei")) {
          let taipei_props = ["area", "density", "population", "rni", "radial_buffers", "centre_density"];
          for (let t = 0; t < taipei_props.length; t++) {
            if (local_city[taipei_props[t]]) {
              let yr_keys = Object.keys(local_city[taipei_props[t]]);
              for (let y = 0; y < yr_keys.length; y++) {
                if (parseInt(yr_keys[y]) < 1700)
                  delete local_city[taipei_props[t]][yr_keys[y]];
              }
            }
          }
        }
        
        //Ukrainian archaeological megasites (e.g. Maydanets) lapse after antiquity
        if (key_str.toLowerCase().includes("maydanets") || key_str.toLowerCase().includes("maidanets")) {
          let maydanets_props = ["area", "density", "population", "rni", "radial_buffers", "centre_density"];
          for (let m = 0; m < maydanets_props.length; m++) {
            if (local_city[maydanets_props[m]]) {
              let yr_keys = Object.keys(local_city[maydanets_props[m]]);
              for (let y = 0; y < yr_keys.length; y++) {
                if (parseInt(yr_keys[y]) >= 0)
                  delete local_city[maydanets_props[m]][yr_keys[y]];
              }
            }
          }
          if (local_city.population) {
            local_city.population["-999"] = 0;
          }
        }
        
        local_city.key = key_str;
        return_obj[key_str] = local_city;
      }
      //Inject Vaduz into Stadestér GHSL dataset if not present
      if (!return_obj["stadester-Vaduz-Liechtenstein"] && (!stadester_obj || !stadester_obj["Vaduz-Liechtenstein"])) {
        return_obj["stadester-Vaduz-Liechtenstein"] = {
          name: "Vaduz",
          country: "Liechtenstein",
          elevation: 455,
          key: "stadester-Vaduz-Liechtenstein",
          coords: [47.141, 9.521],
          original_names: ["vaduz"],
          other_names: ["Vaduz"],
          population: {
            "1400": 300,
            "1500": 400,
            "1600": 500,
            "1700": 600,
            "1800": 800,
            "1900": 1000,
            "1910": 1300,
            "1920": 1400,
            "1930": 1600,
            "1940": 2000,
            "1950": 2700,
            "1960": 3400,
            "1970": 3900,
            "1980": 4600,
            "1990": 4900,
            "2000": 5000,
            "2010": 5200,
            "2020": 5700
          },
          region: "europe",
          type: "manual"
        };
      }
      
      console.log(`- Appended ${all_stadester_cities.length} historical Stadestér entries (truncated < ${cutoff_year}).`);
    }
    
    //3. Assign .region (string) and .colour via Voronoi equirectangular raster sampling
    voronoi_candidates = [
      options.voronoi_file,
      path.join(raw_folder, "voronoi_subdivisions.png"),
      path.join(raw_folder, "regional_subdivisions.png"),
      path.join(h1, "population_Stadester", "voronoi_subdivisions.png"),
      "E:/Active Projects/Project 2136 - Stadestér/input/voronoi_subdivisions.png"
    ];
    for (let i = 0; i < voronoi_candidates.length; i++) {
      if (voronoi_candidates[i] && fs.existsSync(voronoi_candidates[i])) {
        try {
          voronoi_png = pngjs_lib.PNG.sync.read(fs.readFileSync(voronoi_candidates[i]));
          console.log(`- Loaded Voronoi regions raster from ${voronoi_candidates[i]} (${voronoi_png.width}x${voronoi_png.height}).`);
          break;
        } catch (e) {
          console.warn(`- Failed to read Voronoi raster from ${voronoi_candidates[i]}:`, e);
        }
      }
    }
    
    region_defines = (global.config && global.config.defines && global.config.defines.regions) ?
      global.config.defines.regions : {
        northern_america: { colour: [87, 122, 175], name: "Northern America" },
        latin_america: { colour: [71, 165, 101], name: "Latin America" },
        europe: { colour: [47, 97, 170], name: "Europe" },
        eastern_europe_and_russia: { colour: [20, 114, 30], name: "Eastern Europe and Russia" },
        central_asia: { colour: [41, 193, 175], name: "Central Asia" },
        middle_east: { colour: [198, 130, 129], name: "Middle East" },
        maghreb_egypt: { colour: [239, 188, 112], name: "Maghreb and Egypt" },
        sub_saharan_africa: { colour: [155, 101, 77], name: "Sub-Saharan Africa" },
        oceania: { colour: [0, 205, 143], name: "Oceania" },
        indian_subcontinent: { colour: [214, 144, 83], name: "Indian Subcontinent" },
        southeast_asia: { colour: [97, 144, 163], name: "Southeast Asia" },
        eastasia: { colour: [173, 62, 62], name: "East Asia" }
      };
    
    all_region_keys = Object.keys(region_defines);
    for (let i = 0; i < all_region_keys.length; i++) {
      let reg = region_defines[all_region_keys[i]];
      if (reg && reg.colour)
        colour_to_region[reg.colour.join(",")] = { key: all_region_keys[i], colour: reg.colour };
    }
    
    all_return_keys = Object.keys(return_obj);
    for (let i = 0; i < all_return_keys.length; i++) {
      let local_city = return_obj[all_return_keys[i]];
      if (!local_city || !Array.isArray(local_city.coords) || local_city.coords.length < 2) continue;
      
      let lat = Number(local_city.coords[0]);
      let lng = Number(local_city.coords[1]);
      if (isNaN(lat) || isNaN(lng)) continue;
      
      if (voronoi_png) {
        let x = Math.min(voronoi_png.width - 1, Math.max(0, Math.floor(((lng - (-180))/360)*voronoi_png.width)));
        let y = Math.min(voronoi_png.height - 1, Math.max(0, Math.floor(((90 - lat)/180)*voronoi_png.height)));
        local_city.pixel_coords = [x, y];
        
        let idx = (y * voronoi_png.width + x)*4;
        let rgb_key = `${voronoi_png.data[idx]},${voronoi_png.data[idx + 1]},${voronoi_png.data[idx + 2]}`;
        let reg = colour_to_region[rgb_key];
        if (reg) {
          local_city.colour = reg.colour;
          local_city.region = reg.key;
        }
      }
    }
    
    //4. Repair all GHSL and historical city display names
    population_Stadester_uud.repairGHSLCityNames(return_obj);
    
    //Return statement
    return return_obj;
  };
}
