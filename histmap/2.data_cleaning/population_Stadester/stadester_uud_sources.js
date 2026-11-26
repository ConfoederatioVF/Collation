//Initialise functions
{
  if (!global.population_Stadester_uud) global.population_Stadester_uud = {};
  if (!global.JSON5 && typeof require !== "undefined")
    try { global.JSON5 = require("json5"); } catch (e) {}
  if (!global.population_Stadester_config && typeof require !== "undefined")
    try { require(path.join(__dirname, "config", "stadester_config.js")); } catch (e) {}
  
  /**
   * Normalises Eastern European / Slavic romanisation variants so Populstat caron backticks
   * and modern transliterations match reliably within compatible jurisdictions.
   * @alias population_Stadester_uud.normaliseSlavicName
   *
   * @param {string} arg0_name
   *
   * @returns {string}
   */
  population_Stadester_uud.normaliseSlavicName = function (arg0_name) {
    //Convert from parameters
    let name = population_Stadester_uud.processCityName(arg0_name);

    //Guard clauses
    if (!name) return "";

    //Function body
    let norm = name
      .replace(/_[A-Za-z]{2}_\d+$/, "")
      .toLowerCase()
      .replace(/[ûŭ]/g, "u")
      .replace(/[ёë]/g, "e")
      .replace(/['’`´]o/g, "e")
      .replace(/yo|jo/g, "e")
      .replace(/aw/g, "au")
      .replace(/ow/g, "ou")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/['’`´\-.,\s]/g, "")
      .replace(/nadonu|ondon|nadone/g, "don")
      .replace(/shch/g, "sc")
      .replace(/szcz/g, "sc")
      .replace(/zh/g, "z")
      .replace(/sh/g, "s")
      .replace(/sz/g, "s")
      .replace(/kh|ch|cz/g, "c")
      .replace(/ts/g, "c")
      .replace(/j/g, "y")
      .replace(/yi|iy|yy|ii/g, "i")
      .replace(/y/g, "i")
      .replace(/ia/g, "a")
      .replace(/ie/g, "e")
      .replace(/io/g, "o")
      .replace(/iu/g, "u")
      .replace(/(.)\1+/g, "$1");

    //Return statement
    return norm;
  };


  /**
   * Normalises Western European and North American city names (punctuation, accents,
   * Saint/St./Sainte abbreviations, and trailing province/district tags).
   * @alias population_Stadester_uud.normaliseWesternName
   *
   * @param {string} arg0_name
   *
   * @returns {string}
   */
  population_Stadester_uud.normaliseWesternName = function (arg0_name) {
    //Convert from parameters
    let name = population_Stadester_uud.processCityName(arg0_name);

    //Declare local instance variables
    let norm;

    //Guard clauses
    if (!name) return "";

    //Function body
    norm = name
      .replace(/,\s*(toronto|montreal|montréal|ottawa|quebec|québec|vancouver|winnipeg|halifax|hamilton|calgary|edmonton|victoria)$/i, "")
      .replace(/-(?:on|qc|nb|ns|pe|pei|nl|mb|sk|ab|bc|yt|nt|nu|kujalleq|kona|kohala|kaua['’ʻ]?i)$/, "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/['’`´ʻʼ]/g, "")
      .replace(/[-.,/]/g, " ")
      .replace(/\bste\b/g, "sainte")
      .replace(/\bst\b/g, "saint")
      .replace(/\s+/g, " ")
      .trim();

    //Return statement
    return norm;
  };


  population_Stadester_uud.us_states = [
    "Alabama", "Alaska", "American Samoa", "Arizona", "Arkansas", "California",
    "Colorado", "Connecticut", "Delaware", "District of Columbia", "Florida",
    "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas",
    "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Puerto Rico",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas",
    "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
  ];


  /**
   * Checks whether a given country string represents the United States (country-level) or a US state/territory.
   * @alias population_Stadester_uud.isUSCountryOrState
   *
   * @param {string} arg0_country
   *
   * @returns {boolean}
   */
  population_Stadester_uud.isUSCountryOrState = function (arg0_country) {
    //Convert from parameters
    let country = (arg0_country) ? String(arg0_country).toLowerCase().trim() : "";

    //Declare local instance variables
    let us_aliases = ["united states", "united states of america", "usa", "uniteds"];

    //Guard clauses
    if (!country) return false;
    if (us_aliases.includes(country)) return true;

    //Function body
    for (let i = 0; i < population_Stadester_uud.us_states.length; i++)
      if (country === population_Stadester_uud.us_states[i].toLowerCase()) return true;

    //Return statement
    return false;
  };


  /**
   * Checks whether two jurisdictions are compatible US entities (e.g. "United States" and "New York").
   * @alias population_Stadester_uud.areCompatibleUSCountries
   *
   * @param {string} arg0_country_a
   * @param {string} arg1_country_b
   *
   * @returns {boolean}
   */
  population_Stadester_uud.areCompatibleUSCountries = function (arg0_country_a, arg1_country_b) {
    //Convert from parameters
    let c_a = (arg0_country_a) ? String(arg0_country_a).toLowerCase().trim() : "";
    let c_b = (arg1_country_b) ? String(arg1_country_b).toLowerCase().trim() : "";

    //Guard clauses
    if (!c_a || !c_b) return false;
    if (c_a === c_b) return true;

    //Function body
    let is_us_a = (c_a === "united states" || c_a === "united states of america" || c_a === "usa" || c_a === "uniteds");
    let is_us_b = (c_b === "united states" || c_b === "united states of america" || c_b === "usa" || c_b === "uniteds");

    if (is_us_a && population_Stadester_uud.isUSCountryOrState(c_b)) return true;
    if (is_us_b && population_Stadester_uud.isUSCountryOrState(c_a)) return true;

    //Return statement
    return false;
  };


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
    let checkPeakFallback = function () {
      let peak_a = population_Stadester_uud.getPeakPopulation(pop_a);
      let peak_b = population_Stadester_uud.getPeakPopulation(pop_b);
      if (peak_a > 0 && peak_b > 0) {
        let ratio = peak_a/peak_b;
        if (ratio < 0.1 || ratio > 10.0) return { valid: false, overlaps: false };
      }
      return { valid: true, overlaps: false };
    };
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
    if (int_start > int_end) return checkPeakFallback();
    
    let all_keys = Array.from(new Set([...keys_a, ...keys_b])).sort((a, b) => a - b);
    let check_keys = all_keys.filter(yr => yr >= int_start && yr <= int_end);
    let getValueAtYear = function (pop, keys, yr) {
      if (pop[yr] !== undefined) return parseFloat(Array.isArray(pop[yr]) ? pop[yr][0] : pop[yr]);
      let lower = keys[0], upper = keys[keys.length - 1];
      for (let j = 0; j < keys.length; j++) {
        if (keys[j] < yr) lower = keys[j];
        if (keys[j] > yr) { upper = keys[j]; break; }
      }
      let vl = parseFloat(Array.isArray(pop[lower]) ? pop[lower][0] : pop[lower]);
      let vu = parseFloat(Array.isArray(pop[upper]) ? pop[upper][0] : pop[upper]);
      if (!isNaN(vl) && !isNaN(vu) && upper !== lower) return vl + (vu - vl)*((yr - lower)/(upper - lower));
      return isNaN(vl) ? vu : vl;
    };
    
    for (let k = 0; k < check_keys.length; k++) {
      let yr = check_keys[k];
      let num_a = getValueAtYear(pop_a, keys_a, yr), num_b = getValueAtYear(pop_b, keys_b, yr);
      if (!isNaN(num_a) && !isNaN(num_b) && num_a > 0 && num_b > 0) {
        valid_checks++;
        let ratio = num_a/num_b;
        if (ratio < 0.25 || ratio > 4.0) fail_count++;
      }
    }
    if (valid_checks === 0) return checkPeakFallback();
    if ((fail_count/valid_checks) > 0.5 || (valid_checks <= 2 && fail_count === valid_checks))
      return { valid: false, overlaps: true };
    
    //Return statement
    return { valid: true, overlaps: true };
  };
  
  /**
   * Lazily builds and caches the global exonym group lookup from `viscount_skill_profiles.json5`.
   * @alias population_Stadester_uud.getExonymLookup
   *
   * @returns {{ audit: Object|null, stem_to_group: Map<string, number> }}
   */
  population_Stadester_uud.getExonymLookup = function () {
    //Function body
    if (global._cached_uud_exonym_lookup !== undefined)
      return global._cached_uud_exonym_lookup;

    let audit_mod = null;
    let stem_to_group = new Map();

    try {
      let audit_mod_path = path.resolve(__dirname, "../../../.agents/skills/population-regional-study/scripts/viscount_entity_and_continuity_audit.js");
      audit_mod = fs.existsSync(audit_mod_path) ? require(audit_mod_path).viscount_entity_audit : null;
      let profiles = (audit_mod) ? audit_mod.loadSkillProfiles() : null;
      let groups = (profiles && Array.isArray(profiles.romanisation_equivalences)) ? profiles.romanisation_equivalences : [];
      for (let i = 0; i < groups.length; i++) {
        let grp = groups[i];
        if (!Array.isArray(grp)) continue;
        for (let x = 0; x < grp.length; x++) {
          let item = String(grp[x] || "");
          if (item) stem_to_group.set(item, i);
        }
      }
    } catch (e) {
      audit_mod = null;
    }

    global._cached_uud_exonym_lookup = { audit: audit_mod, stem_to_group: stem_to_group };

    //Return statement
    return global._cached_uud_exonym_lookup;
  };


  /**
   * Builds and memoises a non-enumerable name/stem/exonym index on a city object for O(1) matching.
   * @alias population_Stadester_uud.getCityNameIndex
   *
   * @param {Object} arg0_city
   *
   * @returns {Object}
   */
  population_Stadester_uud.getCityNameIndex = function (arg0_city) {
    //Convert from parameters
    let city = arg0_city;

    //Guard clauses
    if (!city || typeof city !== "object") {
      return {
        comp_set: null,
        entity_stems: null,
        exonym_groups: null,
        name_set: new Set(),
        names: [],
        prim: "",
        sig: "",
        slavic_set: null,
        west_set: null
      };
    }

    //Declare local instance variables
    let other_len = Array.isArray(city.other_names) ? city.other_names.length : 0;
    let orig_len = Array.isArray(city.original_names) ? city.original_names.length : 0;
    let sig = `${city.name || ""}|${city.country || ""}|${other_len}|${orig_len}`;

    if (city._uud_name_idx && city._uud_name_idx.sig === sig)
      return city._uud_name_idx;

    let name_set = new Set();
    let names = [];
    let raw_list = [];

    //Function body
    if (city.name) {
      let norm_res = (global.stadester_name_normaliser) ?
        global.stadester_name_normaliser.normaliseCityName(city.name, city.country) :
        { extra_aliases: [], name: city.name };
      if (norm_res.name) raw_list.push(norm_res.name);
      raw_list.push(city.name);
      if (norm_res.extra_aliases.length > 0) raw_list = raw_list.concat(norm_res.extra_aliases);
    }
    if (other_len > 0) raw_list = raw_list.concat(city.other_names);
    if (orig_len > 0) raw_list = raw_list.concat(city.original_names);

    for (let k = 0; k < raw_list.length; k++) {
      let decoded = (global.stadester_name_normaliser) ?
        global.stadester_name_normaliser.decodeHaceksAndQuotes(raw_list[k], city.country) : raw_list[k];
      let stat_clean = (global.stadester_name_normaliser) ?
        global.stadester_name_normaliser.cleanStatisticalWrapper(decoded, city.country) : decoded;
      let proc = population_Stadester_uud.processCityName(stat_clean || raw_list[k]);
      if (proc && !name_set.has(proc)) {
        name_set.add(proc);
        names.push(proc);
      }
      if (decoded && decoded !== stat_clean) {
        let proc_dec = population_Stadester_uud.processCityName(decoded);
        if (proc_dec && !name_set.has(proc_dec)) {
          name_set.add(proc_dec);
          names.push(proc_dec);
        }
      }
    }

    let idx = {
      comp_set: null,
      entity_stems: null,
      exonym_groups: null,
      name_set: name_set,
      names: names,
      prim: city.name ? population_Stadester_uud.processCityName(city.name) : "",
      sig: sig,
      slavic_set: null,
      west_set: null
    };

    Object.defineProperty(city, "_uud_name_idx", {
      configurable: true,
      enumerable: false,
      value: idx,
      writable: true
    });

    //Return statement
    return idx;
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
    //Return statement
    return population_Stadester_uud.getCityNameIndex(arg0_city).names;
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

    //Guard clauses
    if (!city_a || !city_b) return false;

    //Declare local instance variables
    let idx_a = population_Stadester_uud.getCityNameIndex(city_a);
    let idx_b = population_Stadester_uud.getCityNameIndex(city_b);
    let key_a = city_a.key ? String(city_a.key).toLowerCase() : "";
    let key_b = city_b.key ? String(city_b.key).toLowerCase() : "";
    let name_a_prim = idx_a.prim;
    let name_b_prim = idx_b.prim;

    //Guard clauses: Brooklyn-New York is a distinct historical entity before 1898 and must NEVER match New York
    if (
      (name_a_prim === "brooklyn" && (name_b_prim === "new york" || name_b_prim === "new york city")) ||
      (name_b_prim === "brooklyn" && (name_a_prim === "new york" || name_a_prim === "new york city")) ||
      (key_a.startsWith("brooklyn-") && key_b.startsWith("new york-")) ||
      (key_b.startsWith("brooklyn-") && key_a.startsWith("new york-"))
    ) {
      return false;
    }

    //Function body: 1. O(1) Set intersection on exact processed names
    let small_set = (idx_a.name_set.size <= idx_b.name_set.size) ? idx_a.name_set : idx_b.name_set;
    let large_set = (idx_a.name_set.size <= idx_b.name_set.size) ? idx_b.name_set : idx_a.name_set;
    for (let nm of small_set) {
      if (nm && large_set.has(nm)) return true;
    }

    let c_a = city_a.country ? String(city_a.country).toLowerCase().trim() : "";
    let c_b = city_b.country ? String(city_b.country).toLowerCase().trim() : "";

    if (!global._uud_slavic_countries_set) {
      global._uud_slavic_countries_set = new Set([
        "belarus", "bulgaria", "estonia", "finland", "kazakhstan", "latvia",
        "lithuania", "moldova", "poland", "russia", "serbia", "ukraine", "ussr"
      ]);
    }
    if (!global._uud_slavic_alias_pairs_norm) {
      let raw_pairs = [
        ["Dymytrov", "Myrnohrad"],
        ["Krasnoarmijs'k", "Pokrovsk"],
        ["Stachanov", "Kadiivka"],
        ["Krasnyj Lu`c", "Khrustalnyi"],
        ["Torez", "Chystiakove"],
        ["Krasnodon", "Sorokyne"],
        ["Sverdlovs'k", "Dovzhansk"],
        ["Kirovsk", "Holubivka"],
        ["Illi`civs'k", "Chornomorsk"],
        ["Komsomol's'k", "Horishni Plavni"],
        ["Atomgrad", "Zheleznogorsk"],
        ["Ivanovo", "Ivanovo-Voznesensk"],
        ["Abakan", "Ust-Abakanskoe"],
        ["Korolev", "Kaliningrad"],
        ["Rostov", "Rostov Veliky"],
        ["Mstislaw", "Mscislau"],
        ["Raha`caû", "Rahachow"],
        ["Beryozovsky", "Berëzovski"],
        ["Gus'-Chrustal'nyj", "Gus'-Hrustal'nyj"],
        ["Charkiv", "Kharkiv"],
        ["Borovi`'ci", "Borovichi"]
      ];
      global._uud_slavic_alias_pairs_norm = raw_pairs.map(function (arg0_p) {
        return [
          population_Stadester_uud.normaliseSlavicName(arg0_p[0]),
          population_Stadester_uud.normaliseSlavicName(arg0_p[1])
        ];
      });
    }

    if (c_a && c_a === c_b && global._uud_slavic_countries_set.has(c_a)) {
      if (!idx_a.slavic_set) {
        let s_set = new Set();
        for (let i = 0; i < idx_a.names.length; i++) {
          let ns = population_Stadester_uud.normaliseSlavicName(idx_a.names[i]);
          if (ns.length >= 4) s_set.add(ns);
        }
        idx_a.slavic_set = s_set;
      }
      if (!idx_b.slavic_set) {
        let s_set = new Set();
        for (let i = 0; i < idx_b.names.length; i++) {
          let ns = population_Stadester_uud.normaliseSlavicName(idx_b.names[i]);
          if (ns.length >= 4) s_set.add(ns);
        }
        idx_b.slavic_set = s_set;
      }
      for (let sn of idx_a.slavic_set) {
        if (idx_b.slavic_set.has(sn)) return true;
      }
      let has_close_coords = Boolean(
        Array.isArray(city_a.coords) && Array.isArray(city_b.coords) &&
        typeof population_Stadester_uud.haversineDistance === "function" &&
        population_Stadester_uud.haversineDistance(city_a.coords, city_b.coords) <= 18
      );
      if (has_close_coords) {
        let pairs = global._uud_slavic_alias_pairs_norm;
        for (let i = 0; i < pairs.length; i++) {
          let p0 = pairs[i][0];
          let p1 = pairs[i][1];
          if ((idx_a.slavic_set.has(p0) && idx_b.slavic_set.has(p1)) || (idx_a.slavic_set.has(p1) && idx_b.slavic_set.has(p0)))
            return true;
        }
      }
    }

    let west_dist_km = (
      Array.isArray(city_a.coords) && Array.isArray(city_b.coords) &&
      typeof population_Stadester_uud.haversineDistance === "function"
    ) ? population_Stadester_uud.haversineDistance(city_a.coords, city_b.coords) : Infinity;
    let has_west_close_coords = (west_dist_km <= 25);
    let is_compat_west_country = (
      (c_a && c_a === c_b) ||
      c_a === "united states" ||
      c_b === "united states" ||
      c_a === "united states of america" ||
      c_b === "united states of america" ||
      (typeof population_Stadester_uud.areCompatibleUSCountries === "function" &&
        population_Stadester_uud.areCompatibleUSCountries(c_a, c_b)) ||
      (
        typeof population_Stadester_ghsl !== "undefined" &&
        typeof population_Stadester_ghsl.areCompatibleTwinCountries === "function" &&
        population_Stadester_ghsl.areCompatibleTwinCountries(city_a.country, city_b.country)
      )
    );
    if (has_west_close_coords && is_compat_west_country) {
      if (!idx_a.west_set) {
        let w_set = new Set();
        let c_set = new Set();
        for (let i = 0; i < idx_a.names.length; i++) {
          let nw = population_Stadester_uud.normaliseWesternName(idx_a.names[i]);
          if (nw.length >= 3) {
            w_set.add(nw);
            let cw = nw.replace(/\s+/g, "").replace(/(.)\1+/g, "$1");
            if (cw.length >= 5) c_set.add(cw);
          }
        }
        idx_a.west_set = w_set;
        idx_a.comp_set = c_set;
      }
      if (!idx_b.west_set) {
        let w_set = new Set();
        let c_set = new Set();
        for (let i = 0; i < idx_b.names.length; i++) {
          let nw = population_Stadester_uud.normaliseWesternName(idx_b.names[i]);
          if (nw.length >= 3) {
            w_set.add(nw);
            let cw = nw.replace(/\s+/g, "").replace(/(.)\1+/g, "$1");
            if (cw.length >= 5) c_set.add(cw);
          }
        }
        idx_b.west_set = w_set;
        idx_b.comp_set = c_set;
      }
      for (let wn of idx_a.west_set) {
        if (idx_b.west_set.has(wn)) return true;
      }
      if (west_dist_km <= 15.0) {
        for (let cn of idx_a.comp_set) {
          if (idx_b.comp_set.has(cn)) return true;
        }
      }

      let ex_lookup = population_Stadester_uud.getExonymLookup();
      if (ex_lookup && ex_lookup.audit) {
        if (!idx_a.entity_stems) {
          let es = new Set();
          let eg = new Set();
          for (let i = 0; i < idx_a.names.length; i++) {
            let st = ex_lookup.audit.normaliseEntityStem(idx_a.names[i]);
            if (st) {
              es.add(st);
              let grp = ex_lookup.stem_to_group.get(st);
              if (grp !== undefined) eg.add(grp);
            }
          }
          idx_a.entity_stems = es;
          idx_a.exonym_groups = eg;
        }
        if (!idx_b.entity_stems) {
          let es = new Set();
          let eg = new Set();
          for (let i = 0; i < idx_b.names.length; i++) {
            let st = ex_lookup.audit.normaliseEntityStem(idx_b.names[i]);
            if (st) {
              es.add(st);
              let grp = ex_lookup.stem_to_group.get(st);
              if (grp !== undefined) eg.add(grp);
            }
          }
          idx_b.entity_stems = es;
          idx_b.exonym_groups = eg;
        }
        for (let st of idx_a.entity_stems) {
          if (idx_b.entity_stems.has(st)) return true;
        }
        for (let grp of idx_a.exonym_groups) {
          if (idx_b.exonym_groups.has(grp)) return true;
        }
      }
    }

    //Return statement
    return false;
  };

  /**
   * Computes lossless inverted-index tokens covering all exact, western, Slavic, exonym,
   * and Class 2 subdivision conditions under which `canMergeMunicipalities()` can allow a merge.
   * @alias population_Stadester_uud.getCityMatchTokens
   *
   * @param {Object} arg0_city
   *
   * @returns {Array<string>}
   */
  population_Stadester_uud.getCityMatchTokens = function (arg0_city) {
    //Convert from parameters
    let city = arg0_city;

    //Guard clauses
    if (!city || typeof city !== "object") return [];

    //Declare local instance variables
    let idx = population_Stadester_uud.getCityNameIndex(city);
    let norm = population_Stadester_uud.getNameNormaliser();
    let tokens = new Set();

    //Function body
    for (let nm of idx.name_set)
      if (nm) tokens.add(`nm:${nm}`);

    if (!idx.west_set) {
      let w_set = new Set();
      let c_set = new Set();
      for (let i = 0; i < idx.names.length; i++) {
        let nw = population_Stadester_uud.normaliseWesternName(idx.names[i]);
        if (nw.length >= 3) {
          w_set.add(nw);
          let cw = nw.replace(/\s+/g, "").replace(/(.)\1+/g, "$1");
          if (cw.length >= 5) c_set.add(cw);
        }
      }
      idx.west_set = w_set;
      idx.comp_set = c_set;
    }
    for (let wn of idx.west_set) tokens.add(`ws:${wn}`);
    for (let cn of idx.comp_set) tokens.add(`cs:${cn}`);

    let c_low = city.country ? String(city.country).toLowerCase().trim() : "";
    if (!global._uud_slavic_countries_set) {
      global._uud_slavic_countries_set = new Set([
        "belarus", "bulgaria", "estonia", "finland", "kazakhstan", "latvia",
        "lithuania", "moldova", "poland", "russia", "serbia", "ukraine", "ussr"
      ]);
    }
    if (c_low && global._uud_slavic_countries_set.has(c_low)) {
      if (!idx.slavic_set) {
        let s_set = new Set();
        for (let i = 0; i < idx.names.length; i++) {
          let ns = population_Stadester_uud.normaliseSlavicName(idx.names[i]);
          if (ns.length >= 4) s_set.add(ns);
        }
        idx.slavic_set = s_set;
      }
      for (let sn of idx.slavic_set) tokens.add(`sl:${sn}`);
      if (global._uud_slavic_alias_pairs_norm) {
        let pairs = global._uud_slavic_alias_pairs_norm;
        for (let i = 0; i < pairs.length; i++) {
          if (idx.slavic_set.has(pairs[i][0])) tokens.add(`sl:${pairs[i][1]}`);
          if (idx.slavic_set.has(pairs[i][1])) tokens.add(`sl:${pairs[i][0]}`);
        }
      }
    }

    let ex_lookup = population_Stadester_uud.getExonymLookup();
    if (ex_lookup && ex_lookup.audit) {
      if (!idx.entity_stems) {
        let es = new Set();
        let eg = new Set();
        for (let i = 0; i < idx.names.length; i++) {
          let st = ex_lookup.audit.normaliseEntityStem(idx.names[i]);
          if (st) {
            es.add(st);
            let grp = ex_lookup.stem_to_group.get(st);
            if (grp !== undefined) eg.add(grp);
          }
        }
        idx.entity_stems = es;
        idx.exonym_groups = eg;
      }
      for (let st of idx.entity_stems) tokens.add(`es:${st}`);
      for (let grp of idx.exonym_groups) tokens.add(`eg:${grp}`);
    }

    if (city._subdiv_id) tokens.add(`sd:${city._subdiv_id}`);
    if (norm) {
      let c_norm = norm.normaliseCountryName(city.country);
      let cur_fold = norm.foldAscii(city.name);
      if (c_norm && cur_fold) tokens.add(`pn:${c_norm}:${cur_fold}`);
      if (c_norm && city._parent_mun_meta && city._parent_mun_meta.parent_name) {
        let par_fold = norm.foldAscii(city._parent_mun_meta.parent_name);
        if (par_fold) tokens.add(`pn:${c_norm}:${par_fold}`);
      }
    }

    //Return statement
    return Array.from(tokens);
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
      let k = all_ot_population_keys[i];
      let local_value = ot_population_obj[k];
      if (Array.isArray(local_value)) local_value = local_value.flat(Infinity);
      let arr_val = Array.isArray(local_value) ? local_value : [local_value];
      population_obj[k] = Array.isArray(population_obj[k]) ? population_obj[k].concat(arr_val) : arr_val;
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
      let orig_src = (target_city.name ? [target_city.name] : []).concat(Array.isArray(target_city.other_names) ? target_city.other_names : []);
      for (let i = 0; i < orig_src.length; i++) {
        let proc_n = population_Stadester_uud.processCityName(orig_src[i]);
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
    let allow_identity_update = (
      typeof population_Stadester_uud.hasViscountSource !== "function" ||
      !population_Stadester_uud.hasViscountSource(target_city) ||
      population_Stadester_uud.hasViscountSource(source_city)
    );
    let source_peak = population_Stadester_uud.getPeakPopulation(source_city.population);
    if (allow_identity_update && source_city.name && source_peak >= (target_city.name_peaks[source_city.name] || 0)) {
      target_city.name_peaks[source_city.name] = source_peak;
      if (source_city.coords) target_city.name_coords[source_city.name] = source_city.coords;
    }
    if (allow_identity_update && source_city.name_peaks) {
      let s_keys = Object.keys(source_city.name_peaks);
      for (let i = 0; i < s_keys.length; i++) {
        let k = s_keys[i], p = source_city.name_peaks[k];
        if (p >= (target_city.name_peaks[k] || 0)) {
          target_city.name_peaks[k] = p;
          let sc = (source_city.name_coords && source_city.name_coords[k]) ? source_city.name_coords[k] : source_city.coords;
          if (sc) target_city.name_coords[k] = sc;
        }
      }
    }
    if (allow_identity_update) {
      let max_name_peak = -1, all_name_keys = Object.keys(target_city.name_peaks);
      for (let i = 0; i < all_name_keys.length; i++) {
        let k = all_name_keys[i], p = target_city.name_peaks[k];
        if (p > max_name_peak) { max_name_peak = p; best_name = k; }
      }
      if (best_name) {
        target_city.name = best_name;
        if (target_city.name_coords && target_city.name_coords[best_name]) target_city.coords = target_city.name_coords[best_name];
      }
    }
    if (!target_city.other_names) target_city.other_names = [];
    if (old_target_name) candidate_names.push(old_target_name);
    if (source_city.name) candidate_names.push(source_city.name);
    if (Array.isArray(source_city.other_names)) candidate_names = candidate_names.concat(source_city.other_names);
    if (Array.isArray(target_city.other_names)) candidate_names = candidate_names.concat(target_city.other_names);
    for (let i = 0; i < candidate_names.length; i++)
      if (candidate_names[i] && candidate_names[i] !== target_city.name && !target_city.other_names.includes(candidate_names[i]))
        target_city.other_names.push(candidate_names[i]);
    if (source_city.is_agglomeration_of) target_city.is_agglomeration_of = source_city.is_agglomeration_of;
    if (source_city["found.yr"] !== undefined && (target_city["found.yr"] === undefined || Number(source_city["found.yr"]) < Number(target_city["found.yr"])))
      target_city["found.yr"] = source_city["found.yr"];
    if (source_city._raw_lapsed === true)
      target_city._raw_lapsed = true;
    if (Number.isFinite(source_city._annexation_year) && !Number.isFinite(target_city._annexation_year))
      target_city._annexation_year = source_city._annexation_year;
    if (Array.isArray(source_city.original_names)) {
      for (let i = 0; i < source_city.original_names.length; i++)
        if (source_city.original_names[i] && !target_city.original_names.includes(source_city.original_names[i]))
          target_city.original_names.push(source_city.original_names[i]);
    }
    if (Array.isArray(source_city._war_displacement_years)) {
      if (!target_city._war_displacement_years) target_city._war_displacement_years = [];
      for (let i = 0; i < source_city._war_displacement_years.length; i++)
        if (!target_city._war_displacement_years.includes(source_city._war_displacement_years[i]))
          target_city._war_displacement_years.push(source_city._war_displacement_years[i]);
    }
    if (typeof population_Stadester_uud.appendCitySources === "function")
      population_Stadester_uud.appendCitySources(target_city, source_city.sources || source_city.type);
    if (source_city.population) {
      if (target_city._from_districts_only === true && source_city._from_districts_only !== true && source_city._is_intra_district !== true) {
        target_city._from_districts_only = false;
        if (!target_city.population) target_city.population = {};
        let s_peak = population_Stadester_uud.getPeakPopulation(source_city.population);
        let t_yrs = Object.keys(target_city.population);
        for (let i = 0; i < t_yrs.length; i++) {
          let yk = t_yrs[i];
          let yn = parseInt(yk, 10);
          let tv = Number(target_city.population[yk] || 0);
          if (Number.isFinite(yn) && yn >= 1900 && s_peak > 0 && tv < 0.05*s_peak)
            delete target_city.population[yk];
        }
        let s_yrs = Object.keys(source_city.population);
        for (let i = 0; i < s_yrs.length; i++) {
          let yk = s_yrs[i];
          let yn = parseInt(yk, 10);
          let sv = Number(source_city.population[yk] || 0);
          let tv = Number(target_city.population[yk] || 0);
          if (sv > 0 && (!(tv > 0) || (Number.isFinite(yn) && yn >= 1900 && sv > tv)))
            target_city.population[yk] = sv;
        }
      } else if (source_city._from_districts_only === true || source_city._is_intra_district === true) {
        if (!target_city.population) target_city.population = {};
        let s_yrs = Object.keys(source_city.population);
        for (let i = 0; i < s_yrs.length; i++) {
          let yk = s_yrs[i];
          let sv = Number(source_city.population[yk] || 0);
          let tv = Number(target_city.population[yk] || 0);
          if (sv > 0 && (!(tv > 0) || sv > tv))
            target_city.population[yk] = sv;
        }
      } else if (is_metro) {
        if (!target_city.population) target_city.population = {};
        if (!target_city.metro_population) target_city.metro_population = {};
        if (!Array.isArray(target_city._metro_only_years)) target_city._metro_only_years = [];
        let s_yrs = Object.keys(source_city.population);
        for (let i = 0; i < s_yrs.length; i++) {
          let yk = s_yrs[i];
          let yn = parseInt(yk, 10);
          let sv = Number(source_city.population[yk] || 0);
          if (!(sv > 0)) continue;
          if (Number.isFinite(yn) && yn >= 1900) {
            target_city.metro_population[yk] = sv;
            if (!(Number(target_city.population[yk]) > 0)) {
              target_city.population[yk] = sv;
              if (!target_city._metro_only_years.includes(yk)) target_city._metro_only_years.push(yk);
            }
          } else {
            let cur = target_city.population[yk];
            if (Array.isArray(cur)) cur.push(sv);
            else if (cur !== undefined) target_city.population[yk] = [cur, sv];
            else target_city.population[yk] = sv;
          }
        }
      } else {
        if (Array.isArray(target_city._metro_only_years) && target_city._metro_only_years.length > 0 && target_city.population) {
          let s_yrs = Object.keys(source_city.population);
          for (let i = 0; i < s_yrs.length; i++) {
            let yk = s_yrs[i];
            if (Number(source_city.population[yk]) > 0 && target_city._metro_only_years.includes(yk))
              delete target_city.population[yk];
          }
        }
        target_city.population = population_Stadester_uud.mergeCityPopulations(target_city.population, source_city.population);
      }
    }
    if (Number.isFinite(target_city._annexation_year) && target_city.population) {
      let t_annex = Number(target_city._annexation_year);
      let t_yrs = Object.keys(target_city.population);
      for (let i = 0; i < t_yrs.length; i++) {
        let yn = parseInt(t_yrs[i], 10);
        if (Number.isFinite(yn) && yn >= t_annex)
          delete target_city.population[t_yrs[i]];
      }
    }
    
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
    let cfg = global.population_Stadester_config;
    let cfg_buringh = (cfg && cfg.coord_overrides && cfg.coord_overrides.buringh) ? cfg.coord_overrides.buringh : {};
    let coord_overrides = (cfg && cfg.buringh_coord_overrides) ? cfg.buringh_coord_overrides : {};
    let header = (buringh_array.length > 0 && Array.isArray(buringh_array[0])) ? buringh_array[0] : null;
    let return_obj = {};
    let start_index = (header) ? 1 : 0;
    
    for (let i = start_index; i < buringh_array.length; i++) {
      let local_city = buringh_array[i];
      let local_obj = {};
      
      if (Array.isArray(local_city)) {
        for (let x = 0; x < local_city.length; x++)
          local_obj[header[x]] = local_city[x];
      } else if (local_city && typeof local_city === "object") {
        local_obj = local_city;
      }
      
      if (!local_obj.city) continue;
      let local_country = local_obj.country;
      let local_key = `${local_obj.city}-${local_obj.country}`;
      let ov = cfg_buringh[local_key];
      if (ov && ov.resolution === "non_settlement") continue;
      if (ov && ov.country_override) local_country = ov.country_override;
      
      if (!return_obj[local_key]) {
        let ov_coords = (ov && Array.isArray(ov.coords) && ov.coords.length >= 2) ? ov.coords : coord_overrides[local_key];
        let parsed_coords = ov_coords ? ov_coords.slice() : [
          parseFloat(String(local_obj["latitude in degrees"]).replace(",", ".")),
          parseFloat(String(local_obj["longitude in degrees"]).replace(",", "."))
        ];
        return_obj[local_key] = {
          name: local_obj.city,
          coords: parsed_coords,
          country: local_country,
          other_names: local_obj["synonyms and historical names"] ?
            local_obj["synonyms and historical names"].split(",").map(item => item.trim()) : [],
          key: local_key,
          population: {}
        };
      }
      
      let actual_city = return_obj[local_key];
      let local_population = parseFloat(String(local_obj["inhabitants in 000-s"]).replace(",", "."));
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
    let all_cities_keys;
    let all_return_keys;
    let cfg = global.population_Stadester_config;
    let cfg_devries = (cfg && cfg.coord_overrides && cfg.coord_overrides.devries) ? cfg.coord_overrides.devries : {};
    let coord_overrides = (cfg && cfg.devries_coord_overrides) ? cfg.devries_coord_overrides : {};
    let devries_cities_file = path.join(raw_folder, "devries", "europop.csv");
    let devries_cities = File.loadCSVAsJSON(devries_cities_file, { mode: "vertical" });
    let devries_coords_file = path.join(raw_folder, "devries", "city_coords.csv");
    let devries_coords = File.loadCSVAsArray(devries_coords_file);
    let return_obj = {};
    
    all_cities_keys = Object.keys(devries_cities);
    for (let i = 0; i < all_cities_keys.length; i++) {
      let local_city = devries_cities[all_cities_keys[i]];
      return_obj[all_cities_keys[i]] = { key: all_cities_keys[i], population: {} };
      let actual_city = return_obj[all_cities_keys[i]];
      
      if (local_city.year) {
        for (let x = 0; x < local_city.year.length; x++) {
          if (local_city.population && local_city.population[x] && local_city.population[x] !== "NA") {
            let local_population = parseInt(parseFloat(local_city.population[x])*1000);
            if (local_population > 0)
              actual_city.population[local_city.year[x]] = local_population;
          }
        }
      }
      if (local_city.region) actual_city.country = local_city.region[0];
    }
    
    for (let i = 0; i < devries_coords.length; i++) {
      let local_value = devries_coords[i];
      if (!local_value) continue;
      
      let local_key = Array.isArray(local_value) ? local_value[2] : local_value.city;
      let local_lat = parseFloat(Array.isArray(local_value) ? local_value[1] : local_value.lat);
      let local_lng = parseFloat(Array.isArray(local_value) ? local_value[0] : local_value.lon);
      
      if (local_key && return_obj[local_key] && !isNaN(local_lat) && !isNaN(local_lng)) {
        let override_key = `${local_key}-${return_obj[local_key].country}`;
        let ov = cfg_devries[local_key] || cfg_devries[override_key] || cfg_devries[`${return_obj[local_key].country}.${local_key}`];
        if (ov && ov.resolution === "non_settlement") {
          return_obj[local_key]._skip_non_settlement = true;
          continue;
        }
        if (ov && ov.country_override) return_obj[local_key].country = ov.country_override;
        if (ov && Array.isArray(ov.coords) && ov.coords.length >= 2) {
          return_obj[local_key].coords = ov.coords.slice();
        } else if (coord_overrides[override_key]) {
          return_obj[local_key].coords = coord_overrides[override_key].slice();
        } else {
          return_obj[local_key].coords = [local_lat, local_lng];
        }
      }
    }
    
    all_return_keys = Object.keys(return_obj);
    for (let i = 0; i < all_return_keys.length; i++) {
      let local_city = return_obj[all_return_keys[i]];
      if (local_city._skip_non_settlement) continue;
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
    let cfg = global.population_Stadester_config;
    let country_mappings = (cfg && cfg.populstat_countries) ? cfg.populstat_countries : {};
    let pop_overrides = (cfg && cfg.coord_overrides && cfg.coord_overrides.populstat) ? cfg.coord_overrides.populstat : {};
    let populstat_file = path.join(raw_folder, "populstat_cities", "populstat_cities.json");
    let populstat_obj = JSON.parse(fs.readFileSync(populstat_file, "utf8"));
    let return_obj = {};
    let sub_fields = ["prov.", "province", "prefecture", "state", "région", "subdivision"];
    
    let all_countries = Object.keys(populstat_obj);
    for (let i = 0; i < all_countries.length; i++) {
      let raw_country_key = all_countries[i];
      let local_country = populstat_obj[raw_country_key];
      let all_local_cities = Object.keys(local_country);
      let local_country_name = country_mappings[raw_country_key] || raw_country_key;
      
      for (let x = 0; x < all_local_cities.length; x++) {
        let raw_city_key = all_local_cities[x];
        let ov = pop_overrides[`${raw_country_key}.${raw_city_key}`];
        if (ov && ov.resolution === "non_settlement") continue;
        
        let local_city = local_country[raw_city_key];
        let eff_country = (ov && ov.country_override) ? ov.country_override : local_country_name;
        let local_key = `${raw_city_key}-${eff_country}`;
        
        if (ov && Array.isArray(ov.coords) && ov.coords.length >= 2)
          local_city.coords = ov.coords.slice();
        if (ov && ov.subdivision_override !== undefined) {
          let sub_field = sub_fields.find(sf => local_city[sf] !== undefined) || "subdivision";
          local_city[sub_field] = ov.subdivision_override;
        }
        
        if (local_city.population) {
          let normalised_pop = {};
          let pop_keys = Object.keys(local_city.population);
          for (let y = 0; y < pop_keys.length; y++) {
            let raw_key = String(pop_keys[y]).trim();
            let norm_key = (raw_key.length >= 8 && Number(raw_key) > 10000) ? raw_key.slice(0, 4) : raw_key;
            normalised_pop[norm_key] = local_city.population[pop_keys[y]]*1000;
          }
          local_city.population = normalised_pop;
        }
        if (local_city.type !== undefined) delete local_city.type;
        local_city.country = eff_country;
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
    let all_wcp_keys;
    let cfg = global.population_Stadester_config;
    let wcp_file = path.join(raw_folder, "worldcitypop", "chandler_modelski_cities.json");
    let wcp_obj = JSON.parse(fs.readFileSync(wcp_file, "utf8"));
    let wcp_overrides = (cfg && cfg.coord_overrides && cfg.coord_overrides.worldcitypop) ? cfg.coord_overrides.worldcitypop : {};
    
    //Function body
    all_wcp_keys = Object.keys(wcp_obj);
    for (let i = 0; i < all_wcp_keys.length; i++) {
      let k = all_wcp_keys[i];
      let entry = wcp_obj[k];
      if (!entry) continue;
      if (/^(?:gelibolu|gallipoli)$/i.test(String(entry.name || "").trim()) && entry.population) {
        let g_yrs = Object.keys(entry.population);
        for (let y = 0; y < g_yrs.length; y++) {
          let yn = parseInt(g_yrs[y], 10);
          if (Number.isFinite(yn) && yn < 1400) delete entry.population[g_yrs[y]];
        }
      }
      if (/^(?:gliwice|gleiwitz)$/i.test(String(entry.name || "").trim()) && entry.population) {
        let gl_yrs = Object.keys(entry.population);
        for (let y = 0; y < gl_yrs.length; y++) {
          let yn = parseInt(gl_yrs[y], 10);
          if (Number.isFinite(yn) && yn <= 1900 && Number(entry.population[gl_yrs[y]]) > 100000)
            delete entry.population[gl_yrs[y]];
        }
      }
      if (/^weisbaden$/i.test(String(entry.name || "").trim())) {
        entry.name = "Wiesbaden";
        if (entry.population) {
          let w_yrs = Object.keys(entry.population);
          for (let y = 0; y < w_yrs.length; y++) {
            let yn = parseInt(w_yrs[y], 10);
            if (Number.isFinite(yn) && yn <= 1850 && Number(entry.population[w_yrs[y]]) > 25000)
              delete entry.population[w_yrs[y]];
          }
        }
      }
      if (/^(?:katowice|kattowitz)$/i.test(String(entry.name || "").trim()) && entry.population) {
        let kt_yrs = Object.keys(entry.population);
        for (let y = 0; y < kt_yrs.length; y++) {
          let yn = parseInt(kt_yrs[y], 10);
          if (Number.isFinite(yn) && yn < 1865 && Number(entry.population[kt_yrs[y]]) > 1500)
            delete entry.population[kt_yrs[y]];
        }
      }
      if (/^chemnitz$/i.test(String(entry.name || "").trim()) && entry.population) {
        let ch_yrs = Object.keys(entry.population);
        for (let y = 0; y < ch_yrs.length; y++) {
          let yn = parseInt(ch_yrs[y], 10);
          if (Number.isFinite(yn) && yn < 1830 && Number(entry.population[ch_yrs[y]]) > 20000)
            delete entry.population[ch_yrs[y]];
        }
      }
      if (/^frankenthal$/i.test(String(entry.name || "").trim()) && entry.population) {
        let fr_yrs = Object.keys(entry.population);
        for (let y = 0; y < fr_yrs.length; y++) {
          let yn = parseInt(fr_yrs[y], 10);
          if (Number.isFinite(yn) && yn < 1850 && Number(entry.population[fr_yrs[y]]) > 15000)
            delete entry.population[fr_yrs[y]];
        }
      }
      let ov = wcp_overrides[k] || (entry.country ? wcp_overrides[`${entry.country}.${k}`] : null);
      if (!ov) continue;
      if (ov.resolution === "non_settlement") { delete wcp_obj[k]; continue; }
      if (Array.isArray(ov.coords) && ov.coords.length >= 2) {
        entry.coords = [Number(ov.coords[0]), Number(ov.coords[1])];
        entry.latitude = entry.coords[0];
        entry.longitude = entry.coords[1];
      }
      if (ov.country_override) entry.country = ov.country_override;
    }
    
    //Return statement
    return wcp_obj;
  };
  
  if (typeof require !== "undefined")
    try { require(path.join(__dirname, "stadester_uud_ghsl_names.js")); } catch (e) {}
  
  /**
   * Re-keys Moscow Oblast Korolev away from Kaliningrad-Russia and absorbs duplicate non-POLARIS twins within 5 km.
   * @alias population_Stadester_uud.absorbSecondaryNonPolarisTwins
   *
   * @param {Object} arg0_return_obj
   * @param {Map} arg1_city_grid
   * @param {Object} arg2_actual_city
   * @param {Object} arg3_local_city
   * @param {number} arg4_min_pol_yr
   * @param {Function} arg5_get_grid_cells
   * @param {Function} arg6_add_to_grid
   * @param {Function} arg7_is_agglomeration
   *
   * @returns {Object}
   */
  population_Stadester_uud.absorbSecondaryNonPolarisTwins = function (
    arg0_return_obj,
    arg1_city_grid,
    arg2_actual_city,
    arg3_local_city,
    arg4_min_pol_yr,
    arg5_get_grid_cells,
    arg6_add_to_grid,
    arg7_is_agglomeration
  ) {
    //Convert from parameters
    let return_obj = arg0_return_obj;
    let city_grid = arg1_city_grid;
    let actual_city = arg2_actual_city;
    let local_city = arg3_local_city;
    let min_pol_yr_for_cut = arg4_min_pol_yr;
    let getGridCells = arg5_get_grid_cells;
    let addToGrid = arg6_add_to_grid;
    let isAgglomeration = arg7_is_agglomeration;

    //Declare local instance variables
    let peer_cells;

    //Guard clauses
    if (!return_obj || !actual_city || !local_city || !Array.isArray(actual_city.coords)) return actual_city;

    //Function body: 1. Re-key Moscow Oblast Korolev away from Kaliningrad-Russia so Kaliningrad RU.23 keeps its key
    if (actual_city.key === "Kaliningrad-Russia" && local_city.key === "Korolev-Russia") {
      let old_cell = `${Math.floor(Number(actual_city.coords[0]))},${Math.floor(Number(actual_city.coords[1]))}`;
      if (city_grid && city_grid.has(old_cell)) city_grid.get(old_cell).delete("Kaliningrad-Russia");
      delete return_obj["Kaliningrad-Russia"];
      if (return_obj["Korolev-Russia"] && return_obj["Korolev-Russia"] !== actual_city) {
        let kpeer = return_obj["Korolev-Russia"];
        if (Array.isArray(kpeer.other_names)) {
          if (!actual_city.other_names) actual_city.other_names = [];
          for (let kn = 0; kn < kpeer.other_names.length; kn++)
            if (kpeer.other_names[kn] && !actual_city.other_names.includes(kpeer.other_names[kn]))
              actual_city.other_names.push(kpeer.other_names[kn]);
        }
        population_Stadester_uud.appendCitySources(actual_city, kpeer.sources);
        if (city_grid && city_grid.has(old_cell)) city_grid.get(old_cell).delete("Korolev-Russia");
        delete return_obj["Korolev-Russia"];
      }
      actual_city.key = "Korolev-Russia";
      if (typeof addToGrid === "function") addToGrid(actual_city);
    }

    //2. Absorb duplicate non-POLARIS non-agglomeration same-country twin within 5 km (25 km for US entities)
    if (typeof getGridCells === "function" && city_grid) {
      peer_cells = getGridCells(actual_city.coords, 0.28);
      for (let pc = 0; pc < peer_cells.length; pc++) {
        let pset = city_grid.get(peer_cells[pc]);
        if (!pset) continue;
        let pkeys = Array.from(pset);
        for (let pk_i = 0; pk_i < pkeys.length; pk_i++) {
          let pk = pkeys[pk_i];
          let peer = return_obj[pk];
          if (!peer || peer === actual_city || (typeof isAgglomeration === "function" && isAgglomeration(peer))) continue;
          if (typeof population_Stadester_uud.hasViscountSource === "function" && population_Stadester_uud.hasViscountSource(peer)) continue;
          let is_us_pair = Boolean(
            (typeof population_Stadester_uud.areCompatibleUSCountries === "function" &&
              population_Stadester_uud.areCompatibleUSCountries(peer.country, actual_city.country)) ||
            (
              (peer.country === "United States" || peer.country === "United States of America") &&
              typeof population_Stadester_uud.isUSCountryOrState === "function" &&
              population_Stadester_uud.isUSCountryOrState(actual_city.country)
            )
          );
          let same_or_compat_country = (peer.country === actual_city.country) ||
            is_us_pair ||
            (
              peer.country === "United States" &&
              typeof population_Stadester_uud.isCompleteViscountCountry === "function" &&
              population_Stadester_uud.isCompleteViscountCountry(actual_city.country, actual_city)
            ) ||
            (
              typeof population_Stadester_ghsl !== "undefined" &&
              typeof population_Stadester_ghsl.areCompatibleTwinCountries === "function" &&
              population_Stadester_ghsl.areCompatibleTwinCountries(peer.country, actual_city.country)
            );
          if (!same_or_compat_country) continue;
          let max_twin_dist = is_us_pair ? 25 : 5;
          if (!Array.isArray(peer.coords) || population_Stadester_uud.haversineDistance(actual_city.coords, peer.coords) > max_twin_dist) continue;
          let name_act_prim = (typeof population_Stadester_uud.processCityName === "function") ?
            population_Stadester_uud.processCityName(actual_city.name || "") : String(actual_city.name || "").toLowerCase();
          let name_peer_prim = (typeof population_Stadester_uud.processCityName === "function") ?
            population_Stadester_uud.processCityName(peer.name || "") : String(peer.name || "").toLowerCase();
          if (
            (name_act_prim === "brooklyn" && (name_peer_prim === "new york" || name_peer_prim === "new york city")) ||
            (name_peer_prim === "brooklyn" && (name_act_prim === "new york" || name_act_prim === "new york city"))
          ) {
            continue;
          }
          if (!population_Stadester_uud.checkExactNameMatch(actual_city, peer)) continue;
          if (typeof population_Stadester_uud.canMergeMunicipalities === "function") {
            let twin_gate = population_Stadester_uud.canMergeMunicipalities(actual_city, peer, { max_semantic_km: max_twin_dist });
            if (!twin_gate.allow) continue;
          }
          if (!actual_city.other_names) actual_city.other_names = [];
          if (peer.name && peer.name !== actual_city.name && !actual_city.other_names.includes(peer.name))
            actual_city.other_names.push(peer.name);
          if (Array.isArray(peer.other_names)) {
            for (let pn = 0; pn < peer.other_names.length; pn++)
              if (peer.other_names[pn] && peer.other_names[pn] !== actual_city.name && !actual_city.other_names.includes(peer.other_names[pn]))
                actual_city.other_names.push(peer.other_names[pn]);
          }
          let act_found_yr = Number(actual_city["found.yr"] !== undefined ? actual_city["found.yr"] : actual_city.foundation_year);
          if (!Number.isFinite(act_found_yr)) act_found_yr = -Infinity;
          if (peer.population && Number.isFinite(min_pol_yr_for_cut)) {
            let cut_p = Math.min(1897, min_pol_yr_for_cut);
            let pyrs = Object.keys(peer.population);
            for (let pi = 0; pi < pyrs.length; pi++) {
              let pyr_n = parseInt(pyrs[pi], 10);
              if (Number.isFinite(pyr_n) && pyr_n >= act_found_yr && pyr_n < cut_p && actual_city.population[pyrs[pi]] === undefined)
                actual_city.population[pyrs[pi]] = peer.population[pyrs[pi]];
            }
          }
          population_Stadester_uud.appendCitySources(actual_city, peer.sources);
          if (actual_city.name === "New York" && (actual_city.country === "New York" || actual_city.country === "United States")) {
            actual_city.coords = [40.7128, -74.0060];
            if (Array.isArray(actual_city.other_names))
              actual_city.other_names = actual_city.other_names.filter(function (arg0_n) { return arg0_n !== "Brooklyn"; });
          }
          pset.delete(pk);
          delete return_obj[pk];
        }
      }
    }

    //Return statement
    return actual_city;
  };

  /**
   * Cleans post-merge UUD anomalies: terminates RU/UA/BY agglomerations pre-1975 and scrubs 1-to-2-year post-1975 U/V-spikes.
   * @alias population_Stadester_uud.cleanPostMergeUUD
   *
   * @param {Object} arg0_uud_obj
   *
   * @returns {Object}
   */
  population_Stadester_uud.cleanPostMergeUUD = function (arg0_uud_obj) {
    //Convert from parameters
    let uud_obj = arg0_uud_obj;

    //Declare local instance variables
    let all_keys;
    let non_agglom_grid = new Map();
    let polaris_countries = ["Belarus", "Estonia", "Finland", "Latvia", "Lithuania", "Moldova", "Poland", "Russia", "Ukraine"];

    //Guard clauses
    if (!uud_obj || typeof uud_obj !== "object") return uud_obj;

    //Function body
    all_keys = Object.keys(uud_obj);
    for (let i = 0; i < all_keys.length; i++) {
      let c_obj = uud_obj[all_keys[i]];
      if (!c_obj || !Array.isArray(c_obj.coords) || c_obj.coords.length < 2) continue;
      let k_l = String(all_keys[i] || "").toLowerCase();
      let n_l = String(c_obj.name || "").toLowerCase();
      if (Boolean(c_obj.is_agglomeration) || k_l.includes("agglomeration") || n_l.includes("agglomeration")) continue;
      let in_complete_viscount_c = polaris_countries.includes(c_obj.country) ||
        (typeof population_Stadester_uud.isCompleteViscountCountry === "function" && population_Stadester_uud.isCompleteViscountCountry(c_obj.country, c_obj));
      if (!in_complete_viscount_c) continue;
      let gk = `${Math.floor(Number(c_obj.coords[0]))}_${Math.floor(Number(c_obj.coords[1]))}`;
      if (!non_agglom_grid.has(gk)) non_agglom_grid.set(gk, []);
      non_agglom_grid.get(gk).push(c_obj);
    }

    for (let i = 0; i < all_keys.length; i++) {
      let city = uud_obj[all_keys[i]];
      if (!city || !city.population) continue;

      let key_lower = String(all_keys[i] || "").toLowerCase();
      let name_lower = String(city.name || "").toLowerCase();
      let is_agglom = Boolean(city.is_agglomeration) || key_lower.includes("agglomeration") || name_lower.includes("agglomeration");
      let is_viscount_city = Boolean(typeof population_Stadester_uud.hasViscountSource === "function" && population_Stadester_uud.hasViscountSource(city));
      let in_complete_viscount_city = polaris_countries.includes(city.country) ||
        (typeof population_Stadester_uud.isCompleteViscountCountry === "function" && population_Stadester_uud.isCompleteViscountCountry(city.country, city));
      if (is_agglom && in_complete_viscount_city && !is_viscount_city) {
        let has_core_city = false;
        if (Array.isArray(city.coords) && city.coords.length >= 2) {
          let lat0 = Number(city.coords[0]);
          let lng0 = Number(city.coords[1]);
          for (let dx = -1; dx <= 1 && !has_core_city; dx++) {
            for (let dy = -1; dy <= 1 && !has_core_city; dy++) {
              let bucket = non_agglom_grid.get(`${Math.floor(lat0) + dx}_${Math.floor(lng0) + dy}`);
              if (!bucket) continue;
              for (let z = 0; z < bucket.length; z++) {
                let peer = bucket[z];
                let peer_compat = (peer.country === city.country) ||
                  (
                    typeof population_Stadester_ghsl !== "undefined" &&
                    typeof population_Stadester_ghsl.areCompatibleTwinCountries === "function" &&
                    population_Stadester_ghsl.areCompatibleTwinCountries(peer.country, city.country)
                  );
                if (peer_compat && population_Stadester_uud.haversineDistance(city.coords, peer.coords) <= 15.0) {
                  has_core_city = true;
                  break;
                }
              }
            }
          }
        }
        if (has_core_city) {
          delete uud_obj[all_keys[i]];
          continue;
        }
        let p_keys = Object.keys(city.population);
        for (let x = 0; x < p_keys.length; x++) {
          let yr_num = parseInt(p_keys[x], 10);
          if (Number.isFinite(yr_num) && yr_num >= 1975)
            delete city.population[p_keys[x]];
        }
        continue;
      }

      let has_war = Array.isArray(city._war_displacement_years) && city._war_displacement_years.length > 0;
      for (let pass = 0; pass < 2; pass++) {
        let yrs = Object.keys(city.population).map(Number).filter(function (arg0_n) {
          return Number.isFinite(arg0_n) && arg0_n >= 1975 && Number(city.population[arg0_n]) > 0;
        }).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
        let removed = false;

        for (let idx = 1; idx < yrs.length - 1; idx++) {
          let y_prev = yrs[idx - 1];
          let y_cur = yrs[idx];
          let y_next = yrs[idx + 1];
          if (has_war && y_cur >= 2022) continue;
          if ((y_next - y_prev) > 6) continue;
          let v_prev = Number(city.population[y_prev]);
          let v_cur = Number(city.population[y_cur]);
          let v_next = Number(city.population[y_next]);
          if (Math.max(v_prev, v_cur, v_next) < 250) continue;
          if ((v_prev >= v_cur*2.4 && v_next >= v_cur*2.4) || (v_cur >= v_prev*2.4 && v_cur >= v_next*2.4)) {
            delete city.population[y_cur];
            removed = true;
          }
        }
        if (removed) continue;

        for (let idx = 1; idx < yrs.length - 2; idx++) {
          let y_prev = yrs[idx - 1];
          let y_a = yrs[idx];
          let y_b = yrs[idx + 1];
          let y_next = yrs[idx + 2];
          if (has_war && y_b >= 2022) continue;
          if ((y_b - y_a) > 2 || (y_next - y_prev) > 8) continue;
          let v_prev = Number(city.population[y_prev]);
          let v_a = Number(city.population[y_a]);
          let v_b = Number(city.population[y_b]);
          let v_next = Number(city.population[y_next]);
          if (Math.max(v_prev, v_next) < 250) continue;
          if (
            (v_prev >= v_a*2.4 && v_prev >= v_b*2.4 && v_next >= v_a*2.4 && v_next >= v_b*2.4) ||
            (v_a >= v_prev*2.4 && v_b >= v_prev*2.4 && v_a >= v_next*2.4 && v_b >= v_next*2.4)
          ) {
            delete city.population[y_a];
            delete city.population[y_b];
            removed = true;
          }
        }
        if (!removed) break;
      }
    }

    //Return statement
    return uud_obj;
  };

  /**
   * Loads `stadester_name_normaliser` lazily and returns it.
   * @alias population_Stadester_uud.getNameNormaliser
   *
   * @returns {Object|null}
   */
  population_Stadester_uud.getNameNormaliser = function () {
    //Function body
    if (!global.stadester_name_normaliser && typeof require !== "undefined") {
      try {
        require(path.join(__dirname, "stadester_name_normaliser.js"));
      } catch (e) {}
    }

    //Return statement
    return global.stadester_name_normaliser || null;
  };

  /**
   * Assigns official `urban_city_proper` municipal boundary metadata (`_mun_id`, `_mun_scope`, `_mun_is_capital`),
   * Class 2 intra-municipal parent metadata, and Class 3 historical annexation metadata onto a settlement record.
   * @alias population_Stadester_uud.assignMunicipalMetadata
   *
   * @param {Object} arg0_city
   *
   * @returns {Object}
   */
  population_Stadester_uud.assignMunicipalMetadata = function (arg0_city) {
    //Convert from parameters
    let city = arg0_city;

    //Guard clauses
    if (!city || typeof city !== "object") return city;
    if (city._mun_checked === true) return city;

    //Declare local instance variables
    let is_metro = Boolean(
      city.population_scope === "metro" ||
      city.extent_type === "metro" ||
      city.is_agglomeration === true ||
      /\(metro\)|agglomeration|metropolitan/i.test(String(city.name || city.key || ""))
    );
    let norm = population_Stadester_uud.getNameNormaliser();

    //Function body
    city._mun_checked = true;
    if (is_metro || !norm) {
      city._mun_id = "";
      city._mun_scope = "";
      return city;
    }

    let lat = Array.isArray(city.coords) ? Number(city.coords[0]) : NaN;
    let lng = Array.isArray(city.coords) ? Number(city.coords[1]) : NaN;
    let p_meta = norm.resolveParentMunicipality(city.name, city.country, city.coords);
    let h_meta = norm.resolveHistoricalAmalgamation(city.name, city.country, city.coords);
    let poly_hit = (Number.isFinite(lat) && Number.isFinite(lng)) ?
      norm.resolveMunicipalBoundary(lat, lng, city.country) : null;

    if (poly_hit && poly_hit.id) {
      city._mun_scope = poly_hit.boundary_scope || "urban_city_proper";
      if (city._mun_scope === "urban_city_proper") {
        city._mun_id = poly_hit.id;
        city._mun_name = poly_hit.name;
        city._mun_is_capital = Boolean(poly_hit.is_capital);
      } else {
        city._mun_id = "";
      }
    } else {
      city._mun_id = "";
      city._mun_scope = "";
    }

    if (p_meta && p_meta.parent_name) {
      let c_norm = norm.normaliseCountryName(city.country);
      city._parent_mun_meta = p_meta;
      city._subdiv_id = `subdiv:${c_norm}:${norm.foldAscii(p_meta.parent_name)}`;
      let cur_fold = norm.foldAscii(city.name);
      let par_fold = norm.foldAscii(p_meta.parent_name);
      if (cur_fold && par_fold && cur_fold !== par_fold)
        city._is_intra_district = true;
      if (!city._mun_id) {
        city._mun_name = p_meta.parent_name;
        city._mun_is_capital = Boolean(p_meta.is_capital_override);
      }
    } else {
      let c_norm = norm.normaliseCountryName(city.country);
      let cur_fold = norm.foldAscii(city.name);
      let cfg = norm.loadMetroSubdivisions();
      let c_parents = (cfg && cfg.intra_municipal_parents) ? cfg.intra_municipal_parents[c_norm] : null;
      let p_obj = (c_parents && cur_fold) ? c_parents[cur_fold] : null;
      if (!p_obj && c_parents && cur_fold) {
        let p_keys = Object.keys(c_parents);
        for (let i = 0; i < p_keys.length; i++) {
          if (norm.foldAscii(c_parents[p_keys[i]].canonical_name) === cur_fold) {
            p_obj = c_parents[p_keys[i]];
            break;
          }
        }
      }
      if (p_obj) {
        let within_r = (!Number.isFinite(lat) || !Number.isFinite(lng) || !Array.isArray(p_obj.coords) || !Number.isFinite(p_obj.max_radius_km)) ?
          true : (norm.haversineKm([lat, lng], p_obj.coords) <= p_obj.max_radius_km);
        if (within_r) {
          city._subdiv_id = `subdiv:${c_norm}:${norm.foldAscii(p_obj.canonical_name)}`;
          if (!city._mun_name) city._mun_name = p_obj.canonical_name;
        }
      }
    }
    if (h_meta && h_meta.parent_name)
      city._hist_amalg_meta = h_meta;

    //Return statement
    return city;
  };

  /**
   * Enforces the Global 4-Class Epoch-Aware Same-Municipality Merge Gate across UUD, GazetteerLoader, and GHSL.
   * Cross-municipality proximity merges and blind polygon-containment collapses are strictly forbidden.
   * @alias population_Stadester_uud.canMergeMunicipalities
   *
   * @param {Object} arg0_city_a
   * @param {Object} arg1_city_b
   * @param {Object} [arg2_options]
   *
   * @returns {{ allow: boolean, dist_km: number, reason: string }}
   */
  population_Stadester_uud.canMergeMunicipalities = function (arg0_city_a, arg1_city_b, arg2_options) {
    //Convert from parameters
    let city_a = arg0_city_a;
    let city_b = arg1_city_b;
    let options = (arg2_options) ? arg2_options : {};

    //Guard clauses
    if (!city_a || !city_b) return { allow: false, dist_km: Infinity, reason: "invalid_city" };

    //Declare local instance variables
    let dist_km = (Array.isArray(city_a.coords) && Array.isArray(city_b.coords) && typeof population_Stadester_uud.haversineDistance === "function") ?
      population_Stadester_uud.haversineDistance(city_a.coords, city_b.coords) : Infinity;
    let norm = population_Stadester_uud.getNameNormaliser();

    //Function body
    if (norm && norm.isProtectedDistinctPair(city_a.name, city_b.name))
      return { allow: false, dist_km: dist_km, reason: "protected_distinct_neighbours" };

    let is_agg_a = Boolean(city_a.population_scope === "metro" || city_a.extent_type === "metro" || city_a.is_agglomeration);
    let is_agg_b = Boolean(city_b.population_scope === "metro" || city_b.extent_type === "metro" || city_b.is_agglomeration);
    if (is_agg_a !== is_agg_b)
      return { allow: false, dist_km: dist_km, reason: "metro_vs_city_proper_mismatch" };

    //Class 3 Temporal Anti-Anachronism Guard: pre-annexation historical municipalities NEVER merge into parent
    let has_pre_annex_a = Number.isFinite(city_a._annexation_year);
    let has_pre_annex_b = Number.isFinite(city_b._annexation_year);
    if (has_pre_annex_a || has_pre_annex_b) {
      let fold_a = norm ? norm.foldAscii(city_a.name) : String(city_a.name || "").toLowerCase();
      let fold_b = norm ? norm.foldAscii(city_b.name) : String(city_b.name || "").toLowerCase();
      if (fold_a !== fold_b)
        return { allow: false, dist_km: dist_km, reason: "blocked_pre_annexation_historic_municipality" };
    }

    population_Stadester_uud.assignMunicipalMetadata(city_a);
    population_Stadester_uud.assignMunicipalMetadata(city_b);

    //Class 2 Intra-Municipal Subdivision check
    if (norm && city_a._subdiv_id && city_b._subdiv_id && city_a._subdiv_id === city_b._subdiv_id)
      return { allow: true, dist_km: dist_km, reason: "intra_municipal_subdivision" };
    if (norm) {
      let fa = norm.foldAscii(city_a.name);
      let fb = norm.foldAscii(city_b.name);
      let c_norm_a = norm.normaliseCountryName(city_a.country);
      let c_norm_b = norm.normaliseCountryName(city_b.country);
      if (c_norm_a && c_norm_a === c_norm_b) {
        if (city_a._parent_mun_meta && norm.foldAscii(city_a._parent_mun_meta.parent_name) === fb && (!city_a._parent_mun_meta.effective_from_year || city_a._is_intra_district === true))
          return { allow: true, dist_km: dist_km, reason: "intra_municipal_subdivision" };
        if (city_b._parent_mun_meta && norm.foldAscii(city_b._parent_mun_meta.parent_name) === fa && (!city_b._parent_mun_meta.effective_from_year || city_b._is_intra_district === true))
          return { allow: true, dist_km: dist_km, reason: "intra_municipal_subdivision" };
      }
    }

    let mun_a = (city_a._mun_scope === "urban_city_proper") ? (city_a._mun_id || "") : "";
    let mun_b = (city_b._mun_scope === "urban_city_proper") ? (city_b._mun_id || "") : "";
    let is_exact_name = (typeof population_Stadester_uud.checkExactNameMatch === "function") ?
      population_Stadester_uud.checkExactNameMatch(city_a, city_b) : false;

    //Different urban_city_proper polygons -> HARD BLOCK unless exact same folded name <= 20 km OR coarse legacy pin snap
    if (mun_a && mun_b && mun_a !== mun_b) {
      let same_folded_name = Boolean(norm && norm.foldAscii(city_a.name) && norm.foldAscii(city_a.name) === norm.foldAscii(city_b.name));
      if (same_folded_name && dist_km <= 20.0)
        return { allow: true, dist_km: dist_km, reason: "same_settlement_semantic_match" };
      let one_legacy = (
        typeof population_Stadester_uud.hasViscountSource === "function" &&
        (!population_Stadester_uud.hasViscountSource(city_a) || !population_Stadester_uud.hasViscountSource(city_b))
      );
      if (is_exact_name && one_legacy && dist_km <= 10.0)
        return { allow: true, dist_km: dist_km, reason: "semantic_legacy_pin_snap" };
      return { allow: false, dist_km: dist_km, reason: "blocked_cross_municipality" };
    }

    //Same urban_city_proper polygon OR outside polygon coverage OR broad_rural_amalgamation:
    //ZERO blind polygon-containment or proximity-only merges — require semantic/exonym match!
    if (!is_exact_name)
      return { allow: false, dist_km: dist_km, reason: "blocked_no_semantic_or_subdivision_basis" };

    let max_sem_km = Number.isFinite(options.max_semantic_km) ? Number(options.max_semantic_km) : 15.0;
    if (norm && norm.foldAscii(city_a.name) && norm.foldAscii(city_a.name) === norm.foldAscii(city_b.name))
      max_sem_km = Math.max(max_sem_km, 30.0);
    if (dist_km <= max_sem_km)
      return { allow: true, dist_km: dist_km, reason: "same_settlement_semantic_match" };

    //Return statement
    return { allow: false, dist_km: dist_km, reason: "blocked_distance_exceeded" };
  };

  /**
   * Normalises names, drops non-habitation features/statistical shells, splits Class 3 historical annexations
   * at `annexation_year` (INV-13), and flattens Class 2 intra-municipal subdivisions BEFORE UUD merging.
   * @alias population_Stadester_uud.prepareAndFlattenSourceDB
   *
   * @param {Object} arg0_db_obj
   * @param {string} [arg1_db_key]
   *
   * @returns {Object}
   */
  population_Stadester_uud.prepareAndFlattenSourceDB = function (arg0_db_obj, arg1_db_key) {
    //Convert from parameters
    let db_key = String(arg1_db_key || "");
    let db_obj = arg0_db_obj;

    //Guard clauses
    if (!db_obj || typeof db_obj !== "object") return {};

    //Declare local instance variables
    let all_keys = Object.keys(db_obj);
    let collapsed = {};
    let is_viscount_db = (db_key === "viscount_regional");
    let norm = population_Stadester_uud.getNameNormaliser();
    let passthrough = {};

    let pushParentBucket = function (arg0_parent_name, arg1_parent_coords, arg2_parent_cap, arg3_city, arg4_key, arg5_is_district) {
      let c_norm = norm ? norm.normaliseCountryName(arg3_city.country) : String(arg3_city.country || "").toLowerCase();
      let p_fold = norm ? norm.foldAscii(arg0_parent_name) : String(arg0_parent_name || "").toLowerCase();
      let group_tag = `${c_norm}|${p_fold}`;
      if (!collapsed[group_tag]) collapsed[group_tag] = [];
      collapsed[group_tag].push({
        city: arg3_city,
        is_district: Boolean(arg5_is_district),
        key: arg4_key,
        parent_coords: arg1_parent_coords,
        parent_is_capital: Boolean(arg2_parent_cap),
        parent_name: arg0_parent_name
      });
    };

    //Function body
    for (let i = 0; i < all_keys.length; i++) {
      let k = all_keys[i];
      let city = db_obj[k];
      if (!city || typeof city !== "object") continue;

      let raw_name = String(city.name || k.split("-")[0] || "").trim();
      if (norm && norm.isNonHabitationFeature(raw_name)) continue;

      let parent_floor = norm ? norm.resolveAmalgamationParentFloor(raw_name, city.country) : null;
      if (Number.isFinite(parent_floor) && city.population && typeof city.population === "object") {
        let p_yrs = Object.keys(city.population);
        let kept_any = false;
        for (let py = 0; py < p_yrs.length; py++) {
          let yn = parseInt(p_yrs[py], 10);
          if (Number.isFinite(yn) && yn < parent_floor) {
            delete city.population[p_yrs[py]];
          } else if (Number.isFinite(yn) && Number(city.population[p_yrs[py]]) > 0) {
            kept_any = true;
          }
        }
        if (!kept_any) continue;
        if (Number.isFinite(Number(city.foundation_year)) && Number(city.foundation_year) < parent_floor)
          city.foundation_year = parent_floor;
        if (Number.isFinite(Number(city["found.yr"])) && Number(city["found.yr"]) < parent_floor)
          city["found.yr"] = parent_floor;
      }

      if (Array.isArray(city.coords) && city.coords.length >= 2) {
        let la = Number(city.coords[0]);
        let lo = Number(city.coords[1]);
        let ctry_l = String(city.country || "").toLowerCase();
        let fold_r = norm ? norm.foldAscii(raw_name) : raw_name.toLowerCase();
        if (ctry_l === "latvia" && /riga/i.test(raw_name) && lo < 22.0)
          city.coords = [56.946, 24.10589];
        if (ctry_l === "italy" && /^(?:napoli|naples)$/i.test(raw_name) && la > 40.89 && lo < 14.23)
          city.coords = [40.85177, 14.26812];
        if (ctry_l === "greece" && fold_r === "larisa" && la < 39.0 && lo >= 22.0 && lo <= 23.0)
          city.coords = [39.63902, 22.41913];
        if (ctry_l === "denmark" && fold_r === "altona" && la > 55.0) {
          city.country = "Germany";
          city.coords = [53.55, 9.93333];
        }
        if (ctry_l === "turkey" && fold_r === "bayrampasa" && lo > 35.0 && population_Stadester_uud.getPeakPopulation(city.population) >= 100000)
          city.coords = [41.045, 28.902];
      }

      if (norm) {
        let nr = norm.normaliseCityName(raw_name, city.country);
        if (nr.name && nr.name !== city.name) {
          if (!Array.isArray(city.other_names)) city.other_names = [];
          if (city.name && !city.other_names.includes(city.name) && !/`|^[A-Z\s]{4,}$|^[a-z\s]{4,}$/.test(city.name))
            city.other_names.push(city.name);
          for (let a = 0; a < nr.extra_aliases.length; a++)
            if (!city.other_names.includes(nr.extra_aliases[a])) city.other_names.push(nr.extra_aliases[a]);
          city.name = nr.name;
        }
      }

      population_Stadester_uud.assignMunicipalMetadata(city);

      let is_metro = Boolean(city.population_scope === "metro" || city.extent_type === "metro" || city.is_agglomeration);
      if (is_metro) {
        passthrough[k] = city;
        continue;
      }

      //Class 3: Historical Municipal Amalgamation (split pre-annexation vs post-annexation at annexation_year)
      let h_meta = city._hist_amalg_meta;
      if (h_meta && Number.isFinite(h_meta.annexation_year) && city.population) {
        let t_annex = Number(h_meta.annexation_year);
        let pre_pop = {};
        let post_pop = {};
        let pyrs = Object.keys(city.population);
        for (let y = 0; y < pyrs.length; y++) {
          let yk = pyrs[y];
          let yn = parseInt(yk, 10);
          let val = city.population[yk];
          if (Number.isFinite(yn) && yn < t_annex) pre_pop[yk] = val;
          else post_pop[yk] = val;
        }
        if (Object.keys(pre_pop).length > 0) {
          let pre_city = Object.assign({}, city, {
            _annexation_year: t_annex,
            _annexed_into: h_meta.parent_name,
            _raw_lapsed: true,
            population: pre_pop
          });
          passthrough[k] = pre_city;
        }
        if (Object.keys(post_pop).length > 0) {
          let post_city = Object.assign({}, city, {
            _is_intra_district: true,
            population: post_pop
          });
          pushParentBucket(h_meta.parent_name, h_meta.parent_coords, h_meta.parent_is_capital, post_city, `${k}__post${t_annex}`, true);
        }
        continue;
      }

      //Class 2: Pure Intra-Municipal Subdivision (respect optional effective_from_year)
      let p_meta = city._parent_mun_meta;
      if (p_meta && p_meta.parent_name) {
        if (Number.isFinite(p_meta.effective_from_year) && city.population) {
          let t_eff = Number(p_meta.effective_from_year);
          let pre_pop = {};
          let post_pop = {};
          let pyrs = Object.keys(city.population);
          for (let y = 0; y < pyrs.length; y++) {
            let yk = pyrs[y];
            let yn = parseInt(yk, 10);
            if (Number.isFinite(yn) && yn < t_eff) pre_pop[yk] = city.population[yk];
            else post_pop[yk] = city.population[yk];
          }
          if (Object.keys(pre_pop).length > 0) {
            passthrough[k] = Object.assign({}, city, { _annexation_year: t_eff, _raw_lapsed: true, population: pre_pop });
          }
          if (Object.keys(post_pop).length > 0) {
            let post_city = Object.assign({}, city, { _is_intra_district: true, population: post_pop });
            pushParentBucket(p_meta.parent_name, p_meta.parent_coords, p_meta.is_capital_override, post_city, k, true);
          }
        } else {
          let is_self_parent = norm ? (norm.foldAscii(city.name) === norm.foldAscii(p_meta.parent_name)) : false;
          pushParentBucket(p_meta.parent_name, p_meta.parent_coords, p_meta.is_capital_override, city, k, !is_self_parent);
        }
        continue;
      }

      //Check if this city itself is a parent target of Class 2/3 buckets in the same DB
      if (norm) {
        let c_norm = norm.normaliseCountryName(city.country);
        let c_fold = norm.foldAscii(city.name);
        let m_cfg = norm.loadMetroSubdivisions();
        let h_cfg = norm.loadHistoricalAmalgamations();
        let is_known_parent = Boolean(
          (m_cfg && m_cfg.intra_municipal_parents && m_cfg.intra_municipal_parents[c_norm] && m_cfg.intra_municipal_parents[c_norm][c_fold]) ||
          (h_cfg && Array.isArray(h_cfg.amalgamations) && h_cfg.amalgamations.some(function (arg0_a) {
            return norm.normaliseCountryName(arg0_a.country) === c_norm && norm.foldAscii(arg0_a.parent_name) === c_fold;
          }))
        );
        if (is_known_parent) {
          pushParentBucket(city.name, city.coords, Boolean(city.is_capital || city.capital || city._mun_is_capital), city, k, false);
          continue;
        }
      }

      passthrough[k] = city;
    }

    let g_keys = Object.keys(collapsed);
    for (let i = 0; i < g_keys.length; i++) {
      let grp = collapsed[g_keys[i]];
      if (grp.length === 1 && !grp[0].is_district) {
        passthrough[grp[0].key] = grp[0].city;
        continue;
      }

      grp.sort(function (arg0_a, arg1_b) {
        let ca = arg0_a.city;
        let cb = arg1_b.city;
        if (arg0_a.is_district !== arg1_b.is_district) return arg0_a.is_district ? 1 : -1;
        let cap_a = Boolean(ca.is_capital || ca.capital || ca._mun_is_capital || arg0_a.parent_is_capital);
        let cap_b = Boolean(cb.is_capital || cb.capital || cb._mun_is_capital || arg1_b.parent_is_capital);
        if (cap_a !== cap_b) return cap_a ? -1 : 1;
        return population_Stadester_uud.getPeakPopulation(cb.population) - population_Stadester_uud.getPeakPopulation(ca.population);
      });

      let lead_item = grp[0];
      let lead = lead_item.city;
      if (lead_item.parent_name && lead.name !== lead_item.parent_name) {
        if (!Array.isArray(lead.other_names)) lead.other_names = [];
        if (lead.name && !lead.other_names.includes(lead.name)) lead.other_names.push(lead.name);
        lead.name = lead_item.parent_name;
      }
      if (lead_item.parent_is_capital || lead._mun_is_capital) lead.is_capital = true;
      if (lead_item.is_district && Array.isArray(lead_item.parent_coords)) lead.coords = lead_item.parent_coords.slice();

      let has_unified_lead = !lead_item.is_district;
      if (!has_unified_lead) lead._from_districts_only = true;
      if (!lead.population) lead.population = {};
      let unified_years = new Set(has_unified_lead ? Object.keys(lead.population).filter(function (arg0_y) { return Number(lead.population[arg0_y]) > 0; }) : []);

      for (let x = 1; x < grp.length; x++) {
        let sub_item = grp[x];
        let sub = sub_item.city;
        if (!Array.isArray(lead.other_names)) lead.other_names = [];
        if (sub.name && sub.name !== lead.name && !lead.other_names.includes(sub.name))
          lead.other_names.push(sub.name);
        if (Array.isArray(sub.other_names)) {
          for (let on = 0; on < sub.other_names.length; on++)
            if (sub.other_names[on] && sub.other_names[on] !== lead.name && !lead.other_names.includes(sub.other_names[on]))
              lead.other_names.push(sub.other_names[on]);
        }
        if (sub.population) {
          let syrs = Object.keys(sub.population);
          for (let y = 0; y < syrs.length; y++) {
            let yk = syrs[y];
            let sv = Number(sub.population[yk] || 0);
            if (!(sv > 0)) continue;
            if (unified_years.has(yk)) continue;
            if (!sub_item.is_district) {
              if (!(Number(lead.population[yk]) > 0)) lead.population[yk] = sv;
            } else if (!has_unified_lead) {
              lead.population[yk] = Math.round(Number(lead.population[yk] || 0) + sv);
            }
          }
        }
        population_Stadester_uud.appendCitySources(lead, sub.sources || sub.type);
      }

      let lead_floor = norm ? norm.resolveAmalgamationParentFloor(lead.name, lead.country) : null;
      if (Number.isFinite(lead_floor) && lead.population && typeof lead.population === "object") {
        let lyrs = Object.keys(lead.population);
        for (let y = 0; y < lyrs.length; y++) {
          let yn = parseInt(lyrs[y], 10);
          if (Number.isFinite(yn) && yn < lead_floor)
            delete lead.population[lyrs[y]];
        }
        if (Number.isFinite(Number(lead.foundation_year)) && Number(lead.foundation_year) < lead_floor)
          lead.foundation_year = lead_floor;
        if (Number.isFinite(Number(lead["found.yr"])) && Number(lead["found.yr"]) < lead_floor)
          lead["found.yr"] = lead_floor;
      }

      passthrough[lead_item.key] = lead;
    }

    //Return statement
    return passthrough;
  };

  /**
   * Loads Viscount regional settlements via ViscountGazetteerLoader.
   * @alias population_Stadester_uud.getViscountRegionalObject
   *
   * @param {Object} [arg0_options]
   *
   * @returns {Object}
   */
  population_Stadester_uud.getViscountRegionalObject = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Guard clauses
    if (!global.ViscountGazetteerLoader && typeof require !== "undefined")
      try { require(path.join(__dirname, "ViscountGazetteerLoader.js")); } catch (e) {}
    if (!global.ViscountGazetteerLoader) {
      console.error("population_Stadester_uud.getViscountRegionalObject: ViscountGazetteerLoader unavailable.");
      return {};
    }

    //Return statement
    return global.ViscountGazetteerLoader.getViscountRegionalObject(options);
  };

  /**
   * Backwards-compatible wrapper loading Project POLARIS settlements via ViscountGazetteerLoader.
   * @alias population_Stadester_uud.getPolarisRussiaObject
   *
   * @param {Object} [arg0_options]
   *
   * @returns {Object}
   */
  population_Stadester_uud.getPolarisRussiaObject = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Return statement
    return population_Stadester_uud.getViscountRegionalObject({ only_project: "POLARIS", ...options });
  };
}
