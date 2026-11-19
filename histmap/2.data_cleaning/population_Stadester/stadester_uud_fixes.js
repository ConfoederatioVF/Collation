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
      if (stadester_obj["New York-New York"]) {
        stadester_obj["New York-New York"].coords = [40.7128, -74.0060];
        if (Array.isArray(stadester_obj["New York-New York"].other_names))
          stadester_obj["New York-New York"].other_names = stadester_obj["New York-New York"].other_names.filter(function (arg0_n) { return arg0_n !== "Brooklyn"; });
      }

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

      if (stadester_obj["Kahului-Hawaii"])
        stadester_obj["Kahului-Hawaii"].coords = [20.8893, -156.4729];

      if (stadester_obj["Merrimack-New Hampshire"] && stadester_obj["East Merrimack-New Hampshire"]) {
        let merr = stadester_obj["Merrimack-New Hampshire"];
        let emerr = stadester_obj["East Merrimack-New Hampshire"];
        if (!Array.isArray(merr.other_names)) merr.other_names = [];
        if (!merr.other_names.includes("East Merrimack")) merr.other_names.push("East Merrimack");
        if (Array.isArray(emerr.other_names)) {
          for (let ei = 0; ei < emerr.other_names.length; ei++)
            if (emerr.other_names[ei] && !merr.other_names.includes(emerr.other_names[ei]))
              merr.other_names.push(emerr.other_names[ei]);
        }
        delete stadester_obj["East Merrimack-New Hampshire"];
      }

      if (stadester_obj["Allegheny-Pennsylvania"]) {
        let all_pa = stadester_obj["Allegheny-Pennsylvania"];
        all_pa.coords = [40.4564, -80.0088];
        truncateCityYears(all_pa, (yr) => yr > 1907);
        if (all_pa.population) {
          let all_yrs = Object.keys(all_pa.population).map(Number).filter(n => !isNaN(n) && Number(all_pa.population[n]) > 0).sort((a, b) => a - b);
          all_pa._raw_max_year = (all_yrs.length > 0) ? all_yrs[all_yrs.length - 1] : null;
        }
      }

      if (stadester_obj["Allegheny Center (Pittsburgh)-Pennsylvania"]) {
        let ac_pa = stadester_obj["Allegheny Center (Pittsburgh)-Pennsylvania"];
        let target_pa = stadester_obj["Allegheny-Pennsylvania"] || stadester_obj["Pittsburgh-Pennsylvania"];
        if (target_pa) {
          if (!Array.isArray(target_pa.other_names)) target_pa.other_names = [];
          if (!target_pa.other_names.includes("Allegheny Center")) target_pa.other_names.push("Allegheny Center");
          if (Array.isArray(ac_pa.other_names)) {
            for (let ai = 0; ai < ac_pa.other_names.length; ai++)
              if (ac_pa.other_names[ai] && !target_pa.other_names.includes(ac_pa.other_names[ai]))
                target_pa.other_names.push(ac_pa.other_names[ai]);
          }
        }
        delete stadester_obj["Allegheny Center (Pittsburgh)-Pennsylvania"];
      }

      //POLARIS: Clean up Murmansk-Russia empty-population UUD ghost onto Romanov-on-Murman-Russia
      if (stadester_obj["Murmansk-Russia"] && stadester_obj["Romanov-on-Murman-Russia"]) {
        let mur_empty = stadester_obj["Murmansk-Russia"];
        let mur_pop = mur_empty.population || {};
        let has_pos_mur = Object.keys(mur_pop).some(function (arg0_y) { return Number(mur_pop[arg0_y]) > 0; });
        if (!has_pos_mur) {
          let rom_mur = stadester_obj["Romanov-on-Murman-Russia"];
          if (!Array.isArray(rom_mur.other_names)) rom_mur.other_names = [];
          if (!rom_mur.other_names.includes("Murmansk")) rom_mur.other_names.push("Murmansk");
          delete stadester_obj["Murmansk-Russia"];
        }
      }

      //POLARIS: Separate Khazar capital Samandar/Semender (<=1050AD) from modern Makhachkala suburb Semender-Russia (>=1648AD)
      if (stadester_obj["Semender-Russia"] && stadester_obj["Semender-Russia"].population) {
        let sem_mod = stadester_obj["Semender-Russia"];
        if (Number(sem_mod.population["1648"]) > 0 && Number(sem_mod.population["700"]) > 5000) {
          if (!stadester_obj["Semender Khazar Capital-Russia"]) {
            let kh_pop = {};
            let sem_yrs = Object.keys(sem_mod.population);
            for (let sy = 0; sy < sem_yrs.length; sy++) {
              let yr_n = parseInt(sem_yrs[sy], 10);
              if (Number.isFinite(yr_n) && yr_n <= 1050 && Number(sem_mod.population[sem_yrs[sy]]) > 0)
                kh_pop[sem_yrs[sy]] = Math.round(Number(sem_mod.population[sem_yrs[sy]]));
            }
            if (Object.keys(kh_pop).length >= 2) {
              stadester_obj["Semender Khazar Capital-Russia"] = {
                coords: [42.94423, 47.49527],
                country: "Russia",
                key: "Semender Khazar Capital-Russia",
                name: "Semender (Khazar Capital)",
                other_names: ["Samandar", "Khazar Samandar"],
                population: kh_pop,
                sources: ["POLARIS"],
                viscount_project: "POLARIS"
              };
            }
          }
          truncateCityYears(sem_mod, function (arg0_yr) { return arg0_yr < 1648; });
          sem_mod["found.yr"] = 1648;
          sem_mod.foundation_year = 1648;
        }
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

    let foreign_script_re = /[\u0400-\u04FF\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]/;
    let latin_centaur_countries = new Set([
      "Alabama", "Alaska", "American Samoa", "Arizona", "Arkansas", "Bermuda", "Bolivia", "Brazil",
      "California", "Canada", "Colorado", "Connecticut", "Delaware", "District of Columbia", "Florida",
      "French Guiana", "Greenland", "Guyana", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas",
      "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
      "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
      "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
      "Paraguay", "Pennsylvania", "Rhode Island", "Saint Pierre and Miquelon", "South Carolina",
      "South Dakota", "Suriname", "Tennessee", "Texas", "United States", "United States of America",
      "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
    ]);
    all_cities = Object.keys(stadester_obj);
    for (let i = 0; i < all_cities.length; i++) {
      let city = stadester_obj[all_cities[i]];
      if (!city) continue;
      let c_name = String(city.country || "").trim();
      let is_us_georgia = (c_name === "Georgia" && Array.isArray(city.coords) && Number(city.coords[1]) < -30);
      if (!latin_centaur_countries.has(c_name) && !is_us_georgia) continue;
      if (Array.isArray(city.other_names)) {
        city.other_names = city.other_names.filter(function (arg0_a) {
          let s = String(arg0_a || "").trim();
          return s && !foreign_script_re.test(s) && !/^Ist\s+Pitc/i.test(s);
        });
      }
      if (Array.isArray(city.original_names)) {
        city.original_names = city.original_names.filter(function (arg0_a) {
          let s = String(arg0_a || "").trim();
          return s && !foreign_script_re.test(s) && !/^ist\s+pitc/i.test(s);
        });
      }
    }

    //Post-merge sweep across stadester_obj to eliminate remaining *-United States duplicates
    let cur_keys = Object.keys(stadester_obj);
    let viscount_state_entries = [];

    for (let i = 0; i < cur_keys.length; i++) {
      let v_city = stadester_obj[cur_keys[i]];
      if (!v_city || typeof v_city !== "object" || !Array.isArray(v_city.coords) || v_city.coords.length < 2) continue;
      if (!population_Stadester_uud.hasViscountSource(v_city)) continue;
      if (v_city.country === "United States" || v_city.country === "United States of America") continue;
      if (typeof population_Stadester_uud.isUSCountryOrState === "function" && population_Stadester_uud.isUSCountryOrState(v_city.country))
        viscount_state_entries.push(v_city);
    }

    for (let i = 0; i < cur_keys.length; i++) {
      let c_key = cur_keys[i];
      let city = stadester_obj[c_key];
      if (!city || typeof city !== "object" || !Array.isArray(city.coords) || city.coords.length < 2) continue;
      if (c_key === "Washington-United States") continue;
      if (city.country !== "United States" && city.country !== "United States of America") continue;
      if (population_Stadester_uud.hasViscountSource(city)) continue;

      let best_dist = 30.0;
      let best_target = null;
      let city_name_prim = (typeof population_Stadester_uud.processCityName === "function") ?
        population_Stadester_uud.processCityName(city.name) : String(city.name || "").toLowerCase();

      for (let x = 0; x < viscount_state_entries.length; x++) {
        let v_entry = viscount_state_entries[x];
        let v_name_prim = (typeof population_Stadester_uud.processCityName === "function") ?
          population_Stadester_uud.processCityName(v_entry.name) : String(v_entry.name || "").toLowerCase();
        if (
          (city_name_prim === "brooklyn" && (v_name_prim === "new york" || v_name_prim === "new york city")) ||
          (v_name_prim === "brooklyn" && (city_name_prim === "new york" || city_name_prim === "new york city"))
        ) {
          continue;
        }
        let d_km = population_Stadester_uud.haversineDistance(city.coords, v_entry.coords);
        if (d_km <= best_dist) {
          let is_match = (typeof population_Stadester_uud.checkExactNameMatch === "function") ?
            population_Stadester_uud.checkExactNameMatch(city, v_entry) : (city.name === v_entry.name);
          if (is_match) {
            best_dist = d_km;
            best_target = v_entry;
          }
        }
      }

      if (best_target) {
        let v_yrs = Object.keys(best_target.population || {}).map(Number).filter(function (arg0_n) {
          return Number.isFinite(arg0_n) && Number(best_target.population[arg0_n]) > 0;
        }).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
        let min_viscount_yr = (v_yrs.length > 0) ? v_yrs[0] : Infinity;
        let found_yr = Number(best_target["found.yr"] !== undefined ? best_target["found.yr"] : (best_target.foundation_year !== undefined ? best_target.foundation_year : (city["found.yr"] !== undefined ? city["found.yr"] : city.foundation_year)));
        if (!Number.isFinite(found_yr)) found_yr = -Infinity;

        if (city.population) {
          if (!best_target.population) best_target.population = {};
          let c_yrs = Object.keys(city.population);
          for (let y = 0; y < c_yrs.length; y++) {
            let yr_num = parseInt(c_yrs[y], 10);
            let val = Number(city.population[c_yrs[y]]);
            if (Number.isFinite(yr_num) && Number.isFinite(val) && val > 0) {
              if (yr_num >= found_yr && yr_num < min_viscount_yr && best_target.population[c_yrs[y]] === undefined)
                best_target.population[c_yrs[y]] = val;
            }
          }
        }

        if (!best_target.other_names) best_target.other_names = [];
        if (city.name && city.name !== best_target.name && !best_target.other_names.includes(city.name))
          best_target.other_names.push(city.name);
        if (Array.isArray(city.other_names)) {
          for (let on = 0; on < city.other_names.length; on++) {
            let on_name = city.other_names[on];
            if (on_name && on_name !== best_target.name && !best_target.other_names.includes(on_name))
              best_target.other_names.push(on_name);
          }
        }

        if (Number.isFinite(found_yr) && (best_target["found.yr"] === undefined || found_yr < Number(best_target["found.yr"]))) {
          best_target["found.yr"] = found_yr;
          best_target.foundation_year = found_yr;
        }

        population_Stadester_uud.appendCitySources(best_target, city.sources || city.type);
        if (best_target.name === "New York" && best_target.country === "New York") {
          best_target.coords = [40.7128, -74.0060];
          if (Array.isArray(best_target.other_names))
            best_target.other_names = best_target.other_names.filter(function (arg0_n) { return arg0_n !== "Brooklyn"; });
        }
        delete stadester_obj[c_key];
      }
    }

    //Enforce foundation_year pruning: delete every population key with Number(yr) < found_yr
    all_cities = Object.keys(stadester_obj);
    for (let i = 0; i < all_cities.length; i++) {
      let city = stadester_obj[all_cities[i]];
      if (!city || !city.population) continue;
      let found_yr = Number(city["found.yr"] !== undefined ? city["found.yr"] : city.foundation_year);
      if (Number.isFinite(found_yr) && found_yr > 2026) {
        found_yr = (found_yr >= 100000 && found_yr <= 202699) ? Math.floor(found_yr/100) : NaN;
        if (Number.isFinite(found_yr)) {
          city["found.yr"] = found_yr;
          city.foundation_year = found_yr;
        } else {
          delete city["found.yr"];
          delete city.foundation_year;
        }
      }
      if (Number.isFinite(found_yr)) {
        let p_keys = Object.keys(city.population);
        for (let x = 0; x < p_keys.length; x++) {
          let yr_num = parseInt(p_keys[x], 10);
          if (Number.isFinite(yr_num) && yr_num < found_yr)
            delete city.population[p_keys[x]];
        }
        if (Number.isFinite(city._raw_min_year) && city._raw_min_year < found_yr) {
          let rem_yrs = Object.keys(city.population).map(Number).filter(function (arg0_n) {
            return Number.isFinite(arg0_n) && Number(city.population[arg0_n]) > 0;
          }).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
          city._raw_min_year = (rem_yrs.length > 0) ? rem_yrs[0] : null;
        }
      }
    }

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
                let is_name_overlap = population_Stadester_uud.checkExactNameMatch(local_city, agg);
                if (!is_name_overlap) {
                  let all_a = population_Stadester_uud.getAllCityNames(local_city);
                  let all_b = population_Stadester_uud.getAllCityNames(agg);
                  for (let ax = 0; ax < all_a.length && !is_name_overlap; ax++) {
                    for (let bx = 0; bx < all_b.length; bx++) {
                      let na = all_a[ax];
                      let nb = all_b[bx];
                      if (na.length >= 4 && nb.length >= 4 && (na === nb || nb.includes(na) || na.includes(nb))) {
                        is_name_overlap = true;
                        break;
                      }
                    }
                  }
                }
                if (is_name_overlap) { metro_match = agg; break; }
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
   * Checks whether `arg0_city` carries any Viscount regional project attribution (`.viscount_project` or a complete Viscount source tag).
   * @alias population_Stadester_uud.hasViscountSource
   *
   * @param {Object} arg0_city
   *
   * @returns {boolean}
   */
  population_Stadester_uud.hasViscountSource = function (arg0_city) {
    //Convert from parameters
    let city = arg0_city;

    //Guard clauses
    if (!city || typeof city !== "object") return false;

    //Function body
    if (typeof city.viscount_project === "string" && city.viscount_project.trim().length > 0)
      return true;
    if (
      population_Stadester_uud.hasCitySource(city, "POLARIS") ||
      population_Stadester_uud.hasCitySource(city, "CENTAUR")
    ) {
      return true;
    }

    let io_lib = (typeof StadesterPartitionIO !== "undefined") ? StadesterPartitionIO : null;
    if (!io_lib && typeof require !== "undefined") {
      try {
        let mod = require("./StadesterPartitionIO.js");
        io_lib = (mod && mod.StadesterPartitionIO) ? mod.StadesterPartitionIO : global.StadesterPartitionIO;
      } catch (e) {}
    }
    if (io_lib && typeof io_lib.loadPrecedenceRegistry === "function") {
      let reg = io_lib.loadPrecedenceRegistry();
      let projs = Array.isArray(reg && reg.projects) ? reg.projects : [];
      for (let i = 0; i < projs.length; i++) {
        if (projs[i].status === "complete" && population_Stadester_uud.hasCitySource(city, projs[i].key))
          return true;
      }
    }

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
   * Checks whether `arg0_country` (or optional `arg1_city` with coordinates) belongs to a Viscount regional project whose status is `"complete"`.
   * @alias population_Stadester_uud.isCompleteViscountCountry
   *
   * @param {string} arg0_country
   * @param {Object} [arg1_city]
   *
   * @returns {boolean}
   */
  population_Stadester_uud.isCompleteViscountCountry = function (arg0_country, arg1_city) {
    //Convert from parameters
    let city = (arg1_city && typeof arg1_city === "object") ? arg1_city : null;
    let country = (arg0_country) ? String(arg0_country) : "";

    //Declare local instance variables
    let io_lib = (typeof StadesterPartitionIO !== "undefined") ? StadesterPartitionIO : null;

    //Function body
    if (!io_lib && typeof require !== "undefined") {
      try {
        let mod = require("./StadesterPartitionIO.js");
        io_lib = (mod && mod.StadesterPartitionIO) ? mod.StadesterPartitionIO : global.StadesterPartitionIO;
      } catch (e) {}
    }

    if (io_lib && typeof io_lib.loadPrecedenceRegistry === "function") {
      let reg = io_lib.loadPrecedenceRegistry();
      if (city && typeof io_lib.assignCityToViscountRegion === "function") {
        let assigned = io_lib.assignCityToViscountRegion(city, city.key || "", reg);
        if (assigned) {
          //Return statement
          return assigned.status === "complete";
        }
      }
      let norm = io_lib.normaliseCountryString(country);
      let proj = (reg && reg.country_lookup) ? reg.country_lookup[norm] : null;
      if (proj) {
        //Return statement
        return proj.status === "complete";
      }
    }

    //Return statement
    return (country === "Russia" || country === "Ukraine" || country === "Belarus");
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
          let name_lead_prim = (typeof population_Stadester_uud.processCityName === "function") ?
            population_Stadester_uud.processCityName(leader_city.name || "") : String(leader_city.name || "").toLowerCase();
          let name_cand_prim = (typeof population_Stadester_uud.processCityName === "function") ?
            population_Stadester_uud.processCityName(candidate_city.name || "") : String(candidate_city.name || "").toLowerCase();
          if (
            (name_cand_prim === "brooklyn" && (name_lead_prim === "new york" || name_lead_prim === "new york city")) ||
            (name_lead_prim === "brooklyn" && (name_cand_prim === "new york" || name_cand_prim === "new york city"))
          ) {
            continue;
          }
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


  /**
   * Absorbs co-located (`<= 1,5 km`) same-country overlapping `>= 1850 AD` CENTAUR twin records
   * cleanly into the higher-ranking primary city so compiled Stadestér 2.0 shards contain zero `[TWINS]`.
   * @alias population_Stadester_uud.reconcileCloseSameCountryTwins
   *
   * @param {Object} arg0_stadester_obj
   *
   * @returns {Object}
   */
  population_Stadester_uud.reconcileCloseSameCountryTwins = function (arg0_stadester_obj) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;

    //Guard clauses
    if (!stadester_obj || typeof stadester_obj !== "object") return stadester_obj;

    //Declare local instance variables
    let all_keys = Object.keys(stadester_obj);
    let by_country = {};
    let merged_count = 0;

    let haversineKm = function (arg0_c1, arg1_c2) {
      let la1 = Number(arg0_c1[0])*Math.PI/180;
      let lo1 = Number(arg0_c1[1])*Math.PI/180;
      let la2 = Number(arg1_c2[0])*Math.PI/180;
      let lo2 = Number(arg1_c2[1])*Math.PI/180;
      let d_la = la2 - la1;
      let d_lo = lo2 - lo1;
      let h = Math.sin(d_la*0.5)*Math.sin(d_la*0.5) +
        Math.cos(la1)*Math.cos(la2)*Math.sin(d_lo*0.5)*Math.sin(d_lo*0.5);

      return 12742*Math.asin(Math.min(1, Math.sqrt(h)));
    };

    //Drop or merge legacy Populstat `(agglomeration)` ghost records inside PRETA/CENTAUR into their base city
    let agglom_keys = Object.keys(stadester_obj).filter(function (arg0_k) {
      let c = stadester_obj[arg0_k];
      return c && /\(agglomeration\)/i.test(String(c.name || arg0_k));
    });
    for (let i = 0; i < agglom_keys.length; i++) {
      let ak = agglom_keys[i];
      let ac = stadester_obj[ak];
      if (!ac) continue;
      let a_proj = String(ac.viscount_project || "").toUpperCase();
      if (!a_proj && typeof global.StadesterPartitionIO !== "undefined" && typeof global.StadesterPartitionIO.assignCityToViscountRegion === "function") {
        let rd = global.StadesterPartitionIO.assignCityToViscountRegion(ac, ak);
        if (rd && rd.key) a_proj = String(rd.key).toUpperCase();
      }
      if (a_proj !== "PRETA" && a_proj !== "CENTAUR") continue;
      let base_name = String(ac.name || "").replace(/\s*\(agglomeration\)\s*/gi, "").trim();
      let base_key = `${base_name}-${ac.country}`;
      let target = stadester_obj[base_key];
      if (!target && Array.isArray(ac.coords)) {
        let cand_keys = Object.keys(stadester_obj);
        for (let x = 0; x < cand_keys.length; x++) {
          let ck = cand_keys[x];
          if (ck === ak) continue;
          let cc = stadester_obj[ck];
          if (!cc || cc.country !== ac.country || !Array.isArray(cc.coords)) continue;
          if (String(cc.name || "").trim().toLowerCase() === base_name.toLowerCase() && haversineKm(ac.coords, cc.coords) <= 25.0) {
            target = cc;
            break;
          }
        }
      }
      if (target && target.population && ac.population) {
        let a_yrs = Object.keys(ac.population);
        for (let y = 0; y < a_yrs.length; y++) {
          let yk = a_yrs[y];
          let yv = Number(ac.population[yk]);
          if (Number.isFinite(yv) && yv > 0 && !(Number(target.population[yk]) > 0))
            target.population[yk] = yv;
        }
        population_Stadester_uud.appendCitySources(target, ac.sources || ac.type);
      }
      delete stadester_obj[ak];
      merged_count++;
    }

    //Function body
    all_keys = Object.keys(stadester_obj);
    for (let i = 0; i < all_keys.length; i++) {
      let key = all_keys[i];
      let city = stadester_obj[key];

      if (!city || !Array.isArray(city.coords) || !city.population) continue;
      let ctry = String(city.country || "").trim().toLowerCase();
      let proj_key = String(city.viscount_project || "").toUpperCase();

      if (!proj_key && typeof global.StadesterPartitionIO !== "undefined" && typeof global.StadesterPartitionIO.assignCityToViscountRegion === "function") {
        let reg_desc = global.StadesterPartitionIO.assignCityToViscountRegion(city, key);

        if (reg_desc && reg_desc.key) proj_key = String(reg_desc.key).toUpperCase();
      }
      let active_ge1850 = new Set();
      let max_pop = 0;
      let yr_keys = Object.keys(city.population);

      for (let x = 0; x < yr_keys.length; x++) {
        let yr = Number(yr_keys[x]);
        let val = Number(city.population[yr_keys[x]]);

        if (Number.isFinite(yr) && val > 0) {
          if (yr >= 1850) active_ge1850.add(yr);
          if (val > max_pop) max_pop = val;
        }
      }
      if (active_ge1850.size === 0) continue;
      let srcs = Array.isArray(city.sources) ? city.sources : (city.type ? [city.type] : []);
      let score = (srcs.includes("populstat") ? 1e8 : 0) +
        (srcs.includes("chandler_modelski") ? 5e7 : 0) +
        (srcs.some(function (arg0_s) { return arg0_s !== "CENTAUR"; }) ? 1e7 : 0) +
        max_pop;

      if (!by_country[ctry]) by_country[ctry] = [];
      by_country[ctry].push({
        active_ge1850: active_ge1850,
        city: city,
        dropped: false,
        key: key,
        proj_key: proj_key,
        score: score
      });
    }

    let countries = Object.keys(by_country);

    for (let c = 0; c < countries.length; c++) {
      let arr = by_country[countries[c]];

      if (arr.length < 2) continue;
      arr.sort(function (arg0_a, arg1_b) { return arg1_b.score - arg0_a.score; });

      for (let i = 0; i < arr.length; i++) {
        let a = arr[i];

        if (a.dropped) continue;
        for (let x = i + 1; x < arr.length; x++) {
          let b = arr[x];

          if (b.dropped) continue;
          let touches_viscount = (
            a.proj_key === "CENTAUR" || b.proj_key === "CENTAUR" ||
            a.proj_key === "PRETA" || b.proj_key === "PRETA"
          );

          if (!touches_viscount) continue;
          if (Math.abs(a.city.coords[0] - b.city.coords[0]) > 0.02 || Math.abs(a.city.coords[1] - b.city.coords[1]) > 0.06) continue;
          let overlaps = false;

          b.active_ge1850.forEach(function (arg0_yr) {
            if (a.active_ge1850.has(arg0_yr)) overlaps = true;
          });
          if (!overlaps) continue;
          if (haversineKm(a.city.coords, b.city.coords) > 1.5) continue;

          if (!Array.isArray(a.city.other_names)) a.city.other_names = [];
          if (b.city.name && !a.city.other_names.includes(b.city.name)) a.city.other_names.push(b.city.name);
          if (Array.isArray(b.city.other_names)) {
            for (let k = 0; k < b.city.other_names.length; k++)
              if (b.city.other_names[k] && !a.city.other_names.includes(b.city.other_names[k]))
                a.city.other_names.push(b.city.other_names[k]);
          }
          let b_yrs = Object.keys(b.city.population);

          for (let y = 0; y < b_yrs.length; y++) {
            let yk = b_yrs[y];
            let yv = Number(b.city.population[yk]);
            let yi = Number(yk);

            if (Number.isFinite(yv) && yv > 0 && !(Number(a.city.population[yk]) > 0)) {
              a.city.population[yk] = yv;
              if (Number.isFinite(yi) && yi >= 1850) a.active_ge1850.add(yi);
            }
          }
          population_Stadester_uud.appendCitySources(a.city, b.city.sources || b.city.type);
          delete stadester_obj[b.key];
          b.dropped = true;
          merged_count++;
        }
      }
    }
    if (merged_count > 0)
      console.log(`- Reconciled ${merged_count} close same-country CENTAUR twin record(s).`);

    //Return statement
    return stadester_obj;
  };
}
