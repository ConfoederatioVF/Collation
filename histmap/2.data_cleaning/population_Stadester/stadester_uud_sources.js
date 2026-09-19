//Initialise functions
{
  if (!global.population_Stadester_uud) global.population_Stadester_uud = {};
  
  /**
   * Normalises and cleans city names for fuzzy semantic matching.
   * @alias population_Stadester_uud.processCityName
   * 
   * @param {string} arg0_name
   * 
   * @returns {string}
   */
  population_Stadester_uud.processCityName = function (arg0_name) {
    //Convert from parameters
    let name = (arg0_name) ? `${arg0_name}` : "";
    
    //Declare local instance variables
    name = name.replace(/\([^)]*\)/g, "");
    name = name.replace(/\bgreater\b/gi, "");
    name = name.replace(/\bagglomeration\b/gi, "");
    name = name.replace(/\(\s*\)/g, "");
    
    //Return statement
    return name.replace(/\s+/g, " ").trim().toLowerCase();
  };
  
  /**
   * Regularises city name casing and removes delimiters.
   * @alias population_Stadester_uud.regulariseCityName
   * 
   * @param {string} arg0_name
   * 
   * @returns {string}
   */
  population_Stadester_uud.regulariseCityName = function (arg0_name) {
    //Convert from parameters
    let name = (arg0_name) ? `${arg0_name}` : "";
    
    //Declare local instance variables
    let city = name.replace(/[_-]/g, " ");
    city = city.replace(/\s+/g, " ").trim();
    city = city.replace(/([a-zA-Z]+)/g, w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase());
    
    //Return statement
    return city;
  };
  
  /**
   * Retrieves peak recorded population in a city's historical timeline.
   * @alias population_Stadester_uud.getPeakPopulation
   * 
   * @param {Object} arg0_population_obj
   * 
   * @returns {number}
   */
  population_Stadester_uud.getPeakPopulation = function (arg0_population_obj) {
    //Convert from parameters
    let population_obj = arg0_population_obj;
    
    //Declare local instance variables
    let max_pop = 0;
    
    //Guard clauses
    if (!population_obj) return 0;
    
    let all_years = Object.keys(population_obj);
    for (let i = 0; i < all_years.length; i++) {
      let val = Array.isArray(population_obj[all_years[i]]) ?
        population_obj[all_years[i]][0] : population_obj[all_years[i]];
      let pop = parseFloat(val);
      if (pop > max_pop) max_pop = pop;
    }
    
    //Return statement
    return max_pop;
  };
  
  /**
   * Checks whether population trajectories overlap and maintain valid ratios.
   * @alias population_Stadester_uud.isPopulationRatioValid
   * 
   * @param {Object} arg0_pop_a
   * @param {Object} arg1_pop_b
   * 
   * @returns {{valid: boolean, overlaps: boolean}}
   */
  population_Stadester_uud.isPopulationRatioValid = function (arg0_pop_a, arg1_pop_b) {
    //Convert from parameters
    let pop_a = arg0_pop_a;
    let pop_b = arg1_pop_b;
    
    //Declare local instance variables
    let fail_count = 0;
    let keys_a;
    let keys_b;
    let valid_checks = 0;
    
    //Guard clauses
    if (!pop_a || !pop_b) return { valid: true, overlaps: false };
    keys_a = Object.keys(pop_a).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b);
    keys_b = Object.keys(pop_b).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b);
    if (keys_a.length === 0 || keys_b.length === 0) return { valid: true, overlaps: false };
    
    let min_a = keys_a[0], max_a = keys_a[keys_a.length - 1];
    let min_b = keys_b[0], max_b = keys_b[keys_b.length - 1];
    let int_start = Math.max(min_a, min_b);
    let int_end = Math.min(max_a, max_b);
    
    if (int_start > int_end) {
      let peak_a = population_Stadester_uud.getPeakPopulation(pop_a);
      let peak_b = population_Stadester_uud.getPeakPopulation(pop_b);
      if (peak_a > 0 && peak_b > 0) {
        let ratio = peak_a/peak_b;
        if (ratio < 0.1 || ratio > 10.0) return { valid: false, overlaps: false };
      }
      return { valid: true, overlaps: false };
    }
    
    let all_keys = Array.from(new Set([...keys_a, ...keys_b])).sort((a, b) => a - b);
    let check_keys = all_keys.filter(yr => yr >= int_start && yr <= int_end);
    
    function getValueAtYear(pop, keys, yr) {
      if (pop[yr] !== undefined) {
        let val = Array.isArray(pop[yr]) ? pop[yr][0] : pop[yr];
        return parseFloat(val);
      }
      let lower = keys[0], upper = keys[keys.length - 1];
      for (let j = 0; j < keys.length; j++) {
        if (keys[j] < yr) lower = keys[j];
        if (keys[j] > yr) { upper = keys[j]; break; }
      }
      let val_lower = parseFloat(Array.isArray(pop[lower]) ? pop[lower][0] : pop[lower]);
      let val_upper = parseFloat(Array.isArray(pop[upper]) ? pop[upper][0] : pop[upper]);
      if (!isNaN(val_lower) && !isNaN(val_upper) && upper !== lower)
        return val_lower + (val_upper - val_lower)*((yr - lower)/(upper - lower));
      return isNaN(val_lower) ? val_upper : val_lower;
    }
    
    for (let k = 0; k < check_keys.length; k++) {
      let yr = check_keys[k];
      let num_a = getValueAtYear(pop_a, keys_a, yr);
      let num_b = getValueAtYear(pop_b, keys_b, yr);
      
      if (!isNaN(num_a) && !isNaN(num_b) && num_a > 0 && num_b > 0) {
        valid_checks++;
        let ratio = num_a/num_b;
        if (ratio < 0.25 || ratio > 4.0) fail_count++;
      }
    }
    
    if (valid_checks > 0 && (fail_count/valid_checks) > 0.5) return { valid: false, overlaps: true };
    if (valid_checks > 0 && valid_checks <= 2 && fail_count === valid_checks) return { valid: false, overlaps: true };
    
    //Return statement
    return { valid: true, overlaps: true };
  };
  
  /**
   * Extracts all processed name variants for a city entry.
   * @alias population_Stadester_uud.getAllCityNames
   * 
   * @param {Object} arg0_city
   * 
   * @returns {Array<string>}
   */
  population_Stadester_uud.getAllCityNames = function (arg0_city) {
    //Convert from parameters
    let city = arg0_city;
    
    //Declare local instance variables
    let names = [];
    
    //Guard clauses
    if (!city) return [];
    
    if (city.name) {
      let proc = population_Stadester_uud.processCityName(city.name);
      if (proc && !names.includes(proc)) names.push(proc);
    }
    if (Array.isArray(city.other_names)) {
      for (let k = 0; k < city.other_names.length; k++) {
        let proc = population_Stadester_uud.processCityName(city.other_names[k]);
        if (proc && !names.includes(proc)) names.push(proc);
      }
    }
    if (Array.isArray(city.original_names)) {
      for (let k = 0; k < city.original_names.length; k++) {
        let proc = population_Stadester_uud.processCityName(city.original_names[k]);
        if (proc && !names.includes(proc)) names.push(proc);
      }
    }
    
    //Return statement
    return names;
  };
  
  /**
   * Checks if two cities have any matching processed name variants.
   * @alias population_Stadester_uud.checkExactNameMatch
   * 
   * @param {Object} arg0_city_a
   * @param {Object} arg1_city_b
   * 
   * @returns {boolean}
   */
  population_Stadester_uud.checkExactNameMatch = function (arg0_city_a, arg1_city_b) {
    //Convert from parameters
    let city_a = arg0_city_a;
    let city_b = arg1_city_b;
    
    //Declare local instance variables
    let names_a = population_Stadester_uud.getAllCityNames(city_a);
    let names_b = population_Stadester_uud.getAllCityNames(city_b);
    
    for (let x = 0; x < names_a.length; x++)
      for (let y = 0; y < names_b.length; y++)
        if (names_a[x] && names_a[x] === names_b[y]) return true;
    
    //Return statement
    return false;
  };
  
  /**
   * Merges two population objects by concatenating observations per year.
   * @alias population_Stadester_uud.mergeCityPopulations
   * 
   * @param {Object} arg0_population_obj
   * @param {Object} arg1_population_obj
   * 
   * @returns {Object}
   */
  population_Stadester_uud.mergeCityPopulations = function (arg0_population_obj, arg1_population_obj) {
    //Convert from parameters
    let population_obj = JSON.parse(JSON.stringify(arg0_population_obj || {}));
    let ot_population_obj = JSON.parse(JSON.stringify(arg1_population_obj || {}));
    
    //Declare local instance variables
    let all_ot_population_keys = Object.keys(ot_population_obj);
    let all_population_keys = Object.keys(population_obj);
    
    for (let i = 0; i < all_population_keys.length; i++)
      if (!Array.isArray(population_obj[all_population_keys[i]]))
        population_obj[all_population_keys[i]] = [population_obj[all_population_keys[i]]];
    
    for (let i = 0; i < all_ot_population_keys.length; i++) {
      let local_value = ot_population_obj[all_ot_population_keys[i]];
      if (Array.isArray(local_value)) local_value = local_value.flat(Infinity);
      
      if (Array.isArray(population_obj[all_ot_population_keys[i]])) {
        if (!Array.isArray(local_value)) {
          population_obj[all_ot_population_keys[i]].push(local_value);
        } else {
          population_obj[all_ot_population_keys[i]] = population_obj[all_ot_population_keys[i]].concat(local_value);
        }
      } else {
        if (!Array.isArray(local_value)) {
          population_obj[all_ot_population_keys[i]] = [local_value];
        } else {
          population_obj[all_ot_population_keys[i]] = local_value;
        }
      }
    }
    
    //Return statement
    return population_obj;
  };
  
  /**
   * Merges source city attributes and population into target city.
   * @alias population_Stadester_uud.mergeCityEntries
   * 
   * @param {Object} arg0_target_city
   * @param {Object} arg1_source_city
   * @param {boolean} arg2_is_metro
   * 
   * @returns {Object}
   */
  population_Stadester_uud.mergeCityEntries = function (arg0_target_city, arg1_source_city, arg2_is_metro) {
    //Convert from parameters
    let target_city = arg0_target_city;
    let source_city = arg1_source_city;
    let is_metro = arg2_is_metro;
    
    //Guard clauses
    if (!target_city || !source_city) return target_city;
    
    //Declare local instance variables
    let best_name = target_city.name;
    let candidate_names = [];
    let old_target_name = target_city.name;
    
    if (!target_city.original_names) {
      target_city.original_names = [];
      if (target_city.name) {
        let proc_n = population_Stadester_uud.processCityName(target_city.name);
        if (proc_n) target_city.original_names.push(proc_n);
      }
      if (Array.isArray(target_city.other_names))
        for (let i = 0; i < target_city.other_names.length; i++) {
          let proc_n = population_Stadester_uud.processCityName(target_city.other_names[i]);
          if (proc_n && !target_city.original_names.includes(proc_n)) target_city.original_names.push(proc_n);
        }
    }
    
    if (!target_city.name_peaks) {
      target_city.name_peaks = {};
      target_city.name_coords = {};
      if (target_city.name) {
        target_city.name_peaks[target_city.name] = population_Stadester_uud.getPeakPopulation(target_city.population);
        if (target_city.coords) target_city.name_coords[target_city.name] = target_city.coords;
      }
    }
    
    let source_peak = population_Stadester_uud.getPeakPopulation(source_city.population);
    if (source_city.name) {
      let cur_peak = target_city.name_peaks[source_city.name] || 0;
      if (source_peak >= cur_peak) {
        target_city.name_peaks[source_city.name] = source_peak;
        if (source_city.coords) target_city.name_coords[source_city.name] = source_city.coords;
      }
    }
    
    if (source_city.name_peaks) {
      let s_keys = Object.keys(source_city.name_peaks);
      for (let i = 0; i < s_keys.length; i++) {
        let k = s_keys[i];
        let p = source_city.name_peaks[k];
        let cur_peak = target_city.name_peaks[k] || 0;
        if (p >= cur_peak) {
          target_city.name_peaks[k] = p;
          if (source_city.name_coords && source_city.name_coords[k]) {
            target_city.name_coords[k] = source_city.name_coords[k];
          } else if (source_city.coords) {
            target_city.name_coords[k] = source_city.coords;
          }
        }
      }
    }
    
    let max_name_peak = -1;
    let all_name_keys = Object.keys(target_city.name_peaks);
    for (let i = 0; i < all_name_keys.length; i++) {
      let k = all_name_keys[i];
      let p = target_city.name_peaks[k];
      if (p > max_name_peak) {
        max_name_peak = p;
        best_name = k;
      }
    }
    
    if (best_name) {
      target_city.name = best_name;
      if (target_city.name_coords && target_city.name_coords[best_name])
        target_city.coords = target_city.name_coords[best_name];
    }
    
    if (!target_city.other_names) target_city.other_names = [];
    if (old_target_name) candidate_names.push(old_target_name);
    if (source_city.name) candidate_names.push(source_city.name);
    if (Array.isArray(source_city.other_names)) candidate_names = candidate_names.concat(source_city.other_names);
    if (Array.isArray(target_city.other_names)) candidate_names = candidate_names.concat(target_city.other_names);
    
    for (let i = 0; i < candidate_names.length; i++) {
      let cur = candidate_names[i];
      if (cur && cur !== target_city.name && !target_city.other_names.includes(cur))
        target_city.other_names.push(cur);
    }
    
    if (source_city.is_agglomeration_of) target_city.is_agglomeration_of = source_city.is_agglomeration_of;
    if (source_city.population)
      target_city.population = is_metro ?
        population_Stadester_uud.mergeCityPopulations(source_city.population, target_city.population) :
        population_Stadester_uud.mergeCityPopulations(target_city.population, source_city.population);
    
    //Return statement
    return target_city;
  };
  
  /**
   * Loads Buringh raw European urban population file.
   * @alias population_Stadester_uud.getBuringhObject
   * 
   * @param {string} [arg0_raw_folder]
   * 
   * @returns {Object}
   */
  population_Stadester_uud.getBuringhObject = function (arg0_raw_folder) {
    //Convert from parameters
    let raw_folder = arg0_raw_folder ? arg0_raw_folder : `${h1}/population_Stadester/`;
    
    //Declare local instance variables
    let buringh_file = path.join(raw_folder, "buringh", "European urban population, 700 - 2000.txt");
    let buringh_array = File.loadCSVAsArray(buringh_file, { delimiter: "@", utf: "utf16le" });
    let header = buringh_array[0];
    let return_obj = {};
    
    for (let i = 1; i < buringh_array.length; i++) {
      let local_city = buringh_array[i];
      let local_obj = {};
      for (let x = 0; x < local_city.length; x++)
        local_obj[header[x]] = local_city[x];
      
      if (!local_obj.city) continue;
      let local_country = local_obj.country;
      let local_key = `${local_obj.city}-${local_obj.country}`;
      
      if (!return_obj[local_key]) {
        return_obj[local_key] = {
          name: local_obj.city,
          coords: [
            parseFloat(String(local_obj["latitude in degrees"]).replace(",", ".")),
            parseFloat(String(local_obj["longitude in degrees"]).replace(",", "."))
          ],
          country: local_country,
          other_names: local_obj["synonyms and historical names"] ?
            local_obj["synonyms and historical names"].split(",").map(item => item.trim()) : [],
          key: local_key,
          population: {}
        };
      }
      
      let actual_city = return_obj[local_key];
      let local_population = parseFloat(local_obj["inhabitants in 000-s"]);
      if (local_population > 0 && local_obj.year)
        actual_city.population[local_obj.year] = local_population*1000;
    }
    
    delete return_obj.city;
    delete return_obj["city-country"];
    
    //Return statement
    return return_obj;
  };
  
  /**
   * Loads DeVries raw European urban population file.
   * @alias population_Stadester_uud.getDeVriesCitiesObject
   * 
   * @param {string} [arg0_raw_folder]
   * 
   * @returns {Object}
   */
  population_Stadester_uud.getDeVriesCitiesObject = function (arg0_raw_folder) {
    //Convert from parameters
    let raw_folder = arg0_raw_folder ? arg0_raw_folder : `${h1}/population_Stadester/`;
    
    //Declare local instance variables
    let actual_return_obj = {};
    let devries_cities_file = path.join(raw_folder, "devries", "europop.csv");
    let devries_cities = File.loadCSVAsJSON(devries_cities_file, { mode: "vertical" });
    let devries_coords_file = path.join(raw_folder, "devries", "city_coords.csv");
    let devries_coords = File.loadCSVAsArray(devries_coords_file);
    let return_obj = {};
    
    let all_cities_keys = Object.keys(devries_cities);
    for (let i = 0; i < all_cities_keys.length; i++) {
      let local_city = devries_cities[all_cities_keys[i]];
      return_obj[all_cities_keys[i]] = {
        key: all_cities_keys[i],
        population: {}
      };
      let actual_city = return_obj[all_cities_keys[i]];
      
      if (local_city.year) {
        for (let x = 0; x < local_city.year.length; x++) {
          if (local_city.population && local_city.population[x] && local_city.population[x] !== "NA") {
            let local_population = parseInt(local_city.population[x]*1000);
            if (local_population > 0)
              actual_city.population[local_city.year[x]] = local_population;
          }
        }
      }
      if (local_city.region) actual_city.country = local_city.region[0];
    }
    
    for (let i = 1; i < devries_coords.length; i++) {
      let local_value = devries_coords[i];
      let local_lat = parseFloat(local_value[1]);
      let local_lng = parseFloat(local_value[0]);
      let local_key = local_value[2];
      if (return_obj[local_key])
        return_obj[local_key].coords = [local_lat, local_lng];
    }
    
    let all_return_keys = Object.keys(return_obj);
    for (let i = 0; i < all_return_keys.length; i++) {
      let local_city = return_obj[all_return_keys[i]];
      let local_city_name = population_Stadester_uud.regulariseCityName(local_city.key);
      let local_key = (local_city.country) ? `${local_city_name}-${local_city.country}` : local_city_name;
      
      local_city.name = local_city_name;
      local_city.key = local_key;
      actual_return_obj[local_key] = local_city;
    }
    
    //Return statement
    return actual_return_obj;
  };
  
  /**
   * Loads Populstat raw cities database.
   * @alias population_Stadester_uud.getPopulstatObject
   * 
   * @param {string} [arg0_raw_folder]
   * 
   * @returns {Object}
   */
  population_Stadester_uud.getPopulstatObject = function (arg0_raw_folder) {
    //Convert from parameters
    let raw_folder = arg0_raw_folder ? arg0_raw_folder : `${h1}/population_Stadester/`;
    
    //Declare local instance variables
    let country_mappings = (global.population_Stadester_config && global.population_Stadester_config.populstat_countries) ?
      global.population_Stadester_config.populstat_countries : {};
    let populstat_file = path.join(raw_folder, "populstat_cities", "populstat_cities.json");
    let populstat_obj = JSON.parse(fs.readFileSync(populstat_file, "utf8"));
    let return_obj = {};
    
    let all_countries = Object.keys(populstat_obj);
    for (let i = 0; i < all_countries.length; i++) {
      let local_country = populstat_obj[all_countries[i]];
      let all_local_cities = Object.keys(local_country);
      let local_country_name = country_mappings[all_countries[i]] || all_countries[i];
      
      for (let x = 0; x < all_local_cities.length; x++) {
        let local_city = local_country[all_local_cities[x]];
        let local_key = `${all_local_cities[x]}-${local_country_name}`;
        
        if (local_city.population) {
          let pop_keys = Object.keys(local_city.population);
          for (let y = 0; y < pop_keys.length; y++)
            local_city.population[pop_keys[y]] = local_city.population[pop_keys[y]]*1000;
        }
        local_city.country = local_country_name;
        local_city.key = local_key;
        return_obj[local_key] = local_city;
      }
    }
    
    //Return statement
    return return_obj;
  };
  
  /**
   * Loads WorldCityPop / Chandler-Modelski cities database.
   * @alias population_Stadester_uud.getWorldcitypopObject
   * 
   * @param {string} [arg0_raw_folder]
   * 
   * @returns {Object}
   */
  population_Stadester_uud.getWorldcitypopObject = function (arg0_raw_folder) {
    //Convert from parameters
    let raw_folder = arg0_raw_folder ? arg0_raw_folder : `${h1}/population_Stadester/`;
    
    //Declare local instance variables
    let wcp_file = path.join(raw_folder, "worldcitypop", "chandler_modelski_cities.json");
    
    //Return statement
    return JSON.parse(fs.readFileSync(wcp_file, "utf8"));
  };
  
  /**
   * Checks whether a city name string contains corrupted Unicode replacement characters, question marks, or placeholder text.
   * @alias population_Stadester_uud.isCorruptedCityName
   * 
   * @param {string} arg0_str
   * 
   * @returns {boolean}
   */
  population_Stadester_uud.isCorruptedCityName = function (arg0_str) {
    //Convert from parameters
    let str = (arg0_str !== undefined && arg0_str !== null) ? `${arg0_str}` : "";
    
    //Declare local instance variables
    let trimmed = str.trim();
    
    //Guard clauses
    if (!trimmed) return true;
    if (trimmed === "0" || trimmed === "Unknown" || trimmed === "Settlement" || /^[?\s\-_.,]+$/.test(trimmed))
      return true;
    if (trimmed.includes("?") || trimmed.includes("\uFFFD") || trimmed.includes("\u00EF\u00BF\u00BD"))
      return true;
    
    //Return statement
    return false;
  };
  
  /**
   * Checks whether a candidate name denotes a subordinate district, prefecture, or borough.
   * @alias population_Stadester_uud.isSubordinateDistrictName
   * 
   * @param {string} arg0_name
   * 
   * @returns {boolean}
   */
  population_Stadester_uud.isSubordinateDistrictName = function (arg0_name) {
    //Convert from parameters
    let name = (arg0_name !== undefined && arg0_name !== null) ? `${arg0_name}` : "";
    
    //Declare local instance variables
    let district_terms = [
      "arrondissement", "borough", "county", "district", "locality",
      "new area", "prefecture", "subdistrict", "subprefecture", "suburb",
      "township", "ward", "zone"
    ];
    let lower = name.toLowerCase();
    
    //Guard clauses
    if (!name) return false;
    
    //Function body
    for (let i = 0; i < district_terms.length; i++)
      if (lower.includes(district_terms[i])) return true;
    
    //Return statement
    return false;
  };
  
  /**
   * Strips parenthetical remarks, dataset prefixes, and delimiters from candidate city name strings.
   * @alias population_Stadester_uud.cleanCandidateCityString
   * 
   * @param {string} arg0_name
   * 
   * @returns {string}
   */
  population_Stadester_uud.cleanCandidateCityString = function (arg0_name) {
    //Convert from parameters
    let name = (arg0_name !== undefined && arg0_name !== null) ? `${arg0_name}` : "";
    
    //Declare local instance variables
    let cleaned;
    
    //Guard clauses
    if (!name) return "";
    
    //Function body
    cleaned = name.replace(/\s*\([^)]*\)/g, "").trim();
    cleaned = cleaned.replace(/^ghsl-/i, "").replace(/^stadester-/i, "").replace(/^oxford-/i, "").trim();
    cleaned = cleaned.replace(/^-/, "").trim();
    
    //Return statement
    return cleaned;
  };
  
  /**
   * Parses a raw semicolon-delimited city name list into cleaned, evaluated candidate objects.
   * @alias population_Stadester_uud.parseDelimitedCandidates
   * 
   * @param {string} arg0_raw_name
   * 
   * @returns {Array<Object>}
   */
  population_Stadester_uud.parseDelimitedCandidates = function (arg0_raw_name) {
    //Convert from parameters
    let raw_name = (arg0_raw_name !== undefined && arg0_raw_name !== null) ? `${arg0_raw_name}` : "";
    
    //Declare local instance variables
    let candidate_records = [];
    let raw_parts;
    
    //Guard clauses
    if (!raw_name) return [];
    
    //Function body
    raw_parts = raw_name.split(";");
    
    for (let i = 0; i < raw_parts.length; i++) {
      let raw_part = raw_parts[i].trim();
      if (!raw_part) continue;
      
      let cleaned = population_Stadester_uud.cleanCandidateCityString(raw_part);
      let is_corrupt = population_Stadester_uud.isCorruptedCityName(cleaned);
      let is_subordinate = population_Stadester_uud.isSubordinateDistrictName(cleaned);
      
      candidate_records.push({
        cleanName: cleaned,
        hasSubordinateTerm: is_subordinate,
        isCorrupted: is_corrupt,
        originalText: raw_part,
        rank: i
      });
    }
    
    //Return statement
    return candidate_records;
  };
  
  /**
   * Selects the primary non-corrupted, non-subordinate urban core city name from a delimited candidate list.
   * @alias population_Stadester_uud.getPrimaryCityName
   * 
   * @param {string} arg0_raw_name
   * @param {number} [arg1_target_pop=0]
   * 
   * @returns {string}
   */
  population_Stadester_uud.getPrimaryCityName = function (arg0_raw_name, arg1_target_pop) {
    //Convert from parameters
    let raw_name = (arg0_raw_name !== undefined && arg0_raw_name !== null) ? `${arg0_raw_name}` : "";
    let target_pop = (arg1_target_pop !== undefined) ? Number(arg1_target_pop) : 0;
    
    //Declare local instance variables
    let cand_zero;
    let candidates = population_Stadester_uud.parseDelimitedCandidates(raw_name);
    
    //Guard clauses
    if (candidates.length === 0)
      return population_Stadester_uud.cleanCandidateCityString(raw_name);
    
    cand_zero = candidates[0];
    if (!cand_zero.isCorrupted)
      return cand_zero.cleanName;
    
    for (let i = 1; i < candidates.length; i++) {
      let c = candidates[i];
      if (!c.isCorrupted && !c.hasSubordinateTerm)
        return c.cleanName;
    }
    
    if (target_pop < 150000) {
      for (let i = 1; i < candidates.length; i++) {
        let c = candidates[i];
        if (!c.isCorrupted)
          return c.cleanName;
      }
    }
    
    //Return statement
    return cand_zero.cleanName || population_Stadester_uud.cleanCandidateCityString(raw_name);
  };
  
  /**
   * Loads GHSL source CSV tables into a memory map of ID_UC_G0 / ID_MTUC_G0 to clean city names.
   * @alias population_Stadester_uud.loadGHSLCsvNames
   * 
   * @param {string} [arg0_csv_path]
   * 
   * @returns {Map<string, string>}
   */
  population_Stadester_uud.loadGHSLCsvNames = function (arg0_csv_path) {
    //Convert from parameters
    let csv_path = arg0_csv_path;
    
    //Declare local instance variables
    let candidate_paths = [];
    let lines;
    let raw_text;
    let resolved_path = "";
    
    //Guard clauses
    if (global.population_Stadester_GHSL_map && global.population_Stadester_GHSL_map.size > 0 && !csv_path)
      return global.population_Stadester_GHSL_map;
    
    if (!global.population_Stadester_GHSL_map)
      global.population_Stadester_GHSL_map = new Map();
    
    //Function body
    if (csv_path && fs.existsSync(csv_path)) {
      resolved_path = csv_path;
    } else {
      candidate_paths = [
        path.join(h1, "population_Stadester", "ghsl", "GHSL.csv"),
        path.join(h1, "population_GHSL", "GHSL.csv"),
        path.join(h1, "population_GHSL", "GHS_UCDB_MTUC_GLOBE_R2024A.csv"),
        "D:/Project 1436 - Dataview/data/stadester/GHSL.csv"
      ];
      for (let i = 0; i < candidate_paths.length; i++) {
        if (fs.existsSync(candidate_paths[i])) {
          resolved_path = candidate_paths[i];
          break;
        }
      }
    }
    
    if (!resolved_path || !fs.existsSync(resolved_path)) {
      console.warn(`[population_Stadester_uud] GHSL source file not found.`);
      return global.population_Stadester_GHSL_map;
    }
    
    try {
      raw_text = fs.readFileSync(resolved_path, "utf8").replace(/^\uFEFF/, "");
      lines = raw_text.split(/\r?\n/);
      
      for (let i = 1; i < lines.length; i++) {
        let line = lines[i].trim();
        if (!line) continue;
        
        let parts = line.split(";");
        if (parts.length >= 2) {
          let id_str = parts[0].trim();
          let city_name = parts[1].trim();
          if (id_str && city_name && city_name !== "0" && !population_Stadester_uud.isCorruptedCityName(city_name))
            global.population_Stadester_GHSL_map.set(id_str, city_name);
        }
      }
      console.log(`- Loaded ${global.population_Stadester_GHSL_map.size} clean city names from GHSL source file (${resolved_path}).`);
    } catch (e) {
      console.warn(`[population_Stadester_uud] Error loading GHSL source file:`, e);
    }
    
    //Return statement
    return global.population_Stadester_GHSL_map;
  };
  
  /**
   * Resolves a city display name, prioritizing GHSL source table lookups for GHSL entries and primary core names.
   * @alias population_Stadester_uud.resolveCityDisplayName
   * 
   * @param {string} arg0_key
   * @param {string} [arg1_raw_name]
   * @param {Array<number>} [arg2_coords]
   * @param {number} [arg3_pop=0]
   * @param {number|string} [arg4_id]
   * 
   * @returns {string}
   */
  population_Stadester_uud.resolveCityDisplayName = function (arg0_key, arg1_raw_name, arg2_coords, arg3_pop, arg4_id) {
    //Convert from parameters
    let coords = arg2_coords;
    let id_val = arg4_id;
    let key = (arg0_key !== undefined && arg0_key !== null) ? `${arg0_key}` : "";
    let pop = (arg3_pop !== undefined) ? Number(arg3_pop) : 0;
    let raw_name = (arg1_raw_name !== undefined && arg1_raw_name !== null) ? `${arg1_raw_name}` : "";
    
    //Declare local instance variables
    let ghsl_map = population_Stadester_uud.loadGHSLCsvNames();
    let key_clean;
    let lookup_id = "";
    let primary;
    
    //1. If key is ghsl- or id is passed, lookup in GHSL source CSV table
    if (key.toLowerCase().startsWith("ghsl-") || id_val !== undefined) {
      if (id_val !== undefined && id_val !== null) lookup_id = String(id_val);
      if (!lookup_id && key.toLowerCase().startsWith("ghsl-")) {
        let match = key.match(/\d+/);
        if (match) lookup_id = match[0];
      }
      if (lookup_id && ghsl_map.has(lookup_id)) {
        let csv_name = ghsl_map.get(lookup_id);
        if (csv_name && csv_name !== "0" && !population_Stadester_uud.isCorruptedCityName(csv_name))
          return csv_name;
      }
    }
    
    //2. Extract primary candidate from raw_name
    if (raw_name && raw_name !== "0") {
      primary = population_Stadester_uud.getPrimaryCityName(raw_name, pop);
      if (primary && primary !== "0" && !population_Stadester_uud.isCorruptedCityName(primary))
        return primary;
    }
    
    //3. Fallback to clean candidate from key string
    key_clean = population_Stadester_uud.cleanCandidateCityString(key);
    if (key_clean && key_clean !== "0" && !population_Stadester_uud.isCorruptedCityName(key_clean))
      return key_clean;
    
    //Return statement
    return population_Stadester_uud.cleanCandidateCityString(key);
  };
  
  /**
   * Repairs a single city entry's name using GHSL source table lookups and primary core candidate parsing.
   * @alias population_Stadester_uud.repairGHSLCityName
   * 
   * @param {Object} arg0_city
   * @param {Object} [arg1_options]
   * 
   * @returns {Object}
   */
  population_Stadester_uud.repairGHSLCityName = function (arg0_city, arg1_options) {
    //Convert from parameters
    let city = arg0_city;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let max_pop = 0;
    let old_name;
    let resolved_name;
    
    //Guard clauses
    if (!city) return city;
    
    //Function body
    max_pop = population_Stadester_uud.getPeakPopulation(city.population);
    resolved_name = population_Stadester_uud.resolveCityDisplayName(
      city.key || "",
      city.name || "",
      city.coords,
      max_pop,
      city.id
    );
    
    if (resolved_name && !population_Stadester_uud.isCorruptedCityName(resolved_name)) {
      if (city.name && city.name !== resolved_name) {
        old_name = city.name;
        if (!city.other_names) city.other_names = [];
        if (!city.other_names.includes(old_name)) city.other_names.push(old_name);
      }
      city.name = resolved_name;
    }
    
    //Return statement
    return city;
  };
  
  /**
   * Batch repairs all city entries in a Stadestér or UUD dataset using GHSL source table lookups.
   * @alias population_Stadester_uud.repairGHSLCityNames
   * 
   * @param {Object} arg0_cities_obj
   * @param {Object} [arg1_options]
   * 
   * @returns {Object}
   */
  population_Stadester_uud.repairGHSLCityNames = function (arg0_cities_obj, arg1_options) {
    //Convert from parameters
    let cities_obj = arg0_cities_obj;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let all_keys;
    let repaired_count = 0;
    
    //Guard clauses
    if (!cities_obj) return {};
    
    //Function body
    all_keys = Object.keys(cities_obj);
    for (let i = 0; i < all_keys.length; i++) {
      let city = cities_obj[all_keys[i]];
      let prev_name = city ? city.name : "";
      population_Stadester_uud.repairGHSLCityName(city, options);
      if (city && city.name !== prev_name) repaired_count++;
    }
    
    if (repaired_count > 0)
      console.log(`- Repaired ${repaired_count} GHSL city names across dataset using source file.`);
    
    //Return statement
    return cities_obj;
  };
}
