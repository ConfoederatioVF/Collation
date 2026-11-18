//Initialise functions
{
  let fs = global.fs || require("fs");
  let JSON5 = global.JSON5 || require("json5");
  let path = global.path || require("path");

  if (!global.fs) global.fs = fs;
  if (!global.path) global.path = path;
  if (!global.StadesterPartitionIO && typeof require !== "undefined") {
    try { require(path.join(__dirname, "StadesterPartitionIO.js")); } catch (e) {}
  }
  if ((!global.population_Stadester_uud || !global.population_Stadester_uud.checkExactNameMatch) && typeof require !== "undefined") {
    try { require(path.join(__dirname, "stadester_uud_sources.js")); } catch (e) {}
  }
  if ((!global.population_Stadester_uud || !global.population_Stadester_uud.haversineDistance) && typeof require !== "undefined") {
    try { require(path.join(__dirname, "stadester_uud.js")); } catch (e) {}
  }
  if ((!global.population_Stadester_uud || !global.population_Stadester_uud.appendCitySources) && typeof require !== "undefined") {
    try { require(path.join(__dirname, "stadester_uud_fixes.js")); } catch (e) {}
  }

  /**
   * Unified Operation Viscount settlement gazetteer loader and cross-frontier deduplicator.
   * Evaluates active Viscount regional projects in inverse (`z-index`) precedence order (`z_priority = order`:
   * `14` down to `1`) and within each project by internal source tier priority (`priority` descending), ensuring
   * higher-order borderland studies supersede lower-order ones on shared settlements whilst backfilling uncovered years.
   *
   * @class ViscountGazetteerLoader
   */
  global.ViscountGazetteerLoader = class {
    /**
     * Loads and deduplicates all active Viscount regional settlement gazetteers in descending `z_priority` (`14 -> 1`).
     * @alias ViscountGazetteerLoader.getViscountRegionalObject
     *
     * @param {Object} [arg0_options]
     *  @param {string} [arg0_options.config_path] - Optional override path for single-project manifest
     *  @param {string} [arg0_options.only_project] - Optional single Viscount project key filter (e.g. `"POLARIS"`)
     *  @param {string} [arg0_options.precedence_config_path] - Override path to `viscount_precedence.json5`
     *  @param {Array<string>} [arg0_options.project_keys] - Optional whitelist of Viscount project keys
     *  @param {string} [arg0_options.project_root] - SVEA repository root directory
     *
     * @returns {Object} Deduplicated settlement dictionary keyed cleanly for UUD merger
     */
    static getViscountRegionalObject (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let active_projects = [];
      let city_spatial_grid = new Map();
      let exact_coord_match_km = 2.5;
      let haversine_name_match_km = 15.0;
      let loaded_count_by_project = {};
      let return_obj = {};
      let root_dir = (options.project_root) ? options.project_root : ((fs.existsSync("./histmap/1.data_raw")) ?
        path.resolve(".") : path.resolve(__dirname, "../../.."));
      let spatial_step_deg = 0.5;
      let total_gazetteer_files = 0;

      //Function body
      active_projects = this.resolveActiveProjects(root_dir, options);
      if (active_projects.length === 0) {
        console.error("[ViscountGazetteerLoader] No active Viscount gazetteer manifests found on disk.");
        return {};
      }

      for (let i = 0; i < active_projects.length; i++) {
        let proj = active_projects[i];
        let manifest_path = (options.config_path && active_projects.length === 1) ?
          path.resolve(options.config_path) :
          path.resolve(root_dir, proj.gazetteer_manifest);

        if (!fs.existsSync(manifest_path)) continue;

        let manifest_obj;
        try {
          manifest_obj = JSON5.parse(fs.readFileSync(manifest_path, "utf8"));
        } catch (e) {
          console.error(`[ViscountGazetteerLoader] Failed to parse manifest ${manifest_path}:`, e);
          continue;
        }

        let proj_exact_km = exact_coord_match_km;
        let proj_name_km = haversine_name_match_km;
        let merge_opts = manifest_obj.merge_options || manifest_obj.deduplication;
        if (merge_opts) {
          if (Number.isFinite(merge_opts.exact_coord_match_km))
            proj_exact_km = merge_opts.exact_coord_match_km;
          if (Number.isFinite(merge_opts.haversine_name_match_km))
            proj_name_km = merge_opts.haversine_name_match_km;
        }

        let gazetteers = Array.isArray(manifest_obj.gazetteers) ?
          manifest_obj.gazetteers.slice().sort(function (arg0_a, arg1_b) {
            return (arg1_b.priority || 0) - (arg0_a.priority || 0);
          }) : [];

        loaded_count_by_project[proj.key] = 0;
        total_gazetteer_files += gazetteers.length;

        this.mergeProjectGazetteers(return_obj, city_spatial_grid, {
          exact_coord_match_km: proj_exact_km,
          gazetteers: gazetteers,
          haversine_name_match_km: proj_name_km,
          loaded_count_by_project: loaded_count_by_project,
          proj: proj,
          root_dir: root_dir,
          spatial_step_deg: spatial_step_deg
        });
      }

      //Harmonise standalone Ch. 1-3 pre-modern POLARIS entries so none terminate at a cliff right at 1900
      let uud_ref = global.population_Stadester_uud || {};
      let pol_keys = Object.keys(return_obj);
      for (let i = 0; i < pol_keys.length; i++) {
        let pk = pol_keys[i];
        let city = return_obj[pk];
        if (!city || city.viscount_project !== "POLARIS" || !(city.polaris_priority < 3) || !city.population)
          continue;
        let yrs = Object.keys(city.population).map(Number).filter(function (arg0_n) {
          return Number.isFinite(arg0_n) && Number(city.population[arg0_n]) > 0;
        }).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
        if (yrs.length === 0) continue;

        if (yrs[0] <= 1858) {
          for (let y = 0; y < yrs.length; y++)
            if (yrs[y] > 1858) delete city.population[yrs[y]];
        } else if (yrs[yrs.length - 1] <= 1900 && Array.isArray(city.coords) && city.coords.length >= 2) {
          let lat = Number(city.coords[0]);
          let lng = Number(city.coords[1]);
          let gx = Math.floor(lng/spatial_step_deg);
          let gy = Math.floor(lat/spatial_step_deg);
          let best_peer = null;
          let best_dist = 8.0;
          for (let dx = -1; dx <= 1; dx++) {
            for (let dy = -1; dy <= 1; dy++) {
              let bucket = city_spatial_grid.get(`${gx + dx},${gy + dy}`);
              if (!bucket) continue;
              for (let b = 0; b < bucket.length; b++) {
                let peer = return_obj[bucket[b]];
                if (!peer || peer === city || peer.viscount_project !== "POLARIS" || peer.polaris_priority !== 3)
                  continue;
                if (peer.country !== city.country) continue;
                let dist_km = (typeof uud_ref.haversineDistance === "function") ?
                  uud_ref.haversineDistance(city.coords, peer.coords) : 999999;
                if (dist_km <= best_dist) {
                  best_dist = dist_km;
                  best_peer = peer;
                }
              }
            }
          }
          if (best_peer) {
            if (!best_peer.population) best_peer.population = {};
            for (let y = 0; y < yrs.length; y++)
              if (yrs[y] < 1897 && best_peer.population[yrs[y]] === undefined)
                best_peer.population[yrs[y]] = city.population[yrs[y]];
            if (Array.isArray(city.other_names)) {
              if (!best_peer.other_names) best_peer.other_names = [];
              for (let on = 0; on < city.other_names.length; on++)
                if (city.other_names[on] && !best_peer.other_names.includes(city.other_names[on]))
                  best_peer.other_names.push(city.other_names[on]);
            }
            if (city.name && city.name !== best_peer.name && best_peer.other_names && !best_peer.other_names.includes(city.name))
              best_peer.other_names.push(city.name);
            delete return_obj[pk];
          } else {
            for (let y = 0; y < yrs.length; y++)
              if (yrs[y] > 1896) delete city.population[yrs[y]];
          }
        }
      }

      //Harmonise pre-modern/colonial Tier 1-2 CENTAUR entries into Tier 3 modern census anchors within 1.55 km
      let centaur_keys = Object.keys(return_obj);
      for (let i = 0; i < centaur_keys.length; i++) {
        let pk = centaur_keys[i];
        let city = return_obj[pk];
        if (!city || city.viscount_project !== "CENTAUR" || !((city.polaris_priority || 1) < 3) || !city.population)
          continue;
        if (!Array.isArray(city.coords) || city.coords.length < 2)
          continue;
        let yrs = Object.keys(city.population).map(Number).filter(function (arg0_n) {
          return Number.isFinite(arg0_n) && Number(city.population[arg0_n]) > 0;
        }).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
        if (yrs.length === 0) continue;

        let lat = Number(city.coords[0]);
        let lng = Number(city.coords[1]);
        let gx = Math.floor(lng/spatial_step_deg);
        let gy = Math.floor(lat/spatial_step_deg);
        let best_peer = null;
        let best_dist = 1.55;
        for (let dx = -1; dx <= 1; dx++) {
          for (let dy = -1; dy <= 1; dy++) {
            let bucket = city_spatial_grid.get(`${gx + dx},${gy + dy}`);
            if (!bucket) continue;
            for (let b = 0; b < bucket.length; b++) {
              let peer = return_obj[bucket[b]];
              if (!peer || peer === city || peer.viscount_project !== "CENTAUR" || peer.polaris_priority !== 3)
                continue;
              if (peer.country !== city.country) continue;
              let c_name_prim = (typeof uud_ref.processCityName === "function") ?
                uud_ref.processCityName(city.name) : String(city.name || "").toLowerCase();
              let p_name_prim = (typeof uud_ref.processCityName === "function") ?
                uud_ref.processCityName(peer.name) : String(peer.name || "").toLowerCase();
              if (
                (c_name_prim === "brooklyn" && (p_name_prim === "new york" || p_name_prim === "new york city")) ||
                (p_name_prim === "brooklyn" && (c_name_prim === "new york" || c_name_prim === "new york city"))
              ) {
                continue;
              }
              let dist_km = (typeof uud_ref.haversineDistance === "function") ?
                uud_ref.haversineDistance(city.coords, peer.coords) : 999999;
              if (dist_km <= best_dist) {
                best_dist = dist_km;
                best_peer = peer;
              }
            }
          }
        }
        if (best_peer) {
          if (!best_peer.population) best_peer.population = {};
          let peer_yrs = Object.keys(best_peer.population).map(Number).filter(function (arg0_n) {
            return Number.isFinite(arg0_n) && Number(best_peer.population[arg0_n]) > 0;
          }).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
          let peer_min_yr = (peer_yrs.length > 0) ? peer_yrs[0] : Infinity;
          for (let y = 0; y < yrs.length; y++)
            if (yrs[y] < peer_min_yr && best_peer.population[yrs[y]] === undefined)
              best_peer.population[yrs[y]] = city.population[yrs[y]];
          if (!best_peer.other_names) best_peer.other_names = [];
          if (city.name && city.name !== best_peer.name && !best_peer.other_names.includes(city.name))
            best_peer.other_names.push(city.name);
          if (Array.isArray(city.other_names)) {
            for (let on = 0; on < city.other_names.length; on++)
              if (city.other_names[on] && city.other_names[on] !== best_peer.name && !best_peer.other_names.includes(city.other_names[on]))
                best_peer.other_names.push(city.other_names[on]);
          }
          if (Array.isArray(city.original_names)) {
            if (!best_peer.original_names) best_peer.original_names = [];
            for (let orn = 0; orn < city.original_names.length; orn++)
              if (city.original_names[orn] && !best_peer.original_names.includes(city.original_names[orn]))
                best_peer.original_names.push(city.original_names[orn]);
          }
          delete return_obj[pk];
        }
      }

      let proj_summary = Object.keys(loaded_count_by_project)
        .map(function (arg0_k) { return `${arg0_k}: ${loaded_count_by_project[arg0_k]}`; })
        .join(", ");
      console.log(`- [ViscountGazetteerLoader] Loaded ${Object.keys(return_obj).length} deduplicated settlements from ${active_projects.length} Viscount project(s) / ${total_gazetteer_files} gazetteers (${proj_summary}).`);

      //Return statement
      return return_obj;
    }


    /**
     * Checks whether two settlements share compatible population scales before name-based spatial merging,
     * preventing small homonym villages from overwriting nearby cities.
     * @alias ViscountGazetteerLoader.hasCompatiblePopulationScale
     *
     * @param {Object} arg0_pop_a
     * @param {Object} arg1_pop_b
     *
     * @returns {boolean}
     */
    static hasCompatiblePopulationScale (arg0_pop_a, arg1_pop_b) {
      //Convert from parameters
      let pop_a = (arg0_pop_a && typeof arg0_pop_a === "object") ? arg0_pop_a : {};
      let pop_b = (arg1_pop_b && typeof arg1_pop_b === "object") ? arg1_pop_b : {};

      //Declare local instance variables
      let best_gap = Infinity;
      let best_pair = null;
      let yrs_a = Object.keys(pop_a).map(Number).filter(function (arg0_n) { return Number.isFinite(arg0_n) && Number(pop_a[arg0_n]) > 0; });
      let yrs_b = Object.keys(pop_b).map(Number).filter(function (arg0_n) { return Number.isFinite(arg0_n) && Number(pop_b[arg0_n]) > 0; });

      //Guard clauses
      if (yrs_a.length === 0 || yrs_b.length === 0) return true;

      //Function body
      for (let i = 0; i < yrs_a.length; i++) {
        for (let x = 0; x < yrs_b.length; x++) {
          let gap = Math.abs(yrs_a[i] - yrs_b[x]);
          if (gap < best_gap || (gap === best_gap && Math.max(yrs_a[i], yrs_b[x]) <= 2021)) {
            best_gap = gap;
            best_pair = [Number(pop_a[yrs_a[i]]), Number(pop_b[yrs_b[x]])];
          }
        }
      }

      if (best_pair && best_gap <= 30) {
        let p_big = Math.max(best_pair[0], best_pair[1]);
        let p_small = Math.max(1, Math.min(best_pair[0], best_pair[1]));
        if (p_big >= 5000 && (p_big/p_small) > 5.0)
          return false;
      }

      //Return statement
      return true;
    }


    /**
     * Merges all sorted gazetteer files for a single Viscount project into `arg0_return_obj` using a spatial index.
     * @alias ViscountGazetteerLoader.mergeProjectGazetteers
     *
     * @param {Object} arg0_return_obj
     * @param {Map} arg1_spatial_grid
     * @param {Object} arg2_options
     */
    static mergeProjectGazetteers (arg0_return_obj, arg1_spatial_grid, arg2_options) {
      //Convert from parameters
      let return_obj = arg0_return_obj;
      let spatial_grid = arg1_spatial_grid;
      let options = (arg2_options) ? arg2_options : {};

      //Declare local instance variables
      let exact_coord_match_km = options.exact_coord_match_km || 2.5;
      let gazetteers = options.gazetteers || [];
      let haversine_name_match_km = options.haversine_name_match_km || 15.0;
      let loaded_counts = options.loaded_count_by_project || {};
      let proj = options.proj;
      let root_dir = options.root_dir;
      let spatial_step_deg = options.spatial_step_deg || 0.5;
      let uud = global.population_Stadester_uud || {};

      //Function body
      for (let i = 0; i < gazetteers.length; i++) {
        let gaz_entry = gazetteers[i];
        let gaz_id = gaz_entry.key || gaz_entry.id;
        let gaz_path = path.resolve(root_dir, gaz_entry.path || gaz_entry.file_path || "");
        let raw_json;

        if (!gaz_path || !fs.existsSync(gaz_path)) {
          console.error(`[ViscountGazetteerLoader] Gazetteer file missing at ${gaz_path}`);
          continue;
        }

        try {
          raw_json = JSON5.parse(fs.readFileSync(gaz_path, "utf8"));
        } catch (e) {
          console.error(`[ViscountGazetteerLoader] Failed to parse ${gaz_path}:`, e);
          continue;
        }

        let all_keys = Object.keys(raw_json);
        for (let x = 0; x < all_keys.length; x++) {
          let city_key = all_keys[x];
          let raw_city = raw_json[city_key];
          if (!raw_city || !Array.isArray(raw_city.coords) || raw_city.coords.length < 2) continue;

          let lat = parseFloat(raw_city.coords[0]);
          let lng = parseFloat(raw_city.coords[1]);
          if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
          if (lat < -90 || lat > 90 || lng < -180 || lng > 180) continue;

          let clean_pop = {};
          if (raw_city.population && typeof raw_city.population === "object") {
            let pop_years = Object.keys(raw_city.population);
            for (let y = 0; y < pop_years.length; y++) {
              let yr = parseInt(pop_years[y], 10);
              let val = Number(raw_city.population[pop_years[y]]);
              if (Number.isFinite(yr) && Number.isFinite(val) && val > 0)
                clean_pop[yr] = Math.round(val);
            }
          }
          if (Object.keys(clean_pop).length === 0) continue;

          let candidate_city = {
            _raw_lapsed: Boolean(raw_city._raw_lapsed === true || clean_pop["-999"] === 0),
            coords: [lat, lng],
            country: raw_city.country || gaz_entry.default_country || proj.default_country || "Russia",
            key: city_key,
            name: raw_city.name || city_key.split("-")[0],
            original_names: [],
            other_names: Array.isArray(raw_city.other_names) ? raw_city.other_names.slice() : [],
            polaris_priority: gaz_entry.priority || 1,
            polaris_source: gaz_id,
            population: clean_pop,
            region: raw_city.region || gaz_id,
            sources: [proj.key],
            viscount_order: proj.order,
            viscount_project: proj.key,
            viscount_z_priority: proj.z_priority
          };
          let raw_found = (raw_city["found.yr"] !== undefined) ? raw_city["found.yr"] : raw_city.foundation_year;
          if (raw_found !== undefined && Number.isFinite(Number(raw_found))) {
            let parsed_found = parseInt(raw_found, 10);
            candidate_city["found.yr"] = parsed_found;
            candidate_city.foundation_year = parsed_found;
          }
          if (Number.isFinite(candidate_city["found.yr"])) {
            let cand_f_yr = candidate_city["found.yr"];
            let pop_clean_keys = Object.keys(clean_pop);
            for (let py = 0; py < pop_clean_keys.length; py++) {
              let yr_clean_n = parseInt(pop_clean_keys[py], 10);
              if (Number.isFinite(yr_clean_n) && yr_clean_n < cand_f_yr)
                delete clean_pop[pop_clean_keys[py]];
            }
          }
          if (gaz_id === "russian_invasion_of_ukraine" && (candidate_city.country === "Ukraine" || raw_city._war_displacement === true))
            candidate_city._war_displacement_years = Object.keys(clean_pop).map(Number).filter(function (arg0_n) { return !isNaN(arg0_n); });

          let candidate_names = (typeof uud.getAllCityNames === "function") ? uud.getAllCityNames(candidate_city) : [candidate_city.name];
          candidate_city.original_names = candidate_names.slice();

          let cand_yr_nums = Object.keys(candidate_city.population).map(Number).filter(function (arg0_n) { return !isNaN(arg0_n); }).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
          let cand_max_yr = cand_yr_nums[cand_yr_nums.length - 1];
          let cand_min_yr = cand_yr_nums[0];

          //Collect spatial bucket keys within 1 degree of candidate
          let base_gx = Math.floor(lng/spatial_step_deg);
          let base_gy = Math.floor(lat/spatial_step_deg);
          let candidate_pool = [];
          for (let dx = -1; dx <= 1; dx++) {
            for (let dy = -1; dy <= 1; dy++) {
              let bucket = spatial_grid.get(`${base_gx + dx},${base_gy + dy}`);
              if (bucket) {
                for (let b = 0; b < bucket.length; b++)
                  candidate_pool.push(bucket[b]);
              }
            }
          }

          let matched_key = undefined;
          for (let y = 0; y < candidate_pool.length; y++) {
            let ex_key = candidate_pool[y];
            let ex_city = return_obj[ex_key];
            if (!ex_city) continue;

            let dist_km = (typeof uud.haversineDistance === "function") ?
              uud.haversineDistance(ex_city.coords, candidate_city.coords) : 999999;
            if (dist_km > haversine_name_match_km) continue;

            let is_cross_project = ex_city.viscount_project !== candidate_city.viscount_project;
            let is_name_match = (typeof uud.checkExactNameMatch === "function") ?
              uud.checkExactNameMatch(ex_city, candidate_city) : (ex_city.name === candidate_city.name);

            if (is_name_match || (is_cross_project && dist_km <= exact_coord_match_km)) {
              let ex_yr_nums = Object.keys(ex_city.population).map(Number).filter(function (arg0_n) { return !isNaN(arg0_n); }).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
              let ex_max_yr = ex_yr_nums[ex_yr_nums.length - 1];
              let ex_min_yr = ex_yr_nums[0];
              let is_pre1815_bridge = (Math.min(ex_max_yr, cand_max_yr) <= 1815 && is_name_match);

              if (!is_cross_project && ex_city.polaris_priority === 3 && candidate_city.polaris_priority === 3 && ex_city.key !== candidate_city.key && dist_km > 0.3)
                continue;
              if (dist_km > 1.0 && !is_pre1815_bridge && !this.hasCompatiblePopulationScale(ex_city.population, candidate_city.population))
                continue;
              let is_temporally_compatible = true;

              if (ex_min_yr > cand_max_yr || cand_min_yr > ex_max_yr) {
                let gap_end = (ex_min_yr > cand_max_yr) ? ex_min_yr : cand_min_yr;
                let gap_start = (ex_min_yr > cand_max_yr) ? cand_max_yr : ex_max_yr;
                let max_allowed_gap = (typeof uud.getMaxTemporalProximityGap === "function") ?
                  uud.getMaxTemporalProximityGap(gap_start, gap_end) :
                  ((gap_start < 0 && gap_end <= 200) ? 1000 : 200);
                if ((gap_end - gap_start) > max_allowed_gap)
                  is_temporally_compatible = false;
              }
              if (is_temporally_compatible) {
                matched_key = ex_key;
                ex_city._matched_max_yr = ex_max_yr;
                break;
              }
            }
          }

          if (matched_key) {
            let ex_city = return_obj[matched_key];
            let cand_years = Object.keys(candidate_city.population);
            let ex_is_higher_z = (ex_city.viscount_z_priority > candidate_city.viscount_z_priority);

            for (let y = 0; y < cand_years.length; y++) {
              let yr = cand_years[y];
              if (ex_is_higher_z) {
                //Higher z_priority project keeps canonical values; lower z_priority backfills missing years only
                if (ex_city.population[yr] === undefined)
                  ex_city.population[yr] = candidate_city.population[yr];
              } else if (gaz_id === "russian_invasion_of_ukraine" || ex_city.population[yr] === undefined) {
                ex_city.population[yr] = candidate_city.population[yr];
              } else if (ex_city.polaris_priority === candidate_city.polaris_priority) {
                ex_city.population[yr] = Math.round(Math.sqrt(ex_city.population[yr]*candidate_city.population[yr]));
              }
            }

            let prev_max_yr = Number.isFinite(ex_city._matched_max_yr) ? ex_city._matched_max_yr : -Infinity;
            delete ex_city._matched_max_yr;
            let cand_found = Number(candidate_city["found.yr"] !== undefined ? candidate_city["found.yr"] : candidate_city.foundation_year);
            if (Number.isFinite(cand_found) && (ex_city["found.yr"] === undefined || cand_found < Number(ex_city["found.yr"]))) {
              ex_city["found.yr"] = cand_found;
              ex_city.foundation_year = cand_found;
            }
            let eff_found = Number(ex_city["found.yr"] !== undefined ? ex_city["found.yr"] : ex_city.foundation_year);
            if (Number.isFinite(eff_found)) {
              let ex_pop_keys = Object.keys(ex_city.population);
              for (let ey = 0; ey < ex_pop_keys.length; ey++) {
                let yr_num = parseInt(ex_pop_keys[ey], 10);
                if (Number.isFinite(yr_num) && yr_num < eff_found)
                  delete ex_city.population[ex_pop_keys[ey]];
              }
            }
            if (cand_max_yr > prev_max_yr && !candidate_city._raw_lapsed)
              ex_city._raw_lapsed = false;
            else if (candidate_city._raw_lapsed && cand_max_yr >= prev_max_yr)
              ex_city._raw_lapsed = true;

            if (Array.isArray(candidate_city._war_displacement_years)) {
              if (!ex_city._war_displacement_years) ex_city._war_displacement_years = [];
              for (let y = 0; y < candidate_city._war_displacement_years.length; y++) {
                let w_yr = candidate_city._war_displacement_years[y];
                if (!ex_city._war_displacement_years.includes(w_yr))
                  ex_city._war_displacement_years.push(w_yr);
              }
            }
            for (let y = 0; y < candidate_city.other_names.length; y++)
              if (!ex_city.other_names.includes(candidate_city.other_names[y]))
                ex_city.other_names.push(candidate_city.other_names[y]);
            for (let y = 0; y < candidate_city.original_names.length; y++)
              if (!ex_city.original_names.includes(candidate_city.original_names[y]))
                ex_city.original_names.push(candidate_city.original_names[y]);
            if (typeof uud.appendCitySources === "function") {
              uud.appendCitySources(ex_city, candidate_city.sources || proj.key);
            } else {
              if (!Array.isArray(ex_city.sources)) ex_city.sources = [];
              if (proj.key && !ex_city.sources.includes(proj.key))
                ex_city.sources.push(proj.key);
            }
          } else {
            let target_key = city_key;
            if (return_obj[target_key]) {
              for (let suffix = 2; suffix <= 9999; suffix++) {
                let cand_key = `${city_key}_${suffix}`;
                if (!return_obj[cand_key]) {
                  target_key = cand_key;
                  break;
                }
              }
            }
            candidate_city.key = target_key;
            return_obj[target_key] = candidate_city;
            loaded_counts[proj.key] = (loaded_counts[proj.key] || 0) + 1;

            let grid_key = `${base_gx},${base_gy}`;
            if (!spatial_grid.has(grid_key))
              spatial_grid.set(grid_key, []);
            spatial_grid.get(grid_key).push(target_key);
          }
        }
      }
    }


    /**
     * Resolves active Viscount project descriptors on disk sorted strictly by inverse `z_priority` (`14 -> 1`).
     * @alias ViscountGazetteerLoader.resolveActiveProjects
     *
     * @param {string} arg0_root_dir
     * @param {Object} [arg1_options]
     *
     * @returns {Array<Object>}
     */
    static resolveActiveProjects (arg0_root_dir, arg1_options) {
      //Convert from parameters
      let root_dir = arg0_root_dir;
      let options = (arg1_options) ? arg1_options : {};

      //Declare local instance variables
      let active = [];
      let filter_set = null;
      let registry = (global.StadesterPartitionIO) ?
        global.StadesterPartitionIO.loadPrecedenceRegistry(options.precedence_config_path) : null;

      //Guard clauses
      if (!registry || !Array.isArray(registry.projects)) return [];

      //Function body
      if (options.only_project) {
        filter_set = new Set([String(options.only_project).toUpperCase()]);
      } else if (Array.isArray(options.project_keys) && options.project_keys.length > 0) {
        filter_set = new Set(options.project_keys.map(function (arg0_k) { return String(arg0_k).toUpperCase(); }));
      }

      for (let i = 0; i < registry.projects.length; i++) {
        let proj = registry.projects[i];
        if (filter_set && !filter_set.has(proj.key)) continue;

        let manifest_abs = (options.config_path && filter_set && filter_set.size === 1) ?
          path.resolve(options.config_path) :
          (proj.gazetteer_manifest ? path.resolve(root_dir, proj.gazetteer_manifest) : "");

        if (manifest_abs && fs.existsSync(manifest_abs))
          active.push(proj);
      }

      //Sort strictly descending by z_priority (14 -> 1) so higher-order regions claim borderlands first
      active.sort(function (arg0_a, arg1_b) {
        return (arg1_b.z_priority || arg1_b.order || 0) - (arg0_a.z_priority || arg0_a.order || 0);
      });

      //Return statement
      return active;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountGazetteerLoader: global.ViscountGazetteerLoader };
