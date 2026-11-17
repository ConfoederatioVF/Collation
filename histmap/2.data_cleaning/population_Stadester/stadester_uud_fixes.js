//Initialise functions
{
  if (!global.population_Stadester_uud) global.population_Stadester_uud = {};

  /**
   * Appends unique, non-empty source tags onto `arg0_city.sources`, migrating and removing any legacy `.type` string.
   * Rejects `"viscount_regional"` placeholders so only canonical DB keys or Viscount project names are recorded.
   * @alias population_Stadester_uud.appendCitySources
   *
   * @param {Object} arg0_city
   * @param {string|Array<string>} [arg1_sources]
   *
   * @returns {Object}
   */
  population_Stadester_uud.appendCitySources = function (arg0_city, arg1_sources) {
    //Convert from parameters
    let city = arg0_city;
    let raw_sources = arg1_sources;

    //Declare local instance variables
    let candidates = [];
    let existing = [];
    let incoming = Array.isArray(raw_sources) ?
      raw_sources : ((raw_sources !== undefined && raw_sources !== null) ? [raw_sources] : []);

    //Guard clauses
    if (!city || typeof city !== "object") return city;

    //Function body
    if (Array.isArray(city.sources)) existing = city.sources.slice();
    city.sources = [];

    for (let i = 0; i < existing.length; i++)
      candidates.push(existing[i]);
    if (typeof city.type === "string" && city.type.trim().length > 0)
      candidates.push(city.type);
    if (city.type !== undefined)
      delete city.type;
    for (let i = 0; i < incoming.length; i++)
      candidates.push(incoming[i]);

    for (let i = 0; i < candidates.length; i++) {
      let src = (typeof candidates[i] === "string") ? candidates[i].trim() : "";
      if (!src || src === "viscount_regional") continue;
      if (!city.sources.includes(src))
        city.sources.push(src);
    }

    //Return statement
    return city;
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
    let manual_entries = [
      { key: "Vaduz-Liechtenstein", pop_2025: 5800 },
      { key: "Macau-Macao", pop_2025: 710000 }
    ];
    let maydanets_names = ["Maydanets-Ukraine", "Maidanets-Ukraine"];
    let taipei_names = ["T'aipei-Taiwan", "Taipei-Taiwan", "Taipei-China"];

    //Function body
    try {
      if (stadester_obj["Washington-United States"])
        stadester_obj["Washington-United States"].coords = [38.906727075772245, -77.0366352170292];

      //Aachen, Germany geolocation fix (Buringh raw coords point to Bergisch Gladbach)
      if (stadester_obj["Aachen-Germany"])
        stadester_obj["Aachen-Germany"].coords = [50.7753455, 6.0838868];

      //Lamphun, Thailand geolocation fix
      if (stadester_obj["Lamphun-Thailand"])
        stadester_obj["Lamphun-Thailand"].coords = [18.5744357, 99.00369719999999];

      //Inject curated manual records if missing
      population_Stadester_uud.injectManualRecords(stadester_obj);
      all_cities = Object.keys(stadester_obj);

      //Ensure Vaduz and Macau have smooth modern annual entries
      for (let i = 0; i < manual_entries.length; i++) {
        let m_cfg = manual_entries[i];
        let m_city = stadester_obj[m_cfg.key];
        if (!m_city || !m_city.population) continue;
        if (m_city.population["2025"] === undefined) m_city.population["2025"] = m_cfg.pop_2025;
        m_city._raw_max_year = 2025;
        let missing_yrs = [];
        for (let x = 1950; x <= 2025; x++)
          if (m_city.population[x] === undefined) missing_yrs.push(x);
        if (missing_yrs.length > 0)
          m_city.population = population_Stadester_uud.linearInterpolationObject(m_city.population, { years: missing_yrs });
      }

      if (stadester_obj["Cardiff-United Kingdom"] && stadester_obj["Rhondda-United Kingdom"]) {
        let cardiff_city = stadester_obj["Cardiff-United Kingdom"];
        let rhondda_city = stadester_obj["Rhondda-United Kingdom"];
        let swap_pop = JSON.parse(JSON.stringify(cardiff_city.population));
        let swap_max = cardiff_city._raw_max_year;
        let swap_min = cardiff_city._raw_min_year;
        cardiff_city.population = JSON.parse(JSON.stringify(rhondda_city.population));
        cardiff_city._raw_max_year = rhondda_city._raw_max_year;
        cardiff_city._raw_min_year = rhondda_city._raw_min_year;
        rhondda_city.population = swap_pop;
        rhondda_city._raw_max_year = swap_max;
        rhondda_city._raw_min_year = swap_min;
      }
      delete stadester_obj["Minneapolis-United States of America"];

      //Taipei anachronistic antiquity & Maydanets archaeological lapse cleanup
      let truncateCityYears = function (arg0_city, arg1_predicate) {
        let props = ["area", "density", "population", "rni", "radial_buffers", "centre_density"];
        for (let p = 0; p < props.length; p++) {
          let dict = arg0_city[props[p]];
          if (!dict) continue;
          let yr_keys = Object.keys(dict);
          for (let y = 0; y < yr_keys.length; y++)
            if (arg1_predicate(parseInt(yr_keys[y], 10))) delete dict[yr_keys[y]];
        }
      };

      for (let t = 0; t < taipei_names.length; t++) {
        let t_city = stadester_obj[taipei_names[t]];
        if (!t_city) continue;
        truncateCityYears(t_city, (yr) => yr < 1700);
        if (t_city.population) {
          let pos_yrs = Object.keys(t_city.population).map(Number).filter(n => !isNaN(n) && Number(t_city.population[n]) > 0).sort((a, b) => a - b);
          t_city._raw_min_year = (pos_yrs.length > 0) ? pos_yrs[0] : null;
        }
      }

      for (let m = 0; m < maydanets_names.length; m++) {
        let m_city = stadester_obj[maydanets_names[m]];
        if (!m_city) continue;
        truncateCityYears(m_city, (yr) => yr >= 0);
        if (m_city.population) m_city.population["-999"] = 0;
        m_city._raw_lapsed = true;
      }
    } catch (e) {
      console.warn(e);
    }

    all_cities = Object.keys(stadester_obj);
    for (let i = 0; i < all_cities.length; i++) {
      let city = stadester_obj[all_cities[i]];
      if (!city || !city.population) continue;
      let pop_keys = Object.keys(city.population);
      for (let x = 0; x < pop_keys.length; x++)
        city.population[pop_keys[x]] = Math.max(0, Math.round(city.population[pop_keys[x]]));
    }

    if (typeof population_Stadester_uud.repairGHSLCityNames === "function")
      population_Stadester_uud.repairGHSLCityNames(stadester_obj);

    //Return statement
    return stadester_obj;
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

    //Declare local instance variables
    let all_cities;
    let cell_size = 2.5;
    let grid = new Map();

    //Function body
    //Deduplicate and merge population first
    stadester_obj = population_Stadester_uud.removeStadesterDuplicates(stadester_obj);
    if (do_not_flatten_metros) return stadester_obj;

    all_cities = Object.keys(stadester_obj);

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
                if (name_a && name_b && (name_a === name_b || name_b.includes(name_a) || name_a.includes(name_b))) { metro_match = agg; break; }
              }
            }
          }
          if (metro_match) break;
        }
        if (metro_match) break;
      }

      if (metro_match && local_city.population && metro_match.population) {
        let local_max_yr = Number.isFinite(local_city._raw_max_year) ? local_city._raw_max_year : -Infinity;
        let pop_keys = Object.keys(metro_match.population);
        for (let x = 0; x < pop_keys.length; x++) {
          let yr = pop_keys[x];
          let yr_num = Number(yr);
          let agg_pop = parseFloat(metro_match.population[yr]);
          let city_pop = parseFloat(local_city.population[yr]);
          if (isNaN(city_pop) && Number.isFinite(local_max_yr) && yr_num > local_max_yr && (yr_num - local_max_yr) <= 30)
            city_pop = parseFloat(local_city.population[local_max_yr]);
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
   * Checks whether `arg0_city` records `arg1_source` in `.sources` (or legacy `.type`).
   * @alias population_Stadester_uud.hasCitySource
   *
   * @param {Object} arg0_city
   * @param {string} arg1_source
   *
   * @returns {boolean}
   */
  population_Stadester_uud.hasCitySource = function (arg0_city, arg1_source) {
    //Convert from parameters
    let city = arg0_city;
    let target = (typeof arg1_source === "string") ? arg1_source.trim() : "";

    //Guard clauses
    if (!city || typeof city !== "object" || !target) return false;

    //Function body
    if (Array.isArray(city.sources) && city.sources.includes(target))
      return true;
    if (city.type === target)
      return true;

    //Return statement
    return false;
  };


  /**
   * Injects curated manual city entries (`Vaduz-Liechtenstein`, `Macau-Macao`) into `arg0_stadester_obj` if absent.
   * @alias population_Stadester_uud.injectManualRecords
   *
   * @param {Object} arg0_stadester_obj
   *
   * @returns {Object}
   */
  population_Stadester_uud.injectManualRecords = function (arg0_stadester_obj) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;

    //Guard clauses
    if (!stadester_obj || typeof stadester_obj !== "object") return stadester_obj;

    //Function body
    let manual_defs = [
      {
        name: "Vaduz", country: "Liechtenstein", elevation: 455, key: "Vaduz-Liechtenstein", coords: [47.141, 9.521],
        original_names: ["vaduz"], other_names: ["Vaduz"], _raw_min_year: 1400, _raw_max_year: 2025, sources: ["manual"],
        population: {
          "1400": 300, "1500": 400, "1600": 500, "1700": 600, "1800": 800, "1900": 1000,
          "1910": 1300, "1920": 1400, "1930": 1600, "1940": 2000, "1950": 2700, "1960": 3400,
          "1970": 3900, "1980": 4600, "1990": 4900, "2000": 5000, "2010": 5200, "2020": 5700, "2025": 5800
        }
      },
      {
        name: "Macau", country: "Macao", elevation: 10, key: "Macau-Macao", coords: [22.1987, 113.5439],
        original_names: ["macau", "macao"], other_names: ["Macau", "Macao"], _raw_min_year: 1557, _raw_max_year: 2025, sources: ["manual"],
        population: {
          "1557": 500, "1560": 1000, "1600": 5000, "1635": 35000, "1700": 19500, "1750": 24000,
          "1800": 30000, "1850": 29000, "1900": 63000, "1910": 75000, "1920": 84000, "1930": 120000,
          "1940": 150000, "1950": 188000, "1960": 169000, "1970": 249000, "1980": 242000, "1990": 352000,
          "2000": 432000, "2010": 540000, "2020": 680000, "2025": 710000
        }
      }
    ];
    for (let i = 0; i < manual_defs.length; i++)
      if (!stadester_obj[manual_defs[i].key]) stadester_obj[manual_defs[i].key] = manual_defs[i];

    //Return statement
    return stadester_obj;
  };


  /**
   * Removes duplicate city entries sharing coordinates and merges their historical populations and source tags.
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

    //Function body
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

      let clusters_in_cell = [];
      for (let i = 0; i < group.length; i++) {
        let candidate_entry = group[i];
        let candidate_city = candidate_entry.city;
        if (!candidate_city || !candidate_city.population) continue;

        let cand_yrs = Object.keys(candidate_city.population).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b);
        let merged_into_cluster = false;

        for (let c = 0; c < clusters_in_cell.length; c++) {
          let leader_entry = clusters_in_cell[c];
          let leader_city = leader_entry.city;
          let is_same_name = population_Stadester_uud.checkExactNameMatch(leader_city, candidate_city);
          if (is_same_name) {
            let lead_yrs = Object.keys(leader_city.population).map(Number).filter(n => !isNaN(n) && Number(leader_city.population[n]) > 0).sort((a, b) => a - b);
            let is_temporally_compatible = true;
            if (lead_yrs.length > 0 && cand_yrs.length > 0) {
              let cand_max_yr = cand_yrs[cand_yrs.length - 1];
              let cand_min_yr = cand_yrs[0];
              let lead_max_yr = lead_yrs[lead_yrs.length - 1];
              let lead_min_yr = lead_yrs[0];
              if (lead_min_yr > cand_max_yr || cand_min_yr > lead_max_yr) {
                let gap_end = (lead_min_yr > cand_max_yr) ? lead_min_yr : cand_min_yr;
                let gap_start = (lead_min_yr > cand_max_yr) ? cand_max_yr : lead_max_yr;
                let max_allowed_gap = population_Stadester_uud.getMaxTemporalProximityGap(gap_start, gap_end);
                if ((gap_end - gap_start) > max_allowed_gap)
                  is_temporally_compatible = false;
              }
            }
            if (is_temporally_compatible) {
              for (let pop_key in candidate_city.population) {
                if (!leader_city.population.hasOwnProperty(pop_key)) {
                  leader_city.population[pop_key] = candidate_city.population[pop_key];
                  leader_entry.had_merged_keys = true;
                }
              }
              if (Number.isFinite(candidate_city._raw_min_year))
                leader_city._raw_min_year = Number.isFinite(leader_city._raw_min_year) ?
                  Math.min(leader_city._raw_min_year, candidate_city._raw_min_year) : candidate_city._raw_min_year;
              if (Number.isFinite(candidate_city._raw_max_year))
                leader_city._raw_max_year = Number.isFinite(leader_city._raw_max_year) ?
                  Math.max(leader_city._raw_max_year, candidate_city._raw_max_year) : candidate_city._raw_max_year;
              if (Array.isArray(candidate_city._war_displacement_years)) {
                if (!leader_city._war_displacement_years) leader_city._war_displacement_years = [];
                for (let w = 0; w < candidate_city._war_displacement_years.length; w++)
                  if (!leader_city._war_displacement_years.includes(candidate_city._war_displacement_years[w]))
                    leader_city._war_displacement_years.push(candidate_city._war_displacement_years[w]);
              }
              population_Stadester_uud.appendCitySources(leader_city, candidate_city.sources || candidate_city.type);
              merged_into_cluster = true;
              break;
            }
          }
        }

        if (!merged_into_cluster)
          clusters_in_cell.push({ key: candidate_entry.key, city: candidate_city, had_merged_keys: false });
      }

      for (let c = 0; c < clusters_in_cell.length; c++) {
        let cluster_item = clusters_in_cell[c];
        let best = cluster_item.city;
        population_Stadester_uud.appendCitySources(best);
        if (cluster_item.had_merged_keys) {
          let all_pop_keys = Object.keys(best.population).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b);
          if (all_pop_keys.length >= 2)
            best.population = population_Stadester_uud.linearInterpolationObject(best.population, { years: all_pop_keys });
        }
        result[cluster_item.key] = best;
      }
    }

    //Return statement
    return result;
  };
}
