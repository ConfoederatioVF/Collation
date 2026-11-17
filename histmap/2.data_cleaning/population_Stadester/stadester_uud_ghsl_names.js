//Initialise functions
{
  if (!global.population_Stadester_uud) global.population_Stadester_uud = {};

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

    for (let i = 1; i < candidates.length; i++)
      if (!candidates[i].isCorrupted && !candidates[i].hasSubordinateTerm) return candidates[i].cleanName;
    if (target_pop < 150000)
      for (let i = 1; i < candidates.length; i++)
        if (!candidates[i].isCorrupted) return candidates[i].cleanName;

    //Return statement
    return cand_zero.cleanName || population_Stadester_uud.cleanCandidateCityString(raw_name);
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
      "arrondissement", "borough", "county", "district", "locality", "new area",
      "prefecture", "subdistrict", "subprefecture", "suburb", "township", "ward", "zone"
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
        "F:/Active Projects/Project 1436 - Dataview/data/stadester/GHSL.csv", path.join(h1, "population_Stadester", "ghsl", "GHSL.csv"),
        path.join(h1, "population_GHSL", "GHSL.csv"), path.join(h1, "population_GHSL", "GHS_UCDB_MTUC_GLOBE_R2024A.csv"),
        "D:/Project 1436 - Dataview/data/stadester/GHSL.csv"
      ];
      for (let i = 0; i < candidate_paths.length; i++)
        if (fs.existsSync(candidate_paths[i])) { resolved_path = candidate_paths[i]; break; }
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

      candidate_records.push({ cleanName: cleaned, hasSubordinateTerm: is_subordinate, isCorrupted: is_corrupt, originalText: raw_part, rank: i });
    }

    //Return statement
    return candidate_records;
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
    resolved_name = population_Stadester_uud.resolveCityDisplayName(city.key || "", city.name || "", city.coords, max_pop, city.id);

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
}
