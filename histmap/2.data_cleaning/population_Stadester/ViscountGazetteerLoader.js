//Initialise functions
{
  let fs = global.fs || require("fs");
  let JSON5 = global.JSON5 || require("json5");
  let path = global.path || require("path");

  if (!global.StadesterPartitionIO && typeof require !== "undefined") {
    try { require(path.join(__dirname, "StadesterPartitionIO.js")); } catch (e) {}
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

      let proj_summary = Object.keys(loaded_count_by_project)
        .map(function (arg0_k) { return `${arg0_k}: ${loaded_count_by_project[arg0_k]}`; })
        .join(", ");
      console.log(`- [ViscountGazetteerLoader] Loaded ${Object.keys(return_obj).length} deduplicated settlements from ${active_projects.length} Viscount project(s) / ${total_gazetteer_files} gazetteers (${proj_summary}).`);

      //Return statement
      return return_obj;
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
          if (gaz_id === "russian_invasion_of_ukraine")
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
            let suffix = 2;
            let target_key = city_key;
            while (return_obj[target_key]) {
              target_key = `${city_key}_${suffix}`;
              suffix++;
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
