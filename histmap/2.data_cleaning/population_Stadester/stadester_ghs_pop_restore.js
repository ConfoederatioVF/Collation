//Initialise functions
{
  if (!global.population_Stadester_ghs_pop) global.population_Stadester_ghs_pop = {};
  if (!global.population_Stadester_config && typeof require !== "undefined")
    try { require(path.join(__dirname, "config", "stadester_config.js")); } catch (e) {}
  if ((!global.population_Stadester_uud || !global.population_Stadester_uud.hasCitySource) && typeof require !== "undefined")
    try { require(path.join(__dirname, "stadester_uud_fixes.js")); } catch (e) {}
  
  /**
   * Restores authoritative empirical POLARIS trajectories (and founding/abandonment bounds) across 1975-2025.
   * Prevents peacetime GHSL/GHS-POP approximations from overriding verified post-1975 censuses or prematurely activating newly founded towns,
   * and zeroes post-lapse years for abandoned post-1975 POLARIS settlements (e.g. Pripyat 1986).
   * @alias population_Stadester_ghs_pop.restoreEmpiricalPolarisTrajectories
   * 
   * @param {Array<Object>} arg0_city_entries
   * @param {Object} [arg1_options]
   * @param {Object} [arg2_stadester_obj]
   * 
   * @returns {number}
   */
  population_Stadester_ghs_pop.restoreEmpiricalPolarisTrajectories = function (arg0_city_entries, arg1_options, arg2_stadester_obj) {
    //Convert from parameters
    let city_entries = Array.isArray(arg0_city_entries) ? arg0_city_entries : [];
    let options = (arg1_options) ? arg1_options : {};
    let stadester_obj = arg2_stadester_obj;
    
    //Declare local instance variables
    let cfg = global.population_Stadester_config;
    let cutoff_year = (options.cutoff_year !== undefined) ?
      options.cutoff_year : ((cfg && cfg.cutoff_year !== undefined) ? cfg.cutoff_year : 1975);
    let end_year = (options.end_year !== undefined) ?
      options.end_year : ((cfg && cfg.end_year !== undefined) ? cfg.end_year : 2025);
    let preserve_manual = (options.preserve_manual_entries !== undefined) ?
      options.preserve_manual_entries :
      ((cfg && cfg.preserve_manual_entries !== undefined) ? cfg.preserve_manual_entries : true);
    let restored_count = 0;
    
    //Guard clauses
    if (city_entries.length === 0 && !stadester_obj) return 0;
    
    //Function body: 1. Zero post-abandonment years on lapsed post-1975 POLARIS cities (e.g. Pripyat)
    if (stadester_obj && typeof stadester_obj === "object") {
      let all_keys = Object.keys(stadester_obj);
      for (let i = 0; i < all_keys.length; i++) {
        let city = stadester_obj[all_keys[i]];
        if (!city || city._raw_lapsed !== true || !city.population) continue;
        if (!population_Stadester_uud.hasCitySource(city, "POLARIS")) continue;
        let bounds = population_Stadester_ghs_pop.getEmpiricalBounds(city);
        if (Number.isFinite(bounds.raw_max_year) && bounds.raw_max_year >= cutoff_year && bounds.raw_max_year < end_year) {
          for (let yr = bounds.raw_max_year + 1; yr <= end_year; yr++)
            city.population[yr] = 0;
        }
      }
    }
    
    //Function body: 2. Restore empirical POLARIS post-1975 observations & found.yr start bounds
    for (let i = 0; i < city_entries.length; i++) {
      let ce = city_entries[i];
      if (!ce || !ce.city || ce.is_suppressed_ucdb_twin || ce.is_suppressed_non_ucdb_twin) continue;
      if (!population_Stadester_uud.hasCitySource(ce.city, "POLARIS")) continue;
      if (preserve_manual && population_Stadester_uud.hasCitySource(ce.city, "manual")) continue;
      if (!ce.city.population) ce.city.population = {};
      
      let eff_start = Math.max(cutoff_year, Number.isFinite(ce.found_yr) ? ce.found_yr : cutoff_year);
      for (let yr = cutoff_year; yr < Math.min(end_year + 1, eff_start); yr++)
        ce.city.population[yr] = 0;
      
      if (Number.isFinite(ce.raw_max_year) && ce.raw_max_year >= cutoff_year) {
        let emp_at_max = 0;
        let end_restore = Math.min(end_year, ce.raw_max_year);
        let has_post_zero = false;
        let model_at_max = Number(ce.city.population[ce.raw_max_year]) || 0;
        
        for (let yr = eff_start; yr <= end_restore; yr++) {
          if (ce.raw_pop && ce.raw_pop[yr] !== undefined && Number(ce.raw_pop[yr]) <= 0) {
            ce.city.population[yr] = 0;
            continue;
          }
          let raw_val = (ce.raw_pop && ce.raw_pop[yr] !== undefined && Number(ce.raw_pop[yr]) > 0) ?
            Number(ce.raw_pop[yr]) :
            ((typeof population_Stadester_ghsl !== "undefined" && typeof population_Stadester_ghsl.getContinuousCityPopulation === "function") ?
              population_Stadester_ghsl.getContinuousCityPopulation(ce.raw_pop, yr) : NaN);
          if (Number.isFinite(raw_val) && raw_val > 0)
            ce.city.population[yr] = Math.round(raw_val);
        }
        
        for (let yr = end_restore + 1; yr <= end_year; yr++) {
          if (ce.raw_pop && ce.raw_pop[yr] !== undefined && Number(ce.raw_pop[yr]) <= 0) {
            ce.city.population[yr] = 0;
            has_post_zero = true;
          }
        }
        
        emp_at_max = Number(ce.city.population[end_restore]) || 0;
        if (!has_post_zero && end_restore < end_year && emp_at_max > 0) {
          for (let yr = end_restore + 1; yr <= end_year; yr++) {
            if (ce.war_years_set && ce.war_years_set.has(yr)) continue;
            if (ce.raw_pop && ce.raw_pop[yr] !== undefined && Number(ce.raw_pop[yr]) <= 0) {
              ce.city.population[yr] = 0;
              continue;
            }
            if (model_at_max > 0 && Number(ce.city.population[yr]) > 0) {
              let drift = Math.min(1.15, Math.max(0.85, Number(ce.city.population[yr])/model_at_max));
              ce.city.population[yr] = Math.max(0, Math.round(emp_at_max*drift));
            } else {
              ce.city.population[yr] = emp_at_max;
            }
          }
        }
        restored_count++;
      }
    }
    
    //Return statement
    return restored_count;
  };
  
  /**
   * Restores curated manual city trajectories (hasCitySource(city, "manual")) when preserve_manual_entries is enabled.
   * @alias population_Stadester_ghs_pop.restoreManualEntries
   * 
   * @param {Array<Object>} arg0_city_entries
   * @param {Object} [arg1_options]
   * 
   * @returns {number}
   */
  population_Stadester_ghs_pop.restoreManualEntries = function (arg0_city_entries, arg1_options) {
    //Convert from parameters
    let city_entries = Array.isArray(arg0_city_entries) ? arg0_city_entries : [];
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let cfg = global.population_Stadester_config;
    let preserve_manual = (options.preserve_manual_entries !== undefined) ?
      options.preserve_manual_entries :
      ((cfg && cfg.preserve_manual_entries !== undefined) ? cfg.preserve_manual_entries : true);
    let restored_count = 0;
    
    //Guard clauses
    if (!preserve_manual || city_entries.length === 0) return 0;
    
    //Function body
    for (let i = 0; i < city_entries.length; i++) {
      let ce = city_entries[i];
      if (ce.city && population_Stadester_uud.hasCitySource(ce.city, "manual") && ce.manual_pop_backup) {
        ce.city.population = Object.assign({}, ce.manual_pop_backup);
        delete ce.city._ghsl_area;
        delete ce.city._ghsl_area_partial;
        restored_count++;
      }
    }
    
    //Return statement
    return restored_count;
  };
  
  /**
   * Restores explicit war-displacement population entries so GHSL/GHS-POP approximations never overwrite active conflict observations.
   * @alias population_Stadester_ghs_pop.restoreWarDisplacementYears
   * 
   * @param {Array<Object>} arg0_city_entries
   * @param {Object} [arg1_options]
   * 
   * @returns {number}
   */
  population_Stadester_ghs_pop.restoreWarDisplacementYears = function (arg0_city_entries, arg1_options) {
    //Convert from parameters
    let city_entries = Array.isArray(arg0_city_entries) ? arg0_city_entries : [];
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let cfg = global.population_Stadester_config;
    let preserve_war = (options.preserve_war_displacement_entries !== undefined) ?
      options.preserve_war_displacement_entries :
      ((cfg && cfg.preserve_war_displacement_entries !== undefined) ? cfg.preserve_war_displacement_entries : true);
    let restored_count = 0;
    
    //Guard clauses
    if (!preserve_war || city_entries.length === 0) return 0;
    
    //Function body
    for (let i = 0; i < city_entries.length; i++) {
      let ce = city_entries[i];
      if (ce.is_suppressed_ucdb_twin || ce.is_suppressed_non_ucdb_twin) continue;
      if (!ce.war_years_set || !ce.war_pop_backup) continue;
      if (!ce.city.population) ce.city.population = {};
      let did_restore = false;
      for (let w_yr of ce.war_years_set) {
        if (ce.war_pop_backup[w_yr] !== undefined) {
          ce.city.population[w_yr] = ce.war_pop_backup[w_yr];
          did_restore = true;
        }
      }
      if (did_restore) restored_count++;
    }
    
    //Return statement
    return restored_count;
  };
  
  /**
   * Streams a top-level dictionary object to JSON with 2-space indentation, avoiding V8 single-string length limits on huge datasets.
   * @alias population_Stadester_ghs_pop.writeJSONSafe
   * 
   * @param {string} arg0_file_path
   * @param {Object} arg1_obj
   */
  population_Stadester_ghs_pop.writeJSONSafe = function (arg0_file_path, arg1_obj) {
    //Convert from parameters
    let file_path = arg0_file_path;
    let obj = arg1_obj;
    
    //Declare local instance variables
    let all_keys;
    let buffer = ["{\n"];
    let buffer_len = 2;
    let fd;
    let flush_threshold = 8*1024*1024;
    let parent_dir = path.dirname(path.resolve(file_path));
    let wrote_any = false;
    
    //Guard clauses
    if (!file_path || !obj) return;
    if (!fs.existsSync(parent_dir)) fs.mkdirSync(parent_dir, { recursive: true });
    
    //Function body
    all_keys = Object.keys(obj);
    fd = fs.openSync(file_path, "w");
    try {
      for (let i = 0; i < all_keys.length; i++) {
        let k = all_keys[i];
        let val_str = JSON.stringify(obj[k], null, 2);
        if (val_str === undefined) continue;
        let prefix = wrote_any ? ",\n  " : "  ";
        let chunk = `${prefix}${JSON.stringify(k)}: ${val_str.replace(/\n/g, "\n  ")}`;
        buffer.push(chunk);
        buffer_len += chunk.length;
        wrote_any = true;
        if (buffer_len >= flush_threshold) {
          fs.writeSync(fd, buffer.join(""), null, "utf8");
          buffer = [];
          buffer_len = 0;
        }
      }
      if (!wrote_any) {
        fs.writeSync(fd, "{}", null, "utf8");
      } else {
        buffer.push("\n}");
        fs.writeSync(fd, buffer.join(""), null, "utf8");
      }
    } finally {
      fs.closeSync(fd);
    }
  };
  
  global.population_Stadester_ghs_pop_restore_loaded = true;
}
