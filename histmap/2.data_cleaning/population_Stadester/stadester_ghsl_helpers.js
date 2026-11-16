//Initialise functions
{
  if (!global.population_Stadester_ghsl) global.population_Stadester_ghsl = {};
  if (!global.population_Stadester_uud) global.population_Stadester_uud = {};
  
  /**
   * Checks whether two Stadestér country/state codes refer to compatible sovereign/subnational jurisdictions for twin matching.
   * @alias population_Stadester_ghsl.areCompatibleTwinCountries
   * 
   * @param {string} arg0_country_a
   * @param {string} arg1_country_b
   * 
   * @returns {boolean}
   */
  population_Stadester_ghsl.areCompatibleTwinCountries = function (arg0_country_a, arg1_country_b) {
    //Convert from parameters
    let country_a = arg0_country_a;
    let country_b = arg1_country_b;
    
    //Declare local instance variables
    let c_a;
    let c_b;
    let legacy_russia;
    let legacy_uk;
    
    //Function body
    c_a = String(country_a || "").trim().toLowerCase();
    c_b = String(country_b || "").trim().toLowerCase();
    
    //Guard clauses
    if (!c_a || !c_b) return false;
    if (c_a === c_b) return true;
    
    if ((c_a === "usa" && c_b.startsWith("usas-")) || (c_b === "usa" && c_a.startsWith("usas-"))) {
      //Return statement
      return true;
    }
    
    legacy_uk = ["uk", "unkingd", "united kingdom", "great britain"];
    if (legacy_uk.includes(c_a) && legacy_uk.includes(c_b)) {
      //Return statement
      return true;
    }
    
    legacy_russia = ["russia", "russia_polaris_russia", "ussr"];
    if (legacy_russia.includes(c_a) && legacy_russia.includes(c_b)) {
      //Return statement
      return true;
    }
    
    //Return statement
    return false;
  };
  
  /**
   * Returns a census-split-resistant baseline weight for a GHSL cluster member anchored at entry_year.
   * @alias population_Stadester_ghsl.getClusterEntryReferenceWeight
   * 
   * @param {Object} arg0_raw_pop
   * @param {number} [arg1_entry_year=1975]
   * 
   * @returns {number}
   */
  population_Stadester_ghsl.getClusterEntryReferenceWeight = function (arg0_raw_pop, arg1_entry_year) {
    //Convert from parameters
    let entry_year = (arg1_entry_year !== undefined) ? parseInt(arg1_entry_year) : 1975;
    let raw_pop = arg0_raw_pop;
    
    //Declare local instance variables
    let best_pre_yr = -Infinity;
    let earliest_post_val = 0;
    let earliest_post_yr = Infinity;
    let mid_idx;
    let pop_keys;
    let samples = [];
    let val;
    
    //Guard clauses
    if (!raw_pop) return 0;
    
    //Function body
    for (let yr = entry_year - 5; yr <= entry_year; yr++) {
      val = population_Stadester_ghsl.getContinuousCityPopulation(raw_pop, yr);
      if (val > 0) samples.push(val);
    }
    
    if (samples.length > 0) {
      samples.sort((a, b) => a - b);
      mid_idx = Math.floor(samples.length/2);
      if (samples.length % 2 === 1) {
        //Return statement
        return samples[mid_idx];
      } else {
        //Return statement
        return (samples[mid_idx - 1] + samples[mid_idx])/2;
      }
    }
    
    pop_keys = raw_pop._sorted_keys;
    if (!pop_keys) {
      pop_keys = Object.keys(raw_pop).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b);
      Object.defineProperty(raw_pop, "_sorted_keys", { configurable: true, value: pop_keys });
    }
    
    for (let i = 0; i < pop_keys.length; i++) {
      let yr = pop_keys[i];
      let cur_val = Number(raw_pop[yr]) || 0;
      if (cur_val <= 0) continue;
      if (yr >= entry_year - 25 && yr <= entry_year && yr > best_pre_yr)
        best_pre_yr = yr;
      if (yr > entry_year && yr <= 2025 && yr < earliest_post_yr) {
        earliest_post_yr = yr;
        earliest_post_val = cur_val;
      }
    }
    
    if (Number.isFinite(best_pre_yr) && best_pre_yr > -Infinity) {
      //Return statement
      return Number(raw_pop[best_pre_yr]) || 0;
    }
    if (earliest_post_val > 0) {
      //Return statement
      return earliest_post_val;
    }
    
    //Return statement
    return population_Stadester_ghsl.getModernReferencePopulation({ population: raw_pop });
  };
  
  /**
   * Evaluates a pre-GHSL city population dictionary continuously at a target year.
   * @alias population_Stadester_ghsl.getContinuousCityPopulation
   * 
   * @param {Object} arg0_pop_obj
   * @param {number} arg1_year
   * 
   * @returns {number}
   */
  population_Stadester_ghsl.getContinuousCityPopulation = function (arg0_pop_obj, arg1_year) {
    //Convert from parameters
    let pop_obj = arg0_pop_obj;
    let year = Number(arg1_year);
    
    //Declare local instance variables
    let hi;
    let lo;
    let max_yr;
    let mid;
    let pop_keys;
    
    //Guard clauses
    if (!pop_obj || !Number.isFinite(year)) return 0;
    if (pop_obj[year] !== undefined)
      return Math.max(0, Number(pop_obj[year]) || 0);
    
    //Function body
    pop_keys = pop_obj._sorted_keys;
    if (!pop_keys) {
      pop_keys = Object.keys(pop_obj).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b);
      Object.defineProperty(pop_obj, "_sorted_keys", { configurable: true, value: pop_keys });
    }
    if (pop_keys.length === 0) return 0;
    if (year < pop_keys[0]) return 0;
    
    max_yr = pop_keys[pop_keys.length - 1];
    if (year > max_yr) {
      if (max_yr >= 1975 && year >= 1975 && (year - max_yr) <= 200) {
        //Return statement
        return Math.max(0, Number(pop_obj[max_yr]) || 0);
      }
      //Return statement
      return 0;
    }
    
    lo = 0;
    hi = pop_keys.length - 1;
    while (lo <= hi) {
      mid = (lo + hi) >> 1;
      if (pop_keys[mid] === year) {
        //Return statement
        return Math.max(0, Number(pop_obj[pop_keys[mid]]) || 0);
      } else if (pop_keys[mid] < year) {
        lo = mid + 1;
      } else {
        hi = mid - 1;
      }
    }
    
    if (hi >= 0 && lo < pop_keys.length) {
      let gap = pop_keys[lo] - pop_keys[hi];
      let max_gap = (typeof population_Stadester_uud !== "undefined" && typeof population_Stadester_uud.getMaxTemporalProximityGap === "function") ?
        population_Stadester_uud.getMaxTemporalProximityGap(pop_keys[hi], pop_keys[lo]) : 200;
      if (gap > 0 && gap <= max_gap) {
        let v0 = Math.max(0, Number(pop_obj[pop_keys[hi]]) || 0);
        let v1 = Math.max(0, Number(pop_obj[pop_keys[lo]]) || 0);
        
        //Return statement
        return v0 + ((year - pop_keys[hi])/gap)*(v1 - v0);
      }
    }
    
    //Return statement
    return 0;
  };
  
  /**
   * Returns a reference modern population (1975/2000/1970/1980 or latest >=1775) for ranking primary city candidates.
   * @alias population_Stadester_ghsl.getModernReferencePopulation
   * 
   * @param {Object} arg0_city_obj
   * 
   * @returns {number}
   */
  population_Stadester_ghsl.getModernReferencePopulation = function (arg0_city_obj) {
    //Convert from parameters
    let city_obj = arg0_city_obj;
    
    //Declare local instance variables
    let best_yr = -Infinity;
    let best_val = 0;
    let fast_val = 0;
    let pop_keys;
    
    //Guard clauses
    if (!city_obj || !city_obj.population) return 0;
    
    //Function body
    fast_val = Number(
      city_obj.population[1975] ||
      city_obj.population[2000] ||
      city_obj.population[1970] ||
      city_obj.population[1980] ||
      city_obj.population[2010] ||
      city_obj.population[2020] ||
      city_obj.population[2025] ||
      0
    );
    if (fast_val > 0) {
      //Return statement
      return fast_val;
    }
    
    pop_keys = Object.keys(city_obj.population);
    for (let i = 0; i < pop_keys.length; i++) {
      let yr = Number(pop_keys[i]);
      let val = Number(city_obj.population[pop_keys[i]]);
      if (Number.isFinite(yr) && yr >= 1775 && Number.isFinite(val) && val > 0 && yr > best_yr) {
        best_yr = yr;
        best_val = val;
      }
    }
    
    //Return statement
    return best_val;
  };
  
  /**
   * Returns all normalised name tokens for a Stadestér city object for GHSL cluster matching.
   * @alias population_Stadester_ghsl.getNormalisedCityNames
   * 
   * @param {Object} arg0_city_obj
   * 
   * @returns {Array<string>}
   */
  population_Stadester_ghsl.getNormalisedCityNames = function (arg0_city_obj) {
    //Convert from parameters
    let city_obj = arg0_city_obj;
    
    //Declare local instance variables
    let all_raw_names;
    let name_set = new Set();
    let norm_name;
    
    //Guard clauses
    if (!city_obj) return [];
    
    //Function body
    all_raw_names = (population_Stadester_uud && population_Stadester_uud.getAllCityNames) ?
      population_Stadester_uud.getAllCityNames(city_obj) : [];
    
    for (let i = 0; i < all_raw_names.length; i++) {
      norm_name = population_Stadester_ghsl.normaliseGHSLName(all_raw_names[i]);
      if (norm_name) name_set.add(norm_name);
    }
    if (city_obj.name) {
      norm_name = population_Stadester_ghsl.normaliseGHSLName(city_obj.name);
      if (norm_name) name_set.add(norm_name);
    }
    
    //Return statement
    return Array.from(name_set);
  };
  
  /**
   * Smoothly interpolates GHSL 5-year epoch benchmarks (1975-2025) into annual values using
   * Fritsch-Carlson monotone piecewise cubic Hermite interpolation (PCHIP).
   * @alias population_Stadester_ghsl.interpolateGHSLSeries
   * 
   * @param {Object} arg0_series_obj
   * @param {Object} [arg1_options]
   *  @param {Array<number>} [arg1_options.epochs]
   * 
   * @returns {Object} { first_active_ep, last_active_ep, values }
   */
  population_Stadester_ghsl.interpolateGHSLSeries = function (arg0_series_obj, arg1_options) {
    //Convert from parameters
    let options = (arg1_options) ? arg1_options : {};
    let series_obj = arg0_series_obj;
    
    //Declare local instance variables
    let d = [];
    let epochs = options.epochs || [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025];
    let h = [];
    let m;
    let n;
    let values = {};
    let xs = [];
    let ys = [];
    
    //Guard clauses
    if (!series_obj) return { first_active_ep: null, last_active_ep: null, values: values };
    
    //Function body
    for (let i = 0; i < epochs.length; i++) {
      let ep = epochs[i];
      let val = Number(series_obj[ep]);
      if (Number.isFinite(val) && val > 0) {
        xs.push(ep);
        ys.push(val);
      }
    }
    
    n = xs.length;
    if (n === 0) return { first_active_ep: null, last_active_ep: null, values: values };
    if (n === 1) {
      values[xs[0]] = ys[0];
      
      //Return statement
      return { first_active_ep: xs[0], last_active_ep: xs[0], values: values };
    }
    
    for (let i = 0; i < n - 1; i++) {
      let step_h = xs[i + 1] - xs[i];
      h.push(step_h);
      d.push((ys[i + 1] - ys[i])/step_h);
    }
    
    m = new Array(n).fill(0);
    if (n === 2) {
      m[0] = d[0];
      m[1] = d[0];
    } else {
      m[0] = ((2*h[0] + h[1])*d[0] - h[0]*d[1])/(h[0] + h[1]);
      if (m[0]*d[0] <= 0) {
        m[0] = 0;
      } else if (Math.abs(m[0]) > Math.abs(3*d[0])) {
        m[0] = 3*d[0];
      }
      
      m[n - 1] = ((2*h[n - 2] + h[n - 3])*d[n - 2] - h[n - 2]*d[n - 3])/(h[n - 2] + h[n - 3]);
      if (m[n - 1]*d[n - 2] <= 0) {
        m[n - 1] = 0;
      } else if (Math.abs(m[n - 1]) > Math.abs(3*d[n - 2])) {
        m[n - 1] = 3*d[n - 2];
      }
      
      for (let i = 1; i < n - 1; i++) {
        if (d[i - 1]*d[i] <= 0) {
          m[i] = 0;
        } else {
          let w1 = 2*h[i] + h[i - 1];
          let w2 = h[i] + 2*h[i - 1];
          m[i] = (w1 + w2)/(w1/d[i - 1] + w2/d[i]);
        }
      }
    }
    
    for (let i = 0; i < n - 1; i++) {
      let hi = Math.max(ys[i], ys[i + 1]);
      let lo = Math.min(ys[i], ys[i + 1]);
      for (let yr = xs[i]; yr <= xs[i + 1]; yr++) {
        if (yr === xs[i]) {
          values[yr] = ys[i];
        } else if (yr === xs[i + 1]) {
          values[yr] = ys[i + 1];
        } else {
          let t = (yr - xs[i])/h[i];
          let t2 = t*t;
          let t3 = t2*t;
          let interp_val = (2*t3 - 3*t2 + 1)*ys[i] + (t3 - 2*t2 + t)*h[i]*m[i] + (-2*t3 + 3*t2)*ys[i + 1] + (t3 - t2)*h[i]*m[i + 1];
          values[yr] = Math.min(hi, Math.max(lo, interp_val));
        }
      }
    }
    
    //Return statement
    return {
      first_active_ep: xs[0],
      last_active_ep: xs[n - 1],
      values: values
    };
  };
  
  /**
   * Checks whether two co-located cluster member entries represent duplicate records of the same city rather than distinct municipalities or cross-border towns.
   * @alias population_Stadester_ghsl.isCoLocatedCityTwin
   * 
   * @param {Object} arg0_entry_a
   * @param {Object} arg1_entry_b
   * @param {number} arg2_dist_km
   * 
   * @returns {boolean}
   */
  population_Stadester_ghsl.isCoLocatedCityTwin = function (arg0_entry_a, arg1_entry_b, arg2_dist_km) {
    //Convert from parameters
    let dist_km = (arg2_dist_km !== undefined) ? Number(arg2_dist_km) : Infinity;
    let entry_a = arg0_entry_a;
    let entry_b = arg1_entry_b;
    
    //Declare local instance variables
    let c_a;
    let c_b;
    let is_agglom_pair;
    let key_a;
    let key_b;
    let pri_a;
    let pri_b;
    let raw_key_a;
    let raw_key_b;
    let stem_a;
    let stem_b;
    
    //Guard clauses
    if (!entry_a || !entry_b || !entry_a.city || !entry_b.city || !(dist_km <= 50)) return false;
    if (!population_Stadester_ghsl.areCompatibleTwinCountries(entry_a.city.country, entry_b.city.country)) return false;
    
    //Function body
    c_a = String(entry_a.city.country || "");
    c_b = String(entry_b.city.country || "");
    raw_key_a = String(entry_a.key || "");
    raw_key_b = String(entry_b.key || "");
    
    stem_a = (c_a && raw_key_a.endsWith("-" + c_a)) ?
      raw_key_a.slice(0, raw_key_a.length - c_a.length - 1) :
      ((raw_key_a.lastIndexOf("-") >= 0) ? raw_key_a.slice(0, raw_key_a.lastIndexOf("-")) : raw_key_a);
    stem_b = (c_b && raw_key_b.endsWith("-" + c_b)) ?
      raw_key_b.slice(0, raw_key_b.length - c_b.length - 1) :
      ((raw_key_b.lastIndexOf("-") >= 0) ? raw_key_b.slice(0, raw_key_b.lastIndexOf("-")) : raw_key_b);
    
    pri_a = population_Stadester_ghsl.normaliseGHSLName(entry_a.city.name);
    pri_b = population_Stadester_ghsl.normaliseGHSLName(entry_b.city.name);
    key_a = population_Stadester_ghsl.normaliseGHSLName(stem_a);
    key_b = population_Stadester_ghsl.normaliseGHSLName(stem_b);
    
    if ((pri_a && (pri_a === pri_b || pri_a === key_b)) || (key_a && (key_a === pri_b || key_a === key_b))) {
      //Return statement
      return true;
    }
    
    is_agglom_pair = raw_key_a.toLowerCase().includes("agglomeration") ||
      raw_key_b.toLowerCase().includes("agglomeration");
    if (dist_km <= 5 && !is_agglom_pair && population_Stadester_ghsl.matchesAnyGHSLToken(entry_a.norm_names, entry_b.norm_names)) {
      //Return statement
      return true;
    }
    
    //Return statement
    return false;
  };
  
  /**
   * Checks whether any normalised city name matches any normalised GHSL token.
   * @alias population_Stadester_ghsl.matchesAnyGHSLToken
   * 
   * @param {Array<string>} arg0_city_names
   * @param {Array<string>} arg1_tokens
   * 
   * @returns {boolean}
   */
  population_Stadester_ghsl.matchesAnyGHSLToken = function (arg0_city_names, arg1_tokens) {
    //Convert from parameters
    let city_names = arg0_city_names || [];
    let tokens = arg1_tokens || [];
    
    //Function body
    for (let i = 0; i < city_names.length; i++) {
      let c_name = city_names[i];
      if (!c_name) continue;
      for (let x = 0; x < tokens.length; x++) {
        let tok = tokens[x];
        if (!tok) continue;
        if (c_name === tok) return true;
      }
    }
    
    //Return statement
    return false;
  };
  
  /**
   * Normalises a city or GHSL token name by stripping diacritics, parentheticals, and urban suffixes.
   * @alias population_Stadester_ghsl.normaliseGHSLName
   * 
   * @param {string} arg0_name
   * 
   * @returns {string}
   */
  population_Stadester_ghsl.normaliseGHSLName = function (arg0_name) {
    //Convert from parameters
    let name = (arg0_name) ? `${arg0_name}` : "";
    
    //Return statement
    return name
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\([^)]*\)/g, "")
      .replace(/\b(greater|agglomeration|zona urbana|cdp|city|grad|subtotal)\b/gi, "")
      .replace(/['’`´]/g, "")
      .replace(/[^a-zA-Z0-9\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  };
  
  /**
   * Checks whether [lng, lat] falls inside a GeoJSON Polygon or MultiPolygon geometry.
   * @alias population_Stadester_ghsl.pointInGeometry
   * 
   * @param {number} arg0_lng
   * @param {number} arg1_lat
   * @param {Object} arg2_geometry
   * 
   * @returns {boolean}
   */
  population_Stadester_ghsl.pointInGeometry = function (arg0_lng, arg1_lat, arg2_geometry) {
    //Convert from parameters
    let lng = Number(arg0_lng);
    let lat = Number(arg1_lat);
    let geometry = arg2_geometry;
    
    //Guard clauses
    if (!geometry || !geometry.coordinates) return false;
    
    //Function body
    if (geometry.type === "Polygon")
      return population_Stadester_ghsl.pointInPolygon(lng, lat, geometry.coordinates);
    if (geometry.type === "MultiPolygon") {
      for (let i = 0; i < geometry.coordinates.length; i++)
        if (population_Stadester_ghsl.pointInPolygon(lng, lat, geometry.coordinates[i]))
          return true;
    }
    
    //Return statement
    return false;
  };
  
  /**
   * Checks whether [lng, lat] falls inside a Polygon ring array (outer ring minus holes).
   * @alias population_Stadester_ghsl.pointInPolygon
   * 
   * @param {number} arg0_lng
   * @param {number} arg1_lat
   * @param {Array<Array<Array<number>>>} arg2_rings
   * 
   * @returns {boolean}
   */
  population_Stadester_ghsl.pointInPolygon = function (arg0_lng, arg1_lat, arg2_rings) {
    //Convert from parameters
    let lng = Number(arg0_lng);
    let lat = Number(arg1_lat);
    let rings = arg2_rings;
    
    //Guard clauses
    if (!rings || rings.length === 0) return false;
    if (!population_Stadester_ghsl.pointInRing(lng, lat, rings[0])) return false;
    
    //Function body
    for (let i = 1; i < rings.length; i++)
      if (population_Stadester_ghsl.pointInRing(lng, lat, rings[i]))
        return false;
    
    //Return statement
    return true;
  };
  
  /**
   * Ray-casting point-in-ring test for [lng, lat].
   * @alias population_Stadester_ghsl.pointInRing
   * 
   * @param {number} arg0_lng
   * @param {number} arg1_lat
   * @param {Array<Array<number>>} arg2_ring
   * 
   * @returns {boolean}
   */
  population_Stadester_ghsl.pointInRing = function (arg0_lng, arg1_lat, arg2_ring) {
    //Convert from parameters
    let lng = Number(arg0_lng);
    let lat = Number(arg1_lat);
    let ring = arg2_ring;
    
    //Declare local instance variables
    let inside = false;
    
    //Guard clauses
    if (!ring || ring.length < 3) return false;
    
    //Function body
    for (let i = 0, x = ring.length - 1; i < ring.length; x = i++) {
      let xi = ring[i][0];
      let xj = ring[x][0];
      let yi = ring[i][1];
      let yj = ring[x][1];
      let intersect = ((yi > lat) !== (yj > lat)) && (lng < (xj - xi)*(lat - yi)/((yj - yi) || 1e-12) + xi);
      if (intersect) inside = !inside;
    }
    
    //Return statement
    return inside;
  };
  
  global.population_Stadester_ghsl_helpers = true;
}
