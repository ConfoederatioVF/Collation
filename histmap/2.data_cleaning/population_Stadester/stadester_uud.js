//Initialise functions
{
  if (!global.population_Stadester_uud) global.population_Stadester_uud = {};
  if (!global.population_Stadester_config && typeof require !== "undefined")
    try { require(path.join(__dirname, "config", "stadester_config.js")); } catch (e) {}
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
   * Returns the HYDE benchmark step interval at a given year (1000 years before 0 AD, 100 years from 0 to 1700 AD, 10 years after 1700 AD).
   * @alias population_Stadester_uud.getHydeIntervalAtYear
   * 
   * @param {number} arg0_year
   * 
   * @returns {number}
   */
  population_Stadester_uud.getHydeIntervalAtYear = function (arg0_year) {
    //Convert from parameters
    let year = Number(arg0_year);
    
    //Return statement
    if (year < 0) {
      return 1000;
    } else if (year < 1700) {
      return 100;
    } else {
      return 10;
    }
  };
  
  /**
   * Returns the canonical HYDE domain years (-10000 to 2025, annual from 1950-2025) for standalone execution.
   * @alias population_Stadester_uud.getDefaultHYDEYears
   * 
   * @returns {Array<number>}
   */
  population_Stadester_uud.getDefaultHYDEYears = function () {
    //Declare local instance variables
    let default_years = [
      -10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000
    ];
    
    //100-year intervals (0 to 1700 AD)
    for (let i = 0; i <= 1700; i += 100)
      default_years.push(i);
    
    //10-year intervals (1710 to 1950 AD)
    for (let i = 1710; i <= 1950; i += 10)
      default_years.push(i);
    
    //1-year intervals (1951 to 2025 AD)
    for (let i = 1951; i <= 2025; i++)
      default_years.push(i);
    
    //Return statement
    return default_years;
  };
  
  /**
   * Returns the maximum allowed temporal proximity gap between two benchmark years: +/-200 years or the HYDE interval at that time period, whichever is greater.
   * @alias population_Stadester_uud.getMaxTemporalProximityGap
   * 
   * @param {number} arg0_y0
   * @param {number} arg1_y1
   * 
   * @returns {number}
   */
  population_Stadester_uud.getMaxTemporalProximityGap = function (arg0_y0, arg1_y1) {
    //Convert from parameters
    let y0 = Number(arg0_y0);
    let y1 = Number(arg1_y1);
    
    //Declare local instance variables
    let cfg = global.population_Stadester_config;
    let hyde_years = (typeof landuse_HYDE !== "undefined" && Array.isArray(landuse_HYDE.sorted_hyde_years) && landuse_HYDE.sorted_hyde_years.length > 0) ?
      landuse_HYDE.sorted_hyde_years : population_Stadester_uud.getDefaultHYDEYears();
    let max_hyde_step = 0;
    let max_yr = Math.max(y0, y1);
    let min_hiatus = (cfg && Number.isFinite(cfg.min_hiatus_years)) ? cfg.min_hiatus_years : 200;
    let min_yr = Math.min(y0, y1);
    
    //Guard clauses
    if (!Number.isFinite(y0) || !Number.isFinite(y1)) return min_hiatus;
    
    //Function body
    if (min_yr < hyde_years[0])
      max_hyde_step = 1000;
    
    for (let i = 0; i < hyde_years.length - 1; i++) {
      let h_a = hyde_years[i];
      let h_b = hyde_years[i + 1];
      let step = h_b - h_a;
      if (min_yr === max_yr) {
        if (min_yr >= h_a && min_yr <= h_b && step > max_hyde_step)
          max_hyde_step = step;
      } else if (h_b > min_yr && h_a < max_yr && step > max_hyde_step) {
        max_hyde_step = step;
      }
    }
    
    //Return statement
    return Math.max(min_hiatus, max_hyde_step);
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
      if (cur_year >= min_year && cur_year <= max_year) {
        let left_idx = 0;
        for (let j = 0; j < years.length - 1; j++)
          if (cur_year >= years[j] && cur_year <= years[j + 1]) {
            left_idx = j;
            break;
          }
        let x0 = years[left_idx], x1 = years[left_idx + 1];
        let y0 = values[left_idx], y1 = values[left_idx + 1];
        let gap = x1 - x0;
        let max_gap = population_Stadester_uud.getMaxTemporalProximityGap(x0, x1);
        let is_hiatus = (gap > max_gap || y0 <= 0 || y1 <= 0);
        if (cur_year === x0) {
          object[cur_year] = y0;
        } else if (cur_year === x1) {
          object[cur_year] = y1;
        } else if (!is_hiatus) {
          object[cur_year] = population_Stadester_uud.cubicSplineInterpolation(years, values, cur_year);
        }
      }
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
        let gap = x1 - x0;
        let max_gap = population_Stadester_uud.getMaxTemporalProximityGap(x0, x1);
        let is_hiatus = (gap > max_gap || y0 <= 0 || y1 <= 0);
        if (cur_year === x0) {
          object[cur_year] = y0;
        } else if (cur_year === x1) {
          object[cur_year] = y1;
        } else if (!is_hiatus) {
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
  
  //Load source loaders, fixes, and city matching helpers
  if (typeof require !== "undefined") {
    try { require(path.join(__dirname, "stadester_uud_sources.js")); } catch (e) {}
    try { require(path.join(__dirname, "stadester_uud_fixes.js")); } catch (e) {}
  }
  
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
    let cannot_be_merged = [
      { name: "Gibraltar", ot_name: "Línea de la Concepción" },
      { name: "Pittsburgh", ot_name: "Allegheny" },
      { name: "Pittsburgh", ot_name: "Allegheny City" },
      { name: "St. Louis", ot_name: "Cahokia" },
      { name: "Saint Louis", ot_name: "Cahokia" },
      { name: "New York", ot_name: "Brooklyn" },
      { name: "New York City", ot_name: "Brooklyn" }
    ];
    let city_grid = new Map();
    let max_explicit_precision = 0.1;
    let raw_folder = options.raw_folder ? options.raw_folder : `${h1}/population_Stadester/`;
    let return_obj = {};
    
    let db_configs = options.source_dbs ? options.source_dbs : {
      populstat: { data: population_Stadester_uud.getPopulstatObject(raw_folder) },
      chandler_modelski: { data: population_Stadester_uud.getWorldcitypopObject(raw_folder), is_metro: true, precision: 0.1, semantic_precision: 1 },
      devries: { data: population_Stadester_uud.getDeVriesCitiesObject(raw_folder), precision: 0.1, semantic_precision: 1 },
      buringh: { data: population_Stadester_uud.getBuringhObject(raw_folder), precision: 0.05, semantic_precision: 1 },
      viscount_regional: { data: population_Stadester_uud.getViscountRegionalObject(options), is_polaris: true, precision: 0.05, semantic_precision: 0.25 }
    };
    let audit_log = Array.isArray(options.audit_log_array) ? options.audit_log_array : null;
    
    let cannot_be_merged_pairs = cannot_be_merged.map(function (arg0_p) {
      return [
        population_Stadester_uud.processCityName(arg0_p.name),
        population_Stadester_uud.processCityName(arg0_p.ot_name)
      ];
    });
    let grid_step = 0.25;

    function getGridCells(coords, radius) {
      let min_lat = Math.floor((Number(coords[0]) - radius)/grid_step);
      let max_lat = Math.floor((Number(coords[0]) + radius)/grid_step);
      let min_lng = Math.floor((Number(coords[1]) - radius)/grid_step);
      let max_lng = Math.floor((Number(coords[1]) + radius)/grid_step);
      let cells = [];
      for (let lat = min_lat; lat <= max_lat; lat++)
        for (let lng = min_lng; lng <= max_lng; lng++)
          cells.push(`${lat},${lng}`);
      return cells;
    }
    
    function addToGrid(city) {
      if (!city || !city.coords) return;
      let cell = `${Math.floor(Number(city.coords[0])/grid_step)},${Math.floor(Number(city.coords[1])/grid_step)}`;
      if (!city_grid.has(cell)) city_grid.set(cell, new Set());
      city_grid.get(cell).add(city.key);
    }
    
    function isAgglomeration(city) {
      if (!city) return false;
      if (city.population_scope === "city_proper" || city.population_scope === "suburb") return false;
      if (city.population_scope === "metro" || city.extent_type === "metro" || city.is_agglomeration) return true;
      if (city.key) {
        let lower_k = String(city.key).toLowerCase();
        if (lower_k.includes("(agglomeration)") || lower_k.includes("agglomeration") || lower_k.includes("(metro)") || lower_k.startsWith("greater ")) return true;
      }
      if (city.name) {
        let lower = city.name.toLowerCase();
        if (lower.includes("agglomeration") || lower.includes("(metro)") || lower.includes("greater")) return true;
      }
      return false;
    }
    
    function isBlockedMerge(city_a, city_b) {
      let name_a_prim = population_Stadester_uud.processCityName(city_a.name || "");
      let name_b_prim = population_Stadester_uud.processCityName(city_b.name || "");
      if (
        (name_a_prim === "brooklyn" && (name_b_prim === "new york" || name_b_prim === "new york city")) ||
        (name_b_prim === "brooklyn" && (name_a_prim === "new york" || name_a_prim === "new york city"))
      ) {
        return true;
      }
      let key_a = (city_a && city_a.key) ? String(city_a.key).toLowerCase() : "";
      let key_b = (city_b && city_b.key) ? String(city_b.key).toLowerCase() : "";
      if (
        (key_a.startsWith("brooklyn-") && key_b.startsWith("new york-")) ||
        (key_b.startsWith("brooklyn-") && key_a.startsWith("new york-"))
      ) {
        return true;
      }
      let idx_a = population_Stadester_uud.getCityNameIndex(city_a);
      let idx_b = population_Stadester_uud.getCityNameIndex(city_b);
      for (let i = 0; i < cannot_be_merged_pairs.length; i++) {
        let pair_a = cannot_be_merged_pairs[i][0];
        let pair_b = cannot_be_merged_pairs[i][1];
        if ((idx_a.name_set.has(pair_a) && idx_b.name_set.has(pair_b)) || (idx_a.name_set.has(pair_b) && idx_b.name_set.has(pair_a)))
          return true;
      }
      return false;
    }
    
    let all_db_keys = Object.keys(db_configs);
    for (let i = 0; i < all_db_keys.length; i++) {
      let local_db = db_configs[all_db_keys[i]];
      if (typeof population_Stadester_uud.prepareAndFlattenSourceDB === "function")
        local_db.data = population_Stadester_uud.prepareAndFlattenSourceDB(local_db.data, all_db_keys[i]);
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
          if (local_city.type !== undefined) delete local_city.type;
          population_Stadester_uud.appendCitySources(local_city, all_db_keys[i]);
          return_obj[all_local_cities[x]] = local_city;
          addToGrid(local_city);
        }
        continue;
      }
      
      for (let x = 0; x < all_local_cities.length; x++) {
        let local_city = local_db.data[all_local_cities[x]];
        let has_valid_coords = Boolean(
          local_city &&
          Array.isArray(local_city.coords) &&
          !isNaN(parseFloat(local_city.coords[0])) &&
          !isNaN(parseFloat(local_city.coords[1]))
        );
        let was_merged = [false, undefined];
        
        if (has_valid_coords) {
          let search_radius = Math.max(local_db.precision || 0, max_explicit_precision);
          let semantic_radius = Math.max(search_radius, local_db.semantic_precision || 0);
          let cells_to_check = getGridCells(local_city.coords, semantic_radius);
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
            if (!local_uud_city || !local_uud_city.coords) continue;
            if (
              local_db.is_polaris &&
              local_uud_city.viscount_project &&
              local_uud_city.viscount_project === local_city.viscount_project &&
              local_uud_city.key !== local_city.key
            ) {
              continue;
            }
            if (local_db.is_polaris && isAgglomeration(local_city) !== isAgglomeration(local_uud_city))
              continue;
            let local_distance = population_Stadester_uud.getCoordsDistance(local_uud_city.coords, local_city.coords);
            if (local_distance > semantic_radius) continue;
            if (isBlockedMerge(local_uud_city, local_city)) continue;

            let mun_gate = (typeof population_Stadester_uud.canMergeMunicipalities === "function") ?
              population_Stadester_uud.canMergeMunicipalities(local_uud_city, local_city, { max_semantic_km: 15.0 }) :
              { allow: false, dist_km: Infinity, reason: "no_gate" };
            let is_exact_name = population_Stadester_uud.checkExactNameMatch(local_uud_city, local_city);
            if (!mun_gate.allow) {
              if (audit_log && mun_gate.dist_km <= 5.0) {
                audit_log.push({
                  action: "blocked",
                  a_key: local_uud_city.key,
                  a_mun: local_uud_city._mun_id || "",
                  a_name: local_uud_city.name,
                  b_key: local_city.key,
                  b_mun: local_city._mun_id || "",
                  b_name: local_city.name,
                  dist_km: Number(mun_gate.dist_km.toFixed(3)),
                  reason: mun_gate.reason
                });
              }
              continue;
            }

            {
              let dist_km = mun_gate.dist_km;
              let is_us_compat = (
                dist_km <= 25 &&
                typeof population_Stadester_uud.areCompatibleUSCountries === "function" &&
                population_Stadester_uud.areCompatibleUSCountries(local_uud_city.country, local_city.country)
              );
              let is_same_country = Boolean(
                local_uud_city.country &&
                local_city.country &&
                (
                  local_uud_city.country === local_city.country ||
                  is_us_compat ||
                  (typeof population_Stadester_ghsl !== "undefined" && typeof population_Stadester_ghsl.areCompatibleTwinCountries === "function" &&
                    population_Stadester_ghsl.areCompatibleTwinCountries(local_uud_city.country, local_city.country))
                )
              );
              let pop_check = population_Stadester_uud.isPopulationRatioValid(local_uud_city.population, local_city.population);
              let is_match = false;
              
              let cand_yrs = Object.keys(local_city.population || {}).map(Number).filter(n => !isNaN(n) && Number(local_city.population[n]) > 0).sort((a, b) => a - b);
              let uud_yrs = Object.keys(local_uud_city.population || {}).map(Number).filter(n => !isNaN(n) && Number(local_uud_city.population[n]) > 0).sort((a, b) => a - b);
              let is_temporally_compatible = true;
              
              if (cand_yrs.length > 0 && uud_yrs.length > 0) {
                let cand_min_yr = cand_yrs[0];
                let cand_max_yr = cand_yrs[cand_yrs.length - 1];
                let uud_min_yr = uud_yrs[0];
                let uud_max_yr = uud_yrs[uud_yrs.length - 1];
                
                if (uud_min_yr > cand_max_yr || cand_min_yr > uud_max_yr) {
                  let gap_end = (uud_min_yr > cand_max_yr) ? uud_min_yr : cand_min_yr;
                  let gap_start = (uud_min_yr > cand_max_yr) ? cand_max_yr : uud_max_yr;
                  let max_allowed_gap = population_Stadester_uud.getMaxTemporalProximityGap(gap_start, gap_end);
                  let temporal_gap = gap_end - gap_start;
                  if (temporal_gap > max_allowed_gap)
                    is_temporally_compatible = false;
                }
              }
              
              if (mun_gate.reason === "intra_municipal_subdivision" || mun_gate.reason === "post_annexation_amalgamation") {
                is_match = true;
              } else if (is_temporally_compatible && is_exact_name) {
                if (local_db.is_polaris) {
                  if ((is_same_country || local_distance <= search_radius) && local_distance <= semantic_radius && pop_check.valid)
                    is_match = true;
                } else if (is_same_country && local_distance <= semantic_radius && pop_check.valid) {
                  is_match = true;
                }
              }
              
              if (is_match) {
                let score = 0;
                if (mun_gate.reason === "intra_municipal_subdivision") score += 25000;
                if (mun_gate.reason === "same_settlement_semantic_match") score += 15000;
                if (is_exact_name) score += 10000;
                if (local_distance < 0.01) score += 5000;
                if (local_distance <= search_radius) score += 3000;
                if (Boolean(local_db.is_metro) === isAgglomeration(local_uud_city)) score += 2000;
                if (local_db.is_polaris && isAgglomeration(local_uud_city)) score -= 500000;
                score += (1.0 - (local_distance/Math.max(0.01, semantic_radius)))*1000;
                let peak = population_Stadester_uud.getPeakPopulation(local_uud_city.population);
                score += (peak/100);
                if (score > best_score) {
                  best_score = score;
                  best_match = local_uud_city;
                  best_match._last_merge_reason = mun_gate.reason;
                  best_match._last_merge_dist_km = Number(dist_km.toFixed(3));
                }
              }
            }
          }
          
          if (best_match) was_merged = [true, best_match];
        }
        
        if (was_merged[0] && was_merged[1]) {
          let actual_city = was_merged[1];
          if (audit_log) {
            audit_log.push({
              action: "merged",
              a_key: actual_city.key,
              a_mun: actual_city._mun_id || "",
              a_name: actual_city.name,
              b_key: local_city.key,
              b_mun: local_city._mun_id || "",
              b_name: local_city.name,
              dist_km: actual_city._last_merge_dist_km || 0,
              reason: actual_city._last_merge_reason || "uud_merge"
            });
          }
          if (local_city.population && actual_city.population) {
            let act_yrs = Object.keys(actual_city.population).map(Number).filter(n => !isNaN(n) && Number(actual_city.population[n]) > 0).sort((a, b) => a - b);
            let cand_yrs = Object.keys(local_city.population).map(Number).filter(n => !isNaN(n) && Number(local_city.population[n]) > 0).sort((a, b) => a - b);
            if (act_yrs.length > 0 && cand_yrs.length > 1) {
              let cand_clusters = [[cand_yrs[0]]];
              for (let y = 1; y < cand_yrs.length; y++) {
                let prev_y = cand_yrs[y - 1];
                let cur_y = cand_yrs[y];
                let max_gap = population_Stadester_uud.getMaxTemporalProximityGap(prev_y, cur_y);
                if ((cur_y - prev_y) > max_gap) {
                  cand_clusters.push([cur_y]);
                } else {
                  cand_clusters[cand_clusters.length - 1].push(cur_y);
                }
              }
              if (cand_clusters.length > 1) {
                let act_max = act_yrs[act_yrs.length - 1];
                let act_min = act_yrs[0];
                let filtered_pop = {};
                let kept_any = false;
                for (let y = 0; y < cand_clusters.length; y++) {
                  let cl = cand_clusters[y];
                  let c_max = cl[cl.length - 1];
                  let c_min = cl[0];
                  let cl_ok = true;
                  if (act_min > c_max || c_min > act_max) {
                    let g_end = (act_min > c_max) ? act_min : c_min;
                    let g_start = (act_min > c_max) ? c_max : act_max;
                    if ((g_end - g_start) > population_Stadester_uud.getMaxTemporalProximityGap(g_start, g_end))
                      cl_ok = false;
                  }
                  if (cl_ok) {
                    for (let z = 0; z < cl.length; z++)
                      filtered_pop[cl[z]] = local_city.population[cl[z]];
                    kept_any = true;
                  }
                }
                if (kept_any)
                  local_city = Object.assign({}, local_city, { population: filtered_pop });
              }
            }
          }
          let already_has_polaris = (
            local_db.is_polaris &&
            typeof population_Stadester_uud.hasViscountSource === "function" &&
            population_Stadester_uud.hasViscountSource(actual_city)
          );
          let max_pol_yr_for_cut = -Infinity;
          let min_pol_yr_for_cut = Infinity;
          if (local_db.is_polaris) {
            if (!actual_city.population) actual_city.population = {};
            if (local_city.population) {
              let pol_years = Object.keys(local_city.population);
              for (let y = 0; y < pol_years.length; y++) {
                let yr_num = parseInt(pol_years[y], 10);
                if (Number.isFinite(yr_num) && Number(local_city.population[pol_years[y]]) > 0) {
                  if (yr_num < min_pol_yr_for_cut) min_pol_yr_for_cut = yr_num;
                  if (yr_num > max_pol_yr_for_cut) max_pol_yr_for_cut = yr_num;
                }
                if (yr_num <= 1900 && !already_has_polaris)
                  delete actual_city.population[pol_years[y]];
              }
              if (
                !already_has_polaris &&
                !isAgglomeration(actual_city) &&
                max_pol_yr_for_cut >= 1975 &&
                Number.isFinite(min_pol_yr_for_cut) &&
                typeof population_Stadester_uud.isCompleteViscountCountry === "function" &&
                population_Stadester_uud.isCompleteViscountCountry(actual_city.country, actual_city)
              ) {
                let cut_pol_yr = Math.min(1897, min_pol_yr_for_cut);
                let ex_pop_keys = Object.keys(actual_city.population);
                for (let ek = 0; ek < ex_pop_keys.length; ek++) {
                  let eyr = parseInt(ex_pop_keys[ek], 10);
                  if (Number.isFinite(eyr) && eyr >= cut_pol_yr)
                    delete actual_city.population[ex_pop_keys[ek]];
                }
              }
            }
          }
          if (already_has_polaris && (local_city.polaris_priority || 1) < 3) {
            if (local_city.population && actual_city.population) {
              let ex_min = Math.min.apply(null, Object.keys(actual_city.population).map(Number).filter(Number.isFinite));
              let cand_ks = Object.keys(local_city.population);
              for (let ck = 0; ck < cand_ks.length; ck++) {
                let cyr = parseInt(cand_ks[ck], 10);
                if (Number.isFinite(cyr) && cyr < ex_min && actual_city.population[cand_ks[ck]] === undefined)
                  actual_city.population[cand_ks[ck]] = local_city.population[cand_ks[ck]];
              }
            }
            if (Array.isArray(local_city.other_names)) {
              if (!actual_city.other_names) actual_city.other_names = [];
              for (let on = 0; on < local_city.other_names.length; on++)
                if (local_city.other_names[on] && !actual_city.other_names.includes(local_city.other_names[on]))
                  actual_city.other_names.push(local_city.other_names[on]);
            }
          } else {
            population_Stadester_uud.mergeCityEntries(actual_city, local_city, local_db.is_metro);
          }
          if (local_db.is_polaris && !isAgglomeration(actual_city) && (!already_has_polaris || (local_city.polaris_priority || 1) >= 3)) {
            let actual_norm = population_Stadester_uud.processCityName(actual_city.name || "");
            let local_norm = population_Stadester_uud.processCityName(local_city.name || "");
            let actual_west = (typeof population_Stadester_uud.normaliseWesternName === "function") ?
              population_Stadester_uud.normaliseWesternName(actual_city.name || "") : actual_norm;
            let local_west = (typeof population_Stadester_uud.normaliseWesternName === "function") ?
              population_Stadester_uud.normaliseWesternName(local_city.name || "") : local_norm;
            let is_primary_label_same = Boolean(
              (actual_norm && local_norm && actual_norm === local_norm) ||
              (actual_west && local_west && actual_west === local_west)
            );
            let act_pop_yrs = Object.keys(actual_city.population || {}).map(Number).filter(function (arg0_n) { return Number.isFinite(arg0_n) && Number(actual_city.population[arg0_n]) > 0; });
            let loc_pop_yrs = Object.keys(local_city.population || {}).map(Number).filter(function (arg0_n) { return Number.isFinite(arg0_n) && Number(local_city.population[arg0_n]) > 0; });
            let act_latest_yr = act_pop_yrs.length > 0 ? Math.max.apply(null, act_pop_yrs) : -Infinity;
            let loc_latest_yr = loc_pop_yrs.length > 0 ? Math.max.apply(null, loc_pop_yrs) : -Infinity;
            let act_peak = population_Stadester_uud.getPeakPopulation(actual_city.population);
            let loc_peak = population_Stadester_uud.getPeakPopulation(local_city.population);
            let act_is_cap = Boolean(actual_city.is_capital || actual_city.capital);
            let loc_is_cap = Boolean(local_city.is_capital || local_city.capital);
            let can_take_canonical_identity = Boolean(
              (loc_is_cap && !act_is_cap) ||
              ((!act_is_cap || loc_is_cap) && (is_primary_label_same || (loc_latest_yr >= act_latest_yr && loc_peak >= act_peak*0.5)))
            );

            if (loc_is_cap) actual_city.is_capital = true;
            if (local_city.name && actual_city.name !== local_city.name) {
              if (!actual_city.other_names) actual_city.other_names = [];
              if (can_take_canonical_identity) {
                actual_city.other_names.push(actual_city.name);
                actual_city.name = local_city.name;
              } else {
                actual_city.other_names.push(local_city.name);
              }
            }
            if (Array.isArray(actual_city.other_names) && actual_city.other_names.length > 0) {
              let seen_low = new Set([String(actual_city.name || "").trim().toLowerCase()]);
              let dedup_o = [];
              for (let oi = 0; oi < actual_city.other_names.length; oi++) {
                let s = String(actual_city.other_names[oi] || "").trim();
                let lo = s.toLowerCase();
                if (!s || seen_low.has(lo)) continue;
                seen_low.add(lo);
                dedup_o.push(s);
              }
              actual_city.other_names = dedup_o;
            }
            if (actual_city.name_peaks && local_city.name && can_take_canonical_identity)
              actual_city.name_peaks[local_city.name] = 1e12;
            if (can_take_canonical_identity && Array.isArray(local_city.coords) && local_city.coords.length >= 2) {
              actual_city.coords = [Number(local_city.coords[0]), Number(local_city.coords[1])];
              addToGrid(actual_city);
            }
            let is_us_rekey = Boolean(
              (actual_city.country === "United States" || actual_city.country === "United States of America") &&
              local_city.country &&
              local_city.country !== actual_city.country &&
              typeof population_Stadester_uud.isUSCountryOrState === "function" &&
              population_Stadester_uud.isUSCountryOrState(local_city.country)
            );
            if (is_us_rekey) {
              let is_washington = (actual_city.name === "Washington" || local_city.name === "Washington");
              if (!is_washington) {
                let old_key = actual_city.key;
                let new_key = local_city.key;
                actual_city.country = local_city.country;
                if (old_key !== new_key) {
                  delete return_obj[old_key];
                  if (city_grid && Array.isArray(actual_city.coords)) {
                    let old_cell = `${Math.floor(Number(actual_city.coords[0]))},${Math.floor(Number(actual_city.coords[1]))}`;
                    if (city_grid.has(old_cell)) city_grid.get(old_cell).delete(old_key);
                  }
                  actual_city.key = new_key;
                  return_obj[new_key] = actual_city;
                  addToGrid(actual_city);
                }
              }
            }
            if (actual_city.name === "New York" && (actual_city.country === "New York" || actual_city.country === "United States")) {
              actual_city.coords = [40.7128, -74.0060];
              addToGrid(actual_city);
              if (Array.isArray(actual_city.other_names))
                actual_city.other_names = actual_city.other_names.filter(function (arg0_n) { return arg0_n !== "Brooklyn"; });
            }
            if (typeof population_Stadester_uud.absorbSecondaryNonPolarisTwins === "function")
              population_Stadester_uud.absorbSecondaryNonPolarisTwins(
                return_obj,
                city_grid,
                actual_city,
                local_city,
                min_pol_yr_for_cut,
                getGridCells,
                addToGrid,
                isAgglomeration
              );
          }
          if (local_db.is_polaris && !isAgglomeration(actual_city) && (!already_has_polaris || (local_city.polaris_priority || 1) >= 3) && local_city.population && actual_city.population) {
            let pol_yrs = Object.keys(local_city.population).map(Number).filter(function (arg0_n) { return Number.isFinite(arg0_n) && Number(local_city.population[arg0_n]) > 0; }).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
            if (pol_yrs.length > 0) {
              for (let py = 0; py < pol_yrs.length; py++)
                actual_city.population[pol_yrs[py]] = [local_city.population[pol_yrs[py]]];
              if (pol_yrs.length >= 2) {
                let existing_yrs = Object.keys(actual_city.population).map(Number).filter(Number.isFinite);
                for (let ey = 0; ey < existing_yrs.length; ey++) {
                  let y = existing_yrs[ey];
                  if (local_city.population[y] !== undefined) continue;
                  if (y > pol_yrs[0] && y < pol_yrs[pol_yrs.length - 1]) {
                    let prev_p = null;
                    let next_p = null;
                    for (let k = 0; k < pol_yrs.length - 1; k++) {
                      if (pol_yrs[k] < y && pol_yrs[k + 1] > y) {
                        prev_p = pol_yrs[k];
                        next_p = pol_yrs[k + 1];
                        break;
                      }
                    }
                    if (prev_p !== null && (next_p - prev_p) <= 15) {
                      let v_prev = Number(local_city.population[prev_p]) || 0;
                      let v_next = Number(local_city.population[next_p]) || 0;
                      let v_interp = v_prev + (v_next - v_prev)*((y - prev_p)/(next_p - prev_p));
                      let raw_arr = Array.isArray(actual_city.population[y]) ? actual_city.population[y] : [actual_city.population[y]];
                      let cleaned_arr = raw_arr.filter(function (arg0_v) {
                        let nv = Number(arg0_v);
                        return Number.isFinite(nv) && nv > 0 && v_interp > 0 && (nv/v_interp) <= 2.5 && (v_interp/nv) <= 2.5;
                      });
                      if (cleaned_arr.length > 0)
                        actual_city.population[y] = cleaned_arr;
                      else
                        delete actual_city.population[y];
                    }
                  }
                }
              }
            }
          }
          if (local_city.viscount_project && (!actual_city.viscount_z_priority || local_city.viscount_z_priority > actual_city.viscount_z_priority)) {
            actual_city.viscount_order = local_city.viscount_order;
            actual_city.viscount_project = local_city.viscount_project;
            actual_city.viscount_z_priority = local_city.viscount_z_priority;
            if (local_city.population_scope) actual_city.population_scope = local_city.population_scope;
            if (local_city.extent_type) actual_city.extent_type = local_city.extent_type;
            if (local_city.is_agglomeration) actual_city.is_agglomeration = local_city.is_agglomeration;
            if (local_city.metro_parent_key) actual_city.metro_parent_key = local_city.metro_parent_key;
            if (local_city.metro_key) actual_city.metro_key = local_city.metro_key;
          }
          let merged_sources = local_db.is_polaris ?
            (local_city.sources || local_city.viscount_project) :
            (local_city.sources || all_db_keys[i]);
          population_Stadester_uud.appendCitySources(actual_city, merged_sources);
          return_obj[actual_city.key] = actual_city;
        } else if (has_valid_coords) {
          let new_sources = local_db.is_polaris ?
            (local_city.sources || local_city.viscount_project) :
            (local_city.sources || all_db_keys[i]);
          let target_key = all_local_cities[x];
          if (return_obj[target_key]) {
            let clean_src_tag = local_db.is_polaris ?
              String(local_city.viscount_project || "viscount").toLowerCase() :
              all_db_keys[i];
            let assigned = false;
            for (let s_idx = 2; s_idx <= 9999; s_idx++) {
              let cand_k = `${all_local_cities[x]}_${s_idx}`;
              if (!return_obj[cand_k]) {
                target_key = cand_k;
                assigned = true;
                break;
              }
            }
            if (!assigned) target_key = `${all_local_cities[x]}_${clean_src_tag}`;
          }
          local_city.key = target_key;
          if (local_city.type !== undefined) delete local_city.type;
          population_Stadester_uud.appendCitySources(local_city, new_sources);
          return_obj[target_key] = local_city;
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
    if (typeof population_Stadester_uud.injectManualRecords === "function")
      population_Stadester_uud.injectManualRecords(return_obj);
    
    //Ensure Lamphun geolocation is fixed to authoritative coordinates
    if (return_obj["Lamphun-Thailand"])
      return_obj["Lamphun-Thailand"].coords = [18.5744357, 99.00369719999999];
    
    //Clean RU/UA/BY post-1975 agglomeration tails and 1-2 year Populstat U/V-spikes before recording empirical bounds
    if (typeof population_Stadester_uud.cleanPostMergeUUD === "function")
      population_Stadester_uud.cleanPostMergeUUD(return_obj);
    
    //Record true pre-interpolation empirical bounds so downstream GHSL/GHS-POP partitioning knows exact census end-years
    let final_uud_keys = Object.keys(return_obj);
    for (let i = 0; i < final_uud_keys.length; i++) {
      let local_city = return_obj[final_uud_keys[i]];
      if (!local_city || !local_city.population) continue;
      let all_yrs = Object.keys(local_city.population).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b);
      let pos_yrs = all_yrs.filter(y => Number(local_city.population[y]) > 0);
      local_city._raw_min_year = (pos_yrs.length > 0) ? pos_yrs[0] : null;
      local_city._raw_max_year = (pos_yrs.length > 0) ? pos_yrs[pos_yrs.length - 1] : null;
      if (local_city.population["-999"] === 0 || (all_yrs.length > 0 && Number(local_city.population[all_yrs[all_yrs.length - 1]]) <= 0))
        local_city._raw_lapsed = true;
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
    let hyde_years = (typeof landuse_HYDE !== "undefined" && landuse_HYDE && landuse_HYDE.sorted_hyde_years) ?
      landuse_HYDE.sorted_hyde_years : population_Stadester_uud.getDefaultHYDEYears();
    let prehistoric_1000y = [-10000, -9000, -8000, -7000, -6000, -5000, -4000];
    let antiquity_100y = Array.from({ length: 31 }, (_, i) => -3000 + i*100);
    let post_1ad = hyde_years.filter(y => y > 0 && y <= 2025);
    let target_years = (options.years) ? options.years.filter(y => y >= -10000 && y <= 2025) : [...prehistoric_1000y, ...antiquity_100y, ...post_1ad];
    
    console.log(`- Interpolating UUD for ${all_cities.length} cities over years:`, target_years.length);
    for (let i = 0; i < all_cities.length; i++) {
      let local_city = uud_obj[all_cities[i]];
      if (!local_city || !local_city.population) continue;
      
      //Record empirical span before interpolation if not already annotated
      let found_yr = Number(local_city["found.yr"] !== undefined ? local_city["found.yr"] : local_city.foundation_year);
      if (Number.isFinite(found_yr) && found_yr > 0 && found_yr < 1) {
        found_yr = Math.round(found_yr*10000);
        local_city["found.yr"] = found_yr;
        local_city.foundation_year = found_yr;
      }
      if (Number.isFinite(found_yr) && found_yr > 2026) {
        found_yr = (found_yr >= 100000 && found_yr <= 202699) ? Math.floor(found_yr/100) : NaN;
        if (Number.isFinite(found_yr)) {
          local_city["found.yr"] = found_yr;
          local_city.foundation_year = found_yr;
        } else {
          delete local_city["found.yr"];
          delete local_city.foundation_year;
        }
      }
      if (Number.isFinite(found_yr)) {
        let ex_pop_keys = Object.keys(local_city.population);
        for (let py = 0; py < ex_pop_keys.length; py++) {
          let yr_n = parseInt(ex_pop_keys[py], 10);
          if (Number.isFinite(yr_n) && yr_n < found_yr)
            delete local_city.population[ex_pop_keys[py]];
        }
      }

      if (local_city._raw_max_year === undefined) {
        let all_yrs = Object.keys(local_city.population).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b);
        let pos_yrs = all_yrs.filter(y => Number(local_city.population[y]) > 0);
        local_city._raw_min_year = (pos_yrs.length > 0) ? pos_yrs[0] : null;
        local_city._raw_max_year = (pos_yrs.length > 0) ? pos_yrs[pos_yrs.length - 1] : null;
        if (local_city.population["-999"] === 0 || (all_yrs.length > 0 && Number(local_city.population[all_yrs[all_yrs.length - 1]]) <= 0))
          local_city._raw_lapsed = true;
      }
      
      let valid_keys = Object.keys(local_city.population).filter(k => local_city.population[k] > 0);
      if (valid_keys.length >= 2) {
        let missing_years = target_years.filter(function (arg0_y) {
          if (local_city.population[arg0_y] !== undefined) return false;
          if (Number.isFinite(found_yr) && arg0_y < found_yr) return false;
          if (Number.isFinite(local_city._annexation_year) && arg0_y >= Number(local_city._annexation_year)) return false;
          return true;
        });
        if (missing_years.length > 0) {
          if (options.mode === "cubic") {
            local_city.population = population_Stadester_uud.cubicSplineInterpolationObject(local_city.population, { years: missing_years });
          } else {
            local_city.population = population_Stadester_uud.linearInterpolationObject(local_city.population, { years: missing_years });
          }
        }
        if (Number.isFinite(found_yr)) {
          let post_keys = Object.keys(local_city.population);
          for (let py = 0; py < post_keys.length; py++) {
            let yr_n = parseInt(post_keys[py], 10);
            if (Number.isFinite(yr_n) && yr_n < found_yr)
              delete local_city.population[post_keys[py]];
          }
        }
      }
    }
    
    //Legacy flat forward-padding is disabled by default so GHS-POP gridcell partitioning handles post-empirical tails dynamically
    if (options.pad_modern_flat === true) {
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
      if (
        local_city.population_scope !== "city_proper" &&
        local_city.population_scope !== "suburb" &&
        local_city.name &&
        (local_city.name.toLowerCase().includes("agglomeration") || local_city.name.toLowerCase().includes("(metro)") || local_city.name.toLowerCase().includes("greater")) &&
        !local_city.is_agglomeration_of
      )
        local_city.is_agglomeration_of = population_Stadester_uud.processCityName(local_city.name);
      if (local_city.name && local_city.name.includes(":")) continue;
      if (typeof population_Stadester_uud.appendCitySources === "function") {
        population_Stadester_uud.appendCitySources(local_city, local_city.type);
        if (!Array.isArray(local_city.sources) || local_city.sources.length === 0)
          population_Stadester_uud.appendCitySources(local_city, local_city.viscount_project || "populstat");
      }
      return_obj[all_cities[i]] = local_city;
    }
    
    //Return statement
    return return_obj;
  };
  
  if (typeof require !== "undefined")
    try { require(path.join(__dirname, "stadester_ghsl.js")); } catch (e) {}
}