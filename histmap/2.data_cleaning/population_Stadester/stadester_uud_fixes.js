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

      //MANDALA: Normalise legacy Populstat Vietnamese Mojibake keys, Thai/Lao/Khmer exonym keys & Ban-prefix twins
      let sea_mojibake_renames = [
        ["Ha nôi-Vietnam", "Hanoi-Vietnam", "Hanoi", null],
        ["-Dà Nãng-Vietnam", "Da Nang-Vietnam", "Da Nang", null],
        ["Hãi Phong-Vietnam", "Hai Phong-Vietnam", "Hai Phong", null],
        ["Krung Thep-Thailand", "Bangkok-Thailand", "Bangkok", "Krung Thep"],
        ["Ban Pak Phanang-Thailand", "Pak Phanang-Thailand", "Pak Phanang", "Ban Pak Phanang"],
        ["Krâchéh-Cambodia", "Kratie-Cambodia", "Kratie", "Krâchéh"],
        ["Viangchan-Laos", "Vientiane-Laos", "Vientiane", "Viangchan"]
      ];
      for (let sm = 0; sm < sea_mojibake_renames.length; sm++) {
        let [bad_k, good_k, good_nm, keep_alias] = sea_mojibake_renames[sm];
        let bad_c = stadester_obj[bad_k];
        if (!bad_c) continue;
        let good_c = stadester_obj[good_k];
        if (good_c && good_c.population && bad_c.population) {
          let byrs = Object.keys(bad_c.population);
          for (let by = 0; by < byrs.length; by++) {
            let yk = byrs[by];
            let bv = Number(bad_c.population[yk]) || 0;
            let gv = Number(good_c.population[yk]) || 0;
            if (bv > gv && gv === 0) good_c.population[yk] = bv;
          }
          if (!Array.isArray(good_c.other_names)) good_c.other_names = [];
          if (keep_alias && !good_c.other_names.includes(keep_alias))
            good_c.other_names.push(keep_alias);
          population_Stadester_uud.appendCitySources(good_c, bad_c.sources || bad_c.type);
          delete stadester_obj[bad_k];
        } else {
          bad_c.key = good_k;
          bad_c.name = good_nm;
          if (keep_alias) {
            if (!Array.isArray(bad_c.other_names)) bad_c.other_names = [];
            if (!bad_c.other_names.includes(keep_alias)) bad_c.other_names.push(keep_alias);
          }
          stadester_obj[good_k] = bad_c;
          delete stadester_obj[bad_k];
        }
      }

      //MANDALA: Disambiguate legacy Simpang Empat-Malaysia at Sitiawan coords (4.22N, 100.70E) from Simpang Empat (Perak 4.95N)
      if (stadester_obj["Simpang Empat-Malaysia"] && Array.isArray(stadester_obj["Simpang Empat-Malaysia"].coords) && Number(stadester_obj["Simpang Empat-Malaysia"].coords[0]) < 4.5) {
        let se_sit = stadester_obj["Simpang Empat-Malaysia"];
        let sit_existing = stadester_obj["Sitiawan-Malaysia"];
        if (sit_existing && sit_existing.population && se_sit.population) {
          let syrs = Object.keys(se_sit.population);
          for (let sy = 0; sy < syrs.length; sy++) {
            let yk = syrs[sy];
            let sv = Number(se_sit.population[yk]) || 0;
            let gv = Number(sit_existing.population[yk]) || 0;
            if (sv > gv) sit_existing.population[yk] = sv;
          }
          population_Stadester_uud.appendCitySources(sit_existing, se_sit.sources || se_sit.type);
          delete stadester_obj["Simpang Empat-Malaysia"];
        } else {
          se_sit.key = "Sitiawan-Malaysia";
          se_sit.name = "Sitiawan";
          if (!Array.isArray(se_sit.other_names)) se_sit.other_names = [];
          if (!se_sit.other_names.includes("Simpang Empat")) se_sit.other_names.push("Simpang Empat");
          stadester_obj["Sitiawan-Malaysia"] = se_sit;
          delete stadester_obj["Simpang Empat-Malaysia"];
        }
        if (stadester_obj["Simpang Empat-Malaysia_2"] && !stadester_obj["Simpang Empat-Malaysia"]) {
          let se_real = stadester_obj["Simpang Empat-Malaysia_2"];
          se_real.key = "Simpang Empat-Malaysia";
          stadester_obj["Simpang Empat-Malaysia"] = se_real;
          delete stadester_obj["Simpang Empat-Malaysia_2"];
        }
      }

      //INDUS: Clean legacy Populstat South Asian cantonment/OG/township outgrowths & circumflex Romanisations
      let indus_countries = new Set(["India", "Pakistan", "Bangladesh", "Sri Lanka", "Nepal", "Bhutan", "Maldives"]);
      let indus_drop_re = /(?:\b(?:cantonment|cantt\.?|stage\s+og|layout\s+og|og|township|railway\s+settlement|civil\s+lines|defence\s+colony|model\s+town|punjabi\s+bagh|karol\s+bagh|electronic\s+city|finance\s+tec|national\s+park|tea\s+garden|project\s+site)\b|new\s+kar[âa]chi\s+no\.\s*\d)/i;
      let indus_ward_drops = new Set([
        "New Delhi-India", "Behala-India", "Jadabpur-India", "Sultanpur Majra-India",
        "Landhi Korangi-Pakistan", "Sahijpur Bogha-India"
      ]);
      let indus_canonical_renames = {
        "Wâh Cantonment-Pakistan": ["Wah-Pakistan", "Wah"],
        "Wah Cantonment-Pakistan": ["Wah-Pakistan", "Wah"],
        "Khâriân Cantonment-Pakistan": ["Kharian-Pakistan", "Kharian"],
        "Kharian Cantonment-Pakistan": ["Kharian-Pakistan", "Kharian"],
        "Hâora-India": ["Howrah-India", "Howrah"],
        "Hubli-Dhârwâr-India": ["Hubballi-Dharwad-India", "Hubballi-Dharwad"],
        "New Barâkpur-India": ["New Barrackpore-India", "New Barrackpore"],
        "Ulubâria-India": ["Uluberia-India", "Uluberia"],
        "Sandîp-Bangladesh": ["Sandwip-Bangladesh", "Sandwip"],
        "Bhadrâvati New Town-India": ["Bhadravati-India", "Bhadravati"],
        "Raurkela-India": ["Rourkela-India", "Rourkela"]
      };
      let indus_all_keys = Object.keys(stadester_obj);
      for (let ik = 0; ik < indus_all_keys.length; ik++) {
        let cur_k = indus_all_keys[ik];
        let cur_c = stadester_obj[cur_k];
        if (!cur_c || !indus_countries.has(cur_c.country)) continue;
        if (indus_canonical_renames[cur_k]) {
          let [tgt_k, tgt_nm] = indus_canonical_renames[cur_k];
          let existing_tgt = stadester_obj[tgt_k];
          if (existing_tgt && existing_tgt !== cur_c) {
            if (cur_c.population && existing_tgt.population) {
              let cyrs = Object.keys(cur_c.population);
              for (let cy = 0; cy < cyrs.length; cy++) {
                if (existing_tgt.population[cyrs[cy]] === undefined && Number(cur_c.population[cyrs[cy]]) > 0)
                  existing_tgt.population[cyrs[cy]] = cur_c.population[cyrs[cy]];
              }
            }
            population_Stadester_uud.appendCitySources(existing_tgt, cur_c.sources || cur_c.type);
            delete stadester_obj[cur_k];
          } else {
            cur_c.key = tgt_k;
            cur_c.name = tgt_nm;
            stadester_obj[tgt_k] = cur_c;
            if (tgt_k !== cur_k) delete stadester_obj[cur_k];
          }
          continue;
        }
        let cur_nm = String(cur_c.name || "").replace(/[!^%+]+/g, "").replace(/\s*&\s*$/, "").trim();
        if (cur_nm !== String(cur_c.name || "")) cur_c.name = cur_nm;
        if (indus_ward_drops.has(cur_k) || indus_drop_re.test(cur_nm)) {
          delete stadester_obj[cur_k];
          continue;
        }
        if (/[âêîôûÂÊÎÔÛ]/.test(cur_nm) || /[âêîôûÂÊÎÔÛ]/.test(cur_k)) {
          let stripped_nm = cur_nm.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
          let stripped_k = cur_k.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
          if (stripped_nm && stripped_nm !== cur_nm) {
            if (!Array.isArray(cur_c.other_names)) cur_c.other_names = [];
            if (!cur_c.other_names.includes(stripped_nm)) cur_c.other_names.push(stripped_nm);
            cur_c.name = stripped_nm;
          }
          if (stripped_k && stripped_k !== cur_k) {
            let ex_clean = stadester_obj[stripped_k];
            if (ex_clean && ex_clean !== cur_c && Array.isArray(ex_clean.coords) && Array.isArray(cur_c.coords) &&
                population_Stadester_uud.haversineDistance(ex_clean.coords, cur_c.coords) <= 25) {
              if (cur_c.population && ex_clean.population) {
                let cyrs = Object.keys(cur_c.population);
                for (let cy = 0; cy < cyrs.length; cy++) {
                  if (ex_clean.population[cyrs[cy]] === undefined && Number(cur_c.population[cyrs[cy]]) > 0)
                    ex_clean.population[cyrs[cy]] = cur_c.population[cyrs[cy]];
                }
              }
              population_Stadester_uud.appendCitySources(ex_clean, cur_c.sources || cur_c.type);
              delete stadester_obj[cur_k];
            } else if (!ex_clean) {
              cur_c.key = stripped_k;
              stadester_obj[stripped_k] = cur_c;
              delete stadester_obj[cur_k];
            }
          }
        }
      }
      //INDUS: Absorb any remaining non-Viscount Populstat twin within 5 km of a same-name INDUS city
      let indus_visc_by_nc = new Map();
      let post_indus_keys = Object.keys(stadester_obj);
      for (let pk = 0; pk < post_indus_keys.length; pk++) {
        let vc = stadester_obj[post_indus_keys[pk]];
        if (!vc || !indus_countries.has(vc.country) || !Array.isArray(vc.coords) || vc.coords.length < 2) continue;
        if (!population_Stadester_uud.hasViscountSource(vc)) continue;
        let nk = `${String(vc.name || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim()}|${vc.country}`;
        if (!indus_visc_by_nc.has(nk)) indus_visc_by_nc.set(nk, []);
        indus_visc_by_nc.get(nk).push(vc);
      }
      for (let pk = 0; pk < post_indus_keys.length; pk++) {
        let cur_k = post_indus_keys[pk];
        let nc = stadester_obj[cur_k];
        if (!nc || !indus_countries.has(nc.country) || !Array.isArray(nc.coords) || nc.coords.length < 2) continue;
        if (population_Stadester_uud.hasViscountSource(nc)) continue;
        let nk = `${String(nc.name || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim()}|${nc.country}`;
        let vc_list = indus_visc_by_nc.get(nk);
        if (!vc_list) continue;
        for (let vi = 0; vi < vc_list.length; vi++) {
          let vc = vc_list[vi];
          if (population_Stadester_uud.haversineDistance(nc.coords, vc.coords) <= 5.0) {
            population_Stadester_uud.appendCitySources(vc, nc.sources || nc.type);
            delete stadester_obj[cur_k];
            break;
          }
        }
      }

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
      "California", "Canada", "Colombia", "Colorado", "Connecticut", "Delaware", "District of Columbia",
      "Ecuador", "Florida", "French Guiana", "Greenland", "Guyana", "Hawaii", "Idaho", "Illinois",
      "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts",
      "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
      "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota",
      "Ohio", "Oklahoma", "Oregon", "Paraguay", "Pennsylvania", "Peru", "Rhode Island",
      "Saint Pierre and Miquelon", "South Carolina", "South Dakota", "Suriname", "Tennessee", "Texas",
      "United States", "United States of America", "Utah", "Vermont", "Virginia", "Washington",
      "West Virginia", "Wisconsin", "Wyoming"
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
      if (Number.isFinite(found_yr) && found_yr > 0 && found_yr < 1) {
        found_yr = Math.round(found_yr*10000);
        city["found.yr"] = found_yr;
        city.foundation_year = found_yr;
      }
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

      // Case-insensitive deduplication of .other_names (drop exact duplicates and exact matches to .name)
      if (Array.isArray(city.other_names)) {
        let seen_other = new Set([String(city.name || "").trim().toLowerCase()]);
        let clean_other = [];
        for (let oi = 0; oi < city.other_names.length; oi++) {
          let s = String(city.other_names[oi] || "").trim();
          let lo = s.toLowerCase();
          if (!s || seen_other.has(lo)) continue;
          seen_other.add(lo);
          clean_other.push(s);
        }
        if (clean_other.length > 0) city.other_names = clean_other;
        else delete city.other_names;
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
    if (do_not_flatten_metros === true) return stadester_obj;

    //Use the unified 3-Phase Spatiotemporally Agnostic Metropolitan Reconciler
    let MetroRec = global.StadesterMetroReconciler;
    if (!MetroRec) {
      let rec_p = (typeof __dirname !== "undefined" && fs.existsSync(path.join(__dirname, "StadesterMetroReconciler.js"))) ?
        path.join(__dirname, "StadesterMetroReconciler.js") :
        path.resolve(process.cwd(), "histmap/2.data_cleaning/population_Stadester/StadesterMetroReconciler.js");
      MetroRec = require(rec_p).StadesterMetroReconciler;
    }
    let reconciler = new MetroRec({ use_trailing_carry: true });
    let recon_res = reconciler.reconcile(stadester_obj);
    if (recon_res && recon_res.stats && recon_res.stats.metros_inspected > 0) {
      console.log(
        `- [StadesterMetroReconciler] Reconciled ${recon_res.stats.metros_inspected} metro(s): ` +
        `${recon_res.stats.reconciled_positive_pairs} positive-residual, ${recon_res.stats.reconciled_negative_pairs} negative-residual ` +
        `(${recon_res.stats.removed_metro_year_points} metro year-points removed, ${recon_res.stats.absorbed_metros_removed} absorbed shells pruned, ` +
        `max conservation err=${recon_res.stats.max_conservation_err.toFixed(2)}).`
      );
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

      let is_agg = (city.population_scope === "city_proper" || city.population_scope === "suburb") ? "city" :
        ((city.population_scope === "metro" || city.extent_type === "metro" || city.is_agglomeration || (city.name && (city.name.toLowerCase().includes("agglomeration") || city.name.toLowerCase().includes("(metro)") || city.name.toLowerCase().includes("greater")))) ? "agg" : "city");
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
            let is_same_viscount_proj = Boolean(
              leader_city.viscount_project &&
              candidate_city.viscount_project &&
              leader_city.viscount_project === candidate_city.viscount_project
            );
            let is_temporally_compatible = true;
            if (!is_same_viscount_proj && lead_yrs.length > 0 && cand_yrs.length > 0) {
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
    let preta_countries = new Set(["Bolivia", "Brazil", "Paraguay", "Guyana", "Suriname", "French Guiana", "Colombia", "Peru", "Ecuador"]);
    let agglom_keys = Object.keys(stadester_obj).filter(function (arg0_k) {
      let c = stadester_obj[arg0_k];
      return c && /\(agglomeration\)/i.test(`${arg0_k} ${c.name || ""}`);
    });
    for (let i = 0; i < agglom_keys.length; i++) {
      let ak = agglom_keys[i];
      let ac = stadester_obj[ak];
      if (!ac) continue;
      let a_proj = String(ac.viscount_project || "").toUpperCase();
      if (!a_proj && preta_countries.has(String(ac.country || "").trim())) a_proj = "PRETA";
      if (!a_proj && typeof global.StadesterPartitionIO !== "undefined" && typeof global.StadesterPartitionIO.assignCityToViscountRegion === "function") {
        let rd = global.StadesterPartitionIO.assignCityToViscountRegion(ac, ak);
        if (rd && rd.key) a_proj = String(rd.key).toUpperCase();
      }
      if (a_proj !== "PRETA" && a_proj !== "CENTAUR" && a_proj !== "INDUS" && a_proj !== "CASTLE" && a_proj !== "JADE" && a_proj !== "SARAY" && a_proj !== "MANDALA" && a_proj !== "JAGUAR") continue;
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

      let norm_nm = String(city.name || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
      if (!by_country[ctry]) by_country[ctry] = [];
      by_country[ctry].push({
        active_ge1850: active_ge1850,
        city: city,
        dropped: false,
        key: key,
        norm_name: norm_nm,
        proj_key: proj_key,
        score: score
      });
    }

    let countries = Object.keys(by_country);

    for (let c = 0; c < countries.length; c++) {
      let arr = by_country[countries[c]];

      if (arr.length < 2) continue;
      arr.sort(function (arg0_a, arg1_b) { return arg1_b.score - arg0_a.score; });

      let grid = new Map();
      for (let i = 0; i < arr.length; i++) {
        let gx = Math.floor(arr[i].city.coords[0]*5);
        let gy = Math.floor(arr[i].city.coords[1]*5);
        let gk = `${gx},${gy}`;
        if (!grid.has(gk)) grid.set(gk, []);
        grid.get(gk).push(i);
      }

      for (let i = 0; i < arr.length; i++) {
        let a = arr[i];
        if (a.dropped) continue;
        let gx = Math.floor(a.city.coords[0]*5);
        let gy = Math.floor(a.city.coords[1]*5);

        for (let dx = -1; dx <= 1; dx++) {
          for (let dy = -1; dy <= 1; dy++) {
            let bucket = grid.get(`${gx + dx},${gy + dy}`);
            if (!bucket) continue;
            for (let bi = 0; bi < bucket.length; bi++) {
              let x = bucket[bi];
              if (x <= i) continue;
              let b = arr[x];
              if (b.dropped) continue;
              let touches_viscount = (
                a.proj_key === "CENTAUR" || b.proj_key === "CENTAUR" ||
                a.proj_key === "PRETA" || b.proj_key === "PRETA" ||
                a.proj_key === "INDUS" || b.proj_key === "INDUS" ||
                a.proj_key === "CASTLE" || b.proj_key === "CASTLE" ||
                a.proj_key === "JADE" || b.proj_key === "JADE" ||
                a.proj_key === "SARAY" || b.proj_key === "SARAY" ||
                a.proj_key === "MANDALA" || b.proj_key === "MANDALA" ||
                a.proj_key === "JAGUAR" || b.proj_key === "JAGUAR"
              );

              if (!touches_viscount) continue;
              let same_exact_name = Boolean(a.norm_name && a.norm_name === b.norm_name);
              if (!same_exact_name) continue;
              let max_lat_d = 0.16;
              let max_lng_d = 0.20;
              if (Math.abs(a.city.coords[0] - b.city.coords[0]) > max_lat_d || Math.abs(a.city.coords[1] - b.city.coords[1]) > max_lng_d) continue;
              let max_twin_km = 15.0;
              let overlaps = false;

              b.active_ge1850.forEach(function (arg0_yr) {
                if (a.active_ge1850.has(arg0_yr)) overlaps = true;
              });
              if (!overlaps) continue;
              if (haversineKm(a.city.coords, b.city.coords) > max_twin_km) continue;

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
                  if (Number.isFinite(yi) && Number.isFinite(Number(a.city.foundation_year)) && yi < Number(a.city.foundation_year))
                    delete a.city.foundation_year;
                }
              }
              population_Stadester_uud.appendCitySources(a.city, b.city.sources || b.city.type);
              delete stadester_obj[b.key];
              b.dropped = true;
              merged_count++;
            }
          }
        }
      }
    }
    if (merged_count > 0)
      console.log(`- Reconciled ${merged_count} close same-country CENTAUR twin record(s).`);

    //JAGUAR: Reconcile same-country/same-stem historical-to-modern variant duplicates (<= 25 km for variant spellings / suffixes, <= 5 km for identical names)
    let jaguar_by_country = {};
    let jaguar_keys = Object.keys(stadester_obj);
    let jaguar_merged = 0;
    let jaguar_suffixes = [
      "Puerto Rico", "Cuba", "Jamaica", "St. Lucia", "Saint Lucia", "Guadeloupe",
      "Martinique", "Barbados", "Cayman Islands", "Cayman", "Marie-Galante", "Dominica",
      "Barbuda", "Antigua", "Harbour Island", "The Bahamas", "Bahamas", "Sint Maarten",
      "St. Maarten", "Saint Martin", "Trinidad", "Tobago", "Grenada", "St. Vincent",
      "St. Kitts", "Nevis", "Montserrat", "Aruba", "Curaçao", "Curacao", "Bonaire",
      "Bermuda", "Haiti", "Nicaragua", "Costa Rica", "El Salvador", "Honduras",
      "Guatemala", "Belize", "Panama", "Dominican Republic", "Mexico"
    ];

    let normaliseJaguarStem = function (arg0_name, arg1_country) {
      let s = String(arg0_name || "").trim();

      s = s.replace(/^(.+?)\s*\(\s*(Le|La|Les|L'|El|Los|Las)\s*-\s*\)\s*$/i, "$2 $1");
      s = s.split(";")[0].split("(")[0].trim();

      let suffix_list = (arg1_country) ? [String(arg1_country).trim()].concat(jaguar_suffixes) : jaguar_suffixes;
      for (let si = 0; si < suffix_list.length; si++) {
        let suf = suffix_list[si];
        if (!suf) continue;
        let esc = suf.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        let re = new RegExp(`\\s+${esc}$`, "i");
        if (re.test(s)) {
          let stripped = s.replace(re, "").trim();
          if (stripped.length >= 3) {
            s = stripped;
            break;
          }
        }
      }

      let base = s.toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/ł/g, "l")
        .replace(/đ/g, "d")
        .replace(/ø/g, "o")
        .replace(/ß/g, "ss")
        .replace(/æ/g, "ae")
        .replace(/œ/g, "oe");
      base = base.replace(/^(?:st\.?|saint|san|santa|sao|al-|el-)\s+/i, "saint ");
      base = base.replace(/kh/g, "k");
      base = base.replace(/gh/g, "g");
      base = base.replace(/ph/g, "f");
      base = base.replace(/dj/g, "j");
      base = base.replace(/ou/g, "u");
      base = base.replace(/[jy]/g, "i");
      base = base.replace(/ts/g, "c");
      base = base.replace(/[cq]/g, "k");
      base = base.replace(/[^a-z0-9]+/g, "");

      return base;
    };

    for (let i = 0; i < jaguar_keys.length; i++) {
      let key = jaguar_keys[i];
      let city = stadester_obj[key];
      if (!city || !Array.isArray(city.coords) || city.coords.length < 2 || !city.population) continue;

      let proj_key = String(city.viscount_project || "").toUpperCase();
      if (!proj_key && typeof global.StadesterPartitionIO !== "undefined" && typeof global.StadesterPartitionIO.assignCityToViscountRegion === "function") {
        let reg_desc = global.StadesterPartitionIO.assignCityToViscountRegion(city, key);
        if (reg_desc && reg_desc.key) proj_key = String(reg_desc.key).toUpperCase();
      }
      if (proj_key !== "JAGUAR") continue;

      let country_str = String(city.country || "").trim();
      let ctry = country_str.toLowerCase();
      if (ctry === "netherlands antilles" || ctry === "saba" || ctry === "bonaire" || ctry === "sint eustatius")
        ctry = "caribbean netherlands";
      if (!ctry) continue;

      let is_metro = Boolean(
        city.population_scope === "metro" ||
        city.extent_type === "metro" ||
        city.is_agglomeration === true ||
        /\(metro\)|agglomeration|metropolitan/i.test(String(city.name || ""))
      );
      let max_pop = 0;
      let max_yr = -99999;
      let yr_keys = Object.keys(city.population);
      for (let x = 0; x < yr_keys.length; x++) {
        let yi = Number(yr_keys[x]);
        let pv = Number(city.population[yr_keys[x]]);
        if (Number.isFinite(yi) && Number.isFinite(pv) && pv > 0) {
          if (yi > max_yr) max_yr = yi;
          if (pv > max_pop) max_pop = pv;
        }
      }
      if (max_yr === -99999) continue;

      let display_nm = String(city.name || key).trim();
      let stem = normaliseJaguarStem(display_nm, country_str);
      if (!stem) continue;

      let raw_stem = normaliseJaguarStem(display_nm, "");
      let has_accent = /[^\x00-\x7F]/.test(display_nm);
      let has_country_suf = (stem !== raw_stem) || /\s+(?:Puerto Rico|Cuba|Jamaica|St\.\s*Lucia|Saint Lucia|Guadeloupe|Martinique|Barbados|Cayman|Marie-Galante|Dominica|Barbuda|Harbour Island|Sint Maarten|Nicaragua|Costa Rica|El Salvador|Honduras|Bonaire)$/i.test(display_nm);
      let is_dup_key = /_\d+$/.test(key);
      let is_inverted = /\(\s*(?:Le|La|Les|L'|El|Los|Las)\s*-\s*\)/i.test(display_nm);
      let score = (max_yr >= 1975 ? 1e11 : 0) +
        (population_Stadester_uud.hasCitySource(city, "JAGUAR") ? 5e10 : 0) +
        (has_country_suf ? -5e10 : 0) +
        (is_inverted ? -1e10 : 0) +
        (has_accent ? 2e10 : 0) +
        (is_dup_key ? -1e9 : 0) +
        max_pop;

      if (!jaguar_by_country[ctry]) jaguar_by_country[ctry] = [];
      jaguar_by_country[ctry].push({
        city: city,
        dropped: false,
        is_metro: is_metro,
        key: key,
        name: display_nm,
        score: score,
        stem: stem
      });
    }

    let jaguar_countries = Object.keys(jaguar_by_country);
    for (let c = 0; c < jaguar_countries.length; c++) {
      let arr = jaguar_by_country[jaguar_countries[c]];
      if (arr.length < 2) continue;
      arr.sort(function (arg0_a, arg1_b) { return arg1_b.score - arg0_a.score; });

      let by_stem = new Map();
      for (let i = 0; i < arr.length; i++) {
        let sk = `${arr[i].stem}|${arr[i].is_metro ? "m" : "c"}`;
        if (!by_stem.has(sk)) by_stem.set(sk, []);
        by_stem.get(sk).push(arr[i]);
      }

      by_stem.forEach(function (arg0_group) {
        if (arg0_group.length < 2) return;
        for (let i = 0; i < arg0_group.length; i++) {
          let a = arg0_group[i];
          if (a.dropped) continue;
          for (let x = i + 1; x < arg0_group.length; x++) {
            let b = arg0_group[x];
            if (b.dropped) continue;
            if (Math.abs(a.city.coords[0] - b.city.coords[0]) > 0.25 || Math.abs(a.city.coords[1] - b.city.coords[1]) > 0.45) continue;
            let d_km = haversineKm(a.city.coords, b.city.coords);
            let max_d_km = (a.name.toLowerCase() !== b.name.toLowerCase()) ? 25.0 : 5.0;
            if (d_km > max_d_km) continue;

            if (!Array.isArray(a.city.other_names)) a.city.other_names = [];
            if (b.city.name && b.city.name !== a.city.name && !a.city.other_names.includes(b.city.name))
              a.city.other_names.push(b.city.name);
            if (Array.isArray(b.city.other_names)) {
              for (let k = 0; k < b.city.other_names.length; k++)
                if (b.city.other_names[k] && b.city.other_names[k] !== a.city.name && !a.city.other_names.includes(b.city.other_names[k]))
                  a.city.other_names.push(b.city.other_names[k]);
            }

            let b_yrs = Object.keys(b.city.population);
            for (let y = 0; y < b_yrs.length; y++) {
              let yk = b_yrs[y];
              let yv = Number(b.city.population[yk]);
              let yi = Number(yk);
              if (Number.isFinite(yv) && yv > 0 && !(Number(a.city.population[yk]) > 0)) {
                a.city.population[yk] = yv;
                if (Number.isFinite(yi) && Number.isFinite(Number(a.city.foundation_year)) && yi < Number(a.city.foundation_year))
                  delete a.city.foundation_year;
                if (Number.isFinite(yi) && Number.isFinite(Number(a.city["found.yr"])) && yi < Number(a.city["found.yr"]))
                  delete a.city["found.yr"];
              }
            }

            if (Number.isFinite(b.city._raw_min_year)) {
              a.city._raw_min_year = Number.isFinite(a.city._raw_min_year) ?
                Math.min(a.city._raw_min_year, b.city._raw_min_year) : b.city._raw_min_year;
            }
            if (Number.isFinite(b.city._raw_max_year)) {
              a.city._raw_max_year = Number.isFinite(a.city._raw_max_year) ?
                Math.max(a.city._raw_max_year, b.city._raw_max_year) : b.city._raw_max_year;
            }

            population_Stadester_uud.appendCitySources(a.city, b.city.sources || b.city.type);
            delete stadester_obj[b.key];
            b.dropped = true;
            jaguar_merged++;
          }
        }
      });
    }
    if (jaguar_merged > 0)
      console.log(`- Reconciled ${jaguar_merged} JAGUAR same-country same-stem variant/twin record(s).`);

    //Return statement
    return stadester_obj;
  };

  /**
   * Flattens intra-municipal subdivisions up to top-level municipalities (capital status overriding largest population),
   * repairs Riga/Valletta/Naples/Athens coordinate/aggregation defects, strips statistical boundaries, and normalises name casing/haceks.
   * @alias population_Stadester_uud.flattenToMunicipalityLevelAndCleanNames
   *
   * @param {Object} arg0_stadester_obj
   *
   * @returns {Object}
   */
  population_Stadester_uud.flattenToMunicipalityLevelAndCleanNames = function (arg0_stadester_obj) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;

    //Guard clauses
    if (!stadester_obj || typeof stadester_obj !== "object") return stadester_obj;

    //Declare local instance variables
    let collapsed_count = 0;
    let dropped_junk = 0;
    let normaliser = global.stadester_name_normaliser || null;
    let renamed_count = 0;

    if (!normaliser) {
      let norm_path = path.join(__dirname, "stadester_name_normaliser.js");
      if (fs.existsSync(norm_path))
        normaliser = require(norm_path).stadester_name_normaliser;
    }

    //Function body
    // 1. Repair explicit coordinate/aggregation defects (Riga [56.95, 21.1] typo, Greater Valletta, Naples centroid)
    let all_keys_pre = Object.keys(stadester_obj);
    let has_proper_valletta = false;
    for (let i = 0; i < all_keys_pre.length; i++) {
      let c = stadester_obj[all_keys_pre[i]];
      if (!c || !Array.isArray(c.coords)) continue;
      let nm_low = String(c.name || "").trim().toLowerCase();
      let ctry_low = normaliser ? normaliser.normaliseCountryName(c.country) : String(c.country || "").trim().toLowerCase();
      if (ctry_low === "latvia" && nm_low === "riga" && Math.abs(Number(c.coords[1]) - 21.1) < 0.2) {
        c.coords = [56.946, 24.10589];
      } else if (ctry_low === "malta" && nm_low === "valletta" && Math.abs(Number(c.coords[0]) - 35.89924) < 0.05) {
        has_proper_valletta = true;
        c.coords = [35.89924, 14.5141];
        c.is_capital = true;
        c.population = {
          1580: 4000, 1600: 10000, 1650: 15000, 1700: 18000, 1750: 21000,
          1800: 23000, 1851: 24500, 1901: 22768, 1911: 24423, 1921: 22392,
          1931: 22779, 1948: 18666, 1957: 18202, 1967: 15279, 1985: 9340,
          1995: 7184, 2005: 6315, 2011: 6444, 2021: 5157, 2025: 5157
        };
        c.sources = ["manual", "MAGNETIC"];
      } else if (ctry_low === "italy" && (nm_low === "napoli" || nm_low === "naples") && Number(c.coords[0]) > 40.89 && Number(c.coords[1]) < 14.23) {
        c.coords = [40.85177, 14.26812];
        c.name = "Naples";
        c.is_capital = true;
      } else if (ctry_low === "south africa" && (nm_low === "johannesburg" || nm_low === "pretoria")) {
        c.population_scope = "city_proper";
        delete c.extent_type;
        delete c.is_agglomeration;
        if (c.population && typeof c.population === "object") {
          let p2011 = Number(c.population[2011] || 0);
          if (p2011 > 0 && !(Number(c.population[2025] || 0) > 0))
            c.population[2025] = Math.round(p2011*1.25);
          if (nm_low === "johannesburg" && Number(c.population[2025] || 0) < 1000000) {
            c.population[2000] = Math.max(Number(c.population[2000] || 0), 3225810);
            c.population[2011] = Math.max(Number(c.population[2011] || 0), 4434827);
            c.population[2020] = Math.max(Number(c.population[2020] || 0), 5635127);
            c.population[2025] = 5926668;
          }
        }
      }
    }

    if (!has_proper_valletta) {
      let val_rec = {
        coords: [35.89924, 14.5141],
        country: "Malta",
        "found.yr": 1566,
        foundation_year: 1566,
        is_capital: true,
        key: "Valletta-Malta",
        name: "Valletta",
        other_names: ["La Vallette", "Il-Belt Valletta"],
        population: {
          1580: 4000, 1600: 10000, 1650: 15000, 1700: 18000, 1750: 21000,
          1800: 23000, 1851: 24500, 1901: 22768, 1911: 24423, 1921: 22392,
          1931: 22779, 1948: 18666, 1957: 18202, 1967: 15279, 1985: 9340,
          1995: 7184, 2005: 6315, 2011: 6444, 2021: 5157, 2025: 5157
        },
        sources: ["manual", "MAGNETIC"],
        viscount_project: "MAGNETIC",
        viscount_z_priority: 10
      };
      stadester_obj["Valletta-Malta"] = val_rec;
    }

    for (let i = 0; i < all_keys_pre.length; i++) {
      let k = all_keys_pre[i];
      let c = stadester_obj[k];
      if (!c) continue;
      if (String(c.country || "").trim().toLowerCase() === "malta" && /^greater valletta$/i.test(String(c.name || "").trim())) {
        delete stadester_obj[k];
        dropped_junk++;
      }
    }

    // 2. Clean names, drop non-habitation junk/survey codes, and resolve intra-municipal parents
    let all_keys = Object.keys(stadester_obj);
    let parent_index = new Map();

    for (let i = 0; i < all_keys.length; i++) {
      let k = all_keys[i];
      let c = stadester_obj[k];
      if (!c || !c.name) continue;

      if (/\\[^\\]+\\/.test(String(c.name))) {
        delete stadester_obj[k];
        dropped_junk++;
        continue;
      }
      let stripped_lead = String(c.name).replace(/^[`"']+/, "").trim();
      if (stripped_lead && stripped_lead !== c.name) c.name = stripped_lead;
      if (/^weisbaden$/i.test(String(c.name || "").trim())) {
        c.name = "Wiesbaden";
        if (c.population) {
          let wb_yrs = Object.keys(c.population);
          for (let wy = 0; wy < wb_yrs.length; wy++) {
            let wyn = parseInt(wb_yrs[wy], 10);
            if (Number.isFinite(wyn) && wyn <= 1850 && Number(c.population[wb_yrs[wy]]) > 25000)
              delete c.population[wb_yrs[wy]];
          }
        }
      }
      if (/^(?:katowice|kattowitz)$/i.test(String(c.name || "").trim()) && c.population) {
        let kw_yrs = Object.keys(c.population);
        for (let ky = 0; ky < kw_yrs.length; ky++) {
          let kyn = parseInt(kw_yrs[ky], 10);
          if (Number.isFinite(kyn) && kyn < 1865 && Number(c.population[kw_yrs[ky]]) > 1500)
            delete c.population[kw_yrs[ky]];
        }
      }
      if (/^chemnitz$/i.test(String(c.name || "").trim()) && c.population) {
        let cm_yrs = Object.keys(c.population);
        for (let cy = 0; cy < cm_yrs.length; cy++) {
          let cyn = parseInt(cm_yrs[cy], 10);
          if (Number.isFinite(cyn) && cyn < 1830 && Number(c.population[cm_yrs[cy]]) > 20000)
            delete c.population[cm_yrs[cy]];
        }
      }
      if (/^frankenthal$/i.test(String(c.name || "").trim()) && c.population) {
        let fk_yrs = Object.keys(c.population);
        for (let fy = 0; fy < fk_yrs.length; fy++) {
          let fyn = parseInt(fk_yrs[fy], 10);
          if (Number.isFinite(fyn) && fyn < 1850 && Number(c.population[fk_yrs[fy]]) > 15000)
            delete c.population[fk_yrs[fy]];
        }
      }

      if (normaliser && normaliser.isJunkOrSurveyCode(c.name)) {
        delete stadester_obj[k];
        dropped_junk++;
        continue;
      }

      if (/^austria and czechoslovakia$/i.test(String(c.country || "").trim()) && Array.isArray(c.coords)) {
        c.country = (Number(c.coords[0]) >= 48.9) ? "Czech Republic" : "Austria";
      }

      // SC-04: Enforce documented abandonment ceilings on ancient ruins
      let ruin_max_year = null;
      let nm_low_sc = String(c.name || "").trim().toLowerCase();
      if (nm_low_sc === "seleucia on the tigris") ruin_max_year = 300;
      else if (nm_low_sc === "simurrum") ruin_max_year = -1500;
      else if (nm_low_sc === "deru") ruin_max_year = 600;
      else if (nm_low_sc === "wāsiṭ" || nm_low_sc === "wasit") ruin_max_year = 1600;
      else if (nm_low_sc === "pandu rajar dhibi") ruin_max_year = -500;
      if (ruin_max_year !== null && c.population && typeof c.population === "object") {
        let r_yrs = Object.keys(c.population);
        for (let ry = 0; ry < r_yrs.length; ry++) {
          let ryn = parseInt(r_yrs[ry], 10);
          if (Number.isFinite(ryn) && ryn > ruin_max_year) delete c.population[r_yrs[ry]];
        }
      }

      // SC-05: Enforce documented colonial/modern foundation floors (prevent 1400 AD backprojection)
      let col_min_year = null;
      if (nm_low_sc === "canning" && /india/i.test(String(c.country || ""))) col_min_year = 1858;
      else if (/^char\s*fasson$/i.test(nm_low_sc)) col_min_year = 1885;
      else if (nm_low_sc === "berhampore" || nm_low_sc === "baharampur") col_min_year = 1757;
      else if (nm_low_sc === "bakerganj") col_min_year = 1741;
      else if (nm_low_sc === "english bazar") col_min_year = 1680;
      if (col_min_year !== null && c.population && typeof c.population === "object") {
        let c_yrs = Object.keys(c.population);
        for (let cy = 0; cy < c_yrs.length; cy++) {
          let cyn = parseInt(c_yrs[cy], 10);
          if (Number.isFinite(cyn) && cyn < col_min_year) delete c.population[c_yrs[cy]];
        }
      }

      if (normaliser) {
        let norm_res = normaliser.normaliseCityName(c.name, c.country);
        if (norm_res.name && norm_res.name !== c.name) {
          if (!Array.isArray(c.other_names)) c.other_names = [];
          if (!c.other_names.includes(c.name) && !/`|^[A-Z\s]{4,}$|^[a-z\s]{4,}$/.test(c.name))
            c.other_names.push(c.name);
          for (let a = 0; a < norm_res.extra_aliases.length; a++)
            if (!c.other_names.includes(norm_res.extra_aliases[a]))
              c.other_names.push(norm_res.extra_aliases[a]);
          c.name = norm_res.name;
          renamed_count++;
        }
        let parent_floor = (typeof normaliser.resolveAmalgamationParentFloor === "function") ?
          normaliser.resolveAmalgamationParentFloor(c.name, c.country) : null;
        if (Number.isFinite(parent_floor) && c.population && typeof c.population === "object") {
          let p_yrs = Object.keys(c.population);
          let kept_any = false;
          for (let py = 0; py < p_yrs.length; py++) {
            let yn = parseInt(p_yrs[py], 10);
            if (Number.isFinite(yn) && yn < parent_floor) {
              delete c.population[p_yrs[py]];
            } else if (Number.isFinite(yn) && Number(c.population[p_yrs[py]]) > 0) {
              kept_any = true;
            }
          }
          if (!kept_any) {
            delete stadester_obj[k];
            continue;
          }
          if (Number.isFinite(Number(c.foundation_year)) && Number(c.foundation_year) < parent_floor)
            c.foundation_year = parent_floor;
          if (Number.isFinite(Number(c["found.yr"])) && Number(c["found.yr"]) < parent_floor)
            c["found.yr"] = parent_floor;
        }
        if (Number.isFinite(c._annexation_year) && c.population && typeof c.population === "object") {
          let t_annex = Number(c._annexation_year);
          let a_yrs = Object.keys(c.population);
          let kept_pre = false;
          for (let ay = 0; ay < a_yrs.length; ay++) {
            let yn = parseInt(a_yrs[ay], 10);
            if (Number.isFinite(yn) && yn >= t_annex) {
              delete c.population[a_yrs[ay]];
            } else if (Number.isFinite(yn) && Number(c.population[a_yrs[ay]]) > 0) {
              kept_pre = true;
            }
          }
          if (!kept_pre) {
            delete stadester_obj[k];
            continue;
          }
        }
      }

      let ctry_low = normaliser ? normaliser.normaliseCountryName(c.country) : String(c.country || "").trim().toLowerCase();
      let nm_fold = normaliser ? normaliser.foldAscii(c.name) : String(c.name || "").trim().toLowerCase();
      let idx_key = `${ctry_low}|${nm_fold}`;
      if (!parent_index.has(idx_key)) parent_index.set(idx_key, []);
      parent_index.get(idx_key).push(k);
    }

    // Helper to merge child into parent without double-counting metro totals
    let mergeIntoParent = function (arg0_parent_key, arg1_child_key, arg2_parent_meta) {
      let p_city = stadester_obj[arg0_parent_key];
      let c_city = stadester_obj[arg1_child_key];
      if (!p_city || !c_city || arg0_parent_key === arg1_child_key) return false;

      if (!Array.isArray(p_city.other_names)) p_city.other_names = [];
      if (c_city.name && c_city.name !== p_city.name && !p_city.other_names.includes(c_city.name))
        p_city.other_names.push(c_city.name);
      if (Array.isArray(c_city.other_names)) {
        for (let a = 0; a < c_city.other_names.length; a++)
          if (c_city.other_names[a] && c_city.other_names[a] !== p_city.name && !p_city.other_names.includes(c_city.other_names[a]))
            p_city.other_names.push(c_city.other_names[a]);
      }

      if (!p_city.population) p_city.population = {};
      let p_floor = (normaliser && typeof normaliser.resolveAmalgamationParentFloor === "function") ?
        normaliser.resolveAmalgamationParentFloor(p_city.name, p_city.country) : null;
      let c_yrs = Object.keys(c_city.population || {});
      for (let y = 0; y < c_yrs.length; y++) {
        let yk = c_yrs[y];
        let yn = parseInt(yk, 10);
        if (Number.isFinite(p_floor) && Number.isFinite(yn) && yn < p_floor) continue;
        let cv = Number(c_city.population[yk] || 0);
        let pv = Number(p_city.population[yk] || 0);
        if (cv > pv) p_city.population[yk] = cv;
      }

      if (arg2_parent_meta && arg2_parent_meta.is_capital_override)
        p_city.is_capital = true;
      if (arg2_parent_meta && Array.isArray(arg2_parent_meta.parent_coords))
        p_city.coords = arg2_parent_meta.parent_coords.slice();
      if (c_city.is_capital) p_city.is_capital = true;

      if (typeof population_Stadester_uud.appendCitySources === "function")
        population_Stadester_uud.appendCitySources(p_city, c_city.sources || c_city.type);

      delete stadester_obj[arg1_child_key];
      collapsed_count++;
      return true;
    };

    // 3. Consolidate intra-municipal districts into top-level municipalities
    let keys_after_clean = Object.keys(stadester_obj);
    for (let i = 0; i < keys_after_clean.length; i++) {
      let k = keys_after_clean[i];
      let c = stadester_obj[k];
      if (!c || !normaliser) continue;
      if (Number.isFinite(c._annexation_year) && !normaliser.resolveParentMunicipality(c.name, c.country, c.coords)) continue;

      let p_meta = normaliser.resolveParentMunicipality(c.name, c.country, c.coords);
      if (!p_meta) {
        let h_meta = normaliser.resolveHistoricalAmalgamation(c.name, c.country, c.coords);
        if (h_meta && Number.isFinite(h_meta.annexation_year) && c.population) {
          let h_yrs = Object.keys(c.population).map(Number).filter(function (arg0_n) { return Number.isFinite(arg0_n) && Number(c.population[arg0_n]) > 0; });
          let h_min = (h_yrs.length > 0) ? Math.min.apply(null, h_yrs) : Infinity;
          let h_max = (h_yrs.length > 0) ? Math.max.apply(null, h_yrs) : -Infinity;
          if (h_min >= h_meta.annexation_year && h_max >= h_meta.annexation_year) {
            p_meta = {
              effective_from_year: h_meta.annexation_year,
              is_capital_override: Boolean(h_meta.parent_is_capital),
              parent_coords: h_meta.parent_coords,
              parent_name: h_meta.parent_name
            };
          }
        }
      }
      if (!p_meta) continue;
      if (Number.isFinite(p_meta.effective_from_year) && c.population) {
        let local_max_yr = -Infinity;
        let pop_keys = Object.keys(c.population);
        for (let z = 0; z < pop_keys.length; z++) {
          let yr_num = parseInt(pop_keys[z], 10);
          if (Number.isFinite(yr_num) && Number(c.population[pop_keys[z]]) > 0 && yr_num > local_max_yr)
            local_max_yr = yr_num;
        }
        if (local_max_yr > -Infinity && local_max_yr < p_meta.effective_from_year) continue;
      }

      let ctry_low = normaliser ? normaliser.normaliseCountryName(c.country) : String(c.country || "").trim().toLowerCase();
      let target_fold = normaliser.foldAscii(p_meta.parent_name);
      let cands = parent_index.get(`${ctry_low}|${target_fold}`) || [];
      let best_parent = null;
      let best_score = -Infinity;

      for (let x = 0; x < cands.length; x++) {
        let pk = cands[x];
        if (!stadester_obj[pk] || pk === k) continue;
        let pc = stadester_obj[pk];
        let peak = (typeof population_Stadester_uud.getPeakPopulation === "function") ?
          population_Stadester_uud.getPeakPopulation(pc.population) : 0;
        let sc = (pc.is_capital ? 1e12 : 0) + peak;
        if (sc > best_score) {
          best_score = sc;
          best_parent = pk;
        }
      }

      if (best_parent) {
        mergeIntoParent(best_parent, k, p_meta);
      } else {
        c.name = p_meta.parent_name;
        if (p_meta.is_capital_override) c.is_capital = true;
        if (Array.isArray(p_meta.parent_coords)) c.coords = p_meta.parent_coords.slice();
        if (!parent_index.has(`${ctry_low}|${target_fold}`))
          parent_index.set(`${ctry_low}|${target_fold}`, [k]);
      }
    }

    // 4. Final same-country semantic/exonym deduplication within 15 km (catches Riga, Warsaw, Naples, Sofia, Kėdainiai, etc.)
    let audit_mod_path = path.resolve(__dirname, "../../../.agents/skills/population-regional-study/scripts/viscount_entity_and_continuity_audit.js");
    let entity_audit = fs.existsSync(audit_mod_path) ? require(audit_mod_path).viscount_entity_audit : null;
    let profiles = entity_audit ? entity_audit.loadSkillProfiles() : null;
    let token_index = new Map();
    let final_keys = Object.keys(stadester_obj);
    let score_map = new Map();

    for (let i = 0; i < final_keys.length; i++) {
      let fk = final_keys[i];
      let fc = stadester_obj[fk];
      let sc = (fc && fc.is_capital ? 1e12 : 0) + ((typeof population_Stadester_uud.getPeakPopulation === "function" && fc) ? population_Stadester_uud.getPeakPopulation(fc.population) : 0);
      score_map.set(fk, sc);
    }

    final_keys.sort(function (arg0_a, arg1_b) {
      return score_map.get(arg1_b) - score_map.get(arg0_a);
    });

    for (let i = 0; i < final_keys.length; i++) {
      let k = final_keys[i];
      let c = stadester_obj[k];
      if (!c || !Array.isArray(c.coords) || c.coords.length < 2) continue;
      let lat = Number(c.coords[0]);
      let lng = Number(c.coords[1]);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;

      if (typeof population_Stadester_uud.assignMunicipalMetadata === "function")
        population_Stadester_uud.assignMunicipalMetadata(c);
      let cand_tokens = (typeof population_Stadester_uud.getCityMatchTokens === "function") ?
        population_Stadester_uud.getCityMatchTokens(c) : [];
      let candidate_pool = [];
      let seen_pool = new Set();
      for (let t = 0; t < cand_tokens.length; t++) {
        let hits = token_index.get(cand_tokens[t]);
        if (!hits) continue;
        for (let h = 0; h < hits.length; h++) {
          if (!seen_pool.has(hits[h])) {
            seen_pool.add(hits[h]);
            candidate_pool.push(hits[h]);
          }
        }
      }

      let dup_parent = null;
      for (let b = 0; b < candidate_pool.length; b++) {
        let pk = candidate_pool[b];
        let pc = stadester_obj[pk];
        if (!pc) continue;
        let pc_ctry = normaliser ? normaliser.normaliseCountryName(pc.country) : String(pc.country || "").toLowerCase();
        let c_ctry = normaliser ? normaliser.normaliseCountryName(c.country) : String(c.country || "").toLowerCase();
        if (pc_ctry !== c_ctry) continue;
        let d_km = (typeof population_Stadester_uud.haversineDistance === "function") ?
          population_Stadester_uud.haversineDistance(pc.coords, c.coords) : 999999;
        let same_folded_name = Boolean(
          normaliser &&
          normaliser.foldAscii(pc.name) &&
          normaliser.foldAscii(pc.name) === normaliser.foldAscii(c.name)
        );
        let max_d_km = same_folded_name ? 30.0 : 15.0;
        if (d_km > max_d_km) continue;
        let is_agg_pc = Boolean(pc.population_scope === "metro" || pc.extent_type === "metro" || pc.is_agglomeration);
        let is_agg_c = Boolean(c.population_scope === "metro" || c.extent_type === "metro" || c.is_agglomeration);
        if (same_folded_name && (is_agg_pc !== is_agg_c)) {
          if (is_agg_c && !pc.metro_population) {
            pc.metro_population = JSON.parse(JSON.stringify(c.population || {}));
          } else if (is_agg_pc && !is_agg_c) {
            let c_post50 = 0;
            if (c.population) {
              let c_yks = Object.keys(c.population);
              for (let yy = 0; yy < c_yks.length; yy++) {
                let yyn = parseInt(c_yks[yy], 10);
                if (Number.isFinite(yyn) && yyn >= 1950 && Number(c.population[c_yks[yy]]) > 0) c_post50++;
              }
            }
            if (c_post50 >= 2) {
              if (!pc.metro_population) pc.metro_population = JSON.parse(JSON.stringify(pc.population || {}));
              pc.population = JSON.parse(JSON.stringify(c.population || {}));
            } else if (pc.population) {
              let p2011 = Number(pc.population[2011] || 0);
              if (p2011 > 0 && !(Number(pc.population[2025] || 0) > 0))
                pc.population[2025] = Math.round(p2011*1.25);
              if (/^johannesburg$/i.test(String(pc.name || "").trim()) && Number(pc.population[2025] || 0) < 1000000) {
                pc.population[2000] = Math.max(Number(pc.population[2000] || 0), 3225810);
                pc.population[2011] = Math.max(Number(pc.population[2011] || 0), 4434827);
                pc.population[2020] = Math.max(Number(pc.population[2020] || 0), 5635127);
                pc.population[2025] = 5926668;
              }
            }
            pc.population_scope = "city_proper";
            delete pc.extent_type;
            delete pc.is_agglomeration;
          }
          dup_parent = pk;
          break;
        }
        if (typeof population_Stadester_uud.canMergeMunicipalities === "function") {
          let gate = population_Stadester_uud.canMergeMunicipalities(pc, c, { max_semantic_km: max_d_km });
          if (!gate.allow) continue;
        } else {
          let is_match = (typeof population_Stadester_uud.checkExactNameMatch === "function") ?
            population_Stadester_uud.checkExactNameMatch(pc, c) : false;
          if (!is_match && entity_audit && profiles)
            is_match = entity_audit.areEquivalentExonyms(pc.name, c.name, profiles);
          if (!is_match) continue;
        }
        dup_parent = pk;
        break;
      }

      if (dup_parent) {
        mergeIntoParent(dup_parent, k, null);
        for (let t = 0; t < cand_tokens.length; t++) {
          let tok = cand_tokens[t];
          let list = token_index.get(tok);
          if (!list) {
            token_index.set(tok, [dup_parent]);
          } else if (!list.includes(dup_parent)) {
            list.push(dup_parent);
          }
        }
      } else {
        for (let t = 0; t < cand_tokens.length; t++) {
          let tok = cand_tokens[t];
          let list = token_index.get(tok);
          if (!list) {
            token_index.set(tok, [k]);
          } else {
            list.push(k);
          }
        }
      }
    }

    // 5. Cross-country historical sovereign-transfer deduplication (East Prussia, Kresy, Alsace, Pomerania/Silesia, etc.)
    let transfer_pairs = new Set([
      "germany|russia", "russia|germany",
      "germany|poland", "poland|germany",
      "germany|lithuania", "lithuania|germany",
      "poland|belarus", "belarus|poland",
      "poland|ukraine", "ukraine|poland",
      "poland|lithuania", "lithuania|poland",
      "austria|poland", "poland|austria",
      "austria|ukraine", "ukraine|austria",
      "austria|czechia", "czechia|austria",
      "hungary|slovakia", "slovakia|hungary",
      "hungary|romania", "romania|hungary",
      "romania|moldova", "moldova|romania",
      "romania|ukraine", "ukraine|romania",
      "russia|lithuania", "lithuania|russia",
      "russia|latvia", "latvia|russia",
      "russia|estonia", "estonia|russia",
      "russia|finland", "finland|russia",
      "russia|poland", "poland|russia",
      "russia|belarus", "belarus|russia",
      "russia|ukraine", "ukraine|russia",
      "germany|france", "france|germany",
      "germany|denmark", "denmark|germany",
      "italy|croatia", "croatia|italy",
      "italy|slovenia", "slovenia|italy"
    ]);
    let exonym_groups = [
      ["konigsberg", "kaliningrad", "krolewiec", "karaliaucius"],
      ["tilsit", "sovetsk"],
      ["insterburg", "chernyakhovsk", "cernjachovsk"],
      ["gumbinnen", "gusev"],
      ["pillau", "baltiysk", "baltiisk"],
      ["ragnit", "neman", "ragaine"],
      ["labiau", "polessk"],
      ["tapiau", "gvardeysk", "gvardeisk"],
      ["wehlau", "znamensk"],
      ["heiligenbeil", "mamonovo"],
      ["preussisch eylau", "pr eylau", "bagrationovsk"],
      ["stalluponen", "nesterov"],
      ["pillkallen", "dobrovolsk"],
      ["darkehmen", "ozersk", "ozyorsk"],
      ["friedland", "pravdinsk"],
      ["gerdauen", "zheleznodorozhny", "zheleznodorozhnyy"],
      ["allenburg", "druzhba"],
      ["domnau", "domnovo"],
      ["zinten", "kornevo"],
      ["cranz", "zelenogradsk"],
      ["rauschen", "svetlogorsk"],
      ["fischhausen", "primorsk"],
      ["palmnicken", "yantarnyy", "yantarny"],
      ["memel", "klaipeda"],
      ["heydekrug", "silute"],
      ["allenstein", "olsztyn"],
      ["braunsberg", "braniewo"],
      ["bartenstein", "bartoszyce"],
      ["heilsberg", "lidzbark warminski"],
      ["lyck", "elk"],
      ["lotzen", "gizycko"],
      ["rastenburg", "ketrzyn"],
      ["osterode", "ostroda"],
      ["lemberg", "lviv", "lwow", "lvov"],
      ["wilna", "vilnius", "vilna", "wilno"],
      ["kowno", "kaunas"],
      ["dunaburg", "daugavpils"],
      ["libau", "liepaja"],
      ["mitau", "jelgava"],
      ["brest-litovsk", "brest", "brzesc"],
      ["grodno", "hrodna"]
    ];
    let exonym_group_id = new Map();
    for (let gi = 0; gi < exonym_groups.length; gi++) {
      for (let gj = 0; gj < exonym_groups[gi].length; gj++)
        exonym_group_id.set(exonym_groups[gi][gj], gi);
    }
    let getMinMaxYr = function (arg0_pop) {
      let mn = Infinity;
      let mx = -Infinity;
      if (!arg0_pop || typeof arg0_pop !== "object") return [mn, mx];
      let yks = Object.keys(arg0_pop);
      for (let y = 0; y < yks.length; y++) {
        let yn = parseInt(yks[y], 10);
        if (Number.isFinite(yn) && Number(arg0_pop[yks[y]]) > 0) {
          if (yn < mn) mn = yn;
          if (yn > mx) mx = yn;
        }
      }
      return [mn, mx];
    };
    let transfer_grid = new Map();
    let t_keys = Object.keys(stadester_obj);
    for (let ti = 0; ti < t_keys.length; ti++) {
      let tk = t_keys[ti];
      let tc = stadester_obj[tk];
      if (!tc || !Array.isArray(tc.coords) || tc.coords.length < 2) continue;
      let la = Number(tc.coords[0]);
      let lo = Number(tc.coords[1]);
      if (!Number.isFinite(la) || !Number.isFinite(lo)) continue;
      let gkey = `${Math.floor(la*20)},${Math.floor(lo*20)}`;
      if (!transfer_grid.has(gkey)) transfer_grid.set(gkey, []);
      transfer_grid.get(gkey).push(tk);
    }
    for (let ti = 0; ti < t_keys.length; ti++) {
      let tk = t_keys[ti];
      let tc = stadester_obj[tk];
      if (!tc || !Array.isArray(tc.coords) || tc.coords.length < 2) continue;
      let tc_ctry = normaliser ? normaliser.normaliseCountryName(tc.country) : String(tc.country || "").toLowerCase();
      let tc_mm = getMinMaxYr(tc.population);
      let tc_fold = normaliser ? normaliser.foldAscii(tc.name) : String(tc.name || "").toLowerCase();
      let tc_gid = exonym_group_id.has(tc_fold) ? exonym_group_id.get(tc_fold) : -1;
      let la = Number(tc.coords[0]);
      let lo = Number(tc.coords[1]);
      let gx = Math.floor(la*20);
      let gy = Math.floor(lo*20);
      let cands_t = [];
      for (let dx = -1; dx <= 1; dx++) {
        for (let dy = -1; dy <= 1; dy++) {
          let arr = transfer_grid.get(`${gx + dx},${gy + dy}`);
          if (arr) {
            for (let ai = 0; ai < arr.length; ai++) cands_t.push(arr[ai]);
          }
        }
      }
      for (let ci = 0; ci < cands_t.length; ci++) {
        let pk = cands_t[ci];
        if (pk === tk || !stadester_obj[pk] || !stadester_obj[tk]) continue;
        let pc = stadester_obj[pk];
        let pc_ctry = normaliser ? normaliser.normaliseCountryName(pc.country) : String(pc.country || "").toLowerCase();
        if (pc_ctry === tc_ctry || !transfer_pairs.has(`${pc_ctry}|${tc_ctry}`)) continue;
        let d_km = (typeof population_Stadester_uud.haversineDistance === "function") ?
          population_Stadester_uud.haversineDistance(pc.coords, tc.coords) : 999999;
        if (d_km > 5.0) continue;
        let pc_mm = getMinMaxYr(pc.population);
        let pc_fold = normaliser ? normaliser.foldAscii(pc.name) : String(pc.name || "").toLowerCase();
        let pc_gid = exonym_group_id.has(pc_fold) ? exonym_group_id.get(pc_fold) : -2;
        let exonym_hit = (tc_gid >= 0 && tc_gid === pc_gid);
        let semantic_hit = exonym_hit || (
          typeof population_Stadester_uud.checkExactNameMatch === "function" &&
          population_Stadester_uud.checkExactNameMatch(pc, tc)
        );
        if (!semantic_hit) continue;
        let keep_tc = (tc_mm[1] > pc_mm[1]) || (tc_mm[1] === pc_mm[1] && String(tc.viscount_project || "") === "POLARIS");
        if (keep_tc) {
          mergeIntoParent(tk, pk, null);
        } else {
          mergeIntoParent(pk, tk, null);
          break;
        }
      }
    }

    // 6. Enforce canonical historic-centre coordinates (SC-11) and founding-year floors (SC-13/SC-15)
    try {
      let hc_path = require("path").join(__dirname, "config", "historic_city_centres.json5");
      if (require("fs").existsSync(hc_path)) {
        let j5 = global.JSON5 || require("json5");
        let hc_cfg = j5.parse(require("fs").readFileSync(hc_path, "utf8"));
        let hc_map = (hc_cfg && hc_cfg.centres) ? hc_cfg.centres : {};
        let hc_keys = Object.keys(hc_map);
        for (let hi = 0; hi < hc_keys.length; hi++) {
          let hk = hc_keys[hi];
          if (stadester_obj[hk] && Array.isArray(hc_map[hk]))
            stadester_obj[hk].coords = hc_map[hk].slice();
        }
      }
    } catch (e) {
      console.error("[stadester_uud_fixes] Failed to enforce historic_city_centres.json5:", e);
    }
    if (stadester_obj["City and County of the City of London-United Kingdom"])
      stadester_obj["City and County of the City of London-United Kingdom"].name = "City of London";

    let founding_floors = {
      "Mandalay-Myanmar": 1857,
      "Goiânia-Brazil": 1933,
      "Belterra-Brazil": 1934,
      "Marabá-Brazil": 1898,
      "Petrolina-Brazil": 1870,
      "Porto Nacional-Brazil": 1738,
      "Boa Vista-Brazil": 1830,
      "Alenquer-Brazil": 1758,
      "Almeirim-Brazil": 1758,
      "Borba-Brazil": 1756,
      "Lábrea-Brazil": 1871,
      "Alvorada-Brazil": 1965,
      "Mazagão Velho-Brazil": 1770,
      "São Miguel-Brazil": 1632,
      "Cartagena-Colombia": 1533,
      "Buenos Aires-Argentina": 1536,
      "Puerto Santander-Colombia": 1926,
      "La Pintada-Colombia": 1815
    };
    let ff_keys = Object.keys(founding_floors);
    for (let fi = 0; fi < ff_keys.length; fi++) {
      let fk = ff_keys[fi];
      let f_city = stadester_obj[fk];
      if (!f_city || !f_city.population) continue;
      let f_yr = founding_floors[fk];
      let p_keys = Object.keys(f_city.population);
      for (let pi = 0; pi < p_keys.length; pi++) {
        let py = parseInt(p_keys[pi], 10);
        if (Number.isFinite(py) && py < f_yr) delete f_city.population[p_keys[pi]];
      }
    }

    console.log(`- [MunicipalityFlattening] Renamed ${renamed_count}, collapsed ${collapsed_count} intra-municipal/duplicate entries, dropped ${dropped_junk} junk/survey entries.`);

    //Return statement
    return stadester_obj;
  };
}
